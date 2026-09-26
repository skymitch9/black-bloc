from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from .golive import twitch_login_from_url
from .youtube import BROWSER_AGENT

log = logging.getLogger(__name__)

GDQ = "gdq"
RPGLB = "rpglb"
HORARO = "horaro"
OENGUS = "oengus"
TRACKER_SOURCES = (GDQ, RPGLB)
SOURCES = (*TRACKER_SOURCES, HORARO, OENGUS)
SOURCE_WORDS = {
    GDQ: "GDQ tracker",
    RPGLB: "RPG Limit Break tracker",
    HORARO: "horaro.net",
    OENGUS: "Oengus",
}
SITE_WORDS = {
    GDQ: "the GDQ tracker",
    RPGLB: "the RPG Limit Break tracker",
    HORARO: "horaro.net",
    OENGUS: "oengus.io",
}
RUNNER = "runner"
HOST = "host"
COMMENTATOR = "commentator"
PARTS = (RUNNER, HOST, COMMENTATOR)

TRACKER_BASES = {
    GDQ: "https://tracker.gamesdonequick.com/tracker",
    RPGLB: "https://tracker.rpglimitbreak.com",
}
API_PATH = "/api/v2"
TRACKER = TRACKER_BASES[GDQ] + API_PATH
EVENT_URL = "{api}/events/{ref}/"
RUNS_URL = "{api}/events/{ref}/runs/?limit=500"
SHORT_URL = "{api}/events/?short={short}"
EVENTS_URL = "{api}/events/"
TRACKER_EVENT = "{base}/event/{ref}"
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
RPGLB_SCHEDULE = re.compile(
    r"^https?://(?:www\.)?rpglimitbreak\.com/schedule/?(?:[?#].*)?$", re.IGNORECASE
)
RPGLB_TRACKER = re.compile(
    r"^https?://(?:(?:www\.)?rpglimitbreak\.com/tracker|tracker\.rpglimitbreak\.com)/"
    r"(?:event|runs|index)/([A-Za-z0-9_-]+)/?(?:[?#].*)?$",
    re.IGNORECASE,
)
HORARO_SCHEDULE = re.compile(
    r"^https?://(?:www\.)?horaro\.net/([A-Za-z0-9][A-Za-z0-9_-]*)/"
    r"([A-Za-z0-9][A-Za-z0-9_-]*?)(?:\.json)?/?(?:[?#].*)?$",
    re.IGNORECASE,
)
HORARO_SITE = "https://horaro.net"
HORARO_PAGE = HORARO_SITE + "/{ref}"
HORARO_JSON = HORARO_SITE + "/{ref}.json"
HORARO_SCHEDULES = HORARO_SITE + "/-/api/v1/events/{slug}/schedules"
HORARO_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,60}$")
OENGUS_URL = re.compile(
    r"^https?://(?:www\.)?oengus\.io/marathon/([A-Za-z0-9_-]{1,40})"
    r"(?:/schedule(?:/([A-Za-z0-9_-]{1,40}))?)?/?(?:[?#].*)?$",
    re.IGNORECASE,
)
OENGUS_SITE = "https://oengus.io"
OENGUS_PAGE = OENGUS_SITE + "/marathon/{id}/schedule"
OENGUS_MARATHON = OENGUS_SITE + "/api/v1/marathons/{id}"
OENGUS_SCHEDULES = OENGUS_SITE + "/api/v2/marathons/{id}/schedules"
OENGUS_LINES = OENGUS_SITE + "/api/v2/marathons/{id}/schedules/for-slug/{slug}"
OENGUS_HOME = OENGUS_SITE + "/api/v2/marathons/for-home"
OENGUS_LISTS = ("live", "next", "open")
OENGUS_ID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
OENGUS_TWITCH = "TWITCH"
ISO_DURATION = re.compile(
    r"^P(?:(\d+(?:\.\d+)?)D)?(?:T(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?"
    r"(?:(\d+(?:\.\d+)?)S)?)?$",
    re.IGNORECASE,
)
MARKDOWN_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]*)\)")
PLAYER_SPLIT = re.compile(r"\s*(?:,|&|\s+vs\.?\s+|\s+and\s+)\s*", re.IGNORECASE)
GAME_COLUMNS = ("game",)
PLAYER_COLUMNS = ("player(s)", "players", "player", "runner(s)", "runners", "runner")
CATEGORY_COLUMNS = ("category",)
ID_COLUMNS = ("hidden:id",)
GDQ_SHORT = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{2,40}$")
SHORT_PREFIX = "short:"
LATEST = "latest"

NOT_PUBLISHED_AT = (
    "{site} has the event but has not published its schedule yet (it answers 404 for the runs)"
)
NOT_PUBLISHED = NOT_PUBLISHED_AT.format(site=SITE_WORDS[GDQ])
NO_SUCH_EVENT = "{site} has no event {ref}"
NO_EVENT_YET = "{site} lists no event yet"
ANSWERED = "{site} answered {status}"
UNREACHABLE = "{site} could not be reached ({why})"
NOT_JSON = "{site} answered with something that is not a schedule"
NOT_PUBLISHED_OENGUS = "{site} has the marathon but has not published its schedule yet"
UNKNOWN_SOURCE = "Black Bloc has no reader for {source}"
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
    for source, pattern in ((GDQ, GDQ_TRACKER), (RPGLB, RPGLB_TRACKER)):
        found = pattern.match(text)
        if found:
            ref = found.group(1)
            return (source, ref if ref.isdigit() else SHORT_PREFIX + ref)
    if RPGLB_SCHEDULE.match(text):
        return (RPGLB, LATEST)
    found = HORARO_SCHEDULE.match(text)
    if found:
        return (HORARO, f"{found.group(1).lower()}/{found.group(2).lower()}")
    found = OENGUS_URL.match(text)
    if found:
        return (OENGUS, "/".join(one for one in found.groups() if one))
    if GDQ_SHORT.match(text) and not text.isdigit() and "." not in text:
        return (GDQ, SHORT_PREFIX + text)
    return None


def is_short(ref: Any) -> bool:
    return str(ref or "").startswith(SHORT_PREFIX)


def site_of(source: Any) -> str:
    return SITE_WORDS.get(str(source or ""), str(source or ""))


def api_of(source: str) -> str:
    return TRACKER_BASES[source] + API_PATH


def tracker_source(base: Any) -> str | None:
    """The source word a tracker base URL stands for, or None for a tracker Black Bloc lacks."""
    wanted = str(base or "").strip().rstrip("/").lower()
    for source, known in TRACKER_BASES.items():
        if known.lower() == wanted:
            return source
    return None


def schedule_page(source: str, ref: Any) -> str:
    if source == GDQ and not is_short(ref):
        return SCHEDULE_PAGE.format(ref=ref)
    if source in TRACKER_BASES and str(ref or "").isdigit():
        return event_url(ref, source)
    if source == HORARO and ref:
        return HORARO_PAGE.format(ref=ref)
    if source == OENGUS and ref:
        marathon, slug = oengus_ref(ref)
        page = OENGUS_PAGE.format(id=marathon)
        return f"{page}/{slug}" if slug else page
    return ""


def oengus_ref(ref: Any) -> tuple[str, str | None]:
    """`ss4c8` → (ss4c8, None); `ss4c8/2` → (ss4c8, 2) — a slug only when staff pasted one."""
    marathon, _, slug = str(ref or "").partition("/")
    return (marathon, slug or None)


def duration_seconds(text: Any) -> int | None:
    """`PT1H30M` → 5400; Oengus writes every estimate and setup this way."""
    found = ISO_DURATION.match(str(text or "").strip())
    if not found or not any(found.groups()):
        return None
    days, hours, minutes, seconds = (float(one or 0) for one in found.groups())
    return int(round(days * 86400 + hours * 3600 + minutes * 60 + seconds))


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


def unlinked(text: Any) -> str:
    """`[Name](url)` → `Name`, the way horaro.net writes a linked cell."""
    return _text(MARKDOWN_LINK.sub(lambda found: found.group(1), str(text or "")))


def _column(columns: list[str], wanted: tuple[str, ...]) -> int | None:
    lowered = [" ".join(str(one or "").split()).lower() for one in columns]
    for name in wanted:
        if name in lowered:
            return lowered.index(name)
    return None


def _cell_of(data: Any, index: int | None) -> Any:
    if index is None or not isinstance(data, list) or index >= len(data):
        return None
    return data[index]


def horaro_people(cell: Any) -> tuple[Person, ...]:
    """A player cell split on `,` `&` `vs` `and`; `[name](twitch link)` gives a login."""
    found: list[Person] = []
    for piece in PLAYER_SPLIT.split(str(cell or "").strip()):
        link = MARKDOWN_LINK.fullmatch(piece.strip())
        name = _text(link.group(1) if link else piece)
        if not name:
            continue
        found.append(Person(name, twitch_login_from_url(link.group(2)) if link else None, RUNNER))
    return tuple(found)


def _moment(stamp: Any, text: Any) -> datetime | None:
    if isinstance(stamp, int | float) and not isinstance(stamp, bool):
        return datetime.fromtimestamp(stamp, UTC)
    found = utc_iso(text)
    return datetime.fromisoformat(found) if found else None


def horaro_schedule_of(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    for key in ("schedule", "data"):
        if isinstance(payload.get(key), dict):
            return payload[key]
    return payload


def parse_horaro(payload: Any) -> list[Run]:
    """One horaro.net schedule into runs: the columns are found by name, not by position."""
    schedule = horaro_schedule_of(payload)
    columns = [str(one or "") for one in schedule.get("columns") or ()]
    game_at = _column(columns, GAME_COLUMNS)
    players_at = _column(columns, PLAYER_COLUMNS)
    category_at = _column(columns, CATEGORY_COLUMNS)
    id_at = _column(columns, ID_COLUMNS)
    found: list[Run] = []
    for index, item in enumerate(schedule.get("items") or ()):
        if not isinstance(item, dict):
            continue
        data = item.get("data")
        game = unlinked(_cell_of(data, game_at))
        if not game:
            continue
        starts = _moment(item.get("scheduled_t"), item.get("scheduled"))
        length = item.get("length_t")
        seconds = int(length) if isinstance(length, int) and length >= 0 else None
        ends = starts + timedelta(seconds=seconds) if starts and seconds is not None else None
        given_id = _text(_cell_of(data, id_at))
        found.append(
            Run(
                external_id=given_id or f"#{index}",
                order=index + 1,
                game=game,
                display_name=game,
                category=unlinked(_cell_of(data, category_at)),
                starts_at=starts.isoformat() if starts else None,
                ends_at=ends.isoformat() if ends else None,
                run_seconds=seconds,
                people=horaro_people(_cell_of(data, players_at)),
            )
        )
    return found


def oengus_people(runners: Any) -> tuple[Person, ...]:
    """One runner each; the TWITCH connection gives the login, none leaves the name alone."""
    found: list[Person] = []
    for runner in runners or ():
        if not isinstance(runner, dict):
            continue
        profile = runner.get("profile") if isinstance(runner.get("profile"), dict) else {}
        name = _text(runner.get("runnerName")) or _text(profile.get("displayName"))
        name = name or _text(profile.get("username"))
        if not name:
            continue
        login = None
        for link in profile.get("connections") or ():
            if isinstance(link, dict) and str(link.get("platform") or "").upper() == OENGUS_TWITCH:
                login = _text(link.get("username")).lower() or None
                break
        found.append(Person(name, login, RUNNER))
    return tuple(found)


def parse_oengus(payload: Any) -> list[Run]:
    """One Oengus schedule's lines into runs; a setup block is not a run. The end takes the
    setup after the run, as the tracker's end does."""
    lines = payload.get("lines") if isinstance(payload, dict) else payload
    found: list[Run] = []
    for index, line in enumerate(lines or ()):
        if not isinstance(line, dict) or line.get("setupBlock"):
            continue
        game = _text(line.get("game"))
        if not game:
            continue
        starts = _moment(None, line.get("date"))
        seconds = duration_seconds(line.get("estimate"))
        setup = duration_seconds(line.get("setupTime")) or 0
        ends = None
        if starts is not None and seconds is not None:
            ends = starts + timedelta(seconds=seconds + setup)
        position = line.get("position")
        found.append(
            Run(
                external_id=str(line["id"]) if line.get("id") is not None else f"#{index}",
                order=int(position) + 1 if isinstance(position, int) else index + 1,
                game=game,
                display_name=game,
                category=_text(line.get("category")),
                starts_at=starts.isoformat() if starts else None,
                ends_at=ends.isoformat() if ends else None,
                run_seconds=seconds,
                people=oengus_people(line.get("runners")),
            )
        )
    return found


def oengus_home(payload: Any) -> list[dict[str, Any]]:
    """`for-home`'s live, next and open lists as one list, each id once."""
    found: list[dict[str, Any]] = []
    taken: set[str] = set()
    for key in OENGUS_LISTS:
        rows = payload.get(key) if isinstance(payload, dict) else None
        for row in rows or ():
            if not isinstance(row, dict) or not OENGUS_ID.match(str(row.get("id") or "")):
                continue
            if str(row["id"]) in taken:
                continue
            taken.add(str(row["id"]))
            found.append(row)
    return found


def horaro_span(schedule: Any) -> tuple[str | None, str | None]:
    """A listed schedule's start and, from its last item, its end."""
    if not isinstance(schedule, dict):
        return (None, None)
    starts = _moment(schedule.get("start_t"), schedule.get("start"))
    ends = None
    for item in schedule.get("items") or ():
        if not isinstance(item, dict):
            continue
        at = _moment(item.get("scheduled_t"), item.get("scheduled"))
        length = item.get("length_t")
        if at is not None:
            end = at + timedelta(seconds=length if isinstance(length, int) else 0)
            ends = end if ends is None or end > ends else ends
    return (starts.isoformat() if starts else None, ends.isoformat() if ends else None)


def next_page(payload: Any) -> str | None:
    found = payload.get("next") if isinstance(payload, dict) else None
    return str(found) if found else None


def event_url(ref: Any, source: str = GDQ) -> str:
    return TRACKER_EVENT.format(base=TRACKER_BASES[source], ref=ref)


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
            raise ScheduleError(
                UNREACHABLE.format(site=_site_of_url(url), why=type(exc).__name__)
            ) from exc

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    async def _json(self, url: str, source: str = GDQ) -> tuple[int, Any]:
        status, body = await self._request(url)
        if status == 200 and not isinstance(body, dict):
            raise ScheduleError(NOT_JSON.format(site=site_of(source)))
        return (status, body)

    async def horaro(self, ref: str) -> dict[str, Any]:
        """One horaro.net schedule's JSON export; a missing one is refused in words."""
        status, body = await self._json(HORARO_JSON.format(ref=ref), HORARO)
        if status == 404:
            raise ScheduleError(NO_SUCH_EVENT.format(site=site_of(HORARO), ref=ref))
        if status != 200:
            raise ScheduleError(ANSWERED.format(site=site_of(HORARO), status=status))
        return horaro_schedule_of(body)

    async def horaro_schedules(self, slug: str) -> list[dict[str, Any]]:
        """Every schedule horaro.net lists for one event, oldest first."""
        if not HORARO_SLUG.match(str(slug or "")):
            raise ScheduleError(NO_SUCH_EVENT.format(site=site_of(HORARO), ref=str(slug)[:40]))
        status, body = await self._json(HORARO_SCHEDULES.format(slug=slug), HORARO)
        if status == 404:
            raise ScheduleError(NO_SUCH_EVENT.format(site=site_of(HORARO), ref=slug))
        if status != 200:
            raise ScheduleError(ANSWERED.format(site=site_of(HORARO), status=status))
        return [row for row in body.get("data") or () if isinstance(row, dict)]

    async def oengus_marathon(self, marathon: str) -> dict[str, Any]:
        """One Oengus marathon's v1 record: its name, dates and the Twitch channel it airs on."""
        site = site_of(OENGUS)
        if not OENGUS_ID.match(str(marathon or "")):
            raise ScheduleError(NO_SUCH_EVENT.format(site=site, ref=str(marathon)[:40]))
        status, body = await self._json(OENGUS_MARATHON.format(id=marathon), OENGUS)
        if status == 404:
            raise ScheduleError(NO_SUCH_EVENT.format(site=site, ref=marathon))
        if status != 200:
            raise ScheduleError(ANSWERED.format(site=site, status=status))
        return body

    async def oengus_home(self) -> list[dict[str, Any]]:
        """The marathons oengus.io's home lists: live, next and open for submissions."""
        status, body = await self._json(OENGUS_HOME, OENGUS)
        if status != 200:
            raise ScheduleError(ANSWERED.format(site=site_of(OENGUS), status=status))
        return oengus_home(body)

    async def oengus_runs(self, ref: str) -> list[Run]:
        """The pasted slug, else the first published schedule; none published yet reads like an
        unpublished tracker event."""
        site = site_of(OENGUS)
        marathon, wanted = oengus_ref(ref)
        if not OENGUS_ID.match(marathon) or (wanted and not OENGUS_ID.match(wanted)):
            raise ScheduleError(NO_SUCH_EVENT.format(site=site, ref=str(ref)[:40]))
        status, body = await self._json(OENGUS_SCHEDULES.format(id=marathon), OENGUS)
        if status == 404:
            raise ScheduleError(NO_SUCH_EVENT.format(site=site, ref=marathon))
        if status != 200:
            raise ScheduleError(ANSWERED.format(site=site, status=status))
        published = [
            str(row.get("slug"))
            for row in body.get("data") or ()
            if isinstance(row, dict) and row.get("published") and row.get("slug")
        ]
        slug = wanted if wanted in published else (published[0] if published else None)
        if slug is None:
            raise ScheduleError(NOT_PUBLISHED_OENGUS.format(site=site), unpublished=True)
        status, body = await self._json(OENGUS_LINES.format(id=marathon, slug=slug), OENGUS)
        if status == 404:
            raise ScheduleError(NOT_PUBLISHED_OENGUS.format(site=site), unpublished=True)
        if status != 200:
            raise ScheduleError(ANSWERED.format(site=site, status=status))
        return parse_oengus(body)

    async def resolve(self, source: str, ref: str) -> tuple[str, str]:
        """(the event id, its name) — a short such as `AGDQ2027` is looked up once here."""
        if source == HORARO:
            schedule = await self.horaro(ref)
            return (ref, _text(schedule.get("name")) or ref)
        if source == OENGUS:
            marathon, _slug = oengus_ref(ref)
            record = await self.oengus_marathon(marathon)
            return (ref, _text(record.get("name")) or marathon)
        if source not in TRACKER_BASES:
            raise ScheduleError(UNKNOWN_SOURCE.format(source=source))
        site = site_of(source)
        api = api_of(source)
        if ref == LATEST:
            listed = [row for row in await self.events(source) if row.get("id") is not None]
            if not listed:
                raise ScheduleError(NO_EVENT_YET.format(site=site))
            newest = listed[0]
            return (str(newest["id"]), _text(newest.get("name")) or str(newest["id"]))
        if is_short(ref):
            short = ref[len(SHORT_PREFIX) :]
            status, body = await self._json(SHORT_URL.format(api=api, short=short), source)
            if status != 200:
                raise ScheduleError(ANSWERED.format(site=site, status=status))
            event = event_from(body)
            if event is None:
                raise ScheduleError(NO_SUCH_EVENT.format(site=site, ref=short))
            return (str(event["id"]), _text(event.get("name")) or short)
        status, body = await self._json(EVENT_URL.format(api=api, ref=ref), source)
        if status == 404:
            raise ScheduleError(NO_SUCH_EVENT.format(site=site, ref=ref))
        if status != 200:
            raise ScheduleError(ANSWERED.format(site=site, status=status))
        return (str(body.get("id") or ref), _text(body.get("name")) or str(ref))

    async def events(self, source: str = GDQ) -> list[dict[str, Any]]:
        """Every event the tracker lists, newest first; one page today, `next` followed if not."""
        if source not in TRACKER_BASES:
            raise ScheduleError(UNKNOWN_SOURCE.format(source=source))
        url: str | None = EVENTS_URL.format(api=api_of(source))
        found: list[dict[str, Any]] = []
        pages = 0
        while url and pages < PAGES_MAX:
            status, body = await self._json(url, source)
            if status != 200:
                raise ScheduleError(ANSWERED.format(site=site_of(source), status=status))
            found.extend(row for row in body.get("results") or () if isinstance(row, dict))
            url = next_page(body)
            pages += 1
        return found

    async def runs(self, source: str, ref: str) -> list[Run]:
        if source == HORARO:
            return parse_horaro(await self.horaro(ref))
        if source == OENGUS:
            return await self.oengus_runs(ref)
        if source not in TRACKER_BASES:
            raise ScheduleError(UNKNOWN_SOURCE.format(source=source))
        site = site_of(source)
        url: str | None = RUNS_URL.format(api=api_of(source), ref=ref)
        found: list[Run] = []
        pages = 0
        while url and pages < PAGES_MAX:
            status, body = await self._json(url, source)
            if status == 404:
                raise ScheduleError(NOT_PUBLISHED_AT.format(site=site), unpublished=True)
            if status != 200:
                raise ScheduleError(ANSWERED.format(site=site, status=status))
            found.extend(parse_gdq(body))
            url = next_page(body)
            pages += 1
        if url:
            log.warning("marathon: %s", TOO_MANY_PAGES.format(pages=PAGES_MAX))
        return found


def _site_of_url(url: str) -> str:
    for source, base in (*TRACKER_BASES.items(), (HORARO, HORARO_SITE), (OENGUS, OENGUS_SITE)):
        if url.startswith(base):
            return site_of(source)
    parts = url.split("/")
    return parts[2] if len(parts) > 2 else "the schedule site"


__all__ = [
    "COMMENTATOR",
    "GDQ",
    "HORARO",
    "HOST",
    "OENGUS",
    "PARTS",
    "RPGLB",
    "RUNNER",
    "SOURCES",
    "SOURCE_WORDS",
    "TRACKER_BASES",
    "TRACKER_SOURCES",
    "Person",
    "Run",
    "ScheduleClient",
    "ScheduleError",
    "event_from",
    "event_url",
    "horaro_people",
    "horaro_schedule_of",
    "horaro_span",
    "api_of",
    "duration_seconds",
    "is_short",
    "next_gdq_event",
    "next_page",
    "oengus_home",
    "oengus_people",
    "oengus_ref",
    "parse_oengus",
    "parse_gdq",
    "parse_horaro",
    "read_url",
    "schedule_page",
    "seconds_of",
    "site_of",
    "tracker_source",
    "unlinked",
    "utc_iso",
]
