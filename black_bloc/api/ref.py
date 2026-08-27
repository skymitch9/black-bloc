from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

from .auth import guild_of, staff_dependency
from .names import (
    MEMBER_SEARCH_LIMIT,
    channels,
    parse_ids,
    resolve,
    roles,
    search_members,
)

log = logging.getLogger(__name__)


def build_router(bot: Any) -> APIRouter:
    router = APIRouter(
        prefix="/api/ref", tags=["ref"], dependencies=[Depends(staff_dependency(bot))]
    )

    @router.get("/channels")
    async def ref_channels() -> list[dict[str, Any]]:
        guild = guild_of(bot)
        return channels(guild) if guild is not None else []

    @router.get("/roles")
    async def ref_roles() -> list[dict[str, Any]]:
        guild = guild_of(bot)
        return roles(guild) if guild is not None else []

    @router.get("/members")
    async def ref_members(q: str = "", limit: int = MEMBER_SEARCH_LIMIT) -> list[dict[str, Any]]:
        guild = guild_of(bot)
        return search_members(guild, q, limit) if guild is not None else []

    @router.get("/names")
    async def ref_names(ids: str = "") -> dict[str, dict[str, Any]]:
        guild = guild_of(bot)
        return resolve(guild, parse_ids(ids))

    return router
