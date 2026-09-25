from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, NamedTuple

from .golive import parse_ts
from .marathon_sources import COMMENTATOR, GDQ, HOST, RUNNER, Run, event_url, utc_iso
from .settings_store import (
    MARATHON_PART_COMMENTATOR_KEY,
    MARATHON_PART_HOST_KEY,
    MARATHON_PART_RUNNER_KEY,
    MARATHON_STATE_DONE_KEY,
    MARATHON_STATE_DROPPED_KEY,
    MARATHON_STATE_LIVE_KEY,
    MARATHON_STATE_UPCOMING_KEY,
    marathon_marks,
)
from .timezones import unix

BAF = "BaF"

UPCOMING = "upcoming"
LIVE = "live"
DONE = "done"
DROPPED = "dropped"
RUN_STATES = (UPCOMING, LIVE, DONE, DROPPED)
BY_TITLE = "title"
BY_SCHEDULE = "schedule"
BY_STAFF = "staff"

FAR = "far"
NEAR = "near"
ON = "live"
OVER = "over"
PAUSED = "paused"
PHASES = (FAR, NEAR, ON, OVER, PAUSED)
PHASE_WORDS = {
    FAR: "far off",
    NEAR: "coming up",
    ON: "on now",
    OVER: "over",
    PAUSED: "paused",
}
AFTER_END = timedelta(days=1)
TITLE_REACH = timedelta(hours=12)
NAME_FLOOR = 3

PART_KEYS = {
    RUNNER: MARATHON_PART_RUNNER_KEY,
    HOST: MARATHON_PART_HOST_KEY,
    COMMENTATOR: MARATHON_PART_COMMENTATOR_KEY,
}
STATE_KEYS = {
    UPCOMING: MARATHON_STATE_UPCOMING_KEY,
    LIVE: MARATHON_STATE_LIVE_KEY,
    DONE: MARATHON_STATE_DONE_KEY,
    DROPPED: MARATHON_STATE_DROPPED_KEY,
}
PART_ORDER = (RUNNER, HOST, COMMENTATOR)
MESSAGE_LIMIT = 2000
TWITCH_URL = "https://twitch.tv/{login}"

PANEL_TITLE = "Marathons"
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /event again"
OURS_NEXT = f"**{BAF} next**"
MY_RUNS = "**My runs**"
NOTHING_NEXT = f"Nobody from {BAF} is on a schedule that is coming up."
NOTHING_MINE = "You are not on any schedule Black Bloc follows."
NEXT_LINE = "<t:{unix}:R> · **{game}** — {member} {part} · {marathon}"
MARATHON_LINE = "**{name}** · {phase} · {dates} · {ours} " + BAF + " of {runs} · {read}"
NO_DATES = "dates not published"
CARD_HEAD = "{phase} · {dates}"
CARD_SCHEDULE = "**Schedule:** [{source}]({url}) · {read} · {next} · {counts}"
NEXT_READ = "next read <t:{unix}:R>"
NEXT_READ_PAUSED = "paused — not read until it is resumed"
CARD_COUNTS = "{runs} run(s), {ours} " + BAF
CARD_RUNS = "**Runs**"
CARD_EVENT = "**Event**"
CARD_CHANNEL = "**Channel:** {channel}"
CARD_NO_CHANNEL = "none — each run links its runner"
CARD_POSTS = "**Posts:** {board}"
CARD_BOARD_UP = "the board is up in <#{channel}>"
CARD_BOARD_NONE = "no board yet"
READ_AGO = "last read <t:{unix}:R>"
NEVER_READ = "not read yet"
FETCH_TROUBLE = "could not be read since <t:{unix}:f> — {why}"
MODE_LINE = "Marathon posts are **{mode}**."
NO_MARATHONS = (
    "Black Bloc follows no marathon schedule yet. Staff add one with **Add a marathon…**."
)
PICK_MARATHON = "Pick a marathon to manage…"
PICK_UNMATCHED = "Pick a name from this schedule…"
PICK_MEMBER = "…then the member it is"
ADD_TITLE = "Add a marathon"
ADD_NAME = "Name"
ADD_URL = "Schedule link (GDQ)"
ADD_LOGIN = "Twitch channel it airs on — blank for none"
ADD_NAME_HINT = "AGDQ 2027"
ADD_URL_HINT = "https://gamesdonequick.com/schedule/74"
ADD_LOGIN_HINT = "gamesdonequick"
REMOVE_QUESTION = (
    "Remove **{name}**? Its runs and pairings go with it and its ping window closes. Posts already "
    "made stay where they are."
)
REMOVED = "**{name}** is off the list, with its runs and pairings."
ADDED = "**{name}** is on the list. {read}"
READ_NOW = "Its schedule has {runs} run(s), {ours} of them " + BAF + "."
PAUSED_NOW = "**{name}** is paused — nothing is read or posted until it is resumed."
RESUMED_NOW = "**{name}** is being read again."
REFRESHED = "**{name}** was read just now: {runs} run(s), {ours} of them " + BAF + "."
REFRESH_FAILED = "**{name}** could not be read just now — {why}. Every run is kept as it was."
BOARD_POSTED = "The board for **{name}** is up to date."
BOARD_NOT_POSTED = "The board for **{name}** was not posted — {why}."
PAIRED = "**{runner}** on this schedule is {member} from now on."
PAIRED_EVERYWHERE = "**{runner}** on every schedule is {member} from now on."
UNPAIRED = "**{runner}** is no longer paired — the automatic match decides again."
SHOUTED = "The shoutout for **{game}** is out."
SHOUT_NOT_POSTED = "The shoutout for **{game}** was not posted — {why}."
MARKED_DONE = "**{game}** is marked done."
NO_SUCH_MARATHON = "Black Bloc follows no marathon **{given}** here, so nothing was done."
NO_SUCH_RUN = "That run is not on **{name}**'s schedule any more, so nothing was done."
NO_SUCH_PAIRING = "That pairing is gone already, so nothing was changed."
NOT_SHOUTABLE = (
    "**{game}** is {state} or has its shoutout already, so nothing was posted. Only a "
    + BAF
    + " run that is coming up or on now without a shoutout can be shouted by hand."
)
NOT_OURS = (
    "Nobody from " + BAF + " is on **{game}**, so there is nobody to shout. Pair a name first."
)
ALREADY_DONE = "**{game}** is already {state}, so nothing was changed."
NO_NAME = "A marathon needs a name, so nothing was added."
NO_RUNNER = "Pick or type the name as the schedule writes it, so nothing was paired."
NO_MEMBER = "Pick the member that name is, so nothing was paired."
NO_SUCH_CHANNEL = (
    "**{login}** is not one of the channels on the Go-live page, so nothing was changed. Add the "
    "channel there first, or leave it blank."
)
BAD_POLL = "A marathon's own read gap is 10 to 120 minutes, or blank for the setting's."
SITE_BUTTON = "Open the Events page"
NEXT_ADDED_LINE = "Added — see **{name}** on the list."
NEXT_NOT_YET = (
    "Black Bloc has not looked up the next GDQ event for this one yet. **Look again** asks the "
    "tracker now."
)
NEXT_DISMISSED_LINE = "Dismissed — **Look again** asks the tracker once more."
NEXT_ALREADY = "**{next}** is already on the list as **{name}**, so there is nothing to add."
NOT_GDQ = "**{name}** is not a GDQ marathon, so there is no next GDQ event to look up."
NOT_OVER = (
    "**{name}** is not over yet, so nothing was looked up. The next GDQ event is suggested once "
    "it ends."
)
NOTHING_SUGGESTED = (
    "**{name}** has no next event waiting, so nothing was changed. **Look again** asks the "
    "tracker."
)
SUGGESTION_MOVED = (
    "That is not the suggestion waiting on **{name}** any more, so nothing was changed. Open "
    "/event ▸ Marathons… or the Events page for the current one."
)
LOOK_FAILED = (
    "The GDQ tracker could not be read just now — {why}. The suggestion is kept as it was."
)
NEXT_DISMISSED = (
    "**{next}** is dismissed for **{name}**. **Look again** asks the tracker once more."
)
RUN_RESET = "**{game}** is coming up again. Reminders already sent stay sent."
RUN_MARKED_LIVE = "**{game}** is on now, marked by staff."
NOT_RESETTABLE = (
    "**{game}** is {state}, so nothing was changed. Only a done run can be marked coming up again."
)
NOT_LIVEABLE = (
    "**{game}** is {state}, so nothing was changed. Only a run coming up or done can be marked "
    "live."
)
POLL_TITLE = "Re-read every…"
POLL_LABEL = "Minutes between reads — blank for the default"
POLL_HINT = "30"
POLL_SAVED = "**{name}** is re-read every {minutes} minutes while it is near."
POLL_CLEARED = "**{name}** is re-read on the marathon_poll_minutes gap again."
PICK_RUN = "Pick a run to move…"
NEXT_BUTTON_ADD = "Add it"
NEXT_BUTTON_DISMISS = "Not this one"
NEXT_BUTTON_LOOK = "Look again"
MOVED_WORDS = "moved from <t:{unix}:t>"
EVENT_LINE = "Event **#{event_id}** — {status}"
EVENT_WAITING_LINE = "Event: waiting for the schedule — made the moment it has dates"
EVENT_NONE_LINE = "Event: none — **Make an event now** puts one into the events review"
EVENT_GONE = "gone"
EVENT_MADE = "**{name}** is in the events review as event **#{event_id}**."
EVENT_WAITING = (
    "**{name}** has no dates yet, so its event waits for the schedule — it goes into the events "
    "review the moment GDQ publishes one."
)
EVENT_ALREADY = (
    "**{name}** already carries event **#{event_id}**, so nothing was made. **Unlink** it first "
    "to make another."
)
EVENT_NOT_MADE = "The event was not made: {why}"
EVENT_NOBODY = (
    "nobody is left to propose it as — whoever added the marathon is not on the server. Press "
    "**Make an event now** yourself."
)
EVENT_UNLINKED = (
    "**{name}** no longer carries event **#{event_id}**. The event itself was not touched."
)
EVENT_STOPPED_WAITING = "**{name}** no longer waits to make an event."
NO_EVENT = "**{name}** carries no event, so there was nothing to unlink."
MARATHON_OF_EVENT = "Marathon: **{name}** — {ours} " + BAF + " run(s)"
RUN_OF_EVENT = "Marathon run: **{game}** on **{name}**"
EVENT_MODES_WITH_ONE = ("marathon", "both")
BAD_ADD_EVENT = (
    "Say none, marathon, runs or both for what it makes in the events, so nothing was added."
)

ADD = "add"
REFRESH = "refresh"
PAUSE = "pause"
RESUME = "resume"
BOARD = "board"
REMOVE = "remove"
PAIR = "pair"
LOGS = "logs"
BACK = "back"
EVENTS = "events"
MINE = "mine"
NEXT = "next"
POLL = "poll"
ADD_NEXT = "add_next"
DISMISS_NEXT = "dismiss_next"
LOOK_AGAIN = "look_again"
SHOUT = "shout"
MARK_DONE = "mark_done"
MARK_UPCOMING = "mark_upcoming"
MARK_LIVE = "mark_live"
MAKE_EVENT = "make_event"
UNLINK_EVENT = "unlink_event"
FEEDS = "feeds"


class MarathonMove(NamedTuple):
    action: str
    label: str
    style: str = "secondary"
    row: int = 2


ADD_MOVE = MarathonMove(ADD, "Add a marathon…", "primary", 2)
MINE_MOVE = MarathonMove(MINE, "My runs", row=2)
REFRESH_ROOT_MOVE = MarathonMove(REFRESH, "Refresh", row=2)
LOGS_MOVE = MarathonMove(LOGS, "Logs", row=2)
READ_MOVE = MarathonMove(REFRESH, "Read it now", "primary", 2)
PAUSE_MOVE = MarathonMove(PAUSE, "Pause", row=2)
RESUME_MOVE = MarathonMove(RESUME, "Resume", row=2)
BOARD_POST_MOVE = MarathonMove(BOARD, "Post the board", row=2)
BOARD_REFRESH_MOVE = MarathonMove(BOARD, "Refresh the board", row=2)
REMOVE_MOVE = MarathonMove(REMOVE, "Remove", "danger", 3)
PAIR_MOVE = MarathonMove(PAIR, "Pair a runner…", row=3)
BACK_MOVE = MarathonMove(BACK, "Back", row=4)
EVENTS_MOVE = MarathonMove(EVENTS, "Back", row=4)
NEXT_MOVE = MarathonMove(NEXT, "Next up…", row=3)
POLL_MOVE = MarathonMove(POLL, POLL_TITLE, row=3)
ADD_NEXT_MOVE = MarathonMove(ADD_NEXT, NEXT_BUTTON_ADD, "primary", 2)
DISMISS_NEXT_MOVE = MarathonMove(DISMISS_NEXT, NEXT_BUTTON_DISMISS, row=2)
LOOK_AGAIN_MOVE = MarathonMove(LOOK_AGAIN, NEXT_BUTTON_LOOK, row=2)
SHOUT_MOVE = MarathonMove(SHOUT, "Shout it now", "primary", 2)
MARK_DONE_MOVE = MarathonMove(MARK_DONE, "Mark done", row=2)
MARK_UPCOMING_MOVE = MarathonMove(MARK_UPCOMING, "Mark it upcoming", row=2)
MARK_LIVE_MOVE = MarathonMove(MARK_LIVE, "Mark it live", row=2)
MAKE_EVENT_MOVE = MarathonMove(MAKE_EVENT, "Make an event now", row=3)
UNLINK_EVENT_MOVE = MarathonMove(UNLINK_EVENT, "Unlink the event", row=3)
FEEDS_MOVE = MarathonMove(FEEDS, "Feeds…", row=3)


def root_moves(*, staff: bool) -> tuple[MarathonMove, ...]:
    return (
        (ADD_MOVE, MINE_MOVE, REFRESH_ROOT_MOVE, LOGS_MOVE, FEEDS_MOVE, EVENTS_MOVE)
        if staff
        else (MINE_MOVE, REFRESH_ROOT_MOVE, EVENTS_MOVE)
    )


def card_moves(
    marathon: Any, *, has_unmatched: bool, has_next: bool = False
) -> tuple[MarathonMove, ...]:
    """Only moves that change something are drawn: Pause or Resume, Post or Refresh the board."""
    active = bool(_cell(marathon, "active", 1))
    found = [READ_MOVE] if active else []
    found.append(PAUSE_MOVE if active else RESUME_MOVE)
    found.append(BOARD_REFRESH_MOVE if _cell(marathon, "board_message_id") else BOARD_POST_MOVE)
    found.append(REMOVE_MOVE)
    if has_unmatched:
        found.append(PAIR_MOVE)
    if has_next:
        found.append(NEXT_MOVE)
    found.append(POLL_MOVE)
    found.append(event_move(marathon))
    found.append(BACK_MOVE)
    return tuple(found)


def wants_its_event(marathon: Any) -> bool:
    return str(_cell(marathon, "event_mode") or "none") in EVENT_MODES_WITH_ONE


def event_move(marathon: Any) -> MarathonMove:
    """Staff final say both ways: a linked or waiting marathon unlinks, a bare one makes one."""
    if _cell(marathon, "event_id") or wants_its_event(marathon):
        return UNLINK_EVENT_MOVE
    return MAKE_EVENT_MOVE


def event_line(marathon: Any, status: Any) -> str:
    event_id = _cell(marathon, "event_id")
    if event_id:
        return EVENT_LINE.format(event_id=int(event_id), status=status or EVENT_GONE)
    if wants_its_event(marathon):
        return EVENT_WAITING_LINE
    return EVENT_NONE_LINE


def next_moves(record: Any, *, over: bool) -> tuple[MarathonMove, ...]:
    found: list[MarathonMove] = []
    if next_state(record) == NEXT_OPEN:
        found += [ADD_NEXT_MOVE, DISMISS_NEXT_MOVE]
    if over:
        found.append(LOOK_AGAIN_MOVE)
    found.append(BACK_MOVE)
    return tuple(found)


def run_moves(row: Any) -> tuple[MarathonMove, ...]:
    state = _cell(row, "state")
    found: list[MarathonMove] = []
    if is_ours(row) and state in (UPCOMING, LIVE) and not _cell(row, "shout_message_id"):
        found.append(SHOUT_MOVE)
    if can_mark_live(row):
        found.append(MARK_LIVE_MOVE)
    if state in (UPCOMING, LIVE):
        found.append(MARK_DONE_MOVE)
    if can_mark_upcoming(row):
        found.append(MARK_UPCOMING_MOVE)
    found.append(BACK_MOVE)
    return tuple(found)


def can_mark_upcoming(row: Any) -> bool:
    return _cell(row, "state") == DONE


def can_mark_live(row: Any) -> bool:
    return _cell(row, "state") in (UPCOMING, DONE)


def held(row: Any) -> bool:
    """Staff put this run where it is: the title never moves it, only the clock's end does."""
    return _cell(row, "live_because") == BY_STAFF and _cell(row, "state") in (UPCOMING, LIVE)


def _cell(row: Any, key: str, fallback: Any = None) -> Any:
    if row is None:
        return fallback
    if isinstance(row, dict):
        return row.get(key, fallback)
    try:
        return row[key]
    except (IndexError, KeyError):
        return fallback


def people_of(row: Any) -> list[dict[str, Any]]:
    raw = _cell(row, "people")
    if isinstance(raw, list):
        return [dict(one) for one in raw if isinstance(one, dict)]
    try:
        found = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    return [one for one in found if isinstance(one, dict)] if isinstance(found, list) else []


def marks_of(row: Any) -> list[int]:
    raw = _cell(row, "reminders_sent")
    try:
        found = json.loads(raw or "[]") if not isinstance(raw, list) else raw
    except (TypeError, ValueError):
        return []
    return sorted({int(one) for one in found if isinstance(one, int)}) if found else []


# --- matching ---------------------------------------------------------------------------------


def runner_key(name: Any) -> str:
    return " ".join(str(name or "").split()).lower()


def match_people(
    people: Any,
    links: dict[str, int],
    pairings: Any,
    *,
    marathon_id: Any = None,
    match_hosts: bool = True,
    usernames: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Staff pairings first, then the member's Twitch link, then — only for a name the schedule
    gave no link for — a member whose Discord username is exactly that name."""
    here: dict[str, int] = {}
    everywhere: dict[str, int] = {}
    for row in pairings or ():
        name = runner_key(_cell(row, "runner_name"))
        owner = _cell(row, "marathon_id")
        target = everywhere if owner is None else here
        if owner is None or marathon_id is None or int(owner) == int(marathon_id):
            target[name] = int(_cell(row, "user_id"))
    lowered = {str(login).lower(): int(user) for login, user in (links or {}).items()}
    named = {runner_key(name): int(user) for name, user in (usernames or {}).items()}
    found: list[dict[str, Any]] = []
    for person in people or ():
        name = str(_cell(person, "name") if isinstance(person, dict) else person.name)
        login = _cell(person, "login") if isinstance(person, dict) else person.login
        part = str(_cell(person, "part") if isinstance(person, dict) else person.part)
        user_id: int | None = None
        if part == RUNNER or match_hosts:
            key = runner_key(name)
            user_id = here.get(key) or everywhere.get(key)
            if user_id is None and login:
                user_id = lowered.get(str(login).lower())
            if user_id is None and not login:
                user_id = named.get(key)
        found.append({"name": name, "login": login, "part": part, "user_id": user_id})
    return found


def ours(people: Any) -> list[dict[str, Any]]:
    """The people of ours on a run, one line per member, the runner part first."""
    kept: dict[int, dict[str, Any]] = {}
    for person in sorted(
        (one for one in people or () if one.get("user_id")),
        key=lambda one: PART_ORDER.index(one["part"]) if one["part"] in PART_ORDER else 9,
    ):
        kept.setdefault(int(person["user_id"]), person)
    return list(kept.values())


def is_ours(row: Any) -> bool:
    return bool(ours(people_of(row)))


def unmatched_names(runs: Any) -> list[str]:
    seen: dict[str, str] = {}
    for run in runs or ():
        for person in people_of(run):
            if not person.get("user_id"):
                seen.setdefault(runner_key(person.get("name")), str(person.get("name") or ""))
    return sorted((name for name in seen.values() if name), key=str.lower)


# --- the diff ---------------------------------------------------------------------------------


@dataclass
class Plan:
    inserts: list[Run] = field(default_factory=list)
    updates: list[tuple[Any, Run, bool]] = field(default_factory=list)
    dropped: list[Any] = field(default_factory=list)
    reappeared: list[Any] = field(default_factory=list)

    @property
    def moved(self) -> list[tuple[Any, Run, bool]]:
        return [one for one in self.updates if one[2]]


def moved_by(before: Any, after: Any) -> float | None:
    old, new = parse_ts(before), parse_ts(after)
    if old is None or new is None:
        return None
    return abs((new - old).total_seconds()) / 60


def diff(rows: Any, runs: list[Run], *, move_minutes: int) -> Plan:
    """By external id: new rows in, moved ones flagged, missing ones dropped, never deleted."""
    known = {str(_cell(row, "external_id")): row for row in rows or ()}
    plan = Plan()
    seen: set[str] = set()
    for run in runs:
        seen.add(run.external_id)
        row = known.get(run.external_id)
        if row is None:
            plan.inserts.append(run)
            continue
        shift = moved_by(_cell(row, "scheduled_at"), run.starts_at)
        plan.updates.append((row, run, shift is not None and shift >= int(move_minutes)))
        if _cell(row, "state") == DROPPED:
            plan.reappeared.append(row)
    for external_id, row in known.items():
        if external_id not in seen and _cell(row, "state") not in (DROPPED, DONE):
            plan.dropped.append(row)
    return plan


def schedule_hash(runs: list[Run]) -> str:
    shape = [
        [one.external_id, one.order, one.game, one.category, one.starts_at, one.ends_at]
        + [[p.name, p.login, p.part] for p in one.people]
        for one in runs
    ]
    return hashlib.sha256(
        json.dumps(shape, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def span(runs: list[Run]) -> tuple[str | None, str | None]:
    starts = sorted(one.starts_at for one in runs if one.starts_at)
    ends = sorted(one.ends_at or one.starts_at for one in runs if one.ends_at or one.starts_at)
    return (starts[0] if starts else None, ends[-1] if ends else None)


# --- when a marathon is read ------------------------------------------------------------------


def phase(marathon: Any, now: datetime, *, lead_days: int) -> str:
    if not bool(_cell(marathon, "active", 1)):
        return PAUSED
    starts = parse_ts(_cell(marathon, "starts_at"))
    ends = parse_ts(_cell(marathon, "ends_at")) or starts
    if starts is None:
        return FAR
    if now < starts - timedelta(days=int(lead_days)):
        return FAR
    if now < starts:
        return NEAR
    if ends is not None and now > ends:
        return OVER
    return ON


def is_near(marathon: Any, now: datetime, *, lead_days: int) -> bool:
    found = phase(marathon, now, lead_days=lead_days)
    if found in (NEAR, ON):
        return True
    if found != OVER:
        return False
    ends = parse_ts(_cell(marathon, "ends_at")) or parse_ts(_cell(marathon, "starts_at"))
    return ends is not None and now <= ends + AFTER_END


def next_read_at(
    marathon: Any, now: datetime, *, poll_minutes: int, far_hours: int, lead_days: int
) -> datetime | None:
    if not bool(_cell(marathon, "active", 1)):
        return None
    last = parse_ts(_cell(marathon, "last_fetched_at"))
    if last is None:
        return now
    if is_near(marathon, now, lead_days=lead_days):
        return last + timedelta(minutes=int(_cell(marathon, "poll_minutes") or poll_minutes))
    return last + timedelta(hours=int(far_hours))


def fetch_due(
    marathon: Any, now: datetime, *, poll_minutes: int, far_hours: int, lead_days: int
) -> bool:
    at = next_read_at(
        marathon, now, poll_minutes=poll_minutes, far_hours=far_hours, lead_days=lead_days
    )
    return at is not None and now >= at


def board_due_off(marathon: Any, now: datetime) -> bool:
    ends = parse_ts(_cell(marathon, "ends_at"))
    return ends is not None and now > ends + AFTER_END


def window_bounds(marathon: Any, slack_hours: int) -> tuple[str, str] | None:
    starts = parse_ts(_cell(marathon, "starts_at"))
    ends = parse_ts(_cell(marathon, "ends_at")) or starts
    if starts is None or ends is None:
        return None
    slack = timedelta(hours=int(slack_hours))
    return ((starts - slack).isoformat(), (ends + slack).isoformat())


# --- the live title ---------------------------------------------------------------------------

PUNCTUATION = re.compile(r"[^\w\s]+", re.UNICODE)


def normalise(text: Any) -> str:
    return " ".join(PUNCTUATION.sub(" ", str(text or "").lower()).split())


def _contains(haystack: str, needle: str) -> bool:
    return bool(needle) and len(needle) >= NAME_FLOOR and f" {needle} " in f" {haystack} "


def title_hit(title: Any, game: Any, runs: Any, now: datetime) -> Any:
    """The run the stream is showing: a game name in the title, or the stream's category equal
    to the run's Twitch game; a runner's name breaks a tie, then the nearest scheduled time."""
    said = normalise(title)
    category = normalise(game)
    best: tuple[int, float] | None = None
    found = None
    for row in runs or ():
        if _cell(row, "state") in (DONE, DROPPED):
            continue
        at = parse_ts(_cell(row, "scheduled_at"))
        if at is None or abs(at - now) > TITLE_REACH:
            continue
        names = {
            normalise(_cell(row, "game")),
            normalise(_cell(row, "display_name")),
            normalise(_cell(row, "twitch_game")),
        }
        named = any(_contains(said, one) for one in names)
        same_game = bool(category) and category == normalise(_cell(row, "twitch_game"))
        if not (named or same_game):
            continue
        runner = any(
            _contains(said, normalise(person.get("name")))
            for person in people_of(row)
            if person.get("part") == RUNNER
        )
        score = (int(named) * 2 + int(runner), -abs((at - now).total_seconds()))
        if best is None or score > best:
            best, found = score, row
    return found


# --- states -----------------------------------------------------------------------------------


class Change(NamedTuple):
    row: Any
    to: str
    because: str
    skipped: bool = False


def _when(row: Any) -> tuple[datetime, int]:
    at = parse_ts(_cell(row, "scheduled_at")) or datetime.max.replace(tzinfo=UTC)
    return (at, int(_cell(row, "order_no") or 0))


def advance(
    runs: Any, now: datetime, *, hit: Any = None, watching: bool, grace_minutes: int
) -> list[Change]:
    """Every state move one tick makes. `watching` means a live title can confirm runs, so the
    schedule alone waits out the grace; without it the schedule decides at the start time."""
    grace = timedelta(minutes=int(grace_minutes))
    rows = sorted((one for one in runs or () if _cell(one, "state") != DROPPED), key=_when)
    changes: list[Change] = []
    live_now = [one for one in rows if _cell(one, "state") == LIVE]
    if hit is not None:
        hit_at = _when(hit)
        if _cell(hit, "state") != LIVE:
            changes.append(Change(hit, LIVE, BY_TITLE))
        for row in rows:
            if row is hit or _cell(row, "id") == _cell(hit, "id") or held(row):
                continue
            if _cell(row, "state") == LIVE:
                changes.append(Change(row, DONE, BY_TITLE))
            elif _cell(row, "state") == UPCOMING and _when(row) < hit_at:
                changes.append(Change(row, DONE, BY_TITLE, skipped=True))
        return changes
    next_live = None
    for row in rows:
        if _cell(row, "state") != UPCOMING:
            continue
        at = parse_ts(_cell(row, "scheduled_at"))
        ends = parse_ts(_cell(row, "ends_at")) or at
        if at is None or at > now:
            continue
        if ends is not None and now > ends + grace:
            changes.append(Change(row, DONE, BY_SCHEDULE, skipped=True))
            continue
        if watching and now < at + grace:
            continue
        next_live = row
    if next_live is not None:
        changes.append(Change(next_live, LIVE, BY_SCHEDULE))
        for row in rows:
            if row is next_live or held(row):
                continue
            if _cell(row, "state") == LIVE or (
                _cell(row, "state") == UPCOMING
                and _when(row) < _when(next_live)
                and not any(one.row is row for one in changes)
            ):
                changes.append(Change(row, DONE, BY_SCHEDULE, skipped=_cell(row, "state") != LIVE))
        return changes
    for row in live_now:
        ends = parse_ts(_cell(row, "ends_at")) or parse_ts(_cell(row, "scheduled_at"))
        if ends is not None and now > ends + grace:
            changes.append(Change(row, DONE, BY_SCHEDULE))
    return changes


# --- reminders --------------------------------------------------------------------------------


def reminder_marks(text: Any, ping_minutes: int) -> tuple[int, ...]:
    found = set(marathon_marks(text) or ())
    found.add(int(ping_minutes))
    return tuple(sorted(found, reverse=True))


def due_marks(
    row: Any, marks: Any, now: datetime, *, stale_minutes: int
) -> tuple[int | None, list[int]]:
    """(the one mark to post now, the marks to skip): the latest due mark wins, anything older
    than `stale_minutes` past its moment is skipped and never posted late."""
    if _cell(row, "state") != UPCOMING:
        return (None, [])
    at = parse_ts(_cell(row, "scheduled_at"))
    if at is None:
        return (None, [])
    sent = set(marks_of(row))
    due: list[int] = []
    stale: list[int] = []
    for mark in sorted(set(int(one) for one in marks or ())):
        if mark in sent:
            continue
        moment = at - timedelta(minutes=mark)
        if now < moment:
            continue
        if now - moment > timedelta(minutes=int(stale_minutes)):
            stale.append(mark)
        else:
            due.append(mark)
    if not due:
        return (None, stale)
    return (due[0], stale + due[1:])


def rearmed(sent: Any, new_start: Any, now: datetime) -> list[int]:
    """A run that moved later forgets every mark whose moment is in the future again."""
    at = parse_ts(new_start)
    if at is None:
        return sorted(set(int(one) for one in sent or ()))
    return sorted({int(one) for one in sent or () if at - timedelta(minutes=int(one)) <= now})


# --- the next GDQ event ----------------------------------------------------------------------

NEXT_OPEN = "open"
NEXT_DISMISSED = "dismissed"
NEXT_ADDED = "added"
NEXT_NONE = "none"


def suggestion_of(marathon: Any) -> dict[str, Any] | None:
    raw = _cell(marathon, "suggested_next")
    if isinstance(raw, dict):
        return dict(raw)
    try:
        found = json.loads(raw) if raw else None
    except (TypeError, ValueError):
        return None
    return found if isinstance(found, dict) else None


def next_state(record: Any) -> str | None:
    if not isinstance(record, dict):
        return None
    if record.get("event_id") is None:
        return NEXT_NONE
    if record.get("added_marathon_id"):
        return NEXT_ADDED
    if record.get("dismissed_at"):
        return NEXT_DISMISSED
    return NEXT_OPEN


def suggestion_record(event: dict[str, Any], now: datetime) -> dict[str, Any]:
    return {
        "event_id": str(event["id"]),
        "short": str(event.get("short") or ""),
        "name": " ".join(str(event.get("name") or event.get("short") or event["id"]).split()),
        "datetime": utc_iso(event.get("datetime")),
        "url": event_url(event["id"]),
        "found_at": now.isoformat(),
        "dismissed_at": None,
        "added_marathon_id": None,
    }


def none_record(now: datetime) -> dict[str, Any]:
    return {"event_id": None, "found_at": now.isoformat()}


def is_over(marathon: Any, now: datetime) -> bool:
    ends = parse_ts(_cell(marathon, "ends_at")) or parse_ts(_cell(marathon, "starts_at"))
    return ends is not None and now > ends


def suggests(marathon: Any) -> bool:
    return _cell(marathon, "source") == GDQ


def wants_suggestion(marathon: Any, now: datetime) -> bool:
    """Once per marathon: a GDQ one, active, over, with no record yet — a NULL is the only retry."""
    return (
        suggests(marathon)
        and bool(_cell(marathon, "active", 1))
        and is_over(marathon, now)
        and not _cell(marathon, "suggested_next")
    )


def next_fields(marathon: Any, record: Any) -> dict[str, Any]:
    record = record or {}
    return {
        "marathon": _cell(marathon, "name") or "",
        "next": record.get("name") or "",
        "when": stamp_of(record.get("datetime"), "D"),
        "relative": stamp_of(record.get("datetime"), "R"),
        "url": record.get("url") or "",
    }


# --- words ------------------------------------------------------------------------------------


class Rendered(NamedTuple):
    text: str
    fell_back: bool


def render(template: Any, default: str, **fields: Any) -> Rendered:
    """Checklist 17: a staff template that will not fill falls back to the shipped words."""
    try:
        return Rendered(str(template).format_map(fields), False)
    except Exception:
        return Rendered(default.format_map(fields), True)


def stamp_of(value: Any, style: str) -> str:
    at = parse_ts(value)
    return f"<t:{unix(at)}:{style}>" if at is not None else "—"


def mention_line(people: list[dict[str, Any]]) -> str:
    return ", ".join(f"<@{int(one['user_id'])}>" for one in people)


def member_ids(row: Any) -> list[int]:
    return [int(one["user_id"]) for one in ours(people_of(row))]


def run_url(row: Any, channel_login: Any, fallback: str = "") -> str:
    """The marathon's channel when it has one, else the first of ours with a Twitch login."""
    if channel_login:
        return TWITCH_URL.format(login=channel_login)
    for person in ours(people_of(row)):
        if person.get("login"):
            return TWITCH_URL.format(login=person["login"])
    return fallback


def run_fields(row: Any, marathon: Any, words: dict[str, str], *, url: str) -> dict[str, Any]:
    people = ours(people_of(row))
    part = people[0]["part"] if people else RUNNER
    return {
        "member": mention_line(people),
        "game": _cell(row, "game") or "",
        "category": _cell(row, "category") or "",
        "url": url,
        "marathon": _cell(marathon, "name") or "",
        "part": words.get(PART_KEYS.get(part, MARATHON_PART_RUNNER_KEY), part),
        "when": stamp_of(_cell(row, "scheduled_at"), "f"),
        "relative": stamp_of(_cell(row, "scheduled_at"), "R"),
        "in": stamp_of(_cell(row, "scheduled_at"), "R"),
        "state": words.get(STATE_KEYS.get(str(_cell(row, "state")), ""), _cell(row, "state")),
    }


def board_text(
    marathon: Any,
    rows: Any,
    words: dict[str, str],
    *,
    head: Any,
    head_default: str,
    line: Any,
    line_default: str,
    empty: str,
    url: str,
) -> Rendered:
    mine = sorted((one for one in rows or () if is_ours(one)), key=_when)
    top = render(
        head,
        head_default,
        marathon=_cell(marathon, "name") or "",
        count=len(mine),
        starts=stamp_of(_cell(marathon, "starts_at"), "f"),
        ends=stamp_of(_cell(marathon, "ends_at"), "f"),
        url=url,
    )
    fell_back = top.fell_back
    lines = [top.text]
    for row in mine:
        one = render(line, line_default, **run_fields(row, marathon, words, url=url))
        fell_back = fell_back or one.fell_back
        lines.append(one.text)
    if not mine:
        lines.append(empty)
    kept: list[str] = []
    spent = 0
    for text in lines:
        if spent + len(text) + 1 > MESSAGE_LIMIT:
            break
        kept.append(text)
        spent += len(text) + 1
    return Rendered("\n".join(kept), fell_back)


def next_runs(rows: Any, now: datetime, limit: int = 5) -> list[Any]:
    return sorted(
        (
            one
            for one in rows or ()
            if _cell(one, "state") in (UPCOMING, LIVE)
            and is_ours(one)
            and (parse_ts(_cell(one, "ends_at")) or now) >= now
        ),
        key=_when,
    )[:limit]
