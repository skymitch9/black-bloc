from datetime import date

from black_bloc.sports import nhl
from black_bloc.sports.model import FINAL
from tests.sports_fakes import Recorded, payload


def bracket():
    return nhl.parse_bracket(payload("nhl_bracket_2026"), 2026)


def test_series_letters_pair_into_the_next_round():
    assert nhl.next_of("A") == ("I", "a")
    assert nhl.next_of("H") == ("L", "b")
    assert nhl.next_of("K") == ("N", "a")
    assert nhl.next_of("N") == ("O", "b")
    assert nhl.next_of("O") is None


def test_every_link_sends_the_winner_on_to_the_next_series():
    found = bracket()
    assert len(found.links) == 14
    for source, (target, _slot) in found.links.items():
        game, after = found.game(source), found.game(target)
        winner = game.a_ext_id if game.a_score > game.b_score else game.b_ext_id
        assert winner in (after.a_ext_id, after.b_ext_id), source


def test_the_2026_cup_final_is_carolina_over_vegas_in_six():
    final = bracket().game("O")
    assert (final.a_ext_id, final.a_score, final.b_ext_id, final.b_score) == ("12", 4, "54", 2)
    assert (final.status, final.round) == (FINAL, 4)
    assert bracket().names["12"] == "Carolina Hurricanes"
    assert bracket().best_of["A"] == 7


def test_season_labels():
    assert nhl.season_of("20262027") == "2026-27"
    assert nhl.season_of(2026) == "2025-26"
    assert nhl.year_of("2025-26") == 2026


def test_a_days_scores_read_home_as_a():
    games = nhl.parse_score(payload("nhl_score_day"))
    assert (games[0].a_ext_id, games[0].a_score, games[0].b_ext_id, games[0].b_score) == (
        "8",
        5,
        "68",
        4,
    )
    assert games[0].status == FINAL


async def test_the_bracket_and_scores_answer_found():
    fetch = Recorded({"playoff-bracket/2026": "nhl_bracket_2026", "score/": "nhl_score_day"})
    answer = await nhl.bracket("2025-26", fetch=fetch)
    assert (answer.ok, answer.via, answer.value.season) == (True, "nhl", "2025-26")
    assert (await nhl.scores(date(2026, 11, 5), fetch=fetch)).ok
