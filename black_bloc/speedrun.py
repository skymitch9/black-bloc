"""speedrun.com's public REST API v1: one runner by Twitch name, and a runner's personal bests."""

from __future__ import annotations

import json
import logging
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
VERIFIED = "verified"
TWITCH_HOSTS = ("twitch.tv", "www.twitch.tv", "m.twitch.tv")

THROTTLED = "throttled"
SERVER = "server"
UNREACHABLE = "unreachable"
BAD_ANSWER = "bad_answer"
NOT_FOUND = "not_found"
REFUSED = "refused"
TOO_LARGE = "too_large"
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


def twitch_login_of(uri: Any) -> str | None:
    """The login a twitch.tv address names, case-folded; anything else is no login."""
    text = str(uri or "").strip()
    if not text:
        return None
    parts = urlsplit(text if "//" in text else f"https://{text}")
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
    return str(unwrapped(found).get("id") or "")


def runner_from(row: Any) -> Runner | None:
    if not isinstance(row, dict) or not row.get("id"):
        return None
    names = row.get("names") if isinstance(row.get("names"), dict) else {}
    twitch = row.get("twitch") if isinstance(row.get("twitch"), dict) else {}
    return Runner(
        id=str(row["id"]),
        name=str(names.get("international") or names.get("japanese") or row["id"]),
        weblink=str(row.get("weblink") or ""),
        twitch_login=twitch_login_of(twitch.get("uri")),
    )


def parsed_time(value: Any) -> datetime | None:
    try:
        found = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return found if found.tzinfo else found.replace(tzinfo=UTC)


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
        picked = chosen.get(variable.get("id"))
        if not picked:
            continue
        pairs.append((str(variable["id"]), str(picked)))
        options = (variable.get("values") or {}).get("values") or {}
        label = (options.get(picked) or {}).get("label") if isinstance(options, dict) else None
        if label:
            labels.append(str(label))
    return (sorted(pairs), labels)


def category_words(level: str, category: str, labels: list[str]) -> str:
    words = f"{level}: {category}" if level and category else level or category
    return f"{words} ({', '.join(labels)})" if labels else words


def game_name(game: dict[str, Any]) -> str:
    names = game.get("names") if isinstance(game.get("names"), dict) else {}
    return str(names.get("international") or names.get("japanese") or game.get("id") or "")


def personal_best_from(item: Any) -> PersonalBest | None:
    if not isinstance(item, dict) or not isinstance(item.get("run"), dict):
        return None
    run = item["run"]
    times = run.get("times") if isinstance(run.get("times"), dict) else {}
    try:
        seconds = float(times.get("primary_t"))
    except (TypeError, ValueError):
        return None
    if not run.get("id") or seconds <= 0:
        return None
    game = unwrapped(item.get("game"))
    category = unwrapped(item.get("category"))
    level = unwrapped(item.get("level"))
    game_id = id_of(item.get("game")) or id_of(run.get("game"))
    category_id = id_of(item.get("category")) or id_of(run.get("category"))
    level_id = id_of(item.get("level")) or id_of(run.get("level"))
    pairs, labels = subcategories(category, run.get("values"))
    status = run.get("status") if isinstance(run.get("status"), dict) else {}
    place = item.get("place")
    slot = "|".join(
        [game_id, category_id, level_id, ",".join(f"{one}={two}" for one, two in pairs)]
    )
    return PersonalBest(
        run_id=str(run["id"]),
        slot=slot,
        game=game_name(game) or game_id,
        category=category_words(
            str(level.get("name") or ""), str(category.get("name") or ""), labels
        ),
        seconds=seconds,
        place=int(place) if isinstance(place, int) and place > 0 else None,
        weblink=str(run.get("weblink") or ""),
        status=str(status.get("status") or ""),
        verified_at=parsed_time(status.get("verify-date")),
    )


def more_pages(payload: dict[str, Any], asked: int) -> bool:
    pagination = payload.get("pagination")
    if not isinstance(pagination, dict):
        return False
    try:
        return int(pagination.get("size")) >= int(asked)
    except (TypeError, ValueError):
        return False


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

    def __init__(self, *, request: Any = None, origin: Any = None) -> None:
        self._request = request or self._aiohttp_request
        self._session: Any = None
        self.agent = agent(origin)
        self.embed = EMBED_FULL
        self.requests = 0

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
                body = await whole_body(response.content, MAX_BODY_BYTES)
                if body is None:
                    if response.status == 200:
                        raise SpeedrunError(TOO_LARGE)
                    return (response.status, None)
                try:
                    return (response.status, json.loads(body))
                except ValueError:
                    return (response.status, None)
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
        rows = payload["data"] if isinstance(payload["data"], list) else []
        return [found for found in map(runner_from, rows) if found is not None]

    async def users_by_name(self, name: str) -> list[Runner]:
        wanted = quote(str(name).strip(), safe="")
        payload = await self.get(f"/users?lookup={wanted}&max={LOOKUP_MAX}")
        rows = payload["data"] if isinstance(payload["data"], list) else []
        return [found for found in map(runner_from, rows) if found is not None]

    async def _bests_page(self, runner_id: str, offset: int) -> dict[str, Any]:
        path = "/users/{who}/personal-bests?embed={embed}&max={max}&offset={offset}"
        wanted = quote(str(runner_id), safe="")
        try:
            return await self.get(
                path.format(who=wanted, embed=self.embed, max=PAGE_MAX, offset=offset)
            )
        except SpeedrunError as exc:
            if exc.status != 400 or self.embed == EMBED_PLAIN:
                raise
            log.warning("speedrun: the nested embed was refused; asking without sub-categories")
            self.embed = EMBED_PLAIN
            return await self.get(
                path.format(who=wanted, embed=self.embed, max=PAGE_MAX, offset=offset)
            )

    async def personal_bests(self, runner_id: str) -> list[PersonalBest]:
        """Every personal best speedrun.com lists for a runner, verified or not."""
        found: list[PersonalBest] = []
        for page in range(PAGE_LIMIT):
            payload = await self._bests_page(runner_id, page * PAGE_MAX)
            rows = payload["data"] if isinstance(payload["data"], list) else []
            found.extend(one for one in map(personal_best_from, rows) if one is not None)
            if not more_pages(payload, PAGE_MAX):
                break
        return found


__all__ = [
    "AGENT",
    "API_URL",
    "BAD_ANSWER",
    "EMBED_FULL",
    "EMBED_PLAIN",
    "NOT_FOUND",
    "OUTAGE_KINDS",
    "REFUSED",
    "REQUEST_TIMEOUT_SECONDS",
    "SERVER",
    "SITE",
    "THROTTLED",
    "TOO_LARGE",
    "UNREACHABLE",
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
