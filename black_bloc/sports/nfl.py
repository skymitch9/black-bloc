"""The NFL playoff bracket, built from ESPN's seeds with the reseeding rule."""

from __future__ import annotations

from typing import Any

from . import espn, http
from .model import (
    ESPN,
    FINAL,
    NFL,
    SCHEDULED,
    SLOT_A,
    SLOT_B,
    Bracket,
    Found,
    Game,
    failed,
    found,
)

CONFERENCES = ("AFC", "NFC")
SEEDS = 7
WILD_CARD = ((2, 7), (3, 6), (4, 5))
SUPER_BOWL = "SB"
ROUND_WC, ROUND_DIV, ROUND_CONF, ROUND_SB = 1, 2, 3, 4


def wc_key(conference: str, at: int) -> str:
    return f"{conference}-WC-{at}"


def div_key(conference: str, at: int) -> str:
    return f"{conference}-DIV-{at}"


def conf_key(conference: str) -> str:
    return f"{conference}-CONF"


def oriented(game: Game, a: str | None, b: str | None) -> tuple[int | None, int | None]:
    if game.a_ext_id == a and game.b_ext_id == b:
        return game.a_score, game.b_score
    return game.b_score, game.a_score


def winner_of(game: Game | None) -> str | None:
    if game is None or game.status != FINAL or game.a_score is None or game.b_score is None:
        return None
    if game.a_score == game.b_score:
        return None
    return game.a_ext_id if game.a_score > game.b_score else game.b_ext_id


class Builder:
    def __init__(self, seeds: dict[str, list[str]], results: list[Game], season: str) -> None:
        self.bracket = Bracket(league=NFL, season=season)
        self.played = {
            frozenset((one.a_ext_id, one.b_ext_id)): one
            for one in results
            if one.a_ext_id and one.b_ext_id
        }
        self.seed_of: dict[str, int] = {}
        self.seeds = {conf: list(seeds.get(conf) or [])[:SEEDS] for conf in CONFERENCES}
        for conf in CONFERENCES:
            for at, ext_id in enumerate(self.seeds[conf], start=1):
                self.seed_of[ext_id] = at
                self.bracket.seeds[ext_id] = at

    def ranked(self, *teams: str | None) -> list[str | None]:
        known = sorted((one for one in teams if one), key=lambda one: self.seed_of.get(one, 99))
        return [*known, *(None for one in teams if not one)]

    def add(self, key: str, a: str | None, b: str | None, round_number: int) -> Game:
        result = self.played.get(frozenset((a, b))) if a and b else None
        if result is None:
            game = Game("", key, a, b, None, None, SCHEDULED, None, None, round_number)
        else:
            score_a, score_b = oriented(result, a, b)
            game = Game(
                result.ext_id,
                key,
                a,
                b,
                score_a,
                score_b,
                result.status,
                result.starts_at,
                result.period_words,
                round_number,
            )
        self.bracket.games.append(game)
        return game

    def link(self, source: Game, target: str, winner: str | None, target_game: Game) -> None:
        if winner is None:
            return
        slot = SLOT_A if target_game.a_ext_id == winner else SLOT_B
        self.bracket.links[source.source_key] = (target, slot)

    def conference(self, conf: str) -> str | None:
        seeds = self.seeds[conf]
        if len(seeds) < SEEDS:
            return None
        wild = [
            self.add(wc_key(conf, at), seeds[high - 1], seeds[low - 1], ROUND_WC)
            for at, (high, low) in enumerate(WILD_CARD, start=1)
        ]
        winners = [winner_of(one) for one in wild]
        if all(winners):
            lowest, *rest = sorted(winners, key=lambda one: -self.seed_of[one])
            first = self.add(div_key(conf, 1), seeds[0], lowest, ROUND_DIV)
            second = self.add(div_key(conf, 2), *self.ranked(*rest), ROUND_DIV)
            for game, winner in zip(wild, winners, strict=True):
                target = first if winner == lowest else second
                self.link(game, target.source_key, winner, target)
        else:
            first = self.add(div_key(conf, 1), seeds[0], None, ROUND_DIV)
            second = self.add(div_key(conf, 2), None, None, ROUND_DIV)
        div_winners = [winner_of(first), winner_of(second)]
        if all(div_winners):
            final = self.add(conf_key(conf), *self.ranked(*div_winners), ROUND_CONF)
            for game, winner in zip((first, second), div_winners, strict=True):
                self.link(game, final.source_key, winner, final)
        else:
            final = self.add(conf_key(conf), None, None, ROUND_CONF)
        return winner_of(final)

    def build(self) -> Bracket:
        champions = [self.conference(conf) for conf in CONFERENCES]
        if any(not self.seeds[conf] for conf in CONFERENCES):
            return self.bracket
        self.add(SUPER_BOWL, champions[0], champions[1], ROUND_SB)
        self.bracket.links[conf_key(CONFERENCES[0])] = (SUPER_BOWL, SLOT_A)
        self.bracket.links[conf_key(CONFERENCES[1])] = (SUPER_BOWL, SLOT_B)
        return self.bracket


def build(seeds: dict[str, list[str]], results: list[Game], season: str) -> Bracket:
    """The bracket as far as the results reach; a round not yet decided has open slots."""
    return Builder(seeds, results, season).build()


def postseason(events: list[Any], teams: set[str]) -> list[Game]:
    """ESPN's season-type 3 games between playoff teams (the Pro Bowl is dropped)."""
    found_games: list[Game] = []
    for event in events:
        if (event.get("season") or {}).get("type") not in (3, "3"):
            continue
        game = espn.parse_event(event)
        if game is not None and game.a_ext_id in teams and game.b_ext_id in teams:
            found_games.append(game)
    return found_games


async def bracket(season: str, *, fetch: http.Fetch | None = None) -> Found:
    year = espn.year_of(NFL, season)
    if year is None:
        return failed(f"{season} is not a season {espn.NAME} can read", ESPN)
    standings = await http.get_json(espn.standings_url(NFL, year), fetch=fetch)
    if not standings.ok:
        return espn.named(standings, f"the {year} NFL standings")
    seeds, names = espn.parse_seeds(standings.value)
    if any(len(seeds.get(conf) or []) < SEEDS for conf in CONFERENCES):
        return failed(f"{espn.NAME} sent no {year} NFL playoff seeds", ESPN)
    events: list[Any] = []
    for week in espn.NFL_WEEKS:
        answer = await http.get_json(
            espn.scoreboard_url(NFL, postseason=True, week=week, season=year), fetch=fetch
        )
        if not answer.ok:
            return espn.named(answer, f"the {year} NFL playoff week {week}")
        events += (answer.value or {}).get("events") or []
    teams = {one for conf in CONFERENCES for one in seeds[conf][:SEEDS]}
    built = build(seeds, postseason(events, teams), espn.season_of(NFL, year) or str(year))
    built.names.update({ext_id: names[ext_id] for ext_id in teams if ext_id in names})
    return found(built, ESPN)


__all__ = [
    "CONFERENCES",
    "SUPER_BOWL",
    "bracket",
    "build",
    "conf_key",
    "div_key",
    "postseason",
    "wc_key",
    "winner_of",
]
