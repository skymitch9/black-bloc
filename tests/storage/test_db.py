import sqlite3

import aiosqlite
import pytest

from black_bloc.storage.db import SCHEMA_VERSION, Database


async def test_connect_bootstraps_schema(tmp_path):
    db = Database(tmp_path / "nested" / "t.sqlite3")
    await db.connect()
    try:
        cur = await db.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        row = await cur.fetchone()
        assert row is not None and row["value"] == str(SCHEMA_VERSION)
        assert SCHEMA_VERSION == 65
        cur = await db.conn.execute("PRAGMA table_info(spotlight_channels)")
        assert {
            "spotlight",
            "youtube_channel_id",
            "youtube_handle",
        } <= {r["name"] for r in await cur.fetchall()}
        cur = await db.conn.execute("PRAGMA table_info(raid_trains)")
        assert "event_id" in {r["name"] for r in await cur.fetchall()}
        cur = await db.conn.execute("PRAGMA table_info(requests)")
        assert {
            "built",
            "how_to_test",
            "ready_by",
            "sent_back_reason",
            "check_asked_by",
            "check_asked_at",
            "thread_id",
            "source",
        } <= {r["name"] for r in await cur.fetchall()}
        cur = await db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {r["name"] for r in await cur.fetchall()}
        assert {"settings", "action_log", "role_menus", "role_menu_options"} <= tables
        assert {"role_requests", "role_grants"} <= tables
        assert {"application_forms", "application_questions", "applications"} <= tables
        assert {"golive_links", "golive_optout", "golive_sessions"} <= tables
        cur = await db.conn.execute("PRAGMA table_info(golive_sessions)")
        assert {
            "also_source",
            "also_url",
            "also_platform",
            "also_started_at",
        } <= {r["name"] for r in await cur.fetchall()}
        assert "golive_fan_roles" in tables
        cur = await db.conn.execute("PRAGMA table_info(golive_fan_roles)")
        columns = {r["name"] for r in await cur.fetchall()}
        assert {
            "guild_id",
            "user_id",
            "role_id",
            "created_at",
            "created_by",
            "unworn_since",
            "spotlight_id",
        } == columns
        assert "streamers" in tables
        assert {"youtube_links", "youtube_videos"} <= tables
        cur = await db.conn.execute("PRAGMA table_info(youtube_links)")
        assert {
            "user_id",
            "channel_id",
            "handle",
            "title",
            "linked_at",
            "etag",
            "seeded",
        } == {r["name"] for r in await cur.fetchall()}
        cur = await db.conn.execute("PRAGMA table_info(youtube_videos)")
        assert {
            "video_id",
            "user_id",
            "channel_id",
            "title",
            "published_at",
            "seen_at",
            "kind",
            "announced_at",
            "announced_message_id",
            "mode",
        } == {r["name"] for r in await cur.fetchall()}
        assert {"tempvoice_channels", "tempvoice_prefs", "honeypot_hits"} <= tables
        assert {"user_timezones", "events", "mod_cases"} <= tables
        cur = await db.conn.execute("PRAGMA table_info(mod_cases)")
        columns = {row["name"] for row in await cur.fetchall()}
        assert {"kind", "moderator_id", "duration_s", "mode", "applied"} <= columns
        assert "log_message_id" in columns
        assert {"note", "note_by", "note_at", "voided_at", "voided_by", "void_reason"} <= columns
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
        assert "poll_drafts" in tables
        assert {"chat_intents", "chat_lines"} <= tables
        assert {"knowledge_sections", "personality_tropes"} <= tables
        assert {"chat_window", "llm_ledger"} <= tables
        assert {"requests", "request_comments"} <= tables
        assert "sessions" in tables
        cur = await db.conn.execute("PRAGMA table_info(sessions)")
        columns = {r["name"] for r in await cur.fetchall()}
        assert {"id", "user_id", "created_at", "expires_at", "revoked_at"} == columns
    finally:
        await db.close()


async def test_a_request_and_its_comments_carry_what_the_requests_page_shows(tmp_path):
    db = Database(tmp_path / "r.sqlite3")
    await db.connect()
    try:
        cur = await db.conn.execute("PRAGMA table_info(requests)")
        columns = {row["name"] for row in await cur.fetchall()}
        assert {"id", "guild_id", "user_id", "what", "why", "due_on", "status"} <= columns
        assert {"priority", "assignee_id", "notes", "created_at", "message_id"} <= columns
        assert {"decided_by", "decided_at", "decline_reason", "done_at"} <= columns
        cur = await db.conn.execute("PRAGMA table_info(request_comments)")
        columns = {row["name"] for row in await cur.fetchall()}
        assert {"id", "request_id", "author_id", "text", "at"} <= columns
        cur = await db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='requests'"
        )
        assert "requests_by_status" in {row["name"] for row in await cur.fetchall()}
    finally:
        await db.close()


async def test_a_requests_comments_go_when_the_request_does(tmp_path):
    db = Database(tmp_path / "r.sqlite3")
    await db.connect()
    try:
        await db.conn.execute(
            "INSERT INTO requests(id, guild_id, user_id, what, why, status, created_at) "
            "VALUES (1, 7, 9, 'a bot', 'because', 'pending', '2026-08-27T00:00:00+00:00')"
        )
        await db.conn.execute(
            "INSERT INTO request_comments(request_id, author_id, text, at) "
            "VALUES (1, 9, 'any news?', '2026-08-27T00:00:00+00:00')"
        )
        await db.conn.commit()
        await db.conn.execute("DELETE FROM requests WHERE id = 1")
        await db.conn.commit()
        cur = await db.conn.execute("SELECT COUNT(*) AS found FROM request_comments")

        assert (await cur.fetchone())["found"] == 0
    finally:
        await db.close()


async def test_a_chat_intent_and_its_lines_carry_what_the_chat_page_edits(tmp_path):
    db = Database(tmp_path / "c.sqlite3")
    await db.connect()
    try:
        cur = await db.conn.execute("PRAGMA table_info(chat_intents)")
        columns = {row["name"] for row in await cur.fetchall()}
        assert {"id", "guild_id", "name", "triggers", "kind"} <= columns
        assert {"enabled", "sort", "created_by", "updated_at"} <= columns
        cur = await db.conn.execute("PRAGMA table_info(chat_lines)")
        columns = {row["name"] for row in await cur.fetchall()}
        assert {"id", "intent_id", "text", "slot", "enabled", "created_by", "updated_at"} <= columns
    finally:
        await db.close()


async def test_one_guild_cannot_hold_two_intents_of_the_same_name(tmp_path):
    db = Database(tmp_path / "c.sqlite3")
    await db.connect()
    try:
        await db.conn.execute(
            "INSERT INTO chat_intents(guild_id, name, triggers, kind, updated_at) "
            "VALUES (7, 'greeting', '[]', 'canned', 'now')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            await db.conn.execute(
                "INSERT INTO chat_intents(guild_id, name, triggers, kind, updated_at) "
                "VALUES (7, 'greeting', '[]', 'canned', 'now')"
            )
    finally:
        await db.close()


async def test_a_deleted_intent_takes_its_lines_with_it(tmp_path):
    """The lines are a child table, so a delete cannot leave orphans behind."""
    db = Database(tmp_path / "c.sqlite3")
    await db.connect()
    try:
        cur = await db.conn.execute(
            "INSERT INTO chat_intents(guild_id, name, triggers, kind, updated_at) "
            "VALUES (7, 'cookout', '[]', 'canned', 'now')"
        )
        intent_id = cur.lastrowid
        await db.conn.execute(
            "INSERT INTO chat_lines(intent_id, text, updated_at) VALUES (?, 'hi', 'now')",
            (intent_id,),
        )
        await db.conn.execute("DELETE FROM chat_intents WHERE id = ?", (intent_id,))
        cur = await db.conn.execute("SELECT COUNT(*) AS n FROM chat_lines")
        assert (await cur.fetchone())["n"] == 0
    finally:
        await db.close()


async def test_a_knowledge_section_carries_what_the_search_and_the_page_need(tmp_path):
    db = Database(tmp_path / "k.sqlite3")
    await db.connect()
    try:
        cur = await db.conn.execute("PRAGMA table_info(knowledge_sections)")
        columns = {row["name"] for row in await cur.fetchall()}
        assert {"id", "guild_id", "title", "body", "source", "tag"} <= columns
        assert {"updated_at", "updated_by"} <= columns
        cur = await db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND tbl_name='knowledge_sections'"
        )
        assert "knowledge_sections_by_source" in {row["name"] for row in await cur.fetchall()}
    finally:
        await db.close()


async def test_a_knowledge_section_is_written_by_staff_or_by_the_server_and_nothing_else(tmp_path):
    db = Database(tmp_path / "k.sqlite3")
    await db.connect()
    try:
        for source in ("staff", "server"):
            await db.conn.execute(
                "INSERT INTO knowledge_sections(guild_id, title, body, source, updated_at) "
                "VALUES (7, 'Rules', 'Be kind.', ?, 'now')",
                (source,),
            )
        with pytest.raises(sqlite3.IntegrityError):
            await db.conn.execute(
                "INSERT INTO knowledge_sections(guild_id, title, body, source, updated_at) "
                "VALUES (7, 'Rules', 'Be kind.', 'somebody_else', 'now')"
            )
    finally:
        await db.close()


async def test_the_trope_pool_is_keyed_by_name_so_a_reseed_cannot_double_it(tmp_path):
    db = Database(tmp_path / "t.sqlite3")
    await db.connect()
    try:
        cur = await db.conn.execute("PRAGMA table_info(personality_tropes)")
        columns = {row["name"] for row in await cur.fetchall()}
        assert {"name", "label", "voice", "neighbours", "enabled", "sort"} <= columns
        assert {"source", "updated_at", "updated_by"} <= columns
        await db.conn.execute(
            "INSERT INTO personality_tropes(name, label, voice, updated_at) "
            "VALUES ('warm', 'warm', 'You are WARM today.', 'now')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            await db.conn.execute(
                "INSERT INTO personality_tropes(name, label, voice, updated_at) "
                "VALUES ('warm', 'warm', 'again', 'now')"
            )
    finally:
        await db.close()


async def test_a_window_turn_belongs_to_a_member_or_to_the_bot_and_nothing_else(tmp_path):
    db = Database(tmp_path / "w.sqlite3")
    await db.connect()
    try:
        cur = await db.conn.execute("PRAGMA table_info(chat_window)")
        columns = {row["name"] for row in await cur.fetchall()}
        assert {"id", "guild_id", "channel_id", "user_id", "at"} <= columns
        assert {"speaker", "content", "tier"} <= columns
        for speaker in ("member", "bot"):
            await db.conn.execute(
                "INSERT INTO chat_window(guild_id, channel_id, user_id, at, speaker, content) "
                "VALUES (7, 11, 900, 'now', ?, 'hello')",
                (speaker,),
            )
        with pytest.raises(sqlite3.IntegrityError):
            await db.conn.execute(
                "INSERT INTO chat_window(guild_id, channel_id, user_id, at, speaker, content) "
                "VALUES (7, 11, 900, 'now', 'moderator', 'hello')"
            )
    finally:
        await db.close()


async def test_the_ledger_records_a_call_that_failed_as_well_as_one_that_answered(tmp_path):
    """A failed call still spends a turn, so the fuses can only count what is written here."""
    db = Database(tmp_path / "l.sqlite3")
    await db.connect()
    try:
        cur = await db.conn.execute("PRAGMA table_info(llm_ledger)")
        columns = {row["name"] for row in await cur.fetchall()}
        assert {"id", "at", "guild_id", "user_id", "turn", "provider", "model"} <= columns
        assert {"tier", "outcome", "input_tokens", "output_tokens"} <= columns
        assert {"cache_read_tokens", "cache_write_tokens", "cost_microdollars"} <= columns
        for outcome in ("ok", "error"):
            await db.conn.execute(
                "INSERT INTO llm_ledger(at, guild_id, user_id, turn, provider, model, tier, "
                "outcome) VALUES ('now', 7, 900, 'abc', 'anthropic', 'claude-haiku-4-5', "
                "'important', ?)",
                (outcome,),
            )
        with pytest.raises(sqlite3.IntegrityError):
            await db.conn.execute(
                "INSERT INTO llm_ledger(at, guild_id, user_id, turn, provider, model, tier, "
                "outcome) VALUES ('now', 7, 900, 'abc', 'anthropic', 'claude-haiku-4-5', "
                "'important', 'maybe')"
            )
    finally:
        await db.close()


async def test_a_poll_row_carries_every_column_phase_10_stores(tmp_path):
    db = Database(tmp_path / "p.sqlite3")
    await db.connect()
    try:
        cur = await db.conn.execute("PRAGMA table_info(polls)")
        columns = {row["name"] for row in await cur.fetchall()}
        assert {"guild_id", "creator_id", "question", "kind", "surface", "multi"} <= columns
        assert {"anonymous", "results", "hours", "auto_thread", "ping_role_id"} <= columns
        assert "status" in columns
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


SCHEMA_29_TICKETS = """CREATE TABLE modmail_tickets (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id       INTEGER NOT NULL,
    user_id        INTEGER NOT NULL,
    mode           TEXT    NOT NULL,
    channel_id     INTEGER NOT NULL,
    thread_id      INTEGER,
    status         TEXT    NOT NULL DEFAULT 'open',
    opened_at      TEXT    NOT NULL,
    closed_at      TEXT,
    closed_by      INTEGER,
    close_reason   TEXT,
    log_message_id INTEGER
)"""


async def test_the_sticky_card_and_practice_columns_arrive_on_a_schema_29_database(tmp_path):
    """29 → 30: both columns are added by ALTER, and a row written before them still reads."""
    path = tmp_path / "old.sqlite3"
    old = await aiosqlite.connect(path)
    old.row_factory = aiosqlite.Row
    await old.execute(SCHEMA_29_TICKETS)
    await old.execute(
        "INSERT INTO modmail_tickets(guild_id, user_id, mode, channel_id, status, opened_at) "
        "VALUES (1, 900, 'channel', 10, 'open', '2026-08-26T00:00:00+00:00')"
    )
    await old.commit()
    await old.close()

    db = Database(path)
    await db.connect()
    try:
        cur = await db.conn.execute("PRAGMA table_info(modmail_tickets)")
        columns = {row["name"] for row in await cur.fetchall()}
        assert {"card_message_id", "practice", "source", "opened_by"} <= columns
        cur = await db.conn.execute("SELECT * FROM modmail_tickets WHERE id = 1")
        row = await cur.fetchone()
        assert row["card_message_id"] is None
        assert row["practice"] == 0
        # 37 -> 38: a ticket older than the doors came in the only way there was.
        assert row["source"] == "dm" and row["opened_by"] is None
        cur = await db.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await db.close()


async def test_the_streamer_list_arrives_on_a_database_that_never_had_it(tmp_path):
    """38 → 39: one CREATE-IF-NOT-EXISTS table and its index, so an old database gains the
    streamer list on connect with nobody on it and nothing else touched."""
    path = tmp_path / "old39.sqlite3"
    old = await aiosqlite.connect(path)
    await old.execute("CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    await old.execute("INSERT INTO schema_meta(key, value) VALUES ('schema_version', '38')")
    await old.execute(
        "CREATE TABLE golive_fan_roles (guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, "
        "role_id INTEGER NOT NULL, created_at TEXT NOT NULL, created_by INTEGER, "
        "PRIMARY KEY (guild_id, user_id))"
    )
    await old.execute(
        "INSERT INTO golive_fan_roles VALUES (1, 2, 3, '2026-09-01T00:00:00+00:00', NULL)"
    )
    await old.commit()
    await old.close()

    db = Database(path)
    await db.connect()
    try:
        cur = await db.conn.execute("PRAGMA table_info(streamers)")
        assert {row["name"] for row in await cur.fetchall()} == {
            "guild_id",
            "user_id",
            "first_live_at",
            "last_live_at",
            "live_count",
            "platform",
            "login",
            "listed",
            "hidden_by",
            "hidden_at",
        }
        cur = await db.conn.execute("SELECT COUNT(*) AS n FROM streamers")
        assert (await cur.fetchone())["n"] == 0
        cur = await db.conn.execute("SELECT COUNT(*) AS n FROM golive_fan_roles")
        assert (await cur.fetchone())["n"] == 1
        cur = await db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='streamers_by_last_live'"
        )
        assert await cur.fetchone() is not None
        cur = await db.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await db.close()


async def test_the_self_test_tables_arrive_on_a_database_that_never_had_them(tmp_path):
    """30 → 31: two CREATE-IF-NOT-EXISTS tables, so an old database gains them on connect."""
    path = tmp_path / "old31.sqlite3"
    old = await aiosqlite.connect(path)
    await old.execute("CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    await old.execute("INSERT INTO schema_meta(key, value) VALUES ('schema_version', '30')")
    await old.commit()
    await old.close()

    db = Database(path)
    await db.connect()
    try:
        cur = await db.conn.execute("PRAGMA table_info(selftest_runs)")
        assert {row["name"] for row in await cur.fetchall()} == {
            "id",
            "guild_id",
            "started_at",
            "finished_at",
            "ok",
            "failed",
            "posted",
            "purged_at",
            "via",
            "actor_id",
            "keep_minutes",
        }
        cur = await db.conn.execute("PRAGMA table_info(selftest_messages)")
        assert {row["name"] for row in await cur.fetchall()} == {
            "id",
            "run_id",
            "guild_id",
            "channel_id",
            "message_id",
            "posted_at",
        }
        cur = await db.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await db.close()


async def test_the_action_log_index_arrives_on_a_database_that_never_had_it(tmp_path):
    """31 → 32: the self-test's run detail reads one run's check rows out of the action log."""
    path = tmp_path / "old32.sqlite3"
    old = await aiosqlite.connect(path)
    await old.execute("CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    await old.execute("INSERT INTO schema_meta(key, value) VALUES ('schema_version', '31')")
    await old.commit()
    await old.close()

    db = Database(path)
    await db.connect()
    try:
        cur = await db.conn.execute("PRAGMA index_info(action_log_by_kind)")
        assert [row["name"] for row in await cur.fetchall()] == ["guild_id", "kind", "id"]
        cur = await db.conn.execute(
            "EXPLAIN QUERY PLAN SELECT at, kind, details FROM action_log WHERE guild_id = ? "
            "AND kind IN (?, ?) AND json_extract(details, '$.run_id') = ? ORDER BY id",
            (1, "selftest.check", "web.selftest.check", 1),
        )
        assert any("action_log_by_kind" in row["detail"] for row in await cur.fetchall())
    finally:
        await db.close()


async def test_a_fresh_database_carries_the_sticky_card_and_practice_columns(tmp_path):
    db = Database(tmp_path / "fresh.sqlite3")
    await db.connect()
    try:
        await open_ticket(db, 901, 20)
        cur = await db.conn.execute("SELECT * FROM modmail_tickets WHERE user_id = 901")
        row = await cur.fetchone()
        assert row["card_message_id"] is None
        assert row["practice"] == 0
        await db.conn.execute(
            "UPDATE modmail_tickets SET card_message_id = 55, practice = 1 WHERE user_id = 901"
        )
        await db.conn.commit()
        cur = await db.conn.execute("SELECT * FROM modmail_tickets WHERE user_id = 901")
        row = await cur.fetchone()
        assert row["card_message_id"] == 55
        assert row["practice"] == 1
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
        names = {row["name"] for row in await cur.fetchall()}
        assert {"live_role_added", "live_role_id"} <= names
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
        assert names.count("live_role_id") == 1
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


async def test_a_schema_20_file_gains_the_fan_role_table_and_keeps_its_rows(tmp_path):
    """Schema 21 is additive: the file that ships without ping roles gets the table on the
    next boot and nothing already in it is rewritten."""
    path = tmp_path / "old.sqlite3"
    db = Database(path)
    await db.connect()
    await open_session(db, 5)
    await db.conn.execute("DROP TABLE golive_fan_roles")
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '20')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        assert "golive_fan_roles" in {row["name"] for row in await cur.fetchall()}
        cur = await again.conn.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        )
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
        cur = await again.conn.execute("SELECT user_id FROM golive_sessions")
        assert [row["user_id"] for row in await cur.fetchall()] == [5]
        await again.conn.execute(
            "INSERT INTO golive_fan_roles(guild_id, user_id, role_id, created_at, created_by) "
            "VALUES (7, 5, 99, '2026-09-02T00:00:00+00:00', 3)"
        )
        with pytest.raises(sqlite3.IntegrityError):
            await again.conn.execute(
                "INSERT INTO golive_fan_roles(guild_id, user_id, role_id, created_at) "
                "VALUES (7, 5, 100, '2026-09-02T00:00:00+00:00')"
            )
    finally:
        await again.close()


async def test_a_schema_21_file_gains_the_youtube_tables_and_keeps_its_rows(tmp_path):
    """Schema 22 is additive: the file that ships without upload posts gets the two tables on
    the next boot and nothing already in it is rewritten."""
    path = tmp_path / "old21.sqlite3"
    db = Database(path)
    await db.connect()
    await open_session(db, 5)
    await db.conn.execute("DROP TABLE youtube_links")
    await db.conn.execute("DROP TABLE youtube_videos")
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '21')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        assert {"youtube_links", "youtube_videos"} <= {row["name"] for row in await cur.fetchall()}
        cur = await again.conn.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        )
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
        cur = await again.conn.execute("SELECT user_id FROM golive_sessions")
        assert [row["user_id"] for row in await cur.fetchall()] == [5]
        await again.conn.execute(
            "INSERT INTO youtube_links(user_id, channel_id, linked_at) "
            "VALUES (5, 'UCsXVk37bltHxD1rDPwtNM8Q', '2026-09-02T00:00:00+00:00')"
        )
        cur = await again.conn.execute("SELECT seeded FROM youtube_links WHERE user_id = 5")
        assert (await cur.fetchone())["seeded"] == 0
        with pytest.raises(sqlite3.IntegrityError):
            await again.conn.execute(
                "INSERT INTO youtube_links(user_id, channel_id, linked_at) "
                "VALUES (5, 'UCother', '2026-09-02T00:00:00+00:00')"
            )
    finally:
        await again.close()


async def test_a_video_is_recorded_once_however_often_the_feed_repeats_it(tmp_path):
    """`youtube_videos.video_id` is the primary key, so a re-poll cannot announce twice."""
    db = Database(tmp_path / "v.sqlite3")
    await db.connect()
    try:
        await db.conn.execute(
            "INSERT INTO youtube_videos(video_id, user_id, channel_id, published_at, seen_at) "
            "VALUES ('abc', 5, 'UC1', '2026-09-01T00:00:00+00:00', '2026-09-02T00:00:00+00:00')"
        )
        cur = await db.conn.execute("SELECT kind, announced_at, mode FROM youtube_videos")
        row = await cur.fetchone()
        assert (row["kind"], row["announced_at"], row["mode"]) == ("video", None, None)
        with pytest.raises(sqlite3.IntegrityError):
            await db.conn.execute(
                "INSERT INTO youtube_videos(video_id, user_id, channel_id, published_at, "
                "seen_at) VALUES ('abc', 6, 'UC2', '2026-09-01T00:00:00+00:00', "
                "'2026-09-02T00:00:00+00:00')"
            )
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


async def test_an_open_poll_gains_a_vote_scheme_column_and_keeps_its_old_scheme(tmp_path):
    """KI-9: a poll written before the column stays NULL, which reads as the old hash."""
    path = tmp_path / "old.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute("ALTER TABLE polls DROP COLUMN vote_scheme")
    await db.conn.execute(
        "INSERT INTO polls(id, guild_id, creator_id, question, anonymous, status, created_at) "
        "VALUES (1, 7, 9, 'now?', 1, 'open', '2026-08-27T00:00:00+00:00')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("PRAGMA table_info(polls)")
        assert "vote_scheme" in {row["name"] for row in await cur.fetchall()}
        cur = await again.conn.execute("SELECT vote_scheme FROM polls WHERE id = 1")
        assert (await cur.fetchone())["vote_scheme"] is None
    finally:
        await again.close()


async def test_a_self_test_run_gains_its_keep_minutes_column_on_an_older_file(tmp_path):
    """46 → 47: `/test keep:` is on the ROW, so a run outlives the restart that forgets it."""
    path = tmp_path / "old.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute("ALTER TABLE selftest_runs DROP COLUMN keep_minutes")
    await db.conn.execute(
        "INSERT INTO selftest_runs(id, guild_id, started_at, via) "
        "VALUES (1, 7, '2026-09-20T00:00:00+00:00', 'discord')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("PRAGMA table_info(selftest_runs)")
        assert "keep_minutes" in {row["name"] for row in await cur.fetchall()}
        cur = await again.conn.execute("SELECT keep_minutes FROM selftest_runs WHERE id = 1")
        assert (await cur.fetchone())["keep_minutes"] is None
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


async def test_an_events_row_gains_the_two_where_columns_on_an_older_file(tmp_path):
    path = tmp_path / "old.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute("ALTER TABLE events DROP COLUMN where_kind")
    await db.conn.execute("ALTER TABLE events DROP COLUMN where_channel_id")
    await db.conn.execute(
        "INSERT INTO events(id, guild_id, requester_id, title, location, starts_at, status, "
        "created_at) VALUES (1, 7, 9, 'Block Party', 'the park', '2026-09-14T19:30:00+00:00', "
        "'pending', '2026-09-10T00:00:00+00:00')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("PRAGMA table_info(events)")
        names = {row["name"] for row in await cur.fetchall()}
        assert {"where_kind", "where_channel_id"} <= names
        cur = await again.conn.execute("SELECT * FROM events WHERE id = 1")
        row = await cur.fetchone()
        assert row["where_kind"] is None and row["where_channel_id"] is None
        assert row["location"] == "the park"
    finally:
        await again.close()

    third = Database(path)
    await third.connect()
    try:
        cur = await third.conn.execute("PRAGMA table_info(events)")
        names = [row["name"] for row in await cur.fetchall()]
        assert names.count("where_kind") == 1 and names.count("where_channel_id") == 1
        cur = await third.conn.execute(
            "SELECT value FROM schema_meta WHERE key = 'schema_version'"
        )
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await third.close()


async def test_a_profile_and_an_optout_carry_what_the_memory_reads(tmp_path):
    db = Database(tmp_path / "m.sqlite3")
    await db.connect()
    try:
        cur = await db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        assert {"chat_profiles", "chat_memory_optout"} <= {
            row["name"] for row in await cur.fetchall()
        }
        cur = await db.conn.execute("PRAGMA table_info(chat_profiles)")
        assert {
            "user_id",
            "guild_id",
            "call_me",
            "notes",
            "threads",
            "turns_seen",
            "created_at",
            "updated_at",
        } == {row["name"] for row in await cur.fetchall()}
        await db.conn.execute(
            "INSERT INTO chat_profiles(user_id, guild_id, created_at, updated_at) "
            "VALUES (9, 7, '2026-09-02T00:00:00+00:00', '2026-09-02T00:00:00+00:00')"
        )
        cur = await db.conn.execute("SELECT notes, threads, turns_seen FROM chat_profiles")
        row = await cur.fetchone()
        assert (row["notes"], row["threads"], row["turns_seen"]) == ("[]", "[]", 0)
        with pytest.raises(sqlite3.IntegrityError):
            await db.conn.execute(
                "INSERT INTO chat_profiles(user_id, guild_id, created_at, updated_at) "
                "VALUES (9, 7, '2026-09-02T00:00:00+00:00', '2026-09-02T00:00:00+00:00')"
            )
    finally:
        await db.close()


async def test_a_schema_22_file_gains_the_memory_tables_and_the_held_from_column(tmp_path):
    """Schema 23 is additive: the file that ships before long-term memory gets the two tables,
    requests gain held_from, and nothing already in it is rewritten."""
    path = tmp_path / "old22.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute("DROP TABLE chat_profiles")
    await db.conn.execute("DROP TABLE chat_memory_optout")
    await db.conn.execute("ALTER TABLE requests DROP COLUMN held_from")
    await db.conn.execute(
        "INSERT INTO requests(id, guild_id, user_id, what, why, status, created_at) "
        "VALUES (1, 7, 9, 'a bot', 'because', 'in_progress', '2026-08-27T00:00:00+00:00')"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '22')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        assert {"chat_profiles", "chat_memory_optout"} <= {
            row["name"] for row in await cur.fetchall()
        }
        cur = await again.conn.execute("PRAGMA table_info(requests)")
        assert "held_from" in {row["name"] for row in await cur.fetchall()}
        cur = await again.conn.execute("SELECT status, held_from FROM requests WHERE id = 1")
        row = await cur.fetchone()
        assert (row["status"], row["held_from"]) == ("in_progress", None)
        cur = await again.conn.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        )
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await again.close()


async def test_a_schema_25_file_gains_the_four_review_columns_and_keeps_its_rows(tmp_path):
    """Schema 26 is additive and backfills nothing: a done row from before the review state
    keeps its status, and the four new columns read as nothing rather than crashing."""
    path = tmp_path / "old25.sqlite3"
    db = Database(path)
    await db.connect()
    for column in ("built", "how_to_test", "ready_by", "sent_back_reason"):
        await db.conn.execute(f"ALTER TABLE requests DROP COLUMN {column}")
    await db.conn.execute(
        "INSERT INTO requests(id, guild_id, user_id, what, why, status, created_at, done_at) "
        "VALUES (1, 7, 9, 'raid trains', 'because', 'done', '2026-09-01T00:00:00+00:00', "
        "'2026-09-02T00:00:00+00:00')"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '25')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("PRAGMA table_info(requests)")
        assert {"built", "how_to_test", "ready_by", "sent_back_reason"} <= {
            row["name"] for row in await cur.fetchall()
        }
        cur = await again.conn.execute(
            "SELECT status, built, how_to_test, ready_by, sent_back_reason, done_at "
            "FROM requests WHERE id = 1"
        )
        row = await cur.fetchone()
        assert row["status"] == "done" and row["done_at"] == "2026-09-02T00:00:00+00:00"
        assert (row["built"], row["how_to_test"]) == (None, None)
        assert (row["ready_by"], row["sent_back_reason"]) == (None, None)
        cur = await again.conn.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        )
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await again.close()


async def test_a_schema_26_file_gains_the_two_check_asked_columns_and_keeps_its_rows(tmp_path):
    """Schema 27 is additive: a review row from before Ask-them-to-check keeps its status and
    reads both new columns as nothing."""
    path = tmp_path / "old26.sqlite3"
    db = Database(path)
    await db.connect()
    for column in ("check_asked_by", "check_asked_at"):
        await db.conn.execute(f"ALTER TABLE requests DROP COLUMN {column}")
    await db.conn.execute(
        "INSERT INTO requests(id, guild_id, user_id, what, why, status, created_at, ready_by) "
        "VALUES (1, 7, 9, 'a request board', 'because', 'review', "
        "'2026-09-03T00:00:00+00:00', 5)"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '26')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("PRAGMA table_info(requests)")
        assert {"check_asked_by", "check_asked_at"} <= {
            row["name"] for row in await cur.fetchall()
        }
        cur = await again.conn.execute(
            "SELECT status, ready_by, check_asked_by, check_asked_at FROM requests WHERE id = 1"
        )
        row = await cur.fetchone()
        assert (row["status"], row["ready_by"]) == ("review", 5)
        assert (row["check_asked_by"], row["check_asked_at"]) == (None, None)
        cur = await again.conn.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        )
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await again.close()


async def test_a_schema_28_file_gains_the_six_case_columns_and_keeps_its_rows(tmp_path):
    """Schema 29 is additive: a case written before notes and voiding keeps every value it had
    and reads all six new columns as nothing."""
    path = tmp_path / "old28.sqlite3"
    db = Database(path)
    await db.connect()
    for column in ("note", "note_by", "note_at", "voided_at", "voided_by", "void_reason"):
        await db.conn.execute(f"ALTER TABLE mod_cases DROP COLUMN {column}")
    await db.conn.execute(
        "INSERT INTO mod_cases(id, guild_id, user_id, kind, moderator_id, reason, at, mode, "
        "applied, log_message_id) VALUES (1, 7, 900, 'warn', 3, 'spamming', "
        "'2026-09-04T00:00:00+00:00', 'on', 1, 55)"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '28')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("PRAGMA table_info(mod_cases)")
        names = [row["name"] for row in await cur.fetchall()]
        assert {"note", "note_by", "note_at", "voided_at", "voided_by", "void_reason"} <= set(names)
        assert names.count("note") == 1 and names.count("voided_at") == 1
        cur = await again.conn.execute("SELECT * FROM mod_cases WHERE id = 1")
        row = await cur.fetchone()
        assert (row["kind"], row["reason"], row["applied"]) == ("warn", "spamming", 1)
        assert (row["user_id"], row["moderator_id"], row["log_message_id"]) == (900, 3, 55)
        assert (row["note"], row["note_by"], row["note_at"]) == (None, None, None)
        assert (row["voided_at"], row["voided_by"], row["void_reason"]) == (None, None, None)
        cur = await again.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await again.close()


async def test_a_schema_22_file_gains_the_raid_train_tables_and_keeps_its_rows(tmp_path):
    """Schema 24 is additive: a file that shipped without raid trains gets both tables on the
    next boot, and nothing already in it is rewritten."""
    path = tmp_path / "old22.sqlite3"
    db = Database(path)
    await db.connect()
    await open_session(db, 5)
    await db.conn.execute("DROP TABLE raid_slots")
    await db.conn.execute("DROP TABLE raid_trains")
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '22')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        assert {"raid_trains", "raid_slots"} <= {row["name"] for row in await cur.fetchall()}
        cur = await again.conn.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        )
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
        cur = await again.conn.execute("SELECT user_id FROM golive_sessions")
        assert [row["user_id"] for row in await cur.fetchall()] == [5]
    finally:
        await again.close()


async def test_the_retired_request_statuses_become_open_once_and_nothing_else_moves(tmp_path):
    """pending, approved and planned are gone; a second boot finds nothing left to move."""
    path = tmp_path / "states.sqlite3"
    db = Database(path)
    await db.connect()
    for request_id, status in (
        (1, "pending"),
        (2, "approved"),
        (3, "planned"),
        (4, "in_progress"),
        (5, "done"),
        (6, "declined"),
        (7, "withdrawn"),
    ):
        await db.conn.execute(
            "INSERT INTO requests(id, guild_id, user_id, what, why, status, created_at) "
            "VALUES (?, 7, 9, 'a bot', 'because', ?, '2026-08-27T00:00:00+00:00')",
            (request_id, status),
        )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("SELECT id, status FROM requests ORDER BY id")
        assert [row["status"] for row in await cur.fetchall()] == [
            "open",
            "open",
            "open",
            "in_progress",
            "done",
            "declined",
            "withdrawn",
        ]
    finally:
        await again.close()

    third = Database(path)
    await third.connect()
    try:
        cur = await third.conn.execute(
            "SELECT COUNT(*) AS found FROM requests WHERE status = ?", ("open",)
        )
        assert (await cur.fetchone())["found"] == 3
    finally:
        await third.close()


async def test_a_new_request_row_defaults_to_open(tmp_path):
    db = Database(tmp_path / "d.sqlite3")
    await db.connect()
    try:
        await db.conn.execute(
            "INSERT INTO requests(id, guild_id, user_id, what, why, created_at) "
            "VALUES (1, 7, 9, 'a bot', 'because', '2026-09-02T00:00:00+00:00')"
        )
        cur = await db.conn.execute("SELECT status FROM requests WHERE id = 1")
        assert (await cur.fetchone())["status"] == "open"
    finally:
        await db.close()


async def test_two_slots_cannot_share_one_position_on_a_train(tmp_path):
    db = Database(tmp_path / "trains.sqlite3")
    await db.connect()
    try:
        await db.conn.execute(
            "INSERT INTO raid_trains(id, guild_id, organizer_id, title, starts_at, "
            "slot_minutes, slot_count, created_at, updated_at) "
            "VALUES (1, 7, 3, 'Saturday', '2026-09-14T19:00:00+00:00', 60, 2, 'now', 'now')"
        )
        await db.conn.execute(
            "INSERT INTO raid_slots(train_id, position, starts_at, ends_at) "
            "VALUES (1, 1, '2026-09-14T19:00:00+00:00', '2026-09-14T20:00:00+00:00')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            await db.conn.execute(
                "INSERT INTO raid_slots(train_id, position, starts_at, ends_at) "
                "VALUES (1, 1, '2026-09-14T19:00:00+00:00', '2026-09-14T20:00:00+00:00')"
            )
        cur = await db.conn.execute("SELECT status FROM raid_trains")
        assert (await cur.fetchone())["status"] == "open"
        cur = await db.conn.execute("SELECT locked FROM raid_slots")
        assert (await cur.fetchone())["locked"] == 0
    finally:
        await db.close()


APPLICATION_FORMS_AT_26 = """
CREATE TABLE application_forms (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id          INTEGER NOT NULL,
    name              TEXT    NOT NULL,
    title             TEXT    NOT NULL,
    description       TEXT,
    role_id           INTEGER NOT NULL,
    review_channel_id INTEGER,
    approver_role_id  INTEGER,
    owner_user_id     INTEGER,
    next_step         TEXT,
    approved_text     TEXT,
    expires_days      INTEGER,
    retry_days        INTEGER,
    open              INTEGER NOT NULL DEFAULT 1,
    panel_channel_id  INTEGER,
    panel_message_id  INTEGER,
    created_by        INTEGER NOT NULL,
    created_at        TEXT    NOT NULL,
    updated_at        TEXT    NOT NULL,
    UNIQUE (guild_id, name)
)
"""


async def _a_schema_26_applications_file(path):
    db = Database(path)
    await db.connect()
    await db.conn.execute("PRAGMA foreign_keys=OFF")
    await db.conn.execute("DROP TABLE application_forms")
    await db.conn.execute(APPLICATION_FORMS_AT_26)
    for form_id, name in ((1, "twitch-team"), (2, "mod-team")):
        await db.conn.execute(
            "INSERT INTO application_forms(id, guild_id, name, title, role_id, created_by, "
            "created_at, updated_at) VALUES (?, 7, ?, ?, 4242, 1, 'then', 'then')",
            (form_id, name, name.title()),
        )
    for form_id, position, label in ((1, 1, "Twitch handle"), (1, 2, "How long"), (2, 1, "Why")):
        await db.conn.execute(
            "INSERT INTO application_questions(form_id, position, label) VALUES (?, ?, ?)",
            (form_id, position, label),
        )
    await db.conn.execute(
        "INSERT INTO applications(id, guild_id, form_id, user_id, answers, status, submitted_at) "
        "VALUES (1, 7, 1, 900, '[]', 'approved', 'then')"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '26')"
    )
    await db.conn.commit()
    await db.close()


async def test_a_schema_26_file_lets_a_form_drop_its_role_and_keeps_every_question(tmp_path):
    """Schema 28 rebuilds application_forms BEFORE foreign_keys goes on, because the drop
    would otherwise cascade every application_questions row away with it."""
    path = tmp_path / "old26.sqlite3"
    await _a_schema_26_applications_file(path)

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("PRAGMA table_info(application_forms)")
        role = next(row for row in await cur.fetchall() if row["name"] == "role_id")
        assert role["notnull"] == 0
        cur = await again.conn.execute(
            "SELECT id, name, role_id FROM application_forms ORDER BY id"
        )
        assert [tuple(row) for row in await cur.fetchall()] == [
            (1, "twitch-team", 4242),
            (2, "mod-team", 4242),
        ]
        cur = await again.conn.execute(
            "SELECT form_id, position, label FROM application_questions ORDER BY form_id, position"
        )
        assert [tuple(row) for row in await cur.fetchall()] == [
            (1, 1, "Twitch handle"),
            (1, 2, "How long"),
            (2, 1, "Why"),
        ]
        cur = await again.conn.execute("SELECT status FROM applications WHERE id = 1")
        assert (await cur.fetchone())["status"] == "approved"
        cur = await again.conn.execute("PRAGMA foreign_keys")
        assert (await cur.fetchone())[0] == 1
        cur = await again.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        assert "application_forms_loosened" not in {row["name"] for row in await cur.fetchall()}
        cur = await again.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
        await again.conn.execute(
            "INSERT INTO application_forms(guild_id, name, title, role_id, created_by, "
            "created_at, updated_at) VALUES (7, 'no-role', 'No role', NULL, 1, 'now', 'now')"
        )
    finally:
        await again.close()


async def test_the_application_forms_rebuild_runs_once_and_is_quiet_the_second_time(
    tmp_path, caplog
):
    path = tmp_path / "twice.sqlite3"
    await _a_schema_26_applications_file(path)

    caplog.clear()
    with caplog.at_level("WARNING"):
        first = Database(path)
        await first.connect()
        await first.close()
    assert any("rebuilding application_forms" in one.message for one in caplog.records)

    caplog.clear()
    with caplog.at_level("WARNING"):
        second = Database(path)
        await second.connect()
        try:
            cur = await second.conn.execute("SELECT COUNT(*) AS n FROM application_questions")
            assert (await cur.fetchone())["n"] == 3
        finally:
            await second.close()
    assert not any("rebuilding application_forms" in one.message for one in caplog.records)


async def test_a_schema_32_file_gains_the_draft_table_and_keeps_its_polls(tmp_path):
    """Schema 33 is additive: a poll written before saved drafts is untouched, and the new
    table arrives empty with one row per person per guild."""
    path = tmp_path / "old32.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute("DROP TABLE poll_drafts")
    await db.conn.execute(
        "INSERT INTO polls(id, guild_id, creator_id, question, status, created_at) "
        "VALUES (1, 7, 9, 'Pizza or tacos?', 'open', '2026-09-06T00:00:00+00:00')"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '32')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        assert "poll_drafts" in {row["name"] for row in await cur.fetchall()}
        cur = await again.conn.execute("SELECT COUNT(*) AS n FROM poll_drafts")
        assert (await cur.fetchone())["n"] == 0
        cur = await again.conn.execute("SELECT question, status FROM polls WHERE id = 1")
        row = await cur.fetchone()
        assert (row["question"], row["status"]) == ("Pizza or tacos?", "open")
        cur = await again.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)

        await again.conn.execute(
            "INSERT INTO poll_drafts(guild_id, user_id, payload, saved_at) "
            "VALUES (7, 9, '{}', 'now')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            await again.conn.execute(
                "INSERT INTO poll_drafts(guild_id, user_id, payload, saved_at) "
                "VALUES (7, 9, '{}', 'later')"
            )
    finally:
        await again.close()


GUIDE_TABLES = (
    "guides",
    "guide_steps",
    "guide_faults",
    "guide_facts",
    "guide_media",
    "guide_releases",
)


async def a_schema_34_file(path):
    """What the code at `main` leaves behind: everything but the six guides tables."""
    db = Database(path)
    await db.connect()
    for name in GUIDE_TABLES:
        await db.conn.execute(f"DROP TABLE IF EXISTS {name}")
    await db.conn.execute("DROP INDEX IF EXISTS guides_one_published_command")
    await db.conn.execute(
        "INSERT INTO settings(guild_id, key, value, updated_at) VALUES (1, 'golive_mode', "
        "'\"on\"', '2026-09-16T00:00:00+00:00')"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '34')"
    )
    await db.conn.commit()
    await db.close()


async def test_a_schema_34_file_gains_the_six_guides_tables_and_keeps_its_rows(tmp_path):
    """Schema 35 is additive: the file that ships before guides gets the six tables and the
    partial unique index, and nothing already in it is rewritten."""
    path = tmp_path / "old34.sqlite3"
    await a_schema_34_file(path)

    db = Database(path)
    await db.connect()
    try:
        cur = await db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        assert set(GUIDE_TABLES) <= {row["name"] for row in await cur.fetchall()}
        cur = await db.conn.execute("SELECT key, value FROM settings")
        assert [tuple(row) for row in await cur.fetchall()] == [("golive_mode", '"on"')]
        cur = await db.conn.execute(
            "SELECT value FROM schema_meta WHERE key = 'schema_version'"
        )
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("PRAGMA table_info(guides)")
        assert {row["name"] for row in await cur.fetchall()} == {
            "id",
            "guild_id",
            "slug",
            "title",
            "goal",
            "audience",
            "feature",
            "command",
            "sort",
            "published",
            "seed_hash",
            "updated_at",
            "updated_by",
        }
    finally:
        await again.close()


async def test_a_guide_keeps_one_slug_and_one_published_guide_per_command(tmp_path):
    db = Database(tmp_path / "guides.sqlite3")
    await db.connect()
    try:
        await db.conn.execute(
            "INSERT INTO guides(guild_id, slug, title, goal, audience, feature, command, "
            "published, updated_at) VALUES (1, 'a', 'A', 'g', 'member', 'golive', '/golive', "
            "1, '2026-09-16T00:00:00+00:00')"
        )
        await db.conn.commit()

        with pytest.raises(sqlite3.IntegrityError):
            await db.conn.execute(
                "INSERT INTO guides(guild_id, slug, title, goal, audience, feature, command, "
                "published, updated_at) VALUES (1, 'b', 'B', 'g', 'member', 'golive', "
                "'/golive', 1, '2026-09-16T00:00:00+00:00')"
            )
        # Unpublished, a staff one, and another guild are all allowed beside it.
        await db.conn.execute(
            "INSERT INTO guides(guild_id, slug, title, goal, audience, feature, command, "
            "published, updated_at) VALUES (1, 'c', 'C', 'g', 'member', 'golive', '/golive', "
            "0, '2026-09-16T00:00:00+00:00')"
        )
        await db.conn.execute(
            "INSERT INTO guides(guild_id, slug, title, goal, audience, feature, command, "
            "published, updated_at) VALUES (1, 'd', 'D', 'g', 'staff', 'golive', '/golive', "
            "1, '2026-09-16T00:00:00+00:00')"
        )
        await db.conn.execute(
            "INSERT INTO guides(guild_id, slug, title, goal, audience, feature, command, "
            "published, updated_at) VALUES (2, 'a', 'A', 'g', 'member', 'golive', '/golive', "
            "1, '2026-09-16T00:00:00+00:00')"
        )
        await db.conn.commit()

        with pytest.raises(sqlite3.IntegrityError):
            await db.conn.execute(
                "INSERT INTO guides(guild_id, slug, title, goal, audience, feature, "
                "updated_at) VALUES (1, 'a', 'Again', 'g', 'member', 'golive', "
                "'2026-09-16T00:00:00+00:00')"
            )
    finally:
        await db.close()


async def test_a_deleted_guide_takes_its_steps_faults_facts_and_pictures_with_it(tmp_path):
    db = Database(tmp_path / "guides.sqlite3")
    await db.connect()
    try:
        cur = await db.conn.execute(
            "INSERT INTO guides(guild_id, slug, title, goal, audience, feature, updated_at) "
            "VALUES (1, 'a', 'A', 'g', 'member', 'golive', '2026-09-16T00:00:00+00:00')"
        )
        guide_id = cur.lastrowid
        await db.conn.execute(
            "INSERT INTO guide_steps(guide_id, position, do_text) VALUES (?, 1, 'Press **A**.')",
            (guide_id,),
        )
        await db.conn.execute(
            "INSERT INTO guide_faults(guide_id, position, symptom, answer) "
            "VALUES (?, 1, 'no', 'yes')",
            (guide_id,),
        )
        await db.conn.execute(
            "INSERT INTO guide_facts(guide_id, position, kind, ref) "
            "VALUES (?, 1, 'setting', 'golive_mode')",
            (guide_id,),
        )
        await db.conn.execute(
            "INSERT INTO guide_media(guild_id, guide_id, file, sha256, shot_at) "
            "VALUES (1, ?, '1.png', 'abc', '2026-09-16T00:00:00+00:00')",
            (guide_id,),
        )
        await db.conn.commit()

        await db.conn.execute("DELETE FROM guides WHERE id = ?", (guide_id,))
        await db.conn.commit()

        for table in ("guide_steps", "guide_faults", "guide_facts", "guide_media"):
            cur = await db.conn.execute(f"SELECT COUNT(*) AS n FROM {table}")
            assert (await cur.fetchone())["n"] == 0, table
    finally:
        await db.close()


async def a_schema_35_file(path):
    """What the code at `main` leaves behind: everything but the posts table."""
    db = Database(path)
    await db.connect()
    await db.conn.execute("DROP INDEX IF EXISTS posts_by_guild")
    await db.conn.execute("DROP TABLE IF EXISTS posts")
    await db.conn.execute(
        "INSERT INTO settings(guild_id, key, value, updated_at) VALUES (1, 'guides_mode', "
        "'\"on\"', '2026-09-16T00:00:00+00:00')"
    )
    await db.conn.execute(
        "INSERT INTO guides(guild_id, slug, title, goal, feature, updated_at) "
        "VALUES (1, 'kept', 'Kept', 'Nothing here moves.', 'core', '2026-09-16T00:00:00+00:00')"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '35')"
    )
    await db.conn.commit()
    await db.close()


async def test_a_schema_35_file_gains_the_posts_table_and_keeps_its_rows(tmp_path):
    """Schema 36 is additive: the file that ships before posts gets the table and its index,
    and nothing already in it is rewritten."""
    path = tmp_path / "old35.sqlite3"
    await a_schema_35_file(path)

    db = Database(path)
    await db.connect()
    try:
        cur = await db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        assert "posts" in {row["name"] for row in await cur.fetchall()}
        cur = await db.conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        assert "posts_by_guild" in {row["name"] for row in await cur.fetchall()}
        cur = await db.conn.execute("SELECT key, value FROM settings")
        assert [tuple(row) for row in await cur.fetchall()] == [("guides_mode", '"on"')]
        cur = await db.conn.execute("SELECT slug FROM guides")
        assert [row["slug"] for row in await cur.fetchall()] == ["kept"]
        cur = await db.conn.execute(
            "SELECT value FROM schema_meta WHERE key = 'schema_version'"
        )
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
        cur = await db.conn.execute("SELECT COUNT(*) AS n FROM posts")
        assert (await cur.fetchone())["n"] == 0
    finally:
        await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("PRAGMA table_info(posts)")
        assert {row["name"] for row in await cur.fetchall()} == {
            "id",
            "guild_id",
            "slug",
            "title",
            "channel_id",
            "body",
            "style",
            "pin",
            "message_id",
            "shadow_message_id",
            "posted_hash",
            "posted_at",
            "posted_by",
            "seed_hash",
            "updated_at",
            "updated_by",
        }
    finally:
        await again.close()


async def a_schema_36_file(path):
    """What the code at `main` leaves behind: posts, with no shadow copy to track."""
    db = Database(path)
    await db.connect()
    await db.conn.execute("ALTER TABLE posts DROP COLUMN shadow_message_id")
    await db.conn.execute(
        "INSERT INTO posts(guild_id, slug, title, channel_id, body, style, pin, message_id, "
        "posted_hash, updated_at) VALUES (1, 'welcome', 'Welcome and rules', 5, 'Hello.', "
        "'plain', 1, 99, 'a-hash', '2026-09-16T00:00:00+00:00')"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '36')"
    )
    await db.conn.commit()
    await db.close()


async def test_a_schema_36_file_gains_shadow_message_id_and_keeps_every_post(tmp_path):
    """Schema 37 is one nullable column: the posts already written keep every word, every id
    and their posted hash, and the new column arrives empty."""
    path = tmp_path / "old36.sqlite3"
    await a_schema_36_file(path)

    db = Database(path)
    await db.connect()
    try:
        cur = await db.conn.execute("PRAGMA table_info(posts)")
        assert "shadow_message_id" in {row["name"] for row in await cur.fetchall()}
        cur = await db.conn.execute("SELECT * FROM posts WHERE guild_id = 1")
        row = await cur.fetchone()
        assert row["slug"] == "welcome" and row["body"] == "Hello."
        assert row["message_id"] == 99 and row["posted_hash"] == "a-hash"
        assert row["shadow_message_id"] is None
        cur = await db.conn.execute(
            "SELECT value FROM schema_meta WHERE key = 'schema_version'"
        )
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await db.close()


async def test_two_posts_cannot_share_a_slug_and_only_the_two_styles_are_storable(tmp_path):
    db = Database(tmp_path / "posts.sqlite3")
    await db.connect()
    try:
        await db.conn.execute(
            "INSERT INTO posts(guild_id, slug, title, body, style, updated_at) "
            "VALUES (1, 'welcome', 'Welcome', '', 'plain', 'now')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            await db.conn.execute(
                "INSERT INTO posts(guild_id, slug, title, body, style, updated_at) "
                "VALUES (1, 'welcome', 'Again', '', 'plain', 'now')"
            )
        # The same slug in another server is a different post, and that is allowed.
        await db.conn.execute(
            "INSERT INTO posts(guild_id, slug, title, body, style, updated_at) "
            "VALUES (2, 'welcome', 'Welcome', '', 'embed', 'now')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            await db.conn.execute(
                "INSERT INTO posts(guild_id, slug, title, body, style, updated_at) "
                "VALUES (3, 'welcome', 'Welcome', '', 'markdown', 'now')"
            )
        cur = await db.conn.execute("SELECT pin, message_id FROM posts WHERE guild_id = 1")
        row = await cur.fetchone()
        assert row["pin"] == 1 and row["message_id"] is None
    finally:
        await db.close()


async def test_a_schema_40_file_gains_requests_thread_id_and_keeps_its_rows(tmp_path):
    """Schema 41 is additive: a request filed before the forum keeps its card and reads the
    new column as nothing, so the old status channel goes on carrying it."""
    path = tmp_path / "old40.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute("ALTER TABLE requests DROP COLUMN thread_id")
    await db.conn.execute(
        "INSERT INTO requests(id, guild_id, user_id, what, why, status, created_at, message_id) "
        "VALUES (1, 7, 9, 'a request forum', 'so it stops scrolling', 'open', "
        "'2026-09-17T00:00:00+00:00', 4242)"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '40')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("PRAGMA table_info(requests)")
        assert "thread_id" in {row["name"] for row in await cur.fetchall()}
        cur = await again.conn.execute(
            "SELECT status, message_id, thread_id FROM requests WHERE id = 1"
        )
        row = await cur.fetchone()
        assert (row["status"], row["message_id"], row["thread_id"]) == ("open", 4242, None)
        cur = await again.conn.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        )
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await again.close()


async def test_a_schema_41_file_gains_requests_source_and_reads_old_rows_as_panel(tmp_path):
    """Schema 42 is additive: a request filed before the forum could adopt a post reads as
    `panel`, which is where every one of them actually came from."""
    path = tmp_path / "old41.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute("ALTER TABLE requests DROP COLUMN source")
    await db.conn.execute(
        "INSERT INTO requests(id, guild_id, user_id, what, why, status, created_at) "
        "VALUES (1, 7, 9, 'a request board', 'the doc is a mess', 'open', "
        "'2026-09-17T00:00:00+00:00')"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '41')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("PRAGMA table_info(requests)")
        assert "source" in {row["name"] for row in await cur.fetchall()}
        cur = await again.conn.execute("SELECT status, source FROM requests WHERE id = 1")
        row = await cur.fetchone()
        assert (row["status"], row["source"]) == ("open", "panel")
        await again.conn.execute(
            "INSERT INTO requests(id, guild_id, user_id, what, why, status, created_at, source) "
            "VALUES (2, 7, 9, 'a post', 'by hand', 'open', '2026-09-17T00:00:00+00:00', 'forum')"
        )
        cur = await again.conn.execute("SELECT source FROM requests WHERE id = 2")
        assert (await cur.fetchone())["source"] == "forum"
        cur = await again.conn.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        )
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await again.close()


async def test_a_schema_42_file_gains_the_three_moved_to_columns_all_empty(tmp_path):
    """42 → 43: the hand-off trail is three additive columns, NULL on every row that predates it.

    `info/send-to-design.md` §A — one cell each on requests, events and modmail_tickets, so a
    thing that has been sent somewhere says where, both ways, without a table of its own."""
    path = tmp_path / "old43.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute(
        "INSERT INTO requests(id, guild_id, user_id, what, why, status, created_at) "
        "VALUES (1, 7, 9, 'a games night', 'nothing to do', 'open', "
        "'2026-09-17T00:00:00+00:00')"
    )
    await db.conn.execute(
        "INSERT INTO events(id, guild_id, requester_id, title, starts_at, status, created_at) "
        "VALUES (1, 7, 9, 'Block Party', '2026-09-18T00:00:00+00:00', 'pending', "
        "'2026-09-17T00:00:00+00:00')"
    )
    await db.conn.execute(
        "INSERT INTO modmail_tickets(id, guild_id, user_id, mode, channel_id, status, opened_at) "
        "VALUES (1, 7, 9, 'channel', 10, 'open', '2026-09-17T00:00:00+00:00')"
    )
    for table in ("requests", "events", "modmail_tickets"):
        await db.conn.execute(f"ALTER TABLE {table} DROP COLUMN moved_to")
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '42')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        for table in ("requests", "events", "modmail_tickets"):
            cur = await again.conn.execute(f"PRAGMA table_info({table})")
            assert "moved_to" in {row["name"] for row in await cur.fetchall()}, table
            cur = await again.conn.execute(f"SELECT moved_to FROM {table} WHERE id = 1")
            assert (await cur.fetchone())["moved_to"] is None, table
        await again.conn.execute("UPDATE requests SET moved_to = 'event:2' WHERE id = 1")
        cur = await again.conn.execute("SELECT moved_to FROM requests WHERE id = 1")
        assert (await cur.fetchone())["moved_to"] == "event:2"
        cur = await again.conn.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        )
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await again.close()


async def test_every_post_that_predates_versions_gets_version_one_and_only_once(tmp_path):
    """48 → 49: the backfill is what stops View meeting an empty list on a post written
    before the table existed, and running it twice must not write a second row."""
    path = tmp_path / "posts49.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute(
        "INSERT INTO posts(id, guild_id, slug, title, channel_id, body, style, pin, "
        "updated_at, updated_by) VALUES "
        "(1, 7, 'welcome', 'Welcome and rules', 500, 'The words.', 'plain', 1, "
        "'2026-09-01T00:00:00+00:00', 42)"
    )
    await db.conn.execute("DELETE FROM post_versions")
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("SELECT * FROM post_versions ORDER BY n")
        rows = [dict(row) for row in await cur.fetchall()]
        assert len(rows) == 1
        one = rows[0]
        assert one["post_id"] == 1 and one["n"] == 1 and one["guild_id"] == 7
        assert one["title"] == "Welcome and rules" and one["body"] == "The words."
        assert one["style"] == "plain" and one["channel_id"] == 500 and one["pin"] == 1
        assert one["because"] == "backfill" and one["via"] == "boot"
        assert one["saved_at"] == "2026-09-01T00:00:00+00:00" and one["saved_by"] == 42
    finally:
        await again.close()

    third = Database(path)
    await third.connect()
    try:
        cur = await third.conn.execute("SELECT COUNT(*) AS n FROM post_versions")
        assert (await cur.fetchone())["n"] == 1, "the backfill is idempotent"
        cur = await third.conn.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        )
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await third.close()


SCHEMA_49_FAN_ROLES = (
    "CREATE TABLE golive_fan_roles (guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, "
    "role_id INTEGER NOT NULL, created_at TEXT NOT NULL, created_by INTEGER, "
    "unworn_since TEXT, PRIMARY KEY (guild_id, user_id))"
)


async def test_a_schema_49_file_lets_a_ping_role_belong_to_a_channel_and_keeps_its_rows(tmp_path):
    """49 → 50: `user_id` was NOT NULL and part of the key, so a spotlight could not hold a
    role at all. The rebuild keeps every member's row and its `unworn_since` stamp."""
    path = tmp_path / "fanroles50.sqlite3"
    old = await aiosqlite.connect(path)
    await old.execute("CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    await old.execute("INSERT INTO schema_meta(key, value) VALUES ('schema_version', '49')")
    await old.execute(SCHEMA_49_FAN_ROLES)
    await old.execute(
        "INSERT INTO golive_fan_roles(guild_id, user_id, role_id, created_at, created_by, "
        "unworn_since) VALUES (7, 900, 5000, '2026-09-01T00:00:00+00:00', 42, "
        "'2026-09-10T00:00:00+00:00')"
    )
    await old.commit()
    await old.close()

    db = Database(path)
    await db.connect()
    try:
        cur = await db.conn.execute("PRAGMA table_info(golive_fan_roles)")
        columns = {row["name"]: row for row in await cur.fetchall()}
        assert "spotlight_id" in columns
        assert not columns["user_id"]["notnull"]

        cur = await db.conn.execute("SELECT * FROM golive_fan_roles")
        rows = [dict(row) for row in await cur.fetchall()]
        assert len(rows) == 1
        assert rows[0]["user_id"] == 900 and rows[0]["role_id"] == 5000
        assert rows[0]["created_by"] == 42 and rows[0]["spotlight_id"] is None
        assert rows[0]["unworn_since"] == "2026-09-10T00:00:00+00:00"

        await db.conn.execute(
            "INSERT INTO golive_fan_roles(guild_id, user_id, role_id, created_at, created_by, "
            "spotlight_id) VALUES (7, NULL, 6000, '2026-09-20T00:00:00+00:00', 42, 1)"
        )
        await db.conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            await db.conn.execute(
                "INSERT INTO golive_fan_roles(guild_id, user_id, role_id, created_at, "
                "created_by, spotlight_id) VALUES (7, NULL, 6001, "
                "'2026-09-20T00:00:00+00:00', 42, 1)"
            )
        await db.conn.rollback()
        with pytest.raises(sqlite3.IntegrityError):
            await db.conn.execute(
                "INSERT INTO golive_fan_roles(guild_id, user_id, role_id, created_at, "
                "created_by) VALUES (7, 900, 6002, '2026-09-20T00:00:00+00:00', 42)"
            )
        await db.conn.rollback()

        cur = await db.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("SELECT COUNT(*) AS n FROM golive_fan_roles")
        assert (await cur.fetchone())["n"] == 2, "the rebuild is not run a second time"
        cur = await again.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'golive_fan%'"
        )
        assert {row["name"] for row in await cur.fetchall()} == {"golive_fan_roles"}
    finally:
        await again.close()


SCHEMA_50_RAID_TRAINS = (
    "CREATE TABLE raid_trains (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, "
    "organizer_id INTEGER NOT NULL, title TEXT NOT NULL, description TEXT, "
    "starts_at TEXT NOT NULL, slot_minutes INTEGER NOT NULL, slot_count INTEGER NOT NULL, "
    "status TEXT NOT NULL DEFAULT 'open', channel_id INTEGER, lineup_message_id INTEGER, "
    "thread_id INTEGER, scheduled_event_id INTEGER, cancel_reason TEXT, "
    "created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
)


async def test_a_schema_50_file_gains_the_trains_event_column_and_keeps_its_rows(tmp_path):
    """50 -> 51: a train made before the link reads back with `event_id` NULL, not missing."""
    path = tmp_path / "trains51.sqlite3"
    old = await aiosqlite.connect(path)
    await old.execute("CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    await old.execute("INSERT INTO schema_meta(key, value) VALUES ('schema_version', '50')")
    await old.execute(SCHEMA_50_RAID_TRAINS)
    await old.execute(
        "INSERT INTO raid_trains(guild_id, organizer_id, title, starts_at, slot_minutes, "
        "slot_count, status, created_at, updated_at) VALUES (7, 42, 'Saturday', "
        "'2026-10-01T18:00:00+00:00', 60, 4, 'open', '2026-09-01T00:00:00+00:00', "
        "'2026-09-01T00:00:00+00:00')"
    )
    await old.commit()
    await old.close()

    db = Database(path)
    await db.connect()
    try:
        cur = await db.conn.execute("PRAGMA table_info(raid_trains)")
        assert "event_id" in {row["name"] for row in await cur.fetchall()}
        cur = await db.conn.execute("SELECT * FROM raid_trains")
        rows = [dict(row) for row in await cur.fetchall()]
        assert len(rows) == 1
        assert rows[0]["title"] == "Saturday" and rows[0]["event_id"] is None
        cur = await db.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await db.close()


async def test_a_spotlight_row_gains_its_starts_at_column_on_an_older_file(tmp_path):
    """52 → 53: the owner's date range. A row written before it keeps a NULL start, which
    everywhere means *started already*, so nothing on an existing list goes quiet."""
    path = tmp_path / "old.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute("ALTER TABLE spotlight_channels DROP COLUMN starts_at")
    await db.conn.execute(
        "INSERT INTO spotlight_channels(id, guild_id, twitch_login, added_at, pin) "
        "VALUES (1, 7, 'gamesdonequick', '2026-09-20T00:00:00+00:00', 1)"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("PRAGMA table_info(spotlight_channels)")
        assert "starts_at" in {row["name"] for row in await cur.fetchall()}
        cur = await again.conn.execute("SELECT starts_at FROM spotlight_channels WHERE id = 1")
        assert (await cur.fetchone())["starts_at"] is None
        cur = await again.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await again.close()


async def test_a_schema_53_file_gains_the_channel_notes_table_and_keeps_its_rows(tmp_path):
    """53 → 54 is additive: an older file keeps its rows and gains an empty notes table."""
    path = tmp_path / "old53.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute("DROP TABLE channel_notes")
    await db.conn.execute(
        "INSERT INTO spotlight_channels(id, guild_id, twitch_login, added_at, pin) "
        "VALUES (1, 7, 'gamesdonequick', '2026-09-20T00:00:00+00:00', 1)"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '53')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("PRAGMA table_info(channel_notes)")
        assert {r["name"] for r in await cur.fetchall()} == {
            "guild_id",
            "channel_id",
            "note",
            "set_by",
            "set_at",
        }
        cur = await again.conn.execute("SELECT COUNT(*) AS n FROM channel_notes")
        assert (await cur.fetchone())["n"] == 0
        cur = await again.conn.execute("SELECT twitch_login FROM spotlight_channels WHERE id = 1")
        assert (await cur.fetchone())["twitch_login"] == "gamesdonequick"
        cur = await again.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
        await again.conn.execute(
            "INSERT INTO channel_notes(guild_id, channel_id, note, set_at) VALUES (7, 1, 'a', 'x')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            await again.conn.execute(
                "INSERT INTO channel_notes(guild_id, channel_id, note, set_at) "
                "VALUES (7, 1, 'b', 'y')"
            )
    finally:
        await again.close()


async def test_a_schema_54_file_gains_the_channel_drafts_table_and_keeps_its_notes(tmp_path):
    """54 → 56 is additive: an older file keeps its notes and gains an empty drafts table."""
    path = tmp_path / "old54.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute("DROP TABLE channel_drafts")
    await db.conn.execute(
        "INSERT INTO channel_notes(guild_id, channel_id, note, set_at) VALUES (7, 1, 'a', 'x')"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '54')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("PRAGMA table_info(channel_drafts)")
        assert {r["name"] for r in await cur.fetchall()} == {
            "guild_id",
            "channel_id",
            "draft",
            "status",
            "decided_by",
            "decided_at",
        }
        cur = await again.conn.execute("SELECT COUNT(*) AS n FROM channel_drafts")
        assert (await cur.fetchone())["n"] == 0
        cur = await again.conn.execute("SELECT note FROM channel_notes WHERE channel_id = 1")
        assert (await cur.fetchone())["note"] == "a"
        cur = await again.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
        await again.conn.execute(
            "INSERT INTO channel_drafts(guild_id, channel_id, draft) VALUES (7, 1, 'd')"
        )
        cur = await again.conn.execute("SELECT status FROM channel_drafts WHERE channel_id = 1")
        assert (await cur.fetchone())["status"] == "draft"
        with pytest.raises(sqlite3.IntegrityError):
            await again.conn.execute(
                "INSERT INTO channel_drafts(guild_id, channel_id, draft) VALUES (7, 1, 'e')"
            )
    finally:
        await again.close()


async def test_a_schema_56_file_gains_the_channel_reach_table_and_keeps_its_drafts(tmp_path):
    """56 → 57 is additive: an older file keeps its drafts and gains an empty reach table."""
    path = tmp_path / "old56.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute("DROP TABLE channel_reach")
    await db.conn.execute(
        "INSERT INTO channel_drafts(guild_id, channel_id, draft) VALUES (7, 1, 'kept')"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '56')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("PRAGMA table_info(channel_reach)")
        assert {r["name"] for r in await cur.fetchall()} == {
            "guild_id",
            "channel_id",
            "shown",
            "set_by",
            "set_at",
        }
        cur = await again.conn.execute("SELECT COUNT(*) AS n FROM channel_reach")
        assert (await cur.fetchone())["n"] == 0
        cur = await again.conn.execute("SELECT draft FROM channel_drafts WHERE channel_id = 1")
        assert (await cur.fetchone())["draft"] == "kept"
        cur = await again.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
        await again.conn.execute(
            "INSERT INTO channel_reach(guild_id, channel_id, shown, set_at) VALUES (7, 1, 1, 'x')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            await again.conn.execute(
                "INSERT INTO channel_reach(guild_id, channel_id, shown, set_at) "
                "VALUES (7, 1, 0, 'y')"
            )
        with pytest.raises(sqlite3.IntegrityError):
            await again.conn.execute(
                "INSERT INTO channel_reach(guild_id, channel_id, set_at) VALUES (7, 2, 'z')"
            )
    finally:
        await again.close()


async def test_a_schema_57_file_gains_the_chat_review_table_and_keeps_its_rows(tmp_path):
    """57 → 58 is additive: an older file keeps its reach rows and gains an empty review queue."""
    path = tmp_path / "old57.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute("DROP TABLE chat_review")
    await db.conn.execute(
        "INSERT INTO channel_reach(guild_id, channel_id, shown, set_at) VALUES (7, 1, 1, 'x')"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '57')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("PRAGMA table_info(chat_review)")
        assert {
            "guild_id",
            "asked",
            "answered",
            "reason",
            "reply_id",
            "suggested_intent_id",
            "suggested_kind",
            "suggested_line",
            "status",
            "decided_by",
            "decided_at",
        } <= {r["name"] for r in await cur.fetchall()}
        cur = await again.conn.execute("SELECT COUNT(*) AS n FROM chat_review")
        assert (await cur.fetchone())["n"] == 0
        cur = await again.conn.execute("SELECT shown FROM channel_reach WHERE channel_id = 1")
        assert (await cur.fetchone())["shown"] == 1
        cur = await again.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
        row = (
            "INSERT INTO chat_review(guild_id, channel_id, user_id, asked, answered, reason, "
            "reply_id, at, status) VALUES (7, 1, 2, 'q', 'a', 'reask', ?, 'x', ?)"
        )
        await again.conn.execute(row, (10, "open"))
        with pytest.raises(sqlite3.IntegrityError):
            await again.conn.execute(row, (10, "open"))
        with pytest.raises(sqlite3.IntegrityError):
            await again.conn.execute(row, (11, "maybe"))
    finally:
        await again.close()


async def test_a_schema_54_file_gains_chat_voice_and_three_columns_and_keeps_its_rows(tmp_path):
    """54 → 55 (56 once channels-page merged) is additive: the tone table, the ledger's trope,
    a staff-written body."""
    path = tmp_path / "old54.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute("DROP TABLE chat_voice")
    await db.conn.execute("DROP TABLE llm_ledger")
    await db.conn.execute(
        "CREATE TABLE llm_ledger (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, "
        "guild_id INTEGER, user_id INTEGER, turn TEXT NOT NULL, provider TEXT NOT NULL, "
        "model TEXT NOT NULL, tier TEXT NOT NULL, outcome TEXT NOT NULL DEFAULT 'ok', "
        "input_tokens INTEGER NOT NULL DEFAULT 0, output_tokens INTEGER NOT NULL DEFAULT 0, "
        "cache_read_tokens INTEGER NOT NULL DEFAULT 0, cache_write_tokens INTEGER NOT NULL "
        "DEFAULT 0, cost_microdollars INTEGER NOT NULL DEFAULT 0)"
    )
    await db.conn.execute(
        "INSERT INTO llm_ledger(at, turn, provider, model, tier) VALUES ('x', 't', 'p', 'm', 's')"
    )
    await db.conn.execute("DROP TABLE personality_tropes")
    await db.conn.execute(
        "CREATE TABLE personality_tropes (name TEXT PRIMARY KEY, label TEXT NOT NULL, voice TEXT "
        "NOT NULL, neighbours TEXT NOT NULL DEFAULT '[]', enabled INTEGER NOT NULL DEFAULT 1, "
        "sort INTEGER NOT NULL DEFAULT 0, source TEXT NOT NULL DEFAULT 'gabi', updated_at TEXT "
        "NOT NULL, updated_by INTEGER)"
    )
    await db.conn.execute(
        "INSERT INTO personality_tropes(name, label, voice, updated_at) "
        "VALUES ('noir', 'noir', 'old', 'x')"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '54')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("PRAGMA table_info(chat_voice)")
        assert {r["name"] for r in await cur.fetchall()} == {
            "guild_id",
            "user_id",
            "trope",
            "turns",
            "since",
            "pinned",
            "pinned_by",
            "pinned_at",
        }
        cur = await again.conn.execute("SELECT trope, turn FROM llm_ledger")
        row = await cur.fetchone()
        assert row["turn"] == "t" and row["trope"] is None
        cur = await again.conn.execute(
            "SELECT voice, voice_edited_by, voice_edited_at FROM personality_tropes"
        )
        row = await cur.fetchone()
        assert row["voice"] == "old" and row["voice_edited_at"] is None
        cur = await again.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
        await again.conn.execute("INSERT INTO chat_voice(guild_id, user_id) VALUES (7, 1)")
        with pytest.raises(sqlite3.IntegrityError):
            await again.conn.execute("INSERT INTO chat_voice(guild_id, user_id) VALUES (7, 1)")
    finally:
        await again.close()


async def test_a_schema_58_file_gains_ping_mode_windows_and_the_session_gate(tmp_path):
    """58 → 59: a row written before keeps pinging always, and its open session has no
    remembered gate answer yet, so the boot reconcile writes one without posting."""
    path = tmp_path / "old58.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute("DROP TABLE spotlight_ping_windows")
    await db.conn.execute("ALTER TABLE spotlight_channels DROP COLUMN ping_mode")
    await db.conn.execute("ALTER TABLE spotlight_sessions DROP COLUMN pinging_last")
    await db.conn.execute(
        "INSERT INTO spotlight_channels(id, guild_id, twitch_login, added_at, pin) "
        "VALUES (1, 7, 'gamesdonequick', '2026-09-20T00:00:00+00:00', 1)"
    )
    await db.conn.execute(
        "INSERT INTO spotlight_sessions(id, guild_id, spotlight_id, started_at, mode) "
        "VALUES (1, 7, 1, '2026-09-24T00:00:00+00:00', 'on')"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '58')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("SELECT ping_mode FROM spotlight_channels WHERE id = 1")
        assert (await cur.fetchone())["ping_mode"] == "always"
        cur = await again.conn.execute("SELECT pinging_last FROM spotlight_sessions WHERE id = 1")
        assert (await cur.fetchone())["pinging_last"] is None
        cur = await again.conn.execute("PRAGMA table_info(spotlight_ping_windows)")
        assert {r["name"] for r in await cur.fetchall()} == {
            "id",
            "guild_id",
            "spotlight_id",
            "starts_at",
            "ends_at",
            "note",
            "source",
            "source_id",
            "added_by",
            "added_at",
        }
        cur = await again.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name='spotlight_ping_windows_by_channel'"
        )
        assert await cur.fetchone() is not None
        cur = await again.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await again.close()


async def test_a_schema_59_file_gains_the_three_marathon_tables_and_keeps_its_windows(tmp_path):
    """59 → 60 is additive: the marathon tables arrive through the bootstrap and a ping window
    written before is untouched."""
    path = tmp_path / "old59.sqlite3"
    db = Database(path)
    await db.connect()
    for table in ("marathon_people", "marathon_runs", "marathons"):
        await db.conn.execute(f"DROP TABLE {table}")
    await db.conn.execute(
        "INSERT INTO spotlight_ping_windows(guild_id, spotlight_id, starts_at, ends_at, added_at) "
        "VALUES (7, 3, '2027-01-04T00:00:00+00:00', '2027-01-11T00:00:00+00:00', "
        "'2026-09-25T00:00:00+00:00')"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '59')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'marathon%'"
        )
        assert {r["name"] for r in await cur.fetchall()} >= {
            "marathons",
            "marathon_runs",
            "marathon_people",
        }
        cur = await again.conn.execute("PRAGMA table_info(marathon_runs)")
        assert {"external_id", "people", "reminders_sent", "shout_message_id", "live_because"} <= {
            r["name"] for r in await cur.fetchall()
        }
        cur = await again.conn.execute("SELECT COUNT(*) AS n FROM spotlight_ping_windows")
        assert (await cur.fetchone())["n"] == 1
        cur = await again.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await again.close()


async def test_a_run_is_unique_per_marathon_and_an_everywhere_pairing_is_unique_per_name(tmp_path):
    """The diff leans on (marathon_id, external_id); a NULL marathon_id pairing is still one per
    name, which the three-column UNIQUE alone would not give (NULLs are distinct in SQLite)."""
    db = Database(tmp_path / "t.sqlite3")
    await db.connect()
    try:
        insert_run = (
            "INSERT INTO marathon_runs(marathon_id, external_id, game, first_seen_at, "
            "last_seen_at) "
            "VALUES (1, '42', 'Blaster Master', 'x', 'x')"
        )
        await db.conn.execute(insert_run)
        with pytest.raises(sqlite3.IntegrityError):
            await db.conn.execute(insert_run)
        pair = (
            "INSERT INTO marathon_people(guild_id, marathon_id, runner_name, user_id, added_at) "
            "VALUES (7, NULL, 'kungfufruitcup', 9, 'x')"
        )
        await db.conn.execute(pair)
        with pytest.raises(sqlite3.IntegrityError):
            await db.conn.execute(pair)
    finally:
        await db.close()


async def test_schema_61_adds_the_next_event_suggestion_to_a_marathon_and_keeps_its_rows(tmp_path):
    path = tmp_path / "t.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute("ALTER TABLE marathons DROP COLUMN suggested_next")
    await db.conn.execute(
        "INSERT INTO marathons(guild_id, name, schedule_url, source, source_ref, added_at) "
        "VALUES (7, 'Halo Fest', 'https://gamesdonequick.com/schedule/73', 'gdq', '73', 'x')"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '60')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("SELECT name, suggested_next FROM marathons")
        row = await cur.fetchone()
        assert row["name"] == "Halo Fest" and row["suggested_next"] is None
        cur = await again.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await again.close()


async def test_schema_62_links_a_marathon_to_its_event_and_keeps_its_rows(tmp_path):
    path = tmp_path / "t.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute("ALTER TABLE marathons DROP COLUMN event_id")
    await db.conn.execute("ALTER TABLE marathons DROP COLUMN event_wanted")
    await db.conn.execute(
        "INSERT INTO marathons(guild_id, name, schedule_url, source, source_ref, added_at) "
        "VALUES (7, 'AGDQ 2027', 'https://gamesdonequick.com/schedule/74', 'gdq', '74', 'x')"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '61')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("SELECT name, event_id, event_wanted FROM marathons")
        row = await cur.fetchone()
        assert row["name"] == "AGDQ 2027"
        assert row["event_id"] is None and row["event_wanted"] == 0
        cur = await again.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await again.close()


async def test_schema_63_adds_the_feeds_and_a_marathons_feed_and_keeps_its_rows(tmp_path):
    path = tmp_path / "t.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute("DROP TABLE marathon_feeds")
    await db.conn.execute("DROP TABLE marathon_feed_seeds")
    await db.conn.execute("ALTER TABLE marathons DROP COLUMN feed_id")
    await db.conn.execute(
        "INSERT INTO marathons(guild_id, name, schedule_url, source, source_ref, added_at) "
        "VALUES (7, 'AGDQ 2027', 'https://gamesdonequick.com/schedule/74', 'gdq', '74', 'x')"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '62')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("SELECT name, feed_id FROM marathons")
        row = await cur.fetchone()
        assert row["name"] == "AGDQ 2027" and row["feed_id"] is None
        cur = await again.conn.execute("PRAGMA table_info(marathon_feeds)")
        assert {"source", "feed_ref", "spotlight_id", "action", "suggested", "ignored"} <= {
            r["name"] for r in await cur.fetchall()
        }
        cur = await again.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await again.close()


async def test_a_feed_needs_a_channel_and_a_channel_has_one_feed(tmp_path):
    db = Database(tmp_path / "t.sqlite3")
    await db.connect()
    try:
        insert = (
            "INSERT INTO marathon_feeds(guild_id, source, feed_ref, spotlight_id, name, added_at) "
            "VALUES (7, ?, ?, ?, 'GDQ', 'x')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            await db.conn.execute(insert, ("tracker", "https://a", None))
        await db.conn.execute(insert, ("tracker", "https://a", 3))
        with pytest.raises(sqlite3.IntegrityError):
            await db.conn.execute(insert, ("horaro", "esa", 3))
        with pytest.raises(sqlite3.IntegrityError):
            await db.conn.execute(insert, ("tracker", "https://a", 4))
    finally:
        await db.close()


async def test_schema_64_adds_the_event_modes_and_the_channel_opt_out_and_carries_the_wish(
    tmp_path,
):
    path = tmp_path / "t.sqlite3"
    db = Database(path)
    await db.connect()
    for table, column in (
        ("marathons", "event_mode"),
        ("marathons", "held_by_channel"),
        ("marathon_runs", "event_id"),
        ("marathon_feeds", "event_mode"),
        ("marathon_feeds", "held_by_channel"),
        ("spotlight_channels", "marathons"),
    ):
        await db.conn.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
    insert = (
        "INSERT INTO marathons(guild_id, name, schedule_url, source, source_ref, event_id, "
        "event_wanted, added_at) VALUES (7, ?, ?, 'gdq', ?, ?, ?, 'x')"
    )
    await db.conn.execute(insert, ("Linked", "https://g/1", "1", 5, 0))
    await db.conn.execute(insert, ("Waiting", "https://g/2", "2", None, 1))
    await db.conn.execute(insert, ("Bare", "https://g/3", "3", None, 0))
    await db.conn.execute(
        "INSERT INTO spotlight_channels(guild_id, twitch_login, added_at) VALUES (7, 'esa', 'x')"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '63')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("SELECT name, event_mode, held_by_channel FROM marathons")
        modes = {row["name"]: row["event_mode"] for row in await cur.fetchall()}
        assert modes == {"Linked": "marathon", "Waiting": "marathon", "Bare": "none"}
        cur = await again.conn.execute("SELECT marathons FROM spotlight_channels")
        assert (await cur.fetchone())["marathons"] == 1
        cur = await again.conn.execute("PRAGMA table_info(marathon_runs)")
        assert "event_id" in {r["name"] for r in await cur.fetchall()}
        cur = await again.conn.execute("PRAGMA table_info(marathon_feeds)")
        assert {"event_mode", "held_by_channel"} <= {r["name"] for r in await cur.fetchall()}
        await again.conn.execute("UPDATE marathons SET event_mode = 'none'")
        await again.conn.commit()
    finally:
        await again.close()

    third = Database(path)
    await third.connect()
    try:
        cur = await third.conn.execute("SELECT DISTINCT event_mode FROM marathons")
        assert [row["event_mode"] for row in await cur.fetchall()] == ["none"]
    finally:
        await third.close()


async def test_schema_65_adds_the_marathon_spotlights_and_keeps_its_rows(tmp_path):
    """64 → 65 is additive: the small table a marathon remembers its spotlit runners in."""
    path = tmp_path / "old64.sqlite3"
    db = Database(path)
    await db.connect()
    await db.conn.execute("DROP TABLE marathon_spotlights")
    await db.conn.execute(
        "INSERT INTO marathons(guild_id, name, schedule_url, source, source_ref, added_at) "
        "VALUES (7, 'AGDQ 2027', 'https://gamesdonequick.com/schedule/74', 'gdq', '74', "
        "'2026-09-25T00:00:00+00:00')"
    )
    await db.conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '64')"
    )
    await db.conn.commit()
    await db.close()

    again = Database(path)
    await again.connect()
    try:
        cur = await again.conn.execute("PRAGMA table_info(marathon_spotlights)")
        assert {"marathon_id", "login", "spotlight_id", "run_id", "added_at"} <= {
            r["name"] for r in await cur.fetchall()
        }
        cur = await again.conn.execute("SELECT COUNT(*) AS n FROM marathons")
        assert (await cur.fetchone())["n"] == 1
        await again.conn.execute(
            "INSERT INTO marathon_spotlights(marathon_id, login, spotlight_id, added_at) "
            "VALUES (1, 'caseyfast', 3, '2026-09-25T00:00:00+00:00')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            await again.conn.execute(
                "INSERT INTO marathon_spotlights(marathon_id, login, spotlight_id, added_at) "
                "VALUES (1, 'caseyfast', 4, '2026-09-25T00:00:00+00:00')"
            )
        cur = await again.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'")
        assert (await cur.fetchone())["value"] == str(SCHEMA_VERSION)
    finally:
        await again.close()
