"""The leaderboard as a post: the block it draws, its redraw, and the one move that pins it."""

from __future__ import annotations

import logging
from typing import Any

from . import block_look as look
from . import points_moves as moves
from . import points_view, posts
from . import sticky as sticky_rules
from .logkinds import VIA_DISCORD
from .panels import Outcome, refusal
from .points_panel import heading_of, lines_of
from .settings_store import POINTS_CHANNEL

log = logging.getLogger(__name__)

SLUG = "leaderboard"
NO_CHANNEL = (
    "There is no leaderboard channel to pin it in, so nothing was done. Pick one for "
    "points_channel_id first."
)
CHANNEL_GONE = (
    "Black Bloc cannot find the leaderboard channel (points_channel_id), so nothing was done. "
    "Pick a channel it can see."
)
HAS_ANOTHER = (
    "<#{channel_id}> already keeps another sticky message ({words}), so nothing was done. Press "
    "**Replace it** to keep the leaderboard there instead."
)
ALREADY = "The leaderboard is already the sticky message in <#{channel_id}>."
PINNED_SAID = "The leaderboard is the sticky message in <#{channel_id}> now. {placed}"

SAMPLE_BOARD = (
    ("Moth", 9, 425, 90),
    ("Dax", 7, 300, 70),
    ("Pawpette", 4, 175, 40),
)


def board_look(store: Any, guild_id: int, rows: Any) -> look.Look:
    """The top places, one line each, under the board's heading; the empty line while none."""
    order = points_view.order_of(store, guild_id)
    wanted = list(rows or ())[: moves.top_of(store, guild_id)]
    return look.Look(
        heading_of(store, guild_id, order)[: look.TITLE_MAX],
        look.lines_within(lines_of(store, guild_id, wanted))
        or moves.said(store, guild_id, "points_board_empty"),
    )


def sample_rows() -> list[dict[str, Any]]:
    return [
        {"place": at, "shown": name, "runs": runs, "xp": xp, "speedpoints": points}
        for at, (name, runs, xp, points) in enumerate(SAMPLE_BOARD, start=1)
    ]


def is_off(store: Any, guild_id: int) -> bool:
    return moves.mode_of(store, guild_id) == moves.OFF


async def block_rows(bot: Any, guild: Any) -> list[dict[str, Any]]:
    """The top places in the board's own order, read once per draw."""
    if is_off(bot.store, guild.id):
        return []
    order = points_view.order_of(bot.store, guild.id)
    board = await moves.board(bot, guild.id, order)
    return [
        points_view.place_row(guild, one) | {"shown": moves.name_of(guild, one.user_id)}
        for one in board[: moves.top_of(bot.store, guild.id)]
    ]


def block_parts(bot: Any, guild: Any, rows: Any) -> Any:
    if is_off(bot.store, guild.id):
        return None
    return look.parts_of(board_look(bot.store, guild.id, rows))


def channel_label(guild: Any, channel_id: Any) -> str:
    """#name · Category, as every channel picker on the site reads."""
    channel = guild.get_channel(int(channel_id)) if channel_id else None
    if channel is None:
        return ""
    category = getattr(getattr(channel, "category", None), "name", None)
    name = f"#{getattr(channel, 'name', channel_id)}"
    return f"{name} · {category}" if category else name


def aimed(bot: Any, guild: Any) -> int | None:
    found = bot.store.get(guild.id, POINTS_CHANNEL)
    try:
        return int(found) if found else None
    except (TypeError, ValueError):
        return None


async def board_state(bot: Any, guild: Any) -> dict[str, Any]:
    """Where the leaderboard is pinned, and what sits in the channel it is aimed at."""
    channel_id = aimed(bot, guild)
    post = await posts.get_post(bot.db, guild.id, SLUG)
    mine = await sticky_rules.row_of_post(bot.db, int(post["id"])) if post is not None else None
    there = (
        await sticky_rules.get_row(bot.db, guild.id, channel_id) if channel_id else None
    )
    ours = mine is not None and there is not None and there["channel_id"] == mine["channel_id"]
    other = None if there is None or ours else there
    return {
        "channel_id": channel_id,
        "channel": channel_label(guild, channel_id),
        "post": post,
        "sticky": mine,
        "other": other,
    }


async def ensure_post(bot: Any, guild: Any, actor: Any, *, via: str) -> Outcome:
    """The leaderboard post: made once with its block and the embed style, then reused."""
    from .post_blocks import LEADERBOARD, attach, kinds_on

    post = await posts.get_post(bot.db, guild.id, SLUG)
    if post is None:
        made = await posts.make_post(
            bot,
            guild,
            actor,
            title=moves.said(bot.store, guild.id, "points_board_post_title"),
            slug=SLUG,
            style=posts.EMBED,
            via=via,
        )
        if not made.ok:
            return made
        post = made.value
        await posts.set_post_fields(bot.db, int(post["id"]), by=posts.actor_id(actor), pin=0)
    if LEADERBOARD not in await kinds_on(bot.db, int(post["id"])):
        await attach(bot.db, post, LEADERBOARD, by=posts.actor_id(actor))
    return Outcome(True, "", value=await posts.get_post_by_id(bot.db, int(post["id"])))


async def pin_board(
    bot: Any, guild: Any, actor: Any, *, replace: bool = False, via: str = VIA_DISCORD
) -> Outcome:
    """The leaderboard post kept at the bottom of points_channel_id; pressing it again is safe."""
    from .sticky_posts import desk_of

    channel_id = aimed(bot, guild)
    if channel_id is None:
        return refusal(NO_CHANNEL, "no_channel", 409)
    if guild.get_channel(channel_id) is None:
        return refusal(CHANNEL_GONE, "channel_gone", 409)
    state = await board_state(bot, guild)
    mine = state["sticky"]
    if mine is not None and int(mine["channel_id"]) == channel_id:
        return Outcome(True, ALREADY.format(channel_id=channel_id), "already", 200, mine)
    other = state["other"]
    if other is not None and not replace:
        return refusal(
            HAS_ANOTHER.format(
                channel_id=channel_id, words=sticky_rules.preview(sticky_rules.words_of(other))
            ),
            "channel_has_sticky",
            409,
        )
    made = await ensure_post(bot, guild, actor, via=via)
    if not made.ok:
        return made
    desk = desk_of(bot)
    if mine is not None:
        moved = await desk.remove(guild, int(mine["channel_id"]), actor, via=via)
        if not moved.ok:
            return moved
    saved = await desk.save(guild, channel_id, None, actor, via=via, post=int(made.value["id"]))
    if not saved.ok:
        return saved
    said = PINNED_SAID.format(channel_id=channel_id, placed=saved.message)
    return Outcome(True, said, "pinned", 200, saved.value)


async def redraw(bot: Any, guild: Any) -> bool:
    """A points move changed the board: every message carrying it is redrawn now."""
    from .cogs.community.live_blocks import keeper_of

    keep = keeper_of(bot)
    if keep is None:
        return False
    try:
        return bool(await keep(guild))
    except Exception as exc:
        log.warning(
            "points: the leaderboard post was not redrawn — %s: %s", type(exc).__name__, exc
        )
        return False


__all__ = [
    "SLUG",
    "board_state",
    "channel_label",
    "ensure_post",
    "pin_board",
    "SAMPLE_BOARD",
    "block_parts",
    "block_rows",
    "board_look",
    "redraw",
    "sample_rows",
]
