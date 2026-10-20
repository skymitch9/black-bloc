from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from ... import questions as rules
from ... import questions_moves as moves
from ... import questions_rehearse as testing
from ... import questions_store as store
from ...logkinds import VIA_WEBSITE
from ..auth import Refused, staff_dependency
from ..writes import actor_for, require_db, require_guild, wanted_id, writer_dependency

DIRECTIONS = ("up", "down")
BAD_DIRECTION = "A question moves `up` or `down`, so nothing moved."


def question_row(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "position": int(row["position"]),
        "body": row["body"],
        "status": row["status"],
        "slot_at": row["slot_at"],
        "posted_by": row["posted_by"],
        "channel_id": str(row["channel_id"]) if row["channel_id"] else None,
        "message_id": str(row["message_id"]) if row["message_id"] else None,
        "added_by": str(row["added_by"]) if row["added_by"] else None,
        "added_at": row["added_at"],
        "resolved_at": row["resolved_at"],
    }


def message_url(guild: Any, row: Any) -> str | None:
    base = rules.channel_url(guild.id, row["channel_id"])
    return f"{base}/{int(row['message_id'])}" if base and row["message_id"] else None


async def index(bot: Any, guild: Any) -> dict[str, Any]:
    found = await moves.week(bot, guild)
    queued = await store.queued(bot.db, guild.id)
    history = await store.history(bot.db, guild.id)
    posted = found["posted"]
    shown = testing.this_weeks_question(found)
    home = testing.home_of(bot, guild)
    return {
        "mode": found["mode"],
        "slot_at": rules.slot_key(found["slot"]),
        "state": found["status"],
        "owner_set": rules.owner_of(bot.store, guild.id) is not None,
        "posted_id": int(posted["id"]) if posted is not None else None,
        "test_id": int(shown["id"]) if shown is not None else None,
        "test_home": str(home) if home else None,
        "queue": [question_row(row) for row in queued],
        "history": [question_row(row) | {"url": message_url(guild, row)} for row in history],
    }


async def current(bot: Any, guild: Any) -> dict[str, Any]:
    """What the owner-side task posts: nothing unless this week's slot is still waiting."""
    found = await moves.week(bot, guild)
    mode = found["mode"]
    question = found["question"] if found["status"] == rules.PENDING else None
    if mode == rules.OFF:
        question = None
    wanted = moves.target_id(bot, guild, mode)[0] if mode != rules.OFF else None
    return {
        "slot_at": rules.slot_key(found["slot"]),
        "state": found["status"],
        "question_id": int(question["id"]) if question is not None else None,
        "body": question["body"] if question is not None else None,
        "rendered": rules.rendered(bot.store, guild.id, question["body"]) if question else None,
        "channel_id": str(wanted) if wanted else None,
        "guild_id": str(guild.id),
        "channel_url": rules.channel_url(guild.id, wanted),
        "mode": mode,
    }


def answered(outcome: Any) -> dict[str, Any]:
    if not outcome.ok:
        raise Refused(outcome.status or 409, outcome.code or "refused", outcome.message)
    return {"ok": True, "message": outcome.message, "value": outcome.value}


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/questions", tags=["questions"], dependencies=[Depends(staff_dependency(bot))]
    )

    def ready() -> Any:
        guild = require_guild(bot)
        require_db(bot)
        return guild

    @router.get("")
    async def questions_index() -> dict[str, Any]:
        return await index(bot, ready())

    @router.get("/current")
    async def questions_current() -> dict[str, Any]:
        return await current(bot, ready())

    @router.post("")
    async def questions_add(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        outcome = await moves.add(
            bot, guild, actor_for(bot, who, guild), payload.get("text"), via=VIA_WEBSITE
        )
        return answered(outcome)

    @router.post("/post-now")
    async def questions_post_now(request: Request) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        outcome = await moves.post_now(bot, guild, actor_for(bot, who, guild), via=VIA_WEBSITE)
        return answered(outcome)

    @router.post("/rehearse")
    async def questions_rehearse(request: Request) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        outcome = await testing.rehearse(bot, guild, actor_for(bot, who, guild), via=VIA_WEBSITE)
        return answered(outcome)

    @router.post("/skip")
    async def questions_skip(request: Request) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        outcome = await moves.skip(bot, guild, actor_for(bot, who, guild), via=VIA_WEBSITE)
        return answered(outcome)

    @router.post("/unskip")
    async def questions_unskip(request: Request) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        outcome = await moves.unskip(bot, guild, actor_for(bot, who, guild), via=VIA_WEBSITE)
        return answered(outcome)

    @router.put("/{question_id}")
    async def questions_edit(
        request: Request, question_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        outcome = await moves.edit(
            bot,
            guild,
            actor_for(bot, who, guild),
            wanted_id(question_id),
            payload.get("body"),
            via=VIA_WEBSITE,
        )
        return answered(outcome)

    @router.delete("/{question_id}")
    async def questions_remove(request: Request, question_id: str) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        outcome = await moves.remove(
            bot, guild, actor_for(bot, who, guild), wanted_id(question_id), via=VIA_WEBSITE
        )
        return answered(outcome)

    @router.post("/{question_id}/move")
    async def questions_move(
        request: Request, question_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        direction = str(payload.get("direction") or "")
        if direction not in DIRECTIONS:
            raise Refused(400, "bad_direction", BAD_DIRECTION)
        outcome = await moves.move(
            bot,
            guild,
            actor_for(bot, who, guild),
            wanted_id(question_id),
            direction,
            via=VIA_WEBSITE,
        )
        return answered(outcome)

    @router.post("/{question_id}/requeue")
    async def questions_requeue(request: Request, question_id: str) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        outcome = await moves.requeue(
            bot, guild, actor_for(bot, who, guild), wanted_id(question_id), via=VIA_WEBSITE
        )
        return answered(outcome)

    @router.post("/{question_id}/take-down")
    async def questions_take_down(request: Request, question_id: str) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        outcome = await moves.take_down(
            bot, guild, actor_for(bot, who, guild), wanted_id(question_id), via=VIA_WEBSITE
        )
        return answered(outcome)

    return router
