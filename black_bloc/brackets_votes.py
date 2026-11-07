"""List-bracket votes: a member's vote, the organiser's Close now, and the minute's close sweep."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from . import brackets_store as store_
from .brackets import play
from .brackets.model import BY_VOTES, REPORTED
from .brackets_moves import (
    OFF,
    actor_id,
    answered,
    done,
    lock_for,
    mode_of,
    note,
    now_stamp,
    require_on,
    require_runner,
    stop,
    touched,
)
from .brackets_sets import entrant_name, kept, overridden, running, the_set
from .logkinds import VIA_DISCORD, VIA_WEBSITE
from .panels import Outcome
from .settings_store import BRACKETS_VOTES_VISIBLE, DEFAULT_TIMEZONE_KEY
from .timezones import DEFAULT_TZ, zone

log = logging.getLogger(__name__)


def when_words(bot: Any, guild: Any, stamp: Any, via: str) -> str:
    """A Discord timestamp in Discord; on the site, a plain day and time in the server's zone."""
    found = play.parsed(stamp)
    if found is None:
        return ""
    if via != VIA_WEBSITE:
        return f"<t:{int(found.timestamp())}:f>"
    name = bot.store.get(guild.id, DEFAULT_TIMEZONE_KEY) or DEFAULT_TZ
    local = found.astimezone(zone(name) or zone(DEFAULT_TZ) or UTC)
    hour = local.hour % 12 or 12
    clock = f"{hour}:{local.minute:02d} {'am' if local.hour < 12 else 'pm'}"
    return f"{local:%a} {clock} {local.tzname()}"


def visible(bot: Any, guild: Any) -> bool:
    return bool(bot.store.get(guild.id, BRACKETS_VOTES_VISIBLE))


def is_open(match: Any, held: dict[str, Any] | None) -> bool:
    return bool(held) and match.state in store_.VOTE_OPEN and not held["closed_at"]


def due(held: dict[str, Any], moment: datetime) -> bool:
    """An unreadable closing time is due now, so a bad row never holds a vote open for ever."""
    closes = play.parsed(held["closes_at"])
    return closes is None or closes <= moment


def votes_only(bot: Any, guild: Any, row: Any, key: str) -> None:
    if not store_.votes_decide(row):
        raise stop(bot, guild, "brackets_not_votes_said", "not_votes", 409, set=key)


@answered
async def vote(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    key: str,
    slot: Any,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """Anyone in the server may vote while the set is open; a second press changes the vote."""
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row, current, people, _ = await running(bot, guild, tournament_id)
        match = the_set(bot, guild, row, current, key)
        votes_only(bot, guild, row, match.key)
        if slot not in store_.VOTE_SLOTS or match.slot(slot) is None:
            raise stop(bot, guild, "brackets_vote_pick_said", "bad_slot", 400, set=match.key)
        held = await store_.ballot(bot.db, row["id"], match.key)
        if not is_open(match, held) or due(held, datetime.now(UTC)):
            raise stop(bot, guild, "brackets_vote_not_open_said", "vote_closed", 409, set=match.key)
        user = actor_id(actor)
        if user is None:
            raise stop(bot, guild, "brackets_not_in_set_said", "not_in_set", 403, set=match.key)
        await store_.cast(bot.db, row["id"], match.key, user, slot)
        outcome = done(
            bot,
            guild,
            "brackets_vote_said",
            row["id"],
            name=entrant_name(people, match.slot(slot)),
            closes=when_words(bot, guild, held["closes_at"], via),
        )
        return replace(outcome, changed=(match.key,))


async def closed(
    bot: Any,
    guild: Any,
    actor: Any,
    row: Any,
    current: Any,
    people: dict,
    match: Any,
    held: dict[str, Any],
    via: str,
) -> Outcome:
    """The counts become the score and the higher side wins through override; level waits on
    the organiser."""
    a, b = int(held["a"]), int(held["b"])
    counts = {"votes_a": a, "votes_b": b}
    if a == b:
        stamp = now_stamp()
        work = play.working(current)
        tied = work.matches[match.key]
        tied.state, tied.score_a, tied.score_b, tied.reported_at = REPORTED, a, b, stamp
        moved = play.moved(work, current, stamp)
        _, gone = await kept(bot, guild, row, moved)
        await note(
            bot, guild, "vote_closed", actor, row["id"], via, set=match.key, tied=True, **counts
        )
        outcome = done(
            bot,
            guild,
            "brackets_vote_tied_line",
            row["id"],
            a=entrant_name(people, match.slot_a),
            b=entrant_name(people, match.slot_b),
            **counts,
        )
        return touched(outcome, moved, gone)
    return await overridden(
        bot,
        guild,
        actor,
        row,
        current,
        people,
        match,
        via,
        event="vote_closed",
        extra={"tied": False, **counts},
        score_a=a,
        score_b=b,
        free=True,
        how=BY_VOTES,
    )


@answered
async def close_vote(
    bot: Any, guild: Any, actor: Any, tournament_id: int, key: str, *, via: str = VIA_DISCORD
) -> Outcome:
    """The organiser's Close now: the vote is counted at once."""
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row, current, people, _ = await running(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        match = the_set(bot, guild, row, current, key)
        votes_only(bot, guild, row, match.key)
        held = await store_.ballot(bot.db, row["id"], match.key)
        if not is_open(match, held):
            raise stop(bot, guild, "brackets_vote_not_open_said", "vote_closed", 409, set=match.key)
        return await closed(bot, guild, actor, row, current, people, match, held, via)


async def close_due_votes(
    bot: Any, guild: Any, now: datetime | None = None, *, via: str = VIA_DISCORD
) -> dict[int, tuple[str, ...]]:
    """The sweep: every running voted list bracket opens what became playable and closes what
    is due; answers the set keys each tournament's cards owe."""
    if mode_of(bot.store, guild.id) == OFF:
        return {}
    moment = now or datetime.now(UTC)
    owed: dict[int, tuple[str, ...]] = {}
    for row in await store_.tournaments(bot.db, guild.id):
        if row["state"] != store_.RUNNING or not store_.votes_decide(row):
            continue
        keys: list[str] = []
        async with lock_for(bot, row["id"]):
            fresh = await store_.tournament(bot.db, guild.id, row["id"])
            if fresh is None or fresh["state"] != store_.RUNNING:
                continue
            keys += await store_.sync_votes(bot.db, fresh)
            held = await store_.ballots(bot.db, fresh["id"])
            for key in sorted(held):
                current = await store_.bracket(bot.db, fresh)
                match = current.matches.get(key) if current is not None else None
                if match is None or not is_open(match, held[key]) or not due(held[key], moment):
                    continue
                people = {one["id"]: one for one in await store_.entrants(bot.db, fresh["id"])}
                try:
                    outcome = await closed(
                        bot, guild, None, fresh, current, people, match, held[key], via
                    )
                except Exception:
                    log.exception("brackets: closing the vote on %s %s failed", fresh["id"], key)
                    continue
                keys += list(outcome.changed)
                held = await store_.ballots(bot.db, fresh["id"])
        if keys:
            owed[int(row["id"])] = tuple(dict.fromkeys(keys))
    return owed


__all__ = ["close_due_votes", "close_vote", "closed", "vote", "when_words"]
