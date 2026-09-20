from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ...cogs.content.golive import (
    LINK_TAKEN,
    all_links,
    all_optouts,
    clean_login,
    get_link,
    link_channel,
    opt_in,
    opt_out,
    recent_sessions,
    unlink_channel,
)
from ...golive import (
    TWITCH,
    StreamInfo,
    author_line,
    display_name,
    embed_footer,
    ended_author,
    ended_footer,
    ended_render,
    render,
)
from ...logkinds import VIA_WEBSITE
from ..auth import Refused, staff_dependency
from ..names import resolve_one
from ..writes import (
    actor_for,
    require_db,
    require_guild,
    wanted_id,
    writer_dependency,
)

log = logging.getLogger(__name__)

SESSIONS_DEFAULT_LIMIT = 50
SESSIONS_MAX_LIMIT = 200

PREVIEW_STREAM = StreamInfo(
    url="https://www.twitch.tv/blackbloc",
    game="Celeste",
    title="Any% attempts",
    platform=TWITCH,
)
PREVIEW_DURATION = "2 h 10 min"
PREVIEW_SOURCE = "twitch"

NOT_LINKED = (
    "**{user_id}** has no Twitch account linked, so there was nothing to unlink. The links table "
    "shows who has one."
)
NOT_OPTED_OUT = (
    "**{user_id}** was not opted out, so there was nothing to undo. The opt-outs table lists "
    "everyone who is."
)
BAD_LOGIN = (
    "**{given}** is not a Twitch channel name Black Bloc can use, so nothing was linked. Give the "
    "name out of the channel's own address — letters, numbers and underscores, 25 at most."
)
LINKED = (
    "**{name}** is linked to twitch.tv/{login}. Black Bloc did not check that channel exists — it "
    "finds that out the first time it looks for a stream."
)
OPTED_OUT = "**{name}** is opted out, so no stream of theirs is announced from now on."
OPTED_IN = "**{name}** is no longer opted out, so their streams can be announced again."


def with_name(guild: Any, user_id: Any) -> dict[str, Any]:
    return {
        "user_id": str(user_id),
        "user_name": resolve_one(guild, user_id)["display_name"],
    }


def link_row(guild: Any, row: Any) -> dict[str, Any]:
    return with_name(guild, row["user_id"]) | {
        "twitch_login": row["twitch_login"],
        "twitch_user_id": row["twitch_user_id"],
        "linked_at": row["linked_at"],
    }


def session_row(guild: Any, row: Any) -> dict[str, Any]:
    return with_name(guild, row["user_id"]) | {
        "id": row["id"],
        "source": row["source"],
        "url": row["url"],
        "game": row["game"],
        "title": row["title"],
        "platform": row["platform"],
        "also_source": row["also_source"],
        "also_url": row["also_url"],
        "also_platform": row["also_platform"],
        "started_at": row["started_at"],
        "ended_at": row["ended_at"],
        "mode": row["mode"],
        "announced_message_id": (
            str(row["announced_message_id"]) if row["announced_message_id"] else None
        ),
    }


def preview_payload(bot: Any, guild: Any, actor: Any) -> dict[str, Any]:
    """Both wordings through the bot's own renderers, so the page carries no second copy."""
    store = bot.store
    name = display_name(actor)
    suffix = store.get(guild.id, "golive_end_suffix")
    live = render(
        store.get(guild.id, "golive_template"),
        PREVIEW_STREAM,
        actor,
        ping_role_id=store.get(guild.id, "golive_ping_role_id"),
    )
    return {
        "live": {"text": live, "author": author_line(name, PREVIEW_STREAM.platform)},
        "ended": {
            "text": ended_render(
                store.get(guild.id, "golive_end_template"),
                PREVIEW_STREAM,
                name,
                content=live,
                suffix=suffix,
                duration=PREVIEW_DURATION,
                keep_mention=bool(store.get(guild.id, "golive_end_keep_mention")),
            ),
            "author": ended_author(
                store.get(guild.id, "golive_end_author"),
                name,
                PREVIEW_STREAM.platform,
                duration=PREVIEW_DURATION,
            ),
            "footer": ended_footer(embed_footer(PREVIEW_SOURCE), suffix),
        },
    }


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    staff = staff_dependency(bot)
    router = APIRouter(
        prefix="/api/golive", tags=["golive"], dependencies=[Depends(staff_dependency(bot))]
    )

    @router.get("/preview")
    async def golive_preview(request: Request) -> dict[str, Any]:
        who = await staff(request)
        guild = require_guild(bot)
        return preview_payload(bot, guild, actor_for(bot, who, guild))

    @router.get("/links")
    async def golive_links() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        return [link_row(guild, row) for row in await all_links(bot.db)]

    @router.delete("/links/{user_id}")
    async def golive_unlink(request: Request, user_id: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(user_id)
        removed, _ = await unlink_channel(
            bot, guild, actor_for(bot, who, guild), wanted, via=VIA_WEBSITE
        )
        if not removed:
            raise Refused(404, "not_linked", NOT_LINKED.format(user_id=wanted))
        return {"unlinked": True, "user_id": str(wanted)}

    @router.post("/links")
    async def golive_link(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(payload.get("user_id"))
        given = str(payload.get("twitch_login") or "")
        outcome, _ = await link_channel(
            bot,
            guild,
            actor_for(bot, who, guild),
            wanted,
            given,
            helix=None,
            via=VIA_WEBSITE,
        )
        if outcome == "bad_login":
            raise Refused(400, "bad_login", BAD_LOGIN.format(given=given[:40] or "nothing"))
        if outcome == "taken":
            raise Refused(409, "link_taken", LINK_TAKEN.format(channel=clean_login(given)))
        row = link_row(guild, await get_link(bot.db, wanted))
        return row | {
            "checked": False,
            "message": LINKED.format(
                name=row["user_name"] or wanted, login=row["twitch_login"]
            ),
        }

    @router.get("/optouts")
    async def golive_optouts() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        return [
            with_name(guild, row["user_id"]) | {"at": row["at"]}
            for row in await all_optouts(bot.db)
        ]

    @router.post("/optouts")
    async def golive_opt_out(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(payload.get("user_id"))
        await opt_out(bot, guild, actor_for(bot, who, guild), wanted, via=VIA_WEBSITE)
        named = with_name(guild, wanted)
        return named | {
            "opted_out": True,
            "message": OPTED_OUT.format(name=named["user_name"] or wanted),
        }

    @router.delete("/optouts/{user_id}")
    async def golive_opt_in(request: Request, user_id: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(user_id)
        if not await opt_in(bot, guild, actor_for(bot, who, guild), wanted, via=VIA_WEBSITE):
            raise Refused(404, "not_opted_out", NOT_OPTED_OUT.format(user_id=wanted))
        named = with_name(guild, wanted)
        return named | {
            "opted_out": False,
            "message": OPTED_IN.format(name=named["user_name"] or wanted),
        }

    @router.get("/sessions")
    async def golive_sessions(limit: int = SESSIONS_DEFAULT_LIMIT) -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        wanted = max(1, min(int(limit), SESSIONS_MAX_LIMIT))
        return [
            session_row(guild, row) for row in await recent_sessions(bot.db, guild.id, wanted)
        ]

    return router
