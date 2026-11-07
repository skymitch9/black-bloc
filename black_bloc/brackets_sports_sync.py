"""The sports poller: one feed call per league and season a tick, shared by every bracket of it."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from . import brackets_sports as sports_
from . import brackets_store as store_
from . import brackets_thread as thread_
from .brackets import play
from .brackets.model import DONE
from .brackets_moves import OFF, league_of, mode_of
from .settings_store import BRACKETS_SYNC_IDLE_MINUTES, BRACKETS_SYNC_SECONDS
from .sports import feeds
from .sports.model import FINAL, LIVE

log = logging.getLogger(__name__)

SOON_MINUTES = 15
Group = tuple[str, str]


async def watched(bot: Any, guild: Any) -> dict[Group, list[Any]]:
    """Every running sports bracket with a feed, by the league and season its feed reads."""
    found: dict[Group, list[Any]] = {}
    for row in await store_.tournaments(bot.db, guild.id):
        if row["state"] != store_.RUNNING or not store_.fed(row):
            continue
        found.setdefault((league_of(row), str(row["season"] or "")), []).append(row)
    return found


async def busy(bot: Any, row: Any, now: datetime) -> bool:
    """A set being played, or one due to start within 15 minutes (or started and not final)."""
    cur = await bot.db.conn.execute(
        "SELECT state, live_status, scheduled_at FROM tournament_sets WHERE tournament_id = ?",
        (row["id"],),
    )
    soon = now + timedelta(minutes=SOON_MINUTES)
    for one in await cur.fetchall():
        if one["state"] in DONE or one["live_status"] == FINAL:
            continue
        if one["live_status"] == LIVE:
            return True
        starts = play.parsed(one["scheduled_at"]) if one["scheduled_at"] else None
        if starts is not None and starts <= soon:
            return True
    return False


async def interval(bot: Any, guild: Any, rows: list[Any], now: datetime) -> timedelta:
    for row in rows:
        if await busy(bot, row, now):
            return timedelta(seconds=int(bot.store.get(guild.id, BRACKETS_SYNC_SECONDS)))
    return timedelta(minutes=int(bot.store.get(guild.id, BRACKETS_SYNC_IDLE_MINUTES)))


async def sweep(
    bot: Any, guild: Any, last: dict[tuple[int, str, str], datetime], now: datetime | None = None
) -> dict[int, tuple[str, ...]]:
    """Each due group's feed is read once (never under a lock), then written to each bracket and
    its cards caught up; answers the set keys each tournament changed."""
    if getattr(guild, "unavailable", False) or mode_of(bot.store, guild.id) == OFF:
        return {}
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    owed: dict[int, tuple[str, ...]] = {}
    for (league, season), rows in (await watched(bot, guild)).items():
        mark = (int(guild.id), league, season)
        wait = await interval(bot, guild, rows, moment)
        if mark in last and moment - last[mark] < wait:
            continue
        last[mark] = moment
        answer = await feeds.bracket(league, season, fetch=sports_.fetch_of(bot))
        scores = None
        if answer.ok and any([await sports_.wants_scores(bot, row) for row in rows]):
            day = sports_.today_of(bot, guild, moment)
            scores = await feeds.scores(league, day, fetch=sports_.fetch_of(bot))
        for row in rows:
            try:
                found = await sports_.applied(bot, guild, row["id"], answer, scores)
            except Exception:
                log.exception("brackets: syncing tournament %s from its feed failed", row["id"])
                continue
            keys = tuple(found[0]) if found else ()
            fresh = await store_.tournament(bot.db, guild.id, row["id"])
            if fresh is None:
                continue
            flipped = bool(row["feed_failed_at"]) != bool(fresh["feed_failed_at"])
            if not keys and not flipped:
                continue
            if keys:
                owed[int(row["id"])] = keys
            try:
                await thread_.sync(bot, guild, fresh, keys=keys)
            except Exception:
                log.exception("brackets: the synced cards for tournament %s failed", row["id"])
    return owed


__all__ = ["SOON_MINUTES", "busy", "interval", "sweep", "watched"]
