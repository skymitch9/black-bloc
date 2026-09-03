from __future__ import annotations

import json
from pathlib import Path

import pytest
from discord import app_commands

from black_bloc.cogs.content.youtube import (
    NOT_LINKED,
    POLL_FAILURES_BEFORE_DEGRADED,
    YouTube,
    all_links,
    counts,
    get_link,
    known_ids,
    recent_videos,
    set_link,
)
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore
from black_bloc.storage.db import Database
from black_bloc.youtube import LIVE, SHORT, VIDEO, YouTubeError, parse_feed

FEED = (Path(__file__).resolve().parents[2] / "fixtures" / "youtube_feed.xml").read_text(
    encoding="utf-8"
)
VIDEOS = parse_feed(FEED)
CHANNEL = "UCsXVk37bltHxD1rDPwtNM8Q"
GUILD = 7
TEST_CHANNEL = 111
GOLIVE_CHANNEL = 222
UPLOAD_CHANNEL = 333
STREAMER = 900
FAN_ROLE = 4242
PING_ROLE = 5151


# --- the doubles -------------------------------------------------------------------------------


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id
        self.name = f"role-{role_id}"
        self.mention = f"<@&{role_id}>"


class FakeMessage:
    def __init__(self, message_id):
        self.id = message_id


class FakeChannel:
    def __init__(self, channel_id):
        self.id = channel_id
        self.mention = f"<#{channel_id}>"
        self.posts = []
        self.explode = None

    async def send(self, content=None, **kwargs):
        if self.explode is not None:
            raise self.explode
        self.posts.append({"content": content, **kwargs})
        return FakeMessage(9000 + len(self.posts))


class FakeMember:
    def __init__(self, guild, user_id=STREAMER, name="Casey"):
        self.id = user_id
        self.guild = guild
        self.display_name = name
        self.name = name.lower()
        self.mention = f"<@{user_id}>"
        self.bot = False
        self.roles = []
        guild.members[user_id] = self


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black Bloc"
        self.channels = {}
        self.members = {}
        self.roles = [FakeRole(FAN_ROLE), FakeRole(PING_ROLE)]
        self.unavailable = False

    def add(self, channel):
        self.channels[channel.id] = channel
        return channel

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_member(self, user_id):
        return self.members.get(user_id)

    def get_role(self, role_id):
        return next((role for role in self.roles if role.id == role_id), None)


class FakeGuard:
    def __init__(self, allowed):
        self.allowed = allowed

    def allows_channel(self, channel_id):
        return int(channel_id) in self.allowed


class FakeBot:
    def __init__(self, db, store, guild, settings):
        self.db = db
        self.store = store
        self.guild = guild
        self.guilds = [guild]
        self.settings = settings
        self.guard = None

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.deferred = False

    async def defer(self, ephemeral=False):
        self.deferred = True

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.response.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeInteraction:
    def __init__(self, bot, user):
        self.client = bot
        self.user = user
        self.guild = bot.guild
        self.guild_id = bot.guild.id
        self.channel_id = TEST_CHANNEL
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)

    @property
    def sent(self):
        return self.response.messages[-1]["content"] if self.response.messages else None


class _Feed:
    """A stand-in YouTubeClient: hands back canned feeds and records what was asked."""

    def __init__(self, *rounds, keyed=False, kinds=None, resolves=None):
        self.rounds = list(rounds)
        self.keyed = keyed
        self.kinds = kinds or {}
        self.resolves = resolves
        self.asked: list[str] = []
        self.closed = False

    async def fetch_feed(self, channel_id, etag=None):
        self.asked.append(channel_id)
        reply = self.rounds.pop(0) if self.rounds else (200, None, [])
        if isinstance(reply, Exception):
            raise reply
        return reply

    async def classify(self, video_ids):
        return {one: self.kinds[one] for one in video_ids if one in self.kinds}

    async def resolve(self, text):
        if isinstance(self.resolves, Exception):
            raise self.resolves
        return self.resolves or (CHANNEL, "Kurzgesagt")

    async def close(self):
        self.closed = True


# --- fixtures ----------------------------------------------------------------------------------


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "yt.sqlite3")
    await database.connect()
    try:
        yield database
    finally:
        await database.close()


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", TEST_CHANNEL)
    await store.set(GUILD, "golive_channel_id", GOLIVE_CHANNEL)
    guild = FakeGuild()
    for channel_id in (TEST_CHANNEL, GOLIVE_CHANNEL, UPLOAD_CHANNEL):
        guild.add(FakeChannel(channel_id))
    return FakeBot(db, store, guild, settings)


@pytest.fixture
def cog(bot):
    return YouTube(bot)


@pytest.fixture
def member(bot):
    return FakeMember(bot.guild)


async def kinds_logged(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def details_logged(db, kind):
    cur = await db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id", (kind,)
    )
    return [json.loads(row["details"]) for row in await cur.fetchall() if row["details"]]


async def linked(db, cog, feed=None, seeded=True):
    await set_link(db, STREAMER, CHANNEL, None, "Kurzgesagt")
    if seeded:
        await db.conn.execute("UPDATE youtube_links SET seeded = 1 WHERE user_id = ?", (STREAMER,))
        await db.conn.commit()
    if feed is not None:
        cog.client = feed
    return await get_link(db, STREAMER)


async def on_mode(bot, mode="on"):
    await bot.store.set(GUILD, "youtube_mode", mode)


# --- seeding: D10 ------------------------------------------------------------------------------


async def test_the_first_sweep_after_a_link_counts_everything_as_seen_and_announces_nothing(
    bot, cog, db, member
):
    await on_mode(bot)
    await linked(db, cog, _Feed((200, None, VIDEOS)), seeded=False)

    await cog.poll_once()

    assert await known_ids(db, STREAMER) == {video.video_id for video in VIDEOS}
    assert bot.guild.get_channel(GOLIVE_CHANNEL).posts == []
    assert "youtube.announce" not in await kinds_logged(db)
    assert (await details_logged(db, "youtube.seeded"))[0]["counted_as_seen"] == 5


async def test_a_seeded_link_is_not_seeded_twice(bot, cog, db, member):
    await linked(db, cog, _Feed((200, None, VIDEOS), (200, None, VIDEOS)), seeded=False)

    await cog.poll_once()
    await cog.poll_once()

    assert (await kinds_logged(db)).count("youtube.seeded") == 1
    assert (await get_link(db, STREAMER))["seeded"] == 1


async def test_a_video_published_after_the_seed_is_the_one_that_gets_announced(
    bot, cog, db, member
):
    await on_mode(bot)
    older, newer = VIDEOS[2], VIDEOS[2]
    feed = _Feed((200, None, [older]), (200, None, [older, newer]))
    await linked(db, cog, feed, seeded=False)

    await cog.poll_once()
    await cog.poll_once()

    assert bot.guild.get_channel(GOLIVE_CHANNEL).posts == []


# --- announcing --------------------------------------------------------------------------------


async def test_a_new_full_video_is_posted_to_the_go_live_channel_when_no_upload_one_is_set(
    bot, cog, db, member
):
    """D3: a blank youtube_channel_id is the go-live channel, not nowhere."""
    await on_mode(bot)
    await linked(db, cog, _Feed((200, None, [VIDEOS[2]])))

    await cog.poll_once()

    posts = bot.guild.get_channel(GOLIVE_CHANNEL).posts
    assert len(posts) == 1
    assert "Casey" in posts[0]["content"]
    assert VIDEOS[2].url in posts[0]["content"]
    assert bot.guild.get_channel(UPLOAD_CHANNEL).posts == []


async def test_the_upload_channel_wins_once_it_is_set(bot, cog, db, member):
    await on_mode(bot)
    await bot.store.set(GUILD, "youtube_channel_id", UPLOAD_CHANNEL)
    await linked(db, cog, _Feed((200, None, [VIDEOS[2]])))

    await cog.poll_once()

    assert len(bot.guild.get_channel(UPLOAD_CHANNEL).posts) == 1
    assert bot.guild.get_channel(GOLIVE_CHANNEL).posts == []


async def test_the_row_is_written_before_the_post_so_a_crash_loses_one_never_duplicates(
    bot, cog, db, member
):
    await on_mode(bot)
    bot.guild.get_channel(GOLIVE_CHANNEL).explode = RuntimeError("discord fell over")
    await linked(db, cog, _Feed((200, None, [VIDEOS[2]])))

    await cog.poll_once()

    rows = await recent_videos(db)
    assert [row["video_id"] for row in rows] == [VIDEOS[2].video_id]
    assert rows[0]["announced_at"] is None
    assert "youtube.post_failed" in await kinds_logged(db)


async def test_the_same_video_is_never_announced_twice_however_often_it_is_polled(
    bot, cog, db, member
):
    await on_mode(bot)
    await linked(db, cog, _Feed((200, None, [VIDEOS[2]]), (200, None, [VIDEOS[2]])))

    await cog.poll_once()
    await cog.poll_once()

    assert len(bot.guild.get_channel(GOLIVE_CHANNEL).posts) == 1


async def test_the_mode_at_the_time_is_stored_on_the_row_so_a_later_flip_cannot_rewrite_it(
    bot, cog, db, member
):
    await on_mode(bot)
    await linked(db, cog, _Feed((200, None, [VIDEOS[2]])))

    await cog.poll_once()
    await on_mode(bot, "off")

    row = (await recent_videos(db))[0]
    assert row["mode"] == "on"
    assert row["announced_message_id"] is not None


# --- modes -------------------------------------------------------------------------------------


async def test_off_posts_nothing_and_logs_no_announcement_at_all(bot, cog, db, member):
    await on_mode(bot, "off")
    await linked(db, cog, _Feed((200, None, [VIDEOS[2]])))

    await cog.poll_once()

    assert bot.guild.get_channel(GOLIVE_CHANNEL).posts == []
    logged = await kinds_logged(db)
    assert "youtube.announce" not in logged and "youtube.would_announce" not in logged


async def test_shadow_writes_the_would_line_with_the_rendered_text_and_posts_nothing(
    bot, cog, db, member
):
    await on_mode(bot, "shadow")
    await linked(db, cog, _Feed((200, None, [VIDEOS[2]])))

    await cog.poll_once()

    assert bot.guild.get_channel(GOLIVE_CHANNEL).posts == []
    said = (await details_logged(db, "youtube.would_announce"))[0]
    assert "Casey" in said["text"]
    assert said["mode"] == "shadow"
    assert said["video_id"] == VIDEOS[2].video_id
    assert (await recent_videos(db))[0]["mode"] == "shadow"


async def test_ships_off_so_nothing_is_announced_before_a_lead_says_so(bot, cog, db, member):
    """D8: the registry default, checked here because a feature that ships on is the bug."""
    assert bot.store.get(GUILD, "youtube_mode") == "off"


# --- test mode ---------------------------------------------------------------------------------


async def test_test_mode_refuses_the_post_and_says_so_as_a_would_line_not_a_failure(
    bot, cog, db, member
):
    """The owner's rule: the bot speaks only in the test channel; the refusal is not a fault."""
    await on_mode(bot)
    bot.guard = FakeGuard({TEST_CHANNEL})
    await linked(db, cog, _Feed((200, None, [VIDEOS[2]])))

    await cog.poll_once()

    assert bot.guild.get_channel(GOLIVE_CHANNEL).posts == []
    logged = await kinds_logged(db)
    assert "youtube.would_announce" in logged
    assert "youtube.post_failed" not in logged
    assert (await details_logged(db, "youtube.would_announce"))[0]["reason"] == "test_mode"


async def test_the_test_channel_itself_is_still_posted_to(bot, cog, db, member):
    await on_mode(bot)
    bot.guard = FakeGuard({TEST_CHANNEL})
    await bot.store.set(GUILD, "youtube_channel_id", TEST_CHANNEL)
    await linked(db, cog, _Feed((200, None, [VIDEOS[2]])))

    await cog.poll_once()

    assert len(bot.guild.get_channel(TEST_CHANNEL).posts) == 1


# --- shorts: D5 --------------------------------------------------------------------------------


async def test_a_short_is_skipped_by_default_and_the_reason_is_in_the_log(bot, cog, db, member):
    await on_mode(bot)
    short = next(video for video in VIDEOS if video.kind == SHORT)
    await linked(db, cog, _Feed((200, None, [short])))

    await cog.poll_once()

    assert bot.guild.get_channel(GOLIVE_CHANNEL).posts == []
    assert (await details_logged(db, "youtube.skipped"))[0]["reason"] == "short"
    assert (await recent_videos(db))[0]["kind"] == SHORT


async def test_a_short_is_announced_once_the_setting_says_so(bot, cog, db, member):
    await on_mode(bot)
    await bot.store.set(GUILD, "youtube_announce_shorts", True)
    short = next(video for video in VIDEOS if video.kind == SHORT)
    await linked(db, cog, _Feed((200, None, [short])))

    await cog.poll_once()

    assert len(bot.guild.get_channel(GOLIVE_CHANNEL).posts) == 1


async def test_shorts_are_told_apart_with_no_api_key_at_all(bot, cog, db, member):
    """Measured 2026-09-02: the /shorts/ address is the signal, so the key is not needed."""
    await on_mode(bot)
    await linked(db, cog, _Feed((200, None, VIDEOS)))

    await cog.poll_once()

    posted = len(bot.guild.get_channel(GOLIVE_CHANNEL).posts)
    assert posted == 2
    assert len(await details_logged(db, "youtube.skipped")) == 3


# --- live streams: D6 --------------------------------------------------------------------------


async def test_the_api_key_calls_a_live_broadcast_live_and_it_is_skipped(bot, cog, db, member):
    await on_mode(bot)
    feed = _Feed((200, None, [VIDEOS[2]]), keyed=True, kinds={VIDEOS[2].video_id: LIVE})
    await linked(db, cog, feed)

    await cog.poll_once()

    assert bot.guild.get_channel(GOLIVE_CHANNEL).posts == []
    assert (await details_logged(db, "youtube.skipped"))[0]["reason"] == "live"


async def test_without_a_key_an_open_youtube_go_live_session_is_what_marks_an_entry_live(
    bot, cog, db, member
):
    """D6's fallback: the only live signal a keyless feed has is the member's own session."""
    await on_mode(bot)
    await db.conn.execute(
        "INSERT INTO golive_sessions(guild_id, user_id, source, platform, started_at, mode) "
        "VALUES (?, ?, 'presence', 'YouTube', '2026-09-02T00:00:00+00:00', 'on')",
        (GUILD, STREAMER),
    )
    await db.conn.commit()
    await linked(db, cog, _Feed((200, None, [VIDEOS[2]])))

    await cog.poll_once()

    assert bot.guild.get_channel(GOLIVE_CHANNEL).posts == []
    assert (await details_logged(db, "youtube.skipped"))[0]["reason"] == "live"


async def test_a_twitch_session_does_not_make_a_youtube_upload_look_live(bot, cog, db, member):
    await on_mode(bot)
    await db.conn.execute(
        "INSERT INTO golive_sessions(guild_id, user_id, source, platform, started_at, mode) "
        "VALUES (?, ?, 'twitch', 'Twitch', '2026-09-02T00:00:00+00:00', 'on')",
        (GUILD, STREAMER),
    )
    await db.conn.commit()
    await linked(db, cog, _Feed((200, None, [VIDEOS[2]])))

    await cog.poll_once()

    assert len(bot.guild.get_channel(GOLIVE_CHANNEL).posts) == 1


# --- pings: D4 ---------------------------------------------------------------------------------


async def test_the_ping_role_and_the_fan_role_are_both_mentioned_and_both_allowed(
    bot, cog, db, member
):
    await on_mode(bot)
    await bot.store.set(GUILD, "youtube_ping_role_id", PING_ROLE)
    await bot.store.set(GUILD, "pings_mode", "on")
    await db.conn.execute(
        "INSERT INTO golive_fan_roles(guild_id, user_id, role_id, created_at) "
        "VALUES (?, ?, ?, '2026-09-02T00:00:00+00:00')",
        (GUILD, STREAMER, FAN_ROLE),
    )
    await db.conn.commit()
    await linked(db, cog, _Feed((200, None, [VIDEOS[2]])))

    await cog.poll_once()

    post = bot.guild.get_channel(GOLIVE_CHANNEL).posts[0]
    assert post["content"].startswith(f"<@&{PING_ROLE}> <@&{FAN_ROLE}> ")
    allowed = post["allowed_mentions"]
    assert allowed.everyone is False and allowed.users is False
    assert {role.id for role in allowed.roles} == {PING_ROLE, FAN_ROLE}


async def test_turning_the_fan_roles_off_leaves_only_the_one_ping_role(bot, cog, db, member):
    await on_mode(bot)
    await bot.store.set(GUILD, "youtube_ping_role_id", PING_ROLE)
    await bot.store.set(GUILD, "youtube_ping_fan_roles", False)
    await bot.store.set(GUILD, "pings_mode", "on")
    await db.conn.execute(
        "INSERT INTO golive_fan_roles(guild_id, user_id, role_id, created_at) "
        "VALUES (?, ?, ?, '2026-09-02T00:00:00+00:00')",
        (GUILD, STREAMER, FAN_ROLE),
    )
    await db.conn.commit()
    await linked(db, cog, _Feed((200, None, [VIDEOS[2]])))

    await cog.poll_once()

    post = bot.guild.get_channel(GOLIVE_CHANNEL).posts[0]
    assert post["content"].startswith(f"<@&{PING_ROLE}> ")
    assert f"<@&{FAN_ROLE}>" not in post["content"]


async def test_a_display_name_carrying_everyone_cannot_ping_it(bot, cog, db):
    """Checklist 11: the name is attacker-controlled, so allowed_mentions is what stops it."""
    await on_mode(bot)
    FakeMember(bot.guild, name="@everyone")
    await linked(db, cog, _Feed((200, None, [VIDEOS[2]])))

    await cog.poll_once()

    allowed = bot.guild.get_channel(GOLIVE_CHANNEL).posts[0]["allowed_mentions"]
    assert allowed.everyone is False and allowed.roles is False


# --- the feed's flakiness ----------------------------------------------------------------------


async def test_a_channel_whose_feed_will_not_answer_leaves_the_link_alone(bot, cog, db, member):
    """Measured: a 404 is the feed misbehaving, so nothing is unlinked and nothing is seeded."""
    await linked(db, cog, _Feed(YouTubeError("the feed would not answer")))

    await cog.poll_once()

    assert len(await all_links(db)) == 1
    assert cog.last_poll_error is not None


async def test_three_dead_sweeps_in_a_row_write_one_degraded_line_not_three(bot, cog, db, member):
    await linked(
        db, cog, _Feed(*[YouTubeError("down")] * (POLL_FAILURES_BEFORE_DEGRADED + 2))
    )

    for _ in range(POLL_FAILURES_BEFORE_DEGRADED + 2):
        await cog.poll_once()

    assert (await kinds_logged(db)).count("youtube.poll_degraded") == 1


async def test_one_good_sweep_clears_the_failure_count(bot, cog, db, member):
    await linked(db, cog, _Feed(YouTubeError("down"), (200, None, [])))

    await cog.poll_once()
    await cog.poll_once()

    assert cog.poll_failures == 0
    assert cog.last_poll_ok_at is not None
    assert cog.last_poll_error is None


async def test_a_304_changes_nothing_and_costs_no_announcement(bot, cog, db, member):
    await on_mode(bot)
    await linked(db, cog, _Feed((304, "W/x", [])))

    await cog.poll_once()

    assert bot.guild.get_channel(GOLIVE_CHANNEL).posts == []
    assert cog.unchanged == 1


async def test_the_health_the_page_reads_is_this_cogs_own_record(bot, cog, db, member):
    assert cog.loop_health("poller") == (None, None)
    assert cog.loop_health("not_a_loop") == (None, None)
    await linked(db, cog, _Feed((200, None, [])))

    await cog.poll_once()

    assert cog.loop_health("poller")[0] is not None


# --- one channel, two members ------------------------------------------------------------------


async def test_a_channel_linked_twice_is_polled_once_and_warns(bot, cog, db, member, caplog):
    await set_link(db, STREAMER, CHANNEL, None, "Kurzgesagt")
    await set_link(db, STREAMER + 1, CHANNEL, None, "Kurzgesagt")
    cog.client = _Feed((200, None, []), (200, None, []))

    await cog.poll_once()

    assert cog.client.asked == [CHANNEL]
    assert "linked to both" in caplog.text


# --- the poll gap is a setting ------------------------------------------------------------------


async def test_the_gap_between_sweeps_is_re_read_rather_than_frozen_at_boot(bot, cog):
    assert cog._minutes() == 10
    cog._retime()
    assert cog.poller.minutes == 10

    await bot.store.set(GUILD, "youtube_poll_minutes", 30)
    cog._retime()

    assert cog.poller.minutes == 30


# --- the member commands -------------------------------------------------------------------------


async def test_link_resolves_seeds_and_says_how_many_were_counted_as_history(
    bot, cog, db, member
):
    cog.client = _Feed((200, None, VIDEOS), resolves=(CHANNEL, "Kurzgesagt"))
    interaction = FakeInteraction(bot, member)

    await cog.link.callback(cog, interaction, "@kurzgesagt")

    assert (await get_link(db, STREAMER))["channel_id"] == CHANNEL
    assert "Kurzgesagt" in interaction.sent
    assert "5" in interaction.sent
    assert await known_ids(db, STREAMER) == {video.video_id for video in VIDEOS}
    assert "youtube.link" in await kinds_logged(db)


async def test_link_says_out_loud_that_announcements_are_off(bot, cog, db, member):
    cog.client = _Feed((200, None, []), resolves=(CHANNEL, "Kurzgesagt"))
    interaction = FakeInteraction(bot, member)

    await cog.link.callback(cog, interaction, CHANNEL)

    assert "off" in interaction.sent
    assert "/uploads mode on" in interaction.sent


async def test_a_channel_that_cannot_be_resolved_is_refused_in_words_and_logged(
    bot, cog, db, member
):
    cog.client = _Feed(resolves=YouTubeError("I could not turn that into a channel id"))
    interaction = FakeInteraction(bot, member)

    await cog.link.callback(cog, interaction, "not a channel")

    assert "could not turn" in interaction.sent
    assert await get_link(db, STREAMER) is None
    assert "youtube.resolve_failed" in await kinds_logged(db)


async def test_a_channel_somebody_else_owns_is_refused_with_a_sentence(bot, cog, db, member):
    """Checklist 16: two members must not silently claim one external identity."""
    await set_link(db, STREAMER + 1, CHANNEL, None, "Kurzgesagt")
    cog.client = _Feed((200, None, []), resolves=(CHANNEL, "Kurzgesagt"))
    interaction = FakeInteraction(bot, member)

    await cog.link.callback(cog, interaction, CHANNEL)

    assert "already linked to another member" in interaction.sent
    assert "ask a Lead" in interaction.sent
    assert await get_link(db, STREAMER) is None


async def test_unlink_without_a_link_says_so_and_names_the_command_that_makes_one(
    bot, cog, db, member
):
    interaction = FakeInteraction(bot, member)

    await cog.unlink.callback(cog, interaction)

    assert interaction.sent == NOT_LINKED
    assert "/youtube link" in interaction.sent


async def test_unlink_forgets_the_channel(bot, cog, db, member):
    await linked(db, cog)
    interaction = FakeInteraction(bot, member)

    await cog.unlink.callback(cog, interaction)

    assert await get_link(db, STREAMER) is None
    assert "youtube.unlink" in await kinds_logged(db)


async def test_status_says_where_uploads_go_and_what_happens_to_shorts(bot, cog, db, member):
    await on_mode(bot)
    await linked(db, cog)
    interaction = FakeInteraction(bot, member)

    await cog.status.callback(cog, interaction)

    assert "Kurzgesagt" in interaction.sent
    assert f"<#{GOLIVE_CHANNEL}>" in interaction.sent
    assert "not announced" in interaction.sent


async def test_status_explains_the_mode_rather_than_saying_a_bare_no(bot, cog, db, member):
    await linked(db, cog)
    interaction = FakeInteraction(bot, member)

    await cog.status.callback(cog, interaction)

    assert "upload announcements are **off**" in interaction.sent


async def test_status_with_no_link_points_at_the_command_that_makes_one(bot, cog, db, member):
    interaction = FakeInteraction(bot, member)

    await cog.status.callback(cog, interaction)

    assert "/youtube link" in interaction.sent


# --- the staff commands ---------------------------------------------------------------------------


def _staff(bot, member):
    bot.store.is_staff = lambda who: True


async def test_mode_is_staff_only(bot, cog, db, member):
    bot.store.is_staff = lambda who: False
    interaction = FakeInteraction(bot, member)
    choice = app_commands.Choice(name="on", value="on")

    await cog.mode.callback(cog, interaction, choice)

    assert "staff only" in interaction.sent
    assert bot.store.get(GUILD, "youtube_mode") == "off"


async def test_mode_on_with_nowhere_to_post_says_so_rather_than_going_quiet(
    bot, cog, db, member
):
    _staff(bot, member)
    real = bot.store.get
    bot.store.get = lambda guild_id, key: (
        None if key in ("youtube_channel_id", "golive_channel_id") else real(guild_id, key)
    )
    interaction = FakeInteraction(bot, member)

    await cog.mode.callback(cog, interaction, app_commands.Choice(name="on", value="on"))

    assert "nowhere to go" in interaction.sent
    assert "/uploads setup" in interaction.sent


async def test_setup_points_the_uploads_at_a_channel_and_a_role(bot, cog, db, member):
    _staff(bot, member)
    interaction = FakeInteraction(bot, member)
    channel = bot.guild.get_channel(UPLOAD_CHANNEL)

    await cog.setup_uploads.callback(cog, interaction, channel, FakeRole(PING_ROLE))

    assert bot.store.get(GUILD, "youtube_channel_id") == UPLOAD_CHANNEL
    assert bot.store.get(GUILD, "youtube_ping_role_id") == PING_ROLE
    assert "youtube.setup" in await kinds_logged(db)


async def test_setup_with_nothing_given_changes_nothing_and_says_what_to_pass(
    bot, cog, db, member
):
    _staff(bot, member)
    interaction = FakeInteraction(bot, member)

    await cog.setup_uploads.callback(cog, interaction, None, None)

    assert "Pass a channel" in interaction.sent
    assert bot.store.get(GUILD, "youtube_channel_id") is None


async def test_link_for_links_somebody_else_and_logs_who_did_it(bot, cog, db, member):
    _staff(bot, member)
    other = FakeMember(bot.guild, user_id=STREAMER + 1, name="Rivet")
    cog.client = _Feed((200, None, VIDEOS), resolves=(CHANNEL, "Kurzgesagt"))
    interaction = FakeInteraction(bot, member)

    await cog.link_for.callback(cog, interaction, other, CHANNEL)

    assert (await get_link(db, other.id))["channel_id"] == CHANNEL
    assert "Rivet" in interaction.sent


async def test_unlink_for_somebody_with_no_link_says_where_to_look(bot, cog, db, member):
    _staff(bot, member)
    other = FakeMember(bot.guild, user_id=STREAMER + 1, name="Rivet")
    interaction = FakeInteraction(bot, member)

    await cog.unlink_for.callback(cog, interaction, other)

    assert "has no YouTube channel linked" in interaction.sent
    assert "/uploads list" in interaction.sent


async def test_list_shows_health_and_whether_the_key_is_set(bot, cog, db, member):
    _staff(bot, member)
    await linked(db, cog)
    interaction = FakeInteraction(bot, member)

    await cog.list_links.callback(cog, interaction)

    assert "not set (feed only)" in interaction.sent
    assert "Kurzgesagt" in interaction.sent
    assert "last good sweep" in interaction.sent


async def test_list_with_nobody_linked_says_so(bot, cog, db, member):
    _staff(bot, member)
    interaction = FakeInteraction(bot, member)

    await cog.list_links.callback(cog, interaction)

    assert "Nobody has linked" in interaction.sent


# --- the store helpers ----------------------------------------------------------------------------


async def test_counts_are_read_off_the_tables_not_kept_in_memory(bot, cog, db, member):
    await on_mode(bot)
    await linked(db, cog, _Feed((200, None, [VIDEOS[2]])))

    await cog.poll_once()

    assert await counts(db) == {"links": 1, "videos": 1, "announced": 1}


async def test_a_member_the_bot_cannot_see_still_has_the_video_recorded(bot, cog, db):
    """No member, no announcement — but the row is stored so it is not announced later either."""
    await on_mode(bot)
    await linked(db, cog, _Feed((200, None, [VIDEOS[2]])))

    await cog.poll_once()

    assert [row["video_id"] for row in await recent_videos(db)] == [VIDEOS[2].video_id]
    assert bot.guild.get_channel(GOLIVE_CHANNEL).posts == []


async def test_closing_the_cog_closes_the_client_session(bot, cog):
    cog.client = _Feed()

    await cog.cog_unload()

    assert cog.client.closed is True


async def test_a_kind_the_feed_alone_cannot_settle_is_still_a_video(bot, cog, db, member):
    await on_mode(bot)
    assert VIDEOS[2].kind == VIDEO
    await linked(db, cog, _Feed((200, None, [VIDEOS[2]])))

    await cog.poll_once()

    assert (await recent_videos(db))[0]["kind"] == VIDEO
