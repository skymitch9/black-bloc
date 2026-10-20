from __future__ import annotations

from typing import Any

import discord

from . import baf_runs as runs
from . import marathon as mt
from .command_errors import AnswersErrors
from .panels import Panel, opened, retire, still_staff
from .settings_store import (
    RUNS_DEFAULTS,
    RUNS_LOOKUP_COUNT,
    RUNS_LOOKUP_LINE,
    RUNS_LOOKUP_MORE,
    RUNS_LOOKUP_NO_DATE,
    RUNS_LOOKUP_NONE,
    RUNS_LOOKUP_SEEN,
    RUNS_LOOKUP_TAGS,
    RUNS_LOOKUP_TITLE,
)

PANEL_TITLE = "BaF runs"
PANEL_MINUTES = 10
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /runs again"
SEARCH_LABEL = "Search…"
AGAIN_LABEL = "Search again"
SITE_LABEL = "Open on the site"
MODAL_TITLE = "Search BaF runs"
FIELD_LABEL = "Game"
FIELD_HINT = "Shredder's Revenge"
FIELD_NAME_LIMIT = 256
FIELD_VALUE_LIMIT = 1024
QUERY_LIMIT = 100
TAG_JOIN = " · "


def worded(bot: Any, guild_id: int, key: str, **fields: Any) -> str:
    return mt.render(bot.store.get(guild_id, key), RUNS_DEFAULTS[key], **fields).text


def date_word(bot: Any, guild_id: int, value: Any) -> str:
    stamp = mt.stamp_of(value, "d") if value else "—"
    return worded(bot, guild_id, RUNS_LOOKUP_NO_DATE) if stamp == "—" else stamp


def tag_fields(game: dict[str, Any]) -> dict[str, str]:
    series = game.get(runs.SERIES) or ""
    genre = game.get(runs.GENRE) or ""
    developer = game.get(runs.DEVELOPER) or ""
    return {
        "series": series,
        "genre": genre,
        "developer": developer,
        "tags": TAG_JOIN.join(filter(None, (series, genre, developer))),
    }


def game_field(bot: Any, guild_id: int, game: dict[str, Any]) -> tuple[str, str]:
    tags = tag_fields(game)
    name = worded(bot, guild_id, RUNS_LOOKUP_TITLE, game=game["game"], **tags)[:FIELD_NAME_LIMIT]
    tag_line = worded(bot, guild_id, RUNS_LOOKUP_TAGS, **tags).strip() if tags["tags"] else ""
    lines = [tag_line] if tag_line else []
    lines.append(
        worded(
            bot,
            guild_id,
            RUNS_LOOKUP_SEEN,
            n=game["times"],
            date=date_word(bot, guild_id, game["last_date"]),
            event=game["last_event"] or "—",
            **tags,
        )
    )
    for run in game["runs"]:
        lines.append(
            worded(
                bot,
                guild_id,
                RUNS_LOOKUP_LINE,
                date=date_word(bot, guild_id, run["date"]),
                event=run["event"] or "—",
                category=run["category"] or "—",
                runners=run["runners_text"] or "—",
            )
        )
    if game["more"]:
        lines.append(worded(bot, guild_id, RUNS_LOOKUP_MORE, more=game["more"]))
    kept: list[str] = []
    spent = 0
    for line in lines:
        if spent + len(line) + 1 > FIELD_VALUE_LIMIT:
            break
        kept.append(line)
        spent += len(line) + 1
    return (name or game["game"][:FIELD_NAME_LIMIT], "\n".join(kept) or "—")


def answer_embed(bot: Any, guild_id: int, query: str, found: runs.Found) -> Any:
    embed = discord.Embed(title=PANEL_TITLE)
    if not found.games:
        near = TAG_JOIN.join(found.suggestions)
        said = worded(bot, guild_id, RUNS_LOOKUP_NONE, query=query, suggestions=near)
        embed.description = said.strip()[:4000]
        return embed
    for game in found.games:
        name, value = game_field(bot, guild_id, game)
        embed.add_field(name=name, value=value, inline=False)
    return embed


class RunsPanel(Panel):
    def __init__(self, bot: Any, query: str = "") -> None:
        super().__init__(PANEL_MINUTES, footer=PANEL_TIMEOUT_FOOTER, again=self.shown_again)
        self.query = query
        self.add_item(SearchButton(AGAIN_LABEL if query else SEARCH_LABEL))
        url = runs.page_url(getattr(getattr(bot, "settings", None), "origin", ""), query)
        if url:
            self.add_item(discord.ui.Button(label=SITE_LABEL, url=url))

    async def shown_again(self, interaction: discord.Interaction, previous: Any) -> None:
        if self.query:
            await show_answer(interaction, self.query, previous)
            return
        embed, view = await build_root(interaction.client, interaction.guild)
        retire(previous)
        view.message = await interaction.edit_original_response(embed=embed, view=view)


async def build_root(bot: Any, guild: Any) -> tuple[Any, RunsPanel]:
    every = await runs.view(bot, guild)
    shown = [row for row in every if not row["removed"]]
    embed = discord.Embed(
        title=PANEL_TITLE,
        description=worded(
            bot, guild.id, RUNS_LOOKUP_COUNT, runs=len(shown), games=len(runs.games(every))
        ),
    )
    return embed, RunsPanel(bot)


async def show_answer(interaction: discord.Interaction, query: str, previous: Any) -> None:
    bot = interaction.client
    found = await runs.lookup(bot, interaction.guild, interaction.user, query)
    view = RunsPanel(bot, query)
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=answer_embed(bot, interaction.guild.id, query, found),
        view=view,
        allowed_mentions=discord.AllowedMentions.none(),
    )


class SearchButton(discord.ui.Button):
    def __init__(self, label: str) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.primary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.send_modal(
            SearchModal(previous=self.view, query=getattr(self.view, "query", ""))
        )


class SearchModal(AnswersErrors, discord.ui.Modal):
    typed = discord.ui.TextInput(label=FIELD_LABEL, placeholder=FIELD_HINT, max_length=QUERY_LIMIT)

    def __init__(self, previous: Any = None, query: str = "") -> None:
        super().__init__(title=MODAL_TITLE)
        self.previous = previous
        self.typed.default = query[:QUERY_LIMIT] or None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        await show_answer(interaction, " ".join(str(self.typed).split()), self.previous)
