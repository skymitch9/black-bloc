from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

LINK_OK = "ok"
LINK_MISSING = "missing"
LINK_UNREACHABLE = "unreachable"

MISSING_STATUSES = (404, 410)
SERVER_ERROR = 500
HEADER_BYTES = 65536
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


async def aiohttp_status(url: str, *, seconds: int, headers: dict[str, str]) -> int:
    """One GET, redirects followed, the body never read and the session never kept."""
    import aiohttp

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=seconds),
        max_line_size=HEADER_BYTES,
        max_field_size=HEADER_BYTES,
    ) as session:
        async with session.get(url, headers=headers, allow_redirects=True) as response:
            return int(response.status)


async def link_answers(url: Any, *, seconds: int, fetch: Any = None) -> str:
    """Whether a typed link answers at all; `fetch` is the request, so a test needs no network."""
    said = str(url or "").strip()
    if not said:
        return LINK_UNREACHABLE
    request = fetch or aiohttp_status
    try:
        status = int(
            await request(said, seconds=int(seconds), headers={"User-Agent": USER_AGENT})
        )
    except Exception as exc:
        log.debug("linkcheck: %s did not answer: %s", said, type(exc).__name__)
        return LINK_UNREACHABLE
    if status in MISSING_STATUSES:
        return LINK_MISSING
    if status >= SERVER_ERROR:
        return LINK_UNREACHABLE
    return LINK_OK
