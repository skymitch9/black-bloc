from __future__ import annotations

import pytest

from black_bloc import pings

ROUTES = [
    ("GET", "/api/pings/streamers"),
    ("POST", "/api/pings/streamers"),
    ("DELETE", "/api/pings/streamers/21"),
    ("POST", "/api/pings/setup"),
]


@pytest.mark.parametrize(("method", "route"), ROUTES)
def test_every_pings_route_needs_a_session(client, method, route):
    assert client.request(method, route).status_code == 401


@pytest.mark.parametrize(("method", "route"), ROUTES)
def test_every_pings_route_refuses_a_non_staff_visitor(client, sign_in, method, route):
    sign_in(client, uid=1234, staff=False)
    assert client.request(method, route).status_code == 403


@pytest.fixture
async def on(web, wf):
    await web.store.set(wf.GUILD_ID, "pings_mode", "on")
    return web


async def test_the_table_carries_what_the_pings_section_draws(
    client, sign_in, on, guild, wf
):
    member = wf.member(guild, 21, name="namu")
    sign_in(client)
    client.post("/api/pings/streamers", json={"member_id": "21"})
    fan = wf.member(guild, 22, name="fan")
    await fan.add_roles(guild.get_role(int((await pings.get_fan_role(on.db, wf.GUILD_ID, 21))[
        "role_id"
    ])))

    rows = client.get("/api/pings/streamers").json()

    assert len(rows) == 1
    assert rows[0]["member_id"] == "21" and rows[0]["member"] == member.display_name
    assert rows[0]["role"] == "Namu pings" and rows[0]["followers"] == 1
    assert rows[0]["created_by"] == "7" and rows[0]["created_at"]


async def test_a_role_deleted_by_hand_reads_as_no_count_rather_than_zero(
    client, sign_in, on, guild, wf
):
    wf.member(guild, 21, name="namu")
    sign_in(client)
    client.post("/api/pings/streamers", json={"member_id": "21"})
    guild.roles = [role for role in guild.roles if role.id < 900]

    row = client.get("/api/pings/streamers").json()[0]

    assert row["followers"] is None and row["role"] is None


async def test_staff_can_start_a_role_from_the_site_and_it_leaves_a_web_line(
    client, sign_in, on, guild, wf
):
    wf.member(guild, 21, name="namu")
    sign_in(client)

    response = client.post("/api/pings/streamers", json={"member_id": "21"})

    assert response.status_code == 200
    assert response.json()["role"] == "Namu pings"
    assert "streamers" in response.json()["message"]
    assert await pings.get_fan_role(on.db, wf.GUILD_ID, 21) is not None
    assert "web.pings.fan_role_created" in await wf.kinds_in(on.db)


async def test_the_site_may_hand_an_existing_role_over(client, sign_in, on, guild, wf):
    wf.member(guild, 21, name="namu")
    sign_in(client)

    response = client.post(
        "/api/pings/streamers", json={"member_id": "21", "role_id": str(wf.PLAIN_ROLE_ID)}
    )

    assert response.json()["role_id"] == str(wf.PLAIN_ROLE_ID)
    assert guild.made_roles == []


def test_a_member_black_bloc_cannot_see_is_a_sentence(client, sign_in, on):
    sign_in(client)
    response = client.post("/api/pings/streamers", json={"member_id": "999"})
    assert response.status_code == 404
    assert "Pick them from the list" in response.json()["message"]


def test_a_role_that_is_gone_is_a_sentence(client, sign_in, on, guild, wf):
    wf.member(guild, 21, name="namu")
    sign_in(client)
    response = client.post(
        "/api/pings/streamers", json={"member_id": "21", "role_id": "123456"}
    )
    assert response.status_code == 400
    assert "not a role in this server" in response.json()["message"]


def test_an_id_that_is_not_a_number_is_a_sentence(client, sign_in, on):
    sign_in(client)
    response = client.post("/api/pings/streamers", json={"member_id": "namu"})
    assert response.status_code == 400
    assert "Copy ID" in response.json()["message"]


async def test_a_second_ask_for_the_same_streamer_says_they_already_have_one(
    client, sign_in, on, guild, wf
):
    wf.member(guild, 21, name="namu")
    sign_in(client)
    client.post("/api/pings/streamers", json={"member_id": "21"})

    response = client.post("/api/pings/streamers", json={"member_id": "21"})

    assert response.status_code == 409
    assert "already has a ping role" in response.json()["message"]


async def test_removing_takes_the_row_the_role_and_leaves_a_web_line(
    client, sign_in, on, guild, wf
):
    wf.member(guild, 21, name="namu")
    sign_in(client)
    made = client.post("/api/pings/streamers", json={"member_id": "21"}).json()

    response = client.delete("/api/pings/streamers/21")

    assert response.json()["removed"] is True
    assert "is gone from the server" in response.json()["message"]
    assert guild.get_role(int(made["role_id"])) is None or guild.roles[-1].deleted
    assert await pings.get_fan_role(on.db, wf.GUILD_ID, 21) is None
    assert "web.pings.fan_role_removed" in await wf.kinds_in(on.db)


def test_removing_somebody_with_no_role_says_so(client, sign_in, on, guild, wf):
    wf.member(guild, 21, name="namu")
    sign_in(client)
    response = client.delete("/api/pings/streamers/21")
    assert response.status_code == 404
    assert "no ping role" in response.json()["message"]


async def test_setup_makes_the_events_role_and_points_both_feeds_at_it(
    client, sign_in, on, guild, wf
):
    sign_in(client)

    response = client.post("/api/pings/setup", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["created"] is True and payload["menu"] == "notifications"
    assert on.store.get(wf.GUILD_ID, "golive_ping_role_id") == int(payload["role_id"])
    assert on.store.get(wf.GUILD_ID, "events_ping_role_id") == int(payload["role_id"])
    assert "web.pings.setup" in await wf.kinds_in(on.db)


def test_setup_takes_the_role_the_page_picked(client, sign_in, on, guild, wf):
    sign_in(client)

    payload = client.post(
        "/api/pings/setup", json={"role_id": str(wf.PLAIN_ROLE_ID)}
    ).json()

    assert payload["role_id"] == str(wf.PLAIN_ROLE_ID) and payload["created"] is False
    assert guild.made_roles == []


def test_setup_with_no_body_at_all_still_works(client, sign_in, on):
    sign_in(client)
    assert client.post("/api/pings/setup").status_code == 200


def test_setup_says_the_feature_is_still_off_rather_than_pretending(client, sign_in, web):
    sign_in(client)
    assert "still off" in client.post("/api/pings/setup", json={}).json()["message"]
