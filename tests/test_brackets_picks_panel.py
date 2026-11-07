# ruff: noqa: F401, F811
from __future__ import annotations

from black_bloc import brackets_picks as picks_
from black_bloc import brackets_picks_panel as panel
from black_bloc import brackets_store as store_
from black_bloc.brackets_picks_panel import GamePick, RoundPick
from tests.test_brackets_moves import ADA, GUILD, TO, bot, guild, who
from tests.test_brackets_picks import ids, made, row_of, sheet


def test_a_round_of_32_games_is_two_lists_of_16():
    assert [len(one) for one in panel.chunks(list(range(32)))] == [16, 16]
    assert [len(one) for one in panel.chunks(list(range(25)))] == [25]
    assert [len(one) for one in panel.chunks(list(range(3)))] == [3]
    assert panel.chunks([]) == []


async def test_the_panel_offers_each_round_whose_teams_are_known(bot, guild):
    tid = await made(bot, guild)
    embed, view, refused = await panel.built(bot, guild, who(guild, ADA), tid, None)
    assert refused == ""
    assert embed.description == "0 of 3 picked · locks —"
    rounds = [one for one in view.children if isinstance(one, RoundPick)]
    games = [one for one in view.children if isinstance(one, GamePick)]
    assert [option.value for option in rounds[0].options] == ["1"]
    assert [option.value for option in games[0].options] == ["W1-1", "W1-2"]
    await sheet(bot, guild, ADA, tid, **{"W1-1": "Ants", "W1-2": "Cats"})
    embed, view, _ = await panel.built(bot, guild, who(guild, ADA), tid, 2)
    games = [one for one in view.children if isinstance(one, GamePick)]
    assert [option.label for option in games[0].options] == ["Ants v Cats"]
    assert embed.description.startswith("2 of 3 picked")


async def test_after_the_lock_the_panel_shows_points_and_rank_and_no_picking(bot, guild):
    tid = await made(bot, guild)
    await sheet(bot, guild, ADA, tid, **{"W1-1": "Ants"})
    await store_.update(
        bot.db, tid, {"picks_locked_at": "2026-01-01T00:00:00+00:00"}
    )
    embed, view, _ = await panel.built(bot, guild, who(guild, ADA), tid, None)
    assert embed.description == "0 point(s) · rank 1 of 1"
    assert not [one for one in view.children if isinstance(one, (RoundPick, GamePick))]


async def test_a_bracket_with_no_sheets_is_refused_in_words(bot, guild):
    from black_bloc import brackets_moves as moves

    tid = (await moves.create(bot, guild, who(guild, TO), {"name": "Knuck Up"})).value
    embed, view, refused = await panel.built(bot, guild, who(guild, ADA), tid, None)
    assert (embed, view, refused) == (None, None, "**Knuck Up** has no pick sheets.")
