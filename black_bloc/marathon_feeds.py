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
    OENGUS,
    RPGLB,
    SOURCE_WORDS,
    TRACKER_BASES,
    event_url,
    horaro_span,
    schedule_page,
    tracker_source,
    utc_iso,
)
from .timezones import unix

TRACKER = "tracker"
HORARO_FEED = "horaro"
OENGUS_FEED = "oengus"
FEED_SOURCES = (TRACKER, HORARO_FEED, OENGUS_FEED)
ADD = "add"
SUGGEST = "suggest"
ACTIONS = (ADD, SUGGEST)
ACTION_WORDS = {ADD: "adds", SUGGEST: "suggests"}
VIA_FEED = "feed"
BECAUSE_STAFF = "staff"
BECAUSE_CHANNEL = "channel_removed"
FAILURES_IMPORTANT = 3
NAME_LIMIT = 60
SEEN_LIMIT = 2000
OENGUS_READS_PER_CHECK = 40


class Seed(NamedTuple):
    login: str
    source: str
    feed_ref: str
    name: str


SEEDS = (
    Seed("gamesdonequick", TRACKER, TRACKER_BASES[GDQ], "GDQ"),
    Seed("rpglimitbreak", TRACKER, TRACKER_BASES[RPGLB], "RPG Limit Break"),
    Seed("speedstuff4charity", OENGUS_FEED, "speedstuff4charity", "Speed Stuff 4 Charity"),
)

PICK_GDQ = "gdq"
PICK_RPGLB = "rpglb"
PICK_HORARO = "horaro"
PICK_OENGUS = "oengus"
PICKS = {
    PICK_GDQ: (TRACKER, TRACKER_BASES[GDQ]),
    PICK_RPGLB: (TRACKER, TRACKER_BASES[RPGLB]),
    PICK_HORARO: (HORARO_FEED, None),
    PICK_OENGUS: (OENGUS_FEED, None),
}
PICK_WORDS = {
    PICK_GDQ: "the GDQ tracker",
    PICK_RPGLB: "the RPG Limit Break tracker",
    PICK_HORARO: "horaro.net — give the event's slug",
    PICK_OENGUS: (
        "Oengus — finds this channel's marathons on oengus.io (Speed Stuff 4 Charity's home)"
    ),
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
    "the RPG Limit Break tracker, horaro.net or Oengus."
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
FEED_REREAD = "It read every Oengus marathon's record again ({count} remembered before)."
SUGGESTION_GONE = "**{event}** is not waiting on **{name}** any more, so nothing was changed."
SUGGESTION_DISMISSED = "**{event}** is dismissed — **{name}** will not suggest it again."
SUGGESTION_ALREADY = "**{event}** is already on the list as **{marathon}**, so nothing was added."
NOTICE_PAUSED = "Paused by {who}."
NOTICE_REMOVED = "Removed by {who} — the feed will not add it again."
NOTICE_ADDED = "Added by {who}."
NOTICE_DISMISSED = "Dismissed by {who}."
NOTICE_GONE = "That marathon is not on the list any more, so nothing was done."
NOTICE_WHEN = "When"
NOTICE_READ_FROM = "Read from"
NOTICE_CHANNEL = "Channel"
NOTICE_SCHEDULE = "Schedule"
NOTICE_EVENT = "Event"
NOTICE_FOUND_BY = "Found by"
NOTICE_NO_DATES = "dates not published yet"
NOTICE_NO_CHANNEL = "no channel row"
NOTICE_FEED_GONE = "a feed that has since been removed"
NOTICE_WHEN_RANGE = "<t:{starts}:f> – <t:{ends}:f>"
NOTICE_READING = "{read} · {next} · {counts}"
NOTICE_READ_LABEL = "Read it now"
NOTICE_MANAGE_LABEL = "Manage…"
NOTICE_SITE_LABEL = "Open on the site"
NOTICE_MODE_PLACEHOLDER = "Event: none / marathon / runs / both"
FEED_OFF = (
    "Feeds are off (marathon_feeds), so nothing checks on its own; Check now still works."
)
NEVER_CHECKED = "not checked yet"
CHECKED_AGO = "last checked <t:{unix}:R>"
CHECK_TROUBLE = "could not be checked since <t:{unix}:f> — {why}"
FEED_LINE = "**{name}** · {source} · {channel} · {action} · every {hours} h · {read}{paused}"
FEED_HEAD_LINE = "**{name}** · {source} · {channel} · {action}"
FEED_READING = "**Checks:** every {hours} h · {read}{next}{paused}"
NEXT_CHECK = " · next check <t:{unix}:R>"
PAUSED_MARK = " · **paused**"
IGNORED_LINE = "{count} removed event(s) it will not add again"
NO_FEEDS = "No feeds yet. **Add a feed…** picks one of the channels Black Bloc watches."
FEEDS_TITLE = "Marathon feeds"
PICK_FEED = "Pick a feed to manage…"
PICK_CHANNEL = "Pick the channel the feed belongs to…"
PICK_SUGGESTION = "Pick a waiting event…"
ADD_FEED_TITLE = "Add a feed"
ADD_FEED_SOURCE = "Read from — gdq, rpglb, horaro or oengus"
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
    if kind == OENGUS_FEED:
        return OENGUS
    return None


def source_word(feed: Any) -> str:
    found = marathon_source(feed)
    if found == HORARO:
        return f"horaro.net/{_cell(feed, 'feed_ref')}"
    if found == OENGUS:
        return SOURCE_WORDS[OENGUS]
    return SOURCE_WORDS.get(str(found or ""), str(_cell(feed, "feed_ref") or ""))


def pick_of(given: Any) -> tuple[str, str | None] | None:
    return PICKS.get(str(given or "").strip().lower())


def pick_for(feed: Any) -> str | None:
    source = marathon_source(feed)
    if source == HORARO:
        return PICK_HORARO
    if source == OENGUS:
        return PICK_OENGUS
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


def seen_of(feed: Any) -> list[dict[str, Any]]:
    """What each Oengus marathon's v1 record said, read once: `{ref, twitch}`."""
    found: list[dict[str, Any]] = []
    for one in list_of(_cell(feed, "seen")):
        if isinstance(one, dict) and one.get("ref"):
            found.append({"ref": str(one["ref"]), "twitch": str(one.get("twitch") or "").lower()})
        elif isinstance(one, str) and one:
            found.append({"ref": one, "twitch": ""})
    return found


def seen_after(seen: list[dict[str, Any]], read: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The memory with this check's reads added, newest kept when it outgrows SEEN_LIMIT."""
    return [*seen, *read][-SEEN_LIMIT:]


def to_read(listed: Any, seen: list[dict[str, Any]]) -> list[str]:
    """The `for-home` ids whose v1 record was never read, capped per check."""
    known = {one["ref"] for one in seen}
    found = [str(row["id"]) for row in listed or () if str(row.get("id")) not in known]
    return found[:OENGUS_READS_PER_CHECK]


def seen_record(ref: str, record: Any) -> dict[str, Any]:
    twitch = record.get("twitch") if isinstance(record, dict) else None
    return {"ref": str(ref), "twitch": str(twitch or "").strip().lower()}


def oengus_candidates(
    listed: Any, seen: list[dict[str, Any]], login: str, now: datetime, recent_days: int
) -> list[Candidate]:
    """Every listed marathon whose v1 `twitch` is the channel's login, ending ahead of now (or
    within `recent_days`)."""
    wanted = str(login or "").strip().lower()
    ours = {one["ref"] for one in seen if wanted and one["twitch"] == wanted}
    found: list[Candidate] = []
    for row in listed or ():
        ref = str(row.get("id") or "") if isinstance(row, dict) else ""
        if ref not in ours:
            continue
        starts, ends = utc_iso(row.get("startDate")), utc_iso(row.get("endDate"))
        if not _recent(ends or starts, now, recent_days):
            continue
        name = " ".join(str(row.get("name") or ref).split())
        found.append(Candidate(ref, name[:100], starts, ends, schedule_page(OENGUS, ref)))
    found.sort(key=lambda one: (one.starts_at or "", one.ref))
    return found


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


def reading_line(feed: Any, hours: int) -> str:
    checked = parse_ts(_cell(feed, "last_checked_at"))
    active = bool(_cell(feed, "active", 1))
    due = checked + timedelta(hours=int(hours)) if checked is not None and active else None
    return FEED_READING.format(
        hours=hours,
        read=read_line(feed),
        next=NEXT_CHECK.format(unix=unix(due)) if due is not None else "",
        paused="" if active else PAUSED_MARK,
    )


def head_line(feed: Any, channel: str) -> str:
    return FEED_HEAD_LINE.format(
        name=_cell(feed, "name"),
        source=source_word(feed),
        channel=channel,
        action=ACTION_WORDS.get(str(_cell(feed, "action")), str(_cell(feed, "action"))),
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
    if dismissed_of(feed) or seen_of(feed):
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
    "OENGUS_FEED",
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
    "oengus_candidates",
    "open_suggestions",
    "seen_after",
    "seen_of",
    "seen_record",
    "suggested_of",
    "suggestion_record",
    "to_read",
    "tracker_candidates",
]
