"""Whether a marathon is a BaF event, and which heads-up carries each show-day's one
Marathon-role ping."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any, NamedTuple

from . import marathon as mt
from . import marathon_overlay as overlay
from . import marathon_reminder_posts as mrem
from . import marathon_signals as sig
from .golive import parse_ts
from .marathon_role_ping import BAF_EVENT_DAY, BAF_EVENT_PINGED
from .marathon_sources import GDQ_HOTFIX, RUNNER
from .timezones import zone

YES = "yes"
NO = "no"
UNSURE = "unsure"
FOLLOW = "follow"
CLEAR = "clear"
CLEARED = "cleared"
ANSWER_FIELDS = ("answer", "answered_by", "answered_at")
CLEAR_FIELDS = (CLEARED, "cleared_by", "cleared_at")
ANSWERS = (YES, NO, UNSURE)
CHOICES = (FOLLOW, YES, NO)
BY_STAFF = "staff"
BY_LEADS = "leads"
BY_NAME = "name"
BY_RUNS = "all_runs"
BY_SHARE = "share"
BY_FEW = "few_runs"
BY_MIXED = "mixed"
BY_NO_RUNS = "no_runs"
BY_ACTED = "acted"
REASONS = (
    BY_STAFF,
    BY_LEADS,
    BY_NAME,
    BY_RUNS,
    BY_SHARE,
    BY_FEW,
    BY_MIXED,
    BY_NO_RUNS,
    BY_ACTED,
)
RULE_REASONS = (BY_NAME, BY_RUNS, BY_ACTED)
OPEN_REASONS = (BY_SHARE, BY_ACTED)
COLUMN = "baf_event"
ASK_COLUMN = "baf_event_ask"
PINGS_COLUMN = "baf_event_pings"
PER_RUN = "per_run"
EVENT = "event"
PING_WILL = "will"
PING_DONE = "done"
PING_UNCONFIRMED = "unconfirmed"
PING_OFF = "off"
CARRY = "carry"
QUIET = "quiet"
NOBODY_TO_NAME = "nobody_to_name"
NO_BAF_RUN = "no_baf_run"
MARKS_SPENT = "marks_spent"
CAUSES = (NOBODY_TO_NAME, NO_BAF_RUN, MARKS_SPENT)
SENT = "sent"
GIVE_BACK = "give_back"
UNKNOWN = "unknown"
ASK_PENDING = "pending"
ASK_FAILED = "failed"
ASK_NOWHERE = "nowhere"
ASK_ANSWERED = "answered"
YES_WORDS = ("yes", "on", "true", "1")
NO_WORDS = ("no", "off", "false", "0")
FOLLOW_WORDS = ("", "follow", "default", "auto", "null", "none")
BAD_CHOICE = (
    "Say follow, yes or no for whether **{marathon}** is a BaF event, so nothing was changed."
)
BAD_CHOICE_CODE = "bad_baf_event"
FOLD = re.compile(r"[^a-z0-9]+")
GAP = "[^a-z0-9]*"
NOTHING = timedelta(0)
DAY_SPAN = timedelta(hours=24)
FIRST = datetime.min.replace(tzinfo=UTC)


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
    asks: tuple[dict[str, Any], ...] = ()

    @property
    def rows(self) -> list[Any]:
        return [row for day in self.days for row in day]

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
    cause: str | None = None

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


def opens_with(show: Any, name: Any) -> bool:
    """The show's name starts with the listed name on whole words, spacing and punctuation
    set aside."""
    wanted = name_key(name)
    if not wanted:
        return False
    pattern = GAP + GAP.join(re.escape(one) for one in wanted) + "(?![a-z0-9])"
    return re.match(pattern, str(show or "").lower()) is not None


def name_hit(names: Any, candidates: Any) -> str:
    shows = list(candidates or ())
    for name in names or ():
        if any(opens_with(one, name) for one in shows):
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


def counts(rows: Any) -> tuple[int, int]:
    """`(runs, runs with a BaF runner)`, dropped runs left out."""
    found = kept(rows)
    return (len(found), len([row for row in found if has_runner(row)]))


def worked_out(
    marathon: Any, rows: Any, *, names: Any, min_runs: int, ask_percent: int
) -> Judgement:
    runs, baf = counts(rows)
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


def judge(
    marathon: Any,
    rows: Any,
    *,
    names: Any,
    min_runs: int,
    ask_percent: int,
    said: Any = None,
    follow: bool = False,
    acted: bool = False,
) -> Judgement:
    """The marathon's switch first (set aside with `follow`), then the answer to its question,
    then the name and the runs; an unsure reading stays yes once the bot acted on a yes."""
    found = worked_out(marathon, rows, names=names, min_runs=min_runs, ask_percent=ask_percent)
    own = None if follow else stored(marathon)
    if own is not None:
        return Judgement(YES if own else NO, BY_STAFF, found.runs, found.baf)
    if said in (YES, NO):
        return Judgement(str(said), BY_LEADS, found.runs, found.baf)
    if found.answer == UNSURE and acted:
        return Judgement(YES, BY_ACTED, found.runs, found.baf)
    return found


def acted(records: Any) -> bool:
    """The bot already gave a show-day its own one ping because a rule said yes."""
    return any(
        not one.get(PER_RUN)
        and not one.get("missed")
        and (one.get("sent") or one.get("unconfirmed"))
        and one.get("reason") in RULE_REASONS
        for one in records or ()
    )


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


def named(record: dict[str, Any]) -> set[int]:
    return {int(one) for one in record.get("runs") or () if str(one).isdigit()}


def overlap(record: dict[str, Any], day: Any) -> timedelta:
    starts, ends = span_of(day)
    was_from, was_to = parse_ts(record.get("starts_at")), parse_ts(record.get("ends_at"))
    if None in (starts, ends, was_from, was_to):
        return NOTHING
    return max(min(ends, was_to) - max(starts, was_from), NOTHING)


def covers(record: dict[str, Any], day: Any, days: Any = None) -> bool:
    """The record is this day's: it names one of its runs; or none of its runs is on any day
    any more and this is the one day whose planned hours it overlaps most."""
    wanted = named(record)
    if wanted & set(ids_of(day)):
        return True
    every = [list(one) for one in days or ()] or [list(day)]
    if any(wanted & set(ids_of(one)) for one in every):
        return False
    best = max(every, key=lambda one: overlap(record, one))
    return overlap(record, best) > NOTHING and ids_of(best) == ids_of(day)


def pinged(records: Any, day: Any, days: Any = None, *, yes: bool = True) -> dict[str, Any] | None:
    """The record that closes the day: its own one ping whatever the judgement says now, or a
    per-run mention once the day is a BaF event."""
    found = [one for one in records or () if not one.get("missed") and covers(one, day, days)]
    own = [one for one in found if not one.get(PER_RUN)]
    kept = own or (found if yes else [])
    return next((one for one in kept if one.get("sent")), kept[0] if kept else None)


def missed(records: Any, day: Any, days: Any = None) -> dict[str, Any] | None:
    for record in records or ():
        if record.get("missed") and covers(record, day, days):
            return record
    return None


def proof_of(record: dict[str, Any], rows: Any, role_id: Any) -> tuple[str, Any, Any]:
    """`(SENT | GIVE_BACK | UNKNOWN, message, channel)` for a claim never marked sent, from
    what its run remembers posting at that mark."""
    row = next((one for one in rows or () if mt._cell(one, "id") == record.get("run_id")), None)
    mark = record.get("mark")
    entry = mrem.of_run(row).get(int(mark)) if row is not None and mark is not None else None
    if entry is None:
        return (UNKNOWN, None, None)
    copy = entry.get(mrem.PUBLIC)
    if not copy:
        return (GIVE_BACK, None, None)
    if role_id and f"<@&{int(role_id)}>" in str(copy.get("head") or ""):
        return (SENT, copy.get("message_id"), copy.get("channel_id"))
    return (UNKNOWN, None, None)


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


def no_carrier(day: Any, marks: Any, limit: int, *, speaks: Any = None) -> str:
    """Why nothing carries a BaF event day's ping."""
    speaks = speaks or _always
    ours = [row for row in kept(day) if mt.is_ours(row)]
    if not ours:
        return NO_BAF_RUN
    left = [
        row for row in ours if mt._cell(row, "state") == mt.UPCOMING and unsent(row, marks, limit)
    ]
    if left and not any(speaks(row) for row in left):
        return NOBODY_TO_NAME
    return MARKS_SPENT


def may_be_matched(day: Any, now: datetime) -> bool:
    """A run nobody of ours is on yet that has not started: a match could still bring a
    heads-up."""
    return any(
        mt._cell(row, "state") == mt.UPCOMING
        and not mt.is_ours(row)
        and sig.sheet_start(row) is not None
        and now < sig.sheet_start(row)
        for row in kept(day)
    )


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
        tuple(asks_of(marathon)),
    )


def judgement_of(found: Reading, *, own: bool = True) -> Judgement:
    """The whole event's answer, over every run on a show-day; each show-day takes it. With
    `own` off the switch is set aside: what following would give."""
    return judge(
        found.marathon,
        found.rows,
        names=found.names,
        min_runs=found.min_runs,
        ask_percent=found.ask_percent,
        said=answer_of(found.asks),
        follow=not own,
        acted=acted(found.records),
    )


def undecided(judgement: Judgement) -> bool:
    """Nothing staff said decides it and the runs alone cannot."""
    return judgement.reason in OPEN_REASONS


def closed(found: Reading, day: Any, judgement: Judgement) -> dict[str, Any] | None:
    return pinged(found.records, day, found.days, yes=judgement.yes)


def plan(found: Reading, row: Any, mark: int, *, speaks: Any = None) -> Plan:
    """What one heads-up does about the Marathon role: per run as before, the day's one
    carrier, or quiet because the day has or had its own."""
    day = day_of(row, found.days)
    if day is None:
        return Plan(PER_RUN)
    judgement = judgement_of(found)
    record = closed(found, day, judgement)
    if record is not None:
        return Plan(QUIET, BAF_EVENT_PINGED, judgement, day, record)
    if not judgement.yes:
        return Plan(PER_RUN, None, judgement, day)
    chosen, _next = carrier(day, found.marks, found.limit, this=row, this_mark=mark, speaks=speaks)
    if chosen is not None and sig.same(chosen, row) and int(mark) <= found.limit:
        return Plan(CARRY, None, judgement, day)
    return Plan(QUIET, BAF_EVENT_DAY, judgement, day)


def quiet_reason(found: Reading, row: Any) -> str | None:
    """Why a heads-up that is not a run's own (a host block's) stays quiet on this day."""
    day = day_of(row, found.days)
    if day is None:
        return None
    judgement = judgement_of(found)
    if closed(found, day, judgement) is not None:
        return BAF_EVENT_PINGED
    return BAF_EVENT_DAY if judgement.yes else None


def predicts(found: Reading, row: Any, mark: int, *, speaks: Any = None) -> bool | None:
    """Whether a heads-up still to come would carry the day's ping; None where the per-run
    rule decides."""
    day = day_of(row, found.days)
    if day is None:
        return None
    judgement = judgement_of(found)
    if closed(found, day, judgement) is not None:
        return False
    if not judgement.yes:
        return None
    chosen, next_mark = carrier(day, found.marks, found.limit, speaks=speaks)
    return chosen is not None and sig.same(chosen, row) and int(mark) == next_mark


def day_states(found: Reading, *, speaks: Any = None) -> list[DayState]:
    states: list[DayState] = []
    judgement = judgement_of(found)
    worked = judgement_of(found, own=False)
    for day in found.days:
        record = closed(found, day, judgement)
        chosen, mark, cause = (None, None, None)
        if judgement.yes and record is None:
            chosen, mark = carrier(day, found.marks, found.limit, speaks=speaks)
            if chosen is None:
                cause = no_carrier(day, found.marks, found.limit, speaks=speaks)
        states.append(
            DayState(
                list(day),
                span_of(day)[0],
                judgement,
                worked,
                record,
                chosen,
                mark,
                all(mt._cell(row, "state") == mt.DONE for row in kept(day)),
                cause,
            )
        )
    return states


def ping_state(state: DayState, mentions: bool) -> str:
    """What becomes of one show-day's Marathon-role ping."""
    if state.record is not None:
        return PING_DONE if state.record.get("sent") else PING_UNCONFIRMED
    if not state.judgement.yes:
        return PER_RUN
    if not mentions:
        return PING_OFF
    if state.carrier is None:
        return state.cause or MARKS_SPENT
    return PING_WILL


def asks(found: Reading, states: Any) -> bool:
    """Whether the event's question is open: nothing decided it and a show-day is still to
    come."""
    return undecided(judgement_of(found)) and any(not one.over for one in states or ())


# --- the question -------------------------------------------------------------------------------


def asks_of(marathon: Any) -> list[dict[str, Any]]:
    """The event's question records; one from when each show-day had its own is kept and read
    as the event's."""
    raw = mt._cell(marathon, ASK_COLUMN)
    try:
        found = json.loads(raw or "[]") if isinstance(raw, str) or raw is None else raw
    except (TypeError, ValueError):
        return []
    if isinstance(found, dict):
        found = [found] if found else []
    return [dict(one) for one in found if isinstance(one, dict)] if isinstance(found, list) else []


def dump_asks(records: Any) -> str | None:
    found = [dict(one) for one in records or ()]
    return json.dumps(found) if found else None


def answered(asks: Any) -> dict[str, Any] | None:
    """The answer that stands: the latest one given, whichever question it was given on."""
    found = [one for one in asks or () if one.get("answer") in (YES, NO)]
    if not found:
        return None
    return max(
        enumerate(found),
        key=lambda pair: (parse_ts(pair[1].get("answered_at")) or FIRST, pair[0]),
    )[1]


def question(asks: Any) -> dict[str, Any] | None:
    """The event's question: the answer that stands, else the event's own record, the posted
    one first. An unanswered record of a per-day question is not it, nor is one whose answer
    was cleared."""
    said = answered(asks)
    if said is not None:
        return said
    own = [one for one in asks or () if one.get(EVENT) and not one.get(CLEARED)]
    return next((one for one in own if one.get("message_id")), own[-1] if own else None)


def cleared(asks: Any) -> dict[str, Any] | None:
    """The latest record whose answer staff cleared, while no answer stands."""
    if answered(asks) is not None:
        return None
    found = [one for one in asks or () if one.get(CLEARED)]
    if not found:
        return None
    return max(
        enumerate(found),
        key=lambda pair: (parse_ts(pair[1].get("cleared_at")) or FIRST, pair[0]),
    )[1]


def with_answer(record: dict[str, Any], answer: str, by: Any, at: str) -> dict[str, Any]:
    kept = {key: value for key, value in record.items() if key not in CLEAR_FIELDS}
    return kept | {"answer": answer, "answered_by": by, "answered_at": at}


def without_answers(asks: Any, by: Any, at: str) -> list[dict[str, Any]]:
    """Every answer taken off its record; the record stays, flagged, and is not asked on
    again."""
    return [
        {key: value for key, value in one.items() if key not in ANSWER_FIELDS}
        | {CLEARED: True, "cleared_by": by, "cleared_at": at}
        if one.get("answer") in (YES, NO)
        else dict(one)
        for one in asks or ()
    ]


def answer_of(asks: Any) -> str | None:
    said = answered(asks)
    return said.get("answer") if said else None


def ask_state(record: Any) -> str | None:
    if not record:
        return None
    if record.get("answer") in (YES, NO):
        return ASK_ANSWERED
    if record.get("message_id"):
        return ASK_PENDING
    if record.get("blocked"):
        return ASK_NOWHERE
    return ASK_FAILED if record.get("failed_at") or record.get("gave_up") else None


def same_schedule(record: dict[str, Any], rows: Any, judgement: Judgement) -> bool:
    return named(record) == set(ids_of(rows)) and record.get("baf") == judgement.baf


__all__ = [
    "ANSWERS",
    "ASK_ANSWERED",
    "ASK_COLUMN",
    "ASK_FAILED",
    "ASK_NOWHERE",
    "ASK_PENDING",
    "BAD_CHOICE",
    "BAD_CHOICE_CODE",
    "BY_ACTED",
    "BY_FEW",
    "BY_LEADS",
    "BY_MIXED",
    "BY_NAME",
    "BY_NO_RUNS",
    "BY_RUNS",
    "BY_SHARE",
    "BY_STAFF",
    "CARRY",
    "CAUSES",
    "CHOICES",
    "CLEAR",
    "CLEARED",
    "COLUMN",
    "DayState",
    "EVENT",
    "FOLLOW",
    "GIVE_BACK",
    "Judgement",
    "MARKS_SPENT",
    "NO",
    "NOBODY_TO_NAME",
    "NO_BAF_RUN",
    "OPEN_REASONS",
    "PER_RUN",
    "PINGS_COLUMN",
    "PING_DONE",
    "PING_OFF",
    "PING_UNCONFIRMED",
    "PING_WILL",
    "Plan",
    "QUIET",
    "REASONS",
    "RULE_REASONS",
    "Reading",
    "SENT",
    "UNKNOWN",
    "UNSURE",
    "YES",
    "acted",
    "answer_of",
    "answered",
    "ask_state",
    "asks",
    "asks_of",
    "carrier",
    "choice_of",
    "clean",
    "cleared",
    "closed",
    "counts",
    "covers",
    "day_of",
    "day_states",
    "days_of",
    "dump_asks",
    "dump_pings",
    "event_mark",
    "has_runner",
    "judge",
    "judgement_of",
    "kept",
    "may_be_matched",
    "missed",
    "name_hit",
    "name_key",
    "named",
    "names_of",
    "no_carrier",
    "opens_with",
    "overlap",
    "ping_state",
    "pinged",
    "pings_of",
    "plan",
    "predicts",
    "proof_of",
    "question",
    "quiet_reason",
    "reading",
    "record_for",
    "same_schedule",
    "sent",
    "show_names",
    "span_of",
    "stored",
    "undecided",
    "unsent",
    "with_answer",
    "without",
    "without_answers",
    "worked_out",
]
