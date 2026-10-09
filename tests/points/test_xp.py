from __future__ import annotations

import pytest

from black_bloc.points.model import PointsError
from black_bloc.points.xp import (
    DEFAULT_TIERS,
    DEFAULT_TIERS_TEXT,
    parse_tiers,
    tiers_text,
    xp_for,
)


@pytest.mark.parametrize(
    ("seconds", "xp"),
    [
        (1, 5),
        (59, 5),
        (60, 5),
        (599, 5),
        (600, 25),
        (899, 25),
        (900, 50),
        (1799, 50),
        (1800, 100),
        (5 * 3600, 100),
    ],
)
def test_each_tier_is_a_floor_the_run_reaches(seconds, xp):
    assert xp_for(seconds) == xp


def test_the_least_and_the_most_bound_whatever_the_tiers_say():
    tiers = ((60.0, 1), (600.0, 500))
    assert xp_for(30, tiers, low=5, high=100) == 5
    assert xp_for(60, tiers, low=5, high=100) == 5
    assert xp_for(600, tiers, low=5, high=100) == 100


def test_staff_can_retune_the_tiers_and_the_order_they_wrote_them_in_does_not_matter():
    tiers = parse_tiers("30:00=200, 1:00=10, 10:00=40")
    assert tiers == ((60.0, 10), (600.0, 40), (1800.0, 200))
    assert xp_for(700, tiers, low=0, high=1000) == 40


def test_the_shipped_tiers_round_trip_through_their_text():
    assert parse_tiers(DEFAULT_TIERS_TEXT) == DEFAULT_TIERS
    assert DEFAULT_TIERS_TEXT == "1:00=5, 10:00=25, 15:00=50, 30:00=100"
    assert tiers_text(parse_tiers("1m=5, 10m=25")) == "1:00=5, 10:00=25"


@pytest.mark.parametrize(
    "given",
    ["", "1:00", "1:00=x", "1:00=5, 1:00=6", "fast=5", "1:00=-1", "1:00=5,,", "1:00=100001"],
)
def test_tiers_that_cannot_be_read_are_refused(given):
    with pytest.raises(PointsError) as refused:
        parse_tiers(given)
    assert refused.value.code == "bad_tiers"
