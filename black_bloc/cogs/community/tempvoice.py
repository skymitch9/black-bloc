from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ...actionlog import log_action
from ...command_errors import AnswersErrors
from ...golive import now_iso, parse_ts
from ...settings_store import (
    DB_UNAVAILABLE,
    TEMPVOICE_MODES,
    TEMPVOICE_NAME_TEMPLATE,
    require_staff,
)

log = logging.getLogger(__name__)

CREATOR_NAME = "join to create a channel"
AFK_FALLBACK_NAME = "You Still Here?"
PANEL_PREFIX = "tempvoice"
RECONCILE_GRACE_SECONDS = 60
RECONCILE_MINUTES = 5
NAME_LIMIT = 100
LOCKS_ATTR = "_tempvoice_channel_locks"

NOT_A_TEMP_CHANNEL = (
    "This panel is not attached to a temporary voice channel any more, so nothing was changed. "
    "Join the join-to-create channel again to get a fresh one."
)
NOT_ALLOWED = (
    "Black Bloc did not make you a voice channel because join-to-create is for members with the "
    "<@&{role_id}> role. Ask a Lead for that role, then join the channel again."
)
CANNOT_EDIT = (
    "Discord refused that change, so nothing happened. Black Bloc needs the Manage Channels and "
    "Move Members permissions in this category. Ask a Lead to check them, then try again."
)
NOT_IN_CHANNEL = (
    "**{name}** is not in this channel, so nothing was changed. They have to be connected here "
    "before they can be moved out."
)
OWNER_STILL_HERE = (
    "This channel still belongs to <@{owner_id}>, and they are still in it, so it cannot be "
    "claimed. Ask them to hand it over with the Transfer button."
)
NO_TEST_CHANNEL = (
    "Black Bloc is in test mode and cannot see its test channel, so no channel was created. Set "
    "TEST_CHANNEL_ID to a channel the bot can read, restart it, then run this again."
)
CANNOT_CREATE = (
    "Discord refused to create the channel, so nothing was made. Black Bloc needs the Manage "
    "Channels permission in this server. Ask an admin to give it that, then run this again."
)
CLAIM_LOST = (
    "Someone else just claimed this channel, so nothing was changed. Ask them to hand it over "
    "with the Transfer button, or make your own by joining the join-to-create channel."
)
CLAIM_NEEDS_CONNECTION = (
    "You have to be connected to this channel before you can claim it, so nothing was changed. "
    "Join the voice channel, then press Claim again."
)
ALREADY_A_LOBBY = (
    "This server already has a join-to-create channel — {where} — so a second one was not made. "
    "Delete that channel, or run `/tempvoice forget {channel_id}` if it is already gone, then "
    "run this again."
)
NOT_A_LOBBY = (
    "**{channel_id}** is not one of Black Bloc's join-to-create channels, so nothing was "
    "forgotten. `/tempvoice status` lists the ones it knows about."
)
NOT_AN_ID = (
    "**{given}** is not a channel id, so nothing was forgotten. Right-click the channel and "
    "choose Copy Channel ID, or read the id out of `/tempvoice status`."
)
FORGOTTEN = (
    "Black Bloc has forgotten **{channel_id}** — joining it no longer makes anybody a temporary "
    "channel."
)


def channel_name(template: str, member_name: str, saved: str | None = None) -> str:
    """A spawned channel's name: the member's remembered one, else the rendered template."""
    name = (saved or "").strip()
    if not name:
        try:
            name = template.format(user=member_name).strip()
        except Exception:
            log.warning("temp voice: the name template %r could not be rendered", template)
            name = TEMPVOICE_NAME_TEMPLATE.format(user=member_name)
    return name[:NAME_LIMIT] or TEMPVOICE_NAME_TEMPLATE.format(user=member_name)[:NAME_LIMIT]


def bottom_position(positions: Any) -> int:
    values = [int(p) for p in positions]
    return max(values) + 1 if values else 0


def creator_position(afk_position: int | None, fallback: int) -> int:
    """Taking the AFK channel's own slot puts the new channel directly above it."""
    if afk_position is None:
        return max(fallback, 0)
    return max(afk_position, 0)


def spawn_position(creator: int) -> int:
    return max(creator, 0) + 1


def parse_limit(raw: str) -> int | None:
    text = raw.strip()
    if not text.isdigit():
        return None
    value = int(text)
    return value if 0 <= value <= 99 else None


def is_panel_owner(owner_id: Any, clicker_id: Any) -> bool:
    return int(owner_id) == int(clicker_id)


def not_owner_message(owner_id: int) -> str:
    return (
        f"This panel belongs to <@{owner_id}>, so nothing was changed. Make your own channel by "
        "joining the join-to-create channel, or ask them to use the Permit button."
    )


def is_stale(created_at: Any, now: datetime, grace_seconds: int) -> bool:
    """An empty channel old enough to delete; an unreadable timestamp counts as old."""
    started = parse_ts(created_at)
    if started is None:
        return True
    return (now - started).total_seconds() >= grace_seconds


def panel_id(action: str) -> str:
    return f"{PANEL_PREFIX}:{action}"


def channel_lock(bot: Any, channel_id: int) -> asyncio.Lock:
    locks = getattr(bot, LOCKS_ATTR, None)
    if locks is None:
        locks = {}
        setattr(bot, LOCKS_ATTR, locks)
    lock = locks.get(channel_id)
    if lock is None:
        lock = locks[channel_id] = asyncio.Lock()
    return lock


def connected_ids(channel: Any) -> set[int]:
    """Who Discord says is in the voice channel right now."""
    return {int(user_id) for user_id in getattr(channel, "voice_states", {})}


def owner_overwrites(guild: Any, member: Any, *, locked: bool = False, hidden: bool = False) -> Any:
    everyone = discord.PermissionOverwrite()
    if locked:
        everyone.connect = False
    if hidden:
        everyone.view_channel = False
    return {
        guild.default_role: everyone,
        member: discord.PermissionOverwrite(
            view_channel=True,
            connect=True,
            manage_channels=True,
            move_members=True,
            mute_members=True,
            deafen_members=True,
        ),
    }


def panel_text(member: Any) -> str:
    return (
        f"**{member.display_name}'s channel** — the buttons below belong to <@{member.id}>. "
        "Rename it, cap it, lock it, hide it, or hand it to someone else."
    )


async def add_channel(
    db: Any, channel_id: int, guild_id: int, owner_id: int, creator_id: int
) -> None:
    await db.conn.execute(
        "INSERT OR REPLACE INTO tempvoice_channels(channel_id, guild_id, owner_id, creator_id, "
        "created_at) VALUES (?, ?, ?, ?, ?)",
        (channel_id, guild_id, owner_id, creator_id, now_iso()),
    )
    await db.conn.commit()


async def get_row(db: Any, channel_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM tempvoice_channels WHERE channel_id = ?", (channel_id,)
    )
    return await cur.fetchone()


async def rows_for_guild(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM tempvoice_channels WHERE guild_id = ? ORDER BY channel_id", (guild_id,)
    )
    return list(await cur.fetchall())


async def delete_row(db: Any, channel_id: int) -> bool:
    cur = await db.conn.execute(
        "DELETE FROM tempvoice_channels WHERE channel_id = ?", (channel_id,)
    )
    await db.conn.commit()
    return cur.rowcount > 0


async def set_panel_message(db: Any, channel_id: int, message_id: int) -> None:
    await db.conn.execute(
        "UPDATE tempvoice_channels SET panel_message_id = ? WHERE channel_id = ?",
        (message_id, channel_id),
    )
    await db.conn.commit()


async def set_owner(db: Any, channel_id: int, owner_id: int) -> None:
    await db.conn.execute(
        "UPDATE tempvoice_channels SET owner_id = ? WHERE channel_id = ?", (owner_id, channel_id)
    )
    await db.conn.commit()


async def get_prefs(db: Any, user_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM tempvoice_prefs WHERE user_id = ?", (user_id,))
    return await cur.fetchone()


async def save_prefs(
    db: Any,
    user_id: int,
    *,
    name: str | None = None,
    user_limit: int | None = None,
    locked: bool | None = None,
    hidden: bool | None = None,
) -> None:
    """Remember one setting for next time; the others keep whatever they already were."""
    row = await get_prefs(db, user_id)
    current = {"name": None, "user_limit": None, "locked": 0, "hidden": 0}
    if row is not None:
        current = {key: row[key] for key in current}
    given = {"name": name, "user_limit": user_limit, "locked": locked, "hidden": hidden}
    merged = {key: (current[key] if value is None else value) for key, value in given.items()}
    await db.conn.execute(
        "INSERT OR REPLACE INTO tempvoice_prefs(user_id, name, user_limit, locked, hidden) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            user_id,
            merged["name"],
            merged["user_limit"],
            int(bool(merged["locked"])),
            int(bool(merged["hidden"])),
        ),
    )
    await db.conn.commit()


def pref(row: Any, key: str) -> Any:
    if row is None:
        return None
    try:
        return row[key]
    except (IndexError, KeyError):
        return None


def creator_spot(bot: Any, guild: Any) -> tuple[Any, int, str]:
    guard = getattr(bot, "guard", None)
    if guard is not None:
        test_channel = bot.get_channel(guard.test_channel_id) if guard.test_channel_id else None
        if test_channel is None:
            return None, 0, "no_test_channel"
        category = test_channel.category
        voice = list(getattr(category, "voice_channels", ())) if category is not None else []
        return category, bottom_position(c.position for c in voice), "test_category"
    afk = getattr(guild, "afk_channel", None)
    if afk is None:
        afk = next((c for c in guild.voice_channels if c.name == AFK_FALLBACK_NAME), None)
    if afk is not None:
        return afk.category, creator_position(afk.position, 0), "above_afk"
    return None, bottom_position(c.position for c in guild.voice_channels), "bottom"


def where_sentence(where: str) -> str:
    if where == "test_category":
        return (
            "Test mode is on, so it went in the test channel's category — join it there to "
            "try it. Run `/tempvoice setup` again once test mode is off and it will go "
            "directly above the AFK channel."
        )
    if where == "above_afk":
        return "It sits directly above the AFK channel, as asked."
    return (
        "Black Bloc could not find an AFK channel to sit above, so it went to the bottom of "
        "the list — drag it where you want it."
    )


async def make_creator_channel(
    bot: Any, guild: Any, actor: Any, name: str | None = None
) -> tuple[str, str]:
    """Set up join-to-create, for slash and web alike: (what happened, what to say)."""
    live = [
        cid
        for cid in (bot.store.get(guild.id, "tempvoice_creator_ids") or [])
        if guild.get_channel(cid) is not None
    ]
    if live:
        return (
            "already",
            ALREADY_A_LOBBY.format(where=f"<#{live[0]}>", channel_id=live[0]),
        )
    category, position, where = creator_spot(bot, guild)
    if where == "no_test_channel":
        return ("no_test_channel", NO_TEST_CHANNEL)
    try:
        channel = await guild.create_voice_channel(
            name or CREATOR_NAME,
            category=category,
            position=position,
            reason="Black Bloc temp voice: join-to-create",
        )
    except discord.HTTPException as exc:
        log.warning("temp voice: setup could not create the creator channel: %s", exc)
        return ("refused", CANNOT_CREATE)
    ids = list(bot.store.get(guild.id, "tempvoice_creator_ids") or [])
    if channel.id not in ids:
        ids.append(channel.id)
    await bot.store.set(
        guild.id, "tempvoice_creator_ids", ids, by=getattr(actor, "id", actor)
    )
    await log_action(
        bot,
        guild,
        "tempvoice.setup",
        actor=actor,
        details={"channel_id": channel.id, "placed": where},
    )
    return (
        "created",
        f"**{channel.name}** is ready — {channel.mention}. {where_sentence(where)}",
    )


async def panel_context(interaction: discord.Interaction, *, owner_only: bool = True) -> Any:
    """This click's temp-channel row, or None once the clicker has been answered."""
    bot = interaction.client
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(interaction.channel_id):
        await interaction.response.send_message(guard.refusal_message(), ephemeral=True)
        return None
    if not bot.db.is_connected:
        await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
        return None
    row = await get_row(bot.db, interaction.channel_id)
    if row is None:
        await interaction.response.send_message(NOT_A_TEMP_CHANNEL, ephemeral=True)
        return None
    if owner_only and not is_panel_owner(row["owner_id"], interaction.user.id):
        await interaction.response.send_message(
            not_owner_message(row["owner_id"]),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        return None
    return row


async def panel_log(interaction: discord.Interaction, kind: str, **details: Any) -> None:
    await log_action(
        interaction.client,
        interaction.guild,
        f"tempvoice.{kind}",
        actor=interaction.user,
        details={"channel_id": interaction.channel_id} | details,
    )


async def answer(interaction: discord.Interaction, text: str) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(
            text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )
        return
    await interaction.response.send_message(
        text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )


class RenameModal(AnswersErrors, discord.ui.Modal, title="Rename this channel"):
    name = discord.ui.TextInput(label="New name", max_length=NAME_LIMIT)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        row = await panel_context(interaction)
        if row is None:
            return
        await interaction.response.defer(ephemeral=True)
        wanted = str(self.name).strip()[:NAME_LIMIT]
        if not wanted:
            await answer(interaction, "A channel needs a name, so nothing was changed.")
            return
        try:
            await interaction.channel.edit(name=wanted, reason="Black Bloc temp voice")
        except discord.HTTPException as exc:
            log.warning("temp voice: rename refused in %s: %s", interaction.channel_id, exc)
            await answer(interaction, CANNOT_EDIT)
            return
        await save_prefs(interaction.client.db, row["owner_id"], name=wanted)
        await panel_log(interaction, "rename", name=wanted)
        await answer(interaction, f"Renamed to **{wanted}**, and remembered for next time.")


class LimitModal(AnswersErrors, discord.ui.Modal, title="How many people?"):
    limit = discord.ui.TextInput(label="0 to 99 (0 means no limit)", max_length=2)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        row = await panel_context(interaction)
        if row is None:
            return
        await interaction.response.defer(ephemeral=True)
        value = parse_limit(str(self.limit))
        if value is None:
            await answer(
                interaction,
                "That is not a number between 0 and 99, so nothing was changed. Type a whole "
                "number — 0 lets anyone in.",
            )
            return
        try:
            await interaction.channel.edit(user_limit=value, reason="Black Bloc temp voice")
        except discord.HTTPException as exc:
            log.warning("temp voice: limit refused in %s: %s", interaction.channel_id, exc)
            await answer(interaction, CANNOT_EDIT)
            return
        await save_prefs(interaction.client.db, row["owner_id"], user_limit=value)
        await panel_log(interaction, "limit", user_limit=value)
        await answer(
            interaction,
            "Anyone can join now." if value == 0 else f"Capped at **{value}** people.",
        )


class MemberPick(discord.ui.UserSelect):
    def __init__(self, action: str, placeholder: str) -> None:
        super().__init__(placeholder=placeholder, min_values=1, max_values=1)
        self.action = action

    async def callback(self, interaction: discord.Interaction) -> None:
        row = await panel_context(interaction)
        if row is None:
            return
        await interaction.response.defer(ephemeral=True)
        target = self.values[0]
        channel = interaction.channel
        handler = getattr(self, f"_{self.action}")
        await handler(interaction, channel, target, row)

    async def _kick(self, interaction: Any, channel: Any, target: Any, row: Any) -> None:
        if target.id not in connected_ids(channel):
            await answer(interaction, NOT_IN_CHANNEL.format(name=target.display_name))
            return
        if not await self._move_out(interaction, target):
            return
        await panel_log(interaction, "kick", target_id=target.id)
        await answer(interaction, f"Moved **{target.display_name}** out of the channel.")

    async def _ban(self, interaction: Any, channel: Any, target: Any, row: Any) -> None:
        try:
            await channel.set_permissions(
                target,
                connect=False,
                view_channel=False,
                reason="Black Bloc temp voice: banned",
            )
        except discord.HTTPException as exc:
            log.warning("temp voice: ban refused in %s: %s", channel.id, exc)
            await panel_log(interaction, "ban_failed", target_id=target.id, reason=str(exc))
            await answer(interaction, CANNOT_EDIT)
            return
        if target.id in connected_ids(channel):
            await self._move_out(interaction, target, answered=False)
        await panel_log(interaction, "ban", target_id=target.id)
        await answer(
            interaction,
            f"**{target.display_name}** can no longer join this channel. The Permit button "
            "undoes it.",
        )

    async def _permit(self, interaction: Any, channel: Any, target: Any, row: Any) -> None:
        try:
            await channel.set_permissions(
                target, connect=True, view_channel=True, reason="Black Bloc temp voice: permitted"
            )
        except discord.HTTPException as exc:
            log.warning("temp voice: permit refused in %s: %s", channel.id, exc)
            await panel_log(interaction, "permit_failed", target_id=target.id, reason=str(exc))
            await answer(interaction, CANNOT_EDIT)
            return
        await panel_log(interaction, "permit", target_id=target.id)
        await answer(interaction, f"**{target.display_name}** can join this channel now.")

    async def _transfer(self, interaction: Any, channel: Any, target: Any, row: Any) -> None:
        async with channel_lock(interaction.client, channel.id):
            fresh = await get_row(interaction.client.db, channel.id)
            if fresh is None:
                await answer(interaction, NOT_A_TEMP_CHANNEL)
                return
            if int(fresh["owner_id"]) != int(row["owner_id"]):
                await answer(interaction, CLAIM_LOST)
                return
            await hand_over(interaction.client, channel, fresh["owner_id"], target)
            await panel_log(
                interaction, "transfer", target_id=target.id, from_id=fresh["owner_id"]
            )
        await answer(interaction, f"**{target.display_name}** owns this channel now.")

    async def _move_out(self, interaction: Any, target: Any, *, answered: bool = True) -> bool:
        try:
            await target.move_to(None, reason="Black Bloc temp voice")
        except discord.HTTPException as exc:
            log.warning("temp voice: could not move %s out: %s", target.id, exc)
            if answered:
                await answer(interaction, CANNOT_EDIT)
            return False
        return True


class MemberPickView(AnswersErrors, discord.ui.View):
    def __init__(self, action: str, placeholder: str) -> None:
        super().__init__(timeout=180)
        self.add_item(MemberPick(action, placeholder))


async def hand_over(bot: Any, channel: Any, old_owner_id: int, new_owner: Any) -> None:
    """Move the owner overwrite to the new owner and record them on the row."""
    await set_owner(bot.db, channel.id, new_owner.id)
    old = channel.guild.get_member(old_owner_id)
    try:
        if old is not None and old.id != new_owner.id:
            await channel.set_permissions(old, overwrite=None, reason="Black Bloc temp voice")
        await channel.set_permissions(
            new_owner,
            overwrite=owner_overwrites(channel.guild, new_owner)[new_owner],
            reason="Black Bloc temp voice",
        )
    except discord.HTTPException as exc:
        log.warning("temp voice: could not move the owner overwrite in %s: %s", channel.id, exc)


class TempVoicePanel(AnswersErrors, discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Rename", custom_id=panel_id("rename"), row=0)
    async def rename(self, interaction: discord.Interaction, button: Any) -> None:
        if await panel_context(interaction) is None:
            return
        await interaction.response.send_modal(RenameModal())

    @discord.ui.button(label="Limit", custom_id=panel_id("limit"), row=0)
    async def limit(self, interaction: discord.Interaction, button: Any) -> None:
        if await panel_context(interaction) is None:
            return
        await interaction.response.send_modal(LimitModal())

    @discord.ui.button(label="Lock / Unlock", custom_id=panel_id("lock"), row=0)
    async def lock(self, interaction: discord.Interaction, button: Any) -> None:
        row = await panel_context(interaction)
        if row is None:
            return
        await self._toggle(interaction, row, "connect")

    @discord.ui.button(label="Hide / Show", custom_id=panel_id("hide"), row=0)
    async def hide(self, interaction: discord.Interaction, button: Any) -> None:
        row = await panel_context(interaction)
        if row is None:
            return
        await self._toggle(interaction, row, "view_channel")

    @discord.ui.button(label="Kick", custom_id=panel_id("kick"), row=1)
    async def kick(self, interaction: discord.Interaction, button: Any) -> None:
        await self._pick(interaction, "kick", "Who should leave this channel?")

    @discord.ui.button(label="Ban", custom_id=panel_id("ban"), row=1)
    async def ban(self, interaction: discord.Interaction, button: Any) -> None:
        await self._pick(interaction, "ban", "Who should be kept out of this channel?")

    @discord.ui.button(label="Permit", custom_id=panel_id("permit"), row=1)
    async def permit(self, interaction: discord.Interaction, button: Any) -> None:
        await self._pick(interaction, "permit", "Who should be let in?")

    @discord.ui.button(label="Transfer", custom_id=panel_id("transfer"), row=2)
    async def transfer(self, interaction: discord.Interaction, button: Any) -> None:
        await self._pick(interaction, "transfer", "Who should own this channel?")

    @discord.ui.button(label="Claim", custom_id=panel_id("claim"), row=2)
    async def claim(self, interaction: discord.Interaction, button: Any) -> None:
        row = await panel_context(interaction, owner_only=False)
        if row is None:
            return
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel
        async with channel_lock(interaction.client, channel.id):
            fresh = await get_row(interaction.client.db, channel.id)
            if fresh is None:
                await answer(interaction, NOT_A_TEMP_CHANNEL)
                return
            owner_id = fresh["owner_id"]
            if is_panel_owner(owner_id, interaction.user.id):
                await answer(interaction, "You already own this channel, so nothing changed.")
                return
            if int(owner_id) != int(row["owner_id"]):
                await answer(interaction, CLAIM_LOST)
                return
            here = connected_ids(channel)
            if interaction.user.id not in here:
                await answer(interaction, CLAIM_NEEDS_CONNECTION)
                return
            if owner_id in here:
                await answer(interaction, OWNER_STILL_HERE.format(owner_id=owner_id))
                return
            await hand_over(interaction.client, channel, owner_id, interaction.user)
            await panel_log(interaction, "claim", from_id=owner_id)
        await answer(interaction, "This channel is yours now.")

    async def _pick(self, interaction: discord.Interaction, action: str, placeholder: str) -> None:
        if await panel_context(interaction) is None:
            return
        await interaction.response.send_message(
            placeholder, view=MemberPickView(action, placeholder), ephemeral=True
        )

    async def _toggle(self, interaction: discord.Interaction, row: Any, permission: str) -> None:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        channel = interaction.channel
        everyone = channel.guild.default_role
        overwrite = channel.overwrites_for(everyone)
        was_off = getattr(overwrite, permission) is False
        setattr(overwrite, permission, None if was_off else False)
        try:
            await channel.set_permissions(
                everyone, overwrite=overwrite, reason="Black Bloc temp voice"
            )
        except discord.HTTPException as exc:
            log.warning("temp voice: %s toggle refused in %s: %s", permission, channel.id, exc)
            await answer(interaction, CANNOT_EDIT)
            return
        locking = permission == "connect"
        if locking:
            await save_prefs(interaction.client.db, row["owner_id"], locked=not was_off)
            said = "Unlocked — anyone may join." if was_off else "Locked — nobody new may join."
            kind = "unlock" if was_off else "lock"
        else:
            await save_prefs(interaction.client.db, row["owner_id"], hidden=not was_off)
            said = (
                "Visible again to everyone."
                if was_off
                else "Hidden — only people already in it can see it."
            )
            kind = "show" if was_off else "hide"
        await panel_log(interaction, kind)
        await answer(interaction, said)


class TempVoice(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._creator_locks: dict[int, asyncio.Lock] = {}

    tempvoice = app_commands.Group(
        name="tempvoice", description="Temporary voice channels people make by joining one"
    )

    async def cog_load(self) -> None:
        self.bot.add_view(TempVoicePanel())
        if not self.bot.db.is_connected:
            return
        await self.reconcile_channels()
        self._reconcile_loop.start()

    async def cog_unload(self) -> None:
        self._reconcile_loop.cancel()

    @tasks.loop(minutes=RECONCILE_MINUTES)
    async def _reconcile_loop(self) -> None:
        if self.bot.db.is_connected:
            await self.reconcile_channels()

    @_reconcile_loop.before_loop
    async def _before_reconcile(self) -> None:
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self.bot.db.is_connected:
            await self.reconcile_channels()

    async def reconcile_channels(self) -> None:
        """Forget rows whose channel is gone, and delete temp channels nobody is in."""
        now = datetime.now(UTC)
        for guild in list(getattr(self.bot, "guilds", ())):
            for row in await rows_for_guild(self.bot.db, guild.id):
                channel = guild.get_channel(row["channel_id"])
                if channel is None:
                    await delete_row(self.bot.db, row["channel_id"])
                    log.info("temp voice: forgot channel %s — it is gone", row["channel_id"])
                    continue
                if connected_ids(channel):
                    continue
                if not is_stale(row["created_at"], now, RECONCILE_GRACE_SECONDS):
                    continue
                await self._delete_channel(guild, channel, "reconciled")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        if member.bot or not self.bot.db.is_connected:
            return
        left = before.channel
        joined = after.channel
        if left is not None and (joined is None or joined.id != left.id):
            await self._maybe_delete(member.guild, left)
        if joined is not None and (left is None or left.id != joined.id):
            await self._maybe_create(member, joined)

    async def _maybe_delete(self, guild: Any, channel: Any) -> None:
        if await get_row(self.bot.db, channel.id) is None:
            return
        if connected_ids(channel):
            return
        await self._delete_channel(guild, channel, "empty")

    async def _delete_channel(self, guild: Any, channel: Any, reason: str) -> None:
        async with channel_lock(self.bot, channel.id):
            row = await get_row(self.bot.db, channel.id)
            if row is None:
                return
            try:
                await channel.delete(reason="Black Bloc temp voice: nobody left in it")
            except discord.HTTPException as exc:
                log.warning("temp voice: could not delete channel %s: %s", channel.id, exc)
                await log_action(
                    self.bot,
                    guild,
                    "tempvoice.delete_failed",
                    details={
                        "channel_id": channel.id,
                        "reason": f"{type(exc).__name__}: {exc}",
                    },
                )
                return
            await delete_row(self.bot.db, channel.id)
            await log_action(
                self.bot,
                guild,
                "tempvoice.delete",
                target=row["owner_id"],
                details={"channel_id": channel.id, "reason": reason},
            )

    async def _maybe_create(self, member: Any, channel: Any) -> None:
        guild = member.guild
        store = self.bot.store
        if store.get(guild.id, "tempvoice_mode") != "on":
            return
        if channel.id not in (store.get(guild.id, "tempvoice_creator_ids") or []):
            return
        if not self._may_act_in(channel):
            log.warning(
                "temp voice: TEST MODE — ignoring the creator channel %s outside the test "
                "channel's category",
                channel.id,
            )
            return
        async with self._lock(self._creator_locks, channel.id):
            await self._create_for(member, channel)

    async def _create_for(self, member: Any, creator: Any) -> None:
        guild = member.guild
        store = self.bot.store
        role_id = store.get(guild.id, "tempvoice_allowed_role_id")
        if role_id and not any(r.id == role_id for r in getattr(member, "roles", ())):
            await self._turn_away(member, role_id)
            return
        prefs = await get_prefs(self.bot.db, member.id)
        name = channel_name(
            store.get(guild.id, "tempvoice_name_template"),
            member.display_name,
            pref(prefs, "name"),
        )
        try:
            channel = await guild.create_voice_channel(
                name,
                category=creator.category,
                position=spawn_position(creator.position),
                overwrites=owner_overwrites(
                    guild,
                    member,
                    locked=bool(pref(prefs, "locked")),
                    hidden=bool(pref(prefs, "hidden")),
                ),
                user_limit=int(pref(prefs, "user_limit") or 0),
                reason=f"Black Bloc temp voice for {member}",
            )
        except discord.HTTPException as exc:
            log.warning("temp voice: could not create a channel for %s: %s", member.id, exc)
            await log_action(
                self.bot,
                guild,
                "tempvoice.create_failed",
                target=member,
                details={"reason": f"{type(exc).__name__}: {exc}"},
            )
            return
        await add_channel(self.bot.db, channel.id, guild.id, member.id, creator.id)
        await log_action(
            self.bot,
            guild,
            "tempvoice.create",
            actor=member,
            target=member,
            details={"channel_id": channel.id, "name": name},
        )
        try:
            await member.move_to(channel, reason="Black Bloc temp voice")
        except discord.HTTPException as exc:
            log.warning("temp voice: could not move %s into %s: %s", member.id, channel.id, exc)
            await log_action(
                self.bot,
                guild,
                "tempvoice.move_failed",
                target=member,
                details={"channel_id": channel.id, "reason": f"{type(exc).__name__}: {exc}"},
            )
        await self._post_panel(guild, channel, member)

    async def _turn_away(self, member: Any, role_id: int) -> None:
        guild = member.guild
        try:
            await member.move_to(
                getattr(guild, "afk_channel", None), reason="Black Bloc temp voice: not a member"
            )
        except discord.HTTPException as exc:
            log.warning("temp voice: could not move %s out of the creator: %s", member.id, exc)
        try:
            await member.send(
                NOT_ALLOWED.format(role_id=role_id),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException as exc:
            log.info("temp voice: could not DM %s about the missing role: %s", member.id, exc)
        await log_action(
            self.bot,
            guild,
            "tempvoice.turned_away",
            target=member,
            details={"role_id": role_id},
        )

    async def _post_panel(self, guild: Any, channel: Any, member: Any) -> None:
        guard = getattr(self.bot, "guard", None)
        if guard is not None and not guard.allows_channel(channel.id):
            log.warning("temp voice: TEST MODE — no control panel posted in %s", channel.id)
            await log_action(
                self.bot,
                guild,
                "tempvoice.would_post_panel",
                target=member,
                details={"channel_id": channel.id},
            )
            return
        try:
            message = await channel.send(
                panel_text(member),
                view=TempVoicePanel(),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except Exception as exc:
            log.warning("temp voice: could not post the panel in %s: %s", channel.id, exc)
            await log_action(
                self.bot,
                guild,
                "tempvoice.panel_failed",
                target=member,
                details={"channel_id": channel.id, "reason": f"{type(exc).__name__}: {exc}"},
            )
            return
        await set_panel_message(self.bot.db, channel.id, message.id)

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

    def _creator_spot(self, guild: Any) -> tuple[Any, int, str]:
        return creator_spot(self.bot, guild)

    def _lock(self, locks: dict[int, asyncio.Lock], key: int) -> asyncio.Lock:
        lock = locks.get(key)
        if lock is None:
            lock = locks[key] = asyncio.Lock()
        return lock

    async def _database_ready(self, interaction: discord.Interaction) -> bool:
        if self.bot.db.is_connected:
            return True
        log.warning("temp voice: refused a command — the database is not connected")
        await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
        return False

    @tempvoice.command(name="setup", description="Create the join-to-create voice channel")
    @app_commands.describe(name="What the join-to-create channel is called")
    async def setup_channel(
        self, interaction: discord.Interaction, name: str | None = None
    ) -> None:
        if not await require_staff(interaction):
            return
        if not await self._database_ready(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        _, said = await make_creator_channel(
            self.bot, interaction.guild, interaction.user, name
        )
        await interaction.followup.send(
            said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @tempvoice.command(name="forget", description="Stop treating a channel id as join-to-create")
    @app_commands.describe(channel_id="The id of the join-to-create channel to forget")
    async def forget(self, interaction: discord.Interaction, channel_id: str) -> None:
        if not await require_staff(interaction):
            return
        digits = channel_id.strip().lstrip("<#").rstrip(">")
        if not digits.isdigit():
            await interaction.response.send_message(
                NOT_AN_ID.format(given=channel_id), ephemeral=True
            )
            return
        removed = await self._forget(interaction.guild, int(digits), actor=interaction.user)
        if not removed:
            await interaction.response.send_message(
                NOT_A_LOBBY.format(channel_id=digits), ephemeral=True
            )
            return
        await interaction.response.send_message(
            FORGOTTEN.format(channel_id=digits), ephemeral=True
        )

    async def _forget(self, guild: Any, channel_id: int, actor: Any = None) -> bool:
        ids = list(self.bot.store.get(guild.id, "tempvoice_creator_ids") or [])
        if channel_id not in ids:
            return False
        ids.remove(channel_id)
        await self.bot.store.set(
            guild.id, "tempvoice_creator_ids", ids, by=getattr(actor, "id", None)
        )
        await log_action(
            self.bot,
            guild,
            "tempvoice.creator_removed",
            actor=actor,
            details={"channel_id": channel_id},
        )
        return True

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        if not self.bot.db.is_connected:
            return
        await self._forget(channel.guild, channel.id)
        await delete_row(self.bot.db, channel.id)

    @tempvoice.command(name="status", description="Show how temporary voice channels are set up")
    async def status(self, interaction: discord.Interaction) -> None:
        if not await require_staff(interaction):
            return
        if not await self._database_ready(interaction):
            return
        guild = interaction.guild
        store = self.bot.store
        creators = store.get(guild.id, "tempvoice_creator_ids") or []
        role_id = store.get(guild.id, "tempvoice_allowed_role_id")
        rows = await rows_for_guild(self.bot.db, guild.id)
        lines = [
            f"**mode** — {store.get(guild.id, 'tempvoice_mode')}",
            "**join-to-create** — "
            + (", ".join(f"<#{c}>" for c in creators) if creators else "not set up yet"),
            f"**name template** — `{store.get(guild.id, 'tempvoice_name_template')}`",
            f"**allowed role** — {f'<@&{role_id}>' if role_id else 'anyone'}",
            f"**channels open now** — {len(rows)}",
        ]
        await interaction.response.send_message(
            "\n".join(lines), ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @tempvoice.command(name="mode", description="Turn join-to-create off or on")
    @app_commands.describe(mode="off, or on (join-to-create makes channels)")
    @app_commands.choices(
        mode=[app_commands.Choice(name=name, value=name) for name in TEMPVOICE_MODES]
    )
    async def mode(
        self, interaction: discord.Interaction, mode: app_commands.Choice[str]
    ) -> None:
        if not await require_staff(interaction):
            return
        await self.bot.store.set(
            interaction.guild.id, "tempvoice_mode", mode.value, by=interaction.user.id
        )
        await interaction.response.send_message(
            f"Join-to-create is now **{mode.value}**.", ephemeral=True
        )
        await log_action(
            self.bot,
            interaction.guild,
            "tempvoice.mode",
            actor=interaction.user,
            details={"mode": mode.value},
        )

    @staticmethod
    def _where_sentence(where: str) -> str:
        return where_sentence(where)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TempVoice(bot))
