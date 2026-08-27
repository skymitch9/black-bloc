from __future__ import annotations

import asyncio
import logging
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ...actionlog import log_action
from ...golive import (
    END_GRACE_SECONDS,
    POLL_SECONDS,
    TWITCH,
    YOUTUBE,
    StreamInfo,
    announcement_embed,
    edits_on_end,
    embed_summary,
    end_details,
    ended_embed,
    ended_text,
    enriched,
    extract_stream,
    from_twitch,
    now_iso,
    parse_ts,
    passes_role_filters,
    render,
    should_announce,
    twitch_enrichable,
    twitch_login_from_url,
    with_box_art,
)
from ...settings_store import DB_UNAVAILABLE, GOLIVE_MODES, require_staff
from ...twitch import TwitchClient, TwitchError

log = logging.getLogger(__name__)

TWITCH_OFF = (
    "go-live: Twitch enrichment is off (TWITCH_CLIENT_ID/TWITCH_CLIENT_SECRET are not set); "
    "detection runs on Discord presence alone"
)
OPTED_OUT = (
    "Done — Black Bloc will not announce your streams. Run `/golive optin` if you change "
    "your mind."
)
OPTED_IN = (
    "Done — Black Bloc will announce your streams again when it sees you go live. "
    "`/golive optout` turns it back off."
)
NOT_OPTED_OUT = (
    "You were not opted out, so nothing changed — Black Bloc already announces your streams."
)
BAD_LOGIN = (
    "That does not look like a Twitch channel name, so nothing was linked. Use the channel name "
    "from your channel address (the part after twitch.tv/), for example `blackbloc`."
)
NOT_LINKED = (
    "You had no Twitch channel linked, so nothing changed. Link one with `/twitch link "
    "<your twitch channel name>`."
)
LINK_NOT_CHECKED = (
    "Linked **{channel}** to you, but Twitch could not be reached to check that the channel name "
    "exists, so it has not been verified. If announcements do not fill in your game and title, "
    "run `/twitch link` again later to re-check it."
)
LINK_TAKEN = (
    "**{channel}** is already linked to another member here, so nothing was changed. A Twitch "
    "channel name can only belong to one member — if that channel is yours, ask a Lead to remove "
    "the other link first."
)
PLATFORM_UNKNOWN = "an unknown platform"
TEST_STREAMS = {
    TWITCH: StreamInfo(
        url="https://www.twitch.tv/blackbloc",
        game="Just Chatting",
        title="a test stream",
        platform=TWITCH,
        game_id="509658",
        box_art_url="https://static-cdn.jtvnw.net/ttv-boxart/509658-285x380.jpg",
    ),
    YOUTUBE: StreamInfo(
        url="https://www.youtube.com/watch?v=blackblocbaf",
        game="a test game",
        title="a test stream",
        platform=YOUTUBE,
        thumbnail_url="https://i.ytimg.com/vi/aqz-KE-bpKQ/hqdefault.jpg",
    ),
}


def _row_value(row: Any, key: str) -> Any:
    if row is None:
        return None
    try:
        return row[key]
    except (IndexError, KeyError):
        return None


@dataclass(frozen=True)
class PostResult:
    message: Any = None
    reason: str | None = None

    @property
    def ok(self) -> bool:
        return self.message is not None


async def set_link(db: Any, user_id: int, login: str, twitch_user_id: str | None = None) -> None:
    await db.conn.execute(
        "INSERT OR REPLACE INTO golive_links(user_id, twitch_login, twitch_user_id, linked_at) "
        "VALUES (?, ?, ?, ?)",
        (user_id, login, twitch_user_id, now_iso()),
    )
    await db.conn.commit()


async def get_link(db: Any, user_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM golive_links WHERE user_id = ?", (user_id,))
    return await cur.fetchone()


async def all_links(db: Any) -> list[Any]:
    cur = await db.conn.execute("SELECT * FROM golive_links ORDER BY twitch_login")
    return list(await cur.fetchall())


async def link_owner(db: Any, login: str) -> int | None:
    cur = await db.conn.execute(
        "SELECT user_id FROM golive_links WHERE twitch_login = ? ORDER BY user_id LIMIT 1",
        (login,),
    )
    row = await cur.fetchone()
    return int(row["user_id"]) if row else None


async def remove_link(db: Any, user_id: int) -> bool:
    cur = await db.conn.execute("DELETE FROM golive_links WHERE user_id = ?", (user_id,))
    await db.conn.commit()
    return cur.rowcount > 0


async def set_optout(db: Any, user_id: int) -> None:
    await db.conn.execute(
        "INSERT OR REPLACE INTO golive_optout(user_id, at) VALUES (?, ?)", (user_id, now_iso())
    )
    await db.conn.commit()


async def clear_optout(db: Any, user_id: int) -> bool:
    cur = await db.conn.execute("DELETE FROM golive_optout WHERE user_id = ?", (user_id,))
    await db.conn.commit()
    return cur.rowcount > 0


async def all_optouts(db: Any) -> list[Any]:
    cur = await db.conn.execute("SELECT * FROM golive_optout ORDER BY at DESC")
    return list(await cur.fetchall())


async def is_opted_out(db: Any, user_id: int) -> bool:
    cur = await db.conn.execute("SELECT 1 FROM golive_optout WHERE user_id = ?", (user_id,))
    return await cur.fetchone() is not None


async def start_session(
    db: Any, guild_id: int, user_id: int, source: str, info: StreamInfo, mode: str
) -> int | None:
    try:
        cur = await db.conn.execute(
            "INSERT INTO golive_sessions(guild_id, user_id, source, url, game, title, platform, "
            "started_at, mode) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                guild_id,
                user_id,
                source,
                info.url,
                info.game,
                info.title,
                info.platform,
                now_iso(),
                mode,
            ),
        )
    except sqlite3.IntegrityError:
        log.info("go-live: a session for %s is already open; not starting a second", user_id)
        return None
    await db.conn.commit()
    return cur.lastrowid


async def discard_session(db: Any, session_id: int) -> None:
    await db.conn.execute("DELETE FROM golive_sessions WHERE id = ?", (session_id,))
    await db.conn.commit()


async def set_live_role_added(db: Any, session_id: int) -> None:
    await db.conn.execute(
        "UPDATE golive_sessions SET live_role_added = 1 WHERE id = ?", (session_id,)
    )
    await db.conn.commit()


async def latest_session(db: Any, guild_id: int, user_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM golive_sessions WHERE guild_id = ? AND user_id = ? ORDER BY id DESC LIMIT 1",
        (guild_id, user_id),
    )
    return await cur.fetchone()


async def open_session_for(
    db: Any, guild_id: int, user_id: int, source: str | None = None
) -> Any:
    sql = "SELECT * FROM golive_sessions WHERE guild_id = ? AND user_id = ? AND ended_at IS NULL"
    params: tuple[Any, ...] = (guild_id, user_id)
    if source is not None:
        sql += " AND source = ?"
        params += (source,)
    cur = await db.conn.execute(sql + " ORDER BY id DESC LIMIT 1", params)
    return await cur.fetchone()


async def open_sessions(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM golive_sessions WHERE guild_id = ? AND ended_at IS NULL ORDER BY id",
        (guild_id,),
    )
    return list(await cur.fetchall())


async def recent_sessions(db: Any, guild_id: int, limit: int = 50) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM golive_sessions WHERE guild_id = ? ORDER BY id DESC LIMIT ?",
        (guild_id, int(limit)),
    )
    return list(await cur.fetchall())


async def end_session(db: Any, session_id: int, at: str) -> None:
    await db.conn.execute(
        "UPDATE golive_sessions SET ended_at = ? WHERE id = ? AND ended_at IS NULL",
        (at, session_id),
    )
    await db.conn.commit()


async def set_announced(db: Any, session_id: int, message_id: int) -> None:
    await db.conn.execute(
        "UPDATE golive_sessions SET announced_message_id = ? WHERE id = ?", (message_id, session_id)
    )
    await db.conn.commit()


async def counts(db: Any, guild_id: int) -> dict[str, int]:
    async def scalar(sql: str, params: tuple[Any, ...] = ()) -> int:
        cur = await db.conn.execute(sql, params)
        row = await cur.fetchone()
        return int(row["n"]) if row else 0

    return {
        "links": await scalar("SELECT COUNT(*) AS n FROM golive_links"),
        "optouts": await scalar("SELECT COUNT(*) AS n FROM golive_optout"),
        "open_sessions": await scalar(
            "SELECT COUNT(*) AS n FROM golive_sessions WHERE guild_id = ? AND ended_at IS NULL",
            (guild_id,),
        ),
    }


def clean_login(raw: str) -> str | None:
    login = twitch_login_from_url(raw) or raw.strip().lower().lstrip("@")
    if not login or len(login) > 25:
        return None
    if not all(ch.isalnum() or ch == "_" for ch in login):
        return None
    return login


class GoLive(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.helix: TwitchClient | None = None
        self._end_tasks: dict[int, asyncio.Task] = {}
        self._locks: dict[int, asyncio.Lock] = {}
        self.last_poll_ok_at: str | None = None
        self.last_poll_error: str | None = None

    golive = app_commands.Group(name="golive", description="Go-live announcements")
    twitch = app_commands.Group(name="twitch", description="Link your Twitch channel")

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name != "poller":
            return (None, None)
        return (self.last_poll_ok_at, self.last_poll_error)

    async def cog_load(self) -> None:
        settings = self.bot.settings
        if settings.twitch_configured:
            self.helix = TwitchClient(settings.twitch_client_id, settings.twitch_client_secret)
        else:
            log.info(TWITCH_OFF)
        if not self.bot.db.is_connected:
            return
        await self.reconcile_open_sessions()
        if self.helix is not None:
            self.poller.start()

    async def reconcile_open_sessions(self) -> None:
        """Close every session a stop left open, keeping the ones still genuinely live."""
        for guild in list(getattr(self.bot, "guilds", ())):
            for row in await open_sessions(self.bot.db, guild.id):
                if await self._still_live(guild, row):
                    continue
                await self._close_session(guild, row, "reconciled_on_start")

    async def _still_live(self, guild: Any, row: Any) -> bool:
        member = guild.get_member(row["user_id"])
        if member is not None and extract_stream(getattr(member, "activities", ())) is not None:
            return True
        if row["source"] != "twitch" or self.helix is None:
            return False
        login = _row_value(await get_link(self.bot.db, row["user_id"]), "twitch_login")
        login = login or twitch_login_from_url(row["url"])
        if not login:
            return False
        try:
            return bool(await self.helix.get_streams([login]))
        except TwitchError as exc:
            log.warning(
                "go-live: could not check whether %s is still live (%s); leaving the session open",
                login,
                exc,
            )
            return True

    async def _close_session(self, guild: Any, row: Any, reason: str) -> None:
        member = guild.get_member(row["user_id"])
        end_mode = self._end_mode(guild.id)
        await end_session(self.bot.db, row["id"], now_iso())
        await self._remove_live_role(guild, member, row)
        await log_action(
            self.bot,
            guild,
            "golive.end",
            target=member if member is not None else row["user_id"],
            details={"session_id": row["id"], "source": row["source"], "reason": reason}
            | end_details(end_mode),
        )
        await self._mark_ended(guild, row, end_mode)

    async def cog_unload(self) -> None:
        self.poller.cancel()
        for task in self._end_tasks.values():
            task.cancel()
        self._end_tasks.clear()
        if self.helix is not None:
            await self.helix.close()

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member) -> None:
        if after.bot or after.guild is None:
            return
        was = extract_stream(getattr(before, "activities", ()))
        now_live = extract_stream(after.activities)
        if now_live is not None:
            self._cancel_end(after.id)
            if was is None:
                await self._go_live(after, now_live, "presence")
        elif was is not None:
            self._schedule_end(after)

    async def _go_live(self, member: Any, info: StreamInfo, source: str) -> None:
        async with self._lock(member.id):
            await self._go_live_once(member, info, source)

    async def _go_live_once(self, member: Any, info: StreamInfo, source: str) -> None:
        guild = member.guild
        mode = self._mode(guild.id)
        if mode == "off" or member.bot or not self.bot.db.is_connected:
            return
        if await is_opted_out(self.bot.db, member.id):
            return
        store = self.bot.store
        if not passes_role_filters(
            [role.id for role in member.roles],
            store.get(guild.id, "golive_require_role_id"),
            store.get(guild.id, "golive_ignore_role_id"),
        ):
            return
        last = await latest_session(self.bot.db, guild.id, member.id)
        cooldown = store.get(guild.id, "golive_cooldown_minutes")
        if not should_announce(datetime.now(UTC), last, cooldown):
            return
        if source == "presence":
            info = await self._enrich(member, info)
        info = await self._box_art(guild, info)
        session_id = await start_session(self.bot.db, guild.id, member.id, source, info, mode)
        if session_id is None:
            return
        text = render(
            store.get(guild.id, "golive_template"),
            info,
            member,
            ping_role_id=store.get(guild.id, "golive_ping_role_id"),
        )
        embed = self._embed(guild, info, member, source)
        result = (
            await self._post(guild, text, embed) if mode == "on" else PostResult(reason="shadow")
        )
        if result.ok:
            await set_announced(self.bot.db, session_id, result.message.id)
        details = {
            "source": source,
            "mode": mode,
            "session_id": session_id,
            "url": info.url,
            "game": info.game,
            "platform": info.platform,
            "text": text,
        }
        if embed is not None:
            details["embed"] = embed_summary(embed)
        if not result.ok and result.reason not in ("shadow", "test_mode"):
            await log_action(
                self.bot,
                guild,
                "golive.post_failed",
                target=member,
                details=details | {"reason": result.reason},
            )
            await discard_session(self.bot.db, session_id)
            return
        await log_action(
            self.bot,
            guild,
            "golive.announce" if result.ok else "golive.would_announce",
            target=member,
            details=details,
        )
        if await self._live_role(guild, member, add=True):
            await set_live_role_added(self.bot.db, session_id)

    async def _end_live(self, guild: Any, member: Any, source: str | None) -> None:
        if not self.bot.db.is_connected:
            return
        row = await open_session_for(self.bot.db, guild.id, member.id, source)
        if row is None:
            return
        end_mode = self._end_mode(guild.id)
        await end_session(self.bot.db, row["id"], now_iso())
        await self._remove_live_role(guild, member, row)
        await log_action(
            self.bot,
            guild,
            "golive.end",
            target=member,
            details={"session_id": row["id"], "source": row["source"]} | end_details(end_mode),
        )
        await self._mark_ended(guild, row, end_mode)

    async def _mark_ended(self, guild: Any, row: Any, end_mode: str) -> None:
        message_id = row["announced_message_id"]
        if not edits_on_end(end_mode) or not message_id:
            return
        channel = self._channel(guild)
        if channel is None:
            return
        suffix = self.bot.store.get(guild.id, "golive_end_suffix")
        try:
            message = await channel.fetch_message(message_id)
            await message.edit(
                content=ended_text(message.content, suffix),
                allowed_mentions=self._mentions(guild.id),
                **self._ended_embed(guild, row, message, suffix),
            )
        except Exception as exc:
            log.info(
                "go-live: could not mark message %s as ended (%s: %s)",
                message_id,
                type(exc).__name__,
                exc,
            )

    def _embed(self, guild: Any, info: StreamInfo, member: Any, source: str) -> Any:
        if not self.bot.store.get(guild.id, "golive_embed"):
            return None
        return announcement_embed(info, member, source)

    def _ended_embed(
        self, guild: Any, row: Any, message: Any, suffix: str | None
    ) -> dict[str, Any]:
        existing = list(getattr(message, "embeds", None) or ())
        if not existing:
            return {}
        name = self._display_name(guild, row)
        return {"embed": ended_embed(existing[0], name, _row_value(row, "platform"), suffix)}

    async def _box_art(self, guild: Any, info: StreamInfo) -> StreamInfo:
        """Twitch knows the game's art; YouTube and presence-only streams are never asked."""
        if self.helix is None or info.box_art_url or not info.game_id:
            return info
        if not twitch_enrichable(info) or not self.bot.store.get(guild.id, "golive_embed"):
            return info
        try:
            games = await self.helix.get_games([info.game_id])
        except TwitchError as exc:
            log.warning(
                "go-live: no box art for game %s (%s); posting without it", info.game_id, exc
            )
            return info
        return with_box_art(info, games[0]) if games else info

    async def _enrich(self, member: Any, info: StreamInfo) -> StreamInfo:
        if self.helix is None or not twitch_enrichable(info) or (info.game and info.title):
            return info
        login = _row_value(await get_link(self.bot.db, member.id), "twitch_login")
        login = login or twitch_login_from_url(info.url)
        if not login:
            return info
        try:
            streams = await self.helix.get_streams([login])
        except TwitchError as exc:
            log.warning("go-live: Twitch lookup for %s failed: %s", login, exc)
            return info
        return enriched(info, streams[0] if streams else None)

    async def _post(self, guild: Any, text: str, embed: Any = None) -> PostResult:
        channel_id = self.bot.store.get(guild.id, "golive_channel_id")
        if not channel_id:
            log.warning("go-live: not posted — golive_channel_id is not set")
            return PostResult(reason="no_channel_configured")
        guard = getattr(self.bot, "guard", None)
        if guard is not None and not guard.allows_channel(channel_id):
            log.warning("go-live: TEST MODE — refused to post to channel %s", channel_id)
            return PostResult(reason="test_mode")
        channel = self._channel(guild)
        if channel is None:
            log.warning("go-live: not posted — channel %s is not visible", channel_id)
            return PostResult(reason="channel_not_visible")
        try:
            message = await channel.send(
                text,
                allowed_mentions=self._mentions(guild.id),
                **({"embed": embed} if embed is not None else {}),
            )
        except Exception as exc:
            log.warning("go-live: not posted — %s: %s", type(exc).__name__, exc)
            return PostResult(reason=f"{type(exc).__name__}: {exc}")
        return PostResult(message=message)

    async def _live_role(self, guild: Any, member: Any, *, add: bool) -> bool:
        role_id = self.bot.store.get(guild.id, "golive_live_role_id")
        if not role_id:
            return False
        role = guild.get_role(role_id)
        if role is None:
            log.warning("go-live: live role %s is not in this server", role_id)
            return False
        if not self._may_change_roles(guild.id):
            log.info(
                "go-live: would %s the live role %s for %s",
                "add" if add else "remove",
                role_id,
                member.id,
            )
            await log_action(
                self.bot,
                guild,
                "golive.would_add_role" if add else "golive.would_remove_role",
                target=member,
                details={"role_id": role_id},
            )
            return False
        try:
            if add:
                await member.add_roles(role, reason="Black Bloc go-live")
            else:
                await member.remove_roles(role, reason="Black Bloc go-live")
        except discord.HTTPException as exc:
            log.warning("go-live: could not change the live role for %s: %s", member.id, exc)
            return False
        await log_action(
            self.bot,
            guild,
            "golive.add_role" if add else "golive.remove_role",
            target=member,
            details={"role_id": role_id},
        )
        return True

    async def _remove_live_role(self, guild: Any, member: Any, row: Any) -> None:
        if not _row_value(row, "live_role_added"):
            return
        role_id = self.bot.store.get(guild.id, "golive_live_role_id")
        role = guild.get_role(role_id) if role_id else None
        stuck = None
        if role is None:
            stuck = "role_missing"
        elif member is None:
            stuck = "member_not_visible"
        elif getattr(self.bot, "guard", None) is not None:
            stuck = "test_mode"
        if stuck is None:
            try:
                await member.remove_roles(role, reason="Black Bloc go-live ended")
            except discord.HTTPException as exc:
                stuck = f"{type(exc).__name__}: {exc}"
        if stuck is None:
            await log_action(
                self.bot,
                guild,
                "golive.remove_role",
                target=member,
                details={"role_id": role_id},
            )
            return
        log.warning(
            "go-live: the live role %s is stuck on %s (%s)", role_id, row["user_id"], stuck
        )
        await log_action(
            self.bot,
            guild,
            "golive.role_stuck",
            target=member if member is not None else row["user_id"],
            details={"role_id": role_id, "user_id": row["user_id"], "reason": stuck},
        )

    def _mentions(self, guild_id: int) -> discord.AllowedMentions:
        ping_role_id = self.bot.store.get(guild_id, "golive_ping_role_id")
        return discord.AllowedMentions(
            everyone=False,
            users=False,
            roles=[discord.Object(ping_role_id)] if ping_role_id else False,
        )

    def _lock(self, user_id: int) -> asyncio.Lock:
        lock = self._locks.get(user_id)
        if lock is None:
            lock = self._locks[user_id] = asyncio.Lock()
        return lock

    def _mode(self, guild_id: int) -> str:
        return self.bot.store.get(guild_id, "golive_mode")

    def _end_mode(self, guild_id: int) -> str:
        return self.bot.store.get(guild_id, "golive_end_mode")

    def _may_change_roles(self, guild_id: int) -> bool:
        return self._mode(guild_id) == "on" and getattr(self.bot, "guard", None) is None

    def _channel(self, guild: Any) -> Any:
        channel_id = self.bot.store.get(guild.id, "golive_channel_id")
        if not channel_id:
            return None
        return self.bot.get_channel(channel_id) or guild.get_channel(channel_id)

    def _display_name(self, guild: Any, row: Any) -> str:
        member = guild.get_member(row["user_id"])
        return str(getattr(member, "display_name", None) or row["user_id"])

    def _find_member(self, user_id: int) -> Any:
        for guild in self.bot.guilds:
            member = guild.get_member(user_id)
            if member is not None:
                return member
        return None

    def _cancel_end(self, user_id: int) -> None:
        task = self._end_tasks.pop(user_id, None)
        if task is not None:
            task.cancel()

    def _schedule_end(self, member: Any) -> None:
        self._cancel_end(member.id)
        self._end_tasks[member.id] = asyncio.create_task(
            self._end_after_grace(member), name=f"golive-end-{member.id}"
        )

    async def _end_after_grace(self, member: Any) -> None:
        try:
            await asyncio.sleep(END_GRACE_SECONDS)
            await self._end_live(member.guild, member, "presence")
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("go-live: could not end the session for %s", member.id)
        finally:
            if self._end_tasks.get(member.id) is asyncio.current_task():
                self._end_tasks.pop(member.id, None)

    @tasks.loop(seconds=POLL_SECONDS)
    async def poller(self) -> None:
        try:
            await self.poll_once()
        except Exception as exc:
            self.last_poll_error = f"{type(exc).__name__}: {exc}"
            log.exception("go-live: the Twitch poll failed")

    @poller.before_loop
    async def _before_poller(self) -> None:
        await self.bot.wait_until_ready()

    async def age_out_sessions(self) -> None:
        """Close sessions still open long past any plausible stream, so nobody wedges."""
        for guild in list(getattr(self.bot, "guilds", ())):
            hours = self.bot.store.get(guild.id, "golive_max_session_hours")
            if not hours:
                continue
            cutoff = datetime.now(UTC) - timedelta(hours=int(hours))
            for row in await open_sessions(self.bot.db, guild.id):
                started = parse_ts(row["started_at"])
                if started is not None and started > cutoff:
                    continue
                log.warning(
                    "go-live: session %s has been open since %s; closing it",
                    row["id"],
                    row["started_at"],
                )
                await self._close_session(guild, row, "aged_out")

    async def poll_once(self) -> None:
        """One Twitch sweep: live logins with no open session go live, gone ones end."""
        if not self.bot.db.is_connected:
            return
        await self.age_out_sessions()
        if self.helix is None:
            return
        by_login: dict[str, int] = {}
        for row in await all_links(self.bot.db):
            login = row["twitch_login"]
            if login in by_login:
                log.warning(
                    "go-live: twitch login %s is linked to both %s and %s; only the first is "
                    "polled",
                    login,
                    by_login[login],
                    row["user_id"],
                )
                continue
            by_login[login] = row["user_id"]
        if not by_login:
            self.last_poll_ok_at = now_iso()
            self.last_poll_error = None
            return
        try:
            streams = await self.helix.get_streams(list(by_login))
        except TwitchError as exc:
            self.last_poll_error = str(exc)
            log.warning("go-live: Twitch poll failed: %s", exc)
            return
        self.last_poll_ok_at = now_iso()
        self.last_poll_error = None
        live = {stream.user_login: stream for stream in streams}
        for login, user_id in by_login.items():
            member = self._find_member(user_id)
            if member is None:
                continue
            guild_id = member.guild.id
            stream = live.get(login)
            if stream is not None:
                if await open_session_for(self.bot.db, guild_id, user_id) is None:
                    await self._go_live(member, from_twitch(stream), "twitch")
            elif await open_session_for(self.bot.db, guild_id, user_id, "twitch") is not None:
                await self._end_live(member.guild, member, "twitch")

    async def _database_ready(self, interaction: discord.Interaction) -> bool:
        if self.bot.db.is_connected:
            return True
        log.warning("go-live: refused a command — the database is not connected")
        await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
        return False

    @golive.command(name="optout", description="Stop Black Bloc announcing your streams")
    async def optout(self, interaction: discord.Interaction) -> None:
        if not await self._database_ready(interaction):
            return
        await set_optout(self.bot.db, interaction.user.id)
        await interaction.response.send_message(OPTED_OUT, ephemeral=True)
        await self._log_command(interaction, "golive.optout")

    @golive.command(name="optin", description="Let Black Bloc announce your streams again")
    async def optin(self, interaction: discord.Interaction) -> None:
        if not await self._database_ready(interaction):
            return
        cleared = await clear_optout(self.bot.db, interaction.user.id)
        await interaction.response.send_message(
            OPTED_IN if cleared else NOT_OPTED_OUT, ephemeral=True
        )
        if cleared:
            await self._log_command(interaction, "golive.optin")

    @golive.command(name="status", description="Show how the go-live feed is set up")
    async def status(self, interaction: discord.Interaction) -> None:
        if not await require_staff(interaction):
            return
        if not await self._database_ready(interaction):
            return
        guild = interaction.guild
        store = self.bot.store
        totals = await counts(self.bot.db, guild.id)
        channel_id = store.get(guild.id, "golive_channel_id")
        polling = "running" if self.poller.is_running() else (
            "off — no Twitch credentials" if self.helix is None else "stopped"
        )
        lines = [
            f"**mode** — {self._mode(guild.id)}",
            f"**channel** — {f'<#{channel_id}>' if channel_id else 'not set'}",
            f"**cooldown** — {store.get(guild.id, 'golive_cooldown_minutes')} minute(s)",
            f"**twitch polling** — {polling}",
            f"**last good poll** — {self.last_poll_ok_at or 'never'}",
            f"**last poll error** — {self.last_poll_error or 'none'}",
            f"**links** — {totals['links']} · **opt-outs** — {totals['optouts']} · "
            f"**live now** — {totals['open_sessions']}",
        ]
        lines += [
            f"• {self._display_name(guild, row)} on "
            f"{_row_value(row, 'platform') or PLATFORM_UNKNOWN}"
            for row in await open_sessions(self.bot.db, guild.id)
        ]
        await interaction.response.send_message(
            "\n".join(lines), ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @golive.command(name="mode", description="Turn go-live announcements off, shadow or on")
    @app_commands.describe(mode="off, shadow (log only) or on (post announcements)")
    @app_commands.choices(
        mode=[app_commands.Choice(name=name, value=name) for name in GOLIVE_MODES]
    )
    async def mode(
        self, interaction: discord.Interaction, mode: app_commands.Choice[str]
    ) -> None:
        if not await require_staff(interaction):
            return
        await self.bot.store.set(
            interaction.guild.id, "golive_mode", mode.value, by=interaction.user.id
        )
        await interaction.response.send_message(
            f"Go-live announcements are now **{mode.value}**.", ephemeral=True
        )
        await log_action(
            self.bot,
            interaction.guild,
            "golive.mode",
            actor=interaction.user,
            details={"mode": mode.value},
        )

    @golive.command(name="test", description="Show what a go-live announcement would look like")
    @app_commands.describe(platform="Pretend the stream is on this platform instead of your own")
    @app_commands.choices(
        platform=[app_commands.Choice(name=name, value=name) for name in TEST_STREAMS]
    )
    async def test(
        self,
        interaction: discord.Interaction,
        platform: app_commands.Choice[str] | None = None,
    ) -> None:
        if not await require_staff(interaction):
            return
        store = self.bot.store
        guild = interaction.guild
        info = (
            TEST_STREAMS[platform.value]
            if platform is not None
            else extract_stream(getattr(interaction.user, "activities", ()))
            or TEST_STREAMS[TWITCH]
        )
        text = render(store.get(guild.id, "golive_template"), info, interaction.user)
        source = "twitch" if (info.platform or "").casefold() == TWITCH.casefold() else "presence"
        embed = self._embed(guild, info, interaction.user, source)
        details: dict[str, Any] = {"text": text, "platform": info.platform}
        if embed is not None:
            details["embed"] = embed_summary(embed)
        await interaction.response.send_message(
            text,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
            **({"embed": embed} if embed is not None else {}),
        )
        await log_action(
            self.bot, guild, "golive.test", actor=interaction.user, details=details
        )

    @twitch.command(name="link", description="Tell Black Bloc your Twitch channel name")
    @app_commands.describe(channel="Your Twitch channel name (the part after twitch.tv/)")
    async def link(self, interaction: discord.Interaction, channel: str) -> None:
        if not await self._database_ready(interaction):
            return
        cleaned = clean_login(channel)
        if cleaned is None:
            await interaction.response.send_message(BAD_LOGIN, ephemeral=True)
            return
        owner = await link_owner(self.bot.db, cleaned)
        if owner is not None and owner != interaction.user.id:
            await interaction.response.send_message(
                LINK_TAKEN.format(channel=cleaned),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        twitch_user_id = None
        checked = self.helix is None
        if self.helix is not None:
            try:
                users = await self.helix.get_users([cleaned])
            except TwitchError as exc:
                log.warning("go-live: could not check the login %s: %s", cleaned, exc)
                users = None
            if users == []:
                await interaction.response.send_message(
                    f"Twitch has no channel called **{cleaned}**, so nothing was linked. Check "
                    "the spelling against your channel address and run the command again.",
                    ephemeral=True,
                )
                return
            if users:
                checked = True
                twitch_user_id = users[0].id
        await set_link(self.bot.db, interaction.user.id, cleaned, twitch_user_id)
        await interaction.response.send_message(
            (
                f"Linked **{cleaned}** to you. Black Bloc will use it to fill in the game and "
                "title when you go live, and to spot streams Discord does not show. "
                "`/twitch unlink` undoes it."
            )
            if checked
            else LINK_NOT_CHECKED.format(channel=cleaned),
            ephemeral=True,
        )
        await self._log_command(
            interaction, "golive.link", details={"login": cleaned, "checked": checked}
        )

    @twitch.command(name="unlink", description="Forget your Twitch channel")
    async def unlink(self, interaction: discord.Interaction) -> None:
        if not await self._database_ready(interaction):
            return
        removed = await remove_link(self.bot.db, interaction.user.id)
        if not removed:
            await interaction.response.send_message(NOT_LINKED, ephemeral=True)
            return
        await interaction.response.send_message(
            "Done — Black Bloc has forgotten your Twitch channel. Discord presence still "
            "announces your streams; `/golive optout` stops that too.",
            ephemeral=True,
        )
        await self._log_command(interaction, "golive.unlink")

    async def _log_command(
        self, interaction: discord.Interaction, kind: str, details: dict[str, Any] | None = None
    ) -> None:
        if interaction.guild is None:
            return
        await log_action(
            self.bot,
            interaction.guild,
            kind,
            actor=interaction.user,
            target=interaction.user,
            details=details,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GoLive(bot))
