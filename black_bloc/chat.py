from __future__ import annotations

import json
import logging
import random
import re
from datetime import UTC, datetime
from typing import Any

from . import chat_data
from .emoji import tone_for, toned_text
from .presence import human_count, status_guild

log = logging.getLogger(__name__)

LINE_LIMIT = 200
FALLBACK_NAME = "friend"
UNKNOWN = "unknown"
INSULT = "insult"
GREETING = "greeting"

CANNED = "canned"
DATA = "data"
ROUTE = "route"
KINDS: tuple[str, ...] = (CANNED, DATA, ROUTE)

FILLED = "filled"
EMPTY = "empty"
ATTENDEE = "attendee"
SLOTS: tuple[str, ...] = (FILLED, EMPTY, ATTENDEE)

NAME_LIMIT = 60
TRIGGER_LIMIT = 60
TRIGGERS_MAX = 40
TEXT_LIMIT = 500
NAME_SHAPE = re.compile(r"^[a-z][a-z0-9_]*$")

MENTION = re.compile(r"<@[!&]?\d+>")
KEEP = re.compile(r"[^0-9a-z ]+")
LOVE_MARKS = ("❤", "♥", "\U0001f5a4", "\U0001f49c", "\U0001f496", "<3")

INTENTS: dict[str, tuple[str, ...]] = {
    "insult": (
        "you suck",
        "you stink",
        "shut up",
        "shut it",
        "bad bot",
        "dumb bot",
        "stupid bot",
        "useless bot",
        "trash bot",
        "worst bot",
        "youre useless",
        "youre annoying",
        "nobody asked",
    ),
    "love": (
        "i love you",
        "love you",
        "love ya",
        "ily",
        "youre the best",
        "best bot",
        "good bot",
        "youre awesome",
        "youre great",
        "love this bot",
    ),
    "thanks": (
        "thanks",
        "thank you",
        "thankyou",
        "thx",
        "ty",
        "tysm",
        "appreciate it",
        "appreciate you",
        "much appreciated",
    ),
    "what_can_you_do": (
        "what can you do",
        "what do you do",
        "what are you",
        "who are you",
        "what are your commands",
        "what commands do you have",
        "whats your job",
        "what can you help with",
    ),
    "help": (
        "help",
        "help me",
        "i need help",
        "can you help",
        "how do i",
        "how does this work",
        "need a hand",
        "im stuck",
        "whats the command",
    ),
    "how_are_you": (
        "how are you",
        "how are ya",
        "how are things",
        "hows it going",
        "hows it hanging",
        "hows your day",
        "how you doing",
        "how ya doing",
        "you good",
        "you ok",
        "you okay",
    ),
    "greeting": (
        "hi",
        "hii",
        "hiya",
        "hello",
        "hey",
        "heya",
        "yo",
        "sup",
        "wassup",
        "whats up",
        "whats good",
        "good morning",
        "good afternoon",
        "good evening",
        "morning",
        "evening",
        "howdy",
        "greetings",
    ),
}

ORDER: tuple[str, ...] = (
    "insult",
    "love",
    "thanks",
    "what_can_you_do",
    "help",
    "how_are_you",
    "greeting",
)

DATA_INTENTS: dict[str, tuple[str, ...]] = {
    "birthdays": (
        "birthdays",
        "any birthdays",
        "whose birthday",
        "whose birthday is it",
        "next birthday",
        "next birthdays",
    ),
    "whats_next": (
        "whats next",
        "next event",
        "the next event",
        "when is the next",
        "anything coming up",
        "whats coming up",
    ),
    "who_is_live": (
        "whos live",
        "who is live",
        "anyone live",
        "who is streaming",
        "whos streaming",
        "anyone streaming",
    ),
    "head_count": (
        "how many of us",
        "how many people",
        "how many members",
        "member count",
        "head count",
    ),
    "my_roles": (
        "my roles",
        "what roles do i have",
        "what roles can i pick",
        "which roles can i pick",
        "what roles are there",
    ),
    "time_for_me": (
        "what time is that for me",
        "what time is that my time",
        "in my time zone",
        "in my timezone",
        "what time is that here",
    ),
}

ROUTE_INTENTS: dict[str, tuple[str, ...]] = {
    "need_a_mod": (
        "i need a mod",
        "need a mod",
        "get a mod",
        "mod please",
        "staff please",
        "i need staff",
        "help me",
        "report",
    ),
}

DATA_LINES: dict[str, dict[str, tuple[str, ...]]] = {
    "birthdays": {
        FILLED: ("Birthdays coming up, {name}: {list}",),
        EMPTY: ("No birthdays stored yet, {name} — `/birthday set` adds yours to the list.",),
    },
    "whats_next": {
        FILLED: ("Next up, {name}: **{title}** {when} in {channel}.",),
        EMPTY: ("Nothing on the calendar yet, {name}. `/event request` gets one started.",),
    },
    "who_is_live": {
        FILLED: ("Live right now, {name}: {names} — {links}",),
        EMPTY: ("Nobody is streaming right now, {name} — the cookout is all off-camera.",),
    },
    "head_count": {
        FILLED: ("{count} of us at the cookout right now, {name}.",),
        EMPTY: ("I cannot count heads at the moment, {name}. Ask me again in a minute.",),
    },
    "my_roles": {
        FILLED: ("You can pick from {menus}, {name}. Right now you have {roles}.",),
        EMPTY: ("Role picking is off right now, {name}, so there is nothing to pick.",),
    },
    "time_for_me": {
        FILLED: ("That is {time} for you, {name}.",),
        EMPTY: (
            "I need to know your zone before I can work that out, {name}. Run `/timezone set` "
            "and ask me again.",
        ),
    },
}

ROUTE_LINES: dict[str, dict[str, tuple[str, ...]]] = {
    "need_a_mod": {
        FILLED: (
            "DM me and I will open a ticket for staff, {name} — send the message straight to me "
            "and somebody will pick it up.",
        ),
        EMPTY: ("Staff to ask, {name}: {roles}.",),
    },
}

TOKENS: dict[str, tuple[str, ...]] = {
    "who_is_live": ("{names}", "{links}"),
    "whats_next": ("{title}", "{when}", "{channel}"),
    "birthdays": ("{list}",),
    "head_count": ("{count}",),
    "my_roles": ("{menus}", "{roles}"),
    "time_for_me": ("{time}",),
    "need_a_mod": ("{roles}",),
}

BUILTIN_ORDER: tuple[str, ...] = (
    "insult",
    "love",
    "thanks",
    "need_a_mod",
    "birthdays",
    "whats_next",
    "who_is_live",
    "head_count",
    "my_roles",
    "time_for_me",
    "what_can_you_do",
    "help",
    "how_are_you",
    "greeting",
)

BUILTIN_TRIGGERS: dict[str, tuple[str, ...]] = {
    **INTENTS,
    **DATA_INTENTS,
    **ROUTE_INTENTS,
    UNKNOWN: (),
}

BUILTIN_KINDS: dict[str, str] = (
    {name: CANNED for name in INTENTS}
    | {name: DATA for name in DATA_INTENTS}
    | {name: ROUTE for name in ROUTE_INTENTS}
    | {UNKNOWN: CANNED}
)

BUILTIN_NAMES: frozenset[str] = frozenset(BUILTIN_TRIGGERS)

LINES: dict[str, tuple[str, ...]] = {
    "greeting": (
        "Hey {name}! Pull up a chair — the cookout is already going.",
        "{name}! Good to see you. What can I get you?",
        "Hi {name} 👋 I am on shift, so just say the word.",
        "Hey there, {name}. A plate is ready whenever you are.",
        "{name}! Welcome in. Ask me anything, or run `/help` for the menu.",
        "Hello {name}! Still just a bot, but a friendly one.",
    ),
    "thanks": (
        "Any time, {name}. That is what I am here for.",
        "You got it, {name}.",
        "No thanks needed, {name} — I run on electricity, not gratitude. Nice to hear it though.",
        "Happy to help, {name}. Holler if you need anything else.",
        "Any time. Go enjoy the cookout, {name}.",
        "That is the job, {name}. Glad it landed.",
    ),
    "how_are_you": (
        "Running clean, {name} — no errors, no complaints.",
        "Doing well, {name}! Nothing is burning and the grill is still hot.",
        "Same as always, {name}: awake, online and mildly enthusiastic.",
        "All good here, {name}. How is your day going?",
        "Cannot complain, {name} — I am a bot, so the bar is low and I am clearing it.",
    ),
    "what_can_you_do": (
        "Plenty, {name} — roles, events, birthdays, go-live posts and keeping things tidy. "
        "`/help` lists it all.",
        "I keep the cookout running, {name}: role menus, temp voice, event posts and mod tools. "
        "Try `/help`.",
        "Short version, {name}: I announce, organise and moderate. The long version is `/help`.",
        "Ask `/help` for the full menu, {name} — roles, events, streams and moderation are the "
        "big four.",
        "I am the cookout's helper bot, {name}. `/help` shows every command I answer to.",
    ),
    "help": (
        "I have got you, {name} — run `/help` and I will list everything I answer to.",
        "Say the word, {name}. `/help` is the menu, and an Auntie or Uncle can take it from there.",
        "Start with `/help`, {name}. If it is a people problem, staff are the better call.",
        "Try `/help` for commands, {name} — and if you need a human, staff are around.",
        "Happy to point you somewhere, {name}: `/help` first, staff second.",
    ),
    "love": (
        "Love you too, {name} 🖤",
        "That is the nicest thing anyone has said to me all day, {name}.",
        "Aw, {name}. I would blush if I had the hardware.",
        "Right back at you, {name}. Best crowd at any cookout.",
        "You are alright yourself, {name}.",
    ),
    "insult": (
        "Harsh, {name}, but fair on some days. I will keep trying.",
        "Noted, {name}. I will add that to my performance review.",
        "That one stung, {name}. Well — it would have, if I had feelings.",
        "Fair enough, {name}. Still here though.",
        "I will take it, {name}. Someone has to keep the cookout humble.",
    ),
    UNKNOWN: (
        "Not sure I follow, {name} — try `/help` for what I can do.",
        "That one is past me, {name}. `/help` shows what I actually understand.",
        "I only speak fluent commands, {name} — `/help` has the list.",
        "You have lost me, {name}, but `/help` might have what you want.",
        "Cannot help with that one yet, {name}. `/help` shows what I can.",
    ),
}

ATTENDEE_LINES: dict[str, tuple[str, ...]] = {
    "how_are_you": (
        "Good, {name}! Keeping an eye on {attendees} cookout attendees right now.",
    ),
    "greeting": (
        "Hey {name}! That makes {attendees} of us at the cookout today.",
    ),
}


class ChatError(ValueError):
    """An intent or a line was given something Black Bloc will not store."""


class Tokens(dict):
    """A token nothing filled in is left as it was typed, never raised."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def normalise(text: Any) -> str:
    """Mention-free, punctuation-free, lowercase words with single spaces."""
    raw = MENTION.sub(" ", str(text or "")).lower().replace("'", "").replace("’", "")
    return " ".join(KEEP.sub(" ", raw).split())


def has_phrase(words: str, phrase: str) -> bool:
    return f" {phrase} " in f" {words} "


def matches(words: str, triggers: Any) -> bool:
    return any(has_phrase(words, normalise(phrase)) for phrase in triggers or () if str(phrase))


def render(line: Any, values: dict[str, Any]) -> str:
    try:
        return str(line).format_map(Tokens(values))
    except (IndexError, KeyError, ValueError) as exc:
        log.warning("chat: %r was left as typed — %s: %s", line, type(exc).__name__, exc)
        return str(line)


def by_name(intents: Any) -> dict[str, Any]:
    return {str(row["name"]): row for row in intents or ()}


def customs(intents: Any) -> list[Any]:
    """A guild's own intents, in the order staff put them in."""
    found = [row for row in intents or () if not row["builtin"] and row["enabled"]]
    return sorted(found, key=lambda row: (int(row["sort"]), int(row["id"])))


def has_something_to_say(row: Any) -> bool:
    return bool((row.get("lines") or {}).get(FILLED))


def classify(text: Any, intents: Any = ()) -> str:
    """One intent name: a guild's own intents first, then the built-in ones, then unknown."""
    raw = MENTION.sub(" ", str(text or ""))
    words = normalise(raw)
    rows = by_name(intents)
    if words:
        for row in customs(intents):
            if has_something_to_say(row) and matches(words, row["triggers"]):
                return str(row["name"])
    love = rows.get("love")
    if (love is None or love["enabled"]) and any(mark in raw for mark in LOVE_MARKS):
        return "love"
    if not words:
        return UNKNOWN
    for name in BUILTIN_ORDER:
        row = rows.get(name)
        if row is not None and not row["enabled"]:
            continue
        triggers = row["triggers"] if row is not None else BUILTIN_TRIGGERS[name]
        if matches(words, triggers):
            return name
    return UNKNOWN


def bare_greeting(text: Any, intents: Any = ()) -> bool:
    """Nothing but a hello — the whole message, mention aside, is one greeting phrase."""
    words = normalise(text)
    if not words:
        return False
    row = by_name(intents).get(GREETING)
    triggers = row["triggers"] if row is not None else INTENTS[GREETING]
    return any(normalise(phrase) == words for phrase in triggers or ())


def kind_of(intent: str, intents: Any = ()) -> str:
    row = by_name(intents).get(intent)
    return str(row["kind"]) if row is not None else BUILTIN_KINDS.get(intent, CANNED)


def tokens_of(intent: str) -> tuple[str, ...]:
    """The tokens THIS intent fills in, beyond `{name}` and `{attendees}`."""
    return TOKENS.get(intent, ())


def code_lines(intent: str, slot: str) -> tuple[str, ...]:
    """What the code tables say, which is the fallback whenever a guild has nothing."""
    if intent in DATA_LINES:
        return DATA_LINES[intent].get(slot, ())
    if intent in ROUTE_LINES:
        return ROUTE_LINES[intent].get(slot, ())
    if slot == ATTENDEE:
        return ATTENDEE_LINES.get(intent, ())
    if slot == EMPTY:
        return ()
    return LINES.get(intent) or LINES[UNKNOWN]


def pool(
    intent: str, attendees: int | None = None, intents: Any = (), slot: str = FILLED
) -> tuple[str, ...]:
    """The lines an intent may answer with: the guild's own, else the code table."""
    row = by_name(intents).get(intent)
    stored = (row.get("lines") if row is not None else None) or {}
    found = tuple(stored.get(slot) or ()) or code_lines(intent, slot)
    if slot != FILLED or attendees is None:
        return found
    if row is not None:
        return found + tuple(stored.get(ATTENDEE) or ())
    return found + ATTENDEE_LINES.get(intent, ())


def respond(
    intent: str,
    *,
    name: str,
    attendees: int | None = None,
    rng: random.Random | None = None,
    intents: Any = (),
    slot: str = FILLED,
    tokens: dict[str, Any] | None = None,
) -> str:
    """One line in Black Bloc's voice for an intent."""
    chooser = rng or random
    lines = pool(intent, attendees, intents, slot) or LINES[UNKNOWN]
    return render(chooser.choice(lines), {"name": name, "attendees": attendees, **(tokens or {})})


def display_name(member: Any) -> str:
    found = getattr(member, "display_name", None) or getattr(member, "name", None) or ""
    return str(found).strip() or FALLBACK_NAME


def attendees_for(member: Any, bot: Any) -> int | None:
    guild = getattr(member, "guild", None) or status_guild(bot)
    return human_count(guild) if guild is not None else None


class Answer:
    """One reply and the labels the cog logs it under."""

    def __init__(self, intent: str, kind: str, slot: str, text: str) -> None:
        self.intent = intent
        self.kind = kind
        self.slot = slot
        self.text = text


async def answer_for(
    text: Any, member: Any, bot: Any, *, rng: random.Random | None = None, guild: Any = None
) -> Answer:
    """Classify, look up whatever live state the intent needs, and pick a line."""
    home = guild if guild is not None else getattr(member, "guild", None)
    guild_id = getattr(home, "id", None)
    intents = await guild_intents(bot, guild_id)
    intent = classify(text, intents)
    kind = kind_of(intent, intents)
    tokens, filled = await chat_data.tokens_for(bot, home, member, intent, text)
    slot = FILLED if kind == CANNED or filled else EMPTY
    line = respond(
        intent,
        name=display_name(member),
        attendees=attendees_for(member, bot),
        rng=rng,
        intents=intents,
        slot=slot,
        tokens=tokens,
    )
    return Answer(intent, kind, slot, toned_text(line, tone_for(bot, guild_id)))


async def reply_for(
    text: Any, member: Any, bot: Any, *, rng: random.Random | None = None
) -> str | None:
    """The whole answer, in one call — swap this out for a real conversation backend."""
    return (await answer_for(text, member, bot, rng=rng)).text


NAME_NOT_A_NAME = (
    "An intent's name is lowercase letters, numbers and underscores — `cookout_hours`, say. "
    "{given} is not one, so nothing was saved."
)
NAME_TOO_LONG = (
    "An intent's name has to be {limit} characters or fewer, so nothing was saved. Shorten it "
    "and send it again."
)
NAME_IS_BUILT_IN = (
    "**{name}** is one of Black Bloc's own intents, so a second one cannot take that name. Edit "
    "the built-in one instead, or pick another name."
)
NO_TRIGGERS = (
    "An intent needs at least one trigger phrase, or nothing would ever reach it. Add a phrase "
    "and send it again."
)
TOO_MANY_TRIGGERS = (
    "An intent takes at most {limit} trigger phrases, so nothing was saved. Trim the list, or "
    "split it into two intents."
)
TRIGGER_TOO_LONG = (
    "A trigger phrase has to be {limit} characters or fewer, so nothing was saved. **{given}** "
    "is longer than that."
)
NO_TEXT = "A line needs some words in it, so nothing was saved."
TEXT_TOO_LONG = (
    "A line has to be {limit} characters or fewer, so nothing was saved. Discord will take a "
    "longer one, but nobody reads it."
)
NOT_A_SLOT = (
    "**{given}** is not somewhere a line can go. They are {known} — `filled` is the ordinary "
    "answer, `empty` is what a data intent says when there is nothing to report."
)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def clean_name(value: Any) -> str:
    said = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    if len(said) > NAME_LIMIT:
        raise ChatError(NAME_TOO_LONG.format(limit=NAME_LIMIT))
    if not NAME_SHAPE.match(said):
        raise ChatError(NAME_NOT_A_NAME.format(given=repr(str(value or ""))[:60]))
    if said in BUILTIN_NAMES:
        raise ChatError(NAME_IS_BUILT_IN.format(name=said))
    return said


def clean_triggers(value: Any) -> list[str]:
    given = value if isinstance(value, list | tuple) else str(value or "").split(",")
    found: list[str] = []
    for item in given:
        said = " ".join(str(item).strip().split())
        if not said:
            continue
        if len(said) > TRIGGER_LIMIT:
            raise ChatError(TRIGGER_TOO_LONG.format(limit=TRIGGER_LIMIT, given=said[:60]))
        if said not in found:
            found.append(said)
    if not found:
        raise ChatError(NO_TRIGGERS)
    if len(found) > TRIGGERS_MAX:
        raise ChatError(TOO_MANY_TRIGGERS.format(limit=TRIGGERS_MAX))
    return found


def clean_text(value: Any) -> str:
    said = str(value or "").strip()
    if not said:
        raise ChatError(NO_TEXT)
    if len(said) > TEXT_LIMIT:
        raise ChatError(TEXT_TOO_LONG.format(limit=TEXT_LIMIT))
    return said


def clean_slot(value: Any) -> str:
    said = str(value or FILLED).strip().lower()
    if said not in SLOTS:
        raise ChatError(NOT_A_SLOT.format(given=str(value)[:40], known=", ".join(SLOTS)))
    return said


def read_triggers(value: Any) -> tuple[str, ...]:
    try:
        found = json.loads(str(value or "[]"))
    except (TypeError, ValueError):
        return ()
    return tuple(str(item) for item in found) if isinstance(found, list) else ()


async def list_intents(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM chat_intents WHERE guild_id = ? ORDER BY sort, id", (int(guild_id),)
    )
    return list(await cur.fetchall())


async def get_intent(db: Any, intent_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM chat_intents WHERE id = ?", (int(intent_id),))
    return await cur.fetchone()


async def named_intent(db: Any, guild_id: int, name: str) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM chat_intents WHERE guild_id = ? AND name = ?", (int(guild_id), str(name))
    )
    return await cur.fetchone()


async def lines_for(db: Any, intent_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM chat_lines WHERE intent_id = ? ORDER BY id", (int(intent_id),)
    )
    return list(await cur.fetchall())


async def get_line(db: Any, line_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM chat_lines WHERE id = ?", (int(line_id),))
    return await cur.fetchone()


async def create_intent(
    db: Any,
    guild_id: int,
    name: str,
    triggers: Any,
    *,
    kind: str = CANNED,
    enabled: bool = True,
    sort: int = 0,
    by: int | None = None,
) -> int:
    cur = await db.conn.execute(
        "INSERT INTO chat_intents(guild_id, name, triggers, kind, enabled, sort, created_by, "
        "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            int(guild_id),
            str(name),
            json.dumps([str(one) for one in triggers]),
            str(kind),
            1 if enabled else 0,
            int(sort),
            by,
            now_iso(),
        ),
    )
    await db.conn.commit()
    return int(cur.lastrowid)


async def update_intent(db: Any, intent_id: int, **fields: Any) -> None:
    parts, values = [], []
    for key in ("name", "triggers", "enabled", "sort"):
        if key not in fields:
            continue
        value = fields[key]
        if key == "triggers":
            value = json.dumps([str(one) for one in value])
        elif key == "enabled":
            value = 1 if value else 0
        elif key == "sort":
            value = int(value)
        parts.append(f"{key} = ?")
        values.append(value)
    if not parts:
        return
    parts.append("updated_at = ?")
    values += [now_iso(), int(intent_id)]
    await db.conn.execute(f"UPDATE chat_intents SET {', '.join(parts)} WHERE id = ?", values)
    await db.conn.commit()


async def delete_intent(db: Any, intent_id: int) -> bool:
    cur = await db.conn.execute("DELETE FROM chat_intents WHERE id = ?", (int(intent_id),))
    await db.conn.commit()
    return bool(cur.rowcount)


async def add_line(
    db: Any,
    intent_id: int,
    text: str,
    *,
    slot: str = FILLED,
    enabled: bool = True,
    by: int | None = None,
) -> int:
    cur = await db.conn.execute(
        "INSERT INTO chat_lines(intent_id, text, slot, enabled, created_by, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (int(intent_id), str(text), str(slot), 1 if enabled else 0, by, now_iso()),
    )
    await db.conn.commit()
    return int(cur.lastrowid)


async def update_line(db: Any, line_id: int, **fields: Any) -> None:
    parts, values = [], []
    for key in ("text", "slot", "enabled"):
        if key not in fields:
            continue
        value = (1 if fields[key] else 0) if key == "enabled" else str(fields[key])
        parts.append(f"{key} = ?")
        values.append(value)
    if not parts:
        return
    parts.append("updated_at = ?")
    values += [now_iso(), int(line_id)]
    await db.conn.execute(f"UPDATE chat_lines SET {', '.join(parts)} WHERE id = ?", values)
    await db.conn.commit()


async def delete_line(db: Any, line_id: int) -> bool:
    cur = await db.conn.execute("DELETE FROM chat_lines WHERE id = ?", (int(line_id),))
    await db.conn.commit()
    return bool(cur.rowcount)


async def seed_defaults(db: Any, guild_id: int, by: int | None = None) -> int:
    """Today's code tables as rows staff can edit — once per guild, and never twice."""
    made = 0
    for position, name in enumerate((*BUILTIN_ORDER, UNKNOWN)):
        if await named_intent(db, guild_id, name) is not None:
            continue
        intent_id = await create_intent(
            db,
            guild_id,
            name,
            BUILTIN_TRIGGERS[name],
            kind=BUILTIN_KINDS[name],
            sort=position,
            by=by,
        )
        for slot in SLOTS:
            for text in code_lines(name, slot):
                await add_line(db, intent_id, text, slot=slot, by=by)
        made += 1
    if made:
        log.info("chat: seeded %d intent(s) for guild %s", made, guild_id)
    return made


async def loaded_intents(db: Any, guild_id: int) -> tuple[dict[str, Any], ...]:
    """The rows classification reads: enabled lines only, grouped by slot."""
    found = []
    for row in await list_intents(db, guild_id):
        lines: dict[str, list[str]] = {slot: [] for slot in SLOTS}
        for line in await lines_for(db, row["id"]):
            if line["enabled"]:
                lines.setdefault(str(line["slot"]), []).append(str(line["text"]))
        found.append(
            {
                "id": int(row["id"]),
                "name": str(row["name"]),
                "kind": str(row["kind"]),
                "enabled": bool(row["enabled"]),
                "sort": int(row["sort"]),
                "triggers": read_triggers(row["triggers"]),
                "builtin": str(row["name"]) in BUILTIN_NAMES,
                "lines": {slot: tuple(texts) for slot, texts in lines.items()},
            }
        )
    return tuple(found)


CACHE_ATTR = "_chat_intents"


def invalidate(bot: Any, guild_id: int | None = None) -> None:
    """Forget the cached rows, so the next reply reads what was just saved."""
    cache = getattr(bot, CACHE_ATTR, None)
    if not isinstance(cache, dict):
        return
    if guild_id is None:
        cache.clear()
    else:
        cache.pop(int(guild_id), None)


async def guild_intents(bot: Any, guild_id: int | None) -> tuple[dict[str, Any], ...]:
    if guild_id is None:
        return ()
    cache = getattr(bot, CACHE_ATTR, None)
    if not isinstance(cache, dict):
        cache = {}
        setattr(bot, CACHE_ATTR, cache)
    found = cache.get(int(guild_id))
    if found is not None:
        return found
    db = getattr(bot, "db", None)
    if db is None or not getattr(db, "is_connected", False):
        return ()
    try:
        found = await loaded_intents(db, guild_id)
    except Exception as exc:
        log.warning("chat: intents for %s not read — %s: %s", guild_id, type(exc).__name__, exc)
        return ()
    cache[int(guild_id)] = found
    return found
