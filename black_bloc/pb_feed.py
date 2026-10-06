"""The personal best feed's rules and words: the mode, who is due, and what a post says."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta
from typing import Any

import discord

from . import pb_store, shadow
from .settings_store import (
    PB_FEED_AUTO_MATCH,
    PB_FEED_CHANNEL,
    PB_FEED_DEFAULTS,
    PB_FEED_FEATURE,
    PB_FEED_INTERVAL,
    PB_FEED_MODE,
    PB_FEED_MODES,
    PB_FEED_PING_ROLE,
    PB_FEED_REMATCH_DAYS,
)
from .speedrun import PersonalBest

log = logging.getLogger(__name__)

FEATURE = PB_FEED_FEATURE
PAGE = "pbs.html"
OFF = "off"
SHADOW = "shadow"
ON = "on"
TICK_CAP = 5
BACKOFF_FIRST_MINUTES = 5
BACKOFF_MAX_MINUTES = 360
EMBED_COLOUR = 0xF4C430
DESCRIPTION_LIMIT = 4000
TITLE_LIMIT = 256

LOOKUP = "lookup"
LOOK = "look"

NO_CHANNEL = (
    "pb_feed_channel_id is blank, so there is nowhere to post it. Pick a channel on the "
    "Personal bests page or in /settings; this run is recorded and will not be posted later."
)
CHANNEL_GONE = (
    "the channel pb_feed_channel_id names is not one Black Bloc can find. Pick the channel "
    "again on the Personal bests page; this run is recorded and will not be posted later."
)
NO_SHADOW_HOME = (
    "there is no rehearsal home: shadow_channel_id, pb_feed_shadow_channel_id and "
    "log_channel_id are all blank or gone. Set one of them to see rehearsal copies."
)
TEST_MODE_REFUSED = "test mode keeps Black Bloc out of that channel"
SEND_FORBIDDEN = (
    "Discord refused the post (Discord said: {said}). Give Black Bloc View Channel, Send "
    "Messages and Embed Links in that channel; this run will not be posted later."
)
SEND_FAILED = (
    "Discord answered with an error ({status}: {said}), so the post was not made. This run "
    "will not be posted later."
)


def mode_of(store: Any, guild_id: int) -> str:
    found = str(store.get(guild_id, PB_FEED_MODE))
    return found if found in PB_FEED_MODES else OFF


def said(store: Any, guild_id: int, key: str, **fields: Any) -> str:
    """Staff wording first; a template that cannot be filled falls back to the shipped one."""
    wording = str(store.get(guild_id, key) or "").strip()
    if wording:
        try:
            return wording.format(**fields)
        except (IndexError, KeyError, ValueError):
            log.warning("pb feed: %s could not be filled in; the shipped wording was used", key)
    return str(PB_FEED_DEFAULTS[key]).format(**fields)


def time_words(seconds: Any) -> str:
    """1:02:03, 2:03 or 0:59, with thousandths only when the run has them."""
    total = max(0.0, float(seconds or 0))
    millis = round(total * 1000)
    whole, part = divmod(millis, 1000)
    hours, rest = divmod(whole, 3600)
    minutes, secs = divmod(rest, 60)
    words = f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"
    return f"{words}.{part:03d}" if part else words


def backoff_minutes(failures: int) -> int:
    steps = max(0, int(failures) - 1)
    return int(min(BACKOFF_MAX_MINUTES, BACKOFF_FIRST_MINUTES * (2 ** min(steps, 16))))


def per_tick(people: int, interval_minutes: int) -> int:
    """How many members one minute's tick takes, so the whole list spans the interval."""
    if people <= 0:
        return 0
    return max(1, min(TICK_CAP, math.ceil(people / max(1, int(interval_minutes)))))


def post_fields(
    store: Any, guild_id: int, member: Any, user_id: int, runner: str, best: PersonalBest
) -> dict[str, str]:
    place = best.place
    return {
        "member": getattr(member, "mention", None) or f"<@{user_id}>",
        "name": str(getattr(member, "display_name", None) or runner),
        "runner": runner,
        "game": discord.utils.escape_markdown(best.game),
        "category": discord.utils.escape_markdown(best.category),
        "time": time_words(best.seconds),
        "place": str(place or ""),
        "place_line": f" {said(store, guild_id, 'pb_feed_place_text', place=place)}"
        if place
        else "",
        "link": best.weblink,
    }


def post_embed(
    store: Any, guild_id: int, member: Any, user_id: int, runner: str, best: PersonalBest
) -> discord.Embed:
    fields = post_fields(store, guild_id, member, user_id, runner, best)
    embed = discord.Embed(
        title=said(store, guild_id, "pb_feed_post_title", **fields)[:TITLE_LIMIT],
        description=said(store, guild_id, "pb_feed_post_text", **fields)[:DESCRIPTION_LIMIT],
        colour=EMBED_COLOUR,
    )
    if fields["link"].startswith("https://"):
        embed.url = fields["link"]
    return embed


def link_view(store: Any, guild_id: int, link: str) -> discord.ui.View | None:
    if not str(link).startswith("https://"):
        return None
    view = discord.ui.View(timeout=None)
    view.add_item(
        discord.ui.Button(
            label=said(store, guild_id, "pb_feed_link_label")[:80] or "speedrun.com",
            style=discord.ButtonStyle.link,
            url=link,
        )
    )
    return view


def aimed_at(store: Any, guild_id: int) -> int | None:
    return shadow.as_channel_id(store.get(guild_id, PB_FEED_CHANNEL))


def ping_role(store: Any, guild_id: int) -> int | None:
    return shadow.as_channel_id(store.get(guild_id, PB_FEED_PING_ROLE))


def rehearsal_line(bot: Any, guild: Any) -> str:
    aimed = aimed_at(bot.store, guild.id)
    words = f"<#{aimed}>" if aimed else said(bot.store, guild.id, "pb_feed_no_channel_words")
    return shadow.note_line(bot, guild, words)


def send_reason(exc: BaseException) -> str:
    if isinstance(exc, discord.Forbidden):
        return SEND_FORBIDDEN.format(said=exc.text or exc.status)
    if isinstance(exc, discord.HTTPException):
        return SEND_FAILED.format(status=exc.status, said=exc.text or type(exc).__name__)
    return SEND_FAILED.format(status=type(exc).__name__, said=str(exc)[:200])


def wants_lookup(
    row: Any, login: str | None, *, auto: bool, now: datetime, rematch_days: int
) -> bool:
    """A linked member with no answer yet, or whose 'nobody' answer has aged out."""
    if not auto or not login:
        return False
    if row is None:
        return True
    if row["state"] != pb_store.NONE:
        return False
    checked = pb_store.parsed(row["checked_at"])
    if checked is None or (row["twitch_login"] or "") != login:
        return True
    return now - checked >= timedelta(days=max(1, int(rematch_days)))


def link_moved(row: Any, login: str | None) -> bool:
    """An automatic match made from a Twitch login the member no longer has."""
    return (
        row is not None
        and row["state"] == pb_store.MATCHED
        and row["source"] == pb_store.AUTO
        and (row["twitch_login"] or "") != (login or "")
    )


def look_due(row: Any, *, now: datetime, interval_minutes: int) -> bool:
    if row["state"] != pb_store.MATCHED or not row["src_user_id"]:
        return False
    looked = pb_store.parsed(row["looked_at"])
    return looked is None or now - looked >= timedelta(minutes=max(1, int(interval_minutes)))


def work_list(
    rows: dict[int, Any],
    links: dict[int, str],
    present: Any,
    *,
    store: Any,
    guild_id: int,
    now: datetime,
) -> list[tuple[str, int]]:
    """Everyone a tick could take, lookups first, then the looks longest overdue."""
    auto = bool(store.get(guild_id, PB_FEED_AUTO_MATCH))
    rematch_days = int(store.get(guild_id, PB_FEED_REMATCH_DAYS))
    interval = int(store.get(guild_id, PB_FEED_INTERVAL))
    lookups: list[tuple[str, int]] = []
    looks: list[tuple[str, str, int]] = []
    for user_id in sorted(set(rows) | set(links)):
        if user_id not in present:
            continue
        row = rows.get(user_id)
        login = links.get(user_id)
        if link_moved(row, login) or wants_lookup(
            row, login, auto=auto, now=now, rematch_days=rematch_days
        ):
            lookups.append((LOOKUP, user_id))
        elif row is not None and look_due(row, now=now, interval_minutes=interval):
            looks.append((str(row["looked_at"] or ""), LOOK, user_id))
    return lookups + [(what, user_id) for _, what, user_id in sorted(looks)]


def population(rows: dict[int, Any], links: dict[int, str], present: Any) -> int:
    """Everyone the feed could ever ask about: the matched, and the linked with no row yet."""
    counted = 0
    for user_id in set(rows) | set(links):
        if user_id not in present:
            continue
        row = rows.get(user_id)
        if row is None or row["state"] in (pb_store.MATCHED, pb_store.NONE):
            counted += 1
    return counted


__all__ = [
    "BACKOFF_FIRST_MINUTES",
    "BACKOFF_MAX_MINUTES",
    "CHANNEL_GONE",
    "FEATURE",
    "LOOK",
    "LOOKUP",
    "NO_CHANNEL",
    "NO_SHADOW_HOME",
    "OFF",
    "ON",
    "PAGE",
    "SHADOW",
    "TEST_MODE_REFUSED",
    "TICK_CAP",
    "aimed_at",
    "backoff_minutes",
    "link_moved",
    "link_view",
    "look_due",
    "mode_of",
    "per_tick",
    "ping_role",
    "population",
    "post_embed",
    "post_fields",
    "rehearsal_line",
    "said",
    "send_reason",
    "time_words",
    "wants_lookup",
    "work_list",
]
