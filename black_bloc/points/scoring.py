"""One approved run's XP and speedpoints, as the settings and the live bounties make them."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from .bounty import Bounty, points_for
from .xp import DEFAULT_HIGH, DEFAULT_LOW, DEFAULT_TIERS, Tier, xp_for

DEFAULT_PER_RUN = 10


@dataclass(frozen=True)
class Rules:
    tiers: tuple[Tier, ...] = DEFAULT_TIERS
    low: int = DEFAULT_LOW
    high: int = DEFAULT_HIGH
    per_run: int = DEFAULT_PER_RUN


@dataclass(frozen=True)
class Score:
    xp: int
    speedpoints: int
    bounty_id: int | None


def score(
    seconds: float, game: object, at: datetime, rules: Rules, bounties: Iterable[Bounty] = ()
) -> Score:
    points, bounty_id = points_for(rules.per_run, game, at, bounties)
    return Score(xp_for(seconds, rules.tiers, rules.low, rules.high), points, bounty_id)
