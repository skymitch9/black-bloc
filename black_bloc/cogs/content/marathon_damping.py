"""The one place a far-off run's move is held back from public posts, counted, and let go."""

from __future__ import annotations

from datetime import datetime
from typing import Any, NamedTuple

from ... import marathon as mt
from ... import marathon_damping as md
from ... import marathon_reminder_posts as mrem
from ...actionlog import log_action
from ...settings_store import (
    MARATHON_MOVE_DAMPING_MINUTES_KEY,
    MARATHON_MOVE_DAMPING_READS_KEY,
    MARATHON_MOVE_MINUTES_KEY,
    MARATHON_REMINDER_ON_MOVE_KEY,
)

READ = "schedule_read"
DAMPED_BECAUSE = (READ,)


class Written(NamedTuple):
    fields: dict[str, Any]
    held: bool
    before: Any
    let_go: bool = False

    def public(self, moved: bool, starts_at: Any, move_minutes: int) -> bool:
        """Whether the reminders are re-armed and the move logged now."""
        if self.held:
            return False
        if self.let_go:
            return md.moved_enough(self.before, starts_at, move_minutes)
        return moved


def minutes_of(bot: Any, guild_id: int) -> int:
    return int(bot.store.get(guild_id, MARATHON_MOVE_DAMPING_MINUTES_KEY) or 0)


def needed_of(bot: Any, guild_id: int) -> int:
    return md.reads_needed(bot.store.get(guild_id, MARATHON_MOVE_DAMPING_READS_KEY))


def written(
    bot: Any, guild_id: int, row: Any, starts_at: Any, now: datetime, *, because: str = READ
) -> Written:
    """What a new start does to the wait: the columns to store with it, whether the public
    follow-up waits, and the start public posts said before."""
    before = md.shown_start(row)
    if md.same(mt._cell(row, "scheduled_at"), starts_at):
        return Written({}, md.waits(row), before)
    if (
        because in DAMPED_BECAUSE
        and mt._cell(row, "state") == mt.UPCOMING
        and md.damped(minutes_of(bot, guild_id), now, before, starts_at)
    ):
        return Written(md.held_fields(row, starts_at), True, before)
    if md.pending(row):
        return Written(dict(md.CLEARED), False, before, True)
    return Written({}, False, before)


async def publish(cog: Any, guild: Any, marathon: Any, row: Any, now: datetime) -> bool:
    """The existing move path, measured from the start last published; True when it counted
    as a move."""
    from .marathon import update_run

    bot = cog.bot
    before, after = row[md.PUBLISHED], row["scheduled_at"]
    fields: dict[str, Any] = dict(md.CLEARED)
    moved = md.moved_enough(before, after, int(bot.store.get(guild.id, MARATHON_MOVE_MINUTES_KEY)))
    if moved:
        fields |= mrem.run_fields(
            row, after, now, str(bot.store.get(guild.id, MARATHON_REMINDER_ON_MOVE_KEY))
        )
    await update_run(bot.db, row["id"], **fields)
    if moved and mt.is_ours(row):
        for member_id in mt.member_ids(row):
            await log_action(
                bot,
                guild,
                "marathon.member_run_moved",
                target=member_id,
                details={
                    "marathon_id": marathon["id"],
                    "run_id": row["id"],
                    "member_id": member_id,
                    "game": row["game"],
                    "from": before,
                    "to": after,
                },
            )
    return moved


async def let_lapse(cog: Any, row: Any, now: datetime) -> None:
    """The move went back to what was published: nothing is said, and a mark skipped as late
    while it was away is due again."""
    from .marathon import update_run

    fields: dict[str, Any] = dict(md.CLEARED)
    if row["state"] == mt.UPCOMING:
        fields |= mrem.run_fields(row, row["scheduled_at"], now, mrem.EDIT)
    await update_run(cog.bot.db, row["id"], **fields)


async def hold(cog: Any, guild: Any, marathon: Any, row: Any, reads: int) -> None:
    from .marathon import update_run

    bot = cog.bot
    await update_run(bot.db, row["id"], **{md.READS: reads})
    if reads != 1 or not mt.is_ours(row):
        return
    move_minutes = int(bot.store.get(guild.id, MARATHON_MOVE_MINUTES_KEY))
    if not md.moved_enough(row[md.PUBLISHED], row["scheduled_at"], move_minutes):
        return
    await log_action(
        bot,
        guild,
        "marathon.move_held",
        details={
            "marathon_id": marathon["id"],
            "run_id": row["id"],
            "game": row["game"],
            "published": row[md.PUBLISHED],
            "candidate": row["scheduled_at"],
            "reads_needed": needed_of(bot, guild.id),
        },
    )


async def settle(cog: Any, guild: Any, marathon: Any, now: datetime, *, read: bool) -> int:
    """Every run whose move is waiting: a read counts it, a tick only lets go of one that
    came near, went back, or was moved by someone else. It answers how many were published."""
    from .marathon import runs_of

    bot = cog.bot
    minutes, needed = minutes_of(bot, guild.id), needed_of(bot, guild.id)
    published = 0
    for row in await runs_of(bot.db, marathon["id"]):
        found = md.step(row, now, minutes=minutes, needed=needed, read=read)
        if found.what == md.CLEAR:
            await let_lapse(cog, row, now)
        elif found.what == md.PUBLISH:
            await publish(cog, guild, marathon, row, now)
            published += 1
        elif found.what == md.HOLD:
            await hold(cog, guild, marathon, row, found.reads)
    return published


__all__ = [
    "DAMPED_BECAUSE",
    "READ",
    "Written",
    "hold",
    "let_lapse",
    "minutes_of",
    "needed_of",
    "publish",
    "settle",
    "written",
]
