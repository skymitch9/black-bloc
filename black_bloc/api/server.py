from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from .. import __version__
from . import auth, ref, settings_api, status
from .auth import Refused, refused_handler, validation_handler
from .status import latency_ms
from .tools import birthdays, events, golive, honeypot, mod, modmail, rolemenus, tempvoice

log = logging.getLogger(__name__)

CSP = (
    "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
)
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000",
    "Content-Security-Policy": CSP,
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}


def create_app(bot: Any, *, oauth_request: Any = None) -> FastAPI:
    app = FastAPI(
        title="Black Bloc API",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response

    @app.middleware("http")
    async def access_log(request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        log.info("%s %s %d", request.method, request.url.path, response.status_code)
        return response

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "ok": True,
            "version": __version__,
            "ready": bool(bot.is_ready()),
            "guilds": len(bot.guilds),
            "latency_ms": latency_ms(bot),
        }

    app.add_exception_handler(Refused, refused_handler)
    app.add_exception_handler(RequestValidationError, validation_handler)
    app.include_router(auth.build_router(bot, oauth_request=oauth_request))
    app.include_router(status.build_router(bot))
    app.include_router(ref.build_router(bot))
    app.include_router(settings_api.build_router(bot))
    app.include_router(rolemenus.build_router(bot))
    app.include_router(golive.build_router(bot))
    app.include_router(events.build_router(bot))
    app.include_router(birthdays.build_router(bot))
    app.include_router(tempvoice.build_router(bot))
    app.include_router(honeypot.build_router(bot))
    app.include_router(mod.build_router(bot))
    app.include_router(modmail.build_router(bot))

    root = Path(bot.settings.site_root)
    if root.is_dir():
        app.mount("/", StaticFiles(directory=root, html=True), name="site")
    else:
        log.warning("api: %s is not a directory — serving the API without the page", root)
    return app


async def start_api(bot: Any) -> None:
    settings = bot.settings
    config = uvicorn.Config(
        create_app(bot),
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        access_log=False,
        forwarded_allow_ips="*",
    )
    server = uvicorn.Server(config)
    log.info("API listening on http://%s:%d", settings.api_host, settings.api_port)
    await server.serve()
