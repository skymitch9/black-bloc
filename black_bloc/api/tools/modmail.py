from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ...cogs.moderation.modmail import (
    all_snippets,
    block_member,
    blocked_rows,
    close_ticket,
    drop_snippet,
    get_ticket,
    may_remove,
    put_snippet,
    resolve_place,
    send_reply,
    ticket_messages,
    tickets_by_status,
    unblock_member,
)
from ...events import clamp
from ...logkinds import VIA_WEBSITE
from ...modmail import CLOSED, OPEN, SOURCE_WEB, field_of, load_attachments
from ..auth import Refused, staff_dependency
from ..names import resolve_one
from ..writes import (
    actor_for,
    guard_of,
    refuse_guarded,
    require_db,
    require_guild,
    wanted_id,
    writer_dependency,
)

log = logging.getLogger(__name__)

TICKETS_LIMIT = 200
REPLY_LIMIT = 1900
REASON_LIMIT = 400
SNIPPET_LIMIT = 1900

NO_SUCH_TICKET = (
    "Black Bloc has no ticket **#{ticket_id}**, so nothing was done. The modmail page lists the "
    "ones it has."
)
TICKET_CLOSED = (
    "Ticket **#{ticket_id}** is closed already, so nothing was sent. Open tickets are the ones "
    "the member can still reply to."
)
NOTHING_TO_SEND = (
    "That reply was empty, so nothing was sent. Write something for the member to read."
)
UNKNOWN_STATUS = (
    "**{given}** is not a state a ticket can be in, so nothing was listed. They are {known}."
)
CLOSE_RACED = (
    "Ticket **#{ticket_id}** was closed by somebody else a moment ago, so nothing was done twice."
)
CLOSE_WOULD_DELETE = (
    "Closing that ticket would delete its channel, and Black Bloc is in **test mode** — so "
    "nothing was closed. Press **Close…** on the ticket's card in the test channel instead, or "
    "wait until the owner turns test mode off."
)
SNIPPET_NEEDS_BOTH = (
    "A snippet needs a short name and the text it stands for, so nothing was saved."
)
NO_SUCH_SNIPPET = (
    "Black Bloc has no snippet called **{name}**, so there was nothing to remove."
)
DM_FAILED = (
    "The member could not be sent that reply — their DMs are closed or they have left. It is "
    "saved on the ticket so staff can see it."
)


def ticket_row(guild: Any, row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": str(row["user_id"]),
        "user_name": resolve_one(guild, row["user_id"])["display_name"],
        "mode": row["mode"],
        "status": row["status"],
        "channel_id": str(row["channel_id"]) if row["channel_id"] else None,
        "thread_id": str(row["thread_id"]) if row["thread_id"] else None,
        "opened_at": row["opened_at"],
        "closed_at": row["closed_at"],
        "closed_by_id": str(row["closed_by"]) if row["closed_by"] else None,
        "closed_by_name": (
            resolve_one(guild, row["closed_by"])["display_name"] if row["closed_by"] else None
        ),
        "close_reason": row["close_reason"],
        "practice": bool(field_of(row, "practice", 0)),
    }


def message_row(guild: Any, row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "at": row["at"],
        "author_id": str(row["author_id"]),
        "author_name": resolve_one(guild, row["author_id"])["display_name"],
        "direction": row["direction"],
        "anonymous": bool(row["anonymous"]),
        "content": row["content"],
        "attachments": load_attachments(row["attachments"]),
        "delivered": bool(row["delivered"]),
    }


def snippet_row(guild: Any, row: Any) -> dict[str, Any]:
    return {
        "name": row["name"],
        "content": row["content"],
        "by_id": str(row["by"]) if row["by"] else None,
        "by_name": resolve_one(guild, row["by"])["display_name"] if row["by"] else None,
        "at": row["at"],
    }


def block_row(guild: Any, row: Any) -> dict[str, Any]:
    return {
        "user_id": str(row["user_id"]),
        "user_name": resolve_one(guild, row["user_id"])["display_name"],
        "by_id": str(row["by"]) if row["by"] else None,
        "by_name": resolve_one(guild, row["by"])["display_name"] if row["by"] else None,
        "reason": row["reason"],
        "at": row["at"],
    }


async def wanted_ticket(bot: Any, guild: Any, ticket_id: int, *, must_be_open: bool = False):
    row = await get_ticket(bot.db, ticket_id)
    if row is None or row["guild_id"] != guild.id:
        raise Refused(404, "no_such_ticket", NO_SUCH_TICKET.format(ticket_id=ticket_id))
    if must_be_open and row["status"] != OPEN:
        raise Refused(409, "ticket_closed", TICKET_CLOSED.format(ticket_id=ticket_id))
    return row


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/modmail", tags=["modmail"], dependencies=[Depends(staff_dependency(bot))]
    )

    @router.get("/tickets")
    async def modmail_tickets(status: str = "") -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        wanted = str(status or "").strip()
        if wanted and wanted not in (OPEN, CLOSED):
            raise Refused(
                400,
                "unknown_status",
                UNKNOWN_STATUS.format(given=wanted, known=f"{OPEN}, {CLOSED}"),
            )
        rows = await tickets_by_status(bot.db, guild.id, wanted or None, TICKETS_LIMIT)
        return [ticket_row(guild, row) for row in rows]

    @router.get("/tickets/{ticket_id}")
    async def modmail_ticket(ticket_id: int) -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        row = await wanted_ticket(bot, guild, ticket_id)
        messages = await ticket_messages(bot.db, ticket_id)
        return ticket_row(guild, row) | {
            "messages": [message_row(guild, message) for message in messages]
        }

    @router.post("/tickets/{ticket_id}/reply")
    async def modmail_reply(
        request: Request, ticket_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await wanted_ticket(bot, guild, ticket_id, must_be_open=True)
        text = clamp(payload.get("text"), REPLY_LIMIT)
        if not text:
            raise Refused(400, "nothing_to_send", NOTHING_TO_SEND)
        anonymous = bool(payload.get("anonymous"))
        why_not = await send_reply(
            bot,
            guild,
            row,
            actor_for(bot, who, guild),
            text,
            anonymous=anonymous,
            via=VIA_WEBSITE,
            source=SOURCE_WEB,
        )
        return {
            "sent": why_not is None,
            "ticket_id": ticket_id,
            "message": DM_FAILED if why_not else "Sent.",
        }

    @router.post("/tickets/{ticket_id}/close")
    async def modmail_close(
        request: Request, ticket_id: int, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await wanted_ticket(bot, guild, ticket_id, must_be_open=True)
        body = payload or {}
        reason = clamp(body.get("reason"), REASON_LIMIT) or None
        silent = bool(body.get("silent"))
        if guard_of(bot) is not None:
            place, _ = await resolve_place(bot, guild, row)
            if place is not None and not may_remove(bot, place):
                refuse_guarded(CLOSE_WOULD_DELETE)
        closed, why_not = await close_ticket(
            bot,
            guild,
            row,
            by=actor_for(bot, who, guild),
            reason=reason,
            silent=silent,
            via=VIA_WEBSITE,
        )
        if not closed:
            raise Refused(409, "close_raced", CLOSE_RACED.format(ticket_id=ticket_id))
        fresh = await get_ticket(bot.db, ticket_id)
        return {
            "closed": True,
            "ticket": ticket_row(guild, fresh),
            "transcript": why_not is None,
        }

    @router.get("/snippets")
    async def modmail_snippets() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        return [snippet_row(guild, row) for row in await all_snippets(bot.db)]

    @router.post("/snippets")
    async def modmail_snippet_save(
        request: Request, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        name = str(payload.get("name") or "").strip().lower()
        content = clamp(payload.get("content"), SNIPPET_LIMIT)
        if not name or not content:
            raise Refused(400, "bad_request", SNIPPET_NEEDS_BOTH)
        outcome = await put_snippet(
            bot,
            guild,
            actor_for(bot, who, guild),
            name,
            content,
            overwrite=True,
            via=VIA_WEBSITE,
        )
        if not outcome.ok:
            raise Refused(outcome.status, outcome.code, outcome.message)
        return {"saved": True, "name": name, "content": content}

    @router.delete("/snippets/{name}")
    async def modmail_snippet_remove(request: Request, name: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = str(name or "").strip().lower()
        outcome = await drop_snippet(
            bot, guild, actor_for(bot, who, guild), wanted, via=VIA_WEBSITE
        )
        if not outcome.ok:
            raise Refused(404, "no_such_snippet", NO_SUCH_SNIPPET.format(name=wanted))
        return {"removed": True, "name": wanted}

    @router.get("/blocks")
    async def modmail_blocks() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        return [block_row(guild, row) for row in await blocked_rows(bot.db)]

    @router.post("/blocks")
    async def modmail_block(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        user_id = wanted_id(payload.get("user_id"))
        reason = clamp(payload.get("reason"), REASON_LIMIT) or None
        await block_member(
            bot, guild, actor_for(bot, who, guild), user_id, reason, via=VIA_WEBSITE
        )
        return {"blocked": True, "user_id": str(user_id)}

    @router.delete("/blocks/{user_id}")
    async def modmail_unblock(request: Request, user_id: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(user_id)
        await unblock_member(bot, guild, actor_for(bot, who, guild), wanted, via=VIA_WEBSITE)
        return {"unblocked": True, "user_id": str(wanted)}

    return router
