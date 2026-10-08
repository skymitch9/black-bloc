# ruff: noqa: F401, F811
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from black_bloc import brackets_people as people
from black_bloc import brackets_sets as sets
from black_bloc import brackets_store as store_
from black_bloc import brackets_view
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
    own = await sets.confirm_report(bot, guild, who(guild, ADA), tid, "W1-1")
    assert own.code == "own_report"
    final = await sets.confirm_report(bot, guild, who(guild, BEA), tid, "W1-1")
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


async def test_after_complete_a_correction_says_to_reopen_first(bot, guild):
    tid = await started(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    await sets.report(bot, guild, who(guild, TO), tid, "W1-1", 2, 0)
    assert (await moves.complete(bot, guild, who(guild, TO), tid)).ok
    expected = "**Knuck Up 12** is complete. Reopen it first, then change W1-1."
    for outcome in (
        await sets.reset(bot, guild, who(guild, TO), tid, "W1-1"),
        await sets.override(bot, guild, who(guild, TO), tid, "W1-1", score_a=0, score_b=2),
    ):
        assert (outcome.ok, outcome.code, outcome.status) == (False, "reopen_first", 409)
        assert outcome.message == expected
    member = await sets.reset(bot, guild, who(guild, ADA), tid, "W1-1")
    assert member.code == "not_organiser"


async def test_two_different_reports_at_once_leave_one_and_refuse_the_other(bot, guild):
    tid = await started(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    first, second = await asyncio.gather(
        sets.report(bot, guild, who(guild, ADA), tid, "W1-1", 2, 0),
        sets.report(bot, guild, who(guild, BEA), tid, "W1-1", 0, 2),
    )
    assert (first.ok, second.ok) == (True, False)
    assert (second.code, second.status) == ("reported_differently", 409)
    assert second.message == "W1-1 was reported 2–0. Confirm that, or dispute it."
    match = await the_set(bot, tid, "W1-1")
    assert (match.state, match.score_a, match.score_b) == ("reported", 2, 0)
    assert [kind for kind, *_ in await rows(bot.db)][-1] == "brackets.set_reported"


async def test_a_second_report_that_differs_is_refused_and_the_same_one_confirms(bot, guild):
    tid = await started(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    assert (await sets.report(bot, guild, who(guild, BEA), tid, "W1-1", 1, 2)).ok
    differs = await sets.report(bot, guild, who(guild, ADA), tid, "W1-1", 2, 1)
    assert (differs.code, differs.message) == (
        "reported_differently",
        "W1-1 was reported 1–2. Confirm that, or dispute it.",
    )
    assert (await the_set(bot, tid, "W1-1")).state == "reported"
    same = await sets.report(bot, guild, who(guild, ADA), tid, "W1-1", 1, 2)
    assert same.message == "W1-1 is final: Bea wins 2–1."
    assert same.changed == ("W1-1",)


async def test_a_forced_swiss_rematch_shows_in_the_view_and_on_every_set_row(bot, guild):
    tid = await started(bot, guild, ADA, BEA, CY, STAFF, format="swiss", swiss_rounds=3)
    row = await store_.tournament(bot.db, GUILD, tid)
    for key in ("S1-1", "S1-2"):
        await sets.override(bot, guild, who(guild, TO), tid, key, score_a=2, score_b=0)
    second = (await store_.bracket(bot.db, row)).matches["S1-2"]
    for gone in (second.slot_a, second.slot_b):
        assert (await people.dq(bot, guild, who(guild, TO), tid, gone)).ok
    current = await store_.bracket(bot.db, row)
    third = current.matches["S3-1"]
    assert third.rematch
    view = await brackets_view.full(bot.db, row)
    assert next(one for one in view["sets"] if one["key"] == "S3-1")["rematch"] is True
    assert {one["rematch"] for one in view["sets"] if one["key"] != "S3-1"} == {False}
    assert (await sets.call(bot, guild, who(guild, TO), tid, "S3-1")).ok
    assert (await rows(bot.db))[-1][3]["rematch"] is True
    await sets.report(bot, guild, who(guild, TO), tid, "S3-1", 2, 0)
    kind, _, _, details = (await rows(bot.db))[-1]
    assert (kind, details["rematch"]) == ("brackets.set_overridden", True)


async def test_a_pool_set_is_reported_confirmed_and_swept_like_any_other(bot, guild):
    tid = await started(
        bot, guild, ADA, BEA, CY, STAFF, format="double", pools_format="round_robin"
    )
    assert (await store_.tournament(bot.db, GUILD, tid))["state"] == "pools"
    reported = await sets.report(bot, guild, who(guild, ADA), tid, "A.R1-1", 2, 1)
    assert reported.ok and reported.changed == ("A.R1-1",)
    assert reported.message.startswith("A.R1-1 reported 2–1.")
    confirmed = await sets.confirm_report(bot, guild, who(guild, STAFF), tid, "A.R1-1")
    assert confirmed.message == "A.R1-1 is final: Ada wins 2–1."
    await sets.report(bot, guild, who(guild, BEA), tid, "B.R1-1", 2, 0)
    reported_at = datetime.fromisoformat((await the_set(bot, tid, "B.R1-1")).reported_at)
    swept = await sets.confirm_due(bot, guild, reported_at + timedelta(minutes=12))
    assert swept == [(tid, "B.R1-1")]
    stranger = await sets.report(bot, guild, who(guild, CY), tid, "A.R1-1", 2, 0)
    assert stranger.code == "not_in_set"
    missing = await sets.call(bot, guild, who(guild, TO), tid, "C.R1-1")
    assert (missing.code, missing.status) == ("no_set", 404)
