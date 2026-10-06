from __future__ import annotations

import json
import pathlib

import pytest

from black_bloc import structure_store
from black_bloc.api.auth import sees_structure
from black_bloc.api.tools.structure import build_router
from black_bloc.cogs.core import set_key
from black_bloc.cogs.moderation.structure_backup import take_snapshot
from black_bloc.structure import (
    LEADS_KEYS,
    LEADS_ONLY,
    LEADS_ONLY_CODE,
    MANUAL,
    OPERATOR_CODE,
    OPERATOR_REFUSED,
    SNAPSHOT_FIELDS,
)

ROUTES = [
    ("GET", "/api/structure", None),
    ("POST", "/api/structure/snapshots", {}),
    ("GET", "/api/structure/compare?old=1&new=now", None),
    ("POST", "/api/structure/snapshots/1/download", {}),
]


@pytest.fixture(autouse=True)
def the_default_sign_in_is_the_owner(guild):
    guild.owner_id = 7


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


# ---------------------------------------------------------------- leads only (2026-10-05)

MOD = 8
OPERATOR_TOKEN = "operator-read-token-long-enough-to-be-taken"
BEARER = {"Authorization": f"Bearer {OPERATOR_TOKEN}"}
SITE = PAGE.parent


def structure_routes(app):
    found = [
        (method.upper(), path)
        for path, moves in app.openapi()["paths"].items()
        if "structure" in path
        for method in moves
    ]
    assert len(found) >= 4, found
    return sorted(found)


def filled(path):
    return path.replace("{snapshot_id}", "1")


def refusal_of(response):
    return (response.status_code, response.json()["error"], response.json()["message"])


def test_the_route_list_these_tests_walk_is_every_structure_route_the_app_has(client):
    walked = sorted(
        (method, route.split("?")[0].replace("/1/", "/{snapshot_id}/"))
        for method, route, _ in ROUTES
    )

    assert structure_routes(client.app) == walked
    assert len(walked) == 4


def test_every_structure_route_refuses_ordinary_staff_in_words(client, sign_in, guild, wf):
    wf.member(guild, MOD, name="mod", staff=True)
    sign_in(client, uid=MOD)
    assert client.get("/api/settings").status_code == 200

    found = structure_routes(client.app)

    assert found
    for method, path in found:
        response = client.request(method, filled(path), json={})
        assert refusal_of(response) == (403, LEADS_ONLY_CODE, LEADS_ONLY), (method, path)


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
async def test_ordinary_staff_leave_no_snapshot_and_no_row_behind(
    client, sign_in, web, guild, wf, method, route, payload
):
    await structure_store.store(web.db, wf.GUILD_ID, {"roles": []}, source=MANUAL, keep=5)
    wf.member(guild, MOD, name="mod", staff=True)
    sign_in(client, uid=MOD)

    response = client.request(method, route, json=payload)

    assert response.status_code == 403 and response.json()["error"] == LEADS_ONLY_CODE
    assert "roles" not in response.json() and "snapshots" not in response.json()
    assert await structure_store.count(web.db, wf.GUILD_ID) == 1
    assert await wf.kinds_in(web.db) == []


def test_every_structure_route_is_behind_the_one_gate_by_construction(web):
    router = build_router(web)

    assert len(router.dependencies) == 1
    gate = router.dependencies[0].dependency
    assert gate.__qualname__.startswith("leads_dependency.")
    source = (
        pathlib.Path(__file__).resolve().parents[3] / "black_bloc/api/tools/structure.py"
    ).read_text(encoding="utf-8")
    assert source.count("APIRouter(") == 1 and "staff_dependency(bot))]" not in source
    assert "sees_structure(bot, who)" in source and sees_structure.__module__.endswith("api.auth")


def test_the_owner_gets_in_holding_no_staff_role(client, sign_in, guild, wf):
    guild.owner_id = 31
    owner = guild.add_member(wf.Member(31, [], name="owner", manage_guild=True))
    assert not owner.roles
    sign_in(client, uid=31)

    assert client.get("/api/structure").status_code == 200
    assert client.post("/api/structure/snapshots", json={}).status_code == 200
    assert client.get("/api/auth/me").json()["structure"] is True


def test_an_administrator_gets_in(client, sign_in, guild, wf):
    admin = guild.add_member(wf.Member(32, [], name="admin", manage_guild=True))
    admin.guild_permissions.administrator = True
    sign_in(client, uid=32)

    assert client.get("/api/structure").status_code == 200
    assert client.get("/api/auth/me").json()["structure"] is True


def test_manage_server_alone_is_staff_and_not_a_lead(client, sign_in, guild, wf):
    guild.add_member(wf.Member(33, [], name="manager", manage_guild=True))
    sign_in(client, uid=33)

    assert client.get("/api/settings").status_code == 200
    assert refusal_of(client.get("/api/structure")) == (403, LEADS_ONLY_CODE, LEADS_ONLY)


async def test_a_holder_of_the_structure_role_gets_in_and_loses_it_with_the_role(
    client, sign_in, web, guild, wf
):
    guild.roles.append(wf.Role(77, "Leads", position=8))
    lead = wf.member(guild, MOD, name="lead", staff=True)
    lead.roles.append(guild.get_role(77))
    await web.store.set(wf.GUILD_ID, "structure_backup_role_id", 77)
    sign_in(client, uid=MOD)

    assert client.get("/api/structure").status_code == 200
    assert client.get("/api/auth/me").json()["structure"] is True
    lead.roles.remove(guild.get_role(77))

    assert refusal_of(client.get("/api/structure")) == (403, LEADS_ONLY_CODE, LEADS_ONLY)
    assert client.post("/api/structure/snapshots", json={}).status_code == 403
    assert client.get("/api/auth/me").json()["structure"] is False


async def test_the_structure_role_never_lets_in_someone_who_is_not_staff(
    client, sign_in, web, guild, wf
):
    guild.roles.append(wf.Role(77, "Leads", position=8))
    guild.add_member(wf.Member(34, [guild.get_role(77)], name="friend"))
    await web.store.set(wf.GUILD_ID, "structure_backup_role_id", 77)
    sign_in(client, uid=34, staff=False)

    for method, path in structure_routes(client.app):
        response = client.request(method, filled(path), json={})
        assert (response.status_code, response.json()["error"]) == (403, "not_staff"), path
    assert client.get("/api/auth/me").json()["structure"] is False


def test_with_no_role_set_every_staff_role_is_refused(client, sign_in, web, guild, wf):
    assert web.store.get(wf.GUILD_ID, "structure_backup_role_id") is None
    mod = wf.member(guild, MOD, name="mod", staff=True)
    mod.roles += [guild.get_role(wf.PLAIN_ROLE_ID), wf.Role(0, "zero")]
    sign_in(client, uid=MOD)

    assert refusal_of(client.get("/api/structure")) == (403, LEADS_ONLY_CODE, LEADS_ONLY)
    assert client.get("/api/auth/me").json()["structure"] is False


def test_a_member_and_a_visitor_are_refused_as_they_always_were(client, sign_in):
    assert client.get("/api/structure").json()["error"] == "not_signed_in"
    sign_in(client, uid=1234, staff=False)

    assert refusal_of(client.get("/api/structure"))[:2] == (403, "not_staff")


async def test_the_operator_token_is_refused_in_words_on_every_route_and_leaves_no_row(
    client, web, wf
):
    web.settings.operator_read_token = OPERATOR_TOKEN
    assert client.get("/api/settings", headers=BEARER).status_code == 200
    before = await wf.kinds_in(web.db)

    for method, path in structure_routes(client.app):
        response = client.request(method, filled(path), json={}, headers=BEARER)
        assert refusal_of(response) == (403, OPERATOR_CODE, OPERATOR_REFUSED), (method, path)
    wrong = client.get("/api/structure", headers={"Authorization": "Bearer not-the-token-at-all"})

    assert refusal_of(wrong) == (403, OPERATOR_CODE, OPERATOR_REFUSED)
    assert await wf.kinds_in(web.db) == before == ["web.operator.read"]
    assert client.get("/api/auth/me", headers=BEARER).json()["structure"] is False
    for needed in ("operator token", "nothing was read", "Sign in on the dashboard"):
        assert needed in OPERATOR_REFUSED


def test_the_operator_token_does_not_ride_in_on_a_leads_cookie(client, sign_in, web):
    web.settings.operator_read_token = OPERATOR_TOKEN
    sign_in(client)
    assert client.get("/api/structure").status_code == 200

    response = client.get("/api/structure/compare?old=1&new=now", headers=BEARER)

    assert refusal_of(response) == (403, OPERATOR_CODE, OPERATOR_REFUSED)


def test_a_bearer_changes_nothing_while_no_operator_token_is_configured(client, sign_in):
    sign_in(client)

    assert client.get("/api/structure", headers=BEARER).status_code == 200


@pytest.mark.parametrize("key", LEADS_KEYS)
async def test_the_keys_that_decide_who_sees_it_are_changed_only_by_a_lead(
    client, sign_in, web, guild, wf, key
):
    wf.member(guild, MOD, name="mod", staff=True)
    sign_in(client, uid=MOD)
    value = str(wf.STAFF_ROLE_ID if key.endswith("role_id") else wf.TEST_CHANNEL_ID)

    put = client.put(f"/api/settings/{key}", json={"value": value})
    cleared = client.delete(f"/api/settings/{key}")

    assert refusal_of(put) == (403, LEADS_ONLY_CODE, LEADS_ONLY)
    assert refusal_of(cleared) == (403, LEADS_ONLY_CODE, LEADS_ONLY)
    assert web.store.get(wf.GUILD_ID, key) is None
    assert await wf.kinds_in(web.db) == []
    client.cookies.clear()
    sign_in(client)
    assert client.put(f"/api/settings/{key}", json={"value": value}).status_code == 200
    assert str(web.store.get(wf.GUILD_ID, key)) == value
    assert client.delete(f"/api/settings/{key}").status_code == 200


def test_the_three_gated_keys_are_the_role_and_the_two_notice_channels():
    assert LEADS_KEYS == (
        "structure_backup_role_id",
        "structure_backup_channel_id",
        "structure_backup_shadow_channel_id",
    )


async def test_ordinary_staff_still_see_that_the_feature_exists_and_its_mode_and_nothing_more(
    client, sign_in, web, guild, wf
):
    sign_in(client)
    client.post("/api/structure/snapshots", json={})
    client.cookies.clear()
    wf.member(guild, MOD, name="mod", staff=True)
    sign_in(client, uid=MOD)

    status = client.get("/api/status").json()
    row = next(one for one in status["features"] if one["feature"] == "structure_backup")
    settings = client.get("/api/settings").text

    assert row["mode"] == "shadow" and set(row) == {"key", "feature", "mode"}
    assert "structure_backup_mode" in settings
    assert client.put(
        "/api/settings/structure_backup_mode", json={"value": "off"}
    ).status_code == 200
    logged = client.get("/api/actions?kind=web.structure&per_page=20&details=1").json()["actions"]
    assert [one["kind"] for one in logged] == ["web.structure.captured"]
    assert set(logged[0]["details"]) <= {
        "via",
        "source",
        "snapshot_id",
        "roles",
        "categories",
        "channels",
        "overwrites",
        "changes",
    }
    for name in ("blackbloc-logs", "general", "Aunties", "Admin"):
        assert name not in str(logged), name


def test_the_rail_offers_structure_only_to_someone_the_bot_says_may_see_it():
    shell = (SITE / "shell.js").read_text(encoding="utf-8")
    app = (SITE / "app.js").read_text(encoding="utf-8")

    assert "{ tab: 'structure', label: 'Structure', icon: 'navStructure', leads: true }" in shell
    assert "hidden: item.leads ? true : undefined," in shell
    assert "(leadsOnly && !lead)" in shell
    assert "paintNavFor(isMemberOnly(me), Boolean(me) && me.structure === true);" in shell
    assert "error.code === 'structure_leads_only'" in app
    assert "Structure is for the server’s leads" in app
    assert "me.structure" not in PAGE.read_text(encoding="utf-8")


def test_the_page_states_where_the_notice_goes_from_the_two_keys_and_nothing_else():
    source = PAGE.read_text(encoding="utf-8")

    assert (
        "const NOTICE_KEYS = { on: 'structure_backup_channel_id', "
        "shadow: 'structure_backup_shadow_channel_id' };"
    ) in source
    assert "badge('notice goes nowhere', 'warn')" in source and "badge('notice off')" in source
    assert "staff_channel_id" not in source and "'shadow_channel_id'" not in source
