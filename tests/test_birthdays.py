from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from black_bloc.birthdays import (
    DESCRIPTION_LIMIT,
    FALLBACK_ZONE,
    PANEL_BUTTONS,
    age,
    card_lines,
    celebrates_today,
    chunked,
    clamp_month_day,
    date_modal_title,
    date_problem,
    local_today,
    member_zone_name,
    month_day_text,
    month_lines,
    next_occurrence,
    observed,
    panel_buttons,
    parse_birthday_input,
    parse_color,
    render_description,
    stamp,
    status_lines,
    stored_prefill,
    stored_sentence,
    upcoming,
    upcoming_lines,
    year_problem,
)
from black_bloc.settings_store import BIRTHDAY_TEMPLATE, BIRTHDAY_TZ

PHOENIX = ZoneInfo(BIRTHDAY_TZ)
NEW_YORK = ZoneInfo("America/New_York")
TOKYO = ZoneInfo("Asia/Tokyo")


def test_clamp_keeps_every_pair_inside_a_real_calendar():
    assert clamp_month_day(2, 29) == (2, 29)
    assert clamp_month_day(2, 30) == (2, 29)
    assert clamp_month_day(13, 40) == (12, 31)
    assert clamp_month_day(0, 0) == (1, 1)
    assert clamp_month_day(4, 31) == (4, 30)
    assert clamp_month_day("nope", 1) == (1, 1)


def test_impossible_dates_are_refused_with_a_sentence_not_clamped():
    assert date_problem(6, 17) is None
    assert date_problem(2, 29) is None
    assert "no day" in date_problem(2, 30)
    assert "no month" in date_problem(13, 1)
    assert date_problem("x", 1).startswith("A birthday needs")


def test_the_birth_year_is_bounded():
    today = date(2026, 8, 26)
    assert year_problem(None, today) is None
    assert year_problem(1994, today) is None
    assert "not a birth year" in year_problem(2027, today)
    assert "not a birth year" in year_problem(1899, today)
    assert "whole number" in year_problem("soon", today)


def test_february_29_is_observed_on_the_28th_in_ordinary_years():
    assert observed(2, 29, 2024) == (2, 29)
    assert observed(2, 29, 2026) == (2, 28)
    assert observed(3, 1, 2026) == (3, 1)
    assert celebrates_today(2, 29, date(2026, 2, 28))
    assert not celebrates_today(2, 29, date(2026, 3, 1))
    assert celebrates_today(2, 29, date(2024, 2, 29))
    assert not celebrates_today(2, 29, date(2024, 2, 28))


def test_next_occurrence_is_local_midnight_and_rolls_into_next_year():
    now = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    when = next_occurrence(12, 24, PHOENIX, now)
    assert when == datetime(2026, 12, 24, 0, 0, tzinfo=PHOENIX)

    passed = next_occurrence(1, 2, PHOENIX, now)
    assert passed == datetime(2027, 1, 2, 0, 0, tzinfo=PHOENIX)

    today = next_occurrence(8, 26, PHOENIX, now)
    assert today == datetime(2026, 8, 26, 0, 0, tzinfo=PHOENIX)


def test_next_occurrence_of_a_leap_day_lands_on_the_28th_in_ordinary_years():
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    assert next_occurrence(2, 29, PHOENIX, now) == datetime(2026, 2, 28, 0, 0, tzinfo=PHOENIX)
    leap = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    assert next_occurrence(2, 29, PHOENIX, leap) == datetime(2024, 2, 29, 0, 0, tzinfo=PHOENIX)


def test_a_utc_minus_four_member_celebrates_the_evening_before_in_phoenix():
    moment = datetime(2026, 8, 10, 4, 30, tzinfo=UTC)

    assert local_today(NEW_YORK, moment) == date(2026, 8, 10)
    assert local_today(PHOENIX, moment) == date(2026, 8, 9)
    assert celebrates_today(8, 10, local_today(NEW_YORK, moment))
    assert not celebrates_today(8, 10, local_today(PHOENIX, moment))


def test_a_member_east_of_utc_celebrates_before_everyone_else():
    moment = datetime(2026, 8, 9, 15, 30, tzinfo=UTC)
    assert local_today(TOKYO, moment) == date(2026, 8, 10)
    assert celebrates_today(8, 10, local_today(TOKYO, moment))
    assert not celebrates_today(8, 10, local_today(PHOENIX, moment))


def test_an_unusable_zone_name_falls_back_to_the_server_zone():
    moment = datetime(2026, 8, 10, 4, 30, tzinfo=UTC)
    assert local_today("Mars/Olympus", moment) == local_today(PHOENIX, moment)
    assert local_today(None, moment) == local_today(PHOENIX, moment)
    assert FALLBACK_ZONE.utcoffset(None).total_seconds() == -7 * 3600


def test_age_is_the_years_they_turn_this_year():
    today = date(2026, 8, 26)
    assert age(1994, today) == 32
    assert age(None, today) is None
    assert age("", today) is None
    assert age("nope", today) is None
    assert age(2030, today) is None
    ahead = next_occurrence(1, 2, PHOENIX, datetime(2026, 8, 26, 12, 0, tzinfo=UTC))
    assert age(1990, ahead.date()) == 37
    assert age(1990, today) == 36


def test_the_colour_falls_back_when_it_is_not_a_hex_code():
    assert parse_color("#4eefff") == 0x4EEFFF
    assert parse_color("4eefff") == 0x4EEFFF
    assert parse_color("blue") == 0x4EEFFF
    assert parse_color(None) == 0x4EEFFF


def test_a_broken_template_falls_back_to_the_default_wording():
    assert render_description(BIRTHDAY_TEMPLATE, "PT") == "Happy Birthday **PT**!"
    assert render_description("{name} turns {age}!", "PT", 39) == "PT turns 39!"
    assert render_description("{nope}", "PT") == "Happy Birthday **PT**!"
    assert "@everyone" in render_description(BIRTHDAY_TEMPLATE, "@everyone")
    assert len(render_description("{name}", "x" * 5000)) == DESCRIPTION_LIMIT


def test_upcoming_orders_by_the_next_local_midnight():
    now = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    entries = [
        {"user_id": 1, "month": 12, "day": 24, "tz": BIRTHDAY_TZ, "year": 2002},
        {"user_id": 2, "month": 9, "day": 3, "tz": BIRTHDAY_TZ, "year": None},
        {"user_id": 3, "month": 1, "day": 2, "tz": BIRTHDAY_TZ, "year": None},
        {"user_id": 4, "month": 8, "day": 26, "tz": BIRTHDAY_TZ, "year": None},
    ]

    order = [u.user_id for u in upcoming(entries, now, limit=3)]

    assert order == [4, 2, 1]
    assert len(upcoming(entries, now, limit=0)) == 4
    assert stamp(next_occurrence(9, 3, PHOENIX, now)) == (
        f"<t:{int(datetime(2026, 9, 3, tzinfo=PHOENIX).timestamp())}:D>"
    )


def test_month_day_reads_as_words():
    assert month_day_text(9, 3) == "September 3"
    assert month_day_text(99, 99) == "December 31"


async def test_the_zone_lookup_prefers_the_member_s_own_zone(db):
    assert await member_zone_name(db, 5) == BIRTHDAY_TZ

    await db.conn.execute(
        "INSERT INTO user_timezones(user_id, tz, set_at) VALUES (5, 'America/New_York', 'now')"
    )
    await db.conn.commit()

    assert await member_zone_name(db, 5) == "America/New_York"
    assert await member_zone_name(db, 6) == BIRTHDAY_TZ


async def test_a_database_that_cannot_answer_still_gives_a_zone():
    class Broken:
        @property
        def conn(self):
            raise RuntimeError("not connected")

    assert await member_zone_name(Broken(), 1) == BIRTHDAY_TZ


# --- the panel's pure half (wave 1) ------------------------------------------------------


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("09-15", (9, 15, None)),
        ("09/15", (9, 15, None)),
        ("09.15", (9, 15, None)),
        ("09 15", (9, 15, None)),
        ("  9-5  ", (9, 5, None)),
        ("09-15-1994", (9, 15, 1994)),
        ("09/15/1994", (9, 15, 1994)),
        ("2-30", (2, 30, None)),
        ("2-29", (2, 29, None)),
        ("09-15-2200", (9, 15, 2200)),
    ],
)
def test_a_date_is_read_from_both_shapes_and_all_four_separators(typed, expected):
    assert parse_birthday_input(typed) == expected


@pytest.mark.parametrize(
    "typed",
    ["", None, "next tuesday", "15", "09-15-1994-3", "sept 15", "09--", "09-1a"],
)
def test_anything_that_is_not_two_or_three_numbers_is_unreadable(typed):
    assert parse_birthday_input(typed) is None


def test_the_modal_never_guesses_a_year():
    assert parse_birthday_input("09-15")[2] is None
    assert parse_birthday_input("09-15-1994")[2] == 1994


@pytest.mark.parametrize(
    ("has_date", "opted_out", "expected"),
    [
        (False, False, ("Set my birthday", "Refresh")),
        (True, False, ("Change my birthday", "Remove", "Opt out", "Refresh")),
        (True, True, ("Change my birthday", "Remove", "Opt in", "Refresh")),
        (False, True, ("Set my birthday", "Refresh")),
    ],
)
def test_the_button_table_is_data_and_the_unreachable_pair_falls_back(
    has_date, opted_out, expected
):
    row = panel_buttons(has_date, opted_out)
    assert tuple(one.label for one in row) == expected
    assert all(one.style in ("primary", "secondary", "success", "danger") for one in row)


def test_only_the_set_button_opens_a_modal():
    for key, row in PANEL_BUTTONS.items():
        assert [one.action for one in row if one.needs_modal] == ["set"], key


def test_the_confirmation_sentence_names_the_zone_and_the_next_one():
    when = datetime(2027, 8, 10, tzinfo=PHOENIX)

    said = stored_sentence("Your", 8, 10, 1987, BIRTHDAY_TZ, when)

    assert said.startswith("Your birthday is **August 10** (1987).")
    assert f"midnight in **{BIRTHDAY_TZ}**" in said
    assert stamp(when, "D") in said
    assert "(1987)" not in stored_sentence("Your", 8, 10, None, BIRTHDAY_TZ, when)


def test_a_card_reads_differently_for_you_and_for_somebody_else():
    when = datetime(2027, 8, 10, tzinfo=PHOENIX)

    mine = card_lines("PT", 8, 10, 1987, BIRTHDAY_TZ, when, 40, False, mine=True)
    theirs = card_lines("PT", 8, 10, 1987, BIRTHDAY_TZ, when, 40, False, mine=False)

    assert mine[0] == "**PT** — August 10 (1987), turning 40"
    assert theirs[0] == "**PT** — August 10, turning 40"
    assert mine[-1].startswith("You are **opted out**")
    assert theirs[-1].startswith("They are **opted out**")
    assert len(card_lines("PT", 8, 10, None, BIRTHDAY_TZ, when, None, True)) == 2


def test_the_upcoming_lines_name_each_person_and_their_own_date():
    entries = [
        {"user_id": 1, "month": 8, "day": 10, "year": None, "tz": BIRTHDAY_TZ},
        {"user_id": 2, "month": 1, "day": 2, "year": None, "tz": BIRTHDAY_TZ},
    ]

    lines = upcoming_lines(entries, upcoming(entries, limit=5))

    assert len(lines) == 2
    assert all(line.startswith("· <@") for line in lines)
    assert any("August 10" in line for line in lines)


def test_the_month_list_groups_by_month_and_marks_the_opted_out():
    rows = [
        {"month": 1, "day": 2, "user_id": 5, "source": "import", "opted_in": 1},
        {"month": 1, "day": 9, "user_id": 6, "source": "self", "opted_in": 0},
        {"month": 8, "day": 10, "user_id": 7, "source": "self", "opted_in": 1},
    ]

    lines = month_lines(rows)

    assert lines[0] == "**January**"
    assert lines[2].endswith("(self · opted out)")
    assert lines[3] == "**August**"
    assert month_lines([]) == []


def test_the_status_wording_is_health_not_liveness():
    lines = status_lines(
        {
            "mode": "shadow",
            "channel_id": 111,
            "template": "Happy Birthday **{name}**!",
            "color": "#4eefff",
            "role_id": None,
            "test_mode": True,
            "show_age": False,
            "totals": {"stored": 2, "opted_in": 1, "imported": 1, "self": 1},
            "staff": "2 role(s)",
            "last_run_at": None,
            "last_error": None,
            "loop_minutes": 5,
        }
    )

    text = "\n".join(lines)
    assert "**mode** — shadow" in text
    assert "**channel** — <#111>" in text
    assert "**role** — none (test mode gives no roles)" in text
    assert "**stored** — 2 (1 opted in · 1 imported · 1 set by the person)" in text
    assert "**last sweep** — not yet (every 5 minutes)" in text
    assert "**last error** — none" in text
    assert "import" not in text.replace("1 imported", "")


def test_the_modal_title_never_passes_discords_forty_five_characters():
    assert date_modal_title(True) == "Your birthday"
    assert date_modal_title(False, "Nadia") == "Set Nadia's birthday"
    assert len(date_modal_title(False, "N" * 90)) == 45


def test_a_stored_date_is_offered_back_in_the_shape_it_is_typed_in():
    assert stored_prefill(8, 10, None) == "08-10"
    assert stored_prefill(8, 10, 1987) == "08-10-1987"
    assert parse_birthday_input(stored_prefill(8, 10, 1987)) == (8, 10, 1987)


def test_long_reports_are_split_into_messages_discord_will_take():
    pages = chunked([f"line {n} " + "x" * 100 for n in range(60)])
    assert len(pages) > 1
    assert all(len(page) <= 1900 for page in pages)
    assert chunked([]) == []
