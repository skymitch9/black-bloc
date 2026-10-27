"""Bluesky's public AppView: one account's author feed, read without a login."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

from . import __version__

log = logging.getLogger(__name__)

FEED_URL = (
    "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor={actor}&limit={limit}"
)
AGENT = "BlackBloc/{version} (Discord bot for a speedrunning community)"
REQUEST_TIMEOUT_SECONDS = 20
MAX_BODY_BYTES = 8_000_000
OK = 200


@dataclass(frozen=True)
class Read:
    status: int | None
    feed: list[dict[str, Any]] = field(default_factory=list)
    why: str | None = None

    @property
    def ok(self) -> bool:
        return self.why is None


async def aiohttp_fetch(url: str, headers: dict[str, str], seconds: int) -> tuple[int, bytes]:
    """One GET; the body is read up to the cap and the session is never kept."""
    import aiohttp

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=seconds)) as session:
        async with session.get(url, headers=headers) as response:
            body = await response.content.read(MAX_BODY_BYTES + 1)
            return int(response.status), body


def headers() -> dict[str, str]:
    return {"User-Agent": AGENT.format(version=__version__), "Accept": "application/json"}


async def read_feed(handle: str, limit: int, *, fetch: Any = None) -> Read:
    """`(status, feed, why)`: `why` is None only for a readable 200."""
    url = FEED_URL.format(actor=quote(str(handle), safe=""), limit=int(limit))
    request = fetch or aiohttp_fetch
    try:
        status, body = await request(url, headers(), REQUEST_TIMEOUT_SECONDS)
    except Exception as exc:
        return Read(None, why=f"{type(exc).__name__}: {exc}".strip().rstrip(":")[:300])
    if int(status) != OK:
        return Read(int(status), why=f"Bluesky answered {int(status)}")
    if len(body) > MAX_BODY_BYTES:
        return Read(int(status), why="the answer was larger than Black Bloc reads")
    try:
        payload = json.loads(body)
    except (TypeError, ValueError) as exc:
        return Read(int(status), why=f"the answer was not JSON ({type(exc).__name__})")
    feed = payload.get("feed") if isinstance(payload, dict) else None
    if not isinstance(feed, list):
        return Read(int(status), why="the answer had no feed list")
    return Read(int(status), [one for one in feed if isinstance(one, dict)])


__all__ = ["AGENT", "FEED_URL", "Read", "aiohttp_fetch", "headers", "read_feed"]
