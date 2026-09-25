from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from black_bloc.cogs.content.golive import (
    end_session,
    get_link,
    is_opted_out,
    set_link,
    set_optout,
)
from black_bloc.cogs.content.golive import (
    start_session as start_golive_session,
)
from black_bloc.cogs.content.spotlight import (
    add_channel,
    add_window,
    channel_by_id,
    channel_by_login,
    channels_for,
    set_announced,
    start_session,
    windows_for,
)
from black_bloc.golive import HISTORY_NOTHING, StreamInfo

ROUTES = [
    ("GET", "/api/golive/links"),
    ("POST", "/api/golive/links"),
    ("POST", "/api/golive/links/sweep"),
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
    ("GET", "/api/golive/spotlight/1/windows"),
    ("POST", "/api/golive/spotlight/1/windows"),
    ("DELETE", "/api/golive/spotlight/1/windows/1"),
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


async def test_opting_a_live_member_out_ends_the_announcement_that_is_already_out(
    client, sign_in, web, guild, wf
):
    """The site's door reaches the same settle `/golive` does — one path, one sentence."""
    from black_bloc.cogs.content.golive import GoLive, open_session_for

    wf.member(guild, 21, name="ada")
    session_id = await start_golive_session(
        web.db, wf.GUILD_ID, 21, "twitch", StreamInfo(url="u", game="g", title="t"), "on"
    )
    assert session_id is not None
    web.cogs["GoLive"] = GoLive(web)
    sign_in(client)

    out = client.post("/api/golive/optouts", json={"user_id": "21"}).json()

    assert "is opted out" in out["message"]
    assert "edited to say the stream has ended" in out["message"]
    assert "golive_member_optout_post" in out["message"]
    assert await open_session_for(web.db, wf.GUILD_ID, 21) is None


async def test_opting_a_member_out_with_nothing_running_says_only_the_plain_sentence(
    client, sign_in, web, guild, wf
):
    from black_bloc.cogs.content.golive import GoLive

    wf.member(guild, 21, name="ada")
    web.cogs["GoLive"] = GoLive(web)
    sign_in(client)

    out = client.post("/api/golive/optouts", json={"user_id": "21"}).json()

    assert "is opted out" in out["message"]
    assert "golive_member_optout_post" not in out["message"]


async def test_opting_a_member_back_in_never_announces_a_stream_already_running(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    await set_optout(web.db, 21)
    sign_in(client)

    back = client.delete("/api/golive/optouts/21").json()

    assert "not announced after the fact" in back["message"]


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
        starts_at=fields.pop("starts_at", None),
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


# --- the channel record over HTTP ------------------------------------------------------------


async def test_a_channel_added_with_no_spotlight_takes_the_key_and_never_expires(
    client, sign_in, web, wf
):
    sign_in(client)

    found = client.post(
        "/api/golive/spotlight", json={"twitch_login": "rpglimitbreak", "days": 3}
    ).json()

    assert found["spotlight"] is False and found["kept"] is True
    assert found["expires_at"] is None
    assert "adds the pin and the reminders" in found["message"]


async def test_the_key_can_make_a_channel_spotlit_from_the_start(client, sign_in, web, wf):
    sign_in(client)
    await web.store.set(web.guild.id, "golive_channel_spotlight_default", True)

    found = client.post("/api/golive/spotlight", json={"twitch_login": "frostfatales"}).json()

    assert found["spotlight"] is True


async def test_a_youtube_channel_with_no_twitch_name_is_refused_in_words(client, sign_in, web):
    sign_in(client)

    answer = client.post(
        "/api/golive/spotlight", json={"twitch_login": "", "youtube": "@GamesDoneQuick"}
    )

    assert answer.status_code == 400
    said = answer.json()["message"]
    assert "needs a Twitch name" in said and "Link a YouTube channel" in said


async def test_a_row_carries_its_spotlight_its_optout_and_its_youtube_side(
    client, sign_in, web, wf
):
    sign_in(client)
    made = client.post(
        "/api/golive/spotlight", json={"twitch_login": "esamarathon", "spotlight": True}
    ).json()

    rows = client.get("/api/golive/spotlight").json()

    row = next(one for one in rows if one["id"] == made["id"])
    assert row["spotlight"] is True and row["announce"] is True
    assert row["opted_out"] is False
    assert row["youtube_channel_id"] is None and row["youtube_handle"] is None
    assert row["youtube_url"] is None


async def test_the_spotlight_toggle_keeps_the_row_and_says_which_way_it_went(
    client, sign_in, web, wf
):
    sign_in(client)
    made = client.post(
        "/api/golive/spotlight", json={"twitch_login": "esamarathon", "spotlight": True}
    ).json()

    off = client.patch(
        f"/api/golive/spotlight/{made['id']}", json={"spotlight": False}
    ).json()

    assert off["spotlight"] is False and off["id"] == made["id"]
    assert "no pin and no reminders" in off["message"]

    on = client.patch(f"/api/golive/spotlight/{made['id']}", json={"spotlight": True}).json()
    assert on["spotlight"] is True and "is spotlighted" in on["message"]


async def test_a_channel_can_be_opted_out_of_announcements_and_back_in(client, sign_in, web, wf):
    sign_in(client)
    made = client.post("/api/golive/spotlight", json={"twitch_login": "esamarathon"}).json()

    out = client.patch(f"/api/golive/spotlight/{made['id']}", json={"announce": False}).json()

    assert out["announce"] is False and out["opted_out"] is True
    assert "is opted out" in out["message"] and "stays on the list" in out["message"]

    back = client.patch(f"/api/golive/spotlight/{made['id']}", json={"announce": True}).json()
    assert back["announce"] is True and "opted back in" in back["message"]


async def test_opting_a_live_channel_out_from_the_site_ends_the_open_session(
    client, sign_in, web, wf
):
    """The site's door reaches the same settle the panel's does — one path, one sentence."""
    from black_bloc.cogs.content.spotlight import Spotlight, open_session

    spotlight_id = await a_spotlight(web, wf)
    session_id = await start_session(
        web.db,
        wf.GUILD_ID,
        spotlight_id,
        StreamInfo(url="https://www.twitch.tv/gamesdonequick", game="Celeste", title="AGDQ"),
        "on",
    )
    await set_announced(web.db, session_id, 4242)
    web.cogs["Spotlight"] = Spotlight(web)
    sign_in(client)

    out = client.patch(f"/api/golive/spotlight/{spotlight_id}", json={"announce": False}).json()

    assert out["announce"] is False and out["live"] is False
    assert "is opted out" in out["message"]
    assert "edited to say the stream has ended" in out["message"]
    assert await open_session(web.db, spotlight_id) is None


async def test_unlinking_a_youtube_channel_that_is_not_there_says_so_rather_than_a_status(
    client, sign_in, web
):
    sign_in(client)
    made = client.post("/api/golive/spotlight", json={"twitch_login": "esamarathon"}).json()

    answer = client.patch(f"/api/golive/spotlight/{made['id']}", json={"youtube": None})

    assert answer.status_code == 404
    assert "nothing to unlink" in answer.json()["message"]


async def test_linking_a_youtube_channel_with_no_youtube_half_running_refuses_in_words(
    client, sign_in, web
):
    sign_in(client)
    made = client.post("/api/golive/spotlight", json={"twitch_login": "esamarathon"}).json()

    answer = client.patch(
        f"/api/golive/spotlight/{made['id']}", json={"youtube": "@GamesDoneQuick"}
    )

    assert answer.status_code == 503
    assert "YouTube half is not running" in answer.json()["message"]


async def test_a_channel_can_be_added_already_opted_out(client, sign_in, web, wf):
    """The owner's flow for rpglimitbreak: on the list from the start, announcing nothing."""
    sign_in(client)

    found = client.post(
        "/api/golive/spotlight", json={"twitch_login": "rpglimitbreak", "announce": False}
    ).json()

    assert found["announce"] is False and found["opted_out"] is True
    rows = client.get("/api/golive/spotlight").json()
    assert any(one["twitch_login"] == "rpglimitbreak" for one in rows)


# --- Link from history: the Streamers toolbar's one bulk door ---------------------------------


async def past_session(db, guild_id, user_id, url, platform="Twitch"):
    session_id = await start_golive_session(
        db, guild_id, user_id, "presence", StreamInfo(url=url, platform=platform), "shadow"
    )
    await end_session(db, session_id, "2026-09-01T00:00:00+00:00")


async def test_the_history_sweep_links_the_newest_channel_and_answers_in_words(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    await past_session(web.db, wf.GUILD_ID, 21, "https://twitch.tv/oldname")
    await past_session(web.db, wf.GUILD_ID, 21, "https://twitch.tv/adastreams")
    sign_in(client)

    response = client.post("/api/golive/links/sweep", json={})

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "linked": 1,
        "opted_out": 0,
        "taken": 0,
        "unreadable": 0,
        "left": 0,
        "message": "Linked 1 person (Ada → twitch.tv/adastreams).",
    }
    assert (await get_link(web.db, 21))["twitch_login"] == "adastreams"
    assert await wf.kinds_in(web.db) == ["web.golive.link", "web.golive.history_swept"]


async def test_the_history_sweep_counts_the_opted_out_and_links_nobody(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    await set_optout(web.db, 21)
    await past_session(web.db, wf.GUILD_ID, 21, "https://twitch.tv/adastreams")
    sign_in(client)

    body = client.post("/api/golive/links/sweep", json={}).json()

    assert body["linked"] == 0 and body["opted_out"] == 1
    assert "asked not to be announced" in body["message"]
    assert await get_link(web.db, 21) is None


async def test_the_history_sweep_refuses_a_channel_another_member_holds(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    wf.member(guild, 22, name="namu")
    await set_link(web.db, 22, "adastreams", "t-1")
    await past_session(web.db, wf.GUILD_ID, 21, "https://twitch.tv/adastreams")
    sign_in(client)

    body = client.post("/api/golive/links/sweep", json={}).json()

    assert body["taken"] == 1 and body["linked"] == 0
    assert "already belongs to somebody else" in body["message"]
    assert await get_link(web.db, 21) is None


async def test_a_history_sweep_with_nothing_to_do_says_so_rather_than_answering_empty(
    client, sign_in, web
):
    sign_in(client)

    body = client.post("/api/golive/links/sweep", json={}).json()

    assert body == {
        "linked": 0,
        "opted_out": 0,
        "taken": 0,
        "unreadable": 0,
        "left": 0,
        "message": HISTORY_NOTHING,
    }


# --- the owner's date range (2026-09-22) ------------------------------------------------------


def days_ahead(days):
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


async def test_the_list_carries_the_start_the_range_and_whether_it_is_scheduled(
    client, sign_in, web, wf
):
    await a_spotlight(web, wf)
    await a_spotlight(
        web, wf, "esamarathon", starts_at=days_ahead(3), expires_at=days_ahead(10)
    )
    sign_in(client)

    rows = {one["twitch_login"]: one for one in client.get("/api/golive/spotlight").json()}

    assert rows["gamesdonequick"]["starts_at"] is None
    assert rows["gamesdonequick"]["scheduled"] is False
    assert rows["gamesdonequick"]["range"] == "kept"
    assert rows["gamesdonequick"]["announced"] == "spotlight · kept"
    assert rows["esamarathon"]["starts_at"] is not None
    assert rows["esamarathon"]["scheduled"] is True
    assert rows["esamarathon"]["range"].startswith("from ")
    assert rows["esamarathon"]["announced"].endswith("· scheduled")


async def test_adding_a_channel_takes_a_start_and_an_end_as_dates(client, sign_in, web, wf):
    sign_in(client)

    found = client.post(
        "/api/golive/spotlight",
        json={
            "twitch_login": "esamarathon",
            "starts_at": "2026-11-01 09:00",
            "expires_at": "2026-11-08 09:00",
            "tz": "UTC",
            "spotlight": True,
        },
    ).json()

    assert found["starts_at"] == "2026-11-01T09:00:00+00:00"
    assert found["expires_at"] == "2026-11-08T09:00:00+00:00"
    assert found["kept"] is False
    assert "from 1 Nov to 8 Nov" in found["message"]


async def test_adding_a_channel_with_a_start_and_no_end_keeps_it_for_ever(
    client, sign_in, web, wf
):
    sign_in(client)

    found = client.post(
        "/api/golive/spotlight",
        json={"twitch_login": "esamarathon", "starts_at": "2026-11-01 09:00", "tz": "UTC",
              "expires_at": None, "spotlight": True},
    ).json()

    assert found["starts_at"] == "2026-11-01T09:00:00+00:00"
    assert found["kept"] is True and found["range"] == "from 1 Nov · kept"


async def test_adding_a_backwards_range_is_refused_with_words_and_never_a_bare_status(
    client, sign_in, web, wf
):
    sign_in(client)

    response = client.post(
        "/api/golive/spotlight",
        json={
            "twitch_login": "esamarathon",
            "starts_at": "2026-11-08 09:00",
            "expires_at": "2026-11-01 09:00",
            "tz": "UTC",
        },
    )

    assert response.status_code == 422
    assert "ends before it starts" in response.json()["message"]
    assert await channels_for(web.db, wf.GUILD_ID) == []


async def test_a_start_nobody_can_read_is_refused_by_name(client, sign_in, web, wf):
    sign_in(client)

    response = client.post(
        "/api/golive/spotlight",
        json={"twitch_login": "esamarathon", "starts_at": "next tuesday"},
    )

    assert response.status_code == 422
    assert "next tuesday" in response.json()["message"]
    assert await channels_for(web.db, wf.GUILD_ID) == []


async def test_a_patch_sets_both_dates_and_says_the_row_is_scheduled(client, sign_in, web, wf):
    spotlight_id = await a_spotlight(web, wf)
    sign_in(client)

    found = client.patch(
        f"/api/golive/spotlight/{spotlight_id}",
        json={"starts_at": days_ahead(3), "expires_at": days_ahead(10)},
    ).json()

    assert found["scheduled"] is True and found["starts_at"] is not None
    assert "before that start" in found["message"]
    row = await channel_by_id(web.db, spotlight_id)
    assert row["starts_at"] is not None and row["expires_at"] is not None


async def test_a_patch_with_a_null_start_clears_it(client, sign_in, web, wf):
    spotlight_id = await a_spotlight(web, wf, starts_at=days_ahead(3))
    sign_in(client)

    found = client.patch(
        f"/api/golive/spotlight/{spotlight_id}", json={"starts_at": None}
    ).json()

    assert found["starts_at"] is None and found["scheduled"] is False
    assert (await channel_by_id(web.db, spotlight_id))["starts_at"] is None


async def test_a_patch_that_would_end_before_the_start_is_refused_and_stores_nothing(
    client, sign_in, web, wf
):
    spotlight_id = await a_spotlight(
        web, wf, starts_at=days_ahead(10), expires_at=days_ahead(20)
    )
    sign_in(client)

    response = client.patch(
        f"/api/golive/spotlight/{spotlight_id}", json={"expires_at": days_ahead(3)}
    )

    assert response.status_code == 422
    assert "ends before it starts" in response.json()["message"]
    row = await channel_by_id(web.db, spotlight_id)
    assert row["expires_at"] > row["starts_at"]


async def test_a_patch_date_nobody_can_read_is_refused_by_name(client, sign_in, web, wf):
    spotlight_id = await a_spotlight(web, wf)
    sign_in(client)

    response = client.patch(
        f"/api/golive/spotlight/{spotlight_id}", json={"expires_at": "soonish"}
    )

    assert response.status_code == 422
    assert "soonish" in response.json()["message"]


async def test_the_dates_routes_stay_staff_only(client, sign_in, web, wf):
    spotlight_id = await a_spotlight(web, wf)
    sign_in(client, staff=False)

    response = client.patch(
        f"/api/golive/spotlight/{spotlight_id}", json={"starts_at": days_ahead(2)}
    )

    assert response.status_code == 403
    assert (await channel_by_id(web.db, spotlight_id))["starts_at"] is None


# --- ping windows (owner, 2026-09-25) ----------------------------------------------------------


async def a_window(web, wf, spotlight_id, start_hours, end_hours, **fields):
    now = datetime.now(UTC)
    return await add_window(
        web.db,
        wf.GUILD_ID,
        spotlight_id,
        (now + timedelta(hours=start_hours)).isoformat(),
        (now + timedelta(hours=end_hours)).isoformat(),
        **fields,
    )


async def test_a_row_carries_its_ping_mode_its_state_and_its_windows(client, sign_in, web, wf):
    spotlight_id = await a_spotlight(web, wf, ping_mode="events")
    await a_window(web, wf, spotlight_id, -1, 5, note="AGDQ 2027")
    await a_window(web, wf, spotlight_id, 48, 72, source="marathon", source_id=4)
    await a_spotlight(web, wf, "esamarathon")
    sign_in(client)

    rows = {one["twitch_login"]: one for one in client.get("/api/golive/spotlight").json()}

    gdq = rows["gamesdonequick"]
    assert gdq["ping_mode"] == "events" and gdq["pinging"] is True
    assert gdq["ping_state"].startswith("Pings: during events — open until ")
    assert [one["staff"] for one in gdq["windows"]] == [True, False]
    assert gdq["windows"][0]["open"] is True and gdq["windows"][0]["note"] == "AGDQ 2027"
    assert gdq["windows"][1]["source_words"] == "from the marathon schedule"
    assert rows["esamarathon"]["ping_mode"] == "always"
    assert rows["esamarathon"]["ping_state"] == "Pings: always"
    assert rows["esamarathon"]["windows"] == []


async def test_a_patch_sets_the_ping_mode_and_leaves_one_row(client, sign_in, web, wf):
    spotlight_id = await a_spotlight(web, wf)
    sign_in(client)

    answer = client.patch(f"/api/golive/spotlight/{spotlight_id}", json={"ping_mode": "never"})

    assert answer.status_code == 200
    body = answer.json()
    assert body["ping_mode"] == "never" and body["ping_state"] == "Pings: never"
    assert "nothing it posts mentions a role" in body["message"]
    assert await wf.kinds_in(web.db) == ["web.golive.spotlight_ping_mode_set"]
    said = await wf.one_web_row(web.db, "web.golive.spotlight_ping_mode_set")
    assert said["from"] == "always" and said["to"] == "never"


async def test_an_unknown_ping_mode_is_refused_before_anything_is_written(
    client, sign_in, web, wf
):
    spotlight_id = await a_spotlight(web, wf)
    sign_in(client)

    answer = client.patch(
        f"/api/golive/spotlight/{spotlight_id}", json={"ping_mode": "loud", "pin": False}
    )

    assert answer.status_code == 422
    assert "**loud** is not a ping mode" in answer.json()["message"]
    row = await channel_by_id(web.db, spotlight_id)
    assert row["ping_mode"] == "always" and row["pin"] == 1
    assert await wf.kinds_in(web.db) == []


async def test_windows_are_listed_added_and_removed_through_their_routes(
    client, sign_in, web, wf
):
    spotlight_id = await a_spotlight(web, wf, ping_mode="events")
    sign_in(client)

    added = client.post(
        f"/api/golive/spotlight/{spotlight_id}/windows",
        json={
            "starts_at": "2027-01-12 15:00",
            "ends_at": "2027-01-19 23:00",
            "note": "AGDQ 2027",
            "tz": "UTC",
        },
    )

    assert added.status_code == 200
    body = added.json()
    assert body["window"]["starts_at"] == "2027-01-12T15:00:00+00:00"
    assert "pings from 12 Jan" in body["message"]
    assert [one["note"] for one in body["windows"]] == ["AGDQ 2027"]
    listed = client.get(f"/api/golive/spotlight/{spotlight_id}/windows").json()
    assert [one["id"] for one in listed] == [body["window"]["id"]]
    assert await wf.kinds_in(web.db) == ["web.golive.spotlight_window_added"]

    gone = client.delete(f"/api/golive/spotlight/{spotlight_id}/windows/{body['window']['id']}")

    assert gone.status_code == 200 and gone.json()["removed"] is True
    assert await windows_for(web.db, spotlight_id) == []
    assert await wf.kinds_in(web.db) == [
        "web.golive.spotlight_window_added",
        "web.golive.spotlight_window_removed",
    ]


async def test_a_window_is_refused_in_words_without_both_ends_backwards_or_unreadable(
    client, sign_in, web, wf
):
    spotlight_id = await a_spotlight(web, wf)
    sign_in(client)
    path = f"/api/golive/spotlight/{spotlight_id}/windows"

    half = client.post(path, json={"starts_at": "2027-01-12 15:00", "tz": "UTC"})
    backwards = client.post(
        path, json={"starts_at": "2027-01-19 23:00", "ends_at": "2027-01-12 15:00", "tz": "UTC"}
    )
    garbled = client.post(path, json={"starts_at": "someday", "ends_at": "2027-01-12 15:00"})

    assert half.status_code == 422 and "start AND an end" in half.json()["message"]
    assert backwards.status_code == 422
    assert "ends before it starts" in backwards.json()["message"]
    assert garbled.status_code == 422 and "someday" in garbled.json()["message"]
    assert await windows_for(web.db, spotlight_id) == []


async def test_a_marathon_window_cannot_be_removed_from_here(client, sign_in, web, wf):
    spotlight_id = await a_spotlight(web, wf)
    window_id = await a_window(web, wf, spotlight_id, 24, 48, source="marathon", source_id=4)
    sign_in(client)

    answer = client.delete(f"/api/golive/spotlight/{spotlight_id}/windows/{window_id}")

    assert answer.status_code == 409
    assert answer.json()["message"] == (
        "That window comes from the marathon schedule — change it there."
    )
    assert len(await windows_for(web.db, spotlight_id)) == 1


async def test_a_window_on_another_row_or_gone_is_a_404_in_words(client, sign_in, web, wf):
    spotlight_id = await a_spotlight(web, wf)
    other = await a_spotlight(web, wf, "esamarathon")
    window_id = await a_window(web, wf, other, 24, 48)
    sign_in(client)

    answer = client.delete(f"/api/golive/spotlight/{spotlight_id}/windows/{window_id}")

    assert answer.status_code == 404
    assert "not there any more" in answer.json()["message"]
