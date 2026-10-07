from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends

from ... import marathon as mt
from ... import marathon_baf_event as baf
from ... import marathon_inbox as mi
from ... import marathon_schedule_page as page
from ...cogs.content.golive import all_links as twitch_links
from ...cogs.content.marathon import (
    MODE_OFF,
    channel_login,
    get_marathon,
    mode_of,
    runs_of,
)
from ...cogs.content.marathon_announce import announces
from ...cogs.content.marathon_archive import archived_marathon, archived_runs
from ...cogs.content.marathon_baf_event import reading_for, speaks_for
from ...cogs.content.marathon_host_highlights import reminder_marks, role_for, speaking
from ...cogs.content.marathon_host_highlights import wanted as host_posts_wanted
from ...cogs.content.marathon_people import zone_of
from ...cogs.content.marathon_public import people_for
from ...cogs.content.marathon_public_reminders import reminder_channel
from ...cogs.content.marathon_public_reminders import wanted as public_reminders_wanted
from ...cogs.content.marathon_role_ping import verdict_for
from ...cogs.content.marathon_signals import setup_minutes
from ...cogs.content.youtube import all_links as youtube_links
from ...settings_store import (
    MARATHON_FAR_POLL_HOURS_KEY,
    MARATHON_LEAD_DAYS_KEY,
    MARATHON_PING_MINUTES_KEY,
    MARATHON_POLL_MINUTES_KEY,
    MARATHON_REMINDER_STALE_KEY,
    MARATHON_TRACKER_REFRESH_KEY,
)
from ..auth import Refused, staff_dependency
from ..names import resolve_one
from ..writes import require_db, require_guild
from .marathons import BECAUSE_WORDS

log = logging.getLogger(__name__)

SCAN = 400


def kinds() -> tuple[str, ...]:
    return tuple(page.MOVE_KINDS) + tuple(f"web.{one}" for one in page.MOVE_KINDS)


async def recent_moves(db: Any, guild_id: int, marathon_id: int) -> list[dict[str, Any]]:
    """The marathon's action rows that changed a time or a state, newest first."""
    wanted = kinds()
    marks = ", ".join("?" for _ in wanted)
    cur = await db.conn.execute(
        f"SELECT id, at, kind, actor_id, details FROM action_log WHERE guild_id = ? "
        f"AND kind IN ({marks}) AND json_extract(details, '$.marathon_id') = ? "
        "ORDER BY id DESC LIMIT ?",
        (int(guild_id), *wanted, int(marathon_id), SCAN),
    )
    found = []
    for row in await cur.fetchall():
        try:
            details = json.loads(row["details"] or "{}")
        except (TypeError, ValueError):
            details = {}
        found.append(
            {
                "id": row["id"],
                "at": row["at"],
                "kind": row["kind"],
                "actor_id": row["actor_id"],
                "details": details,
            }
        )
    return found


async def links_for(db: Any) -> tuple[dict[int, str], dict[int, Any]]:
    twitch = {int(row["user_id"]): str(row["twitch_login"]) for row in await twitch_links(db)}
    youtube = {int(row["user_id"]): row for row in await youtube_links(db)}
    return (twitch, youtube)


def reading_of(bot: Any, guild: Any, row: Any, now: datetime) -> dict[str, Any]:
    store = bot.store
    lead_days = int(store.get(guild.id, MARATHON_LEAD_DAYS_KEY))
    phase = mt.phase(row, now, lead_days=lead_days)
    read_at = mt.next_read_at(
        row,
        now,
        poll_minutes=int(store.get(guild.id, MARATHON_POLL_MINUTES_KEY)),
        far_hours=int(store.get(guild.id, MARATHON_FAR_POLL_HOURS_KEY)),
        lead_days=lead_days,
    )
    return {
        "phase": phase,
        "phase_word": mt.PHASE_WORDS.get(phase, phase),
        "next_read_at": read_at.isoformat() if read_at is not None else None,
    }


def posting_of(bot: Any, guild: Any, row: Any, runs: Any) -> dict[str, Any]:
    """What the tick would post for this marathon, asked of the tick's own functions."""
    days = reading_for(bot, guild.id, row, runs)
    speaks = speaks_for(bot, guild, row)
    ping_mark = int(bot.store.get(guild.id, MARATHON_PING_MINUTES_KEY))
    verdict = verdict_for(bot, guild, row)
    following = bool(row["active"]) and mode_of(bot, guild.id) != MODE_OFF

    def run_role(run: Any) -> bool:
        return verdict.mentions and bool(people_for(bot, guild, row, run))

    def block_role(block: Any) -> bool:
        found = role_for(bot, guild, row, block, ping_mark, days)
        return found is not None and found.mentions

    return {
        "marks": reminder_marks(bot, guild.id),
        "ping_mark": ping_mark,
        "stale_minutes": int(bot.store.get(guild.id, MARATHON_REMINDER_STALE_KEY)),
        "reminds_runs": following and mi.is_tracked(row),
        "reminds_hosts": following
        and host_posts_wanted(bot, guild, row)
        and public_reminders_wanted(bot, guild.id)
        and announces(bot, guild.id, row)
        and reminder_channel(bot, guild.id) is not None,
        "run_role": run_role,
        "block_role": block_role,
        "block_speaks": lambda block: bool(speaking(bot, guild, row, block)),
        "carries": lambda run, mark: baf.predicts(days, run, mark, speaks=speaks),
    }


def baf_event_of(bot: Any, guild: Any, row: Any, runs: Any) -> dict[str, Any]:
    """The marathon's BaF event answer; every page day takes it."""
    found = baf.judgement_of(reading_for(bot, guild.id, row, runs))
    return {"answer": found.answer, "reason": found.reason}


async def sheet(
    bot: Any, guild: Any, marathon_id: Any, *, now: datetime | None = None
) -> dict[str, Any]:
    db = bot.db
    now = now or datetime.now(UTC)
    row = await get_marathon(db, guild.id, marathon_id)
    archived = row is None
    if archived:
        row = await archived_marathon(db, guild.id, marathon_id)
        if row is None:
            raise Refused(404, "not_found", mt.NO_SUCH_MARATHON.format(given=str(marathon_id)[:40]))
    runs = await (archived_runs if archived else runs_of)(db, row["id"])
    twitch, youtube = await links_for(db)
    return page.payload(
        row,
        runs,
        now=now,
        tz_name=zone_of(bot, guild),
        writes=True,
        archived=archived,
        channel_login=await channel_login(bot, row),
        twitch=twitch,
        youtube=youtube,
        name_of=lambda user_id: resolve_one(guild, user_id)["display_name"],
        setup_minutes=setup_minutes(bot, guild.id),
        refresh_seconds=int(bot.store.get(guild.id, MARATHON_TRACKER_REFRESH_KEY)),
        actions=await recent_moves(db, guild.id, row["id"]),
        because_words=BECAUSE_WORDS,
        names=True,
        baf_event=baf_event_of(bot, guild, row, runs),
        **(
            {}
            if archived
            else reading_of(bot, guild, row, now) | posting_of(bot, guild, row, runs)
        ),
    )


def build_router(bot: Any) -> APIRouter:
    router = APIRouter(
        prefix="/api/marathons",
        tags=["marathons"],
        dependencies=[Depends(staff_dependency(bot))],
    )

    @router.get("/{marathon_id}/schedule")
    async def marathon_schedule(marathon_id: int) -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        return await sheet(bot, guild, marathon_id)

    return router
