"""A BaF host's public posts, one set per host BLOCK: a runner's reminders at every mark and a
runner's highlight, measured from the block's first run."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, NamedTuple

from . import marathon as mt
from . import marathon_reminder_posts as mrem
from .golive import parse_ts

COLUMN = "host_highlight_posts"
UPCOMING = "upcoming"
LIVE = "live"
DONE = "done"
STATES = (UPCOMING, LIVE, DONE)
AS_RUN_STATE = {UPCOMING: mt.UPCOMING, LIVE: mt.LIVE, DONE: mt.DONE}


class Block(NamedTuple):
    runs: list[Any]
    hosts: list[dict[str, Any]]

    @property
    def first(self) -> Any:
        return self.runs[0]

    @property
    def run_ids(self) -> list[int]:
        return [int(mt._cell(one, "id")) for one in self.runs]

    @property
    def start_run_id(self) -> int:
        return self.run_ids[0]

    @property
    def user_ids(self) -> list[int]:
        return [int(one["user_id"]) for one in self.hosts]

    @property
    def names(self) -> str:
        return ", ".join(str(one["name"]) for one in self.hosts)

    @property
    def starts(self) -> datetime | None:
        return parse_ts(mt._cell(self.first, "scheduled_at"))


def _host(one: Any) -> dict[str, Any]:
    return {
        "user_id": int(one["user_id"]),
        "name": str(one.get("name") or one["user_id"]),
        "login": str(one["login"]) if one.get("login") else None,
        "part": mt.HOST,
    }


def listed_hosts(row: Any) -> list[dict[str, Any]]:
    return [one for one in mt.people_of(row) if one.get("part") == mt.HOST]


def baf_hosts(row: Any) -> list[dict[str, Any]]:
    found: dict[int, dict[str, Any]] = {}
    for one in listed_hosts(row):
        if one.get("user_id"):
            found.setdefault(int(one["user_id"]), _host(one))
    return list(found.values())


def blocks(runs: Any) -> list[Block]:
    """In schedule order: a BaF host's block runs on across the runs they host and runs with no
    host listed, and ends at a run someone else hosts. Hosts whose blocks cover the same runs
    share one block, as two runners on one run share one post. Dropped runs are off it."""
    rows = sorted((one for one in runs or () if mt._cell(one, "state") != mt.DROPPED), key=mt._when)
    open_: dict[int, list[Any]] = {}
    who: dict[int, dict[str, Any]] = {}
    closed: list[tuple[int, list[Any]]] = []
    for row in rows:
        if not listed_hosts(row):
            continue
        here = baf_hosts(row)
        ids = {one["user_id"] for one in here}
        for user_id in [one for one in open_ if one not in ids]:
            closed.append((user_id, open_.pop(user_id)))
        for one in here:
            open_.setdefault(one["user_id"], []).append(row)
            who.setdefault(one["user_id"], one)
    closed.extend(open_.items())
    merged: dict[tuple[int, ...], Block] = {}
    for user_id, mine in closed:
        key = tuple(int(mt._cell(one, "id")) for one in mine)
        found = merged.setdefault(key, Block(mine, []))
        found.hosts.append(who[user_id])
    return sorted(merged.values(), key=lambda one: (mt._when(one.first), one.user_ids))


def state_of(block: Block) -> str:
    states = [mt._cell(one, "state") for one in block.runs]
    if all(one in (mt.DONE, mt.DROPPED) for one in states):
        return DONE
    if all(one == mt.UPCOMING for one in states):
        return UPCOMING
    return LIVE


def view_row(block: Block) -> dict[str, Any]:
    """The block as a run for the runner's renderer: its first run, in the block's state."""
    first = block.first
    row = dict(first) if isinstance(first, dict) else {key: first[key] for key in first.keys()}
    row["state"] = AS_RUN_STATE[state_of(block)]
    return row


def containing(found: list[Block], run_id: Any) -> Block | None:
    return next((one for one in found if int(run_id) in one.run_ids), None)


def left_behind(record: dict[str, Any], runs: Any) -> Block | None:
    """A post that is up whose block is gone (the host unlinked, the runs
    dropped) still follows its own runs to the end, naming the hosts it was posted for."""
    wanted = set(record["runs"])
    rows = sorted((one for one in runs or () if int(mt._cell(one, "id")) in wanted), key=mt._when)
    if not rows or not record.get("hosts"):
        return None
    return Block(rows, [dict(one) for one in record["hosts"]])


def _marks(raw: Any) -> list[int]:
    kept = set()
    for one in raw or ():
        try:
            kept.add(int(one))
        except (TypeError, ValueError):
            continue
    return sorted(kept)


def _pointer(one: dict[str, Any]) -> dict[str, Any]:
    from . import marathon_announce as ma

    return {
        "hosts": [_host(host) for host in one.get("hosts") or ()],
        "message_id": int(one["message_id"]) if one.get("message_id") else None,
        "channel_id": int(one["channel_id"]) if one.get("channel_id") else None,
        "removed": bool(one.get("removed")),
        "tried": bool(one.get("tried")),
        "named": ma.named_of(one.get("named")),
        "skipped": bool(one.get("skipped")),
    }


def _record(one: dict[str, Any]) -> dict[str, Any]:
    if "start_run_id" not in one:
        run_id = int(one["run_id"])
        return {
            "start_run_id": run_id,
            "runs": [run_id],
            "marks": [],
            mrem.HOST_FIELD: {},
            "legacy_reminded": bool(one.get("reminded")),
        } | _pointer(one)
    start = int(one["start_run_id"])
    return {
        "start_run_id": start,
        "runs": [int(run) for run in one.get("runs") or ()] or [start],
        "marks": _marks(one.get("marks")),
        mrem.HOST_FIELD: mrem.posts_of(one.get(mrem.HOST_FIELD)),
    } | _pointer(one)


def records(marathon: Any) -> list[dict[str, Any]]:
    """A per-run record from `host-highlights-per-run` reads as a one-run block keyed by it."""
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
            kept.append(_record(one))
        except (KeyError, TypeError, ValueError):
            continue
    return kept


def dump(found: list[dict[str, Any]]) -> str:
    return json.dumps(found, sort_keys=True)


def _shares_host(record: dict[str, Any], block: Block) -> bool:
    return bool({one["user_id"] for one in record["hosts"]} & set(block.user_ids))


def claim(found: list[dict[str, Any]], block: Block, used: set[int]) -> dict[str, Any] | None:
    """The block's record: the one that starts where it starts, else one sharing a host and a
    run — so a block that grows, shrinks or moves keeps its post and its marks."""
    free = [one for one in found if id(one) not in used and _shares_host(one, block)]
    record = next((one for one in free if one["start_run_id"] == block.start_run_id), None)
    if record is None:
        record = next((one for one in free if set(one["runs"]) & set(block.run_ids)), None)
    if record is not None:
        used.add(id(record))
    return record


def attach(record: dict[str, Any], block: Block) -> bool:
    wanted = {
        "start_run_id": block.start_run_id,
        "runs": block.run_ids,
        "hosts": [dict(one) for one in block.hosts],
    }
    changed = any(record.get(key) != value for key, value in wanted.items())
    record.update(wanted)
    return changed


def new_record(block: Block) -> dict[str, Any]:
    record: dict[str, Any] = {
        "message_id": None,
        "channel_id": None,
        "removed": False,
        "tried": False,
        "named": None,
        "skipped": False,
        "marks": [],
        mrem.HOST_FIELD: {},
    }
    attach(record, block)
    return record


def is_up(record: Any) -> bool:
    return bool(record and record.get("message_id")) and not record.get("removed")


def auto_wanted(block: Block, record: Any) -> bool:
    """The marathon's Auto-highlight switch, as for a runner: once per block, never again once
    it was tried or taken down."""
    return (
        state_of(block) == LIVE
        and not (record and (record.get("tried") or record.get("message_id")))
    )


def as_reminded_run(block: Block, marks: Any) -> dict[str, Any]:
    """What `mt.due_marks` reads: the block's start, upcoming only while all of it is."""
    return {
        "state": mt.UPCOMING if state_of(block) == UPCOMING else mt.LIVE,
        "scheduled_at": mt._cell(block.first, "scheduled_at"),
        "reminders_sent": list(marks or ()),
    }


def due(
    block: Block, record: Any, marks: Any, now: datetime, *, stale_minutes: int
) -> tuple[int | None, list[int]]:
    return mt.due_marks(
        as_reminded_run(block, (record or {}).get("marks")),
        marks,
        now,
        stale_minutes=stale_minutes,
    )


def passed_marks(block: Block, marks: Any, now: datetime) -> list[int]:
    """Every mark whose moment is behind us: what a per-run record's one heads-up stands for."""
    at = block.starts
    if at is None:
        return []
    return sorted(int(one) for one in marks if at - timedelta(minutes=int(one)) <= now)


def rearmed(
    record: dict[str, Any], block: Block, now: datetime, mode: str = mrem.REPOST
) -> bool:
    """A block that moved later forgets every mark whose moment is ahead again — in `edit`,
    only the marks that never posted."""
    kept, posts = mrem.rearmed(
        record.get("marks"),
        record.get(mrem.HOST_FIELD) or {},
        mt._cell(block.first, "scheduled_at"),
        now,
        mode,
    )
    if kept == sorted({int(one) for one in record.get("marks") or ()}):
        return False
    record["marks"] = kept
    record[mrem.HOST_FIELD] = posts
    return True


def is_dropped(block: Block) -> bool:
    return all(mt._cell(one, "state") == mt.DROPPED for one in block.runs)


def dropped_row(block: Block) -> dict[str, Any]:
    return view_row(block) | {"state": mt.DROPPED}


__all__ = [
    "Block",
    "COLUMN",
    "DONE",
    "LIVE",
    "UPCOMING",
    "attach",
    "auto_wanted",
    "baf_hosts",
    "blocks",
    "claim",
    "containing",
    "dropped_row",
    "due",
    "dump",
    "is_dropped",
    "is_up",
    "left_behind",
    "new_record",
    "passed_marks",
    "rearmed",
    "records",
    "state_of",
    "view_row",
]
