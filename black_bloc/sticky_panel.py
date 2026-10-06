"""Sticky messages: the /sticky panel — the list, one sticky's card, and the words modal."""

from __future__ import annotations

from typing import Any

import discord

from . import sticky as rules
from .actionlog import send_logs
from .command_errors import AnswersErrors
from .panels import (
    DESCRIPTION_LIMIT,
    Panel,
    answer,
    capped_placeholder,
    clamped,
    confirm,
    confirm_items,
    db_up,
    opened,
    retire,
    site_page_url,
    still_staff,
)
from .sticky_posts import desk_of

SELECT_MAX = 25
STYLES = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}
CHANNEL_TYPES = [discord.ChannelType.text, discord.ChannelType.news]


class StickyPanel(Panel):
    def __init__(self, minutes: int, *, channel_id: int | None = None) -> None:
        super().__init__(minutes, footer=rules.PANEL_TIMEOUT_FOOTER, again=self.shown_again)
        self.channel_id = channel_id

    async def shown_again(self, interaction: discord.Interaction, previous: Any) -> None:
        if self.channel_id is None:
            await render_root(interaction, previous)
            return
        await render_card(interaction, self.channel_id, previous)


def minutes_for(bot: Any, guild_id: int) -> int:
    return rules.panel_minutes(bot.store, guild_id)


def site_url(bot: Any) -> str | None:
    url = site_page_url(getattr(getattr(bot, "settings", None), "origin", ""), rules.LOG_FEATURE)
    return f"{url}{rules.SITE_ANCHOR}" if url else None


def channel_names(guild: Any, rows: Any) -> dict[int, str]:
    found: dict[int, str] = {}
    for row in rows:
        channel = guild.get_channel(int(row["channel_id"]))
        if channel is not None:
            found[int(row["channel_id"])] = str(getattr(channel, "name", row["channel_id"]))
    return found


async def build_root(bot: Any, guild: Any) -> tuple[discord.Embed, StickyPanel]:
    rows = await rules.rows_for_guild(bot.db, guild.id)
    mode = rules.mode_of(bot.store, guild.id)
    embed = discord.Embed(
        title=rules.PANEL_TITLE, description=clamped(rules.root_lines(rows, mode))
    )
    view = StickyPanel(minutes_for(bot, guild.id))
    options = rules.sticky_options(rows, channel_names(guild, rows))
    if options:
        view.add_item(StickyPick(options))
    view.add_item(AddPick())
    view.add_item(ModePick(mode))
    url = site_url(bot)
    for move in rules.root_buttons(has_site=url is not None):
        view.add_item(SiteButton(move, url) if move.action == rules.SITE else MoveButton(move))
    return (embed, view)


def build_card(bot: Any, guild: Any, row: Any) -> tuple[discord.Embed, StickyPanel]:
    channel_id = int(row["channel_id"])
    channel = guild.get_channel(channel_id)
    name = getattr(channel, "name", None)
    title = (
        rules.CARD_TITLE.format(name=name)
        if name
        else rules.GONE_CHANNEL.format(ident=channel_id)
    )
    state = rules.row_line(row, rules.mode_of(bot.store, guild.id))
    body = str(row["text"])[: DESCRIPTION_LIMIT - len(state) - 2]
    embed = discord.Embed(title=title[:256], description=f"{body}\n\n{state}")
    view = StickyPanel(minutes_for(bot, guild.id), channel_id=channel_id)
    for move in rules.card_buttons(row):
        view.add_item(MoveButton(move))
    return (embed, view)


async def show(interaction: discord.Interaction, built: Any, previous: Any) -> None:
    embed, view = built
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def render_root(interaction: discord.Interaction, previous: Any = None) -> None:
    await show(interaction, await build_root(interaction.client, interaction.guild), previous)


async def render_card(
    interaction: discord.Interaction, channel_id: int, previous: Any = None
) -> None:
    """A sticky that is gone by the time its card is asked for lands back on the list."""
    bot = interaction.client
    row = await rules.get_row(bot.db, interaction.guild.id, channel_id)
    if row is None:
        await render_root(interaction, previous)
        return
    await show(interaction, build_card(bot, interaction.guild, row), previous)


async def back_to_root(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    await render_root(interaction, previous)


async def open_card(
    interaction: discord.Interaction, channel_id: int, previous: Any = None
) -> None:
    if not await opened(interaction):
        return
    await render_card(interaction, channel_id, previous)


async def run_mode(interaction: discord.Interaction, value: str, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    outcome = await desk_of(interaction.client).set_mode(
        interaction.guild, value, interaction.user
    )
    await render_root(interaction, previous)
    await answer(interaction, outcome.message)


async def run_save(
    interaction: discord.Interaction, channel_id: int, text: str, previous: Any = None
) -> None:
    """A refused save is answered and the card is left alone, so it cannot read as a save."""
    if not await opened(interaction):
        return
    outcome = await desk_of(interaction.client).save(
        interaction.guild, channel_id, text, interaction.user
    )
    if outcome.ok:
        await render_card(interaction, channel_id, previous)
    await answer(interaction, outcome.message)


async def run_move(
    interaction: discord.Interaction, action: str, channel_id: int, previous: Any = None
) -> None:
    if not await opened(interaction):
        return
    desk = desk_of(interaction.client)
    move = desk.pause if action == rules.PAUSE else desk.resume
    outcome = await move(interaction.guild, channel_id, interaction.user)
    await render_card(interaction, channel_id, previous)
    await answer(interaction, outcome.message)


async def ask_remove(
    interaction: discord.Interaction, channel_id: int, previous: Any = None
) -> None:
    if not await opened(interaction):
        return
    bot = interaction.client
    row = await rules.get_row(bot.db, interaction.guild.id, channel_id)
    if row is None:
        await render_root(interaction, previous)
        await answer(interaction, rules.NO_STICKY)
        return
    embed, _ = build_card(bot, interaction.guild, row)
    view = StickyPanel(minutes_for(bot, interaction.guild.id), channel_id=channel_id)

    async def yes(pressed: discord.Interaction, card: Any) -> None:
        await run_remove(pressed, channel_id, card)

    async def no(pressed: discord.Interaction, card: Any) -> None:
        await open_card(pressed, channel_id, card)

    await confirm(
        interaction,
        view,
        embed,
        confirm_items(yes=rules.REMOVE_YES, no=rules.BACK_MOVE.label, on_yes=yes, on_no=no),
        previous,
        question=rules.REMOVE_QUESTION.format(channel_id=channel_id),
    )


async def run_remove(
    interaction: discord.Interaction, channel_id: int, previous: Any = None
) -> None:
    if not await opened(interaction):
        return
    outcome = await desk_of(interaction.client).remove(
        interaction.guild, channel_id, interaction.user
    )
    await render_root(interaction, previous)
    await answer(interaction, outcome.message)


async def open_words(
    interaction: discord.Interaction, channel_id: int, previous: Any = None
) -> None:
    """A modal has to be the first answer, so staff and the database are asked without a defer."""
    if not await still_staff(interaction):
        return
    if not await db_up(interaction):
        return
    row = await rules.get_row(interaction.client.db, interaction.guild.id, channel_id)
    await interaction.response.send_modal(
        WordsModal(channel_id, row["text"] if row is not None else "", previous)
    )


class MoveButton(discord.ui.Button):
    def __init__(self, move: rules.StickyMove) -> None:
        super().__init__(label=move.label, style=STYLES[move.style], row=move.row)
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        action = self.move.action
        channel_id = getattr(view, "channel_id", None)
        if action == rules.LOGS:
            await send_logs(interaction, rules.LOG_FEATURE)
        elif action in (rules.REFRESH, rules.BACK):
            await back_to_root(interaction, view)
        elif action == rules.EDIT:
            await open_words(interaction, channel_id, view)
        elif action == rules.REMOVE:
            await ask_remove(interaction, channel_id, view)
        elif action == rules.PAUSE:
            await run_move(interaction, rules.PAUSE, channel_id, view)
        else:
            await run_move(interaction, rules.RESUME, channel_id, view)


class SiteButton(discord.ui.Button):
    def __init__(self, move: rules.StickyMove, url: str) -> None:
        super().__init__(label=move.label, style=discord.ButtonStyle.link, url=url, row=move.row)


class StickyPick(discord.ui.Select):
    def __init__(self, options: list[tuple[str, int]]) -> None:
        shown = options[:SELECT_MAX]
        super().__init__(
            placeholder=capped_placeholder(
                len(shown), len(options), pick=rules.PICK_PLACEHOLDER
            ),
            options=[
                discord.SelectOption(label=label, value=str(ident)) for label, ident in shown
            ],
            min_values=1,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_card(interaction, int(self.values[0]), self.view)


class AddPick(discord.ui.ChannelSelect):
    def __init__(self) -> None:
        super().__init__(
            placeholder=rules.ADD_PLACEHOLDER,
            channel_types=CHANNEL_TYPES,
            min_values=1,
            max_values=1,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_words(interaction, int(self.values[0].id), self.view)


class ModePick(discord.ui.Select):
    def __init__(self, current: Any) -> None:
        super().__init__(
            placeholder=rules.MODE_PLACEHOLDER,
            options=[
                discord.SelectOption(label=label, value=value, default=now)
                for value, label, now in rules.mode_options(current)
            ],
            min_values=1,
            max_values=1,
            row=2,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_mode(interaction, self.values[0], self.view)


class WordsModal(AnswersErrors, discord.ui.Modal):
    words = discord.ui.TextInput(
        label=rules.WORDS_LABEL, style=discord.TextStyle.paragraph, max_length=rules.TEXT_MAX
    )

    def __init__(self, channel_id: int, current: str = "", previous: Any = None) -> None:
        super().__init__(title=rules.WORDS_TITLE[:45])
        self.channel_id = int(channel_id)
        self.previous = previous
        self.words.default = current or None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_save(interaction, self.channel_id, str(self.words), self.previous)


__all__ = [
    "AddPick",
    "ModePick",
    "MoveButton",
    "StickyPanel",
    "StickyPick",
    "WordsModal",
    "build_card",
    "build_root",
    "render_card",
    "render_root",
]
