from __future__ import annotations

from datetime import timedelta
from typing import Any

from ... import marathon as mt
from ... import marathon_events as me
from ... import marathon_host_highlights as mhh
from ... import marathon_hosts as mh
from ...actionlog import log_action
from ...events import DESCRIPTION_LIMIT as EVENT_DESCRIPTION_LIMIT
from ...events import LOCATION_LIMIT as EVENT_LOCATION_LIMIT
from ...events import SCHEDULED_OK, WHERE_OTHER, EventFields, Where, clamp, get_event
from ...events import TITLE_LIMIT as EVENT_TITLE_LIMIT
from ...logkinds import VIA_DISCORD, kind_via
from ...marathon_sources import schedule_page
from ...panels import Outcome, refusal
from ...settings_store import (
    MARATHON_ANNOUNCEMENTS_DEFAULT_KEY,
    MARATHON_ANNOUNCEMENTS_OFF_SAID_KEY,
    MARATHON_ANNOUNCEMENTS_ON_SAID_KEY,
    MARATHON_HOST_EVENT_DESCRIPTION_KEY,
    MARATHON_HOST_EVENT_TITLE_KEY,
    MARATHON_RUN_EVENT_CANCEL_ON_LEAVE_KEY,
)
from .marathon import (
    NO_SUCH,
    channel_login,
    cog_of,
    get_marathon,
    runs_of,
    said_default,
    update_marathon,
)

NOT_HOST = "not_host"
SWITCHED_OFF = "switched_off"
HOST_GONE = "marathon_removed"
SAID = {
    (mh.ANNOUNCE, True): MARATHON_ANNOUNCEMENTS_ON_SAID_KEY,
    (mh.ANNOUNCE, False): MARATHON_ANNOUNCEMENTS_OFF_SAID_KEY,
}
DEFAULTS = {mh.ANNOUNCE: MARATHON_ANNOUNCEMENTS_DEFAULT_KEY}


def words(bot: Any, guild_id: int, key: str, **fields: Any) -> str:
    return mt.render(bot.store.get(guild_id, key), said_default(key), **fields).text


def host_events_on(marathon: Any) -> bool:
    """Host blocks get events exactly when the marathon's BaF run/host events are on."""
    return bool(mt._cell(marathon, "active")) and me.makes_run_events(me.mode_of(marathon))


def switch_state(bot: Any, guild_id: int, marathon: Any, which: str) -> dict[str, Any]:
    default = bool(bot.store.get(guild_id, DEFAULTS[which]))
    own = mh.stored(marathon, which)
    return {"own": own, "on": default if own is None else own, "default": default}


async def set_switch(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon: Any,
    which: str,
    given: Any,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """BaF announcements for one marathon: on, off, or None to follow the setting."""
    from .marathon_thread_controls import controls_changed

    understood, wanted = mh.clean_switch(given)
    if not understood:
        return refusal(mh.BAD_SWITCH.format(what=mh.WHAT[which]), mh.BAD_SWITCH_CODE, 422)
    async with cog_of(bot).lock(marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return refusal(mt.NO_SUCH_MARATHON.format(given=marathon["id"]), NO_SUCH, 404)
        was = switch_state(bot, guild.id, fresh, which)
        await update_marathon(
            bot.db, fresh["id"], **{which: None if wanted is None else int(wanted)}
        )
        fresh = await get_marathon(bot.db, guild.id, fresh["id"])
        now = switch_state(bot, guild.id, fresh, which)
    details = {
        "marathon_id": fresh["id"],
        "name": fresh["name"],
        "from": was["own"],
        "to": now["own"],
        "on": now["on"],
        "via": via,
    }
    await log_action(
        bot, guild, kind_via("marathon.announcements_set", via), actor=actor, details=details
    )
    await controls_changed(bot, guild, fresh["id"])
    return Outcome(
        True,
        words(bot, guild.id, SAID[(which, now["on"])], marathon=fresh["name"]),
        value=await get_marathon(bot.db, guild.id, fresh["id"]),
    )


def host_names(guild: Any, block: mhh.Block) -> str:
    names = []
    for one in block.hosts:
        member = guild.get_member(int(one["user_id"])) if hasattr(guild, "get_member") else None
        names.append(str(getattr(member, "display_name", "") or "") or str(one["name"]))
    return ", ".join(names)


async def host_fields(bot: Any, guild: Any, marathon: Any, block: mhh.Block) -> Any:
    starts, ends = mh.span_of(block)
    if starts is None:
        return None
    finishes = ends if ends is not None and ends > starts else starts
    login = await channel_login(bot, marathon)
    own = next((one.get("login") for one in block.hosts if one.get("login")), None)
    if login or own:
        place = mt.TWITCH_URL.format(login=login or own)
    else:
        place = (
            schedule_page(marathon["source"], marathon["source_ref"]) or marathon["schedule_url"]
        )
    fields = mh.event_fields(block, marathon, host_names(guild, block))
    title = words(bot, guild.id, MARATHON_HOST_EVENT_TITLE_KEY, **fields)
    description = words(bot, guild.id, MARATHON_HOST_EVENT_DESCRIPTION_KEY, **fields)
    return EventFields(
        clamp(title, EVENT_TITLE_LIMIT),
        clamp(description, EVENT_DESCRIPTION_LIMIT),
        Where(WHERE_OTHER, None, clamp(place, EVENT_LOCATION_LIMIT)),
        starts,
        max(1, int((finishes - starts).total_seconds() // 60)),
    )


def details_of(marathon: Any, record: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "marathon_id": marathon["id"],
        "members": list(record["hosts"]),
        "runs": list(record["runs"]),
    } | extra


async def _redate(
    bot: Any, guild: Any, marathon: Any, record: dict[str, Any], block: mhh.Block, event: Any
) -> int:
    from .marathon_events import redated

    fields = await host_fields(bot, guild, marathon, block)
    if fields is None:
        return 0
    finishes = fields.starts + timedelta(minutes=int(fields.minutes))
    moved = await redated(bot, guild, event, fields.starts, finishes)
    if moved is None:
        return 0
    extra = {"event_id": record["event_id"], "scheduled": moved}
    await log_action(
        bot, guild, "marathon.host_event_redated", details=details_of(marathon, record, **extra)
    )
    if moved not in SCHEDULED_OK:
        await log_action(
            bot,
            guild,
            "marathon.scheduled_move_failed",
            details=details_of(marathon, record, **extra),
        )
    return 1


async def _make(
    bot: Any, guild: Any, marathon: Any, block: mhh.Block, actor: Any, via: str
) -> dict[str, Any] | None:
    from .marathon_events import event_from

    fields = await host_fields(bot, guild, marathon, block)
    if fields is None:
        return None
    record = {
        "event_id": 0,
        "start_run_id": block.start_run_id,
        "runs": block.run_ids,
        "hosts": block.user_ids,
    }
    made, why, reviewed = await event_from(bot, guild, marathon, fields, actor=actor, via=via)
    if made is None:
        await log_action(
            bot,
            guild,
            kind_via("marathon.host_event_failed", via),
            actor=actor,
            details=details_of(marathon, record, reason=why[:300], via=via),
        )
        return record
    record["event_id"] = int(made["id"])
    await log_action(
        bot,
        guild,
        kind_via("marathon.host_event_made", via),
        actor=actor,
        target=block.user_ids[0],
        details=details_of(
            marathon,
            record,
            event_id=int(made["id"]),
            status=made["status"],
            reviewed=reviewed,
            via=via,
        ),
    )
    return record


async def sync_host_events(
    bot: Any, guild: Any, marathon: Any, *, actor: Any = None, via: str = VIA_DISCORD
) -> dict[str, int]:
    """Under the marathon's lock: one event per BaF host BLOCK while its BaF run/host events are
    on, kept to the block's span; called off when the block is gone or the switch goes off."""
    fresh = await get_marathon(bot.db, guild.id, marathon["id"])
    if fresh is None:
        return {}
    counts = {"made": 0, "redated": 0, "cancelled": 0, "failed": 0}
    wanted = host_events_on(fresh)
    found = mh.event_records(fresh)
    before = mh.dump_records(found)
    blocks = mhh.blocks(await runs_of(bot.db, fresh["id"]))
    now = cog_of(bot).clock()
    cancelling = bool(bot.store.get(guild.id, MARATHON_RUN_EVENT_CANCEL_ON_LEAVE_KEY))
    events = {}
    for record in found:
        event = await get_event(bot.db, record["event_id"])
        if event is not None:
            events[id(record)] = event
    found = [one for one in found if id(one) in events]
    used: set[int] = set()
    owner: dict[int, mhh.Block] = {}
    for block in blocks:
        record = mh.claim(found, block, used)
        if record is not None:
            owner[id(record)] = block
    kept: list[dict[str, Any]] = []
    for record in found:
        block = owner.get(id(record))
        event = events[id(record)]
        if block is not None and wanted:
            mh.fit(record, block)
            kept.append(record)
            counts["redated"] += await _redate(bot, guild, fresh, record, block, event)
            continue
        reason = NOT_HOST if block is None else SWITCHED_OFF
        if reason == SWITCHED_OFF and not cancelling:
            continue
        counts["cancelled"] += await _cancelled(bot, guild, fresh, record, reason, actor, via)
    if wanted:
        claimed = {id(block) for block in owner.values()}
        for block in blocks:
            _starts, ends = mh.span_of(block)
            if id(block) in claimed or ends is None or ends <= now:
                continue
            record = await _make(bot, guild, fresh, block, actor, via)
            if record is None:
                continue
            if not record["event_id"]:
                counts["failed"] += 1
                continue
            kept.append(record)
            counts["made"] += 1
    if mh.dump_records(kept) != before:
        await update_marathon(bot.db, fresh["id"], host_event_ids=mh.dump_records(kept))
    return counts


async def _cancelled(
    bot: Any,
    guild: Any,
    marathon: Any,
    record: dict[str, Any],
    reason: str,
    actor: Any,
    via: str,
) -> int:
    from .marathon_events import call_off

    event_id = record["event_id"]
    cancelled, trouble = await call_off(bot, guild, event_id, reason, actor=actor, via=via)
    target = record["hosts"][0] if record["hosts"] else None
    if not cancelled:
        if trouble:
            await log_action(
                bot,
                guild,
                "marathon.host_event_failed",
                details=details_of(
                    marathon, record, event_id=event_id, reason=trouble, calling_off=reason
                ),
            )
        return 0
    await log_action(
        bot,
        guild,
        kind_via("marathon.host_event_cancelled", via),
        actor=actor,
        target=target,
        details=details_of(marathon, record, event_id=event_id, reason=reason, via=via),
    )
    return 1


async def cancel_every_host_event(
    bot: Any, guild: Any, marathon: Any, *, actor: Any = None, via: str = VIA_DISCORD
) -> int:
    fresh = await get_marathon(bot.db, guild.id, marathon["id"]) or marathon
    found = mh.event_records(fresh)
    cancelled = 0
    for record in found:
        cancelled += await _cancelled(bot, guild, fresh, record, HOST_GONE, actor, via)
    if found:
        await update_marathon(bot.db, fresh["id"], host_event_ids=mh.dump_records([]))
    return cancelled


__all__ = [
    "cancel_every_host_event",
    "host_events_on",
    "set_switch",
    "switch_state",
    "sync_host_events",
]
