from __future__ import annotations

from typing import Any

from ... import marathon as mt
from ... import marathon_ping as mp
from ...actionlog import log_action
from ...logkinds import VIA_DISCORD, kind_via
from ...settings_store import (
    MARATHON_PING_ROLE_BUTTON_OFF_KEY,
    MARATHON_PING_ROLE_BUTTON_ON_KEY,
    MARATHON_PING_ROLE_DEFAULT_KEY,
    MARATHON_PING_ROLE_LINE_OFF_KEY,
    MARATHON_PING_ROLE_LINE_ON_KEY,
    MARATHON_PING_ROLE_OFF_SAID_KEY,
    MARATHON_PING_ROLE_ON_SAID_KEY,
    MARATHON_PING_ROLE_SAME_KEY,
)
from .marathon import (
    NO_SUCH,
    Outcome,
    cog_of,
    get_marathon,
    refusal,
    said_default,
    update_marathon,
)


def words(bot: Any, guild_id: int, key: str, **fields: Any) -> str:
    return mt.render(bot.store.get(guild_id, key), said_default(key), **fields).text


def default_for_new(bot: Any, guild_id: int) -> int:
    return 1 if bot.store.get(guild_id, MARATHON_PING_ROLE_DEFAULT_KEY) else 0


def card_line(bot: Any, guild_id: int, marathon: Any) -> str:
    if mp.pings_role(marathon):
        return words(bot, guild_id, MARATHON_PING_ROLE_LINE_ON_KEY)
    return words(bot, guild_id, MARATHON_PING_ROLE_LINE_OFF_KEY)


def card_move(bot: Any, guild_id: int, marathon: Any) -> Any:
    return mp.card_move(
        marathon,
        words(bot, guild_id, MARATHON_PING_ROLE_BUTTON_ON_KEY),
        words(bot, guild_id, MARATHON_PING_ROLE_BUTTON_OFF_KEY),
    )


async def set_ping_role(
    bot: Any, guild: Any, actor: Any, marathon: Any, given: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Off: no role in its reminders or shoutouts and no ping window; on: both come back."""
    wanted = mp.clean_ping_role(given)
    if wanted is None:
        return refusal(mp.BAD_PING_ROLE, mp.BAD_PING_ROLE_CODE, 422)
    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return refusal(mt.NO_SUCH_MARATHON.format(given=marathon["id"]), NO_SUCH, 404)
        was = mp.pings_role(fresh)
        if was == wanted:
            said = words(bot, guild.id, MARATHON_PING_ROLE_SAME_KEY, marathon=fresh["name"])
            return Outcome(True, said, value=fresh)
        await update_marathon(bot.db, fresh["id"], ping_role=1 if wanted else 0)
        fresh = await get_marathon(bot.db, guild.id, fresh["id"])
        await cog.sync_window(guild, fresh)
    await log_action(
        bot,
        guild,
        kind_via("marathon.ping_role_set", via),
        actor=actor,
        details={
            "marathon_id": fresh["id"],
            "name": fresh["name"],
            "from": was,
            "to": wanted,
            "spotlight_id": fresh["spotlight_id"],
            "via": via,
        },
    )
    key = MARATHON_PING_ROLE_ON_SAID_KEY if wanted else MARATHON_PING_ROLE_OFF_SAID_KEY
    return Outcome(
        True,
        words(bot, guild.id, key, marathon=fresh["name"]),
        value=await get_marathon(bot.db, guild.id, fresh["id"]),
    )


__all__ = ["card_line", "card_move", "default_for_new", "set_ping_role", "words"]
