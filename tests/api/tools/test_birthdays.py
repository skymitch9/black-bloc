from __future__ import annotations

import pytest

from black_bloc.cogs.community.birthdays import get_birthday

ROUTES = [
    ("GET", "/api/birthdays", None),
    ("PUT", "/api/birthdays/21", {"month": 3, "day": 4}),
    ("DELETE", "/api/birthdays/21", None),
]


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_birthday_route_needs_a_session(client, method, route, payload):
    assert client.request(method, route, json=payload).status_code == 401


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_birthday_route_refuses_a_non_staff_visitor(
    client, sign_in, method, route, payload
):
    sign_in(client, uid=1234, staff=False)
    assert client.request(method, route, json=payload).status_code == 403


async def test_a_birthday_is_stored_with_the_staff_source_and_logged(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    sign_in(client)

    response = client.put("/api/birthdays/21", json={"month": 3, "day": 4, "year": 1994})

    assert response.status_code == 200
    body = response.json()
    assert (body["month"], body["day"], body["year"]) == (3, 4, 1994)
    assert body["user_name"] == "Ada" and body["source"] == "staff"
    assert body["when"]
    stored = await get_birthday(web.db, 21)
    assert (stored["month"], stored["day"], stored["source"]) == (3, 4, "staff")
    assert "web.birthday.set" in await wf.kinds_in(web.db)


async def test_the_list_is_ordered_by_month_and_day(client, sign_in, web, guild, wf):
    wf.member(guild, 21, name="ada")
    wf.member(guild, 22, name="grace")
    sign_in(client)
    client.put("/api/birthdays/21", json={"month": 12, "day": 1})
    client.put("/api/birthdays/22", json={"month": 1, "day": 9})

    rows = client.get("/api/birthdays").json()

    assert [row["user_id"] for row in rows] == ["22", "21"]
    assert [row["month"] for row in rows] == [1, 12]


def test_a_date_that_does_not_exist_is_refused_with_the_reason(client, sign_in):
    sign_in(client)

    response = client.put("/api/birthdays/21", json={"month": 2, "day": 31})

    assert response.status_code == 400
    assert response.json()["error"] == "bad_date"
    assert "February" in response.json()["message"]


def test_a_birth_year_out_of_range_is_refused(client, sign_in):
    sign_in(client)
    response = client.put("/api/birthdays/21", json={"month": 2, "day": 3, "year": 1066})
    assert response.status_code == 400
    assert response.json()["error"] == "bad_year"


def test_a_birthday_with_no_date_at_all_says_so(client, sign_in):
    sign_in(client)
    response = client.put("/api/birthdays/21", json={})
    assert response.status_code == 400
    assert "month and a day" in response.json()["message"]


async def test_removing_a_birthday_says_so_and_refuses_when_there_is_none(
    client, sign_in, web, wf
):
    sign_in(client)
    client.put("/api/birthdays/21", json={"month": 3, "day": 4})

    response = client.delete("/api/birthdays/21")

    assert response.json() == {"removed": True, "user_id": "21"}
    assert await get_birthday(web.db, 21) is None
    assert "web.birthday.clear" in await wf.kinds_in(web.db)

    again = client.delete("/api/birthdays/21")
    assert again.status_code == 404 and "nothing to remove" in again.json()["message"]


def test_a_member_id_that_is_not_a_number_is_a_sentence(client, sign_in):
    sign_in(client)
    assert client.put("/api/birthdays/nobody", json={"month": 3, "day": 4}).status_code == 400
    assert client.delete("/api/birthdays/nobody").status_code == 400
