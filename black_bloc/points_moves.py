"""Point system moves both doors call: submit, decide, edit, recompute, bounties."""

from __future__ import annotations

import asyncio
import functools
import logging
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import points_store as store_
from .actionlog import log_action
from .brackets.access import holds_role, is_staff
from .events import APPROVED as EVENT_APPROVED
from .events import DEFAULT_DURATION_MINUTES
from .events import DONE as EVENT_DONE
from .events import LIVE as EVENT_LIVE
from .golive import parse_ts
from .logkinds import VIA_DISCORD, kind_via
from .panels import Outcome
from .pb_feed import plain
from .points import clock
from .points.board import Change, Place, diff, standings
from .points.bounty import Bounty
from .points.model import (
    APPROVED,
    BONUS_KINDS,
    BY_POINTS,
    DOWN,
    ENTERED,
    EXTRA,
    LEFT,
    MULTIPLIER,
    PENDING,
    REJECTED,
    REMOVED,
    UP,
    PointsError,
)
from .points.scoring import Rules, Score, score
from .points.xp import DEFAULT_TIERS, parse_tiers
from .settings_store import (
    DEFAULT_TIMEZONE_KEY,
    POINTS_BOUNTY_CLOCK,
    POINTS_DEFAULTS,
    POINTS_MODE,
    POINTS_MODES,
    POINTS_PER_RUN,
    POINTS_TOP_N,
    POINTS_VERIFIER_ROLE,
    POINTS_XP_MAX,
    POINTS_XP_MIN,
    POINTS_XP_TIERS,
)

log = logging.getLogger(__name__)

HEAD = "points"

OFF, SHADOW, ON = POINTS_MODES

GAME_LIMIT = 100

CATEGORY_LIMIT = 100

NOTE_LIMIT = 300

PROOF_LIMIT = 500

REASON_LIMIT = 300

BOUNTY_NAME_LIMIT = 100

BOUNTY_GAMES_MOST = 25

MULTIPLIER_MOST = 10.0

EXTRA_MOST = 100_000

LOCKS_ATTR = "_points_locks"

SUBMITTED = "submitted"

WINDOW_FIELDS = ("event_id", "starts_at", "ends_at")

LINK = re.compile(r"^https?://[^\s/$.?#][^\s]*\.[^\s]+$", re.IGNORECASE)

DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")

EVENT_LIVE_STATES = (EVENT_APPROVED, EVENT_LIVE, EVENT_DONE)

ANNOUNCE_WORDS = {
    ENTERED: "points_announce_entered",
    LEFT: "points_announce_left",
    UP: "points_announce_up",
    DOWN: "points_announce_down",
}

STAFF_WORDS = {
    "approved": "Approved {name}'s **{game}** run ({time}) — {xp} XP, {points} speedpoints.",
    "approved_bounty": (
        "Approved {name}'s **{game}** run ({time}) — {xp} XP, {points} speedpoints with the "
        "bounty **{bounty}**."
    ),
    "rejected": "Rejected {name}'s **{game}** run ({time}).",
    "removed": "Took {name}'s **{game}** run ({time}) off the leaderboard.",
    "edited": "Saved {name}'s **{game}** run ({time}).",
    "reopened": "Saved {name}'s **{game}** run ({time}); it is waiting for a decision again.",
    "recomputed": "Recomputed the approved runs: {count} of {total} changed.",
    "bounty_created": "Created the bounty **{name}**.",
    "bounty_saved": "Saved the bounty **{name}**.",
    "bounty_ended": "Ended the bounty **{name}**.",
    "bounty_already_ended": "The bounty **{name}** has already ended.",
    "no_bounty": "There is no bounty {id} here, so nothing was done.",
    "no_event": "There is no event {id} here, so nothing was saved.",
    "bad_bounty_name": "A bounty needs a name of 1 to {limit} characters, so nothing was saved.",
    "bad_bounty_games": (
        "A bounty needs 1 to {most} games, each 1 to {limit} characters, so nothing was saved."
    ),
    "bad_bounty_kind": "A bounty's bonus is multiplier or extra, so nothing was saved.",
    "bad_bounty_amount": "A {kind} bounty takes {allowed}, not {given}, so nothing was saved.",
    "bad_bounty_window": (
        "A bounty runs during one event or between a start and an end date — give one of "
        "the two, so nothing was saved."
    ),
    "bad_bounty_date": (
        "**{given}** is not a date Black Bloc can read, so nothing was saved. Write it like "
        "2026-10-31 or 2026-10-31T18:00."
    ),
    "bounty_ends_first": "A bounty has to end after it starts, so nothing was saved.",
    "nothing_to_edit": "Nothing was given to change, so nothing was saved.",
}

AMOUNT_WORDS = {
    MULTIPLIER: f"a multiplier above 1 and at most {MULTIPLIER_MOST:g}",
    EXTRA: f"a whole number of extra speedpoints from 1 to {EXTRA_MOST}",
}

REFUSED_STATUS = {
    "no_time": 400,
    "bad_time": 400,
    "bad_tiers": 400,
}


@dataclass(frozen=True)
class Result:
    id: int
    dm: str | None = None
    dm_to: int | None = None
    announce: tuple[str, ...] = ()
    changes: tuple[Change, ...] = ()


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


def lock_for(bot: Any, guild_id: int) -> asyncio.Lock:
    locks = bot.__dict__.setdefault(LOCKS_ATTR, {})
    found = locks.get(int(guild_id))
    if found is None:
        found = locks[int(guild_id)] = asyncio.Lock()
    return found


def mode_of(store: Any, guild_id: int) -> str:
    found = str(store.get(guild_id, POINTS_MODE))
    return found if found in POINTS_MODES else OFF


def said(store: Any, guild_id: int, key: str, **fields: Any) -> str:
    """A staff line from STAFF_WORDS; a member's from staff wording, else the shipped one."""
    if key in STAFF_WORDS:
        return STAFF_WORDS[key].format(**fields)
    wording = str(store.get(guild_id, key) or "").strip()
    if wording:
        try:
            return wording.format(**fields)
        except Exception as exc:
            log.warning("points: %s could not be filled in (%s); shipped wording used", key, exc)
    return str(POINTS_DEFAULTS[key]).format(**fields)


def stop(bot: Any, guild: Any, key: str, code: str, status: int, **fields: Any) -> Stop:
    return Stop(Outcome(False, said(bot.store, guild.id, key, **fields), code, status))


def actor_id(actor: Any) -> int | None:
    found = getattr(actor, "id", None)
    return int(found) if found is not None else None


def now() -> datetime:
    return datetime.now(UTC)


def name_of(guild: Any, user_id: Any) -> str:
    member = guild.get_member(int(user_id)) if hasattr(guild, "get_member") else None
    found = getattr(member, "display_name", None) or getattr(member, "name", None)
    return plain(found) if found else f"<@{int(user_id)}>"


def state_words(bot: Any, guild: Any, state: str) -> str:
    return said(bot.store, guild.id, f"points_state_{state}")


def run_words(row: Any) -> dict[str, Any]:
    return {"game": plain(row["game"]), "time": clock.shown(row["seconds"])}


async def note(
    bot: Any,
    guild: Any,
    event: str,
    actor: Any,
    via: str,
    *,
    target: Any = None,
    reason: Any = None,
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
            reason=reason or None,
            details={"via": via, **details},
        )
    except Exception:
        log.exception("points: could not write the %s row", kind)


def require_on(bot: Any, guild: Any) -> None:
    if mode_of(bot.store, guild.id) == OFF:
        raise stop(bot, guild, "points_off_said", "points_off", 409)


def may_verify(store: Any, guild: Any, person: Any) -> bool:
    """Staff, or a holder of the verifier role; the role decides."""
    if guild is None or person is None:
        return False
    if is_staff(store, person):
        return True
    try:
        wanted = int(store.get(guild.id, POINTS_VERIFIER_ROLE) or 0)
    except (TypeError, ValueError):
        return False
    return bool(wanted) and holds_role(person, wanted)


def role_words(bot: Any, guild: Any) -> str:
    role_id = bot.store.get(guild.id, POINTS_VERIFIER_ROLE)
    role = guild.get_role(int(role_id)) if role_id and hasattr(guild, "get_role") else None
    if role is not None:
        return f"**{role.name}**"
    return said(bot.store, guild.id, "points_no_verifier_role_words")


def require_verifier(bot: Any, guild: Any, actor: Any) -> None:
    if not may_verify(bot.store, guild, actor):
        raise stop(
            bot,
            guild,
            "points_not_verifier_said",
            "not_verifier",
            403,
            role=role_words(bot, guild),
        )


def require_staff(bot: Any, guild: Any, actor: Any) -> None:
    if not is_staff(bot.store, actor):
        raise stop(bot, guild, "points_not_staff_said", "not_staff", 403)


def require_state(bot: Any, guild: Any, row: Any, *allowed: str) -> None:
    if row["state"] not in allowed:
        raise stop(
            bot,
            guild,
            "points_wrong_state_said",
            "wrong_state",
            409,
            state=state_words(bot, guild, row["state"]),
        )


async def raced(bot: Any, guild: Any, run_id: int) -> None:
    """Another process decided the run between the read and the write: say where it is now."""
    row = await loaded(bot, guild, run_id)
    raise stop(
        bot,
        guild,
        "points_wrong_state_said",
        "wrong_state",
        409,
        state=state_words(bot, guild, row["state"]),
    )


async def loaded(bot: Any, guild: Any, run_id: int) -> Any:
    row = await store_.run(bot.db, guild.id, int(run_id))
    if row is None:
        raise stop(bot, guild, "points_no_run_said", "no_run", 404, id=run_id)
    return row


def clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def refused(bot: Any, guild: Any, error: PointsError) -> Stop:
    return stop(
        bot,
        guild,
        f"points_{error.code}_said",
        error.code,
        REFUSED_STATUS.get(error.code, 400),
        **error.fields,
    )


def run_values(bot: Any, guild: Any, given: dict[str, Any], *, creating: bool) -> dict:
    """The fields a submission or an edit may set, each checked; a bad one refuses in words."""
    found: dict[str, Any] = {}
    if creating or "game" in given:
        game = clean(given.get("game"))
        if not game or len(game) > GAME_LIMIT:
            raise stop(bot, guild, "points_no_game_said", "no_game", 400, limit=GAME_LIMIT)
        found["game"] = game
    for field, limit, words in (
        ("category", CATEGORY_LIMIT, "category"),
        ("note", NOTE_LIMIT, "note"),
    ):
        if field in given:
            text = clean(given.get(field))
            if len(text) > limit:
                raise stop(
                    bot, guild, "points_too_long_said", "too_long", 400, field=words, limit=limit
                )
            found[field] = text or None
    if creating or "time" in given:
        try:
            found["seconds"] = clock.seconds_of(given.get("time"))
        except PointsError as error:
            raise refused(bot, guild, error) from None
    if creating or "proof_url" in given:
        proof = str(given.get("proof_url") or "").strip()
        if not proof:
            raise stop(bot, guild, "points_no_proof_said", "no_proof", 400)
        if len(proof) > PROOF_LIMIT or not LINK.match(proof):
            raise stop(bot, guild, "points_bad_proof_said", "bad_proof", 400, given=proof[:60])
        found["proof_url"] = proof
    return found


def rules_of(store: Any, guild_id: int) -> Rules:
    try:
        tiers = parse_tiers(store.get(guild_id, POINTS_XP_TIERS))
    except PointsError:
        log.warning("points: points_xp_tiers could not be read; the shipped tiers were used")
        tiers = DEFAULT_TIERS
    return Rules(
        tiers=tiers,
        low=int(store.get(guild_id, POINTS_XP_MIN)),
        high=int(store.get(guild_id, POINTS_XP_MAX)),
        per_run=int(store.get(guild_id, POINTS_PER_RUN)),
    )


def event_window(event: Any) -> tuple[datetime | None, datetime | None]:
    if event is None or event["status"] not in EVENT_LIVE_STATES:
        return None, None
    starts = parse_ts(event["starts_at"])
    if starts is None:
        return None, None
    ends = parse_ts(event["ends_at"]) or starts + timedelta(minutes=DEFAULT_DURATION_MINUTES)
    return starts, ends


async def bounties_of(bot: Any, guild_id: int) -> list[tuple[Any, Bounty, Any]]:
    """Every bounty with its window resolved: the event's own when it has one, else its dates."""
    rows = await store_.bounties(bot.db, guild_id)
    wanted = sorted({int(row["event_id"]) for row in rows if row["event_id"] is not None})
    found = await store_.events(bot.db, guild_id, wanted)
    resolved = []
    for row in rows:
        event = found.get(int(row["event_id"])) if row["event_id"] is not None else None
        if row["event_id"] is not None:
            starts, ends = event_window(event)
        else:
            starts, ends = parse_ts(row["starts_at"]), parse_ts(row["ends_at"])
        bounty = Bounty(
            int(row["id"]),
            str(row["name"]),
            tuple(store_.games_of(row)),
            str(row["kind"]),
            float(row["amount"]),
            starts,
            ends,
            bool(row["active"]),
        )
        resolved.append((row, bounty, event))
    return resolved


def clock_of(store: Any, guild_id: int, row: Any, decided_at: str | None) -> datetime:
    """The moment a bounty is judged at: the approval, or the submission when staff chose so."""
    if store.get(guild_id, POINTS_BOUNTY_CLOCK) == SUBMITTED:
        return parse_ts(row["submitted_at"]) or now()
    return parse_ts(decided_at) or now()


async def board(bot: Any, guild_id: int, by: str = BY_POINTS) -> list[Place]:
    return standings(await store_.totals(bot.db, guild_id), by)


def top_of(store: Any, guild_id: int) -> int:
    return int(store.get(guild_id, POINTS_TOP_N))


def announce_lines(
    bot: Any, guild: Any, changes: list[Change], after: list[Place], top: int
) -> tuple[str, ...]:
    places = {one.user_id: one for one in after}
    lines = []
    for change in changes:
        place = places.get(change.user_id)
        lines.append(
            said(
                bot.store,
                guild.id,
                ANNOUNCE_WORDS[change.kind],
                name=name_of(guild, change.user_id),
                place=change.now if change.now is not None else "",
                was=change.was if change.was is not None else "",
                top=top,
                points=place.speedpoints if place else 0,
                xp=place.xp if place else 0,
            )
        )
    return tuple(lines)


async def board_moved(
    bot: Any, guild: Any, actor: Any, via: str, before: list[Place]
) -> tuple[tuple[Change, ...], tuple[str, ...]]:
    """What the move did to the top places, and the one row that records it."""
    after = await board(bot, guild.id)
    top = top_of(bot.store, guild.id)
    changes = diff(before, after, top)
    if not changes:
        return (), ()
    lines = announce_lines(bot, guild, changes, after, top)
    event = "top_changed" if mode_of(bot.store, guild.id) == ON else "would_announce"
    await note(
        bot,
        guild,
        event,
        actor,
        via,
        top=top,
        changes=[
            {"kind": one.kind, "user_id": one.user_id, "was": one.was, "now": one.now}
            for one in changes
        ],
        lines=list(lines),
    )
    return tuple(changes), lines


def touched(outcome: Outcome, run_id: int | None, changes: tuple, board_changed: bool) -> Outcome:
    keys = [f"run:{run_id}"] if run_id is not None else []
    if board_changed:
        keys.append("board")
    if changes:
        keys.append("top")
    return replace(outcome, changed=tuple(keys))


def dm_words(bot: Any, guild: Any, key: str, row: Any, reason: str) -> str:
    because = (
        said(bot.store, guild.id, "points_dm_reason", reason=plain(reason))
        if reason
        else said(bot.store, guild.id, "points_dm_no_reason")
    )
    return said(bot.store, guild.id, key, reason=because, **run_words(row))


async def scored(bot: Any, guild: Any, row: Any, decided_at: str) -> Score:
    rules = rules_of(bot.store, guild.id)
    found = [bounty for _, bounty, _ in await bounties_of(bot, guild.id)]
    at = clock_of(bot.store, guild.id, row, decided_at)
    return score(float(row["seconds"]), row["game"], at, rules, found)


@answered
async def submit(
    bot: Any, guild: Any, actor: Any, given: dict[str, Any], *, via: str = VIA_DISCORD
) -> Outcome:
    require_on(bot, guild)
    values = run_values(bot, guild, given, creating=True)
    user_id = actor_id(actor) or 0
    named = given.get("user_id")
    if named not in (None, ""):
        try:
            wanted = int(str(named).strip().lstrip("<@!").rstrip(">"))
        except ValueError:
            wanted = -1
        if wanted != user_id:
            require_staff(bot, guild, actor)
            if wanted <= 0:
                raise stop(bot, guild, "points_no_run_said", "no_member", 404, id=str(named)[:20])
            user_id = wanted
    run_id = await store_.add_run(bot.db, guild.id, user_id, values)
    await note(
        bot,
        guild,
        "submitted",
        actor,
        via,
        target=user_id,
        run=run_id,
        game=values["game"],
        seconds=values["seconds"],
        proof_url=values["proof_url"],
    )
    words = {"game": plain(values["game"]), "time": clock.shown(values["seconds"])}
    outcome = Outcome(
        True, said(bot.store, guild.id, "points_submitted_said", **words), value=Result(run_id)
    )
    return touched(outcome, run_id, (), False)


@answered
async def approve(
    bot: Any, guild: Any, actor: Any, run_id: int, *, via: str = VIA_DISCORD
) -> Outcome:
    require_on(bot, guild)
    async with lock_for(bot, guild.id):
        row = await loaded(bot, guild, run_id)
        require_verifier(bot, guild, actor)
        if row["user_id"] == actor_id(actor) and not is_staff(bot.store, actor):
            raise stop(bot, guild, "points_own_run_said", "own_run", 403)
        require_state(bot, guild, row, PENDING)
        before = await board(bot, guild.id)
        at = store_.stamp()
        found = await scored(bot, guild, row, at)
        values = {
            "state": APPROVED,
            "decided_by": actor_id(actor),
            "decided_at": at,
            "reason": None,
            "xp": found.xp,
            "speedpoints": found.speedpoints,
            "bounty_id": found.bounty_id,
        }
        if not await store_.update_run(bot.db, row["id"], values, when_state=PENDING):
            await raced(bot, guild, row["id"])
        await note(
            bot,
            guild,
            "approved",
            actor,
            via,
            target=row["user_id"],
            run=row["id"],
            game=row["game"],
            xp=found.xp,
            speedpoints=found.speedpoints,
            bounty=found.bounty_id,
        )
        changes, lines = await board_moved(bot, guild, actor, via, before)
    bounty_name = await bounty_name_of(bot, guild, found.bounty_id)
    key = "approved_bounty" if bounty_name else "approved"
    message = said(
        bot.store,
        guild.id,
        key,
        name=name_of(guild, row["user_id"]),
        xp=found.xp,
        points=found.speedpoints,
        bounty=bounty_name,
        **run_words(row),
    )
    outcome = Outcome(True, message, value=Result(row["id"], announce=lines, changes=changes))
    return touched(outcome, row["id"], changes, True)


async def bounty_name_of(bot: Any, guild: Any, bounty_id: int | None) -> str:
    if bounty_id is None:
        return ""
    row = await store_.bounty(bot.db, guild.id, int(bounty_id))
    return plain(row["name"]) if row is not None else ""


def reason_of(reason: Any) -> str:
    return clean(reason)[:REASON_LIMIT]


@answered
async def reject(
    bot: Any, guild: Any, actor: Any, run_id: int, reason: Any = "", *, via: str = VIA_DISCORD
) -> Outcome:
    require_on(bot, guild)
    why = reason_of(reason)
    async with lock_for(bot, guild.id):
        row = await loaded(bot, guild, run_id)
        require_verifier(bot, guild, actor)
        if row["user_id"] == actor_id(actor) and not is_staff(bot.store, actor):
            raise stop(bot, guild, "points_own_run_said", "own_run", 403)
        require_state(bot, guild, row, PENDING)
        values = {
            "state": REJECTED,
            "decided_by": actor_id(actor),
            "decided_at": store_.stamp(),
            "reason": why or None,
        }
        if not await store_.update_run(bot.db, row["id"], values, when_state=PENDING):
            await raced(bot, guild, row["id"])
        await note(
            bot,
            guild,
            "rejected",
            actor,
            via,
            target=row["user_id"],
            reason=why,
            run=row["id"],
            game=row["game"],
        )
    dm = dm_words(bot, guild, "points_dm_rejected", row, why)
    message = said(
        bot.store, guild.id, "rejected", name=name_of(guild, row["user_id"]), **run_words(row)
    )
    outcome = Outcome(True, message, value=Result(row["id"], dm=dm, dm_to=int(row["user_id"])))
    return touched(outcome, row["id"], (), False)


@answered
async def remove(
    bot: Any, guild: Any, actor: Any, run_id: int, reason: Any = "", *, via: str = VIA_DISCORD
) -> Outcome:
    require_on(bot, guild)
    why = reason_of(reason)
    async with lock_for(bot, guild.id):
        row = await loaded(bot, guild, run_id)
        require_staff(bot, guild, actor)
        require_state(bot, guild, row, APPROVED)
        before = await board(bot, guild.id)
        values = {
            "state": REMOVED,
            "decided_by": actor_id(actor),
            "decided_at": store_.stamp(),
            "reason": why or None,
        }
        if not await store_.update_run(bot.db, row["id"], values, when_state=APPROVED):
            await raced(bot, guild, row["id"])
        await note(
            bot,
            guild,
            "removed",
            actor,
            via,
            target=row["user_id"],
            reason=why,
            run=row["id"],
            game=row["game"],
            xp=row["xp"],
            speedpoints=row["speedpoints"],
        )
        changes, lines = await board_moved(bot, guild, actor, via, before)
    dm = dm_words(bot, guild, "points_dm_removed", row, why)
    message = said(
        bot.store, guild.id, "removed", name=name_of(guild, row["user_id"]), **run_words(row)
    )
    outcome = Outcome(
        True,
        message,
        value=Result(row["id"], dm=dm, dm_to=int(row["user_id"]), announce=lines, changes=changes),
    )
    return touched(outcome, row["id"], changes, True)


@answered
async def edit(
    bot: Any,
    guild: Any,
    actor: Any,
    run_id: int,
    given: dict[str, Any],
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """Staff correct a run; a rejected or removed one goes back to waiting for a decision."""
    require_on(bot, guild)
    async with lock_for(bot, guild.id):
        row = await loaded(bot, guild, run_id)
        require_staff(bot, guild, actor)
        values = run_values(bot, guild, given, creating=False)
        reopened = row["state"] in (REJECTED, REMOVED)
        if not values and not reopened:
            raise stop(bot, guild, "nothing_to_edit", "nothing_to_edit", 400)
        before = await board(bot, guild.id)
        merged = {**dict(row), **values}
        if reopened:
            values.update(
                state=PENDING,
                decided_by=None,
                decided_at=None,
                reason=None,
                xp=0,
                speedpoints=0,
                bounty_id=None,
            )
        elif row["state"] == APPROVED:
            found = await scored(bot, guild, merged, row["decided_at"])
            values.update(xp=found.xp, speedpoints=found.speedpoints, bounty_id=found.bounty_id)
        if not await store_.update_run(bot.db, row["id"], values, when_state=row["state"]):
            await raced(bot, guild, row["id"])
        await note(
            bot,
            guild,
            "edited",
            actor,
            via,
            target=row["user_id"],
            run=row["id"],
            changed=sorted(set(values) & set(store_.RUN_FIELDS)),
            was=row["state"],
            reopened=reopened,
        )
        counted = row["state"] == APPROVED
        changes, lines = await board_moved(bot, guild, actor, via, before) if counted else ((), ())
    key = "reopened" if reopened else "edited"
    message = said(
        bot.store, guild.id, key, name=name_of(guild, row["user_id"]), **run_words(merged)
    )
    outcome = Outcome(True, message, value=Result(row["id"], announce=lines, changes=changes))
    return touched(outcome, row["id"], changes, counted)


@answered
async def recompute(bot: Any, guild: Any, actor: Any, *, via: str = VIA_DISCORD) -> Outcome:
    """Every approved run again, under today's tiers, points and bounties, at its own clock."""
    require_on(bot, guild)
    async with lock_for(bot, guild.id):
        require_staff(bot, guild, actor)
        before = await board(bot, guild.id)
        rules = rules_of(bot.store, guild.id)
        found = [bounty for _, bounty, _ in await bounties_of(bot, guild.id)]
        rows = await store_.runs(bot.db, guild.id, state=APPROVED, limit=-1)
        count = 0
        for row in rows:
            at = clock_of(bot.store, guild.id, row, row["decided_at"])
            fresh = score(float(row["seconds"]), row["game"], at, rules, found)
            was = Score(row["xp"], row["speedpoints"], row["bounty_id"])
            if fresh != was:
                count += 1
                await store_.update_run(
                    bot.db,
                    row["id"],
                    {
                        "xp": fresh.xp,
                        "speedpoints": fresh.speedpoints,
                        "bounty_id": fresh.bounty_id,
                    },
                    when_state=APPROVED,
                )
        await note(bot, guild, "recomputed", actor, via, changed=count, total=len(rows))
        changes, lines = await board_moved(bot, guild, actor, via, before)
    message = said(bot.store, guild.id, "recomputed", count=count, total=len(rows))
    outcome = Outcome(True, message, value=Result(0, announce=lines, changes=changes))
    return touched(outcome, None, changes, count > 0)


def when_of(store: Any, guild_id: int, given: Any, *, end: bool) -> datetime:
    """An ISO date or date-time; without a zone it is the server's, a bare end date is inclusive."""
    text = str(given or "").strip()
    try:
        found = datetime.fromisoformat(text)
    except ValueError:
        raise PointsError("bad_bounty_date", given=text[:40]) from None
    if found.tzinfo is None:
        try:
            zone = ZoneInfo(str(store.get(guild_id, DEFAULT_TIMEZONE_KEY) or "UTC"))
        except (ZoneInfoNotFoundError, ValueError):
            zone = ZoneInfo("UTC")
        found = found.replace(tzinfo=zone)
    if end and DATE_ONLY.match(text):
        found += timedelta(days=1)
    return found.astimezone(UTC)


def bounty_values(
    bot: Any, guild: Any, given: dict[str, Any], row: Any, events: dict[int, Any]
) -> dict[str, Any]:
    """The fields a bounty create or edit may set, each checked; a bad one refuses in words."""
    found: dict[str, Any] = {}

    def bad(key: str, **fields: Any) -> Stop:
        return stop(bot, guild, key, key, 400, **fields)

    if row is None or "name" in given:
        name = clean(given.get("name"))
        if not name or len(name) > BOUNTY_NAME_LIMIT:
            raise bad("bad_bounty_name", limit=BOUNTY_NAME_LIMIT)
        found["name"] = name
    if row is None or "games" in given:
        games = given.get("games")
        games = [games] if isinstance(games, str) else games
        cleaned = [clean(one) for one in games] if isinstance(games, list) else []
        if (
            not cleaned
            or len(cleaned) > BOUNTY_GAMES_MOST
            or any(not one or len(one) > GAME_LIMIT for one in cleaned)
        ):
            raise bad("bad_bounty_games", most=BOUNTY_GAMES_MOST, limit=GAME_LIMIT)
        found["games"] = list(dict.fromkeys(cleaned))
    kind = given.get("kind", row["kind"] if row is not None else None)
    if kind not in BONUS_KINDS:
        raise bad("bad_bounty_kind")
    if row is None or "kind" in given or "amount" in given:
        found["kind"] = kind
        raw = given.get("amount", row["amount"] if row is not None else None)
        try:
            amount = float(raw)
        except (TypeError, ValueError):
            amount = float("nan")
        fits = (
            1 < amount <= MULTIPLIER_MOST
            if kind == MULTIPLIER
            else amount.is_integer() and 1 <= amount <= EXTRA_MOST
        )
        if not fits:
            raise bad(
                "bad_bounty_amount", kind=kind, allowed=AMOUNT_WORDS[kind], given=str(raw)[:20]
            )
        found["amount"] = amount
    if row is None or any(key in given for key in WINDOW_FIELDS):
        event_id = given.get("event_id")
        has_event = event_id not in (None, "")
        if has_event and (given.get("starts_at") or given.get("ends_at")):
            raise bad("bad_bounty_window")
        if has_event:
            try:
                wanted = int(event_id)
            except (TypeError, ValueError):
                raise bad("no_event", id=str(event_id)[:20]) from None
            if wanted not in events:
                raise bad("no_event", id=wanted)
            found.update(event_id=wanted, starts_at=None, ends_at=None)
        else:
            starts = given.get("starts_at") or (row["starts_at"] if row is not None else None)
            ends = given.get("ends_at") or (row["ends_at"] if row is not None else None)
            if not starts or not ends:
                raise bad("bad_bounty_window")
            try:
                opens = when_of(bot.store, guild.id, starts, end=False)
                closes = when_of(bot.store, guild.id, ends, end=True)
            except PointsError as error:
                raise bad(error.code, **error.fields) from None
            if closes <= opens:
                raise bad("bounty_ends_first")
            found.update(event_id=None, starts_at=opens.isoformat(), ends_at=closes.isoformat())
    if "active" in given:
        found["active"] = bool(given["active"])
    return found


async def event_ids_in(bot: Any, guild: Any, given: dict[str, Any]) -> dict[int, Any]:
    raw = given.get("event_id")
    try:
        wanted = int(raw) if raw not in (None, "") else None
    except (TypeError, ValueError):
        return {}
    return await store_.events(bot.db, guild.id, [wanted]) if wanted is not None else {}


async def loaded_bounty(bot: Any, guild: Any, bounty_id: int) -> Any:
    row = await store_.bounty(bot.db, guild.id, int(bounty_id))
    if row is None:
        raise stop(bot, guild, "no_bounty", "no_bounty", 404, id=bounty_id)
    return row


@answered
async def bounty_create(
    bot: Any, guild: Any, actor: Any, given: dict[str, Any], *, via: str = VIA_DISCORD
) -> Outcome:
    require_on(bot, guild)
    require_staff(bot, guild, actor)
    events = await event_ids_in(bot, guild, given)
    values = bounty_values(bot, guild, given, None, events)
    bounty_id = await store_.add_bounty(bot.db, guild.id, values, actor_id(actor) or 0)
    await note(
        bot,
        guild,
        "bounty_set",
        actor,
        via,
        bounty=bounty_id,
        created=True,
        name=values["name"],
        games=values["games"],
        kind=values["kind"],
        amount=values["amount"],
        event_id=values.get("event_id"),
    )
    message = said(bot.store, guild.id, "bounty_created", name=plain(values["name"]))
    return replace(
        Outcome(True, message, value=Result(bounty_id)), changed=(f"bounty:{bounty_id}",)
    )


@answered
async def bounty_edit(
    bot: Any,
    guild: Any,
    actor: Any,
    bounty_id: int,
    given: dict[str, Any],
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    require_on(bot, guild)
    require_staff(bot, guild, actor)
    row = await loaded_bounty(bot, guild, bounty_id)
    events = await event_ids_in(bot, guild, given)
    values = bounty_values(bot, guild, given, row, events)
    await store_.update_bounty(bot.db, row["id"], values)
    await note(
        bot,
        guild,
        "bounty_set",
        actor,
        via,
        bounty=row["id"],
        created=False,
        changed=sorted(values),
    )
    name = values.get("name", row["name"])
    message = said(bot.store, guild.id, "bounty_saved", name=plain(name))
    return replace(
        Outcome(True, message, value=Result(row["id"])), changed=(f"bounty:{row['id']}",)
    )


@answered
async def bounty_end(
    bot: Any, guild: Any, actor: Any, bounty_id: int, *, via: str = VIA_DISCORD
) -> Outcome:
    require_on(bot, guild)
    require_staff(bot, guild, actor)
    row = await loaded_bounty(bot, guild, bounty_id)
    if not row["active"]:
        raise stop(
            bot, guild, "bounty_already_ended", "already_ended", 409, name=plain(row["name"])
        )
    await store_.update_bounty(bot.db, row["id"], {"active": False})
    await note(bot, guild, "bounty_ended", actor, via, bounty=row["id"], name=row["name"])
    message = said(bot.store, guild.id, "bounty_ended", name=plain(row["name"]))
    return replace(
        Outcome(True, message, value=Result(row["id"])), changed=(f"bounty:{row['id']}",)
    )
