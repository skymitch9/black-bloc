"""The leaderboard as both doors read it: rows, runs, bounties and a member's next place."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import points_moves as moves
from . import points_store as store_
from .pb_feed import plain
from .points import clock
from .points.board import CLIMB, FIRST, Place, next_rank
from .points.bounty import live_at
from .points.model import BY_POINTS, BY_XP, MULTIPLIER, ORDERS, PENDING
from .settings_store import (
    DEFAULT_TIMEZONE_KEY,
    POINTS_BOARD_ORDER,
    POINTS_PER_RUN,
    POINTS_WORDS,
)


def order_of(store: Any, guild_id: int, given: Any = None) -> str:
    wanted = str(given or store.get(guild_id, POINTS_BOARD_ORDER) or BY_POINTS)
    return wanted if wanted in ORDERS else BY_POINTS


def member_name(guild: Any, user_id: Any) -> str | None:
    if user_id is None:
        return None
    member = guild.get_member(int(user_id)) if hasattr(guild, "get_member") else None
    found = getattr(member, "display_name", None) or getattr(member, "name", None)
    return str(found) if found else None


def page_words(store: Any, guild_id: int) -> dict[str, str]:
    return {key: str(store.get(guild_id, key) or "") for key in POINTS_WORDS}


def place_row(guild: Any, place: Place) -> dict[str, Any]:
    return {
        "place": place.place,
        "user_id": str(place.user_id),
        "name": member_name(guild, place.user_id),
        "runs": place.runs,
        "xp": place.xp,
        "speedpoints": place.speedpoints,
    }


def run_row(store: Any, guild: Any, row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": str(row["user_id"]),
        "name": member_name(guild, row["user_id"]),
        "game": row["game"],
        "category": row["category"],
        "seconds": row["seconds"],
        "time": clock.shown(row["seconds"]),
        "proof_url": row["proof_url"],
        "note": row["note"],
        "submitted_at": row["submitted_at"],
        "state": row["state"],
        "state_words": moves.said(store, guild.id, f"points_state_{row['state']}"),
        "decided_by": str(row["decided_by"]) if row["decided_by"] is not None else None,
        "decided_by_name": member_name(guild, row["decided_by"]),
        "decided_at": row["decided_at"],
        "reason": row["reason"],
        "xp": row["xp"],
        "speedpoints": row["speedpoints"],
        "bounty_id": row["bounty_id"],
    }


def local(store: Any, guild_id: int, when: datetime) -> str:
    try:
        zone = ZoneInfo(str(store.get(guild_id, DEFAULT_TIMEZONE_KEY) or "UTC"))
    except (ZoneInfoNotFoundError, ValueError):
        zone = ZoneInfo("UTC")
    found = when.astimezone(zone)
    return f"{found:%b} {found.day}, {found:%H:%M}"


def bounty_row(store: Any, guild: Any, row: Any, bounty: Any, event: Any) -> dict[str, Any]:
    amount = f"{float(row['amount']):g}"
    bonus_key = (
        "points_bounty_multiplier_words"
        if row["kind"] == MULTIPLIER
        else "points_bounty_extra_words"
    )
    bonus = moves.said(store, guild.id, bonus_key, amount=amount)
    if row["event_id"] is not None:
        title = plain(event["title"]) if event is not None else f"#{row['event_id']}"
        when = moves.said(store, guild.id, "points_bounty_event_words", event=title)
    else:
        when = moves.said(
            store,
            guild.id,
            "points_bounty_until_words",
            ends=local(store, guild.id, bounty.ends_at) if bounty.ends_at else "",
            starts=local(store, guild.id, bounty.starts_at) if bounty.starts_at else "",
        )
    games = list(bounty.games)
    line = moves.said(
        store,
        guild.id,
        "points_bounty_line",
        name=plain(row["name"]),
        games=", ".join(plain(one) for one in games),
        bonus=bonus,
        when=when,
    )
    return {
        "id": row["id"],
        "name": row["name"],
        "games": games,
        "kind": row["kind"],
        "amount": float(row["amount"]),
        "event_id": row["event_id"],
        "event_title": event["title"] if event is not None else None,
        "starts_at": bounty.starts_at.isoformat() if bounty.starts_at else None,
        "ends_at": bounty.ends_at.isoformat() if bounty.ends_at else None,
        "active": bool(row["active"]),
        "live": live_at(bounty, moves.now()),
        "line": line,
    }


async def bounties(bot: Any, guild: Any, *, current_only: bool = False) -> list[dict[str, Any]]:
    """Every bounty, or only those live or still to come."""
    at = moves.now()
    found = []
    for row, bounty, event in await moves.bounties_of(bot, guild.id):
        upcoming = bounty.active and bounty.ends_at is not None and bounty.ends_at > at
        if current_only and not upcoming:
            continue
        found.append(bounty_row(bot.store, guild, row, bounty, event))
    return found


async def next_rank_of(bot: Any, guild: Any, user_id: int) -> dict[str, Any]:
    board = await moves.board(bot, guild.id, BY_POINTS)
    found = next_rank(
        board, int(user_id), by=BY_POINTS, per_run=int(bot.store.get(guild.id, POINTS_PER_RUN))
    )
    above = found.above
    if found.kind == CLIMB and above is not None:
        line = moves.said(
            bot.store,
            guild.id,
            "points_next_rank_said",
            place=found.place,
            points=found.value,
            gap=found.gap,
            name=moves.name_of(guild, above.user_id),
            above=above.place,
            runs=found.runs if found.runs is not None else "",
        )
    elif found.kind == FIRST:
        line = moves.said(bot.store, guild.id, "points_next_rank_first_said", points=found.value)
    else:
        line = moves.said(bot.store, guild.id, "points_next_rank_unranked_said")
    return {
        "kind": found.kind,
        "place": found.place,
        "speedpoints": found.value,
        "above_user_id": str(above.user_id) if above is not None else None,
        "above_name": member_name(guild, above.user_id) if above is not None else None,
        "above_place": above.place if above is not None else None,
        "gap": found.gap,
        "runs": found.runs,
        "line": line,
    }


async def index(
    bot: Any, guild: Any, viewer: int, *, by: Any = None, verifier: bool, staff: bool
) -> dict[str, Any]:
    order = order_of(bot.store, guild.id, by)
    board = await moves.board(bot, guild.id, order)
    top = moves.top_of(bot.store, guild.id)
    pending = await store_.count(bot.db, guild.id, PENDING) if verifier else None
    return {
        "mode": moves.mode_of(bot.store, guild.id),
        "by": order,
        "orders": [BY_POINTS, BY_XP],
        "top_n": top,
        "may_verify": verifier,
        "staff": staff,
        "words": page_words(bot.store, guild.id),
        "board": [place_row(guild, one) for one in board[:top]],
        "members": len(board),
        "me": await next_rank_of(bot, guild, viewer),
        "bounties": await bounties(bot, guild, current_only=True),
        "pending": pending,
    }


async def full_board(bot: Any, guild: Any, *, by: Any = None) -> dict[str, Any]:
    order = order_of(bot.store, guild.id, by)
    board = await moves.board(bot, guild.id, order)
    return {"by": order, "rows": [place_row(guild, one) for one in board]}
