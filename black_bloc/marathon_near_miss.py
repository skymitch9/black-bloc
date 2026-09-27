"""A stranger on a tracked marathon's schedule whose name IS a member's Discord username."""

from __future__ import annotations

import json
from typing import Any, NamedTuple

from . import marathon as mt
from . import marathon_people as mp

HERE = "here"
EVERYWHERE = "everywhere"
NOT_THEM = "not"
ACTIONS = (HERE, EVERYWHERE, NOT_THEM)
TEMPLATE = r"marathon:nearmiss:(?P<marathon_id>[0-9]+):(?P<action>here|everywhere|not)"
CUSTOM_ID = "marathon:nearmiss:{marathon_id}:{action}"
LABEL_LIMIT = 80

POSTED = "marathon.near_miss_posted"
WOULD_POST = "marathon.would_post_near_miss"
RESOLVED = "marathon.near_miss_resolved"
FAILED = "marathon.near_miss_failed"
POSTED_KINDS = (POSTED, WOULD_POST)
SEEN_KINDS = (POSTED, WOULD_POST, RESOLVED)


class Seen(NamedTuple):
    posted: set[tuple[str, int]]
    resolved: set[str]


def custom_id(marathon_id: Any, action: str) -> str:
    return CUSTOM_ID.format(marathon_id=int(marathon_id), action=action)


def label(text: Any) -> str:
    return str(text or "").strip()[:LABEL_LIMIT] or "…"


def counts(entry: dict[str, Any], *, match_hosts: bool) -> bool:
    return match_hosts or mt.RUNNER in (entry.get("parts") or ())


def exact_match(
    entry: dict[str, Any], usernames: dict[str, int], *, match_hosts: bool = True
) -> tuple[str, int] | None:
    """Only the near miss whose username equals the Twitch login or the schedule name outright."""
    if entry.get("user_id") or not counts(entry, match_hosts=match_hosts):
        return None
    wanted = {str(entry.get(one) or "").strip().lower() for one in ("login", "name")} - {""}
    for username in sorted(usernames or {}):
        if username.lower() not in wanted:
            continue
        found = (username, int(usernames[username]))
        if mp.looks_like(entry, {username: found[1]}) == found:
            return found
    return None


def details_of(row: Any) -> dict[str, Any]:
    raw = mt._cell(row, "details")
    try:
        found = json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        return {}
    return found if isinstance(found, dict) else {}


def seen_of(rows: Any) -> Seen:
    posted: set[tuple[str, int]] = set()
    resolved: set[str] = set()
    for row in rows or ():
        details = details_of(row)
        key = str(details.get("runner_key") or "")
        if not key:
            continue
        if mt._cell(row, "kind") == RESOLVED:
            resolved.add(key)
        elif details.get("channel_id"):
            posted.add((key, int(details["channel_id"])))
    return Seen(posted, resolved)


def post_for(rows: Any, message_id: Any) -> tuple[Any, dict[str, Any]] | None:
    for row in rows or ():
        details = details_of(row)
        if mt._cell(row, "kind") in POSTED_KINDS and str(details.get("message_id")) == str(
            message_id
        ):
            return (row, details)
    return None


def answered(rows: Any, runner_key: str) -> dict[str, Any] | None:
    for row in rows or ():
        details = details_of(row)
        if mt._cell(row, "kind") == RESOLVED and details.get("runner_key") == runner_key:
            return details
    return None
