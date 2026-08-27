from __future__ import annotations

import pytest

from black_bloc.cogs.content.golive import get_link, set_link, set_optout

ROUTES = [
    ("GET", "/api/golive/links"),
    ("DELETE", "/api/golive/links/7"),
    ("GET", "/api/golive/optouts"),
    ("GET", "/api/golive/sessions"),
]


@pytest.mark.parametrize(("method", "route"), ROUTES)
def test_every_golive_route_needs_a_session(client, method, route):
    assert client.request(method, route).status_code == 401


@pytest.mark.parametrize(("method", "route"), ROUTES)
def test_every_golive_route_refuses_a_non_staff_visitor(client, sign_in, method, route):
    sign_in(client, uid=1234, staff=False)
    assert client.request(method, route).status_code == 403


async def test_links_come_back_with_the_member_name_resolved(client, sign_in, web, guild, wf):
    wf.member(guild, 21, name="ada")
    await set_link(web.db, 21, "adastreams", "t-1")
    sign_in(client)

    rows = client.get("/api/golive/links").json()

    assert rows[0]["user_id"] == "21"
    assert rows[0]["user_name"] == "Ada"
    assert rows[0]["twitch_login"] == "adastreams"


async def test_an_unlink_removes_the_row_and_leaves_a_web_line(client, sign_in, web, wf):
    await set_link(web.db, 21, "adastreams")
    sign_in(client)

    response = client.delete("/api/golive/links/21")

    assert response.json() == {"unlinked": True, "user_id": "21"}
    assert await get_link(web.db, 21) is None
    assert "web.golive.unlink" in await wf.kinds_in(web.db)


def test_unlinking_somebody_who_is_not_linked_says_so(client, sign_in):
    sign_in(client)
    response = client.delete("/api/golive/links/21")
    assert response.status_code == 404
    assert "nothing to unlink" in response.json()["message"]


def test_an_id_that_is_not_a_number_is_a_sentence(client, sign_in):
    sign_in(client)
    response = client.delete("/api/golive/links/nobody")
    assert response.status_code == 400
    assert "nobody" in response.json()["message"]


async def test_optouts_and_sessions_are_listed_newest_first(client, sign_in, web, guild, wf):
    wf.member(guild, 21, name="ada")
    await set_optout(web.db, 21)
    for n in range(3):
        await web.db.conn.execute(
            "INSERT INTO golive_sessions(guild_id, user_id, source, started_at, ended_at, mode) "
            "VALUES (?, 21, 'twitch', ?, ?, 'on')",
            (
                wf.GUILD_ID,
                f"2026-08-2{n}T00:00:00+00:00",
                f"2026-08-2{n}T01:00:00+00:00",
            ),
        )
    await web.db.conn.commit()
    sign_in(client)

    optouts = client.get("/api/golive/optouts").json()
    sessions = client.get("/api/golive/sessions", params={"limit": 2}).json()

    assert optouts[0]["user_id"] == "21" and optouts[0]["user_name"] == "Ada"
    assert len(sessions) == 2
    assert sessions[0]["started_at"] > sessions[1]["started_at"]
    assert sessions[0]["user_name"] == "Ada"


async def test_the_session_limit_is_clamped(client, sign_in, web):
    sign_in(client)
    assert client.get("/api/golive/sessions", params={"limit": 10000}).status_code == 200
    assert client.get("/api/golive/sessions", params={"limit": 0}).status_code == 200
