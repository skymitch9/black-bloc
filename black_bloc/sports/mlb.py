"""MLB's statsapi: the postseason series, teams, players and a day's schedule."""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

from . import http
from .espn import stamp
from .model import (
    FINAL,
    LIVE,
    MLB,
    MLB_API,
    SCHEDULED,
    SLOT_A,
    SLOT_B,
    Bracket,
    Found,
    Game,
    Player,
    Team,
    aliases_of,
    failed,
    found,
    number,
    text,
)

NAME = "MLB"
BASE = "https://statsapi.mlb.com/api/v1"
ROUNDS = {"F": 1, "D": 2, "L": 3, "W": 4}
STATES = {"Final": FINAL, "Live": LIVE, "Preview": SCHEDULED}
FALLBACK_LINKS: dict[str, tuple[str, str]] = {
    "F_1": ("D_2", SLOT_B),
    "F_2": ("D_1", SLOT_B),
    "F_3": ("D_4", SLOT_B),
    "F_4": ("D_3", SLOT_B),
    "D_1": ("L_1", SLOT_A),
    "D_2": ("L_1", SLOT_B),
    "D_3": ("L_2", SLOT_A),
    "D_4": ("L_2", SLOT_B),
    "L_1": ("W_1", SLOT_A),
    "L_2": ("W_1", SLOT_B),
}


def season_of(year: Any) -> str | None:
    found_year = number(year)
    return None if found_year is None else str(found_year)


def year_of(season: str) -> int | None:
    return number(str(season)[:4])


def series_url(year: int) -> str:
    return f"{BASE}/schedule/postseason/series?season={int(year)}&sportId=1"


def teams_url() -> str:
    return f"{BASE}/teams?sportId=1"


def players_url(year: int) -> str:
    return f"{BASE}/sports/1/players?season={int(year)}"


def schedule_url(day: date) -> str:
    return f"{BASE}/schedule?sportId=1&date={day.isoformat()}&hydrate=linescore"


def side_id(game: dict[str, Any], side: str) -> str | None:
    return text((((game.get("teams") or {}).get(side) or {}).get("team") or {}).get("id"))


def state_of(game: dict[str, Any]) -> str:
    return STATES.get(str((game.get("status") or {}).get("abstractGameState")), SCHEDULED)


def series_game(series: dict[str, Any], key: str, names: dict[str, str]) -> Game | None:
    games = [one for one in series.get("games") or [] if isinstance(one, dict)]
    if not games:
        return None
    first = games[0]
    home, away = side_id(first, "home"), side_id(first, "away")
    for side in ("home", "away"):
        team = ((first.get("teams") or {}).get(side) or {}).get("team") or {}
        if text(team.get("id")):
            names[str(team["id"])] = text(team.get("name")) or str(team["id"])
    wins: Counter[str] = Counter()
    for game in games:
        if state_of(game) != FINAL:
            continue
        for side in ("home", "away"):
            held = (game.get("teams") or {}).get(side) or {}
            if held.get("isWinner") and side_id(game, side):
                wins[side_id(game, side)] += 1
    length = number(first.get("gamesInSeries")) or len(games)
    needed = length // 2 + 1
    done = any(count >= needed for count in wins.values())
    started = any(state_of(game) != SCHEDULED for game in games)
    return Game(
        ext_id=key,
        source_key=key,
        a_ext_id=home,
        b_ext_id=away,
        a_score=wins.get(home, 0) if started else None,
        b_score=wins.get(away, 0) if started else None,
        status=FINAL if done else (LIVE if started else SCHEDULED),
        starts_at=stamp(first.get("gameDate")),
        period_words=text(first.get("seriesDescription")),
        round=ROUNDS.get(key.split("_")[0]),
    )


def linked(games: dict[str, Game]) -> dict[str, tuple[str, str]]:
    """A later series' teams name the earlier series they won; the rest is the 2026 shape."""
    links: dict[str, tuple[str, str]] = {}
    for key, game in games.items():
        later, winner = (game.round or 0) + 1, winner_of(game)
        for target, other in games.items():
            if other.round != later:
                continue
            if winner and winner == other.a_ext_id:
                links[key] = (target, SLOT_A)
            elif winner and winner == other.b_ext_id:
                links[key] = (target, SLOT_B)
        if key not in links and key in FALLBACK_LINKS:
            links[key] = FALLBACK_LINKS[key]
    return links


def winner_of(game: Game) -> str | None:
    if game.status != FINAL or game.a_score is None or game.b_score is None:
        return None
    if game.a_score == game.b_score:
        return None
    return game.a_ext_id if game.a_score > game.b_score else game.b_ext_id


def parse_series(payload: Any, year: int) -> Bracket:
    found_bracket = Bracket(league=MLB, season=season_of(year) or "")
    games: dict[str, Game] = {}
    for one in payload.get("series") or [] if isinstance(payload, dict) else []:
        key = text((one.get("series") or {}).get("id"))
        if key is None:
            continue
        game = series_game(one, key, found_bracket.names)
        if game is None:
            continue
        games[key] = game
        found_bracket.best_of[key] = number((one.get("games") or [{}])[0].get("gamesInSeries")) or 1
    found_bracket.links = linked(games)
    found_bracket.games = sorted(games.values(), key=lambda game: (game.round or 0, game.ext_id))
    return found_bracket


def parse_teams(payload: Any) -> list[Team]:
    found_teams: list[Team] = []
    for team in payload.get("teams") or [] if isinstance(payload, dict) else []:
        ext_id, name = text(team.get("id")), text(team.get("name"))
        if not ext_id or not name or team.get("active") is False:
            continue
        aliases = aliases_of(name, team.get("teamName"), team.get("locationName"))
        found_teams.append(Team(ext_id, name, text(team.get("abbreviation")), MLB, aliases))
    return found_teams


def parse_players(payload: Any) -> list[Player]:
    found_players: list[Player] = []
    for person in payload.get("people") or [] if isinstance(payload, dict) else []:
        ext_id, name = text(person.get("id")), text(person.get("fullName"))
        if not ext_id or not name or person.get("active") is False:
            continue
        team = text((person.get("currentTeam") or {}).get("id"))
        found_players.append(Player(ext_id, name, team, MLB, text(person.get("initLastName"))))
    return found_players


def inning_words(game: dict[str, Any]) -> str | None:
    line = game.get("linescore") or {}
    return text(f"{line.get('inningState') or ''} {line.get('currentInningOrdinal') or ''}")


def parse_schedule(payload: Any) -> list[Game]:
    found_games: list[Game] = []
    for day in payload.get("dates") or [] if isinstance(payload, dict) else []:
        for game in day.get("games") or []:
            ext_id = text(game.get("gamePk"))
            if ext_id is None:
                continue
            state = state_of(game)
            teams = game.get("teams") or {}
            found_games.append(
                Game(
                    ext_id=ext_id,
                    source_key=ext_id,
                    a_ext_id=side_id(game, "home"),
                    b_ext_id=side_id(game, "away"),
                    a_score=number((teams.get("home") or {}).get("score"))
                    if state != SCHEDULED
                    else None,
                    b_score=number((teams.get("away") or {}).get("score"))
                    if state != SCHEDULED
                    else None,
                    status=state,
                    starts_at=stamp(game.get("gameDate")),
                    period_words=inning_words(game) if state == LIVE else None,
                )
            )
    return found_games


def named(answer: Found, what: str) -> Found:
    return failed(f"{NAME} {answer.why} for {what}", MLB_API)


async def bracket(season: str, *, fetch: http.Fetch | None = None) -> Found:
    year = year_of(season)
    if year is None:
        return failed(f"{season} is not a season {NAME} can read", MLB_API)
    answer = await http.get_json(series_url(year), fetch=fetch)
    if not answer.ok:
        return named(answer, f"the {year} postseason")
    parsed = parse_series(answer.value, year)
    if not parsed.games:
        return failed(f"{NAME} sent no {year} postseason", MLB_API)
    return found(parsed, MLB_API)


async def teams(*, fetch: http.Fetch | None = None) -> Found:
    answer = await http.get_json(teams_url(), fetch=fetch)
    if not answer.ok:
        return named(answer, "the teams")
    listed = parse_teams(answer.value)
    return found(listed, MLB_API) if listed else failed(f"{NAME} sent no teams", MLB_API)


async def players(year: int, *, fetch: http.Fetch | None = None) -> Found:
    answer = await http.get_json(players_url(year), fetch=fetch)
    if not answer.ok:
        return named(answer, f"the {year} players")
    listed = parse_players(answer.value)
    return found(listed, MLB_API) if listed else failed(f"{NAME} sent no players", MLB_API)


async def scores(day: date, *, fetch: http.Fetch | None = None) -> Found:
    answer = await http.get_json(schedule_url(day), fetch=fetch)
    if not answer.ok:
        return named(answer, f"the scores of {day.isoformat()}")
    return found(parse_schedule(answer.value), MLB_API)


__all__ = [
    "FALLBACK_LINKS",
    "NAME",
    "bracket",
    "parse_players",
    "parse_schedule",
    "parse_series",
    "parse_teams",
    "players",
    "players_url",
    "schedule_url",
    "scores",
    "season_of",
    "series_url",
    "teams",
    "teams_url",
    "year_of",
    "winner_of",
]
