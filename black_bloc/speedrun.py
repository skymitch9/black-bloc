"""speedrun.com's public REST API v1: one runner by Twitch name, and a runner's personal bests."""

from __future__ import annotations

import json
import logging
import math
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote, urlsplit

from . import __version__

log = logging.getLogger(__name__)

API_URL = "https://www.speedrun.com/api/v1"
SITE = "speedrun.com"
REQUEST_TIMEOUT_SECONDS = 20
MAX_BODY_BYTES = 16_000_000
READ_BYTES = 65_536
PAGE_MAX = 200
PAGE_LIMIT = 5
LOOKUP_MAX = 20
AGENT = "BlackBloc/{version} (Discord bot for a speedrunning community; {origin})"
AGENT_ORIGIN = "https://github.com/skymitch9/black-bloc"
EMBED_FULL = "game,category.variables,level"
EMBED_PLAIN = "game,category,level"
EMBED_RETRY_SECONDS = 6 * 60 * 60
UNTOLD = "?"
VERIFIED = "verified"
TWITCH_HOSTS = ("twitch.tv", "www.twitch.tv", "m.twitch.tv")

THROTTLED = "throttled"
SERVER = "server"
UNREACHABLE = "unreachable"
BAD_ANSWER = "bad_answer"
NOT_FOUND = "not_found"
REFUSED = "refused"
TOO_LARGE = "too_large"
MALFORMED = "malformed"
OUTAGE_KINDS = (THROTTLED, SERVER, UNREACHABLE, BAD_ANSWER)

SAID = {
    THROTTLED: (
        "speedrun.com said Black Bloc is asking too often (it answered {status}), so nothing was "
        "read. Black Bloc waits before it asks again; nothing needs doing."
    ),
    SERVER: (
        "speedrun.com answered with a fault of its own ({status}), so nothing was read. Black "
        "Bloc waits and asks again; nothing needs doing unless it lasts for hours."
    ),
    UNREACHABLE: (
        "speedrun.com could not be reached ({why}), so nothing was read. That is the network "
        "or their site, not a setting here; Black Bloc waits and asks again."
    ),
    BAD_ANSWER: (
        "speedrun.com answered with something Black Bloc could not read ({why}), so nothing "
        "was taken from it. Black Bloc waits and asks again."
    ),
    NOT_FOUND: (
        "speedrun.com has nothing at that address (it answered 404), so that account is taken "
        "to be gone."
    ),
    TOO_LARGE: (
        "speedrun.com's answer for this runner is larger than Black Bloc will read, so their "
        "personal bests were not looked at. Tell a Lead: this needs a change in the bot."
    ),
    REFUSED: (
        "speedrun.com refused the question Black Bloc asked (it answered {status}), so nothing "
        "was read. Tell a Lead: this needs a change in the bot."
    ),
    MALFORMED: (
        "speedrun.com's answer here was not the list its API documents ({why}), so nothing was "
        "taken from it. Nobody else is affected; Black Bloc asks again at the next look."
    ),
}


class SpeedrunError(RuntimeError):
    """speedrun.com could not be read; `kind` says how, the message says it in words."""

    def __init__(self, kind: str, *, status: int = 0, why: str = "") -> None:
        super().__init__(SAID[kind].format(status=status, why=why))
        self.kind = kind
        self.status = status

    @property
    def outage(self) -> bool:
        return self.kind in OUTAGE_KINDS


@dataclass(frozen=True)
class Runner:
    id: str
    name: str
    weblink: str
    twitch_login: str | None


@dataclass(frozen=True)
class PersonalBest:
    run_id: str
    slot: str
    game: str
    category: str
    seconds: float
    place: int | None
    weblink: str
    status: str
    verified_at: datetime | None


def agent(origin: Any = None) -> str:
    return AGENT.format(version=__version__, origin=str(origin or "").strip() or AGENT_ORIGIN)


def words(value: Any) -> str:
    """Text speedrun.com sent as text; anything else is nothing."""
    return value if isinstance(value, str) else ""


def twitch_login_of(uri: Any) -> str | None:
    """The login a twitch.tv address names, case-folded; anything else is no login."""
    text = words(uri).strip()
    if not text:
        return None
    try:
        parts = urlsplit(text if "//" in text else f"https://{text}")
    except ValueError:
        return None
    if parts.netloc.casefold() not in TWITCH_HOSTS:
        return None
    path = [piece for piece in parts.path.split("/") if piece]
    return path[0].casefold() if len(path) == 1 else None


def unwrapped(found: Any) -> dict[str, Any]:
    """An embed is `{"data": {...}}`; an empty one is `{"data": []}`; a bare id is a string."""
    if isinstance(found, dict):
        inner = found.get("data", found)
        return inner if isinstance(inner, dict) else {}
    return {}


def id_of(found: Any) -> str:
    if isinstance(found, str):
        return found
    return words(unwrapped(found).get("id"))


def runner_from(row: Any) -> Runner | None:
    if not isinstance(row, dict) or not words(row.get("id")):
        return None
    names = row.get("names") if isinstance(row.get("names"), dict) else {}
    twitch = row.get("twitch") if isinstance(row.get("twitch"), dict) else {}
    return Runner(
        id=row["id"],
        name=words(names.get("international")) or words(names.get("japanese")) or row["id"],
        weblink=words(row.get("weblink")),
        twitch_login=twitch_login_of(twitch.get("uri")),
    )


def parsed_time(value: Any) -> datetime | None:
    try:
        found = datetime.fromisoformat(words(value).replace("Z", "+00:00"))
    except (TypeError, ValueError, OverflowError):
        return None
    return found if found.tzinfo else found.replace(tzinfo=UTC)


def seconds_of(value: Any) -> float | None:
    """A leaderboard time as a real, positive number of seconds, or None."""
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        return None
    try:
        found = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return found if math.isfinite(found) and found > 0 else None


def place_of(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def subcategories(category: dict[str, Any], values: Any) -> tuple[list[tuple[str, str]], list[str]]:
    """The sub-category choices a run made, as id pairs and as the labels people read."""
    variables = category.get("variables")
    listed = variables.get("data") if isinstance(variables, dict) else None
    chosen = values if isinstance(values, dict) else {}
    pairs: list[tuple[str, str]] = []
    labels: list[str] = []
    for variable in listed if isinstance(listed, list) else ():
        if not isinstance(variable, dict) or not variable.get("is-subcategory"):
            continue
        name = words(variable.get("id"))
        picked = words(chosen.get(name)) if name else ""
        if not picked:
            continue
        pairs.append((name, picked))
        held = variable.get("values")
        options = held.get("values") if isinstance(held, dict) else None
        option = options.get(picked) if isinstance(options, dict) else None
        label = words(option.get("label")) if isinstance(option, dict) else ""
        if label:
            labels.append(label)
    return (sorted(pairs), labels)


def untold(values: Any) -> str:
    """Every choice a run made, when which of them are sub-categories was not told."""
    chosen = values if isinstance(values, dict) else {}
    pairs = sorted(
        (name, picked) for name, picked in chosen.items() if words(name) and words(picked)
    )
    return UNTOLD + ",".join(f"{one}={two}" for one, two in pairs) if pairs else ""


def category_words(level: str, category: str, labels: list[str]) -> str:
    said = f"{level}: {category}" if level and category else level or category
    return f"{said} ({', '.join(labels)})" if labels else said


def game_name(game: dict[str, Any]) -> str:
    names = game.get("names") if isinstance(game.get("names"), dict) else {}
    return (
        words(names.get("international")) or words(names.get("japanese")) or words(game.get("id"))
    )


def personal_best_from(item: Any, *, nested: bool = True) -> PersonalBest | None:
    """One listed run; `nested` is whether the answer came with the sub-category variables."""
    if not isinstance(item, dict) or not isinstance(item.get("run"), dict):
        return None
    run = item["run"]
    times = run.get("times") if isinstance(run.get("times"), dict) else {}
    seconds = seconds_of(times.get("primary_t"))
    run_id = words(run.get("id"))
    if not run_id or seconds is None:
        return None
    game = unwrapped(item.get("game"))
    category = unwrapped(item.get("category"))
    level = unwrapped(item.get("level"))
    game_id = id_of(item.get("game")) or id_of(run.get("game"))
    category_id = id_of(item.get("category")) or id_of(run.get("category"))
    level_id = id_of(item.get("level")) or id_of(run.get("level"))
    pairs, labels = subcategories(category, run.get("values"))
    choices = (
        ",".join(f"{one}={two}" for one, two in pairs) if nested else untold(run.get("values"))
    )
    status = run.get("status") if isinstance(run.get("status"), dict) else {}
    return PersonalBest(
        run_id=run_id,
        slot="|".join([game_id, category_id, level_id, choices]),
        game=game_name(game) or game_id,
        category=category_words(words(level.get("name")), words(category.get("name")), labels),
        seconds=seconds,
        place=place_of(item.get("place")),
        weblink=words(run.get("weblink")),
        status=words(status.get("status")),
        verified_at=parsed_time(status.get("verify-date")),
    )


def more_pages(payload: dict[str, Any], asked: int) -> bool:
    pagination = payload.get("pagination")
    if not isinstance(pagination, dict):
        return False
    try:
        return int(pagination.get("size")) >= int(asked)
    except (TypeError, ValueError, OverflowError):
        return False


def listed(payload: dict[str, Any]) -> list[Any]:
    """The rows of an answer; anything but a list is that one question's trouble."""
    rows = payload["data"]
    if not isinstance(rows, list):
        raise SpeedrunError(MALFORMED, why=f"data was a {type(rows).__name__}")
    return rows


async def whole_body(content: Any, cap: int) -> bytes | None:
    """The answer read to its end, or None once it has really passed the cap."""
    pieces: list[bytes] = []
    size = 0
    async for piece in content.iter_chunked(READ_BYTES):
        size += len(piece)
        if size > cap:
            return None
        pieces.append(piece)
    return b"".join(pieces)


class SpeedrunClient:
    """One GET per question, timed out and under the bot's own agent; it raises SpeedrunError."""

    def __init__(self, *, request: Any = None, origin: Any = None, clock: Any = None) -> None:
        self._request = request or self._aiohttp_request
        self._session: Any = None
        self._clock = clock or time.monotonic
        self.agent = agent(origin)
        self.plain_since: float | None = None
        self.requests = 0

    @property
    def embed(self) -> str:
        """The nested embed, unless it was refused less than EMBED_RETRY_SECONDS ago."""
        since = self.plain_since
        if since is not None and self._clock() - since >= EMBED_RETRY_SECONDS:
            self.plain_since = None
        return EMBED_FULL if self.plain_since is None else EMBED_PLAIN

    def _open(self) -> Any:
        import aiohttp

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
            )
        return self._session

    async def _aiohttp_request(self, url: str, headers: dict[str, str]) -> tuple[int, Any]:
        import aiohttp

        try:
            async with self._open().get(url, headers=headers) as response:
                if response.status != 200:
                    return (response.status, None)
                body = await whole_body(response.content, MAX_BODY_BYTES)
                if body is None:
                    raise SpeedrunError(TOO_LARGE)
                try:
                    return (200, json.loads(body))
                except ValueError:
                    return (200, None)
        except (TimeoutError, aiohttp.ClientError, OSError) as exc:
            raise SpeedrunError(UNREACHABLE, why=type(exc).__name__) from exc

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    async def get(self, path: str) -> dict[str, Any]:
        self.requests += 1
        status, body = await self._request(
            f"{API_URL}{path}", {"User-Agent": self.agent, "Accept": "application/json"}
        )
        if status == 200:
            if not isinstance(body, dict) or "data" not in body:
                raise SpeedrunError(BAD_ANSWER, why="it was not the JSON the API documents")
            return body
        if status in (420, 429):
            raise SpeedrunError(THROTTLED, status=status)
        if status == 404:
            raise SpeedrunError(NOT_FOUND, status=status)
        if status >= 500:
            raise SpeedrunError(SERVER, status=status)
        raise SpeedrunError(REFUSED, status=status)

    async def users_by_twitch(self, login: str) -> list[Runner]:
        """Whoever speedrun.com returns for a Twitch name; the caller decides who is a match."""
        wanted = quote(str(login).strip(), safe="")
        payload = await self.get(f"/users?twitch={wanted}&max={LOOKUP_MAX}")
        return [found for found in map(runner_from, listed(payload)) if found is not None]

    async def users_by_name(self, name: str) -> list[Runner]:
        wanted = quote(str(name).strip(), safe="")
        payload = await self.get(f"/users?lookup={wanted}&max={LOOKUP_MAX}")
        return [found for found in map(runner_from, listed(payload)) if found is not None]

    async def _bests_page(self, runner_id: str, offset: int) -> tuple[dict[str, Any], bool]:
        """One page, and whether it came with the sub-category variables."""
        path = "/users/{who}/personal-bests?embed={embed}&max={max}&offset={offset}"
        wanted = quote(str(runner_id), safe="")
        embed = self.embed
        try:
            payload = await self.get(
                path.format(who=wanted, embed=embed, max=PAGE_MAX, offset=offset)
            )
            return (payload, embed == EMBED_FULL)
        except SpeedrunError as exc:
            if exc.status != 400 or embed == EMBED_PLAIN:
                raise
            refused = exc
        try:
            payload = await self.get(
                path.format(who=wanted, embed=EMBED_PLAIN, max=PAGE_MAX, offset=offset)
            )
        except SpeedrunError as again:
            if again.status == 400:
                raise refused from None
            raise
        log.warning("speedrun: the nested embed was refused; sub-categories are not told apart")
        self.plain_since = self._clock()
        return (payload, False)

    async def personal_bests(self, runner_id: str) -> list[PersonalBest]:
        """Every personal best speedrun.com lists for a runner, verified or not."""
        found: list[PersonalBest] = []
        for page in range(PAGE_LIMIT):
            payload, nested = await self._bests_page(runner_id, page * PAGE_MAX)
            for row in listed(payload):
                one = personal_best_from(row, nested=nested)
                if one is not None:
                    found.append(one)
            if not more_pages(payload, PAGE_MAX):
                break
        return found


__all__ = [
    "AGENT",
    "API_URL",
    "BAD_ANSWER",
    "EMBED_FULL",
    "EMBED_PLAIN",
    "EMBED_RETRY_SECONDS",
    "MALFORMED",
    "NOT_FOUND",
    "OUTAGE_KINDS",
    "REFUSED",
    "REQUEST_TIMEOUT_SECONDS",
    "SERVER",
    "SITE",
    "THROTTLED",
    "TOO_LARGE",
    "UNREACHABLE",
    "UNTOLD",
    "VERIFIED",
    "PersonalBest",
    "Runner",
    "SpeedrunClient",
    "SpeedrunError",
    "agent",
    "category_words",
    "personal_best_from",
    "runner_from",
    "twitch_login_of",
]
