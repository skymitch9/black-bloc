"""Twitch channels watched by name, with no Discord member behind them."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from .golive import (
    GAME_FALLBACK,
    TWITCH,
    YOUTUBE,
    StreamInfo,
    _Fields,
    humanise_duration,
    now_iso,
    parse_ts,
    tidy,
    twitch_login_from_url,
)
from .settings_store import (
    CHANNEL_OPTOUT_DELETE,
    CHANNEL_OPTOUT_END,
    CHANNEL_OPTOUT_LEAVE,
    SPOTLIGHT_BAD_DATE,
    SPOTLIGHT_BUMP_TEMPLATE,
    SPOTLIGHT_DATES_BUTTON,
    SPOTLIGHT_END_BEFORE_START,
    SPOTLIGHT_ENDS_LABEL,
    SPOTLIGHT_RANGE,
    SPOTLIGHT_RANGE_KEPT,
    SPOTLIGHT_SCHEDULED_WORD,
    SPOTLIGHT_STARTS_LABEL,
)
from .timezones import DEFAULT_TZ, zone

log = logging.getLogger(__name__)

LOGIN_MAX = 25
PLATFORM = TWITCH
CHANNEL_URL = "https://www.twitch.tv/{login}"
YOUTUBE_URL = "https://www.youtube.com/channel/{channel_id}"
PIN_REASON = "Black Bloc keeps this spotlight pinned while it streams"
UNPIN_REASON = "Black Bloc unpinned this spotlight — the stream is over"
KEPT = "kept"
UNTIL = "until {when}"
LABEL_MAX = 45
BAD_DATE = "bad_date"
END_BEFORE_START = "end_before_start"
DATE_ONLY = "%Y-%m-%d"
DATE_AND_TIME = "%Y-%m-%d %H:%M"
STARTS_PLACEHOLDER = "2026-09-30 19:00"
ENDS_PLACEHOLDER = "2026-10-07 23:00, or 7"
SCHEDULED_CELL = "spotlight · {when} · {word}"
PANEL_SCHEDULED = " · **{word}**"
DATES_MODAL_TITLE = "A spotlight’s dates"
DATES_SAID = "**{login}** runs {when}."
SCHEDULED_SAID = (
    "**{login}** runs {when}. Nothing of its is announced, pinned or reminded before "
    "that start — the row sits on the list until then."
)
ANNOUNCED_CELL = "spotlight · {when}"
CHANNEL_ONLY = "channel only"

BAD_LOGIN = (
    "**{given}** is not a Twitch channel name, so nothing was spotlighted. Use the name from "
    "the channel address — the part after twitch.tv/ — for example `gamesdonequick`."
)
ALREADY_SPOTLIT = (
    "**{login}** is already on the spotlight list, so nothing was added. **Extend** on its own "
    "row moves the date it runs out instead — that is the move you want if this is a new "
    "marathon on the same channel."
)
ALREADY_SPOTLIT_EVENT = (
    "**{login}** is already on the spotlight list, so nothing was added. Extend it to this "
    "event's end instead — its row on the Go-live page has the move."
)
NO_SUCH_ROW = (
    "That spotlight row is not there any more, so nothing was changed. It may have run out, or "
    "somebody else may have removed it — the Go-live page's Streamers list shows what is left."
)
NO_KEY = (
    "Twitch credentials are not set (TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET), so nothing is "
    "being watched and no spotlight can be announced. The list below is still kept — it starts "
    "working the moment a Lead sets them."
)
MODE_OFF = (
    "Spotlight is **off**, so nothing on this list is watched or announced. The list is kept "
    "as it is — turning it back on picks up where it left off."
)
MODE_SHADOW = (
    "Spotlight is in **shadow**, so announcements, reminders and pins are rehearsed where "
    "shadow_channel_id points and nothing reaches the go-live channel."
)
NO_CHANNEL = (
    "There is nowhere to announce a spotlight: golive_channel_id is not set. Nothing was "
    "posted, and the row is still on the list."
)
PIN_REFUSED = (
    "**{login}**'s announcement was posted but could not be pinned ({reason}). Black Bloc "
    "needs **Manage Messages** in that channel, and a channel can hold 50 pins. Nothing else "
    "about the spotlight changed."
)
UNPIN_REFUSED = (
    "**{login}**'s announcement could not be unpinned ({reason}), so it is still pinned in the "
    "go-live channel. Taking the pin off by hand is safe — nothing else is waiting on it."
)
ADDED = (
    "**{login}** is on the spotlight list, {when}. Black Bloc announces it in the go-live "
    "channel whenever it goes live, reminds people every {hours} hours while it runs, and "
    "{pin}."
)
ADDED_PIN = "pins the announcement for the duration"
ADDED_NO_PIN = "leaves the announcement unpinned"
ADDED_PLAIN = (
    "**{login}** is on the list, {when}. Black Bloc announces it in the go-live channel "
    "whenever it goes live, exactly as it announces anybody else's stream, and edits the post "
    "to past tense when it ends. **Spotlight on** adds the pin and the reminders."
)
REMOVED = (
    "**{login}** is off the spotlight list. Any announcement it has out there is left as "
    "posted; nothing else was changed."
)
EXTENDED = "**{login}** now runs {when}."
KEPT_SAID = "**{login}** is kept for ever now, so no purge will take it off the list."
EXPIRES_SAID = "**{login}** runs out {when} and will be purged then."
PINNED_SAID = "**{login}**'s announcements will be pinned while it streams."
UNPINNED_SAID = "**{login}**'s announcements will not be pinned."
BUMPED_SAID = "Reminded the go-live channel that **{login}** is still live."
NOT_LIVE = (
    "**{login}** is not live right now, so there was nothing to remind anybody about. The "
    "reminder is offered again the moment Black Bloc sees it go live."
)
NO_COG = (
    "Black Bloc's spotlight half is not running right now, so no reminder could be posted. "
    "Nothing about **{login}** changed, and the next reminder is still due on time — tell a "
    "Lead if the bot has not finished starting up."
)
BUMP_FAILED = (
    "**{login}** is live, but the reminder could not be posted ({reason}). Nothing about the "
    "spotlight changed and the next one is still due on time."
)

PANEL_TITLE = "Spotlight"
PANEL_INTRO = (
    "Twitch channels watched by name, for org channels and marathons that have nobody in this "
    "server behind them. Adding one is staff-only."
)
PANEL_EMPTY = "No channel is spotlighted yet."
PANEL_ROW = "**{login}** — {when}{spot}{youtube}{live}{note}"
PANEL_LIVE = " · **live now**"
PANEL_NOTE = " · {note}"
PANEL_SPOTLIT = " · spotlit"
PANEL_YOUTUBE = " · {said}"
ADD_BUTTON = "Add a channel…"
ADD_MODAL_TITLE = "Spotlight a Twitch channel"
ADD_LOGIN_LABEL = "The name after twitch.tv/"
ADD_LOGIN_PLACEHOLDER = "gamesdonequick"
ADD_DAYS_LABEL = "Days to keep it — blank means for ever"
ADD_DAYS_PLACEHOLDER = "7"
BAD_DAYS = (
    "**{given}** is not a number of days, so nothing was added. Write a whole number of days, "
    "or leave it blank to keep the channel on the list for ever."
)
PICK_A_CHANNEL = "A spotlighted channel…"
ROW_MOVE = "What to do with {login}…"
EXTEND_WEEK = "Extend a week"
KEEP_FOREVER = "Keep for ever"
BUMP_NOW = "Bump now"
REMOVE = "Remove"
SPOTLIGHT_BUTTON = "Channels…"
EVENT_SPOTLIGHT_LABEL = "Spotlight this stream"
EVENT_NOT_TWITCH = (
    "This event's **Where** is not a twitch.tv address, so there is no channel to spotlight. "
    "Change the Where to the channel's own address and the move appears."
)
EVENT_SPOTLIT = (
    "**{login}** is spotlighted until {when} — the go-live channel announces it, reminds "
    "people while it runs, and pins it for the duration."
)
EVENT_CANCELLED_BECAUSE = "event_cancelled"
SPOTLIT_UNTIL = "Spotlighted until {when}."

GIVE_PING_ROLE = "Give it a ping role"
TAKE_PING_ROLE = "Remove its ping role"
PING_ROLE_LINE = " · <@&{role_id}>"

SPOTLIGHT_ON = "Spotlight on"
SPOTLIGHT_OFF = "Spotlight off"
SPOTLIT_SAID = (
    "**{login}** is spotlighted: its announcement is pinned while it streams and a reminder "
    "goes out every so often. Everything else about the channel stays as it is."
)
NOT_SPOTLIT_SAID = (
    "**{login}** is announced like anybody else's stream now — one post when it goes live, "
    "edited to past tense when it ends, no pin and no reminders. It stays on the list."
)
SPOTLIT_STATE = "Spotlighted — pinned while it streams, reminded every {hours} h."
NOT_SPOTLIT_STATE = "Announced like any other stream — no pin, no reminders."
CHANNEL_ONLY_NOTE = "A channel Black Bloc watches by name. Nobody here is behind it."

NEEDS_A_TWITCH_NAME = (
    "**{given}** is a YouTube channel, and a channel row still needs a Twitch name to hang "
    "on, so nothing was added. Add the channel by its Twitch name first, then **Link a "
    "YouTube channel** on its own row puts the YouTube side on it."
)
NO_YOUTUBE_GIVEN = (
    "No YouTube channel was given, so nothing was linked. Paste the address that starts with "
    "youtube.com/channel/UC…, or the @handle."
)
YOUTUBE_LINKED = (
    "**{login}** is linked to {title}. Black Bloc watches that YouTube channel for live "
    "streams as well as its Twitch one."
)
YOUTUBE_UNLINKED = (
    "**{login}**'s YouTube channel is unlinked, so only its Twitch side is watched now. "
    "Nothing else about the channel changed."
)
NO_YOUTUBE_LINKED = (
    "**{login}** has no YouTube channel linked, so there was nothing to unlink. Its row on "
    "the Go-live page has the move that links one."
)
NO_YOUTUBE_COG = (
    "Black Bloc's YouTube half is not running right now, so the channel could not be looked "
    "up and nothing was linked. Nothing about **{login}** changed."
)
REMOVE_CHANNEL_ASK = (
    "Removes {name} from the list, its spotlight, its YouTube link and its ping role (per "
    "pings_fan_role_delete). Nothing in Discord is deleted except the role if that setting "
    "says so."
)
CHANNEL_REMOVED = (
    "**{login}** is off the list. Any announcement it has out there is left as posted; "
    "nothing else was changed."
)

OPT_OUT = "Opt out of announcements"
OPT_IN = "Opt back in"
OPTED_OUT_SAID = (
    "**{login}** is opted out, so nothing of its is announced from now on — no post, no pin "
    "and no reminders, whatever its spotlight says. It stays on the list, it keeps its ping "
    "role and it keeps its YouTube link, and **Opt back in** starts it announcing again."
)
OPTED_IN_SAID = (
    "**{login}** is opted back in, so the next stream it starts is announced again. Nothing "
    "that happened while it was opted out is posted after the fact."
)
OPTED_OUT_STATE = "Opted out — nothing of its is announced, whatever the spotlight says."
OPTED_OUT_CELL = "opted out"
OPTED_OUT_POST_SAID = {
    CHANNEL_OPTOUT_END: (
        "The announcement that was out has been unpinned and edited to say the stream has "
        "ended, exactly as any stream end does, and the session is closed (per "
        "`golive_channel_optout_post`)."
    ),
    CHANNEL_OPTOUT_DELETE: (
        "The announcement that was out has been deleted and the session is closed (per "
        "`golive_channel_optout_post`)."
    ),
    CHANNEL_OPTOUT_LEAVE: (
        "The announcement that was out is left exactly as it was posted — only the pin came "
        "off — and the session is closed (per `golive_channel_optout_post`)."
    ),
}
UNPINNED = "unpinned"
UNPINNED_NOW = (
    "The announcement that is out now has been unpinned; it stays posted, no reminder follows "
    "it, and it is edited to past tense when the stream ends."
)
PINNED = "pinned"
PINNED_NOW = (
    "The announcement that is out now has been pinned for the rest of the stream, and the "
    "reminders pick up from here."
)
UNPINNED_ENDED = "unpinned_ended"
UNPINNED_ENDED_NOW = (
    "Its last announcement, from a stream that has already ended, was still pinned and has "
    "been unpinned; the next one is pinned when it goes live."
)
SPOTLIT_SETTLED = {PINNED: PINNED_NOW, UNPINNED_ENDED: UNPINNED_ENDED_NOW}

LINK_YOUTUBE = "Link a YouTube channel"
UNLINK_YOUTUBE = "Unlink it"
REMOVE_CHANNEL = "Remove this channel"
CHANNELS_BUTTON = "Channels…"
CHANNELS_TITLE = "Channels"
CHANNELS_INTRO = (
    "Twitch channels watched by name, for org channels and marathons that have nobody in this "
    "server behind them. Each one is announced like any other stream; **Spotlight on** adds "
    "the pin and the reminders. Adding one is staff-only."
)
ADD_CHANNEL_MODAL_TITLE = "Add a channel"
ADD_YOUTUBE_LABEL = "Its YouTube channel — blank for none"
ADD_YOUTUBE_PLACEHOLDER = "@GamesDoneQuick"
ADD_SPOTLIGHT_LABEL = "Spotlight it? yes or no"
ADD_SPOTLIGHT_PLACEHOLDER = "no"
BAD_SPOTLIGHT_ANSWER = (
    "**{given}** is not a yes or a no, so nothing was added. Write `yes` to pin and remind "
    "while it streams, `no` to announce it like any other stream, or leave it blank."
)
YES_WORDS = ("y", "yes", "on", "true", "1")
NO_WORDS = ("n", "no", "off", "false", "0")

RECONCILED = "reconciled_on_start"
ENDED = "ended"
EXPIRED = "expired"
REMOVED_BECAUSE = "removed"
OPTED_OUT_ENDED = "opted_out"
SPOTLIGHT_OFF_BECAUSE = "spotlight_off"
SPOTLIGHT_ON_BECAUSE = "spotlight_on"
FAN_ROLE_EXPIRED = "spotlight_expired"
FAN_ROLE_REMOVED = "spotlight_removed"
FAN_ROLE_TAKEN = "staff_removed"


@dataclass(frozen=True)
class Bump:
    """When the next reminder is due, and whether it is due now."""

    due_at: datetime | None
    due: bool


def _cell(row: Any, key: str) -> Any:
    if row is None:
        return None
    try:
        return row[key]
    except (IndexError, KeyError, TypeError):
        return getattr(row, key, None)


def clean_login(raw: Any) -> str | None:
    """A Twitch channel name out of a name, an @handle or a whole channel address."""
    login = twitch_login_from_url(raw) or str(raw or "").strip().lower().lstrip("@")
    if not login or len(login) > LOGIN_MAX:
        return None
    if not all(ch.isalnum() or ch == "_" for ch in login):
        return None
    return login


def login_from_url(url: Any) -> str | None:
    """The channel name an event's Where points at, or None when it is not a Twitch link."""
    found = twitch_login_from_url(url)
    return clean_login(found) if found else None


def channel_url(login: Any) -> str:
    return CHANNEL_URL.format(login=str(login or ""))


def youtube_url(channel_id: Any) -> str | None:
    wanted = str(channel_id or "").strip()
    return YOUTUBE_URL.format(channel_id=wanted) if wanted else None


def display_for(row: Any) -> str:
    return str(_cell(row, "display_name") or _cell(row, "twitch_login") or "")


def announces(row: Any) -> bool:
    """A row with no `announce` cell is one the migration has not reached: announced."""
    found = _cell(row, "announce")
    return True if found is None else bool(found)


def is_spotlit(row: Any) -> bool:
    """A row with no `spotlight` cell is one the migration has not reached: spotlighted."""
    found = _cell(row, "spotlight")
    return True if found is None else bool(found)


def youtube_of(row: Any) -> str | None:
    return str(_cell(row, "youtube_channel_id") or "").strip() or None


def youtube_said(row: Any) -> str | None:
    """What a channel's YouTube side is called: its handle where there is one, else its id."""
    handle = str(_cell(row, "youtube_handle") or "").strip()
    return handle or youtube_of(row)


def wanted_spotlight(given: Any, fallback: bool) -> bool | None:
    """`None` is the refusal: a word that is neither a yes nor a no, never a silent default."""
    word = str(given or "").strip().lower()
    if not word:
        return fallback
    if word in YES_WORDS:
        return True
    if word in NO_WORDS:
        return False
    return None


def spotlight_state(row: Any, hours: Any) -> str:
    if not announces(row):
        return OPTED_OUT_STATE
    if not is_spotlit(row):
        return NOT_SPOTLIT_STATE
    return SPOTLIT_STATE.format(hours=hours)


def spotlight_said(row: Any, settled: Any = None) -> str:
    """One sentence for both doors; `settled` is what the open announcement had done to it."""
    login = _cell(row, "twitch_login")
    if is_spotlit(row):
        said = SPOTLIT_SAID.format(login=login)
        clause = SPOTLIT_SETTLED.get(str(settled or ""), _refusal(settled))
        return f"{said} {clause}" if clause else said
    said = NOT_SPOTLIT_SAID.format(login=login)
    return f"{said} {UNPINNED_NOW}" if settled == UNPINNED else said


def _refusal(settled: Any) -> str:
    known = {UNPINNED, *OPTED_OUT_POST_SAID}
    return "" if not settled or settled in known else str(settled)


def announce_said(row: Any, settled: Any = None) -> str:
    """One sentence for both doors; the clause lands only when a session was open."""
    login = _cell(row, "twitch_login")
    if announces(row):
        return OPTED_IN_SAID.format(login=login)
    said = OPTED_OUT_SAID.format(login=login)
    clause = OPTED_OUT_POST_SAID.get(str(settled or ""))
    return f"{said} {clause}" if clause else said


def keeps_forever(row: Any) -> bool:
    return not str(_cell(row, "expires_at") or "").strip()


def is_expired(row: Any, now: datetime | None = None) -> bool:
    """A kept row never expires; an unreadable date is treated as no date, never as due."""
    raw = _cell(row, "expires_at")
    if not str(raw or "").strip():
        return False
    when = parse_ts(raw)
    if when is None:
        log.warning("spotlight: expires_at %r is unreadable; the row is left on the list", raw)
        return False
    return (now or datetime.now(UTC)) >= when


def when_words(value: Any) -> str:
    when = parse_ts(value)
    if when is None:
        return ""
    return f"{when.day} {when.strftime('%b')}"


def until_words(row: Any) -> str:
    """`kept`, or `until 30 Sep` — the two halves the owner's two meanings of 'pin' became."""
    if keeps_forever(row):
        return KEPT
    said = when_words(_cell(row, "expires_at"))
    return UNTIL.format(when=said) if said else KEPT


def starts_at_of(row: Any) -> Any:
    return _cell(row, "starts_at")


def is_scheduled(row: Any, now: datetime | None = None) -> bool:
    """An unreadable start is treated as no start: the row is watched, never stranded."""
    raw = starts_at_of(row)
    if not str(raw or "").strip():
        return False
    when = parse_ts(raw)
    if when is None:
        log.warning("spotlight: starts_at %r is unreadable; the row is treated as started", raw)
        return False
    return (now or datetime.now(UTC)) < when


def range_words(row: Any, template: Any = None, kept_template: Any = None) -> str:
    """`from 25 Sep to 30 Sep`, `from 25 Sep · kept`, `until 30 Sep`, or `kept`."""
    started = when_words(starts_at_of(row))
    if not started:
        return until_words(row)
    if keeps_forever(row):
        wanted = str(kept_template or "").strip() or SPOTLIGHT_RANGE_KEPT
        return _filled(wanted, SPOTLIGHT_RANGE_KEPT, start=started, end="")
    wanted = str(template or "").strip() or SPOTLIGHT_RANGE
    return _filled(
        wanted, SPOTLIGHT_RANGE, start=started, end=when_words(_cell(row, "expires_at"))
    )


def _filled(wanted: str, fallback: str, **fields: Any) -> str:
    """Unreadable wording falls back to the shipped default rather than showing nothing."""
    try:
        return wanted.format(**fields)
    except Exception as exc:
        log.warning("spotlight: wording %r could not be rendered (%s); using the default",
                    wanted, exc)
        return fallback.format(**fields)


def scheduled_word(word: Any = None) -> str:
    return str(word or "").strip() or SPOTLIGHT_SCHEDULED_WORD


def announced_words(
    row: Any,
    now: datetime | None = None,
    template: Any = None,
    kept_template: Any = None,
    word: Any = None,
) -> str:
    said = range_words(row, template, kept_template)
    if not is_scheduled(row, now):
        return ANNOUNCED_CELL.format(when=said)
    return SCHEDULED_CELL.format(when=said, word=scheduled_word(word))


def typed_moment(value: Any, tz_name: Any = None) -> str:
    """What a stored instant looks like back in the box it was typed into."""
    when = parse_ts(value)
    if when is None:
        return ""
    zi = zone(tz_name) or zone(DEFAULT_TZ)
    return when.astimezone(zi).strftime(DATE_AND_TIME)


def read_moment(given: Any, tz_name: Any = None, now: datetime | None = None) -> tuple[Any, Any]:
    """`(iso, problem)` — a blank is `(None, None)`, which everywhere means now / for ever.

    A whole timestamp is taken as given; `YYYY-MM-DD HH:MM` and `YYYY-MM-DD` are read in the
    zone asked for. A start already gone by is ACCEPTED and stored as typed, never rewritten.
    """
    text = str(given or "").strip()
    if not text:
        return (None, None)
    zi = zone(tz_name) or zone(DEFAULT_TZ)
    for shape in (DATE_AND_TIME, DATE_ONLY):
        try:
            naive = datetime.strptime(text, shape)
        except ValueError:
            continue
        return (naive.replace(tzinfo=zi).astimezone(UTC).isoformat(), None)
    whole = parse_ts(text.replace(" ", "T")) if "T" in text or "+" in text else None
    if whole is not None:
        return (whole.astimezone(UTC).isoformat(), None)
    return (None, BAD_DATE)


def read_end(given: Any, tz_name: Any = None, now: datetime | None = None) -> tuple[Any, Any]:
    """The end box keeps the old `days` box working: a bare whole number is that many days."""
    text = str(given or "").strip()
    if text.isdigit():
        return (expiry_in_days(int(text), now), None)
    return read_moment(text, tz_name, now)


def range_problem(starts_at: Any, expires_at: Any) -> Any:
    """`END_BEFORE_START` or None. A kept row, or one with no start, can never be wrong."""
    start = parse_ts(starts_at)
    end = parse_ts(expires_at)
    if start is None or end is None:
        return None
    return END_BEFORE_START if end <= start else None


def bad_date_said(given: Any, template: Any = None) -> str:
    wanted = str(template or "").strip() or SPOTLIGHT_BAD_DATE
    return _filled(wanted, SPOTLIGHT_BAD_DATE, given=str(given or "")[:40])


def end_before_start_said(starts_at: Any, expires_at: Any, template: Any = None) -> str:
    wanted = str(template or "").strip() or SPOTLIGHT_END_BEFORE_START
    return _filled(
        wanted,
        SPOTLIGHT_END_BEFORE_START,
        start=when_words(starts_at) or str(starts_at or ""),
        end=when_words(expires_at) or str(expires_at or ""),
    )


def dates_said(row: Any, now: datetime | None = None, **wording: Any) -> str:
    said = range_words(row, wording.get("template"), wording.get("kept_template"))
    shape = SCHEDULED_SAID if is_scheduled(row, now) else DATES_SAID
    return shape.format(login=_cell(row, "twitch_login"), when=said)


def dates_button(label: Any = None) -> str:
    return str(label or "").strip() or SPOTLIGHT_DATES_BUTTON


def starts_label(label: Any = None) -> str:
    return (str(label or "").strip() or SPOTLIGHT_STARTS_LABEL)[:LABEL_MAX]


def ends_label(label: Any = None) -> str:
    return (str(label or "").strip() or SPOTLIGHT_ENDS_LABEL)[:LABEL_MAX]


def bump_hours_for(row: Any, default_hours: Any) -> int:
    own = _cell(row, "bump_hours")
    wanted = own if own else default_hours
    try:
        return max(1, int(wanted))
    except (TypeError, ValueError):
        return max(1, int(default_hours or 1))


def next_bump_at(
    started_at: Any, last_bump_at: Any, hours: int
) -> datetime | None:
    """Measured from the last reminder, and from the start until there has been one."""
    base = parse_ts(last_bump_at) or parse_ts(started_at)
    if base is None or hours <= 0:
        return None
    return base + timedelta(hours=hours)


def bump_due(session: Any, hours: int, now: datetime | None = None) -> Bump:
    """Never on the first look, never twice inside one interval, never after the end."""
    if str(_cell(session, "ended_at") or "").strip():
        return Bump(None, False)
    due_at = next_bump_at(
        _cell(session, "started_at"), _cell(session, "last_bump_at"), hours
    )
    if due_at is None:
        return Bump(None, False)
    return Bump(due_at, (now or datetime.now(UTC)) >= due_at)


def expiry_in_days(days: Any, now: datetime | None = None) -> str | None:
    """`None` days means keep it for ever, which is a NULL, not a far-off date."""
    if days is None or str(days).strip() == "":
        return None
    try:
        wanted = int(days)
    except (TypeError, ValueError):
        return None
    if wanted <= 0:
        return None
    return ((now or datetime.now(UTC)) + timedelta(days=wanted)).isoformat()


def expiry_for_event(ends_at: Any, slack_hours: Any) -> str | None:
    """An event's spotlight runs to its end plus the slack, so an overrun is still announced."""
    over = parse_ts(ends_at)
    if over is None:
        return None
    try:
        slack = max(0, int(slack_hours))
    except (TypeError, ValueError):
        slack = 0
    return (over + timedelta(hours=slack)).isoformat()


def extended_by_days(row: Any, days: int, now: datetime | None = None) -> str:
    """Extending a row that has run out counts from today, not from the date it missed."""
    at = now or datetime.now(UTC)
    when = parse_ts(_cell(row, "expires_at"))
    base = when if when is not None and when > at else at
    return (base + timedelta(days=days)).isoformat()


def platform_of(url: Any) -> str:
    """Which side opened a session, read off its own address — no column says it."""
    return YOUTUBE if "youtu" in str(url or "").lower() else TWITCH


def info_of(session: Any, login: Any) -> StreamInfo:
    """The StreamInfo a session stands for — never a member, and the side its url names."""
    url = _cell(session, "url") or channel_url(login)
    return StreamInfo(
        url=url,
        game=_cell(session, "game"),
        title=_cell(session, "title"),
        platform=platform_of(url),
    )


def bump_fields(info: StreamInfo, name: str, duration: str) -> _Fields:
    return _Fields(
        name=name,
        game=info.game or GAME_FALLBACK,
        title=info.title or "",
        url=info.url or "",
        duration=duration or "",
    )


def bump_duration(session: Any, at: Any = None) -> str:
    return humanise_duration(_cell(session, "started_at"), at or now_iso())


def bump_render(template: Any, info: StreamInfo, name: str, duration: str) -> str:
    """The reminder; unreadable wording falls back to the default rather than posting nothing."""
    fields = bump_fields(info, name, duration)
    wanted = str(template or "").strip() or SPOTLIGHT_BUMP_TEMPLATE
    try:
        return tidy(wanted.format_map(fields))
    except Exception as exc:
        log.warning(
            "spotlight: reminder wording %r could not be rendered (%s); using the default",
            template,
            exc,
        )
        return tidy(SPOTLIGHT_BUMP_TEMPLATE.format_map(fields))


def panel_line(
    row: Any, live: bool, role_id: Any = None, now: datetime | None = None, **wording: Any
) -> str:
    note = _cell(row, "note")
    said_youtube = youtube_said(row)
    ranged = range_words(row, wording.get("template"), wording.get("kept_template"))
    said = PANEL_ROW.format(
        login=_cell(row, "twitch_login"),
        when=ranged if is_spotlit(row) else "on the list",
        spot=PANEL_SPOTLIT if is_spotlit(row) else "",
        youtube=PANEL_YOUTUBE.format(said=said_youtube) if said_youtube else "",
        live=PANEL_LIVE if live else "",
        note=PANEL_NOTE.format(note=note) if note else "",
    )
    if is_scheduled(row, now):
        said += PANEL_SCHEDULED.format(word=scheduled_word(wording.get("word")))
    return said + (PING_ROLE_LINE.format(role_id=int(role_id)) if role_id else "")


def added_said(row: Any, hours: int, **wording: Any) -> str:
    ranged = range_words(row, wording.get("template"), wording.get("kept_template"))
    if not is_spotlit(row):
        return ADDED_PLAIN.format(login=_cell(row, "twitch_login"), when=ranged)
    return ADDED.format(
        login=_cell(row, "twitch_login"),
        when=ranged,
        hours=hours,
        pin=ADDED_PIN if _cell(row, "pin") else ADDED_NO_PIN,
    )


def reason_of(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"
