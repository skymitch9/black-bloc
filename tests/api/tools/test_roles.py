from __future__ import annotations

from datetime import UTC, datetime

import discord
import pytest

from black_bloc import rolegrants as grants

MEMBER_ID = 900

ROUTES = [
    ("GET", "/api/roles/grants", None),
    ("POST", "/api/roles/grants", {"user_id": "900", "role_id": "22", "days": 7}),
    ("POST", "/api/roles/grants/1/extend", {"days": 3}),
    ("DELETE", "/api/roles/grants/1", None),
]


class Refused:
    def __init__(self, status):
        self.status = status
        self.reason = "refused"


def call(client, method, route, payload):
    return client.request(method, route, json=payload)


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_grant_route_needs_a_session(client, method, route, payload):
    response = call(client, method, route, payload)
    assert response.status_code == 401
    assert response.json()["error"] == "not_signed_in"


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_grant_route_refuses_a_non_staff_visitor(client, sign_in, method, route, payload):
    sign_in(client, uid=1234, staff=False)
    response = call(client, method, route, payload)
    assert response.status_code == 403
    assert response.json()["error"] == "not_staff"


async def test_a_grant_hands_the_role_over_and_is_listed_with_names(client, sign_in, web, wf):
    sign_in(client)
    member = wf.member(web.guild, MEMBER_ID, name="ada")

    made = client.post(
        "/api/roles/grants",
        json={"user_id": str(MEMBER_ID), "role_id": str(wf.STAFF_ROLE_ID), "days": 7},
    ).json()

    assert made["open"] is True and made["source"] == "staff"
    assert made["user_name"] == "Ada" and made["role_name"] == "Aunties / Uncles"
    assert made["expires_at"] is not None
    assert member.edits and wf.STAFF_ROLE_ID in member.edits[0]
    listed = client.get("/api/roles/grants").json()
    assert [row["id"] for row in listed] == [made["id"]]
    assert "web.role.granted" in await wf.kinds_in(web.db)


async def test_a_grant_with_no_days_never_runs_out(client, sign_in, web, wf):
    sign_in(client)
    wf.member(web.guild, MEMBER_ID, name="ada")

    made = client.post(
        "/api/roles/grants", json={"user_id": str(MEMBER_ID), "role_id": str(wf.PLAIN_ROLE_ID)}
    ).json()

    assert made["expires_at"] is None


def test_days_that_are_not_a_number_are_refused_in_words(client, sign_in, web, wf):
    sign_in(client)
    wf.member(web.guild, MEMBER_ID, name="ada")

    response = client.post(
        "/api/roles/grants",
        json={"user_id": str(MEMBER_ID), "role_id": str(wf.PLAIN_ROLE_ID), "days": "a week"},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "bad_days"
    assert "not a number of days" in response.json()["message"]


def test_a_member_or_role_that_is_gone_is_named_rather_than_guessed(client, sign_in, web, wf):
    sign_in(client)
    wf.member(web.guild, MEMBER_ID, name="ada")

    gone = client.post(
        "/api/roles/grants", json={"user_id": "4040", "role_id": str(wf.PLAIN_ROLE_ID)}
    )
    no_role = client.post(
        "/api/roles/grants", json={"user_id": str(MEMBER_ID), "role_id": "4040"}
    )

    assert gone.status_code == 404 and gone.json()["error"] == "no_such_member"
    assert no_role.status_code == 404 and no_role.json()["error"] == "no_such_role"


def test_a_refused_role_edit_leaves_no_record_behind(client, sign_in, web, wf):
    sign_in(client)
    member = wf.member(web.guild, MEMBER_ID, name="ada")
    member.edit_raises = discord.HTTPException(Refused(403), "no")

    response = client.post(
        "/api/roles/grants",
        json={"user_id": str(MEMBER_ID), "role_id": str(wf.STAFF_ROLE_ID), "days": 7},
    )

    assert response.status_code == 409 and response.json()["error"] == "role_refused"
    assert "Manage Roles" in response.json()["message"]
    assert client.get("/api/roles/grants").json() == []


async def test_extending_pushes_the_end_date_back(client, sign_in, web, wf):
    sign_in(client)
    wf.member(web.guild, MEMBER_ID, name="ada")
    grant_id = await grants.add_grant(
        web.db, wf.GUILD_ID, MEMBER_ID, wf.PLAIN_ROLE_ID, "staff", until=grants.expires_at(3)
    )

    row = client.post(f"/api/roles/grants/{grant_id}/extend", json={"days": 4}).json()

    assert (grants.parse_ts(row["expires_at"]) - datetime.now(UTC)).days == 6
    assert "web.role.extended" in await wf.kinds_in(web.db)


async def test_extending_a_grant_with_no_end_date_is_refused_in_words(client, sign_in, web, wf):
    sign_in(client)
    grant_id = await grants.add_grant(
        web.db, wf.GUILD_ID, MEMBER_ID, wf.PLAIN_ROLE_ID, "staff"
    )

    response = client.post(f"/api/roles/grants/{grant_id}/extend", json={"days": 4})

    assert response.status_code == 409 and response.json()["error"] == "no_end_date"


async def test_extending_needs_a_number_of_days(client, sign_in, web, wf):
    sign_in(client)
    grant_id = await grants.add_grant(
        web.db, wf.GUILD_ID, MEMBER_ID, wf.PLAIN_ROLE_ID, "staff", until=grants.expires_at(3)
    )

    response = client.post(f"/api/roles/grants/{grant_id}/extend", json={})

    assert response.status_code == 400 and response.json()["error"] == "no_days"


async def test_ending_a_grant_now_takes_the_role_off_too(client, sign_in, web, wf):
    sign_in(client)
    member = wf.member(web.guild, MEMBER_ID, name="ada")
    member.roles = [web.guild.get_role(wf.PLAIN_ROLE_ID)]
    grant_id = await grants.add_grant(
        web.db, wf.GUILD_ID, MEMBER_ID, wf.PLAIN_ROLE_ID, "staff", until=grants.expires_at(3)
    )

    row = client.delete(f"/api/roles/grants/{grant_id}").json()

    assert row["open"] is False and row["removed_reason"] == "ended_by_staff"
    assert member.edits == [[]]
    assert "web.role.ended" in await wf.kinds_in(web.db)


async def test_ending_a_grant_twice_is_refused_rather_than_repeated(client, sign_in, web, wf):
    sign_in(client)
    grant_id = await grants.add_grant(
        web.db, wf.GUILD_ID, MEMBER_ID, wf.PLAIN_ROLE_ID, "staff", until=grants.expires_at(3)
    )
    client.delete(f"/api/roles/grants/{grant_id}")

    again = client.delete(f"/api/roles/grants/{grant_id}")

    assert again.status_code == 409 and again.json()["error"] == "already_ended"


def test_a_grant_nobody_has_is_a_404_with_a_sentence(client, sign_in):
    sign_in(client)

    response = client.delete("/api/roles/grants/404")

    assert response.status_code == 404
    assert "no timed role **#404**" in response.json()["message"]


async def test_the_list_filters_by_member_and_by_role(client, sign_in, web, wf):
    sign_in(client)
    mine = await grants.add_grant(web.db, wf.GUILD_ID, MEMBER_ID, wf.PLAIN_ROLE_ID, "staff")
    theirs = await grants.add_grant(web.db, wf.GUILD_ID, 901, wf.STAFF_ROLE_ID, "menu")

    by_member = client.get(f"/api/roles/grants?user_id={MEMBER_ID}").json()
    by_role = client.get(f"/api/roles/grants?role_id={wf.STAFF_ROLE_ID}").json()

    assert [row["id"] for row in by_member] == [mine]
    assert [row["id"] for row in by_role] == [theirs]


async def test_a_grant_for_a_role_they_already_hold_only_starts_the_clock(client, sign_in, web, wf):
    sign_in(client)
    member = wf.member(web.guild, MEMBER_ID, name="ada")
    member.roles = [web.guild.get_role(wf.PLAIN_ROLE_ID)]

    made = client.post(
        "/api/roles/grants",
        json={"user_id": str(MEMBER_ID), "role_id": str(wf.PLAIN_ROLE_ID), "days": 7},
    ).json()

    assert member.edits == []
    assert made["expires_at"] is not None
