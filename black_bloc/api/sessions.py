from __future__ import annotations

import logging
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from ..golive import now_iso, parse_ts

log = logging.getLogger(__name__)

CACHE_ATTR = "_api_session_cache"
CACHE_TTL_SECONDS = 30.0
CACHE_MAX_KEYS = 4096
ID_BYTES = 24

NO_DATABASE = "auth: the database is unreachable, so this sign-in cannot be revoked later"


class SessionCache:
    """Verdicts about session ids, kept CACHE_TTL_SECONDS; a logout writes False at once."""

    def __init__(self, ttl: float = CACHE_TTL_SECONDS, limit: int = CACHE_MAX_KEYS) -> None:
        self.ttl = ttl
        self.limit = limit
        self._seen: dict[str, tuple[bool, float]] = {}

    def get(self, sid: str, *, now: float | None = None) -> bool | None:
        found = self._seen.get(sid)
        if found is None:
            return None
        live, until = found
        if (time.monotonic() if now is None else now) >= until:
            del self._seen[sid]
            return None
        return live

    def put(self, sid: str, live: bool, *, now: float | None = None) -> None:
        at = time.monotonic() if now is None else now
        self._seen.pop(sid, None)
        self._seen[sid] = (live, at + self.ttl)
        while len(self._seen) > self.limit:
            del self._seen[next(iter(self._seen))]

    def forget(self, sid: str) -> None:
        self._seen.pop(sid, None)


def cache_for(bot: Any) -> SessionCache:
    """One cache per bot, so a logout is seen by the very next request in this process."""
    found = getattr(bot, CACHE_ATTR, None)
    if found is None:
        found = SessionCache()
        setattr(bot, CACHE_ATTR, found)
    return found


def database_of(bot: Any) -> Any:
    db = getattr(bot, "db", None)
    return db if db is not None and db.is_connected else None


def new_id() -> str:
    return secrets.token_urlsafe(ID_BYTES)


def expiry_iso(ttl: int, *, now: datetime | None = None) -> str:
    return ((now or datetime.now(UTC)) + timedelta(seconds=int(ttl))).isoformat()


def is_past(value: Any, *, now: datetime | None = None) -> bool:
    """An unreadable stamp counts as past — a session nobody can date is not a live one."""
    when = parse_ts(value)
    if when is None:
        return True
    return (now or datetime.now(UTC)) >= when


async def start(bot: Any, user_id: int, *, ttl: int) -> str:
    """The row a sign-in writes; its id travels in the signed cookie."""
    sid = new_id()
    db = database_of(bot)
    if db is None:
        log.warning(NO_DATABASE)
        return sid
    await db.conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now_iso(),))
    await db.conn.execute(
        "INSERT INTO sessions(id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (sid, int(user_id), now_iso(), expiry_iso(ttl)),
    )
    await db.conn.commit()
    cache_for(bot).put(sid, True)
    return sid


async def alive(bot: Any, sid: Any) -> bool:
    """Present, unexpired and unrevoked — one cached read on the request path."""
    db = database_of(bot)
    if db is None:
        return True
    if not isinstance(sid, str) or not sid:
        return False
    cache = cache_for(bot)
    known = cache.get(sid)
    if known is not None:
        return known
    cur = await db.conn.execute("SELECT expires_at, revoked_at FROM sessions WHERE id = ?", (sid,))
    row = await cur.fetchone()
    live = bool(row is not None and row["revoked_at"] is None and not is_past(row["expires_at"]))
    cache.put(sid, live)
    return live


async def end(bot: Any, sid: Any) -> None:
    """Sign-out: the row is revoked and the cache says so before the next request."""
    if not isinstance(sid, str) or not sid:
        return
    cache_for(bot).put(sid, False)
    db = database_of(bot)
    if db is None:
        return
    await db.conn.execute(
        "UPDATE sessions SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
        (now_iso(), sid),
    )
    await db.conn.commit()


__all__ = [
    "CACHE_MAX_KEYS",
    "CACHE_TTL_SECONDS",
    "SessionCache",
    "alive",
    "cache_for",
    "database_of",
    "end",
    "expiry_iso",
    "is_past",
    "new_id",
    "start",
]
