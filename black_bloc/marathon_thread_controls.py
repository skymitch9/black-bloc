"""The control message pinned in a tracked marathon's thread: events and the spotlight."""

from __future__ import annotations

from typing import Any, NamedTuple

from . import marathon_events as me
from . import marathon_spotlight as ms
from .marathon_baf_event import CHOICES, FOLLOW, NO, YES

EVENT = "event"
RUNS = "runs"
SPOTLIGHT = "spotlight"
HIGHLIGHT = "highlight"
PING = "ping"
HOSTS = "hosts"
HOST_EVENTS = "hostevents"
ANNOUNCE = "announce"
OVERLAY = "overlay"
BAF = "baf"
ACTIONS = (EVENT, RUNS, SPOTLIGHT, HIGHLIGHT, PING, ANNOUNCE, OVERLAY, BAF)
RETIRED = (HOSTS, HOST_EVENTS)
ON = "on"
OFF = "off"
CANCEL = "cancel"
BAF_CHOICES = CHOICES
BAF_ROW = 4
TEMPLATE = (
    r"marathon:controls:(?P<marathon_id>[0-9]+)"
    r":(?P<action>event|runs|spotlight|highlight|ping|hosts|hostevents|announce|overlay|baf)"
    r":(?P<to>on|off|cancel|follow|yes|no)"
)
CUSTOM_ID = "marathon:controls:{marathon_id}:{action}:{to}"

SPOT_ON = "on"
SPOT_OFF = "off"
SPOT_KEPT = "kept"
SPOT_NONE = "none"
SPOT_WAITING = "waiting"
SPOT_OF_STATE = {
    ms.HELD: SPOT_ON,
    ms.HELD_OTHER: SPOT_ON,
    ms.UNTIL: SPOT_ON,
    ms.SCHEDULED: SPOT_ON,
    ms.KEPT: SPOT_KEPT,
    ms.WAITING: SPOT_WAITING,
    ms.DARK: SPOT_OFF,
    ms.NO_CHANNEL: SPOT_NONE,
}
LABEL_LIMIT = 80
POSTED_REASON = "Black Bloc: the marathon's controls"
BECAUSE_STARTED = "staff_started"
TRACKER_PAGE = "{origin}/schedule.html#marathon-{marathon_id}"


class Control(NamedTuple):
    action: str
    to: str
    word: str
    disabled: bool = False
    row: int | None = None


def custom_id(marathon_id: Any, action: str, to: str) -> str:
    return CUSTOM_ID.format(marathon_id=int(marathon_id), action=action, to=to)


def halves(mode: Any) -> tuple[bool, bool]:
    return (me.makes_marathon_event(mode), me.makes_run_events(mode))


def mode_from(marathon_on: bool, runs_on: bool) -> str:
    if marathon_on and runs_on:
        return me.BOTH
    if marathon_on:
        return me.MARATHON
    if runs_on:
        return me.RUNS
    return me.NONE


def wanted_mode(mode: Any, action: str, to: str) -> str:
    """The new event mode a press asks for: one half moves, the other stays."""
    marathon_on, runs_on = halves(mode)
    if action == EVENT:
        marathon_on = to == ON
    elif action == RUNS:
        runs_on = to == ON
    return mode_from(marathon_on, runs_on)


def spot_word(state: Any) -> str:
    return SPOT_OF_STATE.get(str(state or ""), SPOT_OFF)


def spot_control(spot: str) -> Control:
    if spot == SPOT_WAITING:
        return Control(SPOTLIGHT, CANCEL, spot)
    return Control(
        SPOTLIGHT, ON if spot in (SPOT_OFF, SPOT_NONE) else OFF, spot, disabled=spot == SPOT_NONE
    )


def switch(action: str, on: bool) -> Control:
    return Control(action, OFF if on else ON, ON if on else OFF)


def baf_controls(choice: Any) -> tuple[Control, ...]:
    """The BaF event switch: one button per answer in a row of its own, the one that stands
    lit and not pressable."""
    chosen = str(choice or FOLLOW)
    return tuple(
        Control(BAF, one, ON if one == chosen else OFF, disabled=one == chosen, row=BAF_ROW)
        for one in BAF_CHOICES
    )


def controls(
    mode: Any,
    spot_state: Any,
    highlight: bool = False,
    ping: bool = False,
    announce: bool = True,
    overlay: bool | None = None,
) -> tuple[Control, ...]:
    """Each button carries the move it makes, so a stale label can never do the opposite."""
    marathon_on, runs_on = halves(mode)
    spot = spot_word(spot_state)
    return (
        Control(EVENT, OFF if marathon_on else ON, ON if marathon_on else OFF),
        Control(RUNS, OFF if runs_on else ON, ON if runs_on else OFF),
        spot_control(spot),
        switch(HIGHLIGHT, highlight),
        switch(PING, ping),
        switch(ANNOUNCE, announce),
        *(() if overlay is None else (switch(OVERLAY, overlay),)),
    )


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
    "BAF_CHOICES",
    "Control",
    "FOLLOW",
    "NO",
    "RETIRED",
    "YES",
    "baf_controls",
    "controls",
    "custom_id",
    "halves",
    "label",
    "mode_from",
    "spot_control",
    "spot_word",
    "switch",
    "tracker_url",
    "wanted_mode",
]
