"""The /pb panel's Settings door: the board's size, order and channel, and its pinned post."""

from __future__ import annotations

from typing import Any

import discord

from . import points_moves as moves
from . import points_post
from . import sticky as sticky_rules
from .cogs.core import set_key
from .panels import answer, clamped, opened, retire
from .points.model import BY_POINTS, BY_XP
from .points_panel import BOARD, SETTINGS, BoardPanel, Move, heading_of
from .settings_store import POINTS_BOARD_ORDER, POINTS_CHANNEL, POINTS_TOP_N
from .sticky_posts import desk_of

TITLE = "Leaderboard settings"
TOP_LINE = "**Top** {n}"
ORDER_LINE = "**Order** {order}"
CHANNEL_LINE = "**Channel** {channel}"
NO_CHANNEL = "none yet"
PINNED_LINE = "**Pinned** {state}"
NOT_PINNED = "not yet"
OTHER_LINE = "**Already there** {words}"
TOP_CHOICES = (5, 10, 15, 20, 25)
TOP_OPTION = "Top {n}"
TOP_PLACEHOLDER = "How many places it shows…"
ORDER_PLACEHOLDER = "What it ranks by…"
CHANNEL_PLACEHOLDER = "The leaderboard channel…"
PIN_LABEL = "Pin the leaderboard here"
REPLACE_LABEL = "Replace it"
PIN = "pin"
REPLACE = "replace"
PAUSE = "pause"
RESUME = "resume"
CHANNEL_TYPES = [discord.ChannelType.text, discord.ChannelType.news]


async def state_lines(bot: Any, guild: Any, found: dict[str, Any]) -> list[str]:
    store = bot.store
    order = str(store.get(guild.id, POINTS_BOARD_ORDER) or BY_POINTS)
    lines = [
        TOP_LINE.format(n=moves.top_of(store, guild.id)),
        ORDER_LINE.format(order=heading_of(store, guild.id, order)),
        CHANNEL_LINE.format(channel=found["channel"] or NO_CHANNEL),
    ]
    sticky = found["sticky"]
    if sticky is None:
        lines.append(PINNED_LINE.format(state=NOT_PINNED))
    else:
        mode, _ = await desk_of(bot).rule_of(guild, sticky)
        lines.append(PINNED_LINE.format(state=sticky_rules.row_line(sticky, mode)))
    if found["other"] is not None:
        words = sticky_rules.preview(sticky_rules.words_of(found["other"]))
        lines.append(OTHER_LINE.format(words=words))
    return lines


def moves_of(found: dict[str, Any]) -> list[tuple[str, str, discord.ButtonStyle]]:
    """Only the moves that would work: Pin where it is not yet, Replace over another sticky."""
    found_moves: list[tuple[str, str, discord.ButtonStyle]] = []
    sticky = found["sticky"]
    here = sticky is not None and int(sticky["channel_id"]) == int(found["channel_id"] or 0)
    if found["channel_id"] and not here:
        if found["other"] is not None:
            found_moves.append((REPLACE, REPLACE_LABEL, discord.ButtonStyle.danger))
        else:
            found_moves.append((PIN, PIN_LABEL, discord.ButtonStyle.primary))
    if sticky is not None:
        running = sticky_rules.is_running(sticky)
        move = sticky_rules.PAUSE_MOVE if running else sticky_rules.RESUME_MOVE
        if sticky["trouble"]:
            move = sticky_rules.RETRY_MOVE
        action = PAUSE if running else RESUME
        found_moves.append((action, move.label, discord.ButtonStyle.secondary))
    return found_moves


async def build_settings(bot: Any, guild: Any, *, by: str = BY_POINTS) -> tuple[Any, Any]:
    found = await points_post.board_state(bot, guild)
    embed = discord.Embed(title=TITLE, description=clamped(await state_lines(bot, guild, found)))
    view = BoardPanel(bot, guild, by=by, surface=SETTINGS)
    view.add_item(TopPick(moves.top_of(bot.store, guild.id)))
    view.add_item(OrderPick(bot, guild))
    view.add_item(ChannelPick(found["channel_id"]))
    for action, label, style in moves_of(found):
        view.add_item(BoardMove(label, action, style))
    view.add_item(Move(moves.said(bot.store, guild.id, "points_back_label"), BOARD, row=3))
    return (embed, view)


async def render_settings(interaction: discord.Interaction, previous: Any = None) -> None:
    by = getattr(previous, "by", None) or BY_POINTS
    embed, view = await build_settings(interaction.client, interaction.guild, by=by)
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def open_settings(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    await render_settings(interaction, previous)


async def change(
    interaction: discord.Interaction, key: str, value: Any, previous: Any = None
) -> None:
    """One write through the settings door every panel shares; a refusal is said, not hidden."""
    if not await opened(interaction):
        return
    outcome = await set_key(interaction.client, interaction.guild, key, value, interaction.user)
    await render_settings(interaction, previous)
    if not outcome.ok:
        await answer(interaction, outcome.message)


async def pressed(interaction: discord.Interaction, action: str, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    bot = interaction.client
    guild = interaction.guild
    if action in (PIN, REPLACE):
        outcome = await points_post.pin_board(
            bot, guild, interaction.user, replace=action == REPLACE
        )
    else:
        found = await points_post.board_state(bot, guild)
        sticky = found["sticky"]
        if sticky is None:
            await render_settings(interaction, previous)
            return
        desk = desk_of(bot)
        move = desk.pause if action == PAUSE else desk.resume
        outcome = await move(guild, int(sticky["channel_id"]), interaction.user)
    await render_settings(interaction, previous)
    await answer(interaction, outcome.message)


class TopPick(discord.ui.Select):
    def __init__(self, current: int) -> None:
        super().__init__(
            placeholder=TOP_PLACEHOLDER,
            options=[
                discord.SelectOption(
                    label=TOP_OPTION.format(n=n), value=str(n), default=n == current
                )
                for n in TOP_CHOICES
            ],
            min_values=1,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await change(interaction, POINTS_TOP_N, int(self.values[0]), self.view)


class OrderPick(discord.ui.Select):
    def __init__(self, bot: Any, guild: Any) -> None:
        current = str(bot.store.get(guild.id, POINTS_BOARD_ORDER) or BY_POINTS)
        super().__init__(
            placeholder=ORDER_PLACEHOLDER,
            options=[
                discord.SelectOption(
                    label=heading_of(bot.store, guild.id, order)[:100],
                    value=order,
                    default=order == current,
                )
                for order in (BY_POINTS, BY_XP)
            ],
            min_values=1,
            max_values=1,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await change(interaction, POINTS_BOARD_ORDER, self.values[0], self.view)


class ChannelPick(discord.ui.ChannelSelect):
    def __init__(self, current: int | None) -> None:
        super().__init__(
            placeholder=CHANNEL_PLACEHOLDER,
            channel_types=CHANNEL_TYPES,
            default_values=[discord.Object(id=current)] if current else [],
            min_values=1,
            max_values=1,
            row=2,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await change(interaction, POINTS_CHANNEL, int(self.values[0].id), self.view)


class BoardMove(discord.ui.Button):
    def __init__(self, label: str, action: str, style: discord.ButtonStyle) -> None:
        super().__init__(label=label[:80], style=style, row=3)
        self.action = action

    async def callback(self, interaction: discord.Interaction) -> None:
        await pressed(interaction, self.action, self.view)


__all__ = [
    "BoardMove",
    "ChannelPick",
    "OrderPick",
    "TopPick",
    "build_settings",
    "moves_of",
    "open_settings",
    "render_settings",
]
