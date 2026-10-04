"""A posted reminder follows its run or its host block: a move rewrites it in place, a run
taken off the schedule says so, and a message that is gone is forgotten."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any, NamedTuple

import discord

from ... import marathon as mt
from ... import marathon_host_highlights as mhh
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
    channel_login,
    get_marathon,
    mode_of,
    rehearsal_details,
    runs_of,
    update_run,
)
from .marathon_host_highlights import block_text, speaking
from .marathon_host_highlights import details_of as block_details
from .marathon_host_highlights import save as save_blocks
from .marathon_inbox import find_channel, reopened
from .marathon_public import people_for
from .marathon_public_reminders import public_url, reminder_text

log = logging.getLogger(__name__)

EDITED = "edited"
LOST = "lost"
FAILED = "failed"
NOT_READABLE = "channel not readable"
RETRY_AFTER = timedelta(minutes=10)
FOLLOWED = (mt.UPCOMING, mt.DROPPED)


class Change(NamedTuple):
    outcome: str
    mark: int
    name: str
    copy: dict[str, Any]
    text: str
    why: str | None

    def details(self, at: Any, *, dropped: bool) -> dict[str, Any]:
        found = {
            "mark": self.mark,
            "copy": self.name,
            "from": self.copy["at"],
            "to": at,
            "dropped": dropped,
            "message_id": str(self.copy["message_id"]),
            "channel_id": self.copy["channel_id"],
        }
        return found if self.why is None else found | {"reason": self.why}


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
        message = await (await reopened(channel)).fetch_message(int(copy["message_id"]))
        await message.edit(
            content=mrem.body(copy, text), allowed_mentions=discord.AllowedMentions.none()
        )
    except (discord.NotFound, LookupError):
        return (LOST, mrem.GONE_MESSAGE)
    except discord.Forbidden:
        return (LOST, mrem.GONE_PERMISSION)
    except Exception as exc:
        return (FAILED, reason_of(exc))
    return (EDITED, None)


async def follow_copies(
    cog: Any,
    guild: Any,
    posts: dict[int, dict[str, Any]],
    budget: mrem.Budget,
    text_for: Callable[[str], Awaitable[str | None]],
    at: Any,
) -> list[Change]:
    """Every remembered copy whose words changed, edited once; `posts` is brought up to date
    and what happened comes back for its rows. A failure that was already logged is left out."""
    found: list[Change] = []
    for mark, name, copy in mrem.standing(posts):
        text = await text_for(name)
        if text is None or text == copy["text"] or waits(cog, copy, text):
            continue
        if not budget.take():
            continue
        outcome, why = await rewrite(cog, guild, copy, text)
        if outcome == FAILED:
            if failed_first(cog, copy, text):
                found.append(Change(outcome, mark, name, copy, text, why))
            continue
        tried(cog).pop(copy["message_id"], None)
        if outcome == EDITED:
            mrem.shown(posts, mark, name, text, at)
        else:
            mrem.forget(posts, mark, name)
        found.append(Change(outcome, mark, name, copy, text, why))
    return found


def stored(changes: list[Change]) -> bool:
    return any(one.outcome != FAILED for one in changes)


# --- a run's reminders -------------------------------------------------------------------------


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

    async def text_for(name: str) -> str | None:
        return await run_text(cog, guild, marathon, row, name)

    changes = await follow_copies(cog, guild, posts, budget, text_for, row["scheduled_at"])
    if stored(changes):
        await update_run(bot.db, row["id"], **{mrem.COLUMN: mrem.dump(posts)})
    for one in changes:
        details = cog.run_details(marathon, row) | one.details(
            row["scheduled_at"], dropped=row["state"] == mt.DROPPED
        )
        if one.outcome == EDITED:
            await log_action(
                bot,
                guild,
                "marathon.would_edit_reminder"
                if mode_of(bot, guild.id) != MODE_ON
                else "marathon.reminder_edited",
                details=details | rehearsal_details(bot, guild),
            )
        elif one.outcome == LOST:
            await log_action(bot, guild, "marathon.reminder_lost", details=details)
        else:
            await log_action(bot, guild, "marathon.reminder_edit_failed", details=details)


async def sync_runs(cog: Any, guild: Any, marathon: Any, budget: mrem.Budget) -> None:
    """The soonest run first, so a whole day that shifts corrects what is nearest."""
    rows = [one for one in await runs_of(cog.bot.db, marathon["id"]) if followed(one)]
    for row in sorted(rows, key=mt._when):
        await follow_run(cog, guild, marathon, row, budget)


# --- a host block's heads-ups ------------------------------------------------------------------


def blocks_followed(
    found: list[dict[str, Any]], runs: Any
) -> list[tuple[mhh.Block, dict[str, Any], bool]]:
    """(block, its record, dropped): every block still ahead whose record remembers a post, and
    every such record whose runs are all off the schedule."""
    used: set[int] = set()
    kept: list[tuple[mhh.Block, dict[str, Any], bool]] = []
    for block in mhh.blocks(runs):
        record = mhh.claim(found, block, used)
        if record is not None and mhh.state_of(block) == mhh.UPCOMING:
            kept.append((block, record, False))
    for record in found:
        if id(record) in used:
            continue
        block = mhh.left_behind(record, runs)
        if block is not None and mhh.is_dropped(block):
            kept.append((block, record, True))
    return sorted(
        (one for one in kept if mrem.standing(one[1][mrem.HOST_FIELD])),
        key=lambda one: mt._when(one[0].first),
    )


async def follow_block(
    cog: Any,
    guild: Any,
    marathon: Any,
    block: mhh.Block,
    record: dict[str, Any],
    dropped: bool,
    budget: mrem.Budget,
) -> bool:
    bot = cog.bot
    at = mt._cell(block.first, "scheduled_at")
    people = speaking(marathon, block)
    login = await channel_login(bot, marathon)

    async def text_for(name: str) -> str | None:
        if not people:
            return None
        return block_text(bot, guild, marathon, block, people, login, dropped=dropped)

    changes = await follow_copies(cog, guild, record[mrem.HOST_FIELD], budget, text_for, at)
    for one in changes:
        details = block_details(marathon, block, **one.details(at, dropped=dropped))
        if one.outcome == EDITED:
            await log_action(
                bot,
                guild,
                "marathon.would_edit_host_reminder"
                if mode_of(bot, guild.id) != MODE_ON
                else "marathon.host_reminder_edited",
                details=details | rehearsal_details(bot, guild),
            )
        elif one.outcome == LOST:
            await log_action(bot, guild, "marathon.host_reminder_lost", details=details)
        else:
            await log_action(bot, guild, "marathon.host_reminder_edit_failed", details=details)
    return stored(changes)


async def sync_blocks(cog: Any, guild: Any, marathon: Any, budget: mrem.Budget) -> None:
    """A block's start is its first run's; the record is saved once per block that changed, so
    an edit Discord took is never forgotten by a later failure."""
    bot = cog.bot
    found = mhh.records(marathon)
    if not any(mrem.standing(one[mrem.HOST_FIELD]) for one in found):
        return
    runs = await runs_of(bot.db, marathon["id"])
    for block, record, dropped in blocks_followed(found, runs):
        if await follow_block(cog, guild, marathon, block, record, dropped, budget):
            await save_blocks(bot, marathon, found)


async def sync_reminders(cog: Any, guild: Any, marathon: Any) -> mrem.Budget | None:
    """Every posted reminder says its run's time; unchanged costs no Discord call, and one pass
    makes at most marathon_reminder_edit_limit edits — runs first, then host blocks."""
    bot = cog.bot
    fresh = await get_marathon(bot.db, guild.id, marathon["id"]) if marathon else None
    if not edits(bot, guild, fresh):
        return None
    budget = mrem.Budget(bot.store.get(guild.id, MARATHON_REMINDER_EDIT_LIMIT_KEY))
    try:
        await sync_runs(cog, guild, fresh, budget)
        await sync_blocks(cog, guild, fresh, budget)
    except Exception as exc:
        log.warning("marathon: following the posted reminders failed — %s", reason_of(exc))
    return budget


__all__ = [
    "blocks_followed",
    "edits",
    "follow_block",
    "follow_copies",
    "follow_run",
    "on_move",
    "rewrite",
    "sync_blocks",
    "sync_reminders",
    "sync_runs",
]
