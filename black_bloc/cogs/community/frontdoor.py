from __future__ import annotations

import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ...actionlog import log_action
from ...command_errors import SafeDynamicItem
from ...frontdoor import (
    CUSTOM_ID_TEMPLATE,
    DOOR_COLOUR,
    DOOR_DOWN_SAID,
    DOOR_GUARDED,
    DOOR_MOVED_SAID,
    DOOR_NO_CHANNEL,
    DOOR_NOT_UP,
    DOOR_OFF,
    DOOR_POSTED_SAID,
    DOOR_STUCK,
    EVENT,
    EVENT_HANDOFF_TEXT,
    EVENT_HANDOFF_TITLE,
    KINDS,
    LABEL_DEFAULTS,
    PANEL_TIMEOUT_FOOTER,
    REQUEST,
    TICKET,
    custom_id,
    door_embed,
    door_is_on,
    door_takes_over,
    followed_slug,
    label_for,
)
from ...golive import now_iso
from ...logkinds import VIA_DISCORD, kind_via
from ...loops import wait_ready
from ...panels import Outcome, Panel, answer, panel_minutes, refusal
from ...posted import drop_message, message_is_there, overtaken_by
from ...posts import row_value
from ...settings_store import (
    FRONTDOOR_CHANNEL,
    FRONTDOOR_MESSAGE,
    FRONTDOOR_PANEL_MINUTES,
    GUILD_ONLY,
    MODMAIL_PANEL_MESSAGE,
)
from ..community.events import ProposeButton
from ..community.requests import FileButton
from ..moderation.modmail import open_ticket_modal, panel_where

log = logging.getLogger(__name__)

COG_NAME = "FrontDoor"
RECONCILE_MINUTES = 5

POSTED = "frontdoor.posted"
MOVED = "frontdoor.moved"
TAKEN_DOWN = "frontdoor.taken_down"
GONE = "frontdoor.gone"
BELOW_POST = "frontdoor.below_post"
POST_FAILED = "frontdoor.post_failed"
WOULD_POST = "frontdoor.would_post"
WOULD_TAKE_DOWN = "frontdoor.would_take_down"
WOULD_HIDE_TICKET_BUTTON = "frontdoor.would_hide_ticket_button"
TICKET_BUTTON_HIDDEN = "frontdoor.ticket_button_hidden"


async def open_the_ticket(interaction: discord.Interaction) -> None:
    """Modmail's own opener; every gate and refusal is still modmail's own."""
    await open_ticket_modal(interaction)


async def open_the_request(interaction: discord.Interaction) -> None:
    """The `/request` panel's File a request press, unchanged — it never reads its own view."""
    await FileButton().callback(interaction)


async def open_the_event(interaction: discord.Interaction) -> None:
    """A draft is a card that replaces the message it was raised from, so on a posted door it
    is raised from a private one instead."""
    embed, view = event_handoff(interaction.client, interaction.guild)
    await interaction.response.send_message(
        embed=embed,
        view=view,
        ephemeral=True,
        allowed_mentions=discord.AllowedMentions.none(),
    )
    view.message = await interaction.original_response()


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
OPENERS: dict[str, Any] = {
    TICKET: open_the_ticket,
    REQUEST: open_the_request,
    EVENT: open_the_event,
}


class DoorPanel(Panel):
    def __init__(self, minutes: int) -> None:
        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER)


class EventHandoff(Panel):
    """The posted door cannot draw the draft over itself, so the draft opens in here."""

    def __init__(self, minutes: int, label: str) -> None:
        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER)
        self.add_item(EventDoor(label))


class DoorButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=CUSTOM_ID_TEMPLATE
):
    """One of the three posted buttons: persistent, and its whole answer is ephemeral."""

    def __init__(self, kind: str, guild_id: Any, label: str | None = None) -> None:
        self.kind = kind
        self.guild_id = int(guild_id)
        super().__init__(
            discord.ui.Button(
                label=label or LABEL_DEFAULTS[kind],
                style=discord.ButtonStyle.primary,
                custom_id=custom_id(kind, guild_id),
                row=0,
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: Any):
        return cls(str(match["kind"]), int(match["guild_id"]))

    async def on_click(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return
        if not door_is_on(interaction.client.store, interaction.guild.id):
            await answer(interaction, DOOR_OFF)
            return
        await OPENERS[self.kind](interaction)


def door_view(bot: Any, guild: Any) -> discord.ui.View:
    """The posted door belongs to the room, so it outlives the process that posted it."""
    view = discord.ui.View(timeout=None)
    for kind in KINDS:
        view.add_item(DoorButton(kind, guild.id, label_for(bot.store, guild.id, kind)))
    return view


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


def where_the_door_is(bot: Any, guild: Any) -> tuple[Any, int | None]:
    channel_id = bot.store.get(guild.id, FRONTDOOR_CHANNEL)
    message_id = bot.store.get(guild.id, FRONTDOOR_MESSAGE)
    channel = (
        (guild.get_channel(channel_id) or bot.get_channel(channel_id)) if channel_id else None
    )
    return channel, (int(message_id) if message_id else None)


async def hide_ticket_button(bot: Any, guild: Any) -> int | None:
    """One door per channel: modmail's own button comes down while the front door is up in it.

    `modmail_panel_channel_id` keeps its value, so moving the door away puts the button back."""
    channel, message_id = panel_where(bot, guild)
    if channel is None or not message_id:
        return None
    if door_takes_over(bot.store, guild.id) != int(channel.id):
        return None
    gone = await drop_message(
        bot, guild, channel, message_id, would_kind=WOULD_HIDE_TICKET_BUTTON
    )
    if not gone:
        return None
    await bot.store.clear(guild.id, MODMAIL_PANEL_MESSAGE)
    await log_action(
        bot,
        guild,
        TICKET_BUTTON_HIDDEN,
        details={"channel_id": channel.id, "message_id": message_id},
    )
    return message_id


async def post_door(
    bot: Any,
    guild: Any,
    actor: Any,
    channel: Any,
    *,
    moving: bool | None = None,
    via: str = VIA_DISCORD,
) -> Outcome:
    """One front door per guild, posted from Discord or from the website."""
    if channel is None:
        return refusal(DOOR_NO_CHANNEL, "no_such_channel", 400)
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel.id):
        await log_action(
            bot,
            guild,
            kind_via(WOULD_POST, via),
            actor=actor,
            details={"channel_id": channel.id, "via": via},
        )
        return refusal(DOOR_GUARDED, "test_mode", 409)
    old_channel, old_id = where_the_door_is(bot, guild)
    store = bot.store
    try:
        message = await channel.send(
            embed=door_embed(store, guild.id),
            view=door_view(bot, guild),
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except Exception as exc:
        log.warning("frontdoor: could not post the front door: %s", exc)
        await log_action(
            bot,
            guild,
            POST_FAILED,
            actor=actor,
            details={"channel_id": channel.id, "reason": f"{type(exc).__name__}: {exc}"},
        )
        return refusal(DOOR_STUCK, "door_stuck", 500)
    by = getattr(actor, "id", actor)
    await store.set(guild.id, FRONTDOOR_CHANNEL, channel.id, by=by)
    await store.set(guild.id, FRONTDOOR_MESSAGE, str(message.id), by=by)
    moved = (old_id is not None) if moving is None else moving
    if moved and old_channel is not None and old_id:
        await drop_message(bot, guild, old_channel, old_id, would_kind=WOULD_TAKE_DOWN)
    await log_action(
        bot,
        guild,
        kind_via(MOVED if moved else POSTED, via),
        actor=actor,
        details={"channel_id": channel.id, "message_id": message.id, "via": via},
    )
    await hide_ticket_button(bot, guild)
    said = (DOOR_MOVED_SAID if moved else DOOR_POSTED_SAID).format(where=channel.id)
    return Outcome(True, said, value=message.id)


async def take_door_down(
    bot: Any, guild: Any, actor: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Down means down: the message goes and both keys are cleared, so nothing puts it back."""
    channel, message_id = where_the_door_is(bot, guild)
    if not bot.store.get(guild.id, FRONTDOOR_CHANNEL):
        return refusal(DOOR_NOT_UP, "no_door", 404)
    if channel is not None and message_id:
        await drop_message(bot, guild, channel, message_id, would_kind=WOULD_TAKE_DOWN)
    await bot.store.clear(guild.id, FRONTDOOR_MESSAGE)
    await bot.store.clear(guild.id, FRONTDOOR_CHANNEL)
    await log_action(
        bot,
        guild,
        kind_via(TAKEN_DOWN, via),
        actor=actor,
        details={
            "channel_id": getattr(channel, "id", None),
            "message_id": message_id,
            "via": via,
        },
    )
    return Outcome(True, DOOR_DOWN_SAID, value=message_id)


class FrontDoor(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._shadowed: set[int] = set()
        self.last_ok_at: str | None = None
        self.last_error: str | None = None

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name != "_reconcile_loop":
            return (None, None)
        return (self.last_ok_at, self.last_error)

    async def cog_load(self) -> None:
        self.bot.add_dynamic_items(DoorButton)
        if not self.bot.db.is_connected:
            return
        await self.reconcile()
        self._reconcile_loop.start()

    async def cog_unload(self) -> None:
        self._reconcile_loop.cancel()

    @tasks.loop(minutes=RECONCILE_MINUTES)
    async def _reconcile_loop(self) -> None:
        if self.bot.db.is_connected:
            await self.reconcile()

    @_reconcile_loop.before_loop
    async def _before_reconcile(self) -> None:
        await wait_ready(self.bot, self._reconcile_error)

    @_reconcile_loop.error
    async def _reconcile_error(self, error: BaseException) -> None:
        self.last_error = f"{type(error).__name__}: {error}"
        log.exception("frontdoor: the reconcile loop stopped", exc_info=error)
        self._reconcile_loop.restart()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self.bot.db.is_connected:
            return
        await self.reconcile()
        if not self._reconcile_loop.is_running():
            self._reconcile_loop.start()

    @commands.Cog.listener()
    async def on_post_published(self, guild: Any, row: Any) -> None:
        """A re-posted rules message moves what follows it, at once and on the next sweep."""
        if not self.bot.db.is_connected:
            return
        if str(row_value(row, "slug", "")) != followed_slug(self.bot.store, guild.id):
            return
        await self._redoor(guild)

    async def reconcile(self) -> None:
        for guild in list(getattr(self.bot, "guilds", ())):
            if getattr(guild, "unavailable", False):
                continue
            await self._redoor(guild)
        self.last_ok_at = now_iso()

    async def _redoor(self, guild: Any) -> None:
        """A door deleted by hand is put back, and one the rules message has overtaken is
        posted again so it stays directly under the rules."""
        bot = self.bot
        channel, message_id = where_the_door_is(bot, guild)
        if not door_is_on(bot.store, guild.id):
            if bot.store.get(guild.id, FRONTDOOR_CHANNEL):
                await take_door_down(bot, guild, None)
            return
        if not bot.store.get(guild.id, FRONTDOOR_CHANNEL) or channel is None:
            return
        overtaken = await overtaken_by(
            bot, guild, channel, message_id, followed_slug(bot.store, guild.id)
        )
        if overtaken is None and message_id and await message_is_there(channel, message_id):
            self._shadowed.discard(guild.id)
            await hide_ticket_button(bot, guild)
            return
        guard = getattr(bot, "guard", None)
        if guard is not None and not guard.allows_channel(channel.id):
            if guild.id not in self._shadowed:
                self._shadowed.add(guild.id)
                await log_action(
                    bot,
                    guild,
                    WOULD_POST,
                    details={"channel_id": channel.id, "reason": "reconcile"},
                )
            return
        if overtaken is not None:
            await log_action(
                bot,
                guild,
                BELOW_POST,
                details={
                    "channel_id": channel.id,
                    "message_id": message_id,
                    "post_message_id": overtaken,
                    "slug": followed_slug(bot.store, guild.id),
                },
            )
        elif message_id:
            await log_action(
                bot,
                guild,
                GONE,
                details={"channel_id": channel.id, "message_id": message_id},
            )
        outcome = await post_door(bot, guild, None, channel, moving=overtaken is not None)
        if outcome.ok:
            self._shadowed.discard(guild.id)

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
    "BELOW_POST",
    "COG_NAME",
    "DOORS",
    "GONE",
    "MOVED",
    "OPENERS",
    "POSTED",
    "POST_FAILED",
    "TAKEN_DOWN",
    "TICKET_BUTTON_HIDDEN",
    "WOULD_HIDE_TICKET_BUTTON",
    "WOULD_POST",
    "WOULD_TAKE_DOWN",
    "DoorButton",
    "DoorPanel",
    "EventDoor",
    "EventHandoff",
    "FrontDoor",
    "RequestDoor",
    "TicketDoor",
    "build_panel",
    "door_view",
    "event_handoff",
    "hide_ticket_button",
    "open_the_event",
    "open_the_request",
    "open_the_ticket",
    "post_door",
    "take_door_down",
    "where_the_door_is",
]
