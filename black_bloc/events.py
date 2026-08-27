from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Any

import discord

from .golive import parse_ts
from .timezones import stamp

log = logging.getLogger(__name__)

TITLE_LIMIT = 100
DESCRIPTION_LIMIT = 1000
LOCATION_LIMIT = 100
EVENT_NAME_LIMIT = 100
CHANNEL_NAME_LIMIT = 100
DEFAULT_DURATION_MINUTES = 120
MAX_DURATION_MINUTES = 7 * 24 * 60

PENDING = "pending"
APPROVED = "approved"
DENIED = "denied"
LIVE = "live"
DONE = "done"
CANCELLED = "cancelled"
STATUSES = (PENDING, APPROVED, DENIED, LIVE, DONE, CANCELLED)
OPEN_STATUSES = (PENDING, APPROVED, LIVE)
TRANSITIONS: dict[str, tuple[str, ...]] = {
    PENDING: (APPROVED, DENIED, CANCELLED),
    APPROVED: (LIVE, DONE, CANCELLED),
    LIVE: (DONE, CANCELLED),
    DENIED: (),
    DONE: (),
    CANCELLED: (),
}

COLOURS: dict[str, int] = {
    PENDING: 0x5865F2,
    APPROVED: 0x57F287,
    DENIED: 0xED4245,
    LIVE: 0xFEE75C,
    DONE: 0x99AAB5,
    CANCELLED: 0x99AAB5,
}

DURATION_PATTERN = re.compile(r"^(?:(\d{1,4})h)?(?:(\d{1,5})m)?$")

BAD_START = (
    "**{given}** is not a date Black Bloc can read, so nothing was submitted. Write it as "
    "`YYYY-MM-DD HH:MM` on a 24-hour clock — `{example}` is half past seven in the evening on "
    "the 14th — and it is read in **{tz}**, which `/timezone set` changes."
)
START_IN_THE_PAST = (
    "**{given}** has already gone by in **{tz}**, so nothing was submitted. Pick a time in the "
    "future, or run `/timezone set` if that zone is not the one you are in."
)
BAD_DURATION = (
    "**{given}** is not a length Black Bloc can read, so nothing was submitted. Write it as "
    "`1h30m`, `2h` or `45m` — leave it empty for two hours — and keep it under a week."
)


def clamp(text: Any, limit: int) -> str:
    return str(text or "").strip()[:limit]


def slugify(text: Any) -> str:
    """Discord channel-name rules: lowercase, `a-z0-9-`, no runs of dashes."""
    folded = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")


def channel_name(status: str, user_name: Any, title: Any) -> str:
    tail = "-".join(part for part in (slugify(user_name), slugify(title)) if part)
    name = f"{status}-{tail}" if tail else status
    return name[:CHANNEL_NAME_LIMIT].strip("-") or status


def parse_duration(text: Any, default: int = DEFAULT_DURATION_MINUTES) -> int | None:
    """Minutes from `1h30m`, or None when it cannot be read; empty means the default."""
    raw = str(text or "").strip().lower().replace(" ", "")
    if not raw:
        return default
    match = DURATION_PATTERN.match(raw)
    if match is None or not any(match.groups()):
        return None
    minutes = int(match.group(1) or 0) * 60 + int(match.group(2) or 0)
    if minutes <= 0 or minutes > MAX_DURATION_MINUTES:
        return None
    return minutes


def describe_duration(minutes: Any) -> str:
    total = int(minutes or 0)
    hours, rest = divmod(max(total, 0), 60)
    if hours and rest:
        return f"{hours}h {rest}m"
    if hours:
        return f"{hours}h"
    return f"{rest}m"


def can_transition(before: Any, after: Any) -> bool:
    return str(after) in TRANSITIONS.get(str(before), ())


def is_due(when: Any, now: datetime) -> bool:
    parsed = parse_ts(when)
    return parsed is not None and parsed <= now


def build_card(
    *,
    event_id: Any,
    title: str,
    requester_id: int,
    starts_at: datetime,
    minutes: int,
    location: str | None = None,
    description: str | None = None,
    status: str = PENDING,
    deny_reason: str | None = None,
) -> discord.Embed:
    """The one card every surface shows: review channel, DM, announcement."""
    embed = discord.Embed(
        title=clamp(title, TITLE_LIMIT),
        description=clamp(description, DESCRIPTION_LIMIT) or None,
        colour=COLOURS.get(status, COLOURS[PENDING]),
    )
    embed.add_field(name="Who", value=f"<@{requester_id}>", inline=True)
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="How long", value=describe_duration(minutes), inline=True)
    embed.add_field(name="When", value=stamp(starts_at), inline=False)
    if location:
        embed.add_field(name="Where", value=clamp(location, LOCATION_LIMIT), inline=False)
    if deny_reason:
        embed.add_field(name="Why not", value=clamp(deny_reason, 1024), inline=False)
    embed.set_footer(text=f"Event #{event_id}")
    return embed


def mentions(ping_role_id: Any = None) -> discord.AllowedMentions:
    """Nothing an event's author typed may ping; only the configured role may."""
    return discord.AllowedMentions(
        everyone=False,
        users=False,
        roles=[discord.Object(int(ping_role_id))] if ping_role_id else False,
    )


def announce_text(ping_role_id: Any = None) -> str:
    prefix = f"<@&{ping_role_id}> " if ping_role_id else ""
    return f"{prefix}A new event is on the calendar — hit **Interested** to be reminded."


def golive_text(title: str, ping_role_id: Any = None) -> str:
    prefix = f"<@&{ping_role_id}> " if ping_role_id else ""
    return f"{prefix}**{clamp(title, TITLE_LIMIT)}** is starting now!"


def ends_at(starts_at: datetime, minutes: int) -> datetime:
    return starts_at + timedelta(minutes=max(int(minutes), 1))


def start_error(given: Any, tz_name: str, example: str) -> str:
    return BAD_START.format(given=clamp(given, 80) or "(nothing)", tz=tz_name, example=example)
