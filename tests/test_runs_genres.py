import json
from pathlib import Path

import pytest

from black_bloc import runs_genres as rg
from black_bloc.settings_store import (
    RUNS_DEFAULTS,
    RUNS_GENRE_FAMILIES,
    RUNS_GENRE_QUALIFIERS,
    RUNS_GENRE_UPPER,
)

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


SHAPES = json.loads(
    (Path(__file__).parent / "fixtures" / "runs" / "genre_format.json").read_text(encoding="utf-8")
)
SHAPE_RULE = (
    rg.parse_qualifiers(SHAPES["qualifiers"]),
    rg.parse_families(SHAPES["families"]),
    rg.parse_upper(SHAPES["upper"]),
)


def test_the_format_fixture_reads_the_shipped_defaults():
    assert SHAPES["qualifiers"] == RUNS_DEFAULTS[RUNS_GENRE_QUALIFIERS]
    assert SHAPES["families"] == RUNS_DEFAULTS[RUNS_GENRE_FAMILIES]
    assert SHAPES["upper"] == RUNS_DEFAULTS[RUNS_GENRE_UPPER]
    assert rg.parse_upper(SHAPES["upper"]) == rg.UPPER_WORDS


@pytest.mark.parametrize(("text", "shown"), SHAPES["cases"])
def test_every_fixture_genre_is_spelled_the_house_way(text, shown):
    assert rg.genre_format(text, *SHAPE_RULE) == shown
    assert rg.genre_format(shown, *SHAPE_RULE) == shown


def test_a_list_splits_on_commas_and_each_entry_has_its_own_family():
    assert rg.genre_entries(" Soulslike ,, Action  adventure ") == ["Soulslike", "Action adventure"]
    assert rg.genre_entries(None) == []
    assert rg.genre_families("Soulslike, Action adventure", *SHAPE_RULE[:2]) == [
        "soulslike",
        "adventure",
    ]
    assert rg.genre_families("Kart racer, Racing", *SHAPE_RULE[:2]) == ["racing"]
    assert rg.genre_families("", *SHAPE_RULE[:2]) == []


def test_without_a_rule_only_the_same_spelling_is_one_entry():
    assert rg.genre_format("Roguelike, roguelite") == "Roguelike, Roguelite"
    assert rg.genre_format("roguelike, ROGUELIKE") == "Roguelike"
    assert rg.genre_format("fps", upper=()) == "Fps"


def test_a_developer_alias_line_is_found_by_its_name_or_any_alias():
    lines = rg.parse_families("FromSoftware: fromsoft, from software\nNintendo: nintendo ead")
    wanted = ["fromsoftware", "fromsoft", "from software"]
    assert rg.alias_words("FromSoftware", lines) == wanted
    assert rg.alias_words("From Software", lines) == wanted
    assert rg.alias_words("Capcom", lines) == []
    assert rg.alias_words("", lines) == []
