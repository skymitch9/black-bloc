from __future__ import annotations

import pytest

from black_bloc import sticky as rules

WORDS = "How to submit a run: post the link and your time."
ROUTES = [
    ("GET", "/api/sticky", None),
    ("PUT", "/api/sticky/501", {"text": WORDS}),
    ("POST", "/api/sticky/501/pause", None),
    ("POST", "/api/sticky/501/resume", None),
    ("DELETE", "/api/sticky/501", None),
]


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_sticky_route_needs_a_session(client, method, route, payload):
    assert client.request(method, route, json=payload).status_code == 401


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_sticky_route_refuses_a_non_staff_visitor(client, sign_in, method, route, payload):
    sign_in(client, uid=1234, staff=False)
    assert client.request(method, route, json=payload).status_code == 403


async def test_a_save_rehearses_and_answers_the_row_the_page_draws(
    client, sign_in, web, guild, wf
):
    await web.store.set(wf.GUILD_ID, "shadow_channel_id", wf.TEST_CHANNEL_ID)
    sign_in(client)

    response = client.put(f"/api/sticky/{wf.OTHER_CHANNEL_ID}", json={"text": WORDS})

    assert response.status_code == 200
    found = response.json()
    assert found["sticky"]["channel_id"] == str(wf.OTHER_CHANNEL_ID)
    assert found["sticky"]["channel_name"] == "general"
    assert found["sticky"]["state"] == "rehearsing"
    assert found["sticky"]["posted_channel_id"] == str(wf.TEST_CHANNEL_ID)
    assert "shadow" in found["message"]
    assert guild.get_channel(wf.OTHER_CHANNEL_ID).messages == []
    copy = guild.get_channel(wf.TEST_CHANNEL_ID).messages[-1]
    assert copy.content.endswith(WORDS) and f"<#{wf.OTHER_CHANNEL_ID}>" in copy.content
    assert await wf.kinds_in(web.db) == ["web.sticky.set", "sticky.would_post"]


async def test_on_posts_in_the_channel_and_the_list_says_live(client, sign_in, web, guild, wf):
    await web.store.set(wf.GUILD_ID, "sticky_mode", "on")
    sign_in(client)

    client.put(f"/api/sticky/{wf.OTHER_CHANNEL_ID}", json={"text": WORDS})
    rows = client.get("/api/sticky").json()

    assert [one.content for one in guild.get_channel(wf.OTHER_CHANNEL_ID).messages] == [WORDS]
    assert [(row["channel_id"], row["state"], row["gone"]) for row in rows] == [
        (str(wf.OTHER_CHANNEL_ID), "live", False)
    ]
    assert rows[0]["text"] == WORDS and rows[0]["paused"] is False


async def test_pause_resume_and_remove_each_leave_one_web_row(client, sign_in, web, guild, wf):
    await web.store.set(wf.GUILD_ID, "sticky_mode", "on")
    sign_in(client)
    path = f"/api/sticky/{wf.OTHER_CHANNEL_ID}"
    client.put(path, json={"text": WORDS})
    here = guild.get_channel(wf.OTHER_CHANNEL_ID)

    paused = client.post(f"{path}/pause")
    assert paused.status_code == 200 and paused.json()["sticky"]["state"] == "paused"
    assert here.messages == []
    assert client.post(f"{path}/pause").json()["error"] == "already_paused"

    resumed = client.post(f"{path}/resume")
    assert resumed.status_code == 200 and resumed.json()["sticky"]["state"] == "live"
    assert len(here.messages) == 1
    assert client.post(f"{path}/resume").status_code == 409

    removed = client.delete(path)
    assert removed.json() == {
        "removed": True,
        "channel_id": str(wf.OTHER_CHANNEL_ID),
        "message": "Removed. #general has no sticky message now.",
    }
    assert here.messages == [] and client.get("/api/sticky").json() == []
    web_kinds = [kind for kind in await wf.kinds_in(web.db) if kind.startswith("web.")]
    assert web_kinds == [
        "web.sticky.set",
        "web.sticky.paused",
        "web.sticky.resumed",
        "web.sticky.removed",
    ]


def test_a_refusal_is_a_sentence_and_never_a_bare_status(client, sign_in, wf):
    sign_in(client)

    blank = client.put(f"/api/sticky/{wf.OTHER_CHANNEL_ID}", json={"text": "  "})
    voice = client.put(f"/api/sticky/{wf.VOICE_CHANNEL_ID}", json={"text": WORDS})
    nowhere = client.put("/api/sticky/424242", json={"text": WORDS})
    nothing = client.post(f"/api/sticky/{wf.OTHER_CHANNEL_ID}/pause")
    gone = client.delete(f"/api/sticky/{wf.OTHER_CHANNEL_ID}")
    words = client.put("/api/sticky/general", json={"text": WORDS})

    assert (blank.status_code, blank.json()["error"]) == (400, "bad_text")
    assert (voice.status_code, voice.json()["error"]) == (400, "not_postable")
    assert (nowhere.status_code, nowhere.json()["error"]) == (404, "no_such_channel")
    assert (nothing.status_code, nothing.json()["message"]) == (404, rules.NO_STICKY)
    assert gone.status_code == 404 and words.status_code == 400
    for refused in (blank, voice, nowhere, nothing, gone, words):
        assert len(refused.json()["message"].split()) > 6


@pytest.mark.parametrize("given", [["a", "b"], {"a": 1}, 7, True])
def test_words_that_are_not_a_string_are_refused_and_nothing_is_stored(client, sign_in, wf, given):
    sign_in(client)

    refused = client.put(f"/api/sticky/{wf.OTHER_CHANNEL_ID}", json={"text": given})

    assert (refused.status_code, refused.json()["error"]) == (400, "bad_text")
    assert refused.json()["message"] == rules.NOT_WORDS
    assert client.get("/api/sticky").json() == []


async def test_the_page_is_answered_in_channel_names_never_discord_markup(
    client, sign_in, web, wf
):
    sign_in(client)
    path = f"/api/sticky/{wf.OTHER_CHANNEL_ID}"

    off = client.put(path, json={"text": WORDS})
    assert "<#" not in off.json()["message"] and "`" not in off.json()["message"]

    await web.store.set(wf.GUILD_ID, "shadow_channel_id", wf.TEST_CHANNEL_ID)
    saved = client.put(path, json={"text": WORDS}).json()
    voice = client.put(f"/api/sticky/{wf.VOICE_CHANNEL_ID}", json={"text": WORDS}).json()
    await rules.write_trouble(
        web.db, wf.GUILD_ID, wf.OTHER_CHANNEL_ID, rules.TROUBLE_HOME_GONE.format(home=424242)
    )
    listed = client.get("/api/sticky").json()[0]
    paused = client.post(f"{path}/pause").json()
    removed = client.delete(path).json()

    assert "#general" in saved["message"] and "**shadow**" in saved["message"]
    assert "#voice" in voice["message"]
    assert "424242" in listed["trouble"] and "sticky_shadow_channel_id" in listed["trouble"]
    for words in (saved["message"], voice["message"], listed["trouble"], paused["message"]):
        assert "<#" not in words and "`" not in words
    assert removed["message"] == "Removed. #general has no sticky message now."


async def test_a_sticky_whose_channel_is_gone_still_lists_so_it_can_be_removed(
    client, sign_in, web, wf
):
    await rules.write_words(web.db, wf.GUILD_ID, 424242, WORDS, 7)
    sign_in(client)

    rows = client.get("/api/sticky").json()

    assert rows[0]["gone"] is True and rows[0]["channel_name"] is None
    assert client.delete("/api/sticky/424242").status_code == 200


async def test_a_post_can_be_the_sticky_and_the_list_names_it(client, sign_in, web, guild, wf):
    from black_bloc import posts

    await web.store.set(wf.GUILD_ID, "sticky_mode", "on")
    await posts.create_post(
        web.db, wf.GUILD_ID, slug="rules", title="House rules", body="Be kind.", pin=False
    )
    sign_in(client)

    saved = client.put(f"/api/sticky/{wf.OTHER_CHANNEL_ID}", json={"post": "rules"})
    missing = client.put(f"/api/sticky/{wf.TEST_CHANNEL_ID}", json={"post": "nothing"})
    rows = client.get("/api/sticky").json()

    assert saved.status_code == 200, saved.text
    assert saved.json()["sticky"]["post"]["slug"] == "rules"
    assert [one.content for one in guild.get_channel(wf.OTHER_CHANNEL_ID).messages] == [
        "Be kind."
    ]
    assert rows[0]["words"] == "The post **House rules**" and rows[0]["state"] == "live"
    assert missing.status_code == 404 and missing.json()["error"] == "no_such_post"
