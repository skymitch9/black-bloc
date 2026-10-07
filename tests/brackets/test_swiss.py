from __future__ import annotations

import pytest

from black_bloc.brackets import play, standings, swiss
from black_bloc.brackets.model import BYE, DQ, SWISS
from tests.brackets.test_play import NOW, built, play_out, seeds, win


def round_of(bracket, round_: int) -> list[tuple]:
    return [(match.slot_a, match.slot_b) for match in bracket.ordered() if match.round == round_]


@pytest.mark.parametrize(("count", "rounds"), [(2, 1), (4, 2), (5, 3), (8, 3), (9, 4), (17, 5)])
def test_the_default_round_count_is_log2_rounded_up(count, rounds):
    assert swiss.rounds_for(count) == rounds
    assert swiss.rounds_for(count, 6) == 6


def test_round_one_pairs_the_top_half_against_the_bottom_half():
    assert round_of(built(8, format=SWISS), 1) == [(1, 5), (2, 6), (3, 7), (4, 8)]


def test_eight_entrants_pair_inside_score_groups_and_finish_in_seed_order():
    bracket = built(8, format=SWISS)
    for key in ("S1-1", "S1-2", "S1-3", "S1-4"):
        bracket = win(bracket, key, "a")
    assert round_of(bracket, 2) == [(1, 3), (2, 4), (5, 7), (6, 8)]
    bracket = play_out(bracket)
    assert round_of(bracket, 3) == [(1, 2), (3, 5), (4, 6), (7, 8)]
    assert standings.placements(bracket) == {entrant: entrant for entrant in seeds(8)}
    rates = {row.entrant: row.opponents_rate for row in standings.table(bracket)}
    assert (rates[2], rates[3], rates[4]) == (0.6667, 0.5556, 0.3333)


def test_five_entrants_get_one_bye_each_round_and_opponents_win_rate_splits_two_points():
    bracket = built(5, format=SWISS)
    assert round_of(bracket, 1) == [(1, 3), (2, 4), (5, None)]
    assert bracket.matches["S1-3"].state == BYE
    bracket = play_out(bracket)
    assert round_of(bracket, 2) == [(1, 2), (5, 3), (4, None)]
    assert round_of(bracket, 3) == [(1, 4), (2, 5), (3, None)]
    rows = {row.entrant: row for row in standings.table(bracket)}
    assert {entrant: row.record.set_wins for entrant, row in rows.items()} == {
        1: 3,
        2: 2,
        3: 2,
        4: 1,
        5: 1,
    }
    assert (rows[2].opponents_rate, rows[3].opponents_rate) == (0.5556, 0.6667)
    assert standings.placements(bracket) == {1: 1, 3: 2, 2: 3, 4: 4, 5: 5}


def test_nine_entrants_play_four_rounds_with_no_rematch_and_one_bye_each_at_most():
    bracket = built(9, format=SWISS)
    assert round_of(bracket, 1) == [(1, 5), (2, 6), (3, 7), (4, 8), (9, None)]
    bracket = play_out(bracket)
    assert swiss.current_round(bracket) == 4
    met = [
        frozenset((match.slot_a, match.slot_b))
        for match in bracket.matches.values()
        if match.slot_b is not None
    ]
    assert len(met) == len(set(met)) == 16
    byes = [match.slot_a for match in bracket.matches.values() if match.state == BYE]
    assert len(byes) == len(set(byes)) == 4
    assert sorted(standings.placements(bracket)) == seeds(9)


def test_a_withdrawn_entrant_is_not_paired_again():
    bracket = built(6, format=SWISS)
    bracket = play.withdraw(bracket, 6, DQ, NOW).bracket
    bracket = play_out(bracket)
    later = [match for match in bracket.matches.values() if match.round > 1]
    assert all(6 not in (match.slot_a, match.slot_b) for match in later)


def test_the_pairing_falls_back_to_top_down_when_every_pairing_is_a_rematch():
    played = {
        frozenset((1, 2)),
        frozenset((3, 4)),
        frozenset((1, 3)),
        frozenset((2, 4)),
        frozenset((1, 4)),
        frozenset((2, 3)),
    }
    assert swiss.pairings([1, 2, 3, 4], dict.fromkeys(range(1, 5), 0), played) == [(1, 2), (3, 4)]


def test_a_set_number_of_rounds_is_kept():
    bracket = play_out(built(4, format=SWISS, swiss_rounds=3))
    assert swiss.current_round(bracket) == 3
