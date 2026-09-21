from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ...actionlog import log_action, send_logs
from ...command_errors import AnswersErrors
from ...golive import YOUTUBE, joins_session, now_iso
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
    GOLIVE_COSTREAM_MODE_KEY,
    GUILD_ONLY,
    YOUTUBE_LIVE_MODES,
    YOUTUBE_LIVE_POLL_MINUTES,
    SettingError,
)
from ...youtube import (
    BACK,
    KEEP_IT,
    LINK,
    LINK_FOR,
    LOGS,
    NOBODY_LINKED,
    PANEL_TIMEOUT_FOOTER,
    PANEL_TITLE,
    REFRESH,
    RELINK,
    SELECT_CAP,
    UNLINK,
    UNLINK_FOR,
    PanelMove,
    YouTubeClient,
    YouTubeError,
    card_buttons,
    health_lines,
    link_lines,
    panel_minutes,
    status_lines,
    where_words,
)
from ...youtube_live import (
    CONFIRM_UNITS,
    LIVE_ID_UNKNOWN,
    LIVE_URL,
    SEARCH_UNITS,
    UNREADABLE_EVERY_SECONDS,
    after_probe,
    channel_info,
    is_over,
    stream_info,
)

log = logging.getLogger(__name__)

COG_NAME = "YouTube"
GOLIVE_COG = "GoLive"
YOUTUBE_SOURCE = "youtube"
OPEN_SESSION_BECAUSE = "open_session:{source}"
JOINED_BECAUSE = "joined_session"
UNKNOWN_SOURCE = "unknown"
GO_LIVE_DOOR = "go_live"
ADD_PLATFORM_DOOR = "add_platform"
NO_KEY = (
    "youtube: no YOUTUBE_API_KEY, so a live stream is announced from the channel's own live "
    "page alone — the post's title reads Live now and no video id is searched for"
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
    "Linked **{title}** to you. Black Bloc watches it and posts when you go live. **Unlink** "
    "on this panel undoes it."
)
LINKED_FOR = "Linked **{title}** to {who}. Black Bloc posts when that channel goes live."
UNLINKED = (
    "Done — Black Bloc has forgotten your YouTube channel and will not announce your live "
    "streams."
)
UNLINKED_FOR = (
    "Done — **{who}**'s YouTube channel is forgotten and their live streams are not announced."
)
UNLINKED_DM = (
    "A Lead has removed the YouTube channel Black Bloc had linked to you in **{guild}**, so "
    "your live streams are no longer announced there. You can link one again with `/youtube`."
)
UNLINKED_DM_WHY = "\n\nWhat they said: {why}"
LIVE_MODE_OFF_NOTE = (
    " Live-stream announcements are **off** at the moment, so nothing is posted until a Lead "
    "sets **Live streams are…** on this panel to shadow or on."
)
LIVE_MODE_OFF_LINE = (
    "Live-stream announcements are **off** for this server at the moment, so nothing is posted. "
    "Linking is still worth doing — it is your own opt-in, and the mode is the server's switch. "
    "A Lead changes it with **Live streams are…** on this panel."
)
LIVE_MODE_SET = "Live-stream announcements are now **{mode}**."
LIVE_MODE_PLACEHOLDER = "Live streams are…"
LIVE_MODE_LABELS = {
    "off": "off — linked channels are not checked for live streams",
    "shadow": "shadow — the probe runs and logs, nothing else changes",
    "on": "on — a linked channel going live is announced",
}
LIVE_NO_GOLIVE_CHANNEL = (
    "A live stream is announced through the go-live feature, and `golive_channel_id` is not set, "
    "so there is nowhere to post one yet. **Setup** on `/golive` picks a channel."
)
LIVE_GOLIVE_NOT_ON = (
    "Go-live announcements are **{mode}** at the moment, and a YouTube stream is announced "
    "through them — so nothing is posted until `golive_mode` is on."
)
FEATURE_MISSING = (
    "The YouTube feature is not loaded right now, so nothing was changed. Tell a Lead — the "
    "bot needs a restart."
)


PANEL_INTRO = (
    "Tell Black Bloc where your YouTube channel is and it posts when you go live, in the same "
    "place a Twitch stream is announced."
)
SITE_BUTTON = "Open on the site"
FEATURE = "youtube"
PICK_A_CHANNEL = "Somebody's channel…"
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

STYLES = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}


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


def live_seen_details(channel_id: str, video_id: Any, probe: Any, mode: str) -> dict[str, Any]:
    """The facts every `youtube.live_seen` row carries, announced or not."""
    return {
        "channel_id": channel_id,
        "video_id": video_id,
        "botcheck": bool(getattr(probe, "botcheck", False)),
        "mode": mode,
    }


def cog_of(bot: Any) -> Any:
    getter = getattr(bot, "get_cog", None)
    return getter(COG_NAME) if callable(getter) else None


def display_of(member: Any) -> str:
    return str(
        getattr(member, "display_name", None) or getattr(member, "name", None) or member
    )


def id_of(member: Any) -> int:
    return int(getattr(member, "id", member) or 0)


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
        "INSERT OR REPLACE INTO youtube_links(user_id, channel_id, handle, title, linked_at) "
        "VALUES (?, ?, ?, ?, ?)",
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


async def counts(db: Any) -> dict[str, int]:
    cur = await db.conn.execute("SELECT COUNT(*) AS n FROM youtube_links")
    row = await cur.fetchone()
    return {"links": int(row["n"]) if row else 0}


async def link_channel(
    bot: Any,
    guild: Any,
    actor: Any,
    member: Any,
    given: Any,
    *,
    via: str = VIA_DISCORD,
    because: str | None = None,
    via_video: bool = False,
) -> tuple[str, Any]:
    """Resolve, refuse a channel somebody else owns, store — one write, one log row."""
    cog = cog_of(bot)
    if cog is None:
        return (FEATURE_MISSING, None)
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
    await set_link(bot.db, user_id, channel_id, _handle_of(str(given)), title)
    row = await get_link(bot.db, user_id)
    named = title or channel_id
    who = display_of(member)
    said = (LINKED if mine else LINKED_FOR).format(title=named, who=who)
    if mine and bot.store.get(guild.id, "youtube_live_mode") == "off":
        said += LIVE_MODE_OFF_NOTE
    await log_action(
        bot,
        guild,
        kind_via("youtube.link", via),
        actor=actor,
        target=member,
        details={"title": title, "via": via}
        | ({"because": because} if because else {})
        | ({"via_video": True} if via_video else {}),
    )
    return (said, row)


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


async def set_live_mode(
    bot: Any, guild: Any, actor: Any, value: str, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    """The live half's own switch; go-live still decides whether anything is posted."""
    try:
        await bot.store.set(guild.id, "youtube_live_mode", value, by=id_of(actor) or None)
    except SettingError as exc:
        return (str(exc), None)
    extra = ""
    if value != "off":
        golive_mode = bot.store.get(guild.id, "golive_mode")
        if not bot.store.get(guild.id, "golive_channel_id"):
            extra = f" {LIVE_NO_GOLIVE_CHANNEL}"
        elif golive_mode != "on":
            extra = f" {LIVE_GOLIVE_NOT_ON.format(mode=golive_mode)}"
    await log_action(
        bot,
        guild,
        kind_via("youtube.live_mode", via),
        actor=actor,
        details={"mode": value, "via": via},
    )
    return (LIVE_MODE_SET.format(mode=value) + extra, None)


class YouTube(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.client = YouTubeClient(getattr(bot.settings, "youtube_api_key", None))
        self.last_probe_at: str | None = None
        self.last_probe_error: str | None = None
        self.probed = 0
        self.confirms = 0
        self.confirms_day = ""
        self.live_misses: dict[str, int] = {}
        self.live_video: dict[str, str] = {}
        self.unreadable_at: dict[str, datetime] = {}
        self.last_botcheck = False

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name == "live_poller":
            return (self.last_probe_at, self.last_probe_error)
        return (None, None)

    async def cog_load(self) -> None:
        if not self.client.keyed:
            log.info(NO_KEY)
        if not self.bot.db.is_connected:
            return
        self.live_poller.start()

    async def cog_unload(self) -> None:
        self.live_poller.cancel()
        await self.client.close()

    # --- the live probe ----------------------------------------------------------------------

    @tasks.loop(minutes=1)
    async def live_poller(self) -> None:
        try:
            await self.probe_all()
        except Exception as exc:
            self.last_probe_error = f"{type(exc).__name__}: {exc}"
            log.exception("youtube: the live probe failed")
        self._retime_live()

    @live_poller.before_loop
    async def _before_live_poller(self) -> None:
        if await wait_ready(self.bot, self._live_poller_stopped):
            self._retime_live()

    @live_poller.error
    async def _live_poller_stopped(self, exc: BaseException) -> None:
        """The loop stops for the life of the process unless it is started again."""
        self.last_probe_error = f"{type(exc).__name__}: {exc}"
        log.error("youtube: the live probe stopped; restarting it", exc_info=exc)
        self.live_poller.restart()

    def _retime_live(self) -> None:
        wanted = self._live_minutes()
        if self.live_poller.minutes != wanted:
            self.live_poller.change_interval(minutes=wanted)

    def _live_minutes(self) -> int:
        guild = next(iter(getattr(self.bot, "guilds", ()) or ()), None)
        if guild is None:
            return YOUTUBE_LIVE_POLL_MINUTES
        return max(1, int(self.bot.store.get(guild.id, "youtube_live_poll_minutes")))

    async def probe_all(self) -> None:
        """One live sweep of every linked channel whose server has the live half switched on."""
        if not self.bot.db.is_connected:
            return
        worked = 0
        failed: str | None = None
        for row in await self._pollable():
            member = self._find_member(int(row["user_id"]))
            if member is None:
                continue
            mode = self._live_mode(member.guild.id)
            if mode == "off":
                continue
            channel_id = str(row["channel_id"])
            try:
                probe = await self.client.probe_live(channel_id)
            except YouTubeError as exc:
                failed = str(exc)
                log.warning("youtube: could not probe %s for a live stream: %s", channel_id, exc)
                continue
            worked += 1
            self.probed += 1
            self.last_botcheck = bool(getattr(probe, "botcheck", False))
            await self._probed(member, channel_id, probe, mode)
        channels, channel_failed = await self._probe_channels()
        worked += channels
        if worked:
            self.last_probe_at = now_iso()
        self.last_probe_error = failed or channel_failed

    async def _probe_channels(self) -> tuple[int, str | None]:
        """The same sweep over channel rows — a streamer with no member is still a streamer."""
        from .spotlight import channels_with_youtube

        worked = 0
        failed: str | None = None
        for row in await channels_with_youtube(self.bot.db):
            guild = self._guild_of(int(row["guild_id"]))
            if guild is None:
                continue
            mode = self._live_mode(guild.id)
            if mode == "off":
                continue
            channel_id = str(row["youtube_channel_id"])
            try:
                probe = await self.client.probe_live(channel_id)
            except YouTubeError as exc:
                failed = str(exc)
                log.warning("youtube: could not probe channel %s: %s", channel_id, exc)
                continue
            worked += 1
            self.probed += 1
            self.last_botcheck = bool(getattr(probe, "botcheck", False))
            if probe.live:
                await self._channel_live(guild, row, channel_id, probe, mode)
            else:
                await self._channel_not_live(guild, row, channel_id)
        return (worked, failed)

    def _guild_of(self, guild_id: int) -> Any:
        for guild in getattr(self.bot, "guilds", ()) or ():
            if int(getattr(guild, "id", 0)) == guild_id:
                return guild
        return None

    async def _channel_live(
        self, guild: Any, row: Any, channel_id: str, probe: Any, mode: str
    ) -> None:
        """One session per channel row: whichever side sees it first opens it, and the other
        side notes it rather than announcing the same stream twice."""
        from ... import spotlight as spot
        from . import spotlight as spot_cog

        self.live_misses[channel_id] = 0
        known = self.live_video.get(channel_id)
        if known is not None and (probe.video_id is None or known == probe.video_id):
            return
        cog = spot_cog.cog_of(self.bot)
        open_row = await spot_cog.open_session(self.bot.db, row["id"])
        self.live_video[channel_id] = probe.video_id or LIVE_ID_UNKNOWN
        if open_row is not None:
            await self._channel_seen(guild, row, channel_id, probe, mode, joined=True)
            return
        info = (
            stream_info(probe.video_id, "", "")
            if probe.video_id
            else channel_info(channel_id)
        )
        await self._channel_seen(guild, row, channel_id, probe, mode, url=info.url)
        if cog is None:
            log.warning(
                "youtube: the spotlight cog is not loaded; %s is not announced", channel_id
            )
            return
        async with cog._lock(row["id"]):
            fresh = await spot_cog.channel_by_id(self.bot.db, row["id"])
            if fresh is None or await spot_cog.open_session(self.bot.db, row["id"]):
                return
            await cog.announce_info(guild, fresh, info, spot.display_for(fresh))

    async def _channel_seen(
        self,
        guild: Any,
        row: Any,
        channel_id: str,
        probe: Any,
        mode: str,
        *,
        joined: bool = False,
        url: str | None = None,
    ) -> None:
        details = live_seen_details(channel_id, probe.video_id, probe, mode) | {
            "spotlight_id": row["id"],
            "login": row["twitch_login"],
            "announced": not joined,
        }
        if joined:
            details["because"] = JOINED_BECAUSE
        if url:
            details["url"] = url
        await log_action(
            self.bot,
            guild,
            "youtube.live_seen" if mode == "on" else "youtube.would_live_seen",
            details=details,
        )

    async def _channel_not_live(self, guild: Any, row: Any, channel_id: str) -> None:
        """Only the side that opened the session ends it; a Twitch one is the Twitch sweep's."""
        from ... import spotlight as spot
        from . import spotlight as spot_cog

        misses = after_probe(self.live_misses.get(channel_id), False)
        self.live_misses[channel_id] = misses
        if not is_over(misses, self._end_misses(guild.id)):
            return
        self.live_misses[channel_id] = 0
        self.live_video.pop(channel_id, None)
        cog = spot_cog.cog_of(self.bot)
        session = await spot_cog.open_session(self.bot.db, row["id"])
        if cog is None or session is None:
            return
        if spot.platform_of(session["url"]) != spot.YOUTUBE:
            return
        async with cog._lock(row["id"]):
            fresh = await spot_cog.open_session(self.bot.db, row["id"])
            if fresh is None:
                return
            await cog._end(guild, row, fresh, spot.ENDED)

    async def _probed(self, member: Any, channel_id: str, probe: Any, mode: str) -> None:
        if not probe.readable:
            await self._unreadable(member, channel_id)
        if probe.live:
            await self._live_now(member, channel_id, probe, mode)
            return
        await self._not_live(member, channel_id)

    async def _unreadable(self, member: Any, channel_id: str) -> None:
        """A page that changed shape says so once an hour and reads as offline — never a raise."""
        now = datetime.now(UTC)
        last = self.unreadable_at.get(channel_id)
        if last is not None and (now - last).total_seconds() < UNREADABLE_EVERY_SECONDS:
            return
        self.unreadable_at[channel_id] = now
        log.warning(
            "youtube: %s's live page was not the shape the probe reads; taking it as offline",
            channel_id,
        )
        await log_action(
            self.bot,
            member.guild,
            "youtube.probe_unreadable",
            target=member,
            details={
                "channel_id": channel_id,
                "url": LIVE_URL.format(channel_id=channel_id),
            },
        )

    async def _live_now(self, member: Any, channel_id: str, probe: Any, mode: str) -> None:
        self.live_misses[channel_id] = 0
        known = self.live_video.get(channel_id)
        if known is not None and (probe.video_id is None or known == probe.video_id):
            return
        guild = member.guild
        open_session = await self._any_open_session(guild, member)
        joins = open_session is not None and joins_session(
            open_session, YOUTUBE, self.bot.store.get(guild.id, GOLIVE_COSTREAM_MODE_KEY)
        )
        if open_session is not None and not joins:
            if known is None:
                await self._live_seen(
                    guild,
                    member,
                    live_seen_details(channel_id, probe.video_id, probe, mode)
                    | {
                        "announced": False,
                        "because": OPEN_SESSION_BECAUSE.format(
                            source=_row_value(open_session, "source") or UNKNOWN_SOURCE
                        ),
                    },
                    mode,
                )
            self.live_video[channel_id] = probe.video_id or LIVE_ID_UNKNOWN
            return
        video_id = probe.video_id or await self._searched(guild, member, channel_id)
        confirmed = await self._confirm(guild, member, video_id) if video_id else None
        self.live_video[channel_id] = video_id or LIVE_ID_UNKNOWN
        if confirmed is not None and not confirmed.live:
            return
        info = (
            stream_info(
                video_id,
                getattr(confirmed, "title", ""),
                getattr(confirmed, "thumbnail", ""),
            )
            if video_id
            else channel_info(channel_id)
        )
        await self._live_seen(
            guild,
            member,
            live_seen_details(channel_id, video_id, probe, mode)
            | {
                "url": info.url,
                "title": info.title,
                "confirmed": confirmed is not None,
                "announced": True,
            }
            | ({"because": JOINED_BECAUSE} if joins else {}),
            mode,
        )
        await (
            self._add_platform(guild, member, info)
            if joins
            else self._go_live(guild, member, info)
        )

    async def _live_seen(
        self, guild: Any, member: Any, details: dict[str, Any], mode: str
    ) -> None:
        await log_action(
            self.bot,
            guild,
            "youtube.live_seen" if mode == "on" else "youtube.would_live_seen",
            target=member,
            details=details,
        )

    async def _searched(self, guild: Any, member: Any, channel_id: str) -> str | None:
        """100 units, on the transition only: the bot-check page carries no canonical link."""
        if not getattr(self.client, "keyed", False):
            return None
        self._spent(SEARCH_UNITS)
        try:
            found = await self.client.search_live(channel_id)
        except YouTubeError as exc:
            log.warning("youtube: could not search %s for its live video: %s", channel_id, exc)
            await log_action(
                self.bot,
                guild,
                "youtube.live_search_failed",
                target=member,
                details={"channel_id": channel_id, "units": SEARCH_UNITS, "reason": str(exc)},
            )
            return None
        await log_action(
            self.bot,
            guild,
            "youtube.live_id_searched",
            target=member,
            details={"channel_id": channel_id, "units": SEARCH_UNITS, "video_id": found},
        )
        return found

    async def _not_live(self, member: Any, channel_id: str) -> None:
        guild = member.guild
        misses = after_probe(self.live_misses.get(channel_id), False)
        self.live_misses[channel_id] = misses
        if not is_over(misses, self._end_misses(guild.id)):
            return
        self.live_misses[channel_id] = 0
        self.live_video.pop(channel_id, None)
        await self._end_live(guild, member)

    async def _confirm(self, guild: Any, member: Any, video_id: Any) -> Any:
        """One unit, only where a key exists; a refusal is said out loud and announced anyway."""
        if not getattr(self.client, "keyed", False):
            return None
        self._spent(CONFIRM_UNITS)
        try:
            return await self.client.confirm_live(video_id)
        except YouTubeError as exc:
            log.warning("youtube: could not confirm the live stream %s: %s", video_id, exc)
            await log_action(
                self.bot,
                guild,
                "youtube.live_confirm_failed",
                target=member,
                details={"video_id": str(video_id), "reason": str(exc)},
            )
            return None

    def _spent(self, units: int = CONFIRM_UNITS) -> None:
        today = datetime.now(UTC).date().isoformat()
        if self.confirms_day != today:
            self.confirms_day = today
            self.confirms = 0
        self.confirms += int(units)

    async def _go_live(self, guild: Any, member: Any, info: Any) -> None:
        await self._hand_off(guild, member, info, GO_LIVE_DOOR)

    async def _add_platform(self, guild: Any, member: Any, info: Any) -> None:
        await self._hand_off(guild, member, info, ADD_PLATFORM_DOOR)

    async def _hand_off(self, guild: Any, member: Any, info: Any, door: str) -> None:
        goer = getattr(self._golive(), door, None)
        if goer is None:
            log.warning(
                "youtube: the go-live cog is not loaded; %s's stream is not announced", member.id
            )
            await log_action(
                self.bot,
                guild,
                "youtube.live_announce_failed",
                target=member,
                details={"url": info.url, "reason": "golive_cog_missing"},
            )
            return
        await goer(member, info, YOUTUBE_SOURCE)

    async def _end_live(self, guild: Any, member: Any) -> None:
        ender = getattr(self._golive(), "end_live", None)
        if ender is None:
            log.warning(
                "youtube: the go-live cog is not loaded; %s's session is left open", member.id
            )
            return
        await ender(guild, member, YOUTUBE_SOURCE)

    def _golive(self) -> Any:
        getter = getattr(self.bot, "get_cog", None)
        return getter(GOLIVE_COG) if callable(getter) else None

    async def _any_open_session(self, guild: Any, member: Any) -> Any:
        from .golive import open_session_for

        return await open_session_for(self.bot.db, guild.id, member.id)

    async def is_live_now(self, user_id: Any) -> bool | None:
        """Go-live's reconcile asks this; None means the probe could not answer, not 'offline'."""
        row = await get_link(self.bot.db, int(user_id))
        channel_id = _row_value(row, "channel_id")
        if not channel_id:
            return False
        try:
            probe = await self.client.probe_live(str(channel_id))
        except YouTubeError as exc:
            log.warning(
                "youtube: could not check whether %s is still live (%s)", channel_id, exc
            )
            return None
        return probe.live if probe.readable else None

    def _live_mode(self, guild_id: int) -> str:
        return self.bot.store.get(guild_id, "youtube_live_mode")

    def _end_misses(self, guild_id: int) -> int:
        return int(self.bot.store.get(guild_id, "youtube_live_end_misses"))

    async def _pollable(self) -> list[Any]:
        """One row per channel; a channel linked twice is probed for the first member only."""
        by_channel: dict[str, Any] = {}
        for row in await all_links(self.bot.db):
            channel_id = str(row["channel_id"])
            if channel_id in by_channel:
                log.warning(
                    "youtube: channel %s is linked to both %s and %s; only the first is probed",
                    channel_id,
                    by_channel[channel_id]["user_id"],
                    row["user_id"],
                )
                continue
            by_channel[channel_id] = row
        return list(by_channel.values())

    def _find_member(self, user_id: int) -> Any:
        for guild in self.bot.guilds:
            member = guild.get_member(user_id)
            if member is not None:
                return member
        return None

    # --- the command -------------------------------------------------------------------------

    @app_commands.command(
        name="youtube",
        description="Your YouTube channel, and whether your live streams are announced",
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


async def card_state(bot: Any, member: Any) -> Any:
    return await get_link(bot.db, id_of(member))


def member_lines(bot: Any, guild: Any, member: Any, row: Any, *, mine: bool) -> list[str]:
    store = bot.store
    mode = store.get(guild.id, "youtube_live_mode")
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
                where=where_words(
                    mode,
                    store.get(guild.id, "golive_mode"),
                    store.get(guild.id, "golive_channel_id"),
                ),
            )
        )
    if mode == "off":
        lines.append(LIVE_MODE_OFF_LINE)
    return lines


def names_of(guild: Any, rows: Any) -> dict[int, str]:
    found: dict[int, str] = {}
    for row in rows:
        user_id = int(row["user_id"])
        member = guild.get_member(user_id)
        if member is not None:
            found[user_id] = display_of(member)
    return found


async def live_health(bot: Any, guild: Any) -> dict[str, Any]:
    """One reading, read by the panel and by the site, so the two cannot say different things."""
    from .golive import open_sessions

    cog = cog_of(bot)
    store = bot.store
    reading = sorted(str(one) for one in (getattr(cog, "live_video", None) or {}))
    open_now = 0
    if getattr(bot.db, "is_connected", False):
        open_now = len(
            [
                row
                for row in await open_sessions(bot.db, guild.id)
                if str(_row_value(row, "source") or "") == YOUTUBE_SOURCE
            ]
        )
    return {
        "mode": store.get(guild.id, "youtube_live_mode"),
        "minutes": store.get(guild.id, "youtube_live_poll_minutes"),
        "misses": store.get(guild.id, "youtube_live_end_misses"),
        "last_probe_at": getattr(cog, "last_probe_at", None),
        "last_probe_error": getattr(cog, "last_probe_error", None)
        or (None if cog is not None else FEATURE_MISSING),
        "probed": int(getattr(cog, "probed", 0) or 0),
        "quota": int(getattr(cog, "confirms", 0) or 0),
        "botcheck": bool(getattr(cog, "last_botcheck", False)),
        "open": open_now,
        "reading_live": len(reading),
        "reading_live_channels": reading,
    }


async def staff_lines(bot: Any, guild: Any, rows: Any, names: dict[int, str]) -> list[str]:
    cog = cog_of(bot)
    client = getattr(cog, "client", None)
    lines = [""]
    lines.extend(
        health_lines(
            keyed=bool(getattr(client, "keyed", False)),
            links=(await counts(bot.db))["links"],
            live=await live_health(bot, guild),
        )
    )
    if not getattr(client, "keyed", False):
        lines.append(NO_KEY)
    lines.extend(link_lines(rows[:SELECT_CAP], names))
    return lines


async def panel_embed(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, Any, list[Any]]:
    """The root embed, plus what the controls need: the caller's row and every linked row."""
    staff = bot.store.is_staff(actor)
    row = await card_state(bot, actor)
    lines = member_lines(bot, guild, actor, row, mine=True)
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
    if staff and picking:
        view.add_item(WhoPick())
    elif staff:
        view.add_item(LiveModePick(bot.store.get(guild.id, "youtube_live_mode")))
    return (embed, view)


async def build_card(
    bot: Any, guild: Any, member: Any
) -> tuple[discord.Embed, YouTubePanel]:
    row = await card_state(bot, member)
    embed = discord.Embed(
        title=PANEL_TITLE,
        description="\n".join(member_lines(bot, guild, member, row, mine=False)),
    )
    view = YouTubePanel(minutes_for(bot, guild.id))
    view.member_id = id_of(member)
    view.mine = False
    for move in card_buttons(linked=row is not None, mine=False, staff=True):
        view.add_item(MoveButton(move))
    add_site_button(view, bot, row=0)
    return (embed, view)


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
        said, _row = await link_channel(
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


async def run_live_mode(
    interaction: discord.Interaction, value: str, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    said, _row = await set_live_mode(
        interaction.client, interaction.guild, interaction.user, value
    )
    await render_panel(interaction, previous)
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


class LiveModePick(discord.ui.Select):
    """Row 4 is the picker's row, so this stands down while staff are choosing a member."""

    def __init__(self, current: str) -> None:
        super().__init__(
            placeholder=LIVE_MODE_PLACEHOLDER,
            options=[
                discord.SelectOption(
                    label=LIVE_MODE_LABELS[name], value=name, default=(name == current)
                )
                for name in YOUTUBE_LIVE_MODES
            ],
            min_values=1,
            max_values=1,
            row=4,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_live_mode(interaction, self.values[0], self.view)


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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(YouTube(bot))


__all__ = [
    "ALREADY_LINKED",
    "LINKED",
    "LIVE_MODE_OFF_LINE",
    "NOBODY_LINKED",
    "NOT_LINKED",
    "NOT_LINKED_FOR",
    "NO_KEY",
    "UNLINKED",
    "UNLINKED_FOR",
    "LinkModal",
    "LinkRefused",
    "LinkedPick",
    "LiveModePick",
    "MoveButton",
    "UnlinkForModal",
    "WhoPick",
    "YouTube",
    "YouTubePanel",
    "all_links",
    "back_to_panel",
    "build_card",
    "build_panel",
    "counts",
    "get_link",
    "link_channel",
    "link_owner",
    "live_health",
    "remove_link",
    "render_panel",
    "set_link",
    "set_live_mode",
    "tell_unlinked",
    "unlink_channel",
]
