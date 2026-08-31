from __future__ import annotations

import discord
import pytest

from black_bloc.cogs.community.tempvoice import add_channel, get_prefs

ROOM = "/api/tempvoice/rooms/{channel_id}"

ROUTES = [
    ("GET", "/api/tempvoice/channels", None),
    ("POST", "/api/tempvoice/setup", {}),
    ("POST", "/api/tempvoice/forget", {"channel_id": "1"}),
    ("POST", "/api/tempvoice/rooms/1/rename", {"name": "quiet"}),
    ("POST", "/api/tempvoice/rooms/1/limit", {"limit": 4}),
    ("POST", "/api/tempvoice/rooms/1/lock", {"locked": True}),
    ("POST", "/api/tempvoice/rooms/1/hide", {"hidden": True}),
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


@pytest.fixture
async def open_room(client, sign_in, web, guild, wf):
    """One live temp channel, owned by a member, with the staffer signed in."""
    wf.member(guild, 21, name="ada")
    spawned = guild.get_channel(wf.VOICE_CHANNEL_ID)
    await add_channel(web.db, spawned.id, wf.GUILD_ID, 21, 4242)
    sign_in(client)
    return spawned


async def test_the_open_list_carries_what_each_room_is_set_to(client, open_room):
    open_room.user_limit = 5

    rows = client.get("/api/tempvoice/channels").json()

    assert rows[0]["user_limit"] == 5
    assert rows[0]["locked"] is False and rows[0]["hidden"] is False


async def test_rename_edits_discord_remembers_it_and_logs_it_as_web(
    client, web, wf, open_room
):
    response = client.post(ROOM.format(channel_id=open_room.id) + "/rename", json={"name": "quiet"})

    assert response.status_code == 200
    assert open_room.name == "quiet"
    assert response.json()["room"]["name"] == "quiet"
    assert "quiet" in response.json()["message"]
    prefs = await get_prefs(web.db, 21)
    assert prefs["name"] == "quiet"
    assert "web.tempvoice.rename" in await wf.kinds_in(web.db)


async def test_the_web_rename_line_says_it_came_from_the_website(client, web, open_room):
    client.post(ROOM.format(channel_id=open_room.id) + "/rename", json={"name": "quiet"})

    cur = await web.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = 'web.tempvoice.rename'"
    )
    row = await cur.fetchone()
    assert '"via": "website"' in row["details"]


async def test_rename_with_nothing_typed_refuses_in_words(client, open_room):
    response = client.post(ROOM.format(channel_id=open_room.id) + "/rename", json={"name": "  "})

    assert response.status_code == 400
    assert "needs a name" in response.json()["message"]


async def test_a_rename_discord_refuses_comes_back_as_a_sentence(client, web, wf, open_room):
    open_room.edit_raises = discord.HTTPException(
        type("R", (), {"status": 403, "reason": "no"})(), "nope"
    )

    response = client.post(ROOM.format(channel_id=open_room.id) + "/rename", json={"name": "quiet"})

    assert response.status_code == 409
    assert "Manage Channels" in response.json()["message"]
    assert "web.tempvoice.rename_failed" in await wf.kinds_in(web.db)


async def test_limit_caps_the_room_and_remembers_it(client, web, open_room):
    response = client.post(ROOM.format(channel_id=open_room.id) + "/limit", json={"limit": 4})

    assert response.status_code == 200
    assert open_room.user_limit == 4
    assert response.json()["room"]["user_limit"] == 4
    prefs = await get_prefs(web.db, 21)
    assert prefs["user_limit"] == 4


@pytest.mark.parametrize("given", ["-1", "100", "lots", ""])
async def test_a_limit_discord_would_not_take_refuses_in_words(client, open_room, given):
    response = client.post(ROOM.format(channel_id=open_room.id) + "/limit", json={"limit": given})

    assert response.status_code == 400
    assert "0 to 99" in response.json()["message"]


async def test_lock_and_unlock_go_through_the_same_path_the_panel_uses(client, web, open_room):
    locked = client.post(ROOM.format(channel_id=open_room.id) + "/lock", json={"locked": True})

    assert locked.status_code == 200
    assert locked.json()["room"]["locked"] is True
    prefs = await get_prefs(web.db, 21)
    assert prefs["locked"] == 1

    opened = client.post(ROOM.format(channel_id=open_room.id) + "/lock", json={"locked": False})

    assert opened.json()["room"]["locked"] is False
    assert "Unlocked" in opened.json()["message"]


async def test_asking_for_the_state_it_is_already_in_says_so_and_spends_no_call(
    client, open_room
):
    client.post(ROOM.format(channel_id=open_room.id) + "/lock", json={"locked": True})

    again = client.post(ROOM.format(channel_id=open_room.id) + "/lock", json={"locked": True})

    assert again.status_code == 200
    assert "already locked" in again.json()["message"]


async def test_hide_and_show_flip_the_everyone_overwrite(client, web, wf, open_room):
    hidden = client.post(ROOM.format(channel_id=open_room.id) + "/hide", json={"hidden": True})

    assert hidden.json()["room"]["hidden"] is True
    assert "web.tempvoice.hide" in await wf.kinds_in(web.db)

    shown = client.post(ROOM.format(channel_id=open_room.id) + "/hide", json={"hidden": False})

    assert shown.json()["room"]["hidden"] is False


async def test_a_channel_the_bot_does_not_track_refuses_in_words(client, sign_in, wf):
    sign_in(client)

    response = client.post(ROOM.format(channel_id=wf.VOICE_CHANNEL_ID) + "/lock", json={})

    assert response.status_code == 404
    assert "not keeping track" in response.json()["message"]


async def test_a_room_outside_the_test_category_is_refused_while_test_mode_is_on(
    client, web, wf, open_room
):
    web.guard = wf.Guard()
    open_room.category_id = None

    response = client.post(ROOM.format(channel_id=open_room.id) + "/rename", json={"name": "x"})

    assert response.status_code == 409
    assert "test mode" in response.json()["message"]


async def test_a_room_in_the_test_category_is_allowed_while_test_mode_is_on(
    client, web, wf, open_room
):
    web.guard = wf.Guard()
    open_room.category_id = wf.CATEGORY_ID

    response = client.post(ROOM.format(channel_id=open_room.id) + "/rename", json={"name": "x"})

    assert response.status_code == 200
