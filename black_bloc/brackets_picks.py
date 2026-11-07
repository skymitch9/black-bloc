"""Pick sheets: a member's sheet, the quick pick, staff's Edit sheet, the lock, the one rescore."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any

from . import brackets_store as store_
from .brackets import picks, play
from .brackets.model import COMPLETE
from .brackets.sports_shape import is_pending
from .brackets_moves import (
    OFF,
    actor_id,
    answered,
    bad_option,
    done,
    edit,
    league_of,
    loaded,
    lock_for,
    mode_of,
    note,
    now_stamp,
    require_on,
    require_runner,
    require_state,
    stop,
    when,
)
from .logkinds import VIA_DISCORD
from .panels import Outcome
from .settings_store import (
    BRACKETS_LEADERBOARD_ROWS,
    BRACKETS_PICK_POINTS,
    BRACKETS_PICK_TIEBREAK,
)
from .sports import nfl
from .sports.model import FINAL, LIVE, NFL

log = logging.getLogger(__name__)

OPEN_STATES = (store_.DRAFT, store_.SEEDING, store_.RUNNING)
SHOWN_STATES = (*OPEN_STATES, store_.COMPLETE)
STARTED = (LIVE, FINAL)
PICK_FIELDS = ("picks_lock_at", "picks_points", "picks_on")
TIEBREAK_MOST = 9999
REASON_LIMIT = 300


@dataclass
class Sheets:
    """One tournament's picks as every door reads them."""

    row: Any
    tree: picks.Tree
    bracket: Any
    meta: dict[str, Any]
    locked: bool
    table: tuple[int, ...]
    sheets: dict[int, Any] = field(default_factory=dict)
    picks: dict[int, dict[str, int]] = field(default_factory=dict)

    def mine(self, user_id: int | None) -> dict[str, int]:
        return picks.cleaned(self.tree, self.picks.get(int(user_id or 0), {}))

    def count(self) -> int:
        return sum(1 for user in self.sheets if self.mine(user))


def table_of(store: Any, row: Any) -> tuple[int, ...]:
    found = picks.points_table(store_.column(row, "picks_points"))
    if found is None:
        found = picks.points_table(store.get(row["guild_id"], BRACKETS_PICK_POINTS))
    return found or picks.DEFAULT_POINTS


def tiebreak_on(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, BRACKETS_PICK_TIEBREAK))


def reseeds_of(row: Any, meta: dict[str, Any]) -> dict | None:
    """The NFL reseed by this bracket's own set keys, when every game it names was imported."""
    if league_of(row) != NFL:
        return None
    keyed = {value["source_key"]: key for key, value in meta.items() if value["source_key"]}
    rules = nfl.reseed_rules()
    named = {one for slots in rules.values() for keys, _ in slots.values() for one in keys}
    if not (set(rules) | named) <= set(keyed):
        return None
    return {
        keyed[source]: {
            slot: (tuple(keyed[one] for one in keys), rank) for slot, (keys, rank) in slots.items()
        }
        for source, slots in rules.items()
    }


def started(bracket: Any, meta: dict[str, Any]) -> bool:
    """A game past any play-in has a result or is being played."""
    if bracket is None:
        return False
    for match in bracket.matches.values():
        if is_pending(match) or match.round < 1:
            continue
        if match.state == COMPLETE or (meta.get(match.key) or {}).get("live_status") in STARTED:
            return True
    return False


def due(row: Any, bracket: Any, meta: dict[str, Any], now: datetime | None = None) -> bool:
    found = play.parsed(store_.column(row, "picks_lock_at"))
    moment = now or datetime.now(UTC)
    return (found is not None and found <= moment) or started(bracket, meta)


def is_locked(row: Any, bracket: Any, meta: dict[str, Any], now: datetime | None = None) -> bool:
    if row["state"] not in OPEN_STATES:
        return True
    return bool(store_.column(row, "picks_locked_at")) or due(row, bracket, meta, now)


async def read(bot: Any, row: Any, now: datetime | None = None) -> Sheets:
    bracket = await store_.bracket(bot.db, row)
    meta = await store_.sports_rows(bot.db, row["id"]) if bracket is not None else {}
    people = await store_.entrants(bot.db, row["id"])
    seeds = {one["id"]: int(one["seed"]) for one in people if one["seed"] is not None}
    tree = picks.tree_of(bracket, seeds, reseeds_of(row, meta))
    return Sheets(
        row=row,
        tree=tree,
        bracket=bracket,
        meta=meta,
        locked=is_locked(row, bracket, meta, now),
        table=table_of(bot.store, row),
        sheets=await store_.sheets(bot.db, row["id"]),
        picks=await store_.all_picks(bot.db, row["id"]),
    )


async def rescore(bot: Any, row: Any) -> None:
    """The one writer of every sheet's points, correct, possible and rank; a complete
    tournament's ranks stay as they were."""
    if not store_.picks_on(row) or row["state"] not in OPEN_STATES:
        return
    found = await read(bot, row)
    if not found.sheets:
        return
    scores = {
        user: picks.score(found.tree, found.picks.get(user, {}), found.bracket, found.table)
        for user in found.sheets
    }
    guesses = (
        {user: one["tiebreak"] for user, one in found.sheets.items()}
        if tiebreak_on(bot.store, row["guild_id"])
        else {}
    )
    ranks = picks.ranked(scores, guesses, picks.final_total(found.bracket))
    await store_.write_scores(
        bot.db,
        row["id"],
        {
            user: (one.points, one.correct, one.possible, ranks[user])
            for user, one in scores.items()
        },
    )


def require_picks(bot: Any, guild: Any, row: Any) -> None:
    if not store_.picks_on(row):
        raise stop(bot, guild, "brackets_picks_off_said", "picks_off", 409, name=row["name"])


def require_open(bot: Any, guild: Any, found: Sheets) -> None:
    require_picks(bot, guild, found.row)
    if not found.tree.nodes:
        raise stop(bot, guild, "brackets_picks_off_said", "picks_off", 409, name=found.row["name"])
    if found.locked:
        raise stop(
            bot, guild, "brackets_pick_too_late", "picks_locked", 409, name=found.row["name"]
        )


def entrant_of(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def given_sheet(bot: Any, guild: Any, given: dict[str, Any]) -> tuple[dict[str, int], Any]:
    """`{picks: {set key: entrant id}, tiebreak}` checked for shape; a bad one refuses in words."""
    bad = bad_option(bot, guild, given)
    wanted = given.get("picks") or {}
    if not isinstance(wanted, dict):
        raise bad("picks", "each game's key with the id of the entrant picked to win it")
    found: dict[str, int] = {}
    for key, value in wanted.items():
        entrant = entrant_of(value)
        if entrant is None:
            raise bad("picks", "each game's key with the id of the entrant picked to win it")
        found[str(key)[:40]] = entrant
    guess = given.get("tiebreak")
    if guess in (None, ""):
        return found, None
    number = entrant_of(guess)
    if number is None or not 0 <= number <= TIEBREAK_MOST:
        raise bad("tiebreak", f"a whole number from 0 to {TIEBREAK_MOST}")
    return found, number


def consistent(bot: Any, guild: Any, found: Sheets, sheet: dict[str, int]) -> None:
    wrong = picks.wrong(found.tree, sheet)
    if wrong:
        raise stop(
            bot, guild, "brackets_pick_inconsistent_said", "pick_inconsistent", 409, set=wrong[0]
        )


@answered
async def save_sheet(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    given: dict[str, Any],
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """A member's whole sheet, until the lock; their own presses are not logged."""
    require_on(bot, guild)
    user = actor_id(actor)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        found = await read(bot, row)
        require_open(bot, guild, found)
        sheet, guess = given_sheet(bot, guild, given or {})
        consistent(bot, guild, found, sheet)
        if not tiebreak_on(bot.store, guild.id):
            held = found.sheets.get(int(user or 0))
            guess = held["tiebreak"] if held is not None else None
        fresh = await store_.write_sheet(bot.db, row["id"], int(user or 0), sheet, guess)
        await rescore(bot, row)
        outcome = done(bot, guild, "brackets_sheet_saved_said", row["id"])
        return replace(outcome, changed=("sheet_added",) if fresh else ())


@answered
async def quick_pick(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    key: str,
    entrant: Any,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """One pick from the Discord panel, saved at once; later picks it no longer allows go."""
    require_on(bot, guild)
    user = int(actor_id(actor) or 0)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        found = await read(bot, row)
        require_open(bot, guild, found)
        wanted = entrant_of(entrant)
        sheet = {**found.mine(user), str(key): wanted}
        kept = picks.cleaned(found.tree, sheet)
        if wanted is None or kept.get(str(key)) != wanted:
            raise stop(
                bot,
                guild,
                "brackets_pick_inconsistent_said",
                "pick_inconsistent",
                409,
                set=str(key)[:20],
            )
        held = found.sheets.get(user)
        guess = held["tiebreak"] if held is not None else None
        fresh = await store_.write_sheet(bot.db, row["id"], user, kept, guess)
        await rescore(bot, row)
        people = {one["id"]: one for one in await store_.entrants(bot.db, row["id"])}
        name = people[wanted]["name"] if wanted in people else str(wanted)
        outcome = done(bot, guild, "brackets_pick_saved", row["id"], name=name, set=str(key))
        return replace(outcome, changed=("sheet_added",) if fresh else ())


@answered
async def edit_sheet(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    user_id: int,
    given: dict[str, Any],
    *,
    member: str | None = None,
    via: str = VIA_DISCORD,
) -> Outcome:
    """Staff change a member's sheet at any time before the tournament is complete, with a
    reason; the sheet then says it was edited by staff."""
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        require_picks(bot, guild, row)
        require_state(bot, guild, row, *OPEN_STATES)
        reason = " ".join(str((given or {}).get("reason") or "").split())[:REASON_LIMIT]
        if not reason:
            raise stop(
                bot, guild, "reason_needed", "reason_needed", 400, member=member or f"<@{user_id}>"
            )
        found = await read(bot, row)
        sheet, guess = given_sheet(bot, guild, given or {})
        consistent(bot, guild, found, sheet)
        held = found.sheets.get(int(user_id))
        if "tiebreak" not in (given or {}) and held is not None:
            guess = held["tiebreak"]
        stamp = now_stamp() if found.locked else None
        fresh = await store_.write_sheet(
            bot.db,
            row["id"],
            int(user_id),
            sheet,
            guess,
            locked_at=stamp,
            edited_by=actor_id(actor),
        )
        await rescore(bot, row)
        await note(
            bot,
            guild,
            "sheet_edited",
            actor,
            row["id"],
            via,
            target=int(user_id),
            member=str(user_id),
            picks=len(sheet),
            reason=reason,
        )
        outcome = done(bot, guild, "sheet_edited", row["id"], member=member or f"<@{user_id}>")
        return replace(outcome, changed=("sheet_added",) if fresh else ())


def lock_given(bot: Any, guild: Any, given: dict[str, Any]) -> str | None:
    bad = bad_option(bot, guild, given)
    return when(
        bot, guild, given.get("picks_lock_at"), lambda _, allowed: bad("picks_lock_at", allowed)
    )


def points_given(bot: Any, guild: Any, given: dict[str, Any]) -> str:
    found = picks.points_table(given.get("picks_points"))
    if found is None:
        raise bad_option(bot, guild, given)(
            "picks_points", "whole numbers from 0 to 1000 separated by commas, like 1,2,4,8"
        )
    return ",".join(str(one) for one in found)


async def configured(
    bot: Any, guild: Any, actor: Any, tournament_id: int, given: dict[str, Any], via: str
) -> Outcome:
    """The organiser's picks settings: the lock time, the points, picks on or off before the
    lock. A lock moved into the future opens locked sheets again."""
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        if not store_.is_sports(row):
            raise stop(bot, guild, "not_sports", "not_sports", 409, name=row["name"])
        require_state(bot, guild, row, *OPEN_STATES)
        found = await read(bot, row)
        values: dict[str, Any] = {}
        if "picks_on" in given:
            if not isinstance(given["picks_on"], bool):
                raise bad_option(bot, guild, given)("picks_on", "true or false")
            if found.locked and bool(given["picks_on"]) != store_.picks_on(row):
                raise stop(bot, guild, "picks_on_locked", "picks_locked", 409, name=row["name"])
            values["picks_on"] = int(given["picks_on"])
        if "picks_points" in given:
            values["picks_points"] = points_given(bot, guild, given)
        if "picks_lock_at" in given:
            values["picks_lock_at"] = lock_given(bot, guild, given)
            moved = dict(row) | values
            if store_.column(row, "picks_locked_at") and not due(moved, found.bracket, found.meta):
                values["picks_locked_at"] = None
                await store_.lock_sheets(bot.db, row["id"], None)
        await store_.update(bot.db, row["id"], values)
        await note(bot, guild, "edited", actor, row["id"], via, changed=sorted(values))
        fresh = await store_.tournament(bot.db, guild.id, row["id"])
        await rescore(bot, fresh)
        return done(bot, guild, "edited", row["id"], name=row["name"])


@answered
async def edit_with_picks(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    given: dict[str, Any],
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """The bracket's edit; the picks fields also reach a running bracket, until it is complete."""
    given = dict(given or {})
    wanted = {name: given.pop(name) for name in PICK_FIELDS if name in given}
    if not wanted:
        return await edit(bot, guild, actor, tournament_id, given, via=via)
    require_on(bot, guild)
    if given:
        outcome = await edit(bot, guild, actor, tournament_id, given, via=via)
        if not outcome.ok:
            return outcome
    return await configured(bot, guild, actor, tournament_id, wanted, via)


def first_game(bracket: Any, meta: dict[str, Any]) -> str | None:
    """The earliest start of a game past any play-in, else of any game, else none."""
    if bracket is None:
        return None
    timed = [
        (match.round >= 1, play.parsed((meta.get(match.key) or {}).get("scheduled_at")))
        for match in bracket.matches.values()
        if not is_pending(match)
    ]
    for wanted in (True, False):
        found = [moment for main, moment in timed if moment is not None and (main or not wanted)]
        if found:
            return min(found).astimezone(UTC).isoformat()
    return None


async def lock_from_games(bot: Any, row: Any) -> None:
    """At Import and Build the lock is the first game's start, and nothing is locked yet."""
    bracket = await store_.bracket(bot.db, row)
    meta = await store_.sports_rows(bot.db, row["id"]) if bracket is not None else {}
    values = {"picks_lock_at": first_game(bracket, meta), "picks_locked_at": None}
    await store_.update(bot.db, row["id"], values)
    await store_.lock_sheets(bot.db, row["id"], None)


async def lock_due(
    bot: Any, guild: Any, now: datetime | None = None, *, via: str = VIA_DISCORD
) -> list[int]:
    """The minute's sweep: a sports bracket whose lock time passed, or whose first game has
    begun, locks every sheet once; answers the tournaments whose starter card owes a redraw."""
    if mode_of(bot.store, guild.id) == OFF:
        return []
    moment = now or datetime.now(UTC)
    locked: list[int] = []
    for row in await store_.tournaments(bot.db, guild.id):
        if not store_.picks_on(row) or row["state"] not in OPEN_STATES:
            continue
        if store_.column(row, "picks_locked_at"):
            continue
        async with lock_for(bot, row["id"]):
            fresh = await store_.tournament(bot.db, guild.id, row["id"])
            if fresh is None or store_.column(fresh, "picks_locked_at"):
                continue
            bracket = await store_.bracket(bot.db, fresh)
            meta = await store_.sports_rows(bot.db, fresh["id"]) if bracket is not None else {}
            if bracket is None or not due(fresh, bracket, meta, moment):
                continue
            stamp = moment.astimezone(UTC).isoformat()
            await store_.update(bot.db, fresh["id"], {"picks_locked_at": stamp})
            count = await store_.lock_sheets(bot.db, fresh["id"], stamp)
            await note(bot, guild, "picks_locked", None, fresh["id"], via, sheets=count)
            locked.append(int(fresh["id"]))
    return locked


@dataclass(frozen=True)
class Board:
    """What the starter card and the My picks panel show of a bracket's sheets."""

    locked: bool
    lock_at: str | None
    count: int
    games: int
    rows: tuple[tuple[int, int, int], ...] = ()


async def board(bot: Any, row: Any) -> Board | None:
    if not store_.picks_on(row) or row["state"] not in SHOWN_STATES:
        return None
    found = await read(bot, row)
    if not found.tree.nodes:
        return None
    shown = int(bot.store.get(row["guild_id"], BRACKETS_LEADERBOARD_ROWS) or 0)
    ranked = sorted(
        (
            (int(one["rank"] or 0), user, int(one["points"] or 0))
            for user, one in found.sheets.items()
            if found.mine(user)
        ),
        key=lambda one: (one[0] or 10**6, -one[2], one[1]),
    )
    return Board(
        locked=found.locked,
        lock_at=store_.column(row, "picks_lock_at"),
        count=found.count(),
        games=sum(1 for one in found.tree.nodes.values() if one.fixed is None),
        rows=tuple(ranked[:shown]) if found.locked else (),
    )


def sheet_fields(found: Sheets, user_id: int, *, mine: bool) -> dict[str, Any]:
    """One sheet as the page draws it: the picks, the tree they fill, the score and its marks."""
    held = found.sheets.get(int(user_id))
    sheet = found.mine(user_id)
    scored = picks.score(found.tree, sheet, found.bracket, found.table)
    row = found.row
    return {
        "user_id": str(user_id),
        "on": store_.picks_on(row),
        "locked": found.locked,
        "lock_at": store_.column(row, "picks_lock_at"),
        "locked_at": store_.column(row, "picks_locked_at"),
        "may_edit": mine and not found.locked and bool(found.tree.nodes),
        "points_table": list(found.table),
        "round_points": {
            str(node.round): picks.round_points(found.table, node.round)
            for node in found.tree.nodes.values()
        },
        "tree": found.tree.wire(),
        "picks": sheet,
        "tiebreak": held["tiebreak"] if held is not None else None,
        "marks": scored.marks if found.locked or found.row["state"] == store_.COMPLETE else {},
        "points": int(held["points"]) if held is not None else 0,
        "correct": int(held["correct"]) if held is not None else 0,
        "played": scored.played,
        "possible": int(held["possible"]) if held is not None else scored.possible,
        "rank": held["rank"] if held is not None and sheet else None,
        "sheets": found.count(),
        "edited": bool(held is not None and held["edited_by"] is not None),
        "edited_at": held["edited_at"] if held is not None else None,
    }


def leaderboard_rows(found: Sheets, viewer: int | None, runs: bool) -> list[dict[str, Any]]:
    rows = []
    for user, held in found.sheets.items():
        sheet = found.mine(user)
        if not sheet:
            continue
        scored = picks.score(found.tree, sheet, found.bracket, found.table)
        rows.append(
            {
                "user_id": str(user),
                "rank": held["rank"],
                "points": int(held["points"] or 0),
                "correct": int(held["correct"] or 0),
                "played": scored.played,
                "possible": int(held["possible"] or 0),
                "picks": len(sheet),
                "edited": held["edited_by"] is not None,
                "mine": viewer is not None and user == int(viewer),
                "may_open": found.locked or runs or (viewer is not None and user == int(viewer)),
            }
        )
    return sorted(rows, key=lambda one: (one["rank"] or 10**6, -one["points"], one["user_id"]))


__all__ = [
    "Board",
    "PICK_FIELDS",
    "Sheets",
    "board",
    "due",
    "edit_sheet",
    "edit_with_picks",
    "first_game",
    "is_locked",
    "leaderboard_rows",
    "lock_due",
    "lock_from_games",
    "quick_pick",
    "read",
    "rescore",
    "save_sheet",
    "sheet_fields",
]
