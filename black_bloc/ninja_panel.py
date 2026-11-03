from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import discord

from . import ninja as rules
from . import ninja_store as store
from .cogs.core import set_key
from .command_errors import AnswersErrors
from .panels import (
    KEEP_IT,
    Panel,
    answer,
    clamped,
    confirm,
    confirm_items,
    opened,
    option_label,
    panel_minutes,
    retire,
    still_staff,
)
from .settings_store import NINJA_MODE

PANEL_MINUTES_KEY = "posts_panel_minutes"
SELECT_MAX = 25
TITLE_LIMIT = 45
HINT_LIMIT = 100
PLACEHOLDER_LIMIT = 150
LABEL_LIMIT = 80
NUMBER_CHARS = 6


@dataclass
class Draft:
    user_ids: list[int] = field(default_factory=list)
    channel_id: int | None = None


def said(bot: Any, guild: Any, key: str, **fields: Any) -> str:
    return rules.words(bot.store, guild.id, key, **fields)


class NinjaPanel(Panel):
    def __init__(self, bot: Any, guild: Any, *, draft: Draft | None = None) -> None:
        super().__init__(
            panel_minutes(bot.store, guild.id, PANEL_MINUTES_KEY),
            footer=said(bot, guild, "ninja_panel_footer"),
            again=self.shown_again,
        )
        self.draft = draft

    async def shown_again(self, interaction: discord.Interaction, previous: Any) -> None:
        if self.draft is not None:
            await render_card(interaction, self.draft, previous)
            return
        await render_root(interaction, previous)


def root_moves(mode: str) -> list[str]:
    return ["mark", "off" if mode == rules.ON else "on", "refresh"]


def card_moves(draft: Draft) -> list[str]:
    return (["next"] if draft.user_ids and draft.channel_id else []) + ["back"]


def mark_line(bot: Any, guild: Any, row: Any) -> str:
    made = rules.parse_when(row["made_at"])
    return said(
        bot,
        guild,
        "ninja_mark_line",
        user=int(row["user_id"]),
        channel=int(row["channel_id"]),
        left=rules.left_words(bot.store, guild.id, row["posts_left"], row["until"]),
        by=int(row["made_by"]) if row["made_by"] else "",
        made=f"<t:{int(made.timestamp())}:R>" if made else "",
    )


def root_lines(bot: Any, guild: Any, rows: list[Any]) -> list[str]:
    lines = [
        said(
            bot,
            guild,
            "ninja_state_line",
            emoji=rules.emoji_of(bot.store, guild.id),
            mode=rules.mode_of(bot.store, guild.id),
        )
    ]
    if not rows:
        return [*lines, said(bot, guild, "ninja_none_line")]
    return [*lines, *(mark_line(bot, guild, row) for row in rows)]


async def build_root(bot: Any, guild: Any) -> tuple[discord.Embed, NinjaPanel]:
    rows = await store.active(bot.db, guild.id)
    embed = discord.Embed(
        title=said(bot, guild, "ninja_panel_title"),
        description=clamped(root_lines(bot, guild, rows)),
    )
    view = NinjaPanel(bot, guild)
    for name in root_moves(rules.mode_of(bot.store, guild.id)):
        view.add_item(RootButton(bot, guild, name))
    if rows:
        view.add_item(EndPick(bot, guild, rows))
    return embed, view


def build_card(bot: Any, guild: Any, draft: Draft) -> tuple[discord.Embed, NinjaPanel]:
    lines = []
    if draft.user_ids and draft.channel_id:
        lines.append(
            said(
                bot,
                guild,
                "ninja_pick_line",
                who=rules.who_words(guild, draft.user_ids, rules.VIA_DISCORD),
                where=f"<#{draft.channel_id}>",
            )
        )
    embed = discord.Embed(title=said(bot, guild, "ninja_mark_label"), description=clamped(lines))
    view = NinjaPanel(bot, guild, draft=draft)
    view.add_item(WhoPick(bot, guild, draft))
    view.add_item(WherePick(bot, guild, draft))
    for name in card_moves(draft):
        view.add_item(CardButton(bot, guild, name, draft))
    return embed, view


async def show(interaction: discord.Interaction, built: Any, previous: Any) -> None:
    embed, view = built
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def render_root(interaction: discord.Interaction, previous: Any = None) -> None:
    await show(interaction, await build_root(interaction.client, interaction.guild), previous)


async def render_card(interaction: discord.Interaction, draft: Draft, previous: Any = None) -> None:
    await show(interaction, build_card(interaction.client, interaction.guild, draft), previous)


async def after(interaction: discord.Interaction, outcome: Any, previous: Any) -> None:
    await render_root(interaction, previous)
    await answer(interaction, outcome.message)


async def back_to_root(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    await render_root(interaction, previous)


def end_run(mark_id: int) -> Any:
    async def run(interaction: discord.Interaction, previous: Any = None) -> None:
        if not await opened(interaction):
            return
        outcome = await rules.end(interaction.client, interaction.guild, interaction.user, mark_id)
        await after(interaction, outcome, previous)

    return run


async def ask_end(interaction: discord.Interaction, row: Any, previous: Any) -> None:
    bot, guild = interaction.client, interaction.guild
    view = NinjaPanel(bot, guild)
    await confirm(
        interaction,
        view,
        discord.Embed(
            title=said(bot, guild, "ninja_panel_title"),
            description=said(
                bot,
                guild,
                "ninja_end_confirm",
                user=int(row["user_id"]),
                channel=int(row["channel_id"]),
            )[:4000],
        ),
        confirm_items(
            yes=said(bot, guild, "ninja_end_label")[:LABEL_LIMIT],
            no=KEEP_IT,
            on_yes=end_run(int(row["id"])),
            on_no=back_to_root,
        ),
        previous,
    )


async def run_mode(interaction: discord.Interaction, wanted: str, previous: Any) -> None:
    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    outcome = await set_key(bot, guild, NINJA_MODE, wanted, interaction.user)
    await render_root(interaction, previous)
    text = said(bot, guild, "ninja_mode_said", mode=wanted) if outcome.ok else outcome.message
    await answer(interaction, text)


ROOT_STYLES = {
    "mark": ("ninja_mark_label", discord.ButtonStyle.primary),
    "on": ("ninja_on_label", discord.ButtonStyle.success),
    "off": ("ninja_off_label", discord.ButtonStyle.secondary),
    "refresh": ("ninja_refresh_label", discord.ButtonStyle.secondary),
}
CARD_STYLES = {
    "next": ("ninja_next_label", discord.ButtonStyle.primary),
    "back": ("ninja_back_label", discord.ButtonStyle.secondary),
}


class RootButton(discord.ui.Button):
    def __init__(self, bot: Any, guild: Any, name: str) -> None:
        key, style = ROOT_STYLES[name]
        super().__init__(label=said(bot, guild, key)[:LABEL_LIMIT], style=style, row=0)
        self.name = name

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.name == "mark":
            if not await opened(interaction):
                return
            bot, guild = interaction.client, interaction.guild
            draft = Draft(channel_id=rules.default_channel(bot.store, guild.id))
            await render_card(interaction, draft, self.view)
            return
        if self.name in ("on", "off"):
            await run_mode(interaction, self.name, self.view)
            return
        await back_to_root(interaction, self.view)


class CardButton(discord.ui.Button):
    def __init__(self, bot: Any, guild: Any, name: str, draft: Draft) -> None:
        key, style = CARD_STYLES[name]
        super().__init__(label=said(bot, guild, key)[:LABEL_LIMIT], style=style, row=2)
        self.name = name
        self.draft = draft

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.name == "next":
            if not await still_staff(interaction):
                return
            await interaction.response.send_modal(
                LimitsModal(interaction.client, interaction.guild, self.draft, self.view)
            )
            return
        await back_to_root(interaction, self.view)


class WhoPick(discord.ui.UserSelect):
    def __init__(self, bot: Any, guild: Any, draft: Draft) -> None:
        super().__init__(
            placeholder=said(bot, guild, "ninja_who_placeholder")[:PLACEHOLDER_LIMIT],
            min_values=1,
            max_values=SELECT_MAX,
            row=0,
            default_values=[
                discord.SelectDefaultValue(id=one, type=discord.SelectDefaultValueType.user)
                for one in draft.user_ids[:SELECT_MAX]
            ],
        )
        self.draft = draft

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        self.draft.user_ids = [int(one.id) for one in self.values]
        await render_card(interaction, self.draft, self.view)


class WherePick(discord.ui.ChannelSelect):
    def __init__(self, bot: Any, guild: Any, draft: Draft) -> None:
        defaults = (
            [
                discord.SelectDefaultValue(
                    id=draft.channel_id, type=discord.SelectDefaultValueType.channel
                )
            ]
            if draft.channel_id
            else []
        )
        super().__init__(
            placeholder=said(bot, guild, "ninja_where_placeholder")[:PLACEHOLDER_LIMIT],
            channel_types=[
                discord.ChannelType.text,
                discord.ChannelType.news,
                discord.ChannelType.public_thread,
            ],
            min_values=1,
            max_values=1,
            row=1,
            default_values=defaults,
        )
        self.draft = draft

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        self.draft.channel_id = int(self.values[0].id)
        await render_card(interaction, self.draft, self.view)


class EndPick(discord.ui.Select):
    def __init__(self, bot: Any, guild: Any, rows: list[Any]) -> None:
        options = []
        for place, row in enumerate(rows[:SELECT_MAX], start=1):
            member = guild.get_member(int(row["user_id"]))
            channel = guild.get_channel(int(row["channel_id"]))
            name = getattr(member, "display_name", None) or row["user_id"]
            where = getattr(channel, "name", None) or row["channel_id"]
            options.append(
                discord.SelectOption(
                    label=option_label(place, None, f"{name} · #{where}"), value=str(row["id"])
                )
            )
        super().__init__(
            placeholder=said(bot, guild, "ninja_end_placeholder")[:PLACEHOLDER_LIMIT],
            options=options,
            min_values=1,
            max_values=1,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        bot, guild = interaction.client, interaction.guild
        row = await store.get(bot.db, guild.id, int(self.values[0]))
        if row is None or row["ended_at"] is not None:
            await render_root(interaction, self.view)
            await answer(interaction, said(bot, guild, "ninja_not_active_said"))
            return
        await ask_end(interaction, row, self.view)


class LimitsModal(AnswersErrors, discord.ui.Modal):
    def __init__(self, bot: Any, guild: Any, draft: Draft, previous: Any = None) -> None:
        super().__init__(title=said(bot, guild, "ninja_modal_title")[:TITLE_LIMIT])
        self.draft = draft
        self.previous = previous
        posts, minutes = rules.default_limits(bot.store, guild.id)
        blank = said(bot, guild, "ninja_no_limit_placeholder")[:HINT_LIMIT]
        self.posts = discord.ui.TextInput(
            label=said(bot, guild, "ninja_posts_field")[:TITLE_LIMIT],
            required=False,
            max_length=NUMBER_CHARS,
            placeholder=blank,
            default=posts or None,
        )
        self.minutes = discord.ui.TextInput(
            label=said(bot, guild, "ninja_minutes_field")[:TITLE_LIMIT],
            required=False,
            max_length=NUMBER_CHARS,
            placeholder=blank,
            default=minutes or None,
        )
        self.add_item(self.posts)
        self.add_item(self.minutes)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        outcome = await rules.mark(
            interaction.client,
            interaction.guild,
            interaction.user,
            self.draft.user_ids,
            self.draft.channel_id,
            str(self.posts),
            str(self.minutes),
        )
        if not outcome.ok and outcome.code in rules.KEEP_THE_CARD:
            await render_card(interaction, self.draft, self.previous)
        else:
            await render_root(interaction, self.previous)
        await answer(interaction, outcome.message)
