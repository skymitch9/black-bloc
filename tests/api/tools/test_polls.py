from __future__ import annotations

import pytest

from black_bloc import polls as pure
from black_bloc.api.tools.polls import PER_PAGE_MAX
from black_bloc.cogs.community.polls import (
    add_options,
    create_poll,
    get_poll,
    options_of,
    record_vote,
    save_results,
    set_posted,
    set_recurrence,
)
from black_bloc.timezones import DEFAULT_TZ

MEMBER_ID = 21
LEAD_ID = 7
TEST_CHANNEL = 500


async def seed_poll(
    db,
    guild_id,
    *,
    question="Pizza or tacos?",
    status=pure.OPEN,
    anonymous=False,
    channel_id=None,
    labels=("Pizza", "Tacos"),
):
    poll_id = await create_poll(
        db,
        guild_id,
        MEMBER_ID,
        question=question,
        kind=pure.SINGLE,
        surface=pure.NATIVE,
        multi=False,
        anonymous=anonymous,
        results=pure.LIVE,
        hours=24,
        channel_id=channel_id,
        ping_role_id=None,
        status=status,
    )
    await add_options(db, poll_id, list(labels))
    return poll_id


@pytest.fixture
async def seeded(client, sign_in, web, guild, wf):
    wf.member(guild, MEMBER_ID, name="ada")
    wf.member(guild, LEAD_ID, name="lead", staff=True)
    sign_in(client)
    open_id = await seed_poll(web.db, wf.GUILD_ID, channel_id=wf.TEST_CHANNEL_ID)
    await set_posted(
        web.db,
        open_id,
        channel_id=wf.TEST_CHANNEL_ID,
        message_id=9001,
        finishes_at=pure.closes_at(24),
    )
    waiting_id = await seed_poll(
        web.db, wf.GUILD_ID, question="Cookout?", status=pure.PENDING_REVIEW
    )
    return {"open": open_id, "waiting": waiting_id}


async def test_the_index_lists_every_poll_newest_first_with_its_counts(client, seeded):
    body = client.get("/api/polls").json()

    assert body["total"] == 2 and body["shown"] == 2
    assert [row["id"] for row in body["polls"]] == [seeded["waiting"], seeded["open"]]
    first = body["polls"][0]
    assert first["creator_name"] == "Ada"
    assert [item["label"] for item in first["options"]] == ["Pizza", "Tacos"]
    assert first["winner_position"] is None


async def test_the_index_can_be_narrowed_to_one_state(client, seeded):
    body = client.get("/api/polls?status=open").json()

    assert [row["id"] for row in body["polls"]] == [seeded["open"]]


async def test_a_state_no_poll_can_be_in_is_refused_in_words(client, seeded):
    response = client.get("/api/polls?status=wibble")

    assert response.status_code == 400
    assert "wibble" in response.json()["message"]


async def test_the_index_pages_and_clamps_what_it_is_asked_for(client, seeded):
    first = client.get("/api/polls?page=1&per_page=1").json()
    second = client.get("/api/polls?page=2&per_page=1").json()

    assert first["shown"] == 1 and second["shown"] == 1
    assert first["polls"][0]["id"] != second["polls"][0]["id"]
    assert client.get("/api/polls?per_page=9999").json()["per_page"] == PER_PAGE_MAX
    assert client.get("/api/polls?page=wibble").json()["page"] == 1


def creating(client, **body):
    asked = {
        "question": "Pizza or tacos?",
        "options": ["Pizza", "Tacos"],
        "hours": 24,
        "channel_id": str(TEST_CHANNEL),
    }
    asked.update(body)
    return client.post("/api/polls", json=asked)


async def test_the_form_posts_a_poll_and_says_where_it_went(client, seeded, web, wf):
    response = creating(client)

    assert response.status_code == 200
    made = response.json()
    assert made["poll"]["status"] == pure.OPEN and made["poll"]["surface"] == pure.NATIVE
    assert made["note"] is None
    assert str(TEST_CHANNEL) in made["message"]
    assert web.guild.get_channel(TEST_CHANNEL).messages[-1].kwargs["poll"] is not None


async def test_the_form_is_refused_in_words_while_polls_are_switched_off(
    client, seeded, web, wf
):
    """The one-off route now gates on `poll_mode` the way the recurrence route beside it does."""
    await web.store.set(wf.GUILD_ID, "poll_mode", "off")
    before = len(await polls_in(web.db))

    response = creating(client)

    assert response.status_code == 409
    assert "turned off" in response.json()["message"]
    assert len(await polls_in(web.db)) == before


async def test_the_form_refuses_what_the_slash_command_refuses(client, seeded):
    response = creating(client, options=["Pizza"])

    assert response.status_code == 400
    assert "at least 2" in response.json()["message"]


async def test_the_form_derives_the_panel_and_says_why(client, seeded, web):
    made = creating(client, anonymous=True).json()

    assert made["poll"]["surface"] == pure.PANEL
    assert pure.PANEL_BECAUSE_ANONYMOUS in made["note"]
    posted = web.guild.get_channel(TEST_CHANNEL).messages[-1].kwargs
    assert "poll" not in posted and posted["view"] is not None


async def test_the_form_lays_out_a_date_poll_from_a_start_and_a_count(client, seeded, web):
    made = creating(
        client, kind=pure.DATE, options=None, start="2026-09-05", slots=3, step=1,
        step_unit=pure.STEP_DAYS,
    ).json()

    assert [item["label"] for item in made["poll"]["options"]] == [
        "Sat 05 Sep", "Sun 06 Sep", "Mon 07 Sep"
    ]


async def test_the_form_falls_back_to_the_default_channel_and_refuses_with_neither(
    client, seeded, web, wf
):
    await web.store.set(wf.GUILD_ID, "poll_channel_id", TEST_CHANNEL)
    assert creating(client, channel_id=None).status_code == 200

    await web.store.clear(wf.GUILD_ID, "poll_channel_id")
    response = creating(client, channel_id=None)

    assert response.status_code == 400
    assert "nowhere to put" in response.json()["message"]


async def test_the_form_will_not_post_outside_the_test_channel(client, seeded, web, wf):
    web.guard = wf.Guard()

    response = creating(client, channel_id=str(wf.OTHER_CHANNEL_ID))

    assert response.status_code == 409
    assert "test mode" in response.json()["message"]


async def test_the_form_holds_a_poll_when_review_is_on(client, seeded, web, wf):
    await web.store.set(wf.GUILD_ID, "poll_review_mode", "on")
    await web.store.set(wf.GUILD_ID, "staff_channel_id", TEST_CHANNEL)

    made = creating(client).json()

    assert made["poll"]["status"] == pure.PENDING_REVIEW
    assert "approve" in made["message"]
    assert web.guild.get_channel(TEST_CHANNEL).messages[-1].kwargs.get("view") is not None


async def test_creating_from_the_dashboard_leaves_a_web_line_in_the_log(client, seeded, web, wf):
    creating(client)

    cur = await web.db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    assert "web.poll.created" in [row["kind"] for row in await cur.fetchall()]


async def test_an_open_panel_reports_the_votes_it_holds_rather_than_zeroes(client, seeded, web):
    made = creating(client, anonymous=True).json()["poll"]
    option = (await options_of(web.db, int(made["id"])))[0]
    await record_vote(web.db, int(made["id"]), option["id"], MEMBER_ID)

    again = client.get(f"/api/polls/{made['id']}").json()["poll"]

    assert [item["votes"] for item in again["options"]] == [1, 0]


async def test_one_poll_comes_back_with_its_options_and_its_voters(client, seeded, web):
    option = (await options_of(web.db, seeded["open"]))[0]
    await record_vote(web.db, seeded["open"], option["id"], MEMBER_ID)

    body = client.get(f"/api/polls/{seeded['open']}").json()

    assert body["poll"]["question"] == "Pizza or tacos?"
    assert body["poll"]["message_id"] == "9001"
    assert [(v["user_id"], v["label"]) for v in body["votes"]] == [(str(MEMBER_ID), "Pizza")]
    assert body["votes"][0]["user_name"] == "Ada"


async def test_an_anonymous_poll_never_hands_out_a_voter_list(client, seeded, web, wf):
    poll_id = await seed_poll(web.db, wf.GUILD_ID, anonymous=True)
    option = (await options_of(web.db, poll_id))[0]
    await record_vote(web.db, poll_id, option["id"], MEMBER_ID)

    body = client.get(f"/api/polls/{poll_id}").json()

    assert body["poll"]["anonymous"] is True
    assert body["votes"] == []


async def test_a_poll_from_another_server_is_a_not_found_in_words(client, seeded, web):
    poll_id = await seed_poll(web.db, 999999)

    response = client.get(f"/api/polls/{poll_id}")

    assert response.status_code == 404
    assert str(poll_id) in response.json()["message"]


async def test_ending_a_poll_from_the_dashboard_closes_it_and_logs_the_web_line(
    client, seeded, web, wf
):
    response = client.post(f"/api/polls/{seeded['open']}/end")

    assert response.status_code == 200
    assert response.json()["poll"]["status"] == pure.CLOSED
    await wf.one_web_row(web.db, "web.poll.closed")


async def test_a_poll_that_is_already_closed_cannot_be_closed_again(client, seeded):
    client.post(f"/api/polls/{seeded['open']}/end")

    response = client.post(f"/api/polls/{seeded['open']}/end")

    assert response.status_code == 409
    assert "already" in response.json()["message"]


async def test_ending_a_poll_says_so_when_the_final_count_could_not_be_read(client, seeded):
    said = client.post(f"/api/polls/{seeded['open']}/end").json()["message"]

    assert "could not read the final count" in said


async def test_test_mode_refuses_to_end_a_poll_outside_the_test_channel(
    client, seeded, web, wf
):
    web.guard = wf.Guard()
    await web.db.conn.execute(
        "UPDATE polls SET channel_id = ? WHERE id = ?",
        (wf.OTHER_CHANNEL_ID, seeded["open"]),
    )
    await web.db.conn.commit()

    response = client.post(f"/api/polls/{seeded['open']}/end")

    assert response.status_code == 409
    assert "test mode" in response.json()["message"]
    assert (await get_poll(web.db, seeded["open"]))["status"] == pure.OPEN


async def test_cancelling_a_poll_from_the_dashboard_publishes_no_result(client, seeded, web, wf):
    response = client.post(f"/api/polls/{seeded['open']}/cancel")

    assert response.status_code == 200
    assert response.json()["poll"]["status"] == pure.CANCELLED
    await wf.one_web_row(web.db, "web.poll.cancelled")


async def test_a_cancelled_poll_cannot_be_cancelled_twice(client, seeded):
    client.post(f"/api/polls/{seeded['open']}/cancel")

    response = client.post(f"/api/polls/{seeded['open']}/cancel")

    assert response.status_code == 409
    assert "already" in response.json()["message"]


async def test_the_queue_shows_only_the_polls_waiting_on_a_decision(client, seeded):
    rows = client.get("/api/polls/requests").json()

    assert [row["id"] for row in rows] == [seeded["waiting"]]
    assert rows[0]["status"] == pure.PENDING_REVIEW


async def test_approving_from_the_dashboard_posts_the_poll_and_logs_the_web_line(
    client, seeded, web, wf, guild
):
    await web.db.conn.execute(
        "UPDATE polls SET channel_id = ? WHERE id = ?",
        (wf.TEST_CHANNEL_ID, seeded["waiting"]),
    )
    await web.db.conn.commit()

    response = client.post(f"/api/polls/requests/{seeded['waiting']}/approve")

    assert response.status_code == 200
    assert response.json()["poll"]["status"] == pure.OPEN
    assert guild.get_channel(wf.TEST_CHANNEL_ID).messages
    assert "web.poll.approved" in await wf.kinds_in(web.db)


async def test_denying_from_the_dashboard_needs_a_reason(client, seeded):
    response = client.post(f"/api/polls/requests/{seeded['waiting']}/deny", json={})

    assert response.status_code == 400
    assert "needs one line" in response.json()["message"]


async def test_denying_from_the_dashboard_keeps_the_reason_on_the_row(client, seeded, web, wf):
    response = client.post(
        f"/api/polls/requests/{seeded['waiting']}/deny", json={"reason": "not this week"}
    )

    assert response.status_code == 200
    assert response.json()["poll"]["deny_reason"] == "not this week"
    assert "web.poll.denied" in await wf.kinds_in(web.db)


async def test_a_poll_that_is_not_waiting_cannot_be_approved(client, seeded):
    response = client.post(f"/api/polls/requests/{seeded['open']}/approve")

    assert response.status_code == 409
    assert "not waiting" in response.json()["message"].lower()


async def test_test_mode_refuses_to_approve_a_poll_bound_for_another_channel(
    client, seeded, web, wf
):
    web.guard = wf.Guard()
    await web.db.conn.execute(
        "UPDATE polls SET channel_id = ? WHERE id = ?",
        (wf.OTHER_CHANNEL_ID, seeded["waiting"]),
    )
    await web.db.conn.commit()

    response = client.post(f"/api/polls/requests/{seeded['waiting']}/approve")

    assert response.status_code == 409
    assert (await get_poll(web.db, seeded["waiting"]))["status"] == pure.PENDING_REVIEW


async def test_the_export_carries_the_totals_and_one_row_per_voter(client, seeded, web):
    options = await options_of(web.db, seeded["open"])
    await record_vote(web.db, seeded["open"], options[0]["id"], MEMBER_ID)
    await save_results(
        web.db,
        seeded["open"],
        [
            {"position": 0, "label": "Pizza", "votes": 1},
            {"position": 1, "label": "Tacos", "votes": 0},
        ],
        1,
    )

    response = client.get(f"/api/polls/{seeded['open']}/export.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "poll-" in response.headers["content-disposition"]
    body = response.text
    assert "Pizza or tacos?" in body
    assert "0,Pizza,1" in body
    assert f"{MEMBER_ID},Ada,0,Pizza" in body


async def test_the_export_of_an_anonymous_poll_says_why_there_are_no_names(client, seeded, web, wf):
    poll_id = await seed_poll(web.db, wf.GUILD_ID, anonymous=True)

    body = client.get(f"/api/polls/{poll_id}/export.csv").text

    assert "nothing per-person to export" in body
    assert "user_id" not in body


async def test_the_export_of_an_archived_poll_says_the_voters_were_dropped(client, seeded, web):
    await save_results(
        web.db, seeded["open"], [{"position": 0, "label": "Pizza", "votes": 2}], 2
    )
    await web.db.conn.execute(
        "UPDATE poll_results SET votes_dropped = 2 WHERE poll_id = ?", (seeded["open"],)
    )
    await web.db.conn.commit()

    body = client.get(f"/api/polls/{seeded['open']}/export.csv").text

    assert "per-voter rows were dropped" in body


async def seed_recurrence(db, guild_id, *, cadence="daily", at="09:00", paused=False):
    poll_id = await create_poll(
        db,
        guild_id,
        MEMBER_ID,
        question="Are we running tonight?",
        kind=pure.SINGLE,
        surface=pure.NATIVE,
        multi=False,
        anonymous=False,
        results=pure.LIVE,
        hours=24,
        channel_id=TEST_CHANNEL,
        ping_role_id=None,
        status=pure.RECURRING,
    )
    await add_options(db, poll_id, ["Yes", "No"])
    following = None if paused else pure.next_occurrence(cadence, at, "America/Phoenix")
    await set_recurrence(
        db, poll_id, cadence, at, "America/Phoenix", following.isoformat() if following else None
    )
    return poll_id


async def test_the_recurrences_route_names_the_cadence_in_words(client, seeded, web, wf):
    await seed_recurrence(web.db, wf.GUILD_ID, cadence="weekly:sat", at="19:00")

    rows = client.get("/api/polls/recurrences").json()

    assert len(rows) == 1
    assert rows[0]["cadence_said"] == "every Saturday at 19:00 America/Phoenix"
    assert rows[0]["paused"] is False and rows[0]["next_at"] is not None


async def test_a_recurrence_never_shows_up_on_the_poll_index(client, seeded, web, wf):
    await seed_recurrence(web.db, wf.GUILD_ID)

    body = client.get("/api/polls").json()

    assert body["total"] == 2
    assert pure.RECURRING not in [row["status"] for row in body["polls"]]


async def test_pausing_and_starting_a_recurrence_from_the_dashboard(client, seeded, web, wf):
    recurrence_id = await seed_recurrence(web.db, wf.GUILD_ID)

    paused = client.post(f"/api/polls/recurrences/{recurrence_id}/pause", json={"paused": True})
    assert paused.json()["recurrence"]["paused"] is True

    started = client.post(f"/api/polls/recurrences/{recurrence_id}/pause", json={"paused": False})
    assert started.json()["recurrence"]["paused"] is False
    assert "running again" in started.json()["message"]


async def test_deleting_a_recurrence_stops_it_and_says_the_polls_are_untouched(
    client, seeded, web, wf
):
    recurrence_id = await seed_recurrence(web.db, wf.GUILD_ID)

    body = client.delete(f"/api/polls/recurrences/{recurrence_id}").json()

    assert "untouched" in body["message"]
    assert client.get("/api/polls/recurrences").json() == []
    assert (await get_poll(web.db, recurrence_id))["status"] == pure.CANCELLED


async def test_a_poll_number_that_is_not_a_recurrence_is_a_404(client, seeded):
    response = client.delete(f"/api/polls/recurrences/{seeded['open']}")

    assert response.status_code == 404
    assert "no repeating poll" in response.json()["message"]


def repeating(client, **body):
    asked = {
        "question": "Are we running tonight?",
        "options": ["Yes", "No"],
        "hours": 6,
        "channel_id": str(TEST_CHANNEL),
        "cadence": "weekly",
        "day": "sat",
        "at": "19:00",
        "tz": "America/Phoenix",
    }
    asked.update(body)
    return client.post("/api/polls/recurrences", json=asked)


async def polls_in(db) -> list:
    cur = await db.conn.execute("SELECT * FROM polls ORDER BY id")
    return list(await cur.fetchall())


async def test_the_form_saves_a_repeating_poll_and_names_the_cadence(client, seeded, web, wf):
    response = repeating(client)

    assert response.status_code == 200
    made = response.json()["recurrence"]
    assert made["cadence"] == "weekly:sat"
    assert made["cadence_said"] == "every Saturday at 19:00 America/Phoenix"
    assert made["paused"] is False and made["next_at"] is not None
    assert [item["label"] for item in made["options"]] == ["Yes", "No"]
    assert "will run every Saturday" in response.json()["message"]


async def test_a_repeating_poll_is_a_template_and_is_never_posted(client, seeded, web, wf):
    before = len(web.guild.get_channel(TEST_CHANNEL).messages)

    made = repeating(client).json()["recurrence"]

    row = await get_poll(web.db, int(made["id"]))
    assert row["status"] == pure.RECURRING
    assert row["recur_next_at"] is not None and row["message_id"] is None
    assert len(web.guild.get_channel(TEST_CHANNEL).messages) == before


async def test_saving_one_leaves_one_recur_created_line_saying_the_website_did_it(
    client, seeded, web, wf
):
    made = repeating(client).json()["recurrence"]

    rows = await wf.web_rows_in(web.db)
    created = [details for kind, details in rows if kind == "web.poll.recur_created"]
    assert len(created) == 1
    assert created[0]["via"] == "website"
    assert created[0]["recurrence_id"] == int(made["id"])
    assert [kind for kind, _ in rows] == ["web.poll.created", "web.poll.recur_created"]


async def test_a_saved_recurrence_shows_up_on_the_recurring_list(client, seeded):
    made = repeating(client).json()["recurrence"]

    rows = client.get("/api/polls/recurrences").json()

    assert [row["id"] for row in rows] == [int(made["id"])]


async def test_a_cadence_nobody_can_read_is_refused_in_words_and_writes_no_poll(
    client, seeded, web
):
    before = len(await polls_in(web.db))

    response = repeating(client, day="funday")

    assert response.status_code == 400
    assert "funday" in response.json()["message"]
    assert len(await polls_in(web.db)) == before


async def test_a_time_of_day_nobody_can_read_is_refused_before_any_row_exists(
    client, seeded, web
):
    before = len(await polls_in(web.db))

    response = repeating(client, at="half seven")

    assert response.status_code == 400
    assert "24-hour clock" in response.json()["message"]
    assert len(await polls_in(web.db)) == before


async def test_a_timezone_this_machine_does_not_know_is_refused_in_words(client, seeded, web):
    before = len(await polls_in(web.db))

    response = repeating(client, tz="Mars/Olympus")

    assert response.status_code == 400
    assert "Mars/Olympus" in response.json()["message"]
    assert len(await polls_in(web.db)) == before


async def test_a_date_poll_is_told_it_cannot_repeat(client, seeded, web):
    before = len(await polls_in(web.db))

    response = repeating(
        client, kind=pure.DATE, options=None, start="2026-09-05", slots=3, step=1
    )

    assert response.status_code == 400
    assert "cannot recur" in response.json()["message"]
    assert len(await polls_in(web.db)) == before


async def test_a_repeating_poll_will_not_be_pointed_outside_the_test_channel(
    client, seeded, web, wf
):
    web.guard = wf.Guard()
    before = len(await polls_in(web.db))

    response = repeating(client, channel_id=str(wf.OTHER_CHANNEL_ID))

    assert response.status_code == 409
    assert "test mode" in response.json()["message"]
    assert len(await polls_in(web.db)) == before


async def test_a_repeating_poll_is_refused_while_polls_are_switched_off(
    client, seeded, web, wf
):
    await web.store.set(wf.GUILD_ID, "poll_mode", "off")
    before = len(await polls_in(web.db))

    response = repeating(client)

    assert response.status_code == 409
    assert "turned off" in response.json()["message"]
    assert len(await polls_in(web.db)) == before


async def test_a_repeating_poll_is_refused_what_a_one_off_poll_is_refused(client, seeded):
    response = repeating(client, options=["Yes"])

    assert response.status_code == 400
    assert "at least 2" in response.json()["message"]


async def test_a_repeating_poll_falls_back_to_the_default_channel(client, seeded, web, wf):
    await web.store.set(wf.GUILD_ID, "poll_channel_id", TEST_CHANNEL)

    made = repeating(client, channel_id=None).json()["recurrence"]

    assert made["channel_id"] == str(TEST_CHANNEL)


async def test_a_repeating_poll_takes_the_default_timezone_when_none_is_typed(
    client, seeded, web
):
    made = repeating(client, tz=None).json()["recurrence"]

    assert made["tz"] == DEFAULT_TZ


async def test_a_repeating_poll_never_waits_on_a_lead_the_way_a_one_off_does(
    client, seeded, web, wf
):
    await web.store.set(wf.GUILD_ID, "poll_review_mode", "on")
    await web.store.set(wf.GUILD_ID, "staff_channel_id", TEST_CHANNEL)

    made = repeating(client).json()["recurrence"]

    assert (await get_poll(web.db, int(made["id"])))["status"] == pure.RECURRING


async def test_every_poll_route_is_for_staff_only(client, seeded, sign_in):
    sign_in(client, uid=MEMBER_ID, staff=False)

    for method, path in (
        ("GET", "/api/polls"),
        ("POST", "/api/polls"),
        ("GET", "/api/polls/requests"),
        ("GET", "/api/polls/recurrences"),
        ("POST", "/api/polls/recurrences"),
        ("POST", "/api/polls/recurrences/1/pause"),
        ("DELETE", "/api/polls/recurrences/1"),
        ("GET", f"/api/polls/{seeded['open']}"),
        ("GET", f"/api/polls/{seeded['open']}/export.csv"),
        ("POST", f"/api/polls/{seeded['open']}/end"),
        ("POST", f"/api/polls/{seeded['open']}/cancel"),
        ("POST", f"/api/polls/requests/{seeded['waiting']}/approve"),
    ):
        response = client.request(method, path, json={} if method == "POST" else None)
        assert response.status_code == 403, f"{method} {path} answered {response.status_code}"
