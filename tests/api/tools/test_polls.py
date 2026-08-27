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
)

MEMBER_ID = 21
LEAD_ID = 7


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


async def test_the_index_says_the_create_form_is_not_here_yet(client, seeded):
    assert any("next update" in note for note in client.get("/api/polls").json()["notes"])


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
    assert "web.poll.end" in await wf.kinds_in(web.db)


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
    assert "web.poll.cancel" in await wf.kinds_in(web.db)


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


async def test_every_poll_route_is_for_staff_only(client, seeded, sign_in):
    sign_in(client, uid=MEMBER_ID, staff=False)

    for method, path in (
        ("GET", "/api/polls"),
        ("GET", "/api/polls/requests"),
        ("GET", f"/api/polls/{seeded['open']}"),
        ("GET", f"/api/polls/{seeded['open']}/export.csv"),
        ("POST", f"/api/polls/{seeded['open']}/end"),
        ("POST", f"/api/polls/{seeded['open']}/cancel"),
        ("POST", f"/api/polls/requests/{seeded['waiting']}/approve"),
    ):
        response = client.request(method, path, json={} if method == "POST" else None)
        assert response.status_code == 403, f"{method} {path} answered {response.status_code}"
