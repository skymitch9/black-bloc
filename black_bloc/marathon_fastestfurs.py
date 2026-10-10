from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Any

from .marathon_feeds import Candidate
from .marathon_sources import (
    ANSWERED,
    FASTESTFURS,
    HOST,
    NO_SUCH_EVENT,
    NOT_JSON,
    PLAYER_SPLIT,
    RUNNER,
    Person,
    Run,
    ScheduleError,
    site_of,
    utc_iso,
)

Request = Callable[[str], Awaitable[tuple[int, Any]]]

SITE = "https://fastestfurs.com"
PAGE = SITE + "/schedule/{id}"
API = "https://cheetah.fastestfurs.com"
EVENTS = API + "/api/events"
SCHEDULE = API + "/api/public/schedules/event/{id}"
EVENT_ID = re.compile(r"^\d{1,9}$")
URL = re.compile(
    r"^https?://(?:(?:www\.)?fastestfurs\.com/schedule|cheetah\.fastestfurs\.com/api/public/"
    r"schedules/event)/(\d{1,9})/?(?:[?#].*)?$",
    re.IGNORECASE,
)
RUN_ITEM = "run"
DATE_ONLY = "T00:00:00"
NOT_PUBLISHED = "{site} has the event but has not published its schedule yet"


def read_ref(text: Any) -> str | None:
    """The event id out of a fastestfurs.com schedule page or its API link."""
    found = URL.match(str(text or "").strip())
    return found.group(1) if found else None


def schedule_page(ref: Any) -> str:
    return PAGE.format(id=ref) if EVENT_ID.match(str(ref or "")) else ""


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _minutes(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0


def people_of(item: dict[str, Any]) -> tuple[Person, ...]:
    """Runners from the plain-name `runners` string, then the item's hosts; never a login."""
    found: list[Person] = []
    run = item.get("runs") if isinstance(item.get("runs"), dict) else {}
    for piece in PLAYER_SPLIT.split(str(run.get("runners") or "").strip()):
        name = _text(piece)
        if name:
            found.append(Person(name, None, RUNNER))
    for one in item.get("scheduleItemHosts") or ():
        host = one.get("host") if isinstance(one, dict) else None
        name = _text(host.get("name")) if isinstance(host, dict) else ""
        if name:
            found.append(Person(name, None, HOST))
    return tuple(found)


def _order(item: dict[str, Any]) -> int:
    given = item.get("orderIndex")
    return given if isinstance(given, int) else 0


def _actual(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _slot(
    item: dict[str, Any], *, use_actuals: bool, includes_setup: bool
) -> tuple[int, int | None]:
    """(seconds the item holds the clock, its actual seconds when finished)."""
    planned = (_minutes(item.get("duration")) + _minutes(item.get("setupTime"))) * 60
    actual = _actual(item.get("actualDuration")) if use_actuals else None
    if actual is None:
        return (planned, None)
    setup = 0 if includes_setup else _minutes(item.get("setupTime")) * 60
    return (actual + setup, actual)


def parse_fastestfurs(
    payload: Any, *, actual_includes_setup: bool = True, use_actuals: bool = True
) -> list[Run]:
    """One public schedule into runs, timed by walking the items from `startDateTime`: a
    finished item by its `actualDuration`, the rest by `duration` + `setupTime`."""
    if not isinstance(payload, dict):
        return []
    at_text = utc_iso(payload.get("startDateTime"))
    at = datetime.fromisoformat(at_text) if at_text else None
    items = [one for one in payload.get("scheduleItems") or () if isinstance(one, dict)]
    items.sort(key=_order)
    found: list[Run] = []
    previous_done = False
    runs_done = True
    for index, item in enumerate(items):
        slot, actual = _slot(item, use_actuals=use_actuals, includes_setup=actual_includes_setup)
        timed = previous_done and runs_done
        starts = at
        if at is not None:
            at = at + timedelta(seconds=slot)
        is_run = item.get("itemType") == RUN_ITEM
        previous_done = actual is not None
        runs_done = runs_done and (previous_done or not is_run)
        run = item.get("runs")
        if not is_run or not isinstance(run, dict):
            continue
        game = _text(run.get("name"))
        if not game:
            continue
        seconds = _minutes(item.get("duration")) * 60
        given = run.get("id") if run.get("id") is not None else item.get("id")
        order = item.get("orderIndex")
        found.append(
            Run(
                external_id=str(given) if given is not None else f"#{index}",
                order=order + 1 if isinstance(order, int) else index + 1,
                game=game,
                display_name=game,
                category=_text(run.get("category")),
                starts_at=starts.isoformat() if starts else None,
                ends_at=at.isoformat() if starts and at else None,
                run_seconds=seconds or None,
                people=people_of(item),
                actual_seconds=actual,
                timed_by_actuals=timed,
            )
        )
    return found


def event_rows(payload: Any) -> list[dict[str, Any]]:
    """`/api/events` rows with an id that can go into a URL."""
    rows = payload if isinstance(payload, list) else ()
    return [row for row in rows if isinstance(row, dict) and EVENT_ID.match(str(row.get("id")))]


def event_span(row: Any) -> tuple[str | None, str | None]:
    """The first day at noon UTC and the midnight after the last day."""
    if not isinstance(row, dict):
        return (None, None)
    starts = _day(row.get("startDate"), hours=12)
    return (starts, _day(row.get("endDate") or row.get("startDate"), hours=24))


def _day(text: Any, *, hours: int) -> str | None:
    found = utc_iso(text)
    if found is None:
        return None
    moment = datetime.fromisoformat(found)
    if DATE_ONLY in found:
        moment = moment + timedelta(hours=hours)
    return moment.isoformat()


def candidates(events: Any, now: datetime, recent_days: int) -> list[Candidate]:
    """Every listed event ending ahead of now or within `recent_days`; all are the channel's."""
    edge = now - timedelta(days=max(0, int(recent_days)))
    found: list[Candidate] = []
    for row in event_rows(events):
        starts, ends = event_span(row)
        moment = ends or starts
        if moment is None or datetime.fromisoformat(moment) < edge:
            continue
        ref = str(row["id"])
        name = _text(row.get("name")) or _text(row.get("short")) or ref
        found.append(Candidate(ref, name[:100], starts, ends, schedule_page(ref)))
    found.sort(key=lambda one: (one.starts_at or "", one.ref))
    return found


async def read_events(request: Request) -> list[dict[str, Any]]:
    site = site_of(FASTESTFURS)
    status, body = await request(EVENTS)
    if status != 200:
        raise ScheduleError(ANSWERED.format(site=site, status=status))
    if not isinstance(body, list):
        raise ScheduleError(NOT_JSON.format(site=site))
    return event_rows(body)


async def resolve(request: Request, ref: str) -> tuple[str, str]:
    """(the event id, its name) from the events list — a schedule not out yet still resolves."""
    site = site_of(FASTESTFURS)
    if not EVENT_ID.match(str(ref or "")):
        raise ScheduleError(NO_SUCH_EVENT.format(site=site, ref=str(ref)[:40]))
    for row in await read_events(request):
        if str(row["id"]) == str(ref):
            return (str(ref), _text(row.get("name")) or str(ref))
    raise ScheduleError(NO_SUCH_EVENT.format(site=site, ref=ref))


async def read_runs(request: Request, ref: str, *, actual_includes_setup: bool = True) -> list[Run]:
    """A 404 or a schedule with no runs yet reads like an unpublished tracker event."""
    site = site_of(FASTESTFURS)
    if not EVENT_ID.match(str(ref or "")):
        raise ScheduleError(NO_SUCH_EVENT.format(site=site, ref=str(ref)[:40]))
    status, body = await request(SCHEDULE.format(id=ref))
    if status == 404:
        raise ScheduleError(NOT_PUBLISHED.format(site=site), unpublished=True)
    if status != 200:
        raise ScheduleError(ANSWERED.format(site=site, status=status))
    if not isinstance(body, dict):
        raise ScheduleError(NOT_JSON.format(site=site))
    runs = parse_fastestfurs(body, actual_includes_setup=actual_includes_setup)
    if not runs:
        raise ScheduleError(NOT_PUBLISHED.format(site=site), unpublished=True)
    return runs


__all__ = [
    "candidates",
    "event_rows",
    "event_span",
    "parse_fastestfurs",
    "people_of",
    "read_events",
    "read_ref",
    "read_runs",
    "resolve",
    "schedule_page",
]
