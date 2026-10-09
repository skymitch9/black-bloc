from __future__ import annotations

from black_bloc.points.board import (
    CLIMB,
    FIRST,
    UNRANKED,
    Change,
    Row,
    diff,
    next_rank,
    place_of,
    standings,
)
from black_bloc.points.model import BY_XP, DOWN, ENTERED, LEFT, UP


def row(uid, sp, xp=0, last="2026-10-09T12:00", runs=1):
    return Row(uid, runs, xp, sp, last)


def order(board):
    return [one.user_id for one in board]


def test_most_speedpoints_first_and_places_count_from_one():
    board = standings([row(1, 10), row(2, 30), row(3, 20)])
    assert order(board) == [2, 3, 1]
    assert [one.place for one in board] == [1, 2, 3]


def test_a_member_with_no_approved_run_is_not_on_the_board():
    assert order(standings([row(1, 0, runs=0), row(2, 10)])) == [2]


def test_a_points_tie_goes_to_more_xp_then_to_whoever_got_there_first():
    board = standings(
        [
            row(1, 20, xp=50, last="2026-10-09T13:00"),
            row(2, 20, xp=100, last="2026-10-09T14:00"),
            row(3, 20, xp=50, last="2026-10-09T12:00"),
        ]
    )
    assert order(board) == [2, 3, 1]


def test_the_xp_view_ranks_by_xp_and_breaks_ties_on_speedpoints():
    board = standings(
        [row(1, 10, xp=100), row(2, 30, xp=25), row(3, 20, xp=100, last="2026-10-09T13:00")],
        by=BY_XP,
    )
    assert order(board) == [3, 1, 2]


def test_next_rank_is_the_place_above_and_one_more_than_the_gap():
    board = standings([row(1, 50), row(2, 30), row(3, 30, last="2026-10-09T13:00")])
    found = next_rank(board, 2, per_run=10)
    assert (found.kind, found.place, found.value, found.above.user_id, found.gap, found.runs) == (
        CLIMB,
        2,
        30,
        1,
        21,
        3,
    )
    tied = next_rank(board, 3, per_run=10)
    assert (tied.place, tied.above.user_id, tied.gap, tied.runs) == (3, 2, 1, 1)


def test_the_member_in_first_place_has_nobody_to_pass():
    found = next_rank(standings([row(1, 50), row(2, 30)]), 1)
    assert (found.kind, found.place, found.above, found.gap) == (FIRST, 1, None, 0)


def test_a_member_not_on_the_board_is_told_so():
    found = next_rank(standings([row(1, 50)]), 9)
    assert (found.kind, found.place, found.above) == (UNRANKED, None, None)
    assert next_rank([], 9).kind == UNRANKED


def test_next_rank_by_xp_counts_xp_and_no_runs():
    board = standings([row(1, 10, xp=100), row(2, 50, xp=25)], by=BY_XP)
    found = next_rank(board, 2, by=BY_XP, per_run=10)
    assert (found.value, found.gap, found.runs) == (25, 76, None)


def test_place_of_finds_a_member_or_nobody():
    board = standings([row(1, 50)])
    assert place_of(board, 1).place == 1
    assert place_of(board, 2) is None


def top(*pairs):
    return standings([row(uid, sp) for uid, sp in pairs])


def test_nothing_changed_is_no_change():
    board = top((1, 30), (2, 20))
    assert diff(board, board, 10) == []


def test_a_new_member_entering_pushes_the_rest_down():
    before = top((1, 30), (2, 20))
    after = top((1, 30), (2, 20), (3, 25))
    assert diff(before, after, 10) == [Change(ENTERED, 3, None, 2), Change(DOWN, 2, 2, 3)]


def test_a_swap_is_one_up_and_one_down():
    before = top((1, 30), (2, 20))
    after = top((1, 30), (2, 40))
    assert diff(before, after, 10) == [Change(UP, 2, 2, 1), Change(DOWN, 1, 1, 2)]


def test_dropping_out_of_the_top_is_a_leave_and_climbing_in_is_an_entry():
    before = top((1, 30), (2, 20), (3, 10))
    after = top((1, 30), (2, 5), (3, 10))
    assert diff(before, after, 2) == [Change(ENTERED, 3, 3, 2), Change(LEFT, 2, 2, 3)]


def test_a_member_whose_only_run_is_removed_leaves_and_has_no_place():
    before = top((1, 30), (2, 20))
    after = top((1, 30))
    assert diff(before, after, 10) == [Change(LEFT, 2, 2, None)]


def test_moves_below_the_top_are_not_announced():
    before = top((1, 50), (2, 40), (3, 30), (4, 20))
    after = top((1, 50), (2, 40), (3, 10), (4, 20))
    assert diff(before, after, 2) == []


def test_fewer_members_than_the_top_still_reports_each_move():
    before = top((1, 30))
    after = top((1, 30), (2, 40))
    assert diff(before, after, 10) == [Change(ENTERED, 2, None, 1), Change(DOWN, 1, 1, 2)]
    assert diff([], top((1, 10)), 10) == [Change(ENTERED, 1, None, 1)]
