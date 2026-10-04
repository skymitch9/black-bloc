from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .golive import parse_ts
from .marathon_signals import chains
from .marathon_spotlight import in_reach, span_of

TYPE_RERUN = "rerun"
REASON_TYPE = "type"
TITLE_HEAD = "title:"
TAG_HEAD = "tag:"
LEADING_TAG = re.compile(r"^\s*[\[(【]([^\])】]*)[\])】]")
LIVE_HEAD = "live:"
OVERRULED_MARATHON = "marathon"
PLAIN = "plain"
SKIP = "skip"
LIVE = "live"
CLEARED_STAFF = "staff"
CLEARED_TITLE = "title"
CLEARED_TYPE = "type"
CLEARED_MARATHON = "marathon"
CLEARED_ACTION = "action"
BECAUSE_REPLAY = "replay"


@dataclass(frozen=True)
class Verdict:
    replay: bool
    reason: str | None = None
    overruled: str | None = None
    matched: str | None = None


def words_of(text: Any) -> tuple[str, ...]:
    found: list[str] = []
    for part in re.split(r"[,\n]", str(text or "")):
        word = part.strip().casefold()
        if word and word not in found:
            found.append(word)
    return tuple(found)


def _pattern(word: str) -> re.Pattern[str]:
    return re.compile(r"(?<!\w)" + re.escape(word) + r"(?!\w)", re.IGNORECASE)


def word_in(title: Any, words: Any) -> str | None:
    """The first listed word the title carries whole; a longer word containing it does not count."""
    text = str(title or "")
    if not text:
        return None
    for word in words if isinstance(words, tuple | list) else words_of(words):
        if _pattern(word).search(text):
            return word
    return None


def tag_in(title: Any, words: Any) -> str | None:
    """The listed word a title OPENS with: inside a leading bracket, or bare before : - | ."""
    text = str(title or "")
    listed = words if isinstance(words, tuple | list) else words_of(words)
    found = LEADING_TAG.match(text)
    if found is not None:
        return word_in(found.group(1), listed)
    for word in listed:
        if re.match(r"^\s*" + re.escape(word) + r"(?:\s*[:|]|\s+[-–—]\s)", text, re.IGNORECASE):
            return word
    return None


def is_certain(reason: Any) -> bool:
    text = str(reason or "")
    return text == REASON_TYPE or text.startswith(TAG_HEAD)


def _cell(row: Any, key: str) -> Any:
    if row is None:
        return None
    try:
        return row[key]
    except (IndexError, KeyError, TypeError):
        return getattr(row, key, None)


def day_blocks(runs: Any) -> list[tuple[datetime, datetime]]:
    """One block per chain of runs: its earliest start to its latest end, sheet or re-timed."""
    found: list[tuple[datetime, datetime]] = []
    for chain in chains(runs):
        marks = [
            at
            for row in chain
            for key in ("sheet_at", "scheduled_at", "sheet_ends_at", "ends_at")
            if (at := parse_ts(_cell(row, key))) is not None
        ]
        if marks:
            found.append((min(marks), max(marks)))
    return found


def run_around(
    paired: Any, now: datetime, lead_minutes: int = 0, tail_minutes: int = 0
) -> bool:
    """`paired` is (marathon, runs) each; a marathon with no timed run keeps its whole span."""
    for marathon, runs in paired or ():
        blocks = day_blocks(runs)
        if not blocks:
            if in_reach(span_of(marathon), now, lead_minutes, tail_minutes):
                return True
            continue
        if any(in_reach(block, now, lead_minutes, tail_minutes) for block in blocks):
            return True
    return False


def in_marathon(
    marathons: Any, now: datetime, lead_minutes: int = 0, tail_minutes: int = 0
) -> bool:
    return any(in_reach(span_of(one), now, lead_minutes, tail_minutes) for one in marathons or ())


def verdict(
    title: Any,
    stream_type: Any = None,
    *,
    words: Any = (),
    live_words: Any = (),
    marathon: bool = False,
    tag_certain: bool = False,
) -> Verdict:
    """Twitch's rerun mark and a leading tag are certain; any other title word is fuzzy, and
    fuzzy is live."""
    if str(stream_type or "").strip().casefold() == TYPE_RERUN:
        return Verdict(True, REASON_TYPE)
    tagged = tag_in(title, words) if tag_certain else None
    if tagged is not None:
        return Verdict(True, TAG_HEAD + tagged, matched=tagged)
    matched = word_in(title, words)
    if matched is None:
        return Verdict(False)
    if marathon:
        return Verdict(False, overruled=OVERRULED_MARATHON, matched=matched)
    live = word_in(title, live_words)
    if live is not None:
        return Verdict(False, overruled=LIVE_HEAD + live, matched=matched)
    return Verdict(True, TITLE_HEAD + matched, matched=matched)


def is_replay(session: Any) -> bool:
    return bool(_cell(session, "replay_reason")) and not _cell(session, "replay_cleared")


def reason_words(reason: Any, type_words: str, title_words: str, tag_words: str = "") -> str:
    text = str(reason or "")
    if text.startswith(TAG_HEAD):
        return (tag_words or title_words).replace("{word}", text[len(TAG_HEAD) :])
    if text.startswith(TITLE_HEAD):
        return title_words.replace("{word}", text[len(TITLE_HEAD) :])
    return type_words


def state_line(
    session: Any, state: str, type_words: str, title_words: str, tag_words: str = ""
) -> str | None:
    if not is_replay(session):
        return None
    reason = reason_words(_cell(session, "replay_reason"), type_words, title_words, tag_words)
    return state.replace("{reason}", reason)


def cleared_because(reason: Any, now: Verdict, action: Any) -> str:
    """Why a replay session became live without staff: the key, a marathon, or the stream."""
    if action == LIVE:
        return CLEARED_ACTION
    if now.overruled == OVERRULED_MARATHON:
        return CLEARED_MARATHON
    return CLEARED_TYPE if reason == REASON_TYPE else CLEARED_TITLE
