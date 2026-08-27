from __future__ import annotations

import pytest

from black_bloc.cogs.community.tempvoice import add_channel

ROUTES = [
    ("GET", "/api/tempvoice/channels", None),
    ("POST", "/api/tempvoice/setup", {}),
]


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_tempvoice_route_needs_a_session(client, method, route, payload):
    assert client.request(method, route, json=payload).status_code == 401


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_tempvoice_route_refuses_a_non_staff_visitor(
    client, sign_in, method, route, payload
):
    sign_in(client, uid=1234, staff=False)
    assert client.request(method, route, json=payload).status_code == 403


async def test_live_channels_come_back_with_the_owner_resolved(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    spawned = guild.channels[-1]
    await add_channel(web.db, spawned.id, wf.GUILD_ID, 21, wf.VOICE_CHANNEL_ID)
    await add_channel(web.db, 4242, wf.GUILD_ID, 21, wf.VOICE_CHANNEL_ID)
    sign_in(client)

    rows = {row["channel_id"]: row for row in client.get("/api/tempvoice/channels").json()}

    assert rows[str(spawned.id)]["owner_name"] == "Ada"
    assert rows[str(spawned.id)]["gone"] is False
    assert rows["4242"]["gone"] is True
    assert rows["4242"]["name"] is None


async def test_setup_makes_the_lobby_and_records_the_setting(client, sign_in, web, guild, wf):
    sign_in(client)

    response = client.post("/api/tempvoice/setup", json={"name": "join to talk"})

    assert response.status_code == 200
    made = guild.created[-1]
    assert made.name == "join to talk"
    assert web.store.get(wf.GUILD_ID, "tempvoice_creator_ids") == [made.id]
    kinds = await wf.kinds_in(web.db)
    assert "tempvoice.setup" in kinds and "web.tempvoice.setup" in kinds


async def test_a_second_lobby_is_refused_with_the_first_one_named(client, sign_in, web, wf):
    sign_in(client)
    client.post("/api/tempvoice/setup", json={})

    again = client.post("/api/tempvoice/setup", json={})

    assert again.status_code == 409
    assert again.json()["error"] == "already_a_lobby"
    assert "already has" in again.json()["message"]


async def test_setup_in_test_mode_puts_it_in_the_test_category(client, sign_in, web, guild, wf):
    web.guard = wf.Guard()
    sign_in(client)

    response = client.post("/api/tempvoice/setup", json={})

    assert response.status_code == 200
    assert "Test mode is on" in response.json()["message"]
    assert guild.created[-1].kwargs["category"] is guild.get_channel(wf.CATEGORY_ID)
