from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

import discord
from discord.ext import commands, tasks

from ... import marathon as mt
from ... import marathon_events as me
from ... import pings
from ... import shadow as shadow_home
from ... import spotlight as spot
from ...actionlog import log_action, send_logs
from ...command_errors import AnswersErrors, SafeDynamicItem
from ...events import APPROVED as EVENT_APPROVED
from ...events import CANCELLED as EVENT_CANCELLED
from ...events import DESCRIPTION_LIMIT as EVENT_DESCRIPTION_LIMIT
from ...events import LOCATION_LIMIT as EVENT_LOCATION_LIMIT
from ...events import PANEL_MINUTES_KEY as EVENT_PANEL_MINUTES_KEY
from ...events import PENDING as EVENT_PENDING
from ...events import (
    SCHEDULED_OK,
    WHERE_OTHER,
    EventFields,
    Where,
    cancel_for,
    clamp,
    get_event,
    move_scheduled_event,
    read_where,
    update_event,
)
from ...events import TITLE_LIMIT as EVENT_TITLE_LIMIT
from ...golive import now_iso, parse_ts, ping_prefix
from ...logkinds import VIA_DISCORD, kind_via
from ...loops import Reconciler, wait_ready
from ...marathon_channels import HELD_REFUSAL, OPTED_OUT_REFUSAL, takes_marathons
from ...marathon_channels import channel_word as channel_word_of
from ...marathon_sources import (
    GDQ,
    SOURCE_WORDS,
    ScheduleClient,
    ScheduleError,
    next_gdq_event,
    read_url,
    schedule_page,
)
from ...panels import (
    KEEP_IT,
    Outcome,
    Panel,
    answer,
    clamped,
    confirm,
    confirm_items,
    opened,
    panel_minutes,
    refusal,
    retire,
    site_page_url,
    still_staff,
)
from ...settings_store import (
    DB_UNAVAILABLE,
    MARATHON_ALREADY_ADDED_KEY,
    MARATHON_BOARD_EMPTY_KEY,
    MARATHON_BOARD_LINE_KEY,
    MARATHON_BOARD_TEMPLATE_KEY,
    MARATHON_CHANNEL_KEY,
    MARATHON_COULD_NOT_READ_KEY,
    MARATHON_DEFAULTS,
    MARATHON_DONE_TEMPLATE_KEY,
    MARATHON_EDIT_DONE_KEY,
    MARATHON_EVENT_DESCRIPTION_KEY,
    MARATHON_FAR_POLL_HOURS_KEY,
    MARATHON_LATE_GRACE_KEY,
    MARATHON_LEAD_DAYS_KEY,
    MARATHON_LIVE_PINGS_KEY,
    MARATHON_LIVE_TEMPLATE_KEY,
    MARATHON_MATCH_HOSTS_KEY,
    MARATHON_MODE_KEY,
    MARATHON_MOVE_MINUTES_KEY,
    MARATHON_NEXT_ADDED_TEMPLATE_KEY,
    MARATHON_NEXT_NONE_TEMPLATE_KEY,
    MARATHON_NEXT_TEMPLATE_KEY,
    MARATHON_NOTICE_HOME_KEY,
    MARATHON_NOTICE_TITLE_KEY,
    MARATHON_PIN_BOARD_KEY,
    MARATHON_PING_MINUTES_KEY,
    MARATHON_POLL_MINUTES_KEY,
    MARATHON_REMINDER_MINUTES_KEY,
    MARATHON_REMINDER_PINGS_KEY,
    MARATHON_REMINDER_STALE_KEY,
    MARATHON_REMINDER_TEMPLATE_KEY,
    MARATHON_SHOUT_WHEN_RUN_HAS_EVENT_KEY,
    MARATHON_SUGGEST_NEXT_KEY,
    MARATHON_TITLE_CONFIRMS_KEY,
    MARATHON_UNKNOWN_SITE_KEY,
    MARATHON_WINDOW_SLACK_KEY,
    MARATHON_WORDS,
)
from ...timezones import unix
from .spotlight import channel_by_id, channel_by_login, open_session, windows_for

log = logging.getLogger(__name__)

COG_NAME = "Marathons"
FEATURE = "marathon"
GOLIVE_CHANNEL_KEY = "golive_channel_id"
STAFF_CHANNEL_KEY = "staff_channel_id"
MODE_ON = "on"
MODE_OFF = "off"
SHADOW_FEATURE = "marathon"
TICK_MINUTES = 1
FAILURES_IMPORTANT = 3
NO_CHANNEL = "no channel is set for marathon posts"
NO_STAFF_CHANNEL = "no staff channel is set (staff_channel_id)"
NOT_VISIBLE = "the marathon channel is not one Black Bloc can see"
TEST_MODE = "test mode keeps Black Bloc out of that channel"
MODE_IS_OFF = "marathon posts are off"
PIN_REASON = "Black Bloc: the marathon board"
UNPIN_REASON = "Black Bloc: the marathon is over"

UNKNOWN_SITE = "unknown_site"
DUPLICATE = "duplicate"
UNREADABLE = "unreadable"
NO_NAME_CODE = "no_name"
NO_SUCH = "no_such_marathon"
NO_SUCH_RUN_CODE = "no_such_run"
NO_SUCH_PAIRING_CODE = "no_such_pairing"
NO_SUCH_CHANNEL_CODE = "no_such_channel"
NOT_SHOUTABLE_CODE = "not_shoutable"
NOT_OURS_CODE = "not_ours"
ALREADY_DONE_CODE = "already_done"
NO_RUNNER_CODE = "no_runner"
NO_MEMBER_CODE = "no_member"
BAD_POLL_CODE = "bad_poll"
NOT_GDQ_CODE = "not_gdq"
NOT_OVER_CODE = "not_over"
NOTHING_SUGGESTED_CODE = "nothing_suggested"
SUGGESTION_MOVED_CODE = "suggestion_moved"
NOT_RESETTABLE_CODE = "not_resettable"
NOT_LIVEABLE_CODE = "not_liveable"
NEXT_TEMPLATE = (
    r"marathon:(?P<marathon_id>[0-9]+):next:(?P<event_id>[0-9]+):(?P<action>add|dismiss)"
)
NEXT_ADD = "add"
NEXT_DISMISS = "dismiss"
RECENT_DONE_HOURS = 12
POST_FAILED = "post_failed"
POLL_RANGE = (10, 120)
EVENT_EXISTS_CODE = "event_exists"
EVENT_REFUSED_CODE = "event_refused"
NO_EVENT_CODE = "no_event"
MARATHON_REMOVED = "marathon_removed"
EVENT_KEPT_IN_STEP = (EVENT_PENDING, EVENT_APPROVED)
EVENT_ANNOUNCED = (EVENT_APPROVED, "live")
NOTICE_EVENTS = "events"
NOTICE_STAFF = "staff"
NOTICE_SHADOW = "shadow"
OPTED_OUT_CODE = "channel_opted_out"
HELD_CODE = "held_by_channel"


def _cell(row: Any, key: str, fallback: Any = None) -> Any:
    if row is None:
        return fallback
    try:
        return row[key]
    except (IndexError, KeyError):
        return fallback


def actor_id(actor: Any) -> int | None:
    found = getattr(actor, "id", actor)
    return int(found) if isinstance(found, int) else None


# --- the tables -------------------------------------------------------------------------------


async def list_marathons(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM marathons WHERE guild_id = ? ORDER BY COALESCE(starts_at, '9999'), id",
        (int(guild_id),),
    )
    return list(await cur.fetchall())


async def get_marathon(db: Any, guild_id: int, marathon_id: Any) -> Any:
    try:
        wanted = int(marathon_id)
    except (TypeError, ValueError):
        return None
    cur = await db.conn.execute(
        "SELECT * FROM marathons WHERE id = ? AND guild_id = ?", (wanted, int(guild_id))
    )
    return await cur.fetchone()


async def marathon_by_ref(db: Any, guild_id: int, source: str, ref: Any) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM marathons WHERE guild_id = ? AND source = ? AND source_ref = ? "
        "ORDER BY id LIMIT 1",
        (int(guild_id), source, str(ref)),
    )
    return await cur.fetchone()


async def save_suggestion(db: Any, marathon_id: int, record: Any) -> None:
    await update_marathon(
        db, marathon_id, suggested_next=json.dumps(record) if record is not None else None
    )


async def marathon_by_url(db: Any, guild_id: int, url: str) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM marathons WHERE guild_id = ? AND schedule_url = ?", (int(guild_id), url)
    )
    return await cur.fetchone()


async def runs_of(db: Any, marathon_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM marathon_runs WHERE marathon_id = ? "
        "ORDER BY COALESCE(scheduled_at, '9999'), order_no, id",
        (int(marathon_id),),
    )
    return list(await cur.fetchall())


async def run_by_id(db: Any, marathon_id: int, run_id: Any) -> Any:
    try:
        wanted = int(run_id)
    except (TypeError, ValueError):
        return None
    cur = await db.conn.execute(
        "SELECT * FROM marathon_runs WHERE id = ? AND marathon_id = ?", (wanted, int(marathon_id))
    )
    return await cur.fetchone()


async def pairings_of(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM marathon_people WHERE guild_id = ? ORDER BY runner_name, id",
        (int(guild_id),),
    )
    return list(await cur.fetchall())


async def pairing_by_id(db: Any, guild_id: int, pairing_id: Any) -> Any:
    try:
        wanted = int(pairing_id)
    except (TypeError, ValueError):
        return None
    cur = await db.conn.execute(
        "SELECT * FROM marathon_people WHERE id = ? AND guild_id = ?", (wanted, int(guild_id))
    )
    return await cur.fetchone()


async def insert_marathon(
    db: Any,
    guild_id: int,
    *,
    name: str,
    url: str,
    source: str,
    ref: str,
    spotlight_id: int | None,
    starts_at: str | None,
    added_by: int | None,
    feed_id: int | None = None,
    event_mode: str = "none",
) -> int:
    cur = await db.conn.execute(
        "INSERT INTO marathons(guild_id, name, schedule_url, source, source_ref, spotlight_id, "
        "starts_at, ends_at, added_by, added_at, feed_id, event_mode) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            int(guild_id),
            name,
            url,
            source,
            ref,
            spotlight_id,
            starts_at,
            starts_at,
            added_by,
            now_iso(),
            feed_id,
            event_mode,
        ),
    )
    await db.conn.commit()
    return int(cur.lastrowid)


MARATHON_COLUMNS = {
    "name",
    "spotlight_id",
    "starts_at",
    "ends_at",
    "active",
    "poll_minutes",
    "board_channel_id",
    "board_message_id",
    "board_pinned",
    "last_fetched_at",
    "last_fetch_ok",
    "last_error",
    "fetch_failures",
    "fetch_hash",
    "source_ref",
    "suggested_next",
    "event_id",
    "event_wanted",
    "feed_id",
    "event_mode",
    "held_by_channel",
}
RUN_COLUMNS = {
    "order_no",
    "game",
    "display_name",
    "twitch_game",
    "category",
    "runners_text",
    "people",
    "scheduled_at",
    "ends_at",
    "run_seconds",
    "previous_scheduled_at",
    "moved_at",
    "state",
    "live_at",
    "live_because",
    "done_at",
    "shout_message_id",
    "shout_channel_id",
    "reminders_sent",
    "last_seen_at",
    "event_id",
}


async def update_marathon(db: Any, marathon_id: int, **fields: Any) -> None:
    wanted = {key: value for key, value in fields.items() if key in MARATHON_COLUMNS}
    if not wanted:
        return
    sets = ", ".join(f"{key} = ?" for key in wanted)
    await db.conn.execute(
        f"UPDATE marathons SET {sets} WHERE id = ?", (*wanted.values(), int(marathon_id))
    )
    await db.conn.commit()


async def update_run(db: Any, run_id: int, **fields: Any) -> None:
    wanted = {key: value for key, value in fields.items() if key in RUN_COLUMNS}
    if not wanted:
        return
    sets = ", ".join(f"{key} = ?" for key in wanted)
    await db.conn.execute(
        f"UPDATE marathon_runs SET {sets} WHERE id = ?", (*wanted.values(), int(run_id))
    )
    await db.conn.commit()


async def delete_marathon(db: Any, marathon_id: int) -> None:
    for sql in (
        "DELETE FROM marathon_runs WHERE marathon_id = ?",
        "DELETE FROM marathon_people WHERE marathon_id = ?",
        "DELETE FROM marathon_spotlights WHERE marathon_id = ?",
        "DELETE FROM marathons WHERE id = ?",
    ):
        await db.conn.execute(sql, (int(marathon_id),))
    await db.conn.commit()


async def upsert_pairing(
    db: Any,
    guild_id: int,
    marathon_id: int | None,
    runner_name: str,
    user_id: int,
    added_by: int | None,
) -> int:
    key = mt.runner_key(runner_name)
    await db.conn.execute(
        "DELETE FROM marathon_people WHERE guild_id = ? AND runner_name = ? AND marathon_id IS ?",
        (int(guild_id), key, marathon_id),
    )
    cur = await db.conn.execute(
        "INSERT INTO marathon_people(guild_id, marathon_id, runner_name, user_id, added_by, "
        "added_at) VALUES (?, ?, ?, ?, ?, ?)",
        (int(guild_id), marathon_id, key, int(user_id), added_by, now_iso()),
    )
    await db.conn.commit()
    return int(cur.lastrowid)


async def delete_pairing(db: Any, pairing_id: int) -> bool:
    cur = await db.conn.execute("DELETE FROM marathon_people WHERE id = ?", (int(pairing_id),))
    await db.conn.commit()
    return cur.rowcount > 0


def usernames_of(guild: Any) -> dict[str, int]:
    return {
        str(member.name).lower(): int(member.id)
        for member in list(getattr(guild, "members", None) or ())
        if getattr(member, "name", None) and not getattr(member, "bot", False)
    }


async def links_of(db: Any) -> dict[str, int]:
    cur = await db.conn.execute("SELECT twitch_login, user_id FROM golive_links")
    return {str(row["twitch_login"]).lower(): int(row["user_id"]) for row in await cur.fetchall()}


async def marathon_windows(db: Any, marathon_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM spotlight_ping_windows WHERE source = ? AND source_id = ?",
        (spot.WINDOW_MARATHON, int(marathon_id)),
    )
    return list(await cur.fetchall())


# --- small reads ------------------------------------------------------------------------------


async def opted_out_channel(db: Any, spotlight_id: Any) -> Any:
    """The channel row when it is opted out of marathons; None when it takes them or is gone."""
    if spotlight_id in (None, "", 0, "0"):
        return None
    try:
        row = await channel_by_id(db, int(spotlight_id))
    except (TypeError, ValueError):
        return None
    return row if row is not None and not takes_marathons(row) else None


def opted_out_said(row: Any) -> str:
    return OPTED_OUT_REFUSAL.format(channel=channel_word_of(row))


def words_for(bot: Any, guild_id: int) -> dict[str, str]:
    return {key: str(bot.store.get(guild_id, key)) for key in MARATHON_WORDS}


def mode_of(bot: Any, guild_id: int) -> str:
    return str(bot.store.get(guild_id, MARATHON_MODE_KEY))


def cog_of(bot: Any) -> Any:
    getter = getattr(bot, "get_cog", None)
    return getter(COG_NAME) if callable(getter) else None


def rehearsal_home(bot: Any, guild: Any) -> int | None:
    return shadow_home.channel_id(bot, guild, feature=SHADOW_FEATURE)


def rehearsal_details(bot: Any, guild: Any) -> dict[str, Any]:
    """The `shadow_home` a would-row carries: the home a rehearsal went to, empty when `on`."""
    if mode_of(bot, guild.id) == MODE_ON:
        return {}
    return {"shadow_home": rehearsal_home(bot, guild)}


async def channel_login(bot: Any, marathon: Any) -> str | None:
    spotlight_id = _cell(marathon, "spotlight_id")
    if not spotlight_id:
        return None
    row = await channel_by_id(bot.db, int(spotlight_id))
    return str(row["twitch_login"]) if row is not None else None


def said_default(key: str) -> str:
    return str(MARATHON_DEFAULTS[key])


def refused_with(
    bot: Any, guild_id: int, key: str, code: str, status: int, **fields: Any
) -> Outcome:
    rendered = mt.render(bot.store.get(guild_id, key), said_default(key), **fields)
    return refusal(rendered.text, code, status)


# --- the shared moves: the routes and the panel both come in by these -------------------------


async def create_marathon(
    bot: Any,
    guild: Any,
    actor: Any,
    *,
    name: Any,
    url: Any,
    spotlight_id: Any = None,
    make_event: Any = None,
    event_mode: Any = None,
    via: str = VIA_DISCORD,
    feed_id: int | None = None,
) -> Outcome:
    from ...marathon_events import BAD_MODE, makes_marathon_event
    from .marathon_events import BAD_MODE_CODE, mode_for_new

    feed = None
    if feed_id is not None:
        from .marathon_feeds import get_feed

        feed = await get_feed(bot.db, guild.id, feed_id)
    wanted_mode = mode_for_new(
        bot, guild.id, event_mode=event_mode, make_event=make_event, feed=feed
    )
    if wanted_mode is None:
        return refusal(BAD_MODE.format(given=str(event_mode)[:40]), BAD_MODE_CODE, 422)
    wanted_name = " ".join(str(name or "").split())[:100]
    wanted_url = str(url or "").strip()
    if not wanted_name:
        return refusal(mt.NO_NAME, NO_NAME_CODE, 422)
    found = read_url(wanted_url)
    if found is None:
        return refused_with(bot, guild.id, MARATHON_UNKNOWN_SITE_KEY, UNKNOWN_SITE, 422)
    existing = await marathon_by_url(bot.db, guild.id, wanted_url)
    if existing is not None:
        return refused_with(
            bot, guild.id, MARATHON_ALREADY_ADDED_KEY, DUPLICATE, 409, name=existing["name"]
        )
    channel = None
    if spotlight_id not in (None, "", 0, "0"):
        channel = await channel_by_id(bot.db, int(spotlight_id))
        if channel is None or int(channel["guild_id"]) != int(guild.id):
            return refusal(
                mt.NO_SUCH_CHANNEL.format(login=str(spotlight_id)[:40]), NO_SUCH_CHANNEL_CODE, 404
            )
        if not takes_marathons(channel):
            return refusal(opted_out_said(channel), OPTED_OUT_CODE, 409)
    cog = cog_of(bot)
    source, ref = found
    try:
        ref, _event_name = await cog.client.resolve(source, ref)
    except ScheduleError as exc:
        return refused_with(
            bot, guild.id, MARATHON_COULD_NOT_READ_KEY, UNREADABLE, 422, reason=str(exc)
        )
    marathon_id = await insert_marathon(
        bot.db,
        guild.id,
        name=wanted_name,
        url=wanted_url,
        source=source,
        ref=ref,
        spotlight_id=int(channel["id"]) if channel is not None else None,
        starts_at=None,
        added_by=actor_id(actor),
        feed_id=feed_id,
    )
    await log_action(
        bot,
        guild,
        kind_via("marathon.added", via),
        actor=actor,
        details={
            "marathon_id": marathon_id,
            "name": wanted_name,
            "url": wanted_url,
            "source": source,
            "ref": ref,
            "spotlight_id": _cell(channel, "id"),
            "feed_id": feed_id,
            "event_mode": wanted_mode,
            "via": via,
        },
    )
    row = await get_marathon(bot.db, guild.id, marathon_id)
    async with cog.lock(marathon_id):
        read = await cog.refresh(guild, row)
        said = mt.ADDED.format(name=wanted_name, read=read.message)
        await update_marathon(bot.db, marathon_id, event_mode=wanted_mode)
        fresh = await get_marathon(bot.db, guild.id, marathon_id)
        if makes_marathon_event(wanted_mode) and not fresh["event_id"]:
            made = await make_event_for(bot, guild, actor, fresh, via=via)
            said = f"{said} {made.message}"
        await sync_runs(bot, guild, fresh, actor=actor)
    fresh = await get_marathon(bot.db, guild.id, marathon_id)
    return Outcome(True, said, value=fresh)


async def refresh_marathon(bot: Any, guild: Any, marathon: Any) -> Outcome:
    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return refusal(mt.NO_SUCH_MARATHON.format(given=marathon["id"]), NO_SUCH, 404)
        read = await cog.refresh(guild, fresh)
        if read.ok:
            await cog.follow(guild, await get_marathon(bot.db, guild.id, marathon["id"]))
    return read


async def set_active(
    bot: Any, guild: Any, actor: Any, marathon: Any, active: bool, *, via: str = VIA_DISCORD
) -> Outcome:
    if active and _cell(marathon, "held_by_channel"):
        held = await opted_out_channel(bot.db, _cell(marathon, "spotlight_id"))
        if held is not None:
            return refusal(
                HELD_REFUSAL.format(name=marathon["name"], channel=channel_word_of(held)),
                HELD_CODE,
                409,
            )
    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        await update_marathon(
            bot.db, marathon["id"], active=1 if active else 0, held_by_channel=0
        )
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        await cog.sync_window(guild, fresh)
    await log_action(
        bot,
        guild,
        kind_via("marathon.resumed" if active else "marathon.paused", via),
        actor=actor,
        details={"marathon_id": marathon["id"], "name": marathon["name"], "via": via},
    )
    said = mt.RESUMED_NOW if active else mt.PAUSED_NOW
    return Outcome(True, said.format(name=marathon["name"]), value=fresh)


async def set_channel(
    bot: Any, guild: Any, actor: Any, marathon: Any, spotlight_id: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    channel = None
    if spotlight_id not in (None, "", 0, "0"):
        channel = await channel_by_id(bot.db, int(spotlight_id))
        if channel is None or int(channel["guild_id"]) != int(guild.id):
            return refusal(
                mt.NO_SUCH_CHANNEL.format(login=str(spotlight_id)[:40]), NO_SUCH_CHANNEL_CODE, 404
            )
        if not takes_marathons(channel):
            return refusal(opted_out_said(channel), OPTED_OUT_CODE, 409)
    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        await update_marathon(bot.db, marathon["id"], spotlight_id=_cell(channel, "id"))
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        await cog.sync_window(guild, fresh)
    await log_action(
        bot,
        guild,
        kind_via("marathon.channel_set", via),
        actor=actor,
        details={
            "marathon_id": marathon["id"],
            "from": _cell(marathon, "spotlight_id"),
            "to": _cell(channel, "id"),
            "login": _cell(channel, "twitch_login"),
            "via": via,
        },
    )
    return Outcome(True, "", value=fresh)


async def rename_marathon(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon: Any,
    name: Any,
    poll_minutes: Any,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    changes: dict[str, Any] = {}
    if name is not None:
        wanted = " ".join(str(name).split())[:100]
        if not wanted:
            return refusal(mt.NO_NAME, NO_NAME_CODE, 422)
        changes["name"] = wanted
    if poll_minutes is not None:
        if poll_minutes in ("", 0):
            changes["poll_minutes"] = None
        elif (
            isinstance(poll_minutes, bool)
            or not isinstance(poll_minutes, int)
            or not POLL_RANGE[0] <= poll_minutes <= POLL_RANGE[1]
        ):
            return refusal(mt.BAD_POLL, BAD_POLL_CODE, 422)
        else:
            changes["poll_minutes"] = poll_minutes
    if changes:
        await update_marathon(bot.db, marathon["id"], **changes)
        await log_action(
            bot,
            guild,
            kind_via("marathon.updated", via),
            actor=actor,
            details={"marathon_id": marathon["id"], **changes, "via": via},
        )
    return Outcome(True, "", value=await get_marathon(bot.db, guild.id, marathon["id"]))


async def remove_marathon(
    bot: Any, guild: Any, actor: Any, marathon: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    from ...marathon_feeds import VIA_FEED
    from .marathon_events import cancel_every_run_event
    from .marathon_feeds import ignore_removed

    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        await cancel_linked_event(bot, guild, actor, marathon, via=via)
        await cancel_every_run_event(bot, guild, marathon, actor=actor)
        await cog.drop_windows(guild, marathon)
        await cog.unpin_board(guild, marathon, because="removed")
        await delete_marathon(bot.db, marathon["id"])
        await ignore_removed(bot, guild, actor, marathon, via=VIA_FEED)
    await log_action(
        bot,
        guild,
        kind_via("marathon.removed", via),
        actor=actor,
        details={"marathon_id": marathon["id"], "name": marathon["name"], "via": via},
    )
    return Outcome(True, mt.REMOVED.format(name=marathon["name"]))


async def pair_runner(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon: Any,
    runner_name: Any,
    user_id: Any,
    *,
    everywhere: bool = False,
    via: str = VIA_DISCORD,
) -> Outcome:
    name = " ".join(str(runner_name or "").split())[:100]
    if not name:
        return refusal(mt.NO_RUNNER, NO_RUNNER_CODE, 422)
    try:
        member_id = int(user_id)
    except (TypeError, ValueError):
        return refusal(mt.NO_MEMBER, NO_MEMBER_CODE, 422)
    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        pairing_id = await upsert_pairing(
            bot.db,
            guild.id,
            None if everywhere else int(marathon["id"]),
            name,
            member_id,
            actor_id(actor),
        )
        await cog.rematch(guild, marathon)
        await sync_runs(bot, guild, marathon, actor=actor)
        await cog.sync_board(guild, await get_marathon(bot.db, guild.id, marathon["id"]))
    await log_action(
        bot,
        guild,
        kind_via("marathon.paired", via),
        actor=actor,
        target=member_id,
        details={
            "marathon_id": marathon["id"],
            "pairing_id": pairing_id,
            "runner": name,
            "member_id": member_id,
            "everywhere": everywhere,
            "via": via,
        },
    )
    said = mt.PAIRED_EVERYWHERE if everywhere else mt.PAIRED
    return Outcome(True, said.format(runner=name, member=f"<@{member_id}>"), value=pairing_id)


async def unpair_runner(
    bot: Any, guild: Any, actor: Any, marathon: Any, pairing: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        await delete_pairing(bot.db, pairing["id"])
        await cog.rematch(guild, marathon)
        await sync_runs(bot, guild, marathon, actor=actor)
        await cog.sync_board(guild, await get_marathon(bot.db, guild.id, marathon["id"]))
    await log_action(
        bot,
        guild,
        kind_via("marathon.unpaired", via),
        actor=actor,
        target=int(pairing["user_id"]),
        details={
            "marathon_id": marathon["id"],
            "pairing_id": pairing["id"],
            "runner": pairing["runner_name"],
            "member_id": int(pairing["user_id"]),
            "via": via,
        },
    )
    return Outcome(True, mt.UNPAIRED.format(runner=pairing["runner_name"]))


async def post_board(
    bot: Any, guild: Any, actor: Any, marathon: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        why = await cog.sync_board(guild, fresh, force=True, actor=actor, via=via)
    if why:
        return refusal(mt.BOARD_NOT_POSTED.format(name=marathon["name"], why=why), POST_FAILED, 409)
    return Outcome(True, mt.BOARD_POSTED.format(name=marathon["name"]))


async def shout_now(
    bot: Any, guild: Any, actor: Any, marathon: Any, run: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        row = await run_by_id(bot.db, marathon["id"], run["id"])
        if row is None:
            return refusal(mt.NO_SUCH_RUN.format(name=marathon["name"]), NO_SUCH_RUN_CODE, 404)
        if not mt.is_ours(row):
            return refusal(mt.NOT_OURS.format(game=row["game"]), NOT_OURS_CODE, 409)
        if row["state"] not in (mt.UPCOMING, mt.LIVE) or row["shout_message_id"]:
            return refusal(
                mt.NOT_SHOUTABLE.format(game=row["game"], state=row["state"]),
                NOT_SHOUTABLE_CODE,
                409,
            )
        if row["state"] == mt.UPCOMING:
            await update_run(
                bot.db, row["id"], state=mt.LIVE, live_at=now_iso(), live_because=mt.BY_STAFF
            )
            row = await run_by_id(bot.db, marathon["id"], run["id"])
        why = await cog.shout(guild, marathon, row, actor=actor, via=via, force=True)
        await cog.sync_board(guild, await get_marathon(bot.db, guild.id, marathon["id"]))
    if why:
        return refusal(mt.SHOUT_NOT_POSTED.format(game=row["game"], why=why), POST_FAILED, 409)
    return Outcome(True, mt.SHOUTED.format(game=row["game"]))


async def mark_done(
    bot: Any, guild: Any, actor: Any, marathon: Any, run: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        row = await run_by_id(bot.db, marathon["id"], run["id"])
        if row is None:
            return refusal(mt.NO_SUCH_RUN.format(name=marathon["name"]), NO_SUCH_RUN_CODE, 404)
        if row["state"] in (mt.DONE, mt.DROPPED):
            return refusal(
                mt.ALREADY_DONE.format(game=row["game"], state=row["state"]),
                ALREADY_DONE_CODE,
                409,
            )
        await cog.finish(guild, marathon, row, because=mt.BY_STAFF, actor=actor, via=via)
        await cog.sync_board(guild, await get_marathon(bot.db, guild.id, marathon["id"]))
    return Outcome(True, mt.MARKED_DONE.format(game=row["game"]))


async def look_again(
    bot: Any, guild: Any, actor: Any, marathon: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Staff ask the tracker again: a dismissal is cleared and whatever is next is suggested."""
    if not mt.suggests(marathon):
        return refusal(mt.NOT_GDQ.format(name=marathon["name"]), NOT_GDQ_CODE, 409)
    cog = cog_of(bot)
    if not mt.is_over(marathon, cog.clock()):
        return refusal(mt.NOT_OVER.format(name=marathon["name"]), NOT_OVER_CODE, 409)
    async with cog.lock(marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return refusal(mt.NO_SUCH_MARATHON.format(given=marathon["id"]), NO_SUCH, 404)
        return await cog.suggest_next(guild, fresh, notify=False, actor=actor, via=via)


async def open_suggestion(bot: Any, guild: Any, marathon: Any, event_id: Any) -> Any:
    """The fresh row and its open record, or the Outcome that refuses in words."""
    fresh = await get_marathon(bot.db, guild.id, marathon["id"])
    if fresh is None:
        return refusal(mt.NO_SUCH_MARATHON.format(given=marathon["id"]), NO_SUCH, 404)
    record = mt.suggestion_of(fresh)
    if mt.next_state(record) != mt.NEXT_OPEN:
        return refusal(
            mt.NOTHING_SUGGESTED.format(name=fresh["name"]), NOTHING_SUGGESTED_CODE, 409
        )
    if event_id is not None and str(event_id) != str(record["event_id"]):
        return refusal(
            mt.SUGGESTION_MOVED.format(name=fresh["name"]), SUGGESTION_MOVED_CODE, 409
        )
    return (fresh, record)


async def add_next(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon: Any,
    *,
    event_id: Any = None,
    via: str = VIA_DISCORD,
) -> Outcome:
    """Add it: the suggested event becomes a marathon on the ending one's channel, and the record
    keeps the link. An event already on the list is linked, never added twice."""
    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        found = await open_suggestion(bot, guild, marathon, event_id)
        if isinstance(found, Outcome):
            return found
        fresh, record = found
        existing = await marathon_by_ref(bot.db, guild.id, GDQ, record["event_id"])
        if existing is not None:
            added = existing
            said = mt.NEXT_ALREADY.format(next=record["name"], name=existing["name"])
        else:
            channel = (
                await channel_by_id(bot.db, int(fresh["spotlight_id"]))
                if fresh["spotlight_id"]
                else None
            )
            made = await create_marathon(
                bot,
                guild,
                actor,
                name=record["name"],
                url=record["url"],
                spotlight_id=_cell(channel, "id"),
                via=via,
            )
            if not made.ok:
                return made
            added, said = made.value, made.message
        record |= {
            "added_marathon_id": int(added["id"]),
            "added_at": cog.clock().isoformat(),
            "added_by": actor_id(actor),
        }
        await save_suggestion(bot.db, fresh["id"], record)
        await log_action(
            bot,
            guild,
            kind_via("marathon.next_added", via),
            actor=actor,
            details={
                "marathon_id": int(added["id"]),
                "from_marathon_id": fresh["id"],
                "event": record["event_id"],
                "name": record["name"],
                "by": actor_id(actor),
                "created": existing is None,
                "via": via,
            },
        )
        await cog.fold_notice(guild, fresh, record)
    return Outcome(True, said, value=added)


async def dismiss_next(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon: Any,
    *,
    event_id: Any = None,
    via: str = VIA_DISCORD,
) -> Outcome:
    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        found = await open_suggestion(bot, guild, marathon, event_id)
        if isinstance(found, Outcome):
            return found
        fresh, record = found
        record |= {"dismissed_at": cog.clock().isoformat(), "dismissed_by": actor_id(actor)}
        await save_suggestion(bot.db, fresh["id"], record)
        await log_action(
            bot,
            guild,
            kind_via("marathon.next_dismissed", via),
            actor=actor,
            details={
                "marathon_id": fresh["id"],
                "event": record["event_id"],
                "name": record["name"],
                "by": actor_id(actor),
                "via": via,
            },
        )
        await cog.fold_notice(guild, fresh, record)
    return Outcome(True, mt.NEXT_DISMISSED.format(next=record["name"], name=fresh["name"]))


async def mark_upcoming(
    bot: Any, guild: Any, actor: Any, marathon: Any, run: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """A done run comes back: staff hold it, reminders already sent stay sent."""
    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        row = await run_by_id(bot.db, marathon["id"], run["id"])
        if row is None:
            return refusal(mt.NO_SUCH_RUN.format(name=marathon["name"]), NO_SUCH_RUN_CODE, 404)
        if not mt.can_mark_upcoming(row):
            return refusal(
                mt.NOT_RESETTABLE.format(game=row["game"], state=row["state"]),
                NOT_RESETTABLE_CODE,
                409,
            )
        await update_run(
            bot.db,
            row["id"],
            state=mt.UPCOMING,
            live_at=None,
            done_at=None,
            live_because=mt.BY_STAFF,
        )
        await log_action(
            bot,
            guild,
            kind_via("marathon.run_reset", via),
            actor=actor,
            details=cog.run_details(marathon, row)
            | {"from": row["state"], "because": mt.BY_STAFF, "via": via},
        )
        await cog.sync_board(guild, await get_marathon(bot.db, guild.id, marathon["id"]))
    return Outcome(True, mt.RUN_RESET.format(game=row["game"]))


async def mark_live(
    bot: Any, guild: Any, actor: Any, marathon: Any, run: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Staff say it is on: held live until its slot and the grace are over; shouted if it is
    ours and never was."""
    cog = cog_of(bot)
    why = None
    async with cog.lock(marathon["id"]):
        row = await run_by_id(bot.db, marathon["id"], run["id"])
        if row is None:
            return refusal(mt.NO_SUCH_RUN.format(name=marathon["name"]), NO_SUCH_RUN_CODE, 404)
        if not mt.can_mark_live(row):
            return refusal(
                mt.NOT_LIVEABLE.format(game=row["game"], state=row["state"]),
                NOT_LIVEABLE_CODE,
                409,
            )
        await update_run(
            bot.db,
            row["id"],
            state=mt.LIVE,
            live_at=cog.clock().isoformat(),
            done_at=None,
            live_because=mt.BY_STAFF,
        )
        await log_action(
            bot,
            guild,
            kind_via("marathon.run_live", via),
            actor=actor,
            details=cog.run_details(marathon, row)
            | {"from": row["state"], "because": mt.BY_STAFF, "via": via},
        )
        fresh = await run_by_id(bot.db, marathon["id"], run["id"])
        if mt.is_ours(fresh) and not fresh["shout_message_id"]:
            why = await cog.shout(guild, marathon, fresh, actor=actor, via=via)
        await cog.sync_board(guild, await get_marathon(bot.db, guild.id, marathon["id"]))
    said = mt.RUN_MARKED_LIVE.format(game=row["game"])
    if why:
        said += " " + mt.SHOUT_NOT_POSTED.format(game=row["game"], why=why)
    return Outcome(True, said)


# --- a marathon is an event -------------------------------------------------------------------


async def marathon_for_event(db: Any, guild_id: int, event_id: Any) -> Any:
    try:
        wanted = int(event_id)
    except (TypeError, ValueError):
        return None
    cur = await db.conn.execute(
        "SELECT * FROM marathons WHERE guild_id = ? AND event_id = ? ORDER BY id LIMIT 1",
        (int(guild_id), wanted),
    )
    return await cur.fetchone()


async def marathon_of_event_line(bot: Any, guild_id: int, event_id: Any) -> str:
    """The line an event's card says about the marathon that made it; blank for any other."""
    row = await marathon_for_event(bot.db, guild_id, event_id)
    if row is None:
        from .marathon_events import run_of_event

        run = await run_of_event(bot.db, guild_id, event_id)
        if run is None:
            return ""
        return mt.RUN_OF_EVENT.format(game=run["game"], name=run["marathon_name"])
    runs = await runs_of(bot.db, row["id"])
    ours = len([one for one in runs if one["state"] != mt.DROPPED and mt.is_ours(one)])
    return mt.MARATHON_OF_EVENT.format(name=row["name"], ours=ours)


async def linked_event(bot: Any, marathon: Any) -> Any:
    event_id = _cell(marathon, "event_id")
    return await get_event(bot.db, int(event_id)) if event_id else None


async def event_status_of(bot: Any, marathon: Any) -> str | None:
    if not _cell(marathon, "event_id"):
        return None
    row = await linked_event(bot, marathon)
    return str(row["status"]) if row is not None else mt.EVENT_GONE


def event_description(bot: Any, guild: Any, marathon: Any) -> str:
    home = bot.store.get(guild.id, MARATHON_CHANNEL_KEY) or bot.store.get(
        guild.id, GOLIVE_CHANNEL_KEY
    )
    rendered = mt.render(
        bot.store.get(guild.id, MARATHON_EVENT_DESCRIPTION_KEY),
        said_default(MARATHON_EVENT_DESCRIPTION_KEY),
        marathon=marathon["name"],
        channel=f"<#{int(home)}>" if home else "",
    )
    return clamp(rendered.text, EVENT_DESCRIPTION_LIMIT)


async def event_fields_of(bot: Any, guild: Any, marathon: Any) -> EventFields | None:
    """The draft a marathon's event is proposed with; None until the schedule has dates."""
    starts = parse_ts(marathon["starts_at"])
    finishes = parse_ts(marathon["ends_at"])
    if starts is None or finishes is None:
        return None
    login = await channel_login(bot, marathon)
    place = (
        mt.TWITCH_URL.format(login=login)
        if login
        else schedule_page(marathon["source"], marathon["source_ref"]) or marathon["schedule_url"]
    )
    return EventFields(
        clamp(marathon["name"], EVENT_TITLE_LIMIT),
        event_description(bot, guild, marathon),
        Where(WHERE_OTHER, None, clamp(place, EVENT_LOCATION_LIMIT)),
        starts,
        max(1, int((finishes - starts).total_seconds() // 60)),
    )


def requester_for(guild: Any, marathon: Any, actor: Any = None) -> Any:
    """Whoever pressed, else whoever added the marathon, else Black Bloc itself."""
    if actor is not None:
        return actor
    added_by = _cell(marathon, "added_by")
    member = guild.get_member(int(added_by)) if added_by else None
    return member if member is not None else getattr(guild, "me", None)


async def make_event_for(
    bot: Any, guild: Any, actor: Any, marathon: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """A marathon's event goes through the events review like any proposal, never around it."""
    if _cell(marathon, "event_id"):
        return refusal(
            mt.EVENT_ALREADY.format(name=marathon["name"], event_id=int(marathon["event_id"])),
            EVENT_EXISTS_CODE,
            409,
        )
    fields = await event_fields_of(bot, guild, marathon)
    if fields is None:
        return Outcome(True, mt.EVENT_WAITING.format(name=marathon["name"]))
    requester = requester_for(guild, marathon, actor)
    if requester is None:
        await stop_waiting(bot, marathon)
        return refusal(
            mt.EVENT_NOT_MADE.format(why=mt.EVENT_NOBODY), EVENT_REFUSED_CODE, 409
        )
    from ..community.events import propose_from

    said, row = await propose_from(bot, guild, requester, fields, via=via)
    if row is None:
        await stop_waiting(bot, marathon)
        return refusal(mt.EVENT_NOT_MADE.format(why=said), EVENT_REFUSED_CODE, 409)
    await update_marathon(bot.db, marathon["id"], event_id=int(row["id"]))
    await log_action(
        bot,
        guild,
        kind_via("marathon.event_made", via),
        actor=actor,
        details={"marathon_id": marathon["id"], "event_id": int(row["id"]), "via": via},
    )
    return Outcome(
        True,
        mt.EVENT_MADE.format(name=marathon["name"], event_id=int(row["id"])),
        value=int(row["id"]),
    )


async def stop_waiting(bot: Any, marathon: Any) -> None:
    """A wish that cannot be met is dropped, as `event_wanted = 0` was: the mode loses its
    marathon half, so the next read does not try again."""
    from ...marathon_events import mode_of as event_mode_of
    from ...marathon_events import with_marathon_event

    fresh = await get_marathon(bot.db, marathon["guild_id"], marathon["id"])
    mode = event_mode_of(fresh if fresh is not None else marathon)
    await update_marathon(bot.db, marathon["id"], event_mode=with_marathon_event(mode, False))


async def make_event_now(
    bot: Any, guild: Any, actor: Any, marathon: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """The staff door: under the marathon's lock, so a tick cannot make a second one. The
    marathon's mode gains its marathon half, so the event is kept in step from then on."""
    from ...marathon_events import mode_of as event_mode_of
    from ...marathon_events import with_marathon_event

    async with cog_of(bot).lock(marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return refusal(mt.NO_SUCH_MARATHON.format(given=marathon["id"]), NO_SUCH, 404)
        if not fresh["event_id"]:
            wanted = with_marathon_event(event_mode_of(fresh), True)
            await update_marathon(bot.db, fresh["id"], event_mode=wanted)
            fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        return await make_event_for(bot, guild, actor, fresh, via=via)


async def unlink_the_event(
    bot: Any, guild: Any, actor: Any, marathon: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    async with cog_of(bot).lock(marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return refusal(mt.NO_SUCH_MARATHON.format(given=marathon["id"]), NO_SUCH, 404)
        return await unlink_event(bot, guild, actor, fresh, via=via)


async def unlink_event(
    bot: Any, guild: Any, actor: Any, marathon: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Clears the pointer and the wish (the mode loses its marathon half); the event itself
    is not touched."""
    from ...marathon_events import mode_of as event_mode_of
    from ...marathon_events import with_marathon_event

    event_id = _cell(marathon, "event_id")
    if not event_id and not mt.wants_its_event(marathon):
        return refusal(mt.NO_EVENT.format(name=marathon["name"]), NO_EVENT_CODE, 409)
    was = event_mode_of(marathon)
    now = with_marathon_event(was, False)
    await update_marathon(bot.db, marathon["id"], event_id=None, event_mode=now)
    await log_action(
        bot,
        guild,
        kind_via("marathon.event_unlinked", via),
        actor=actor,
        details={
            "marathon_id": marathon["id"],
            "event_id": event_id,
            "from": was,
            "to": now,
            "via": via,
        },
    )
    if not event_id:
        return Outcome(True, mt.EVENT_STOPPED_WAITING.format(name=marathon["name"]))
    return Outcome(
        True, mt.EVENT_UNLINKED.format(name=marathon["name"], event_id=int(event_id))
    )


async def cancel_linked_event(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon: Any,
    *,
    reason: str = MARATHON_REMOVED,
    via: str = VIA_DISCORD,
) -> None:
    """A removed marathon takes its open event with it, through the door the card presses."""
    row = await linked_event(bot, marathon)
    if row is None or row["status"] not in EVENT_KEPT_IN_STEP:
        return
    try:
        await cancel_for(
            bot, guild, row, actor if actor is not None else 0, reason=reason, via=via
        )
    except Exception as exc:
        log.warning(
            "marathon: calling off event #%s for marathon %s did not finish — %s: %s",
            row["id"],
            marathon["id"],
            type(exc).__name__,
            exc,
        )
    fresh = await get_event(bot.db, int(row["id"]))
    if _cell(fresh, "status") != EVENT_CANCELLED:
        return
    await log_action(
        bot,
        guild,
        kind_via("marathon.event_cancelled", via),
        actor=actor,
        details={
            "marathon_id": marathon["id"],
            "event_id": int(row["id"]),
            "reason": reason,
            "via": via,
        },
    )


async def sync_runs(bot: Any, guild: Any, marathon: Any, *, actor: Any = None) -> None:
    """The run events follow whatever just changed; they are the bot's own knock-on rows."""
    from .marathon_events import sync_run_events

    await sync_run_events(bot, guild, marathon, actor=actor)


# --- the cog ----------------------------------------------------------------------------------


class Marathons(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.client = ScheduleClient()
        self.clock = lambda: datetime.now(UTC)
        self._locks: dict[int, asyncio.Lock] = {}
        self._reconciler = Reconciler()
        self._board_sent: dict[int, tuple[Any, str]] = {}
        self._next_tried: set[int] = set()
        self._feed_locks: dict[int, asyncio.Lock] = {}
        self.feeds_seeded: set[int] = set()
        self.last_tick_ok_at: str | None = None
        self.last_tick_error: str | None = None

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name != "ticker":
            return (None, None)
        return (self.last_tick_ok_at, self.last_tick_error)

    def lock(self, marathon_id: Any) -> asyncio.Lock:
        key = int(marathon_id)
        found = self._locks.get(key)
        if found is None:
            found = self._locks[key] = asyncio.Lock()
        return found

    def feed_lock(self, feed_id: Any) -> asyncio.Lock:
        key = int(feed_id)
        found = self._feed_locks.get(key)
        if found is None:
            found = self._feed_locks[key] = asyncio.Lock()
        return found

    async def cog_load(self) -> None:
        from .marathon_feeds import FeedButton, NoticeModePick
        from .marathon_people import PeopleButton

        self.bot.add_dynamic_items(NextButton, FeedButton, NoticeModePick, PeopleButton)
        if not self.bot.db.is_connected:
            return
        self.ticker.start()

    async def cog_unload(self) -> None:
        self.ticker.cancel()
        await self.client.close()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self.bot.db.is_connected:
            return
        await self._reconciler.run(self.tick_once, skip_if_recent=True)

    # --- the minute tick --------------------------------------------------------------------

    @tasks.loop(minutes=TICK_MINUTES)
    async def ticker(self) -> None:
        try:
            await self._reconciler.run(self.tick_once)
        except Exception as exc:
            self.last_tick_error = f"{type(exc).__name__}: {exc}"
            log.exception("marathon: the tick failed")

    @ticker.before_loop
    async def _before_ticker(self) -> None:
        await wait_ready(self.bot, self._ticker_stopped)

    @ticker.error
    async def _ticker_stopped(self, exc: BaseException) -> None:
        self.last_tick_error = f"{type(exc).__name__}: {exc}"
        log.error("marathon: the tick stopped; restarting it", exc_info=exc)
        self.ticker.restart()

    def _guilds(self) -> list[Any]:
        return [
            guild
            for guild in list(getattr(self.bot, "guilds", ()) or ())
            if not getattr(guild, "unavailable", False)
        ]

    async def tick_once(self) -> None:
        from .marathon_feeds import tick_feeds

        if not self.bot.db.is_connected:
            return
        for guild in self._guilds():
            off = mode_of(self.bot, guild.id) == MODE_OFF
            if not off:
                await tick_feeds(self, guild)
            for row in await list_marathons(self.bot.db, guild.id):
                async with self.lock(row["id"]):
                    fresh = await get_marathon(self.bot.db, guild.id, row["id"])
                    if fresh is None:
                        continue
                    if not off:
                        await self.tick_marathon(guild, fresh)
                    elif fresh["board_pinned"] and mt.board_due_off(fresh, self.clock()):
                        await self.unpin_board(guild, fresh, because="over")
        self.last_tick_ok_at = now_iso()
        self.last_tick_error = None

    async def tick_marathon(self, guild: Any, marathon: Any) -> None:
        now = self.clock()
        store = self.bot.store
        if mt.fetch_due(
            marathon,
            now,
            poll_minutes=int(store.get(guild.id, MARATHON_POLL_MINUTES_KEY)),
            far_hours=int(store.get(guild.id, MARATHON_FAR_POLL_HOURS_KEY)),
            lead_days=int(store.get(guild.id, MARATHON_LEAD_DAYS_KEY)),
        ):
            await self.refresh(guild, marathon)
            marathon = await get_marathon(self.bot.db, guild.id, marathon["id"])
        if marathon is None:
            return
        if marathon["board_pinned"] and mt.board_due_off(marathon, now):
            await self.unpin_board(guild, marathon, because="over")
        if not marathon["active"]:
            return
        if mt.is_near(marathon, now, lead_days=int(store.get(guild.id, MARATHON_LEAD_DAYS_KEY))):
            await self.follow(guild, marathon)
        await self.maybe_suggest(guild, marathon["id"])

    # --- the next GDQ event -----------------------------------------------------------------

    async def maybe_suggest(self, guild: Any, marathon_id: int) -> None:
        """Once per marathon per boot: a failure leaves NULL, and only the next boot retries it."""
        if not self.bot.store.get(guild.id, MARATHON_SUGGEST_NEXT_KEY):
            return
        fresh = await get_marathon(self.bot.db, guild.id, marathon_id)
        if fresh is None or int(fresh["id"]) in self._next_tried:
            return
        if not mt.wants_suggestion(fresh, self.clock()):
            return
        self._next_tried.add(int(fresh["id"]))
        await self.suggest_next(guild, fresh, notify=True)

    def next_words(self, guild: Any, marathon: Any, record: Any) -> str:
        fields = mt.next_fields(marathon, record)
        state = mt.next_state(record)
        key = {
            mt.NEXT_NONE: MARATHON_NEXT_NONE_TEMPLATE_KEY,
            mt.NEXT_ADDED: MARATHON_NEXT_ADDED_TEMPLATE_KEY,
        }.get(state, MARATHON_NEXT_TEMPLATE_KEY)
        return mt.render(self.bot.store.get(guild.id, key), said_default(key), **fields).text

    async def suggest_next(
        self,
        guild: Any,
        marathon: Any,
        *,
        notify: bool,
        actor: Any = None,
        via: str = VIA_DISCORD,
    ) -> Outcome:
        """Record first, then the log row, then the notice (checklist 12). A fetch failure writes
        nothing, so the row keeps whatever it had."""
        now = self.clock()
        base = {"marathon_id": marathon["id"], "name": marathon["name"], "via": via}
        try:
            events = await self.client.events()
        except Exception as exc:
            why = str(exc)[:200] if isinstance(exc, ScheduleError) else type(exc).__name__
            await log_action(
                self.bot,
                guild,
                kind_via("marathon.next_failed", via),
                actor=actor,
                details=base | {"reason": why},
            )
            return refusal(mt.LOOK_FAILED.format(why=why), UNREADABLE, 502)
        before = mt.suggestion_of(marathon)
        event = next_gdq_event(events, marathon["source_ref"], now)
        if event is None:
            record = mt.none_record(now)
            await save_suggestion(self.bot.db, marathon["id"], record)
            await log_action(
                self.bot, guild, kind_via("marathon.next_none", via), actor=actor, details=base
            )
            await self.fold_notice(guild, marathon, before)
            return Outcome(True, self.next_words(guild, marathon, record), value=record)
        record = mt.suggestion_record(event, now)
        existing = await marathon_by_ref(self.bot.db, guild.id, GDQ, record["event_id"])
        if existing is not None and int(existing["id"]) != int(marathon["id"]):
            record["added_marathon_id"] = int(existing["id"])
        carried = (
            before is not None
            and mt.next_state(before) == mt.NEXT_OPEN
            and before.get("event_id") == record["event_id"]
            and before.get("notice_message_id")
        )
        if carried:
            record |= {
                "notice_channel_id": before.get("notice_channel_id"),
                "notice_message_id": before.get("notice_message_id"),
            }
        await save_suggestion(self.bot.db, marathon["id"], record)
        shadow = mode_of(self.bot, guild.id) != MODE_ON
        details = base | {
            "event": record["event_id"],
            "short": record["short"],
            "next": record["name"],
            "datetime": record["datetime"],
            "already_on_list": record["added_marathon_id"],
        }
        await log_action(
            self.bot,
            guild,
            kind_via("marathon.would_suggest_next" if shadow else "marathon.next_suggested", via),
            actor=actor,
            details=details | rehearsal_details(self.bot, guild),
        )
        if not carried:
            await self.fold_notice(guild, marathon, before)
        if notify and mt.next_state(record) == mt.NEXT_OPEN:
            await self.post_notice(guild, marathon, record)
        return Outcome(True, self.next_words(guild, marathon, record), value=record)

    async def post_notice(self, guild: Any, marathon: Any, record: dict[str, Any]) -> None:
        text = self.next_words(guild, marathon, record)
        view = notice_view(marathon["id"], record["event_id"])
        message, channel_id, why = await self._send_staff(
            guild,
            text,
            view,
            title=record.get("name"),
            what={"marathon_id": marathon["id"], "event": record["event_id"], "notice": "next"},
        )
        if message is None:
            await log_action(
                self.bot,
                guild,
                "marathon.next_notice_failed",
                details={"marathon_id": marathon["id"], "event": record["event_id"], "reason": why},
            )
            return
        record |= {
            "notice_channel_id": channel_id,
            "notice_message_id": int(message.id),
            "notice_home": NOTICE_SHADOW if mode_of(self.bot, guild.id) != MODE_ON else "",
        }
        await save_suggestion(self.bot.db, marathon["id"], record)

    async def fold_notice(self, guild: Any, marathon: Any, record: Any) -> None:
        """Cosmetic, last: an added notice reads the added words, any other is struck through;
        the buttons stay on it, disabled."""
        if not isinstance(record, dict) or not record.get("notice_message_id"):
            return
        message = await self._fetch(
            guild, record.get("notice_channel_id"), record.get("notice_message_id")
        )
        if message is None:
            return
        if mt.next_state(record) == mt.NEXT_ADDED:
            text = self.next_words(guild, marathon, record)
        else:
            text = "~~" + self.next_words(guild, marathon, {**record, "added_marathon_id": None})
            text += "~~"
        home = record.get("notice_home")
        shadowed = (
            home == NOTICE_SHADOW
            if home is not None
            else str(record.get("notice_channel_id"))
            != str(self.bot.store.get(guild.id, STAFF_CHANNEL_KEY))
        )
        if shadowed:
            text = self._staff_shadowed(guild, text)
        try:
            await message.edit(
                content=text,
                view=notice_view(marathon["id"], record["event_id"], disabled=True),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except Exception as exc:
            log.warning("marathon: could not fold a next-event notice — %s", spot.reason_of(exc))

    def _staff_shadowed(self, guild: Any, text: str) -> str:
        home = self.bot.store.get(guild.id, STAFF_CHANNEL_KEY)
        said = shadow_home.note_line(self.bot, guild, f"<#{home}>" if home else "#?")
        return f"{said}\n{text}" if said else text

    async def _send_staff(
        self,
        guild: Any,
        text: str,
        view: Any,
        *,
        title: Any = None,
        what: Any = None,
        embed: Any = None,
    ) -> tuple[Any, int | None, str | None]:
        """`on` posts where marathon_notice_home says — a post in the events forum while events
        are reviewed there, else staff_channel_id; `shadow` rehearses where shadow_channel_id
        says. Every notice that goes up leaves one marathon.notice_posted row."""
        mode = mode_of(self.bot, guild.id)
        if mode == MODE_OFF:
            return (None, None, MODE_IS_OFF)
        if mode == MODE_ON and self.notice_in_forum(guild):
            found = await self._post_in_forum(
                guild, text, view, title=title, what=what, embed=embed
            )
            if found is not None:
                return found
        home = self.bot.store.get(guild.id, STAFF_CHANNEL_KEY)
        if not home:
            return (None, None, NO_STAFF_CHANNEL)
        channel_id = int(home) if mode == MODE_ON else rehearsal_home(self.bot, guild)
        if channel_id is None:
            return (None, None, NO_CHANNEL)
        guard = getattr(self.bot, "guard", None)
        if guard is not None and not guard.allows_channel(channel_id):
            return (None, None, TEST_MODE)
        channel = shadow_home.channel_of(self.bot, guild, channel_id)
        if channel is None:
            return (None, None, NOT_VISIBLE)
        body = text if mode == MODE_ON else self._staff_shadowed(guild, text)
        try:
            message = await channel.send(
                body,
                view=view,
                allowed_mentions=discord.AllowedMentions.none(),
                **({"embed": embed} if embed is not None else {}),
            )
        except Exception as exc:
            return (None, channel_id, spot.reason_of(exc))
        home_word = NOTICE_STAFF if mode == MODE_ON else NOTICE_SHADOW
        await self._notice_posted(guild, home_word, channel_id, message, what)
        return (message, channel_id, None)

    def notice_in_forum(self, guild: Any) -> bool:
        from ...events import forum_channel_id, reviews_in_forum

        store = self.bot.store
        return (
            str(store.get(guild.id, MARATHON_NOTICE_HOME_KEY)) == NOTICE_EVENTS
            and reviews_in_forum(store, guild.id)
            and forum_channel_id(store, guild.id) is not None
        )

    async def _post_in_forum(
        self, guild: Any, text: str, view: Any, *, title: Any, what: Any, embed: Any = None
    ) -> tuple[Any, int | None, str | None] | None:
        """None falls back to the staff channel, with the reason logged."""
        from ...events import MARATHON_TAG, open_notice_post

        name = mt.render(
            self.bot.store.get(guild.id, MARATHON_NOTICE_TITLE_KEY),
            said_default(MARATHON_NOTICE_TITLE_KEY),
            name=str(title or "").strip() or "?",
        ).text
        post, message, why = await open_notice_post(
            self.bot, guild, name, text, view, tag=MARATHON_TAG, embed=embed
        )
        if post is None or message is None:
            await log_action(
                self.bot,
                guild,
                "marathon.notice_forum_failed",
                details=dict(what or {}) | {"reason": why, "fallback": NOTICE_STAFF},
            )
            return None
        await self._notice_posted(guild, NOTICE_EVENTS, int(post.id), message, what)
        return (message, int(post.id), None)

    async def _notice_posted(
        self, guild: Any, home: str, channel_id: Any, message: Any, what: Any
    ) -> None:
        await log_action(
            self.bot,
            guild,
            "marathon.notice_posted",
            details=dict(what or {})
            | {
                "home": home,
                "channel_id": channel_id,
                "message_id": str(getattr(message, "id", "")) or None,
            },
        )

    # --- reading the schedule ---------------------------------------------------------------

    async def refresh(self, guild: Any, marathon: Any) -> Outcome:
        """One read of the schedule, applied as a diff. A failure keeps every run as it was."""
        now = self.clock()
        try:
            runs = await self.client.runs(marathon["source"], marathon["source_ref"])
        except ScheduleError as exc:
            return await self._failed(guild, marathon, exc, now)
        except Exception as exc:
            return await self._failed(guild, marathon, ScheduleError(str(exc)[:200]), now)
        found = await self.apply(guild, marathon, runs, now)
        await self.sync_window(guild, await get_marathon(self.bot.db, guild.id, marathon["id"]))
        ours = len([one for one in await runs_of(self.bot.db, marathon["id"]) if mt.is_ours(one)])
        return Outcome(
            True,
            mt.READ_NOW.format(runs=len(runs), ours=ours)
            if runs
            else mt.render(
                self.bot.store.get(guild.id, "marathon_no_runs_yet"),
                said_default("marathon_no_runs_yet"),
                marathon=marathon["name"],
            ).text,
            value=found,
        )

    async def _failed(
        self, guild: Any, marathon: Any, exc: ScheduleError, now: datetime
    ) -> Outcome:
        failures = int(marathon["fetch_failures"] or 0) + (0 if exc.unpublished else 1)
        await update_marathon(
            self.bot.db,
            marathon["id"],
            last_fetched_at=now.isoformat(),
            last_fetch_ok=0,
            last_error=str(exc)[:300],
            fetch_failures=failures,
        )
        details = {
            "marathon_id": marathon["id"],
            "name": marathon["name"],
            "reason": str(exc)[:300],
            "failures": failures,
            "unpublished": exc.unpublished,
        }
        await log_action(self.bot, guild, "marathon.fetch_failed", details=details)
        if failures == FAILURES_IMPORTANT and not exc.unpublished:
            await log_action(self.bot, guild, "marathon.schedule_stale", details=details)
        return refusal(
            mt.REFRESH_FAILED.format(name=marathon["name"], why=str(exc)), UNREADABLE, 502
        )

    async def apply(self, guild: Any, marathon: Any, runs: list[Any], now: datetime) -> dict:
        db = self.bot.db
        digest = mt.schedule_hash(runs)
        rows = await runs_of(db, marathon["id"])
        plan = mt.diff(
            rows,
            runs,
            move_minutes=int(self.bot.store.get(guild.id, MARATHON_MOVE_MINUTES_KEY)),
        )
        changed = digest != marathon["fetch_hash"]
        counts = {"runs": len(runs), "added": 0, "moved": 0, "dropped": 0}
        stamp = now.isoformat()
        if changed:
            counts = await self._write_plan(guild, marathon, plan, now) | {"runs": len(runs)}
        starts, ends = mt.span(runs)
        await update_marathon(
            db,
            marathon["id"],
            starts_at=starts or marathon["starts_at"],
            ends_at=ends or marathon["ends_at"],
            fetch_hash=digest,
            last_fetched_at=stamp,
            last_fetch_ok=1,
            last_error=None,
            fetch_failures=0,
        )
        matched = await self.rematch(guild, marathon)
        await self.event_follows(
            guild, marathon, await get_marathon(db, guild.id, marathon["id"])
        )
        await sync_runs(self.bot, guild, marathon)
        await log_action(
            self.bot,
            guild,
            "marathon.fetched",
            details={"marathon_id": marathon["id"], "changed": changed, **counts},
        )
        if changed and (counts["added"] or counts["moved"] or counts["dropped"]):
            await log_action(
                self.bot,
                guild,
                "marathon.schedule_changed",
                details={"marathon_id": marathon["id"], **counts},
            )
        return counts | {"changed": changed, "matched": matched}

    async def event_follows(self, guild: Any, before: Any, after: Any) -> None:
        """The first dated read makes a waiting event; a read that moves the dates re-dates it."""
        if after is None:
            return
        if not after["event_id"]:
            if mt.wants_its_event(after) and after["starts_at"] and after["ends_at"]:
                made = await make_event_for(self.bot, guild, None, after)
                if not made.ok:
                    await log_action(
                        self.bot,
                        guild,
                        "marathon.event_make_failed",
                        details={"marathon_id": after["id"], "reason": made.message},
                    )
            return
        span = ("starts_at", "ends_at")
        if all(before[key] == after[key] for key in span):
            return
        await self.redate_event(guild, before, after)

    async def redate_event(self, guild: Any, before: Any, after: Any) -> None:
        row = await linked_event(self.bot, after)
        starts, finishes = parse_ts(after["starts_at"]), parse_ts(after["ends_at"])
        if row is None or row["status"] not in EVENT_KEPT_IN_STEP or not (starts and finishes):
            return
        await update_event(
            self.bot.db,
            int(row["id"]),
            title=row["title"],
            description=row["description"],
            where=read_where(row),
            starts_at=starts,
            finishes_at=finishes,
        )
        moved = await move_scheduled_event(
            self.bot, guild, await get_event(self.bot.db, int(row["id"]))
        )
        details = {
            "marathon_id": after["id"],
            "event_id": int(row["id"]),
            "from": {"starts_at": row["starts_at"], "ends_at": row["ends_at"]},
            "to": {"starts_at": starts.isoformat(), "ends_at": finishes.isoformat()},
            "scheduled": moved,
        }
        await log_action(self.bot, guild, "marathon.event_redated", details=details)
        if moved not in SCHEDULED_OK:
            await log_action(self.bot, guild, "marathon.scheduled_move_failed", details=details)

    async def _write_plan(self, guild: Any, marathon: Any, plan: Any, now: datetime) -> dict:
        db = self.bot.db
        stamp = now.isoformat()
        for run in plan.inserts:
            await db.conn.execute(
                "INSERT INTO marathon_runs(marathon_id, external_id, order_no, game, "
                "display_name, twitch_game, category, runners_text, people, scheduled_at, "
                "ends_at, run_seconds, first_seen_at, last_seen_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    int(marathon["id"]),
                    run.external_id,
                    run.order,
                    run.game,
                    run.display_name,
                    run.twitch_game,
                    run.category,
                    _runners_text(run),
                    json.dumps(_raw_people(run)),
                    run.starts_at,
                    run.ends_at,
                    run.run_seconds,
                    stamp,
                    stamp,
                ),
            )
        await db.conn.commit()
        for row, run, moved in plan.updates:
            fields: dict[str, Any] = {
                "order_no": run.order,
                "game": run.game,
                "display_name": run.display_name,
                "twitch_game": run.twitch_game,
                "category": run.category,
                "runners_text": _runners_text(run),
                "people": json.dumps(_merged_people(row, run)),
                "scheduled_at": run.starts_at,
                "ends_at": run.ends_at,
                "run_seconds": run.run_seconds,
                "last_seen_at": stamp,
            }
            if row["state"] == mt.DROPPED:
                fields["state"] = mt.UPCOMING
            if moved:
                fields["previous_scheduled_at"] = row["scheduled_at"]
                fields["moved_at"] = stamp
                fields["reminders_sent"] = json.dumps(
                    mt.rearmed(mt.marks_of(row), run.starts_at, now)
                )
            await update_run(db, row["id"], **fields)
            if moved and mt.is_ours(row):
                for member_id in mt.member_ids(row):
                    await log_action(
                        self.bot,
                        guild,
                        "marathon.member_run_moved",
                        target=member_id,
                        details={
                            "marathon_id": marathon["id"],
                            "run_id": row["id"],
                            "member_id": member_id,
                            "game": run.game,
                            "from": row["scheduled_at"],
                            "to": run.starts_at,
                        },
                    )
        for row in plan.dropped:
            await update_run(db, row["id"], state=mt.DROPPED)
        return {
            "added": len(plan.inserts),
            "moved": len(plan.moved),
            "dropped": len(plan.dropped),
        }

    async def rematch(self, guild: Any, marathon: Any) -> int:
        """Every run's people against today's links and pairings; a run newly ours is logged."""
        db = self.bot.db
        links = await links_of(db)
        pairings = await pairings_of(db, guild.id)
        hosts = bool(self.bot.store.get(guild.id, MARATHON_MATCH_HOSTS_KEY))
        usernames = usernames_of(guild)
        newly = 0
        for row in await runs_of(db, marathon["id"]):
            before = mt.people_of(row)
            after = mt.match_people(
                before,
                links,
                pairings,
                marathon_id=marathon["id"],
                match_hosts=hosts,
                usernames=usernames,
            )
            if after == before:
                continue
            await update_run(db, row["id"], people=json.dumps(after))
            was = {int(one["user_id"]) for one in mt.ours(before)}
            for person in mt.ours(after):
                if int(person["user_id"]) in was:
                    continue
                newly += 1
                await log_action(
                    self.bot,
                    guild,
                    "marathon.run_matched",
                    target=int(person["user_id"]),
                    details={
                        "marathon_id": marathon["id"],
                        "run_id": row["id"],
                        "member_id": int(person["user_id"]),
                        "runner": person["name"],
                        "part": person["part"],
                        "game": row["game"],
                    },
                )
        return newly

    # --- the ping window --------------------------------------------------------------------

    async def sync_window(self, guild: Any, marathon: Any) -> None:
        """ONE marathon window, on the marathon's channel, for its dates; nothing otherwise."""
        if marathon is None:
            return
        db = self.bot.db
        spotlight_id = marathon["spotlight_id"]
        row = await channel_by_id(db, int(spotlight_id)) if spotlight_id else None
        bounds = mt.window_bounds(
            marathon, int(self.bot.store.get(guild.id, MARATHON_WINDOW_SLACK_KEY))
        )
        keep = row is not None and bool(marathon["active"]) and bounds is not None
        existing = await marathon_windows(db, marathon["id"])
        stale = [one for one in existing if not keep or int(one["spotlight_id"]) != int(row["id"])]
        for window in stale:
            await db.conn.execute(
                "DELETE FROM spotlight_ping_windows WHERE id = ?", (int(window["id"]),)
            )
            await db.conn.commit()
            await log_action(
                self.bot,
                guild,
                "marathon.window_dropped",
                details={
                    "marathon_id": marathon["id"],
                    "window_id": window["id"],
                    "spotlight_id": window["spotlight_id"],
                },
            )
        if not keep:
            return
        starts, ends = bounds
        current = next((one for one in existing if one not in stale), None)
        if current is not None:
            if (current["starts_at"], current["ends_at"], current["note"]) == (
                starts,
                ends,
                marathon["name"],
            ):
                return
            await db.conn.execute(
                "UPDATE spotlight_ping_windows SET starts_at = ?, ends_at = ?, note = ? "
                "WHERE id = ?",
                (starts, ends, marathon["name"], int(current["id"])),
            )
            await db.conn.commit()
            window_id = int(current["id"])
        else:
            cur = await db.conn.execute(
                "INSERT INTO spotlight_ping_windows(guild_id, spotlight_id, starts_at, ends_at, "
                "note, source, source_id, added_by, added_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    int(guild.id),
                    int(row["id"]),
                    starts,
                    ends,
                    marathon["name"],
                    spot.WINDOW_MARATHON,
                    int(marathon["id"]),
                    None,
                    now_iso(),
                ),
            )
            await db.conn.commit()
            window_id = int(cur.lastrowid)
        await log_action(
            self.bot,
            guild,
            "marathon.window_set",
            details={
                "marathon_id": marathon["id"],
                "window_id": window_id,
                "spotlight_id": row["id"],
                "starts_at": starts,
                "ends_at": ends,
            },
        )

    async def drop_windows(self, guild: Any, marathon: Any) -> None:
        await self.sync_window(guild, {**dict(marathon), "active": 0})

    # --- following a near marathon ----------------------------------------------------------

    async def follow(self, guild: Any, marathon: Any) -> bool:
        """States, then reminders, then the board — the board last because it shows the rest."""
        if marathon is None or not marathon["active"] or mode_of(self.bot, guild.id) == MODE_OFF:
            return False
        now = self.clock()
        moved = await self.advance(guild, marathon, now)
        await self.remind(guild, marathon, now)
        await self.sync_board(guild, await get_marathon(self.bot.db, guild.id, marathon["id"]))
        return moved

    async def advance(self, guild: Any, marathon: Any, now: datetime) -> bool:
        store = self.bot.store
        rows = await runs_of(self.bot.db, marathon["id"])
        session = None
        if marathon["spotlight_id"] and store.get(guild.id, MARATHON_TITLE_CONFIRMS_KEY):
            if await channel_by_id(self.bot.db, int(marathon["spotlight_id"])) is not None:
                session = await open_session(self.bot.db, int(marathon["spotlight_id"]))
        hit = (
            mt.title_hit(_cell(session, "title"), _cell(session, "game"), rows, now)
            if session is not None
            else None
        )
        changes = mt.advance(
            rows,
            now,
            hit=hit,
            watching=session is not None,
            grace_minutes=int(store.get(guild.id, MARATHON_LATE_GRACE_KEY)),
        )
        touched = False
        for change in changes:
            ours = mt.is_ours(change.row)
            touched = touched or ours
            if change.to == mt.LIVE:
                await update_run(
                    self.bot.db,
                    change.row["id"],
                    state=mt.LIVE,
                    live_at=now.isoformat(),
                    live_because=change.because,
                )
                if not ours:
                    continue
                await log_action(
                    self.bot,
                    guild,
                    "marathon.run_live",
                    details=self.run_details(marathon, change.row) | {"because": change.because},
                )
                fresh = await run_by_id(self.bot.db, marathon["id"], change.row["id"])
                if not fresh["shout_message_id"]:
                    await self.shout(guild, marathon, fresh)
                continue
            if change.skipped and ours:
                await update_run(
                    self.bot.db, change.row["id"], state=mt.DONE, done_at=now.isoformat()
                )
                await log_action(
                    self.bot,
                    guild,
                    "marathon.run_skipped",
                    details=self.run_details(marathon, change.row) | {"because": change.because},
                )
                continue
            await self.finish(guild, marathon, change.row, because=change.because, quiet=not ours)
        return touched

    def run_details(self, marathon: Any, row: Any) -> dict[str, Any]:
        members = mt.member_ids(row)
        return {
            "marathon_id": marathon["id"],
            "run_id": row["id"],
            "member_id": members[0] if members else None,
            "members": members,
            "game": row["game"],
            "scheduled_at": row["scheduled_at"],
        }

    async def finish(
        self,
        guild: Any,
        marathon: Any,
        row: Any,
        *,
        because: str,
        quiet: bool = False,
        actor: Any = None,
        via: str = VIA_DISCORD,
    ) -> None:
        """Done is recorded first; the past-tense edit is cosmetic and may fail on its own."""
        await update_run(self.bot.db, row["id"], state=mt.DONE, done_at=now_iso())
        if quiet:
            return
        edited = False
        if row["shout_message_id"] and self.bot.store.get(guild.id, MARATHON_EDIT_DONE_KEY):
            edited = await self._edit_done(guild, marathon, row)
        await log_action(
            self.bot,
            guild,
            kind_via("marathon.run_done", via),
            actor=actor,
            details=self.run_details(marathon, row)
            | {"because": because, "edited": edited, "via": via},
        )

    async def _edit_done(self, guild: Any, marathon: Any, row: Any) -> bool:
        words = words_for(self.bot, guild.id)
        url = mt.run_url(row, await channel_login(self.bot, marathon), marathon["schedule_url"])
        text = mt.render(
            words[MARATHON_DONE_TEMPLATE_KEY],
            said_default(MARATHON_DONE_TEMPLATE_KEY),
            **mt.run_fields(row, marathon, words, url=url),
        ).text
        message = await self._fetch(guild, row["shout_channel_id"], row["shout_message_id"])
        if message is None:
            return False
        try:
            await message.edit(content=text, allowed_mentions=discord.AllowedMentions.none())
        except Exception as exc:
            log.warning("marathon: could not edit a shoutout — %s", spot.reason_of(exc))
            return False
        return True

    # --- reminders --------------------------------------------------------------------------

    async def remind(self, guild: Any, marathon: Any, now: datetime) -> None:
        store = self.bot.store
        ping_mark = int(store.get(guild.id, MARATHON_PING_MINUTES_KEY))
        marks = mt.reminder_marks(store.get(guild.id, MARATHON_REMINDER_MINUTES_KEY), ping_mark)
        stale_after = int(store.get(guild.id, MARATHON_REMINDER_STALE_KEY))
        for row in await runs_of(self.bot.db, marathon["id"]):
            if not mt.is_ours(row):
                continue
            mark, skipped = mt.due_marks(row, marks, now, stale_minutes=stale_after)
            if mark is None and not skipped:
                continue
            sent = sorted(
                set(mt.marks_of(row)) | set(skipped) | ({mark} if mark is not None else set())
            )
            await update_run(self.bot.db, row["id"], reminders_sent=json.dumps(sent))
            for one in skipped:
                await log_action(
                    self.bot,
                    guild,
                    "marathon.reminder_skipped",
                    details=self.run_details(marathon, row) | {"mark": one},
                )
            if mark is not None:
                await self._post_reminder(guild, marathon, row, mark, pinging=mark == ping_mark)

    async def _post_reminder(
        self, guild: Any, marathon: Any, row: Any, mark: int, *, pinging: bool
    ) -> None:
        words = words_for(self.bot, guild.id)
        login = await channel_login(self.bot, marathon)
        url = mt.run_url(row, login, marathon["schedule_url"])
        text = mt.render(
            words[MARATHON_REMINDER_TEMPLATE_KEY],
            said_default(MARATHON_REMINDER_TEMPLATE_KEY),
            **mt.run_fields(row, marathon, words, url=url),
        ).text
        roles: list[int] = []
        if pinging and self.bot.store.get(guild.id, MARATHON_REMINDER_PINGS_KEY):
            roles = await self._ping_roles(guild, marathon, row)
        message, channel_id, why = await self._send(guild, ping_prefix(*roles) + text, roles)
        details = self.run_details(marathon, row) | {
            "mark": mark,
            "pinged": bool(roles),
            "roles": roles,
            "message_id": str(getattr(message, "id", "")) or None,
            "channel_id": channel_id,
        }
        if message is None:
            await log_action(
                self.bot, guild, "marathon.reminder_failed", details=details | {"reason": why}
            )
            return
        shadow = mode_of(self.bot, guild.id) != MODE_ON
        await log_action(
            self.bot,
            guild,
            "marathon.would_remind" if shadow else "marathon.reminded",
            details=details | rehearsal_details(self.bot, guild),
        )

    async def _ping_roles(self, guild: Any, marathon: Any, row: Any) -> list[int]:
        """The member's own ping role, and the channel's through the ping-windows gate — never
        the global go-live role: this is not a go-live."""
        found: list[int] = []
        for member_id in mt.member_ids(row):
            role_id = await pings.announced_fan_role(self.bot, guild, member_id)
            if role_id:
                found.append(int(role_id))
        spotlight_id = marathon["spotlight_id"]
        channel = await channel_by_id(self.bot.db, int(spotlight_id)) if spotlight_id else None
        if channel is not None and spot.pings_now(
            channel, await windows_for(self.bot.db, int(channel["id"])), self.clock()
        ):
            role_id = await pings.announced_spotlight_fan_role(self.bot, guild, int(channel["id"]))
            if role_id:
                found.append(int(role_id))
        return list(dict.fromkeys(found))

    # --- the shoutout -----------------------------------------------------------------------

    async def shout(
        self,
        guild: Any,
        marathon: Any,
        row: Any,
        *,
        actor: Any = None,
        via: str = VIA_DISCORD,
        force: bool = False,
    ) -> str | None:
        """`force` is staff pressing Shout it now: it posts whatever the run's event says."""
        if not force and await self.said_by_its_event(guild, marathon, row):
            return None
        words = words_for(self.bot, guild.id)
        login = await channel_login(self.bot, marathon)
        url = mt.run_url(row, login, marathon["schedule_url"])
        text = mt.render(
            words[MARATHON_LIVE_TEMPLATE_KEY],
            said_default(MARATHON_LIVE_TEMPLATE_KEY),
            **mt.run_fields(row, marathon, words, url=url),
        ).text
        roles: list[int] = []
        if self.bot.store.get(guild.id, MARATHON_LIVE_PINGS_KEY):
            roles = await self._ping_roles(guild, marathon, row)
        message, channel_id, why = await self._send(guild, ping_prefix(*roles) + text, roles)
        details = self.run_details(marathon, row) | {"pinged": bool(roles), "via": via}
        if message is None:
            await log_action(
                self.bot,
                guild,
                kind_via("marathon.shout_failed", via),
                actor=actor,
                details=details | {"reason": why},
            )
            return why
        await update_run(
            self.bot.db, row["id"], shout_message_id=int(message.id), shout_channel_id=channel_id
        )
        shadow = mode_of(self.bot, guild.id) != MODE_ON
        await log_action(
            self.bot,
            guild,
            kind_via("marathon.would_shout" if shadow else "marathon.shouted", via),
            actor=actor,
            details=details
            | {"message_id": str(message.id), "channel_id": channel_id}
            | rehearsal_details(self.bot, guild),
        )
        return None

    async def said_by_its_event(self, guild: Any, marathon: Any, row: Any) -> bool:
        """A run whose own event is approved is announced by the events feature as it starts;
        the shoutout would say it twice, so it is skipped unless the key says both."""
        if self.bot.store.get(guild.id, MARATHON_SHOUT_WHEN_RUN_HAS_EVENT_KEY):
            return False
        event_id = _cell(row, "event_id")
        event = await get_event(self.bot.db, int(event_id)) if event_id else None
        if event is None or event["status"] not in EVENT_ANNOUNCED:
            return False
        await log_action(
            self.bot,
            guild,
            "marathon.shout_skipped",
            details=self.run_details(marathon, row)
            | {"because": "run_event", "event_id": int(event_id)},
        )
        return True

    # --- the board --------------------------------------------------------------------------

    async def board_words(self, guild: Any, marathon: Any) -> str:
        words = words_for(self.bot, guild.id)
        rows = await runs_of(self.bot.db, marathon["id"])
        login = await channel_login(self.bot, marathon)
        url = (
            f"https://twitch.tv/{login}"
            if login
            else schedule_page(marathon["source"], marathon["source_ref"])
            or marathon["schedule_url"]
        )
        return mt.board_text(
            marathon,
            rows,
            words,
            head=words[MARATHON_BOARD_TEMPLATE_KEY],
            head_default=said_default(MARATHON_BOARD_TEMPLATE_KEY),
            line=words[MARATHON_BOARD_LINE_KEY],
            line_default=said_default(MARATHON_BOARD_LINE_KEY),
            empty=words[MARATHON_BOARD_EMPTY_KEY],
            url=url,
        ).text

    async def sync_board(
        self,
        guild: Any,
        marathon: Any,
        *,
        force: bool = False,
        actor: Any = None,
        via: str = VIA_DISCORD,
    ) -> str | None:
        """Posted once the first run of ours is found (or when staff ask), then edited in place."""
        if marathon is None:
            return None
        mode = mode_of(self.bot, guild.id)
        if mode == MODE_OFF:
            return MODE_IS_OFF
        rows = await runs_of(self.bot.db, marathon["id"])
        if not force and not marathon["board_message_id"] and not any(map(mt.is_ours, rows)):
            return None
        text = await self.board_words(guild, marathon)
        shadow = mode != MODE_ON
        target = self._target(guild)
        key = int(marathon["id"])
        if (
            not force
            and marathon["board_message_id"]
            and self._board_sent.get(key) == (target, text)
        ):
            return None
        message = None
        if marathon["board_message_id"] and marathon["board_channel_id"] == target:
            message = await self._fetch(
                guild, marathon["board_channel_id"], marathon["board_message_id"]
            )
        if message is not None:
            if (getattr(message, "content", None) or "").endswith(text) and not force:
                self._board_sent[key] = (target, text)
                return None
            try:
                await message.edit(
                    content=self._shadowed(guild, text) if shadow else text,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except Exception as exc:
                why = spot.reason_of(exc)
                await log_action(
                    self.bot,
                    guild,
                    kind_via("marathon.board_failed", via),
                    actor=actor,
                    details={"marathon_id": marathon["id"], "reason": why, "via": via},
                )
                return why
            self._board_sent[key] = (target, text)
            await log_action(
                self.bot,
                guild,
                kind_via(
                    "marathon.would_refresh_board" if shadow else "marathon.board_refreshed", via
                ),
                actor=actor,
                details={"marathon_id": marathon["id"], "message_id": str(message.id), "via": via}
                | rehearsal_details(self.bot, guild),
            )
            return None
        sent, channel_id, why = await self._send(guild, text, [], quiet=True)
        if sent is None:
            await log_action(
                self.bot,
                guild,
                kind_via("marathon.board_failed", via),
                actor=actor,
                details={"marathon_id": marathon["id"], "reason": why, "via": via},
            )
            return why
        await update_marathon(
            self.bot.db,
            marathon["id"],
            board_channel_id=channel_id,
            board_message_id=int(sent.id),
            board_pinned=0,
        )
        self._board_sent[key] = (target, text)
        await log_action(
            self.bot,
            guild,
            kind_via("marathon.would_post_board" if shadow else "marathon.board_posted", via),
            actor=actor,
            details={
                "marathon_id": marathon["id"],
                "message_id": str(sent.id),
                "channel_id": channel_id,
                "via": via,
            }
            | rehearsal_details(self.bot, guild),
        )
        if (
            not shadow
            and self.bot.store.get(guild.id, MARATHON_PIN_BOARD_KEY)
            and not mt.board_due_off(marathon, self.clock())
        ):
            await self._pin(guild, marathon, sent)
        return None

    async def _pin(self, guild: Any, marathon: Any, message: Any) -> None:
        try:
            await message.pin(reason=PIN_REASON)
        except Exception as exc:
            await log_action(
                self.bot,
                guild,
                "marathon.board_pin_failed",
                details={"marathon_id": marathon["id"], "reason": spot.reason_of(exc)},
            )
            return
        await update_marathon(self.bot.db, marathon["id"], board_pinned=1)
        await log_action(
            self.bot,
            guild,
            "marathon.board_pinned",
            details={"marathon_id": marathon["id"], "message_id": str(message.id)},
        )

    async def unpin_board(self, guild: Any, marathon: Any, *, because: str) -> None:
        """Checklist 3: the pin comes off because the MESSAGE carries one, whatever the keys say."""
        if not marathon["board_message_id"]:
            return
        await update_marathon(self.bot.db, marathon["id"], board_pinned=0)
        message = await self._fetch(
            guild, marathon["board_channel_id"], marathon["board_message_id"]
        )
        if message is None or not bool(getattr(message, "pinned", False)):
            return
        try:
            await message.unpin(reason=UNPIN_REASON)
        except Exception as exc:
            await log_action(
                self.bot,
                guild,
                "marathon.board_unpin_failed",
                details={"marathon_id": marathon["id"], "reason": spot.reason_of(exc)},
            )
            return
        await log_action(
            self.bot,
            guild,
            "marathon.board_unpinned",
            details={"marathon_id": marathon["id"], "because": because},
        )

    # --- where the posts go -----------------------------------------------------------------

    def _home(self, guild: Any) -> int | None:
        found = self.bot.store.get(guild.id, MARATHON_CHANNEL_KEY) or self.bot.store.get(
            guild.id, GOLIVE_CHANNEL_KEY
        )
        return int(found) if found else None

    def _target(self, guild: Any) -> int | None:
        if mode_of(self.bot, guild.id) == MODE_ON:
            return self._home(guild)
        return rehearsal_home(self.bot, guild)

    def _shadowed(self, guild: Any, text: str) -> str:
        home = self._home(guild)
        said = shadow_home.note_line(self.bot, guild, f"<#{home}>" if home else "#?")
        return f"{said}\n{text}" if said else text

    async def _send(
        self, guild: Any, text: str, roles: list[int], *, quiet: bool = False
    ) -> tuple[Any, int | None, str | None]:
        """`on` posts in the marathon channel; `shadow` rehearses where shadow_channel_id says."""
        mode = mode_of(self.bot, guild.id)
        if mode == MODE_OFF:
            return (None, None, MODE_IS_OFF)
        if self._home(guild) is None:
            return (None, None, NO_CHANNEL)
        channel_id = self._target(guild)
        if channel_id is None:
            return (None, None, NO_CHANNEL)
        guard = getattr(self.bot, "guard", None)
        if guard is not None and not guard.allows_channel(channel_id):
            return (None, None, TEST_MODE)
        channel = shadow_home.channel_of(self.bot, guild, channel_id)
        if channel is None:
            return (None, None, NOT_VISIBLE)
        body = self._shadowed(guild, text) if mode != MODE_ON else text
        mentions = (
            discord.AllowedMentions.none()
            if quiet or not roles
            else discord.AllowedMentions(
                everyone=False, users=False, roles=[discord.Object(one) for one in roles]
            )
        )
        try:
            message = await channel.send(body, allowed_mentions=mentions)
        except Exception as exc:
            return (None, channel_id, spot.reason_of(exc))
        return (message, channel_id, None)

    async def _fetch(self, guild: Any, channel_id: Any, message_id: Any) -> Any:
        if not channel_id or not message_id:
            return None
        channel = shadow_home.channel_of(self.bot, guild, channel_id)
        if channel is None:
            return None
        try:
            return await channel.fetch_message(int(message_id))
        except Exception as exc:
            log.info("marathon: could not read message %s — %s", message_id, spot.reason_of(exc))
            return None


# --- the staff notice's buttons (KI-20: they outlive a restart) --------------------------------


def next_custom_id(marathon_id: Any, event_id: Any, action: str) -> str:
    return f"marathon:{int(marathon_id)}:next:{int(event_id)}:{action}"


class NextButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=NEXT_TEMPLATE
):
    def __init__(
        self, marathon_id: int, event_id: int, action: str, *, disabled: bool = False
    ) -> None:
        self.marathon_id = int(marathon_id)
        self.event_id = int(event_id)
        self.action = action
        adding = action == NEXT_ADD
        super().__init__(
            discord.ui.Button(
                label=mt.NEXT_BUTTON_ADD if adding else mt.NEXT_BUTTON_DISMISS,
                style=discord.ButtonStyle.primary if adding else discord.ButtonStyle.secondary,
                custom_id=next_custom_id(marathon_id, event_id, action),
                disabled=disabled,
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["marathon_id"]), int(match["event_id"]), match["action"])

    async def on_click(self, interaction: discord.Interaction) -> None:
        bot = interaction.client
        guard = getattr(bot, "guard", None)
        if guard is not None and not guard.allows_channel(interaction.channel_id):
            await answer(interaction, guard.refusal_message())
            return
        if not await still_staff(interaction):
            return
        if not bot.db.is_connected:
            await answer(interaction, DB_UNAVAILABLE)
            return
        await interaction.response.defer(ephemeral=True)
        row = await get_marathon(bot.db, interaction.guild.id, self.marathon_id)
        if row is None:
            await answer(interaction, mt.NO_SUCH_MARATHON.format(given=self.marathon_id))
            return
        doing = add_next if self.action == NEXT_ADD else dismiss_next
        outcome = await doing(
            bot, interaction.guild, interaction.user, row, event_id=self.event_id
        )
        await answer(interaction, outcome.message)


def notice_view(marathon_id: Any, event_id: Any, *, disabled: bool = False) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    for action in (NEXT_ADD, NEXT_DISMISS):
        view.add_item(NextButton(int(marathon_id), int(event_id), action, disabled=disabled))
    return view


# --- /event ▸ Marathons… ----------------------------------------------------------------------

ROOT = "root"
CARD = "card"
MINE_VIEW = "mine"
PAIR_VIEW = "pair"
NEXT_VIEW = "next"
RUN_VIEW = "run"
STYLES = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "danger": discord.ButtonStyle.danger,
}
SELECT_CAP = 25
NEXT_LIMIT = 5
MINE_LIMIT = 10


class MarathonPanel(Panel):
    def __init__(self, minutes: int, where: str = ROOT, marathon_id: Any = None) -> None:
        super().__init__(minutes, footer=mt.PANEL_TIMEOUT_FOOTER, again=reopen)
        self.where = where
        self.marathon_id = marathon_id
        self.runner: str | None = None
        self.run_id: Any = None


def minutes_for(bot: Any, guild_id: int) -> int:
    return panel_minutes(bot.store, guild_id, EVENT_PANEL_MINUTES_KEY)


def now_for(bot: Any) -> datetime:
    cog = cog_of(bot)
    return cog.clock() if cog is not None else datetime.now(UTC)


def phase_of(bot: Any, guild: Any, row: Any) -> str:
    lead = int(bot.store.get(guild.id, MARATHON_LEAD_DAYS_KEY))
    return mt.phase(row, now_for(bot), lead_days=lead)


def next_line(row: Any, marathon: Any, words: dict[str, str]) -> str:
    fields = mt.run_fields(row, marathon, words, url="")
    at = parse_ts(row["scheduled_at"])
    return mt.NEXT_LINE.format(
        unix=unix(at) if at is not None else 0,
        game=row["game"],
        member=fields["member"],
        part=fields["part"],
        marathon=marathon["name"],
    )


async def upcoming_of_ours(bot: Any, guild: Any, *, member_id: int | None = None) -> list[str]:
    now = now_for(bot)
    words = words_for(bot, guild.id)
    found: list[tuple[Any, Any]] = []
    for marathon in await list_marathons(bot.db, guild.id):
        if not marathon["active"] or phase_of(bot, guild, marathon) in (mt.OVER, mt.FAR):
            continue
        for row in mt.next_runs(await runs_of(bot.db, marathon["id"]), now, limit=MINE_LIMIT):
            if member_id is None or int(member_id) in mt.member_ids(row):
                found.append((row, marathon))
    found.sort(key=lambda one: str(one[0]["scheduled_at"] or ""))
    limit = NEXT_LIMIT if member_id is None else MINE_LIMIT
    return [next_line(row, marathon, words) for row, marathon in found[:limit]]


def dates_of(row: Any) -> str:
    starts = parse_ts(row["starts_at"])
    ends = parse_ts(row["ends_at"])
    return f"<t:{unix(starts)}:d> – <t:{unix(ends or starts)}:d>" if starts else mt.NO_DATES


def read_of(row: Any) -> str:
    fetched = parse_ts(row["last_fetched_at"])
    if row["last_fetch_ok"] == 0 and fetched is not None:
        return mt.FETCH_TROUBLE.format(unix=unix(fetched), why=row["last_error"] or "")
    if fetched is not None:
        return mt.READ_AGO.format(unix=unix(fetched))
    return mt.NEVER_READ


def counts_of(runs: list[Any]) -> tuple[int, int]:
    live = [one for one in runs if one["state"] != mt.DROPPED]
    return (len(live), len([one for one in live if mt.is_ours(one)]))


def marathon_line(bot: Any, guild: Any, row: Any, runs: list[Any]) -> str:
    phase = phase_of(bot, guild, row)
    total, ours = counts_of(runs)
    return mt.MARATHON_LINE.format(
        name=row["name"],
        phase=mt.PHASE_WORDS.get(phase, phase),
        dates=dates_of(row),
        ours=ours,
        runs=total,
        read=read_of(row),
    )


def reading_of(bot: Any, guild: Any, row: Any, runs: list[Any]) -> dict[str, str]:
    """The reading line's three parts, shared by the card and the staff notice's embed."""
    store = bot.store
    due = mt.next_read_at(
        row,
        now_for(bot),
        poll_minutes=int(store.get(guild.id, MARATHON_POLL_MINUTES_KEY)),
        far_hours=int(store.get(guild.id, MARATHON_FAR_POLL_HOURS_KEY)),
        lead_days=int(store.get(guild.id, MARATHON_LEAD_DAYS_KEY)),
    )
    total, ours = counts_of(runs)
    return {
        "read": read_of(row),
        "next": mt.NEXT_READ.format(unix=unix(due)) if due is not None else mt.NEXT_READ_PAUSED,
        "counts": mt.CARD_COUNTS.format(runs=total, ours=ours),
    }


def source_of(row: Any) -> tuple[str, str]:
    return (
        SOURCE_WORDS.get(row["source"], row["source"]),
        schedule_page(row["source"], row["source_ref"]) or row["schedule_url"],
    )


def schedule_line(bot: Any, guild: Any, row: Any, runs: list[Any]) -> str:
    source, url = source_of(row)
    return mt.CARD_SCHEDULE.format(source=source, url=url, **reading_of(bot, guild, row, runs))


def add_moves(view: Any, moves: Any) -> None:
    for move in moves:
        view.add_item(MarathonMoveButton(move))


def add_site_button(view: Any, bot: Any, row: int) -> None:
    url = site_page_url(getattr(getattr(bot, "settings", None), "origin", ""), FEATURE)
    if url:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link, label=mt.SITE_BUTTON, url=url, row=row
            )
        )


async def build_panel(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, MarathonPanel]:
    """One command, two audiences: members read BaF next; staff also manage the list."""
    staff = bool(bot.store.is_staff(actor))
    rows = await list_marathons(bot.db, guild.id)
    lines = [mt.OURS_NEXT, *(await upcoming_of_ours(bot, guild) or [mt.NOTHING_NEXT])]
    if staff:
        lines += ["", mt.MODE_LINE.format(mode=mode_of(bot, guild.id))]
        for row in rows[:SELECT_CAP]:
            lines.append(marathon_line(bot, guild, row, await runs_of(bot.db, row["id"])))
        if not rows:
            lines.append(mt.NO_MARATHONS)
    embed = discord.Embed(title=mt.PANEL_TITLE, description=clamped(lines))
    view = MarathonPanel(minutes_for(bot, guild.id))
    if staff and rows:
        view.add_item(MarathonPick(rows))
    elif rows:
        from .marathon_people import MarathonPeoplePick

        view.add_item(MarathonPeoplePick(rows))
    add_moves(view, mt.root_moves(staff=staff))
    if staff:
        add_site_button(view, bot, row=3)
    return (embed, view)


async def build_mine(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, MarathonPanel]:
    lines = [
        mt.MY_RUNS,
        *(await upcoming_of_ours(bot, guild, member_id=actor.id) or [mt.NOTHING_MINE]),
    ]
    embed = discord.Embed(title=mt.PANEL_TITLE, description=clamped(lines))
    view = MarathonPanel(minutes_for(bot, guild.id), MINE_VIEW)
    add_moves(view, (mt.BACK_MOVE,))
    return (embed, view)


async def build_card(
    bot: Any, guild: Any, marathon_id: Any, *, pairing: bool = False, runner: Any = None
) -> tuple[discord.Embed | None, MarathonPanel | None]:
    row = await get_marathon(bot.db, guild.id, marathon_id)
    if row is None:
        return (None, None)
    runs = await runs_of(bot.db, row["id"])
    words = words_for(bot, guild.id)
    login = await channel_login(bot, row)
    phase = phase_of(bot, guild, row)
    lines = [
        mt.CARD_HEAD.format(phase=mt.PHASE_WORDS.get(phase, phase), dates=dates_of(row)),
        schedule_line(bot, guild, row, runs),
    ]
    if row["poll_minutes"]:
        lines.append(mt.POLL_SAVED.format(name=row["name"], minutes=row["poll_minutes"]))
    has_next = mt.suggests(row) and mt.is_over(row, now_for(bot))
    if has_next:
        lines.append(next_line_of(bot, guild, row))
    ours = [one for one in runs if one["state"] != mt.DROPPED and mt.is_ours(one)]
    lines += ["", mt.CARD_RUNS] + [next_line(one, row, words) for one in ours[:MINE_LIMIT]]
    if not runs:
        lines.append(
            mt.render(
                words["marathon_no_runs_yet"],
                said_default("marathon_no_runs_yet"),
                marathon=row["name"],
            ).text
        )
    board = (
        mt.CARD_BOARD_UP.format(channel=row["board_channel_id"])
        if row["board_message_id"] and row["board_channel_id"]
        else mt.CARD_BOARD_NONE
    )
    lines += [
        "",
        mt.CARD_EVENT,
        mt.event_line(row, await event_status_of(bot, row)),
        me.EVENT_MODE_LINE.format(words=me.mode_words(me.mode_of(row))),
        "",
        mt.CARD_CHANNEL.format(channel=f"twitch.tv/{login}" if login else mt.CARD_NO_CHANNEL),
        mt.CARD_POSTS.format(board=board),
    ]
    unmatched = mt.unmatched_names(runs)
    embed = discord.Embed(title=row["name"], description=clamped(lines))
    view = MarathonPanel(minutes_for(bot, guild.id), PAIR_VIEW if pairing else CARD, row["id"])
    if pairing:
        view.runner = runner
        view.add_item(NamePick(unmatched, runner))
        view.add_item(WhoPick())
        add_moves(view, (mt.BACK_MOVE,))
        return (embed, view)
    movable = movable_runs(runs, now_for(bot))
    if movable:
        view.add_item(RunPick(movable, words))
    view.add_item(EventModePick(me.mode_of(row)))
    add_moves(view, mt.card_moves(row, has_unmatched=bool(unmatched), has_next=has_next))
    return (embed, view)


def next_line_of(bot: Any, guild: Any, row: Any) -> str:
    record = mt.suggestion_of(row)
    state = mt.next_state(record)
    if state is None:
        return mt.NEXT_NOT_YET
    if state == mt.NEXT_DISMISSED:
        return "~~" + cog_of(bot).next_words(guild, row, record) + "~~\n" + mt.NEXT_DISMISSED_LINE
    if state == mt.NEXT_ADDED:
        return mt.NEXT_ADDED_LINE.format(name=record.get("name") or "")
    return cog_of(bot).next_words(guild, row, record)


def movable_runs(runs: list[Any], now: datetime) -> list[Any]:
    """Ours, anything live, and anything done in the last hours — the runs a staff move fixes."""
    recent = now.timestamp() - RECENT_DONE_HOURS * 3600
    found = []
    for row in runs:
        if row["state"] == mt.DROPPED:
            continue
        done_at = parse_ts(row["done_at"])
        if (
            mt.is_ours(row)
            or row["state"] == mt.LIVE
            or (done_at is not None and done_at.timestamp() >= recent)
        ):
            found.append(row)
    found.sort(
        key=lambda one: abs(
            (parse_ts(one["scheduled_at"]) or now).timestamp() - now.timestamp()
        )
    )
    kept = found[:SELECT_CAP]
    kept.sort(key=lambda one: (str(one["scheduled_at"] or "9999"), one["id"]))
    return kept


async def build_next(bot: Any, guild: Any, marathon_id: Any) -> tuple[Any, Any]:
    row = await get_marathon(bot.db, guild.id, marathon_id)
    if row is None:
        return (None, None)
    embed = discord.Embed(title=row["name"], description=clamped([next_line_of(bot, guild, row)]))
    view = MarathonPanel(minutes_for(bot, guild.id), NEXT_VIEW, row["id"])
    over = mt.suggests(row) and mt.is_over(row, now_for(bot))
    add_moves(view, mt.next_moves(mt.suggestion_of(row), over=over))
    return (embed, view)


async def build_run(bot: Any, guild: Any, marathon_id: Any, run_id: Any) -> tuple[Any, Any]:
    row = await get_marathon(bot.db, guild.id, marathon_id)
    run = await run_by_id(bot.db, row["id"], run_id) if row is not None else None
    if run is None:
        return (None, None)
    words = words_for(bot, guild.id)
    state = mt.run_fields(run, row, words, url="")["state"]
    event_id = run["event_id"]
    event = await get_event(bot.db, int(event_id)) if event_id else None
    lines = [
        f"**{run['game']}** — {run['category'] or ''}",
        f"{mt.stamp_of(run['scheduled_at'], 'f')} · {state}",
        run["runners_text"] or "",
        me.run_event_line(event_id, _cell(event, "status")) if event_id else "",
    ]
    embed = discord.Embed(title=row["name"], description=clamped([one for one in lines if one]))
    view = MarathonPanel(minutes_for(bot, guild.id), RUN_VIEW, row["id"])
    view.run_id = run["id"]
    add_moves(view, mt.run_moves(run) + me.run_event_moves(run))
    return (embed, view)


async def render(interaction: discord.Interaction, embed: Any, view: Any, previous: Any) -> None:
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def open_root(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction, staff=False):
        return
    embed, view = await build_panel(interaction.client, interaction.guild, interaction.user)
    await render(interaction, embed, view, previous)


async def open_mine(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction, staff=False):
        return
    embed, view = await build_mine(interaction.client, interaction.guild, interaction.user)
    await render(interaction, embed, view, previous)


async def open_card(
    interaction: discord.Interaction,
    marathon_id: Any,
    previous: Any = None,
    *,
    pairing: bool = False,
    runner: Any = None,
) -> None:
    if not await opened(interaction):
        return
    embed, view = await build_card(
        interaction.client, interaction.guild, marathon_id, pairing=pairing, runner=runner
    )
    if view is None:
        await open_root(interaction, previous)
        await answer(interaction, mt.NO_SUCH_MARATHON.format(given=str(marathon_id)[:40]))
        return
    await render(interaction, embed, view, previous)


async def open_next(interaction: discord.Interaction, marathon_id: Any, previous: Any) -> None:
    if not await opened(interaction):
        return
    embed, view = await build_next(interaction.client, interaction.guild, marathon_id)
    if view is None:
        await open_root(interaction, previous)
        return
    await render(interaction, embed, view, previous)


async def open_run(
    interaction: discord.Interaction, marathon_id: Any, run_id: Any, previous: Any
) -> None:
    if not await opened(interaction):
        return
    embed, view = await build_run(interaction.client, interaction.guild, marathon_id, run_id)
    if view is None:
        await open_card(interaction, marathon_id, previous)
        await answer(interaction, mt.NO_SUCH_RUN.format(name=str(marathon_id)))
        return
    await render(interaction, embed, view, previous)


async def reopen(interaction: discord.Interaction, previous: Any) -> None:
    from .marathon_feeds import FEED_VIEWS, reopen_feeds

    where = getattr(previous, "where", ROOT)
    if where in FEED_VIEWS:
        await reopen_feeds(interaction, previous)
    elif where == NEXT_VIEW and getattr(previous, "marathon_id", None):
        await open_next(interaction, previous.marathon_id, previous)
    elif where == RUN_VIEW and getattr(previous, "run_id", None):
        await open_run(interaction, previous.marathon_id, previous.run_id, previous)
    elif where in (CARD, PAIR_VIEW) and getattr(previous, "marathon_id", None):
        await open_card(interaction, previous.marathon_id, previous)
    elif where == MINE_VIEW:
        await open_mine(interaction, previous)
    else:
        await open_root(interaction, previous)


async def run_move(
    interaction: discord.Interaction, view: Any, doing: Any, *, back: Any = None
) -> None:
    """Every staff move re-reads the marathon first: another door may have removed it."""
    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    row = await get_marathon(bot.db, guild.id, view.marathon_id)
    if row is None:
        await open_root(interaction, view)
        await answer(interaction, mt.NO_SUCH_MARATHON.format(given=str(view.marathon_id)[:40]))
        return
    outcome = await doing(bot, guild, interaction.user, row)
    if await get_marathon(bot.db, guild.id, row["id"]) is None:
        await open_root(interaction, view)
    elif back is not None:
        await back(interaction, view)
    else:
        await open_card(interaction, row["id"], view)
    if outcome.message:
        await answer(interaction, outcome.message)


def run_doing(action: str, run_id: Any) -> Any:
    shared = {
        mt.SHOUT: shout_now,
        mt.MARK_DONE: mark_done,
        mt.MARK_UPCOMING: mark_upcoming,
        mt.MARK_LIVE: mark_live,
    }[action]
    return lambda bot, guild, actor, row: shared(bot, guild, actor, row, {"id": run_id})


def run_event_doing(action: str, run_id: Any) -> Any:
    from .marathon_events import make_run_event_now, unlink_run_event

    shared = make_run_event_now if action == me.MAKE_RUN_EVENT else unlink_run_event
    return lambda bot, guild, actor, row: shared(bot, guild, actor, row, {"id": run_id})


def next_doing(action: str) -> Any:
    shared = {mt.ADD_NEXT: add_next, mt.DISMISS_NEXT: dismiss_next, mt.LOOK_AGAIN: look_again}
    return shared[action]


async def back_to_next(interaction: discord.Interaction, view: Any) -> None:
    embed, fresh = await build_next(interaction.client, interaction.guild, view.marathon_id)
    if fresh is None:
        await open_card(interaction, view.marathon_id, view)
        return
    await render(interaction, embed, fresh, view)


async def back_to_run(interaction: discord.Interaction, view: Any) -> None:
    embed, fresh = await build_run(
        interaction.client, interaction.guild, view.marathon_id, view.run_id
    )
    if fresh is None:
        await open_card(interaction, view.marathon_id, view)
        return
    await render(interaction, embed, fresh, view)


async def ask_remove(interaction: discord.Interaction, view: Any) -> None:
    if not await opened(interaction):
        return
    row = await get_marathon(interaction.client.db, interaction.guild.id, view.marathon_id)
    if row is None:
        await open_root(interaction, view)
        return
    embed, fresh = await build_card(interaction.client, interaction.guild, row["id"])
    fresh.clear_items()

    async def yes(one: discord.Interaction, card: Any) -> None:
        await run_move(
            one,
            card,
            lambda bot, guild, actor, marathon: remove_marathon(bot, guild, actor, marathon),
        )

    async def no(one: discord.Interaction, card: Any) -> None:
        await open_card(one, row["id"], card)

    await confirm(
        interaction,
        fresh,
        embed,
        confirm_items(yes=mt.REMOVE_MOVE.label, no=KEEP_IT, on_yes=yes, on_no=no),
        view,
        question=mt.REMOVE_QUESTION.format(name=row["name"]),
    )


class MarathonMoveButton(discord.ui.Button):
    def __init__(self, move: Any) -> None:
        super().__init__(label=move.label, style=STYLES[move.style], row=move.row)
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        action = self.move.action
        if action == mt.FEEDS or action.startswith("feed_"):
            from .marathon_feeds import feed_move

            await feed_move(interaction, view, action)
        elif action == mt.LOGS:
            await send_logs(interaction, FEATURE)
        elif action == mt.EVENTS:
            from ..community.events import back_to_panel

            await back_to_panel(interaction, view)
        elif action == mt.MINE:
            await open_mine(interaction, view)
        elif action == mt.BACK:
            if view.where in (PAIR_VIEW, NEXT_VIEW, RUN_VIEW):
                await open_card(interaction, view.marathon_id, view)
            else:
                await open_root(interaction, view)
        elif action == mt.NEXT:
            await open_next(interaction, view.marathon_id, view)
        elif action == mt.POLL:
            if await still_staff(interaction):
                row = await get_marathon(
                    interaction.client.db, interaction.guild.id, view.marathon_id
                )
                current = row["poll_minutes"] if row is not None else None
                await interaction.response.send_modal(PollModal(view, current))
        elif action in (mt.ADD_NEXT, mt.DISMISS_NEXT, mt.LOOK_AGAIN):
            await run_move(interaction, view, next_doing(action), back=back_to_next)
        elif action in (mt.SHOUT, mt.MARK_DONE, mt.MARK_UPCOMING, mt.MARK_LIVE):
            await run_move(interaction, view, run_doing(action, view.run_id), back=back_to_run)
        elif action in (me.MAKE_RUN_EVENT, me.UNLINK_RUN_EVENT):
            await run_move(
                interaction, view, run_event_doing(action, view.run_id), back=back_to_run
            )
        elif action == mt.ADD:
            if await still_staff(interaction):
                from .marathon_events import default_mode

                wanted = default_mode(interaction.client, interaction.guild.id)
                await interaction.response.send_modal(AddMarathonModal(view, wanted))
        elif action == mt.MAKE_EVENT:
            await run_move(interaction, view, make_event_now)
        elif action == mt.UNLINK_EVENT:
            await run_move(interaction, view, unlink_the_event)
        elif action == mt.REFRESH and view.where == ROOT:
            await open_root(interaction, view)
        elif action == mt.REFRESH:
            await run_move(
                interaction,
                view,
                lambda bot, guild, actor, row: refresh_marathon(bot, guild, row),
            )
        elif action in (mt.PAUSE, mt.RESUME):
            await run_move(
                interaction,
                view,
                lambda bot, guild, actor, row: set_active(
                    bot, guild, actor, row, action == mt.RESUME
                ),
            )
        elif action == mt.BOARD:
            await run_move(interaction, view, post_board)
        elif action == mt.REMOVE:
            await ask_remove(interaction, view)
        elif action == mt.PAIR:
            await open_card(interaction, view.marathon_id, view, pairing=True)
        elif action == mt.PEOPLE:
            from .marathon_people import open_people

            await open_people(interaction, view.marathon_id, view)


class MarathonPick(discord.ui.Select):
    def __init__(self, rows: list[Any]) -> None:
        super().__init__(
            placeholder=mt.PICK_MARATHON,
            options=[
                discord.SelectOption(label=str(row["name"])[:100], value=str(row["id"]))
                for row in rows[:SELECT_CAP]
            ],
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_card(interaction, self.values[0], self.view)


class RunPick(discord.ui.Select):
    def __init__(self, rows: list[Any], words: dict[str, str]) -> None:
        options = []
        for row in rows[:SELECT_CAP]:
            state = words.get(mt.STATE_KEYS.get(str(row["state"]), ""), row["state"])
            said = " · ".join(one for one in (str(state), row["runners_text"] or "") if one)
            options.append(
                discord.SelectOption(
                    label=str(row["game"])[:100], value=str(row["id"]), description=said[:100]
                )
            )
        super().__init__(placeholder=mt.PICK_RUN, options=options, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_run(interaction, self.view.marathon_id, self.values[0], self.view)


class NamePick(discord.ui.Select):
    def __init__(self, names: list[str], chosen: Any = None) -> None:
        options = [
            discord.SelectOption(label=name[:100], value=name[:100], default=name == chosen)
            for name in names[:SELECT_CAP]
        ] or [discord.SelectOption(label="—", value="")]
        super().__init__(placeholder=mt.PICK_UNMATCHED, options=options, row=0, disabled=not names)

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_card(
            interaction, self.view.marathon_id, self.view, pairing=True, runner=self.values[0]
        )


class WhoPick(discord.ui.UserSelect):
    def __init__(self) -> None:
        super().__init__(placeholder=mt.PICK_MEMBER, row=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if not view.runner:
            if await still_staff(interaction):
                await answer(interaction, mt.NO_RUNNER)
            return
        member_id = int(self.values[0].id)
        await run_move(
            interaction,
            view,
            lambda bot, guild, actor, row: pair_runner(
                bot, guild, actor, row, view.runner, member_id
            ),
        )


class AddMarathonModal(AnswersErrors, discord.ui.Modal, title=mt.ADD_TITLE):
    name = discord.ui.TextInput(label=mt.ADD_NAME, placeholder=mt.ADD_NAME_HINT, max_length=100)
    url = discord.ui.TextInput(label=mt.ADD_URL, placeholder=mt.ADD_URL_HINT, max_length=200)
    login = discord.ui.TextInput(
        label=mt.ADD_LOGIN, placeholder=mt.ADD_LOGIN_HINT, required=False, max_length=40
    )
    event = discord.ui.TextInput(label=me.ADD_EVENT_LABEL, required=False, max_length=8)

    def __init__(self, previous: Any = None, mode: str = me.NONE) -> None:
        super().__init__()
        self.previous = previous
        self.event.default = mode

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        bot, guild = interaction.client, interaction.guild
        event_mode = me.wanted_mode_answer(self.event) if str(self.event).strip() else None
        if str(self.event).strip() and event_mode is None:
            await open_root(interaction, self.previous)
            await answer(interaction, mt.BAD_ADD_EVENT)
            return
        given = str(self.login).strip().lower().lstrip("@")
        spotlight_id = None
        if given:
            channel = await channel_by_login(bot.db, guild.id, given)
            if channel is None:
                await open_root(interaction, self.previous)
                await answer(interaction, mt.NO_SUCH_CHANNEL.format(login=given[:40]))
                return
            spotlight_id = channel["id"]
        outcome = await create_marathon(
            bot,
            guild,
            interaction.user,
            name=str(self.name),
            url=str(self.url),
            spotlight_id=spotlight_id,
            event_mode=event_mode,
        )
        if outcome.ok:
            await open_card(interaction, outcome.value["id"], self.previous)
        else:
            await open_root(interaction, self.previous)
        await answer(interaction, outcome.message)


class EventModePick(discord.ui.Select):
    def __init__(self, current: str) -> None:
        super().__init__(
            placeholder=me.PICK_MODE,
            options=[
                discord.SelectOption(label=me.MODE_WORDS[one], value=one, default=one == current)
                for one in me.MODES
            ],
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        from .marathon_events import set_event_mode

        wanted = self.values[0]
        await run_move(
            interaction,
            self.view,
            lambda bot, guild, actor, row: set_event_mode(bot, guild, actor, row, wanted),
        )


class PollModal(AnswersErrors, discord.ui.Modal, title=mt.POLL_TITLE):
    minutes = discord.ui.TextInput(
        label=mt.POLL_LABEL, placeholder=mt.POLL_HINT, required=False, max_length=4
    )

    def __init__(self, previous: Any = None, current: Any = None) -> None:
        super().__init__()
        self.previous = previous
        self.minutes.default = str(current) if current else None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        bot, guild = interaction.client, interaction.guild
        marathon_id = getattr(self.previous, "marathon_id", None)
        row = await get_marathon(bot.db, guild.id, marathon_id)
        if row is None:
            await open_root(interaction, self.previous)
            await answer(interaction, mt.NO_SUCH_MARATHON.format(given=str(marathon_id)[:40]))
            return
        given = str(self.minutes).strip()
        wanted: Any = "" if not given else (int(given) if given.isdigit() else given)
        outcome = await rename_marathon(bot, guild, interaction.user, row, None, wanted)
        await open_card(interaction, row["id"], self.previous)
        if not outcome.ok:
            await answer(interaction, outcome.message)
        elif wanted == "":
            await answer(interaction, mt.POLL_CLEARED.format(name=row["name"]))
        else:
            await answer(interaction, mt.POLL_SAVED.format(name=row["name"], minutes=wanted))


def _raw_people(run: Any) -> list[dict[str, Any]]:
    return [{"name": one.name, "login": one.login, "part": one.part} for one in run.people]


def _merged_people(row: Any, run: Any) -> list[dict[str, Any]]:
    """The fresh names with yesterday's matches kept, so rematch can say who is NEWLY ours."""
    before = {(one.get("name"), one.get("part")): one.get("user_id") for one in mt.people_of(row)}
    return [one | {"user_id": before.get((one["name"], one["part"]))} for one in _raw_people(run)]


def _runners_text(run: Any) -> str:
    return ", ".join(one.name for one in run.people if one.part == "runner")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Marathons(bot))


__all__ = [
    "COG_NAME",
    "Marathons",
    "NextButton",
    "add_next",
    "create_marathon",
    "dismiss_next",
    "get_marathon",
    "list_marathons",
    "look_again",
    "make_event_for",
    "make_event_now",
    "marathon_of_event_line",
    "mark_done",
    "mark_live",
    "mark_upcoming",
    "pair_runner",
    "pairings_of",
    "post_board",
    "refresh_marathon",
    "remove_marathon",
    "rename_marathon",
    "run_by_id",
    "runs_of",
    "set_active",
    "set_channel",
    "shout_now",
    "unlink_the_event",
    "unpair_runner",
]
