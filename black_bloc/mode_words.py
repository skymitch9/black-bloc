"""What a stored mode value is called wherever a person reads it."""

from __future__ import annotations

from typing import Any

SHADOW = "shadow"
TEST_WORD = "test"
STAFF_ONLY_WORD = "staff only"
STAFF_ONLY_KEYS: tuple[str, ...] = ("tempvoice_mode",)


def mode_word(key: str, value: Any) -> str:
    said = str(value)
    if said != SHADOW:
        return said
    return STAFF_ONLY_WORD if key in STAFF_ONLY_KEYS else TEST_WORD


def stored_mode(key: str, value: Any, allowed: tuple[str, ...]) -> Any:
    """The word a person typed back to the value it stands for."""
    if SHADOW in allowed and isinstance(value, str) and value == mode_word(key, SHADOW):
        return SHADOW
    return value


def words_for(key: str, allowed: tuple[str, ...]) -> str:
    return ", ".join(mode_word(key, one) for one in allowed)


__all__ = [
    "SHADOW",
    "STAFF_ONLY_KEYS",
    "STAFF_ONLY_WORD",
    "TEST_WORD",
    "mode_word",
    "stored_mode",
    "words_for",
]
