from __future__ import annotations

import pytest

from black_bloc import questions_store as store

OPERATOR_TOKEN = "operator-read-token-long-enough-to-be-taken"
BEARER = {"Authorization": f"Bearer {OPERATOR_TOKEN}"}

ROUTES = [
    ("GET", "/api/questions", None),
    ("GET", "/api/questions/current", None),
    ("POST", "/api/questions", {"text": "one?"}),
    ("PUT", "/api/questions/1", {"body": "x"}),
    ("DELETE", "/api/questions/1", None),
    ("POST", "/api/questions/1/move", {"direction": "up"}),
    ("POST", "/api/questions/1/requeue", None),
    ("POST", "/api/questions/1/take-down", None),
    ("POST", "/api/questions/post-now", None),
    ("POST", "/api/questions/skip", None),
    ("POST", "/api/questions/unskip", None),
]


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_question_route_needs_a_session(client, method, route, payload):
    assert client.request(method, route, json=payload).status_code == 401


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_question_route_refuses_a_non_staff_visitor(client, sign_in, method, route, payload):
    sign_in(client, uid=1234, staff=False)
    assert client.request(method, route, json=payload).status_code == 403


async def test_a_pasted_list_queues_one_question_per_line_and_logs_once(client, sign_in, web, wf):
    sign_in(client)

    response = client.post("/api/questions", json={"text": "one?\n\n two? \nthree?"})

    assert response.status_code == 200
    assert response.json()["message"] == "3 question(s) added to the queue."
    found = client.get("/api/questions").json()
    assert [row["body"] for row in found["queue"]] == ["one?", "two?", "three?"]
    assert found["mode"] == "shadow" and found["state"] == "pending"
    assert found["owner_set"] is False and found["history"] == []
    kinds = await wf.kinds_in(web.db)
    assert kinds.count("web.question.added") == 1 and "question.added" not in kinds


def test_an_empty_paste_is_refused_in_words(client, sign_in):
    sign_in(client)

    response = client.post("/api/questions", json={"text": "  \n "})

    assert response.status_code == 400
    assert "one per line" in response.json()["message"]


async def test_move_edit_remove_and_put_back_from_the_page(client, sign_in, web, wf):
    sign_in(client)
    client.post("/api/questions", json={"text": "one?\ntwo?"})
    first, second = (row["id"] for row in client.get("/api/questions").json()["queue"])

    assert client.post(f"/api/questions/{second}/move", json={"direction": "up"}).status_code == 200
    assert client.put(f"/api/questions/{first}", json={"body": "one, edited?"}).status_code == 200
    assert client.delete(f"/api/questions/{second}").status_code == 200
    found = client.get("/api/questions").json()
    assert [row["body"] for row in found["queue"]] == ["one, edited?"]
    assert [row["status"] for row in found["history"]] == ["removed"]

    assert client.post(f"/api/questions/{second}/requeue").status_code == 200
    refused = client.post(f"/api/questions/{second}/requeue")
    assert refused.status_code == 409 and "removed" in refused.json()["message"]
    sideways = client.post(f"/api/questions/{first}/move", json={"direction": "left"})
    assert sideways.status_code == 400
    assert client.delete("/api/questions/999").status_code == 404


async def test_post_now_rehearses_then_take_it_down_puts_it_back_on_top(
    client, sign_in, web, guild, wf
):
    await web.store.set(wf.GUILD_ID, "shadow_channel_id", wf.OTHER_CHANNEL_ID)
    sign_in(client)
    client.post("/api/questions", json={"text": "one?\ntwo?"})

    posted = client.post("/api/questions/post-now")

    assert posted.status_code == 200, posted.json()
    channel = guild.get_channel(wf.OTHER_CHANNEL_ID)
    assert channel.messages[-1].content.endswith("one?")
    assert "out of cycle" in posted.json()["message"]
    found = client.get("/api/questions").json()
    assert found["state"] == "pending"
    [history] = found["history"]
    assert history["posted_by"] == "bot" and history["slot_at"] is None
    assert history["url"].startswith("https://discord.com/")
    current = client.get("/api/questions/current").json()
    assert current["state"] == "pending" and current["body"] == "two?"

    down = client.post(f"/api/questions/{history['id']}/take-down")

    assert down.status_code == 200, down.json()
    queue = client.get("/api/questions").json()["queue"]
    assert [row["body"] for row in queue] == ["one?", "two?"]
    kinds = await wf.kinds_in(web.db)
    assert "web.question.posted_extra" in kinds and "web.question.taken_down" in kinds


async def test_undo_skip_on_a_week_whose_time_has_passed_is_refused_in_words(
    client, sign_in, web, wf
):
    from datetime import UTC, datetime

    from black_bloc import questions as rules

    now = datetime.now(UTC)
    last, _ = rules.slots_around(now, rules.schedule_of(web.store, wf.GUILD_ID))
    await store.ensure_slot(web.db, wf.GUILD_ID, rules.slot_key(last), now)
    await store.set_slot(web.db, wf.GUILD_ID, rules.slot_key(last), rules.SKIPPED, now)
    sign_in(client)

    refused = client.post("/api/questions/unskip")

    assert refused.status_code == 409
    assert refused.json()["message"] == rules.SKIP_PASSED
    assert client.get("/api/questions").json()["slot_at"] != rules.slot_key(last)


async def test_skip_and_undo_from_the_page(client, sign_in, web, wf):
    sign_in(client)

    assert client.post("/api/questions/skip").status_code == 200
    assert client.get("/api/questions").json()["state"] == "skipped"
    assert client.post("/api/questions/skip").status_code == 409
    assert client.post("/api/questions/unskip").status_code == 200
    assert client.post("/api/questions/unskip").status_code == 409


async def test_the_operator_token_reads_this_weeks_question_and_where_to_post_it(client, web, wf):
    web.settings.operator_read_token = OPERATOR_TOKEN
    await web.store.set(wf.GUILD_ID, "shadow_channel_id", wf.OTHER_CHANNEL_ID)
    await web.store.set(wf.GUILD_ID, "question_template", "QOTW: {question}")
    from datetime import UTC, datetime

    await store.add_many(web.db, wf.GUILD_ID, ["one?"], None, datetime.now(UTC))

    found = client.get("/api/questions/current", headers=BEARER)

    assert found.status_code == 200
    body = found.json()
    assert set(body) >= {
        "slot_at",
        "question_id",
        "body",
        "rendered",
        "channel_id",
        "guild_id",
        "channel_url",
        "mode",
    }
    assert body["body"] == "one?" and body["rendered"] == "QOTW: one?"
    assert body["mode"] == "shadow" and body["channel_id"] == str(wf.OTHER_CHANNEL_ID)
    assert body["channel_url"] == (
        f"https://discord.com/channels/{wf.GUILD_ID}/{wf.OTHER_CHANNEL_ID}"
    )
    assert client.post("/api/questions/post-now", headers=BEARER).status_code == 403


async def test_an_empty_queue_or_off_hands_the_owner_nothing_to_post(client, sign_in, web, wf):
    sign_in(client)
    assert client.get("/api/questions/current").json()["body"] is None

    client.post("/api/questions", json={"text": "one?"})
    await web.store.set(wf.GUILD_ID, "question_mode", "off")
    found = client.get("/api/questions/current").json()
    assert found["body"] is None and found["channel_url"] is None and found["mode"] == "off"
