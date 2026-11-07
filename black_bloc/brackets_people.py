"""Entrant moves: sign-up, check-in, adding by hand, removal, drop, DQ and putting back."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from . import brackets_store as store_
from . import sports_names
from .brackets import access, checkin, play, pools
from .brackets.model import (
    DQ,
    DROP,
)
from .brackets_moves import (
    NAME_LIMIT,
    OFF,
    actor_id,
    answered,
    bad_option,
    clean_text,
    done,
    engine,
    loaded,
    lock_for,
    mode_of,
    note,
    now_stamp,
    person,
    require_on,
    require_runner,
    require_signups,
    require_state,
    stop,
    touched,
    votes_synced,
)
from .logkinds import VIA_DISCORD, VIA_WEBSITE
from .panels import Outcome
from .settings_store import DEFAULT_TIMEZONE_KEY
from .sports.model import SOURCE_NAMES
from .timezones import DEFAULT_TZ, zone

log = logging.getLogger(__name__)

SHORT_LIMIT = 20
SEED_LIMIT = 1024
EXT_LIMIT = 100
EDIT_FIELDS = ("name", "short", "seed", "ext_source", "ext_id")


def clock_words(bot: Any, guild: Any, when: datetime, via: str) -> str:
    """A Discord timestamp in Discord; on the site, a plain time in the server's zone."""
    if via != VIA_WEBSITE:
        return f"<t:{int(when.timestamp())}:t>"
    name = bot.store.get(guild.id, DEFAULT_TIMEZONE_KEY) or DEFAULT_TZ
    local = when.astimezone(zone(name) or zone(DEFAULT_TZ) or UTC)
    hour = local.hour % 12 or 12
    return f"{hour}:{local.minute:02d} {'am' if local.hour < 12 else 'pm'} {local.tzname()}"


@answered
async def open_check_in(
    bot: Any, guild: Any, actor: Any, tournament_id: int, *, via: str = VIA_DISCORD
) -> Outcome:
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        require_signups(bot, guild, row)
        require_state(bot, guild, row, store_.SIGNUPS, store_.SEEDING)
        opened = datetime.now(UTC)
        closes = checkin.closes_at(opened, row["check_in_minutes"])
        await store_.update(
            bot.db,
            row["id"],
            {
                "state": store_.CHECK_IN,
                "check_in_opened_at": opened.isoformat(),
                "check_in_closes_at": closes.isoformat(),
            },
        )
        for one in await store_.entrants(bot.db, row["id"]):
            if one["user_id"] is None and not one["dropped"] and not one["checked_in"]:
                await store_.update_entrant(
                    bot.db, one["id"], {"checked_in": 1, "checked_in_at": opened.isoformat()}
                )
        await note(bot, guild, "check_in_opened", actor, row["id"], via, closes=closes.isoformat())
        return done(
            bot,
            guild,
            "check_in_opened",
            row["id"],
            name=row["name"],
            closes=clock_words(bot, guild, closes, via),
        )


async def finish_check_in(bot: Any, guild: Any, actor: Any, row: Any, via: str) -> Outcome:
    gone = checkin.no_shows(await store_.entrants(bot.db, row["id"]))
    stamp = now_stamp()
    for entrant_id in gone:
        await store_.update_entrant(
            bot.db,
            entrant_id,
            {"dropped": 1, "dropped_why": store_.NO_SHOW, "dropped_at": stamp},
        )
    await store_.update(bot.db, row["id"], {"state": store_.SEEDING})
    await note(bot, guild, "check_in_closed", actor, row["id"], via, removed=gone)
    return done(bot, guild, "check_in_closed", row["id"], name=row["name"], removed=len(gone))


@answered
async def close_check_in(
    bot: Any, guild: Any, actor: Any, tournament_id: int, *, via: str = VIA_DISCORD
) -> Outcome:
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        require_signups(bot, guild, row)
        require_state(bot, guild, row, store_.CHECK_IN)
        return await finish_check_in(bot, guild, actor, row, via)


async def close_due_check_ins(
    bot: Any, guild: Any, now: datetime | None = None, *, via: str = VIA_DISCORD
) -> list[int]:
    """The sweep layer 2 runs: every check-in whose window has passed closes by itself."""
    if mode_of(bot.store, guild.id) == OFF:
        return []
    moment = now or datetime.now(UTC)
    closed: list[int] = []
    for row in await store_.tournaments(bot.db, guild.id):
        if row["state"] != store_.CHECK_IN:
            continue
        async with lock_for(bot, row["id"]):
            fresh = await store_.tournament(bot.db, guild.id, row["id"])
            if fresh is None or fresh["state"] != store_.CHECK_IN:
                continue
            closes = play.parsed(fresh["check_in_closes_at"])
            if closes is None:
                log.warning(
                    "brackets: tournament %s check-in closing time %r could not be read; "
                    "closing it now",
                    fresh["id"],
                    fresh["check_in_closes_at"],
                )
            elif not checkin.due(closes, moment):
                continue
            await finish_check_in(bot, guild, None, fresh, via)
            closed.append(int(fresh["id"]))
    return closed


@answered
async def set_check_in(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    entrant_id: int,
    checked_in: bool = True,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        found = await person(bot, guild, row, entrant_id)
        if found["user_id"] != actor_id(actor) and not access.may_run(bot.store, guild, actor):
            raise stop(
                bot, guild, "brackets_not_yours_said", "not_yours", 403, entrant=found["name"]
            )
        require_signups(bot, guild, row)
        require_state(bot, guild, row, store_.CHECK_IN)
        if found["dropped"]:
            raise stop(
                bot,
                guild,
                "brackets_already_out_said",
                "already_out",
                409,
                entrant=found["name"],
                name=row["name"],
            )
        await store_.update_entrant(
            bot.db,
            found["id"],
            {"checked_in": int(checked_in), "checked_in_at": now_stamp() if checked_in else None},
        )
        event = "checked_in" if checked_in else "checked_out"
        await note(
            bot,
            guild,
            event,
            actor,
            row["id"],
            via,
            target=found["user_id"],
            entrant=found["id"],
        )
        return done(
            bot, guild, f"brackets_{event}_said", row["id"], entrant=found["name"], name=row["name"]
        )


@answered
async def join(
    bot: Any, guild: Any, actor: Any, tournament_id: int, *, via: str = VIA_DISCORD
) -> Outcome:
    """A member signs themselves up; someone who left may sign up again, a removal stands."""
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_signups(bot, guild, row)
        require_state(bot, guild, row, store_.SIGNUPS)
        user_id = actor_id(actor)
        name = clean_text(getattr(actor, "display_name", None) or user_id, NAME_LIMIT)
        found = await store_.entrant_of(bot.db, row["id"], user_id)
        if found is not None and not found["dropped"] and not found["dq"]:
            raise stop(
                bot,
                guild,
                "brackets_already_in_said",
                "already_in",
                409,
                entrant=found["name"],
                name=row["name"],
            )
        if found is not None and found["dropped_why"] == store_.REMOVED:
            raise stop(bot, guild, "brackets_removed_by_to_said", "removed", 403, name=row["name"])
        cap = row["entrant_cap"]
        if cap and await count_in(bot, row) >= cap:
            raise stop(bot, guild, "brackets_full_said", "full", 409, name=row["name"], cap=cap)
        if found is not None:
            await store_.update_entrant(bot.db, found["id"], back_in(name))
            entrant_id = found["id"]
        else:
            entrant_id = await store_.add_entrant(
                bot.db, row["id"], name, user_id=user_id, added_by=user_id
            )
        await note(
            bot,
            guild,
            "entrant_added",
            actor,
            row["id"],
            via,
            target=user_id,
            entrant=entrant_id,
            by_self=True,
        )
        return done(bot, guild, "brackets_joined_said", row["id"], name=row["name"])


def back_in(name: str | None = None) -> dict[str, Any]:
    found = {"dropped": 0, "dropped_why": None, "dropped_at": None, "dq": 0}
    return found | ({"name": name} if name else {})


async def count_in(bot: Any, row: Any) -> int:
    return sum(1 for one in await store_.entrants(bot.db, row["id"]) if not one["dropped"])


@answered
async def add_entrant(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    *,
    name: Any = None,
    user_id: int | None = None,
    ext_source: Any = None,
    ext_id: Any = None,
    short: Any = None,
    via: str = VIA_DISCORD,
) -> Outcome:
    """The TO adds a member, or a guest who is not on Discord (no user id; the TO reports)."""
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        require_state(bot, guild, row, *store_.BEFORE_START)
        member = guild.get_member(int(user_id)) if user_id is not None else None
        if store_.kind_of(row) in (store_.LIST, store_.SPORTS):
            user_id = None
        given = {"ext_source": ext_source, "ext_id": ext_id, "short": short}
        matched = await matched_ext(bot, guild, given)
        if matched is not None and not name:
            name = matched["name"]
        wanted = clean_text(name or getattr(member, "display_name", None), NAME_LIMIT + 1)
        if not wanted or len(wanted) > NAME_LIMIT:
            raise stop(bot, guild, "no_name", "no_name", 400, limit=NAME_LIMIT)
        found = (
            await store_.entrant_of(bot.db, row["id"], int(user_id))
            if user_id is not None
            else None
        )
        if found is not None and not found["dropped"]:
            raise stop(
                bot,
                guild,
                "brackets_already_in_said",
                "already_in",
                409,
                entrant=found["name"],
                name=row["name"],
            )
        guest_in = user_id is None and row["state"] == store_.CHECK_IN
        if found is not None:
            await store_.update_entrant(bot.db, found["id"], back_in(wanted))
            entrant_id = found["id"]
        else:
            entrant_id = await store_.add_entrant(
                bot.db,
                row["id"],
                wanted,
                user_id=int(user_id) if user_id is not None else None,
                added_by=actor_id(actor),
                checked_in=guest_in,
                **ext_values(bot, guild, given, matched),
            )
        await note(
            bot,
            guild,
            "entrant_added",
            actor,
            row["id"],
            via,
            target=user_id,
            entrant=entrant_id,
            guest=user_id is None,
            **({"ext": f"{matched['source']}:{matched['ext_id']}"} if matched else {}),
        )
        return done(bot, guild, "entrant_added", row["id"], entrant=wanted, name=row["name"])


async def matched_ext(bot: Any, guild: Any, given: dict[str, Any]) -> Any:
    """The names row an entrant's `ext_source` + `ext_id` point at; both blank is no match."""
    source = clean_text(given.get("ext_source"), EXT_LIMIT)
    ext_id = clean_text(given.get("ext_id"), EXT_LIMIT)
    if not source and not ext_id:
        return None
    if not source or not ext_id:
        raise bad_option(bot, guild, given)("ext_id" if source else "ext_source", "both or neither")
    found = await sports_names.known(bot.db, source, ext_id)
    if found is None:
        raise stop(
            bot,
            guild,
            "brackets_ext_unknown_said",
            "ext_unknown",
            400,
            source=SOURCE_NAMES.get(source, source),
            ext_id=ext_id,
        )
    return found


def short_of(bot: Any, guild: Any, given: dict[str, Any]) -> str | None:
    short = clean_text(given.get("short"), SHORT_LIMIT + 1)
    if len(short) > SHORT_LIMIT:
        raise bad_option(bot, guild, given)("short", f"1 to {SHORT_LIMIT} characters")
    return short or None


def ext_values(bot: Any, guild: Any, given: dict[str, Any], matched: Any) -> dict[str, Any]:
    short = short_of(bot, guild, given)
    if matched is None:
        return {"ext_source": None, "ext_id": None, "short": short}
    return {
        "ext_source": matched["source"],
        "ext_id": matched["ext_id"],
        "short": short or matched["short"],
    }


def seed_value(bot: Any, guild: Any, given: dict[str, Any]) -> int | None:
    value = given.get("seed")
    if value in (None, ""):
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= SEED_LIMIT:
        raise bad_option(bot, guild, given)("seed", f"a whole number from 1 to {SEED_LIMIT}")
    return value


async def edited_values(bot: Any, guild: Any, found: Any, given: dict[str, Any]) -> dict:
    """Only the fields named, each checked; a matched id with no short name takes the feed's."""
    values: dict[str, Any] = {}
    if "name" in given:
        name = clean_text(given.get("name"), NAME_LIMIT + 1)
        if not name or len(name) > NAME_LIMIT:
            raise stop(bot, guild, "no_name", "no_name", 400, limit=NAME_LIMIT)
        values["name"] = name
    if "seed" in given:
        values["seed"] = seed_value(bot, guild, given)
    if "short" in given:
        values["short"] = short_of(bot, guild, given)
    if "ext_source" in given or "ext_id" in given:
        matched = await matched_ext(bot, guild, given)
        values["ext_source"] = matched["source"] if matched is not None else None
        values["ext_id"] = matched["ext_id"] if matched is not None else None
        if matched is not None and "short" not in given and not found["short"]:
            values["short"] = matched["short"]
    return {key: value for key, value in values.items() if found[key] != value}


async def sets_holding(bot: Any, row: Any, entrant_id: int) -> tuple[str, ...]:
    current = await store_.bracket(bot.db, row)
    if current is None:
        return ()
    return tuple(
        key
        for key, match in current.matches.items()
        if int(entrant_id) in (match.slot_a, match.slot_b)
    )


@answered
async def edit_entrant(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    entrant_id: int,
    given: dict[str, Any],
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """Name, short name, seed and the feed's id, at any time (the owner's by-hand rule)."""
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        found = await person(bot, guild, row, entrant_id)
        wanted = {key: value for key, value in (given or {}).items() if key in EDIT_FIELDS}
        values = await edited_values(bot, guild, found, wanted)
        if values:
            await store_.update_entrant(bot.db, found["id"], values)
            await note(
                bot,
                guild,
                "entrant_edited",
                actor,
                row["id"],
                via,
                target=found["user_id"],
                entrant=found["id"],
                changed=sorted(values),
            )
        outcome = done(
            bot,
            guild,
            "brackets_entrant_edited_said",
            row["id"],
            entrant=values.get("name", found["name"]),
            name=row["name"],
        )
        if "name" in values or "short" in values:
            return replace(outcome, changed=await sets_holding(bot, row, found["id"]))
        return outcome


@answered
async def remove_entrant(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    entrant_id: int,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """Before the start only; once it runs, a DQ is the move."""
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        require_state(bot, guild, row, *store_.BEFORE_START)
        found = await person(bot, guild, row, entrant_id)
        if found["dropped"]:
            raise stop(
                bot,
                guild,
                "brackets_already_out_said",
                "already_out",
                409,
                entrant=found["name"],
                name=row["name"],
            )
        await store_.update_entrant(
            bot.db,
            found["id"],
            {"dropped": 1, "dropped_why": store_.REMOVED, "dropped_at": now_stamp()},
        )
        await note(
            bot,
            guild,
            "entrant_removed",
            actor,
            row["id"],
            via,
            target=found["user_id"],
            entrant=found["id"],
        )
        return done(
            bot, guild, "entrant_removed", row["id"], entrant=found["name"], name=row["name"]
        )


@answered
async def restore_entrant(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    entrant_id: int,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """Undoes a removal, a leave, a no-show, a drop or a DQ; forfeits played stand."""
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        require_state(bot, guild, row, *store_.BEFORE_START, *store_.PLAYING)
        found = await person(bot, guild, row, entrant_id)
        names = {"entrant": found["name"], "name": row["name"]}
        if not found["dropped"] and not found["dq"]:
            raise stop(bot, guild, "not_out", "not_out", 409, **names)
        moved = None
        if row["state"] in store_.PLAYING:
            current = await store_.bracket(bot.db, row)
            if current is None or found["id"] not in current.entrants:
                raise stop(
                    bot, guild, "brackets_not_in_bracket_said", "not_in_bracket", 409, **names
                )
            moved = engine(bot, guild, row, names, pools.reinstate, current, found["id"], None)
            await store_.save(bot.db, row["id"], moved.bracket, moved.changed, moved.removed)
            await votes_synced(bot, guild, row, via)
        await store_.update_entrant(bot.db, found["id"], back_in())
        await note(
            bot,
            guild,
            "entrant_restored",
            actor,
            row["id"],
            via,
            target=found["user_id"],
            entrant=found["id"],
        )
        outcome = done(bot, guild, "entrant_restored", row["id"], **names)
        return touched(outcome, moved) if moved is not None else outcome


async def withdrawn(
    bot: Any, guild: Any, actor: Any, row: Any, found: Any, why: str, via: str
) -> Outcome:
    names = {"entrant": found["name"], "name": row["name"]}
    if found["dq"] or found["dropped"]:
        raise stop(bot, guild, "brackets_already_out_said", "already_out", 409, **names)
    current = await store_.bracket(bot.db, row)
    if current is None:
        raise stop(bot, guild, "brackets_not_in_bracket_said", "not_in_bracket", 409, **names)
    moved = engine(bot, guild, row, names, pools.withdraw, current, found["id"], why, now_stamp())
    flags = {"dq": 1} if why == DQ else {"dropped": 1, "dropped_why": store_.DROPPED}
    await store_.update_entrant(bot.db, found["id"], flags | {"dropped_at": now_stamp()})
    gone = await store_.save(bot.db, row["id"], moved.bracket, moved.changed, moved.removed)
    await votes_synced(bot, guild, row, via)
    event = "dq" if why == DQ else "dropped"
    key = "dq" if why == DQ else "brackets_dropped_said"
    await note(
        bot,
        guild,
        event,
        actor,
        row["id"],
        via,
        target=found["user_id"],
        entrant=found["id"],
        forfeited=moved.changed,
    )
    return touched(done(bot, guild, key, row["id"], **names), moved, gone)


@answered
async def dq(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    entrant_id: int,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        require_state(bot, guild, row, *store_.PLAYING)
        found = await person(bot, guild, row, entrant_id)
        return await withdrawn(bot, guild, actor, row, found, DQ, via)


@answered
async def drop(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    entrant_id: int,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """The entrant's own move (or the TO's): before the start they leave, after it they forfeit."""
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        found = await person(bot, guild, row, entrant_id)
        if found["user_id"] != actor_id(actor) and not access.may_run(bot.store, guild, actor):
            raise stop(
                bot, guild, "brackets_not_yours_said", "not_yours", 403, entrant=found["name"]
            )
        require_state(bot, guild, row, *store_.BEFORE_START, *store_.PLAYING)
        if row["state"] in store_.PLAYING:
            return await withdrawn(bot, guild, actor, row, found, DROP, via)
        if found["dropped"]:
            raise stop(
                bot,
                guild,
                "brackets_already_out_said",
                "already_out",
                409,
                entrant=found["name"],
                name=row["name"],
            )
        await store_.update_entrant(
            bot.db,
            found["id"],
            {"dropped": 1, "dropped_why": store_.LEFT, "dropped_at": now_stamp()},
        )
        await note(
            bot,
            guild,
            "dropped",
            actor,
            row["id"],
            via,
            target=found["user_id"],
            entrant=found["id"],
            before_start=True,
        )
        if found["user_id"] == actor_id(actor):
            return done(bot, guild, "brackets_left_said", row["id"], name=row["name"])
        return done(
            bot, guild, "entrant_removed", row["id"], entrant=found["name"], name=row["name"]
        )
