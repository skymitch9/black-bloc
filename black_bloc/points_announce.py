"""The top-places post: one post per change batch, in the channel the mode points at."""

from __future__ import annotations

import logging
from typing import Any

import discord

from . import points_moves as moves
from . import shadow
from .actionlog import log_action
from .logkinds import VIA_DISCORD, kind_via
from .settings_store import POINTS_CHANNEL, POINTS_FEATURE, POINTS_PING_ROLE

log = logging.getLogger(__name__)

POSTED = "posted"
REHEARSED = "rehearsed"
NOT_POSTED = "not_posted"
NO_CHANNEL = "no_channel"
NO_SHADOW_HOME = "no_shadow_home"
TEST_MODE_REFUSED = "test_mode"
DESCRIPTION_LIMIT = 4000


def role_of(store: Any, guild_id: int) -> int | None:
    return shadow.as_channel_id(store.get(guild_id, POINTS_PING_ROLE))


def embed_of(bot: Any, guild: Any, lines: tuple[str, ...]) -> discord.Embed:
    return discord.Embed(
        title=moves.said(bot.store, guild.id, "points_announce_title"),
        description="\n".join(lines)[:DESCRIPTION_LIMIT],
    )


async def failed(bot: Any, guild: Any, reason: str, home: Any, lines: Any, via: str) -> str:
    """A real post that did not go out is loud; it never shares a kind with the dry run."""
    try:
        await log_action(
            bot,
            guild,
            kind_via("points.announce_failed", via),
            details={"via": via, "channel_id": home, "reason": reason, "lines": list(lines)},
        )
    except Exception:
        log.exception("points: could not write the announce_failed row")
    return NOT_POSTED


async def announce(bot: Any, guild: Any, outcome: Any, *, via: str = VIA_DISCORD) -> str:
    """A move's lines, posted once: the real channel when on, the rehearsal home in shadow."""
    lines = tuple(getattr(getattr(outcome, "value", None), "announce", ()) or ())
    if not getattr(outcome, "ok", False) or not lines:
        return NOT_POSTED
    mode = moves.mode_of(bot.store, guild.id)
    if mode == moves.OFF:
        return NOT_POSTED
    rehearsing = mode == moves.SHADOW
    aimed = shadow.as_channel_id(bot.store.get(guild.id, POINTS_CHANNEL))
    home = shadow.channel_id(bot, guild, feature=POINTS_FEATURE) if rehearsing else aimed
    channel = shadow.channel_of(bot, guild, home)
    if channel is None:
        if rehearsing:
            return NOT_POSTED
        return await failed(bot, guild, NO_CHANNEL, home, lines, via)
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel.id):
        if rehearsing:
            return NOT_POSTED
        return await failed(bot, guild, TEST_MODE_REFUSED, home, lines, via)
    role = None if rehearsing else role_of(bot.store, guild.id)
    if rehearsing:
        content = shadow.note_line(bot, guild, f"<#{aimed}>" if aimed else "#?") or None
        allowed = discord.AllowedMentions.none()
    else:
        content = f"<@&{role}>" if role else None
        allowed = (
            discord.AllowedMentions(everyone=False, users=False, roles=[discord.Object(id=role)])
            if role
            else discord.AllowedMentions.none()
        )
    try:
        await channel.send(content, embed=embed_of(bot, guild, lines), allowed_mentions=allowed)
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        log.warning("points: the top-places post did not go out — %s", reason)
        if rehearsing:
            return NOT_POSTED
        return await failed(bot, guild, reason, home, lines, via)
    return REHEARSED if rehearsing else POSTED


__all__ = ["NOT_POSTED", "POSTED", "REHEARSED", "announce", "embed_of"]
