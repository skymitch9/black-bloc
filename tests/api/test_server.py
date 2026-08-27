import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from black_bloc.api.assets import NO_STORE, REVALIDATE
from black_bloc.api.server import (
    AVATAR_HOSTS,
    NO_STORE_HEADERS,
    SAME_ORIGIN,
    SAME_SITE_HEADER,
    SECURITY_HEADERS,
    create_app,
)

ORIGIN = "https://testserver"
SAME_SITE = {SAME_SITE_HEADER: SAME_ORIGIN}


def client_for(bot, **kwargs):
    return TestClient(create_app(bot), base_url=ORIGIN, headers=SAME_SITE, **kwargs)


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
    assert "discordapp" not in csp.split("img-src", 1)[0]


def test_the_csp_lets_discord_avatars_load_and_nothing_else_off_site(bot):
    """`img-src 'self' data:` alone made every Members avatar a broken image."""
    csp = client_for(bot).get("/health").headers["Content-Security-Policy"]

    images = csp.split("img-src ", 1)[1].split(";", 1)[0]

    assert images == f"'self' data: {AVATAR_HOSTS}"
    assert "https:" not in csp.replace(AVATAR_HOSTS, "")


def test_the_page_is_served_from_this_app_at_the_root(bot):
    r = client_for(bot).get("/")
    assert r.status_code == 200
    assert "Black Bloc" in r.text
    assert client_for(bot).get("/assets/app.js").status_code == 200


def test_every_page_asks_for_the_favicon_this_app_can_actually_serve(bot):
    """The log was a `GET /favicon.ico 404` on every page load."""
    pages = sorted(Path(bot.settings.site_root).glob("*.html"))
    assert len(pages) >= 13
    for page in pages:
        assert '<link rel="icon" href="/favicon.ico"' in page.read_text(encoding="utf-8"), page

    response = client_for(bot).get("/favicon.ico")

    assert response.status_code == 200
    assert response.content[:4] == b"\x00\x00\x01\x00"


def test_every_page_carries_the_build_id_on_every_asset_it_asks_for(bot):
    """Returning browsers rendered a deploy-old site.css until a hard reload."""
    client = client_for(bot)
    for page in sorted(Path(bot.settings.site_root).glob("*.html")):
        html = client.get(f"/{page.name}").text
        assert re.search(r'(?:href|src)="/assets/[^"?#]+"', html) is None, page
        assert "?v=" in html, page


def test_the_page_is_never_stored_and_the_assets_are_revalidated(bot):
    client = client_for(bot)
    assert client.get("/index.html").headers["Cache-Control"] == NO_STORE
    assert client.get("/assets/app.js").headers["Cache-Control"] == REVALIDATE


def test_the_api_still_runs_when_the_page_is_not_on_disk(bot, tmp_path):
    bot.settings.site_root = Path(tmp_path / "nothing-here")
    assert client_for(bot).get("/health").status_code == 200


def test_the_schema_and_the_docs_are_not_published(bot):
    """This app is the public front door now — its route list is not a page."""
    client = client_for(bot)
    for path in ("/openapi.json", "/docs", "/redoc"):
        assert client.get(path).status_code == 404, path


def test_a_refusal_never_leaks_a_bare_status(bot):
    body = client_for(bot).get("/api/status").json()
    assert set(body) == {"error", "message"}
    assert body["message"].endswith(".")


WRITE_ROUTES = (
    "/api/honeypot/setup",
    "/api/tempvoice/setup",
    "/api/birthdays/import",
    "/api/mod/cases/1/apply",
)


def web_client(web, **headers):
    """No default headers, so each test says exactly what the browser sent."""
    return TestClient(create_app(web), base_url=ORIGIN, headers=headers or None)


@pytest.mark.parametrize("path", WRITE_ROUTES)
def test_a_form_post_from_another_site_never_reaches_a_handler(web, sign_in, path):
    client = web_client(web, **{SAME_SITE_HEADER: "cross-site", "origin": "https://evil.test"})
    sign_in(client)

    response = client.post(path, data={"user_id": "7", "confirm": "yes"})

    assert response.status_code == 403
    assert response.json()["error"] == "cross_site"
    assert response.json()["message"].endswith(".")


async def test_a_cross_site_write_leaves_no_trace_in_the_log(web, sign_in, wf):
    client = web_client(web, origin="https://evil.test")
    sign_in(client)

    assert client.post("/api/rolemenus", json={"name": "c", "title": "C"}).status_code == 403
    assert await wf.kinds_in(web.db) == []


def test_a_same_site_form_post_is_refused_before_the_handler_reads_it(web, sign_in):
    client = web_client(web, **{SAME_SITE_HEADER: SAME_ORIGIN})
    sign_in(client)

    response = client.post("/api/rolemenus", data={"name": "c", "title": "C"})

    assert response.status_code == 415
    assert response.json()["error"] == "not_json"
    assert response.json()["message"].endswith(".")


def test_a_same_origin_json_write_still_works(web, sign_in):
    client = web_client(web, **{SAME_SITE_HEADER: SAME_ORIGIN})
    sign_in(client)

    made = client.post("/api/rolemenus", json={"name": "colours", "title": "Colours"})

    assert made.status_code == 200
    assert made.json()["name"] == "colours"


def test_an_exact_origin_stands_in_for_a_browser_that_sends_no_fetch_metadata(web, sign_in):
    client = web_client(web, origin=ORIGIN)
    sign_in(client)

    assert client.post("/api/rolemenus", json={"name": "c", "title": "C"}).status_code == 200


def test_a_write_with_neither_header_is_refused(web, sign_in):
    client = web_client(web)
    sign_in(client)

    assert client.post("/api/rolemenus", json={"name": "c", "title": "C"}).status_code == 403


def test_reads_are_never_blocked_by_the_same_site_check(web, sign_in):
    client = web_client(web, origin="https://evil.test")
    sign_in(client)

    assert client.get("/api/rolemenus").status_code == 200


def test_logout_is_not_exempt(web, sign_in):
    refused = web_client(web, origin="https://evil.test")
    sign_in(refused)
    assert refused.post("/api/auth/logout").status_code == 403

    allowed = web_client(web, **{SAME_SITE_HEADER: SAME_ORIGIN})
    sign_in(allowed)
    assert allowed.post("/api/auth/logout").status_code == 200


def test_a_bodyless_delete_needs_no_content_type(client, sign_in):
    sign_in(client)
    client.post("/api/rolemenus", json={"name": "colours", "title": "Colours"})

    assert client.delete("/api/rolemenus/colours").status_code == 200


def test_every_api_answer_is_no_store(bot):
    for path in ("/api/status", "/api/auth/me"):
        headers = client_for(bot).get(path).headers
        for name, value in NO_STORE_HEADERS.items():
            assert headers[name] == value, path
