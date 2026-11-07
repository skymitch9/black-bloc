# ruff: noqa: F401, F811
from __future__ import annotations

from dataclasses import replace

from black_bloc import brackets_moves as moves
from black_bloc import brackets_people as people
from black_bloc import brackets_sets as sets
from black_bloc import brackets_sports as sports
from black_bloc import brackets_store as store_
from black_bloc.brackets.sports_shape import is_pending, pending_key
from black_bloc.sports import feeds, nfl
from black_bloc.sports.model import FINAL, LIVE, NHL_API, SCHEDULED, Bracket, Game, failed, found
from tests.sports_fakes import Recorded, payload
from tests.test_brackets_moves import (
    ADA,
    GUILD,
    STRANGER,
    TO,
    bot,
    guild,
    rows,
    who,
)

NHL_ROUTES = {"playoff-bracket/2026": "nhl_bracket_2026"}


async def made(bot, guild, **given):
    values = {"name": "Stanley Cup", "kind": "sports", "league": "nhl", "season": "2025-26"}
    outcome = await moves.create(bot, guild, who(guild, TO), values | given)
    assert outcome.ok, outcome.message
    return outcome.value


async def imported(bot, guild, **given):
    bot.sports_fetch = Recorded(NHL_ROUTES)
    tid = await made(bot, guild, **given)
    outcome = await sports.import_bracket(bot, guild, who(guild, TO), tid)
    assert outcome.ok, outcome.message
    return tid


async def running(bot, guild):
    tid = await imported(bot, guild)
    assert (await moves.start(bot, guild, who(guild, TO), tid)).ok
    return tid


async def meta(bot, tid):
    return await store_.sports_rows(bot.db, tid)


async def state(bot, tid):
    row = await store_.tournament(bot.db, GUILD, tid)
    return row, await store_.bracket(bot.db, row)


def nhl_answer(**changed):
    parsed = feeds.nhl.parse_bracket(payload("nhl_bracket_2026"), 2026)
    for key, values in changed.items():
        parsed.games = [
            replace(one, **values) if one.source_key == key else one for one in parsed.games
        ]
    return found(parsed, NHL_API)


def scheduled_answer():
    parsed = feeds.nhl.parse_bracket(payload("nhl_bracket_2026"), 2026)
    parsed.games = [
        replace(one, status=SCHEDULED, a_score=None, b_score=None) for one in parsed.games
    ]
    return found(parsed, NHL_API)


async def test_a_sports_bracket_names_its_league_and_season_and_takes_the_leagues_feed(bot, guild):
    tid = await made(bot, guild, best_of=5, pools_format="round_robin")
    row = await store_.tournament(bot.db, GUILD, tid)
    assert (row["kind"], row["league"], row["season"], row["source"], row["source_ref"]) == (
        "sports",
        "nhl",
        "2025-26",
        "nhl",
        "nhl:2025-26",
    )
    assert (row["format"], row["best_of"], row["third_place"], row["pools_format"]) == (
        "single",
        1,
        0,
        "none",
    )


async def test_by_hand_is_source_own_and_a_league_is_required_in_words(bot, guild):
    tid = await made(bot, guild, source="own", league="ncaam", season="")
    row = await store_.tournament(bot.db, GUILD, tid)
    assert (row["source"], row["league"]) == ("own", "ncaam")
    assert row["season"] == feeds.current_season("ncaam", __import__("datetime").date.today())
    refused = await moves.create(bot, guild, who(guild, TO), {"name": "X", "kind": "sports"})
    assert (refused.ok, refused.code, refused.status) == (False, "bad_option", 400)
    assert "league cannot be None" in refused.message


async def test_an_edit_moves_the_league_and_its_feed_with_it(bot, guild):
    tid = await made(bot, guild)
    assert (await moves.edit(bot, guild, who(guild, TO), tid, {"league": "nba"})).ok
    row = await store_.tournament(bot.db, GUILD, tid)
    assert (row["league"], row["source"], row["source_ref"]) == (
        "nba",
        "nba",
        f"nba:{row['season']}",
    )


async def test_import_writes_the_feeds_teams_and_sets_with_explicit_links(bot, guild):
    tid = await imported(bot, guild)
    row, bracket = await state(bot, tid)
    assert row["state"] == "draft"
    teams = await store_.entrants(bot.db, tid)
    assert len(teams) == 16
    assert {(one["ext_source"], one["user_id"]) for one in teams} == {("nhl", None)}
    shown = [key for key in bracket.matches if not is_pending(key)]
    assert len(shown) == 15
    first = bracket.matches["W1-1"]
    assert (first.winner_to, first.winner_slot, first.best_of, first.state) == (
        "W2-1",
        "a",
        7,
        "ready",
    )
    assert all(one.state != "complete" for one in bracket.matches.values())
    keyed = await meta(bot, tid)
    assert keyed["W4-1"]["source_key"] == "O"
    assert keyed["W1-1"]["source_key"] == "A"
    logged = [kind for kind, *_ in await rows(bot.db)]
    assert logged.count("brackets.imported") == 1


async def test_import_again_asks_first_then_replaces_hand_edits(bot, guild):
    tid = await imported(bot, guild)
    entrant = (await store_.entrants(bot.db, tid))[0]
    edited = await people.edit_entrant(
        bot, guild, who(guild, TO), tid, entrant["id"], {"name": "X"}
    )
    assert edited.ok
    asked = await sports.import_bracket(bot, guild, who(guild, TO), tid)
    assert (asked.ok, asked.code, asked.status) == (False, "confirm_reimport", 409)
    assert "hand edits included" in asked.message
    again = await sports.import_bracket(bot, guild, who(guild, TO), tid, replace=True)
    assert again.ok, again.message
    names = {one["name"] for one in await store_.entrants(bot.db, tid)}
    assert "X" not in names and len(names) == 16


async def test_import_is_refused_by_hand_after_the_start_and_when_the_feed_fails(bot, guild):
    own = await made(bot, guild, source="own")
    refused = await sports.import_bracket(bot, guild, who(guild, TO), own)
    assert (refused.code, refused.status) == ("not_fed", 409)
    tid = await running(bot, guild)
    late = await sports.import_bracket(bot, guild, who(guild, TO), tid)
    assert (late.code, late.status) == ("wrong_state", 409)
    bot.sports_fetch = Recorded({})
    fresh = await made(bot, guild)
    down = await sports.import_bracket(bot, guild, who(guild, TO), fresh)
    assert (down.ok, down.code, down.status) == (False, "feed_down", 502)
    assert down.message.startswith("NHL had nothing at that address")
    assert not await store_.entrants(bot.db, fresh)
    stranger = await sports.import_bracket(bot, guild, who(guild, STRANGER), fresh)
    assert stranger.code == "not_organiser"


async def test_build_by_hand_seeds_single_elimination_with_byes_and_start_keeps_it(bot, guild):
    tid = await made(bot, guild, source="own")
    for name in ("Bruins", "Leafs", "Habs", "Sens", "Wings"):
        assert (await people.add_entrant(bot, guild, who(guild, TO), tid, name=name)).ok
    built = await sports.build(bot, guild, who(guild, TO), tid)
    assert (built.ok, built.message) == (True, "Built **Stanley Cup** — 4 set(s).")
    _, bracket = await state(bot, tid)
    assert sum(1 for one in bracket.matches.values() if one.state == "bye") == 3
    asked = await sports.build(bot, guild, who(guild, TO), tid)
    assert asked.code == "confirm_rebuild"
    before = sorted(bracket.matches)
    assert (await moves.start(bot, guild, who(guild, TO), tid)).ok
    row, after = await state(bot, tid)
    assert row["state"] == "running" and sorted(after.matches) == before


async def test_start_with_no_sets_builds_through_the_engine(bot, guild):
    tid = await made(bot, guild, source="own")
    for name in ("Bruins", "Leafs"):
        assert (await people.add_entrant(bot, guild, who(guild, TO), tid, name=name)).ok
    assert (await moves.start(bot, guild, who(guild, TO), tid)).ok
    _, bracket = await state(bot, tid)
    assert list(bracket.matches) == ["W1-1"]


async def test_the_feed_decides_every_final_in_round_order_through_the_override(bot, guild):
    tid = await running(bot, guild)
    keys, decided = await sports.applied(bot, guild, tid, nhl_answer())
    assert decided == 15
    row, bracket = await state(bot, tid)
    assert all(
        one.state == "complete" for key, one in bracket.matches.items() if not is_pending(key)
    )
    final = bracket.matches["W4-1"]
    champion = next(one for one in await store_.entrants(bot.db, tid) if one["ext_id"] == "12")
    assert (final.winner, final.score_a, final.score_b) == (champion["id"], 4, 2)
    assert final.confirmed_how == "feed"
    assert {one["decided_by"] for one in (await meta(bot, tid)).values() if one["source_key"]} == {
        "feed"
    }
    logged = [kind for kind, *_ in await rows(bot.db)]
    assert logged.count("brackets.feed_result") == 15
    assert logged.count("brackets.synced") == 1
    again, more = await sports.applied(bot, guild, tid, nhl_answer())
    assert (again, more) == ([], 0)
    assert [kind for kind, *_ in await rows(bot.db)].count("brackets.synced") == 1


async def test_a_live_series_writes_its_score_and_words_without_deciding(bot, guild):
    tid = await running(bot, guild)
    await sports.applied(bot, guild, tid, scheduled_answer())
    answer = scheduled_answer()
    answer.value.games = [
        replace(one, status=LIVE, a_score=2, b_score=1, period_words="BOS leads 2-1")
        if one.source_key == "A"
        else one
        for one in answer.value.games
    ]
    keys, decided = await sports.applied(bot, guild, tid, answer)
    assert (keys, decided) == (["W1-1"], 0)
    _, bracket = await state(bot, tid)
    one = bracket.matches["W1-1"]
    assert (one.state, one.score_a, one.score_b) == ("ready", 2, 1)
    written = (await meta(bot, tid))["W1-1"]
    assert (written["live_status"], written["period_words"]) == ("live", "BOS leads 2-1")


async def test_a_held_set_is_left_alone_until_release_hold(bot, guild):
    tid = await running(bot, guild)
    edited = await sports.edit_set(
        bot, guild, who(guild, TO), tid, "W1-1", {"score_a": 1, "score_b": 0, "reason": "TV"}
    )
    assert (edited.ok, edited.message) == (
        True,
        "Saved W1-1; the feed leaves it alone until Release hold.",
    )
    await sports.applied(bot, guild, tid, nhl_answer())
    _, bracket = await state(bot, tid)
    assert bracket.matches["W1-1"].state == "ready"
    assert ((await meta(bot, tid))["W1-1"]["held"], bracket.matches["W1-1"].score_a) == (1, 1)
    released = await sports.release_hold(bot, guild, who(guild, TO), tid, "W1-1")
    assert released.ok
    again = await sports.release_hold(bot, guild, who(guild, TO), tid, "W1-1")
    assert again.code == "not_held"
    await sports.applied(bot, guild, tid, nhl_answer())
    _, bracket = await state(bot, tid)
    assert bracket.matches["W1-1"].state == "complete"
    logged = await rows(bot.db)
    edits = [details for kind, _, _, details in logged if kind == "brackets.set_edited"]
    assert edits[0]["reason"] == "TV"
    assert [kind for kind, *_ in logged].count("brackets.hold_released") == 1


async def test_a_staff_decide_on_a_sports_set_names_the_winner_and_holds_it(bot, guild):
    tid = await running(bot, guild)
    decided = await sets.override(bot, guild, who(guild, TO), tid, "W1-1", winner="b")
    assert decided.ok, decided.message
    _, bracket = await state(bot, tid)
    one = bracket.matches["W1-1"]
    assert (one.state, one.winner, one.score_a) == ("complete", one.slot_b, None)
    assert (
        (await meta(bot, tid))["W1-1"]["decided_by"],
        (await meta(bot, tid))["W1-1"]["held"],
    ) == (
        "staff",
        1,
    )
    await sports.applied(bot, guild, tid, nhl_answer())
    _, bracket = await state(bot, tid)
    assert bracket.matches["W1-1"].winner == one.slot_b
    reset = await sets.reset(bot, guild, who(guild, TO), tid, "W1-1")
    assert reset.ok and (await meta(bot, tid))["W1-1"]["held"] == 1


async def test_a_feed_failure_is_logged_once_per_streak_and_its_recovery_once(bot, guild):
    tid = await running(bot, guild)
    down = failed("NHL had a server error for the 2026 playoff bracket", NHL_API)
    assert await sports.applied(bot, guild, tid, down) is None
    assert await sports.applied(bot, guild, tid, down) is None
    row, _ = await state(bot, tid)
    assert (row["feed_failures"], row["feed_error"]) == (2, down.why)
    assert row["feed_failed_at"]
    await sports.applied(bot, guild, tid, nhl_answer())
    row, _ = await state(bot, tid)
    assert (row["feed_failures"], row["feed_failed_at"], row["feed_error"]) == (0, None, None)
    assert row["feed_ok_at"]
    logged = await rows(bot.db)
    kinds = [kind for kind, *_ in logged]
    assert (kinds.count("brackets.feed_failed"), kinds.count("brackets.feed_back")) == (1, 1)
    back = next(details for kind, _, _, details in logged if kind == "brackets.feed_back")
    assert back["line"] == "NHL is answering again"


async def test_sync_now_reads_the_feed_and_answers_in_words(bot, guild):
    tid = await running(bot, guild)
    bot.sports_fetch = Recorded(NHL_ROUTES)
    synced = await sports.sync_now(bot, guild, who(guild, TO), tid)
    assert (synced.ok, synced.message) == (True, "Synced **Stanley Cup** — 15 set(s) changed.")
    again = await sports.sync_now(bot, guild, who(guild, TO), tid)
    assert again.message == "Synced **Stanley Cup** — nothing changed."
    bot.sports_fetch = Recorded({})
    down = await sports.sync_now(bot, guild, who(guild, TO), tid)
    assert (down.ok, down.code, down.status) == (False, "feed_down", 502)
    assert "results can be entered by hand" in down.message


async def test_edit_sets_time_status_and_before_the_start_the_teams(bot, guild):
    tid = await imported(bot, guild)
    teams = await store_.entrants(bot.db, tid)
    _, bracket = await state(bot, tid)
    other = next(one["id"] for one in teams if not bracket.matches["W1-1"].holds(one["id"]))
    edited = await sports.edit_set(
        bot,
        guild,
        who(guild, TO),
        tid,
        "W1-1",
        {"scheduled_at": "2026-04-20T23:00:00+00:00", "live_status": "scheduled", "slot_b": other},
    )
    assert edited.ok, edited.message
    _, bracket = await state(bot, tid)
    assert bracket.matches["W1-1"].slot_b == other
    written = (await meta(bot, tid))["W1-1"]
    assert (written["scheduled_at"], written["live_status"], written["held"]) == (
        "2026-04-20T23:00:00+00:00",
        "scheduled",
        1,
    )
    emptied = await sports.edit_set(bot, guild, who(guild, TO), tid, "W1-1", {"slot_b": None})
    assert emptied.ok
    _, bracket = await state(bot, tid)
    assert bracket.matches["W1-1"].state == "waiting"
    assert pending_key("W1-1", "b") in bracket.matches


async def test_edit_refuses_in_words(bot, guild):
    tid = await running(bot, guild)
    nothing = await sports.edit_set(bot, guild, who(guild, TO), tid, "W1-1", {})
    assert (nothing.code, nothing.status) == ("nothing_to_edit", 400)
    bad = await sports.edit_set(bot, guild, who(guild, TO), tid, "W1-1", {"score_a": -1})
    assert (bad.code, bad.status) == ("bad_option", 400)
    assert "score_a" in bad.message
    when = await sports.edit_set(bot, guild, who(guild, TO), tid, "W1-1", {"scheduled_at": "x"})
    assert "scheduled_at" in when.message
    await sets.override(bot, guild, who(guild, TO), tid, "W1-1", winner="a")
    _, bracket = await state(bot, tid)
    played = await sports.edit_set(
        bot, guild, who(guild, TO), tid, "W1-1", {"slot_a": bracket.matches["W1-2"].slot_a}
    )
    assert (played.code, played.status) == ("slot_played", 409)
    stub = await sports.edit_set(
        bot, guild, who(guild, TO), tid, pending_key("W2-1", "a"), {"score_a": 1}
    )
    assert stub.code == "no_set"


async def test_a_corrected_score_on_a_decided_set_keeps_its_winner(bot, guild):
    tid = await running(bot, guild)
    await sets.override(bot, guild, who(guild, TO), tid, "W1-1", winner="a")
    edited = await sports.edit_set(
        bot, guild, who(guild, TO), tid, "W1-1", {"score_a": 4, "score_b": 3}
    )
    assert edited.ok
    _, bracket = await state(bot, tid)
    one = bracket.matches["W1-1"]
    assert (one.winner, one.score_a, one.score_b) == (one.slot_a, 4, 3)


def nfl_answer(results):
    seeds, names = feeds.espn.parse_seeds(payload("espn_standings_nfl"))
    built = nfl.build(seeds, results, "2025")
    built.names.update(names)
    return found(built, "espn")


async def test_the_nfl_rounds_after_the_wild_card_are_named_as_the_feed_reseeds(bot, guild):
    values = {"name": "NFL Playoffs", "kind": "sports", "league": "nfl", "season": "2025"}
    tid = (await moves.create(bot, guild, who(guild, TO), values)).value
    original = feeds.bracket

    async def bracket_of(league, season, *, fetch=None):
        return nfl_answer([])

    feeds.bracket = bracket_of
    try:
        imported_ = await sports.import_bracket(bot, guild, who(guild, TO), tid)
    finally:
        feeds.bracket = original
    assert imported_.ok, imported_.message
    assert (await moves.start(bot, guild, who(guild, TO), tid)).ok
    _, bracket = await state(bot, tid)
    keyed = {value["source_key"]: key for key, value in (await meta(bot, tid)).items()}
    first = bracket.matches[keyed["AFC-DIV-1"]]
    assert first.slot_a is not None and first.slot_b is None and first.state == "waiting"
    assert pending_key(first.key, "b") in bracket.matches
    seeds, _ = feeds.espn.parse_seeds(payload("espn_standings_nfl"))
    playoff = {one for conf in nfl.CONFERENCES for one in seeds[conf][:7]}
    results = nfl.postseason(payload("espn_scoreboard_nfl_post")["events"], playoff)
    pairs = {
        frozenset((one.a_ext_id, one.b_ext_id))
        for one in nfl_answer(results).value.games
        if one.round == 1
    }
    wild_card = [one for one in results if frozenset((one.a_ext_id, one.b_ext_id)) in pairs]
    keys, decided = await sports.applied(bot, guild, tid, nfl_answer(wild_card))
    assert decided == 6
    _, bracket = await state(bot, tid)
    first = bracket.matches[keyed["AFC-DIV-1"]]
    assert None not in (first.slot_a, first.slot_b) and first.state == "ready"
    assert pending_key(first.key, "b") not in bracket.matches
    wildcard = [bracket.matches[keyed[f"AFC-WC-{at}"]] for at in (1, 2, 3)]
    assert all(one.winner_to in (keyed["AFC-DIV-1"], keyed["AFC-DIV-2"]) for one in wildcard)
    assert all(bracket.matches[one.winner_to].holds(one.winner) for one in wildcard)


async def test_a_set_built_by_hand_is_matched_by_its_two_teams_on_the_day(bot, guild):
    from black_bloc import sports_names
    from black_bloc.sports.model import Team

    teams = [
        Team("2", "Boston Celtics", "BOS", "nba"),
        Team("24", "San Antonio Spurs", "SA", "nba"),
    ]
    await sports_names.upsert(bot.db, "team", "nba", "espn", teams)
    values = {"name": "Finals", "kind": "sports", "league": "nba", "season": "2025-26"}
    tid = (await moves.create(bot, guild, who(guild, TO), values)).value
    for ext_id in ("2", "24"):
        added = await people.add_entrant(
            bot, guild, who(guild, TO), tid, ext_source="espn", ext_id=ext_id
        )
        assert added.ok, added.message
    assert (await sports.build(bot, guild, who(guild, TO), tid)).ok
    assert (await moves.start(bot, guild, who(guild, TO), tid)).ok
    game = Game("401", "401", "24", "2", 101, 99, FINAL, "2026-06-05T00:30:00+00:00")
    nothing = found(Bracket(league="nba", season="2025-26"), "nba")
    keys, decided = await sports.applied(bot, guild, tid, nothing, found([game], "espn"))
    assert decided == 1
    _, bracket = await state(bot, tid)
    one = bracket.matches["W1-1"]
    spurs = next(p for p in await store_.entrants(bot.db, tid) if p["ext_id"] == "24")
    assert (one.winner, one.score_a, one.score_b) == (
        spurs["id"],
        *((99, 101) if one.slot_a != spurs["id"] else (101, 99)),
    )
    other = found([replace(game, b_ext_id="9")], "espn")
    assert await sports.applied(bot, guild, tid, nothing, other) == ([], 0)


async def test_a_bracket_run_by_hand_is_never_written_by_a_feed(bot, guild):
    tid = await made(bot, guild, source="own")
    for name in ("Bruins", "Leafs"):
        assert (await people.add_entrant(bot, guild, who(guild, TO), tid, name=name)).ok
    assert (await moves.start(bot, guild, who(guild, TO), tid)).ok
    assert await sports.applied(bot, guild, tid, nhl_answer()) == ([], 0)
    refused = await sports.sync_now(bot, guild, who(guild, TO), tid)
    assert refused.code == "not_fed"
