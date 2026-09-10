from datetime import UTC, date, datetime

import pytest

from black_bloc import when_picker as wp

PHOENIX = "America/Phoenix"
NEW_YORK = "America/New_York"
NOW = datetime(2026, 9, 10, 22, 7, tzinfo=UTC)


def labels(options):
    return [one.label for one in options]


def values(options):
    return [one.value for one in options]


def chosen(options):
    return [one.value for one in options if one.default]


def test_the_day_list_fills_the_select_exactly_and_keeps_the_typed_door_last():
    found = wp.day_options(PHOENIX, NOW)

    assert len(found) == wp.SELECT_CAP == 25
    assert found[-1].value == wp.LATER_VALUE
    assert found[-1].label == wp.LATER_LABEL
    assert len(set(values(found))) == len(found)


def test_the_first_two_days_are_named_and_the_rest_are_dates():
    found = labels(wp.day_options(PHOENIX, NOW))

    assert found[0] == "Today · Thu Sep 10"
    assert found[1] == "Tomorrow · Fri Sep 11"
    assert found[2] == "Sat Sep 12"


def test_the_day_list_is_read_in_the_drafts_own_zone_not_in_utc():
    """22:07 UTC is still the 10th in Phoenix and already the 11th in Tokyo."""
    assert wp.local_date(PHOENIX, NOW) == date(2026, 9, 10)
    assert wp.local_date("Asia/Tokyo", NOW) == date(2026, 9, 11)
    assert labels(wp.day_options("Asia/Tokyo", NOW))[0] == "Today · Fri Sep 11"


def test_the_day_list_walks_over_a_month_boundary_without_repeating_a_date():
    found = wp.day_options(PHOENIX, datetime(2026, 8, 25, 12, 0, tzinfo=UTC))
    days = values(found)[:-1]

    assert days[0] == "2026-08-25"
    assert "2026-09-01" in days
    assert days[-1] == "2026-09-17"
    assert len(set(days)) == len(days) == wp.DAY_COUNT


def test_the_day_list_crosses_a_dst_change_in_new_york_a_day_at_a_time():
    """The clocks go back on 2026-11-01; a day is a calendar day, not 24 hours."""
    found = values(wp.day_options(NEW_YORK, datetime(2026, 10, 28, 16, 0, tzinfo=UTC)))[:-1]

    assert found[:6] == [
        "2026-10-28",
        "2026-10-29",
        "2026-10-30",
        "2026-10-31",
        "2026-11-01",
        "2026-11-02",
    ]
    assert len(set(found)) == wp.DAY_COUNT


def test_a_typed_date_outside_the_list_takes_the_last_slot_and_is_the_selected_one():
    far = date(2027, 1, 5)
    found = wp.day_options(PHOENIX, NOW, picked=far, later=far)

    assert len(found) == wp.SELECT_CAP
    assert values(found)[-2] == "2027-01-05"
    assert chosen(found) == ["2027-01-05"]
    assert "2026-10-03" not in values(found)


def test_a_typed_date_already_in_the_list_does_not_take_a_second_slot():
    near = date(2026, 9, 12)
    found = wp.day_options(PHOENIX, NOW, picked=near, later=near)

    assert len(found) == wp.SELECT_CAP
    assert values(found).count("2026-09-12") == 1
    assert chosen(found) == ["2026-09-12"]


def test_the_day_count_can_never_push_the_list_past_discords_cap():
    assert len(wp.day_options(PHOENIX, NOW, count=90)) == wp.SELECT_CAP
    assert len(wp.day_options(PHOENIX, NOW, count=0)) == 2
    assert len(wp.day_options(PHOENIX, NOW, count=3)) == 4


def test_the_hours_are_a_twelve_hour_clock_with_a_twenty_four_hour_value():
    found = wp.hour_options()

    assert len(found) == 24
    assert labels(found)[0] == "12 AM"
    assert labels(found)[11] == "11 AM"
    assert labels(found)[12] == "12 PM"
    assert labels(found)[23] == "11 PM"
    assert values(found)[13] == "13"


def test_the_hour_picked_is_the_one_marked_and_hour_zero_is_not_read_as_nothing():
    assert chosen(wp.hour_options(0)) == ["0"]
    assert chosen(wp.hour_options(19)) == ["19"]
    assert chosen(wp.hour_options(None)) == []


@pytest.mark.parametrize(
    ("step", "count", "first_two"),
    [(5, 12, [":00", ":05"]), (15, 4, [":00", ":15"]), (60, 1, [":00"])],
)
def test_the_minute_step_decides_the_list_and_never_overflows_the_select(step, count, first_two):
    found = wp.minute_options(step)

    assert len(found) == count <= wp.SELECT_CAP
    assert labels(found)[: len(first_two)] == first_two


def test_a_step_outside_the_bounds_is_pulled_back_rather_than_crashing():
    assert wp.clean_step(0) == wp.STEP_MIN
    assert wp.clean_step(1000) == wp.STEP_MAX
    assert wp.clean_step("abc") == 15
    assert wp.clean_step(None) == 15
    assert len(wp.minute_options(0)) == 12


def test_minute_zero_is_marked_the_way_a_chosen_minute_is():
    assert chosen(wp.minute_options(15, 0)) == ["0"]
    assert chosen(wp.minute_options(15, 30)) == ["30"]
    assert chosen(wp.minute_options(15, None)) == []


def test_the_zone_list_says_what_the_clock_reads_there_now():
    found = wp.zone_options([PHOENIX, "Europe/London"], None, PHOENIX, NOW)

    assert labels(found)[0] == "America/Phoenix · now 3:07 PM"
    assert labels(found)[1] == "Europe/London · now 11:07 PM"
    assert found[-1].value == wp.OTHER_VALUE


def test_the_zone_list_falls_back_to_the_guilds_default_when_the_choices_are_empty():
    found = wp.zone_options([], None, "Europe/Berlin", NOW)

    assert values(found) == ["Europe/Berlin", wp.OTHER_VALUE]


def test_a_stored_zone_outside_the_choices_replaces_the_last_of_a_full_list():
    twenty_four = [f"Etc/GMT+{n}" for n in range(1, 13)] + [
        f"Etc/GMT-{n}" for n in range(1, 13)
    ]
    found = wp.zone_options(twenty_four, "Asia/Kolkata", PHOENIX, NOW)

    assert len(found) == wp.SELECT_CAP
    assert values(found)[-2] == "Asia/Kolkata"
    assert "Etc/GMT-12" not in values(found)
    assert chosen(found) == ["Asia/Kolkata"]


def test_a_stored_zone_outside_a_short_list_is_added_rather_than_replacing_anything():
    found = wp.zone_options([PHOENIX, "Europe/London"], "Asia/Kolkata", PHOENIX, NOW)

    assert values(found) == [PHOENIX, "Europe/London", "Asia/Kolkata", wp.OTHER_VALUE]
    assert chosen(found) == ["Asia/Kolkata"]


def test_more_zones_than_the_select_holds_are_cut_to_twenty_four():
    found = wp.zone_options([f"Etc/GMT+{n % 12 + 1}" for n in range(40)], None, PHOENIX, NOW)

    assert len(found) == wp.SELECT_CAP


def test_a_member_who_never_chose_sees_the_guilds_default_selected():
    found = wp.zone_options([PHOENIX, "Europe/London"], None, "Europe/London", NOW)

    assert chosen(found) == ["Europe/London"]


def test_the_durations_fit_the_select_and_every_value_is_one_parse_duration_reads():
    from black_bloc.events import parse_duration

    found = wp.duration_options()

    assert len(found) == 13 <= wp.SELECT_CAP
    for option, (minutes, _value, _label) in zip(found, wp.DURATIONS, strict=True):
        assert parse_duration(option.value) == minutes
    assert labels(found)[-1] == "All day"


def test_the_duration_a_setting_names_is_the_one_marked_and_odd_numbers_still_read():
    from black_bloc.events import parse_duration

    assert wp.duration_for(120) == "2h"
    assert chosen(wp.duration_options(wp.duration_for(120))) == ["2h"]
    assert wp.duration_for(1440) == "24h"
    assert parse_duration(wp.duration_for(37)) == 37
    assert wp.duration_for("nonsense") == ""


def test_an_empty_draft_says_all_three_things_it_still_needs():
    start, why = wp.resolve(wp.WhenDraft(zone=PHOENIX), NOW)

    assert start is None
    assert why == wp.NEEDS_WHEN.format(parts="a day, an hour and a minute")


def test_a_half_filled_draft_names_only_what_is_left():
    draft = wp.WhenDraft(zone=PHOENIX, day=date(2026, 9, 12))

    _start, why = wp.resolve(draft, NOW)
    assert why == wp.NEEDS_WHEN.format(parts="an hour and a minute")

    draft.hour = 19
    _start, why = wp.resolve(draft, NOW)
    assert why == wp.NEEDS_WHEN.format(parts="a minute")


def test_a_full_draft_reads_as_the_string_the_cogs_validator_already_takes():
    draft = wp.WhenDraft(zone=PHOENIX, day=date(2026, 9, 12), hour=19, minute=30)

    assert wp.resolve(draft, NOW) == ("2026-09-12 19:30", "")


def test_midnight_on_the_hour_is_a_time_and_not_a_missing_one():
    draft = wp.WhenDraft(zone=PHOENIX, day=date(2026, 9, 12), hour=0, minute=0)

    assert wp.resolve(draft, NOW) == ("2026-09-12 00:00", "")


def test_a_typed_date_that_parses_becomes_the_day_and_wins_over_the_dropdown():
    draft = wp.WhenDraft(zone=PHOENIX, day=date(2026, 9, 12), hour=19, minute=30)
    draft.later_text = "2027-01-05"

    assert draft.chosen_day() == date(2027, 1, 5)
    assert wp.resolve(draft, NOW) == ("2027-01-05 19:30", "")


def test_a_typed_date_that_does_not_parse_is_kept_and_said_rather_than_thrown_away():
    draft = wp.WhenDraft(zone=PHOENIX, hour=19, minute=30, later_text="next tuesday")

    start, why = wp.resolve(draft, NOW)

    assert start is None
    assert draft.later_text == "next tuesday"
    assert "next tuesday" in why and "YYYY-MM-DD" in why


def test_a_bad_typed_date_is_said_before_the_missing_hour_so_one_line_is_enough():
    draft = wp.WhenDraft(zone=PHOENIX, later_text="soon")

    _start, why = wp.resolve(draft, NOW)

    assert why.startswith("**soon**")


def test_a_very_long_typed_date_is_cut_before_it_reaches_the_sentence():
    draft = wp.WhenDraft(zone=PHOENIX, later_text="x" * 500)

    _start, why = wp.resolve(draft, NOW)

    assert "x" * 80 in why and "x" * 81 not in why


def test_parse_day_takes_the_one_shape_and_refuses_the_rest():
    assert wp.parse_day("2026-09-14") == date(2026, 9, 14)
    assert wp.parse_day(" 2026-09-14 ") == date(2026, 9, 14)
    assert wp.parse_day("14/09/2026") is None
    assert wp.parse_day("2026-13-01") is None
    assert wp.parse_day("") is None
    assert wp.parse_day(None) is None


def test_a_zone_this_machine_cannot_resolve_still_renders_a_list():
    """A stored zone that tzdata dropped must not take the picker down with it."""
    found = wp.zone_options(["Middle/Earth", PHOENIX], None, PHOENIX, NOW)

    assert labels(found)[0].startswith("Middle/Earth · now ")
    assert len(found) == 3
