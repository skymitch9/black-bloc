from __future__ import annotations

import pytest

from black_bloc.cogs.moderation.modmail import (
    add_message,
    blocked_row,
    create_practice_ticket,
    create_ticket,
    get_snippet,
    get_ticket,
    set_ticket_place,
)
from black_bloc.modmail import IN, OPEN

ROUTES = [
    ("GET", "/api/modmail/tickets", None),
    ("GET", "/api/modmail/tickets/1", None),
    ("POST", "/api/modmail/tickets/1/reply", {"text": "hello"}),
    ("POST", "/api/modmail/tickets/1/close", {}),
    ("GET", "/api/modmail/snippets", None),
    ("POST", "/api/modmail/snippets", {"name": "hi", "content": "hello"}),
    ("DELETE", "/api/modmail/snippets/hi", None),
    ("GET", "/api/modmail/blocks", None),
    ("POST", "/api/modmail/blocks", {"user_id": "21"}),
    ("DELETE", "/api/modmail/blocks/21", None),
    ("POST", "/api/modmail/panel", {"channel_id": "1"}),
    ("DELETE", "/api/modmail/panel", None),
]


async def a_ticket(web, wf, *, user_id: int = 21, channel_id: int | None = None) -> int:
    ticket_id = await create_ticket(web.db, wf.GUILD_ID, user_id, "channel")
    await set_ticket_place(web.db, ticket_id, channel_id or wf.TEST_CHANNEL_ID, None)
    await add_message(web.db, ticket_id, user_id, IN, content="are you there?")
    return ticket_id


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_modmail_route_needs_a_session(client, method, route, payload):
    assert client.request(method, route, json=payload).status_code == 401


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_modmail_route_refuses_a_non_staff_visitor(
    client, sign_in, method, route, payload
):
    sign_in(client, uid=1234, staff=False)
    assert client.request(method, route, json=payload).status_code == 403


async def test_tickets_list_by_status_with_the_member_resolved(client, sign_in, web, guild, wf):
    wf.member(guild, 21, name="ada")
    await a_ticket(web, wf)
    sign_in(client)

    everything = client.get("/api/modmail/tickets").json()
    open_only = client.get("/api/modmail/tickets", params={"status": "open"}).json()
    closed = client.get("/api/modmail/tickets", params={"status": "closed"}).json()

    assert len(everything) == 1 and everything[0]["user_name"] == "Ada"
    assert everything[0]["status"] == OPEN
    assert everything[0]["practice"] is False
    assert len(open_only) == 1 and closed == []


async def test_a_practice_ticket_is_kept_off_the_list_but_readable_by_number(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    real = await a_ticket(web, wf)
    practice = await create_practice_ticket(web.db, wf.GUILD_ID, 22)
    sign_in(client)

    listed = client.get("/api/modmail/tickets").json()
    named = client.get(f"/api/modmail/tickets/{practice}").json()

    assert [row["id"] for row in listed] == [real]
    assert named["id"] == practice and named["practice"] is True
    assert client.get("/api/modmail/tickets", params={"status": "sideways"}).status_code == 400


async def test_one_ticket_comes_back_with_its_messages_in_order(client, sign_in, web, guild, wf):
    wf.member(guild, 21, name="ada")
    ticket_id = await a_ticket(web, wf)
    sign_in(client)

    body = client.get(f"/api/modmail/tickets/{ticket_id}").json()

    assert body["id"] == ticket_id
    assert [m["content"] for m in body["messages"]] == ["are you there?"]
    assert body["messages"][0]["direction"] == IN
    assert body["messages"][0]["author_name"] == "Ada"
    assert client.get("/api/modmail/tickets/4242").status_code == 404


async def test_a_reply_reaches_the_member_and_the_ticket(client, sign_in, web, guild, wf):
    member = wf.member(guild, 21, name="ada")
    ticket_id = await a_ticket(web, wf)
    sign_in(client)

    response = client.post(
        f"/api/modmail/tickets/{ticket_id}/reply", json={"text": "we are here", "anonymous": True}
    )

    assert response.status_code == 200 and response.json()["sent"] is True
    assert member.dms
    body = client.get(f"/api/modmail/tickets/{ticket_id}").json()
    assert body["messages"][-1]["content"] == "we are here"
    assert body["messages"][-1]["anonymous"] is True
    assert "web.modmail.reply" in await wf.kinds_in(web.db)


async def test_an_empty_reply_and_a_closed_ticket_are_both_refused(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    ticket_id = await a_ticket(web, wf)
    sign_in(client)

    empty = client.post(f"/api/modmail/tickets/{ticket_id}/reply", json={"text": "   "})
    assert empty.status_code == 400 and empty.json()["error"] == "nothing_to_send"

    client.post(f"/api/modmail/tickets/{ticket_id}/close", json={})
    after = client.post(f"/api/modmail/tickets/{ticket_id}/reply", json={"text": "hello?"})
    assert after.status_code == 409 and after.json()["error"] == "ticket_closed"


async def test_closing_files_the_transcript_and_tells_the_member(
    client, sign_in, web, guild, wf
):
    member = wf.member(guild, 21, name="ada")
    await web.store.set(wf.GUILD_ID, "modmail_log_channel_id", wf.TEST_CHANNEL_ID)
    ticket_id = await a_ticket(web, wf, channel_id=wf.OTHER_CHANNEL_ID)
    sign_in(client)

    response = client.post(
        f"/api/modmail/tickets/{ticket_id}/close", json={"reason": "answered"}
    )

    assert response.status_code == 200
    assert response.json()["closed"] is True and response.json()["transcript"] is True
    assert (await get_ticket(web.db, ticket_id))["status"] == "closed"
    assert member.dms and "answered" in member.dms[-1]
    kinds = [kind for kind, _ in await wf.web_rows_in(web.db)]
    assert kinds == ["web.modmail.closed"], kinds


async def test_a_silent_close_tells_nobody(client, sign_in, web, guild, wf):
    member = wf.member(guild, 21, name="ada")
    ticket_id = await a_ticket(web, wf)
    sign_in(client)

    client.post(f"/api/modmail/tickets/{ticket_id}/close", json={"silent": True})

    assert member.dms == []
    assert (await get_ticket(web.db, ticket_id))["status"] == "closed"


async def test_closing_a_ticket_whose_channel_would_be_deleted_is_409_in_test_mode(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    ticket_id = await a_ticket(web, wf, channel_id=wf.OTHER_CHANNEL_ID)
    web.guard = wf.Guard()
    sign_in(client)

    response = client.post(f"/api/modmail/tickets/{ticket_id}/close", json={})

    assert response.status_code == 409
    assert response.json()["error"] == "test_mode"
    assert "test mode" in response.json()["message"]
    assert (await get_ticket(web.db, ticket_id))["status"] == OPEN
    assert guild.get_channel(wf.OTHER_CHANNEL_ID).deleted is False


async def test_a_ticket_in_the_test_category_still_closes_under_the_guard(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    ticket_id = await a_ticket(web, wf, channel_id=wf.TEST_CHANNEL_ID)
    web.guard = wf.Guard()
    sign_in(client)

    response = client.post(f"/api/modmail/tickets/{ticket_id}/close", json={})

    assert response.status_code == 200
    assert (await get_ticket(web.db, ticket_id))["status"] == "closed"


async def test_snippets_are_saved_listed_and_removed(client, sign_in, web, wf):
    sign_in(client, uid=7)

    saved = client.post("/api/modmail/snippets", json={"name": "Hi", "content": "Hello there"})

    assert saved.json() == {"saved": True, "name": "hi", "content": "Hello there"}
    assert (await get_snippet(web.db, "hi"))["content"] == "Hello there"
    assert [row["name"] for row in client.get("/api/modmail/snippets").json()] == ["hi"]

    removed = client.delete("/api/modmail/snippets/hi")
    assert removed.json() == {"removed": True, "name": "hi"}
    assert await get_snippet(web.db, "hi") is None
    assert client.delete("/api/modmail/snippets/hi").status_code == 404
    assert "web.modmail.snippet_saved" in await wf.kinds_in(web.db)


def test_a_snippet_needs_a_name_and_content(client, sign_in):
    sign_in(client)
    assert client.post("/api/modmail/snippets", json={"name": "hi"}).status_code == 400
    assert client.post("/api/modmail/snippets", json={"content": "x"}).status_code == 400


async def test_blocks_are_added_listed_and_lifted(client, sign_in, web, guild, wf):
    wf.member(guild, 21, name="ada")
    sign_in(client, uid=7)

    client.post("/api/modmail/blocks", json={"user_id": "21", "reason": "abuse"})

    rows = client.get("/api/modmail/blocks").json()
    assert rows[0]["user_id"] == "21" and rows[0]["reason"] == "abuse"
    assert rows[0]["user_name"] == "Ada" and rows[0]["by_id"] == "7"
    assert await blocked_row(web.db, 21) is not None

    assert client.delete("/api/modmail/blocks/21").json()["unblocked"] is True
    assert await blocked_row(web.db, 21) is None
    kinds = await wf.kinds_in(web.db)
    assert "web.modmail.blocked" in kinds and "web.modmail.unblocked" in kinds


def test_a_block_needs_a_real_id(client, sign_in):
    sign_in(client)
    assert client.post("/api/modmail/blocks", json={"user_id": "nobody"}).status_code == 400
    assert client.delete("/api/modmail/blocks/nobody").status_code == 400


async def test_the_ticket_button_is_posted_and_taken_down_from_the_website(
    client, sign_in, web, guild, wf
):
    sign_in(client, uid=7)

    posted = client.post("/api/modmail/panel", json={"channel_id": str(wf.TEST_CHANNEL_ID)})

    assert posted.status_code == 200 and posted.json()["posted"] is True
    assert posted.json()["channel_id"] == str(wf.TEST_CHANNEL_ID)
    assert web.store.get(wf.GUILD_ID, "modmail_panel_channel_id") == wf.TEST_CHANNEL_ID
    channel = guild.get_channel(wf.TEST_CHANNEL_ID)
    assert channel.messages[-1].kwargs["embed"].title == "Need a moderator?"

    down = client.delete("/api/modmail/panel")

    assert down.status_code == 200 and down.json()["taken_down"] is True
    assert web.store.get(wf.GUILD_ID, "modmail_panel_channel_id") is None
    assert web.store.get(wf.GUILD_ID, "modmail_panel_message_id") is None
    kinds = await wf.kinds_in(web.db)
    assert "web.modmail.panel_posted" in kinds
    assert "web.modmail.panel_taken_down" in kinds
    assert "modmail.panel_posted" not in kinds


async def test_posting_the_ticket_button_twice_moves_it_and_leaves_one_row_each_time(
    client, sign_in, web, guild, wf
):
    sign_in(client, uid=7)

    client.post("/api/modmail/panel", json={"channel_id": str(wf.TEST_CHANNEL_ID)})
    again = client.post("/api/modmail/panel", json={"channel_id": str(wf.TEST_CHANNEL_ID)})

    assert again.status_code == 200
    kinds = await wf.kinds_in(web.db)
    assert "web.modmail.panel_moved" in kinds


def test_a_ticket_button_needs_a_channel_the_bot_can_see(client, sign_in):
    sign_in(client)

    assert client.post("/api/modmail/panel", json={}).status_code == 400
    assert (
        client.post("/api/modmail/panel", json={"channel_id": "404"}).json()["error"]
        == "no_such_channel"
    )


async def test_the_ticket_button_is_refused_outside_the_test_channel_in_test_mode(
    client, sign_in, web, guild, wf
):
    web.guard = wf.Guard()
    sign_in(client)

    refused = client.post("/api/modmail/panel", json={"channel_id": str(wf.OTHER_CHANNEL_ID)})

    assert refused.status_code == 409 and refused.json()["error"] == "test_mode"
    assert "test mode" in refused.json()["message"]
    assert web.store.get(wf.GUILD_ID, "modmail_panel_channel_id") is None
    assert guild.get_channel(wf.OTHER_CHANNEL_ID).messages == []


def test_taking_down_a_button_that_is_not_up_says_so_rather_than_pretending(
    client, sign_in
):
    sign_in(client)

    said = client.delete("/api/modmail/panel")

    assert said.status_code == 200
    assert said.json()["taken_down"] is False
    assert "no **Open a ticket** button" in said.json()["message"]


async def test_a_ticket_says_which_door_it_came_in_by(client, sign_in, web, guild, wf):
    wf.member(guild, 21, name="ada")
    ticket_id = await a_ticket(web, wf)
    sign_in(client)

    row = client.get(f"/api/modmail/tickets/{ticket_id}").json()

    assert row["source"] == "dm" and row["opened_by_id"] is None
