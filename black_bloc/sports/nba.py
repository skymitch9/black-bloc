"""stats.nba.com: the playoff bracket's series and the player index (Referer/Origin headers)."""

from __future__ import annotations

from typing import Any

from . import http
from .model import (
    FINAL,
    LIVE,
    NBA,
    NBA_API,
    SCHEDULED,
    SLOT_A,
    SLOT_B,
    Bracket,
    Found,
    Game,
    Player,
    failed,
    found,
    number,
    text,
)

NAME = "NBA"
BRACKET = "https://stats.nba.com/stats/playoffbracket?LeagueID=00&SeasonYear={year}&State=2"
PLAYERS = "https://stats.nba.com/stats/playerindex?LeagueID=00&Season={season}"
SERIES_LENGTH = 7
FINAL_ROUND = 4
PLAY_IN_ROUND = 0


def season_of(year: Any) -> str | None:
    """`SeasonYear=2025` is the 2025-26 season (its Finals are in June 2026)."""
    found_year = number(year)
    return None if found_year is None else f"{found_year}-{str(found_year + 1)[2:]}"


def year_of(season: str) -> int | None:
    return number(str(season)[:4])


def bracket_url(year: int) -> str:
    return BRACKET.format(year=int(year))


def players_url(season: str) -> str:
    return PLAYERS.format(season=season)


def key_of(round_number: int, order: int) -> str:
    return f"R{round_number}-{order}"


def series_state(series: dict[str, Any]) -> str:
    if number(series.get("seriesWinner")):
        return FINAL
    wins = (number(series.get("highSeedSeriesWins")) or 0) + (
        number(series.get("lowSeedSeriesWins")) or 0
    )
    return LIVE if wins else SCHEDULED


def wins_of(series: dict[str, Any], team_id: Any) -> int | None:
    if team_id is None:
        return None
    if number(series.get("highSeedId")) == number(team_id):
        return number(series.get("highSeedSeriesWins"))
    if number(series.get("lowSeedId")) == number(team_id):
        return number(series.get("lowSeedSeriesWins"))
    return None


def team_id(value: Any) -> str | None:
    found_id = number(value)
    return str(found_id) if found_id else None


def parse_series(found_bracket: Bracket, series: dict[str, Any], key: str, round_number: int):
    for side in ("highSeed", "lowSeed"):
        ext_id = team_id(series.get(f"{side}Id"))
        if ext_id is None:
            continue
        city, name = text(series.get(f"{side}City")), text(series.get(f"{side}Name"))
        found_bracket.names[ext_id] = " ".join(one for one in (city, name) if one) or ext_id
        seed = number(series.get(f"{side}Rank"))
        if seed:
            found_bracket.seeds[ext_id] = seed
    top = team_id(series.get("displayTopTeam")) or team_id(series.get("highSeedId"))
    bottom = team_id(series.get("displayBottomTeam")) or team_id(series.get("lowSeedId"))
    found_bracket.games.append(
        Game(
            ext_id=text(series.get("seriesId")) or key,
            source_key=key,
            a_ext_id=top,
            b_ext_id=bottom,
            a_score=wins_of(series, top),
            b_score=wins_of(series, bottom),
            status=series_state(series),
            starts_at=None,
            period_words=text(series.get("seriesText")),
            round=round_number,
        )
    )
    found_bracket.best_of[key] = SERIES_LENGTH


def parse_bracket(payload: Any) -> Bracket:
    """Series keyed by round and `displayOrderNumber`; order n feeds n // 2 of the next round."""
    held = payload.get("bracket") if isinstance(payload, dict) else None
    held = held if isinstance(held, dict) else {}
    found_bracket = Bracket(league=NBA, season=season_of(held.get("seasonYear")) or "")
    for at, series in enumerate(held.get("playInBracketSeries") or []):
        if isinstance(series, dict):
            parse_series(found_bracket, series, f"P-{at}", PLAY_IN_ROUND)
    for series in held.get("playoffBracketSeries") or []:
        round_number = number(series.get("roundNumber"))
        order = number(series.get("displayOrderNumber"))
        if round_number is None or order is None:
            continue
        key = key_of(round_number, order)
        parse_series(found_bracket, series, key, round_number)
        if round_number < FINAL_ROUND:
            found_bracket.links[key] = (
                key_of(round_number + 1, order // 2),
                SLOT_A if order % 2 == 0 else SLOT_B,
            )
    return found_bracket


def parse_players(payload: Any) -> list[Player]:
    sets = payload.get("resultSets") if isinstance(payload, dict) else None
    table = sets[0] if sets and isinstance(sets[0], dict) else {}
    headers = list(table.get("headers") or [])
    found_players: list[Player] = []
    for row in table.get("rowSet") or []:
        one = dict(zip(headers, row, strict=False))
        ext_id = team_id(one.get("PERSON_ID"))
        first, last = text(one.get("PLAYER_FIRST_NAME")), text(one.get("PLAYER_LAST_NAME"))
        name = " ".join(part for part in (first, last) if part)
        if ext_id and name:
            short = f"{first[0]}. {last}" if first and last else name
            found_players.append(Player(ext_id, name, team_id(one.get("TEAM_ID")), NBA, short))
    return found_players


def named(answer: Found, what: str) -> Found:
    return failed(f"{NAME} {answer.why} for {what}", NBA_API)


async def bracket(season: str, *, fetch: http.Fetch | None = None) -> Found:
    year = year_of(season)
    if year is None:
        return failed(f"{season} is not a season the {NAME} can read", NBA_API)
    answer = await http.get_json(bracket_url(year), fetch=fetch)
    if not answer.ok:
        return named(answer, f"the {season} playoff bracket")
    parsed = parse_bracket(answer.value)
    if not parsed.games:
        return failed(f"{NAME} sent no {season} playoff bracket", NBA_API)
    return found(parsed, NBA_API)


async def players(season: str, *, fetch: http.Fetch | None = None) -> Found:
    answer = await http.get_json(players_url(season), fetch=fetch)
    if not answer.ok:
        return named(answer, f"the {season} players")
    listed = parse_players(answer.value)
    if not listed:
        return failed(f"{NAME} sent no {season} players", NBA_API)
    return found(listed, NBA_API)


__all__ = [
    "NAME",
    "bracket",
    "bracket_url",
    "key_of",
    "parse_bracket",
    "parse_players",
    "players",
    "players_url",
    "season_of",
    "year_of",
]
