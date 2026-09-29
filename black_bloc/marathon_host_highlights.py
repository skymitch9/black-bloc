"""A BaF host's public highlight and heads-up: one per run they host, like a runner's."""

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
POSTABLE = (mt.UPCOMING, mt.LIVE, mt.DONE)
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


class Hosted(NamedTuple):
    run: Any
    hosts: list[dict[str, Any]]

    @property
    def run_id(self) -> int:
        return int(mt._cell(self.run, "id"))

    @property
    def user_ids(self) -> list[int]:
        return [int(one["user_id"]) for one in self.hosts]

    @property
    def names(self) -> str:
        return ", ".join(str(one["name"]) for one in self.hosts)

    @property
    def starts(self) -> datetime | None:
        return parse_ts(mt._cell(self.run, "scheduled_at"))


def baf_hosts(row: Any) -> list[dict[str, Any]]:
    found: dict[int, dict[str, Any]] = {}
    for one in mt.people_of(row):
        if one.get("part") != mt.HOST or not one.get("user_id"):
            continue
        user_id = int(one["user_id"])
        found.setdefault(
            user_id,
            {
                "user_id": user_id,
                "name": str(one.get("name") or user_id),
                "login": str(one["login"]) if one.get("login") else None,
                "part": mt.HOST,
            },
        )
    return list(found.values())


def hosted(runs: Any) -> list[Hosted]:
    """Every run on the schedule with a BaF host, in schedule order; dropped runs are off it."""
    rows = sorted(
        (one for one in runs or () if mt._cell(one, "state") != mt.DROPPED), key=mt._when
    )
    return [Hosted(row, found) for row in rows if (found := baf_hosts(row))]


def state_of(item: Hosted) -> str:
    state = mt._cell(item.run, "state")
    if state == mt.LIVE:
        return LIVE
    return DONE if state in (mt.DONE, mt.DROPPED) else UPCOMING


def postable(item: Hosted) -> bool:
    return mt._cell(item.run, "state") in POSTABLE


def left_behind(record: dict[str, Any], runs: Any) -> Hosted | None:
    """A post that is up whose run lost its BaF host (Scan hosts off, the host unlinked, the run
    dropped) still follows its run to the end, naming the hosts it was posted for."""
    row = next((one for one in runs or () if int(mt._cell(one, "id")) == record["run_id"]), None)
    if row is None or not record.get("hosts"):
        return None
    return Hosted(row, [dict(one) for one in record["hosts"]])


def _host(one: Any) -> dict[str, Any]:
    return {
        "user_id": int(one["user_id"]),
        "name": str(one.get("name") or one["user_id"]),
        "login": str(one["login"]) if one.get("login") else None,
        "part": mt.HOST,
    }


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
                    "run_id": int(one["run_id"]),
                    "hosts": [_host(host) for host in one.get("hosts") or ()],
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


def record_for(found: list[dict[str, Any]], item: Hosted) -> dict[str, Any] | None:
    return next((one for one in found if one["run_id"] == item.run_id), None)


def new_record(item: Hosted) -> dict[str, Any]:
    return {
        "run_id": item.run_id,
        "hosts": [dict(one) for one in item.hosts],
        "message_id": None,
        "channel_id": None,
        "removed": False,
        "tried": False,
        "reminded": False,
    }


def is_up(record: Any) -> bool:
    return bool(record and record.get("message_id")) and not record.get("removed")


def auto_wanted(marathon: Any, item: Hosted, record: Any) -> bool:
    """The marathon's Auto-highlight switch, as for a runner: once per run, never again once it
    was tried or staff took it down."""
    return (
        bool(mt._cell(marathon, "public_highlight", 0))
        and mt._cell(item.run, "state") == mt.LIVE
        and not (record and (record.get("tried") or record.get("message_id")))
    )


def heads_up_due(
    item: Hosted, record: Any, now: datetime, *, minutes: int, stale_minutes: int
) -> str | None:
    """SEND, SKIP (the moment passed too long ago) or None: once per run, at a runner reminder's
    moment. A run that moved later is due again, as a runner's reminder is."""
    if item.starts is None or mt._cell(item.run, "state") != mt.UPCOMING:
        return None
    moment = item.starts - timedelta(minutes=int(minutes))
    if now < moment:
        return None
    if record and record.get("reminded"):
        return None
    return SKIP if now - moment > timedelta(minutes=int(stale_minutes)) else SEND


def rearm(record: Any, item: Hosted, now: datetime, *, minutes: int) -> bool:
    """True when a heads-up already sent is due again because its run moved later."""
    if not (record and record.get("reminded")) or item.starts is None:
        return False
    return item.starts - timedelta(minutes=int(minutes)) > now


def clean_move(given: Any) -> str | None:
    word = str(given or "").strip().lower()
    return word if word in (POST, REMOVE) else None


__all__ = [
    "BAD_MOVE",
    "COLUMN",
    "DONE",
    "Hosted",
    "LIVE",
    "POST",
    "REMOVE",
    "SEND",
    "SKIP",
    "UPCOMING",
    "auto_wanted",
    "baf_hosts",
    "clean_move",
    "dump",
    "heads_up_due",
    "hosted",
    "is_up",
    "left_behind",
    "new_record",
    "postable",
    "rearm",
    "record_for",
    "records",
    "state_of",
]
