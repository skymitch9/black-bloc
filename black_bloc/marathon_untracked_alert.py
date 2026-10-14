"""The untracked alert: a marathon with BaF on it, still not tracked as its start nears."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from . import marathon as mt
from . import marathon_inbox as mi
from .golive import parse_ts
from .timezones import unix

COLUMN = "untracked_alert_at"
POSTED = "posted"
SKIPPED = "skipped"
FAILED = "failed"
NO_ROLE = "no role is set (marathon_untracked_alert_role_id)"
RUNNER = "runner"
ROLE_GONE = "the role is not on the server"


def _cell(row: Any, key: str) -> Any:
    try:
        return row[key]
    except (IndexError, KeyError, TypeError):
        return None


def live_runs(runs: Any) -> list[Any]:
    return [one for one in runs or () if _cell(one, "state") != mt.DROPPED]


def baf_of(runs: Any) -> tuple[set[int], set[int]]:
    runners: set[int] = set()
    hosts: set[int] = set()
    for run in live_runs(runs):
        for person in mt.people_of(run):
            if not person.get("user_id"):
                continue
            if person.get("part") == mt.HOST:
                hosts.add(int(person["user_id"]))
            elif person.get("counts") is not False:
                runners.add(int(person["user_id"]))
    return (runners, hosts)


def parts_of(runs: Any) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for run in live_runs(runs):
        for person in mt.people_of(run):
            if not person.get("user_id"):
                continue
            if person.get("part") == mt.HOST:
                one = (int(person["user_id"]), mt.HOST)
            elif person.get("counts") is not False:
                one = (int(person["user_id"]), RUNNER)
            else:
                continue
            if one not in found:
                found.append(one)
    return found


def who_of(runs: Any, runner: Callable[[str], str], host: Callable[[str], str]) -> str:
    return ", ".join(
        (host if part == mt.HOST else runner)(f"<@{user_id}>") for user_id, part in parts_of(runs)
    )


def start_of(marathon: Any, runs: Any) -> datetime | None:
    found = parse_ts(_cell(marathon, "starts_at"))
    if found is not None:
        return found
    starts = [at for at in (parse_ts(_cell(one, "scheduled_at")) for one in live_runs(runs)) if at]
    return min(starts) if starts else None


def wanted(marathon: Any, runs: Any, now: datetime, hours: Any) -> bool:
    hours = int(hours or 0)
    if hours <= 0 or marathon is None or _cell(marathon, COLUMN):
        return False
    if not _cell(marathon, "active") or mi.state_of(marathon) != mi.FOUND:
        return False
    start = start_of(marathon, runs)
    if start is None or not now < start <= now + timedelta(hours=hours):
        return False
    runners, hosts = baf_of(runs)
    return bool(runners or hosts)


def hours_left(start: datetime, now: datetime) -> float:
    return round((start - now).total_seconds() / 3600, 1)


def fields_of(
    marathon: Any, runs: Any, now: datetime, role: str, who: str = ""
) -> dict[str, Any]:
    start = start_of(marathon, runs) or now
    runners, hosts = baf_of(runs)
    at = unix(start)
    return {
        "role": role,
        "name": _cell(marathon, "name") or "",
        "when": f"<t:{at}:f>",
        "relative": f"<t:{at}:R>",
        "hours": hours_left(start, now),
        "baf": len(runners | hosts),
        "runners": len(runners),
        "hosts": len(hosts),
        "who": who,
    }


def details_of(marathon: Any, runs: Any, now: datetime) -> dict[str, Any]:
    start = start_of(marathon, runs)
    runners, hosts = baf_of(runs)
    return {
        "marathon_id": _cell(marathon, "id"),
        "name": _cell(marathon, "name"),
        "starts_at": start.isoformat() if start else None,
        "hours_left": hours_left(start, now) if start else None,
        "baf_runners": len(runners),
        "baf_hosts": len(hosts),
    }
