from __future__ import annotations

from datetime import timedelta
from typing import Any

from ... import marathon as mt
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
    MARATHON_HOST_EVENTS_DEFAULT_KEY,
    MARATHON_HOST_EVENTS_OFF_SAID_KEY,
    MARATHON_HOST_EVENTS_ON_SAID_KEY,
    MARATHON_RUN_EVENT_CANCEL_ON_LEAVE_KEY,
    MARATHON_SCAN_HOSTS_DEFAULT_KEY,
    MARATHON_SCAN_HOSTS_OFF_SAID_KEY,
    MARATHON_SCAN_HOSTS_ON_SAID_KEY,
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
    (mh.SCAN, True): MARATHON_SCAN_HOSTS_ON_SAID_KEY,
    (mh.SCAN, False): MARATHON_SCAN_HOSTS_OFF_SAID_KEY,
    (mh.EVENTS, True): MARATHON_HOST_EVENTS_ON_SAID_KEY,
    (mh.EVENTS, False): MARATHON_HOST_EVENTS_OFF_SAID_KEY,
    (mh.ANNOUNCE, True): MARATHON_ANNOUNCEMENTS_ON_SAID_KEY,
    (mh.ANNOUNCE, False): MARATHON_ANNOUNCEMENTS_OFF_SAID_KEY,
}
DEFAULTS = {
    mh.SCAN: MARATHON_SCAN_HOSTS_DEFAULT_KEY,
    mh.EVENTS: MARATHON_HOST_EVENTS_DEFAULT_KEY,
    mh.ANNOUNCE: MARATHON_ANNOUNCEMENTS_DEFAULT_KEY,
}



def words(bot: Any, guild_id: int, key: str, **fields: Any) -> str:
    return mt.render(bot.store.get(guild_id, key), said_default(key), **fields).text


def scans(bot: Any, guild_id: int, marathon: Any) -> bool:
    return mh.scans_hosts(marathon, bot.store.get(guild_id, MARATHON_SCAN_HOSTS_DEFAULT_KEY))


def host_events_on(bot: Any, guild_id: int, marathon: Any) -> bool:
    return mh.makes_host_events(marathon, bot.store.get(guild_id, MARATHON_HOST_EVENTS_DEFAULT_KEY))


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
    """Scan hosts, BaF host events or Runner/Host announcements for one marathon: on, off, or
    None to follow the setting."""
    from .marathon import rematched
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
        if which == mh.SCAN:
            await rematched(bot, guild, fresh, actor)
        elif which == mh.EVENTS:
            await sync_host_events(bot, guild, fresh, actor=actor, via=via)
    details = {
        "marathon_id": fresh["id"],
        "name": fresh["name"],
        "from": was["own"],
        "to": now["own"],
        "on": now["on"],
        "via": via,
    }
    await log_action(
        bot,
        guild,
        kind_via(
            "marathon.scan_hosts_set"
            if which == mh.SCAN
            else "marathon.host_events_set"
            if which == mh.EVENTS
            else "marathon.announcements_set",
            via,
        ),
        actor=actor,
        details=details,
    )
    await controls_changed(bot, guild, fresh["id"])
    return Outcome(
        True,
        words(bot, guild.id, SAID[(which, now["on"])], marathon=fresh["name"]),
        value=await get_marathon(bot.db, guild.id, fresh["id"]),
    )


def host_names(guild: Any, span: mh.HostSpan) -> str:
    member = guild.get_member(span.user_id) if hasattr(guild, "get_member") else None
    return str(getattr(member, "display_name", "") or "") or span.name


async def host_fields(bot: Any, guild: Any, marathon: Any, span: mh.HostSpan) -> Any:
    if span.starts is None:
        return None
    finishes = span.ends if span.ends is not None and span.ends > span.starts else span.starts
    login = await channel_login(bot, marathon)
    own = next(
        (
            one.get("login")
            for row in span.runs
            for one in mt.people_of(row)
            if one.get("user_id") == span.user_id and one.get("login")
        ),
        None,
    )
    if login or own:
        place = mt.TWITCH_URL.format(login=login or own)
    else:
        place = (
            schedule_page(marathon["source"], marathon["source_ref"]) or marathon["schedule_url"]
        )
    fields = mh.event_fields(span, marathon, host_names(guild, span))
    title = words(bot, guild.id, MARATHON_HOST_EVENT_TITLE_KEY, **fields)
    description = words(bot, guild.id, MARATHON_HOST_EVENT_DESCRIPTION_KEY, **fields)
    return EventFields(
        clamp(title, EVENT_TITLE_LIMIT),
        clamp(description, EVENT_DESCRIPTION_LIMIT),
        Where(WHERE_OTHER, None, clamp(place, EVENT_LOCATION_LIMIT)),
        span.starts,
        max(1, int((finishes - span.starts).total_seconds() // 60)),
    )


def details_of(marathon: Any, user_id: int, **extra: Any) -> dict[str, Any]:
    return {"marathon_id": marathon["id"], "member_id": int(user_id)} | extra


async def sync_host_events(
    bot: Any, guild: Any, marathon: Any, *, actor: Any = None, via: str = VIA_DISCORD
) -> dict[str, int]:
    """Under the marathon's lock: one event per BaF host while the switch is on and the marathon
    scans its hosts, kept to their hosted runs' span; called off when they stop being a host."""
    from .marathon_events import event_from, redated

    fresh = await get_marathon(bot.db, guild.id, marathon["id"])
    if fresh is None:
        return {}
    counts = {"made": 0, "redated": 0, "cancelled": 0, "failed": 0}
    wanted = (
        bool(fresh["active"])
        and host_events_on(bot, guild.id, fresh)
        and scans(bot, guild.id, fresh)
    )
    ids = mh.event_ids(fresh)
    spans = {one.user_id: one for one in mh.hosted(await runs_of(bot.db, fresh["id"]))}
    now = cog_of(bot).clock()
    changed = False
    cancelling = bool(bot.store.get(guild.id, MARATHON_RUN_EVENT_CANCEL_ON_LEAVE_KEY))
    for user_id, event_id in list(ids.items()):
        event = await get_event(bot.db, event_id)
        span = spans.get(user_id)
        if event is None:
            ids.pop(user_id)
            changed = True
            continue
        if span is not None and wanted:
            fields = await host_fields(bot, guild, fresh, span)
            if fields is None:
                continue
            finishes = fields.starts + timedelta(minutes=int(fields.minutes))
            moved = await redated(bot, guild, event, fields.starts, finishes)
            if moved is not None:
                counts["redated"] += 1
                await log_action(
                    bot,
                    guild,
                    "marathon.host_event_redated",
                    details=details_of(fresh, user_id, event_id=event_id, scheduled=moved),
                )
                if moved not in SCHEDULED_OK:
                    await log_action(
                        bot,
                        guild,
                        "marathon.scheduled_move_failed",
                        details=details_of(fresh, user_id, event_id=event_id, scheduled=moved),
                    )
            continue
        ids.pop(user_id)
        changed = True
        reason = NOT_HOST if span is None else SWITCHED_OFF
        if reason == SWITCHED_OFF and not cancelling:
            continue
        counts["cancelled"] += await _cancelled(
            bot, guild, fresh, user_id, event_id, reason, actor, via
        )
    if wanted:
        for user_id, span in spans.items():
            if user_id in ids or span.ends is None or span.ends <= now:
                continue
            fields = await host_fields(bot, guild, fresh, span)
            if fields is None:
                continue
            made, why, reviewed = await event_from(bot, guild, fresh, fields, actor=actor, via=via)
            if made is None:
                counts["failed"] += 1
                await log_action(
                    bot,
                    guild,
                    kind_via("marathon.host_event_failed", via),
                    actor=actor,
                    details=details_of(fresh, user_id, reason=why[:300], via=via),
                )
                continue
            ids[user_id] = int(made["id"])
            changed = True
            counts["made"] += 1
            await log_action(
                bot,
                guild,
                kind_via("marathon.host_event_made", via),
                actor=actor,
                target=user_id,
                details=details_of(
                    fresh,
                    user_id,
                    event_id=int(made["id"]),
                    status=made["status"],
                    reviewed=reviewed,
                    runs=[int(row["id"]) for row in span.runs],
                    via=via,
                ),
            )
    if changed:
        await update_marathon(bot.db, fresh["id"], host_event_ids=mh.dump_ids(ids))
    return counts


async def _cancelled(
    bot: Any,
    guild: Any,
    marathon: Any,
    user_id: int,
    event_id: int,
    reason: str,
    actor: Any,
    via: str,
) -> int:
    from .marathon_events import call_off

    cancelled, trouble = await call_off(bot, guild, event_id, reason, actor=actor, via=via)
    if not cancelled:
        if trouble:
            await log_action(
                bot,
                guild,
                "marathon.host_event_failed",
                details=details_of(
                    marathon, user_id, event_id=event_id, reason=trouble, calling_off=reason
                ),
            )
        return 0
    await log_action(
        bot,
        guild,
        kind_via("marathon.host_event_cancelled", via),
        actor=actor,
        target=user_id,
        details=details_of(marathon, user_id, event_id=event_id, reason=reason, via=via),
    )
    return 1


async def cancel_every_host_event(
    bot: Any, guild: Any, marathon: Any, *, actor: Any = None, via: str = VIA_DISCORD
) -> int:
    fresh = await get_marathon(bot.db, guild.id, marathon["id"]) or marathon
    ids = mh.event_ids(fresh)
    cancelled = 0
    for user_id, event_id in ids.items():
        cancelled += await _cancelled(bot, guild, fresh, user_id, event_id, HOST_GONE, actor, via)
    if ids:
        await update_marathon(bot.db, fresh["id"], host_event_ids=mh.dump_ids({}))
    return cancelled


__all__ = [
    "cancel_every_host_event",
    "host_events_on",
    "scans",
    "set_switch",
    "switch_state",
    "sync_host_events",
]
