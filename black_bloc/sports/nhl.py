"""The NHL's own site API: the playoff bracket (series A to O) and a day's scores."""

from __future__ import annotations

from datetime import date
from typing import Any

from . import http
from .espn import stamp
from .model import (
    FINAL,
    LIVE,
    NHL,
    NHL_API,
    SCHEDULED,
    SLOT_A,
    SLOT_B,
    Bracket,
    Found,
    Game,
    failed,
    found,
    number,
    text,
)

NAME = "NHL"
BRACKET = "https://api-web.nhle.com/v1/playoff-bracket/{year}"
SCORE = "https://api-web.nhle.com/v1/score/{day}"
SERIES_LENGTH = 7
LETTERS = "ABCDEFGHIJKLMNO"
ROUND_STARTS = (0, 8, 12, 14, 15)
STATES = {
    "FUT": SCHEDULED,
    "PRE": SCHEDULED,
    "LIVE": LIVE,
    "CRIT": LIVE,
    "OFF": FINAL,
    "FINAL": FINAL,
}


def season_of(value: Any) -> str | None:
    """`20262027` or a bracket year (2027) both become 2026-27."""
    raw = str(value or "").strip()
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[6:]}"
    year = number(raw)
    return None if year is None else f"{year - 1}-{str(year)[2:]}"


def year_of(season: str) -> int | None:
    head = number(str(season)[:4])
    if head is None:
        return None
    return head + 1 if "-" in str(season) else head


def bracket_url(year: int) -> str:
    return BRACKET.format(year=int(year))


def score_url(day: date) -> str:
    return SCORE.format(day=day.isoformat())


def next_of(letter: str) -> tuple[str, str] | None:
    """A and B feed I, C and D feed J, … M and N feed O; the earlier letter takes slot a."""
    at = LETTERS.find(letter)
    if at < 0 or at >= ROUND_STARTS[-2]:
        return None
    for start, after in zip(ROUND_STARTS, ROUND_STARTS[1:], strict=False):
        if start <= at < after:
            offset = at - start
            return LETTERS[after + offset // 2], SLOT_A if offset % 2 == 0 else SLOT_B
    return None


def series_state(series: dict[str, Any]) -> str:
    if series.get("winningTeamId"):
        return FINAL
    wins = (number(series.get("topSeedWins")) or 0) + (number(series.get("bottomSeedWins")) or 0)
    return LIVE if wins else SCHEDULED


def parse_bracket(payload: Any, year: int) -> Bracket:
    found_bracket = Bracket(league=NHL, season=season_of(year) or "")
    for series in payload.get("series") or [] if isinstance(payload, dict) else []:
        letter = text(series.get("seriesLetter"))
        if letter is None:
            continue
        top, bottom = series.get("topSeedTeam") or {}, series.get("bottomSeedTeam") or {}
        for team, rank in ((top, "topSeedRank"), (bottom, "bottomSeedRank")):
            ext_id = text(team.get("id"))
            if ext_id is None:
                continue
            found_bracket.names[ext_id] = text((team.get("name") or {}).get("default")) or ext_id
            seed = number(series.get(rank))
            if seed is not None:
                found_bracket.seeds[ext_id] = seed
        found_bracket.games.append(
            Game(
                ext_id=letter,
                source_key=letter,
                a_ext_id=text(top.get("id")),
                b_ext_id=text(bottom.get("id")),
                a_score=number(series.get("topSeedWins")),
                b_score=number(series.get("bottomSeedWins")),
                status=series_state(series),
                starts_at=None,
                period_words=text(series.get("seriesTitle")),
                round=number(series.get("playoffRound")),
            )
        )
        found_bracket.best_of[letter] = SERIES_LENGTH
        target = next_of(letter)
        if target is not None:
            found_bracket.links[letter] = target
    return found_bracket


def period_words(game: dict[str, Any]) -> str | None:
    period = game.get("periodDescriptor") or {}
    clock = game.get("clock") or {}
    words = " ".join(
        str(one)
        for one in (
            period.get("periodType") if period.get("periodType") != "REG" else None,
            f"P{period['number']}" if period.get("number") else None,
            clock.get("timeRemaining"),
        )
        if one
    )
    return text(words)


def parse_score(payload: Any) -> list[Game]:
    found_games: list[Game] = []
    for game in payload.get("games") or [] if isinstance(payload, dict) else []:
        ext_id = text(game.get("id"))
        if ext_id is None:
            continue
        home, away = game.get("homeTeam") or {}, game.get("awayTeam") or {}
        state = STATES.get(str(game.get("gameState")), SCHEDULED)
        found_games.append(
            Game(
                ext_id=ext_id,
                source_key=ext_id,
                a_ext_id=text(home.get("id")),
                b_ext_id=text(away.get("id")),
                a_score=number(home.get("score")) if state != SCHEDULED else None,
                b_score=number(away.get("score")) if state != SCHEDULED else None,
                status=state,
                starts_at=stamp(game.get("startTimeUTC")),
                period_words=period_words(game) if state == LIVE else None,
            )
        )
    return found_games


def named(answer: Found, what: str) -> Found:
    return failed(f"{NAME} {answer.why} for {what}", NHL_API)


async def bracket(season: str, *, fetch: http.Fetch | None = None) -> Found:
    year = year_of(season)
    if year is None:
        return failed(f"{season} is not a season the {NAME} can read", NHL_API)
    answer = await http.get_json(bracket_url(year), fetch=fetch)
    if not answer.ok:
        return named(answer, f"the {year} playoff bracket")
    parsed = parse_bracket(answer.value, year)
    if not parsed.games:
        return failed(f"{NAME} sent no {year} playoff bracket", NHL_API)
    return found(parsed, NHL_API)


async def scores(day: date, *, fetch: http.Fetch | None = None) -> Found:
    answer = await http.get_json(score_url(day), fetch=fetch)
    if not answer.ok:
        return named(answer, f"the scores of {day.isoformat()}")
    return found(parse_score(answer.value), NHL_API)


__all__ = [
    "NAME",
    "bracket",
    "bracket_url",
    "next_of",
    "parse_bracket",
    "parse_score",
    "score_url",
    "scores",
    "season_of",
    "year_of",
]
