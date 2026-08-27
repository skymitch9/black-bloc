from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import discord

from . import timezones

log = logging.getLogger(__name__)

QUESTION_LIMIT = 300
LABEL_LIMIT = 55
MAX_NATIVE_OPTIONS = 10
MAX_PANEL_OPTIONS = 25
MIN_OPTIONS = 2
MIN_HOURS = 1
MAX_HOURS = 32 * 24
DEFAULT_HOURS = 24
RATING_SLOTS = 5
BAR_CELLS = 20
FULL = "█"
EMPTY = "░"
LABEL_COLUMN = 18
THREAD_NAME_LIMIT = 100

SINGLE = "single"
CHECKBOX = "checkbox"
YESNO = "yesno"
RATING = "rating"
DATE = "date"
FREE_TEXT = "text"
NUMBER = "number"
RANKED = "ranked"
NATIVE_KINDS = (SINGLE, CHECKBOX, YESNO, RATING)
PANEL_KINDS = (DATE,)
KNOWN_KINDS = NATIVE_KINDS + PANEL_KINDS
LATER_KINDS = (FREE_TEXT, NUMBER, RANKED)
KINDS = KNOWN_KINDS + LATER_KINDS
GENERATED_KINDS = (YESNO, RATING, DATE)
MULTI_KINDS = (CHECKBOX, DATE)
BUTTONS_UP_TO = 5

NATIVE = "native"
PANEL = "panel"
SURFACES = (NATIVE, PANEL)

LIVE = "live"
AT_CLOSE = "close"
RESULTS_CHOICES = (LIVE, AT_CLOSE)

DATE_PLAIN = "plain"
DATE_TIMESTAMP = "timestamp"
DATE_LABEL_FORMS = (DATE_PLAIN, DATE_TIMESTAMP)
MIN_SLOTS = 2
MAX_SLOTS = MAX_PANEL_OPTIONS
STEP_HOURS = "hours"
STEP_DAYS = "days"
DATE_STEPS = (STEP_HOURS, STEP_DAYS)
MAX_STEP = 168
DAY_FORMAT = "%Y-%m-%d"
DAY_TIME_FORMAT = "%Y-%m-%d %H:%M"
DAY_LABEL = "%a %d %b"

DAILY = "daily"
WEEKLY = "weekly"
MONTHLY = "monthly"
CADENCES = (DAILY, WEEKLY, MONTHLY)
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
WEEKDAY_NAMES = (
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
)
MAX_MONTH_DAY = 28
CLOCK_FORMAT = "%H:%M"

DRAFT = "draft"
PENDING_REVIEW = "pending_review"
OPEN = "open"
CLOSED = "closed"
ARCHIVED = "archived"
DENIED = "denied"
CANCELLED = "cancelled"
RECURRING = "recurring"
STATUSES = (DRAFT, PENDING_REVIEW, OPEN, CLOSED, ARCHIVED, DENIED, CANCELLED, RECURRING)
OPEN_STATUSES = (DRAFT, PENDING_REVIEW, OPEN)
SETTLED_STATUSES = (CLOSED, CANCELLED, DENIED, ARCHIVED)

TRANSITIONS: dict[str, tuple[str, ...]] = {
    DRAFT: (PENDING_REVIEW, OPEN, CANCELLED),
    PENDING_REVIEW: (OPEN, DENIED, CANCELLED),
    OPEN: (CLOSED, CANCELLED),
    CLOSED: (ARCHIVED,),
    CANCELLED: (ARCHIVED,),
    DENIED: (),
    ARCHIVED: (),
    RECURRING: (CANCELLED,),
}

TERMINAL_STATUSES = tuple(status for status, allowed in TRANSITIONS.items() if not allowed)

COLOURS: dict[str, int] = {
    DRAFT: 0x5865F2,
    PENDING_REVIEW: 0x5865F2,
    OPEN: 0x57F287,
    CLOSED: 0x99AAB5,
    ARCHIVED: 0x99AAB5,
    DENIED: 0xED4245,
    CANCELLED: 0xED4245,
    RECURRING: 0x5865F2,
}

KIND_NAMES: dict[str, str] = {
    SINGLE: "single choice",
    CHECKBOX: "checkbox",
    YESNO: "yes / no",
    RATING: "rating 1-5",
    DATE: "date",
    FREE_TEXT: "free text",
    NUMBER: "number",
    RANKED: "ranked choice",
}

LATER_KIND_NAMES: dict[str, str] = {
    FREE_TEXT: "A **free text** poll",
    NUMBER: "A **number** poll",
    RANKED: "A **ranked choice** poll",
}

NEXT_UPDATE = "that kind of poll arrives with the next update"

KIND_NOT_YET = (
    "{what} needs a voting surface Black Bloc does not have yet, so nothing was posted — "
    f"{NEXT_UPDATE}. Until then a poll can be single choice, checkbox, yes/no, a "
    "1-5 rating or a date."
)
TOO_MANY = (
    "**{count}** options is more than the {limit} Black Bloc can put on one poll, so nothing was "
    "posted. Cut it to {limit} or fewer and run it again."
)

PANEL_BECAUSE_ANONYMOUS = (
    "Discord's own polls list everybody who voted, so an **anonymous** one cannot be theirs"
)
PANEL_BECAUSE_HIDDEN = (
    "Discord's own polls show the bars as the votes come in and there is no way to hide them"
)
PANEL_BECAUSE_LONG = "**{count}** options is more than the {limit} a Discord poll carries"
PANEL_SAID = (
    "This one is a Black Bloc panel rather than a Discord poll, because {why}. People vote with "
    "the buttons under it; everything else works the same."
)

NO_QUESTION = (
    "A poll needs a question, so nothing was posted. Put the thing you are asking in the "
    "question box — it is the heading everybody votes under."
)
QUESTION_TOO_LONG = (
    "That question is **{given}** characters and Discord allows {limit}, so nothing was posted. "
    "Shorten it and run the command again; the long version can go in the channel underneath."
)
TOO_FEW_OPTIONS = (
    "A poll needs at least {limit} options and this one has **{given}**, so nothing was posted. "
    "Write them separated by `|` — `Pizza | Tacos | Neither` is three."
)
LABEL_TOO_LONG = (
    "The option **{given}** is longer than the {limit} characters Discord allows on a poll "
    "answer, so nothing was posted. Shorten that one and run the command again."
)
DUPLICATE_OPTION = (
    "**{given}** is in the options twice, so nothing was posted — two identical answers split "
    "the votes and nobody can tell them apart. Remove one of them and try again."
)
BAD_HOURS = (
    "**{given}** is not a length Black Bloc can give a poll, so nothing was posted. Discord "
    "counts poll length in whole hours, from {low} to {high} (32 days)."
)

BAD_START = (
    "**{given}** is not a date Black Bloc can read, so nothing was posted. Write it as "
    "`2026-09-05`, or `2026-09-05 19:00` when the time of day matters."
)
BAD_SLOTS = (
    "A date poll needs between {low} and {high} slots and this one asked for **{given}**, so "
    "nothing was posted. Say how many with `slots:`."
)
BAD_STEP = (
    "**{given}** is not a gap Black Bloc can leave between two slots, so nothing was posted. It "
    "counts in whole {unit}, from 1 to {high}."
)
BAD_STEP_UNIT = (
    "**{given}** is not a unit a date poll can step by, so nothing was posted. It is `hours` or "
    "`days`."
)
DATE_NEEDS_A_START = (
    "A date poll needs a start date, so nothing was posted. Give it one with "
    "`start:2026-09-05` and Black Bloc lays the slots out from there."
)

PANEL_HOW_ONE = "Press an option to vote. Pressing a different one moves your vote."
PANEL_HOW_MANY = "Press everything that works for you. Pressing one again takes it back."
PANEL_HIDDEN = "Hidden until this closes, so nobody's vote is swayed by the bars."
PANEL_ANONYMOUS = (
    "Nobody is told who pressed what — Black Bloc does not keep your name against a vote here."
)
PANEL_VOTE = "Vote"
PANEL_CLEAR = "Clear my vote"

VOTED_ONE = "Your vote is on **{label}**."
VOTED_MANY = "You have {labels}."
VOTE_CLEARED = "Your vote is cleared, so nothing of yours counts towards this poll now."
VOTE_NOT_OPEN = (
    "That poll is **{status}**, so nothing was counted. The result on the message is the final one."
)
VOTE_GONE = (
    "Black Bloc has no record of that poll any more, so nothing was counted. It may have been "
    "archived — the polls page on the dashboard keeps the result."
)
PICK_SOMETHING = (
    "Nothing was picked, so nothing changed. Choose at least one option, or use "
    f"**{PANEL_CLEAR}** to take your vote back."
)

BAD_CLOCK = (
    "**{given}** is not a time of day Black Bloc can read, so nothing was saved. Write it on the "
    "24-hour clock — `09:00`, `19:30`."
)
BAD_WEEKDAY = (
    "**{given}** is not a day of the week, so nothing was saved. A weekly poll runs on one of "
    "{known}."
)
BAD_MONTH_DAY = (
    "**{given}** is not a day of the month Black Bloc will use, so nothing was saved. It counts "
    "from 1 to {limit} — every month has those, and a poll set for the 31st would skip February."
)
BAD_ZONE = (
    "**{given}** is not a timezone this machine knows, so nothing was saved. Write it the tzdata "
    "way — `America/Phoenix`, `Europe/London`."
)
RECUR_NOT_A_DATE = (
    "A **date** poll cannot recur, so nothing was saved — its slots are fixed days, and the second "
    "time round it would be asking about a day that has been and gone. Run `/poll create "
    "kind:date` when you need one, or recur a checkbox poll with the days written on it."
)
RECUR_NONE = "No poll is set to repeat. `/poll recur create` starts one."
RECUR_SAVED = "**{question}** will run {cadence}. The first one opens <t:{when}:R>."
RECUR_PAUSED = "**{question}** is paused. Nothing opens until it is started again."
RECUR_RESUMED = "**{question}** is running again. The next one opens <t:{when}:R>."
RECUR_DELETED = "**{question}** will not run again. Polls it already opened are untouched."
NOT_A_RECURRENCE = (
    "Black Bloc has no repeating poll **#{poll_id}**, so nothing was done. `/poll recur list` has "
    "the ones it knows about."
)
CADENCE_DAILY = "every day at {clock} {zone}"
CADENCE_WEEKLY = "every {day} at {clock} {zone}"
CADENCE_MONTHLY = "on the {day}{ordinal} of each month at {clock} {zone}"

RESULTS_TITLE = "{question}"
NO_VOTES = "Nobody voted."
WINNER_MARK = "  <- winner"
TIED = "It is a tie between {names}."
AVERAGE = "Average rating: **{mean}** out of {top}."


class NeedsPanel(ValueError):
    """The poll asked for something only the (not yet built) panel surface can do."""


def clamp(text: Any, limit: int) -> str:
    return str(text or "").strip()[:limit]


def can_transition(before: Any, after: Any) -> bool:
    return str(after) in TRANSITIONS.get(str(before), ())


def split_options(text: Any) -> list[str]:
    """`Pizza | Tacos` is two options; blank entries are dropped, not counted."""
    return [part.strip() for part in str(text or "").split("|") if part.strip()]


def options_for(kind: str, text: Any) -> list[str]:
    """Yes/no and rating generate their own answers; everything else is what was typed."""
    if kind == YESNO:
        return ["Yes", "No"]
    if kind == RATING:
        return [str(number) for number in range(1, RATING_SLOTS + 1)]
    return split_options(text)


def validate(question: Any, labels: Any, hours: Any) -> str | None:
    """The refusal sentence, or None when the poll is postable."""
    asked = str(question or "").strip()
    if not asked:
        return NO_QUESTION
    if len(asked) > QUESTION_LIMIT:
        return QUESTION_TOO_LONG.format(given=len(asked), limit=QUESTION_LIMIT)
    found = list(labels or ())
    if len(found) < MIN_OPTIONS:
        return TOO_FEW_OPTIONS.format(limit=MIN_OPTIONS, given=len(found))
    seen: set[str] = set()
    for label in found:
        if len(label) > LABEL_LIMIT:
            return LABEL_TOO_LONG.format(given=clamp(label, 60), limit=LABEL_LIMIT)
        folded = label.casefold()
        if folded in seen:
            return DUPLICATE_OPTION.format(given=clamp(label, 60))
        seen.add(folded)
    if not whole_hours(hours):
        return BAD_HOURS.format(given=clamp(hours, 40), low=MIN_HOURS, high=MAX_HOURS)
    return None


def whole_hours(hours: Any) -> bool:
    return whole(hours, MIN_HOURS, MAX_HOURS)


def parse_day(text: Any, tz_name: Any = timezones.DEFAULT_TZ) -> datetime | None:
    """`2026-09-05`, or `2026-09-05 19:00`, read in the server's zone and returned as UTC."""
    zi = timezones.zone(tz_name) or timezones.zone(timezones.DEFAULT_TZ)
    typed = str(text or "").strip()
    for shape in (DAY_TIME_FORMAT, DAY_FORMAT):
        try:
            naive = datetime.strptime(typed, shape)
        except ValueError:
            continue
        return naive.replace(tzinfo=zi).astimezone(UTC)
    return None


def clock_label(when: datetime) -> str:
    """`7 pm`, `7:30 pm` — the twelve-hour form, built by hand because Windows has no `%-I`."""
    hour = when.hour % 12 or 12
    minute = f":{when.minute:02d}" if when.minute else ""
    return f"{hour}{minute} {'am' if when.hour < 12 else 'pm'}"


def slot_label(
    when: datetime, *, with_time: bool, form: str = DATE_PLAIN, tz_name: Any = timezones.DEFAULT_TZ
) -> str:
    """The answer text for one date slot, in whichever form the server has asked for."""
    if form == DATE_TIMESTAMP:
        return f"<t:{int(when.timestamp())}:{'f' if with_time else 'D'}>"
    zi = timezones.zone(tz_name) or timezones.zone(timezones.DEFAULT_TZ)
    local = when.astimezone(zi)
    day = local.strftime(DAY_LABEL)
    return f"{day} · {clock_label(local)}" if with_time else day


def date_trouble(start: Any, slots: Any, step: Any, unit: Any) -> str | None:
    """The refusal sentence for a date poll's own arguments, or None when they work."""
    if not str(start or "").strip():
        return DATE_NEEDS_A_START
    if parse_day(start) is None:
        return BAD_START.format(given=clamp(start, 40))
    if str(unit) not in DATE_STEPS:
        return BAD_STEP_UNIT.format(given=clamp(unit, 40))
    if not whole(slots, MIN_SLOTS, MAX_SLOTS):
        return BAD_SLOTS.format(given=clamp(slots, 40), low=MIN_SLOTS, high=MAX_SLOTS)
    if not whole(step, 1, MAX_STEP):
        return BAD_STEP.format(given=clamp(step, 40), unit=unit, high=MAX_STEP)
    return None


def date_slots(
    start: Any,
    slots: Any,
    step: Any,
    unit: Any = STEP_DAYS,
    *,
    form: str = DATE_PLAIN,
    tz_name: Any = timezones.DEFAULT_TZ,
) -> list[dict[str, str]]:
    """One row per candidate slot: the answer text, and the instant it stands for."""
    first = parse_day(start, tz_name)
    if first is None:
        return []
    gap = timedelta(hours=int(step)) if str(unit) == STEP_HOURS else timedelta(days=int(step))
    zi = timezones.zone(tz_name) or timezones.zone(timezones.DEFAULT_TZ)
    with_time = str(unit) == STEP_HOURS or first.astimezone(zi).time() != datetime.min.time()
    return [
        {
            "label": slot_label(first + gap * n, with_time=with_time, form=form, tz_name=tz_name),
            "value": (first + gap * n).isoformat(),
        }
        for n in range(int(slots))
    ]


def parse_clock(text: Any) -> tuple[int, int] | None:
    try:
        found = datetime.strptime(str(text or "").strip(), CLOCK_FORMAT)
    except ValueError:
        return None
    return (found.hour, found.minute)


def cadence_token(every: Any, day: Any = None) -> str | None:
    """`daily`, `weekly:sat`, `monthly:12` — one string the row carries and the loop reads."""
    kind = str(every or "").strip().lower()
    if kind == DAILY:
        return DAILY
    if kind == WEEKLY:
        wanted = str(day or "").strip().lower()[:3]
        return f"{WEEKLY}:{wanted}" if wanted in WEEKDAYS else None
    if kind == MONTHLY:
        try:
            at = int(str(day or "").strip())
        except (TypeError, ValueError):
            return None
        return f"{MONTHLY}:{at}" if 1 <= at <= MAX_MONTH_DAY else None
    return None


def cadence_trouble(every: Any, day: Any, at_text: Any, tz_name: Any) -> str | None:
    """The refusal sentence for a recurrence's own arguments, or None when they work."""
    kind = str(every or "").strip().lower()
    if kind == WEEKLY and cadence_token(kind, day) is None:
        return BAD_WEEKDAY.format(given=clamp(day, 40) or "nothing", known=", ".join(WEEKDAYS))
    if kind == MONTHLY and cadence_token(kind, day) is None:
        return BAD_MONTH_DAY.format(given=clamp(day, 40) or "nothing", limit=MAX_MONTH_DAY)
    if cadence_token(kind, day) is None:
        return BAD_WEEKDAY.format(given=clamp(every, 40) or "nothing", known=", ".join(CADENCES))
    if parse_clock(at_text) is None:
        return BAD_CLOCK.format(given=clamp(at_text, 40) or "nothing")
    if not timezones.is_known(tz_name):
        return BAD_ZONE.format(given=clamp(tz_name, 60) or "nothing")
    return None


def next_occurrence(
    token: Any, at_text: Any, tz_name: Any, after: datetime | None = None
) -> datetime | None:
    """The next instant this cadence comes round, read in its own zone and returned as UTC."""
    clock = parse_clock(at_text)
    zi = timezones.zone(tz_name)
    if clock is None or zi is None:
        return None
    kind, _, detail = str(token or "").partition(":")
    moment = (after or datetime.now(UTC)).astimezone(zi)
    when = moment.replace(hour=clock[0], minute=clock[1], second=0, microsecond=0)
    if kind == DAILY:
        if when <= moment:
            when += timedelta(days=1)
    elif kind == WEEKLY:
        if detail not in WEEKDAYS:
            return None
        when += timedelta(days=(WEEKDAYS.index(detail) - when.weekday()) % 7)
        if when <= moment:
            when += timedelta(days=7)
    elif kind == MONTHLY:
        if not detail.isdigit() or not 1 <= int(detail) <= MAX_MONTH_DAY:
            return None
        when = when.replace(day=int(detail))
        if when <= moment:
            year, month = divmod(when.month, 12)
            when = when.replace(year=when.year + year, month=month + 1)
    else:
        return None
    return when.astimezone(UTC)


def ordinal(number: Any) -> str:
    value = int(number)
    if 11 <= value % 100 <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")


def describe_cadence(token: Any, at_text: Any, tz_name: Any) -> str:
    kind, _, detail = str(token or "").partition(":")
    clock = str(at_text or "?")
    zone_name = str(tz_name or timezones.DEFAULT_TZ)
    if kind == WEEKLY and detail in WEEKDAYS:
        return CADENCE_WEEKLY.format(
            day=WEEKDAY_NAMES[WEEKDAYS.index(detail)], clock=clock, zone=zone_name
        )
    if kind == MONTHLY and detail.isdigit():
        return CADENCE_MONTHLY.format(
            day=int(detail), ordinal=ordinal(detail), clock=clock, zone=zone_name
        )
    return CADENCE_DAILY.format(clock=clock, zone=zone_name)


def whole(value: Any, low: int, high: int) -> bool:
    if isinstance(value, bool) or not isinstance(value, int):
        return False
    return low <= value <= high


def surface_for(kind: str, anonymous: bool, results: str, slot_count: int) -> str:
    """`native`, `panel`, or a refusal sentence for a kind no surface carries yet."""
    if kind in LATER_KINDS:
        raise NeedsPanel(
            KIND_NOT_YET.format(what=LATER_KIND_NAMES.get(kind, f"A **{kind}** poll"))
        )
    if kind not in KNOWN_KINDS:
        raise NeedsPanel(KIND_NOT_YET.format(what=f"A **{clamp(kind, 40)}** poll"))
    if int(slot_count) > MAX_PANEL_OPTIONS:
        raise NeedsPanel(TOO_MANY.format(count=int(slot_count), limit=MAX_PANEL_OPTIONS))
    return PANEL if panel_reason(anonymous, results, slot_count) else NATIVE


def panel_reason(anonymous: bool, results: str, slot_count: int) -> str | None:
    """Why this poll cannot be Discord's own — the first thing that rules native out."""
    if anonymous:
        return PANEL_BECAUSE_ANONYMOUS
    if results == AT_CLOSE:
        return PANEL_BECAUSE_HIDDEN
    if int(slot_count) > MAX_NATIVE_OPTIONS:
        return PANEL_BECAUSE_LONG.format(count=int(slot_count), limit=MAX_NATIVE_OPTIONS)
    return None


def panel_note(anonymous: bool, results: str, slot_count: int) -> str | None:
    why = panel_reason(anonymous, results, slot_count)
    return PANEL_SAID.format(why=why) if why else None


def is_multi(kind: str) -> bool:
    return kind in MULTI_KINDS


def closes_at(hours: int, now: datetime | None = None) -> datetime:
    return (now or datetime.now(UTC)) + timedelta(hours=max(int(hours), MIN_HOURS))


def describe_hours(hours: Any) -> str:
    total = max(int(hours or 0), 0)
    days, rest = divmod(total, 24)
    if days and rest:
        return f"{days}d {rest}h"
    if days:
        return f"{days}d"
    return f"{total}h"


def bar(votes: Any, total: Any, cells: int = BAR_CELLS) -> str:
    counted = max(int(votes or 0), 0)
    everyone = max(int(total or 0), 0)
    filled = round(cells * counted / everyone) if everyone else 0
    filled = max(0, min(cells, filled))
    return FULL * filled + EMPTY * (cells - filled)


def share(votes: Any, total: Any) -> int:
    everyone = max(int(total or 0), 0)
    if not everyone:
        return 0
    return round(100 * max(int(votes or 0), 0) / everyone)


def ranked(counts: Any) -> list[dict[str, Any]]:
    """Most votes first; ties keep the order the options were written in."""
    rows = [dict(row) for row in counts or ()]
    return sorted(rows, key=lambda row: (-int(row.get("votes") or 0), int(row.get("position", 0))))


def winners(counts: Any) -> list[dict[str, Any]]:
    rows = ranked(counts)
    if not rows or not int(rows[0].get("votes") or 0):
        return []
    best = int(rows[0]["votes"])
    return [row for row in rows if int(row.get("votes") or 0) == best]


def results_text(counts: Any, total: Any) -> str:
    """The bar chart every surface shows, in one monospaced block."""
    rows = ranked(counts)
    if not rows:
        return NO_VOTES
    top = winners(counts)
    top_positions = {int(row["position"]) for row in top}
    alone = len(top) == 1
    lines: list[str] = []
    for row in rows:
        label = clamp(row.get("label"), LABEL_COLUMN).ljust(LABEL_COLUMN)
        votes = int(row.get("votes") or 0)
        mark = WINNER_MARK if alone and int(row["position"]) in top_positions else ""
        lines.append(
            f"{label} {bar(votes, total)} {votes:>4}  ({share(votes, total):>3}%){mark}"
        )
    return "\n".join(lines)


def average_rating(counts: Any) -> float | None:
    """The mean of a rating poll, or None when nothing numeric was voted for."""
    total = 0
    weighted = 0.0
    for row in counts or ():
        try:
            value = float(str(row.get("label")).strip())
        except (TypeError, ValueError):
            return None
        votes = max(int(row.get("votes") or 0), 0)
        total += votes
        weighted += value * votes
    if not total:
        return None
    return round(weighted / total, 2)


def results_embed(
    *,
    poll_id: Any,
    question: str,
    counts: Any,
    total: Any,
    status: str = CLOSED,
    kind: str = SINGLE,
    closed_at: Any = None,
    approximate: bool = False,
) -> discord.Embed:
    """The one results card: the slash command, the loop and the review card all use it."""
    embed = discord.Embed(
        title=clamp(question, QUESTION_LIMIT),
        description=f"```\n{results_text(counts, total)}\n```",
        colour=COLOURS.get(status, COLOURS[CLOSED]),
    )
    counted = max(int(total or 0), 0)
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(
        name="Votes", value=f"{counted}{' so far' if approximate else ''}", inline=True
    )
    if kind == RATING:
        mean = average_rating(counts)
        if mean is not None:
            embed.add_field(
                name="Average", value=AVERAGE.format(mean=mean, top=RATING_SLOTS), inline=False
            )
    won = winners(counts)
    if len(won) > 1:
        names = ", ".join(f"**{clamp(row['label'], LABEL_LIMIT)}**" for row in won)
        embed.add_field(name="Winner", value=TIED.format(names=names), inline=False)
    if closed_at:
        embed.add_field(name="Closed", value=str(closed_at), inline=False)
    embed.set_footer(text=f"Poll #{poll_id}")
    return embed


def panel_text(counts: Any, voters: Any, *, hidden: bool) -> str:
    """The block under a panel poll: the bars, or the options with the bars withheld."""
    if not hidden:
        return results_text(counts, voters)
    rows = list(counts or ())
    if not rows:
        return NO_VOTES
    return "\n".join(
        f"{n}. {clamp(row.get('label'), LABEL_LIMIT)}" for n, row in enumerate(rows, 1)
    )


def panel_embed(
    *,
    poll_id: Any,
    question: str,
    counts: Any,
    voters: Any,
    kind: str = SINGLE,
    multi: bool = False,
    anonymous: bool = False,
    hidden: bool = False,
    status: str = OPEN,
    closes_at: datetime | None = None,
) -> discord.Embed:
    """The panel's own card. It carries the live totals unless the poll hides them."""
    withholding = hidden and status == OPEN
    embed = discord.Embed(
        title=clamp(question, QUESTION_LIMIT),
        description=f"```\n{panel_text(counts, voters, hidden=withholding)}\n```",
        colour=COLOURS.get(status, COLOURS[OPEN]),
    )
    counted = max(int(voters or 0), 0)
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="Voters", value=str(counted), inline=True)
    embed.add_field(name="How", value=PANEL_HOW_MANY if multi else PANEL_HOW_ONE, inline=False)
    if withholding:
        embed.add_field(name="Results", value=PANEL_HIDDEN, inline=False)
    if anonymous:
        embed.add_field(name="Anonymous", value=PANEL_ANONYMOUS, inline=False)
    if kind == RATING and not withholding:
        mean = average_rating(counts)
        if mean is not None:
            embed.add_field(
                name="Average", value=AVERAGE.format(mean=mean, top=RATING_SLOTS), inline=False
            )
    if closes_at is not None and status == OPEN:
        embed.add_field(name="Closes", value=f"<t:{int(closes_at.timestamp())}:R>", inline=False)
    embed.set_footer(text=f"Poll #{poll_id}")
    return embed


def voted_text(labels: Any, *, multi: bool) -> str:
    chosen = [clamp(label, LABEL_LIMIT) for label in labels or ()]
    if not chosen:
        return VOTE_CLEARED
    if not multi:
        return VOTED_ONE.format(label=chosen[0])
    return VOTED_MANY.format(labels=", ".join(f"**{one}**" for one in chosen))


def review_card(
    *,
    poll_id: Any,
    question: str,
    creator_id: int,
    kind: str,
    labels: Any,
    hours: Any,
    status: str = PENDING_REVIEW,
    deny_reason: str | None = None,
) -> discord.Embed:
    """The card staff approve or deny, and the one the creator is DM'd."""
    embed = discord.Embed(
        title=clamp(question, QUESTION_LIMIT),
        colour=COLOURS.get(status, COLOURS[PENDING_REVIEW]),
    )
    embed.add_field(name="Who", value=f"<@{creator_id}>", inline=True)
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="Kind", value=KIND_NAMES.get(kind, kind), inline=True)
    embed.add_field(name="Open for", value=describe_hours(hours), inline=True)
    shown = "\n".join(
        f"{n}. {clamp(label, LABEL_LIMIT)}" for n, label in enumerate(labels or (), 1)
    )
    embed.add_field(name="Options", value=shown or "none", inline=False)
    if deny_reason:
        embed.add_field(name="Why not", value=clamp(deny_reason, 1024), inline=False)
    embed.set_footer(text=f"Poll #{poll_id}")
    return embed


def mentions(ping_role_id: Any = None) -> discord.AllowedMentions:
    """Nothing a poll's author typed may ping; only the configured role may."""
    return discord.AllowedMentions(
        everyone=False,
        users=False,
        roles=[discord.Object(int(ping_role_id))] if ping_role_id else False,
    )


def open_text(creator_id: Any, ping_role_id: Any = None) -> str:
    prefix = f"<@&{ping_role_id}> " if ping_role_id else ""
    return f"{prefix}<@{creator_id}> started a poll."


def reminder_text(question: str, when: Any = None) -> str:
    tail = f" It closes {when}." if when else ""
    return f"Last call on **{clamp(question, 80)}** — the poll is still open.{tail}"


def closed_text(question: str) -> str:
    return f"**{clamp(question, 80)}** is closed. Here is how it went."


def thread_name(question: str) -> str:
    return clamp(question, THREAD_NAME_LIMIT) or "Poll"


def counts_from_options(rows: Any) -> list[dict[str, Any]]:
    """The stored options turned into the shape every renderer and the API read."""
    return [
        {
            "position": int(row["position"]),
            "label": str(row["label"]),
            "votes": int(row["final_votes"] or 0),
        }
        for row in rows or ()
    ]
