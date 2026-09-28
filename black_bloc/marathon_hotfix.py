from __future__ import annotations

import asyncio
import csv
import html as html_text
import io
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

from .doc_import import CONTENT_HOST_TAIL, DOCS_HOST, REDIRECTS, DocImportError, hop_allowed
from .golive import twitch_login_from_url
from .marathon_feeds import Candidate
from .marathon_sources import (
    ANSWERED,
    GDQ_HOTFIX,
    HOST,
    RUNNER,
    UNREACHABLE,
    Person,
    Run,
    ScheduleError,
    seconds_of,
    site_of,
)
from .timezones import zone

log = logging.getLogger(__name__)

Get = Callable[..., Awaitable[Any]]

PAGE = "https://gamesdonequick.com/hotfix/schedule"
PAGE_HOSTS = ("gamesdonequick.com", "www.gamesdonequick.com")
HOSTS = (*PAGE_HOSTS, DOCS_HOST)
TAILS = (CONTENT_HOST_TAIL,)
URL = re.compile(
    r"^https?://(?:www\.)?gamesdonequick\.com/hotfix(?:/schedule)?/?(?:\?[^#]*)?(?:#(.*))?$",
    re.IGNORECASE,
)
SHEET = re.compile(
    r"https://docs\.google\.com/spreadsheets/d/e/([A-Za-z0-9_-]{20,200})/pubhtml"
    r"(\?[^\"'\s<>\\]*)?"
)
CSV_URL = "https://docs.google.com/spreadsheets/d/e/{key}/pub?{gid}single=true&output=csv"
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
EASTERN = "America/New_York"
MAX_BYTES = 1024 * 1024
MAX_HOPS = 5
SECONDS = 20
TOTAL_SECONDS = 45
BLOCK_GAP_DAYS = 1
SHOWS_DEFAULT = ("GDQueer",)
DATE_COLUMN = "show date"
START_PREFIX = "show start"
SHOW_COLUMN = "show"
HOST_COLUMN = "host"
GAME_COLUMN = "game"
CATEGORY_COLUMN = "category"
ESTIMATE_COLUMN = "estimate"
RUNNER_COLUMNS = ("runners", "runner(s)", "runner")
TIME_FORMATS = ("%I:%M:%S %p", "%I:%M %p", "%H:%M:%S", "%H:%M")

NO_SHEET = "the Hotfix page no longer embeds a schedule sheet"
NOT_SHEET = "the Hotfix sheet no longer has the Show Date, Show and Game columns"
TOO_BIG = "{site} answered with more than {limit} KB, so it was not read"
WENT_ELSEWHERE = "{site} sent Black Bloc to {host}, which it does not fetch"
TOO_MANY_HOPS = "{site} redirected more than {hops} times"
NAME_THE_SHOW = (
    "the Hotfix page carries several shows — add the show's name after a #, for example "
    f"{PAGE}#GDQueer"
)
NO_SUCH_SHOW = "the Hotfix sheet lists no {show} block ahead"
NOT_LISTED = "the Hotfix sheet does not list {show} on {day} any more"


@dataclass(frozen=True)
class Block:
    show: str
    key: str
    first: date
    last: date
    runs: tuple[Run, ...]

    @property
    def ref(self) -> str:
        return f"{self.key}/{self.first.isoformat()}"

    @property
    def starts_at(self) -> str | None:
        return self.runs[0].starts_at if self.runs else None

    @property
    def ends_at(self) -> str | None:
        ends = [one.ends_at or one.starts_at for one in self.runs if one.ends_at or one.starts_at]
        return max(ends) if ends else None


@dataclass(frozen=True)
class _Row:
    index: int
    show: str
    day: date
    start: time | None
    host: str
    game: str
    category: str
    seconds: int | None
    runners: tuple[str, ...]
    links: tuple[str, ...]


def show_key(name: Any) -> str:
    return "-".join(unquote(str(name or "")).lower().split())


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def ref_of(fragment: Any) -> str:
    """`GDQueer` → `gdqueer`; `gdqueer/2026-10-03` stays itself; blank stays blank."""
    given = unquote(str(fragment or "")).strip()
    show, _, day = given.rpartition("/")
    if show and ISO_DATE.match(day.strip()):
        return f"{show_key(show)}/{day.strip()}"
    return show_key(given)


def read_ref(text: Any) -> str | None:
    found = URL.match(str(text or "").strip())
    return ref_of(found.group(1)) if found else None


def page_of(ref: Any) -> str:
    return f"{PAGE}#{ref}" if ref else PAGE


def shows_of(given: Any) -> list[str]:
    """The settings key's list: comma-separated, trimmed, each show once."""
    found: list[str] = []
    for part in str(given or "").split(","):
        name = _text(part)
        if name and show_key(name) not in {show_key(one) for one in found}:
            found.append(name)
    return found


def _day(text: Any) -> date | None:
    try:
        return datetime.strptime(_text(text), "%m/%d/%Y").date()
    except ValueError:
        return None


def _clock(text: Any) -> time | None:
    given = _text(text).upper()
    for form in TIME_FORMATS:
        try:
            return datetime.strptime(given, form).time()
        except ValueError:
            continue
    return None


def _columns(header: list[list[str]]) -> dict[str, int]:
    found: dict[str, int] = {}
    for row in header:
        for index, cell in enumerate(row):
            name = _text(cell).lower()
            if name.startswith(START_PREFIX):
                name = START_PREFIX
            if name and name not in found:
                found[name] = index
    return found


def _cell(row: list[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return _text(row[index])


def _split(cell: str) -> tuple[str, ...]:
    return tuple(one for one in (_text(part) for part in cell.split(",")) if one)


def _rows(text: str) -> list[_Row]:
    table = list(csv.reader(io.StringIO(str(text or "").lstrip("﻿"))))
    first = next((i for i, row in enumerate(table) if row and _day(row[0])), len(table))
    names = _columns(table[:first])
    at = {name: names.get(name) for name in (DATE_COLUMN, SHOW_COLUMN, GAME_COLUMN)}
    if None in at.values():
        raise ScheduleError(NOT_SHEET)
    runners_at = next((names[one] for one in RUNNER_COLUMNS if one in names), None)
    links_at = runners_at + 1 if runners_at is not None else None
    found: list[_Row] = []
    kept = list(enumerate(table[first:]))
    starts: dict[tuple[str, date], time] = {}
    for _index, row in kept:
        day, clock = _day(_cell(row, at[DATE_COLUMN])), _clock(_cell(row, names.get(START_PREFIX)))
        if day is not None and clock is not None:
            starts.setdefault((show_key(_cell(row, at[SHOW_COLUMN])), day), clock)
    for index, row in kept:
        day = _day(_cell(row, at[DATE_COLUMN]))
        show, game = _cell(row, at[SHOW_COLUMN]), _cell(row, at[GAME_COLUMN])
        if day is None or not show or not game:
            continue
        found.append(
            _Row(
                index=index,
                show=show,
                day=day,
                start=starts.get((show_key(show), day)),
                host=_cell(row, names.get(HOST_COLUMN)),
                game=game,
                category=_cell(row, names.get(CATEGORY_COLUMN)),
                seconds=seconds_of(_cell(row, names.get(ESTIMATE_COLUMN))),
                runners=_split(_cell(row, runners_at)),
                links=_split(_cell(row, links_at)),
            )
        )
    return found


def _logins(runners: tuple[str, ...], links: tuple[str, ...]) -> list[str | None]:
    logins = [twitch_login_from_url(one) for one in links]
    if len(logins) == len(runners):
        return logins
    known = {str(one): one for one in logins if one}
    return [known.get(name.lower()) for name in runners]


def _people(row: _Row) -> tuple[Person, ...]:
    found = [
        Person(name, login, RUNNER)
        for name, login in zip(row.runners, _logins(row.runners, row.links), strict=True)
    ]
    for host in _split(row.host):
        if show_key(host) != show_key(row.show):
            found.append(Person(host, None, HOST))
    return tuple(found)


def _runs(rows: list[_Row]) -> tuple[Run, ...]:
    eastern = zone(EASTERN)
    found: list[Run] = []
    taken: dict[str, int] = {}
    cursor: datetime | None = None
    today: date | None = None
    for order, row in enumerate(rows, start=1):
        if row.day != today:
            today = row.day
            cursor = datetime.combine(row.day, row.start, eastern) if row.start else None
        starts = cursor
        ends = starts + timedelta(seconds=row.seconds or 0) if starts is not None else None
        cursor = ends
        base = f"{show_key(row.game)}/{show_key(row.category)}"[:120]
        taken[base] = taken.get(base, 0) + 1
        found.append(
            Run(
                external_id=base if taken[base] == 1 else f"{base}#{taken[base]}",
                order=order,
                game=row.game,
                display_name=row.game,
                category=row.category,
                starts_at=starts.astimezone(UTC).isoformat() if starts else None,
                ends_at=ends.astimezone(UTC).isoformat() if ends else None,
                run_seconds=row.seconds,
                people=_people(row),
            )
        )
    return tuple(found)


def blocks_of(text: str) -> list[Block]:
    """Every show's rows, split where two show dates are more than a day apart."""
    by_show: dict[str, list[_Row]] = {}
    for row in _rows(text):
        by_show.setdefault(show_key(row.show), []).append(row)
    found: list[Block] = []
    for key, rows in by_show.items():
        rows.sort(key=lambda one: (one.day, one.index))
        chunk: list[_Row] = []
        for row in rows:
            if chunk and (row.day - chunk[-1].day).days > BLOCK_GAP_DAYS:
                found.append(Block(chunk[0].show, key, chunk[0].day, chunk[-1].day, _runs(chunk)))
                chunk = []
            chunk.append(row)
        if chunk:
            found.append(Block(chunk[0].show, key, chunk[0].day, chunk[-1].day, _runs(chunk)))
    found.sort(key=lambda one: (one.first, one.key))
    return found


def parse_hotfix(text: str, shows: Any) -> list[Block]:
    """The blocks of the listed shows (case-insensitive exact names), each with its runs."""
    wanted = {show_key(one) for one in shows or ()}
    return [one for one in blocks_of(text) if one.key in wanted]


def block_for(blocks: list[Block], ref: Any, now: datetime) -> Block:
    """The block a marathon's ref names: its first date, else the block holding that date; a
    bare show name is the first block not over yet."""
    key, _, day = str(ref or "").partition("/")
    if not key:
        raise ScheduleError(NAME_THE_SHOW)
    mine = [one for one in blocks if one.key == key]
    if not day:
        ahead = [one for one in mine if _at(one.ends_at) is None or _at(one.ends_at) >= now]
        if not ahead:
            raise ScheduleError(NO_SUCH_SHOW.format(show=key))
        return ahead[0]
    wanted = date.fromisoformat(day)
    for one in mine:
        if one.first == wanted:
            return one
    for one in mine:
        if one.first <= wanted <= one.last:
            return one
    raise ScheduleError(NOT_LISTED.format(show=key, day=day), unpublished=True)


def _at(stamp: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(stamp)) if stamp else None
    except ValueError:
        return None


def candidates(
    blocks: list[Block], now: datetime, recent_days: int, taken: set[str]
) -> list[Candidate]:
    """Each listed block not over (by END) more than `recent_days` ago. A show's name alone,
    unless the sheet holds two of its blocks or a marathon already has that name."""
    per_show: dict[str, int] = {}
    for one in blocks:
        per_show[one.key] = per_show.get(one.key, 0) + 1
    edge = now - timedelta(days=max(0, int(recent_days)))
    found: list[Candidate] = []
    for one in blocks:
        ends = _at(one.ends_at or one.starts_at)
        if ends is None or ends < edge:
            continue
        name = one.show
        if per_show[one.key] > 1 or name.lower() in taken:
            name = f"{one.show} ({one.first.strftime('%b %Y')})"
        found.append(Candidate(one.ref, name[:100], one.starts_at, one.ends_at, page_of(one.ref)))
    return found


def sheet_url_of(page: str) -> str | None:
    """The pub CSV of the Google Sheet the Hotfix page embeds, keeping its tab (`gid`)."""
    text = html_text.unescape(str(page or "")).replace("\\u0026", "&").replace("\\/", "/")
    found = SHEET.search(text)
    if found is None:
        return None
    query = parse_qs(html_text.unescape(found.group(2) or "").lstrip("?"))
    gid = next((one for one in query.get("gid", []) if one.isdigit()), None)
    return CSV_URL.format(key=found.group(1), gid=f"gid={gid}&" if gid else "")


def allowed(url: Any) -> bool:
    return hop_allowed(str(url or ""), HOSTS, TAILS)


async def fetch(get: Get, url: str, agent: str) -> str:
    """One document, redirects followed by hand; every hop is checked BEFORE it is asked."""
    site = site_of(GDQ_HOTFIX)
    for _ in range(MAX_HOPS + 1):
        if not allowed(url):
            log.info("marathon: the Hotfix read was sent to %s; refused", url[:120])
            host = (urlsplit(url).hostname or "?") if "://" in url else "?"
            raise ScheduleError(WENT_ELSEWHERE.format(site=site, host=host[:60]))
        try:
            hop = await get(url, seconds=SECONDS, limit=MAX_BYTES, agent=agent)
        except DocImportError as exc:
            raise ScheduleError(UNREACHABLE.format(site=site, why=exc.code)) from exc
        if hop.status in REDIRECTS:
            if not hop.location:
                raise ScheduleError(ANSWERED.format(site=site, status=hop.status))
            url = urljoin(url, hop.location)
            continue
        if hop.status != 200:
            raise ScheduleError(ANSWERED.format(site=site, status=hop.status))
        if hop.too_big:
            raise ScheduleError(TOO_BIG.format(site=site, limit=MAX_BYTES // 1024))
        return bytes(hop.body).decode("utf-8", errors="replace")
    raise ScheduleError(TOO_MANY_HOPS.format(site=site, hops=MAX_HOPS))


async def read_sheet(
    get: Get, agent: str, page_url: str = PAGE, fallback: Any = None
) -> tuple[str, str]:
    """(the CSV, the CSV's URL): the page, its embedded sheet, the sheet. A page that cannot be
    read falls back to the last good CSV URL; a page without a sheet is a failure."""
    try:
        async with asyncio.timeout(TOTAL_SECONDS):
            return await _read_sheet(get, agent, page_url, fallback)
    except TimeoutError as exc:
        raise ScheduleError(UNREACHABLE.format(site=site_of(GDQ_HOTFIX), why="timeout")) from exc


async def _read_sheet(get: Get, agent: str, page_url: str, fallback: Any) -> tuple[str, str]:
    try:
        page = await fetch(get, page_url, agent)
    except ScheduleError as exc:
        if not fallback or not allowed(fallback):
            raise
        log.info("marathon: the Hotfix page could not be read (%s); the last good sheet", exc)
        return (_checked(await fetch(get, str(fallback), agent)), str(fallback))
    sheet = sheet_url_of(page)
    if sheet is None:
        raise ScheduleError(NO_SHEET)
    return (_checked(await fetch(get, sheet, agent)), sheet)


def _checked(text: str) -> str:
    _rows(text)
    return text


__all__ = [
    "PAGE",
    "SHOWS_DEFAULT",
    "Block",
    "allowed",
    "block_for",
    "blocks_of",
    "candidates",
    "fetch",
    "page_of",
    "parse_hotfix",
    "read_ref",
    "read_sheet",
    "ref_of",
    "sheet_url_of",
    "show_key",
    "shows_of",
]
