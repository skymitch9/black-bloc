from __future__ import annotations

from types import SimpleNamespace

import pytest

from black_bloc.cogs.content.youtube import get_link, set_link
from black_bloc.youtube import YouTubeError

CHANNEL = "UCsXVk37bltHxD1rDPwtNM8Q"
OTHER = "UC_x5XG1OV2P6uZZ5FSM9Ttw"

ROUTES = [
    ("GET", "/api/youtube/links"),
    ("POST", "/api/youtube/links"),
    ("DELETE", "/api/youtube/links/7"),
    ("GET", "/api/youtube/status"),
]

UPLOAD_FIELDS = (
    "running",
    "last_ok_at",
    "last_error",
    "failures",
    "fetches",
    "unchanged",
    "unchanged_ratio",
    "videos",
    "announced",
)


class FakeCog:
    """The cog the router reaches for: it owns the client the link path resolves through."""

    def __init__(self, db, *, keyed=False, resolves=None, boom=None):
        self.db = db
        self.client = SimpleNamespace(keyed=keyed, resolve=self._resolve)
        self.live_poller = SimpleNamespace(is_running=lambda: True)
        self.last_probe_at = "2026-09-17T13:00:00+00:00"
        self.last_probe_error = None
        self.probed = 3
        self.confirms = 0
        self._resolves = resolves or (CHANNEL, "Kurzgesagt")
        self._boom = boom

    async def _resolve(self, text):
        if self._boom is not None:
            raise self._boom
        return self._resolves


@pytest.mark.parametrize(("method", "route"), ROUTES)
def test_every_youtube_route_needs_a_session(client, method, route):
    assert client.request(method, route).status_code == 401


@pytest.mark.parametrize(("method", "route"), ROUTES)
def test_every_youtube_route_refuses_a_non_staff_visitor(client, sign_in, method, route):
    sign_in(client, uid=1234, staff=False)
    assert client.request(method, route).status_code == 403


async def test_links_carry_the_member_name_and_nothing_about_an_upload(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    await set_link(web.db, 21, CHANNEL, "@ada", "Ada Makes")
    sign_in(client)

    rows = client.get("/api/youtube/links").json()

    assert rows[0]["user_id"] == "21"
    assert rows[0]["user_name"] == "Ada"
    assert rows[0]["channel_id"] == CHANNEL
    assert rows[0]["handle"] == "@ada"
    assert rows[0]["title"] == "Ada Makes"
    assert set(rows[0]) == {"user_id", "user_name", "channel_id", "handle", "title", "linked_at"}


async def test_an_unlink_removes_the_row_and_leaves_a_web_line(client, sign_in, web, wf):
    await set_link(web.db, 21, CHANNEL)
    sign_in(client)

    response = client.delete("/api/youtube/links/21")

    assert response.json() == {"unlinked": True, "user_id": "21"}
    assert await get_link(web.db, 21) is None
    kinds = await wf.kinds_in(web.db)
    assert kinds.count("web.youtube.unlink") == 1
    assert "youtube.unlink" not in kinds


def test_unlinking_somebody_who_is_not_linked_says_where_to_look(client, sign_in):
    sign_in(client)

    response = client.delete("/api/youtube/links/21")

    assert response.status_code == 404
    assert "nothing to unlink" in response.json()["message"]
    assert "links table" in response.json()["message"]


def test_an_id_that_is_not_a_number_is_a_sentence_not_a_stack_trace(client, sign_in):
    sign_in(client)

    response = client.delete("/api/youtube/links/nobody")

    assert response.status_code == 400
    assert "nobody" in response.json()["message"]


async def test_linking_resolves_stores_and_says_what_happens_next(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    web.cogs["YouTube"] = FakeCog(web.db)
    sign_in(client)

    response = client.post(
        "/api/youtube/links", json={"member_id": "21", "channel": "@kurzgesagt"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["channel_id"] == CHANNEL
    assert "goes live" in body["message"]
    assert "counted as seen" not in body["message"]
    assert (await get_link(web.db, 21))["channel_id"] == CHANNEL
    kinds = await wf.kinds_in(web.db)
    assert kinds.count("web.youtube.link") == 1
    assert "youtube.link" not in kinds


async def test_linking_refuses_a_channel_another_member_already_holds(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    wf.member(guild, 22, name="bo")
    await set_link(web.db, 21, CHANNEL, None, "Kurzgesagt")
    web.cogs["YouTube"] = FakeCog(web.db)
    sign_in(client)

    response = client.post(
        "/api/youtube/links", json={"member_id": "22", "channel": CHANNEL}
    )

    assert response.status_code == 409
    assert "only belong to one member" in response.json()["message"]
    assert await get_link(web.db, 22) is None


async def test_a_channel_youtube_cannot_resolve_is_refused_in_the_clients_own_words(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    web.cogs["YouTube"] = FakeCog(
        web.db, boom=YouTubeError("I could not turn that into a YouTube channel id")
    )
    sign_in(client)

    response = client.post("/api/youtube/links", json={"member_id": "21", "channel": "nope"})

    assert response.status_code == 400
    assert "could not turn" in response.json()["message"]
    assert await get_link(web.db, 21) is None


async def test_an_empty_channel_says_what_to_paste(client, sign_in, web, guild, wf):
    wf.member(guild, 21, name="ada")
    web.cogs["YouTube"] = FakeCog(web.db)
    sign_in(client)

    response = client.post("/api/youtube/links", json={"member_id": "21", "channel": "  "})

    assert response.status_code == 400
    assert "youtube.com/channel/UC" in response.json()["message"]


def test_linking_while_the_cog_is_not_loaded_says_the_feature_is_off(client, sign_in, web):
    sign_in(client)

    response = client.post("/api/youtube/links", json={"member_id": "21", "channel": CHANNEL})

    assert response.status_code == 503
    assert "YouTube" in response.json()["message"]


def test_the_videos_route_is_gone_rather_than_answering_an_empty_list(client, sign_in):
    sign_in(client)

    assert client.get("/api/youtube/videos").status_code == 404


async def test_status_says_whether_the_key_is_set_and_what_the_probe_is_doing(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    await set_link(web.db, 21, CHANNEL)
    web.cogs["YouTube"] = FakeCog(web.db, keyed=True)
    sign_in(client)

    body = client.get("/api/youtube/status").json()

    assert body["api_key_set"] is True
    assert body["links"] == 1
    assert not set(body) & set(UPLOAD_FIELDS)
    assert body["live_mode"] == "off" and body["live_minutes"] == 5
    assert body["live_end_misses"] == 2 and body["live_running"] is True
    assert body["last_probe_at"] == "2026-09-17T13:00:00+00:00"
    assert body["last_probe_error"] is None
    assert body["probed"] == 3 and body["quota_today"] == 0 and body["live_now"] == 0
    assert body["botcheck"] is False
    assert body["reading_live"] == 0
    assert body["walled"] == 0 and body["id_unknown"] == 0


async def test_status_says_when_the_last_probe_was_served_youtubes_bot_check(
    client, sign_in, web, guild, wf
):
    """KI-30: staff can see why a live stream was announced without its video id."""
    cog = FakeCog(web.db, keyed=True)
    cog.last_botcheck = True
    web.cogs["YouTube"] = cog
    sign_in(client)

    assert client.get("/api/youtube/status").json()["botcheck"] is True


async def test_status_counts_the_channels_the_probe_reads_as_live_right_now(
    client, sign_in, web, guild, wf
):
    """A probe that reads live while another source holds the session moves this, not live_now."""
    cog = FakeCog(web.db, keyed=True)
    cog.live_video = {CHANNEL: "?"}
    web.cogs["YouTube"] = cog
    sign_in(client)

    body = client.get("/api/youtube/status").json()

    assert body["reading_live"] == 1 and body["live_now"] == 0


async def test_status_says_what_the_live_probe_is_doing_when_the_cog_is_loaded(
    client, sign_in, web, guild, wf
):
    """§D: the site and the panel read one health function, so they cannot disagree."""
    await web.store.set(guild.id, "youtube_live_mode", "shadow")
    web.cogs["YouTube"] = FakeCog(web.db, keyed=True)
    sign_in(client)

    body = client.get("/api/youtube/status").json()

    assert body["live_mode"] == "shadow"


def test_status_with_no_cog_loaded_reports_it_rather_than_pretending(client, sign_in, web):
    sign_in(client)

    body = client.get("/api/youtube/status").json()

    assert body["api_key_set"] is False
    assert body["live_running"] is False
    assert body["live_mode"] == "off"
    assert body["last_probe_at"] is None
    assert body["last_probe_error"]


async def test_status_says_how_many_channels_are_behind_the_wall_and_how_many_ids_are_unknown(
    client, sign_in, web, guild, wf
):
    """KI-30 (a): the wall is its own outcome, so the page can say it in words."""
    cog = FakeCog(web.db, keyed=True)
    cog.walled = {CHANNEL: None, "UC3Oe-jfrIqEGygxYBYyN6jQ": True}
    cog.live_video = {"UC3Oe-jfrIqEGygxYBYyN6jQ": "?", "UCother": "FAMWR-HDS8U"}
    web.cogs["YouTube"] = cog
    sign_in(client)

    body = client.get("/api/youtube/status").json()

    assert body["walled"] == 2 and body["id_unknown"] == 1 and body["reading_live"] == 2
