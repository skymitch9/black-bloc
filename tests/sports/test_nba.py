from black_bloc.sports import nba
from black_bloc.sports.model import FINAL
from tests.sports_fakes import Recorded, payload


def bracket():
    return nba.parse_bracket(payload("nba_bracket_2025"))


def winner(game):
    return game.a_ext_id if game.a_score > game.b_score else game.b_ext_id


def test_every_link_puts_the_winner_in_the_slot_it_names():
    found = bracket()
    assert len(found.links) == 14
    for source, (target, slot) in found.links.items():
        after = found.game(target)
        assert (after.a_ext_id if slot == "a" else after.b_ext_id) == winner(found.game(source))


def test_the_2026_finals_are_the_knicks_over_the_spurs_in_five():
    final = bracket().game("R4-0")
    assert final.status == FINAL
    assert bracket().names[winner(final)] == "New York Knicks"
    assert sorted((final.a_score, final.b_score)) == [1, 4]


def test_seeds_and_the_season_label():
    found = bracket()
    assert found.season == "2025-26"
    assert found.seeds["1610612765"] == 1
    assert found.best_of["R1-0"] == 7


def test_the_player_index_reads_by_header():
    players = nba.parse_players(payload("nba_playerindex"))
    assert (players[0].name, players[0].short, players[0].team_ext_id) == (
        "Precious Achiuwa",
        "P. Achiuwa",
        "1610612758",
    )


async def test_calls_carry_the_nba_headers():
    fetch = Recorded({"playoffbracket": "nba_bracket_2025", "playerindex": "nba_playerindex"})
    answer = await nba.bracket("2025-26", fetch=fetch)
    assert (answer.ok, answer.via) == (True, "nba")
    assert "SeasonYear=2025" in fetch.urls()[0]
    assert (await nba.players("2026-27", fetch=fetch)).ok
    assert all(headers["Origin"] == "https://www.nba.com" for _, headers in fetch.asked)
