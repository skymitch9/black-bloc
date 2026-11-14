from __future__ import annotations

import json

import pytest

from black_bloc import rolegrants as grants
from black_bloc import timed_roles as timed
from black_bloc.cogs.community.role_menus import TITLE_MAX, get_menu

ADA, BO, CY = 900, 901, 902
RUNNER, HOST = 44, 45
LATER = "2099-02-28"

ROUTES = [
    ("GET", "/api/rolemenus", None),
    ("GET", "/api/rolemenus/btb", None),
    ("GET", "/api/rolemenus/marathons", None),
    ("GET", "/api/rolemenus/timed-roles", None),
    ("POST", "/api/rolemenus/timed-roles", {"role_id": "44"}),
    ("DELETE", "/api/rolemenus/timed-roles/44", None),
    ("POST", "/api/rolemenus", {"title": "Back to Black"}),
    ("PUT", "/api/rolemenus/btb", {"title": "Back to Black"}),
    ("DELETE", "/api/rolemenus/btb", None),
    ("POST", "/api/rolemenus/btb/attach", {"marathon_id": "1"}),
    ("POST", "/api/rolemenus/btb/end-now", None),
    ("POST", "/api/rolemenus/btb/end-earlier", None),
    ("POST", "/api/rolemenus/btb/list/preview", {"role_id": "44", "lines": "ada"}),
    ("POST", "/api/rolemenus/btb/list", {"role_id": "44", "user_ids": ["900"]}),
    ("GET", "/api/rolemenus/btb/fill", None),
    ("POST", "/api/rolemenus/btb/fill", None),
]

RETIRED = [
    ("POST", "/api/rolemenus/btb/post"),
    ("POST", "/api/rolemenus/btb/unpost"),
    ("POST", "/api/rolemenus/btb/assign"),
    ("GET", "/api/rolemenus/requests"),
    ("POST", "/api/rolemenus/requests/1/approve"),
    ("POST", "/api/rolemenus/requests/1/deny"),
    ("POST", "/api/rolemenus/seed"),
]


@pytest.fixture
def roles(guild, wf):
    """Two roles of their own, so the fakes' default Member role stays out of every count."""
    for role_id, name in ((RUNNER, "Runner"), (HOST, "Host")):
        if guild.get_role(role_id) is None:
            guild.roles.append(wf.Role(role_id, name, position=1))
    return guild


def wearing(guild, user_id, *role_ids):
    member = guild.get_member(user_id)
    member.roles = [*member.roles, *(guild.get_role(one) for one in role_ids)]
    return member


def role_ids_of(member):
    return [role.id for role in member.roles]


def listed(client, *role_ids):
    for role_id in role_ids:
        assert client.post("/api/rolemenus/timed-roles", json={"role_id": str(role_id)}).is_success


def an_event(client, title="Back to Black", **body):
    response = client.post("/api/rolemenus", json={"title": title, **body})
    assert response.status_code == 200, response.json()
    return response.json()


def give(client, event, role_id, *user_ids, remove=False):
    return client.post(
        f"/api/rolemenus/{event['name']}/list",
        json={
            "role_id": str(role_id),
            "user_ids": [str(one) for one in user_ids],
            "remove": remove,
        },
    )


async def a_marathon(web, wf, ends_at="2099-02-28T05:00:00+00:00", name="Back to Black 2027"):
    cur = await web.db.conn.execute(
        "INSERT INTO marathons(guild_id, name, source, source_ref, schedule_url, added_by, "
        "added_at, ends_at) VALUES (?, ?, 'gdq', ?, ?, 1, '2026-01-01T00:00:00+00:00', ?)",
        (wf.GUILD_ID, name, name, f"https://{name.replace(' ', '')}", ends_at),
    )
    await web.db.conn.commit()
    return cur.lastrowid


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_timed_roles_route_needs_a_staff_session(client, sign_in, method, route, payload):
    assert client.request(method, route, json=payload).status_code == 401
    sign_in(client, uid=1234, staff=False)
    refused = client.request(method, route, json=payload)
    assert refused.status_code == 403 and refused.json()["error"] == "not_staff"


@pytest.mark.parametrize(("method", "route"), RETIRED)
def test_every_retired_route_answers_410_in_words(client, sign_in, method, route):
    sign_in(client)

    response = client.request(method, route, json={})

    assert response.status_code == 410
    body = response.json()
    assert body["error"] == "rolemenu_retired"
    assert "Give roles…" in body["message"] and "Give from a list…" in body["message"]


async def test_the_timed_list_is_read_added_to_and_removed_from(client, sign_in, web, roles, wf):
    sign_in(client)
    wf.member(roles, ADA, name="ada")
    wearing(roles, ADA, RUNNER)

    added = client.post("/api/rolemenus/timed-roles", json={"role_id": str(RUNNER)})

    assert added.status_code == 200, added.json()
    assert added.json() | {"added_at": None} == {
        "role_id": str(RUNNER),
        "label": "Runner",
        "emoji": None,
        "position": 0,
        "role_name": "Runner",
        "wearing": 1,
        "assigned": 0,
        "removable": True,
        "added_by": "7",
        "added_at": None,
    }
    named = client.post("/api/rolemenus/timed-roles", json={"role_id": str(HOST), "label": "Hosts"})
    assert named.json()["label"] == "Hosts"
    assert [row["role_id"] for row in client.get("/api/rolemenus/timed-roles").json()] == [
        str(RUNNER),
        str(HOST),
    ]
    assert client.delete(f"/api/rolemenus/timed-roles/{HOST}").json() == {
        "removed": True,
        "role_id": str(HOST),
    }
    assert await timed.role_ids(web.db, wf.GUILD_ID) == [RUNNER]
    kinds = await wf.kinds_in(web.db)
    assert kinds.count("web.role_menu.option_added") == 2
    assert kinds.count("web.role_menu.option_removed") == 1


async def test_each_refusal_of_the_timed_list_has_its_own_code_and_sentence(
    client, sign_in, web, roles, wf
):
    sign_in(client)
    listed(client, RUNNER)
    roles.get_role(HOST).managed = True
    await web.store.set(wf.GUILD_ID, "golive_ping_role_id", wf.ADMIN_ROLE_ID, by=7)
    event = an_event(client)
    wf.member(roles, ADA, name="ada")
    web.guard = None
    give(client, event, RUNNER, ADA)

    for body, status, code, words in (
        ({"role_id": "4242"}, 404, "no_such_role", "not a role in this server"),
        ({"role_id": str(HOST)}, 409, "cannot_strip", "could not take **Host** off"),
        ({"role_id": str(wf.ADMIN_ROLE_ID)}, 409, "pings_role", "belongs to `/pings`"),
        ({"role_id": str(RUNNER)}, 409, "already_timed", "already a timed role"),
    ):
        refused = client.post("/api/rolemenus/timed-roles", json=body)
        assert (refused.status_code, refused.json()["error"]) == (status, code), body
        assert words in refused.json()["message"], body
    held = client.delete(f"/api/rolemenus/timed-roles/{RUNNER}")
    assert held.status_code == 409 and held.json()["error"] == "role_assigned"
    assert "still assigned 1 time(s)" in held.json()["message"]
    gone = client.delete(f"/api/rolemenus/timed-roles/{HOST}")
    assert gone.status_code == 404 and gone.json()["error"] == "not_timed"


async def test_a_new_event_from_a_name_and_date_or_from_a_marathon(client, sign_in, web, roles, wf):
    sign_in(client)
    marathon_id = await a_marathon(web, wf)

    dated = an_event(client, "Back to Black", ends_at=LATER)
    following = an_event(client, "", marathon_id=str(marathon_id))
    bare = an_event(client, "Volunteers")

    assert dated["name"] == "back-to-black" and dated["ends_source"] == "date"
    assert dated["end_label"].startswith("ends 2099-02-28")
    assert "(date, no marathon)" in dated["end_label"]
    assert dated["can_attach"] is True and dated["can_fill"] is False
    assert following["title"] == "Back to Black 2027" and following["ends_source"] == "marathon"
    assert following["marathon_name"] == "Back to Black 2027"
    assert following["ends_at"] == "2099-03-01T05:00:00+00:00"
    assert following["can_attach"] is False
    assert bare["end_label"] == "no end set" and bare["open"] is True
    assert "<t:" not in dated["end_label"] + following["end_label"]
    assert [row["name"] for row in client.get("/api/rolemenus").json()] == [
        "back-to-black-2027",
        "back-to-black",
        "volunteers",
    ]
    [choice] = client.get("/api/rolemenus/marathons").json()
    assert (choice["event"], choice["event_title"]) == ("back-to-black-2027", "Back to Black 2027")


async def test_a_new_event_the_site_gets_wrong_is_refused_in_words_and_makes_nothing(
    client, sign_in, web, roles, wf
):
    sign_in(client)
    marathon_id = await a_marathon(web, wf)
    an_event(client, "Taken", marathon_id=str(marathon_id))
    before = await wf.kinds_in(web.db)

    for body, status, code in (
        ({"title": ""}, 400, "needs_name"),
        ({"title": "t" * (TITLE_MAX + 1)}, 400, "too_long"),
        ({"title": "Late", "ends_at": "2020-01-01"}, 400, "past_date"),
        ({"title": "Soon", "ends_at": "soon"}, 400, "bad_date"),
        ({"title": "Ghost", "marathon_id": "4242"}, 404, "no_such_marathon"),
        ({"title": "Again", "marathon_id": str(marathon_id)}, 409, "marathon_taken"),
    ):
        refused = client.post("/api/rolemenus", json=body)
        assert (refused.status_code, refused.json()["error"]) == (status, code), body
        assert refused.json()["message"], body
    assert await wf.kinds_in(web.db) == before
    again = client.post("/api/rolemenus", json={"title": "Again", "marathon_id": str(marathon_id)})
    assert "one event per marathon" in again.json()["message"]


async def test_an_event_row_counts_who_is_assigned_per_role_and_the_last_pass(
    client, sign_in, web, roles, wf
):
    sign_in(client)
    listed(client, RUNNER, HOST)
    event = an_event(client, ends_at=LATER)
    for user_id, name in ((ADA, "ada"), (BO, "bo")):
        wf.member(roles, user_id, name=name)
    web.guard = None
    give(client, event, RUNNER, ADA, BO)
    give(client, event, HOST, ADA)

    row = client.get(f"/api/rolemenus/{event['name']}").json()

    assert row["assigned"] == 2
    assert row["assigned_by_role"] == [
        {"role_id": str(RUNNER), "label": "Runner", "count": 2},
        {"role_id": str(HOST), "label": "Host", "count": 1},
    ]
    assert row["last_pass"] == {"passes": 0, "members": 0, "failures": 0, "ended_at": None}
    assert row["end_now_question"] == (
        "Take 2 role(s) off 2 people now? 0 keep a role through another event."
    )
    assert row["buffer_default"] == 1 and row["ends_set_by"] == "7"


async def test_a_put_renames_the_event_and_sets_the_end_with_one_row_each(
    client, sign_in, web, roles, wf
):
    sign_in(client)
    event = an_event(client)
    before = len(await wf.kinds_in(web.db))

    renamed = client.put(f"/api/rolemenus/{event['name']}", json={"title": "BtB 2027"}).json()
    dated = client.put(
        f"/api/rolemenus/{event['name']}", json={"ends_source": "date", "ends_at": LATER}
    ).json()

    assert renamed["title"] == "BtB 2027" and renamed["name"] == "back-to-black"
    assert dated["ends_source"] == "date" and dated["ends_at"].startswith("2099-")
    assert (await wf.kinds_in(web.db))[before:] == ["web.role_menu.edit", "web.role_menu.end_set"]
    moved = client.put(f"/api/rolemenus/{event['name']}", json={"options": []})
    assert moved.status_code == 410 and moved.json()["error"] == "options_moved"


async def test_an_end_the_site_gets_wrong_is_refused_by_cause_and_writes_nothing(
    client, sign_in, web, roles, wf
):
    sign_in(client)
    event = an_event(client)
    before = await wf.kinds_in(web.db)
    for body, status, code in (
        ({"ends_source": "date", "ends_at": "2020-01-01"}, 400, "past_date"),
        ({"ends_source": "date", "ends_at": "soon"}, 400, "bad_date"),
        ({"ends_source": "marathon", "ends_marathon_id": "4242"}, 404, "no_such_marathon"),
        ({"ends_source": "sometimes"}, 400, "bad_end_source"),
        ({"buffer_days": 3}, 400, "buffer_needs_marathon"),
    ):
        response = client.put(f"/api/rolemenus/{event['name']}", json=body)
        assert (response.status_code, response.json()["error"]) == (status, code), body
        assert response.json()["message"]
    assert await wf.kinds_in(web.db) == before
    assert (await get_menu(web.db, wf.GUILD_ID, event["name"]))["ends_source"] == "none"
    for method, route in (
        ("GET", "/api/rolemenus/ghost"),
        ("PUT", "/api/rolemenus/ghost"),
        ("DELETE", "/api/rolemenus/ghost"),
        ("POST", "/api/rolemenus/ghost/end-now"),
        ("POST", "/api/rolemenus/ghost/attach"),
    ):
        response = client.request(method, route, json={})
        assert response.status_code == 404, route
        assert "no event called **ghost**" in response.json()["message"], route


async def test_a_put_that_turns_a_dated_event_to_a_marathon_attaches_and_holds_an_earlier_end(
    client, sign_in, web, roles, wf
):
    sign_in(client)
    marathon_id = await a_marathon(web, wf, ends_at="2099-01-10T05:00:00+00:00")
    event = an_event(client, ends_at=LATER)

    row = client.put(
        f"/api/rolemenus/{event['name']}",
        json={"ends_source": "marathon", "ends_marathon_id": str(marathon_id), "buffer_days": 3},
    ).json()

    assert row["ends_source"] == "marathon" and row["ends_at"] == event["ends_at"]
    assert row["ends_held_at"] == "2099-01-13T05:00:00+00:00" and row["buffer_days"] == 3
    assert row["held_question"].startswith("Use **Back to Black**'s earlier end?")
    assert (await wf.kinds_in(web.db)).count("web.role_menu.end_set") == 2
    taken = client.post(f"/api/rolemenus/{event['name']}/end-earlier").json()
    assert taken["ends_at"] == "2099-01-13T05:00:00+00:00" and taken["ends_held_at"] is None
    assert "role_menu.end_held" in await wf.kinds_in(web.db)


async def test_a_put_that_follows_a_later_marathon_keeps_the_buffer_it_was_given(
    client, sign_in, web, roles, wf
):
    sign_in(client)
    marathon_id = await a_marathon(web, wf, ends_at="2099-03-10T05:00:00+00:00")
    event = an_event(client, ends_at=LATER)

    row = client.put(
        f"/api/rolemenus/{event['name']}",
        json={"ends_source": "marathon", "ends_marathon_id": str(marathon_id), "buffer_days": 3},
    ).json()

    assert row["ends_at"] == "2099-03-13T05:00:00+00:00" and row["buffer_days"] == 3
    assert (await wf.kinds_in(web.db)).count("web.role_menu.end_set") == 2
    again = client.put(f"/api/rolemenus/{event['name']}", json={"buffer_days": ""}).json()
    assert again["buffer_days"] is None and again["ends_at"] == "2099-03-11T05:00:00+00:00"


async def test_attach_follows_a_later_marathon_and_refuses_by_cause(
    client, sign_in, web, roles, wf
):
    sign_in(client)
    later = await a_marathon(web, wf, ends_at="2099-03-10T05:00:00+00:00")
    other = await a_marathon(web, wf, name="Fall Fest")
    event = an_event(client, ends_at=LATER)
    an_event(client, "Fall crew", marathon_id=str(other))
    route = f"/api/rolemenus/{event['name']}/attach"

    taken = client.post(route, json={"marathon_id": other})
    ghost = client.post(route, json={"marathon_id": 4242})
    row = client.post(route, json={"marathon_id": later}).json()
    again = client.post(route, json={"marathon_id": later})

    assert (taken.status_code, taken.json()["error"]) == (409, "marathon_taken")
    assert "**Fall crew**" in taken.json()["message"]
    assert (ghost.status_code, ghost.json()["error"]) == (404, "no_such_marathon")
    assert row["ends_at"] == "2099-03-11T05:00:00+00:00" and row["ends_held_at"] is None
    assert (again.status_code, again.json()["error"]) == (409, "already_follows")


async def test_a_list_preview_matches_names_mentions_ids_and_ticks_and_writes_nothing(
    client, sign_in, web, roles, wf
):
    sign_in(client)
    listed(client, RUNNER)
    event = an_event(client, ends_at=LATER)
    wf.member(roles, ADA, name="ada")
    wf.member(roles, BO, name="sam")
    wf.member(roles, CY, name="cy").display_name = "Sam"
    web.guard = None
    give(client, event, RUNNER, CY)
    before = await wf.kinds_in(web.db)

    found = client.post(
        f"/api/rolemenus/{event['name']}/list/preview",
        json={
            "role_id": str(RUNNER),
            "lines": f"ADA\n<@{CY}>\nsam\nnobody\n\nada",
            "user_ids": [str(ADA)],
        },
    ).json()

    assert [(one["user_id"], one["typed"], one["note"]) for one in found["matched"]] == [
        (str(ADA), "ADA", None),
        (str(CY), f"<@{CY}>", "already"),
    ]
    assert found["unmatched"] == [
        {"typed": "sam", "why": "ambiguous"},
        {"typed": "nobody", "why": "unknown"},
    ]
    assert found["to_save"] == [str(ADA)] and found["role_name"] == "Runner"
    assert await wf.kinds_in(web.db) == before
    menu = await get_menu(web.db, wf.GUILD_ID, event["name"])
    assert await timed.event_grant(web.db, wf.GUILD_ID, ADA, RUNNER, menu["id"]) is None


async def test_a_list_save_gives_with_source_site_list_and_take_off_reverses_it(
    client, sign_in, web, roles, wf
):
    sign_in(client)
    listed(client, RUNNER)
    event = an_event(client, ends_at=LATER)
    ada = wf.member(roles, ADA, name="ada")
    bo = wf.member(roles, BO, name="bo")
    web.guard = None

    given = give(client, event, RUNNER, ADA, BO, 4242).json()

    assert (given["given"], given["refused"], given["gone"]) == (2, 0, ["4242"])
    assert "**Runner**: given to 2" in given["message"]
    assert given["event"]["assigned"] == 2
    assert RUNNER in role_ids_of(ada) and RUNNER in role_ids_of(bo)
    menu = await get_menu(web.db, wf.GUILD_ID, event["name"])
    row = await timed.event_grant(web.db, wf.GUILD_ID, ADA, RUNNER, menu["id"])
    assert row["source"] == grants.SITE_LIST and row["expires_at"] == menu["ends_at"]
    assert "web.role_menu.assign" in await wf.kinds_in(web.db)

    taken = give(client, event, RUNNER, ADA, remove=True).json()

    assert taken["given"] == 1 and "taken off 1" in taken["message"]
    assert RUNNER not in role_ids_of(ada) and RUNNER in role_ids_of(bo)
    assert "web.role_menu.unassign" in await wf.kinds_in(web.db)


async def test_a_list_is_refused_by_cause_before_anything_is_written(
    client, sign_in, web, roles, wf
):
    sign_in(client)
    listed(client, RUNNER)
    event = an_event(client, ends_at=LATER)
    wf.member(roles, ADA, name="ada")
    web.guard = wf.Guard(wf.TEST_CHANNEL_ID)
    before = await wf.kinds_in(web.db)
    route = f"/api/rolemenus/{event['name']}/list"
    too_many = "\n".join(f"person{n}" for n in range(501))

    for path, body, status, code in (
        ("/preview", {"role_id": str(RUNNER), "lines": "\n  \n"}, 400, "nobody_named"),
        ("/preview", {"role_id": str(RUNNER), "lines": too_many}, 400, "list_too_long"),
        ("/preview", {"role_id": str(HOST), "lines": "ada"}, 409, "not_timed"),
        ("/preview", {"role_id": "4242", "lines": "ada"}, 404, "no_such_role"),
        ("", {"role_id": str(RUNNER), "user_ids": []}, 400, "nobody_named"),
        ("", {"role_id": str(RUNNER), "user_ids": [str(ADA)]}, 409, "test_mode"),
    ):
        refused = client.post(route + path, json=body)
        assert (refused.status_code, refused.json()["error"]) == (status, code), (path, code)
        assert refused.json()["message"]
    assert await wf.kinds_in(web.db) == before
    await web.db.conn.execute("UPDATE role_menus SET ended_at = '2020-01-01T00:00:00+00:00'")
    await web.db.conn.commit()
    web.guard = None
    ended = client.post(route, json={"role_id": str(RUNNER), "user_ids": [str(ADA)]})
    assert (ended.status_code, ended.json()["error"]) == (409, "event_ended")


async def schedule(web, marathon_id, people):
    await web.db.conn.execute(
        "INSERT INTO marathon_runs(marathon_id, external_id, game, people, scheduled_at, "
        "first_seen_at, last_seen_at) VALUES (?, 'r1', 'Game', ?, '2099-01-01T00:00:00+00:00', "
        "'2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')",
        (marathon_id, json.dumps(people)),
    )
    await web.db.conn.commit()


async def test_fill_previews_counts_and_unmatched_names_then_gives_only_the_missing(
    client, sign_in, web, roles, wf
):
    sign_in(client)
    listed(client, RUNNER)
    await web.store.set(wf.GUILD_ID, "rolemenu_fill_runner_role_id", RUNNER, by=7)
    marathon_id = await a_marathon(web, wf)
    await schedule(
        web,
        marathon_id,
        [
            {"name": "Ada", "part": "runner", "user_id": ADA},
            {"name": "Stranger", "part": "runner"},
            {"name": "Hosty", "part": "host", "user_id": BO},
        ],
    )
    ada = wf.member(roles, ADA, name="ada")
    wf.member(roles, BO, name="bo")
    event = an_event(client, "", marathon_id=str(marathon_id))
    before = await wf.kinds_in(web.db)

    preview = client.get(f"/api/rolemenus/{event['name']}/fill").json()

    runner = next(one for one in preview["lines"] if one["part"] == "runner")
    host = next(one for one in preview["lines"] if one["part"] == "host")
    assert (runner["role_id"], runner["role_name"], runner["timed"]) == (
        str(RUNNER),
        "Runner",
        True,
    )
    assert (runner["matched"], runner["missing"], runner["unmatched"]) == (1, 1, ["Stranger"])
    assert (host["role_id"], host["setting"]) == (None, "rolemenu_fill_host_role_id")
    assert preview["missing"] == 1 and preview["marathon_name"] == "Back to Black 2027"
    assert await wf.kinds_in(web.db) == before

    web.guard = wf.Guard(wf.TEST_CHANNEL_ID)
    guarded = client.post(f"/api/rolemenus/{event['name']}/fill")
    assert (guarded.status_code, guarded.json()["error"]) == (409, "test_mode")
    web.guard = None
    done = client.post(f"/api/rolemenus/{event['name']}/fill").json()
    assert done["given"] == 1 and "1 given" in done["message"]
    assert RUNNER in role_ids_of(ada)
    again = client.post(f"/api/rolemenus/{event['name']}/fill").json()
    assert again["given"] == 0 and "nothing was given" in again["message"]

    dated = an_event(client, "Dated", ends_at=LATER)
    refused = client.get(f"/api/rolemenus/{dated['name']}/fill")
    assert (refused.status_code, refused.json()["error"]) == (409, "no_marathon")


async def test_end_now_takes_the_roles_off_everyone_not_kept_and_the_question_says_so(
    client, sign_in, web, roles, wf
):
    sign_in(client)
    listed(client, RUNNER)
    event = an_event(client, ends_at=LATER)
    other = an_event(client, "Other", ends_at="2099-05-01")
    wf.member(roles, ADA, name="ada")
    ada = wearing(roles, ADA, RUNNER)
    bo = wf.member(roles, BO, name="bo")
    web.guard = None
    give(client, other, RUNNER, BO)

    asked = client.get(f"/api/rolemenus/{event['name']}").json()["end_now_question"]
    response = client.post(f"/api/rolemenus/{event['name']}/end-now")

    assert asked == "Take 1 role(s) off 1 people now? 1 keep a role through another event."
    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["pass"]["members"] == 1 and body["pass"]["ended"] is True
    assert "**Back to Black** ended" in body["message"]
    assert body["open"] is False and body["end_now_question"] is None
    assert RUNNER not in role_ids_of(ada) and RUNNER in role_ids_of(bo)
    assert "web.role_menu.ended" in await wf.kinds_in(web.db)


async def test_end_now_under_the_guard_is_the_guards_409(client, sign_in, web, roles, wf):
    sign_in(client)
    event = an_event(client)
    web.guard = wf.Guard(wf.TEST_CHANNEL_ID)

    response = client.post(f"/api/rolemenus/{event['name']}/end-now")

    assert response.status_code == 409 and response.json()["error"] == "test_mode"
    assert (await get_menu(web.db, wf.GUILD_ID, event["name"]))["ended_at"] is None


async def test_use_the_earlier_end_takes_a_held_end_and_refuses_when_none_waits(
    client, sign_in, web, roles, wf
):
    sign_in(client)
    marathon_id = await a_marathon(web, wf)
    event = an_event(client, "", marathon_id=str(marathon_id))
    menu = await get_menu(web.db, wf.GUILD_ID, event["name"])

    nothing = client.post(f"/api/rolemenus/{event['name']}/end-earlier")
    assert nothing.status_code == 409 and nothing.json()["error"] == "nothing_held"

    await web.db.conn.execute(
        "UPDATE marathons SET ends_at = '2099-02-20T05:00:00+00:00' WHERE id = ?", (marathon_id,)
    )
    await web.db.conn.execute(
        "UPDATE role_menus SET ends_held_at = '2099-02-21T05:00:00+00:00' WHERE id = ?",
        (menu["id"],),
    )
    await web.db.conn.commit()
    held = client.get(f"/api/rolemenus/{event['name']}").json()
    assert held["held_label"].startswith("2099-02-2") and "<t:" not in held["held_question"]

    row = client.post(f"/api/rolemenus/{event['name']}/end-earlier").json()

    assert row["ends_at"] == "2099-02-21T05:00:00+00:00" and row["ends_held_at"] is None
    assert "web.role_menu.end_set" in await wf.kinds_in(web.db)


async def test_an_event_still_to_end_is_not_deleted_while_people_are_assigned(
    client, sign_in, web, roles, wf
):
    sign_in(client)
    listed(client, RUNNER)
    event = an_event(client, ends_at=LATER)
    wf.member(roles, ADA, name="ada")
    web.guard = None
    give(client, event, RUNNER, ADA)

    refused = client.delete(f"/api/rolemenus/{event['name']}")

    assert refused.status_code == 409 and refused.json()["error"] == "menu_still_ends"
    assert "End it now" in refused.json()["message"]
    client.put(f"/api/rolemenus/{event['name']}", json={"ends_source": "none"})
    assert client.delete(f"/api/rolemenus/{event['name']}").json() == {
        "deleted": True,
        "name": event["name"],
    }


async def test_the_marathon_row_names_the_events_that_end_with_it(
    client, sign_in, web, guild, roles, wf
):
    from black_bloc.cogs.community.role_menus import menus_ending_with

    sign_in(client)
    listed(client, RUNNER)
    marathon_id = await a_marathon(web, wf)
    assert await menus_ending_with(web, guild, marathon_id) == []
    event = an_event(client, "BtB crew", marathon_id=str(marathon_id))
    wf.member(roles, ADA, name="ada")
    web.guard = None
    give(client, event, RUNNER, ADA)

    [line] = await menus_ending_with(web, guild, marathon_id)

    assert line == {"name": "btb-crew", "title": "BtB crew", "roles": 1, "assigned": 1}
    await web.db.conn.execute("UPDATE role_menus SET ended_at = '2099-01-01T00:00:00+00:00'")
    await web.db.conn.commit()
    assert await menus_ending_with(web, guild, marathon_id) == []


async def test_end_now_never_takes_a_role_pings_owns_even_one_set_on_the_list_by_hand(
    client, sign_in, web, roles, wf
):
    """§7.3.3: the pass skips `/pings` roles, however a role came to sit on the timed list."""
    from black_bloc import pings

    sign_in(client)
    listed(client, RUNNER)
    event = an_event(client)
    wf.member(roles, ADA, name="ada")
    member = wearing(roles, ADA, RUNNER)
    await pings.set_fan_role(web.db, wf.GUILD_ID, ADA, RUNNER, 7)
    web.guard = None

    response = client.post(f"/api/rolemenus/{event['name']}/end-now")

    assert response.status_code == 200, response.json()
    assert response.json()["pass"]["members"] == 0
    assert RUNNER in role_ids_of(member)


async def test_a_put_to_a_marathon_another_open_event_follows_is_refused_in_words(
    client, sign_in, web, roles, wf
):
    sign_in(client)
    marathon_id = await a_marathon(web, wf)
    an_event(client, "Taken", marathon_id=str(marathon_id))
    event = an_event(client, ends_at=LATER)
    before = await wf.kinds_in(web.db)

    refused = client.put(
        f"/api/rolemenus/{event['name']}",
        json={"ends_source": "marathon", "ends_marathon_id": str(marathon_id)},
    )

    assert (refused.status_code, refused.json()["error"]) == (409, "marathon_taken")
    assert "**Taken**" in refused.json()["message"]
    assert await wf.kinds_in(web.db) == before


async def test_end_now_on_an_event_somebody_already_ended_is_refused_and_runs_nothing(
    client, sign_in, web, roles, wf
):
    sign_in(client)
    listed(client, RUNNER)
    event = an_event(client, ends_at=LATER)
    web.guard = None
    assert client.post(f"/api/rolemenus/{event['name']}/end-now").status_code == 200
    wf.member(roles, ADA, name="ada")
    member = wearing(roles, ADA, RUNNER)
    before = await wf.kinds_in(web.db)

    again = client.post(f"/api/rolemenus/{event['name']}/end-now")

    assert (again.status_code, again.json()["error"]) == (409, "event_ended")
    assert RUNNER in role_ids_of(member)
    assert await wf.kinds_in(web.db) == before
