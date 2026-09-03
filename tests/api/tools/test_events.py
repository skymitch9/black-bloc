from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from black_bloc.events import create_event, get_event

ROUTES = [
    ("GET", "/api/events", None),
    ("GET", "/api/events/1", None),
    ("PUT", "/api/events/1", {"title": "x", "start": "2099-01-01 19:00"}),
    ("POST", "/api/events/1/approve", None),
    ("POST", "/api/events/1/deny", {"reason": "no"}),
    ("POST", "/api/events/1/cancel", {}),
]


def a_start(days: int = 3) -> str:
    """A `YYYY-MM-DD HH:MM` the validator will accept, read in the zone the body names."""
    return (datetime.now(UTC) + timedelta(days=days)).strftime("%Y-%m-%d %H:%M")


async def an_event(web, wf, *, status: str = "pending", requester: int = 21) -> int:
    starts = datetime.now(UTC) + timedelta(days=1)
    event_id = await create_event(
        web.db,
        wf.GUILD_ID,
        requester,
        title="Bloc night",
        description="come along",
        location="the park",
        starts_at=starts,
        finishes_at=starts + timedelta(hours=2),
    )
    if status != "pending":
        await web.db.conn.execute(
            "UPDATE events SET status = ? WHERE id = ?", (status, event_id)
        )
        await web.db.conn.commit()
    return event_id


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_event_route_needs_a_session(client, method, route, payload):
    assert client.request(method, route, json=payload).status_code == 401


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_event_route_refuses_a_non_staff_visitor(client, sign_in, method, route, payload):
    sign_in(client, uid=1234, staff=False)
    assert client.request(method, route, json=payload).status_code == 403


async def test_the_queue_lists_events_with_the_requester_resolved(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    await an_event(web, wf)
    await an_event(web, wf, status="denied")
    sign_in(client)

    everything = client.get("/api/events").json()
    pending = client.get("/api/events", params={"status": "pending"}).json()

    assert len(everything) == 2
    assert [row["status"] for row in pending] == ["pending"]
    assert pending[0]["requester_name"] == "Ada"
    assert pending[0]["minutes"] == 120
    assert pending[0]["title"] == "Bloc night"


def test_an_unknown_status_is_refused_by_name(client, sign_in):
    sign_in(client)
    response = client.get("/api/events", params={"status": "sideways"})
    assert response.status_code == 400
    assert "sideways" in response.json()["message"]


async def test_approving_moves_the_event_and_leaves_both_log_lines(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    web.guard = wf.Guard()
    event_id = await an_event(web, wf)
    sign_in(client, uid=7)

    response = client.post(f"/api/events/{event_id}/approve")

    assert response.status_code == 200
    assert response.json()["event"]["status"] == "approved"
    row = await get_event(web.db, event_id)
    assert row["status"] == "approved" and row["decided_by"] == 7
    assert (await wf.one_web_row(web.db, "web.event.approved"))["event_id"] == event_id


async def test_a_second_decision_is_refused_rather_than_taken_twice(client, sign_in, web, wf):
    web.guard = wf.Guard()
    event_id = await an_event(web, wf)
    sign_in(client)
    client.post(f"/api/events/{event_id}/approve")

    again = client.post(f"/api/events/{event_id}/deny", json={"reason": "changed my mind"})

    assert again.status_code == 409
    assert again.json()["error"] == "already_decided"
    assert "already" in again.json()["message"]


async def test_denying_needs_a_reason_and_sends_it_to_the_requester(
    client, sign_in, web, guild, wf
):
    requester = wf.member(guild, 21, name="ada")
    web.guard = wf.Guard()
    event_id = await an_event(web, wf)
    sign_in(client)

    empty = client.post(f"/api/events/{event_id}/deny", json={"reason": "  "})
    assert empty.status_code == 400 and empty.json()["error"] == "no_reason"

    response = client.post(f"/api/events/{event_id}/deny", json={"reason": "clashes"})

    assert response.json()["event"]["deny_reason"] == "clashes"
    assert requester.dms and "clashes" in requester.dms[0]
    assert "web.event.denied" in await wf.kinds_in(web.db)


async def test_cancelling_an_approved_event_says_so(client, sign_in, web, wf):
    web.guard = wf.Guard()
    event_id = await an_event(web, wf, status="approved")
    sign_in(client)

    response = client.post(f"/api/events/{event_id}/cancel", json={"reason": "weather"})

    assert response.status_code == 200
    assert response.json()["event"]["status"] == "cancelled"
    await wf.one_web_row(web.db, "web.event.cancelled")


async def test_cancelling_a_settled_event_is_refused_with_its_state(client, sign_in, web, wf):
    event_id = await an_event(web, wf, status="done")
    sign_in(client)

    response = client.post(f"/api/events/{event_id}/cancel", json={})

    assert response.status_code == 409
    assert "done" in response.json()["message"]


async def test_an_event_this_server_does_not_have_is_a_404(client, sign_in, web, wf):
    sign_in(client)
    for route in ("approve", "deny", "cancel"):
        response = client.post(f"/api/events/4242/{route}", json={"reason": "x"})
        assert response.status_code == 404
        assert "no event" in response.json()["message"]
    assert client.get("/api/events/4242").status_code == 404
    assert client.put("/api/events/4242", json={"title": "x"}).status_code == 404


async def test_the_detail_route_carries_the_fields_the_queue_row_does(client, sign_in, web, wf):
    event_id = await an_event(web, wf)
    sign_in(client)

    body = client.get(f"/api/events/{event_id}").json()["event"]

    assert body["description"] == "come along" and body["location"] == "the park"
    assert body["duration"] == "2h" and body["minutes"] == 120
    assert body["editable"] is True
    assert body["announced"] is False and body["scheduled"] is False


async def test_editing_rewrites_the_row_through_the_cogs_own_validation(
    client, sign_in, web, wf
):
    event_id = await an_event(web, wf)
    sign_in(client)

    response = client.put(
        f"/api/events/{event_id}",
        json={
            "title": "Bloc morning",
            "description": "earlier now",
            "location": "the other park",
            "start": a_start(),
            "duration": "1h30m",
            "tz": "UTC",
        },
    )

    assert response.status_code == 200
    body = response.json()["event"]
    assert body["title"] == "Bloc morning" and body["location"] == "the other park"
    assert body["minutes"] == 90 and body["duration"] == "1h 30m"
    row = await get_event(web.db, event_id)
    assert row["title"] == "Bloc morning"
    assert "web.event.edited" in await wf.kinds_in(web.db)


@pytest.mark.parametrize(
    ("body", "why"),
    [
        ({"title": "", "start": "2099-01-01 19:00"}, "an event needs a name"),
        ({"title": "x", "start": "next tuesday"}, "not a date black bloc can read"),
        ({"title": "x", "start": "2020-01-01 19:00"}, "has already gone by"),
        ({"title": "x", "start": "2099-01-01 19:00", "duration": "ages"}, "not a length"),
    ],
)
async def test_an_edit_the_validator_refuses_says_why_and_changes_nothing(
    client, sign_in, web, wf, body, why
):
    event_id = await an_event(web, wf)
    sign_in(client)

    response = client.put(f"/api/events/{event_id}", json={**body, "tz": "UTC"})

    assert response.status_code == 400
    assert response.json()["error"] == "event_refused"
    assert why in response.json()["message"].lower()
    assert (await get_event(web.db, event_id))["title"] == "Bloc night"


@pytest.mark.parametrize("status", ["denied", "cancelled", "done"])
async def test_a_settled_event_cannot_be_edited(client, sign_in, web, wf, status):
    event_id = await an_event(web, wf, status=status)
    sign_in(client)

    response = client.put(
        f"/api/events/{event_id}",
        json={"title": "x", "start": a_start(), "tz": "UTC"},
    )

    assert response.status_code == 409
    assert response.json()["error"] == "not_editable"
    assert status in response.json()["message"]


async def test_an_edited_approved_event_says_what_did_not_follow(client, sign_in, web, wf):
    event_id = await an_event(web, wf, status="approved")
    await web.db.conn.execute(
        "UPDATE events SET announce_message_id = ?, scheduled_event_id = ? WHERE id = ?",
        (555, 666, event_id),
    )
    await web.db.conn.commit()
    sign_in(client)

    notes = client.put(
        f"/api/events/{event_id}",
        json={"title": "Bloc morning", "start": a_start(), "tz": "UTC"},
    ).json()["notes"]

    assert len(notes) == 2
    assert any("announcement" in one for one in notes)
    assert any("scheduled event" in one for one in notes)


async def test_the_review_channel_is_renamed_to_follow_the_title(
    client, sign_in, web, guild, wf
):
    event_id = await an_event(web, wf)
    wf.member(guild, 21, name="ada")
    channel = guild.get_channel(wf.TEST_CHANNEL_ID)
    await web.db.conn.execute(
        "UPDATE events SET review_channel_id = ? WHERE id = ?", (channel.id, event_id)
    )
    await web.db.conn.commit()
    sign_in(client)

    client.put(
        f"/api/events/{event_id}",
        json={"title": "Bloc morning", "start": a_start(), "tz": "UTC"},
    )

    assert channel.name == "pending-ada-bloc-morning"
