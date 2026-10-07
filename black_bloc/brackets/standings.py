"""Placements and standings, and what each entrant is waiting on."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .model import (
    BYE,
    CALLED,
    COMPLETE,
    DISPUTED,
    ELIMINATION,
    READY,
    REPORTED,
    SWISS,
    WAITING,
    Bracket,
)
from .play import finished
from .tally import Record, records

PLAY = "play"
CALLED_UP = "called"
CONFIRM = "confirm"
OPPONENT_CONFIRMS = "opponent_confirms"
TO_DECIDES = "to_decides"
WAITS = "waits"
NEXT_ROUND = "next_round"
DONE = "done"
OUT = "out"
WAITING_CODES = (
    PLAY,
    CALLED_UP,
    CONFIRM,
    OPPONENT_CONFIRMS,
    TO_DECIDES,
    WAITS,
    NEXT_ROUND,
    DONE,
    OUT,
)


@dataclass
class Row:
    entrant: int
    place: int | None
    record: Record
    opponents_rate: float = 0.0


def eliminated(bracket: Bracket) -> dict[int, int]:
    found: dict[int, int] = {}
    for match in bracket.ordered():
        if match.state not in (COMPLETE, BYE):
            continue
        if match.placement_loser is not None and match.loser is not None:
            found[match.loser] = match.placement_loser
        if match.placement_winner is not None and match.winner is not None:
            found[match.winner] = match.placement_winner
    return found


def opponents_rate(found: dict[int, Record], entrant: int) -> float:
    rates = [found[other].win_rate for other in found[entrant].opponents if other in found]
    return round(sum(rates) / len(rates), 4) if rates else 0.0


def head_to_head(found: dict[int, Record], group: list[int]) -> dict[int, int]:
    members = set(group)
    return {
        entrant: sum(1 for beaten in found[entrant].beat if beaten in members) for entrant in group
    }


def grouped(entrants: list[int], key: Callable[[int], Any]) -> list[list[int]]:
    groups: list[list[int]] = []
    for entrant in sorted(entrants, key=key):
        if groups and key(groups[-1][0]) == key(entrant):
            groups[-1].append(entrant)
        else:
            groups.append([entrant])
    return groups


def ranked(
    bracket: Bracket, found: dict[int, Record], primary: Callable[[int], Any]
) -> list[tuple[int, int]]:
    """Primary order, then head to head inside a tie, then the TO's order; a tie left shares."""
    seed = {entrant: at for at, entrant in enumerate(bracket.entrants)}
    told = {entrant: at for at, entrant in enumerate(bracket.final_order)}
    placed: list[tuple[int, int]] = []
    for group in grouped(list(found), primary):
        h2h = head_to_head(found, group)
        for tied in grouped(group, lambda entrant, h2h=h2h: -h2h[entrant]):
            place = len(placed) + 1
            if len(tied) > 1 and all(entrant in told for entrant in tied):
                for offset, entrant in enumerate(sorted(tied, key=told.__getitem__)):
                    placed.append((entrant, place + offset))
            else:
                placed += [(entrant, place) for entrant in sorted(tied, key=seed.__getitem__)]
    return placed


def table(bracket: Bracket) -> list[Row]:
    """Round robin and Swiss: the live table; places are final once every set is done."""
    found = {
        entrant: one for entrant, one in records(bracket).items() if entrant in bracket.entrants
    }
    rates = {entrant: opponents_rate(found, entrant) for entrant in found}
    if bracket.format == SWISS:
        order = ranked(bracket, found, lambda e: (-found[e].set_wins, -rates[e]))
    else:
        order = ranked(bracket, found, lambda e: (-found[e].set_wins, -found[e].game_wins))
    return [Row(entrant, place, found[entrant], rates[entrant]) for entrant, place in order]


def placements(bracket: Bracket) -> dict[int, int]:
    """Final or so-far places: elimination places as entrants go out, a table's once it is done."""
    if bracket.format in ELIMINATION:
        return eliminated(bracket)
    if not finished(bracket):
        return {}
    return {row.entrant: row.place for row in table(bracket) if row.place is not None}


def waiting_on(bracket: Bracket) -> dict[int, dict[str, Any]]:
    placed = placements(bracket)
    found: dict[int, dict[str, Any]] = {}
    for entrant in bracket.entrants:
        mine = [match for match in bracket.ordered() if match.holds(entrant)]
        live = [match for match in mine if match.state in (READY, CALLED, REPORTED, DISPUTED)]
        if entrant in bracket.withdrawn:
            found[entrant] = {"what": OUT, "set": None, "opponent": None, "open": 0}
            continue
        if live:
            match = live[0]
            what = {READY: PLAY, CALLED: CALLED_UP, DISPUTED: TO_DECIDES}.get(match.state)
            if match.state == REPORTED:
                what = (
                    OPPONENT_CONFIRMS if match.reported_side == match.side_of(entrant) else CONFIRM
                )
            found[entrant] = {
                "what": what,
                "set": match.key,
                "opponent": match.other(entrant),
                "open": len(live),
            }
            continue
        waiting = next((match for match in mine if match.state == WAITING), None)
        if waiting is not None:
            found[entrant] = {"what": WAITS, "set": waiting.key, "opponent": None, "open": 0}
        elif entrant in placed or finished(bracket):
            found[entrant] = {"what": DONE, "set": None, "opponent": None, "open": 0}
        else:
            found[entrant] = {"what": NEXT_ROUND, "set": None, "opponent": None, "open": 0}
    return found
