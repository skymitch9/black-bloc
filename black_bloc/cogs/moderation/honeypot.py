from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from ...actionlog import log_action, send_logs
from ...command_errors import AnswersErrors, SafeDynamicItem
from ...command_visibility import STAFF_ONLY
from ...honeypot import (
    ARMED_WITH_NO_TRAP,
    BACK,
    CHANNEL_NAME_MAX,
    CLEAR_EXEMPT,
    DEAD_TRAP_LINE,
    EXEMPT_NOTHING_CHANGED,
    EXEMPT_NOW_NOBODY,
    EXEMPT_PLACEHOLDER,
    EXEMPT_SELECT_MAX,
    EXEMPT_TOO_MANY,
    FORGET,
    FORGET_PLACEHOLDER,
    LOGS,
    MODE_IS_OFF_WAY_BACK,
    MODE_PLACEHOLDER,
    MODE_SET,
    NOT_A_NUMBER,
    NUMBERS_TITLE,
    PANEL_MINUTES_KEY,
    PANEL_MINUTES_LABEL,
    PANEL_NUMBERS,
    PANEL_TIMEOUT_FOOTER,
    PANEL_TITLE,
    PURGE_DAYS_LABEL,
    REFRESH,
    SETTINGS,
    SETTINGS_DONE,
    SETTINGS_NOTHING,
    SETUP,
    SITE,
    TEST_MODE_LINE,
    TRAP_NAME_LABEL,
    TRAP_NAME_TITLE,
    HoneypotMove,
    exempt_defaults,
    exempt_diff,
    exempt_editable,
    exempt_sentence,
    forget_buttons,
    mode_options,
    panel_minutes,
    root_buttons,
    settings_buttons,
    trap_options,
)
from ...logkinds import VIA_DISCORD, kind_via
from ...panels import (
    Outcome,
    Panel,
    answer,
    clamped,
    db_up,
    opened,
    retire,
    site_page_url,
    still_staff,
)
from ...settings_store import (
    DB_UNAVAILABLE,
    GUILD_ONLY,
    HONEYPOT_PURGE_MAX_DAYS,
    SettingError,
    coerce_value,
    require_staff,
    staff_roles_sentence,
)

log = logging.getLogger(__name__)

TRAP_NAME = "🍯-do-not-post-here"
TRAP_MESSAGE_TYPES = (discord.MessageType.default, discord.MessageType.reply)
SHADOW_OFFER_MINUTES = 10
NOTICE = (
    "This channel is a trap for bots. **Do not post here** — anything posted is treated as spam "
    "and the account is banned."
)
BAN_TEMPLATE = r"honeypot:ban:(?P<hit_id>[0-9]+)"
CONTENT_LIMIT = 500

DM_BEFORE_BAN = (
    "You have been banned from **{guild}** because you posted in a channel that exists only to "
    "catch spam bots, and its pinned notice says so. If you are a person and this was a mistake, "
    "ask a moderator of that server to review the ban — Black Bloc cannot undo it for you."
)
ALREADY_BANNED = (
    "That account was already banned for this post, so nothing changed. `/honeypot` shows what "
    "the trap has caught."
)
NO_SUCH_HIT = (
    "Black Bloc has no record of that trap post any more, so nobody was banned. It may have been "
    "cleared from the database; ban the account by hand if it is still a problem."
)
BAN_IN_TEST_MODE = (
    "Black Bloc is in test mode, so it refused to ban anyone and logged what it would have done "
    "instead. Bans start working when the owner turns test mode off — until then, ban by hand if "
    "this one is real."
)
BAN_REFUSED = (
    "Discord refused the ban, so the account is still here. Black Bloc needs the Ban Members "
    "permission and its own role has to sit above theirs in Server Settings → Roles. Ask an admin "
    "to fix that, then ban by hand."
)
CANNOT_CREATE = (
    "Discord refused to create the channel, so no trap was made. Black Bloc needs the Manage "
    "Channels permission in this server. Ask an admin to give it that, then run this again."
)
NO_TEST_CHANNEL_TRAP = (
    "Black Bloc is in test mode and cannot see its test channel, so no trap was made. Set "
    "TEST_CHANNEL_ID to a channel the bot can read, restart it, then run this again."
)
NOTICE_NOT_POSTED = (
    "The pinned notice was not posted, because test mode keeps Black Bloc out of every channel "
    "but the test one. Post it by hand for now, or run this again once test mode is off."
)
NO_STAFF_ROLES = (
    "Black Bloc cannot work out who counts as staff, so the trap was left as it was. Nobody but "
    "server admins would be exempt from it, which means one mistyped message from a moderator "
    "would ban them. Point `staff_channel_id` at a channel only staff can see with `/settings "
    "set staff_channel_id`, check the panel lists the roles you expect, then set the mode again."
)
NO_STAFF_WARNING = (
    "⚠️ **No staff roles resolve.** Only people with Manage Server are exempt, so a moderator "
    "who posts here would be banned. Fix `staff_channel_id` before leaving the trap on."
)
ALREADY_A_TRAP = (
    "This server already has a trap channel — {where} — so a second one was not made. Two traps "
    "are two things to remember; delete that channel, or forget it from the honeypot panel or "
    "this page if it is already gone, then run this again."
)
NOT_A_TRAP = (
    "**{channel_id}** is not one of Black Bloc's trap channels, so nothing was forgotten. "
    "`/honeypot` lists the ones it knows about."
)
FORGOTTEN = (
    "Black Bloc has forgotten **{channel_id}** — it is no longer a trap, and posts there are "
    "ignored from now on."
)


def ban_custom_id(hit_id: int) -> str:
    return f"honeypot:ban:{hit_id}"


def exempt_reason(member: Any, staff_ids: set[int], exempt_ids: set[int]) -> str | None:
    """Why the trap is ignoring this author, or None when they are fair game."""
    if getattr(member, "bot", False):
        return "bot"
    perms = getattr(member, "guild_permissions", None)
    if perms is not None and getattr(perms, "manage_guild", False):
        return "manage_guild"
    role_ids = {getattr(r, "id", None) for r in getattr(member, "roles", ())}
    if role_ids & staff_ids:
        return "staff"
    if role_ids & exempt_ids:
        return "exempt_role"
    return None


def trimmed(content: Any) -> str:
    return str(content or "")[:CONTENT_LIMIT]


def offer_text(user_id: int, content: str) -> str:
    return (
        f"Trap post from <@{user_id}> — shadow mode, so nothing was done to them beyond deleting "
        f"it. Ban them with the button if this is a bot.\n> {content or '(no text)'}"
    )


async def record_hit(
    db: Any,
    guild_id: int,
    user_id: int,
    channel_id: int,
    message_id: int | None,
    content: str,
    mode: str,
    action: str,
) -> int | None:
    cur = await db.conn.execute(
        "INSERT INTO honeypot_hits(guild_id, user_id, channel_id, message_id, content, at, mode, "
        "action) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            guild_id,
            user_id,
            channel_id,
            message_id,
            content,
            datetime.now(UTC).isoformat(),
            mode,
            action,
        ),
    )
    await db.conn.commit()
    return cur.lastrowid


async def get_hit(db: Any, hit_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM honeypot_hits WHERE id = ?", (hit_id,))
    return await cur.fetchone()


async def set_hit_action(db: Any, hit_id: int, action: str) -> None:
    await db.conn.execute("UPDATE honeypot_hits SET action = ? WHERE id = ?", (action, hit_id))
    await db.conn.commit()


async def banned_already(db: Any, guild_id: int, user_id: int) -> bool:
    cur = await db.conn.execute(
        "SELECT 1 FROM honeypot_hits WHERE guild_id = ? AND user_id = ? AND action = 'banned' "
        "LIMIT 1",
        (guild_id, user_id),
    )
    return await cur.fetchone() is not None


async def offered_recently(db: Any, guild_id: int, user_id: int, minutes: int) -> bool:
    """True when this author already got a Ban-now button inside the window."""
    since = (datetime.now(UTC) - timedelta(minutes=minutes)).isoformat()
    cur = await db.conn.execute(
        "SELECT 1 FROM honeypot_hits WHERE guild_id = ? AND user_id = ? AND action = 'would_ban' "
        "AND at >= ? LIMIT 1",
        (guild_id, user_id, since),
    )
    return await cur.fetchone() is not None


async def recent_hits(db: Any, guild_id: int, limit: int = 50) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM honeypot_hits WHERE guild_id = ? ORDER BY id DESC LIMIT ?",
        (guild_id, int(limit)),
    )
    return list(await cur.fetchall())


async def hit_counts(db: Any, guild_id: int) -> dict[str, int]:
    cur = await db.conn.execute(
        "SELECT action, COUNT(*) AS n FROM honeypot_hits WHERE guild_id = ? GROUP BY action",
        (guild_id,),
    )
    return {row["action"]: int(row["n"]) for row in await cur.fetchall()}


async def do_ban(
    bot: Any, guild: Any, user_id: int, channel_name: str, purge_days: int
) -> str | None:
    """None when the account was banned; otherwise the reason it was not."""
    if getattr(bot, "guard", None) is not None:
        log.warning("honeypot: TEST MODE — refused to ban %s", user_id)
        return "test_mode"
    user = guild.get_member(user_id) or discord.Object(id=user_id)
    await _dm_before_ban(guild, user)
    days = max(0, min(int(purge_days), HONEYPOT_PURGE_MAX_DAYS))
    try:
        await guild.ban(
            user,
            reason=f"Honeypot: posted in #{channel_name}",
            delete_message_seconds=days * 86400,
        )
    except discord.HTTPException as exc:
        log.warning("honeypot: could not ban %s: %s", user_id, exc)
        return f"{type(exc).__name__}: {exc}"
    return None


async def _dm_before_ban(guild: Any, user: Any) -> None:
    send = getattr(user, "send", None)
    if send is None:
        return
    try:
        await send(
            DM_BEFORE_BAN.format(guild=guild.name),
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except Exception as exc:
        log.info("honeypot: could not warn %s before the ban: %s", getattr(user, "id", "?"), exc)


async def ban_hit(
    bot: Any, guild: Any, hit_id: int, actor: Any, by: str, *, via: str = VIA_DISCORD
) -> tuple[str, str]:
    """The Ban-now path, for the button and the web alike: (what happened, what to say)."""
    hit = await get_hit(bot.db, hit_id)
    if hit is None:
        return ("no_such_hit", NO_SUCH_HIT)
    if hit["action"] == "banned":
        return ("already", ALREADY_BANNED)
    channel = bot.get_channel(hit["channel_id"])
    failure = await do_ban(
        bot,
        guild,
        hit["user_id"],
        getattr(channel, "name", "the trap channel"),
        int(bot.store.get(guild.id, "honeypot_purge_days") or 0),
    )
    if failure == "test_mode":
        await log_action(
            bot,
            guild,
            "honeypot.would_ban",
            actor=actor,
            target=hit["user_id"],
            details={"hit_id": hit_id, "reason": "test_mode", "by": by},
        )
        return ("test_mode", BAN_IN_TEST_MODE)
    if failure is not None:
        await set_hit_action(bot.db, hit_id, "ban_failed")
        await log_action(
            bot,
            guild,
            "honeypot.ban_failed",
            actor=actor,
            target=hit["user_id"],
            details={"hit_id": hit_id, "reason": failure, "by": by},
        )
        return ("refused", BAN_REFUSED)
    await set_hit_action(bot.db, hit_id, "banned")
    await log_action(
        bot,
        guild,
        kind_via("honeypot.banned", via),
        actor=actor,
        target=hit["user_id"],
        details={"hit_id": hit_id, "by": by, "via": via},
    )
    return ("banned", f"Banned <@{hit['user_id']}> for that trap post.")


def recorded_traps(bot: Any, guild: Any) -> list[int]:
    return [int(cid) for cid in (bot.store.get(guild.id, "honeypot_channel_ids") or [])]


def live_traps(bot: Any, guild: Any) -> list[int]:
    """The one home for the fact that decides both Setup… and what setup refuses."""
    return [cid for cid in recorded_traps(bot, guild) if guild.get_channel(cid) is not None]


def dead_traps(bot: Any, guild: Any) -> list[int]:
    return [cid for cid in recorded_traps(bot, guild) if guild.get_channel(cid) is None]


async def make_trap_channel(
    bot: Any, guild: Any, actor: Any, name: str | None = None, *, via: str = VIA_DISCORD
) -> tuple[str, str]:
    """Create the trap channel, for slash and web alike: (what happened, what to say)."""
    live = live_traps(bot, guild)
    if live:
        return ("already", ALREADY_A_TRAP.format(where=f"<#{live[0]}>", channel_id=live[0]))
    category = test_category(bot)
    if category is False:
        return ("no_test_channel", NO_TEST_CHANNEL_TRAP)
    try:
        channel = await guild.create_text_channel(
            name or TRAP_NAME,
            category=category or None,
            position=len(list(guild.text_channels)),
            overwrites={
                guild.default_role: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    create_public_threads=False,
                    create_private_threads=False,
                    send_messages_in_threads=False,
                    add_reactions=False,
                    attach_files=False,
                    embed_links=False,
                    use_external_emojis=False,
                )
            },
            slowmode_delay=0,
            reason="Black Bloc honeypot",
        )
    except discord.HTTPException as exc:
        log.warning("honeypot: setup could not create the trap channel: %s", exc)
        return ("refused", CANNOT_CREATE)
    ids = list(bot.store.get(guild.id, "honeypot_channel_ids") or [])
    if channel.id not in ids:
        ids.append(channel.id)
    await bot.store.set(guild.id, "honeypot_channel_ids", ids, by=getattr(actor, "id", actor))
    posted = await post_notice(bot, channel)
    await log_action(
        bot,
        guild,
        kind_via("honeypot.setup", via),
        actor=actor,
        details={"channel_id": channel.id, "notice_posted": posted, "via": via},
    )
    mode = bot.store.get(guild.id, "honeypot_mode")
    return (
        "created",
        f"{channel.mention} is the trap, and the mode is **{mode}**. "
        + ("Its notice is posted and pinned." if posted else NOTICE_NOT_POSTED),
    )


def test_category(bot: Any) -> Any:
    """The test channel's category while the guard is on; None when it is off."""
    guard = getattr(bot, "guard", None)
    if guard is None:
        return None
    channel = bot.get_channel(guard.test_channel_id) if guard.test_channel_id else None
    if channel is None:
        return False
    return channel.category


async def post_notice(bot: Any, channel: Any) -> bool:
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel.id):
        log.warning("honeypot: TEST MODE — the trap notice was not posted in %s", channel.id)
        return False
    try:
        message = await channel.send(NOTICE, allowed_mentions=discord.AllowedMentions.none())
        await message.pin(reason="Black Bloc honeypot")
    except Exception as exc:
        log.warning("honeypot: could not post the notice in %s: %s", channel.id, exc)
        return False
    return True


class BanNowButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=BAN_TEMPLATE
):
    def __init__(self, hit_id: int) -> None:
        self.hit_id = hit_id
        super().__init__(
            discord.ui.Button(
                label="Ban now",
                style=discord.ButtonStyle.danger,
                custom_id=ban_custom_id(hit_id),
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["hit_id"]))

    async def on_click(self, interaction: discord.Interaction) -> None:
        bot = interaction.client
        if not await require_staff(interaction):
            return
        if not bot.db.is_connected:
            await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
            return
        _, said = await ban_hit(
            bot, interaction.guild, self.hit_id, interaction.user, "button"
        )
        await interaction.response.send_message(
            said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )


class Honeypot(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._locks: dict[int, asyncio.Lock] = {}

    async def cog_load(self) -> None:
        self.bot.add_dynamic_items(BanNowButton)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.webhook_id is not None:
            return
        if getattr(message, "type", None) not in TRAP_MESSAGE_TYPES:
            return
        me = getattr(self.bot, "user", None)
        if me is not None and message.author.id == me.id:
            return
        if not self.bot.db.is_connected:
            return
        store = self.bot.store
        mode = store.get(message.guild.id, "honeypot_mode")
        if mode == "off":
            return
        traps = store.get(message.guild.id, "honeypot_channel_ids") or []
        channel = message.channel
        if channel.id not in traps and getattr(channel, "parent_id", None) not in traps:
            return
        async with self._lock(message.author.id):
            await self._caught(message, mode)

    async def _caught(self, message: discord.Message, mode: str) -> None:
        guild = message.guild
        author = message.author
        store = self.bot.store
        reason = exempt_reason(
            author,
            store.staff_role_ids(guild),
            set(store.get(guild.id, "honeypot_exempt_role_ids") or []),
        )
        content = trimmed(message.content)
        if reason is not None:
            await record_hit(
                self.bot.db,
                guild.id,
                author.id,
                message.channel.id,
                message.id,
                content,
                mode,
                "exempt",
            )
            await log_action(
                self.bot,
                guild,
                "honeypot.exempt",
                target=author,
                details={"reason": reason, "channel_id": message.channel.id},
            )
            return
        offered = await offered_recently(
            self.bot.db, guild.id, author.id, SHADOW_OFFER_MINUTES
        )
        await self._delete(message)
        hit_id = await record_hit(
            self.bot.db,
            guild.id,
            author.id,
            message.channel.id,
            message.id,
            content,
            mode,
            "would_ban",
        )
        details = {"hit_id": hit_id, "channel_id": message.channel.id, "content": content}
        if mode == "on":
            if await banned_already(self.bot.db, guild.id, author.id):
                await set_hit_action(self.bot.db, hit_id, "banned")
                await log_action(
                    self.bot,
                    guild,
                    "honeypot.banned",
                    target=author,
                    details=details | {"reason": "already_banned"},
                )
                return
            failure = await do_ban(
                self.bot,
                guild,
                author.id,
                getattr(message.channel, "name", "the trap channel"),
                int(store.get(guild.id, "honeypot_purge_days") or 0),
            )
            if failure is None:
                await set_hit_action(self.bot.db, hit_id, "banned")
                await log_action(
                    self.bot, guild, "honeypot.banned", target=author, details=details
                )
                return
            if failure != "test_mode":
                await set_hit_action(self.bot.db, hit_id, "ban_failed")
                await log_action(
                    self.bot,
                    guild,
                    "honeypot.ban_failed",
                    target=author,
                    details=details | {"reason": failure},
                )
                return
            details = details | {"reason": "test_mode"}
        if offered:
            await log_action(
                self.bot, guild, "honeypot.hit_recorded", target=author, details=details
            )
            return
        await log_action(
            self.bot, guild, "honeypot.would_ban", target=author, details=details
        )
        await self._offer_ban(guild, hit_id, author.id, content)

    async def _delete(self, message: discord.Message) -> None:
        if not self._may_act_in(message.channel):
            log.warning(
                "honeypot: TEST MODE — the trap post in %s was left alone, because that channel "
                "is outside the test channel's category",
                message.channel.id,
            )
            await log_action(
                self.bot,
                message.guild,
                "honeypot.would_delete",
                target=message.author,
                details={"channel_id": message.channel.id},
            )
            return
        try:
            await message.delete()
        except discord.HTTPException as exc:
            log.warning("honeypot: could not delete the trap post %s: %s", message.id, exc)
            await log_action(
                self.bot,
                message.guild,
                "honeypot.delete_failed",
                target=message.author,
                details={
                    "channel_id": message.channel.id,
                    "reason": f"{type(exc).__name__}: {exc}",
                },
            )

    async def _offer_ban(self, guild: Any, hit_id: int | None, user_id: int, content: str) -> None:
        if hit_id is None:
            return
        channel_id = self.bot.store.get(guild.id, "log_channel_id")
        channel = self.bot.get_channel(channel_id) if channel_id else None
        if channel is None:
            log.warning("honeypot: no log channel, so no Ban now button for hit %s", hit_id)
            return
        guard = getattr(self.bot, "guard", None)
        if guard is not None and not guard.allows_channel(channel.id):
            log.warning("honeypot: TEST MODE — no Ban now button posted for hit %s", hit_id)
            return
        view = discord.ui.View(timeout=None)
        view.add_item(BanNowButton(hit_id))
        try:
            await channel.send(
                offer_text(user_id, content),
                view=view,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except Exception as exc:
            log.warning("honeypot: could not offer the ban button for hit %s: %s", hit_id, exc)

    def _lock(self, user_id: int) -> asyncio.Lock:
        lock = self._locks.get(user_id)
        if lock is None:
            lock = self._locks[user_id] = asyncio.Lock()
        return lock

    def _may_act_in(self, channel: Any) -> bool:
        guard = getattr(self.bot, "guard", None)
        if guard is None:
            return True
        test_channel = (
            self.bot.get_channel(guard.test_channel_id) if guard.test_channel_id else None
        )
        if test_channel is None:
            return False
        return getattr(channel, "category_id", None) == getattr(test_channel, "category_id", None)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        if not self.bot.db.is_connected:
            return
        await forget_trap(self.bot, channel.guild, channel.id)

    @app_commands.command(
        name="honeypot", description="The trap channel that catches spam bots"
    )
    @app_commands.default_permissions(STAFF_ONLY)
    async def honeypot(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return
        if not await require_staff(interaction):
            return
        if not await db_up(interaction):
            return
        embed, view = await build_root(self.bot, interaction.guild)
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()


# --- the moves, one function each, one write and one log row -------------------------------------


def arming_refusal(bot: Any, guild: Any) -> str | None:
    """The mode picker and `set_mode` read one answer, so offer and verdict cannot disagree."""
    if not bot.store.staff_roles(guild):
        return NO_STAFF_ROLES
    return None


async def set_mode(
    bot: Any, guild: Any, value: str, actor: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    if value == "on":
        blocker = arming_refusal(bot, guild)
        if blocker is not None:
            return Outcome(False, blocker, "no_staff_roles", 409)
    await bot.store.set(guild.id, "honeypot_mode", value, by=getattr(actor, "id", actor))
    await log_action(
        bot,
        guild,
        kind_via("honeypot.mode", via),
        actor=actor,
        details={"mode": value, "via": via},
    )
    return Outcome(True, MODE_SET.format(mode=value), "set", 200, value)


async def set_exempt_roles(
    bot: Any, guild: Any, role_ids: Any, actor: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """The whole list in one write: the selection IS the list, so add and remove are one move."""
    before = exempt_defaults(bot.store.get(guild.id, "honeypot_exempt_role_ids") or [])
    after = exempt_defaults(role_ids)
    added, removed = exempt_diff(before, after)
    if not added and not removed:
        return Outcome(True, EXEMPT_NOTHING_CHANGED, "unchanged", 200, before)
    await bot.store.set(guild.id, "honeypot_exempt_role_ids", after, by=getattr(actor, "id", actor))
    await log_action(
        bot,
        guild,
        kind_via("honeypot.exempt_set", via),
        actor=actor,
        details={"role_ids": after, "added": added, "removed": removed, "via": via},
    )
    said = EXEMPT_NOW_NOBODY if not after else exempt_sentence(added, removed)
    return Outcome(True, said, "set", 200, after)


async def forget_trap(
    bot: Any, guild: Any, channel_id: int, actor: Any = None, *, via: str = VIA_DISCORD
) -> Outcome:
    ids = recorded_traps(bot, guild)
    if int(channel_id) not in ids:
        return Outcome(False, NOT_A_TRAP.format(channel_id=channel_id), "not_a_trap", 404)
    ids.remove(int(channel_id))
    await bot.store.set(
        guild.id, "honeypot_channel_ids", ids, by=getattr(actor, "id", None)
    )
    await log_action(
        bot,
        guild,
        kind_via("honeypot.trap_removed", via),
        actor=actor,
        details={"channel_id": int(channel_id), "via": via},
    )
    return Outcome(True, FORGOTTEN.format(channel_id=channel_id), "forgotten", 200, ids)


async def save_settings(
    bot: Any, guild: Any, changes: Any, actor: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Every value is validated before any of them is written, so a refusal writes nothing."""
    wanted = {key: value for key, value in (changes or {}).items() if key in SETTINGS_KEYS}
    if not wanted:
        return Outcome(True, SETTINGS_NOTHING, "nothing", 200)
    for key, value in wanted.items():
        try:
            coerce_value(key, value)
        except SettingError as exc:
            return Outcome(False, str(exc), "refused", 400)
    for key, value in wanted.items():
        await bot.store.set(guild.id, key, value, by=getattr(actor, "id", actor))
    await log_action(
        bot,
        guild,
        kind_via("honeypot.settings", via),
        actor=actor,
        details={"changed": wanted, "via": via},
    )
    return Outcome(
        True,
        SETTINGS_DONE.format(
            minutes=panel_minutes(bot.store, guild.id),
            days=bot.store.get(guild.id, "honeypot_purge_days"),
        ),
        "saved",
        200,
    )


def status_lines(bot: Any, guild: Any, totals: dict[str, int]) -> list[str]:
    """The panel embed and what `/honeypot status` printed are ONE list, never two shapes."""
    store = bot.store
    channels = recorded_traps(bot, guild)
    roles = store.get(guild.id, "honeypot_exempt_role_ids") or []
    staff = store.staff_roles(guild)
    mode = store.get(guild.id, "honeypot_mode")
    lines = [
        f"**mode** — {mode}",
        f"**staff (always exempt)** — {staff_roles_sentence(staff)}",
        "**trap channels** — "
        + (", ".join(f"<#{c}>" for c in channels) if channels else "not set up yet"),
        f"**purge** — {store.get(guild.id, 'honeypot_purge_days')} day(s) of their messages",
        "**exempt roles** — "
        + (", ".join(f"<@&{r}>" for r in roles) if roles else "staff only"),
        f"**caught** — {totals.get('banned', 0)} banned · "
        f"{totals.get('would_ban', 0)} logged in shadow · "
        f"{totals.get('ban_failed', 0)} failed · {totals.get('exempt', 0)} ignored",
    ]
    blocker = arming_refusal(bot, guild)
    if blocker is not None:
        lines.append(blocker)
    gone = dead_traps(bot, guild)
    if gone:
        lines.append(
            DEAD_TRAP_LINE.format(
                ids=", ".join(str(one) for one in gone),
                them="it" if len(gone) == 1 else "them",
            )
        )
    if mode == "on" and not live_traps(bot, guild):
        lines.append(ARMED_WITH_NO_TRAP)
    if not exempt_editable(roles):
        lines.append(EXEMPT_TOO_MANY.format(count=len(exempt_defaults(roles))))
    if getattr(bot, "guard", None) is not None:
        lines.append(TEST_MODE_LINE)
    if not staff and mode == "on":
        lines.append(NO_STAFF_WARNING)
    return lines


def settings_lines(bot: Any, guild: Any) -> list[str]:
    return [
        f"**this panel stays live** — {panel_minutes(bot.store, guild.id)} minute(s)",
        f"**a ban deletes** — {bot.store.get(guild.id, 'honeypot_purge_days')} day(s) of their "
        f"messages, 0 to {HONEYPOT_PURGE_MAX_DAYS}",
        "",
        MODE_IS_OFF_WAY_BACK,
    ]


def trap_names(guild: Any, recorded: Any) -> dict[int, str]:
    found: dict[int, str] = {}
    for one in recorded or ():
        channel = guild.get_channel(int(one))
        if channel is not None:
            found[int(one)] = str(getattr(channel, "name", one))
    return found


# --- the panel -----------------------------------------------------------------------------------


STYLES = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}
SETTINGS_KEYS = (PANEL_MINUTES_KEY, "honeypot_purge_days")
PURGE_DAYS_LABEL_BOUNDED = f"{PURGE_DAYS_LABEL} (0–{HONEYPOT_PURGE_MAX_DAYS})"
SETTINGS_TITLE = "How the honeypot panel behaves"
FORGET_TITLE = "Which trap channel to forget"
FORGET_INTRO = (
    "Forgetting a channel only stops Black Bloc treating it as a trap — the channel itself is "
    "left exactly where it is."
)


class HoneypotPanel(Panel):
    def __init__(self, minutes: int) -> None:
        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER)


def minutes_for(bot: Any, guild_id: int) -> int:
    return panel_minutes(bot.store, guild_id)


def add_root_buttons(view: Any, bot: Any, guild: Any) -> None:
    url = site_page_url(getattr(getattr(bot, "settings", None), "origin", ""), "honeypot")
    moves = root_buttons(
        may_setup=not live_traps(bot, guild),
        may_forget=bool(recorded_traps(bot, guild)),
        may_clear=bool(bot.store.get(guild.id, "honeypot_exempt_role_ids") or []),
        has_site=url is not None,
    )
    for move in moves:
        view.add_item(SiteButton(move, url) if move.action == SITE else MoveButton(move))


async def build_root(bot: Any, guild: Any) -> tuple[discord.Embed, HoneypotPanel]:
    totals = await hit_counts(bot.db, guild.id)
    embed = discord.Embed(title=PANEL_TITLE, description=clamped(status_lines(bot, guild, totals)))
    view = HoneypotPanel(minutes_for(bot, guild.id))
    view.add_item(
        ModePick(bot.store.get(guild.id, "honeypot_mode"), arming_refusal(bot, guild) is None)
    )
    roles = bot.store.get(guild.id, "honeypot_exempt_role_ids") or []
    if exempt_editable(roles):
        view.add_item(ExemptPick(exempt_defaults(roles)))
    add_root_buttons(view, bot, guild)
    return (embed, view)


def build_settings(bot: Any, guild: Any) -> tuple[discord.Embed, HoneypotPanel]:
    embed = discord.Embed(title=SETTINGS_TITLE, description=clamped(settings_lines(bot, guild)))
    view = HoneypotPanel(minutes_for(bot, guild.id))
    for move in settings_buttons():
        view.add_item(MoveButton(move))
    return (embed, view)


def build_forget(bot: Any, guild: Any) -> tuple[discord.Embed, HoneypotPanel]:
    recorded = recorded_traps(bot, guild)
    options = trap_options(recorded, trap_names(guild, recorded))
    embed = discord.Embed(title=FORGET_TITLE, description=clamped([FORGET_INTRO]))
    view = HoneypotPanel(minutes_for(bot, guild.id))
    if options:
        view.add_item(ForgetPick(options))
    for move in forget_buttons():
        view.add_item(MoveButton(move))
    return (embed, view)


async def show(interaction: discord.Interaction, built: Any, previous: Any) -> None:
    embed, view = built
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def render_root(interaction: discord.Interaction, previous: Any = None) -> None:
    await show(interaction, await build_root(interaction.client, interaction.guild), previous)


async def render_settings(interaction: discord.Interaction, previous: Any = None) -> None:
    await show(interaction, build_settings(interaction.client, interaction.guild), previous)


async def render_forget(interaction: discord.Interaction, previous: Any = None) -> None:
    await show(interaction, build_forget(interaction.client, interaction.guild), previous)


async def back_to_root(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    await render_root(interaction, previous)


async def open_settings(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    await render_settings(interaction, previous)


async def open_forget(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    await render_forget(interaction, previous)


async def run_mode(interaction: discord.Interaction, value: str, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    outcome = await set_mode(interaction.client, interaction.guild, value, interaction.user)
    await render_root(interaction, previous)
    await answer(interaction, outcome.message)


async def run_exempt(
    interaction: discord.Interaction, role_ids: Any, previous: Any = None
) -> None:
    if not await opened(interaction):
        return
    outcome = await set_exempt_roles(
        interaction.client, interaction.guild, role_ids, interaction.user
    )
    await render_root(interaction, previous)
    await answer(interaction, outcome.message)


async def run_forget(
    interaction: discord.Interaction, channel_id: int, previous: Any = None
) -> None:
    if not await opened(interaction):
        return
    outcome = await forget_trap(
        interaction.client, interaction.guild, int(channel_id), interaction.user
    )
    await render_root(interaction, previous)
    await answer(interaction, outcome.message)


async def run_setup(interaction: discord.Interaction, name: str, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    _, said = await make_trap_channel(
        interaction.client, interaction.guild, interaction.user, name or None
    )
    await render_root(interaction, previous)
    await answer(interaction, said)


async def run_settings(
    interaction: discord.Interaction, changes: dict[str, Any], previous: Any = None
) -> None:
    """A refused value is answered and the card is NOT re-rendered, so it cannot read as a save."""
    if not await opened(interaction):
        return
    outcome = await save_settings(
        interaction.client, interaction.guild, changes, interaction.user
    )
    if not outcome.ok:
        await answer(interaction, outcome.message)
        return
    await render_settings(interaction, previous)
    await answer(interaction, outcome.message)


# --- the controls --------------------------------------------------------------------------------


class MoveButton(discord.ui.Button):
    def __init__(self, move: HoneypotMove) -> None:
        super().__init__(label=move.label, style=STYLES[move.style], row=move.row)
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        action = self.move.action
        if action == LOGS:
            await send_logs(interaction, "honeypot")
            return
        if action in (REFRESH, BACK):
            await back_to_root(interaction, view)
            return
        if action == SETTINGS:
            await open_settings(interaction, view)
            return
        if action == FORGET:
            await open_forget(interaction, view)
            return
        if action == CLEAR_EXEMPT:
            await run_exempt(interaction, [], view)
            return
        await self.open_modal(interaction, view)

    async def open_modal(self, interaction: discord.Interaction, view: Any) -> None:
        if not await still_staff(interaction):
            return
        if not await db_up(interaction):
            return
        bot = interaction.client
        guild = interaction.guild
        if self.move.action == SETUP:
            await interaction.response.send_modal(TrapNameModal(view))
            return
        if self.move.action == PANEL_NUMBERS:
            await interaction.response.send_modal(
                NumbersModal(
                    minutes_for(bot, guild.id),
                    bot.store.get(guild.id, "honeypot_purge_days"),
                    view,
                )
            )


class SiteButton(discord.ui.Button):
    def __init__(self, move: HoneypotMove, url: str) -> None:
        super().__init__(label=move.label, style=discord.ButtonStyle.link, url=url, row=move.row)


class ModePick(discord.ui.Select):
    def __init__(self, current: Any, may_arm: bool) -> None:
        super().__init__(
            placeholder=MODE_PLACEHOLDER,
            options=[
                discord.SelectOption(label=label, value=value, default=now)
                for value, label, now in mode_options(current, may_arm)
            ],
            min_values=1,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_mode(interaction, self.values[0], self.view)


class ExemptPick(discord.ui.RoleSelect):
    """The selection IS the list; **Exempt nobody** is the second door onto the empty case."""

    def __init__(self, stored: list[int]) -> None:
        super().__init__(
            placeholder=EXEMPT_PLACEHOLDER,
            min_values=0,
            max_values=EXEMPT_SELECT_MAX,
            default_values=[discord.Object(id=one) for one in stored],
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_exempt(interaction, [one.id for one in self.values], self.view)


class ForgetPick(discord.ui.Select):
    def __init__(self, options: list[tuple[str, int, bool]]) -> None:
        super().__init__(
            placeholder=FORGET_PLACEHOLDER,
            options=[
                discord.SelectOption(label=label, value=str(ident))
                for label, ident, _live in options[:EXEMPT_SELECT_MAX]
            ],
            min_values=1,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_forget(interaction, int(self.values[0]), self.view)


# --- the modals ----------------------------------------------------------------------------------


class TrapNameModal(AnswersErrors, discord.ui.Modal):
    trap = discord.ui.TextInput(
        label=TRAP_NAME_LABEL, max_length=CHANNEL_NAME_MAX, required=False
    )

    def __init__(self, previous: Any = None) -> None:
        super().__init__(title=TRAP_NAME_TITLE[:45])
        self.previous = previous
        self.trap.default = TRAP_NAME

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_setup(interaction, str(self.trap).strip(), self.previous)


class NumbersModal(AnswersErrors, discord.ui.Modal):
    stays = discord.ui.TextInput(label=PANEL_MINUTES_LABEL, max_length=5)
    purge = discord.ui.TextInput(label=PURGE_DAYS_LABEL_BOUNDED, max_length=2)

    def __init__(self, minutes: Any, days: Any, previous: Any = None) -> None:
        super().__init__(title=NUMBERS_TITLE[:45])
        self.previous = previous
        self.stays.default = str(minutes)
        self.purge.default = str(days)

    def fields(self) -> tuple[tuple[Any, str, str, int], ...]:
        return (
            (self.stays, PANEL_MINUTES_KEY, PANEL_MINUTES_LABEL, 1),
            (self.purge, "honeypot_purge_days", PURGE_DAYS_LABEL_BOUNDED, 0),
        )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """A modal has no Range, so both fields are parsed before either is written."""
        changes: dict[str, Any] = {}
        for item, key, label, floor in self.fields():
            given = str(item).strip()
            if not given.isdigit() or int(given) < floor:
                await answer(
                    interaction,
                    NOT_A_NUMBER.format(given=given[:40] or "nothing", label=label),
                )
                return
            changes[key] = int(given)
        await run_settings(interaction, changes, self.previous)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Honeypot(bot))
