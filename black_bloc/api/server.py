from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .. import __version__, personas
from . import auth, costs, ref, selftest_api, settings_api, status
from .assets import NO_STORE, SiteFiles, build_id
from .auth import Refused, refused_handler, validation_handler
from .status import latency_ms
from .tools import (
    applications,
    birthdays,
    chat,
    chat_memory,
    events,
    golive,
    honeypot,
    members,
    mod,
    modmail,
    pings,
    polls,
    raidtrain,
    requests,
    rolemenus,
    roles,
    tempvoice,
    youtube,
)

log = logging.getLogger(__name__)

AVATAR_HOSTS = "https://cdn.discordapp.com https://media.discordapp.net"
CSP = (
    f"default-src 'self'; img-src 'self' data: {AVATAR_HOSTS}; style-src 'self'; "
    "script-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
)
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000",
    "Content-Security-Policy": CSP,
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}
NO_STORE_HEADERS = {"Cache-Control": NO_STORE, "Pragma": "no-cache"}

API_PREFIX = "/api"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
SAME_SITE_HEADER = "sec-fetch-site"
SAME_ORIGIN = "same-origin"
JSON_MEDIA_TYPE = "application/json"

CROSS_SITE = (
    "That change did not come from the Black Bloc dashboard, so nothing was done. Another site "
    "cannot make changes here in your name, and this is the check that stops it — open the "
    "dashboard yourself and try again."
)
NOT_JSON = (
    "That change did not arrive the way the dashboard sends one, so nothing was done. It is a "
    "fault in the page rather than in what you typed — reload the dashboard and try again."
)
UNKNOWN_ROUTE = (
    "This dashboard asked Black Bloc for something it does not serve, so nothing was done. That "
    "is a fault in the page rather than a problem with your access — reload the dashboard, and "
    "tell a Lead if it keeps happening."
)


def same_site(request: Request, origin: str) -> bool:
    """The browser's own answer first; an exact Origin match when it sends none."""
    if request.headers.get(SAME_SITE_HEADER) == SAME_ORIGIN:
        return True
    return request.headers.get("origin") == origin


def has_body(request: Request) -> bool:
    if request.headers.get("transfer-encoding"):
        return True
    try:
        return int(request.headers.get("content-length") or 0) > 0
    except ValueError:
        return True


def json_bodied(request: Request) -> bool:
    given = request.headers.get("content-type")
    if given is None:
        return not has_body(request)
    return given.split(";")[0].strip().lower() == JSON_MEDIA_TYPE


def create_app(bot: Any, *, oauth_request: Any = None) -> FastAPI:
    app = FastAPI(
        title="Black Bloc API",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.bot = bot

    @app.middleware("http")
    async def same_site_writes(request: Request, call_next: Any) -> Any:
        if request.url.path.startswith(API_PREFIX) and request.method not in SAFE_METHODS:
            if not same_site(request, bot.settings.origin):
                log.warning(
                    "api: refused a cross-site %s %s", request.method, request.url.path
                )
                return JSONResponse({"error": "cross_site", "message": CROSS_SITE}, 403)
            if not json_bodied(request):
                return JSONResponse({"error": "not_json", "message": NOT_JSON}, 415)
        return await call_next(request)

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if request.url.path.startswith(API_PREFIX):
            for name, value in NO_STORE_HEADERS.items():
                response.headers[name] = value
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
            "personality_pool_version": personas.POOL_VERSION,
        }

    async def unknown_route(request: Request, exc: Any) -> Any:
        """An /api path nothing serves would otherwise answer Starlette's bare `detail`."""
        if request.url.path.startswith(API_PREFIX):
            return JSONResponse(
                {"error": "unknown_route", "message": UNKNOWN_ROUTE},
                status_code=getattr(exc, "status_code", 404),
            )
        return await http_exception_handler(request, exc)

    app.add_exception_handler(Refused, refused_handler)
    app.add_exception_handler(RequestValidationError, validation_handler)
    app.add_exception_handler(StarletteHTTPException, unknown_route)
    app.include_router(auth.build_router(bot, oauth_request=oauth_request))
    app.include_router(status.build_router(bot))
    app.include_router(costs.build_router(bot))
    app.include_router(ref.build_router(bot))
    app.include_router(settings_api.build_router(bot))
    app.include_router(rolemenus.build_router(bot))
    app.include_router(roles.build_router(bot))
    app.include_router(golive.build_router(bot))
    app.include_router(youtube.build_router(bot))
    app.include_router(pings.build_router(bot))
    app.include_router(events.build_router(bot))
    app.include_router(polls.build_router(bot))
    app.include_router(birthdays.build_router(bot))
    app.include_router(tempvoice.build_router(bot))
    app.include_router(honeypot.build_router(bot))
    app.include_router(mod.build_router(bot))
    app.include_router(members.build_router(bot))
    app.include_router(modmail.build_router(bot))
    app.include_router(chat.build_router(bot))
    app.include_router(chat_memory.build_router(bot))
    app.include_router(requests.build_router(bot))
    app.include_router(raidtrain.build_router(bot))
    app.include_router(applications.build_router(bot))
    app.include_router(selftest_api.build_router(bot))

    root = Path(bot.settings.site_root)
    if root.is_dir():
        build = build_id(root)
        log.info("site: build id %s", build)
        app.mount("/", SiteFiles(directory=root, build=build), name="site")
    else:
        log.warning("api: %s is not a directory — serving the API without the page", root)
    return app


def api_app(bot: Any) -> FastAPI:
    """One app per bot, kept so the self-test reads the same route table the site is served by."""
    found = getattr(bot, "_api_app", None)
    if found is None:
        found = create_app(bot)
        bot._api_app = found
    return found


async def start_api(bot: Any) -> None:
    settings = bot.settings
    config = uvicorn.Config(
        api_app(bot),
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        access_log=False,
        forwarded_allow_ips="*",
    )
    server = uvicorn.Server(config)
    log.info("API listening on http://%s:%d", settings.api_host, settings.api_port)
    await server.serve()
