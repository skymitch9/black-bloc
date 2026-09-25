from __future__ import annotations

import json
import pathlib

import pytest

from black_bloc.cogs.content.marathon import Marathons, get_marathon
from black_bloc.cogs.content.marathon_feeds import get_feed, insert_feed
from black_bloc.cogs.content.spotlight import add_channel
from black_bloc.marathon_sources import ScheduleError

FIXTURES = pathlib.Path(__file__).parents[2] / "fixtures" / "marathon"
GDQ_BASE = "https://tracker.gamesdonequick.com/tracker"

ROUTES = [
    ("GET", "/api/marathons/feeds"),
    ("POST", "/api/marathons/feeds"),
    ("PATCH", "/api/marathons/feeds/1"),
    ("DELETE", "/api/marathons/feeds/1"),
    ("POST", "/api/marathons/feeds/1/check"),
    ("POST", "/api/marathons/feeds/1/look"),
    ("POST", "/api/marathons/feeds/1/forget"),
    ("POST", "/api/marathons/feeds/1/add"),
]


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FeedClient:
    def __init__(self):
        self.events_given = fixture("gdq_events_list.json")["results"]
        self.horaro = {"esa": fixture("horaro_esa_schedules.json")["data"]}
        self.raises = None

    async def events(self, source="gdq"):
        if self.raises is not None:
            raise self.raises
        return list(self.events_given) if source == "gdq" else []

    async def horaro_schedules(self, slug):
        if slug not in self.horaro:
            raise ScheduleError(f"horaro.net has no event {slug}")
        return list(self.horaro[slug])

    async def resolve(self, source, ref):
        return (str(ref), f"{source} {ref}")

    async def runs(self, source, ref):
        return []

    async def close(self):
        return None


@pytest.fixture
async def cog(web, wf):
    await web.store.set(wf.GUILD_ID, "marathon_mode", "on")
    await web.store.set(wf.GUILD_ID, "marathon_event_mode_default", "none")
    made = Marathons(web)
    made.client = FeedClient()
    web.cogs["Marathons"] = made
    return made


async def channel(web, wf, login, name):
    return await add_channel(
        web.db, wf.GUILD_ID, login, added_by=7, expires_at=None, pin=False, display_name=name
    )


async def gdq_feed(web, wf, action="add"):
    spotlight_id = await channel(web, wf, "gamesdonequick", "GamesDoneQuick")
    return await insert_feed(
        web.db,
        wf.GUILD_ID,
        source="tracker",
        feed_ref=GDQ_BASE,
        spotlight_id=spotlight_id,
        name="GDQ",
        action=action,
        added_by=7,
    )


@pytest.mark.parametrize(("method", "route"), ROUTES)
def test_every_feed_route_needs_a_session(client, method, route):
    assert client.request(method, route).status_code == 401


@pytest.mark.parametrize(("method", "route"), ROUTES)
def test_every_feed_route_refuses_a_non_staff_visitor(client, sign_in, method, route):
    sign_in(client, uid=1234, staff=False)
    assert client.request(method, route).status_code == 403


async def test_the_list_carries_feeds_and_the_channel_rows_a_feed_may_start_from(
    client, sign_in, web, wf, cog
):
    feed_id = await gdq_feed(web, wf)
    await channel(web, wf, "esamarathon", "ESAMarathon")
    sign_in(client)
    body = client.get("/api/marathons/feeds").json()
    assert body["enabled"] is True and body["hours"] == 6 and body["action_default"] == "add"
    assert [one["id"] for one in body["feeds"]] == [feed_id]
    gdq = body["feeds"][0]
    assert gdq["source"] == "gdq" and gdq["source_word"] == "GDQ tracker"
    assert gdq["channel_name"] == "GamesDoneQuick" and gdq["last_checked_at"] is None
    channels = {one["login"]: one for one in body["channels"]}
    assert channels["gamesdonequick"]["feed_name"] == "GDQ"
    assert channels["esamarathon"]["feed_name"] is None
    assert [one["value"] for one in body["sources"]] == ["gdq", "rpglb", "horaro"]


async def test_adding_a_horaro_feed_checks_it_and_leaves_one_web_row(
    client, sign_in, web, wf, cog
):
    esa = await channel(web, wf, "esamarathon", "ESAMarathon")
    sign_in(client)
    response = client.post(
        "/api/marathons/feeds",
        json={"spotlight_id": esa, "source": "horaro", "slug": "esa", "action": "suggest"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "horaro" and body["feed_ref"] == "esa"
    assert body["action"] == "suggest" and body["last_checked_at"] is not None
    assert "horaro.net/esa" in body["message"]
    assert (await wf.one_web_row(web.db, "web.marathon.feed_created"))["feed"] == "ESAMarathon"


async def test_add_a_feed_refuses_in_words(client, sign_in, web, wf, cog):
    esa = await channel(web, wf, "esamarathon", "ESAMarathon")
    await gdq_feed(web, wf)
    sign_in(client)
    for given, status, code in (
        ({"spotlight_id": 9999, "source": "gdq"}, 404, "no_channel"),
        ({"spotlight_id": esa, "source": "oengus"}, 422, "unknown_source"),
        ({"spotlight_id": esa, "source": "horaro"}, 422, "no_slug"),
        ({"spotlight_id": esa, "source": "horaro", "slug": "nope"}, 422, "slug_unreadable"),
    ):
        response = client.post("/api/marathons/feeds", json=given)
        assert response.status_code == status, (given, response.text)
        assert response.json()["error"] == code
        assert response.json()["message"]
    other = client.get("/api/marathons/feeds").json()["feeds"][0]
    twice = client.post(
        "/api/marathons/feeds", json={"spotlight_id": other["spotlight_id"], "source": "gdq"}
    )
    assert twice.status_code == 409 and "One channel, one feed" in twice.json()["message"]


async def test_check_now_adds_the_events_ahead_and_the_marathon_row_names_its_feed(
    client, sign_in, web, wf, cog
):
    feed_id = await gdq_feed(web, wf)
    sign_in(client)
    body = client.post(f"/api/marathons/feeds/{feed_id}/check").json()
    assert "4 added" in body["message"]
    assert [one["name"] for one in body["marathons"]][-1] == "Awesome Games Done Quick 2027"
    listed = client.get("/api/marathons").json()["marathons"]
    assert {one["feed_name"] for one in listed} == {"GDQ"}
    assert (await wf.one_web_row(web.db, "web.marathon.feed_checked"))["added"] == 4


async def test_a_check_that_fails_is_a_502_in_words(client, sign_in, web, wf, cog):
    feed_id = await gdq_feed(web, wf)
    cog.client.raises = ScheduleError("the GDQ tracker answered 503")
    sign_in(client)
    response = client.post(f"/api/marathons/feeds/{feed_id}/check")
    assert response.status_code == 502 and "answered 503" in response.json()["message"]
    assert client.get("/api/marathons/feeds").json()["feeds"][0]["trouble"]


async def test_patch_pauses_switches_to_suggest_and_refuses_a_bad_word(
    client, sign_in, web, wf, cog
):
    feed_id = await gdq_feed(web, wf)
    sign_in(client)
    body = client.patch(
        f"/api/marathons/feeds/{feed_id}", json={"active": False, "action": "suggest"}
    ).json()
    assert body["active"] is False and body["action"] == "suggest"
    assert "paused" in body["message"] and "suggests" in body["message"]
    bad = client.patch(f"/api/marathons/feeds/{feed_id}", json={"action": "maybe"})
    assert bad.status_code == 422 and bad.json()["error"] == "bad_action"
    bad = client.patch(f"/api/marathons/feeds/{feed_id}", json={"active": "no"})
    assert bad.status_code == 422 and bad.json()["error"] == "bad_active"


async def test_suggestions_are_added_or_dismissed_and_look_again_clears(
    client, sign_in, web, wf, cog
):
    feed_id = await gdq_feed(web, wf, action="suggest")
    sign_in(client)
    body = client.post(f"/api/marathons/feeds/{feed_id}/check").json()
    assert [one["ref"] for one in body["suggestions"]] == ["71", "72", "73", "74"]
    took = client.post(f"/api/marathons/feeds/{feed_id}/add", json={"event_ref": "74"})
    assert took.status_code == 200, took.text
    made = await get_marathon(web.db, wf.GUILD_ID, took.json()["marathon_id"])
    assert made["feed_id"] == feed_id and made["source_ref"] == "74"
    gone = client.post(f"/api/marathons/feeds/{feed_id}/add", json={"event_ref": "74"})
    assert gone.status_code == 409 and gone.json()["error"] == "suggestion_gone"
    body = client.patch(f"/api/marathons/feeds/{feed_id}", json={"dismiss": "73"}).json()
    assert [one["ref"] for one in body["dismissed"]] == ["73"]
    body = client.post(f"/api/marathons/feeds/{feed_id}/look").json()
    assert body["dismissed"] == [] and "73" in [one["ref"] for one in body["suggestions"]]


async def test_forget_ignored_and_remove_the_feed(client, sign_in, web, wf, cog):
    feed_id = await gdq_feed(web, wf)
    sign_in(client)
    client.post(f"/api/marathons/feeds/{feed_id}/check")
    marathon = client.get("/api/marathons").json()["marathons"][0]
    client.delete(f"/api/marathons/{marathon['id']}")
    body = client.get("/api/marathons/feeds").json()["feeds"][0]
    assert body["ignored_count"] == 1
    forgot = client.post(f"/api/marathons/feeds/{feed_id}/forget").json()
    assert forgot["ignored_count"] == 0 and "forgot 1" in forgot["message"]
    nothing = client.post(f"/api/marathons/feeds/{feed_id}/forget")
    assert nothing.status_code == 409 and nothing.json()["error"] == "nothing_ignored"
    gone = client.delete(f"/api/marathons/feeds/{feed_id}").json()
    assert gone["removed"] is True and "stay on the list" in gone["message"]
    assert await get_feed(web.db, wf.GUILD_ID, feed_id) is None
    missing = client.post(f"/api/marathons/feeds/{feed_id}/check")
    assert missing.status_code == 404 and missing.json()["message"]


async def test_patch_sets_the_feeds_event_mode_renames_and_moves_it(client, sign_in, web, wf, cog):
    feed_id = await gdq_feed(web, wf)
    other = await channel(web, wf, "speedstuff4charity", "Speed Stuff 4 Charity")
    sign_in(client)

    body = client.patch(
        f"/api/marathons/feeds/{feed_id}", json={"event_mode": "both", "name": "Games Done Quick"}
    ).json()
    assert body["event_mode"] == "both" and body["event_mode_effective"] == "both"
    assert body["name"] == "Games Done Quick"

    body = client.patch(f"/api/marathons/feeds/{feed_id}", json={"event_mode": None}).json()
    assert body["event_mode"] is None and body["event_mode_effective"] == "none"
    bad = client.patch(f"/api/marathons/feeds/{feed_id}", json={"event_mode": "often"})
    assert bad.status_code == 422 and bad.json()["error"] == "bad_mode"

    moved = client.patch(f"/api/marathons/feeds/{feed_id}", json={"spotlight_id": other}).json()
    assert moved["spotlight_id"] == other and "Speed Stuff 4 Charity" in moved["message"]
