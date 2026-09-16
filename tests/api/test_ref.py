from __future__ import annotations

import pytest

REF_ROUTES = [
    "/api/ref/channels",
    "/api/ref/roles",
    "/api/ref/members",
    "/api/ref/names",
]


@pytest.mark.parametrize("route", REF_ROUTES)
def test_every_reference_route_needs_a_session(client, route):
    response = client.get(route)
    assert response.status_code == 401
    assert response.json()["error"] == "not_signed_in"


@pytest.mark.parametrize("route", REF_ROUTES)
def test_every_reference_route_refuses_a_non_staff_visitor(client, sign_in, route):
    sign_in(client, uid=1234, staff=False)
    response = client.get(route)
    assert response.status_code == 403
    assert response.json()["error"] == "not_staff"
    assert "Ask a Lead" in response.json()["message"]


@pytest.mark.parametrize("route", REF_ROUTES)
def test_every_reference_route_answers_a_staff_session(client, sign_in, route):
    sign_in(client)
    assert client.get(route).status_code == 200


def test_channels_come_back_with_ids_as_strings(client, sign_in, wf):
    sign_in(client)
    rows = client.get("/api/ref/channels").json()
    by_id = {row["id"]: row for row in rows}
    assert by_id[str(wf.TEST_CHANNEL_ID)]["name"] == "blackbloc-logs"
    assert by_id[str(wf.TEST_CHANNEL_ID)]["type"] == "text"
    assert by_id[str(wf.VOICE_CHANNEL_ID)]["type"] == "voice"
    assert all(isinstance(row["id"], str) for row in rows)


def test_roles_come_back_highest_first(client, sign_in):
    sign_in(client)
    rows = client.get("/api/ref/roles").json()
    assert [row["name"] for row in rows] == ["Admin", "Aunties / Uncles", "Member"]


def test_member_search_filters_and_clamps(client, sign_in, guild, wf):
    wf.member(guild, 21, name="ada")
    wf.member(guild, 22, name="grace")
    sign_in(client)

    assert [r["id"] for r in client.get("/api/ref/members", params={"q": "ada"}).json()] == ["21"]
    assert len(client.get("/api/ref/members", params={"limit": 1}).json()) == 1
    assert client.get("/api/ref/members", params={"q": "nobody"}).json() == []


def test_names_resolves_a_batch_of_mixed_ids(client, sign_in, guild, wf):
    wf.member(guild, 21, name="ada")
    sign_in(client)
    ids = f"21,{wf.STAFF_ROLE_ID},{wf.TEST_CHANNEL_ID},999999"

    body = client.get("/api/ref/names", params={"ids": ids}).json()

    assert body["21"]["kind"] == "member"
    assert body[str(wf.STAFF_ROLE_ID)]["kind"] == "role"
    assert body[str(wf.TEST_CHANNEL_ID)]["kind"] == "channel"
    assert body["999999"]["kind"] == "unknown"


def test_names_without_ids_is_an_empty_answer_not_an_error(client, sign_in):
    sign_in(client)
    response = client.get("/api/ref/names")
    assert response.status_code == 200 and response.json() == {}


def test_a_malformed_limit_is_a_sentence(client, sign_in):
    sign_in(client)
    response = client.get("/api/ref/members", params={"limit": "lots"})
    assert response.status_code == 400
    assert set(response.json()) == {"error", "message"}
