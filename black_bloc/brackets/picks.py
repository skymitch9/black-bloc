"""Pick sheets, pure: the tree a member predicts, which picks it allows, and what a sheet scores."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .model import BYE, COMPLETE, VOID, A, B, Bracket, Match
from .sports_shape import is_pending

DEFAULT_POINTS = (1, 2, 4, 8, 16, 32)
MOST_POINTS = 1000
HIT = "hit"
MISS = "miss"
NO_SEED = 10**6


@dataclass(frozen=True)
class Rule:
    """Where a predicted slot comes from: one entrant, or the k-th best seed among the
    predicted winners of `sources`."""

    entrant: int | None = None
    sources: tuple[str, ...] = ()
    rank: int = 0

    def wire(self) -> dict[str, Any]:
        if self.sources:
            return {"from": list(self.sources), "rank": self.rank}
        return {"entrant": self.entrant}


@dataclass(frozen=True)
class Node:
    key: str
    round: int
    a: Rule
    b: Rule
    fixed: int | None = None

    def wire(self) -> dict[str, Any]:
        return {"round": self.round, "a": self.a.wire(), "b": self.b.wire(), "fixed": self.fixed}


@dataclass
class Tree:
    nodes: dict[str, Node] = field(default_factory=dict)
    seeds: dict[int, int] = field(default_factory=dict)

    def ordered(self) -> list[Node]:
        return sorted(self.nodes.values(), key=lambda one: (one.round, one.key))

    def wire(self) -> dict[str, Any]:
        return {
            "sets": {key: node.wire() for key, node in self.nodes.items()},
            "seeds": {str(entrant): seed for entrant, seed in self.seeds.items()},
        }


@dataclass(frozen=True)
class Score:
    points: int = 0
    correct: int = 0
    played: int = 0
    possible: int = 0
    marks: dict[str, str] = field(default_factory=dict)


def counted(match: Match) -> bool:
    return not is_pending(match) and match.state != VOID


def fixed_of(match: Match) -> int | None:
    """A set nobody picks: a bye, and a play-in already decided."""
    if match.state == BYE:
        return match.winner
    if match.round <= 0 and match.state == COMPLETE:
        return match.winner
    return None


def tree_of(
    bracket: Bracket | None,
    seeds: dict[int, int] | None = None,
    reseeds: dict[str, dict[str, tuple[tuple[str, ...], int]]] | None = None,
) -> Tree:
    """Each slot is fed by the set linked into it, else it is the entrant sitting there now;
    `reseeds` (set key → slot → (source keys, rank)) replaces the links a reseeding league
    cannot know before its results."""
    found = Tree(seeds=dict(seeds or {}))
    if bracket is None:
        return found
    shown = {key: match for key, match in bracket.matches.items() if counted(match)}
    feeders: dict[tuple[str, str], str] = {}
    for match in shown.values():
        if match.winner_to in shown:
            feeders[(match.winner_to, match.winner_slot or A)] = match.key
    for match in shown.values():
        rules = {}
        for slot in (A, B):
            wanted = (reseeds or {}).get(match.key, {}).get(slot)
            if wanted and all(one in shown for one in wanted[0]):
                rules[slot] = Rule(sources=tuple(wanted[0]), rank=int(wanted[1]))
            elif (match.key, slot) in feeders:
                rules[slot] = Rule(sources=(feeders[(match.key, slot)],))
            else:
                rules[slot] = Rule(entrant=match.slot(slot))
        found.nodes[match.key] = Node(
            match.key, int(match.round), rules[A], rules[B], fixed_of(match)
        )
    return found


def seed_order(tree: Tree, entrant: int) -> tuple[int, int]:
    return (tree.seeds.get(entrant) or NO_SEED, entrant)


def slot_of(tree: Tree, rule: Rule, winners: dict[str, int | None]) -> int | None:
    if not rule.sources:
        return rule.entrant
    known = [winners.get(one) for one in rule.sources]
    if any(one is None for one in known):
        return None
    ranked = sorted(known, key=lambda one: seed_order(tree, one))
    return ranked[rule.rank] if 0 <= rule.rank < len(ranked) else None


def predicted(tree: Tree, picks: dict[str, int]) -> tuple[dict[str, tuple], dict[str, int | None]]:
    """The member's bracket: each set's two predicted entrants and its predicted winner."""
    slots: dict[str, tuple[int | None, int | None]] = {}
    winners: dict[str, int | None] = {}
    for node in tree.ordered():
        pair = (slot_of(tree, node.a, winners), slot_of(tree, node.b, winners))
        slots[node.key] = pair
        if node.fixed is not None:
            winners[node.key] = node.fixed
            continue
        pick = picks.get(node.key)
        winners[node.key] = pick if pick is not None and pick in pair else None
    return slots, winners


def wrong(tree: Tree, picks: dict[str, int]) -> list[str]:
    """The picks this tree does not allow."""
    kept = cleaned(tree, picks)
    return sorted(key for key in picks if key not in kept)


def cleaned(tree: Tree, picks: dict[str, int]) -> dict[str, int]:
    """What is left of a sheet once every pick the tree no longer allows is dropped, earliest
    first, so a changed early pick clears the later picks that hung on it."""
    found = {key: value for key, value in picks.items() if key in tree.nodes}
    _, winners = predicted(tree, found)
    return {
        key: value
        for key, value in found.items()
        if tree.nodes[key].fixed is None and winners.get(key) == value
    }


def points_table(text: Any) -> tuple[int, ...] | None:
    """`1,2,4,8,16,32` as numbers; None when any part is not a whole number from 0 to 1000."""
    parts = [one.strip() for one in str(text or "").split(",") if one.strip()]
    if not parts:
        return None
    try:
        found = tuple(int(one) for one in parts)
    except ValueError:
        return None
    if any(not 0 <= one <= MOST_POINTS for one in found):
        return None
    return found


def round_points(table: tuple[int, ...], round_: int) -> int:
    """Round 0 scores nothing; a round past the table's end takes its last value."""
    if round_ <= 0 or not table:
        return 0
    return table[min(round_, len(table)) - 1]


def results(bracket: Bracket | None) -> tuple[set[tuple[int, int]], set[int]]:
    """The (round, winner) of every set played, and everyone who has lost one."""
    won: set[tuple[int, int]] = set()
    out: set[int] = set()
    if bracket is None:
        return won, out
    for match in bracket.matches.values():
        if not counted(match) or match.state != COMPLETE:
            continue
        if match.winner is not None:
            won.add((int(match.round), match.winner))
        if match.loser is not None:
            out.add(match.loser)
    return won, out


def score(
    tree: Tree, picks: dict[str, int], bracket: Bracket | None, table: tuple[int, ...]
) -> Score:
    """By (round, winning entrant), not by set: a member earns round r's points for every
    entrant they had winning in round r who won a round r set, wherever it was drawn."""
    won, out = results(bracket)
    points = correct = played = possible = 0
    marks: dict[str, str] = {}
    for key, entrant in cleaned(tree, picks).items():
        round_ = tree.nodes[key].round
        if round_ <= 0:
            continue
        worth = round_points(table, round_)
        if (round_, entrant) in won:
            points, correct, played = points + worth, correct + 1, played + 1
            marks[key] = HIT
        elif entrant in out:
            played += 1
            marks[key] = MISS
        else:
            possible += worth
    return Score(points, correct, played, possible, marks)


def final_total(bracket: Bracket | None) -> int | None:
    """The final's two scores added, once it is played."""
    if bracket is None:
        return None
    last = [
        match
        for match in bracket.matches.values()
        if counted(match) and match.round >= 1 and not match.winner_to
    ]
    if len(last) != 1:
        return None
    final = last[0]
    if final.state != COMPLETE or final.score_a is None or final.score_b is None:
        return None
    return int(final.score_a) + int(final.score_b)


def ranked(
    scores: dict[int, Score], tiebreaks: dict[int, int | None], total: int | None
) -> dict[int, int]:
    """Most points first; level sheets share a rank unless the tiebreak (closest guess of the
    final's total) separates them."""

    def order(user: int) -> tuple[int, int]:
        guess = tiebreaks.get(user)
        gap = abs(guess - total) if total is not None and guess is not None else NO_SEED
        return (-scores[user].points, gap)

    found: dict[int, int] = {}
    users = sorted(scores, key=lambda one: (order(one), one))
    for at, user in enumerate(users, start=1):
        before = users[at - 2] if at > 1 else None
        found[user] = found[before] if before is not None and order(before) == order(user) else at
    return found


__all__ = [
    "DEFAULT_POINTS",
    "HIT",
    "MISS",
    "Node",
    "Rule",
    "Score",
    "Tree",
    "cleaned",
    "final_total",
    "points_table",
    "predicted",
    "ranked",
    "results",
    "round_points",
    "score",
    "tree_of",
    "wrong",
]
