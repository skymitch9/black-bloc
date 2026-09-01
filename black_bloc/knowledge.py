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
SNIPPET_CHARS = 400
TOKEN_MIN = 2
TOKENS_MAX = 8
HITS_DEFAULT = 3
GROUNDING_BYTES = 6 * 1024
SECTIONS_MAX = 200

TITLE_LIMIT = 100
BODY_LIMIT = 4000
TAG_LIMIT = 40

ALL_OF = "all"
ANY_OF = "any"

WORD = re.compile(r"[^a-z0-9_./-]+")
SPACES = re.compile(r"\s+")

GROUNDING_OPENER = (
    "(What the server's notes say, for your answer — quote it rather than inventing:"
)
GROUNDING_CLOSER = ")"

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


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def tokenize(query: Any) -> tuple[str, ...]:
    """Lowercased, deduped, two characters or more, eight at most."""
    found: list[str] = []
    for raw in WORD.split(str(query or "").lower()):
        word = raw.strip()
        if len(word) < TOKEN_MIN or word in found:
            continue
        found.append(word)
        if len(found) >= TOKENS_MAX:
            break
    return tuple(found)


def occurrences(haystack: str, needle: str, cap: int = BODY_CAP) -> int:
    found = 0
    at = haystack.find(needle)
    while at != -1 and found < cap:
        found += 1
        at = haystack.find(needle, at + len(needle))
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
        if token in title:
            points += TITLE_WEIGHT
        if token in tag:
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
    )


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
        found.sort(key=lambda hit: (-hit.score, hit.title.lower(), hit.id))
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


def section_text(hit: Any) -> str:
    title = str(value_of(hit, "title")).strip()
    body = str(value_of(hit, "body")).strip()
    if not body:
        return title
    return f"{title}: {body}" if title else body


def grounding(hits: Any, budget: int = GROUNDING_BYTES) -> str:
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
    return f"{GROUNDING_OPENER} {' · '.join(kept)}{GROUNDING_CLOSER}"


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


def channel_sections(guild: Any) -> list[tuple[str, str, str]]:
    named: list[str] = []
    found: list[tuple[str, str, str]] = []
    for channel in getattr(guild, "text_channels", ()) or ():
        name = str(getattr(channel, "name", "") or "").strip()
        if not name:
            continue
        named.append(f"#{name}")
        topic = str(getattr(channel, "topic", "") or "").strip()
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


def role_sections(guild: Any) -> list[tuple[str, str, str]]:
    names = [
        str(getattr(role, "name", "") or "").strip()
        for role in getattr(guild, "roles", ()) or ()
        if str(getattr(role, "name", "") or "").strip() not in ("", "@everyone")
    ]
    if not names:
        return []
    return [("Roles in this server", shorten(", ".join(names), BODY_LIMIT), "role")]


def event_section(row: Any) -> tuple[str, str, str] | None:
    title = str(value_of(row, "title")).strip()
    if not title:
        return None
    when = str(value_of(row, "starts_at")).strip()
    where = str(value_of(row, "location")).strip()
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
    from .cogs.community.events import events_by_status
    from .cogs.community.role_menus import get_options, list_menus, picking_is_on
    from .events import APPROVED

    found = [*channel_sections(guild), *role_sections(guild)]
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
    return found


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
