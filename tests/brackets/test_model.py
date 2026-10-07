from __future__ import annotations

from black_bloc.brackets.model import (
    GRAND,
    LOSERS,
    RESULT_FIELDS,
    WINNERS,
    Match,
    cleared,
    key_of,
    order_key,
)


def test_keys_read_side_round_and_position():
    assert key_of(WINNERS, 2, 3) == "W2-3"
    assert key_of(LOSERS, 1, 1) == "L1-1"
    assert key_of(GRAND, 2, 1) == "G2-1"


def test_play_order_puts_each_losers_round_after_the_winners_round_that_feeds_it():
    sets = [
        Match(key_of(side, round_, 1), side, round_, 1, 3)
        for side, round_ in ((WINNERS, 1), (WINNERS, 2), (LOSERS, 1), (LOSERS, 2), (GRAND, 1))
    ]
    assert [one.key for one in sorted(sets, key=order_key)] == [
        "W1-1",
        "L1-1",
        "W2-1",
        "L2-1",
        "G1-1",
    ]


def test_clearing_a_result_keeps_the_structure_and_the_slots():
    match = Match(
        "W1-1", WINNERS, 1, 1, 3, slot_a=4, slot_b=5, winner_to="W2-1", score_a=2, winner=4
    )
    fresh = cleared(match)
    assert (fresh.slot_a, fresh.slot_b, fresh.winner_to) == (4, 5, "W2-1")
    assert all(getattr(fresh, name) is None for name in RESULT_FIELDS)


def test_a_set_knows_its_sides():
    match = Match("W1-1", WINNERS, 1, 1, 3, slot_a=4, slot_b=5)
    assert (match.side_of(4), match.side_of(5), match.side_of(6), match.side_of(None)) == (
        "a",
        "b",
        None,
        None,
    )
    assert (match.other(4), match.other(5), match.other(6)) == (5, 4, None)
    assert match.holds(5) and not match.holds(None)
