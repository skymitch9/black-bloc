"""A tracked marathon's log rows post in its own thread under the log channel."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .logkinds import feature_of
from .settings_store import (
    MARATHON_DEFAULTS,
    MARATHON_LOG_THREAD_NAME_KEY,
    MARATHON_LOG_THREAD_OPENING_KEY,
    MARATHON_LOG_THREADS_KEY,
)

log = logging.getLogger(__name__)

FEATURE = "marathon"
MADE = "marathon.log_thread_made"
LOST = "marathon.log_thread_lost"
OWN_KINDS = (MADE, LOST)
LOCKS_ATTR = "_marathon_log_thread_locks"
REASON = "Black Bloc: the log for a tracked marathon"
COLUMNS = "id, name, starts_at, tracked_at, ignored_at, log_thread_id, log_thread_channel_id"


def marathon_id_of(details: Any) -> int | None:
    try:
        found = (details or {}).get("marathon_id")
        return int(found) if found not in (None, "") else None
    except (AttributeError, TypeError, ValueError):
        return None


def routed_id(bot: Any, guild: Any, kind: str, details: Any) -> int | None:
    if kind in OWN_KINDS or feature_of(kind) != FEATURE:
        return None
    marathon_id = marathon_id_of(details)
    if marathon_id is None or not bot.store.get(guild.id, MARATHON_LOG_THREADS_KEY):
        return None
    return marathon_id


def lock_for(bot: Any, guild_id: int, marathon_id: int) -> asyncio.Lock:
    locks = bot.__dict__.setdefault(LOCKS_ATTR, {})
    key = (int(guild_id), int(marathon_id))
    found = locks.get(key)
    if found is None:
        found = locks[key] = asyncio.Lock()
    return found


async def row_of(db: Any, guild_id: int, marathon_id: int) -> Any:
    cur = await db.conn.execute(
        f"SELECT {COLUMNS} FROM marathons WHERE guild_id = ? AND id = ?",
        (int(guild_id), int(marathon_id)),
    )
    return await cur.fetchone()


def words(bot: Any, guild_id: int, key: str, **fields: Any) -> str:
    from .marathon import render

    return render(bot.store.get(guild_id, key), str(MARATHON_DEFAULTS[key]), **fields).text


async def made_thread(bot: Any, guild: Any, row: Any, channel: Any, replaced: Any) -> Any:
    from . import marathon_inbox as mi
    from .actionlog import log_action
    from .cogs.content.marathon_inbox import make_thread
    from .marathon_thread_controls import tracker_url

    if not hasattr(channel, "create_thread"):
        raise TypeError(f"channel {channel.id} does not take threads")
    when = mi.date_of(row["starts_at"])
    url = tracker_url(getattr(getattr(bot, "settings", None), "origin", ""), row["id"]) or ""
    thread, _first = await make_thread(
        bot,
        channel,
        words(bot, guild.id, MARATHON_LOG_THREAD_NAME_KEY, marathon=row["name"], when=when),
        words(
            bot, guild.id, MARATHON_LOG_THREAD_OPENING_KEY, marathon=row["name"], when=when, url=url
        ),
        reason=REASON,
    )
    await bot.db.conn.execute(
        "UPDATE marathons SET log_thread_id = ?, log_thread_channel_id = ? WHERE id = ?",
        (int(thread.id), int(channel.id), int(row["id"])),
    )
    await bot.db.conn.commit()
    await log_action(
        bot,
        guild,
        "marathon.log_thread_made",
        details={
            "marathon_id": row["id"],
            "name": row["name"],
            "channel_id": int(channel.id),
            "thread_id": int(thread.id),
            "replaced": replaced,
        },
    )
    return thread


async def thread_for(bot: Any, guild: Any, kind: str, details: Any, channel: Any) -> Any:
    """The marathon's log thread when the row is routed there, else None (the channel)."""
    from . import marathon_inbox as mi

    marathon_id = routed_id(bot, guild, kind, details)
    if marathon_id is None or not mi.is_tracked(await row_of(bot.db, guild.id, marathon_id)):
        return None
    from .actionlog import log_action
    from .cogs.content.marathon_inbox import find_channel, reopened

    async with lock_for(bot, guild.id, marathon_id):
        row = await row_of(bot.db, guild.id, marathon_id)
        if not mi.is_tracked(row):
            return None
        stored = row["log_thread_id"]
        if stored and row["log_thread_channel_id"] == int(channel.id):
            thread, lost = await find_channel(bot, guild, stored)
            if thread is not None:
                return await reopened(thread)
            if not lost:
                raise LookupError(f"thread {stored} could not be read just now")
            await log_action(
                bot, guild, "marathon.log_thread_lost", details={"marathon_id": marathon_id, "thread_id": stored}
            )
        return await made_thread(bot, guild, row, channel, stored or None)


async def deliver(
    bot: Any, guild: Any, kind: str, details: Any, channel: Any, embed: Any
) -> None:
    """The embed goes to the marathon's log thread when it has one, else to the channel."""
    try:
        thread = await thread_for(bot, guild, kind, details, channel)
    except Exception as exc:
        log.warning(
            "action log: %s thread unusable, posted to the channel — %s: %s",
            kind,
            type(exc).__name__,
            exc,
        )
        thread = None
    if thread is not None:
        try:
            await thread.send(embed=embed)
            return
        except Exception as exc:
            log.warning(
                "action log: %s not posted in thread %s, posted to the channel — %s: %s",
                kind,
                getattr(thread, "id", "?"),
                type(exc).__name__,
                exc,
            )
    await channel.send(embed=embed)
