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

from ... import pings
from ...actionlog import log_action, send_logs
from ...command_errors import AnswersErrors
from ...golive import (
    END_GRACE_SECONDS,
    PANEL_TIMEOUT_FOOTER,
    PANEL_TITLE,
    POLL_SECONDS,
    SITE_BUTTON,
    TWITCH,
    YOUTUBE,
    StreamInfo,
    announcement_embed,
    card_lines,
    edits_on_end,
    embed_summary,
    end_details,
    end_summary,
    ended_embed,
    ended_text,
    enriched,
    extract_stream,
    from_twitch,
    now_iso,
    panel_buttons,
    panel_minutes,
    parse_ts,
    passes_role_filters,
    render,
    should_announce,
    site_page_url,
    twitch_enrichable,
    twitch_login_from_url,
    with_box_art,
)
from ...logkinds import VIA_DISCORD, kind_via
from ...panels import (
    SELECT_OPTION_LIMIT,
    Panel,
    answer,
    capped_placeholder,
    opened,
    retire,
    still_staff,
)
from ...settings_store import DB_UNAVAILABLE, GOLIVE_MODES, GUILD_ONLY
from ...twitch import TwitchClient, TwitchError

log = logging.getLogger(__name__)

TWITCH_OFF = (
    "go-live: Twitch enrichment is off (TWITCH_CLIENT_ID/TWITCH_CLIENT_SECRET are not set); "
    "detection runs on Discord presence alone"
)
POLLING_NO_CREDS = (
    "off — no Twitch credentials; the sweep still runs and still ages sessions out"
)
POLLING_NO_COG = "not known — the go-live cog is not loaded, so nothing is polling or announcing"
POLL_FAILURES_BEFORE_DEGRADED = 3
FEATURE = "golive"
COG_NAME = "GoLive"
LOGIN_MAX = 25
SELECT_CAP = 25
OPTED_OUT = (
    "Done — Black Bloc will not announce your streams. **Announce my streams again** on the "
    "same panel changes your mind."
)
OPTED_IN = (
    "Done — Black Bloc will announce your streams again when it sees you go live. "
    "**Stop announcing my streams** turns it back off."
)
BAD_LOGIN = (
    "That does not look like a Twitch channel name, so nothing was linked. Use the channel name "
    "from your channel address (the part after twitch.tv/), for example `blackbloc`."
)
NO_SUCH_CHANNEL = (
    "Twitch has no channel called **{channel}**, so nothing was linked. Check the spelling "
    "against your channel address and try again."
)
LINKED = (
    "Linked **{channel}** to you. Black Bloc will use it to fill in the game and title when you "
    "go live, and to spot streams Discord does not show. **Unlink** undoes it."
)
LINK_NOT_CHECKED = (
    "Linked **{channel}** to you, but Twitch could not be reached to check that the channel name "
    "exists, so it has not been verified. If announcements do not fill in your game and title, "
    "**Change my channel** re-checks it later."
)
LINK_TAKEN = (
    "**{channel}** is already linked to another member here, so nothing was changed. A Twitch "
    "channel name can only belong to one member — if that channel is yours, ask a Lead to remove "
    "the other link first."
)
UNLINKED = (
    "Done — Black Bloc has forgotten your Twitch channel. Discord presence still announces your "
    "streams; **Stop announcing my streams** stops that too."
)
MODE_SET = "Go-live announcements are now **{mode}**."
PLATFORM_UNKNOWN = "an unknown platform"
TEST_MODE_NOTE = "test mode means nothing is posted outside <#{test_channel_id}>"
TEST_MODE_LINE = "Right now {note}, so nothing of yours reaches the announcement channel."
COMMAND_DESCRIPTION = "Your Twitch channel, and whether your streams get announced"
LINK_MODAL_TITLE = "Your Twitch channel"
LINK_MODAL_LABEL = "The name after twitch.tv/"
LINK_MODAL_PLACEHOLDER = "blackbloc"
PREVIEW_SELF = "self"
PREVIEW_PICK = "Preview an announcement…"
PREVIEW_AS_YOU_ARE = "As you are now"
MODE_PICK = "Announcements: off / shadow / on"
MODE_OPTION = "Announcements: {mode}"
PICK_A_STREAMER = "Somebody who has linked a channel…"
STREAMERS_TITLE = "Streamers"
STREAMERS_INTRO = (
    "Everyone who has linked a Twitch channel. Picking one shows what Black Bloc knows about "
    "them, and lets you undo it for them — the same as the Go-live page on the site."
)
STREAMERS_EMPTY = "Nobody has linked a Twitch channel yet."
STREAMER_CARD = "**{name}** — twitch.tv/{login}"
STREAMER_OPTION = "{name} — twitch.tv/{login}"
STREAMER_UNVERIFIED = " — not verified with Twitch"
STREAMER_OPTED_OUT = "Opted out, so none of their streams are announced."
STREAMER_ANNOUNCED = "Announced whenever Black Bloc sees them go live."
STREAMER_UNLINK_CONFIRM = (
    "Unlink **{name}** from twitch.tv/{login}? They keep every role they already have, and "
    "Discord presence still announces them."
)
THEY_UNLINKED = "Done — **{name}** is no longer linked to a Twitch channel."
THEY_OPTED_OUT = "Done — no stream of **{name}**'s is announced from now on."
THEY_OPTED_IN = "Done — **{name}**'s streams can be announced again."
UNLINK_THEM = "Unlink them"
OPT_THEM_OUT = "Opt them out"
OPT_THEM_IN = "Opt them back in"
STAFF_ONLY_LINE = "The go-live feed's own settings are for staff."
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


async def set_live_role_added(db: Any, session_id: int, role_id: int) -> None:
    """Record which role went on, so that role comes off however the setting changes."""
    await db.conn.execute(
        "UPDATE golive_sessions SET live_role_added = 1, live_role_id = ? WHERE id = ?",
        (int(role_id), session_id),
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
    if not login or len(login) > LOGIN_MAX:
        return None
    if not all(ch.isalnum() or ch == "_" for ch in login):
        return None
    return login


def target_id(target: Any) -> int:
    return int(getattr(target, "id", target))


def member_for(guild: Any, target: Any) -> Any:
    if getattr(target, "id", None) is not None:
        return target
    return guild.get_member(int(target))


async def auto_fan_role(bot: Any, guild: Any, target: Any, *, by: int | None) -> str:
    """`pings_fan_role_creation auto` is the only setting that makes a role from a link."""
    member = member_for(guild, target)
    if member is None:
        return ""
    outcome = await pings.maybe_auto_create(bot, guild, member, by=by)
    return f" {outcome.message}" if outcome is not None and outcome.ok else ""


async def fan_role_after_leaving(bot: Any, guild: Any, target: Any, *, by: int | None) -> str:
    """`pings_fan_role_on_unlink` decides; `keep` — the default — says nothing at all."""
    outcome = await pings.on_streamer_left(bot, guild, target_id(target), by=by)
    return f" {outcome.message}" if outcome is not None and outcome.ok else ""


async def link_channel(
    bot: Any,
    guild: Any,
    actor: Any,
    target: Any,
    given: Any,
    *,
    helix: Any = None,
    via: str = VIA_DISCORD,
) -> tuple[str, str]:
    """The one place a Twitch channel is linked: (what happened, the fan-role sentence)."""
    cleaned = clean_login(str(given or ""))
    if cleaned is None:
        return "bad_login", ""
    wanted = target_id(target)
    owner = await link_owner(bot.db, cleaned)
    if owner is not None and owner != wanted:
        return "taken", ""
    twitch_user_id = None
    if helix is not None:
        try:
            users = await helix.get_users([cleaned])
        except TwitchError as exc:
            log.warning("go-live: could not check the login %s: %s", cleaned, exc)
            users = None
        if users == []:
            return "no_such_channel", ""
        if users:
            twitch_user_id = users[0].id
    checked = twitch_user_id is not None
    await set_link(bot.db, wanted, cleaned, twitch_user_id)
    extra = await auto_fan_role(bot, guild, target, by=target_id(actor))
    await log_action(
        bot,
        guild,
        kind_via("golive.link", via),
        actor=actor,
        target=target,
        details={"login": cleaned, "checked": checked, "via": via},
    )
    return ("linked_unchecked" if helix is not None and not checked else "linked"), extra


async def unlink_channel(
    bot: Any, guild: Any, actor: Any, target: Any, *, via: str = VIA_DISCORD
) -> tuple[bool, str]:
    """(whether a row went, the fan-role sentence) — one write, one `golive.unlink` row."""
    removed = await remove_link(bot.db, target_id(target))
    if not removed:
        return False, ""
    extra = await fan_role_after_leaving(bot, guild, target, by=target_id(actor))
    await log_action(
        bot,
        guild,
        kind_via("golive.unlink", via),
        actor=actor,
        target=target,
        details={"via": via},
    )
    return True, extra


async def opt_out(
    bot: Any, guild: Any, actor: Any, target: Any, *, via: str = VIA_DISCORD
) -> str:
    await set_optout(bot.db, target_id(target))
    extra = await fan_role_after_leaving(bot, guild, target, by=target_id(actor))
    await log_action(
        bot,
        guild,
        kind_via("golive.optout", via),
        actor=actor,
        target=target,
        details={"via": via},
    )
    return extra


async def opt_in(
    bot: Any, guild: Any, actor: Any, target: Any, *, via: str = VIA_DISCORD
) -> bool:
    cleared = await clear_optout(bot.db, target_id(target))
    if cleared:
        await log_action(
            bot,
            guild,
            kind_via("golive.optin", via),
            actor=actor,
            target=target,
            details={"via": via},
        )
    return cleared


async def set_mode(
    bot: Any, guild: Any, actor: Any, value: str, *, via: str = VIA_DISCORD
) -> str:
    await bot.store.set(guild.id, "golive_mode", value, by=target_id(actor))
    await log_action(
        bot,
        guild,
        kind_via("golive.mode", via),
        actor=actor,
        details={"mode": value, "via": via},
    )
    return MODE_SET.format(mode=value)


def test_mode_note(bot: Any, guild: Any) -> str | None:
    """The honest answer to 'why was my real stream not announced' — never a stack trace."""
    channel_id = bot.store.get(guild.id, "golive_channel_id")
    guard = getattr(bot, "guard", None)
    if not channel_id or guard is None or guard.allows_channel(channel_id):
        return None
    return TEST_MODE_NOTE.format(test_channel_id=guard.test_channel_id)


async def status_lines(bot: Any, cog: Any, guild: Any) -> list[str]:
    """What `/golive status` said, now the staff half of the panel's embed."""
    store = bot.store
    totals = await counts(bot.db, guild.id)
    channel_id = store.get(guild.id, "golive_channel_id")
    note = test_mode_note(bot, guild)
    where = f"<#{channel_id}>" if channel_id else "not set"
    ending = end_summary(
        store.get(guild.id, "golive_end_mode"), store.get(guild.id, "golive_end_suffix")
    )
    failures = getattr(cog, "poll_failures", 0)
    lines = [
        f"**mode** — {store.get(guild.id, 'golive_mode')}",
        f"**stream end** — {ending}",
        f"**channel** — {where}" + (f" — but {note}" if note else ""),
        f"**cooldown** — {store.get(guild.id, 'golive_cooldown_minutes')} minute(s)",
        f"**twitch polling** — {polling_summary(cog)}",
        f"**last good poll** — {getattr(cog, 'last_poll_ok_at', None) or 'never'}",
        f"**last poll error** — {getattr(cog, 'last_poll_error', None) or 'none'}"
        + (f" ({failures} in a row)" if failures else ""),
        f"**links** — {totals['links']} · **opt-outs** — {totals['optouts']} · "
        f"**live now** — {totals['open_sessions']}",
    ]
    lines += [
        f"• {display_name_of(guild, row['user_id'])} on "
        f"{_row_value(row, 'platform') or PLATFORM_UNKNOWN}"
        for row in await open_sessions(bot.db, guild.id)
    ]
    return lines


def polling_summary(cog: Any) -> str:
    """Health, not liveness — the last good poll and the last error are lines of their own."""
    if cog is None:
        return POLLING_NO_COG
    if cog.helix is None:
        return POLLING_NO_CREDS
    return "running" if cog.poller.is_running() else "stopped"


def display_name_of(guild: Any, user_id: Any) -> str:
    member = guild.get_member(int(user_id))
    return str(getattr(member, "display_name", None) or user_id)


def preview(bot: Any, guild: Any, actor: Any, platform: Any) -> tuple[str, Any, dict[str, Any]]:
    """What an announcement would look like — never posted, never pinged (checklist 13)."""
    info = (
        TEST_STREAMS[platform]
        if platform in TEST_STREAMS
        else extract_stream(getattr(actor, "activities", ())) or TEST_STREAMS[TWITCH]
    )
    text = render(bot.store.get(guild.id, "golive_template"), info, actor)
    source = "twitch" if (info.platform or "").casefold() == TWITCH.casefold() else "presence"
    embed = (
        announcement_embed(info, actor, source)
        if bot.store.get(guild.id, "golive_embed")
        else None
    )
    details: dict[str, Any] = {"text": text, "platform": info.platform}
    if embed is not None:
        details["embed"] = embed_summary(embed)
    return text, embed, details


class GoLive(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.helix: TwitchClient | None = None
        self._end_tasks: dict[int, asyncio.Task] = {}
        self._locks: dict[int, asyncio.Lock] = {}
        self.last_poll_ok_at: str | None = None
        self.last_poll_error: str | None = None
        self.poll_failures = 0

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
        fan_role_id = await pings.announced_fan_role(self.bot, guild, member.id)
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
            fan_role_id=fan_role_id,
        )
        embed = self._embed(guild, info, member, source)
        result = (
            await self._post(guild, text, embed, fan_role_id=fan_role_id)
            if mode == "on"
            else PostResult(reason="shadow")
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
            "fan_role_id": fan_role_id,
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
        added = await self._live_role(guild, member, add=True)
        if added is not None:
            await set_live_role_added(self.bot.db, session_id, added)

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
        fan_role_id = await pings.announced_fan_role(
            self.bot, guild, row["user_id"], notice=False
        )
        try:
            message = await channel.fetch_message(message_id)
            await message.edit(
                content=ended_text(message.content, suffix),
                allowed_mentions=self._mentions(guild.id, fan_role_id),
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
        name = display_name_of(guild, row["user_id"])
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

    async def _post(
        self, guild: Any, text: str, embed: Any = None, *, fan_role_id: int | None = None
    ) -> PostResult:
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
                allowed_mentions=self._mentions(guild.id, fan_role_id),
                **({"embed": embed} if embed is not None else {}),
            )
        except Exception as exc:
            log.warning("go-live: not posted — %s: %s", type(exc).__name__, exc)
            return PostResult(reason=f"{type(exc).__name__}: {exc}")
        return PostResult(message=message)

    async def _live_role(self, guild: Any, member: Any, *, add: bool) -> int | None:
        """The id of the role that actually moved, or None when none did."""
        role_id = self.bot.store.get(guild.id, "golive_live_role_id")
        if not role_id:
            return None
        role = guild.get_role(role_id)
        if role is None:
            log.warning("go-live: live role %s is not in this server", role_id)
            return None
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
            return None
        try:
            if add:
                await member.add_roles(role, reason="Black Bloc go-live")
            else:
                await member.remove_roles(role, reason="Black Bloc go-live")
        except discord.HTTPException as exc:
            log.warning("go-live: could not change the live role for %s: %s", member.id, exc)
            return None
        await log_action(
            self.bot,
            guild,
            "golive.add_role" if add else "golive.remove_role",
            target=member,
            details={"role_id": role_id},
        )
        return int(role_id)

    async def _remove_live_role(self, guild: Any, member: Any, row: Any) -> None:
        if not _row_value(row, "live_role_added"):
            return
        role_id = _row_value(row, "live_role_id") or self.bot.store.get(
            guild.id, "golive_live_role_id"
        )
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

    def _mentions(
        self, guild_id: int, fan_role_id: int | None = None
    ) -> discord.AllowedMentions:
        wanted = [
            role_id
            for role_id in (self.bot.store.get(guild_id, "golive_ping_role_id"), fan_role_id)
            if role_id
        ]
        return discord.AllowedMentions(
            everyone=False,
            users=False,
            roles=[discord.Object(role_id) for role_id in dict.fromkeys(wanted)] or False,
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

    def _poll_worked(self) -> None:
        self.last_poll_ok_at = now_iso()
        self.last_poll_error = None
        self.poll_failures = 0

    async def _poll_failed(self, exc: TwitchError) -> None:
        """One action-log line per outage, at the point the sweep stops being trustworthy."""
        self.last_poll_error = str(exc)
        self.poll_failures += 1
        log.warning(
            "go-live: Twitch poll failed (%d in a row): %s", self.poll_failures, exc
        )
        if self.poll_failures != POLL_FAILURES_BEFORE_DEGRADED:
            return
        for guild in list(getattr(self.bot, "guilds", ())):
            await log_action(
                self.bot,
                guild,
                "golive.poll_degraded",
                details={
                    "failures": self.poll_failures,
                    "reason": f"{type(exc).__name__}: {exc}",
                    "open_sessions": len(await open_sessions(self.bot.db, guild.id)),
                },
            )

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
            self._poll_worked()
            return
        try:
            streams = await self.helix.get_streams(list(by_login))
        except TwitchError as exc:
            await self._poll_failed(exc)
            return
        self._poll_worked()
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

    async def _ready(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return False
        if self.bot.db.is_connected:
            return True
        log.warning("go-live: refused a command — the database is not connected")
        await answer(interaction, DB_UNAVAILABLE)
        return False

    @app_commands.command(name="golive", description=COMMAND_DESCRIPTION)
    async def golive(self, interaction: discord.Interaction) -> None:
        if not await self._ready(interaction):
            return
        embed, view = await build_panel(self.bot, interaction.guild, interaction.user)
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()


class GoLivePanel(Panel):
    def __init__(self, minutes: int) -> None:
        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER)


def styles() -> dict[str, discord.ButtonStyle]:
    return {
        "primary": discord.ButtonStyle.primary,
        "secondary": discord.ButtonStyle.secondary,
        "success": discord.ButtonStyle.success,
        "danger": discord.ButtonStyle.danger,
    }


def minutes_for(bot: Any, guild_id: int) -> int:
    return panel_minutes(bot.store, guild_id)


def cog_of(bot: Any) -> Any:
    getter = getattr(bot, "get_cog", None)
    return getter(COG_NAME) if callable(getter) else None


async def db_up(interaction: discord.Interaction) -> bool:
    """`db_ready` answers a followup; this one is for the reads that happen BEFORE a defer."""
    if interaction.client.db.is_connected:
        return True
    await answer(interaction, DB_UNAVAILABLE)
    return False


def add_site_link(view: Any, bot: Any, row: int) -> None:
    url = site_page_url(getattr(getattr(bot, "settings", None), "origin", ""))
    if url:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link, label=SITE_BUTTON, url=url, row=row
            )
        )


def link_said(outcome: str, given: Any) -> str:
    channel = clean_login(str(given or "")) or str(given or "")[:LOGIN_MAX]
    return {
        "bad_login": BAD_LOGIN,
        "taken": LINK_TAKEN.format(channel=channel),
        "no_such_channel": NO_SUCH_CHANNEL.format(channel=channel),
        "linked": LINKED.format(channel=channel),
        "linked_unchecked": LINK_NOT_CHECKED.format(channel=channel),
    }[outcome]


async def own_unlink(bot: Any, guild: Any, actor: Any) -> str:
    _, extra = await unlink_channel(bot, guild, actor, actor)
    return UNLINKED + extra


async def own_opt_out(bot: Any, guild: Any, actor: Any) -> str:
    return OPTED_OUT + await opt_out(bot, guild, actor, actor)


async def own_opt_in(bot: Any, guild: Any, actor: Any) -> str:
    await opt_in(bot, guild, actor, actor)
    return OPTED_IN


OWN_MOVES: dict[str, Any] = {
    "unlink": own_unlink,
    "optout": own_opt_out,
    "optin": own_opt_in,
}


async def their_move(bot: Any, guild: Any, actor: Any, user_id: int, action: str) -> str:
    """Staff's half of the same three functions, with a target who is not the actor."""
    name = display_name_of(guild, user_id)
    if action == "unlink":
        await unlink_channel(bot, guild, actor, user_id)
        return THEY_UNLINKED.format(name=name)
    if action == "optout":
        await opt_out(bot, guild, actor, user_id)
        return THEY_OPTED_OUT.format(name=name)
    await opt_in(bot, guild, actor, user_id)
    return THEY_OPTED_IN.format(name=name)


async def build_panel(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, Any]:
    """One command, two panels: what a member may do and what staff may do, from one embed."""
    store = bot.store
    staff = bool(store.is_staff(actor))
    row = await get_link(bot.db, actor.id)
    login = _row_value(row, "twitch_login")
    opted_out = await is_opted_out(bot.db, actor.id)
    note = test_mode_note(bot, guild)
    mode = store.get(guild.id, "golive_mode")
    lines = card_lines(
        login,
        _row_value(row, "twitch_user_id"),
        opted_out,
        mode=mode,
        channel_note=None if staff or not note else TEST_MODE_LINE.format(note=note),
    )
    if staff:
        lines += await status_lines(bot, cog_of(bot), guild)
    else:
        lines.append(STAFF_ONLY_LINE)
    embed = discord.Embed(title=PANEL_TITLE, description="\n".join(lines))
    view = GoLivePanel(minutes_for(bot, guild.id))
    for move in panel_buttons(linked=bool(login), opted_out=opted_out, staff=staff):
        view.add_item(MoveButton(move))
    add_site_link(view, bot, 2)
    if staff:
        view.add_item(PreviewPick())
        view.add_item(ModePick(mode))
    return embed, view


async def render_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = await build_panel(interaction.client, interaction.guild, interaction.user)
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def run_move(interaction: discord.Interaction, move: Any, previous: Any = None) -> None:
    action = move.action
    if action == "logs":
        await send_logs(interaction, FEATURE)
        return
    if move.needs_modal:
        if not await db_up(interaction):
            return
        row = await get_link(interaction.client.db, interaction.user.id)
        await interaction.response.send_modal(
            LinkModal(_row_value(row, "twitch_login"), previous)
        )
        return
    if action == "streamers":
        if not await still_staff(interaction):
            return
        if not await opened(interaction, staff=False):
            return
        await render_streamers(interaction, None, previous)
        return
    if not await opened(interaction, staff=False):
        return
    if action == "refresh":
        await render_panel(interaction, previous)
        return
    said = await OWN_MOVES[action](interaction.client, interaction.guild, interaction.user)
    await render_panel(interaction, previous)
    await answer(interaction, said)


class MoveButton(discord.ui.Button):
    def __init__(self, move: Any) -> None:
        super().__init__(label=move.label, style=styles()[move.style], row=move.row)
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_move(interaction, self.move, self.view)


class LinkModal(AnswersErrors, discord.ui.Modal, title=LINK_MODAL_TITLE):
    """One short line, so it is not `panels.NoteModal`'s paragraph field."""

    channel = discord.ui.TextInput(
        label=LINK_MODAL_LABEL, placeholder=LINK_MODAL_PLACEHOLDER, max_length=LOGIN_MAX
    )

    def __init__(self, login: Any = None, previous: Any = None) -> None:
        super().__init__()
        self.previous = previous
        if login:
            self.channel.default = str(login)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction, staff=False):
            return
        bot = interaction.client
        given = str(self.channel)
        outcome, extra = await link_channel(
            bot,
            interaction.guild,
            interaction.user,
            interaction.user,
            given,
            helix=getattr(cog_of(bot), "helix", None),
        )
        await render_panel(interaction, self.previous)
        await answer(interaction, link_said(outcome, given) + extra)


class PreviewPick(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(
            placeholder=PREVIEW_PICK,
            options=[discord.SelectOption(label=PREVIEW_AS_YOU_ARE, value=PREVIEW_SELF)]
            + [discord.SelectOption(label=name, value=name) for name in TEST_STREAMS],
            min_values=1,
            max_values=1,
            row=3,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        if not await db_up(interaction):
            return
        bot = interaction.client
        text, embed, details = preview(bot, interaction.guild, interaction.user, self.values[0])
        await interaction.response.send_message(
            text,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
            **({"embed": embed} if embed is not None else {}),
        )
        await log_action(
            bot, interaction.guild, "golive.test", actor=interaction.user, details=details
        )


class ModePick(discord.ui.Select):
    def __init__(self, current: Any) -> None:
        super().__init__(
            placeholder=MODE_PICK,
            options=[
                discord.SelectOption(
                    label=MODE_OPTION.format(mode=name), value=name, default=name == current
                )
                for name in GOLIVE_MODES
            ],
            min_values=1,
            max_values=1,
            row=4,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        if not await opened(interaction, staff=False):
            return
        said = await set_mode(
            interaction.client, interaction.guild, interaction.user, self.values[0]
        )
        await render_panel(interaction, self.view)
        await answer(interaction, said)


def streamer_lines(guild: Any, row: Any, opted_out: bool) -> list[str]:
    line = STREAMER_CARD.format(
        name=display_name_of(guild, row["user_id"]), login=row["twitch_login"]
    )
    if not row["twitch_user_id"]:
        line += STREAMER_UNVERIFIED
    return [line, STREAMER_OPTED_OUT if opted_out else STREAMER_ANNOUNCED]


async def build_streamers(
    bot: Any, guild: Any, picked: Any = None
) -> tuple[discord.Embed, Any]:
    rows = await all_links(bot.db)
    chosen = (
        next((row for row in rows if int(row["user_id"]) == int(picked)), None)
        if picked is not None
        else None
    )
    lines = [STREAMERS_INTRO] if rows else [STREAMERS_EMPTY]
    view = GoLivePanel(minutes_for(bot, guild.id))
    if rows:
        view.add_item(StreamerPick(guild, rows[:SELECT_CAP], len(rows), chosen))
    if chosen is not None:
        away = await is_opted_out(bot.db, chosen["user_id"])
        lines += streamer_lines(guild, chosen, away)
        view.add_item(TheirMoveButton("unlink", chosen["user_id"]))
        view.add_item(TheirMoveButton("optin" if away else "optout", chosen["user_id"]))
    view.add_item(BackButton(row=2))
    add_site_link(view, bot, 2)
    embed = discord.Embed(title=STREAMERS_TITLE, description="\n".join(lines))
    return embed, view


async def render_streamers(
    interaction: discord.Interaction, picked: Any = None, previous: Any = None
) -> None:
    embed, view = await build_streamers(interaction.client, interaction.guild, picked)
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


class StreamerPick(discord.ui.Select):
    def __init__(
        self, guild: Any, rows: list[Any], total: int, chosen: Any = None
    ) -> None:
        super().__init__(
            placeholder=capped_placeholder(len(rows), total, pick=PICK_A_STREAMER),
            options=[
                discord.SelectOption(
                    label=STREAMER_OPTION.format(
                        name=display_name_of(guild, row["user_id"]),
                        login=row["twitch_login"],
                    )[:SELECT_OPTION_LIMIT],
                    value=str(row["user_id"]),
                    default=chosen is not None
                    and int(row["user_id"]) == int(chosen["user_id"]),
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
        await render_streamers(interaction, int(self.values[0]), self.view)


class TheirMoveButton(discord.ui.Button):
    LABELS = {"unlink": UNLINK_THEM, "optout": OPT_THEM_OUT, "optin": OPT_THEM_IN}

    def __init__(self, action: str, user_id: Any) -> None:
        super().__init__(
            label=self.LABELS[action],
            style=(
                discord.ButtonStyle.success
                if action == "optin"
                else discord.ButtonStyle.danger
            ),
            row=1,
        )
        self.action = action
        self.user_id = int(user_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        if not await opened(interaction, staff=False):
            return
        if self.action == "unlink":
            await render_unlink_confirm(interaction, self.user_id, self.view)
            return
        said = await their_move(
            interaction.client, interaction.guild, interaction.user, self.user_id, self.action
        )
        await render_streamers(interaction, self.user_id, self.view)
        await answer(interaction, said)


async def render_unlink_confirm(
    interaction: discord.Interaction, user_id: int, previous: Any = None
) -> None:
    bot = interaction.client
    guild = interaction.guild
    row = await get_link(bot.db, user_id)
    if row is None:
        await render_streamers(interaction, None, previous)
        return
    embed = discord.Embed(
        title=STREAMERS_TITLE,
        description=STREAMER_UNLINK_CONFIRM.format(
            name=display_name_of(guild, user_id), login=row["twitch_login"]
        ),
    )
    view = GoLivePanel(minutes_for(bot, guild.id))
    view.add_item(UnlinkYesButton(user_id))
    view.add_item(StreamersBackButton(user_id))
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


class UnlinkYesButton(discord.ui.Button):
    def __init__(self, user_id: int) -> None:
        super().__init__(label="Yes, unlink them", style=discord.ButtonStyle.danger, row=0)
        self.user_id = int(user_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        if not await opened(interaction, staff=False):
            return
        said = await their_move(
            interaction.client, interaction.guild, interaction.user, self.user_id, "unlink"
        )
        await render_streamers(interaction, None, self.view)
        await answer(interaction, said)


class StreamersBackButton(discord.ui.Button):
    def __init__(self, user_id: Any = None, row: int = 0) -> None:
        super().__init__(label="Back", style=discord.ButtonStyle.secondary, row=row)
        self.user_id = None if user_id is None else int(user_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        if not await opened(interaction, staff=False):
            return
        await render_streamers(interaction, self.user_id, self.view)


class BackButton(discord.ui.Button):
    def __init__(self, row: int = 0) -> None:
        super().__init__(label="Back", style=discord.ButtonStyle.secondary, row=row)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction, staff=False):
            return
        await render_panel(interaction, self.view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GoLive(bot))
