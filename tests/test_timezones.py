from datetime import UTC, datetime

import pytest

from black_bloc.storage.db import Database
from black_bloc.timezones import (
    CHOICE_LIMIT,
    DEFAULT_TZ,
    START_EXAMPLE,
    get_timezone,
    is_known,
    known_timezones,
    local_time,
    parse_start,
    set_timezone,
    stamp,
    stored_timezone,
    suggest,
    unix,
    zone,
)

USER = 900


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "tz.sqlite3")
    await database.connect()
    try:
        yield database
    finally:
        await database.close()


def test_the_default_zone_resolves_on_this_machine():
    assert zone(DEFAULT_TZ) is not None
    assert is_known(DEFAULT_TZ) is True
    assert is_known("Middle/Earth") is False
    assert is_known(None) is False
    assert is_known("../../etc/passwd") is False


def test_the_example_start_is_one_the_parser_accepts():
    assert parse_start(START_EXAMPLE, DEFAULT_TZ) is not None


def test_phoenix_never_moves_because_arizona_has_no_summer_time():
    winter = parse_start("2026-01-14 19:30", "America/Phoenix")
    summer = parse_start("2026-07-14 19:30", "America/Phoenix")
    assert winter.utcoffset().total_seconds() == 0
    assert winter.hour == 2 and winter.day == 15
    assert summer.hour == 2 and summer.day == 15


def test_a_zone_that_does_move_gives_two_different_utc_times():
    winter = parse_start("2026-01-14 19:30", "America/New_York")
    summer = parse_start("2026-07-14 19:30", "America/New_York")
    assert winter.hour == 0 and winter.day == 15
    assert summer.hour == 23 and summer.day == 14


def test_a_start_read_in_a_zone_round_trips_back_to_what_was_typed():
    typed = "2026-09-14 19:30"
    when = parse_start(typed, "Europe/London")
    assert local_time("Europe/London", when) == typed


def test_a_start_black_bloc_cannot_read_is_refused_rather_than_guessed():
    assert parse_start("next tuesday", DEFAULT_TZ) is None
    assert parse_start("2026-09-14", DEFAULT_TZ) is None
    assert parse_start("2026-13-40 19:30", DEFAULT_TZ) is None
    assert parse_start("", DEFAULT_TZ) is None
    assert parse_start(None, DEFAULT_TZ) is None
    assert parse_start("2026-09-14 19:30", "Middle/Earth") is None


def test_the_autocomplete_prefers_what_the_name_starts_with_and_stops_at_twenty_five():
    hits = suggest("phoenix")
    assert "America/Phoenix" in hits
    assert len(suggest("a")) == CHOICE_LIMIT
    assert len(suggest("")) == CHOICE_LIMIT
    assert suggest("america/p")[0].startswith("America/P")
    assert suggest("qqqqq") == []


def test_the_autocomplete_takes_a_typed_space_for_the_underscore_in_a_name():
    assert "America/New_York" in suggest("new york")


def test_every_suggestion_is_a_zone_the_parser_will_accept():
    for name in suggest("europe/lo"):
        assert is_known(name)


def test_known_timezones_is_sorted_and_holds_the_default():
    names = known_timezones()
    assert names == sorted(names)
    assert DEFAULT_TZ in names


def test_a_card_stamp_carries_both_hammertime_forms():
    when = datetime(2026, 9, 14, 2, 30, tzinfo=UTC)
    seconds = unix(when)
    assert stamp(when) == f"<t:{seconds}:F> (<t:{seconds}:R>)"


async def test_a_member_with_no_row_is_read_as_phoenix(db):
    assert await stored_timezone(db, USER) is None
    assert await get_timezone(db, USER) == DEFAULT_TZ


async def test_a_chosen_zone_round_trips_and_can_be_changed(db):
    await set_timezone(db, USER, "Europe/London")
    assert await stored_timezone(db, USER) == "Europe/London"
    await set_timezone(db, USER, "Asia/Tokyo")
    assert await get_timezone(db, USER) == "Asia/Tokyo"


async def test_a_stored_zone_this_machine_cannot_resolve_falls_back_to_the_default(db):
    await db.conn.execute(
        "INSERT INTO user_timezones(user_id, tz, set_at) VALUES (?, 'Middle/Earth', '2026-08-26')",
        (USER,),
    )
    await db.conn.commit()

    assert await stored_timezone(db, USER) is None
    assert await get_timezone(db, USER) == DEFAULT_TZ
