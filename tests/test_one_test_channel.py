import json
from types import SimpleNamespace

import pytest

from black_bloc import one_test_channel, settings_store
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore

GUILD = 1073710702776299640
OTHER_GUILD = 99
LOG = 1542316174472380517
POST_TEST = 1550284332365783091
ELSEWHERE = 1076003845232148580
AT = "2026-10-10T12:00:00+00:00"
LIVE_ROWS = {
    "log_channel_id": LOG,
    "shadow_channel_id": LOG,
    "posts_shadow_channel_id": POST_TEST,
    "points_shadow_channel_id": POST_TEST,
    "structure_backup_mode": "shadow",
    "brackets_mode": "shadow",
}


async def stored(db, guild_id, key, value):
    await db.conn.execute(
        "INSERT OR REPLACE INTO settings(guild_id, key, value, updated_by, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (guild_id, key, json.dumps(value), None, AT),
    )
    await db.conn.commit()


async def live_mirror(db):
    """The rows read live through /api/settings 2026-10-20: two overrides, both #post-test."""
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


def test_every_retired_key_is_gone_from_the_registry_and_the_structure_one_stays():
    for key in one_test_channel.RETIRED_KEYS:
        assert key not in settings_store.KEY_TYPES
        assert key not in settings_store.KEY_HELP
    assert settings_store.KEY_TYPES["structure_backup_shadow_channel_id"] == "channel"
    assert "structure_backup_shadow_channel_id" not in one_test_channel.RETIRED_KEYS


async def test_the_dry_run_against_the_live_rows_copies_post_test_and_drops_two_keys(db):
    await live_mirror(db)

    [found] = await one_test_channel.dry_run(db)

    assert found == {
        "guild_id": GUILD,
        "copy": {"key": "shadow_channel_id", "before": LOG, "after": POST_TEST},
        "drop": {"points_shadow_channel_id": POST_TEST, "posts_shadow_channel_id": POST_TEST},
        "skipped": None,
    }
    assert await value_of(db, GUILD, "shadow_channel_id") == LOG, "a dry run writes nothing"


async def test_applying_twice_copies_once_drops_once_and_logs_one_row(bot, db):
    await live_mirror(db)

    first = await one_test_channel.apply(bot)
    rows_after_first = await actions(db)
    second = await one_test_channel.apply(bot)

    assert [one["guild_id"] for one in first] == [GUILD] and second == []
    assert await actions(db) == rows_after_first
    assert await value_of(db, GUILD, "shadow_channel_id") == POST_TEST
    assert not set(one_test_channel.RETIRED_KEYS) & await keys_of(db, GUILD)
    [(guild_id, kind, details)] = rows_after_first
    assert (guild_id, kind) == (GUILD, "settings.migrated")
    assert details["removed"] == ["points_shadow_channel_id", "posts_shadow_channel_id"]
    assert details["copied"] == {"key": "shadow_channel_id", "before": LOG, "after": POST_TEST}
    assert details["build"] == "one-test-channel"
    await bot.store.load()
    assert bot.store.get(GUILD, "shadow_channel_id") == POST_TEST


async def test_a_test_channel_already_there_is_kept_and_only_the_rows_go(bot, db):
    await stored(db, GUILD, "shadow_channel_id", POST_TEST)
    await stored(db, GUILD, "golive_shadow_channel_id", POST_TEST)
    await stored(db, GUILD, "marathon_shadow_channel_id", None)

    [found] = await one_test_channel.apply(bot)

    assert found["copy"] is None
    assert sorted(found["drop"]) == ["golive_shadow_channel_id", "marathon_shadow_channel_id"]
    assert await keys_of(db, GUILD) == {"shadow_channel_id"}


async def test_disagreeing_overrides_copy_nothing_delete_nothing_and_say_so(bot, db):
    await stored(db, GUILD, "shadow_channel_id", LOG)
    await stored(db, GUILD, "posts_shadow_channel_id", POST_TEST)
    await stored(db, GUILD, "brackets_shadow_channel_id", ELSEWHERE)

    [found] = await one_test_channel.apply(bot)

    assert found["copy"] is None and found["drop"] == {}
    assert found["skipped"] == {
        "reason": "the set overrides disagree",
        "test_channel": LOG,
        "overrides": {
            "brackets_shadow_channel_id": ELSEWHERE,
            "posts_shadow_channel_id": POST_TEST,
        },
    }
    assert await value_of(db, GUILD, "shadow_channel_id") == LOG
    assert {"posts_shadow_channel_id", "brackets_shadow_channel_id"} <= await keys_of(db, GUILD)
    [(_, kind, details)] = await actions(db)
    assert kind == "settings.migration_skipped"
    assert details["overrides"] == found["skipped"]["overrides"]
    await one_test_channel.apply(bot)
    assert [kind for _, kind, _ in await actions(db)] == ["settings.migration_skipped"] * 2, (
        "every boot says so again until a Lead resolves it"
    )


async def test_only_guilds_with_retired_rows_are_touched(bot, db):
    await stored(db, OTHER_GUILD, "shadow_channel_id", LOG)
    await stored(db, GUILD, "birthday_shadow_channel_id", POST_TEST)

    done = await one_test_channel.apply(bot)

    assert [one["guild_id"] for one in done] == [GUILD]
    assert await value_of(db, OTHER_GUILD, "shadow_channel_id") == LOG
    assert await value_of(db, GUILD, "shadow_channel_id") == POST_TEST


async def test_a_clean_database_is_left_alone(bot, db):
    assert await one_test_channel.apply(bot) == []
    assert await actions(db) == []
