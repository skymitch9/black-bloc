"""Who a member is on speedrun.com: an exact Twitch login or an exact name, never a guess."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .speedrun import Runner

FOUND = "found"
NOBODY = "nobody"
AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class Answer:
    outcome: str
    runner: Runner | None = None
    candidates: int = 0


def folded(value: Any) -> str:
    return str(value or "").strip().casefold()


def one_of(found: list[Runner]) -> Answer:
    distinct = {runner.id: runner for runner in found}
    if len(distinct) == 1:
        return Answer(FOUND, next(iter(distinct.values())), 1)
    return Answer(AMBIGUOUS if distinct else NOBODY, None, len(distinct))


def exact(login: Any, runners: Any) -> Answer:
    """The one runner whose own profile names this Twitch login; two or none is no match."""
    wanted = folded(login)
    if not wanted:
        return Answer(NOBODY)
    return one_of([one for one in runners or () if folded(one.twitch_login) == wanted])


def named(name: Any, runners: Any) -> Answer:
    """The one runner whose speedrun.com name is exactly this, case aside."""
    wanted = folded(name)
    if not wanted:
        return Answer(NOBODY)
    return one_of([one for one in runners or () if folded(one.name) == wanted])


async def by_twitch(client: Any, login: Any) -> Answer:
    return exact(login, await client.users_by_twitch(str(login)))


async def by_name(client: Any, name: Any) -> Answer:
    return named(name, await client.users_by_name(str(name)))


__all__ = ["AMBIGUOUS", "FOUND", "NOBODY", "Answer", "by_name", "by_twitch", "exact", "named"]
