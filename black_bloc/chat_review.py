from __future__ import annotations

import asyncio
import json
import logging
import re
import sqlite3
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from .actionlog import log_action
from .chat import (
    CANNED,
    ChatError,
    add_line,
    clean_name,
    clean_triggers,
    create_intent,
    invalidate,
    list_intents,
    named_intent,
    normalise,
    read_triggers,
    update_intent,
)
from .chat_memory import CONSENT_KEY, OPTOUT, json_object, remembers
from .knowledge import (
    SERVER,
    STAFF,
    KnowledgeError,
    add_section,
    clean_body,
    clean_title,
    list_sections,
    update_section,
)
from .llm import ERROR, GROQ, IMPORTANT, OK, LLMError, record
from .settings_store import (
    REVIEW_ACK_KEY,
    REVIEW_ACK_PHRASES,
    REVIEW_BAD_KIND_KEY,
    REVIEW_BUTTON_KEY,
    REVIEW_DIGEST_HOUR,
    REVIEW_DIGEST_HOUR_KEY,
    REVIEW_DIGEST_KEY,
    REVIEW_DOWNVOTE_EMOJI,
    REVIEW_DOWNVOTE_KEY,
    REVIEW_MODE_KEY,
    REVIEW_NEEDS_LINE_KEY,
    REVIEW_NEEDS_PHRASE_KEY,
    REVIEW_NO_INTENT_KEY,
    REVIEW_NOT_IT_KEY,
    REVIEW_NOT_IT_PHRASES,
    REVIEW_PLACEHOLDER_KEY,
    REVIEW_REASK_KEY,
    REVIEW_REASK_SECONDS,
    REVIEW_REASON_DOWNVOTE_KEY,
    REVIEW_REASON_NOT_IT_KEY,
    REVIEW_REASON_REASK_KEY,
    REVIEW_REASON_UNGROUNDED_KEY,
    REVIEW_SECTION_KEY,
    REVIEW_SUGGEST_INTENT_KEY,
    REVIEW_SUGGEST_KNOWLEDGE_KEY,
    REVIEW_SUGGEST_NONE_KEY,
    REVIEW_SUGGEST_PHRASE_KEY,
    REVIEW_UNTAGGED_KEY,
    REVIEW_WORDS,
)
from .timezones import DEFAULT_TZ, zone

log = logging.getLogger(__name__)

ON = "on"
UNGROUNDED = "ungrounded"
REASK = "reask"
DOWNVOTE = "downvote"
NOT_IT = "not_it"
REASONS: tuple[str, ...] = (UNGROUNDED, REASK, DOWNVOTE, NOT_IT)
REASON_KEYS: dict[str, str] = {
    UNGROUNDED: REVIEW_REASON_UNGROUNDED_KEY,
    REASK: REVIEW_REASON_REASK_KEY,
    DOWNVOTE: REVIEW_REASON_DOWNVOTE_KEY,
    NOT_IT: REVIEW_REASON_NOT_IT_KEY,
}

OPEN = "open"
APPROVED = "approved"
CHANGED = "changed"
DISMISSED = "dismissed"
STATUSES: tuple[str, ...] = (OPEN, APPROVED, CHANGED, DISMISSED)

INTENT = "intent"
PHRASE = "phrase"
KNOWLEDGE = "knowledge"
NONE = "none"
KINDS: tuple[str, ...] = (INTENT, PHRASE, KNOWLEDGE, NONE)
TEACHES: tuple[str, ...] = (INTENT, PHRASE, KNOWLEDGE)

OPENED_KIND = "chat.review_opened"
TAGGED_KIND = "chat.review_tagged"
APPROVED_KIND = "chat.review_approved"
CHANGED_KIND = "chat.review_changed"
DISMISSED_KIND = "chat.review_dismissed"
REOPENED_KIND = "chat.review_reopened"
DIGEST_KIND = "chat.review_digest"

REVIEW_TIER = "review"
SIMPLE_MODEL_KEY = "chat_simple_model"
CAP_KEY = "chat_monthly_cap_usd"
DAILY_KEY = "chat_daily_turns"
TIMEZONE_KEY = "default_timezone"
LOG_CHANNEL_KEY = "log_channel_id"
TEXT_CHARS = 1000
LINE_CHARS = 300
WHY_CHARS = 200
REPLIES_KEPT = 500
TAG_BATCH = 5
INTENTS_SHOWN = 60
TRIGGERS_SHOWN = 12
SECTIONS_SHOWN = 40
MICRODOLLARS = 1_000_000
STATE_ATTR = "_chat_review"
SECTION_ANCHOR = "#sect-review"
NAME_CHARS = 40
NOT_A_NAME = re.compile(r"[^a-z0-9_]+")

UNTAGGED_NO_KEY = "no_key"
UNTAGGED_CAPPED = "capped"
UNTAGGED_OFF = "off"
UNTAGGED_FULL = "full"

TAG_SYSTEM = (
    "You review one exchange between a Discord member and Black Bloc, the server's bot, that "
    "may have gone wrong. Decide the ONE thing the bot should learn so the next person who says "
    "this gets a better answer, and answer with a single JSON object and nothing else:\n"
    '{"kind": "intent"|"phrase"|"knowledge"|"none", "intent": "<name or null>", '
    '"phrase": "<trigger phrase or null>", "line": "<one-line fact or null>", '
    '"section": "<knowledge note heading or null>", "why": "<short reason>"}\n'
    "- phrase: the member meant one of the EXISTING intents listed; intent is its exact name and "
    "phrase is a short trigger (2 to 6 words, lowercase, no punctuation) taken from how they "
    "said it.\n"
    "- intent: nothing listed fits and this will be asked again; intent is a new snake_case "
    "name and phrase is its first trigger.\n"
    "- knowledge: the member asked about a fact of this server the bot did not know; line is "
    "that fact as one plain sentence ONLY if the exchange itself states it, and section is the "
    "listed note heading it belongs under, or null.\n"
    "- none: nothing to learn (a joke, a complaint, small talk, or the answer was fine).\n"
    "Never invent a fact. Never put a person's name, handle or anything private in a phrase or "
    "line."
)
TAG_USER = (
    "Why this was flagged: {reason}\n\nThe member said:\n{asked}\n\nBlack Bloc answered:\n"
    "{answered}\n\nThe intents that exist (name: some of its phrases):\n{intents}\n\n"
    "The knowledge notes that exist:\n{sections}"
)
NOTHING_LISTED = "(none)"
BAD_SHAPE = "the model's answer was not in the shape asked for"


@dataclass(frozen=True)
class Answered:
    guild_id: int
    channel_id: int
    user_id: int
    asked: str
    answered: str
    tier: str | None
    trope: str | None
    intent: str | None
    message_id: int | None
    reply_id: int | None
    at: datetime


@dataclass(frozen=True)
class Suggestion:
    kind: str = NONE
    intent: str | None = None
    phrase: str | None = None
    line: str | None = None
    section: str | None = None
    why: str = ""


@dataclass
class Tracker:
    waiting: dict[tuple[int, int], Answered]
    replies: OrderedDict[int, Answered]
    grounded: dict[tuple[int, int], int]
    tasks: set[Any]


def tracker(bot: Any) -> Tracker:
    found = getattr(bot, STATE_ATTR, None)
    if not isinstance(found, Tracker):
        found = Tracker({}, OrderedDict(), {}, set())
        setattr(bot, STATE_ATTR, found)
    return found


def clipped(text: Any, limit: int = TEXT_CHARS) -> str:
    said = " ".join(str(text or "").split())
    return said if len(said) <= limit else f"{said[: limit - 1]}…"


def setting(store: Any, guild_id: Any, key: str, fallback: Any) -> Any:
    if store is None or guild_id is None:
        return fallback
    try:
        found = store.get(int(guild_id), key)
    except Exception as exc:
        log.warning("chat review: %s was unreadable — %s: %s", key, type(exc).__name__, exc)
        return fallback
    return fallback if found is None else found


def whole(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def is_on(bot: Any, guild_id: Any) -> bool:
    return setting(getattr(bot, "store", None), guild_id, REVIEW_MODE_KEY, "off") == ON


def phrases(value: Any) -> tuple[str, ...]:
    found: list[str] = []
    for one in str(value or "").replace("\n", ",").split(","):
        said = normalise(one)
        if said and said not in found:
            found.append(said)
    return tuple(found)


def says_one_of(text: Any, listed: Any) -> bool:
    words = normalise(text)
    return bool(words) and any(f" {one} " in f" {words} " for one in listed)


def only_an_ack(text: Any, listed: Any) -> bool:
    words = normalise(text)
    if not words:
        return True
    left = f" {words} "
    for one in sorted(listed, key=len, reverse=True):
        while f" {one} " in left:
            left = left.replace(f" {one} ", " ")
    return not left.strip()


def words(store: Any, guild_id: Any, key: str, **values: Any) -> str:
    """Staff's wording, or the registry's when theirs will not format."""
    try:
        return str(setting(store, guild_id, key, REVIEW_WORDS[key][0])).format(**values)
    except Exception as exc:
        log.warning("chat review: %s would not format, so the default was said — %s", key, exc)
        return REVIEW_WORDS[key][0].format(**values)


def reason_word(store: Any, guild_id: Any, reason: Any) -> str:
    key = REASON_KEYS.get(str(reason))
    return words(store, guild_id, key) if key else str(reason)


def note_grounding(bot: Any, channel_id: Any, user_id: Any, hits: Any) -> None:
    """What the careful tier had to go on, read once by `answered` right after the reply."""
    try:
        count = len(hits or ())
    except TypeError:
        count = 0
    tracker(bot).grounded[(int(channel_id or 0), int(user_id or 0))] = count


async def keeps_text(bot: Any, guild_id: int, user_id: int) -> bool:
    """The memory opt-out, read the way `/memory` reads it; unreadable means no."""
    consent = setting(bot.store, guild_id, CONSENT_KEY, OPTOUT)
    return await remembers(bot.db, user_id, guild_id, consent=consent)


async def open_item(bot: Any, one: Answered, reason: str) -> int | None:
    """One review row per bot reply; an opted-out person leaves nothing behind."""
    db = usable_db(bot)
    if db is None or not is_on(bot, one.guild_id):
        return None
    if not await keeps_text(bot, one.guild_id, one.user_id):
        return None
    try:
        cur = await db.conn.execute(
            "INSERT OR IGNORE INTO chat_review(guild_id, channel_id, user_id, asked, answered, "
            "tier, trope, intent, reason, message_id, reply_id, at, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                one.guild_id,
                one.channel_id,
                one.user_id,
                clipped(one.asked),
                clipped(one.answered),
                one.tier,
                one.trope,
                one.intent,
                reason,
                one.message_id,
                one.reply_id,
                datetime.now(UTC).isoformat(),
                OPEN,
            ),
        )
        await db.conn.commit()
    except Exception as exc:
        log.warning("chat review: an item was not opened — %s: %s", type(exc).__name__, exc)
        return None
    if not cur.rowcount:
        return None
    made = int(cur.lastrowid)
    guild = guild_of(bot, one.guild_id)
    if guild is not None:
        await log_action(
            bot,
            guild,
            OPENED_KIND,
            target=one.user_id,
            details={"id": made, "reason": reason, "tier": one.tier, "intent": one.intent},
        )
    schedule_tag(bot, made)
    return made


def usable_db(bot: Any) -> Any:
    db = getattr(bot, "db", None)
    return db if db is not None and getattr(db, "is_connected", False) else None


def guild_of(bot: Any, guild_id: Any) -> Any:
    getter = getattr(bot, "get_guild", None)
    return getter(int(guild_id)) if getter is not None and guild_id is not None else None


def schedule_tag(bot: Any, item_id: int) -> None:
    """Tagging never holds up a reply; the review tick picks up anything this misses."""
    try:
        task = asyncio.get_running_loop().create_task(tag_one(bot, item_id))
    except RuntimeError:
        return
    held = tracker(bot).tasks
    held.add(task)
    task.add_done_callback(held.discard)


async def answered(
    bot: Any,
    message: Any,
    reply: Any,
    said: Any,
    *,
    now: datetime | None = None,
) -> int | None:
    """Remember the answer for the follow-up checks, and queue it when nothing grounded it."""
    guild_id = getattr(getattr(message, "guild", None), "id", None)
    channel_id = int(getattr(getattr(message, "channel", None), "id", 0) or 0)
    user_id = int(getattr(getattr(message, "author", None), "id", 0) or 0)
    found = tracker(bot)
    hits = found.grounded.pop((channel_id, user_id), None)
    if guild_id is None or not is_on(bot, guild_id):
        return None
    one = Answered(
        guild_id=int(guild_id),
        channel_id=channel_id,
        user_id=user_id,
        asked=str(getattr(message, "content", "") or ""),
        answered=str(getattr(said, "text", "") or ""),
        tier=getattr(said, "tier", None),
        trope=getattr(said, "trope", None),
        intent=getattr(said, "intent", None),
        message_id=getattr(message, "id", None),
        reply_id=getattr(reply, "id", None),
        at=now or datetime.now(UTC),
    )
    found.waiting[(channel_id, user_id)] = one
    if one.reply_id is not None:
        found.replies[int(one.reply_id)] = one
        while len(found.replies) > REPLIES_KEPT:
            found.replies.popitem(last=False)
    if one.tier == IMPORTANT and hits == 0:
        return await open_item(bot, one, UNGROUNDED)
    return None


async def heard(bot: Any, message: Any, *, now: datetime | None = None) -> int | None:
    """The same person's next message in the same place, weighed against the last answer."""
    guild_id = getattr(getattr(message, "guild", None), "id", None)
    if guild_id is None:
        return None
    channel_id = int(getattr(getattr(message, "channel", None), "id", 0) or 0)
    user_id = int(getattr(getattr(message, "author", None), "id", 0) or 0)
    waiting = tracker(bot).waiting
    last = waiting.get((channel_id, user_id))
    if last is None or last.message_id == getattr(message, "id", None):
        return None
    waiting.pop((channel_id, user_id), None)
    if not is_on(bot, guild_id):
        return None
    store = bot.store
    seconds = whole(setting(store, guild_id, REVIEW_REASK_KEY, REVIEW_REASK_SECONDS), 0)
    at = now or datetime.now(UTC)
    text = getattr(message, "content", "")
    not_it = phrases(setting(store, guild_id, REVIEW_NOT_IT_KEY, REVIEW_NOT_IT_PHRASES))
    gap = at - last.at
    if says_one_of(text, not_it) and gap <= timedelta(seconds=max(seconds, REVIEW_REASK_SECONDS)):
        return await open_item(bot, last, NOT_IT)
    if seconds <= 0 or gap > timedelta(seconds=seconds):
        return None
    if only_an_ack(text, phrases(setting(store, guild_id, REVIEW_ACK_KEY, REVIEW_ACK_PHRASES))):
        return None
    return await open_item(bot, last, REASK)


def same_emoji(given: Any, wanted: Any) -> bool:
    said = str(wanted or "").strip()
    if not said:
        return False
    found = str(given or "")
    return found == said or found.replace("️", "") == said.replace("️", "")


async def reacted(bot: Any, payload: Any) -> int | None:
    """A thumbs down on one of Black Bloc's own recent chat answers, by anybody but the bot."""
    guild_id = getattr(payload, "guild_id", None)
    me = getattr(getattr(bot, "user", None), "id", None)
    if guild_id is None or getattr(payload, "user_id", None) == me:
        return None
    one = tracker(bot).replies.get(int(getattr(payload, "message_id", 0) or 0))
    if one is None or not is_on(bot, guild_id):
        return None
    wanted = setting(bot.store, guild_id, REVIEW_DOWNVOTE_KEY, REVIEW_DOWNVOTE_EMOJI)
    if not same_emoji(getattr(payload, "emoji", ""), wanted):
        return None
    return await open_item(bot, one, DOWNVOTE)


async def get_item(db: Any, item_id: Any) -> Any:
    try:
        wanted = int(item_id)
    except (TypeError, ValueError):
        return None
    cur = await db.conn.execute("SELECT * FROM chat_review WHERE id = ?", (wanted,))
    return await cur.fetchone()


async def list_items(
    db: Any, guild_id: int, *, status: str | None = OPEN, reason: str | None = None
) -> list[Any]:
    sql = "SELECT * FROM chat_review WHERE guild_id = ?"
    values: list[Any] = [int(guild_id)]
    if status:
        sql += " AND status = ?"
        values.append(status)
    if reason:
        sql += " AND reason = ?"
        values.append(reason)
    cur = await db.conn.execute(f"{sql} ORDER BY id DESC", values)
    return list(await cur.fetchall())


async def counts(db: Any, guild_id: int) -> dict[str, int]:
    found = {status: 0 for status in STATUSES}
    cur = await db.conn.execute(
        "SELECT status, COUNT(*) AS n FROM chat_review WHERE guild_id = ? GROUP BY status",
        (int(guild_id),),
    )
    for row in await cur.fetchall():
        found[str(row["status"])] = int(row["n"])
    cur = await db.conn.execute(
        "SELECT COUNT(*) AS n FROM chat_review WHERE guild_id = ? AND status = ? AND "
        "tagged_at IS NULL",
        (int(guild_id), OPEN),
    )
    row = await cur.fetchone()
    found["untagged"] = int(row["n"]) if row is not None else 0
    return found


async def month_spent(db: Any, now: datetime) -> int:
    since = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    cur = await db.conn.execute(
        "SELECT SUM(cost_microdollars) AS spent FROM llm_ledger WHERE at >= ?", (since,)
    )
    row = await cur.fetchone()
    return int((row["spent"] if row is not None else 0) or 0)


async def turns_today(db: Any, now: datetime) -> int:
    since = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    cur = await db.conn.execute(
        "SELECT COUNT(DISTINCT turn) AS n FROM llm_ledger WHERE at >= ?", (since,)
    )
    row = await cur.fetchone()
    return int((row["n"] if row is not None else 0) or 0)


async def why_untagged(bot: Any, guild_id: int, *, now: datetime | None = None) -> str | None:
    """None when the cheap model may tag now; otherwise the one reason it may not."""
    if not is_on(bot, guild_id):
        return UNTAGGED_OFF
    if not getattr(bot.settings, "simple_tier_configured", False):
        return UNTAGGED_NO_KEY
    at = now or datetime.now(UTC)
    cap = whole(setting(bot.store, guild_id, CAP_KEY, 0), 0)
    if await month_spent(bot.db, at) >= cap * MICRODOLLARS:
        return UNTAGGED_CAPPED
    daily = whole(setting(bot.store, guild_id, DAILY_KEY, 0), 0)
    if daily and await turns_today(bot.db, at) >= daily:
        return UNTAGGED_FULL
    return None


def intents_text(rows: Any) -> str:
    found = []
    for row in list(rows or ())[:INTENTS_SHOWN]:
        if not row["enabled"]:
            continue
        said = ", ".join(read_triggers(row["triggers"])[:TRIGGERS_SHOWN])
        found.append(f"{row['name']}: {said}")
    return "\n".join(found) or NOTHING_LISTED


def sections_text(rows: Any) -> str:
    found = [str(row["title"]) for row in list(rows or ()) if str(row["source"]) == STAFF]
    return "\n".join(found[:SECTIONS_SHOWN]) or NOTHING_LISTED


def tag_prompt(item: Any, intents: Any, sections: Any) -> tuple[str, list[dict[str, str]]]:
    said = TAG_USER.format(
        reason=str(item["reason"]),
        asked=str(item["asked"]),
        answered=str(item["answered"]),
        intents=intents_text(intents),
        sections=sections_text(sections),
    )
    return (TAG_SYSTEM, [{"role": "user", "content": said}])


def text_or_none(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError
    said = " ".join(value.split())
    if len(said) > limit:
        raise ValueError
    return said or None


def made_name(value: Any, phrase: str) -> str:
    base = str(value or "") or phrase
    said = NOT_A_NAME.sub("_", base.strip().lower().replace(" ", "_").replace("-", "_"))
    said = said.strip("_")[:NAME_CHARS].strip("_")
    if not said or not said[0].isalpha():
        said = f"asked_{said}".strip("_")[:NAME_CHARS]
    return said


def parse_tag(text: Any, intents: Any) -> Suggestion:
    """The strict shape or `none`; a name the server does not have never survives."""
    found = json_object(text)
    if found is None or not isinstance(found.get("kind"), str):
        return Suggestion(why=BAD_SHAPE)
    kind = found["kind"].strip().lower()
    if kind not in KINDS:
        return Suggestion(why=BAD_SHAPE)
    try:
        intent = text_or_none(found.get("intent"), 60)
        phrase = text_or_none(found.get("phrase"), 60)
        line = text_or_none(found.get("line"), LINE_CHARS)
        section = text_or_none(found.get("section"), 100)
        why = text_or_none(found.get("why"), 1000) or ""
    except ValueError:
        return Suggestion(why=BAD_SHAPE)
    why = clipped(why, WHY_CHARS)
    names = {str(row["name"]).lower(): str(row["name"]) for row in intents or ()}
    phrase = normalise(phrase) if phrase else None
    if kind == NONE:
        return Suggestion(why=why)
    if kind == KNOWLEDGE:
        if not line:
            return Suggestion(why=BAD_SHAPE)
        return Suggestion(KNOWLEDGE, line=line, section=section, why=why)
    if not phrase:
        return Suggestion(why=BAD_SHAPE)
    existing = names.get(str(intent or "").lower())
    if existing is not None:
        return Suggestion(PHRASE, intent=existing, phrase=phrase, why=why)
    if kind == PHRASE:
        return Suggestion(why=BAD_SHAPE)
    return Suggestion(INTENT, intent=made_name(intent, phrase), phrase=phrase, why=why)


async def save_suggestion(db: Any, item_id: int, found: Suggestion, intents: Any) -> None:
    ids = {str(row["name"]): int(row["id"]) for row in intents or ()}
    await db.conn.execute(
        "UPDATE chat_review SET suggested_kind = ?, suggested_intent = ?, "
        "suggested_intent_id = ?, suggested_phrase = ?, suggested_line = ?, "
        "suggested_section = ?, suggested_why = ?, tagged_at = ? WHERE id = ?",
        (
            found.kind,
            found.intent,
            ids.get(str(found.intent)) if found.kind == PHRASE else None,
            found.phrase,
            found.line,
            found.section,
            found.why,
            datetime.now(UTC).isoformat(),
            int(item_id),
        ),
    )
    await db.conn.commit()


async def tag_one(bot: Any, item_id: int, *, now: datetime | None = None) -> str | None:
    """One capped call to the cheap model; the answer is a suggestion, never a write."""
    db = usable_db(bot)
    if db is None:
        return None
    item = await get_item(db, item_id)
    if item is None or item["tagged_at"] is not None or item["status"] != OPEN:
        return None
    guild_id = int(item["guild_id"])
    at = now or datetime.now(UTC)
    held = await why_untagged(bot, guild_id, now=at)
    if held is not None:
        log.info("chat review: item %s waits untagged (%s)", item_id, held)
        return None
    from .chat_llm import groq

    model = str(setting(bot.store, guild_id, SIMPLE_MODEL_KEY, "") or "")
    client = groq(bot, model, REVIEW_TIER)
    if client is None:
        return None
    intents = await list_intents(db, guild_id)
    system, messages = tag_prompt(item, intents, await list_sections(db, guild_id))
    turn = uuid.uuid4().hex
    try:
        reply = await client.reply(system=system, messages=messages, json_only=True)
    except LLMError as exc:
        await record(
            db,
            guild_id=guild_id,
            user_id=None,
            turn=turn,
            provider=GROQ,
            model=client.model,
            tier=REVIEW_TIER,
            outcome=ERROR,
            at=at,
        )
        log.warning("chat review: the cheap model did not tag %s — %s", item_id, exc.reason)
        return None
    await record(
        db,
        guild_id=guild_id,
        user_id=None,
        turn=turn,
        provider=reply.provider,
        model=reply.model,
        tier=REVIEW_TIER,
        outcome=OK,
        usage=reply.usage,
        at=at,
    )
    found = parse_tag(reply.text, intents)
    if found.why == BAD_SHAPE:
        log.warning("chat review: item %s was answered out of shape: %r", item_id, reply.text[:200])
    await save_suggestion(db, int(item_id), found, intents)
    guild = guild_of(bot, guild_id)
    if guild is not None:
        await log_action(
            bot,
            guild,
            TAGGED_KIND,
            details={
                "id": int(item_id),
                "kind": found.kind,
                "intent": found.intent,
                "phrase": found.phrase,
                "section": found.section,
                "why": found.why,
            },
        )
    return found.kind


async def tag_waiting(bot: Any, *, limit: int = TAG_BATCH, now: datetime | None = None) -> int:
    """A small batch of open, untagged items; stops at the first one the cap holds back."""
    db = usable_db(bot)
    if db is None:
        return 0
    cur = await db.conn.execute(
        "SELECT id, guild_id FROM chat_review WHERE status = ? AND tagged_at IS NULL "
        "ORDER BY id LIMIT ?",
        (OPEN, int(limit)),
    )
    done = 0
    for row in await cur.fetchall():
        if await why_untagged(bot, int(row["guild_id"]), now=now) is not None:
            continue
        if await tag_one(bot, int(row["id"]), now=now) is not None:
            done += 1
    return done


def suggestion_of(row: Any) -> Suggestion | None:
    if row["tagged_at"] is None:
        return None
    return Suggestion(
        kind=str(row["suggested_kind"] or NONE),
        intent=row["suggested_intent"],
        phrase=row["suggested_phrase"],
        line=row["suggested_line"],
        section=row["suggested_section"],
        why=str(row["suggested_why"] or ""),
    )


def suggestion_word(store: Any, guild_id: Any, found: Suggestion | None) -> str:
    if found is None:
        return words(store, guild_id, REVIEW_UNTAGGED_KEY)
    if found.kind == PHRASE:
        return words(
            store, guild_id, REVIEW_SUGGEST_PHRASE_KEY, phrase=found.phrase, intent=found.intent
        )
    if found.kind == INTENT:
        return words(
            store, guild_id, REVIEW_SUGGEST_INTENT_KEY, intent=found.intent, phrase=found.phrase
        )
    if found.kind == KNOWLEDGE:
        return words(
            store,
            guild_id,
            REVIEW_SUGGEST_KNOWLEDGE_KEY,
            section=found.section or words(store, guild_id, REVIEW_SECTION_KEY),
            line=found.line,
        )
    return words(store, guild_id, REVIEW_SUGGEST_NONE_KEY)


@dataclass(frozen=True)
class Taught:
    kind: str
    intent: str | None = None
    phrase: str | None = None
    section: str | None = None
    made: bool = False
    section_id: int | None = None
    intent_id: int | None = None


class ReviewError(ValueError):
    """A change a review cannot write: a keyed sentence, or the helper's own words in `said`."""

    def __init__(self, key: str = "", *, said: str = "", **values: Any) -> None:
        super().__init__(key or said)
        self.key = key
        self.said = said
        self.values = values


async def add_phrase(bot: Any, guild_id: int, name: str, phrase: str) -> Taught:
    row = await named_intent(bot.db, guild_id, name)
    if row is None:
        raise ReviewError(REVIEW_NO_INTENT_KEY, intent=name)
    try:
        triggers = clean_triggers([*read_triggers(row["triggers"]), phrase])
    except ChatError as exc:
        raise ReviewError(said=str(exc)) from exc
    await update_intent(bot.db, int(row["id"]), triggers=triggers)
    invalidate(bot, guild_id)
    return Taught(PHRASE, intent=str(row["name"]), phrase=phrase, intent_id=int(row["id"]))


async def make_intent(bot: Any, guild_id: int, name: str, phrase: str, by: Any) -> Taught:
    try:
        wanted = clean_name(name)
        triggers = clean_triggers([phrase])
    except ChatError as exc:
        raise ReviewError(said=str(exc)) from exc
    if await named_intent(bot.db, guild_id, wanted) is not None:
        return await add_phrase(bot, guild_id, wanted, phrase)
    try:
        made = await create_intent(bot.db, guild_id, wanted, triggers, kind=CANNED, by=by)
    except sqlite3.IntegrityError:
        return await add_phrase(bot, guild_id, wanted, phrase)
    await add_line(
        bot.db,
        made,
        words(bot.store, guild_id, REVIEW_PLACEHOLDER_KEY),
        enabled=False,
        by=by,
    )
    invalidate(bot, guild_id)
    return Taught(INTENT, intent=wanted, phrase=triggers[0], made=True, intent_id=made)


async def add_fact(bot: Any, guild_id: int, line: str, section: Any, by: Any) -> Taught:
    fallback = words(bot.store, guild_id, REVIEW_SECTION_KEY)
    try:
        title = clean_title(section or fallback)
    except KnowledgeError:
        title = clean_title(fallback)
    rows = await list_sections(bot.db, guild_id)
    mine = {str(row["title"]).lower(): row for row in rows if str(row["source"]) == STAFF}
    theirs = {str(row["title"]).lower() for row in rows if str(row["source"]) == SERVER}
    if title.lower() in theirs and title.lower() not in mine:
        title = clean_title(fallback)
    row = mine.get(title.lower())
    try:
        if row is None:
            made = await add_section(bot.db, guild_id, title, clean_body(line), by=by)
            return Taught(KNOWLEDGE, section=title, section_id=made)
        body = clean_body(f"{str(row['body']).rstrip()}\n{line}")
        await update_section(bot.db, int(row["id"]), body=body, by=by)
    except KnowledgeError as exc:
        raise ReviewError(said=str(exc)) from exc
    return Taught(KNOWLEDGE, section=str(row["title"]), section_id=int(row["id"]))


async def teach(bot: Any, guild_id: int, found: Suggestion, by: Any) -> Taught:
    """The one place a review becomes an intent, a phrase or a fact."""
    if found.kind not in TEACHES:
        raise ReviewError(REVIEW_BAD_KIND_KEY, kind=str(found.kind)[:40])
    if found.kind == KNOWLEDGE:
        line = " ".join(str(found.line or "").split())
        if not line:
            raise ReviewError(REVIEW_NEEDS_LINE_KEY)
        return await add_fact(bot, guild_id, line, found.section, by)
    phrase = " ".join(str(found.phrase or "").split())
    if not phrase:
        raise ReviewError(REVIEW_NEEDS_PHRASE_KEY)
    if found.kind == PHRASE:
        return await add_phrase(bot, guild_id, str(found.intent or ""), phrase)
    return await make_intent(bot, guild_id, made_name(found.intent, phrase), phrase, by)


async def decide(db: Any, item_id: int, status: str, by: Any) -> bool:
    """Only an open item is decided, so two staff pressing at once write once."""
    cur = await db.conn.execute(
        "UPDATE chat_review SET status = ?, decided_by = ?, decided_at = ? "
        "WHERE id = ? AND status = ?",
        (status, by, datetime.now(UTC).isoformat(), int(item_id), OPEN),
    )
    await db.conn.commit()
    return bool(cur.rowcount)


async def record_change(db: Any, item_id: int, found: Suggestion) -> None:
    """What staff wrote in place of the suggestion, so the row says what was learned."""
    await db.conn.execute(
        "UPDATE chat_review SET suggested_kind = ?, suggested_intent = ?, suggested_phrase = ?, "
        "suggested_line = ?, suggested_section = ? WHERE id = ?",
        (found.kind, found.intent, found.phrase, found.line, found.section, int(item_id)),
    )
    await db.conn.commit()


async def undecide(db: Any, item_id: int, status: str) -> None:
    await db.conn.execute(
        "UPDATE chat_review SET status = ?, decided_by = NULL, decided_at = NULL "
        "WHERE id = ? AND status = ?",
        (OPEN, int(item_id), status),
    )
    await db.conn.commit()


async def reopen(db: Any, item_id: int) -> bool:
    cur = await db.conn.execute(
        "UPDATE chat_review SET status = ?, decided_by = NULL, decided_at = NULL "
        "WHERE id = ? AND status = ?",
        (OPEN, int(item_id), DISMISSED),
    )
    await db.conn.commit()
    return bool(cur.rowcount)


def chat_link(bot: Any, guild_id: Any) -> str:
    from .chat_panel import site_page_url

    url = site_page_url(getattr(getattr(bot, "settings", None), "origin", ""))
    if url:
        return f"{url}{SECTION_ANCHOR}"
    return f"/chat ▸ {words(bot.store, guild_id, REVIEW_BUTTON_KEY)}"


def local_now(bot: Any, guild_id: int, now: datetime) -> datetime:
    name = setting(bot.store, guild_id, TIMEZONE_KEY, DEFAULT_TZ)
    return now.astimezone(zone(name) or zone(DEFAULT_TZ) or UTC)


async def digest_sent_since(db: Any, guild_id: int, since: datetime) -> bool:
    cur = await db.conn.execute(
        "SELECT COUNT(*) AS n FROM action_log WHERE guild_id = ? AND kind = ? AND at >= ?",
        (int(guild_id), DIGEST_KIND, since.astimezone(UTC).isoformat()),
    )
    row = await cur.fetchone()
    return bool(row is not None and int(row["n"]))


async def digest(bot: Any, guild: Any, *, now: datetime | None = None) -> bool:
    """One line a local day, at the set hour, and only while something waits."""
    db = usable_db(bot)
    if db is None or guild is None or not is_on(bot, guild.id):
        return False
    at = now or datetime.now(UTC)
    local = local_now(bot, guild.id, at)
    hour = whole(setting(bot.store, guild.id, REVIEW_DIGEST_HOUR_KEY, REVIEW_DIGEST_HOUR), 9)
    if local.hour < hour:
        return False
    day = local.replace(hour=0, minute=0, second=0, microsecond=0)
    if await digest_sent_since(db, guild.id, day):
        return False
    waiting = (await counts(db, guild.id))[OPEN]
    if not waiting:
        return False
    text = words(
        bot.store, guild.id, REVIEW_DIGEST_KEY, count=waiting, link=chat_link(bot, guild.id)
    )
    posted = await post_line(bot, guild, text)
    await log_action(
        bot, guild, DIGEST_KIND, details={"open": waiting, "posted": posted, "day": str(day.date())}
    )
    return posted


async def post_line(bot: Any, guild: Any, text: str) -> bool:
    import discord

    channel_id = setting(bot.store, guild.id, LOG_CHANNEL_KEY, None)
    channel = guild.get_channel(int(channel_id)) if channel_id else None
    if channel is None:
        log.warning("chat review: the digest was not posted — no log channel is set or visible")
        return False
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel):
        log.info("chat review: test mode, so the digest was not posted in %s", channel_id)
        return False
    try:
        await channel.send(text, allowed_mentions=discord.AllowedMentions.none())
    except Exception as exc:
        log.warning("chat review: the digest was not posted — %s: %s", type(exc).__name__, exc)
        return False
    return True


def markdown(bot: Any, guild_id: int, rows: Any, *, now: datetime | None = None) -> str:
    """The open queue as one document a scheduled reader can work through."""
    store = bot.store
    at = (now or datetime.now(UTC)).isoformat(timespec="minutes")
    lines = [f"# Chat review queue — {len(list(rows))} open", "", f"Exported {at} UTC.", ""]
    for row in rows:
        found = suggestion_of(row)
        lines += [
            f"## Item {int(row['id'])} — {reason_word(store, guild_id, row['reason'])}",
            "",
            f"- when: {row['at']}",
            f"- tier: {row['tier'] or 'written line'} · intent matched: {row['intent'] or '-'}",
            f"- asked: {json.dumps(str(row['asked']), ensure_ascii=False)}",
            f"- answered: {json.dumps(str(row['answered']), ensure_ascii=False)}",
            f"- suggestion: {strip_marks(suggestion_word(store, guild_id, found))}",
        ]
        if found is not None and found.why:
            lines.append(f"- why: {found.why}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def strip_marks(text: str) -> str:
    return str(text).replace("**", "")


__all__ = [
    "APPROVED",
    "CHANGED",
    "DISMISSED",
    "DOWNVOTE",
    "KINDS",
    "NOT_IT",
    "OPEN",
    "REASK",
    "REASONS",
    "STATUSES",
    "UNGROUNDED",
    "Answered",
    "ReviewError",
    "Suggestion",
    "Taught",
    "answered",
    "counts",
    "decide",
    "digest",
    "get_item",
    "heard",
    "list_items",
    "markdown",
    "note_grounding",
    "open_item",
    "parse_tag",
    "reacted",
    "record_change",
    "reopen",
    "suggestion_of",
    "suggestion_word",
    "tag_one",
    "tag_waiting",
    "teach",
    "undecide",
    "why_untagged",
]
