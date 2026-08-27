from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from black_bloc.cogs.community.events import create_event, get_event

ROUTES = [
    ("GET", "/api/events", None),
    ("POST", "/api/events/1/approve", None),
    ("POST", "/api/events/1/deny", {"reason": "no"}),
    ("POST", "/api/events/1/cancel", {}),
]


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
    kinds = await wf.kinds_in(web.db)
    assert "event.approved" in kinds and "web.event.approved" in kinds


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
    kinds = await wf.kinds_in(web.db)
    assert "event.cancelled" in kinds and "web.event.cancel" in kinds


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
