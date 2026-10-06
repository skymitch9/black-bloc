from __future__ import annotations

from datetime import UTC, datetime

import pytest

from black_bloc import pb_store
from black_bloc.pb_looks import Feed
from black_bloc.speedrun import UNREACHABLE, SpeedrunError
from tests.test_pb_looks import NOW, ZFG, FakeClient, best, link

ADA = 900
BEA = 901
GONE = 999
ROUTES = [
    ("GET", "/api/pbs", None),
    ("PUT", "/api/pbs/900", {"runner": "zfg"}),
    ("DELETE", "/api/pbs/900", None),
    ("POST", "/api/pbs/900/block", None),
    ("POST", "/api/pbs/900/unblock", None),
    ("POST", "/api/pbs/900/optin", None),
    ("POST", "/api/pbs/900/look", None),
]


@pytest.fixture
def speedrun(web):
    """The module's one bot keeps its feed between tests, so each test hands it a fresh fake."""
    found = FakeClient()
    web._pb_feed = Feed(web, found)
    yield found
    del web._pb_feed


@pytest.fixture
def people(guild, wf):
    wf.member(guild, ADA, name="ada")
    wf.member(guild, BEA, name="bea")
    wf.member(guild, 7, name="sky", staff=True)


async def match(web, wf, user_id=ADA, runner=ZFG, login="zfg1"):
    await link(web.db, user_id, login)
    return await pb_store.write_match(
        web.db, wf.GUILD_ID, user_id, runner, source="auto", twitch_login=login, now=NOW
    )


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_route_needs_a_session(client, method, route, payload):
    assert client.request(method, route, json=payload).status_code == 401


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_route_refuses_a_non_staff_visitor(client, sign_in, method, route, payload):
    sign_in(client, uid=1234, staff=False)
    assert client.request(method, route, json=payload).status_code == 403


def test_the_index_starts_in_shadow_with_nobody_and_nothing(client, sign_in, speedrun):
    sign_in(client)

    found = client.get("/api/pbs").json()

    assert found == {
        "mode": "shadow",
        "interval_minutes": 60,
        "last_look": None,
        "people": [],
        "posts": [],
    }


async def test_the_index_lists_the_linked_and_the_matched_with_how_and_when(
    client, sign_in, web, wf, people, speedrun
):
    await match(web, wf)
    await link(web.db, BEA, "bea_tv")
    await link(web.db, GONE, "left_the_server")
    await pb_store.record_look(web.db, wf.GUILD_ID, ADA, [best("r1")], first=True, now=NOW)
    await pb_store.record_ok(web.db, wf.GUILD_ID, found=0, now=NOW)
    sign_in(client)

    found = client.get("/api/pbs").json()

    assert [(one["name"], one["state"]) for one in found["people"]] == [
        ("Ada", "matched"),
        ("Bea", None),
    ]
    ada = found["people"][0]
    assert (ada["user_id"], ada["runner"], ada["source"], ada["twitch_login"]) == (
        str(ADA),
        "zfg",
        "auto",
        "zfg1",
    )
    assert ada["runner_link"] == "https://www.speedrun.com/users/zfg"
    assert ada["looked_at"] == NOW.isoformat() == ada["baseline_at"] and ada["here"] is True
    assert found["last_look"]["outcome"] == "ok" and found["last_look"]["asks_again_at"] is None


async def test_a_matched_member_who_left_is_still_listed_and_marked(
    client, sign_in, web, wf, speedrun
):
    await match(web, wf, GONE)
    sign_in(client)

    found = client.get("/api/pbs").json()["people"]

    assert [(one["user_id"], one["here"]) for one in found] == [(str(GONE), False)]


async def test_set_by_hand_matches_and_leaves_one_web_row(
    client, sign_in, web, wf, people, speedrun
):
    speedrun.by_name["zfg"] = [ZFG]
    sign_in(client)

    response = client.put(f"/api/pbs/{ADA}", json={"runner": "zfg"})

    assert response.status_code == 200
    found = response.json()
    assert found["person"]["state"] == "matched" and found["person"]["source"] == "staff"
    assert "is now matched to **zfg**" in found["message"]
    details = await wf.one_web_row(web.db, "web.pbfeed.set_by_hand")
    assert details["runner"] == "zfg"


async def test_a_name_speedrun_does_not_have_is_a_404_in_words(
    client, sign_in, web, wf, people, speedrun
):
    sign_in(client)

    response = client.put(f"/api/pbs/{ADA}", json={"runner": "nobody"})

    assert response.status_code == 404
    assert "no single account named exactly **nobody**" in response.text
    assert await wf.kinds_in(web.db) == []


async def test_an_outage_is_a_502_that_says_network_not_permission(
    client, sign_in, web, wf, people, speedrun
):
    speedrun.raises = SpeedrunError(UNREACHABLE, why="TimeoutError")
    sign_in(client)

    response = client.put(f"/api/pbs/{ADA}", json={"runner": "zfg"})

    assert response.status_code == 502
    assert "could not be reached" in response.text and "permission" not in response.text


async def test_a_runner_someone_else_holds_is_a_409_naming_them(
    client, sign_in, web, wf, people, speedrun
):
    await match(web, wf)
    speedrun.by_name["zfg"] = [ZFG]
    sign_in(client)

    response = client.put(f"/api/pbs/{BEA}", json={"runner": "zfg"})

    assert response.status_code == 409 and f"<@{ADA}>" in response.text


async def test_unmatch_block_and_unblock_walk_one_member_through_the_states(
    client, sign_in, web, wf, people, speedrun
):
    await match(web, wf)
    sign_in(client)

    unmatched = client.delete(f"/api/pbs/{ADA}").json()
    blocked = client.post(f"/api/pbs/{ADA}/block").json()
    unblocked = client.post(f"/api/pbs/{ADA}/unblock").json()

    assert [one["person"]["state"] for one in (unmatched, blocked, unblocked)] == [
        "none",
        "blocked",
        "none",
    ]
    assert unmatched["person"]["runner"] is None
    assert await wf.kinds_in(web.db) == [
        "web.pbfeed.unmatched",
        "web.pbfeed.blocked",
        "web.pbfeed.unblocked",
    ]


async def test_staff_clear_a_members_opt_out(client, sign_in, web, wf, people, speedrun):
    await match(web, wf)
    await pb_store.write_state(
        web.db, wf.GUILD_ID, ADA, pb_store.OPTED_OUT, state_by="member", keep_runner=True
    )
    sign_in(client)

    refused = client.delete(f"/api/pbs/{ADA}")
    cleared = client.post(f"/api/pbs/{ADA}/optin")

    assert refused.status_code == 409 and "asked not to have" in refused.text
    assert cleared.json()["person"]["state"] == "matched"
    await wf.one_web_row(web.db, "web.pbfeed.opt_out_cleared")


async def test_a_move_that_does_not_apply_is_a_409_in_words(
    client, sign_in, web, wf, people, speedrun
):
    sign_in(client)

    for route in ("unblock", "optin", "look"):
        response = client.post(f"/api/pbs/{BEA}/{route}")
        assert response.status_code == 409 and "nothing was done" in response.text


async def test_look_now_rehearses_the_news_and_the_index_lists_the_post(
    client, sign_in, web, guild, wf, people, speedrun
):
    await web.store.set(wf.GUILD_ID, "shadow_channel_id", wf.TEST_CHANNEL_ID)
    await match(web, wf)
    await pb_store.record_look(web.db, wf.GUILD_ID, ADA, [best("r1")], first=True, now=NOW)
    speedrun.bests[ZFG.id] = [best("r9", seconds=90.0, verified_at=datetime.now(UTC))]
    sign_in(client)

    response = client.post(f"/api/pbs/{ADA}/look")

    assert response.status_code == 200
    assert "1 new personal best(s)" in response.json()["message"]
    copy = guild.get_channel(wf.TEST_CHANNEL_ID).messages[-1]
    assert "Rehearsal" in copy.content
    posts = client.get("/api/pbs").json()["posts"]
    assert [(one["run_id"], one["outcome"]) for one in posts] == [("r9", "rehearsed")]
    assert (posts[0]["name"], posts[0]["game"], posts[0]["seconds"]) == (
        "Ada",
        "Ocarina of Time",
        90.0,
    )
    assert posts[0]["channel_id"] == str(wf.TEST_CHANNEL_ID)
    assert await wf.kinds_in(web.db) == ["pbfeed.would_post", "web.pbfeed.looked"]


async def test_look_now_is_refused_while_the_feed_is_off(
    client, sign_in, web, wf, people, speedrun
):
    await match(web, wf)
    await web.store.set(wf.GUILD_ID, "pb_feed_mode", "off")
    sign_in(client)

    response = client.post(f"/api/pbs/{ADA}/look")

    assert response.status_code == 409 and "pb_feed_mode" in response.text
    assert speedrun.asked == []


def test_an_id_that_is_not_a_number_is_a_400_in_words(client, sign_in, speedrun):
    sign_in(client)

    response = client.post("/api/pbs/not-a-number/block")

    assert response.status_code == 400 and "is not an id" in response.text

