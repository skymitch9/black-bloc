"""The stale archive: off the list after enough failed reads, back on a read that works."""

from __future__ import annotations

import logging
from typing import Any

from ... import marathon_archive as ma
from ... import marathon_feeds as mf
from ... import marathon_stale as st
from ...actionlog import log_action
from ...settings_store import MARATHON_STALE_ARCHIVE_HOURS_KEY, MARATHON_STALE_ARCHIVE_READS_KEY
from . import marathon_signals as signals
from .marathon import cog_of, get_marathon, update_marathon
from .marathon_archive import archive_held, archived_marathon, restore_marathon

log = logging.getLogger(__name__)


async def archive_if_stale(cog: Any, guild: Any, before: Any) -> bool:
    """Called with the marathon's lock held, after a read of it failed."""
    bot = cog.bot
    fresh = await get_marathon(bot.db, guild.id, before["id"])
    if fresh is None or not st.counted(before, fresh):
        return False
    hours = bot.store.get(guild.id, MARATHON_STALE_ARCHIVE_HOURS_KEY)
    reads = bot.store.get(guild.id, MARATHON_STALE_ARCHIVE_READS_KEY)
    if not st.is_stale(fresh, cog.clock(), reads=reads, hours=hours):
        return False
    await log_action(
        bot, guild, "marathon.stale_archived", details=st.archived_details(fresh, hours)
    )
    return await archive_held(bot, guild, None, fresh, ma.STALE)


async def try_again(bot: Any, guild: Any, marathon_id: Any) -> bool:
    """One read of an archived marathon marked stale; only a read that works restores it."""
    cog = cog_of(bot)
    row = await archived_marathon(bot.db, guild.id, marathon_id)
    if not st.is_marked(row):
        return False
    try:
        runs = await cog.client.runs(
            row["source"],
            row["source_ref"],
            **signals.reader_for(bot, guild.id, row["source"]),
        )
    except Exception as exc:
        log.info("marathon: archived %s still does not read (%s)", row["id"], exc)
        return False
    done = await restore_marathon(bot, guild, None, row["id"], via=mf.VIA_FEED)
    if not done.ok:
        log.info("marathon: archived %s read but was not restored (%s)", row["id"], done.message)
        return False
    async with cog.lock(row["id"]):
        fresh = await get_marathon(bot.db, guild.id, row["id"])
        if fresh is None:
            return False
        await update_marathon(bot.db, fresh["id"], active=1 if row["active"] else 0)
        fresh = await get_marathon(bot.db, guild.id, row["id"])
        read = await cog.take(guild, fresh, runs, cog.clock())
    await log_action(
        bot,
        guild,
        "marathon.stale_restored",
        details={
            "marathon_id": row["id"],
            "name": row["name"],
            "runs": int((read.value or {}).get("runs") or 0),
        },
    )
    return True


__all__ = ["archive_if_stale", "try_again"]
