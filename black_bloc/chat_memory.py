from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from .chat import has_phrase, normalise

log = logging.getLogger(__name__)

DM = "dm"
SERVER = "server"
SCOPES = (DM, SERVER)

OFF = "off"
ON = "on"
MEMORY_MODES = (OFF, ON)
OPTOUT = "optout"
OPTIN = "optin"
CONSENT_CHOICES = (OPTOUT, OPTIN)
SEPARATE = "separate"
SHARED = "shared"
DM_SCOPES = (SEPARATE, SHARED)
COUNTS = "counts"
FULL = "full"
STAFF_VIEWS = (COUNTS, FULL)

CALL_ME_CHARS = 40
NOTE_CHARS = 120
NOTES_MAX = 6
THREADS_MAX = 5
NOTES_CEILING = 20
THREADS_CEILING = 20
RETENTION_DAYS = 180
RETENTION_MAX_DAYS = 3650
QUOTE_RUN_WORDS = 6
DISTIL_MIN_TURNS = 2
DISTIL_MAX_TURNS = 24

MODE_KEY = "chat_memory_mode"
CONSENT_KEY = "chat_memory_consent"
RETENTION_KEY = "chat_memory_retention_days"
DM_SCOPE_KEY = "chat_memory_dm_scope"
STAFF_VIEW_KEY = "chat_memory_staff_view"
NOTES_MAX_KEY = "chat_memory_notes_max"
THREADS_MAX_KEY = "chat_memory_threads_max"
MODEL_KEY = "chat_memory_model"

DISTILLED_KIND = "chat.memory_distilled"
DISTIL_FAILED_KIND = "chat.memory_distil_failed"
FORGOT_KIND = "chat.memory_forgot"
OPTOUT_KIND = "chat.memory_optout"
OPTIN_KIND = "chat.memory_optin"
EXPIRED_KIND = "chat.memory_expired"

MEMORY_TIER = "memory"

BY_SELF = "self"
BY_STAFF = "staff"
BY_LEAVE = "leave"
BY_EXPIRY = "expiry"

RULE_QUOTE = "quote"
RULE_THIRD = "third_person"
RULE_EVENT = "event"
RULE_AVAILABILITY = "availability"
RULE_SENSITIVE = "sensitive"
RULE_LONG = "too_long"
RULE_EMPTY = "empty"

QUOTE_MARKS = '"“”«»„‟`'

THIRD_PARTY: tuple[str, ...] = (
    "said",
    "says",
    "saying",
    "told",
    "telling",
    "mentioned",
    "according to",
    "their friend",
    "his friend",
    "her friend",
    "somebody else",
    "someone else",
    "everyone else",
    "the other person",
)

AVAILABILITY: tuple[str, ...] = (
    "usually on",
    "usually online",
    "usually around",
    "online at",
    "online around",
    "logs on",
    "logs in",
    "is online",
    "is offline",
    "is available",
    "available at",
    "available on",
    "free at",
    "free on",
    "busy at",
    "busy on",
    "off on",
    "works nights",
    "works days",
    "night shift",
    "day shift",
    "shift",
    "timezone",
    "time zone",
    "utc",
    "gmt",
    "lives in",
    "based in",
    "located in",
    "weekends",
    "weekdays",
    "schedule",
    "asleep",
    "awake",
    "at work",
    "in school",
)

EVENTS: tuple[str, ...] = (
    "yesterday",
    "today",
    "tonight",
    "last night",
    "last week",
    "this morning",
    "this afternoon",
    "earlier",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "was banned",
    "got banned",
    "was warned",
    "got warned",
    "was muted",
    "was kicked",
    "was timed out",
    "joined the call",
    "left the server",
    "streamed",
    "posted",
    "complained",
    "argued",
    "apologised",
    "apologized",
)

OUTCOMES: tuple[str, ...] = (
    "won",
    "lost",
    "died",
    "quit",
    "quits",
    "quitting",
    "leaving",
    "departure",
    "departures",
    "finished",
    "failed",
    "banned",
    "kicked",
    "muted",
    "warned",
    "timed out",
    "was declined",
)

OTHER_NAME_CHARS = 3
OTHER_NAMES_MAX = 2000

SENSITIVE: tuple[str, ...] = (
    "depressed",
    "depression",
    "anxiety",
    "anxious",
    "adhd",
    "autistic",
    "autism",
    "bipolar",
    "therapy",
    "therapist",
    "medication",
    "meds",
    "diagnosed",
    "disabled",
    "disability",
    "illness",
    "surgery",
    "christian",
    "muslim",
    "jewish",
    "hindu",
    "buddhist",
    "atheist",
    "religion",
    "religious",
    "church",
    "mosque",
    "synagogue",
    "republican",
    "democrat",
    "conservative",
    "liberal",
    "politics",
    "political",
    "voted",
    "gay",
    "lesbian",
    "bisexual",
    "asexual",
    "queer",
    "years old",
    "age",
    "aged",
    "born in",
    "birthday",
    "minor",
    "underage",
    "broke",
    "poor",
    "rich",
    "salary",
    "wage",
    "rent",
    "unemployed",
    "money",
    "paycheck",
    "bills",
    "debt",
)

MEMORY_OPENER = (
    "(What you remember about this person from earlier chats — preferences only; never claim "
    "they are online, free or anywhere in particular:"
)
MEMORY_CLOSER = ")"
CALL_ME_PART = "they go by {name}"
THREADS_PART = "still open: {threads}"

DISTIL_SYSTEM = (
    "You keep a tiny profile of ONE person so a chat bot can talk to them better next time.\n"
    "Answer with one JSON object and nothing else, exactly these three keys:\n"
    '{{"call_me": string or null, "notes": [string], "threads": [string]}}\n'
    "call_me — what they want to be called, at most {call_me_chars} characters, only if they "
    "said so themselves; otherwise null.\n"
    "notes — at most {notes_max} durable preferences about HOW TO TREAT THIS PERSON, at most "
    "{note_chars} characters each.\n"
    "threads — at most {threads_max} topics they were asking about, at most {note_chars} "
    "characters each, a topic only and never an outcome.\n"
    "KEEP: what to call them, how they like to be talked to, and standing facts they stated "
    "about themselves.\n"
    "THROW AWAY: quotes of anything anybody said, anything about another person, anything that "
    "HAPPENED (events, dates, outcomes), when they are online or free, where they live, their "
    "schedule, and anything about health, religion, politics, sexuality, age or money.\n"
    "Write every note in your own words, in the third person, about this one person.\n"
    "Empty lists are a good answer when there is nothing worth keeping.\n"
    "JSON only. No prose, no code fence, no extra keys."
)

DISTIL_USER = "The profile so far:\n{profile}\n\nThe conversation that just ended:\n{turns}"
NOTHING_SAID = "(nothing)"


def shingles(turns: Any, run: int = QUOTE_RUN_WORDS) -> set[str]:
    """Every `run`-word phrase anybody actually typed, so a note cannot quote one back."""
    found: set[str] = set()
    for turn in turns or ():
        words = normalise(turn_text(turn)).split()
        for start in range(0, max(0, len(words) - run + 1)):
            found.add(" ".join(words[start : start + run]))
    return found


def turn_text(turn: Any) -> str:
    if isinstance(turn, dict):
        return str(turn.get("content") or "")
    try:
        return str(turn["content"])
    except (TypeError, KeyError, IndexError):
        return str(getattr(turn, "content", "") or "")


def turn_speaker(turn: Any) -> str:
    if isinstance(turn, dict):
        return str(turn.get("speaker") or "")
    try:
        return str(turn["speaker"])
    except (TypeError, KeyError, IndexError):
        return str(getattr(turn, "speaker", "") or "")


def other_names(guild: Any, user_id: Any) -> tuple[str, ...]:
    """Everybody else's display name, so a note that names one of them can be recognised."""
    mine = int(user_id or 0)
    found: list[str] = []
    for member in list(getattr(guild, "members", ()) or ())[:OTHER_NAMES_MAX]:
        if int(getattr(member, "id", 0) or 0) == mine or getattr(member, "bot", False):
            continue
        name = normalise(getattr(member, "display_name", "") or getattr(member, "name", ""))
        if len(name) >= OTHER_NAME_CHARS:
            found.append(name)
    return tuple(dict.fromkeys(found))


def why_dropped(
    text: Any, *, quoted: Any = (), thread: bool = False, others: Any = ()
) -> str | None:
    """The rule a note breaks, by name, or None when it may be kept."""
    said = str(text or "").strip()
    if not said:
        return RULE_EMPTY
    if len(said) > NOTE_CHARS:
        return RULE_LONG
    if any(mark in said for mark in QUOTE_MARKS):
        return RULE_QUOTE
    if "<@" in said or "@" in said:
        return RULE_THIRD
    words = normalise(said)
    if not words:
        return RULE_EMPTY
    if any(has_phrase(words, phrase) for phrase in THIRD_PARTY):
        return RULE_THIRD
    if any(has_phrase(words, name) for name in others or ()):
        return RULE_THIRD
    if any(has_phrase(words, phrase) for phrase in AVAILABILITY):
        return RULE_AVAILABILITY
    if any(has_phrase(words, phrase) for phrase in SENSITIVE):
        return RULE_SENSITIVE
    against = OUTCOMES if thread else (*EVENTS, *OUTCOMES)
    if any(has_phrase(words, phrase) for phrase in against):
        return RULE_EVENT
    run = words.split()
    for start in range(0, max(0, len(run) - QUOTE_RUN_WORDS + 1)):
        if " ".join(run[start : start + QUOTE_RUN_WORDS]) in (quoted or ()):
            return RULE_QUOTE
    return None


@dataclass(frozen=True)
class Note:
    text: str
    where: str = SERVER
    at: str = ""

    def as_dict(self) -> dict[str, str]:
        return {"text": self.text, "where": self.where, "at": self.at}


@dataclass(frozen=True)
class Profile:
    call_me: str = ""
    notes: tuple[Note, ...] = ()
    threads: tuple[Note, ...] = ()
    turns_seen: int = 0
    created_at: str = ""
    updated_at: str = ""

    @property
    def empty(self) -> bool:
        return not (self.call_me or self.notes or self.threads)

    def visible(self, *, in_dm: bool, shared: bool = False) -> Profile:
        """A public channel never sees what was learned in a DM, whatever the prompt says."""
        if in_dm or shared:
            return self
        return Profile(
            call_me=self.call_me,
            notes=tuple(one for one in self.notes if one.where != DM),
            threads=tuple(one for one in self.threads if one.where != DM),
            turns_seen=self.turns_seen,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


@dataclass(frozen=True)
class Distilled:
    call_me: str = ""
    notes: tuple[str, ...] = ()
    threads: tuple[str, ...] = ()
    dropped: tuple[str, ...] = ()

    @property
    def empty(self) -> bool:
        return not (self.call_me or self.notes or self.threads)


def notes_of(raw: Any) -> tuple[Note, ...]:
    found: list[Note] = []
    for one in raw or ():
        if not isinstance(one, dict):
            continue
        text = str(one.get("text") or "").strip()
        if not text:
            continue
        where = str(one.get("where") or SERVER)
        found.append(Note(text=text, where=where if where in SCOPES else SERVER,
                          at=str(one.get("at") or "")))
    return tuple(found)


def loaded(raw: Any) -> Any:
    try:
        return json.loads(str(raw or "[]"))
    except (TypeError, ValueError):
        return []


def profile_from_row(row: Any) -> Profile:
    return Profile(
        call_me=str(row["call_me"] or ""),
        notes=notes_of(loaded(row["notes"])),
        threads=notes_of(loaded(row["threads"])),
        turns_seen=int(row["turns_seen"] or 0),
        created_at=str(row["created_at"] or ""),
        updated_at=str(row["updated_at"] or ""),
    )


def profile_json(profile: Profile) -> str:
    return json.dumps(
        {
            "call_me": profile.call_me or None,
            "notes": [one.text for one in profile.notes],
            "threads": [one.text for one in profile.threads],
        },
        ensure_ascii=False,
    )


def transcript(turns: Any) -> str:
    lines = [
        f"{turn_speaker(turn) or 'member'}: {turn_text(turn)}"
        for turn in list(turns or ())[-DISTIL_MAX_TURNS:]
        if turn_text(turn).strip()
    ]
    return "\n".join(lines) if lines else NOTHING_SAID


def distil_prompt(
    profile: Profile | None,
    turns: Any,
    *,
    where: str = SERVER,
    shared: bool = False,
    notes_max: int = NOTES_MAX,
    threads_max: int = THREADS_MAX,
) -> tuple[str, list[dict[str, str]]]:
    """The strict-JSON instruction, the profile this scope may see, and the expired turns."""
    seen = (profile or Profile()).visible(in_dm=where == DM, shared=shared)
    system = DISTIL_SYSTEM.format(
        call_me_chars=CALL_ME_CHARS,
        note_chars=NOTE_CHARS,
        notes_max=max(1, int(notes_max)),
        threads_max=max(1, int(threads_max)),
    )
    said = DISTIL_USER.format(profile=profile_json(seen), turns=transcript(turns))
    return (system, [{"role": "user", "content": said}])


def json_object(text: Any) -> Any:
    """A code fence is the one wrapper tolerated; anything else that is not an object is None."""
    said = str(text or "").strip()
    if said.startswith("```"):
        said = said.split("\n", 1)[1] if "\n" in said else ""
        said = said.rsplit("```", 1)[0].strip()
    try:
        found = json.loads(said)
    except (TypeError, ValueError):
        return None
    return found if isinstance(found, dict) else None


DISTIL_KEYS = frozenset({"call_me", "notes", "threads"})


def parse_distilled(text: Any, *, turns: Any = (), others: Any = ()) -> Distilled | None:
    """Bad JSON, unknown keys or an over-long call_me are a no-op; one bad note is dropped."""
    found = json_object(text)
    if found is None or not DISTIL_KEYS.issuperset(found):
        return None
    call_me = found.get("call_me")
    if call_me is not None and not isinstance(call_me, str):
        return None
    name = " ".join(str(call_me or "").split())
    if len(name) > CALL_ME_CHARS:
        return None
    quoted = shingles(turns)
    dropped: list[str] = []
    broke_name = why_dropped(name, quoted=quoted, others=others) if name else None
    if broke_name is not None:
        dropped.append(broke_name)
        name = ""
    kept: dict[str, list[str]] = {"notes": [], "threads": []}
    for field in ("notes", "threads"):
        raw = found.get(field, [])
        if raw is None:
            raw = []
        if not isinstance(raw, list):
            return None
        for one in raw:
            if not isinstance(one, str):
                return None
            broke = why_dropped(
                one, quoted=quoted, thread=field == "threads", others=others
            )
            if broke is not None:
                dropped.append(broke)
                continue
            kept[field].append(" ".join(one.split()))
    return Distilled(
        call_me=name,
        notes=tuple(kept["notes"]),
        threads=tuple(kept["threads"]),
        dropped=tuple(dropped),
    )


def widest(first: str, second: str) -> str:
    return SERVER if SERVER in (first, second) else DM


def merged_notes(
    fresh: Any, old: Any, *, where: str, at: str, limit: int
) -> tuple[Note, ...]:
    """Newest first, deduped by the words themselves; a note seen in both scopes stays public."""
    found: list[Note] = []
    seen: dict[str, int] = {}
    for text in fresh or ():
        key = normalise(text)
        if key in seen:
            continue
        seen[key] = len(found)
        found.append(Note(text=str(text), where=where, at=at))
    for note in old or ():
        key = normalise(note.text)
        at_index = seen.get(key)
        if at_index is not None:
            standing = found[at_index]
            found[at_index] = Note(
                text=standing.text,
                where=widest(standing.where, note.where),
                at=standing.at,
            )
            continue
        seen[key] = len(found)
        found.append(note)
    return tuple(found[: max(0, int(limit))])


def merge(
    old: Profile | None,
    new: Distilled,
    *,
    where: str = SERVER,
    at: str = "",
    notes_max: int = NOTES_MAX,
    threads_max: int = THREADS_MAX,
    seen: int = 0,
) -> Profile:
    """Newest wins on the name; notes and threads keep the newest of each, capped."""
    standing = old or Profile()
    when = at or datetime.now(UTC).isoformat()
    return Profile(
        call_me=(new.call_me or standing.call_me)[:CALL_ME_CHARS],
        notes=merged_notes(new.notes, standing.notes, where=where, at=when, limit=notes_max),
        threads=merged_notes(
            new.threads, standing.threads, where=where, at=when, limit=threads_max
        ),
        turns_seen=int(standing.turns_seen) + max(0, int(seen)),
        created_at=standing.created_at or when,
        updated_at=when,
    )


def memory_note(profile: Profile | None, *, in_dm: bool, shared: bool = False) -> str:
    """The block that rides beside the people note; empty when there is nothing to say."""
    if profile is None:
        return ""
    seen = profile.visible(in_dm=in_dm, shared=shared)
    if seen.empty:
        return ""
    parts: list[str] = []
    if seen.call_me:
        parts.append(CALL_ME_PART.format(name=seen.call_me))
    parts.extend(one.text for one in seen.notes)
    if seen.threads:
        parts.append(THREADS_PART.format(threads="; ".join(one.text for one in seen.threads)))
    return f"{MEMORY_OPENER} {' · '.join(parts)}{MEMORY_CLOSER}"


def drop_matching(profile: Profile, text: Any) -> tuple[Profile, int]:
    """Whatever a person points at by a few of its words, gone — theirs to drop, one at a time."""
    wanted = normalise(text)
    if not wanted:
        return (profile, 0)
    notes = tuple(one for one in profile.notes if wanted not in normalise(one.text))
    threads = tuple(one for one in profile.threads if wanted not in normalise(one.text))
    call_me = "" if wanted in normalise(profile.call_me) and profile.call_me else profile.call_me
    gone = (
        len(profile.notes)
        - len(notes)
        + len(profile.threads)
        - len(threads)
        + (1 if call_me != profile.call_me else 0)
    )
    if not gone:
        return (profile, 0)
    return (
        Profile(
            call_me=call_me,
            notes=notes,
            threads=threads,
            turns_seen=profile.turns_seen,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        ),
        gone,
    )


async def profile_for(db: Any, user_id: Any, guild_id: Any) -> Profile | None:
    try:
        cur = await db.conn.execute(
            "SELECT * FROM chat_profiles WHERE user_id = ? AND guild_id = ?",
            (int(user_id or 0), int(guild_id or 0)),
        )
        row = await cur.fetchone()
    except Exception as exc:
        log.warning("chat memory: a profile was not read — %s: %s", type(exc).__name__, exc)
        return None
    return profile_from_row(row) if row is not None else None


async def save_profile(db: Any, user_id: Any, guild_id: Any, profile: Profile) -> bool:
    at = profile.updated_at or datetime.now(UTC).isoformat()
    try:
        await db.conn.execute(
            "INSERT INTO chat_profiles(user_id, guild_id, call_me, notes, threads, turns_seen, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, guild_id) DO UPDATE SET call_me = excluded.call_me, "
            "notes = excluded.notes, threads = excluded.threads, "
            "turns_seen = excluded.turns_seen, updated_at = excluded.updated_at",
            (
                int(user_id or 0),
                int(guild_id or 0),
                profile.call_me or None,
                json.dumps([one.as_dict() for one in profile.notes], ensure_ascii=False),
                json.dumps([one.as_dict() for one in profile.threads], ensure_ascii=False),
                int(profile.turns_seen),
                profile.created_at or at,
                at,
            ),
        )
        await db.conn.commit()
    except Exception as exc:
        log.warning("chat memory: a profile was not saved — %s: %s", type(exc).__name__, exc)
        return False
    return True


async def forget(db: Any, user_id: Any, guild_id: Any) -> bool:
    try:
        cur = await db.conn.execute(
            "DELETE FROM chat_profiles WHERE user_id = ? AND guild_id = ?",
            (int(user_id or 0), int(guild_id or 0)),
        )
        await db.conn.commit()
    except Exception as exc:
        log.warning("chat memory: a profile was not forgotten — %s: %s", type(exc).__name__, exc)
        return False
    return bool(cur.rowcount)


async def forget_everywhere(db: Any, user_id: Any) -> int:
    """A member who leaves is forgotten in every server at once (D3)."""
    try:
        cur = await db.conn.execute(
            "DELETE FROM chat_profiles WHERE user_id = ?", (int(user_id or 0),)
        )
        await db.conn.commit()
    except Exception as exc:
        log.warning("chat memory: a leaver was not forgotten — %s: %s", type(exc).__name__, exc)
        return 0
    return int(cur.rowcount or 0)


async def opted_out(db: Any, user_id: Any, guild_id: Any) -> bool:
    try:
        cur = await db.conn.execute(
            "SELECT 1 FROM chat_memory_optout WHERE user_id = ? AND guild_id = ?",
            (int(user_id or 0), int(guild_id or 0)),
        )
        row = await cur.fetchone()
    except Exception as exc:
        log.warning("chat memory: the opt-outs were not read — %s: %s", type(exc).__name__, exc)
        return True
    return row is not None


async def set_optout(db: Any, user_id: Any, guild_id: Any, *, at: str | None = None) -> bool:
    try:
        await db.conn.execute(
            "INSERT OR REPLACE INTO chat_memory_optout(user_id, guild_id, at) VALUES (?, ?, ?)",
            (int(user_id or 0), int(guild_id or 0), at or datetime.now(UTC).isoformat()),
        )
        await db.conn.commit()
    except Exception as exc:
        log.warning("chat memory: the opt-out was not saved — %s: %s", type(exc).__name__, exc)
        return False
    return True


async def clear_optout(db: Any, user_id: Any, guild_id: Any) -> bool:
    try:
        cur = await db.conn.execute(
            "DELETE FROM chat_memory_optout WHERE user_id = ? AND guild_id = ?",
            (int(user_id or 0), int(guild_id or 0)),
        )
        await db.conn.commit()
    except Exception as exc:
        log.warning("chat memory: the opt-out was not lifted — %s: %s", type(exc).__name__, exc)
        return False
    return bool(cur.rowcount)


async def expire(db: Any, *, days: int = RETENTION_DAYS, now: datetime | None = None) -> int:
    """A profile nobody has added to in `days` is deleted; 0 days keeps them forever."""
    if not int(days or 0):
        return 0
    before = ((now or datetime.now(UTC)) - timedelta(days=int(days))).isoformat()
    try:
        cur = await db.conn.execute(
            "DELETE FROM chat_profiles WHERE updated_at < ?", (before,)
        )
        await db.conn.commit()
    except Exception as exc:
        log.warning("chat memory: nothing was expired — %s: %s", type(exc).__name__, exc)
        return 0
    return int(cur.rowcount or 0)


async def profile_rows(db: Any, guild_id: Any) -> list[Any]:
    try:
        cur = await db.conn.execute(
            "SELECT * FROM chat_profiles WHERE guild_id = ? ORDER BY updated_at DESC",
            (int(guild_id or 0),),
        )
        return list(await cur.fetchall())
    except Exception as exc:
        log.warning("chat memory: the profiles were not listed — %s: %s", type(exc).__name__, exc)
        return []


async def optout_count(db: Any, guild_id: Any) -> int:
    try:
        cur = await db.conn.execute(
            "SELECT COUNT(*) AS found FROM chat_memory_optout WHERE guild_id = ?",
            (int(guild_id or 0),),
        )
        row = await cur.fetchone()
    except Exception as exc:
        log.warning("chat memory: the opt-outs were not counted — %s: %s", type(exc).__name__, exc)
        return 0
    return int(row["found"]) if row is not None else 0
