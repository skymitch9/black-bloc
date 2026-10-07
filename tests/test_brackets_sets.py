# ruff: noqa: F401, F811
from __future__ import annotations

from datetime import datetime, timedelta

from black_bloc import brackets_people as people
from black_bloc import brackets_sets as sets
from tests.test_brackets_moves import (
    ADA,
    BEA,
    CY,
    GUILD,
    STAFF,
    TO,
    bot,
    entrant_id,
    guild,
    made,
    moves,
    rows,
    signed_up,
    started,
    the_set,
    who,
)


async def test_a_player_reports_and_the_opponent_confirms_and_nobody_else_may(bot, guild):
    tid = await started(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    stranger = await sets.report(bot, guild, who(guild, CY), tid, "W1-1", 2, 0)
    assert (stranger.code, stranger.status) == ("not_in_set", 403)
    reported = await sets.report(bot, guild, who(guild, ADA), tid, "W1-1", 2, 1)
    assert reported.message == (
        "W1-1 reported 2–1. It stands in 12 minute(s) unless Bea disputes it."
    )
    own = await sets.confirm(bot, guild, who(guild, ADA), tid, "W1-1")
    assert own.code == "own_report"
    final = await sets.confirm(bot, guild, who(guild, BEA), tid, "W1-1")
    assert final.message == "W1-1 is final: Ada wins 2–1."
    match = await the_set(bot, tid, "W1-1")
    assert (match.state, match.confirmed_how, match.confirmed_by) == ("complete", "opponent", BEA)
    assert [kind for kind, *_ in await rows(bot.db)][-2:] == [
        "brackets.set_reported",
        "brackets.set_confirmed",
    ]


async def test_a_score_that_does_not_fit_and_a_set_that_is_not_ready_are_refused(bot, guild):
    tid = await started(bot, guild, ADA, BEA, CY, STAFF, format="single")
    bad = await sets.report(bot, guild, who(guild, ADA), tid, "W1-1", 3, 0)
    assert (bad.code, bad.status, bad.message) == (
        "bad_score",
        400,
        "That score does not finish a best of 3: the winner has 2 game(s) and the loser fewer.",
    )
    waiting = await sets.report(bot, guild, who(guild, TO), tid, "W2-1", 2, 0)
    assert (waiting.code, waiting.message) == (
        "not_ready",
        "W2-1 is waiting for a player, so it cannot be played yet.",
    )
    missing = await sets.report(bot, guild, who(guild, TO), tid, "W9-9", 2, 0)
    assert (missing.code, missing.status) == ("no_set", 404)


async def test_a_to_report_is_final_at_once_and_reports_for_a_guest(bot, guild):
    tid = await signed_up(bot, guild, ADA, format="single", best_of_finals=3)
    await people.add_entrant(bot, guild, who(guild, TO), tid, name="Remy")
    await moves.start(bot, guild, who(guild, TO), tid)
    outcome = await sets.report(bot, guild, who(guild, TO), tid, "W1-1", 0, 2)
    assert outcome.message == "W1-1 is final: Remy wins 2–0."
    match = await the_set(bot, tid, "W1-1")
    assert (match.state, match.confirmed_how) == ("complete", "to")
    assert (await rows(bot.db))[-1][0] == "brackets.set_overridden"


async def test_a_dispute_goes_to_the_to_who_decides_it(bot, guild):
    tid = await started(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    await sets.report(bot, guild, who(guild, ADA), tid, "W1-1", 2, 0)
    disputed = await sets.dispute(bot, guild, who(guild, BEA), tid, "W1-1", "  wrong   stage ")
    assert disputed.message == "W1-1 is disputed; a tournament organiser decides it."
    assert (await the_set(bot, tid, "W1-1")).dispute_note == "wrong stage"
    to = await sets.dispute(bot, guild, who(guild, TO), tid, "W1-1", "x")
    assert to.code == "not_in_set"
    decided = await sets.override(bot, guild, who(guild, TO), tid, "W1-1", score_a=1, score_b=2)
    assert decided.message == "W1-1 is final: Bea wins 2–1."


async def test_a_forfeit_override_and_a_reset_that_clears_what_it_decided(bot, guild):
    tid = await started(bot, guild, ADA, BEA, CY, STAFF, format="single")
    ada = await entrant_id(bot, tid, ADA)
    first = await the_set(bot, tid, "W1-1")
    assert ada in (first.slot_a, first.slot_b)
    outcome = await sets.override(bot, guild, who(guild, TO), tid, "W1-1", winner=ada, forfeit=True)
    assert outcome.message == "W1-1 is final: Ada wins by forfeit."
    assert (await the_set(bot, tid, "W2-1")).slot_a == ada
    reset = await sets.reset(bot, guild, who(guild, TO), tid, "W1-1")
    assert reset.message == "W1-1 is open again; every set it decided after it is cleared."
    assert (await the_set(bot, tid, "W2-1")).slot_a is None
    member = await sets.reset(bot, guild, who(guild, ADA), tid, "W1-1")
    assert member.code == "not_organiser"


async def test_an_unanswered_report_stands_after_the_confirm_time(bot, guild):
    tid = await started(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    await sets.report(bot, guild, who(guild, BEA), tid, "W1-1", 0, 2)
    reported = datetime.fromisoformat((await the_set(bot, tid, "W1-1")).reported_at)
    assert await sets.confirm_due(bot, guild, reported + timedelta(minutes=11)) == []
    assert await sets.confirm_due(bot, guild, reported + timedelta(minutes=12)) == [(tid, "W1-1")]
    match = await the_set(bot, tid, "W1-1")
    assert (match.state, match.confirmed_how, match.winner) == (
        "complete",
        "time",
        await entrant_id(bot, tid, BEA),
    )
    kind, actor, _, details = (await rows(bot.db))[-1]
    assert (kind, actor, details["how"], details["set"]) == (
        "brackets.set_confirmed",
        None,
        "time",
        "W1-1",
    )
