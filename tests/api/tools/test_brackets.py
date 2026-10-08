from __future__ import annotations

import asyncio

import httpx
import pytest

STAFFER = 7
TO = 8
ADA = 21
BEA = 22
NOBODY = 30
TO_ROLE = 555

ROUTES = [
    ("GET", "/api/brackets", None),
    ("GET", "/api/brackets/1", None),
    ("POST", "/api/brackets", {"name": "x"}),
    ("PATCH", "/api/brackets/1", {"name": "y"}),
    ("POST", "/api/brackets/1/signups/open", {}),
    ("POST", "/api/brackets/1/join", {}),
    ("POST", "/api/brackets/1/sets/W1-1/report", {"score_a": 2, "score_b": 0}),
]


@pytest.fixture
async def people(guild, wf, web):
    from tests.api.conftest import WebRole

    guild.roles.append(WebRole(TO_ROLE, "Tournament Organiser"))
    wf.member(guild, STAFFER, name="sky", staff=True)
    organiser = wf.member(guild, TO, name="tess")
    organiser.roles.append(guild.get_role(TO_ROLE))
    wf.member(guild, ADA, name="ada")
    wf.member(guild, BEA, name="bea")
    wf.member(guild, NOBODY, name="sam")
    await web.store.set(wf.GUILD_ID, "brackets_to_role_id", TO_ROLE)


def as_(client, sign_in, wf, uid):
    client.cookies.clear()
    sign_in(client, uid=uid, staff=uid == STAFFER)
    client.headers.update(wf.SAME_SITE)
    return client


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_route_needs_a_session(client, method, route, payload):
    response = client.request(method, route, json=payload)
    assert response.status_code == 401
    assert response.json()["message"]


def made(client, **given):
    response = client.post("/api/brackets", json={"name": "Knuck Up 12", **given})
    assert response.status_code == 200, response.text
    return response.json()["tournament"]


async def test_a_member_reads_the_list_and_a_tournament_but_cannot_create(
    client, sign_in, wf, people
):
    organiser = as_(client, sign_in, wf, TO)
    tid = made(organiser, format="single")["id"]

    member = as_(client, sign_in, wf, ADA)
    listed = member.get("/api/brackets").json()
    assert (listed["mode"], listed["may_run"]) == ("shadow", False)
    assert [row["id"] for row in listed["tournaments"]] == [tid]
    one = member.get(f"/api/brackets/{tid}").json()
    assert (one["name"], one["state"], one["may_run"], one["mine"]) == (
        "Knuck Up 12",
        "draft",
        False,
        None,
    )
    refused = member.post("/api/brackets", json={"name": "mine"})
    assert refused.status_code == 403
    assert refused.json()["error"] == "not_organiser"
    assert "**Tournament Organiser**" in refused.json()["message"]


async def test_a_whole_single_elimination_through_the_website(client, sign_in, wf, web, people):
    organiser = as_(client, sign_in, wf, TO)
    tid = made(organiser, format="single", best_of_finals=3)["id"]
    opened = organiser.post(f"/api/brackets/{tid}/signups/open", json={})
    assert opened.json()["message"] == "Sign-ups for **Knuck Up 12** are open."

    for player in (ADA, BEA):
        joined = as_(client, sign_in, wf, player).post(f"/api/brackets/{tid}/join", json={})
        assert joined.json()["message"] == "You are in **Knuck Up 12**."

    organiser = as_(client, sign_in, wf, TO)
    guest = organiser.post(f"/api/brackets/{tid}/entrants", json={"name": "Remy"}).json()
    remy = next(one["id"] for one in guest["tournament"]["entrants"] if one["guest"])
    removed = organiser.delete(f"/api/brackets/{tid}/entrants/{remy}")
    assert removed.json()["message"] == "Remy is out of **Knuck Up 12**."
    organiser.post(f"/api/brackets/{tid}/signups/close", json={})
    started = organiser.post(f"/api/brackets/{tid}/start", json={}).json()
    assert started["message"] == "**Knuck Up 12** has started — 1 set(s) to play."
    (only,) = started["tournament"]["sets"]
    assert (only["a_name"], only["b_name"], only["state"]) == ("Ada", "Bea", "ready")

    ada = as_(client, sign_in, wf, ADA)
    bad = ada.post(f"/api/brackets/{tid}/sets/W1-1/report", json={"score_a": 3, "score_b": 0})
    assert (bad.status_code, bad.json()["error"]) == (400, "bad_score")
    reported = ada.post(f"/api/brackets/{tid}/sets/W1-1/report", json={"score_a": 2, "score_b": 1})
    assert reported.json()["message"] == (
        "W1-1 reported 2–1. It stands in 12 minute(s) unless Bea disputes it."
    )
    mine = reported.json()["tournament"]
    assert mine["waiting_on"][0]["what"] == "opponent_confirms"

    bea = as_(client, sign_in, wf, BEA)
    final = bea.post(f"/api/brackets/{tid}/sets/W1-1/confirm", json={})
    assert final.json()["message"] == "W1-1 is final: Ada wins 2–1."

    organiser = as_(client, sign_in, wf, TO)
    done = organiser.post(f"/api/brackets/{tid}/complete", json={}).json()
    assert {one["name"]: one["placement"] for one in done["tournament"]["entrants"]} == {
        "Ada": 1,
        "Bea": 2,
        "Remy": None,
    }

    kinds = [kind for kind in await wf.kinds_in(web.db) if "brackets" in kind]
    assert kinds == [
        "web.brackets.created",
        "web.brackets.signups_opened",
        "web.brackets.entrant_added",
        "web.brackets.entrant_added",
        "web.brackets.entrant_added",
        "web.brackets.entrant_removed",
        "web.brackets.signups_closed",
        "web.brackets.started",
        "web.brackets.set_reported",
        "web.brackets.set_confirmed",
        "web.brackets.completed",
    ]


async def test_a_member_outside_the_set_is_refused_in_words(client, sign_in, wf, people):
    organiser = as_(client, sign_in, wf, TO)
    tid = made(organiser)["id"]
    organiser.post(f"/api/brackets/{tid}/signups/open", json={})
    for player in (ADA, BEA):
        as_(client, sign_in, wf, player).post(f"/api/brackets/{tid}/join", json={})
    organiser = as_(client, sign_in, wf, STAFFER)
    organiser.post(f"/api/brackets/{tid}/start", json={})
    stranger = as_(client, sign_in, wf, NOBODY)
    refused = stranger.post(
        f"/api/brackets/{tid}/sets/W1-1/report", json={"score_a": 2, "score_b": 0}
    )
    assert refused.status_code == 403
    assert refused.json() == {
        "error": "not_in_set",
        "message": "You are not playing in W1-1, so nothing was done. Its two players and "
        "tournament organisers can report it.",
    }


async def test_an_unknown_tournament_and_a_bad_id_answer_in_words(client, sign_in, wf, people):
    member = as_(client, sign_in, wf, ADA)
    missing = member.get("/api/brackets/999")
    assert missing.status_code == 404
    assert missing.json()["message"] == "There is no tournament 999 here, so nothing was done."
    bad = member.get("/api/brackets/abc")
    assert bad.status_code == 400 and "Copy ID" in bad.json()["message"]


async def test_staff_override_a_finished_set_and_take_it_back(client, sign_in, wf, people):
    staff = as_(client, sign_in, wf, STAFFER)
    tid = made(staff, format="single", best_of_finals=3)["id"]
    for name in ("P1", "P2"):
        staff.post(f"/api/brackets/{tid}/entrants", json={"name": name})
    staff.post(f"/api/brackets/{tid}/start", json={})
    decided = staff.post(
        f"/api/brackets/{tid}/sets/W1-1/override", json={"score_a": 0, "score_b": 2}
    )
    assert decided.json()["message"] == "W1-1 is final: P2 wins 2–0."
    reset = staff.post(f"/api/brackets/{tid}/sets/W1-1/reset", json={})
    assert reset.json()["tournament"]["sets"][0]["state"] == "ready"
    forfeit = staff.post(
        f"/api/brackets/{tid}/sets/W1-1/override", json={"winner": "a", "forfeit": True}
    )
    assert forfeit.json()["message"] == "W1-1 is final: P1 wins by forfeit."


async def test_a_differing_second_report_is_refused_with_the_score_already_reported(
    client, sign_in, wf, people
):
    organiser = as_(client, sign_in, wf, TO)
    tid = made(organiser, format="single", best_of_finals=3)["id"]
    organiser.post(f"/api/brackets/{tid}/signups/open", json={})
    for player in (ADA, BEA):
        as_(client, sign_in, wf, player).post(f"/api/brackets/{tid}/join", json={})
    as_(client, sign_in, wf, TO).post(f"/api/brackets/{tid}/start", json={})
    ada = as_(client, sign_in, wf, ADA)
    ada.post(f"/api/brackets/{tid}/sets/W1-1/report", json={"score_a": 2, "score_b": 1})
    bea = as_(client, sign_in, wf, BEA)
    differs = bea.post(f"/api/brackets/{tid}/sets/W1-1/report", json={"score_a": 1, "score_b": 2})
    assert differs.status_code == 409
    assert differs.json() == {
        "error": "reported_differently",
        "message": "W1-1 was reported 2–1. Confirm that, or dispute it.",
    }
    view = bea.get(f"/api/brackets/{tid}").json()
    (only,) = view["sets"]
    assert (only["state"], only["score_a"], only["score_b"]) == ("reported", 2, 1)


async def test_every_website_write_lets_the_thread_catch_up_and_a_refusal_does_not(
    client, sign_in, wf, people, monkeypatch
):
    from black_bloc import brackets_thread

    followed = []

    async def follow(bot, guild, tournament_id, outcome, *, move=None):
        followed.append((tournament_id, move, outcome.ok))

    monkeypatch.setattr(brackets_thread, "follow", follow)
    organiser = as_(client, sign_in, wf, TO)
    tid = made(organiser)["id"]
    organiser.post(f"/api/brackets/{tid}/signups/open", json={})
    refused = as_(client, sign_in, wf, ADA).post(f"/api/brackets/{tid}/start", json={})

    assert refused.status_code == 403
    assert followed == [(tid, "create", True), (tid, "open_signups", True)]


async def test_a_website_write_answers_before_the_thread_catches_up(
    client, sign_in, wf, web, people, monkeypatch
):
    from black_bloc import brackets_thread

    gate = asyncio.Event()
    caught_up = []

    async def follow(bot, guild, tournament_id, outcome, *, move=None):
        await gate.wait()
        caught_up.append(move)

    monkeypatch.setattr(brackets_thread, "follow", follow)
    organiser = as_(client, sign_in, wf, TO)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=organiser.app),
        base_url=str(organiser.base_url),
        cookies=dict(organiser.cookies.items()),
        headers=dict(organiser.headers),
    ) as fast:
        answered = await asyncio.wait_for(fast.post("/api/brackets", json={"name": "X"}), 5)

    assert answered.status_code == 200 and caught_up == []
    gate.set()
    await asyncio.gather(*brackets_thread.following(web))
    assert caught_up == ["create"]


async def test_a_follow_that_fails_never_reaches_the_request(
    client, sign_in, wf, web, people, monkeypatch
):
    from black_bloc import brackets_thread

    async def broken(*args, **kwargs):
        raise RuntimeError("discord is down")

    monkeypatch.setattr(brackets_thread, "sync", broken)
    organiser = as_(client, sign_in, wf, TO)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=organiser.app),
        base_url=str(organiser.base_url),
        cookies=dict(organiser.cookies.items()),
        headers=dict(organiser.headers),
    ) as fast:
        answered = await fast.post("/api/brackets", json={"name": "X"})
    await asyncio.gather(*brackets_thread.following(web))

    assert answered.status_code == 200


async def test_the_move_into_knuck_up_is_staff_only_and_refused_in_words_while_shadow(
    client, sign_in, wf, people
):
    organiser = as_(client, sign_in, wf, TO)
    tid = made(organiser)["id"]

    refused = organiser.post(f"/api/brackets/{tid}/move", json={})
    assert refused.status_code == 403 and "staff" in refused.json()["message"]

    shadowed = as_(client, sign_in, wf, STAFFER).post(f"/api/brackets/{tid}/move", json={})
    assert shadowed.status_code == 409
    assert shadowed.json()["error"] == "not_on"
    assert "brackets_mode is shadow" in shadowed.json()["message"]


async def told(web, kind="brackets.would_dm"):
    import json

    cur = await web.db.conn.execute(
        "SELECT target_id, details FROM action_log WHERE kind = ? ORDER BY id", (kind,)
    )
    return [(row[0], json.loads(row[1])) for row in await cur.fetchall()]


async def test_the_list_carries_the_page_words_the_cap_and_the_organisers_name(
    client, sign_in, wf, web, people
):
    organiser = as_(client, sign_in, wf, TO)
    tid = made(organiser, format="single", entrant_cap=8)["id"]
    await web.store.set(wf.GUILD_ID, "brackets_waiting_play", "Go play {opponent}")
    listed = as_(client, sign_in, wf, ADA).get("/api/brackets").json()
    (row,) = listed["tournaments"]
    assert (row["id"], row["entrant_cap"], row["to_name"]) == (tid, 8, "Tess")
    assert listed["words"]["brackets_waiting_play"] == "Go play {opponent}"
    assert listed["words"]["brackets_sign_up_label"] == "Sign up"
    one = as_(client, sign_in, wf, ADA).get(f"/api/brackets/{tid}").json()
    assert (one["to_name"], one["shadow"]) == ("Tess", False)


async def test_a_dq_and_a_drop_from_the_site_tell_the_player_with_the_reason(
    client, sign_in, wf, web, people
):
    organiser = as_(client, sign_in, wf, TO)
    tid = made(organiser, format="single", best_of_finals=3)["id"]
    organiser.post(f"/api/brackets/{tid}/signups/open", json={})
    for player in (ADA, BEA, NOBODY):
        as_(client, sign_in, wf, player).post(f"/api/brackets/{tid}/join", json={})
    organiser = as_(client, sign_in, wf, TO)
    started = organiser.post(f"/api/brackets/{tid}/start", json={}).json()["tournament"]
    ids = {one["name"]: one["id"] for one in started["entrants"]}
    dq = organiser.post(
        f"/api/brackets/{tid}/entrants/{ids['Ada']}/dq", json={"reason": "  no   show "}
    )
    assert dq.status_code == 200, dq.text
    organiser.post(f"/api/brackets/{tid}/entrants/{ids['Bea']}/drop", json={})
    rows = await told(web)
    assert [(target, details["dm"], details["reason"]) for target, details in rows] == [
        (ADA, "brackets_dm_dq", "no show"),
        (BEA, "brackets_dm_dropped", ""),
    ]
    assert rows[0][1]["text"].endswith("Reason: no show")


async def test_a_player_dropping_themselves_is_not_told(client, sign_in, wf, web, people):
    organiser = as_(client, sign_in, wf, TO)
    tid = made(organiser)["id"]
    organiser.post(f"/api/brackets/{tid}/signups/open", json={})
    ada = as_(client, sign_in, wf, ADA)
    mine = ada.post(f"/api/brackets/{tid}/join", json={}).json()["tournament"]["mine"]
    left = ada.post(f"/api/brackets/{tid}/entrants/{mine}/drop", json={"reason": "busy"})
    assert left.status_code == 200, left.text
    assert await told(web) == []


async def test_a_removal_from_the_site_tells_the_member_and_never_a_guest(
    client, sign_in, wf, web, people
):
    organiser = as_(client, sign_in, wf, TO)
    tid = made(organiser)["id"]
    organiser.post(f"/api/brackets/{tid}/signups/open", json={})
    as_(client, sign_in, wf, ADA).post(f"/api/brackets/{tid}/join", json={})
    organiser = as_(client, sign_in, wf, TO)
    view = organiser.post(f"/api/brackets/{tid}/entrants", json={"name": "Remy"}).json()
    ids = {one["name"]: one["id"] for one in view["tournament"]["entrants"]}
    for name in ("Ada", "Remy"):
        gone = organiser.request(
            "DELETE", f"/api/brackets/{tid}/entrants/{ids[name]}", json={"reason": "late"}
        )
        assert gone.status_code == 200, gone.text
    assert [(target, details["dm"]) for target, details in await told(web)] == [
        (ADA, "brackets_dm_removed")
    ]


async def test_a_decision_and_a_reset_from_the_site_tell_both_players(
    client, sign_in, wf, web, people
):
    organiser = as_(client, sign_in, wf, TO)
    tid = made(organiser, format="single", best_of_finals=3)["id"]
    organiser.post(f"/api/brackets/{tid}/signups/open", json={})
    for player in (ADA, BEA):
        as_(client, sign_in, wf, player).post(f"/api/brackets/{tid}/join", json={})
    organiser = as_(client, sign_in, wf, TO)
    organiser.post(f"/api/brackets/{tid}/start", json={})
    decided = organiser.post(
        f"/api/brackets/{tid}/sets/W1-1/override",
        json={"score_a": 2, "score_b": 0, "reason": "stream VOD"},
    )
    assert decided.status_code == 200, decided.text
    organiser.post(f"/api/brackets/{tid}/sets/W1-1/reset", json={"reason": "replay"})
    refused = organiser.post(f"/api/brackets/{tid}/sets/W1-1/reset", json={"reason": "again"})
    assert refused.status_code == 409
    found = [
        (target, details["dm"], details["reason"]) for target, details in await told(web)
    ]
    assert found == [
        (ADA, "brackets_dm_decided", "stream VOD"),
        (BEA, "brackets_dm_decided", "stream VOD"),
        (ADA, "brackets_dm_reset", "replay"),
        (BEA, "brackets_dm_reset", "replay"),
    ]
    assert "W1-1 is final: Ada wins 2–0." in (await told(web))[0][1]["text"]
