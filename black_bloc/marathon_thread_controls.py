"""The control message pinned in a tracked marathon's thread, shaped by the show's phase."""

from __future__ import annotations

from typing import Any, NamedTuple

from . import marathon as mt
from . import marathon_events as me
from . import marathon_spotlight as ms
from .golive import parse_ts
from .marathon_baf_event import (
    BY_LEADS,
    BY_NAME,
    BY_NO_RUNS,
    CLEAR,
    FOLLOW,
    NO,
    UNSURE,
    YES,
    Judgement,
)

EVENT = "event"
RUNS = "runs"
SPOTLIGHT = "spotlight"
HIGHLIGHT = "highlight"
PING = "ping"
HOSTS = "hosts"
HOST_EVENTS = "hostevents"
ANNOUNCE = "announce"
HOST_ANNOUNCE = "hostannounce"
OVERLAY = "overlay"
BAF = "baf"
ARCHIVE = "archive"
LINK = "link"
ACTIONS = (EVENT, SPOTLIGHT, PING, ANNOUNCE, HOST_ANNOUNCE, BAF, ARCHIVE)
RETIRED = (HOSTS, HOST_EVENTS, RUNS, HIGHLIGHT, OVERLAY)
ON = "on"
OFF = "off"
CANCEL = "cancel"
TEMPLATE = (
    r"marathon:controls:(?P<marathon_id>[0-9]+)"
    r":(?P<action>event|runs|spotlight|highlight|ping|hosts|hostevents|announce|hostannounce"
    r"|overlay|baf|archive)"
    r":(?P<to>on|off|cancel|follow|yes|no|clear)"
)
CUSTOM_ID = "marathon:controls:{marathon_id}:{action}:{to}"
RUNS_GONE = (
    "BaF run/host events left the thread controls: the marathon's drawer on the site and "
    "/event set them. Nothing was changed."
)
OVERLAY_GONE = (
    "Event schedule left the thread controls: the marathon's drawer on the site sets it. "
    "Nothing was changed."
)
HIGHLIGHT_GONE = (
    "Auto-highlight is part of Runner announcements now: a run's highlight follows that switch "
    "and each run's own answer. Nothing was changed."
)

BAF_SAID_YES = "said_yes"
BAF_SAID_NO = "said_no"
BAF_SAID_UNSURE = "said_unsure"
BAF_STAFF_YES = "staff_yes"
BAF_STAFF_NO = "staff_no"
BAF_ANSWERED_YES = "answered_yes"
BAF_ANSWERED_NO = "answered_no"
REASON_NAMED = "named"
REASON_RUNS = "runs"
REASON_NO_RUNS = "no_runs"

SPOT_SWITCHED = (ms.HELD, ms.HELD_OTHER, ms.UNTIL, ms.SCHEDULED, ms.WAITING, ms.DARK)
LINE_UNTIL = "until"
LINE_STARTS = "starts"
LINE_KEPT = "kept"
LINE_NONE = "none"
LINE_RUNNING = "running"
SPOT_RUNNING = (ms.UNTIL, ms.HELD_OTHER)
SPOT_LINES = {
    ms.HELD: LINE_UNTIL,
    ms.HELD_OTHER: LINE_UNTIL,
    ms.UNTIL: LINE_UNTIL,
    ms.SCHEDULED: LINE_STARTS,
    ms.WAITING: LINE_STARTS,
    ms.KEPT: LINE_KEPT,
    ms.NO_CHANNEL: LINE_NONE,
}
LABEL_LIMIT = 80
POSTED_REASON = "Black Bloc: the marathon's controls"
TRACKER_PAGE = "{origin}/schedule.html#marathon-{marathon_id}"


class Control(NamedTuple):
    action: str
    to: str
    word: str
    row: int = 0
    label: str | None = None


def custom_id(marathon_id: Any, action: str, to: str) -> str:
    return CUSTOM_ID.format(marathon_id=int(marathon_id), action=action, to=to)


def wanted_mode(mode: Any, action: str, to: str) -> str:
    """The marathon half moves; the run/host half stays as the drawer or /event left it."""
    marathon_on = me.makes_marathon_event(mode)
    runs_on = me.makes_run_events(mode)
    if action == EVENT:
        marathon_on = to == ON
    if marathon_on and runs_on:
        return me.BOTH
    if marathon_on:
        return me.MARATHON
    return me.RUNS if runs_on else me.NONE


def switch(action: str, on: bool, row: int = 0) -> Control:
    return Control(action, OFF if on else ON, ON if on else OFF, row)


def spot_switch(spot_state: Any, follows: bool) -> tuple[Control, ...]:
    """None while the channel is kept on Go-live or the marathon has no channel."""
    if str(spot_state or "") not in SPOT_SWITCHED:
        return ()
    return (switch(SPOTLIGHT, follows),)


def spot_line(spot_state: Any, follows: bool = True) -> str | None:
    """A spotlight staff or another marathon set, while this one does not follow, says so."""
    if not follows and str(spot_state or "") in SPOT_RUNNING:
        return LINE_RUNNING
    return SPOT_LINES.get(str(spot_state or ""))


def baf_reason(judged: Judgement) -> str:
    if judged.reason == BY_NAME:
        return REASON_NAMED
    if judged.reason == BY_NO_RUNS:
        return REASON_NO_RUNS
    return REASON_RUNS


def baf_control(own: bool | None, followed: Judgement) -> Control:
    """One button: the reading, and its one reverse. A staff answer clears back to follow, a
    Leads answer clears, and what the bot worked out is said the other way."""
    if own is not None:
        return Control(BAF, FOLLOW, ON if own else OFF, 1, BAF_STAFF_YES if own else BAF_STAFF_NO)
    if followed.reason == BY_LEADS:
        yes = followed.answer == YES
        said = BAF_ANSWERED_YES if yes else BAF_ANSWERED_NO
        return Control(BAF, CLEAR, ON if yes else OFF, 1, said)
    if followed.answer == YES:
        return Control(BAF, NO, ON, 1, BAF_SAID_YES)
    if followed.answer == UNSURE:
        return Control(BAF, YES, OFF, 1, BAF_SAID_UNSURE)
    return Control(BAF, YES, OFF, 1, BAF_SAID_NO)


def controls(
    mode: Any,
    spot_state: Any,
    *,
    follows: bool,
    ping: bool,
    announce: bool,
    host_announce: bool,
    baf: Control | None = None,
    over: bool = False,
) -> tuple[Control, ...]:
    """Each button carries the move it makes, so a stale label can never do the opposite."""
    if over:
        return (Control(LINK, "", ""), Control(ARCHIVE, ON, ARCHIVE))
    marathon_on = me.makes_marathon_event(mode)
    return (
        switch(ANNOUNCE, announce),
        switch(HOST_ANNOUNCE, host_announce),
        switch(PING, ping),
        *spot_switch(spot_state, follows),
        switch(EVENT, marathon_on),
        Control(LINK, "", "", 1),
        *((baf,) if baf is not None else ()),
    )


def after_show(marathon: Any, now: Any) -> bool:
    """Only a known end puts the controls in their after-show shape."""
    ends = parse_ts(mt._cell(marathon, "ends_at"))
    return ends is not None and now > ends


def tracker_url(origin: Any, marathon_id: Any) -> str | None:
    """The marathon's Marathon tracker page on the site; None while the site has no address."""
    base = str(origin or "").strip().rstrip("/")
    if not base.startswith(("https://", "http://")):
        return None
    return TRACKER_PAGE.format(origin=base, marathon_id=int(marathon_id))


def label(text: Any) -> str:
    return str(text or "").strip()[:LABEL_LIMIT] or "…"


__all__ = [
    "ACTIONS",
    "CLEAR",
    "Control",
    "FOLLOW",
    "NO",
    "RETIRED",
    "YES",
    "baf_control",
    "baf_reason",
    "after_show",
    "controls",
    "custom_id",
    "label",
    "spot_line",
    "spot_switch",
    "switch",
    "tracker_url",
    "wanted_mode",
]
