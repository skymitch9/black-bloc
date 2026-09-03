from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from .actionlog import log_action
from .chat_llm import (
    MEMBER,
    SIMPLE_MODEL_KEY,
    WINDOW_KEEP_MINUTES,
    about_staff,
    allowance,
    groq,
    read_setting,
    usable_db,
)
from .chat_memory import (
    CONSENT_KEY,
    DISTIL_FAILED_KIND,
    DISTIL_MIN_TURNS,
    DISTILLED_KIND,
    DM,
    EXPIRED_KIND,
    MEMORY_TIER,
    MODE_KEY,
    MODEL_KEY,
    NOTES_MAX,
    NOTES_MAX_KEY,
    ON,
    OPTOUT,
    RETENTION_DAYS,
    RETENTION_KEY,
    SERVER,
    THREADS_MAX,
    THREADS_MAX_KEY,
    distil_prompt,
    expire,
    merge,
    other_names,
    parse_distilled,
    profile_for,
    remembers,
    save_profile,
    turn_speaker,
)
from .llm import ERROR, GROQ, OK, LLMError, record

log = logging.getLogger(__name__)

DISTIL_MAX_TOKENS = 600


def memory_is_on(store: Any, guild_id: Any) -> bool:
    """Affirmative only: off, unreadable, or no server at all all mean nothing is written."""
    if store is None or guild_id is None:
        return False
    return read_setting(store, guild_id, MODE_KEY, "off") == ON


def whole(store: Any, guild_id: Any, key: str, fallback: int) -> int:
    try:
        return int(read_setting(store, guild_id, key, fallback))
    except (TypeError, ValueError):
        return fallback


async def expiring(
    db: Any, *, minutes: int = WINDOW_KEEP_MINUTES, now: datetime | None = None
) -> list[Any]:
    """The turns this sweep is about to delete, oldest first — read before the DELETE."""
    before = ((now or datetime.now(UTC)) - timedelta(minutes=minutes)).isoformat()
    try:
        cur = await db.conn.execute(
            "SELECT * FROM chat_window WHERE at < ? ORDER BY id", (before,)
        )
        return list(await cur.fetchall())
    except Exception as exc:
        log.warning("chat memory: the expiring turns were not read — %s: %s",
                    type(exc).__name__, exc)
        return []


def conversations(rows: Any) -> dict[tuple[Any, int, int], list[Any]]:
    """One conversation is one person in one place; a DM has no guild, so it files under None."""
    found: dict[tuple[Any, int, int], list[Any]] = {}
    for row in rows or ():
        key = (row["guild_id"], int(row["channel_id"] or 0), int(row["user_id"] or 0))
        found.setdefault(key, []).append(row)
    return found


def member_turns(turns: Any) -> list[Any]:
    return [one for one in turns or () if turn_speaker(one) == MEMBER]


def worth_distilling(turns: Any) -> bool:
    """Two member turns at least, and not one word of a staff conversation."""
    mine = member_turns(turns)
    if len(mine) < DISTIL_MIN_TURNS:
        return False
    return not any(about_staff(one["content"]) for one in mine)


async def distil_one(
    bot: Any,
    db: Any,
    *,
    guild: Any,
    guild_id: Any,
    user_id: int,
    turns: list[Any],
    where: str,
    now: datetime,
) -> bool:
    """One conversation into one profile; False means nothing was written, never a partial one."""
    store = bot.store
    notes_max = whole(store, guild_id, NOTES_MAX_KEY, NOTES_MAX)
    threads_max = whole(store, guild_id, THREADS_MAX_KEY, THREADS_MAX)
    standing = await profile_for(db, user_id, guild_id)
    system, messages = distil_prompt(
        standing, turns, where=where, notes_max=notes_max, threads_max=threads_max
    )
    model = str(read_setting(store, guild_id, MODEL_KEY, "") or "") or str(
        read_setting(store, guild_id, SIMPLE_MODEL_KEY, "") or ""
    )
    client = groq(bot, model, MEMORY_TIER)
    if client is None:
        return False
    turn = uuid.uuid4().hex
    try:
        answer = await client.reply(system=system, messages=messages, json_only=True)
    except LLMError as exc:
        await record(
            db,
            guild_id=guild_id,
            user_id=user_id,
            turn=turn,
            provider=GROQ,
            model=client.model,
            tier=MEMORY_TIER,
            outcome=ERROR,
            at=now,
        )
        log.warning("chat memory: the distillation did not answer — %s", exc.reason)
        return False
    await record(
        db,
        guild_id=guild_id,
        user_id=user_id,
        turn=turn,
        provider=answer.provider,
        model=answer.model,
        tier=MEMORY_TIER,
        outcome=OK,
        usage=answer.usage,
        at=now,
    )
    found = parse_distilled(
        answer.text, turns=turns, others=other_names(guild, user_id)
    )
    if found is None:
        log.warning("chat memory: a distillation was not in the shape asked for")
        return False
    if found.empty and standing is None:
        return True
    fresh = merge(
        standing,
        found,
        where=where,
        at=now.isoformat(),
        notes_max=notes_max,
        threads_max=threads_max,
        seen=len(member_turns(turns)),
    )
    if not await save_profile(db, user_id, guild_id, fresh):
        return False
    if guild is not None:
        await log_action(
            bot,
            guild,
            DISTILLED_KIND,
            target=user_id,
            details={
                "notes": len(fresh.notes),
                "threads": len(fresh.threads),
                "dropped": len(found.dropped),
                "where": where,
            },
        )
    return True


async def run(bot: Any, *, now: datetime | None = None) -> dict[str, int]:
    """Every expiring conversation, before the sweep deletes it. Never raises into the loop."""
    db = usable_db(bot)
    if db is None:
        return {"looked": 0, "distilled": 0, "failed": 0, "expired": 0}
    at = now or datetime.now(UTC)
    home = getattr(bot.settings, "dev_guild_id", None)
    looked = distilled = failed = 0
    for (guild_id, _channel_id, user_id), turns in conversations(
        await expiring(db, now=at)
    ).items():
        where = SERVER if guild_id is not None else DM
        filed_under = guild_id if guild_id is not None else home
        if filed_under is None or not memory_is_on(bot.store, filed_under):
            continue
        if not worth_distilling(turns):
            continue
        consent = read_setting(bot.store, filed_under, CONSENT_KEY, OPTOUT)
        if not await remembers(db, user_id, filed_under, consent=consent):
            continue
        spent = await allowance(db, bot.store, filed_under, user_id, now=at)
        if not spent.ok:
            log.info("chat memory: the models are closed for now (%s)", spent.why)
            break
        guild = bot.get_guild(int(filed_under)) if hasattr(bot, "get_guild") else None
        looked += 1
        if await distil_one(
            bot,
            db,
            guild=guild,
            guild_id=filed_under,
            user_id=user_id,
            turns=turns,
            where=where,
            now=at,
        ):
            distilled += 1
        else:
            failed += 1
    if failed:
        await tell(bot, home, DISTIL_FAILED_KIND, {"conversations": failed})
    gone = await forget_the_old(bot, db, home=home, now=at)
    return {"looked": looked, "distilled": distilled, "failed": failed, "expired": gone}


async def forget_the_old(bot: Any, db: Any, *, home: Any, now: datetime) -> int:
    days = whole(bot.store, home, RETENTION_KEY, RETENTION_DAYS) if home is not None else 0
    gone = await expire(db, days=days, now=now) if days else 0
    if gone:
        await tell(bot, home, EXPIRED_KIND, {"profiles": gone})
    return gone


async def tell(bot: Any, guild_id: Any, kind: str, details: dict[str, Any]) -> None:
    guild = bot.get_guild(int(guild_id)) if guild_id and hasattr(bot, "get_guild") else None
    if guild is None:
        return
    await log_action(bot, guild, kind, details=details)


__all__ = [
    "conversations",
    "distil_one",
    "expiring",
    "forget_the_old",
    "member_turns",
    "memory_is_on",
    "run",
    "worth_distilling",
]
