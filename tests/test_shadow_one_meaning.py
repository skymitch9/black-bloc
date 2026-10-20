import json
from types import SimpleNamespace

import pytest

from black_bloc import settings_store, shadow_one_meaning
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore

GUILD = 1073710702776299640
OTHER_GUILD = 99
AT = "2026-10-20T09:00:00+00:00"
LIVE_ROWS = {
    "golive_mode": "on",
    "youtube_live_mode": "on",
    "spotlight_mode": "on",
    "modmail_enabled": True,
    "youtube_mode": "on",
    "tempvoice_mode": "on",
    "rehearsal_note": "",
}
DEFAULT_ROWS = {
    "boot_status_mode": "on",
    "handoff_mode": "on",
    "golive_costream_mode": "on",
    "chat_greeting_via_model": "on",
    "pb_feed_posting_shadow": "Staff are still trying this out.",
    "pb_feed_no_channel_words": "nowhere yet — pb_feed_channel_id is blank",
    "points_modmail_off_said": "Runs reach staff through modmail.",
}


async def stored(db, guild_id, key, value):
    await db.conn.execute(
        "INSERT OR REPLACE INTO settings(guild_id, key, value, updated_by, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (guild_id, key, json.dumps(value), None, AT),
    )
    await db.conn.commit()


async def live_mirror(db):
    """The values read live through /api/settings 2026-10-20 02:13 Phoenix, plus the stale
    youtube_mode row and the blank rehearsal_note row the boot log names; the API cannot say
    which defaults are stored."""
    for key, value in LIVE_ROWS.items():
        await stored(db, GUILD, key, value)


async def keys_of(db, guild_id):
    cur = await db.conn.execute("SELECT key FROM settings WHERE guild_id = ?", (guild_id,))
    return {row["key"] for row in await cur.fetchall()}


async def value_of(db, guild_id, key):
    cur = await db.conn.execute(
        "SELECT value FROM settings WHERE guild_id = ? AND key = ?", (guild_id, key)
    )
    row = await cur.fetchone()
    return json.loads(row["value"]) if row is not None else None


async def actions(db):
    cur = await db.conn.execute("SELECT guild_id, kind, details FROM action_log ORDER BY id")
    found = await cur.fetchall()
    return [(row["guild_id"], row["kind"], json.loads(row["details"])) for row in found]


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    store = SettingsStore(db, load_settings(_env_file=None))
    await store.load()
    return SimpleNamespace(db=db, store=store, get_channel=lambda _id: None)


def test_every_retired_key_is_gone_from_the_registry_and_the_new_one_is_a_bool():
    for key in shadow_one_meaning.RETIRED_KEYS:
        assert key not in settings_store.KEY_TYPES, key
        assert key not in settings_store.KEY_HELP, key
    assert settings_store.KEY_TYPES["golive_youtube"] == "bool"
    assert settings_store.KEY_TYPES["chat_greeting_via_model"] == "bool"


async def test_the_dry_run_against_the_live_rows_drops_five_and_writes_golive_youtube(db):
    await live_mirror(db)

    [found] = await shadow_one_meaning.dry_run(db)

    assert found == {
        "guild_id": GUILD,
        "drop": {
            "youtube_live_mode": "on",
            "spotlight_mode": "on",
            "modmail_enabled": True,
            "youtube_mode": "on",
            "rehearsal_note": "",
        },
        "write": {"golive_youtube": {"before": None, "after": True}},
        "notes": [],
    }
    assert await value_of(db, GUILD, "youtube_live_mode") == "on", "a dry run writes nothing"


async def test_applying_twice_writes_once_drops_once_and_logs_one_row(bot, db):
    await live_mirror(db)

    first = await shadow_one_meaning.apply(bot)
    rows_after_first = await actions(db)
    second = await shadow_one_meaning.apply(bot)

    assert [one["guild_id"] for one in first] == [GUILD] and second == []
    assert await actions(db) == rows_after_first
    assert await keys_of(db, GUILD) == {"golive_mode", "golive_youtube", "tempvoice_mode"}
    assert await value_of(db, GUILD, "golive_youtube") is True
    [(guild_id, kind, details)] = rows_after_first
    assert (guild_id, kind) == (GUILD, "settings.migrated")
    assert details["build"] == "shadow-one-meaning"
    assert details["removed"] == [
        "modmail_enabled",
        "rehearsal_note",
        "spotlight_mode",
        "youtube_live_mode",
        "youtube_mode",
    ]
    assert details["written"] == {"golive_youtube": {"before": None, "after": True}}
    await bot.store.load()
    assert bot.store.get(GUILD, "golive_youtube") is True
    assert bot.store.get(GUILD, "golive_mode") == "on"


async def test_rows_stored_at_their_old_defaults_go_too_and_the_greeting_becomes_a_bool(bot, db):
    for key, value in DEFAULT_ROWS.items():
        await stored(db, GUILD, key, value)

    [found] = await shadow_one_meaning.apply(bot)

    assert sorted(found["drop"]) == sorted(set(DEFAULT_ROWS) - {"chat_greeting_via_model"})
    assert found["write"] == {"chat_greeting_via_model": {"before": "on", "after": True}}
    assert await keys_of(db, GUILD) == {"chat_greeting_via_model"}
    assert await value_of(db, GUILD, "chat_greeting_via_model") is True
    assert await shadow_one_meaning.apply(bot) == []


@pytest.mark.parametrize(
    ("was", "watches", "noted"),
    [("on", True, False), ("off", False, False), ("shadow", False, True)],
)
async def test_youtube_live_mode_maps_to_the_bool_and_shadow_fails_safe(
    bot, db, was, watches, noted
):
    await stored(db, GUILD, "youtube_live_mode", was)

    [found] = await shadow_one_meaning.apply(bot)

    assert await value_of(db, GUILD, "golive_youtube") is watches
    assert (shadow_one_meaning.YOUTUBE_SHADOW_WAS in found["notes"]) is noted


async def test_a_golive_youtube_already_stored_is_kept(bot, db):
    await stored(db, GUILD, "golive_youtube", False)
    await stored(db, GUILD, "youtube_live_mode", "on")

    [found] = await shadow_one_meaning.apply(bot)

    assert found["write"] == {}
    assert await value_of(db, GUILD, "golive_youtube") is False
    assert "youtube_live_mode" not in await keys_of(db, GUILD)


async def test_spotlight_off_under_a_live_golive_is_said_in_the_row(bot, db):
    await stored(db, GUILD, "spotlight_mode", "off")

    [found] = await shadow_one_meaning.apply(bot)

    assert found["notes"] == [
        "spotlights now follow golive_mode: spotlight_mode was off, golive_mode is shadow"
    ]
    [(_, _, details)] = await actions(db)
    assert details["notes"] == found["notes"]


async def test_spotlight_off_under_golive_off_says_nothing_new(bot, db):
    await stored(db, GUILD, "spotlight_mode", "off")
    await stored(db, GUILD, "golive_mode", "off")

    [found] = await shadow_one_meaning.apply(bot)

    assert found["notes"] == [] and found["drop"] == {"spotlight_mode": "off"}


async def test_only_guilds_with_a_retired_row_are_touched(bot, db):
    await stored(db, OTHER_GUILD, "golive_mode", "on")
    await stored(db, OTHER_GUILD, "chat_greeting_via_model", True)
    await live_mirror(db)

    found = await shadow_one_meaning.apply(bot)

    assert [one["guild_id"] for one in found] == [GUILD]
    assert await keys_of(db, OTHER_GUILD) == {"golive_mode", "chat_greeting_via_model"}


async def test_a_lost_log_row_is_a_warning_and_the_settings_still_move(
    bot, db, monkeypatch, caplog
):
    async def broken(*_args, **_kwargs):
        raise RuntimeError("log down")

    monkeypatch.setattr(shadow_one_meaning, "log_action", broken)
    await live_mirror(db)

    await shadow_one_meaning.apply(bot)

    assert "a migration row was not written" in caplog.text
    assert "youtube_live_mode" not in await keys_of(db, GUILD)


async def test_the_stale_rehearsal_note_row_alone_is_dropped_once(bot, db):
    await stored(db, GUILD, "rehearsal_note", "")

    [found] = await shadow_one_meaning.apply(bot)

    assert found["drop"] == {"rehearsal_note": ""} and found["write"] == {}
    assert "rehearsal_note" not in await keys_of(db, GUILD)
    assert await shadow_one_meaning.apply(bot) == []
