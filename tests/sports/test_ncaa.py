from datetime import date

from black_bloc.sports import ncaa
from black_bloc.sports.model import FINAL
from tests.sports_fakes import Recorded, payload


def bracket():
    return ncaa.parse_bracket(payload("henrygd_bracket_men_2026"), "ncaam")


def test_the_2026_final_is_michigan_over_uconn():
    final = bracket().game("701")
    assert (final.a_ext_id, final.a_score, final.b_ext_id, final.b_score) == (
        "uconn",
        63,
        "michigan",
        69,
    )
    assert (final.status, final.round) == (FINAL, 6)


def test_the_first_four_is_round_zero_and_feeds_the_bottom_of_its_first_round_game():
    found = bracket()
    assert found.game("101").round == 0
    assert found.links["101"] == ("225", "b")
    assert found.game("225").b_ext_id == "howard"


def test_every_link_puts_the_winner_in_the_slot_it_names():
    found = bracket()
    for source, (target, slot) in found.links.items():
        game, after = found.game(source), found.game(target)
        if after is None:
            continue
        winner = game.a_ext_id if game.a_score > game.b_score else game.b_ext_id
        assert (after.a_ext_id if slot == "a" else after.b_ext_id) == winner, source


def test_seeds_names_and_the_season_label():
    found = bracket()
    assert found.season == "2025-26"
    assert found.seeds["michigan"] == 1
    assert found.names["uconn"] == "UConn"


def test_schools_are_slugs_with_the_long_name_as_an_alias():
    schools = {one.ext_id: one for one in ncaa.parse_schools(payload("henrygd_schools"))}
    assert schools["uconn"].name == "Connecticut"
    assert schools["uconn"].aliases == ("University of Connecticut",)


def test_the_scoreboard_keys_teams_by_their_slug():
    games = ncaa.parse_scoreboard(payload("henrygd_scoreboard_men"))
    assert (games[0].a_ext_id, games[0].b_ext_id, games[0].a_score, games[0].b_score) == (
        "ohio-st",
        "tcu",
        64,
        66,
    )


def test_season_labels_go_both_ways():
    assert ncaa.season_of(2026) == "2025-26"
    assert ncaa.year_of("2025-26") == 2026
    assert ncaa.year_of("2027") == 2027


async def test_the_bracket_asks_for_the_tournament_year():
    fetch = Recorded({"brackets/basketball-women/d1/2026": "henrygd_bracket_men_2026"})
    answer = await ncaa.bracket("ncaaw", "2025-26", fetch=fetch)
    assert (answer.ok, answer.via) == (True, "ncaa")


async def test_a_missing_bracket_is_worded_with_the_source():
    answer = await ncaa.bracket("ncaam", "2026-27", fetch=Recorded({}))
    assert answer.why == "NCAA (ncaa-api) answered 404 for the 2027 bracket"


async def test_scores_and_schools_answer_found():
    fetch = Recorded({"scoreboard": "henrygd_scoreboard_men", "schools": "henrygd_schools"})
    assert (await ncaa.scores("ncaam", date(2026, 3, 19), fetch=fetch)).ok
    assert len((await ncaa.schools(fetch=fetch)).value) == 6
