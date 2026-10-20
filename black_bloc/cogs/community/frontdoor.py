from __future__ import annotations

import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ...actionlog import log_action
from ...command_errors import SafeDynamicItem
from ...frontdoor import (
    CUSTOM_ID_HEAD,
    CUSTOM_ID_TEMPLATE,
    DOOR_COLOUR,
    DOOR_DOWN_SAID,
    DOOR_GUARDED,
    DOOR_MOVED_SAID,
    DOOR_NO_CHANNEL,
    DOOR_NOT_UP,
    DOOR_OFF,
    DOOR_OFF_THE_POST_SAID,
    DOOR_POSTED_SAID,
    DOOR_RIDES_ELSEWHERE,
    DOOR_RIDES_POST_SAID,
    DOOR_STUCK,
    EVENT,
    EVENT_HANDOFF_TEXT,
    EVENT_HANDOFF_TITLE,
    LABEL_DEFAULTS,
    PANEL_TIMEOUT_FOOTER,
    REQUEST,
    TICKET,
    custom_id,
    door_embed,
    door_hash,
    door_is_on,
    door_takes_over,
    followed_slug,
    label_for,
    shown_kinds,
)
from ...golive import now_iso
from ...logkinds import VIA_DISCORD, kind_via
from ...loops import Reconciler, wait_ready
from ...panels import Outcome, Panel, answer, panel_minutes, refusal
from ...post_blocks import LIVE_KINDS, carries_live, keep_drawn, redraw_post
from ...posted import drop_message, duplicates_near, message_is_there, overtaken_by
from ...posts import (
    carries_door,
    door_carrier,
    door_drawn,
    get_post_by_id,
    is_posted,
    row_value,
    set_carries_door,
    shadow_channel_id,
    shadow_id,
    where_words,
)
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
DUPLICATE_SEEN = "frontdoor.duplicate_seen"
RIDES_POST = "frontdoor.rides_post"
REDRAWN_ON_POST = "frontdoor.redrawn_on_post"


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
    for kind in shown_kinds(bot.store, guild.id):
        view.add_item(DoorButton(kind, guild.id, label_for(bot.store, guild.id, kind)))
    return view


def build_panel(bot: Any, guild: Any, actor: Any = None) -> tuple[discord.Embed, DoorPanel]:
    """The one card: the posted message wears it, and so does `/ask`."""
    store = bot.store
    view = DoorPanel(panel_minutes(store, guild.id, FRONTDOOR_PANEL_MINUTES))
    for kind in shown_kinds(store, guild.id):
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


def carried_parts(bot: Any, guild: Any, row: Any) -> tuple[discord.Embed, Any, str] | None:
    """The door's card, its buttons and the stamp of both, for a post that carries it."""
    store = bot.store
    if not door_is_on(store, guild.id):
        return None
    return door_embed(store, guild.id), door_view(bot, guild), door_hash(store, guild.id)


def ours(row: Any) -> set[int]:
    return {int(found) for found in (row_value(row, "message_id"), shadow_id(row)) if found}


async def carrier_up(bot: Any, guild: Any) -> Any:
    """The post carrying the door, while it has a message for the door to ride."""
    row = await door_carrier(bot.db, guild.id)
    return row if row is not None and is_posted(row) else None


async def redraw_carrier(
    bot: Any, guild: Any, row: Any, actor: Any = None, *, via: str = VIA_DISCORD
) -> bool:
    """Rebuilt whole when any block's stamp moved; the post's own words stay as posted."""
    return await redraw_post(
        bot, guild, row, actor, via=via, done_kind=REDRAWN_ON_POST, failed_kind=POST_FAILED
    )


async def drop_the_doors_own(bot: Any, guild: Any, row: Any) -> None:
    """The door's own message, wherever it is, goes — the post's message is never one of them."""
    kept = ours(row)
    channel, message_id = where_the_door_is(bot, guild)
    if message_id and message_id not in kept and channel is not None:
        await drop_message(bot, guild, channel, message_id, would_kind=WOULD_TAKE_DOWN)


async def mirror_the_ride(bot: Any, guild: Any, row: Any, actor: Any = None) -> bool:
    """The door's own keys point at the post's message, so every door path finds it there."""
    store = bot.store
    real = row_value(row, "message_id")
    wanted = {
        FRONTDOOR_CHANNEL: row_value(row, "channel_id"),
        FRONTDOOR_MESSAGE: str(real) if real else None,
    }
    changed = False
    for key, value in wanted.items():
        have = store.get(guild.id, key)
        if (str(have) if have else None) == (str(value) if value else None):
            continue
        if value:
            await store.set(guild.id, key, value, by=getattr(actor, "id", actor))
        else:
            await store.clear(guild.id, key)
        changed = True
    return changed


async def release_the_ride(bot: Any, guild: Any, row: Any, *, keep_channel: bool) -> bool:
    """The keys that point at the post's message are let go; nothing is deleted."""
    store = bot.store
    kept = ours(row)
    cleared = False
    found = store.get(guild.id, FRONTDOOR_MESSAGE)
    if found and int(found) in kept:
        await store.clear(guild.id, FRONTDOOR_MESSAGE)
        cleared = True
    if cleared and not keep_channel:
        await store.clear(guild.id, FRONTDOOR_CHANNEL)
    return cleared


async def door_rides_post(
    bot: Any, guild: Any, row: Any, actor: Any = None, *, via: str = VIA_DISCORD
) -> None:
    """The door is on the post's message: its own copies go and its keys follow the post."""
    await drop_the_doors_own(bot, guild, row)
    if await mirror_the_ride(bot, guild, row, actor):
        await log_action(
            bot,
            guild,
            kind_via(RIDES_POST, via),
            actor=actor,
            details={
                "slug": row_value(row, "slug"),
                "post_id": int(row["id"]),
                "channel_id": row_value(row, "channel_id"),
                "message_id": row_value(row, "message_id"),
                "shadow_message_id": shadow_id(row),
                "via": via,
            },
        )
    await hide_ticket_button(bot, guild)


async def door_leaves_post(
    bot: Any, guild: Any, row: Any, actor: Any = None, *, via: str = VIA_DISCORD
) -> None:
    """The post's message went, and the door was part of it."""
    if not await release_the_ride(bot, guild, row, keep_channel=False):
        return
    await log_action(
        bot,
        guild,
        kind_via(TAKEN_DOWN, via),
        actor=actor,
        details={
            "slug": row_value(row, "slug"),
            "channel_id": row_value(row, "channel_id"),
            "message_id": row_value(row, "message_id") or shadow_id(row),
            "with_post": True,
            "via": via,
        },
    )


async def door_follows_post(
    bot: Any, guild: Any, row: Any, actor: Any = None, *, via: str = VIA_DISCORD
) -> None:
    """Carry the front door was switched on this post: a message already up changes at once."""
    if not is_posted(row):
        return
    await redraw_carrier(bot, guild, row, actor, via=via)
    fresh = await get_post_by_id(bot.db, int(row["id"]))
    if door_drawn(fresh):
        await door_rides_post(bot, guild, fresh, actor, via=via)
    elif not carries_door(fresh):
        await release_the_ride(bot, guild, row, keep_channel=True)


async def keep_the_ride(
    bot: Any, guild: Any, row: Any, actor: Any = None, *, via: str = VIA_DISCORD
) -> None:
    """The sweep's half: the door's words re-drawn in place, its keys kept on the post."""
    await redraw_carrier(bot, guild, row, actor, via=via)
    fresh = await get_post_by_id(bot.db, int(row["id"]))
    if not door_is_on(bot.store, guild.id):
        await release_the_ride(bot, guild, row, keep_channel=False)
        return
    if door_drawn(fresh):
        await door_rides_post(bot, guild, fresh, actor, via=via)


async def door_on_the_post(
    bot: Any, guild: Any, actor: Any, channel: Any, row: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Posting the door where a post already carries it posts nothing and deletes nothing."""
    title = str(row_value(row, "title", ""))
    aimed = row_value(row, "channel_id")
    homes = {int(found) for found in (aimed,) if found}
    if shadow_id(row):
        home = shadow_channel_id(bot, guild)
        if home:
            homes.add(int(home))
    where = where_words(guild, aimed or next(iter(homes), None))
    if int(channel.id) not in homes:
        return refusal(
            DOOR_RIDES_ELSEWHERE.format(title=title, where=where), "door_rides_post", 409
        )
    if not door_is_on(bot.store, guild.id):
        return refusal(DOOR_OFF, "door_off", 409)
    await keep_the_ride(bot, guild, row, actor, via=via)
    return Outcome(
        True,
        DOOR_RIDES_POST_SAID.format(title=title, where=where),
        value=row_value(row, "message_id") or shadow_id(row),
    )


async def take_the_door_off_its_post(
    bot: Any, guild: Any, actor: Any, row: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Down means down here too: the post stays up without the door, and stops carrying it."""
    await set_carries_door(bot.db, int(row["id"]), False)
    fresh = await get_post_by_id(bot.db, int(row["id"]))
    await redraw_carrier(bot, guild, fresh, actor, via=via)
    await drop_the_doors_own(bot, guild, row)
    for key in (FRONTDOOR_MESSAGE, FRONTDOOR_CHANNEL):
        await bot.store.clear(guild.id, key)
    message_id = row_value(row, "message_id") or shadow_id(row)
    await log_action(
        bot,
        guild,
        kind_via(TAKEN_DOWN, via),
        actor=actor,
        details={
            "slug": row_value(row, "slug"),
            "channel_id": row_value(row, "channel_id"),
            "message_id": message_id,
            "off_the_post": True,
            "via": via,
        },
    )
    return Outcome(
        True, DOOR_OFF_THE_POST_SAID.format(title=row_value(row, "title", "")), value=message_id
    )


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
    carrier = await carrier_up(bot, guild)
    if carrier is not None:
        return await door_on_the_post(bot, guild, actor, channel, carrier, via=via)
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel.id):
        await log_action(
            bot,
            guild,
            kind_via(WOULD_POST, via),
            actor=actor,
            details={"channel_id": channel.id, "via": via},
        )
        return refusal(DOOR_GUARDED.format(wanted=channel.id), "test_mode", 409)
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
    carrier = await door_carrier(bot.db, guild.id)
    if carrier is not None and door_drawn(carrier) and is_posted(carrier):
        return await take_the_door_off_its_post(bot, guild, actor, carrier, via=via)
    if carrier is not None:
        await set_carries_door(bot.db, int(carrier["id"]), False)
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
    return Outcome(
        True, DOOR_DOWN_SAID, value=message_id
    )


class FrontDoor(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._shadowed: set[int] = set()
        self._reconciles = Reconciler()
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
        await self.reconcile(skip_if_recent=True)
        if not self._reconcile_loop.is_running():
            self._reconcile_loop.start()

    @commands.Cog.listener()
    async def on_post_published(self, guild: Any, row: Any) -> None:
        """A re-posted rules message moves what follows it, at once and on the next sweep."""
        if not self.bot.db.is_connected:
            return
        if str(row_value(row, "slug", "")) != followed_slug(
            self.bot.store, guild.id
        ) and not carries_door(row):
            return
        await self._reconciles.run(lambda: self._redoor(guild), stamp=False)

    async def redraw_now(self, guild: Any) -> bool:
        """A block's words were saved on the site: the carrier is redrawn under the sweep's lock."""
        if not self.bot.db.is_connected:
            return False
        return await self._reconciles.run(lambda: self._redoor(guild), stamp=False)

    async def redraw_blocks_now(self, guild: Any) -> bool:
        """Any other block's words were saved: every carrier is redrawn under the same lock."""
        if not self.bot.db.is_connected:
            return False
        return await self._reconciles.run(lambda: self._redraw_all(guild), stamp=False)

    async def _redraw_all(self, guild: Any) -> None:
        await self._redoor(guild)
        await keep_drawn(self.bot, guild)

    async def keep_live_now(self, guild: Any) -> bool:
        """A live block's list may have moved: its carriers are redrawn under the same lock."""
        if not self.bot.db.is_connected:
            return False
        return await self._reconciles.run(lambda: self._keep_live(guild), stamp=False)

    async def _keep_live(self, guild: Any) -> None:
        carrier = await carrier_up(self.bot, guild)
        if carrier is not None and await carries_live(self.bot.db, int(carrier["id"])):
            await keep_the_ride(self.bot, guild, carrier)
        await keep_drawn(self.bot, guild, LIVE_KINDS)

    async def reconcile(self, *, skip_if_recent: bool = False) -> bool:
        return await self._reconciles.run(self._sweep, skip_if_recent=skip_if_recent)

    async def _sweep(self) -> None:
        for guild in list(getattr(self.bot, "guilds", ())):
            if getattr(guild, "unavailable", False):
                continue
            await self._redoor(guild)
            await keep_drawn(self.bot, guild)
        self.last_ok_at = now_iso()

    async def _redoor(self, guild: Any) -> None:
        """A door deleted by hand is put back, and one the rules message has overtaken is
        posted again so it stays directly under the rules."""
        bot = self.bot
        store = bot.store
        carrier = await carrier_up(bot, guild)
        if carrier is not None:
            await keep_the_ride(bot, guild, carrier)
            return
        channel, message_id = where_the_door_is(bot, guild)
        if not door_is_on(store, guild.id):
            if store.get(guild.id, FRONTDOOR_CHANNEL):
                await take_door_down(bot, guild, None)
            return
        if not store.get(guild.id, FRONTDOOR_CHANNEL) or channel is None:
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
        overtaken = await overtaken_by(
            bot, guild, channel, message_id, followed_slug(store, guild.id)
        )
        if overtaken is None and message_id and await message_is_there(channel, message_id):
            self._shadowed.discard(guild.id)
            await hide_ticket_button(bot, guild)
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
        also = await duplicates_near(channel, message_id, f"{CUSTOM_ID_HEAD}:")
        if also:
            await log_action(
                bot,
                guild,
                DUPLICATE_SEEN,
                details={"channel_id": channel.id, "message_id": message_id, "also": also},
            )
            return
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
    "DUPLICATE_SEEN",
    "GONE",
    "MOVED",
    "OPENERS",
    "POSTED",
    "POST_FAILED",
    "REDRAWN_ON_POST",
    "RIDES_POST",
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
    "carried_parts",
    "carrier_up",
    "door_follows_post",
    "door_leaves_post",
    "door_on_the_post",
    "door_rides_post",
    "drop_the_doors_own",
    "keep_the_ride",
    "mirror_the_ride",
    "ours",
    "redraw_carrier",
    "release_the_ride",
    "take_the_door_off_its_post",
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
