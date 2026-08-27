from __future__ import annotations

import random
import re
from typing import Any

from .emoji import tone_for, toned_text
from .presence import human_count, status_guild

LINE_LIMIT = 200
FALLBACK_NAME = "friend"
UNKNOWN = "unknown"
INSULT = "insult"

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


def normalise(text: Any) -> str:
    """Mention-free, punctuation-free, lowercase words with single spaces."""
    raw = MENTION.sub(" ", str(text or "")).lower().replace("'", "").replace("’", "")
    return " ".join(KEEP.sub(" ", raw).split())


def has_phrase(words: str, phrase: str) -> bool:
    return f" {phrase} " in f" {words} "


def classify(text: Any) -> str:
    """One intent name for a message, matching whole words rather than substrings."""
    raw = MENTION.sub(" ", str(text or ""))
    words = normalise(raw)
    if any(mark in raw for mark in LOVE_MARKS):
        return "love"
    if not words:
        return UNKNOWN
    for intent in ORDER:
        if any(has_phrase(words, phrase) for phrase in INTENTS[intent]):
            return intent
    return UNKNOWN


def pool(intent: str, attendees: int | None) -> tuple[str, ...]:
    lines = LINES.get(intent) or LINES[UNKNOWN]
    if attendees is None:
        return lines
    return lines + ATTENDEE_LINES.get(intent, ())


def respond(
    intent: str,
    *,
    name: str,
    attendees: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """One line in Black Bloc's voice for an intent."""
    chooser = rng or random
    line = chooser.choice(pool(intent, attendees))
    return line.format(name=name, attendees=attendees)


def display_name(member: Any) -> str:
    found = getattr(member, "display_name", None) or getattr(member, "name", None) or ""
    return str(found).strip() or FALLBACK_NAME


def attendees_for(member: Any, bot: Any) -> int | None:
    guild = getattr(member, "guild", None) or status_guild(bot)
    return human_count(guild) if guild is not None else None


def reply_for(
    text: Any, member: Any, bot: Any, *, rng: random.Random | None = None
) -> str | None:
    """The whole answer, in one call — swap this out for a real conversation backend."""
    line = respond(
        classify(text),
        name=display_name(member),
        attendees=attendees_for(member, bot),
        rng=rng,
    )
    return toned_text(line, tone_for(bot, getattr(getattr(member, "guild", None), "id", None)))
