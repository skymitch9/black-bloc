from __future__ import annotations

import pytest

from black_bloc import ninja
from black_bloc import ninja_store as store

ROUTES = [
    ("GET", "/api/ninja", None),
    ("POST", "/api/ninja", {"user_ids": ["21"], "channel_id": "501", "posts": 1}),
    ("DELETE", "/api/ninja/1", None),
]


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_ninja_route_needs_a_session(client, method, route, payload):
    assert client.request(method, route, json=payload).status_code == 401


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_ninja_route_refuses_a_non_staff_visitor(client, sign_in, method, route, payload):
    sign_in(client, uid=1234, staff=False)
    assert client.request(method, route, json=payload).status_code == 403


async def test_marking_from_the_page_lists_the_mark_with_names_and_logs_once(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="pt")
    sign_in(client)

    response = client.post(
        "/api/ninja",
        json={"user_ids": ["21"], "channel_id": str(wf.OTHER_CHANNEL_ID), "posts": "2"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "@Pt marked in #general · 2 post(s)."
    found = client.get("/api/ninja").json()
    assert found["mode"] == "on" and found["emoji"] == "\U0001f977\U0001f3ff"
    assert (found["default_posts"], found["default_minutes"]) == ("1", "")
    [row] = found["active"]
    assert (row["user_name"], row["channel_name"], row["posts_left"]) == ("Pt", "#general", 2)
    assert row["made_by"] == "7" and found["ended"] == []
    kinds = await wf.kinds_in(web.db)
    assert kinds.count("web.ninja.marked") == 1 and "ninja.marked" not in kinds
    assert ninja.marked(web)[(wf.GUILD_ID, 21)] == {wf.OTHER_CHANNEL_ID}


@pytest.mark.parametrize(
    ("payload", "status", "said"),
    [
        ({"user_ids": [], "channel_id": "501", "posts": 1}, 400, "Nobody was picked"),
        ({"user_ids": ["21"], "channel_id": "", "posts": 1}, 400, "No channel was picked"),
        ({"user_ids": ["21"], "channel_id": "501"}, 400, "Neither posts nor minutes"),
        ({"user_ids": ["21"], "channel_id": "501", "minutes": "x"}, 400, "**x** is not a number"),
        ({"user_ids": "21", "channel_id": "501", "posts": 1}, 400, "Nobody was picked"),
    ],
)
def test_a_mark_the_page_cannot_make_is_refused_in_words(client, sign_in, payload, status, said):
    sign_in(client)
    response = client.post("/api/ninja", json=payload)
    assert response.status_code == status
    assert said in response.json()["message"]


def test_a_second_mark_on_the_same_member_and_channel_is_refused(client, sign_in):
    sign_in(client)
    body = {"user_ids": ["21"], "channel_id": "501", "posts": 1}
    assert client.post("/api/ninja", json=body).status_code == 200
    again = client.post("/api/ninja", json=body)
    assert again.status_code == 409
    assert "End that mark first" in again.json()["message"]


async def test_ending_from_the_page_ends_it_once(client, sign_in, web, wf):
    sign_in(client)
    client.post("/api/ninja", json={"user_ids": ["21"], "channel_id": "501", "minutes": 30})
    [row] = client.get("/api/ninja").json()["active"]

    response = client.delete(f"/api/ninja/{row['id']}")
    again = client.delete(f"/api/ninja/{row['id']}")

    assert response.status_code == 200 and "is ended" in response.json()["message"]
    assert again.status_code == 409
    found = client.get("/api/ninja").json()
    assert found["active"] == [] and found["ended"][0]["ended_because"] == store.STAFF
    assert (await wf.kinds_in(web.db)).count("web.ninja.ended") == 1


def test_a_mark_id_that_is_not_a_number_is_refused(client, sign_in):
    sign_in(client)
    assert client.delete("/api/ninja/abc").status_code == 400
