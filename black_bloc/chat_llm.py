from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from .actionlog import log_action
from .channel_notes import notes_or_nothing
from .chat import MENTION, has_phrase, normalise
from .chat_check import FIXED_KIND, check_reply
from .chat_voice import heard_for
from .directory import DIRECTORY_NONE, directory_block
from .groq import GroqClient
from .knowledge import grounding, is_strong, list_sections, search
from .llm import (
    ANTHROPIC,
    ERROR,
    GROQ,
    IMPORTANT,
    MODEL,
    OK,
    SIMPLE,
    HaikuClient,
    LLMError,
    record,
)
from .personas import (
    COOKOUT,
    COOKOUT_VOICE,
    COOKOUT_VOICE_KEY,
    PERSONALITY_KEY,
    TONE_CLAUSE,
    TONE_CLAUSE_KEY,
    Trope,
    pick_trope,
    pooled,
    system_blocks,
    system_text,
)
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
REPLY_KIND = "chat.llm_reply"
ERROR_KIND = "chat.llm_error"

ON = "on"
LLM_MODE_KEY = "chat_llm_mode"
SIMPLE_MODEL_KEY = "chat_simple_model"
REPLY_LIMIT = 1900
NOTHING: tuple[None, None, None] = (None, None, None)
CLIENTS_ATTR = "_chat_clients"
ERRORS_ATTR = "_chat_tier_errors"

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

PEOPLE_OPENER = (
    "(Who they pointed at, from the server itself — this is the truth about them, so say this "
    "and nothing more about them:"
)
PEOPLE_CLOSER = ")"

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
    if is_strong(hits):
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


async def last_turn_at(db: Any) -> str | None:
    try:
        cur = await db.conn.execute("SELECT MAX(at) FROM llm_ledger")
        row = await cur.fetchone()
    except Exception as exc:
        log.warning("chat: the ledger's last turn could not be read — %s", exc)
        return None
    found = row[0] if row is not None else None
    return str(found) if found else None


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


def tier_errors(bot: Any) -> dict[str, str]:
    """What each tier's last call did, so the `/chat` panel can say a tier is down."""
    found = getattr(bot, ERRORS_ATTR, None)
    if not isinstance(found, dict):
        found = {}
        setattr(bot, ERRORS_ATTR, found)
    return found


def clients_for(bot: Any) -> dict[str, Any]:
    """One client per tier, built once. A key that is not set is a tier that is not here."""
    found = getattr(bot, CLIENTS_ATTR, None)
    if not isinstance(found, dict):
        found = {}
        setattr(bot, CLIENTS_ATTR, found)
    return found


def haiku(bot: Any) -> Any:
    settings = bot.settings
    if not settings.important_tier_configured:
        return None
    made = clients_for(bot)
    if IMPORTANT not in made:
        made[IMPORTANT] = HaikuClient(settings.anthropic_api_key)
    return made[IMPORTANT]


def groq(bot: Any, model: str, slot: str = SIMPLE) -> Any:
    """Rebuilt when the model setting changes; one slot per caller, so two models never thrash."""
    settings = bot.settings
    if not settings.simple_tier_configured:
        return None
    made = clients_for(bot)
    found = made.get(slot)
    if found is None or found.model != model:
        found = GroqClient(settings.groq_api_key, model=model)
        made[slot] = found
    return found


def read_setting(store: Any, guild_id: Any, key: str, fallback: Any) -> Any:
    if store is None or guild_id is None:
        return fallback
    try:
        found = store.get(int(guild_id), key)
    except Exception as exc:
        log.warning("chat: %s was unreadable — %s: %s", key, type(exc).__name__, exc)
        return fallback
    return fallback if found is None else found


def llm_is_on(bot: Any, guild_id: Any) -> bool:
    """Affirmative only: off, unreadable, or a DM all mean the models are not in play."""
    store = getattr(bot, "store", None)
    if store is None or guild_id is None:
        return False
    return read_setting(store, guild_id, LLM_MODE_KEY, "off") == ON


def usable_db(bot: Any) -> Any:
    db = getattr(bot, "db", None)
    return db if db is not None and getattr(db, "is_connected", False) else None


async def hits_for(db: Any, guild_id: Any, text: Any) -> Any:
    if guild_id is None:
        return ()
    try:
        return search(await list_sections(db, int(guild_id)), spoken(text))
    except Exception as exc:
        log.warning("chat: the notes were not searched — %s: %s", type(exc).__name__, exc)
        return ()


def people_note(notes: Any) -> str:
    found = [str(one) for one in notes or () if str(one).strip()]
    return f"{PEOPLE_OPENER} {' · '.join(found)}{PEOPLE_CLOSER}" if found else ""


def who_they_named(bot: Any, guild: Any, text: Any) -> list[tuple[str, str]]:
    from .chat_data import member_notes

    if guild is None:
        return []
    try:
        return member_notes(bot, guild, text)
    except Exception as exc:
        log.warning("chat: the people named were not read — %s: %s", type(exc).__name__, exc)
        return []


def user_turn(text: Any, hits: Any, notes: Any = (), memory: Any = "") -> str:
    said = spoken(text)
    parts = [said, grounding(hits), people_note(notes), str(memory or "")]
    return "\n\n".join(one for one in parts if one)


async def memory_for(bot: Any, db: Any, guild_id: Any, user_id: int, *, in_dm: bool) -> str:
    """One indexed SELECT on the reply path, and nothing at all when memory is off."""
    from .chat_memory import (
        DM_SCOPE_KEY,
        MODE_KEY,
        SHARED,
        memory_note,
        profile_for,
    )

    home = guild_id if guild_id is not None else getattr(bot.settings, "dev_guild_id", None)
    if home is None or read_setting(bot.store, home, MODE_KEY, "off") != ON:
        return ""
    shared = read_setting(bot.store, home, DM_SCOPE_KEY, "") == SHARED
    return memory_note(await profile_for(db, user_id, home), in_dm=in_dm, shared=shared)


async def say_capped(bot: Any, guild: Any, at: datetime) -> None:
    db = usable_db(bot)
    guild_id = getattr(guild, "id", None)
    if db is None or guild_id is None:
        return
    if await capped_already_logged(db, guild_id, month_start(at)):
        return
    await log_action(bot, guild, CAPPED_KIND, details={"month": month_start(at)[:7]})


async def try_tier(
    bot: Any,
    name: str,
    *,
    model_setting: str,
    system: Any,
    messages: Any,
    directory: str = "",
    sheet: Any = None,
    clause_text: Any = None,
) -> Any:
    client = haiku(bot) if name == IMPORTANT else groq(bot, model_setting)
    if client is None:
        return None
    words = {"sheet": sheet, "clause_text": clause_text}
    if name == IMPORTANT:
        return await client.reply(
            system=system_blocks(system, directory, **words), messages=messages
        )
    return await client.reply(system=system_text(system, directory, **words), messages=messages)


async def mood_for(
    bot: Any, db: Any, guild_id: Any, channel_id: Any, user_id: int, window: Any, at: datetime
) -> Trope | None:
    """A DM keeps the per-conversation roll; in a server the tone follows the member."""
    setting = read_setting(bot.store, guild_id, PERSONALITY_KEY, COOKOUT)
    rows = await pooled(bot)
    if guild_id is None:
        return pick_trope(
            setting, rows, key=window_key(channel_id, user_id), turns=llm_turns(window)
        )
    heard = await heard_for(db, setting, rows, guild_id=guild_id, user_id=user_id, now=at)
    return heard.trope


async def made_real(bot: Any, guild: Any, text: Any, people: Any = ()) -> str:
    """A named channel or role the server does not have never reaches anybody."""
    said = str(text or "")
    if guild is None:
        return said
    try:
        found = check_reply(bot, guild, said, people)
    except Exception as exc:
        log.warning("chat: the reply was not checked — %s: %s", type(exc).__name__, exc)
        return said
    if not found.fixed:
        return said
    log.info(
        "chat: a reply named %s that this server does not have",
        ", ".join([*found.channels, *found.roles]),
    )
    await log_action(
        bot,
        guild,
        FIXED_KIND,
        details={
            "channels": found.channels,
            "roles": found.roles,
            "fixed": found.fixed,
        },
    )
    return found.text


def channels_block(bot: Any, guild: Any, notes: Any = None) -> str:
    """Built fresh for every call: a channel made this morning is in this afternoon's answer."""
    if guild is None:
        return DIRECTORY_NONE
    try:
        return directory_block(bot, guild, notes)
    except Exception as exc:
        log.warning("chat: the channel list was not built — %s: %s", type(exc).__name__, exc)
        return DIRECTORY_NONE


async def conversational_reply(
    bot: Any, *, guild: Any, member: Any, channel: Any, text: Any
) -> tuple[str | None, str | None, str | None]:
    """The whole second rung: knowledge, tier, one or two calls, and the ledger for each."""
    guild_id = getattr(guild, "id", None)
    if not llm_is_on(bot, guild_id):
        return NOTHING
    db = usable_db(bot)
    if db is None:
        return NOTHING
    settings = bot.settings
    important, simple = settings.important_tier_configured, settings.simple_tier_configured
    if not (important or simple):
        return NOTHING

    at = datetime.now(UTC)
    user_id = int(getattr(member, "id", 0) or 0)
    channel_id = getattr(channel, "id", None)
    spent = await allowance(db, bot.store, guild_id, user_id, now=at)
    if not spent.ok:
        if spent.why == CAPPED:
            await say_capped(bot, guild, at)
        log.info("chat: the models are closed for now (%s)", spent.why)
        return NOTHING

    window = await window_for(db, channel_id, user_id, now=at)
    hits = await hits_for(db, guild_id, text)
    tier = tier_for(text, hits, window)
    order = ladder(tier, important=important, simple=simple)
    if not order:
        return NOTHING

    voice = await mood_for(bot, db, guild_id, channel_id, user_id, window, at)
    tone = voice.name if voice is not None else COOKOUT
    sheet = read_setting(bot.store, guild_id, COOKOUT_VOICE_KEY, COOKOUT_VOICE)
    clause_text = read_setting(bot.store, guild_id, TONE_CLAUSE_KEY, TONE_CLAUSE)
    model_setting = str(read_setting(bot.store, guild_id, SIMPLE_MODEL_KEY, "") or "")
    named = who_they_named(bot, guild, text)
    remembered = await memory_for(bot, db, guild_id, user_id, in_dm=guild_id is None)
    asked = user_turn(text, hits, [note for _, note in named], remembered)
    messages = [*as_messages(window), {"role": "user", "content": asked}]
    directory = channels_block(bot, guild, await notes_or_nothing(db, guild_id))
    turn = uuid.uuid4().hex
    errors = tier_errors(bot)

    for name in order:
        try:
            answer = await try_tier(
                bot,
                name,
                model_setting=model_setting,
                system=voice,
                messages=messages,
                directory=directory,
                sheet=sheet,
                clause_text=clause_text,
            )
        except LLMError as exc:
            errors[name] = exc.reason
            await record(
                db,
                guild_id=guild_id,
                user_id=user_id,
                turn=turn,
                provider=ANTHROPIC if name == IMPORTANT else GROQ,
                model=MODEL if name == IMPORTANT else model_setting,
                tier=name,
                outcome=ERROR,
                at=at,
                trope=tone,
            )
            log.warning("chat: the %s tier did not answer — %s", name, exc.reason)
            if guild is not None:
                await log_action(
                    bot, guild, ERROR_KIND, details={"tier": name, "why": exc.reason}
                )
            continue
        if answer is None:
            continue
        errors.pop(name, None)
        await record(
            db,
            guild_id=guild_id,
            user_id=user_id,
            turn=turn,
            provider=answer.provider,
            model=answer.model,
            tier=name,
            outcome=OK,
            usage=answer.usage,
            at=at,
            trope=tone,
        )
        people = [who for who, _ in named]
        said = clip(await made_real(bot, guild, answer.text, people), REPLY_LIMIT)
        if not said:
            continue
        await remember(
            db,
            guild_id=guild_id,
            channel_id=channel_id,
            user_id=user_id,
            speaker=MEMBER,
            content=spoken(text),
            at=at,
        )
        await remember(
            db,
            guild_id=guild_id,
            channel_id=channel_id,
            user_id=user_id,
            speaker=BOT,
            content=said,
            tier=name,
            at=at,
        )
        return (said, name, tone)
    return NOTHING


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
