from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from black_bloc.cogs.content.marathon import Marathons, get_marathon, runs_of
from black_bloc.cogs.content.spotlight import add_channel
from black_bloc.marathon_sources import Person, Run, ScheduleError

URL = "https://gamesdonequick.com/schedule/74"
SKY = 21
NOW = datetime.now(UTC).replace(microsecond=0)

ROUTES = [
    ("GET", "/api/marathons"),
    ("POST", "/api/marathons"),
    ("GET", "/api/marathons/1"),
    ("PATCH", "/api/marathons/1"),
    ("DELETE", "/api/marathons/1"),
    ("POST", "/api/marathons/1/refresh"),
    ("POST", "/api/marathons/1/board"),
    ("GET", "/api/marathons/1/people"),
    ("POST", "/api/marathons/1/people"),
    ("DELETE", "/api/marathons/1/people/1"),
    ("POST", "/api/marathons/1/runs/1/shout"),
    ("POST", "/api/marathons/1/runs/1/done"),
]


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
    def __init__(self):
        self.runs_given = list(SCHEDULE)
        self.raises = None

    async def resolve(self, source, ref):
        if self.raises is not None:
            raise self.raises
        return ("74", "Awesome Games Done Quick 2027")

    async def runs(self, source, ref):
        if self.raises is not None:
            raise self.raises
        return list(self.runs_given)

    async def close(self):
        return None


@pytest.fixture
async def cog(web, wf):
    await web.store.set(wf.GUILD_ID, "marathon_mode", "on")
    await web.store.set(wf.GUILD_ID, "marathon_channel_id", wf.TEST_CHANNEL_ID)
    await web.db.conn.execute(
        "INSERT OR REPLACE INTO golive_links(user_id, twitch_login, linked_at) VALUES (?, ?, ?)",
        (SKY, "skyruns", at(-9999)),
    )
    await web.db.conn.commit()
    made = Marathons(web)
    made.client = FakeClient()
    web.cogs["Marathons"] = made
    return made


def add(client, **extra):
    return client.post("/api/marathons", json={"name": "AGDQ 2027", "schedule_url": URL, **extra})


@pytest.mark.parametrize(("method", "route"), ROUTES)
def test_every_marathon_route_needs_a_session(client, method, route):
    assert client.request(method, route).status_code == 401


@pytest.mark.parametrize(("method", "route"), ROUTES)
def test_every_marathon_route_refuses_a_non_staff_visitor(client, sign_in, method, route):
    sign_in(client, uid=1234, staff=False)
    assert client.request(method, route).status_code == 403


async def test_adding_a_marathon_reads_it_and_answers_with_its_runs(client, sign_in, web, cog, wf):
    sign_in(client)
    response = add(client)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "AGDQ 2027" and body["source"] == "gdq" and body["source_ref"] == "74"
    assert body["runs"] == 3 and body["ours"] == 1
    assert [one["game"] for one in body["run_list"]] == [
        "Celeste",
        "Super Metroid",
        "Blaster Master",
    ]
    assert body["run_list"][1]["ours"] is True and body["run_list"][1]["shoutable"] is True
    assert body["unmatched"] == ["Interview Crew", "Somebody"]
    assert "3 run(s), 1 of them ours" in body["message"]
    assert (await wf.one_web_row(web.db, "web.marathon.added"))["name"] == "AGDQ 2027"


async def test_an_unknown_site_a_duplicate_and_an_unreadable_link_are_refused_in_words(
    client, sign_in, cog
):
    sign_in(client)
    other = client.post(
        "/api/marathons", json={"name": "ESA", "schedule_url": "https://horaro.net/esa/2027"}
    )
    assert other.status_code == 422
    assert other.json()["error"] == "unknown_site"
    assert "GDQ schedule only" in other.json()["message"]
    assert add(client).status_code == 200
    again = add(client, name="Again")
    assert again.status_code == 409 and "already follows" in again.json()["message"]
    cog.client.raises = ScheduleError("the GDQ tracker has no event 99")
    missing = client.post(
        "/api/marathons",
        json={"name": "Nope", "schedule_url": "https://gamesdonequick.com/schedule/99"},
    )
    assert missing.status_code == 422 and "no event 99" in missing.json()["message"]
    nameless = client.post("/api/marathons", json={"name": " ", "schedule_url": URL})
    assert nameless.status_code == 422 and nameless.json()["error"] == "no_name"


async def test_the_list_says_the_mode_and_each_marathons_state(client, sign_in, cog):
    sign_in(client)
    add(client)
    body = client.get("/api/marathons").json()

    assert body["mode"] == "on"
    row = body["marathons"][0]
    assert row["phase"] == "near" and row["phase_word"] == "coming up"
    assert row["last_fetch_ok"] is True and row["trouble"] is None


async def test_a_schedule_that_will_not_read_says_so_in_words(client, sign_in, web, cog, wf):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    cog.client.raises = ScheduleError("the GDQ tracker answered 503")
    refused = client.post(f"/api/marathons/{marathon_id}/refresh")
    assert refused.status_code == 502 and "503" in refused.json()["message"]
    row = client.get("/api/marathons").json()["marathons"][0]
    assert "503" in row["trouble"] and row["fetch_failures"] == 1
    assert len(await runs_of(web.db, marathon_id)) == 3


async def test_patch_pauses_resumes_renames_and_sets_the_channel(client, sign_in, web, cog, wf):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    spotlight_id = await add_channel(
        web.db, wf.GUILD_ID, "gamesdonequick", added_by=7, expires_at=None, pin=True
    )

    body = client.patch(
        f"/api/marathons/{marathon_id}",
        json={"active": False, "name": "AGDQ", "spotlight_id": str(spotlight_id)},
    ).json()
    assert body["active"] is False and body["name"] == "AGDQ"
    assert body["channel_login"] == "gamesdonequick" and body["window"] is None
    body = client.patch(f"/api/marathons/{marathon_id}", json={"active": True}).json()
    assert body["active"] is True and body["window"]["starts_at"]
    bad = client.patch(f"/api/marathons/{marathon_id}", json={"poll_minutes": 5})
    assert bad.status_code == 422
    kinds = await wf.kinds_in(web.db)
    assert "web.marathon.paused" in kinds and "web.marathon.resumed" in kinds
    assert "web.marathon.channel_set" in kinds and "web.marathon.updated" in kinds


async def test_pairing_a_name_makes_the_run_ours_and_unpairing_undoes_it(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    paired = client.post(
        f"/api/marathons/{marathon_id}/people",
        json={"runner_name": "Interview Crew", "user_id": "77"},
    ).json()
    assert paired["pairings"][0]["runner_name"] == "interview crew"
    body = client.get(f"/api/marathons/{marathon_id}").json()
    assert body["ours"] == 2 and body["unmatched"] == ["Somebody"]
    pairing_id = paired["pairings"][0]["id"]
    gone = client.delete(f"/api/marathons/{marathon_id}/people/{pairing_id}").json()
    assert gone["pairings"] == []
    assert client.get(f"/api/marathons/{marathon_id}").json()["ours"] == 1
    missing = client.delete(f"/api/marathons/{marathon_id}/people/{pairing_id}")
    assert missing.status_code == 404
    nobody = client.post(f"/api/marathons/{marathon_id}/people", json={"runner_name": "X"})
    assert nobody.status_code == 422 and nobody.json()["error"] == "no_member"


async def test_staff_post_the_board_shout_a_run_and_mark_it_done(client, sign_in, web, cog, wf):
    sign_in(client)
    body = add(client).json()
    marathon_id = body["id"]
    ours = next(one for one in body["run_list"] if one["ours"])
    theirs = next(one for one in body["run_list"] if not one["ours"])

    board = client.post(f"/api/marathons/{marathon_id}/board")
    assert board.status_code == 200 and board.json()["board_message_id"]
    shout = client.post(f"/api/marathons/{marathon_id}/runs/{ours['id']}/shout").json()
    assert shout["run"]["shouted"] is True and shout["run"]["state"] == "live"
    twice = client.post(f"/api/marathons/{marathon_id}/runs/{ours['id']}/shout")
    assert twice.status_code == 409 and twice.json()["error"] == "not_shoutable"
    not_ours = client.post(f"/api/marathons/{marathon_id}/runs/{theirs['id']}/shout")
    assert not_ours.status_code == 409 and not_ours.json()["error"] == "not_ours"
    done = client.post(f"/api/marathons/{marathon_id}/runs/{ours['id']}/done").json()
    assert done["run"]["state"] == "done"
    again = client.post(f"/api/marathons/{marathon_id}/runs/{ours['id']}/done")
    assert again.status_code == 409
    missing = client.post(f"/api/marathons/{marathon_id}/runs/9999/done")
    assert missing.status_code == 404
    kinds = await wf.kinds_in(web.db)
    assert "web.marathon.board_posted" in kinds and "web.marathon.shouted" in kinds
    assert "web.marathon.run_done" in kinds


async def test_removing_a_marathon_takes_its_runs_and_says_so(client, sign_in, web, cog, wf):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    gone = client.delete(f"/api/marathons/{marathon_id}").json()
    assert gone["removed"] is True and "off the list" in gone["message"]
    assert await get_marathon(web.db, wf.GUILD_ID, marathon_id) is None
    assert await runs_of(web.db, marathon_id) == []
    assert client.get(f"/api/marathons/{marathon_id}").status_code == 404
    assert "web.marathon.removed" in await wf.kinds_in(web.db)


async def test_a_write_with_no_cog_loaded_is_refused_in_words_not_a_bare_status(
    client, sign_in, web
):
    sign_in(client)
    response = add(client)
    assert response.status_code == 503
    assert "Marathon schedules" in response.json()["message"]
