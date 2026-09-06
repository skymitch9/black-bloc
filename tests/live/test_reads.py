"""Every GET the pages make answers 200 on the DEPLOYED host, with the keys they read."""

from __future__ import annotations

import pytest

from .conftest import readable_paths, spec_for

pytestmark = pytest.mark.live

NOBODY = "not_a_member"


def rows_of(payload, spec) -> list:
    """Where the contract's `keys` live, by `shape` — the reading `site/mock/check.mjs` makes."""
    shape = spec.get("shape")
    if shape == "list":
        return list(payload)
    if shape == "map":
        return list(payload.values())
    if shape == "namespaces":
        return [row for name in spec.get("namespaces", []) for row in payload.get(name, [])]
    return [payload]


@pytest.mark.parametrize("path", readable_paths())
def test_every_read_the_pages_make_answers_on_the_live_host(reader, path):
    """A member-scoped read refuses the operator in words: it is nobody's account."""
    response = reader.get(path)

    if response.status_code == 403 and response.json().get("error") == NOBODY:
        assert "member" in response.json()["message"]
        return
    assert response.status_code == 200, f"{path} answered {response.status_code}: {response.text}"
    if path.endswith(".csv"):
        assert response.text, f"{path} answered an empty file"
        return
    spec = spec_for(path)
    for row in rows_of(response.json(), spec):
        missing = [key for key in spec.get("keys", []) if key not in row]
        assert not missing, f"{path} is missing {missing}"


def test_health_answers_without_any_token_at_all(stranger):
    """The one route a load balancer reaches; it says nothing a stranger may not know."""
    response = stranger.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert {"version", "ready", "guilds", "latency_ms"} <= set(body)


def test_the_bot_is_connected_and_in_the_server(reader):
    body = reader.get("/api/status").json()

    assert body["bot"]["ready"] is True, "the gateway is not connected"
    assert body["guild"] is not None, "the bot is in no server it can report on"
    assert body["bot"]["guilds"] >= 1


def test_no_loop_has_stopped_or_failed(reader):
    """Checklist 9: a stopped loop is the failure a status page exists to surface."""
    loops = reader.get("/api/status").json()["loops"]

    assert loops, "no loops are loaded at all"
    broken = [f"{one['cog']}.{one['name']}" for one in loops if one["state"] != "ok"]
    assert not broken, f"these loops are not running: {broken}"
