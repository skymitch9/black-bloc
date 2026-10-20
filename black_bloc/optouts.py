"""One per-person table of who is out of what: the only way to ask, and the only way to write."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from .actionlog import log_action
from .logkinds import VIA_DISCORD, kind_via
from .settings_store import OPTOUT_DEFAULTS

log = logging.getLogger(__name__)

ANNOUNCE = "announce"
BIRTHDAY = "birthday"
CHAT_MEMORY = "chat_memory"
CHAT_MEMORY_IN = "chat_memory_in"
PBS = "pbs"
STREAMER_LIST = "streamer_list"
OUT_KINDS: tuple[str, ...] = (ANNOUNCE, BIRTHDAY, CHAT_MEMORY, PBS, STREAMER_LIST)
KINDS: tuple[str, ...] = (*OUT_KINDS, CHAT_MEMORY_IN)
IMPLICIT = "consent:optin"
MIGRATED = "migrated"
OVERRIDDEN = "optouts.overridden"
CACHE_ATTR = "_announce_out"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _known(kind: str) -> str:
    if kind not in KINDS:
        raise ValueError(f"{kind!r} is not an opt-out kind")
    return kind


async def is_out(db: Any, guild_id: Any, user_id: Any, kind: str) -> bool:
    """True when the person is out; an unreadable table answers True, never announced."""
    try:
        cur = await db.conn.execute(
            "SELECT 1 FROM person_optouts WHERE guild_id = ? AND user_id = ? AND kind = ?",
            (int(guild_id or 0), int(user_id or 0), _known(kind)),
        )
        return await cur.fetchone() is not None
    except ValueError:
        raise
    except Exception as exc:
        log.warning("opt-outs: %s was not read — %s: %s", kind, type(exc).__name__, exc)
        return True


async def row_of(db: Any, guild_id: Any, user_id: Any, kind: str) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM person_optouts WHERE guild_id = ? AND user_id = ? AND kind = ?",
        (int(guild_id or 0), int(user_id or 0), _known(kind)),
    )
    return await cur.fetchone()


async def rows(db: Any, guild_id: Any, kinds: Any = None) -> list[Any]:
    wanted = tuple(_known(one) for one in (kinds or OUT_KINDS))
    cur = await db.conn.execute(
        f"SELECT * FROM person_optouts WHERE guild_id = ? AND kind IN "
        f"({', '.join('?' for _ in wanted)}) ORDER BY kind, at DESC, user_id",
        (int(guild_id or 0), *wanted),
    )
    return list(await cur.fetchall())


async def out_of(db: Any, guild_id: Any, kind: str) -> set[int]:
    return {int(row["user_id"]) for row in await rows(db, guild_id, (kind,))}


async def count(db: Any, guild_id: Any, kind: str) -> int:
    cur = await db.conn.execute(
        "SELECT COUNT(*) AS found FROM person_optouts WHERE guild_id = ? AND kind = ?",
        (int(guild_id or 0), _known(kind)),
    )
    row = await cur.fetchone()
    return int(row["found"]) if row is not None else 0


async def _mirror(db: Any, user_id: int, kind: str, out: bool, at: str) -> None:
    if kind != ANNOUNCE:
        return
    if out:
        await db.conn.execute(
            "INSERT OR REPLACE INTO golive_optout(user_id, at) VALUES (?, ?)", (user_id, at)
        )
    else:
        await db.conn.execute("DELETE FROM golive_optout WHERE user_id = ?", (user_id,))


async def set_out(
    db: Any,
    guild_id: Any,
    user_id: Any,
    kind: str,
    *,
    by: Any = None,
    reason: Any = None,
    at: str | None = None,
    commit: bool = True,
) -> bool:
    """True when the row is new. The go-live table is still written for one release."""
    when = at or _now()
    cur = await db.conn.execute(
        "INSERT OR IGNORE INTO person_optouts(guild_id, user_id, kind, by, reason, at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            int(guild_id or 0),
            int(user_id or 0),
            _known(kind),
            int(by) if by else None,
            str(reason) if reason else None,
            when,
        ),
    )
    await _mirror(db, int(user_id or 0), kind, True, when)
    if commit:
        await db.conn.commit()
    if kind == ANNOUNCE:
        await load(db)
    return bool(cur.rowcount)


async def clear_out(
    db: Any, guild_id: Any, user_id: Any, kind: str, *, commit: bool = True
) -> bool:
    cur = await db.conn.execute(
        "DELETE FROM person_optouts WHERE guild_id = ? AND user_id = ? AND kind = ?",
        (int(guild_id or 0), int(user_id or 0), _known(kind)),
    )
    await _mirror(db, int(user_id or 0), kind, False, _now())
    if commit:
        await db.conn.commit()
    if kind == ANNOUNCE:
        await load(db)
    return bool(cur.rowcount)


async def load(db: Any) -> dict[int, frozenset[int]]:
    """The announce opt-outs held in memory for the readers that cannot await."""
    cur = await db.conn.execute(
        "SELECT guild_id, user_id FROM person_optouts WHERE kind = ?", (ANNOUNCE,)
    )
    found: dict[int, set[int]] = {}
    for row in await cur.fetchall():
        found.setdefault(int(row["guild_id"]), set()).add(int(row["user_id"]))
    held = {guild_id: frozenset(ids) for guild_id, ids in found.items()}
    setattr(db, CACHE_ATTR, held)
    return held


def silenced(db: Any, guild_id: Any) -> frozenset[int]:
    """Everyone out of announcements in one guild, from memory; empty before the first load."""
    held = getattr(db, CACHE_ATTR, None) if db is not None else None
    if held is None:
        return frozenset()
    return held.get(int(guild_id or 0), frozenset())


def said(store: Any, guild_id: Any, key: str, **fields: Any) -> str:
    """Checklist 17: words staff edited that will not fill fall back to the shipped ones."""
    try:
        return str(store.get(guild_id, key)).format_map(fields)
    except Exception:
        return str(OPTOUT_DEFAULTS[key]).format_map(fields)


async def overridden(
    bot: Any,
    guild: Any,
    actor: Any,
    target: Any,
    *,
    kind: str,
    move: str,
    reason: Any = None,
    via: str = VIA_DISCORD,
) -> None:
    """One row whenever staff announce, or let announce, someone who opted out."""
    await log_action(
        bot,
        guild,
        kind_via("optouts.overridden", via),
        actor=actor,
        target=target,
        details={"kind": kind, "move": move, "reason": reason or None, "via": via},
    )


__all__ = [
    "ANNOUNCE",
    "BIRTHDAY",
    "CHAT_MEMORY",
    "CHAT_MEMORY_IN",
    "IMPLICIT",
    "KINDS",
    "MIGRATED",
    "OUT_KINDS",
    "OVERRIDDEN",
    "PBS",
    "STREAMER_LIST",
    "clear_out",
    "count",
    "is_out",
    "load",
    "out_of",
    "overridden",
    "row_of",
    "rows",
    "said",
    "set_out",
    "silenced",
]
