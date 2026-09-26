from __future__ import annotations

from datetime import datetime
from typing import Any

from ... import marathon as mt
from ... import marathon_spotlight as ms
from ...actionlog import log_action
from ...logkinds import VIA_DISCORD, kind_via
from ...settings_store import (
    MARATHON_SPOTLIGHT_FOLLOWS_KEY,
    MARATHON_SPOTLIGHT_LEAD_MINUTES_KEY,
)
from ...spotlight import is_spotlit
from .marathon import (
    MODE_OFF,
    NO_SUCH,
    Outcome,
    cog_of,
    get_marathon,
    mode_of,
    now_for,
    refusal,
    update_marathon,
)
from .marathon_channels import locked, marathons_on_channel
from .spotlight import channel_by_id, settle_open_session, update_channel

BAD_MODE_CODE = "bad_spotlight_mode"


def enabled(bot: Any, guild_id: int) -> bool:
    return bool(bot.store.get(guild_id, MARATHON_SPOTLIGHT_FOLLOWS_KEY))


def lead_of(bot: Any, guild_id: int) -> int:
    return int(bot.store.get(guild_id, MARATHON_SPOTLIGHT_LEAD_MINUTES_KEY))


async def _row_of(bot: Any, guild: Any, marathon: Any) -> Any:
    spotlight_id = marathon["spotlight_id"] if marathon is not None else None
    if not spotlight_id:
        return None
    row = await channel_by_id(bot.db, int(spotlight_id))
    if row is None or int(row["guild_id"]) != int(guild.id):
        return None
    return row


async def follow_spotlight(
    bot: Any, guild: Any, marathon: Any, now: datetime | None = None
) -> str | None:
    """`set`, `extended`, or None when the row was left alone."""
    if marathon is None or mode_of(bot, guild.id) == MODE_OFF:
        return None
    row = await _row_of(bot, guild, marathon)
    at = now or now_for(bot)
    fields = ms.plan(
        row, marathon, at, enabled=enabled(bot, guild.id), lead_minutes=lead_of(bot, guild.id)
    )
    if fields is None:
        return None
    await update_channel(bot.db, int(row["id"]), **fields)
    fresh = await channel_by_id(bot.db, int(row["id"]))
    turned_on = "spotlight" in fields
    if turned_on:
        await settle_open_session(bot, guild, row, fresh, {"spotlight": 1})
    span = ms.span_of(marathon)
    await log_action(
        bot,
        guild,
        "marathon.spotlight_set" if turned_on else "marathon.spotlight_extended",
        details={
            "marathon_id": marathon["id"],
            "name": marathon["name"],
            "spotlight_id": row["id"],
            "login": row["twitch_login"],
            "span_starts_at": span[0].isoformat(),
            "span_ends_at": span[1].isoformat(),
            "from_expires_at": row["expires_at"],
            "expires_at": fields["expires_at"],
        },
    )
    return "set" if turned_on else "extended"


async def lift(bot: Any, guild: Any, row: Any, marathon_id: Any, because: str) -> Any:
    """A marathon's own spotlight given back: off, kept, and its pin off a live post."""
    await update_channel(bot.db, int(row["id"]), **ms.lifted_fields())
    fresh = await channel_by_id(bot.db, int(row["id"]))
    await settle_open_session(bot, guild, row, fresh, {"spotlight": 0})
    await log_action(
        bot,
        guild,
        "marathon.spotlight_lifted",
        details={
            "marathon_id": marathon_id,
            "spotlight_id": row["id"],
            "login": row["twitch_login"],
            "expires_at": row["expires_at"],
            "because": because,
        },
    )
    return fresh


async def after_staff_dim(
    bot: Any, guild: Any, actor: Any, was: Any, fresh: Any, *, via: str = VIA_DISCORD
) -> str:
    """Staff turned a channel's spotlight off: each marathon spotlighting it now stops for good,
    and a spotlight a marathon had turned on gives back its dates. The words for the answer."""
    if was is None or fresh is None or not is_spotlit(was) or is_spotlit(fresh):
        return ""
    held = ms.held_by(fresh)
    if held is not None:
        await update_channel(bot.db, int(fresh["id"]), expires_at=None, spotlit_by_marathon=None)
    hits = ms.dimmed_during(
        await marathons_on_channel(bot.db, guild.id, fresh["id"]),
        now_for(bot),
        enabled=enabled(bot, guild.id),
        lead_minutes=lead_of(bot, guild.id),
    )
    said: list[str] = []
    cog = cog_of(bot)
    for one in hits:
        async with locked(cog, one["id"]):
            await update_marathon(bot.db, one["id"], spotlight_mode=ms.OFF)
            again = await channel_by_id(bot.db, int(fresh["id"]))
            if again is not None and is_spotlit(again) and ms.held_by(again) == int(one["id"]):
                await lift(bot, guild, again, one["id"], ms.BECAUSE_STAFF_OFF)
        await log_action(
            bot,
            guild,
            kind_via("marathon.spotlight_mode_set", via),
            actor=actor,
            details={
                "marathon_id": one["id"],
                "name": one["name"],
                "from": ms.FOLLOW,
                "to": ms.OFF,
                "because": ms.BECAUSE_STAFF_OFF,
                "spotlight_id": fresh["id"],
                "via": via,
            },
        )
        said.append(ms.STAFF_OFF_CLAUSE.format(name=one["name"]))
    return " ".join(said)


async def set_spotlight_mode(
    bot: Any, guild: Any, actor: Any, marathon: Any, given: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    wanted = ms.clean_mode(given)
    if wanted is None:
        return refusal(ms.BAD_MODE, BAD_MODE_CODE, 422)
    async with locked(cog_of(bot), marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return refusal(mt.NO_SUCH_MARATHON.format(given=marathon["id"]), NO_SUCH, 404)
        was = ms.mode_of(fresh)
        if was == wanted:
            return Outcome(True, ms.MODE_SAME.format(name=fresh["name"]), value=fresh)
        await update_marathon(bot.db, fresh["id"], spotlight_mode=wanted)
        fresh = await get_marathon(bot.db, guild.id, fresh["id"])
        row = await _row_of(bot, guild, fresh)
        if wanted == ms.OFF:
            if row is not None and is_spotlit(row) and ms.held_by(row) == int(fresh["id"]):
                await lift(bot, guild, row, fresh["id"], ms.BECAUSE_MODE_OFF)
        else:
            await follow_spotlight(bot, guild, fresh)
    await log_action(
        bot,
        guild,
        kind_via("marathon.spotlight_mode_set", via),
        actor=actor,
        details={
            "marathon_id": fresh["id"],
            "name": fresh["name"],
            "from": was,
            "to": wanted,
            "via": via,
        },
    )
    said = ms.MODE_SAID[wanted].format(name=fresh["name"], lead=lead_of(bot, guild.id))
    return Outcome(True, said, value=await get_marathon(bot.db, guild.id, fresh["id"]))


__all__ = ["after_staff_dim", "follow_spotlight", "lift", "set_spotlight_mode"]
