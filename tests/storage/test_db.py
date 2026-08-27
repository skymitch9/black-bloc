import sqlite3

import pytest

from black_bloc.storage.db import SCHEMA_VERSION, Database


async def test_connect_bootstraps_schema(tmp_path):
    db = Database(tmp_path / "nested" / "t.sqlite3")
    await db.connect()
    try:
        cur = await db.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        row = await cur.fetchone()
        assert row is not None and row["value"] == str(SCHEMA_VERSION)
        assert SCHEMA_VERSION == 6
        cur = await db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {r["name"] for r in await cur.fetchall()}
        assert {"settings", "action_log", "role_menus", "role_menu_options"} <= tables
        assert {"golive_links", "golive_optout", "golive_sessions"} <= tables
        assert {"tempvoice_channels", "tempvoice_prefs", "honeypot_hits"} <= tables
        assert "birthdays" in tables
        cur = await db.conn.execute("PRAGMA table_info(birthdays)")
        columns = {r["name"] for r in await cur.fetchall()}
        assert {"user_id", "month", "day", "year", "opted_in", "source"} <= columns
        assert {"set_at", "last_announced_on", "role_added"} <= columns
    finally:
        await db.close()


async def open_session(db, user_id, source="presence"):
    await db.conn.execute(
        "INSERT INTO golive_sessions(guild_id, user_id, source, started_at, mode) "
        "VALUES (1, ?, ?, '2026-08-26T00:00:00+00:00', 'on')",
        (user_id, source),
    )
    await db.conn.commit()


async def test_the_live_role_column_and_the_open_session_index_are_added(tmp_path):
    db = Database(tmp_path / "t.sqlite3")
    await db.connect()
    try:
        cur = await db.conn.execute("PRAGMA table_info(golive_sessions)")
        assert "live_role_added" in {row["name"] for row in await cur.fetchall()}
        cur = await db.conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        assert "golive_open_session" in {row["name"] for row in await cur.fetchall()}
    finally:
        await db.close()


async def test_the_migration_step_is_idempotent(tmp_path):
    path = tmp_path / "t.sqlite3"
    for _ in range(3):
        db = Database(path)
        await db.connect()
        await db.close()
    db = Database(path)
    await db.connect()
    try:
        cur = await db.conn.execute("PRAGMA table_info(golive_sessions)")
        names = [row["name"] for row in await cur.fetchall()]
        assert names.count("live_role_added") == 1
    finally:
        await db.close()


async def test_only_one_session_per_member_may_be_open(tmp_path):
    db = Database(tmp_path / "t.sqlite3")
    await db.connect()
    try:
        await open_session(db, 5)
        with pytest.raises(sqlite3.IntegrityError):
            await open_session(db, 5, "twitch")
    finally:
        await db.close()


async def test_duplicate_open_sessions_are_closed_before_the_index_is_built(tmp_path):
    path = tmp_path / "t.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute("DROP INDEX golive_open_session")
    await open_session(db, 5)
    await open_session(db, 5, "twitch")
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute(
            "SELECT COUNT(*) AS n FROM golive_sessions WHERE ended_at IS NULL"
        )
        assert (await cur.fetchone())["n"] == 1
    finally:
        await again.close()
