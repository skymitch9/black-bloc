from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import discord
import pytest

from black_bloc import questions as rules
from black_bloc.settings_store import QUESTION_DEFAULTS


class Store:
    def __init__(self, **values):
        self.values = dict(QUESTION_DEFAULTS) | {"default_timezone": "America/Phoenix"}
        self.values.update(values)

    def get(self, guild_id, key):
        return self.values.get(key)


def schedule(weekday="monday", clock="09:00", tz="America/Phoenix", grace=5, catchup=24):
    return rules.schedule_of(
        Store(
            question_weekday=weekday,
            question_time=clock,
            default_timezone=tz,
            question_grace_minutes=grace,
            question_catchup_hours=catchup,
        ),
        7,
    )


def message(content, author=1, kind=discord.MessageType.default, at=None):
    return SimpleNamespace(
        content=content,
        author=SimpleNamespace(id=author),
        type=kind,
        created_at=at or datetime(2026, 10, 19, 16, 0, tzinfo=UTC),
        id=55,
    )


def test_a_monday_nine_in_phoenix_is_sixteen_utc_all_year():
    found = schedule()
    for now in (
        datetime(2026, 1, 14, 12, 0, tzinfo=UTC),
        datetime(2026, 7, 15, 12, 0, tzinfo=UTC),
    ):
        last, following = rules.slots_around(now, found)
        assert last.weekday() == 0 and following.weekday() == 0
        assert (last.hour, last.minute) == (16, 0)
        assert (following.hour, following.minute) == (16, 0)
        assert following - last == timedelta(days=7)


def test_the_slot_moves_with_dst_in_a_zone_that_has_it():
    found = schedule(weekday="sunday", clock="09:00", tz="America/New_York")
    winter, _ = rules.slots_around(datetime(2026, 1, 20, tzinfo=UTC), found)
    summer, _ = rules.slots_around(datetime(2026, 7, 20, tzinfo=UTC), found)
    assert (winter.hour, summer.hour) == (14, 13)
    before, across = rules.slots_around(datetime(2026, 3, 5, tzinfo=UTC), found)
    assert (before.hour, across.hour) == (14, 13)
    assert across - before == timedelta(days=7, hours=-1)


@pytest.mark.parametrize("weekday", list(rules.QUESTION_WEEKDAYS))
def test_every_weekday_lands_on_its_own_day(weekday):
    found = schedule(weekday=weekday, clock="18:30", tz="Europe/London")
    last, following = rules.slots_around(datetime(2026, 10, 19, 12, 0, tzinfo=UTC), found)
    local = following.astimezone(found.tz)
    assert local.strftime("%A").lower() == weekday
    assert (local.hour, local.minute) == (18, 30)
    assert last < datetime(2026, 10, 19, 12, 0, tzinfo=UTC) < following


def test_the_slot_itself_is_the_last_one_at_its_minute():
    found = schedule()
    nine = datetime(2026, 10, 19, 16, 0, tzinfo=UTC)
    last, following = rules.slots_around(nine, found)
    assert last == nine and following == nine + timedelta(days=7)
    last, _ = rules.slots_around(nine - timedelta(seconds=1), found)
    assert last == nine - timedelta(days=7)


def test_an_unreadable_time_or_day_falls_back_to_monday_nine():
    found = rules.schedule_of(Store(question_time="nonsense", question_weekday="funday"), 7)
    assert (found.weekday, found.hour, found.minute) == (0, 9, 0)


@pytest.mark.parametrize(
    "content",
    [
        "What game got you into speedrunning?",
        "**What game got you into speedrunning?**",
        "what GAME got   you into\nspeedrunning?",
        "Question of the week! __What game got you into *speedrunning*?__ Reply below",
        "> What game got you into speedrunning?",
        "||What game got you into speedrunning?||",
    ],
)
def test_the_owners_post_matches_through_markdown_case_whitespace_and_extra_words(content):
    since = datetime(2026, 10, 19, 15, 45, tzinfo=UTC)
    found = rules.owner_post(
        [message(content, author=1)], 1, "What game got you into speedrunning?", since
    )
    assert found is not None


def test_someone_else_posting_the_same_words_is_not_the_owner():
    since = datetime(2026, 10, 19, 15, 45, tzinfo=UTC)
    found = rules.owner_post(
        [message("What game got you into speedrunning?", author=2)],
        1,
        "What game got you into speedrunning?",
        since,
    )
    assert found is None


def test_an_older_post_a_system_message_or_a_different_question_is_not_a_match():
    since = datetime(2026, 10, 19, 15, 45, tzinfo=UTC)
    body = "What game got you into speedrunning?"
    old = message(body, at=since - timedelta(minutes=1))
    pinned = message(body, kind=discord.MessageType.pins_add)
    other = message("What is your favourite category?")
    assert rules.owner_post([old, pinned, other], 1, body, since) is None
    assert rules.owner_post([message(body)], None, body, since) is None
    assert not rules.says_question("anything", "  ")


def test_the_template_fills_and_a_broken_one_falls_back():
    assert rules.rendered(Store(question_template="QOTW: {question}"), 7, "Why?") == "QOTW: Why?"
    assert rules.rendered(Store(question_template="{nope}"), 7, "Why?") == "Why?"


def test_the_thread_name_is_clipped_to_discords_hundred():
    name = rules.thread_name(Store(), 7, "x" * 300)
    assert len(name) == rules.THREAD_NAME_LIMIT
    assert rules.thread_name(Store(question_thread_name_template=" "), 7, "") == (
        rules.THREAD_FALLBACK
    )


def test_the_warning_names_the_day_and_time_in_the_servers_zone():
    found = schedule()
    slot = datetime(2026, 10, 19, 16, 0, tzinfo=UTC)
    text = rules.warn_text(Store(), 7, slot, found)
    assert "Monday" in text and "09:00" in text


def test_many_questions_split_one_per_line_and_blank_lines_are_dropped():
    assert rules.split_lines("one?\n\n  two?  \r\nthree?\n") == ["one?", "two?", "three?"]
    assert rules.split_lines("   \n") == []


def test_the_current_slot_is_last_weeks_only_while_it_is_still_pending():
    found = schedule()
    nine = datetime(2026, 10, 19, 16, 0, tzinfo=UTC)
    soon = nine + timedelta(hours=1)
    assert rules.current_slot(soon, found, {"status": rules.PENDING}) == nine
    assert rules.current_slot(soon, found, None) == nine + timedelta(days=7)
    late = nine + timedelta(hours=25)
    assert rules.current_slot(late, found, {"status": rules.PENDING}) == nine + timedelta(days=7)


@pytest.mark.parametrize(
    "status",
    [rules.POSTED, rules.SKIPPED, rules.SKIPPED_EMPTY, rules.MISSED, rules.TAKEN_DOWN],
)
def test_a_settled_slot_hands_this_week_to_the_next_one(status):
    nine = datetime(2026, 10, 19, 16, 0, tzinfo=UTC)
    soon = nine + timedelta(hours=1)
    assert rules.current_slot(soon, schedule(), {"status": status}) == nine + timedelta(days=7)


def test_the_channel_url_is_the_discord_link():
    assert rules.channel_url(1, 2) == "https://discord.com/channels/1/2"
    assert rules.channel_url(1, None) is None
