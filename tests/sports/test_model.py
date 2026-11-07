from black_bloc.sports.model import (
    LEAGUES,
    Bracket,
    Game,
    aliases_of,
    failed,
    found,
    number,
    text,
)


def test_the_six_leagues_are_the_owners_list():
    assert LEAGUES == ("nfl", "nba", "mlb", "nhl", "ncaam", "ncaaw")


def test_found_and_failed_carry_who_answered():
    yes = found([1], "espn")
    no = failed("ESPN answered 403 " + "x" * 400, "espn")
    assert (yes.ok, yes.value, yes.via, yes.why) == (True, [1], "espn", None)
    assert (no.ok, no.value, no.via) == (False, None, "espn")
    assert len(no.why) == 300


def test_number_and_text_never_raise():
    assert number("139") == 139
    assert number(None) is None
    assert number("Final") is None
    assert text("  Boston   Celtics ") == "Boston Celtics"
    assert text("") is None


def test_aliases_drop_the_name_itself_and_repeats():
    assert aliases_of("Boston Celtics", "Celtics", "Boston", "Celtics", "Boston Celtics", None) == (
        "Celtics",
        "Boston",
    )


def test_a_bracket_finds_a_game_by_its_source_key():
    game = Game("1", "W1", "a", "b", None, None, "scheduled", None)
    held = Bracket("nfl", "2025", games=[game])
    assert held.game("W1") is game
    assert held.game("W2") is None
