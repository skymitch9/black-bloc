from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from ... import marathon as mt
from ... import marathon_overlay as overlay
from ... import marathon_signals as sig
from ...actionlog import log_action
from ...logkinds import VIA_DISCORD, kind_via
from ...marathon_sources import retimes_itself
from ...panels import Outcome, refusal
from ...settings_store import (
    MARATHON_CATEGORY_CONFIRMS_KEY,
    MARATHON_MOVE_MINUTES_KEY,
    MARATHON_RETRO_CATEGORY_KEY,
    MARATHON_SETUP_MINUTES_KEY,
    MARATHON_TITLE_CONFIRMS_KEY,
)
from ...twitch import TwitchError
from .spotlight import GOLIVE_COG

log = logging.getLogger(__name__)

LOOKUP_BATCH = 25


def helix_of(bot: Any) -> Any:
    getter = getattr(bot, "get_cog", None)
    cog = getter(GOLIVE_COG) if callable(getter) else None
    return getattr(cog, "helix", None)


def watching(bot: Any, guild_id: int) -> bool:
    store = bot.store
    return bool(
        store.get(guild_id, MARATHON_TITLE_CONFIRMS_KEY)
        or store.get(guild_id, MARATHON_CATEGORY_CONFIRMS_KEY)
    )


def _cell(row: Any, key: str) -> Any:
    try:
        return row[key]
    except (IndexError, KeyError, TypeError):
        return None


def setup_minutes(bot: Any, guild_id: int) -> int:
    return int(bot.store.get(guild_id, MARATHON_SETUP_MINUTES_KEY) or 0)


def setup_for(bot: Any, guild_id: int, source: Any) -> dict[str, int]:
    """The setup buffer as the schedule reader's keyword — only for a schedule Black Bloc
    keeps the clock for; any other source is read exactly as before."""
    if retimes_itself(source):
        return {}
    return {"setup_minutes": setup_minutes(bot, guild_id)}


def holds(marathon: Any, row: Any) -> bool:
    """A live or done run of a schedule Black Bloc keeps the clock for is not moved by a read."""
    return not retimes_itself(_cell(marathon, "source")) and sig.settled(row)


def held_plan(marathon: Any, updates: Any) -> list[tuple[Any, Any, bool]]:
    return [(row, run, moved and not holds(marathon, row)) for row, run, moved in updates]


async def resolve_categories(cog: Any, guild: Any, marathon: Any) -> int:
    """Each run's Twitch category, asked for once and kept on the run; a lookup Twitch refuses
    is tried again after a while, never every minute."""
    from .marathon import runs_of, update_run

    bot = cog.bot
    if not marathon["spotlight_id"] or not bot.store.get(guild.id, MARATHON_CATEGORY_CONFIRMS_KEY):
        return 0
    wanted = [row for row in await runs_of(bot.db, marathon["id"]) if sig.wants_lookup(row)]
    if not wanted:
        return 0
    now = cog.clock()
    tried = cog.__dict__.setdefault("category_tried", {})
    last = tried.get(int(marathon["id"]))
    if last is not None and now - last < sig.LOOK_AGAIN:
        return 0
    helix = helix_of(bot)
    if helix is None:
        tried[int(marathon["id"])] = now
        return 0
    wanted = wanted[:LOOKUP_BATCH]
    names = [name for row in wanted for name in sig.lookup_names(row)]
    try:
        named = await helix.games_named(names)
        searched: dict[str, list[Any]] = {}
        for row in wanted:
            if sig.found_in(row, named, {}) is not None:
                continue
            for name in sig.lookup_names(row):
                if name not in searched:
                    searched[name] = await helix.search_categories(name)
    except TwitchError as exc:
        tried[int(marathon["id"])] = now
        await log_action(
            bot,
            guild,
            "marathon.category_lookup_failed",
            details={"marathon_id": marathon["id"], "runs": len(wanted), "reason": str(exc)[:200]},
        )
        return 0
    tried.pop(int(marathon["id"]), None)
    stamp = now.isoformat()
    found = 0
    for row in wanted:
        game = sig.found_in(row, named, searched)
        found += int(game is not None)
        await update_run(
            bot.db,
            row["id"],
            twitch_game_id=getattr(game, "id", None) or None,
            twitch_category=getattr(game, "name", None) or None,
            twitch_looked_at=stamp,
        )
    await log_action(
        bot,
        guild,
        "marathon.categories_found",
        details={"marathon_id": marathon["id"], "found": found, "none": len(wanted) - found},
    )
    return len(wanted)


async def verdict_of(cog: Any, guild: Any, marathon: Any, session: Any, rows: Any, now: datetime):
    """The run the stream shows by title, by category, or both; a disagreement is logged once
    per pair of runs, not every minute."""
    store = cog.bot.store
    title_row = (
        mt.title_hit(_cell(session, "title"), None, rows, now)
        if store.get(guild.id, MARATHON_TITLE_CONFIRMS_KEY)
        else None
    )
    matches = (
        sig.category_matches(
            _cell(session, "game_id"),
            _cell(session, "game"),
            rows,
            now,
            retro=store.get(guild.id, MARATHON_RETRO_CATEGORY_KEY),
        )
        if store.get(guild.id, MARATHON_CATEGORY_CONFIRMS_KEY)
        else []
    )
    verdict = sig.decide(title_row, matches, now)
    seen = cog.__dict__.setdefault("disagreed", {})
    if verdict is None or not verdict.disagree:
        seen.pop(int(marathon["id"]), None)
        return verdict
    pair = (verdict.title_row["id"], verdict.category_row["id"])
    if seen.get(int(marathon["id"])) != pair:
        seen[int(marathon["id"])] = pair
        await log_action(
            cog.bot,
            guild,
            "marathon.signals_disagree",
            details={
                "marathon_id": marathon["id"],
                "title": _cell(session, "title"),
                "category": _cell(session, "game"),
                "category_id": _cell(session, "game_id"),
                "title_run": {"run_id": pair[0], "game": verdict.title_row["game"]},
                "category_run": {"run_id": pair[1], "game": verdict.category_row["game"]},
                "trusted": verdict.because,
                "run_id": verdict.row["id"],
            },
        )
    return verdict


def _moved_enough(before: Any, after: Any, minutes: int) -> bool:
    shift = mt.moved_by(before, after)
    return shift is not None and shift >= int(minutes)


async def retime(cog: Any, guild: Any, marathon: Any, *, because: str) -> int:
    """The clock kept by Black Bloc for a schedule that does not move itself."""
    from .marathon import get_marathon, runs_of, update_run

    if marathon is None or retimes_itself(marathon["source"]):
        return 0
    bot = cog.bot
    kept = await get_marathon(bot.db, guild.id, marathon["id"]) or marathon
    rows = await runs_of(bot.db, marathon["id"])
    if overlay.applied(kept):
        changes = overlay.retimed(rows)
    else:
        changes = sig.retimed(rows, setup_minutes(bot, guild.id))
    if not changes:
        return 0
    now = cog.clock()
    move_minutes = int(bot.store.get(guild.id, MARATHON_MOVE_MINUTES_KEY))
    for change in changes:
        fields: dict[str, Any] = {"scheduled_at": change.starts_at, "ends_at": change.ends_at}
        if _moved_enough(change.row["scheduled_at"], change.starts_at, move_minutes):
            fields["reminders_sent"] = json.dumps(
                mt.rearmed(mt.marks_of(change.row), change.starts_at, now)
            )
        await update_run(bot.db, change.row["id"], **fields)
    first = changes[0]
    await log_action(
        bot,
        guild,
        "marathon.retimed",
        details={
            "marathon_id": marathon["id"],
            "runs": len(changes),
            "because": because,
            "first": {
                "run_id": first.row["id"],
                "game": first.row["game"],
                "from": first.row["scheduled_at"],
                "to": first.starts_at,
            },
        },
    )
    return len(changes)


async def anchor(db: Any, row: Any, at: datetime) -> None:
    from .marathon import update_run

    await update_run(db, row["id"], actual_started_at=at.isoformat(), actual_ended_at=None)


async def sheet_times(
    bot: Any, guild: Any, actor: Any, marathon: Any, *, via: str = VIA_DISCORD
) -> Any:
    """Staff put every run back on the sheet's own times; the stream re-times again only when
    it next shows a run starting."""
    from .marathon import NO_SUCH, cog_of, get_marathon, runs_of, update_run

    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return refusal(mt.NO_SUCH_MARATHON.format(given=marathon["id"]), NO_SUCH, 404)
        back = sig.on_the_sheet(await runs_of(bot.db, fresh["id"]))
        if not back:
            return refusal(
                sig.SHEET_TIMES_NONE.format(name=fresh["name"]), sig.SHEET_TIMES_CODE, 409
            )
        for one in back:
            await update_run(
                bot.db,
                one.row["id"],
                scheduled_at=one.starts_at,
                ends_at=one.ends_at,
                actual_started_at=None,
                actual_ended_at=None,
            )
        await log_action(
            bot,
            guild,
            kind_via("marathon.sheet_times", via),
            actor=actor,
            details={"marathon_id": fresh["id"], "runs": len(back), "via": via},
        )
        await cog.sync_board(guild, await get_marathon(bot.db, guild.id, fresh["id"]))
    return Outcome(True, sig.SHEET_TIMES_DONE.format(name=fresh["name"], count=len(back)))
