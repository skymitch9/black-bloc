from __future__ import annotations

from types import SimpleNamespace

import pytest

from black_bloc.api import page_views
from black_bloc.settings_store import (
    COMMITTEE_ROLE_ID,
    KEY_TYPES,
    VIEW_MEMBER_PAGES,
    VIEW_PAGES,
    namespace_of,
    view_key,
)

VIEWER = 1234


def role(role_id):
    return SimpleNamespace(id=role_id)


def test_every_page_has_a_roles_key_in_one_settings_group():
    for page in VIEW_PAGES:
        key = view_key(page)
        assert KEY_TYPES[key] == "roles"
        assert namespace_of(key) == "core"


def test_every_page_has_api_prefixes_of_its_own_kind():
    staff = set(page_views.STAFF_PAGE_PREFIXES)
    members = set(page_views.MEMBER_PAGE_PREFIXES)
    assert staff | members == set(VIEW_PAGES)
    assert not staff & members
    assert members == set(VIEW_MEMBER_PAGES)


async def test_runs_opens_to_committee_and_member_pages_to_everyone_by_default(web, wf):
    assert web.store.get(wf.GUILD_ID, view_key("runs")) == [COMMITTEE_ROLE_ID]
    for page in VIEW_MEMBER_PAGES:
        assert web.store.get(wf.GUILD_ID, view_key(page)) == [wf.GUILD_ID]
    assert web.store.get(wf.GUILD_ID, view_key("events")) == []
    assert web.store.default(view_key("brackets"), wf.GUILD_ID) == [wf.GUILD_ID]


async def test_a_role_or_everyone_opens_a_page_and_nothing_else_does(web, wf):
    guild = SimpleNamespace(id=wf.GUILD_ID)
    committee = SimpleNamespace(roles=[role(COMMITTEE_ROLE_ID)])
    plain = SimpleNamespace(roles=[role(wf.PLAIN_ROLE_ID)])
    assert page_views.may_view(web.store, guild, committee, "runs")
    assert not page_views.may_view(web.store, guild, plain, "runs")
    assert page_views.may_view(web.store, guild, plain, "brackets")
    assert not page_views.may_view(web.store, guild, plain, "nope")
    assert not page_views.may_view(web.store, guild, None, "brackets")


def test_a_prefix_matches_whole_segments_only():
    assert page_views.under("/api/runs", "/api/runs")
    assert page_views.under("/api/runs/games", "/api/runs")
    assert not page_views.under("/api/runsx", "/api/runs")
    assert page_views.pages_at("/api/actions", page_views.STAFF_PAGE_PREFIXES) == [
        "overview",
        "health",
        "audit",
    ]


async def test_a_runs_viewer_reads_runs_and_names_but_never_writes(client, sign_in, web, wf):
    await web.store.set(wf.GUILD_ID, view_key("runs"), [wf.PLAIN_ROLE_ID])
    sign_in(client, uid=VIEWER, staff=False)
    assert client.get("/api/runs").status_code == 200
    assert client.get("/api/runs/games").status_code == 200
    assert client.get("/api/runs/export.csv").status_code == 200
    assert client.get("/api/ref/roles").status_code == 200
    refused = client.post("/api/runs", json={"game": "x"}, headers=wf.SAME_SITE)
    assert refused.status_code == 403 and refused.json()["error"] == "read_only"
    assert client.get("/api/events").status_code == 403
    assert client.get("/api/actions").status_code == 403
    assert client.get("/api/settings").status_code == 403


async def test_a_member_without_the_role_is_still_refused_runs(client, sign_in, web, wf):
    sign_in(client, uid=VIEWER, staff=False)
    found = client.get("/api/runs")
    assert found.status_code == 403 and found.json()["error"] == "not_staff"
    assert client.get("/api/ref/roles").status_code == 403


async def test_me_lists_the_pages_a_member_may_open(client, sign_in, web, wf):
    await web.store.set(wf.GUILD_ID, view_key("runs"), [wf.PLAIN_ROLE_ID])
    sign_in(client, uid=VIEWER, staff=False)
    views = client.get("/api/auth/me").json()["views"]
    assert views == [page for page in VIEW_PAGES if page in {*VIEW_MEMBER_PAGES, "runs"}]


async def test_staff_open_every_page(client, sign_in, web, wf):
    sign_in(client)
    assert client.get("/api/auth/me").json()["views"] == list(VIEW_PAGES)


@pytest.mark.parametrize("path", ["/api/brackets", "/api/guides"])
async def test_a_member_page_closes_when_everyone_is_taken_off_it(
    client, sign_in, web, wf, path
):
    page = "brackets" if "brackets" in path else "guides"
    sign_in(client, uid=VIEWER, staff=False)
    assert client.get(path).status_code != 403
    await web.store.set(wf.GUILD_ID, view_key(page), [])
    closed = client.get(path)
    assert closed.status_code == 403 and closed.json()["error"] == "page_closed"
    assert page not in client.get("/api/auth/me").json()["views"]


async def test_a_member_page_opening_never_opens_its_staff_reads(client, sign_in, web, wf):
    sign_in(client, uid=VIEWER, staff=False)
    assert client.get("/api/requests").status_code == 403
