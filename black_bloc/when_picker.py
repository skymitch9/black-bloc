from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import discord

from .command_errors import AnswersErrors
from .panels import Panel
from .timezones import DEFAULT_TZ, zone

SELECT_CAP = 25
DAY_COUNT = 24
ZONE_COUNT = 24
STEP_MIN = 5
STEP_MAX = 60
DAY_FORMAT = "%Y-%m-%d"
DAY_EXAMPLE = "2026-09-14"
START_FORMAT = "%Y-%m-%d %H:%M"

LATER_VALUE = "__later__"
OTHER_VALUE = "__other__"
LATER_LABEL = "Later — pick a date…"
OTHER_LABEL = "Other — type it…"

DAY_PLACEHOLDER = "Which day?"
HOUR_PLACEHOLDER = "Start time — hour"
MINUTE_PLACEHOLDER = "Start time — minute"
ZONE_PLACEHOLDER = "Which time zone?"
DURATION_PLACEHOLDER = "How long?"

LATER_TITLE = "Pick a date"
LATER_LABEL_FIELD = "Date — YYYY-MM-DD"
ZONE_MODAL_TITLE = "Your time zone"
ZONE_MODAL_LABEL = "Region/City — Phoenix is America/Phoenix"
ZONE_INPUT_LIMIT = 60
ZONE_BACK = "Back"

NEEDS_DAY = "a day"
NEEDS_HOUR = "an hour"
NEEDS_MINUTE = "a minute"
NEEDS_WHEN = "Pick {parts} from the dropdowns above, and the time is set."
BAD_DAY = (
    "**{given}** is not a date Black Bloc can read, so this draft has no day on it yet. Write it "
    f"as `YYYY-MM-DD` — `{DAY_EXAMPLE}` is the 14th of September — or pick one from the **Day** "
    "dropdown instead."
)

DURATIONS: tuple[tuple[int, str, str], ...] = (
    (30, "30m", "30m"),
    (45, "45m", "45m"),
    (60, "1h", "1h"),
    (90, "1h30m", "1h 30m"),
    (120, "2h", "2h"),
    (150, "2h30m", "2h 30m"),
    (180, "3h", "3h"),
    (240, "4h", "4h"),
    (300, "5h", "5h"),
    (360, "6h", "6h"),
    (480, "8h", "8h"),
    (720, "12h", "12h"),
    (1440, "24h", "All day"),
)


def parse_day(text: Any) -> date | None:
    try:
        return datetime.strptime(str(text or "").strip(), DAY_FORMAT).date()
    except ValueError:
        return None


def local_now(zone_name: Any, now: datetime | None = None) -> datetime:
    when = now or datetime.now(UTC)
    here = zone(zone_name)
    return when.astimezone(here) if here is not None else when


def local_date(zone_name: Any, now: datetime | None = None) -> date:
    return local_now(zone_name, now).date()


def clock(zone_name: Any, now: datetime | None = None) -> str:
    return hour_minute(local_now(zone_name, now))


def hour_minute(when: datetime) -> str:
    half = when.hour % 12 or 12
    return f"{half}:{when.minute:02d} {'AM' if when.hour < 12 else 'PM'}"


def hour_label(hour: int) -> str:
    half = int(hour) % 12 or 12
    return f"{half} {'AM' if int(hour) < 12 else 'PM'}"


def minute_label(minute: int) -> str:
    return f":{int(minute):02d}"


def day_label(one: date, today: date) -> str:
    if one == today:
        return f"Today · {one:%a %b %d}"
    if one == today + timedelta(days=1):
        return f"Tomorrow · {one:%a %b %d}"
    return f"{one:%a %b %d}"


def clean_step(step: Any) -> int:
    try:
        wanted = int(step)
    except (TypeError, ValueError):
        return 15
    return max(STEP_MIN, min(STEP_MAX, wanted))


def duration_for(minutes: Any) -> str:
    """The text `events.parse_duration` reads for a number of minutes, table first."""
    try:
        wanted = int(minutes)
    except (TypeError, ValueError):
        return ""
    for count, value, _label in DURATIONS:
        if count == wanted:
            return value
    return f"{wanted}m"


@dataclass
class WhenDraft:
    """What the three dropdowns and the typed date hold between renders."""

    zone: str = DEFAULT_TZ
    day: date | None = None
    hour: int | None = None
    minute: int | None = None
    later_text: str = ""

    def typed_day(self) -> date | None:
        return parse_day(self.later_text) if self.later_text else None

    def chosen_day(self) -> date | None:
        return self.typed_day() if self.later_text else self.day

    def start_text(self) -> str | None:
        chosen = self.chosen_day()
        if chosen is None or self.hour is None or self.minute is None:
            return None
        return f"{chosen:{DAY_FORMAT}} {int(self.hour):02d}:{int(self.minute):02d}"


def said_when(draft: WhenDraft) -> str:
    """`Fri Sep 12 · 7:00 PM`, or nothing at all while any of the three is still unpicked."""
    day = draft.chosen_day()
    if day is None or draft.hour is None or draft.minute is None:
        return ""
    picked = datetime(day.year, day.month, day.day, int(draft.hour), int(draft.minute))
    return f"{day:%a %b %d} · {hour_minute(picked)}"


def missing_parts(draft: WhenDraft) -> list[str]:
    parts = []
    if draft.chosen_day() is None:
        parts.append(NEEDS_DAY)
    if draft.hour is None:
        parts.append(NEEDS_HOUR)
    if draft.minute is None:
        parts.append(NEEDS_MINUTE)
    return parts


def said_list(parts: list[str]) -> str:
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def resolve(draft: WhenDraft, now: datetime | None = None) -> tuple[str | None, str]:
    """`YYYY-MM-DD HH:MM` for the cog's own validator, or the sentence saying what is missing."""
    start = draft.start_text()
    if start is not None:
        return (start, "")
    if draft.later_text and draft.typed_day() is None:
        return (None, BAD_DAY.format(given=str(draft.later_text).strip()[:80]))
    return (None, NEEDS_WHEN.format(parts=said_list(missing_parts(draft))))


def day_options(
    zone_name: Any,
    now: datetime | None = None,
    count: int = DAY_COUNT,
    picked: date | None = None,
    later: date | None = None,
) -> list[discord.SelectOption]:
    today = local_date(zone_name, now)
    try:
        wanted = max(1, min(int(count), DAY_COUNT))
    except (TypeError, ValueError):
        wanted = DAY_COUNT
    days = [today + timedelta(days=step) for step in range(wanted)]
    if later is not None and later not in days:
        days = days[:-1] + [later]
    options = [
        discord.SelectOption(
            label=day_label(one, today), value=one.isoformat(), default=(one == picked)
        )
        for one in days
    ]
    options.append(discord.SelectOption(label=LATER_LABEL, value=LATER_VALUE))
    return options


def hour_options(picked: int | None = None) -> list[discord.SelectOption]:
    return [
        discord.SelectOption(
            label=hour_label(one), value=str(one), default=(picked is not None and one == picked)
        )
        for one in range(24)
    ]


def minute_options(step: Any = 15, picked: int | None = None) -> list[discord.SelectOption]:
    wanted = clean_step(step)
    return [
        discord.SelectOption(
            label=minute_label(one), value=str(one), default=(picked is not None and one == picked)
        )
        for one in range(0, 60, wanted)
    ]


def zone_options(
    choices: Any,
    stored: str | None = None,
    guild_default: str = DEFAULT_TZ,
    now: datetime | None = None,
) -> list[discord.SelectOption]:
    names = [str(one) for one in (choices or ())][:ZONE_COUNT]
    if not names:
        names = [str(guild_default or DEFAULT_TZ)]
    if stored and stored not in names:
        names = names[:-1] + [stored] if len(names) >= ZONE_COUNT else [*names, stored]
    selected = stored or guild_default
    options = [
        discord.SelectOption(
            label=f"{name} · now {clock(name, now)}"[:100],
            value=name,
            default=(name == selected),
        )
        for name in names
    ]
    options.append(discord.SelectOption(label=OTHER_LABEL, value=OTHER_VALUE))
    return options


def duration_options(picked: Any = None) -> list[discord.SelectOption]:
    wanted = str(picked or "")
    return [
        discord.SelectOption(label=label, value=value, default=(value == wanted))
        for _minutes, value, label in DURATIONS
    ]


class DaySelect(discord.ui.Select):
    def __init__(self, draft: WhenDraft, now: datetime | None = None, row: int = 0) -> None:
        super().__init__(
            placeholder=DAY_PLACEHOLDER,
            options=day_options(
                draft.zone, now, picked=draft.chosen_day(), later=draft.typed_day()
            ),
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        draft = self.view.draft
        if self.values[0] == LATER_VALUE:
            await interaction.response.send_modal(
                LaterModal(current=draft.later_text, on_submit=self.view.take_later)
            )
            return
        draft.day = parse_day(self.values[0])
        draft.later_text = ""
        await self.view.rerender(interaction)


class HourSelect(discord.ui.Select):
    def __init__(self, draft: WhenDraft, row: int = 1) -> None:
        super().__init__(
            placeholder=HOUR_PLACEHOLDER,
            options=hour_options(draft.hour),
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.draft.hour = int(self.values[0])
        await self.view.rerender(interaction)


class MinuteSelect(discord.ui.Select):
    def __init__(self, draft: WhenDraft, step: Any = 15, row: int = 2) -> None:
        super().__init__(
            placeholder=MINUTE_PLACEHOLDER,
            options=minute_options(step, draft.minute),
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.draft.minute = int(self.values[0])
        await self.view.rerender(interaction)


class ZoneSelect(discord.ui.Select):
    def __init__(
        self,
        choices: Any,
        stored: str | None = None,
        guild_default: str = DEFAULT_TZ,
        now: datetime | None = None,
        row: int = 0,
    ) -> None:
        super().__init__(
            placeholder=ZONE_PLACEHOLDER,
            options=zone_options(choices, stored, guild_default, now),
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.values[0] == OTHER_VALUE:
            await self.view.take_other(interaction)
            return
        await self.view.take_zone(interaction, self.values[0])


class DurationSelect(discord.ui.Select):
    def __init__(self, picked: Any = None, row: int = 3) -> None:
        super().__init__(
            placeholder=DURATION_PLACEHOLDER,
            options=duration_options(picked),
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.take_duration(interaction, self.values[0])


class LaterModal(AnswersErrors, discord.ui.Modal, title=LATER_TITLE):
    """Stores what was typed and re-renders; a date it cannot read is said on the panel."""

    day = discord.ui.TextInput(label=LATER_LABEL_FIELD, placeholder=DAY_EXAMPLE, max_length=10)

    def __init__(
        self,
        *,
        current: str = "",
        on_submit: Callable[[discord.Interaction, str], Awaitable[None]],
    ) -> None:
        super().__init__()
        self.day.default = current or None
        self.takes_day = on_submit

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.takes_day(interaction, str(self.day))


class ZoneModal(AnswersErrors, discord.ui.Modal, title=ZONE_MODAL_TITLE):
    """The typed door onto all 598 zones; refusing is `events.set_zone`'s job, not this one's."""

    zone = discord.ui.TextInput(
        label=ZONE_MODAL_LABEL, placeholder=DEFAULT_TZ, max_length=ZONE_INPUT_LIMIT
    )

    def __init__(
        self,
        *,
        current: str = "",
        on_submit: Callable[[discord.Interaction, str], Awaitable[None]],
    ) -> None:
        super().__init__()
        self.zone.default = current or None
        self.takes_zone = on_submit

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.takes_zone(interaction, str(self.zone))


class BackButton(discord.ui.Button):
    def __init__(self, label: str = ZONE_BACK, row: int = 1) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=row)

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.go_back(interaction)


class ZonePanel(Panel):
    """The zone dropdown, the typed door and the way back; whose panel raised it decides Back."""

    def __init__(
        self,
        minutes: int,
        *,
        footer: str,
        choices: Any,
        stored: str | None,
        guild_default: str,
        on_pick: Callable[[discord.Interaction, str, Any], Awaitable[None]],
        on_other: Callable[[discord.Interaction, Any], Awaitable[None]],
        on_back: Callable[[discord.Interaction, Any], Awaitable[None]],
        now: datetime | None = None,
    ) -> None:
        super().__init__(minutes, footer=footer)
        self.takes_zone = on_pick
        self.takes_other = on_other
        self.goes_back = on_back
        self.add_item(ZoneSelect(choices, stored, guild_default, now))
        self.add_item(BackButton())

    async def take_zone(self, interaction: discord.Interaction, name: str) -> None:
        await self.takes_zone(interaction, name, self)

    async def take_other(self, interaction: discord.Interaction) -> None:
        await self.takes_other(interaction, self)

    async def go_back(self, interaction: discord.Interaction) -> None:
        await self.goes_back(interaction, self)


__all__ = [
    "BAD_DAY",
    "DAY_COUNT",
    "DURATIONS",
    "LATER_LABEL",
    "LATER_VALUE",
    "NEEDS_WHEN",
    "OTHER_LABEL",
    "OTHER_VALUE",
    "SELECT_CAP",
    "STEP_MAX",
    "STEP_MIN",
    "ZONE_COUNT",
    "BackButton",
    "DaySelect",
    "DurationSelect",
    "HourSelect",
    "LaterModal",
    "MinuteSelect",
    "WhenDraft",
    "ZoneModal",
    "ZonePanel",
    "ZoneSelect",
    "clean_step",
    "clock",
    "day_label",
    "day_options",
    "duration_for",
    "duration_options",
    "hour_label",
    "hour_options",
    "local_date",
    "local_now",
    "minute_options",
    "parse_day",
    "resolve",
    "said_when",
    "zone_options",
]
