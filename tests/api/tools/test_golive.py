from __future__ import annotations

import pytest

from black_bloc.cogs.content.golive import get_link, is_opted_out, set_link, set_optout

ROUTES = [
    ("GET", "/api/golive/links"),
    ("POST", "/api/golive/links"),
    ("DELETE", "/api/golive/links/7"),
    ("GET", "/api/golive/optouts"),
    ("POST", "/api/golive/optouts"),
    ("DELETE", "/api/golive/optouts/7"),
    ("GET", "/api/golive/sessions"),
    ("GET", "/api/golive/preview"),
]


@pytest.mark.parametrize(("method", "route"), ROUTES)
def test_every_golive_route_needs_a_session(client, method, route):
    assert client.request(method, route).status_code == 401


@pytest.mark.parametrize(("method", "route"), ROUTES)
def test_every_golive_route_refuses_a_non_staff_visitor(client, sign_in, method, route):
    sign_in(client, uid=1234, staff=False)
    assert client.request(method, route).status_code == 403


async def test_links_come_back_with_the_member_name_resolved(client, sign_in, web, guild, wf):
    wf.member(guild, 21, name="ada")
    await set_link(web.db, 21, "adastreams", "t-1")
    sign_in(client)

    rows = client.get("/api/golive/links").json()

    assert rows[0]["user_id"] == "21"
    assert rows[0]["user_name"] == "Ada"
    assert rows[0]["twitch_login"] == "adastreams"


async def test_an_unlink_removes_the_row_and_leaves_a_web_line(client, sign_in, web, wf):
    await set_link(web.db, 21, "adastreams")
    sign_in(client)

    response = client.delete("/api/golive/links/21")

    assert response.json() == {"unlinked": True, "user_id": "21"}
    assert await get_link(web.db, 21) is None
    assert await wf.one_web_row(web.db, "web.golive.unlink") == {"via": wf.VIA_WEBSITE}
    assert await wf.kinds_in(web.db) == ["web.golive.unlink"]


def test_unlinking_somebody_who_is_not_linked_says_so(client, sign_in):
    sign_in(client)
    response = client.delete("/api/golive/links/21")
    assert response.status_code == 404
    assert "nothing to unlink" in response.json()["message"]


def test_an_id_that_is_not_a_number_is_a_sentence(client, sign_in):
    sign_in(client)
    response = client.delete("/api/golive/links/nobody")
    assert response.status_code == 400
    assert "nobody" in response.json()["message"]


async def test_optouts_and_sessions_are_listed_newest_first(client, sign_in, web, guild, wf):
    wf.member(guild, 21, name="ada")
    await set_optout(web.db, 21)
    for n in range(3):
        await web.db.conn.execute(
            "INSERT INTO golive_sessions(guild_id, user_id, source, started_at, ended_at, mode) "
            "VALUES (?, 21, 'twitch', ?, ?, 'on')",
            (
                wf.GUILD_ID,
                f"2026-08-2{n}T00:00:00+00:00",
                f"2026-08-2{n}T01:00:00+00:00",
            ),
        )
    await web.db.conn.commit()
    sign_in(client)

    optouts = client.get("/api/golive/optouts").json()
    sessions = client.get("/api/golive/sessions", params={"limit": 2}).json()

    assert optouts[0]["user_id"] == "21" and optouts[0]["user_name"] == "Ada"
    assert len(sessions) == 2
    assert sessions[0]["started_at"] > sessions[1]["started_at"]
    assert sessions[0]["user_name"] == "Ada"


async def test_a_session_row_says_which_platform_it_was_on(client, sign_in, web, guild, wf):
    wf.member(guild, 21, name="ada")
    await web.db.conn.execute(
        "INSERT INTO golive_sessions(guild_id, user_id, source, platform, started_at, mode) "
        "VALUES (?, 21, 'presence', 'YouTube', '2026-08-27T00:00:00+00:00', 'on')",
        (wf.GUILD_ID,),
    )
    await web.db.conn.commit()
    sign_in(client)

    rows = client.get("/api/golive/sessions").json()

    assert rows[0]["platform"] == "YouTube"


async def test_the_session_limit_is_clamped(client, sign_in, web):
    sign_in(client)
    assert client.get("/api/golive/sessions", params={"limit": 10000}).status_code == 200
    assert client.get("/api/golive/sessions", params={"limit": 0}).status_code == 200


async def test_linking_a_member_stores_the_login_and_says_it_was_not_checked(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    sign_in(client)

    response = client.post(
        "/api/golive/links",
        json={"user_id": "21", "twitch_login": "https://twitch.tv/AdaStreams?x=1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["twitch_login"] == "adastreams"
    assert body["checked"] is False
    assert "did not check" in body["message"]
    row = await get_link(web.db, 21)
    assert row["twitch_login"] == "adastreams"
    details = await wf.one_web_row(web.db, "web.golive.link")
    assert details == {"via": wf.VIA_WEBSITE, "login": "adastreams", "checked": False}
    assert await wf.kinds_in(web.db) == ["web.golive.link"]


async def test_linking_refuses_a_channel_another_member_already_holds(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    wf.member(guild, 22, name="bo")
    await set_link(web.db, 21, "adastreams", "t-1")
    sign_in(client)

    response = client.post(
        "/api/golive/links", json={"user_id": "22", "twitch_login": "adastreams"}
    )

    assert response.status_code == 409
    assert "only belong to one member" in response.json()["message"]
    assert await get_link(web.db, 22) is None
    assert await wf.kinds_in(web.db) == []


def test_linking_refuses_something_that_is_not_a_channel_name_in_words(client, sign_in):
    sign_in(client)

    response = client.post(
        "/api/golive/links", json={"user_id": "21", "twitch_login": "not a name!"}
    )

    assert response.status_code == 400
    assert "nothing was linked" in response.json()["message"]


async def test_opting_a_member_out_and_back_in_again(client, sign_in, web, guild, wf):
    wf.member(guild, 21, name="ada")
    sign_in(client)

    out = client.post("/api/golive/optouts", json={"user_id": "21"})
    assert out.status_code == 200
    assert out.json()["opted_out"] is True
    assert await is_opted_out(web.db, 21) is True

    back = client.delete("/api/golive/optouts/21")
    assert back.status_code == 200
    assert back.json()["opted_out"] is False
    assert await is_opted_out(web.db, 21) is False

    rows = await wf.web_rows_in(web.db)
    assert [kind for kind, _ in rows] == ["web.golive.optout", "web.golive.optin"]
    assert [found["via"] for _, found in rows] == [wf.VIA_WEBSITE, wf.VIA_WEBSITE]
    assert await wf.kinds_in(web.db) == ["web.golive.optout", "web.golive.optin"]


def test_taking_away_an_optout_nobody_has_says_so_in_words(client, sign_in):
    sign_in(client)

    response = client.delete("/api/golive/optouts/21")

    assert response.status_code == 404
    assert "nothing to undo" in response.json()["message"]


async def test_a_refused_link_leaves_no_row_at_all(client, sign_in, web, wf):
    """Checklist 34 the other way: a write that did not happen leaves nothing behind."""
    sign_in(client)

    client.post("/api/golive/links", json={"user_id": "21", "twitch_login": "not a name!"})
    client.delete("/api/golive/links/21")
    client.delete("/api/golive/optouts/21")

    assert await wf.kinds_in(web.db) == []


async def test_the_website_never_says_a_link_it_did_not_check_was_checked(
    client, sign_in, web, guild, wf
):
    """Checklist 10: the route passes helix=None, so `checked` is false and the row says so."""
    wf.member(guild, 21, name="ada")
    sign_in(client)

    body = client.post(
        "/api/golive/links", json={"user_id": "21", "twitch_login": "adastreams"}
    ).json()

    assert body["checked"] is False
    assert "did not check" in body["message"]
    assert (await get_link(web.db, 21))["twitch_user_id"] is None
    assert (await wf.one_web_row(web.db, "web.golive.link"))["checked"] is False


async def test_the_preview_renders_both_wordings_through_the_bots_own_functions(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 7, name="ada", staff=True)
    sign_in(client)

    found = client.get("/api/golive/preview").json()

    assert found["live"]["author"] == "Ada is now live on Twitch!"
    assert "Ada" in found["live"]["text"] and "Celeste" in found["live"]["text"]
    assert found["ended"]["text"] == (
        "**Ada** was streaming **Celeste** — the stream has ended. "
        "https://www.twitch.tv/blackbloc"
    )
    assert found["ended"]["author"] == "Ada was live on Twitch"
    assert found["ended"]["footer"] == "Black Bloc · via Twitch · stream ended"


async def test_the_preview_reads_the_wording_this_guild_saved(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 7, name="ada", staff=True)
    await web.store.set(wf.GUILD_ID, "golive_end_template", "{name} streamed for {duration}")
    await web.store.set(wf.GUILD_ID, "golive_end_author", "that was {platform}")
    sign_in(client)

    found = client.get("/api/golive/preview").json()

    assert found["ended"]["text"] == "Ada streamed for 2 h 10 min"
    assert found["ended"]["author"] == "that was Twitch"


async def test_a_blank_end_wording_previews_the_suffix_the_old_way(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 7, name="ada", staff=True)
    await web.store.set(wf.GUILD_ID, "golive_end_template", "")
    sign_in(client)

    found = client.get("/api/golive/preview").json()

    assert found["ended"]["text"] == found["live"]["text"] + " — stream ended"


async def test_the_preview_drops_the_ping_unless_the_guild_keeps_it(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 7, name="ada", staff=True)
    await web.store.set(wf.GUILD_ID, "golive_ping_role_id", 4242)
    sign_in(client)

    found = client.get("/api/golive/preview").json()
    assert found["live"]["text"].startswith("<@&4242> ")
    assert not found["ended"]["text"].startswith("<@&4242> ")

    await web.store.set(wf.GUILD_ID, "golive_end_keep_mention", True)
    kept = client.get("/api/golive/preview").json()
    assert kept["ended"]["text"].startswith("<@&4242> ")


def test_the_preview_refuses_a_member_in_words(client, sign_in):
    sign_in(client, uid=1234, staff=False)

    response = client.get("/api/golive/preview")

    assert response.status_code == 403
    assert "does not hold a staff role" in response.json()["message"]
    assert response.json()["message"] != "403"


def test_the_preview_writes_nothing(client, sign_in):
    sign_in(client)
    assert client.get("/api/golive/preview").status_code == 200
    assert client.post("/api/golive/preview").status_code in (404, 405)
