"""Twitch channels watched by name, with no Discord member behind them."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from .golive import (
    GAME_FALLBACK,
    TWITCH,
    StreamInfo,
    _Fields,
    humanise_duration,
    now_iso,
    parse_ts,
    tidy,
    twitch_login_from_url,
)
from .settings_store import SPOTLIGHT_BUMP_TEMPLATE

log = logging.getLogger(__name__)

LOGIN_MAX = 25
CHANNEL_URL = "https://www.twitch.tv/{login}"
PIN_REASON = "Black Bloc keeps this spotlight pinned while it streams"
UNPIN_REASON = "Black Bloc unpinned this spotlight — the stream is over"
KEPT = "kept"
UNTIL = "until {when}"
ANNOUNCED_CELL = "spotlight · {when}"
CHANNEL_ONLY = "channel only"

BAD_LOGIN = (
    "**{given}** is not a Twitch channel name, so nothing was spotlighted. Use the name from "
    "the channel address — the part after twitch.tv/ — for example `gamesdonequick`."
)
ALREADY_SPOTLIT = (
    "**{login}** is already on the spotlight list, so nothing was added. **Extend** on its own "
    "row moves the date it runs out instead — that is the move you want if this is a new "
    "marathon on the same channel."
)
ALREADY_SPOTLIT_EVENT = (
    "**{login}** is already on the spotlight list, so nothing was added. Extend it to this "
    "event's end instead — its row on the Go-live page has the move."
)
NO_SUCH_ROW = (
    "That spotlight row is not there any more, so nothing was changed. It may have run out, or "
    "somebody else may have removed it — the Go-live page's Streamers list shows what is left."
)
NO_KEY = (
    "Twitch credentials are not set (TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET), so nothing is "
    "being watched and no spotlight can be announced. The list below is still kept — it starts "
    "working the moment a Lead sets them."
)
MODE_OFF = (
    "Spotlight is **off**, so nothing on this list is watched or announced. The list is kept "
    "as it is — turning it back on picks up where it left off."
)
MODE_SHADOW = (
    "Spotlight is in **shadow**, so announcements, reminders and pins are rehearsed where "
    "shadow_channel_id points and nothing reaches the go-live channel."
)
NO_CHANNEL = (
    "There is nowhere to announce a spotlight: golive_channel_id is not set. Nothing was "
    "posted, and the row is still on the list."
)
PIN_REFUSED = (
    "**{login}**'s announcement was posted but could not be pinned ({reason}). Black Bloc "
    "needs **Manage Messages** in that channel, and a channel can hold 50 pins. Nothing else "
    "about the spotlight changed."
)
UNPIN_REFUSED = (
    "**{login}**'s announcement could not be unpinned ({reason}), so it is still pinned in the "
    "go-live channel. Taking the pin off by hand is safe — nothing else is waiting on it."
)
ADDED = (
    "**{login}** is on the spotlight list, {when}. Black Bloc announces it in the go-live "
    "channel whenever it goes live, reminds people every {hours} hours while it runs, and "
    "{pin}."
)
ADDED_PIN = "pins the announcement for the duration"
ADDED_NO_PIN = "leaves the announcement unpinned"
REMOVED = (
    "**{login}** is off the spotlight list. Any announcement it has out there is left as "
    "posted; nothing else was changed."
)
EXTENDED = "**{login}** now runs {when}."
KEPT_SAID = "**{login}** is kept for ever now, so no purge will take it off the list."
EXPIRES_SAID = "**{login}** runs out {when} and will be purged then."
PINNED_SAID = "**{login}**'s announcements will be pinned while it streams."
UNPINNED_SAID = "**{login}**'s announcements will not be pinned."
BUMPED_SAID = "Reminded the go-live channel that **{login}** is still live."
NOT_LIVE = (
    "**{login}** is not live right now, so there was nothing to remind anybody about. The "
    "reminder is offered again the moment Black Bloc sees it go live."
)
NO_COG = (
    "Black Bloc's spotlight half is not running right now, so no reminder could be posted. "
    "Nothing about **{login}** changed, and the next reminder is still due on time — tell a "
    "Lead if the bot has not finished starting up."
)
BUMP_FAILED = (
    "**{login}** is live, but the reminder could not be posted ({reason}). Nothing about the "
    "spotlight changed and the next one is still due on time."
)

PANEL_TITLE = "Spotlight"
PANEL_INTRO = (
    "Twitch channels watched by name, for org channels and marathons that have nobody in this "
    "server behind them. Adding one is staff-only."
)
PANEL_EMPTY = "No channel is spotlighted yet."
PANEL_ROW = "**{login}** — {when}{live}{note}"
PANEL_LIVE = " · **live now**"
PANEL_NOTE = " · {note}"
ADD_BUTTON = "Add a channel…"
ADD_MODAL_TITLE = "Spotlight a Twitch channel"
ADD_LOGIN_LABEL = "The name after twitch.tv/"
ADD_LOGIN_PLACEHOLDER = "gamesdonequick"
ADD_DAYS_LABEL = "Days to keep it — blank means for ever"
ADD_DAYS_PLACEHOLDER = "7"
BAD_DAYS = (
    "**{given}** is not a number of days, so nothing was added. Write a whole number of days, "
    "or leave it blank to keep the channel on the list for ever."
)
PICK_A_CHANNEL = "A spotlighted channel…"
ROW_MOVE = "What to do with {login}…"
EXTEND_WEEK = "Extend a week"
KEEP_FOREVER = "Keep for ever"
BUMP_NOW = "Bump now"
REMOVE = "Remove"
SPOTLIGHT_BUTTON = "Spotlight…"
EVENT_SPOTLIGHT_LABEL = "Spotlight this stream"
EVENT_NOT_TWITCH = (
    "This event's **Where** is not a twitch.tv address, so there is no channel to spotlight. "
    "Change the Where to the channel's own address and the move appears."
)
EVENT_SPOTLIT = (
    "**{login}** is spotlighted until {when} — the go-live channel announces it, reminds "
    "people while it runs, and pins it for the duration."
)
EVENT_CANCELLED_BECAUSE = "event_cancelled"
SPOTLIT_UNTIL = "Spotlighted until {when}."

RECONCILED = "reconciled_on_start"
ENDED = "ended"
EXPIRED = "expired"
REMOVED_BECAUSE = "removed"


@dataclass(frozen=True)
class Bump:
    """When the next reminder is due, and whether it is due now."""

    due_at: datetime | None
    due: bool


def _cell(row: Any, key: str) -> Any:
    if row is None:
        return None
    try:
        return row[key]
    except (IndexError, KeyError, TypeError):
        return getattr(row, key, None)


def clean_login(raw: Any) -> str | None:
    """A Twitch channel name out of a name, an @handle or a whole channel address."""
    login = twitch_login_from_url(raw) or str(raw or "").strip().lower().lstrip("@")
    if not login or len(login) > LOGIN_MAX:
        return None
    if not all(ch.isalnum() or ch == "_" for ch in login):
        return None
    return login


def login_from_url(url: Any) -> str | None:
    """The channel name an event's Where points at, or None when it is not a Twitch link."""
    found = twitch_login_from_url(url)
    return clean_login(found) if found else None


def channel_url(login: Any) -> str:
    return CHANNEL_URL.format(login=str(login or ""))


def display_for(row: Any) -> str:
    return str(_cell(row, "display_name") or _cell(row, "twitch_login") or "")


def keeps_forever(row: Any) -> bool:
    return not str(_cell(row, "expires_at") or "").strip()


def is_expired(row: Any, now: datetime | None = None) -> bool:
    """A kept row never expires; an unreadable date is treated as no date, never as due."""
    raw = _cell(row, "expires_at")
    if not str(raw or "").strip():
        return False
    when = parse_ts(raw)
    if when is None:
        log.warning("spotlight: expires_at %r is unreadable; the row is left on the list", raw)
        return False
    return (now or datetime.now(UTC)) >= when


def when_words(value: Any) -> str:
    when = parse_ts(value)
    if when is None:
        return ""
    return f"{when.day} {when.strftime('%b')}"


def until_words(row: Any) -> str:
    """`kept`, or `until 30 Sep` — the two halves the owner's two meanings of 'pin' became."""
    if keeps_forever(row):
        return KEPT
    said = when_words(_cell(row, "expires_at"))
    return UNTIL.format(when=said) if said else KEPT


def announced_words(row: Any) -> str:
    return ANNOUNCED_CELL.format(when=until_words(row))


def bump_hours_for(row: Any, default_hours: Any) -> int:
    own = _cell(row, "bump_hours")
    wanted = own if own else default_hours
    try:
        return max(1, int(wanted))
    except (TypeError, ValueError):
        return max(1, int(default_hours or 1))


def next_bump_at(
    started_at: Any, last_bump_at: Any, hours: int
) -> datetime | None:
    """Measured from the last reminder, and from the start until there has been one."""
    base = parse_ts(last_bump_at) or parse_ts(started_at)
    if base is None or hours <= 0:
        return None
    return base + timedelta(hours=hours)


def bump_due(session: Any, hours: int, now: datetime | None = None) -> Bump:
    """Never on the first look, never twice inside one interval, never after the end."""
    if str(_cell(session, "ended_at") or "").strip():
        return Bump(None, False)
    due_at = next_bump_at(
        _cell(session, "started_at"), _cell(session, "last_bump_at"), hours
    )
    if due_at is None:
        return Bump(None, False)
    return Bump(due_at, (now or datetime.now(UTC)) >= due_at)


def expiry_in_days(days: Any, now: datetime | None = None) -> str | None:
    """`None` days means keep it for ever, which is a NULL, not a far-off date."""
    if days is None or str(days).strip() == "":
        return None
    try:
        wanted = int(days)
    except (TypeError, ValueError):
        return None
    if wanted <= 0:
        return None
    return ((now or datetime.now(UTC)) + timedelta(days=wanted)).isoformat()


def expiry_for_event(ends_at: Any, slack_hours: Any) -> str | None:
    """An event's spotlight runs to its end plus the slack, so an overrun is still announced."""
    over = parse_ts(ends_at)
    if over is None:
        return None
    try:
        slack = max(0, int(slack_hours))
    except (TypeError, ValueError):
        slack = 0
    return (over + timedelta(hours=slack)).isoformat()


def extended_by_days(row: Any, days: int, now: datetime | None = None) -> str:
    """Extending a row that has run out counts from today, not from the date it missed."""
    at = now or datetime.now(UTC)
    when = parse_ts(_cell(row, "expires_at"))
    base = when if when is not None and when > at else at
    return (base + timedelta(days=days)).isoformat()


def info_of(session: Any, login: Any) -> StreamInfo:
    """The StreamInfo a spotlight session stands for — always Twitch, never a member."""
    return StreamInfo(
        url=_cell(session, "url") or channel_url(login),
        game=_cell(session, "game"),
        title=_cell(session, "title"),
        platform=TWITCH,
    )


def bump_fields(info: StreamInfo, name: str, duration: str) -> _Fields:
    return _Fields(
        name=name,
        game=info.game or GAME_FALLBACK,
        title=info.title or "",
        url=info.url or "",
        duration=duration or "",
    )


def bump_duration(session: Any, at: Any = None) -> str:
    return humanise_duration(_cell(session, "started_at"), at or now_iso())


def bump_render(template: Any, info: StreamInfo, name: str, duration: str) -> str:
    """The reminder; unreadable wording falls back to the default rather than posting nothing."""
    fields = bump_fields(info, name, duration)
    wanted = str(template or "").strip() or SPOTLIGHT_BUMP_TEMPLATE
    try:
        return tidy(wanted.format_map(fields))
    except Exception as exc:
        log.warning(
            "spotlight: reminder wording %r could not be rendered (%s); using the default",
            template,
            exc,
        )
        return tidy(SPOTLIGHT_BUMP_TEMPLATE.format_map(fields))


def panel_line(row: Any, live: bool) -> str:
    note = _cell(row, "note")
    return PANEL_ROW.format(
        login=_cell(row, "twitch_login"),
        when=until_words(row),
        live=PANEL_LIVE if live else "",
        note=PANEL_NOTE.format(note=note) if note else "",
    )


def added_said(row: Any, hours: int) -> str:
    return ADDED.format(
        login=_cell(row, "twitch_login"),
        when=until_words(row),
        hours=hours,
        pin=ADDED_PIN if _cell(row, "pin") else ADDED_NO_PIN,
    )


def reason_of(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"
