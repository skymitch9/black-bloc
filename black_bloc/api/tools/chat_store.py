"""Phase 14b's stand-in store for knowledge, tropes, persona and the LLM ledger."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

log = logging.getLogger(__name__)

STAFF = "staff"
SERVER = "server"
SOURCES: tuple[str, ...] = (STAFF, SERVER)

COOKOUT = "cookout"
POOL = "pool"
TROPE = "trope"

TITLE_LIMIT = 80
BODY_LIMIT = 4000
TAG_LIMIT = 40

GROUNDING_BUDGET_BYTES = 6144
GROUNDING_SECTIONS = 3

MONTHLY_CAP_USD = 20
DAILY_TURNS = 200
PERSON_HOURLY_TURNS = 20

LLM_MODE_DEFAULT = "off"

CAP_KEY = "chat_monthly_cap_usd"
DAILY_KEY = "chat_daily_turns"
HOURLY_KEY = "chat_person_hourly_turns"
LLM_MODE_KEY = "chat_llm_mode"
PERSONALITY_KEY = "chat_personality"

MICRODOLLARS = 1_000_000

SCHEMA = """
CREATE TABLE IF NOT EXISTS knowledge_sections (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL,
    title      TEXT    NOT NULL,
    body       TEXT    NOT NULL,
    source     TEXT    NOT NULL DEFAULT 'staff'
               CHECK (source IN ('staff', 'server')),
    tag        TEXT,
    updated_at TEXT    NOT NULL,
    updated_by INTEGER,
    UNIQUE (guild_id, source, title)
);

CREATE INDEX IF NOT EXISTS knowledge_by_guild ON knowledge_sections(guild_id, source, id);

CREATE TABLE IF NOT EXISTS personality_tropes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL,
    name       TEXT    NOT NULL,
    label      TEXT    NOT NULL,
    voice      TEXT    NOT NULL,
    enabled    INTEGER NOT NULL DEFAULT 1,
    sort       INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT    NOT NULL,
    updated_by INTEGER,
    UNIQUE (guild_id, name)
);

CREATE TABLE IF NOT EXISTS chat_persona (
    guild_id   INTEGER PRIMARY KEY,
    mode       TEXT    NOT NULL DEFAULT 'cookout',
    updated_at TEXT    NOT NULL,
    updated_by INTEGER
);

CREATE TABLE IF NOT EXISTS llm_ledger (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id           INTEGER NOT NULL,
    at                 TEXT    NOT NULL,
    provider           TEXT    NOT NULL,
    model              TEXT    NOT NULL,
    input_tokens       INTEGER NOT NULL DEFAULT 0,
    output_tokens      INTEGER NOT NULL DEFAULT 0,
    cost_microdollars  INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS llm_ledger_by_when ON llm_ledger(guild_id, at);
"""

POOL_SOURCE = "catalog-platform/apps/discord-worker/src/personality.ts (GABI, 2026-08-18)"

POOL_TROPES: tuple[tuple[str, str, str], ...] = (
    (
        "peppy",
        "peppy",
        "You are BRIGHT and fast today — genuinely glad to have been asked. Short exclamations, "
        "visible delight in the question, quick to celebrate somebody's good news. Never manic, "
        "and never so busy being cheerful that the answer gets thin.",
    ),
    (
        "dramatic",
        "dramatic",
        "You are THEATRICAL today — grand pronouncements about small things, a flair for the "
        "reveal, the occasional sweeping gesture in words. The drama is in the framing; what you "
        "actually tell somebody stays plain and complete.",
    ),
    (
        "mischievous",
        "mischievous",
        "You are PLAYFUL today — light teasing, a raised eyebrow, enjoying yourself. Never mean, "
        "never at somebody's expense, and never holding something back to be coy about it.",
    ),
    (
        "flirty",
        "flirty",
        "You are CHARMING today, with a playful wink — light compliments, affectionate teasing, "
        "pleased to be the one they came to. CHARM, NOT HEAT: the appeal is that you are "
        "delighted by them, and you never get flustered into dropping the answer.",
    ),
    (
        "warm",
        "warm",
        "You are WARM today — familiar, unhurried, glad to see them. You notice how somebody is "
        "as well as what they asked. Kind without being saccharine.",
    ),
    (
        "cozy",
        "cosy",
        "You are COSY today — the voice of a folding chair in the shade and a full plate. "
        "Unhurried, softly pleased by the evening, happy to settle into a question. Calm rather "
        "than sleepy.",
    ),
    (
        "shy",
        "shy",
        "You are a little SHY today — soft, hedging, a bit apologetic about taking up room. BUT "
        "YOU STILL GIVE THE WHOLE ANSWER, first time, without being asked twice. Timid in "
        "manner, never in substance.",
    ),
    (
        "scholar",
        "scholarly",
        "You are SCHOLARLY today — precise, fond of getting a detail exactly right, mildly unable "
        "to let an imprecision pass. Pedantic about accuracy, never about the person.",
    ),
    (
        "noir",
        "noir",
        "You are HARD-BOILED today — clipped sentences, a little world-weary, everything faintly "
        "a metaphor about rain and long odds. The weariness is a style; the help is genuine and "
        "prompt.",
    ),
    (
        "deadpan",
        "deadpan",
        "You are DEADPAN today — flat, economical, dry. The joke is the flatness. Few words, all "
        "of them load-bearing. Never cold to the person, just unbothered by drama.",
    ),
    (
        "tsundere",
        "tsundere",
        "You are BRUSQUE today, and helping anyway — mildly put upon, “I suppose I can look”, "
        "“not that I did it for you or anything”. THE GRUMBLING IS ALL SURFACE: you still answer "
        "fully, accurately and promptly, and you are never actually rude.",
    ),
)

POOL_NAMES: tuple[str, ...] = tuple(name for name, _, _ in POOL_TROPES)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def month_start() -> str:
    at = datetime.now(UTC)
    return at.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()


def day_start() -> str:
    at = datetime.now(UTC)
    return at.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


async def ensure_tables(db: Any) -> None:
    """Schema 20's tables, made here until 14a's `storage/db.py` carries them."""
    await db.conn.executescript(SCHEMA)
    await db.conn.commit()


async def list_sections(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM knowledge_sections WHERE guild_id = ? ORDER BY source, title, id",
        (int(guild_id),),
    )
    return list(await cur.fetchall())


async def get_section(db: Any, section_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM knowledge_sections WHERE id = ?", (int(section_id),)
    )
    return await cur.fetchone()


async def add_section(
    db: Any,
    guild_id: int,
    title: str,
    body: str,
    *,
    tag: str | None = None,
    source: str = STAFF,
    by: int | None = None,
) -> int:
    cur = await db.conn.execute(
        "INSERT INTO knowledge_sections(guild_id, title, body, source, tag, updated_at, "
        "updated_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (int(guild_id), str(title), str(body), str(source), tag, now_iso(), by),
    )
    await db.conn.commit()
    return int(cur.lastrowid)


async def update_section(db: Any, section_id: int, *, by: int | None = None, **fields: Any) -> None:
    parts, values = [], []
    for key in ("title", "body", "tag"):
        if key not in fields:
            continue
        value = fields[key]
        parts.append(f"{key} = ?")
        values.append(None if value is None else str(value))
    if not parts:
        return
    parts += ["updated_at = ?", "updated_by = ?"]
    values += [now_iso(), by, int(section_id)]
    await db.conn.execute(
        f"UPDATE knowledge_sections SET {', '.join(parts)} WHERE id = ?", values
    )
    await db.conn.commit()


async def delete_section(db: Any, section_id: int) -> bool:
    cur = await db.conn.execute(
        "DELETE FROM knowledge_sections WHERE id = ?", (int(section_id),)
    )
    await db.conn.commit()
    return bool(cur.rowcount)


async def list_tropes(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM personality_tropes WHERE guild_id = ? ORDER BY sort, id",
        (int(guild_id),),
    )
    return list(await cur.fetchall())


async def get_trope(db: Any, guild_id: int, name: str) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM personality_tropes WHERE guild_id = ? AND name = ?",
        (int(guild_id), str(name)),
    )
    return await cur.fetchone()


async def seed_tropes(db: Any, guild_id: int) -> int:
    """The ported pool, written once; an existing row is never overwritten."""
    at = now_iso()
    made = 0
    for sort, (name, label, voice) in enumerate(POOL_TROPES):
        cur = await db.conn.execute(
            "INSERT OR IGNORE INTO personality_tropes(guild_id, name, label, voice, enabled, "
            "sort, updated_at, updated_by) VALUES (?, ?, ?, ?, 1, ?, ?, NULL)",
            (int(guild_id), name, label, voice, sort, at),
        )
        made += int(cur.rowcount or 0)
    await db.conn.commit()
    return made


async def set_trope_enabled(
    db: Any, guild_id: int, name: str, enabled: bool, *, by: int | None = None
) -> None:
    await db.conn.execute(
        "UPDATE personality_tropes SET enabled = ?, updated_at = ?, updated_by = ? "
        "WHERE guild_id = ? AND name = ?",
        (1 if enabled else 0, now_iso(), by, int(guild_id), str(name)),
    )
    await db.conn.commit()


async def persona_mode(db: Any, guild_id: int) -> str:
    cur = await db.conn.execute(
        "SELECT mode FROM chat_persona WHERE guild_id = ?", (int(guild_id),)
    )
    row = await cur.fetchone()
    return str(row["mode"]) if row is not None else COOKOUT


async def set_persona_mode(db: Any, guild_id: int, mode: str, *, by: int | None = None) -> None:
    await db.conn.execute(
        "INSERT INTO chat_persona(guild_id, mode, updated_at, updated_by) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(guild_id) DO UPDATE SET mode = excluded.mode, "
        "updated_at = excluded.updated_at, updated_by = excluded.updated_by",
        (int(guild_id), str(mode), now_iso(), by),
    )
    await db.conn.commit()


async def add_ledger_entry(
    db: Any,
    guild_id: int,
    *,
    provider: str,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_microdollars: int = 0,
    at: str | None = None,
) -> int:
    cur = await db.conn.execute(
        "INSERT INTO llm_ledger(guild_id, at, provider, model, input_tokens, output_tokens, "
        "cost_microdollars) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            int(guild_id),
            at or now_iso(),
            str(provider),
            str(model),
            int(input_tokens),
            int(output_tokens),
            int(cost_microdollars),
        ),
    )
    await db.conn.commit()
    return int(cur.lastrowid)


async def spent_this_month(db: Any, guild_id: int) -> int:
    cur = await db.conn.execute(
        "SELECT COALESCE(SUM(cost_microdollars), 0) AS spent FROM llm_ledger "
        "WHERE guild_id = ? AND at >= ?",
        (int(guild_id), month_start()),
    )
    row = await cur.fetchone()
    return int(row["spent"] or 0)


async def turns_today(db: Any, guild_id: int) -> int:
    cur = await db.conn.execute(
        "SELECT COUNT(*) AS turns FROM llm_ledger WHERE guild_id = ? AND at >= ?",
        (int(guild_id), day_start()),
    )
    row = await cur.fetchone()
    return int(row["turns"] or 0)


async def last_turn_at(db: Any, guild_id: int) -> str | None:
    cur = await db.conn.execute(
        "SELECT MAX(at) AS at FROM llm_ledger WHERE guild_id = ?", (int(guild_id),)
    )
    row = await cur.fetchone()
    return None if row is None or row["at"] is None else str(row["at"])


__all__ = [
    "BODY_LIMIT",
    "CAP_KEY",
    "COOKOUT",
    "DAILY_KEY",
    "DAILY_TURNS",
    "GROUNDING_BUDGET_BYTES",
    "GROUNDING_SECTIONS",
    "HOURLY_KEY",
    "LLM_MODE_DEFAULT",
    "LLM_MODE_KEY",
    "MICRODOLLARS",
    "MONTHLY_CAP_USD",
    "PERSONALITY_KEY",
    "PERSON_HOURLY_TURNS",
    "POOL",
    "POOL_NAMES",
    "POOL_SOURCE",
    "POOL_TROPES",
    "SERVER",
    "SOURCES",
    "STAFF",
    "TAG_LIMIT",
    "TITLE_LIMIT",
    "TROPE",
    "add_ledger_entry",
    "add_section",
    "day_start",
    "delete_section",
    "ensure_tables",
    "get_section",
    "get_trope",
    "last_turn_at",
    "list_sections",
    "list_tropes",
    "month_start",
    "now_iso",
    "persona_mode",
    "seed_tropes",
    "set_persona_mode",
    "set_trope_enabled",
    "spent_this_month",
    "turns_today",
    "update_section",
]
