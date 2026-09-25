from __future__ import annotations

from typing import Any

BECAUSE_OPTED_OUT = "channel_opted_out"
BECAUSE_OPTED_IN = "channel_opted_in"
OPTED_OUT_SEEDS = ("esamarathon",)
OPT_OUT_KEY = "optout:{login}"

MARATHONS_ON_BUTTON = "Marathons on"
MARATHONS_OFF_BUTTON = "Marathons off"
NO_MARATHONS_CELL = "no marathons"
MARATHONS_ON_SAID = (
    "**{login}** takes marathons again — a feed can be added for it, and {count} marathon(s) "
    "paused when it was opted out are read again."
)
MARATHONS_OFF_SAID = (
    "**{login}** is opted out of marathons — no feed checks for it, nothing can be added on "
    "it, and {count} marathon(s) on it are paused until it is turned back on."
)
MARATHONS_SAME = "**{login}** already {state}, so nothing was changed."
TAKES_WORDS = {True: "takes marathons", False: "is opted out of marathons"}
OPTED_OUT_REFUSAL = (
    "**{channel}** is opted out of marathons — turn it on in its row first, so nothing was "
    "changed."
)
HELD_REFUSAL = (
    "**{name}** is paused because **{channel}** is opted out of marathons — turn marathons back "
    "on for the channel first, so nothing was changed."
)
PANEL_LINE = "Marathons: **{state}**"
PANEL_ON = "on"
PANEL_OFF = "off — nothing is added, read or fed for this channel"


def _cell(row: Any, key: str, fallback: Any = None) -> Any:
    if row is None:
        return fallback
    if isinstance(row, dict):
        return row.get(key, fallback)
    try:
        return row[key]
    except (IndexError, KeyError):
        return fallback


def takes_marathons(row: Any) -> bool:
    """A row the migration has not reached takes marathons."""
    found = _cell(row, "marathons")
    return True if found is None else bool(found)


def channel_word(row: Any) -> str:
    return str(_cell(row, "display_name") or _cell(row, "twitch_login") or "?")


def seed_key(login: str) -> str:
    return OPT_OUT_KEY.format(login=str(login).lower())


def panel_line(row: Any) -> str:
    return PANEL_LINE.format(state=PANEL_ON if takes_marathons(row) else PANEL_OFF)


__all__ = [
    "BECAUSE_OPTED_IN",
    "BECAUSE_OPTED_OUT",
    "OPTED_OUT_SEEDS",
    "channel_word",
    "panel_line",
    "seed_key",
    "takes_marathons",
]
