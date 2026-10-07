"""Best-of: which length a set plays, and whether a score fits it."""

from __future__ import annotations

from typing import Any

from .model import BracketError, Options

LONGEST = 15


def wins_needed(best_of: int) -> int:
    return best_of // 2 + 1


def valid_length(best_of: Any) -> bool:
    return (
        isinstance(best_of, int)
        and not isinstance(best_of, bool)
        and 1 <= best_of <= LONGEST
        and best_of % 2 == 1
    )


def fits(best_of: int, score_a: Any, score_b: Any) -> bool:
    """A finished set: one side reached the wins needed, the other did not."""
    scores = (score_a, score_b)
    if any(not isinstance(one, int) or isinstance(one, bool) or one < 0 for one in scores):
        return False
    need = wins_needed(best_of)
    return max(scores) == need and min(scores) < need


def checked(best_of: int, score_a: Any, score_b: Any) -> tuple[int, int]:
    if not fits(best_of, score_a, score_b):
        raise BracketError("bad_score", best_of=best_of, wins=wins_needed(best_of))
    return int(score_a), int(score_b)


def length_for(options: Options, alive: int, *, final: bool) -> int:
    """The finals length for the last set, the late length from top N on, else the default."""
    if final:
        return options.best_of_finals
    late = options.best_of_from_round
    if late and alive and alive <= late:
        return options.best_of_late
    return options.best_of
