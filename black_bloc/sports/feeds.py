"""Which source answers what, per league, and the fallback when the first one fails."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import date

from . import espn, http, mlb, nba, ncaa, nfl, nhl
from .model import (
    ESPN,
    MLB,
    MLB_API,
    NBA,
    NBA_API,
    NCAA,
    NCAAM,
    NCAAW,
    NFL,
    NHL,
    NHL_API,
    Found,
    failed,
)

TEAMS = "teams"
PLAYERS = "players"
BRACKET = "bracket"
SCORES = "scores"
SPLIT_START_MONTH = 8
MLB_START_MONTH = 3


@dataclass(frozen=True)
class Feed:
    primary: str
    fallback: str | None = None


FEEDS: dict[str, dict[str, Feed]] = {
    TEAMS: {
        NFL: Feed(ESPN),
        NBA: Feed(ESPN),
        MLB: Feed(ESPN, MLB_API),
        NHL: Feed(ESPN),
        NCAAM: Feed(ESPN),
        NCAAW: Feed(ESPN),
    },
    PLAYERS: {
        NFL: Feed(ESPN),
        NBA: Feed(ESPN, NBA_API),
        MLB: Feed(ESPN, MLB_API),
        NHL: Feed(ESPN),
    },
    BRACKET: {
        NFL: Feed(ESPN),
        NBA: Feed(NBA_API),
        MLB: Feed(MLB_API),
        NHL: Feed(NHL_API),
        NCAAM: Feed(NCAA),
        NCAAW: Feed(NCAA),
    },
    SCORES: {
        NFL: Feed(ESPN),
        NBA: Feed(ESPN),
        MLB: Feed(ESPN, MLB_API),
        NHL: Feed(ESPN, NHL_API),
        NCAAM: Feed(ESPN, NCAA),
        NCAAW: Feed(ESPN, NCAA),
    },
}

Call = Callable[[], Awaitable[Found]]


def feed_for(league: str, need: str = SCORES) -> Feed | None:
    return FEEDS.get(need, {}).get(league)


def current_season(league: str, today: date) -> str:
    """The season a day belongs to, in the label every adapter answers with."""
    if league == MLB:
        return str(today.year if today.month >= MLB_START_MONTH else today.year - 1)
    start = today.year if today.month >= SPLIT_START_MONTH else today.year - 1
    if league == NFL:
        return str(start)
    return f"{start}-{str(start + 1)[2:]}"


async def answered(feed: Feed | None, calls: dict[str, Call], what: str) -> Found:
    """The primary's answer, else the fallback's; both failing names both reasons."""
    if feed is None:
        return failed(f"no source has {what}")
    first = await calls[feed.primary]()
    if first.ok or feed.fallback is None:
        return replace(first, via=feed.primary)
    second = await calls[feed.fallback]()
    if second.ok:
        return replace(second, via=feed.fallback)
    return failed(f"{first.why}; then {second.why}", feed.primary)


async def teams(league: str, *, fetch: http.Fetch | None = None) -> Found:
    calls: dict[str, Call] = {
        ESPN: lambda: espn.teams(league, fetch=fetch),
        MLB_API: lambda: mlb.teams(fetch=fetch),
    }
    return await answered(feed_for(league, TEAMS), calls, f"{league} teams")


async def schools(*, fetch: http.Fetch | None = None) -> Found:
    return await answered(Feed(NCAA), {NCAA: lambda: ncaa.schools(fetch=fetch)}, "schools")


async def espn_players(league: str, fetch: http.Fetch | None) -> Found:
    listed = await espn.teams(league, fetch=fetch)
    if not listed.ok:
        return listed
    return await espn.players(league, [one.ext_id for one in listed.value], fetch=fetch)


async def players(
    league: str, *, fetch: http.Fetch | None = None, today: date | None = None
) -> Found:
    season = current_season(league, today or date.today())
    calls: dict[str, Call] = {
        ESPN: lambda: espn_players(league, fetch),
        NBA_API: lambda: nba.players(season, fetch=fetch),
        MLB_API: lambda: mlb.players(int(season[:4]), fetch=fetch),
    }
    return await answered(feed_for(league, PLAYERS), calls, f"{league} players")


async def bracket(league: str, season: str, *, fetch: http.Fetch | None = None) -> Found:
    calls: dict[str, Call] = {
        ESPN: lambda: nfl.bracket(season, fetch=fetch),
        NBA_API: lambda: nba.bracket(season, fetch=fetch),
        MLB_API: lambda: mlb.bracket(season, fetch=fetch),
        NHL_API: lambda: nhl.bracket(season, fetch=fetch),
        NCAA: lambda: ncaa.bracket(league, season, fetch=fetch),
    }
    return await answered(feed_for(league, BRACKET), calls, f"a {league} bracket")


async def scores(league: str, day: date, *, fetch: http.Fetch | None = None) -> Found:
    calls: dict[str, Call] = {
        ESPN: lambda: espn.scores(league, day, fetch=fetch),
        MLB_API: lambda: mlb.scores(day, fetch=fetch),
        NHL_API: lambda: nhl.scores(day, fetch=fetch),
        NCAA: lambda: ncaa.scores(league, day, fetch=fetch),
    }
    return await answered(feed_for(league, SCORES), calls, f"{league} scores")


__all__ = [
    "BRACKET",
    "FEEDS",
    "PLAYERS",
    "SCORES",
    "TEAMS",
    "Feed",
    "answered",
    "bracket",
    "current_season",
    "feed_for",
    "players",
    "schools",
    "scores",
    "teams",
]
