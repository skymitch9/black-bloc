from __future__ import annotations

from black_bloc.points.model import (
    BONUS_KINDS,
    CHANGE_KINDS,
    ORDERS,
    STATES,
    PointsError,
)


def test_a_refusal_carries_its_code_and_the_fields_its_words_take():
    error = PointsError("bad_time", given="fast")
    assert (error.code, error.fields, str(error)) == ("bad_time", {"given": "fast"}, "bad_time")


def test_the_vocabularies_are_the_ones_the_design_names():
    assert STATES == ("pending", "approved", "rejected", "removed")
    assert BONUS_KINDS == ("multiplier", "extra")
    assert ORDERS == ("points", "xp")
    assert CHANGE_KINDS == ("entered", "left", "up", "down")
