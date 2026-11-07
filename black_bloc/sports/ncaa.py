"""henrygd's ncaa-api (a wrapper of NCAA.com): the tournament bracket, scoreboards, schools."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from . import http
from .model import (
    FINAL,
    LIVE,
    NCAA,
    NCAAM,
    NCAAW,
    SCHEDULED,
    SLOT_A,
    SLOT_B,
    Bracket,
    Found,
    Game,
    Team,
    aliases_of,
    failed,
    found,
    number,
    text,
)

NAME = "NCAA (ncaa-api)"
BASE = "https://ncaa-api.henrygd.me"
SPORTS: dict[str, str] = {NCAAM: "basketball-men", NCAAW: "basketball-women"}
BRACKET_STATES = {"F": FINAL, "I": LIVE, "P": SCHEDULED}
BOARD_STATES = {"final": FINAL, "live": LIVE, "pre": SCHEDULED}
ROUND_SIZE = 100


def season_of(year: Any) -> str | None:
    """The tournament of March 2026 ends the 2025-26 season."""
    found_year = number(year)
    return None if found_year is None else f"{found_year - 1}-{str(found_year)[2:]}"


def year_of(season: str) -> int | None:
    head = number(str(season)[:4])
    if head is None:
        return None
    return head + 1 if "-" in str(season) else head


def bracket_url(league: str, year: int) -> str:
    return f"{BASE}/brackets/{SPORTS[league]}/d1/{int(year)}"


def scoreboard_url(league: str, day: date) -> str:
    return f"{BASE}/scoreboard/{SPORTS[league]}/d1/{day.strftime('%Y/%m/%d')}"


def schools_url() -> str:
    return f"{BASE}/schools-index"


def epoch(value: Any) -> str | None:
    seconds = number(value)
    if not seconds:
        return None
    return datetime.fromtimestamp(seconds, UTC).isoformat()


def clock_words(game: dict[str, Any], state: str) -> str | None:
    if state == FINAL:
        return text(game.get("finalMessage")) or "FINAL"
    if state == LIVE:
        return text(" ".join(str(game.get(one) or "") for one in ("currentPeriod", "contestClock")))
    return text(" ".join(str(game.get(one) or "") for one in ("startDate", "startTime")))


def parse_bracket(payload: Any, league: str) -> Bracket | None:
    """Every game keyed by its `bracketPositionId`, linked by `victorBracketPositionId`."""
    championships = payload.get("championships") if isinstance(payload, dict) else None
    champ = championships[0] if championships and isinstance(championships[0], dict) else None
    if champ is None:
        return None
    found_bracket = Bracket(league=league, season=season_of(champ.get("year")) or "")
    for game in champ.get("games") or []:
        position = number(game.get("bracketPositionId"))
        if position is None:
            continue
        key = str(position)
        sides = {bool(one.get("isTop")): one for one in game.get("teams") or []}
        top, bottom = sides.get(True) or {}, sides.get(False) or {}
        state = BRACKET_STATES.get(str(game.get("gameState")), SCHEDULED)
        for team in (top, bottom):
            slug = text(team.get("seoname"))
            if slug is None:
                continue
            seed = number(team.get("seed"))
            if seed is not None:
                found_bracket.seeds[slug] = seed
            found_bracket.names[slug] = text(team.get("nameShort")) or slug
        found_bracket.games.append(
            Game(
                ext_id=text(game.get("contestId")) or key,
                source_key=key,
                a_ext_id=text(top.get("seoname")),
                b_ext_id=text(bottom.get("seoname")),
                a_score=number(top.get("score")) if state != SCHEDULED else None,
                b_score=number(bottom.get("score")) if state != SCHEDULED else None,
                status=state,
                starts_at=epoch(game.get("startTimeEpoch")),
                period_words=clock_words(game, state),
                round=position // ROUND_SIZE - 1,
            )
        )
        target = number(game.get("victorBracketPositionId"))
        if target is not None:
            slot = SLOT_A if str(game.get("victorGamePosition")) == "Top" else SLOT_B
            found_bracket.links[key] = (str(target), slot)
    return found_bracket


def parse_scoreboard(payload: Any) -> list[Game]:
    found_games: list[Game] = []
    for entry in payload.get("games") or [] if isinstance(payload, dict) else []:
        game = entry.get("game") if isinstance(entry, dict) else None
        if not isinstance(game, dict) or not text(game.get("gameID")):
            continue
        home, away = game.get("home") or {}, game.get("away") or {}
        state = BOARD_STATES.get(str(game.get("gameState")), SCHEDULED)
        found_games.append(
            Game(
                ext_id=str(game["gameID"]),
                source_key=str(game["gameID"]),
                a_ext_id=text((home.get("names") or {}).get("seo")),
                b_ext_id=text((away.get("names") or {}).get("seo")),
                a_score=number(home.get("score")) if state != SCHEDULED else None,
                b_score=number(away.get("score")) if state != SCHEDULED else None,
                status=state,
                starts_at=epoch(game.get("startTimeEpoch")),
                period_words=clock_words(game, state),
            )
        )
    return found_games


def parse_schools(payload: Any) -> list[Team]:
    found_schools: list[Team] = []
    for one in payload if isinstance(payload, list) else []:
        slug, name = text(one.get("slug")), text(one.get("name"))
        if slug and name:
            found_schools.append(Team(slug, name, None, "", aliases_of(name, one.get("long"))))
    return found_schools


def named(answer: Found, what: str) -> Found:
    return failed(f"{NAME} {answer.why} for {what}", NCAA)


async def bracket(league: str, season: str, *, fetch: http.Fetch | None = None) -> Found:
    year = year_of(season)
    if year is None:
        return failed(f"{season} is not a season {NAME} can read", NCAA)
    answer = await http.get_json(bracket_url(league, year), fetch=fetch)
    if not answer.ok:
        return named(answer, f"the {year} bracket")
    parsed = parse_bracket(answer.value, league)
    if parsed is None or not parsed.games:
        return failed(f"{NAME} sent no {year} bracket", NCAA)
    return found(parsed, NCAA)


async def scores(league: str, day: date, *, fetch: http.Fetch | None = None) -> Found:
    answer = await http.get_json(scoreboard_url(league, day), fetch=fetch)
    if not answer.ok:
        return named(answer, f"the scores of {day.isoformat()}")
    return found(parse_scoreboard(answer.value), NCAA)


async def schools(*, fetch: http.Fetch | None = None) -> Found:
    answer = await http.get_json(schools_url(), fetch=fetch)
    if not answer.ok:
        return named(answer, "the schools")
    listed = parse_schools(answer.value)
    if not listed:
        return failed(f"{NAME} sent no schools", NCAA)
    return found(listed, NCAA)


__all__ = [
    "NAME",
    "bracket",
    "bracket_url",
    "parse_bracket",
    "parse_schools",
    "parse_scoreboard",
    "schools",
    "schools_url",
    "scoreboard_url",
    "scores",
    "season_of",
    "year_of",
]
