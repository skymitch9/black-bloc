"""One HTTP session for every sports feed: paced per host, answering `Found`, never raising."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlsplit

from .model import Found, failed, found

AGENT = "Mozilla/5.0 (Black Bloc)"
TIMEOUT_SECONDS = 15
MAX_BODY_BYTES = 8_000_000
OK = 200
DEFAULT_GAP_SECONDS = 0.1
GAPS: dict[str, float] = {
    "ncaa-api.henrygd.me": 0.4,
    "stats.nba.com": 0.6,
}
NBA_HEADERS = {"Referer": "https://www.nba.com/", "Origin": "https://www.nba.com"}

Fetch = Callable[[str, dict[str, str], int], Awaitable[tuple[int, bytes]]]


class Pacer:
    """Waits until a host's minimum gap since the last call has passed."""

    def __init__(self, clock: Callable[[], float] = time.monotonic, sleep: Any = None) -> None:
        self.clock = clock
        self.sleep = sleep or asyncio.sleep
        self.last: dict[str, float] = {}
        self.locks: dict[str, asyncio.Lock] = {}

    async def wait(self, host: str) -> None:
        lock = self.locks.setdefault(host, asyncio.Lock())
        async with lock:
            gap = GAPS.get(host, DEFAULT_GAP_SECONDS)
            last = self.last.get(host)
            if last is not None:
                left = gap - (self.clock() - last)
                if left > 0:
                    await self.sleep(left)
            self.last[host] = self.clock()


PACER = Pacer()
_session: Any = None


async def session() -> Any:
    global _session
    import aiohttp

    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS),
            headers={"User-Agent": AGENT, "Accept": "application/json"},
        )
    return _session


async def close() -> None:
    global _session
    held, _session = _session, None
    if held is not None and not held.closed:
        await held.close()


async def network(url: str, headers: dict[str, str], seconds: int) -> tuple[int, bytes]:
    await PACER.wait(urlsplit(url).hostname or "")
    held = await session()
    async with held.get(url, headers=headers) as response:
        if (response.content_length or 0) > MAX_BODY_BYTES:
            return int(response.status), bytes(MAX_BODY_BYTES + 1)
        return int(response.status), await response.read()


def headers_for(url: str) -> dict[str, str]:
    found_headers = {"User-Agent": AGENT, "Accept": "application/json"}
    if (urlsplit(url).hostname or "").endswith("nba.com"):
        found_headers.update(NBA_HEADERS)
    return found_headers


async def get_json(url: str, *, fetch: Fetch | None = None) -> Found:
    """The parsed body of a 200, or why not in words; any transport error is a `why`."""
    request = fetch or network
    try:
        status, body = await request(url, headers_for(url), TIMEOUT_SECONDS)
    except Exception as exc:
        named = type(exc).__name__
        return failed(f"did not answer ({named}{': ' + str(exc) if str(exc) else ''})")
    if int(status) != OK:
        return failed(f"answered {int(status)}")
    if len(body) > MAX_BODY_BYTES:
        return failed("sent more than Black Bloc reads")
    try:
        return found(json.loads(body))
    except (TypeError, ValueError):
        return failed("answered with something that is not JSON")


__all__ = [
    "AGENT",
    "GAPS",
    "NBA_HEADERS",
    "PACER",
    "TIMEOUT_SECONDS",
    "Fetch",
    "Pacer",
    "close",
    "get_json",
    "headers_for",
    "network",
    "session",
]
