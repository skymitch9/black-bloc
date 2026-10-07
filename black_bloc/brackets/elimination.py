"""Single and double elimination: the structure, its links, the drop pattern and the places."""

from __future__ import annotations

from .bestof import length_for
from .model import (
    GRAND,
    LOSERS,
    THIRD,
    WINNERS,
    A,
    B,
    Bracket,
    Match,
    Options,
    key_of,
)
from .seeding import bracket_size, first_round


def rounds_of(size: int) -> int:
    return size.bit_length() - 1


def winners_matches(size: int, round_: int) -> int:
    return size >> round_


def losers_rounds(size: int) -> int:
    return max(0, 2 * rounds_of(size) - 2)


def losers_matches(size: int, round_: int) -> int:
    return size >> ((round_ + 1) // 2 + 1)


def slot_for(position: int) -> str:
    return A if position % 2 == 1 else B


def flipped(position: int, count: int) -> int:
    """The drop pattern: a winners loser lands beside the neighbouring pair, never its own."""
    if count == 1:
        return 1
    return position + 1 if position % 2 == 1 else position - 1


def drop_target(size: int, round_: int, position: int) -> tuple[str, str]:
    """Where the loser of winners round `round_`, set `position`, goes."""
    if losers_rounds(size) == 0:
        return key_of(GRAND, 1, 1), B
    if round_ == 1:
        return key_of(LOSERS, 1, (position + 1) // 2), slot_for(position)
    target = 2 * round_ - 2
    return key_of(LOSERS, target, flipped(position, losers_matches(size, target))), B


def winners_alive(size: int, round_: int) -> int:
    return size if round_ == 1 else 4 * winners_matches(size, round_)


def losers_alive(size: int, round_: int) -> int:
    count = losers_matches(size, round_)
    return 4 * count if round_ % 2 == 1 else 3 * count


def losers_place(size: int, round_: int) -> int:
    return 3 + sum(
        losers_matches(size, later) for later in range(round_ + 1, losers_rounds(size) + 1)
    )


def seat(matches: dict[str, Match], pairs: list[tuple[int | None, int | None]]) -> None:
    for position, (slot_a, slot_b) in enumerate(pairs, start=1):
        found = matches[key_of(WINNERS, 1, position)]
        found.slot_a, found.slot_b = slot_a, slot_b


def single(entrants: list[int], options: Options) -> Bracket:
    size = bracket_size(len(entrants))
    last = rounds_of(size)
    matches: dict[str, Match] = {}
    third = options.third_place and last >= 2
    for round_ in range(1, last + 1):
        count = winners_matches(size, round_)
        for position in range(1, count + 1):
            final = round_ == last
            alive = 2 * count
            found = Match(
                key=key_of(WINNERS, round_, position),
                side=WINNERS,
                round=round_,
                position=position,
                best_of=length_for(options, alive, final=final),
                alive=alive,
                loser_place=2 if final else (None if third and round_ == last - 1 else count + 1),
                winner_place=1 if final else None,
            )
            if not final:
                found.winner_to = key_of(WINNERS, round_ + 1, (position + 1) // 2)
                found.winner_slot = slot_for(position)
            if third and round_ == last - 1:
                found.loser_to, found.loser_slot = key_of(THIRD, 1, 1), slot_for(position)
            matches[found.key] = found
    if third:
        matches[key_of(THIRD, 1, 1)] = Match(
            key=key_of(THIRD, 1, 1),
            side=THIRD,
            round=1,
            position=1,
            best_of=length_for(options, 4, final=False),
            alive=4,
            winner_place=3,
            loser_place=4,
        )
    seat(matches, first_round(entrants))
    return Bracket(options=options, entrants=list(entrants), matches=matches)


def double(entrants: list[int], options: Options) -> Bracket:
    size = bracket_size(len(entrants))
    last = rounds_of(size)
    lower = losers_rounds(size)
    matches: dict[str, Match] = {}
    for round_ in range(1, last + 1):
        count = winners_matches(size, round_)
        for position in range(1, count + 1):
            alive = winners_alive(size, round_)
            found = Match(
                key=key_of(WINNERS, round_, position),
                side=WINNERS,
                round=round_,
                position=position,
                best_of=length_for(options, alive, final=False),
                alive=alive,
            )
            if round_ == last:
                found.winner_to, found.winner_slot = key_of(GRAND, 1, 1), A
            else:
                found.winner_to = key_of(WINNERS, round_ + 1, (position + 1) // 2)
                found.winner_slot = slot_for(position)
            found.loser_to, found.loser_slot = drop_target(size, round_, position)
            matches[found.key] = found
    for round_ in range(1, lower + 1):
        count = losers_matches(size, round_)
        for position in range(1, count + 1):
            alive = losers_alive(size, round_)
            found = Match(
                key=key_of(LOSERS, round_, position),
                side=LOSERS,
                round=round_,
                position=position,
                best_of=length_for(options, alive, final=False),
                alive=alive,
                loser_place=losers_place(size, round_),
            )
            if round_ == lower:
                found.winner_to, found.winner_slot = key_of(GRAND, 1, 1), B
            elif round_ % 2 == 1:
                found.winner_to, found.winner_slot = key_of(LOSERS, round_ + 1, position), A
            else:
                found.winner_to = key_of(LOSERS, round_ + 1, (position + 1) // 2)
                found.winner_slot = slot_for(position)
            matches[found.key] = found
    grand = Match(
        key=key_of(GRAND, 1, 1),
        side=GRAND,
        round=1,
        position=1,
        best_of=length_for(options, 2, final=True),
        alive=2,
        winner_place=1,
        loser_place=2,
    )
    matches[grand.key] = grand
    if options.grand_final_reset:
        reset = Match(
            key=key_of(GRAND, 2, 1),
            side=GRAND,
            round=2,
            position=1,
            best_of=length_for(options, 2, final=True),
            alive=2,
            reset_of=grand.key,
            winner_place=1,
            loser_place=2,
        )
        matches[reset.key] = reset
    seat(matches, first_round(entrants))
    return Bracket(options=options, entrants=list(entrants), matches=matches)
