from __future__ import annotations

import logging
from typing import Any

from ... import marathon as mt
from ... import marathon_events as me
from ...actionlog import log_action
from ...events import CANCELLED as EVENT_CANCELLED
from ...events import DESCRIPTION_LIMIT as EVENT_DESCRIPTION_LIMIT
from ...events import LOCATION_LIMIT as EVENT_LOCATION_LIMIT
from ...events import (
    SCHEDULED_OK,
    WHERE_OTHER,
    EventFields,
    Where,
    approved_from,
    cancel_for,
    clamp,
    get_event,
    move_scheduled_event,
    read_where,
    update_event,
)
from ...events import TITLE_LIMIT as EVENT_TITLE_LIMIT
from ...golive import parse_ts
from ...logkinds import VIA_DISCORD, kind_via
from ...marathon_sources import schedule_page
from ...panels import Outcome, refusal
from ...settings_store import (
    MARATHON_EVENT_MODE_DEFAULT_KEY,
    MARATHON_RUN_EVENT_CANCEL_ON_LEAVE_KEY,
    MARATHON_RUN_EVENT_DESCRIPTION_KEY,
    MARATHON_RUN_EVENT_TITLE_KEY,
    MARATHON_RUN_EVENTS_REVIEWED_KEY,
)
from .marathon import (
    EVENT_KEPT_IN_STEP,
    MODE_ON,
    NO_SUCH,
    NO_SUCH_RUN_CODE,
    cancel_linked_event,
    channel_login,
    cog_of,
    get_marathon,
    make_event_for,
    mode_of,
    requester_for,
    run_by_id,
    runs_of,
    said_default,
    update_marathon,
    update_run,
)

log = logging.getLogger(__name__)

BAD_MODE_CODE = "bad_mode"
RUN_EVENT_EXISTS_CODE = "run_event_exists"
NOT_OURS_CODE = "not_ours"
NO_TIME_CODE = "no_time"
RUN_EVENT_REFUSED_CODE = "run_event_refused"
NO_RUN_EVENT_CODE = "no_run_event"
UNLINKED = 0


def default_mode(bot: Any, guild_id: int) -> str:
    return me.clean_mode(bot.store.get(guild_id, MARATHON_EVENT_MODE_DEFAULT_KEY)) or me.NONE


def mode_for_new(
    bot: Any, guild_id: int, *, event_mode: Any, make_event: Any, feed: Any
) -> str | None:
    """The mode given, else the old make_event yes / no (one release), else the feed's own,
    else the setting's. None is the refusal: a word that is not a mode."""
    if event_mode not in (None, ""):
        return me.clean_mode(event_mode)
    if make_event is not None:
        return me.MARATHON if make_event else me.NONE
    return me.clean_mode(mt._cell(feed, "event_mode")) or default_mode(bot, guild_id)


def run_words(bot: Any, guild: Any, row: Any, marathon: Any) -> me.RunEventWords:
    names: dict[int, str] = {}
    for user_id in mt.member_ids(row):
        member = guild.get_member(int(user_id)) if hasattr(guild, "get_member") else None
        if member is not None:
            names[int(user_id)] = str(getattr(member, "display_name", "") or "")
    fields = me.run_event_fields(row, marathon, {key: one for key, one in names.items() if one})
    store = bot.store
    title = mt.render(
        store.get(guild.id, MARATHON_RUN_EVENT_TITLE_KEY),
        said_default(MARATHON_RUN_EVENT_TITLE_KEY),
        **fields,
    ).text
    description = mt.render(
        store.get(guild.id, MARATHON_RUN_EVENT_DESCRIPTION_KEY),
        said_default(MARATHON_RUN_EVENT_DESCRIPTION_KEY),
        **fields,
    ).text
    return me.RunEventWords(
        clamp(title, EVENT_TITLE_LIMIT), clamp(description, EVENT_DESCRIPTION_LIMIT)
    )


async def run_fields(bot: Any, guild: Any, marathon: Any, row: Any) -> EventFields | None:
    starts, finishes = parse_ts(row["scheduled_at"]), parse_ts(row["ends_at"])
    if starts is None:
        return None
    if finishes is None or finishes <= starts:
        finishes = starts
    login = await channel_login(bot, marathon)
    runners = me.run_logins(row)
    if login:
        place = mt.TWITCH_URL.format(login=login)
    elif runners:
        place = mt.TWITCH_URL.format(login=runners[0])
    else:
        place = schedule_page(marathon["source"], marathon["source_ref"]) or marathon[
            "schedule_url"
        ]
    words = run_words(bot, guild, row, marathon)
    return EventFields(
        words.title,
        words.description,
        Where(WHERE_OTHER, None, clamp(place, EVENT_LOCATION_LIMIT)),
        starts,
        max(1, int((finishes - starts).total_seconds() // 60)),
    )


def run_details(marathon: Any, row: Any, **extra: Any) -> dict[str, Any]:
    return {
        "marathon_id": marathon["id"],
        "run_id": row["id"],
        "game": row["game"],
        "members": mt.member_ids(row),
    } | extra


def reviews_runs(bot: Any, guild_id: int) -> bool:
    """Reviewed when staff say so — and always while marathon posts only rehearse, so nothing
    reaches the calendar or the announce channel before a staff press."""
    return bool(bot.store.get(guild_id, MARATHON_RUN_EVENTS_REVIEWED_KEY)) or (
        mode_of(bot, guild_id) != MODE_ON
    )


async def make_run_event(
    bot: Any, guild: Any, marathon: Any, row: Any, *, actor: Any = None, via: str = VIA_DISCORD
) -> Outcome:
    """Called under the marathon's lock with a run of ours that has no event."""
    fields = await run_fields(bot, guild, marathon, row)
    if fields is None:
        return refusal(me.RUN_EVENT_NO_TIME.format(game=row["game"]), NO_TIME_CODE, 409)
    requester = requester_for(guild, marathon, actor)
    reviewed = reviews_runs(bot, guild.id)
    made = None
    why = mt.EVENT_NOBODY
    if requester is not None:
        try:
            if reviewed:
                from ..community.events import propose_from

                why, made = await propose_from(bot, guild, requester, fields, via=via)
            else:
                made = await approved_from(
                    bot, guild, requester, fields, because="marathon_run", via=via
                )
        except Exception as exc:
            why = f"{type(exc).__name__}: {exc}"
            log.warning("marathon: the event for run %s was not made — %s", row["id"], why)
    if made is None:
        await log_action(
            bot,
            guild,
            kind_via("marathon.run_event_failed", via),
            actor=actor,
            details=run_details(marathon, row, reason=str(why)[:300], via=via),
        )
        return refusal(
            me.RUN_EVENT_NOT_MADE.format(game=row["game"], why=why), RUN_EVENT_REFUSED_CODE, 409
        )
    await update_run(bot.db, row["id"], event_id=int(made["id"]))
    await log_action(
        bot,
        guild,
        kind_via("marathon.run_event_made", via),
        actor=actor,
        details=run_details(
            marathon,
            row,
            event_id=int(made["id"]),
            status=made["status"],
            reviewed=reviewed,
            via=via,
        ),
    )
    return Outcome(
        True,
        me.RUN_EVENT_MADE.format(game=row["game"], event_id=int(made["id"])),
        value=int(made["id"]),
    )


async def cancel_run_event(
    bot: Any,
    guild: Any,
    marathon: Any,
    row: Any,
    reason: str,
    *,
    actor: Any = None,
    via: str = VIA_DISCORD,
) -> bool:
    """The pointer goes whatever happens; the event is called off when it is still open."""
    event_id = int(row["event_id"])
    event = await get_event(bot.db, event_id)
    await update_run(bot.db, row["id"], event_id=None)
    if event is None or event["status"] not in EVENT_KEPT_IN_STEP:
        return False
    trouble = None
    try:
        await cancel_for(
            bot, guild, event, actor if actor is not None else 0, reason=reason, via=via
        )
    except Exception as exc:
        trouble = f"{type(exc).__name__}: {exc}"[:300]
        log.warning("marathon: calling off event #%s did not finish — %s", event_id, trouble)
    after = await get_event(bot.db, event_id)
    if after is None or after["status"] != EVENT_CANCELLED:
        await log_action(
            bot,
            guild,
            "marathon.run_event_failed",
            details=run_details(
                marathon, row, event_id=event_id, reason=trouble, calling_off=reason
            ),
        )
        return False
    await log_action(
        bot,
        guild,
        kind_via("marathon.run_event_cancelled", via),
        actor=actor,
        details=run_details(marathon, row, event_id=event_id, reason=reason, via=via),
    )
    return True


async def redate_run_event(bot: Any, guild: Any, marathon: Any, row: Any, event: Any) -> None:
    starts, finishes = parse_ts(row["scheduled_at"]), parse_ts(row["ends_at"])
    if starts is None or event["status"] not in EVENT_KEPT_IN_STEP:
        return
    if finishes is None or finishes <= starts:
        finishes = starts
    if (parse_ts(event["starts_at"]), parse_ts(event["ends_at"])) == (starts, finishes):
        return
    await update_event(
        bot.db,
        int(event["id"]),
        title=event["title"],
        description=event["description"],
        where=read_where(event),
        starts_at=starts,
        finishes_at=finishes,
    )
    moved = await move_scheduled_event(bot, guild, await get_event(bot.db, int(event["id"])))
    details = run_details(
        marathon,
        row,
        event_id=int(event["id"]),
        **{
            "from": {"starts_at": event["starts_at"], "ends_at": event["ends_at"]},
            "to": {"starts_at": starts.isoformat(), "ends_at": finishes.isoformat()},
            "scheduled": moved,
        },
    )
    await log_action(bot, guild, "marathon.run_event_redated", details=details)
    if moved not in SCHEDULED_OK:
        await log_action(bot, guild, "marathon.scheduled_move_failed", details=details)


def makeable(row: Any, now: Any) -> bool:
    finishes = parse_ts(row["ends_at"]) or parse_ts(row["scheduled_at"])
    return (
        row["event_id"] is None
        and mt.is_ours(row)
        and row["state"] in (mt.UPCOMING, mt.LIVE)
        and parse_ts(row["scheduled_at"]) is not None
        and finishes is not None
        and finishes > now
    )


async def sync_run_events(
    bot: Any, guild: Any, marathon: Any, *, actor: Any = None, via: str = VIA_DISCORD
) -> dict[str, int]:
    """Under the marathon's lock: every linked run is kept in step (re-dated, or called off when
    it is dropped or nobody of ours is left); in runs / both, every run of ours without one gets
    one. A run staff unlinked (event_id 0) is never made again on its own."""
    fresh = await get_marathon(bot.db, guild.id, marathon["id"])
    if fresh is None:
        return {}
    counts = {"made": 0, "redated": 0, "cancelled": 0, "failed": 0}
    wanted = me.makes_run_events(me.mode_of(fresh)) and bool(fresh["active"])
    now = cog_of(bot).clock()
    for row in await runs_of(bot.db, fresh["id"]):
        if row["event_id"]:
            event = await get_event(bot.db, int(row["event_id"]))
            if event is None:
                await update_run(bot.db, row["id"], event_id=None)
                continue
            if row["state"] == mt.DROPPED:
                counts["cancelled"] += await cancel_run_event(
                    bot, guild, fresh, row, me.RUN_DROPPED, actor=actor, via=via
                )
            elif not mt.is_ours(row):
                counts["cancelled"] += await cancel_run_event(
                    bot, guild, fresh, row, me.NOT_OURS, actor=actor, via=via
                )
            else:
                await redate_run_event(bot, guild, fresh, row, event)
            continue
        if wanted and makeable(row, now):
            made = await make_run_event(bot, guild, fresh, row, actor=actor, via=via)
            counts["made" if made.ok else "failed"] += 1
    return counts


async def leave_run_events(
    bot: Any, guild: Any, marathon: Any, *, actor: Any = None, via: str = VIA_DISCORD
) -> dict[str, int]:
    """Out of runs / both: every linked run lets go of its event, called off when the key says."""
    cancelling = bool(bot.store.get(guild.id, MARATHON_RUN_EVENT_CANCEL_ON_LEAVE_KEY))
    counts = {"cancelled": 0, "kept": 0}
    for row in await runs_of(bot.db, marathon["id"]):
        if not row["event_id"]:
            continue
        if cancelling:
            counts["cancelled"] += await cancel_run_event(
                bot, guild, marathon, row, me.MODE_CHANGED, actor=actor, via=via
            )
        else:
            await update_run(bot.db, row["id"], event_id=None)
            counts["kept"] += 1
    return counts


async def cancel_every_run_event(
    bot: Any, guild: Any, marathon: Any, *, actor: Any = None, via: str = VIA_DISCORD
) -> int:
    cancelled = 0
    for row in await runs_of(bot.db, marathon["id"]):
        if row["event_id"]:
            cancelled += await cancel_run_event(
                bot, guild, marathon, row, me.MARATHON_REMOVED, actor=actor, via=via
            )
    return cancelled


async def set_event_mode(
    bot: Any, guild: Any, actor: Any, marathon: Any, mode: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Applies at once: makes what the new mode asks for, lets go of what it no longer does."""
    wanted = me.clean_mode(mode)
    if wanted is None:
        return refusal(me.BAD_MODE.format(given=str(mode or "")[:40]), BAD_MODE_CODE, 422)
    async with cog_of(bot).lock(marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return refusal(mt.NO_SUCH_MARATHON.format(given=marathon["id"]), NO_SUCH, 404)
        was = me.mode_of(fresh)
        if was == wanted:
            return Outcome(
                True,
                me.MODE_SAME.format(name=fresh["name"], words=me.mode_words(wanted)),
                value=fresh,
            )
        await update_marathon(bot.db, fresh["id"], event_mode=wanted)
        said = [me.MODE_SET.format(name=fresh["name"], words=me.mode_words(wanted))]
        details: dict[str, Any] = {}
        fresh = await get_marathon(bot.db, guild.id, fresh["id"])
        if me.makes_marathon_event(wanted) and not fresh["event_id"]:
            made = await make_event_for(bot, guild, actor, fresh)
            said.append(made.message)
        elif not me.makes_marathon_event(wanted) and fresh["event_id"]:
            if bot.store.get(guild.id, MARATHON_RUN_EVENT_CANCEL_ON_LEAVE_KEY):
                await cancel_linked_event(bot, guild, actor, fresh, reason=me.MODE_CHANGED)
            details["marathon_event"] = int(fresh["event_id"])
            await update_marathon(bot.db, fresh["id"], event_id=None)
        fresh = await get_marathon(bot.db, guild.id, fresh["id"])
        if me.makes_run_events(wanted):
            counts = await sync_run_events(bot, guild, fresh, actor=actor)
            details |= counts
            if counts.get("made"):
                said.append(me.RUN_EVENTS_MADE.format(count=counts["made"]))
        elif me.makes_run_events(was):
            counts = await leave_run_events(bot, guild, fresh, actor=actor)
            details |= counts
            if counts["cancelled"]:
                said.append(me.RUN_EVENTS_CANCELLED.format(count=counts["cancelled"]))
            if counts["kept"]:
                said.append(me.RUN_EVENTS_KEPT.format(count=counts["kept"]))
    await log_action(
        bot,
        guild,
        kind_via("marathon.event_mode_set", via),
        actor=actor,
        details={"marathon_id": fresh["id"], "from": was, "to": wanted, "via": via} | details,
    )
    return Outcome(True, " ".join(said), value=await get_marathon(bot.db, guild.id, fresh["id"]))


async def make_run_event_now(
    bot: Any, guild: Any, actor: Any, marathon: Any, run: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """The staff door for one run, whatever the mode: under the lock, never a second one."""
    async with cog_of(bot).lock(marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        row = await run_by_id(bot.db, marathon["id"], run["id"]) if fresh is not None else None
        if row is None:
            return refusal(mt.NO_SUCH_RUN.format(name=marathon["name"]), NO_SUCH_RUN_CODE, 404)
        if row["event_id"]:
            return refusal(
                me.RUN_EVENT_ALREADY.format(game=row["game"], event_id=int(row["event_id"])),
                RUN_EVENT_EXISTS_CODE,
                409,
            )
        if not mt.is_ours(row) or row["state"] == mt.DROPPED:
            return refusal(me.RUN_EVENT_NOT_OURS.format(game=row["game"]), NOT_OURS_CODE, 409)
        return await make_run_event(bot, guild, fresh, row, actor=actor, via=via)


async def unlink_run_event(
    bot: Any, guild: Any, actor: Any, marathon: Any, run: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Staff final say: the run lets go of its event and is never given one again on its own
    (event_id 0); the event itself is not touched."""
    async with cog_of(bot).lock(marathon["id"]):
        row = await run_by_id(bot.db, marathon["id"], run["id"])
        if row is None:
            return refusal(mt.NO_SUCH_RUN.format(name=marathon["name"]), NO_SUCH_RUN_CODE, 404)
        event_id = row["event_id"]
        if not event_id:
            return refusal(me.RUN_EVENT_NONE.format(game=row["game"]), NO_RUN_EVENT_CODE, 409)
        await update_run(bot.db, row["id"], event_id=UNLINKED)
    await log_action(
        bot,
        guild,
        kind_via("marathon.run_event_unlinked", via),
        actor=actor,
        details=run_details(marathon, row, event_id=int(event_id), via=via),
    )
    return Outcome(True, me.RUN_EVENT_UNLINKED.format(game=row["game"], event_id=int(event_id)))


async def run_of_event(db: Any, guild_id: int, event_id: Any) -> Any:
    try:
        wanted = int(event_id)
    except (TypeError, ValueError):
        return None
    if not wanted:
        return None
    cur = await db.conn.execute(
        "SELECT marathon_runs.*, marathons.name AS marathon_name FROM marathon_runs "
        "JOIN marathons ON marathons.id = marathon_runs.marathon_id "
        "WHERE marathons.guild_id = ? AND marathon_runs.event_id = ? LIMIT 1",
        (int(guild_id), wanted),
    )
    return await cur.fetchone()


__all__ = [
    "cancel_every_run_event",
    "default_mode",
    "leave_run_events",
    "make_run_event",
    "make_run_event_now",
    "mode_for_new",
    "run_of_event",
    "set_event_mode",
    "sync_run_events",
    "unlink_run_event",
]
