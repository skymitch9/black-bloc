"""The shapes every sports adapter answers in."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

NFL = "nfl"
NBA = "nba"
MLB = "mlb"
NHL = "nhl"
NCAAM = "ncaam"
NCAAW = "ncaaw"
LEAGUES: tuple[str, ...] = (NFL, NBA, MLB, NHL, NCAAM, NCAAW)
PRO_LEAGUES: tuple[str, ...] = (NFL, NBA, MLB, NHL)
COLLEGE: tuple[str, ...] = (NCAAM, NCAAW)

TEAM = "team"
SCHOOL = "school"
PLAYER = "player"
KINDS: tuple[str, ...] = (TEAM, SCHOOL, PLAYER)

LIVE = "live"
FINAL = "final"
SCHEDULED = "scheduled"
STATUSES: tuple[str, ...] = (LIVE, FINAL, SCHEDULED)

ESPN = "espn"
NCAA = "ncaa"
NHL_API = "nhl"
NBA_API = "nba"
MLB_API = "mlb"
SOURCES: tuple[str, ...] = (ESPN, NCAA, NHL_API, NBA_API, MLB_API)
SOURCE_NAMES: dict[str, str] = {
    ESPN: "ESPN",
    NCAA: "NCAA (ncaa-api)",
    NHL_API: "NHL",
    NBA_API: "NBA",
    MLB_API: "MLB",
}

SLOT_A = "a"
SLOT_B = "b"


@dataclass(frozen=True)
class Team:
    ext_id: str
    name: str
    short: str | None
    league: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Player:
    ext_id: str
    name: str
    team_ext_id: str | None
    league: str
    short: str | None = None


@dataclass(frozen=True)
class Game:
    ext_id: str
    source_key: str
    a_ext_id: str | None
    b_ext_id: str | None
    a_score: int | None
    b_score: int | None
    status: str
    starts_at: str | None
    period_words: str | None = None
    round: int | None = None


@dataclass
class Bracket:
    league: str
    season: str
    games: list[Game] = field(default_factory=list)
    links: dict[str, tuple[str, str]] = field(default_factory=dict)
    seeds: dict[str, int] = field(default_factory=dict)
    best_of: dict[str, int] = field(default_factory=dict)
    names: dict[str, str] = field(default_factory=dict)

    def game(self, source_key: str) -> Game | None:
        return next((one for one in self.games if one.source_key == source_key), None)


@dataclass(frozen=True)
class Found:
    ok: bool
    why: str | None = None
    value: Any = None
    via: str | None = None


def found(value: Any, via: str | None = None) -> Found:
    return Found(True, None, value, via)


def failed(why: str, via: str | None = None) -> Found:
    return Found(False, str(why)[:300], None, via)


def number(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def text(value: Any) -> str | None:
    found_text = " ".join(str(value or "").split())
    return found_text or None


def aliases_of(name: str, *values: Any) -> tuple[str, ...]:
    """The other names a thing goes by, once each, never its own name again."""
    found_names = (text(one) for one in values)
    return tuple(dict.fromkeys(one for one in found_names if one and one != name))


__all__ = [
    "COLLEGE",
    "ESPN",
    "FINAL",
    "KINDS",
    "LEAGUES",
    "LIVE",
    "MLB",
    "MLB_API",
    "NBA",
    "NBA_API",
    "NCAA",
    "NCAAM",
    "NCAAW",
    "NFL",
    "NHL",
    "NHL_API",
    "PLAYER",
    "PRO_LEAGUES",
    "SCHEDULED",
    "SCHOOL",
    "SLOT_A",
    "SLOT_B",
    "SOURCES",
    "SOURCE_NAMES",
    "STATUSES",
    "TEAM",
    "Bracket",
    "Found",
    "Game",
    "Player",
    "Team",
    "aliases_of",
    "failed",
    "found",
    "number",
    "text",
]
