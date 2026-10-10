"""The /pb panel's face: the leaderboard, the next place up, Submit a run, the feed."""

from __future__ import annotations

import math
from typing import Any

import discord

from . import pb_panel, points_tickets, points_view
from . import points_moves as moves
from .brackets.access import is_staff
from .command_errors import AnswersErrors
from .panels import Panel, clamped, db_up, opened, retire
from .points.model import BY_POINTS, BY_XP
from .settings_store import PB_FEED_PANEL_MINUTES

PAGE_SIZE = 25
LABEL_LIMIT = 45
BUTTON_LIMIT = 80
HINT_LIMIT = 100
PENDING_LABEL = "Pending ({count})"
PENDING_TITLE = "Runs waiting for a decision"
PENDING_NONE = "Nothing is waiting."
BOARD = "board"
FULL = "full"
PENDING = "pending"
SUBMIT = "submit"
NEXT = "next"
FEED = "feed"
PREVIOUS = "previous"
NEXT_PAGE = "next_page"
SETTINGS = "settings"
SETTINGS_LABEL = "Settings…"


def words(bot: Any, guild: Any, key: str, **fields: Any) -> str:
    return moves.said(bot.store, guild.id, key, **fields)


class BoardPanel(Panel):
    def __init__(
        self, bot: Any, guild: Any, *, by: str, surface: str = BOARD, page: int = 0
    ) -> None:
        super().__init__(
            int(bot.store.get(guild.id, PB_FEED_PANEL_MINUTES)),
            footer=words(bot, guild, "points_panel_footer"),
            again=self.shown_again,
        )
        self.by = by
        self.surface = surface
        self.page = page

    async def shown_again(self, interaction: discord.Interaction, previous: Any) -> None:
        if self.surface == FULL:
            await render_full(interaction, previous, page=self.page)
            return
        if self.surface == PENDING:
            await render_pending(interaction, previous)
            return
        if self.surface == SETTINGS:
            from .points_board_panel import render_settings

            await render_settings(interaction, previous)
            return
        await render_board(interaction, previous)


def by_of(previous: Any) -> str | None:
    return getattr(previous, "by", None)


def lines_of(store: Any, guild_id: int, rows: list[dict[str, Any]]) -> list[str]:
    return [
        moves.said(
            store,
            guild_id,
            "points_board_line",
            place=row["place"],
            name=row["shown"],
            runs=row["runs"],
            xp=row["xp"],
            points=row["speedpoints"],
        )
        for row in rows
    ]


def board_lines(bot: Any, guild: Any, rows: list[dict[str, Any]]) -> list[str]:
    shown = [row | {"shown": moves.name_of(guild, row["user_id"])} for row in rows]
    return lines_of(bot.store, guild.id, shown)


def heading_of(store: Any, guild_id: int, by: str) -> str:
    key = "points_board_xp_title" if by == BY_XP else "points_board_title"
    return moves.said(store, guild_id, key)


def title_of(bot: Any, guild: Any, by: str) -> str:
    return heading_of(bot.store, guild.id, by)


async def build_board(
    bot: Any, guild: Any, member: Any, *, by: Any = None, note: str = ""
) -> tuple[discord.Embed, BoardPanel]:
    verifier = moves.may_verify(bot.store, guild, member)
    found = await points_view.index(
        bot, guild, member.id, by=by, verifier=verifier, staff=is_staff(bot.store, member)
    )
    order = found["by"]
    lines = board_lines(bot, guild, found["board"]) or [words(bot, guild, "points_board_empty")]
    embed = discord.Embed(
        title=title_of(bot, guild, order),
        description=clamped([note, ""] + lines if note else lines),
    )
    bounties = [row["line"] for row in found["bounties"] if row["live"]]
    embed.add_field(
        name=words(bot, guild, "points_bounties_heading")[:256],
        value=clamped(bounties or [words(bot, guild, "points_bounty_none")])[:1024],
        inline=False,
    )
    view = BoardPanel(bot, guild, by=order)
    switch = BY_XP if order == BY_POINTS else BY_POINTS
    switch_key = "points_xp_label" if switch == BY_XP else "points_points_label"
    view.add_item(Move(words(bot, guild, switch_key), switch, row=0))
    view.add_item(Move(words(bot, guild, "points_full_board_label"), FULL, row=0))
    view.add_item(Move(words(bot, guild, "points_next_rank_label"), NEXT, row=0))
    if found["mode"] != moves.OFF:
        view.add_item(Move(words(bot, guild, "points_submit_label"), SUBMIT, row=0, primary=True))
    view.add_item(Move(words(bot, guild, "points_feed_label"), FEED, row=1))
    if verifier:
        waiting = await points_tickets.pending(bot, guild)
        if waiting:
            view.add_item(Move(PENDING_LABEL.format(count=len(waiting)), PENDING, row=1))
    if found["staff"]:
        view.add_item(Move(SETTINGS_LABEL, SETTINGS, row=1))
    return (embed, view)


async def build_full(
    bot: Any, guild: Any, *, by: Any = None, page: int = 0
) -> tuple[discord.Embed, BoardPanel]:
    found = await points_view.full_board(bot, guild, by=by)
    rows = found["rows"]
    pages = max(1, math.ceil(len(rows) / PAGE_SIZE))
    page = min(max(0, int(page)), pages - 1)
    shown = rows[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
    lines = board_lines(bot, guild, shown) or [words(bot, guild, "points_board_empty")]
    embed = discord.Embed(title=title_of(bot, guild, found["by"]), description=clamped(lines))
    embed.set_footer(text=words(bot, guild, "points_page_words", page=page + 1, pages=pages))
    view = BoardPanel(bot, guild, by=found["by"], surface=FULL, page=page)
    if page > 0:
        view.add_item(Move(words(bot, guild, "points_previous_label"), PREVIOUS, row=0))
    if page < pages - 1:
        view.add_item(Move(words(bot, guild, "points_next_label"), NEXT_PAGE, row=0))
    view.add_item(Move(words(bot, guild, "points_back_label"), BOARD, row=0))
    return (embed, view)


async def build_pending(
    bot: Any, guild: Any, *, by: Any = None
) -> tuple[discord.Embed, BoardPanel]:
    waiting = await points_tickets.pending(bot, guild)
    lines = [points_tickets.pending_line(guild, ticket, row) for ticket, row in waiting]
    embed = discord.Embed(title=PENDING_TITLE, description=clamped(lines or [PENDING_NONE]))
    view = BoardPanel(bot, guild, by=by or BY_POINTS, surface=PENDING)
    view.add_item(Move(words(bot, guild, "points_back_label"), BOARD, row=0))
    return (embed, view)


async def show(interaction: discord.Interaction, built: Any, previous: Any) -> None:
    embed, view = built
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def render_board(
    interaction: discord.Interaction, previous: Any = None, *, by: Any = None, note: str = ""
) -> None:
    built = await build_board(
        interaction.client,
        interaction.guild,
        interaction.user,
        by=by or by_of(previous),
        note=note,
    )
    await show(interaction, built, previous)


async def render_full(
    interaction: discord.Interaction, previous: Any = None, *, page: int = 0
) -> None:
    built = await build_full(interaction.client, interaction.guild, by=by_of(previous), page=page)
    await show(interaction, built, previous)


async def render_pending(interaction: discord.Interaction, previous: Any = None) -> None:
    if not moves.may_verify(interaction.client.store, interaction.guild, interaction.user):
        await render_board(interaction, previous)
        return
    built = await build_pending(interaction.client, interaction.guild, by=by_of(previous))
    await show(interaction, built, previous)


async def next_rank(interaction: discord.Interaction, previous: Any) -> None:
    found = await points_view.next_rank_of(
        interaction.client, interaction.guild, interaction.user.id
    )
    await render_board(interaction, previous, note=found["line"])


async def submitted(interaction: discord.Interaction, given: dict[str, Any], previous: Any) -> None:
    if not await opened(interaction, staff=False):
        return
    outcome = await points_tickets.submit(
        interaction.client, interaction.guild, interaction.user, given
    )
    await render_board(interaction, previous, note=outcome.message)


class Move(discord.ui.Button):
    def __init__(self, label: str, action: str, *, row: int, primary: bool = False) -> None:
        style = discord.ButtonStyle.primary if primary else discord.ButtonStyle.secondary
        super().__init__(label=label[:BUTTON_LIMIT], style=style, row=row)
        self.action = action

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if self.action == SUBMIT:
            if not await db_up(interaction):
                return
            await interaction.response.send_modal(
                SubmitModal(interaction.client, interaction.guild, view)
            )
            return
        if self.action == SETTINGS:
            from .points_board_panel import open_settings

            await open_settings(interaction, view)
            return
        if not await opened(interaction, staff=False):
            return
        if self.action in (BY_POINTS, BY_XP):
            await render_board(interaction, view, by=self.action)
        elif self.action == FULL:
            await render_full(interaction, view)
        elif self.action in (PREVIOUS, NEXT_PAGE):
            step = -1 if self.action == PREVIOUS else 1
            await render_full(interaction, view, page=getattr(view, "page", 0) + step)
        elif self.action == NEXT:
            await next_rank(interaction, view)
        elif self.action == PENDING:
            await render_pending(interaction, view)
        elif self.action == FEED:
            await pb_panel.render_own(interaction, view, home=True)
        else:
            await render_board(interaction, view)


class SubmitModal(AnswersErrors, discord.ui.Modal):
    """Five fields, Discord's most: the presser is the player."""

    def __init__(self, bot: Any, guild: Any, previous: Any = None) -> None:
        super().__init__(title=words(bot, guild, "points_submit_title")[:LABEL_LIMIT])
        self.previous = previous

        def field(key: str, limit: int, *, required: bool = True, hint: str = "") -> Any:
            found = discord.ui.TextInput(
                max_length=limit,
                required=required,
                placeholder=words(bot, guild, hint)[:HINT_LIMIT] if hint else None,
            )
            self.add_item(
                discord.ui.Label(text=words(bot, guild, key)[:LABEL_LIMIT], component=found)
            )
            return found

        self.game = field("points_game_label", moves.GAME_LIMIT)
        self.category = field("points_category_label", moves.CATEGORY_LIMIT, required=False)
        self.time = field("points_time_label", 40, hint="points_time_hint")
        self.proof = field("points_proof_label", moves.PROOF_LIMIT, hint="points_proof_hint")
        self.note = field("points_note_label", moves.NOTE_LIMIT, required=False)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        given = {
            "game": str(self.game),
            "category": str(self.category),
            "time": str(self.time),
            "proof_url": str(self.proof),
            "note": str(self.note),
        }
        await submitted(interaction, given, self.previous)


async def open_panel(interaction: discord.Interaction) -> None:
    if not await db_up(interaction):
        return
    embed, view = await build_board(interaction.client, interaction.guild, interaction.user)
    await interaction.response.send_message(
        embed=embed, view=view, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )
    view.message = await interaction.original_response()


__all__ = [
    "BoardPanel",
    "Move",
    "SubmitModal",
    "build_board",
    "build_full",
    "build_pending",
    "open_panel",
    "render_board",
]
