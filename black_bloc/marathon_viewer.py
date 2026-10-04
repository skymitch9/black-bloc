from __future__ import annotations

import asyncio
import html as html_text
import json
import logging
import re
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from urllib.parse import parse_qs, urljoin, urlsplit

from .doc_import import CONTENT_HOST_TAIL, DOCS_HOST, REDIRECTS, DocImportError, hop_allowed
from .marathon import runner_key
from .marathon_hotfix import CSV_URL, EASTERN, MAX_BYTES, SECONDS, Get, fetch
from .marathon_sources import HOST, Run, ScheduleError
from .settings_store import MARATHON_HOTFIX_VIEWER_URL
from .spotlight import clean_login
from .timezones import zone

log = logging.getLogger(__name__)

PAGE = MARATHON_HOTFIX_VIEWER_URL
SITE = "the Hotfix schedule viewer"
FROM_VIEWER = "viewer"
SCRIPT_HOST = "script.google.com"
SHORT_HOST = "gdq.gg"
FIXED_HOSTS = (SCRIPT_HOST, SHORT_HOST, DOCS_HOST)
TAILS = (CONTENT_HOST_TAIL,)
LINK_HOSTS = (SHORT_HOST, DOCS_HOST)
TOTAL_SECONDS = 90
CACHE_SECONDS = 300
SHORT_HOPS = 3
SCRIPTS_MAX = 3
HOSTS_MAX = 200
LINKS_MAX = 8
ROWS_MAX = 2000
NAME_MAX = 60
LABEL_MAX = 100
SERIAL_HOURS = 5
START_PREFIX = "Show Start"

SCRIPT_TAG = re.compile(r"<script\b[^>]{0,300}?\bsrc\s*=\s*[\"']([^\"'<>\s]{1,300})[\"']", re.I)
DATA_URL = re.compile(
    r"DATA_URL\s*=\s*[\"'](https://script\.google\.com/macros/s/[A-Za-z0-9_-]{20,200}/exec)[\"']"
)
HOST_TABLE = re.compile(r"hostLinks\s*=\s*\{([^{}]{0,20000})\}")
PAIR = re.compile(r"[\"']([^\"'\n]{1,60})[\"']\s*:\s*[\"']([^\"'\n]{1,200})[\"']")
ANCHOR = re.compile(r"<a\b([^>]{0,600})>(.{0,400}?)</a\s*>", re.I | re.S)
HREF = re.compile(r"\bhref\s*=\s*[\"']([^\"'<>\s]{1,300})[\"']", re.I)
TAG = re.compile(r"<[^>]{0,300}>")
PUBLISHED = re.compile(
    r"^https://docs\.google\.com/spreadsheets/(?:u/\d{1,3}/)?d/e/([A-Za-z0-9_-]{20,200})/"
    r"pub(?:html)?(?:\?([^#\s]{0,300}))?(?:#.*)?$"
)

SHEET_PAGE = "https://docs.google.com/spreadsheets/d/e/{key}/pubhtml"
NO_DATA = "the page's script names no schedule feed"
NOT_ROWS = "the viewer's feed did not answer a list of rows"
NOT_A_SHEET = "goes to {host}, which is not a published Google Sheet"
NO_REDIRECT = "answered {status} instead of sending on to a sheet"
READ_FOUND = (
    "Read the viewer: {rows} schedule row(s), {hosts} host(s) with Twitch names, {events} event "
    "schedule(s)."
)
NO_ROWS = "no"
ROWS_TROUBLE = "Its schedule feed could not be read ({why})."
EVENT_READ = "**{label}** has its own schedule sheet."
EVENT_SKIPPED = "**{label}** was not read — it {why}."
VIEWER_OFF = (
    "The viewer link is blank, so this source is off and nothing was read. The GDQ sheet is "
    "read alone."
)
VIEWER_UNREADABLE = (
    "The Hotfix schedule viewer could not be read just now ({why}). Nothing was changed — the "
    "GDQ sheet is still read, and any earlier copy of the viewer is kept."
)
NOT_HOTFIX = "**{name}** does not read the GDQ Hotfix schedule, so it has no viewer to read."


@dataclass(frozen=True)
class EventLink:
    label: str
    href: str


@dataclass(frozen=True)
class EventSheet:
    label: str
    href: str
    page: str
    csv_url: str
    text: str


@dataclass(frozen=True)
class FeedRow:
    show: str
    day: date | None
    start: time | None
    host: str
    game: str
    category: str
    seconds: int | None
    runners: str
    stream: str


@dataclass(frozen=True)
class Viewer:
    page: str
    data_url: str | None = None
    hosts: dict[str, str] = field(default_factory=dict)
    links: tuple[EventLink, ...] = ()
    sheets: tuple[EventSheet, ...] = ()
    skipped: tuple[tuple[str, str], ...] = ()
    rows: int | None = None
    rows_trouble: str | None = None


@dataclass
class ViewerCache:
    viewer: Viewer | None = None
    read_at: datetime | None = None
    trouble: str | None = None
    failed_at: datetime | None = None
    failed_page: str | None = None
    said: Any = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def keep(self, viewer: Viewer, now: datetime) -> None:
        self.viewer, self.read_at = viewer, now
        self.trouble = self.failed_at = self.failed_page = self.said = None

    def failed(self, page: str, why: str, now: datetime) -> None:
        self.trouble, self.failed_at, self.failed_page = why, now, page

    def fresh(self, page: str, now: datetime, seconds: int = CACHE_SECONDS) -> bool:
        if self.viewer is None or self.read_at is None or self.viewer.page != page:
            return False
        return now - self.read_at < timedelta(seconds=seconds)

    def waiting(self, page: str, now: datetime, seconds: int = CACHE_SECONDS) -> bool:
        """A read of this page failed a moment ago, so it is not asked again yet."""
        if self.failed_at is None or self.failed_page != page:
            return False
        return now - self.failed_at < timedelta(seconds=seconds)

    def copy_for(self, page: str) -> Viewer | None:
        return self.viewer if self.viewer is not None and self.viewer.page == page else None


def cache_of(owner: Any) -> ViewerCache:
    found = getattr(owner, "viewer_cache", None)
    if not isinstance(found, ViewerCache):
        found = ViewerCache()
        owner.viewer_cache = found
    return found


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def page_host(page: Any) -> str:
    try:
        return (urlsplit(str(page or "")).hostname or "").lower()
    except ValueError:
        return ""


def allow_for(page: Any) -> Any:
    """The hop check for one viewer page: its own host, Google's script, short-link and sheet
    hosts, and Google's content hosts — nothing else."""
    own = page_host(page)
    hosts = (*((own,) if own else ()), *FIXED_HOSTS)

    def allowed(url: Any) -> bool:
        return hop_allowed(str(url or ""), hosts, TAILS)

    return allowed


def script_urls(page_html: Any, page: str) -> list[str]:
    """The page's own scripts: same host only, in page order."""
    own = page_host(page)
    found: list[str] = []
    for src in SCRIPT_TAG.findall(str(page_html or "")):
        url = urljoin(page, html_text.unescape(src))
        if page_host(url) == own and url.startswith("https://") and url not in found:
            found.append(url)
        if len(found) >= SCRIPTS_MAX:
            break
    return found


def data_url_of(script: Any) -> str | None:
    found = DATA_URL.search(str(script or ""))
    return found.group(1) if found else None


def hosts_of(script: Any) -> dict[str, str]:
    """The script's host table: a host's name (as `runner_key` folds it) → their Twitch login."""
    table = HOST_TABLE.search(str(script or ""))
    found: dict[str, str] = {}
    if table is None:
        return found
    for name, link in PAIR.findall(table.group(1)):
        key = runner_key(name)[:NAME_MAX]
        login = clean_login(link) if "twitch.tv/" in link.lower() else None
        if key and login and key not in found:
            found[key] = login
        if len(found) >= HOSTS_MAX:
            break
    return found


def _https(url: str) -> str:
    return "https://" + url[len("http://") :] if url.lower().startswith("http://") else url


def event_links(page_html: Any) -> list[EventLink]:
    """The page's links to an event's own schedule: a gdq.gg short link or a Google Sheet."""
    found: list[EventLink] = []
    for attrs, inner in ANCHOR.findall(str(page_html or "")):
        href = HREF.search(attrs)
        if href is None:
            continue
        url = _https(html_text.unescape(href.group(1)))
        if not url.startswith("https://") or page_host(url) not in LINK_HOSTS:
            continue
        label = _text(html_text.unescape(TAG.sub(" ", inner)))[:LABEL_MAX]
        if url not in {one.href for one in found}:
            found.append(EventLink(label or url[:LABEL_MAX], url))
        if len(found) >= LINKS_MAX:
            break
    return found


def sheet_of(url: Any) -> tuple[str, str] | None:
    """(the published sheet's page, its CSV) for a published Google Sheet link, else None."""
    found = PUBLISHED.match(str(url or "").strip())
    if found is None:
        return None
    query = parse_qs(html_text.unescape(found.group(2) or ""))
    gid = next((one for one in query.get("gid", []) if one.isdigit()), None)
    key = found.group(1)
    page = SHEET_PAGE.format(key=key) + (f"?gid={gid}" if gid else "")
    return (page, CSV_URL.format(key=key, gid=f"gid={gid}&" if gid else ""))


def _stamp(raw: Any) -> datetime | None:
    try:
        at = datetime.fromisoformat(str(raw or "").strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return at if at.tzinfo is not None else at.replace(tzinfo=UTC)


def serial_day(raw: Any) -> date | None:
    """`2026-10-03T04:00:00.000Z` (midnight Eastern, said in UTC) → 3 October."""
    at = _stamp(raw)
    eastern = zone(EASTERN)
    if at is None or eastern is None:
        return None
    return at.astimezone(eastern).date()


def serial_clock(raw: Any) -> time | None:
    """A Sheets time-of-day serial: always written five hours ahead, whatever the season."""
    at = _stamp(raw)
    if at is None:
        return None
    moved = at.astimezone(UTC) - timedelta(hours=SERIAL_HOURS)
    return time(moved.hour, moved.minute)


def serial_seconds(raw: Any) -> int | None:
    """A Sheets duration serial: the same five hours taken off, read as a length."""
    at = _stamp(raw)
    if at is None:
        return None
    moved = at.astimezone(UTC) - timedelta(hours=SERIAL_HOURS)
    return moved.hour * 3600 + moved.minute * 60 + moved.second


def feed_rows(payload: Any) -> list[FeedRow]:
    """The viewer feed's rows; anything that is not a row with a show and a game is left out."""
    if not isinstance(payload, list):
        raise ScheduleError(NOT_ROWS)
    found: list[FeedRow] = []
    for one in payload[:ROWS_MAX]:
        if not isinstance(one, dict):
            continue
        start = next((one[key] for key in one if str(key).startswith(START_PREFIX)), None)
        show, game = _text(one.get("Show"))[:NAME_MAX], _text(one.get("Game"))[:200]
        if not show or not game:
            continue
        found.append(
            FeedRow(
                show=show,
                day=serial_day(one.get("Show Date")),
                start=serial_clock(start),
                host=_text(one.get("Host"))[:200],
                game=game,
                category=_text(one.get("Category"))[:200],
                seconds=serial_seconds(one.get("Estimate")),
                runners=_text(one.get("Runners"))[:300],
                stream=_text(one.get("Runner Stream"))[:300],
            )
        )
    return found


def starts_at(row: FeedRow) -> datetime | None:
    eastern = zone(EASTERN)
    if row.day is None or row.start is None or eastern is None:
        return None
    return datetime.combine(row.day, row.start, eastern)


async def _resolve(get: Get, agent: str, link: EventLink, allow: Any) -> tuple[str, str] | str:
    """A link's published sheet, found from the Location header alone; a target that is not a
    sheet is never fetched."""
    url = link.href
    for _ in range(SHORT_HOPS):
        direct = sheet_of(url)
        if direct is not None:
            return direct
        if page_host(url) != SHORT_HOST or not allow(url):
            return NOT_A_SHEET.format(host=(page_host(url) or "?")[:60])
        try:
            hop = await get(url, seconds=SECONDS, limit=MAX_BYTES, agent=agent)
        except DocImportError as exc:
            return str(exc.code)[:80]
        if hop.status not in REDIRECTS or not hop.location:
            return NO_REDIRECT.format(status=hop.status)
        url = _https(urljoin(url, str(hop.location)[:2000]))
    return sheet_of(url) or NOT_A_SHEET.format(host=(page_host(url) or "?")[:60])


async def _read(get: Get, agent: str, page: str, with_rows: bool) -> Viewer:
    allow = allow_for(page)
    page_html = await fetch(get, page, agent, allow=allow, site=SITE)
    script = ""
    for url in script_urls(page_html, page):
        try:
            script += "\n" + await fetch(get, url, agent, allow=allow, site=SITE)
        except ScheduleError as exc:
            log.info("marathon: a viewer script could not be read (%s)", exc)
    links = event_links(page_html)
    sheets: list[EventSheet] = []
    skipped: list[tuple[str, str]] = []
    for link in links:
        found = await _resolve(get, agent, link, allow)
        if isinstance(found, str):
            skipped.append((link.label, found))
            continue
        try:
            text = await fetch(get, found[1], agent, allow=allow, site=SITE)
        except ScheduleError as exc:
            skipped.append((link.label, str(exc)[:200]))
            continue
        sheets.append(EventSheet(link.label, link.href, found[0], found[1], text))
    data_url = data_url_of(script)
    rows, trouble = None, None
    if with_rows:
        try:
            rows = len(await read_rows(get, agent, page, data_url))
        except ScheduleError as exc:
            trouble = str(exc)[:200]
    return Viewer(
        page=page,
        data_url=data_url,
        hosts=hosts_of(script),
        links=tuple(links),
        sheets=tuple(sheets),
        skipped=tuple(skipped),
        rows=rows,
        rows_trouble=trouble,
    )


async def read_rows(get: Get, agent: str, page: str, data_url: Any) -> list[FeedRow]:
    if not data_url:
        raise ScheduleError(NO_DATA)
    text = await fetch(get, str(data_url), agent, allow=allow_for(page), site=SITE)
    try:
        return feed_rows(json.loads(text))
    except ValueError as exc:
        raise ScheduleError(NOT_ROWS) from exc


async def read_viewer(get: Get, agent: str, page: str, *, with_rows: bool = False) -> Viewer:
    """The viewer page, its script's host table and feed link, and each event sheet it links."""
    try:
        async with asyncio.timeout(TOTAL_SECONDS):
            return await _read(get, agent, str(page), with_rows)
    except TimeoutError as exc:
        raise ScheduleError(f"{SITE} could not be reached (timeout)") from exc


def with_host_logins(runs: Any, hosts: dict[str, str]) -> tuple[list[Run], dict[str, str]]:
    """Each host the schedule gave no Twitch channel takes the viewer table's; (the runs,
    who was filled)."""
    filled: dict[str, str] = {}
    found: list[Run] = []
    for run in runs or ():
        people = []
        for person in run.people:
            login = hosts.get(runner_key(person.name)) if person.part == HOST else None
            if login and not person.login:
                filled[person.name] = login
                person = replace(person, login=login, login_from=FROM_VIEWER)
            people.append(person)
        found.append(replace(run, people=tuple(people)))
    return (found, filled)


def summary(viewer: Viewer) -> dict[str, Any]:
    return {
        "page": viewer.page,
        "rows": viewer.rows,
        "rows_trouble": viewer.rows_trouble,
        "feed": bool(viewer.data_url),
        "hosts": len(viewer.hosts),
        "events": [
            {"label": one.label, "href": one.href, "sheet_url": one.page} for one in viewer.sheets
        ],
        "skipped": [{"label": label, "why": why} for label, why in viewer.skipped],
    }


__all__ = [
    "PAGE",
    "SITE",
    "FROM_VIEWER",
    "EventLink",
    "EventSheet",
    "FeedRow",
    "Viewer",
    "ViewerCache",
    "allow_for",
    "cache_of",
    "data_url_of",
    "event_links",
    "feed_rows",
    "hosts_of",
    "page_host",
    "read_rows",
    "read_viewer",
    "script_urls",
    "serial_clock",
    "serial_day",
    "serial_seconds",
    "sheet_of",
    "starts_at",
    "summary",
    "with_host_logins",
]
