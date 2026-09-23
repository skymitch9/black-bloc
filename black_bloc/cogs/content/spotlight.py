from __future__ import annotations

import asyncio
import logging
import sqlite3
from typing import Any

import discord
from discord.ext import commands, tasks

from ... import pings
from ... import shadow as shadow_home
from ... import spotlight as words
from ...actionlog import log_action
from ...command_errors import AnswersErrors
from ...golive import (
    announcement_embed,
    embed_summary,
    ended_embed,
    ended_render,
    from_twitch,
    humanise_duration,
    now_iso,
    ping_prefix,
    render,
    with_box_art,
)
from ...logkinds import VIA_DISCORD, kind_via
from ...loops import Reconciler, wait_ready
from ...panels import Panel, answer, opened, retire, still_staff
from ...settings_store import (
    CHANNEL_OPTOUT_DELETE,
    CHANNEL_OPTOUT_END,
    CHANNEL_OPTOUT_POST_KEY,
    CHANNEL_SPOTLIGHT_DEFAULT_KEY,
    DEFAULT_TIMEZONE_KEY,
    SPOTLIGHT_BAD_DATE_KEY,
    SPOTLIGHT_BUMP_CLEANUP_KEY,
    SPOTLIGHT_BUMP_HOURS_KEY,
    SPOTLIGHT_BUMP_PINGS_KEY,
    SPOTLIGHT_BUMP_TEMPLATE_KEY,
    SPOTLIGHT_DATES_BUTTON_KEY,
    SPOTLIGHT_DEFAULT_DAYS_KEY,
    SPOTLIGHT_END_BEFORE_START_KEY,
    SPOTLIGHT_END_MISSES_KEY,
    SPOTLIGHT_ENDS_LABEL_KEY,
    SPOTLIGHT_MODE_KEY,
    SPOTLIGHT_PIN_KEY,
    SPOTLIGHT_POLL_MINUTES,
    SPOTLIGHT_POLL_MINUTES_KEY,
    SPOTLIGHT_RANGE_KEPT_KEY,
    SPOTLIGHT_RANGE_KEY,
    SPOTLIGHT_SCHEDULED_WORD_KEY,
    SPOTLIGHT_STARTS_LABEL_KEY,
)
from ...timezones import get_timezone
from ...twitch import TwitchError

log = logging.getLogger(__name__)

COG_NAME = "Spotlight"
GOLIVE_COG = "GoLive"
CHANNEL_KEY = "golive_channel_id"
PING_KEY = "golive_ping_role_id"
TEMPLATE_KEY = "golive_template"
LIVE_AUTHOR_KEY = "golive_live_author"
EMBED_KEY = "golive_embed"
END_TEMPLATE_KEY = "golive_end_template"
END_AUTHOR_KEY = "golive_end_author"
MODE_ON = "on"
MODE_OFF = "off"
MODE_SHADOW = "shadow"
SOURCE = "spotlight"
EXTEND_DAYS = 7
SELECT_CAP = 25
NO_CHANNEL = "no_channel_configured"
NOT_VISIBLE = "channel_not_visible"
TEST_MODE = "test_mode"


def _cell(row: Any, key: str) -> Any:
    if row is None:
        return None
    try:
        return row[key]
    except (IndexError, KeyError, TypeError):
        return getattr(row, key, None)


def wording_for(bot: Any, guild_id: int) -> dict[str, Any]:
    """The three range words, read once so one panel render asks the store three times."""
    return {
        "template": bot.store.get(guild_id, SPOTLIGHT_RANGE_KEY),
        "kept_template": bot.store.get(guild_id, SPOTLIGHT_RANGE_KEPT_KEY),
        "word": bot.store.get(guild_id, SPOTLIGHT_SCHEDULED_WORD_KEY),
    }


async def zone_for(bot: Any, guild: Any, actor: Any) -> str:
    """A typed date is read in the person's own zone, falling back to the guild's."""
    fallback = bot.store.get(guild.id, DEFAULT_TIMEZONE_KEY)
    wanted = getattr(actor, "id", actor)
    try:
        return await get_timezone(bot.db, int(wanted), fallback)
    except (TypeError, ValueError):
        return str(fallback or "")


async def add_channel(
    db: Any,
    guild_id: int,
    login: str,
    *,
    added_by: int | None,
    expires_at: str | None,
    pin: bool,
    starts_at: str | None = None,
    bump_hours: int | None = None,
    display_name: str | None = None,
    note: str | None = None,
    event_id: int | None = None,
    twitch_user_id: str | None = None,
    spotlight: bool = True,
    announce: bool = True,
    youtube_channel_id: str | None = None,
    youtube_handle: str | None = None,
) -> int | None:
    try:
        cur = await db.conn.execute(
            "INSERT INTO spotlight_channels(guild_id, twitch_login, twitch_user_id, "
            "display_name, note, added_by, added_at, starts_at, expires_at, bump_hours, pin, "
            "event_id, spotlight, announce, youtube_channel_id, youtube_handle) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                guild_id,
                login,
                twitch_user_id,
                display_name,
                note,
                added_by,
                now_iso(),
                starts_at,
                expires_at,
                bump_hours,
                1 if pin else 0,
                event_id,
                1 if spotlight else 0,
                1 if announce else 0,
                youtube_channel_id,
                youtube_handle,
            ),
        )
    except sqlite3.IntegrityError:
        return None
    await db.conn.commit()
    return cur.lastrowid


async def channels_for(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM spotlight_channels WHERE guild_id = ? ORDER BY twitch_login",
        (guild_id,),
    )
    return list(await cur.fetchall())


async def channel_by_id(db: Any, spotlight_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM spotlight_channels WHERE id = ?", (int(spotlight_id),)
    )
    return await cur.fetchone()


async def channel_by_login(db: Any, guild_id: int, login: str) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM spotlight_channels WHERE guild_id = ? AND twitch_login = ?",
        (guild_id, login),
    )
    return await cur.fetchone()


async def channel_for_event(db: Any, guild_id: int, event_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM spotlight_channels WHERE guild_id = ? AND event_id = ? LIMIT 1",
        (guild_id, int(event_id)),
    )
    return await cur.fetchone()


async def channels_with_youtube(db: Any) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM spotlight_channels WHERE youtube_channel_id IS NOT NULL "
        "AND youtube_channel_id <> '' ORDER BY guild_id, id"
    )
    return list(await cur.fetchall())


async def update_channel(db: Any, spotlight_id: int, **fields: Any) -> None:
    allowed = (
        "starts_at",
        "expires_at",
        "bump_hours",
        "pin",
        "note",
        "display_name",
        "twitch_user_id",
        "spotlight",
        "announce",
        "youtube_channel_id",
        "youtube_handle",
    )
    wanted = [(name, fields[name]) for name in allowed if name in fields]
    if not wanted:
        return
    sets = ", ".join(f"{name} = ?" for name, _ in wanted)
    await db.conn.execute(
        f"UPDATE spotlight_channels SET {sets} WHERE id = ?",
        tuple(value for _, value in wanted) + (int(spotlight_id),),
    )
    await db.conn.commit()


async def discard_session(db: Any, session_id: int) -> None:
    await db.conn.execute("DELETE FROM spotlight_sessions WHERE id = ?", (int(session_id),))
    await db.conn.commit()


async def delete_channel(db: Any, spotlight_id: int) -> bool:
    cur = await db.conn.execute(
        "DELETE FROM spotlight_channels WHERE id = ?", (int(spotlight_id),)
    )
    await db.conn.commit()
    return cur.rowcount > 0


async def start_session(
    db: Any, guild_id: int, spotlight_id: int, info: Any, mode: str
) -> int | None:
    try:
        cur = await db.conn.execute(
            "INSERT INTO spotlight_sessions(guild_id, spotlight_id, started_at, title, game, "
            "url, mode) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (guild_id, int(spotlight_id), now_iso(), info.title, info.game, info.url, mode),
        )
    except sqlite3.IntegrityError:
        log.info("spotlight: a session for %s is already open", spotlight_id)
        return None
    await db.conn.commit()
    return cur.lastrowid


async def refresh_session_info(db: Any, session_id: int, game: Any, title: Any) -> None:
    await db.conn.execute(
        "UPDATE spotlight_sessions SET game = COALESCE(?, game), title = COALESCE(?, title) "
        "WHERE id = ?",
        (game or None, title or None, int(session_id)),
    )
    await db.conn.commit()


async def open_session(db: Any, spotlight_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM spotlight_sessions WHERE spotlight_id = ? AND ended_at IS NULL "
        "ORDER BY id DESC LIMIT 1",
        (int(spotlight_id),),
    )
    return await cur.fetchone()


async def open_sessions(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM spotlight_sessions WHERE guild_id = ? AND ended_at IS NULL ORDER BY id",
        (guild_id,),
    )
    return list(await cur.fetchall())


async def last_session(db: Any, spotlight_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM spotlight_sessions WHERE spotlight_id = ? ORDER BY id DESC LIMIT 1",
        (int(spotlight_id),),
    )
    return await cur.fetchone()


async def recent_sessions(db: Any, guild_id: int, limit: int = 50) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM spotlight_sessions WHERE guild_id = ? ORDER BY id DESC LIMIT ?",
        (guild_id, int(limit)),
    )
    return list(await cur.fetchall())


async def end_session(db: Any, session_id: int, at: str) -> None:
    await db.conn.execute(
        "UPDATE spotlight_sessions SET ended_at = ? WHERE id = ? AND ended_at IS NULL",
        (at, int(session_id)),
    )
    await db.conn.commit()


async def set_announced(db: Any, session_id: int, message_id: int) -> None:
    await db.conn.execute(
        "UPDATE spotlight_sessions SET announced_message_id = ? WHERE id = ?",
        (int(message_id), int(session_id)),
    )
    await db.conn.commit()


async def note_bump(db: Any, session_id: int, message_id: Any, at: str) -> None:
    await db.conn.execute(
        "UPDATE spotlight_sessions SET last_bump_at = ?, bump_count = bump_count + 1 "
        "WHERE id = ?",
        (at, int(session_id)),
    )
    if message_id:
        await db.conn.execute(
            "INSERT OR IGNORE INTO spotlight_bumps(session_id, message_id, at) VALUES (?, ?, ?)",
            (int(session_id), int(message_id), at),
        )
    await db.conn.commit()


async def bumps_of(db: Any, session_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM spotlight_bumps WHERE session_id = ? ORDER BY at, message_id",
        (int(session_id),),
    )
    return list(await cur.fetchall())


async def forget_bumps(db: Any, session_id: int) -> None:
    await db.conn.execute(
        "DELETE FROM spotlight_bumps WHERE session_id = ?", (int(session_id),)
    )
    await db.conn.commit()


def cog_of(bot: Any) -> Any:
    getter = getattr(bot, "get_cog", None)
    return getter(COG_NAME) if callable(getter) else None


class Spotlight(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._locks: dict[int, asyncio.Lock] = {}
        self._reconciler = Reconciler()
        self.misses: dict[int, int] = {}
        self.scheduled: set[int] = set()
        self.last_poll_ok_at: str | None = None
        self.last_poll_error: str | None = None

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name != "poller":
            return (None, None)
        return (self.last_poll_ok_at, self.last_poll_error)

    async def cog_load(self) -> None:
        if not self.bot.db.is_connected:
            return
        await self._reconciler.run(self.reconcile_open_sessions, stamp=bool(self._guilds()))
        self.poller.start()

    async def cog_unload(self) -> None:
        self.poller.cancel()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self.bot.db.is_connected:
            return
        await self._reconciler.run(self.reconcile_open_sessions, skip_if_recent=True)

    def _guilds(self) -> list[Any]:
        return [
            guild
            for guild in list(getattr(self.bot, "guilds", ()) or ())
            if not getattr(guild, "unavailable", False)
        ]

    async def reconcile_open_sessions(self) -> None:
        """Checklist 37: the state is read inside the lock, so two boots close one session once."""
        for guild in self._guilds():
            for session in await open_sessions(self.bot.db, guild.id):
                row = await channel_by_id(self.bot.db, session["spotlight_id"])
                if row is not None and await self._message(guild, session) is not None:
                    continue
                await end_session(self.bot.db, session["id"], now_iso())
                await log_action(
                    self.bot,
                    guild,
                    "golive.spotlight_reconciled",
                    details={
                        "session_id": session["id"],
                        "spotlight_id": session["spotlight_id"],
                        "login": _cell(row, "twitch_login"),
                        "reason": words.RECONCILED,
                    },
                )

    # --- the sweep -------------------------------------------------------------------------

    @tasks.loop(minutes=SPOTLIGHT_POLL_MINUTES)
    async def poller(self) -> None:
        try:
            await self.poll_once()
        except Exception as exc:
            self.last_poll_error = words.reason_of(exc)
            log.exception("spotlight: the sweep failed")
        self._retime()

    @poller.before_loop
    async def _before_poller(self) -> None:
        if await wait_ready(self.bot, self._poller_stopped):
            self._retime()

    @poller.error
    async def _poller_stopped(self, exc: BaseException) -> None:
        """The loop stops for the life of the process unless it is started again."""
        self.last_poll_error = words.reason_of(exc)
        log.error("spotlight: the sweep stopped; restarting it", exc_info=exc)
        self.poller.restart()

    def _retime(self) -> None:
        wanted = self._poll_minutes()
        if self.poller.minutes != wanted:
            self.poller.change_interval(minutes=wanted)

    def _poll_minutes(self) -> int:
        guild = next(iter(getattr(self.bot, "guilds", ()) or ()), None)
        if guild is None:
            return SPOTLIGHT_POLL_MINUTES
        return max(1, int(self.bot.store.get(guild.id, SPOTLIGHT_POLL_MINUTES_KEY)))

    async def poll_once(self) -> None:
        """One batched Helix call for the whole list, plus the expiry sweep on the same tick."""
        if not self.bot.db.is_connected:
            return
        for guild in list(getattr(self.bot, "guilds", ())):
            if self._mode(guild.id) == MODE_OFF:
                continue
            await self.sweep_expiries(guild)
            rows = await channels_for(self.bot.db, guild.id)
            await self.sweep_starts(guild, rows)
            if not rows:
                continue
            helix = self._helix()
            if helix is None:
                self.last_poll_error = words.NO_KEY
                continue
            try:
                streams = await helix.get_streams([row["twitch_login"] for row in rows])
            except TwitchError as exc:
                self.last_poll_error = str(exc)
                log.warning("spotlight: could not ask Twitch about the list — %s", exc)
                continue
            self.last_poll_ok_at = now_iso()
            self.last_poll_error = None
            live = {stream.user_login: stream for stream in streams}
            for row in rows:
                await self._seen(guild, row, live.get(row["twitch_login"]))

    async def sweep_starts(self, guild: Any, rows: list[Any]) -> None:
        """One row per start that PASSES while this process is up; a boot notes nothing."""
        for row in rows:
            spotlight_id = int(row["id"])
            if words.is_scheduled(row):
                self.scheduled.add(spotlight_id)
                continue
            if spotlight_id not in self.scheduled:
                continue
            self.scheduled.discard(spotlight_id)
            await log_action(
                self.bot,
                guild,
                "golive.spotlight_started",
                details={
                    "spotlight_id": spotlight_id,
                    "login": row["twitch_login"],
                    "starts_at": _cell(row, "starts_at"),
                    "expires_at": row["expires_at"],
                },
            )

    async def sweep_expiries(self, guild: Any) -> None:
        """A row whose date has passed ends its open session first, then leaves the list."""
        for row in await channels_for(self.bot.db, guild.id):
            if not words.is_spotlit(row) or not words.is_expired(row):
                continue
            async with self._lock(row["id"]):
                fresh = await channel_by_id(self.bot.db, row["id"])
                if fresh is None or not words.is_expired(fresh):
                    continue
                await self._expire(guild, fresh, words.EXPIRED)

    async def _expire(self, guild: Any, row: Any, because: str) -> None:
        session = await open_session(self.bot.db, row["id"])
        if session is not None:
            await self._end(guild, row, session, words.EXPIRED)
        await drop_fan_role(self.bot, guild, row, because=words.FAN_ROLE_EXPIRED)
        await delete_channel(self.bot.db, row["id"])
        self.misses.pop(int(row["id"]), None)
        self.scheduled.discard(int(row["id"]))
        await log_action(
            self.bot,
            guild,
            "golive.spotlight_expired",
            details={
                "spotlight_id": row["id"],
                "login": row["twitch_login"],
                "expires_at": row["expires_at"],
                "event_id": row["event_id"],
                "because": because,
            },
        )

    async def _seen(self, guild: Any, row: Any, stream: Any) -> None:
        async with self._lock(row["id"]):
            fresh = await channel_by_id(self.bot.db, row["id"])
            if fresh is None:
                return
            session = await open_session(self.bot.db, fresh["id"])
            # A start still ahead gates the ANNOUNCEMENT only: a session already open runs
            # to its own end, so a date set mid-stream never strands a live post.
            if session is None and words.is_scheduled(fresh):
                return
            if stream is not None:
                self.misses[int(fresh["id"])] = 0
                if session is None:
                    await self._announce(guild, fresh, stream)
                else:
                    await self._maybe_bump(guild, fresh, session, from_twitch(stream))
                return
            if session is None or words.platform_of(_cell(session, "url")) != words.PLATFORM:
                return
            seen = self.misses.get(int(fresh["id"]), 0) + 1
            self.misses[int(fresh["id"])] = seen
            if seen < self._end_misses(guild.id):
                return
            await self._end(guild, fresh, session, words.ENDED)

    # --- the three posts -------------------------------------------------------------------

    async def _announce(self, guild: Any, row: Any, stream: Any) -> None:
        info = await self._box_art(guild, from_twitch(stream))
        name = str(getattr(stream, "user_name", "") or "").strip() or words.display_for(row)
        if name != words.display_for(row):
            await update_channel(self.bot.db, row["id"], display_name=name)
        await self.announce_info(guild, row, info, name)

    async def announce_info(self, guild: Any, row: Any, info: Any, name: str) -> None:
        """The one announcement, whichever sweep saw it: spotlight only decides the pin.
        An opted-out channel stops here — no session, so no end and no reminders either."""
        if not words.announces(row):
            return
        mode = self._mode(guild.id)
        session_id = await start_session(self.bot.db, guild.id, row["id"], info, mode)
        if session_id is None:
            return
        store = self.bot.store
        fan_role_id = await pings.announced_spotlight_fan_role(self.bot, guild, row["id"])
        text = render(
            store.get(guild.id, TEMPLATE_KEY),
            info,
            ping_role_id=store.get(guild.id, PING_KEY),
            fan_role_id=fan_role_id,
            name=name,
        )
        embed = (
            announcement_embed(
                info,
                source=SOURCE,
                name=name,
                author=store.get(guild.id, LIVE_AUTHOR_KEY),
            )
            if store.get(guild.id, EMBED_KEY)
            else None
        )
        message, reason = await self._post(guild, text, embed, mode, fan_role_id=fan_role_id)
        details = {
            "spotlight_id": row["id"],
            "session_id": session_id,
            "login": row["twitch_login"],
            "mode": mode,
            "url": info.url,
            "game": info.game,
            "title": info.title,
            "text": text,
            "pin": bool(row["pin"]) and words.is_spotlit(row),
            "spotlight": words.is_spotlit(row),
            "announce": words.announces(row),
            "platform": info.platform,
            "fan_role_id": fan_role_id,
        }
        if embed is not None:
            details["embed"] = embed_summary(embed)
        if message is None:
            await log_action(
                self.bot,
                guild,
                "golive.spotlight_post_failed",
                details=details | {"reason": reason},
            )
            await discard_session(self.bot.db, session_id)
            return
        await set_announced(self.bot.db, session_id, message.id)
        details["message_id"] = str(message.id)
        details["channel_id"] = str(getattr(getattr(message, "channel", None), "id", "") or "")
        await log_action(
            self.bot,
            guild,
            (
                (
                    "golive.spotlight_announced"
                    if mode == MODE_ON
                    else "golive.would_spotlight_announce"
                )
                if words.is_spotlit(row)
                else (
                    "golive.channel_announced"
                    if mode == MODE_ON
                    else "golive.would_channel_announce"
                )
            ),
            details=details,
        )
        if row["pin"] and words.is_spotlit(row):
            await self._pin(guild, row, message)

    async def _maybe_bump(self, guild: Any, row: Any, session: Any, info: Any) -> None:
        if not words.is_spotlit(row) or not words.announces(row):
            return
        hours = words.bump_hours_for(row, self.bot.store.get(guild.id, SPOTLIGHT_BUMP_HOURS_KEY))
        if not words.bump_due(session, hours).due:
            return
        await self.bump(guild, row, session, info)

    async def bump(
        self,
        guild: Any,
        row: Any,
        session: Any,
        info: Any = None,
        *,
        via: str = VIA_DISCORD,
        actor: Any = None,
    ) -> Any:
        """One short reminder, never pinned; it pings only while `spotlight_bump_pings` is on."""
        stream = info if info is not None else await self._current(row, session)
        refreshed = await self._refresh(session, stream)
        stream = await self._box_art(guild, stream)
        at = now_iso()
        pinging = bool(self.bot.store.get(guild.id, SPOTLIGHT_BUMP_PINGS_KEY))
        fan_role_id = (
            await pings.announced_spotlight_fan_role(self.bot, guild, row["id"], notice=False)
            if pinging
            else None
        )
        prefix = (
            ping_prefix(self.bot.store.get(guild.id, PING_KEY), fan_role_id) if pinging else ""
        )
        text = prefix + words.bump_render(
            self.bot.store.get(guild.id, SPOTLIGHT_BUMP_TEMPLATE_KEY),
            stream,
            words.display_for(row),
            words.bump_duration(session, at),
        )
        store = self.bot.store
        embed = (
            announcement_embed(
                stream,
                source=SOURCE,
                name=words.display_for(row),
                author=store.get(guild.id, LIVE_AUTHOR_KEY),
            )
            if store.get(guild.id, EMBED_KEY)
            else None
        )
        message, reason = await self._post(
            guild,
            text,
            embed,
            self._mode(guild.id),
            fan_role_id=fan_role_id,
            pinging=pinging,
        )
        said = {"game": stream.game, "title": stream.title, "refreshed": refreshed}
        if embed is not None:
            said["embed"] = embed_summary(embed)
        if message is None:
            await log_action(
                self.bot,
                guild,
                "golive.spotlight_post_failed",
                details={
                    "spotlight_id": row["id"],
                    "session_id": session["id"],
                    "login": row["twitch_login"],
                    "what": "bump",
                    "text": text,
                    "reason": reason,
                }
                | said,
            )
            return None
        await note_bump(self.bot.db, session["id"], message.id, at)
        await log_action(
            self.bot,
            guild,
            kind_via("golive.spotlight_bumped", via),
            actor=actor,
            details={
                "spotlight_id": row["id"],
                "session_id": session["id"],
                "login": row["twitch_login"],
                "mode": self._mode(guild.id),
                "text": text,
                "message_id": str(message.id),
                "bump": int(_cell(session, "bump_count") or 0) + 1,
                "pinged": pinging,
                "fan_role_id": fan_role_id,
                "via": via,
            }
            | said,
        )
        return message

    async def _current(self, row: Any, session: Any) -> Any:
        """What the channel streams NOW; the announce-time words when Helix cannot say."""
        stored = words.info_of(session, row["twitch_login"])
        helix = self._helix()
        if helix is None or stored.platform != words.PLATFORM:
            return stored
        try:
            streams = await helix.get_streams([row["twitch_login"]])
        except TwitchError as exc:
            log.warning(
                "spotlight: bump for %s used the stored game (%s)", row["twitch_login"], exc
            )
            return stored
        return from_twitch(streams[0]) if streams else stored

    async def _refresh(self, session: Any, info: Any) -> bool:
        changed = (info.game and info.game != _cell(session, "game")) or (
            info.title and info.title != _cell(session, "title")
        )
        if changed:
            await refresh_session_info(self.bot.db, session["id"], info.game, info.title)
        return bool(changed)

    async def _end(
        self, guild: Any, row: Any, session: Any, reason: str, *, post: str = CHANNEL_OPTOUT_END
    ) -> None:
        """The caller holds the row's lock; the state moves before any message does."""
        ended_at = now_iso()
        await end_session(self.bot.db, session["id"], ended_at)
        self.misses.pop(int(row["id"]), None)
        await log_action(
            self.bot,
            guild,
            "golive.spotlight_ended" if words.is_spotlit(row) else "golive.channel_ended",
            details={
                "spotlight_id": row["id"],
                "session_id": session["id"],
                "login": row["twitch_login"],
                "reason": reason,
                "post": post,
                "bumps": int(_cell(session, "bump_count") or 0),
                "spotlight": words.is_spotlit(row),
                "announce": words.announces(row),
            },
        )
        message = await self._message(guild, session)
        if post == CHANNEL_OPTOUT_DELETE:
            await self._delete_post(guild, row, session, message)
        else:
            await self._unpin(guild, row, message, because=reason)
            if post == CHANNEL_OPTOUT_END:
                await self._mark_ended(guild, row, session, message, ended_at)
        if self.bot.store.get(guild.id, SPOTLIGHT_BUMP_CLEANUP_KEY):
            await self._clear_bumps(guild, session)

    async def _delete_post(self, guild: Any, row: Any, session: Any, message: Any) -> None:
        """Deleting takes the pin with it, so there is nothing left to unpin afterwards."""
        if message is None:
            return
        try:
            await message.delete()
        except Exception as exc:
            reason = words.reason_of(exc)
            log.warning("spotlight: could not delete %s — %s", row["twitch_login"], reason)
            await log_action(
                self.bot,
                guild,
                "golive.spotlight_post_failed",
                details={
                    "spotlight_id": row["id"],
                    "session_id": session["id"],
                    "login": row["twitch_login"],
                    "what": "delete",
                    "message_id": str(getattr(message, "id", "")),
                    "reason": reason,
                },
            )
            return
        await log_action(
            self.bot,
            guild,
            "golive.spotlight_post_deleted",
            details={
                "spotlight_id": row["id"],
                "session_id": session["id"],
                "login": row["twitch_login"],
                "message_id": str(getattr(message, "id", "")),
            },
        )

    async def _mark_ended(
        self,
        guild: Any,
        row: Any,
        session: Any,
        message: Any,
        ended_at: str,
    ) -> None:
        if message is None:
            return
        store = self.bot.store
        template = store.get(guild.id, END_TEMPLATE_KEY)
        name = words.display_for(row)
        duration = humanise_duration(session["started_at"], ended_at)
        info = words.info_of(session, row["twitch_login"])
        existing = list(getattr(message, "embeds", None) or ())
        try:
            await message.edit(
                content=ended_render(
                    template,
                    info,
                    name,
                    content=message.content,
                    duration=duration,
                ),
                allowed_mentions=self._mentions(guild.id),
                **(
                    {
                        "embed": ended_embed(
                            existing[0],
                            name,
                            info.platform,
                            template,
                            author=store.get(guild.id, END_AUTHOR_KEY),
                            duration=duration,
                        )
                    }
                    if existing
                    else {}
                ),
            )
        except Exception as exc:
            log.info(
                "spotlight: could not mark message %s as ended (%s)",
                _cell(session, "announced_message_id"),
                words.reason_of(exc),
            )

    async def _clear_bumps(self, guild: Any, session: Any) -> None:
        channel = await self._channel_of(guild, session)
        for bump in await bumps_of(self.bot.db, session["id"]):
            if channel is None:
                continue
            try:
                found = await channel.fetch_message(int(bump["message_id"]))
                await found.delete()
            except Exception as exc:
                log.info(
                    "spotlight: a reminder under session %s stays — %s",
                    session["id"],
                    words.reason_of(exc),
                )
        await forget_bumps(self.bot.db, session["id"])

    # --- pinning ---------------------------------------------------------------------------

    async def _pin(
        self, guild: Any, row: Any, message: Any, *, because: str | None = None
    ) -> str | None:
        """Checklist 12: the session is already recorded; a pin that fails changes nothing."""
        if message is None or bool(getattr(message, "pinned", False)):
            return None
        said = {"because": because} if because else {}
        try:
            await message.pin(reason=words.PIN_REASON)
        except Exception as exc:
            reason = words.reason_of(exc)
            log.warning("spotlight: could not pin %s — %s", row["twitch_login"], reason)
            await log_action(
                self.bot,
                guild,
                "golive.spotlight_pin_failed",
                details={
                    "spotlight_id": row["id"],
                    "login": row["twitch_login"],
                    "message_id": str(getattr(message, "id", "")),
                    "reason": reason,
                }
                | said,
            )
            return words.PIN_REFUSED.format(login=row["twitch_login"], reason=reason)
        await log_action(
            self.bot,
            guild,
            "golive.spotlight_pinned",
            details={
                "spotlight_id": row["id"],
                "login": row["twitch_login"],
                "message_id": str(message.id),
            }
            | said,
        )
        return None

    async def _unpin(
        self, guild: Any, row: Any, message: Any, *, because: str | None = None
    ) -> str | None:
        """Checklist 3: the pin comes off because the MESSAGE carries one, not because the key
        still says pin — a mid-stream flip must not strand it."""
        if message is None or not bool(getattr(message, "pinned", False)):
            return None
        said = {"because": because} if because else {}
        try:
            await message.unpin(reason=words.UNPIN_REASON)
        except Exception as exc:
            reason = words.reason_of(exc)
            log.warning("spotlight: could not unpin %s — %s", row["twitch_login"], reason)
            await log_action(
                self.bot,
                guild,
                "golive.spotlight_unpin_failed",
                details={
                    "spotlight_id": row["id"],
                    "login": row["twitch_login"],
                    "message_id": str(getattr(message, "id", "")),
                    "reason": reason,
                }
                | said,
            )
            return words.UNPIN_REFUSED.format(login=row["twitch_login"], reason=reason)
        await log_action(
            self.bot,
            guild,
            "golive.spotlight_unpinned",
            details={
                "spotlight_id": row["id"],
                "login": row["twitch_login"],
                "message_id": str(message.id),
            }
            | said,
        )
        return None

    # --- where the posts go ------------------------------------------------------------------

    async def _post(
        self,
        guild: Any,
        text: str,
        embed: Any,
        mode: str,
        *,
        fan_role_id: int | None = None,
        pinging: bool = True,
    ) -> tuple[Any, str | None]:
        """`on` posts in the go-live channel; `shadow` rehearses where shadow_channel_id says."""
        channel_id = self.bot.store.get(guild.id, CHANNEL_KEY)
        if not channel_id:
            log.warning("spotlight: not posted — %s is not set", CHANNEL_KEY)
            return (None, NO_CHANNEL)
        said = ""
        if mode != MODE_ON:
            where = shadow_home.channel_id(self.bot, guild)
            if not where:
                return (None, NO_CHANNEL)
            said = shadow_home.note_line(self.bot, guild, f"<#{int(channel_id)}>")
            channel_id = where
        guard = getattr(self.bot, "guard", None)
        if guard is not None and not guard.allows_channel(channel_id):
            log.warning("spotlight: TEST MODE — refused to post to channel %s", channel_id)
            return (None, TEST_MODE)
        channel = shadow_home.channel_of(self.bot, guild, channel_id)
        if channel is None:
            log.warning("spotlight: not posted — channel %s is not visible", channel_id)
            return (None, NOT_VISIBLE)
        try:
            message = await channel.send(
                f"{said}\n{text}" if said else text,
                allowed_mentions=self._mentions(
                    guild.id, fan_role_id, pinging=pinging
                ),
                **({"embed": embed} if embed is not None else {}),
            )
        except Exception as exc:
            reason = words.reason_of(exc)
            log.warning("spotlight: not posted — %s", reason)
            return (None, reason)
        return (message, None)

    async def _channel_of(self, guild: Any, session: Any) -> Any:
        mode = str(_cell(session, "mode") or MODE_ON)
        channel_id = (
            self.bot.store.get(guild.id, CHANNEL_KEY)
            if mode == MODE_ON
            else shadow_home.channel_id(self.bot, guild)
        )
        return shadow_home.channel_of(self.bot, guild, channel_id)

    async def _message(self, guild: Any, session: Any) -> Any:
        message_id = _cell(session, "announced_message_id")
        if not message_id:
            return None
        channel = await self._channel_of(guild, session)
        if channel is None:
            return None
        try:
            return await channel.fetch_message(int(message_id))
        except Exception as exc:
            log.info(
                "spotlight: could not read message %s — %s", message_id, words.reason_of(exc)
            )
            return None

    async def _box_art(self, guild: Any, info: Any) -> Any:
        helix = self._helix()
        if helix is None or info.box_art_url or not info.game_id:
            return info
        if not self.bot.store.get(guild.id, EMBED_KEY):
            return info
        try:
            games = await helix.get_games([info.game_id])
        except TwitchError as exc:
            log.warning("spotlight: no box art for game %s (%s)", info.game_id, exc)
            return info
        return with_box_art(info, games[0]) if games else info

    # --- the small stuff ---------------------------------------------------------------------

    def _helix(self) -> Any:
        """The go-live cog's client, so one app token and one session serve both sweeps."""
        getter = getattr(self.bot, "get_cog", None)
        cog = getter(GOLIVE_COG) if callable(getter) else None
        return getattr(cog, "helix", None)

    def _lock(self, spotlight_id: Any) -> asyncio.Lock:
        key = int(spotlight_id)
        lock = self._locks.get(key)
        if lock is None:
            lock = self._locks[key] = asyncio.Lock()
        return lock

    def _mode(self, guild_id: int) -> str:
        return self.bot.store.get(guild_id, SPOTLIGHT_MODE_KEY)

    def _end_misses(self, guild_id: int) -> int:
        return max(1, int(self.bot.store.get(guild_id, SPOTLIGHT_END_MISSES_KEY)))

    def _mentions(
        self, guild_id: int, fan_role_id: int | None = None, *, pinging: bool = True
    ) -> discord.AllowedMentions:
        wanted = [
            int(role_id)
            for role_id in (self.bot.store.get(guild_id, PING_KEY), fan_role_id)
            if role_id and pinging
        ]
        return discord.AllowedMentions(
            everyone=False,
            users=False,
            roles=[discord.Object(role_id) for role_id in dict.fromkeys(wanted)] or False,
        )


# --- the shared moves, which the routes and the panel both come in by -------------------------


async def drop_fan_role(
    bot: Any,
    guild: Any,
    row: Any,
    *,
    because: str,
    actor: Any = None,
    via: str = VIA_DISCORD,
) -> Any:
    """A channel that leaves the list takes its ping role with it, the one `pings` way."""
    return await pings.remove_fan_role(
        bot,
        guild,
        by=getattr(actor, "id", actor),
        via=via,
        spotlight=row,
        because=because,
    )


async def give_fan_role(
    bot: Any, guild: Any, actor: Any, spotlight_id: int, *, role: Any = None, via: str = VIA_DISCORD
) -> tuple[Any, Any]:
    """Staff's door to a channel's own ping role: `(outcome, row)`, the row None when it is gone."""
    row = await channel_by_id(bot.db, spotlight_id)
    if row is None or int(row["guild_id"]) != int(guild.id):
        return (None, None)
    outcome = await pings.ensure_fan_role(
        bot,
        guild,
        None,
        by=getattr(actor, "id", actor),
        existing_role=role,
        staff=True,
        via=via,
        spotlight=row,
    )
    return (outcome, row)


async def take_fan_role(
    bot: Any, guild: Any, actor: Any, spotlight_id: int, *, via: str = VIA_DISCORD
) -> tuple[Any, Any]:
    """Staff always get the final say: the move that reverses `give_fan_role`."""
    row = await channel_by_id(bot.db, spotlight_id)
    if row is None or int(row["guild_id"]) != int(guild.id):
        return (None, None)
    outcome = await drop_fan_role(
        bot, guild, row, because=words.FAN_ROLE_TAKEN, actor=actor, via=via
    )
    return (outcome, row)


async def spotlight_channel(
    bot: Any,
    guild: Any,
    actor: Any,
    login: str,
    *,
    days: Any = None,
    keep: bool = False,
    pin: Any = None,
    bump_hours: int | None = None,
    note: str | None = None,
    event_id: int | None = None,
    expires_at: Any = False,
    starts_at: Any = None,
    spotlight: Any = None,
    announce: bool = True,
    youtube_channel_id: str | None = None,
    youtube_handle: str | None = None,
    via: str = VIA_DISCORD,
) -> tuple[str, Any]:
    """One door for the panel, the route and the event card: `(outcome, row)`."""
    clean = words.clean_login(login)
    if clean is None:
        return ("bad_login", None)
    if await channel_by_login(bot.db, guild.id, clean) is not None:
        return ("already", None)
    store = bot.store
    spotlit = bool(
        store.get(guild.id, CHANNEL_SPOTLIGHT_DEFAULT_KEY) if spotlight is None else spotlight
    )
    when = (
        expires_at
        if expires_at is not False
        else (
            None
            if keep or not spotlit
            else words.expiry_in_days(
                days if days is not None else store.get(guild.id, SPOTLIGHT_DEFAULT_DAYS_KEY)
            )
        )
    )
    wanted_pin = bool(store.get(guild.id, SPOTLIGHT_PIN_KEY) if pin is None else pin)
    spotlight_id = await add_channel(
        bot.db,
        guild.id,
        clean,
        added_by=getattr(actor, "id", actor),
        expires_at=when,
        starts_at=starts_at or None,
        pin=wanted_pin,
        bump_hours=bump_hours,
        display_name=clean,
        note=note,
        event_id=event_id,
        spotlight=spotlit,
        announce=bool(announce),
        youtube_channel_id=youtube_channel_id,
        youtube_handle=youtube_handle,
    )
    if spotlight_id is None:
        return ("already", None)
    row = await channel_by_id(bot.db, spotlight_id)
    await log_action(
        bot,
        guild,
        kind_via("golive.spotlight_added", via),
        actor=actor,
        details={
            "spotlight_id": spotlight_id,
            "login": clean,
            "starts_at": starts_at or None,
            "expires_at": when,
            "pin": wanted_pin,
            "spotlight": spotlit,
            "announce": bool(announce),
            "youtube_channel_id": youtube_channel_id,
            "bump_hours": bump_hours,
            "event_id": event_id,
            "via": via,
        },
    )
    return ("added", row)


async def set_dates(
    bot: Any,
    guild: Any,
    actor: Any,
    spotlight_id: int,
    starts_at: Any,
    expires_at: Any,
    *,
    via: str = VIA_DISCORD,
) -> tuple[str, Any, str]:
    """One door for the modal, the drawer and the route: `(outcome, row, said)`.

    A blank start means now and a blank end means for ever, so both are stored as NULL.
    A start already gone by is stored as given — never silently rewritten, never refused.
    """
    row = await channel_by_id(bot.db, spotlight_id)
    if row is None or int(row["guild_id"]) != int(guild.id):
        return ("no_row", None, words.NO_SUCH_ROW)
    problem = words.range_problem(starts_at, expires_at)
    if problem is not None:
        said = words.end_before_start_said(
            starts_at, expires_at, bot.store.get(guild.id, SPOTLIGHT_END_BEFORE_START_KEY)
        )
        return (problem, row, said)
    fresh = await change_spotlight(
        bot,
        guild,
        actor,
        spotlight_id,
        via=via,
        starts_at=starts_at or None,
        expires_at=expires_at or None,
    )
    return ("dated", fresh, words.dates_said(fresh, **wording_for(bot, guild.id)))


async def read_dates(
    bot: Any, guild: Any, actor: Any, given_start: Any, given_end: Any
) -> tuple[Any, Any, str | None]:
    """`(starts_at, expires_at, refusal)` — the two boxes both doors type into."""
    tz_name = await zone_for(bot, guild, actor)
    start, trouble = words.read_moment(given_start, tz_name)
    if trouble is not None:
        return (None, None, _bad_date(bot, guild, given_start))
    end, trouble = words.read_end(given_end, tz_name)
    if trouble is not None:
        return (None, None, _bad_date(bot, guild, given_end))
    return (start, end, None)


def _bad_date(bot: Any, guild: Any, given: Any) -> str:
    return words.bad_date_said(given, bot.store.get(guild.id, SPOTLIGHT_BAD_DATE_KEY))


async def set_announce(
    bot: Any, guild: Any, actor: Any, spotlight_id: int, on: bool, *, via: str = VIA_DISCORD
) -> tuple[Any, str | None]:
    """A channel's own opt-out, the member opt-out's twin: the row, its role, its YouTube
    link and its spotlight all stay, and nothing of its is posted while it is off.
    Turning it off with a stream OPEN settles that announcement now — `(row, settled)`."""
    return await changed_spotlight(
        bot, guild, actor, spotlight_id, via=via, announce=1 if on else 0
    )


async def set_spotlight(
    bot: Any, guild: Any, actor: Any, spotlight_id: int, on: bool, *, via: str = VIA_DISCORD
) -> tuple[Any, str | None]:
    """The toggle: the row, its role and its sessions all stay; only the pin and the
    reminders come and go. Staff final say, both ways, at any time."""
    return await changed_spotlight(
        bot, guild, actor, spotlight_id, via=via, spotlight=1 if on else 0
    )


async def link_youtube(
    bot: Any, guild: Any, actor: Any, spotlight_id: int, given: Any, *, via: str = VIA_DISCORD
) -> tuple[str, Any, str]:
    """`(outcome, row, said)` — the resolver the member links go through, no key needed."""
    from .youtube import cog_of as youtube_cog_of

    row = await channel_by_id(bot.db, spotlight_id)
    if row is None or int(row["guild_id"]) != int(guild.id):
        return ("no_row", None, words.NO_SUCH_ROW)
    wanted = str(given or "").strip()
    if not wanted:
        return ("no_channel", row, words.NO_YOUTUBE_GIVEN)
    cog = youtube_cog_of(bot)
    client = getattr(cog, "client", None)
    if client is None:
        return ("no_cog", row, words.NO_YOUTUBE_COG.format(login=row["twitch_login"]))
    try:
        channel_id, title = await client.resolve(wanted)
    except Exception as exc:
        return ("bad_channel", row, str(exc))
    handle = _youtube_handle_of(wanted)
    fresh = await change_spotlight(
        bot,
        guild,
        actor,
        spotlight_id,
        via=via,
        youtube_channel_id=channel_id,
        youtube_handle=handle,
    )
    said = words.YOUTUBE_LINKED.format(
        login=row["twitch_login"], title=title or handle or channel_id
    )
    return ("linked", fresh, said)


async def unlink_youtube(
    bot: Any, guild: Any, actor: Any, spotlight_id: int, *, via: str = VIA_DISCORD
) -> tuple[str, Any, str]:
    row = await channel_by_id(bot.db, spotlight_id)
    if row is None or int(row["guild_id"]) != int(guild.id):
        return ("no_row", None, words.NO_SUCH_ROW)
    if not words.youtube_of(row):
        return ("not_linked", row, words.NO_YOUTUBE_LINKED.format(login=row["twitch_login"]))
    fresh = await change_spotlight(
        bot,
        guild,
        actor,
        spotlight_id,
        via=via,
        youtube_channel_id=None,
        youtube_handle=None,
    )
    return ("unlinked", fresh, words.YOUTUBE_UNLINKED.format(login=row["twitch_login"]))


def _youtube_handle_of(given: str) -> str | None:
    from ...youtube import channel_id_in, handle_in

    if channel_id_in(given):
        return None
    found = handle_in(given)
    return f"@{found}" if found else None


async def change_spotlight(
    bot: Any, guild: Any, actor: Any, spotlight_id: int, *, via: str = VIA_DISCORD, **fields: Any
) -> Any:
    fresh, _ = await changed_spotlight(bot, guild, actor, spotlight_id, via=via, **fields)
    return fresh


async def changed_spotlight(
    bot: Any, guild: Any, actor: Any, spotlight_id: int, *, via: str = VIA_DISCORD, **fields: Any
) -> tuple[Any, str | None]:
    """The one write both doors reach: `(the row after it, what an OPEN announcement had
    done to it)`. The row moves first, so a refusal from Discord never leaves it half-flipped."""
    row = await channel_by_id(bot.db, spotlight_id)
    if row is None or int(row["guild_id"]) != int(guild.id):
        return (None, None)
    await update_channel(bot.db, spotlight_id, **fields)
    fresh = await channel_by_id(bot.db, spotlight_id)
    await log_action(
        bot,
        guild,
        kind_via("golive.spotlight_updated", via),
        actor=actor,
        details={"spotlight_id": spotlight_id, "login": row["twitch_login"], "via": via}
        | {name: fields[name] for name in sorted(fields)},
    )
    return (fresh, await settle_open_session(bot, guild, row, fresh, fields))


async def settle_open_session(
    bot: Any, guild: Any, was: Any, now: Any, fields: dict[str, Any]
) -> str | None:
    """Opting a live channel out ENDS the stream that is out there; the spotlight flag moves
    only the pin. Nothing here waits on Twitch, which never reports a 24/7 rerun offline."""
    cog = cog_of(bot)
    if cog is None or now is None:
        return None
    opted_out = "announce" in fields and words.announces(was) and not words.announces(now)
    dimmed = "spotlight" in fields and words.is_spotlit(was) and not words.is_spotlit(now)
    brightened = "spotlight" in fields and not words.is_spotlit(was) and words.is_spotlit(now)
    if not (opted_out or dimmed or brightened):
        return None
    spotlight_id = int(now["id"])
    async with cog._lock(spotlight_id):
        session = await open_session(bot.db, spotlight_id)
        if brightened and not opted_out:
            return await _brighten(cog, bot, guild, now, session)
        if session is None:
            return None
        if opted_out:
            post = str(bot.store.get(guild.id, CHANNEL_OPTOUT_POST_KEY))
            await cog._end(guild, now, session, words.OPTED_OUT_ENDED, post=post)
            return post
        message = await cog._message(guild, session)
        await cog._unpin(guild, now, message, because=words.SPOTLIGHT_OFF_BECAUSE)
        return words.UNPINNED


async def _brighten(cog: Any, bot: Any, guild: Any, row: Any, session: Any) -> str | None:
    """Toggle time only: the poller never re-pins what staff unpinned by hand mid-stream."""
    because = words.SPOTLIGHT_ON_BECAUSE
    if session is not None:
        if not row["pin"] or not words.announces(row):
            return None
        message = await cog._message(guild, session)
        if message is None or bool(getattr(message, "pinned", False)):
            return None
        refused = await cog._pin(guild, row, message, because=because)
        return refused or words.PINNED
    last = await last_session(bot.db, int(row["id"]))
    if last is None:
        return None
    message = await cog._message(guild, last)
    if message is None or not bool(getattr(message, "pinned", False)):
        return None
    refused = await cog._unpin(guild, row, message, because=because)
    return refused or words.UNPINNED_ENDED


async def forget_spotlight(
    bot: Any, guild: Any, actor: Any, spotlight_id: int, *, via: str = VIA_DISCORD
) -> Any:
    """Staff final say: a row goes whatever state it is in, and its session is closed first."""
    cog = cog_of(bot)
    row = await channel_by_id(bot.db, spotlight_id)
    if row is None or int(row["guild_id"]) != int(guild.id):
        return None
    session = await open_session(bot.db, spotlight_id)
    if session is not None and cog is not None:
        async with cog._lock(spotlight_id):
            await cog._end(guild, row, session, words.REMOVED_BECAUSE)
    await drop_fan_role(bot, guild, row, because=words.FAN_ROLE_REMOVED, actor=actor, via=via)
    await delete_channel(bot.db, spotlight_id)
    if cog is not None:
        cog.misses.pop(int(spotlight_id), None)
        cog.scheduled.discard(int(spotlight_id))
    await log_action(
        bot,
        guild,
        kind_via("golive.spotlight_removed", via),
        actor=actor,
        details={
            "spotlight_id": spotlight_id,
            "login": row["twitch_login"],
            "event_id": row["event_id"],
            "via": via,
        },
    )
    return row


async def expire_for_event(bot: Any, guild: Any, event_id: int) -> Any:
    """A cancelled event takes its spotlight with it, at once rather than at its old end."""
    cog = cog_of(bot)
    row = await channel_for_event(bot.db, guild.id, event_id)
    if row is None or cog is None:
        return None
    async with cog._lock(row["id"]):
        fresh = await channel_by_id(bot.db, row["id"])
        if fresh is None:
            return None
        await cog._expire(guild, fresh, words.EVENT_CANCELLED_BECAUSE)
    return fresh


async def bump_now(
    bot: Any, guild: Any, actor: Any, spotlight_id: int, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    row = await channel_by_id(bot.db, spotlight_id)
    if row is None or int(row["guild_id"]) != int(guild.id):
        return ("no_row", None)
    session = await open_session(bot.db, spotlight_id)
    if session is None:
        return ("not_live", row)
    cog = cog_of(bot)
    if cog is None:
        return ("no_cog", row)
    async with cog._lock(spotlight_id):
        fresh = await open_session(bot.db, spotlight_id)
        if fresh is None:
            return ("not_live", row)
        message = await cog.bump(guild, row, fresh, via=via, actor=actor)
    return ("bumped" if message is not None else "bump_failed", row)


async def live_now(bot: Any, guild: Any) -> dict[int, Any]:
    return {
        int(session["spotlight_id"]): session
        for session in await open_sessions(bot.db, guild.id)
    }


# --- the /golive sub-panel --------------------------------------------------------------------


def minutes_for(bot: Any, guild_id: int) -> int:
    from ...golive import panel_minutes

    return panel_minutes(bot.store, guild_id)


class SpotlightPanel(Panel):
    def __init__(self, minutes: int) -> None:
        from ...golive import PANEL_TIMEOUT_FOOTER

        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER)


def mode_lines(bot: Any, guild: Any) -> list[str]:
    said: list[str] = []
    mode = bot.store.get(guild.id, SPOTLIGHT_MODE_KEY)
    if mode == MODE_OFF:
        said.append(words.MODE_OFF)
    elif mode == MODE_SHADOW:
        said.append(words.MODE_SHADOW)
    cog = cog_of(bot)
    if cog is not None and cog._helix() is None:
        said.append(words.NO_KEY)
    if not bot.store.get(guild.id, CHANNEL_KEY):
        said.append(words.NO_CHANNEL)
    return said


async def build_spotlight(
    bot: Any, guild: Any, picked: Any = None
) -> tuple[discord.Embed, Any]:
    rows = await channels_for(bot.db, guild.id)
    open_by_id = await live_now(bot, guild)
    chosen = (
        next((row for row in rows if int(row["id"]) == int(picked)), None)
        if picked is not None
        else None
    )
    held = {
        pings.spotlight_of(one): one["role_id"]
        for one in await pings.spotlight_fan_roles(bot.db, guild.id)
    }
    said = wording_for(bot, guild.id)
    lines = [words.CHANNELS_INTRO] + mode_lines(bot, guild)
    lines += (
        [
            words.panel_line(
                row, int(row["id"]) in open_by_id, held.get(int(row["id"])), **said
            )
            for row in rows[:SELECT_CAP]
        ]
        if rows
        else [words.PANEL_EMPTY]
    )
    view = SpotlightPanel(minutes_for(bot, guild.id))
    if rows:
        view.add_item(ChannelPick(rows[:SELECT_CAP], chosen))
    if chosen is not None:
        live = int(chosen["id"]) in open_by_id
        held = await pings.get_spotlight_fan_role(bot.db, guild.id, chosen["id"])
        spotlit = words.is_spotlit(chosen)
        view.add_item(
            SpotlightMoveButton("spotlight_off" if spotlit else "spotlight_on", chosen["id"])
        )
        view.add_item(
            DatesButton(chosen["id"], bot.store.get(guild.id, SPOTLIGHT_DATES_BUTTON_KEY))
        )
        # Panels over slash: the kept / expires / bump moves belong to the spotlight, so they
        # render only while it is on, and Bump only while something is live to bump.
        if spotlit:
            if words.keeps_forever(chosen):
                view.add_item(SpotlightMoveButton("expire", chosen["id"]))
            else:
                view.add_item(SpotlightMoveButton("extend", chosen["id"]))
                view.add_item(SpotlightMoveButton("keep", chosen["id"]))
            if live and words.announces(chosen):
                view.add_item(SpotlightMoveButton("bump", chosen["id"]))
        view.add_item(
            SpotlightMoveButton(
                "opt_in" if not words.announces(chosen) else "opt_out", chosen["id"]
            )
        )
        view.add_item(SpotlightMoveButton("take_role" if held is not None else "give_role",
                                         chosen["id"]))
        if words.youtube_of(chosen):
            view.add_item(SpotlightMoveButton("unlink_youtube", chosen["id"]))
        else:
            view.add_item(LinkYouTubeButton(chosen["id"]))
        view.add_item(SpotlightMoveButton("remove", chosen["id"]))
    view.add_item(AddChannelButton())
    view.add_item(SpotlightBackButton())
    embed = discord.Embed(title=words.CHANNELS_TITLE, description="\n".join(lines))
    return embed, view


async def render_spotlight(
    interaction: discord.Interaction, picked: Any = None, previous: Any = None
) -> None:
    embed, view = await build_spotlight(interaction.client, interaction.guild, picked)
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


class ChannelPick(discord.ui.Select):
    def __init__(self, rows: list[Any], chosen: Any = None) -> None:
        super().__init__(
            placeholder=words.PICK_A_CHANNEL,
            options=[
                discord.SelectOption(
                    label=f"{row['twitch_login']} — {words.range_words(row)}"[:100],
                    value=str(row["id"]),
                    default=chosen is not None and int(row["id"]) == int(chosen["id"]),
                )
                for row in rows
            ],
            min_values=1,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        if not await opened(interaction, staff=False):
            return
        await render_spotlight(interaction, int(self.values[0]), self.view)


class SpotlightMoveButton(discord.ui.Button):
    LABELS = {
        "extend": words.EXTEND_WEEK,
        "keep": words.KEEP_FOREVER,
        "expire": "Let it expire",
        "bump": words.BUMP_NOW,
        "spotlight_on": words.SPOTLIGHT_ON,
        "spotlight_off": words.SPOTLIGHT_OFF,
        "opt_out": words.OPT_OUT,
        "opt_in": words.OPT_IN,
        "unlink_youtube": words.UNLINK_YOUTUBE,
        "give_role": words.GIVE_PING_ROLE,
        "take_role": words.TAKE_PING_ROLE,
        "remove": words.REMOVE,
    }
    STYLES = {
        "extend": discord.ButtonStyle.primary,
        "keep": discord.ButtonStyle.success,
        "expire": discord.ButtonStyle.secondary,
        "bump": discord.ButtonStyle.primary,
        "spotlight_on": discord.ButtonStyle.success,
        "spotlight_off": discord.ButtonStyle.secondary,
        "opt_out": discord.ButtonStyle.secondary,
        "opt_in": discord.ButtonStyle.success,
        "unlink_youtube": discord.ButtonStyle.secondary,
        "give_role": discord.ButtonStyle.success,
        "take_role": discord.ButtonStyle.secondary,
        "remove": discord.ButtonStyle.danger,
    }
    ROWS = {
        "opt_out": 2,
        "opt_in": 2,
        "give_role": 2,
        "take_role": 2,
        "unlink_youtube": 2,
        "remove": 2,
    }

    def __init__(self, action: str, spotlight_id: Any) -> None:
        super().__init__(
            label=self.LABELS[action],
            style=self.STYLES[action],
            row=self.ROWS.get(action, 1),
        )
        self.action = action
        self.spotlight_id = int(spotlight_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        if not await opened(interaction, staff=False):
            return
        said, keep_picked = await run_spotlight_move(
            interaction.client,
            interaction.guild,
            interaction.user,
            self.spotlight_id,
            self.action,
        )
        await render_spotlight(
            interaction, self.spotlight_id if keep_picked else None, self.view
        )
        await answer(interaction, said)


async def run_spotlight_move(
    bot: Any, guild: Any, actor: Any, spotlight_id: int, action: str
) -> tuple[str, bool]:
    row = await channel_by_id(bot.db, spotlight_id)
    if row is None or int(row["guild_id"]) != int(guild.id):
        return (words.NO_SUCH_ROW, False)
    login = row["twitch_login"]
    if action == "remove":
        await forget_spotlight(bot, guild, actor, spotlight_id)
        return (words.REMOVED.format(login=login), False)
    if action == "keep":
        await change_spotlight(bot, guild, actor, spotlight_id, expires_at=None)
        return (words.KEPT_SAID.format(login=login), True)
    if action == "expire":
        when = words.expiry_in_days(bot.store.get(guild.id, SPOTLIGHT_DEFAULT_DAYS_KEY))
        outcome, fresh, said = await set_dates(
            bot, guild, actor, spotlight_id, _cell(row, "starts_at"), when
        )
        if outcome != "dated":
            return (said, True)
        return (words.EXPIRES_SAID.format(login=login, when=words.when_words(when)), True)
    if action in ("spotlight_on", "spotlight_off"):
        fresh, settled = await set_spotlight(
            bot, guild, actor, spotlight_id, action == "spotlight_on"
        )
        return (words.spotlight_said(fresh, settled), True)
    if action in ("opt_out", "opt_in"):
        fresh, settled = await set_announce(
            bot, guild, actor, spotlight_id, action == "opt_in"
        )
        return (words.announce_said(fresh, settled), True)
    if action == "unlink_youtube":
        _, _, said = await unlink_youtube(bot, guild, actor, spotlight_id)
        return (said, True)
    if action in ("give_role", "take_role"):
        move = give_fan_role if action == "give_role" else take_fan_role
        outcome, _ = await move(bot, guild, actor, spotlight_id)
        if outcome is None:
            return (words.NO_SUCH_ROW, False)
        return (outcome.message, True)
    if action == "bump":
        outcome, _ = await bump_now(bot, guild, actor, spotlight_id)
        if outcome == "bumped":
            return (words.BUMPED_SAID.format(login=login), True)
        if outcome == "not_live":
            return (words.NOT_LIVE.format(login=login), True)
        if outcome == "no_cog":
            return (words.NO_COG.format(login=login), True)
        return (words.BUMP_FAILED.format(login=login, reason=words.NO_CHANNEL), True)
    outcome, fresh, said = await set_dates(
        bot,
        guild,
        actor,
        spotlight_id,
        _cell(row, "starts_at"),
        words.extended_by_days(row, EXTEND_DAYS),
    )
    if outcome != "dated":
        return (said, True)
    return (words.EXTENDED.format(login=login, when=words.range_words(fresh)), True)


class AddChannelButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label=words.ADD_BUTTON, style=discord.ButtonStyle.primary, row=3
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.send_modal(
            AddChannelModal(self.view, interaction.client, interaction.guild)
        )


class DatesButton(discord.ui.Button):
    def __init__(self, spotlight_id: Any, label: Any = None) -> None:
        super().__init__(
            label=words.dates_button(label), style=discord.ButtonStyle.secondary, row=1
        )
        self.spotlight_id = int(spotlight_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        bot = interaction.client
        row = await channel_by_id(bot.db, self.spotlight_id)
        if row is None:
            await answer(interaction, words.NO_SUCH_ROW)
            return
        tz_name = await zone_for(bot, interaction.guild, interaction.user)
        await interaction.response.send_modal(
            DatesModal(
                self.spotlight_id,
                words.starts_label(bot.store.get(interaction.guild.id, SPOTLIGHT_STARTS_LABEL_KEY)),
                words.ends_label(bot.store.get(interaction.guild.id, SPOTLIGHT_ENDS_LABEL_KEY)),
                words.typed_moment(_cell(row, "starts_at"), tz_name),
                words.typed_moment(row["expires_at"], tz_name),
                self.view,
            )
        )


class DatesModal(AnswersErrors, discord.ui.Modal, title=words.DATES_MODAL_TITLE):
    def __init__(
        self,
        spotlight_id: int,
        starts_label: str,
        ends_label: str,
        starts: str,
        ends: str,
        previous: Any = None,
    ) -> None:
        super().__init__()
        self.spotlight_id = int(spotlight_id)
        self.previous = previous
        self.starts = discord.ui.TextInput(
            label=starts_label,
            placeholder=words.STARTS_PLACEHOLDER,
            default=starts or None,
            required=False,
            max_length=20,
        )
        self.ends = discord.ui.TextInput(
            label=ends_label,
            placeholder=words.ENDS_PLACEHOLDER,
            default=ends or None,
            required=False,
            max_length=20,
        )
        self.add_item(self.starts)
        self.add_item(self.ends)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction, staff=False):
            return
        bot = interaction.client
        start, end, refusal = await read_dates(
            bot, interaction.guild, interaction.user, str(self.starts), str(self.ends)
        )
        if refusal is None:
            _, _, refusal = await set_dates(
                bot,
                interaction.guild,
                interaction.user,
                self.spotlight_id,
                start,
                end,
            )
        await render_spotlight(interaction, self.spotlight_id, self.previous)
        await answer(interaction, refusal)


class LinkYouTubeButton(discord.ui.Button):
    def __init__(self, spotlight_id: Any) -> None:
        super().__init__(
            label=words.LINK_YOUTUBE, style=discord.ButtonStyle.primary, row=2
        )
        self.spotlight_id = int(spotlight_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.send_modal(
            LinkYouTubeModal(self.spotlight_id, self.view)
        )


class LinkYouTubeModal(AnswersErrors, discord.ui.Modal, title=words.LINK_YOUTUBE):
    channel = discord.ui.TextInput(
        label=words.ADD_YOUTUBE_LABEL,
        placeholder=words.ADD_YOUTUBE_PLACEHOLDER,
        max_length=120,
    )

    def __init__(self, spotlight_id: int, previous: Any = None) -> None:
        super().__init__()
        self.spotlight_id = int(spotlight_id)
        self.previous = previous

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction, staff=False):
            return
        _, _, said = await link_youtube(
            interaction.client,
            interaction.guild,
            interaction.user,
            self.spotlight_id,
            str(self.channel),
        )
        await render_spotlight(interaction, self.spotlight_id, self.previous)
        await answer(interaction, said)


class AddChannelModal(AnswersErrors, discord.ui.Modal, title=words.ADD_CHANNEL_MODAL_TITLE):
    channel = discord.ui.TextInput(
        label=words.ADD_LOGIN_LABEL,
        placeholder=words.ADD_LOGIN_PLACEHOLDER,
        max_length=words.LOGIN_MAX,
    )
    spotlight = discord.ui.TextInput(
        label=words.ADD_SPOTLIGHT_LABEL,
        placeholder=words.ADD_SPOTLIGHT_PLACEHOLDER,
        required=False,
        max_length=5,
    )
    youtube = discord.ui.TextInput(
        label=words.ADD_YOUTUBE_LABEL,
        placeholder=words.ADD_YOUTUBE_PLACEHOLDER,
        required=False,
        max_length=120,
    )
    def __init__(self, previous: Any = None, bot: Any = None, guild: Any = None) -> None:
        super().__init__()
        self.previous = previous
        store = getattr(bot, "store", None)
        guild_id = getattr(guild, "id", None)
        start_label = store.get(guild_id, SPOTLIGHT_STARTS_LABEL_KEY) if store else None
        end_label = store.get(guild_id, SPOTLIGHT_ENDS_LABEL_KEY) if store else None
        self.starts = discord.ui.TextInput(
            label=words.starts_label(start_label),
            placeholder=words.STARTS_PLACEHOLDER,
            required=False,
            max_length=20,
        )
        self.ends = discord.ui.TextInput(
            label=words.ends_label(end_label),
            placeholder=words.ENDS_PLACEHOLDER,
            required=False,
            max_length=20,
        )
        self.add_item(self.starts)
        self.add_item(self.ends)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction, staff=False):
            return
        bot = interaction.client
        given = str(self.channel)
        start, end, refusal = await read_dates(
            bot, interaction.guild, interaction.user, str(self.starts), str(self.ends)
        )
        if refusal is None and words.range_problem(start, end) is not None:
            refusal = words.end_before_start_said(
                start, end, bot.store.get(interaction.guild.id, SPOTLIGHT_END_BEFORE_START_KEY)
            )
        if refusal is not None:
            await render_spotlight(interaction, None, self.previous)
            await answer(interaction, refusal)
            return
        asked = str(self.spotlight).strip()
        wanted = words.wanted_spotlight(
            asked, bool(bot.store.get(interaction.guild.id, CHANNEL_SPOTLIGHT_DEFAULT_KEY))
        )
        if wanted is None:
            await render_spotlight(interaction, None, self.previous)
            await answer(
                interaction, words.BAD_SPOTLIGHT_ANSWER.format(given=asked[:40])
            )
            return
        outcome, row = await spotlight_channel(
            bot,
            interaction.guild,
            interaction.user,
            given,
            expires_at=end,
            starts_at=start,
            spotlight=wanted,
        )
        said = add_said(bot, interaction.guild, outcome, row, given)
        wanted_youtube = str(self.youtube).strip()
        if row is not None and wanted_youtube:
            _, fresh, linked = await link_youtube(
                bot, interaction.guild, interaction.user, row["id"], wanted_youtube
            )
            row = fresh if fresh is not None else row
            said = f"{said} {linked}"
        await render_spotlight(
            interaction, row["id"] if row is not None else None, self.previous
        )
        await answer(interaction, said)


def add_said(bot: Any, guild: Any, outcome: str, row: Any, given: Any) -> str:
    if outcome == "bad_login":
        return words.BAD_LOGIN.format(given=str(given or "nothing")[:40])
    if outcome == "already":
        return words.ALREADY_SPOTLIT.format(
            login=words.clean_login(given) or str(given or "")[: words.LOGIN_MAX]
        )
    return words.added_said(
        row,
        words.bump_hours_for(row, bot.store.get(guild.id, SPOTLIGHT_BUMP_HOURS_KEY)),
        **wording_for(bot, guild.id),
    )


class SpotlightBackButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Back", style=discord.ButtonStyle.secondary, row=3)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction, staff=False):
            return
        from .golive import render_panel

        await render_panel(interaction, self.view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Spotlight(bot))
