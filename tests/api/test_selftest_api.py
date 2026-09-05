from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from black_bloc import selftest
from black_bloc.api.selftest_api import NOTHING_TO_PURGE, RUNS_LIMIT
from black_bloc.api.server import create_app


def only(*checks):
    def chosen(_bot):
        return tuple(checks)

    return chosen


def one_check(name, detail="fine", fails=False):
    async def body(_one):
        if fails:
            raise selftest.CheckFailed(detail)
        return detail

    return selftest.Check(name, "core", body)


def stub(monkeypatch, *checks):
    monkeypatch.setattr(selftest, "checks_for", only(*checks))


def finished(client, run_id, tries=200):
    """The POST starts the run and lets go, so the test polls the way the Health card does."""
    for _ in range(tries):
        body = client.get(f"/api/selftest/{run_id}").json()
        if body["finished_at"]:
            return body
        time.sleep(0.01)
    raise AssertionError(f"run {run_id} never finished")


@pytest.fixture
def client(web, wf):
    """As a CONTEXT MANAGER, unlike the shared fixture: without it every request gets a new
    event loop and the run this door starts in the background is killed on the way out."""
    with TestClient(create_app(web), base_url=wf.ORIGIN, headers=wf.SAME_SITE) as one:
        yield one


@pytest.fixture(autouse=True)
def quick(monkeypatch):
    """Every test here names its own checks; the real ones would build a second FastAPI app."""
    stub(monkeypatch, one_check("config.log_channel_id"))


async def test_a_run_started_from_the_website_answers_its_id_and_then_its_result(
    client, sign_in, web, wf
):
    sign_in(client)

    started = client.post("/api/selftest", json={})

    assert started.status_code == 200
    body = started.json()
    assert body["run_id"] and body["started_at"] and body["checks"] == 1

    found = finished(client, body["run_id"])

    assert (found["ok"], found["failed"], found["posted"]) == (1, 0, 0)
    assert found["via"] == "website"
    assert found["running"] is False
    assert [row["name"] for row in found["checks"]] == ["config.log_channel_id"]
    assert found["checks"][0]["ok"] is True
    kinds = [kind for kind in await wf.kinds_in(web.db) if "selftest" in kind]
    assert kinds == [
        "web.selftest.started",
        "web.selftest.check",
        "web.selftest.finished",
    ]


async def test_the_list_says_which_run_is_going_and_how_long_the_cards_live(client, sign_in):
    sign_in(client)
    empty = client.get("/api/selftest").json()

    assert empty["runs"] == [] and empty["running"] is None
    assert empty["purge_minutes"] == 5

    run_id = client.post("/api/selftest", json={}).json()["run_id"]
    finished(client, run_id)
    body = client.get("/api/selftest").json()

    assert len(body["runs"]) == 1
    assert set(body["runs"][0]) == {
        "run_id",
        "started_at",
        "finished_at",
        "ok",
        "failed",
        "posted",
        "purged_at",
        "via",
        "actor_id",
        "running",
    }
    assert body["running"] is None


async def test_a_failing_check_is_a_sentence_on_the_run_rather_than_a_failed_request(
    client, sign_in, monkeypatch
):
    stub(monkeypatch, one_check("read./api/costs", "TypeError: no", fails=True))
    sign_in(client)

    run_id = client.post("/api/selftest", json={}).json()["run_id"]
    found = finished(client, run_id)

    assert (found["ok"], found["failed"]) == (0, 1)
    assert found["checks"][0]["ok"] is False
    assert found["checks"][0]["detail"] == "CheckFailed: TypeError: no"


async def test_a_second_start_is_refused_in_words_and_never_as_a_bare_status(
    client, sign_in, web, wf, monkeypatch
):
    """Global rule: a person never sees a bare 409 — the body says what happened and why."""
    sign_in(client)
    going = selftest.Run(bot=web, guild=web.guild, total=41)
    going.run_id = 99
    web._selftest_running = {wf.GUILD_ID: going}

    refused = client.post("/api/selftest", json={})

    assert refused.status_code == 409
    said = refused.json()["message"]
    assert "already running" in said and "0 of 41 checks done" in said
    assert refused.json()["error"] == "selftest_running"
    assert client.get("/api/selftest").json()["running"] == 99


async def test_purging_a_run_takes_its_cards_down_and_stamps_it(
    client, sign_in, web, wf, monkeypatch
):
    async def posts(one):
        await one.post(content="a card")
        return "posted"

    stub(monkeypatch, selftest.Check("panel.settings", "core", posts))
    await web.store.set(wf.GUILD_ID, "selftest_channel_id", wf.TEST_CHANNEL_ID)
    sign_in(client)

    run_id = client.post("/api/selftest", json={}).json()["run_id"]
    ran = finished(client, run_id)

    assert ran["posted"] == 1 and ran["purged_at"] is None

    purged = client.post(f"/api/selftest/{run_id}/purge", json={})

    assert purged.status_code == 200
    assert purged.json()["purged"] == 1
    assert purged.json()["purged_at"]
    assert purged.json()["notes"] == []
    assert await selftest.waiting_messages(web.db, wf.GUILD_ID) == []


async def test_purging_a_run_with_nothing_left_says_so_rather_than_reading_as_a_failure(
    client, sign_in
):
    sign_in(client)
    run_id = client.post("/api/selftest", json={}).json()["run_id"]
    finished(client, run_id)

    purged = client.post(f"/api/selftest/{run_id}/purge", json={})

    assert purged.status_code == 200
    assert purged.json()["purged"] == 0
    assert purged.json()["notes"] == [NOTHING_TO_PURGE]


async def test_a_run_this_server_does_not_have_is_a_sentence_not_a_bare_404(client, sign_in):
    sign_in(client)

    missing = client.get("/api/selftest/404")

    assert missing.status_code == 404
    assert "no self-test run numbered 404" in missing.json()["message"]
    assert "Health page" in missing.json()["message"]
    assert client.post("/api/selftest/404/purge", json={}).status_code == 404


def test_every_self_test_route_needs_a_staff_session(client):
    for method, path in (
        ("GET", "/api/selftest"),
        ("GET", "/api/selftest/1"),
        ("POST", "/api/selftest"),
        ("POST", "/api/selftest/1/purge"),
    ):
        response = client.request(method, path, json={} if method == "POST" else None)
        assert response.status_code in (401, 403), path
        assert response.json()["message"], path


def test_the_list_is_capped_so_one_page_never_grows_without_bound():
    assert RUNS_LIMIT == 20
