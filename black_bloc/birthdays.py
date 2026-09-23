from __future__ import annotations

import logging
import re
from calendar import isleap, monthrange
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone
from typing import Any, NamedTuple
from zoneinfo import ZoneInfo

from .panels import panel_minutes as library_panel_minutes
from .settings_store import (
    BIRTHDAY_COLOR,
    BIRTHDAY_POST_FAILED_KEY,
    BIRTHDAY_POST_MISSING_KEY,
    BIRTHDAY_POST_NOBODY_KEY,
    BIRTHDAY_POST_OFF_KEY,
    BIRTHDAY_POST_POSTED_KEY,
    BIRTHDAY_POST_REHEARSED_KEY,
    BIRTHDAY_POST_SKIPPED_KEY,
    BIRTHDAY_POST_WORDS,
    BIRTHDAY_TEMPLATE,
    BIRTHDAY_TZ,
    HEX_COLOR,
)

log = logging.getLogger(__name__)

FALLBACK_ZONE = timezone(timedelta(hours=-7), "America/Phoenix")
DEFAULT_COLOR_VALUE = 0x4EEFFF
DESCRIPTION_LIMIT = 2000
MESSAGE_LIMIT = 1900
NEXT_LIMIT = 5

PANEL_MINUTES_KEY = "birthday_panel_minutes"
PANEL_NEXT_KEY = "birthday_panel_next_for_members"
PANEL_LOOKUP_KEY = "birthday_panel_lookup"

PANEL_TITLE = "Birthdays"
PANEL_INTRO = "Tell Black Bloc when your birthday is, and see whose is coming up."
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /birthday again"
PANEL_NEXT_HEADING = "**Next birthdays**"
PANEL_NEXT_IS_STAFF_ONLY = (
    "The list of birthdays coming up is for staff in this server, so it is not shown here."
)
MODE_WARNINGS: dict[str, str] = {
    "off": (
        "⚠️ Birthday wishes are **off**, so nothing is posted on the day yet. Your birthday is "
        "still stored, and staff can turn wishes on."
    ),
    "shadow": (
        "⚠️ Birthday wishes are in **shadow** — the day is written to the log but nothing is "
        "posted yet. Staff can turn wishes on."
    ),
}
DATE_MODAL_TITLE_LIMIT = 45
DATE_MINE_TITLE = "Your birthday"
DATE_THEIRS_TITLE = "Set {who}'s birthday"
DATE_LABEL = "Your birthday — MM-DD, or MM-DD-YYYY"
DATE_PLACEHOLDER = "09-15   or   09-15-1994"
DATE_INPUT_LIMIT = 10
DATE_UNREADABLE = (
    "Black Bloc could not read that as a date. Write it as **MM-DD** — `09-15` — or add the "
    "year as **MM-DD-YYYY** — `09-15-1994`. The year is optional, and leaving it out keeps "
    "your age private."
)
LOOKUP_PLACEHOLDER = "Look someone up…"
MONTH_PLACEHOLDER = "List a month…"
EVERY_MONTH = "Every month"
MODE_PLACEHOLDER = "Wishes are…"

MONTH_NAMES: tuple[str, ...] = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


@dataclass(frozen=True)
class Upcoming:
    user_id: int
    when: datetime
    year: int | None


def zone_for(name: Any) -> Any:
    """The member's zone, falling back to the server's when the name is unusable."""
    for candidate in (str(name or "").strip(), BIRTHDAY_TZ):
        if not candidate:
            continue
        try:
            return ZoneInfo(candidate)
        except Exception as exc:
            log.warning("birthdays: zone %r is unusable (%s); falling back", candidate, exc)
    return FALLBACK_ZONE


def clamp_month_day(month: Any, day: Any) -> tuple[int, int]:
    """Any pair of numbers turned into a date that exists in a leap year."""
    try:
        m = int(month)
        d = int(day)
    except (TypeError, ValueError):
        return (1, 1)
    m = max(1, min(m, 12))
    d = max(1, min(d, 29 if m == 2 else monthrange(2024, m)[1]))
    return (m, d)


def date_problem(month: Any, day: Any) -> str | None:
    """The sentence to answer with when that month and day are not a real date."""
    try:
        m = int(month)
        d = int(day)
    except (TypeError, ValueError):
        return "A birthday needs a month between 1 and 12 and a day, both as whole numbers."
    if not 1 <= m <= 12:
        return f"There is no month **{m}** — months run from 1 (January) to 12 (December)."
    longest = 29 if m == 2 else monthrange(2024, m)[1]
    if not 1 <= d <= longest:
        return (
            f"**{MONTH_NAMES[m - 1]}** has no day **{d}** — it runs from 1 to {longest}. "
            "Check the day and run the command again."
        )
    return None


def year_problem(year: Any, today: date) -> str | None:
    if year is None:
        return None
    try:
        value = int(year)
    except (TypeError, ValueError):
        return "The birth year has to be a whole number, like 1994."
    if not 1900 <= value <= today.year:
        return (
            f"**{value}** is not a birth year Black Bloc can use — it takes years from 1900 to "
            f"{today.year}. Leave the year out to keep your age private."
        )
    return None


def observed(month: int, day: int, year: int) -> tuple[int, int]:
    """February 29 is kept on February 28 in the years that do not have it."""
    if month == 2 and day == 29 and not isleap(year):
        return (2, 28)
    return (month, day)


def celebrates_today(month: Any, day: Any, today: date) -> bool:
    m, d = clamp_month_day(month, day)
    return observed(m, d, today.year) == (today.month, today.day)


def next_occurrence(month: Any, day: Any, tz: Any, now: datetime | None = None) -> datetime:
    """Midnight of the next time that birthday comes round, in that member's own zone."""
    zone = tz if hasattr(tz, "utcoffset") else zone_for(tz)
    moment = (now or datetime.now(UTC)).astimezone(zone)
    m, d = clamp_month_day(month, day)
    today = moment.date()
    for year in (today.year, today.year + 1):
        om, od = observed(m, d, year)
        when = date(year, om, od)
        if when >= today:
            return datetime.combine(when, time(0, 0), tzinfo=zone)
    return datetime.combine(date(today.year + 1, m, d), time(0, 0), tzinfo=zone)


def local_today(tz: Any, now: datetime | None = None) -> date:
    zone = tz if hasattr(tz, "utcoffset") else zone_for(tz)
    return (now or datetime.now(UTC)).astimezone(zone).date()


def age(year: Any, today: date) -> int | None:
    """How old they turn in `today`'s year, or None when no year is stored."""
    if year in (None, ""):
        return None
    try:
        value = int(year)
    except (TypeError, ValueError):
        return None
    turned = today.year - value
    return turned if 0 <= turned <= 150 else None


def parse_color(value: Any) -> int:
    """The embed colour as an int; anything unreadable falls back to the incumbent's."""
    match = HEX_COLOR.match(str(value or "").strip())
    if match is None:
        log.warning("birthdays: colour %r is not a hex colour; using %s", value, BIRTHDAY_COLOR)
        return DEFAULT_COLOR_VALUE
    return int(match.group(1), 16)


def render_description(template: str, name: str, age_value: int | None = None) -> str:
    """The one line the embed carries; a broken template falls back to the default."""
    shown = "" if age_value is None else str(age_value)
    try:
        text = str(template).format(name=name, age=shown)
    except Exception as exc:
        log.warning(
            "birthdays: template %r could not be rendered (%s); using the default", template, exc
        )
        text = BIRTHDAY_TEMPLATE.format(name=name, age=shown)
    return text[:DESCRIPTION_LIMIT]


def upcoming(entries: Any, now: datetime | None = None, limit: int = 5) -> list[Upcoming]:
    """The next birthdays in each member's own zone, soonest first."""
    moment = now or datetime.now(UTC)
    found = [
        Upcoming(
            user_id=int(entry["user_id"]),
            when=next_occurrence(entry["month"], entry["day"], entry.get("tz"), moment),
            year=entry.get("year"),
        )
        for entry in entries or ()
    ]
    found.sort(key=lambda u: (u.when.astimezone(UTC), u.user_id))
    return found[: max(0, int(limit))] if limit else found


def stamp(when: datetime, style: str = "D") -> str:
    return f"<t:{int(when.timestamp())}:{style}>"


def month_day_text(month: Any, day: Any) -> str:
    m, d = clamp_month_day(month, day)
    return f"{MONTH_NAMES[m - 1]} {d}"


DATE_PARTS = re.compile(r"[-/. ]+")


def parse_birthday_input(text: Any) -> tuple[int, int, int | None] | None:
    """`MM-DD` or `MM-DD-YYYY` typed any of four ways; None when it cannot be read at all."""
    parts = [piece for piece in DATE_PARTS.split(str(text or "").strip()) if piece]
    if len(parts) not in (2, 3) or not all(piece.isdigit() for piece in parts):
        return None
    numbers = [int(piece) for piece in parts]
    if len(numbers) == 2:
        return (numbers[0], numbers[1], None)
    return (numbers[0], numbers[1], numbers[2])


def date_modal_title(mine: bool, name: Any = "") -> str:
    """Discord refuses a modal title over 45 characters, and display names are arbitrary."""
    if mine:
        return DATE_MINE_TITLE
    return DATE_THEIRS_TITLE.format(who=name)[:DATE_MODAL_TITLE_LIMIT]


def stored_prefill(month: Any, day: Any, year: Any) -> str:
    return f"{int(month):02d}-{int(day):02d}" + (f"-{int(year)}" if year else "")


def chunked(lines: list[str], limit: int = MESSAGE_LIMIT) -> list[str]:
    """The lines packed into as few messages as Discord's length cap allows."""
    pages: list[str] = []
    current = ""
    for line in lines:
        piece = line[:limit]
        if current and len(current) + len(piece) + 1 > limit:
            pages.append(current)
            current = piece
        else:
            current = f"{current}\n{piece}" if current else piece
    if current:
        pages.append(current)
    return pages


class PanelButton(NamedTuple):
    action: str
    label: str
    style: str
    needs_modal: bool = False


SET_MINE = PanelButton("set", "Set my birthday", "primary", needs_modal=True)
CHANGE_MINE = PanelButton("set", "Change my birthday", "primary", needs_modal=True)
REMOVE_MINE = PanelButton("remove", "Remove", "danger")
OPT_OUT = PanelButton("optout", "Opt out", "secondary")
OPT_IN = PanelButton("optin", "Opt in", "success")
REFRESH = PanelButton("refresh", "Refresh", "secondary")

PANEL_BUTTONS: dict[tuple[bool, bool], tuple[PanelButton, ...]] = {
    (False, False): (SET_MINE, REFRESH),
    (True, False): (CHANGE_MINE, REMOVE_MINE, OPT_OUT, REFRESH),
    (True, True): (CHANGE_MINE, REMOVE_MINE, OPT_IN, REFRESH),
}


def panel_buttons(has_date: bool, opted_out: bool) -> tuple[PanelButton, ...]:
    key = (bool(has_date), bool(opted_out))
    return PANEL_BUTTONS.get(key, PANEL_BUTTONS[(False, False)])


def panel_minutes(store: Any, guild_id: int) -> int:
    return library_panel_minutes(store, guild_id, PANEL_MINUTES_KEY)


def panel_shows_next(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, PANEL_NEXT_KEY))


def panel_allows_lookup(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, PANEL_LOOKUP_KEY))


def stored_sentence(
    whose: str, month: Any, day: Any, year: Any, zone: str, when: datetime
) -> str:
    return (
        f"{whose} birthday is **{month_day_text(month, day)}**"
        + (f" ({year})" if year else "")
        + f". Black Bloc posts it at midnight in **{zone}**, and the next one is "
        + stamp(when, "D")
        + "."
    )


def card_lines(
    name: str,
    month: Any,
    day: Any,
    year: Any,
    zone: str,
    when: datetime,
    years: int | None,
    opted_in: bool,
    mine: bool = False,
) -> list[str]:
    lines = [
        f"**{name}** — {month_day_text(month, day)}"
        + (f" ({year})" if year and mine else "")
        + (f", turning {years}" if years is not None else ""),
        f"Next: {stamp(when, 'D')} ({stamp(when, 'R')}), midnight in **{zone}**",
    ]
    if not opted_in:
        lines.append(
            "You are **opted out**, so nothing will be posted."
            if mine
            else "They are **opted out**, so nothing will be posted."
        )
    return lines


def upcoming_lines(entries: list[dict[str, Any]], items: list[Upcoming]) -> list[str]:
    by_id = {entry["user_id"]: entry for entry in entries}
    return [
        f"· <@{item.user_id}> — "
        f"{month_day_text(by_id[item.user_id]['month'], by_id[item.user_id]['day'])} "
        f"({stamp(item.when, 'D')}, {stamp(item.when, 'R')})"
        for item in items
    ]


def month_lines(rows: Any) -> list[str]:
    lines: list[str] = []
    seen: int | None = None
    for row in rows or ():
        if row["month"] != seen:
            seen = row["month"]
            lines.append(f"**{MONTH_NAMES[seen - 1]}**")
        marks = "" if row["opted_in"] else " · opted out"
        lines.append(f"· {row['day']} — <@{row['user_id']}> ({row['source']}{marks})")
    return lines


def stored_line(totals: dict[str, int]) -> str:
    return (
        f"**stored** — {totals['stored']} ({totals['opted_in']} opted in · "
        f"{totals['imported']} imported · {totals['self']} set by the person)"
    )


def status_lines(values: dict[str, Any]) -> list[str]:
    channel_id = values.get("channel_id")
    role_id = values.get("role_id")
    return [
        f"**mode** — {values['mode']}",
        f"**channel** — {f'<#{channel_id}>' if channel_id else 'not set'}",
        f"**template** — `{values['template']}`",
        f"**colour** — {values['color']}",
        f"**role** — {f'<@&{role_id}>' if role_id else 'none'}"
        + (" (test mode gives no roles)" if values.get("test_mode") else ""),
        f"**ages shown** — {values['show_age']}",
        stored_line(values["totals"]),
        f"**staff** — {values['staff']}",
        f"**last sweep** — {values['last_run_at'] or 'not yet'} "
        f"(every {values['loop_minutes']} minutes)",
        f"**last error** — {values['last_error'] or 'none'}",
    ]



POSTED = "posted"
MISSING = "missing"
FAILED = "failed"
SKIPPED = "skipped"


@dataclass(frozen=True)
class PostedToday:
    mode: str
    again: bool = False
    posted: int = 0
    skipped: int = 0
    missing: int = 0
    failed: int = 0
    channel: str = ""
    said: str = ""

    @property
    def celebrants(self) -> int:
        return self.posted + self.skipped + self.missing + self.failed

    def answer(self) -> dict[str, Any]:
        return {
            "posted": self.posted,
            "skipped": self.skipped,
            "missing": self.missing,
            "failed": self.failed,
            "mode": self.mode,
            "again": self.again,
            "said": self.said,
        }


def post_word(store: Any, guild_id: int, key: str) -> str:
    return str(store.get(guild_id, key) or "").strip() or BIRTHDAY_POST_WORDS[key]


def post_line(store: Any, guild_id: int, key: str, **values: Any) -> str:
    try:
        return post_word(store, guild_id, key).format(**values)
    except (IndexError, KeyError, ValueError) as exc:
        log.warning("birthdays: %s would not fill (%s); the shipped wording was used", key, exc)
        return BIRTHDAY_POST_WORDS[key].format(**values)


def channel_words(guild: Any, channel_id: Any) -> str:
    if not channel_id:
        return ""
    channel = guild.get_channel(int(channel_id)) if guild is not None else None
    name = getattr(channel, "name", None)
    return f"#{name}" if name else f"<#{int(channel_id)}>"


def post_today_said(store: Any, guild_id: int, found: PostedToday) -> str:
    if found.mode == "off":
        return post_word(store, guild_id, BIRTHDAY_POST_OFF_KEY)
    if not found.celebrants:
        return post_word(store, guild_id, BIRTHDAY_POST_NOBODY_KEY)
    lines = []
    if found.posted:
        key = BIRTHDAY_POST_POSTED_KEY if found.mode == "on" else BIRTHDAY_POST_REHEARSED_KEY
        lines.append(post_line(store, guild_id, key, n=found.posted, channel=found.channel))
    for key, count in (
        (BIRTHDAY_POST_SKIPPED_KEY, found.skipped),
        (BIRTHDAY_POST_MISSING_KEY, found.missing),
        (BIRTHDAY_POST_FAILED_KEY, found.failed),
    ):
        if count:
            lines.append(post_line(store, guild_id, key, n=count))
    return "\n".join(lines)


async def member_zone_name(db: Any, user_id: int) -> str:
    """The member's own zone when `/timezone` stored one, else the server's."""
    try:
        cur = await db.conn.execute(
            "SELECT tz FROM user_timezones WHERE user_id = ?", (int(user_id),)
        )
        row = await cur.fetchone()
    except Exception as exc:
        log.warning("birthdays: could not read the zone for %s (%s)", user_id, exc)
        return BIRTHDAY_TZ
    stored = row["tz"] if row is not None else None
    return str(stored) if stored else BIRTHDAY_TZ
