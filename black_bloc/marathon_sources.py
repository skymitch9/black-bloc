from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .golive import twitch_login_from_url
from .youtube import BROWSER_AGENT

log = logging.getLogger(__name__)

GDQ = "gdq"
SOURCES = (GDQ,)
SOURCE_WORDS = {GDQ: "GDQ tracker"}
RUNNER = "runner"
HOST = "host"
COMMENTATOR = "commentator"
PARTS = (RUNNER, HOST, COMMENTATOR)

TRACKER = "https://tracker.gamesdonequick.com/tracker/api/v2"
EVENT_URL = TRACKER + "/events/{ref}/"
RUNS_URL = TRACKER + "/events/{ref}/runs/?limit=500"
SHORT_URL = TRACKER + "/events/?short={short}"
EVENTS_URL = TRACKER + "/events/"
TRACKER_EVENT = "https://tracker.gamesdonequick.com/tracker/event/{ref}"
SCHEDULE_PAGE = "https://gamesdonequick.com/schedule/{ref}"
REQUEST_TIMEOUT_SECONDS = 20
PAGES_MAX = 20

GDQ_SCHEDULE = re.compile(
    r"^https?://(?:www\.)?gamesdonequick\.com/schedule/(\d+)/?(?:[?#].*)?$", re.IGNORECASE
)
GDQ_TRACKER = re.compile(
    r"^https?://tracker\.gamesdonequick\.com/tracker/(?:event|runs|index)/([A-Za-z0-9_-]+)/?"
    r"(?:[?#].*)?$",
    re.IGNORECASE,
)
GDQ_SHORT = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{2,40}$")
SHORT_PREFIX = "short:"

NOT_PUBLISHED = (
    "the GDQ tracker has the event but has not published its schedule yet (it answers 404 for "
    "the runs)"
)
NO_SUCH_EVENT = "the GDQ tracker has no event {ref}"
ANSWERED = "the GDQ tracker answered {status}"
UNREACHABLE = "the GDQ tracker could not be reached ({why})"
NOT_JSON = "the GDQ tracker answered with something that is not a schedule"
TOO_MANY_PAGES = "the schedule ran past {pages} pages, so only the first ones were read"


class ScheduleError(RuntimeError):
    """A schedule could not be read; the message is words a person can be shown."""

    def __init__(self, message: str, *, unpublished: bool = False) -> None:
        super().__init__(message)
        self.unpublished = unpublished


@dataclass(frozen=True)
class Person:
    name: str
    login: str | None
    part: str


@dataclass(frozen=True)
class Run:
    external_id: str
    order: int | None
    game: str
    display_name: str
    category: str
    starts_at: str | None
    ends_at: str | None
    run_seconds: int | None
    people: tuple[Person, ...] = field(default=())
    twitch_game: str = ""


def read_url(url: Any) -> tuple[str, str] | None:
    """The source and its reference out of a link staff paste, or None for any other site."""
    text = str(url or "").strip()
    found = GDQ_SCHEDULE.match(text)
    if found:
        return (GDQ, found.group(1))
    found = GDQ_TRACKER.match(text)
    if found:
        ref = found.group(1)
        return (GDQ, ref if ref.isdigit() else SHORT_PREFIX + ref)
    if GDQ_SHORT.match(text) and not text.isdigit() and "." not in text:
        return (GDQ, SHORT_PREFIX + text)
    return None


def is_short(ref: Any) -> bool:
    return str(ref or "").startswith(SHORT_PREFIX)


def schedule_page(source: str, ref: Any) -> str:
    return SCHEDULE_PAGE.format(ref=ref) if source == GDQ and not is_short(ref) else ""


def seconds_of(text: Any) -> int | None:
    """`1:07:15` → 4035; the tracker also writes `0` and leaves it blank."""
    parts = str(text or "").strip().split(":")
    if not parts or not all(one.isdigit() for one in parts) or len(parts) > 3:
        return None
    total = 0
    for one in parts:
        total = total * 60 + int(one)
    return total


def utc_iso(text: Any) -> str | None:
    try:
        moment = datetime.fromisoformat(str(text or "").strip())
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).isoformat()


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _people(row: dict[str, Any]) -> tuple[Person, ...]:
    found: list[Person] = []
    for part, column in ((RUNNER, "runners"), (HOST, "hosts"), (COMMENTATOR, "commentators")):
        for talent in row.get(column) or ():
            if not isinstance(talent, dict):
                continue
            name = _text(talent.get("name"))
            if not name:
                continue
            found.append(Person(name, twitch_login_from_url(talent.get("stream")), part))
    return tuple(found)


def parse_gdq(payload: Any) -> list[Run]:
    """One page of `/events/<id>/runs/` into runs; a row without an id or a name is skipped."""
    rows = payload.get("results") if isinstance(payload, dict) else payload
    found: list[Run] = []
    for row in rows or ():
        if not isinstance(row, dict) or row.get("id") is None:
            continue
        game = _text(row.get("name")) or _text(row.get("display_name"))
        if not game:
            continue
        order = row.get("order")
        found.append(
            Run(
                external_id=str(row["id"]),
                order=int(order) if isinstance(order, int) else None,
                game=game,
                display_name=_text(row.get("display_name")) or game,
                category=_text(row.get("category")),
                starts_at=utc_iso(row.get("starttime")),
                ends_at=utc_iso(row.get("endtime")),
                run_seconds=seconds_of(row.get("run_time")),
                people=_people(row),
                twitch_game=_text(row.get("twitch_name")),
            )
        )
    return found


def next_page(payload: Any) -> str | None:
    found = payload.get("next") if isinstance(payload, dict) else None
    return str(found) if found else None


def event_url(ref: Any) -> str:
    return TRACKER_EVENT.format(ref=ref)


def next_gdq_event(events: Any, after: Any, now: datetime) -> dict[str, Any] | None:
    """The soonest event still ahead that is not `after` (the marathon's own id); archived ones
    are history. A draft is kept: every announced GDQ event is a draft until its schedule is up."""
    own = str(after or "")
    ahead: list[tuple[datetime, dict[str, Any]]] = []
    for row in events or ():
        if not isinstance(row, dict) or row.get("id") is None or row.get("archived"):
            continue
        if str(row["id"]) == own:
            continue
        starts = utc_iso(row.get("datetime"))
        if starts is None:
            continue
        moment = datetime.fromisoformat(starts)
        if moment > now:
            ahead.append((moment, row))
    ahead.sort(key=lambda one: (one[0], str(one[1]["id"])))
    return ahead[0][1] if ahead else None


def event_from(payload: Any) -> dict[str, Any] | None:
    rows = payload.get("results") if isinstance(payload, dict) else None
    for row in rows or ():
        if isinstance(row, dict) and row.get("id") is not None:
            return row
    return None


class ScheduleClient:
    """One GET per page through the bot's own agent; every failure is a ScheduleError."""

    def __init__(self, *, request: Any = None) -> None:
        self._request = request or self._aiohttp_request
        self._session: Any = None

    async def _aiohttp_request(self, url: str) -> tuple[int, Any]:
        import aiohttp

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
            )
        try:
            async with self._session.get(url, headers={"User-Agent": BROWSER_AGENT}) as response:
                if response.status != 200:
                    return (response.status, None)
                try:
                    return (200, await response.json(content_type=None))
                except ValueError:
                    return (200, None)
        except (TimeoutError, aiohttp.ClientError, OSError) as exc:
            raise ScheduleError(UNREACHABLE.format(why=type(exc).__name__)) from exc

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    async def _json(self, url: str) -> tuple[int, Any]:
        status, body = await self._request(url)
        if status == 200 and not isinstance(body, dict):
            raise ScheduleError(NOT_JSON)
        return (status, body)

    async def resolve(self, source: str, ref: str) -> tuple[str, str]:
        """(the event id, its name) — a short such as `AGDQ2027` is looked up once here."""
        if source != GDQ:
            raise ScheduleError(NO_SUCH_EVENT.format(ref=ref))
        if is_short(ref):
            short = ref[len(SHORT_PREFIX) :]
            status, body = await self._json(SHORT_URL.format(short=short))
            if status != 200:
                raise ScheduleError(ANSWERED.format(status=status))
            event = event_from(body)
            if event is None:
                raise ScheduleError(NO_SUCH_EVENT.format(ref=short))
            return (str(event["id"]), _text(event.get("name")) or short)
        status, body = await self._json(EVENT_URL.format(ref=ref))
        if status == 404:
            raise ScheduleError(NO_SUCH_EVENT.format(ref=ref))
        if status != 200:
            raise ScheduleError(ANSWERED.format(status=status))
        return (str(body.get("id") or ref), _text(body.get("name")) or str(ref))

    async def events(self) -> list[dict[str, Any]]:
        """Every event the tracker lists, newest first; one page today, `next` followed if not."""
        url: str | None = EVENTS_URL
        found: list[dict[str, Any]] = []
        pages = 0
        while url and pages < PAGES_MAX:
            status, body = await self._json(url)
            if status != 200:
                raise ScheduleError(ANSWERED.format(status=status))
            found.extend(row for row in body.get("results") or () if isinstance(row, dict))
            url = next_page(body)
            pages += 1
        return found

    async def runs(self, source: str, ref: str) -> list[Run]:
        if source != GDQ:
            raise ScheduleError(NO_SUCH_EVENT.format(ref=ref))
        url: str | None = RUNS_URL.format(ref=ref)
        found: list[Run] = []
        pages = 0
        while url and pages < PAGES_MAX:
            status, body = await self._json(url)
            if status == 404:
                raise ScheduleError(NOT_PUBLISHED, unpublished=True)
            if status != 200:
                raise ScheduleError(ANSWERED.format(status=status))
            found.extend(parse_gdq(body))
            url = next_page(body)
            pages += 1
        if url:
            log.warning("marathon: %s", TOO_MANY_PAGES.format(pages=PAGES_MAX))
        return found


__all__ = [
    "COMMENTATOR",
    "GDQ",
    "HOST",
    "PARTS",
    "RUNNER",
    "SOURCES",
    "SOURCE_WORDS",
    "Person",
    "Run",
    "ScheduleClient",
    "ScheduleError",
    "event_from",
    "event_url",
    "is_short",
    "next_gdq_event",
    "next_page",
    "parse_gdq",
    "read_url",
    "schedule_page",
    "seconds_of",
    "utc_iso",
]
