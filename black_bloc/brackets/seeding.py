"""Seeding: the standard 1-v-N order, byes to the top seeds, randomise and reorder."""

from __future__ import annotations

import random
from typing import Any

from .model import BracketError


def bracket_size(count: int) -> int:
    size = 2
    while size < count:
        size *= 2
    return size


def standard_order(size: int) -> list[int]:
    """Seed numbers in bracket position order, so position pairs are 1vN, then the halves split."""
    order = [1]
    while len(order) < size:
        total = len(order) * 2
        order = [seed for kept in order for seed in (kept, total + 1 - kept)]
    return order


def first_round(entrants: list[int]) -> list[tuple[int | None, int | None]]:
    """Round-one pairs by seed; a seed past the field is a bye, so byes fall to the top seeds."""
    size = bracket_size(len(entrants))
    seeded = [
        entrants[seed - 1] if seed <= len(entrants) else None for seed in standard_order(size)
    ]
    return [(seeded[at], seeded[at + 1]) for at in range(0, size, 2)]


def randomised(entrants: list[int], rng: Any = None) -> list[int]:
    found = list(entrants)
    (rng or random.SystemRandom()).shuffle(found)
    return found


def reordered(entrants: list[int], wanted: list[int]) -> list[int]:
    """The TO's order: exactly the same entrants, each once."""
    if sorted(wanted) != sorted(entrants) or len(set(wanted)) != len(wanted):
        raise BracketError("bad_order")
    return list(wanted)
