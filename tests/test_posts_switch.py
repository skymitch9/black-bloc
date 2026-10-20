import json
from types import SimpleNamespace

import pytest

from black_bloc import posts_switch
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore

GUILD = 1073710702776299640
OTHER_GUILD = 99
SPEED_AND_PBS = 1076003845232148580
POST_TEST = 1550284332365783091
WELCOME = 1285369365071527997
OLD_DOOR_COPY = 1560105628234420427
LEADERBOARD_COPY = 1560200000000000001
AT = "2026-10-10T12:00:00+00:00"
LIVE_ROWS = {
    "posts_mode": "on",
    "question_mode": "on",
    "sticky_shadow_channel_id": POST_TEST,
    "question_shadow_channel_id": POST_TEST,
    "frontdoor_shadow_channel_id": POST_TEST,
    "frontdoor_shadow_message_id": str(OLD_DOOR_COPY),
    "posts_shadow_channel_id": POST_TEST,
    "points_mode": "shadow",
}


async def stored(db, guild_id, key, value):
    await db.conn.execute(
        "INSERT OR REPLACE INTO settings(guild_id, key, value, updated_by, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (guild_id, key, json.dumps(value), None, AT),
    )
    await db.conn.commit()


async def sticky(db, guild_id, channel_id, **fields):
    row = {
        "text": "",
        "paused": 0,
        "trouble": None,
        "message_id": None,
        "posted_channel_id": None,
        "post_id": None,
    } | fields
    await db.conn.execute(
        "INSERT INTO sticky_messages(guild_id, channel_id, text, paused, trouble, message_id, "
        "posted_channel_id, post_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            guild_id,
            channel_id,
            row["text"],
            row["paused"],
            row["trouble"],
            row["message_id"],
            row["posted_channel_id"],
            row["post_id"],
            AT,
            AT,
        ),
    )
    await db.conn.commit()


async def live_mirror(db):
    """The rows the switch audit read live on 2026-10-19: one leaderboard sticky rehearsing."""
    for key, value in LIVE_ROWS.items():
        await stored(db, GUILD, key, value)
    await sticky(
        db,
        GUILD,
        SPEED_AND_PBS,
        post_id=2,
        message_id=LEADERBOARD_COPY,
        posted_channel_id=POST_TEST,
    )


async def keys_of(db, guild_id):
    cur = await db.conn.execute("SELECT key FROM settings WHERE guild_id = ?", (guild_id,))
    return {row["key"] for row in await cur.fetchall()}


async def value_of(db, guild_id, key):
    cur = await db.conn.execute(
        "SELECT value FROM settings WHERE guild_id = ? AND key = ?", (guild_id, key)
    )
    row = await cur.fetchone()
    return json.loads(row["value"]) if row is not None else None


async def sticky_row(db, guild_id, channel_id):
    cur = await db.conn.execute(
        "SELECT * FROM sticky_messages WHERE guild_id = ? AND channel_id = ?",
        (guild_id, channel_id),
    )
    return await cur.fetchone()


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


async def test_the_dry_run_against_the_live_rows_pauses_one_sticky_and_drops_five_keys(db):
    await live_mirror(db)

    [found] = await posts_switch.dry_run(db)

    assert found["guild_id"] == GUILD
    assert found["pause"] == [
        {
            "channel_id": SPEED_AND_PBS,
            "post_id": 2,
            "copy": {"channel_id": POST_TEST, "message_id": LEADERBOARD_COPY},
            "before": "rehearsing",
            "after": "paused",
        }
    ]
    assert found["drop"] == {
        "frontdoor_shadow_channel_id": POST_TEST,
        "frontdoor_shadow_message_id": str(OLD_DOOR_COPY),
        "question_mode": "on",
        "question_shadow_channel_id": POST_TEST,
        "sticky_shadow_channel_id": POST_TEST,
    }
    assert found["modes"] == {}
    assert (await sticky_row(db, GUILD, SPEED_AND_PBS))["paused"] == 0, "a dry run writes nothing"
    assert "question_mode" in await keys_of(db, GUILD)


async def test_applying_pauses_keeps_the_copy_drops_the_keys_and_logs_each_act(bot, db):
    await live_mirror(db)

    done = await posts_switch.apply(bot)

    assert [one["guild_id"] for one in done] == [GUILD]
    row = await sticky_row(db, GUILD, SPEED_AND_PBS)
    assert row["paused"] == 1 and row["trouble"] is None
    assert (row["message_id"], row["posted_channel_id"]) == (LEADERBOARD_COPY, POST_TEST)
    assert await keys_of(db, GUILD) == {"posts_mode", "posts_shadow_channel_id", "points_mode"}
    assert await value_of(db, GUILD, "posts_mode") == "on"
    logged = await actions(db)
    assert [kind for _, kind, _ in logged] == ["sticky.paused_by_migration", "settings.migrated"]
    paused = logged[0][2]
    assert (paused["before"], paused["after"], paused["channel_id"]) == (
        "rehearsing",
        "paused",
        SPEED_AND_PBS,
    )
    migrated = logged[1][2]
    assert migrated["removed"] == sorted(done[0]["drop"]) and len(migrated["removed"]) == 5
    assert migrated["build"] == "posts-one-switch"


async def test_a_second_boot_finds_nothing_and_writes_no_row(bot, db):
    await live_mirror(db)

    first = await posts_switch.apply(bot)
    rows_after_first = await actions(db)
    second = await posts_switch.apply(bot)

    assert first and second == []
    assert await actions(db) == rows_after_first
    assert await posts_switch.dry_run(db) == []


async def test_shadow_values_map_to_on_for_posts_and_off_for_the_door_and_polls(bot, db):
    await stored(db, GUILD, "posts_mode", "shadow")
    await stored(db, GUILD, "frontdoor_mode", "shadow")
    await stored(db, GUILD, "poll_mode", "shadow")
    await stored(db, GUILD, "sticky_mode", "shadow")

    [found] = await posts_switch.apply(bot)

    assert found["modes"] == {
        "posts_mode": {"before": "shadow", "after": "on"},
        "frontdoor_mode": {"before": "shadow", "after": "off"},
        "poll_mode": {"before": "shadow", "after": "off"},
    }
    for key, wanted in (("posts_mode", "on"), ("frontdoor_mode", "off"), ("poll_mode", "off")):
        assert await value_of(db, GUILD, key) == wanted
    await bot.store.load()
    assert bot.store.get(GUILD, "posts_mode") == "on"
    assert bot.store.get(GUILD, "frontdoor_mode") == "off"
    assert "sticky_mode" not in await keys_of(db, GUILD)


async def test_only_running_rehearsals_pause_and_only_in_their_own_guild(bot, db):
    await sticky(db, GUILD, 1, message_id=11, posted_channel_id=POST_TEST, paused=1)
    await sticky(db, GUILD, 2, message_id=12, posted_channel_id=POST_TEST, trouble="held")
    await sticky(db, GUILD, 3, message_id=13, posted_channel_id=3)
    await sticky(db, GUILD, 4)
    await sticky(db, OTHER_GUILD, 5, message_id=15, posted_channel_id=POST_TEST)

    done = await posts_switch.apply(bot)

    assert [(one["guild_id"], [row["channel_id"] for row in one["pause"]]) for one in done] == [
        (OTHER_GUILD, [5])
    ]
    for channel_id, paused in ((1, 1), (2, 0), (3, 0), (4, 0)):
        assert (await sticky_row(db, GUILD, channel_id))["paused"] == paused
    assert (await sticky_row(db, OTHER_GUILD, 5))["paused"] == 1


async def test_a_clean_database_is_left_alone(bot, db):
    assert await posts_switch.apply(bot) == []
    assert await actions(db) == []
