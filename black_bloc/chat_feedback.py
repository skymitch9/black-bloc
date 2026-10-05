"""A member who genuinely says Black Bloc was mean or wrong moves their own tone one step."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from . import tone_keys
from .actionlog import log_action
from .chat_memory import json_object
from .chat_review import (
    CAP_KEY,
    DAILY_KEY,
    MICRODOLLARS,
    SIMPLE_MODEL_KEY,
    guild_of,
    keeps_text,
    month_spent,
    phrases,
    says_one_of,
    setting,
    turns_today,
    usable_db,
    whole,
)
from .chat_voice import (
    MEAN,
    WINDOW_MINUTES,
    WRONG,
    avoid_span,
    claim_feedback,
    col,
    eased,
    fed_already,
    move_for_feedback,
    order_of,
    settle_of,
    step_toward,
    voice_row,
)
from .llm import ERROR, GROQ, OK, LLMError, record
from .personas import PERSONALITY_KEY, POOL, enabled_tropes, list_tropes

log = logging.getLogger(__name__)

NONE = "none"
REACTIONS = (NONE, MEAN, WRONG)
FEEDBACK_TIER = "feedback"
STATE_ATTR = "_chat_feedback"
ON = "on"
TEXT_CHARS = 500
CUE_CHARS = 80
JUDGED_PER_ANSWER = 2
REPLY_WAIT_SECONDS = 3.0
ANSWERS_KEPT = 500
MOVED_KIND = "chat.voice_feedback"
HELD_KIND = "chat.voice_feedback_held"
HELD_PINNED = "pinned"
HELD_NO_STEP = "no_step"
CLOSED_NO_KEY = "no_key"
CLOSED_CAPPED = "capped"
CLOSED_FULL = "full"
ORDER_KEYS = {MEAN: tone_keys.GENTLE_ORDER_KEY, WRONG: tone_keys.CAREFUL_ORDER_KEY}

JUDGE_SYSTEM = (
    "You read one message a Discord member wrote straight after Black Bloc, the server's bot, "
    "answered them. Decide whether the member is GENUINELY telling the bot that its answer was "
    "mean or that it was wrong, and answer with a single JSON object and nothing else:\n"
    '{"reaction": "none"|"mean"|"wrong", "genuine": true|false, '
    '"cue": "<the few words of theirs that show it, or null>"}\n'
    "- mean: they are hurt or put off by HOW the bot spoke to them (rude, harsh, hurtful, "
    "disrespectful, talking down).\n"
    "- wrong: they say WHAT the bot told them is incorrect, untrue or made up.\n"
    "- none: anything else — thanks, a new question, a complaint about somebody else, or "
    "disagreeing about a topic rather than about the bot's answer.\n"
    "- genuine is false when they are joking, teasing back, laughing (lol, lmao, haha, a "
    "laughing or skull emoji), playing along with the bot's own bit, or exaggerating for fun. "
    "When you cannot tell, genuine is false.\n"
    "Never put a person's name or handle in cue."
)
JUDGE_USER = "Black Bloc answered:\n{answered}\n\nThe member then wrote:\n{said}"


@dataclass(frozen=True)
class Verdict:
    reaction: str = NONE
    genuine: bool = False
    cue: str = ""
    shaped: bool = True

    @property
    def moves(self) -> bool:
        return self.genuine and self.reaction in (MEAN, WRONG)


@dataclass
class Answered:
    channel_id: int
    message_id: int | None
    reply_id: int | None
    text: str
    at: datetime
    judged: int = 0


@dataclass
class Tracker:
    answers: dict[tuple[int, int], Answered] = field(default_factory=dict)
    closed: set[tuple[int, str]] = field(default_factory=set)
    tasks: set[Any] = field(default_factory=set)


def tracker(bot: Any) -> Tracker:
    found = getattr(bot, STATE_ATTR, None)
    if not isinstance(found, Tracker):
        found = Tracker()
        setattr(bot, STATE_ATTR, found)
    return found


def parse_verdict(text: Any) -> Verdict:
    """The strict shape or nothing: an answer out of shape never moves anybody's tone."""
    found = json_object(text)
    if found is None:
        return Verdict(shaped=False)
    reaction = found.get("reaction")
    genuine = found.get("genuine")
    cue = found.get("cue")
    if not isinstance(reaction, str) or reaction.strip().lower() not in REACTIONS:
        return Verdict(shaped=False)
    if not isinstance(genuine, bool) or not (cue is None or isinstance(cue, str)):
        return Verdict(shaped=False)
    said = " ".join(str(cue or "").split())[:CUE_CHARS]
    kind = reaction.strip().lower()
    if kind == NONE:
        return Verdict()
    return Verdict(kind, genuine, said)


def is_on(bot: Any, guild_id: Any) -> bool:
    key = tone_keys.FEEDBACK_MODE_KEY
    return str(setting(bot.store, guild_id, key, tone_keys.TONE_SETTINGS[key][1])) == ON


def cue_in(bot: Any, guild_id: Any, text: Any) -> bool:
    """The free half: only a message carrying one of staff's cue words is ever judged."""
    cues = phrases(setting(bot.store, guild_id, tone_keys.FEEDBACK_CUES_KEY, ""))
    return says_one_of(text, cues)


def answered(
    bot: Any, message: Any, reply: Any, said: Any, *, now: datetime | None = None
) -> None:
    """Keep the last MODEL answer each member got, so their next words can be weighed on it."""
    guild_id = getattr(getattr(message, "guild", None), "id", None)
    if guild_id is None or not getattr(said, "tier", None):
        return
    user_id = int(getattr(getattr(message, "author", None), "id", 0) or 0)
    kept = tracker(bot).answers
    kept.pop((int(guild_id), user_id), None)
    kept[(int(guild_id), user_id)] = Answered(
        channel_id=int(getattr(getattr(message, "channel", None), "id", 0) or 0),
        message_id=getattr(message, "id", None),
        reply_id=getattr(reply, "id", None),
        text=str(getattr(said, "text", "") or ""),
        at=now or datetime.now(UTC),
    )
    while len(kept) > ANSWERS_KEPT:
        kept.pop(next(iter(kept)))


def replies_to(message: Any, last: Answered) -> bool:
    wanted = getattr(getattr(message, "reference", None), "message_id", None)
    return wanted is not None and last.reply_id is not None and int(wanted) == int(last.reply_id)


def mentions_bot(bot: Any, message: Any) -> bool:
    me = getattr(getattr(bot, "user", None), "id", None)
    if me is None or getattr(message, "mention_everyone", False):
        return False
    return any(getattr(one, "id", None) == me for one in getattr(message, "mentions", ()) or ())


def addressed(bot: Any, message: Any, last: Answered, at: datetime) -> bool:
    """Only words said TO the bot: a reply to its answer to this member, or an @-mention."""
    gap = at - last.at
    if gap < timedelta(0) or gap > timedelta(minutes=WINDOW_MINUTES):
        return False
    if getattr(getattr(message, "reference", None), "message_id", None) is not None:
        return replies_to(message, last)
    return mentions_bot(bot, message)


async def closed_why(bot: Any, guild_id: int, at: datetime) -> str | None:
    """None while the quick model may judge; otherwise the one reason it may not."""
    if not getattr(bot.settings, "simple_tier_configured", False):
        return CLOSED_NO_KEY
    cap = whole(setting(bot.store, guild_id, CAP_KEY, 0), 0)
    if await month_spent(bot.db, at) >= cap * MICRODOLLARS:
        return CLOSED_CAPPED
    daily = whole(setting(bot.store, guild_id, DAILY_KEY, 0), 0)
    if daily and await turns_today(bot.db, at) >= daily:
        return CLOSED_FULL
    return None


def said_once(bot: Any, guild_id: int, why: str | None) -> None:
    """The models being closed is one log line, not one for every message that waited."""
    closed = tracker(bot).closed
    if why is None:
        for one in [one for one in closed if one[0] == guild_id]:
            closed.discard(one)
        return
    if (guild_id, why) in closed:
        return
    closed.add((guild_id, why))
    log.info("chat feedback: nothing is judged in %s for now (%s)", guild_id, why)


async def fuse_open(bot: Any, guild_id: int, user_id: int, at: datetime) -> bool:
    """The member's own hourly turns bound the verdicts they can cause, as they bound replies."""
    from .chat_llm import CHAT_PERSON_HOURLY_TURNS, PERSON_TURNS_KEY, hour_before, person_turns

    limit = whole(setting(bot.store, guild_id, PERSON_TURNS_KEY, CHAT_PERSON_HOURLY_TURNS), 0)
    return not limit or await person_turns(bot.db, user_id, hour_before(at)) < limit


async def judge(
    bot: Any, guild_id: int, user_id: int, last: Answered, said: str, at: datetime
) -> Verdict:
    """One capped call to the quick model, on the member's own count; an error is no verdict."""
    from .chat_llm import groq

    model = str(setting(bot.store, guild_id, SIMPLE_MODEL_KEY, "") or "")
    client = groq(bot, model, FEEDBACK_TIER)
    if client is None:
        return Verdict(shaped=False)
    asked = JUDGE_USER.format(answered=last.text[:TEXT_CHARS], said=said[:TEXT_CHARS])
    turn = uuid.uuid4().hex
    spent = {"db": bot.db, "guild_id": guild_id, "user_id": user_id, "turn": turn, "at": at}
    try:
        reply = await client.reply(
            system=JUDGE_SYSTEM, messages=[{"role": "user", "content": asked}], json_only=True
        )
    except LLMError as exc:
        await record(
            **spent, provider=GROQ, model=client.model, tier=FEEDBACK_TIER, outcome=ERROR
        )
        log.warning("chat feedback: the quick model did not judge — %s", exc.reason)
        return Verdict(shaped=False)
    await record(
        **spent,
        provider=reply.provider,
        model=reply.model,
        tier=FEEDBACK_TIER,
        outcome=OK,
        usage=reply.usage,
    )
    found = parse_verdict(reply.text)
    if not found.shaped:
        log.warning("chat feedback: a verdict came back out of shape: %r", reply.text[:200])
    return found


async def moved(
    bot: Any, guild_id: int, user_id: int, row: Any, found: Verdict, message: Any, at: datetime
) -> str | None:
    """One step toward gentle or careful; a pin, or nowhere to step, holds and says why."""
    if not await claim_feedback(bot.db, guild_id, user_id):
        return None
    row = await voice_row(bot.db, guild_id, user_id)
    guild = guild_of(bot, guild_id)
    tone = str(col(row, "tone", ""))
    kept = await keeps_text(bot, guild_id, user_id)
    details = {
        "member": str(user_id),
        "why": found.reaction,
        "cue": found.cue if kept else None,
        "cue_kept": kept,
        "message_id": str(getattr(message, "id", "") or ""),
    }
    held = None
    wanted = None
    if col(row, "pinned"):
        held = HELD_PINNED
    else:
        order = order_of(setting(bot.store, guild_id, ORDER_KEYS[found.reaction], ""))
        names = [one.name for one in enabled_tropes(await list_tropes(bot.db))]
        wanted = step_toward(tone, order, names)
        if wanted is None:
            held = HELD_NO_STEP
    if held is not None:
        log.info("chat feedback: %s keeps %s (%s)", user_id, col(row, "pinned") or tone, held)
        if guild is not None:
            await log_action(
                bot,
                guild,
                HELD_KIND,
                target=user_id,
                details={**details, "tone": col(row, "pinned") or tone, "held": held},
            )
        return None
    settle = settle_of(bot.store, guild_id)
    await move_for_feedback(
        bot.db,
        guild_id,
        user_id,
        wanted,
        found.reaction,
        now=at,
        settled=eased(col(row, "settled", 0), settle),
        avoid_for=avoid_span(settle),
    )
    if guild is not None:
        await log_action(
            bot,
            guild,
            MOVED_KIND,
            target=user_id,
            details={**details, "from": tone, "tone": wanted},
        )
    return wanted


async def pin_held(bot: Any, guild_id: int, user_id: int, row: Any, message: Any) -> None:
    """A pinned member's complaint costs no model call: one row a conversation says it held."""
    if not await claim_feedback(bot.db, guild_id, user_id):
        return
    pinned = str(col(row, "pinned", ""))
    log.info("chat feedback: %s keeps %s (%s)", user_id, pinned, HELD_PINNED)
    guild = guild_of(bot, guild_id)
    if guild is None:
        return
    await log_action(
        bot,
        guild,
        HELD_KIND,
        target=user_id,
        details={
            "member": str(user_id),
            "why": None,
            "cue": None,
            "cue_kept": False,
            "judged": False,
            "message_id": str(getattr(message, "id", "") or ""),
            "tone": pinned,
            "held": HELD_PINNED,
        },
    )


async def heard(bot: Any, message: Any, *, now: datetime | None = None) -> str | None:
    """Weigh one message against the last model answer its author got; the tone it moved to."""
    guild_id = getattr(getattr(message, "guild", None), "id", None)
    db = usable_db(bot)
    if guild_id is None or db is None:
        return None
    guild_id = int(guild_id)
    user_id = int(getattr(getattr(message, "author", None), "id", 0) or 0)
    last = tracker(bot).answers.get((guild_id, user_id))
    if last is None or last.message_id == getattr(message, "id", None):
        return None
    at = now or datetime.now(UTC)
    text = str(getattr(message, "content", "") or "")
    if not addressed(bot, message, last, at):
        return None
    if not is_on(bot, guild_id) or not cue_in(bot, guild_id, text):
        return None
    if str(setting(bot.store, guild_id, PERSONALITY_KEY, "")).strip().lower() != POOL:
        return None
    row = await voice_row(db, guild_id, user_id)
    if row is None or fed_already(row):
        return None
    if col(row, "pinned"):
        await pin_held(bot, guild_id, user_id, row, message)
        return None
    if not col(row, "tone") or last.judged >= JUDGED_PER_ANSWER:
        return None
    why = await closed_why(bot, guild_id, at)
    said_once(bot, guild_id, why)
    if why is not None or not await fuse_open(bot, guild_id, user_id, at):
        return None
    last.judged += 1
    found = await judge(bot, guild_id, user_id, last, text, at)
    if not found.moves:
        return None
    return await moved(bot, guild_id, user_id, row, found, message, at)


async def weighed(bot: Any, message: Any) -> None:
    try:
        await heard(bot, message)
    except Exception as exc:
        log.warning("chat feedback: a message was not weighed — %s: %s", type(exc).__name__, exc)


def schedule(bot: Any, message: Any) -> Any:
    """A task for a member who has a tracked answer, and nothing at all for anybody else."""
    guild_id = getattr(getattr(message, "guild", None), "id", None)
    user_id = int(getattr(getattr(message, "author", None), "id", 0) or 0)
    if guild_id is None or (int(guild_id), user_id) not in tracker(bot).answers:
        return None
    try:
        task = asyncio.get_running_loop().create_task(weighed(bot, message))
    except RuntimeError:
        return None
    held = tracker(bot).tasks
    held.add(task)
    task.add_done_callback(held.discard)
    return task


async def before_reply(bot: Any, message: Any, *, seconds: float = REPLY_WAIT_SECONDS) -> None:
    """The verdict lands before the answer is worded, but never holds the answer for long."""
    task = schedule(bot, message)
    if task is None:
        return
    try:
        await asyncio.wait_for(asyncio.shield(task), timeout=seconds)
    except TimeoutError:
        log.info("chat feedback: a verdict was still out, so the answer did not wait for it")
