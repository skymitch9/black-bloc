from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, NamedTuple

import discord

from .actionlog import log_action
from .command_errors import NETWORK_ERRORS
from .golive import now_iso, parse_ts
from .linkcheck import LINK_MISSING, LINK_UNREACHABLE
from .logkinds import VIA_DISCORD, kind_via
from .panels import capped_placeholder
from .panels import panel_minutes as library_panel_minutes
from .panels import site_page_url as library_site_page_url
from .settings_store import (
    DEFAULT_TIMEZONE_KEY,
    EVENTS_LATE_CEILING_MINUTES,
    EVENTS_RETENTION_MAX_DAYS,
    EVENTS_RETENTION_MIN_DAYS,
    EVENTS_SCHEDULED_NAME_KEY,
    EVENTS_SCHEDULED_NAME_TEMPLATE,
    NAME_PLACEHOLDER,
    TIME_STEP_KEY,
    TIMEZONE_CHOICES_KEY,
    WHERE_ALIASES,
    WHERE_ALIASES_KEY,
    WHERE_CHECK_KEY,
    WHERE_CHECK_MODE,
    WHERE_CHECK_SECONDS,
    WHERE_CHECK_SECONDS_KEY,
    staff_roles_sentence,
    where_alias_table,
)
from .timezones import (
    AMBIGUOUS,
    DEFAULT_TZ,
    GAP,
    START_EXAMPLE,
    clock_trouble,
    is_known,
    local_time,
    parse_start,
    set_timezone,
    stamp,
    stored_timezone,
    suggest,
)
from .when_picker import WhenDraft, resolve, said_when

log = logging.getLogger(__name__)

TITLE_LIMIT = 100
DESCRIPTION_LIMIT = 1000
LOCATION_LIMIT = 100
EVENT_NAME_LIMIT = 100
CHANNEL_NAME_LIMIT = 100
BUTTON_LABEL_LIMIT = 80
DEFAULT_DURATION_MINUTES = 120
MAX_DURATION_MINUTES = 7 * 24 * 60

PENDING = "pending"
APPROVED = "approved"
DENIED = "denied"
LIVE = "live"
DONE = "done"
CANCELLED = "cancelled"
STATUSES = (PENDING, APPROVED, DENIED, LIVE, DONE, CANCELLED)
OPEN_STATUSES = (PENDING, APPROVED, LIVE)
SWEPT_STATUSES = (DONE, DENIED, CANCELLED)
DECIDED_STATUSES = (DENIED, CANCELLED)
SWEPT_ANCHORS = ("decided_at", "ends_at", "created_at")
SWEEP_KEPT_DAYS = "Black Bloc event {event_id}: kept {kept} day(s)"
SWEEP_KEPT_MINUTES = "Black Bloc event {event_id}: kept {kept} minute(s) while in test mode"
TRANSITIONS: dict[str, tuple[str, ...]] = {
    PENDING: (APPROVED, DENIED, CANCELLED),
    APPROVED: (LIVE, DONE, CANCELLED),
    LIVE: (DONE, CANCELLED),
    DENIED: (APPROVED,),
    DONE: (),
    CANCELLED: (),
}

TERMINAL_STATUSES = tuple(status for status, allowed in TRANSITIONS.items() if not allowed)

COLOURS: dict[str, int] = {
    PENDING: 0x5865F2,
    APPROVED: 0x57F287,
    DENIED: 0xED4245,
    LIVE: 0xFEE75C,
    DONE: 0x99AAB5,
    CANCELLED: 0x99AAB5,
}

DURATION_PATTERN = re.compile(r"^(?:(\d{1,4})h)?(?:(\d{1,5})m)?$")

ZONE_BUTTON = "My time zone"
BAD_START = (
    "**{given}** is not a date Black Bloc can read, so nothing was submitted. Write it as "
    "`YYYY-MM-DD HH:MM` on a 24-hour clock — `{example}` is half past seven in the evening on "
    f"the 14th — and it is read in **{{tz}}**, which **{ZONE_BUTTON}** on `/event` changes."
)
START_IN_THE_PAST = (
    "**{given}** has already gone by in **{tz}**, so nothing was submitted. Pick a time in the "
    f"future, or press **{ZONE_BUTTON}** on `/event` if that zone is not the one you are in."
)
BAD_DURATION = (
    "**{given}** is not a length Black Bloc can read, so nothing was submitted. Write it as "
    "`1h30m`, `2h` or `45m` — leave it empty for two hours — and keep it under a week."
)

ANNOUNCE_HEAD = "A new event is on the calendar."
INTERESTED_LINK = "Hit **Interested** on it to be reminded: {url}"
INTERESTED_HERE = "Hit **Interested** on it in the server's Events list to be reminded."
NO_SCHEDULED_EVENT = (
    "There is no Discord event to click this time, so watch this channel — Black Bloc says so "
    "again when it starts."
)


def clamp(text: Any, limit: int) -> str:
    return str(text or "").strip()[:limit]


def slugify(text: Any) -> str:
    """Discord channel-name rules: lowercase, `a-z0-9-`, no runs of dashes."""
    folded = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")


def channel_name(status: str, user_name: Any, title: Any) -> str:
    tail = "-".join(part for part in (slugify(user_name), slugify(title)) if part)
    name = f"{status}-{tail}" if tail else status
    return name[:CHANNEL_NAME_LIMIT].strip("-") or status


def parse_duration(text: Any, default: int = DEFAULT_DURATION_MINUTES) -> int | None:
    """Minutes from `1h30m`, or None when it cannot be read; empty means the default."""
    raw = str(text or "").strip().lower().replace(" ", "")
    if not raw:
        return default
    match = DURATION_PATTERN.match(raw)
    if match is None or not any(match.groups()):
        return None
    minutes = int(match.group(1) or 0) * 60 + int(match.group(2) or 0)
    if minutes <= 0 or minutes > MAX_DURATION_MINUTES:
        return None
    return minutes


def describe_duration(minutes: Any) -> str:
    total = int(minutes or 0)
    hours, rest = divmod(max(total, 0), 60)
    if hours and rest:
        return f"{hours}h {rest}m"
    if hours:
        return f"{hours}h"
    return f"{rest}m"


def can_transition(before: Any, after: Any) -> bool:
    return str(after) in TRANSITIONS.get(str(before), ())


def is_due(when: Any, now: datetime) -> bool:
    parsed = parse_ts(when)
    return parsed is not None and parsed <= now


def swept_anchor(row: Any) -> datetime | None:
    """A refused event's room counts from the decision; a finished one from when it ended."""
    if str(cell(row, "status") or "") not in DECIDED_STATUSES:
        return parse_ts(cell(row, "ends_at"))
    for column in SWEPT_ANCHORS:
        found = parse_ts(cell(row, column))
        if found is not None:
            return found
    return None


WHERE_VOICE = "voice"
WHERE_TEXT = "text"
WHERE_OTHER = "other"
WHERE_KINDS = (WHERE_VOICE, WHERE_TEXT, WHERE_OTHER)
WHERE_CHANNEL_KINDS = (WHERE_VOICE, WHERE_TEXT)
WHERE_BUTTON = "Where"
WHERE_VOICE_MARK = "🔊 "
WHERE_TEXT_MARK = "#"
WHERE_GONE_WORD = "a channel that has gone"
WHERE_JOIN = " · "
WHERE_LINK_JOIN = "\n\n"
WHERE_LINK_KEY = "events_where_link_in_description"
WHERE_SCHEMES = ("http://", "https://")
WHERE_BARE_HOST = "www."
WHERE_ASSUMED_SCHEME = "https://"
WHERE_OPEN_LINK_BUTTON = "Open link"
ROW_ITEM_CAP = 5
WHERE_HOST = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}(/\S*)?$", re.IGNORECASE)
WHERE_HANDLE = re.compile(r"^@?[a-z0-9._-]{1,64}$", re.IGNORECASE)
WHERE_ALIAS_SPLIT = re.compile(r"[/\s]+")


class Where(NamedTuple):
    """A channel, a typed place, or a channel with a link beside it; `text` means all three."""

    kind: str | None = None
    channel_id: int | None = None
    text: str = ""


WHERE_UNSET = Where()


def cell(row: Any, name: str) -> Any:
    """A column an older row may not carry yet, read without raising."""
    try:
        return row[name]
    except (KeyError, IndexError, TypeError):
        return None


def channel_where_kind(channel: Any) -> str | None:
    """Voice and stage are one kind to a person; anything unpickable is no kind at all."""
    kind = getattr(getattr(channel, "type", None), "name", None)
    if kind in ("voice", "stage_voice"):
        return WHERE_VOICE
    if kind in ("text", "news"):
        return WHERE_TEXT
    return None


def where_of_channel(channel: Any) -> Where:
    kind = channel_where_kind(channel)
    return Where(kind, int(channel.id), "") if kind else WHERE_UNSET


def read_where(row: Any) -> Where:
    """A stored event's place; a row from before schema 34 reads as the typed kind it was."""
    kind = cell(row, "where_kind")
    channel_id = cell(row, "where_channel_id")
    text = clamp(cell(row, "location"), LOCATION_LIMIT)
    if kind in WHERE_CHANNEL_KINDS and channel_id:
        return Where(str(kind), int(channel_id), text)
    return Where(WHERE_OTHER, None, text) if text else WHERE_UNSET


def where_link(text: Any) -> str | None:
    """The href when the typed place IS one link and nothing else; `the.bar at 8` is not."""
    said = str(text or "").strip()
    if len(said.split()) != 1:
        return None
    lowered = said.lower()
    for scheme in WHERE_SCHEMES:
        if lowered.startswith(scheme):
            return said if len(said) > len(scheme) else None
    if lowered.startswith(WHERE_BARE_HOST) and len(said) > len(WHERE_BARE_HOST):
        return f"{WHERE_ASSUMED_SCHEME}{said}"
    if WHERE_HOST.match(said):
        return f"{WHERE_ASSUMED_SCHEME}{said}"
    return None


def where_typed(text: Any, aliases: Any = WHERE_ALIASES) -> str:
    """`ttv/skyaiva` and `yt skyaiva` become the link they mean; anything else is left as typed."""
    said = str(text or "").strip()
    if not said or where_link(said) is not None:
        return said
    parts = WHERE_ALIAS_SPLIT.split(said, maxsplit=1)
    if len(parts) != 2:
        return said
    template = where_alias_table(aliases).get(parts[0].lower())
    if template is None or WHERE_HANDLE.match(parts[1]) is None:
        return said
    return template.format(handle=parts[1].lstrip("@"))


def where_shown(text: Any) -> str:
    """A link masked so an embed shows the place rather than the scheme; anything else as typed."""
    said = clamp(text, LOCATION_LIMIT)
    url = where_link(said)
    if url is None or ")" in url:
        return said
    label = url.split("://", 1)[-1].rstrip("/").replace("]", "").replace(")", "")
    return f"[{clamp(label, LOCATION_LIMIT)}]({url})" if label else said


def where_line(where: Where, *, linked: bool = True) -> str:
    """The card's and the draft's one Where line; empty means the field is left out."""
    text = clamp(where.text, LOCATION_LIMIT)
    shown = where_shown(text) if linked else text
    if where.kind in WHERE_CHANNEL_KINDS and where.channel_id:
        said = f"<#{int(where.channel_id)}>"
        return f"{said}{WHERE_JOIN}{shown}" if shown else said
    return shown


def where_said(where: Where, channel: Any = None) -> str:
    """Plain words for a button label, where a mention would render as its own id."""
    text = clamp(where.text, LOCATION_LIMIT)
    if where.kind in WHERE_CHANNEL_KINDS and where.channel_id:
        name = str(getattr(channel, "name", "") or "")
        mark = WHERE_VOICE_MARK if where.kind == WHERE_VOICE else WHERE_TEXT_MARK
        said = f"{mark}{name}" if name else WHERE_GONE_WORD
        return f"{said}{WHERE_JOIN}{text}" if text else said
    return text


def where_button_label(where: Where, channel: Any = None) -> str:
    said = where_said(where, channel)
    if not said:
        return WHERE_BUTTON
    return clamp(f"{WHERE_BUTTON}: {said}", BUTTON_LABEL_LIMIT)


WHERE_NOTE_MARK = " — ⚠️ {note}"
WHERE_NOTE_MISSING = "that page answered 404 — check the name"
WHERE_NOTE_UNREACHABLE = "{host} did not answer within {seconds} s — the link is kept as typed"
WHERE_REFUSED_MISSING = (
    "**{url}** answered 404, so nowhere was saved and the old place was kept. That usually "
    "means the name is misspelt — check it and open the box again. A Lead can set "
    "`events_where_link_check` to warn if you would rather it were kept anyway."
)
WHERE_REFUSED_UNREACHABLE = (
    "**{url}** did not answer within {seconds} seconds, so nowhere was saved and the old place "
    "was kept. The site may be down, or slower than the box can wait — try again in a moment. A "
    "Lead can set `events_where_link_check` to warn if you would rather it were kept anyway."
)


def link_host(url: Any) -> str:
    """The host on its own, for a sentence that should not read out a whole href."""
    return str(url or "").split("://", 1)[-1].split("/", 1)[0]


def where_note(verdict: str, url: Any, seconds: Any) -> str:
    """The draft's one-line warning; `LINK_OK` has nothing to say."""
    if verdict == LINK_MISSING:
        return WHERE_NOTE_MISSING
    if verdict == LINK_UNREACHABLE:
        return WHERE_NOTE_UNREACHABLE.format(host=link_host(url) or url, seconds=seconds)
    return ""


def where_refused(verdict: str, url: Any, seconds: Any) -> str:
    """The refusing mode's sentence: what happened, what was kept, and what to do."""
    said = clamp(url, LOCATION_LIMIT)
    if verdict == LINK_MISSING:
        return WHERE_REFUSED_MISSING.format(url=said)
    return WHERE_REFUSED_UNREACHABLE.format(url=said, seconds=seconds)


WHERE_UNKNOWN_KIND = (
    "**{given}** is not a kind of place Black Bloc can set, so nothing was saved. It takes a "
    "voice channel, a text channel, or **somewhere else** with the place typed in."
)
WHERE_NEEDS_A_CHANNEL = (
    "A voice or text channel has to be picked before it can be saved, so nothing was changed. "
    "Pick one from the list, or choose **somewhere else** and type where it is."
)
WHERE_NO_SUCH_CHANNEL = (
    "Black Bloc cannot find channel **{given}** on this server, so nothing was saved. It may "
    "have been deleted — pick one from the list, or choose **somewhere else** and type it."
)
WHERE_NOT_A_PLACE = (
    "**{name}** is not somewhere an event can happen, so nothing was saved. Discord takes a "
    "voice channel, a stage or a text channel — or **somewhere else** with the place typed in."
)


def checked_where(
    guild: Any, kind: Any, channel_id: Any, text: Any, *, aliases: Any = WHERE_ALIASES
) -> tuple[Where | None, str]:
    """The website's door onto the same three kinds, refusing in words rather than a status."""
    wanted = str(kind or "").strip().lower()
    typed = clamp(where_typed(clamp(text, LOCATION_LIMIT), aliases), LOCATION_LIMIT)
    if not wanted:
        return (Where(WHERE_OTHER, None, typed) if typed else WHERE_UNSET), ""
    if wanted not in WHERE_KINDS:
        return None, WHERE_UNKNOWN_KIND.format(given=clamp(kind, 40))
    if wanted == WHERE_OTHER:
        return (Where(WHERE_OTHER, None, typed) if typed else WHERE_UNSET), ""
    given = str(channel_id or "").strip()
    if not given.isdigit():
        return None, WHERE_NEEDS_A_CHANNEL
    channel = guild.get_channel(int(given))
    if channel is None:
        return None, WHERE_NO_SUCH_CHANNEL.format(given=clamp(given, 40))
    found = where_of_channel(channel)
    if found.kind is None:
        return None, WHERE_NOT_A_PLACE.format(
            name=clamp(getattr(channel, "name", ""), 60) or given
        )
    return found._replace(text=typed), ""


def described_with_where(description: Any, where: Where, *, appended: bool = True) -> str:
    """A channel is the place, so the link typed beside it rides in the description instead."""
    body = clamp(description, DESCRIPTION_LIMIT)
    text = clamp(where.text, LOCATION_LIMIT)
    if not appended or not text or where.kind not in WHERE_CHANNEL_KINDS:
        return body
    said = where_link(text) or text
    trimmed = clamp(body, max(DESCRIPTION_LIMIT - len(said) - len(WHERE_LINK_JOIN), 0))
    return f"{trimmed}{WHERE_LINK_JOIN}{said}" if trimmed else said


def build_card(
    *,
    event_id: Any,
    title: str,
    requester_id: int,
    starts_at: datetime,
    minutes: int,
    where: Where = WHERE_UNSET,
    description: str | None = None,
    status: str = PENDING,
    deny_reason: str | None = None,
) -> discord.Embed:
    """The one card every surface shows: review channel, DM, announcement."""
    embed = discord.Embed(
        title=clamp(title, TITLE_LIMIT),
        description=clamp(description, DESCRIPTION_LIMIT) or None,
        colour=COLOURS.get(status, COLOURS[PENDING]),
    )
    embed.add_field(name="Who", value=f"<@{requester_id}>", inline=True)
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="How long", value=describe_duration(minutes), inline=True)
    embed.add_field(name="When", value=stamp(starts_at), inline=False)
    said = where_line(where)
    if said:
        embed.add_field(name="Where", value=said, inline=False)
    if deny_reason:
        embed.add_field(name="Why not", value=clamp(deny_reason, 1024), inline=False)
    embed.set_footer(text=f"Event #{event_id}")
    return embed


def mentions(ping_role_id: Any = None) -> discord.AllowedMentions:
    """Nothing an event's author typed may ping; only the configured role may."""
    return discord.AllowedMentions(
        everyone=False,
        users=False,
        roles=[discord.Object(int(ping_role_id))] if ping_role_id else False,
    )


def announce_text(
    ping_role_id: Any = None, *, has_scheduled: bool = False, event_url: str | None = None
) -> str:
    prefix = f"<@&{ping_role_id}> " if ping_role_id else ""
    if has_scheduled and event_url:
        return f"{prefix}{ANNOUNCE_HEAD} {INTERESTED_LINK.format(url=event_url)}"
    if has_scheduled:
        return f"{prefix}{ANNOUNCE_HEAD} {INTERESTED_HERE}"
    return f"{prefix}{ANNOUNCE_HEAD} {NO_SCHEDULED_EVENT}"


def golive_text(title: str, ping_role_id: Any = None) -> str:
    prefix = f"<@&{ping_role_id}> " if ping_role_id else ""
    return f"{prefix}**{clamp(title, TITLE_LIMIT)}** is starting now!"


def ends_at(starts_at: datetime, minutes: int) -> datetime:
    return starts_at + timedelta(minutes=max(int(minutes), 1))


def start_error(given: Any, tz_name: str, example: str) -> str:
    return BAD_START.format(given=clamp(given, 80) or "(nothing)", tz=tz_name, example=example)


LOCKS_ATTR = "_event_locks"
LOCATION_FALLBACK = "Ask in the server"
SELECT_CAP = 25
SELECT_OPTION_LIMIT = 100
LIST_PAGE = 10
DENY_LIMIT = 400
CANCEL_NOTE_LIMIT = 400
PANEL_MINUTES_KEY = "event_panel_minutes"
PANEL_OWN_LIST_KEY = "event_panel_own_list"
DEFAULT_MINUTES_KEY = "events_default_minutes"

UNKNOWN_TZ = (
    "**{given}** is not a time zone Black Bloc knows, so nothing was saved. Write the "
    "`Region/City` name Discord and your phone both use — `America/Phoenix`, `Europe/London`, "
    "`Asia/Tokyo`."
)
DID_YOU_MEAN = "Did you mean {names}?"
TZ_SET = (
    "Your time zone is **{tz}**, where it is now **{now}**. Times you type into a proposal are "
    f"read in that zone, so `{START_EXAMPLE}` means half past seven in the evening for you."
)
TZ_SHOW = (
    f"Your time zone is **{{tz}}**, where it is now **{{now}}**. **{ZONE_BUTTON}** changes it."
)
TZ_SHOW_DEFAULT = (
    "You have not set a time zone, so Black Bloc reads the times you type as **{tz}**, where it "
    f"is now **{{now}}**. **{ZONE_BUTTON}** changes that."
)

EVENTS_OFF = (
    "Event proposals are turned off on this server, so nothing was submitted. A Lead turns them "
    "back on with **Settings** on `/event` — ask one if you have something to run."
)
NO_TEST_CHANNEL = (
    "Black Bloc is in test mode and cannot work out where a review channel would be allowed, so "
    "nothing was submitted. Its test channel has to exist AND has to sit inside a category — set "
    "TEST_CHANNEL_ID to a channel the bot can read, put that channel in a category, restart it, "
    "then try again."
)
NO_TITLE = (
    "An event needs a name, so nothing was submitted. Put something in the Title box — it is the "
    "heading everybody sees on the card."
)
DST_GAP = (
    "**{given}** never happens in **{tz}** — the clocks jump forward over that hour, so nothing "
    "was submitted. Pick a time before or after the hour that is skipped, or press "
    f"**{ZONE_BUTTON}** if that zone is not the one you are in."
)
DST_AMBIGUOUS = (
    "**{given}** happens twice in **{tz}** — the clocks go back and that hour runs again, so "
    "Black Bloc will not guess which of the two you meant and nothing was submitted. Pick a time "
    "an hour either side of it."
)
DRAFT_TITLE = "Propose an event — draft"
DRAFT_NEEDED = "(needed)"
DRAFT_NOT_SET = "(not set)"
DRAFT_NOTHING_YET = "(nothing yet)"
DRAFT_WHAT_LIMIT = 120
DRAFT_WHEN = "{when}, read in **{tz}**"
DRAFT_ZONE_HINT = (
    "Times are read in **{tz}** — the server's default. Press **Time zone** if that is not yours."
)
DRAFT_ZONE = "Times are read in **{tz}**, which **Time zone** changes."
STILL_NEEDED = "**Still needed:** {why}"
TEXT_BUTTON = "Title & details"
ZONE_PANEL_BUTTON = "Time zone"
SUBMIT_BUTTON = "Submit"
TEXT_MODAL_TITLE = "Title & details"
WHERE_PANEL_TITLE = "Where is it?"
WHERE_PANEL_INTRO = (
    "Pick the voice or text channel it happens in, or **Other** for a place or a link that is "
    "not on this server. With a channel picked the box is still yours — a Twitch link or a note "
    "beside it is optional. Leaving it all empty is fine — the card just will not say where."
)
WHERE_PLACEHOLDER = "A voice or text channel…"
WHERE_OTHER_BUTTON = "Other — type a place or link…"
WHERE_LINK_BUTTON = "Link or place (optional)…"
WHERE_CLEAR_BUTTON = "Clear"
WHERE_MODAL_TITLE = "Somewhere else"
WHERE_LINK_MODAL_TITLE = "A link or a note"
WHERE_MODAL_LABEL = "Where, or a link"
WHERE_JOIN_NOTE = (
    "A voice or stage channel gives everybody a **Join** button on the Discord event; anything "
    "else is written on it as words."
)
ZONE_PANEL_TITLE = "Your time zone"
ZONE_PANEL_INTRO = (
    "Times you pick are read in this zone. Pick one, or **Other — type it…** for anywhere else."
)
CANCELLED_ANNOUNCEMENT = "**{title}** is cancelled and is no longer happening."
NO_CATEGORY = (
    "Black Bloc has nowhere to put the review channel, so nothing was submitted. A Lead points it "
    "at a category with **Settings** on `/event`, then this works."
)
NOT_A_CATEGORY = (
    "**events_category_id** points at something that is not a category, so nothing was "
    "submitted. A Lead fixes it with **Settings** on `/event`."
)
CANNOT_CREATE = (
    "Discord refused to make the review channel, so nothing was submitted. Black Bloc needs the "
    "Manage Channels permission in that category. Tell a Lead, then try again."
)
CATEGORY_TROUBLE: dict[str, str] = {
    "no_test_channel": NO_TEST_CHANNEL,
    "no_category": NO_CATEGORY,
    "not_a_category": NOT_A_CATEGORY,
}
SUBMITTED = (
    "**{title}** is in — the mods will review it and Black Bloc will DM you either way. {where}"
)
SUBMITTED_HERE = (
    "Their review card is in {channel} — you can see and post in there too, so answer anything "
    "they ask and put updates in the same place."
)
SUBMITTED_TEST = (
    "Test mode is on, so the review card is in this channel rather than in {channel}, which is "
    "where it will go once the owner lifts it."
)
SUBMITTED_NO_CARD = (
    "Black Bloc could not post the review card in {channel} — the log says why, and a Lead can "
    "still decide it there by hand."
)
STARTS_AT = "It starts {local} your time ({tz}) · {stamp}"
NO_SUCH_EVENT = (
    "Black Bloc has no record of that event any more, so nothing was changed. `/event` shows the "
    "ones it still knows about."
)
ALREADY_DECIDED = (
    "Somebody got there first — event #{event_id} is already **{status}**, so nothing was "
    "changed. Its card above shows who decided and when."
)
APPROVED_SAID = "Approved. {extra}"
DENIED_SAID = "Denied, and the requester has been told why."
DM_APPROVED = "Your event **{title}** was approved on **{guild}**. It starts {stamp}."
DM_DENIED = (
    "Your event **{title}** was not approved on **{guild}**. The reason given was: {reason}. Ask "
    "a Lead there if you want to talk it over — Black Bloc cannot change the decision."
)
DM_CANCELLED = "Your event **{title}** on **{guild}** has been cancelled — {why}"
CANCEL_NOTE = " The reason given was: {note}"
CANCEL_WHY: dict[str, str] = {
    "never_got_a_channel": (
        "Black Bloc could not finish setting it up, so nobody was ever able to review it. Propose "
        "it again with `/event`."
    ),
    "review_channel_gone": (
        "the channel the mods were reviewing it in is no longer there. Propose it again with "
        "`/event` if it should still happen."
    ),
    "review_channel_deleted": (
        "the channel the mods were reviewing it in was deleted. Propose it again with `/event` "
        "if it should still happen."
    ),
    "unreadable_start": (
        "Black Bloc could not read the start time stored for it. Propose it again with `/event` "
        "and write the time as `YYYY-MM-DD HH:MM`."
    ),
}
CANCEL_WHY_DEFAULT = (
    "either you or a member of staff called it off. Ask a Lead there if that is a surprise."
)
DM_MISSED = (
    "Your event **{title}** on **{guild}** finished before Black Bloc ever announced it, so "
    "nobody was told it was on. It has been marked done. Sorry — propose it again with `/event` "
    "if you want another go."
)
CANCELLED_SAID = "Event #{event_id} is cancelled."
NOT_OPEN = "Event #{event_id} is already **{status}**, so there was nothing to cancel."
NOT_AN_ID = "**{given}** is not an event number, so nothing was cancelled. `/event` has them."
NO_STAFF_WARNING = (
    "⚠️ **No staff roles resolve**, so nobody but server admins can see a review channel or press "
    "Approve. Point `staff_channel_id` at a channel only staff can see with `/settings` ▸ "
    "staff_channel_id`, then open `/event` again."
)

PANEL_TITLE = "Events"
PANEL_INTRO = "Propose something for the server to do, and see where the open ones have got to."
PANEL_EMPTY = "You have not proposed an event yet."
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /event again"
PICK_AN_EVENT = "Pick an event…"
CALL_ONE_OFF = "Call one off…"
SITE_BUTTON = "Open on the site"
NOTHING_OPEN = "Nothing is open — nothing is waiting on a decision and nothing is running."
NO_MOVES_LEFT = "**{status}** is where an event finishes — nothing moves it now."
DENIED_ROOM_GONE = (
    "It was denied and the room it was reviewed in was cleaned up — propose it again with "
    "**Propose an event**."
)
REVIEW_ROOM_BUTTON = "The review channel"
CHANNEL_URL = "https://discord.com/channels/{guild_id}/{channel_id}"


async def create_event(
    db: Any,
    guild_id: int,
    requester_id: int,
    *,
    title: str,
    description: str | None,
    where: Where = WHERE_UNSET,
    starts_at: datetime,
    finishes_at: datetime,
) -> int | None:
    cur = await db.conn.execute(
        "INSERT INTO events(guild_id, requester_id, title, description, location, where_kind, "
        "where_channel_id, starts_at, ends_at, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            guild_id,
            requester_id,
            title,
            description or None,
            clamp(where.text, LOCATION_LIMIT) or None,
            where.kind or None,
            int(where.channel_id) if where.channel_id else None,
            starts_at.isoformat(),
            finishes_at.isoformat(),
            PENDING,
            now_iso(),
        ),
    )
    await db.conn.commit()
    return cur.lastrowid


class EventFields(NamedTuple):
    title: str
    description: str
    where: Where
    starts: datetime
    minutes: int


def checked_fields(
    *,
    title: Any,
    description: Any,
    where: Where = WHERE_UNSET,
    start: Any,
    duration: Any,
    tz_name: str,
    now: datetime,
) -> tuple[EventFields | None, str]:
    """Every rule an event's fields have to pass, for the modal and the dashboard alike."""
    wanted = clamp(title, TITLE_LIMIT)
    if not wanted:
        return None, NO_TITLE
    starts = parse_start(start, tz_name)
    if starts is None:
        return None, start_error(start, tz_name, START_EXAMPLE)
    trouble = clock_trouble(start, tz_name)
    if trouble == GAP:
        return None, DST_GAP.format(given=clamp(start, 80), tz=tz_name)
    if trouble == AMBIGUOUS:
        return None, DST_AMBIGUOUS.format(given=clamp(start, 80), tz=tz_name)
    if starts <= now:
        return None, START_IN_THE_PAST.format(given=clamp(start, 80), tz=tz_name)
    minutes = parse_duration(duration)
    if minutes is None:
        return None, BAD_DURATION.format(given=clamp(duration, 40))
    return (
        EventFields(
            wanted,
            clamp(description, DESCRIPTION_LIMIT),
            where._replace(text=clamp(where.text, LOCATION_LIMIT)),
            starts,
            minutes,
        ),
        "",
    )


@dataclass
class EventDraft:
    """What the Propose panel holds between renders; nothing typed into it can be refused."""

    when: WhenDraft = field(default_factory=WhenDraft)
    title: str = ""
    description: str = ""
    where: Where = WHERE_UNSET
    duration: str = ""
    where_note: str = ""


def draft_check(draft: EventDraft, now: datetime) -> tuple[EventFields | None, str]:
    """The panel's own gate: `checked_fields` once there is a time, its own sentence before."""
    start, trouble = resolve(draft.when, now)
    if start is None:
        if not clamp(draft.title, TITLE_LIMIT):
            return None, NO_TITLE
        return None, trouble
    return checked_fields(
        title=draft.title,
        description=draft.description,
        where=draft.where,
        start=start,
        duration=draft.duration,
        tz_name=draft.when.zone,
        now=now,
    )


def draft_when_line(draft: EventDraft, now: datetime) -> str:
    said = said_when(draft.when)
    if said:
        return DRAFT_WHEN.format(when=said, tz=draft.when.zone)
    return resolve(draft.when, now)[1]


def draft_how_long(draft: EventDraft) -> str:
    minutes = parse_duration(draft.duration)
    if minutes is None:
        return clamp(draft.duration, 40) or DRAFT_NOT_SET
    return describe_duration(minutes)


def draft_lines(draft: EventDraft, now: datetime, *, chosen: bool, why: str = "") -> list[str]:
    """The draft card, in the order the design writes it, with one Still-needed line at most."""
    when = draft_when_line(draft, now)
    said = where_line(draft.where) or DRAFT_NOT_SET
    if draft.where_note:
        said = f"{said}{WHERE_NOTE_MARK.format(note=draft.where_note)}"
    lines = [
        f"**Title** — {clamp(draft.title, TITLE_LIMIT) or DRAFT_NEEDED}",
        f"**When** — {when}",
        f"**How long** — {draft_how_long(draft)}",
        f"**Where** — {said}",
        f"**What** — {clamp(draft.description, DRAFT_WHAT_LIMIT) or DRAFT_NOTHING_YET}",
    ]
    lines.append((DRAFT_ZONE if chosen else DRAFT_ZONE_HINT).format(tz=draft.when.zone))
    if why and why != when:
        lines.append(STILL_NEEDED.format(why=why))
    return lines


def scheduled_name(
    template: Any, title: Any, *, fallback: str = EVENTS_SCHEDULED_NAME_TEMPLATE
) -> str:
    """Staff-editable text, so a template that will not render falls back (checklist 17)."""
    wanted = clamp(title, TITLE_LIMIT)
    try:
        rendered = (str(template or "").strip() or NAME_PLACEHOLDER).format(title=wanted)
    except (KeyError, IndexError, ValueError) as exc:
        log.warning("events: the calendar name %r would not render: %s", template, exc)
        rendered = fallback.format(title=wanted)
    return clamp(rendered, EVENT_NAME_LIMIT) or wanted[:EVENT_NAME_LIMIT]


async def update_event(
    db: Any,
    event_id: int,
    *,
    title: str,
    description: str | None,
    where: Where = WHERE_UNSET,
    starts_at: datetime,
    finishes_at: datetime,
) -> None:
    await db.conn.execute(
        "UPDATE events SET title = ?, description = ?, location = ?, where_kind = ?, "
        "where_channel_id = ?, starts_at = ?, ends_at = ? WHERE id = ?",
        (
            title,
            description or None,
            clamp(where.text, LOCATION_LIMIT) or None,
            where.kind or None,
            int(where.channel_id) if where.channel_id else None,
            starts_at.isoformat(),
            finishes_at.isoformat(),
            event_id,
        ),
    )
    await db.conn.commit()


async def get_event(db: Any, event_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    return await cur.fetchone()


async def events_by_status(db: Any, guild_id: int, statuses: Any) -> list[Any]:
    marks = ", ".join("?" for _ in statuses)
    cur = await db.conn.execute(
        f"SELECT * FROM events WHERE guild_id = ? AND status IN ({marks}) ORDER BY starts_at",
        (guild_id, *statuses),
    )
    return list(await cur.fetchall())


async def own_events(
    db: Any, guild_id: int, user_id: int, statuses: Any = OPEN_STATUSES
) -> list[Any]:
    """One member's own events — nothing before the panel ever asked this."""
    marks = ", ".join("?" for _ in statuses)
    cur = await db.conn.execute(
        f"SELECT * FROM events WHERE guild_id = ? AND requester_id = ? AND status IN ({marks}) "
        "ORDER BY starts_at",
        (guild_id, user_id, *statuses),
    )
    return list(await cur.fetchall())


async def due_events(db: Any, status: str, column: str, before: str) -> list[Any]:
    cur = await db.conn.execute(
        f"SELECT * FROM events WHERE status = ? AND {column} IS NOT NULL AND {column} <= ? "
        "ORDER BY id",
        (status, before),
    )
    return list(await cur.fetchall())


async def set_review(
    db: Any,
    event_id: int,
    channel_id: int | None,
    message_id: int | None,
    card_channel_id: int | None = None,
) -> None:
    await db.conn.execute(
        "UPDATE events SET review_channel_id = ?, review_message_id = ?, card_channel_id = ? "
        "WHERE id = ?",
        (channel_id, message_id, card_channel_id, event_id),
    )
    await db.conn.commit()


async def set_where(db: Any, event_id: int, where: Where) -> None:
    """Staff final say, one fact at a time: the three columns `Where` owns and nothing else."""
    await db.conn.execute(
        "UPDATE events SET location = ?, where_kind = ?, where_channel_id = ? WHERE id = ?",
        (
            clamp(where.text, LOCATION_LIMIT) or None,
            where.kind or None,
            int(where.channel_id) if where.channel_id else None,
            event_id,
        ),
    )
    await db.conn.commit()


async def set_status(
    db: Any,
    event_id: int,
    status: str,
    *,
    decided_by: int | None = None,
    deny_reason: str | None = None,
) -> None:
    await db.conn.execute(
        "UPDATE events SET status = ?, decided_by = COALESCE(?, decided_by), "
        "decided_at = COALESCE(?, decided_at), deny_reason = COALESCE(?, deny_reason) WHERE id = ?",
        (
            status,
            decided_by,
            now_iso() if decided_by is not None else None,
            deny_reason,
            event_id,
        ),
    )
    await db.conn.commit()


async def set_scheduled(db: Any, event_id: int, scheduled_event_id: int) -> None:
    await db.conn.execute(
        "UPDATE events SET scheduled_event_id = ? WHERE id = ?", (scheduled_event_id, event_id)
    )
    await db.conn.commit()


async def set_announced(db: Any, event_id: int, message_id: int) -> None:
    await db.conn.execute(
        "UPDATE events SET announce_message_id = ? WHERE id = ?", (message_id, event_id)
    )
    await db.conn.commit()


async def event_for_channel(db: Any, channel_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM events WHERE review_channel_id = ? ORDER BY id DESC LIMIT 1", (channel_id,)
    )
    return await cur.fetchone()


def event_lock(bot: Any, event_id: int) -> asyncio.Lock:
    locks = getattr(bot, LOCKS_ATTR, None)
    if locks is None:
        locks = {}
        setattr(bot, LOCKS_ATTR, locks)
    lock = locks.get(event_id)
    if lock is None:
        lock = locks[event_id] = asyncio.Lock()
    return lock


def drop_lock(bot: Any, event_id: int) -> None:
    """A settled event will never be raced again, so its lock stops being kept."""
    locks = getattr(bot, LOCKS_ATTR, None)
    if locks is not None:
        locks.pop(event_id, None)


def duration_minutes(row: Any) -> int:
    starts = parse_ts(row["starts_at"])
    finishes = parse_ts(row["ends_at"])
    if starts is None or finishes is None:
        return DEFAULT_DURATION_MINUTES
    return max(int((finishes - starts).total_seconds() // 60), 1)


def card_for(row: Any) -> discord.Embed:
    """One place turns a stored event into the card every surface shows."""
    starts = parse_ts(row["starts_at"]) or datetime.now(UTC)
    return build_card(
        event_id=row["id"],
        title=row["title"],
        requester_id=row["requester_id"],
        starts_at=starts,
        minutes=duration_minutes(row),
        where=read_where(row),
        description=row["description"],
        status=row["status"],
        deny_reason=row["deny_reason"],
    )


def review_overwrites(
    guild: Any, staff_roles: Any, me: Any = None, requester: Any = None
) -> dict[Any, Any]:
    overwrites: dict[Any, Any] = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False)
    }
    for role in staff_roles:
        overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
    if me is not None:
        overwrites[me] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_channels=True
        )
    if requester is not None:
        overwrites[requester] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True
        )
    return overwrites


def events_category(bot: Any, guild: Any) -> tuple[Any, str]:
    """Where review channels go: the test channel's category while the guard is installed."""
    guard = getattr(bot, "guard", None)
    if guard is not None:
        test_channel = bot.get_channel(guard.test_channel_id) if guard.test_channel_id else None
        category = getattr(test_channel, "category", None)
        if test_channel is None or category is None:
            return None, "no_test_channel"
        return category, "test_category"
    category_id = bot.store.get(guild.id, "events_category_id")
    if not category_id:
        return None, "no_category"
    category = guild.get_channel(category_id)
    if category is None:
        return None, "no_category"
    if not isinstance(category, discord.CategoryChannel) and not hasattr(category, "channels"):
        return None, "not_a_category"
    return category, "category"


def card_channel(bot: Any, review_channel: Any) -> Any:
    """The review card goes to the test channel while the guard would refuse the review one."""
    guard = getattr(bot, "guard", None)
    if guard is None or guard.allows_channel(review_channel.id):
        return review_channel
    return bot.get_channel(guard.test_channel_id) if guard.test_channel_id else None


async def dm(user: Any, text: str, embed: discord.Embed | None = None) -> bool:
    """Whether the person actually got told."""
    send = getattr(user, "send", None)
    if send is None:
        return False
    try:
        await send(text, embed=embed, allowed_mentions=discord.AllowedMentions.none())
    except Exception as exc:
        log.info("events: could not DM %s: %s", getattr(user, "id", "?"), exc)
        return False
    return True


async def tell_or_log(bot: Any, guild: Any, user: Any, row: Any, text: str) -> None:
    """A DM the requester is owed; a failure is a logged fact, never a silent one."""
    if await dm(user, text, card_for(row)):
        return
    await log_action(
        bot,
        guild,
        "event.dm_failed",
        target=row["requester_id"],
        details={"event_id": row["id"]},
    )


async def rename_channel(bot: Any, guild: Any, row: Any, status: str, user_name: str) -> None:
    channel = guild.get_channel(row["review_channel_id"]) if row["review_channel_id"] else None
    if channel is None:
        return
    wanted = channel_name(status, user_name, row["title"])
    if getattr(channel, "name", None) == wanted:
        return
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_place(channel):
        await log_action(
            bot,
            guild,
            "event.would_rename",
            details={"event_id": row["id"], "channel_id": channel.id, "name": wanted},
        )
        return
    try:
        await channel.edit(name=wanted, reason=f"Black Bloc event {row['id']}")
    except NETWORK_ERRORS as exc:
        log.warning("events: could not rename %s to %s: %s", channel.id, wanted, exc)
        await log_action(
            bot,
            guild,
            "event.rename_failed",
            details={
                "event_id": row["id"],
                "channel_id": channel.id,
                "reason": f"{type(exc).__name__}: {exc}",
            },
        )


async def scheduled_place(bot: Any, guild: Any, row: Any) -> dict[str, Any]:
    """Discord's own three doors: a voice channel, a stage, or the external kind with words."""
    where = read_where(row)
    if where.kind in WHERE_CHANNEL_KINDS and where.channel_id:
        channel = guild.get_channel(int(where.channel_id))
        if channel is None:
            await log_action(
                bot,
                guild,
                "event.where_channel_gone",
                target=row["requester_id"],
                details={
                    "event_id": row["id"],
                    "channel_id": int(where.channel_id),
                    "where_kind": where.kind,
                },
            )
        else:
            kind = getattr(getattr(channel, "type", None), "name", None)
            if kind == "stage_voice":
                return {"entity_type": discord.EntityType.stage_instance, "channel": channel}
            if kind == "voice":
                return {"entity_type": discord.EntityType.voice, "channel": channel}
            return {
                "entity_type": discord.EntityType.external,
                "location": clamp(f"#{getattr(channel, 'name', '')}", LOCATION_LIMIT),
            }
    return {
        "entity_type": discord.EntityType.external,
        "location": clamp(where.text, LOCATION_LIMIT) or LOCATION_FALLBACK,
    }


async def create_scheduled_event(bot: Any, guild: Any, row: Any) -> tuple[Any, str | None]:
    """The scheduled event Discord made, or the reason there is not one."""
    if not bot.store.get(guild.id, "events_create_scheduled"):
        return None, "turned_off"
    starts = parse_ts(row["starts_at"])
    finishes = parse_ts(row["ends_at"])
    if starts is None:
        return None, "unreadable_start"
    if finishes is None:
        finishes = ends_at(starts, default_minutes(bot.store, guild.id))
    if getattr(bot, "guard", None) is not None:
        log.warning("events: TEST MODE — no scheduled event made for event %s", row["id"])
        await log_action(
            bot,
            guild,
            "event.would_create_scheduled",
            target=row["requester_id"],
            details={"event_id": row["id"], "reason": "test_mode"},
        )
        return None, "test_mode"
    place = await scheduled_place(bot, guild, row)
    try:
        made = await guild.create_scheduled_event(
            name=scheduled_name(
                bot.store.get(guild.id, EVENTS_SCHEDULED_NAME_KEY), row["title"]
            ),
            description=described_with_where(
                row["description"],
                read_where(row),
                appended=bool(bot.store.get(guild.id, WHERE_LINK_KEY)),
            )
            or None,
            start_time=starts,
            end_time=finishes,
            privacy_level=discord.PrivacyLevel.guild_only,
            reason=f"Black Bloc event {row['id']}",
            **place,
        )
    except NETWORK_ERRORS as exc:
        log.warning("events: could not make a scheduled event for %s: %s", row["id"], exc)
        await log_action(
            bot,
            guild,
            "event.create_scheduled_failed",
            target=row["requester_id"],
            details={"event_id": row["id"], "reason": f"{type(exc).__name__}: {exc}"},
        )
        return None, f"{type(exc).__name__}: {exc}"
    await set_scheduled(bot.db, row["id"], made.id)
    return made, None


async def find_scheduled_event(guild: Any, scheduled_id: int) -> Any:
    """The cache first, then Discord — a restart empties the cache, not the calendar."""
    cached = getattr(guild, "get_scheduled_event", None)
    found = cached(scheduled_id) if cached is not None else None
    if found is not None:
        return found
    fetch = getattr(guild, "fetch_scheduled_event", None)
    if fetch is None:
        return None
    return await fetch(scheduled_id)


async def cancel_scheduled_event(bot: Any, guild: Any, row: Any) -> None:
    scheduled_id = row["scheduled_event_id"]
    if not scheduled_id:
        return
    details = {"event_id": row["id"], "scheduled_event_id": scheduled_id}
    if getattr(bot, "guard", None) is not None:
        await log_action(
            bot,
            guild,
            "event.would_cancel_scheduled",
            details=details | {"reason": "test_mode"},
        )
        return
    reason = f"Black Bloc event {row['id']} cancelled"
    try:
        event = await find_scheduled_event(guild, scheduled_id)
        if event is None:
            raise ValueError("Discord has no such scheduled event")
        if getattr(event, "status", None) is discord.EventStatus.active:
            await event.end(reason=reason)
        else:
            await event.cancel(reason=reason)
    except NETWORK_ERRORS as exc:
        log.warning("events: could not cancel scheduled event %s: %s", scheduled_id, exc)
        await log_action(
            bot,
            guild,
            "event.cancel_scheduled_failed",
            details=details | {"reason": f"{type(exc).__name__}: {exc}"},
        )


async def post_to_announce(
    bot: Any, guild: Any, row: Any, text: str, embed: discord.Embed | None, kind: str
) -> int | None:
    """The one guarded way anything of this feature reaches a public channel."""
    ping_role_id = bot.store.get(guild.id, "events_ping_role_id")
    details = {"event_id": row["id"]}
    mode = bot.store.get(guild.id, "events_mode")
    if mode != "on":
        await log_action(
            bot, guild, f"event.would_{kind}", details=details | {"reason": f"mode_{mode}"}
        )
        return None
    channel_id = bot.store.get(guild.id, "events_announce_channel_id")
    channel = bot.get_channel(channel_id) if channel_id else None
    if channel is None:
        await log_action(
            bot, guild, f"event.{kind}_failed", details=details | {"reason": "no_channel"}
        )
        return None
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel.id):
        await log_action(
            bot, guild, f"event.would_{kind}", details=details | {"reason": "test_mode"}
        )
        return None
    try:
        message = await channel.send(text, embed=embed, allowed_mentions=mentions(ping_role_id))
    except Exception as exc:
        log.warning("events: could not post %s for event %s: %s", kind, row["id"], exc)
        await log_action(
            bot,
            guild,
            f"event.{kind}_failed",
            details=details | {"reason": f"{type(exc).__name__}: {exc}"},
        )
        return None
    await log_action(bot, guild, f"event.{kind}", details=details | {"channel_id": channel.id})
    return message.id


async def edit_announcement(bot: Any, guild: Any, row: Any) -> None:
    """A public post must stop advertising an event that is off."""
    message_id = row["announce_message_id"]
    if not message_id:
        return
    channel_id = bot.store.get(guild.id, "events_announce_channel_id")
    channel = bot.get_channel(channel_id) if channel_id else None
    details = {"event_id": row["id"], "message_id": message_id}
    if channel is None:
        await log_action(
            bot,
            guild,
            "event.edit_announcement_failed",
            details=details | {"reason": "no_channel"},
        )
        return
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel):
        await log_action(bot, guild, "event.would_edit_announcement", details=details)
        return
    partial = getattr(channel, "get_partial_message", None)
    try:
        message = (
            partial(message_id) if partial is not None else await channel.fetch_message(message_id)
        )
        await message.edit(
            content=CANCELLED_ANNOUNCEMENT.format(title=clamp(row["title"], TITLE_LIMIT)),
            embed=card_for(row),
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except NETWORK_ERRORS as exc:
        log.warning("events: could not edit the announcement for %s: %s", row["id"], exc)
        await log_action(
            bot,
            guild,
            "event.edit_announcement_failed",
            details=details | {"reason": f"{type(exc).__name__}: {exc}"},
        )
        return
    await log_action(bot, guild, "event.announcement_edited", details=details)


async def cancel_event(
    bot: Any,
    guild: Any,
    row: Any,
    reason: str,
    *,
    by: int | None = None,
    note: Any = None,
    via: str = VIA_DISCORD,
) -> bool:
    """Cancel one event and undo what it left behind; False when it was past cancelling."""
    async with event_lock(bot, row["id"]):
        fresh = await get_event(bot.db, row["id"])
        if fresh is None or not can_transition(fresh["status"], CANCELLED):
            return False
        await set_status(bot.db, fresh["id"], CANCELLED)
        drop_lock(bot, fresh["id"])
        kept = clamp(note, CANCEL_NOTE_LIMIT)
        await log_action(
            bot,
            guild,
            kind_via("event.cancelled", via),
            target=fresh["requester_id"],
            reason=kept or reason,
            details={"event_id": fresh["id"], "title": fresh["title"], "via": via},
        )
        await cancel_scheduled_event(bot, guild, fresh)
        fresh = await get_event(bot.db, row["id"])
        await edit_announcement(bot, guild, fresh)
        if by == fresh["requester_id"]:
            return True
        why = CANCEL_WHY.get(reason, CANCEL_WHY_DEFAULT)
        await tell_or_log(
            bot,
            guild,
            guild.get_member(fresh["requester_id"]),
            fresh,
            DM_CANCELLED.format(title=fresh["title"], guild=guild.name, why=why)
            + (CANCEL_NOTE.format(note=kept) if kept else ""),
        )
        return True


async def apply_decision(
    bot: Any,
    guild: Any,
    event_id: int,
    status: str,
    actor: Any,
    reason: str | None = None,
    *,
    via: str = VIA_DISCORD,
) -> tuple[str, Any]:
    """Approve or deny, once, whoever gets the lock first: (what to say, the settled row)."""
    async with event_lock(bot, event_id):
        row = await get_event(bot.db, event_id)
        if row is None:
            return (NO_SUCH_EVENT, None)
        if not can_transition(row["status"], status):
            return (ALREADY_DECIDED.format(event_id=event_id, status=row["status"]), None)
        await set_status(
            bot.db, event_id, status, decided_by=getattr(actor, "id", actor), deny_reason=reason
        )
        if status in TERMINAL_STATUSES:
            drop_lock(bot, event_id)
        await log_action(
            bot,
            guild,
            kind_via(f"event.{status}", via),
            actor=actor,
            target=row["requester_id"],
            reason=reason,
            details={"event_id": event_id, "title": row["title"], "via": via},
        )
        fresh = await get_event(bot.db, event_id)
        requester = guild.get_member(row["requester_id"])
        why_not: str | None = None
        message_id: int | None = None
        if status == APPROVED:
            made, why_not = await create_scheduled_event(bot, guild, fresh)
            fresh = await get_event(bot.db, event_id)
            ping_role_id = bot.store.get(guild.id, "events_ping_role_id")
            message_id = await post_to_announce(
                bot,
                guild,
                fresh,
                announce_text(
                    ping_role_id,
                    has_scheduled=made is not None,
                    event_url=getattr(made, "url", None),
                ),
                card_for(fresh),
                "announce",
            )
            if message_id is not None:
                await set_announced(bot.db, event_id, message_id)
                fresh = await get_event(bot.db, event_id)
        await tell_requester(guild, requester, fresh, status, reason)
        name = getattr(requester, "display_name", str(row["requester_id"]))
        await rename_channel(bot, guild, fresh, status, name)
        if status == DENIED:
            return (DENIED_SAID, fresh)
        return (APPROVED_SAID.format(extra=approve_extra(why_not, message_id)), fresh)


async def tell_requester(
    guild: Any, requester: Any, row: Any, status: str, reason: str | None
) -> None:
    if status == DENIED:
        await dm(
            requester,
            DM_DENIED.format(title=row["title"], guild=guild.name, reason=reason or "none given"),
            card_for(row),
        )
        return
    starts = parse_ts(row["starts_at"])
    await dm(
        requester,
        DM_APPROVED.format(
            title=row["title"],
            guild=guild.name,
            stamp=f"<t:{int(starts.timestamp())}:F>" if starts else "soon",
        ),
        card_for(row),
    )


def approve_extra(why_not: str | None, message_id: int | None) -> str:
    parts = []
    if why_not == "test_mode":
        parts.append(
            "Test mode is on, so no real Discord scheduled event was made — the log says "
            "`event.would_create_scheduled`."
        )
    elif why_not == "turned_off":
        parts.append("Scheduled events are turned off in **Settings**.")
    elif why_not is not None:
        parts.append("Discord refused to make the scheduled event — the log says why.")
    if message_id is None:
        parts.append("Nothing was announced publicly; the log says why.")
    return " ".join(parts) or "The event is announced and the requester has been told."


async def make_review_channel(bot: Any, guild: Any, row: Any, actor: Any, category: Any) -> Any:
    """The staff-only room one proposal is reviewed in, or None once the failure is recorded."""
    staff = bot.store.staff_roles(guild)
    if not staff:
        log.warning("events: no staff roles resolve, so %s is admin-only", row["id"])
    try:
        return await guild.create_text_channel(
            channel_name(PENDING, getattr(actor, "display_name", str(actor)), row["title"]),
            category=category,
            overwrites=review_overwrites(guild, staff, getattr(guild, "me", None), actor),
            reason=f"Black Bloc event {row['id']}",
        )
    except NETWORK_ERRORS as exc:
        log.warning("events: could not make a review channel for %s: %s", row["id"], exc)
        await set_status(bot.db, row["id"], CANCELLED)
        await log_action(
            bot,
            guild,
            "event.channel_failed",
            target=actor,
            details={"event_id": row["id"], "reason": f"{type(exc).__name__}: {exc}"},
        )
        return None


async def post_review_card(bot: Any, guild: Any, row: Any, channel: Any, view: Any) -> int | None:
    """Where the card actually went, so the reply can say so."""
    target = card_channel(bot, channel)
    if target is None:
        await log_action(
            bot,
            guild,
            "event.would_post_card",
            details={"event_id": row["id"], "channel_id": channel.id},
        )
        return None
    try:
        message = await target.send(
            embed=card_for(row), view=view, allowed_mentions=discord.AllowedMentions.none()
        )
    except Exception as exc:
        log.warning("events: could not post the card for %s: %s", row["id"], exc)
        await log_action(
            bot,
            guild,
            "event.card_failed",
            details={"event_id": row["id"], "reason": f"{type(exc).__name__}: {exc}"},
        )
        return None
    await set_review(bot.db, row["id"], channel.id, message.id, target.id)
    return target.id


async def submit_event(
    bot: Any,
    guild: Any,
    actor: Any,
    fields: EventFields,
    *,
    review_view: Any = None,
    via: str = VIA_DISCORD,
) -> tuple[str, Any]:
    """One proposal, whichever door it came through: a row, a room, a card and the sentence."""
    category, where = events_category(bot, guild)
    if where in CATEGORY_TROUBLE:
        return (CATEGORY_TROUBLE[where], None)
    event_id = await create_event(
        bot.db,
        guild.id,
        getattr(actor, "id", actor),
        title=fields.title,
        description=fields.description,
        where=fields.where,
        starts_at=fields.starts,
        finishes_at=ends_at(fields.starts, fields.minutes),
    )
    row = await get_event(bot.db, event_id)
    channel = await make_review_channel(bot, guild, row, actor, category)
    if channel is None:
        return (CANNOT_CREATE, None)
    await set_review(bot.db, event_id, channel.id, None)
    await log_action(
        bot,
        guild,
        kind_via("event.created", via),
        actor=actor,
        target=actor,
        details={
            "event_id": event_id,
            "title": fields.title,
            "channel_id": channel.id,
            "via": via,
        },
    )
    row = await get_event(bot.db, event_id)
    posted = await post_review_card(
        bot, guild, row, channel, review_view(event_id) if review_view is not None else None
    )
    if posted is None:
        said = SUBMITTED_NO_CARD
    elif posted == channel.id:
        said = SUBMITTED_HERE
    else:
        said = SUBMITTED_TEST
    return (
        SUBMITTED.format(title=fields.title, where=said.format(channel=f"<#{channel.id}>")),
        await get_event(bot.db, event_id),
    )


def may_cancel(store: Any, row: Any, actor: Any) -> bool:
    """The requester-or-staff rule, so nothing renders a move the shared path would refuse."""
    if row is None or row["status"] not in OPEN_STATUSES:
        return False
    return row["requester_id"] == getattr(actor, "id", actor) or store.is_staff(actor)


async def cancel_for(
    bot: Any,
    guild: Any,
    row: Any,
    actor: Any,
    *,
    note: Any = None,
    reason: Any = None,
    via: str = VIA_DISCORD,
) -> tuple[str, Any]:
    """Calling one off through either door — the cancel AND the rename the site never did."""
    actor_id = getattr(actor, "id", actor)
    why = str(reason or f"cancelled_by_{actor_id}")
    if not await cancel_event(bot, guild, row, why, by=actor_id, note=note, via=via):
        fresh = await get_event(bot.db, row["id"])
        status = fresh["status"] if fresh is not None else CANCELLED
        return (NOT_OPEN.format(event_id=row["id"], status=status), None)
    fresh = await get_event(bot.db, row["id"])
    member = guild.get_member(fresh["requester_id"])
    await rename_channel(
        bot, guild, fresh, CANCELLED, getattr(member, "display_name", str(fresh["requester_id"]))
    )
    return (CANCELLED_SAID.format(event_id=row["id"]), fresh)


def wanted_event_id(given: Any) -> int | None:
    """`#12`, `12`, or nothing Black Bloc can read."""
    digits = str(given or "").strip().lstrip("#")
    return int(digits) if digits.isdigit() else None


def event_line(row: Any) -> str:
    starts = parse_ts(row["starts_at"])
    where = f" · <#{row['review_channel_id']}>" if row["review_channel_id"] else ""
    when = f"<t:{int(starts.timestamp())}:R>" if starts else "at an unreadable time"
    return (
        f"**#{row['id']}** {clamp(row['title'], 60)} — {row['status']} · {when}"
        f" · {describe_duration(duration_minutes(row))}{where}"
    )


def list_lines(rows: Any, staff_roles: Any) -> list[str]:
    """What `/event list` wrote, now the staff half of the panel's embed."""
    lines = [f"**staff (who may approve)** — {staff_roles_sentence(staff_roles)}"]
    lines.extend(event_line(row) for row in rows)
    if not staff_roles:
        lines.append(NO_STAFF_WARNING)
    return lines


def counts_of(rows: Any) -> dict[str, int]:
    found = dict.fromkeys(OPEN_STATUSES, 0)
    for row in rows:
        status = row["status"]
        if status in found:
            found[status] += 1
    return found


def counts_line(counts: dict[str, int]) -> str:
    return " · ".join(f"**{counts.get(status, 0)}** {status}" for status in OPEN_STATUSES)


class EventMove(NamedTuple):
    action: str
    label: str
    style: str
    needs_modal: bool = False


MOVE_TARGETS: dict[str, str] = {"approve": APPROVED, "deny": DENIED, "cancel": CANCELLED}
APPROVE = EventMove("approve", "Approve", "success")
APPROVE_AFTER_ALL = EventMove("approve", "Approve after all", "success")
DENY = EventMove("deny", "Deny", "danger", needs_modal=True)
CALL_IT_OFF = EventMove("cancel", "Call it off", "danger", needs_modal=True)

CARD_BUTTONS: dict[str, tuple[EventMove, ...]] = {
    PENDING: (APPROVE, DENY, CALL_IT_OFF),
    APPROVED: (CALL_IT_OFF,),
    LIVE: (CALL_IT_OFF,),
    DENIED: (APPROVE_AFTER_ALL,),
    DONE: (),
    CANCELLED: (),
}


def card_buttons(
    status: Any, *, may_cancel_here: bool = True, room_resolves: bool = True
) -> tuple[EventMove, ...]:
    """§C's table as data: only what TRANSITIONS allows and the guards would let through."""
    text = str(status or "")
    if text == DENIED and not room_resolves:
        return ()
    found = CARD_BUTTONS.get(text, ())
    if not may_cancel_here:
        return tuple(one for one in found if one.action != "cancel")
    return found


def card_footer_override(status: Any, *, room_resolves: bool = True) -> str | None:
    text = str(status or "")
    if text == DENIED and not room_resolves:
        return DENIED_ROOM_GONE
    if not CARD_BUTTONS.get(text):
        return NO_MOVES_LEFT.format(status=text)
    return None


def option_label(row: Any) -> str:
    """A select option's label, clamped to Discord's 100-character cap."""
    prefix = f"#{row['id']} · {row['status']} · "
    return prefix + clamp(row["title"], max(0, SELECT_OPTION_LIMIT - len(prefix)))


def pick_placeholder(shown: int, total: int) -> str:
    return capped_placeholder(shown, total, pick=PICK_AN_EVENT)


def site_page_url(origin: Any) -> str | None:
    return library_site_page_url(origin, "events")


def review_channel_url(guild_id: Any, channel_id: Any) -> str:
    return CHANNEL_URL.format(guild_id=int(guild_id), channel_id=int(channel_id))


def panel_minutes(store: Any, guild_id: int) -> int:
    return library_panel_minutes(store, guild_id, PANEL_MINUTES_KEY)


def panel_shows_own_list(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, PANEL_OWN_LIST_KEY))


def default_minutes(store: Any, guild_id: int) -> int:
    return int(store.get(guild_id, DEFAULT_MINUTES_KEY) or DEFAULT_DURATION_MINUTES)


def guild_zone(store: Any, guild_id: int) -> str:
    return str(store.get(guild_id, DEFAULT_TIMEZONE_KEY) or DEFAULT_TZ)


def zone_choices(store: Any, guild_id: int) -> list[str]:
    stored = str(store.get(guild_id, TIMEZONE_CHOICES_KEY) or "")
    return [one.strip() for one in stored.split(",") if one.strip()]


def minute_step(store: Any, guild_id: int) -> int:
    return int(store.get(guild_id, TIME_STEP_KEY) or 15)


def where_aliases(store: Any, guild_id: int) -> str:
    return str(store.get(guild_id, WHERE_ALIASES_KEY) or WHERE_ALIASES)


def link_check_mode(store: Any, guild_id: int) -> str:
    return str(store.get(guild_id, WHERE_CHECK_KEY) or WHERE_CHECK_MODE).strip().lower()


def link_check_seconds(store: Any, guild_id: int) -> int:
    return int(store.get(guild_id, WHERE_CHECK_SECONDS_KEY) or WHERE_CHECK_SECONDS)


def zone_line(name: str, *, chosen: bool) -> str:
    """`/timezone show`, verbatim, as the line the member panel opens with."""
    return (TZ_SHOW if chosen else TZ_SHOW_DEFAULT).format(tz=name, now=local_time(name))


def when_line(when: datetime, tz_name: str) -> str:
    """Both readings of one typed time: theirs, and the one every other client renders."""
    return STARTS_AT.format(local=local_time(tz_name, when), tz=tz_name, stamp=stamp(when))


async def set_zone(db: Any, user_id: int, given: Any) -> tuple[bool, str]:
    """The zone modal's whole job: store it, or refuse in words with what it might have been."""
    name = str(given or "").strip()
    if not is_known(name):
        near = suggest(name, 5)
        said = UNKNOWN_TZ.format(given=clamp(name, 60) or "(nothing)")
        if near:
            said += " " + DID_YOU_MEAN.format(names=", ".join(f"`{one}`" for one in near))
        return (False, said)
    await set_timezone(db, user_id, name)
    return (True, TZ_SET.format(tz=name, now=local_time(name)))


async def stored_zone(db: Any, user_id: int, fallback: Any = DEFAULT_TZ) -> tuple[str, bool]:
    chosen = await stored_timezone(db, user_id)
    if chosen is not None:
        return (chosen, True)
    wanted = str(fallback or "").strip()
    return (wanted if is_known(wanted) else DEFAULT_TZ, False)


SETTINGS_KEYS = (
    "events_mode",
    "events_category_id",
    "events_announce_channel_id",
    "events_ping_role_id",
    "events_create_scheduled",
    "events_channel_retention_days",
    "events_max_late_minutes",
)


def settings_lines(store: Any, guild: Any, health: Any = ()) -> list[str]:
    """What `/event settings` printed, now the sub-panel's embed."""
    category_id = store.get(guild.id, "events_category_id")
    announce_id = store.get(guild.id, "events_announce_channel_id")
    role_id = store.get(guild.id, "events_ping_role_id")
    return [
        f"**mode** — {store.get(guild.id, 'events_mode')}",
        "**category** — " + (f"<#{category_id}>" if category_id else "not set"),
        "**announce channel** — " + (f"<#{announce_id}>" if announce_id else "not set"),
        "**ping role** — " + (f"<@&{role_id}>" if role_id else "nobody"),
        f"**scheduled events** — {store.get(guild.id, 'events_create_scheduled')}",
        f"**channels kept** — {store.get(guild.id, 'events_channel_retention_days')} day(s)",
        f"**announced up to** — {store.get(guild.id, 'events_max_late_minutes')} minute(s) "
        "after it should have started",
        f"**staff (who may approve)** — {staff_roles_sentence(store.staff_roles(guild))}",
        *health,
    ]


NUMBERS_LABELS: dict[str, str] = {
    "retention": f"Days a finished channel is kept ({EVENTS_RETENTION_MIN_DAYS}–"
    f"{EVENTS_RETENTION_MAX_DAYS})",
    "late": f"Minutes late it may still be announced (0–{EVENTS_LATE_CEILING_MINUTES})",
}
NOT_A_NUMBER = (
    "**{given}** is not a whole number, so nothing was changed. {label} takes a number between "
    "{low} and {high}."
)
OUT_OF_BOUNDS = (
    "**{given}** is outside what Discord and Black Bloc allow, so nothing was changed. {label} "
    "takes a number between {low} and {high}."
)
NUMBER_BOUNDS: dict[str, tuple[str, int, int]] = {
    "events_channel_retention_days": (
        "Days a finished channel is kept",
        EVENTS_RETENTION_MIN_DAYS,
        EVENTS_RETENTION_MAX_DAYS,
    ),
    "events_max_late_minutes": (
        "Minutes late it may still be announced",
        0,
        EVENTS_LATE_CEILING_MINUTES,
    ),
}


def checked_numbers(retention: Any, late: Any) -> tuple[dict[str, int] | None, str]:
    """The same bounds `/event settings` clamped by, now that a modal types them free-hand."""
    wanted: dict[str, int] = {}
    for key, given in (
        ("events_channel_retention_days", retention),
        ("events_max_late_minutes", late),
    ):
        label, low, high = NUMBER_BOUNDS[key]
        text = str(given or "").strip()
        if not text.isdigit():
            return None, NOT_A_NUMBER.format(
                given=clamp(text, 40) or "(nothing)", label=label, low=low, high=high
            )
        value = int(text)
        if value < low or value > high:
            return None, OUT_OF_BOUNDS.format(given=value, label=label, low=low, high=high)
        wanted[key] = value
    return wanted, ""


async def write_settings(
    store: Any, guild_id: int, actor_id: int | None, changes: dict[str, Any]
) -> dict[str, Any]:
    """One write per key the panel actually touched; `None` means clear, as the old flags did."""
    changed: dict[str, Any] = {}
    for key, value in changes.items():
        if key not in SETTINGS_KEYS:
            continue
        if value is None:
            await store.clear(guild_id, key)
            changed[key] = None
        else:
            changed[key] = await store.set(guild_id, key, value, by=actor_id)
    return changed
