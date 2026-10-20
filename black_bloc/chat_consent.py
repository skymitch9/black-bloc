"""chat_memory_consent changes only after staff see how many people it moves, and it moves rows."""

from __future__ import annotations

from typing import Any

from . import optouts
from .chat_memory import CONSENT_KEY, OPTIN, OPTOUT
from .settings_store import (
    CHAT_MEMORY_CONSENT_CONFIRM_IN_KEY,
    CHAT_MEMORY_CONSENT_CONFIRM_OUT_KEY,
)

CONFIRM_CODE = "confirm_needed"
ASKS = {OPTIN: CHAT_MEMORY_CONSENT_CONFIRM_OUT_KEY, OPTOUT: CHAT_MEMORY_CONSENT_CONFIRM_IN_KEY}


def humans(guild: Any) -> set[int]:
    found = getattr(guild, "members", None) or ()
    members = list(found.values() if isinstance(found, dict) else found)
    return {int(one.id) for one in members if not getattr(one, "bot", False)}


async def _implicit(db: Any, guild_id: int) -> set[int]:
    return {
        int(row["user_id"])
        for row in await optouts.rows(db, guild_id, (optouts.CHAT_MEMORY,))
        if row["reason"] == optouts.IMPLICIT
    }


async def changing(db: Any, guild: Any, to: str) -> list[int]:
    """Who the move to `to` turns: out of memory for optin, back into it for optout."""
    out = await optouts.out_of(db, guild.id, optouts.CHAT_MEMORY)
    kept_in = await optouts.out_of(db, guild.id, optouts.CHAT_MEMORY_IN)
    if to == OPTIN:
        return sorted(one for one in humans(guild) if one not in out and one not in kept_in)
    implicit = await _implicit(db, guild.id)
    chose_out = out - implicit
    return sorted(
        one
        for one in humans(guild)
        if one not in chose_out and (one not in kept_in or one in implicit)
    )


def current(bot: Any, guild: Any) -> str:
    return str(bot.store.get(guild.id, CONSENT_KEY) or OPTOUT)


async def asked(bot: Any, guild: Any, value: Any) -> str | None:
    """The count sentence staff confirm, or None when nothing would change."""
    wanted = str(value or OPTOUT)
    if wanted == current(bot, guild) or wanted not in ASKS:
        return None
    moved = await changing(bot.db, guild, wanted)
    return optouts.said(bot.store, guild.id, ASKS[wanted], count=len(moved))


async def flipped(bot: Any, guild: Any, was: Any, now: Any, actor: Any) -> dict[str, Any] | None:
    """At the flip the people it moved get rows of their own, so no row changes meaning. The
    count rides on the settings.set row: one write, one row."""
    before, after = str(was or OPTOUT), str(now or OPTOUT)
    if before == after:
        return None
    moved = await changing(bot.db, guild, after)
    by = int(getattr(actor, "id", actor) or 0) or None
    if after == OPTIN:
        for user_id in moved:
            await optouts.set_out(
                bot.db,
                guild.id,
                user_id,
                optouts.CHAT_MEMORY,
                by=by,
                reason=optouts.IMPLICIT,
                commit=False,
            )
    else:
        for user_id in await _implicit(bot.db, guild.id):
            await optouts.clear_out(bot.db, guild.id, user_id, optouts.CHAT_MEMORY, commit=False)
    await bot.db.conn.commit()
    return {"from": before, "to": after, "count": len(moved)}


__all__ = ["CONFIRM_CODE", "asked", "changing", "flipped", "humans"]
