from __future__ import annotations

from types import SimpleNamespace

import pytest

from black_bloc.api.tools.youtube import state_of
from black_bloc.cogs.content.youtube import get_link, set_link
from black_bloc.youtube import SHORT, VIDEO, YouTubeError

CHANNEL = "UCsXVk37bltHxD1rDPwtNM8Q"
OTHER = "UC_x5XG1OV2P6uZZ5FSM9Ttw"

ROUTES = [
    ("GET", "/api/youtube/links"),
    ("POST", "/api/youtube/links"),
    ("DELETE", "/api/youtube/links/7"),
    ("GET", "/api/youtube/videos"),
    ("GET", "/api/youtube/status"),
]


class FakeVideo:
    def __init__(self, video_id, kind=VIDEO):
        self.video_id = video_id
        self.title = f"video {video_id}"
        self.url = f"https://www.youtube.com/watch?v={video_id}"
        self.published = "2026-09-01T00:00:00+00:00"
        self.channel_id = CHANNEL
        self.author = "Kurzgesagt"
        self.kind = kind


class FakeCog:
    """The cog the router reaches for: it owns the client and the link-and-seed step."""

    def __init__(self, db, *, keyed=False, resolves=None, seeds=2, boom=None):
        self.db = db
        self.client = SimpleNamespace(keyed=keyed, resolve=self._resolve)
        self.poller = SimpleNamespace(is_running=lambda: True)
        self.live_poller = SimpleNamespace(is_running=lambda: True)
        self.last_poll_ok_at = "2026-09-02T00:00:00+00:00"
        self.last_poll_error = None
        self.last_probe_at = "2026-09-17T13:00:00+00:00"
        self.last_probe_error = None
        self.probed = 3
        self.confirms = 0
        self.poll_failures = 0
        self.fetches = 8
        self.unchanged = 2
        self._resolves = resolves or (CHANNEL, "Kurzgesagt")
        self._seeds = seeds
        self._boom = boom

    async def _resolve(self, text):
        if self._boom is not None:
            raise self._boom
        return self._resolves

    async def link_and_seed(self, user_id, channel_id, given, title):
        await set_link(self.db, user_id, channel_id, None, title)
        if self._seeds:
            await self.db.conn.execute(
                "UPDATE youtube_links SET seeded = 1 WHERE user_id = ?", (user_id,)
            )
            await self.db.conn.commit()
        return self._seeds


async def a_video(db, user_id, video_id, *, kind=VIDEO, announced=None, mode=None):
    await db.conn.execute(
        "INSERT INTO youtube_videos(video_id, user_id, channel_id, title, published_at, "
        "seen_at, kind, announced_at, mode) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            video_id,
            user_id,
            CHANNEL,
            f"video {video_id}",
            f"2026-09-0{video_id[-1]}T00:00:00+00:00",
            "2026-09-02T00:00:00+00:00",
            kind,
            announced,
            mode,
        ),
    )
    await db.conn.commit()


@pytest.mark.parametrize(("method", "route"), ROUTES)
def test_every_youtube_route_needs_a_session(client, method, route):
    assert client.request(method, route).status_code == 401


@pytest.mark.parametrize(("method", "route"), ROUTES)
def test_every_youtube_route_refuses_a_non_staff_visitor(client, sign_in, method, route):
    sign_in(client, uid=1234, staff=False)
    assert client.request(method, route).status_code == 403


async def test_links_carry_the_member_name_and_the_last_video_seen(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    await set_link(web.db, 21, CHANNEL, "@ada", "Ada Makes")
    await a_video(web.db, 21, "vid1")
    sign_in(client)

    rows = client.get("/api/youtube/links").json()

    assert rows[0]["user_id"] == "21"
    assert rows[0]["user_name"] == "Ada"
    assert rows[0]["channel_id"] == CHANNEL
    assert rows[0]["handle"] == "@ada"
    assert rows[0]["title"] == "Ada Makes"
    assert rows[0]["last_video"] == "video vid1"
    assert rows[0]["seeded"] is False


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


async def test_linking_resolves_seeds_and_says_how_many_count_as_history(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    web.cogs["YouTube"] = FakeCog(web.db, seeds=5)
    sign_in(client)

    response = client.post(
        "/api/youtube/links", json={"member_id": "21", "channel": "@kurzgesagt"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["channel_id"] == CHANNEL
    assert "5 video(s)" in body["message"]
    assert "nothing already published is announced" in body["message"]
    assert (await get_link(web.db, 21))["channel_id"] == CHANNEL
    kinds = await wf.kinds_in(web.db)
    assert kinds.count("web.youtube.link") == 1
    assert "youtube.link" not in kinds


async def test_a_link_whose_feed_would_not_answer_says_the_seed_is_still_to_come(
    client, sign_in, web, guild, wf
):
    """Claiming a check that was skipped is a lie (checklist 10), so it says so instead."""
    wf.member(guild, 21, name="ada")
    web.cogs["YouTube"] = FakeCog(web.db, seeds=0)
    sign_in(client)

    body = client.post(
        "/api/youtube/links", json={"member_id": "21", "channel": CHANNEL}
    ).json()

    assert body["seeded"] is False
    assert "would not answer" in body["message"]
    assert "no announcement is made" in body["message"]


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
    assert "YouTube uploads" in response.json()["message"]


async def test_videos_come_back_newest_first_with_a_state_the_table_can_colour(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    await a_video(web.db, 21, "vid1", announced="2026-09-02T00:00:00+00:00", mode="on")
    await a_video(web.db, 21, "vid2", kind=SHORT)
    await a_video(web.db, 21, "vid3", announced="2026-09-03T00:00:00+00:00", mode="shadow")
    sign_in(client)

    rows = client.get("/api/youtube/videos", params={"limit": 10}).json()

    assert [row["video_id"] for row in rows] == ["vid3", "vid2", "vid1"]
    assert [row["state"] for row in rows] == ["would", "skipped", "announced"]
    assert rows[1]["kind"] == SHORT
    assert rows[0]["user_name"] == "Ada"
    assert rows[0]["url"] == "https://www.youtube.com/watch?v=vid3"


async def test_the_video_limit_is_clamped_at_both_ends(client, sign_in, web):
    sign_in(client)

    assert client.get("/api/youtube/videos", params={"limit": 10000}).status_code == 200
    assert client.get("/api/youtube/videos", params={"limit": 0}).status_code == 200


def test_state_reads_the_mode_that_was_stored_not_the_one_set_now():
    assert state_of({"announced_at": "x", "mode": "on"}) == "announced"
    assert state_of({"announced_at": "x", "mode": "shadow"}) == "would"
    assert state_of({"announced_at": None, "mode": None}) == "skipped"


async def test_status_says_whether_the_key_is_set_and_how_the_sweep_is_doing(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="ada")
    await set_link(web.db, 21, CHANNEL)
    await a_video(web.db, 21, "vid1", announced="2026-09-02T00:00:00+00:00", mode="on")
    web.cogs["YouTube"] = FakeCog(web.db, keyed=True)
    sign_in(client)

    body = client.get("/api/youtube/status").json()

    assert body["api_key_set"] is True
    assert body["running"] is True
    assert body["last_ok_at"] == "2026-09-02T00:00:00+00:00"
    assert body["last_error"] is None
    assert body["unchanged_ratio"] == 0.25
    assert body["links"] == 1 and body["videos"] == 1 and body["announced"] == 1
    assert body["live_mode"] == "off" and body["live_minutes"] == 5
    assert body["live_end_misses"] == 2 and body["live_running"] is True
    assert body["last_probe_at"] == "2026-09-17T13:00:00+00:00"
    assert body["last_probe_error"] is None
    assert body["probed"] == 3 and body["quota_today"] == 0 and body["live_now"] == 0
    assert body["botcheck"] is False


async def test_status_says_when_the_last_probe_was_served_youtubes_bot_check(
    client, sign_in, web, guild, wf
):
    """KI-30: staff can see why a live stream was announced without its video id."""
    cog = FakeCog(web.db, keyed=True)
    cog.last_botcheck = True
    web.cogs["YouTube"] = cog
    sign_in(client)

    assert client.get("/api/youtube/status").json()["botcheck"] is True


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
    assert body["running"] is False
    assert body["live_running"] is False
    assert body["live_mode"] == "off"
    assert body["last_ok_at"] is None
    assert body["unchanged_ratio"] is None
