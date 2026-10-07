from __future__ import annotations

from black_bloc.brackets import play, tally
from black_bloc.brackets.model import DQ, SWISS
from tests.brackets.test_play import NOW, TO, built


def test_sets_games_byes_and_who_beat_whom():
    bracket = built(3, format=SWISS)
    bracket = play.override(bracket, "S1-1", TO, NOW, score_a=2, score_b=1).bracket
    found = tally.records(bracket)
    assert (found[1].set_wins, found[1].game_wins, found[1].game_losses, found[1].beat) == (
        1,
        2,
        1,
        [2],
    )
    assert (found[2].set_losses, found[2].game_wins, found[2].opponents) == (1, 1, [1])
    assert (found[3].byes, found[3].set_wins, found[3].played, found[3].opponents) == (1, 1, 1, [])
    assert found[3].win_rate == 1.0


def test_a_forfeit_counts_the_set_and_no_games():
    bracket = play.withdraw(built(2, format=SWISS), 2, DQ, NOW).bracket
    found = tally.records(bracket)
    assert (found[1].set_wins, found[1].game_wins, found[2].set_losses) == (1, 0, 1)


def test_met_holds_every_pairing_made():
    assert tally.met(built(4, format=SWISS)) == {frozenset((1, 3)), frozenset((2, 4))}
