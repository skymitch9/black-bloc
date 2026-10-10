from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import discord

from . import posts
from .actionlog import log_action
from .events import clamp
from .logkinds import VIA_DISCORD, kind_via
from .panels import Outcome, refusal
from .settings_store import (
    BIRTHDAY_BLOCK_LABEL,
    BIRTHDAY_BLOCK_OFF_SAID,
    BIRTHDAY_BLOCK_REFUSED_SAID,
    BIRTHDAY_BLOCK_SAVED_SAID,
    BIRTHDAY_BLOCK_TEXT,
    BIRTHDAY_BLOCK_TITLE,
    EVENTS_BLOCK_LABEL,
    EVENTS_BLOCK_TEXT,
    EVENTS_BLOCK_TITLE,
    EVENTS_UPCOMING_EMPTY,
    EVENTS_UPCOMING_LINE,
    EVENTS_UPCOMING_MAX,
    EVENTS_UPCOMING_TITLE,
    FRONTDOOR_EVENT_LABEL,
    FRONTDOOR_REQUEST_LABEL,
    FRONTDOOR_SHOW_EVENT,
    FRONTDOOR_SHOW_REQUEST,
    FRONTDOOR_SHOW_TICKET,
    FRONTDOOR_TEXT,
    FRONTDOOR_TICKET_LABEL,
    FRONTDOOR_TITLE,
    GOLIVE_BLOCK_EMPTY,
    GOLIVE_BLOCK_LINE,
    GOLIVE_BLOCK_MAX,
    GOLIVE_BLOCK_TITLE,
    GOLIVE_BLOCK_TITLE_CHARS,
    GOLIVE_BLOCK_UNTITLED,
    MARATHON_BLOCK_ADDED_SAID,
    MARATHON_BLOCK_LABEL,
    MARATHON_BLOCK_REMOVED_SAID,
    MARATHON_BLOCK_TEXT,
    MARATHON_BLOCK_TITLE,
    MARATHON_BLOCK_UNSET_SAID,
    MARATHON_ROLE_ID,
    PINGS_BLOCK_LABEL,
    PINGS_BLOCK_TEXT,
    PINGS_BLOCK_TITLE,
    POINTS_BOARD_ORDER,
    POINTS_FEATURE,
    POINTS_MODE,
    POINTS_TOP_N,
    POSTS_BLOCK_BIRTHDAY_NAME,
    POSTS_BLOCK_BIRTHDAY_NAME_DEFAULT,
    POSTS_BLOCK_FRONTDOOR_NAME,
    POSTS_BLOCK_FRONTDOOR_NAME_DEFAULT,
    POSTS_BLOCK_LEADERBOARD_NAME,
    POSTS_BLOCK_LEADERBOARD_NAME_DEFAULT,
    POSTS_BLOCK_LINKS_CARD,
    POSTS_BLOCK_LINKS_NAME,
    POSTS_BLOCK_LINKS_NAME_DEFAULT,
    POSTS_BLOCK_LINKS_ROWS,
    POSTS_BLOCK_LINKS_TEXT,
    POSTS_BLOCK_LINKS_TITLE,
    POSTS_BLOCK_LIVENOW_NAME,
    POSTS_BLOCK_LIVENOW_NAME_DEFAULT,
    POSTS_BLOCK_MARATHONROLE_NAME,
    POSTS_BLOCK_MARATHONROLE_NAME_DEFAULT,
    POSTS_BLOCK_PINGSFOLLOW_NAME,
    POSTS_BLOCK_PINGSFOLLOW_NAME_DEFAULT,
    POSTS_BLOCK_PROPOSEEVENT_NAME,
    POSTS_BLOCK_PROPOSEEVENT_NAME_DEFAULT,
    POSTS_BLOCK_TEMPVOICE_NAME,
    POSTS_BLOCK_TEMPVOICE_NAME_DEFAULT,
    POSTS_BLOCK_UPCOMING_NAME,
    POSTS_BLOCK_UPCOMING_NAME_DEFAULT,
    REHEARSAL_NOTE,
    TEMPVOICE_BLOCK_CONTROLS_LABEL,
    TEMPVOICE_BLOCK_LOBBY_LABEL,
    TEMPVOICE_BLOCK_SHOW_CONTROLS,
    TEMPVOICE_BLOCK_TEXT,
    TEMPVOICE_BLOCK_TITLE,
)

log = logging.getLogger(__name__)

FRONTDOOR = "frontdoor"
TEMPVOICE = "tempvoice"
MARATHONROLE = "marathonrole"
PINGSFOLLOW = "pingsfollow"
BIRTHDAY = "birthday"
PROPOSEEVENT = "proposeevent"
LIVENOW = "livenow"
UPCOMING = "upcoming"
LINKS = "links"
LEADERBOARD = "leaderboard"
LIVE_KINDS = (LIVENOW, UPCOMING, LEADERBOARD)
NAME_MAX = 80
MAX_EMBEDS = 10
MAX_ROWS = 5
MAX_COMPONENTS = 25
REDRAWN = "post.redrawn"

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
BLOCK_TOO_BIG = (
    "The **{name}** block does not fit on **{title}**: Discord allows one message {limit}, and "
    "with it this one would need {need}. Nothing was changed. Remove a block first, or put "
    "this one on another post."
)
LIMIT_WORDS = {
    "embeds": ("at most 10 cards", "{n} cards"),
    "rows": ("at most 5 rows of buttons", "{n} rows"),
    "components": ("at most 25 buttons and menus", "{n} buttons and menus"),
}
ORDERED_NOW_SAID = " The message shows the new order now."
DRAWN_NOW_SAID = " The message already up shows it now."
DRAWN_LATER_SAID = " The message shows it the next time you press **Update the post**."
DRAWN_OFF_SAID = " The message already up no longer shows it."
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
    footprint: tuple[int, int, int] = (1, 1, 5)
    load: Callable[[Any, Any], Awaitable[Any]] | None = None
    owner: tuple[str, str] | None = None


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


async def blocks_turned(
    bot: Any, guild: Any, row: Any, actor: Any, wanted: bool, *, via: str = VIA_DISCORD
) -> tuple[Any, str]:
    """A block with no feature-side keys of its own: the message already up is redrawn whole."""
    post_id = int(row["id"])
    if not posts.is_posted(row):
        return row, ""
    drew = await redraw_post(bot, guild, row, actor, via=via, force=True)
    fresh = await posts.get_post_by_id(bot.db, post_id)
    if not drew:
        return fresh, DRAWN_LATER_SAID
    return fresh, DRAWN_NOW_SAID if wanted else DRAWN_OFF_SAID


def voice_parts(bot: Any, guild: Any, row: Any) -> Any:
    from .cogs.community.tempvoice import block_parts

    return block_parts(bot, guild, row)


def marathon_role_parts(bot: Any, guild: Any, row: Any) -> Any:
    from .cogs.content.marathon_role import block_parts

    return block_parts(bot, guild, row)


def pings_parts(bot: Any, guild: Any, row: Any) -> Any:
    from .cogs.content.pings import block_parts

    return block_parts(bot, guild, row)


def birthday_parts(bot: Any, guild: Any, row: Any) -> Any:
    from .cogs.community.birthdays import block_parts

    return block_parts(bot, guild, row)


def propose_parts(bot: Any, guild: Any, row: Any) -> Any:
    from .cogs.community.events import block_parts

    return block_parts(bot, guild, row)


LOADED: dict[tuple[str, int], Any] = {}


def loaded(kind: str, guild_id: Any) -> Any:
    return LOADED.get((kind, int(guild_id)))


async def load_kinds(bot: Any, guild: Any, kinds: list[str]) -> None:
    """A live block's list is read here, before its sync draw; the others read nothing."""
    for kind in kinds:
        found = KINDS.get(kind)
        if found is not None and found.load is not None:
            LOADED[(kind, int(guild.id))] = await found.load(bot, guild)


def live_parts(bot: Any, guild: Any, row: Any) -> Any:
    from .cogs.content.golive import block_parts

    return block_parts(bot, guild, loaded(LIVENOW, guild.id))


async def live_load(bot: Any, guild: Any) -> Any:
    from .cogs.content.golive import block_streams

    return await block_streams(bot, guild)


def upcoming_parts(bot: Any, guild: Any, row: Any) -> Any:
    from .cogs.community.events import upcoming_block_parts

    return upcoming_block_parts(bot, guild, loaded(UPCOMING, guild.id))


async def upcoming_load(bot: Any, guild: Any) -> Any:
    from .cogs.community.events import upcoming_block_events

    return await upcoming_block_events(bot, guild)


def links_parts(bot: Any, guild: Any, row: Any) -> Any:
    from .link_buttons import links_parts as drawn

    return drawn(bot, guild, row)


def leaderboard_parts(bot: Any, guild: Any, row: Any) -> Any:
    from .points_post import block_parts

    return block_parts(bot, guild, loaded(LEADERBOARD, guild.id))


async def leaderboard_load(bot: Any, guild: Any) -> Any:
    from .points_post import block_rows

    return await block_rows(bot, guild)


async def blocks_redraw(bot: Any, guild: Any) -> bool:
    finder = getattr(bot, "get_cog", None)
    cog = finder("FrontDoor") if finder is not None else None
    redraw = getattr(cog, "redraw_blocks_now", None)
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
        footprint=(1, 1, 3),
    ),
    TEMPVOICE: BlockKind(
        key=TEMPVOICE,
        name_key=POSTS_BLOCK_TEMPVOICE_NAME,
        name_default=POSTS_BLOCK_TEMPVOICE_NAME_DEFAULT,
        exclusive=False,
        cache_column="",
        keys=(
            TEMPVOICE_BLOCK_TITLE,
            TEMPVOICE_BLOCK_TEXT,
            TEMPVOICE_BLOCK_LOBBY_LABEL,
            TEMPVOICE_BLOCK_CONTROLS_LABEL,
            TEMPVOICE_BLOCK_SHOW_CONTROLS,
        ),
        parts=voice_parts,
        turned=blocks_turned,
        redraw=blocks_redraw,
        footprint=(1, 1, 5),
    ),
    MARATHONROLE: BlockKind(
        key=MARATHONROLE,
        name_key=POSTS_BLOCK_MARATHONROLE_NAME,
        name_default=POSTS_BLOCK_MARATHONROLE_NAME_DEFAULT,
        exclusive=False,
        cache_column="",
        keys=(
            MARATHON_BLOCK_TITLE,
            MARATHON_BLOCK_TEXT,
            MARATHON_BLOCK_LABEL,
            MARATHON_BLOCK_ADDED_SAID,
            MARATHON_BLOCK_REMOVED_SAID,
            MARATHON_BLOCK_UNSET_SAID,
            MARATHON_ROLE_ID,
        ),
        parts=marathon_role_parts,
        turned=blocks_turned,
        redraw=blocks_redraw,
        footprint=(1, 1, 1),
    ),
    PINGSFOLLOW: BlockKind(
        key=PINGSFOLLOW,
        name_key=POSTS_BLOCK_PINGSFOLLOW_NAME,
        name_default=POSTS_BLOCK_PINGSFOLLOW_NAME_DEFAULT,
        exclusive=False,
        cache_column="",
        keys=(PINGS_BLOCK_TITLE, PINGS_BLOCK_TEXT, PINGS_BLOCK_LABEL),
        parts=pings_parts,
        turned=blocks_turned,
        redraw=blocks_redraw,
        footprint=(1, 1, 1),
    ),
    BIRTHDAY: BlockKind(
        key=BIRTHDAY,
        name_key=POSTS_BLOCK_BIRTHDAY_NAME,
        name_default=POSTS_BLOCK_BIRTHDAY_NAME_DEFAULT,
        exclusive=False,
        cache_column="",
        keys=(
            BIRTHDAY_BLOCK_TITLE,
            BIRTHDAY_BLOCK_TEXT,
            BIRTHDAY_BLOCK_LABEL,
            BIRTHDAY_BLOCK_SAVED_SAID,
            BIRTHDAY_BLOCK_REFUSED_SAID,
            BIRTHDAY_BLOCK_OFF_SAID,
        ),
        parts=birthday_parts,
        turned=blocks_turned,
        redraw=blocks_redraw,
        footprint=(1, 1, 1),
    ),
    PROPOSEEVENT: BlockKind(
        key=PROPOSEEVENT,
        name_key=POSTS_BLOCK_PROPOSEEVENT_NAME,
        name_default=POSTS_BLOCK_PROPOSEEVENT_NAME_DEFAULT,
        exclusive=False,
        cache_column="",
        keys=(EVENTS_BLOCK_TITLE, EVENTS_BLOCK_TEXT, EVENTS_BLOCK_LABEL),
        parts=propose_parts,
        turned=blocks_turned,
        redraw=blocks_redraw,
        footprint=(1, 1, 1),
    ),
    LIVENOW: BlockKind(
        key=LIVENOW,
        name_key=POSTS_BLOCK_LIVENOW_NAME,
        name_default=POSTS_BLOCK_LIVENOW_NAME_DEFAULT,
        exclusive=False,
        cache_column="",
        keys=(
            GOLIVE_BLOCK_TITLE,
            GOLIVE_BLOCK_LINE,
            GOLIVE_BLOCK_UNTITLED,
            GOLIVE_BLOCK_EMPTY,
            GOLIVE_BLOCK_MAX,
            GOLIVE_BLOCK_TITLE_CHARS,
        ),
        parts=live_parts,
        turned=blocks_turned,
        redraw=blocks_redraw,
        footprint=(1, 0, 0),
        load=live_load,
    ),
    UPCOMING: BlockKind(
        key=UPCOMING,
        name_key=POSTS_BLOCK_UPCOMING_NAME,
        name_default=POSTS_BLOCK_UPCOMING_NAME_DEFAULT,
        exclusive=False,
        cache_column="",
        keys=(
            EVENTS_UPCOMING_TITLE,
            EVENTS_UPCOMING_LINE,
            EVENTS_UPCOMING_EMPTY,
            EVENTS_UPCOMING_MAX,
        ),
        parts=upcoming_parts,
        turned=blocks_turned,
        redraw=blocks_redraw,
        footprint=(1, 0, 0),
        load=upcoming_load,
    ),
    LINKS: BlockKind(
        key=LINKS,
        name_key=POSTS_BLOCK_LINKS_NAME,
        name_default=POSTS_BLOCK_LINKS_NAME_DEFAULT,
        exclusive=False,
        cache_column="",
        keys=(
            POSTS_BLOCK_LINKS_ROWS,
            POSTS_BLOCK_LINKS_TITLE,
            POSTS_BLOCK_LINKS_TEXT,
            POSTS_BLOCK_LINKS_CARD,
        ),
        parts=links_parts,
        turned=blocks_turned,
        redraw=blocks_redraw,
        footprint=(1, 2, 10),
    ),
    LEADERBOARD: BlockKind(
        key=LEADERBOARD,
        name_key=POSTS_BLOCK_LEADERBOARD_NAME,
        name_default=POSTS_BLOCK_LEADERBOARD_NAME_DEFAULT,
        exclusive=False,
        cache_column="",
        keys=(
            "points_board_title",
            "points_board_xp_title",
            "points_board_line",
            "points_board_empty",
            POINTS_TOP_N,
            POINTS_BOARD_ORDER,
        ),
        parts=leaderboard_parts,
        turned=blocks_turned,
        redraw=blocks_redraw,
        footprint=(1, 0, 0),
        load=leaderboard_load,
        owner=(POINTS_MODE, POINTS_FEATURE),
    ),
}


def owner_of(kinds: Any) -> tuple[str, str] | None:
    """The feature whose mode and rehearsal home a post carrying these blocks follows."""
    for kind in kinds or ():
        found = KINDS.get(str(kind))
        if found is not None and found.owner is not None:
            return found.owner
    return None


def kind_of(kind: Any) -> BlockKind | None:
    return KINDS.get(str(kind or "").strip().casefold())


def name_of(store: Any, guild_id: int, found: BlockKind) -> str:
    return clamp(store.get(guild_id, found.name_key), NAME_MAX) or found.name_default


def attached_by_cache(row: Any) -> list[str]:
    """What the row's own columns say it carries, for the paths that cannot read the table."""
    return [
        key
        for key, found in KINDS.items()
        if found.cache_column and posts.row_value(row, found.cache_column)
    ]


def parts_of(bot: Any, guild: Any, row: Any, kinds: list[str]) -> dict[str, Any]:
    """Each attached kind's (embed, view, stamp), in the order given, skipping one that is off."""
    drawn: dict[str, Any] = {}
    for kind in kinds:
        found = KINDS.get(kind)
        parts = found.parts(bot, guild, row) if found is not None else None
        if parts is not None:
            drawn[kind] = parts
    return drawn


def footprint_of(row: Any, kinds: list[str]) -> dict[str, int]:
    """The most a message with these blocks can hold, whatever each feature draws today."""
    style = posts.wanted_style(posts.row_value(row, "style", posts.PLAIN))
    found = {"embeds": 1 if style == posts.EMBED else 0, "rows": 0, "components": 0}
    for kind in kinds:
        one = KINDS.get(kind)
        if one is None:
            continue
        embeds, rows, components = one.footprint
        found["embeds"] += embeds
        found["rows"] += rows
        found["components"] += components
    return found


def too_big(row: Any, kinds: list[str]) -> tuple[str, str] | None:
    """Discord's own caps on one message: 10 cards, 5 rows, 25 buttons and menus."""
    need = footprint_of(row, kinds)
    for part, cap in (("embeds", MAX_EMBEDS), ("rows", MAX_ROWS), ("components", MAX_COMPONENTS)):
        if need[part] > cap:
            limit, words = LIMIT_WORDS[part]
            return limit, words.format(n=need[part])
    return None


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


async def drawn_of(db: Any, post_id: int) -> dict[str, Any]:
    """Each attached block's stamp as the message in Discord shows it (None: not drawn)."""
    return {str(row["kind"]): row["drawn_hash"] for row in await blocks_of(db, post_id)}


async def set_drawn(db: Any, post_id: int, stamps: dict[str, Any]) -> None:
    """Every attached block's stamp after a send or an edit; the door's is mirrored on posts."""
    for kind in await kinds_on(db, post_id):
        stamp = stamps.get(kind)
        await db.conn.execute(
            "UPDATE post_blocks SET drawn_hash = ? WHERE post_id = ? AND kind = ?",
            (str(stamp) if stamp else None, int(post_id), kind),
        )
    await db.conn.commit()
    await posts.set_door_drawn(db, int(post_id), stamps.get(FRONTDOOR))


async def keep_cache(db: Any, post_id: int) -> None:
    """Each kind's column on the post says what the table says, and nothing else writes it."""
    have = set(await kinds_on(db, post_id))
    for key, found in KINDS.items():
        if not found.cache_column:
            continue
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
    over = too_big(row, [*await kinds_on(bot.db, post_id), found.key])
    if over is not None:
        return refusal(
            BLOCK_TOO_BIG.format(name=name, title=title, limit=over[0], need=over[1]),
            "block_too_big",
            409,
        )
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
        **({found.cache_column: True} if found.cache_column else {}),
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
        **({found.cache_column: False} if found.cache_column else {}),
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
        drew = await redraw_post(bot, guild, fresh, actor, via=via, force=True)
        said += ORDERED_NOW_SAID if drew else ORDERED_LATER_SAID
        fresh = await posts.get_post_by_id(bot.db, post_id)
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


# --- the message already up -------------------------------------------------------------------


def kept_part(message: Any) -> list[Any]:
    """The post's own card as it was posted; a plain post's words ride as content, untouched."""
    return [] if getattr(message, "content", "") else list(getattr(message, "embeds", [])[:1])


async def sticky_edit(bot: Any, guild: Any, row: Any) -> dict[str, Any] | None:
    """A sticky's post is drawn whole again, its rehearsal note too: the sticky reposts it fresh."""
    from . import shadow
    from . import sticky as sticky_rules
    from .sticky_posts import post_message

    owner = await sticky_rules.row_of_post(bot.db, int(row["id"]))
    if owner is None:
        return None
    channel_id = int(owner["channel_id"])
    rehearsing = int(owner["posted_channel_id"] or 0) != channel_id
    note = shadow.note_line(bot, guild, f"<#{channel_id}>") if rehearsing else ""
    payload, _ = await post_message(bot, guild, row, note)
    return payload


async def needs_redraw(bot: Any, row: Any, kinds: list[str], stamps: dict[str, Any]) -> bool:
    have = await drawn_of(bot.db, int(row["id"]))
    if any((stamps.get(kind) or None) != (have.get(kind) or None) for kind in kinds):
        return True
    return (stamps.get(FRONTDOOR) or None) != (posts.row_value(row, "door_hash") or None)


async def redraw_post(
    bot: Any,
    guild: Any,
    row: Any,
    actor: Any = None,
    *,
    via: str = VIA_DISCORD,
    force: bool = False,
    done_kind: str = REDRAWN,
    failed_kind: str = posts.POST_FAILED,
) -> bool:
    """The message already up is rebuilt: the post's part as posted, then every block, fresh."""
    post_id = int(row["id"])
    kinds = await kinds_on(bot.db, post_id)
    await load_kinds(bot, guild, kinds)
    drawn = parts_of(bot, guild, row, kinds)
    stamps = {kind: parts[2] for kind, parts in drawn.items()}
    if not force and not await needs_redraw(bot, row, kinds, stamps):
        return False
    if posts.row_value(row, "message_id") and not posts.guard_allows(
        bot, posts.row_value(row, "channel_id")
    ):
        return False
    message = await posts.posted_message(bot, guild, row)
    if message is None:
        return False
    edit = await sticky_edit(bot, guild, row)
    if edit is None:
        made = posts.with_blocks({"content": None, "embed": None}, list(drawn.values()))
        edit = {"embeds": kept_part(message) + made["embeds"], "view": made["view"]}
    try:
        await message.edit(**edit, allowed_mentions=discord.AllowedMentions.none())
    except discord.HTTPException as exc:
        log.warning("post blocks: could not redraw %s: %s", posts.row_value(row, "slug"), exc)
        await log_action(
            bot,
            guild,
            failed_kind,
            actor=actor,
            details={
                "slug": posts.row_value(row, "slug"),
                "message_id": int(message.id),
                "reason": f"{type(exc).__name__}: {exc}",
            },
        )
        return False
    await set_drawn(bot.db, post_id, stamps)
    await log_action(
        bot,
        guild,
        kind_via(done_kind, via),
        actor=actor,
        details={
            "slug": posts.row_value(row, "slug"),
            "post_id": post_id,
            "message_id": int(message.id),
            "drawn": stamps.get(FRONTDOOR) is not None,
            "blocks": list(stamps),
            "via": via,
        },
    )
    return True


async def keep_drawn(bot: Any, guild: Any, kinds: Any = None) -> int:
    """The sweep's half for every carrier the door does not ride: changed words are redrawn."""
    only = tuple(kinds or ())
    marks = f" AND post_blocks.kind IN ({', '.join('?' for _ in only)})" if only else ""
    cur = await bot.db.conn.execute(
        "SELECT DISTINCT posts.* FROM posts JOIN post_blocks ON post_blocks.post_id = posts.id "
        f"WHERE posts.guild_id = ? AND posts.carries_door = 0{marks} ORDER BY posts.id",
        (int(guild.id), *only),
    )
    redrawn = 0
    for row in list(await cur.fetchall()):
        if posts.is_posted(row) and await redraw_post(bot, guild, row):
            redrawn += 1
    return redrawn


async def carries_live(db: Any, post_id: int) -> bool:
    return any(kind in LIVE_KINDS for kind in await kinds_on(db, int(post_id)))


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
    "BLOCK_TOO_BIG",
    "DRAWN_LATER_SAID",
    "DRAWN_NOW_SAID",
    "DRAWN_OFF_SAID",
    "MAX_COMPONENTS",
    "MAX_EMBEDS",
    "MAX_ROWS",
    "ORDERED_NOW_SAID",
    "REDRAWN",
    "blocks_redraw",
    "blocks_turned",
    "drawn_of",
    "footprint_of",
    "keep_drawn",
    "kept_part",
    "needs_redraw",
    "redraw_post",
    "set_drawn",
    "voice_parts",
    "too_big",
    "BLOCK_ADDED_SAID",
    "BLOCK_ALREADY_SAID",
    "BLOCK_HELD_ELSEWHERE",
    "BLOCK_NOT_ON",
    "BLOCK_REMOVED_SAID",
    "FRONTDOOR",
    "TEMPVOICE",
    "KINDS",
    "BIRTHDAY",
    "MARATHONROLE",
    "PINGSFOLLOW",
    "PROPOSEEVENT",
    "birthday_parts",
    "marathon_role_parts",
    "pings_parts",
    "propose_parts",
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
    "LEADERBOARD",
    "LINKS",
    "LIVENOW",
    "leaderboard_load",
    "leaderboard_parts",
    "owner_of",
    "LIVE_KINDS",
    "LOADED",
    "UPCOMING",
    "carries_live",
    "links_parts",
    "live_load",
    "live_parts",
    "load_kinds",
    "loaded",
    "upcoming_load",
    "upcoming_parts",
]
