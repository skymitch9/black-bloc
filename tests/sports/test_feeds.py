from datetime import date

from black_bloc.sports import feeds
from tests.sports_fakes import Recorded


def test_every_league_has_a_feed_for_teams_brackets_and_scores():
    for league in ("nfl", "nba", "mlb", "nhl", "ncaam", "ncaaw"):
        for need in (feeds.TEAMS, feeds.BRACKET, feeds.SCORES):
            assert feeds.feed_for(league, need) is not None, (league, need)
    assert feeds.feed_for("ncaam", feeds.PLAYERS) is None
    assert feeds.feed_for("nhl", feeds.SCORES) == feeds.Feed("espn", "nhl")


def test_the_current_season_per_league():
    november, february = date(2026, 11, 6), date(2027, 2, 1)
    assert feeds.current_season("nba", november) == "2026-27"
    assert feeds.current_season("ncaam", february) == "2026-27"
    assert feeds.current_season("nfl", february) == "2026"
    assert feeds.current_season("mlb", november) == "2026"
    assert feeds.current_season("mlb", february) == "2026"


async def test_a_primary_that_fails_falls_through_and_says_who_answered():
    fetch = Recorded({"baseball/mlb/teams": (500, b""), "mlb.com/api/v1/teams": "mlb_teams"})
    answer = await feeds.teams("mlb", fetch=fetch)
    assert (answer.ok, answer.via, len(answer.value)) == (True, "mlb", 3)


async def test_both_failing_names_both_reasons():
    answer = await feeds.teams("mlb", fetch=Recorded({}))
    assert answer.ok is False
    assert answer.via == "espn"
    assert answer.why == "ESPN answered 404 for the MLB teams; then MLB answered 404 for the teams"


async def test_a_feed_with_no_fallback_answers_the_primary():
    answer = await feeds.teams("nba", fetch=Recorded())
    assert (answer.ok, answer.via) == (True, "espn")


async def test_players_come_from_every_teams_roster():
    fetch = Recorded()
    answer = await feeds.players("nba", fetch=fetch, today=date(2026, 11, 6))
    assert (answer.ok, answer.via, len(answer.value)) == (True, "espn", 6)
    assert sum("/roster" in url for url in fetch.urls()) == 2


async def test_nba_players_fall_back_to_the_player_index():
    fetch = Recorded({"basketball/nba/teams?": "espn_teams_nba", "playerindex": "nba_playerindex"})
    answer = await feeds.players("nba", fetch=fetch, today=date(2026, 11, 6))
    assert (answer.ok, answer.via) == (True, "nba")
    assert "Season=2026-27" in fetch.urls()[-1]


async def test_schools_brackets_and_scores_name_their_source():
    fetch = Recorded(
        {
            "schools-index": "henrygd_schools",
            "playoff-bracket": "nhl_bracket_2026",
            "basketball/nba/scoreboard": "espn_scoreboard_nba",
        }
    )
    assert (await feeds.schools(fetch=fetch)).via == "ncaa"
    assert (await feeds.bracket("nhl", "2025-26", fetch=fetch)).via == "nhl"
    assert (await feeds.scores("nba", date(2026, 11, 6), fetch=fetch)).via == "espn"
