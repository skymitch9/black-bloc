"""Runner/Host announcements: the marathon's switch and each person's opt-out."""

from __future__ import annotations

import json
from typing import Any

from . import marathon as mt
from . import marathon_hosts as mh

SWITCH = mh.ANNOUNCE
OPTED = "announce_opt_out"
OPT_OUT = "optout"
OPT_IN = "optin"
OUT_WORDS = (OPT_OUT, "out", "remove", "off")
IN_WORDS = (OPT_IN, "in", "post", "on")
BAD_OPT = "Say out or in for a person's announcements, so nothing was changed."
BAD_OPT_CODE = "bad_opt"
NOT_BAF = "Nobody from BaF with that id is on **{marathon}**, so nothing was changed."
NOT_BAF_CODE = "not_baf"


def announces(marathon: Any, default: Any) -> bool:
    return mh.switch_on(marathon, SWITCH, default)


def opted_out(marathon: Any) -> set[int]:
    raw = mt._cell(marathon, OPTED)
    try:
        found = json.loads(raw or "[]") if not isinstance(raw, list) else raw
    except (TypeError, ValueError):
        return set()
    kept: set[int] = set()
    for one in found if isinstance(found, list) else ():
        try:
            kept.add(int(one))
        except (TypeError, ValueError):
            continue
    return kept


def dump(ids: Any) -> str:
    return json.dumps(sorted({int(one) for one in ids}))


def toggled(opted: set[int], user_ids: Any, out: bool) -> set[int]:
    wanted = {int(one) for one in user_ids}
    return (opted | wanted) if out else (opted - wanted)


def kept(people: Any, opted: set[int]) -> list[dict[str, Any]]:
    return [dict(one) for one in people or () if int(one["user_id"]) not in opted]


def run_people(row: Any, opted: set[int]) -> list[dict[str, Any]]:
    """The BaF people a runner's public post names: everyone of ours not opted out."""
    return kept(mt.ours(mt.people_of(row)), opted)


def all_out(user_ids: Any, opted: set[int]) -> bool:
    ids = [int(one) for one in user_ids]
    return bool(ids) and all(one in opted for one in ids)


def clean_opt(given: Any) -> bool | None:
    """True to opt out, False to opt back in, None when the word is not understood."""
    if isinstance(given, bool):
        return given
    word = str(given if given is not None else "").strip().lower()
    if word in OUT_WORDS:
        return True
    if word in IN_WORDS:
        return False
    return None


__all__ = [
    "BAD_OPT",
    "NOT_BAF",
    "OPTED",
    "OPT_IN",
    "OPT_OUT",
    "SWITCH",
    "all_out",
    "announces",
    "clean_opt",
    "dump",
    "kept",
    "opted_out",
    "run_people",
    "toggled",
]
