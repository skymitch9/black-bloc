from datetime import UTC, datetime, timedelta

from black_bloc import spotlight
from black_bloc.golive import StreamInfo
from black_bloc.settings_store import SPOTLIGHT_BUMP_TEMPLATE

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def row(**fields):
    base = {
        "id": 1,
        "guild_id": 7,
        "twitch_login": "gamesdonequick",
        "display_name": "GamesDoneQuick",
        "note": None,
        "expires_at": None,
        "bump_hours": None,
        "pin": 1,
        "event_id": None,
    }
    return base | fields


def session(**fields):
    base = {
        "id": 3,
        "spotlight_id": 1,
        "started_at": NOW.isoformat(),
        "ended_at": None,
        "last_bump_at": None,
        "bump_count": 0,
        "title": "AGDQ 2027",
        "game": "Celeste",
        "url": "https://www.twitch.tv/gamesdonequick",
        "mode": "on",
    }
    return base | fields


def test_a_channel_name_is_read_out_of_a_name_an_at_handle_or_a_whole_address():
    assert spotlight.clean_login("GamesDoneQuick") == "gamesdonequick"
    assert spotlight.clean_login("@GamesDoneQuick") == "gamesdonequick"
    assert spotlight.clean_login("https://twitch.tv/GamesDoneQuick") == "gamesdonequick"
    assert spotlight.clean_login("https://www.twitch.tv/gdq?foo=1") == "gdq"


def test_a_name_that_is_not_a_channel_is_refused_rather_than_guessed():
    assert spotlight.clean_login("games done quick") is None
    assert spotlight.clean_login("") is None
    assert spotlight.clean_login(None) is None
    assert spotlight.clean_login("a" * 26) is None


def test_login_from_url_only_answers_for_a_twitch_address():
    assert spotlight.login_from_url("https://www.twitch.tv/gamesdonequick") == "gamesdonequick"
    assert spotlight.login_from_url("https://youtube.com/@gdq") is None
    assert spotlight.login_from_url("the bar at 8") is None


def test_a_kept_row_never_expires_and_reads_kept():
    kept = row(expires_at=None)
    assert spotlight.keeps_forever(kept) is True
    assert spotlight.is_expired(kept, NOW) is False
    assert spotlight.until_words(kept) == "kept"
    assert spotlight.announced_words(kept) == "spotlight · kept"


def test_a_dated_row_expires_at_its_date_and_reads_until_that_day():
    soon = row(expires_at=(NOW + timedelta(days=10)).isoformat())
    assert spotlight.is_expired(soon, NOW) is False
    assert spotlight.is_expired(soon, NOW + timedelta(days=11)) is True
    assert spotlight.until_words(soon) == "until 30 Sep"
    assert spotlight.announced_words(soon) == "spotlight · until 30 Sep"


def test_an_unreadable_date_leaves_the_row_alone_rather_than_purging_it():
    assert spotlight.is_expired(row(expires_at="whenever"), NOW) is False


def test_the_bump_is_measured_from_the_start_until_there_has_been_one():
    live = session()
    assert spotlight.bump_due(live, 4, NOW).due is False
    assert spotlight.bump_due(live, 4, NOW + timedelta(hours=3, minutes=59)).due is False
    ready = spotlight.bump_due(live, 4, NOW + timedelta(hours=4))
    assert ready.due is True and ready.due_at == NOW + timedelta(hours=4)


def test_after_one_bump_the_next_is_measured_from_that_bump_not_from_the_start():
    bumped = session(last_bump_at=(NOW + timedelta(hours=4)).isoformat(), bump_count=1)
    assert spotlight.bump_due(bumped, 4, NOW + timedelta(hours=5)).due is False
    assert spotlight.bump_due(bumped, 4, NOW + timedelta(hours=8)).due is True


def test_a_session_that_is_over_is_never_bumped_again():
    over = session(ended_at=(NOW + timedelta(hours=1)).isoformat())
    assert spotlight.bump_due(over, 1, NOW + timedelta(days=9)).due is False


def test_a_rows_own_hours_beat_the_key_and_a_blank_one_falls_back_to_it():
    assert spotlight.bump_hours_for(row(bump_hours=6), 4) == 6
    assert spotlight.bump_hours_for(row(bump_hours=None), 4) == 4
    assert spotlight.bump_hours_for(row(bump_hours=0), 4) == 4
    assert spotlight.bump_hours_for(row(bump_hours="nonsense"), 4) == 4


def test_days_become_a_date_and_nothing_becomes_kept_for_ever():
    assert spotlight.expiry_in_days(None) is None
    assert spotlight.expiry_in_days("") is None
    assert spotlight.expiry_in_days(0) is None
    when = spotlight.expiry_in_days(7, NOW)
    assert when is not None and when.startswith("2026-09-27")


def test_an_events_spotlight_runs_to_its_end_plus_the_slack():
    ends = (NOW + timedelta(hours=6)).isoformat()
    assert spotlight.expiry_for_event(ends, 2).startswith("2026-09-20T20:00")
    assert spotlight.expiry_for_event(ends, 0).startswith("2026-09-20T18:00")
    assert spotlight.expiry_for_event(None, 2) is None


def test_extending_a_row_that_has_run_out_counts_from_today():
    stale = row(expires_at=(NOW - timedelta(days=30)).isoformat())
    assert spotlight.extended_by_days(stale, 7, NOW).startswith("2026-09-27")
    ahead = row(expires_at=(NOW + timedelta(days=3)).isoformat())
    assert spotlight.extended_by_days(ahead, 7, NOW).startswith("2026-09-30")


def test_the_reminder_fills_the_five_placeholders_and_tidies_what_is_missing():
    info = StreamInfo(url="https://www.twitch.tv/gdq", game="Celeste", platform="Twitch")
    said = spotlight.bump_render(SPOTLIGHT_BUMP_TEMPLATE, info, "GamesDoneQuick", "4 h")
    assert said == (
        "**GamesDoneQuick** is still live — **Celeste**, 4 h so far. https://www.twitch.tv/gdq"
    )


def test_a_reminder_with_no_game_reads_something_rather_than_empty_bold():
    info = StreamInfo(url="https://www.twitch.tv/gdq", platform="Twitch")
    said = spotlight.bump_render(SPOTLIGHT_BUMP_TEMPLATE, info, "GDQ", "1 h")
    assert "**something**" in said and "****" not in said


def test_unreadable_wording_falls_back_to_the_default_rather_than_posting_nothing():
    info = StreamInfo(url="u", game="g", platform="Twitch")
    said = spotlight.bump_render("{name} {nope", info, "GDQ", "2 h")
    assert said.startswith("**GDQ** is still live")


def test_blank_wording_is_the_default_too():
    info = StreamInfo(url="u", game="g", platform="Twitch")
    assert spotlight.bump_render("   ", info, "GDQ", "2 h").startswith("**GDQ** is still live")


def test_a_session_becomes_a_twitch_streaminfo_even_when_the_row_kept_no_url():
    info = spotlight.info_of(session(url=None), "gamesdonequick")
    assert info.url == "https://www.twitch.tv/gamesdonequick" and info.platform == "Twitch"
    assert spotlight.info_of(session(), "gdq").game == "Celeste"


def test_the_panel_line_says_the_date_whether_it_is_live_and_any_note():
    kept = row(note="the owner's marathon channel")
    said = spotlight.panel_line(kept, True)
    assert "**gamesdonequick**" in said and "kept" in said
    assert "**live now**" in said and "the owner's marathon channel" in said
    assert "**live now**" not in spotlight.panel_line(kept, False)


def test_the_added_sentence_names_the_date_the_hours_and_whether_it_pins():
    said = spotlight.added_said(row(pin=1), 4)
    assert "kept" in said and "every 4 hours" in said and "pins the announcement" in said
    assert "leaves the announcement unpinned" in spotlight.added_said(row(pin=0), 4)


def test_the_duplicate_refusal_offers_extend_rather_than_a_bare_no():
    said = spotlight.ALREADY_SPOTLIT.format(login="gamesdonequick")
    assert "Extend" in said and "nothing was added" in said


def test_a_pin_refusal_says_what_happened_what_it_needs_and_what_did_not_change():
    said = spotlight.PIN_REFUSED.format(login="gdq", reason="Forbidden: 403")
    assert "could not be pinned" in said and "Manage Messages" in said
    assert "Nothing else about the spotlight changed" in said


def test_display_falls_back_to_the_login_when_nobody_has_named_the_channel():
    assert spotlight.display_for(row(display_name=None)) == "gamesdonequick"
    assert spotlight.display_for(row()) == "GamesDoneQuick"


def test_the_opt_out_sentence_says_what_became_of_an_announcement_that_was_out():
    off = row(announce=0)
    assert "announcement that was out" not in spotlight.announce_said(off)
    for post in ("end", "delete", "leave"):
        said = spotlight.announce_said(off, post)
        assert "is opted out" in said and "golive_channel_optout_post" in said
    assert "edited to say the stream has ended" in spotlight.announce_said(off, "end")
    assert "has been deleted" in spotlight.announce_said(off, "delete")
    assert "left exactly as it was posted" in spotlight.announce_said(off, "leave")


def test_opting_back_in_never_carries_the_clause_and_neither_does_an_unknown_word():
    assert "announcement that was out" not in spotlight.announce_said(row(announce=1), "end")
    assert "announcement that was out" not in spotlight.announce_said(row(announce=0), "nope")


def test_the_spotlight_off_sentence_says_the_pin_came_off_when_one_did():
    off = row(spotlight=0)
    assert "unpinned" not in spotlight.spotlight_said(off)
    assert "has been unpinned" in spotlight.spotlight_said(off, spotlight.UNPINNED)
    assert "unpinned" not in spotlight.spotlight_said(row(spotlight=1), spotlight.UNPINNED)


def test_the_spotlight_on_sentence_says_what_became_of_the_pin():
    on = row(spotlight=1)
    assert spotlight.spotlight_said(on) == spotlight.SPOTLIT_SAID.format(login="gamesdonequick")
    assert spotlight.PINNED_NOW in spotlight.spotlight_said(on, spotlight.PINNED)
    assert spotlight.UNPINNED_ENDED_NOW in spotlight.spotlight_said(on, spotlight.UNPINNED_ENDED)
    refused = spotlight.PIN_REFUSED.format(login="gamesdonequick", reason="Forbidden")
    assert refused in spotlight.spotlight_said(on, refused)
    assert "end" not in spotlight.spotlight_said(on, "end").split("stays as it is.")[1]


# --- the owner's date range (2026-09-22): a spotlight has a START as well as an end ----------


def test_a_row_with_no_start_reads_exactly_as_it_always_did():
    assert spotlight.is_scheduled(row(), NOW) is False
    assert spotlight.range_words(row(expires_at=None)) == "kept"
    assert spotlight.range_words(row(expires_at=(NOW + timedelta(days=10)).isoformat())) == (
        "until 30 Sep"
    )


def test_a_start_still_ahead_is_scheduled_and_one_already_gone_is_not():
    ahead = row(starts_at=(NOW + timedelta(days=3)).isoformat())
    assert spotlight.is_scheduled(ahead, NOW) is True
    assert spotlight.is_scheduled(ahead, NOW + timedelta(days=4)) is False
    assert spotlight.is_scheduled(row(starts_at=(NOW - timedelta(days=1)).isoformat()), NOW) is (
        False
    )


def test_an_unreadable_start_is_treated_as_started_rather_than_stranding_the_row():
    assert spotlight.is_scheduled(row(starts_at="whenever"), NOW) is False
    assert spotlight.range_words(row(starts_at="whenever")) == "kept"


def test_a_range_reads_from_one_day_to_the_other_and_says_kept_when_there_is_no_end():
    both = row(
        starts_at=(NOW + timedelta(days=3)).isoformat(),
        expires_at=(NOW + timedelta(days=10)).isoformat(),
    )
    assert spotlight.range_words(both) == "from 23 Sep to 30 Sep"
    assert spotlight.range_words(row(starts_at=both["starts_at"])) == "from 23 Sep · kept"


def test_the_announced_cell_names_a_scheduled_row_and_a_started_one_differently():
    ahead = row(starts_at=(NOW + timedelta(days=3)).isoformat())
    assert spotlight.announced_words(ahead, NOW) == "spotlight · from 23 Sep · kept · scheduled"
    assert spotlight.announced_words(ahead, NOW + timedelta(days=4)) == (
        "spotlight · from 23 Sep · kept"
    )


def test_the_three_range_words_are_settings_keys_and_a_broken_one_falls_back():
    both = row(
        starts_at=(NOW + timedelta(days=3)).isoformat(),
        expires_at=(NOW + timedelta(days=10)).isoformat(),
    )
    assert spotlight.range_words(both, "{start} → {end}") == "23 Sep → 30 Sep"
    assert spotlight.range_words(both, "{nonsense}") == "from 23 Sep to 30 Sep"
    assert spotlight.scheduled_word("not yet") == "not yet"
    assert spotlight.announced_words(both, NOW, word="not yet").endswith("· not yet")


def test_a_typed_date_is_read_in_the_zone_it_was_typed_in():
    read, trouble = spotlight.read_moment("2026-09-30 19:00", "America/Phoenix")
    assert trouble is None and read == "2026-10-01T02:00:00+00:00"
    read, trouble = spotlight.read_moment("2026-09-30", "UTC")
    assert trouble is None and read == "2026-09-30T00:00:00+00:00"


def test_a_blank_box_is_not_a_refusal_it_is_now_or_for_ever():
    assert spotlight.read_moment("") == (None, None)
    assert spotlight.read_moment(None) == (None, None)
    assert spotlight.read_end("") == (None, None)


def test_a_date_nobody_can_read_is_refused_in_words_naming_what_was_typed():
    read, trouble = spotlight.read_moment("next tuesday", "UTC")
    assert read is None and trouble == spotlight.BAD_DATE
    said = spotlight.bad_date_said("next tuesday")
    assert "next tuesday" in said and "YYYY-MM-DD" in said


def test_the_end_box_still_takes_a_bare_number_of_days_so_the_old_box_keeps_working():
    read, trouble = spotlight.read_end("7", "UTC", NOW)
    assert trouble is None and read == (NOW + timedelta(days=7)).isoformat()


def test_a_whole_stored_timestamp_comes_back_out_of_the_box_it_went_into():
    assert spotlight.typed_moment("2026-10-01T02:00:00+00:00", "America/Phoenix") == (
        "2026-09-30 19:00"
    )
    assert spotlight.typed_moment(None) == ""
    read, trouble = spotlight.read_moment("2026-10-01T02:00:00+00:00")
    assert trouble is None and read == "2026-10-01T02:00:00+00:00"


def test_an_end_before_its_start_is_a_problem_and_a_kept_row_can_never_be_one():
    start = (NOW + timedelta(days=3)).isoformat()
    assert spotlight.range_problem(start, (NOW + timedelta(days=10)).isoformat()) is None
    assert spotlight.range_problem(start, (NOW + timedelta(days=1)).isoformat()) == (
        spotlight.END_BEFORE_START
    )
    assert spotlight.range_problem(start, start) == spotlight.END_BEFORE_START
    assert spotlight.range_problem(start, None) is None
    assert spotlight.range_problem(None, (NOW + timedelta(days=1)).isoformat()) is None


def test_a_start_already_gone_by_is_accepted_and_stored_as_given_never_rewritten():
    read, trouble = spotlight.read_moment("2020-01-02 10:00", "UTC")
    assert trouble is None and read == "2020-01-02T10:00:00+00:00"
    assert spotlight.range_problem(read, (NOW + timedelta(days=1)).isoformat()) is None


def test_the_backwards_refusal_names_both_days_and_is_a_settings_key():
    said = spotlight.end_before_start_said(
        (NOW + timedelta(days=3)).isoformat(), (NOW + timedelta(days=1)).isoformat()
    )
    assert "23 Sep" in said and "21 Sep" in said
    assert spotlight.end_before_start_said("x", "y", "{start}/{end}") == "x/y"


def test_the_panel_line_marks_a_scheduled_row_and_leaves_a_started_one_alone():
    ahead = row(starts_at=(NOW + timedelta(days=3)).isoformat())
    assert spotlight.panel_line(ahead, False, now=NOW).endswith("**scheduled**")
    assert "scheduled" not in spotlight.panel_line(ahead, False, now=NOW + timedelta(days=4))


def test_the_two_modal_labels_are_keys_and_are_clamped_to_what_discord_shows():
    assert spotlight.starts_label(None) == "Starts — blank means now"
    assert spotlight.ends_label("Ends") == "Ends"
    assert len(spotlight.starts_label("x" * 80)) == spotlight.LABEL_MAX
    assert spotlight.dates_button(None) == "Set dates…"
    assert spotlight.dates_button("Dates") == "Dates"


def test_the_dates_sentence_says_a_scheduled_row_will_stay_quiet_until_its_start():
    ahead = row(starts_at=(NOW + timedelta(days=3)).isoformat())
    said = spotlight.dates_said(ahead, NOW)
    assert "from 23 Sep · kept" in said and "before that start" in said
    assert "before that start" not in spotlight.dates_said(ahead, NOW + timedelta(days=4))


def test_what_a_row_says_it_was_added_as_reads_the_range_not_only_the_end():
    both = row(
        starts_at=(NOW + timedelta(days=3)).isoformat(),
        expires_at=(NOW + timedelta(days=10)).isoformat(),
    )
    assert "from 23 Sep to 30 Sep" in spotlight.added_said(both, 4)
