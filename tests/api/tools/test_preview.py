from __future__ import annotations

import pytest

ROUTES = [
    ("GET", "/api/preview/features", None),
    ("POST", "/api/preview/message", {"feature": "golive_live"}),
]


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_preview_route_needs_a_session(client, method, route, payload):
    assert client.request(method, route, json=payload).status_code == 401


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_preview_route_refuses_a_member_in_words(client, sign_in, method, route, payload):
    sign_in(client, uid=1234, staff=False)

    answered = client.request(method, route, json=payload)

    assert answered.status_code == 403
    assert answered.json()["message"]
    assert "403" not in answered.json()["message"]


def test_the_features_map_names_every_key_that_has_a_mock(client, sign_in):
    sign_in(client, uid=7)

    found = client.get("/api/preview/features").json()

    assert found["keys"]["golive_template"] == "golive_live"
    assert "golive_end_suffix" not in found["keys"]
    golive = next(one for one in found["features"] if one["feature"] == "golive_live")
    assert golive["where"] == "golive.html"
    assert golive["sample"]["platform"] == "Twitch"


def test_the_announcement_comes_back_with_its_card_and_the_draft_in_it(client, sign_in):
    sign_in(client, uid=7)

    answered = client.post(
        "/api/preview/message",
        json={
            "feature": "golive_live",
            "overrides": {"golive_template": "<@&4242> {name} is live"},
        },
    )

    found = answered.json()
    assert answered.status_code == 200
    assert found["content"].endswith("Casey is live")
    assert found["embeds"][0]["author"]["name"] == "Casey is now live on Twitch!"
    assert found["mentions"]["roles"][0]["id"] == "4242"


async def test_a_preview_writes_nothing_and_logs_nothing(client, sign_in, web, wf):
    sign_in(client, uid=7)
    before = web.store.get(wf.GUILD_ID, "golive_template")
    kinds = await wf.kinds_in(web.db)

    client.post(
        "/api/preview/message",
        json={"feature": "golive_live", "overrides": {"golive_template": "drafted only"}},
    )

    assert web.store.get(wf.GUILD_ID, "golive_template") == before
    assert not web.store.is_stored(wf.GUILD_ID, "golive_template")
    assert await wf.kinds_in(web.db) == kinds


def test_a_feature_the_bot_does_not_draw_is_refused_in_words(client, sign_in):
    sign_in(client, uid=7)

    answered = client.post("/api/preview/message", json={"feature": "not_a_thing"})

    assert answered.status_code == 400
    assert answered.json()["error"] == "no_such_preview"
    assert "not_a_thing" in answered.json()["message"]


def test_a_key_from_another_message_is_refused_in_words(client, sign_in):
    sign_in(client, uid=7)

    answered = client.post(
        "/api/preview/message",
        json={"feature": "golive_live", "overrides": {"frontdoor_title": "no"}},
    )

    assert answered.status_code == 400
    assert answered.json()["error"] == "not_this_features_key"
    assert "frontdoor_title" in answered.json()["message"]


def test_the_platform_chip_moves_the_sample(client, sign_in):
    sign_in(client, uid=7)

    found = client.post(
        "/api/preview/message",
        json={"feature": "golive_live", "sample": {"platform": "youtube"}},
    ).json()

    assert "youtube.com" in found["content"]
    assert found["embeds"][0]["footer"]["text"].endswith("YouTube")
