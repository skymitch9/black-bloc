"""The My picks panel: the lock, a member's points and rank, the site link, and quick picks."""

from __future__ import annotations

from typing import Any

import discord

from . import brackets_cards as cards
from . import brackets_picks as picks_
from . import brackets_store as store_
from . import brackets_thread as thread_
from .brackets import picks
from .brackets_moves import said
from .panels import Outcome, Panel, answer, db_up, opened
from .settings_store import BRACKETS_PANEL_MINUTES

OPTIONS_LIMIT = 25
OPTION_TEXT = 100
LABEL_LIMIT = 80
PICKS_PATH = "/picks"


def words(bot: Any, guild: Any, key: str, **fields: Any) -> str:
    return said(bot.store, guild.id, key, **fields)


def text(value: Any, limit: int = OPTION_TEXT) -> str:
    return str(value or "")[:limit] or "—"


def chunks(items: list[Any], size: int = OPTIONS_LIMIT) -> list[list[Any]]:
    """Even pieces of at most `size`: 32 games are two lists of 16, not 25 and 7."""
    if not items:
        return []
    count = -(-len(items) // size)
    step = -(-len(items) // count)
    return [items[at : at + step] for at in range(0, len(items), step)]


class PicksPanel(Panel):
    def __init__(self, bot: Any, guild: Any, tournament_id: int, round_: int | None) -> None:
        super().__init__(
            int(bot.store.get(guild.id, BRACKETS_PANEL_MINUTES)),
            footer=said(bot.store, guild.id, "brackets_panel_footer"),
            again=self.shown_again,
        )
        self.tournament_id = int(tournament_id)
        self.round = round_

    async def shown_again(self, interaction: discord.Interaction, previous: Any) -> None:
        await render(interaction, self.tournament_id, self.round, previous)


def pickable(found: picks_.Sheets, user: int) -> dict[int, list[tuple[str, tuple]]]:
    """Per round, each game whose two predicted teams are both known."""
    slots, _ = picks.predicted(found.tree, found.mine(user))
    rounds: dict[int, list[tuple[str, tuple]]] = {}
    for node in found.tree.ordered():
        pair = slots[node.key]
        if node.fixed is None and None not in pair:
            rounds.setdefault(node.round, []).append((node.key, pair))
    return rounds


def round_label(bot: Any, guild: Any, found: picks_.Sheets, key: str) -> str:
    match = found.bracket.matches.get(key) if found.bracket is not None else None
    return text(cards.round_words(bot.store, guild.id, match) if match is not None else key)


def lines(bot: Any, guild: Any, found: picks_.Sheets, user: int) -> list[str]:
    mine = found.mine(user)
    if not found.locked:
        when = cards.when_words(store_.column(found.row, "picks_lock_at")) or "—"
        total = sum(1 for one in found.tree.nodes.values() if one.fixed is None)
        return [
            words(
                bot, guild, "brackets_my_picks_open_line", count=len(mine), total=total, when=when
            )
        ]
    held = found.sheets.get(user)
    if held is None or not mine:
        return [words(bot, guild, "brackets_picks_locked_line", count=found.count())]
    return [
        words(
            bot,
            guild,
            "brackets_my_picks_line",
            points=int(held["points"] or 0),
            rank=held["rank"] or "–",
            sheets=found.count(),
        )
    ]


async def built(
    bot: Any, guild: Any, user: Any, tournament_id: int, round_: int | None, note: str = ""
) -> tuple[discord.Embed | None, PicksPanel | None, str]:
    row = await store_.tournament(bot.db, guild.id, int(tournament_id))
    if row is None:
        return None, None, words(bot, guild, "brackets_no_tournament_said", id=tournament_id)
    if not store_.picks_on(row):
        return None, None, words(bot, guild, "brackets_picks_off_said", name=row["name"])
    found = await picks_.read(bot, row)
    me = int(user.id)
    body = "\n".join([*([note] if note else []), *lines(bot, guild, found, me)])
    embed = discord.Embed(title=text(row["name"], 256), description=body[:4000])
    view = PicksPanel(bot, guild, row["id"], round_)
    if not found.locked:
        rounds = pickable(found, me)
        if rounds:
            wanted = round_ if round_ in rounds else min(rounds)
            view.round = wanted
            view.add_item(RoundPick(bot, guild, found, rounds, wanted))
            people = {one["id"]: one["name"] for one in await store_.entrants(bot.db, row["id"])}
            mine = found.mine(me)
            for at, piece in enumerate(chunks(rounds[wanted])[:2]):
                view.add_item(GamePick(bot, guild, row["id"], piece, people, mine, at + 1))
    url = cards.site_url(thread_.origin_of(bot), row["id"])
    if url:
        view.add_item(
            discord.ui.Button(
                label=text(words(bot, guild, "brackets_picks_link_label"), LABEL_LIMIT),
                style=discord.ButtonStyle.link,
                url=f"{url}{PICKS_PATH}",
                row=4,
            )
        )
    return embed, view, ""


async def open_picks(interaction: discord.Interaction, tournament_id: int) -> None:
    if not await db_up(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    embed, view, refused = await built(bot, guild, interaction.user, tournament_id, None)
    if view is None:
        await answer(interaction, refused)
        return
    await interaction.response.send_message(
        embed=embed, view=view, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )
    view.message = await interaction.original_response()


async def render(
    interaction: discord.Interaction,
    tournament_id: int,
    round_: int | None,
    previous: Any,
    note: str = "",
) -> None:
    bot, guild = interaction.client, interaction.guild
    embed, view, refused = await built(bot, guild, interaction.user, tournament_id, round_, note)
    if view is None:
        await answer(interaction, refused)
        return
    if previous is not None:
        previous.replaced = True
        previous.stop()
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


class RoundPick(discord.ui.Select):
    def __init__(
        self, bot: Any, guild: Any, found: picks_.Sheets, rounds: dict, wanted: int
    ) -> None:
        options = [
            discord.SelectOption(
                label=round_label(bot, guild, found, games[0][0]),
                value=str(number),
                default=number == wanted,
            )
            for number, games in sorted(rounds.items())[:OPTIONS_LIMIT]
        ]
        super().__init__(
            placeholder=text(words(bot, guild, "brackets_pick_round_placeholder"), 150),
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction, staff=False):
            return
        view = self.view
        await render(interaction, view.tournament_id, int(self.values[0]), view)


class GamePick(discord.ui.Select):
    """A game of the round: picking it offers its two teams as buttons."""

    def __init__(
        self,
        bot: Any,
        guild: Any,
        tournament_id: int,
        games: list[tuple[str, tuple]],
        people: dict[int, str],
        mine: dict[str, int],
        row: int,
    ) -> None:
        options = []
        for key, (a, b) in games:
            picked = mine.get(key)
            about = (
                words(bot, guild, "brackets_your_pick_words", name=people.get(picked, picked))
                if picked is not None
                else None
            )
            options.append(
                discord.SelectOption(
                    label=text(f"{people.get(a, a)} v {people.get(b, b)}"),
                    value=key,
                    description=text(about) if about else None,
                )
            )
        super().__init__(
            placeholder=text(words(bot, guild, "brackets_pick_game_placeholder"), 150),
            options=options,
            row=row,
        )
        self.tournament_id = int(tournament_id)
        self.games = dict(games)
        self.people = people

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction, staff=False):
            return
        key = self.values[0]
        view = self.view
        for item in [one for one in view.children if isinstance(one, WinnerButton)]:
            view.remove_item(item)
        for entrant in self.games[key]:
            view.add_item(
                WinnerButton(self.tournament_id, key, entrant, self.people.get(entrant, entrant))
            )
        await interaction.edit_original_response(view=view)


class WinnerButton(discord.ui.Button):
    def __init__(self, tournament_id: int, key: str, entrant: int, name: Any) -> None:
        super().__init__(label=text(name, LABEL_LIMIT), style=discord.ButtonStyle.primary, row=3)
        self.tournament_id = int(tournament_id)
        self.key = key
        self.entrant = int(entrant)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction, staff=False):
            return
        bot, guild = interaction.client, interaction.guild
        outcome = await picks_.quick_pick(
            bot, guild, interaction.user, self.tournament_id, self.key, self.entrant
        )
        view = self.view
        await render(interaction, self.tournament_id, view.round, view, note=outcome.message)
        if outcome.ok and outcome.changed:
            await thread_.follow(bot, guild, self.tournament_id, Outcome(True, "", value=None))


__all__ = ["PicksPanel", "chunks", "open_picks", "pickable"]
