from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from ... import baf_runs as runs
from ...logkinds import VIA_WEBSITE
from ...settings_store import RUNS_PARTS, RUNS_SOURCES
from ..auth import Refused, staff_dependency
from ..writes import actor_for, require_db, require_guild, writer_dependency

CSV_TYPE = "text/csv; charset=utf-8"
CSV_NAME = 'attachment; filename="baf-runs.csv"'
NOTHING_TO_IMPORT = (
    "There was nothing to import, so nothing was read. Paste a GDQ tracker event link, or "
    "choose a CSV file."
)


def answered(outcome: Any) -> dict[str, Any]:
    if not outcome.ok:
        raise Refused(outcome.status or 409, outcome.code or "refused", outcome.message)
    return {"ok": True, "message": outcome.message, "value": outcome.value}


def names_of(rows: list[dict[str, Any]], tag: str) -> list[str]:
    return sorted({row[tag] for row in rows if row[tag]}, key=str.lower)


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/runs", tags=["runs"], dependencies=[Depends(staff_dependency(bot))]
    )

    def ready() -> Any:
        guild = require_guild(bot)
        require_db(bot)
        return guild

    @router.get("")
    async def runs_index(
        game: str = "",
        event: str = "",
        series: str = "",
        genre: str = "",
        runner: str = "",
        year: str = "",
        how: str = "",
        q: str = "",
        removed: bool | None = None,
    ) -> dict[str, Any]:
        guild = ready()
        every = await runs.view(bot, guild)
        wanted = {
            "game": game,
            "event": event,
            "series": series,
            "genre": genre,
            "runner": runner,
            "year": year,
            "how": how,
            "q": q,
        }
        rule = runs.genre_rule(bot, guild.id)
        rows = every
        if any(wanted.values()) or removed is not None:
            rows = runs.filtered(every, **wanted, removed=bool(removed), rule=rule)
        sources = list(bot.store.get(guild.id, RUNS_SOURCES) or ())
        return {
            "rows": rows,
            "events": await runs.counted_events(bot.db, guild.id, sources),
            "series_names": names_of(every, runs.SERIES),
            "genre_names": names_of(every, runs.GENRE),
            "genre_families": runs.families_shown(rule),
            "sources": sources,
            "parts": list(bot.store.get(guild.id, RUNS_PARTS) or ()),
        }

    @router.get("/games")
    async def runs_games() -> dict[str, Any]:
        guild = ready()
        return {"games": runs.games(await runs.view(bot, guild))}

    @router.get("/export.csv")
    async def runs_export() -> Response:
        guild = ready()
        text = runs.export_csv(await runs.view(bot, guild))
        return Response(
            content=text, media_type=CSV_TYPE, headers={"Content-Disposition": CSV_NAME}
        )

    @router.post("")
    async def runs_add(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        outcome = await runs.add(bot, guild, actor_for(bot, who, guild), payload, via=VIA_WEBSITE)
        return answered(outcome)

    @router.post("/import")
    async def runs_import(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        actor = actor_for(bot, who, guild)
        dry_run = payload.get("dry_run") is not False
        if str(payload.get("event_url") or "").strip():
            outcome = await runs.import_event(
                bot,
                guild,
                actor,
                payload.get("event_url"),
                dry_run=dry_run,
                pairs=payload.get("pairs") if isinstance(payload.get("pairs"), dict) else None,
                via=VIA_WEBSITE,
            )
        elif str(payload.get("csv") or "").strip():
            outcome = await runs.import_csv(
                bot, guild, actor, payload.get("csv"), dry_run=dry_run, via=VIA_WEBSITE
            )
        else:
            raise Refused(400, "nothing_to_import", NOTHING_TO_IMPORT)
        return answered(outcome)

    @router.put("/series/{game_key:path}")
    async def runs_series(
        request: Request, game_key: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        outcome = await runs.set_series(
            bot,
            guild,
            actor_for(bot, who, guild),
            game_key,
            payload.get("series"),
            via=VIA_WEBSITE,
        )
        return answered(outcome)

    @router.put("/genre/{game_key:path}")
    async def runs_genre(
        request: Request, game_key: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        outcome = await runs.set_genre(
            bot,
            guild,
            actor_for(bot, who, guild),
            game_key,
            payload.get("genre"),
            via=VIA_WEBSITE,
        )
        return answered(outcome)

    @router.put("/{key}")
    async def runs_edit(request: Request, key: str, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        outcome = await runs.edit(
            bot, guild, actor_for(bot, who, guild), key, payload, via=VIA_WEBSITE
        )
        return answered(outcome)

    @router.delete("/{key}")
    async def runs_remove(request: Request, key: str) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        outcome = await runs.remove(bot, guild, actor_for(bot, who, guild), key, via=VIA_WEBSITE)
        return answered(outcome)

    @router.post("/{key}/restore")
    async def runs_restore(request: Request, key: str) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        outcome = await runs.restore(bot, guild, actor_for(bot, who, guild), key, via=VIA_WEBSITE)
        return answered(outcome)

    return router
