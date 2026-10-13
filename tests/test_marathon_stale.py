from datetime import UTC, datetime, timedelta

import pytest

from black_bloc import marathon_stale as st

NOW = datetime(2026, 10, 12, 22, 0, tzinfo=UTC)


def ago(hours):
    return (NOW - timedelta(hours=hours)).isoformat()


def row(**given):
    base = {
        "id": 17,
        "name": "Speed Stuff",
        "active": 1,
        "ignored_at": None,
        "fetch_failures": 3,
        "last_error": "oengus.io answered 401",
        "stale_clock_at": ago(25),
    }
    return base | given


def test_it_takes_the_reads_and_the_hours_together():
    assert st.is_stale(row(), NOW, reads=3, hours=24) is True
    assert st.is_stale(row(stale_clock_at=ago(24)), NOW, reads=3, hours=24) is True
    assert st.is_stale(row(stale_clock_at=ago(23)), NOW, reads=3, hours=24) is False
    assert st.is_stale(row(fetch_failures=2), NOW, reads=3, hours=24) is False
    old = row(fetch_failures=2, stale_clock_at=ago(900))
    assert st.is_stale(old, NOW, reads=3, hours=24) is False


def test_reads_at_zero_never_archives_and_hours_at_zero_needs_the_reads_alone():
    old = row(fetch_failures=99, stale_clock_at=ago(900))
    assert st.is_stale(old, NOW, reads=0, hours=0) is False
    assert st.is_stale(row(stale_clock_at=ago(0)), NOW, reads=3, hours=0) is True
    assert st.is_stale(row(fetch_failures=1, stale_clock_at=ago(0)), NOW, reads=1, hours=0) is True


def test_no_stored_clock_never_archives():
    assert st.is_stale(row(stale_clock_at=None), NOW, reads=3, hours=24) is False
    assert st.is_stale(row(stale_clock_at=None), NOW, reads=3, hours=0) is False
    assert st.is_stale(row(stale_clock_at="not a time"), NOW, reads=3, hours=24) is False
    assert st.is_stale(None, NOW, reads=3, hours=24) is False


@pytest.mark.parametrize("given", [{"active": 0}, {"ignored_at": ago(1)}])
def test_a_paused_or_ignored_marathon_is_never_stale(given):
    assert st.is_stale(row(**given), NOW, reads=3, hours=24) is False


def test_the_clock_starts_at_the_first_failure_seen_and_is_kept_after_it():
    assert st.failed_fields(row(stale_clock_at=None), NOW, unpublished=False) == {
        "stale_clock_at": NOW.isoformat()
    }
    assert st.failed_fields(row(), NOW, unpublished=False) == {}


def test_an_unpublished_answer_restarts_the_clock():
    assert st.failed_fields(row(), NOW, unpublished=True) == {"stale_clock_at": NOW.isoformat()}


def test_a_failure_is_counted_only_when_the_count_went_up():
    assert st.counted({"fetch_failures": 2}, {"fetch_failures": 3}) is True
    assert st.counted({"fetch_failures": 3}, {"fetch_failures": 3}) is False
    assert st.counted({"fetch_failures": None}, {"fetch_failures": 1}) is True


def test_the_log_details_name_the_reason_the_count_and_the_clock():
    assert st.archived_details(row(), 24) == {
        "marathon_id": 17,
        "name": "Speed Stuff",
        "reason": "oengus.io answered 401",
        "failures": 3,
        "unreadable_since": ago(25),
        "hours": 24,
    }


def test_only_a_listed_archived_row_marked_stale_is_tried_once_each():
    known = {
        "74": {"id": 1, "archived": 0, "archived_why": None},
        "75": {"id": 2, "archived": 1, "archived_why": "stale"},
        "76": {"id": 3, "archived": 1, "archived_why": "staff"},
        "77": {"id": 4, "archived": 1, "archived_why": "ended"},
        "78": {"id": 5, "archived": 1, "archived_why": "stale"},
    }
    assert [one["id"] for one in st.tries(known, ["74", "75", "75", "76", "77", "99"])] == [2]
    assert st.tries(known, []) == []


def test_a_restore_restarts_the_clock_and_a_stale_one_starts_its_count_again():
    assert st.restored_fields({"archived_why": "stale"}, NOW) == {
        "stale_clock_at": NOW.isoformat(),
        "fetch_failures": 0,
    }
    assert st.restored_fields({"archived_why": "staff"}, NOW) == {"stale_clock_at": NOW.isoformat()}
    assert st.is_marked({"archived_why": "stale"}) and not st.is_marked({"archived_why": "staff"})
    assert st.is_marked(None) is False
