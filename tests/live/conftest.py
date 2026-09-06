"""The live suite's own gates: skipped whole without both env names, marked `live` throughout."""

from __future__ import annotations

import json
import os
import pathlib

import httpx
import pytest

URL_NAME = "BLACK_BLOC_LIVE_URL"
TOKEN_NAME = "BLACK_BLOC_LIVE_TOKEN"
SESSION_NAME = "BLACK_BLOC_LIVE_SESSION"
SESSION_COOKIE = "__Host-bb_session"

NO_ENV = (
    f"{URL_NAME} and {TOKEN_NAME} are both needed to hit the deployed api. "
    "See docs/access/testing.md."
)
NO_SESSION = (
    f"{SESSION_NAME} is not set, so there is no staff session to write with. The operator "
    "token can only read. See docs/access/testing.md."
)
TIMEOUT = 30.0
CONTRACT = pathlib.Path(__file__).resolve().parents[2] / "site" / "mock" / "contract.json"

pytestmark = pytest.mark.live


def live_url() -> str | None:
    return (os.environ.get(URL_NAME) or "").strip().rstrip("/") or None


def live_token() -> str | None:
    return (os.environ.get(TOKEN_NAME) or "").strip() or None


def live_session() -> str | None:
    return (os.environ.get(SESSION_NAME) or "").strip() or None


def same_site_headers() -> dict[str, str]:
    """What the dashboard's own fetch sends, so `same_site_writes` is not the thing that answers."""
    return {"origin": live_url() or "", "sec-fetch-site": "same-origin"}


def readable_paths() -> list[str]:
    """The contract's own GET inventory, minus anything with an id to fill in."""
    found = json.loads(CONTRACT.read_text(encoding="utf-8"))
    return sorted(
        {
            route["path"]
            for route in found["routes"]
            if route["method"] == "GET" and "{" not in route["path"]
        }
    )


def keys_for(path: str) -> list[str]:
    found = json.loads(CONTRACT.read_text(encoding="utf-8"))
    for route in found["routes"]:
        if route["method"] == "GET" and route["path"] == path:
            return list(route.get("keys") or [])
    return []


@pytest.fixture(scope="session", autouse=True)
def needs_env():
    if not (live_url() and live_token()):
        pytest.skip(NO_ENV, allow_module_level=True)


@pytest.fixture
def reader():
    """The operator token: it can look, never change — auth.py refuses every write on it."""
    with httpx.Client(
        base_url=live_url(),
        headers={"authorization": f"Bearer {live_token()}"},
        timeout=TIMEOUT,
        follow_redirects=False,
    ) as client:
        yield client


@pytest.fixture
def stranger():
    with httpx.Client(base_url=live_url(), timeout=TIMEOUT, follow_redirects=False) as client:
        yield client


@pytest.fixture
def writer():
    """A staff session cookie, because the operator token is read-only by design."""
    session = live_session()
    if not session:
        pytest.skip(NO_SESSION)
    with httpx.Client(
        base_url=live_url(),
        cookies={SESSION_COOKIE: session},
        headers={"sec-fetch-site": "same-origin", "content-type": "application/json"},
        timeout=TIMEOUT,
        follow_redirects=False,
    ) as client:
        yield client
