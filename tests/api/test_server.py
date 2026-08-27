from fastapi.testclient import TestClient

from black_bloc.api.server import create_app

SITE = "https://blackbloc.heygabi.ai"


def client_for(bot):
    return TestClient(create_app(bot), base_url="http://testserver")


def test_health(bot):
    r = client_for(bot).get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["ready"] is True
    assert body["latency_ms"] == 42


def test_health_stays_public(bot):
    """No cookie, no sign-in — /health is the uptime probe, not a dashboard route."""
    r = client_for(bot).get("/health", headers={"Origin": SITE})
    assert r.status_code == 200


def test_cors_allows_the_site_origin_with_credentials(bot):
    r = client_for(bot).get("/api/auth/me", headers={"Origin": SITE})
    assert r.headers["access-control-allow-origin"] == SITE
    assert r.headers["access-control-allow-credentials"] == "true"


def test_cors_refuses_any_other_origin(bot):
    r = client_for(bot).options(
        "/api/auth/me",
        headers={
            "Origin": "https://not-the-site.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in r.headers


def test_cors_preflight_passes_for_the_site_origin(bot):
    r = client_for(bot).options(
        "/api/auth/logout",
        headers={"Origin": SITE, "Access-Control-Request-Method": "POST"},
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == SITE


def test_a_refusal_never_leaks_a_bare_status(bot):
    body = client_for(bot).get("/api/status").json()
    assert set(body) == {"error", "message"}
    assert body["message"].endswith(".")
