from datetime import UTC, datetime, timedelta

import pytest

from black_bloc.raidtrain import (
    CANCELLED,
    DONE,
    LIVE,
    LOCKED,
    OPEN,
    STATUS_WORDS,
    STATUSES,
    TERMINAL_STATUSES,
    TRANSITIONS,
    allowed_moves,
    cancelled_text,
    caps_ok,
    due_checkins,
    due_reminders,
    ends_at,
    filled,
    live_post_text,
    may_move,
    missed_reminders,
    move_refusal,
    neighbours,
    next_open_position,
    open_positions,
    positions_word,
    reminder_text,
    render_lineup,
    slot_at,
    slot_times,
    slots_held,
    twitch_url,
)

START = datetime(2026, 9, 14, 19, 0, tzinfo=UTC)


def iso(when):
    return when.isoformat()


def train(**over):
    row = {
        "id": 1,
        "title": "Saturday train",
        "description": "Everyone welcome.",
        "starts_at": iso(START),
        "slot_minutes": 60,
        "slot_count": 3,
        "status": OPEN,
        "cancel_reason": None,
    }
    row.update(over)
    return row


def slot(position, **over):
    start = START + timedelta(minutes=60 * (position - 1))
    row = {
        "id": position,
        "train_id": 1,
        "position": position,
        "starts_at": iso(start),
        "ends_at": iso(start + timedelta(minutes=60)),
        "user_id": None,
        "twitch_login": None,
        "claimed_at": None,
        "assigned_by": None,
        "locked": 0,
        "reminded_at": None,
        "checked_in_at": None,
        "live_posted_at": None,
    }
    row.update(over)
    return row


def lineup():
    return [
        slot(1, user_id=11, twitch_login="alpha"),
        slot(2, user_id=22, twitch_login="beta"),
        slot(3),
    ]


def test_slots_run_back_to_back_from_the_start():
    times = slot_times(START, 60, 3)
    assert len(times) == 3
    assert times[0] == (START, START + timedelta(hours=1))
    assert times[1][0] == times[0][1]
    assert times[2][1] == START + timedelta(hours=3)


def test_a_train_with_no_slots_has_no_times():
    assert slot_times(START, 60, 0) == []


def test_the_end_of_a_train_comes_from_its_own_rows_first():
    rows = lineup()
    assert ends_at(train(), rows) == START + timedelta(hours=3)
    assert ends_at(train(slot_count=5), None) == START + timedelta(hours=5)
    assert ends_at({"starts_at": "not a time"}, None) is None


def test_only_the_named_moves_are_allowed():
    assert may_move(OPEN, LOCKED) is True
    assert may_move(LOCKED, OPEN) is True
    assert may_move(LOCKED, LIVE) is True
    assert may_move(LIVE, DONE) is True
    assert may_move(DONE, LIVE) is False
    assert may_move(CANCELLED, OPEN) is False
    assert may_move("nonsense", OPEN) is False
    assert set(TERMINAL_STATUSES) == {DONE, CANCELLED}
    assert set(TRANSITIONS) == set(STATUSES)
    assert set(STATUS_WORDS) == set(STATUSES)
    for allowed in TRANSITIONS.values():
        assert set(allowed) <= set(STATUSES)


def test_a_refusal_says_what_is_allowed_instead_of_printing_a_status_list():
    said = move_refusal(LIVE, OPEN)
    assert "**live**" in said and "**done**" in said
    assert "cannot be marked **open**" in said
    assert allowed_moves(LIVE) == "**done**"
    assert allowed_moves(OPEN) == "**locked**, **live** or **cancelled**"
    assert allowed_moves(DONE) == "nothing"
    assert "end of the line" in move_refusal(DONE, OPEN)


def test_the_cap_counts_what_a_member_already_holds_and_zero_means_no_ceiling():
    rows = lineup()
    assert caps_ok(rows, 11, 1) is False
    assert caps_ok(rows, 33, 1) is True
    assert caps_ok(rows, 11, 0) is True
    assert caps_ok(rows, 11, 2) is True
    assert [row["position"] for row in slots_held(rows, 11)] == [1]


def test_the_open_slots_are_found_in_order():
    rows = [slot(1), slot(2, user_id=22), slot(3)]
    assert open_positions(rows) == [1, 3]
    assert next_open_position(rows) == 1
    assert positions_word(rows) == "#1, #3"
    assert next_open_position([slot(1, user_id=1)]) is None
    assert positions_word([slot(1, user_id=1)]) == "none"
    assert filled(rows) == 1


def test_a_slot_is_found_by_position_and_knows_its_neighbours():
    rows = lineup()
    assert slot_at(rows, 2)["user_id"] == 22
    assert slot_at(rows, 9) is None
    before, after = neighbours(rows, 2)
    assert before["position"] == 1 and after["position"] == 3
    assert neighbours(rows, 1)[0] is None


def test_the_lineup_names_the_ping_role_only_and_reads_every_slot():
    text = render_lineup(train(), lineup(), ping_role_id=77)
    assert text.startswith("<@&77> ")
    assert "**Saturday train**" in text
    assert "2/3 slot(s) filled" in text
    assert "https://twitch.tv/alpha" in text
    assert "<@11>" in text and "_open_" in text
    assert "`/raidtrain claim`" in text


def test_a_locked_lineup_stops_inviting_claims_and_a_cancelled_one_says_so():
    locked = render_lineup(train(status=LOCKED), lineup())
    assert "`/raidtrain claim`" not in locked
    assert "locked" in locked
    off = render_lineup(train(status=CANCELLED, cancel_reason="the venue fell through"), lineup())
    assert "**This train is cancelled.**" in off
    assert "the venue fell through" in off


def test_a_checked_in_slot_is_marked_on_the_lineup():
    rows = lineup()
    rows[0]["checked_in_at"] = iso(START)
    assert "✅" in render_lineup(train(), rows)


def test_the_reminder_names_who_raids_in_and_who_to_raid_next():
    rows = lineup()
    before, after = neighbours(rows, 2)
    said = reminder_text(train(), rows[1], before, after, link="https://discord.com/x")
    assert "**Saturday train**" in said
    assert "slot **#2**" in said
    assert "<@11>" in said and "https://twitch.tv/alpha" in said
    assert "raid" in said
    assert "https://discord.com/x" in said


def test_the_first_and_last_holders_are_told_they_open_and_close_the_train():
    rows = lineup()
    opener = reminder_text(train(), rows[0], *neighbours(rows, 1))
    assert "you open the train" in opener
    closer = reminder_text(train(), rows[1], *neighbours(rows, 2))
    assert "you close the train" in closer


def test_a_cancellation_dm_names_the_train_and_the_reason_when_there_is_one():
    assert "no longer happening" in cancelled_text(train())
    assert "the venue fell through" in cancelled_text(train(), "the venue fell through")


def test_a_reminder_is_due_inside_the_lead_window_and_only_once():
    rows = lineup()
    now = START - timedelta(minutes=20)
    assert [row["position"] for row in due_reminders(now, 30, rows)] == [1]
    rows[0]["reminded_at"] = iso(now)
    assert due_reminders(now, 30, rows) == []


def test_an_unclaimed_slot_is_never_reminded():
    rows = [slot(1)]
    assert due_reminders(START - timedelta(minutes=5), 30, rows) == []


def test_a_reminder_whose_slot_has_gone_by_ages_out_instead_of_arriving_late():
    rows = lineup()
    now = START + timedelta(minutes=40)
    assert [row["position"] for row in due_reminders(now, 30, rows)] == [2]
    assert [row["position"] for row in missed_reminders(now, rows)] == [1]
    assert missed_reminders(START - timedelta(minutes=5), rows) == []


def test_a_check_in_needs_an_open_session_inside_the_slots_own_window():
    rows = lineup()
    assert [row["position"] for row in due_checkins(START, rows, [11])] == [1]
    assert due_checkins(START, rows, [22]) == []
    assert due_checkins(START - timedelta(minutes=30), rows, [11]) == []
    early = START - timedelta(minutes=10)
    assert [row["position"] for row in due_checkins(early, rows, [11])] == [1]
    rows[0]["checked_in_at"] = iso(START)
    assert due_checkins(START, rows, [11]) == []


def test_the_train_moves_line_names_who_is_on_air_and_who_is_next():
    rows = lineup()
    said = live_post_text(train(), rows[0], rows[1])
    assert "**alpha**" in said and "**beta**" in said
    assert "https://twitch.tv/alpha" in said
    last = live_post_text(train(), rows[1], rows[2])
    assert "last booked slot" in last


def test_a_twitch_url_survives_an_at_sign():
    assert twitch_url("@name") == "https://twitch.tv/name"
    assert twitch_url(None) == "https://twitch.tv/"


@pytest.mark.parametrize("status", [OPEN, LOCKED, LIVE, DONE, CANCELLED])
def test_every_status_renders_a_lineup_rather_than_raising(status):
    assert render_lineup(train(status=status), lineup())
