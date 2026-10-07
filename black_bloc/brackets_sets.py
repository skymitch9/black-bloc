"""Set moves: call, report, confirm, dispute, the TO's override and reset, the confirm sweep."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from . import brackets_store as store_
from .brackets import access, play
from .brackets.model import (
    COMPLETE,
    REPORTED,
)
from .brackets_moves import (
    NOTE_LIMIT,
    OFF,
    actor_id,
    answered,
    clean_text,
    done,
    engine,
    loaded,
    lock_for,
    mode_of,
    note,
    now_stamp,
    require_on,
    require_runner,
    require_state,
    said,
    stop,
)
from .logkinds import VIA_DISCORD
from .panels import Outcome


async def running(bot: Any, guild: Any, tournament_id: int) -> tuple[Any, Any, dict, dict]:
    row = await loaded(bot, guild, tournament_id)
    require_state(bot, guild, row, store_.RUNNING)
    current = await store_.bracket(bot.db, row)
    people = {one["id"]: one for one in await store_.entrants(bot.db, row["id"])}
    return row, current, people, {"name": row["name"]}


def the_set(bot: Any, guild: Any, row: Any, current: Any, key: str) -> Any:
    found = current.matches.get(str(key)) if current is not None else None
    if found is None:
        raise stop(
            bot, guild, "brackets_no_set_said", "no_set", 404, set=str(key)[:20], name=row["name"]
        )
    return found


def player_side(people: dict, match: Any, actor: Any) -> str | None:
    me = actor_id(actor)
    for side in ("a", "b"):
        entrant = match.slot(side)
        if entrant is not None and people.get(entrant) is not None:
            if people[entrant]["user_id"] is not None and people[entrant]["user_id"] == me:
                return side
    return None


def entrant_name(people: dict, entrant: int | None) -> str:
    found = people.get(entrant) if entrant is not None else None
    return found["name"] if found is not None else "—"


def final_words(bot: Any, guild: Any, people: dict, match: Any) -> str:
    result = (
        said(bot.store, guild.id, "brackets_forfeit_words")
        if match.score_a is None or match.forfeit
        else f"{max(match.score_a, match.score_b)}–{min(match.score_a, match.score_b)}"
    )
    return said(
        bot.store,
        guild.id,
        "brackets_set_final_said",
        set=match.key,
        winner=entrant_name(people, match.winner),
        result=result,
    )


async def kept(bot: Any, row: Any, moved: Any) -> Any:
    await store_.save(bot.db, row["id"], moved.bracket, moved.changed, moved.removed)
    return moved.bracket.matches


def score_of(value: Any) -> Any:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


@answered
async def call(
    bot: Any, guild: Any, actor: Any, tournament_id: int, key: str, *, via: str = VIA_DISCORD
) -> Outcome:
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row, current, people, names = await running(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        match = the_set(bot, guild, row, current, key)
        moved = engine(
            bot, guild, row, names, play.call, current, match.key, actor_id(actor), now_stamp()
        )
        after = (await kept(bot, row, moved))[match.key]
        await note(bot, guild, "set_called", actor, row["id"], via, set=match.key)
        return done(
            bot,
            guild,
            "brackets_set_called_said",
            row["id"],
            set=match.key,
            a=entrant_name(people, after.slot_a),
            b=entrant_name(people, after.slot_b),
        )


@answered
async def report(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    key: str,
    score_a: Any,
    score_b: Any,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """A player's report waits for the opponent; a TO's report is final at once."""
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row, current, people, names = await running(bot, guild, tournament_id)
        match = the_set(bot, guild, row, current, key)
        side = player_side(people, match, actor)
        stamp = now_stamp()
        if side is None:
            if not access.may_run(bot.store, guild, actor):
                raise stop(bot, guild, "brackets_not_in_set_said", "not_in_set", 403, set=match.key)
            return await overridden(
                bot,
                guild,
                actor,
                row,
                current,
                people,
                match,
                via,
                score_a=score_of(score_a),
                score_b=score_of(score_b),
            )
        moved = engine(
            bot,
            guild,
            row,
            names,
            play.report,
            current,
            match.key,
            side,
            score_of(score_a),
            score_of(score_b),
            actor_id(actor),
            stamp,
        )
        after = (await kept(bot, row, moved))[match.key]
        if after.state == COMPLETE:
            await note(
                bot,
                guild,
                "set_confirmed",
                actor,
                row["id"],
                via,
                set=match.key,
                how=after.confirmed_how,
                winner=after.winner,
            )
            return Outcome(True, final_words(bot, guild, people, after), value=row["id"])
        await note(
            bot,
            guild,
            "set_reported",
            actor,
            row["id"],
            via,
            set=match.key,
            score_a=after.score_a,
            score_b=after.score_b,
        )
        return done(
            bot,
            guild,
            "brackets_set_reported_said",
            row["id"],
            set=match.key,
            score_a=after.score_a,
            score_b=after.score_b,
            minutes=row["confirm_minutes"],
            opponent=entrant_name(people, after.slot("b" if side == "a" else "a")),
        )


async def overridden(
    bot: Any,
    guild: Any,
    actor: Any,
    row: Any,
    current: Any,
    people: dict,
    match: Any,
    via: str,
    **result: Any,
) -> Outcome:
    moved = engine(
        bot,
        guild,
        row,
        {"name": row["name"]},
        play.override,
        current,
        match.key,
        actor_id(actor),
        now_stamp(),
        **result,
    )
    after = (await kept(bot, row, moved))[match.key]
    await note(
        bot,
        guild,
        "set_overridden",
        actor,
        row["id"],
        via,
        set=match.key,
        score_a=after.score_a,
        score_b=after.score_b,
        winner=after.winner,
        forfeit=after.forfeit,
        cleared=[one for one in moved.changed if one != match.key],
    )
    return Outcome(True, final_words(bot, guild, people, after), value=row["id"])


@answered
async def confirm_report(
    bot: Any, guild: Any, actor: Any, tournament_id: int, key: str, *, via: str = VIA_DISCORD
) -> Outcome:
    """The opponent confirms; a TO who is not playing lets the reported score stand."""
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row, current, people, names = await running(bot, guild, tournament_id)
        match = the_set(bot, guild, row, current, key)
        side = player_side(people, match, actor)
        stamp = now_stamp()
        if side is None:
            if not access.may_run(bot.store, guild, actor):
                raise stop(bot, guild, "brackets_not_in_set_said", "not_in_set", 403, set=match.key)
            moved = engine(
                bot, guild, row, names, play.accept, current, match.key, actor_id(actor), stamp
            )
        else:
            moved = engine(
                bot,
                guild,
                row,
                names,
                play.confirm_report,
                current,
                match.key,
                side,
                actor_id(actor),
                stamp,
            )
        after = (await kept(bot, row, moved))[match.key]
        await note(
            bot,
            guild,
            "set_confirmed",
            actor,
            row["id"],
            via,
            set=match.key,
            how=after.confirmed_how,
            winner=after.winner,
        )
        return Outcome(True, final_words(bot, guild, people, after), value=row["id"])


@answered
async def dispute(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    key: str,
    note_text: Any = None,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row, current, people, names = await running(bot, guild, tournament_id)
        match = the_set(bot, guild, row, current, key)
        side = player_side(people, match, actor)
        if side is None:
            raise stop(bot, guild, "brackets_not_in_set_said", "not_in_set", 403, set=match.key)
        words = clean_text(note_text, NOTE_LIMIT) or None
        moved = engine(
            bot,
            guild,
            row,
            names,
            play.dispute,
            current,
            match.key,
            side,
            actor_id(actor),
            words,
            now_stamp(),
        )
        await kept(bot, row, moved)
        await note(bot, guild, "set_disputed", actor, row["id"], via, set=match.key)
        return done(bot, guild, "brackets_set_disputed_said", row["id"], set=match.key)


@answered
async def override(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    key: str,
    *,
    score_a: Any = None,
    score_b: Any = None,
    winner: Any = None,
    forfeit: bool = False,
    via: str = VIA_DISCORD,
) -> Outcome:
    """The TO decides a set from any state, or corrects a final one; what it fed is replayed."""
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row, current, people, _ = await running(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        match = the_set(bot, guild, row, current, key)
        side = winner if winner in ("a", "b") else match.side_of(score_of(winner))
        return await overridden(
            bot,
            guild,
            actor,
            row,
            current,
            people,
            match,
            via,
            score_a=score_of(score_a),
            score_b=score_of(score_b),
            winner=side,
            forfeit=bool(forfeit),
        )


@answered
async def reset(
    bot: Any, guild: Any, actor: Any, tournament_id: int, key: str, *, via: str = VIA_DISCORD
) -> Outcome:
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row, current, people, names = await running(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        match = the_set(bot, guild, row, current, key)
        moved = engine(
            bot, guild, row, names, play.reset, current, match.key, actor_id(actor), now_stamp()
        )
        await kept(bot, row, moved)
        await note(
            bot,
            guild,
            "set_reset",
            actor,
            row["id"],
            via,
            set=match.key,
            cleared=[one for one in moved.changed if one != match.key],
            removed=moved.removed,
        )
        return done(bot, guild, "brackets_set_reset_said", row["id"], set=match.key)


async def confirm_due(
    bot: Any, guild: Any, now: datetime | None = None, *, via: str = VIA_DISCORD
) -> list[tuple[int, str]]:
    """The sweep layer 2 runs: a report nobody answered within the confirm time stands."""
    if mode_of(bot.store, guild.id) == OFF:
        return []
    moment = now or datetime.now(UTC)
    confirmed: list[tuple[int, str]] = []
    for row in await store_.tournaments(bot.db, guild.id):
        if row["state"] != store_.RUNNING:
            continue
        async with lock_for(bot, row["id"]):
            fresh = await store_.tournament(bot.db, guild.id, row["id"])
            current = await store_.bracket(bot.db, fresh) if fresh else None
            if current is None or fresh["state"] != store_.RUNNING:
                continue
            waiting = [one.key for one in current.matches.values() if one.state == REPORTED]
            if not waiting:
                continue
            moved = play.confirm_due(current, moment, int(fresh["confirm_minutes"]))
            if not moved.changed:
                continue
            after = await kept(bot, fresh, moved)
            for key in waiting:
                if after[key].state == COMPLETE:
                    confirmed.append((int(fresh["id"]), key))
                    await note(
                        bot,
                        guild,
                        "set_confirmed",
                        None,
                        fresh["id"],
                        via,
                        set=key,
                        how=after[key].confirmed_how,
                        winner=after[key].winner,
                    )
    return confirmed
