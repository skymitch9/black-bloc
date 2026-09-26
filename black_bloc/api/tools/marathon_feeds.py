from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from ... import marathon_feeds as mf
from ...cogs.content.marathon_events import default_mode
from ...cogs.content.marathon_feeds import (
    channel_rows,
    channel_word,
    check_now,
    create_feed,
    dismiss_suggestion,
    forget_ignored,
    get_feed,
    hours_of,
    list_feeds,
    look_again,
    marathons_of_feed,
    remove_feed,
    set_feed,
    take_suggestion,
)
from ...cogs.content.spotlight import channel_by_id
from ...logkinds import VIA_WEBSITE
from ...marathon_channels import takes_marathons
from ...marathon_events import MODE_WORDS, clean_mode
from ...settings_store import MARATHON_FEED_ACTION_KEY, MARATHON_FEEDS_KEY
from ..auth import Refused, staff_dependency
from ..writes import actor_for, require_cog, require_db, require_guild, wanted_id, writer_dependency
from .marathons import COG, FEATURE, answered

TROUBLE = "could not be checked since {when} — {why}"


def suggestion_row(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "ref": str(record.get("ref")),
        "name": record.get("name"),
        "starts_at": record.get("starts_at"),
        "url": record.get("url"),
        "found_at": record.get("found_at"),
        "dismissed_at": record.get("dismissed_at"),
    }


async def feed_row(bot: Any, guild: Any, feed: Any) -> dict[str, Any]:
    channel = await channel_by_id(bot.db, int(feed["spotlight_id"]))
    made = await marathons_of_feed(bot.db, feed["id"])
    ignored = mf.ignored_of(feed)
    failed = feed["last_ok"] is not None and not int(feed["last_ok"])
    return {
        "id": feed["id"],
        "name": feed["name"],
        "source": mf.pick_for(feed),
        "source_word": mf.source_word(feed),
        "feed_ref": feed["feed_ref"],
        "spotlight_id": feed["spotlight_id"],
        "channel_login": channel["twitch_login"] if channel is not None else None,
        "channel_name": channel_word(channel),
        "action": feed["action"],
        "event_mode": clean_mode(feed["event_mode"]),
        "event_mode_effective": clean_mode(feed["event_mode"]) or default_mode(bot, guild.id),
        "event_mode_word": MODE_WORDS[
            clean_mode(feed["event_mode"]) or default_mode(bot, guild.id)
        ],
        "held_by_channel": bool(feed["held_by_channel"]),
        "active": bool(feed["active"]),
        "hours": hours_of(bot, guild.id),
        "last_checked_at": feed["last_checked_at"],
        "last_ok": None if feed["last_ok"] is None else bool(feed["last_ok"]),
        "last_error": feed["last_error"],
        "checks_failed": int(feed["checks_failed"] or 0),
        "trouble": (
            TROUBLE.format(when=feed["last_checked_at"] or "", why=feed["last_error"] or "")
            if failed
            else None
        ),
        "ignored": ignored,
        "ignored_count": len(ignored),
        "seen_count": len(mf.seen_of(feed)),
        "suggestions": [suggestion_row(one) for one in mf.open_suggestions(feed)],
        "dismissed": [suggestion_row(one) for one in mf.dismissed_of(feed)],
        "marathons": [
            {"id": one["id"], "name": one["name"], "starts_at": one["starts_at"]} for one in made
        ],
    }


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/marathons/feeds",
        tags=["marathons"],
        dependencies=[Depends(staff_dependency(bot))],
    )

    async def wanted(guild: Any, feed_id: Any) -> Any:
        row = await get_feed(bot.db, guild.id, feed_id)
        if row is None:
            raise Refused(404, "not_found", mf.NO_SUCH_FEED.format(given=str(feed_id)[:40]))
        return row

    async def after(guild: Any, feed_id: Any, message: str) -> dict[str, Any]:
        return await feed_row(bot, guild, await wanted(guild, feed_id)) | {"message": message}

    def writable() -> Any:
        guild = require_guild(bot)
        require_db(bot)
        require_cog(bot, COG, FEATURE)
        return guild

    @router.get("")
    async def feed_list() -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        rows = await list_feeds(bot.db, guild.id)
        taken = {int(one["spotlight_id"]): one["name"] for one in rows}
        return {
            "enabled": bool(bot.store.get(guild.id, MARATHON_FEEDS_KEY)),
            "hours": hours_of(bot, guild.id),
            "action_default": bot.store.get(guild.id, MARATHON_FEED_ACTION_KEY),
            "feeds": [await feed_row(bot, guild, one) for one in rows],
            "channels": [
                {
                    "id": one["id"],
                    "login": one["twitch_login"],
                    "name": channel_word(one),
                    "feed_name": taken.get(int(one["id"])),
                    "marathons": takes_marathons(one),
                }
                for one in await channel_rows(bot.db, guild.id)
            ],
            "sources": [
                {"value": key, "label": mf.PICK_WORDS[key]} for key in mf.PICKS
            ],
        }

    @router.post("")
    async def feed_create(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = writable()
        made = answered(
            await create_feed(
                bot,
                guild,
                actor_for(bot, who, guild),
                spotlight_id=payload.get("spotlight_id"),
                pick=payload.get("source"),
                slug=payload.get("slug"),
                name=payload.get("name"),
                action=payload.get("action") or None,
                via=VIA_WEBSITE,
            )
        )
        return await after(guild, made.value["id"], made.message)

    @router.patch("/{feed_id}")
    async def feed_patch(request: Request, feed_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = writable()
        row = await wanted(guild, feed_id)
        actor = actor_for(bot, who, guild)
        said: list[str] = []
        if "active" in payload and not isinstance(payload["active"], bool):
            raise Refused(422, "bad_active", mf.BAD_ACTIVE)
        if "action" in payload and payload["action"] not in mf.ACTIONS:
            raise Refused(422, "bad_action", mf.BAD_ACTION)
        if {"active", "action", "name", "spotlight_id", "event_mode"} & set(payload):
            given = payload.get("spotlight_id")
            done = answered(
                await set_feed(
                    bot,
                    guild,
                    actor,
                    row,
                    active=payload.get("active"),
                    action=payload.get("action"),
                    name=payload.get("name") if "name" in payload else None,
                    spotlight_id=wanted_id(given) if given not in (None, "") else None,
                    event_mode=payload["event_mode"] or "" if "event_mode" in payload else None,
                    via=VIA_WEBSITE,
                )
            )
            said.append(done.message)
        if "dismiss" in payload:
            if payload["dismiss"] in (None, ""):
                raise Refused(422, "bad_ref", mf.BAD_REF)
            done = answered(
                await dismiss_suggestion(
                    bot, guild, actor, row, str(payload["dismiss"]), via=VIA_WEBSITE
                )
            )
            said.append(done.message)
        return await after(guild, feed_id, " ".join(one for one in said if one))

    @router.delete("/{feed_id}")
    async def feed_delete(request: Request, feed_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = writable()
        row = await wanted(guild, feed_id)
        done = answered(
            await remove_feed(bot, guild, actor_for(bot, who, guild), row, via=VIA_WEBSITE)
        )
        return {"removed": True, "id": feed_id, "message": done.message}

    async def step(request: Request, feed_id: int, shared: Any) -> dict[str, Any]:
        who = await writer(request)
        guild = writable()
        row = await wanted(guild, feed_id)
        done = answered(
            await shared(bot, guild, actor_for(bot, who, guild), row, via=VIA_WEBSITE)
        )
        return await after(guild, feed_id, done.message)

    @router.post("/{feed_id}/check")
    async def feed_check(request: Request, feed_id: int) -> dict[str, Any]:
        return await step(request, feed_id, check_now)

    @router.post("/{feed_id}/look")
    async def feed_look(request: Request, feed_id: int) -> dict[str, Any]:
        return await step(request, feed_id, look_again)

    @router.post("/{feed_id}/forget")
    async def feed_forget(request: Request, feed_id: int) -> dict[str, Any]:
        return await step(request, feed_id, forget_ignored)

    @router.post("/{feed_id}/add")
    async def feed_take(request: Request, feed_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = writable()
        row = await wanted(guild, feed_id)
        ref = payload.get("event_ref")
        if ref in (None, ""):
            raise Refused(422, "bad_ref", mf.BAD_REF)
        done = answered(
            await take_suggestion(
                bot, guild, actor_for(bot, who, guild), row, str(ref), via=VIA_WEBSITE
            )
        )
        return await after(guild, feed_id, done.message) | {"marathon_id": done.value["id"]}

    return router
