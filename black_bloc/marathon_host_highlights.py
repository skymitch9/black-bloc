"""A BaF host's public highlight and heads-up: one per contiguous hosted span."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, NamedTuple

from . import marathon as mt
from .golive import parse_ts

COLUMN = "host_highlight_posts"
POST = "post"
REMOVE = "remove"
UPCOMING = "upcoming"
LIVE = "live"
DONE = "done"
STATES = (UPCOMING, LIVE, DONE)
SEND = "send"
SKIP = "skip"
BAD_MOVE = "Say post or remove for a host highlight, so nothing was changed."
BAD_MOVE_CODE = "bad_host_highlight"
NOT_HOSTING = "**{name}** hosts nothing on **{marathon}** that Black Bloc can highlight."
NOT_HOSTING_CODE = "not_hosting"
NOT_SCANNED = (
    "**{marathon}** does not scan its hosts, so there is no BaF host to highlight — turn Scan "
    "hosts on first."
)
NOT_SCANNED_CODE = "hosts_not_scanned"


class Span(NamedTuple):
    user_id: int
    name: str
    login: str | None
    runs: list[Any]
    starts: datetime | None
    ends: datetime | None

    @property
    def run_ids(self) -> list[int]:
        return [int(mt._cell(one, "id")) for one in self.runs]


def hosts_of(row: Any) -> list[dict[str, Any]]:
    return [one for one in mt.people_of(row) if one.get("part") == mt.HOST]


def _span(user_id: int, rows: list[Any]) -> Span:
    mine = [
        one
        for row in rows
        for one in hosts_of(row)
        if one.get("user_id") and int(one["user_id"]) == user_id
    ]
    name = next((str(one.get("name")) for one in mine if one.get("name")), str(user_id))
    login = next((str(one.get("login")) for one in mine if one.get("login")), None)
    starts = [at for at in (parse_ts(mt._cell(one, "scheduled_at")) for one in rows) if at]
    ends = [
        at
        for at in (
            parse_ts(mt._cell(one, "ends_at")) or parse_ts(mt._cell(one, "scheduled_at"))
            for one in rows
        )
        if at
    ]
    return Span(
        user_id,
        name,
        login,
        list(rows),
        min(starts) if starts else None,
        max(ends) if ends else None,
    )


def spans(runs: Any) -> list[Span]:
    """In schedule order: a host's span runs on across runs they host and runs with no host at
    all, and ends at a run someone else hosts. Dropped runs are not on the schedule."""
    rows = sorted(
        (one for one in runs or () if mt._cell(one, "state") != mt.DROPPED), key=mt._when
    )
    open_: dict[int, list[Any]] = {}
    found: list[tuple[int, list[Any]]] = []
    for row in rows:
        hosts = hosts_of(row)
        if not hosts:
            continue
        here = {int(one["user_id"]) for one in hosts if one.get("user_id")}
        for user_id in [one for one in open_ if one not in here]:
            found.append((user_id, open_.pop(user_id)))
        for user_id in here:
            open_.setdefault(user_id, []).append(row)
    found.extend(open_.items())
    made = [_span(user_id, rows) for user_id, rows in found]
    return sorted(made, key=lambda one: (mt._when(one.runs[0]), one.user_id))


def state_of(span: Span) -> str:
    states = [mt._cell(one, "state") for one in span.runs]
    if all(one == mt.DONE for one in states):
        return DONE
    if all(one == mt.UPCOMING for one in states):
        return UPCOMING
    return LIVE


def records(marathon: Any) -> list[dict[str, Any]]:
    raw = mt._cell(marathon, COLUMN)
    try:
        found = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    kept = []
    for one in found if isinstance(found, list) else ():
        if not isinstance(one, dict):
            continue
        try:
            kept.append(
                {
                    "user_id": int(one["user_id"]),
                    "runs": [int(run) for run in one.get("runs") or ()],
                    "message_id": int(one["message_id"]) if one.get("message_id") else None,
                    "channel_id": int(one["channel_id"]) if one.get("channel_id") else None,
                    "removed": bool(one.get("removed")),
                    "tried": bool(one.get("tried")),
                    "reminded": bool(one.get("reminded")),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return kept


def dump(found: list[dict[str, Any]]) -> str:
    return json.dumps(found, sort_keys=True)


def record_for(found: list[dict[str, Any]], span: Span) -> dict[str, Any] | None:
    """The record of a span: the same host, sharing a run — so a slot that moves keeps it."""
    ids = set(span.run_ids)
    return next(
        (one for one in found if one["user_id"] == span.user_id and ids & set(one["runs"])),
        None,
    )


def new_record(span: Span) -> dict[str, Any]:
    return {
        "user_id": span.user_id,
        "runs": span.run_ids,
        "message_id": None,
        "channel_id": None,
        "removed": False,
        "tried": False,
        "reminded": False,
    }


def is_up(record: Any) -> bool:
    return bool(record and record.get("message_id")) and not record.get("removed")


def fields_of(span: Span, marathon: Any, *, url: str) -> dict[str, str]:
    games = list(dict.fromkeys(str(mt._cell(one, "game") or "") for one in span.runs))
    link = mt.TWITCH_URL.format(login=span.login) if span.login else url
    return {
        "name": span.name,
        "mention": f"<@{int(span.user_id)}>",
        "show": str(mt._cell(marathon, "name") or ""),
        "when": _stamp(span.starts, "f"),
        "relative": _stamp(span.starts, "R"),
        "until": _stamp(span.ends, "t"),
        "link": link,
        "url": url,
        "games": ", ".join(one for one in games if one),
        "runs": str(len(span.runs)),
    }


def _stamp(at: datetime | None, style: str) -> str:
    return mt.stamp_of(at.isoformat(), style) if at is not None else "—"


def heads_up_due(
    span: Span, record: Any, now: datetime, *, minutes: int, stale_minutes: int
) -> str | None:
    """SEND, SKIP (the moment passed too long ago) or None; once per span, before its first run
    starts."""
    if record and record.get("reminded"):
        return None
    if span.starts is None or mt._cell(span.runs[0], "state") != mt.UPCOMING:
        return None
    moment = span.starts - timedelta(minutes=int(minutes))
    if now < moment:
        return None
    return SKIP if now - moment > timedelta(minutes=int(stale_minutes)) else SEND


def clean_move(given: Any) -> str | None:
    word = str(given or "").strip().lower()
    return word if word in (POST, REMOVE) else None


__all__ = [
    "BAD_MOVE",
    "COLUMN",
    "DONE",
    "LIVE",
    "POST",
    "REMOVE",
    "SEND",
    "SKIP",
    "Span",
    "UPCOMING",
    "clean_move",
    "dump",
    "fields_of",
    "heads_up_due",
    "hosts_of",
    "is_up",
    "new_record",
    "record_for",
    "records",
    "spans",
    "state_of",
]
