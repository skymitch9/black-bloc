from datetime import UTC, datetime, timedelta

import pytest

from black_bloc.events import (
    APPROVED,
    CANCELLED,
    DEFAULT_DURATION_MINUTES,
    DENIED,
    DESCRIPTION_LIMIT,
    DONE,
    LIVE,
    MAX_DURATION_MINUTES,
    OPEN_STATUSES,
    PENDING,
    STATUSES,
    SWEPT_STATUSES,
    TITLE_LIMIT,
    TRANSITIONS,
    announce_text,
    build_card,
    can_transition,
    channel_name,
    clamp,
    describe_duration,
    ends_at,
    golive_text,
    is_due,
    mentions,
    parse_duration,
    slugify,
    start_error,
)
from black_bloc.timezones import START_EXAMPLE, unix

WHEN = datetime(2026, 9, 15, 2, 30, tzinfo=UTC)


def test_slugify_keeps_only_what_discord_allows_in_a_channel_name():
    assert slugify("Sky's Block Party!") == "sky-s-block-party"
    assert slugify("  spaced   out  ") == "spaced-out"
    assert slugify("Ünïcödé Ríde") == "unicode-ride"
    assert slugify("---") == ""
    assert slugify(None) == ""
    assert slugify("🎉🎉🎉") == ""


def test_a_channel_name_is_the_status_then_the_person_then_the_event():
    assert channel_name(PENDING, "sky", "Block Party") == "pending-sky-block-party"
    assert channel_name(APPROVED, "sky", "Block Party") == "approved-sky-block-party"
    assert channel_name(DONE, "sky", "Block Party") == "done-sky-block-party"


def test_a_channel_name_never_passes_discord_s_hundred_characters():
    name = channel_name(PENDING, "A" * 60, "B" * 90)
    assert len(name) == 100
    assert not name.endswith("-")


def test_a_nameless_event_still_gets_a_channel_name():
    assert channel_name(PENDING, "🎉", "🎉") == "pending"
    assert channel_name(PENDING, "", "") == "pending"


def test_durations_are_read_in_hours_and_minutes():
    assert parse_duration("1h30m") == 90
    assert parse_duration("2h") == 120
    assert parse_duration("45m") == 45
    assert parse_duration("1h 30m") == 90
    assert parse_duration("1H30M") == 90


def test_an_empty_duration_means_two_hours():
    assert parse_duration("") == DEFAULT_DURATION_MINUTES
    assert parse_duration(None) == DEFAULT_DURATION_MINUTES
    assert parse_duration("   ") == DEFAULT_DURATION_MINUTES


def test_a_duration_black_bloc_cannot_read_is_refused_rather_than_guessed():
    assert parse_duration("2") is None
    assert parse_duration("a while") is None
    assert parse_duration("0h0m") is None
    assert parse_duration("90") is None
    assert parse_duration(f"{MAX_DURATION_MINUTES + 1}m") is None


def test_durations_read_back_the_way_they_were_written():
    assert describe_duration(90) == "1h 30m"
    assert describe_duration(120) == "2h"
    assert describe_duration(45) == "45m"
    assert describe_duration(0) == "0m"


def test_the_status_machine_refuses_the_moves_that_would_lose_a_decision():
    assert can_transition(PENDING, APPROVED) is True
    assert can_transition(PENDING, DENIED) is True
    assert can_transition(APPROVED, LIVE) is True
    assert can_transition(LIVE, DONE) is True
    assert can_transition(DENIED, APPROVED) is False
    assert can_transition(DONE, LIVE) is False
    assert can_transition(CANCELLED, APPROVED) is False
    assert can_transition(APPROVED, DENIED) is False
    assert can_transition("nonsense", APPROVED) is False


def test_every_status_can_be_cancelled_only_while_it_is_still_open():
    assert can_transition(PENDING, CANCELLED) is True
    assert can_transition(APPROVED, CANCELLED) is True
    assert can_transition(LIVE, CANCELLED) is True
    assert can_transition(DONE, CANCELLED) is False
    assert can_transition(DENIED, CANCELLED) is False


def test_the_transition_table_names_only_real_statuses():
    assert set(TRANSITIONS) == set(STATUSES)
    for allowed in TRANSITIONS.values():
        assert set(allowed) <= set(STATUSES)


def test_a_card_carries_both_hammertime_stamps():
    card = build_card(
        event_id=4,
        title="Block Party",
        requester_id=900,
        starts_at=WHEN,
        minutes=90,
        location="the park",
        description="bring a chair",
    )
    when = next(field.value for field in card.fields if field.name == "When")
    assert f"<t:{unix(WHEN)}:F>" in when
    assert f"<t:{unix(WHEN)}:R>" in when
    assert card.footer.text == "Event #4"


def test_a_card_clamps_what_the_requester_typed():
    card = build_card(
        event_id=1,
        title="T" * 300,
        requester_id=900,
        starts_at=WHEN,
        minutes=60,
        description="D" * 4000,
        location="L" * 300,
    )
    assert len(card.title) == TITLE_LIMIT
    assert len(card.description) == DESCRIPTION_LIMIT
    assert len(next(f.value for f in card.fields if f.name == "Where")) == 100


def test_a_card_leaves_out_what_was_not_given():
    card = build_card(
        event_id=1, title="Block Party", requester_id=900, starts_at=WHEN, minutes=60
    )
    names = [field.name for field in card.fields]
    assert "Where" not in names and "Why not" not in names
    assert card.description is None


def test_a_denied_card_says_why():
    card = build_card(
        event_id=1,
        title="Block Party",
        requester_id=900,
        starts_at=WHEN,
        minutes=60,
        status=DENIED,
        deny_reason="clashes with the marathon",
    )
    assert "clashes with the marathon" in [f.value for f in card.fields]


@pytest.mark.parametrize("status", STATUSES)
def test_every_status_has_a_colour(status):
    card = build_card(
        event_id=1,
        title="t",
        requester_id=1,
        starts_at=WHEN,
        minutes=60,
        status=status,
    )
    assert card.colour is not None


def test_only_the_configured_role_may_ever_be_pinged():
    none_allowed = mentions(None)
    assert none_allowed.everyone is False
    assert none_allowed.users is False
    assert none_allowed.roles is False

    one_allowed = mentions(42)
    assert one_allowed.everyone is False and one_allowed.users is False
    assert [role.id for role in one_allowed.roles] == [42]


def test_the_announcement_only_mentions_the_role_when_there_is_one():
    assert announce_text(None).startswith("A new event")
    assert announce_text(42).startswith("<@&42> ")
    assert golive_text("Block Party") == "**Block Party** is starting now!"
    assert golive_text("Block Party", 42).startswith("<@&42> ")


def test_a_title_full_of_pings_cannot_smuggle_one_into_the_go_live_line():
    said = golive_text("@everyone come here")
    assert "@everyone come here" in said
    assert mentions(None).everyone is False


def test_the_end_time_is_the_start_plus_the_duration():
    assert ends_at(WHEN, 90) == WHEN + timedelta(minutes=90)
    assert ends_at(WHEN, 0) == WHEN + timedelta(minutes=1)


def test_due_is_true_once_the_time_has_passed_and_never_on_a_bad_timestamp():
    now = datetime(2026, 9, 15, 3, 0, tzinfo=UTC)
    assert is_due(WHEN.isoformat(), now) is True
    assert is_due((now + timedelta(minutes=1)).isoformat(), now) is False
    assert is_due("sometime soon", now) is False
    assert is_due(None, now) is False


def test_the_start_refusal_shows_an_example_and_names_the_zone():
    said = start_error("next tuesday", "America/Phoenix", START_EXAMPLE)
    assert "next tuesday" in said
    assert START_EXAMPLE in said and "America/Phoenix" in said
    assert "/timezone set" in said


def test_clamp_trims_and_cuts():
    assert clamp("  hello  ", 100) == "hello"
    assert clamp("x" * 200, 10) == "x" * 10
    assert clamp(None, 10) == ""


def test_the_announcement_only_promises_an_interested_button_when_one_exists():
    with_event = announce_text(None, has_scheduled=True, event_url="https://discord.com/events/1/2")
    assert "Interested" in with_event
    assert "https://discord.com/events/1/2" in with_event

    no_url = announce_text(None, has_scheduled=True)
    assert "Interested" in no_url and "http" not in no_url

    without = announce_text(None, has_scheduled=False)
    assert "Interested" not in without
    assert "watch this channel" in without


def test_the_announcement_keeps_its_ping_prefix_whichever_wording_it_uses():
    assert announce_text(42, has_scheduled=True, event_url="u").startswith("<@&42> ")
    assert announce_text(42, has_scheduled=False).startswith("<@&42> ")


def test_the_statuses_a_finished_channel_sweep_covers_are_the_settled_ones():
    assert set(SWEPT_STATUSES) == {DONE, DENIED, CANCELLED}
    assert not set(SWEPT_STATUSES) & set(OPEN_STATUSES)
