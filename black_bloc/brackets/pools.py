"""Pools into a bracket: the snake split, a bracket per pool, the progression, the whole places."""

from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from typing import Any

from . import elimination, play, standings
from .model import (
    CALLED,
    COMPLETE,
    DISPUTED,
    DONE,
    DOUBLE,
    ELIMINATION,
    FINAL,
    FORFEITS,
    LOSERS,
    POOL_FORMATS,
    POOLS,
    READY,
    REPORTED,
    SWISS,
    WAITING,
    WINNERS,
    A,
    B,
    Bracket,
    BracketError,
    Match,
    Options,
    Plan,
    key_of,
)
from .play import Moved
from .seeding import bracket_size, standard_order

WAITS_FOR_FINAL = "final"
MOST_POOLS = 16
PLAYED = (REPORTED, DISPUTED, COMPLETE)


def letter(pool: int) -> str:
    return chr(64 + int(pool))


def prefixed(pool: int, key: str) -> str:
    return f"{letter(pool)}.{key}"


def inner(key: str) -> str:
    return str(key).split(".", 1)[-1]


def pool_of(key: str) -> int | None:
    head, dot, _ = str(key).partition(".")
    if not dot or len(head) != 1 or not "A" <= head <= "Z":
        return None
    return ord(head) - 64


def split(entrants: list[int], count: int) -> list[list[int]]:
    """Seeds dealt in snake order (A B B A A B …), so every pool gets a fair share of the top."""
    found: list[list[int]] = [[] for _ in range(count)]
    for at, entrant in enumerate(entrants):
        row, column = divmod(at, count)
        found[column if row % 2 == 0 else count - 1 - column].append(entrant)
    return found


def pool_options(plan: Plan) -> Options:
    return Options(format=plan.format, swiss_rounds=plan.swiss_rounds, best_of=plan.best_of)


def checked(count: int, plan: Plan, final_format: str) -> None:
    """Refuses a plan the field cannot fill, in the engine's words."""
    if plan.format not in POOL_FORMATS or not 1 <= plan.count <= MOST_POOLS:
        raise BracketError("bad_pools")
    if final_format not in ELIMINATION:
        raise BracketError("pools_need_elimination")
    if count < 2 * plan.count:
        raise BracketError("too_few_for_pools", count=count, pools=plan.count)
    smallest = count // plan.count
    if not 1 <= plan.advance <= smallest or plan.advance * plan.count < 2:
        raise BracketError("advance_too_many", advance=plan.advance, smallest=smallest)
    if final_format == DOUBLE and plan.losers_from is not None:
        if not 2 <= plan.losers_from <= plan.advance:
            raise BracketError("bad_losers_from", place=plan.losers_from, advance=plan.advance)
    most = max(1, smallest - 1)
    if plan.format == SWISS and plan.swiss_rounds and plan.swiss_rounds > most:
        raise BracketError("too_many_pool_rounds", rounds=plan.swiss_rounds, most=most)


def build(entrants: list[int], options: Options, plan: Plan, now: str | None = None) -> Moved:
    """The pools phase: one round robin or Swiss per pool, every set keyed by its pool letter."""
    if len(set(entrants)) != len(entrants):
        raise BracketError("bad_order")
    checked(len(entrants), plan, options.format)
    parts = [play.build(members, pool_options(plan), now).bracket for members in split(
        list(entrants), plan.count
    )]
    whole = joined(Bracket(options, list(entrants), plan=plan), parts, None)
    return Moved(whole, [match.key for match in whole.ordered()])


def part(whole: Bracket, matches: dict[str, Match], options: Options) -> Bracket:
    seated = {one for match in matches.values() for one in (match.slot_a, match.slot_b) if one}
    return Bracket(
        options=options,
        entrants=[one for one in whole.entrants if one in seated],
        matches=matches,
        withdrawn={one: why for one, why in whole.withdrawn.items() if one in seated},
        final_order=[one for one in whole.final_order if one in seated],
    )


def pool_parts(whole: Bracket) -> list[Bracket]:
    """Each pool as its own bracket, its keys without the letter."""
    plan = whole.plan
    assert plan is not None
    found = []
    for pool in range(1, plan.count + 1):
        matches = {
            inner(match.key): replace(match, key=inner(match.key))
            for match in whole.matches.values()
            if match.phase == POOLS and match.pool == pool
        }
        found.append(part(whole, matches, pool_options(plan)))
    return found


def final_part(whole: Bracket) -> Bracket | None:
    matches = {
        key: copy.deepcopy(match) for key, match in whole.matches.items() if match.phase == FINAL
    }
    return part(whole, matches, whole.options) if matches else None


def joined(base: Bracket, parts: list[Bracket], final: Bracket | None) -> Bracket:
    matches: dict[str, Match] = {}
    for pool, one in enumerate(parts, start=1):
        for match in one.matches.values():
            key = prefixed(pool, match.key)
            matches[key] = replace(match, key=key, phase=POOLS, pool=pool)
    for match in (final.matches.values() if final else ()):
        matches[match.key] = replace(match, phase=FINAL, pool=None)
    return Bracket(
        options=base.options,
        entrants=list(base.entrants),
        matches=matches,
        withdrawn=dict(base.withdrawn),
        final_order=list(base.final_order),
        plan=base.plan,
    )


def diffed(after: Bracket, before: Bracket) -> Moved:
    changed = [m.key for m in after.ordered() if before.matches.get(m.key) != m]
    removed = [key for key in before.matches if key not in after.matches]
    return Moved(after, changed, removed)


def named(error: BracketError, pool: int) -> BracketError:
    if "set" in error.fields:
        error.fields["set"] = prefixed(pool, str(error.fields["set"]))
    return error


def on_set(whole: Bracket, key: str, move: Callable[..., Moved], *args: Any, closes: bool = False,
           **kw: Any) -> Moved:
    """A set move on the pool or the final that holds the set; the rest is carried as it was."""
    pools, final = pool_parts(whole), final_part(whole)
    pool = pool_of(key)
    if pool is None:
        if final is None or key not in final.matches:
            raise BracketError("no_set", set=key)
        moved = move(final, key, *args, **kw)
        return diffed(joined(whole, pools, moved.bracket), whole)
    if not 1 <= pool <= len(pools) or inner(key) not in pools[pool - 1].matches:
        raise BracketError("no_set", set=key)
    if closes and final is not None:
        raise BracketError("pools_closed", set=key)
    try:
        moved = move(pools[pool - 1], inner(key), *args, **kw)
    except BracketError as error:
        raise named(error, pool) from None
    pools[pool - 1] = moved.bracket
    return diffed(joined(whole, pools, final), whole)


def settled(work: Bracket, before: Bracket, now: str | None) -> Moved:
    pools, final = pool_parts(work), final_part(work)
    for one in [*pools, *([final] if final else [])]:
        play.settle(one, now)
    return diffed(joined(work, pools, final), before)


def call(bracket: Bracket, key: str, by: int | None, now: str | None) -> Moved:
    if bracket.plan is None:
        return play.call(bracket, key, by, now)
    return on_set(bracket, key, play.call, by, now)


def report(bracket: Bracket, key: str, side: str, score_a: int, score_b: int, by: int | None,
           now: str | None) -> Moved:
    if bracket.plan is None:
        return play.report(bracket, key, side, score_a, score_b, by, now)
    return on_set(bracket, key, play.report, side, score_a, score_b, by, now)


def confirm_report(bracket: Bracket, key: str, side: str, by: int | None, now: str | None) -> Moved:
    if bracket.plan is None:
        return play.confirm_report(bracket, key, side, by, now)
    return on_set(bracket, key, play.confirm_report, side, by, now)


def accept(bracket: Bracket, key: str, by: int | None, now: str | None) -> Moved:
    if bracket.plan is None:
        return play.accept(bracket, key, by, now)
    return on_set(bracket, key, play.accept, by, now)


def dispute(bracket: Bracket, key: str, side: str, by: int | None, note: str | None,
            now: str | None) -> Moved:
    if bracket.plan is None:
        return play.dispute(bracket, key, side, by, note, now)
    return on_set(bracket, key, play.dispute, side, by, note, now)


def reset(bracket: Bracket, key: str, by: int | None, now: str | None) -> Moved:
    if bracket.plan is None:
        return play.reset(bracket, key, by, now)
    return on_set(bracket, key, play.reset, by, now, closes=True)


def override(bracket: Bracket, key: str, by: int | None, now: str | None, **kw: Any) -> Moved:
    if bracket.plan is None:
        return play.override(bracket, key, by, now, **kw)
    return on_set(bracket, key, play.override, by, now, closes=True, **kw)


def confirm_due(bracket: Bracket, now: datetime, minutes: int) -> Moved:
    if bracket.plan is None:
        return play.confirm_due(bracket, now, minutes)
    pools, final = pool_parts(bracket), final_part(bracket)
    pools = [play.confirm_due(one, now, minutes).bracket for one in pools]
    if final is not None:
        final = play.confirm_due(final, now, minutes).bracket
    return diffed(joined(bracket, pools, final), bracket)


def withdraw(bracket: Bracket, entrant: int, why: str, now: str | None) -> Moved:
    if bracket.plan is None:
        return play.withdraw(bracket, entrant, why, now)
    if why not in FORFEITS:
        raise BracketError("bad_reason")
    if entrant not in bracket.entrants:
        raise BracketError("not_in_bracket")
    if entrant in bracket.withdrawn:
        raise BracketError("already_out")
    work = copy.deepcopy(bracket)
    work.withdrawn[entrant] = why
    return settled(work, bracket, now)


def reinstate(bracket: Bracket, entrant: int, now: str | None) -> Moved:
    if bracket.plan is None:
        return play.reinstate(bracket, entrant, now)
    if entrant not in bracket.withdrawn:
        raise BracketError("not_out")
    work = copy.deepcopy(bracket)
    del work.withdrawn[entrant]
    return settled(work, bracket, now)


def pools_finished(bracket: Bracket) -> bool:
    return bracket.plan is not None and all(play.finished(one) for one in pool_parts(bracket))


def finished(bracket: Bracket) -> bool:
    if bracket.plan is None:
        return play.finished(bracket)
    final = final_part(bracket)
    return final is not None and play.finished(final)


def sets_to_play(bracket: Bracket) -> tuple[int, int]:
    if bracket.plan is None:
        return play.sets_to_play(bracket)
    final = final_part(bracket)
    if final is not None:
        return play.sets_to_play(final)
    counts = [play.sets_to_play(one) for one in pool_parts(bracket)]
    return sum(one[0] for one in counts), sum(one[1] for one in counts)


def still_in(pool: Bracket) -> list[standings.Row]:
    return [row for row in standings.table(pool) if row.entrant not in pool.withdrawn]


def leaders(pool: Bracket, advance: int) -> list[int]:
    """The pool's top `advance` still in, by the table as it stands."""
    return [row.entrant for row in still_in(pool)[:advance]]


def cut(pool: Bracket, advance: int, number: int) -> list[int]:
    """The pool's top `advance` still in; a tie across the line is refused until ordered."""
    rows = still_in(pool)
    if len(rows) > advance > 0 and rows[advance - 1].place == rows[advance].place:
        tied = [row.entrant for row in rows if row.place == rows[advance].place]
        raise BracketError("pool_tie", pool=letter(number), place=advance, tied=tied)
    return [row.entrant for row in rows[:advance]]


def told_with_withdrawn(whole: Bracket) -> list[int]:
    """The organiser's order, then everyone withdrawn they did not name: the out are placed last."""
    if not whole.final_order:
        return list(whole.final_order)
    rest = [one for one in whole.withdrawn if one not in whole.final_order]
    return [*whole.final_order, *rest]


def tie_of(pool: Bracket, advance: int, number: int) -> list[int]:
    try:
        cut(pool, advance, number)
    except BracketError as error:
        return list(error.fields.get("tied") or [])
    return []


def tiers(cuts: list[list[int]], plan: Plan, final_format: str) -> tuple[list[int], list[int]]:
    """Advancers by pool place then pool; the `losers_from` places start in losers (double only)."""
    winners: list[int] = []
    losers: list[int] = []
    losers_from = plan.losers_from if final_format == DOUBLE else None
    for place in range(1, plan.advance + 1):
        for found in cuts:
            if place <= len(found):
                into = losers if losers_from and place >= losers_from else winners
                into.append(found[place - 1])
    if not winners:
        return losers, []
    return winners, losers


def seated(order: list[int], size: int) -> list[tuple[int | None, int | None]]:
    spots = [order[seed - 1] if seed <= len(order) else None for seed in standard_order(size)]
    return [(spots[at], spots[at + 1]) for at in range(0, size, 2)]


def clashes(order: list[int], size: int, home: dict[int, int]) -> int:
    return sum(
        1 for a, b in seated(order, size) if a is not None and b is not None and home[a] == home[b]
    )


def apart(order: list[int], size: int, home: dict[int, int], tier: dict[int, int]) -> list[int]:
    """Two from one pool never meet in the first set: the lower one swaps within its pool place."""
    order = list(order)
    while clashes(order, size, home):
        now = clashes(order, size, home)
        pair = next(
            (a, b) for a, b in seated(order, size)
            if a is not None and b is not None and home[a] == home[b]
        )
        lower = max(pair, key=order.index)
        at = order.index(lower)
        others = sorted(
            (one for one in order if tier[one] == tier[lower] and one not in pair),
            key=lambda one: abs(order.index(one) - at),
        )
        for other in others:
            trial = list(order)
            there = trial.index(other)
            trial[at], trial[there] = other, lower
            if clashes(trial, size, home) < now:
                order = trial
                break
        else:
            return order
    return order


def entered(winners: list[int], losers: list[int], options: Options, now: str | None) -> Bracket:
    """A double elimination: `losers` start in losers round 1, `winners` in winners round 2."""
    size = max(bracket_size(len(winners)), bracket_size(len(losers)))
    shell = elimination.double(list(range(1, 2 * size + 1)), options)
    for position in range(1, size + 1):
        del shell.matches[key_of(WINNERS, 1, position)]
    for side, round_, people in ((WINNERS, 2, winners), (LOSERS, 1, losers)):
        for position, (a, b) in enumerate(seated(people, size), start=1):
            match = shell.matches[key_of(side, round_, position)]
            match.slot_a, match.slot_b = a, b
    bracket = Bracket(options=options, entrants=[*winners, *losers], matches=shell.matches)
    play.settle(bracket, now)
    play.pace(bracket)
    placed_by_alive(bracket)
    return bracket


def first_met(bracket: Bracket, entrant: int) -> tuple[bool, list[int]]:
    """Who an entrant can meet in their first played set: the one seated (True), or the two
    the feeding set holds (False)."""
    live = next(
        (m for m in bracket.ordered() if m.holds(entrant) and m.state in (READY, CALLED, WAITING)),
        None,
    )
    if live is None:
        return True, []
    other = live.other(entrant)
    if other is not None:
        return True, [other]
    open_slot = B if live.slot_a == entrant else A
    feeder = next(
        (
            m for m in bracket.matches.values()
            if (m.winner_to, m.winner_slot) == (live.key, open_slot)
            or (m.loser_to, m.loser_slot) == (live.key, open_slot)
        ),
        None,
    )
    if feeder is None:
        return True, []
    return False, [one for one in (feeder.slot_a, feeder.slot_b) if one is not None]


def first_apart(winners: list[int], losers: list[int], options: Options, home: dict[int, int],
                tier: dict[int, int], now: str | None) -> Bracket:
    """Losers-side entrants swap within their pool place so their first played set avoids
    their own pool where it can; a seat's opponents stay put when its occupant moves."""
    built = entered(winners, losers, options, now)
    seat = {one: at for at, one in enumerate(losers)}
    sure: list[bool] = []
    faces: list[list[tuple[bool, int]]] = []
    for one in losers:
        seated_, them = first_met(built, one)
        sure.append(seated_)
        faces.append([(other in seat, seat.get(other, other)) for other in them])
    watchers: list[set[int]] = [{at} for at in range(len(losers))]
    for at, found in enumerate(faces):
        for is_seat, ref in found:
            if is_seat:
                watchers[ref].add(at)

    def term(order: list[int], at: int) -> tuple[int, int]:
        same = sum(
            1 for is_seat, ref in faces[at]
            if home[order[ref] if is_seat else ref] == home[order[at]]
        )
        return (same, 0) if sure[at] else (0, same)

    def total(order: list[int], seats: set[int]) -> tuple[int, int]:
        found = [term(order, at) for at in seats]
        return sum(one[0] for one in found), sum(one[1] for one in found)

    order = list(losers)
    better = True
    while better:
        better = False
        for at in range(len(order)):
            if total(order, {at}) == (0, 0):
                continue
            for there in range(len(order)):
                if there == at or tier[order[at]] != tier[order[there]]:
                    continue
                touched = watchers[at] | watchers[there]
                before = total(order, touched)
                trial = list(order)
                trial[at], trial[there] = trial[there], trial[at]
                if total(trial, touched) < before:
                    order, better = trial, True
                    break
    return built if order == losers else entered(winners, order, options, now)


def placed_by_alive(bracket: Bracket) -> None:
    """A set that knocks someone out places them below everyone still in when it is played."""
    last = max((one.round for one in bracket.matches.values() if one.side == WINNERS), default=1)
    out: dict[tuple[int, int, int], int] = {}
    for match in play.rehearsed(bracket).matches.values():
        if match.state == COMPLETE and match.loser_to is None and match.side in (WINNERS, LOSERS):
            here = play.level(match, last)
            out[here] = out.get(here, 0) + 1
    for match in bracket.matches.values():
        if match.side in (WINNERS, LOSERS) and match.loser_to is None and match.loser_place:
            match.loser_place = match.alive - out.get(play.level(match, last), 0) + 1


def final_of(whole: Bracket, now: str | None) -> Bracket:
    plan = whole.plan
    assert plan is not None
    pools = pool_parts(whole)
    cuts = [cut(one, plan.advance, number) for number, one in enumerate(pools, start=1)]
    winners, losers = tiers(cuts, plan, whole.options.format)
    if len(winners) + len(losers) < 2:
        raise BracketError("too_few", count=len(winners) + len(losers))
    home = {one: number for number, found in enumerate(cuts, start=1) for one in found}
    tier = {one: place for found in cuts for place, one in enumerate(found, start=1)}
    if not losers:
        order = apart(winners, bracket_size(len(winners)), home, tier)
        return play.build(order, whole.options, now).bracket
    size = max(bracket_size(len(winners)), bracket_size(len(losers)))
    return first_apart(apart(winners, size, home, tier), apart(losers, size, home, tier),
                       whole.options, home, tier, now)


def advance(whole: Bracket, now: str | None) -> Moved:
    """Builds the final from the pools' top N; refused while a pool is open or tied on the line."""
    if whole.plan is None:
        raise BracketError("no_pools")
    if final_part(whole) is not None:
        raise BracketError("already_advanced")
    left = sum(
        1 for one in pool_parts(whole) for match in one.matches.values()
        if match.state not in DONE
    )
    if not pools_finished(whole):
        raise BracketError("pools_unfinished", open=left)
    whole = replace(whole, final_order=told_with_withdrawn(whole))
    final = final_of(whole, now)
    after = joined(whole, pool_parts(whole), final)
    changed = [match.key for match in after.ordered() if match.phase == FINAL]
    return Moved(after, changed, [])


def forfeited_out(whole: Bracket, match: Match) -> bool:
    """A set settled by a withdrawal carries no player's word."""
    return match.forfeit in FORFEITS and match.loser in whole.withdrawn


def unadvance(whole: Bracket) -> Moved:
    """Back to pools: the final goes while none of its sets has a result."""
    final = final_part(whole)
    if whole.plan is None or final is None:
        raise BracketError("not_advanced")
    played = [m.key for m in final.ordered() if m.state in PLAYED and not forfeited_out(whole, m)]
    if played:
        raise BracketError("final_played", count=len(played), set=played[0])
    after = joined(whole, pool_parts(whole), None)
    return Moved(after, [], [match.key for match in final.ordered()])


def pool_places(whole: Bracket) -> dict[int, tuple[int, int]]:
    """Each entrant's pool and place in it."""
    found: dict[int, tuple[int, int]] = {}
    for number, one in enumerate(pool_parts(whole), start=1):
        for row in standings.table(one):
            found[row.entrant] = (number, row.place or 0)
    return found


def placements(bracket: Bracket) -> dict[int, int]:
    """The final's places, then everyone else by pool place (a withdrawn one after), sharing."""
    if bracket.plan is None:
        return standings.placements(bracket)
    final = final_part(bracket)
    if final is None:
        return {}
    found = dict(standings.placements(final))
    where = pool_places(bracket)
    rest = [one for one in bracket.entrants if one not in final.entrants]

    def group(one: int) -> tuple[int, int]:
        return (int(one in bracket.withdrawn), where.get(one, (0, 0))[1])

    below = len(final.entrants)
    for one in sorted(rest, key=group):
        ahead = sum(1 for other in rest if group(other) < group(one))
        found[one] = below + 1 + ahead
    return found


def waiting_on(bracket: Bracket) -> dict[int, dict[str, Any]]:
    if bracket.plan is None:
        return standings.waiting_on(bracket)
    final = final_part(bracket)
    found: dict[int, dict[str, Any]] = {}
    for number, one in enumerate(pool_parts(bracket), start=1):
        for entrant, wait in standings.waiting_on(one).items():
            if wait["set"]:
                wait = {**wait, "set": prefixed(number, wait["set"])}
            if wait["what"] in (standings.DONE, standings.NEXT_ROUND) and final is None:
                wait = {**wait, "what": WAITS_FOR_FINAL if play.finished(one)
                        else standings.NEXT_ROUND}
            if final is not None and entrant not in bracket.withdrawn:
                wait = {"what": standings.DONE, "set": None, "opponent": None, "open": 0}
            found[entrant] = wait
    if final is not None:
        found.update(standings.waiting_on(final))
    return found
