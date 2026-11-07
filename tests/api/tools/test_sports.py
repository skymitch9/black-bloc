from __future__ import annotations

from black_bloc import sports_names
from black_bloc.sports import espn
from tests.sports_fakes import payload

STAFFER = 7
ADA = 21


def as_(client, sign_in, wf, uid):
    client.cookies.clear()
    sign_in(client, uid=uid, staff=uid == STAFFER)
    client.headers.update(wf.SAME_SITE)
    return client


async def seeded(web):
    teams = espn.parse_teams(payload("espn_teams_nba"), "nba")
    await sports_names.upsert(web.db, "team", "nba", "espn", teams)


def test_every_sports_route_needs_a_session(client):
    for method, route in (
        ("GET", "/api/ref/sports?q=bos"),
        ("GET", "/api/sports"),
        ("POST", "/api/sports/refresh"),
    ):
        response = client.request(method, route, json={} if method == "POST" else None)
        assert response.status_code == 401, route
        assert response.json()["message"]


async def test_any_member_may_search_the_names(client, sign_in, wf, web, guild):
    wf.member(guild, ADA, name="ada")
    await seeded(web)
    member = as_(client, sign_in, wf, ADA)
    found = member.get("/api/ref/sports", params={"kind": "team", "league": "nba", "q": "bos"})
    assert found.status_code == 200, found.text
    assert found.json() == [
        {
            "ext_id": "2",
            "name": "Boston Celtics",
            "short": "BOS",
            "league": "nba",
            "team": None,
            "source": "espn",
            "kind": "team",
        }
    ]
    assert member.get("/api/ref/sports", params={"kind": "team", "q": ""}).json() == []


async def test_the_names_status_and_refresh_are_staff_only(client, sign_in, wf, web, guild):
    wf.member(guild, ADA, name="ada")
    member = as_(client, sign_in, wf, ADA)
    for method, route in (("GET", "/api/sports"), ("POST", "/api/sports/refresh")):
        refused = member.request(method, route, json={} if method == "POST" else None)
        assert refused.status_code == 403, route
        assert refused.json()["message"]


async def test_refresh_runs_now_and_leaves_one_web_row(client, sign_in, wf, web, guild):
    wf.member(guild, STAFFER, name="sky", staff=True)
    staff = as_(client, sign_in, wf, STAFFER)
    done = staff.post("/api/sports/refresh", json={})
    assert done.status_code == 200, done.text
    body = done.json()
    assert body["message"] == "Names refreshed: 7 of 11 lists answered."
    assert body["running"] is False
    lists = {one["list"]: one for one in body["lists"]}
    assert lists["team:nba"]["rows"] == 2
    assert lists["team:nfl"]["why"] == "ESPN answered 404 for the NFL teams"
    kinds = await wf.kinds_in(web.db)
    assert kinds.count("web.sports.refresh") == 1
    assert kinds.count("sports.names_refreshed") == 1
    status = staff.get("/api/sports").json()
    assert {one["list"] for one in status["lists"]} == set(lists)
    assert status["checked_at"]
