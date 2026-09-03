from __future__ import annotations

import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from ... import pings
from ...actionlog import (
    LOGS_DEFAULT,
    LOGS_MAX,
    LOGS_MIN,
    log_action,
    send_logs,
)
from ...command_visibility import STAFF_ONLY
from ...modcases import pages_under_limit
from ...settings_store import DB_UNAVAILABLE, GUILD_ONLY, require_staff
from .golive import get_link, latest_session

log = logging.getLogger(__name__)

CHOICE_LIMIT = 25
NAME_LIMIT = 100

NO_STREAMERS = (
    "Nobody has a ping role yet, so there is nothing to follow. A streamer starts one with "
    "`/pings fans on`, and staff can start one for anybody with `/pingroles streamer add`."
)
NO_SUCH_STREAMER = (
    "**{given}** is not somebody with a ping role here, so nothing was changed. Run `/pings "
    "follow` again and pick a name from the list rather than typing one."
)
ALREADY_FOLLOWING = (
    "You already follow **{name}**, so nothing was changed. `/pings unfollow` stops it."
)
NOT_FOLLOWING = (
    "You do not follow **{name}**, so there was nothing to stop. `/pings list` shows who you do "
    "follow."
)
FOLLOWING = (
    "Done — you now wear **{role}**, so Black Bloc mentions you when **{name}** goes live. "
    "`/pings unfollow` stops it."
)
UNFOLLOWED = "Done — you no longer get **{name}**'s go-live pings."
EVENTS_ON = (
    "Done — you now wear **{role}**, so you get pinged when somebody goes live and when an event "
    "starts. `/pings events off` stops it."
)
EVENTS_OFF = (
    "Done — you no longer get go-live and event pings. `/pings events on` brings them back."
)
EVENTS_ALREADY_ON = (
    "You already wear **{role}**, so nothing was changed. `/pings events off` takes it back off."
)
EVENTS_ALREADY_OFF = (
    "You do not wear **{role}**, so there was nothing to take off. `/pings events on` puts it on."
)
LIST_HEAD = "**Your pings**"
LIST_EVENTS_ON = "• Go-live and event pings — **on** (<@&{role_id}>)"
LIST_EVENTS_OFF = "• Go-live and event pings — **off**; `/pings events on` turns them on"
LIST_EVENTS_UNSET = "• Go-live and event pings — staff have not set up the Events role yet"
LIST_NONE = "• You follow no streamers. `/pings follow` picks one."
LIST_ONE = "• **{name}** — <@&{role_id}>"
FANS_OFF_NONE = (
    "You have no ping role, so there was nothing to take away. `/pings fans on` starts one."
)
STREAMER_LIST_EMPTY = (
    "Nobody has a ping role on this server yet. Start one for somebody with `/pingroles streamer "
    "add <member>`, or let a streamer start their own with `/pings fans on`."
)
STREAMER_LINE = "• **{name}** — <@&{role_id}> · {count}"
FOLLOWERS_KNOWN = "{count} follower(s)"
FOLLOWERS_UNKNOWN = "the role is gone from the server"


def role_of(guild: Any, role_id: Any) -> Any:
    return guild.get_role(int(role_id)) if role_id else None


def wears(member: Any, role_id: Any) -> bool:
    return any(role.id == int(role_id) for role in getattr(member, "roles", ()))


def followers_word(guild: Any, role_id: Any) -> str:
    role = role_of(guild, role_id)
    if role is None:
        return FOLLOWERS_UNKNOWN
    return FOLLOWERS_KNOWN.format(count=len(getattr(role, "members", ()) or ()))


class Pings(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    pingroles = app_commands.Group(
        name="pingroles",
        description="Set up the opt-in ping roles",
        default_permissions=STAFF_ONLY,
    )
    streamer = app_commands.Group(
        name="streamer", description="A streamer's own ping role", parent=pingroles
    )
    ping = app_commands.Group(name="pings", description="Choose which pings you get")
    events = app_commands.Group(
        name="events", description="Go-live and event pings", parent=ping
    )
    fans = app_commands.Group(
        name="fans", description="Your own ping role, if you stream", parent=ping
    )

    async def _ready(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await self._say(interaction, GUILD_ONLY)
            return False
        if not self.bot.db.is_connected:
            log.warning("pings: refused a command — the database is not connected")
            await self._say(interaction, DB_UNAVAILABLE)
            return False
        return True

    async def _on(self, interaction: discord.Interaction) -> bool:
        if pings.is_on(self.bot, interaction.guild.id):
            return True
        await self._say(interaction, pings.OFF)
        return False

    @staticmethod
    async def _say(interaction: discord.Interaction, text: str) -> None:
        await interaction.response.send_message(
            text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    async def _pages(self, interaction: discord.Interaction, lines: list[str]) -> None:
        for index, page in enumerate(pages_under_limit(lines)):
            answer = interaction.followup.send if index else interaction.response.send_message
            await answer(
                page, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
            )

    async def _streamer_choices(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        if interaction.guild is None or not self.bot.db.is_connected:
            return []
        needle = str(current or "").casefold()
        found: list[app_commands.Choice[str]] = []
        for row in await pings.all_fan_roles(self.bot.db, interaction.guild.id):
            label = pings.option_label(interaction.guild, row)
            if needle and needle not in label.casefold():
                continue
            found.append(app_commands.Choice(name=label[:NAME_LIMIT], value=str(row["user_id"])))
            if len(found) == CHOICE_LIMIT:
                break
        return found

    async def _wanted_streamer(self, interaction: discord.Interaction, given: str) -> Any:
        """The fan-role row a `/pings follow` argument names, or None once they are answered."""
        rows = await pings.all_fan_roles(self.bot.db, interaction.guild.id)
        if not rows:
            await self._say(interaction, NO_STREAMERS)
            return None
        wanted = str(given or "").strip()
        row = next((one for one in rows if str(one["user_id"]) == wanted), None)
        if row is None:
            folded = wanted.casefold()
            row = next(
                (
                    one
                    for one in rows
                    if pings.option_label(interaction.guild, one).casefold() == folded
                ),
                None,
            )
        if row is None:
            await self._say(interaction, NO_SUCH_STREAMER.format(given=wanted[:60] or "nothing"))
        return row

    @ping.command(name="follow", description="Get one streamer's go-live pings")
    @app_commands.describe(streamer="Whose pings you want")
    async def follow(self, interaction: discord.Interaction, streamer: str) -> None:
        await self._follow(interaction, streamer, adding=True)

    @follow.autocomplete("streamer")
    async def follow_names(self, interaction: discord.Interaction, current: str):
        return await self._streamer_choices(interaction, current)

    @ping.command(name="unfollow", description="Stop one streamer's go-live pings")
    @app_commands.describe(streamer="Whose pings you want to stop")
    async def unfollow(self, interaction: discord.Interaction, streamer: str) -> None:
        await self._follow(interaction, streamer, adding=False)

    @unfollow.autocomplete("streamer")
    async def unfollow_names(self, interaction: discord.Interaction, current: str):
        return await self._streamer_choices(interaction, current)

    async def _follow(
        self, interaction: discord.Interaction, given: str, *, adding: bool
    ) -> None:
        if not await self._ready(interaction) or not await self._on(interaction):
            return
        guild = interaction.guild
        row = await self._wanted_streamer(interaction, given)
        if row is None:
            return
        name = pings.option_label(guild, row)
        role = role_of(guild, row["role_id"])
        if role is None:
            await self._say(interaction, NO_SUCH_STREAMER.format(given=name[:60]))
            return
        held = wears(interaction.user, role.id)
        if held == adding:
            said = ALREADY_FOLLOWING if adding else NOT_FOLLOWING
            await self._say(interaction, said.format(name=name))
            return
        refusal = await pings.wear(self.bot, guild, interaction.user, role, add=adding)
        if refusal is not None:
            await self._say(interaction, refusal)
            return
        await self._say(
            interaction,
            FOLLOWING.format(role=role.name, name=name) if adding
            else UNFOLLOWED.format(name=name),
        )
        await log_action(
            self.bot,
            guild,
            "pings.follow" if adding else "pings.unfollow",
            actor=interaction.user,
            target=interaction.user,
            details={"role_id": role.id, "streamer_id": int(row["user_id"])},
        )

    @ping.command(name="list", description="What Black Bloc pings you about")
    async def pings_list(self, interaction: discord.Interaction) -> None:
        if not await self._ready(interaction):
            return
        guild = interaction.guild
        events_role_id = pings.events_role_id(self.bot, guild.id)
        lines = [LIST_HEAD]
        if not events_role_id:
            lines.append(LIST_EVENTS_UNSET)
        elif wears(interaction.user, events_role_id):
            lines.append(LIST_EVENTS_ON.format(role_id=events_role_id))
        else:
            lines.append(LIST_EVENTS_OFF)
        mine = [
            row
            for row in await pings.all_fan_roles(self.bot.db, guild.id)
            if wears(interaction.user, row["role_id"])
        ]
        if not mine:
            lines.append(LIST_NONE)
        lines += [
            LIST_ONE.format(name=pings.option_label(guild, row), role_id=row["role_id"])
            for row in mine
        ]
        await self._pages(interaction, lines)

    @events.command(name="on", description="Get go-live and event pings")
    async def events_on(self, interaction: discord.Interaction) -> None:
        await self._events(interaction, adding=True)

    @events.command(name="off", description="Stop go-live and event pings")
    async def events_off(self, interaction: discord.Interaction) -> None:
        await self._events(interaction, adding=False)

    async def _events(self, interaction: discord.Interaction, *, adding: bool) -> None:
        if not await self._ready(interaction) or not await self._on(interaction):
            return
        guild = interaction.guild
        role_id = pings.events_role_id(self.bot, guild.id)
        if not role_id:
            await self._say(interaction, pings.NO_EVENTS_ROLE)
            return
        role = role_of(guild, role_id)
        if role is None:
            await self._say(interaction, pings.EVENTS_ROLE_GONE.format(role_id=role_id))
            return
        if wears(interaction.user, role.id) == adding:
            said = EVENTS_ALREADY_ON if adding else EVENTS_ALREADY_OFF
            await self._say(interaction, said.format(role=role.name))
            return
        refusal = await pings.wear(self.bot, guild, interaction.user, role, add=adding)
        if refusal is not None:
            await self._say(interaction, refusal)
            return
        await self._say(
            interaction, EVENTS_ON.format(role=role.name) if adding else EVENTS_OFF
        )
        await log_action(
            self.bot,
            guild,
            "pings.events_on" if adding else "pings.events_off",
            actor=interaction.user,
            target=interaction.user,
            details={"role_id": role.id},
        )

    @fans.command(name="on", description="Give your followers a role that pings them")
    async def fans_on(self, interaction: discord.Interaction) -> None:
        if not await self._ready(interaction) or not await self._on(interaction):
            return
        guild = interaction.guild
        if self.bot.store.get(guild.id, pings.CREATION_KEY) == pings.STAFF:
            await self._say(interaction, pings.STAFF_ONLY_CREATION)
            return
        if not await self._streams(guild, interaction.user.id):
            await self._say(interaction, pings.NOT_A_STREAMER)
            return
        outcome = await pings.ensure_fan_role(
            self.bot, guild, interaction.user, by=interaction.user.id
        )
        await self._say(interaction, outcome.message)

    @fans.command(name="off", description="Take your own ping role away")
    async def fans_off(self, interaction: discord.Interaction) -> None:
        if not await self._ready(interaction) or not await self._on(interaction):
            return
        guild = interaction.guild
        if await pings.get_fan_role(self.bot.db, guild.id, interaction.user.id) is None:
            await self._say(interaction, FANS_OFF_NONE)
            return
        outcome = await pings.remove_fan_role(
            self.bot, guild, interaction.user.id, by=interaction.user.id
        )
        await self._say(interaction, outcome.message)

    async def _streams(self, guild: Any, user_id: int) -> bool:
        """A linked channel, or a stream Black Bloc has already seen, counts as streaming here."""
        if await get_link(self.bot.db, user_id) is not None:
            return True
        return await latest_session(self.bot.db, guild.id, user_id) is not None

    @pingroles.command(
        name="setup", description="Make or reuse the Events role and point pings at it"
    )
    @app_commands.describe(role="Use this role instead of making one")
    async def setup_command(
        self, interaction: discord.Interaction, role: discord.Role | None = None
    ) -> None:
        if not await require_staff(interaction):
            return
        if not await self._ready(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        outcome = await pings.setup_events_role(
            self.bot, interaction.guild, by=interaction.user.id, role=role
        )
        await interaction.followup.send(
            outcome.message, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @streamer.command(name="add", description="Start a streamer's own ping role")
    @app_commands.describe(member="The streamer", role="Use this role instead of making one")
    async def streamer_add(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role | None = None,
    ) -> None:
        if not await require_staff(interaction):
            return
        if not await self._ready(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        outcome = await pings.ensure_fan_role(
            self.bot,
            interaction.guild,
            member,
            by=interaction.user.id,
            existing_role=role,
            staff=True,
        )
        await interaction.followup.send(
            outcome.message, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @streamer.command(name="remove", description="Take a streamer's own ping role away")
    @app_commands.describe(member="The streamer")
    async def streamer_remove(
        self, interaction: discord.Interaction, member: discord.Member
    ) -> None:
        if not await require_staff(interaction):
            return
        if not await self._ready(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        outcome = await pings.remove_fan_role(
            self.bot, interaction.guild, member.id, by=interaction.user.id
        )
        await interaction.followup.send(
            outcome.message, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @streamer.command(name="list", description="Who has a ping role, and how many follow it")
    async def streamer_list(self, interaction: discord.Interaction) -> None:
        if not await require_staff(interaction):
            return
        if not await self._ready(interaction):
            return
        guild = interaction.guild
        rows = await pings.all_fan_roles(self.bot.db, guild.id)
        if not rows:
            await self._say(interaction, STREAMER_LIST_EMPTY)
            return
        await self._pages(
            interaction,
            [
                STREAMER_LINE.format(
                    name=pings.option_label(guild, row),
                    role_id=row["role_id"],
                    count=followers_word(guild, row["role_id"]),
                )
                for row in rows
            ],
        )

    @pingroles.command(name="logs", description="The last few ping-role log lines")
    @app_commands.describe(
        count="How many lines, 1 to 50 (10 by default)",
        important_only="True to leave out the dry runs and the housekeeping",
    )
    async def pingroles_logs(
        self,
        interaction: discord.Interaction,
        count: app_commands.Range[int, LOGS_MIN, LOGS_MAX] = LOGS_DEFAULT,
        important_only: bool = False,
    ) -> None:
        await send_logs(interaction, "pings", count=count, important_only=important_only)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Pings(bot))
