from __future__ import annotations

import logging
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, Request

from ...chat import (
    BUILTIN_NAMES,
    CANNED,
    SLOTS,
    ChatError,
    add_line,
    answer_for,
    clean_name,
    clean_slot,
    clean_text,
    clean_triggers,
    create_intent,
    delete_intent,
    delete_line,
    get_intent,
    get_line,
    invalidate,
    lines_for,
    list_intents,
    read_triggers,
    seed_defaults,
    update_intent,
    update_line,
)
from ..auth import Refused, staff_dependency
from ..writes import (
    actor_for,
    note,
    reader_dependency,
    require_db,
    require_guild,
    writer_dependency,
)

log = logging.getLogger(__name__)

NO_SUCH_INTENT = (
    "Black Bloc has no chat intent **#{intent_id}** any more, so nothing was done. The Chat page "
    "lists the ones it has."
)
NO_SUCH_LINE = (
    "Black Bloc has no chat line **#{line_id}** any more, so nothing was done. Somebody may have "
    "removed it while this page was open."
)
BUILT_IN_STAYS = (
    "**{name}** is one of Black Bloc's own intents, so it cannot be deleted — turn it off instead "
    "and it will stop answering, or edit its triggers and lines to say something else."
)
BUILT_IN_KEEPS_ITS_NAME = (
    "**{name}** is one of Black Bloc's own intents and its name is what the bot looks it up by, "
    "so the name cannot change. Its triggers, its lines and its on/off switch all can."
)
NAME_TAKEN = (
    "This server already has an intent called **{name}**, so nothing was saved. Pick another name, "
    "or edit the one that is there."
)
TRY_NEEDS_TEXT = (
    "There is nothing to try yet, so nothing was worked out. Type the sentence somebody would say "
    "and send it again."
)
INTENT_MADE = "**{name}** is in. It will answer as soon as it has a line to say."
INTENT_SAVED = "**{name}** is saved."
INTENT_GONE = "**{name}** is gone. Nothing answers to those phrases any more."
LINE_ADDED = "That line is in — **{name}** may say it from now on."
LINE_SAVED = "That line is saved."
LINE_GONE = "That line is gone."


def _id(value: Any) -> str | None:
    return str(value) if value is not None else None


def line_row(row: Any) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "intent_id": str(row["intent_id"]),
        "text": str(row["text"]),
        "slot": str(row["slot"]),
        "enabled": bool(row["enabled"]),
        "created_by": _id(row["created_by"]),
        "updated_at": row["updated_at"],
    }


def intent_row(row: Any, lines: Any) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "name": str(row["name"]),
        "kind": str(row["kind"]),
        "enabled": bool(row["enabled"]),
        "sort": int(row["sort"]),
        "triggers": list(read_triggers(row["triggers"])),
        "builtin": str(row["name"]) in BUILTIN_NAMES,
        "created_by": _id(row["created_by"]),
        "updated_at": row["updated_at"],
        "lines": [line_row(one) for one in lines],
    }


def refused(exc: ChatError) -> Refused:
    return Refused(400, "chat_refused", str(exc))


def wanted_enabled(payload: dict[str, Any], key: str = "enabled") -> Any:
    given = payload.get(key)
    return None if given is None else bool(given)


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    reader = reader_dependency(bot)
    router = APIRouter(
        prefix="/api/chat", tags=["chat"], dependencies=[Depends(staff_dependency(bot))]
    )

    async def _shown(guild: Any, row: Any) -> dict[str, Any]:
        return intent_row(row, await lines_for(bot.db, row["id"]))

    async def _wanted_intent(guild: Any, intent_id: int) -> Any:
        row = await get_intent(bot.db, intent_id)
        if row is None or row["guild_id"] != guild.id:
            raise Refused(404, "no_such_intent", NO_SUCH_INTENT.format(intent_id=intent_id))
        return row

    async def _wanted_line(guild: Any, line_id: int) -> tuple[Any, Any]:
        row = await get_line(bot.db, line_id)
        owner = await get_intent(bot.db, row["intent_id"]) if row is not None else None
        if owner is None or owner["guild_id"] != guild.id:
            raise Refused(404, "no_such_line", NO_SUCH_LINE.format(line_id=line_id))
        return row, owner

    @router.get("/intents")
    async def chat_intents() -> dict[str, Any]:
        """A guild that has never been seeded is seeded here, so the page is never blank."""
        guild = require_guild(bot)
        require_db(bot)
        rows = await list_intents(bot.db, guild.id)
        if not rows:
            await seed_defaults(bot.db, guild.id)
            invalidate(bot, guild.id)
            rows = await list_intents(bot.db, guild.id)
        return {
            "intents": [await _shown(guild, row) for row in rows],
            "slots": list(SLOTS),
            "notes": [],
        }

    @router.post("/intents")
    async def chat_intent_create(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        try:
            name = clean_name(payload.get("name"))
            triggers = clean_triggers(payload.get("triggers"))
        except ChatError as exc:
            raise refused(exc) from exc
        try:
            intent_id = await create_intent(
                bot.db,
                guild.id,
                name,
                triggers,
                kind=CANNED,
                enabled=payload.get("enabled") is not False,
                sort=int(payload.get("sort") or 0),
                by=int(who["id"]),
            )
        except sqlite3.IntegrityError as exc:
            raise Refused(409, "name_taken", NAME_TAKEN.format(name=name)) from exc
        text = payload.get("text")
        if text:
            try:
                await add_line(bot.db, intent_id, clean_text(text), by=int(who["id"]))
            except ChatError as exc:
                raise refused(exc) from exc
        invalidate(bot, guild.id)
        await note(bot, guild, "web.chat.intent_created", who, details={"name": name})
        row = await get_intent(bot.db, intent_id)
        return {"intent": await _shown(guild, row), "message": INTENT_MADE.format(name=name)}

    @router.put("/intents/{intent_id}")
    async def chat_intent_edit(
        request: Request, intent_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await _wanted_intent(guild, intent_id)
        built_in = str(row["name"]) in BUILTIN_NAMES
        fields: dict[str, Any] = {}
        try:
            if payload.get("name") is not None and str(payload["name"]) != row["name"]:
                if built_in:
                    raise Refused(
                        409, "built_in", BUILT_IN_KEEPS_ITS_NAME.format(name=row["name"])
                    )
                fields["name"] = clean_name(payload["name"])
            if payload.get("triggers") is not None:
                fields["triggers"] = clean_triggers(payload["triggers"])
        except ChatError as exc:
            raise refused(exc) from exc
        enabled = wanted_enabled(payload)
        if enabled is not None:
            fields["enabled"] = enabled
        if payload.get("sort") is not None:
            fields["sort"] = int(payload["sort"])
        try:
            await update_intent(bot.db, intent_id, **fields)
        except sqlite3.IntegrityError as exc:
            raise Refused(
                409, "name_taken", NAME_TAKEN.format(name=fields.get("name"))
            ) from exc
        invalidate(bot, guild.id)
        await note(
            bot,
            guild,
            "web.chat.intent_edited",
            who,
            details={"intent_id": intent_id, "changed": sorted(fields)},
        )
        fresh = await get_intent(bot.db, intent_id)
        return {
            "intent": await _shown(guild, fresh),
            "message": INTENT_SAVED.format(name=fresh["name"]),
        }

    @router.delete("/intents/{intent_id}")
    async def chat_intent_delete(request: Request, intent_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await _wanted_intent(guild, intent_id)
        if str(row["name"]) in BUILTIN_NAMES:
            raise Refused(409, "built_in", BUILT_IN_STAYS.format(name=row["name"]))
        await delete_intent(bot.db, intent_id)
        invalidate(bot, guild.id)
        await note(
            bot, guild, "web.chat.intent_deleted", who, details={"name": str(row["name"])}
        )
        return {
            "removed": True,
            "intent_id": str(intent_id),
            "message": INTENT_GONE.format(name=row["name"]),
        }

    @router.post("/intents/{intent_id}/lines")
    async def chat_line_add(
        request: Request, intent_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await _wanted_intent(guild, intent_id)
        try:
            text = clean_text(payload.get("text"))
            slot = clean_slot(payload.get("slot"))
        except ChatError as exc:
            raise refused(exc) from exc
        line_id = await add_line(
            bot.db,
            intent_id,
            text,
            slot=slot,
            enabled=payload.get("enabled") is not False,
            by=int(who["id"]),
        )
        invalidate(bot, guild.id)
        await note(
            bot,
            guild,
            "web.chat.line_added",
            who,
            details={"intent_id": intent_id, "slot": slot},
        )
        return {
            "line": line_row(await get_line(bot.db, line_id)),
            "message": LINE_ADDED.format(name=row["name"]),
        }

    @router.put("/lines/{line_id}")
    async def chat_line_edit(
        request: Request, line_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        await _wanted_line(guild, line_id)
        fields: dict[str, Any] = {}
        try:
            if payload.get("text") is not None:
                fields["text"] = clean_text(payload["text"])
            if payload.get("slot") is not None:
                fields["slot"] = clean_slot(payload["slot"])
        except ChatError as exc:
            raise refused(exc) from exc
        enabled = wanted_enabled(payload)
        if enabled is not None:
            fields["enabled"] = enabled
        await update_line(bot.db, line_id, **fields)
        invalidate(bot, guild.id)
        await note(
            bot,
            guild,
            "web.chat.line_edited",
            who,
            details={"line_id": line_id, "changed": sorted(fields)},
        )
        return {"line": line_row(await get_line(bot.db, line_id)), "message": LINE_SAVED}

    @router.delete("/lines/{line_id}")
    async def chat_line_delete(request: Request, line_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row, owner = await _wanted_line(guild, line_id)
        await delete_line(bot.db, line_id)
        invalidate(bot, guild.id)
        await note(
            bot,
            guild,
            "web.chat.line_deleted",
            who,
            details={"intent_id": int(owner["id"]), "slot": str(row["slot"])},
        )
        return {"removed": True, "line_id": str(line_id), "message": LINE_GONE}

    @router.post("/try")
    async def chat_try(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        """A dry run: the real classifier and the real live data, and nothing is sent."""
        who = await reader(request)
        guild = require_guild(bot)
        require_db(bot)
        text = str(payload.get("text") or "").strip()
        if not text:
            raise Refused(400, "no_text", TRY_NEEDS_TEXT)
        answer = await answer_for(text, actor_for(bot, who, guild), bot, guild=guild)
        return {
            "intent": answer.intent,
            "kind": answer.kind,
            "slot": answer.slot,
            "line": answer.text,
        }

    return router


__all__ = ["build_router", "intent_row", "line_row"]
