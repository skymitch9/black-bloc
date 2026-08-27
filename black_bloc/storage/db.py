from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

log = logging.getLogger(__name__)

SCHEMA_VERSION = 6

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
    panel_message_id INTEGER
);

CREATE TABLE IF NOT EXISTS tempvoice_prefs (
    user_id    INTEGER PRIMARY KEY,
    name       TEXT,
    user_limit INTEGER,
    locked     INTEGER DEFAULT 0,
    hidden     INTEGER DEFAULT 0
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
"""

ADDED_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("golive_sessions", "live_role_added", "INTEGER NOT NULL DEFAULT 0"),
    ("birthdays", "role_added_id", "INTEGER"),
)

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
        await self._conn.executescript(SCHEMA)
        await self._add_missing_columns()
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
