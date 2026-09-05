from __future__ import annotations

import discord
import pytest

from black_bloc import rolegrants as grants
from black_bloc.cogs.community.role_menus import (
    DESCRIPTION_MAX,
    LABEL_MAX,
    OPTIONS_MAX,
    TITLE_MAX,
    get_menu,
    get_options,
)

MEMBER = 900

ROUTES = [
    ("GET", "/api/rolemenus", None),
    ("POST", "/api/rolemenus", {"name": "colours", "title": "Colours"}),
    ("PUT", "/api/rolemenus/colours", {"title": "Colours"}),
    ("DELETE", "/api/rolemenus/colours", None),
    ("POST", "/api/rolemenus/colours/post", {"channel_id": "500"}),
    ("POST", "/api/rolemenus/colours/unpost", None),
    ("POST", "/api/rolemenus/seed", None),
    ("POST", "/api/rolemenus/colours/assign", {"user_id": "900", "role_ids": []}),
]


def call(client, method, route, payload):
    return client.request(method, route, json=payload)


async def menus_on(web, wf) -> None:
    """`rolemenu_mode` ships off, and a panel is not posted while members cannot pick."""
    await web.store.set(wf.GUILD_ID, "rolemenu_mode", "on")


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
    assert "web.role_menu.create" in await wf.kinds_in(web.db)


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
        ("POST", "/api/rolemenus/ghost/unpost"),
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
    assert "web.role_menu.delete" in await wf.kinds_in(web.db)


async def test_posting_a_panel_puts_it_in_the_channel_and_remembers_the_message(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await menus_on(web, wf)
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
    assert "web.role_menu.post" in await wf.kinds_in(web.db)


async def test_unpost_deletes_the_message_and_forgets_it(client, sign_in, web, guild, wf):
    sign_in(client)
    await a_posted_menu(client, web, wf, wf.TEST_CHANNEL_ID)
    channel = guild.get_channel(wf.TEST_CHANNEL_ID)
    assert channel.messages

    response = client.post("/api/rolemenus/colours/unpost", json={})

    assert response.status_code == 200
    assert response.json()["unposted"] is True
    assert "panel is down" in response.json()["message"]
    assert channel.messages == []
    menu = await get_menu(web.db, wf.GUILD_ID, "colours")
    assert menu["message_id"] is None
    assert menu["channel_id"] == wf.TEST_CHANNEL_ID
    assert "web.role_menu.unposted" in await wf.kinds_in(web.db)


async def test_seed_creates_the_defaults_and_says_what_it_did(client, sign_in, web, wf):
    sign_in(client)

    response = client.post("/api/rolemenus/seed", json={})

    assert response.status_code == 200
    body = response.json()
    assert "pronouns" in body["created"] and body["skipped"] == []
    assert "Created: pronouns" in body["message"]
    assert {menu["name"] for menu in client.get("/api/rolemenus").json()} >= set(body["created"])
    assert "web.role_menu.seeded" in await wf.kinds_in(web.db)


async def test_seeding_twice_rewrites_nothing_and_says_which_were_already_there(
    client, sign_in, web, wf
):
    sign_in(client)
    await a_menu(client, wf, "pronouns")
    client.put(
        "/api/rolemenus/pronouns",
        json={"options": [{"role_id": str(wf.PLAIN_ROLE_ID), "label": "Kept"}]},
    )

    body = client.post("/api/rolemenus/seed", json={}).json()

    assert "pronouns" in body["skipped"] and "pronouns" not in body["created"]
    assert "Already there, left alone: pronouns" in body["message"]
    menu = await get_menu(web.db, wf.GUILD_ID, "pronouns")
    kept = await get_options(web.db, menu["id"])
    assert [row["label"] for row in kept] == ["Kept"]

    again = client.post("/api/rolemenus/seed", json={}).json()
    assert again["created"] == [] and "pronouns" in again["skipped"]


async def a_staff_menu(client, web, wf, name: str = "runner") -> None:
    await menus_on(web, wf)
    await a_menu(client, wf, name)
    client.put(
        f"/api/rolemenus/{name}",
        json={
            "mode": "staff",
            "options": [{"role_id": str(wf.STAFF_ROLE_ID), "label": "Runner"}],
        },
    )


async def test_assign_gives_the_role_through_the_same_path_as_the_picker(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await a_staff_menu(client, web, wf)
    member = wf.member(guild, MEMBER, name="ada")

    response = client.post(
        "/api/rolemenus/runner/assign",
        json={"user_id": str(MEMBER), "role_ids": [str(wf.STAFF_ROLE_ID)]},
    )

    assert response.status_code == 200
    assert "Added: Runner" in response.json()["message"]
    assert wf.STAFF_ROLE_ID in [role.id for role in member.roles]
    grant = await grants.open_grant(web.db, wf.GUILD_ID, MEMBER, wf.STAFF_ROLE_ID)
    assert grant is not None and grant["source"] == grants.STAFF
    assert "web.role_menu.assign" in await wf.kinds_in(web.db)


async def test_assign_with_remove_takes_the_role_off_again(client, sign_in, web, guild, wf):
    sign_in(client)
    await a_staff_menu(client, web, wf)
    member = wf.member(guild, MEMBER, name="ada")
    client.post(
        "/api/rolemenus/runner/assign",
        json={"user_id": str(MEMBER), "role_ids": [str(wf.STAFF_ROLE_ID)]},
    )

    response = client.post(
        "/api/rolemenus/runner/assign",
        json={"user_id": str(MEMBER), "role_ids": [str(wf.STAFF_ROLE_ID)], "remove": True},
    )

    assert response.status_code == 200
    assert response.json()["assigned"] is False
    assert "Removed: Runner" in response.json()["message"]
    assert wf.STAFF_ROLE_ID not in [role.id for role in member.roles]
    assert "web.role_menu.unassign" in await wf.kinds_in(web.db)


async def test_assign_only_ever_touches_the_roles_that_menu_owns(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await a_staff_menu(client, web, wf)
    member = wf.member(guild, MEMBER, name="ada")
    member.roles = [*member.roles, guild.get_role(wf.ADMIN_ROLE_ID)]

    client.post(
        "/api/rolemenus/runner/assign",
        json={"user_id": str(MEMBER), "role_ids": [str(wf.STAFF_ROLE_ID)]},
    )

    held = [role.id for role in member.roles]
    assert wf.ADMIN_ROLE_ID in held and wf.STAFF_ROLE_ID in held


async def test_assigning_what_they_already_have_says_so_and_changes_nothing(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await a_staff_menu(client, web, wf)
    member = wf.member(guild, MEMBER, name="ada")
    client.post(
        "/api/rolemenus/runner/assign",
        json={"user_id": str(MEMBER), "role_ids": [str(wf.STAFF_ROLE_ID)]},
    )
    before = len(member.edits)

    again = client.post(
        "/api/rolemenus/runner/assign",
        json={"user_id": str(MEMBER), "role_ids": [str(wf.STAFF_ROLE_ID)]},
    )

    assert again.status_code == 200
    assert "already has exactly those roles" in again.json()["message"]
    assert len(member.edits) == before


async def test_assign_refuses_a_member_the_bot_cannot_see_and_an_empty_menu(
    client, sign_in, web, wf
):
    sign_in(client)
    await a_staff_menu(client, web, wf)
    await a_menu(client, wf, "empty")

    stranger = client.post(
        "/api/rolemenus/runner/assign", json={"user_id": "4242", "role_ids": []}
    )
    empty = client.post("/api/rolemenus/empty/assign", json={"user_id": str(MEMBER)})

    assert stranger.status_code == 404 and "not somebody Black Bloc can see" in (
        stranger.json()["message"]
    )
    assert empty.status_code == 400 and "nothing to hand out" in empty.json()["message"]


async def test_assign_is_refused_while_role_menus_are_turned_off(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await a_staff_menu(client, web, wf)
    wf.member(guild, MEMBER, name="ada")
    await web.store.set(wf.GUILD_ID, "rolemenu_mode", "off")

    response = client.post(
        "/api/rolemenus/runner/assign",
        json={"user_id": str(MEMBER), "role_ids": [str(wf.STAFF_ROLE_ID)]},
    )

    assert response.status_code == 409
    assert response.json()["error"] == "rolemenu_off"


async def test_a_role_change_discord_refuses_comes_back_as_a_sentence(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await a_staff_menu(client, web, wf)
    member = wf.member(guild, MEMBER, name="ada")
    member.edit_raises = discord.HTTPException(
        type("Refused", (), {"status": 403, "reason": "refused"})(), "no"
    )

    response = client.post(
        "/api/rolemenus/runner/assign",
        json={"user_id": str(MEMBER), "role_ids": [str(wf.STAFF_ROLE_ID)]},
    )

    assert response.status_code == 409
    assert response.json()["error"] == "role_refused"


async def test_unposting_a_menu_with_no_panel_refuses_in_words(client, sign_in, web, wf):
    sign_in(client)
    await a_menu(client, wf)

    response = client.post("/api/rolemenus/colours/unpost", json={})

    assert response.status_code == 400
    assert "nothing to take down" in response.json()["message"]


async def test_unpost_of_a_panel_outside_the_test_channel_is_refused_and_shadow_logged(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await a_posted_menu(client, web, wf, wf.TEST_CHANNEL_ID)
    await web.db.conn.execute(
        "UPDATE role_menus SET channel_id = ? WHERE name = 'colours'", (wf.OTHER_CHANNEL_ID,)
    )
    await web.db.conn.commit()
    web.guard = wf.Guard()

    response = client.post("/api/rolemenus/colours/unpost", json={})

    assert response.status_code == 409
    assert response.json()["error"] == "test_mode"
    kinds = await wf.kinds_in(web.db)
    assert "web.role_menu.would_unpost" in kinds
    assert "web.role_menu.unposted" not in kinds
    menu = await get_menu(web.db, wf.GUILD_ID, "colours")
    assert menu["message_id"] is not None


async def test_posting_outside_the_test_channel_is_refused_while_the_guard_is_on(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await menus_on(web, wf)
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
    assert "web.role_menu.post" not in await wf.kinds_in(web.db)

    allowed = client.post(
        "/api/rolemenus/colours/post", json={"channel_id": str(wf.TEST_CHANNEL_ID)}
    )
    assert allowed.status_code == 200


async def test_posting_is_refused_while_role_menus_are_turned_off(
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

    assert response.status_code == 409
    assert response.json()["error"] == "rolemenu_off"
    assert "turned off" in response.json()["message"]
    assert guild.get_channel(wf.TEST_CHANNEL_ID).messages == []
    assert "web.role_menu.post" not in await wf.kinds_in(web.db)

    await menus_on(web, wf)
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
    await menus_on(web, wf)
    await web.store.set(wf.GUILD_ID, "role_menu_channel_id", wf.TEST_CHANNEL_ID)
    await a_menu(client, wf)
    client.put(
        "/api/rolemenus/colours",
        json={"options": [{"role_id": str(wf.PLAIN_ROLE_ID), "label": "Member"}]},
    )

    response = client.post("/api/rolemenus/colours/post", json={})

    assert response.json()["channel_id"] == str(wf.TEST_CHANNEL_ID)


async def test_an_option_that_is_not_an_object_is_refused_before_anything_is_written(
    client, sign_in, web, wf
):
    sign_in(client)
    await a_menu(client, wf)

    response = client.put(
        "/api/rolemenus/colours",
        json={"title": "Changed", "options": [str(wf.PLAIN_ROLE_ID)]},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "bad_option"
    assert client.get("/api/rolemenus").json()[0]["title"] == "Pick a colour"


async def test_a_description_that_is_not_text_is_coerced_before_any_write(client, sign_in, wf):
    sign_in(client)
    await a_menu(client, wf)

    updated = client.put("/api/rolemenus/colours", json={"description": 7}).json()

    assert updated["description"] == "7"


async def test_a_bad_role_late_in_the_list_leaves_the_heading_alone(client, sign_in, wf):
    """Checklist 12: the whole body is checked, then written — never half-written."""
    sign_in(client)
    await a_menu(client, wf)

    response = client.put(
        "/api/rolemenus/colours",
        json={
            "title": "Changed",
            "options": [
                {"role_id": str(wf.PLAIN_ROLE_ID), "label": "Member"},
                {"role_id": "999999", "label": "Ghost"},
            ],
        },
    )

    assert response.status_code == 400
    listed = client.get("/api/rolemenus").json()[0]
    assert listed["title"] == "Pick a colour"
    assert listed["options"] == []


@pytest.mark.parametrize(
    ("field", "value"),
    [("title", "t" * (TITLE_MAX + 1)), ("description", "d" * (DESCRIPTION_MAX + 1))],
)
def test_a_heading_or_line_past_discords_limit_is_refused_with_the_reason(
    client, sign_in, field, value
):
    sign_in(client)

    response = client.post("/api/rolemenus", json={"name": "c", "title": "C", field: value})

    assert response.status_code == 400
    assert response.json()["error"] == "too_long"
    assert "will not show more than" in response.json()["message"]
    assert client.get("/api/rolemenus").json() == []


async def test_a_label_past_the_limit_and_a_twenty_sixth_option_are_refused(client, sign_in, wf):
    sign_in(client)
    await a_menu(client, wf)

    long_label = client.put(
        "/api/rolemenus/colours",
        json={"options": [{"role_id": str(wf.PLAIN_ROLE_ID), "label": "l" * (LABEL_MAX + 1)}]},
    )
    too_many = client.put(
        "/api/rolemenus/colours",
        json={
            "options": [
                {"role_id": str(wf.PLAIN_ROLE_ID), "label": f"Member {n}"}
                for n in range(OPTIONS_MAX + 1)
            ]
        },
    )

    assert long_label.status_code == 400 and long_label.json()["error"] == "too_long"
    assert too_many.status_code == 400
    assert "at most 25 roles" in too_many.json()["message"]
    assert client.get("/api/rolemenus").json()[0]["options"] == []


REQUEST_ROUTES = [
    ("GET", "/api/rolemenus/requests", None),
    ("POST", "/api/rolemenus/requests/1/approve", {}),
    ("POST", "/api/rolemenus/requests/1/deny", {"reason": "no"}),
]


@pytest.mark.parametrize(("method", "route", "payload"), REQUEST_ROUTES)
def test_every_request_route_needs_a_staff_session(client, sign_in, method, route, payload):
    assert call(client, method, route, payload).status_code == 401
    sign_in(client, uid=1234, staff=False)
    assert call(client, method, route, payload).status_code == 403


async def a_request(client, web, wf, *, expires=None, role_id=None):
    """A menu that asks first, a member who asked, and the row the routes act on."""
    client.post(
        "/api/rolemenus",
        json={"name": "runner", "title": "Runner", "approval": True, "expires_days": expires},
    )
    wanted = role_id if role_id is not None else wf.STAFF_ROLE_ID
    client.put(
        "/api/rolemenus/runner",
        json={"options": [{"role_id": str(wanted), "label": "Runner"}]},
    )
    menu = await get_menu(web.db, wf.GUILD_ID, "runner")
    return await grants.create_request(web.db, wf.GUILD_ID, menu["id"], MEMBER, wanted)


async def test_a_menu_remembers_approval_and_its_two_clocks(client, sign_in, web, wf):
    sign_in(client)

    made = client.post(
        "/api/rolemenus",
        json={
            "name": "runner",
            "title": "Runner",
            "approval": True,
            "expires_days": 7,
            "retry_days": 14,
        },
    ).json()

    assert (made["approval"], made["expires_days"], made["retry_days"]) == (True, 7, 14)
    edited = client.put(
        "/api/rolemenus/runner", json={"approval": False, "expires_days": 0}
    ).json()
    assert edited["approval"] is False and edited["expires_days"] is None
    assert edited["retry_days"] == 14


def test_a_menu_edit_that_says_nothing_about_the_clocks_leaves_them_alone(client, sign_in, wf):
    sign_in(client)
    client.post(
        "/api/rolemenus",
        json={"name": "runner", "title": "Runner", "approval": True, "expires_days": 7},
    )

    edited = client.put("/api/rolemenus/runner", json={"title": "Runner status"}).json()

    assert edited["approval"] is True and edited["expires_days"] == 7


def test_approval_and_days_that_arrive_in_the_wrong_shape_are_refused(client, sign_in):
    sign_in(client)

    bad_approval = client.post(
        "/api/rolemenus", json={"name": "a", "title": "A", "approval": "yes"}
    )
    bad_days = client.post(
        "/api/rolemenus", json={"name": "b", "title": "B", "expires_days": "a week"}
    )

    assert bad_approval.status_code == 400 and bad_approval.json()["error"] == "bad_approval"
    assert bad_days.status_code == 400 and bad_days.json()["error"] == "bad_days"
    assert client.get("/api/rolemenus").json() == []


async def test_the_queue_lists_pending_requests_with_names(client, sign_in, web, wf):
    sign_in(client)
    wf.member(web.guild, MEMBER, name="ada")
    request_id = await a_request(client, web, wf)

    rows = client.get("/api/rolemenus/requests").json()

    assert [row["id"] for row in rows] == [request_id]
    assert rows[0]["status"] == "pending" and rows[0]["user_name"] == "Ada"
    assert rows[0]["role_name"] == "Aunties / Uncles"
    assert rows[0]["user_id"] == str(MEMBER) and rows[0]["decided_by_id"] is None


async def test_the_queue_filters_by_status_and_names_an_unknown_one(client, sign_in, web, wf):
    sign_in(client)
    wf.member(web.guild, MEMBER, name="ada")
    await a_request(client, web, wf)

    assert client.get("/api/rolemenus/requests?status=denied").json() == []
    unknown = client.get("/api/rolemenus/requests?status=maybe")
    assert unknown.status_code == 400 and unknown.json()["error"] == "unknown_status"
    assert "pending, approved" in unknown.json()["message"]


async def test_approving_from_the_page_hands_the_role_over_and_logs_it(client, sign_in, web, wf):
    sign_in(client)
    member = wf.member(web.guild, MEMBER, name="ada")
    request_id = await a_request(client, web, wf, expires=7)

    body = client.post(f"/api/rolemenus/requests/{request_id}/approve", json={}).json()

    assert body["request"]["status"] == "approved"
    assert body["request"]["decided_by_id"] == "7"
    assert "Approved" in body["message"]
    assert member.edits and wf.STAFF_ROLE_ID in member.edits[0]
    grant = await grants.open_grant(web.db, wf.GUILD_ID, MEMBER, wf.STAFF_ROLE_ID)
    assert grant["expires_at"] is not None and grant["source"] == "approval"
    assert "web.role.approved" in await wf.kinds_in(web.db)


async def test_the_days_in_the_body_beat_the_menus_own_number(client, sign_in, web, wf):
    sign_in(client)
    wf.member(web.guild, MEMBER, name="ada")
    request_id = await a_request(client, web, wf, expires=7)

    client.post(f"/api/rolemenus/requests/{request_id}/approve", json={"days": 0})

    grant = await grants.open_grant(web.db, wf.GUILD_ID, MEMBER, wf.STAFF_ROLE_ID)
    assert grant["expires_at"] is None


async def test_denying_needs_a_reason_and_sends_it_on(client, sign_in, web, wf):
    sign_in(client)
    member = wf.member(web.guild, MEMBER, name="ada")
    request_id = await a_request(client, web, wf)

    empty = client.post(f"/api/rolemenus/requests/{request_id}/deny", json={"reason": " "})
    body = client.post(
        f"/api/rolemenus/requests/{request_id}/deny", json={"reason": "not this month"}
    ).json()

    assert empty.status_code == 400 and empty.json()["error"] == "no_reason"
    assert body["request"]["status"] == "denied"
    assert body["request"]["deny_reason"] == "not this month"
    assert member.edits == [] and "not this month" in member.dms[0]
    assert "web.role.denied" in await wf.kinds_in(web.db)


async def test_a_second_decision_is_refused_rather_than_repeated(client, sign_in, web, wf):
    sign_in(client)
    wf.member(web.guild, MEMBER, name="ada")
    request_id = await a_request(client, web, wf)
    client.post(f"/api/rolemenus/requests/{request_id}/approve", json={})

    again = client.post(f"/api/rolemenus/requests/{request_id}/deny", json={"reason": "no"})

    assert again.status_code == 409 and again.json()["error"] == "not_decided"
    assert "already **approved**" in again.json()["message"]


def test_a_request_nobody_has_is_refused_with_a_sentence(client, sign_in):
    sign_in(client)

    response = client.post("/api/rolemenus/requests/404/approve", json={})

    assert response.status_code == 409
    assert "no record of that request" in response.json()["message"]


async def test_a_queue_row_names_its_menu_and_carries_the_asker_s_picture(
    client, sign_in, web, wf
):
    """The page has only a menu id otherwise, and no menu row carries one."""
    sign_in(client)
    member = wf.member(web.guild, MEMBER, name="ada")
    request_id = await a_request(client, web, wf, expires=7)

    row = client.get("/api/rolemenus/requests").json()[0]

    assert row["menu_name"] == "runner"
    assert row["user_avatar"] == member.display_avatar.url
    decided = client.post(f"/api/rolemenus/requests/{request_id}/approve", json={}).json()
    assert decided["request"]["menu_name"] == "runner"


async def test_a_request_from_somebody_who_has_left_still_names_its_menu(client, sign_in, web, wf):
    sign_in(client)
    await a_request(client, web, wf)

    row = client.get("/api/rolemenus/requests").json()[0]

    assert row["menu_name"] == "runner"
    assert row["user_avatar"] is None


async def a_posted_menu(client, web, wf, channel_id):
    await menus_on(web, wf)
    await a_menu(client, wf)
    client.put(
        "/api/rolemenus/colours",
        json={"options": [{"role_id": str(wf.PLAIN_ROLE_ID), "label": "Member"}]},
    )
    client.post("/api/rolemenus/colours/post", json={"channel_id": str(channel_id)})


async def test_saving_a_different_channel_moves_the_panel_rather_than_cloning_it(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await a_posted_menu(client, web, wf, wf.OTHER_CHANNEL_ID)

    body = client.put(
        "/api/rolemenus/colours", json={"channel_id": str(wf.TEST_CHANNEL_ID)}
    ).json()

    assert guild.get_channel(wf.OTHER_CHANNEL_ID).messages == [], "the old panel came down"
    landed = guild.get_channel(wf.TEST_CHANNEL_ID).messages
    assert len(landed) == 1, "one panel, in the new channel"
    assert body["channel_id"] == str(wf.TEST_CHANNEL_ID)
    assert body["message_id"] == str(landed[0].id)
    menu = await get_menu(web.db, wf.GUILD_ID, "colours")
    assert (menu["channel_id"], menu["message_id"]) == (wf.TEST_CHANNEL_ID, landed[0].id)
    assert (await wf.kinds_in(web.db)).count("web.role_menu.post") == 2


async def test_saving_the_channel_it_is_already_in_posts_nothing_again(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await a_posted_menu(client, web, wf, wf.TEST_CHANNEL_ID)
    was = guild.get_channel(wf.TEST_CHANNEL_ID).messages[0].id

    client.put("/api/rolemenus/colours", json={"channel_id": str(wf.TEST_CHANNEL_ID)})

    messages = guild.get_channel(wf.TEST_CHANNEL_ID).messages
    assert [m.id for m in messages] == [was]


async def test_an_edit_that_says_nothing_about_the_channel_leaves_the_panel_alone(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await a_posted_menu(client, web, wf, wf.TEST_CHANNEL_ID)
    was = guild.get_channel(wf.TEST_CHANNEL_ID).messages[0].id

    body = client.put("/api/rolemenus/colours", json={"title": "Colours again"}).json()

    assert body["message_id"] == str(was)
    assert [m.id for m in guild.get_channel(wf.TEST_CHANNEL_ID).messages] == [was]


async def test_a_menu_with_no_panel_is_told_to_post_it_rather_than_moved(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await menus_on(web, wf)
    await a_menu(client, wf)
    client.put(
        "/api/rolemenus/colours",
        json={"options": [{"role_id": str(wf.PLAIN_ROLE_ID), "label": "Member"}]},
    )

    response = client.put("/api/rolemenus/colours", json={"channel_id": str(wf.TEST_CHANNEL_ID)})

    assert response.status_code == 400 and response.json()["error"] == "not_posted"
    assert "no panel to move" in response.json()["message"]
    assert guild.get_channel(wf.TEST_CHANNEL_ID).messages == []


async def test_moving_a_panel_outside_the_test_channel_is_refused_by_the_guard(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await a_posted_menu(client, web, wf, wf.TEST_CHANNEL_ID)
    web.guard = wf.Guard()

    response = client.put("/api/rolemenus/colours", json={"channel_id": str(wf.OTHER_CHANNEL_ID)})

    assert response.status_code == 409 and response.json()["error"] == "test_mode"
    assert len(guild.get_channel(wf.TEST_CHANNEL_ID).messages) == 1
    assert guild.get_channel(wf.OTHER_CHANNEL_ID).messages == []


async def test_a_refused_move_leaves_the_rest_of_the_edit_unsaved(client, sign_in, web, guild, wf):
    """The refusal says nothing was changed, so nothing may be — not even the title."""
    sign_in(client)
    await a_posted_menu(client, web, wf, wf.TEST_CHANNEL_ID)
    web.guard = wf.Guard()

    response = client.put(
        "/api/rolemenus/colours",
        json={"title": "Half saved", "channel_id": str(wf.OTHER_CHANNEL_ID)},
    )

    assert response.status_code == 409
    assert client.get("/api/rolemenus").json()[0]["title"] == "Pick a colour"


async def test_moving_a_panel_to_a_channel_that_is_gone_is_refused_in_words(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await a_posted_menu(client, web, wf, wf.TEST_CHANNEL_ID)

    response = client.put("/api/rolemenus/colours", json={"channel_id": "404"})

    assert response.status_code == 400 and response.json()["error"] == "no_such_channel"
    assert len(guild.get_channel(wf.TEST_CHANNEL_ID).messages) == 1
