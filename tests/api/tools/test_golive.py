from __future__ import annotations

import pytest

from black_bloc.cogs.content.golive import get_link, is_opted_out, set_link, set_optout
from black_bloc.cogs.content.spotlight import (
    add_channel,
    channel_by_id,
    channel_by_login,
    channels_for,
    set_announced,
    start_session,
)
from black_bloc.golive import StreamInfo

ROUTES = [
    ("GET", "/api/golive/links"),
    ("POST", "/api/golive/links"),
    ("DELETE", "/api/golive/links/7"),
    ("GET", "/api/golive/optouts"),
    ("POST", "/api/golive/optouts"),
    ("DELETE", "/api/golive/optouts/7"),
    ("GET", "/api/golive/sessions"),
    ("GET", "/api/golive/spotlight"),
    ("POST", "/api/golive/spotlight"),
    ("PATCH", "/api/golive/spotlight/1"),
    ("DELETE", "/api/golive/spotlight/1"),
    ("POST", "/api/golive/spotlight/1/bump"),
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


async def test_a_co_stream_row_names_the_other_platform_the_page_draws_beside_it(
    client, sign_in, web, guild, wf
):
    """The Go-live page's join reads these three as optional; a single-platform row is null."""
    wf.member(guild, 21, name="ada")
    await web.db.conn.execute(
        "INSERT INTO golive_sessions(guild_id, user_id, source, platform, url, also_source, "
        "also_url, also_platform, also_started_at, started_at, mode) "
        "VALUES (?, 21, 'twitch', 'Twitch', 'https://twitch.tv/ada', 'youtube', "
        "'https://youtu.be/x', 'YouTube', '2026-08-27T00:30:00+00:00', "
        "'2026-08-27T00:00:00+00:00', 'on')",
        (wf.GUILD_ID,),
    )
    await web.db.conn.execute(
        "INSERT INTO golive_sessions(guild_id, user_id, source, platform, started_at, "
        "ended_at, mode) VALUES (?, 21, 'twitch', 'Twitch', '2026-08-26T00:00:00+00:00', "
        "'2026-08-26T01:00:00+00:00', 'on')",
        (wf.GUILD_ID,),
    )
    await web.db.conn.commit()
    sign_in(client)

    rows = client.get("/api/golive/sessions").json()

    assert rows[1]["also_source"] == "youtube"
    assert rows[1]["also_platform"] == "YouTube"
    assert rows[1]["also_url"] == "https://youtu.be/x"
    assert rows[0]["also_source"] is None and rows[0]["also_platform"] is None
    assert rows[0]["also_url"] is None


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


# --- spotlight (v144) --------------------------------------------------------------------------


async def a_spotlight(web, wf, login="gamesdonequick", **fields):
    return await add_channel(
        web.db,
        wf.GUILD_ID,
        login,
        added_by=7,
        expires_at=fields.pop("expires_at", None),
        pin=fields.pop("pin", True),
        **fields,
    )


async def test_the_list_says_kept_or_the_day_it_runs_out(client, sign_in, web, wf):
    await a_spotlight(web, wf)
    await a_spotlight(web, wf, "esamarathon", expires_at="2026-09-30T00:00:00+00:00")
    sign_in(client)

    rows = {one["twitch_login"]: one for one in client.get("/api/golive/spotlight").json()}

    assert rows["gamesdonequick"]["kept"] is True
    assert rows["gamesdonequick"]["until"] == "kept"
    assert rows["esamarathon"]["kept"] is False
    assert rows["esamarathon"]["until"] == "until 30 Sep"
    assert rows["gamesdonequick"]["live"] is False
    assert rows["gamesdonequick"]["url"] == "https://www.twitch.tv/gamesdonequick"


async def test_adding_a_channel_keeps_it_for_ever_when_no_days_are_given(
    client, sign_in, web, wf
):
    sign_in(client)

    found = client.post(
        "/api/golive/spotlight", json={"twitch_login": "GamesDoneQuick", "spotlight": True}
    ).json()

    assert found["twitch_login"] == "gamesdonequick" and found["kept"] is True
    assert "kept" in found["message"] and "every 4 hours" in found["message"]
    assert await wf.one_web_row(web.db, "web.golive.spotlight_added") is not None


async def test_adding_a_channel_with_days_gives_it_a_date(client, sign_in, web, wf):
    sign_in(client)

    found = client.post(
        "/api/golive/spotlight",
        json={"twitch_login": "esamarathon", "days": 3, "spotlight": True},
    ).json()

    assert found["kept"] is False and found["expires_at"] is not None


async def test_a_name_that_is_not_a_channel_is_refused_in_words(client, sign_in, web, wf):
    sign_in(client)

    response = client.post("/api/golive/spotlight", json={"twitch_login": "games done quick"})

    assert response.status_code == 400
    assert "not a Twitch channel name" in response.json()["message"]
    assert await channels_for(web.db, wf.GUILD_ID) == []


async def test_a_duplicate_is_refused_and_offers_extend(client, sign_in, web, wf):
    await a_spotlight(web, wf)
    sign_in(client)

    response = client.post("/api/golive/spotlight", json={"twitch_login": "gamesdonequick"})

    assert response.status_code == 409
    assert "Extend" in response.json()["message"]
    assert len(await channels_for(web.db, wf.GUILD_ID)) == 1


async def test_days_that_are_not_a_number_are_refused_rather_than_guessed(
    client, sign_in, web, wf
):
    sign_in(client)

    response = client.post(
        "/api/golive/spotlight", json={"twitch_login": "esamarathon", "days": "soon"}
    )

    assert response.status_code == 400
    assert "not a number of days" in response.json()["message"]


async def test_a_patch_can_keep_it_for_ever_and_turn_the_pin_off(client, sign_in, web, wf):
    spotlight_id = await a_spotlight(web, wf, expires_at="2026-09-30T00:00:00+00:00")
    sign_in(client)

    found = client.patch(
        f"/api/golive/spotlight/{spotlight_id}", json={"keep": True, "pin": False}
    ).json()

    assert found["kept"] is True and found["pin"] is False
    row = await channel_by_id(web.db, spotlight_id)
    assert row["expires_at"] is None and row["pin"] == 0
    assert await wf.one_web_row(web.db, "web.golive.spotlight_updated") is not None


async def test_a_patch_with_days_moves_the_date(client, sign_in, web, wf):
    spotlight_id = await a_spotlight(web, wf)
    sign_in(client)

    found = client.patch(f"/api/golive/spotlight/{spotlight_id}", json={"days": 14}).json()

    assert found["kept"] is False and found["expires_at"] is not None


async def test_a_move_on_a_row_that_has_gone_is_a_404_in_words(client, sign_in, web, wf):
    sign_in(client)

    response = client.patch("/api/golive/spotlight/4242", json={"keep": True})

    assert response.status_code == 404
    assert "not there any more" in response.json()["message"]


async def test_removing_a_channel_takes_it_off_the_list(client, sign_in, web, wf):
    spotlight_id = await a_spotlight(web, wf)
    sign_in(client)

    found = client.delete(f"/api/golive/spotlight/{spotlight_id}").json()

    assert found["removed"] is True and found["twitch_login"] == "gamesdonequick"
    assert await channel_by_login(web.db, wf.GUILD_ID, "gamesdonequick") is None
    assert await wf.one_web_row(web.db, "web.golive.spotlight_removed") is not None


async def test_a_bump_refuses_in_words_when_the_channel_is_not_live(
    client, sign_in, web, wf
):
    spotlight_id = await a_spotlight(web, wf)
    sign_in(client)

    response = client.post(f"/api/golive/spotlight/{spotlight_id}/bump")

    assert response.status_code == 409
    assert "not live right now" in response.json()["message"]


async def test_a_live_row_carries_its_session_and_its_past_ones(client, sign_in, web, wf):
    spotlight_id = await a_spotlight(web, wf)
    session_id = await start_session(
        web.db,
        wf.GUILD_ID,
        spotlight_id,
        StreamInfo(url="https://www.twitch.tv/gamesdonequick", game="Celeste", title="AGDQ"),
        "on",
    )
    await set_announced(web.db, session_id, 4242)
    sign_in(client)

    found = client.get("/api/golive/spotlight").json()[0]

    assert found["live"] is True
    assert found["session"]["title"] == "AGDQ"
    assert found["session"]["announced_message_id"] == "4242"
    assert [one["id"] for one in found["sessions"]] == [session_id]


async def test_a_spotlight_row_carries_the_ping_role_the_page_draws(client, sign_in, web, wf):
    """§C: the Ping-role cell on a channel row reads from the same payload the drawer does."""
    spotlight_id = await a_spotlight(web, wf, display_name="GamesDoneQuick")
    sign_in(client)

    before = client.get("/api/golive/spotlight").json()[0]
    assert before["role_id"] is None and before["role"] is None
    assert before["role_wearers"] is None

    client.post("/api/pings/streamers", json={"spotlight_id": str(spotlight_id)})
    after = client.get("/api/golive/spotlight").json()[0]

    assert after["role"] == "GamesDoneQuick pings" and after["role_wearers"] == 0
    assert after["role_id"]
