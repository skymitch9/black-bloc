from datetime import UTC, datetime, timedelta

import pytest

from black_bloc import marathon as mt
from black_bloc import marathon_damping as md

NOW = datetime(2027, 1, 4, 18, 0, tzinfo=UTC)


def at(minutes):
    return (NOW + timedelta(minutes=minutes)).isoformat()


def run(start=900, *, published=None, pending=None, reads=None, state=mt.UPCOMING, length=60):
    return {
        "id": 63,
        "state": state,
        "scheduled_at": at(start),
        "ends_at": at(start + length),
        md.PUBLISHED: at(published) if published is not None else None,
        md.PUBLISHED_END: at(published + length) if published is not None else None,
        md.PENDING: at(pending) if pending is not None else None,
        md.READS: reads,
    }


def step(row, *, minutes=60, needed=2, read=True, now=NOW):
    return md.step(row, now, minutes=minutes, needed=needed, read=read)


def test_a_run_with_nothing_published_shows_its_stored_start_and_takes_no_step():
    row = run()
    assert not md.pending(row) and md.shown_start(row) == at(900)
    assert md.shown_end(row) == at(960)
    assert step(row) == md.Step(md.NOTHING) and step(row, read=False) == md.Step(md.NOTHING)


def test_a_waiting_move_shows_the_start_last_published():
    row = run(836, published=900, pending=836, reads=1)
    assert md.waits(row) and md.shown_start(row) == at(900) and md.shown_end(row) == at(960)
    assert row["scheduled_at"] == at(836)


@pytest.mark.parametrize("state", [mt.LIVE, mt.DONE, mt.DROPPED])
def test_only_a_run_still_coming_up_shows_an_older_start(state):
    row = run(836, published=900, pending=836, reads=1, state=state)
    assert not md.waits(row) and md.shown_start(row) == at(836)
    assert step(row) == md.Step(md.CLEAR)


def test_run_fields_print_the_published_start_while_a_move_waits():
    waiting = run(836, published=900, pending=836, reads=1)
    held = mt.run_fields(waiting, {"name": "FF"}, {}, url="")
    plain = mt.run_fields(run(836), {"name": "FF"}, {}, url="")
    assert held["when"] == mt.stamp_of(at(900), "f") and held["in"] == mt.stamp_of(at(900), "R")
    assert held["relative"] == held["in"]
    assert plain["when"] == mt.stamp_of(at(836), "f")


def test_far_is_strictly_more_than_the_window_and_zero_minutes_never_damps():
    assert md.far(at(61), NOW, 60) and not md.far(at(60), NOW, 60)
    assert not md.far(None, NOW, 60) and not md.far("soon", NOW, 60)
    assert md.damped(60, NOW, at(900), at(836))
    assert not md.damped(60, NOW, at(900), at(45))
    assert not md.damped(60, NOW, at(45), at(900))
    assert not md.damped(0, NOW, at(900), at(836))
    assert not md.damped(None, NOW, at(900), at(836))


def test_same_reads_two_spellings_of_one_instant_as_one():
    assert md.same("2027-01-05T09:00:00+00:00", "2027-01-05T09:00:00Z")
    assert md.same(None, None) and md.same("", None)
    assert not md.same(at(1), at(2)) and not md.same(at(1), None)


def test_the_first_held_move_keeps_what_was_published_and_counts_from_nothing():
    assert md.held_fields(run(900), at(836)) == {
        md.PUBLISHED: at(900),
        md.PUBLISHED_END: at(960),
        md.PENDING: at(836),
        md.READS: 0,
    }


def test_a_second_candidate_keeps_the_published_start_and_starts_its_count_again():
    row = run(836, published=900, pending=836, reads=1)
    found = md.held_fields(row, at(896))
    assert (found[md.PUBLISHED], found[md.PUBLISHED_END]) == (at(900), at(960))
    assert (found[md.PENDING], found[md.READS]) == (at(896), 0)
    assert md.held_fields(row, at(836))[md.READS] == 1


def test_a_read_counts_and_a_tick_does_not():
    row = run(836, published=900, pending=836, reads=0)
    assert step(row) == md.Step(md.HOLD, 1)
    assert step(row, read=False) == md.Step(md.NOTHING)
    assert step(row | {md.READS: 1}) == md.Step(md.PUBLISH, 2)
    assert step(row | {md.READS: 1}, needed=3) == md.Step(md.HOLD, 2)
    assert step(row | {md.READS: 2}, needed=3) == md.Step(md.PUBLISH, 3)


def test_a_start_back_where_it_was_published_is_cleared_on_a_read_or_a_tick():
    row = run(900, published=900, pending=900, reads=0)
    assert step(row) == md.Step(md.CLEAR) and step(row, read=False) == md.Step(md.CLEAR)


def test_a_run_come_near_or_a_key_turned_off_publishes_on_a_tick():
    row = run(836, published=900, pending=836, reads=1)
    assert step(row, read=False, now=NOW + timedelta(minutes=776)) == md.Step(md.PUBLISH)
    assert step(row, read=False, now=NOW + timedelta(minutes=775)) == md.Step(md.NOTHING)
    assert step(row, read=False, minutes=0) == md.Step(md.PUBLISH)
    early = run(900, published=836, pending=900, reads=1)
    assert step(early, read=False, now=NOW + timedelta(minutes=776)) == md.Step(md.PUBLISH)


def test_a_stored_start_nobody_counted_is_published_on_a_tick():
    row = run(870, published=900, pending=836, reads=1)
    assert step(row, read=False) == md.Step(md.PUBLISH)


@pytest.mark.parametrize(("raw", "needed"), [(2, 2), (3, 3), (1, 2), (0, 2), (None, 2), ("x", 2)])
def test_fewer_than_two_reads_is_read_as_two(raw, needed):
    assert md.reads_needed(raw) == needed


def test_moved_enough_is_the_moved_threshold_either_way():
    assert md.moved_enough(at(900), at(905), 5) and md.moved_enough(at(900), at(895), 5)
    assert not md.moved_enough(at(900), at(904), 5) and not md.moved_enough(None, at(900), 5)
