from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from ...actionlog import log_action
from ...settings_store import DB_UNAVAILABLE, HONEYPOT_MODES, require_staff

log = logging.getLogger(__name__)

TRAP_NAME = "🍯-do-not-post-here"
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
NOTICE_NOT_POSTED = (
    "The pinned notice was not posted, because test mode keeps Black Bloc out of every channel "
    "but the test one. Post it by hand for now, or run this again once test mode is off."
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
    try:
        await guild.ban(
            user,
            reason=f"Honeypot: posted in #{channel_name}",
            delete_message_days=purge_days,
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


class BanNowButton(discord.ui.DynamicItem[discord.ui.Button], template=BAN_TEMPLATE):
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

    async def callback(self, interaction: discord.Interaction) -> None:
        bot = interaction.client
        if not await require_staff(interaction):
            return
        if not bot.db.is_connected:
            await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
            return
        hit = await get_hit(bot.db, self.hit_id)
        if hit is None:
            await interaction.response.send_message(NO_SUCH_HIT, ephemeral=True)
            return
        if hit["action"] == "banned":
            await interaction.response.send_message(ALREADY_BANNED, ephemeral=True)
            return
        guild = interaction.guild
        channel = bot.get_channel(hit["channel_id"])
        failure = await do_ban(
            bot,
            guild,
            hit["user_id"],
            getattr(channel, "name", "the trap channel"),
            int(bot.store.get(guild.id, "honeypot_purge_days") or 0),
        )
        if failure == "test_mode":
            await interaction.response.send_message(BAN_IN_TEST_MODE, ephemeral=True)
            await log_action(
                bot,
                guild,
                "honeypot.would_ban",
                actor=interaction.user,
                target=hit["user_id"],
                details={"hit_id": self.hit_id, "reason": "test_mode", "by": "button"},
            )
            return
        if failure is not None:
            await interaction.response.send_message(BAN_REFUSED, ephemeral=True)
            await set_hit_action(bot.db, self.hit_id, "ban_failed")
            await log_action(
                bot,
                guild,
                "honeypot.ban_failed",
                actor=interaction.user,
                target=hit["user_id"],
                details={"hit_id": self.hit_id, "reason": failure, "by": "button"},
            )
            return
        await set_hit_action(bot.db, self.hit_id, "banned")
        await interaction.response.send_message(
            f"Banned <@{hit['user_id']}> for that trap post.",
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await log_action(
            bot,
            guild,
            "honeypot.banned",
            actor=interaction.user,
            target=hit["user_id"],
            details={"hit_id": self.hit_id, "by": "button"},
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
        me = getattr(self.bot, "user", None)
        if me is not None and message.author.id == me.id:
            return
        if not self.bot.db.is_connected:
            return
        store = self.bot.store
        mode = store.get(message.guild.id, "honeypot_mode")
        if mode == "off":
            return
        if message.channel.id not in (store.get(message.guild.id, "honeypot_channel_ids") or []):
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
        await log_action(
            self.bot, guild, "honeypot.would_ban", target=author, details=details
        )
        await self._offer_ban(guild, hit_id, author.id, content)

    async def _delete(self, message: discord.Message) -> None:
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
        guild = interaction.guild
        category = self._test_category()
        if category is False:
            await interaction.response.send_message(
                "Black Bloc is in test mode and cannot see its test channel, so no trap was "
                "made. Set TEST_CHANNEL_ID to a channel the bot can read, restart it, then run "
                "this again.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True)
        try:
            channel = await guild.create_text_channel(
                name or TRAP_NAME,
                category=category or None,
                position=len(list(guild.text_channels)),
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(
                        view_channel=True, send_messages=True
                    )
                },
                slowmode_delay=0,
                reason="Black Bloc honeypot",
            )
        except discord.HTTPException as exc:
            log.warning("honeypot: setup could not create the trap channel: %s", exc)
            await interaction.followup.send(CANNOT_CREATE, ephemeral=True)
            return
        ids = list(self.bot.store.get(guild.id, "honeypot_channel_ids") or [])
        if channel.id not in ids:
            ids.append(channel.id)
        await self.bot.store.set(
            guild.id, "honeypot_channel_ids", ids, by=interaction.user.id
        )
        posted = await self._post_notice(channel)
        mode = self.bot.store.get(guild.id, "honeypot_mode")
        await interaction.followup.send(
            f"{channel.mention} is the trap, and the mode is **{mode}**. "
            + ("Its notice is posted and pinned." if posted else NOTICE_NOT_POSTED),
            ephemeral=True,
        )
        await log_action(
            self.bot,
            guild,
            "honeypot.setup",
            actor=interaction.user,
            details={"channel_id": channel.id, "notice_posted": posted},
        )

    async def _post_notice(self, channel: Any) -> bool:
        guard = getattr(self.bot, "guard", None)
        if guard is not None and not guard.allows_channel(channel.id):
            log.warning("honeypot: TEST MODE — the trap notice was not posted in %s", channel.id)
            return False
        try:
            message = await channel.send(
                NOTICE, allowed_mentions=discord.AllowedMentions.none()
            )
            await message.pin(reason="Black Bloc honeypot")
        except Exception as exc:
            log.warning("honeypot: could not post the notice in %s: %s", channel.id, exc)
            return False
        return True

    def _test_category(self) -> Any:
        """The test channel's category while the guard is on; None when it is off."""
        guard = getattr(self.bot, "guard", None)
        if guard is None:
            return None
        test_channel = (
            self.bot.get_channel(guard.test_channel_id) if guard.test_channel_id else None
        )
        if test_channel is None:
            return False
        return test_channel.category

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
        totals = await hit_counts(self.bot.db, guild.id)
        lines = [
            f"**mode** — {store.get(guild.id, 'honeypot_mode')}",
            "**trap channels** — "
            + (", ".join(f"<#{c}>" for c in channels) if channels else "not set up yet"),
            f"**purge** — {store.get(guild.id, 'honeypot_purge_days')} day(s) of their messages",
            "**exempt roles** — "
            + (", ".join(f"<@&{r}>" for r in roles) if roles else "staff only"),
            f"**caught** — {totals.get('banned', 0)} banned · "
            f"{totals.get('would_ban', 0)} logged in shadow · "
            f"{totals.get('ban_failed', 0)} failed · {totals.get('exempt', 0)} ignored",
        ]
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
