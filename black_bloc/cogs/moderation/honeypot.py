from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from ...actionlog import log_action
from ...command_errors import SafeDynamicItem
from ...settings_store import (
    DB_UNAVAILABLE,
    HONEYPOT_MODES,
    HONEYPOT_PURGE_MAX_DAYS,
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
    "That account was already banned for this post, so nothing changed. `/honeypot status` shows "
    "what the trap has caught."
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
    "set staff_channel_id`, check `/honeypot status` lists the roles you expect, then turn the "
    "trap on again."
)
NO_STAFF_WARNING = (
    "⚠️ **No staff roles resolve.** Only people with Manage Server are exempt, so a moderator "
    "who posts here would be banned. Fix `staff_channel_id` before leaving the trap on."
)
ALREADY_A_TRAP = (
    "This server already has a trap channel — {where} — so a second one was not made. Two traps "
    "are two things to remember; delete that channel, or run `/honeypot forget {channel_id}` if "
    "it is already gone, then run this again."
)
NOT_A_TRAP = (
    "**{channel_id}** is not one of Black Bloc's trap channels, so nothing was forgotten. "
    "`/honeypot status` lists the ones it knows about."
)
NOT_AN_ID = (
    "**{given}** is not a channel id, so nothing was forgotten. Right-click the channel and "
    "choose Copy Channel ID, or read the id out of `/honeypot status`."
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


async def ban_hit(bot: Any, guild: Any, hit_id: int, actor: Any, by: str) -> tuple[str, str]:
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
        "honeypot.banned",
        actor=actor,
        target=hit["user_id"],
        details={"hit_id": hit_id, "by": by},
    )
    return ("banned", f"Banned <@{hit['user_id']}> for that trap post.")


async def make_trap_channel(
    bot: Any, guild: Any, actor: Any, name: str | None = None
) -> tuple[str, str]:
    """Create the trap channel, for slash and web alike: (what happened, what to say)."""
    live = [
        cid
        for cid in (bot.store.get(guild.id, "honeypot_channel_ids") or [])
        if guild.get_channel(cid) is not None
    ]
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
        "honeypot.setup",
        actor=actor,
        details={"channel_id": channel.id, "notice_posted": posted},
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

    honeypot = app_commands.Group(
        name="honeypot", description="The trap channel that catches spam bots"
    )
    exempt = app_commands.Group(
        name="exempt", description="Roles the trap ignores", parent=honeypot
    )

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

    async def _database_ready(self, interaction: discord.Interaction) -> bool:
        if self.bot.db.is_connected:
            return True
        log.warning("honeypot: refused a command — the database is not connected")
        await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
        return False

    @honeypot.command(name="setup", description="Create the trap channel spam bots post in")
    @app_commands.describe(name="What the trap channel is called")
    async def setup_channel(
        self, interaction: discord.Interaction, name: str | None = None
    ) -> None:
        if not await require_staff(interaction):
            return
        if not await self._database_ready(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        _, said = await make_trap_channel(
            self.bot, interaction.guild, interaction.user, name
        )
        await interaction.followup.send(
            said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    async def _post_notice(self, channel: Any) -> bool:
        return await post_notice(self.bot, channel)

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

    def _test_category(self) -> Any:
        return test_category(self.bot)

    @honeypot.command(name="status", description="Show what the trap is set to and has caught")
    async def status(self, interaction: discord.Interaction) -> None:
        if not await require_staff(interaction):
            return
        if not await self._database_ready(interaction):
            return
        guild = interaction.guild
        store = self.bot.store
        channels = store.get(guild.id, "honeypot_channel_ids") or []
        roles = store.get(guild.id, "honeypot_exempt_role_ids") or []
        staff = store.staff_roles(guild)
        mode = store.get(guild.id, "honeypot_mode")
        totals = await hit_counts(self.bot.db, guild.id)
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
        if not staff and mode == "on":
            lines.append(NO_STAFF_WARNING)
        await interaction.response.send_message(
            "\n".join(lines), ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @honeypot.command(name="mode", description="Turn the trap off, to shadow, or on")
    @app_commands.describe(mode="off, shadow (log only) or on (ban whoever posts)")
    @app_commands.choices(
        mode=[app_commands.Choice(name=name, value=name) for name in HONEYPOT_MODES]
    )
    async def mode(
        self, interaction: discord.Interaction, mode: app_commands.Choice[str]
    ) -> None:
        if not await require_staff(interaction):
            return
        if mode.value == "on" and not self.bot.store.staff_roles(interaction.guild):
            await interaction.response.send_message(NO_STAFF_ROLES, ephemeral=True)
            return
        await self.bot.store.set(
            interaction.guild.id, "honeypot_mode", mode.value, by=interaction.user.id
        )
        await interaction.response.send_message(
            f"The trap is now **{mode.value}**.", ephemeral=True
        )
        await log_action(
            self.bot,
            interaction.guild,
            "honeypot.mode",
            actor=interaction.user,
            details={"mode": mode.value},
        )

    @honeypot.command(name="forget", description="Stop treating a channel id as a trap")
    @app_commands.describe(channel_id="The id of the trap channel to forget")
    async def forget(self, interaction: discord.Interaction, channel_id: str) -> None:
        if not await require_staff(interaction):
            return
        guild = interaction.guild
        digits = channel_id.strip().lstrip("<#").rstrip(">")
        if not digits.isdigit():
            await interaction.response.send_message(
                NOT_AN_ID.format(given=channel_id), ephemeral=True
            )
            return
        removed = await self._forget(guild, int(digits), actor=interaction.user)
        if not removed:
            await interaction.response.send_message(
                NOT_A_TRAP.format(channel_id=digits), ephemeral=True
            )
            return
        await interaction.response.send_message(
            FORGOTTEN.format(channel_id=digits), ephemeral=True
        )

    async def _forget(self, guild: Any, channel_id: int, actor: Any = None) -> bool:
        ids = list(self.bot.store.get(guild.id, "honeypot_channel_ids") or [])
        if channel_id not in ids:
            return False
        ids.remove(channel_id)
        await self.bot.store.set(
            guild.id, "honeypot_channel_ids", ids, by=getattr(actor, "id", None)
        )
        await log_action(
            self.bot,
            guild,
            "honeypot.trap_removed",
            actor=actor,
            details={"channel_id": channel_id},
        )
        return True

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        if not self.bot.db.is_connected:
            return
        await self._forget(channel.guild, channel.id)

    @exempt.command(name="add", description="Let a role post in the trap without being banned")
    async def exempt_add(self, interaction: discord.Interaction, role: discord.Role) -> None:
        await self._change_exempt(interaction, role, add=True)

    @exempt.command(name="remove", description="Stop exempting a role from the trap")
    async def exempt_remove(self, interaction: discord.Interaction, role: discord.Role) -> None:
        await self._change_exempt(interaction, role, add=False)

    async def _change_exempt(
        self, interaction: discord.Interaction, role: discord.Role, *, add: bool
    ) -> None:
        if not await require_staff(interaction):
            return
        guild = interaction.guild
        ids = list(self.bot.store.get(guild.id, "honeypot_exempt_role_ids") or [])
        if add and role.id not in ids:
            ids.append(role.id)
        elif not add and role.id in ids:
            ids.remove(role.id)
        else:
            await interaction.response.send_message(
                f"**{role.name}** was already "
                + ("exempt" if add else "not exempt")
                + ", so nothing changed. `/honeypot status` lists the exempt roles.",
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        await self.bot.store.set(
            guild.id, "honeypot_exempt_role_ids", ids, by=interaction.user.id
        )
        await interaction.response.send_message(
            f"**{role.name}** is "
            + ("exempt from the trap now." if add else "no longer exempt from the trap."),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await log_action(
            self.bot,
            guild,
            "honeypot.exempt_add" if add else "honeypot.exempt_remove",
            actor=interaction.user,
            details={"role_id": role.id},
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Honeypot(bot))
