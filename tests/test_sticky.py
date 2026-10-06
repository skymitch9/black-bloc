from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import discord
import pytest

from black_bloc import settings_store
from black_bloc import sticky as rules
from black_bloc.config import load_settings
from black_bloc.settings_store import KEY_CHOICES, KEY_TYPES, SettingError, SettingsStore

GUILD = 7
RUNS = 333
NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


def row(**given):
    base = {
        "channel_id": RUNS,
        "text": "How to submit a run.",
        "paused": 0,
        "trouble": None,
        "message_id": None,
        "posted_channel_id": None,
        "posted_at": None,
        "reposts": 0,
    }
    return base | given


def message(**given):
    base = {
        "guild": SimpleNamespace(id=GUILD),
        "webhook_id": None,
        "type": discord.MessageType.default,
        "author": SimpleNamespace(bot=False),
    }
    return SimpleNamespace(**(base | given))


@pytest.fixture
async def store(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    found = SettingsStore(db, load_settings(_env_file=None))
    await found.load()
    return found


def test_the_six_keys_are_posts_keys_with_the_briefed_defaults(store):
    assert set(settings_store.STICKY_KEYS) == {
        "sticky_mode",
        "sticky_after_messages",
        "sticky_min_seconds",
        "sticky_silent",
        "sticky_panel_minutes",
        "sticky_shadow_channel_id",
    }
    assert {settings_store.namespace_of(key) for key in settings_store.STICKY_KEYS} == {"posts"}
    assert KEY_TYPES["sticky_mode"] == "enum"
    assert KEY_CHOICES["sticky_mode"] == ("off", "shadow", "on")
    assert rules.mode_of(store, GUILD) == "shadow"
    assert rules.numbers(store, GUILD) == (5, 30, True)
    assert rules.panel_minutes(store, GUILD) == 10
    assert store.get(GUILD, "sticky_shadow_channel_id") is None


@pytest.mark.parametrize(
    ("key", "bad"),
    [
        ("sticky_after_messages", 0),
        ("sticky_after_messages", 101),
        ("sticky_min_seconds", 4),
        ("sticky_min_seconds", 3601),
        ("sticky_panel_minutes", 0),
        ("sticky_mode", "loud"),
    ],
)
async def test_a_number_outside_its_bounds_is_refused_with_the_reason(store, key, bad):
    with pytest.raises(SettingError) as refused:
        await store.set(GUILD, key, bad)
    assert len(str(refused.value).split()) > 6


def test_only_a_persons_own_message_counts():
    assert rules.counts(message()) is True
    assert rules.counts(message(type=discord.MessageType.reply)) is True
    assert rules.counts(message(author=SimpleNamespace(bot=True))) is False
    assert rules.counts(message(webhook_id=5)) is False
    assert rules.counts(message(type=discord.MessageType.pins_add)) is False
    assert rules.counts(message(guild=None)) is False


def test_the_gap_is_measured_from_the_last_copy_and_a_bad_time_never_blocks():
    posted = (NOW - timedelta(seconds=12)).isoformat()

    assert rules.seconds_left(row(posted_at=posted), NOW, 30) == 18.0
    assert rules.seconds_left(row(posted_at=posted), NOW, 10) == 0.0
    assert rules.seconds_left(row(posted_at=None), NOW, 30) == 0.0
    assert rules.seconds_left(row(posted_at="not a time"), NOW, 30) == 0.0
    assert rules.seconds_left(row(posted_at=(NOW + timedelta(hours=1)).isoformat()), NOW, 30) == 0.0
    assert rules.seconds_left(row(posted_at="2026-10-05T11:59:50"), NOW, 30) == 20.0


@pytest.mark.parametrize(
    ("given", "mode", "wanted"),
    [
        ({"trouble": "no"}, "on", rules.STOPPED),
        ({"paused": 1}, "on", rules.PAUSED),
        ({"paused": 1, "trouble": "no"}, "on", rules.STOPPED),
        ({}, "off", rules.OFF),
        ({}, "on", rules.WAITING),
        ({"message_id": 5, "posted_channel_id": RUNS}, "on", rules.LIVE),
        ({"message_id": 5, "posted_channel_id": 444}, "shadow", rules.REHEARSING),
    ],
)
def test_the_state_word_is_read_off_the_row_and_the_mode(given, mode, wanted):
    assert rules.state_of(row(**given), mode) == wanted
    assert wanted in rules.STATE_WORDS


def test_a_card_offers_only_the_moves_that_would_be_taken():
    def actions(**given):
        return [move.action for move in rules.card_buttons(row(**given))]

    assert actions() == [rules.EDIT, rules.PAUSE, rules.REMOVE, rules.BACK]
    assert actions(paused=1) == [rules.EDIT, rules.RESUME, rules.REMOVE, rules.BACK]
    assert actions(trouble="no") == [rules.EDIT, rules.RETRY, rules.REMOVE, rules.BACK]
    assert [move.action for move in rules.root_buttons(has_site=False)] == [
        rules.REFRESH,
        rules.LOGS,
    ]
    assert rules.root_buttons(has_site=True)[-1] is rules.SITE_MOVE


def test_the_list_says_each_stickys_state_and_why_one_stopped():
    posted = NOW.isoformat()
    lines = rules.root_lines(
        [
            row(message_id=5, posted_channel_id=RUNS, posted_at=posted, reposts=3),
            row(channel_id=444, trouble="Discord no longer has that channel."),
        ],
        "on",
    )

    assert lines[0] == "**mode** — on"
    assert lines[2] == f"<#{RUNS}> — live · <t:{int(NOW.timestamp())}:R> · moved 3×"
    assert lines[3] == "<#444> — stopped — Discord no longer has that channel."
    assert rules.root_lines([], "shadow")[-1] == rules.NONE_YET


def test_select_options_name_the_channel_and_say_when_it_is_gone():
    long = row(text="word " * 80)

    found = rules.sticky_options([row(), row(channel_id=444), long], {RUNS: "runs"})

    assert found[0] == ("#runs · How to submit a run.", RUNS)
    assert found[1][0].startswith("a channel Discord no longer has (444)")
    assert len(found[2][0]) <= 100
    assert [name for name, _, _ in rules.mode_options("shadow")] == ["off", "shadow", "on"]
    assert [now for _, _, now in rules.mode_options("shadow")] == [False, True, False]


def test_words_are_cleaned_and_refused_in_sentences():
    assert rules.clean("  hello \n") == "hello"
    assert rules.text_refusal("") == rules.NO_WORDS
    assert "1801" in rules.text_refusal("x" * 1801)
    assert rules.text_refusal("x" * rules.TEXT_MAX) is None
    assert rules.preview("a  b\nc") == "a b c"
    assert len(rules.preview("x" * 200)) == rules.PREVIEW_CHARS


def test_a_message_can_sit_in_text_and_announcement_channels_only():
    def kind(name):
        return SimpleNamespace(type=SimpleNamespace(name=name), send=lambda: None)

    assert rules.postable(kind("text")) and rules.postable(kind("news"))
    assert not rules.postable(kind("voice")) and not rules.postable(kind("category"))
    assert not rules.postable(SimpleNamespace())


async def test_one_row_per_channel_and_a_rewrite_clears_what_stopped_it(db):
    assert await rules.write_words(db, GUILD, RUNS, "first", 1) is True
    await rules.write_trouble(db, GUILD, RUNS, "no permission")
    assert await rules.running_channels(db) == []

    assert await rules.write_words(db, GUILD, RUNS, "second", 2) is False

    rows = await rules.rows_for_guild(db, GUILD)
    assert len(rows) == 1
    assert (rows[0]["text"], rows[0]["trouble"], rows[0]["updated_by"]) == ("second", None, 2)
    assert rows[0]["created_by"] == 1
    assert await rules.running_channels(db) == [(GUILD, RUNS)]


async def test_the_copy_the_pause_and_the_delete_are_each_one_write(db):
    await rules.write_words(db, GUILD, RUNS, "words", 1)

    await rules.write_copy(db, GUILD, RUNS, 9001, RUNS, at=NOW)
    await rules.write_copy(db, GUILD, RUNS, 9002, RUNS, moved=True, at=NOW)
    found = await rules.get_row(db, GUILD, RUNS)
    assert (found["message_id"], found["reposts"], found["posted_at"]) == (
        9002,
        1,
        NOW.isoformat(),
    )

    await rules.write_copy(db, GUILD, RUNS, None, None)
    await rules.write_paused(db, GUILD, RUNS, True, 3)
    found = await rules.get_row(db, GUILD, RUNS)
    assert (found["message_id"], found["posted_at"], found["paused"]) == (None, None, 1)
    assert not rules.is_running(found) and not rules.is_running(None)

    assert await rules.delete_row(db, GUILD, RUNS) is True
    assert await rules.delete_row(db, GUILD, RUNS) is False
    assert await rules.get_row(db, GUILD, RUNS) is None
