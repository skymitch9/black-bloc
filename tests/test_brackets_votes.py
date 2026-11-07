# ruff: noqa: F401, F811
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from black_bloc import brackets_moves as moves
from black_bloc import brackets_people as people
from black_bloc import brackets_sets as sets
from black_bloc import brackets_store as store_
from black_bloc import brackets_votes as votes
from black_bloc.logkinds import VIA_WEBSITE
from tests.test_brackets_moves import (
    ADA,
    BEA,
    CY,
    GUILD,
    STAFF,
    STRANGER,
    TO,
    bot,
    guild,
    rows,
    the_set,
    who,
)

CANDY = ("Snickers", "Twix", "Mars", "Kit Kat")


async def listed(bot, guild, *names, decide_by="votes", start=True, **given):
    outcome = await moves.create(
        bot,
        guild,
        who(guild, TO),
        {"name": "Best candy bar", "kind": "list", "decide_by": decide_by, "format": "single"}
        | given,
    )
    assert outcome.ok, outcome.message
    tid = outcome.value
    for name in names:
        added = await people.add_entrant(bot, guild, who(guild, TO), tid, name=name)
        assert added.ok, added.message
    if start:
        started = await moves.start(bot, guild, who(guild, TO), tid)
        assert started.ok, started.message
    return tid


async def held(bot, tid, key):
    return await store_.ballot(bot.db, tid, key)


async def test_a_list_bracket_is_made_with_bo1_sets_no_pools_and_the_registry_vote_time(bot, guild):
    tid = await listed(bot, guild, start=False, best_of=5, pools_format="round_robin")
    row = await store_.tournament(bot.db, GUILD, tid)
    assert (row["kind"], row["decide_by"], row["vote_minutes"]) == ("list", "votes", 1440)
    assert (row["best_of"], row["best_of_late"], row["best_of_finals"]) == (1, 1, 1)
    assert row["pools_format"] == "none"


async def test_a_fighters_bracket_stores_its_kind_and_no_vote_settings(bot, guild):
    outcome = await moves.create(
        bot, guild, who(guild, TO), {"name": "Knuck Up", "vote_minutes": 30, "decide_by": "votes"}
    )
    row = await store_.tournament(bot.db, GUILD, outcome.value)
    assert (row["kind"], row["decide_by"], row["vote_minutes"]) == ("fighters", None, None)


async def test_sports_is_refused_in_words_for_now_and_a_bad_kind_names_the_choices(bot, guild):
    sports = await moves.create(bot, guild, who(guild, TO), {"name": "March", "kind": "sports"})
    assert (sports.ok, sports.code, sports.status) == (False, "bad_option", 400)
    assert "nfl, nba, mlb, nhl, ncaam, ncaaw" in sports.message
    bad = await moves.create(bot, guild, who(guild, TO), {"name": "X", "kind": "cards"})
    assert (bad.code, bad.status) == ("bad_option", 400)
    assert "fighters, sports, list" in bad.message


async def test_the_kind_is_fixed_once_made(bot, guild):
    tid = await listed(bot, guild, start=False)
    refused = await moves.edit(bot, guild, who(guild, TO), tid, {"kind": "fighters"})
    assert (refused.code, refused.status) == ("kind_fixed", 409)
    same = await moves.edit(bot, guild, who(guild, TO), tid, {"kind": "list", "vote_minutes": 60})
    assert same.ok
    assert (await store_.tournament(bot.db, GUILD, tid))["vote_minutes"] == 60


async def test_a_list_bracket_has_no_signups_or_check_in_and_its_entrants_are_plain_names(
    bot, guild
):
    tid = await listed(bot, guild, start=False)
    for move in (moves.open_signups, people.open_check_in):
        refused = await move(bot, guild, who(guild, TO), tid)
        assert (refused.code, refused.status) == ("no_signups", 409)
        assert (
            refused.message
            == "**Best candy bar** is a list bracket, so it has no sign-ups or check-in."
        )
    joined = await people.join(bot, guild, who(guild, ADA), tid)
    assert joined.code == "no_signups"
    added = await people.add_entrant(bot, guild, who(guild, TO), tid, user_id=ADA)
    assert added.ok
    [entrant] = await store_.entrants(bot.db, tid)
    assert (entrant["name"], entrant["user_id"]) == ("Ada", None)


async def test_a_list_bracket_starts_from_draft_and_every_ready_set_opens_a_vote(bot, guild):
    tid = await listed(bot, guild, *CANDY)
    row = await store_.tournament(bot.db, GUILD, tid)
    assert row["state"] == "running"
    ballots = await store_.ballots(bot.db, tid)
    assert sorted(ballots) == ["W1-1", "W1-2"]
    one = ballots["W1-1"]
    opens = datetime.fromisoformat(one["opens_at"])
    assert datetime.fromisoformat(one["closes_at"]) - opens == timedelta(minutes=1440)
    opened = [
        details["set"]
        for kind, _, _, details in await rows(bot.db)
        if kind == "brackets.vote_opened"
    ]
    assert sorted(opened) == ["W1-1", "W1-2"]


async def test_anyone_may_vote_and_a_second_press_changes_the_vote(bot, guild):
    tid = await listed(bot, guild, *CANDY)
    first = await votes.vote(bot, guild, who(guild, STRANGER), tid, "W1-1", "a")
    assert first.ok and first.changed == ("W1-1",)
    assert first.message.startswith("You voted for Snickers · change any time until <t:")
    await votes.vote(bot, guild, who(guild, ADA), tid, "W1-1", "b")
    again = await votes.vote(bot, guild, who(guild, STRANGER), tid, "W1-1", "b")
    assert again.ok
    found = await held(bot, tid, "W1-1")
    assert (found["a"], found["b"]) == (0, 2)
    assert await store_.my_votes(bot.db, tid, STRANGER) == {"W1-1": "b"}
    assert not [kind for kind, *_ in await rows(bot.db) if "vote" in kind and "opened" not in kind]


async def test_a_vote_names_one_side_of_an_open_set(bot, guild):
    tid = await listed(bot, guild, *CANDY)
    bad = await votes.vote(bot, guild, who(guild, ADA), tid, "W1-1", "c")
    assert (bad.code, bad.status) == ("bad_slot", 400)
    waiting = await votes.vote(bot, guild, who(guild, ADA), tid, "W2-1", "a")
    assert waiting.code in ("bad_slot", "vote_closed")
    gone = await votes.vote(bot, guild, who(guild, ADA), tid, "W9-9", "a")
    assert gone.code == "no_set"


async def test_the_organiser_closes_a_vote_and_the_winner_goes_through_override(bot, guild):
    tid = await listed(bot, guild, *CANDY)
    for user, slot in ((ADA, "a"), (BEA, "a"), (CY, "b")):
        await votes.vote(bot, guild, who(guild, user), tid, "W1-1", slot)
    member = await votes.close_vote(bot, guild, who(guild, ADA), tid, "W1-1")
    assert member.code == "not_organiser"
    closed = await votes.close_vote(bot, guild, who(guild, TO), tid, "W1-1")
    assert closed.ok, closed.message
    assert closed.message == "W1-1 is final: Snickers wins 2–1."
    match = await the_set(bot, tid, "W1-1")
    assert (match.state, match.score_a, match.score_b, match.confirmed_how) == (
        "complete",
        2,
        1,
        "votes",
    )
    final = await the_set(bot, tid, "W2-1")
    assert final.slot_a == match.winner
    assert (await held(bot, tid, "W1-1"))["closed_at"]
    logged = [one for one in await rows(bot.db) if one[0] == "brackets.vote_closed"]
    details = logged[-1][3]
    assert {key: details[key] for key in ("set", "votes_a", "votes_b", "tied")} == {
        "set": "W1-1",
        "votes_a": 2,
        "votes_b": 1,
        "tied": False,
    }
    late = await votes.vote(bot, guild, who(guild, STRANGER), tid, "W1-1", "b")
    assert late.code == "vote_closed"


async def test_a_tie_waits_on_the_organiser_who_decides_with_the_counts_kept(bot, guild):
    tid = await listed(bot, guild, *CANDY)
    await votes.vote(bot, guild, who(guild, ADA), tid, "W1-1", "a")
    await votes.vote(bot, guild, who(guild, BEA), tid, "W1-1", "b")
    tied = await votes.close_vote(bot, guild, who(guild, TO), tid, "W1-1")
    assert tied.ok and tied.message == "Tied 1–1 · an organiser decides"
    match = await the_set(bot, tid, "W1-1")
    assert (match.state, match.score_a, match.score_b) == ("reported", 1, 1)
    level = await sets.override(bot, guild, who(guild, TO), tid, "W1-1")
    assert level.code == "pick_winner"
    decided = await sets.override(bot, guild, who(guild, TO), tid, "W1-1", winner="b")
    assert decided.ok, decided.message
    match = await the_set(bot, tid, "W1-1")
    assert (match.state, match.winner, match.score_a, match.score_b) == (
        "complete",
        match.slot_b,
        1,
        1,
    )


async def test_the_organisers_decide_before_close_closes_the_vote(bot, guild):
    tid = await listed(bot, guild, *CANDY)
    await votes.vote(bot, guild, who(guild, ADA), tid, "W1-1", "a")
    decided = await sets.override(bot, guild, who(guild, TO), tid, "W1-1", winner="b")
    assert decided.ok
    assert (await held(bot, tid, "W1-1"))["closed_at"]
    again = await votes.close_vote(bot, guild, who(guild, TO), tid, "W1-1")
    assert again.code == "vote_closed"


async def test_a_reset_opens_a_fresh_vote_and_clears_what_it_fed(bot, guild):
    tid = await listed(bot, guild, *CANDY)
    await votes.vote(bot, guild, who(guild, ADA), tid, "W1-1", "a")
    await votes.vote(bot, guild, who(guild, ADA), tid, "W1-2", "b")
    await votes.close_vote(bot, guild, who(guild, TO), tid, "W1-1")
    await votes.close_vote(bot, guild, who(guild, TO), tid, "W1-2")
    assert await held(bot, tid, "W2-1")
    reset = await sets.reset(bot, guild, who(guild, TO), tid, "W1-1")
    assert reset.ok, reset.message
    fresh = await held(bot, tid, "W1-1")
    assert fresh["closed_at"] is None and (fresh["a"], fresh["b"]) == (0, 0)
    assert await held(bot, tid, "W2-1") is None


async def test_the_sweep_closes_due_votes_and_opens_the_next_round(bot, guild):
    tid = await listed(bot, guild, *CANDY, vote_minutes=5)
    await votes.vote(bot, guild, who(guild, ADA), tid, "W1-1", "b")
    await votes.vote(bot, guild, who(guild, ADA), tid, "W1-2", "a")
    early = await votes.close_due_votes(bot, guild, datetime.now(UTC))
    assert early == {}
    later = datetime.now(UTC) + timedelta(minutes=6)
    owed = await votes.close_due_votes(bot, guild, later)
    assert set(owed[tid]) >= {"W1-1", "W1-2", "W2-1"}
    final = await the_set(bot, tid, "W2-1")
    assert final.state == "ready"
    assert (await held(bot, tid, "W2-1"))["closed_at"] is None


async def test_the_sweep_skips_off_and_an_organiser_decided_bracket(bot, guild):
    tid = await listed(bot, guild, *CANDY, decide_by="organiser")
    assert await store_.ballots(bot.db, tid) == {}
    refused = await votes.vote(bot, guild, who(guild, ADA), tid, "W1-1", "a")
    assert refused.code == "not_votes"
    decided = await sets.override(bot, guild, who(guild, TO), tid, "W1-1", winner="a")
    assert decided.ok
    match = await the_set(bot, tid, "W1-1")
    assert (match.score_a, match.score_b, match.state) == (None, None, "complete")
    await bot.store.set(GUILD, "brackets_mode", "off")
    assert await votes.close_due_votes(bot, guild, datetime.now(UTC) + timedelta(days=9)) == {}


async def test_the_websites_vote_answer_reads_a_plain_day_and_time(bot, guild):
    tid = await listed(bot, guild, *CANDY)
    found = await votes.vote(bot, guild, who(guild, ADA), tid, "W1-1", "a", via=VIA_WEBSITE)
    assert "<t:" not in found.message and " · change any time until " in found.message


async def test_an_unreadable_closing_time_is_due_at_once(bot, guild):
    tid = await listed(bot, guild, *CANDY)
    await bot.db.conn.execute(
        "UPDATE tournament_sets SET vote_closes_at = 'soon' WHERE tournament_id = ? AND key = ?",
        (tid, "W1-1"),
    )
    await bot.db.conn.commit()
    await votes.vote(bot, guild, who(guild, ADA), tid, "W1-2", "a")
    owed = await votes.close_due_votes(bot, guild, datetime.now(UTC))
    assert "W1-1" in owed[tid]
    assert (await the_set(bot, tid, "W1-1")).state == "reported"
