"""The leaderboard as a post: the block it draws, its redraw, and the one move that pins it."""

from __future__ import annotations

import logging
from typing import Any

from . import block_look as look
from . import points_moves as moves
from . import points_view
from .points_panel import heading_of, lines_of

log = logging.getLogger(__name__)

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
    "SAMPLE_BOARD",
    "block_parts",
    "block_rows",
    "board_look",
    "redraw",
    "sample_rows",
]
