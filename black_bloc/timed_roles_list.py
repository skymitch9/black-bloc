from __future__ import annotations

import re
from typing import Any, NamedTuple

LINES_MAX = 500
MENTION = re.compile(r"^<@!?(\d+)>$")
SNOWFLAKE = re.compile(r"^\d{15,22}$")
AMBIGUOUS = "ambiguous"
UNKNOWN = "unknown"


class Matched(NamedTuple):
    typed: str
    member: Any


class Unmatched(NamedTuple):
    typed: str
    why: str


def lines_of(text: Any) -> list[str]:
    """One name, mention or id per line; blanks dropped, repeats kept once, in the order typed."""
    found: list[str] = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if line and line not in found:
            found.append(line)
    return found


def names_of(member: Any) -> set[str]:
    return {
        str(one).strip().lower()
        for one in (
            getattr(member, "name", None),
            getattr(member, "display_name", None),
            getattr(member, "global_name", None),
            getattr(member, "nick", None),
        )
        if one and str(one).strip()
    }


def index(members: Any) -> tuple[dict[int, Any], dict[str, list[Any]]]:
    by_id: dict[int, Any] = {}
    by_name: dict[str, list[Any]] = {}
    for member in members or ():
        by_id[int(member.id)] = member
        for name in names_of(member):
            by_name.setdefault(name, []).append(member)
    return by_id, by_name


def match(members: Any, typed: Any) -> tuple[list[Matched], list[Unmatched]]:
    """Exact matches only; a name two members share names nobody."""
    by_id, by_name = index(members)
    matched: list[Matched] = []
    unmatched: list[Unmatched] = []
    seen: set[int] = set()
    for line in typed or ():
        mention = MENTION.match(line)
        wanted = mention.group(1) if mention else line if SNOWFLAKE.match(line) else None
        if wanted is not None:
            found = [by_id[int(wanted)]] if int(wanted) in by_id else []
        else:
            found = list(
                {int(one.id): one for one in by_name.get(line.lstrip("@").lower(), [])}.values()
            )
        if len(found) > 1:
            unmatched.append(Unmatched(line, AMBIGUOUS))
        elif not found:
            unmatched.append(Unmatched(line, UNKNOWN))
        elif int(found[0].id) not in seen:
            seen.add(int(found[0].id))
            matched.append(Matched(line, found[0]))
    return matched, unmatched


__all__ = [
    "AMBIGUOUS",
    "LINES_MAX",
    "MENTION",
    "SNOWFLAKE",
    "UNKNOWN",
    "Matched",
    "Unmatched",
    "index",
    "lines_of",
    "match",
    "names_of",
]
