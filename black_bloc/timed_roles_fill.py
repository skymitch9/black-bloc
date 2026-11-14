from __future__ import annotations

from typing import Any, NamedTuple

from . import marathon_people as mp
from .marathon_sources import COMMENTATOR, HOST, RUNNER

PARTS = (RUNNER, COMMENTATOR, HOST)
ROLE_KEYS = {
    RUNNER: "rolemenu_fill_runner_role_id",
    COMMENTATOR: "rolemenu_fill_commentator_role_id",
    HOST: "rolemenu_fill_host_role_id",
}
NAMES_SHOWN = 30


class FillLine(NamedTuple):
    part: str
    role_id: int | None
    timed: bool
    matched: list[int]
    missing: list[int]
    unmatched: list[str]


def entry_name(entry: Any) -> str:
    return str(entry.get("name") or entry.get("login") or entry.get("key") or "?")


def plan_fill(
    entries: Any,
    roles: dict[str, Any],
    timed_ids: Any,
    present: Any,
    assigned: Any,
) -> list[FillLine]:
    """Per part: the matched members still to give the part's role, and the names nobody matched."""
    listed = {int(one) for one in timed_ids or ()}
    here = {int(one) for one in present or ()}
    held = {(int(user), int(role)) for user, role in assigned or ()}
    lines: list[FillLine] = []
    for part in PARTS:
        people = [one for one in entries or () if part in (one.get("parts") or ())]
        matched = sorted(
            {
                int(one["user_id"])
                for one in people
                if one.get("user_id") and int(one["user_id"]) in here
            }
        )
        unmatched = sorted(
            {
                entry_name(one)
                for one in people
                if not one.get("user_id") or int(one["user_id"]) not in here
            },
            key=str.lower,
        )
        role_id = int(roles[part]) if roles.get(part) else None
        usable = role_id is not None and role_id in listed
        missing = [user for user in matched if usable and (user, role_id) not in held]
        lines.append(FillLine(part, role_id, usable, matched, missing, unmatched))
    return lines


def people_of(runs: Any) -> list[dict[str, Any]]:
    return mp.group_people(runs)


def missing_count(lines: Any) -> int:
    return sum(len(line.missing) for line in lines or ())


__all__ = [
    "NAMES_SHOWN",
    "PARTS",
    "ROLE_KEYS",
    "FillLine",
    "entry_name",
    "missing_count",
    "people_of",
    "plan_fill",
]
