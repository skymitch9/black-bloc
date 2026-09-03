from __future__ import annotations

import json
import logging
import re
from calendar import isleap, monthrange
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta, timezone
from importlib.resources import files
from pathlib import Path
from typing import Any, NamedTuple
from zoneinfo import ZoneInfo

from .panels import panel_minutes as library_panel_minutes
from .settings_store import BIRTHDAY_COLOR, BIRTHDAY_TEMPLATE, BIRTHDAY_TZ, HEX_COLOR

log = logging.getLogger(__name__)

DATA_FILE = files("black_bloc") / "data" / "birthday_import_2026-08-05.json"
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

MONTHS: dict[str, int] = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
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

TAG_PREFIX = re.compile(r"^\s*[\[(][^\])]*[\])]\s*")
EXPORT_ROW = re.compile(
    r"^\|\s*(?P<month>[A-Za-z]+)\s*\|\s*(?P<day>\d{1,2})\s*\|\s*(?P<name>.+?)\s*\|"
    r"\s*(?P<age>\d{1,3})?\s*\|\s*$"
)

EXACT_DISPLAY_SCORE = 3
EXACT_USERNAME_SCORE = 2
CONTAINS_SCORE = 1
IMPORT_SCORE_FLOOR = 2


@dataclass(frozen=True)
class ImportRow:
    display_name: str
    month: int
    day: int
    age_shown: int | None = None


@dataclass(frozen=True)
class Candidate:
    user_id: int
    display_name: str
    username: str
    score: int


@dataclass(frozen=True)
class Match:
    status: str
    row: ImportRow
    candidates: tuple[Candidate, ...] = field(default=())

    @property
    def member_id(self) -> int | None:
        return self.candidates[0].user_id if self.status == "matched" else None


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


def year_from_age(age_shown: Any, as_of_year: int) -> int | None:
    try:
        value = int(age_shown)
    except (TypeError, ValueError):
        return None
    return as_of_year - value if 0 <= value <= 150 else None


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


def strip_tags(name: str) -> str:
    """`[Straight Hands] ShinDarkShadow` and `(Umazing) nadia` reduced to the name itself."""
    text = str(name or "").strip()
    while True:
        shorter = TAG_PREFIX.sub("", text, count=1)
        if shorter == text or not shorter:
            break
        text = shorter
    return " ".join(text.split())


def _norm(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def score_member(
    query: str, display_name: Any, username: Any, global_name: Any = None
) -> int:
    """3 for the same display name, 2 for the same username, 1 for containing the name."""
    wanted = _norm(query)
    if not wanted:
        return 0
    display = _norm(display_name)
    plain = _norm(strip_tags(display_name))
    user = _norm(username)
    globally = _norm(global_name)
    if display == wanted:
        return EXACT_DISPLAY_SCORE
    if wanted in (plain, user, globally):
        return EXACT_USERNAME_SCORE
    if any(value and wanted in value for value in (display, plain, user, globally)):
        return CONTAINS_SCORE
    return 0


def score_members(query: str, members: Any) -> list[Candidate]:
    scored = [
        Candidate(
            user_id=getattr(member, "id", 0),
            display_name=str(getattr(member, "display_name", "")),
            username=str(getattr(member, "name", "")),
            score=score_member(
                query,
                getattr(member, "display_name", None),
                getattr(member, "name", None),
                getattr(member, "global_name", None),
            ),
        )
        for member in members or ()
    ]
    hits = [c for c in scored if c.score > 0]
    hits.sort(key=lambda c: (-c.score, c.display_name.casefold()))
    return hits


def resolve(row: ImportRow, members: Any) -> Match:
    """One export row against the members Discord returned for it."""
    hits = score_members(strip_tags(row.display_name), members)
    if not hits:
        return Match("not_found", row)
    best = hits[0].score
    top = [c for c in hits if c.score == best]
    if best >= IMPORT_SCORE_FLOOR and len(top) == 1:
        return Match("matched", row, tuple(top))
    return Match("ambiguous", row, tuple(hits[:10]))


def parse_export(text: str) -> list[ImportRow]:
    """The Birthday Bot markdown table as rows; one line per person, header lines ignored."""
    rows: list[ImportRow] = []
    for line in str(text or "").splitlines():
        match = EXPORT_ROW.match(line.strip())
        if match is None:
            continue
        month = MONTHS.get(match.group("month").strip().casefold())
        if month is None:
            continue
        m, d = clamp_month_day(month, match.group("day"))
        shown = match.group("age")
        rows.append(
            ImportRow(
                display_name=" ".join(match.group("name").split()),
                month=m,
                day=d,
                age_shown=int(shown) if shown else None,
            )
        )
    return rows


def load_import_rows(path: Path | None = None) -> list[ImportRow]:
    """The committed seed rows; an unreadable file is empty rows, never a crash."""
    source = Path(path) if path is not None else DATA_FILE
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("birthdays: could not read %s (%s); no rows to import", source, exc)
        return []
    raw = payload.get("rows", []) if isinstance(payload, dict) else payload
    rows: list[ImportRow] = []
    for entry in raw or ():
        try:
            m, d = clamp_month_day(entry["month"], entry["day"])
            rows.append(
                ImportRow(
                    display_name=str(entry["display_name"]),
                    month=m,
                    day=d,
                    age_shown=entry.get("age_shown"),
                )
            )
        except Exception as exc:
            log.warning("birthdays: skipped an unreadable seed row %r (%s)", entry, exc)
    return rows


def import_as_of_year(path: Path | None = None) -> int:
    """The year the export was taken; the ±1 caveat on every imported age hangs off it."""
    source = Path(path) if path is not None else DATA_FILE
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
        return int(str(payload["exported"])[:4])
    except Exception:
        return datetime.now(UTC).year


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
        f"**last import** — {values['last_import_at'] or 'not yet'} "
        f"(every {values['import_hours']} hours)",
        f"**last import error** — {values['last_import_error'] or 'none'}",
    ]


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
