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
from ... import marathon_reminder_posts as mrem
from ... import marathon_role_ping as mrp
from ... import shadow as shadow_home
from ...actionlog import log_action
from ...golive import ping_prefix
from ...logkinds import VIA_DISCORD, kind_via
from ...settings_store import (
    MARATHON_HOST_HIGHLIGHTS_KEY,
    MARATHON_PING_MINUTES_KEY,
    MARATHON_REMINDER_DROPPED_TEMPLATE_KEY,
    MARATHON_REMINDER_MINUTES_KEY,
    MARATHON_REMINDER_ON_MOVE_KEY,
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
from .marathon_public import (
    edit_public,
    fetch_public,
    people_for,
    public_channel,
    public_text,
    rehearsal_of,
    send_public,
    since,
    stands,
)
from .marathon_public_reminders import reminder_channel, reminder_text
from .marathon_public_reminders import wanted as public_reminders_wanted
from .marathon_role_ping import verdict_for

log = logging.getLogger(__name__)

SHADOW_FEATURE = "marathon_public"


def switched_on(bot: Any, guild_id: int) -> bool:
    return bool(bot.store.get(guild_id, MARATHON_HOST_HIGHLIGHTS_KEY))


def wanted(bot: Any, guild: Any, marathon: Any) -> bool:
    """The host posts at all: the key, a tracked active marathon."""
    return (
        switched_on(bot, guild.id)
        and bool(mt._cell(marathon, "active"))
        and mi.is_tracked(marathon)
        and mode_of(bot, guild.id) != MODE_OFF
    )


def speaking(
    bot: Any,
    guild: Any,
    marathon: Any,
    block: mhh.Block,
    *,
    standing: bool = False,
    recorded: Any = None,
    moved: Any = (),
) -> list[dict[str, Any]]:
    """The block's hosts its public posts name: each one announced for a run of it."""
    from .marathon_announce import speaking as announced

    return announced(
        bot,
        guild,
        marathon,
        block,
        standing=standing,
        recorded=recorded,
        moved=moved,
        done=mhh.state_of(block) == mhh.DONE,
    )


def written(block: mhh.Block, was: Any) -> list[dict[str, Any]]:
    """Who a block's highlight named, as it wrote them: its record, else the block's hosts."""
    from .marathon_announce import as_written

    return as_written(was) if was else block.hosts


def why_down(bot: Any, guild: Any, marathon: Any, block: mhh.Block, was: Any, moved: Any) -> str:
    from .marathon_announce import policy_of

    named = was if was is not None else block.hosts
    return ma.block_because(block, policy_of(bot, guild.id, marathon), named, moved)


def sent_cache(cog: Any, marathon_id: Any) -> dict[int, tuple[int | None, str]]:
    found = cog.__dict__.setdefault("host_sent", {})
    return found.setdefault(int(marathon_id), {})


def pointer(record: dict[str, Any]) -> dict[str, Any]:
    return {"public_message_id": record["message_id"], "public_channel_id": record["channel_id"]}


async def highlight_text(
    bot: Any, guild: Any, marathon: Any, block: mhh.Block, people: Any, *, removed: bool = False
) -> str:
    return await public_text(
        bot,
        guild,
        marathon,
        mhh.view_row(block),
        removed=removed,
        people=people,
        over=block.runs[-1],
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
    record["named"] = ma.as_named(people)
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
    record.update(
        message_id=int(sent.id),
        channel_id=int(channel_id),
        removed=False,
        named=ma.as_named(people),
    )
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
    if await stands(
        cog,
        guild,
        marathon,
        mhh.view_row(block),
        message,
        text,
        people=people,
        over=block.runs[-1],
    ):
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


async def follow_named(
    cog: Any,
    guild: Any,
    marathon: Any,
    block: mhh.Block,
    record: dict[str, Any],
    found: list[dict[str, Any]],
) -> bool:
    """A post that is up follows its block with the hosts it names; one that names nobody any
    more is taken down while its block is not over, and left as it stands after. True: the
    record changed."""
    was = record.get("named")
    people = speaking(cog.bot, guild, marathon, block, standing=True, recorded=was)
    if not people:
        if mhh.state_of(block) == mhh.DONE:
            return False
        await take_down(cog, guild, marathon, block, record, found, actor=None, via=VIA_DISCORD)
        return True
    changed = ma.as_named(people) != was
    record["named"] = ma.as_named(people)
    return await follow_one(cog, guild, marathon, block, record, people) or changed


async def skipped(
    bot: Any,
    guild: Any,
    marathon: Any,
    block: mhh.Block,
    record: dict[str, Any] | None,
    found: list[dict[str, Any]],
) -> None:
    """A highlight that would have gone up but names nobody: one row a block saying why."""
    if not mhh.auto_wanted(marathon, block, record) or (record or {}).get("skipped"):
        return
    if record is None:
        record = mhh.new_record(block)
        found.append(record)
    mhh.attach(record, block)
    record["skipped"] = True
    await save(bot, marathon, found)
    await log_action(
        bot,
        guild,
        "marathon.host_highlight_skipped",
        details=details_of(marathon, block, because=quiet_because(bot, guild, marathon, block)),
    )


async def sync_host_highlights(cog: Any, guild: Any, marathon: Any) -> None:
    """Every post that is up follows its block to the end, whatever the switches say now."""
    bot = cog.bot
    fresh = await get_marathon(bot.db, guild.id, marathon["id"]) if marathon else None
    if fresh is None or not mi.is_tracked(fresh) or mode_of(bot, guild.id) == MODE_OFF:
        return
    try:
        found = mhh.records(fresh)
        since(cog)
        if not any(mhh.is_up(one) for one in found):
            return
        changed = False
        seen: set[int] = set()
        for block, record in claimed(found, await blocks_of(bot, guild, fresh)):
            if not mhh.is_up(record):
                continue
            seen.add(id(record))
            changed = mhh.attach(record, block) or changed
            if await follow_named(cog, guild, fresh, block, record, found):
                changed = True
        runs = await runs_of(bot.db, fresh["id"])
        for record in found:
            if id(record) in seen or not mhh.is_up(record):
                continue
            block = mhh.left_behind(record, runs)
            if block is not None and await follow_named(cog, guild, fresh, block, record, found):
                changed = True
        if changed:
            await save(bot, fresh, found)
    except Exception as exc:
        log.warning("marathon: the host highlights failed — %s", reason_of(exc))


async def went_live(cog: Any, guild: Any, marathon: Any, run_id: Any) -> None:
    """A run of a host block goes live: the block's highlight is posted when the marathon's
    Auto-highlight is on and a host of it is announced, once per block."""
    bot = cog.bot
    try:
        fresh = await get_marathon(bot.db, guild.id, marathon["id"]) if marathon else None
        if fresh is None or not wanted(bot, guild, fresh):
            return
        if public_channel(bot, guild.id) is None:
            return
        found = mhh.records(fresh)
        for block, record in claimed(found, await blocks_of(bot, guild, fresh)):
            if int(run_id) not in block.run_ids:
                continue
            people = speaking(bot, guild, fresh, block)
            if not people:
                await skipped(bot, guild, fresh, block, record, found)
                return
            if not mhh.auto_wanted(fresh, block, record):
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
        on_move = str(bot.store.get(guild.id, MARATHON_REMINDER_ON_MOVE_KEY))
        found = mhh.records(fresh)
        for block, record in claimed(found, await blocks_of(bot, guild, fresh)):
            if record is not None:
                touched = mhh.attach(record, block)
                if record.pop("legacy_reminded", False):
                    record["marks"] = mhh.passed_marks(block, marks, now)
                    touched = True
                if mhh.rearmed(record, block, now, on_move) or touched:
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
            record[mrem.HOST_FIELD] = mrem.with_skipped(record[mrem.HOST_FIELD], skipped)
            await save(bot, fresh, found)
            for one in skipped:
                await log_action(
                    bot,
                    guild,
                    "marathon.host_reminder_skipped",
                    details=details_of(fresh, block, mark=one, because="late"),
                )
            if mark is not None:
                copy = await heads_up(bot, guild, fresh, block, mark)
                record[mrem.HOST_FIELD][mark] = mrem.entry_of(public=copy)
                await save(bot, fresh, found)
    except Exception as exc:
        log.warning("marathon: a host heads-up failed — %s", reason_of(exc))


def block_text(
    bot: Any,
    guild: Any,
    marathon: Any,
    block: mhh.Block,
    people: Any,
    login: Any,
    *,
    dropped: bool = False,
) -> str:
    """The block's heads-up as it reads now; `dropped` once every run of it is off the schedule."""
    url = mt.run_url(block.first, login, marathon["schedule_url"], people=people)
    if dropped:
        return reminder_text(
            bot,
            guild,
            marathon,
            mhh.dropped_row(block),
            url=url,
            people=people,
            key=MARATHON_REMINDER_DROPPED_TEMPLATE_KEY,
        )
    return reminder_text(bot, guild, marathon, mhh.view_row(block), url=url, people=people)


async def heads_up(
    bot: Any, guild: Any, marathon: Any, block: mhh.Block, mark: int
) -> dict[str, Any] | None:
    """The runner's public reminder for the block, unless the switches or the opt-out say not.
    It answers the post, for the block to remember."""
    marathon_role = role_for(
        bot, guild, marathon, block, mark, await day_reading(bot, guild, marathon, mark)
    )
    quiet = mrp.row_fields(
        None if marathon_role is None else mrp.unsent(marathon_role, mrp.NO_PUBLIC_COPY)
    )
    base = details_of(marathon, block, mark=mark)
    people = speaking(bot, guild, marathon, block)
    because = (
        "public_reminders_off"
        if not public_reminders_wanted(bot, guild.id)
        else quiet_because(bot, guild, marathon, block)
        if not people
        else None
    )
    if because is not None:
        await log_action(
            bot,
            guild,
            "marathon.host_reminder_skipped",
            details=base | quiet | {"because": because},
        )
        return None
    home = reminder_channel(bot, guild.id)
    if home is None:
        await log_action(
            bot,
            guild,
            "marathon.host_reminder_failed",
            details=base | quiet | {"reason": "no_channel"},
        )
        return None
    text = block_text(bot, guild, marathon, block, people, await channel_login(bot, marathon))
    named = ma.ids_of(people)
    roles = mrp.with_role([], marathon_role)
    message, channel_id, why = await send_public(
        bot, guild, ping_prefix(*roles) + text, roles, home=home
    )
    details = base | {
        "channel_id": channel_id,
        "message_id": str(getattr(message, "id", "")) or None,
    }
    if message is None:
        await log_action(
            bot,
            guild,
            "marathon.host_reminder_failed",
            details=details | quiet | {"reason": why},
        )
        return None
    await log_action(
        bot,
        guild,
        "marathon.would_remind_host" if rehearsing(bot, guild) else "marathon.host_reminded",
        details=details
        | {"pinged": bool(roles), "roles": roles}
        | mrp.row_fields(marathon_role)
        | rehearsal_of(bot, guild),
    )
    return mrem.copy_of(
        message, channel_id, text, mt._cell(block.first, "scheduled_at"), people=named
    )


def quiet_because(bot: Any, guild: Any, marathon: Any, block: mhh.Block) -> str:
    """Why a block names nobody: the host default, unless turning it on would change nothing."""
    from .marathon_announce import policy_of

    found = policy_of(bot, guild.id, marathon)
    if not found.hosts_on and ma.block_people(block, found._replace(hosts_on=True)):
        return "host_announcements_off"
    return "opted_out"


async def day_reading(bot: Any, guild: Any, marathon: Any, mark: int) -> Any:
    """The marathon's show-days, read only for the mark that could carry the role."""
    from .marathon_baf_event import reading_now

    if mark != int(bot.store.get(guild.id, MARATHON_PING_MINUTES_KEY)):
        return None
    return await reading_now(bot, guild, marathon)


def role_for(
    bot: Any, guild: Any, marathon: Any, block: mhh.Block, mark: int, days: Any = None
) -> mrp.Verdict | None:
    """At the ping mark only; a block opening on a BaF run leaves it to that run's own copy,
    and a block on a BaF event day leaves it to the day's one ping."""
    from .marathon_baf_event import quiet_for

    if mark != int(bot.store.get(guild.id, MARATHON_PING_MINUTES_KEY)):
        return None
    verdict = verdict_for(bot, guild, marathon)
    quiet = quiet_for(days, block.first, verdict)
    if quiet is not None:
        return quiet
    if mt.is_ours(block.first) and people_for(bot, guild, marathon, block.first):
        return mrp.unsent(verdict, mrp.RUNNER_COPY)
    return verdict


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
    moved: Any = (),
) -> None:
    """The decision is stored first; the edit to the taken-down line may fail on its own. The
    line names who the post named."""
    bot = cog.bot
    was = record.get("named")
    because = why_down(bot, guild, marathon, block, was, moved)
    record["removed"] = True
    await save(bot, marathon, found)
    sent_cache(cog, marathon["id"]).pop(record["message_id"], None)
    message, _lost = await fetch_public(bot, guild, pointer(record))
    edited = False
    if message is not None:
        text = await highlight_text(bot, guild, marathon, block, written(block, was), removed=True)
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
            because=because,
        ),
    )


async def follow_opt(
    cog: Any, guild: Any, marathon: Any, user_ids: Any, *, actor: Any, via: str
) -> None:
    """After an answer changed a block's post that names nobody any more is taken down, one
    that still names someone is rewritten in place, and one taken down comes back in place
    while its block is not over and Host announcements is on. Only the hosts the move was
    aimed at are weighed afresh."""
    bot = cog.bot
    wanted_ids = {int(one) for one in user_ids}
    found = mhh.records(marathon)
    if not any(one.get("message_id") for one in found):
        return
    changed = False
    for block, record in claimed(found, await blocks_of(bot, guild, marathon)):
        if record is None or not record.get("message_id"):
            continue
        was = record.get("named")
        if not wanted_ids & (set(block.user_ids) | set(ma.ids_of(was) or ())):
            continue
        still = speaking(bot, guild, marathon, block, standing=True, recorded=was, moved=wanted_ids)
        if mhh.is_up(record) and not still:
            await take_down(
                cog,
                guild,
                marathon,
                block,
                record,
                found,
                actor=actor,
                via=via,
                moved=wanted_ids,
            )
        elif mhh.is_up(record):
            record["named"] = ma.as_named(still)
            await save(bot, marathon, found)
            changed = True
        elif record["removed"] and mhh.state_of(block) != mhh.DONE:
            people = speaking(bot, guild, marathon, block)
            if people:
                await put_back(
                    cog, guild, marathon, block, record, found, people, actor=actor, via=via
                )
    if changed:
        await sync_host_highlights(cog, guild, marathon)


async def hosts_of(bot: Any, guild: Any, marathon: Any) -> dict[int, str]:
    """Every BaF host of the marathon's blocks, by id."""
    return {
        one["user_id"]: one["name"]
        for block in await blocks_of(bot, guild, marathon)
        for one in block.hosts
    }


__all__ = [
    "block_text",
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
