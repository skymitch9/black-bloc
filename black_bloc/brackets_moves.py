"""Every tournament move both doors make: one lock per tournament, the engine, the row, the log."""

from __future__ import annotations

import asyncio
import functools
import logging
from datetime import UTC, datetime
from typing import Any

from . import brackets_store as store_
from .actionlog import log_action
from .brackets import access, bestof, checkin, play, seeding, standings
from .brackets.model import (
    BYE,
    COMPLETE,
    DONE,
    DQ,
    DROP,
    FORMATS,
    REPORTED,
    VOID,
    BracketError,
)
from .logkinds import VIA_DISCORD, kind_via
from .panels import Outcome
from .settings_store import (
    BRACKETS_BEST_OF,
    BRACKETS_BEST_OF_FINALS,
    BRACKETS_BEST_OF_FROM_ROUND,
    BRACKETS_BEST_OF_LATE,
    BRACKETS_CHECK_IN_MINUTES,
    BRACKETS_CONFIRM_MINUTES,
    BRACKETS_DEFAULTS,
    BRACKETS_ENTRANT_CAP,
    BRACKETS_FORMAT_DEFAULT,
    BRACKETS_GRAND_FINAL_RESET,
    BRACKETS_MODE,
    BRACKETS_MODES,
    BRACKETS_NUMBERS,
    BRACKETS_SWISS_ROUNDS,
    BRACKETS_THIRD_PLACE,
    BRACKETS_TO_ROLE,
)

log = logging.getLogger(__name__)

HEAD = "brackets"
OFF = "off"
NAME_LIMIT = 100
GAME_LIMIT = 100
NOTE_LIMIT = 300
RULES_LIMIT = 4000
LOCKS_ATTR = "_brackets_locks"
ENGINE_STATUS = {"bad_score": 400, "bad_order": 400, "forfeit_needs_winner": 400, "no_set": 404}
ENGINE_WORDS = {
    code: f"brackets_{code}_said"
    for code in (
        "too_few",
        "bad_order",
        "no_set",
        "not_ready",
        "not_playable",
        "already_complete",
        "disputed",
        "already_called",
        "already_reported",
        "bad_score",
        "reported_differently",
        "not_reported",
        "own_report",
        "not_resettable",
        "nothing_to_reset",
        "forfeit_needs_winner",
        "not_in_set",
        "not_in_bracket",
        "already_out",
        "not_out",
    )
}
WRONG_STATE = "brackets_wrong_state_said"
NUMBER_RANGES = {
    "swiss_rounds": BRACKETS_NUMBERS[BRACKETS_SWISS_ROUNDS][1:],
    "best_of_from_round": BRACKETS_NUMBERS[BRACKETS_BEST_OF_FROM_ROUND][1:],
    "entrant_cap": BRACKETS_NUMBERS[BRACKETS_ENTRANT_CAP][1:],
    "check_in_minutes": BRACKETS_NUMBERS[BRACKETS_CHECK_IN_MINUTES][1:],
    "confirm_minutes": BRACKETS_NUMBERS[BRACKETS_CONFIRM_MINUTES][1:],
}
REQUIRED_NUMBERS = ("check_in_minutes", "confirm_minutes")
LENGTHS = ("best_of", "best_of_late", "best_of_finals")
FLAGS = ("third_place", "grand_final_reset")


class Stop(Exception):
    """A refusal on its way out as an Outcome."""

    def __init__(self, outcome: Outcome) -> None:
        super().__init__(outcome.code)
        self.outcome = outcome


def answered(move: Any) -> Any:
    @functools.wraps(move)
    async def wrapper(*args: Any, **kwargs: Any) -> Outcome:
        try:
            return await move(*args, **kwargs)
        except Stop as stop:
            return stop.outcome

    return wrapper


def lock_for(bot: Any, tournament_id: int) -> asyncio.Lock:
    locks = bot.__dict__.setdefault(LOCKS_ATTR, {})
    found = locks.get(int(tournament_id))
    if found is None:
        found = locks[int(tournament_id)] = asyncio.Lock()
    return found


def mode_of(store: Any, guild_id: int) -> str:
    found = str(store.get(guild_id, BRACKETS_MODE))
    return found if found in BRACKETS_MODES else OFF


def said(store: Any, guild_id: int, key: str, **fields: Any) -> str:
    """Staff wording first; a template that cannot be filled falls back to the shipped one."""
    wording = str(store.get(guild_id, key) or "").strip()
    if wording:
        try:
            return wording.format(**fields)
        except (IndexError, KeyError, ValueError):
            log.warning("brackets: %s could not be filled in; the shipped wording was used", key)
    return str(BRACKETS_DEFAULTS[key]).format(**fields)


def stop(bot: Any, guild: Any, key: str, code: str, status: int, **fields: Any) -> Stop:
    return Stop(Outcome(False, said(bot.store, guild.id, key, **fields), code, status))


def done(bot: Any, guild: Any, key: str, value: Any = None, **fields: Any) -> Outcome:
    return Outcome(True, said(bot.store, guild.id, key, **fields), value=value)


def now_stamp() -> str:
    return store_.stamp()


def actor_id(actor: Any) -> int | None:
    found = getattr(actor, "id", None)
    return int(found) if found is not None else None


def state_words(bot: Any, guild: Any, state: str) -> str:
    return said(bot.store, guild.id, f"brackets_state_{state}")


def role_words(bot: Any, guild: Any) -> str:
    role_id = bot.store.get(guild.id, BRACKETS_TO_ROLE)
    role = guild.get_role(int(role_id)) if role_id and hasattr(guild, "get_role") else None
    if role is not None:
        return f"**{role.name}**"
    return said(bot.store, guild.id, "brackets_no_role_words")


async def note(
    bot: Any,
    guild: Any,
    event: str,
    actor: Any,
    tournament_id: int,
    via: str,
    *,
    target: Any = None,
    **details: Any,
) -> None:
    kind = kind_via(f"{HEAD}.{event}", via)
    try:
        await log_action(
            bot,
            guild,
            kind,
            actor=actor,
            target=target,
            details={"via": via, "tournament": tournament_id, **details},
        )
    except Exception:
        log.exception("brackets: could not write the %s row", kind)


def require_on(bot: Any, guild: Any) -> None:
    if mode_of(bot.store, guild.id) == OFF:
        raise stop(bot, guild, "brackets_off_said", "brackets_off", 409)


def require_runner(bot: Any, guild: Any, actor: Any) -> None:
    if not access.may_run(bot.store, guild, actor):
        raise stop(
            bot,
            guild,
            "brackets_not_organiser_said",
            "not_organiser",
            403,
            role=role_words(bot, guild),
        )


def require_state(bot: Any, guild: Any, row: Any, *allowed: str) -> None:
    if row["state"] not in allowed:
        raise stop(
            bot,
            guild,
            WRONG_STATE,
            "wrong_state",
            409,
            name=row["name"],
            state=state_words(bot, guild, row["state"]),
        )


async def loaded(bot: Any, guild: Any, tournament_id: int) -> Any:
    row = await store_.tournament(bot.db, guild.id, int(tournament_id))
    if row is None:
        raise stop(
            bot, guild, "brackets_no_tournament_said", "no_tournament", 404, id=tournament_id
        )
    return row


async def person(bot: Any, guild: Any, row: Any, entrant_id: int) -> Any:
    found = await store_.entrant(bot.db, row["id"], int(entrant_id))
    if found is None:
        raise stop(
            bot,
            guild,
            "brackets_not_in_bracket_said",
            "no_entrant",
            404,
            entrant=f"#{entrant_id}",
            name=row["name"],
        )
    return found


def engine_stop(bot: Any, guild: Any, row: Any, error: BracketError, names: dict) -> Stop:
    fields = {"name": row["name"], "entrant": "", "count": 0, **names, **error.fields}
    fields["set"] = str(fields.get("set", ""))
    return stop(
        bot,
        guild,
        ENGINE_WORDS.get(error.code, WRONG_STATE),
        error.code,
        ENGINE_STATUS.get(error.code, 409),
        state=state_words(bot, guild, row["state"]),
        **fields,
    )


def engine(bot: Any, guild: Any, row: Any, names: dict, move: Any, *args: Any, **kw: Any) -> Any:
    try:
        return move(*args, **kw)
    except BracketError as error:
        raise engine_stop(bot, guild, row, error, names) from None


def clean_text(value: Any, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def option_values(bot: Any, guild: Any, given: dict[str, Any], *, creating: bool) -> dict:
    """The options a create or an edit may set, each checked; a bad one refuses in words."""
    store = bot.store
    found: dict[str, Any] = {}
    if creating:
        found = {
            "format": store.get(guild.id, BRACKETS_FORMAT_DEFAULT),
            "third_place": int(bool(store.get(guild.id, BRACKETS_THIRD_PLACE))),
            "grand_final_reset": int(bool(store.get(guild.id, BRACKETS_GRAND_FINAL_RESET))),
            "swiss_rounds": store.get(guild.id, BRACKETS_SWISS_ROUNDS),
            "best_of": int(store.get(guild.id, BRACKETS_BEST_OF)),
            "best_of_from_round": store.get(guild.id, BRACKETS_BEST_OF_FROM_ROUND),
            "best_of_late": int(store.get(guild.id, BRACKETS_BEST_OF_LATE)),
            "best_of_finals": int(store.get(guild.id, BRACKETS_BEST_OF_FINALS)),
            "entrant_cap": store.get(guild.id, BRACKETS_ENTRANT_CAP),
            "check_in_minutes": int(store.get(guild.id, BRACKETS_CHECK_IN_MINUTES)),
            "confirm_minutes": int(store.get(guild.id, BRACKETS_CONFIRM_MINUTES)),
        }

    def bad(field: str, allowed: str) -> Stop:
        return stop(
            bot,
            guild,
            "brackets_bad_option_said",
            "bad_option",
            400,
            field=field,
            given=str(given.get(field))[:40],
            allowed=allowed,
        )

    if "name" in given or creating:
        name = clean_text(given.get("name"), NAME_LIMIT + 1)
        if not name or len(name) > NAME_LIMIT:
            raise stop(bot, guild, "brackets_no_name_said", "no_name", 400, limit=NAME_LIMIT)
        found["name"] = name
    if "game" in given:
        found["game"] = clean_text(given.get("game"), GAME_LIMIT) or None
    if "rules_text" in given:
        found["rules_text"] = str(given.get("rules_text") or "").strip()[:RULES_LIMIT] or None
    if "format" in given:
        if given["format"] not in FORMATS:
            raise bad("format", ", ".join(FORMATS))
        found["format"] = given["format"]
    for field in FLAGS:
        if field in given:
            if not isinstance(given[field], bool):
                raise bad(field, "true or false")
            found[field] = int(given[field])
    for field in LENGTHS:
        if field in given:
            if not bestof.valid_length(given[field]):
                raise bad(field, f"an odd number from 1 to {bestof.LONGEST}")
            found[field] = given[field]
    for field, (low, high) in NUMBER_RANGES.items():
        if field not in given:
            continue
        value = given[field]
        if value is None and field not in REQUIRED_NUMBERS:
            found[field] = None
            continue
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise bad(field, f"a whole number from {low} to {high}")
        found[field] = value
    if "starts_at" in given:
        found["starts_at"] = when(bot, guild, given["starts_at"], bad)
    if "to_user_id" in given:
        value = given["to_user_id"]
        try:
            found["to_user_id"] = int(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            raise bad("to_user_id", "a member's id") from None
    return found


def when(bot: Any, guild: Any, value: Any, bad: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        found = datetime.fromisoformat(str(value))
    except ValueError:
        raise bad("starts_at", "a date and time like 2026-10-20T19:00:00+00:00") from None
    return (found if found.tzinfo else found.replace(tzinfo=UTC)).astimezone(UTC).isoformat()


@answered
async def create(
    bot: Any, guild: Any, actor: Any, given: dict[str, Any], *, via: str = VIA_DISCORD
) -> Outcome:
    require_on(bot, guild)
    require_runner(bot, guild, actor)
    values = option_values(bot, guild, given, creating=True)
    values.setdefault("to_user_id", actor_id(actor))
    tournament_id = await store_.create(bot.db, guild.id, values, actor_id(actor) or 0)
    await note(bot, guild, "created", actor, tournament_id, via, name=values["name"])
    return done(bot, guild, "brackets_created_said", tournament_id, name=values["name"])


@answered
async def edit(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    given: dict[str, Any],
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        require_state(bot, guild, row, *store_.BEFORE_START)
        values = option_values(bot, guild, given, creating=False)
        await store_.update(bot.db, row["id"], values)
        name = values.get("name", row["name"])
        await note(bot, guild, "edited", actor, row["id"], via, changed=sorted(values))
        return done(bot, guild, "brackets_edited_said", row["id"], name=name)


async def moved_state(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    via: str,
    *,
    allowed: tuple[str, ...],
    to: str,
    event: str,
    key: str,
    extra: dict[str, Any] | None = None,
) -> Outcome:
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        require_state(bot, guild, row, *allowed)
        await store_.update(bot.db, row["id"], {"state": to, **(extra or {})})
        await note(bot, guild, event, actor, row["id"], via, was=row["state"])
        return done(bot, guild, key, row["id"], name=row["name"])


@answered
async def open_signups(
    bot: Any, guild: Any, actor: Any, tournament_id: int, *, via: str = VIA_DISCORD
) -> Outcome:
    return await moved_state(
        bot,
        guild,
        actor,
        tournament_id,
        via,
        allowed=(store_.DRAFT, store_.SEEDING),
        to=store_.SIGNUPS,
        event="signups_opened",
        key="brackets_signups_opened_said",
    )


@answered
async def close_signups(
    bot: Any, guild: Any, actor: Any, tournament_id: int, *, via: str = VIA_DISCORD
) -> Outcome:
    return await moved_state(
        bot,
        guild,
        actor,
        tournament_id,
        via,
        allowed=(store_.SIGNUPS,),
        to=store_.SEEDING,
        event="signups_closed",
        key="brackets_signups_closed_said",
    )


@answered
async def open_check_in(
    bot: Any, guild: Any, actor: Any, tournament_id: int, *, via: str = VIA_DISCORD
) -> Outcome:
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
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
            "brackets_check_in_opened_said",
            row["id"],
            name=row["name"],
            closes=f"<t:{int(closes.timestamp())}:t>",
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
    return done(
        bot, guild, "brackets_check_in_closed_said", row["id"], name=row["name"], removed=len(gone)
    )


@answered
async def close_check_in(
    bot: Any, guild: Any, actor: Any, tournament_id: int, *, via: str = VIA_DISCORD
) -> Outcome:
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
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
            closes = play.parsed(fresh["check_in_closes_at"]) if fresh else None
            if (
                fresh is None
                or fresh["state"] != store_.CHECK_IN
                or not checkin.due(closes, moment)
            ):
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
    via: str = VIA_DISCORD,
) -> Outcome:
    """The TO adds a member, or a guest who is not on Discord (no user id; the TO reports)."""
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        require_state(bot, guild, row, *store_.BEFORE_START)
        member = guild.get_member(int(user_id)) if user_id is not None else None
        wanted = clean_text(name or getattr(member, "display_name", None), NAME_LIMIT + 1)
        if not wanted or len(wanted) > NAME_LIMIT:
            raise stop(bot, guild, "brackets_no_name_said", "no_name", 400, limit=NAME_LIMIT)
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
        )
        return done(
            bot, guild, "brackets_entrant_added_said", row["id"], entrant=wanted, name=row["name"]
        )


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
            bot,
            guild,
            "brackets_entrant_removed_said",
            row["id"],
            entrant=found["name"],
            name=row["name"],
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
        require_state(bot, guild, row, *store_.BEFORE_START, store_.RUNNING)
        found = await person(bot, guild, row, entrant_id)
        names = {"entrant": found["name"], "name": row["name"]}
        if not found["dropped"] and not found["dq"]:
            raise stop(bot, guild, "brackets_not_out_said", "not_out", 409, **names)
        if row["state"] == store_.RUNNING:
            current = await store_.bracket(bot.db, row)
            if current is not None and found["id"] in current.entrants:
                moved = engine(bot, guild, row, names, play.reinstate, current, found["id"], None)
                await store_.save(bot.db, row["id"], moved.bracket, moved.changed, moved.removed)
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
        return done(bot, guild, "brackets_entrant_restored_said", row["id"], **names)


async def withdrawn(
    bot: Any, guild: Any, actor: Any, row: Any, found: Any, why: str, via: str
) -> Outcome:
    names = {"entrant": found["name"], "name": row["name"]}
    if found["dq"] or found["dropped"]:
        raise stop(bot, guild, "brackets_already_out_said", "already_out", 409, **names)
    current = await store_.bracket(bot.db, row)
    if current is None:
        raise stop(bot, guild, "brackets_not_in_bracket_said", "not_in_bracket", 409, **names)
    moved = engine(bot, guild, row, names, play.withdraw, current, found["id"], why, now_stamp())
    flags = {"dq": 1} if why == DQ else {"dropped": 1, "dropped_why": store_.DROPPED}
    await store_.update_entrant(bot.db, found["id"], flags | {"dropped_at": now_stamp()})
    await store_.save(bot.db, row["id"], moved.bracket, moved.changed, moved.removed)
    event = "dq" if why == DQ else "dropped"
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
    return done(bot, guild, f"brackets_{event}_said", row["id"], **names)


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
        require_state(bot, guild, row, store_.RUNNING)
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
        require_state(bot, guild, row, *store_.BEFORE_START, store_.RUNNING)
        if row["state"] == store_.RUNNING:
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
            bot,
            guild,
            "brackets_entrant_removed_said",
            row["id"],
            entrant=found["name"],
            name=row["name"],
        )


def active(people: list[Any]) -> list[Any]:
    return [one for one in people if not one["dropped"] and not one["dq"]]


@answered
async def seed(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    *,
    order: list[int] | None = None,
    randomise: bool = False,
    via: str = VIA_DISCORD,
) -> Outcome:
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        require_state(bot, guild, row, *store_.BEFORE_START)
        people = await store_.entrants(bot.db, row["id"])
        playing = [one["id"] for one in active(people)]
        names = {"name": row["name"]}
        if randomise:
            wanted = seeding.randomised(playing)
        else:
            try:
                given = [int(one) for one in order or []]
            except (TypeError, ValueError):
                given = []
            wanted = engine(bot, guild, row, names, seeding.reordered, playing, given)
        rest = [one["id"] for one in people if one["id"] not in wanted]
        await store_.write_seeds(bot.db, row["id"], wanted + rest)
        await note(bot, guild, "seeded", actor, row["id"], via, order=wanted, randomised=randomise)
        return done(bot, guild, "brackets_seeded_said", row["id"], **names)


@answered
async def start(
    bot: Any, guild: Any, actor: Any, tournament_id: int, *, via: str = VIA_DISCORD
) -> Outcome:
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        if row["state"] == store_.CHECK_IN:
            raise stop(
                bot, guild, "brackets_check_in_open_said", "check_in_open", 409, name=row["name"]
            )
        require_state(bot, guild, row, *store_.BEFORE_START)
        people = active(await store_.entrants(bot.db, row["id"]))
        names = {"name": row["name"]}
        stamp = now_stamp()
        built = engine(
            bot,
            guild,
            row,
            names,
            play.build,
            [one["id"] for one in people],
            store_.options_of(row),
            stamp,
        )
        await store_.write_seeds(bot.db, row["id"], [one["id"] for one in people])
        await store_.clear_sets(bot.db, row["id"])
        await store_.save(bot.db, row["id"], built.bracket, built.changed, [])
        await store_.update(bot.db, row["id"], {"state": store_.RUNNING, "started_at": stamp})
        played = sum(1 for one in built.bracket.matches.values() if one.state not in (BYE, VOID))
        await note(bot, guild, "started", actor, row["id"], via, entrants=len(people))
        return done(bot, guild, "brackets_started_said", row["id"], name=row["name"], sets=played)


@answered
async def unstart(
    bot: Any, guild: Any, actor: Any, tournament_id: int, *, via: str = VIA_DISCORD
) -> Outcome:
    """Back to seeding: every set and result is cleared, as start.gg's phase reset."""
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        require_state(bot, guild, row, store_.RUNNING)
        await store_.clear_sets(bot.db, row["id"])
        await store_.write_placements(bot.db, row["id"], {})
        await store_.update(bot.db, row["id"], {"state": store_.SEEDING, "started_at": None})
        await note(bot, guild, "unstarted", actor, row["id"], via)
        return done(bot, guild, "brackets_unstarted_said", row["id"], name=row["name"])


@answered
async def complete(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    *,
    order: list[int] | None = None,
    via: str = VIA_DISCORD,
) -> Outcome:
    """Placements written; a round robin or Swiss tie is split by the TO's order when given."""
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        require_state(bot, guild, row, store_.RUNNING)
        current = await store_.bracket(bot.db, row)
        names = {"name": row["name"]}
        if current is None or not play.finished(current):
            left = sum(
                1 for one in (current.matches.values() if current else ()) if one.state not in DONE
            )
            raise stop(
                bot, guild, "brackets_unfinished_said", "unfinished", 409, open=left, **names
            )
        if order is not None:
            try:
                wanted = [int(one) for one in order]
            except (TypeError, ValueError):
                wanted = [0]
            if len(set(wanted)) != len(wanted) or not set(wanted) <= set(current.entrants):
                raise stop(bot, guild, "brackets_bad_order_said", "bad_order", 400)
            await store_.write_final_order(bot.db, row["id"], wanted)
            current.final_order = wanted
        placed = standings.placements(current)
        await store_.write_placements(bot.db, row["id"], placed)
        await store_.update(
            bot.db, row["id"], {"state": store_.COMPLETE, "completed_at": now_stamp()}
        )
        await note(bot, guild, "completed", actor, row["id"], via, placements=placed)
        return done(bot, guild, "brackets_completed_said", row["id"], **names)


@answered
async def reopen(
    bot: Any, guild: Any, actor: Any, tournament_id: int, *, via: str = VIA_DISCORD
) -> Outcome:
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        require_state(bot, guild, row, store_.COMPLETE)
        await store_.write_placements(bot.db, row["id"], {})
        await store_.update(bot.db, row["id"], {"state": store_.RUNNING, "completed_at": None})
        await note(bot, guild, "reopened", actor, row["id"], via)
        return done(bot, guild, "brackets_reopened_said", row["id"], name=row["name"])


@answered
async def cancel(
    bot: Any, guild: Any, actor: Any, tournament_id: int, *, via: str = VIA_DISCORD
) -> Outcome:
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        require_state(bot, guild, row, *(one for one in store_.STATES if one != store_.CANCELLED))
        await store_.update(
            bot.db,
            row["id"],
            {"state": store_.CANCELLED, "state_before": row["state"], "cancelled_at": now_stamp()},
        )
        await note(bot, guild, "cancelled", actor, row["id"], via, was=row["state"])
        return done(bot, guild, "brackets_cancelled_said", row["id"], name=row["name"])


@answered
async def restore(
    bot: Any, guild: Any, actor: Any, tournament_id: int, *, via: str = VIA_DISCORD
) -> Outcome:
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        require_state(bot, guild, row, store_.CANCELLED)
        back = row["state_before"] if row["state_before"] in store_.STATES else store_.DRAFT
        await store_.update(
            bot.db, row["id"], {"state": back, "state_before": None, "cancelled_at": None}
        )
        await note(bot, guild, "restored", actor, row["id"], via, to=back)
        return done(bot, guild, "brackets_restored_said", row["id"], name=row["name"])


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
async def confirm(
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
                play.confirm,
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
