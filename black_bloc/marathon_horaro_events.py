from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from .golive import twitch_login_from_url
from .marathon_feeds import Candidate, _cell, _recent, list_of, seen_after
from .marathon_sources import HORARO_PAGE, ScheduleError, horaro_span

log = logging.getLogger(__name__)

READS_PER_CHECK = 20
NO_QUERY = (
    "this feed searches horaro.net by its name, and its name is blank — rename it to the words "
    "its events are called by"
)
REREAD = "It read every horaro.net event it had looked at again ({count} remembered before)."


def twitch_of(value: Any) -> str:
    """`FastPacedEvents`, `@x` or a twitch.tv link → the bare lower-case login."""
    text = str(value or "").strip().lower()
    return (twitch_login_from_url(text) or text).lstrip("@").strip("/")


def slug_of(event: Any) -> str:
    return str(event.get("slug") or "").strip() if isinstance(event, dict) else ""


def seen_of(feed: Any) -> list[dict[str, Any]]:
    """Every event this feed looked at, `{ref, twitch}`, with its first schedule once read."""
    found: list[dict[str, Any]] = []
    for one in list_of(_cell(feed, "seen")):
        if isinstance(one, dict) and one.get("ref"):
            found.append(dict(one) | {"ref": str(one["ref"]), "twitch": twitch_of(one["twitch"])})
    return found


def ours(events: Any, login: str) -> list[dict[str, Any]]:
    wanted = twitch_of(login)
    if not wanted:
        return []
    return [one for one in events or () if slug_of(one) and twitch_of(one.get("twitch")) == wanted]


def to_read(events: Any, seen: list[dict[str, Any]], login: str) -> list[dict[str, Any]]:
    """The channel's events whose schedules were never read, or were read before one existed."""
    settled = {one["ref"] for one in seen if one.get("schedule")}
    found: dict[str, dict[str, Any]] = {}
    for one in ours(events, login):
        found.setdefault(slug_of(one).lower(), one)
    return [one for ref, one in found.items() if ref not in settled][:READS_PER_CHECK]


def listed_record(event: dict[str, Any]) -> dict[str, Any]:
    return {"ref": slug_of(event).lower(), "twitch": twitch_of(event.get("twitch"))}


def read_record(event: dict[str, Any], schedules: Any) -> dict[str, Any]:
    """The event and its first listed schedule — the one a pasted horaro.net link reads."""
    record = listed_record(event)
    first = next((one for one in schedules or () if slug_of(one)), None)
    if first is None:
        return record
    starts, ends = horaro_span(first)
    schedule = slug_of(first).lower()
    name = " ".join(str(event.get("name") or first.get("name") or record["ref"]).split())
    return record | {
        "schedule": schedule,
        "name": name[:100],
        "starts_at": starts,
        "ends_at": ends,
        "url": first.get("link") or HORARO_PAGE.format(ref=f"{record['ref']}/{schedule}"),
    }


def remembered(seen: list[dict[str, Any]], records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """This check's records in place of what the memory said about the same events, capped."""
    fresh = {one["ref"] for one in records}
    return seen_after([one for one in seen if one["ref"] not in fresh], records)


def candidates(
    events: Any, seen: list[dict[str, Any]], login: str, now: datetime, recent_days: int
) -> list[Candidate]:
    """One per channel event this search lists whose first schedule ends ahead of now (or
    within `recent_days`); the ref is `<event>/<schedule>`, a pasted link's own ref."""
    listed = {slug_of(one).lower() for one in ours(events, login)}
    wanted = twitch_of(login)
    found: list[Candidate] = []
    for one in seen:
        if one["ref"] not in listed or one["twitch"] != wanted or not one.get("schedule"):
            continue
        if not _recent(one.get("ends_at") or one.get("starts_at"), now, recent_days):
            continue
        ref = f"{one['ref']}/{one['schedule']}"
        url = str(one.get("url") or HORARO_PAGE.format(ref=ref))
        name = str(one.get("name") or one["ref"])[:100]
        found.append(Candidate(ref, name, one.get("starts_at"), one.get("ends_at"), url))
    found.sort(key=lambda one: (one.starts_at or "", one.ref))
    return found


async def check(
    client: Any, feed: Any, login: str, now: datetime, recent_days: int
) -> tuple[list[Candidate], list[dict[str, Any]] | None]:
    """One search by the feed's name, then one schedules read per channel event not settled;
    the memory comes back only when it changed."""
    query = " ".join(str(_cell(feed, "name") or "").split())
    if not query:
        raise ScheduleError(NO_QUERY)
    events = await client.horaro_events(query)
    seen = seen_of(feed)
    reading = to_read(events, seen, login)
    skip = {one["ref"] for one in seen} | {slug_of(one).lower() for one in reading}
    listed = {listed_record(one)["ref"]: listed_record(one) for one in events or () if slug_of(one)}
    records = [one for ref, one in listed.items() if ref not in skip]
    for event in reading:
        try:
            records.append(read_record(event, await client.horaro_schedules(slug_of(event))))
        except ScheduleError as exc:
            log.info("marathon: horaro.net %s unread (%s); next check", slug_of(event), exc)
    changed = [one for one in records if one not in seen]
    if changed:
        seen = remembered(seen, changed)
    return candidates(events, seen, login, now, recent_days), (seen if changed else None)


__all__ = [
    "NO_QUERY",
    "READS_PER_CHECK",
    "REREAD",
    "candidates",
    "check",
    "listed_record",
    "ours",
    "read_record",
    "remembered",
    "seen_of",
    "slug_of",
    "to_read",
    "twitch_of",
]
