from __future__ import annotations

import json
import logging
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from .actionlog import log_action
from .chat_llm import (
    MEMBER,
    SIMPLE_MODEL_KEY,
    WINDOW_KEEP_MINUTES,
    about_staff,
    allowance,
    clients_for,
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
    MIN_TURNS_KEY,
    MODE_KEY,
    MODEL_KEY,
    NOTES_MAX,
    NOTES_MAX_KEY,
    ON,
    OPTOUT,
    RAPPORT_MAX,
    RAPPORT_MAX_KEY,
    RETENTION_DAYS,
    RETENTION_KEY,
    SERVER,
    SWEEP_KIND,
    THREADS_MAX,
    THREADS_MAX_KEY,
    distil_prompt,
    expire,
    merge,
    other_names,
    parse_distilled,
    profile_for,
    remembers,
    turn_speaker,
    without_the_dropped,
    write_up,
)
from .groq import GroqClient
from .llm import ERROR, GROQ, OK, LLMError, record

log = logging.getLogger(__name__)

DISTIL_MAX_TOKENS = 1200

KEPT = "kept"
NOTHING = "nothing"
ALL_DROPPED = "all_dropped"
NO_ANSWER = "no_answer"
BAD_SHAPE = "bad_shape"
NO_MODEL = "no_model"
NOT_SAVED = "not_saved"
CLOSED = "models_closed"
WITHDRAWN = "withdrawn"
FORGOTTEN = "forgotten"
STOOD_DOWN = (WITHDRAWN, FORGOTTEN)
FAILURES = (NO_ANSWER, BAD_SHAPE, NO_MODEL, NOT_SAVED)
TROUBLES = (*FAILURES, ALL_DROPPED, CLOSED)

SKIP_SHORT = "short"
SKIP_STAFF = "staff"
SKIP_OPTED_OUT = "opted_out"


@dataclass(frozen=True)
class Outcome:
    """What one conversation came to: a code, the provider's reason, and the rules that fired."""

    code: str
    why: str = ""
    dropped: tuple[str, ...] = ()
    name: int = 0
    notes: int = 0
    threads: int = 0
    rapport: int = 0

    @property
    def stored(self) -> bool:
        return self.code == KEPT


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


def why_skipped(turns: Any, least: int = DISTIL_MIN_TURNS) -> str | None:
    """The reason a conversation never reaches a model, or None when it may."""
    mine = member_turns(turns)
    if len(mine) < max(1, int(least)):
        return SKIP_SHORT
    if any(about_staff(one["content"]) for one in mine):
        return SKIP_STAFF
    return None


def worth_distilling(turns: Any, least: int = DISTIL_MIN_TURNS) -> bool:
    """Enough member turns, and not one word of a staff conversation."""
    return why_skipped(turns, least) is None


def distiller(bot: Any, model: str) -> Any:
    """Its own slot and its own token ceiling: a reasoning model thinks out of the same budget."""
    if not bot.settings.simple_tier_configured:
        return None
    made = clients_for(bot)
    found = made.get(MEMORY_TIER)
    roomy = getattr(found, "max_tokens", DISTIL_MAX_TOKENS) == DISTIL_MAX_TOKENS
    if found is None or found.model != model or not roomy:
        found = GroqClient(bot.settings.groq_api_key, model=model, max_tokens=DISTIL_MAX_TOKENS)
        made[MEMORY_TIER] = found
    return found


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
) -> Outcome:
    """One conversation into one profile; anything but KEPT wrote nothing, never a partial one."""
    store = bot.store
    notes_max = whole(store, guild_id, NOTES_MAX_KEY, NOTES_MAX)
    threads_max = whole(store, guild_id, THREADS_MAX_KEY, THREADS_MAX)
    rapport_max = whole(store, guild_id, RAPPORT_MAX_KEY, RAPPORT_MAX)
    standing = await profile_for(db, user_id, guild_id)
    system, messages = distil_prompt(
        standing,
        turns,
        where=where,
        notes_max=notes_max,
        threads_max=threads_max,
        rapport_max=rapport_max,
    )
    model = str(read_setting(store, guild_id, MODEL_KEY, "") or "") or str(
        read_setting(store, guild_id, SIMPLE_MODEL_KEY, "") or ""
    )
    client = distiller(bot, model)
    if client is None:
        return Outcome(NO_MODEL)
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
        log.warning("chat memory: the distillation did not answer — %s (%s)", exc.reason, exc)
        return Outcome(NO_ANSWER, why=str(exc.reason))
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
        return Outcome(BAD_SHAPE)
    if found.empty:
        return Outcome(ALL_DROPPED if found.dropped else NOTHING, dropped=found.dropped)
    consent = read_setting(store, guild_id, CONSENT_KEY, OPTOUT)
    if not await remembers(db, user_id, guild_id, consent=consent):
        return Outcome(WITHDRAWN)
    current = await profile_for(db, user_id, guild_id)
    if standing is not None and current is None:
        return Outcome(FORGOTTEN)
    found = without_the_dropped(found, standing, current)
    if found.empty:
        return Outcome(NOTHING, dropped=found.dropped)
    fresh = merge(
        current,
        found,
        where=where,
        at=now.isoformat(),
        notes_max=notes_max,
        threads_max=threads_max,
        rapport_max=rapport_max,
        seen=len(member_turns(turns)),
    )
    if not await write_up(
        db, user_id, guild_id, fresh, existed=current is not None, consent=consent
    ):
        return await not_written(db, user_id, guild_id, consent, existed=current is not None)
    if guild is not None:
        await log_action(
            bot,
            guild,
            DISTILLED_KIND,
            target=user_id,
            details={
                "notes": len(fresh.notes),
                "threads": len(fresh.threads),
                "rapport": len(fresh.rapport),
                "dropped": len(found.dropped),
                "where": where,
            },
        )
    return Outcome(
        KEPT,
        dropped=found.dropped,
        name=1 if found.call_me else 0,
        notes=len(found.notes),
        threads=len(found.threads),
        rapport=len(found.rapport),
    )


async def not_written(
    db: Any, user_id: int, guild_id: Any, consent: Any, *, existed: bool
) -> Outcome:
    """Why the one statement touched no row: the person stopped, forgot, or the write failed."""
    if not await remembers(db, user_id, guild_id, consent=consent):
        return Outcome(WITHDRAWN)
    if existed and await profile_for(db, user_id, guild_id) is None:
        return Outcome(FORGOTTEN)
    return Outcome(NOT_SAVED)


def summed(
    *,
    seen: int,
    skipped: Counter[str],
    outcomes: list[Outcome],
    closed: Counter[str],
    expired: int,
) -> dict[str, Any]:
    """One sweep as numbers and reason codes — never a word anybody typed."""
    codes = Counter(one.code for one in outcomes)
    reasons = Counter({code: codes[code] for code in TROUBLES if codes[code]})
    if closed:
        reasons[CLOSED] = sum(closed.values())
    return {
        "seen": seen,
        "looked": len(outcomes),
        "distilled": codes[KEPT],
        "nothing": codes[NOTHING],
        "dropped": codes[ALL_DROPPED],
        "failed": sum(codes[code] for code in FAILURES),
        "closed": sum(closed.values()),
        "expired": expired,
        "skipped": dict(skipped),
        "reasons": dict(reasons),
        "no_answer": dict(Counter(one.why for one in outcomes if one.code == NO_ANSWER)),
        "closed_why": dict(closed),
        "stood_down": {code: codes[code] for code in STOOD_DOWN if codes[code]},
        "rules": dict(Counter(rule for one in outcomes for rule in one.dropped)),
        "lines": {
            "names": sum(one.name for one in outcomes),
            "notes": sum(one.notes for one in outcomes),
            "threads": sum(one.threads for one in outcomes),
            "rapport": sum(one.rapport for one in outcomes),
        },
    }


EMPTY_RUN: dict[str, Any] = summed(
    seen=0, skipped=Counter(), outcomes=[], closed=Counter(), expired=0
)


async def run(bot: Any, *, now: datetime | None = None) -> dict[str, Any]:
    """Every expiring conversation, before the sweep deletes it. Never raises into the loop."""
    db = usable_db(bot)
    if db is None:
        return dict(EMPTY_RUN)
    at = now or datetime.now(UTC)
    home = getattr(bot.settings, "dev_guild_id", None)
    seen = 0
    skipped: Counter[str] = Counter()
    closed: Counter[str] = Counter()
    outcomes: list[Outcome] = []
    for (guild_id, _channel_id, user_id), turns in conversations(
        await expiring(db, now=at)
    ).items():
        where = SERVER if guild_id is not None else DM
        filed_under = guild_id if guild_id is not None else home
        if filed_under is None or not memory_is_on(bot.store, filed_under):
            continue
        seen += 1
        least = whole(bot.store, filed_under, MIN_TURNS_KEY, DISTIL_MIN_TURNS)
        skip = why_skipped(turns, least)
        if skip is not None:
            skipped[skip] += 1
            continue
        consent = read_setting(bot.store, filed_under, CONSENT_KEY, OPTOUT)
        if not await remembers(db, user_id, filed_under, consent=consent):
            skipped[SKIP_OPTED_OUT] += 1
            continue
        spent = await allowance(db, bot.store, filed_under, user_id, now=at)
        if not spent.ok:
            log.info("chat memory: the models are closed for now (%s)", spent.why)
            closed[str(spent.why)] += 1
            continue
        guild = bot.get_guild(int(filed_under)) if hasattr(bot, "get_guild") else None
        outcomes.append(
            await distil_one(
                bot,
                db,
                guild=guild,
                guild_id=filed_under,
                user_id=user_id,
                turns=turns,
                where=where,
                now=at,
            )
        )
    gone = await forget_the_old(bot, db, home=home, now=at)
    found = summed(seen=seen, skipped=skipped, outcomes=outcomes, closed=closed, expired=gone)
    if found["reasons"]:
        await tell(
            bot,
            home,
            DISTIL_FAILED_KIND,
            {
                "conversations": sum(found["reasons"].values()),
                "reasons": found["reasons"],
                "no_answer": found["no_answer"],
                "closed_why": found["closed_why"],
                "rules": found["rules"],
            },
        )
    if seen:
        await tell(bot, home, SWEEP_KIND, {**found, "ran_at": at.isoformat()})
    return found


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


async def last_run(db: Any, guild_id: Any) -> dict[str, Any] | None:
    """The newest sweep that had a conversation in front of it, read back off the action log."""
    try:
        cur = await db.conn.execute(
            "SELECT at, details FROM action_log WHERE guild_id = ? AND kind = ? "
            "ORDER BY id DESC LIMIT 1",
            (int(guild_id or 0), SWEEP_KIND),
        )
        row = await cur.fetchone()
    except Exception as exc:
        log.warning("chat memory: the last sweep was not read — %s: %s", type(exc).__name__, exc)
        return None
    if row is None:
        return None
    try:
        details = json.loads(str(row["details"] or "{}"))
    except (TypeError, ValueError):
        details = {}
    found = {**EMPTY_RUN, **(details if isinstance(details, dict) else {})}
    found["at"] = str(found.get("ran_at") or row["at"] or "")
    return found


__all__ = [
    "EMPTY_RUN",
    "Outcome",
    "conversations",
    "distil_one",
    "distiller",
    "expiring",
    "forget_the_old",
    "last_run",
    "member_turns",
    "memory_is_on",
    "run",
    "why_skipped",
    "worth_distilling",
]
