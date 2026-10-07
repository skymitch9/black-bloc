"""The bracket's plain data: sets, options, the whole bracket, and the engine's one refusal."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

SINGLE = "single"
DOUBLE = "double"
ROUND_ROBIN = "round_robin"
SWISS = "swiss"
FORMATS = (SINGLE, DOUBLE, ROUND_ROBIN, SWISS)
ELIMINATION = (SINGLE, DOUBLE)

WINNERS = "winners"
LOSERS = "losers"
GRAND = "grand"
THIRD = "third"
RR = "rr"
SWISS_SIDE = "swiss"
SIDES = (WINNERS, LOSERS, GRAND, THIRD, RR, SWISS_SIDE)
SIDE_LETTERS = {WINNERS: "W", LOSERS: "L", GRAND: "G", THIRD: "T", RR: "R", SWISS_SIDE: "S"}

WAITING = "waiting"
READY = "ready"
CALLED = "called"
REPORTED = "reported"
DISPUTED = "disputed"
COMPLETE = "complete"
BYE = "bye"
VOID = "void"
STATES = (WAITING, READY, CALLED, REPORTED, DISPUTED, COMPLETE, BYE, VOID)
PLAYABLE = (READY, CALLED)
OPEN = (READY, CALLED, REPORTED, DISPUTED)
DONE = (COMPLETE, BYE, VOID)

A = "a"
B = "b"
SLOTS = (A, B)

BY_OPPONENT = "opponent"
BY_TIME = "time"
BY_TO = "to"
CONFIRMED_HOW = (BY_OPPONENT, BY_TIME, BY_TO)

DQ = "dq"
DROP = "drop"
FORFEITS = (DQ, DROP)

WINNER = "winner"
LOSER = "loser"


class BracketError(Exception):
    """A move the bracket refuses; `code` picks the worded answer, `fields` fill it."""

    def __init__(self, code: str, **fields: Any) -> None:
        super().__init__(code)
        self.code = code
        self.fields = fields


@dataclass(frozen=True)
class Options:
    format: str = DOUBLE
    third_place: bool = False
    grand_final_reset: bool = True
    swiss_rounds: int | None = None
    best_of: int = 3
    best_of_from_round: int | None = None
    best_of_late: int = 5
    best_of_finals: int = 5


@dataclass
class Match:
    key: str
    side: str
    round: int
    position: int
    best_of: int
    state: str = WAITING
    slot_a: int | None = None
    slot_b: int | None = None
    winner_to: str | None = None
    winner_slot: str | None = None
    loser_to: str | None = None
    loser_slot: str | None = None
    reset_of: str | None = None
    alive: int = 0
    winner_place: int | None = None
    loser_place: int | None = None
    score_a: int | None = None
    score_b: int | None = None
    winner: int | None = None
    loser: int | None = None
    forfeit: str | None = None
    called_at: str | None = None
    called_by: int | None = None
    reported_by: int | None = None
    reported_side: str | None = None
    reported_at: str | None = None
    confirmed_by: int | None = None
    confirmed_at: str | None = None
    confirmed_how: str | None = None
    disputed_by: int | None = None
    disputed_at: str | None = None
    dispute_note: str | None = None
    completed_at: str | None = None
    placement_winner: int | None = None
    placement_loser: int | None = None

    def slot(self, which: str) -> int | None:
        return self.slot_a if which == A else self.slot_b

    def side_of(self, entrant: int) -> str | None:
        if entrant is None:
            return None
        if self.slot_a == entrant:
            return A
        if self.slot_b == entrant:
            return B
        return None

    def other(self, entrant: int) -> int | None:
        if self.slot_a == entrant:
            return self.slot_b
        if self.slot_b == entrant:
            return self.slot_a
        return None

    def holds(self, entrant: int) -> bool:
        return entrant is not None and entrant in (self.slot_a, self.slot_b)


RESULT_FIELDS = (
    "score_a",
    "score_b",
    "winner",
    "loser",
    "forfeit",
    "called_at",
    "called_by",
    "reported_by",
    "reported_side",
    "reported_at",
    "confirmed_by",
    "confirmed_at",
    "confirmed_how",
    "disputed_by",
    "disputed_at",
    "dispute_note",
    "completed_at",
    "placement_winner",
    "placement_loser",
)


def cleared(match: Match) -> Match:
    return replace(match, **{name: None for name in RESULT_FIELDS})


@dataclass
class Bracket:
    options: Options
    entrants: list[int]
    matches: dict[str, Match] = field(default_factory=dict)
    withdrawn: dict[int, str] = field(default_factory=dict)
    final_order: list[int] = field(default_factory=list)

    @property
    def format(self) -> str:
        return self.options.format

    def ordered(self) -> list[Match]:
        return sorted(self.matches.values(), key=order_key)

    def get(self, key: str) -> Match:
        found = self.matches.get(key)
        if found is None:
            raise BracketError("no_set", set=key)
        return found


SIDE_ORDER = {WINNERS: 0, LOSERS: 1, THIRD: 2, GRAND: 3, RR: 0, SWISS_SIDE: 0}


def order_key(match: Match) -> tuple[int, int, int, int]:
    """Play order: winners round r, then losers, third place and the grand final last."""
    if match.side == LOSERS:
        return (match.round // 2 + 1, 1, match.round, match.position)
    if match.side in (GRAND, THIRD):
        return (10_000 + match.round, SIDE_ORDER[match.side], match.round, match.position)
    return (match.round, SIDE_ORDER[match.side], match.round, match.position)


def key_of(side: str, round_: int, position: int) -> str:
    return f"{SIDE_LETTERS[side]}{round_}-{position}"
