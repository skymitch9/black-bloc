from datetime import date

from black_bloc.sports import espn
from black_bloc.sports.model import FINAL, LIVE, SCHEDULED
from tests.sports_fakes import Recorded, payload


def test_teams_are_read_with_their_abbreviation_and_other_names():
    teams = espn.parse_teams(payload("espn_teams_nba"), "nba")
    celtics = next(one for one in teams if one.ext_id == "2")
    assert (celtics.name, celtics.short, celtics.league) == ("Boston Celtics", "BOS", "nba")
    assert celtics.aliases == ("Celtics", "Boston")


def test_college_teams_come_from_the_same_shape():
    teams = {one.ext_id: one for one in espn.parse_teams(payload("espn_teams_ncaam"), "ncaam")}
    assert teams["150"].name == "Duke Blue Devils"
    assert teams["150"].short == "DUKE"
    assert "Blue Devils" in teams["150"].aliases


def test_a_grouped_roster_and_a_flat_one_read_the_same():
    nfl = espn.parse_roster(payload("espn_roster_nfl"), "nfl", "12")
    nba = espn.parse_roster(payload("espn_roster_nba"), "nba", "2")
    assert [one.name for one in nfl][:2] == ["Cyrus Allen", "Andrew Armstrong"]
    assert {one.team_ext_id for one in nfl} == {"12"}
    assert nba[1].name == "Mike Conley"
    assert nba[1].short == "M. Conley"


def test_the_scoreboard_reads_final_live_and_scheduled():
    games = {one.ext_id: one for one in espn.parse_scoreboard(payload("espn_scoreboard_nba"))}
    final, live, later = games["401909287"], games["401909289"], games["401909294"]
    assert (final.status, final.a_score, final.b_score) == (FINAL, 139, 132)
    assert (final.a_ext_id, final.b_ext_id) == ("1", "27")
    assert (live.status, live.period_words) == (LIVE, "1:26 - 3rd")
    assert (later.status, later.a_score, later.b_score) == (SCHEDULED, None, None)
    assert later.starts_at == "2026-11-07T03:00:00+00:00"


def test_a_tournament_scoreboard_carries_its_seeded_games():
    games = espn.parse_scoreboard(payload("espn_scoreboard_ncaam_tourney"))
    duke = next(one for one in games if "150" in (one.a_ext_id, one.b_ext_id))
    assert (duke.a_ext_id, duke.a_score, duke.b_score, duke.status) == ("150", 71, 65, FINAL)


def test_the_nfl_standings_give_seven_seeds_a_conference_in_order():
    seeds, names = espn.parse_seeds(payload("espn_standings_nfl"))
    assert seeds["AFC"][:7] == ["7", "17", "30", "23", "34", "2", "24"]
    assert seeds["NFC"][0] == "26"
    assert names["7"] == "Denver Broncos"


def test_espn_names_a_season_by_the_year_it_ends():
    assert espn.season_of("nba", 2027) == "2026-27"
    assert espn.season_of("ncaam", 2026) == "2025-26"
    assert espn.season_of("nfl", 2025) == "2025"
    assert espn.year_of("nhl", "2026-27") == 2027
    assert espn.year_of("nfl", "2025") == 2025


def test_the_urls_follow_the_measured_routes():
    assert espn.teams_url("ncaaw").endswith("womens-college-basketball/teams?limit=1000")
    assert espn.scoreboard_url("ncaam", date(2026, 3, 19), postseason=True).endswith(
        "scoreboard?seasontype=3&dates=20260319&limit=400&groups=100"
    )
    assert espn.scoreboard_url("nfl", postseason=True, week=2, season=2025).endswith(
        "football/nfl/scoreboard?seasontype=3&week=2&dates=2025"
    )
    assert espn.standings_url("nfl", 2025) == (
        "https://site.api.espn.com/apis/v2/sports/football/nfl/standings?season=2025"
    )


async def test_teams_answer_found_with_espn_as_the_source():
    answer = await espn.teams("nba", fetch=Recorded())
    assert (answer.ok, answer.via, len(answer.value)) == (True, "espn", 2)


async def test_one_roster_that_does_not_answer_fails_the_whole_list():
    fetch = Recorded({"teams/2/roster": "espn_roster_nba", "teams/24/roster": (503, b"")})
    answer = await espn.players("nba", ["2", "24"], fetch=fetch)
    assert answer.ok is False
    assert answer.why == "ESPN had a server error for the NBA roster of team 24"


async def test_scores_of_a_day_ask_for_that_date():
    fetch = Recorded({"scoreboard": "espn_scoreboard_nba"})
    answer = await espn.scores("nba", date(2026, 11, 6), fetch=fetch)
    assert answer.ok and len(answer.value) == 3
    assert fetch.urls()[0].endswith("basketball/nba/scoreboard?dates=20261106")
