"""Bounties: bonus speedpoints for a game while a window is open, the single best one applied."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from .model import EXTRA, MULTIPLIER


@dataclass(frozen=True)
class Bounty:
    id: int
    name: str
    games: tuple[str, ...]
    kind: str
    amount: float
    starts_at: datetime | None
    ends_at: datetime | None
    active: bool = True


def game_key(game: object) -> str:
    return " ".join(str(game or "").casefold().split())


def live_at(bounty: Bounty, at: datetime) -> bool:
    if not bounty.active or bounty.starts_at is None or bounty.ends_at is None:
        return False
    return bounty.starts_at <= at < bounty.ends_at


def matches(bounty: Bounty, game: object) -> bool:
    wanted = game_key(game)
    return any(game_key(one) == wanted for one in bounty.games)


def with_bonus(base: int, bounty: Bounty) -> int:
    if bounty.kind == MULTIPLIER:
        return math.floor(base * float(bounty.amount) + 0.5)
    if bounty.kind == EXTRA:
        return base + math.floor(float(bounty.amount) + 0.5)
    return base


def points_for(
    base: int, game: object, at: datetime, bounties: Iterable[Bounty]
) -> tuple[int, int | None]:
    """The run's speedpoints and the bounty that gave them; the best wins, the oldest on a tie."""
    best, chosen = base, None
    for bounty in sorted(bounties, key=lambda one: one.id):
        if not live_at(bounty, at) or not matches(bounty, game):
            continue
        value = with_bonus(base, bounty)
        if value > best:
            best, chosen = value, bounty.id
    return best, chosen
