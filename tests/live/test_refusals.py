"""Nobody ever sees a bare HTTP status: every refusal on the live host is a sentence."""

from __future__ import annotations

import pytest

from .conftest import same_site_headers

pytestmark = pytest.mark.live

WITHOUT_A_TOKEN = ("/api/status", "/api/settings", "/api/actions", "/api/selftest")
STATUS_WORDS = {"401", "403", "404", "409", "429", "503", "Forbidden", "Unauthorized"}


def says_something(response) -> str:
    body = response.json()
    assert isinstance(body, dict), f"answered {type(body).__name__}, not an object"
    assert body.get("message"), f"answered no message at all: {body}"
    assert body.get("error"), f"answered no machine-readable code: {body}"
    said = str(body["message"])
    assert len(said.split()) >= 8, f"that is not a sentence: {said!r}"
    assert said not in STATUS_WORDS
    return said


@pytest.mark.parametrize("path", WITHOUT_A_TOKEN)
def test_no_token_is_refused_in_words_rather_than_a_bare_status(stranger, path):
    response = stranger.get(path)

    assert response.status_code in (401, 403), f"{path} answered {response.status_code}"
    said = says_something(response)
    assert "sign" in said.lower() or "staff" in said.lower()


def test_a_wrong_operator_token_names_the_secret_and_says_no_account_is_locked_out(stranger):
    response = stranger.get(
        "/api/status", headers={"authorization": "Bearer not-the-token-this-server-holds"}
    )

    if response.status_code == 401 and response.json().get("error") == "not_signed_in":
        pytest.skip("operator reads are switched off on this host, so there is no door to test")
    assert response.status_code == 401
    said = says_something(response)
    assert "OPERATOR_READ_TOKEN" in said
    assert "no account is locked out" in said


def test_the_operator_token_is_refused_on_every_write_and_says_why(reader):
    """With the dashboard's own headers the origin check passes, so the OPERATOR gate is what
    answers — without them `same_site_writes` says `cross_site` first and this proves nothing."""
    refused = reader.put(
        "/api/settings/birthday_show_age", json={"value": True}, headers=same_site_headers()
    )

    assert refused.status_code == 403
    assert refused.json()["error"] == "operator_read_only"
    said = says_something(refused)
    assert "never change" in said


def test_a_route_that_does_not_exist_is_still_a_sentence(reader):
    response = reader.get("/api/nothing-is-here")

    assert response.status_code == 404
    said = says_something(response)
    assert "dashboard" in said.lower() or "fault in the page" in said.lower()
