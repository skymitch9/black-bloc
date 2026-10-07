from __future__ import annotations

from black_bloc.brackets import play, standings
from black_bloc.brackets.model import DOUBLE, DQ, ROUND_ROBIN, A, B
from tests.brackets.test_play import NOW, TO, built, win


def test_what_each_entrant_waits_on_through_a_report_and_a_dispute():
    bracket = built(4, format=DOUBLE)
    found = standings.waiting_on(bracket)
    assert found[1] == {"what": standings.PLAY, "set": "W1-1", "opponent": 4, "open": 1}

    bracket = play.report(bracket, "W1-1", A, 2, 0, 1, NOW).bracket
    found = standings.waiting_on(bracket)
    assert (found[1]["what"], found[4]["what"]) == (standings.OPPONENT_CONFIRMS, standings.CONFIRM)

    bracket = play.dispute(bracket, "W1-1", B, 4, None, NOW).bracket
    assert standings.waiting_on(bracket)[4]["what"] == standings.TO_DECIDES

    bracket = play.accept(bracket, "W1-1", TO, NOW).bracket
    found = standings.waiting_on(bracket)
    assert found[1] == {"what": standings.WAITS, "set": "W2-1", "opponent": None, "open": 0}
    assert found[4] == {"what": standings.WAITS, "set": "L1-1", "opponent": None, "open": 0}


def test_a_called_set_and_a_withdrawn_entrant():
    bracket = play.call(built(2, format=DOUBLE), "W1-1", TO, NOW).bracket
    assert standings.waiting_on(bracket)[1]["what"] == standings.CALLED_UP
    bracket = play.withdraw(bracket, 2, DQ, NOW).bracket
    assert standings.waiting_on(bracket)[2]["what"] == standings.OUT


def test_a_finished_entrant_is_done():
    bracket = win(built(2, format=DOUBLE, grand_final_reset=False), "W1-1", A)
    bracket = win(bracket, "G1-1", A)
    assert {entrant: one["what"] for entrant, one in standings.waiting_on(bracket).items()} == {
        1: standings.DONE,
        2: standings.DONE,
    }


def test_a_round_robin_entrant_counts_every_open_set():
    found = standings.waiting_on(built(4, format=ROUND_ROBIN))
    assert found[1] == {"what": standings.PLAY, "set": "R1-1", "opponent": 4, "open": 3}
