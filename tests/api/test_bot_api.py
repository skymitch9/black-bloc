from __future__ import annotations

import pytest

from black_bloc import restart

LEAD = 9
STAFFER = 7


@pytest.fixture
def lead(web, wf, guild):
    one = wf.Member(LEAD, [guild.get_role(wf.ADMIN_ROLE_ID)], name="lead", manage_guild=True)
    guild.add_member(one)
    return one


@pytest.fixture
def staffer(web, wf, guild):
    return wf.member(guild, STAFFER, name="mod", staff=True)


@pytest.fixture
def asked(monkeypatch):
    """The route's own test never starts the shutdown; tests/test_restart.py is where that lives."""
    found: list = []
    monkeypatch.setattr(restart, "schedule", lambda bot, **kw: found.append(bot))
    return found


@pytest.fixture
def can_exit(web):
    codes: list[int] = []
    web.exit_now = codes.append
    return codes


async def test_a_lead_restarts_the_bot_and_the_row_says_who(
    client, sign_in, web, wf, lead, asked, can_exit
):
    sign_in(client, uid=LEAD, staff=True, cached=False)

    answered = client.post("/api/bot/restart", json={})

    assert answered.status_code == 200
    body = answered.json()
    assert str(restart.DOWN_SECONDS) in body["message"] and body["seconds"] == restart.DOWN_SECONDS
    assert len(asked) == 1
    details = await wf.one_web_row(web.db, "web.core.restart_requested")
    assert details["seconds"] == restart.DOWN_SECONDS
    rows = await wf.web_rows_in(web.db)
    assert len(rows) == 1


async def test_a_staffer_without_manage_server_is_refused_in_words(
    client, sign_in, web, wf, staffer, asked, can_exit
):
    sign_in(client, uid=STAFFER, staff=True, cached=False)

    refused = client.post("/api/bot/restart", json={})

    assert refused.status_code == 403
    assert refused.json()["error"] == "not_a_lead"
    assert "Manage Server" in refused.json()["message"]
    assert asked == []
    assert await wf.web_rows_in(web.db) == []


async def test_nobody_else_gets_near_it(client, sign_in, web, wf, asked, can_exit):
    sign_in(client, uid=STAFFER, staff=False, cached=False)

    refused = client.post("/api/bot/restart", json={})

    assert refused.status_code == 403
    assert asked == []
    assert await wf.web_rows_in(web.db) == []


async def test_a_bot_with_no_way_out_refuses_instead_of_pretending(
    client, sign_in, web, wf, lead, asked
):
    """A test double has no `exit_now`, so a route that skipped this check would answer 200
    and restart nothing — the "claiming a check that was skipped is a lie" case."""
    sign_in(client, uid=LEAD, staff=True, cached=False)

    refused = client.post("/api/bot/restart", json={})

    assert refused.status_code == 503
    assert refused.json()["error"] == "cannot_restart"
    assert asked == []
    assert await wf.web_rows_in(web.db) == []
