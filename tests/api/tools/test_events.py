from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from black_bloc.events import (
    WHERE_OTHER,
    WHERE_TEXT,
    WHERE_UNSET,
    WHERE_VOICE,
    Where,
    create_event,
    get_event,
)

ROUTES = [
    ("GET", "/api/events", None),
    ("GET", "/api/events/1", None),
    ("PUT", "/api/events/1", {"title": "x", "start": "2099-01-01 19:00"}),
    ("POST", "/api/events/1/approve", None),
    ("POST", "/api/events/1/deny", {"reason": "no"}),
    ("POST", "/api/events/1/cancel", {}),
    ("POST", "/api/events/1/room/delete", {}),
]


def a_start(days: int = 3) -> str:
    """A `YYYY-MM-DD HH:MM` the validator will accept, read in the zone the body names."""
    return (datetime.now(UTC) + timedelta(days=days)).strftime("%Y-%m-%d %H:%M")


async def an_event(
    web, wf, *, status: str = "pending", requester: int = 21, where: Where | None = None
) -> int:
    where = Where(WHERE_OTHER, None, "the park") if where is None else where
    starts = datetime.now(UTC) + timedelta(days=1)
    event_id = await create_event(
        web.db,
        wf.GUILD_ID,
        requester,
        title="Bloc night",
        description="come along",
        where=where,
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


# The "Where?" picker's website door (`docs/info/where-picker-design.md` §5): three fields on
# every row, the same three kinds, and a sentence for anything the guild cannot make sense of.


async def test_a_row_carries_the_kind_the_channel_and_a_label_the_page_need_not_resolve(
    client, sign_in, web, wf
):
    typed = await an_event(web, wf)
    voiced = await an_event(web, wf, where=Where(WHERE_VOICE, wf.VOICE_CHANNEL_ID, ""))
    nowhere = await an_event(web, wf, where=WHERE_UNSET)
    sign_in(client)

    rows = {row["id"]: row for row in client.get("/api/events").json()}

    assert rows[typed]["where_kind"] == WHERE_OTHER
    assert rows[typed]["where_channel_id"] is None
    assert rows[typed]["where_label"] == "the park"
    assert rows[voiced]["where_kind"] == WHERE_VOICE
    assert rows[voiced]["where_channel_id"] == str(wf.VOICE_CHANNEL_ID)
    assert rows[voiced]["where_label"] == "🔊 voice"
    assert rows[nowhere]["where_kind"] is None
    assert rows[nowhere]["where_label"] == ""


async def test_the_detail_route_carries_the_where_fields_the_queue_row_does(
    client, sign_in, web, wf
):
    event_id = await an_event(web, wf, where=Where(WHERE_TEXT, wf.OTHER_CHANNEL_ID, ""))
    sign_in(client)

    body = client.get(f"/api/events/{event_id}").json()["event"]

    assert body["where_kind"] == WHERE_TEXT
    assert body["where_channel_id"] == str(wf.OTHER_CHANNEL_ID)
    assert body["where_label"] == "#general"


async def test_editing_can_set_each_of_the_three_kinds(client, sign_in, web, wf):
    event_id = await an_event(web, wf)
    sign_in(client)

    def save(**where):
        return client.put(
            f"/api/events/{event_id}",
            json={
                "title": "Bloc night",
                "description": "come along",
                "start": a_start(),
                "duration": "2h",
                "tz": "UTC",
                **where,
            },
        )

    voiced = save(where_kind=WHERE_VOICE, where_channel_id=str(wf.VOICE_CHANNEL_ID))
    assert voiced.status_code == 200
    assert voiced.json()["event"]["where_kind"] == WHERE_VOICE
    row = await get_event(web.db, event_id)
    assert row["where_channel_id"] == wf.VOICE_CHANNEL_ID and row["location"] is None

    texted = save(where_kind=WHERE_TEXT, where_channel_id=str(wf.OTHER_CHANNEL_ID))
    assert texted.json()["event"]["where_label"] == "#general"

    typed = save(where_kind=WHERE_OTHER, location="twitch.tv/blackbloc")
    assert typed.json()["event"]["where_label"] == "twitch.tv/blackbloc"
    row = await get_event(web.db, event_id)
    assert row["where_channel_id"] is None and row["location"] == "twitch.tv/blackbloc"

    cleared = save(where_kind=None, location="")
    assert cleared.json()["event"]["where_kind"] is None
    row = await get_event(web.db, event_id)
    assert row["where_kind"] is None and row["location"] is None


async def test_editing_can_set_a_channel_and_a_link_at_the_same_time(client, sign_in, web, wf):
    """The follow-up: the box is optional beside a channel, not instead of one."""
    event_id = await an_event(web, wf)
    sign_in(client)

    answer = client.put(
        f"/api/events/{event_id}",
        json={
            "title": "Bloc night",
            "description": "come along",
            "start": a_start(),
            "duration": "2h",
            "tz": "UTC",
            "where_kind": WHERE_VOICE,
            "where_channel_id": str(wf.VOICE_CHANNEL_ID),
            "location": "twitch.tv/blackbloc",
        },
    )

    body = answer.json()["event"]
    assert answer.status_code == 200
    assert body["where_kind"] == WHERE_VOICE
    assert body["where_channel_id"] == str(wf.VOICE_CHANNEL_ID)
    assert body["location"] == "twitch.tv/blackbloc"
    assert body["where_label"] == "🔊 voice · twitch.tv/blackbloc"
    row = await get_event(web.db, event_id)
    assert row["where_channel_id"] == wf.VOICE_CHANNEL_ID
    assert row["location"] == "twitch.tv/blackbloc"


async def test_a_text_channel_sent_as_voice_is_stored_as_what_it_actually_is(
    client, sign_in, web, wf
):
    event_id = await an_event(web, wf)
    sign_in(client)

    answer = client.put(
        f"/api/events/{event_id}",
        json={
            "title": "Bloc night",
            "start": a_start(),
            "duration": "2h",
            "tz": "UTC",
            "where_kind": WHERE_VOICE,
            "where_channel_id": str(wf.OTHER_CHANNEL_ID),
        },
    )

    assert answer.json()["event"]["where_kind"] == WHERE_TEXT


@pytest.mark.parametrize(
    ("where", "why"),
    [
        ({"where_kind": "nowhere"}, "not a kind of place"),
        ({"where_kind": "voice"}, "has to be picked"),
        ({"where_kind": "voice", "where_channel_id": "4242"}, "cannot find channel"),
        ({"where_kind": "text", "where_channel_id": "490"}, "not somewhere an event can happen"),
    ],
)
async def test_a_where_the_guild_cannot_make_sense_of_is_refused_in_words(
    client, sign_in, web, wf, where, why
):
    event_id = await an_event(web, wf)
    sign_in(client)

    answer = client.put(
        f"/api/events/{event_id}",
        json={
            "title": "Bloc night",
            "start": a_start(),
            "duration": "2h",
            "tz": "UTC",
            **where,
        },
    )

    assert answer.status_code == 400
    said = answer.json()["message"]
    assert why in said and len(said.split()) > 8
    assert (await get_event(web.db, event_id))["location"] == "the park"


# Event rooms (`docs/info/events-rooms-design.md` §2D): the website's Remove-its-room button
# runs the one `delete_room` the button in Discord runs, and leaves ONE action row with a
# `web.` head (checklist 34).


async def a_room(web, wf, guild, event_id: int) -> object:
    channel = guild.get_channel(wf.OTHER_CHANNEL_ID)
    await web.db.conn.execute(
        "UPDATE events SET review_channel_id = ? WHERE id = ?", (channel.id, event_id)
    )
    await web.db.conn.commit()
    return channel


async def test_removing_a_room_from_the_site_deletes_it_and_calls_the_event_off(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    event_id = await an_event(web, wf)
    channel = await a_room(web, wf, guild, event_id)
    sign_in(client)

    answer = client.post(f"/api/events/{event_id}/room/delete", json={"note": "we need it back"})

    assert answer.status_code == 200
    assert channel.deleted is True
    assert "is cancelled" in answer.json()["message"]
    fresh = await get_event(web.db, event_id)
    assert fresh["status"] == "cancelled" and fresh["review_channel_id"] is None


async def test_removing_a_finished_events_room_leaves_the_status_alone(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    event_id = await an_event(web, wf, status="done")
    channel = await a_room(web, wf, guild, event_id)
    sign_in(client)

    answer = client.post(f"/api/events/{event_id}/room/delete", json={})

    assert answer.status_code == 200
    assert channel.deleted is True
    assert "is cancelled" not in answer.json()["message"]
    assert (await get_event(web.db, event_id))["status"] == "done"


async def test_an_event_with_no_room_is_refused_in_words_not_a_bare_status(
    client, sign_in, web, wf
):
    event_id = await an_event(web, wf)
    sign_in(client)

    answer = client.post(f"/api/events/{event_id}/room/delete", json={})

    assert answer.status_code == 409
    said = answer.json()["message"]
    assert "nothing to remove" in said and len(said.split()) > 8


async def test_one_web_write_leaves_one_action_row_with_the_web_head(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    event_id = await an_event(web, wf, status="done")
    await a_room(web, wf, guild, event_id)
    sign_in(client)

    client.post(f"/api/events/{event_id}/room/delete", json={})

    cur = await web.db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    kinds = [row["kind"] for row in await cur.fetchall()]
    assert kinds.count("web.event.channel_deleted") == 1
    assert "event.channel_deleted" not in kinds
