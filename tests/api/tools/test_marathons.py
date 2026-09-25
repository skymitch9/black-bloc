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
    ("POST", "/api/marathons/1/runs/1/upcoming"),
    ("POST", "/api/marathons/1/runs/1/live"),
    ("POST", "/api/marathons/1/next"),
    ("POST", "/api/marathons/1/event"),
    ("DELETE", "/api/marathons/1/event"),
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
        return (ref if str(ref).isdigit() else "74", "Awesome Games Done Quick 2027")

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
        "/api/marathons", json={"name": "ESA", "schedule_url": "https://oengus.io/marathon/LSS26/schedule"}
    )
    assert other.status_code == 422
    assert other.json()["error"] == "unknown_site"
    assert "horaro.net schedules" in other.json()["message"]
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


# --- the next GDQ event and the run moves (marathon-next-event) ---------------------------

NEXT_EVENT = {
    "id": 75,
    "short": "SGDQ2027",
    "name": "Summer Games Done Quick 2027",
    "datetime": (NOW + timedelta(days=200)).isoformat(),
    "archived": False,
    "draft": True,
}
PAST = [
    a_run(1, -900, "Celeste", [("Somebody", "somebody", "runner")]),
    a_run(2, -800, "Super Metroid", [("Sky", "skyruns", "runner")]),
]


def an_over_marathon(client, cog):
    cog.client.runs_given = list(PAST)
    cog.client.events = lambda: _events()
    return add(client).json()["id"]


async def _events():
    return [NEXT_EVENT]


async def test_look_again_suggests_the_next_event_and_the_row_carries_it(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = an_over_marathon(client, cog)
    before = client.get(f"/api/marathons/{marathon_id}").json()
    assert before["phase"] == "over" and before["next"]["state"] is None
    assert before["next"]["can_look_again"] is True

    looked = client.post(f"/api/marathons/{marathon_id}/next")
    assert looked.status_code == 200, looked.text
    body = looked.json()
    assert body["next"]["state"] == "open" and body["next"]["name"] == NEXT_EVENT["name"]
    assert body["next_waiting"] is True and "is over" in body["message"]
    listed = client.get("/api/marathons").json()
    assert listed["next_waiting"] == 1
    assert "web.marathon.next_suggested" in await wf.kinds_in(web.db)


async def test_not_this_one_folds_the_card_and_add_it_links_the_new_row(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = an_over_marathon(client, cog)
    client.post(f"/api/marathons/{marathon_id}/next")
    dismissed = client.patch(f"/api/marathons/{marathon_id}", json={"dismiss_next": True})
    assert dismissed.status_code == 200 and dismissed.json()["next"]["state"] == "dismissed"
    again = client.patch(f"/api/marathons/{marathon_id}", json={"dismiss_next": True})
    assert again.status_code == 409 and "no next event waiting" in again.json()["message"]
    bad = client.patch(f"/api/marathons/{marathon_id}", json={"dismiss_next": "yes"})
    assert bad.status_code == 422 and bad.json()["error"] == "bad_dismiss"

    client.post(f"/api/marathons/{marathon_id}/next")
    cog.client.runs_given = list(SCHEDULE)
    made = client.post("/api/marathons", json={"next_of": marathon_id, "event_id": "75"})
    assert made.status_code == 200, made.text
    body = made.json()
    assert body["name"] == NEXT_EVENT["name"] and body["source_ref"] == "75"
    parent = client.get(f"/api/marathons/{marathon_id}").json()
    assert parent["next"]["state"] == "added"
    assert parent["next"]["added_marathon_id"] == body["id"]
    assert parent["next"]["added_name"] == NEXT_EVENT["name"]
    kinds = await wf.kinds_in(web.db)
    assert "web.marathon.next_dismissed" in kinds and "web.marathon.next_added" in kinds


async def test_the_next_routes_refuse_in_words_not_gdq_not_over_nothing_suggested(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    near = add(client).json()["id"]
    early = client.post(f"/api/marathons/{near}/next")
    assert early.status_code == 409 and "not over yet" in early.json()["message"]
    nothing = client.post("/api/marathons", json={"next_of": near})
    assert nothing.status_code == 409 and nothing.json()["error"] == "nothing_suggested"
    await web.db.conn.execute("UPDATE marathons SET source = 'horaro' WHERE id = ?", (near,))
    await web.db.conn.commit()
    other = client.post(f"/api/marathons/{near}/next")
    assert other.status_code == 409 and "not a GDQ marathon" in other.json()["message"]
    assert client.get(f"/api/marathons/{near}").json()["next"] is None
    missing = client.post("/api/marathons/9999/next")
    assert missing.status_code == 404


async def test_a_done_run_can_be_marked_upcoming_and_then_live(client, sign_in, web, cog, wf):
    sign_in(client)
    body = add(client).json()
    marathon_id = body["id"]
    ours = next(one for one in body["run_list"] if one["ours"])
    client.post(f"/api/marathons/{marathon_id}/runs/{ours['id']}/done")

    back = client.post(f"/api/marathons/{marathon_id}/runs/{ours['id']}/upcoming")
    assert back.status_code == 200, back.text
    run = back.json()["run"]
    assert run["state"] == "upcoming" and run["held"] is True and run["can_mark_live"] is True
    twice = client.post(f"/api/marathons/{marathon_id}/runs/{ours['id']}/upcoming")
    assert twice.status_code == 409 and twice.json()["error"] == "not_resettable"
    live = client.post(f"/api/marathons/{marathon_id}/runs/{ours['id']}/live").json()
    assert live["run"]["state"] == "live" and live["run"]["shouted"] is True
    assert "marked by staff" in live["message"]
    kinds = await wf.kinds_in(web.db)
    assert "web.marathon.run_reset" in kinds and "web.marathon.run_live" in kinds


async def test_a_marathons_own_read_gap_is_set_and_cleared_from_the_page(
    client, sign_in, cog
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    body = client.patch(f"/api/marathons/{marathon_id}", json={"poll_minutes": 45}).json()
    assert body["poll_minutes"] == 45
    body = client.patch(f"/api/marathons/{marathon_id}", json={"poll_minutes": None}).json()
    assert body["poll_minutes"] is None
    words = client.patch(f"/api/marathons/{marathon_id}", json={"poll_minutes": "soon"})
    assert words.status_code == 422 and "10 to 120 minutes" in words.json()["message"]


# --- a marathon is an event (docs/info/marathon-events-page-design.md §B) --------------------


@pytest.fixture
async def review(web, wf):
    await web.store.set(wf.GUILD_ID, "events_category_id", wf.CATEGORY_ID, by=7)


async def web_row(wf, web, kind):
    found = [details for seen, details in await wf.web_rows_in(web.db) if seen == kind]
    assert len(found) == 1, await wf.web_rows_in(web.db)
    assert found[0]["via"] == "website"
    return found[0]


async def test_adding_with_make_event_puts_its_event_on_the_row_and_in_the_queue(
    client, sign_in, web, cog, wf, review
):
    sign_in(client)
    body = add(client, make_event=True).json()

    event = body["event"]
    assert event["id"] and event["status"] == "pending" and event["wanted"] is True
    assert event["waiting"] is False and f"#{event['id']}" in event["line"]
    queued = client.get("/api/events?status=pending").json()
    mine = next(one for one in queued if one["id"] == event["id"])
    assert mine["title"] == "AGDQ 2027" and mine["starts_at"] == at(60)
    assert mine["marathon"]["id"] == body["id"] and "AGDQ 2027" in mine["marathon"]["line"]
    assert (await web_row(wf, web, "web.marathon.event_made"))["event_id"] == event["id"]


async def test_adding_with_make_event_off_leaves_the_event_line_empty(client, sign_in, cog):
    sign_in(client)
    body = add(client, make_event=False).json()
    assert body["event"] == {
        "id": None,
        "status": None,
        "wanted": False,
        "waiting": False,
        "line": body["event"]["line"],
    }
    assert "Make an event now" in body["event"]["line"]


async def test_make_event_that_is_not_true_or_false_is_refused_in_words(client, sign_in, cog):
    sign_in(client)
    refused = add(client, make_event="yes")
    assert refused.status_code == 422 and refused.json()["error"] == "bad_make_event"
    assert client.get("/api/marathons").json()["marathons"] == []


async def test_the_list_carries_the_add_forms_default_and_each_rows_event(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    add(client, make_event=False)
    payload = client.get("/api/marathons").json()
    assert payload["makes_event"] is True
    assert payload["marathons"][0]["event"]["id"] is None
    await web.store.set(wf.GUILD_ID, "marathon_makes_event", False)
    assert client.get("/api/marathons").json()["makes_event"] is False


async def test_make_now_then_unlink_from_the_site_and_a_second_unlink_says_why(
    client, sign_in, web, cog, wf, review
):
    sign_in(client)
    marathon_id = add(client, make_event=False).json()["id"]

    made = client.post(f"/api/marathons/{marathon_id}/event")
    assert made.status_code == 200, made.text
    event_id = made.json()["event"]["id"]
    assert event_id and f"#{event_id}" in made.json()["message"]
    again = client.post(f"/api/marathons/{marathon_id}/event")
    assert again.status_code == 409 and again.json()["error"] == "event_exists"

    unlinked = client.delete(f"/api/marathons/{marathon_id}/event")
    assert unlinked.status_code == 200 and unlinked.json()["event"]["id"] is None
    assert client.get(f"/api/events/{event_id}").json()["event"]["status"] == "pending"
    assert client.get(f"/api/events/{event_id}").json()["event"]["marathon"] is None
    twice = client.delete(f"/api/marathons/{marathon_id}/event")
    assert twice.status_code == 409 and "carries no event" in twice.json()["message"]
    assert (await web_row(wf, web, "web.marathon.event_unlinked"))["event_id"] == event_id


async def test_removing_from_the_site_calls_the_event_off(client, sign_in, web, cog, wf, review):
    sign_in(client)
    body = add(client, make_event=True).json()
    assert client.delete(f"/api/marathons/{body['id']}").status_code == 200
    event = client.get(f"/api/events/{body['event']['id']}").json()["event"]
    assert event["status"] == "cancelled"
    assert (await web_row(wf, web, "web.marathon.event_cancelled"))["marathon_id"] == body[
        "id"
    ]
