from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from ...settings_store import DB_UNAVAILABLE
from ...timezones import (
    CHOICE_LIMIT,
    DEFAULT_TZ,
    START_EXAMPLE,
    is_known,
    local_time,
    set_timezone,
    stored_timezone,
    suggest,
)

log = logging.getLogger(__name__)

UNKNOWN_TZ = (
    "**{given}** is not a time zone Black Bloc knows, so nothing was saved. Start typing a city "
    "— `Phoenix`, `London`, `Tokyo` — and pick one of the suggestions, which are the "
    "`Region/City` names Discord and your phone both use."
)
TZ_SET = (
    "Your time zone is **{tz}**, where it is now **{now}**. Times you type into `/event create` "
    f"are read in that zone, so `{START_EXAMPLE}` means half past seven in the evening for you."
)
TZ_SHOW = (
    "Your time zone is **{tz}**, where it is now **{now}**. `/timezone set` changes it."
)
TZ_SHOW_DEFAULT = (
    "You have not set a time zone, so Black Bloc reads the times you type as **{tz}**, where it "
    "is now **{now}**. `/timezone set` changes that."
)


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    timezone = app_commands.Group(
        name="timezone", description="The zone Black Bloc reads the times you type in"
    )

    async def _database_ready(self, interaction: discord.Interaction) -> bool:
        if self.bot.db.is_connected:
            return True
        log.warning("events: refused a command — the database is not connected")
        await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
        return False

    async def _suggest_timezones(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return [app_commands.Choice(name=name, value=name) for name in suggest(current)][
            :CHOICE_LIMIT
        ]

    @timezone.command(name="set", description="Tell Black Bloc which time zone you are in")
    @app_commands.describe(tz="Start typing a city — Phoenix, London, Tokyo")
    @app_commands.autocomplete(tz=_suggest_timezones)
    async def timezone_set(self, interaction: discord.Interaction, tz: str) -> None:
        if not await self._database_ready(interaction):
            return
        name = tz.strip()
        if not is_known(name):
            await interaction.response.send_message(
                UNKNOWN_TZ.format(given=name),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        await set_timezone(self.bot.db, interaction.user.id, name)
        await interaction.response.send_message(
            TZ_SET.format(tz=name, now=local_time(name)),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @timezone.command(name="show", description="Show which time zone Black Bloc has for you")
    async def timezone_show(self, interaction: discord.Interaction) -> None:
        if not await self._database_ready(interaction):
            return
        chosen = await stored_timezone(self.bot.db, interaction.user.id)
        name = chosen or DEFAULT_TZ
        await interaction.response.send_message(
            (TZ_SHOW if chosen else TZ_SHOW_DEFAULT).format(tz=name, now=local_time(name)),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Events(bot))
