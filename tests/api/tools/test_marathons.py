from __future__ import annotations

from datetime import UTC, datetime, timedelta

import discord
import pytest

from black_bloc.cogs.content.marathon import Marathons, get_marathon, runs_of
from black_bloc.cogs.content.spotlight import add_channel, channel_by_id
from black_bloc.marathon import BAD_POLL, NO_RENAME
from black_bloc.marathon_people import BY_LINK, MATCHED_WORDS
from black_bloc.marathon_sources import Person, Run, ScheduleError
from black_bloc.settings_store import MARATHON_EVENT_MODES

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
    ("PATCH", "/api/marathons/1/people/1"),
    ("POST", "/api/marathons/1/people/somebody/spotlight"),
    ("DELETE", "/api/marathons/1/people/somebody/spotlight"),
    ("POST", "/api/marathons/1/people/77/opt-out"),
    ("DELETE", "/api/marathons/1/people/77/opt-out"),
    ("POST", "/api/marathons/1/runs/1/shout"),
    ("POST", "/api/marathons/1/runs/1/done"),
    ("POST", "/api/marathons/1/runs/1/upcoming"),
    ("POST", "/api/marathons/1/runs/1/live"),
    ("POST", "/api/marathons/1/next"),
    ("POST", "/api/marathons/1/event"),
    ("DELETE", "/api/marathons/1/event"),
    ("POST", "/api/marathons/1/runs/1/event"),
    ("DELETE", "/api/marathons/1/runs/1/event"),
    ("GET", "/api/marathons/archive"),
    ("POST", "/api/marathons/1/archive"),
    ("POST", "/api/marathons/1/restore"),
    ("POST", "/api/marathons/1/track"),
    ("POST", "/api/marathons/1/ignore"),
    ("POST", "/api/marathons/1/inbox"),
    ("POST", "/api/marathons/1/sheet-times"),
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


def add(client, **extra):
    return client.post("/api/marathons", json={"name": "AGDQ 2027", "schedule_url": URL, **extra})


def track(client, marathon_id):
    tracked = client.post(f"/api/marathons/{marathon_id}/track", json={})
    assert tracked.status_code == 200, tracked.text
    return tracked.json()


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
    assert "3 run(s), 1 of them BaF" in body["message"]
    assert (await wf.one_web_row(web.db, "web.marathon.added"))["name"] == "AGDQ 2027"


async def test_an_unknown_site_a_duplicate_and_an_unreadable_link_are_refused_in_words(
    client, sign_in, cog
):
    sign_in(client)
    other = client.post(
        "/api/marathons", json={"name": "ESA", "schedule_url": "https://example.org/marathon/LSS26/schedule"}
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
    await web.store.set(wf.GUILD_ID, "marathon_ping_role_default", True)
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
    await web.store.set(wf.GUILD_ID, "marathon_hosts_count_as_ours", True)
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
    untracked = client.post(f"/api/marathons/{marathon_id}/board")
    assert untracked.status_code == 409 and untracked.json()["error"] == "not_tracked"
    assert "is not tracked" in untracked.json()["message"]
    track(client, marathon_id)

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


async def test_delete_is_retired_answers_in_words_and_archives_nothing(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]

    said = client.delete(f"/api/marathons/{marathon_id}")

    assert said.status_code == 410
    body = said.json()
    assert body["error"] == "remove_gone"
    assert "Remove is retired" in body["message"] and "Archive it" in body["message"]
    assert "Nothing was changed" in body["message"]
    assert client.get(f"/api/marathons/{marathon_id}").json()["id"] == marathon_id


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
    track(client, marathon_id)
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


async def test_staff_put_a_marathon_back_on_its_sheets_times_from_the_page(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    body = add(client).json()
    marathon_id = body["id"]
    assert body["retimed_runs"] == 0 and body["keeps_clock"] is False
    first = body["run_list"][0]
    assert first["retimed"] is False and first["certain"] is False
    assert first["sheet_at"] == first["scheduled_at"]
    track(client, marathon_id)
    client.post(f"/api/marathons/{marathon_id}/runs/{first['id']}/live")

    back = client.post(f"/api/marathons/{marathon_id}/sheet-times")
    assert back.status_code == 200, back.text
    said = back.json()
    assert "back on the sheet's times" in said["message"]
    assert all(one["actual_started_at"] is None for one in said["run_list"])
    assert said["retimed_runs"] == 0
    twice = client.post(f"/api/marathons/{marathon_id}/sheet-times")
    assert twice.status_code == 409 and twice.json()["error"] == "not_retimed"
    assert "web.marathon.sheet_times" in await wf.kinds_in(web.db)


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
    assert words.status_code == 422 and words.json()["message"] == BAD_POLL


async def test_a_marathon_is_renamed_from_the_page_and_an_empty_name_is_refused_in_words(
    client, sign_in, cog
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    before = client.get(f"/api/marathons/{marathon_id}").json()["name"]
    done = client.patch(
        f"/api/marathons/{marathon_id}", json={"name": " Black in a Flash:  Soul Train "}
    )
    assert done.status_code == 200
    body = done.json()
    assert body["name"] == "Black in a Flash: Soul Train"
    assert f"**{before}** is now called **Black in a Flash: Soul Train**" in body["message"]
    again = client.patch(
        f"/api/marathons/{marathon_id}", json={"name": "Black in a Flash: Soul Train"}
    )
    assert again.status_code == 200 and again.json()["message"] == ""
    empty = client.patch(f"/api/marathons/{marathon_id}", json={"name": "   "})
    assert empty.status_code == 422 and empty.json()["error"] == "no_name"
    assert empty.json()["message"] == NO_RENAME
    kept = client.get(f"/api/marathons/{marathon_id}").json()["name"]
    assert kept == "Black in a Flash: Soul Train"
    assert client.patch("/api/marathons/99999", json={"name": "x"}).status_code == 404


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
    assert payload["event_mode_default"] == "none"
    assert [one["value"] for one in payload["event_modes"]] == list(MARATHON_EVENT_MODES)
    assert payload["marathons"][0]["event"]["id"] is None
    assert payload["marathons"][0]["event_mode"] == "none"
    await web.store.set(wf.GUILD_ID, "marathon_event_mode_default", "runs")
    assert client.get("/api/marathons").json()["event_mode_default"] == "runs"


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


# --- event modes (docs/info/marathon-event-modes-design.md §B) --------------------------------


@pytest.fixture
async def quiet(web, wf):
    await web.store.set(wf.GUILD_ID, "events_create_scheduled", False)


async def test_adding_with_an_event_mode_makes_the_run_events_and_one_web_row(
    client, sign_in, web, cog, wf, quiet
):
    sign_in(client)
    body = add(client, event_mode="runs").json()

    assert body["event_mode"] == "runs" and body["event"]["id"] is None
    metroid = next(one for one in body["run_list"] if one["game"] == "Super Metroid")
    assert metroid["event_id"] and metroid["event_status"] == "approved"
    assert metroid["event_unlinked"] is False
    assert [kind for kind, _ in await wf.web_rows_in(web.db)] == ["web.marathon.added"]
    queued = client.get("/api/events?status=approved").json()
    mine = next(one for one in queued if one["id"] == metroid["event_id"])
    assert mine["marathon"]["run"]["game"] == "Super Metroid"


async def test_a_mode_that_is_not_a_mode_is_refused_and_make_event_still_maps(
    client, sign_in, cog, quiet
):
    sign_in(client)
    refused = add(client, event_mode="often")
    assert refused.status_code == 422 and refused.json()["error"] == "bad_mode"
    assert add(client, make_event=False).json()["event_mode"] == "none"


async def test_patch_event_mode_applies_at_once_and_leaves_one_web_row(
    client, sign_in, web, cog, wf, quiet
):
    sign_in(client)
    marathon_id = add(client).json()["id"]

    body = client.patch(f"/api/marathons/{marathon_id}", json={"event_mode": "runs"}).json()

    assert body["event_mode"] == "runs" and "1 run or host block event(s) made" in body["message"]
    kinds = [kind for kind, _ in await wf.web_rows_in(web.db)]
    assert kinds == ["web.marathon.added", "web.marathon.event_mode_set"]
    assert (await web_row(wf, web, "web.marathon.event_mode_set"))["to"] == "runs"
    wrong = client.patch(f"/api/marathons/{marathon_id}", json={"event_mode": 3})
    assert wrong.status_code == 422


async def test_a_run_event_is_unlinked_and_made_again_from_the_site(
    client, sign_in, web, cog, wf, quiet
):
    sign_in(client)
    body = add(client, event_mode="runs").json()
    metroid = next(one for one in body["run_list"] if one["game"] == "Super Metroid")
    base = f"/api/marathons/{body['id']}/runs/{metroid['id']}/event"

    gone = client.delete(base).json()
    assert gone["run"]["event_id"] is None and gone["run"]["event_unlinked"] is True
    again = client.delete(base)
    assert again.status_code == 409 and "carries no event" in again.json()["message"]
    made = client.post(base).json()
    assert made["run"]["event_id"] and made["run"]["event_status"] == "approved"
    twice = client.post(base)
    assert twice.status_code == 409 and twice.json()["error"] == "run_event_exists"
    celeste = next(one for one in body["run_list"] if one["game"] == "Celeste")
    refused = client.post(f"/api/marathons/{body['id']}/runs/{celeste['id']}/event")
    assert refused.status_code == 409 and refused.json()["error"] == "not_ours"


async def test_the_people_answer_is_baf_then_everyone_with_how_each_matched(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    body = client.get(f"/api/marathons/{marathon_id}/people").json()

    assert body["marathon_id"] == marathon_id and body["timezone"] == "America/Phoenix"
    assert body["pairings"] == []
    assert [one["name"] for one in body["baf"]] == ["Sky"]
    sky = body["baf"][0]
    assert sky["member"] is True and sky["user_id"] == str(SKY) and sky["login"] == "skyruns"
    assert sky["matched_by"] == BY_LINK and sky["matched_word"] == MATCHED_WORDS[BY_LINK]
    assert [one["game"] for one in sky["runs"]] == ["Super Metroid"]
    assert sky["spotlight_id"] is None and sky["channel_id"] is None
    assert [one["name"] for one in body["others"]] == ["Interview Crew", "Somebody"]
    assert body["others"][0]["parts"] == ["host"]
    assert sky["part_tag"] == "runs" and body["others"][0]["part_tag"] == "hosts"


async def test_spotlight_a_runner_makes_a_go_live_row_and_stop_removes_it(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    lit = client.post(f"/api/marathons/{marathon_id}/people/somebody/spotlight", json={})
    assert lit.status_code == 200, lit.text
    somebody = next(one for one in lit.json()["others"] if one["name"] == "Somebody")
    assert somebody["spotlight_id"] and somebody["spotlight_until"]
    assert "spotlit on the Go-live page" in lit.json()["message"]
    rows = client.get("/api/golive/spotlight").json()
    row = next(one for one in rows if one["twitch_login"] == "somebody")
    assert row["note"] == "Somebody at AGDQ 2027"
    kinds = await wf.kinds_in(web.db)
    assert "web.golive.spotlight_added" in kinds and "web.marathon.runner_spotlit" in kinds
    twice = client.post(f"/api/marathons/{marathon_id}/people/somebody/spotlight", json={})
    assert twice.status_code == 409 and twice.json()["error"] == "already_on_golive"
    assert "already on the Go-live page" in twice.json()["message"]

    stopped = client.delete(f"/api/marathons/{marathon_id}/people/somebody/spotlight")
    assert stopped.status_code == 200 and "no longer spotlit" in stopped.json()["message"]
    left = client.get("/api/golive/spotlight").json()
    assert not any(one["twitch_login"] == "somebody" for one in left)
    assert "web.marathon.runner_unspotlit" in await wf.kinds_in(web.db)
    again = client.delete(f"/api/marathons/{marathon_id}/people/somebody/spotlight")
    assert again.status_code == 404 and again.json()["error"] == "not_spotlit"


async def test_spotlight_refuses_in_words_a_name_with_no_twitch_and_a_stranger(
    client, sign_in, cog
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    crew = client.post(f"/api/marathons/{marathon_id}/people/Interview%20Crew/spotlight")
    assert crew.status_code == 422 and crew.json()["error"] == "no_login"
    assert "no Twitch channel" in crew.json()["message"]
    ghost = client.post(f"/api/marathons/{marathon_id}/people/ghost/spotlight", json={})
    assert ghost.status_code == 404 and "Nobody called **ghost**" in ghost.json()["message"]
    bad_run = client.post(
        f"/api/marathons/{marathon_id}/people/skyruns/spotlight", json={"run_id": 9999}
    )
    assert bad_run.status_code == 404


async def test_patch_spotlight_mode_switches_it_and_refuses_a_word_it_does_not_know(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    assert client.get(f"/api/marathons/{marathon_id}").json()["spotlight_mode"] == "follow"

    body = client.patch(f"/api/marathons/{marathon_id}", json={"spotlight_mode": "off"}).json()

    assert body["spotlight_mode"] == "off"
    assert "no longer spotlights its channel" in body["message"]
    said = await web_row(wf, web, "web.marathon.spotlight_mode_set")
    assert (said["from"], said["to"]) == ("follow", "off")
    bad = client.patch(f"/api/marathons/{marathon_id}", json={"spotlight_mode": "often"})
    assert bad.status_code == 422 and bad.json()["error"] == "bad_spotlight_mode"


async def test_patch_ping_role_turns_it_on_and_off_and_refuses_a_word_it_does_not_know(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    spotlight_id = await add_channel(
        web.db, wf.GUILD_ID, "gamesdonequick", added_by=7, expires_at=None, pin=True
    )
    marathon_id = add(client, spotlight_id=str(spotlight_id)).json()["id"]
    first = client.get(f"/api/marathons/{marathon_id}").json()
    assert first["ping_role"] is False and first["window"] is None

    body = client.patch(f"/api/marathons/{marathon_id}", json={"ping_role": True}).json()

    assert body["ping_role"] is True and body["window"]["starts_at"]
    assert "pings again" in body["message"]
    said = await web_row(wf, web, "web.marathon.ping_role_set")
    assert (said["from"], said["to"], said["via"]) == (False, True, "website")
    body = client.patch(f"/api/marathons/{marathon_id}", json={"ping_role": False}).json()
    assert body["ping_role"] is False and body["window"] is None
    bad = client.patch(f"/api/marathons/{marathon_id}", json={"ping_role": "loud"})
    assert bad.status_code == 422 and bad.json()["error"] == "bad_ping_role"


async def test_patch_the_announcements_switch_and_the_retired_host_switches_answer_in_words(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    first = client.get(f"/api/marathons/{marathon_id}").json()
    assert "scan_hosts" not in first and "host_events" not in first
    assert first["announcements"] == {"own": None, "on": True, "default": True}

    body = client.patch(
        f"/api/marathons/{marathon_id}", json={"scan_hosts": True, "host_events": "on"}
    ).json()

    assert "hosts are always found now" in body["message"]
    assert "BaF run/host events in the marathon's drawer" in body["message"]
    assert body["event_mode"] == first["event_mode"]
    bad = client.patch(f"/api/marathons/{marathon_id}", json={"announcements": "loud"})
    assert bad.status_code == 422 and bad.json()["error"] == "bad_switch"
    body = client.patch(f"/api/marathons/{marathon_id}", json={"announcements": "off"}).json()
    assert body["announcements"] == {"own": False, "on": False, "default": True}
    assert "no longer announces its BaF runners publicly" in body["message"]
    said = await web_row(wf, web, "web.marathon.announcements_set")
    assert (said["to"], said["on"], said["via"]) == (False, False, "website")
    body = client.patch(f"/api/marathons/{marathon_id}", json={"announcements": "follow"}).json()
    assert body["announcements"]["own"] is None and body["announcements"]["on"] is True


async def test_a_pairings_twitch_fix_is_set_shown_cleared_and_refused_in_words(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    paired = client.post(
        f"/api/marathons/{marathon_id}/people",
        json={"runner_name": "Somebody", "user_id": "77", "twitch_login": "twitch.tv/some_fix"},
    ).json()
    pairing = paired["pairings"][0]
    assert pairing["twitch_login"] == "some_fix"
    board = client.get(f"/api/marathons/{marathon_id}/people").json()
    person = next(one for one in board["baf"] if one["name"] == "Somebody")
    assert (person["login"], person["sheet_login"]) == ("some_fix", "somebody")

    cleared = client.patch(
        f"/api/marathons/{marathon_id}/people/{pairing['id']}", json={"twitch_login": ""}
    ).json()
    person = next(one for one in cleared["baf"] if one["name"] == "Somebody")
    assert (person["login"], person["sheet_login"]) == ("somebody", None)
    assert "back to the schedule" in cleared["message"]
    bad = client.patch(
        f"/api/marathons/{marathon_id}/people/{pairing['id']}", json={"twitch_login": "no good"}
    )
    assert bad.status_code == 422 and bad.json()["error"] == "bad_twitch"
    assert "is not a Twitch channel name" in bad.json()["message"]
    missing = client.patch(f"/api/marathons/{marathon_id}/people/999", json={})
    assert missing.status_code == 404
    said = await web_row(wf, web, "web.marathon.pairing_login_set")
    assert (said["from"], said["to"]) == ("some_fix", None)


async def test_the_drawer_reads_whether_the_heads_up_mentions_the_marathon_role_and_why_not(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    assert client.get(f"/api/marathons/{marathon_id}").json()["role_ping"] == {
        "mentions": False,
        "reason": "switch_off",
        "line": "",
    }

    client.patch(f"/api/marathons/{marathon_id}", json={"ping_role": True})
    unset = client.get(f"/api/marathons/{marathon_id}").json()["role_ping"]
    assert (unset["mentions"], unset["reason"]) == (False, "unset")
    assert unset["line"] == (
        "The Marathon role is not mentioned: no role is picked in marathon_role_id."
    )

    role = web.guild.roles[0]
    role.mentionable = True
    await web.store.set(wf.GUILD_ID, "marathon_role_id", role.id)
    found = client.get(f"/api/marathons/{marathon_id}").json()["role_ping"]
    assert (found["mentions"], found["reason"]) == (True, None)
    assert found["line"] == (
        f"The public heads-up 15 minutes before a BaF run mentions @{role.name}."
    )
    assert "<@&" not in found["line"]

    await web.store.set(wf.GUILD_ID, "marathon_role_pings", False)
    off = client.get(f"/api/marathons/{marathon_id}").json()["role_ping"]
    assert (off["mentions"], off["reason"]) == (False, "role_pings_off")
    assert off["line"] == "The Marathon role is not mentioned: marathon_role_pings is off."


async def test_the_retired_auto_highlight_field_is_gone_and_a_patch_answers_in_words(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    assert "public_highlight" not in client.get(f"/api/marathons/{marathon_id}").json()

    for given in (True, False, "loud"):
        answer = client.patch(f"/api/marathons/{marathon_id}", json={"public_highlight": given})
        assert answer.status_code == 200
        assert "part of Runner announcements now" in answer.json()["message"]
    seen = [kind for kind, _details in await wf.web_rows_in(web.db)]
    assert "web.marathon.public_highlight_set" not in seen


async def test_following_again_spotlights_a_channel_whose_marathon_is_in_reach(
    client, sign_in, web, cog, wf
):
    await web.store.set(wf.GUILD_ID, "marathon_spotlight_lead_minutes", 90)
    spotlight_id = await add_channel(
        web.db, wf.GUILD_ID, "rpglimitbreak", added_by=7, expires_at=None, pin=True, spotlight=False
    )
    sign_in(client)
    marathon_id = add(client, spotlight_id=str(spotlight_id)).json()["id"]
    row = await channel_by_id(web.db, spotlight_id)
    assert row["spotlight"] == 1 and row["spotlit_by_marathon"] == marathon_id

    client.patch(f"/api/marathons/{marathon_id}", json={"spotlight_mode": "off"})
    assert (await channel_by_id(web.db, spotlight_id))["spotlight"] == 0
    client.patch(f"/api/marathons/{marathon_id}", json={"spotlight_mode": "follow"})
    assert (await channel_by_id(web.db, spotlight_id))["spotlight"] == 1


async def test_archive_it_moves_a_marathon_and_the_archive_lists_it_read_only(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    assert client.get("/api/marathons/archive").json()["total"] == 0

    moved = client.post(f"/api/marathons/{marathon_id}/archive")
    assert moved.status_code == 200
    body = moved.json()
    assert body["archived"] is True and body["archived_why"] == "staff"
    assert "in the archive" in body["message"]
    assert body["archived_word"].startswith("Archived ")
    assert len(body["run_list"]) == 3 and body["archived_why_word"] == "archived by staff"
    assert client.get("/api/marathons").json()["marathons"] == []

    listed = client.get("/api/marathons/archive?limit=5&offset=0").json()
    assert (listed["total"], listed["limit"], listed["offset"]) == (1, 5, 0)
    assert [one["name"] for one in listed["marathons"]] == ["AGDQ 2027"]
    assert listed["marathons"][0]["ours"] == 1
    people = client.get(f"/api/marathons/{marathon_id}/people").json()
    assert people["archived"] is True
    assert [one["name"] for one in people["baf"]] == ["Sky"]
    assert "web.marathon.archived" in await wf.kinds_in(web.db)
    assert client.post(f"/api/marathons/{marathon_id}/refresh").status_code == 404


async def test_restore_brings_it_back_paused_and_refuses_in_words_twice(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    client.post(f"/api/marathons/{marathon_id}/archive")

    back = client.post(f"/api/marathons/{marathon_id}/restore")
    assert back.status_code == 200
    body = back.json()
    assert body["archived"] is False and body["active"] is False
    assert "back on the list, paused" in body["message"]
    assert len(body["run_list"]) == 3
    assert "web.marathon.restored" in await wf.kinds_in(web.db)

    again = client.post(f"/api/marathons/{marathon_id}/restore")
    assert again.status_code == 404 and "no archived marathon" in again.json()["message"]


async def test_track_ignore_and_back_are_routes_and_every_row_says_its_state(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    row = client.get(f"/api/marathons/{marathon_id}").json()
    assert row["tracked_state"] == "found" and row["tracked"] is False
    assert row["thread_url"] is None and row["tracked_at"] is None

    tracked = track(client, marathon_id)
    assert tracked["tracked_state"] == "tracked" and tracked["tracked_by_name"]
    assert "is tracked" in tracked["message"]
    ignored = client.post(f"/api/marathons/{marathon_id}/ignore", json={"on": True}).json()
    assert ignored["tracked_state"] == "ignored" and ignored["tracked"] is False
    assert ignored["ignored_at"] and "is ignored" in ignored["message"]
    back = client.post(f"/api/marathons/{marathon_id}/ignore", json={"on": False}).json()
    assert back["tracked_state"] == "found"
    track(client, marathon_id)
    off = client.post(f"/api/marathons/{marathon_id}/track", json={"on": False}).json()
    assert off["tracked_state"] == "found" and "not tracked any more" in off["message"]
    bad = client.post(f"/api/marathons/{marathon_id}/track", json={"on": "yes"})
    assert bad.status_code == 422 and bad.json()["error"] == "bad_on"
    listed = client.get("/api/marathons").json()["marathons"][0]
    assert listed["tracked_state"] == "found"
    kinds = await wf.kinds_in(web.db)
    for kind in ("tracked", "untracked", "ignored", "unignored"):
        assert f"web.marathon.{kind}" in kinds


async def test_track_refuses_in_words_when_the_channel_is_opted_out(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    row_id = await add_channel(
        web.db, wf.GUILD_ID, "gamesdonequick", added_by=7, expires_at=None, pin=True
    )
    marathon_id = add(client, spotlight_id=row_id).json()["id"]
    await web.db.conn.execute(
        "UPDATE spotlight_channels SET marathons = 0 WHERE id = ?", (row_id,)
    )
    await web.db.conn.commit()
    refused = client.post(f"/api/marathons/{marathon_id}/track", json={})
    assert refused.status_code == 409 and refused.json()["error"] == "channel_opted_out"
    assert "opted out of marathons" in refused.json()["message"]
    assert (await get_marathon(web.db, wf.GUILD_ID, marathon_id))["tracked_at"] is None


async def test_the_detail_carries_the_channel_row_as_go_live_reads_it_and_its_state(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    spotlight_id = await add_channel(
        web.db, wf.GUILD_ID, "rpglimitbreak", added_by=7, expires_at=None, pin=True, spotlight=False
    )
    marathon_id = add(client, spotlight_id=str(spotlight_id)).json()["id"]
    bare_id = client.post(
        "/api/marathons",
        json={"name": "GDQx", "schedule_url": "https://gamesdonequick.com/schedule/75"},
    ).json()["id"]

    body = client.get(f"/api/marathons/{marathon_id}").json()
    listed = next(
        one for one in client.get("/api/golive/spotlight").json() if one["id"] == spotlight_id
    )
    assert body["channel_spotlight"] == listed | {"sessions": body["channel_spotlight"]["sessions"]}
    assert body["spotlight_state"]["state"] in ("off", "waiting", "held")
    assert body["spotlight_state"]["tail_minutes"] == 60

    changed = client.patch(
        f"/api/golive/spotlight/{spotlight_id}", json={"spotlight": True, "days": 7}
    ).json()
    after = client.get(f"/api/marathons/{marathon_id}").json()
    assert after["channel_spotlight"]["spotlight"] is True
    assert after["channel_spotlight"]["expires_at"] == changed["expires_at"]
    assert after["spotlight_state"]["state"] == "until"
    none = client.get(f"/api/marathons/{bare_id}").json()
    assert none["channel_spotlight"] is None and none["spotlight_state"]["state"] == "none"


async def test_patch_schedule_url_moves_the_marathon_to_a_readable_link_and_keeps_its_id(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    track(client, marathon_id)
    other = add(client, name="ESA Summer", schedule_url="https://horaro.net/esa/2026-summer2")
    assert other.status_code == 200

    body = client.patch(
        f"/api/marathons/{marathon_id}",
        json={"schedule_url": "https://oengus.io/marathon/ss4lhs26"},
    ).json()

    assert body["id"] == marathon_id and body["tracked"] is True
    assert (body["source"], body["schedule_url"]) == (
        "oengus",
        "https://oengus.io/marathon/ss4lhs26",
    )
    assert "reads its schedule from the new link now" in body["message"] and body["runs"] == 3
    said = await web_row(wf, web, "web.marathon.link_changed")
    assert said["old"]["url"] == URL and said["new"]["source"] == "oengus"

    unknown = client.patch(f"/api/marathons/{marathon_id}", json={"schedule_url": "https://example.com/x"})
    assert unknown.status_code == 422 and unknown.json()["error"] == "unknown_site"
    assert "Lady Arcaders calendars" in unknown.json()["message"]
    taken = client.patch(
        f"/api/marathons/{marathon_id}",
        json={"schedule_url": "https://horaro.net/esa/2026-summer2"},
    )
    assert taken.status_code == 409 and taken.json()["error"] == "duplicate"
    assert "**ESA Summer** already follows that schedule" in taken.json()["message"]


async def test_post_it_to_the_inbox_now_is_a_route_that_posts_once_and_refuses_in_words(
    client, sign_in, web, cog, wf
):
    forum = web.guild.get_channel(wf.OTHER_CHANNEL_ID)
    forum.type = discord.ChannelType.forum
    await web.store.set(wf.GUILD_ID, "marathon_inbox_channel_id", wf.OTHER_CHANNEL_ID)
    sign_in(client)
    cog.client.runs_given = []
    marathon_id = add(client).json()["id"]
    assert client.get(f"/api/marathons/{marathon_id}").json()["inbox_message_url"] is None

    body = client.post(f"/api/marathons/{marathon_id}/inbox", json={}).json()

    assert "inbox message is up" in body["message"]
    assert body["inbox_message_url"].startswith("https://discord.com/channels/")
    said = await web_row(wf, web, "web.marathon.inbox_posted")
    assert said["early"] is True and said["marathon_id"] == marathon_id
    again = client.post(f"/api/marathons/{marathon_id}/inbox", json={})
    assert again.status_code == 409 and again.json()["error"] == "already_posted"
    await web.store.set(wf.GUILD_ID, "marathon_mode", "off")
    off = client.post(f"/api/marathons/{marathon_id}/inbox", json={})
    assert off.status_code == 409 and "Marathon posts are off" in off.json()["message"]


async def test_a_baf_persons_opt_out_is_shown_on_the_people_card_and_moved_both_ways(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    client.post(
        f"/api/marathons/{marathon_id}/people",
        json={"runner_name": "Interview Crew", "user_id": "77"},
    )
    board = client.get(f"/api/marathons/{marathon_id}/people").json()
    crew = next(one for one in board["baf"] if one["name"] == "Interview Crew")
    assert crew["opted_out"] is False
    assert all(one["opted_out"] is None for one in board["others"])

    out = client.post(f"/api/marathons/{marathon_id}/people/77/opt-out")
    assert out.status_code == 200 and "is opted out of" in out.json()["message"]
    crew = next(one for one in out.json()["baf"] if one["name"] == "Interview Crew")
    assert crew["opted_out"] is True
    said = await web_row(wf, web, "web.marathon.announce_opted_out")
    assert (said["members"], said["via"]) == ([77], "website")

    back = client.delete(f"/api/marathons/{marathon_id}/people/77/opt-out")
    assert back.status_code == 200 and "is back in" in back.json()["message"]
    crew = next(one for one in back.json()["baf"] if one["name"] == "Interview Crew")
    assert crew["opted_out"] is False
    stranger = client.post(f"/api/marathons/{marathon_id}/people/424242/opt-out")
    assert stranger.status_code == 404 and stranger.json()["error"] == "not_baf"


async def test_patch_the_host_announcements_switch_off_by_default_and_logged(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    first = client.get(f"/api/marathons/{marathon_id}").json()
    assert first["host_announcements"] == {"own": None, "on": False, "default": False}

    bad = client.patch(f"/api/marathons/{marathon_id}", json={"host_announcements": "loud"})
    assert bad.status_code == 422 and bad.json()["error"] == "bad_switch"
    assert "Host announcements" in bad.json()["message"]
    body = client.patch(f"/api/marathons/{marathon_id}", json={"host_announcements": "on"}).json()
    assert body["host_announcements"] == {"own": True, "on": True, "default": False}
    assert "announces its BaF hosts publicly now" in body["message"]
    said = await web_row(wf, web, "web.marathon.host_announcements_set")
    assert (said["from"], said["to"], said["on"], said["via"]) == (None, True, True, "website")
    body = client.patch(
        f"/api/marathons/{marathon_id}", json={"host_announcements": "follow"}
    ).json()
    assert body["host_announcements"]["own"] is None and body["host_announcements"]["on"] is False


async def test_a_runs_own_answer_is_shown_on_the_run_and_moved_from_the_site(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    client.post(
        f"/api/marathons/{marathon_id}/people",
        json={"runner_name": "Interview Crew", "user_id": "77"},
    )

    def crew():
        detail = client.get(f"/api/marathons/{marathon_id}").json()
        run = next(one for one in detail["run_list"] if one["game"] == "Blaster Master")
        person = next(one for one in run["people"] if one["name"] == "Interview Crew")
        return run["id"], person["announce"]

    run_id, shown = crew()
    assert (shown["role"], shown["answer"], shown["announced"], shown["why"]) == (
        "host",
        None,
        False,
        "hosts_off",
    )
    assert shown["move"] == "in" and shown["move_label"] == "Announce Interview Crew"
    assert shown["said"].startswith("Interview Crew: not announced for this run — host")
    path = f"/api/marathons/{marathon_id}/runs/{run_id}/people/77/announce"

    done = client.post(path, json={"to": "in"})
    assert done.status_code == 200
    assert "is announced for **Blaster Master**" in done.json()["message"]
    assert {"baf", "others", "pairings"} <= set(done.json())
    _, shown = crew()
    assert (shown["answer"], shown["announced"], shown["why"], shown["move"]) == (
        "in",
        True,
        "run",
        "default",
    )
    said = await web_row(wf, web, "web.marathon.announce_run_set")
    assert (said["member"], said["from"], said["to"], said["via"]) == (
        77,
        "default",
        "in",
        "website",
    )

    back = client.post(path, json={"to": "default"})
    assert back.status_code == 200 and "follows the defaults again" in back.json()["message"]
    assert crew()[1]["answer"] is None
    bad = client.post(path, json={"to": "maybe"})
    assert bad.status_code == 422 and bad.json()["error"] == "bad_announce"
    missing = client.post(path, json={})
    assert missing.status_code == 422 and "nothing was changed" in missing.json()["message"]
    stranger = client.post(
        f"/api/marathons/{marathon_id}/runs/{run_id}/people/424242/announce", json={"to": "in"}
    )
    assert stranger.status_code == 404 and stranger.json()["error"] == "not_on_run"
    gone = client.post(
        f"/api/marathons/{marathon_id}/runs/999999/people/77/announce", json={"to": "in"}
    )
    assert gone.status_code == 404
    unmatched = client.get(f"/api/marathons/{marathon_id}").json()["run_list"][0]["people"][0]
    assert unmatched["announce"] is None


async def test_a_run_that_is_over_refuses_its_own_answer_on_the_site_in_words(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    client.post(
        f"/api/marathons/{marathon_id}/people",
        json={"runner_name": "Interview Crew", "user_id": "77"},
    )

    def crew():
        detail = client.get(f"/api/marathons/{marathon_id}").json()
        run = next(one for one in detail["run_list"] if one["game"] == "Blaster Master")
        person = next(one for one in run["people"] if one["name"] == "Interview Crew")
        return run["id"], person["announce"]

    run_id, _ = crew()
    await web.db.conn.execute("UPDATE marathon_runs SET state = 'done' WHERE id = ?", (run_id,))
    await web.db.conn.commit()
    path = f"/api/marathons/{marathon_id}/runs/{run_id}/people/77/announce"

    for to in ("in", "out", "default"):
        said = client.post(path, json={"to": to})
        assert said.status_code == 409 and said.json()["error"] == "run_over"
        assert said.json()["message"] == "**Blaster Master** is over, so nothing was changed."

    _, shown = crew()
    assert shown["answer"] is None and shown["move"] is None
    kinds = [seen for seen, _ in await wf.web_rows_in(web.db)]
    assert "web.marathon.announce_run_set" not in kinds


async def test_how_a_persons_name_is_written_is_shown_on_the_people_card_and_moved(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    client.post(
        f"/api/marathons/{marathon_id}/people",
        json={"runner_name": "Interview Crew", "user_id": "77"},
    )
    board = client.get(f"/api/marathons/{marathon_id}/people").json()
    crew = next(one for one in board["baf"] if one["name"] == "Interview Crew")
    assert crew["mention"] == {
        "plain": False,
        "own": None,
        "move": "plain",
        "move_label": "No @ for Interview Crew",
    }
    assert all(one["mention"] is None for one in board["others"])

    done = client.post(f"/api/marathons/{marathon_id}/people/77/mention", json={"to": "plain"})
    assert done.status_code == 200 and "with no @" in done.json()["message"]
    crew = next(one for one in done.json()["baf"] if one["name"] == "Interview Crew")
    assert (crew["mention"]["plain"], crew["mention"]["own"], crew["mention"]["move"]) == (
        True,
        "plain",
        "mention",
    )
    said = await web_row(wf, web, "web.marathon.mention_set")
    assert (said["member"], said["from"], said["to"], said["via"]) == (
        77,
        "mention",
        "plain",
        "website",
    )
    back = client.post(f"/api/marathons/{marathon_id}/people/77/mention", json={"to": "mention"})
    assert back.status_code == 200 and "as an @ again" in back.json()["message"]
    bad = client.post(f"/api/marathons/{marathon_id}/people/77/mention", json={"to": "loud"})
    assert bad.status_code == 422 and bad.json()["error"] == "bad_mention"
    stranger = client.post(
        f"/api/marathons/{marathon_id}/people/424242/mention", json={"to": "plain"}
    )
    assert stranger.status_code == 404 and stranger.json()["error"] == "not_baf"


async def test_the_drawer_reads_the_baf_event_switch_what_was_worked_out_and_why(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]

    found = client.get(f"/api/marathons/{marathon_id}").json()["baf_event"]

    assert (found["own"], found["choice"]) == (None, "follow")
    assert (found["answer"], found["reason"]) == ("no", "mixed")
    assert found["worked_out"]["answer"] == "no"
    assert found["worked_out"]["reason_word"] == "1 of 3 runs have a BaF runner"
    assert found["answer_word"] == "not a BaF event"
    assert (found["runs"], found["baf"], found["ask"], found["asked"]) == (3, 1, None, False)
    assert found["line"] == "**AGDQ 2027** is not a BaF event — 1 of 3 runs have a BaF runner."
    (day,) = found["days"]
    assert (day["runs"], day["baf"], day["pinged"], day["carrier"]) == (3, 1, None, None)
    assert (day["ping"], day["line"], day["governed"]) == ("per_run", "", False)
    assert "answer" not in day and "reason" not in day and "ask" not in day
    assert found["lines"] == [found["line"]]


async def test_patch_baf_event_takes_yes_no_and_follow_and_leaves_one_web_row_each(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]

    yes = client.patch(f"/api/marathons/{marathon_id}", json={"baf_event": "yes"})

    assert yes.status_code == 200, yes.text
    assert "is a BaF event now" in yes.json()["message"]
    assert (yes.json()["baf_event"]["own"], yes.json()["baf_event"]["choice"]) == (True, "yes")
    assert (yes.json()["baf_event"]["answer"], yes.json()["baf_event"]["reason"]) == (
        "yes",
        "staff",
    )
    assert yes.json()["baf_event"]["worked_out"]["answer"] == "no"
    said = await web_row(wf, web, "web.marathon.baf_event_set")
    assert (said["from"], said["to"], said["via"]) == ("follow", "yes", "website")
    cur = await web.db.conn.execute(
        "SELECT kind FROM action_log WHERE kind LIKE '%baf_event_set' ORDER BY id"
    )
    assert [row["kind"] for row in await cur.fetchall()] == ["web.marathon.baf_event_set"]

    no = client.patch(f"/api/marathons/{marathon_id}", json={"baf_event": False})
    assert no.json()["baf_event"]["choice"] == "no"
    follow = client.patch(f"/api/marathons/{marathon_id}", json={"baf_event": None})
    assert follow.json()["baf_event"]["choice"] == "follow"
    assert "worked out from the schedule now" in follow.json()["message"]

    bad = client.patch(f"/api/marathons/{marathon_id}", json={"baf_event": "maybe"})
    assert bad.status_code == 422 and bad.json()["error"] == "bad_baf_event"
    assert "Say follow, yes or no" in bad.json()["message"]
    assert client.get(f"/api/marathons/{marathon_id}").json()["baf_event"]["choice"] == "follow"


async def test_patch_clears_the_questions_answer_and_follow_says_what_following_gives(
    client, sign_in, web, cog, wf
):
    import json

    from black_bloc import marathon_baf_event as baf

    sign_in(client)
    marathon_id = add(client).json()["id"]
    said = {"event": True, "message_id": 5, "answer": "yes", "answered_by": 7}
    await web.db.conn.execute(
        "UPDATE marathons SET baf_event_ask = ? WHERE id = ?", (json.dumps([said]), marathon_id)
    )
    await web.db.conn.commit()

    switched = client.patch(f"/api/marathons/{marathon_id}", json={"baf_event": "no"}).json()
    found = switched["baf_event"]
    assert (found["answer"], found["reason"], found["ask"]) == ("no", "staff", "answered")
    assert (found["worked_out"]["answer"], found["worked_out"]["reason"]) == ("yes", "leads")
    assert found["worked_out"]["answer_word"] == "a BaF event"
    followed = client.patch(f"/api/marathons/{marathon_id}", json={"baf_event": None}).json()
    assert followed["baf_event"]["answer"] == found["worked_out"]["answer"]
    assert followed["baf_event"]["reason"] == found["worked_out"]["reason"]

    bad = client.patch(f"/api/marathons/{marathon_id}", json={"baf_event_answer": "maybe"})
    assert bad.status_code == 422 and bad.json()["error"] == "bad_baf_event_answer"
    assert "Say clear" in bad.json()["message"]
    cleared = client.patch(f"/api/marathons/{marathon_id}", json={"baf_event_answer": "clear"})

    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["message"] == (
        "The answer was cleared, so **AGDQ 2027** is not a BaF event now."
    )
    after = cleared.json()["baf_event"]
    assert (after["answer"], after["reason"], after["ask"]) == ("no", "mixed", None)
    assert after["worked_out"]["reason"] == "mixed"
    rows = [details for kind, details in await wf.web_rows_in(web.db) if kind.endswith("event_set")]
    assert [(one["from"], one["to"], one.get("cleared"), one["via"]) for one in rows] == [
        ("follow", "no", None, "website"),
        ("no", "follow", None, "website"),
        ("yes", "follow", True, "website"),
    ]
    cur = await web.db.conn.execute(
        "SELECT baf_event_ask FROM marathons WHERE id = ?", (marathon_id,)
    )
    (left,) = baf.asks_of({"baf_event_ask": (await cur.fetchone())["baf_event_ask"]})
    assert "answer" not in left and left["cleared"] is True and left["cleared_by"]
    again = client.patch(f"/api/marathons/{marathon_id}", json={"baf_event_answer": "clear"})
    assert again.status_code == 200 and "has no answer to clear" in again.json()["message"]


async def test_a_baf_event_day_says_which_heads_up_carries_the_ping_in_the_drawer(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    track(client, marathon_id)
    role = web.guild.roles[0]
    role.mentionable = True
    await web.store.set(wf.GUILD_ID, "marathon_role_id", role.id)
    client.patch(f"/api/marathons/{marathon_id}", json={"ping_role": True, "baf_event": "yes"})

    body = client.get(f"/api/marathons/{marathon_id}").json()

    (day,) = body["baf_event"]["days"]
    assert day["carrier"]["game"] == "Super Metroid" and day["carrier"]["minutes"] == 120
    assert (day["ping"], day["no_ping"], day["pinged"]) == ("will", None, None)
    assert day["line"].endswith(
        f": @{role.name} is mentioned once, on the heads-up 120 minutes before **Super Metroid**."
    )
    assert "<t:" not in day["line"] and "<@&" not in day["line"]
    assert body["baf_event"]["lines"] == [
        "**AGDQ 2027** is a BaF event — the BaF event switch says so.",
        day["line"],
    ]
    assert body["role_ping"]["mentions"] is True and body["role_ping"]["line"] == ""


async def test_the_drawer_reads_the_threads_switches_in_order_with_their_words_and_patches(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]

    found = client.get(f"/api/marathons/{marathon_id}").json()["controls"]

    assert [one["action"] for one in found] == ["announce", "hostannounce", "ping", "event", "baf"]
    assert [one["label"] for one in found] == [
        "Runner announcements: on · turn off",
        "Host announcements: off · turn on",
        "Ping the marathon role: off · turn on",
        found[3]["label"],
        "BaF event: no (1 of 3 runs) · say yes",
    ]
    assert found[0]["patch"] == {"announcements": False} and found[0]["on"] is True
    assert found[4]["patch"] == {"baf_event": "yes"} and found[4]["on"] is False
    body = client.patch(f"/api/marathons/{marathon_id}", json=found[0]["patch"]).json()
    assert body["controls"][0]["label"] == "Runner announcements: off · turn on"
    assert body["controls"][0]["patch"] == {"announcements": True}


async def test_a_marathon_with_a_channel_carries_the_spotlight_switch_after_the_ping(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    spotlight_id = await add_channel(
        web.db, wf.GUILD_ID, "gamesdonequick", added_by=7, expires_at=at(600), pin=True
    )
    marathon_id = add(client, spotlight_id=str(spotlight_id)).json()["id"]

    found = client.get(f"/api/marathons/{marathon_id}").json()["controls"]

    assert [one["action"] for one in found][2:4] == ["ping", "spotlight"]
    spot = found[3]
    assert spot["label"] == "Spotlight follows the schedule: on · turn off"
    assert spot["patch"] == {"spotlight_mode": "off"}
    body = client.patch(f"/api/marathons/{marathon_id}", json=spot["patch"]).json()
    assert body["controls"][3]["label"] == "Spotlight follows the schedule: off · turn on"


async def test_the_people_answer_carries_the_people_views_labels_as_the_keys_say_them(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    marathon_id = add(client).json()["id"]
    await web.store.set(wf.GUILD_ID, "marathon_public_button_opt_out", "Leave this one out")

    labels = client.get(f"/api/marathons/{marathon_id}/people").json()["labels"]

    assert labels["opt_out"] == "Leave this one out"
    assert labels["spotlight"] == "Spotlight their channel…"
    assert labels["unspotlight"] == "Stop spotlighting their channel"
    assert labels["link_near"] == "Link @{username}"
    assert set(labels) == {
        "link_near",
        "unlink",
        "twitch",
        "spotlight",
        "unspotlight",
        "opt_out",
        "opt_in",
    }


async def test_the_drawer_reads_the_threads_spotlight_line_with_the_time_left_to_fill(
    client, sign_in, web, cog, wf
):
    sign_in(client)
    spotlight_id = await add_channel(
        web.db, wf.GUILD_ID, "gamesdonequick", added_by=7, expires_at=at(600), pin=True
    )
    lit = add(client, spotlight_id=str(spotlight_id)).json()["id"]
    assert client.get(f"/api/marathons/{lit}").json()["spotlight_line"] == (
        "Spotlight: on now until {until}"
    )
    client.patch(f"/api/marathons/{lit}", json={"spotlight_id": None})
    assert client.get(f"/api/marathons/{lit}").json()["spotlight_line"] == (
        "Spotlight: no channel to spotlight"
    )
