from __future__ import annotations

import random

import pytest

from black_bloc.brackets import elimination, play, standings
from black_bloc.brackets.model import (
    BYE,
    COMPLETE,
    DOUBLE,
    LOSERS,
    READY,
    SINGLE,
    VOID,
    WINNERS,
    A,
    B,
    Options,
)
from tests.brackets.test_play import NOW, built, play_out, seeds, win


def drops(bracket) -> dict[str, tuple[str, str]]:
    return {
        key: (match.loser_to, match.loser_slot)
        for key, match in bracket.matches.items()
        if match.side == WINNERS
    }


def pairs(bracket, side: str, round_: int) -> list[tuple]:
    return [
        (match.slot_a, match.slot_b)
        for match in bracket.ordered()
        if match.side == side and match.round == round_
    ]


SINGLE_PLACES = {
    2: {1: 1, 2: 2},
    3: {1: 1, 2: 2, 3: 3},
    4: {1: 1, 2: 2, 3: 3, 4: 3},
    5: {1: 1, 2: 2, 3: 3, 4: 3, 5: 5},
    7: {1: 1, 2: 2, 3: 3, 4: 3, 5: 5, 6: 5, 7: 5},
    8: {1: 1, 2: 2, 3: 3, 4: 3, 5: 5, 6: 5, 7: 5, 8: 5},
    9: {1: 1, 2: 2, 3: 3, 4: 3, 5: 5, 6: 5, 7: 5, 8: 5, 9: 9},
    16: {1: 1, 2: 2, 3: 3, 4: 3} | dict.fromkeys(range(5, 9), 5) | dict.fromkeys(range(9, 17), 9),
    17: {1: 1, 2: 2, 3: 3, 4: 3}
    | dict.fromkeys(range(5, 9), 5)
    | dict.fromkeys(range(9, 17), 9)
    | {17: 17},
}

DOUBLE_PLACES = {
    2: {1: 1, 2: 2},
    3: {1: 1, 2: 2, 3: 3},
    4: {1: 1, 2: 2, 3: 3, 4: 4},
    5: {1: 1, 2: 2, 3: 3, 4: 4, 5: 5},
    7: {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 5, 7: 7},
    8: {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 5, 7: 7, 8: 7},
    9: {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 5, 7: 7, 8: 7, 9: 9},
    16: {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 5, 7: 7, 8: 7}
    | dict.fromkeys(range(9, 13), 9)
    | dict.fromkeys(range(13, 17), 13),
    17: {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 5, 7: 7, 8: 7}
    | dict.fromkeys(range(9, 13), 9)
    | dict.fromkeys(range(13, 17), 13)
    | {17: 17},
}


@pytest.mark.parametrize("count", sorted(SINGLE_PLACES))
def test_single_elimination_places_when_the_higher_seed_always_wins(count):
    assert standings.placements(play_out(built(count, format=SINGLE))) == SINGLE_PLACES[count]


@pytest.mark.parametrize("count", sorted(DOUBLE_PLACES))
def test_double_elimination_places_when_the_higher_seed_always_wins(count):
    assert standings.placements(play_out(built(count, format=DOUBLE))) == DOUBLE_PLACES[count]


def test_byes_go_to_the_top_seeds_and_the_first_round_is_one_v_n():
    assert pairs(built(8, format=SINGLE), WINNERS, 1) == [(1, 8), (4, 5), (2, 7), (3, 6)]
    five = built(5, format=SINGLE)
    assert pairs(five, WINNERS, 1) == [(1, None), (4, 5), (2, None), (3, None)]
    assert [five.matches[f"W1-{at}"].state for at in range(1, 5)] == [BYE, READY, BYE, BYE]
    assert pairs(five, WINNERS, 2) == [(1, None), (2, 3)]


def test_seventeen_entrants_make_a_bracket_of_thirty_two_with_one_first_round_set():
    bracket = built(17, format=SINGLE)
    first = [match for match in bracket.ordered() if match.round == 1]
    assert len(first) == 16
    assert [(match.slot_a, match.slot_b) for match in first if match.state == READY] == [(16, 17)]


def test_the_third_place_match_takes_both_semifinal_losers():
    bracket = play_out(built(4, format=SINGLE, third_place=True))
    third = bracket.matches["T1-1"]
    assert (third.slot_a, third.slot_b, third.winner) == (4, 3, 3)
    assert standings.placements(bracket) == {1: 1, 2: 2, 3: 3, 4: 4}


def test_with_three_entrants_the_third_place_match_is_a_bye_for_the_only_semifinal_loser():
    bracket = play_out(built(3, format=SINGLE, third_place=True))
    assert bracket.matches["T1-1"].state == BYE
    assert standings.placements(bracket) == {1: 1, 2: 2, 3: 3}


def test_eight_entrant_double_elimination_drop_pattern():
    bracket = built(8, format=DOUBLE)
    assert drops(bracket) == {
        "W1-1": ("L1-1", A),
        "W1-2": ("L1-1", B),
        "W1-3": ("L1-2", A),
        "W1-4": ("L1-2", B),
        "W2-1": ("L2-2", B),
        "W2-2": ("L2-1", B),
        "W3-1": ("L4-1", B),
    }
    assert [key for key in bracket.matches if key.startswith("L")] == [
        "L1-1",
        "L1-2",
        "L2-1",
        "L2-2",
        "L3-1",
        "L4-1",
    ]
    assert bracket.matches["L4-1"].winner_to == "G1-1"
    assert bracket.matches["W3-1"].winner_to == "G1-1"


def test_sixteen_entrant_double_elimination_drop_pattern():
    found = drops(built(16, format=DOUBLE))
    assert {key: found[key] for key in found if not key.startswith("W1-")} == {
        "W2-1": ("L2-2", B),
        "W2-2": ("L2-1", B),
        "W2-3": ("L2-4", B),
        "W2-4": ("L2-3", B),
        "W3-1": ("L4-2", B),
        "W3-2": ("L4-1", B),
        "W4-1": ("L6-1", B),
    }
    assert {found[f"W1-{at}"] for at in range(1, 9)} == {
        (f"L1-{(at + 1) // 2}", A if at % 2 else B) for at in range(1, 9)
    }


def test_the_losers_rounds_and_their_places():
    assert [elimination.losers_matches(16, r) for r in range(1, 7)] == [4, 4, 2, 2, 1, 1]
    assert [elimination.losers_place(16, r) for r in range(1, 7)] == [13, 9, 7, 5, 4, 3]
    assert [elimination.losers_place(32, r) for r in range(1, 9)] == [25, 17, 13, 9, 7, 5, 4, 3]


def history(bracket) -> list[tuple[str, int, int]]:
    return [
        (match.key, match.winner, match.loser)
        for match in bracket.ordered()
        if match.state == COMPLETE
    ]


@pytest.mark.parametrize("count", [8, 16, 32, 64])
def test_a_dropped_player_never_meets_anyone_they_have_already_played_on_arrival(count):
    """The flip keeps a drop away from its own half; only the last, forced drop can rematch."""
    rng = random.Random(count)
    for _ in range(max(3, 256 // count)):
        bracket = play_out(built(count, format=DOUBLE), lambda match: rng.choice((A, B)))
        met: dict[int, set[int]] = {entrant: set() for entrant in seeds(count)}
        for match in bracket.ordered():
            if match.state != COMPLETE:
                continue
            arriving = match.slot_b if match.side == LOSERS and match.round % 2 == 0 else None
            if arriving is not None and elimination.losers_matches(count, match.round) > 1:
                assert match.slot_a not in met[arriving], (match.key, arriving, match.slot_a)
            met[match.slot_a].add(match.slot_b)
            met[match.slot_b].add(match.slot_a)


def test_best_of_rises_from_top_eight_and_for_the_grand_final():
    bracket = built(
        16,
        format=DOUBLE,
        best_of=3,
        best_of_from_round=8,
        best_of_late=5,
        best_of_finals=7,
    )
    lengths = {(match.side, match.round): match.best_of for match in bracket.matches.values()}
    assert lengths == {
        (WINNERS, 1): 3,
        (WINNERS, 2): 3,
        (WINNERS, 3): 5,
        (WINNERS, 4): 5,
        (LOSERS, 1): 3,
        (LOSERS, 2): 3,
        (LOSERS, 3): 5,
        (LOSERS, 4): 5,
        (LOSERS, 5): 5,
        (LOSERS, 6): 5,
        ("grand", 1): 7,
        ("grand", 2): 7,
    }
    alive = {match.key: match.alive for match in bracket.matches.values()}
    assert (alive["W1-1"], alive["W2-1"], alive["L1-1"], alive["L2-1"]) == (16, 16, 16, 12)
    assert (alive["W3-1"], alive["L3-1"], alive["L4-1"], alive["L6-1"]) == (8, 8, 6, 3)


def test_single_elimination_best_of_from_top_eight():
    bracket = built(16, format=SINGLE, best_of_from_round=8, best_of_finals=5)
    assert [bracket.matches[f"W{r}-1"].best_of for r in range(1, 5)] == [3, 5, 5, 5]


def test_a_losers_round_with_no_one_in_it_is_void_and_the_drop_walks_through():
    bracket = built(5, format=DOUBLE)
    assert bracket.matches["L1-1"].state == "waiting"
    assert bracket.matches["L1-2"].state == VOID
    bracket = win(bracket, "W1-2", A)
    assert (bracket.matches["L1-1"].state, bracket.matches["L1-1"].winner) == (BYE, 5)
    assert bracket.matches["L2-1"].slot_a == 5


def test_building_twice_from_the_same_seeds_gives_the_same_bracket():
    first = play.build(seeds(12), Options(format=DOUBLE), NOW).bracket
    again = play.build(seeds(12), Options(format=DOUBLE), NOW).bracket
    assert first == again
