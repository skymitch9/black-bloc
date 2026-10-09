"""A run's time: read as typed, shown back the speedrun way."""

from __future__ import annotations

import re

from .model import PointsError

MAX_SECONDS = 100 * 3600

GIVEN_LIMIT = 40

NUMBER = r"\d+(?:\.\d+)?"

COLONS = re.compile(rf"^(?:(\d+):)?(?:(\d+):)({NUMBER})$")

PLAIN = re.compile(rf"^{NUMBER}$")

UNIT = re.compile(rf"({NUMBER})\s*([a-z]+)\s*")

UNITS = {
    "h": 3600,
    "hr": 3600,
    "hrs": 3600,
    "hour": 3600,
    "hours": 3600,
    "m": 60,
    "min": 60,
    "mins": 60,
    "minute": 60,
    "minutes": 60,
    "s": 1,
    "sec": 1,
    "secs": 1,
    "second": 1,
    "seconds": 1,
}

ORDER = (3600, 60, 1)


def _colons(text: str) -> float | None:
    found = COLONS.match(text)
    if found is None:
        return None
    hours, minutes, seconds = found.groups()
    if float(seconds) >= 60 or (hours is not None and int(minutes) >= 60):
        return None
    return int(hours or 0) * 3600 + int(minutes) * 60 + float(seconds)


def _units(text: str) -> float | None:
    total = 0.0
    at = 0
    seen: list[int] = []
    for found in UNIT.finditer(text):
        if found.start() != at:
            return None
        size = UNITS.get(found.group(2))
        if size is None or (seen and ORDER.index(size) <= ORDER.index(seen[-1])):
            return None
        seen.append(size)
        total += float(found.group(1)) * size
        at = found.end()
    return total if seen and at == len(text) else None


def seconds_of(given: object) -> float:
    """`1:23:45.67`, `23:45`, `45.2` or `1h 2m 3s` as seconds; anything else refuses."""
    text = " ".join(str(given or "").lower().split())
    if not text:
        raise PointsError("no_time")
    if PLAIN.match(text):
        found: float | None = float(text)
    else:
        found = _colons(text.replace(" ", ""))
        if found is None:
            found = _units(text)
    if found is None or found <= 0 or found > MAX_SECONDS:
        raise PointsError("bad_time", given=str(given)[:GIVEN_LIMIT])
    return round(found, 3)


def shown(seconds: float) -> str:
    """`1:23:45.67` with hours, `23:45` without, hundredths only when the run has them."""
    hundredths = round(float(seconds) * 100)
    whole, part = divmod(hundredths, 100)
    hours, rest = divmod(int(whole), 3600)
    minutes, secs = divmod(rest, 60)
    tail = f".{part:02d}" if part else ""
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}{tail}"
    return f"{minutes}:{secs:02d}{tail}"
