from __future__ import annotations

from datetime import UTC, datetime

import pytest

from black_bloc.brackets import play, pools, standings
from black_bloc.brackets.model import (
    BYE,
    CALLED,
    COMPLETE,
    DOUBLE,
    DQ,
    FINAL,
    POOLS,
    READY,
    REPORTED,
    ROUND_ROBIN,
    SINGLE,
    SWISS,
    A,
    B,
    BracketError,
    Options,
    Plan,
)
from tests.brackets.test_play import NOW, TO, score_for, seeds


def made(count, *, pools_=2, advance=2, losers_from=None, final=DOUBLE, fmt=ROUND_ROBIN, **plan):
    options = Options(format=final, best_of_finals=3)
    found = Plan(fmt, pools_, advance, losers_from, **plan)
    return pools.build(seeds(count), options, found, NOW).bracket


def win(bracket, key, side):
    score_a, score_b = score_for(bracket.matches[key].best_of, side)
    return pools.override(bracket, key, TO, NOW, score_a=score_a, score_b=score_b).bracket


def higher(match):
    return A if match.slot_a < match.slot_b else B


def play_out(bracket, phase=None, decide=higher):
    while True:
        ready = [
            one
            for one in bracket.ordered()
            if one.state in (READY, CALLED) and (phase is None or one.phase == phase)
        ]
        if not ready:
            return bracket
        bracket = win(bracket, ready[0].key, decide(ready[0]))


def seats(bracket, *keys):
    return [(bracket.matches[key].slot_a, bracket.matches[key].slot_b) for key in keys]


def by_place(placed):
    return [placed[one] for one in sorted(placed)]


def test_seeds_are_dealt_in_snake_order():
    assert pools.split(seeds(8), 2) == [[1, 4, 5, 8], [2, 3, 6, 7]]
    assert pools.split(seeds(9), 2) == [[1, 4, 5, 8, 9], [2, 3, 6, 7]]
    assert pools.split(seeds(12), 3) == [[1, 6, 7, 12], [2, 5, 8, 11], [3, 4, 9, 10]]
    assert pools.split(seeds(16), 4) == [
        [1, 8, 9, 16],
        [2, 7, 10, 15],
        [3, 6, 11, 14],
        [4, 5, 12, 13],
    ]


def test_a_pool_key_carries_its_letter_and_reads_back():
    assert pools.prefixed(2, "R1-1") == "B.R1-1"
    assert (pools.pool_of("B.R1-1"), pools.inner("B.R1-1")) == (2, "R1-1")
    assert pools.pool_of("W1-1") is None and pools.inner("W1-1") == "W1-1"


def test_the_pools_are_built_one_round_robin_each_and_nothing_else():
    bracket = made(8)
    assert {one.phase for one in bracket.matches.values()} == {POOLS}
    assert sorted({one.pool for one in bracket.matches.values()}) == [1, 2]
    assert len(bracket.matches) == 12
    assert [one.key for one in bracket.ordered()][:2] == ["A.R1-1", "A.R1-2"]
    assert {one.state for one in bracket.matches.values()} == {READY}


def test_eight_in_two_pools_of_four_send_the_top_two_into_a_four_player_double():
    bracket = play_out(made(8))
    assert pools.pools_finished(bracket) and not pools.finished(bracket)
    moved = pools.advance(bracket, NOW)
    after = moved.bracket
    assert moved.changed and all(after.matches[key].phase == FINAL for key in moved.changed)
    assert seats(after, "W1-1", "W1-2") == [(1, 3), (2, 4)]
    final = play_out(after)
    assert pools.finished(final)
    assert pools.placements(final) == {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 5, 7: 7, 8: 7}


def test_sixteen_in_four_pools_send_the_seconds_into_the_losers_bracket():
    bracket = play_out(made(16, pools_=4, losers_from=2))
    after = pools.advance(bracket, NOW).bracket
    assert seats(after, "W2-1", "W2-2") == [(1, 4), (2, 3)]
    assert seats(after, "L1-1", "L1-2") == [(8, 5), (7, 6)]
    assert not any(one.key.startswith("W1-") for one in after.matches.values())
    assert after.matches["L1-1"].loser_place == 7 and after.matches["L2-1"].loser_place == 5
    placed = pools.placements(play_out(after))
    assert sorted(placed.values()) == [1, 2, 3, 4, 5, 5, 7, 7, 9, 9, 9, 9, 13, 13, 13, 13]
    assert {placed[one] for one in (9, 10, 11, 12)} == {9}
    assert {placed[one] for one in (13, 14, 15, 16)} == {13}


def test_twelve_in_three_pools_make_a_six_player_bracket_with_byes_and_no_pool_rematch():
    bracket = play_out(made(12, pools_=3))
    after = pools.advance(bracket, NOW).bracket
    assert after.matches["W1-1"].state == BYE and after.matches["W1-3"].state == BYE
    assert seats(after, "W1-2", "W1-4") == [(6, 4), (3, 5)]
    home = {one: at for at, found in enumerate(pools.split(seeds(12), 3)) for one in found}
    for match in after.matches.values():
        if match.phase == FINAL and match.slot_a and match.slot_b and match.round == 1:
            assert home[match.slot_a] != home[match.slot_b]
    placed = pools.placements(play_out(after))
    assert sorted(placed.values()) == [1, 2, 3, 4, 5, 5, 7, 7, 7, 10, 10, 10]


def test_twelve_in_three_pools_with_seconds_to_losers_place_one_to_six_then_the_rest():
    bracket = play_out(made(12, pools_=3, losers_from=2))
    after = pools.advance(bracket, NOW).bracket
    assert seats(after, "W2-1", "W2-2", "L1-1", "L1-2") == [(1, None), (2, 3), (6, None), (5, 4)]
    placed = pools.placements(play_out(after))
    assert sorted(placed.values()) == [1, 2, 3, 4, 5, 6, 7, 7, 7, 10, 10, 10]


def test_nine_in_two_pools_of_five_and_four_into_single_elimination():
    bracket = made(9, final=SINGLE)
    assert [len(one.entrants) for one in pools.pool_parts(bracket)] == [5, 4]
    after = pools.advance(play_out(bracket), NOW).bracket
    assert seats(after, "W1-1", "W1-2") == [(1, 3), (2, 4)]
    placed = pools.placements(play_out(after))
    assert placed == {1: 1, 2: 2, 3: 3, 4: 3, 5: 5, 6: 5, 7: 7, 8: 7, 9: 9}


def test_single_elimination_ignores_losers_from():
    after = pools.advance(play_out(made(8, final=SINGLE, losers_from=2)), NOW).bracket
    assert seats(after, "W1-1", "W1-2") == [(1, 3), (2, 4)]


def test_swiss_pools_pair_inside_each_pool_round_by_round():
    bracket = made(16, fmt=SWISS)
    first = [one for one in bracket.ordered() if one.round == 1]
    assert len(first) == 8 and {one.pool for one in first} == {1, 2}
    assert seats(bracket, "A.S1-1") == [(1, 9)]
    bracket = play_out(bracket)
    assert max(one.round for one in bracket.matches.values()) == 3
    assert pools.pools_finished(bracket)
    after = pools.advance(bracket, NOW).bracket
    assert sorted(one for one in pools.final_part(after).entrants) == [1, 2, 3, 4]


def cycle(bracket, pool, beats):
    for key, match in list(bracket.matches.items()):
        if match.pool != pool or match.state != READY:
            continue
        pair = (match.slot_a, match.slot_b)
        winner = next((up for up, down in beats if {up, down} == set(pair)), min(pair))
        bracket = win(bracket, key, A if match.slot_a == winner else B)
    return bracket


def test_a_tie_on_the_cut_line_is_refused_until_the_organiser_orders_it():
    bracket = made(6, pools_=2, advance=1)
    a_pool = pools.split(seeds(6), 2)[0]
    x, y, z = a_pool
    bracket = cycle(bracket, 1, [(x, y), (y, z), (z, x)])
    bracket = play_out(bracket)
    with pytest.raises(BracketError) as raised:
        pools.advance(bracket, NOW)
    assert raised.value.code == "pool_tie"
    assert sorted(raised.value.fields["tied"]) == sorted(a_pool)
    bracket.final_order = [z, x, y]
    after = pools.advance(bracket, NOW).bracket
    assert z in pools.final_part(after).entrants and x not in pools.final_part(after).entrants


def test_advance_is_refused_while_a_pool_is_still_playing():
    bracket = play_out(made(8), decide=higher)
    bracket = pools.reset(bracket, "A.R3-1", TO, NOW).bracket
    with pytest.raises(BracketError) as raised:
        pools.advance(bracket, NOW)
    assert raised.value.code == "pools_unfinished" and raised.value.fields["open"] == 1


def test_a_pool_set_cannot_be_changed_once_the_final_is_built_until_back_to_pools():
    after = pools.advance(play_out(made(8)), NOW).bracket
    for move in (
        lambda: pools.reset(after, "A.R1-1", TO, NOW),
        lambda: pools.override(after, "A.R1-1", TO, NOW, score_a=0, score_b=2),
    ):
        with pytest.raises(BracketError) as raised:
            move()
        assert raised.value.code == "pools_closed" and raised.value.fields["set"] == "A.R1-1"
    back = pools.unadvance(after)
    assert back.changed == [] and set(back.removed) == {
        key for key, one in after.matches.items() if one.phase == FINAL
    }
    assert pools.reset(back.bracket, "A.R1-1", TO, NOW).changed == ["A.R1-1"]


def test_back_to_pools_is_refused_once_a_final_set_has_a_result():
    after = pools.advance(play_out(made(8)), NOW).bracket
    reported = pools.report(after, "W1-1", A, 2, 0, 1, NOW).bracket
    assert reported.matches["W1-1"].state == REPORTED
    with pytest.raises(BracketError) as raised:
        pools.unadvance(reported)
    assert raised.value.code == "final_played" and raised.value.fields["set"] == "W1-1"


def test_a_set_move_inside_a_pool_names_the_set_with_its_pool():
    bracket = made(8)
    moved = pools.report(bracket, "B.R1-1", A, 2, 1, 2, NOW)
    assert moved.changed == ["B.R1-1"]
    with pytest.raises(BracketError) as raised:
        pools.dispute(moved.bracket, "B.R1-1", A, 2, None, NOW)
    assert raised.value.code == "own_report" and raised.value.fields["set"] == "B.R1-1"
    with pytest.raises(BracketError) as raised:
        pools.call(bracket, "C.R1-1", TO, NOW)
    assert raised.value.code == "no_set"


def test_a_dq_in_pools_forfeits_the_pool_and_takes_them_out_of_advancing():
    bracket = made(8)
    moved = pools.withdraw(bracket, 1, DQ, NOW)
    after = moved.bracket
    mine = [one for one in after.matches.values() if one.holds(1)]
    assert {one.forfeit for one in mine} == {DQ} and {one.state for one in mine} == {COMPLETE}
    after = pools.advance(play_out(after), NOW).bracket
    assert 1 not in pools.final_part(after).entrants
    assert set(pools.final_part(after).entrants) == {2, 3, 4, 5}
    placed = pools.placements(play_out(after))
    assert placed[1] == 8 and sorted(placed.values()) == [1, 2, 3, 4, 5, 5, 7, 8]


def test_a_dq_in_the_final_forfeits_the_final_only():
    after = pools.advance(play_out(made(8)), NOW).bracket
    moved = pools.withdraw(after, 3, DQ, NOW)
    assert all(moved.bracket.matches[key].phase == FINAL for key in moved.changed)
    assert moved.bracket.matches["W1-1"].winner == 1


def test_withdraw_and_reinstate_refuse_like_the_single_bracket():
    bracket = made(8)
    with pytest.raises(BracketError) as raised:
        pools.withdraw(bracket, 99, DQ, NOW)
    assert raised.value.code == "not_in_bracket"
    with pytest.raises(BracketError) as raised:
        pools.reinstate(bracket, 1, NOW)
    assert raised.value.code == "not_out"
    out = pools.withdraw(bracket, 1, DQ, NOW).bracket
    with pytest.raises(BracketError) as raised:
        pools.withdraw(out, 1, DQ, NOW)
    assert raised.value.code == "already_out"
    assert pools.reinstate(out, 1, NOW).bracket.withdrawn == {}


def test_the_plan_is_checked_against_the_field():
    cases = [
        (dict(pools_=4), 6, "too_few_for_pools"),
        (dict(advance=5), 8, "advance_too_many"),
        (dict(pools_=1, advance=1), 4, "advance_too_many"),
        (dict(losers_from=3), 8, "bad_losers_from"),
        (dict(losers_from=1), 8, "bad_losers_from"),
        (dict(fmt=SWISS, swiss_rounds=4), 8, "too_many_pool_rounds"),
        (dict(final=SWISS), 8, "pools_need_elimination"),
    ]
    for plan, count, code in cases:
        with pytest.raises(BracketError) as raised:
            made(count, **plan)
        assert raised.value.code == code


def test_waiting_on_says_the_pool_set_then_the_final():
    bracket = made(8)
    first = pools.waiting_on(bracket)
    assert first[1]["set"].startswith("A.") and first[2]["set"].startswith("B.")
    done = play_out(bracket)
    assert {one["what"] for one in pools.waiting_on(done).values()} == {pools.WAITS_FOR_FINAL}
    after = pools.advance(done, NOW).bracket
    waits = pools.waiting_on(after)
    assert waits[1]["set"] == "W1-1" and waits[5]["what"] == standings.DONE


def test_the_sets_to_play_count_the_pools_then_the_final():
    bracket = made(8)
    assert pools.sets_to_play(bracket) == (12, 12)
    after = pools.advance(play_out(bracket), NOW).bracket
    assert pools.sets_to_play(after) == play.sets_to_play(pools.final_part(after))


def test_the_confirm_sweep_reaches_pool_sets():
    bracket = made(8)
    reported = pools.report(bracket, "A.R1-1", A, 2, 1, 1, "2026-10-07T00:00:00+00:00").bracket
    swept = pools.confirm_due(reported, datetime(2026, 10, 8, tzinfo=UTC), 12)
    assert swept.changed == ["A.R1-1"] and swept.bracket.matches["A.R1-1"].state == COMPLETE


def test_a_bracket_without_pools_goes_straight_through_to_play():
    single = play.build(seeds(4), Options(format=SINGLE), NOW).bracket
    assert pools.report(single, "W1-1", A, 2, 0, 1, NOW).changed == ["W1-1"]
    assert pools.placements(single) == {}
    assert pools.finished(single) is False
