"""Round robin: every pair once, scheduled in rounds by the circle method."""

from __future__ import annotations

from .model import RR, Bracket, Match, Options, key_of


def schedule(entrants: list[int]) -> list[list[tuple[int, int]]]:
    """Rounds of pairs; with an odd field one entrant sits each round out."""
    field: list[int | None] = list(entrants)
    if len(field) % 2:
        field.append(None)
    count = len(field)
    rounds: list[list[tuple[int, int]]] = []
    for _ in range(count - 1):
        pairs = [
            (field[at], field[count - 1 - at])
            for at in range(count // 2)
            if field[at] is not None and field[count - 1 - at] is not None
        ]
        rounds.append([(a, b) for a, b in pairs])
        field = [field[0], field[-1], *field[1:-1]]
    return rounds


def match_count(entrants: int) -> int:
    return entrants * (entrants - 1) // 2


def build(entrants: list[int], options: Options) -> Bracket:
    matches: dict[str, Match] = {}
    for round_, pairs in enumerate(schedule(entrants), start=1):
        for position, (slot_a, slot_b) in enumerate(pairs, start=1):
            found = Match(
                key=key_of(RR, round_, position),
                side=RR,
                round=round_,
                position=position,
                best_of=options.best_of,
                slot_a=slot_a,
                slot_b=slot_b,
            )
            matches[found.key] = found
    return Bracket(options=options, entrants=list(entrants), matches=matches)
