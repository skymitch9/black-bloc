from __future__ import annotations

import json
import pathlib

import pytest

from black_bloc import structure_store
from black_bloc.cogs.core import set_key
from black_bloc.cogs.moderation.structure_backup import take_snapshot
from black_bloc.structure import MANUAL, SNAPSHOT_FIELDS

ROUTES = [
    ("GET", "/api/structure", None),
    ("POST", "/api/structure/snapshots", {}),
    ("GET", "/api/structure/compare?old=1&new=now", None),
    ("POST", "/api/structure/snapshots/1/download", {}),
]


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_structure_route_needs_a_session(client, method, route, payload):
    assert client.request(method, route, json=payload).status_code == 401


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_structure_route_refuses_a_non_staff_visitor(
    client, sign_in, method, route, payload
):
    sign_in(client, uid=1234, staff=False)
    assert client.request(method, route, json=payload).status_code == 403


def test_the_index_says_the_mode_and_that_nothing_has_been_taken(client, sign_in):
    sign_in(client)

    found = client.get("/api/structure").json()

    assert found["mode"] == "shadow" and found["hour"] == 4 and found["keep"] == 60
    assert found["timezone"] == "America/Phoenix"
    assert found["last_look"] is None and found["snapshots"] == []


async def test_take_one_now_stores_a_snapshot_and_names_who_took_it(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 7, name="ada", staff=True)
    sign_in(client)

    response = client.post("/api/structure/snapshots", json={})

    assert response.status_code == 200
    found = response.json()
    assert found["outcome"] == "saved" and found["message"].startswith("Snapshot #")
    assert found["snapshot"]["source"] == MANUAL
    assert (found["snapshot"]["roles"], found["snapshot"]["categories"]) == (4, 1)
    assert found["snapshot"]["channels"] == 3
    details = await wf.one_web_row(web.db, "web.structure.captured")
    assert details["snapshot_id"] == found["snapshot"]["id"]
    listed = client.get("/api/structure").json()
    assert [row["id"] for row in listed["snapshots"]] == [found["snapshot"]["id"]]
    assert listed["snapshots"][0]["taken_by_id"] == "7"
    assert listed["snapshots"][0]["taken_by_name"] == "Ada"
    assert len(listed["snapshots"][0]["digest"]) == 12
    assert listed["last_look"]["outcome"] == "saved"


async def test_a_second_take_of_an_unchanged_server_stores_nothing(client, sign_in, web, wf):
    sign_in(client)
    client.post("/api/structure/snapshots", json={})

    again = client.post("/api/structure/snapshots", json={}).json()

    assert again["outcome"] == "unchanged" and "no second copy" in again["message"]
    assert await structure_store.count(web.db, wf.GUILD_ID) == 1
    assert client.get("/api/structure").json()["snapshots"][0]["checks"] == 1


async def test_take_one_now_is_refused_in_words_while_the_feature_is_off(
    client, sign_in, web, wf
):
    await web.store.set(wf.GUILD_ID, "structure_backup_mode", "off")
    sign_in(client)

    response = client.post("/api/structure/snapshots", json={})

    assert response.status_code == 409
    assert response.json()["error"] == "structure_off"
    assert "structure_backup_mode" in response.json()["message"]
    assert await structure_store.count(web.db, wf.GUILD_ID) == 0


async def test_a_discord_failure_is_words_not_a_bare_status(client, sign_in, web, guild, wf):
    async def refuse():
        raise RuntimeError("gateway fell over")

    guild.fetch_roles = refuse
    sign_in(client)

    response = client.post("/api/structure/snapshots", json={})

    assert response.status_code == 502
    assert response.json()["error"] == "capture_failed"
    assert response.json()["message"].startswith("No snapshot was taken — something unexpected")
    assert await wf.kinds_in(web.db) == ["web.structure.capture_failed"]


async def two_snapshots(client, guild, wf):
    first = client.post("/api/structure/snapshots", json={}).json()["snapshot"]["id"]
    guild.roles.append(wf.Role(77, "Streamers", position=3))
    second = client.post("/api/structure/snapshots", json={}).json()["snapshot"]["id"]
    return first, second


async def test_two_snapshots_compare_as_a_list_of_changes_in_words(
    client, sign_in, guild, wf
):
    sign_in(client)
    first, second = await two_snapshots(client, guild, wf)

    found = client.get(f"/api/structure/compare?old={first}&new={second}").json()

    assert (found["old"]["id"], found["new"]["id"], found["now"]) == (first, second, False)
    assert found["count"] == 1
    assert found["changes"] == [
        {"area": "roles", "kind": "added", "text": "Role **Streamers** was added."}
    ]


async def test_a_snapshot_compares_with_the_server_as_it_is_now_and_stores_nothing(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    first = client.post("/api/structure/snapshots", json={}).json()["snapshot"]["id"]
    guild.get_channel(wf.OTHER_CHANNEL_ID).name = "lounge"

    found = client.get(f"/api/structure/compare?old={first}&new=now").json()

    assert found["new"] is None and found["now"] is True
    assert [one["text"] for one in found["changes"]] == [
        "Channel **general** was renamed **lounge**."
    ]
    assert await structure_store.count(web.db, wf.GUILD_ID) == 1
    assert await wf.kinds_in(web.db) == ["web.structure.captured"]


@pytest.mark.parametrize(
    ("query", "status", "error", "said"),
    [
        ("old=999&new=now", 404, "no_such_snapshot", "no structure snapshot **#999**"),
        ("old=abc&new=now", 400, "bad_request", "is not a snapshot number"),
        ("old=&new=", 400, "bad_request", "Comparing needs an older snapshot"),
    ],
)
def test_a_compare_that_cannot_run_says_why(client, sign_in, query, status, error, said):
    sign_in(client)

    response = client.get(f"/api/structure/compare?{query}")

    assert response.status_code == status
    assert response.json()["error"] == error and said in response.json()["message"]


async def test_a_download_is_the_named_fields_as_a_file_and_leaves_one_row(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 7, name="ada", staff=True)
    wf.member(guild, 21, name="spammer")
    sign_in(client)
    taken = client.post("/api/structure/snapshots", json={}).json()["snapshot"]["id"]

    response = client.post(f"/api/structure/snapshots/{taken}/download", json={})

    assert response.status_code == 200
    assert response.headers["content-disposition"].startswith(
        f'attachment; filename="structure-{wf.GUILD_ID}-'
    )
    found = response.json()
    assert set(found) == {"snapshot", "version", "guild", "roles", "channels"}
    assert set(found["snapshot"]) == {*SNAPSHOT_FIELDS, "guild_id", "filename"}
    assert f'filename="{found["snapshot"]["filename"]}"' in response.headers["content-disposition"]
    said = json.dumps(found)
    assert "spammer" not in said and "Ada" not in said and "taken_by" not in said
    assert {role["name"] for role in found["roles"]} >= {"@everyone", "Member", "Admin"}
    kinds = await wf.kinds_in(web.db)
    assert kinds == ["web.structure.captured", "web.structure.downloaded"]


def test_a_download_of_a_snapshot_that_is_gone_says_so(client, sign_in):
    sign_in(client)

    response = client.post("/api/structure/snapshots/404/download", json={})

    assert response.status_code == 404
    assert "may have been pruned" in response.json()["message"]


async def test_one_servers_snapshots_are_not_reachable_from_another(
    client, sign_in, web, wf
):
    other = await structure_store.store(
        web.db, 999, {"roles": [{"id": "999", "name": "@everyone"}]}, source=MANUAL, keep=5
    )
    sign_in(client)

    response = client.post(f"/api/structure/snapshots/{other.row['id']}/download", json={})

    assert response.status_code == 404
    assert client.get("/api/structure").json()["snapshots"] == []


PAGE = pathlib.Path(__file__).resolve().parents[3] / "site/public/assets/page-structure.js"


def test_the_page_takes_the_download_name_from_the_api_and_builds_none_of_its_own():
    source = PAGE.read_text(encoding="utf-8")

    assert "saveFile(found.snapshot.filename, found)" in source
    assert "structure-${" not in source and ".json`" not in source


def test_the_page_asks_the_api_for_structure_rows_and_filters_none_itself():
    source = PAGE.read_text(encoding="utf-8")

    assert "const LOG_KINDS = ['structure', 'web.structure'];" in source
    assert "/api/actions?kind=${kind}&per_page=${LOG_ROWS}" in source
    assert "q=structure" not in source and ".test(String(row.kind))" not in source


async def test_the_two_kinds_the_page_asks_for_bring_back_only_structure_rows(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    client.post("/api/structure/snapshots", json={})
    await take_snapshot(web, guild)
    await set_key(web, guild, "structure_backup_hour", 5, None)

    by_hand = client.get("/api/actions?kind=web.structure&per_page=20").json()["actions"]
    by_bot = client.get("/api/actions?kind=structure&per_page=20").json()["actions"]
    searched = client.get("/api/actions?feature=core&q=structure&per_page=20").json()["actions"]

    assert [row["kind"] for row in by_hand] == ["web.structure.captured"]
    assert [row["kind"] for row in by_bot] == ["structure.unchanged"]
    assert "settings.set" in {row["kind"] for row in searched}
