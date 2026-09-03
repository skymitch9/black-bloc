from __future__ import annotations

import pytest

from black_bloc.cogs.moderation.honeypot import get_hit, record_hit

ROUTES = [
    ("GET", "/api/honeypot/hits", None),
    ("POST", "/api/honeypot/hits/1/ban", None),
    ("POST", "/api/honeypot/setup", {}),
]


async def a_hit(web, wf, *, action: str = "would_ban", user_id: int = 21) -> int:
    return await record_hit(
        web.db,
        wf.GUILD_ID,
        user_id,
        wf.OTHER_CHANNEL_ID,
        999,
        "buy my coins",
        "shadow",
        action,
    )


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_honeypot_route_needs_a_session(client, method, route, payload):
    assert client.request(method, route, json=payload).status_code == 401


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_honeypot_route_refuses_a_non_staff_visitor(
    client, sign_in, method, route, payload
):
    sign_in(client, uid=1234, staff=False)
    assert client.request(method, route, json=payload).status_code == 403


async def test_hits_come_back_newest_first_with_names(client, sign_in, web, guild, wf):
    wf.member(guild, 21, name="spammer")
    await a_hit(web, wf)
    await a_hit(web, wf, action="banned")
    sign_in(client)

    rows = client.get("/api/honeypot/hits", params={"limit": 5}).json()

    assert [row["action"] for row in rows] == ["banned", "would_ban"]
    assert rows[0]["user_name"] == "Spammer"
    assert rows[0]["channel_name"] == "#general"
    assert rows[0]["content"] == "buy my coins"


async def test_ban_now_bans_the_account_and_marks_the_hit(client, sign_in, web, guild, wf):
    wf.member(guild, 21, name="spammer")
    hit_id = await a_hit(web, wf)
    sign_in(client)

    response = client.post(f"/api/honeypot/hits/{hit_id}/ban")

    assert response.status_code == 200
    assert guild.bans and guild.bans[0][0] == 21
    assert (await get_hit(web.db, hit_id))["action"] == "banned"
    assert (await wf.one_web_row(web.db, "web.honeypot.banned"))["hit_id"] == hit_id


async def test_ban_now_is_refused_in_test_mode_with_the_slash_commands_sentence(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="spammer")
    hit_id = await a_hit(web, wf)
    web.guard = wf.Guard()
    sign_in(client)

    response = client.post(f"/api/honeypot/hits/{hit_id}/ban")

    assert response.status_code == 409
    assert response.json()["error"] == "test_mode"
    assert "test mode" in response.json()["message"]
    assert guild.bans == []
    assert (await get_hit(web.db, hit_id))["action"] == "would_ban"
    kinds = await wf.kinds_in(web.db)
    assert "honeypot.would_ban" in kinds and "honeypot.banned" not in kinds


async def test_banning_the_same_hit_twice_says_so(client, sign_in, web, guild, wf):
    wf.member(guild, 21, name="spammer")
    hit_id = await a_hit(web, wf, action="banned")
    sign_in(client)

    response = client.post(f"/api/honeypot/hits/{hit_id}/ban")

    assert response.status_code == 409
    assert response.json()["error"] == "already_banned"
    assert guild.bans == []


def test_a_hit_that_is_gone_is_a_404(client, sign_in):
    sign_in(client)
    response = client.post("/api/honeypot/hits/4242/ban")
    assert response.status_code == 404
    assert "no record" in response.json()["message"]


async def test_setup_makes_the_trap_and_records_the_channel(client, sign_in, web, guild, wf):
    sign_in(client)

    response = client.post("/api/honeypot/setup", json={})

    assert response.status_code == 200
    made = guild.created[-1]
    assert web.store.get(wf.GUILD_ID, "honeypot_channel_ids") == [made.id]
    assert made.messages and made.messages[0].pinned is True
    await wf.one_web_row(web.db, "web.honeypot.setup")


async def test_a_second_trap_is_refused(client, sign_in, web, wf):
    sign_in(client)
    client.post("/api/honeypot/setup", json={})

    again = client.post("/api/honeypot/setup", json={})

    assert again.status_code == 409
    assert again.json()["error"] == "already_a_trap"


async def test_the_trap_notice_is_not_posted_in_test_mode(client, sign_in, web, guild, wf):
    web.guard = wf.Guard()
    sign_in(client)

    response = client.post("/api/honeypot/setup", json={})

    assert response.status_code == 200
    assert "Post it by hand" in response.json()["message"]
    assert guild.created[-1].messages == []
