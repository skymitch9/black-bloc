from __future__ import annotations

import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ... import pings
from ...actionlog import (
    LOGS_DEFAULT,
    LOGS_MAX,
    LOGS_MIN,
    log_action,
    send_logs,
)
from ...command_visibility import STAFF_ONLY
from ...golive import now_iso
from ...settings_store import DB_UNAVAILABLE, YOUTUBE_MODES, require_staff
from ...youtube import LIVE, SHORT, UNKNOWN, YouTubeClient, YouTubeError, render

log = logging.getLogger(__name__)

POLL_FAILURES_BEFORE_DEGRADED = 3
NO_KEY = (
    "youtube: no YOUTUBE_API_KEY, so uploads run on the public feed alone — Shorts are still "
    "told apart by their address, live streams are not"
)
ALREADY_LINKED = (
    "**{channel}** is already linked to another member here, so nothing was changed. A YouTube "
    "channel can only belong to one member — if that channel is yours, ask a Lead to remove the "
    "other link first."
)
NOT_LINKED = (
    "You have no YouTube channel linked, so there was nothing to change. Link one with "
    "`/youtube link <your channel address>`."
)
NOT_LINKED_FOR = (
    "**{who}** has no YouTube channel linked, so there was nothing to unlink. `/uploads list` "
    "shows who has one."
)
LINKED = (
    "Linked **{title}** to you. Black Bloc will post here when you put a new video out — the "
    "{count} already on the channel are counted as seen, so nothing old is announced. "
    "`/youtube unlink` undoes it."
)
LINKED_FOR = (
    "Linked **{title}** to {who}. The {count} video(s) already on the channel are counted as "
    "seen, so nothing old is announced."
)
UNLINKED = (
    "Done — Black Bloc has forgotten your YouTube channel and will not announce your uploads."
)
UNLINKED_FOR = (
    "Done — **{who}**'s YouTube channel is forgotten and their uploads are not announced."
)
NOT_SEEDED_YET = "not checked yet"
NOBODY_LINKED = "Nobody has linked a YouTube channel yet."
MODE_OFF_NOTE = (
    " Announcements are **off** at the moment, so nothing is posted until a Lead runs "
    "`/uploads mode on`."
)
SETUP_DONE = "Upload announcements now go to {where}{ping}."
SETUP_NOTHING = (
    "Nothing was given, so nothing changed. Pass a channel, a ping role, or both — "
    "`/uploads setup channel:#somewhere ping_role:@Fans`."
)
NO_CHANNEL = (
    "Uploads have nowhere to go: neither `youtube_channel_id` nor `golive_channel_id` is set. "
    "Run `/uploads setup channel:#somewhere` and they will start posting."
)


def _row_value(row: Any, key: str) -> Any:
    if row is None:
        return None
    try:
        return row[key]
    except (IndexError, KeyError):
        return None


async def set_link(
    db: Any, user_id: int, channel_id: str, handle: str | None = None, title: str | None = None
) -> None:
    await db.conn.execute(
        "INSERT OR REPLACE INTO youtube_links(user_id, channel_id, handle, title, linked_at, "
        "etag, seeded) VALUES (?, ?, ?, ?, ?, NULL, 0)",
        (user_id, channel_id, handle, title, now_iso()),
    )
    await db.conn.commit()


async def get_link(db: Any, user_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM youtube_links WHERE user_id = ?", (user_id,))
    return await cur.fetchone()


async def all_links(db: Any) -> list[Any]:
    cur = await db.conn.execute("SELECT * FROM youtube_links ORDER BY linked_at")
    return list(await cur.fetchall())


async def link_owner(db: Any, channel_id: str) -> int | None:
    cur = await db.conn.execute(
        "SELECT user_id FROM youtube_links WHERE channel_id = ? ORDER BY user_id LIMIT 1",
        (channel_id,),
    )
    row = await cur.fetchone()
    return int(row["user_id"]) if row else None


async def remove_link(db: Any, user_id: int) -> bool:
    cur = await db.conn.execute("DELETE FROM youtube_links WHERE user_id = ?", (user_id,))
    await db.conn.commit()
    return cur.rowcount > 0


async def mark_seeded(db: Any, user_id: int, etag: str | None) -> None:
    await db.conn.execute(
        "UPDATE youtube_links SET seeded = 1, etag = ? WHERE user_id = ?", (etag, user_id)
    )
    await db.conn.commit()


async def set_etag(db: Any, user_id: int, etag: str | None) -> None:
    await db.conn.execute(
        "UPDATE youtube_links SET etag = ? WHERE user_id = ?", (etag, user_id)
    )
    await db.conn.commit()


async def known_ids(db: Any, user_id: int) -> set[str]:
    cur = await db.conn.execute(
        "SELECT video_id FROM youtube_videos WHERE user_id = ?", (user_id,)
    )
    return {str(row["video_id"]) for row in await cur.fetchall()}


async def record_video(db: Any, user_id: int, video: Any, kind: str) -> bool:
    """Store a video as seen. False when another poll already had it, so nobody announces twice."""
    cur = await db.conn.execute(
        "INSERT OR IGNORE INTO youtube_videos(video_id, user_id, channel_id, title, "
        "published_at, seen_at, kind) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            video.video_id,
            user_id,
            video.channel_id,
            video.title,
            video.published,
            now_iso(),
            kind,
        ),
    )
    await db.conn.commit()
    return cur.rowcount > 0


async def set_announced(
    db: Any, video_id: str, mode: str, message_id: int | None = None
) -> None:
    """The mode travels with the timestamp, so a later flip cannot rewrite what happened."""
    await db.conn.execute(
        "UPDATE youtube_videos SET announced_at = ?, announced_message_id = ?, mode = ? "
        "WHERE video_id = ?",
        (now_iso(), message_id, mode, video_id),
    )
    await db.conn.commit()


async def recent_videos(db: Any, limit: int = 50) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM youtube_videos ORDER BY published_at DESC, rowid DESC LIMIT ?",
        (int(limit),),
    )
    return list(await cur.fetchall())


async def latest_video(db: Any, user_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM youtube_videos WHERE user_id = ? ORDER BY published_at DESC, rowid DESC "
        "LIMIT 1",
        (user_id,),
    )
    return await cur.fetchone()


async def counts(db: Any) -> dict[str, int]:
    async def scalar(sql: str) -> int:
        cur = await db.conn.execute(sql)
        row = await cur.fetchone()
        return int(row["n"]) if row else 0

    return {
        "links": await scalar("SELECT COUNT(*) AS n FROM youtube_links"),
        "videos": await scalar("SELECT COUNT(*) AS n FROM youtube_videos"),
        "announced": await scalar(
            "SELECT COUNT(*) AS n FROM youtube_videos WHERE announced_at IS NOT NULL"
        ),
    }


class YouTube(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.client = YouTubeClient(getattr(bot.settings, "youtube_api_key", None))
        self.last_poll_ok_at: str | None = None
        self.last_poll_error: str | None = None
        self.poll_failures = 0
        self.fetches = 0
        self.unchanged = 0

    youtube = app_commands.Group(name="youtube", description="Your YouTube channel")
    uploads = app_commands.Group(
        name="uploads",
        description="New-upload announcements",
        default_permissions=STAFF_ONLY,
    )

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name != "poller":
            return (None, None)
        return (self.last_poll_ok_at, self.last_poll_error)

    async def cog_load(self) -> None:
        if not self.client.keyed:
            log.info(NO_KEY)
        if not self.bot.db.is_connected:
            return
        self.poller.start()

    async def cog_unload(self) -> None:
        self.poller.cancel()
        await self.client.close()

    # --- the poll ---------------------------------------------------------------------------

    @tasks.loop(minutes=1)
    async def poller(self) -> None:
        try:
            await self.poll_once()
        except Exception as exc:
            self.last_poll_error = f"{type(exc).__name__}: {exc}"
            log.exception("youtube: the uploads poll failed")
        self._retime()

    @poller.before_loop
    async def _before_poller(self) -> None:
        await self.bot.wait_until_ready()
        self._retime()

    @poller.error
    async def _poller_stopped(self, exc: BaseException) -> None:
        """The loop stops for the life of the process unless it is started again."""
        self.last_poll_error = f"{type(exc).__name__}: {exc}"
        log.error("youtube: the uploads poll stopped; restarting it", exc_info=exc)
        self.poller.restart()

    def _retime(self) -> None:
        """The gap is a setting, so every tick re-reads it rather than freezing the boot value."""
        wanted = self._minutes()
        if self.poller.minutes != wanted:
            self.poller.change_interval(minutes=wanted)

    def _minutes(self) -> int:
        guild = next(iter(getattr(self.bot, "guilds", ()) or ()), None)
        if guild is None:
            return 10
        return max(1, int(self.bot.store.get(guild.id, "youtube_poll_minutes")))

    async def poll_once(self) -> None:
        """One sweep of every linked channel: new entries are stored, then maybe announced."""
        if not self.bot.db.is_connected:
            return
        rows = await self._pollable()
        if not rows:
            self._poll_worked()
            return
        failures = 0
        for row in rows:
            try:
                await self._poll_link(row)
            except YouTubeError as exc:
                failures += 1
                log.warning(
                    "youtube: could not read the feed for %s: %s", row["channel_id"], exc
                )
                self.last_poll_error = str(exc)
        if failures and failures == len(rows):
            await self._poll_failed(failures)
            return
        self._poll_worked()

    async def _pollable(self) -> list[Any]:
        """One row per channel; a channel linked twice is polled for the first member only."""
        by_channel: dict[str, Any] = {}
        for row in await all_links(self.bot.db):
            channel_id = str(row["channel_id"])
            if channel_id in by_channel:
                log.warning(
                    "youtube: channel %s is linked to both %s and %s; only the first is polled",
                    channel_id,
                    by_channel[channel_id]["user_id"],
                    row["user_id"],
                )
                continue
            by_channel[channel_id] = row
        return list(by_channel.values())

    async def _poll_link(self, row: Any) -> None:
        user_id = int(row["user_id"])
        status, etag, videos = await self.client.fetch_feed(
            str(row["channel_id"]), _row_value(row, "etag")
        )
        self.fetches += 1
        if status == 304:
            self.unchanged += 1
            return
        if not row["seeded"]:
            await self._seed(user_id, row, videos, etag)
            return
        await set_etag(self.bot.db, user_id, etag)
        seen = await known_ids(self.bot.db, user_id)
        fresh = [video for video in videos if video.video_id not in seen]
        if not fresh:
            return
        kinds = await self._kinds(fresh)
        for video in sorted(fresh, key=lambda one: one.published):
            await self._found(user_id, video, kinds.get(video.video_id, video.kind))

    async def _seed(self, user_id: int, row: Any, videos: Any, etag: str | None) -> None:
        """D10: what is already on the channel at link time is history, never an announcement."""
        stored = 0
        for video in videos:
            if await record_video(self.bot.db, user_id, video, video.kind):
                stored += 1
        await mark_seeded(self.bot.db, user_id, etag)
        for guild in list(getattr(self.bot, "guilds", ())):
            await log_action(
                self.bot,
                guild,
                "youtube.seeded",
                target=user_id,
                details={
                    "user_id": user_id,
                    "channel_id": str(row["channel_id"]),
                    "counted_as_seen": stored,
                },
            )

    async def _kinds(self, videos: Any) -> dict[str, str]:
        """The key refines what the address already says; without one the address stands."""
        if not self.client.keyed:
            return {}
        try:
            return await self.client.classify([video.video_id for video in videos])
        except YouTubeError as exc:
            log.warning("youtube: could not classify %d new video(s): %s", len(videos), exc)
            return {}

    # --- announcing --------------------------------------------------------------------------

    async def _found(self, user_id: int, video: Any, kind: str) -> None:
        member = self._find_member(user_id)
        if member is None:
            await record_video(self.bot.db, user_id, video, kind)
            log.info(
                "youtube: %s is in no visible server; %s stored only", user_id, video.video_id
            )
            return
        guild = member.guild
        kind = await self._settled(guild, member, video, kind)
        if not await record_video(self.bot.db, user_id, video, kind):
            return
        skip = await self._skipped(guild, kind)
        if skip is not None:
            await log_action(
                self.bot,
                guild,
                "youtube.skipped",
                target=member,
                details={
                    "video_id": video.video_id,
                    "kind": kind,
                    "url": video.link,
                    "reason": skip,
                },
            )
            return
        await self._announce(guild, member, video, kind)

    async def _settled(self, guild: Any, member: Any, video: Any, kind: str) -> str:
        """D6: with no key a live broadcast looks like a video, unless they are live right now."""
        if kind in (LIVE, SHORT):
            return kind
        if self.client.keyed and kind != UNKNOWN:
            return kind
        return LIVE if await self._open_golive_session(guild, member) else kind

    async def _open_golive_session(self, guild: Any, member: Any) -> bool:
        from .golive import open_session_for

        row = await open_session_for(self.bot.db, guild.id, member.id)
        return row is not None and str(_row_value(row, "platform") or "").casefold() == "youtube"

    async def _skipped(self, guild: Any, kind: str) -> str | None:
        if kind == LIVE:
            return "live"
        if kind == SHORT and not self.bot.store.get(guild.id, "youtube_announce_shorts"):
            return "short"
        return None

    async def _announce(self, guild: Any, member: Any, video: Any, kind: str) -> None:
        mode = self._mode(guild.id)
        if mode == "off":
            return
        store = self.bot.store
        fan_role_id = await self._fan_role(guild, member)
        ping_role_id = store.get(guild.id, "youtube_ping_role_id")
        text = render(
            store.get(guild.id, "youtube_template"),
            video,
            member,
            ping_role_id=ping_role_id,
            fan_role_id=fan_role_id,
        )
        details = {
            "video_id": video.video_id,
            "kind": kind,
            "url": video.link,
            "text": text,
            "channel_id": video.channel_id,
            "source": "api" if self.client.keyed else "feed",
            "mode": mode,
            "fan_role_id": fan_role_id,
        }
        if mode != "on":
            await log_action(
                self.bot, guild, "youtube.would_announce", target=member, details=details
            )
            await set_announced(self.bot.db, video.video_id, mode)
            return
        message, reason = await self._post(guild, text, fan_role_id)
        if message is None and reason != "test_mode":
            await log_action(
                self.bot,
                guild,
                "youtube.post_failed",
                target=member,
                details=details | {"reason": reason},
            )
            return
        if message is None:
            await log_action(
                self.bot,
                guild,
                "youtube.would_announce",
                target=member,
                details=details | {"reason": "test_mode"},
            )
            return
        await set_announced(self.bot.db, video.video_id, mode, message.id)
        await log_action(
            self.bot,
            guild,
            "youtube.announce",
            target=member,
            details=details | {"message_id": message.id},
        )

    async def _fan_role(self, guild: Any, member: Any) -> int | None:
        if not self.bot.store.get(guild.id, "youtube_ping_fan_roles"):
            return None
        return await pings.announced_fan_role(self.bot, guild, member.id)

    async def _post(self, guild: Any, text: str, fan_role_id: int | None) -> tuple[Any, str | None]:
        """The one guarded path every upload post goes through."""
        channel_id = self._channel_id(guild.id)
        if not channel_id:
            log.warning("youtube: not posted — no upload channel and no go-live channel is set")
            return (None, "no_channel_configured")
        guard = getattr(self.bot, "guard", None)
        if guard is not None and not guard.allows_channel(channel_id):
            log.warning("youtube: TEST MODE — refused to post to channel %s", channel_id)
            return (None, "test_mode")
        channel = self.bot.get_channel(channel_id) or guild.get_channel(channel_id)
        if channel is None:
            log.warning("youtube: not posted — channel %s is not visible", channel_id)
            return (None, "channel_not_visible")
        try:
            message = await channel.send(
                text, allowed_mentions=self._mentions(guild.id, fan_role_id)
            )
        except Exception as exc:
            log.warning("youtube: not posted — %s: %s", type(exc).__name__, exc)
            return (None, f"{type(exc).__name__}: {exc}")
        return (message, None)

    def _mentions(self, guild_id: int, fan_role_id: int | None) -> discord.AllowedMentions:
        wanted = [
            role_id
            for role_id in (self.bot.store.get(guild_id, "youtube_ping_role_id"), fan_role_id)
            if role_id
        ]
        return discord.AllowedMentions(
            everyone=False,
            users=False,
            roles=[discord.Object(role_id) for role_id in dict.fromkeys(wanted)] or False,
        )

    def _channel_id(self, guild_id: int) -> int | None:
        """D3: blank means the go-live channel, so one place is set up rather than two."""
        store = self.bot.store
        return store.get(guild_id, "youtube_channel_id") or store.get(
            guild_id, "golive_channel_id"
        )

    def _mode(self, guild_id: int) -> str:
        return self.bot.store.get(guild_id, "youtube_mode")

    def _where_words(self, guild_id: int) -> str:
        """Why an upload would not be posted, in words — never a bare mode name on its own."""
        mode = self._mode(guild_id)
        where = self._channel_id(guild_id)
        if mode != "on":
            return f"no — upload announcements are **{mode}** for this server at the moment"
        if not where:
            return "no — nowhere is set to post them; a Lead runs `/uploads setup`"
        return f"yes, in <#{where}>"

    def _find_member(self, user_id: int) -> Any:
        for guild in self.bot.guilds:
            member = guild.get_member(user_id)
            if member is not None:
                return member
        return None

    def _poll_worked(self) -> None:
        self.last_poll_ok_at = now_iso()
        self.last_poll_error = None
        self.poll_failures = 0

    async def _poll_failed(self, failures: int) -> None:
        """One action-log line per outage, at the point the sweep stops being trustworthy."""
        self.poll_failures += 1
        log.warning(
            "youtube: every linked channel failed to answer (%d sweep(s) in a row)",
            self.poll_failures,
        )
        if self.poll_failures != POLL_FAILURES_BEFORE_DEGRADED:
            return
        for guild in list(getattr(self.bot, "guilds", ())):
            await log_action(
                self.bot,
                guild,
                "youtube.poll_degraded",
                details={
                    "sweeps": self.poll_failures,
                    "channels": failures,
                    "reason": self.last_poll_error,
                },
            )

    # --- commands ----------------------------------------------------------------------------

    async def _database_ready(self, interaction: discord.Interaction) -> bool:
        if self.bot.db.is_connected:
            return True
        log.warning("youtube: refused a command — the database is not connected")
        await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
        return False

    async def _link_to(
        self, interaction: discord.Interaction, user_id: int, channel: str
    ) -> tuple[str, int] | None:
        """Resolve, refuse a channel somebody else owns, store, and seed. None means refused."""
        try:
            channel_id, title = await self.client.resolve(channel)
        except YouTubeError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            await self._log(
                interaction, "youtube.resolve_failed", {"given": channel[:80], "reason": str(exc)}
            )
            return None
        owner = await link_owner(self.bot.db, channel_id)
        if owner is not None and owner != user_id:
            await interaction.followup.send(
                ALREADY_LINKED.format(channel=title or channel_id),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return None
        await set_link(self.bot.db, user_id, channel_id, _handle_of(channel), title)
        counted = await self._seed_now(user_id, channel_id)
        return ((title or channel_id), counted)

    async def _seed_now(self, user_id: int, channel_id: str) -> int:
        """Linking counts the current feed as history; a feed that will not answer seeds later."""
        row = await get_link(self.bot.db, user_id)
        try:
            _status, etag, videos = await self.client.fetch_feed(channel_id)
        except YouTubeError as exc:
            log.warning("youtube: could not seed %s yet (%s); the poller will", channel_id, exc)
            return 0
        await self._seed(user_id, row, videos, etag)
        return len(videos)

    @youtube.command(name="link", description="Tell Black Bloc your YouTube channel")
    @app_commands.describe(channel="Your channel address, or @handle, or its UC… id")
    async def link(self, interaction: discord.Interaction, channel: str) -> None:
        if not await self._database_ready(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        done = await self._link_to(interaction, interaction.user.id, channel)
        if done is None:
            return
        title, counted = done
        note = "" if self._mode(interaction.guild.id) != "off" else MODE_OFF_NOTE
        await interaction.followup.send(
            LINKED.format(title=title, count=counted) + note,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await self._log(interaction, "youtube.link", {"title": title, "seeded": counted})

    @youtube.command(name="unlink", description="Forget your YouTube channel")
    async def unlink(self, interaction: discord.Interaction) -> None:
        if not await self._database_ready(interaction):
            return
        if not await remove_link(self.bot.db, interaction.user.id):
            await interaction.response.send_message(NOT_LINKED, ephemeral=True)
            return
        await interaction.response.send_message(UNLINKED, ephemeral=True)
        await self._log(interaction, "youtube.unlink")

    @youtube.command(name="status", description="What Black Bloc does with your uploads")
    async def status(self, interaction: discord.Interaction) -> None:
        if not await self._database_ready(interaction):
            return
        row = await get_link(self.bot.db, interaction.user.id)
        if row is None:
            await interaction.response.send_message(NOT_LINKED, ephemeral=True)
            return
        guild = interaction.guild
        latest = await latest_video(self.bot.db, interaction.user.id)
        seen = _row_value(latest, "title")
        if not seen:
            seen = "none yet" if row["seeded"] else NOT_SEEDED_YET
        shorts = self.bot.store.get(guild.id, "youtube_announce_shorts")
        lines = [
            f"**channel** — {row['title'] or row['channel_id']}",
            f"**linked** — {row['linked_at']}",
            f"**last video seen** — {seen}",
            f"**announced here** — {self._where_words(guild.id)}",
            f"**Shorts** — {'announced too' if shorts else 'not announced'}",
        ]
        await interaction.response.send_message(
            "\n".join(lines), ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @uploads.command(name="logs", description="The last few upload log lines")
    @app_commands.describe(
        count="How many lines, 1 to 50 (10 by default)",
        important_only="True to leave out the dry runs and the housekeeping",
    )
    async def uploads_logs(
        self,
        interaction: discord.Interaction,
        count: app_commands.Range[int, LOGS_MIN, LOGS_MAX] = LOGS_DEFAULT,
        important_only: bool = False,
    ) -> None:
        await send_logs(interaction, "youtube", count=count, important_only=important_only)

    @uploads.command(name="mode", description="Turn upload announcements off, shadow or on")
    @app_commands.describe(mode="off, shadow (log only) or on (post announcements)")
    @app_commands.choices(
        mode=[app_commands.Choice(name=name, value=name) for name in YOUTUBE_MODES]
    )
    async def mode(
        self, interaction: discord.Interaction, mode: app_commands.Choice[str]
    ) -> None:
        if not await require_staff(interaction):
            return
        await self.bot.store.set(
            interaction.guild.id, "youtube_mode", mode.value, by=interaction.user.id
        )
        extra = "" if self._channel_id(interaction.guild.id) else f" {NO_CHANNEL}"
        await interaction.response.send_message(
            f"Upload announcements are now **{mode.value}**.{extra}", ephemeral=True
        )
        await log_action(
            self.bot,
            interaction.guild,
            "youtube.mode",
            actor=interaction.user,
            details={"mode": mode.value},
        )

    @uploads.command(name="setup", description="Where uploads are posted, and who is pinged")
    @app_commands.describe(
        channel="Where to post; leave it out to keep using the go-live channel",
        ping_role="Role to mention in front of every upload announcement",
    )
    async def setup_uploads(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
        ping_role: discord.Role | None = None,
    ) -> None:
        if not await require_staff(interaction):
            return
        if channel is None and ping_role is None:
            await interaction.response.send_message(SETUP_NOTHING, ephemeral=True)
            return
        store = self.bot.store
        if channel is not None:
            await store.set(
                interaction.guild.id, "youtube_channel_id", channel.id, by=interaction.user.id
            )
        if ping_role is not None:
            await store.set(
                interaction.guild.id, "youtube_ping_role_id", ping_role.id, by=interaction.user.id
            )
        where = f"<#{self._channel_id(interaction.guild.id)}>"
        ping = f", pinging {ping_role.mention}" if ping_role is not None else ""
        await interaction.response.send_message(
            SETUP_DONE.format(where=where, ping=ping),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await log_action(
            self.bot,
            interaction.guild,
            "youtube.setup",
            actor=interaction.user,
            details={
                "channel_id": getattr(channel, "id", None),
                "ping_role_id": getattr(ping_role, "id", None),
            },
        )

    @uploads.command(name="link-for", description="Link a member's YouTube channel for them")
    @app_commands.describe(member="Whose channel this is", channel="Their channel address or id")
    async def link_for(
        self, interaction: discord.Interaction, member: discord.Member, channel: str
    ) -> None:
        if not await require_staff(interaction):
            return
        if not await self._database_ready(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        done = await self._link_to(interaction, member.id, channel)
        if done is None:
            return
        title, counted = done
        await interaction.followup.send(
            LINKED_FOR.format(title=title, who=member.display_name, count=counted),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await log_action(
            self.bot,
            interaction.guild,
            "youtube.link",
            actor=interaction.user,
            target=member,
            details={"title": title, "seeded": counted},
        )

    @uploads.command(name="unlink-for", description="Forget a member's YouTube channel")
    @app_commands.describe(member="Whose channel to forget")
    async def unlink_for(
        self, interaction: discord.Interaction, member: discord.Member
    ) -> None:
        if not await require_staff(interaction):
            return
        if not await self._database_ready(interaction):
            return
        if not await remove_link(self.bot.db, member.id):
            await interaction.response.send_message(
                NOT_LINKED_FOR.format(who=member.display_name),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        await interaction.response.send_message(
            UNLINKED_FOR.format(who=member.display_name),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await log_action(
            self.bot,
            interaction.guild,
            "youtube.unlink",
            actor=interaction.user,
            target=member,
            details={"user_id": member.id},
        )

    @uploads.command(name="list", description="Who has a YouTube channel linked, and how it is")
    async def list_links(self, interaction: discord.Interaction) -> None:
        if not await require_staff(interaction):
            return
        if not await self._database_ready(interaction):
            return
        guild = interaction.guild
        rows = await all_links(self.bot.db)
        totals = await counts(self.bot.db)
        where = self._channel_id(guild.id)
        lines = [
            f"**mode** — {self._mode(guild.id)}",
            f"**channel** — {f'<#{where}>' if where else 'not set'}",
            f"**every** — {self.bot.store.get(guild.id, 'youtube_poll_minutes')} minute(s)",
            f"**api key** — {'set' if self.client.keyed else 'not set (feed only)'}",
            f"**last good sweep** — {self.last_poll_ok_at or 'never'}",
            f"**last error** — {self.last_poll_error or 'none'}"
            + (f" ({self.poll_failures} sweep(s) in a row)" if self.poll_failures else ""),
            f"**links** — {totals['links']} · **videos seen** — {totals['videos']} · "
            f"**announced** — {totals['announced']}",
        ]
        for row in rows:
            member = guild.get_member(int(row["user_id"]))
            named = getattr(member, "display_name", None) or row["user_id"]
            seen = "seeded" if row["seeded"] else NOT_SEEDED_YET
            lines.append(f"• {named} — {row['title'] or row['channel_id']} ({seen})")
        if not rows:
            lines.append(NOBODY_LINKED)
        await interaction.response.send_message(
            "\n".join(lines), ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    async def _log(
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


def _handle_of(text: str) -> str | None:
    from ...youtube import channel_id_in, handle_in

    return None if channel_id_in(text) else handle_in(text)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(YouTube(bot))
