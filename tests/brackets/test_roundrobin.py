from __future__ import annotations

from itertools import combinations

import pytest

from black_bloc.brackets import play, roundrobin, standings
from black_bloc.brackets.model import READY, ROUND_ROBIN, A, B
from tests.brackets.test_play import NOW, TO, built, play_out, seeds


def test_three_entrants_play_three_rounds_with_one_sitting_out_each():
    assert roundrobin.schedule([1, 2, 3]) == [[(2, 3)], [(1, 3)], [(1, 2)]]


def test_four_entrants_play_three_rounds_of_two():
    assert roundrobin.schedule([1, 2, 3, 4]) == [
        [(1, 4), (2, 3)],
        [(1, 3), (4, 2)],
        [(1, 2), (3, 4)],
    ]


@pytest.mark.parametrize(("count", "rounds"), [(3, 3), (4, 3), (5, 5), (6, 5)])
def test_every_pair_meets_exactly_once(count, rounds):
    found = roundrobin.schedule(seeds(count))
    met = [frozenset(pair) for one in found for pair in one]
    assert len(found) == rounds
    assert sorted(met, key=sorted) == sorted(
        (frozenset(pair) for pair in combinations(seeds(count), 2)), key=sorted
    )
    assert len(met) == roundrobin.match_count(count)
    for one in found:
        playing = [entrant for pair in one for entrant in pair]
        assert len(playing) == len(set(playing))


def test_every_set_is_ready_from_the_start():
    bracket = built(4, format=ROUND_ROBIN)
    assert [match.key for match in bracket.ordered()] == [
        "R1-1",
        "R1-2",
        "R2-1",
        "R2-2",
        "R3-1",
        "R3-2",
    ]
    assert {match.state for match in bracket.matches.values()} == {READY}


def scored(bracket, key: str, score_a: int, score_b: int):
    return play.override(bracket, key, TO, NOW, score_a=score_a, score_b=score_b).bracket


def test_a_three_way_cycle_is_split_by_games_then_head_to_head():
    bracket = built(3, format=ROUND_ROBIN)
    bracket = scored(bracket, "R1-1", 2, 1)
    bracket = scored(bracket, "R2-1", 1, 2)
    bracket = scored(bracket, "R3-1", 2, 0)
    rows = {row.entrant: row for row in standings.table(bracket)}
    assert {
        entrant: (row.record.set_wins, row.record.game_wins) for entrant, row in rows.items()
    } == {
        1: (1, 3),
        2: (1, 2),
        3: (1, 3),
    }
    assert standings.placements(bracket) == {3: 1, 1: 2, 2: 3}


def cycle(bracket):
    """1 beats everyone; 2, 3 and 4 beat each other in a ring, every set 2-1."""
    for match in bracket.ordered():
        a, b = match.slot_a, match.slot_b
        ring = {(2, 3), (3, 4), (4, 2)}
        if 1 in (a, b):
            side = A if a == 1 else B
        else:
            side = A if (a, b) in ring else B
        bracket = scored(bracket, match.key, *((2, 1) if side == A else (1, 2)))
    return bracket


def test_a_tie_nothing_breaks_shares_the_place():
    bracket = cycle(built(4, format=ROUND_ROBIN))
    assert standings.placements(bracket) == {1: 1, 2: 2, 3: 2, 4: 2}


def test_the_tos_order_breaks_a_tie_only_when_it_names_everyone_in_it():
    bracket = cycle(built(4, format=ROUND_ROBIN))
    bracket.final_order = [4, 2]
    assert standings.placements(bracket) == {1: 1, 2: 2, 3: 2, 4: 2}
    bracket.final_order = [4, 2, 3]
    assert standings.placements(bracket) == {1: 1, 4: 2, 2: 3, 3: 4}


@pytest.mark.parametrize("count", [3, 4, 5, 6])
def test_the_higher_seed_winning_every_set_places_the_field_in_seed_order(count):
    bracket = play_out(built(count, format=ROUND_ROBIN))
    assert standings.placements(bracket) == {entrant: entrant for entrant in seeds(count)}
    assert [row.record.set_wins for row in standings.table(bracket)] == list(
        range(count - 1, -1, -1)
    )


def test_places_wait_until_every_set_is_played():
    bracket = scored(built(3, format=ROUND_ROBIN), "R1-1", 2, 0)
    assert standings.placements(bracket) == {}
    assert [row.entrant for row in standings.table(bracket)] == [2, 1, 3]
