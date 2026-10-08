from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Body, Request

from ... import brackets_cards, brackets_store, brackets_thread, brackets_view
from ... import brackets_moves as moves
from ... import brackets_people as people
from ... import brackets_sets as sets
from ...brackets import access
from ...logkinds import VIA_WEBSITE
from ..auth import Refused
from ..names import site_words
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

FOLLOW_GRACE_SECONDS = 1.5
REASON_LIMIT = 300
ENTRANT_DMS = {
    "remove_entrant": "brackets_dm_removed",
    "dq": "brackets_dm_dq",
    "drop": "brackets_dm_dropped",
}


def body_of(payload: Any) -> dict[str, Any]:
    return payload if isinstance(payload, dict) else {}


def reason_of(payload: Any) -> str:
    return " ".join(str(body_of(payload).get("reason") or "").split())[:REASON_LIMIT]


def name_of(guild: Any, user_id: Any) -> str | None:
    if user_id is None:
        return None
    member = guild.get_member(int(user_id)) if hasattr(guild, "get_member") else None
    return str(getattr(member, "display_name", None) or getattr(member, "name", "")) or None


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
        found = await brackets_view.full(bot.db, row, viewer=int(who["id"]), runs=runs(guild, who))
        return found | {"to_name": name_of(guild, row["to_user_id"])}

    async def players(guild: Any, tournament_id: Any, key: str) -> list[int]:
        row = await brackets_store.tournament(bot.db, guild.id, wanted_id(tournament_id))
        current = await brackets_store.bracket(bot.db, row) if row is not None else None
        match = current.matches.get(str(key)) if current is not None else None
        if match is None:
            return []
        people = {one["id"]: one for one in await brackets_store.entrants(bot.db, row["id"])}
        return brackets_cards.player_ids(match, people)

    def told_entrant(tournament_id: Any, entrant_id: int, move: Any, reason: str) -> Any:
        async def after(guild: Any, actor: Any, outcome: Any, held: Any) -> None:
            wanted = wanted_id(tournament_id)
            person = await brackets_store.entrant(bot.db, wanted, entrant_id)
            row = await brackets_store.tournament(bot.db, guild.id, wanted)
            if person is None or row is None:
                return
            await brackets_thread.tell(
                bot,
                guild,
                row,
                person["user_id"],
                ENTRANT_DMS[move.__name__],
                reason,
                actor=actor,
            )

        return after

    def told_players(tournament_id: Any, key: str, dm: str, reason: str) -> tuple[Any, Any]:
        async def before(guild: Any) -> list[int]:
            return await players(guild, tournament_id, key)

        async def after(guild: Any, actor: Any, outcome: Any, held: Any) -> None:
            row = await brackets_store.tournament(bot.db, guild.id, wanted_id(tournament_id))
            fields = {"result": outcome.message} if dm == "brackets_dm_decided" else {}
            for user_id in held or []:
                await brackets_thread.tell(
                    bot, guild, row, user_id, dm, reason, actor=actor, set=key, **fields
                )

        return before, after

    async def answered(
        request: Request,
        tournament_id: Any,
        move: Any,
        *args: Any,
        before: Any = None,
        after: Any = None,
        **words: Any,
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(tournament_id) if tournament_id is not None else None
        actor = actor_for(bot, who, guild)
        given = (wanted,) if wanted is not None else ()
        held = await before(guild) if before is not None else None
        outcome = await move(bot, guild, actor, *given, *args, via=VIA_WEBSITE, **words)
        if not outcome.ok:
            raise Refused(outcome.status or 400, outcome.code, site_words(guild, outcome.message))
        if after is not None:
            await after(guild, actor, outcome, held)
        following = brackets_thread.follow_later(
            bot, guild, outcome.value, outcome, move=getattr(move, "__name__", None)
        )
        if following is not None:
            await asyncio.wait({following}, timeout=FOLLOW_GRACE_SECONDS)
        return {
            "tournament": await shown(guild, int(outcome.value), who),
            "message": site_words(guild, outcome.message),
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
            "words": brackets_view.page_words(bot.store, guild.id),
            "defaults": brackets_view.page_defaults(moves.option_defaults(bot.store, guild.id)),
            "tournaments": [
                brackets_view.summary(row) | {"to_name": name_of(guild, row["to_user_id"])}
                for row in rows
            ],
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
    plain("/{tournament_id}/checkin/open", people.open_check_in)
    plain("/{tournament_id}/checkin/close", people.close_check_in)
    plain("/{tournament_id}/join", people.join)
    plain("/{tournament_id}/start", moves.start)
    plain("/{tournament_id}/unstart", moves.unstart)
    plain("/{tournament_id}/reopen", moves.reopen)
    plain("/{tournament_id}/cancel", moves.cancel)
    plain("/{tournament_id}/restore", moves.restore)
    plain("/{tournament_id}/move", brackets_thread.move_home)
    plain("/{tournament_id}/unadvance", moves.unadvance)

    @router.post("/{tournament_id}/advance")
    async def brackets_advance(
        request: Request, tournament_id: str, payload: Any = OPTIONAL
    ) -> dict[str, Any]:
        order = body_of(payload).get("order")
        return await answered(request, tournament_id, moves.advance, order=order)

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
            people.add_entrant,
            name=given.get("name"),
            user_id=wanted_id(user) if user not in (None, "") else None,
        )

    @router.delete("/{tournament_id}/entrants/{entrant_id}")
    async def brackets_remove(
        request: Request, tournament_id: str, entrant_id: str, payload: Any = OPTIONAL
    ) -> dict[str, Any]:
        entrant = wanted_id(entrant_id)
        return await answered(
            request,
            tournament_id,
            people.remove_entrant,
            entrant,
            after=told_entrant(tournament_id, entrant, people.remove_entrant, reason_of(payload)),
        )

    def entrant_move(path: str, move: Any, *, tells: bool = False) -> None:
        async def route(
            request: Request, tournament_id: str, entrant_id: str, payload: Any = OPTIONAL
        ) -> dict[str, Any]:
            entrant = wanted_id(entrant_id)
            reason = reason_of(payload)
            after = told_entrant(tournament_id, entrant, move, reason) if tells else None
            return await answered(request, tournament_id, move, entrant, after=after)

        route.__name__ = f"brackets_{move.__name__}"
        router.add_api_route(path, route, methods=["POST"])

    entrant_move("/{tournament_id}/entrants/{entrant_id}/restore", people.restore_entrant)
    entrant_move("/{tournament_id}/entrants/{entrant_id}/drop", people.drop, tells=True)
    entrant_move("/{tournament_id}/entrants/{entrant_id}/dq", people.dq, tells=True)

    @router.post("/{tournament_id}/entrants/{entrant_id}/checkin")
    async def brackets_check_in(
        request: Request, tournament_id: str, entrant_id: str, payload: Any = OPTIONAL
    ) -> dict[str, Any]:
        wanted = body_of(payload).get("checked_in", True) is not False
        return await answered(
            request, tournament_id, people.set_check_in, wanted_id(entrant_id), wanted
        )

    def set_move(path: str, move: Any) -> None:
        async def route(request: Request, tournament_id: str, key: str) -> dict[str, Any]:
            return await answered(request, tournament_id, move, key)

        route.__name__ = f"brackets_set_{move.__name__}"
        router.add_api_route(path, route, methods=["POST"])

    set_move("/{tournament_id}/sets/{key}/call", sets.call)
    set_move("/{tournament_id}/sets/{key}/confirm", sets.confirm_report)

    @router.post("/{tournament_id}/sets/{key}/reset")
    async def brackets_set_reset(
        request: Request, tournament_id: str, key: str, payload: Any = OPTIONAL
    ) -> dict[str, Any]:
        before, after = told_players(tournament_id, key, "brackets_dm_reset", reason_of(payload))
        return await answered(request, tournament_id, sets.reset, key, before=before, after=after)

    @router.post("/{tournament_id}/sets/{key}/report")
    async def brackets_report(
        request: Request, tournament_id: str, key: str, payload: Any = OPTIONAL
    ) -> dict[str, Any]:
        given = body_of(payload)
        return await answered(
            request, tournament_id, sets.report, key, given.get("score_a"), given.get("score_b")
        )

    @router.post("/{tournament_id}/sets/{key}/dispute")
    async def brackets_dispute(
        request: Request, tournament_id: str, key: str, payload: Any = OPTIONAL
    ) -> dict[str, Any]:
        return await answered(
            request, tournament_id, sets.dispute, key, body_of(payload).get("note")
        )

    @router.post("/{tournament_id}/sets/{key}/override")
    async def brackets_override(
        request: Request, tournament_id: str, key: str, payload: Any = OPTIONAL
    ) -> dict[str, Any]:
        given = body_of(payload)
        before, after = told_players(tournament_id, key, "brackets_dm_decided", reason_of(payload))
        return await answered(
            request,
            tournament_id,
            sets.override,
            key,
            before=before,
            after=after,
            score_a=given.get("score_a"),
            score_b=given.get("score_b"),
            winner=given.get("winner"),
            forfeit=given.get("forfeit") is True,
        )

    return router
