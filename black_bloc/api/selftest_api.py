from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from .. import selftest
from ..logkinds import VIA_WEBSITE
from .auth import Refused, staff_dependency
from .writes import actor_for, require_db, require_guild, writer_dependency

log = logging.getLogger(__name__)

RUNS_LIMIT = 20
NOTHING_TO_PURGE = (
    "That self-test run has nothing left to delete — its cards have already gone. Nothing was "
    "done, and nothing is wrong."
)
BUSY_CODE = "selftest_running"
NO_RUN_CODE = "no_such_run"


def run_row(row: Any, running_id: int | None = None) -> dict[str, Any]:
    return {
        "run_id": row["id"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "ok": row["ok"],
        "failed": row["failed"],
        "posted": row["posted"],
        "purged_at": row["purged_at"],
        "via": row["via"],
        "actor_id": str(row["actor_id"]) if row["actor_id"] is not None else None,
        "running": row["id"] == running_id,
    }


async def wanted_run(bot: Any, guild: Any, run_id: int) -> Any:
    found = await selftest.one_run(bot.db, guild.id, run_id)
    if found is None:
        raise Refused(404, NO_RUN_CODE, selftest.NO_RUN.format(run_id=run_id))
    return found


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/selftest", tags=["selftest"], dependencies=[Depends(staff_dependency(bot))]
    )

    @router.post("")
    async def start(request: Request) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        try:
            one = await selftest.begin(
                bot, guild, actor=actor_for(bot, who, guild), via=VIA_WEBSITE
            )
        except selftest.SelfTestBusy as exc:
            raise Refused(409, BUSY_CODE, str(exc)) from None
        task = asyncio.create_task(selftest.finish(one), name=f"selftest-{one.run_id}")
        keep_tasks(bot).add(task)
        task.add_done_callback(keep_tasks(bot).discard)
        return {
            "run_id": one.run_id,
            "started_at": one.started_at.isoformat(),
            "checks": one.total,
        }

    @router.get("")
    async def runs() -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        going = selftest.running(bot, guild.id)
        rows = await selftest.recent_runs(bot.db, guild.id, RUNS_LIMIT)
        return {
            "runs": [run_row(row, going.run_id if going else None) for row in rows],
            "running": going.run_id if going else None,
            "purge_minutes": selftest.purge_minutes(bot, guild.id),
            "notes": [],
        }

    @router.get("/{run_id}")
    async def one(run_id: int) -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        found = await wanted_run(bot, guild, run_id)
        going = selftest.running(bot, guild.id)
        return run_row(found, going.run_id if going else None) | {
            "checks": await selftest.checks_of(bot.db, guild.id, run_id)
        }

    @router.post("/{run_id}/purge")
    async def purge(request: Request, run_id: int) -> dict[str, Any]:
        await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        await wanted_run(bot, guild, run_id)
        gone = await selftest.purge(
            bot, guild, run_id=run_id, due_only=False, via=VIA_WEBSITE
        )
        found = await wanted_run(bot, guild, run_id)
        return run_row(found) | {
            "purged": gone,
            "notes": [] if gone else [NOTHING_TO_PURGE],
        }

    return router


def keep_tasks(bot: Any) -> set[Any]:
    """A bare `create_task` can be collected mid-run, so the set holds a reference until it ends."""
    found = getattr(bot, "_selftest_tasks", None)
    if found is None:
        found = set()
        bot._selftest_tasks = found
    return found
