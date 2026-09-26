from __future__ import annotations

import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ... import shadow
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
    DOOR_NO_HOME,
    DOOR_NOT_UP,
    DOOR_OFF,
    DOOR_POSTED_SAID,
    DOOR_REHEARSAL_DOWN_SAID,
    DOOR_REHEARSING_SAID,
    DOOR_SHADOW_LINE,
    DOOR_SHADOW_LINE_HOMELESS,
    DOOR_SHADOW_LINE_NOWHERE,
    DOOR_SHADOW_SAID,
    DOOR_STUCK,
    EVENT,
    EVENT_HANDOFF_TEXT,
    EVENT_HANDOFF_TITLE,
    KINDS,
    LABEL_DEFAULTS,
    PANEL_TIMEOUT_FOOTER,
    REQUEST,
    SHADOW_FEATURE,
    TICKET,
    custom_id,
    door_embed,
    door_hash,
    door_is_on,
    door_rehearses,
    door_takes_over,
    followed_slug,
    label_for,
    panel_follows_the_door,
    rehearsal_copy,
    rehearsal_stamp,
    rehearsal_takes_over,
)
from ...golive import now_iso
from ...logkinds import VIA_DISCORD, kind_via
from ...loops import Reconciler, wait_ready
from ...modmail import panel_rehearsal_copy
from ...panels import Outcome, Panel, answer, panel_minutes, refusal
from ...posted import drop_message, duplicates_near, message_is_there, overtaken_by
from ...posts import row_value, where_words
from ...settings_store import (
    FRONTDOOR_CHANNEL,
    FRONTDOOR_MESSAGE,
    FRONTDOOR_PANEL_MINUTES,
    FRONTDOOR_SHADOW_HASH,
    FRONTDOOR_SHADOW_MESSAGE,
    GUILD_ONLY,
    MODMAIL_PANEL_MESSAGE,
    MODMAIL_PANEL_SHADOW_HASH,
    MODMAIL_PANEL_SHADOW_MESSAGE,
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
POSTED_SHADOW = "frontdoor.posted_shadow"
UPDATED_SHADOW = "frontdoor.updated_shadow"
TAKEN_DOWN_SHADOW = "frontdoor.taken_down_shadow"


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


def shadow_words(bot: Any, guild: Any) -> str:
    """What shadow is doing to the door, in words, for a staffer — never posted anywhere."""
    store = bot.store
    if not door_rehearses(store, guild.id):
        return ""
    home = shadow.channel_id(bot, guild, feature=SHADOW_FEATURE)
    if not home:
        return DOOR_SHADOW_LINE_HOMELESS
    wanted = store.get(guild.id, FRONTDOOR_CHANNEL)
    if not wanted:
        return DOOR_SHADOW_LINE_NOWHERE.format(home=where_words(guild, home))
    return DOOR_SHADOW_LINE.format(
        home=where_words(guild, home), where=where_words(guild, wanted)
    )


def staff_shadow_words(bot: Any, guild: Any, actor: Any) -> str:
    try:
        staff = actor is not None and bot.store.is_staff(actor)
    except Exception:
        staff = False
    return shadow_words(bot, guild) if staff else ""


def build_panel(bot: Any, guild: Any, actor: Any = None) -> tuple[discord.Embed, DoorPanel]:
    """The one card: the posted message wears it, and so does `/ask`."""
    store = bot.store
    view = DoorPanel(panel_minutes(store, guild.id, FRONTDOOR_PANEL_MINUTES))
    for kind in KINDS:
        view.add_item(DOORS[kind](label_for(store, guild.id, kind)))
    embed = door_embed(store, guild.id)
    said = staff_shadow_words(bot, guild, actor)
    if said:
        embed.set_footer(text=said)
    return embed, view


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
    if not panel_follows_the_door(bot.store, guild.id) and door_takes_over(
        bot.store, guild.id
    ) != int(channel.id):
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


async def hide_rehearsed_ticket_button(bot: Any, guild: Any) -> int | None:
    """One door per channel holds in the rehearsal home: the mods see the rules post, then
    the front door under it, exactly as #welcome will show them."""
    store = bot.store
    if not rehearsal_takes_over(store, guild.id):
        return None
    message_id = panel_rehearsal_copy(store, guild.id)
    if not message_id:
        return None
    where, _ = await shadow.find_copy(bot, guild, message_id, feature=SHADOW_FEATURE)
    if where is not None and not await drop_message(
        bot, guild, where, message_id, would_kind=WOULD_HIDE_TICKET_BUTTON
    ):
        return None
    await store.clear(guild.id, MODMAIL_PANEL_SHADOW_MESSAGE)
    await store.clear(guild.id, MODMAIL_PANEL_SHADOW_HASH)
    await log_action(
        bot,
        guild,
        TICKET_BUTTON_HIDDEN,
        details={
            "channel_id": getattr(where, "id", None),
            "message_id": message_id,
            "rehearsal": True,
        },
    )
    return message_id


async def lower_the_real_door(
    bot: Any, guild: Any, actor: Any = None, *, via: str = VIA_DISCORD
) -> int | None:
    """Shadow leaves nothing in the real channel; where the door is AIMED is remembered."""
    channel, message_id = where_the_door_is(bot, guild)
    if not message_id:
        return None
    if channel is not None and not await drop_message(
        bot, guild, channel, message_id, would_kind=WOULD_TAKE_DOWN
    ):
        return None
    await bot.store.clear(guild.id, FRONTDOOR_MESSAGE)
    await log_action(
        bot,
        guild,
        kind_via(TAKEN_DOWN, via),
        actor=actor,
        details={
            "channel_id": getattr(channel, "id", None),
            "message_id": message_id,
            "rehearsal": True,
            "via": via,
        },
    )
    return message_id


async def start_rehearsing(bot: Any, guild: Any, actor: Any = None, *, via: str = VIA_DISCORD):
    """Going into shadow takes the real door — and the button it replaces — down first."""
    await lower_the_real_door(bot, guild, actor, via=via)
    await hide_ticket_button(bot, guild)


def rehearsal_payload(bot: Any, guild: Any, wanted: Any) -> dict[str, Any]:
    """The real card, with one line above it saying where the real one is aimed."""
    note = shadow.note_line(bot, guild, where_words(guild, getattr(wanted, "id", wanted)))
    return {
        "content": note or None,
        "embed": door_embed(bot.store, guild.id),
        "view": door_view(bot, guild),
        "allowed_mentions": discord.AllowedMentions.none(),
    }


def rehearsal_hash(bot: Any, guild: Any, wanted: Any) -> str:
    note = shadow.note_line(bot, guild, where_words(guild, getattr(wanted, "id", wanted)))
    return door_hash(bot.store, guild.id, note)


async def drop_rehearsal(bot: Any, guild: Any, actor: Any = None, *, via: str = VIA_DISCORD):
    """The rehearsal copy goes wherever it ended up, and its two keys go with it."""
    message_id = rehearsal_copy(bot.store, guild.id)
    if not message_id:
        return None
    where, _ = await shadow.find_copy(bot, guild, message_id, feature=SHADOW_FEATURE)
    if where is not None and not await drop_message(
        bot, guild, where, message_id, would_kind=WOULD_TAKE_DOWN
    ):
        return None
    await bot.store.clear(guild.id, FRONTDOOR_SHADOW_MESSAGE)
    await bot.store.clear(guild.id, FRONTDOOR_SHADOW_HASH)
    await log_action(
        bot,
        guild,
        kind_via(TAKEN_DOWN_SHADOW, via),
        actor=actor,
        details={
            "channel_id": getattr(where, "id", None),
            "message_id": message_id,
            "found": where is not None,
            "via": via,
        },
    )
    return message_id


async def rehearse_door(
    bot: Any, guild: Any, actor: Any, wanted: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Test mode refuses the real channel, so the real card goes to the rehearsal home.

    The caller owns the would-row: a person who pressed hears about it every time, the
    five-minute sweep says it once."""
    store = bot.store
    guard = getattr(bot, "guard", None)
    rehearsing = door_rehearses(store, guild.id)
    home_id = shadow.channel_id(bot, guild, feature=SHADOW_FEATURE)
    home = shadow.channel_of(bot, guild, home_id)
    if home is None or (guard is not None and not guard.allows_channel(home_id)):
        return refusal(DOOR_NO_HOME if rehearsing else DOOR_GUARDED, "test_mode", 409)
    copy_id = rehearsal_copy(store, guild.id)
    where, message = await shadow.find_copy(bot, guild, copy_id, feature=SHADOW_FEATURE)
    here = message is not None and int(where.id) == int(home.id)
    overtaken = (
        await overtaken_by(bot, guild, home, copy_id, followed_slug(store, guild.id))
        if here
        else None
    )
    payload = rehearsal_payload(bot, guild, wanted)
    stamp = rehearsal_hash(bot, guild, wanted)
    said = (DOOR_SHADOW_SAID if rehearsing else DOOR_REHEARSING_SAID).format(
        where=home.id, wanted=getattr(wanted, "id", wanted)
    )
    by = getattr(actor, "id", actor)
    if here and overtaken is None:
        if rehearsal_stamp(store, guild.id) == stamp:
            await hide_rehearsed_ticket_button(bot, guild)
            return Outcome(True, said, value=int(message.id))
        try:
            await message.edit(**payload)
        except Exception as exc:
            return await _rehearsal_stuck(bot, guild, actor, home, exc)
        await store.set(guild.id, FRONTDOOR_SHADOW_HASH, stamp, by=by)
        await log_action(
            bot,
            guild,
            kind_via(UPDATED_SHADOW, via),
            actor=actor,
            details={
                "channel_id": home.id,
                "shadow_home": home.id,
                "wanted_channel_id": getattr(wanted, "id", wanted),
                "message_id": int(message.id),
                "via": via,
            },
        )
        await hide_rehearsed_ticket_button(bot, guild)
        return Outcome(True, said, value=int(message.id))
    moved_or_gone = BELOW_POST if overtaken is not None else GONE
    if overtaken is not None or (copy_id and message is None):
        await log_action(
            bot,
            guild,
            moved_or_gone,
            details={
                "channel_id": getattr(where, "id", home.id),
                "message_id": copy_id,
                "post_message_id": overtaken,
                "rehearsal": True,
            },
        )
    try:
        fresh = await home.send(**payload)
    except Exception as exc:
        return await _rehearsal_stuck(bot, guild, actor, home, exc)
    if message is not None:
        await drop_message(bot, guild, where, int(message.id), would_kind=WOULD_TAKE_DOWN)
    await store.set(guild.id, FRONTDOOR_SHADOW_MESSAGE, str(fresh.id), by=by)
    await store.set(guild.id, FRONTDOOR_SHADOW_HASH, stamp, by=by)
    await log_action(
        bot,
        guild,
        kind_via(POSTED_SHADOW, via),
        actor=actor,
        details={
            "channel_id": home.id,
            "shadow_home": home.id,
            "wanted_channel_id": getattr(wanted, "id", wanted),
            "message_id": fresh.id,
            "via": via,
        },
    )
    await hide_rehearsed_ticket_button(bot, guild)
    return Outcome(True, said, value=int(fresh.id))


async def _rehearsal_stuck(
    bot: Any, guild: Any, actor: Any, home: Any, exc: Exception
) -> Outcome:
    log.warning("frontdoor: could not put the rehearsal copy up: %s", exc)
    await log_action(
        bot,
        guild,
        POST_FAILED,
        actor=actor,
        details={
            "channel_id": home.id,
            "rehearsal": True,
            "reason": f"{type(exc).__name__}: {exc}",
        },
    )
    return refusal(DOOR_STUCK, "door_stuck", 500)


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
    rehearsing = door_rehearses(bot.store, guild.id)
    if rehearsing or (guard is not None and not guard.allows_channel(channel.id)):
        if rehearsing:
            await start_rehearsing(bot, guild, actor, via=via)
        outcome = await rehearse_door(bot, guild, actor, channel, via=via)
        if outcome.ok:
            await bot.store.set(
                guild.id, FRONTDOOR_CHANNEL, channel.id, by=getattr(actor, "id", actor)
            )
        else:
            await log_action(
                bot,
                guild,
                kind_via(WOULD_POST, via),
                actor=actor,
                details={
                    "channel_id": channel.id,
                    "shadow_home": shadow.channel_id(bot, guild, feature=SHADOW_FEATURE),
                    "via": via,
                },
            )
        return outcome
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
    if not bot.store.get(guild.id, FRONTDOOR_CHANNEL) and not rehearsal_copy(
        bot.store, guild.id
    ):
        return refusal(DOOR_NOT_UP, "no_door", 404)
    if channel is not None and message_id:
        await drop_message(bot, guild, channel, message_id, would_kind=WOULD_TAKE_DOWN)
    rehearsed = await drop_rehearsal(bot, guild, actor, via=via)
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
        True, DOOR_REHEARSAL_DOWN_SAID if rehearsed else DOOR_DOWN_SAID, value=message_id
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
        if str(row_value(row, "slug", "")) != followed_slug(self.bot.store, guild.id):
            return
        await self._reconciles.run(lambda: self._redoor(guild), stamp=False)

    async def reconcile(self, *, skip_if_recent: bool = False) -> bool:
        return await self._reconciles.run(self._sweep, skip_if_recent=skip_if_recent)

    async def _sweep(self) -> None:
        for guild in list(getattr(self.bot, "guilds", ())):
            if getattr(guild, "unavailable", False):
                continue
            await self._redoor(guild)
        self.last_ok_at = now_iso()

    async def _redoor(self, guild: Any) -> None:
        """A door deleted by hand is put back, and one the rules message has overtaken is
        posted again so it stays directly under the rules."""
        bot = self.bot
        store = bot.store
        channel, message_id = where_the_door_is(bot, guild)
        if not door_is_on(store, guild.id):
            if store.get(guild.id, FRONTDOOR_CHANNEL) or rehearsal_copy(store, guild.id):
                await take_door_down(bot, guild, None)
            return
        if not store.get(guild.id, FRONTDOOR_CHANNEL) or channel is None:
            return
        guard = getattr(bot, "guard", None)
        rehearsing = door_rehearses(store, guild.id)
        if rehearsing or (guard is not None and not guard.allows_channel(channel.id)):
            if rehearsing:
                await start_rehearsing(bot, guild, None)
            outcome = await rehearse_door(bot, guild, None, channel)
            if outcome.ok:
                self._shadowed.discard(guild.id)
            elif outcome.code == "test_mode" and guild.id not in self._shadowed:
                self._shadowed.add(guild.id)
                await log_action(
                    bot,
                    guild,
                    WOULD_POST,
                    details={
                        "channel_id": channel.id,
                        "shadow_home": shadow.channel_id(bot, guild, feature=SHADOW_FEATURE),
                        "reason": "reconcile",
                    },
                )
            return
        await drop_rehearsal(bot, guild, None)
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
    "POSTED_SHADOW",
    "POST_FAILED",
    "TAKEN_DOWN",
    "TAKEN_DOWN_SHADOW",
    "TICKET_BUTTON_HIDDEN",
    "UPDATED_SHADOW",
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
    "drop_rehearsal",
    "event_handoff",
    "hide_rehearsed_ticket_button",
    "hide_ticket_button",
    "lower_the_real_door",
    "open_the_event",
    "open_the_request",
    "open_the_ticket",
    "post_door",
    "rehearsal_hash",
    "rehearsal_payload",
    "rehearse_door",
    "shadow_words",
    "staff_shadow_words",
    "start_rehearsing",
    "take_door_down",
    "where_the_door_is",
]
