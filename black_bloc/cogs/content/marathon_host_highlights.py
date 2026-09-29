"""Each BaF host's public posts, once per host block, in the runner's words at the runner's
marks: a host never makes a run ours."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ... import marathon as mt
from ... import marathon_announce as ma
from ... import marathon_host_highlights as mhh
from ... import marathon_inbox as mi
from ... import shadow as shadow_home
from ...actionlog import log_action
from ...logkinds import VIA_DISCORD, kind_via
from ...settings_store import (
    MARATHON_HOST_HIGHLIGHTS_KEY,
    MARATHON_PING_MINUTES_KEY,
    MARATHON_REMINDER_MINUTES_KEY,
    MARATHON_REMINDER_STALE_KEY,
)
from ...spotlight import reason_of
from .marathon import (
    MODE_OFF,
    MODE_ON,
    channel_login,
    get_marathon,
    mode_of,
    runs_of,
    update_marathon,
)
from .marathon_announce import announces
from .marathon_hosts import scans
from .marathon_public import (
    edit_public,
    fetch_public,
    public_channel,
    public_text,
    rehearsal_of,
    send_public,
)
from .marathon_public_reminders import reminder_channel, reminder_text
from .marathon_public_reminders import wanted as public_reminders_wanted

log = logging.getLogger(__name__)

SHADOW_FEATURE = "marathon_public"


def switched_on(bot: Any, guild_id: int) -> bool:
    return bool(bot.store.get(guild_id, MARATHON_HOST_HIGHLIGHTS_KEY))


def wanted(bot: Any, guild: Any, marathon: Any) -> bool:
    """The host posts at all: the key, a tracked active marathon that scans its hosts."""
    return (
        switched_on(bot, guild.id)
        and bool(mt._cell(marathon, "active"))
        and mi.is_tracked(marathon)
        and mode_of(bot, guild.id) != MODE_OFF
        and scans(bot, guild.id, marathon)
    )


def speaking(marathon: Any, block: mhh.Block) -> list[dict[str, Any]]:
    """The block's hosts who are not opted out: the names its public posts carry."""
    return ma.kept(block.hosts, ma.opted_out(marathon))


def sent_cache(cog: Any, marathon_id: Any) -> dict[int, tuple[int | None, str]]:
    found = cog.__dict__.setdefault("host_sent", {})
    return found.setdefault(int(marathon_id), {})


def pointer(record: dict[str, Any]) -> dict[str, Any]:
    return {"public_message_id": record["message_id"], "public_channel_id": record["channel_id"]}


async def highlight_text(
    bot: Any, guild: Any, marathon: Any, block: mhh.Block, people: Any, *, removed: bool = False
) -> str:
    return await public_text(
        bot, guild, marathon, mhh.view_row(block), removed=removed, people=people or block.hosts
    )


def details_of(marathon: Any, block: mhh.Block, **extra: Any) -> dict[str, Any]:
    return {
        "marathon_id": marathon["id"],
        "run_id": block.start_run_id,
        "runs": block.run_ids,
        "members": block.user_ids,
        "hosts": block.names,
        "game": mt._cell(block.first, "game"),
    } | extra


async def save(bot: Any, marathon: Any, found: list[dict[str, Any]]) -> None:
    await update_marathon(bot.db, marathon["id"], **{mhh.COLUMN: mhh.dump(found)})


async def blocks_of(bot: Any, guild: Any, marathon: Any) -> list[mhh.Block]:
    if not scans(bot, guild.id, marathon):
        return []
    return mhh.blocks(await runs_of(bot.db, marathon["id"]))


def rehearsing(bot: Any, guild: Any) -> bool:
    return mode_of(bot, guild.id) != MODE_ON


def claimed(
    found: list[dict[str, Any]], found_blocks: list[mhh.Block]
) -> list[tuple[mhh.Block, dict[str, Any] | None]]:
    used: set[int] = set()
    return [(block, mhh.claim(found, block, used)) for block in found_blocks]


async def put_back(
    cog: Any,
    guild: Any,
    marathon: Any,
    block: mhh.Block,
    record: dict[str, Any],
    found: list[dict[str, Any]],
    people: Any,
    *,
    actor: Any,
    via: str,
) -> bool:
    """A post taken down comes back IN PLACE when it is still where one would go now."""
    bot = cog.bot
    home = (
        shadow_home.channel_id(bot, guild, feature=SHADOW_FEATURE)
        if rehearsing(bot, guild)
        else public_channel(bot, guild.id)
    )
    if home is None or record["channel_id"] != int(home):
        return False
    message, _lost = await fetch_public(bot, guild, pointer(record))
    text = await highlight_text(bot, guild, marathon, block, people)
    if message is None or await edit_public(bot, guild, message, text) is not None:
        return False
    record["removed"] = False
    await save(bot, marathon, found)
    sent_cache(cog, marathon["id"])[record["message_id"]] = (record["channel_id"], text)
    await log_action(
        bot,
        guild,
        kind_via("marathon.host_highlight_restored", via),
        actor=actor,
        details=details_of(marathon, block, message_id=str(message.id), via=via)
        | rehearsal_of(bot, guild),
    )
    return True


async def post_one(
    cog: Any,
    guild: Any,
    marathon: Any,
    block: mhh.Block,
    record: dict[str, Any],
    found: list[dict[str, Any]],
    people: Any,
) -> None:
    """`tried` is stored before the send, so a restart mid-send never posts it twice."""
    bot = cog.bot
    text = await highlight_text(bot, guild, marathon, block, people)
    base = details_of(marathon, block, auto=True, via=VIA_DISCORD)
    record["tried"] = True
    await save(bot, marathon, found)
    sent, channel_id, why = await send_public(bot, guild, text, [])
    if sent is None:
        await log_action(
            bot,
            guild,
            "marathon.host_highlight_failed",
            details=base | {"step": "post", "reason": why},
        )
        return
    record.update(message_id=int(sent.id), channel_id=int(channel_id), removed=False)
    await save(bot, marathon, found)
    sent_cache(cog, marathon["id"])[int(sent.id)] = (int(channel_id), text)
    await log_action(
        bot,
        guild,
        "marathon.would_post_host_highlight"
        if rehearsing(bot, guild)
        else "marathon.host_highlight_posted",
        details=base
        | {"message_id": str(sent.id), "channel_id": channel_id, "state": mhh.state_of(block)}
        | rehearsal_of(bot, guild),
    )


async def follow_one(
    cog: Any, guild: Any, marathon: Any, block: mhh.Block, record: dict[str, Any], people: Any
) -> bool:
    """An unchanged block costs no Discord call; a message deleted by hand is forgotten (True:
    the record changed)."""
    bot = cog.bot
    text = await highlight_text(bot, guild, marathon, block, people)
    cache = sent_cache(cog, marathon["id"])
    key = record["message_id"]
    if cache.get(key) == (record["channel_id"], text):
        return False
    message, lost = await fetch_public(bot, guild, pointer(record))
    if message is None:
        if not lost:
            return False
        cache.pop(key, None)
        await log_action(
            bot,
            guild,
            "marathon.host_highlight_lost",
            details=details_of(marathon, block, message_id=str(key)),
        )
        record.update(message_id=None, channel_id=None)
        return True
    if (getattr(message, "content", None) or "").endswith(text):
        cache[key] = (record["channel_id"], text)
        return False
    why = await edit_public(bot, guild, message, text)
    if why is not None:
        await log_action(
            bot,
            guild,
            "marathon.host_highlight_failed",
            details=details_of(marathon, block, step="edit", reason=why),
        )
        return False
    cache[key] = (record["channel_id"], text)
    await log_action(
        bot,
        guild,
        "marathon.would_edit_host_highlight"
        if rehearsing(bot, guild)
        else "marathon.host_highlight_edited",
        details=details_of(marathon, block, message_id=str(key), state=mhh.state_of(block))
        | rehearsal_of(bot, guild),
    )
    return False


async def sync_host_highlights(cog: Any, guild: Any, marathon: Any) -> None:
    """Every post that is up follows its block to the end, whatever the switches say now."""
    bot = cog.bot
    fresh = await get_marathon(bot.db, guild.id, marathon["id"]) if marathon else None
    if fresh is None or not mi.is_tracked(fresh) or mode_of(bot, guild.id) == MODE_OFF:
        return
    try:
        found = mhh.records(fresh)
        if not any(mhh.is_up(one) for one in found):
            return
        changed = False
        seen: set[int] = set()
        for block, record in claimed(found, await blocks_of(bot, guild, fresh)):
            if not mhh.is_up(record):
                continue
            seen.add(id(record))
            changed = mhh.attach(record, block) or changed
            if await follow_one(cog, guild, fresh, block, record, speaking(fresh, block)):
                changed = True
        runs = await runs_of(bot.db, fresh["id"])
        for record in found:
            if id(record) in seen or not mhh.is_up(record):
                continue
            block = mhh.left_behind(record, runs)
            if block is not None and await follow_one(
                cog, guild, fresh, block, record, speaking(fresh, block)
            ):
                changed = True
        if changed:
            await save(bot, fresh, found)
    except Exception as exc:
        log.warning("marathon: the host highlights failed — %s", reason_of(exc))


async def went_live(cog: Any, guild: Any, marathon: Any, run_id: Any) -> None:
    """A run of a host block goes live: the block's highlight is posted when the marathon's
    Auto-highlight and Runner/Host announcements are on, once per block."""
    bot = cog.bot
    try:
        fresh = await get_marathon(bot.db, guild.id, marathon["id"]) if marathon else None
        if fresh is None or not wanted(bot, guild, fresh) or not announces(bot, guild.id, fresh):
            return
        if public_channel(bot, guild.id) is None:
            return
        found = mhh.records(fresh)
        for block, record in claimed(found, await blocks_of(bot, guild, fresh)):
            if int(run_id) not in block.run_ids:
                continue
            people = speaking(fresh, block)
            if not people or not mhh.auto_wanted(fresh, block, record):
                return
            if record is None:
                record = mhh.new_record(block)
                found.append(record)
            mhh.attach(record, block)
            await post_one(cog, guild, fresh, block, record, found, people)
            return
    except Exception as exc:
        log.warning("marathon: a host auto-highlight failed — %s", reason_of(exc))


def reminder_marks(bot: Any, guild_id: int) -> tuple[int, ...]:
    """The runner's marks: every marathon_reminder_minutes mark, and the ping mark."""
    return mt.reminder_marks(
        bot.store.get(guild_id, MARATHON_REMINDER_MINUTES_KEY),
        int(bot.store.get(guild_id, MARATHON_PING_MINUTES_KEY)),
    )


async def remind_hosts(cog: Any, guild: Any, marathon: Any, now: datetime) -> None:
    """One public reminder per host block at every runner mark, measured from the block's
    first run; the mark is stored before the send, so a restart never posts it twice."""
    bot = cog.bot
    fresh = await get_marathon(bot.db, guild.id, marathon["id"]) if marathon else None
    if fresh is None or not wanted(bot, guild, fresh):
        return
    try:
        marks = reminder_marks(bot, guild.id)
        stale = int(bot.store.get(guild.id, MARATHON_REMINDER_STALE_KEY))
        found = mhh.records(fresh)
        for block, record in claimed(found, await blocks_of(bot, guild, fresh)):
            if record is not None:
                touched = mhh.attach(record, block)
                if record.pop("legacy_reminded", False):
                    record["marks"] = mhh.passed_marks(block, marks, now)
                    touched = True
                if mhh.rearmed(record, block, now) or touched:
                    await save(bot, fresh, found)
            mark, skipped = mhh.due(block, record, marks, now, stale_minutes=stale)
            if mark is None and not skipped:
                continue
            if record is None:
                record = mhh.new_record(block)
                found.append(record)
            record["marks"] = sorted(
                set(record["marks"]) | set(skipped) | ({mark} if mark is not None else set())
            )
            await save(bot, fresh, found)
            for one in skipped:
                await log_action(
                    bot,
                    guild,
                    "marathon.host_reminder_skipped",
                    details=details_of(fresh, block, mark=one, because="late"),
                )
            if mark is not None:
                await heads_up(bot, guild, fresh, block, mark)
    except Exception as exc:
        log.warning("marathon: a host heads-up failed — %s", reason_of(exc))


async def heads_up(bot: Any, guild: Any, marathon: Any, block: mhh.Block, mark: int) -> None:
    """The runner's public reminder for the block, unless the switches or the opt-out say not."""
    base = details_of(marathon, block, mark=mark)
    people = speaking(marathon, block)
    because = (
        "public_reminders_off"
        if not public_reminders_wanted(bot, guild.id)
        else "announcements_off"
        if not announces(bot, guild.id, marathon)
        else "opted_out"
        if not people
        else None
    )
    if because is not None:
        await log_action(
            bot, guild, "marathon.host_reminder_skipped", details=base | {"because": because}
        )
        return
    home = reminder_channel(bot, guild.id)
    if home is None:
        await log_action(
            bot, guild, "marathon.host_reminder_failed", details=base | {"reason": "no_channel"}
        )
        return
    login = await channel_login(bot, marathon)
    url = mt.run_url(block.first, login, marathon["schedule_url"], people=people)
    text = reminder_text(bot, guild, marathon, mhh.view_row(block), url=url, people=people)
    message, channel_id, why = await send_public(bot, guild, text, [], home=home)
    details = base | {
        "channel_id": channel_id,
        "message_id": str(getattr(message, "id", "")) or None,
    }
    if message is None:
        await log_action(
            bot, guild, "marathon.host_reminder_failed", details=details | {"reason": why}
        )
        return
    await log_action(
        bot,
        guild,
        "marathon.would_remind_host" if rehearsing(bot, guild) else "marathon.host_reminded",
        details=details | rehearsal_of(bot, guild),
    )


async def take_down(
    cog: Any,
    guild: Any,
    marathon: Any,
    block: mhh.Block,
    record: dict[str, Any],
    found: list[dict[str, Any]],
    *,
    actor: Any,
    via: str,
) -> None:
    """The decision is stored first; the edit to the taken-down line may fail on its own."""
    bot = cog.bot
    record["removed"] = True
    await save(bot, marathon, found)
    sent_cache(cog, marathon["id"]).pop(record["message_id"], None)
    message, _lost = await fetch_public(bot, guild, pointer(record))
    edited = False
    if message is not None:
        text = await highlight_text(bot, guild, marathon, block, None, removed=True)
        why = await edit_public(bot, guild, message, text)
        edited = why is None
        if why is not None:
            await log_action(
                bot,
                guild,
                kind_via("marathon.host_highlight_failed", via),
                actor=actor,
                details=details_of(marathon, block, step="remove", reason=why, via=via),
            )
    await log_action(
        bot,
        guild,
        kind_via("marathon.host_highlight_removed", via),
        actor=actor,
        details=details_of(
            marathon,
            block,
            message_id=str(record["message_id"]),
            edited=edited,
            via=via,
            because="opted_out",
        ),
    )


async def follow_opt(
    cog: Any, guild: Any, marathon: Any, user_ids: Any, *, actor: Any, via: str
) -> None:
    """After an opt-out a block's post that names nobody any more is taken down; after an
    opt-in one taken down comes back in place while its block is not over."""
    bot = cog.bot
    wanted_ids = {int(one) for one in user_ids}
    found = mhh.records(marathon)
    if not any(one.get("message_id") for one in found):
        return
    for block, record in claimed(found, await blocks_of(bot, guild, marathon)):
        if record is None or not record.get("message_id"):
            continue
        if not wanted_ids & set(block.user_ids):
            continue
        people = speaking(marathon, block)
        if mhh.is_up(record) and not people:
            await take_down(cog, guild, marathon, block, record, found, actor=actor, via=via)
        elif record["removed"] and people and mhh.state_of(block) != mhh.DONE:
            await put_back(cog, guild, marathon, block, record, found, people, actor=actor, via=via)


async def hosts_of(bot: Any, guild: Any, marathon: Any) -> dict[int, str]:
    """Every BaF host of the marathon's blocks, by id."""
    return {
        one["user_id"]: one["name"]
        for block in await blocks_of(bot, guild, marathon)
        for one in block.hosts
    }


__all__ = [
    "blocks_of",
    "follow_opt",
    "hosts_of",
    "remind_hosts",
    "speaking",
    "switched_on",
    "sync_host_highlights",
    "wanted",
    "went_live",
]
