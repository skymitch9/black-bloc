from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, Request

from ... import brackets_moves as moves
from ... import brackets_store, brackets_view
from ...brackets import access
from ...logkinds import VIA_WEBSITE
from ..auth import Refused
from ..writes import (
    TOO_MANY_WRITES,
    actor_for,
    bucket_for,
    member_gate,
    member_read_dependency,
    require_db,
    require_guild,
    wanted_id,
)

log = logging.getLogger(__name__)

OPTIONAL = Body(default=None)


def body_of(payload: Any) -> dict[str, Any]:
    return payload if isinstance(payload, dict) else {}


def build_router(bot: Any) -> APIRouter:
    reader = member_read_dependency(bot)
    signed_in = member_gate(bot)
    router = APIRouter(prefix="/api/brackets", tags=["brackets"])

    async def writer(request: Request) -> dict[str, Any]:
        who = await signed_in(request)
        if not bucket_for(bot).take(str(who["id"])):
            log.warning("api: rate-limited bracket writes from %s", who["id"])
            raise Refused(429, "slow_down", TOO_MANY_WRITES)
        return who

    def runs(guild: Any, who: dict[str, Any]) -> bool:
        return access.may_run(bot.store, guild, guild.get_member(int(who["id"])))

    async def shown(guild: Any, tournament_id: int, who: dict[str, Any]) -> dict[str, Any]:
        row = await brackets_store.tournament(bot.db, guild.id, tournament_id)
        if row is None:
            raise Refused(
                404,
                "no_tournament",
                moves.said(bot.store, guild.id, "brackets_no_tournament_said", id=tournament_id),
            )
        return await brackets_view.full(bot.db, row, viewer=int(who["id"]), runs=runs(guild, who))

    async def answered(
        request: Request, tournament_id: Any, move: Any, *args: Any, **words: Any
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(tournament_id) if tournament_id is not None else None
        actor = actor_for(bot, who, guild)
        given = (wanted,) if wanted is not None else ()
        outcome = await move(bot, guild, actor, *given, *args, via=VIA_WEBSITE, **words)
        if not outcome.ok:
            raise Refused(outcome.status or 400, outcome.code, outcome.message)
        return {
            "tournament": await shown(guild, int(outcome.value), who),
            "message": outcome.message,
        }

    @router.get("")
    async def brackets_index(request: Request) -> dict[str, Any]:
        who = await reader(request)
        guild = require_guild(bot)
        require_db(bot)
        rows = await brackets_store.tournaments(bot.db, guild.id)
        return {
            "mode": moves.mode_of(bot.store, guild.id),
            "may_run": runs(guild, who),
            "tournaments": [brackets_view.summary(row) for row in rows],
        }

    @router.get("/{tournament_id}")
    async def brackets_one(request: Request, tournament_id: str) -> dict[str, Any]:
        who = await reader(request)
        guild = require_guild(bot)
        require_db(bot)
        return await shown(guild, wanted_id(tournament_id), who)

    @router.post("")
    async def brackets_create(request: Request, payload: Any = OPTIONAL) -> dict[str, Any]:
        return await answered(request, None, moves.create, body_of(payload))

    @router.patch("/{tournament_id}")
    async def brackets_edit(
        request: Request, tournament_id: str, payload: Any = OPTIONAL
    ) -> dict[str, Any]:
        return await answered(request, tournament_id, moves.edit, body_of(payload))

    def plain(path: str, move: Any) -> None:
        async def route(request: Request, tournament_id: str) -> dict[str, Any]:
            return await answered(request, tournament_id, move)

        route.__name__ = f"brackets_{move.__name__}"
        router.add_api_route(path, route, methods=["POST"])

    plain("/{tournament_id}/signups/open", moves.open_signups)
    plain("/{tournament_id}/signups/close", moves.close_signups)
    plain("/{tournament_id}/checkin/open", moves.open_check_in)
    plain("/{tournament_id}/checkin/close", moves.close_check_in)
    plain("/{tournament_id}/join", moves.join)
    plain("/{tournament_id}/start", moves.start)
    plain("/{tournament_id}/unstart", moves.unstart)
    plain("/{tournament_id}/reopen", moves.reopen)
    plain("/{tournament_id}/cancel", moves.cancel)
    plain("/{tournament_id}/restore", moves.restore)

    @router.post("/{tournament_id}/complete")
    async def brackets_complete(
        request: Request, tournament_id: str, payload: Any = OPTIONAL
    ) -> dict[str, Any]:
        order = body_of(payload).get("order")
        return await answered(request, tournament_id, moves.complete, order=order)

    @router.post("/{tournament_id}/seed")
    async def brackets_seed(
        request: Request, tournament_id: str, payload: Any = OPTIONAL
    ) -> dict[str, Any]:
        given = body_of(payload)
        return await answered(
            request,
            tournament_id,
            moves.seed,
            order=given.get("order"),
            randomise=given.get("randomise") is True,
        )

    @router.post("/{tournament_id}/entrants")
    async def brackets_add(
        request: Request, tournament_id: str, payload: Any = OPTIONAL
    ) -> dict[str, Any]:
        given = body_of(payload)
        user = given.get("user_id")
        return await answered(
            request,
            tournament_id,
            moves.add_entrant,
            name=given.get("name"),
            user_id=wanted_id(user) if user not in (None, "") else None,
        )

    @router.delete("/{tournament_id}/entrants/{entrant_id}")
    async def brackets_remove(
        request: Request, tournament_id: str, entrant_id: str
    ) -> dict[str, Any]:
        return await answered(request, tournament_id, moves.remove_entrant, wanted_id(entrant_id))

    def entrant_move(path: str, move: Any) -> None:
        async def route(request: Request, tournament_id: str, entrant_id: str) -> dict[str, Any]:
            return await answered(request, tournament_id, move, wanted_id(entrant_id))

        route.__name__ = f"brackets_{move.__name__}"
        router.add_api_route(path, route, methods=["POST"])

    entrant_move("/{tournament_id}/entrants/{entrant_id}/restore", moves.restore_entrant)
    entrant_move("/{tournament_id}/entrants/{entrant_id}/drop", moves.drop)
    entrant_move("/{tournament_id}/entrants/{entrant_id}/dq", moves.dq)

    @router.post("/{tournament_id}/entrants/{entrant_id}/checkin")
    async def brackets_check_in(
        request: Request, tournament_id: str, entrant_id: str, payload: Any = OPTIONAL
    ) -> dict[str, Any]:
        wanted = body_of(payload).get("checked_in", True) is not False
        return await answered(
            request, tournament_id, moves.set_check_in, wanted_id(entrant_id), wanted
        )

    def set_move(path: str, move: Any) -> None:
        async def route(request: Request, tournament_id: str, key: str) -> dict[str, Any]:
            return await answered(request, tournament_id, move, key)

        route.__name__ = f"brackets_set_{move.__name__}"
        router.add_api_route(path, route, methods=["POST"])

    set_move("/{tournament_id}/sets/{key}/call", moves.call)
    set_move("/{tournament_id}/sets/{key}/confirm", moves.confirm)
    set_move("/{tournament_id}/sets/{key}/reset", moves.reset)

    @router.post("/{tournament_id}/sets/{key}/report")
    async def brackets_report(
        request: Request, tournament_id: str, key: str, payload: Any = OPTIONAL
    ) -> dict[str, Any]:
        given = body_of(payload)
        return await answered(
            request, tournament_id, moves.report, key, given.get("score_a"), given.get("score_b")
        )

    @router.post("/{tournament_id}/sets/{key}/dispute")
    async def brackets_dispute(
        request: Request, tournament_id: str, key: str, payload: Any = OPTIONAL
    ) -> dict[str, Any]:
        return await answered(
            request, tournament_id, moves.dispute, key, body_of(payload).get("note")
        )

    @router.post("/{tournament_id}/sets/{key}/override")
    async def brackets_override(
        request: Request, tournament_id: str, key: str, payload: Any = OPTIONAL
    ) -> dict[str, Any]:
        given = body_of(payload)
        return await answered(
            request,
            tournament_id,
            moves.override,
            key,
            score_a=given.get("score_a"),
            score_b=given.get("score_b"),
            winner=given.get("winner"),
            forfeit=given.get("forfeit") is True,
        )

    return router
