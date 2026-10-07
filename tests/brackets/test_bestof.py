from __future__ import annotations

import pytest

from black_bloc.brackets import bestof
from black_bloc.brackets.model import BracketError, Options


@pytest.mark.parametrize(
    ("best_of", "score", "fits"),
    [
        (3, (2, 0), True),
        (3, (1, 2), True),
        (3, (2, 2), False),
        (3, (3, 1), False),
        (3, (1, 1), False),
        (5, (3, 2), True),
        (5, (2, 3), True),
        (5, (2, 1), False),
        (1, (1, 0), True),
        (1, (0, 0), False),
        (3, (True, 0), False),
        (3, ("2", 0), False),
        (3, (None, 2), False),
    ],
)
def test_a_score_fits_only_when_one_side_reached_the_wins_needed(best_of, score, fits):
    assert bestof.fits(best_of, *score) is fits


def test_checked_answers_the_numbers_the_refusal_needs():
    with pytest.raises(BracketError) as raised:
        bestof.checked(5, 2, 2)
    assert raised.value.fields == {"best_of": 5, "wins": 3}


def test_lengths_are_odd_and_bounded():
    assert [bestof.valid_length(n) for n in (1, 3, 15)] == [True] * 3
    assert [bestof.valid_length(n) for n in (0, 2, 17, -1, True, "3")] == [False] * 6


def test_the_length_for_a_set():
    options = Options(best_of=3, best_of_from_round=8, best_of_late=5, best_of_finals=7)
    assert bestof.length_for(options, 16, final=False) == 3
    assert bestof.length_for(options, 8, final=False) == 5
    assert bestof.length_for(options, 2, final=True) == 7
    assert bestof.length_for(Options(best_of=3), 2, final=False) == 3
