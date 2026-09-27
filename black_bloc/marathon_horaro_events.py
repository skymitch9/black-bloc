from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

from .golive import twitch_login_from_url
from .marathon_feeds import Candidate, _cell, _recent, list_of, seen_after
from .marathon_sources import HORARO_PAGE, ScheduleError, horaro_span

log = logging.getLogger(__name__)

READS_PER_CHECK = 20
WORDS_LIMIT = 5
WORD_LENGTH = 40
OWNER_LENGTH = 60
SEARCH = "search"
NO_QUERY = (
    "this feed searches horaro.net by its name, and its name is blank — rename it to the words "
    "its events are called by, or give it search words"
)
REREAD = "It read every horaro.net event it had looked at again ({count} remembered before)."


def twitch_of(value: Any) -> str:
    """`FastPacedEvents`, `@x` or a twitch.tv link → the bare lower-case login."""
    text = str(value or "").strip().lower()
    return (twitch_login_from_url(text) or text).lstrip("@").strip("/")


def slug_of(event: Any) -> str:
    return str(event.get("slug") or "").strip() if isinstance(event, dict) else ""


def words_of(given: Any) -> list[str] | None:
    """`RGL, RGLtv` → the words, blanks and repeats dropped; None when too many or too long."""
    raw = given if isinstance(given, (list, tuple)) else re.split(r"[,\n]", str(given or ""))
    found: dict[str, str] = {}
    for one in raw:
        word = " ".join(str(one or "").split())
        if len(word) > WORD_LENGTH:
            return None
        if word:
            found.setdefault(word.lower(), word)
    return list(found.values()) if len(found) <= WORDS_LIMIT else None


def owner_clean(given: Any) -> str | None:
    owner = " ".join(str(given or "").split())
    return owner if len(owner) <= OWNER_LENGTH else None


def _is_search(one: Any) -> bool:
    return isinstance(one, dict) and isinstance(one.get(SEARCH), dict)


def search_of(feed: Any) -> dict[str, Any]:
    """The feed's own search, kept in `seen` as `{"search": {owner, words}}`."""
    for one in list_of(_cell(feed, "seen")):
        if _is_search(one):
            given = one[SEARCH]
            return {
                "owner": owner_clean(given.get("owner")) or "",
                "words": words_of(given.get("words")) or [],
            }
    return {"owner": "", "words": []}


def search_with(feed: Any, **changed: Any) -> list[Any]:
    """`seen` with the search replaced by the current one plus `changed`; dropped when blank."""
    search = search_of(feed) | changed
    kept = [one for one in list_of(_cell(feed, "seen")) if not _is_search(one)]
    if search["owner"] or search["words"]:
        return [{SEARCH: search}, *kept]
    return kept


def search_kept(feed: Any, seen: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The memory to write back: the feed's search first, then the events."""
    head = [one for one in list_of(_cell(feed, "seen")) if _is_search(one)][:1]
    return [*head, *seen]


def forgotten(feed: Any) -> str | None:
    """Look again's `seen`: every event forgotten, the search kept."""
    head = search_kept(feed, [])
    return json.dumps(head) if head else None


def queries(feed: Any) -> list[str]:
    """The search words, or the feed's name when it has none."""
    words = search_of(feed)["words"]
    name = " ".join(str(_cell(feed, "name") or "").split())
    return words or ([name] if name else [])


def seen_of(feed: Any) -> list[dict[str, Any]]:
    """Every event this feed looked at, `{ref, twitch}`, with its first schedule once read."""
    found: list[dict[str, Any]] = []
    for one in list_of(_cell(feed, "seen")):
        if isinstance(one, dict) and one.get("ref"):
            found.append(dict(one) | {"ref": str(one["ref"]), "twitch": twitch_of(one["twitch"])})
    return found


def is_ours(event: Any, login: str, owner: str = "") -> bool:
    """The event names the channel's Twitch, or the feed's horaro.net owner owns it."""
    if not slug_of(event):
        return False
    wanted = twitch_of(login)
    if wanted and twitch_of(event.get("twitch")) == wanted:
        return True
    boss = str(owner or "").strip().lower()
    return bool(boss) and str(event.get("owner") or "").strip().lower() == boss


def ours(events: Any, login: str, owner: str = "") -> list[dict[str, Any]]:
    return [one for one in events or () if is_ours(one, login, owner)]


def to_read(
    events: Any, seen: list[dict[str, Any]], login: str, owner: str = ""
) -> list[dict[str, Any]]:
    """The channel's events whose schedules were never read, or were read before one existed."""
    settled = {one["ref"] for one in seen if one.get("schedule")}
    found: dict[str, dict[str, Any]] = {}
    for one in ours(events, login, owner):
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
    events: Any,
    seen: list[dict[str, Any]],
    login: str,
    now: datetime,
    recent_days: int,
    owner: str = "",
) -> list[Candidate]:
    """One per channel event this search lists whose first schedule ends ahead of now (or
    within `recent_days`); the ref is `<event>/<schedule>`, a pasted link's own ref."""
    listed = {slug_of(one).lower() for one in ours(events, login, owner)}
    found: list[Candidate] = []
    for one in seen:
        if one["ref"] not in listed or not one.get("schedule"):
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
    """One search per search word (or by the feed's name), then one schedules read per channel
    event not settled; the memory comes back only when it changed."""
    words = queries(feed)
    if not words:
        raise ScheduleError(NO_QUERY)
    owner = search_of(feed)["owner"]
    events = await searched(client, words)
    seen = seen_of(feed)
    reading = to_read(events, seen, login, owner)
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
    found = candidates(events, seen, login, now, recent_days, owner)
    return found, (search_kept(feed, seen) if changed else None)


async def searched(client: Any, words: list[str]) -> list[dict[str, Any]]:
    """Every word's search, one list, each event once (by slug)."""
    found: dict[str, dict[str, Any]] = {}
    for word in words:
        for one in await client.horaro_events(word) or ():
            if slug_of(one):
                found.setdefault(slug_of(one).lower(), one)
    return list(found.values())


__all__ = [
    "NO_QUERY",
    "OWNER_LENGTH",
    "READS_PER_CHECK",
    "REREAD",
    "WORDS_LIMIT",
    "WORD_LENGTH",
    "candidates",
    "check",
    "forgotten",
    "is_ours",
    "listed_record",
    "ours",
    "owner_clean",
    "queries",
    "read_record",
    "remembered",
    "search_kept",
    "search_of",
    "search_with",
    "searched",
    "seen_of",
    "slug_of",
    "to_read",
    "twitch_of",
    "words_of",
]
