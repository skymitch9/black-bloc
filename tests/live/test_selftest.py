"""The one live test that exercises Discord, through the running bot, with cleanup."""

from __future__ import annotations

import time

import pytest

pytestmark = pytest.mark.live

POLL_SECONDS = 5
GIVE_UP_SECONDS = 300


def poll_until_finished(client, run_id):
    deadline = time.monotonic() + GIVE_UP_SECONDS
    while time.monotonic() < deadline:
        body = client.get(f"/api/selftest/{run_id}").json()
        if body["finished_at"]:
            return body
        time.sleep(POLL_SECONDS)
    raise AssertionError(f"run {run_id} was still going after {GIVE_UP_SECONDS} seconds")


def test_the_operator_token_can_read_the_runs_but_never_start_one(reader):
    """auth.py refuses every non-GET on the operator bearer, and says so in words — so the
    read half of this door is open to a Claude session and the write half is not."""
    listed = reader.get("/api/selftest")

    assert listed.status_code == 200
    body = listed.json()
    assert {"runs", "running", "purge_minutes", "notes"} <= set(body)
    assert isinstance(body["runs"], list)

    refused = reader.post("/api/selftest", json={})

    assert refused.status_code == 403
    assert refused.json()["error"] == "operator_read_only"
    assert "can only look, never change" in refused.json()["message"]


def test_the_boot_run_is_on_the_list_and_finished(reader):
    """Every deploy runs one; if the newest run never finished, the bot died mid-run."""
    runs = reader.get("/api/selftest").json()["runs"]
    if not runs:
        pytest.skip("this host has never run the self-test; start one and run this again")

    newest = runs[0]
    assert newest["finished_at"], f"run {newest['run_id']} never finished"
    assert newest["ok"] > 0


def test_a_run_finishes_clean_and_then_purges_what_it_posted(writer):
    """POST, poll to `finished_at`, no failures, then purge and check `purged_at` — the whole
    ask in one test. It posts into the self-test channel and takes it down again."""
    started = writer.post("/api/selftest", json={})
    if started.status_code == 409:
        pytest.skip(f"a run is already going: {started.json()['message']}")

    assert started.status_code == 200, started.text
    run_id = started.json()["run_id"]
    assert started.json()["started_at"]

    found = poll_until_finished(writer, run_id)
    failures = [check for check in found["checks"] if not check["ok"]]

    assert not failures, [f"{one['name']}: {one['detail']}" for one in failures]
    assert found["failed"] == 0
    assert found["ok"] == len(found["checks"])

    purged = writer.post(f"/api/selftest/{run_id}/purge", json={})

    assert purged.status_code == 200, purged.text
    assert purged.json()["purged_at"], "the run was not stamped as purged"
    assert purged.json()["purged"] == found["posted"]


def test_a_run_this_host_does_not_have_is_refused_in_words(reader):
    missing = reader.get("/api/selftest/99999999")

    assert missing.status_code == 404
    said = missing.json()["message"]
    assert "no self-test run numbered 99999999" in said
    assert said != "404" and "Health page" in said
