from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from .golive import parse_ts
from .marathon_feeds import SEEN_LIMIT, Candidate
from .marathon_sources import (
    ANSWERED,
    LADYARCADERS,
    LADYARCADERS_CALENDAR,
    NO_SUCH_EVENT,
    NOT_JSON,
    RUNNER,
    Person,
    Run,
    ScheduleError,
    schedule_page,
    seconds_of,
    site_of,
)
from .timezones import zone

FLOOR = 24
PROBE_AHEAD = 3
EMPTY_RETRY_CHECKS = 4
NUMBER = re.compile(r"^\d{1,6}$")
ORG_NAMES = ("lady arcaders",)
CALENDAR_MARK = "BEGIN:VCALENDAR"
TIME_PROPERTIES = ("DTSTART", "DTEND")
SHORT_TAG = re.compile(r"^\[([^\]]*)\]\s*")
ESTIMATE = re.compile(r"\s*Time Estimate:\s*([\d:]+)\s*$", re.IGNORECASE)
NAME_SUFFIX = re.compile(r"\s+Schedule$", re.IGNORECASE)
ICS_ESCAPES = {"\\": "\\", ",": ",", ";": ";", "n": "\n", "N": "\n"}

NOT_PUBLISHED = "{site} has no schedule published for event {ref} yet"
EVENT_WORD = "Lady Arcaders event {ref}"


def unfolded(text: Any) -> list[str]:
    """RFC 5545 lines: CRLF or LF, a line starting with a space or a tab continues the last."""
    found: list[str] = []
    for line in str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line[:1] in (" ", "\t") and found:
            found[-1] += line[1:]
        elif line:
            found.append(line)
    return found


def unescaped(value: str) -> str:
    out: list[str] = []
    index = 0
    while index < len(value):
        one = value[index]
        if one == "\\" and index + 1 < len(value) and value[index + 1] in ICS_ESCAPES:
            out.append(ICS_ESCAPES[value[index + 1]])
            index += 2
            continue
        out.append(one)
        index += 1
    return "".join(out)


def split_property(line: str) -> tuple[str, dict[str, str], str]:
    """`DTSTART;TZID=America/Toronto:20260903T120500` → (DTSTART, {TZID: …}, 20260903T120500)."""
    head, quoted, cut = "", False, None
    for index, one in enumerate(line):
        if one == '"':
            quoted = not quoted
        elif one == ":" and not quoted:
            cut = index
            break
    if cut is None:
        return ("", {}, "")
    head, value = line[:cut], line[cut + 1 :]
    name, *params = head.split(";")
    found: dict[str, str] = {}
    for param in params:
        key, _, given = param.partition("=")
        found[key.strip().upper()] = given.strip().strip('"')
    return (name.strip().upper(), found, value)


def ics_moment(value: str, params: dict[str, str], fallback_zone: Any = None) -> str | None:
    """A DATE-TIME (`Z`, TZID or floating) or a DATE, as a UTC ISO string."""
    text = value.strip()
    try:
        if params.get("VALUE", "").upper() == "DATE" or re.fullmatch(r"\d{8}", text):
            return datetime.strptime(text[:8], "%Y%m%d").replace(tzinfo=UTC).isoformat()
        if text.endswith(("Z", "z")):
            moment = datetime.strptime(text[:-1], "%Y%m%dT%H%M%S").replace(tzinfo=UTC)
            return moment.isoformat()
        moment = datetime.strptime(text, "%Y%m%dT%H%M%S")
    except ValueError:
        return None
    place = zone(params["TZID"]) if params.get("TZID") else None
    place = place or (zone(fallback_zone) if fallback_zone else None)
    return moment.replace(tzinfo=place or UTC).astimezone(UTC).isoformat()


def parse_ics(text: Any) -> list[dict[str, Any]]:
    """Every VEVENT as {PROPERTY: text}; DTSTART and DTEND are UTC ISO strings."""
    lines = unfolded(text)
    floating = None
    for line in lines:
        name, _params, value = split_property(line)
        if name == "X-WR-TIMEZONE":
            floating = value.strip()
            break
    events: list[dict[str, Any]] = []
    stack: list[str] = []
    current: dict[str, Any] = {}
    for line in lines:
        name, params, value = split_property(line)
        if name == "BEGIN":
            stack.append(value.strip().upper())
            if stack[-1] == "VEVENT":
                current = {}
            continue
        if name == "END":
            if stack and stack.pop() == "VEVENT":
                events.append(current)
            continue
        if not name or not stack or stack[-1] != "VEVENT":
            continue
        if name in TIME_PROPERTIES:
            current[name] = ics_moment(value, params, floating)
        else:
            current.setdefault(name, unescaped(value))
    return events


def calendar_name(text: Any) -> str:
    for line in unfolded(text):
        name, _params, value = split_property(line)
        if name == "X-WR-CALNAME":
            return NAME_SUFFIX.sub("", " ".join(unescaped(value).split()))
        if name == "BEGIN" and value.strip().upper() == "VEVENT":
            break
    return ""


def is_calendar(text: Any) -> bool:
    return CALENDAR_MARK in str(text or "")[:500].upper()


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def trailing_group(text: str) -> tuple[str, str] | None:
    """`Game (a, b)` → (`Game`, `a, b`) — the last balanced parenthesis group."""
    if not text.endswith(")"):
        return None
    depth = 0
    for index in range(len(text) - 1, -1, -1):
        if text[index] == ")":
            depth += 1
        elif text[index] == "(":
            depth -= 1
            if depth == 0:
                return (text[:index].strip(), text[index + 1 : -1].strip())
    return None


def performers(given: str) -> tuple[Person, ...]:
    found: list[Person] = []
    for piece in given.split(","):
        name = _clean(piece)
        if name and name.lower() not in ORG_NAMES:
            found.append(Person(name, None, RUNNER))
    return tuple(found)


def read_event(event: dict[str, Any]) -> tuple[str, str, str, int | None]:
    """(game, category, performers, estimate seconds) out of SUMMARY and DESCRIPTION."""
    summary = _clean(SHORT_TAG.sub("", _clean(event.get("SUMMARY"))))
    description = _clean(event.get("DESCRIPTION"))
    estimate = ESTIMATE.search(description)
    seconds = seconds_of(estimate.group(1)) if estimate else None
    description = ESTIMATE.sub("", description) if estimate else description
    split = trailing_group(summary)
    game, people = split if split else (summary, "")
    if not people and " by " in description:
        people = description.rsplit(" by ", 1)[1]
    category = ""
    tail = f" by {people}" if people else ""
    head = description[: -len(tail)] if tail and description.endswith(tail) else description
    group = trailing_group(head)
    if group and group[0] == game:
        category = group[1]
    return (game, _clean(category), people, seconds)


def parse_ladyarcaders(events: Any) -> list[Run]:
    """Each VEVENT one run, in time order; performers are names only (no Twitch login)."""
    rows = [one for one in events or () if isinstance(one, dict)]
    rows.sort(key=lambda one: one.get("DTSTART") or "")
    found: list[Run] = []
    for index, event in enumerate(rows):
        game, category, people, seconds = read_event(event)
        if not game:
            continue
        starts, ends = event.get("DTSTART"), event.get("DTEND")
        if seconds is None and parse_ts(starts) and parse_ts(ends):
            seconds = int((parse_ts(ends) - parse_ts(starts)).total_seconds())
        found.append(
            Run(
                external_id=_clean(event.get("UID")) or f"#{index}",
                order=index + 1,
                game=game,
                display_name=game,
                category=category,
                starts_at=starts,
                ends_at=ends,
                run_seconds=seconds,
                people=performers(people),
            )
        )
    return found


def calendar_url(ref: Any) -> str:
    return LADYARCADERS_CALENDAR.format(number=ref)


async def calendar_answer(client: Any, ref: Any) -> tuple[int, str]:
    if not NUMBER.match(str(ref or "")):
        raise ScheduleError(NO_SUCH_EVENT.format(site=site_of(LADYARCADERS), ref=str(ref)[:40]))
    return await client.text(calendar_url(ref))


async def read_calendar(client: Any, ref: Any) -> str:
    """The event's calendar text; "" when ladyarcaders.com answers with nothing yet."""
    site = site_of(LADYARCADERS)
    status, body = await calendar_answer(client, ref)
    if status == 404:
        raise ScheduleError(NO_SUCH_EVENT.format(site=site, ref=ref))
    if status != 200:
        raise ScheduleError(ANSWERED.format(site=site, status=status))
    if body.strip() and not is_calendar(body):
        raise ScheduleError(NOT_JSON.format(site=site))
    return body


async def calendar_runs(client: Any, ref: Any) -> list[Run]:
    """No VEVENT yet reads like an unpublished tracker event."""
    runs = parse_ladyarcaders(parse_ics(await read_calendar(client, ref)))
    if not runs:
        raise ScheduleError(
            NOT_PUBLISHED.format(site=site_of(LADYARCADERS), ref=ref), unpublished=True
        )
    return runs


async def calendar_resolve(client: Any, ref: Any) -> tuple[str, str]:
    body = await read_calendar(client, ref)
    events = parse_ics(body)
    if not events:
        raise ScheduleError(NOT_PUBLISHED.format(site=site_of(LADYARCADERS), ref=ref))
    return (str(ref), event_name(ref, body, events))


def event_name(ref: Any, body: str, events: list[dict[str, Any]]) -> str:
    """The calendar's X-WR-CALNAME without ` Schedule`, else the `[SHORT]` tag, else words."""
    named = calendar_name(body)
    if named:
        return named[:100]
    for event in events:
        tag = SHORT_TAG.match(_clean(event.get("SUMMARY")))
        if tag and tag.group(1).strip():
            return tag.group(1).strip()[:100]
    return EVENT_WORD.format(ref=ref)


def number_of(ref: Any) -> int | None:
    text = str(ref or "").strip()
    return int(text) if NUMBER.match(text) else None


def found_records(seen: Any) -> list[dict[str, Any]]:
    return [one for one in seen or () if isinstance(one, dict) and not one.get("empty_at")]


def highest_known(refs: Any, seen: Any) -> int:
    """The highest event number on the list, removed by staff or remembered as found."""
    numbers = [number_of(one) for one in refs or ()]
    numbers += [number_of(one.get("ref")) for one in found_records(seen)]
    return max([FLOOR, *(one for one in numbers if one is not None)])


def retry_gap(hours: Any) -> timedelta:
    return timedelta(hours=max(1, int(hours)) * EMPTY_RETRY_CHECKS)


def to_probe(refs: Any, seen: Any, now: datetime, hours: Any) -> list[int]:
    """The next PROBE_AHEAD numbers above the highest known, an empty one only after the gap."""
    top = highest_known(refs, seen)
    empty = {
        str(one.get("ref")): parse_ts(one.get("empty_at"))
        for one in seen or ()
        if isinstance(one, dict) and one.get("empty_at")
    }
    gap = retry_gap(hours)
    found: list[int] = []
    for number in range(top + 1, top + 1 + PROBE_AHEAD):
        asked = empty.get(str(number))
        if asked is None or now - asked >= gap:
            found.append(number)
    return found


def found_record(ref: Any, body: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    runs = parse_ladyarcaders(events)
    starts = [one.starts_at for one in runs if one.starts_at]
    ends = [one.ends_at or one.starts_at for one in runs if one.ends_at or one.starts_at]
    return {
        "ref": str(ref),
        "name": event_name(ref, body, events),
        "starts_at": min(starts) if starts else None,
        "ends_at": max(ends) if ends else None,
    }


def empty_record(ref: Any, now: datetime) -> dict[str, Any]:
    return {"ref": str(ref), "empty_at": now.isoformat()}


async def probe(client: Any, numbers: list[int], now: datetime) -> list[dict[str, Any]]:
    """One calendar read per number: VEVENTs are found, anything else empty; a 404 stops."""
    read: list[dict[str, Any]] = []
    for number in numbers:
        status, body = await calendar_answer(client, number)
        if status == 404:
            break
        if status != 200:
            raise ScheduleError(ANSWERED.format(site=site_of(LADYARCADERS), status=status))
        events = parse_ics(body) if is_calendar(body) else []
        read.append(found_record(number, body, events) if events else empty_record(number, now))
    return read


def merged(seen: Any, read: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The memory with this probe's answers replacing the same numbers, capped at SEEN_LIMIT."""
    fresh = {one["ref"] for one in read}
    kept = [one for one in seen or () if isinstance(one, dict) and one.get("ref") not in fresh]
    return [*kept, *read][-SEEN_LIMIT:]


def candidates(seen: Any, now: datetime, recent_days: int) -> list[Candidate]:
    """Every remembered event that ends ahead of now (or ended within `recent_days`)."""
    since = now - timedelta(days=max(0, int(recent_days)))
    found: list[Candidate] = []
    for one in found_records(seen):
        ref = str(one.get("ref") or "")
        at = parse_ts(one.get("ends_at") or one.get("starts_at"))
        if number_of(ref) is None or at is None or at < since:
            continue
        name = _clean(one.get("name")) or EVENT_WORD.format(ref=ref)
        found.append(
            Candidate(
                ref,
                name[:100],
                one.get("starts_at"),
                one.get("ends_at"),
                schedule_page(LADYARCADERS, ref),
            )
        )
    found.sort(key=lambda one: (one.starts_at or "", int(one.ref)))
    return found


__all__ = [
    "EMPTY_RETRY_CHECKS",
    "FLOOR",
    "PROBE_AHEAD",
    "calendar_name",
    "calendar_resolve",
    "calendar_runs",
    "candidates",
    "highest_known",
    "merged",
    "parse_ics",
    "parse_ladyarcaders",
    "probe",
    "to_probe",
]
