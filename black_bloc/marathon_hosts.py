from __future__ import annotations

import json
from typing import Any

from . import marathon as mt
from . import marathon_host_highlights as mhh
from . import spotlight as spot
from .golive import parse_ts

FOLLOW = "follow"
ANNOUNCE = "announcements"
HOST_ANNOUNCE = "host_announcements"
OVERLAY = "overlay"
YES = ("on", "true", "yes", "1")
NO = ("off", "false", "no", "0")
FOLLOWS = ("", "follow", "default", "setting", "null", "none")
BAD_SWITCH = "Say on, off or follow for **{what}**, so nothing was changed."
BAD_SWITCH_CODE = "bad_switch"
WHAT = {
    ANNOUNCE: "BaF announcements",
    HOST_ANNOUNCE: "Host announcements",
    OVERLAY: "Event schedule",
}
SCAN_GONE = (
    "The Scan hosts switch is gone — hosts are always found now, like runners, so nothing was "
    "changed."
)
HOST_EVENTS_GONE = (
    "The BaF host events switch is gone — events now follow the one **BaF run/host events** "
    "switch, so nothing was changed."
)
RETIRED = ("scan_hosts", "host_events")
BAD_TWITCH = (
    "**{given}** is not a Twitch channel name (letters, digits and _, up to 25, or the "
    "channel's twitch.tv link), so nothing was changed."
)
BAD_TWITCH_CODE = "bad_twitch"
LOGIN_SET = "**{runner}** is **twitch.tv/{login}** everywhere Black Bloc uses their channel now."
LOGIN_CLEARED = "**{runner}** is back to the schedule's Twitch channel."
LOGIN_SAME = "**{runner}** already has that Twitch channel, so nothing was changed."
KEEP = object()


def clean_switch(given: Any) -> tuple[bool, bool | None]:
    """`(understood, value)`: True / False, or None to follow the setting."""
    if given is None or isinstance(given, bool):
        return (True, given)
    if isinstance(given, int):
        return (given in (0, 1), bool(given) if given in (0, 1) else None)
    word = str(given).strip().lower()
    if word in YES:
        return (True, True)
    if word in NO:
        return (True, False)
    if word in FOLLOWS:
        return (True, None)
    return (False, None)


def stored(marathon: Any, column: str) -> bool | None:
    value = mt._cell(marathon, column)
    return None if value is None else bool(value)


def switch_on(marathon: Any, column: str, default: Any) -> bool:
    own = stored(marathon, column)
    return bool(default) if own is None else own


def clean_login(given: Any) -> tuple[bool, str | None]:
    """`(understood, login)`: a blank clears the fix."""
    text = str(given or "").strip()
    if not text:
        return (True, None)
    login = spot.clean_login(text)
    return (login is not None, login)


def _ints(values: Any) -> list[int]:
    kept = []
    for one in values or ():
        try:
            kept.append(int(one))
        except (TypeError, ValueError):
            continue
    return kept


def event_records(marathon: Any) -> list[dict[str, Any]]:
    """One record per host BLOCK event; the v190 per-host `{user_id: event_id}` shape reads as
    records with no runs, claimed by that host's first block."""
    raw = mt._cell(marathon, "host_event_ids")
    try:
        found = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    if isinstance(found, dict):
        found = [{"event_id": value, "hosts": [key], "runs": []} for key, value in found.items()]
    if not isinstance(found, list):
        return []
    kept = []
    for one in found:
        if not isinstance(one, dict):
            continue
        try:
            event_id = int(one.get("event_id"))
        except (TypeError, ValueError):
            continue
        runs = _ints(one.get("runs"))
        kept.append(
            {
                "event_id": event_id,
                "start_run_id": runs[0] if runs else None,
                "runs": runs,
                "hosts": _ints(one.get("hosts")),
            }
        )
    return kept


def dump_records(found: list[dict[str, Any]]) -> str:
    return json.dumps(
        [
            {
                "event_id": int(one["event_id"]),
                "runs": list(one["runs"]),
                "hosts": list(one["hosts"]),
            }
            for one in found
        ]
    )


def claim(found: list[dict[str, Any]], block: mhh.Block, used: set[int]) -> dict[str, Any] | None:
    """The block's record: one that starts where it starts, else one sharing a host and a run,
    else a per-host record from before blocks that names one of its hosts."""
    free = [one for one in found if id(one) not in used]
    hosts = set(block.user_ids)
    runs = set(block.run_ids)
    for test in (
        lambda one: one["start_run_id"] == block.start_run_id,
        lambda one: hosts & set(one["hosts"]) and runs & set(one["runs"]),
        lambda one: not one["runs"] and hosts & set(one["hosts"]),
    ):
        hit = next((one for one in free if test(one)), None)
        if hit is not None:
            used.add(id(hit))
            return hit
    return None


def fit(record: dict[str, Any], block: mhh.Block) -> None:
    record["runs"] = block.run_ids
    record["start_run_id"] = block.start_run_id
    record["hosts"] = block.user_ids


def span_of(block: mhh.Block) -> tuple[Any, Any]:
    starts = [at for at in (parse_ts(mt._cell(one, "scheduled_at")) for one in block.runs) if at]
    ends = [
        at
        for at in (
            parse_ts(mt._cell(one, "ends_at")) or parse_ts(mt._cell(one, "scheduled_at"))
            for one in block.runs
        )
        if at
    ]
    return (min(starts) if starts else None, max(ends) if ends else None)


def is_runner_run(row: Any) -> bool:
    """A run of ours for anyone but a host: the one kind that gets a run event on its own."""
    return any(one.get("user_id") and one.get("part") != mt.HOST for one in mt.people_of(row))


def event_fields(block: mhh.Block, marathon: Any, name: str | None = None) -> dict[str, str]:
    games = list(dict.fromkeys(str(mt._cell(one, "game") or "") for one in block.runs))
    return {
        "member": name or block.names,
        "marathon": str(mt._cell(marathon, "name") or ""),
        "games": ", ".join(one for one in games if one),
        "runs": str(len(block.runs)),
    }


def host_only(parts: Any) -> bool:
    kinds = set(parts or ())
    return mt.HOST in kinds and mt.RUNNER not in kinds


def part_tag(parts: Any, words: dict[str, str]) -> str:
    """The small tag beside a BaF person's name: their parts in the part keys' words."""
    return " + ".join(words.get(mt.PART_KEYS.get(one, ""), str(one)) for one in parts or ())


__all__ = [
    "ANNOUNCE",
    "BAD_SWITCH",
    "BAD_TWITCH",
    "FOLLOW",
    "HOST_ANNOUNCE",
    "HOST_EVENTS_GONE",
    "OVERLAY",
    "RETIRED",
    "SCAN_GONE",
    "claim",
    "clean_login",
    "clean_switch",
    "dump_records",
    "event_fields",
    "event_records",
    "fit",
    "host_only",
    "is_runner_run",
    "part_tag",
    "span_of",
    "stored",
]
