from __future__ import annotations

import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from ...frontdoor import (
    DOOR_COLOUR,
    DOOR_OFF,
    EVENT,
    EVENT_HANDOFF_TEXT,
    EVENT_HANDOFF_TITLE,
    KINDS,
    PANEL_TIMEOUT_FOOTER,
    REQUEST,
    TICKET,
    door_embed,
    door_is_on,
    label_for,
)
from ...panels import Panel, answer, panel_minutes
from ...settings_store import FRONTDOOR_PANEL_MINUTES, GUILD_ONLY
from ..community.events import ProposeButton
from ..community.requests import FileButton
from ..moderation.modmail import open_ticket_modal

log = logging.getLogger(__name__)

COG_NAME = "FrontDoor"


async def open_the_ticket(interaction: discord.Interaction) -> None:
    """Modmail's own opener; every gate and refusal is still modmail's own."""
    await open_ticket_modal(interaction)


async def open_the_request(interaction: discord.Interaction) -> None:
    """The `/request` panel's File a request press, unchanged — it never reads its own view."""
    await FileButton().callback(interaction)


class TicketDoor(discord.ui.Button):
    def __init__(self, label: str) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.primary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_the_ticket(interaction)


class RequestDoor(FileButton):
    """`FileButton` with the door's wording; the press itself is inherited, never copied."""

    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label
        self.row = 0


class EventDoor(ProposeButton):
    """`ProposeButton` with the door's wording; the draft it opens is the `/event` one."""

    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label
        self.row = 0


DOORS: dict[str, Any] = {TICKET: TicketDoor, REQUEST: RequestDoor, EVENT: EventDoor}


class DoorPanel(Panel):
    def __init__(self, minutes: int) -> None:
        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER)


class EventHandoff(Panel):
    """The posted door cannot draw the draft over itself, so the draft opens in here."""

    def __init__(self, minutes: int, label: str) -> None:
        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER)
        self.add_item(EventDoor(label))


def build_panel(bot: Any, guild: Any, actor: Any = None) -> tuple[discord.Embed, DoorPanel]:
    """The one card: the posted message wears it, and so does `/ask`."""
    store = bot.store
    view = DoorPanel(panel_minutes(store, guild.id, FRONTDOOR_PANEL_MINUTES))
    for kind in KINDS:
        view.add_item(DOORS[kind](label_for(store, guild.id, kind)))
    return door_embed(store, guild.id), view


def event_handoff(bot: Any, guild: Any) -> tuple[discord.Embed, EventHandoff]:
    label = label_for(bot.store, guild.id, EVENT)
    embed = discord.Embed(
        title=EVENT_HANDOFF_TITLE,
        description=EVENT_HANDOFF_TEXT,
        colour=discord.Colour(DOOR_COLOUR),
    )
    return embed, EventHandoff(
        panel_minutes(bot.store, guild.id, FRONTDOOR_PANEL_MINUTES), label
    )


class FrontDoor(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="ask", description="Ask staff, ask for something, or propose an event"
    )
    async def ask(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return
        if not door_is_on(self.bot.store, interaction.guild.id):
            await answer(interaction, DOOR_OFF)
            return
        embed, view = build_panel(self.bot, interaction.guild, interaction.user)
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FrontDoor(bot))


__all__ = [
    "COG_NAME",
    "DOORS",
    "DoorPanel",
    "EventDoor",
    "EventHandoff",
    "FrontDoor",
    "RequestDoor",
    "TicketDoor",
    "build_panel",
    "event_handoff",
    "open_the_request",
    "open_the_ticket",
]
