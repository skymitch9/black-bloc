"""The point system's states, kinds and its one refusal type."""

from __future__ import annotations

from typing import Any

PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
REMOVED = "removed"
STATES = (PENDING, APPROVED, REJECTED, REMOVED)

MULTIPLIER = "multiplier"
EXTRA = "extra"
BONUS_KINDS = (MULTIPLIER, EXTRA)

BY_POINTS = "points"
BY_XP = "xp"
ORDERS = (BY_POINTS, BY_XP)

ENTERED = "entered"
LEFT = "left"
UP = "up"
DOWN = "down"
CHANGE_KINDS = (ENTERED, LEFT, UP, DOWN)


class PointsError(Exception):
    """A refusal with a code the caller turns into words, and the fields those words take."""

    def __init__(self, code: str, **fields: Any) -> None:
        super().__init__(code)
        self.code = code
        self.fields = fields
