"""The leaderboard: places from totals, the gap to the place above, what moved in the top N."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from .model import BY_POINTS, BY_XP, DOWN, ENTERED, LEFT, UP

FIRST = "first"
CLIMB = "climb"
UNRANKED = "unranked"


@dataclass(frozen=True)
class Row:
    user_id: int
    runs: int
    xp: int
    speedpoints: int
    last_at: str


@dataclass(frozen=True)
class Place:
    place: int
    user_id: int
    runs: int
    xp: int
    speedpoints: int
    last_at: str

    def value(self, by: str = BY_POINTS) -> int:
        return self.xp if by == BY_XP else self.speedpoints


@dataclass(frozen=True)
class NextRank:
    kind: str
    place: int | None
    value: int
    above: Place | None
    gap: int
    runs: int | None


@dataclass(frozen=True)
class Change:
    kind: str
    user_id: int
    was: int | None
    now: int | None


def order_key(row: Row, by: str) -> tuple:
    if by == BY_XP:
        return (-row.xp, -row.speedpoints, row.last_at, row.user_id)
    return (-row.speedpoints, -row.xp, row.last_at, row.user_id)


def standings(rows: Iterable[Row], by: str = BY_POINTS) -> list[Place]:
    """Most speedpoints (or XP) first; a tie goes to more of the other, then the earlier."""
    ranked = sorted((row for row in rows if row.runs > 0), key=lambda row: order_key(row, by))
    return [
        Place(at, row.user_id, row.runs, row.xp, row.speedpoints, row.last_at)
        for at, row in enumerate(ranked, start=1)
    ]


def place_of(board: Sequence[Place], user_id: int) -> Place | None:
    return next((one for one in board if one.user_id == int(user_id)), None)


def next_rank(
    board: Sequence[Place], user_id: int, *, by: str = BY_POINTS, per_run: int = 0
) -> NextRank:
    """The place above and what passing it takes: one more than the gap, so no tie-break decides."""
    mine = place_of(board, user_id)
    if mine is None:
        return NextRank(UNRANKED, None, 0, None, 0, None)
    if mine.place == 1:
        return NextRank(FIRST, 1, mine.value(by), None, 0, None)
    above = board[mine.place - 2]
    gap = above.value(by) - mine.value(by) + 1
    runs = math.ceil(gap / per_run) if by == BY_POINTS and per_run > 0 else None
    return NextRank(CLIMB, mine.place, mine.value(by), above, gap, runs)


def diff(before: Sequence[Place], after: Sequence[Place], top: int) -> list[Change]:
    """Who entered, left, moved up or moved down inside the top `top` places."""
    was = {one.user_id: one.place for one in before}
    now = {one.user_id: one.place for one in after}
    inside = {uid for uid, at in was.items() if at <= top} | {
        uid for uid, at in now.items() if at <= top
    }
    found: list[Change] = []
    for uid in inside:
        old, new = was.get(uid), now.get(uid)
        old_in = old is not None and old <= top
        new_in = new is not None and new <= top
        if new_in and not old_in:
            found.append(Change(ENTERED, uid, old, new))
        elif old_in and not new_in:
            found.append(Change(LEFT, uid, old, new))
        elif new is not None and old is not None and new != old:
            found.append(Change(UP if new < old else DOWN, uid, old, new))
    return sorted(
        found,
        key=lambda one: (one.kind == LEFT, one.now if one.kind != LEFT else one.was, one.user_id),
    )
