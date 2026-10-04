"""A posted reminder follows its run: a move rewrites it in place, a run taken off the
schedule says so, and a message that is gone is forgotten."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import discord

from ... import marathon as mt
from ... import marathon_inbox as mi
from ... import marathon_reminder_posts as mrem
from ...actionlog import log_action
from ...settings_store import (
    MARATHON_PUBLIC_REMINDER_TEMPLATE_KEY,
    MARATHON_REMINDER_DROPPED_TEMPLATE_KEY,
    MARATHON_REMINDER_EDIT_LIMIT_KEY,
    MARATHON_REMINDER_ON_MOVE_KEY,
    MARATHON_REMINDER_TEMPLATE_KEY,
)
from ...spotlight import reason_of
from .marathon import (
    MODE_OFF,
    MODE_ON,
    get_marathon,
    mode_of,
    rehearsal_details,
    runs_of,
    update_run,
)
from .marathon_inbox import find_channel
from .marathon_public import people_for
from .marathon_public_reminders import public_url, reminder_text

log = logging.getLogger(__name__)

EDITED = "edited"
LOST = "lost"
FAILED = "failed"
NOT_READABLE = "channel not readable"
RETRY_AFTER = timedelta(minutes=10)
FOLLOWED = (mt.UPCOMING, mt.DROPPED)


def on_move(bot: Any, guild_id: int) -> str:
    return str(bot.store.get(guild_id, MARATHON_REMINDER_ON_MOVE_KEY))


def edits(bot: Any, guild: Any, marathon: Any) -> bool:
    """Posted reminders are followed at all: a tracked marathon, the feature on, the key at edit."""
    return (
        marathon is not None
        and mi.is_tracked(marathon)
        and mode_of(bot, guild.id) != MODE_OFF
        and on_move(bot, guild.id) == mrem.EDIT
    )


def tried(cog: Any) -> dict[int, tuple[str, Any]]:
    return cog.__dict__.setdefault("reminder_edit_tried", {})


def waits(cog: Any, copy: dict[str, Any], text: str) -> bool:
    """An edit that failed is tried again after a while, never every minute."""
    found = tried(cog).get(copy["message_id"])
    return found is not None and found[0] == text and cog.clock() < found[1]


def failed_first(cog: Any, copy: dict[str, Any], text: str) -> bool:
    """True the first time this edit fails: the one row it leaves."""
    found = tried(cog).get(copy["message_id"])
    tried(cog)[copy["message_id"]] = (text, cog.clock() + RETRY_AFTER)
    return found is None or found[0] != text


async def rewrite(cog: Any, guild: Any, copy: dict[str, Any], text: str) -> tuple[str, str | None]:
    """One edit that notifies nobody. Lost only when Discord says the message or its channel is
    gone, or that Black Bloc may not touch it."""
    channel, lost = await find_channel(cog.bot, guild, copy["channel_id"])
    if channel is None:
        return (LOST, mrem.GONE_CHANNEL) if lost else (FAILED, NOT_READABLE)
    try:
        message = await channel.fetch_message(int(copy["message_id"]))
        await message.edit(
            content=mrem.body(copy, text), allowed_mentions=discord.AllowedMentions.none()
        )
    except (discord.NotFound, LookupError):
        return (LOST, mrem.GONE_MESSAGE)
    except discord.Forbidden:
        return (LOST, mrem.GONE_PERMISSION)
    except Exception as exc:
        return (FAILED, reason_of(exc))
    tried(cog).pop(copy["message_id"], None)
    return (EDITED, None)


def followed(row: Any) -> bool:
    return bool(mt._cell(row, mrem.COLUMN)) and mt.is_ours(row) and row["state"] in FOLLOWED


async def run_text(cog: Any, guild: Any, marathon: Any, row: Any, name: str) -> str | None:
    """What this copy should say now; None leaves it alone (nobody of ours left to name)."""
    dropped = row["state"] == mt.DROPPED
    staff, url = await cog.reminder_words(
        guild,
        marathon,
        row,
        key=MARATHON_REMINDER_DROPPED_TEMPLATE_KEY if dropped else MARATHON_REMINDER_TEMPLATE_KEY,
    )
    if name == mrem.STAFF:
        return staff
    people = people_for(marathon, row)
    if not people:
        return None
    return reminder_text(
        cog.bot,
        guild,
        marathon,
        row,
        url=await public_url(cog.bot, marathon, row, people, url),
        people=people,
        key=MARATHON_REMINDER_DROPPED_TEMPLATE_KEY
        if dropped
        else MARATHON_PUBLIC_REMINDER_TEMPLATE_KEY,
    )


async def follow_run(cog: Any, guild: Any, marathon: Any, row: Any, budget: mrem.Budget) -> None:
    bot = cog.bot
    posts = mrem.of_run(row)
    changed = False
    for mark, name, copy in mrem.standing(posts):
        text = await run_text(cog, guild, marathon, row, name)
        if text is None or text == copy["text"] or waits(cog, copy, text):
            continue
        if not budget.take():
            continue
        outcome, why = await rewrite(cog, guild, copy, text)
        details = cog.run_details(marathon, row) | {
            "mark": mark,
            "copy": name,
            "from": copy["at"],
            "to": row["scheduled_at"],
            "dropped": row["state"] == mt.DROPPED,
            "message_id": str(copy["message_id"]),
            "channel_id": copy["channel_id"],
        }
        if outcome == EDITED:
            mrem.shown(posts, mark, name, text, row["scheduled_at"])
            changed = True
            await log_action(
                bot,
                guild,
                "marathon.would_edit_reminder"
                if mode_of(bot, guild.id) != MODE_ON
                else "marathon.reminder_edited",
                details=details | rehearsal_details(bot, guild),
            )
        elif outcome == LOST:
            mrem.forget(posts, mark, name)
            tried(cog).pop(copy["message_id"], None)
            changed = True
            await log_action(
                bot, guild, "marathon.reminder_lost", details=details | {"reason": why}
            )
        elif failed_first(cog, copy, text):
            await log_action(
                bot, guild, "marathon.reminder_edit_failed", details=details | {"reason": why}
            )
    if changed:
        await update_run(bot.db, row["id"], **{mrem.COLUMN: mrem.dump(posts)})


async def sync_runs(cog: Any, guild: Any, marathon: Any, budget: mrem.Budget) -> None:
    """The soonest run first, so a whole day that shifts corrects what is nearest."""
    rows = [one for one in await runs_of(cog.bot.db, marathon["id"]) if followed(one)]
    for row in sorted(rows, key=mt._when):
        await follow_run(cog, guild, marathon, row, budget)


async def sync_reminders(cog: Any, guild: Any, marathon: Any) -> mrem.Budget | None:
    """Every posted reminder says its run's time; unchanged costs no Discord call, and one pass
    makes at most marathon_reminder_edit_limit edits."""
    bot = cog.bot
    fresh = await get_marathon(bot.db, guild.id, marathon["id"]) if marathon else None
    if not edits(bot, guild, fresh):
        return None
    budget = mrem.Budget(bot.store.get(guild.id, MARATHON_REMINDER_EDIT_LIMIT_KEY))
    try:
        await sync_runs(cog, guild, fresh, budget)
    except Exception as exc:
        log.warning("marathon: following the posted reminders failed — %s", reason_of(exc))
    return budget


__all__ = ["edits", "follow_run", "on_move", "rewrite", "sync_reminders", "sync_runs"]
