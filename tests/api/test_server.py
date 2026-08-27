from pathlib import Path

from fastapi.testclient import TestClient

from black_bloc.api.server import SECURITY_HEADERS, create_app

ORIGIN = "https://testserver"


def client_for(bot):
    return TestClient(create_app(bot), base_url=ORIGIN)


def test_health(bot):
    r = client_for(bot).get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["ready"] is True
    assert body["latency_ms"] == 42


def test_health_stays_public(bot):
    """No cookie, no sign-in — /health is the uptime probe, not a dashboard route."""
    assert client_for(bot).get("/health").status_code == 200


def test_health_reports_no_latency_when_the_gateway_has_not_measured_one(bot):
    bot.latency = float("nan")
    assert client_for(bot).get("/health").json()["latency_ms"] is None


def test_there_is_no_cors_middleware_because_there_is_one_origin(bot):
    r = client_for(bot).get("/health", headers={"Origin": ORIGIN})
    assert "access-control-allow-origin" not in r.headers


def test_every_response_carries_the_security_headers(bot):
    for path in ("/health", "/api/status", "/"):
        headers = client_for(bot).get(path).headers
        for name, value in SECURITY_HEADERS.items():
            assert headers[name] == value, path


def test_the_csp_allows_no_inline_script_and_no_third_party(bot):
    csp = client_for(bot).get("/health").headers["Content-Security-Policy"]
    assert "unsafe-inline" not in csp and "unsafe-eval" not in csp
    assert "frame-ancestors 'none'" in csp


def test_the_page_is_served_from_this_app_at_the_root(bot):
    r = client_for(bot).get("/")
    assert r.status_code == 200
    assert "Black Bloc" in r.text
    assert client_for(bot).get("/assets/app.js").status_code == 200


def test_the_api_still_runs_when_the_page_is_not_on_disk(bot, tmp_path):
    bot.settings.site_root = Path(tmp_path / "nothing-here")
    assert client_for(bot).get("/health").status_code == 200


def test_a_refusal_never_leaks_a_bare_status(bot):
    body = client_for(bot).get("/api/status").json()
    assert set(body) == {"error", "message"}
    assert body["message"].endswith(".")
