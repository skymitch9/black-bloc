from __future__ import annotations

import pytest

from black_bloc import posts

ROUTES = [
    ("GET", "/api/posts", None),
    ("GET", "/api/posts/notice", None),
    ("POST", "/api/posts", {"title": "A notice"}),
    ("PUT", "/api/posts/notice", {"body": "hello"}),
    ("POST", "/api/posts/notice/publish", {}),
    ("POST", "/api/posts/notice/takedown", {}),
    ("POST", "/api/posts/notice/reset", {}),
    ("DELETE", "/api/posts/notice", None),
]


async def a_post(web, wf, *, slug="notice", body="Hello.", channel=True, **fields):
    return await posts.create_post(
        web.db,
        wf.GUILD_ID,
        slug=slug,
        title="A notice",
        body=body,
        channel_id=wf.TEST_CHANNEL_ID if channel else None,
        **fields,
    )


@pytest.fixture(autouse=True)
async def mode_is_on(web, wf):
    """Shadow is the key's default; every test that does not say otherwise is `on`."""
    await web.store.set(wf.GUILD_ID, posts.MODE_KEY, "on")


async def seeded_post(web, guild, wf):
    """The shipped post, with its channel pointed at one this guild actually has."""
    await posts.seed_posts(web, guild)
    row = await posts.get_post(web.db, wf.GUILD_ID, "welcome")
    await posts.set_post_fields(web.db, int(row["id"]), channel_id=wf.TEST_CHANNEL_ID)
    return await posts.get_post(web.db, wf.GUILD_ID, "welcome")


@pytest.mark.parametrize("method,route,payload", ROUTES)
def test_every_route_is_staff_only(client, sign_in, web, wf, method, route, payload):
    sign_in(client, uid=9, staff=False)

    response = client.request(method, route, json=payload)

    assert response.status_code == 403
    assert response.json()["error"] == "not_staff"


@pytest.mark.parametrize("method,route,payload", ROUTES)
def test_every_route_says_so_when_nobody_is_signed_in(client, web, wf, method, route, payload):
    client.cookies.clear()

    response = client.request(method, route, json=payload)

    assert response.status_code == 401
    assert response.json()["error"] == "not_signed_in"


async def test_the_list_carries_the_pills_the_page_draws(client, sign_in, web, wf):
    sign_in(client)
    await a_post(web, wf)
    await a_post(web, wf, slug="empty", body="", channel=False)

    found = client.get("/api/posts").json()

    assert [one["slug"] for one in found["posts"]] == ["notice", "empty"]
    first, second = found["posts"]
    assert first["channel_name"] == "blackbloc-logs"
    assert first["status"] == ["not posted"] and first["move"] == "Post it"
    assert first["cap"] == 2000 and first["title_cap"] == 256
    assert second["channel_id"] is None and second["channel_name"] is None
    assert found["mode"] == "on" and found["may_edit"] is True
    assert [one["style"] for one in found["styles"]] == ["plain", "embed"]
    assert found["guard"]["test_mode"] is False and found["guard"]["said"] is None
    assert found["notes"] == []


async def test_shadow_says_where_the_copy_goes_and_names_the_shadow_channel(
    client, sign_in, web, guild, wf
):
    """§C9: the page has to be able to say `not #welcome, #blackbloc-logs` before anybody
    presses anything."""
    sign_in(client)
    await a_post(web, wf)
    await web.store.set(wf.GUILD_ID, posts.MODE_KEY, "shadow")
    web.guard = wf.Guard()

    found = client.get("/api/posts").json()

    assert found["mode"] == "shadow"
    assert found["shadow"] == {
        "channel_id": str(wf.TEST_CHANNEL_ID),
        "channel_name": "blackbloc-logs",
    }
    assert found["notes"] and "#blackbloc-logs" in found["notes"][0]
    assert "nothing reaches members yet" in found["notes"][0]


async def test_a_shadow_publish_names_the_shadow_channel_and_marks_the_row(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await a_post(web, wf, channel=False)
    await posts.set_post_fields(
        web.db,
        int((await posts.get_post(web.db, wf.GUILD_ID, "notice"))["id"]),
        channel_id=wf.OTHER_CHANNEL_ID,
    )
    await web.store.set(wf.GUILD_ID, posts.MODE_KEY, "shadow")
    web.guard = wf.Guard()

    found = client.post("/api/posts/notice/publish", json={}).json()

    assert guild.get_channel(wf.OTHER_CHANNEL_ID).messages == []
    assert len(guild.get_channel(wf.TEST_CHANNEL_ID).messages) == 1
    assert "#blackbloc-logs" in found["message"] and "shadow copy" in found["message"]
    assert found["post"]["message_id"] is None
    assert found["post"]["shadow_message_id"]
    assert found["post"]["posted_where"] == "shadow"
    assert found["post"]["status"][0] == "posted (shadow)"
    assert found["post"]["move"] == "Update the post"
    assert [kind for kind, _ in await wf.web_rows_in(web.db)] == [
        "web.post.shadow_posted",
        "web.post.pinned",
    ]


async def test_posts_off_refuses_the_publish_in_words(client, sign_in, web, wf):
    sign_in(client)
    await a_post(web, wf)
    await web.store.set(wf.GUILD_ID, posts.MODE_KEY, "off")

    response = client.post("/api/posts/notice/publish", json={})

    assert response.status_code == 409
    assert response.json()["error"] == "posts_off"
    assert "Settings page" in response.json()["message"]
    assert await wf.web_rows_in(web.db) == []


async def test_the_page_is_told_in_words_when_posts_are_off(client, sign_in, web, wf):
    sign_in(client)
    await a_post(web, wf)
    await web.store.set(wf.GUILD_ID, posts.MODE_KEY, "off")

    found = client.get("/api/posts").json()

    assert found["mode"] == "off"
    assert found["notes"] and "Settings page under **posts**" in found["notes"][0]


async def test_test_mode_is_said_in_words_rather_than_left_to_be_discovered(
    client, sign_in, web, wf
):
    sign_in(client)
    await a_post(web, wf)
    web.settings.test_mode = True

    found = client.get("/api/posts").json()

    assert found["guard"]["test_mode"] is True
    assert found["guard"]["test_channel"] == "blackbloc-logs"
    assert "#blackbloc-logs" in found["guard"]["said"]


async def test_a_post_that_is_not_there_is_refused_by_name(client, sign_in, web, wf):
    sign_in(client)

    response = client.get("/api/posts/nothing-here")

    assert response.status_code == 404
    assert response.json()["error"] == "no_such_post"
    assert "**nothing-here**" in response.json()["message"]


async def test_making_one_leaves_one_row_and_no_message(client, sign_in, web, wf):
    sign_in(client)

    found = client.post("/api/posts", json={"title": "When staff are around"}).json()

    assert found["post"]["slug"] == "when-staff-are-around"
    assert found["post"]["body"] == "" and found["post"]["posted"] is False
    assert "Nothing is in Discord" in found["message"]
    assert await wf.one_web_row(web.db, "web.post.created")


async def test_saving_leaves_exactly_one_row_and_never_notes_it_twice(client, sign_in, web, wf):
    """Checklist 34: the shared move logs it, so the route must not note it on top."""
    sign_in(client)
    await a_post(web, wf)

    found = client.put("/api/posts/notice", json={"body": "Written on the site."}).json()

    assert found["post"]["body"] == "Written on the site."
    assert found["message"] == "**A notice** is saved."
    details = await wf.one_web_row(web.db, "web.post.saved")
    assert details["slug"] == "notice"


async def test_over_the_cap_is_a_400_with_the_count_in_the_sentence(client, sign_in, web, wf):
    sign_in(client)
    await a_post(web, wf)

    response = client.put("/api/posts/notice", json={"body": "x" * 2050})

    assert response.status_code == 400
    assert response.json()["error"] == "body_too_long"
    assert "2050" in response.json()["message"] and "2000" in response.json()["message"]
    assert await wf.web_rows_in(web.db) == []


async def test_a_channel_the_server_does_not_have_is_refused_in_words(client, sign_in, web, wf):
    sign_in(client)
    await a_post(web, wf)

    response = client.put("/api/posts/notice", json={"channel_id": "123456"})

    assert response.status_code == 400
    assert response.json()["error"] == "unknown_channel"
    assert "123456" in response.json()["message"]


async def test_posting_sends_once_and_posting_again_edits_the_same_message(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await a_post(web, wf)
    channel = guild.get_channel(wf.TEST_CHANNEL_ID)

    first = client.post("/api/posts/notice/publish", json={}).json()

    assert len(channel.messages) == 1
    assert channel.messages[0].pinned is True
    assert first["post"]["posted"] is True and first["post"]["changes_pending"] is False
    assert "#blackbloc-logs" in first["message"]

    client.put("/api/posts/notice", json={"body": "Changed."})
    pending = client.get("/api/posts/notice").json()
    assert pending["post"]["changes_pending"] is True
    assert "changes not yet posted" in pending["post"]["status"]

    second = client.post("/api/posts/notice/publish", json={}).json()

    assert len(channel.messages) == 1, "a second press never leaves a second copy"
    assert channel.messages[0].kwargs["content"] == "Changed."
    assert second["post"]["changes_pending"] is False
    assert [kind for kind in await wf.kinds_in(web.db) if kind.startswith("web.")] == [
        "web.post.posted",
        "web.post.pinned",
        "web.post.saved",
        "web.post.updated",
    ]


async def test_the_guard_answers_the_same_409_every_other_write_answers(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    web.guard = wf.Guard()
    await a_post(web, wf, channel=False)
    await posts.set_post_fields(
        web.db,
        int((await posts.get_post(web.db, wf.GUILD_ID, "notice"))["id"]),
        channel_id=wf.OTHER_CHANNEL_ID,
    )

    response = client.post("/api/posts/notice/publish", json={})

    assert response.status_code == 409
    assert response.json()["error"] == "test_mode"
    assert "test mode" in response.json()["message"]
    assert guild.get_channel(wf.OTHER_CHANNEL_ID).messages == []
    assert await wf.one_web_row(web.db, "web.post.would_post")


async def test_a_post_with_no_channel_is_refused_before_anything_is_sent(client, sign_in, web, wf):
    sign_in(client)
    await a_post(web, wf, channel=False)

    response = client.post("/api/posts/notice/publish", json={})

    assert response.status_code == 409
    assert response.json()["error"] == "no_channel"
    assert "**Channel**" in response.json()["message"]


async def test_taking_it_down_removes_the_message_and_keeps_the_words(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await a_post(web, wf)
    client.post("/api/posts/notice/publish", json={})
    channel = guild.get_channel(wf.TEST_CHANNEL_ID)

    found = client.post("/api/posts/notice/takedown", json={}).json()

    assert channel.messages == []
    assert found["post"]["posted"] is False and found["post"]["body"] == "Hello."
    assert "Every word is still here" in found["message"]


async def test_a_post_that_is_not_posted_refuses_the_take_down(client, sign_in, web, wf):
    sign_in(client)
    await a_post(web, wf)

    response = client.post("/api/posts/notice/takedown", json={})

    assert response.status_code == 409
    assert response.json()["error"] == "not_posted"


async def test_put_the_original_back_only_works_on_the_shipped_post(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await seeded_post(web, guild, wf)
    await a_post(web, wf)
    client.put("/api/posts/welcome", json={"body": "Staff wrote this."})

    found = client.post("/api/posts/welcome/reset", json={}).json()
    refused = client.post("/api/posts/notice/reset", json={})

    assert found["post"]["body"] == posts.seed_entries()[0]["body"]
    assert found["post"]["channel_id"] == str(wf.TEST_CHANNEL_ID), "the channel is kept"
    assert refused.status_code == 409 and refused.json()["error"] == "not_seeded"


async def test_the_shipped_post_cannot_be_deleted_and_says_what_to_do_instead(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await seeded_post(web, guild, wf)

    response = client.delete("/api/posts/welcome")

    assert response.status_code == 409
    assert response.json()["error"] == "seeded_post"
    assert "Take it down" in response.json()["message"]


async def test_a_posted_post_is_taken_down_before_it_can_be_deleted(client, sign_in, web, wf):
    sign_in(client)
    await a_post(web, wf)
    client.post("/api/posts/notice/publish", json={})

    still = client.delete("/api/posts/notice")
    client.post("/api/posts/notice/takedown", json={})
    gone = client.delete("/api/posts/notice")

    assert still.status_code == 409 and still.json()["error"] == "still_posted"
    assert gone.status_code == 200 and gone.json()["deleted"] == "notice"
    assert await posts.get_post(web.db, wf.GUILD_ID, "notice") is None


async def test_the_seeded_flag_and_the_move_label_travel_with_the_row(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    await seeded_post(web, guild, wf)

    before = client.get("/api/posts/welcome").json()["post"]
    client.post("/api/posts/welcome/publish", json={})
    after = client.get("/api/posts/welcome").json()["post"]

    assert before["seeded"] is True and before["move"] == "Post it"
    assert after["move"] == "Update the post"
    assert after["posted_by"] == "7" and after["posted_at"]
