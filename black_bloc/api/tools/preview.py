from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ...preview import PreviewRefused, features_payload, render
from ..auth import Refused, staff_dependency
from ..writes import require_guild

log = logging.getLogger(__name__)

BAD_BODY = (
    "The dashboard asked for a preview without saying which message, so nothing was drawn. That "
    "is a fault in the page rather than a problem with your access — reload the dashboard."
)


def build_router(bot: Any) -> APIRouter:
    router = APIRouter(
        prefix="/api/preview",
        tags=["preview"],
        dependencies=[Depends(staff_dependency(bot))],
    )

    @router.get("/features")
    async def preview_features() -> dict[str, Any]:
        return features_payload()

    @router.post("/message")
    async def preview_message(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        guild = require_guild(bot)
        if not isinstance(payload, dict):
            raise Refused(400, "bad_preview", BAD_BODY)
        try:
            found = render(
                bot,
                guild,
                payload.get("feature"),
                payload.get("overrides"),
                payload.get("sample"),
            )
        except PreviewRefused as exc:
            raise Refused(400, exc.error, exc.message) from exc
        return found.to_dict()

    return router
