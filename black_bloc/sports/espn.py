"""ESPN's keyless site API: team lists, rosters, scoreboards and the NFL standings' seeds."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from . import http
from .model import (
    COLLEGE,
    ESPN,
    FINAL,
    LIVE,
    MLB,
    NBA,
    NCAAM,
    NCAAW,
    NFL,
    NHL,
    SCHEDULED,
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

NAME = "ESPN"
SITE = "https://site.api.espn.com/apis/site/v2/sports/{path}"
STANDINGS = "https://site.api.espn.com/apis/v2/sports/{path}/standings?season={year}"
PATHS: dict[str, str] = {
    NFL: "football/nfl",
    NBA: "basketball/nba",
    MLB: "baseball/mlb",
    NHL: "hockey/nhl",
    NCAAM: "basketball/mens-college-basketball",
    NCAAW: "basketball/womens-college-basketball",
}
SPLIT_YEARS = (NBA, NHL, *COLLEGE)
STATES = {"pre": SCHEDULED, "in": LIVE, "post": FINAL}
TOURNAMENT_GROUP = "100"
POSTSEASON = "3"
NFL_WEEKS = (1, 2, 3, 4, 5)


def season_of(league: str, year: Any) -> str | None:
    """ESPN names a season by the year it ends: 2027 is NBA and NHL 2026-27."""
    found_year = number(year)
    if found_year is None:
        return None
    if league in SPLIT_YEARS:
        return f"{found_year - 1}-{str(found_year)[2:]}"
    return str(found_year)


def year_of(league: str, season: str) -> int | None:
    head = number(str(season)[:4])
    if head is None:
        return None
    return head + 1 if league in SPLIT_YEARS and "-" in str(season) else head


def teams_url(league: str) -> str:
    return SITE.format(path=f"{PATHS[league]}/teams") + "?limit=1000"


def roster_url(league: str, team_id: str) -> str:
    return SITE.format(path=f"{PATHS[league]}/teams/{team_id}/roster")


def scoreboard_url(
    league: str,
    day: date | None = None,
    *,
    postseason: bool = False,
    week: int | None = None,
    season: int | None = None,
) -> str:
    query: list[str] = []
    if postseason:
        query.append(f"seasontype={POSTSEASON}")
    if week is not None:
        query.append(f"week={int(week)}")
    if season is not None:
        query.append(f"dates={int(season)}")
    elif day is not None:
        query.append(f"dates={day.strftime('%Y%m%d')}")
    if league in COLLEGE:
        query.append("limit=400")
        if postseason:
            query.append(f"groups={TOURNAMENT_GROUP}")
    tail = f"?{'&'.join(query)}" if query else ""
    return SITE.format(path=f"{PATHS[league]}/scoreboard") + tail


def standings_url(league: str, year: int) -> str:
    return STANDINGS.format(path=PATHS[league], year=int(year))


def parse_teams(payload: Any, league: str) -> list[Team]:
    found_teams: list[Team] = []
    for sport in payload.get("sports") or [] if isinstance(payload, dict) else []:
        for one_league in sport.get("leagues") or []:
            for entry in one_league.get("teams") or []:
                team = entry.get("team") if isinstance(entry, dict) else None
                if not isinstance(team, dict) or team.get("isActive") is False:
                    continue
                ext_id, name = text(team.get("id")), text(team.get("displayName"))
                if not ext_id or not name:
                    continue
                aliases = aliases_of(
                    name, team.get("shortDisplayName"), team.get("location"), team.get("name")
                )
                found_teams.append(
                    Team(ext_id, name, text(team.get("abbreviation")), league, aliases)
                )
    return found_teams


def athletes_of(payload: Any) -> list[dict[str, Any]]:
    """A roster lists athletes flat (NBA) or in position groups with `items` (NFL, NHL)."""
    listed = payload.get("athletes") if isinstance(payload, dict) else None
    flat: list[dict[str, Any]] = []
    for one in listed or []:
        if not isinstance(one, dict):
            continue
        if isinstance(one.get("items"), list):
            flat += [item for item in one["items"] if isinstance(item, dict)]
        else:
            flat.append(one)
    return flat


def parse_roster(payload: Any, league: str, team_id: str) -> list[Player]:
    found_players: list[Player] = []
    for one in athletes_of(payload):
        ext_id = text(one.get("id"))
        name = text(one.get("displayName") or one.get("fullName"))
        if ext_id and name:
            found_players.append(
                Player(ext_id, name, str(team_id), league, text(one.get("shortName")))
            )
    return found_players


def stamp(value: Any) -> str | None:
    raw = text(value)
    if raw is None:
        return None
    try:
        when = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return when.astimezone(UTC).isoformat()


def parse_event(event: Any) -> Game | None:
    if not isinstance(event, dict):
        return None
    competitions = event.get("competitions") or []
    competition = competitions[0] if competitions and isinstance(competitions[0], dict) else {}
    sides = {
        one.get("homeAway"): one
        for one in competition.get("competitors") or []
        if isinstance(one, dict)
    }
    home, away = sides.get("home") or {}, sides.get("away") or {}
    status = (event.get("status") or {}).get("type") or {}
    state = STATES.get(str(status.get("state")), SCHEDULED)
    ext_id = text(event.get("id"))
    if ext_id is None:
        return None
    return Game(
        ext_id=ext_id,
        source_key=ext_id,
        a_ext_id=text((home.get("team") or {}).get("id")),
        b_ext_id=text((away.get("team") or {}).get("id")),
        a_score=number(home.get("score")) if state != SCHEDULED else None,
        b_score=number(away.get("score")) if state != SCHEDULED else None,
        status=state,
        starts_at=stamp(event.get("date")),
        period_words=text(status.get("shortDetail")),
    )


def parse_scoreboard(payload: Any) -> list[Game]:
    events = payload.get("events") if isinstance(payload, dict) else None
    return [game for game in map(parse_event, events or []) if game is not None]


def headline_of(event: Any) -> str:
    competitions = event.get("competitions") or [] if isinstance(event, dict) else []
    notes = (competitions[0].get("notes") or []) if competitions else []
    return " ".join(str(one.get("headline") or "") for one in notes if isinstance(one, dict))


def parse_seeds(payload: Any) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Each conference's playoff teams in seed order, and every team's display name."""
    seeds: dict[str, list[str]] = {}
    names: dict[str, str] = {}
    for conference in payload.get("children") or [] if isinstance(payload, dict) else []:
        code = text(conference.get("abbreviation"))
        ranked: list[tuple[int, str]] = []
        for entry in (conference.get("standings") or {}).get("entries") or []:
            team = entry.get("team") or {}
            ext_id = text(team.get("id"))
            if ext_id is None:
                continue
            names[ext_id] = text(team.get("displayName")) or ext_id
            for stat in entry.get("stats") or []:
                seed = whole(stat.get("value")) if stat.get("name") == "playoffSeed" else None
                if seed:
                    ranked.append((seed, ext_id))
        if code:
            seeds[code] = [ext_id for _, ext_id in sorted(ranked)]
    return seeds, names


def whole(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def named(found_answer: Found, what: str) -> Found:
    return failed(f"{NAME} {found_answer.why} for {what}", ESPN)


async def teams(league: str, *, fetch: http.Fetch | None = None) -> Found:
    answer = await http.get_json(teams_url(league), fetch=fetch)
    if not answer.ok:
        return named(answer, f"the {league.upper()} teams")
    listed = parse_teams(answer.value, league)
    if not listed:
        return failed(f"{NAME} sent no {league.upper()} teams", ESPN)
    return found(listed, ESPN)


async def players(league: str, team_ids: list[str], *, fetch: http.Fetch | None = None) -> Found:
    """Every roster must answer, or the list is not replaced."""
    listed: list[Player] = []
    for team_id in team_ids:
        answer = await http.get_json(roster_url(league, team_id), fetch=fetch)
        if not answer.ok:
            return named(answer, f"the {league.upper()} roster of team {team_id}")
        listed += parse_roster(answer.value, league, team_id)
    if not listed:
        return failed(f"{NAME} sent no {league.upper()} players", ESPN)
    return found(listed, ESPN)


async def scores(league: str, day: date, *, fetch: http.Fetch | None = None) -> Found:
    answer = await http.get_json(scoreboard_url(league, day), fetch=fetch)
    if not answer.ok:
        return named(answer, f"the {league.upper()} scores of {day.isoformat()}")
    return found(parse_scoreboard(answer.value), ESPN)


__all__ = [
    "NAME",
    "PATHS",
    "athletes_of",
    "headline_of",
    "parse_event",
    "parse_roster",
    "parse_scoreboard",
    "parse_seeds",
    "parse_teams",
    "players",
    "roster_url",
    "scoreboard_url",
    "scores",
    "season_of",
    "standings_url",
    "teams",
    "teams_url",
    "year_of",
]
