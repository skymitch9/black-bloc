from __future__ import annotations

import pytest

from black_bloc import pings
from black_bloc.cogs.content.spotlight import add_channel

ROUTES = [
    ("GET", "/api/pings/streamers"),
    ("POST", "/api/pings/streamers"),
    ("DELETE", "/api/pings/streamers/21"),
    ("DELETE", "/api/pings/streamers/spotlight/1"),
    ("POST", "/api/pings/setup"),
    ("POST", "/api/pings/raidtrain-role"),
    ("GET", "/api/pings/list"),
    ("POST", "/api/pings/list/21"),
    ("GET", "/api/pings/onboarding"),
    ("POST", "/api/pings/onboarding/sync"),
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


async def test_the_site_names_the_role_it_is_making(client, sign_in, on, guild, wf):
    wf.member(guild, 21, name="namu")
    sign_in(client)

    response = client.post(
        "/api/pings/streamers", json={"member_id": "21", "name": "  Namu   crew "}
    )

    assert response.status_code == 200 and response.json()["role"] == "Namu crew"
    assert [role.name for role in guild.made_roles] == ["Namu crew"]


def test_a_name_a_role_already_has_is_a_sentence_and_never_a_bare_status(
    client, sign_in, on, guild, wf
):
    wf.member(guild, 21, name="namu")
    sign_in(client)

    response = client.post("/api/pings/streamers", json={"member_id": "21", "name": "member"})

    assert response.status_code == 409 and response.json()["error"] == "duplicate_role"
    assert "already exists in this server" in response.json()["message"]
    assert guild.made_roles == []


def test_a_name_that_is_blank_is_a_sentence(client, sign_in, on, guild, wf):
    wf.member(guild, 21, name="namu")
    sign_in(client)

    response = client.post("/api/pings/streamers", json={"member_id": "21", "name": "  "})

    assert response.status_code == 400 and response.json()["error"] == "blank_role_name"
    assert "needs a name" in response.json()["message"]


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


# --- the streamer list (C1/C9) -------------------------------------------------------------------


async def listed(web, wf, user_id, *, hidden=False):
    """Nobody is added by hand in the app, so the test writes the row the listener would."""
    await web.db.conn.execute(
        "INSERT OR REPLACE INTO streamers(guild_id, user_id, first_live_at, last_live_at, "
        "live_count, platform, login, listed, hidden_by, hidden_at) "
        "VALUES (?, ?, '2026-09-01T00:00:00+00:00', '2026-09-10T00:00:00+00:00', 4, 'Twitch', "
        "'namu', ?, ?, ?)",
        (
            wf.GUILD_ID,
            int(user_id),
            0 if hidden else 1,
            7 if hidden else None,
            "2026-09-11T00:00:00+00:00" if hidden else None,
        ),
    )
    await web.db.conn.commit()


async def test_the_list_carries_what_the_streamer_table_draws(client, sign_in, on, guild, wf):
    member = wf.member(guild, 21, name="namu")
    await listed(on, wf, 21)
    sign_in(client)

    rows = client.get("/api/pings/list").json()

    assert len(rows) == 1
    row = rows[0]
    assert row["member_id"] == "21" and row["member"] == member.display_name
    assert row["listed"] is True and row["hidden_by"] is None and row["hidden_at"] is None
    assert row["live_count"] == 4 and row["login"] == "namu" and row["platform"] == "Twitch"
    assert row["role_id"] is None and row["role"] is None and row["followers"] is None


async def test_a_listed_streamer_with_a_role_carries_its_follower_count(
    client, sign_in, on, guild, wf
):
    wf.member(guild, 21, name="namu")
    await listed(on, wf, 21)
    sign_in(client)
    client.post("/api/pings/streamers", json={"member_id": "21"})
    fan = wf.member(guild, 22, name="fan")
    row = await pings.get_fan_role(on.db, wf.GUILD_ID, 21)
    await fan.add_roles(guild.get_role(int(row["role_id"])))

    found = client.get("/api/pings/list").json()[0]

    assert found["role"] == "Namu pings" and found["followers"] == 1


async def test_hiding_and_restoring_are_one_route_both_ways(client, sign_in, on, guild, wf):
    wf.member(guild, 21, name="namu")
    await listed(on, wf, 21)
    sign_in(client)

    hidden = client.post("/api/pings/list/21", json={"listed": False})

    assert hidden.status_code == 200
    assert hidden.json()["listed"] is False
    assert hidden.json()["hidden_by"] == "7"
    assert "off the streamer list" in hidden.json()["message"]
    assert "web.pings.streamer_hidden" in await wf.kinds_in(on.db)

    again = client.post("/api/pings/list/21", json={"listed": False})
    assert again.status_code == 409 and "already off" in again.json()["message"]

    back = client.post("/api/pings/list/21", json={"listed": True})
    assert back.status_code == 200 and back.json()["listed"] is True
    assert "web.pings.streamer_restored" in await wf.kinds_in(on.db)


async def test_hiding_somebody_who_was_never_seen_streaming_refuses_in_words(
    client, sign_in, on, guild, wf
):
    wf.member(guild, 21, name="namu")
    sign_in(client)

    refused = client.post("/api/pings/list/21", json={"listed": False})

    assert refused.status_code == 409
    assert "streamer list" in refused.json()["message"]


# --- the raid-train role (C3/C9) -----------------------------------------------------------------


async def test_the_raid_train_role_route_makes_one_and_points_the_key(
    client, sign_in, on, guild, wf
):
    sign_in(client)

    made = client.post("/api/pings/raidtrain-role", json={})

    assert made.status_code == 200 and made.json()["created"] is True
    assert on.store.get(wf.GUILD_ID, "raidtrain_ping_role_id") == int(made.json()["role_id"])
    assert "web.pings.raidtrain_setup" in await wf.kinds_in(on.db)

    again = client.post("/api/pings/raidtrain-role", json={})
    assert again.status_code == 200 and again.json()["created"] is False


# --- onboarding (C5/C9) --------------------------------------------------------------------------


async def test_the_onboarding_card_reads_without_a_community_server(client, sign_in, on, wf):
    sign_in(client)

    found = client.get("/api/pings/onboarding").json()

    assert found["community"] is False and found["managed"] is True
    assert found["prompts"] == [] and found["last_synced_at"] is None
    assert found["more_on_pings"] == 0 and found["foreign_prompts"] == 0


async def test_sync_now_refuses_in_words_off_a_community_server(client, sign_in, on, wf):
    sign_in(client)

    refused = client.post("/api/pings/onboarding/sync")

    assert refused.status_code == 409
    assert refused.json()["error"] == "no_community"
    assert "Community" in refused.json()["message"]
    assert not [one for one in await wf.kinds_in(on.db) if "onboarding" in one]


async def test_sync_now_refuses_once_the_managed_switch_is_off(client, sign_in, on, wf):
    await on.store.set(wf.GUILD_ID, "pings_onboarding_managed", False)
    sign_in(client)

    refused = client.post("/api/pings/onboarding/sync")

    assert refused.status_code == 409
    assert refused.json()["error"] == "not_managed"
    assert client.get("/api/pings/onboarding").json()["managed"] is False


# --- a channel's ping role through the routes (info/spotlight-pings-design.md §C) -------------


async def a_spotlight(web, wf, login="gamesdonequick", name="GamesDoneQuick"):
    return await add_channel(
        web.db,
        wf.GUILD_ID,
        login,
        added_by=7,
        expires_at=None,
        pin=True,
        display_name=name,
    )


async def test_staff_give_a_channel_a_ping_role_from_the_site(client, sign_in, on, guild, wf):
    spotlight_id = await a_spotlight(on, wf)
    sign_in(client)

    response = client.post("/api/pings/streamers", json={"spotlight_id": str(spotlight_id)})

    assert response.status_code == 200
    row = response.json()
    assert row["kind"] == "spotlight" and row["member_id"] is None
    assert row["spotlight_id"] == spotlight_id and row["spotlight_login"] == "gamesdonequick"
    assert row["member"] == "GamesDoneQuick" and row["role"] == "GamesDoneQuick pings"
    assert row["followers"] == 0 and "GamesDoneQuick pings" in row["message"]
    held = await pings.get_spotlight_fan_role(on.db, wf.GUILD_ID, spotlight_id)
    assert held is not None and held["user_id"] is None
    assert "web.pings.fan_role_created" in await wf.kinds_in(on.db)


async def test_the_table_carries_both_kinds_and_tells_them_apart(client, sign_in, on, guild, wf):
    wf.member(guild, 21, name="namu")
    spotlight_id = await a_spotlight(on, wf)
    sign_in(client)
    client.post("/api/pings/streamers", json={"member_id": "21"})
    client.post("/api/pings/streamers", json={"spotlight_id": str(spotlight_id)})

    rows = client.get("/api/pings/streamers").json()

    assert [row["kind"] for row in rows] == ["member", "spotlight"]
    assert [row["member_id"] for row in rows] == ["21", None]
    assert [row["spotlight_id"] for row in rows] == [None, spotlight_id]


async def test_a_channel_that_is_not_spotlighted_is_refused_in_words(client, sign_in, on, wf):
    sign_in(client)

    response = client.post("/api/pings/streamers", json={"spotlight_id": "404"})

    assert response.status_code == 404
    said = response.json()
    assert said["error"] == "no_such_spotlight"
    assert "is not a spotlighted channel" in said["message"]


async def test_a_second_role_for_one_channel_is_refused_in_words(client, sign_in, on, wf):
    spotlight_id = await a_spotlight(on, wf)
    sign_in(client)
    client.post("/api/pings/streamers", json={"spotlight_id": str(spotlight_id)})

    response = client.post("/api/pings/streamers", json={"spotlight_id": str(spotlight_id)})

    assert response.status_code == 409
    assert "already has a ping role" in response.json()["message"]


async def test_staff_take_a_channels_role_away_again(client, sign_in, on, guild, wf):
    spotlight_id = await a_spotlight(on, wf)
    sign_in(client)
    client.post("/api/pings/streamers", json={"spotlight_id": str(spotlight_id)})

    response = client.delete(f"/api/pings/streamers/spotlight/{spotlight_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["removed"] is True and body["spotlight_id"] == spotlight_id
    assert body["member_id"] is None and body["role_id"]
    assert await pings.get_spotlight_fan_role(on.db, wf.GUILD_ID, spotlight_id) is None
    assert "web.pings.fan_role_removed" in await wf.kinds_in(on.db)


async def test_taking_a_role_from_a_channel_that_has_none_says_so(client, sign_in, on, wf):
    spotlight_id = await a_spotlight(on, wf)
    sign_in(client)

    response = client.delete(f"/api/pings/streamers/spotlight/{spotlight_id}")

    assert response.status_code == 404
    assert "has no ping role" in response.json()["message"]


async def test_the_streamer_list_names_the_channels_beside_the_people(
    client, sign_in, on, guild, wf
):
    spotlight_id = await a_spotlight(on, wf)
    sign_in(client)
    client.post("/api/pings/streamers", json={"spotlight_id": str(spotlight_id)})

    rows = client.get("/api/pings/list").json()

    channel = next(row for row in rows if row["kind"] == "spotlight")
    assert channel["member_id"] is None and channel["member"] == "GamesDoneQuick"
    assert channel["login"] == "gamesdonequick" and channel["listed"] is True
    assert channel["role"] == "GamesDoneQuick pings"
