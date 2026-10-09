from __future__ import annotations

from datetime import UTC, datetime, timedelta

from black_bloc.points.bounty import Bounty, game_key, live_at, matches, points_for, with_bonus
from black_bloc.points.model import EXTRA, MULTIPLIER

NOON = datetime(2026, 10, 9, 12, tzinfo=UTC)


def bounty(id_, kind, amount, *games, start=-1, end=1, active=True):
    return Bounty(
        id_,
        f"bounty {id_}",
        tuple(games) or ("Celeste",),
        kind,
        amount,
        NOON + timedelta(hours=start) if start is not None else None,
        NOON + timedelta(hours=end) if end is not None else None,
        active,
    )


def test_a_multiplier_multiplies_and_extra_adds():
    assert with_bonus(10, bounty(1, MULTIPLIER, 2)) == 20
    assert with_bonus(10, bounty(1, MULTIPLIER, 1.25)) == 13
    assert with_bonus(10, bounty(1, EXTRA, 15)) == 25


def test_a_bounty_counts_only_inside_its_window_and_while_active():
    open_one = bounty(1, EXTRA, 5)
    assert live_at(open_one, NOON)
    assert live_at(open_one, NOON - timedelta(hours=1))
    assert not live_at(open_one, NOON + timedelta(hours=1))
    assert not live_at(bounty(2, EXTRA, 5, active=False), NOON)
    assert not live_at(bounty(3, EXTRA, 5, start=None), NOON)
    assert not live_at(bounty(4, EXTRA, 5, end=None), NOON)


def test_games_match_whatever_their_capitals_and_spaces():
    one = bounty(1, EXTRA, 5, "Super Mario  64")
    assert matches(one, "super mario 64")
    assert not matches(one, "Super Mario Sunshine")
    assert game_key("  Hollow   Knight ") == "hollow knight"


def test_no_bounty_leaves_the_base_points():
    assert points_for(10, "Celeste", NOON, []) == (10, None)
    assert points_for(10, "Celeste", NOON, [bounty(1, EXTRA, 5, "Hades")]) == (10, None)


def test_only_the_single_best_bounty_applies():
    several = [bounty(1, MULTIPLIER, 2), bounty(2, EXTRA, 15), bounty(3, MULTIPLIER, 1.5)]
    assert points_for(10, "Celeste", NOON, several) == (25, 2)
    assert points_for(20, "Celeste", NOON, several) == (40, 1)


def test_a_tie_between_bounties_goes_to_the_oldest():
    assert points_for(10, "Celeste", NOON, [bounty(7, EXTRA, 10), bounty(3, MULTIPLIER, 2)]) == (
        20,
        3,
    )


def test_a_bounty_that_would_not_raise_the_points_is_not_named():
    assert points_for(10, "Celeste", NOON, [bounty(1, MULTIPLIER, 1)]) == (10, None)
    assert points_for(0, "Celeste", NOON, [bounty(1, MULTIPLIER, 3)]) == (0, None)
    assert points_for(0, "Celeste", NOON, [bounty(1, EXTRA, 3)]) == (3, 1)


def test_an_ended_bounty_in_the_list_is_skipped_for_a_live_one():
    found = points_for(
        10, "Celeste", NOON, [bounty(1, EXTRA, 50, active=False), bounty(2, EXTRA, 5)]
    )
    assert found == (15, 2)
