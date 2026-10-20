import json
from pathlib import Path

import pytest

from black_bloc import runs_genres as rg
from black_bloc.settings_store import RUNS_DEFAULTS, RUNS_GENRE_FAMILIES, RUNS_GENRE_QUALIFIERS

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "runs" / "genre_families.json").read_text(
        encoding="utf-8"
    )
)
QUALIFIERS = rg.parse_qualifiers(FIXTURE["qualifiers"])
FAMILIES = rg.parse_families(FIXTURE["families"])


def test_the_shared_fixture_reads_the_shipped_defaults():
    assert FIXTURE["qualifiers"] == RUNS_DEFAULTS[RUNS_GENRE_QUALIFIERS]
    assert FIXTURE["families"] == RUNS_DEFAULTS[RUNS_GENRE_FAMILIES]


@pytest.mark.parametrize(("text", "family"), FIXTURE["cases"])
def test_every_fixture_genre_lands_in_its_family(text, family):
    assert rg.genre_family(text, QUALIFIERS, FAMILIES) == family


def test_text_is_lowered_and_punctuation_and_spacing_count_as_one_space():
    assert rg.normal("  Third-person/Shooter!! ") == "third person shooter"
    assert rg.normal("Shoot 'em up") == "shoot em up"
    assert rg.normal(None) == ""


def test_qualifiers_split_on_commas_or_lines_and_the_longest_comes_off_first():
    assert rg.parse_qualifiers("kart,\nthird-person , KART, ") == ("third person", "kart")
    assert rg.without_qualifiers("third person kart racer", ("third person", "kart")) == "racer"
    assert rg.without_qualifiers("kartography", ("kart",)) == "kartography"


def test_the_full_text_is_tried_against_every_family_before_the_stripped_one():
    families = rg.parse_families("adventure:\naction adventure game: action adventure")
    assert rg.genre_family("Action adventure", ("action",), families) == "action adventure game"
    assert rg.genre_family("Action horror", ("action",), families) == "horror"
    assert rg.genre_family("Action", ("action",), families) == "action"


def test_the_first_family_that_names_a_genre_wins():
    families = rg.parse_families("one: shared\ntwo: shared")
    assert rg.genre_family("Shared", (), families) == "one"


def test_a_line_that_is_not_a_family_is_skipped_and_reported_by_number():
    families, bad = rg.family_lines("racing: racer\nnot a family\n\n: orphan\npuzzle:")
    assert families == (("racing", ("racer",)), ("puzzle", ()))
    assert bad == ((2, "not a family"), (4, ": orphan"))
    assert rg.parse_families(None) == ()


def test_a_family_label_is_capitalised_and_its_terms_carry_every_alias():
    assert rg.family_label("survival horror") == "Survival horror"
    assert rg.family_label("") == ""
    assert rg.family_terms("racing", FAMILIES) == "racing racer racers race kart racer kart racing"
    assert rg.family_terms("puzzle", FAMILIES) == "puzzle"
