from __future__ import annotations

import logging
import re
from typing import Any

from .chat import MENTION, has_phrase, normalise
from .llm import IMPORTANT, SIMPLE

log = logging.getLogger(__name__)

QUESTION_WORDS = 12
CONVERSATION_TURNS = 2
QUESTION_MARK = "?"

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
