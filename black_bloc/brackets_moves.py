"""Tournament moves and the helpers all moves share: a lock each, the engine, the row, the log."""

from __future__ import annotations

import asyncio
import functools
import logging
from datetime import UTC, datetime
from typing import Any

from . import brackets_store as store_
from .actionlog import log_action
from .brackets import access, bestof, play, seeding, standings
from .brackets.model import (
    BYE,
    DONE,
    FORMATS,
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
