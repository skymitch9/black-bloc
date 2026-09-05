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
        assert SCHEMA_VERSION == 31
        cur = await db.conn.execute("PRAGMA table_info(requests)")
        assert {
            "built",
            "how_to_test",
            "ready_by",
            "sent_back_reason",
            "check_asked_by",
            "check_asked_at",
        } <= {r["name"] for r in await cur.fetchall()}
        cur = await db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {r["name"] for r in await cur.fetchall()}
        assert {"settings", "action_log", "role_menus", "role_menu_options"} <= tables
        assert {"role_requests", "role_grants"} <= tables
        assert {"application_forms", "application_questions", "applications"} <= tables
        assert {"golive_links", "golive_optout", "golive_sessions"} <= tables
        assert "golive_fan_roles" in tables
        cur = await db.conn.execute("PRAGMA table_info(golive_fan_roles)")
        columns = {r["name"] for r in await cur.fetchall()}
        assert {"guild_id", "user_id", "role_id", "created_at", "created_by"} == columns
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
        assert {"card_message_id", "practice"} <= columns
        cur = await db.conn.execute("SELECT * FROM modmail_tickets WHERE id = 1")
        row = await cur.fetchone()
        assert row["card_message_id"] is None
        assert row["practice"] == 0
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
        assert (await cur.fetchone())["value"] == "31"
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
