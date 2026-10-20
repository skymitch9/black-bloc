import itertools
import json
from types import SimpleNamespace

from black_bloc import one_optout, optouts
from black_bloc.chat_memory import remembers
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore

GUILD = 1073710702776299640
OTHER_GUILD = 99
AT = "2026-10-20T09:00:00+00:00"
LIVE_SETTINGS = {
    "chat_memory_consent": "optout",
    "golive_mode": "on",
    "marathon_optout_role_ids": [1335035657730523219],
}
KINDS = ("announce", "birthday", "chat_memory", "pbs", "streamer_list")


async def stored(db, guild_id, key, value):
    await db.conn.execute(
        "INSERT OR REPLACE INTO settings(guild_id, key, value, updated_by, updated_at) "
        "VALUES (?, ?, ?, NULL, ?)",
        (guild_id, key, json.dumps(value), AT),
    )
    await db.conn.commit()


async def live_mirror(db):
    """What /api/members/optouts, /api/golive/optouts, /api/birthdays, /api/pings/list and
    /api/settings answered live 2026-10-20 03:10 Phoenix: six marathon role holders, and not
    one row in any per-person store (0 go-live, 0 chat memory, 0 of 42 birthdays, 0 PBs, 0 of
    48 streamers hidden by hand)."""
    for key, value in LIVE_SETTINGS.items():
        await stored(db, GUILD, key, value)


async def legacy(db, user_id, *, golive=False, birthday=False, chat=False, pbs=False, hidden=False):
    if golive:
        await db.conn.execute("INSERT INTO golive_optout(user_id, at) VALUES (?, ?)", (user_id, AT))
    await db.conn.execute(
        "INSERT INTO birthdays(user_id, guild_id, month, day, opted_in, source, set_at) "
        "VALUES (?, ?, 1, 2, ?, 'self', ?)",
        (user_id, GUILD, 0 if birthday else 1, AT),
    )
    if chat:
        await db.conn.execute(
            "INSERT INTO chat_memory_optout(user_id, guild_id, at) VALUES (?, ?, ?)",
            (user_id, GUILD, AT),
        )
    await db.conn.execute(
        "INSERT INTO pb_matches(guild_id, user_id, state, state_by, set_by, updated_at, "
        "opted_out_at) VALUES (?, ?, ?, 'member', ?, ?, ?)",
        (GUILD, user_id, "opted_out" if pbs else "none", user_id, AT, AT if pbs else None),
    )
    await db.conn.execute(
        "INSERT INTO streamers(guild_id, user_id, first_live_at, last_live_at, listed, "
        "hidden_by, hidden_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (GUILD, user_id, AT, AT, 0 if hidden else 1, user_id if hidden else None, AT),
    )
    await db.conn.commit()


async def every_combination(db):
    """One person per combination of the five old stores: 32 people."""
    found = {}
    for at, picked in enumerate(itertools.product((False, True), repeat=5)):
        user_id = 500 + at
        flags = dict(zip(("golive", "birthday", "chat", "pbs", "hidden"), picked, strict=True))
        await legacy(db, user_id, **flags)
        found[user_id] = flags
    return found


async def actions(db):
    cur = await db.conn.execute("SELECT guild_id, kind, details FROM action_log ORDER BY id")
    return [
        (row["guild_id"], row["kind"], json.loads(row["details"])) for row in await cur.fetchall()
    ]


def bot_of(db, store, dev_guild_id=None):
    return SimpleNamespace(
        db=db,
        store=store,
        settings=SimpleNamespace(dev_guild_id=dev_guild_id),
        get_channel=lambda _id: None,
    )


async def a_store(db):
    store = SettingsStore(db, load_settings(_env_file=None))
    await store.load()
    return store


async def test_the_dry_run_against_the_live_rows_finds_nothing_to_copy(db):
    await live_mirror(db)

    assert await one_optout.dry_run(db) == []


async def test_applying_against_the_live_rows_writes_nothing_and_logs_nothing(db):
    await live_mirror(db)
    bot = bot_of(db, await a_store(db))

    assert await one_optout.apply(bot) == []
    assert await actions(db) == []
    assert optouts.silenced(db, GUILD) == frozenset()


async def test_the_dry_run_counts_each_kind_and_writes_nothing(db):
    await live_mirror(db)
    await every_combination(db)

    [found] = await one_optout.dry_run(db)

    assert found["guild_id"] == GUILD
    assert found["counts"] == {kind: 16 for kind in KINDS}
    assert found["notes"] == []
    assert await optouts.rows(db, GUILD) == []


async def test_applying_twice_copies_once_and_logs_one_row_with_the_counts(db):
    await live_mirror(db)
    await every_combination(db)
    bot = bot_of(db, await a_store(db))

    first = await one_optout.apply(bot)
    rows_after_first = await actions(db)
    second = await one_optout.apply(bot)

    assert [one["guild_id"] for one in first] == [GUILD] and second == []
    assert await actions(db) == rows_after_first
    [(guild_id, kind, details)] = rows_after_first
    assert (guild_id, kind) == (GUILD, "optouts.migrated")
    assert details["build"] == "one-optout"
    assert details["counts"] == {kind: 16 for kind in KINDS}
    for kind in KINDS:
        assert await optouts.count(db, GUILD, kind) == 16
    (row,) = [
        one for one in await optouts.rows(db, GUILD, ("streamer_list",)) if one["user_id"] == 501
    ]
    assert (row["by"], row["reason"]) == (501, "migrated")
    assert len(optouts.silenced(db, GUILD)) == 16


async def test_the_old_stores_are_left_as_they_were_for_one_release(db):
    await live_mirror(db)
    await every_combination(db)
    before = {}
    for table in ("golive_optout", "birthdays", "chat_memory_optout", "pb_matches", "streamers"):
        cur = await db.conn.execute(f"SELECT * FROM {table} ORDER BY 1, 2")
        before[table] = [tuple(row) for row in await cur.fetchall()]

    await one_optout.apply(bot_of(db, await a_store(db)))

    for table, rows in before.items():
        cur = await db.conn.execute(f"SELECT * FROM {table} ORDER BY 1, 2")
        assert [tuple(row) for row in await cur.fetchall()] == rows, table


async def test_nobody_silent_before_the_migration_is_announced_after_it(db):
    """Every combination of the five old stores, old gate against new gate: a person each old
    gate kept quiet is still quiet through the one table, for every kind."""
    await live_mirror(db)
    people = await every_combination(db)

    await one_optout.apply(bot_of(db, await a_store(db)))

    for user_id, flags in people.items():
        for flag, kind in (
            ("golive", "announce"),
            ("birthday", "birthday"),
            ("pbs", "pbs"),
            ("hidden", "streamer_list"),
        ):
            assert await optouts.is_out(db, GUILD, user_id, kind) is flags[flag], (user_id, kind)
        assert await remembers(db, user_id, GUILD, consent="optout") is (not flags["chat"])
        assert (user_id in optouts.silenced(db, GUILD)) is flags["golive"]


async def test_a_chat_memory_row_under_an_opt_in_server_is_copied_as_an_opt_in(db):
    await stored(db, GUILD, "chat_memory_consent", "optin")
    await legacy(db, 41, chat=True)
    await legacy(db, 42)

    await one_optout.apply(bot_of(db, await a_store(db)))

    assert await optouts.out_of(db, GUILD, "chat_memory_in") == {41}
    assert await optouts.out_of(db, GUILD, "chat_memory") == set()
    assert await remembers(db, 41, GUILD, consent="optin") is True
    assert await remembers(db, 42, GUILD, consent="optin") is False


async def test_a_streamer_dropped_as_stale_is_not_a_person_who_opted_out(db):
    await live_mirror(db)
    await legacy(db, 43)
    await db.conn.execute("UPDATE streamers SET listed = 0 WHERE user_id = 43")
    await db.conn.commit()

    assert await one_optout.dry_run(db) == []


async def test_the_go_live_table_has_no_guild_so_the_configured_guild_is_used_first(db):
    await stored(db, OTHER_GUILD, "golive_mode", "on")
    await live_mirror(db)
    await db.conn.execute("INSERT INTO golive_optout(user_id, at) VALUES (21, ?)", (AT,))
    await db.conn.commit()

    [found] = await one_optout.apply(bot_of(db, await a_store(db), dev_guild_id=GUILD))

    assert found["counts"] == {"announce": 1}
    assert await optouts.out_of(db, GUILD, "announce") == {21}


async def test_with_two_guilds_and_none_configured_the_go_live_rows_wait_and_say_why(db, caplog):
    await stored(db, OTHER_GUILD, "golive_mode", "on")
    await live_mirror(db)
    await db.conn.execute("INSERT INTO golive_optout(user_id, at) VALUES (21, ?)", (AT,))
    await db.conn.commit()

    assert await one_optout.apply(bot_of(db, await a_store(db))) == []
    assert "golive_optout has no guild column" in caplog.text
    assert await optouts.rows(db, GUILD) == []


async def test_a_lost_log_row_is_a_warning_and_the_rows_still_move(db, monkeypatch, caplog):
    async def broken(*_args, **_kwargs):
        raise RuntimeError("log down")

    monkeypatch.setattr(one_optout, "log_action", broken)
    await live_mirror(db)
    await legacy(db, 44, birthday=True)

    await one_optout.apply(bot_of(db, await a_store(db)))

    assert "a migration row was not written" in caplog.text
    assert await optouts.is_out(db, GUILD, 44, "birthday") is True
