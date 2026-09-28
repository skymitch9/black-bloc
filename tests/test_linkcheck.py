"""Follow-up 4 B (`docs/info/where-picker-design.md`): the link is tried before it is kept.

Every test injects `fetch`, so nothing here touches the network.
"""

import aiohttp
import pytest

from black_bloc.linkcheck import (
    LINK_MISSING,
    LINK_OK,
    LINK_UNREACHABLE,
    USER_AGENT,
    link_answers,
)

pytestmark = pytest.mark.asyncio

URL = "https://twitch.tv/skyaiva"


def answering(status, seen=None):
    async def fetch(url, *, seconds, headers):
        if seen is not None:
            seen.append({"url": url, "seconds": seconds, "headers": headers})
        return status

    return fetch


def raising(exc):
    async def fetch(url, *, seconds, headers):
        raise exc

    return fetch


@pytest.mark.parametrize(
    ("status", "said"),
    [
        *[(one, LINK_OK) for one in (200, 204, 301, 302, 399)],
        *[(one, LINK_OK) for one in (401, 403, 418, 429)],
        (404, LINK_MISSING),
        (410, LINK_MISSING),
        *[(one, LINK_UNREACHABLE) for one in (500, 502, 503)],
    ],
    ids=lambda value: str(value),
)
async def test_the_status_decides_ok_missing_or_unreachable_and_a_refusal_is_still_ok(status, said):
    assert await link_answers(URL, seconds=2, fetch=answering(status)) == said


@pytest.mark.parametrize(
    "trouble",
    [
        TimeoutError(),
        aiohttp.ClientConnectorError(None, OSError("no such host")),
        aiohttp.ClientError("reset"),
        OSError("refused"),
        ValueError("not a url"),
    ],
    ids=["timeout", "dns", "client-error", "refused", "not-a-url"],
)
async def test_a_request_that_never_answers_is_unreachable(trouble):
    assert await link_answers(URL, seconds=2, fetch=raising(trouble)) == LINK_UNREACHABLE


async def test_nothing_to_check_is_unreachable_and_never_asks():
    seen = []

    assert await link_answers("", seconds=2, fetch=answering(200, seen)) == LINK_UNREACHABLE
    assert await link_answers(None, seconds=2, fetch=answering(200, seen)) == LINK_UNREACHABLE
    assert seen == []


async def test_the_browser_user_agent_and_the_bound_go_out_with_the_request():
    """A bare aiohttp UA gets WAF-blocked, which would read as a dead link."""
    seen = []

    assert await link_answers(f"  {URL}  ", seconds=3, fetch=answering(200, seen)) == LINK_OK
    assert seen == [{"url": URL, "seconds": 3, "headers": {"User-Agent": USER_AGENT}}]
    assert "Mozilla/5.0" in USER_AGENT and "aiohttp" not in USER_AGENT.lower()
