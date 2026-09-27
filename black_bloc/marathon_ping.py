from __future__ import annotations

from typing import Any

from .marathon import MarathonMove

ON_ACTION = "ping_role_on"
OFF_ACTION = "ping_role_off"
MOVE_WANTS = {ON_ACTION: True, OFF_ACTION: False}
YES = ("on", "true", "yes", "1")
NO = ("off", "false", "no", "0")
BAD_PING_ROLE = "Say on or off for whether the marathon pings roles, so nothing was changed."
BAD_PING_ROLE_CODE = "bad_ping_role"


def _cell(row: Any, key: str, fallback: Any = None) -> Any:
    if row is None:
        return fallback
    try:
        return row[key]
    except (IndexError, KeyError):
        return fallback


def pings_role(marathon: Any) -> bool:
    """NULL or a missing column reads as off, the owner's default."""
    return bool(_cell(marathon, "ping_role", 0))


def clean_ping_role(given: Any) -> bool | None:
    if isinstance(given, bool):
        return given
    if isinstance(given, int):
        return {0: False, 1: True}.get(given)
    word = str(given if given is not None else "").strip().lower()
    if word in YES:
        return True
    if word in NO:
        return False
    return None


def card_move(marathon: Any, on_label: str, off_label: str) -> MarathonMove:
    """The one button that changes it: its label is the next state."""
    if pings_role(marathon):
        return MarathonMove(OFF_ACTION, off_label[:80], row=2)
    return MarathonMove(ON_ACTION, on_label[:80], row=2)


__all__ = [
    "BAD_PING_ROLE",
    "BAD_PING_ROLE_CODE",
    "MOVE_WANTS",
    "OFF_ACTION",
    "ON_ACTION",
    "card_move",
    "clean_ping_role",
    "pings_role",
]
