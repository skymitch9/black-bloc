from __future__ import annotations

import json
from typing import Any, NamedTuple

from . import marathon as mt
from . import spotlight as spot
from .golive import parse_ts

FOLLOW = "follow"
SCAN = "scan_hosts"
EVENTS = "host_events"
YES = ("on", "true", "yes", "1")
NO = ("off", "false", "no", "0")
FOLLOWS = ("", "follow", "default", "setting", "null", "none")
BAD_SWITCH = "Say on, off or follow for **{what}**, so nothing was changed."
BAD_SWITCH_CODE = "bad_switch"
WHAT = {SCAN: "Scan hosts", EVENTS: "BaF host events"}
BAD_TWITCH = (
    "**{given}** is not a Twitch channel name (letters, digits and _, up to 25, or the "
    "channel's twitch.tv link), so nothing was changed."
)
BAD_TWITCH_CODE = "bad_twitch"
LOGIN_SET = "**{runner}** is **twitch.tv/{login}** everywhere Black Bloc uses their channel now."
LOGIN_CLEARED = "**{runner}** is back to the schedule's Twitch channel."
LOGIN_SAME = "**{runner}** already has that Twitch channel, so nothing was changed."
KEEP = object()


class HostSpan(NamedTuple):
    user_id: int
    name: str
    runs: list[Any]
    starts: Any
    ends: Any


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


def scans_hosts(marathon: Any, default: Any) -> bool:
    return switch_on(marathon, SCAN, default)


def makes_host_events(marathon: Any, default: Any) -> bool:
    return switch_on(marathon, EVENTS, default)


def clean_login(given: Any) -> tuple[bool, str | None]:
    """`(understood, login)`: a blank clears the fix."""
    text = str(given or "").strip()
    if not text:
        return (True, None)
    login = spot.clean_login(text)
    return (login is not None, login)


def event_ids(marathon: Any) -> dict[int, int]:
    raw = mt._cell(marathon, "host_event_ids")
    try:
        found = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}
    if not isinstance(found, dict):
        return {}
    kept: dict[int, int] = {}
    for key, value in found.items():
        try:
            kept[int(key)] = int(value)
        except (TypeError, ValueError):
            continue
    return kept


def dump_ids(ids: dict[int, int]) -> str:
    return json.dumps({str(key): int(value) for key, value in sorted(ids.items())})


def is_runner_run(row: Any) -> bool:
    """A run of ours for anyone but a host: the one kind that gets a run event on its own."""
    return any(one.get("user_id") and one.get("part") != mt.HOST for one in mt.people_of(row))


def hosted(runs: Any) -> list[HostSpan]:
    """Each BaF host once, with the runs they host (dropped runs left out) and their span."""
    found: dict[int, list[Any]] = {}
    names: dict[int, str] = {}
    for row in sorted(
        (one for one in runs or () if mt._cell(one, "state") != mt.DROPPED), key=mt._when
    ):
        for person in mt.people_of(row):
            if person.get("part") != mt.HOST or not person.get("user_id"):
                continue
            user_id = int(person["user_id"])
            if row not in found.setdefault(user_id, []):
                found[user_id].append(row)
            names.setdefault(user_id, str(person.get("name") or user_id))
    spans = []
    for user_id, rows in found.items():
        starts = [at for at in (parse_ts(mt._cell(one, "scheduled_at")) for one in rows) if at]
        ends = [
            at
            for at in (
                parse_ts(mt._cell(one, "ends_at")) or parse_ts(mt._cell(one, "scheduled_at"))
                for one in rows
            )
            if at
        ]
        spans.append(
            HostSpan(
                user_id,
                names[user_id],
                rows,
                min(starts) if starts else None,
                max(ends) if ends else None,
            )
        )
    return spans


def event_fields(span: HostSpan, marathon: Any, name: str | None = None) -> dict[str, str]:
    games = list(dict.fromkeys(str(mt._cell(one, "game") or "") for one in span.runs))
    return {
        "member": name or span.name,
        "marathon": str(mt._cell(marathon, "name") or ""),
        "games": ", ".join(one for one in games if one),
        "runs": str(len(span.runs)),
    }


def host_only(parts: Any) -> bool:
    kinds = set(parts or ())
    return mt.HOST in kinds and mt.RUNNER not in kinds


__all__ = [
    "BAD_SWITCH",
    "BAD_TWITCH",
    "EVENTS",
    "FOLLOW",
    "HostSpan",
    "SCAN",
    "clean_login",
    "clean_switch",
    "dump_ids",
    "event_fields",
    "event_ids",
    "host_only",
    "hosted",
    "is_runner_run",
    "makes_host_events",
    "scans_hosts",
    "stored",
]
