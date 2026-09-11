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


async def test_a_page_that_answers_at_all_is_ok():
    for status in (200, 204, 301, 302, 399):
        assert await link_answers(URL, seconds=2, fetch=answering(status)) == LINK_OK


async def test_a_refusal_is_reachable_and_not_missing():
    """Cloudflare answers 403 to anything that is not a browser; the page is still there."""
    for status in (401, 403, 418, 429):
        assert await link_answers(URL, seconds=2, fetch=answering(status)) == LINK_OK


async def test_the_two_statuses_that_mean_the_page_is_not_there():
    assert await link_answers(URL, seconds=2, fetch=answering(404)) == LINK_MISSING
    assert await link_answers(URL, seconds=2, fetch=answering(410)) == LINK_MISSING


async def test_a_server_error_is_unreachable_rather_than_missing():
    for status in (500, 502, 503):
        assert await link_answers(URL, seconds=2, fetch=answering(status)) == LINK_UNREACHABLE


async def test_a_timeout_is_unreachable():
    assert await link_answers(URL, seconds=1, fetch=raising(TimeoutError())) == LINK_UNREACHABLE


async def test_dns_and_connection_trouble_are_unreachable_too():
    for trouble in (
        aiohttp.ClientConnectorError(None, OSError("no such host")),
        aiohttp.ClientError("reset"),
        OSError("refused"),
        ValueError("not a url"),
    ):
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


async def test_the_body_is_never_read_because_only_the_status_is_asked_for():
    """`fetch` returns an int, so there is nowhere for a page's body to arrive."""
    read = []

    async def fetch(url, *, seconds, headers):
        class Response:
            status = 200

            async def text(self):
                read.append(url)
                return "a whole page"

        return Response().status

    assert await link_answers(URL, seconds=2, fetch=fetch) == LINK_OK
    assert read == []
