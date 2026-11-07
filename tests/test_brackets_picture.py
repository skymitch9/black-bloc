# ruff: noqa: F401, F811
from __future__ import annotations

from black_bloc import brackets_moves as moves
from black_bloc import brackets_people as people
from black_bloc import brackets_picture as picture_
from black_bloc import brackets_sets as sets
from black_bloc import brackets_store as store_
from tests.test_brackets_moves import ADA, BEA, CY, GUILD, TO, who
from tests.test_brackets_thread import (
    bot,
    created,
    guild,
    listed_running,
    moved,
    row_of,
    running,
)


async def row_people(bot, tid):
    return await row_of(bot, tid), await store_.entrants(bot.db, tid)


async def test_before_the_start_the_preview_is_what_start_would_build(bot, guild):
    tid = await created(bot, guild, format="single")
    await moved(bot, guild, tid, moves.open_signups)
    await moved(bot, guild, tid, people.join, actor=ADA)
    row, entrants = await row_people(bot, tid)
    assert picture_.preview(row, entrants) is None

    await moved(bot, guild, tid, people.join, actor=BEA)
    row, entrants = await row_people(bot, tid)
    found = await picture_.bracket_of(bot, row, entrants)
    assert {found.matches["W1-1"].slot_a, found.matches["W1-1"].slot_b} == {
        one["id"] for one in entrants
    }
    assert await store_.bracket(bot.db, row) is None


async def test_the_words_carry_the_kind_state_rounds_and_the_champion(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    await moved(bot, guild, tid, sets.override, "W1-1", score_a=2, score_b=0)
    await moved(bot, guild, tid, moves.complete)
    row, entrants = await row_people(bot, tid)
    bracket = await store_.bracket(bot.db, row)

    words = picture_.words_of(bot.store, GUILD, row, entrants, bracket)

    assert words.kind == "Fighting game"
    assert words.format == "Single elimination"
    assert words.rounds["W1-1"] == "Winners round 1"
    assert words.heads == ("#", "Name", "W-L", "Pts")
    assert words.champion.startswith("Champion: ")


async def test_open_votes_are_counted_only_while_they_are_shown(bot, guild):
    tid = await listed_running(bot, guild, "Snickers", "Twix")
    row, _ = await row_people(bot, tid)
    bracket = await store_.bracket(bot.db, row)
    extras = await picture_.extras_of(bot, GUILD, row, bracket)
    assert extras["W1-1"].votes == (0, 0)

    await bot.store.set(GUILD, "brackets_votes_visible", False)
    assert await picture_.extras_of(bot, GUILD, row, bracket) == {}


async def test_the_standings_head_splits_on_the_bar(bot, guild):
    await bot.store.set(GUILD, "brackets_picture_standings_head", "Rank | Who | Rec | Points")
    tid = await running(bot, guild, ADA, BEA, CY, format="round_robin")
    row, entrants = await row_people(bot, tid)
    bracket = await store_.bracket(bot.db, row)
    words = picture_.words_of(bot.store, GUILD, row, entrants, bracket)
    assert words.heads == ("Rank", "Who", "Rec", "Points")
