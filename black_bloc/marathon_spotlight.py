from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .golive import parse_ts
from .marathon import MarathonMove
from .marathon_channels import takes_marathons
from .marathon_feeds import SEEDS
from .settings_store import PING_MODES
from .spotlight import WINDOW_MARATHON, is_spotlit, keeps_forever

FOLLOW = "follow"
OFF = "off"
MODES = (FOLLOW, OFF)
MODE_WORDS = {FOLLOW: "on", OFF: "off"}
YES = ("follow", "on", "true", "yes", "1")
NO = ("off", "false", "no", "0")

SPOTLIGHT_LINE = "Spotlight the channel while it runs: **{state}**"
SPOTLIGHT_FIELD = "Spotlight the channel while it runs"
SPOTLIGHT_ON_BUTTON = "Spotlight while it runs"
SPOTLIGHT_OFF_BUTTON = "Stop spotlighting it"
MODE_SAID = {
    FOLLOW: (
        "**{name}** spotlights its channel while it runs again — from "
        "{lead} minutes before its first run to {tail} minutes after its last ends."
    ),
    OFF: (
        "**{name}** no longer spotlights its channel. A spotlight it had already turned on is "
        "turned off; one staff set stays as it is."
    ),
}
MODE_SAME = "**{name}** already has that, so nothing was changed."
BAD_MODE = (
    "Say on or off for whether the marathon spotlights its channel while it runs, so nothing "
    "was changed."
)
STAFF_OFF_CLAUSE = "**{name}** will not spotlight it again."
BECAUSE_STAFF_OFF = "staff_turned_the_spotlight_off"
BECAUSE_MARATHON_OVER = "marathon_over"
BECAUSE_MODE_OFF = "mode_off"


def _cell(row: Any, key: str, fallback: Any = None) -> Any:
    if row is None:
        return fallback
    if isinstance(row, dict):
        return row.get(key, fallback)
    try:
        return row[key]
    except (IndexError, KeyError):
        return fallback


def mode_of(marathon: Any) -> str:
    """NULL, or a word nobody wrote, reads as follow."""
    return OFF if str(_cell(marathon, "spotlight_mode") or "").strip().lower() == OFF else FOLLOW


def clean_mode(given: Any) -> str | None:
    if isinstance(given, bool):
        return FOLLOW if given else OFF
    word = str(given if given is not None else "").strip().lower()
    if word in YES:
        return FOLLOW
    if word in NO:
        return OFF
    return None


def span_of(marathon: Any) -> tuple[datetime, datetime] | None:
    starts = parse_ts(_cell(marathon, "starts_at"))
    ends = parse_ts(_cell(marathon, "ends_at")) or starts
    if starts is None or ends is None:
        return None
    return (starts, max(starts, ends))


def reach_end(span: tuple[datetime, datetime], tail_minutes: int = 0) -> datetime:
    """The span's end plus the tail: when a spotlight the marathon holds is given back."""
    return span[1] + timedelta(minutes=max(0, int(tail_minutes)))


def in_reach(
    span: tuple[datetime, datetime] | None,
    now: datetime,
    lead_minutes: int,
    tail_minutes: int = 0,
) -> bool:
    if span is None:
        return False
    starts = span[0]
    return (
        starts - timedelta(minutes=max(0, int(lead_minutes))) <= now < reach_end(span, tail_minutes)
    )


def is_kept(row: Any) -> bool:
    return is_spotlit(row) and keeps_forever(row)


def follows(marathon: Any, *, enabled: bool) -> bool:
    return (
        bool(enabled)
        and marathon is not None
        and bool(_cell(marathon, "active", 1))
        and mode_of(marathon) == FOLLOW
    )


def plan(
    row: Any,
    marathon: Any,
    now: datetime,
    *,
    enabled: bool,
    lead_minutes: int,
    tail_minutes: int = 0,
) -> dict[str, Any] | None:
    """The fields a follow writes on the channel row, or None when it leaves it alone."""
    if row is None or not follows(marathon, enabled=enabled) or not takes_marathons(row):
        return None
    span = span_of(marathon)
    if not in_reach(span, now, lead_minutes, tail_minutes) or is_kept(row):
        return None
    ends = reach_end(span, tail_minutes)
    if is_spotlit(row):
        current = parse_ts(_cell(row, "expires_at"))
        if current is None or current >= ends:
            return None
        return {"expires_at": ends.isoformat()}
    return {
        "spotlight": 1,
        "expires_at": ends.isoformat(),
        "spotlit_by_marathon": int(marathon["id"]),
    }


def lifted_fields() -> dict[str, Any]:
    """What a marathon's spotlight gives back: off, kept, no marathon holding it."""
    return {"spotlight": 0, "expires_at": None, "spotlit_by_marathon": None}


def held_by(row: Any) -> int | None:
    found = _cell(row, "spotlit_by_marathon")
    return int(found) if found not in (None, "", 0) else None


def dimmed_during(
    marathons: Any, now: datetime, *, enabled: bool, lead_minutes: int, tail_minutes: int = 0
) -> list[Any]:
    """The marathons on a channel that were spotlighting it when staff turned it off."""
    return [
        one
        for one in marathons or ()
        if follows(one, enabled=enabled) and in_reach(span_of(one), now, lead_minutes, tail_minutes)
    ]


def is_marathon_login(login: Any) -> bool:
    return str(login or "").strip().lower() in {seed.login for seed in SEEDS}


def is_marathon_channel(row: Any, windows: Any = ()) -> bool:
    """A row that takes marathons and is one: a seeded feed's login, or a marathon window on it."""
    if row is None or not takes_marathons(row):
        return False
    if is_marathon_login(_cell(row, "twitch_login")):
        return True
    return any(_cell(one, "source") == WINDOW_MARATHON for one in windows or ())


def new_row_ping_mode(login: Any, takes: bool, marathon_default: Any, general: Any) -> Any:
    if takes and is_marathon_login(login) and str(marathon_default) in PING_MODES:
        return str(marathon_default)
    return general


FOLLOW_ACTION = "spotlight_follow"
OFF_ACTION = "spotlight_off"
FOLLOW_MOVE = MarathonMove(FOLLOW_ACTION, SPOTLIGHT_ON_BUTTON, row=2)
OFF_MOVE = MarathonMove(OFF_ACTION, SPOTLIGHT_OFF_BUTTON, row=2)
MOVE_MODES = {FOLLOW_ACTION: FOLLOW, OFF_ACTION: OFF}


def card_moves(marathon: Any) -> tuple[MarathonMove, ...]:
    """The one switch that changes something, and only on a marathon with a channel."""
    if not _cell(marathon, "spotlight_id"):
        return ()
    return (OFF_MOVE,) if mode_of(marathon) == FOLLOW else (FOLLOW_MOVE,)


def mode_line(marathon: Any) -> str:
    return SPOTLIGHT_LINE.format(state=MODE_WORDS[mode_of(marathon)])


__all__ = [
    "BAD_MODE",
    "MOVE_MODES",
    "card_moves",
    "FOLLOW",
    "MODES",
    "OFF",
    "clean_mode",
    "dimmed_during",
    "held_by",
    "in_reach",
    "is_kept",
    "is_marathon_channel",
    "is_marathon_login",
    "lifted_fields",
    "mode_line",
    "mode_of",
    "new_row_ping_mode",
    "plan",
    "reach_end",
    "span_of",
]
