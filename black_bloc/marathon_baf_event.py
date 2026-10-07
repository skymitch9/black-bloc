"""Whether a show-day is a BaF event, and which heads-up carries its one Marathon-role ping."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any, NamedTuple

from . import marathon as mt
from . import marathon_overlay as overlay
from . import marathon_signals as sig
from .golive import parse_ts
from .marathon_role_ping import BAF_EVENT_DAY, BAF_EVENT_PINGED
from .marathon_sources import GDQ_HOTFIX, RUNNER
from .timezones import zone

YES = "yes"
NO = "no"
UNSURE = "unsure"
FOLLOW = "follow"
ANSWERS = (YES, NO, UNSURE)
CHOICES = (FOLLOW, YES, NO)
BY_STAFF = "staff"
BY_NAME = "name"
BY_RUNS = "all_runs"
BY_SHARE = "share"
BY_FEW = "few_runs"
BY_MIXED = "mixed"
BY_NO_RUNS = "no_runs"
REASONS = (BY_STAFF, BY_NAME, BY_RUNS, BY_SHARE, BY_FEW, BY_MIXED, BY_NO_RUNS)
COLUMN = "baf_event"
ASK_COLUMN = "baf_event_ask"
PINGS_COLUMN = "baf_event_pings"
PER_RUN = "per_run"
CARRY = "carry"
QUIET = "quiet"
YES_WORDS = ("yes", "on", "true", "1")
NO_WORDS = ("no", "off", "false", "0")
FOLLOW_WORDS = ("", "follow", "default", "auto", "null", "none")
BAD_CHOICE = (
    "Say follow, yes or no for whether **{marathon}** is a BaF event, so nothing was changed."
)
BAD_CHOICE_CODE = "bad_baf_event"
FOLD = re.compile(r"[^a-z0-9]+")
DAY_SPAN = timedelta(hours=24)


class Judgement(NamedTuple):
    answer: str
    reason: str
    runs: int = 0
    baf: int = 0
    name: str = ""

    @property
    def yes(self) -> bool:
        return self.answer == YES


class Reading(NamedTuple):
    marathon: Any
    days: list[list[Any]]
    records: list[dict[str, Any]]
    marks: tuple[int, ...]
    ping_mark: int
    wanted_mark: int
    names: tuple[str, ...]
    min_runs: int
    ask_percent: int

    @property
    def limit(self) -> int:
        return event_mark(self.marks, self.wanted_mark)[0]

    @property
    def fell_back(self) -> bool:
        return event_mark(self.marks, self.wanted_mark)[1]


class Plan(NamedTuple):
    kind: str
    reason: str | None = None
    judgement: Judgement | None = None
    day: list[Any] | None = None
    record: dict[str, Any] | None = None


class DayState(NamedTuple):
    day: list[Any]
    starts_at: datetime | None
    judgement: Judgement
    worked: Judgement
    record: dict[str, Any] | None
    carrier: Any
    carrier_mark: int | None
    over: bool

    @property
    def governed(self) -> bool:
        return self.judgement.yes or self.record is not None


# --- the staff answer ---------------------------------------------------------------------------


def stored(marathon: Any) -> bool | None:
    value = mt._cell(marathon, COLUMN)
    return None if value is None else bool(value)


def clean(given: Any) -> tuple[bool, bool | None]:
    """`(understood, value)`: True / False, or None to follow what the bot works out."""
    if given is None or isinstance(given, bool):
        return (True, given)
    if isinstance(given, int):
        return (given in (0, 1), bool(given) if given in (0, 1) else None)
    word = str(given).strip().lower()
    if word in YES_WORDS:
        return (True, True)
    if word in NO_WORDS:
        return (True, False)
    if word in FOLLOW_WORDS:
        return (True, None)
    return (False, None)


def choice_of(own: bool | None) -> str:
    return FOLLOW if own is None else (YES if own else NO)


# --- the judgement ------------------------------------------------------------------------------


def name_key(text: Any) -> str:
    return FOLD.sub("", str(text or "").lower())


def names_of(text: Any) -> tuple[str, ...]:
    found: list[str] = []
    for part in str(text or "").split(","):
        name = " ".join(part.split())
        if name and name_key(name) and name_key(name) not in {name_key(one) for one in found}:
            found.append(name)
    return tuple(found)


def show_names(marathon: Any) -> tuple[str, ...]:
    """What the marathon's show is called: its own name, and a Hotfix show's name off its ref."""
    found = [str(mt._cell(marathon, "name") or "")]
    if mt._cell(marathon, "source") == GDQ_HOTFIX:
        found.append(str(mt._cell(marathon, "source_ref") or "").split("/")[0])
    return tuple(one for one in found if one)


def name_hit(names: Any, candidates: Any) -> str:
    keys = [name_key(one) for one in candidates or ()]
    for name in names or ():
        wanted = name_key(name)
        if wanted and any(wanted in one for one in keys):
            return str(name)
    return ""


def has_runner(row: Any) -> bool:
    """A matched BaF runner; a BaF host or commentator never makes a run a BaF run here."""
    return any(
        one.get("user_id") and one.get("part") == RUNNER and one.get("counts") is not False
        for one in mt.people_of(row)
    )


def kept(rows: Any) -> list[Any]:
    return [row for row in rows or () if mt._cell(row, "state") != mt.DROPPED]


def worked_out(
    marathon: Any, day: Any, *, names: Any, min_runs: int, ask_percent: int
) -> Judgement:
    rows = kept(day)
    runs = len(rows)
    baf = len([row for row in rows if has_runner(row)])
    hit = name_hit(names, show_names(marathon))
    if hit:
        return Judgement(YES, BY_NAME, runs, baf, hit)
    if not runs:
        return Judgement(NO, BY_NO_RUNS, runs, baf)
    if baf == runs:
        if runs >= max(1, int(min_runs)):
            return Judgement(YES, BY_RUNS, runs, baf)
        return Judgement(NO, BY_FEW, runs, baf)
    if baf * 100 >= int(ask_percent) * runs:
        return Judgement(UNSURE, BY_SHARE, runs, baf)
    return Judgement(NO, BY_MIXED, runs, baf)


def judge(marathon: Any, day: Any, *, names: Any, min_runs: int, ask_percent: int) -> Judgement:
    """Staff first, then the show's name, then the day's runs."""
    found = worked_out(marathon, day, names=names, min_runs=min_runs, ask_percent=ask_percent)
    own = stored(marathon)
    if own is None:
        return found
    return Judgement(YES if own else NO, BY_STAFF, found.runs, found.baf)


# --- show-days ----------------------------------------------------------------------------------


def days_of(rows: Any, tz_name: Any = None) -> list[list[Any]]:
    """The show-days: three hours with nothing on starts a new one, and a show that runs past
    a day without stopping is one day per calendar date in the server's zone."""
    where = zone(str(tz_name or "")) or UTC
    found: list[list[Any]] = []
    for chain in overlay.chains(rows):
        starts, ends = span_of(chain)
        if starts is None or ends is None or ends - starts <= DAY_SPAN:
            found.append(chain)
            continue
        by_date: dict[Any, list[Any]] = {}
        for row in chain:
            by_date.setdefault(sig.sheet_start(row).astimezone(where).date(), []).append(row)
        found.extend(by_date.values())
    return found


def day_of(row: Any, days: Any) -> list[Any] | None:
    for day in days or ():
        if any(sig.same(one, row) for one in day):
            return list(day)
    return None


def span_of(day: Any) -> tuple[datetime | None, datetime | None]:
    starts = [sig.sheet_start(row) for row in day or () if sig.sheet_start(row) is not None]
    ends = [sig.sheet_end(row) or sig.sheet_start(row) for row in day or ()]
    ends = [one for one in ends if one is not None]
    return (min(starts) if starts else None, max(ends) if ends else None)


def ids_of(day: Any) -> list[int]:
    return [int(mt._cell(row, "id")) for row in day or () if mt._cell(row, "id") is not None]


# --- the stored pings ---------------------------------------------------------------------------


def pings_of(marathon: Any) -> list[dict[str, Any]]:
    raw = mt._cell(marathon, PINGS_COLUMN)
    try:
        found = json.loads(raw or "[]") if not isinstance(raw, list) else raw
    except (TypeError, ValueError):
        return []
    return [dict(one) for one in found if isinstance(one, dict)] if isinstance(found, list) else []


def dump_pings(records: Any) -> str | None:
    found = [dict(one) for one in records or ()]
    return json.dumps(found) if found else None


def covers(record: dict[str, Any], day: Any) -> bool:
    """The record is this day's: it names one of its runs, or their planned hours overlap."""
    if set(ids_of(day)) & {int(one) for one in record.get("runs") or () if str(one).isdigit()}:
        return True
    starts, ends = span_of(day)
    was_from, was_to = parse_ts(record.get("starts_at")), parse_ts(record.get("ends_at"))
    if None in (starts, ends, was_from, was_to):
        return False
    return starts < was_to and was_from < ends


def pinged(records: Any, day: Any) -> dict[str, Any] | None:
    for record in records or ():
        if not record.get("missed") and covers(record, day):
            return record
    return None


def missed(records: Any, day: Any) -> dict[str, Any] | None:
    for record in records or ():
        if record.get("missed") and covers(record, day):
            return record
    return None


def record_for(day: Any, row: Any, mark: Any, now: datetime, **extra: Any) -> dict[str, Any]:
    starts, ends = span_of(day)
    return {
        "run_id": mt._cell(row, "id"),
        "game": mt._cell(row, "game"),
        "mark": None if mark is None else int(mark),
        "at": now.isoformat(),
        "runs": ids_of(day),
        "starts_at": starts.isoformat() if starts is not None else None,
        "ends_at": ends.isoformat() if ends is not None else None,
    } | extra


def without(records: Any, record: dict[str, Any]) -> list[dict[str, Any]]:
    return [one for one in records or () if one is not record and one != record]


def sent(records: Any, record: dict[str, Any], **fields: Any) -> list[dict[str, Any]]:
    return [*without(records, record), record | {"sent": True} | fields]


# --- which heads-up carries it ------------------------------------------------------------------


def event_mark(marks: Any, wanted: Any) -> tuple[int, bool]:
    """`(the mark, fell back)`: the wanted mark when it is a reminder mark, else the largest mark
    at or under it, else the smallest there is."""
    found = sorted({int(one) for one in marks or ()})
    wanted = int(wanted)
    if wanted in found or not found:
        return (wanted, False)
    under = [one for one in found if one <= wanted]
    return (under[-1] if under else found[0], True)


def unsent(row: Any, marks: Any, limit: int) -> list[int]:
    gone = set(mt.marks_of(row))
    return sorted(
        (int(one) for one in set(marks or ()) if int(one) <= int(limit) and int(one) not in gone),
        reverse=True,
    )


def _always(_row: Any) -> bool:
    return True


def carrier(
    day: Any,
    marks: Any,
    limit: int,
    *,
    this: Any = None,
    this_mark: int | None = None,
    speaks: Any = None,
) -> tuple[Any, int | None]:
    """`(the run, its next mark)`: the day's first BaF run still coming up that has a heads-up
    left at or under the mark and somebody to name publicly."""
    speaks = speaks or _always
    for row in day or ():
        if mt._cell(row, "state") != mt.UPCOMING or not mt.is_ours(row) or not speaks(row):
            continue
        left = unsent(row, marks, limit)
        if this is not None and sig.same(row, this) and this_mark is not None:
            if int(this_mark) <= int(limit):
                left = sorted(set(left) | {int(this_mark)}, reverse=True)
        if left:
            return (row, left[0])
    return (None, None)


def reading(
    marathon: Any,
    rows: Any,
    *,
    marks: Any,
    ping_mark: int,
    wanted_mark: int,
    names: Any,
    min_runs: int,
    ask_percent: int,
    tz_name: Any = None,
) -> Reading:
    return Reading(
        marathon,
        days_of(rows, tz_name),
        pings_of(marathon),
        tuple(sorted({int(one) for one in marks or ()}, reverse=True)),
        int(ping_mark),
        int(wanted_mark),
        tuple(names or ()),
        int(min_runs),
        int(ask_percent),
    )


def judgement_of(found: Reading, day: Any, *, own: bool = True) -> Judgement:
    rule = judge if own else worked_out
    return rule(
        found.marathon,
        day,
        names=found.names,
        min_runs=found.min_runs,
        ask_percent=found.ask_percent,
    )


def plan(found: Reading, row: Any, mark: int, *, speaks: Any = None) -> Plan:
    """What one heads-up does about the Marathon role: per run as before, the day's one
    carrier, or quiet because the day has or had its own."""
    day = day_of(row, found.days)
    if day is None:
        return Plan(PER_RUN)
    record = pinged(found.records, day)
    judgement = judgement_of(found, day)
    if record is not None:
        return Plan(QUIET, BAF_EVENT_PINGED, judgement, day, record)
    if not judgement.yes:
        return Plan(PER_RUN, None, judgement, day)
    chosen, _next = carrier(
        day, found.marks, found.limit, this=row, this_mark=mark, speaks=speaks
    )
    if chosen is not None and sig.same(chosen, row) and int(mark) <= found.limit:
        return Plan(CARRY, None, judgement, day)
    return Plan(QUIET, BAF_EVENT_DAY, judgement, day)


def quiet_reason(found: Reading, row: Any) -> str | None:
    """Why a heads-up that is not a run's own (a host block's) stays quiet on this day."""
    day = day_of(row, found.days)
    if day is None:
        return None
    if pinged(found.records, day) is not None:
        return BAF_EVENT_PINGED
    return BAF_EVENT_DAY if judgement_of(found, day).yes else None


def predicts(found: Reading, row: Any, mark: int, *, speaks: Any = None) -> bool | None:
    """Whether a heads-up still to come would carry the day's ping; None where the per-run
    rule decides."""
    day = day_of(row, found.days)
    if day is None:
        return None
    if pinged(found.records, day) is not None:
        return False
    if not judgement_of(found, day).yes:
        return None
    chosen, next_mark = carrier(day, found.marks, found.limit, speaks=speaks)
    return chosen is not None and sig.same(chosen, row) and int(mark) == next_mark


def day_states(found: Reading, *, speaks: Any = None) -> list[DayState]:
    states: list[DayState] = []
    for day in found.days:
        judgement = judgement_of(found, day)
        record = pinged(found.records, day)
        chosen, mark = (None, None)
        if judgement.yes and record is None:
            chosen, mark = carrier(day, found.marks, found.limit, speaks=speaks)
        states.append(
            DayState(
                list(day),
                span_of(day)[0],
                judgement,
                judgement_of(found, day, own=False),
                record,
                chosen,
                mark,
                all(mt._cell(row, "state") == mt.DONE for row in kept(day)),
            )
        )
    return states


def current(states: Any) -> DayState | None:
    """The day staff are asking about: the first not over, else the last."""
    found = list(states or ())
    return next((one for one in found if not one.over), found[-1] if found else None)


def asks(states: Any) -> DayState | None:
    """The first day still to come that the bot is not sure about."""
    return next(
        (one for one in states or () if not one.over and one.judgement.answer == UNSURE), None
    )


# --- the question -------------------------------------------------------------------------------


def ask_of(marathon: Any) -> dict[str, Any]:
    raw = mt._cell(marathon, ASK_COLUMN)
    try:
        found = json.loads(raw or "{}") if not isinstance(raw, dict) else raw
    except (TypeError, ValueError):
        return {}
    return dict(found) if isinstance(found, dict) else {}


def dump_ask(record: Any) -> str | None:
    return json.dumps(dict(record)) if record else None


__all__ = [
    "ANSWERS",
    "ASK_COLUMN",
    "BAD_CHOICE",
    "BAD_CHOICE_CODE",
    "BY_FEW",
    "BY_MIXED",
    "BY_NAME",
    "BY_NO_RUNS",
    "BY_RUNS",
    "BY_SHARE",
    "BY_STAFF",
    "CARRY",
    "CHOICES",
    "COLUMN",
    "FOLLOW",
    "NO",
    "PER_RUN",
    "PINGS_COLUMN",
    "QUIET",
    "REASONS",
    "UNSURE",
    "YES",
    "DayState",
    "Judgement",
    "Plan",
    "Reading",
    "ask_of",
    "asks",
    "carrier",
    "choice_of",
    "clean",
    "covers",
    "current",
    "day_of",
    "day_states",
    "days_of",
    "dump_ask",
    "dump_pings",
    "event_mark",
    "has_runner",
    "judge",
    "judgement_of",
    "kept",
    "missed",
    "name_hit",
    "name_key",
    "names_of",
    "pinged",
    "pings_of",
    "plan",
    "predicts",
    "quiet_reason",
    "reading",
    "record_for",
    "sent",
    "show_names",
    "span_of",
    "stored",
    "unsent",
    "without",
    "worked_out",
]
