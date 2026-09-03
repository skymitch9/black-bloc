from __future__ import annotations

import pytest

from black_bloc import applications as forms
from black_bloc import rolegrants as grants

MEMBER = 900

ROUTES = [
    ("GET", "/api/applications/status", None),
    ("GET", "/api/applications/forms", None),
    ("POST", "/api/applications/forms", {"name": "team", "title": "Team", "role_id": "22"}),
    ("PATCH", "/api/applications/forms/1", {"title": "Team"}),
    ("DELETE", "/api/applications/forms/1", None),
    ("PUT", "/api/applications/forms/1/questions", {"questions": []}),
    ("POST", "/api/applications/forms/1/panel", {"channel_id": "500"}),
    ("GET", "/api/applications", None),
    ("GET", "/api/applications/1", None),
    ("POST", "/api/applications/1/decide", {"status": "approved"}),
]


def call(client, method, route, payload):
    return client.request(method, route, json=payload)


async def applications_on(web, wf) -> None:
    await web.store.set(wf.GUILD_ID, forms.MODE_KEY, "on")
    await web.store.set(wf.GUILD_ID, "staff_channel_id", wf.TEST_CHANNEL_ID)


def a_form(client, wf, name: str = "twitch-team") -> dict:
    return client.post(
        "/api/applications/forms",
        json={
            "name": name,
            "title": "Twitch Team",
            "description": "join the Team",
            "role_id": str(wf.PLAIN_ROLE_ID),
        },
    ).json()


async def an_application(web, wf, form_id: int, user_id: int = MEMBER) -> int:
    return await forms.create_application(
        web.db,
        wf.GUILD_ID,
        form_id,
        user_id,
        forms.answers_json([("Twitch handle", "ada")]),
    )


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_application_route_needs_a_session(client, method, route, payload):
    response = call(client, method, route, payload)
    assert response.status_code == 401
    assert response.json()["error"] == "not_signed_in"


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_application_route_refuses_a_non_staff_visitor(
    client, sign_in, method, route, payload
):
    sign_in(client, uid=1234, staff=False)
    response = call(client, method, route, payload)
    assert response.status_code == 403
    assert response.json()["error"] == "not_staff"


async def test_a_form_is_created_listed_and_logged(client, sign_in, web, wf):
    sign_in(client)

    made = a_form(client, wf)

    assert made["name"] == "twitch-team" and made["open"] is True
    assert made["role_id"] == str(wf.PLAIN_ROLE_ID) and made["questions"] == []
    assert made["pending"] == 0
    listed = client.get("/api/applications/forms").json()
    assert [row["name"] for row in listed] == ["twitch-team"]
    assert "web.application.form_created" in await wf.kinds_in(web.db)


def test_a_form_needs_a_name_a_heading_and_a_role(client, sign_in, wf):
    sign_in(client)

    response = client.post("/api/applications/forms", json={"name": "team"})

    assert response.status_code == 400
    assert "needs a short name" in response.json()["message"]


def test_a_form_name_that_is_not_a_slug_is_refused_in_the_same_words(client, sign_in, wf):
    sign_in(client)

    response = client.post(
        "/api/applications/forms",
        json={"name": "Twitch Team", "title": "Team", "role_id": str(wf.PLAIN_ROLE_ID)},
    )

    assert response.status_code == 400
    assert "lower-case letters" in response.json()["message"]


def test_a_second_form_with_the_same_name_is_refused_with_a_sentence(client, sign_in, wf):
    sign_in(client)
    a_form(client, wf)

    response = client.post(
        "/api/applications/forms",
        json={"name": "twitch-team", "title": "Again", "role_id": str(wf.PLAIN_ROLE_ID)},
    )

    assert response.status_code == 400
    assert "already has an application form" in response.json()["message"]


def test_a_role_the_bot_cannot_hand_out_is_refused_by_name(client, sign_in, wf, guild):
    sign_in(client)
    managed = wf.Role(77, "Booster", managed=True)
    guild.roles.append(managed)

    response = client.post(
        "/api/applications/forms",
        json={"name": "team", "title": "Team", "role_id": str(managed.id)},
    )

    assert response.status_code == 400
    assert "cannot hand out **Booster**" in response.json()["message"]


async def test_a_form_is_edited_field_by_field_and_the_change_is_logged(
    client, sign_in, web, wf
):
    sign_in(client)
    made = a_form(client, wf)

    response = client.patch(
        f"/api/applications/forms/{made['id']}",
        json={
            "title": "The Twitch Team",
            "owner_user_id": "7",
            "next_step": "the Team owner sends the invite",
            "expires_days": 0,
            "retry_days": 30,
            "open": False,
        },
    )

    body = response.json()
    assert body["title"] == "The Twitch Team" and body["owner_user_id"] == "7"
    assert body["next_step"] == "the Team owner sends the invite"
    assert body["retry_days"] == 30 and body["open"] is False
    assert "web.application.form_updated" in await wf.kinds_in(web.db)


def test_a_form_number_that_is_not_this_server_s_is_a_404_in_words(client, sign_in):
    sign_in(client)

    response = client.patch("/api/applications/forms/999", json={"title": "x"})

    assert response.status_code == 404
    assert "no application form with that number" in response.json()["message"]


async def test_the_whole_question_list_is_saved_at_once_and_capped_at_five(
    client, sign_in, web, wf
):
    sign_in(client)
    made = a_form(client, wf)

    body = client.put(
        f"/api/applications/forms/{made['id']}/questions",
        json={
            "questions": [
                {"label": "Twitch handle", "placeholder": "twitch.tv/…"},
                {"label": "Why the Team", "style": "long", "required": False},
            ]
        },
    ).json()

    assert [one["position"] for one in body["questions"]] == [1, 2]
    assert body["questions"][1] == {
        "position": 2,
        "label": "Why the Team",
        "style": "long",
        "required": False,
        "placeholder": None,
    }
    assert "web.application.question_changed" in await wf.kinds_in(web.db)

    too_many = client.put(
        f"/api/applications/forms/{made['id']}/questions",
        json={"questions": [{"label": f"Q{n}"} for n in range(6)]},
    )
    assert too_many.status_code == 400
    assert "at most 5 boxes" in too_many.json()["message"]


def test_questions_that_arrive_in_the_wrong_shape_are_refused_in_words(client, sign_in, wf):
    sign_in(client)
    made = a_form(client, wf)

    response = client.put(
        f"/api/applications/forms/{made['id']}/questions", json={"questions": "nope"}
    )

    assert response.status_code == 400
    assert "fault in the page" in response.json()["message"]


async def test_the_panel_is_posted_where_it_was_asked_for(client, sign_in, web, wf):
    sign_in(client)
    made = a_form(client, wf)

    body = client.post(
        f"/api/applications/forms/{made['id']}/panel",
        json={"channel_id": str(wf.TEST_CHANNEL_ID)},
    ).json()

    assert body["posted"] is True and body["channel_id"] == str(wf.TEST_CHANNEL_ID)
    form = await forms.get_form_by_id(web.db, made["id"])
    assert str(form["panel_message_id"]) == body["message_id"]
    assert "web.application.panel_posted" in await wf.kinds_in(web.db)


def test_the_panel_refuses_a_channel_the_bot_cannot_see(client, sign_in, wf):
    sign_in(client)
    made = a_form(client, wf)

    response = client.post(
        f"/api/applications/forms/{made['id']}/panel", json={"channel_id": "12345"}
    )

    assert response.status_code == 400
    assert "not a channel Black Bloc can see" in response.json()["message"]


def test_the_panel_is_refused_while_test_mode_is_on(client, sign_in, web, wf):
    sign_in(client)
    made = a_form(client, wf)
    web.guard = wf.Guard(wf.TEST_CHANNEL_ID)

    response = client.post(
        f"/api/applications/forms/{made['id']}/panel",
        json={"channel_id": str(wf.OTHER_CHANNEL_ID)},
    )

    assert response.status_code == 409
    assert response.json()["error"] == "test_mode"


async def test_a_form_with_somebody_waiting_refuses_to_be_deleted(client, sign_in, web, wf):
    sign_in(client)
    made = a_form(client, wf)
    await an_application(web, wf, made["id"])

    response = client.delete(f"/api/applications/forms/{made['id']}")

    assert response.status_code == 409
    assert "still has 1 application(s) waiting" in response.json()["message"]
    assert client.get("/api/applications/forms").json()


async def test_an_empty_form_is_deleted_and_the_delete_is_logged(client, sign_in, web, wf):
    sign_in(client)
    made = a_form(client, wf)

    body = client.delete(f"/api/applications/forms/{made['id']}").json()

    assert body["deleted"] is True and body["name"] == "twitch-team"
    assert client.get("/api/applications/forms").json() == []
    assert "web.application.form_deleted" in await wf.kinds_in(web.db)


async def test_the_queue_carries_the_answers_and_who_asked(client, sign_in, web, wf):
    sign_in(client)
    wf.member(web.guild, MEMBER, name="ada")
    made = a_form(client, wf)
    application_id = await an_application(web, wf, made["id"])

    rows = client.get("/api/applications").json()

    assert [row["id"] for row in rows] == [application_id]
    assert rows[0]["form_name"] == "twitch-team" and rows[0]["status"] == grants.PENDING
    assert rows[0]["answers"] == [{"label": "Twitch handle", "answer": "ada"}]
    assert rows[0]["user_name"] == "Ada"


async def test_the_queue_filters_by_form_and_by_status(client, sign_in, web, wf):
    sign_in(client)
    one = a_form(client, wf)
    two = a_form(client, wf, name="mod-team")
    waiting = await an_application(web, wf, two["id"])
    settled = await an_application(web, wf, one["id"])
    await forms.decide_application(web.db, settled, grants.WITHDRAWN, decided_by=MEMBER)

    by_form = client.get(f"/api/applications?form={two['id']}").json()
    by_status = client.get("/api/applications?status=withdrawn").json()

    assert [row["id"] for row in by_form] == [waiting]
    assert [row["id"] for row in by_status] == [settled]


def test_a_status_that_is_not_a_state_is_refused_and_names_the_real_ones(client, sign_in):
    sign_in(client)

    response = client.get("/api/applications?status=maybe")

    assert response.status_code == 400
    assert "pending" in response.json()["message"]


async def test_one_application_is_read_back_by_number(client, sign_in, web, wf):
    sign_in(client)
    made = a_form(client, wf)
    application_id = await an_application(web, wf, made["id"])

    body = client.get(f"/api/applications/{application_id}").json()

    assert body["id"] == application_id and body["form_name"] == "twitch-team"
    assert client.get("/api/applications/9999").status_code == 404


async def test_approving_from_the_site_hands_the_role_over_and_logs_the_web_kind(
    client, sign_in, web, wf
):
    sign_in(client)
    await applications_on(web, wf)
    member = wf.member(web.guild, MEMBER, name="ada")
    member.roles = []
    made = a_form(client, wf)
    application_id = await an_application(web, wf, made["id"])

    body = client.post(
        f"/api/applications/{application_id}/decide", json={"status": "approved"}
    ).json()

    assert body["application"]["status"] == grants.APPROVED
    assert member.edits == [[wf.PLAIN_ROLE_ID]]
    grant = await grants.open_grant(web.db, wf.GUILD_ID, MEMBER, wf.PLAIN_ROLE_ID)
    assert grant is not None and body["application"]["grant_id"] == str(grant["id"])
    assert "web.application.approved" in await wf.kinds_in(web.db)


async def test_denying_from_the_site_needs_a_reason_and_sends_it(client, sign_in, web, wf):
    sign_in(client)
    await applications_on(web, wf)
    member = wf.member(web.guild, MEMBER, name="ada")
    made = a_form(client, wf)
    application_id = await an_application(web, wf, made["id"])

    blank = client.post(
        f"/api/applications/{application_id}/decide", json={"status": "denied"}
    )
    assert blank.status_code == 400 and "needs one line" in blank.json()["message"]

    body = client.post(
        f"/api/applications/{application_id}/decide",
        json={"status": "denied", "reason": "not enough hours yet"},
    ).json()

    assert body["application"]["deny_reason"] == "not enough hours yet"
    assert any("not enough hours yet" in said for said in member.dms)
    assert "web.application.denied" in await wf.kinds_in(web.db)


async def test_a_decision_that_is_not_approve_or_deny_is_refused_in_words(
    client, sign_in, web, wf
):
    sign_in(client)
    made = a_form(client, wf)
    application_id = await an_application(web, wf, made["id"])

    response = client.post(
        f"/api/applications/{application_id}/decide", json={"status": "maybe"}
    )

    assert response.status_code == 400
    assert "`approved` or `denied`" in response.json()["message"]


async def test_deciding_one_that_is_already_settled_answers_409_not_a_second_decision(
    client, sign_in, web, wf
):
    sign_in(client)
    await applications_on(web, wf)
    wf.member(web.guild, MEMBER, name="ada")
    made = a_form(client, wf)
    application_id = await an_application(web, wf, made["id"])
    client.post(f"/api/applications/{application_id}/decide", json={"status": "approved"})

    again = client.post(
        f"/api/applications/{application_id}/decide",
        json={"status": "denied", "reason": "too late"},
    )

    assert again.status_code == 409
    assert "already **approved**" in again.json()["message"]


async def test_the_status_route_counts_the_forms_and_the_queue(client, sign_in, web, wf):
    sign_in(client)
    await applications_on(web, wf)
    one = a_form(client, wf)
    two = a_form(client, wf, name="mod-team")
    client.patch(f"/api/applications/forms/{two['id']}", json={"open": False})
    await an_application(web, wf, one["id"])

    body = client.get("/api/applications/status").json()

    assert body == {
        "mode": "on",
        "forms": 2,
        "open_forms": 1,
        "pending": 1,
        "questions_max": forms.QUESTIONS_MAX,
    }
