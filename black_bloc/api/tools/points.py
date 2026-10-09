from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, Request

from ... import points_moves as moves
from ... import points_store, points_view
from ...brackets.access import is_staff
from ...logkinds import VIA_WEBSITE
from ...points.model import STATES
from ..auth import Refused
from ..names import site_words
from ..writes import (
    TOO_MANY_WRITES,
    actor_for,
    bucket_for,
    member_dependency,
    member_gate,
    member_read_dependency,
    require_db,
    require_guild,
    wanted_id,
    writer_dependency,
)

log = logging.getLogger(__name__)

OPTIONAL = Body(default=None)


def body_of(payload: Any) -> dict[str, Any]:
    return payload if isinstance(payload, dict) else {}


def build_router(bot: Any) -> APIRouter:
    reader = member_read_dependency(bot)
    member_writer = member_dependency(bot)
    signed_in = member_gate(bot)
    staff_writer = writer_dependency(bot)
    router = APIRouter(prefix="/api/points", tags=["points"])

    async def decider(request: Request) -> dict[str, Any]:
        who = await signed_in(request)
        if not bucket_for(bot).take(str(who["id"])):
            log.warning("api: rate-limited run decisions from %s", who["id"])
            raise Refused(429, "slow_down", TOO_MANY_WRITES)
        return who

    def roles_of(guild: Any, who: dict[str, Any]) -> tuple[bool, bool]:
        person = guild.get_member(int(who["id"]))
        return moves.may_verify(bot.store, guild, person), is_staff(bot.store, person)

    def place() -> Any:
        guild = require_guild(bot)
        require_db(bot)
        return guild

    def refused(guild: Any, outcome: Any) -> Refused:
        return Refused(outcome.status or 400, outcome.code, site_words(guild, outcome.message))

    async def run_answer(guild: Any, outcome: Any) -> dict[str, Any]:
        if not outcome.ok:
            raise refused(guild, outcome)
        row = await points_store.run(bot.db, guild.id, outcome.value.id)
        return {
            "run": points_view.run_row(bot.store, guild, row),
            "message": site_words(guild, outcome.message),
            "changed": list(outcome.changed),
            "announce": list(outcome.value.announce),
        }

    async def bounty_answer(guild: Any, outcome: Any) -> dict[str, Any]:
        if not outcome.ok:
            raise refused(guild, outcome)
        found = await points_view.bounties(bot, guild)
        row = next(one for one in found if one["id"] == outcome.value.id)
        return {"bounty": row, "message": site_words(guild, outcome.message)}

    @router.get("")
    async def points_index(request: Request, by: str | None = None) -> dict[str, Any]:
        who = await reader(request)
        guild = place()
        verifier, staff = roles_of(guild, who)
        return await points_view.index(
            bot, guild, int(who["id"]), by=by, verifier=verifier, staff=staff
        )

    @router.get("/board")
    async def points_board(request: Request, by: str | None = None) -> dict[str, Any]:
        await reader(request)
        return await points_view.full_board(bot, place(), by=by)

    @router.get("/me")
    async def points_me(request: Request) -> dict[str, Any]:
        who = await reader(request)
        return await points_view.next_rank_of(bot, place(), int(who["id"]))

    @router.get("/runs")
    async def points_runs(
        request: Request, state: str | None = None, user_id: str | None = None
    ) -> dict[str, Any]:
        who = await reader(request)
        guild = place()
        verifier, _ = roles_of(guild, who)
        wanted = wanted_id(user_id) if user_id else None
        if wanted is None and not verifier:
            wanted = int(who["id"])
        if not verifier and wanted != int(who["id"]):
            raise Refused(
                403,
                "not_verifier",
                moves.said(
                    bot.store,
                    guild.id,
                    "points_not_verifier_said",
                    role=moves.role_words(bot, guild),
                ),
            )
        if state is not None and state not in STATES:
            state = None
        rows = await points_store.runs(bot.db, guild.id, state=state, user_id=wanted)
        return {
            "state": state,
            "user_id": str(wanted) if wanted is not None else None,
            "runs": [points_view.run_row(bot.store, guild, row) for row in rows],
        }

    @router.post("/runs")
    async def points_submit(request: Request, payload: Any = OPTIONAL) -> dict[str, Any]:
        who = await member_writer(request)
        guild = place()
        outcome = await moves.submit(
            bot, guild, actor_for(bot, who, guild), body_of(payload), via=VIA_WEBSITE
        )
        return await run_answer(guild, outcome)

    @router.post("/runs/{run_id}/approve")
    async def points_approve(request: Request, run_id: str) -> dict[str, Any]:
        who = await decider(request)
        guild = place()
        outcome = await moves.approve(
            bot, guild, actor_for(bot, who, guild), wanted_id(run_id), via=VIA_WEBSITE
        )
        return await run_answer(guild, outcome)

    @router.post("/runs/{run_id}/reject")
    async def points_reject(
        request: Request, run_id: str, payload: Any = OPTIONAL
    ) -> dict[str, Any]:
        who = await decider(request)
        guild = place()
        outcome = await moves.reject(
            bot,
            guild,
            actor_for(bot, who, guild),
            wanted_id(run_id),
            body_of(payload).get("reason"),
            via=VIA_WEBSITE,
        )
        return await run_answer(guild, outcome)

    @router.post("/runs/{run_id}/remove")
    async def points_remove(
        request: Request, run_id: str, payload: Any = OPTIONAL
    ) -> dict[str, Any]:
        who = await staff_writer(request)
        guild = place()
        outcome = await moves.remove(
            bot,
            guild,
            actor_for(bot, who, guild),
            wanted_id(run_id),
            body_of(payload).get("reason"),
            via=VIA_WEBSITE,
        )
        return await run_answer(guild, outcome)

    @router.patch("/runs/{run_id}")
    async def points_edit(request: Request, run_id: str, payload: Any = OPTIONAL) -> dict[str, Any]:
        who = await staff_writer(request)
        guild = place()
        outcome = await moves.edit(
            bot,
            guild,
            actor_for(bot, who, guild),
            wanted_id(run_id),
            body_of(payload),
            via=VIA_WEBSITE,
        )
        return await run_answer(guild, outcome)

    @router.post("/recompute")
    async def points_recompute(request: Request) -> dict[str, Any]:
        who = await staff_writer(request)
        guild = place()
        outcome = await moves.recompute(bot, guild, actor_for(bot, who, guild), via=VIA_WEBSITE)
        if not outcome.ok:
            raise refused(guild, outcome)
        return {
            "message": site_words(guild, outcome.message),
            "changed": list(outcome.changed),
            "announce": list(outcome.value.announce),
        }

    @router.get("/bounties")
    async def points_bounties(request: Request) -> dict[str, Any]:
        await reader(request)
        return {"bounties": await points_view.bounties(bot, place())}

    @router.post("/bounties")
    async def points_bounty_create(request: Request, payload: Any = OPTIONAL) -> dict[str, Any]:
        who = await staff_writer(request)
        guild = place()
        outcome = await moves.bounty_create(
            bot, guild, actor_for(bot, who, guild), body_of(payload), via=VIA_WEBSITE
        )
        return await bounty_answer(guild, outcome)

    @router.patch("/bounties/{bounty_id}")
    async def points_bounty_edit(
        request: Request, bounty_id: str, payload: Any = OPTIONAL
    ) -> dict[str, Any]:
        who = await staff_writer(request)
        guild = place()
        outcome = await moves.bounty_edit(
            bot,
            guild,
            actor_for(bot, who, guild),
            wanted_id(bounty_id),
            body_of(payload),
            via=VIA_WEBSITE,
        )
        return await bounty_answer(guild, outcome)

    @router.post("/bounties/{bounty_id}/end")
    async def points_bounty_end(request: Request, bounty_id: str) -> dict[str, Any]:
        who = await staff_writer(request)
        guild = place()
        outcome = await moves.bounty_end(
            bot, guild, actor_for(bot, who, guild), wanted_id(bounty_id), via=VIA_WEBSITE
        )
        return await bounty_answer(guild, outcome)

    return router
