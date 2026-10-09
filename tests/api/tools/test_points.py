from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

STAFFER = 7
VERA = 9
ADA = 21
BEA = 22
VERIFIER_ROLE = 556
PROOF = "https://youtu.be/abc123"

ROUTES = [
    ("GET", "/api/points", None),
    ("GET", "/api/points/board", None),
    ("GET", "/api/points/me", None),
    ("GET", "/api/points/runs", None),
    ("POST", "/api/points/runs", {"game": "x"}),
    ("POST", "/api/points/runs/1/approve", {}),
    ("POST", "/api/points/runs/1/reject", {}),
    ("POST", "/api/points/runs/1/remove", {}),
    ("PATCH", "/api/points/runs/1", {}),
    ("POST", "/api/points/recompute", {}),
    ("GET", "/api/points/bounties", None),
    ("POST", "/api/points/bounties", {}),
    ("PATCH", "/api/points/bounties/1", {}),
    ("POST", "/api/points/bounties/1/end", {}),
]


@pytest.fixture
async def people(guild, wf, web):
    from tests.api.conftest import WebRole

    guild.roles.append(WebRole(VERIFIER_ROLE, "Mentor"))
    wf.member(guild, STAFFER, name="sky", staff=True)
    vera = wf.member(guild, VERA, name="vera")
    vera.roles.append(guild.get_role(VERIFIER_ROLE))
    wf.member(guild, ADA, name="ada")
    wf.member(guild, BEA, name="bea")
    await web.store.set(wf.GUILD_ID, "points_verifier_role_id", VERIFIER_ROLE)


def as_(client, sign_in, wf, uid):
    client.cookies.clear()
    sign_in(client, uid=uid, staff=uid == STAFFER)
    client.headers.update(wf.SAME_SITE)
    return client


def submit(client, **given):
    response = client.post(
        "/api/points/runs", json={"game": "Celeste", "time": "30:00", "proof_url": PROOF, **given}
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_route_needs_a_session(client, method, route, payload):
    response = client.request(method, route, json=payload)
    assert response.status_code == 401
    assert response.json()["message"]


async def test_a_member_submits_reads_the_board_and_is_refused_the_staff_moves(
    client, sign_in, wf, web, people
):
    ada = as_(client, sign_in, wf, ADA)
    sent = submit(ada, category="Any%")
    assert sent["message"] == (
        "Your **Celeste** run (30:00) is in. Staff check the proof before it counts."
    )
    assert (sent["run"]["state"], sent["run"]["name"], sent["run"]["time"]) == (
        "pending",
        "Ada",
        "30:00",
    )
    run_id = sent["run"]["id"]

    index = ada.get("/api/points").json()
    assert (index["mode"], index["by"], index["may_verify"], index["staff"], index["pending"]) == (
        "shadow",
        "points",
        False,
        False,
        None,
    )
    assert index["board"] == []
    assert index["me"]["kind"] == "unranked"
    mine = ada.get("/api/points/runs").json()
    assert [row["id"] for row in mine["runs"]] == [run_id]
    others = ada.get(f"/api/points/runs?user_id={BEA}")
    assert (others.status_code, others.json()["error"]) == (403, "not_verifier")
    assert "**Mentor**" in others.json()["message"]

    approve = ada.post(f"/api/points/runs/{run_id}/approve", json={})
    assert (approve.status_code, approve.json()["error"]) == (403, "not_verifier")
    for method, path in (
        ("POST", f"/api/points/runs/{run_id}/remove"),
        ("PATCH", f"/api/points/runs/{run_id}"),
        ("POST", "/api/points/recompute"),
        ("POST", "/api/points/bounties"),
    ):
        refused = ada.request(method, path, json={})
        assert refused.status_code == 403, path
        assert refused.json()["message"], path


async def test_a_submission_without_proof_is_refused_in_words(client, sign_in, wf, people):
    ada = as_(client, sign_in, wf, ADA)
    refused = ada.post("/api/points/runs", json={"game": "Celeste", "time": "45.2"})
    assert (refused.status_code, refused.json()["error"]) == (400, "no_proof")
    assert refused.json()["message"].startswith("A run needs a link to its video or image")
    bad = ada.post("/api/points/runs", json={"game": "Celeste", "time": "soon", "proof_url": PROOF})
    assert (bad.status_code, bad.json()["error"]) == (400, "bad_time")


async def test_a_verifier_and_staff_decide_runs_from_the_site(client, sign_in, wf, web, people):
    ada_run = submit(as_(client, sign_in, wf, ADA))["run"]["id"]
    bea_run = submit(as_(client, sign_in, wf, BEA), time="10:00")["run"]["id"]

    vera = as_(client, sign_in, wf, VERA)
    queue = vera.get("/api/points/runs?state=pending").json()
    assert [row["id"] for row in queue["runs"]] == [ada_run, bea_run]
    approved = vera.post(f"/api/points/runs/{ada_run}/approve", json={}).json()
    assert approved["message"] == (
        "Approved Ada's **Celeste** run (30:00) — 100 XP, 10 speedpoints."
    )
    assert approved["announce"] == ["Ada is in the top 10 at #1 with 10 speedpoints."]
    assert approved["changed"] == [f"run:{ada_run}", "board", "top"]
    rejected = vera.post(f"/api/points/runs/{bea_run}/reject", json={"reason": "no timer"})
    assert rejected.json()["run"]["state"] == "rejected"
    assert rejected.json()["run"]["reason"] == "no timer"
    again = vera.post(f"/api/points/runs/{bea_run}/approve", json={})
    assert (again.status_code, again.json()["error"]) == (409, "wrong_state")

    staff = as_(client, sign_in, wf, STAFFER)
    reopened = staff.patch(f"/api/points/runs/{bea_run}", json={"time": "15:00"}).json()
    assert reopened["run"]["state"] == "pending"
    staff.post(f"/api/points/runs/{bea_run}/approve", json={})
    staff.post(f"/api/points/runs/{bea_run}/approve", json={})
    board = staff.get("/api/points/board?by=xp").json()
    assert [(row["name"], row["xp"]) for row in board["rows"]] == [("Ada", 100), ("Bea", 50)]
    removed = staff.post(f"/api/points/runs/{ada_run}/remove", json={"reason": "dupe"}).json()
    assert removed["announce"] == ["Bea moved up to #1 (was #2).", "Ada dropped out of the top 10."]
    me = as_(client, sign_in, wf, BEA).get("/api/points/me").json()
    assert me["line"] == "You are #1 with 10 speedpoints. Nobody is ahead of you."

    staff = as_(client, sign_in, wf, STAFFER)
    await web.store.set(wf.GUILD_ID, "points_per_run", 30)
    redone = staff.post("/api/points/recompute", json={}).json()
    assert redone["message"] == "Recomputed the approved runs: 1 of 1 changed."

    kinds = [kind for kind in await wf.kinds_in(web.db) if "points" in kind]
    assert kinds == [
        "web.points.submitted",
        "web.points.submitted",
        "web.points.approved",
        "web.points.would_announce",
        "web.points.rejected",
        "web.points.edited",
        "web.points.approved",
        "web.points.would_announce",
        "web.points.removed",
        "web.points.would_announce",
        "web.points.recomputed",
    ]


async def test_staff_run_bounties_from_the_site(client, sign_in, wf, web, people):
    staff = as_(client, sign_in, wf, STAFFER)
    at = datetime.now(UTC)
    made = staff.post(
        "/api/points/bounties",
        json={
            "name": "Game of the month",
            "games": ["Celeste"],
            "kind": "multiplier",
            "amount": 2,
            "starts_at": (at - timedelta(hours=1)).isoformat(),
            "ends_at": (at + timedelta(days=3)).isoformat(),
        },
    )
    assert made.status_code == 200, made.text
    bounty = made.json()["bounty"]
    assert (bounty["live"], bounty["kind"], bounty["amount"]) == (True, "multiplier", 2.0)
    assert bounty["line"].startswith("**Game of the month** — Celeste: ×2 speedpoints, until ")

    listed = as_(client, sign_in, wf, ADA).get("/api/points").json()
    assert [one["id"] for one in listed["bounties"]] == [bounty["id"]]
    run_id = submit(client)["run"]["id"]
    staff = as_(client, sign_in, wf, STAFFER)
    scored = staff.post(f"/api/points/runs/{run_id}/approve", json={}).json()
    assert (scored["run"]["speedpoints"], scored["run"]["bounty_id"]) == (20, bounty["id"])

    edited = staff.patch(f"/api/points/bounties/{bounty['id']}", json={"amount": 3}).json()
    assert edited["bounty"]["amount"] == 3.0
    bad = staff.patch(f"/api/points/bounties/{bounty['id']}", json={"kind": "extra", "amount": 0.5})
    assert (bad.status_code, bad.json()["error"]) == (400, "bad_bounty_amount")
    ended = staff.post(f"/api/points/bounties/{bounty['id']}/end", json={}).json()
    assert (ended["bounty"]["active"], ended["message"]) == (
        False,
        "Ended the bounty **Game of the month**.",
    )
    every = staff.get("/api/points/bounties").json()["bounties"]
    assert [one["active"] for one in every] == [False]
    assert [kind for kind in await wf.kinds_in(web.db) if "bounty" in kind] == [
        "web.points.bounty_set",
        "web.points.bounty_set",
        "web.points.bounty_ended",
    ]
