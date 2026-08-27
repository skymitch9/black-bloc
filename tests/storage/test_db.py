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
        assert SCHEMA_VERSION == 14
        cur = await db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {r["name"] for r in await cur.fetchall()}
        assert {"settings", "action_log", "role_menus", "role_menu_options"} <= tables
        assert {"role_requests", "role_grants"} <= tables
        assert {"golive_links", "golive_optout", "golive_sessions"} <= tables
        assert {"tempvoice_channels", "tempvoice_prefs", "honeypot_hits"} <= tables
        assert {"user_timezones", "events", "mod_cases"} <= tables
        cur = await db.conn.execute("PRAGMA table_info(mod_cases)")
        assert {"kind", "moderator_id", "duration_s", "mode", "applied", "log_message_id"} <= {
            row["name"] for row in await cur.fetchall()
        }
        assert "birthdays" in tables
        cur = await db.conn.execute("PRAGMA table_info(birthdays)")
        columns = {r["name"] for r in await cur.fetchall()}
        assert {"user_id", "month", "day", "year", "opted_in", "source"} <= columns
        assert {"set_at", "last_announced_on", "role_added"} <= columns
        assert {
            "modmail_tickets",
            "modmail_messages",
            "modmail_blocks",
            "modmail_snippets",
        } <= tables
        assert {"polls", "poll_options", "poll_votes", "poll_results"} <= tables
    finally:
        await db.close()


async def test_a_poll_row_carries_every_column_phase_10_stores(tmp_path):
    db = Database(tmp_path / "p.sqlite3")
    await db.connect()
    try:
        cur = await db.conn.execute("PRAGMA table_info(polls)")
        columns = {row["name"] for row in await cur.fetchall()}
        assert {"guild_id", "creator_id", "question", "kind", "surface", "multi"} <= columns
        assert {"anonymous", "results", "hours", "ping_role_id", "status"} <= columns
        assert {"channel_id", "message_id", "thread_id", "closes_at", "reminded_at"} <= columns
        assert {"closed_at", "archived_at", "total_votes"} <= columns
        assert {"recurrence", "recur_at", "recur_tz", "recur_next_at", "schedule_id"} <= columns
        assert {"review_channel_id", "review_message_id", "decided_by", "decided_at"} <= columns
        assert {"deny_reason", "created_at"} <= columns
    finally:
        await db.close()


async def add_poll_option(db, poll_id, position, label="Yes"):
    await db.conn.execute(
        "INSERT INTO poll_options(poll_id, position, label) VALUES (?, ?, ?)",
        (poll_id, position, label),
    )
    await db.conn.commit()


async def test_two_options_cannot_share_one_slot_on_a_poll(tmp_path):
    db = Database(tmp_path / "p.sqlite3")
    await db.connect()
    try:
        await add_poll_option(db, 1, 0)
        await add_poll_option(db, 2, 0)
        with pytest.raises(sqlite3.IntegrityError):
            await add_poll_option(db, 1, 0, label="No")
    finally:
        await db.close()


async def add_poll_vote(db, poll_id, option_id, user_id):
    await db.conn.execute(
        "INSERT INTO poll_votes(poll_id, option_id, user_id, at) VALUES (?, ?, ?, ?)",
        (poll_id, option_id, user_id, "2026-08-27T00:00:00+00:00"),
    )
    await db.conn.commit()


async def test_one_member_votes_once_per_option(tmp_path):
    db = Database(tmp_path / "p.sqlite3")
    await db.connect()
    try:
        await add_poll_vote(db, 1, 1, 900)
        await add_poll_vote(db, 1, 2, 900)
        await add_poll_vote(db, 2, 1, 900)
        with pytest.raises(sqlite3.IntegrityError):
            await add_poll_vote(db, 1, 1, 900)
    finally:
        await db.close()


async def test_a_poll_keeps_one_result_row_forever(tmp_path):
    db = Database(tmp_path / "p.sqlite3")
    await db.connect()
    try:
        await db.conn.execute(
            "INSERT INTO poll_results(poll_id, closed_at, total_votes, counts) "
            "VALUES (1, '2026-08-27T00:00:00+00:00', 3, '[]')"
        )
        await db.conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            await db.conn.execute(
                "INSERT INTO poll_results(poll_id, closed_at, total_votes, counts) "
                "VALUES (1, '2026-08-28T00:00:00+00:00', 4, '[]')"
            )
    finally:
        await db.close()


async def open_ticket(db, user_id, channel_id):
    await db.conn.execute(
        "INSERT INTO modmail_tickets(guild_id, user_id, mode, channel_id, status, opened_at) "
        "VALUES (1, ?, 'channel', ?, 'open', '2026-08-26T00:00:00+00:00')",
        (user_id, channel_id),
    )
    await db.conn.commit()


async def test_only_one_modmail_ticket_per_member_may_be_open(tmp_path):
    db = Database(tmp_path / "t.sqlite3")
    await db.connect()
    try:
        await open_ticket(db, 900, 10)
        with pytest.raises(sqlite3.IntegrityError):
            await open_ticket(db, 900, 11)
        await db.conn.execute("UPDATE modmail_tickets SET status = 'closed'")
        await db.conn.commit()
        await open_ticket(db, 900, 12)
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
        assert names.count("platform") == 1
    finally:
        await db.close()


async def test_a_session_row_gains_a_platform_column_on_an_older_file(tmp_path):
    path = tmp_path / "old.sqlite3"
    db = Database(path)
    await db.connect()
    await open_session(db, 5)
    await db.conn.execute("ALTER TABLE golive_sessions DROP COLUMN platform")
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("PRAGMA table_info(golive_sessions)")
        assert "platform" in {row["name"] for row in await cur.fetchall()}
        cur = await again.conn.execute("SELECT platform FROM golive_sessions WHERE user_id = 5")
        assert (await cur.fetchone())["platform"] is None
    finally:
        await again.close()


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


async def open_role_request(db, user_id, menu_id=3, role_id=10):
    await db.conn.execute(
        "INSERT INTO role_requests(guild_id, menu_id, user_id, role_id, requested_at, status) "
        "VALUES (1, ?, ?, ?, '2026-08-27T00:00:00+00:00', 'pending')",
        (menu_id, user_id, role_id),
    )
    await db.conn.commit()


async def test_only_one_role_request_per_member_and_role_may_be_open(tmp_path):
    db = Database(tmp_path / "t.sqlite3")
    await db.connect()
    try:
        await open_role_request(db, 900)
        with pytest.raises(sqlite3.IntegrityError):
            await open_role_request(db, 900)
        await open_role_request(db, 900, role_id=11)
        await db.conn.execute("UPDATE role_requests SET status = 'denied' WHERE role_id = 10")
        await db.conn.commit()
        await open_role_request(db, 900)
    finally:
        await db.close()


async def test_a_role_menu_gains_the_approval_columns_on_an_older_file(tmp_path):
    path = tmp_path / "old.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute(
        "INSERT INTO role_menus(guild_id, name, title, mode) "
        "VALUES (1, 'runner', 'Runner', 'staff')"
    )
    for column in ("approval", "expires_days", "retry_days"):
        await db.conn.execute(f"ALTER TABLE role_menus DROP COLUMN {column}")
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("PRAGMA table_info(role_menus)")
        names = [row["name"] for row in await cur.fetchall()]
        assert {"approval", "expires_days", "retry_days"} <= set(names)
        assert names.count("approval") == 1
        cur = await again.conn.execute("SELECT * FROM role_menus WHERE name = 'runner'")
        row = await cur.fetchone()
        assert (row["approval"], row["expires_days"], row["retry_days"]) == (0, None, 7)
    finally:
        await again.close()


async def test_an_events_row_gains_a_card_channel_column_on_an_older_file(tmp_path):
    path = tmp_path / "old.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute("ALTER TABLE events DROP COLUMN card_channel_id")
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("PRAGMA table_info(events)")
        names = {row["name"] for row in await cur.fetchall()}
        assert "card_channel_id" in names
    finally:
        await again.close()
