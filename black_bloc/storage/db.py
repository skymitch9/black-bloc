from __future__ import annotations

from pathlib import Path

import aiosqlite

SCHEMA_VERSION = 2

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
        await self._conn.executescript(SCHEMA)
        await self._conn.execute(
            "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
