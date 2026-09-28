from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from . import posts
from .events import clamp
from .logkinds import VIA_DISCORD
from .panels import Outcome, refusal
from .settings_store import (
    FRONTDOOR_EVENT_LABEL,
    FRONTDOOR_REQUEST_LABEL,
    FRONTDOOR_SHOW_EVENT,
    FRONTDOOR_SHOW_REQUEST,
    FRONTDOOR_SHOW_TICKET,
    FRONTDOOR_TEXT,
    FRONTDOOR_TICKET_LABEL,
    FRONTDOOR_TITLE,
    POSTS_BLOCK_FRONTDOOR_NAME,
    POSTS_BLOCK_FRONTDOOR_NAME_DEFAULT,
    REHEARSAL_NOTE,
)

FRONTDOOR = "frontdoor"
NAME_MAX = 80

UNKNOWN_BLOCK = (
    "There is no block called **{kind}**, so nothing was changed. Pick one from the **Add a "
    "block…** list."
)
BLOCK_ADDED_SAID = "The **{name}** block is on **{title}** now."
BLOCK_ALREADY_SAID = "The **{name}** block is already on **{title}**, so nothing changed."
BLOCK_REMOVED_SAID = "The **{name}** block is off **{title}** now."
BLOCK_NOT_ON = "**{title}** has no **{name}** block, so nothing was removed."
BLOCK_HELD_ELSEWHERE = (
    "The **{name}** block is on **{other}**, and it goes on one post at a time, so **{title}** "
    "was not changed. Remove it from **{other}** first."
)
BAD_ORDER = (
    "That order does not name each of **{title}**'s blocks exactly once, so nothing moved. "
    "Reload the page and try again."
)
ORDERED_SAID = "**{title}**'s blocks are in the new order."
ORDERED_LATER_SAID = " The message shows it the next time you press **Update the post**."
REDRAWN_SAID = "Every post carrying the **{name}** block is redrawn with its new words."
REDRAWN_LATER_SAID = (
    "The **{name}** block's words are saved. Posts carrying it pick them up on the next sweep, "
    "within five minutes."
)
HELD_BY = "on {title}"
HELD_BY_NOBODY = "on no post yet"


@dataclass(frozen=True)
class BlockKind:
    key: str
    name_key: str
    name_default: str
    exclusive: bool
    cache_column: str
    keys: tuple[str, ...]
    parts: Callable[[Any, Any, Any], Any]
    turned: Callable[..., Awaitable[tuple[Any, str]]]
    redraw: Callable[[Any, Any], Awaitable[bool]]


def door_parts(bot: Any, guild: Any, row: Any) -> Any:
    from .cogs.community.frontdoor import carried_parts

    return carried_parts(bot, guild, row)


async def door_turned(
    bot: Any, guild: Any, row: Any, actor: Any, wanted: bool, *, via: str = VIA_DISCORD
) -> tuple[Any, str]:
    return await posts.turn_carrying(bot, guild, row, actor, wanted, via=via)


async def door_redraw(bot: Any, guild: Any) -> bool:
    finder = getattr(bot, "get_cog", None)
    cog = finder("FrontDoor") if finder is not None else None
    redraw = getattr(cog, "redraw_now", None)
    if redraw is None:
        return False
    return bool(await redraw(guild))


KINDS: dict[str, BlockKind] = {
    FRONTDOOR: BlockKind(
        key=FRONTDOOR,
        name_key=POSTS_BLOCK_FRONTDOOR_NAME,
        name_default=POSTS_BLOCK_FRONTDOOR_NAME_DEFAULT,
        exclusive=True,
        cache_column="carries_door",
        keys=(
            FRONTDOOR_TITLE,
            FRONTDOOR_TEXT,
            FRONTDOOR_TICKET_LABEL,
            FRONTDOOR_REQUEST_LABEL,
            FRONTDOOR_EVENT_LABEL,
            FRONTDOOR_SHOW_TICKET,
            FRONTDOOR_SHOW_REQUEST,
            FRONTDOOR_SHOW_EVENT,
            REHEARSAL_NOTE,
        ),
        parts=door_parts,
        turned=door_turned,
        redraw=door_redraw,
    ),
}


def kind_of(kind: Any) -> BlockKind | None:
    return KINDS.get(str(kind or "").strip().casefold())


def name_of(store: Any, guild_id: int, found: BlockKind) -> str:
    return clamp(store.get(guild_id, found.name_key), NAME_MAX) or found.name_default


def attached_by_cache(row: Any) -> list[str]:
    """What the row's own columns say it carries, for the paths that cannot read the table."""
    return [key for key, found in KINDS.items() if posts.row_value(row, found.cache_column)]


def parts_of(bot: Any, guild: Any, row: Any, kinds: list[str]) -> dict[str, Any]:
    """Each attached kind's (embed, view, stamp), in the order given, skipping one that is off."""
    drawn: dict[str, Any] = {}
    for kind in kinds:
        found = KINDS.get(kind)
        parts = found.parts(bot, guild, row) if found is not None else None
        if parts is not None:
            drawn[kind] = parts
    return drawn


# --- the rows ---------------------------------------------------------------------------------


def now() -> str:
    return datetime.now(UTC).isoformat()


async def blocks_of(db: Any, post_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM post_blocks WHERE post_id = ? ORDER BY position, id", (int(post_id),)
    )
    return list(await cur.fetchall())


async def kinds_on(db: Any, post_id: int) -> list[str]:
    return [str(row["kind"]) for row in await blocks_of(db, post_id)]


async def blocks_in(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT post_blocks.*, posts.slug AS slug, posts.title AS title FROM post_blocks "
        "JOIN posts ON posts.id = post_blocks.post_id WHERE post_blocks.guild_id = ? "
        "ORDER BY post_blocks.post_id, post_blocks.position, post_blocks.id",
        (int(guild_id),),
    )
    return list(await cur.fetchall())


async def holder_of(db: Any, guild_id: int, kind: str, *, but: Any = None) -> Any:
    cur = await db.conn.execute(
        "SELECT posts.* FROM post_blocks JOIN posts ON posts.id = post_blocks.post_id "
        "WHERE post_blocks.guild_id = ? AND post_blocks.kind = ? AND post_blocks.post_id != ? "
        "ORDER BY post_blocks.post_id LIMIT 1",
        (int(guild_id), str(kind), int(but or 0)),
    )
    return await cur.fetchone()


async def keep_cache(db: Any, post_id: int) -> None:
    """Each kind's column on the post says what the table says, and nothing else writes it."""
    have = set(await kinds_on(db, post_id))
    for key, found in KINDS.items():
        await db.conn.execute(
            f"UPDATE posts SET {found.cache_column} = ? WHERE id = ?",
            (1 if key in have else 0, int(post_id)),
        )
    await db.conn.commit()


async def attach(db: Any, row: Any, kind: str, *, by: Any = None) -> bool:
    found = KINDS[kind]
    post_id = int(row["id"])
    cur = await db.conn.execute(
        "SELECT COALESCE(MAX(position), -1) + 1 AS n FROM post_blocks WHERE post_id = ?",
        (post_id,),
    )
    position = int((await cur.fetchone())["n"])
    cur = await db.conn.execute(
        "INSERT OR IGNORE INTO post_blocks(guild_id, post_id, kind, position, exclusive, "
        "added_at, added_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            int(row["guild_id"]),
            post_id,
            kind,
            position,
            1 if found.exclusive else 0,
            now(),
            int(by) if by else None,
        ),
    )
    if not (cur.rowcount and cur.rowcount > 0):
        await keep_cache(db, post_id)
        return False
    await keep_cache(db, post_id)
    return True


async def detach(db: Any, post_id: int, kind: str) -> bool:
    cur = await db.conn.execute(
        "DELETE FROM post_blocks WHERE post_id = ? AND kind = ?", (int(post_id), str(kind))
    )
    gone = bool(cur.rowcount and cur.rowcount > 0)
    await keep_cache(db, post_id)
    return gone


async def set_carried(db: Any, post_id: int, kind: str, wanted: bool, *, by: Any = None) -> bool:
    row = await posts.get_post_by_id(db, int(post_id))
    if row is None:
        return False
    if not wanted:
        return await detach(db, int(post_id), kind)
    if kind in await kinds_on(db, int(post_id)):
        return True
    return await attach(db, row, kind, by=by)


async def reorder(db: Any, post_id: int, kinds: list[str]) -> None:
    for position, kind in enumerate(kinds):
        await db.conn.execute(
            "UPDATE post_blocks SET position = ? WHERE post_id = ? AND kind = ?",
            (position, int(post_id), kind),
        )
    await db.conn.commit()


async def attach_seeded(db: Any, row: Any, kinds: Any) -> None:
    """A shipped post's blocks, once, when the seed makes the post; a later boot never adds."""
    for kind in kinds or ():
        found = kind_of(kind)
        if found is None:
            continue
        if found.exclusive and await holder_of(db, int(row["guild_id"]), found.key) is not None:
            continue
        await attach(db, row, found.key)


# --- the moves --------------------------------------------------------------------------------


async def add_block(
    bot: Any, guild: Any, row: Any, actor: Any, kind: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    found = kind_of(kind)
    if found is None:
        return refusal(UNKNOWN_BLOCK.format(kind=str(kind or "")[:40]), "unknown_block", 400)
    title = str(posts.row_value(row, "title", ""))
    name = name_of(bot.store, guild.id, found)
    post_id = int(row["id"])
    if found.key in await kinds_on(bot.db, post_id):
        return Outcome(True, BLOCK_ALREADY_SAID.format(name=name, title=title), value=row)
    held = await held_elsewhere(bot, guild, found, post_id, title)
    if held is not None:
        return held
    if not await attach(bot.db, row, found.key, by=posts.actor_id(actor)):
        return await held_elsewhere(bot, guild, found, post_id, title) or refusal(
            BLOCK_HELD_ELSEWHERE.format(name=name, other="another post", title=title),
            "block_held_elsewhere",
            409,
        )
    fresh = await posts.get_post_by_id(bot.db, post_id)
    await posts.note(
        bot,
        guild,
        fresh,
        posts.SAVED,
        actor,
        via=via,
        block_added=found.key,
        **{found.cache_column: True},
    )
    fresh, more = await found.turned(bot, guild, fresh, actor, True, via=via)
    return Outcome(True, BLOCK_ADDED_SAID.format(name=name, title=title) + more, value=fresh)


async def held_elsewhere(
    bot: Any, guild: Any, found: BlockKind, post_id: int, title: str
) -> Outcome | None:
    if not found.exclusive:
        return None
    other = await holder_of(bot.db, guild.id, found.key, but=post_id)
    if other is None:
        return None
    return refusal(
        BLOCK_HELD_ELSEWHERE.format(
            name=name_of(bot.store, guild.id, found),
            other=posts.row_value(other, "title", ""),
            title=title,
        ),
        "block_held_elsewhere",
        409,
    )


async def remove_block(
    bot: Any, guild: Any, row: Any, actor: Any, kind: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    found = kind_of(kind)
    if found is None:
        return refusal(UNKNOWN_BLOCK.format(kind=str(kind or "")[:40]), "unknown_block", 400)
    title = str(posts.row_value(row, "title", ""))
    name = name_of(bot.store, guild.id, found)
    post_id = int(row["id"])
    if not await detach(bot.db, post_id, found.key):
        return refusal(BLOCK_NOT_ON.format(name=name, title=title), "block_not_on", 409)
    fresh = await posts.get_post_by_id(bot.db, post_id)
    await posts.note(
        bot,
        guild,
        fresh,
        posts.SAVED,
        actor,
        via=via,
        block_removed=found.key,
        **{found.cache_column: False},
    )
    fresh, more = await found.turned(bot, guild, fresh, actor, False, via=via)
    return Outcome(True, BLOCK_REMOVED_SAID.format(name=name, title=title) + more, value=fresh)


async def order_blocks(
    bot: Any, guild: Any, row: Any, actor: Any, order: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    title = str(posts.row_value(row, "title", ""))
    post_id = int(row["id"])
    have = await kinds_on(bot.db, post_id)
    wanted = [str(one or "").strip().casefold() for one in (order or ())]
    if sorted(wanted) != sorted(have) or len(set(wanted)) != len(wanted):
        return refusal(BAD_ORDER.format(title=title), "bad_order", 400)
    if wanted == have:
        return Outcome(True, ORDERED_SAID.format(title=title), value=row)
    await reorder(bot.db, post_id, wanted)
    fresh = await posts.get_post_by_id(bot.db, post_id)
    await posts.note(bot, guild, fresh, posts.SAVED, actor, via=via, blocks_order=wanted)
    said = ORDERED_SAID.format(title=title)
    if posts.is_posted(fresh):
        said += ORDERED_LATER_SAID
    return Outcome(True, said, value=fresh)


async def redraw_kind(bot: Any, guild: Any, kind: Any) -> Outcome:
    """A block's words changed: every message carrying it is redrawn now, not on the sweep."""
    found = kind_of(kind)
    if found is None:
        return refusal(UNKNOWN_BLOCK.format(kind=str(kind or "")[:40]), "unknown_block", 400)
    name = name_of(bot.store, guild.id, found)
    ran = await found.redraw(bot, guild)
    said = REDRAWN_SAID if ran else REDRAWN_LATER_SAID
    return Outcome(True, said.format(name=name), value=ran)


# --- what the pages read ----------------------------------------------------------------------


def block_row(bot: Any, guild: Any, row: Any) -> dict[str, Any]:
    found = KINDS.get(str(row["kind"]))
    return {
        "kind": str(row["kind"]),
        "name": name_of(bot.store, guild.id, found) if found is not None else str(row["kind"]),
        "position": int(row["position"]),
        "added_at": row["added_at"],
        "added_by": str(row["added_by"]) if row["added_by"] else None,
    }


async def kinds_shape(bot: Any, guild: Any) -> list[dict[str, Any]]:
    """Every kind, where it is attached, and the keys its editor writes."""
    rows = await blocks_in(bot.db, guild.id)
    shaped = []
    for key, found in KINDS.items():
        on = [
            {"slug": str(one["slug"]), "title": str(one["title"])}
            for one in rows
            if str(one["kind"]) == key
        ]
        shaped.append(
            {
                "kind": key,
                "name": name_of(bot.store, guild.id, found),
                "name_key": found.name_key,
                "exclusive": found.exclusive,
                "keys": list(found.keys),
                "on": on,
                "where": HELD_BY.format(title=on[0]["title"]) if on else HELD_BY_NOBODY,
            }
        )
    return shaped


__all__ = [
    "BAD_ORDER",
    "BLOCK_ADDED_SAID",
    "BLOCK_ALREADY_SAID",
    "BLOCK_HELD_ELSEWHERE",
    "BLOCK_NOT_ON",
    "BLOCK_REMOVED_SAID",
    "FRONTDOOR",
    "KINDS",
    "ORDERED_LATER_SAID",
    "ORDERED_SAID",
    "REDRAWN_LATER_SAID",
    "REDRAWN_SAID",
    "UNKNOWN_BLOCK",
    "BlockKind",
    "add_block",
    "attach",
    "attach_seeded",
    "attached_by_cache",
    "block_row",
    "blocks_in",
    "blocks_of",
    "detach",
    "held_elsewhere",
    "holder_of",
    "keep_cache",
    "kind_of",
    "kinds_on",
    "kinds_shape",
    "name_of",
    "order_blocks",
    "parts_of",
    "redraw_kind",
    "remove_block",
    "reorder",
    "set_carried",
]
