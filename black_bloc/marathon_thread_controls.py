"""The control message pinned in a tracked marathon's thread: events and the spotlight."""

from __future__ import annotations

from typing import Any, NamedTuple

from . import marathon_events as me
from . import marathon_spotlight as ms

EVENT = "event"
RUNS = "runs"
SPOTLIGHT = "spotlight"
ACTIONS = (EVENT, RUNS, SPOTLIGHT)
ON = "on"
OFF = "off"
TEMPLATE = (
    r"marathon:controls:(?P<marathon_id>[0-9]+):(?P<action>event|runs|spotlight):(?P<to>on|off)"
)
CUSTOM_ID = "marathon:controls:{marathon_id}:{action}:{to}"

SPOT_ON = "on"
SPOT_OFF = "off"
SPOT_KEPT = "kept"
SPOT_NONE = "none"
SPOT_OF_STATE = {
    ms.HELD: SPOT_ON,
    ms.HELD_OTHER: SPOT_ON,
    ms.UNTIL: SPOT_ON,
    ms.SCHEDULED: SPOT_ON,
    ms.KEPT: SPOT_KEPT,
    ms.WAITING: SPOT_OFF,
    ms.DARK: SPOT_OFF,
    ms.NO_CHANNEL: SPOT_NONE,
}
LABEL_LIMIT = 80
POSTED_REASON = "Black Bloc: the marathon's controls"
BECAUSE_STARTED = "staff_started"


class Control(NamedTuple):
    action: str
    to: str
    word: str
    disabled: bool = False


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


def controls(mode: Any, spot_state: Any) -> tuple[Control, Control, Control]:
    """Each button carries the move it makes, so a stale label can never do the opposite."""
    marathon_on, runs_on = halves(mode)
    spot = spot_word(spot_state)
    return (
        Control(EVENT, OFF if marathon_on else ON, ON if marathon_on else OFF),
        Control(RUNS, OFF if runs_on else ON, ON if runs_on else OFF),
        Control(
            SPOTLIGHT,
            ON if spot in (SPOT_OFF, SPOT_NONE) else OFF,
            spot,
            disabled=spot == SPOT_NONE,
        ),
    )


def label(text: Any) -> str:
    return str(text or "").strip()[:LABEL_LIMIT] or "…"


__all__ = [
    "ACTIONS",
    "Control",
    "controls",
    "custom_id",
    "halves",
    "label",
    "mode_from",
    "spot_word",
    "wanted_mode",
]
