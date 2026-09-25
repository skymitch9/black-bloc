from __future__ import annotations

from typing import Any, NamedTuple

from .marathon import MarathonMove, _cell, ours, people_of
from .settings_store import MARATHON_EVENT_MODES

NONE = "none"
MARATHON = "marathon"
RUNS = "runs"
BOTH = "both"
MODES = MARATHON_EVENT_MODES
MODE_WORDS = {
    NONE: "No event",
    MARATHON: "One event for the marathon",
    RUNS: "An event per run of ours",
    BOTH: "Both",
}
LEGACY_YES = ("yes", "y", "true", "on", "1")
LEGACY_NO = ("no", "n", "false", "off", "0")

RUN_DROPPED = "run_dropped"
NOT_OURS = "not_ours"
MODE_CHANGED = "mode_changed"
MARATHON_REMOVED = "marathon_removed"
CANCEL_REASONS = (RUN_DROPPED, NOT_OURS, MODE_CHANGED, MARATHON_REMOVED)

BAD_MODE = (
    "**{given}** is not an event mode, so nothing was changed. Say none, marathon, runs or both."
)
MODE_SET = "**{name}** now makes {words}."
FEED_MODE_SET = "The marathons **{name}** adds now make {words}."
MODE_SAME = "**{name}** already makes {words}, so nothing was changed."
MODE_SENTENCES = {
    NONE: "no event",
    MARATHON: "one event for the whole marathon",
    RUNS: "one event per run of ours, kept in step with the schedule",
    BOTH: "one event for the marathon and one per run of ours",
}
RUN_EVENTS_MADE = "{count} run event(s) made."
RUN_EVENTS_CANCELLED = "{count} run event(s) called off."
RUN_EVENTS_KEPT = "{count} run event(s) left on the calendar."
RUN_EVENT_LINE = "event **#{event_id}** — {status}"
RUN_EVENT_MADE = "**{game}** has its own event now, **#{event_id}**."
RUN_EVENT_ALREADY = "**{game}** already has event **#{event_id}**, so nothing was made."
RUN_EVENT_NOT_OURS = "Nobody from here is on **{game}**, so it gets no event of its own."
RUN_EVENT_NO_TIME = (
    "**{game}** has no time on the schedule yet, so there is nothing to date an event by."
)
RUN_EVENT_NOT_MADE = "The event for **{game}** was not made: {why}"
RUN_EVENT_UNLINKED = (
    "**{game}** no longer carries event **#{event_id}**. The event itself was not touched."
)
RUN_EVENT_NONE = "**{game}** carries no event, so there was nothing to unlink."
EVENT_MODE_LINE = "Event mode: **{words}**"
ADD_EVENT_LABEL = "Event: none / marathon / runs / both"
MODE_PICK = "Event mode…"
PICK_MODE = "Pick what this marathon makes…"
FEED_MODE_PICK = "Pick what this feed's marathons make…"
FEED_MODE_LINE = "Its marathons make: **{words}**"
FEED_MODE_DEFAULT = "{words} (the setting's)"
FEED_MODE_FOLLOW_LABEL = "Whatever the setting says"
RENAME_FEED = "Rename…"
MOVE_FEED = "Move to channel…"
RENAME_TITLE = "Rename the feed"
RENAME_LABEL = "Name"
PICK_FEED_CHANNEL = "Pick the channel it belongs to…"
UNLINK_RUN_EVENT = "unlink_run_event"
MAKE_RUN_EVENT = "make_run_event"
UNLINK_RUN_EVENT_MOVE = MarathonMove(UNLINK_RUN_EVENT, "Unlink", row=3)
MAKE_RUN_EVENT_MOVE = MarathonMove(MAKE_RUN_EVENT, "Make it now", row=3)
FEED_RENAME = "feed_rename"
FEED_MOVE_CHANNEL = "feed_move_channel"
FEED_RENAME_MOVE = MarathonMove(FEED_RENAME, RENAME_FEED, row=3)
FEED_MOVE_MOVE = MarathonMove(FEED_MOVE_CHANNEL, MOVE_FEED, row=3)


class RunEventWords(NamedTuple):
    title: str
    description: str


def clean_mode(given: Any) -> str | None:
    text = str(given or "").strip().lower()
    return text if text in MODES else None


def wanted_mode_answer(given: Any) -> str | None:
    """The Add modal's fifth field: a mode word, or yes / no for one release."""
    text = str(given or "").strip().lower()
    if text in MODES:
        return text
    if text in LEGACY_YES:
        return MARATHON
    if text in LEGACY_NO:
        return NONE
    return None


def mode_of(row: Any) -> str:
    return clean_mode(_cell(row, "event_mode")) or NONE


def makes_marathon_event(mode: Any) -> bool:
    return clean_mode(mode) in (MARATHON, BOTH)


def makes_run_events(mode: Any) -> bool:
    return clean_mode(mode) in (RUNS, BOTH)


def with_marathon_event(mode: Any, on: bool) -> str:
    runs = makes_run_events(mode)
    if on:
        return BOTH if runs else MARATHON
    return RUNS if runs else NONE


def mode_words(mode: Any) -> str:
    return MODE_SENTENCES.get(clean_mode(mode) or NONE, MODE_SENTENCES[NONE])


def waiting(row: Any) -> bool:
    """The wish that replaced `event_wanted`: the mode asks for the marathon's event and it
    has none yet."""
    return makes_marathon_event(mode_of(row)) and not _cell(row, "event_id")


def member_names(row: Any, names: dict[int, str] | None = None) -> str:
    found = []
    for person in ours(people_of(row)):
        user_id = int(person["user_id"])
        found.append((names or {}).get(user_id) or str(person.get("name") or user_id))
    return " & ".join(dict.fromkeys(found))


def run_event_fields(row: Any, marathon: Any, names: dict[int, str] | None = None) -> dict:
    return {
        "member": member_names(row, names),
        "game": str(_cell(row, "game") or ""),
        "category": str(_cell(row, "category") or ""),
        "marathon": str(_cell(marathon, "name") or ""),
    }


def run_logins(row: Any) -> list[str]:
    return [str(one["login"]) for one in ours(people_of(row)) if one.get("login")]


def run_event_line(event_id: Any, status: Any) -> str:
    return RUN_EVENT_LINE.format(event_id=int(event_id), status=status or "gone")


def run_event_moves(row: Any) -> tuple[MarathonMove, ...]:
    if _cell(row, "event_id"):
        return (UNLINK_RUN_EVENT_MOVE,)
    from .marathon import DROPPED, is_ours

    if is_ours(row) and _cell(row, "state") != DROPPED and _cell(row, "scheduled_at"):
        return (MAKE_RUN_EVENT_MOVE,)
    return ()


__all__ = [
    "BOTH",
    "MARATHON",
    "MODES",
    "NONE",
    "RUNS",
    "clean_mode",
    "makes_marathon_event",
    "makes_run_events",
    "mode_of",
    "run_event_fields",
    "waiting",
    "wanted_mode_answer",
    "with_marathon_event",
]
