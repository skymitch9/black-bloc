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
    """Nothing to switch on since request #17: the staff control needs no mode."""


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
    for payload in ({"name": "x"}, {"title": "x"}):
        refused = client.post("/api/rolemenus", json=payload)
        assert refused.status_code == 400, payload
        assert refused.json()["message"]


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


def test_a_menu_nobody_has_is_a_404_with_a_sentence(client, sign_in):
    sign_in(client)
    for method, route in (
        ("PUT", "/api/rolemenus/ghost"),
        ("DELETE", "/api/rolemenus/ghost"),
        ("POST", "/api/rolemenus/ghost/end-now"),
        ("POST", "/api/rolemenus/ghost/end-earlier"),
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
    assert response.json()["error"] == "no_such_role"
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
    assert f"at most {OPTIONS_MAX} roles" in too_many.json()["message"]
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


async def a_posted_menu(client, web, wf, channel_id):
    await menus_on(web, wf)
    await a_menu(client, wf)
    client.put(
        "/api/rolemenus/colours",
        json={"options": [{"role_id": str(wf.PLAIN_ROLE_ID), "label": "Member"}]},
    )
    client.post("/api/rolemenus/colours/post", json={"channel_id": str(channel_id)})


async def test_a_put_that_moves_roles_re_stamps_their_open_grants(client, sign_in, web, wf):
    """1a's must-do: options written by the site follow the menu's end like the panel's do."""
    sign_in(client)
    await a_menu(client, wf)
    later = "2099-01-01T00:00:00+00:00"
    menu = await get_menu(web.db, wf.GUILD_ID, "colours")
    await web.db.conn.execute(
        "UPDATE role_menus SET ends_source = 'date', ends_at = ? WHERE id = ?", (later, menu["id"])
    )
    await web.db.conn.commit()
    await grants.add_grant(web.db, wf.GUILD_ID, MEMBER, wf.PLAIN_ROLE_ID, "staff", until=None)

    client.put(
        "/api/rolemenus/colours",
        json={"options": [{"role_id": str(wf.PLAIN_ROLE_ID), "label": "Member"}]},
    )
    assert (await grants.open_grant(web.db, wf.GUILD_ID, MEMBER, wf.PLAIN_ROLE_ID))[
        "expires_at"
    ] == later

    client.put("/api/rolemenus/colours", json={"options": []})
    assert (await grants.open_grant(web.db, wf.GUILD_ID, MEMBER, wf.PLAIN_ROLE_ID))[
        "expires_at"
    ] is None


# --- request #17 1b: the end, End it now, the hold, and the retired doors ------------------------


async def end_menu(client, web, wf, name="btb"):
    client.post("/api/rolemenus", json={"name": name, "title": "Back to Black"})
    client.put(
        f"/api/rolemenus/{name}",
        json={"options": [{"role_id": str(wf.PLAIN_ROLE_ID), "label": "Runner"}]},
    )
    return await get_menu(web.db, wf.GUILD_ID, name)


async def a_marathon(web, wf, ends_at="2099-02-28T05:00:00+00:00"):
    cur = await web.db.conn.execute(
        "INSERT INTO marathons(guild_id, name, source, source_ref, schedule_url, added_by, "
        "added_at, ends_at) VALUES (?, 'Back to Black 2027', 'gdq', 'x', 'https://x', 1, "
        "'2026-01-01T00:00:00+00:00', ?)",
        (wf.GUILD_ID, ends_at),
    )
    await web.db.conn.commit()
    return cur.lastrowid


async def kind_count(web, wf, kind):
    return (await wf.kinds_in(web.db)).count(kind)


@pytest.mark.parametrize(
    ("method", "route"),
    [
        ("POST", "/api/rolemenus/colours/post"),
        ("POST", "/api/rolemenus/colours/unpost"),
        ("GET", "/api/rolemenus/requests"),
        ("POST", "/api/rolemenus/requests/1/approve"),
        ("POST", "/api/rolemenus/requests/1/deny"),
        ("POST", "/api/rolemenus/seed"),
    ],
)
def test_every_retired_self_pick_route_answers_410_in_words(client, sign_in, method, route):
    sign_in(client)

    response = client.request(method, route, json={})

    assert response.status_code == 410
    body = response.json()
    assert body["error"] == "rolemenu_retired"
    assert "Channels & Roles" in body["message"] and "Hand roles out" in body["message"]


async def test_a_menu_row_carries_its_end_who_wears_it_and_the_last_pass(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await end_menu(client, web, wf)
    wf.member(guild, MEMBER, name="ada").roles.append(guild.get_role(wf.PLAIN_ROLE_ID))

    [row] = client.get("/api/rolemenus").json()

    assert row["ends_source"] == "none" and row["ends_at"] is None
    assert row["end_label"] == "no end set"
    assert row["wearing"] == 1
    assert row["buffer_days"] is None and row["buffer_default"] == 1
    assert row["last_pass"] == {"passes": 0, "members": 0, "failures": 0, "ended_at": None}
    assert row["ends_held_at"] is None and row["mode"] == "staff"


async def test_a_put_of_a_typed_date_sets_the_end_with_one_log_row(client, sign_in, web, wf):
    sign_in(client)
    await end_menu(client, web, wf)
    before = len(await wf.kinds_in(web.db))

    row = client.put(
        "/api/rolemenus/btb", json={"ends_source": "date", "ends_at": "2099-02-28"}
    ).json()

    assert row["ends_source"] == "date"
    assert row["ends_at"].startswith("2099-")
    assert row["end_label"].startswith("ends 2099-02-28")
    assert (await wf.kinds_in(web.db))[before:] == ["web.role_menu.end_set"]


async def test_a_put_binds_a_marathon_with_a_buffer_and_lists_what_it_can_bind_to(
    client, sign_in, web, wf
):
    sign_in(client)
    await end_menu(client, web, wf)
    marathon_id = await a_marathon(web, wf)

    [choice] = client.get("/api/rolemenus/marathons").json()
    assert choice["id"] == str(marathon_id) and "Back to Black 2027 · ends" in choice["label"]

    row = client.put(
        "/api/rolemenus/btb",
        json={"ends_source": "marathon", "ends_marathon_id": str(marathon_id), "buffer_days": 2},
    ).json()

    assert row["ends_marathon_id"] == str(marathon_id) and row["buffer_days"] == 2
    assert row["ends_at"] == "2099-03-02T05:00:00+00:00"
    assert "(Back to Black 2027 + 2 d)" in row["end_label"]

    again = client.put("/api/rolemenus/btb", json={"buffer_days": ""}).json()
    assert again["buffer_days"] is None and again["ends_at"] == "2099-03-01T05:00:00+00:00"


async def test_an_end_the_site_gets_wrong_is_refused_in_words_and_writes_nothing(
    client, sign_in, web, wf
):
    sign_in(client)
    await end_menu(client, web, wf)
    before = await wf.kinds_in(web.db)
    for body, error in (
        ({"ends_source": "date", "ends_at": "2020-01-01"}, "past_date"),
        ({"ends_source": "date", "ends_at": "soon"}, "bad_date"),
        ({"ends_source": "marathon", "ends_marathon_id": "4242"}, "no_such_marathon"),
        ({"ends_source": "sometimes"}, "bad_end_source"),
        ({"buffer_days": 3}, "buffer_needs_marathon"),
    ):
        response = client.put("/api/rolemenus/btb", json=body)
        assert response.status_code == 400 and response.json()["error"] == error, body
        assert response.json()["message"]
    assert await wf.kinds_in(web.db) == before
    assert (await get_menu(web.db, wf.GUILD_ID, "btb"))["ends_source"] == "none"


async def test_a_words_only_save_never_touches_the_end(client, sign_in, web, wf):
    sign_in(client)
    menu = await end_menu(client, web, wf)
    await web.db.conn.execute(
        "UPDATE role_menus SET ends_source = 'date', ends_at = '2020-01-01T00:00:00+00:00', "
        "ended_at = '2020-01-02T00:00:00+00:00' WHERE id = ?",
        (menu["id"],),
    )
    await web.db.conn.commit()

    client.put("/api/rolemenus/btb", json={"title": "Back to Black 2027", "mode": "multiple"})

    fresh = await get_menu(web.db, wf.GUILD_ID, "btb")
    assert fresh["ended_at"] == "2020-01-02T00:00:00+00:00"
    assert "web.role_menu.end_set" not in await wf.kinds_in(web.db)


async def test_end_now_takes_the_roles_off_everyone_and_says_how_many(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await end_menu(client, web, wf)
    member = wf.member(guild, MEMBER, name="ada")
    member.roles.append(guild.get_role(wf.PLAIN_ROLE_ID))
    web.guard = None

    response = client.post("/api/rolemenus/btb/end-now")

    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["pass"]["members"] == 1 and body["pass"]["ended"] is True
    assert body["pass"]["left"] == []
    assert "**btb** ended" in body["message"]
    assert body["ended_at"] and body["ends_source"] == "date"
    assert wf.PLAIN_ROLE_ID not in [role.id for role in member.roles]
    assert "web.role_menu.ended" in await wf.kinds_in(web.db)


async def test_end_now_under_the_guard_is_the_guards_409(client, sign_in, web, wf):
    sign_in(client)
    await end_menu(client, web, wf)
    web.guard = wf.Guard(wf.TEST_CHANNEL_ID)

    response = client.post("/api/rolemenus/btb/end-now")

    assert response.status_code == 409 and response.json()["error"] == "test_mode"
    assert (await get_menu(web.db, wf.GUILD_ID, "btb"))["ended_at"] is None


async def test_use_the_earlier_end_takes_a_held_end_and_refuses_when_none_waits(
    client, sign_in, web, wf
):
    sign_in(client)
    menu = await end_menu(client, web, wf)
    marathon_id = await a_marathon(web, wf)
    client.put(
        "/api/rolemenus/btb", json={"ends_source": "marathon", "ends_marathon_id": marathon_id}
    )

    nothing = client.post("/api/rolemenus/btb/end-earlier")
    assert nothing.status_code == 409 and nothing.json()["error"] == "nothing_held"

    await web.db.conn.execute(
        "UPDATE marathons SET ends_at = '2099-02-20T05:00:00+00:00' WHERE id = ?", (marathon_id,)
    )
    await web.db.conn.execute(
        "UPDATE role_menus SET ends_held_at = '2099-02-21T05:00:00+00:00' WHERE id = ?",
        (menu["id"],),
    )
    await web.db.conn.commit()

    row = client.post("/api/rolemenus/btb/end-earlier").json()

    assert row["ends_at"] == "2099-02-21T05:00:00+00:00" and row["ends_held_at"] is None
    assert "web.role_menu.end_set" in await wf.kinds_in(web.db)


async def test_the_row_carries_what_the_earlier_end_and_end_now_confirms_ask(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    menu = await end_menu(client, web, wf)
    member = wf.member(guild, MEMBER, name="ada")
    member.roles.append(guild.get_role(wf.PLAIN_ROLE_ID))

    [quiet] = client.get("/api/rolemenus").json()
    assert quiet["held_label"] is None and quiet["held_past"] is False
    assert quiet["held_question"] is None
    assert quiet["end_now_question"] == "Take 1 role(s) off 1 people now?"

    for held, past, words in (
        ("2099-02-21T05:00:00+00:00", False, "come off 1 people 2099-02-2"),
        ("2020-02-21T05:00:00+00:00", True, "already gone by"),
    ):
        await web.db.conn.execute(
            "UPDATE role_menus SET ends_held_at = ? WHERE id = ?", (held, menu["id"])
        )
        await web.db.conn.commit()

        [row] = client.get("/api/rolemenus").json()

        assert row["held_past"] is past and row["wearing"] == 1
        assert row["held_label"].startswith(held[:4]) and "<t:" not in row["held_label"]
        assert row["held_question"].startswith("Use **btb**'s earlier end?")
        assert words in row["held_question"] and "<t:" not in row["held_question"]


async def test_a_menu_still_to_end_is_not_deleted_while_people_wear_its_roles(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await end_menu(client, web, wf)
    member = wf.member(guild, MEMBER, name="ada")
    member.roles.append(guild.get_role(wf.PLAIN_ROLE_ID))
    client.put("/api/rolemenus/btb", json={"ends_source": "date", "ends_at": "2099-02-28"})

    refused = client.delete("/api/rolemenus/btb")

    assert refused.status_code == 409 and refused.json()["error"] == "menu_still_ends"
    assert "End it now" in refused.json()["message"]
    assert await get_menu(web.db, wf.GUILD_ID, "btb") is not None

    client.put("/api/rolemenus/btb", json={"ends_source": "none"})
    assert client.delete("/api/rolemenus/btb").status_code == 200


async def test_assign_needs_no_switch_and_writes_the_menus_end(client, sign_in, web, guild, wf):
    sign_in(client)
    await end_menu(client, web, wf)
    client.put("/api/rolemenus/btb", json={"ends_source": "date", "ends_at": "2099-02-28"})
    wf.member(guild, MEMBER, name="ada").roles = []

    response = client.post(
        "/api/rolemenus/btb/assign",
        json={"user_id": str(MEMBER), "role_ids": [str(wf.PLAIN_ROLE_ID)]},
    )

    assert response.status_code == 200, response.json()
    grant = await grants.open_grant(web.db, wf.GUILD_ID, MEMBER, wf.PLAIN_ROLE_ID)
    menu = await get_menu(web.db, wf.GUILD_ID, "btb")
    assert grant["expires_at"] == menu["ends_at"]


async def test_the_marathon_row_names_the_menus_that_end_with_it(client, sign_in, web, guild, wf):
    sign_in(client)
    await end_menu(client, web, wf)
    member = wf.member(guild, MEMBER, name="ada")
    member.roles.append(guild.get_role(wf.PLAIN_ROLE_ID))
    marathon_id = await a_marathon(web, wf)
    from black_bloc.cogs.community.role_menus import menus_ending_with

    assert await menus_ending_with(web, guild, marathon_id) == []

    client.put(
        "/api/rolemenus/btb", json={"ends_source": "marathon", "ends_marathon_id": marathon_id}
    )

    [line] = await menus_ending_with(web, guild, marathon_id)
    assert line == {"name": "btb", "title": line["title"], "roles": 1, "wearing": 1}

    await web.db.conn.execute("UPDATE role_menus SET ended_at = '2099-01-01T00:00:00+00:00'")
    await web.db.conn.commit()
    assert await menus_ending_with(web, guild, marathon_id) == []


# --- a role `/pings` hands out never sits on a menu that ends (2026-11-13) ------------------------

PINGS_SAID = "belongs to `/pings`, so nothing was changed"


async def test_every_end_and_end_now_on_a_menu_holding_a_fan_role_is_refused_in_words(
    client, sign_in, web, guild, wf
):
    from black_bloc import pings

    sign_in(client)
    menu = await end_menu(client, web, wf)
    member = wf.member(guild, MEMBER, name="ada")
    member.roles.append(guild.get_role(wf.PLAIN_ROLE_ID))
    marathon_id = await a_marathon(web, wf)
    await pings.set_fan_role(web.db, wf.GUILD_ID, MEMBER, wf.PLAIN_ROLE_ID, 7)
    await web.db.conn.execute(
        "UPDATE role_menus SET ends_held_at = '2099-02-21T05:00:00+00:00' WHERE id = ?",
        (menu["id"],),
    )
    await web.db.conn.commit()
    web.guard = None
    before = await wf.kinds_in(web.db)

    for method, route, body in (
        ("PUT", "/api/rolemenus/btb", {"ends_source": "date", "ends_at": "2099-02-28"}),
        ("PUT", "/api/rolemenus/btb", {"ends_source": "marathon", "ends_marathon_id": marathon_id}),
        ("POST", "/api/rolemenus/btb/end-now", {}),
        ("POST", "/api/rolemenus/btb/end-earlier", {}),
    ):
        response = client.request(method, route, json=body)
        assert response.status_code == 409 and response.json()["error"] == "pings_role", body
        said = response.json()["message"]
        assert PINGS_SAID in said and "**Member**" in said

    assert await wf.kinds_in(web.db) == before
    assert (await get_menu(web.db, wf.GUILD_ID, "btb"))["ends_source"] == "none"
    assert wf.PLAIN_ROLE_ID in [role.id for role in member.roles]

    cleared = client.put("/api/rolemenus/btb", json={"ends_source": "none"})
    assert cleared.status_code == 200


async def test_putting_the_events_role_on_a_menu_is_refused_and_taking_it_off_is_not(
    client, sign_in, web, wf
):
    sign_in(client)
    menu = await end_menu(client, web, wf)
    await web.store.set(wf.GUILD_ID, "golive_ping_role_id", wf.ADMIN_ROLE_ID, by=7)
    both = [
        {"role_id": str(wf.PLAIN_ROLE_ID), "label": "Runner"},
        {"role_id": str(wf.ADMIN_ROLE_ID), "label": "Events"},
    ]

    refused = client.put("/api/rolemenus/btb", json={"options": both})

    assert refused.status_code == 409 and refused.json()["error"] == "pings_role"
    assert "**Admin**" in refused.json()["message"]
    assert [row["role_id"] for row in await get_options(web.db, menu["id"])] == [wf.PLAIN_ROLE_ID]

    await web.db.conn.execute(
        "INSERT INTO role_menu_options(menu_id, role_id, label, emoji, position) "
        "VALUES (?, ?, 'Events', NULL, 1)",
        (menu["id"], wf.ADMIN_ROLE_ID),
    )
    await web.db.conn.commit()

    kept = client.put("/api/rolemenus/btb", json={"title": "Back to Black 2027", "options": both})
    assert kept.status_code == 200
    dropped = client.put("/api/rolemenus/btb", json={"options": both[:1]})
    assert dropped.status_code == 200
    assert [row["role_id"] for row in await get_options(web.db, menu["id"])] == [wf.PLAIN_ROLE_ID]

    ends = client.put(
        "/api/rolemenus/btb",
        json={"options": both[:1], "ends_source": "date", "ends_at": "2099-02-28"},
    )
    assert ends.status_code == 200 and ends.json()["ends_source"] == "date"
