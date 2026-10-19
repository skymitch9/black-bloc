from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone
from typing import Any

import discord

from .settings_store import (
    DEFAULT_TIMEZONE_KEY,
    QUESTION_CATCHUP,
    QUESTION_CHANNEL,
    QUESTION_CLOCK,
    QUESTION_GRACE,
    QUESTION_MODE,
    QUESTION_OWNER,
    QUESTION_TEMPLATE,
    QUESTION_TEMPLATE_DEFAULT,
    QUESTION_THREAD,
    QUESTION_THREAD_NAME,
    QUESTION_TIME,
    QUESTION_TIME_DEFAULT,
    QUESTION_WARN_DAYS,
    QUESTION_WARN_DM,
    QUESTION_WARN_TEMPLATE,
    QUESTION_WARN_TEMPLATE_DEFAULT,
    QUESTION_WEEKDAY,
    QUESTION_WEEKDAYS,
)
from .timezones import DEFAULT_TZ
from .timezones import zone as zone_named

log = logging.getLogger(__name__)

FEATURE = "question"
PANEL_MINUTES_KEY = "posts_panel_minutes"
OFF = "off"
SHADOW = "shadow"
ON = "on"

QUEUED = "queued"
POSTED = "posted"
SKIPPED = "skipped"
REMOVED = "removed"

PENDING = "pending"
SKIPPED_EMPTY = "skipped_empty"
MISSED = "missed"
TAKEN_DOWN = "taken_down"
OPEN_SLOT = (PENDING, SKIPPED, SKIPPED_EMPTY, TAKEN_DOWN)

BY_OWNER = "owner"
BY_BOT = "bot"

LOOKBACK = timedelta(minutes=15)
OWNER_SCAN_LIMIT = 100
MESSAGE_LIMIT = 2000
BODY_LIMIT = 1500
THREAD_NAME_LIMIT = 100
THREAD_FALLBACK = "Question of the week"
FALLBACK_ZONE = timezone(timedelta(hours=-7), DEFAULT_TZ)
USER_CONTENT = (discord.MessageType.default, discord.MessageType.reply)

EMPHASIS = re.compile(r"[*_~`|>]")
SPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Schedule:
    weekday: int
    hour: int
    minute: int
    tz: Any
    grace: timedelta
    catchup: timedelta


def zone_of(name: Any) -> Any:
    return zone_named(name) or zone_named(DEFAULT_TZ) or FALLBACK_ZONE


def weekday_index(name: Any) -> int:
    text = str(name or "").strip().lower()
    return QUESTION_WEEKDAYS.index(text) if text in QUESTION_WEEKDAYS else 0


def clock_of(text: Any) -> tuple[int, int]:
    match = QUESTION_CLOCK.match(str(text or "").strip()) or QUESTION_CLOCK.match(
        QUESTION_TIME_DEFAULT
    )
    return int(match.group(1)), int(match.group(2))


def schedule_of(store: Any, guild_id: int) -> Schedule:
    hour, minute = clock_of(store.get(guild_id, QUESTION_TIME))
    return Schedule(
        weekday=weekday_index(store.get(guild_id, QUESTION_WEEKDAY)),
        hour=hour,
        minute=minute,
        tz=zone_of(store.get(guild_id, DEFAULT_TIMEZONE_KEY)),
        grace=timedelta(minutes=int(store.get(guild_id, QUESTION_GRACE))),
        catchup=timedelta(hours=int(store.get(guild_id, QUESTION_CATCHUP))),
    )


def slot_on(day: date, schedule: Schedule) -> datetime:
    local = datetime.combine(day, time(schedule.hour, schedule.minute), tzinfo=schedule.tz)
    return local.astimezone(UTC)


def slots_around(now: datetime, schedule: Schedule) -> tuple[datetime, datetime]:
    """The latest slot at or before `now`, and the first one after it."""
    today = now.astimezone(schedule.tz).date()
    found = sorted(
        slot_on(today + timedelta(days=offset), schedule)
        for offset in range(-8, 9)
        if (today + timedelta(days=offset)).weekday() == schedule.weekday
    )
    last = max(one for one in found if one <= now)
    following = min(one for one in found if one > now)
    return last, following


def slot_key(when: datetime) -> str:
    return when.astimezone(UTC).isoformat(timespec="seconds")


def slot_from(text: Any) -> datetime | None:
    try:
        found = datetime.fromisoformat(str(text))
    except (TypeError, ValueError):
        return None
    return found if found.tzinfo else found.replace(tzinfo=UTC)


def normalised(text: Any) -> str:
    return SPACE.sub(" ", EMPHASIS.sub("", str(text or "")).casefold()).strip()


def says_question(content: Any, body: Any) -> bool:
    wanted = normalised(body)
    return bool(wanted) and wanted in normalised(content)


def owner_post(messages: Any, owner_id: Any, body: Any, since: datetime) -> Any:
    """The first of the owner's own messages since `since` that carries the question."""
    try:
        owner = int(owner_id)
    except (TypeError, ValueError):
        return None
    for message in messages or ():
        if getattr(message, "type", discord.MessageType.default) not in USER_CONTENT:
            continue
        if getattr(getattr(message, "author", None), "id", None) != owner:
            continue
        created = getattr(message, "created_at", None)
        if created is not None and created < since:
            continue
        if says_question(getattr(message, "content", ""), body):
            return message
    return None


def filled(template: Any, fallback: str, **values: Any) -> str:
    try:
        return str(template).format(**values)
    except Exception as exc:
        log.warning(
            "questions: %r would not fill (%s); the shipped wording was used", template, exc
        )
        return fallback.format(**values)


def rendered(store: Any, guild_id: int, body: Any) -> str:
    text = filled(
        store.get(guild_id, QUESTION_TEMPLATE) or QUESTION_TEMPLATE_DEFAULT,
        QUESTION_TEMPLATE_DEFAULT,
        question=str(body or ""),
    )
    return text[:MESSAGE_LIMIT]


def thread_name(store: Any, guild_id: int, body: Any) -> str:
    text = filled(
        store.get(guild_id, QUESTION_THREAD_NAME) or QUESTION_TEMPLATE_DEFAULT,
        QUESTION_TEMPLATE_DEFAULT,
        question=SPACE.sub(" ", str(body or "")).strip(),
    )
    return text.strip()[:THREAD_NAME_LIMIT] or THREAD_FALLBACK


def day_word(when: datetime, schedule: Schedule) -> str:
    return when.astimezone(schedule.tz).strftime("%A")


def time_word(when: datetime, schedule: Schedule) -> str:
    return when.astimezone(schedule.tz).strftime("%H:%M")


def warn_text(store: Any, guild_id: int, when: datetime, schedule: Schedule) -> str:
    text = filled(
        store.get(guild_id, QUESTION_WARN_TEMPLATE) or QUESTION_WARN_TEMPLATE_DEFAULT,
        QUESTION_WARN_TEMPLATE_DEFAULT,
        day=day_word(when, schedule),
        time=time_word(when, schedule),
    )
    return text[:MESSAGE_LIMIT]


def split_lines(text: Any) -> list[str]:
    return [line.strip()[:BODY_LIMIT] for line in str(text or "").splitlines() if line.strip()]


def mode_of(store: Any, guild_id: int) -> str:
    found = str(store.get(guild_id, QUESTION_MODE) or OFF)
    return found if found in (OFF, SHADOW, ON) else OFF


def owner_of(store: Any, guild_id: int) -> int | None:
    text = str(store.get(guild_id, QUESTION_OWNER) or "").strip()
    return int(text) if text.isdigit() else None


def threads_on(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, QUESTION_THREAD))


def warn_days(store: Any, guild_id: int) -> int:
    return int(store.get(guild_id, QUESTION_WARN_DAYS))


def warn_dm(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, QUESTION_WARN_DM))


def real_channel(store: Any, guild_id: int) -> int | None:
    found = store.get(guild_id, QUESTION_CHANNEL)
    return int(found) if found else None


def panel_minutes(store: Any, guild_id: int) -> int:
    return int(store.get(guild_id, PANEL_MINUTES_KEY))


def channel_url(guild_id: Any, channel_id: Any) -> str | None:
    if not guild_id or not channel_id:
        return None
    return f"https://discord.com/channels/{int(guild_id)}/{int(channel_id)}"


def stamp(when: datetime, style: str = "F") -> str:
    return f"<t:{int(when.timestamp())}:{style}>"


def current_slot(now: datetime, schedule: Schedule, last_row: Any) -> datetime:
    """This week's slot: the last one while it is still open, otherwise the next one."""
    last, following = slots_around(now, schedule)
    if (
        last_row is not None
        and now < last + schedule.catchup
        and str(last_row["status"]) in OPEN_SLOT
    ):
        return last
    return following


PANEL_TITLE = "Weekly questions"
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /questions again"
NEXT_LINE = "**Next** — {when} ({relative})"
STATE_LINE = "**This week** — {state}"
QUESTION_LINE = "**Question** — {body}"
NO_QUESTION_LINE = "**Question** — the queue is empty"
QUEUED_LINE = "**Queued** — {count}"
MODE_LINE = "**Mode** — {mode}"
WHERE_LINE = "**Goes to** — {where}"
OWNER_LINE = "**Posted by** — <@{owner}>, Black Bloc after {grace} min"
NO_OWNER_LINE = "**Posted by** — Black Bloc (question_owner_user_id is not set)"
LAST_LINE = "**Last** — {body} · {by} · {when}"
STATE_WORDS = {
    PENDING: "waiting",
    POSTED: "posted",
    SKIPPED: "skipped",
    SKIPPED_EMPTY: "skipped — the queue was empty",
    MISSED: "missed",
    TAKEN_DOWN: "taken down",
}
BY_WORDS = {BY_OWNER: "by the owner", BY_BOT: "by Black Bloc"}

ADD_LABEL = "Add"
QUEUE_PLACEHOLDER = "Queue…"
POST_NOW_LABEL = "Post now"
SKIP_LABEL = "Skip this week"
UNSKIP_LABEL = "Undo skip"
TAKE_DOWN_LABEL = "Take it down"
REFRESH_LABEL = "Refresh"
EDIT_LABEL = "Edit"
REMOVE_LABEL = "Remove"
UP_LABEL = "Up"
DOWN_LABEL = "Down"
BACK_LABEL = "Back"
ADD_TITLE = "Add questions"
ADD_FIELD = "One question per line"
ADD_PLACEHOLDER = "What game got you into speedrunning?"
EDIT_TITLE = "Edit the question"
EDIT_FIELD = "Question"
CARD_TITLE = "Queued question #{place}"
REMOVE_CONFIRM = "Remove this question from the queue?"
POST_CONFIRM = "Post **{body}** now?"
TAKE_DOWN_CONFIRM = (
    "Delete Black Bloc's post of **{body}** and put it back at the top of the queue?"
)

ADDED = "{n} question(s) added to the queue."
NOTHING_TO_ADD = "There was no question in that, so nothing was added. Write one per line."
EDITED = "The question is changed."
REMOVED_SAID = "The question is out of the queue. Put it back from the history on the site."
MOVED = "The question moved {direction}."
NOT_MOVED = "The question is already at the {end} of the queue, so nothing moved."
REQUEUED = "The question is back at the end of the queue."
POSTED_NOW = "The question is up in {where}."
SKIPPED_SAID = "This week is skipped. The next question stays at the top of the queue."
UNSKIPPED = "This week is back on."
TAKEN_DOWN_SAID = "Black Bloc's post is deleted and the question is back at the top of the queue."
NO_SUCH = (
    "That question is not in the queue any more, so nothing changed. Refresh to see the queue."
)
NOT_QUEUED = (
    "That question is {status}, not queued, so it cannot be changed. Refresh to see the queue."
)
NOT_REMOVED = "Only a removed question can be put back, and that one is {status}."
QUESTIONS_OFF = (
    "Weekly questions are off, so nothing was posted. Set question_mode to shadow or on in "
    "Settings first."
)
QUEUE_EMPTY = "The queue is empty, so there is nothing to post. Add a question first."
ALREADY_UP = (
    "This week's question is already up, so nothing was posted. Take it down first to post another."
)
NOT_SKIPPABLE = "This week's question is already {state}, so there is nothing to skip."
NOT_SKIPPED = "This week is not skipped, so there is nothing to undo."
NOT_BOTS = (
    "Only a question Black Bloc posted can be taken down. The owner's own post is never "
    "deleted by the bot."
)
NOT_POSTED = "That question is {status}, not posted, so there is nothing to take down."
NO_CHANNEL = (
    "There is nowhere to post it: question_channel_id is not set. Pick the channel in "
    "Settings first."
)
NO_REHEARSAL = (
    "There is nowhere to rehearse it: no rehearsal home is set. Pick question_shadow_channel_id "
    "or shadow_channel_id in Settings first."
)
CHANNEL_GONE = (
    "Black Bloc cannot see channel {channel}, so nothing was posted. Check the channel in Settings."
)
POST_REFUSED = "Discord refused the post ({why}), so nothing was posted."
TEST_MODE_REFUSED = "Test mode keeps Black Bloc out of channel {channel}, so nothing was posted."
DELETE_REFUSED = "Discord refused to delete the post ({why}), so nothing changed."
