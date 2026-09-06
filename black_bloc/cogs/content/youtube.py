from __future__ import annotations

import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ... import pings
from ...actionlog import log_action, send_logs
from ...command_errors import AnswersErrors
from ...golive import now_iso
from ...logkinds import VIA_DISCORD, kind_via
from ...loops import wait_ready
from ...panels import (
    NoteModal,
    Panel,
    answer,
    capped_placeholder,
    confirm,
    confirm_items,
    db_up,
    opened,
    option_label,
    retire,
    still_staff,
)
from ...panels import site_page_url as library_site_page_url
from ...settings_store import (
    DB_UNAVAILABLE,
    GUILD_ONLY,
    YOUTUBE_MODES,
    YOUTUBE_POLL_MIN_MINUTES,
    SettingError,
    coerce_value,
)
from ...youtube import (
    BACK,
    KEEP_IT,
    LINK,
    LINK_FOR,
    LIVE,
    LOGS,
    NOBODY_LINKED,
    NOT_SEEDED_YET,
    PANEL_MINUTES_KEY,
    PANEL_TIMEOUT_FOOTER,
    PANEL_TITLE,
    REFRESH,
    RELINK,
    SELECT_CAP,
    SETUP,
    SHORT,
    UNKNOWN,
    UNLINK,
    UNLINK_FOR,
    PanelMove,
    YouTubeClient,
    YouTubeError,
    card_buttons,
    health_lines,
    link_lines,
    panel_minutes,
    render,
    status_lines,
    where_words,
)

log = logging.getLogger(__name__)

COG_NAME = "YouTube"
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
    "You have no YouTube channel linked, so there was nothing to change. **Link my channel** "
    "on this panel connects one."
)
NOT_LINKED_FOR = (
    "**{who}** has no YouTube channel linked, so there was nothing to unlink. The panel lists "
    "everybody who has one."
)
LINKED = (
    "Linked **{title}** to you. Black Bloc will post here when you put a new video out — the "
    "{count} already on the channel are counted as seen, so nothing old is announced. "
    "**Unlink** on this panel undoes it."
)
LINKED_FOR = (
    "Linked **{title}** to {who}. The {count} video(s) already on the channel are counted as "
    "seen, so nothing old is announced."
)
LINKED_NOT_SEEDED = (
    "Linked **{title}** to you, but YouTube's feed would not answer just now, so nothing has "
    "been counted as seen yet. The next sweep does it — until then no upload is announced."
)
LINKED_FOR_NOT_SEEDED = (
    "Linked **{title}** to {who}, but YouTube's feed would not answer just now, so nothing has "
    "been counted as seen yet. The next sweep does it — until then no upload is announced."
)
UNLINKED = (
    "Done — Black Bloc has forgotten your YouTube channel and will not announce your uploads."
)
UNLINKED_FOR = (
    "Done — **{who}**'s YouTube channel is forgotten and their uploads are not announced."
)
UNLINKED_DM = (
    "A Lead has removed the YouTube channel Black Bloc had linked to you in **{guild}**, so "
    "your uploads are no longer announced there. You can link one again with `/youtube`."
)
UNLINKED_DM_WHY = "\n\nWhat they said: {why}"
MODE_OFF_NOTE = (
    " Announcements are **off** at the moment, so nothing is posted until a Lead sets "
    "**Announcements are…** on this panel to shadow or on."
)
MODE_OFF_LINE = (
    "Announcements are **off** for this server at the moment, so nothing is posted. Linking is "
    "still worth doing — it is your own opt-in, and the mode is the server's switch. A Lead "
    "changes it with **Announcements are…** on this panel."
)
MODE_SET = "Upload announcements are now **{mode}**."
SETUP_DONE = "Upload announcements now go to {where}{ping}."
SETUP_NOTHING = "Nothing was given, so nothing changed."
NO_CHANNEL = (
    "Uploads have nowhere to go: neither `youtube_channel_id` nor `golive_channel_id` is set. "
    "**Setup** on this panel picks one and they will start posting."
)
FALLS_BACK = "the go-live channel <#{channel}>"
NOWHERE = "nowhere — neither an upload channel nor a go-live channel is set"
FEATURE_MISSING = (
    "The uploads feature is not loaded right now, so nothing was changed. Tell a Lead — the "
    "bot needs a restart."
)


PANEL_INTRO = (
    "Tell Black Bloc where your YouTube channel is and it posts here when you put a new video "
    "out. Nothing already published is ever announced."
)
SITE_BUTTON = "Open on the site"
FEATURE = "youtube"
PICK_A_CHANNEL = "Somebody's channel…"
MODE_PLACEHOLDER = "Announcements are…"
MODE_LABELS = {
    "off": "off — nothing is checked and nothing is posted",
    "shadow": "shadow — the sweep runs and logs, nothing is posted",
    "on": "on — a new upload is announced",
}
WHOSE_CHANNEL = "Whose channel is it?"
THEIR_CARD = "**{who}**'s YouTube channel"
LINK_TITLE = "Link your YouTube channel"
LINK_FOR_TITLE = "Link a channel for {who}"
LINK_LABEL = "Your channel address, @handle, or UC… id"
LINK_FOR_LABEL = "Their channel address, @handle, or UC… id"
LINK_LIMIT = 200
UNLINK_FOR_TITLE = "Why?"
UNLINK_FOR_LABEL = "One line they will be sent"
NOTE_LIMIT = 400

SETUP_TITLE = "Where uploads are posted"
WHERE_UPLOADS = "Where uploads are posted…"
WHO_IS_PINGED = "Who is pinged…"
SHORTS_ON = "Shorts: announced"
SHORTS_OFF = "Shorts: not announced"
FANS_ON = "Fans pinged: on"
FANS_OFF = "Fans pinged: off"
WORDS_BUTTON = "Words…"
NUMBERS_BUTTON = "Numbers…"
FORGET_BUTTON = "Forget…"
FORGET_PLACEHOLDER = "Clear one of these…"
FORGET_CHANNEL = "the upload channel — uploads fall back to the go-live one"
FORGET_PING_ROLE = "the ping role — nobody is pinged"
WORDS_TITLE = "What an upload announcement says"
WORDS_LABEL = "{name} {title} {url} {channel} {kind}"
TEMPLATE_LIMIT = 500
NUMBERS_TITLE = "Numbers"
EVERY_LABEL = "Minutes between checks"
PANEL_MINUTES_LABEL = "Minutes this panel stays live"
NOT_A_NUMBER = (
    "**{given}** is not a whole number, so nothing was changed. {label} takes a number of "
    "minutes — {floor} or more."
)
WORDS_SAVED = "Saved. An upload announcement now reads like this:"
STYLES = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}
SETUP_KEYS = (
    "youtube_channel_id",
    "youtube_ping_role_id",
    "youtube_announce_shorts",
    "youtube_ping_fan_roles",
    "youtube_template",
    "youtube_poll_minutes",
    PANEL_MINUTES_KEY,
)
SHORTS = "shorts"
FANS = "fans"
WORDS = "words"
NUMBERS = "numbers"
FORGET = "forget"

SHORTS_MOVE = PanelMove(SHORTS, SHORTS_OFF, "secondary", row=2)
FANS_MOVE = PanelMove(FANS, FANS_OFF, "secondary", row=2)
WORDS_MOVE = PanelMove(WORDS, WORDS_BUTTON, "secondary", row=2, modal=True)
NUMBERS_MOVE = PanelMove(NUMBERS, NUMBERS_BUTTON, "secondary", row=2, modal=True)
SETUP_BACK_MOVE = PanelMove(BACK, "Back", "secondary", row=2)
FORGET_MOVE = PanelMove(FORGET, FORGET_BUTTON, "secondary", row=3)
SETUP_MOVES = (SHORTS_MOVE, FANS_MOVE, WORDS_MOVE, NUMBERS_MOVE, SETUP_BACK_MOVE, FORGET_MOVE)


class LinkRefused(RuntimeError):
    """A link the shared path will not make: the paste, or somebody else already owning it."""

    def __init__(self, message: str, *, status: int, code: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


def _row_value(row: Any, key: str) -> Any:
    if row is None:
        return None
    try:
        return row[key]
    except (IndexError, KeyError):
        return None


def cog_of(bot: Any) -> Any:
    getter = getattr(bot, "get_cog", None)
    return getter(COG_NAME) if callable(getter) else None


def display_of(member: Any) -> str:
    return str(
        getattr(member, "display_name", None) or getattr(member, "name", None) or member
    )


def id_of(member: Any) -> int:
    return int(getattr(member, "id", member) or 0)


def upload_channel_id(store: Any, guild_id: int) -> int | None:
    """D3: blank means the go-live channel, so one place is set up rather than two."""
    return store.get(guild_id, "youtube_channel_id") or store.get(guild_id, "golive_channel_id")


def setup_words(store: Any, guild_id: int) -> str:
    upload = store.get(guild_id, "youtube_channel_id")
    golive = store.get(guild_id, "golive_channel_id")
    if upload:
        where = f"<#{upload}>"
    elif golive:
        where = FALLS_BACK.format(channel=golive)
    else:
        where = NOWHERE
    role = store.get(guild_id, "youtube_ping_role_id")
    ping = f", pinging <@&{role}>" if role else ", pinging nobody"
    return SETUP_DONE.format(where=where, ping=ping)


def site_page_url(origin: Any) -> str:
    return library_site_page_url(origin, FEATURE) or ""


def add_site_button(view: Any, bot: Any, row: int) -> None:
    """No origin, no button — a link that goes nowhere is worse than no link at all."""
    url = site_page_url(getattr(getattr(bot, "settings", None), "origin", ""))
    if not url:
        return
    view.add_item(
        discord.ui.Button(
            style=discord.ButtonStyle.link, label=SITE_BUTTON, url=url, row=row
        )
    )


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


async def link_channel(
    bot: Any, guild: Any, actor: Any, member: Any, given: Any, *, via: str = VIA_DISCORD
) -> tuple[str, Any, int]:
    """Resolve, refuse a channel somebody else owns, store and seed — one write, one log row."""
    cog = cog_of(bot)
    if cog is None:
        return (FEATURE_MISSING, None, 0)
    user_id = id_of(member)
    mine = id_of(actor) == user_id
    try:
        channel_id, title = await cog.client.resolve(given)
    except YouTubeError as exc:
        await log_action(
            bot,
            guild,
            kind_via("youtube.resolve_failed", via),
            actor=actor,
            target=member,
            details={
                "given": str(given)[:80],
                "reason": str(exc),
                "network": bool(getattr(exc, "network", False)),
                "via": via,
            },
        )
        raise LinkRefused(str(exc), status=400, code="bad_channel") from exc
    owner = await link_owner(bot.db, channel_id)
    if owner is not None and owner != user_id:
        raise LinkRefused(
            ALREADY_LINKED.format(channel=title or channel_id), status=409, code="link_taken"
        )
    counted = await cog.link_and_seed(user_id, channel_id, given, title)
    row = await get_link(bot.db, user_id)
    named = title or channel_id
    who = display_of(member)
    if _row_value(row, "seeded"):
        said = (LINKED if mine else LINKED_FOR).format(title=named, who=who, count=counted)
    else:
        said = (LINKED_NOT_SEEDED if mine else LINKED_FOR_NOT_SEEDED).format(
            title=named, who=who
        )
    if mine and bot.store.get(guild.id, "youtube_mode") == "off":
        said += MODE_OFF_NOTE
    await log_action(
        bot,
        guild,
        kind_via("youtube.link", via),
        actor=actor,
        target=member,
        details={
            "title": title,
            "seeded": counted,
            "counted": bool(_row_value(row, "seeded")),
            "via": via,
        },
    )
    return (said, row, counted)


async def tell_unlinked(bot: Any, guild: Any, user_id: int, note: Any) -> bool:
    """Staff-final-say: a move that affects somebody carries a reason, best effort."""
    person = guild.get_member(user_id)
    if person is None and callable(getattr(bot, "get_user", None)):
        person = bot.get_user(user_id)
    send = getattr(person, "send", None)
    if send is None:
        return False
    why = str(note or "").strip()
    text = UNLINKED_DM.format(guild=getattr(guild, "name", "the server"))
    if why:
        text += UNLINKED_DM_WHY.format(why=why)
    try:
        await send(text, allowed_mentions=discord.AllowedMentions.none())
    except Exception as exc:
        log.info("youtube: could not DM %s about an unlink: %s", user_id, exc)
        return False
    return True


async def unlink_channel(
    bot: Any,
    guild: Any,
    actor: Any,
    member: Any,
    *,
    note: Any = None,
    via: str = VIA_DISCORD,
) -> tuple[str, Any]:
    """The one path a link is forgotten by, from either door — one write, one log row."""
    user_id = id_of(member)
    mine = id_of(actor) == user_id
    if not await remove_link(bot.db, user_id):
        return ((NOT_LINKED if mine else NOT_LINKED_FOR.format(who=display_of(member))), None)
    details: dict[str, Any] = {"user_id": user_id, "via": via}
    if not mine and bot.store.get(guild.id, "youtube_unlink_dms_them"):
        told = await tell_unlinked(bot, guild, user_id, note)
        details["told"] = told
        if not told:
            details["dm_failed"] = True
    why = str(note or "").strip()
    await log_action(
        bot,
        guild,
        kind_via("youtube.unlink", via),
        actor=actor,
        target=member,
        reason=why or None,
        details=details,
    )
    return ((UNLINKED if mine else UNLINKED_FOR.format(who=display_of(member))), None)


async def set_mode(
    bot: Any, guild: Any, actor: Any, value: str, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    try:
        await bot.store.set(guild.id, "youtube_mode", value, by=id_of(actor) or None)
    except SettingError as exc:
        return (str(exc), None)
    extra = "" if upload_channel_id(bot.store, guild.id) else f" {NO_CHANNEL}"
    await log_action(
        bot,
        guild,
        kind_via("youtube.mode", via),
        actor=actor,
        details={"mode": value, "via": via},
    )
    return (MODE_SET.format(mode=value) + extra, None)


async def save_setup(
    bot: Any, guild: Any, actor: Any, changes: Any, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    """A dict so the sub-panel and any later route write identically; None clears a key."""
    wanted = {key: value for key, value in (changes or {}).items() if key in SETUP_KEYS}
    if not wanted:
        return (SETUP_NOTHING, None)
    for key, value in wanted.items():
        if value is None:
            continue
        try:
            coerce_value(key, value)
        except SettingError as exc:
            return (str(exc), None)
    by = id_of(actor) or None
    for key, value in wanted.items():
        if value is None:
            await bot.store.clear(guild.id, key, by=by)
        else:
            await bot.store.set(guild.id, key, value, by=by)
    await log_action(
        bot,
        guild,
        kind_via("youtube.setup", via),
        actor=actor,
        details={
            "changed": {
                key: (str(value)[:80] if isinstance(value, str) else value)
                for key, value in wanted.items()
            },
            "via": via,
        },
    )
    return (setup_words(bot.store, guild.id), None)


class YouTube(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.client = YouTubeClient(getattr(bot.settings, "youtube_api_key", None))
        self.last_poll_ok_at: str | None = None
        self.last_poll_error: str | None = None
        self.poll_failures = 0
        self.fetches = 0
        self.unchanged = 0

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
        if await wait_ready(self.bot, self._poller_stopped):
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
        return upload_channel_id(self.bot.store, guild_id)

    def _mode(self, guild_id: int) -> str:
        return self.bot.store.get(guild_id, "youtube_mode")

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

    # --- the command -------------------------------------------------------------------------

    async def link_and_seed(
        self, user_id: int, channel_id: str, given: str, title: str | None
    ) -> int:
        """Store the link and count what is already published as history; the web calls it too."""
        await set_link(self.bot.db, user_id, channel_id, _handle_of(given), title)
        row = await get_link(self.bot.db, user_id)
        try:
            _status, etag, videos = await self.client.fetch_feed(channel_id)
        except YouTubeError as exc:
            log.warning("youtube: could not seed %s yet (%s); the poller will", channel_id, exc)
            return 0
        await self._seed(user_id, row, videos, etag)
        return len(videos)

    @app_commands.command(
        name="youtube", description="Your YouTube channel, and how uploads are announced"
    )
    async def youtube(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return
        if not self.bot.db.is_connected:
            log.warning("youtube: refused the panel — the database is not connected")
            await answer(interaction, DB_UNAVAILABLE)
            return
        embed, view = await build_panel(self.bot, interaction.guild, interaction.user)
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()


def _handle_of(text: str) -> str | None:
    from ...youtube import channel_id_in, handle_in

    return None if channel_id_in(text) else handle_in(text)


# --- the panel ---------------------------------------------------------------------------------


class YouTubePanel(Panel):
    def __init__(self, minutes: int) -> None:
        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER)
        self.member_id: int | None = None
        self.mine = True
        self.picking = False


def minutes_for(bot: Any, guild_id: int) -> int:
    return panel_minutes(bot.store, guild_id)


async def card_state(bot: Any, member: Any) -> tuple[Any, Any]:
    user_id = id_of(member)
    row = await get_link(bot.db, user_id)
    latest = await latest_video(bot.db, user_id) if row is not None else None
    return (row, latest)


def member_lines(
    bot: Any, guild: Any, member: Any, row: Any, latest: Any, *, mine: bool
) -> list[str]:
    store = bot.store
    mode = store.get(guild.id, "youtube_mode")
    lines: list[str] = []
    if row is None:
        lines.append(PANEL_INTRO if mine else THEIR_CARD.format(who=display_of(member)))
        lines.append(NOT_LINKED if mine else NOT_LINKED_FOR.format(who=display_of(member)))
    else:
        if not mine:
            lines.append(THEIR_CARD.format(who=display_of(member)))
        lines.extend(
            status_lines(
                row,
                _row_value(latest, "title"),
                where=where_words(mode, upload_channel_id(store, guild.id)),
                shorts=store.get(guild.id, "youtube_announce_shorts"),
            )
        )
    if mode == "off":
        lines.append(MODE_OFF_LINE)
    return lines


def names_of(guild: Any, rows: Any) -> dict[int, str]:
    found: dict[int, str] = {}
    for row in rows:
        user_id = int(row["user_id"])
        member = guild.get_member(user_id)
        if member is not None:
            found[user_id] = display_of(member)
    return found


async def staff_lines(bot: Any, guild: Any, rows: Any, names: dict[int, str]) -> list[str]:
    cog = cog_of(bot)
    client = getattr(cog, "client", None)
    lines = [""]
    lines.extend(
        health_lines(
            mode=bot.store.get(guild.id, "youtube_mode"),
            channel_id=upload_channel_id(bot.store, guild.id),
            minutes=bot.store.get(guild.id, "youtube_poll_minutes"),
            keyed=bool(getattr(client, "keyed", False)),
            last_ok_at=getattr(cog, "last_poll_ok_at", None),
            last_error=getattr(cog, "last_poll_error", None),
            failures=int(getattr(cog, "poll_failures", 0) or 0),
            totals=await counts(bot.db),
        )
    )
    if not getattr(client, "keyed", False):
        lines.append(NO_KEY)
    lines.extend(link_lines(rows[:SELECT_CAP], names))
    return lines


async def panel_embed(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, Any, list[Any]]:
    """The root embed, plus what the controls need: the caller's row and every linked row."""
    staff = bot.store.is_staff(actor)
    row, latest = await card_state(bot, actor)
    lines = member_lines(bot, guild, actor, row, latest, mine=True)
    rows: list[Any] = []
    if staff:
        rows = list(reversed(await all_links(bot.db)))
        lines.extend(await staff_lines(bot, guild, rows, names_of(guild, rows)))
    embed = discord.Embed(title=PANEL_TITLE, description="\n".join(lines))
    return (embed, row, rows)


async def build_panel(
    bot: Any, guild: Any, actor: Any, *, picking: bool = False
) -> tuple[discord.Embed, YouTubePanel]:
    """One command, one panel: the member's own card, and the staff half only for staff."""
    staff = bot.store.is_staff(actor)
    embed, row, rows = await panel_embed(bot, guild, actor)
    view = YouTubePanel(minutes_for(bot, guild.id))
    view.member_id = id_of(actor)
    view.mine = True
    view.picking = picking
    for move in card_buttons(linked=row is not None, mine=True, staff=staff):
        view.add_item(MoveButton(move))
    add_site_button(view, bot, row=0)
    if staff and rows:
        view.add_item(LinkedPick(rows[:SELECT_CAP], len(rows), names_of(guild, rows)))
    if staff:
        view.add_item(ModePick(bot.store.get(guild.id, "youtube_mode")))
    if staff and picking:
        view.add_item(WhoPick())
    return (embed, view)


async def build_card(
    bot: Any, guild: Any, member: Any
) -> tuple[discord.Embed, YouTubePanel]:
    row, latest = await card_state(bot, member)
    embed = discord.Embed(
        title=PANEL_TITLE,
        description="\n".join(member_lines(bot, guild, member, row, latest, mine=False)),
    )
    view = YouTubePanel(minutes_for(bot, guild.id))
    view.member_id = id_of(member)
    view.mine = False
    for move in card_buttons(linked=row is not None, mine=False, staff=True):
        view.add_item(MoveButton(move))
    add_site_button(view, bot, row=0)
    return (embed, view)


def setup_embed(bot: Any, guild: Any) -> discord.Embed:
    store = bot.store
    cog = cog_of(bot)
    client = getattr(cog, "client", None)
    lines = health_lines(
        mode=store.get(guild.id, "youtube_mode"),
        channel_id=upload_channel_id(store, guild.id),
        minutes=store.get(guild.id, "youtube_poll_minutes"),
        keyed=bool(getattr(client, "keyed", False)),
        last_ok_at=getattr(cog, "last_poll_ok_at", None),
        last_error=getattr(cog, "last_poll_error", None),
        failures=int(getattr(cog, "poll_failures", 0) or 0),
        totals={"links": 0, "videos": 0, "announced": 0},
    )[:6]
    role = store.get(guild.id, "youtube_ping_role_id")
    lines.append(f"**ping role** — {f'<@&{role}>' if role else 'nobody'}")
    lines.append(
        f"**fans pinged too** — {'yes' if store.get(guild.id, 'youtube_ping_fan_roles') else 'no'}"
    )
    lines.append(
        f"**Shorts** — "
        f"{'announced too' if store.get(guild.id, 'youtube_announce_shorts') else 'not announced'}"
    )
    lines.append(f"**words** — {store.get(guild.id, 'youtube_template')}")
    lines.append(f"**this panel stays live** — {minutes_for(bot, guild.id)} minute(s)")
    return discord.Embed(title=SETUP_TITLE, description="\n".join(lines))


def setup_view(bot: Any, guild: Any) -> YouTubePanel:
    store = bot.store
    view = YouTubePanel(minutes_for(bot, guild.id))
    view.add_item(UploadChannelPick())
    view.add_item(PingRolePick())
    for move in SETUP_MOVES:
        label = move.label
        if move.action == SHORTS:
            label = SHORTS_ON if store.get(guild.id, "youtube_announce_shorts") else SHORTS_OFF
        if move.action == FANS:
            label = FANS_ON if store.get(guild.id, "youtube_ping_fan_roles") else FANS_OFF
        view.add_item(SetupButton(move._replace(label=label)))
    add_site_button(view, bot, row=3)
    return view


# --- rendering ---------------------------------------------------------------------------------


async def render_panel(
    interaction: discord.Interaction, previous: Any = None, *, picking: bool = False
) -> None:
    bot = interaction.client
    embed, view = await build_panel(bot, interaction.guild, interaction.user, picking=picking)
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def render_card(
    interaction: discord.Interaction, member_id: Any, previous: Any = None
) -> None:
    bot = interaction.client
    guild = interaction.guild
    member = guild.get_member(int(member_id)) or int(member_id)
    embed, view = await build_card(bot, guild, member)
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def render_setup(interaction: discord.Interaction, previous: Any = None) -> None:
    bot = interaction.client
    embed = setup_embed(bot, interaction.guild)
    view = setup_view(bot, interaction.guild)
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def render_forget(interaction: discord.Interaction, previous: Any = None) -> None:
    bot = interaction.client
    embed = setup_embed(bot, interaction.guild)
    view = YouTubePanel(minutes_for(bot, interaction.guild.id))
    view.add_item(ForgetPick())
    view.add_item(SetupButton(SETUP_BACK_MOVE._replace(row=1)))
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def back_to_panel(
    interaction: discord.Interaction, previous: Any = None, *, picking: bool = False
) -> None:
    if not await opened(interaction, staff=False):
        return
    await render_panel(interaction, previous, picking=picking)


async def open_card(
    interaction: discord.Interaction, member_id: Any, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    await render_card(interaction, member_id, previous)


async def open_setup(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    await render_setup(interaction, previous)


async def open_forget(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    await render_forget(interaction, previous)


async def open_confirm(
    interaction: discord.Interaction, move: PanelMove, previous: Any = None
) -> None:
    if not await opened(interaction, staff=False):
        return
    bot = interaction.client
    embed, _row, _rows = await panel_embed(bot, interaction.guild, interaction.user)
    view = YouTubePanel(minutes_for(bot, interaction.guild.id))
    view.member_id = id_of(interaction.user)
    await confirm(
        interaction,
        view,
        embed,
        confirm_items(
            yes=move.yes,
            no=KEEP_IT,
            on_yes=lambda one, card: run_unlink(one, one.user, mine=True, previous=card),
            on_no=back_to_panel,
        ),
        previous,
        question=move.question,
    )


# --- the moves, one function each ----------------------------------------------------------------


async def run_link(
    interaction: discord.Interaction,
    member: Any,
    given: str,
    *,
    mine: bool,
    previous: Any = None,
) -> None:
    if not mine and not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    try:
        said, _row, _counted = await link_channel(
            interaction.client, interaction.guild, interaction.user, member, given
        )
    except LinkRefused as exc:
        said = str(exc)
    if mine:
        await render_panel(interaction, previous)
    else:
        await render_card(interaction, id_of(member), previous)
    await answer(interaction, said)


async def run_unlink(
    interaction: discord.Interaction,
    member: Any,
    *,
    mine: bool,
    note: Any = None,
    previous: Any = None,
) -> None:
    if not mine and not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    said, _row = await unlink_channel(
        interaction.client, interaction.guild, interaction.user, member, note=note
    )
    if mine:
        await render_panel(interaction, previous)
    else:
        await render_card(interaction, id_of(member), previous)
    await answer(interaction, said)


async def run_mode(
    interaction: discord.Interaction, value: str, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    said, _row = await set_mode(
        interaction.client, interaction.guild, interaction.user, value
    )
    await render_panel(interaction, previous)
    await answer(interaction, said)


async def run_setup(
    interaction: discord.Interaction,
    changes: dict[str, Any],
    previous: Any = None,
    *,
    forgetting: bool = False,
) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    said, _row = await save_setup(
        interaction.client, interaction.guild, interaction.user, changes
    )
    if forgetting:
        await render_forget(interaction, previous)
    else:
        await render_setup(interaction, previous)
    await answer(interaction, said)


# --- the controls ------------------------------------------------------------------------------


class MoveButton(discord.ui.Button):
    def __init__(self, move: PanelMove) -> None:
        super().__init__(label=move.label, style=STYLES[move.style], row=move.row)
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        action = self.move.action
        if action == REFRESH:
            if view.mine:
                await back_to_panel(interaction, view)
            else:
                await open_card(interaction, view.member_id, view)
            return
        if action == BACK:
            await back_to_panel(interaction, view)
            return
        if action == LOGS:
            await send_logs(interaction, "youtube")
            return
        if action == SETUP:
            await open_setup(interaction, view)
            return
        if action == LINK_FOR:
            if not await still_staff(interaction):
                return
            await back_to_panel(interaction, view, picking=True)
            return
        if action == UNLINK:
            await open_confirm(interaction, self.move, view)
            return
        if action == UNLINK_FOR:
            if not await still_staff(interaction):
                return
            if not await db_up(interaction):
                return
            await interaction.response.send_modal(UnlinkForModal(view.member_id, view))
            return
        if action in (LINK, RELINK):
            if not await db_up(interaction):
                return
            row = await get_link(interaction.client.db, id_of(interaction.user))
            await interaction.response.send_modal(
                LinkModal(interaction.user, mine=True, previous=view, given=given_of(row))
            )
            return
        if not await still_staff(interaction):
            return
        if not await db_up(interaction):
            return
        member = interaction.guild.get_member(int(view.member_id)) or int(view.member_id)
        row = await get_link(interaction.client.db, id_of(member))
        await interaction.response.send_modal(
            LinkModal(member, mine=False, previous=view, given=given_of(row))
        )


def given_of(row: Any) -> str | None:
    handle = _row_value(row, "handle")
    return str(handle) if handle else (_row_value(row, "channel_id") or None)


class LinkedPick(discord.ui.Select):
    def __init__(self, rows: Any, total: int, names: dict[int, str]) -> None:
        shown = list(rows)
        super().__init__(
            placeholder=capped_placeholder(len(shown), total, pick=PICK_A_CHANNEL),
            options=[
                discord.SelectOption(
                    label=option_label(
                        spot + 1,
                        None,
                        f"{names.get(int(row['user_id'])) or row['user_id']} — "
                        f"{row['title'] or row['channel_id']}",
                    ),
                    value=str(row["user_id"]),
                )
                for spot, row in enumerate(shown)
            ],
            min_values=1,
            max_values=1,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_card(interaction, int(self.values[0]), self.view)


class ModePick(discord.ui.Select):
    def __init__(self, current: str) -> None:
        super().__init__(
            placeholder=MODE_PLACEHOLDER,
            options=[
                discord.SelectOption(
                    label=MODE_LABELS[name], value=name, default=(name == current)
                )
                for name in YOUTUBE_MODES
            ],
            min_values=1,
            max_values=1,
            row=2,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_mode(interaction, self.values[0], self.view)


class WhoPick(discord.ui.UserSelect):
    def __init__(self) -> None:
        super().__init__(placeholder=WHOSE_CHANNEL, min_values=1, max_values=1, row=4)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        if not await db_up(interaction):
            return
        member = self.values[0]
        row = await get_link(interaction.client.db, id_of(member))
        await interaction.response.send_modal(
            LinkModal(member, mine=False, previous=self.view, given=given_of(row))
        )


class UploadChannelPick(discord.ui.ChannelSelect):
    def __init__(self) -> None:
        super().__init__(
            placeholder=WHERE_UPLOADS,
            channel_types=[discord.ChannelType.text],
            min_values=0,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        picked = int(self.values[0].id) if self.values else None
        await run_setup(interaction, {"youtube_channel_id": picked}, self.view)


class PingRolePick(discord.ui.RoleSelect):
    def __init__(self) -> None:
        super().__init__(placeholder=WHO_IS_PINGED, min_values=0, max_values=1, row=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        picked = int(self.values[0].id) if self.values else None
        await run_setup(interaction, {"youtube_ping_role_id": picked}, self.view)


class ForgetPick(discord.ui.Select):
    """Events deviation 6: a client that will not submit an empty picker still has a way out."""

    def __init__(self) -> None:
        super().__init__(
            placeholder=FORGET_PLACEHOLDER,
            options=[
                discord.SelectOption(label=FORGET_CHANNEL, value="youtube_channel_id"),
                discord.SelectOption(label=FORGET_PING_ROLE, value="youtube_ping_role_id"),
            ],
            min_values=1,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_setup(interaction, {self.values[0]: None}, self.view, forgetting=True)


class SetupButton(discord.ui.Button):
    def __init__(self, move: PanelMove) -> None:
        super().__init__(label=move.label, style=STYLES[move.style], row=move.row)
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        action = self.move.action
        if action == BACK:
            if self.move.row == 1:
                await open_setup(interaction, self.view)
            else:
                await back_to_panel(interaction, self.view)
            return
        if action == FORGET:
            await open_forget(interaction, self.view)
            return
        store = interaction.client.store
        guild_id = interaction.guild.id
        if action == SHORTS:
            await run_setup(
                interaction,
                {"youtube_announce_shorts": not store.get(guild_id, "youtube_announce_shorts")},
                self.view,
            )
            return
        if action == FANS:
            await run_setup(
                interaction,
                {"youtube_ping_fan_roles": not store.get(guild_id, "youtube_ping_fan_roles")},
                self.view,
            )
            return
        if not await still_staff(interaction):
            return
        if not await db_up(interaction):
            return
        if action == WORDS:
            await interaction.response.send_modal(
                WordsModal(store.get(guild_id, "youtube_template"), self.view)
            )
            return
        await interaction.response.send_modal(
            NumbersModal(
                store.get(guild_id, "youtube_poll_minutes"),
                minutes_for(interaction.client, guild_id),
                self.view,
            )
        )


# --- the modals --------------------------------------------------------------------------------


class LinkModal(AnswersErrors, discord.ui.Modal):
    channel = discord.ui.TextInput(label=LINK_LABEL, max_length=LINK_LIMIT)

    def __init__(
        self, member: Any, *, mine: bool, previous: Any = None, given: Any = None
    ) -> None:
        title = LINK_TITLE if mine else LINK_FOR_TITLE.format(who=display_of(member))
        super().__init__(title=title[:45])
        self.member = member
        self.mine = mine
        self.previous = previous
        self.channel.label = LINK_LABEL if mine else LINK_FOR_LABEL
        self.channel.default = str(given) if given else None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_link(
            interaction,
            self.member,
            str(self.channel),
            mine=self.mine,
            previous=self.previous,
        )


class UnlinkForModal(NoteModal):
    def __init__(self, member_id: Any, previous: Any = None) -> None:
        self.member_id = member_id
        self.previous = previous
        super().__init__(
            title=UNLINK_FOR_TITLE,
            label=UNLINK_FOR_LABEL,
            max_length=NOTE_LIMIT,
            on_submit=self.reason_given,
            required=False,
        )

    async def reason_given(self, interaction: discord.Interaction, note: str) -> None:
        member = interaction.guild.get_member(int(self.member_id)) or int(self.member_id)
        await run_unlink(
            interaction, member, mine=False, note=note, previous=self.previous
        )


class WordsModal(AnswersErrors, discord.ui.Modal):
    words = discord.ui.TextInput(
        label=WORDS_LABEL, style=discord.TextStyle.paragraph, max_length=TEMPLATE_LIMIT
    )

    def __init__(self, current: Any, previous: Any = None) -> None:
        super().__init__(title=WORDS_TITLE[:45])
        self.previous = previous
        self.words.default = str(current or "")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_setup(interaction, {"youtube_template": str(self.words)}, self.previous)


class NumbersModal(AnswersErrors, discord.ui.Modal):
    every = discord.ui.TextInput(label=EVERY_LABEL, max_length=5)
    stays = discord.ui.TextInput(label=PANEL_MINUTES_LABEL, max_length=5)

    def __init__(self, poll: Any, panel: Any, previous: Any = None) -> None:
        super().__init__(title=NUMBERS_TITLE[:45])
        self.previous = previous
        self.every.default = str(poll)
        self.stays.default = str(panel)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """A modal has no Range, so the floor is checked here and refused in words."""
        changes: dict[str, Any] = {}
        for field, key, label, floor in (
            (self.every, "youtube_poll_minutes", EVERY_LABEL, YOUTUBE_POLL_MIN_MINUTES),
            (self.stays, PANEL_MINUTES_KEY, PANEL_MINUTES_LABEL, 1),
        ):
            given = str(field).strip()
            if not given.isdigit():
                await answer(
                    interaction,
                    NOT_A_NUMBER.format(given=given[:40] or "nothing", label=label, floor=floor),
                )
                return
            changes[key] = int(given)
        await run_setup(interaction, changes, self.previous)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(YouTube(bot))


__all__ = [
    "ALREADY_LINKED",
    "LINKED",
    "LINKED_NOT_SEEDED",
    "MODE_OFF_LINE",
    "NOBODY_LINKED",
    "NOT_LINKED",
    "NOT_LINKED_FOR",
    "NOT_SEEDED_YET",
    "NO_KEY",
    "SETUP_NOTHING",
    "UNLINKED",
    "UNLINKED_FOR",
    "ForgetPick",
    "LinkModal",
    "LinkRefused",
    "LinkedPick",
    "ModePick",
    "MoveButton",
    "NumbersModal",
    "PingRolePick",
    "SetupButton",
    "UnlinkForModal",
    "UploadChannelPick",
    "WhoPick",
    "WordsModal",
    "YouTube",
    "YouTubePanel",
    "all_links",
    "back_to_panel",
    "build_card",
    "build_panel",
    "counts",
    "get_link",
    "latest_video",
    "link_channel",
    "link_owner",
    "recent_videos",
    "remove_link",
    "render_panel",
    "save_setup",
    "set_link",
    "set_mode",
    "setup_view",
    "setup_words",
    "tell_unlinked",
    "unlink_channel",
    "upload_channel_id",
]
