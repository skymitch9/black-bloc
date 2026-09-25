from __future__ import annotations

from contextlib import nullcontext
from typing import Any

from ... import marathon_channels as mc
from ...actionlog import log_action
from ...logkinds import VIA_BOOT, VIA_DISCORD, kind_via
from .marathon import (
    HELD_CODE,
    OPTED_OUT_CODE,
    cog_of,
    get_marathon,
    opted_out_channel,
    opted_out_said,
    update_marathon,
)
from .spotlight import channel_by_id, update_channel


async def marathons_on_channel(db: Any, guild_id: int, spotlight_id: Any) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM marathons WHERE guild_id = ? AND spotlight_id = ? ORDER BY id",
        (int(guild_id), int(spotlight_id)),
    )
    return list(await cur.fetchall())


def locked(cog: Any, marathon_id: Any) -> Any:
    return cog.lock(marathon_id) if cog is not None else nullcontext()


async def set_marathons(
    bot: Any, guild: Any, actor: Any, spotlight_id: Any, on: bool, *, via: str = VIA_DISCORD
) -> tuple[Any, str]:
    """`(row, said)`; the row is None when it is not this server's. The flag moves first, then
    what hangs off it: the feed and the marathons on the channel are held or let go."""
    row = await channel_by_id(bot.db, int(spotlight_id))
    if row is None or int(row["guild_id"]) != int(guild.id):
        return (None, "")
    login = row["twitch_login"]
    was = mc.takes_marathons(row)
    if was == bool(on):
        return (row, mc.MARATHONS_SAME.format(login=login, state=mc.TAKES_WORDS[was]))
    await update_channel(bot.db, int(row["id"]), marathons=1 if on else 0)
    await log_action(
        bot,
        guild,
        kind_via("golive.channel_marathons_set", via),
        actor=actor,
        details={
            "spotlight_id": int(row["id"]),
            "login": login,
            "from": was,
            "to": bool(on),
            "via": via,
        },
    )
    fresh = await channel_by_id(bot.db, int(row["id"]))
    if on:
        count = await release(bot, guild, fresh)
        return (fresh, mc.MARATHONS_ON_SAID.format(login=login, count=count))
    count = await hold(bot, guild, fresh)
    return (fresh, mc.MARATHONS_OFF_SAID.format(login=login, count=count))


async def hold(bot: Any, guild: Any, channel: Any) -> int:
    """Opted out: its feed and every active marathon on it pause, marked as held by the channel."""
    from .marathon_feeds import feed_by_channel, feed_details, update_feed

    feed = await feed_by_channel(bot.db, guild.id, channel["id"])
    if feed is not None and feed["active"]:
        await update_feed(bot.db, feed["id"], active=0, held_by_channel=1)
        await log_action(
            bot,
            guild,
            "marathon.feed_paused",
            details=feed_details(feed, "feed", because=mc.BECAUSE_OPTED_OUT),
        )
    held = 0
    cog = cog_of(bot)
    for row in await marathons_on_channel(bot.db, guild.id, channel["id"]):
        if not row["active"]:
            continue
        async with locked(cog, row["id"]):
            await update_marathon(bot.db, row["id"], active=0, held_by_channel=1)
            if cog is not None:
                await cog.sync_window(guild, await get_marathon(bot.db, guild.id, row["id"]))
        held += 1
        await log_action(
            bot,
            guild,
            "marathon.paused",
            details={
                "marathon_id": row["id"],
                "name": row["name"],
                "because": mc.BECAUSE_OPTED_OUT,
                "automatic": True,
            },
        )
    return held


async def release(bot: Any, guild: Any, channel: Any) -> int:
    """Back on: only what the opt-out paused comes back; a pause staff made stays."""
    from .marathon_feeds import feed_by_channel, feed_details, update_feed

    feed = await feed_by_channel(bot.db, guild.id, channel["id"])
    if feed is not None and feed["held_by_channel"]:
        await update_feed(bot.db, feed["id"], active=1, held_by_channel=0)
        await log_action(
            bot,
            guild,
            "marathon.feed_resumed",
            details=feed_details(feed, "feed", because=mc.BECAUSE_OPTED_IN),
        )
    released = 0
    cog = cog_of(bot)
    for row in await marathons_on_channel(bot.db, guild.id, channel["id"]):
        if not row["held_by_channel"]:
            continue
        async with locked(cog, row["id"]):
            await update_marathon(bot.db, row["id"], active=1, held_by_channel=0)
            if cog is not None:
                await cog.sync_window(guild, await get_marathon(bot.db, guild.id, row["id"]))
        released += 1
        await log_action(
            bot,
            guild,
            "marathon.resumed",
            details={
                "marathon_id": row["id"],
                "name": row["name"],
                "because": mc.BECAUSE_OPTED_IN,
                "automatic": True,
            },
        )
    return released


async def seed_opt_outs(bot: Any, guild: Any) -> list[str]:
    """Once per channel, ever, beside the feed seeds: ESA starts opted out; staff may turn it on."""
    from .marathon_feeds import channel_by_login_in, is_seeded, mark_seeded

    made: list[str] = []
    for login in mc.OPTED_OUT_SEEDS:
        key = mc.seed_key(login)
        if await is_seeded(bot.db, guild.id, key):
            continue
        channel = await channel_by_login_in(bot.db, guild.id, login)
        if channel is None:
            continue
        if mc.takes_marathons(channel):
            await set_marathons(bot, guild, None, channel["id"], False, via=VIA_BOOT)
            made.append(login)
        await mark_seeded(bot.db, guild.id, key)
    return made


__all__ = [
    "HELD_CODE",
    "OPTED_OUT_CODE",
    "hold",
    "marathons_on_channel",
    "opted_out_channel",
    "opted_out_said",
    "release",
    "seed_opt_outs",
    "set_marathons",
]
