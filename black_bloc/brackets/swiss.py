"""Swiss: score-group pairing that avoids rematches, a bye for an odd field, round by round."""

from __future__ import annotations

import math

from .model import DONE, SWISS_SIDE, Bracket, Match, Options, key_of
from .tally import met, records

SEARCH_BUDGET = 20_000


def most_rounds(entrants: int) -> int:
    return max(1, entrants - 1)


def rounds_for(entrants: int, wanted: int | None = None) -> int:
    if wanted:
        return int(wanted)
    return max(1, math.ceil(math.log2(max(2, entrants))))


def candidates(player: int, pool: list[int], points: dict[int, int]) -> list[int]:
    """The partner to try first is halfway down the player's own score group, then outward."""
    group = [other for other in pool if points[other] == points[player]]
    rest = [other for other in pool if points[other] != points[player]]
    ideal = max((len(group) + 1) // 2 - 1, 0)
    return group[ideal:] + list(reversed(group[:ideal])) + rest


def pairings(
    order: list[int], points: dict[int, int], played: set[frozenset[int]]
) -> list[tuple[int, int]]:
    """A full pairing with no rematch when one exists; otherwise the order paired top-down."""
    budget = [SEARCH_BUDGET]

    def solve(pool: list[int]) -> list[tuple[int, int]] | None:
        if not pool:
            return []
        budget[0] -= 1
        if budget[0] < 0:
            return None
        player, rest = pool[0], pool[1:]
        for other in candidates(player, rest, points):
            if frozenset((player, other)) in played:
                continue
            found = solve([one for one in rest if one != other])
            if found is not None:
                return [(player, other), *found]
        return None

    found = solve(list(order))
    if found is not None:
        return found
    return [(order[at], order[at + 1]) for at in range(0, len(order) - 1, 2)]


def standing_order(bracket: Bracket, active: list[int]) -> list[int]:
    found = records(bracket)
    seed = {entrant: at for at, entrant in enumerate(bracket.entrants)}
    return sorted(active, key=lambda entrant: (-found[entrant].set_wins, seed[entrant]))


def bye_for(order: list[int], bracket: Bracket) -> int:
    found = records(bracket)
    for entrant in reversed(order):
        if not found[entrant].byes:
            return entrant
    return order[-1]


def pair_round(bracket: Bracket, round_: int) -> list[Match]:
    active = [entrant for entrant in bracket.entrants if entrant not in bracket.withdrawn]
    order = standing_order(bracket, active)
    bye = None
    if len(order) % 2:
        bye = bye_for(order, bracket)
        order = [entrant for entrant in order if entrant != bye]
    points = {entrant: records(bracket)[entrant].set_wins for entrant in order}
    played = met(bracket)
    pairs = pairings(order, points, played)
    made = [
        Match(
            key=key_of(SWISS_SIDE, round_, position),
            side=SWISS_SIDE,
            round=round_,
            position=position,
            best_of=bracket.options.best_of,
            slot_a=slot_a,
            slot_b=slot_b,
            rematch=frozenset((slot_a, slot_b)) in played,
        )
        for position, (slot_a, slot_b) in enumerate(pairs, start=1)
    ]
    if bye is not None:
        made.append(
            Match(
                key=key_of(SWISS_SIDE, round_, len(made) + 1),
                side=SWISS_SIDE,
                round=round_,
                position=len(made) + 1,
                best_of=bracket.options.best_of,
                slot_a=bye,
            )
        )
    return made


def current_round(bracket: Bracket) -> int:
    return max((match.round for match in bracket.matches.values()), default=0)


def total_rounds(bracket: Bracket) -> int:
    return rounds_for(len(bracket.entrants), bracket.options.swiss_rounds)


def next_round_due(bracket: Bracket) -> bool:
    now = current_round(bracket)
    if now >= total_rounds(bracket):
        return False
    return all(match.state in DONE for match in bracket.matches.values() if match.round == now)


def add_round(bracket: Bracket) -> list[str]:
    made = pair_round(bracket, current_round(bracket) + 1)
    for match in made:
        bracket.matches[match.key] = match
    return [match.key for match in made]


def build(entrants: list[int], options: Options) -> Bracket:
    bracket = Bracket(options=options, entrants=list(entrants))
    add_round(bracket)
    return bracket
