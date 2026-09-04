from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import discord
import pytest

from black_bloc.cogs.content.youtube import (
    FANS_ON,
    FORGET_BUTTON,
    LINK_LABEL,
    MODE_PLACEHOLDER,
    NOT_LINKED,
    NUMBERS_BUTTON,
    PICK_A_CHANNEL,
    POLL_FAILURES_BEFORE_DEGRADED,
    SHORTS_OFF,
    SHORTS_ON,
    SITE_BUTTON,
    WHERE_UPLOADS,
    WHO_IS_PINGED,
    WORDS_BUTTON,
    ForgetPick,
    LinkedPick,
    LinkModal,
    ModePick,
    NumbersModal,
    UploadChannelPick,
    WhoPick,
    YouTube,
    YouTubePanel,
    all_links,
    build_panel,
    counts,
    get_link,
    known_ids,
    recent_videos,
    run_link,
    run_setup,
    save_setup,
    set_link,
    set_mode,
    setup_embed,
    setup_view,
    unlink_channel,
)
from black_bloc.config import load_settings
from black_bloc.settings_store import DB_UNAVAILABLE, SettingsStore
from black_bloc.storage.db import Database
from black_bloc.youtube import (
    CANNOT_RESOLVE,
    FEED_REFUSED,
    KEEP_IT,
    LIVE,
    PANEL_TIMEOUT_FOOTER,
    PANEL_TITLE,
    SHORT,
    UNLINK_QUESTION,
    UNLINK_YES,
    VIDEO,
    YouTubeError,
    card_buttons,
    parse_feed,
)

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
    def __init__(self, message_id, **kwargs):
        self.id = message_id
        self.kwargs = kwargs

    async def edit(self, **kwargs):
        self.kwargs |= kwargs

    @property
    def embeds(self):
        held = self.kwargs.get("embeds")
        if held is not None:
            return list(held)
        one = self.kwargs.get("embed")
        return [one] if one is not None else []


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
        self.dms = []
        self.dm_error = None
        guild.members[user_id] = self

    async def send(self, content=None, **kwargs):
        if self.dm_error is not None:
            raise self.dm_error
        self.dms.append({"content": content, **kwargs})
        return FakeMessage(len(self.dms))


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
        self.cogs = {}

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def get_cog(self, name):
        return self.cogs.get(name)

    def get_user(self, user_id):
        return self.guild.get_member(user_id)


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.modals = []
        self.deferred = False

    def is_done(self):
        return self.deferred or bool(self.messages)

    async def defer(self, ephemeral=False):
        self.deferred = True

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def send_modal(self, modal):
        self.modals.append(modal)
        self.deferred = True


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
        self.edits = []

    async def original_response(self):
        return FakeMessage(1)

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return FakeMessage(9500, **kwargs)

    @property
    def rendered(self):
        if self.edits:
            return self.edits[-1]
        return self.response.messages[-1] if self.response.messages else {}

    @property
    def view(self):
        return self.rendered.get("view")

    @property
    def embed(self):
        return self.rendered.get("embed")

    @property
    def sent(self):
        said = [
            one["content"] for one in self.response.messages if one.get("content") is not None
        ]
        return said[-1] if said else None

    @property
    def ephemeral(self):
        return all(one["ephemeral"] for one in self.response.messages)


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
    made = YouTube(bot)
    bot.cogs["YouTube"] = made
    return made


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


# --- the panel: what renders ---------------------------------------------------------------------


def _staff(bot, yes=True):
    bot.store.is_staff = lambda who: yes


def labels(view):
    return [one.label for one in view.children if getattr(one, "label", None)]


def placeholders(view):
    return [
        one.placeholder for one in view.children if getattr(one, "placeholder", None) is not None
    ]


def button(view, label):
    return next(one for one in view.children if getattr(one, "label", None) == label)


async def test_the_command_answers_one_ephemeral_panel_and_nothing_else(bot, cog, db, member):
    interaction = FakeInteraction(bot, member)

    await cog.youtube.callback(cog, interaction)

    assert len(interaction.response.messages) == 1
    said = interaction.response.messages[0]
    assert said["ephemeral"] is True
    assert said["embed"].title == PANEL_TITLE
    assert said["allowed_mentions"].everyone is False


async def test_a_member_sees_their_own_card_and_none_of_the_staff_half(bot, cog, db, member):
    _staff(bot, False)
    await linked(db, cog)
    interaction = FakeInteraction(bot, member)

    embed, view = await build_panel(bot, bot.guild, member)

    assert "Kurzgesagt" in embed.description
    assert labels(view) == ["Relink…", "Unlink", "Refresh", SITE_BUTTON]
    assert placeholders(view) == []
    assert "last good sweep" not in embed.description
    assert interaction.response.messages == []


async def test_staff_see_the_health_lines_who_is_linked_and_every_staff_control(
    bot, cog, db, member
):
    _staff(bot)
    await linked(db, cog)

    embed, view = await build_panel(bot, bot.guild, member)

    assert "last good sweep" in embed.description
    assert "not set (feed only)" in embed.description
    assert "Kurzgesagt" in embed.description
    assert labels(view) == [
        "Relink…",
        "Unlink",
        "Refresh",
        "Link for somebody…",
        "Setup",
        "Logs",
        SITE_BUTTON,
    ]
    assert placeholders(view) == [PICK_A_CHANNEL, MODE_PLACEHOLDER]


async def test_a_member_is_never_told_who_else_has_a_channel_linked(bot, cog, db, member):
    _staff(bot, False)
    other = FakeMember(bot.guild, user_id=STREAMER + 1, name="Rivet")
    await set_link(db, other.id, CHANNEL, None, "Kurzgesagt")

    embed, _view = await build_panel(bot, bot.guild, member)

    assert "Rivet" not in embed.description
    assert "Kurzgesagt" not in embed.description


@pytest.mark.parametrize("mode", ["off", "shadow", "on"])
@pytest.mark.parametrize("is_linked", [False, True])
@pytest.mark.parametrize("staff", [False, True])
async def test_every_state_renders_exactly_its_row_of_the_button_table(
    bot, cog, db, member, mode, is_linked, staff
):
    """Checklist 3 and 12: the table is data, and no state may render a move it forbids."""
    _staff(bot, staff)
    await on_mode(bot, mode)
    if is_linked:
        await linked(db, cog)

    _embed, view = await build_panel(bot, bot.guild, member)

    wanted = [move.label for move in card_buttons(linked=is_linked, mine=True, staff=staff)]
    assert labels(view) == wanted + [SITE_BUTTON]


async def test_with_the_mode_off_the_embed_says_so_and_link_my_channel_still_renders(
    bot, cog, db, member
):
    _staff(bot, False)
    await on_mode(bot, "off")

    embed, view = await build_panel(bot, bot.guild, member)

    assert "**off**" in embed.description
    assert "Announcements are…" in embed.description
    assert "Link my channel" in labels(view)


async def test_the_off_line_never_tells_anybody_to_run_a_command_that_is_gone(
    bot, cog, db, member
):
    embed, _view = await build_panel(bot, bot.guild, member)

    assert "/uploads" not in embed.description
    assert "/youtube link" not in embed.description


async def test_no_origin_means_no_site_button_rather_than_a_link_that_goes_nowhere(
    bot, cog, db, member
):
    bot.settings = SimpleNamespace(origin="", youtube_api_key=None)

    _embed, view = await build_panel(bot, bot.guild, member)

    assert SITE_BUTTON not in labels(view)


async def test_the_picker_caps_at_twenty_five_and_the_placeholder_says_where_the_rest_are(
    bot, cog, db, member
):
    _staff(bot)
    for spot in range(30):
        await set_link(db, STREAMER + 10 + spot, f"UC{spot:022d}", None, f"channel {spot}")

    _embed, view = await build_panel(bot, bot.guild, member)

    pick = next(one for one in view.children if isinstance(one, LinkedPick))
    assert len(pick.options) == 25
    assert pick.placeholder == "25 of 30 — the rest are on the site"


# --- the panel: linking --------------------------------------------------------------------------


async def test_link_my_channel_opens_the_modal_and_a_relink_arrives_prefilled(
    bot, cog, db, member
):
    await linked(db, cog)
    _embed, view = await build_panel(bot, bot.guild, member)
    interaction = FakeInteraction(bot, member)

    await button(view, "Relink…").callback(interaction)

    modal = interaction.response.modals[0]
    assert isinstance(modal, LinkModal)
    assert modal.channel.default == CHANNEL
    assert modal.channel.label == LINK_LABEL


async def test_the_link_modal_refuses_to_open_while_the_database_is_down(bot, cog, db, member):
    _embed, view = await build_panel(bot, bot.guild, member)
    await db.close()
    interaction = FakeInteraction(bot, member)

    await button(view, "Link my channel").callback(interaction)

    assert interaction.response.modals == []
    assert interaction.sent == DB_UNAVAILABLE


async def test_linking_seeds_the_history_renders_the_card_and_leaves_one_row(
    bot, cog, db, member
):
    cog.client = _Feed((200, None, VIDEOS), resolves=(CHANNEL, "Kurzgesagt"))
    interaction = FakeInteraction(bot, member)

    await run_link(interaction, member, "@kurzgesagt", mine=True)

    assert (await get_link(db, STREAMER))["channel_id"] == CHANNEL
    assert await known_ids(db, STREAMER) == {video.video_id for video in VIDEOS}
    assert "Kurzgesagt" in interaction.sent and "5" in interaction.sent
    assert (await kinds_logged(db)).count("youtube.link") == 1
    assert "Kurzgesagt" in interaction.embed.description


async def test_linking_says_out_loud_that_announcements_are_off(bot, cog, db, member):
    cog.client = _Feed((200, None, []), resolves=(CHANNEL, "Kurzgesagt"))
    interaction = FakeInteraction(bot, member)

    await run_link(interaction, member, CHANNEL, mine=True)

    assert "off" in interaction.sent
    assert "Announcements are…" in interaction.sent


async def test_a_feed_that_would_not_answer_never_claims_a_count_it_did_not_take(
    bot, cog, db, member
):
    """Checklist 10: a check that could not run is said out loud, not reported as done."""
    cog.client = _Feed(YouTubeError("no answer", network=True), resolves=(CHANNEL, "Kurzgesagt"))
    interaction = FakeInteraction(bot, member)

    await run_link(interaction, member, CHANNEL, mine=True)

    assert "would not answer" in interaction.sent
    assert "nothing has been counted as seen yet" in interaction.sent
    assert "already on the channel are counted" not in interaction.sent
    assert (await get_link(db, STREAMER))["seeded"] == 0


async def test_the_three_ways_a_link_can_fail_each_get_their_own_sentence(
    bot, cog, db, member
):
    cog.client = _Feed(resolves=YouTubeError(CANNOT_RESOLVE.format(given="nonsense")))
    bad = FakeInteraction(bot, member)
    await run_link(bad, member, "nonsense", mine=True)

    cog.client = _Feed(resolves=YouTubeError(FEED_REFUSED.format(attempts=4), network=True))
    flaky = FakeInteraction(bot, member)
    await run_link(flaky, member, CHANNEL, mine=True)

    await set_link(db, STREAMER + 1, CHANNEL, None, "Kurzgesagt")
    cog.client = _Feed((200, None, []), resolves=(CHANNEL, "Kurzgesagt"))
    taken = FakeInteraction(bot, member)
    await run_link(taken, member, CHANNEL, mine=True)

    assert "could not turn" in bad.sent
    assert "feed being flaky" in flaky.sent
    assert "already linked to another member" in taken.sent
    assert len({bad.sent, flaky.sent, taken.sent}) == 3
    assert await get_link(db, STREAMER) is None


async def test_a_bad_paste_and_an_outage_are_told_apart_on_the_row_not_by_the_message(
    bot, cog, db, member
):
    cog.client = _Feed(resolves=YouTubeError("nope"))
    await run_link(FakeInteraction(bot, member), member, "nonsense", mine=True)
    cog.client = _Feed(resolves=YouTubeError("down", network=True))
    await run_link(FakeInteraction(bot, member), member, "nonsense", mine=True)

    rows = await details_logged(db, "youtube.resolve_failed")
    assert [row["network"] for row in rows] == [False, True]


async def test_a_channel_somebody_else_owns_leaves_no_row_and_changes_nothing(
    bot, cog, db, member
):
    """Checklist 16: two members must not silently claim one external identity."""
    await set_link(db, STREAMER + 1, CHANNEL, None, "Kurzgesagt")
    cog.client = _Feed((200, None, []), resolves=(CHANNEL, "Kurzgesagt"))
    interaction = FakeInteraction(bot, member)

    await run_link(interaction, member, CHANNEL, mine=True)

    assert "ask a Lead" in interaction.sent
    assert await get_link(db, STREAMER) is None


# --- the panel: unlinking ------------------------------------------------------------------------


async def test_unlink_asks_first_and_keeping_it_changes_nothing(bot, cog, db, member):
    await linked(db, cog)
    _embed, view = await build_panel(bot, bot.guild, member)
    asking = FakeInteraction(bot, member)

    await button(view, "Unlink").callback(asking)

    assert UNLINK_QUESTION in [field.value for field in asking.embed.fields]
    keeping = FakeInteraction(bot, member)
    await button(asking.view, KEEP_IT).callback(keeping)
    assert await get_link(db, STREAMER) is not None


async def test_saying_yes_forgets_the_channel_and_puts_the_link_button_back(
    bot, cog, db, member
):
    await linked(db, cog)
    _embed, view = await build_panel(bot, bot.guild, member)
    asking = FakeInteraction(bot, member)
    await button(view, "Unlink").callback(asking)
    confirming = FakeInteraction(bot, member)

    await button(asking.view, UNLINK_YES).callback(confirming)

    assert await get_link(db, STREAMER) is None
    assert (await kinds_logged(db)).count("youtube.unlink") == 1
    assert "Link my channel" in labels(confirming.view)


async def test_unlinking_yourself_is_never_dmed(bot, cog, db, member):
    await linked(db, cog)
    member.dms = []

    await unlink_channel(bot, bot.guild, member, member)

    assert member.dms == []


async def test_unlink_without_a_link_says_so_without_naming_a_retired_command(
    bot, cog, db, member
):
    said, _row = await unlink_channel(bot, bot.guild, member, member)

    assert said == NOT_LINKED
    assert "/youtube link" not in said


# --- the panel: the staff half -------------------------------------------------------------------


async def test_picking_somebody_opens_their_card_with_the_staff_moves_only(
    bot, cog, db, member
):
    _staff(bot)
    other = FakeMember(bot.guild, user_id=STREAMER + 1, name="Rivet")
    await set_link(db, other.id, CHANNEL, None, "Kurzgesagt")
    _embed, view = await build_panel(bot, bot.guild, member)
    pick = next(one for one in view.children if isinstance(one, LinkedPick))
    pick._values = [str(other.id)]
    interaction = FakeInteraction(bot, member)

    await pick.callback(interaction)

    assert "Rivet" in interaction.embed.description
    assert labels(interaction.view) == [
        "Relink for…",
        "Unlink for",
        "Refresh",
        "Back",
        SITE_BUTTON,
    ]


async def test_link_for_somebody_draws_the_member_picker_only_after_it_is_asked_for(
    bot, cog, db, member
):
    _staff(bot)
    _embed, view = await build_panel(bot, bot.guild, member)
    assert not any(isinstance(one, WhoPick) for one in view.children)
    interaction = FakeInteraction(bot, member)

    await button(view, "Link for somebody…").callback(interaction)

    assert any(isinstance(one, WhoPick) for one in interaction.view.children)


async def test_linking_for_somebody_counts_their_history_and_names_them(bot, cog, db, member):
    _staff(bot)
    other = FakeMember(bot.guild, user_id=STREAMER + 1, name="Rivet")
    cog.client = _Feed((200, None, VIDEOS), resolves=(CHANNEL, "Kurzgesagt"))
    interaction = FakeInteraction(bot, member)

    await run_link(interaction, other, CHANNEL, mine=False)

    assert (await get_link(db, other.id))["channel_id"] == CHANNEL
    assert "Rivet" in interaction.sent
    assert (await kinds_logged(db)).count("youtube.link") == 1


async def test_unlink_for_dms_the_member_the_reason_and_leaves_one_row(bot, cog, db, member):
    _staff(bot)
    other = FakeMember(bot.guild, user_id=STREAMER + 1, name="Rivet")
    await set_link(db, other.id, CHANNEL, None, "Kurzgesagt")

    said, _row = await unlink_channel(bot, bot.guild, member, other, note="wrong channel")

    assert "Rivet" in said
    assert len(other.dms) == 1
    assert "wrong channel" in other.dms[0]["content"]
    assert (await kinds_logged(db)).count("youtube.unlink") == 1


async def test_the_dm_is_a_setting_and_off_means_off(bot, cog, db, member):
    _staff(bot)
    await bot.store.set(GUILD, "youtube_unlink_dms_them", False)
    other = FakeMember(bot.guild, user_id=STREAMER + 1, name="Rivet")
    await set_link(db, other.id, CHANNEL, None, "Kurzgesagt")

    await unlink_channel(bot, bot.guild, member, other, note="wrong channel")

    assert other.dms == []
    assert (await kinds_logged(db)).count("youtube.unlink") == 1


async def test_a_dm_that_cannot_be_delivered_is_a_detail_never_a_second_row(
    bot, cog, db, member
):
    """Checklist 34: one move leaves one row, whatever else went wrong along the way."""
    _staff(bot)
    other = FakeMember(bot.guild, user_id=STREAMER + 1, name="Rivet")
    other.dm_error = RuntimeError("dms are closed")
    await set_link(db, other.id, CHANNEL, None, "Kurzgesagt")

    await unlink_channel(bot, bot.guild, member, other, note="wrong channel")

    assert (await kinds_logged(db)).count("youtube.unlink") == 1
    assert (await details_logged(db, "youtube.unlink"))[0]["dm_failed"] is True


async def test_unlink_for_somebody_with_no_link_says_so_and_writes_nothing(
    bot, cog, db, member
):
    _staff(bot)
    other = FakeMember(bot.guild, user_id=STREAMER + 1, name="Rivet")

    said, _row = await unlink_channel(bot, bot.guild, member, other)

    assert "has no YouTube channel linked" in said
    assert await kinds_logged(db) == []


# --- the panel: the mode select and Setup --------------------------------------------------------


async def test_the_mode_select_writes_through_the_shared_function(bot, cog, db, member):
    _staff(bot)
    _embed, view = await build_panel(bot, bot.guild, member)
    pick = next(one for one in view.children if isinstance(one, ModePick))
    pick._values = ["shadow"]
    interaction = FakeInteraction(bot, member)

    await pick.callback(interaction)

    assert bot.store.get(GUILD, "youtube_mode") == "shadow"
    assert (await kinds_logged(db)).count("youtube.mode") == 1
    assert "shadow" in interaction.sent


async def test_turning_it_on_with_nowhere_to_post_says_so_rather_than_going_quiet(
    bot, cog, db, member
):
    _staff(bot)
    real = bot.store.get
    bot.store.get = lambda guild_id, key: (
        None if key in ("youtube_channel_id", "golive_channel_id") else real(guild_id, key)
    )

    said, _row = await set_mode(bot, bot.guild, member, "on")

    assert "nowhere to go" in said
    assert "Setup" in said


async def test_the_setup_sub_panel_shows_the_mode_as_a_line_not_a_second_select(
    bot, cog, db, member
):
    _staff(bot)
    embed = setup_embed(bot, bot.guild)
    view = setup_view(bot, bot.guild)

    assert "**mode** — off" in embed.description
    assert MODE_PLACEHOLDER not in placeholders(view)
    assert placeholders(view) == [WHERE_UPLOADS, WHO_IS_PINGED]
    assert labels(view) == [
        SHORTS_OFF,
        FANS_ON,
        WORDS_BUTTON,
        NUMBERS_BUTTON,
        "Back",
        FORGET_BUTTON,
        SITE_BUTTON,
    ]


async def test_picking_a_channel_writes_it_and_the_panel_says_where_uploads_go(
    bot, cog, db, member
):
    _staff(bot)
    view = setup_view(bot, bot.guild)
    pick = next(one for one in view.children if isinstance(one, UploadChannelPick))
    pick._values = [SimpleNamespace(id=UPLOAD_CHANNEL)]
    interaction = FakeInteraction(bot, member)

    await pick.callback(interaction)

    assert bot.store.get(GUILD, "youtube_channel_id") == UPLOAD_CHANNEL
    assert f"<#{UPLOAD_CHANNEL}>" in interaction.sent
    assert (await kinds_logged(db)).count("youtube.setup") == 1


async def test_an_empty_picker_clears_the_key_and_says_what_uploads_fall_back_to(
    bot, cog, db, member
):
    _staff(bot)
    await bot.store.set(GUILD, "youtube_channel_id", UPLOAD_CHANNEL)
    view = setup_view(bot, bot.guild)
    pick = next(one for one in view.children if isinstance(one, UploadChannelPick))
    pick._values = []
    interaction = FakeInteraction(bot, member)

    await pick.callback(interaction)

    assert bot.store.get(GUILD, "youtube_channel_id") is None
    assert "go-live channel" in interaction.sent


async def test_forget_clears_exactly_what_an_empty_picker_would(bot, cog, db, member):
    """Events deviation 6: the fallback and the empty submit are one writer, so they agree."""
    _staff(bot)
    await bot.store.set(GUILD, "youtube_channel_id", UPLOAD_CHANNEL)
    empty = FakeInteraction(bot, member)
    await run_setup(empty, {"youtube_channel_id": None})
    cleared = empty.sent

    await bot.store.set(GUILD, "youtube_channel_id", UPLOAD_CHANNEL)
    view = YouTubePanel(10)
    view.add_item(ForgetPick())
    pick = view.children[0]
    pick._values = ["youtube_channel_id"]
    forgetting = FakeInteraction(bot, member)

    await pick.callback(forgetting)

    assert bot.store.get(GUILD, "youtube_channel_id") is None
    assert forgetting.sent == cleared


async def test_the_toggles_flip_the_key_they_name(bot, cog, db, member):
    _staff(bot)
    view = setup_view(bot, bot.guild)
    interaction = FakeInteraction(bot, member)

    await button(view, SHORTS_OFF).callback(interaction)

    assert bot.store.get(GUILD, "youtube_announce_shorts") is True
    assert SHORTS_ON in labels(interaction.view)


async def test_the_numbers_modal_refuses_a_gap_below_the_floor_in_words(bot, cog, db, member):
    _staff(bot)
    interaction = FakeInteraction(bot, member)

    said, _row = await save_setup(bot, bot.guild, member, {"youtube_poll_minutes": 2})

    assert "cannot be less than 5" in said
    assert bot.store.get(GUILD, "youtube_poll_minutes") == 10
    assert await kinds_logged(db) == []
    assert interaction.response.messages == []


async def test_the_numbers_modal_refuses_something_that_is_not_a_number_at_all(
    bot, cog, db, member
):
    _staff(bot)
    modal = NumbersModal(10, 10)
    modal.every._value = "soon"
    modal.stays._value = "10"
    interaction = FakeInteraction(bot, member)

    await modal.on_submit(interaction)

    assert "not a whole number" in interaction.sent
    assert "5 or more" in interaction.sent
    assert await kinds_logged(db) == []


async def test_the_words_modal_writes_the_template_and_the_panel_reads_it_back(
    bot, cog, db, member
):
    _staff(bot)
    interaction = FakeInteraction(bot, member)

    await run_setup(interaction, {"youtube_template": "new video: {title} {url}"})

    assert bot.store.get(GUILD, "youtube_template") == "new video: {title} {url}"
    assert "new video: {title} {url}" in interaction.embed.description


# --- the panel: staff, logs and the database -----------------------------------------------------


async def test_logs_answers_a_new_message_and_leaves_the_panel_where_it_was(
    bot, cog, db, member
):
    _staff(bot)
    _embed, view = await build_panel(bot, bot.guild, member)
    interaction = FakeInteraction(bot, member)

    await button(view, "Logs").callback(interaction)

    assert interaction.edits == []
    assert interaction.response.messages
    assert interaction.ephemeral


async def test_logs_still_refuses_a_staffer_who_was_demoted_since_the_panel_opened(
    bot, cog, db, member
):
    _staff(bot)
    _embed, view = await build_panel(bot, bot.guild, member)
    _staff(bot, False)
    interaction = FakeInteraction(bot, member)

    await button(view, "Logs").callback(interaction)

    assert "staff only" in interaction.sent


@pytest.mark.parametrize("label", ["Link for somebody…", "Setup"])
async def test_a_staffer_demoted_while_the_panel_is_open_moves_nothing(
    bot, cog, db, member, label
):
    _staff(bot)
    _embed, view = await build_panel(bot, bot.guild, member)
    _staff(bot, False)
    interaction = FakeInteraction(bot, member)

    await button(view, label).callback(interaction)

    assert "staff only" in interaction.sent
    assert interaction.edits == []


async def test_the_mode_select_re_asks_whether_the_clicker_is_still_staff(bot, cog, db, member):
    _staff(bot)
    _embed, view = await build_panel(bot, bot.guild, member)
    pick = next(one for one in view.children if isinstance(one, ModePick))
    pick._values = ["on"]
    _staff(bot, False)
    interaction = FakeInteraction(bot, member)

    await pick.callback(interaction)

    assert bot.store.get(GUILD, "youtube_mode") == "off"
    assert "staff only" in interaction.sent


async def test_every_click_re_checks_the_database_after_it_has_deferred(bot, cog, db, member):
    _embed, view = await build_panel(bot, bot.guild, member)
    await db.close()
    interaction = FakeInteraction(bot, member)

    await button(view, "Refresh").callback(interaction)

    assert interaction.sent == DB_UNAVAILABLE
    assert interaction.edits == []


async def test_the_command_refuses_in_words_while_the_database_is_down(bot, cog, db, member):
    await db.close()
    interaction = FakeInteraction(bot, member)

    await cog.youtube.callback(cog, interaction)

    assert interaction.sent == DB_UNAVAILABLE


# --- the panel: the view's own life ---------------------------------------------------------------


async def test_a_re_render_retires_the_view_it_replaced(bot, cog, db, member):
    _embed, first = await build_panel(bot, bot.guild, member)
    interaction = FakeInteraction(bot, member)

    await button(first, "Refresh").callback(interaction)

    assert first.replaced is True
    assert first.is_finished() is True
    assert interaction.view is not first


async def test_a_timeout_disables_every_control_and_says_the_panel_went_quiet(
    bot, cog, db, member
):
    _embed, view = await build_panel(bot, bot.guild, member)
    view.message = FakeMessage(1, embed=discord.Embed(title=PANEL_TITLE, description="x"))

    await view.on_timeout()

    assert all(one.disabled for one in view.children)
    assert view.message.embeds[0].footer.text == PANEL_TIMEOUT_FOOTER
    assert "/youtube" in PANEL_TIMEOUT_FOOTER


async def test_the_panel_minutes_key_is_what_the_view_waits_for(bot, cog, db, member):
    await bot.store.set(GUILD, "youtube_panel_minutes", 4)

    _embed, view = await build_panel(bot, bot.guild, member)

    assert view.timeout == 240


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
