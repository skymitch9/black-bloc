from datetime import date

from black_bloc.sports import mlb
from black_bloc.sports.model import FINAL
from tests.sports_fakes import Recorded, payload


def bracket():
    return mlb.parse_series(payload("mlb_series_2026"), 2026)


def test_the_2026_world_series_is_the_brewers_over_the_rays_in_five():
    series = bracket().game("W_1")
    assert (series.a_ext_id, series.a_score, series.b_ext_id, series.b_score) == (
        "158",
        4,
        "139",
        1,
    )
    assert (series.status, series.round) == (FINAL, 4)
    assert bracket().names["158"] == "Milwaukee Brewers"


def test_each_round_has_its_own_length():
    found = bracket()
    assert (found.best_of["F_1"], found.best_of["D_1"], found.best_of["L_1"]) == (3, 5, 7)


def test_every_link_puts_the_winner_in_the_slot_it_names():
    found = bracket()
    assert len(found.links) == 10
    for source, (target, slot) in found.links.items():
        after = found.game(target)
        assert (after.a_ext_id if slot == "a" else after.b_ext_id) == mlb.winner_of(
            found.game(source)
        )


def test_the_measured_shape_stands_in_before_a_round_has_teams():
    found = mlb.parse_series({"series": [payload("mlb_series_2026")["series"][1]]}, 2026)
    assert found.links == {"F_2": mlb.FALLBACK_LINKS["F_2"]}


def test_teams_players_and_a_days_schedule():
    teams = mlb.parse_teams(payload("mlb_teams"))
    assert (teams[1].name, teams[1].short, teams[1].aliases) == (
        "Pittsburgh Pirates",
        "PIT",
        ("Pirates", "Pittsburgh"),
    )
    judge = next(one for one in mlb.parse_players(payload("mlb_players")) if one.ext_id == "592450")
    assert (judge.name, judge.team_ext_id) == ("Aaron Judge", "147")
    game = mlb.parse_schedule(payload("mlb_schedule_day"))[0]
    assert (game.a_ext_id, game.a_score, game.b_ext_id, game.b_score) == ("139", 1, "158", 4)


async def test_each_call_answers_found_from_mlb():
    fetch = Recorded(
        {
            "postseason/series": "mlb_series_2026",
            "v1/teams": "mlb_teams",
            "sports/1/players": "mlb_players",
            "schedule?": "mlb_schedule_day",
        }
    )
    assert (await mlb.bracket("2026", fetch=fetch)).via == "mlb"
    assert len((await mlb.teams(fetch=fetch)).value) == 3
    assert len((await mlb.players(2026, fetch=fetch)).value) == 3
    assert (await mlb.scores(date(2026, 10, 28), fetch=fetch)).ok
