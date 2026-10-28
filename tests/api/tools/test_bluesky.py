from __future__ import annotations

import pytest

ROUTES = [
    ("GET", "/api/bluesky", None),
    ("POST", "/api/bluesky/read", None),
    ("POST", "/api/bluesky/rehearse", None),
    ("POST", "/api/bluesky/rehearse", {"uri": "at://x/app.bsky.feed.post/y"}),
    ("POST", "/api/bluesky/post-latest", {"count": 2, "where": "test"}),
]


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_bluesky_route_needs_a_session(client, method, route, payload):
    assert client.request(method, route, json=payload).status_code == 401


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_bluesky_route_refuses_a_non_staff_visitor(client, sign_in, method, route, payload):
    sign_in(client, uid=1234, staff=False)
    assert client.request(method, route, json=payload).status_code == 403


async def test_the_status_starts_in_test_mode_with_nothing_read(client, sign_in, web, wf):
    sign_in(client)

    found = client.get("/api/bluesky").json()

    assert found["mode"] == "shadow" and found["handle"] == "blackinaflash.bsky.social"
    assert found["channel_id"] is None and found["seed_count"] == 2
    assert found["last_read_at"] is None and found["failures"] == 0 and found["recent"] == []


async def test_read_now_records_the_feed_and_logs_from_the_site(client, sign_in, web, wf):
    await web.store.set(wf.GUILD_ID, "shadow_channel_id", wf.TEST_CHANNEL_ID)
    sign_in(client)

    response = client.post("/api/bluesky/read")

    assert response.status_code == 200, response.json()
    assert response.json()["message"].startswith("Read 30 post(s) from @blackinaflash.bsky.social")
    found = client.get("/api/bluesky").json()
    assert found["last_ok_at"] and found["recent"]
    kinds = await wf.kinds_in(web.db)
    assert kinds.count("web.bluesky.read_now") == 1 and "bluesky.read_now" not in kinds


async def test_read_now_while_off_is_refused_in_words(client, sign_in, web, wf):
    await web.store.set(wf.GUILD_ID, "bluesky_mode", "off")
    sign_in(client)

    response = client.post("/api/bluesky/read")

    assert response.status_code == 409
    assert "bluesky_mode is off" in response.json()["message"]


async def test_post_the_latest_two_land_in_the_channel_and_a_note_field_is_ignored(
    client, sign_in, web, guild, wf
):
    await web.store.set(wf.GUILD_ID, "bluesky_channel_id", wf.OTHER_CHANNEL_ID)
    sign_in(client)

    response = client.post(
        "/api/bluesky/post-latest",
        json={"count": 2, "where": "channel", "note": "<@123456789012345678> look"},
    )

    assert response.status_code == 200, response.json()
    assert response.json()["message"] == "2 post(s) are up in #general."
    channel = guild.get_channel(wf.OTHER_CHANNEL_ID)
    assert all("<@123456789012345678>" not in message.content for message in channel.messages)
    kinds = await wf.kinds_in(web.db)
    assert kinds.count("web.bluesky.posted_latest") == 1


async def test_post_the_latest_to_the_channel_with_none_set_is_refused_in_words(
    client, sign_in, web, wf
):
    sign_in(client)

    response = client.post("/api/bluesky/post-latest", json={"count": 2, "where": "channel"})

    assert response.status_code == 409
    assert "bluesky_channel_id is blank" in response.json()["message"]


def test_a_count_out_of_range_is_refused_in_words(client, sign_in):
    sign_in(client)

    response = client.post("/api/bluesky/post-latest", json={"count": 50, "where": "test"})

    assert response.status_code == 400
    assert "1 to 10" in response.json()["message"]


async def test_post_to_test_sends_one_copy_to_the_test_channel(client, sign_in, web, guild, wf):
    await web.store.set(wf.GUILD_ID, "shadow_channel_id", wf.TEST_CHANNEL_ID)
    sign_in(client)

    response = client.post("/api/bluesky/rehearse")

    assert response.status_code == 200, response.json()
    assert response.json()["message"] == "1 post(s) are up in #blackbloc-logs."
    assert guild.get_channel(wf.TEST_CHANNEL_ID).messages[-1].content.startswith("Test copy ·")
    assert client.get("/api/bluesky").json()["recent"] == []


VIDEO_URI = "at://did:plc:4lijy65gdkw6gwwctvm6kxoc/app.bsky.feed.post/3myisto7wfc2y"


async def test_post_to_test_on_one_row_sends_that_post_with_its_buttons(
    client, sign_in, web, guild, wf
):
    await web.store.set(wf.GUILD_ID, "shadow_channel_id", wf.TEST_CHANNEL_ID)
    sign_in(client)
    client.post("/api/bluesky/read")
    before = len(guild.get_channel(wf.TEST_CHANNEL_ID).messages)

    response = client.post("/api/bluesky/rehearse", json={"uri": VIDEO_URI})

    assert response.status_code == 200, response.json()
    assert response.json()["value"]["uri"] == VIDEO_URI
    sent = guild.get_channel(wf.TEST_CHANNEL_ID).messages
    assert len(sent) == before + 1
    assert sent[-1].content.splitlines()[-1] == "🦋 **Black in a Flash!** posted on Bluesky"
    assert sent[-1].kwargs["view"] is not None
    kinds = await wf.kinds_in(web.db)
    assert kinds.count("web.bluesky.rehearsed") == 1


def test_post_to_test_on_a_post_never_seen_is_refused_in_words(client, sign_in, web, wf):
    sign_in(client)

    response = client.post(
        "/api/bluesky/rehearse", json={"uri": "at://nobody/app.bsky.feed.post/x"}
    )

    assert response.status_code == 404
    assert "has not seen that post" in response.json()["message"]
