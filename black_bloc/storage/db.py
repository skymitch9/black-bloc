from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

log = logging.getLogger(__name__)

SCHEMA_VERSION = 12

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    guild_id   INTEGER NOT NULL,
    key        TEXT    NOT NULL,
    value      TEXT    NOT NULL,
    updated_by INTEGER,
    updated_at TEXT    NOT NULL,
    PRIMARY KEY (guild_id, key)
);

CREATE TABLE IF NOT EXISTS action_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL,
    at         TEXT    NOT NULL,
    kind       TEXT    NOT NULL,
    actor_id   INTEGER,
    target_id  INTEGER,
    reason     TEXT,
    details    TEXT
);

CREATE TABLE IF NOT EXISTS role_menus (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    name        TEXT    NOT NULL,
    title       TEXT    NOT NULL,
    description TEXT,
    mode        TEXT    NOT NULL DEFAULT 'multiple',
    message_id  INTEGER,
    channel_id  INTEGER,
    UNIQUE (guild_id, name)
);

CREATE TABLE IF NOT EXISTS role_menu_options (
    menu_id  INTEGER NOT NULL REFERENCES role_menus(id) ON DELETE CASCADE,
    role_id  INTEGER NOT NULL,
    label    TEXT    NOT NULL,
    emoji    TEXT,
    position INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (menu_id, role_id)
);

CREATE TABLE IF NOT EXISTS golive_links (
    user_id        INTEGER PRIMARY KEY,
    twitch_login   TEXT    NOT NULL,
    twitch_user_id TEXT,
    linked_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS golive_optout (
    user_id INTEGER PRIMARY KEY,
    at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS golive_sessions (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id              INTEGER NOT NULL,
    user_id               INTEGER NOT NULL,
    source                TEXT    NOT NULL,
    url                   TEXT,
    game                  TEXT,
    title                 TEXT,
    platform              TEXT,
    started_at            TEXT    NOT NULL,
    ended_at              TEXT,
    announced_message_id  INTEGER,
    mode                  TEXT    NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS golive_open_session
    ON golive_sessions(guild_id, user_id) WHERE ended_at IS NULL;

CREATE TABLE IF NOT EXISTS tempvoice_channels (
    channel_id       INTEGER PRIMARY KEY,
    guild_id         INTEGER NOT NULL,
    owner_id         INTEGER NOT NULL,
    creator_id       INTEGER NOT NULL,
    created_at       TEXT    NOT NULL,
    panel_message_id INTEGER,
    panel_channel_id INTEGER
);

CREATE TABLE IF NOT EXISTS tempvoice_prefs (
    user_id       INTEGER PRIMARY KEY,
    name          TEXT,
    user_limit    INTEGER,
    locked        INTEGER DEFAULT 0,
    hidden        INTEGER DEFAULT 0,
    bitrate       INTEGER,
    region        TEXT,
    permitted_ids TEXT,
    banned_ids    TEXT
);

CREATE TABLE IF NOT EXISTS honeypot_hits (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    message_id INTEGER,
    content    TEXT,
    at         TEXT    NOT NULL,
    mode       TEXT    NOT NULL,
    action     TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS user_timezones (
    user_id INTEGER PRIMARY KEY,
    tz      TEXT NOT NULL,
    set_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id           INTEGER NOT NULL,
    requester_id       INTEGER NOT NULL,
    title              TEXT    NOT NULL,
    description        TEXT,
    location           TEXT,
    starts_at          TEXT    NOT NULL,
    ends_at            TEXT,
    status             TEXT    NOT NULL DEFAULT 'pending',
    review_channel_id  INTEGER,
    review_message_id  INTEGER,
    scheduled_event_id INTEGER,
    announce_message_id INTEGER,
    decided_by         INTEGER,
    decided_at         TEXT,
    deny_reason        TEXT,
    created_at         TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS events_by_status ON events(guild_id, status, starts_at);

CREATE TABLE IF NOT EXISTS birthdays (
    user_id           INTEGER PRIMARY KEY,
    guild_id          INTEGER NOT NULL,
    month             INTEGER NOT NULL,
    day               INTEGER NOT NULL,
    year              INTEGER,
    opted_in          INTEGER NOT NULL DEFAULT 1,
    source            TEXT    NOT NULL,
    set_at            TEXT    NOT NULL,
    last_announced_on TEXT,
    role_added        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS modmail_tickets (
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
);

CREATE UNIQUE INDEX IF NOT EXISTS modmail_open_ticket
    ON modmail_tickets(guild_id, user_id) WHERE status = 'open';

CREATE TABLE IF NOT EXISTS modmail_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id   INTEGER NOT NULL REFERENCES modmail_tickets(id),
    at          TEXT    NOT NULL,
    author_id   INTEGER NOT NULL,
    direction   TEXT    NOT NULL,
    anonymous   INTEGER NOT NULL DEFAULT 0,
    content     TEXT,
    attachments TEXT
);

CREATE INDEX IF NOT EXISTS modmail_messages_by_ticket ON modmail_messages(ticket_id, id);

CREATE TABLE IF NOT EXISTS modmail_blocks (
    user_id INTEGER PRIMARY KEY,
    by      INTEGER,
    reason  TEXT,
    at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS modmail_snippets (
    name    TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    by      INTEGER,
    at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mod_cases (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id       INTEGER NOT NULL,
    user_id        INTEGER,
    kind           TEXT    NOT NULL,
    moderator_id   INTEGER,
    reason         TEXT,
    duration_s     INTEGER,
    at             TEXT    NOT NULL,
    mode           TEXT    NOT NULL,
    applied        INTEGER NOT NULL,
    log_message_id INTEGER
);

CREATE INDEX IF NOT EXISTS mod_cases_by_user ON mod_cases(guild_id, user_id, id);
CREATE INDEX IF NOT EXISTS mod_cases_by_kind ON mod_cases(guild_id, kind, at);
"""

ADDED_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("golive_sessions", "live_role_added", "INTEGER NOT NULL DEFAULT 0"),
    ("golive_sessions", "platform", "TEXT"),
    ("events", "card_channel_id", "INTEGER"),
    ("birthdays", "role_added_id", "INTEGER"),
    ("modmail_messages", "delivered", "INTEGER NOT NULL DEFAULT 1"),
    ("mod_cases", "actions", "TEXT"),
    ("mod_cases", "done", "TEXT"),
    ("mod_cases", "failed", "TEXT"),
    ("mod_cases", "message_id", "INTEGER"),
    ("mod_cases", "channel_id", "INTEGER"),
    ("tempvoice_channels", "panel_channel_id", "INTEGER"),
    ("tempvoice_prefs", "bitrate", "INTEGER"),
    ("tempvoice_prefs", "region", "TEXT"),
    ("tempvoice_prefs", "permitted_ids", "TEXT"),
    ("tempvoice_prefs", "banned_ids", "TEXT"),
)

MOD_CASES_CARRIED_OVER = (
    "id, guild_id, user_id, kind, moderator_id, reason, duration_s, at, mode, applied, "
    "log_message_id"
)
MOD_CASES_OLD = "mod_cases_before_null_user"

CLOSE_DUPLICATE_OPEN_SESSIONS = """
UPDATE golive_sessions SET ended_at = ?
WHERE ended_at IS NULL AND id NOT IN (
    SELECT MAX(id) FROM golive_sessions WHERE ended_at IS NULL GROUP BY guild_id, user_id
)
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._conn: aiosqlite.Connection | None = None

    @property
    def is_connected(self) -> bool:
        return self._conn is not None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database.connect() has not been called")
        return self._conn

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._close_duplicate_open_sessions()
        await self._set_aside_mod_cases_with_a_required_user()
        await self._conn.executescript(SCHEMA)
        await self._add_missing_columns()
        await self._restore_set_aside_mod_cases()
        await self._conn.execute(
            "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        await self._conn.commit()

    async def _table_columns(self, table: str) -> set[str]:
        cur = await self.conn.execute(f"PRAGMA table_info({table})")
        return {str(row["name"]) for row in await cur.fetchall()}

    async def _close_duplicate_open_sessions(self) -> None:
        if not await self._table_columns("golive_sessions"):
            return
        cur = await self.conn.execute(
            CLOSE_DUPLICATE_OPEN_SESSIONS, (datetime.now(UTC).isoformat(),)
        )
        if cur.rowcount and cur.rowcount > 0:
            log.warning(
                "database: closed %d duplicate open go-live session(s) before indexing them",
                cur.rowcount,
            )

    async def _set_aside_mod_cases_with_a_required_user(self) -> None:
        cur = await self.conn.execute("PRAGMA table_info(mod_cases)")
        rows = await cur.fetchall()
        if not any(row["name"] == "user_id" and row["notnull"] for row in rows):
            return
        await self.conn.execute("DROP INDEX IF EXISTS mod_cases_by_user")
        await self.conn.execute("DROP INDEX IF EXISTS mod_cases_by_kind")
        await self.conn.execute(f"ALTER TABLE mod_cases RENAME TO {MOD_CASES_OLD}")
        log.warning("database: rebuilding mod_cases so a case may belong to a channel")

    async def _restore_set_aside_mod_cases(self) -> None:
        if not await self._table_columns(MOD_CASES_OLD):
            return
        await self.conn.execute(
            f"INSERT INTO mod_cases({MOD_CASES_CARRIED_OVER}) "
            f"SELECT {MOD_CASES_CARRIED_OVER} FROM {MOD_CASES_OLD}"
        )
        await self.conn.execute(f"DROP TABLE {MOD_CASES_OLD}")

    async def _add_missing_columns(self) -> None:
        for table, column, declaration in ADDED_COLUMNS:
            present = await self._table_columns(table)
            if present and column not in present:
                await self.conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {declaration}"
                )
                log.info("database: added %s.%s", table, column)

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
