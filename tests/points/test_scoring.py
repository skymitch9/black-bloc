from __future__ import annotations

from datetime import UTC, datetime, timedelta

from black_bloc.points.bounty import Bounty
from black_bloc.points.model import EXTRA, MULTIPLIER
from black_bloc.points.scoring import Rules, Score, score

NOON = datetime(2026, 10, 9, 12, tzinfo=UTC)
WINDOW = (NOON - timedelta(hours=1), NOON + timedelta(hours=1))


def test_a_run_gets_its_tier_and_ten_speedpoints_by_default():
    assert score(59, "Celeste", NOON, Rules()) == Score(5, 10, None)
    assert score(1800, "Celeste", NOON, Rules()) == Score(100, 10, None)


def test_a_bounty_raises_the_speedpoints_and_never_the_xp():
    doubled = Bounty(4, "Double Celeste", ("celeste",), MULTIPLIER, 2, *WINDOW)
    assert score(900, "Celeste", NOON, Rules(), [doubled]) == Score(50, 20, 4)
    plus = Bounty(5, "Plus", ("celeste",), EXTRA, 7, *WINDOW)
    assert score(900, "Celeste", NOON, Rules(per_run=3), [plus]) == Score(50, 10, 5)


def test_the_rules_are_whatever_staff_set():
    rules = Rules(tiers=((10.0, 1), (20.0, 2)), low=0, high=2, per_run=4)
    assert score(5, "x", NOON, rules) == Score(0, 4, None)
    assert score(25, "x", NOON, rules) == Score(2, 4, None)
