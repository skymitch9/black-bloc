"""The marathon inbox: one thread where found marathons are managed, one per tracked marathon."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .golive import parse_ts
from .marathon import BACK_MOVE, POLL_MOVE, MarathonMove

FOUND = "found"
TRACKED = "tracked"
IGNORED = "ignored"
ARCHIVED = "archived"
STATES = (FOUND, TRACKED, IGNORED, ARCHIVED)

WHEN_PUBLISHED = "published"
WHEN_ADDED = "added"

HOME_ON = "on"
HOME_SHADOW = "shadow"

TRACK = "track"
IGNORE = "ignore"
UNTRACK = "untrack"
ANYWAY = "anyway"
UNIGNORE = "unignore"
ACTIONS = (TRACK, IGNORE, UNTRACK, ANYWAY)
INBOX_TEMPLATE = r"marathon:inbox:(?P<marathon_id>[0-9]+):(?P<action>track|ignore|untrack|anyway)"
MOVES_BY_STATE = {
    FOUND: (TRACK, IGNORE),
    TRACKED: (UNTRACK,),
    IGNORED: (ANYWAY,),
    ARCHIVED: (),
}
DEFAULT_LABELS = {
    TRACK: "Track",
    IGNORE: "Ignore",
    UNTRACK: "Untrack",
    ANYWAY: "Track anyway",
}

AUTO_ARCHIVE_MINUTES = 10080
RECHECK_MINUTES = 60
THREAD_NAME_LIMIT = 100
THREAD_NAME_FALLBACK = "marathon"
CHANNEL_URL = "https://discord.com/channels/{guild}/{channel}"
MESSAGE_URL = "https://discord.com/channels/{guild}/{channel}/{message}"
WHEN = "<t:{at}:d>"
CARD_THREAD = "{state} · [thread]({url})"

NOT_TRACKED = "the marathon is not tracked"
AUTO_WHO_BOT = "Black Bloc"
NOWHERE = "nowhere yet — marathon posts are off, or no channel is set for them"
WHERE_THREAD = "its own thread, beside the inbox"
WHERE_CHANNEL = "the marathon channel"
NO_INBOX_CHANNEL = "no channel is set for the marathon inbox (marathon_inbox_channel_id)"
NO_THREAD_CHANNEL = "no channel is set for marathon threads (marathon_thread_channel_id)"
CANNOT_THREAD = "that channel does not take threads"
NOT_READ = "the thread could not be read just now"
NO_THREAD_WANTED = "no_thread"
UNTRACK_BECAUSE = "untracked"
THREAD_ARCHIVE_REASON = "Black Bloc: the marathon is not tracked any more"
INBOX_REASON = "Black Bloc: the marathon inbox"
THREAD_REASON = "Black Bloc: a tracked marathon"

TRACK_MOVE = MarathonMove(TRACK, "Track", "primary", 4)
IGNORE_MOVE = MarathonMove(IGNORE, "Ignore", row=4)
UNTRACK_MOVE = MarathonMove(UNTRACK, "Untrack", row=4)
ANYWAY_MOVE = MarathonMove(ANYWAY, "Track anyway", "primary", 4)
MOVE_OF = {TRACK: TRACK_MOVE, IGNORE: IGNORE_MOVE, UNTRACK: UNTRACK_MOVE, ANYWAY: ANYWAY_MOVE}
PANEL_ACTIONS = tuple(f"inbox_{one}" for one in ACTIONS)

LINK = "change_link"
POST_NOW = "inbox_now"
LINK_MOVE = MarathonMove(LINK, "Change the schedule link…", "primary", 2)
POST_NOW_MOVE = MarathonMove(POST_NOW, "Post it to the inbox now", row=2)
LINK_TITLE = "Change the schedule link"
LINK_LABEL = "The new schedule link"
LINK_HINT = "https://oengus.io/marathon/…"
SCHEDULE_LINE = "**Schedule:** {url}"
INBOX_UP = "**Inbox message:** [posted]({url})"
INBOX_WAITING = (
    "**Inbox message:** not posted yet — it posts on the first read that finds runs. **Post it "
    "to the inbox now** posts it early; its Schedule line says it is not out yet until then."
)
INBOX_NOT_HERE = "**Inbox message:** not posted yet."

FEED_AUTO_ON = "feed_auto_on"
FEED_AUTO_OFF = "feed_auto_off"
FEED_AUTO_ON_MOVE = MarathonMove(FEED_AUTO_ON, "Auto-track on", row=2)
FEED_AUTO_OFF_MOVE = MarathonMove(FEED_AUTO_OFF, "Auto-track off", row=2)
FEED_AUTO_LINE = "Auto-track: {state}"
FEED_AUTO_WORDS = {
    True: "on — each marathon it adds is tracked when its schedule is out",
    False: "off — staff press Track",
}
FEED_AUTO_SET = "**{name}** auto-track is {state}."
BAD_AUTO_TRACK = "Say true or false for auto-track, so nothing was changed."
BAD_ON = "Say true or false, so nothing was changed."


def _cell(row: Any, key: str, fallback: Any = None) -> Any:
    if row is None:
        return fallback
    try:
        return row[key]
    except (IndexError, KeyError):
        return fallback


def is_ignored(row: Any) -> bool:
    return bool(_cell(row, "ignored_at"))


def is_tracked(row: Any) -> bool:
    return bool(_cell(row, "tracked_at")) and not is_ignored(row)


def state_of(row: Any, *, archived: bool = False) -> str:
    if archived or _cell(row, "archived_at"):
        return ARCHIVED
    if is_ignored(row):
        return IGNORED
    return TRACKED if is_tracked(row) else FOUND


def moves_of(row: Any, *, archived: bool = False) -> tuple[str, ...]:
    return MOVES_BY_STATE[state_of(row, archived=archived)]


def panel_moves(row: Any) -> tuple[MarathonMove, ...]:
    return tuple(MOVE_OF[one] for one in moves_of(row))


def has_message(row: Any) -> bool:
    return bool(_cell(row, "inbox_message_id"))


def schedule_moves(row: Any) -> tuple[MarathonMove, ...]:
    """The Schedule view: the link, the read gap, and the early post while no message is up."""
    return (LINK_MOVE, POLL_MOVE._replace(row=2), BACK_MOVE)


def custom_id(marathon_id: Any, action: str) -> str:
    return f"marathon:inbox:{int(marathon_id)}:{action}"


def home_of(mode: str) -> str | None:
    if mode == "off":
        return None
    return HOME_ON if mode == "on" else HOME_SHADOW


def channel_url(guild_id: Any, channel_id: Any) -> str | None:
    if not guild_id or not channel_id:
        return None
    return CHANNEL_URL.format(guild=int(guild_id), channel=int(channel_id))


def message_url(guild_id: Any, channel_id: Any, message_id: Any) -> str | None:
    if not guild_id or not channel_id or not message_id:
        return None
    return MESSAGE_URL.format(guild=int(guild_id), channel=int(channel_id), message=int(message_id))


def when_of(value: Any) -> str:
    at = parse_ts(value)
    return WHEN.format(at=int(at.timestamp())) if at is not None else ""


def date_of(value: Any) -> str:
    at = parse_ts(value)
    return at.strftime("%d %b %Y") if at is not None else ""


def thread_name(text: Any) -> str:
    cleaned = " ".join(str(text or "").split())
    return cleaned[:THREAD_NAME_LIMIT] or THREAD_NAME_FALLBACK


def ignored_read_due(row: Any, now: datetime, far_hours: int) -> bool:
    """An ignored marathon is read on the far cadence only, so its dates stay right."""
    if not bool(_cell(row, "active", 1)):
        return False
    last = parse_ts(_cell(row, "last_fetched_at"))
    return last is None or now >= last + timedelta(hours=int(far_hours))


def comparable(content: Any, embeds: Any) -> tuple[Any, ...]:
    """What an inbox message shows, in a shape a posted message and a fresh render share."""
    first = list(embeds or [None])[0]
    fields = tuple(
        (str(getattr(one, "name", "")), str(getattr(one, "value", "")))
        for one in (getattr(first, "fields", None) or ())
    )
    return (str(content or ""), str(getattr(first, "title", "") or ""), fields)


__all__ = [
    "ACTIONS",
    "ANYWAY",
    "ARCHIVED",
    "FOUND",
    "HOME_ON",
    "HOME_SHADOW",
    "IGNORE",
    "IGNORED",
    "INBOX_TEMPLATE",
    "STATES",
    "TRACK",
    "TRACKED",
    "UNTRACK",
    "custom_id",
    "home_of",
    "ignored_read_due",
    "is_ignored",
    "is_tracked",
    "moves_of",
    "state_of",
    "thread_name",
]
