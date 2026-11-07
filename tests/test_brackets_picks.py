# ruff: noqa: F401, F811
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from black_bloc import brackets_moves as moves
from black_bloc import brackets_people as people
from black_bloc import brackets_picks as picks_
from black_bloc import brackets_sets as sets
from black_bloc import brackets_sports as sports
from black_bloc import brackets_store as store_
from black_bloc.sports import feeds
from tests.test_brackets_moves import (
    ADA,
    BEA,
    CY,
    GUILD,
    STAFF,
    TO,
    bot,
    guild,
    rows,
    who,
)
from tests.test_brackets_sports import nfl_answer

TEAMS = ("Ants", "Bees", "Cats", "Dogs")


async def made(bot, guild, **given):
    values = {"name": "Office pool", "kind": "sports", "league": "nba", "source": "own"}
    outcome = await moves.create(bot, guild, who(guild, TO), values | given)
    assert outcome.ok, outcome.message
    tid = outcome.value
    for name in TEAMS:
        assert (await people.add_entrant(bot, guild, who(guild, TO), tid, name=name)).ok
    assert (await sports.build(bot, guild, who(guild, TO), tid)).ok
    return tid


async def ids(bot, tid):
    return {one["name"]: one["id"] for one in await store_.entrants(bot.db, tid)}


async def sheet(bot, guild, user, tid, **chosen):
    team = await ids(bot, tid)
    given = {"picks": {key: team[name] for key, name in chosen.items()}}
    return await picks_.save_sheet(bot, guild, who(guild, user), tid, given)


async def row_of(bot, tid):
    return await store_.tournament(bot.db, GUILD, tid)


async def scores(bot, tid):
    found = await store_.sheets(bot.db, tid)
    return {
        user: (one["points"], one["correct"], one["possible"], one["rank"])
        for user, one in found.items()
    }


async def decided(bot, guild, tid, key, name):
    team = await ids(bot, tid)
    current = await store_.bracket(bot.db, await row_of(bot, tid))
    side = current.matches[key].side_of(team[name])
    outcome = await sets.override(bot, guild, who(guild, TO), tid, key, winner=side)
    assert outcome.ok, outcome.message


async def test_a_new_sports_bracket_takes_sheets_with_the_points_from_settings(bot, guild):
    await bot.store.set(GUILD, "brackets_pick_points", "1, 3,9", by=STAFF)
    tid = await made(bot, guild)
    row = await row_of(bot, tid)
    assert (row["picks_on"], row["picks_points"], row["picks_lock_at"]) == (1, "1,3,9", None)
    assert store_.picks_on(row)
    fighters = await moves.create(bot, guild, who(guild, TO), {"name": "Knuck Up"})
    assert not store_.picks_on(await row_of(bot, fighters.value))
    await bot.store.set(GUILD, "brackets_picks_default", False, by=STAFF)
    assert not store_.picks_on(await row_of(bot, await made(bot, guild)))


async def test_a_member_saves_a_whole_sheet_and_a_skipped_feeder_is_refused_in_words(bot, guild):
    tid = await made(bot, guild)
    saved = await sheet(bot, guild, ADA, tid, **{"W1-1": "Ants", "W1-2": "Cats", "W2-1": "Cats"})
    assert saved.ok, saved.message
    assert saved.message == "Saved."
    assert saved.changed == ("sheet_added",)
    again = await sheet(bot, guild, ADA, tid, **{"W1-1": "Ants", "W1-2": "Cats"})
    assert again.ok and again.changed == ()
    wrong = await sheet(bot, guild, BEA, tid, **{"W1-1": "Ants", "W1-2": "Cats", "W2-1": "Dogs"})
    assert (wrong.ok, wrong.code, wrong.status) == (False, "pick_inconsistent", 409)
    assert "W2-1 needs the pick of the game that feeds it" in wrong.message
    assert await store_.picks_of(bot.db, tid, BEA) == {}
    assert await rows(bot.db, "%sheet%") == []


async def test_a_bad_shape_is_refused_naming_the_field(bot, guild):
    tid = await made(bot, guild)
    refused = await picks_.save_sheet(bot, guild, who(guild, ADA), tid, {"picks": ["W1-1"]})
    assert (refused.ok, refused.code) == (False, "bad_option")
    assert refused.message.startswith("picks cannot be")
    await bot.store.set(GUILD, "brackets_pick_tiebreak", True, by=STAFF)
    refused = await picks_.save_sheet(bot, guild, who(guild, ADA), tid, {"tiebreak": "lots"})
    assert refused.message.startswith("tiebreak cannot be")


async def test_the_tiebreak_is_kept_only_while_the_setting_is_on(bot, guild):
    tid = await made(bot, guild)
    await picks_.save_sheet(bot, guild, who(guild, ADA), tid, {"picks": {}, "tiebreak": 150})
    assert (await store_.sheet(bot.db, tid, ADA))["tiebreak"] is None
    await bot.store.set(GUILD, "brackets_pick_tiebreak", True, by=STAFF)
    await picks_.save_sheet(bot, guild, who(guild, ADA), tid, {"picks": {}, "tiebreak": 150})
    assert (await store_.sheet(bot.db, tid, ADA))["tiebreak"] == 150


async def test_a_fighters_bracket_has_no_sheets(bot, guild):
    fighters = (await moves.create(bot, guild, who(guild, TO), {"name": "Knuck Up"})).value
    refused = await picks_.save_sheet(bot, guild, who(guild, ADA), fighters, {"picks": {}})
    assert (refused.ok, refused.code) == (False, "picks_off")
    assert refused.message == "**Knuck Up** has no pick sheets."


async def test_every_result_rescores_every_sheet_and_level_sheets_share_a_rank(bot, guild):
    tid = await made(bot, guild)
    await sheet(bot, guild, ADA, tid, **{"W1-1": "Ants", "W1-2": "Cats", "W2-1": "Cats"})
    await sheet(bot, guild, BEA, tid, **{"W1-1": "Dogs", "W1-2": "Cats", "W2-1": "Dogs"})
    await sheet(bot, guild, CY, tid, **{"W1-1": "Ants", "W1-2": "Bees", "W2-1": "Ants"})
    assert (await moves.start(bot, guild, who(guild, TO), tid)).ok
    assert await scores(bot, tid) == {ADA: (0, 0, 4, 1), BEA: (0, 0, 4, 1), CY: (0, 0, 4, 1)}
    await decided(bot, guild, tid, "W1-1", "Ants")
    assert await scores(bot, tid) == {ADA: (1, 1, 3, 1), BEA: (0, 0, 1, 3), CY: (1, 1, 3, 1)}
    await decided(bot, guild, tid, "W1-2", "Cats")
    await decided(bot, guild, tid, "W2-1", "Cats")
    assert await scores(bot, tid) == {ADA: (4, 3, 0, 1), BEA: (1, 1, 0, 2), CY: (1, 1, 0, 2)}
    reset = await sets.reset(bot, guild, who(guild, TO), tid, "W2-1")
    assert reset.ok
    assert (await scores(bot, tid))[ADA] == (2, 2, 2, 1)


async def test_the_tiebreak_parts_level_sheets_once_the_final_is_played(bot, guild):
    await bot.store.set(GUILD, "brackets_pick_tiebreak", True, by=STAFF)
    tid = await made(bot, guild)
    team = await ids(bot, tid)
    base = {"W1-1": team["Ants"], "W1-2": team["Cats"], "W2-1": team["Ants"]}
    for user, guess in ((ADA, 150), (BEA, 141)):
        given = {"picks": base, "tiebreak": guess}
        assert (await picks_.save_sheet(bot, guild, who(guild, user), tid, given)).ok
    assert (await moves.start(bot, guild, who(guild, TO), tid)).ok
    await decided(bot, guild, tid, "W1-1", "Ants")
    await decided(bot, guild, tid, "W1-2", "Cats")
    current = await store_.bracket(bot.db, await row_of(bot, tid))
    side = current.matches["W2-1"].side_of(team["Cats"])
    outcome = await sets.override(
        bot, guild, who(guild, TO), tid, "W2-1", winner=side, score_a=70, score_b=72
    )
    assert outcome.ok
    found = await scores(bot, tid)
    assert (found[ADA][3], found[BEA][3]) == (2, 1)


async def test_ranks_are_frozen_once_the_tournament_is_complete(bot, guild):
    tid = await made(bot, guild)
    await sheet(bot, guild, ADA, tid, **{"W1-1": "Ants", "W1-2": "Cats", "W2-1": "Cats"})
    assert (await moves.start(bot, guild, who(guild, TO), tid)).ok
    for key, name in (("W1-1", "Ants"), ("W1-2", "Cats"), ("W2-1", "Cats")):
        await decided(bot, guild, tid, key, name)
    assert (await moves.complete(bot, guild, who(guild, TO), tid)).ok
    before = await scores(bot, tid)
    await picks_.rescore(bot, await row_of(bot, tid))
    assert await scores(bot, tid) == before == {ADA: (4, 3, 0, 1)}


async def test_the_sweep_locks_every_sheet_once_when_the_lock_time_passes(bot, guild):
    tid = await made(bot, guild)
    await sheet(bot, guild, ADA, tid, **{"W1-1": "Ants"})
    soon = datetime.now(UTC) + timedelta(hours=1)
    await store_.update(bot.db, tid, {"picks_lock_at": soon.isoformat()})
    assert await picks_.lock_due(bot, guild) == []
    later = soon + timedelta(minutes=1)
    assert await picks_.lock_due(bot, guild, later) == [tid]
    assert await picks_.lock_due(bot, guild, later) == []
    held = await store_.sheet(bot.db, tid, ADA)
    assert held["locked_at"] == later.isoformat()
    logged = await rows(bot.db, "%picks_locked%")
    assert [(one[0], one[3]["sheets"]) for one in logged] == [
        ("brackets.picks_locked", 1)
    ]
    late = await sheet(bot, guild, ADA, tid, **{"W1-1": "Bees"})
    assert (late.ok, late.code) == (False, "picks_locked")
    assert late.message == "Picks for **Office pool** are locked, so your sheet stays as it is."


async def test_a_result_locks_the_sheets_even_with_no_lock_time(bot, guild):
    tid = await made(bot, guild)
    await sheet(bot, guild, ADA, tid, **{"W1-1": "Ants"})
    assert (await moves.start(bot, guild, who(guild, TO), tid)).ok
    refused = await sheet(bot, guild, BEA, tid, **{"W1-1": "Ants"})
    assert refused.ok
    await decided(bot, guild, tid, "W1-1", "Ants")
    refused = await sheet(bot, guild, BEA, tid, **{"W1-1": "Ants"})
    assert (refused.ok, refused.code) == (False, "picks_locked")
    assert await picks_.lock_due(bot, guild) == [tid]


async def test_a_live_game_locks_the_sheets(bot, guild):
    tid = await made(bot, guild)
    assert (await moves.start(bot, guild, who(guild, TO), tid)).ok
    await store_.write_sports(bot.db, tid, "W1-1", {"live_status": "live"})
    assert await picks_.lock_due(bot, guild) == [tid]


async def test_staff_edit_a_sheet_with_a_reason_and_it_says_so(bot, guild):
    tid = await made(bot, guild)
    team = await ids(bot, tid)
    given = {"picks": {"W1-1": team["Dogs"]}, "reason": "asked in modmail"}
    refused = await picks_.edit_sheet(bot, guild, who(guild, ADA), tid, BEA, given)
    assert (refused.ok, refused.code) == (False, "not_organiser")
    bare = await picks_.edit_sheet(bot, guild, who(guild, TO), tid, BEA, {"picks": {}})
    assert (bare.ok, bare.code) == (False, "reason_needed")
    await store_.update(bot.db, tid, {"picks_locked_at": "2026-01-01T00:00:00+00:00"})
    done = await picks_.edit_sheet(bot, guild, who(guild, TO), tid, BEA, given, member="Bea")
    assert done.ok, done.message
    assert done.message == "Saved Bea's sheet."
    held = await store_.sheet(bot.db, tid, BEA)
    assert (held["edited_by"], held["locked_at"] is not None) == (TO, True)
    assert await store_.picks_of(bot.db, tid, BEA) == {"W1-1": team["Dogs"]}
    logged = await rows(bot.db, "%sheet_edited%")
    assert logged[0][:3] == ("brackets.sheet_edited", TO, BEA)
    assert logged[0][3]["reason"] == "asked in modmail"


async def test_staff_turn_picks_off_before_the_lock_and_not_after(bot, guild):
    tid = await made(bot, guild)
    off = await picks_.edit_with_picks(bot, guild, who(guild, TO), tid, {"picks_on": False})
    assert off.ok
    assert not store_.picks_on(await row_of(bot, tid))
    assert (await picks_.edit_with_picks(bot, guild, who(guild, TO), tid, {"picks_on": True})).ok
    await store_.update(bot.db, tid, {"picks_locked_at": "2026-01-01T00:00:00+00:00"})
    refused = await picks_.edit_with_picks(bot, guild, who(guild, TO), tid, {"picks_on": False})
    assert (refused.ok, refused.code) == (False, "picks_locked")
    member = await picks_.edit_with_picks(bot, guild, who(guild, ADA), tid, {"picks_on": False})
    assert (member.ok, member.code) == (False, "not_organiser")


async def test_a_lock_moved_into_the_future_opens_the_sheets_again(bot, guild):
    tid = await made(bot, guild)
    await sheet(bot, guild, ADA, tid, **{"W1-1": "Ants"})
    past = datetime.now(UTC) - timedelta(minutes=5)
    moved = await picks_.edit_with_picks(
        bot, guild, who(guild, TO), tid, {"picks_lock_at": past.isoformat()}
    )
    assert moved.ok
    assert await picks_.lock_due(bot, guild) == [tid]
    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    assert (
        await picks_.edit_with_picks(bot, guild, who(guild, TO), tid, {"picks_lock_at": future})
    ).ok
    row = await row_of(bot, tid)
    assert row["picks_locked_at"] is None
    assert (await store_.sheet(bot.db, tid, ADA))["locked_at"] is None
    assert (await sheet(bot, guild, ADA, tid, **{"W1-1": "Dogs"})).ok


async def test_the_points_and_lock_are_checked_in_words(bot, guild):
    tid = await made(bot, guild)
    bad = await picks_.edit_with_picks(bot, guild, who(guild, TO), tid, {"picks_points": "1,a"})
    assert (bad.ok, bad.code) == (False, "bad_option")
    assert bad.message.startswith("picks_points cannot be 1,a")
    late = await picks_.edit_with_picks(bot, guild, who(guild, TO), tid, {"picks_lock_at": "x"})
    assert late.message.startswith("picks_lock_at cannot be x")
    good = await picks_.edit_with_picks(bot, guild, who(guild, TO), tid, {"picks_points": "2, 5"})
    assert good.ok and (await row_of(bot, tid))["picks_points"] == "2,5"


async def test_picks_settings_reach_a_running_bracket_but_its_other_options_do_not(bot, guild):
    tid = await made(bot, guild)
    assert (await moves.start(bot, guild, who(guild, TO), tid)).ok
    good = await picks_.edit_with_picks(bot, guild, who(guild, TO), tid, {"picks_points": "3"})
    assert good.ok
    mixed = await picks_.edit_with_picks(
        bot, guild, who(guild, TO), tid, {"picks_points": "4", "name": "New"}
    )
    assert (mixed.ok, mixed.code) == (False, "wrong_state")
    assert (await row_of(bot, tid))["picks_points"] == "3"


async def test_a_quick_pick_saves_at_once_and_drops_the_later_picks_it_breaks(bot, guild):
    tid = await made(bot, guild)
    team = await ids(bot, tid)
    await sheet(bot, guild, ADA, tid, **{"W1-1": "Ants", "W1-2": "Cats", "W2-1": "Ants"})
    outcome = await picks_.quick_pick(bot, guild, who(guild, ADA), tid, "W1-1", team["Dogs"])
    assert outcome.ok and outcome.message == "Saved: Dogs to win W1-1."
    assert await store_.picks_of(bot.db, tid, ADA) == {"W1-1": team["Dogs"], "W1-2": team["Cats"]}
    refused = await picks_.quick_pick(bot, guild, who(guild, ADA), tid, "W2-1", team["Ants"])
    assert (refused.ok, refused.code) == (False, "pick_inconsistent")


async def test_build_and_import_set_the_lock_at_the_first_game_after_any_play_in(bot, guild):
    from black_bloc.brackets.model import Bracket, Match, Options

    bracket = Bracket(
        Options(format="single"),
        [1, 2],
        {
            "W0-1": Match("W0-1", "winners", 0, 1, 1),
            "W1-1": Match("W1-1", "winners", 1, 1, 1),
            "W1-2": Match("W1-2", "winners", 1, 2, 1),
        },
    )
    meta = {
        "W0-1": {"scheduled_at": "2026-03-17T23:00:00+00:00"},
        "W1-1": {"scheduled_at": "2026-03-19T20:00:00+00:00"},
        "W1-2": {"scheduled_at": "2026-03-19T16:15:00+00:00"},
    }
    assert picks_.first_game(bracket, meta) == "2026-03-19T16:15:00+00:00"
    meta["W1-1"]["scheduled_at"] = meta["W1-2"]["scheduled_at"] = None
    assert picks_.first_game(bracket, meta) == "2026-03-17T23:00:00+00:00"
    assert picks_.first_game(bracket, {}) is None
    tid = await made(bot, guild)
    assert (await row_of(bot, tid))["picks_lock_at"] is None


async def test_an_nfl_sheet_predicts_its_own_reseeded_divisional_round(bot, guild):
    values = {"name": "NFL Playoffs", "kind": "sports", "league": "nfl", "season": "2025"}
    tid = (await moves.create(bot, guild, who(guild, TO), values)).value
    original = feeds.bracket

    async def bracket_of(league, season, *, fetch=None):
        return nfl_answer([])

    feeds.bracket = bracket_of
    try:
        assert (await sports.import_bracket(bot, guild, who(guild, TO), tid)).ok
    finally:
        feeds.bracket = original
    row = await row_of(bot, tid)
    found = await picks_.read(bot, row)
    meta = found.meta
    keyed = {value["source_key"]: key for key, value in meta.items() if value["source_key"]}
    seeds = {one["id"]: one["seed"] for one in await store_.entrants(bot.db, tid)}
    current = found.bracket
    wild = [current.matches[keyed[f"AFC-WC-{at}"]] for at in (1, 2, 3)]
    lowest = [max((one.slot_a, one.slot_b), key=lambda team: seeds[team]) for one in wild]
    chosen = {one.key: team for one, team in zip(wild, lowest, strict=True)}
    outcome = await picks_.save_sheet(bot, guild, who(guild, ADA), tid, {"picks": chosen})
    assert outcome.ok, outcome.message
    from black_bloc.brackets import picks

    slots, _ = picks.predicted(found.tree, chosen)
    worst = max(lowest, key=lambda team: seeds[team])
    first = current.matches[keyed["AFC-DIV-1"]]
    assert slots[first.key] == (first.slot_a, worst)
    second = sorted((one for one in lowest if one != worst), key=lambda team: seeds[team])
    assert slots[keyed["AFC-DIV-2"]] == tuple(second)
    divisional = {keyed["AFC-DIV-1"]: worst, **chosen}
    assert (await picks_.save_sheet(bot, guild, who(guild, ADA), tid, {"picks": divisional})).ok


async def test_the_board_counts_sheets_before_the_lock_and_ranks_them_after(bot, guild):
    tid = await made(bot, guild)
    await sheet(bot, guild, ADA, tid, **{"W1-1": "Ants"})
    await sheet(bot, guild, BEA, tid, **{"W1-1": "Dogs"})
    await picks_.save_sheet(bot, guild, who(guild, CY), tid, {"picks": {}})
    found = await picks_.board(bot, await row_of(bot, tid))
    assert (found.locked, found.count, found.games, found.rows) == (False, 2, 3, ())
    assert (await moves.start(bot, guild, who(guild, TO), tid)).ok
    await decided(bot, guild, tid, "W1-1", "Ants")
    found = await picks_.board(bot, await row_of(bot, tid))
    assert found.locked and found.rows == ((1, ADA, 1), (2, BEA, 0))
    await bot.store.set(GUILD, "brackets_leaderboard_rows", 1, by=STAFF)
    assert (await picks_.board(bot, await row_of(bot, tid))).rows == ((1, ADA, 1),)
    fighters = (await moves.create(bot, guild, who(guild, TO), {"name": "Knuck Up"})).value
    assert await picks_.board(bot, await row_of(bot, fighters)) is None


async def test_a_sheet_on_the_page_carries_its_tree_marks_and_the_lock(bot, guild):
    tid = await made(bot, guild)
    await sheet(bot, guild, ADA, tid, **{"W1-1": "Ants", "W1-2": "Cats", "W2-1": "Ants"})
    found = await picks_.read(bot, await row_of(bot, tid))
    shown = picks_.sheet_fields(found, ADA, mine=True)
    assert shown["may_edit"] and not shown["locked"]
    assert shown["marks"] == {}
    assert set(shown["tree"]["sets"]) == {"W1-1", "W1-2", "W2-1"}
    assert shown["round_points"] == {"1": 1, "2": 2}
    assert (await moves.start(bot, guild, who(guild, TO), tid)).ok
    await decided(bot, guild, tid, "W1-1", "Ants")
    found = await picks_.read(bot, await row_of(bot, tid))
    shown = picks_.sheet_fields(found, ADA, mine=True)
    assert (shown["locked"], shown["may_edit"], shown["marks"]) == (True, False, {"W1-1": "hit"})
    assert (shown["points"], shown["correct"], shown["played"], shown["rank"]) == (1, 1, 1, 1)
    board = picks_.leaderboard_rows(found, BEA, False)
    assert [(one["user_id"], one["mine"], one["may_open"]) for one in board] == [
        (str(ADA), False, True)
    ]
