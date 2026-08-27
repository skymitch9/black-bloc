from __future__ import annotations

import pytest

from black_bloc.cogs.community.role_menus import get_menu, get_options

ROUTES = [
    ("GET", "/api/rolemenus", None),
    ("POST", "/api/rolemenus", {"name": "colours", "title": "Colours"}),
    ("PUT", "/api/rolemenus/colours", {"title": "Colours"}),
    ("DELETE", "/api/rolemenus/colours", None),
    ("POST", "/api/rolemenus/colours/post", {"channel_id": "500"}),
]


def call(client, method, route, payload):
    return client.request(method, route, json=payload)


async def a_menu(client, wf, name: str = "colours") -> dict:
    return client.post(
        "/api/rolemenus",
        json={
            "name": name,
            "title": "Pick a colour",
            "description": "one each",
            "mode": "multiple",
        },
    ).json()


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_role_menu_route_needs_a_session(client, method, route, payload):
    response = call(client, method, route, payload)
    assert response.status_code == 401
    assert response.json()["error"] == "not_signed_in"


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_role_menu_route_refuses_a_non_staff_visitor(
    client, sign_in, method, route, payload
):
    sign_in(client, uid=1234, staff=False)
    response = call(client, method, route, payload)
    assert response.status_code == 403
    assert response.json()["error"] == "not_staff"


async def test_a_menu_is_created_listed_and_logged(client, sign_in, web, wf):
    sign_in(client)

    created = await a_menu(client, wf)

    assert created["name"] == "colours" and created["options"] == []
    listed = client.get("/api/rolemenus").json()
    assert [row["name"] for row in listed] == ["colours"]
    assert "web.rolemenu.create" in await wf.kinds_in(web.db)


async def test_a_second_menu_with_the_same_name_is_refused_with_a_sentence(client, sign_in, wf):
    sign_in(client)
    await a_menu(client, wf)

    response = client.post("/api/rolemenus", json={"name": "colours", "title": "Again"})

    assert response.status_code == 400
    assert response.json()["error"] == "name_taken"
    assert "already has a role menu" in response.json()["message"]


def test_a_menu_needs_a_name_and_a_heading(client, sign_in):
    sign_in(client)
    assert client.post("/api/rolemenus", json={"name": "x"}).status_code == 400
    assert client.post("/api/rolemenus", json={"title": "x"}).status_code == 400


def test_an_unknown_mode_is_refused_by_name(client, sign_in):
    sign_in(client)
    response = client.post(
        "/api/rolemenus", json={"name": "c", "title": "C", "mode": "sideways"}
    )
    assert response.status_code == 400
    assert "multiple, single, staff" in response.json()["message"]


async def test_the_put_body_is_the_whole_option_list(client, sign_in, web, wf):
    sign_in(client)
    await a_menu(client, wf)

    first = client.put(
        "/api/rolemenus/colours",
        json={
            "title": "Pick two",
            "options": [
                {"role_id": str(wf.PLAIN_ROLE_ID), "label": "Member", "emoji": "🟦"},
                {"role_id": str(wf.STAFF_ROLE_ID), "label": "Staff"},
            ],
        },
    ).json()

    assert first["title"] == "Pick two"
    assert [row["role_id"] for row in first["options"]] == [
        str(wf.PLAIN_ROLE_ID),
        str(wf.STAFF_ROLE_ID),
    ]
    assert first["options"][0]["emoji"] == "🟦"

    second = client.put(
        "/api/rolemenus/colours",
        json={"options": [{"role_id": str(wf.STAFF_ROLE_ID), "label": "Staff"}]},
    ).json()

    assert [row["role_id"] for row in second["options"]] == [str(wf.STAFF_ROLE_ID)]
    menu = await get_menu(web.db, wf.GUILD_ID, "colours")
    assert len(await get_options(web.db, menu["id"])) == 1


def test_a_role_that_is_gone_leaves_the_menu_alone(client, sign_in, wf):
    sign_in(client)
    client.post("/api/rolemenus", json={"name": "colours", "title": "C"})

    response = client.put(
        "/api/rolemenus/colours", json={"options": [{"role_id": "999999", "label": "Ghost"}]}
    )

    assert response.status_code == 400
    assert response.json()["error"] == "no_such_role"
    assert client.get("/api/rolemenus").json()[0]["options"] == []


def test_a_menu_nobody_has_is_a_404_with_a_sentence(client, sign_in):
    sign_in(client)
    for method, route in (
        ("PUT", "/api/rolemenus/ghost"),
        ("DELETE", "/api/rolemenus/ghost"),
        ("POST", "/api/rolemenus/ghost/post"),
    ):
        response = client.request(method, route, json={})
        assert response.status_code == 404
        assert "no role menu called" in response.json()["message"]


async def test_deleting_a_menu_says_so_and_logs_it(client, sign_in, web, wf):
    sign_in(client)
    await a_menu(client, wf)

    response = client.delete("/api/rolemenus/colours")

    assert response.json() == {"deleted": True, "name": "colours"}
    assert client.get("/api/rolemenus").json() == []
    assert "web.rolemenu.delete" in await wf.kinds_in(web.db)


async def test_posting_a_panel_puts_it_in_the_channel_and_remembers_the_message(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await a_menu(client, wf)
    client.put(
        "/api/rolemenus/colours",
        json={"options": [{"role_id": str(wf.PLAIN_ROLE_ID), "label": "Member"}]},
    )

    response = client.post(
        "/api/rolemenus/colours/post", json={"channel_id": str(wf.TEST_CHANNEL_ID)}
    )

    assert response.status_code == 200
    channel = guild.get_channel(wf.TEST_CHANNEL_ID)
    assert channel.messages and "embed" in channel.messages[0].kwargs
    assert response.json()["message_id"] == str(channel.messages[0].id)
    menu = await get_menu(web.db, wf.GUILD_ID, "colours")
    assert menu["message_id"] == channel.messages[0].id
    assert "web.rolemenu.post" in await wf.kinds_in(web.db)


async def test_posting_outside_the_test_channel_is_refused_while_the_guard_is_on(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await a_menu(client, wf)
    client.put(
        "/api/rolemenus/colours",
        json={"options": [{"role_id": str(wf.PLAIN_ROLE_ID), "label": "Member"}]},
    )
    web.guard = wf.Guard()

    response = client.post(
        "/api/rolemenus/colours/post", json={"channel_id": str(wf.OTHER_CHANNEL_ID)}
    )

    assert response.status_code == 409
    assert response.json()["error"] == "test_mode"
    assert "test mode" in response.json()["message"]
    assert guild.get_channel(wf.OTHER_CHANNEL_ID).messages == []
    assert "web.rolemenu.post" not in await wf.kinds_in(web.db)

    allowed = client.post(
        "/api/rolemenus/colours/post", json={"channel_id": str(wf.TEST_CHANNEL_ID)}
    )
    assert allowed.status_code == 200


async def test_a_staff_menu_and_an_empty_menu_are_not_posted(client, sign_in, wf):
    sign_in(client)
    client.post("/api/rolemenus", json={"name": "runner", "title": "R", "mode": "staff"})
    client.post("/api/rolemenus", json={"name": "empty", "title": "E"})

    staff_menu = client.post("/api/rolemenus/runner/post", json={})
    empty = client.post("/api/rolemenus/empty/post", json={})

    assert staff_menu.status_code == 400 and "staff-assigned" in staff_menu.json()["message"]
    assert empty.status_code == 400 and "no roles on it yet" in empty.json()["message"]


async def test_the_default_channel_setting_is_used_when_none_is_given(client, sign_in, web, wf):
    sign_in(client)
    await web.store.set(wf.GUILD_ID, "role_menu_channel_id", wf.TEST_CHANNEL_ID)
    await a_menu(client, wf)
    client.put(
        "/api/rolemenus/colours",
        json={"options": [{"role_id": str(wf.PLAIN_ROLE_ID), "label": "Member"}]},
    )

    response = client.post("/api/rolemenus/colours/post", json={})

    assert response.json()["channel_id"] == str(wf.TEST_CHANNEL_ID)
