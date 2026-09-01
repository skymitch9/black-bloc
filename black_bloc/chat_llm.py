from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from .chat import MENTION, has_phrase, normalise
from .llm import IMPORTANT, SIMPLE
from .settings_store import (
    CHAT_DAILY_TURNS,
    CHAT_MONTHLY_CAP_USD,
    CHAT_PERSON_HOURLY_TURNS,
)

log = logging.getLogger(__name__)

QUESTION_WORDS = 12
CONVERSATION_TURNS = 2
QUESTION_MARK = "?"

MEMBER = "member"
BOT = "bot"

WINDOW_MINUTES = 30
WINDOW_TURNS = 10
TURN_CHARS = 600
WINDOW_KEEP_MINUTES = 60

MICRODOLLARS_IN_A_DOLLAR = 1_000_000

PERSON_TURNS_KEY = "chat_person_hourly_turns"
DAILY_TURNS_KEY = "chat_daily_turns"
MONTHLY_CAP_KEY = "chat_monthly_cap_usd"

OPEN = "open"
PERSON_FULL = "person"
SERVER_FULL = "server"
CAPPED = "capped"
CAPPED_KIND = "chat.llm_capped"

STAFF_WORDS: tuple[str, ...] = (
    "staff",
    "mod",
    "mods",
    "moderator",
    "moderators",
    "admin",
    "admins",
    "auntie",
    "aunties",
    "uncle",
    "uncles",
    "report",
    "reported",
    "reporting",
    "ban",
    "banned",
    "kick",
    "kicked",
    "muted",
    "timeout",
    "timed out",
    "warned",
    "warning",
    "ticket",
    "modmail",
    "appeal",
    "harassing",
    "harassment",
)

BUDGET_WORDS: tuple[str, ...] = ("budget", "cap", "quota", "limit", "spend", "credit")

SPACES = re.compile(r"\s+")


def spoken(text: Any) -> str:
    """The message with Black Bloc's own mention taken out, punctuation left alone."""
    return SPACES.sub(" ", MENTION.sub(" ", str(text or ""))).strip()


def word_count(text: Any) -> int:
    said = spoken(text)
    return len(said.split()) if said else 0


def is_a_question(text: Any) -> bool:
    return QUESTION_MARK in spoken(text)


def a_real_question(text: Any) -> bool:
    return is_a_question(text) and word_count(text) > QUESTION_WORDS


def about_staff(text: Any) -> bool:
    words = normalise(text)
    return bool(words) and any(has_phrase(words, phrase) for phrase in STAFF_WORDS)


def llm_turns(window: Any) -> int:
    """Turns in this window a model answered; a canned reply is not one of them."""
    found = 0
    for turn in window or ():
        tier = turn.get("tier") if isinstance(turn, dict) else getattr(turn, "tier", None)
        if tier:
            found += 1
    return found


def a_conversation(window: Any) -> bool:
    return llm_turns(window) >= CONVERSATION_TURNS


def tier_for(message: Any, hits: Any = (), window: Any = ()) -> str:
    """IMPORTANT when the answer has to be right; SIMPLE for the banter. One home."""
    if list(hits or ()):
        return IMPORTANT
    if a_real_question(message):
        return IMPORTANT
    if a_conversation(window):
        return IMPORTANT
    if about_staff(message):
        return IMPORTANT
    return SIMPLE


def ladder(tier: str, *, important: bool, simple: bool) -> tuple[str, ...]:
    """Which tiers to try, in order. A tier with no key simply is not on the list."""
    if tier == IMPORTANT:
        wanted = (IMPORTANT,) if important else (SIMPLE,)
    else:
        wanted = (SIMPLE, IMPORTANT) if simple else (IMPORTANT,)
    live = {IMPORTANT: important, SIMPLE: simple}
    return tuple(name for name in wanted if live[name])


def says_a_budget_word(text: Any) -> str | None:
    """The first forbidden word in a sentence, so a test can name it."""
    words = normalise(text)
    for word in BUDGET_WORDS:
        if has_phrase(words, word):
            return word
    return None


def clip(text: Any, limit: int = TURN_CHARS) -> str:
    said = SPACES.sub(" ", str(text or "")).strip()
    return said if len(said) <= limit else f"{said[: limit - 1]}…"


def window_key(channel_id: Any, user_id: Any) -> str:
    return f"{int(channel_id or 0)}:{int(user_id or 0)}"


def hour_before(now: datetime) -> str:
    return (now - timedelta(hours=1)).isoformat()


def day_start(now: datetime) -> str:
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def month_start(now: datetime) -> str:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()


def in_dollars(microdollars: Any) -> float:
    return round(int(microdollars or 0) / MICRODOLLARS_IN_A_DOLLAR, 2)


def money(microdollars: Any) -> str:
    return f"${in_dollars(microdollars):.2f}"


async def remember(
    db: Any,
    *,
    guild_id: int | None,
    channel_id: int | None,
    user_id: int,
    speaker: str,
    content: Any,
    tier: str | None = None,
    at: datetime | None = None,
) -> None:
    """One turn of the conversation, clipped. Never raises into a reply."""
    said = clip(content)
    if not said:
        return
    try:
        await db.conn.execute(
            "INSERT INTO chat_window(guild_id, channel_id, user_id, at, speaker, content, tier) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                None if guild_id is None else int(guild_id),
                int(channel_id or 0),
                int(user_id),
                (at or datetime.now(UTC)).isoformat(),
                str(speaker),
                said,
                tier,
            ),
        )
        await db.conn.commit()
    except Exception as exc:
        log.warning("chat: a turn was not remembered — %s: %s", type(exc).__name__, exc)


async def window_for(
    db: Any,
    channel_id: Any,
    user_id: Any,
    *,
    minutes: int = WINDOW_MINUTES,
    turns: int = WINDOW_TURNS,
    now: datetime | None = None,
) -> list[Any]:
    """The last few exchanges with one person in one place, oldest first."""
    since = ((now or datetime.now(UTC)) - timedelta(minutes=minutes)).isoformat()
    try:
        cur = await db.conn.execute(
            "SELECT * FROM chat_window WHERE channel_id = ? AND user_id = ? AND at >= ? "
            "ORDER BY id DESC LIMIT ?",
            (int(channel_id or 0), int(user_id), since, max(0, int(turns) * 2)),
        )
        rows = list(await cur.fetchall())
    except Exception as exc:
        log.warning("chat: the window was not read — %s: %s", type(exc).__name__, exc)
        return []
    return list(reversed(rows))


async def sweep_window(db: Any, *, minutes: int = WINDOW_KEEP_MINUTES, now: datetime | None = None
                       ) -> int:
    """Kept an hour rather than half of one: the fuses read the ledger, the reply reads 30 min."""
    before = ((now or datetime.now(UTC)) - timedelta(minutes=minutes)).isoformat()
    cur = await db.conn.execute("DELETE FROM chat_window WHERE at < ?", (before,))
    await db.conn.commit()
    return int(cur.rowcount or 0)


def as_messages(window: Any) -> list[dict[str, str]]:
    """The window as the two providers both want it: alternating user and assistant text."""
    found: list[dict[str, str]] = []
    for turn in window or ():
        speaker = str(turn["speaker"])
        content = str(turn["content"])
        if not content:
            continue
        found.append(
            {"role": "assistant" if speaker == BOT else "user", "content": content}
        )
    return found


async def counted(db: Any, sql: str, params: tuple[Any, ...]) -> int:
    try:
        cur = await db.conn.execute(sql, params)
        row = await cur.fetchone()
    except Exception as exc:
        log.warning("chat: a fuse could not be counted — %s: %s", type(exc).__name__, exc)
        return 0
    return int((row[0] if row is not None else 0) or 0)


async def person_turns(db: Any, user_id: int, since: str) -> int:
    return await counted(
        db,
        "SELECT COUNT(DISTINCT turn) FROM llm_ledger WHERE user_id = ? AND at >= ?",
        (int(user_id), since),
    )


async def server_turns(db: Any, since: str) -> int:
    """Every guild and every DM together — the bill is one account's, not one server's."""
    return await counted(
        db, "SELECT COUNT(DISTINCT turn) FROM llm_ledger WHERE at >= ?", (since,)
    )


async def month_spend(db: Any, since: str) -> int:
    return await counted(
        db, "SELECT SUM(cost_microdollars) FROM llm_ledger WHERE at >= ?", (since,)
    )


def setting(store: Any, guild_id: Any, key: str, fallback: int) -> int:
    """A DM has no server to read a number off, so it gets the registry's own default."""
    if store is None or guild_id is None:
        return fallback
    try:
        found = store.get(int(guild_id), key)
    except Exception as exc:
        log.warning("chat: %s was unreadable — %s: %s", key, type(exc).__name__, exc)
        return fallback
    return fallback if found is None else int(found)


@dataclass(frozen=True)
class Allowance:
    why: str = OPEN
    person: int = 0
    person_of: int = 0
    today: int = 0
    today_of: int = 0
    spent: int = 0
    cap: int = 0

    @property
    def ok(self) -> bool:
        return self.why == OPEN


async def allowance(
    db: Any, store: Any, guild_id: Any, user_id: int, *, now: datetime | None = None
) -> Allowance:
    """Three counters, never folded into one: a cheap turn's forgiveness cannot buy a dear one."""
    at = now or datetime.now(UTC)
    person_of = setting(store, guild_id, PERSON_TURNS_KEY, CHAT_PERSON_HOURLY_TURNS)
    today_of = setting(store, guild_id, DAILY_TURNS_KEY, CHAT_DAILY_TURNS)
    cap = setting(store, guild_id, MONTHLY_CAP_KEY, CHAT_MONTHLY_CAP_USD)
    mine = await person_turns(db, user_id, hour_before(at))
    today = await server_turns(db, day_start(at))
    spent = await month_spend(db, month_start(at))
    why = OPEN
    if spent >= cap * MICRODOLLARS_IN_A_DOLLAR:
        why = CAPPED
    elif today_of and today >= today_of:
        why = SERVER_FULL
    elif person_of and mine >= person_of:
        why = PERSON_FULL
    return Allowance(
        why=why,
        person=mine,
        person_of=person_of,
        today=today,
        today_of=today_of,
        spent=spent,
        cap=cap,
    )


async def capped_already_logged(db: Any, guild_id: int, since: str) -> bool:
    """Once per closure survives a restart, because the answer is a row rather than a flag."""
    return (
        await counted(
            db,
            "SELECT COUNT(*) FROM action_log WHERE guild_id = ? AND kind = ? AND at >= ?",
            (int(guild_id), CAPPED_KIND, since),
        )
        > 0
    )
