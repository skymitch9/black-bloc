from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

import pytest

from black_bloc.brackets import play, standings
from black_bloc.brackets.model import (
    BY_OPPONENT,
    BY_TIME,
    BY_TO,
    BYE,
    CALLED,
    COMPLETE,
    DISPUTED,
    DOUBLE,
    DQ,
    DROP,
    READY,
    REPORTED,
    ROUND_ROBIN,
    SINGLE,
    SWISS,
    VOID,
    WAITING,
    A,
    B,
    BracketError,
    Options,
)

NOW = "2026-10-07T12:00:00+00:00"
TO = 99


def seeds(count: int) -> list[int]:
    return list(range(1, count + 1))


def built(count: int, **options) -> play.Bracket:
    options.setdefault("best_of_finals", 3)
    return play.build(seeds(count), Options(**options), NOW).bracket


def score_for(best_of: int, side: str) -> tuple[int, int]:
    need = best_of // 2 + 1
    return (need, 0) if side == A else (0, need)


def win(bracket, key: str, side: str):
    match = bracket.matches[key]
    score_a, score_b = score_for(match.best_of, side)
    return play.override(bracket, key, TO, NOW, score_a=score_a, score_b=score_b).bracket


def higher_seed(match) -> str:
    return A if match.slot_a < match.slot_b else B


def play_out(bracket, decide=higher_seed):
    """Every playable set decided by `decide` until nothing is left to play."""
    while True:
        ready = [match for match in bracket.ordered() if match.state in (READY, CALLED)]
        if not ready:
            return bracket
        bracket = win(bracket, ready[0].key, decide(ready[0]))


def test_too_few_entrants_is_refused():
    with pytest.raises(BracketError) as raised:
        play.build([1], Options(format=SINGLE))
    assert raised.value.code == "too_few"


def test_a_report_waits_for_the_opponent_then_completes_on_their_confirm():
    bracket = built(2, format=SINGLE)
    reported = play.report(bracket, "W1-1", A, 2, 1, 1, NOW)
    match = reported.bracket.matches["W1-1"]
    assert (match.state, match.score_a, match.score_b, match.reported_side) == (REPORTED, 2, 1, A)
    assert reported.changed == ["W1-1"]

    confirmed = play.confirm_report(reported.bracket, "W1-1", B, 2, NOW).bracket.matches["W1-1"]
    assert (confirmed.state, confirmed.winner, confirmed.loser) == (COMPLETE, 1, 2)
    assert (confirmed.confirmed_by, confirmed.confirmed_how) == (2, BY_OPPONENT)
    assert (confirmed.placement_winner, confirmed.placement_loser) == (1, 2)


def test_the_reporter_cannot_confirm_their_own_report():
    bracket = play.report(built(2, format=SINGLE), "W1-1", A, 2, 0, 1, NOW).bracket
    with pytest.raises(BracketError) as raised:
        play.confirm_report(bracket, "W1-1", A, 1, NOW)
    assert raised.value.code == "own_report"


def test_the_opponent_reporting_the_same_score_confirms_it_and_a_different_one_is_refused():
    bracket = play.report(built(2, format=SINGLE), "W1-1", A, 1, 2, 1, NOW).bracket

    with pytest.raises(BracketError) as raised:
        play.report(bracket, "W1-1", B, 2, 0, 2, NOW)
    assert raised.value.code == "reported_differently"
    assert raised.value.fields == {"set": "W1-1", "score_a": 1, "score_b": 2}

    same = play.report(bracket, "W1-1", B, 1, 2, 2, NOW).bracket.matches["W1-1"]
    assert (same.state, same.winner, same.confirmed_how) == (COMPLETE, 2, BY_OPPONENT)


def test_the_reporter_may_correct_their_own_report_before_it_is_confirmed():
    bracket = play.report(built(2, format=SINGLE), "W1-1", A, 2, 0, 1, NOW).bracket
    again = play.report(bracket, "W1-1", A, 2, 1, 1, NOW).bracket.matches["W1-1"]
    assert (again.state, again.score_a, again.score_b) == (REPORTED, 2, 1)


@pytest.mark.parametrize(
    ("best_of", "score"),
    [(3, (2, 2)), (3, (3, 0)), (3, (1, 0)), (3, (-1, 2)), (5, (2, 1)), (1, (1, 1))],
)
def test_a_score_that_does_not_fit_the_best_of_is_refused(best_of, score):
    bracket = built(2, format=SINGLE, best_of_finals=best_of)
    with pytest.raises(BracketError) as raised:
        play.report(bracket, "W1-1", A, *score, 1, NOW)
    assert raised.value.code == "bad_score"
    assert raised.value.fields == {"best_of": best_of, "wins": best_of // 2 + 1}


def test_a_report_on_a_set_that_is_not_ready_is_refused_before_the_score_is_read():
    bracket = built(4, format=SINGLE)
    with pytest.raises(BracketError) as raised:
        play.report(bracket, "W2-1", A, 9, 9, 1, NOW)
    assert raised.value.code == "not_ready"


def test_a_dispute_flags_the_set_for_the_to_who_lets_it_stand_or_overrides_it():
    bracket = play.report(built(2, format=SINGLE), "W1-1", A, 2, 1, 1, NOW).bracket
    disputed = play.dispute(bracket, "W1-1", B, 2, "they used a banned stage", NOW).bracket
    match = disputed.matches["W1-1"]
    assert (match.state, match.disputed_by, match.dispute_note) == (
        DISPUTED,
        2,
        "they used a banned stage",
    )
    with pytest.raises(BracketError) as raised:
        play.report(disputed, "W1-1", A, 2, 0, 1, NOW)
    assert raised.value.code == "disputed"

    kept = play.accept(disputed, "W1-1", TO, NOW).bracket.matches["W1-1"]
    assert (kept.state, kept.winner, kept.confirmed_how, kept.confirmed_by) == (
        COMPLETE,
        1,
        BY_TO,
        TO,
    )
    flipped = play.override(disputed, "W1-1", TO, NOW, score_a=1, score_b=2).bracket
    assert flipped.matches["W1-1"].winner == 2


def test_the_reporter_cannot_dispute_their_own_report():
    bracket = play.report(built(2, format=SINGLE), "W1-1", A, 2, 1, 1, NOW).bracket
    with pytest.raises(BracketError) as raised:
        play.dispute(bracket, "W1-1", A, 1, None, NOW)
    assert raised.value.code == "own_report"


def test_a_report_stands_once_the_confirm_time_has_passed():
    reported_at = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
    bracket = play.report(
        built(2, format=SINGLE), "W1-1", B, 0, 2, 2, reported_at.isoformat()
    ).bracket

    early = play.confirm_due(bracket, reported_at + timedelta(minutes=11, seconds=59), 12)
    assert early.changed == []
    assert early.bracket.matches["W1-1"].state == REPORTED

    late = play.confirm_due(bracket, reported_at + timedelta(minutes=12), 12)
    match = late.bracket.matches["W1-1"]
    assert (match.state, match.winner, match.confirmed_how, match.confirmed_by) == (
        COMPLETE,
        2,
        BY_TIME,
        None,
    )
    assert play.confirms_at(bracket.matches["W1-1"], 12) == reported_at + timedelta(minutes=12)


def test_a_called_set_can_still_be_reported_and_calling_twice_is_refused():
    bracket = play.call(built(2, format=SINGLE), "W1-1", TO, NOW).bracket
    assert (bracket.matches["W1-1"].state, bracket.matches["W1-1"].called_by) == (CALLED, TO)
    with pytest.raises(BracketError) as raised:
        play.call(bracket, "W1-1", TO, NOW)
    assert raised.value.code == "already_called"
    assert play.report(bracket, "W1-1", A, 2, 0, 1, NOW).bracket.matches["W1-1"].state == REPORTED


def test_a_to_report_goes_straight_to_complete_and_advances_the_winner():
    bracket = built(4, format=SINGLE)
    moved = play.override(bracket, "W1-1", TO, NOW, score_a=2, score_b=1)
    assert moved.changed == ["W1-1", "W2-1"]
    assert moved.bracket.matches["W1-1"].confirmed_how == BY_TO
    assert moved.bracket.matches["W2-1"].slot_a == 1
    assert moved.bracket.matches["W2-1"].state == WAITING


def test_resetting_a_reported_set_puts_it_back_to_ready():
    bracket = play.report(built(2, format=SINGLE), "W1-1", A, 2, 0, 1, NOW).bracket
    match = play.reset(bracket, "W1-1", TO, NOW).bracket.matches["W1-1"]
    assert (match.state, match.score_a, match.reported_by) == (READY, None, None)


def test_resetting_a_ready_set_or_a_bye_is_refused():
    bracket = built(3, format=SINGLE)
    for key, code in (("W1-2", "nothing_to_reset"), ("W1-1", "not_resettable")):
        with pytest.raises(BracketError) as raised:
            play.reset(bracket, key, TO, NOW)
        assert raised.value.code == code


def test_a_reset_in_single_elimination_undoes_the_winners_path_and_never_the_other_half():
    bracket = built(8, format=SINGLE)
    for key in ("W1-1", "W1-2", "W1-3", "W1-4"):
        bracket = win(bracket, key, A)
    bracket = win(bracket, "W2-1", A)
    bracket = win(bracket, "W2-2", A)
    assert bracket.matches["W3-1"].state == READY

    undone = play.reset(bracket, "W1-1", TO, NOW)
    after = undone.bracket.matches
    assert sorted(undone.changed) == ["W1-1", "W2-1", "W3-1"]
    assert (after["W1-1"].state, after["W1-1"].winner) == (READY, None)
    assert (after["W2-1"].state, after["W2-1"].slot_a, after["W2-1"].slot_b) == (WAITING, None, 4)
    assert (after["W3-1"].state, after["W3-1"].slot_a, after["W3-1"].slot_b) == (WAITING, None, 2)
    assert after["W2-2"] == bracket.matches["W2-2"]
    assert after["W1-3"] == bracket.matches["W1-3"]


def test_a_correction_replays_downstream_with_the_new_winner():
    bracket = built(4, format=SINGLE)
    bracket = win(win(bracket, "W1-1", A), "W1-2", A)
    bracket = win(bracket, "W2-1", A)
    corrected = play.override(bracket, "W1-1", TO, NOW, score_a=0, score_b=2).bracket
    final = corrected.matches["W2-1"]
    assert (final.state, final.slot_a, final.slot_b, final.winner) == (READY, 4, 2, None)


def test_a_reset_in_double_elimination_takes_back_the_drop_into_losers():
    bracket = built(4, format=DOUBLE)
    bracket = win(win(bracket, "W1-1", A), "W1-2", A)
    bracket = win(bracket, "L1-1", A)
    assert bracket.matches["L2-1"].slot_a == 4

    undone = play.reset(bracket, "W1-1", TO, NOW).bracket.matches
    assert (undone["L1-1"].state, undone["L1-1"].slot_a, undone["L1-1"].slot_b) == (
        WAITING,
        None,
        3,
    )
    assert undone["L2-1"].slot_a is None
    assert (undone["W2-1"].slot_a, undone["W2-1"].slot_b) == (None, 2)


def test_the_grand_final_reset_is_played_only_when_the_losers_side_wins():
    bracket = play_out(built(2, format=DOUBLE))
    assert bracket.matches["G2-1"].state == VOID
    assert standings.placements(bracket) == {1: 1, 2: 2}

    bracket = built(2, format=DOUBLE)
    bracket = win(bracket, "W1-1", A)
    bracket = win(bracket, "G1-1", B)
    reset = bracket.matches["G2-1"]
    assert (reset.state, reset.slot_a, reset.slot_b) == (READY, 1, 2)
    assert bracket.matches["G1-1"].placement_winner is None
    assert standings.placements(bracket) == {}
    bracket = win(bracket, "G2-1", B)
    assert standings.placements(bracket) == {2: 1, 1: 2}

    undone = play.reset(bracket, "G1-1", TO, NOW).bracket.matches["G2-1"]
    assert (undone.state, undone.slot_a, undone.slot_b) == (WAITING, None, None)


def test_without_the_reset_the_first_grand_final_decides():
    bracket = built(2, format=DOUBLE, grand_final_reset=False)
    assert "G2-1" not in bracket.matches
    bracket = win(win(bracket, "W1-1", A), "G1-1", B)
    assert standings.placements(bracket) == {2: 1, 1: 2}


def test_a_dq_forfeits_the_set_in_hand_and_every_later_one():
    bracket = built(4, format=DOUBLE)
    out = play.withdraw(bracket, 4, DQ, NOW)
    first = out.bracket.matches["W1-1"]
    assert (first.state, first.winner, first.loser, first.forfeit) == (COMPLETE, 1, 4, DQ)
    assert (first.score_a, first.score_b) == (None, None)

    bracket = win(out.bracket, "W1-2", A)
    losers = bracket.matches["L1-1"]
    assert (losers.state, losers.winner, losers.forfeit) == (COMPLETE, 3, DQ)
    assert standings.placements(bracket)[4] == 4


def test_a_drop_mid_round_robin_forfeits_their_remaining_sets_only():
    bracket = built(3, format=ROUND_ROBIN)
    bracket = win(bracket, "R1-1", A)
    out = play.withdraw(bracket, 3, DROP, NOW).bracket
    states = {key: (match.state, match.forfeit) for key, match in out.matches.items()}
    assert states == {
        "R1-1": (COMPLETE, None),
        "R2-1": (COMPLETE, DROP),
        "R3-1": (READY, None),
    }
    with pytest.raises(BracketError) as raised:
        play.withdraw(out, 3, DQ, NOW)
    assert raised.value.code == "already_out"


def test_reinstating_lifts_the_dq_but_the_forfeit_stands_until_the_set_is_reset():
    out = play.withdraw(built(2, format=SINGLE), 2, DQ, NOW).bracket
    back = play.reinstate(out, 2, NOW).bracket
    assert back.withdrawn == {}
    assert back.matches["W1-1"].forfeit == DQ
    replay = play.reset(back, "W1-1", TO, NOW).bracket.matches["W1-1"]
    assert (replay.state, replay.forfeit) == (READY, None)


def test_a_forfeit_override_needs_a_winner():
    bracket = built(2, format=SINGLE)
    with pytest.raises(BracketError) as raised:
        play.override(bracket, "W1-1", TO, NOW, forfeit=True)
    assert raised.value.code == "forfeit_needs_winner"
    done = play.override(bracket, "W1-1", TO, NOW, forfeit=True, winner=B).bracket
    assert (done.matches["W1-1"].winner, done.matches["W1-1"].forfeit) == (2, "to")


def test_resetting_a_swiss_set_takes_back_every_later_round():
    bracket = play_out(built(4, format=SWISS))
    assert sorted({match.round for match in bracket.matches.values()}) == [1, 2]
    undone = play.reset(bracket, "S1-1", TO, NOW)
    assert sorted(undone.removed) == ["S2-1", "S2-2"]
    assert undone.bracket.matches["S1-1"].state == READY


def test_a_round_robin_reset_touches_that_set_only():
    bracket = play_out(built(4, format=ROUND_ROBIN))
    undone = play.reset(bracket, "R2-1", TO, NOW)
    assert undone.changed == ["R2-1"]
    assert undone.removed == []


def test_an_unknown_set_is_refused_in_a_code_with_its_key():
    with pytest.raises(BracketError) as raised:
        play.report(built(2, format=SINGLE), "W9-9", A, 2, 0, 1, NOW)
    assert (raised.value.code, raised.value.fields) == ("no_set", {"set": "W9-9"})


def test_a_move_never_changes_the_bracket_it_was_given():
    bracket = built(4, format=DOUBLE)
    before = repr(bracket)
    play.override(bracket, "W1-1", TO, NOW, score_a=2, score_b=0)
    play.withdraw(bracket, 3, DQ, NOW)
    assert repr(bracket) == before


def test_a_finished_bracket_is_finished():
    bracket = built(3, format=SINGLE)
    assert not play.finished(bracket)
    assert play.finished(play_out(bracket))


@pytest.mark.parametrize("fmt", [SINGLE, DOUBLE, ROUND_ROBIN, SWISS])
@pytest.mark.parametrize("count", [2, 3, 5, 6, 9, 12])
def test_any_field_plays_to_the_end_with_random_results(fmt, count):
    rng = random.Random(count * 7 + len(fmt))
    bracket = play_out(built(count, format=fmt), lambda match: rng.choice((A, B)))
    assert play.finished(bracket)
    placed = standings.placements(bracket)
    assert sorted(placed) == seeds(count)
    assert sorted(placed.values())[0] == 1
    assert all(match.state in (COMPLETE, BYE, VOID) for match in bracket.matches.values())


def test_correcting_an_elimination_score_without_changing_the_winner_keeps_what_it_fed():
    bracket = built(4, format=SINGLE)
    bracket = win(win(bracket, "W1-1", A), "W1-2", A)
    bracket = win(bracket, "W2-1", A)
    corrected = play.override(bracket, "W1-1", TO, NOW, score_a=2, score_b=1)
    assert corrected.changed == ["W1-1"]
    assert corrected.bracket.matches["W2-1"] == bracket.matches["W2-1"]
    assert corrected.bracket.matches["W1-1"].score_b == 1


def test_a_round_robin_correction_touches_that_set_either_way():
    bracket = play_out(built(4, format=ROUND_ROBIN))
    for score in ((2, 1), (0, 2)):
        moved = play.override(bracket, "R1-1", TO, NOW, score_a=score[0], score_b=score[1])
        assert (moved.changed, moved.removed) == (["R1-1"], [])


@pytest.mark.parametrize("stamp", ["not a time", None, ""])
def test_a_report_with_an_unreadable_time_stands_at_the_next_sweep(stamp):
    bracket = play.report(built(2, format=SINGLE), "W1-1", B, 0, 2, 2, NOW).bracket
    bracket.matches["W1-1"].reported_at = stamp
    late = play.confirm_due(bracket, datetime(2026, 10, 7, 12, 0, tzinfo=UTC), 12)
    assert (late.bracket.matches["W1-1"].state, late.changed) == (COMPLETE, ["W1-1"])


@pytest.mark.parametrize(
    ("count", "options", "sets"),
    [
        (9, {"format": DOUBLE}, (16, 17)),
        (9, {"format": DOUBLE, "grand_final_reset": False}, (16, 16)),
        (8, {"format": SINGLE}, (7, 7)),
        (8, {"format": SINGLE, "third_place": True}, (8, 8)),
        (5, {"format": ROUND_ROBIN}, (10, 10)),
        (8, {"format": SWISS}, (12, 12)),
        (5, {"format": SWISS}, (6, 6)),
    ],
)
def test_the_sets_to_play_counts_only_sets_that_are_played(count, options, sets):
    assert play.sets_to_play(built(count, **options)) == sets
