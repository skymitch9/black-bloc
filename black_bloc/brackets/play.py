"""The set state machine: every move is a transition over a copy, returning what changed."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from . import elimination, roundrobin, swiss
from .bestof import checked
from .model import (
    BY_OPPONENT,
    BY_TIME,
    BY_TO,
    BYE,
    CALLED,
    COMPLETE,
    DISPUTED,
    DONE,
    DOUBLE,
    FORFEITS,
    GRAND,
    LOSER,
    OPEN,
    PLAYABLE,
    READY,
    REPORTED,
    ROUND_ROBIN,
    SINGLE,
    SLOTS,
    SWISS,
    VOID,
    WAITING,
    WINNER,
    A,
    B,
    Bracket,
    BracketError,
    Match,
    Options,
    cleared,
)

FILLED = "filled"
PENDING = "pending"
DEAD = "dead"
BUILDERS = {
    SINGLE: elimination.single,
    DOUBLE: elimination.double,
    ROUND_ROBIN: roundrobin.build,
    SWISS: swiss.build,
}


@dataclass
class Moved:
    bracket: Bracket
    changed: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)


def build(entrants: list[int], options: Options, now: str | None = None) -> Moved:
    if len(entrants) < 2:
        raise BracketError("too_few", count=len(entrants))
    if len(set(entrants)) != len(entrants):
        raise BracketError("bad_order")
    bracket = BUILDERS[options.format](list(entrants), options)
    settle(bracket, now)
    return Moved(bracket, [match.key for match in bracket.ordered()])


def feeds(bracket: Bracket) -> dict[tuple[str, str], tuple[str, str]]:
    found: dict[tuple[str, str], tuple[str, str]] = {}
    for match in bracket.matches.values():
        if match.winner_to:
            found[(match.winner_to, match.winner_slot or A)] = (match.key, WINNER)
        if match.loser_to:
            found[(match.loser_to, match.loser_slot or A)] = (match.key, LOSER)
    return found


def slot_status(bracket: Bracket, match: Match, which: str, fed: dict) -> str:
    if match.slot(which) is not None:
        return FILLED
    source = fed.get((match.key, which))
    if source is None:
        return DEAD
    origin = bracket.matches[source[0]]
    if origin.state == VOID:
        return DEAD
    if origin.state == BYE and source[1] == LOSER:
        return DEAD
    return PENDING


def places_of(bracket: Bracket, match: Match) -> tuple[int | None, int | None]:
    if match.side == GRAND and match.reset_of is None:
        reset = next((one for one in bracket.matches.values() if one.reset_of == match.key), None)
        if reset is not None and match.forfeit is None and match.winner == match.slot_b:
            return None, None
    loser = match.loser_place if match.loser is not None else None
    return match.winner_place, loser


def put(match: Match, which: str, entrant: int | None) -> bool:
    attr = "slot_a" if which == A else "slot_b"
    if getattr(match, attr) == entrant:
        return False
    setattr(match, attr, entrant)
    return True


def deliver(bracket: Bracket, match: Match) -> set[str]:
    touched: set[str] = set()
    if match.state not in (COMPLETE, BYE):
        return touched
    for to, which, entrant in (
        (match.winner_to, match.winner_slot, match.winner),
        (match.loser_to, match.loser_slot, match.loser),
    ):
        if to and entrant is not None and put(bracket.matches[to], which or A, entrant):
            touched.add(to)
    if match.state in (COMPLETE, BYE):
        placed = places_of(bracket, match)
        if (match.placement_winner, match.placement_loser) != placed:
            match.placement_winner, match.placement_loser = placed
            touched.add(match.key)
    return touched


def finish(match: Match, side: str, now: str | None, *, forfeit: str | None = None) -> None:
    match.winner = match.slot(side)
    match.loser = match.slot(B if side == A else A)
    match.forfeit = forfeit
    match.state = COMPLETE
    match.completed_at = now


def wake(bracket: Bracket, match: Match, fed: dict, now: str | None) -> bool:
    if match.reset_of:
        origin = bracket.matches[match.reset_of]
        if origin.state == COMPLETE:
            if origin.forfeit is None and origin.winner == origin.slot_b:
                match.slot_a, match.slot_b = origin.slot_a, origin.slot_b
                match.state = READY
            else:
                match.state = VOID
            return True
        if origin.state in (BYE, VOID):
            match.state = VOID
            return True
        return False
    found = {which: slot_status(bracket, match, which, fed) for which in SLOTS}
    if found[A] == FILLED and found[B] == FILLED:
        match.state = READY
    elif FILLED in found.values() and DEAD in found.values():
        match.state = BYE
        match.winner = match.slot_a if found[A] == FILLED else match.slot_b
        match.completed_at = now
    elif found[A] == DEAD and found[B] == DEAD:
        match.state = VOID
    else:
        return False
    return True


def forfeit_out(bracket: Bracket, match: Match, now: str | None) -> bool:
    if match.state not in OPEN:
        return False
    gone = [which for which in SLOTS if match.slot(which) in bracket.withdrawn]
    if not gone:
        return False
    winner = A if gone == [B] else (B if gone == [A] else A)
    loser_slot = B if winner == A else A
    finish(match, winner, now, forfeit=bracket.withdrawn[match.slot(loser_slot)])
    match.score_a = match.score_b = None
    return True


def settle(bracket: Bracket, now: str | None = None) -> set[str]:
    """Byes, voids, forfeits and deliveries, until nothing moves; Swiss rounds appear here."""
    changed: set[str] = set()
    while True:
        moved: set[str] = set()
        fed = feeds(bracket)
        for match in bracket.ordered():
            moved |= deliver(bracket, match)
            if match.state == WAITING and wake(bracket, match, fed, now):
                moved.add(match.key)
            if forfeit_out(bracket, match, now):
                moved.add(match.key)
        if bracket.format == SWISS and swiss.next_round_due(bracket):
            moved |= set(swiss.add_round(bracket))
        if not moved:
            return changed
        changed |= moved


def moved(bracket: Bracket, before: Bracket, now: str | None) -> Moved:
    settle(bracket, now)
    changed = [match.key for match in bracket.ordered() if before.matches.get(match.key) != match]
    removed = [key for key in before.matches if key not in bracket.matches]
    return Moved(bracket, changed, removed)


def working(bracket: Bracket) -> Bracket:
    return copy.deepcopy(bracket)


def side_checked(side: str) -> str:
    if side not in SLOTS:
        raise BracketError("not_in_set")
    return side


def refuse_unplayable(match: Match) -> None:
    if match.state == WAITING:
        raise BracketError("not_ready", set=match.key)
    if match.state in (BYE, VOID):
        raise BracketError("not_playable", set=match.key)
    if match.state == COMPLETE:
        raise BracketError("already_complete", set=match.key)
    if match.state == DISPUTED:
        raise BracketError("disputed", set=match.key)


def call(bracket: Bracket, key: str, by: int | None, now: str | None) -> Moved:
    work = working(bracket)
    match = work.get(key)
    if match.state == CALLED:
        raise BracketError("already_called", set=key)
    if match.state != READY:
        refuse_unplayable(match)
        raise BracketError("already_reported", set=key)
    match.state, match.called_at, match.called_by = CALLED, now, by
    return moved(work, bracket, now)


def report(
    bracket: Bracket,
    key: str,
    side: str,
    score_a: int,
    score_b: int,
    by: int | None,
    now: str | None,
) -> Moved:
    """A player's report; the opponent reporting the same score is their confirm."""
    side = side_checked(side)
    work = working(bracket)
    match = work.get(key)
    if match.state not in (*PLAYABLE, REPORTED):
        refuse_unplayable(match)
    score_a, score_b = checked(match.best_of, score_a, score_b)
    if match.state == REPORTED and match.reported_side != side:
        if (match.score_a, match.score_b) != (score_a, score_b):
            raise BracketError(
                "reported_differently", set=key, score_a=match.score_a, score_b=match.score_b
            )
        return confirm(bracket, key, side, by, now)
    match.score_a, match.score_b = score_a, score_b
    match.reported_by, match.reported_side, match.reported_at = by, side, now
    match.state = REPORTED
    return moved(work, bracket, now)


def confirm(bracket: Bracket, key: str, side: str, by: int | None, now: str | None) -> Moved:
    side = side_checked(side)
    work = working(bracket)
    match = work.get(key)
    if match.state != REPORTED:
        refuse_unplayable(match)
        raise BracketError("not_reported", set=key)
    if match.reported_side == side:
        raise BracketError("own_report", set=key)
    agree(match, by, now, BY_OPPONENT)
    return moved(work, bracket, now)


def accept(bracket: Bracket, key: str, by: int | None, now: str | None) -> Moved:
    """The TO lets a reported or disputed score stand as reported."""
    work = working(bracket)
    match = work.get(key)
    if match.state not in (REPORTED, DISPUTED):
        if match.state in PLAYABLE:
            raise BracketError("not_reported", set=key)
        refuse_unplayable(match)
    agree(match, by, now, BY_TO)
    return moved(work, bracket, now)


def agree(match: Match, by: int | None, now: str | None, how: str) -> None:
    winner = A if (match.score_a or 0) > (match.score_b or 0) else B
    match.confirmed_by, match.confirmed_at, match.confirmed_how = by, now, how
    finish(match, winner, now)


def parsed(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def confirms_at(match: Match, minutes: int) -> datetime | None:
    reported = parsed(match.reported_at) if match.state == REPORTED else None
    return reported + timedelta(minutes=minutes) if reported is not None else None


def confirm_due(bracket: Bracket, now: datetime, minutes: int) -> Moved:
    """Every report nobody answered within the confirm time stands."""
    work = working(bracket)
    stamp = now.isoformat()
    for match in work.ordered():
        due = confirms_at(match, minutes)
        if due is not None and due <= now:
            agree(match, None, stamp, BY_TIME)
    return moved(work, bracket, stamp)


def dispute(
    bracket: Bracket, key: str, side: str, by: int | None, note: str | None, now: str | None
) -> Moved:
    side = side_checked(side)
    work = working(bracket)
    match = work.get(key)
    if match.state != REPORTED:
        refuse_unplayable(match)
        raise BracketError("not_reported", set=key)
    if match.reported_side == side:
        raise BracketError("own_report", set=key)
    match.state = DISPUTED
    match.disputed_by, match.disputed_at, match.dispute_note = by, now, note
    return moved(work, bracket, now)


def downstream(bracket: Bracket, match: Match) -> list[str]:
    """What a result reached: its winner's and loser's next sets, a reset it opened, and theirs."""
    if bracket.format == SWISS:
        return [key for key, one in bracket.matches.items() if one.round > match.round]
    found: list[str] = []
    for to, entrant in ((match.winner_to, match.winner), (match.loser_to, match.loser)):
        target = bracket.matches.get(to) if to else None
        if target is not None and entrant is not None and target.holds(entrant):
            found.append(target.key)
    found += [one.key for one in bracket.matches.values() if one.reset_of == match.key]
    return found


def undo(bracket: Bracket, match: Match) -> None:
    """Take a result back, and every result it fed; other branches are never touched."""
    if bracket.format == SWISS:
        for key in downstream(bracket, match):
            del bracket.matches[key]
        reopen(match)
        return
    for key in downstream(bracket, match):
        target = bracket.matches[key]
        if target.state in (COMPLETE, BYE):
            undo(bracket, target)
        for entrant in (match.winner, match.loser):
            which = target.side_of(entrant) if entrant is not None else None
            if which is not None:
                put(target, which, None)
        if target.reset_of == match.key:
            target.slot_a = target.slot_b = None
        reset_state(target)
    reopen(match)


def reset_state(match: Match) -> None:
    kept_a, kept_b = match.slot_a, match.slot_b
    fresh = cleared(match)
    for name in vars(fresh):
        setattr(match, name, getattr(fresh, name))
    match.slot_a, match.slot_b = kept_a, kept_b
    match.state = WAITING


def reopen(match: Match) -> None:
    reset_state(match)
    match.state = READY if match.slot_a is not None and match.slot_b is not None else WAITING


def reset(bracket: Bracket, key: str, by: int | None, now: str | None) -> Moved:
    work = working(bracket)
    match = work.get(key)
    if match.state in (BYE, VOID):
        raise BracketError("not_resettable", set=key)
    if match.state in (WAITING, READY):
        raise BracketError("nothing_to_reset", set=key)
    if match.state == COMPLETE:
        undo(work, match)
    else:
        reopen(match)
    return moved(work, bracket, now)


def override(
    bracket: Bracket,
    key: str,
    by: int | None,
    now: str | None,
    *,
    score_a: int | None = None,
    score_b: int | None = None,
    winner: str | None = None,
    forfeit: bool = False,
) -> Moved:
    """The TO's result: from any playable state, or correcting a finished set."""
    work = working(bracket)
    match = work.get(key)
    if match.state == WAITING:
        raise BracketError("not_ready", set=key)
    if match.state in (BYE, VOID):
        raise BracketError("not_playable", set=key)
    if forfeit:
        if winner not in SLOTS:
            raise BracketError("forfeit_needs_winner", set=key)
        side = winner
        scored: tuple[int | None, int | None] = (None, None)
    else:
        scored = checked(match.best_of, score_a, score_b)
        side = A if scored[0] > scored[1] else B
    if match.state == COMPLETE:
        undo(work, match)
    else:
        reopen(match)
    match.score_a, match.score_b = scored
    match.reported_by, match.reported_at = by, now
    match.confirmed_by, match.confirmed_at, match.confirmed_how = by, now, BY_TO
    finish(match, side, now, forfeit="to" if forfeit else None)
    return moved(work, bracket, now)


def withdraw(bracket: Bracket, entrant: int, why: str, now: str | None) -> Moved:
    """A DQ or a drop mid-bracket: every set they are in, now or later, is forfeited."""
    if why not in FORFEITS:
        raise BracketError("bad_reason")
    if entrant not in bracket.entrants:
        raise BracketError("not_in_bracket")
    if entrant in bracket.withdrawn:
        raise BracketError("already_out")
    work = working(bracket)
    work.withdrawn[entrant] = why
    return moved(work, bracket, now)


def reinstate(bracket: Bracket, entrant: int, now: str | None) -> Moved:
    """Lifts the DQ or drop; forfeits already played stand until a set is reset."""
    if entrant not in bracket.withdrawn:
        raise BracketError("not_out")
    work = working(bracket)
    del work.withdrawn[entrant]
    return moved(work, bracket, now)


def finished(bracket: Bracket) -> bool:
    if any(match.state not in DONE for match in bracket.matches.values()):
        return False
    if bracket.format == SWISS:
        return swiss.current_round(bracket) >= swiss.total_rounds(bracket)
    return True


def entrant_side(match: Match, entrant: int | None) -> str | None:
    return match.side_of(entrant) if entrant is not None else None
