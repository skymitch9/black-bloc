from __future__ import annotations

from black_bloc.brackets import play
from black_bloc.brackets.model import BYE, COMPLETE, READY, WAITING
from black_bloc.brackets.sports_shape import (
    Planned,
    hold_open,
    is_pending,
    let_go,
    pending_key,
    positions,
    shaped,
)

FOUR = [
    Planned("A", 1, 1, 2, 7),
    Planned("B", 1, 3, 4, 7),
    Planned("F", 2, None, None, 7),
]
LINKS = {"A": ("F", "a"), "B": ("F", "b")}


def test_positions_walk_down_from_the_final_by_the_slot_each_set_feeds():
    assert positions(FOUR, LINKS) == {"F": 1, "A": 1, "B": 2}
    assert positions(FOUR, {"A": ("F", "b"), "B": ("F", "a")}) == {"F": 1, "A": 2, "B": 1}


def test_a_set_the_walk_misses_takes_the_next_free_place_of_its_round_in_feed_order():
    planned = [*FOUR, Planned("X", 1, 5, 6), Planned("Y", 1, 7, 8)]
    found = positions(planned, LINKS)
    assert (found["A"], found["B"], found["X"], found["Y"]) == (1, 2, 3, 4)


def test_a_play_in_set_feeds_the_round_one_slot_it_names():
    planned = [
        Planned("P", 0, 5, 6),
        Planned("A", 1, 1, None),
        Planned("B", 1, 3, 4),
        Planned("F", 2, None, None),
    ]
    bracket, sources = shaped(planned, {"P": ("A", "b"), **LINKS})
    keys = {source: key for key, source in sources.items()}
    assert keys == {"P": "W0-2", "A": "W1-1", "B": "W1-2", "F": "W2-1"}
    assert (bracket.matches["W0-2"].winner_to, bracket.matches["W0-2"].winner_slot) == (
        "W1-1",
        "b",
    )
    play.settle(bracket)
    assert bracket.matches["W1-1"].state == WAITING
    assert bracket.matches["W0-2"].state == READY


def test_the_sets_carry_the_feeds_links_best_of_and_places():
    bracket, _ = shaped(FOUR, LINKS)
    first, final = bracket.matches["W1-1"], bracket.matches["W2-1"]
    assert (first.winner_to, first.winner_slot, first.best_of) == ("W2-1", "a", 7)
    assert (first.winner_place, first.loser_place) == (None, 3)
    assert (final.winner_place, final.loser_place) == (1, 2)
    assert bracket.entrants == [1, 2, 3, 4]


def test_a_link_to_a_game_the_feed_lacks_is_dropped():
    bracket, _ = shaped(FOUR[:2], LINKS)
    assert bracket.matches["W1-1"].winner_to is None


def test_a_slot_the_feed_has_not_named_is_held_open_not_byed():
    planned = [Planned("D", 2, 1, None), Planned("W", 1, 2, 3)]
    bracket, _ = shaped(planned, {})
    play.settle(bracket)
    held = bracket.matches[pending_key("W2-1", "b")]
    assert (held.state, held.winner_to, held.winner_slot) == (BYE, "W2-1", "b")
    assert bracket.matches["W2-1"].state == WAITING
    assert is_pending(held) and is_pending(held.key) and not is_pending("W2-1")


def test_filling_the_slot_lets_the_pending_feeder_go_and_the_set_wakes():
    bracket, _ = shaped([Planned("D", 2, 1, None)], {})
    play.settle(bracket)
    play.put(bracket.matches["W2-1"], "b", 9)
    assert let_go(bracket, "W2-1", "b") == pending_key("W2-1", "b")
    assert let_go(bracket, "W2-1", "b") is None
    play.settle(bracket)
    assert bracket.matches["W2-1"].state == READY


def test_hold_open_adds_a_feeder_only_where_nothing_feeds_the_slot():
    bracket, _ = shaped(FOUR, LINKS)
    assert hold_open(bracket) == []
    bracket.matches["W1-1"].slot_a = None
    assert hold_open(bracket) == [pending_key("W1-1", "a")]


def test_a_feed_final_through_override_advances_by_the_stored_link():
    bracket, _ = shaped(FOUR, LINKS)
    play.settle(bracket)
    moved = play.override(bracket, "W1-1", None, "now", score_a=4, score_b=2, winner="a", free=True)
    assert moved.bracket.matches["W1-1"].state == COMPLETE
    assert moved.bracket.matches["W2-1"].slot_a == 1
