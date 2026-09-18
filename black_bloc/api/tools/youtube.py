from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ...cogs.content.youtube import (
    LinkRefused,
    all_links,
    counts,
    get_link,
    latest_video,
    link_channel,
    live_health,
    recent_videos,
    unlink_channel,
)
from ...logkinds import VIA_WEBSITE
from ..auth import Refused, staff_dependency
from ..names import resolve_one
from ..writes import (
    actor_for,
    require_cog,
    require_db,
    require_guild,
    wanted_id,
    writer_dependency,
)

log = logging.getLogger(__name__)

VIDEOS_DEFAULT_LIMIT = 50
VIDEOS_MAX_LIMIT = 200
COG = "YouTube"
FEATURE = "YouTube uploads"

NOT_LINKED = (
    "**{user_id}** has no YouTube channel linked, so there was nothing to unlink. The links "
    "table shows who has one."
)
NO_CHANNEL_GIVEN = (
    "No channel was given, so nothing was linked. Paste the channel address — the one that "
    "starts with youtube.com/channel/UC…, or the @handle."
)
LINKED = (
    "**{name}** is linked to {title}. The {count} video(s) already on the channel are counted "
    "as seen, so nothing already published is announced."
)
LINKED_NOT_SEEDED = (
    "**{name}** is linked to {title}, but YouTube's feed would not answer just now, so nothing "
    "has been counted as seen yet. The next sweep does it — until then no announcement is made."
)


def with_name(guild: Any, user_id: Any) -> dict[str, Any]:
    return {
        "user_id": str(user_id),
        "user_name": resolve_one(guild, user_id)["display_name"],
    }


def link_row(guild: Any, row: Any, latest: Any = None) -> dict[str, Any]:
    return with_name(guild, row["user_id"]) | {
        "channel_id": row["channel_id"],
        "handle": row["handle"],
        "title": row["title"],
        "linked_at": row["linked_at"],
        "seeded": bool(row["seeded"]),
        "last_video": (latest["title"] if latest is not None else None),
        "last_video_at": (latest["published_at"] if latest is not None else None),
    }


def video_row(guild: Any, row: Any) -> dict[str, Any]:
    return with_name(guild, row["user_id"]) | {
        "video_id": row["video_id"],
        "channel_id": row["channel_id"],
        "title": row["title"],
        "url": f"https://www.youtube.com/watch?v={row['video_id']}",
        "kind": row["kind"],
        "published_at": row["published_at"],
        "seen_at": row["seen_at"],
        "announced_at": row["announced_at"],
        "mode": row["mode"],
        "state": state_of(row),
        "announced_message_id": (
            str(row["announced_message_id"]) if row["announced_message_id"] else None
        ),
    }


def state_of(row: Any) -> str:
    """What actually happened to this video, in one word the table can colour."""
    if row["announced_at"] and row["mode"] == "on":
        return "announced"
    if row["announced_at"]:
        return "would"
    return "skipped"


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/youtube", tags=["youtube"], dependencies=[Depends(staff_dependency(bot))]
    )

    @router.get("/links")
    async def youtube_links() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        db = require_db(bot)
        return [
            link_row(guild, row, await latest_video(db, int(row["user_id"])))
            for row in await all_links(db)
        ]

    @router.post("/links")
    async def youtube_link(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        db = require_db(bot)
        require_cog(bot, COG, FEATURE)
        wanted = wanted_id(payload.get("member_id"))
        given = str(payload.get("channel") or "").strip()
        if not given:
            raise Refused(400, "bad_request", NO_CHANNEL_GIVEN)
        member = guild.get_member(wanted) or wanted
        try:
            _said, stored, counted = await link_channel(
                bot, guild, actor_for(bot, who, guild), member, given, via=VIA_WEBSITE
            )
        except LinkRefused as exc:
            raise Refused(exc.status, exc.code, str(exc)) from exc
        row = link_row(guild, stored if stored is not None else await get_link(db, wanted))
        said = LINKED if row["seeded"] else LINKED_NOT_SEEDED
        return row | {
            "message": said.format(
                name=row["user_name"] or wanted,
                title=row["title"] or row["channel_id"],
                count=counted,
            )
        }

    @router.delete("/links/{member_id}")
    async def youtube_unlink(request: Request, member_id: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        db = require_db(bot)
        wanted = wanted_id(member_id)
        if await get_link(db, wanted) is None:
            raise Refused(404, "not_linked", NOT_LINKED.format(user_id=wanted))
        member = guild.get_member(wanted) or wanted
        await unlink_channel(
            bot, guild, actor_for(bot, who, guild), member, via=VIA_WEBSITE
        )
        return {"unlinked": True, "user_id": str(wanted)}

    @router.get("/videos")
    async def youtube_videos(limit: int = VIDEOS_DEFAULT_LIMIT) -> list[dict[str, Any]]:
        guild = require_guild(bot)
        db = require_db(bot)
        wanted = max(1, min(int(limit), VIDEOS_MAX_LIMIT))
        return [video_row(guild, row) for row in await recent_videos(db, wanted)]

    @router.get("/status")
    async def youtube_status() -> dict[str, Any]:
        """The key, both sweeps' health and how many fetches came back unchanged."""
        db = require_db(bot)
        guild = require_guild(bot)
        cog = bot.get_cog(COG) if callable(getattr(bot, "get_cog", None)) else None
        totals = await counts(db)
        live = await live_health(bot, guild)
        live_loop = getattr(cog, "live_poller", None)
        fetches = int(getattr(cog, "fetches", 0) or 0)
        unchanged = int(getattr(cog, "unchanged", 0) or 0)
        return {
            "api_key_set": bool(getattr(getattr(cog, "client", None), "keyed", False)),
            "running": bool(cog is not None and cog.poller.is_running()),
            "last_ok_at": getattr(cog, "last_poll_ok_at", None),
            "last_error": getattr(cog, "last_poll_error", None),
            "failures": int(getattr(cog, "poll_failures", 0) or 0),
            "fetches": fetches,
            "unchanged": unchanged,
            "unchanged_ratio": round(unchanged / fetches, 3) if fetches else None,
            "links": totals["links"],
            "videos": totals["videos"],
            "announced": totals["announced"],
            "live_mode": live["mode"],
            "live_minutes": live["minutes"],
            "live_end_misses": live["misses"],
            "live_running": bool(live_loop is not None and live_loop.is_running()),
            "last_probe_at": live["last_probe_at"],
            "last_probe_error": live["last_probe_error"],
            "probed": live["probed"],
            "quota_today": live["quota"],
            "botcheck": live["botcheck"],
            "live_now": live["open"],
        }

    return router
