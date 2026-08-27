from __future__ import annotations

import pytest

from black_bloc.cogs.community.tempvoice import add_channel

ROUTES = [
    ("GET", "/api/tempvoice/channels", None),
    ("POST", "/api/tempvoice/setup", {}),
    ("POST", "/api/tempvoice/forget", {"channel_id": "1"}),
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


async def test_a_second_setup_repairs_the_lobby_instead_of_making_another(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    client.post("/api/tempvoice/setup", json={})
    made = len(guild.created)

    again = client.post("/api/tempvoice/setup", json={})

    assert again.status_code == 200
    assert again.json()["outcome"] == "repaired"
    assert "repaired" in again.json()["message"]
    assert len(guild.created) == made


async def test_setup_in_test_mode_puts_it_in_the_test_category(client, sign_in, web, guild, wf):
    web.guard = wf.Guard()
    sign_in(client)

    response = client.post("/api/tempvoice/setup", json={})

    assert response.status_code == 200
    assert "Test mode is on" in response.json()["message"]
    assert guild.created[-1].kwargs["category"] is guild.get_channel(wf.CATEGORY_ID)


async def test_forget_drops_one_lobby_and_leaves_the_rest(client, sign_in, web, wf):
    await web.store.set(wf.GUILD_ID, "tempvoice_creator_ids", [wf.VOICE_CHANNEL_ID, 4242], by=7)
    sign_in(client)

    response = client.post(
        "/api/tempvoice/forget", json={"channel_id": str(wf.VOICE_CHANNEL_ID)}
    )

    assert response.status_code == 200
    assert response.json()["forgotten"] is True
    assert str(wf.VOICE_CHANNEL_ID) in response.json()["message"]
    assert web.store.get(wf.GUILD_ID, "tempvoice_creator_ids") == [4242]
    kinds = await wf.kinds_in(web.db)
    assert "tempvoice.creator_removed" in kinds and "web.tempvoice.forget" in kinds


async def test_forget_says_in_words_that_a_channel_was_never_a_lobby(client, sign_in, web, wf):
    await web.store.set(wf.GUILD_ID, "tempvoice_creator_ids", [wf.VOICE_CHANNEL_ID], by=7)
    sign_in(client)

    response = client.post("/api/tempvoice/forget", json={"channel_id": "4242"})

    assert response.status_code == 404
    assert "nothing was forgotten" in response.json()["message"]
    assert web.store.get(wf.GUILD_ID, "tempvoice_creator_ids") == [wf.VOICE_CHANNEL_ID]


def test_forget_refuses_something_that_is_not_an_id_in_words(client, sign_in):
    sign_in(client)

    response = client.post("/api/tempvoice/forget", json={"channel_id": "the lobby"})

    assert response.status_code == 400
    assert "not an id" in response.json()["message"]
