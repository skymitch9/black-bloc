import json
from pathlib import Path

import pytest

from black_bloc import runs_search as rs

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "runs" / "search.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize(("query", "wanted"), FIXTURE["cases"])
def test_every_fixture_query_finds_exactly_its_games(query, wanted):
    found = [name for name, haystack in FIXTURE["haystacks"].items() if rs.matches(query, haystack)]
    assert found == wanted


@pytest.mark.parametrize(
    ("a", "b", "near"),
    [
        ("ab", "ba", True),
        ("abc", "abxc", True),
        ("abc", "ac", True),
        ("abc", "abd", True),
        ("abcd", "badc", False),
        ("abc", "abcde", False),
    ],
)
def test_one_edit_is_a_swap_an_insert_a_delete_or_a_replace(a, b, near):
    assert rs.one_edit(a, b) is near
    assert rs.one_edit(b, a) is near


def test_a_four_letter_word_never_fuzzes_and_a_five_letter_one_does():
    assert not rs.matches("kogn", "kong")
    assert rs.matches("knogs", "kongs")


def test_initials_stay_inside_one_line_and_the_digits_follow_the_run():
    assert rs.matches("dk", "Donkey Kong")
    assert not rs.matches("dk", "Donkey\nKong")
    assert rs.matches("dkc2", "Donkey Kong Country 2")
    assert not rs.matches("dkc2", "Donkey Kong Country 64")


def test_digits_alone_match_a_whole_number_only():
    assert rs.matches("64", "Donkey Kong 64")
    assert not rs.matches("6", "Donkey Kong 64")
    assert not rs.matches("2", "SGDQ 2025\n2D platformer")


def test_a_haystack_is_read_once_and_a_blank_one_matches_nothing():
    rs.prepared.cache_clear()
    rs.matches("kong", "Donkey Kong")
    rs.matches("donkey", "Donkey Kong")
    assert rs.prepared.cache_info().misses == 1
    assert not rs.matches("kong", None)
    assert not rs.matches(None, "Donkey Kong")
