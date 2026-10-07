from __future__ import annotations

from datetime import UTC, datetime, timedelta

from black_bloc.brackets import checkin

ROWS = [
    {"id": 1, "checked_in": 1, "dropped": 0},
    {"id": 2, "checked_in": 0, "dropped": 0},
    {"id": 3, "checked_in": 0, "dropped": 1},
    {"id": 4, "checked_in": 1, "dropped": 1},
]


def test_no_shows_are_everyone_still_in_who_did_not_check_in():
    assert checkin.no_shows(ROWS) == [2]
    assert checkin.present(ROWS) == [1]


def test_the_window_closes_after_its_minutes():
    opened = datetime(2026, 10, 7, 18, 0, tzinfo=UTC)
    closes = checkin.closes_at(opened, 30)
    assert closes == opened + timedelta(minutes=30)
    assert not checkin.due(closes, closes - timedelta(seconds=1))
    assert checkin.due(closes, closes)
    assert not checkin.due(None, closes)
