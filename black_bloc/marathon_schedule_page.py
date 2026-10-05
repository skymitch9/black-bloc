"""The Marathon tracker page's one read: a marathon's runs with where each time came from."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from . import marathon as mt
from . import marathon_host_highlights as mhh
from . import marathon_overlay as overlay
from . import marathon_viewer as mv
from .golive import parse_ts
from .marathon_sources import SOURCE_WORDS, retimes_itself, schedule_page
from .timezones import zone

STREAM = "stream"
STARTED = "started"
ORGANISERS = "organisers"
SOURCE = "source"
FOLLOWS = "follows"
HELD = "held"
TRACKER = "tracker"
KIND_TRACKER = "tracker"
KIND_CLOCK_KEPT = "clock_kept"
MOVES_BY_MARKS = "marks"
ARCHIVED = "archived"
TIMES_FROM_WORDS = {
    ORGANISERS: "the organisers' sheet",
    SOURCE: "the source sheet plus setup time",
    TRACKER: "the tracker",
}
STATE_WORDS = {mt.UPCOMING: "upcoming", mt.LIVE: "live", mt.DONE: "done", mt.DROPPED: "skipped"}
DAY_GAP = timedelta(hours=4)
DAY_SPAN = timedelta(hours=24)
MOVES_LIMIT = 30
MEMBER = "member"
SCHEDULE = "schedule"
HOSTS = "hosts"
POST_LIVE = "live"
POST_RUN = "run"
POST_HOST = "host"
TWITCH = "https://www.twitch.tv/{login}"
YOUTUBE = "https://www.youtube.com/{path}"
LOGIN = re.compile(r"^[A-Za-z0-9_]{2,25}$")
HANDLE = re.compile(r"^@[A-Za-z0-9._-]{3,30}$")
CHANNEL_ID = re.compile(r"^UC[A-Za-z0-9_-]{22}$")

RUN_POST = "Heads-up: **{names}** runs **{game}** in {lead}."
HOST_POST = "Heads-up: **{names}** hosts {runs} from **{game}** in {lead}."
LIVE_POST = "The shoutout for **{names}** on **{game}** is up."
MOVE_KINDS = (
    "marathon.retimed",
    "marathon.run_live",
    "marathon.run_done",
    "marathon.run_reset",
    "marathon.member_run_moved",
    "marathon.schedule_changed",
    "marathon.run_renamed",
    "marathon.overlay_applied",
    "marathon.overlay_dropped",
    "marathon.sheet_times",
)
RETIMED_WORDS = {
    STREAM: "the stream showed a run starting",
    mt.BY_STAFF: "a staff move",
}
RENAMED_WORDS = ", {renamed} renamed"
MOVE_WORDS = {
    "marathon.retimed": (
        "{runs} re-timed after {why}: **{game}** moved from {{{{at:{was}}}}} to {{{{at:{to}}}}}"
    ),
    "marathon.run_live": "**{game}** is on now, by {why}",
    "marathon.run_done": "**{game}** is done, by {why}",
    "marathon.run_reset": "**{game}** was put back to coming up",
    "marathon.member_run_moved": (
        "**{game}** moved from {{{{at:{was}}}}} to {{{{at:{to}}}}} at a read of the source"
    ),
    "marathon.schedule_changed": (
        "The source changed at a read: {added} added, {moved} moved, {dropped} dropped{renamed}"
    ),
    "marathon.run_renamed": "**{game}** was renamed at a read of the source",
    "marathon.overlay_applied": (
        "The organisers' sheet **{label}** was laid over the schedule ({matched} of {runs} matched)"
    ),
    "marathon.overlay_dropped": "The organisers' sheet was taken off the schedule",
    "marathon.sheet_times": "{runs} put back on the sheet's times",
}


def _iso(at: datetime | None) -> str | None:
    return at.astimezone(UTC).isoformat() if at is not None else None


def _moment(value: Any) -> str | None:
    return _iso(parse_ts(value))


def _minutes(span: timedelta) -> int:
    return round(span.total_seconds() / 60)


def plural(count: Any, word: str) -> str:
    return f"{int(count or 0)} {word}{'' if int(count or 0) == 1 else 's'}"


def lead_words(minutes: int) -> str:
    if minutes and minutes % 60 == 0:
        return plural(minutes // 60, "hour")
    return plural(minutes, "minute")


def counts(person: Any) -> bool:
    """The People card's BaF: matched to a member; a commentator never is."""
    return bool(person.get("user_id")) and person.get("part") != mt.COMMENTATOR


def has_baf(row: Any) -> bool:
    return any(counts(one) for one in mt.people_of(row))


# --- channel links -------------------------------------------------------------------------


def twitch_url(login: Any) -> str | None:
    text = str(login or "").strip()
    return TWITCH.format(login=text) if LOGIN.match(text) else None


def youtube_url(link: Any) -> str | None:
    """A member's YouTube link row as a channel address: the handle, else the channel id."""
    if not link:
        return None
    handle = str(mt._cell(link, "handle") or "").strip()
    if handle and not handle.startswith("@"):
        handle = f"@{handle}"
    if HANDLE.match(handle):
        return YOUTUBE.format(path=handle)
    channel = str(mt._cell(link, "channel_id") or "").strip()
    return YOUTUBE.format(path=f"channel/{channel}") if CHANNEL_ID.match(channel) else None


def schedule_login(person: Any) -> Any:
    """The Twitch name the schedule itself gave, never a staff fix and never the host table's."""
    if person.get("login_from") == mv.FROM_VIEWER:
        return None
    return person["sheet_login"] if "sheet_login" in person else person.get("login")


def channels_of(person: Any, twitch: dict[int, str], youtube: dict[int, Any]) -> dict[str, Any]:
    """Each site settled on its own, first hit wins: the member's link, the schedule, hosts."""
    found: dict[str, tuple[str, str]] = {}

    def offer(site: str, url: str | None, source: str) -> None:
        if url and site not in found:
            found[site] = (url, source)

    user_id = person.get("user_id")
    if user_id:
        offer("twitch", twitch_url(twitch.get(int(user_id))), MEMBER)
        offer("youtube", youtube_url(youtube.get(int(user_id))), MEMBER)
    offer("twitch", twitch_url(schedule_login(person)), SCHEDULE)
    if person.get("part") == mt.HOST and person.get("login_from") == mv.FROM_VIEWER:
        offer("twitch", twitch_url(person.get("login")), HOSTS)
    first = found.get("twitch") or found.get("youtube")
    return {
        "twitch_url": found["twitch"][0] if "twitch" in found else None,
        "twitch_from": found["twitch"][1] if "twitch" in found else None,
        "youtube_url": found["youtube"][0] if "youtube" in found else None,
        "youtube_from": found["youtube"][1] if "youtube" in found else None,
        "link_from": first[1] if first else None,
    }


def person_row(
    person: Any, twitch: dict[int, str], youtube: dict[int, Any], name_of: Any
) -> dict[str, Any]:
    user_id = person.get("user_id")
    return {
        "name": person.get("name"),
        "login": person.get("login") or None,
        "part": person.get("part"),
        "user_id": str(user_id) if user_id else None,
        "member_name": name_of(int(user_id)) if user_id else None,
        "baf": counts(person),
    } | channels_of(person, twitch, youtube)


# --- where a time came from ----------------------------------------------------------------


def kind_of(marathon: Any) -> str:
    return KIND_TRACKER if retimes_itself(mt._cell(marathon, "source")) else KIND_CLOCK_KEPT


def times_from(marathon: Any) -> str:
    if kind_of(marathon) == KIND_TRACKER:
        return TRACKER
    return ORGANISERS if overlay.applied(marathon) else SOURCE


def plan_of(row: Any) -> datetime | None:
    return parse_ts(mt._cell(row, "sheet_at") or mt._cell(row, "scheduled_at"))


def plan_end(row: Any) -> datetime | None:
    return parse_ts(mt._cell(row, "sheet_ends_at") or mt._cell(row, "ends_at"))


def start_of(row: Any) -> datetime | None:
    """What really happened when it is known, else the time the bot is working from."""
    return parse_ts(mt._cell(row, "actual_started_at")) or parse_ts(mt._cell(row, "scheduled_at"))


def end_of(row: Any) -> datetime | None:
    return parse_ts(mt._cell(row, "actual_ended_at")) or parse_ts(mt._cell(row, "ends_at"))


def anchored(row: Any) -> bool:
    return bool(mt._cell(row, "actual_started_at") or mt._cell(row, "actual_ended_at"))


def from_of(row: Any, plan_from: str, after_anchor: bool) -> str | None:
    """The tag for the start shown; `after_anchor` is whether a run before it that day really
    started or ended."""
    if mt._cell(row, "state") == mt.DROPPED:
        return None
    if mt._cell(row, "actual_started_at"):
        return STARTED if mt._cell(row, "live_because") == mt.BY_STAFF else STREAM
    if plan_from == TRACKER:
        return TRACKER
    if start_of(row) == plan_of(row):
        return plan_from
    return FOLLOWS if after_anchor else HELD


# --- days ----------------------------------------------------------------------------------


def _local_date(at: datetime, tz_name: Any) -> Any:
    return at.astimezone(zone(str(tz_name or "")) or UTC).date()


def blocks_of(runs: Any, tz_name: Any) -> list[list[Any]]:
    """Runs in the source's order as days: more than four hours with nothing on starts a new
    one, and a block longer than a day (a marathon that never stops) splits by calendar date."""
    ordered = sorted(
        (row for row in runs or () if plan_of(row) is not None),
        key=lambda row: (plan_of(row), int(mt._cell(row, "order_no") or 0)),
    )
    found: list[list[Any]] = []
    ended: datetime | None = None
    for row in ordered:
        if ended is not None and plan_of(row) - ended <= DAY_GAP:
            found[-1].append(row)
        else:
            found.append([row])
        ended = plan_end(row) or plan_of(row)
    days: list[list[Any]] = []
    for block in found:
        last = plan_end(block[-1]) or plan_of(block[-1])
        if last - plan_of(block[0]) <= DAY_SPAN:
            days.append(block)
            continue
        by_date: dict[Any, list[Any]] = {}
        for row in block:
            by_date.setdefault(_local_date(plan_of(row), tz_name), []).append(row)
        days.extend(by_date.values())
    return days


def day_keys(days: list[list[Any]], tz_name: Any) -> list[str]:
    keys: list[str] = []
    for index, rows in enumerate(days):
        key = _local_date(plan_of(rows[0]), tz_name).isoformat()
        keys.append(f"{key}-{index}" if key in keys else key)
    return keys


def day_label(day: Any) -> str:
    return f"{day:%a} {day.day} {day:%b}"


def today_of(days: list[list[Any]], keys: list[str]) -> str | None:
    for state in (mt.LIVE, mt.UPCOMING):
        for key, rows in zip(keys, days, strict=True):
            if any(mt._cell(one, "state") == state for one in rows):
                return key
    return keys[-1] if keys else None


def drift_of(rows: list[Any], plan_from: str) -> tuple[int | None, Any]:
    """How far the next run not yet finished is off its plan; a tracker's upcoming run has no
    plan but itself, so only a run that really started is measured there."""
    for state in (mt.UPCOMING, mt.LIVE):
        row = next((one for one in rows if mt._cell(one, "state") == state), None)
        if row is None:
            continue
        if plan_from == TRACKER and not mt._cell(row, "actual_started_at"):
            continue
        start, plan = start_of(row), plan_of(row)
        if start is not None and plan is not None:
            return (_minutes(start - plan), mt._cell(row, "id"))
    return (None, None)


# --- rows ----------------------------------------------------------------------------------


def estimate_of(row: Any) -> int:
    seconds = mt._cell(row, "run_seconds")
    if seconds:
        return int(seconds)
    start, end = plan_of(row), plan_end(row)
    return max(0, int((end - start).total_seconds())) if start and end else 0


def can_of(row: Any, writes: bool) -> dict[str, bool]:
    state = mt._cell(row, "state")
    return {
        "start": writes and mt.can_mark_live(row),
        "finish": writes and state in (mt.UPCOMING, mt.LIVE),
        "set_start": False,
        "estimate": False,
        "skip": False,
        "restore": False,
    }


def sheet_row(
    row: Any,
    *,
    day: str,
    plan_from: str,
    after_anchor: bool,
    next_up: bool,
    writes: bool,
    people: list[dict[str, Any]],
) -> dict[str, Any]:
    state = str(mt._cell(row, "state"))
    dropped = state == mt.DROPPED
    start, plan = start_of(row), plan_of(row)
    estimate = estimate_of(row)
    return {
        "id": mt._cell(row, "id"),
        "day": day,
        "order_no": mt._cell(row, "order_no"),
        "game": mt._cell(row, "game"),
        "category": mt._cell(row, "category"),
        "people": people,
        "ours": has_baf(row),
        "state": state,
        "state_word": STATE_WORDS.get(state, state),
        "start_at": None if dropped else _iso(start),
        "ends_at": None if dropped else _iso(end_of(row)),
        "from": from_of(row, plan_from, after_anchor),
        "plan_at": _iso(plan),
        "plan_from": plan_from,
        "off_plan_minutes": None if dropped or start is None else _minutes(start - plan),
        "estimate_seconds": estimate,
        "estimate_from": SOURCE,
        "source_estimate_seconds": estimate,
        "actual_started_at": _moment(mt._cell(row, "actual_started_at")),
        "actual_ended_at": _moment(mt._cell(row, "actual_ended_at")),
        "staff_at": None,
        "live_because": mt._cell(row, "live_because"),
        "next_up": next_up,
        "can": can_of(row, writes),
    }


# --- what the bot posts next ---------------------------------------------------------------


def pending(sent: Any, marks: Any, stale: Any) -> list[int]:
    gone = {int(one) for one in sent or ()} | {int(one) for one in stale or ()}
    return sorted((int(one) for one in set(marks or ()) if int(one) not in gone), reverse=True)


def _post(kind: str, row: Any, day: str, mark: int, now: datetime, text: str, role: bool) -> dict:
    at = parse_ts(mt._cell(row, "scheduled_at")) - timedelta(minutes=mark)
    return {
        "at": _iso(at),
        "kind": kind,
        "run_id": mt._cell(row, "id"),
        "day": day,
        "passed": at < now,
        "minutes": mark,
        "role": bool(role),
        "text": text,
    }


def run_posts(
    rows: Any,
    day_of: dict[Any, str],
    *,
    marks: Any,
    ping_mark: int,
    stale_minutes: int,
    now: datetime,
    run_role: Any,
) -> list[dict[str, Any]]:
    """Each upcoming BaF run's marks still to fire, and a live one's shoutout that is up."""
    found: list[dict[str, Any]] = []
    for row in rows:
        ours = mt.ours(mt.people_of(row))
        day = day_of.get(mt._cell(row, "id"))
        if not ours or day is None:
            continue
        names = ", ".join(str(one["name"]) for one in ours)
        game = mt._cell(row, "game")
        state = mt._cell(row, "state")
        if state == mt.LIVE and mt._cell(row, "shout_message_id"):
            found.append(
                {
                    "at": None,
                    "kind": POST_LIVE,
                    "run_id": mt._cell(row, "id"),
                    "day": day,
                    "passed": False,
                    "minutes": None,
                    "role": False,
                    "text": LIVE_POST.format(names=names, game=game),
                }
            )
        if state != mt.UPCOMING or parse_ts(mt._cell(row, "scheduled_at")) is None:
            continue
        _due, stale = mt.due_marks(row, marks, now, stale_minutes=stale_minutes)
        for mark in pending(mt.marks_of(row), marks, stale):
            text = RUN_POST.format(names=names, game=game, lead=lead_words(mark))
            role = mark == int(ping_mark) and bool(run_role(row))
            found.append(_post(POST_RUN, row, day, mark, now, text, role))
    return found


def host_posts(
    marathon: Any,
    rows: Any,
    day_of: dict[Any, str],
    *,
    marks: Any,
    ping_mark: int,
    stale_minutes: int,
    now: datetime,
    block_role: Any,
    block_speaks: Any,
) -> list[dict[str, Any]]:
    """Each upcoming BaF host block's marks still to fire, from the block's own record."""
    found: list[dict[str, Any]] = []
    records = mhh.records(marathon)
    used: set[int] = set()
    for block in mhh.blocks(rows):
        record = mhh.claim(records, block, used)
        day = day_of.get(block.start_run_id)
        if day is None or mhh.state_of(block) != mhh.UPCOMING or block.starts is None:
            continue
        if not block_speaks(block):
            continue
        sent = (record or {}).get("marks") or []
        if record is not None and record.get("legacy_reminded"):
            sent = mhh.passed_marks(block, marks, now)
        _due, stale = mhh.due(block, {"marks": sent}, marks, now, stale_minutes=stale_minutes)
        for mark in pending(sent, marks, stale):
            text = HOST_POST.format(
                names=block.names,
                runs=plural(len(block.runs), "run"),
                game=mt._cell(block.first, "game"),
                lead=lead_words(mark),
            )
            role = mark == int(ping_mark) and bool(block_role(block))
            found.append(_post(POST_HOST, block.first, day, mark, now, text, role))
    return found


# --- moves ---------------------------------------------------------------------------------


def _safe(details: Any, key: str, fallback: Any = "") -> Any:
    value = details.get(key) if isinstance(details, dict) else None
    return fallback if value is None else value


def move_text(kind: str, details: Any, because_words: dict[str, str]) -> str | None:
    """One action row as a sentence, its moments as `{{at:ISO}}` tokens; None when it has no
    words here."""
    bare = kind.removeprefix("web.")
    template = MOVE_WORDS.get(bare)
    if template is None:
        return None
    first = _safe(details, "first", {})
    retimed = RETIMED_WORDS if bare == "marathon.retimed" else {}
    because = str(_safe(details, "because"))
    renamed = _safe(details, "renamed", 0)
    fields = {
        "game": _safe(details, "game") or _safe(first, "game") or "a run",
        "was": _moment(_safe(details, "from") or _safe(first, "from")) or "",
        "to": _moment(_safe(details, "to") or _safe(first, "to")) or "",
        "why": retimed.get(because) or because_words.get(because) or because or "the bot",
        "runs": plural(_safe(details, "runs", 0), "run"),
        "added": _safe(details, "added", 0),
        "moved": _safe(details, "moved", 0),
        "dropped": _safe(details, "dropped", 0),
        "renamed": RENAMED_WORDS.format(renamed=renamed) if renamed else "",
        "label": _safe(details, "label") or "its sheet",
        "matched": _safe(details, "matched", 0),
    }
    if "{was}" in template and not (fields["was"] and fields["to"]):
        return None
    return template.format(**fields)


def move_rows(
    actions: Any, *, because_words: dict[str, str], name_of: Any, names: bool
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for one in actions or ():
        kind = str(one["kind"])
        text = move_text(kind, one["details"], because_words)
        if text is None:
            continue
        actor = one["actor_id"]
        found.append(
            {
                "id": one["id"],
                "at": _moment(one["at"]),
                "by_id": str(actor) if actor and names else None,
                "by_name": name_of(int(actor)) if actor and names else None,
                "kind": kind.removeprefix("web.").removeprefix("marathon."),
                "text": text,
                "undone": False,
            }
        )
        if len(found) >= MOVES_LIMIT:
            break
    return found


# --- the whole read ------------------------------------------------------------------------


def _never(_one: Any) -> bool:
    return False


def _always(_one: Any) -> bool:
    return True


def payload(
    marathon: Any,
    runs: Any,
    *,
    now: datetime,
    tz_name: Any,
    writes: bool,
    archived: bool = False,
    phase: str = "",
    phase_word: str = "",
    next_read_at: Any = None,
    channel_login: Any = None,
    twitch: dict[int, str] | None = None,
    youtube: dict[int, Any] | None = None,
    name_of: Any = str,
    marks: Any = (),
    ping_mark: int = 0,
    stale_minutes: int = 0,
    reminds_runs: bool = False,
    reminds_hosts: bool = False,
    run_role: Any = None,
    block_role: Any = None,
    block_speaks: Any = None,
    setup_minutes: int = 0,
    refresh_seconds: int = 30,
    actions: Any = (),
    because_words: dict[str, str] | None = None,
    names: bool = True,
) -> dict[str, Any]:
    rows = list(runs or ())
    plan_from = times_from(marathon)
    writes = bool(writes) and not archived
    days = blocks_of(rows, tz_name)
    keys = day_keys(days, tz_name)
    day_of: dict[Any, str] = {}
    sheet_rows: list[dict[str, Any]] = []
    day_rows: list[dict[str, Any]] = []
    for key, block in zip(keys, days, strict=True):
        first = next((one for one in block if mt._cell(one, "state") == mt.UPCOMING), None)
        after_anchor = False
        for row in block:
            day_of[mt._cell(row, "id")] = key
            people = [
                person_row(one, twitch or {}, youtube or {}, name_of) for one in mt.people_of(row)
            ]
            sheet_rows.append(
                sheet_row(
                    row,
                    day=key,
                    plan_from=plan_from,
                    after_anchor=after_anchor,
                    next_up=row is first,
                    writes=writes,
                    people=people,
                )
            )
            if mt._cell(row, "state") != mt.DROPPED and anchored(row):
                after_anchor = True
        kept = [one for one in block if mt._cell(one, "state") != mt.DROPPED]
        minutes, run_id = drift_of(block, plan_from)
        day_rows.append(
            {
                "key": key,
                "label": day_label(_local_date(plan_of(block[0]), tz_name)),
                "starts_at": _iso(plan_of(block[0])),
                "runs": len(kept),
                "baf": len([one for one in kept if has_baf(one)]),
                "upcoming": len([one for one in kept if mt._cell(one, "state") == mt.UPCOMING]),
                "drift_minutes": minutes,
                "drift_run_id": run_id,
                "staff_times": 0,
                "staff_estimates": 0,
                "can_shift": False,
                "can_reset": False,
            }
        )
    posts: list[dict[str, Any]] = []
    if not archived:
        common = {
            "marks": marks,
            "ping_mark": ping_mark,
            "stale_minutes": stale_minutes,
            "now": now,
        }
        if reminds_runs:
            posts += run_posts(rows, day_of, run_role=run_role or _never, **common)
        if reminds_hosts:
            posts += host_posts(
                marathon,
                rows,
                day_of,
                block_role=block_role or _never,
                block_speaks=block_speaks or _always,
                **common,
            )
    posts.sort(key=lambda one: (one["at"] or "", one["kind"], one["run_id"]))
    source = mt._cell(marathon, "source")
    return {
        "marathon": {
            "id": mt._cell(marathon, "id"),
            "name": mt._cell(marathon, "name"),
            "source": source,
            "source_word": SOURCE_WORDS.get(source, source),
            "schedule_page": schedule_page(source, mt._cell(marathon, "source_ref"))
            or mt._cell(marathon, "schedule_url"),
            "phase": ARCHIVED if archived else phase,
            "phase_word": ARCHIVED if archived else phase_word,
            "last_fetched_at": _moment(mt._cell(marathon, "last_fetched_at")),
            "next_read_at": None if archived else _moment(next_read_at),
            "channel_login": channel_login or None,
            "watch_url": twitch_url(channel_login),
            "archived": bool(archived),
        },
        "editable": False,
        "kind": kind_of(marathon),
        "moves_by": MOVES_BY_MARKS,
        "times_from": plan_from,
        "times_from_word": TIMES_FROM_WORDS[plan_from],
        "timezone": str(tz_name or "UTC"),
        "now": _iso(now),
        "refresh_seconds": int(refresh_seconds),
        "setup_minutes": int(setup_minutes),
        "heads_up_minutes": min((int(one) for one in marks), default=int(ping_mark)),
        "today": today_of(days, keys),
        "days": day_rows,
        "rows": sheet_rows,
        "next_posts": posts,
        "moves": move_rows(
            actions, because_words=because_words or {}, name_of=name_of, names=names
        ),
        "undo": {"available": False, "text": None},
    }


__all__ = [
    "KIND_CLOCK_KEPT",
    "KIND_TRACKER",
    "MOVE_KINDS",
    "MOVES_LIMIT",
    "blocks_of",
    "can_of",
    "channels_of",
    "day_keys",
    "drift_of",
    "from_of",
    "host_posts",
    "kind_of",
    "lead_words",
    "move_rows",
    "move_text",
    "payload",
    "pending",
    "person_row",
    "plan_of",
    "run_posts",
    "sheet_row",
    "start_of",
    "times_from",
    "today_of",
    "twitch_url",
    "youtube_url",
]
