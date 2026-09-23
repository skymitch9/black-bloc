from __future__ import annotations

import pytest

from black_bloc.birthdays import local_today
from black_bloc.cogs.community.birthdays import (
    COG_NAME,
    Birthdays,
    get_birthday,
    mark_announced,
    save_birthday,
)
from black_bloc.settings_store import BIRTHDAY_TZ

PARTY_CHANNEL = 501

ROUTES = [
    ("GET", "/api/birthdays", None),
    ("PUT", "/api/birthdays/21", {"month": 3, "day": 4}),
    ("POST", "/api/birthdays/21/optin", {"opted_in": False}),
    ("DELETE", "/api/birthdays/21", None),
    ("POST", "/api/birthdays/post-today", {"again": False}),
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


async def test_the_wished_toggle_turns_a_birthday_off_and_on_again(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    await save_birthday(web.db, wf.GUILD_ID, 21, 3, 4, None, "staff")
    sign_in(client)

    off = client.post("/api/birthdays/21/optin", json={"opted_in": False})
    assert off.status_code == 200
    assert off.json()["opted_in"] is False
    assert "says nothing" in off.json()["message"]

    on = client.post("/api/birthdays/21/optin", json={"opted_in": True})
    assert on.status_code == 200
    assert on.json()["opted_in"] is True
    assert bool((await get_birthday(web.db, 21))["opted_in"]) is True
    assert "web.birthday.optin" in await wf.kinds_in(web.db)


def test_the_wished_toggle_says_in_words_that_nobody_has_that_birthday(client, sign_in):
    sign_in(client)

    response = client.post("/api/birthdays/21/optin", json={"opted_in": False})

    assert response.status_code == 404
    assert "nothing to remove" in response.json()["message"]


async def birthday_today(web, wf, user_id):
    today = local_today(BIRTHDAY_TZ)
    await save_birthday(web.db, wf.GUILD_ID, user_id, today.month, today.day, None, "self")
    return today.isoformat()


@pytest.fixture
def loaded(web, monkeypatch):
    monkeypatch.setitem(web.cogs, COG_NAME, Birthdays(web))
    return web


async def test_posting_today_answers_every_count_and_logs_one_website_row(
    client, sign_in, loaded, guild, wf
):
    web = loaded
    wf.member(guild, 21, name="ada")
    wf.member(guild, 22, name="grace")
    await web.store.set(wf.GUILD_ID, "birthday_mode", "on")
    await web.store.set(wf.GUILD_ID, "birthday_channel_id", PARTY_CHANNEL)
    today = await birthday_today(web, wf, 21)
    await birthday_today(web, wf, 22)
    await mark_announced(web.db, 22, today)
    sign_in(client)

    response = client.post("/api/birthdays/post-today", json={"again": False})

    assert response.status_code == 200
    body = response.json()
    assert {key: body[key] for key in ("posted", "skipped", "missing", "failed", "mode")} == {
        "posted": 1,
        "skipped": 1,
        "missing": 0,
        "failed": 0,
        "mode": "on",
    }
    assert body["again"] is False
    assert "Posted 1 birthday wish(es) in #general." in body["said"]
    assert len(guild.get_channel(PARTY_CHANNEL).messages) == 1
    details = await wf.one_web_row(web.db, "web.birthday.posted_now")
    assert (details["posted"], details["again"], details["mode"]) == (1, False, "on")
    assert "birthday.announce" in await wf.kinds_in(web.db)


async def test_posting_them_all_again_from_the_site_wishes_the_wished_too(
    client, sign_in, loaded, guild, wf
):
    web = loaded
    wf.member(guild, 21, name="ada")
    await web.store.set(wf.GUILD_ID, "birthday_mode", "on")
    await web.store.set(wf.GUILD_ID, "birthday_channel_id", PARTY_CHANNEL)
    today = await birthday_today(web, wf, 21)
    await mark_announced(web.db, 21, today)
    sign_in(client)

    body = client.post("/api/birthdays/post-today", json={"again": True}).json()

    assert (body["posted"], body["skipped"], body["again"]) == (1, 0, True)


async def test_nobody_today_is_a_sentence_not_an_error(client, sign_in, loaded, wf):
    await loaded.store.set(wf.GUILD_ID, "birthday_mode", "on")
    sign_in(client)

    response = client.post("/api/birthdays/post-today", json={})

    assert response.status_code == 200
    assert "Nobody who is opted in has a birthday today" in response.json()["said"]


async def test_off_is_refused_with_the_words_saying_how_to_turn_it_on(
    client, sign_in, loaded, wf
):
    await loaded.store.set(wf.GUILD_ID, "birthday_mode", "off")
    sign_in(client)

    response = client.post("/api/birthdays/post-today", json={"again": False})

    assert response.status_code == 409
    assert response.json()["error"] == "birthdays_off"
    assert "birthday_mode" in response.json()["message"]


def test_posting_today_says_so_in_words_when_the_birthdays_cog_is_not_loaded(
    client, sign_in, web
):
    sign_in(client)

    response = client.post("/api/birthdays/post-today", json={"again": False})

    assert response.status_code == 503
    assert "birthdays part of Black Bloc is not loaded" in response.json()["message"]
