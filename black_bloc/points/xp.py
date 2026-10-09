"""XP from a run's length: the tier whose floor it reaches, kept between the least and the most."""

from __future__ import annotations

from collections.abc import Iterable

from .clock import seconds_of, shown
from .model import PointsError

Tier = tuple[float, int]

DEFAULT_TIERS: tuple[Tier, ...] = ((60.0, 5), (600.0, 25), (900.0, 50), (1800.0, 100))

DEFAULT_LOW = 5

DEFAULT_HIGH = 100

MOST_TIERS = 10

MOST_XP = 100_000

GIVEN_LIMIT = 60


def xp_for(
    seconds: float,
    tiers: Iterable[Tier] = DEFAULT_TIERS,
    low: int = DEFAULT_LOW,
    high: int = DEFAULT_HIGH,
) -> int:
    best = 0
    for floor, xp in sorted(tiers):
        if seconds >= floor:
            best = xp
    return int(min(max(best, low), high))


def parse_tiers(given: object) -> tuple[Tier, ...]:
    """`1:00=5, 10:00=25` — each tier a time it starts at and the XP it gives."""
    text = str(given or "").strip()
    found: dict[float, int] = {}
    for part in (one.strip() for one in text.split(",")):
        floor_text, equals, xp_text = part.partition("=")
        try:
            floor = seconds_of(floor_text)
            xp = int(xp_text.strip())
        except (PointsError, ValueError):
            raise PointsError("bad_tiers", given=text[:GIVEN_LIMIT]) from None
        if not equals or floor in found or not 0 <= xp <= MOST_XP:
            raise PointsError("bad_tiers", given=text[:GIVEN_LIMIT])
        found[floor] = xp
    if not 1 <= len(found) <= MOST_TIERS:
        raise PointsError("bad_tiers", given=text[:GIVEN_LIMIT])
    return tuple(sorted(found.items()))


def tiers_text(tiers: Iterable[Tier]) -> str:
    return ", ".join(f"{shown(floor)}={xp}" for floor, xp in sorted(tiers))


DEFAULT_TIERS_TEXT = tiers_text(DEFAULT_TIERS)
