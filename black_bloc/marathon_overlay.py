from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from typing import Any

from . import marathon_signals as sig
from .golive import parse_ts
from .marathon import DROPPED, _cell, normalise, people_of
from .marathon_hotfix import EASTERN
from .marathon_sources import COMMENTATOR, HOST, Person, Run, ScheduleError, seconds_of
from .timezones import zone

COLUMN = "overlay"
STATE_COLUMN = "overlay_sheet"
WHEN = re.compile(
    r"^(\d{4})-(\d{1,2})-(\d{1,2})\s*(?:at|,|T)?\s*(\d{1,2}):(\d{2})(?::\d{2})?\s*([AaPp][Mm])?$"
)
SPLIT = re.compile(r"\s*(?:,|&)\s*")
DAY_ROLLS = timedelta(hours=6)
CHAIN_GAP = timedelta(hours=3)
FITS = 0.5
ROWS_MAX = 500
NAME_MAX = 60
NAMES_MAX = 10
CELL_MAX = 200
TITLE_FLOOR = 6
TIME_COLUMN = "time"
GAME_COLUMN = "game"
COLUMNS = {
    "estimate": "estimate",
    "category": "category",
    "runner": "runners",
    "host": "hosts",
    "commentator": "commentators",
}

NOT_A_SCHEDULE = "the event sheet has no Time and Game columns"
NO_LONGER_LINKED = "the viewer no longer links a schedule sheet that matches"
BY_TITLE = "title"
BY_ORDER = "order"


@dataclass(frozen=True)
class Slot:
    start: datetime
    seconds: int | None
    game: str
    category: str
    runners: tuple[str, ...] = ()
    hosts: tuple[str, ...] = ()
    commentators: tuple[str, ...] = ()


@dataclass(frozen=True)
class Pairing:
    slots: dict[str, Slot]
    how: dict[str, str]
    loose_runs: tuple[str, ...]
    loose_slots: tuple[Slot, ...]

    @property
    def by_title(self) -> int:
        return sum(1 for one in self.how.values() if one == BY_TITLE)


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())[:CELL_MAX]


def _names(cell: Any) -> tuple[str, ...]:
    found: list[str] = []
    for part in SPLIT.split(_text(cell)):
        name = part.strip()[:NAME_MAX]
        if name and name.lower() not in {one.lower() for one in found}:
            found.append(name)
    return tuple(found[:NAMES_MAX])


def when_of(text: Any) -> datetime | None:
    """`2026-10-03 at 1:00PM` → that wall clock in US Eastern, whatever the header calls it."""
    found = WHEN.match(_text(text))
    eastern = zone(EASTERN)
    if found is None or eastern is None:
        return None
    year, month, day, hour, minute = (int(one) for one in found.groups()[:5])
    half = (found.group(6) or "").lower()
    if half:
        if not 1 <= hour <= 12:
            return None
        hour = hour % 12 + (12 if half == "pm" else 0)
    try:
        return datetime(year, month, day, hour, minute, tzinfo=eastern)
    except ValueError:
        return None


def _header(table: list[list[str]]) -> tuple[int, dict[str, int]] | None:
    for index, row in enumerate(table[:10]):
        names = [_text(cell).lower() for cell in row]
        if not any(one.startswith(TIME_COLUMN) for one in names) or GAME_COLUMN not in names:
            continue
        found = {
            TIME_COLUMN: next(i for i, one in enumerate(names) if one.startswith(TIME_COLUMN)),
            GAME_COLUMN: names.index(GAME_COLUMN),
        }
        for at, name in enumerate(names):
            for head, key in COLUMNS.items():
                if name.startswith(head) and key not in found:
                    found[key] = at
        return (index, found)
    return None


def _at(row: list[str], index: int | None) -> str:
    return _text(row[index]) if index is not None and index < len(row) else ""


def slots_of(text: Any) -> list[Slot]:
    """An organisers' schedule sheet as slots; a row with a time and no game is a separator."""
    table = list(csv.reader(io.StringIO(str(text or "").lstrip("﻿"))))[:ROWS_MAX]
    header = _header(table)
    if header is None:
        raise ScheduleError(NOT_A_SCHEDULE)
    first, at = header
    found: list[Slot] = []
    for row in table[first + 1 :]:
        start, game = when_of(_at(row, at[TIME_COLUMN])), _at(row, at[GAME_COLUMN])
        if start is None or not game:
            continue
        found.append(
            Slot(
                start=start,
                seconds=seconds_of(_at(row, at.get("estimate"))) or None,
                game=game,
                category=_at(row, at.get("category")),
                runners=_names(_at(row, at.get("runners"))),
                hosts=_names(_at(row, at.get("hosts"))),
                commentators=_names(_at(row, at.get("commentators"))),
            )
        )
    found.sort(key=lambda one: one.start)
    return found


def show_day(at: Any) -> date | None:
    """The show-day a moment belongs to: Eastern, rolling at 6 AM so a late run stays put."""
    moment = at if isinstance(at, datetime) else parse_ts(at)
    eastern = zone(EASTERN)
    if moment is None or eastern is None:
        return None
    return (moment.astimezone(eastern) - DAY_ROLLS).date()


def _same_title(one: str, other: str) -> bool:
    if not one or not other:
        return False
    if one == other:
        return True
    short, long = sorted((one, other), key=len)
    return len(short) >= TITLE_FLOOR and f" {short} " in f" {long} "


def paired(runs: Any, slots: list[Slot]) -> Pairing:
    """Each run's slot: by game title first (in order, so a game played twice pairs twice), then
    — within one show-day, and only when as many runs as slots are left — by order."""
    free = list(slots)
    found: dict[str, Slot] = {}
    how: dict[str, str] = {}
    listed = list(runs or ())
    for run in listed:
        title = normalise(run.game)
        hit = next((one for one in free if normalise(one.game) == title), None) or next(
            (one for one in free if _same_title(normalise(one.game), title)), None
        )
        if hit is not None:
            free.remove(hit)
            found[run.external_id] = hit
            how[run.external_id] = BY_TITLE
    days: dict[Any, tuple[list[Run], list[Slot]]] = {}
    for run in listed:
        if run.external_id not in found:
            days.setdefault(show_day(run.starts_at), ([], []))[0].append(run)
    for slot in free:
        days.setdefault(show_day(slot.start), ([], []))[1].append(slot)
    for day, (left_runs, left_slots) in days.items():
        if day is None or not left_runs or len(left_runs) != len(left_slots):
            continue
        for run, slot in zip(left_runs, left_slots, strict=True):
            free.remove(slot)
            found[run.external_id] = slot
            how[run.external_id] = BY_ORDER
    return Pairing(
        found,
        how,
        tuple(one.external_id for one in listed if one.external_id not in found),
        tuple(free),
    )


def fits(runs: Any, slots: list[Slot], pairing: Pairing) -> bool:
    """A sheet is this marathon's when their show-days overlap and at least half of the
    marathon's runs are in it by title."""
    listed = list(runs or ())
    ours = {show_day(one.starts_at) for one in listed} - {None}
    theirs = {show_day(one.start) for one in slots}
    if not listed or not (ours & theirs):
        return False
    return pairing.by_title >= len(listed) * FITS


def _people(run: Run, slot: Slot) -> tuple[Person, ...]:
    kept = [one for one in run.people if one.part != COMMENTATOR]
    if slot.hosts:
        kept = [one for one in kept if one.part != HOST]
        kept += [Person(name, None, HOST) for name in slot.hosts]
    return tuple(kept + [Person(name, None, COMMENTATOR) for name in slot.commentators])


def overlaid(runs: Any, pairing: Pairing) -> list[Run]:
    """The runs on the sheet's own clock and people: a paired run takes its slot's start, its
    estimate, hosts and commentators; one with no slot starts where the run before it ends."""
    found: list[Run] = []
    cursor: datetime | None = None
    day: date | None = None
    for run in runs or ():
        slot = pairing.slots.get(run.external_id)
        if slot is not None:
            seconds = slot.seconds or run.run_seconds
            start: datetime | None = slot.start
            people = _people(run, slot)
        else:
            seconds = run.run_seconds
            same = cursor is not None and show_day(run.starts_at) == day
            start = cursor if same else parse_ts(run.starts_at)
            people = run.people
        end = start + timedelta(seconds=seconds or 0) if start is not None else None
        cursor, day = end, show_day(start) if start is not None else day
        found.append(
            replace(
                run,
                starts_at=start.astimezone(UTC).isoformat() if start else None,
                ends_at=end.astimezone(UTC).isoformat() if end else None,
                run_seconds=seconds,
                people=people,
            )
        )
    return found


def kept(runs: Any, rows: Any) -> list[Run]:
    """The runs as the stored rows last held the overlay: their sheet times, estimate, hosts and
    commentators — for a read on which the event sheet could not be had."""
    known = {str(_cell(row, "external_id")): row for row in rows or ()}
    found: list[Run] = []
    for run in runs or ():
        row = known.get(run.external_id)
        if row is None or _cell(row, "state") == DROPPED:
            found.append(run)
            continue
        extra = [one for one in people_of(row) if one.get("part") in (HOST, COMMENTATOR)]
        people = [one for one in run.people if one.part not in (HOST, COMMENTATOR)]
        people += [Person(str(one.get("name") or ""), None, str(one["part"])) for one in extra]
        found.append(
            replace(
                run,
                starts_at=_cell(row, "sheet_at") or run.starts_at,
                ends_at=_cell(row, "sheet_ends_at") or run.ends_at,
                run_seconds=_cell(row, "run_seconds") or run.run_seconds,
                people=tuple(people) if extra else run.people,
            )
        )
    return found


# --- keeping the clock on a sheet that has gaps ------------------------------------------------


def chains(rows: Any) -> list[list[Any]]:
    """A show-day's runs in the sheet's order; three hours with nothing on starts a new one."""
    ordered = sorted(
        (
            row
            for row in rows or ()
            if _cell(row, "state") != DROPPED and sig.sheet_start(row) is not None
        ),
        key=lambda row: (sig.sheet_start(row), int(_cell(row, "order_no") or 0)),
    )
    found: list[list[Any]] = []
    for row in ordered:
        if found:
            ended = sig.sheet_end(found[-1][-1]) or sig.sheet_start(found[-1][-1])
            if sig.sheet_start(row) - ended <= CHAIN_GAP:
                found[-1].append(row)
                continue
        found.append([row])
    return found


def retimed(rows: Any) -> list[sig.Retime]:
    """`marathon_signals.retimed` for a sheet with setup between its runs: a run seen starting
    is anchored there, and each later run of its show-day starts after the one before it by the
    sheet's own gap. Runs before the first anchor keep the sheet's times; a run that is live or
    done and was never seen starting stays where it is."""
    found: list[sig.Retime] = []
    for chain in chains(rows):
        cursor: datetime | None = None
        before: Any = None
        for row in chain:
            actual = parse_ts(_cell(row, "actual_started_at"))
            ended = parse_ts(_cell(row, "actual_ended_at"))
            held = actual is None and sig.settled(row)
            gap = timedelta(0)
            if before is not None and sig.sheet_end(before) is not None:
                gap = max(timedelta(0), sig.sheet_start(row) - sig.sheet_end(before))
            before = row
            if actual is None and cursor is None and ended is None:
                if held:
                    continue
                start, end = sig.sheet_start(row), sig.sheet_end(row)
            else:
                stays = parse_ts(_cell(row, "scheduled_at")) if held else None
                start = actual or stays
                if start is None:
                    start = cursor + gap if cursor is not None else sig.sheet_start(row)
                span = sig.length_of(row)
                end = ended or (parse_ts(_cell(row, "ends_at")) if stays is not None else None)
                if end is None and start is not None and span is not None:
                    end = start + span
                cursor = end
            if sig._differs(_cell(row, "scheduled_at"), start) or sig._differs(
                _cell(row, "ends_at"), end
            ):
                found.append(sig.Retime(row, sig._iso(start), sig._iso(end)))
    return found


# --- what a marathon remembers about its sheet --------------------------------------------------


def state_of(marathon: Any) -> dict[str, Any] | None:
    try:
        found = json.loads(_cell(marathon, STATE_COLUMN) or "null")
    except (TypeError, ValueError):
        return None
    return found if isinstance(found, dict) and found.get("url") else None


def applied(marathon: Any) -> bool:
    found = state_of(marathon)
    return bool(found and found.get("applied"))


def state(sheet: Any, runs: Any, pairing: Pairing, *, on: bool) -> dict[str, Any]:
    return {
        "label": str(sheet.label)[:100],
        "url": str(sheet.page)[:300],
        "runs": len(list(runs or ())),
        "matched": len(pairing.slots),
        "by_order": len(pairing.slots) - pairing.by_title,
        "applied": bool(on),
        "stale": None,
    }


def dump(found: dict[str, Any] | None) -> str | None:
    return json.dumps(found, sort_keys=True) if found else None


__all__ = [
    "COLUMN",
    "NO_LONGER_LINKED",
    "NOT_A_SCHEDULE",
    "STATE_COLUMN",
    "Pairing",
    "Slot",
    "applied",
    "chains",
    "dump",
    "fits",
    "kept",
    "overlaid",
    "paired",
    "retimed",
    "show_day",
    "slots_of",
    "state",
    "state_of",
    "when_of",
]
