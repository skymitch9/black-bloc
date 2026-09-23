from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

log = logging.getLogger(__name__)

STAFF = "staff"
SERVER = "server"
SOURCES: tuple[str, ...] = (STAFF, SERVER)

TITLE_WEIGHT = 8
TAG_WEIGHT = 4
BODY_CAP = 5
STRONG_WORDS = 2
SNIPPET_CHARS = 400
TOKEN_MIN = 3
TOKENS_MAX = 8
HITS_DEFAULT = 3
GROUNDING_BYTES = 6 * 1024
SECTIONS_MAX = 200

TITLE_LIMIT = 100
BODY_LIMIT = 4000
TAG_LIMIT = 40

EVERYONE = "@everyone"
ROLE_TAG = "role"
ROLE_HOLDERS_TITLE = "Who has the {role} role"
ROLE_HOLDERS_BODY = "{role} — {count} {word}: {names}."
ONE_MEMBER = "member"
SOME_MEMBERS = "members"

ALL_OF = "all"
ANY_OF = "any"

WORD = re.compile(r"[^a-z0-9_./-]+")
SPACES = re.compile(r"\s+")
EDGE = re.compile(r"[a-z0-9]")
TOKEN_EDGES = "._/-"
ROLE_NAMED = re.compile(
    "^" + re.escape(ROLE_HOLDERS_TITLE).replace(re.escape("{role}"), "(.+)") + "$", re.IGNORECASE
)
CHANNEL_MARK = "#"

STOP_WORDS: frozenset[str] = frozenset(
    """
    what up hey yo sup hi hello lol ok okay the a an and or is it its im i you u ya yall fam cousin
    whats wassup whatsup wsg hows how who whos where wheres when why which
    has have had does did doing done can could would should will wont cant dont didnt doesnt isnt
    aint get got gonna wanna for with this that thats there theres here are was were been be not
    just like about your yours our they them their she her him his we me my mine
    bro bruh man dude sis lmao lmfao haha hahaha hehe yeah yea yes yep nah nope thanks thank thx ty
    good morning afternoon evening night gm gn all any some one out into from then than too very
    really much well know going also because cause cuz still even tho though
    """.split()
)

GROUNDING_NOTE = (
    "These are notes for you from the server — use them silently: never quote, list or bullet "
    "them back, and mention a channel only when the person's question needs it. Do not invent "
    "anything they do not say."
)
GROUNDING_NOTE_KEY = "chat_grounding_note"
GROUNDING_FRAME = "({note} Notes: {notes})"

TITLE_NEEDED = "A note needs a title, so nothing was saved. One short line naming what it is about."
TITLE_TOO_LONG = (
    "A note's title has to be {limit} characters or fewer, so nothing was saved. The long version "
    "belongs in the note itself."
)
BODY_NEEDED = "A note needs something in it, so nothing was saved."
BODY_TOO_LONG = (
    "A note has to be {limit} characters or fewer, so nothing was saved. Split it into two notes "
    "with their own titles — the search answers with whole notes, and a shorter one answers better."
)
TAG_TOO_LONG = "A note's tag has to be {limit} characters or fewer, so nothing was saved."
TITLE_TAKEN = (
    "This server already has a note called **{title}**, so nothing was saved. Edit that one, or "
    "give this one a heading of its own."
)
NOT_A_SOURCE = (
    "**{given}** is not somewhere a note can come from. They are {known} — `staff` is written by "
    "hand, `server` is rewritten from Discord every day."
)
SERVER_ROW_IS_NOT_YOURS = (
    "That note is one Black Bloc writes from the server itself every day, so an edit would be "
    "overwritten by tomorrow. Change the channel, role or event it describes instead."
)


class KnowledgeError(ValueError):
    """A note was given something Black Bloc will not store."""


@dataclass(frozen=True)
class Hit:
    id: int
    title: str
    body: str
    source: str
    tag: str
    score: int
    snippet: str
    landed: int = 0


@dataclass(frozen=True)
class Found:
    hits: tuple[Hit, ...] = ()
    matched: str = ALL_OF
    scanned: int = 0
    total: int = 0
    terms: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.hits)

    def __len__(self) -> int:
        return len(self.hits)

    def __iter__(self) -> Any:
        return iter(self.hits)

    @property
    def strong(self) -> bool:
        return is_strong(self)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def tokenize(query: Any) -> tuple[str, ...]:
    """Lowercased whole words, stop words out, three characters or more, eight at most."""
    found: list[str] = []
    for raw in WORD.split(str(query or "").lower()):
        word = raw.strip().strip(TOKEN_EDGES)
        if len(word) < TOKEN_MIN or word in STOP_WORDS or word in found:
            continue
        found.append(word)
        if len(found) >= TOKENS_MAX:
            break
    return tuple(found)


def occurrences(haystack: str, needle: str, cap: int = BODY_CAP) -> int:
    """Whole-word landings only, so `up` never counts inside `upcoming`."""
    found = 0
    at = haystack.find(needle) if needle else -1
    while at != -1 and found < cap:
        before = haystack[at - 1] if at else ""
        after = haystack[at + len(needle) : at + len(needle) + 1]
        if not (EDGE.match(before) or EDGE.match(after)):
            found += 1
        at = haystack.find(needle, at + 1)
    return found


def value_of(row: Any, key: str, fallback: Any = "") -> Any:
    if isinstance(row, dict):
        found = row.get(key)
    else:
        try:
            found = row[key]
        except (KeyError, IndexError, TypeError):
            found = getattr(row, key, None)
    return fallback if found is None else found


def score(row: Any, tokens: tuple[str, ...], require: str) -> int:
    """Title beats tag beats body, and every token has to land unless the pass says otherwise."""
    title = str(value_of(row, "title")).lower()
    tag = str(value_of(row, "tag")).lower()
    body = str(value_of(row, "body")).lower()
    total = 0
    landed = 0
    for token in tokens:
        points = 0
        if whole_word(title, token):
            points += TITLE_WEIGHT
        if whole_word(tag, token):
            points += TAG_WEIGHT
        points += occurrences(body, token)
        if points:
            landed += 1
        total += points
    if require == ALL_OF and landed < len(tokens):
        return 0
    return total if landed else 0


def snippet_of(text: Any, tokens: tuple[str, ...]) -> str:
    """The window around the first token that lands, nudged to word boundaries."""
    said = str(text or "")
    lower = said.lower()
    at = -1
    for token in tokens:
        found = lower.find(token)
        if found != -1 and (at == -1 or found < at):
            at = found
    if at == -1:
        at = 0
    start = max(0, at - SNIPPET_CHARS // 3)
    end = min(len(said), start + SNIPPET_CHARS)
    if start > 0:
        space = said.find(" ", start)
        if space != -1 and space < start + 30:
            start = space + 1
    if end < len(said):
        space = said.rfind(" ", start, end)
        if space > start + SNIPPET_CHARS - 60:
            end = space
    body = SPACES.sub(" ", said[start:end]).strip()
    return f"{'…' if start > 0 else ''}{body}{'…' if end < len(said) else ''}"


def hit_from(row: Any, points: int, tokens: tuple[str, ...]) -> Hit:
    return Hit(
        id=int(value_of(row, "id", 0) or 0),
        title=str(value_of(row, "title")),
        body=str(value_of(row, "body")),
        source=str(value_of(row, "source", STAFF)),
        tag=str(value_of(row, "tag")),
        score=points,
        snippet=snippet_of(value_of(row, "body"), tokens),
        landed=len(landed_in(row, tokens)),
    )


def haystack_of(row: Any) -> str:
    return " ".join(str(value_of(row, name)) for name in ("title", "tag", "body")).lower()


def landed_in(row: Any, tokens: Any) -> tuple[str, ...]:
    """The distinct tokens that land on a note as whole words — what a hit is ranked by."""
    haystack = haystack_of(row)
    return tuple(token for token in tokens or () if whole_word(haystack, token))


def name_of(row: Any) -> str:
    """The channel or role a server note is named for, or nothing for a staff note."""
    title = str(value_of(row, "title")).strip()
    if title.startswith(CHANNEL_MARK):
        return title[len(CHANNEL_MARK) :].lower()
    if str(value_of(row, "tag")).lower() == ROLE_TAG:
        named = ROLE_NAMED.match(title)
        if named:
            return named.group(1).lower()
    return ""


def search(rows: Any, query: Any, limit: int = HITS_DEFAULT) -> Found:
    """Every token first, then any token — and the answer says which pass replied."""
    tokens = tokenize(query)
    everything = list(rows or ())
    if not tokens or not everything:
        return Found(terms=tokens)

    def run(require: str) -> list[Hit]:
        found = [
            hit_from(row, points, tokens)
            for row in everything
            if (points := score(row, tokens, require)) > 0
        ]
        found.sort(key=lambda hit: (-hit.landed, -hit.score, hit.title.lower(), hit.id))
        return found

    hits = run(ALL_OF)
    matched = ALL_OF
    if not hits and len(tokens) > 1:
        hits = run(ANY_OF)
        matched = ANY_OF
    return Found(
        hits=tuple(hits[: max(0, int(limit))]),
        matched=matched,
        scanned=len(everything),
        total=len(hits),
        terms=tokens,
    )


def whole_word(haystack: str, token: str) -> bool:
    """`hi` is not in `this`: a token counts only where a letter or digit does not touch it."""
    return occurrences(haystack, token, 1) > 0


def is_strong(found: Any) -> bool:
    """Two distinct words on the top note, or one word naming the channel or role it is about."""
    hits = tuple(getattr(found, "hits", ()) or ())
    terms = tuple(getattr(found, "terms", ()) or ())
    if not hits or not terms:
        return False
    landed = landed_in(hits[0], terms)
    if len(landed) >= STRONG_WORDS:
        return True
    name = name_of(hits[0])
    return bool(name) and any(whole_word(name, term) for term in landed)


def section_text(hit: Any) -> str:
    title = str(value_of(hit, "title")).strip()
    body = str(value_of(hit, "body")).strip()
    if not body:
        return title
    return f"{title}: {body}" if title else body


def grounding(hits: Any, budget: int = GROUNDING_BYTES, note: Any = None) -> str:
    """The notes that fit, whole. A section too big for what is left is DROPPED, never trimmed."""
    kept: list[str] = []
    spent = 0
    for hit in hits or ():
        said = section_text(hit)
        if not said:
            continue
        cost = len(said.encode("utf-8")) + 1
        if spent + cost > budget:
            log.debug("knowledge: a note was left out of the grounding, %d bytes over", cost)
            continue
        kept.append(said)
        spent += cost
    if not kept:
        return ""
    header = str(note or "").strip() or GROUNDING_NOTE
    return GROUNDING_FRAME.format(note=header, notes=" · ".join(kept))


def clean_title(value: Any) -> str:
    said = SPACES.sub(" ", str(value or "")).strip()
    if not said:
        raise KnowledgeError(TITLE_NEEDED)
    if len(said) > TITLE_LIMIT:
        raise KnowledgeError(TITLE_TOO_LONG.format(limit=TITLE_LIMIT))
    return said


def clean_body(value: Any) -> str:
    said = str(value or "").strip()
    if not said:
        raise KnowledgeError(BODY_NEEDED)
    if len(said) > BODY_LIMIT:
        raise KnowledgeError(BODY_TOO_LONG.format(limit=BODY_LIMIT))
    return said


def clean_tag(value: Any) -> str:
    said = SPACES.sub(" ", str(value or "")).strip().lower()
    if len(said) > TAG_LIMIT:
        raise KnowledgeError(TAG_TOO_LONG.format(limit=TAG_LIMIT))
    return said


def clean_source(value: Any) -> str:
    said = str(value or STAFF).strip().lower()
    if said not in SOURCES:
        raise KnowledgeError(NOT_A_SOURCE.format(given=str(value)[:40], known=", ".join(SOURCES)))
    return said


async def list_sections(db: Any, guild_id: int, source: str | None = None) -> list[Any]:
    if source is None:
        cur = await db.conn.execute(
            "SELECT * FROM knowledge_sections WHERE guild_id = ? ORDER BY source, id LIMIT ?",
            (int(guild_id), SECTIONS_MAX),
        )
    else:
        cur = await db.conn.execute(
            "SELECT * FROM knowledge_sections WHERE guild_id = ? AND source = ? ORDER BY id "
            "LIMIT ?",
            (int(guild_id), str(source), SECTIONS_MAX),
        )
    return list(await cur.fetchall())


async def get_section(db: Any, section_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM knowledge_sections WHERE id = ?", (int(section_id),)
    )
    return await cur.fetchone()


async def add_section(
    db: Any,
    guild_id: int,
    title: str,
    body: str,
    *,
    tag: str = "",
    source: str = STAFF,
    by: int | None = None,
) -> int:
    try:
        cur = await db.conn.execute(
            "INSERT INTO knowledge_sections(guild_id, title, body, source, tag, updated_at, "
            "updated_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (int(guild_id), str(title), str(body), str(source), str(tag), now_iso(), by),
        )
    except sqlite3.IntegrityError as exc:
        raise KnowledgeError(TITLE_TAKEN.format(title=str(title))) from exc
    await db.conn.commit()
    return int(cur.lastrowid)


async def update_section(db: Any, section_id: int, **fields: Any) -> None:
    parts, values = [], []
    for key in ("title", "body", "tag"):
        if key in fields:
            parts.append(f"{key} = ?")
            values.append(str(fields[key]))
    if not parts:
        return
    parts.append("updated_at = ?")
    values.append(now_iso())
    if "by" in fields:
        parts.append("updated_by = ?")
        values.append(fields["by"])
    values.append(int(section_id))
    try:
        await db.conn.execute(
            f"UPDATE knowledge_sections SET {', '.join(parts)} WHERE id = ?", values
        )
    except sqlite3.IntegrityError as exc:
        raise KnowledgeError(TITLE_TAKEN.format(title=str(fields.get("title", "")))) from exc
    await db.conn.commit()


async def remove_section(db: Any, section_id: int) -> bool:
    cur = await db.conn.execute(
        "DELETE FROM knowledge_sections WHERE id = ?", (int(section_id),)
    )
    await db.conn.commit()
    return bool(cur.rowcount)


def shorten(value: Any, limit: int) -> str:
    """The ingest trims rather than refuses — a long channel name must not stop the loop."""
    said = SPACES.sub(" ", str(value or "")).strip()
    return said if len(said) <= limit else f"{said[: limit - 1]}…"


def channel_sections(channels: Any, notes: Any = None) -> list[tuple[str, str, str]]:
    named: list[str] = []
    found: list[tuple[str, str, str]] = []
    for channel in channels or ():
        name = str(getattr(channel, "name", "") or "").strip()
        if not name:
            continue
        named.append(f"#{name}")
        topic = str((notes or {}).get(getattr(channel, "id", None)) or "").strip()
        topic = topic or str(getattr(channel, "topic", "") or "").strip()
        if topic:
            found.append((shorten(f"#{name}", TITLE_LIMIT), shorten(topic, BODY_LIMIT), "channel"))
    if named:
        found.insert(
            0,
            (
                "Channels in this server",
                shorten(", ".join(named), BODY_LIMIT),
                "channel",
            ),
        )
    return found


def role_names(guild: Any) -> list[tuple[Any, str]]:
    found = []
    for role in getattr(guild, "roles", ()) or ():
        name = str(getattr(role, "name", "") or "").strip()
        if name and name != EVERYONE:
            found.append((role, name))
    return found


def role_sections(guild: Any) -> list[tuple[str, str, str]]:
    names = [name for _, name in role_names(guild)]
    if not names:
        return []
    return [("Roles in this server", shorten(", ".join(names), BODY_LIMIT), ROLE_TAG)]


def role_holder_sections(guild: Any) -> list[tuple[str, str, str]]:
    """A small role is written out by name; a big one keeps the name-only row and nothing else."""
    from .chat_data import HOLDERS_SHOWN, holders_of

    found = []
    for role, name in role_names(guild):
        people = [
            one
            for one in getattr(role, "members", ()) or ()
            if not getattr(one, "bot", False)
        ]
        if len(people) > HOLDERS_SHOWN:
            continue
        held = holders_of(role)
        if not held:
            continue
        body = ROLE_HOLDERS_BODY.format(
            role=name,
            count=len(held),
            word=ONE_MEMBER if len(held) == 1 else SOME_MEMBERS,
            names=", ".join(held),
        )
        found.append(
            (
                shorten(ROLE_HOLDERS_TITLE.format(role=name), TITLE_LIMIT),
                shorten(body, BODY_LIMIT),
                ROLE_TAG,
            )
        )
    return found


def event_where(row: Any) -> str:
    """Schema 34: the place is a channel or a typed line, and `events` owns which."""
    from .events import read_where, where_line

    return where_line(read_where(row), linked=False).strip()


def event_section(row: Any) -> tuple[str, str, str] | None:
    title = str(value_of(row, "title")).strip()
    if not title:
        return None
    when = str(value_of(row, "starts_at")).strip()
    where = event_where(row)
    about = str(value_of(row, "description")).strip()
    body = f"An approved event starting {when}."
    if where:
        body = f"{body} Where: {where}."
    if about:
        body = f"{body} {about}"
    return (shorten(f"Event: {title}", TITLE_LIMIT), shorten(body, BODY_LIMIT), "event")


def menu_section(menu: Any, options: Any, guild: Any) -> tuple[str, str, str] | None:
    title = str(value_of(menu, "title") or value_of(menu, "name")).strip()
    if not title:
        return None
    names = []
    for option in options or ():
        label = str(value_of(option, "label")).strip()
        role = None
        get_role = getattr(guild, "get_role", None)
        if get_role is not None:
            role = get_role(int(value_of(option, "role_id", 0) or 0))
        names.append(label or str(getattr(role, "name", "") or "").strip())
    picks = ", ".join(name for name in names if name)
    if not picks:
        return None
    return (
        shorten(f"Role menu: {title}", TITLE_LIMIT),
        shorten(f"Members can pick these roles for themselves: {picks}.", BODY_LIMIT),
        "rolemenu",
    )


async def server_sections(bot: Any, guild: Any, db: Any) -> list[tuple[str, str, str]]:
    """What the server itself says about itself, as sections the search can read."""
    from .channel_notes import notes_or_nothing
    from .channel_reach import refresh
    from .cogs.community.role_menus import get_options, list_menus, picking_is_on
    from .directory import open_channels
    from .events import APPROVED, events_by_status

    notes = await notes_or_nothing(db, getattr(guild, "id", None))
    known = await refresh(bot, guild)
    found = [*channel_sections(open_channels(bot, guild, known), notes), *role_sections(guild)]
    now = datetime.now(UTC).isoformat()
    for row in await events_by_status(db, guild.id, (APPROVED,)):
        if str(value_of(row, "starts_at")) < now:
            continue
        section = event_section(row)
        if section is not None:
            found.append(section)
    if picking_is_on(bot, guild.id):
        for menu in await list_menus(db, guild.id):
            section = menu_section(menu, await get_options(db, value_of(menu, "id", 0)), guild)
            if section is not None:
                found.append(section)
    return [*found, *role_holder_sections(guild)]


async def replace_server_sections(db: Any, guild_id: int, sections: Any) -> int:
    """The daily loop owns every `server` row; staff rows are not touched by this."""
    rows = [row for row in sections or () if row]
    await db.conn.execute(
        "DELETE FROM knowledge_sections WHERE guild_id = ? AND source = ?",
        (int(guild_id), SERVER),
    )
    at = now_iso()
    written = 0
    for title, body, tag in rows[:SECTIONS_MAX]:
        cur = await db.conn.execute(
            "INSERT OR IGNORE INTO knowledge_sections(guild_id, title, body, source, tag, "
            "updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (int(guild_id), str(title), str(body), SERVER, str(tag), at),
        )
        written += int(cur.rowcount or 0)
    await db.conn.commit()
    return written
