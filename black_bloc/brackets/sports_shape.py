"""A feed's bracket as engine sets: explicit links, tree positions, and a slot the feed has not
named yet held open by a pending feeder."""

from __future__ import annotations

from dataclasses import dataclass

from .model import BYE, SINGLE, WINNERS, A, B, Bracket, Match, Options, key_of

PENDING_PREFIX = "pending-"
OPTIONS = Options(
    format=SINGLE,
    third_place=False,
    grand_final_reset=False,
    best_of=1,
    best_of_late=1,
    best_of_finals=1,
)


@dataclass(frozen=True)
class Planned:
    source_key: str
    round: int
    slot_a: int | None
    slot_b: int | None
    best_of: int = 1


def pending_key(key: str, slot: str) -> str:
    return f"{PENDING_PREFIX}{key}-{slot}"


def is_pending(match: Match | str) -> bool:
    key = match if isinstance(match, str) else match.key
    return str(key).startswith(PENDING_PREFIX)


def positions(planned: list[Planned], links: dict[str, tuple[str, str]]) -> dict[str, int]:
    """Heap positions from the final down (a feeder of slot a is 2p-1, of b 2p); anything the
    walk misses takes the next free position of its round, in feed order."""
    known = {one.source_key: one for one in planned}
    feeders: dict[str, list[tuple[str, str]]] = {}
    for source, (target, slot) in links.items():
        if source in known and target in known:
            feeders.setdefault(target, []).append((source, slot))
    found: dict[str, int] = {}
    used: dict[int, set[int]] = {}

    def place(key: str, at: int) -> None:
        round_ = known[key].round
        if key in found or at in used.setdefault(round_, set()):
            return
        found[key] = at
        used[round_].add(at)
        for source, slot in feeders.get(key, []):
            place(source, 2 * at - (1 if slot == A else 0))

    tops = [
        one
        for one in planned
        if one.source_key not in links or links[one.source_key][0] not in known
    ]
    for top in sorted(tops, key=lambda one: -one.round):
        place(top.source_key, max(used.get(top.round, {0})) + 1)
    for one in planned:
        if one.source_key not in found:
            at = max(used.setdefault(one.round, {0})) + 1
            found[one.source_key] = at
            used[one.round].add(at)
    return found


def places(planned: list[Planned], key: str, last: int) -> tuple[int | None, int | None]:
    round_ = next(one.round for one in planned if one.source_key == key)
    if round_ == last:
        return 1, 2
    after = sum(1 for one in planned if one.round == round_ + 1)
    return None, 1 + 2 * after if after else None


def shaped(planned: list[Planned], links: dict[str, tuple[str, str]]) -> tuple[Bracket, dict]:
    """The sets, unsettled, and each set's feed key; links to a game the feed lacks are dropped."""
    known = {one.source_key: one for one in planned}
    kept = {key: link for key, link in links.items() if key in known and link[0] in known}
    at = positions(planned, kept)
    keys = {one.source_key: key_of(WINNERS, one.round, at[one.source_key]) for one in planned}
    last = max((one.round for one in planned), default=1)
    matches: dict[str, Match] = {}
    for one in sorted(planned, key=lambda item: (item.round, at[item.source_key])):
        key = keys[one.source_key]
        winner_place, loser_place = places(planned, one.source_key, last)
        link = kept.get(one.source_key)
        matches[key] = Match(
            key=key,
            side=WINNERS,
            round=one.round,
            position=at[one.source_key],
            best_of=max(1, int(one.best_of or 1)),
            slot_a=one.slot_a,
            slot_b=one.slot_b,
            winner_to=keys[link[0]] if link else None,
            winner_slot=link[1] if link else None,
            winner_place=winner_place,
            loser_place=loser_place,
        )
    bracket = Bracket(options=OPTIONS, entrants=seated(matches), matches=matches)
    hold_open(bracket)
    return bracket, {key: source for source, key in keys.items()}


def seated(matches: dict[str, Match]) -> list[int]:
    found: list[int] = []
    for match in matches.values():
        for entrant in (match.slot_a, match.slot_b):
            if entrant is not None and entrant not in found:
                found.append(entrant)
    return found


def fed_slots(bracket: Bracket) -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for match in bracket.matches.values():
        if match.winner_to:
            found.add((match.winner_to, match.winner_slot or A))
        if match.loser_to:
            found.add((match.loser_to, match.loser_slot or A))
    return found


def hold_open(bracket: Bracket) -> list[str]:
    """Every empty slot nothing feeds gets a pending feeder, so the engine never byes it."""
    fed = fed_slots(bracket)
    added: list[str] = []
    for match in list(bracket.matches.values()):
        if is_pending(match):
            continue
        for slot in (A, B):
            if match.slot(slot) is None and (match.key, slot) not in fed:
                key = pending_key(match.key, slot)
                bracket.matches[key] = Match(
                    key=key,
                    side=WINNERS,
                    round=match.round - 1,
                    position=match.position,
                    best_of=1,
                    state=BYE,
                    winner_to=match.key,
                    winner_slot=slot,
                )
                added.append(key)
    return added


def let_go(bracket: Bracket, key: str, slot: str) -> str | None:
    """A slot that is now filled or fed drops its pending feeder; answers the removed key."""
    found = pending_key(key, slot)
    if found in bracket.matches:
        del bracket.matches[found]
        return found
    return None


__all__ = [
    "OPTIONS",
    "PENDING_PREFIX",
    "Planned",
    "fed_slots",
    "hold_open",
    "is_pending",
    "let_go",
    "pending_key",
    "positions",
    "shaped",
]
