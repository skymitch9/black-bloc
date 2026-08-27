from __future__ import annotations

import logging
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .. import __version__
from . import auth, status
from .auth import Refused, refused_handler

log = logging.getLogger(__name__)

CORS_METHODS = ("GET", "POST", "OPTIONS")
CORS_HEADERS = ("content-type",)


def create_app(bot: Any, *, oauth_request: Any = None) -> FastAPI:
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

    app.add_exception_handler(Refused, refused_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(bot.settings.site_origin).rstrip("/")],
        allow_credentials=True,
        allow_methods=list(CORS_METHODS),
        allow_headers=list(CORS_HEADERS),
    )
    app.include_router(auth.build_router(bot, oauth_request=oauth_request))
    app.include_router(status.build_router(bot))
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
