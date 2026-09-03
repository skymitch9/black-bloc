from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ...chat_memory import (
    BY_STAFF,
    COUNTS,
    DM,
    FORGOT_KIND,
    FULL,
    MODE_KEY,
    ON,
    STAFF_VIEW_KEY,
    forget,
    optout_count,
    profile_from_row,
    profile_rows,
)
from ..auth import Refused, staff_dependency
from ..names import as_id, resolve_one
from ..writes import note, reader_dependency, require_db, require_guild, writer_dependency

log = logging.getLogger(__name__)

MEMORY_IS_OFF = (
    "Black Bloc is not remembering anybody on this server, so there is nothing here yet. The "
    "Memory switch above turns it on, and profiles start appearing after the next sweep."
)
CONTENTS_ARE_PRIVATE = (
    "This server keeps what Black Bloc remembers about a member private to that member, so the "
    "notes were not shown — only the counts on this page. It needs `chat_memory_staff_view` set "
    "to `full`, which a Lead can change on the Settings page or with "
    "`/settings set chat_memory_staff_view full`. The member can always read their own with "
    "`/memory show`."
)
NO_SUCH_PROFILE = (
    "Black Bloc remembers nothing about that member on this server, so there was nothing to "
    "show or clear."
)
FORGOT_SAID = "Cleared. Black Bloc remembers nothing about {who} here."


def summary(guild: Any, row: Any, *, full: bool) -> dict[str, Any]:
    """Counts always; the notes themselves only where the server has said staff may read them."""
    profile = profile_from_row(row)
    number = as_id(row["user_id"])
    found: dict[str, Any] = {
        "member": {
            "id": str(number),
            "name": resolve_one(guild, number)["display_name"] or str(number),
        },
        "notes": len(profile.notes),
        "threads": len(profile.threads),
        "turns_seen": profile.turns_seen,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
        "call_me": profile.call_me if full else None,
        "lines": (
            [
                {"text": one.text, "where": one.where, "kind": kind}
                for kind, source in (("note", profile.notes), ("thread", profile.threads))
                for one in source
            ]
            if full
            else []
        ),
    }
    return found


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    reader = reader_dependency(bot)
    router = APIRouter(
        prefix="/api/chat/memory",
        tags=["chat"],
        dependencies=[Depends(staff_dependency(bot))],
    )

    def _full(guild_id: int) -> bool:
        return bot.store.get(guild_id, STAFF_VIEW_KEY) == FULL

    async def _row(guild: Any, member_id: int) -> Any:
        for row in await profile_rows(bot.db, guild.id):
            if int(row["user_id"]) == int(member_id):
                return row
        raise Refused(404, "no_such_profile", NO_SUCH_PROFILE)

    @router.get("", dependencies=[Depends(reader)])
    async def memory_index() -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        full = _full(guild.id)
        rows = await profile_rows(bot.db, guild.id)
        shown = [summary(guild, row, full=full) for row in rows]
        return {
            "mode": bot.store.get(guild.id, MODE_KEY),
            "on": bot.store.get(guild.id, MODE_KEY) == ON,
            "staff_view": FULL if full else COUNTS,
            "profiles": shown,
            "total": len(shown),
            "opted_out": await optout_count(bot.db, guild.id),
            "dm_notes": sum(
                1
                for row in rows
                for one in profile_from_row(row).notes
                if one.where == DM
            ),
            "message": "" if bot.store.get(guild.id, MODE_KEY) == ON else MEMORY_IS_OFF,
        }

    @router.get("/{member_id}", dependencies=[Depends(reader)])
    async def memory_one(member_id: int) -> dict[str, Any]:
        """A refusal in words, never a bare 403: what it needs, and who can change it."""
        guild = require_guild(bot)
        require_db(bot)
        if not _full(guild.id):
            raise Refused(403, "memory_is_private", CONTENTS_ARE_PRIVATE)
        return {"profile": summary(guild, await _row(guild, member_id), full=True)}

    @router.delete("/{member_id}")
    async def memory_forget(request: Request, member_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await _row(guild, member_id)
        await forget(bot.db, member_id, guild.id)
        shown = summary(guild, row, full=False)
        await note(
            bot,
            guild,
            f"web.{FORGOT_KIND}",
            who,
            target=member_id,
            details={"who_asked": BY_STAFF},
        )
        return {
            "member": shown["member"],
            "message": FORGOT_SAID.format(who=shown["member"]["name"]),
        }

    return router


__all__ = ["build_router", "summary"]
