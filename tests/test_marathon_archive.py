from datetime import UTC, datetime, timedelta

from black_bloc import marathon_archive as ma

NOW = datetime(2027, 1, 20, 12, 0, tzinfo=UTC)


def row(ident, ends, starts=None):
    return {
        "id": ident,
        "starts_at": starts.isoformat() if starts else None,
        "ends_at": ends.isoformat() if ends else None,
    }


def test_a_marathon_with_no_end_never_ends_by_itself():
    assert ma.end_of(row(1, None, NOW - timedelta(days=30))) is None
    assert not ma.is_ended(row(1, None, NOW - timedelta(days=30)), NOW, 0)


def test_it_ends_only_once_the_grace_after_its_last_run_has_passed():
    ended = row(1, NOW - timedelta(days=7, minutes=1))
    assert ma.is_ended(ended, NOW, 7)
    assert not ma.is_ended(row(1, NOW - timedelta(days=6)), NOW, 7)
    assert ma.is_ended(row(1, NOW - timedelta(minutes=1)), NOW, 0)
    assert not ma.is_ended(row(1, NOW + timedelta(minutes=1)), NOW, 0)


def test_a_negative_grace_reads_as_the_same_day():
    assert ma.is_ended(row(1, NOW - timedelta(minutes=1)), NOW, -5)


def test_the_end_is_never_before_the_start():
    found = row(1, NOW - timedelta(days=9), NOW - timedelta(days=8))
    assert ma.end_of(found) == NOW - timedelta(days=8)


def test_a_tick_takes_the_one_that_ended_longest_ago():
    rows = [
        row(3, NOW - timedelta(days=9)),
        row(2, NOW - timedelta(days=20)),
        row(1, NOW + timedelta(days=1)),
        row(4, None),
    ]
    assert ma.first_ended(rows, NOW, 7)["id"] == 2
    assert ma.first_ended([rows[2], rows[3]], NOW, 7) is None
    assert ma.first_ended([], NOW, 7) is None


def test_a_why_nobody_wrote_reads_as_ended():
    assert ma.clean_why("staff") == "staff"
    assert ma.clean_why("removed") == "removed"
    assert ma.clean_why("bogus") == "ended"
    assert set(ma.WHY_WORDS) == set(ma.WHYS)


def test_a_page_is_clamped_and_a_bad_number_takes_the_default():
    assert ma.page_of(None, None) == (ma.PAGE_LIMIT, 0)
    assert ma.page_of("x", "-3") == (ma.PAGE_LIMIT, 0)
    assert ma.page_of(0, 10) == (1, 10)
    assert ma.page_of(10_000, 5) == (ma.PAGE_MAX, 5)


def test_the_two_panel_moves_sit_on_rows_with_room():
    assert ma.ARCHIVE_MOVE.row == 4 and ma.ARCHIVE_LIST_MOVE.row == 3
    assert ma.ARCHIVE_MOVE.action != ma.ARCHIVE_LIST_MOVE.action
