from datetime import UTC, datetime

import pytest

from black_bloc import polls


def counts(*pairs):
    return [
        {"position": index, "label": label, "votes": votes}
        for index, (label, votes) in enumerate(pairs)
    ]


def test_every_status_the_machine_names_has_a_row_of_its_own():
    assert set(polls.TRANSITIONS) == set(polls.STATUSES)
    for allowed in polls.TRANSITIONS.values():
        assert set(allowed) <= set(polls.STATUSES)


def test_a_reviewed_poll_walks_from_pending_to_open_and_never_backwards():
    assert polls.can_transition(polls.PENDING_REVIEW, polls.OPEN)
    assert polls.can_transition(polls.OPEN, polls.CLOSED)
    assert polls.can_transition(polls.CLOSED, polls.ARCHIVED)
    assert not polls.can_transition(polls.CLOSED, polls.OPEN)
    assert not polls.can_transition(polls.DENIED, polls.OPEN)
    assert not polls.can_transition(polls.ARCHIVED, polls.CLOSED)


def test_a_denied_or_archived_poll_is_the_end_of_the_line():
    assert polls.DENIED in polls.TERMINAL_STATUSES
    assert polls.ARCHIVED in polls.TERMINAL_STATUSES
    assert polls.OPEN not in polls.TERMINAL_STATUSES


def test_yes_no_and_rating_write_their_own_answers():
    assert polls.options_for(polls.YESNO, "ignored") == ["Yes", "No"]
    assert polls.options_for(polls.RATING, "") == ["1", "2", "3", "4", "5"]


def test_typed_options_are_split_on_pipes_and_blanks_are_dropped():
    assert polls.options_for(polls.SINGLE, "Pizza | Tacos ||  Neither ") == [
        "Pizza",
        "Tacos",
        "Neither",
    ]
    assert polls.split_options(None) == []


def test_a_poll_with_no_question_is_refused_in_words():
    said = polls.validate("   ", ["Yes", "No"], 24)
    assert said is not None and "needs a question" in said


def test_a_question_longer_than_discord_allows_names_both_numbers():
    said = polls.validate("q" * 301, ["Yes", "No"], 24)
    assert said is not None and "301" in said and str(polls.QUESTION_LIMIT) in said


def test_one_option_is_not_a_poll():
    said = polls.validate("Pizza?", ["Pizza"], 24)
    assert said is not None and "at least 2" in said


def test_an_option_longer_than_the_answer_limit_names_the_option():
    said = polls.validate("Q", ["fine", "x" * 56], 24)
    assert said is not None and str(polls.LABEL_LIMIT) in said and "x" in said


def test_two_options_that_read_the_same_are_refused_so_votes_do_not_split():
    said = polls.validate("Q", ["Pizza", "pizza"], 24)
    assert said is not None and "twice" in said


def test_a_length_discord_cannot_express_is_refused_with_the_range():
    for bad in (0, 769, "a while", 1.5, True, None):
        said = polls.validate("Q", ["Yes", "No"], bad)
        assert said is not None and str(polls.MAX_HOURS) in said
    assert polls.validate("Q", ["Yes", "No"], 1) is None
    assert polls.validate("Q", ["Yes", "No"], polls.MAX_HOURS) is None


def test_the_four_v1_kinds_all_land_on_the_native_surface():
    for kind in polls.NATIVE_KINDS:
        assert polls.surface_for(kind, False, polls.LIVE, 4) == polls.NATIVE


def test_an_anonymous_poll_goes_to_the_panel_because_native_lists_its_voters():
    assert polls.surface_for(polls.SINGLE, True, polls.LIVE, 3) == polls.PANEL
    assert polls.panel_reason(True, polls.LIVE, 3) == polls.PANEL_BECAUSE_ANONYMOUS


def test_hiding_results_until_close_goes_to_the_panel_rather_than_being_downgraded():
    assert polls.surface_for(polls.SINGLE, False, polls.AT_CLOSE, 3) == polls.PANEL
    assert polls.panel_reason(False, polls.AT_CLOSE, 3) == polls.PANEL_BECAUSE_HIDDEN


def test_more_than_ten_options_goes_to_the_panel_and_says_the_count():
    assert polls.surface_for(polls.SINGLE, False, polls.LIVE, 12) == polls.PANEL
    said = polls.panel_reason(False, polls.LIVE, 12)
    assert "12" in said and "10" in said


def test_the_first_thing_that_rules_native_out_is_the_thing_named():
    assert polls.panel_reason(True, polls.AT_CLOSE, 20) == polls.PANEL_BECAUSE_ANONYMOUS
    assert polls.panel_reason(False, polls.LIVE, 3) is None
    assert polls.panel_note(False, polls.LIVE, 3) is None
    assert polls.PANEL_BECAUSE_HIDDEN in polls.panel_note(False, polls.AT_CLOSE, 3)


def test_more_options_than_any_surface_carries_is_refused_outright():
    with pytest.raises(polls.NeedsPanel) as caught:
        polls.surface_for(polls.SINGLE, False, polls.LIVE, polls.MAX_PANEL_OPTIONS + 1)
    assert "26" in str(caught.value) and "25" in str(caught.value)


def test_a_date_poll_is_native_up_to_ten_slots_and_a_panel_past_them():
    assert polls.surface_for(polls.DATE, False, polls.LIVE, 10) == polls.NATIVE
    assert polls.surface_for(polls.DATE, False, polls.LIVE, 11) == polls.PANEL


@pytest.mark.parametrize("kind", polls.LATER_KINDS)
def test_a_kind_the_panel_owns_says_so_by_name(kind):
    with pytest.raises(polls.NeedsPanel) as caught:
        polls.surface_for(kind, False, polls.LIVE, 3)
    assert polls.NEXT_UPDATE in str(caught.value)


def test_a_kind_nobody_has_heard_of_is_refused_too():
    with pytest.raises(polls.NeedsPanel):
        polls.surface_for("wibble", False, polls.LIVE, 3)


def test_checkbox_and_date_let_somebody_pick_more_than_one():
    assert polls.is_multi(polls.CHECKBOX) is True
    assert polls.is_multi(polls.DATE) is True
    assert polls.is_multi(polls.SINGLE) is False


def test_the_close_time_is_the_hours_added_to_now():
    now = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)
    assert polls.closes_at(24, now) == datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    assert polls.closes_at(0, now) == datetime(2026, 8, 27, 13, 0, tzinfo=UTC)


def test_a_length_reads_in_days_once_it_is_longer_than_a_day():
    assert polls.describe_hours(6) == "6h"
    assert polls.describe_hours(24) == "1d"
    assert polls.describe_hours(30) == "1d 6h"


def test_the_bar_is_full_at_every_vote_and_empty_at_none():
    assert polls.bar(4, 4) == polls.FULL * polls.BAR_CELLS
    assert polls.bar(0, 4) == polls.EMPTY * polls.BAR_CELLS
    assert polls.bar(2, 4).count(polls.FULL) == polls.BAR_CELLS // 2


def test_a_poll_nobody_voted_in_never_divides_by_zero():
    assert polls.bar(0, 0) == polls.EMPTY * polls.BAR_CELLS
    assert polls.share(0, 0) == 0
    assert polls.results_text(counts(("Yes", 0), ("No", 0)), 0) is not None


def test_the_chart_puts_the_winner_first_and_marks_it():
    text = polls.results_text(counts(("Friday", 6), ("Saturday", 22), ("Sunday", 13)), 41)
    lines = text.splitlines()
    assert lines[0].startswith("Saturday") and "winner" in lines[0]
    assert lines[1].startswith("Sunday") and "winner" not in lines[1]
    assert "54%" in lines[0]


def test_a_tie_marks_nobody_as_the_winner():
    text = polls.results_text(counts(("Yes", 3), ("No", 3)), 6)
    assert "winner" not in text


def test_a_tie_is_named_on_the_card_instead():
    embed = polls.results_embed(
        poll_id=4, question="Q", counts=counts(("Yes", 3), ("No", 3)), total=6
    )
    fields = {field.name: field.value for field in embed.fields}
    assert "Winner" in fields and "**Yes**" in fields["Winner"] and "**No**" in fields["Winner"]


def test_the_winner_helpers_agree_about_an_empty_poll():
    assert polls.winners(counts(("Yes", 0), ("No", 0))) == []
    assert polls.winners([]) == []


def test_a_rating_poll_carries_the_mean_the_bars_cannot_show():
    rows = counts(("1", 1), ("2", 0), ("3", 0), ("4", 0), ("5", 3))
    assert polls.average_rating(rows) == 4.0
    embed = polls.results_embed(
        poll_id=1, question="How was it?", counts=rows, total=4, kind=polls.RATING
    )
    assert any(field.name == "Average" for field in embed.fields)


def test_a_mean_is_not_invented_for_answers_that_are_not_numbers():
    assert polls.average_rating(counts(("Pizza", 3), ("Tacos", 1))) is None
    embed = polls.results_embed(
        poll_id=1, question="Q", counts=counts(("Pizza", 3)), total=3, kind=polls.RATING
    )
    assert not any(field.name == "Average" for field in embed.fields)


def test_a_live_count_says_so_far_and_a_final_one_does_not():
    live = polls.results_embed(
        poll_id=1, question="Q", counts=counts(("Yes", 2)), total=2, approximate=True
    )
    final = polls.results_embed(poll_id=1, question="Q", counts=counts(("Yes", 2)), total=2)
    assert "so far" in dict((f.name, f.value) for f in live.fields)["Votes"]
    assert "so far" not in dict((f.name, f.value) for f in final.fields)["Votes"]


def test_the_results_card_names_the_poll_in_its_footer():
    embed = polls.results_embed(poll_id=9, question="Q", counts=counts(("Yes", 1)), total=1)
    assert embed.footer.text == "Poll #9"


def test_the_review_card_shows_every_option_and_the_length():
    embed = polls.review_card(
        poll_id=2,
        question="Pizza?",
        creator_id=900,
        kind=polls.SINGLE,
        labels=["Pizza", "Tacos"],
        hours=48,
    )
    fields = {field.name: field.value for field in embed.fields}
    assert "1. Pizza" in fields["Options"] and "2. Tacos" in fields["Options"]
    assert fields["Open for"] == "2d"
    assert fields["Who"] == "<@900>"
    assert embed.footer.text == "Poll #2"


def test_a_denied_card_carries_the_reason_the_creator_is_sent():
    embed = polls.review_card(
        poll_id=2,
        question="Q",
        creator_id=1,
        kind=polls.SINGLE,
        labels=["a", "b"],
        hours=1,
        status=polls.DENIED,
        deny_reason="not this week",
    )
    assert any(field.value == "not this week" for field in embed.fields)


def test_only_the_configured_role_may_be_pinged_by_a_poll():
    allowed = polls.mentions(55)
    assert allowed.everyone is False and allowed.users is False
    assert [role.id for role in allowed.roles] == [55]
    assert polls.mentions(None).roles is False


def test_the_opening_line_names_the_creator_and_pings_only_the_role():
    assert polls.open_text(900, 55) == "<@&55> <@900> started a poll."
    assert polls.open_text(900) == "<@900> started a poll."


def test_the_reminder_says_which_poll_and_when_it_closes():
    said = polls.reminder_text("Best day for the cookout?", "<t:1:R>")
    assert "Best day for the cookout?" in said and "<t:1:R>" in said
    assert "closes" not in polls.reminder_text("Q")


def test_a_thread_name_never_outgrows_what_discord_takes():
    assert polls.thread_name("x" * 200) == "x" * polls.THREAD_NAME_LIMIT
    assert polls.thread_name("  ") == "Poll"


def test_stored_options_become_the_shape_every_renderer_reads():
    rows = [
        {"position": 0, "label": "Yes", "final_votes": 3},
        {"position": 1, "label": "No", "final_votes": None},
    ]
    assert polls.counts_from_options(rows) == [
        {"position": 0, "label": "Yes", "votes": 3},
        {"position": 1, "label": "No", "votes": 0},
    ]


def test_a_start_date_is_read_with_or_without_a_time_of_day():
    assert polls.parse_day("2026-09-05") is not None
    assert polls.parse_day("2026-09-05 19:00") is not None
    assert polls.parse_day("5 September") is None
    assert polls.parse_day("") is None


def test_a_date_read_in_the_server_zone_comes_back_as_utc():
    found = polls.parse_day("2026-09-05 19:00")
    assert found.tzinfo is UTC
    assert (found.day, found.hour) == (6, 2)


def test_the_twelve_hour_clock_drops_a_zero_minute_and_keeps_a_real_one():
    at = datetime(2026, 8, 30, 19, 0, tzinfo=UTC)
    assert polls.clock_label(at) == "7 pm"
    assert polls.clock_label(at.replace(minute=30)) == "7:30 pm"
    assert polls.clock_label(at.replace(hour=0)) == "12 am"
    assert polls.clock_label(at.replace(hour=12)) == "12 pm"


def test_a_day_slot_reads_as_plain_text_by_default_and_a_stamp_when_asked():
    at = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    assert polls.slot_label(at, with_time=False) == "Sun 30 Aug"
    assert polls.slot_label(at, with_time=False, form=polls.DATE_TIMESTAMP) == (
        f"<t:{int(at.timestamp())}:D>"
    )
    assert polls.slot_label(at, with_time=True, form=polls.DATE_TIMESTAMP).endswith(":f>")


def test_day_steps_generate_one_slot_a_day_with_no_time_of_day_on_them():
    made = polls.date_slots("2026-09-05", 3, 1, polls.STEP_DAYS)
    assert [row["label"] for row in made] == ["Sat 05 Sep", "Sun 06 Sep", "Mon 07 Sep"]
    assert all("·" not in row["label"] for row in made)
    assert made[0]["value"] < made[1]["value"] < made[2]["value"]


def test_an_hourly_step_puts_the_time_of_day_on_every_slot():
    made = polls.date_slots("2026-09-05 18:00", 3, 2, polls.STEP_HOURS)
    assert [row["label"] for row in made] == [
        "Sat 05 Sep · 6 pm",
        "Sat 05 Sep · 8 pm",
        "Sat 05 Sep · 10 pm",
    ]


def test_a_start_with_a_time_keeps_it_even_when_the_step_is_in_days():
    made = polls.date_slots("2026-09-05 19:30", 2, 1, polls.STEP_DAYS)
    assert made[0]["label"] == "Sat 05 Sep · 7:30 pm"


def test_every_generated_slot_label_fits_what_discord_takes():
    made = polls.date_slots("2026-09-05 19:30", polls.MAX_SLOTS, 1, polls.STEP_DAYS)
    assert len(made) == polls.MAX_SLOTS
    assert all(len(row["label"]) <= polls.LABEL_LIMIT for row in made)


def test_a_date_poll_with_no_start_is_refused_before_anything_is_generated():
    assert polls.date_trouble("", 5, 1, polls.STEP_DAYS) == polls.DATE_NEEDS_A_START
    assert polls.date_slots("", 5, 1, polls.STEP_DAYS) == []


@pytest.mark.parametrize(
    "start, slots, step, unit",
    [
        ("nonsense", 5, 1, polls.STEP_DAYS),
        ("2026-09-05", 1, 1, polls.STEP_DAYS),
        ("2026-09-05", polls.MAX_SLOTS + 1, 1, polls.STEP_DAYS),
        ("2026-09-05", 5, 0, polls.STEP_DAYS),
        ("2026-09-05", 5, polls.MAX_STEP + 1, polls.STEP_HOURS),
        ("2026-09-05", 5, 1, "fortnights"),
        ("2026-09-05", True, 1, polls.STEP_DAYS),
    ],
)
def test_a_date_poll_that_cannot_be_laid_out_is_refused_in_words(start, slots, step, unit):
    said = polls.date_trouble(start, slots, step, unit)
    assert said and "nothing was posted" in said


def test_a_workable_date_poll_is_not_refused():
    assert polls.date_trouble("2026-09-05", 7, 1, polls.STEP_DAYS) is None


def test_a_recurrence_is_one_token_the_row_carries_and_the_loop_reads():
    assert polls.cadence_token("daily") == "daily"
    assert polls.cadence_token("weekly", "Saturday") == "weekly:sat"
    assert polls.cadence_token("monthly", "12") == "monthly:12"
    assert polls.cadence_token("weekly", "funday") is None
    assert polls.cadence_token("yearly", None) is None


def test_a_day_of_the_month_no_month_has_is_refused_with_the_reason():
    assert polls.cadence_token("monthly", 29) is None
    said = polls.cadence_trouble("monthly", 31, "09:00", "America/Phoenix")
    assert said and "February" in said and str(polls.MAX_MONTH_DAY) in said


def test_a_time_of_day_or_zone_nobody_can_read_is_refused():
    assert "24-hour" in polls.cadence_trouble("daily", None, "7pm", "America/Phoenix")
    assert "tzdata" in polls.cadence_trouble("daily", None, "19:00", "Mars/Olympus")
    assert polls.cadence_trouble("daily", None, "19:00", "America/Phoenix") is None


def test_a_daily_poll_moves_to_tomorrow_once_today_has_gone_past():
    # 20:00 UTC is 13:00 in Phoenix, which has no DST and is UTC-7 all year.
    now = datetime(2026, 8, 27, 20, 0, tzinfo=UTC)
    assert polls.next_occurrence("daily", "09:00", "America/Phoenix", now) == datetime(
        2026, 8, 28, 16, 0, tzinfo=UTC
    )
    assert polls.next_occurrence("daily", "19:00", "America/Phoenix", now) == datetime(
        2026, 8, 28, 2, 0, tzinfo=UTC
    )


def test_a_weekly_poll_lands_on_its_own_weekday():
    now = datetime(2026, 8, 27, 20, 0, tzinfo=UTC)
    found = polls.next_occurrence("weekly:sat", "19:00", "America/Phoenix", now)
    assert found.astimezone(polls.timezones.zone("America/Phoenix")).strftime("%a") == "Sat"


def test_a_monthly_poll_rolls_into_the_next_year_at_december():
    found = polls.next_occurrence(
        "monthly:1", "07:30", "America/Phoenix", datetime(2026, 12, 15, tzinfo=UTC)
    )
    assert (found.year, found.month) == (2027, 1)


def test_a_cadence_nobody_can_read_produces_no_next_time_rather_than_a_guess():
    assert polls.next_occurrence("fortnightly", "09:00", "America/Phoenix") is None
    assert polls.next_occurrence("weekly:funday", "09:00", "America/Phoenix") is None
    assert polls.next_occurrence("monthly:31", "09:00", "America/Phoenix") is None
    assert polls.next_occurrence("daily", "9am", "America/Phoenix") is None
    assert polls.next_occurrence("daily", "09:00", "Mars/Olympus") is None


def test_a_cadence_reads_back_as_a_sentence_with_its_zone_named():
    assert polls.describe_cadence("daily", "09:00", "America/Phoenix") == (
        "every day at 09:00 America/Phoenix"
    )
    assert "Saturday" in polls.describe_cadence("weekly:sat", "19:00", "America/Phoenix")
    assert "22nd" in polls.describe_cadence("monthly:22", "07:30", "America/Phoenix")
    assert "1st" in polls.describe_cadence("monthly:1", "07:30", "America/Phoenix")
    assert "11th" in polls.describe_cadence("monthly:11", "07:30", "America/Phoenix")


def test_a_recurring_template_is_only_ever_cancelled_never_opened():
    assert polls.can_transition(polls.RECURRING, polls.CANCELLED)
    assert not polls.can_transition(polls.RECURRING, polls.OPEN)
    assert polls.RECURRING not in polls.OPEN_STATUSES
