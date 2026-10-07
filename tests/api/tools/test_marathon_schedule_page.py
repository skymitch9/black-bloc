from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from black_bloc.cogs.content.marathon import Marathons
from black_bloc.marathon_sources import Person, Run

URL = "https://gamesdonequick.com/schedule/74"
SKY = 21
NOW = datetime.now(UTC).replace(microsecond=0)
ROUTE = "/api/marathons/1/schedule"


def at(minutes):
    return (NOW + timedelta(minutes=minutes)).isoformat()


def a_run(ident, start, game, people):
    return Run(
        str(ident),
        ident,
        game,
        game,
        "Any%",
        at(start),
        at(start + 60),
        3600,
        tuple(Person(*one) for one in people),
    )


SCHEDULE = [
    a_run(1, 60, "Celeste", [("Somebody", "somebody", "runner")]),
    a_run(2, 180, "Super Metroid", [("Sky", "skyruns", "runner")]),
    a_run(3, 300, "Blaster Master", [("Interview Crew", None, "host")]),
]


class FakeClient:
    async def resolve(self, source, ref):
        return (ref if str(ref).isdigit() else "74", "Awesome Games Done Quick 2027")

    async def runs(self, source, ref):
        return list(SCHEDULE)

    async def close(self):
        return None


@pytest.fixture
async def cog(web, wf):
    await web.store.set(wf.GUILD_ID, "marathon_mode", "on")
    await web.store.set(wf.GUILD_ID, "marathon_channel_id", wf.TEST_CHANNEL_ID)
    await web.store.set(wf.GUILD_ID, "marathon_track_makes_thread", False)
    await web.db.conn.execute(
        "INSERT OR REPLACE INTO golive_links(user_id, twitch_login, linked_at) VALUES (?, ?, ?)",
        (SKY, "skyruns", at(-9999)),
    )
    await web.db.conn.commit()
    made = Marathons(web)
    made.client = FakeClient()
    web.cogs["Marathons"] = made
    return made


def add(client):
    made = client.post("/api/marathons", json={"name": "AGDQ 2027", "schedule_url": URL})
    assert made.status_code == 200, made.text
    return made.json()["id"]


def test_the_tracker_read_needs_a_session(client):
    refused = client.get(ROUTE)
    assert refused.status_code == 401
    assert refused.json()["message"] and not refused.json()["message"].isdigit()


def test_the_tracker_read_refuses_a_non_staff_visitor_in_words(client, sign_in):
    sign_in(client, uid=1234, staff=False)
    refused = client.get(ROUTE)
    assert refused.status_code == 403
    assert len(refused.json()["message"].split()) > 5


def test_an_unknown_marathon_is_refused_in_words(client, sign_in, cog):
    sign_in(client)
    refused = client.get("/api/marathons/9999/schedule")
    assert refused.status_code == 404 and refused.json()["error"] == "not_found"
    assert "follows no marathon" in refused.json()["message"]


async def test_the_tracker_read_answers_the_pages_shape_from_the_real_rows(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client)
    found = client.get(f"/api/marathons/{marathon_id}/schedule")
    assert found.status_code == 200, found.text
    body = found.json()
    assert (body["kind"], body["editable"], body["times_from"]) == ("tracker", False, "tracker")
    assert (body["moves_by"], body["refresh_seconds"]) == ("marks", 30)
    assert body["marathon"]["name"] == "AGDQ 2027" and body["marathon"]["archived"] is False
    assert body["marathon"]["next_read_at"]
    assert [one["game"] for one in body["rows"]] == ["Celeste", "Super Metroid", "Blaster Master"]
    assert [one["from"] for one in body["rows"]] == ["tracker"] * 3
    sky = body["rows"][1]
    assert sky["ours"] is True and sky["people"][0]["baf"] is True
    assert sky["people"][0]["twitch_url"] == "https://www.twitch.tv/skyruns"
    assert sky["people"][0]["twitch_from"] == "member"
    assert body["rows"][0]["people"][0]["twitch_from"] == "schedule"
    assert body["rows"][0]["can"] == {
        "start": True,
        "finish": True,
        "set_start": False,
        "estimate": False,
        "skip": False,
        "restore": False,
    }
    assert body["next_posts"] == []
    assert body["undo"] == {"available": False, "text": None}


async def test_a_tracked_marathon_lists_the_marks_still_to_fire_for_its_baf_run(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client)
    assert client.post(f"/api/marathons/{marathon_id}/track", json={}).status_code == 200
    await web.store.set(wf.GUILD_ID, "marathon_reminder_minutes", "120, 15")
    body = client.get(f"/api/marathons/{marathon_id}/schedule").json()
    posts = [one for one in body["next_posts"] if one["kind"] == "run"]
    assert {one["run_id"] for one in posts} == {body["rows"][1]["id"]}
    assert 120 in [one["minutes"] for one in posts]
    assert all(one["text"].startswith("Heads-up: **Sky** runs **Super Metroid**") for one in posts)


async def test_started_now_through_the_existing_route_shows_on_the_next_read(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client)
    first = client.get(f"/api/marathons/{marathon_id}/schedule").json()["rows"][0]
    live = client.post(f"/api/marathons/{marathon_id}/runs/{first['id']}/live")
    assert live.status_code == 200, live.text
    body = client.get(f"/api/marathons/{marathon_id}/schedule").json()
    row = body["rows"][0]
    assert (row["state"], row["from"]) == ("live", "started")
    assert (row["can"]["start"], row["can"]["finish"]) == (False, True)
    assert row["actual_started_at"] and row["off_plan_minutes"] < 0
    assert body["moves"][0]["kind"] == "run_live"
    assert body["moves"][0]["text"] == "**Celeste** is on now, by staff"
    assert body["moves"][0]["by_name"]
    done = client.post(f"/api/marathons/{marathon_id}/runs/{first['id']}/done")
    assert done.status_code == 200, done.text
    after = client.get(f"/api/marathons/{marathon_id}/schedule").json()
    assert after["rows"][0]["state"] == "done"
    assert [one["kind"] for one in after["moves"][:2]] == ["run_done", "run_live"]


async def test_an_archived_marathon_reads_with_no_moves_to_press(client, sign_in, web, cog, wf):
    sign_in(client)
    marathon_id = add(client)
    assert client.post(f"/api/marathons/{marathon_id}/archive").status_code == 200
    body = client.get(f"/api/marathons/{marathon_id}/schedule").json()
    assert body["marathon"]["archived"] is True and body["marathon"]["phase"] == "archived"
    assert len(body["rows"]) == 3
    assert not any(one["can"]["start"] or one["can"]["finish"] for one in body["rows"])
    assert body["next_posts"] == []


async def test_the_refresh_key_rides_the_read(client, sign_in, web, cog, wf):
    sign_in(client)
    marathon_id = add(client)
    await web.store.set(wf.GUILD_ID, "marathon_tracker_refresh_seconds", 45)
    assert client.get(f"/api/marathons/{marathon_id}/schedule").json()["refresh_seconds"] == 45


async def test_the_tracker_marks_each_baf_run_and_a_baf_event_day(client, sign_in, web, cog, wf):
    sign_in(client)
    marathon_id = add(client)

    body = client.get(f"/api/marathons/{marathon_id}/schedule").json()

    assert [one["baf_run"] for one in body["rows"]] == [False, True, False]
    assert [one["baf_event"] for one in body["days"]] == [{"answer": "no", "reason": "mixed"}]

    client.patch(f"/api/marathons/{marathon_id}", json={"baf_event": "yes"})
    body = client.get(f"/api/marathons/{marathon_id}/schedule").json()
    assert [one["baf_event"] for one in body["days"]] == [{"answer": "yes", "reason": "staff"}]


async def test_on_a_baf_event_day_only_the_two_hour_heads_up_is_listed_with_the_role(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client)
    assert client.post(f"/api/marathons/{marathon_id}/track", json={}).status_code == 200
    await web.store.set(wf.GUILD_ID, "marathon_reminder_minutes", "120, 15")
    role = web.guild.roles[0]
    role.mentionable = True
    await web.store.set(wf.GUILD_ID, "marathon_role_id", role.id)
    client.patch(f"/api/marathons/{marathon_id}", json={"ping_role": True})

    before = client.get(f"/api/marathons/{marathon_id}/schedule").json()["next_posts"]
    client.patch(f"/api/marathons/{marathon_id}", json={"baf_event": "yes"})
    after = client.get(f"/api/marathons/{marathon_id}/schedule").json()["next_posts"]

    assert {one["minutes"]: one["role"] for one in before if one["kind"] == "run"} == {
        120: False,
        15: True,
    }
    assert {one["minutes"]: one["role"] for one in after if one["kind"] == "run"} == {
        120: True,
        15: False,
    }
