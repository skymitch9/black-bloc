from __future__ import annotations

import random

import pytest

from black_bloc.brackets import seeding
from black_bloc.brackets.model import BracketError


@pytest.mark.parametrize(("count", "size"), [(2, 2), (3, 4), (4, 4), (5, 8), (9, 16), (17, 32)])
def test_the_bracket_is_the_next_power_of_two(count, size):
    assert seeding.bracket_size(count) == size


def test_the_standard_order_pairs_one_v_n_and_splits_the_top_seeds():
    assert seeding.standard_order(8) == [1, 8, 4, 5, 2, 7, 3, 6]
    assert seeding.standard_order(16) == [1, 16, 8, 9, 4, 13, 5, 12, 2, 15, 7, 10, 3, 14, 6, 11]


def test_byes_fall_to_the_top_seeds():
    assert seeding.first_round([11, 12, 13, 14, 15, 16]) == [
        (11, None),
        (14, 15),
        (12, None),
        (13, 16),
    ]


def test_randomise_keeps_everyone_and_reorders():
    shuffled = seeding.randomised(list(range(1, 33)), random.Random(4))
    assert sorted(shuffled) == list(range(1, 33))
    assert shuffled != list(range(1, 33))


def test_a_reorder_must_name_the_same_entrants_once_each():
    assert seeding.reordered([1, 2, 3], [3, 1, 2]) == [3, 1, 2]
    for wanted in ([1, 2], [1, 2, 2], [1, 2, 4], [1, 1, 2, 3]):
        with pytest.raises(BracketError) as raised:
            seeding.reordered([1, 2, 3], wanted)
        assert raised.value.code == "bad_order"
