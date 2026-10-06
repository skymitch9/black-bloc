from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from ... import structure_store
from ...cogs.moderation.structure_backup import (
    changes_since,
    failure_reason,
    mode_of,
    record_download,
    said,
    take_snapshot,
)
from ...logkinds import VIA_WEBSITE
from ...settings_store import (
    DEFAULT_TIMEZONE_KEY,
    STRUCTURE_BACKUP_HOUR,
    STRUCTURE_BACKUP_KEEP,
)
from ...structure import FAILED, MANUAL, OFF, body_of, export, export_name
from ...structure_diff import changes as changes_between
from ..auth import Refused, staff_dependency
from ..names import resolve_one
from ..writes import actor_for, reader_dependency, require_db, require_guild, writer_dependency

log = logging.getLogger(__name__)

NOW = "now"
LIST_DEFAULT_LIMIT = 100
LIST_MAX_LIMIT = structure_store.LIST_LIMIT

NO_SUCH_SNAPSHOT = (
    "Black Bloc has no structure snapshot **#{given}** — it may have been pruned since this "
    "page was loaded. Refresh the page and pick one from the list."
)
NOT_A_SNAPSHOT = (
    "**{given}** is not a snapshot number, so nothing was compared. Pick a snapshot from the "
    "list and try again."
)
NEEDS_TWO = (
    "Comparing needs an older snapshot and something to compare it with, so nothing was "
    "compared. Pick both and try again."
)


def snapshot_row(guild: Any, row: Any) -> dict[str, Any]:
    by = row["taken_by"]
    return {
        "id": row["id"],
        "taken_at": row["taken_at"],
        "source": row["source"],
        "taken_by_id": str(by) if by is not None else None,
        "taken_by_name": resolve_one(guild, by)["display_name"] if by is not None else None,
        "digest": str(row["digest"])[:12],
        "roles": row["roles"],
        "categories": row["categories"],
        "channels": row["channels"],
        "overwrites": row["overwrites"],
        "checked_at": row["checked_at"],
        "checks": row["checks"],
    }


def look_row(looked: Any) -> dict[str, Any] | None:
    if looked is None:
        return None
    return {"at": looked["last_at"], "outcome": looked["outcome"], "reason": looked["reason"]}


def wanted_snapshot(given: Any) -> int:
    text = str(given or "").strip()
    if not text:
        raise Refused(400, "bad_request", NEEDS_TWO)
    if not text.isdigit():
        raise Refused(400, "bad_request", NOT_A_SNAPSHOT.format(given=text[:40]))
    return int(text)


async def stored(bot: Any, guild: Any, given: Any) -> Any:
    wanted = wanted_snapshot(given)
    row = await structure_store.get(bot.db, guild.id, wanted)
    if row is None:
        raise Refused(404, "no_such_snapshot", NO_SUCH_SNAPSHOT.format(given=wanted))
    return row


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    reader = reader_dependency(bot)
    router = APIRouter(
        prefix="/api/structure",
        tags=["structure"],
        dependencies=[Depends(staff_dependency(bot))],
    )

    @router.get("")
    async def structure_index(limit: int = LIST_DEFAULT_LIMIT) -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        wanted = max(1, min(int(limit), LIST_MAX_LIMIT))
        rows = await structure_store.listed(bot.db, guild.id, wanted)
        return {
            "mode": mode_of(bot, guild.id),
            "hour": bot.store.get(guild.id, STRUCTURE_BACKUP_HOUR),
            "keep": bot.store.get(guild.id, STRUCTURE_BACKUP_KEEP),
            "timezone": bot.store.get(guild.id, DEFAULT_TIMEZONE_KEY),
            "last_look": look_row(await structure_store.look(bot.db, guild.id)),
            "snapshots": [snapshot_row(guild, row) for row in rows],
        }

    @router.post("/snapshots")
    async def structure_take(request: Request) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        taken = await take_snapshot(
            bot, guild, source=MANUAL, actor=actor_for(bot, who, guild), via=VIA_WEBSITE
        )
        if taken.outcome == OFF:
            raise Refused(409, "structure_off", taken.said)
        if taken.outcome == FAILED:
            raise Refused(502, "capture_failed", taken.said)
        return {
            "outcome": taken.outcome,
            "message": taken.said,
            "snapshot": snapshot_row(guild, taken.row),
            "changes": len(taken.changes),
        }

    @router.get("/compare")
    async def structure_compare(request: Request, old: str = "", new: str = "") -> dict[str, Any]:
        await reader(request)
        guild = require_guild(bot)
        require_db(bot)
        before = await stored(bot, guild, old)
        if str(new).strip().lower() == NOW:
            try:
                found = await changes_since(bot, guild, before)
            except Exception as exc:
                log.warning("structure: could not compare — %s: %s", type(exc).__name__, exc)
                reason = failure_reason(exc)
                raise Refused(
                    502,
                    "capture_failed",
                    said(bot.store, guild.id, "structure_backup_failed_said", reason=reason),
                ) from exc
            after = None
        else:
            after_row = await stored(bot, guild, new)
            found = changes_between(body_of(before), body_of(after_row))
            after = snapshot_row(guild, after_row)
        return {
            "old": snapshot_row(guild, before),
            "new": after,
            "now": after is None,
            "count": len(found),
            "changes": found,
        }

    @router.post("/snapshots/{snapshot_id}/download")
    async def structure_download(request: Request, snapshot_id: str) -> JSONResponse:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await stored(bot, guild, snapshot_id)
        await record_download(bot, guild, actor_for(bot, who, guild), row, via=VIA_WEBSITE)
        return JSONResponse(
            export(row),
            headers={"Content-Disposition": f'attachment; filename="{export_name(row)}"'},
        )

    return router
