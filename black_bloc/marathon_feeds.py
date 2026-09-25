from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, NamedTuple

from .golive import parse_ts
from .marathon import MarathonMove, stamp_of
from .marathon_sources import (
    GDQ,
    HORARO,
    HORARO_PAGE,
    RPGLB,
    SOURCE_WORDS,
    TRACKER_BASES,
    event_url,
    horaro_span,
    tracker_source,
    utc_iso,
)
from .timezones import unix

TRACKER = "tracker"
HORARO_FEED = "horaro"
FEED_SOURCES = (TRACKER, HORARO_FEED)
ADD = "add"
SUGGEST = "suggest"
ACTIONS = (ADD, SUGGEST)
ACTION_WORDS = {ADD: "adds", SUGGEST: "suggests"}
VIA_FEED = "feed"
BECAUSE_STAFF = "staff"
BECAUSE_CHANNEL = "channel_removed"
FAILURES_IMPORTANT = 3
NAME_LIMIT = 60


class Seed(NamedTuple):
    login: str
    source: str
    feed_ref: str
    name: str


SEEDS = (
    Seed("gamesdonequick", TRACKER, TRACKER_BASES[GDQ], "GDQ"),
    Seed("rpglimitbreak", TRACKER, TRACKER_BASES[RPGLB], "RPG Limit Break"),
)

PICK_GDQ = "gdq"
PICK_RPGLB = "rpglb"
PICK_HORARO = "horaro"
PICKS = {
    PICK_GDQ: (TRACKER, TRACKER_BASES[GDQ]),
    PICK_RPGLB: (TRACKER, TRACKER_BASES[RPGLB]),
    PICK_HORARO: (HORARO_FEED, None),
}
PICK_WORDS = {
    PICK_GDQ: "the GDQ tracker",
    PICK_RPGLB: "the RPG Limit Break tracker",
    PICK_HORARO: "horaro.net — give the event's slug",
}
PICK_NAMES = {PICK_GDQ: "GDQ", PICK_RPGLB: "RPG Limit Break"}

NO_CHANNEL = "A feed belongs to a channel Black Bloc already watches — add the channel first."
CHANNEL_HAS_FEED = (
    "**{channel}** already has a feed, **{name}**, so nothing was added. One channel, one feed — "
    "remove that one first."
)
SAME_FEED = "**{name}** already reads that, so nothing was added."
UNKNOWN_PICK = (
    "**{given}** is not something a feed can read, so nothing was added. Pick the GDQ tracker, "
    "the RPG Limit Break tracker or horaro.net."
)
NO_SLUG = (
    "A horaro.net feed needs the event's slug — the part after horaro.net/, for example `esa` — "
    "so nothing was added."
)
SLUG_UNREADABLE = "horaro.net did not answer for **{slug}** ({why}), so nothing was added."
NO_SUCH_FEED = "Black Bloc has no feed **{given}** here, so nothing was done."
BAD_ACTION = "Say add or suggest for what a feed does with a new event, so nothing was changed."
BAD_ACTIVE = "Say true to check this feed or false to pause it, so nothing was changed."
BAD_NAME = "A feed needs a name, so nothing was changed."
BAD_REF = "Name the event to add or dismiss, so nothing was changed."
FEED_ADDED = (
    "**{name}** now reads {source} for **{channel}** and {action} every new event it finds. "
    "{checked}"
)
FEED_REMOVED = "**{name}** is gone. The marathons it added stay on the list."
FEED_PAUSED = "**{name}** is paused — it checks nothing until it is resumed."
FEED_HELD = (
    "**{name}** is paused because **{channel}** is opted out of marathons — turn marathons back "
    "on for the channel first, so nothing was changed."
)
FEED_RESUMED = "**{name}** checks again."
FEED_ACTION_SET = "**{name}** now {action} every new event it finds."
FEED_RENAMED = "The feed is called **{name}** now."
FEED_MOVED = "**{name}** now belongs to **{channel}**."
FEED_CHECKED = (
    "**{name}** was checked just now: {found} event(s) ahead, {added} added, {suggested} "
    "suggested."
)
FEED_CHECK_FAILED = "**{name}** could not be checked just now — {why}. Nothing was changed."
FEED_FORGOT = "**{name}** forgot {count} removed event(s); the next check may add them again."
FEED_NOTHING_TO_FORGET = "**{name}** remembers no removed event, so there was nothing to forget."
FEED_LOOKED = "**{name}** forgot {count} dismissed event(s) and looked again."
SUGGESTION_GONE = "**{event}** is not waiting on **{name}** any more, so nothing was changed."
SUGGESTION_DISMISSED = "**{event}** is dismissed — **{name}** will not suggest it again."
SUGGESTION_ALREADY = "**{event}** is already on the list as **{marathon}**, so nothing was added."
NOTICE_PAUSED = "Paused by {who}."
NOTICE_REMOVED = "Removed by {who} — the feed will not add it again."
NOTICE_ADDED = "Added by {who}."
NOTICE_DISMISSED = "Dismissed by {who}."
NOTICE_GONE = "That marathon is not on the list any more, so nothing was done."
FEED_OFF = (
    "Feeds are off (marathon_feeds), so nothing checks on its own; Check now still works."
)
NEVER_CHECKED = "not checked yet"
CHECKED_AGO = "last checked <t:{unix}:R>"
CHECK_TROUBLE = "could not be checked since <t:{unix}:f> — {why}"
FEED_LINE = "**{name}** · {source} · {channel} · {action} · every {hours} h · {read}{paused}"
PAUSED_MARK = " · **paused**"
IGNORED_LINE = "{count} removed event(s) it will not add again"
NO_FEEDS = "No feeds yet. **Add a feed…** picks one of the channels Black Bloc watches."
FEEDS_TITLE = "Marathon feeds"
PICK_FEED = "Pick a feed to manage…"
PICK_CHANNEL = "Pick the channel the feed belongs to…"
PICK_SUGGESTION = "Pick a waiting event…"
ADD_FEED_TITLE = "Add a feed"
ADD_FEED_SOURCE = "Read from — gdq, rpglb or horaro"
ADD_FEED_SLUG = "horaro.net event slug — horaro only"
ADD_FEED_SLUG_HINT = "esa"
ADD_FEED_NAME = "Name — blank for the channel's"
NO_CHANNELS = "There is no channel-only row on the Go-live page yet, so there is nothing to feed."
SUGGESTION_LINE = "**{event}** — {when} ({relative})"
WAITING_HEAD = "Waiting for staff:"
CHANNEL_GONE = "a channel that is gone"

FEED_ADD = "feed_add"
FEED_CHECK = "feed_check"
FEED_PAUSE = "feed_pause"
FEED_RESUME = "feed_resume"
FEED_ACTION = "feed_action"
FEED_LOOK = "feed_look"
FEED_FORGET = "feed_forget"
FEED_REMOVE = "feed_remove"
FEED_BACK = "feed_back"
FEED_TAKE = "feed_take"
FEED_DISMISS = "feed_dismiss"

FEED_ADD_MOVE = MarathonMove(FEED_ADD, "Add a feed…", "primary", 2)
FEED_CHECK_MOVE = MarathonMove(FEED_CHECK, "Check now", "primary", 2)
FEED_PAUSE_MOVE = MarathonMove(FEED_PAUSE, "Pause", row=2)
FEED_RESUME_MOVE = MarathonMove(FEED_RESUME, "Resume", row=2)
FEED_TO_SUGGEST_MOVE = MarathonMove(FEED_ACTION, "Suggest instead of adding", row=2)
FEED_TO_ADD_MOVE = MarathonMove(FEED_ACTION, "Add instead of suggesting", row=2)
FEED_LOOK_MOVE = MarathonMove(FEED_LOOK, "Look again", row=3)
FEED_FORGET_MOVE = MarathonMove(FEED_FORGET, "Forget ignored", row=3)
FEED_REMOVE_MOVE = MarathonMove(FEED_REMOVE, "Remove", "danger", 3)
FEED_TAKE_MOVE = MarathonMove(FEED_TAKE, "Add it", "primary", 2)
FEED_DISMISS_MOVE = MarathonMove(FEED_DISMISS, "Not this one", row=2)
FEED_BACK_MOVE = MarathonMove(FEED_BACK, "Back", row=4)
REMOVE_FEED_QUESTION = (
    "Remove the feed **{name}**? It stops checking; the marathons it added stay on the list."
)


class Candidate(NamedTuple):
    ref: str
    name: str
    starts_at: str | None
    ends_at: str | None
    url: str


def _cell(row: Any, key: str, fallback: Any = None) -> Any:
    if row is None:
        return fallback
    try:
        return row[key]
    except (IndexError, KeyError):
        return fallback


def marathon_source(feed: Any) -> str | None:
    """The `source` word the marathons a feed makes carry: gdq / rpglb / horaro."""
    kind = _cell(feed, "source")
    if kind == TRACKER:
        return tracker_source(_cell(feed, "feed_ref"))
    if kind == HORARO_FEED:
        return HORARO
    return None


def source_word(feed: Any) -> str:
    found = marathon_source(feed)
    if found == HORARO:
        return f"horaro.net/{_cell(feed, 'feed_ref')}"
    return SOURCE_WORDS.get(str(found or ""), str(_cell(feed, "feed_ref") or ""))


def pick_of(given: Any) -> tuple[str, str | None] | None:
    return PICKS.get(str(given or "").strip().lower())


def pick_for(feed: Any) -> str | None:
    source = marathon_source(feed)
    if source == HORARO:
        return PICK_HORARO
    return {GDQ: PICK_GDQ, RPGLB: PICK_RPGLB}.get(str(source or ""))


def list_of(raw: Any) -> list[Any]:
    if isinstance(raw, list):
        return list(raw)
    try:
        found = json.loads(raw) if raw else []
    except (TypeError, ValueError):
        return []
    return found if isinstance(found, list) else []


def suggested_of(feed: Any) -> list[dict[str, Any]]:
    return [one for one in list_of(_cell(feed, "suggested")) if isinstance(one, dict)]


def open_suggestions(feed: Any) -> list[dict[str, Any]]:
    return [one for one in suggested_of(feed) if not one.get("dismissed_at")]


def dismissed_of(feed: Any) -> list[dict[str, Any]]:
    return [one for one in suggested_of(feed) if one.get("dismissed_at")]


def ignored_of(feed: Any) -> list[str]:
    return [str(one) for one in list_of(_cell(feed, "ignored")) if one not in (None, "")]


def check_due(feed: Any, now: datetime, hours: int) -> bool:
    """An active feed is checked when it never was, or its last check is `hours` old."""
    if not bool(_cell(feed, "active", 1)):
        return False
    last = parse_ts(_cell(feed, "last_checked_at"))
    return last is None or now - last >= timedelta(hours=max(1, int(hours)))


def _recent(moment: Any, now: datetime, recent_days: int) -> bool:
    at = parse_ts(moment)
    return at is not None and at >= now - timedelta(days=max(0, int(recent_days)))


def tracker_candidates(
    source: str, events: Any, now: datetime, recent_days: int
) -> list[Candidate]:
    """Every event still ahead (or started within `recent_days`); archived ones are history.
    A draft is kept: every announced tracker event is a draft until its schedule is up."""
    found: list[Candidate] = []
    for row in events or ():
        if not isinstance(row, dict) or row.get("id") is None or row.get("archived"):
            continue
        starts = utc_iso(row.get("datetime"))
        if starts is None or not _recent(starts, now, recent_days):
            continue
        name = " ".join(str(row.get("name") or row.get("short") or row["id"]).split())
        found.append(
            Candidate(str(row["id"]), name[:100], starts, None, event_url(row["id"], source))
        )
    found.sort(key=lambda one: (one.starts_at or "", one.ref))
    return found


def horaro_candidates(
    event: str, feed_name: str, schedules: Any, now: datetime, recent_days: int
) -> list[Candidate]:
    """Every listed schedule that ends ahead of now (or ended within `recent_days`)."""
    found: list[Candidate] = []
    for row in schedules or ():
        slug = str(_cell(row, "slug") or "").strip().lower() if isinstance(row, dict) else ""
        if not slug:
            continue
        starts, ends = horaro_span(row)
        if not _recent(ends or starts, now, recent_days):
            continue
        ref = f"{str(event).lower()}/{slug}"
        title = " ".join(str(row.get("name") or slug).split())
        name = f"{feed_name} {title}" if feed_name and feed_name not in title else title
        found.append(
            Candidate(ref, name[:100], starts, ends, row.get("link") or HORARO_PAGE.format(ref=ref))
        )
    found.sort(key=lambda one: (one.starts_at or "", one.ref))
    return found


def fresh(
    candidates: list[Candidate], *, known: set[str], ignored: list[str], seen: list[str]
) -> list[Candidate]:
    """Never twice: not a marathon already (paused and over ones count), not removed by staff,
    not already suggested or dismissed."""
    skip = set(known) | set(ignored) | set(seen)
    return [one for one in candidates if one.ref not in skip]


def suggestion_record(candidate: Candidate, now: datetime) -> dict[str, Any]:
    return {
        "ref": candidate.ref,
        "name": candidate.name,
        "starts_at": candidate.starts_at,
        "url": candidate.url,
        "found_at": now.isoformat(),
        "dismissed_at": None,
    }


def notice_fields(feed: Any, record: Any, channel: str = "") -> dict[str, Any]:
    record = record or {}
    return {
        "feed": _cell(feed, "name") or "",
        "event": record.get("name") or "",
        "when": stamp_of(record.get("starts_at"), "D"),
        "relative": stamp_of(record.get("starts_at"), "R"),
        "url": record.get("url") or "",
        "channel": channel,
    }


def read_line(feed: Any) -> str:
    checked = parse_ts(_cell(feed, "last_checked_at"))
    if checked is None:
        return NEVER_CHECKED
    if _cell(feed, "last_ok") == 0:
        return CHECK_TROUBLE.format(unix=unix(checked), why=_cell(feed, "last_error") or "")
    return CHECKED_AGO.format(unix=unix(checked))


def feed_line(feed: Any, channel: str, hours: int) -> str:
    return FEED_LINE.format(
        name=_cell(feed, "name"),
        source=source_word(feed),
        channel=channel,
        action=ACTION_WORDS.get(str(_cell(feed, "action")), str(_cell(feed, "action"))),
        hours=hours,
        read=read_line(feed),
        paused="" if _cell(feed, "active", 1) else PAUSED_MARK,
    )


def suggestion_line(record: dict[str, Any]) -> str:
    return SUGGESTION_LINE.format(
        event=record.get("name") or record.get("ref"),
        when=stamp_of(record.get("starts_at"), "D"),
        relative=stamp_of(record.get("starts_at"), "R"),
    )


def feed_moves(feed: Any) -> tuple[MarathonMove, ...]:
    """Only moves that change something: Look again with a dismissal, Forget with an ignore."""
    active = bool(_cell(feed, "active", 1))
    found = [FEED_CHECK_MOVE, FEED_PAUSE_MOVE if active else FEED_RESUME_MOVE]
    found.append(FEED_TO_SUGGEST_MOVE if _cell(feed, "action") == ADD else FEED_TO_ADD_MOVE)
    if dismissed_of(feed):
        found.append(FEED_LOOK_MOVE)
    if ignored_of(feed):
        found.append(FEED_FORGET_MOVE)
    found += [FEED_REMOVE_MOVE, FEED_BACK_MOVE]
    return tuple(found)


def suggestion_moves() -> tuple[MarathonMove, ...]:
    return (FEED_TAKE_MOVE, FEED_DISMISS_MOVE, FEED_BACK_MOVE)


def clean_name(given: Any) -> str:
    return " ".join(str(given or "").split())[:NAME_LIMIT]


__all__ = [
    "ACTIONS",
    "ADD",
    "FEED_SOURCES",
    "HORARO_FEED",
    "SEEDS",
    "SUGGEST",
    "TRACKER",
    "VIA_FEED",
    "Candidate",
    "check_due",
    "feed_line",
    "feed_moves",
    "fresh",
    "horaro_candidates",
    "ignored_of",
    "marathon_source",
    "open_suggestions",
    "suggested_of",
    "suggestion_record",
    "tracker_candidates",
]
