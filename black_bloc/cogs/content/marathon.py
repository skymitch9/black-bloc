from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

import discord
from discord.ext import commands, tasks

from ... import marathon as mt
from ... import pings
from ... import shadow as shadow_home
from ... import spotlight as spot
from ...actionlog import log_action
from ...golive import now_iso, ping_prefix
from ...logkinds import VIA_DISCORD, kind_via
from ...loops import Reconciler, wait_ready
from ...marathon_sources import ScheduleClient, ScheduleError, read_url, schedule_page
from ...panels import Outcome, refusal
from ...settings_store import (
    MARATHON_ALREADY_ADDED_KEY,
    MARATHON_BOARD_EMPTY_KEY,
    MARATHON_BOARD_LINE_KEY,
    MARATHON_BOARD_TEMPLATE_KEY,
    MARATHON_CHANNEL_KEY,
    MARATHON_COULD_NOT_READ_KEY,
    MARATHON_DEFAULTS,
    MARATHON_DONE_TEMPLATE_KEY,
    MARATHON_EDIT_DONE_KEY,
    MARATHON_FAR_POLL_HOURS_KEY,
    MARATHON_LATE_GRACE_KEY,
    MARATHON_LEAD_DAYS_KEY,
    MARATHON_LIVE_PINGS_KEY,
    MARATHON_LIVE_TEMPLATE_KEY,
    MARATHON_MATCH_HOSTS_KEY,
    MARATHON_MODE_KEY,
    MARATHON_MOVE_MINUTES_KEY,
    MARATHON_PIN_BOARD_KEY,
    MARATHON_PING_MINUTES_KEY,
    MARATHON_POLL_MINUTES_KEY,
    MARATHON_REMINDER_MINUTES_KEY,
    MARATHON_REMINDER_PINGS_KEY,
    MARATHON_REMINDER_STALE_KEY,
    MARATHON_REMINDER_TEMPLATE_KEY,
    MARATHON_TITLE_CONFIRMS_KEY,
    MARATHON_UNKNOWN_SITE_KEY,
    MARATHON_WINDOW_SLACK_KEY,
    MARATHON_WORDS,
)
from .spotlight import channel_by_id, open_session, windows_for

log = logging.getLogger(__name__)

COG_NAME = "Marathons"
FEATURE = "marathon"
GOLIVE_CHANNEL_KEY = "golive_channel_id"
MODE_ON = "on"
MODE_OFF = "off"
TICK_MINUTES = 1
FAILURES_IMPORTANT = 3
NO_CHANNEL = "no channel is set for marathon posts"
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
POST_FAILED = "post_failed"
POLL_RANGE = (10, 120)


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
) -> int:
    cur = await db.conn.execute(
        "INSERT INTO marathons(guild_id, name, schedule_url, source, source_ref, spotlight_id, "
        "starts_at, ends_at, added_by, added_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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


def words_for(bot: Any, guild_id: int) -> dict[str, str]:
    return {key: str(bot.store.get(guild_id, key)) for key in MARATHON_WORDS}


def mode_of(bot: Any, guild_id: int) -> str:
    return str(bot.store.get(guild_id, MARATHON_MODE_KEY))


def cog_of(bot: Any) -> Any:
    getter = getattr(bot, "get_cog", None)
    return getter(COG_NAME) if callable(getter) else None


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
    via: str = VIA_DISCORD,
) -> Outcome:
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
            "via": via,
        },
    )
    row = await get_marathon(bot.db, guild.id, marathon_id)
    async with cog.lock(marathon_id):
        read = await cog.refresh(guild, row)
    fresh = await get_marathon(bot.db, guild.id, marathon_id)
    return Outcome(True, mt.ADDED.format(name=wanted_name, read=read.message), value=fresh)


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
    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        await update_marathon(bot.db, marathon["id"], active=1 if active else 0)
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
    bot: Any, guild: Any, actor: Any, marathon: Any, name: Any, poll_minutes: Any, *, via: str
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
    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        await cog.drop_windows(guild, marathon)
        await cog.unpin_board(guild, marathon, because="removed")
        await delete_marathon(bot.db, marathon["id"])
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
        why = await cog.shout(guild, marathon, row, actor=actor, via=via)
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


# --- the cog ----------------------------------------------------------------------------------


class Marathons(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.client = ScheduleClient()
        self.clock = lambda: datetime.now(UTC)
        self._locks: dict[int, asyncio.Lock] = {}
        self._reconciler = Reconciler()
        self._board_sent: dict[int, tuple[Any, str]] = {}
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

    async def cog_load(self) -> None:
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
        if not self.bot.db.is_connected:
            return
        for guild in self._guilds():
            if mode_of(self.bot, guild.id) == MODE_OFF:
                continue
            for row in await list_marathons(self.bot.db, guild.id):
                async with self.lock(row["id"]):
                    fresh = await get_marathon(self.bot.db, guild.id, row["id"])
                    if fresh is not None:
                        await self.tick_marathon(guild, fresh)
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
        newly = 0
        for row in await runs_of(db, marathon["id"]):
            before = mt.people_of(row)
            after = mt.match_people(
                before, links, pairings, marathon_id=marathon["id"], match_hosts=hosts
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
                    details=self._run_details(marathon, change.row) | {"because": change.because},
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
                    details=self._run_details(marathon, change.row) | {"because": change.because},
                )
                continue
            await self.finish(guild, marathon, change.row, because=change.because, quiet=not ours)
        return touched

    def _run_details(self, marathon: Any, row: Any) -> dict[str, Any]:
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
            details=self._run_details(marathon, row)
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
                    details=self._run_details(marathon, row) | {"mark": one},
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
        details = self._run_details(marathon, row) | {
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
            details=details,
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
        self, guild: Any, marathon: Any, row: Any, *, actor: Any = None, via: str = VIA_DISCORD
    ) -> str | None:
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
        details = self._run_details(marathon, row) | {"pinged": bool(roles), "via": via}
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
            details=details | {"message_id": str(message.id), "channel_id": channel_id},
        )
        return None

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
                details={"marathon_id": marathon["id"], "message_id": str(message.id), "via": via},
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
            },
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
        return shadow_home.channel_id(self.bot, guild)

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
    "create_marathon",
    "get_marathon",
    "list_marathons",
    "mark_done",
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
    "unpair_runner",
]
