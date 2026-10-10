"""A marathon tracked while one of its BaF runs is already live: that run is announced once."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ... import marathon as mt
from ... import marathon_inbox as mi
from ...actionlog import log_action
from ...golive import parse_ts
from ...settings_store import MARATHON_LATE_TRACK_SHOUT_KEY
from .marathon import get_marathon, runs_of, update_marathon

DUE = "late_shout_due"


def _cell(row: Any, key: str) -> Any:
    try:
        return row[key]
    except (IndexError, KeyError, TypeError):
        return None


def is_due(marathon: Any) -> bool:
    return bool(_cell(marathon, DUE))


async def arm(db: Any, marathon_id: Any) -> None:
    await update_marathon(db, int(marathon_id), **{DUE: 1})


def went_live_at(row: Any) -> datetime | None:
    for key in ("live_at", "actual_started_at", "scheduled_at"):
        found = parse_ts(_cell(row, key))
        if found is not None:
            return found
    return None


def age_minutes(row: Any, now: datetime) -> int | None:
    at = went_live_at(row)
    return None if at is None else max(0, int((now - at).total_seconds() // 60))


def too_old(age: int | None, cap: int) -> bool:
    return bool(cap) and (age is None or age > cap)


async def sweep(cog: Any, guild: Any, marathon: Any, now: datetime, *, skip: Any = ()) -> int:
    """The first tick after tracking: cleared before posting, so a failure is never retried."""
    bot = cog.bot
    if marathon is None:
        return 0
    marathon = await get_marathon(bot.db, guild.id, marathon["id"])
    if marathon is None or not is_due(marathon):
        return 0
    await update_marathon(bot.db, marathon["id"], **{DUE: 0})
    if not mi.is_tracked(marathon):
        return 0
    cap = int(bot.store.get(guild.id, MARATHON_LATE_TRACK_SHOUT_KEY))
    passed = {int(one) for one in skip}
    shouted = 0
    for row in await runs_of(bot.db, marathon["id"]):
        if int(row["id"]) in passed or row["state"] != mt.LIVE or not mt.is_ours(row):
            continue
        if row["shout_message_id"]:
            continue
        age = age_minutes(row, now)
        if too_old(age, cap):
            await log_action(
                bot,
                guild,
                "marathon.late_shout_skipped",
                details=cog.run_details(marathon, row)
                | {"age_minutes": age, "cap_minutes": cap, "live_at": row["live_at"]},
            )
            continue
        await cog.shout(guild, marathon, row)
        shouted += 1
    return shouted
