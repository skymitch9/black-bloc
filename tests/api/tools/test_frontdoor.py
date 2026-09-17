from __future__ import annotations

import pytest

from black_bloc.frontdoor import LABEL_DEFAULTS, TICKET
from black_bloc.settings_store import FRONTDOOR_TITLE_DEFAULT

ROUTES = [
    ("POST", "/api/frontdoor/panel", {"channel_id": "1"}),
    ("DELETE", "/api/frontdoor/panel", None),
]


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_front_door_route_needs_a_session(client, method, route, payload):
    assert client.request(method, route, json=payload).status_code == 401


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_front_door_route_refuses_a_member_in_words(
    client, sign_in, method, route, payload
):
    sign_in(client, uid=1234, staff=False)
    answered = client.request(method, route, json=payload)

    assert answered.status_code == 403
    assert answered.json()["message"]


async def test_the_front_door_is_posted_and_taken_down_from_the_website(
    client, sign_in, web, guild, wf
):
    sign_in(client, uid=7)

    posted = client.post("/api/frontdoor/panel", json={"channel_id": str(wf.TEST_CHANNEL_ID)})

    assert posted.status_code == 200 and posted.json()["posted"] is True
    assert posted.json()["channel_id"] == str(wf.TEST_CHANNEL_ID)
    assert web.store.get(wf.GUILD_ID, "frontdoor_channel_id") == wf.TEST_CHANNEL_ID
    channel = guild.get_channel(wf.TEST_CHANNEL_ID)
    sent = channel.messages[-1].kwargs
    assert sent["embed"].title == FRONTDOOR_TITLE_DEFAULT
    assert [one.item.label for one in sent["view"].children] == list(LABEL_DEFAULTS.values())

    down = client.delete("/api/frontdoor/panel")

    assert down.status_code == 200 and down.json()["taken_down"] is True
    assert web.store.get(wf.GUILD_ID, "frontdoor_channel_id") is None
    assert web.store.get(wf.GUILD_ID, "frontdoor_message_id") is None
    kinds = await wf.kinds_in(web.db)
    assert "web.frontdoor.posted" in kinds
    assert "web.frontdoor.taken_down" in kinds
    assert "frontdoor.posted" not in kinds


async def test_posting_the_front_door_twice_moves_it_and_leaves_one_row_each_time(
    client, sign_in, web, guild, wf
):
    sign_in(client, uid=7)

    client.post("/api/frontdoor/panel", json={"channel_id": str(wf.TEST_CHANNEL_ID)})
    again = client.post("/api/frontdoor/panel", json={"channel_id": str(wf.TEST_CHANNEL_ID)})

    assert again.status_code == 200
    kinds = await wf.kinds_in(web.db)
    assert "web.frontdoor.moved" in kinds
    assert "frontdoor.moved" not in kinds


def test_the_front_door_needs_a_channel_the_bot_can_see(client, sign_in):
    sign_in(client)

    assert client.post("/api/frontdoor/panel", json={}).status_code == 400
    refused = client.post("/api/frontdoor/panel", json={"channel_id": "404"}).json()
    assert refused["error"] == "no_such_channel"
    assert "Pick one from the list" in refused["message"]


async def test_the_front_door_rehearses_in_the_home_when_test_mode_refuses_its_channel(
    client, sign_in, web, guild, wf
):
    web.guard = wf.Guard()
    sign_in(client)

    posted = client.post("/api/frontdoor/panel", json={"channel_id": str(wf.OTHER_CHANNEL_ID)})

    assert posted.status_code == 200
    assert guild.get_channel(wf.OTHER_CHANNEL_ID).messages == []
    assert guild.get_channel(wf.TEST_CHANNEL_ID).messages
    assert web.store.get(wf.GUILD_ID, "frontdoor_channel_id") == wf.OTHER_CHANNEL_ID
    assert web.store.get(wf.GUILD_ID, "frontdoor_shadow_message_id")
    assert "web.frontdoor.posted_shadow" in await wf.kinds_in(web.db)


async def test_the_front_door_is_refused_in_words_when_there_is_no_rehearsal_home_at_all(
    client, sign_in, web, guild, wf
):
    web.guard = wf.Guard(test_channel_id=0)
    sign_in(client)

    refused = client.post("/api/frontdoor/panel", json={"channel_id": str(wf.OTHER_CHANNEL_ID)})

    assert refused.status_code == 409 and refused.json()["error"] == "test_mode"
    assert "test mode" in refused.json()["message"]
    assert web.store.get(wf.GUILD_ID, "frontdoor_channel_id") is None
    assert guild.get_channel(wf.OTHER_CHANNEL_ID).messages == []
    assert "web.frontdoor.would_post" in await wf.kinds_in(web.db)


def test_taking_down_a_door_that_is_not_up_says_so_rather_than_pretending(client, sign_in):
    sign_in(client)

    said = client.delete("/api/frontdoor/panel")

    assert said.status_code == 200
    assert said.json()["taken_down"] is False
    assert "no front door posted" in said.json()["message"]


async def test_the_website_door_takes_the_ticket_button_down_in_the_same_channel(
    client, sign_in, web, guild, wf
):
    sign_in(client, uid=7)
    client.post("/api/modmail/panel", json={"channel_id": str(wf.TEST_CHANNEL_ID)})
    button_id = web.store.get(wf.GUILD_ID, "modmail_panel_message_id")

    client.post("/api/frontdoor/panel", json={"channel_id": str(wf.TEST_CHANNEL_ID)})

    assert button_id
    assert not web.store.get(wf.GUILD_ID, "modmail_panel_message_id")
    assert web.store.get(wf.GUILD_ID, "modmail_panel_channel_id") == wf.TEST_CHANNEL_ID
    assert "frontdoor.ticket_button_hidden" in await wf.kinds_in(web.db)


def test_the_three_labels_are_the_words_the_card_draws(client, sign_in, web, guild, wf):
    sign_in(client)
    assert LABEL_DEFAULTS[TICKET] == "Ask staff privately"

    client.post("/api/frontdoor/panel", json={"channel_id": str(wf.TEST_CHANNEL_ID)})
    sent = guild.get_channel(wf.TEST_CHANNEL_ID).messages[-1].kwargs

    assert sent["view"].timeout is None
    assert all(one.item.custom_id.startswith("door:") for one in sent["view"].children)
