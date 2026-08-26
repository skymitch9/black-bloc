"""FastAPI app + in-loop uvicorn runner. Off unless API_ENABLED=true.

Runs in the same asyncio loop as the Discord client so routes can read bot
state directly (no IPC). Binds to localhost by default and has NO auth yet —
see docs/KNOWN_ISSUES.md before exposing it.
"""

from __future__ import annotations

import logging
from typing import Any

import uvicorn
from fastapi import FastAPI

from .. import __version__

log = logging.getLogger(__name__)


def create_app(bot: Any) -> FastAPI:
    app = FastAPI(title="Black Bloc API", version=__version__, docs_url=None, redoc_url=None)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        ready = bool(bot.is_ready())
        return {
            "ok": True,
            "version": __version__,
            "ready": ready,
            "guilds": len(bot.guilds),
            "latency_ms": round(bot.latency * 1000) if ready else None,
        }

    return app


async def start_api(bot: Any) -> None:
    settings = bot.settings
    config = uvicorn.Config(
        create_app(bot),
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    log.info("API listening on http://%s:%d", settings.api_host, settings.api_port)
    await server.serve()
