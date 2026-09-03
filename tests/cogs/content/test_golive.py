import asyncio
import json
from datetime import UTC, datetime, timedelta

import discord
import pytest

from black_bloc import actionlog
from black_bloc.actionlog import log_action
from black_bloc.cogs.content import golive as cog_module
from black_bloc.cogs.content.golive import (
    GoLive,
    all_links,
    clean_login,
    clear_optout,
    counts,
    end_session,
    get_link,
    is_opted_out,
    latest_session,
    open_session_for,
    open_sessions,
    remove_link,
    set_announced,
    set_link,
    set_optout,
    start_session,
)
from black_bloc.config import load_settings
from black_bloc.golive import StreamInfo, from_twitch, now_iso
from black_bloc.settings_store import SettingsStore
from black_bloc.storage.db import Database
from black_bloc.twitch import TwitchError, TwitchGame, TwitchStream

GUILD = 7
CHANNEL = 111
LOG_CHANNEL = 222
LIVE_ROLE = 4242
OTHER_LIVE_ROLE = 4343
USER = 900


class FakeMessage:
    def __init__(self, message_id, content, **kwargs):
        self.id = message_id
        self.content = content
        self.kwargs = kwargs
        self.edits = []
        self.embeds = [kwargs["embed"]] if kwargs.get("embed") is not None else []

    async def edit(self, content=None, **kwargs):
        self.content = content
        self.edits.append(kwargs)
        if kwargs.get("embed") is not None:
            self.embeds = [kwargs["embed"]]

    @property
    def embed(self):
        return self.embeds[0] if self.embeds else None


class FakeChannel:
    def __init__(self, channel_id=CHANNEL):
        self.id = channel_id
        self.messages = []

    async def send(self, content=None, **kwargs):
        message = FakeMessage(len(self.messages) + 1, content or "", **kwargs)
        self.messages.append(message)
        return message

    async def fetch_message(self, message_id):
        for message in self.messages:
            if message.id == message_id:
                return message
        raise LookupError(message_id)


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id
        self.name = f"role-{role_id}"


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.channels = {CHANNEL: FakeChannel(CHANNEL), LOG_CHANNEL: FakeChannel(LOG_CHANNEL)}
        self.members = {}

    @property
    def channel(self):
        return self.channels[CHANNEL]

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_role(self, role_id):
        return FakeRole(role_id) if role_id in (LIVE_ROLE, OTHER_LIVE_ROLE) else None

    def get_member(self, user_id):
        return self.members.get(user_id)


class FakeMember:
    def __init__(self, guild, user_id=USER, display_name="Alice", roles=(), activities=()):
        self.id = user_id
        self.guild = guild
        self.display_name = display_name
        self.name = display_name
        self.bot = False
        self.mention = f"<@{user_id}>"
        self.roles = [FakeRole(r) for r in roles]
        self.activities = activities
        self.added = []
        self.removed = []
        guild.members[user_id] = self

    async def add_roles(self, *roles, reason=None):
        self.added += [role.id for role in roles]

    async def remove_roles(self, *roles, reason=None):
        self.removed += [role.id for role in roles]


class FakeGuard:
    def __init__(self, allowed=CHANNEL):
        self.allowed = allowed

    def allows_channel(self, channel_id):
        return channel_id == self.allowed

    def refusal_message(self):
        return "test mode"


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guard = None
        self.guilds = [guild]
        self.guild = guild

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    async def wait_until_ready(self):
        return None


class FakeResponse:
    def __init__(self):
        self.messages = []

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, "kwargs": kwargs})


class FakeInteraction:
    def __init__(self, bot, user, guild=None):
        self.client = bot
        self.user = user
        self.guild = guild
        self.guild_id = guild.id if guild else None
        self.channel_id = CHANNEL
        self.response = FakeResponse()

    @property
    def sent(self):
        return self.response.messages[-1]["content"] if self.response.messages else None


class FakeHelix:
    def __init__(self, streams=(), users=(), games=(), raises=None, game_raises=None):
        self.streams = list(streams)
        self.users = list(users)
        self.games = list(games)
        self.raises = raises
        self.game_raises = game_raises
        self.stream_calls = []
        self.game_calls = []

    async def get_streams(self, logins):
        self.stream_calls.append(list(logins))
        if self.raises is not None:
            raise self.raises
        return [s for s in self.streams if s.user_login in {x.lower() for x in logins}]

    async def get_games(self, ids):
        self.game_calls.append(list(ids))
        if self.game_raises is not None:
            raise self.game_raises
        return [g for g in self.games if g.id in {str(i) for i in ids}]

    async def get_users(self, logins):
        if self.raises is not None:
            raise self.raises
        return [u for u in self.users if u.login in {x.lower() for x in logins}]

    async def close(self):
        return None


def streaming_activity(url="https://www.twitch.tv/alice", game="Celeste", details="any%"):
    activity = discord.Streaming(name="Twitch", url=url)
    activity.game = game
    activity.details = details
    return activity


def youtube_activity(url="https://www.youtube.com/watch?v=xyz", game=None, details=None):
    activity = discord.Streaming(name="YouTube", url=url)
    activity.game = game
    activity.details = details
    return activity


def twitch_stream(login="alice", game="Hades", title="a title", game_id="1", thumbnail=""):
    return TwitchStream(
        "1", login, login.title(), game, title, "2026-08-26T12:00:00Z", game_id, thumbnail
    )


def twitch_game(game_id="1", name="Hades", art="https://boxart/1-285x380.jpg"):
    return TwitchGame(game_id, name, art)


async def action_kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def action_details(db, kind):
    cur = await db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id DESC LIMIT 1", (kind,)
    )
    row = await cur.fetchone()
    return row["details"] if row else None


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "g.sqlite3")
    await database.connect()
    try:
        yield database
    finally:
        await database.close()


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=CHANNEL)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOG_CHANNEL)
    return FakeBot(db, store, settings, FakeGuild())


@pytest.fixture
def cog(bot):
    return GoLive(bot)


@pytest.fixture
def member(bot):
    return FakeMember(bot.guild)


async def test_link_round_trip(db):
    await set_link(db, USER, "alice", "42")
    row = await get_link(db, USER)
    assert row["twitch_login"] == "alice" and row["twitch_user_id"] == "42"
    await set_link(db, USER, "alice2", None)
    assert (await get_link(db, USER))["twitch_login"] == "alice2"
    assert [r["user_id"] for r in await all_links(db)] == [USER]
    assert await remove_link(db, USER) is True
    assert await remove_link(db, USER) is False
    assert await get_link(db, USER) is None


async def test_optout_round_trip(db):
    assert await is_opted_out(db, USER) is False
    await set_optout(db, USER)
    await set_optout(db, USER)
    assert await is_opted_out(db, USER) is True
    assert await clear_optout(db, USER) is True
    assert await clear_optout(db, USER) is False
    assert await is_opted_out(db, USER) is False


async def test_session_lifecycle(db):
    info = StreamInfo(url="u", game="g", title="t")
    session_id = await start_session(db, GUILD, USER, "presence", info, "shadow")
    assert await open_session_for(db, GUILD, USER) is not None
    assert await open_session_for(db, GUILD, USER, "twitch") is None
    assert [r["id"] for r in await open_sessions(db, GUILD)] == [session_id]

    await set_announced(db, session_id, 555)
    await end_session(db, session_id, datetime.now(UTC).isoformat())
    assert await open_session_for(db, GUILD, USER) is None
    last = await latest_session(db, GUILD, USER)
    assert last["announced_message_id"] == 555 and last["ended_at"] is not None
    assert last["mode"] == "shadow" and last["game"] == "g"


async def test_counts_are_per_guild_for_sessions(db):
    await set_link(db, USER, "alice")
    await set_optout(db, USER + 1)
    await start_session(db, GUILD, USER, "presence", StreamInfo(), "shadow")
    await start_session(db, GUILD + 1, USER, "presence", StreamInfo(), "shadow")
    assert await counts(db, GUILD) == {"links": 1, "optouts": 1, "open_sessions": 1}


def test_clean_login_accepts_names_and_urls():
    assert clean_login("Alice") == "alice"
    assert clean_login("  @Alice ") == "alice"
    assert clean_login("https://www.twitch.tv/Alice") == "alice"
    assert clean_login("no spaces here") is None
    assert clean_login("") is None
    assert clean_login("a" * 30) is None


async def test_shadow_mode_logs_but_never_posts(cog, bot, member, db):
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    assert bot.guild.channel.messages == []
    assert "golive.would_announce" in await action_kinds(db)
    session = await open_session_for(db, GUILD, USER)
    assert session["mode"] == "shadow" and session["announced_message_id"] is None
    assert "REGULATORS! Mount up!" in await action_details(db, "golive.would_announce")


async def test_on_mode_posts_and_records_the_message(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")

    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    posted = bot.guild.channel.messages
    assert len(posted) == 1
    assert posted[0].content == (
        "REGULATORS! Mount up! **Alice** is currently streaming **Celeste**! Check it out: u"
    )
    session = await open_session_for(db, GUILD, USER)
    assert session["announced_message_id"] == posted[0].id
    assert "golive.announce" in await action_kinds(db)


async def test_off_mode_does_nothing_at_all(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "off")

    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    assert bot.guild.channel.messages == []
    assert await open_session_for(db, GUILD, USER) is None
    assert await action_kinds(db) == []


async def test_an_opted_out_member_is_never_announced(cog, bot, member, db):
    await set_optout(db, member.id)

    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    assert await open_session_for(db, GUILD, USER) is None
    assert await action_kinds(db) == []


async def test_the_ignore_role_filter_applies(cog, bot, db):
    await bot.store.set(GUILD, "golive_ignore_role_id", 5)
    member = FakeMember(bot.guild, roles=(5,))

    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    assert await open_session_for(db, GUILD, member.id) is None


async def test_the_require_role_filter_applies(cog, bot, db):
    await bot.store.set(GUILD, "golive_require_role_id", 5)
    without = FakeMember(bot.guild, user_id=1, roles=())
    with_role = FakeMember(bot.guild, user_id=2, roles=(5,))

    await cog._go_live(without, StreamInfo(url="u", game="g"), "presence")
    await cog._go_live(with_role, StreamInfo(url="u", game="g"), "presence")

    assert await open_session_for(db, GUILD, 1) is None
    assert await open_session_for(db, GUILD, 2) is not None


async def test_an_open_session_survives_a_restart_and_blocks_a_second_post(bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    await GoLive(bot)._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")
    assert len(bot.guild.channel.messages) == 1

    restarted = GoLive(bot)
    await restarted._go_live(member, StreamInfo(url="u", game="Hades"), "presence")

    assert len(bot.guild.channel.messages) == 1
    assert len(await open_sessions(db, GUILD)) == 1


async def test_the_cooldown_blocks_a_quick_second_stream(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")
    await cog._end_live(bot.guild, member, "presence")

    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")
    assert len(bot.guild.channel.messages) == 1

    old = (datetime.now(UTC) - timedelta(minutes=61)).isoformat()
    await db.conn.execute("UPDATE golive_sessions SET ended_at = ?", (old,))
    await db.conn.commit()
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")
    assert len(bot.guild.channel.messages) == 2


async def test_ending_a_session_edits_the_announcement(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_end_mode", "edit")
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    await cog._end_live(bot.guild, member, "presence")

    assert bot.guild.channel.messages[0].content.endswith(" — stream ended")
    assert len(bot.guild.channel.messages) == 1
    assert await open_session_for(db, GUILD, USER) is None
    assert "golive.end" in await action_kinds(db)
    assert "announcement" not in json.loads(await action_details(db, "golive.end"))


async def test_the_end_edit_is_off_by_default_and_leaves_the_announcement_alone(
    cog, bot, member, db
):
    await bot.store.set(GUILD, "golive_mode", "on")
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")
    posted = bot.guild.channel.messages[0]
    said = posted.content

    await cog._end_live(bot.guild, member, "presence")

    assert bot.store.get(GUILD, "golive_end_mode") == "off"
    assert posted.edits == []
    assert posted.content == said
    assert await open_session_for(db, GUILD, USER) is None
    assert json.loads(await action_details(db, "golive.end"))["announcement"] == "left"


async def test_the_end_edit_being_off_still_takes_the_live_role_back(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_live_role_id", LIVE_ROLE)
    bot.guard = None
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")
    assert member.added == [LIVE_ROLE]

    await cog._end_live(bot.guild, member, "presence")

    assert member.removed == [LIVE_ROLE]
    assert bot.guild.channel.messages[0].edits == []


async def test_a_reconciled_session_leaves_the_announcement_alone_when_the_edit_is_off(
    cog, bot, member, db
):
    await bot.store.set(GUILD, "golive_mode", "on")
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    await cog.reconcile_open_sessions()

    posted = bot.guild.channel.messages[0]
    assert posted.edits == []
    details = json.loads(await action_details(db, "golive.end"))
    assert details["reason"] == "reconciled_on_start" and details["announcement"] == "left"


async def test_ending_without_an_open_session_does_nothing(cog, bot, member, db):
    await cog._end_live(bot.guild, member, "presence")
    assert await action_kinds(db) == []


async def test_live_role_changes_are_only_logged_while_the_guard_is_installed(
    cog, bot, member, db
):
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_live_role_id", LIVE_ROLE)
    bot.guard = FakeGuard()

    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    assert member.added == []
    assert "golive.would_add_role" in await action_kinds(db)


async def test_live_role_is_added_and_removed_once_test_mode_is_off(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_live_role_id", LIVE_ROLE)
    bot.guard = None

    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")
    assert member.added == [LIVE_ROLE]

    await cog._end_live(bot.guild, member, "presence")
    assert member.removed == [LIVE_ROLE]
    assert "golive.add_role" in await action_kinds(db)
    assert "golive.remove_role" in await action_kinds(db)


async def test_shadow_mode_never_touches_roles(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_live_role_id", LIVE_ROLE)
    bot.guard = None

    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    assert member.added == []
    assert "golive.would_add_role" in await action_kinds(db)


async def test_a_guarded_channel_is_never_posted_to(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_channel_id", 999)
    bot.guard = FakeGuard(allowed=CHANNEL)

    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    assert bot.guild.channel.messages == []
    assert "golive.would_announce" in await action_kinds(db)


async def test_the_ping_role_prefixes_the_announcement(cog, bot, member):
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_ping_role_id", 77)

    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    assert bot.guild.channel.messages[0].content.startswith("<@&77> REGULATORS!")


async def test_presence_enrichment_fills_a_missing_game(cog, bot, member, db):
    await set_link(db, member.id, "alice")
    cog.helix = FakeHelix(streams=[twitch_stream()])

    await cog._go_live(member, StreamInfo(url="https://www.twitch.tv/alice"), "presence")

    session = await open_session_for(db, GUILD, USER)
    assert session["game"] == "Hades" and session["title"] == "a title"


async def test_enrichment_is_skipped_when_presence_already_says_everything(cog, bot, member, db):
    await set_link(db, member.id, "alice")
    cog.helix = FakeHelix(streams=[twitch_stream()])

    await cog._go_live(member, StreamInfo(url="u", game="Celeste", title="any%"), "presence")

    assert cog.helix.stream_calls == []
    assert (await open_session_for(db, GUILD, USER))["game"] == "Celeste"


async def test_the_presence_listener_announces_a_new_stream(cog, bot, db):
    before = FakeMember(bot.guild, activities=())
    after = FakeMember(bot.guild, activities=(streaming_activity(),))

    await cog.on_presence_update(before, after)

    assert (await open_session_for(db, GUILD, USER))["source"] == "presence"


async def test_a_youtube_presence_is_announced_with_its_own_url_and_platform(cog, bot, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    before = FakeMember(bot.guild, activities=())
    after = FakeMember(bot.guild, activities=(youtube_activity(),))

    await cog.on_presence_update(before, after)

    session = await open_session_for(db, GUILD, USER)
    assert session["source"] == "presence" and session["platform"] == "YouTube"
    assert session["url"] == "https://www.youtube.com/watch?v=xyz"
    assert bot.guild.channel.messages[0].content.endswith(
        "Check it out: https://www.youtube.com/watch?v=xyz"
    )


async def test_a_youtube_stream_is_never_looked_up_on_twitch(cog, bot, member, db):
    await set_link(db, member.id, "alice")
    cog.helix = FakeHelix(streams=[twitch_stream()])

    info = StreamInfo(url="https://youtu.be/xyz", platform="YouTube")
    await cog._go_live(member, info, "presence")

    assert cog.helix.stream_calls == []
    session = await open_session_for(db, GUILD, USER)
    assert session["platform"] == "YouTube" and session["url"] == "https://youtu.be/xyz"
    assert session["game"] is None and session["title"] is None


async def test_a_twitch_presence_is_still_enriched(cog, bot, member, db):
    await set_link(db, member.id, "alice")
    cog.helix = FakeHelix(streams=[twitch_stream()])

    await cog._go_live(member, StreamInfo(url="https://www.twitch.tv/alice"), "presence")

    assert cog.helix.stream_calls == [["alice"]]
    session = await open_session_for(db, GUILD, USER)
    assert session["platform"] == "Twitch" and session["game"] == "Hades"


async def test_a_youtube_session_is_kept_alive_by_presence_alone(cog, bot, db):
    live = FakeMember(bot.guild, activities=(youtube_activity(),))
    info = StreamInfo(url="https://youtu.be/xyz", platform="YouTube")
    await start_session(db, GUILD, live.id, "presence", info, "on")
    cog.helix = FakeHelix(streams=[])

    await cog.reconcile_open_sessions()

    assert await open_session_for(db, GUILD, live.id) is not None
    assert cog.helix.stream_calls == []


async def test_a_youtube_session_ends_when_the_presence_goes_away(cog, bot, member, db):
    await set_link(db, member.id, "alice")
    await start_session(
        db,
        GUILD,
        member.id,
        "presence",
        StreamInfo(url="https://youtu.be/xyz", platform="YouTube"),
        "on",
    )
    cog.helix = FakeHelix(streams=[twitch_stream()])

    await cog.reconcile_open_sessions()

    assert await open_session_for(db, GUILD, member.id) is None
    assert cog.helix.stream_calls == []


async def test_the_presence_listener_ignores_a_category_change(cog, bot, db):
    live_before = FakeMember(bot.guild, activities=(streaming_activity(game="Celeste"),))
    live_after = FakeMember(bot.guild, activities=(streaming_activity(game="Hades"),))

    await cog.on_presence_update(live_before, live_after)
    await cog.on_presence_update(live_before, live_after)

    assert await open_sessions(db, GUILD) == []
    assert await action_kinds(db) == []


async def test_a_stream_that_stops_ends_after_the_grace(cog, bot, db, monkeypatch):
    monkeypatch.setattr(cog_module, "END_GRACE_SECONDS", 0)
    live = FakeMember(bot.guild, activities=(streaming_activity(),))
    gone = FakeMember(bot.guild, activities=())
    await cog.on_presence_update(FakeMember(bot.guild, activities=()), live)

    await cog.on_presence_update(live, gone)
    task = cog._end_tasks[gone.id]
    await task

    assert await open_session_for(db, GUILD, USER) is None
    assert cog._end_tasks == {}


async def test_a_flap_cancels_the_pending_end(cog, bot, db, monkeypatch):
    monkeypatch.setattr(cog_module, "END_GRACE_SECONDS", 30)
    live = FakeMember(bot.guild, activities=(streaming_activity(),))
    gone = FakeMember(bot.guild, activities=())
    await cog.on_presence_update(FakeMember(bot.guild, activities=()), live)

    await cog.on_presence_update(live, gone)
    task = cog._end_tasks[gone.id]
    await cog.on_presence_update(gone, live)

    assert task.cancelled() or task.cancelling()
    assert cog._end_tasks == {}
    assert await open_session_for(db, GUILD, USER) is not None


async def test_bots_are_ignored(cog, bot, db):
    robot = FakeMember(bot.guild, user_id=5, activities=(streaming_activity(),))
    robot.bot = True

    await cog.on_presence_update(FakeMember(bot.guild, user_id=5), robot)

    assert await open_sessions(db, GUILD) == []


async def test_the_poller_announces_a_linked_login_and_ends_it_when_it_stops(cog, bot, db):
    member = FakeMember(bot.guild)
    await set_link(db, member.id, "alice")
    cog.helix = FakeHelix(streams=[twitch_stream()])

    await cog.poll_once()
    session = await open_session_for(db, GUILD, member.id)
    assert session["source"] == "twitch" and session["game"] == "Hades"

    cog.helix.streams = []
    await cog.poll_once()
    assert await open_session_for(db, GUILD, member.id) is None


async def test_the_poller_does_not_double_announce_a_presence_stream(cog, bot, db):
    member = FakeMember(bot.guild)
    await set_link(db, member.id, "alice")
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")
    cog.helix = FakeHelix(streams=[twitch_stream()])

    await cog.poll_once()

    assert len(await open_sessions(db, GUILD)) == 1


async def test_the_poller_is_inert_without_credentials(cog, bot, db):
    await set_link(db, USER, "alice")
    assert cog.helix is None
    await cog.poll_once()
    assert await open_sessions(db, GUILD) == []


async def test_the_sweep_loop_starts_without_twitch_credentials(cog, bot, db):
    await cog.cog_load()
    try:
        assert cog.helix is None
        assert cog.poller.is_running()
    finally:
        await cog.cog_unload()


async def test_optout_and_optin_commands(cog, bot, member, db):
    interaction = FakeInteraction(bot, member, bot.guild)
    await GoLive.optout.callback(cog, interaction)
    assert await is_opted_out(db, member.id) is True
    assert "will not announce" in interaction.sent

    interaction = FakeInteraction(bot, member, bot.guild)
    await GoLive.optin.callback(cog, interaction)
    assert await is_opted_out(db, member.id) is False
    assert "again" in interaction.sent

    interaction = FakeInteraction(bot, member, bot.guild)
    await GoLive.optin.callback(cog, interaction)
    assert "were not opted out" in interaction.sent


async def test_link_and_unlink_commands(cog, bot, member, db):
    interaction = FakeInteraction(bot, member, bot.guild)
    await GoLive.link.callback(cog, interaction, "https://www.twitch.tv/Alice")
    assert (await get_link(db, member.id))["twitch_login"] == "alice"
    assert "Linked **alice**" in interaction.sent

    interaction = FakeInteraction(bot, member, bot.guild)
    await GoLive.link.callback(cog, interaction, "not a login")
    assert "does not look like a Twitch channel name" in interaction.sent

    interaction = FakeInteraction(bot, member, bot.guild)
    await GoLive.unlink.callback(cog, interaction)
    assert await get_link(db, member.id) is None

    interaction = FakeInteraction(bot, member, bot.guild)
    await GoLive.unlink.callback(cog, interaction)
    assert "had no Twitch channel linked" in interaction.sent


async def test_a_link_makes_a_ping_role_only_when_the_setting_says_auto(
    cog, bot, member, db, monkeypatch
):
    """F14: `pings_fan_role_creation` is the whole gate, and its default is `self`."""
    asked = []

    async def fake(bot_, guild, who, *, by, via="discord"):
        asked.append((guild.id, who.id, by))
        return cog_module.pings.Outcome(True, "Made **Alice pings**.")

    monkeypatch.setattr(cog_module.pings, "maybe_auto_create", fake)
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.link.callback(cog, interaction, "alice")

    assert asked == [(GUILD, member.id, member.id)]
    assert interaction.sent.endswith("Made **Alice pings**.")
    assert interaction.response.messages[-1]["kwargs"]["allowed_mentions"].roles is False


async def test_unlink_and_optout_ask_what_should_happen_to_the_streamers_own_role(
    cog, bot, member, db, monkeypatch
):
    asked = []

    async def fake(bot_, guild, user_id, *, by, via="discord"):
        asked.append(user_id)
        return cog_module.pings.Outcome(True, "The role is gone.")

    monkeypatch.setattr(cog_module.pings, "on_streamer_left", fake)
    await set_link(db, member.id, "alice", None)

    interaction = FakeInteraction(bot, member, bot.guild)
    await GoLive.unlink.callback(cog, interaction)
    assert interaction.sent.endswith("The role is gone.")

    interaction = FakeInteraction(bot, member, bot.guild)
    await GoLive.optout.callback(cog, interaction)
    assert interaction.sent.endswith("The role is gone.")
    assert asked == [member.id, member.id]


async def test_the_default_keep_setting_says_nothing_extra_at_all(cog, bot, member, db):
    await set_link(db, member.id, "alice", None)
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.unlink.callback(cog, interaction)

    assert interaction.sent.endswith("stops that too.")


async def test_link_refuses_a_login_twitch_does_not_know(cog, bot, member, db):
    cog.helix = FakeHelix(users=[])
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.link.callback(cog, interaction, "ghost")

    assert "Twitch has no channel called **ghost**" in interaction.sent
    assert await get_link(db, member.id) is None


async def test_golive_test_previews_ephemerally_without_the_ping_role(
    cog, bot, member, db, monkeypatch
):
    monkeypatch.setattr(cog_module, "require_staff", _always_staff)
    await bot.store.set(GUILD, "golive_ping_role_id", 77)
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.test.callback(cog, interaction)

    assert interaction.sent.startswith("REGULATORS! Mount up! **Alice**")
    assert "<@&77>" not in interaction.sent
    assert interaction.response.messages[0]["ephemeral"] is True
    assert await open_sessions(db, GUILD) == []
    assert "golive.test" in await action_kinds(db)


async def test_golive_test_can_fake_a_youtube_stream(cog, bot, member, db, monkeypatch):
    monkeypatch.setattr(cog_module, "require_staff", _always_staff)
    await bot.store.set(GUILD, "golive_template", "{name} on {platform}: {url}")
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.test.callback(
        cog, interaction, discord.app_commands.Choice(name="YouTube", value="YouTube")
    )

    assert interaction.sent == "Alice on YouTube: https://www.youtube.com/watch?v=blackblocbaf"
    assert interaction.response.messages[0]["ephemeral"] is True
    assert await open_sessions(db, GUILD) == []


async def test_golive_test_still_fakes_twitch_by_default(cog, bot, member, db, monkeypatch):
    monkeypatch.setattr(cog_module, "require_staff", _always_staff)
    await bot.store.set(GUILD, "golive_template", "{platform}: {url}")
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.test.callback(cog, interaction)

    assert interaction.sent == "Twitch: https://www.twitch.tv/blackbloc"


async def test_golive_test_prefers_a_real_stream_when_no_platform_is_chosen(
    cog, bot, monkeypatch
):
    monkeypatch.setattr(cog_module, "require_staff", _always_staff)
    await bot.store.set(GUILD, "golive_template", "{platform}: {url}")
    live = FakeMember(bot.guild, activities=(youtube_activity(),))
    interaction = FakeInteraction(bot, live, bot.guild)

    await GoLive.test.callback(cog, interaction)

    assert interaction.sent == "YouTube: https://www.youtube.com/watch?v=xyz"


async def test_golive_mode_command_stores_and_logs(cog, bot, member, db, monkeypatch):
    monkeypatch.setattr(cog_module, "require_staff", _always_staff)
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.mode.callback(cog, interaction, discord.app_commands.Choice(name="on", value="on"))

    assert bot.store.get(GUILD, "golive_mode") == "on"
    assert "golive.mode" in await action_kinds(db)


async def test_golive_status_reports_the_setup(cog, bot, member, db, monkeypatch):
    monkeypatch.setattr(cog_module, "require_staff", _always_staff)
    await set_link(db, member.id, "alice")
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.status.callback(cog, interaction)

    assert "**mode** — shadow" in interaction.sent
    assert f"<#{CHANNEL}>" in interaction.sent
    assert "no Twitch credentials" in interaction.sent
    assert "ages sessions out" in interaction.sent
    assert "**links** — 1" in interaction.sent


async def test_golive_status_says_the_announcement_is_left_alone_when_the_end_mode_is_off(
    cog, bot, member, db, monkeypatch
):
    monkeypatch.setattr(cog_module, "require_staff", _always_staff)
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.status.callback(cog, interaction)

    assert "**stream end** — off (left as posted)" in interaction.sent
    assert "stream ended" not in interaction.sent


async def test_golive_status_quotes_the_end_wording_when_the_end_mode_is_edit(
    cog, bot, member, db, monkeypatch
):
    monkeypatch.setattr(cog_module, "require_staff", _always_staff)
    await bot.store.set(GUILD, "golive_end_mode", "edit")
    await bot.store.set(GUILD, "golive_end_suffix", " (that's a wrap)")
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.status.callback(cog, interaction)

    assert "**stream end** — edit (\" (that's a wrap)\")" in interaction.sent


async def test_golive_status_names_the_platform_of_everyone_live(cog, bot, member, db, monkeypatch):
    monkeypatch.setattr(cog_module, "require_staff", _always_staff)
    await start_session(
        db, GUILD, member.id, "presence", StreamInfo(url="u", platform="YouTube"), "on"
    )
    stranger = FakeMember(bot.guild, user_id=4242, display_name="Bo")
    await start_session(db, GUILD, stranger.id, "presence", StreamInfo(url="u"), "on")
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.status.callback(cog, interaction)

    assert "• Alice on YouTube" in interaction.sent
    assert "• Bo on an unknown platform" in interaction.sent
    assert interaction.response.messages[0]["kwargs"]["allowed_mentions"].everyone is False


async def test_reconcile_on_start_closes_a_session_nothing_is_streaming(cog, bot, member, db):
    await start_session(db, GUILD, member.id, "presence", StreamInfo(url="u"), "on")

    await cog.reconcile_open_sessions()

    assert await open_session_for(db, GUILD, member.id) is None
    details = json.loads(await action_details(db, "golive.end"))
    assert details["reason"] == "reconciled_on_start"


async def test_reconcile_on_start_keeps_a_member_who_is_still_streaming(cog, bot, db):
    live = FakeMember(bot.guild, activities=(streaming_activity(),))
    await start_session(db, GUILD, live.id, "presence", StreamInfo(url="u"), "on")

    await cog.reconcile_open_sessions()

    assert await open_session_for(db, GUILD, live.id) is not None


async def test_reconcile_on_start_asks_twitch_about_a_twitch_session(cog, bot, member, db):
    await set_link(db, member.id, "alice")
    await start_session(
        db, GUILD, member.id, "twitch", StreamInfo(url="https://www.twitch.tv/alice"), "on"
    )
    cog.helix = FakeHelix(streams=[twitch_stream()])

    await cog.reconcile_open_sessions()

    assert await open_session_for(db, GUILD, member.id) is not None


async def test_an_unreadable_start_time_is_aged_out_rather_than_wedging(cog, bot, member, db):
    session_id = await start_session(db, GUILD, member.id, "presence", StreamInfo(url="u"), "on")
    await db.conn.execute(
        "UPDATE golive_sessions SET started_at = ? WHERE id = ?", ("not-a-date", session_id)
    )
    await db.conn.commit()

    await cog.poll_once()

    assert await open_session_for(db, GUILD, member.id) is None


async def test_the_poll_tick_ages_out_a_session_that_never_ended(cog, bot, member, db):
    session_id = await start_session(db, GUILD, member.id, "presence", StreamInfo(url="u"), "on")
    long_ago = (datetime.now(UTC) - timedelta(hours=13)).isoformat()
    await db.conn.execute(
        "UPDATE golive_sessions SET started_at = ? WHERE id = ?", (long_ago, session_id)
    )
    await db.conn.commit()

    await cog.poll_once()

    assert await open_session_for(db, GUILD, member.id) is None
    assert json.loads(await action_details(db, "golive.end"))["reason"] == "aged_out"


async def test_a_stale_session_no_longer_wedges_the_next_announcement(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    await start_session(db, GUILD, member.id, "presence", StreamInfo(url="u"), "on")

    await cog.reconcile_open_sessions()
    await bot.store.set(GUILD, "golive_cooldown_minutes", 0)
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    assert len(bot.guild.channel.messages) == 1


async def test_the_live_role_is_removed_even_after_the_mode_changes(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_live_role_id", LIVE_ROLE)
    bot.guard = None
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")
    assert member.added == [LIVE_ROLE]
    assert (await open_session_for(db, GUILD, member.id))["live_role_added"] == 1

    await bot.store.set(GUILD, "golive_mode", "shadow")
    await cog._end_live(bot.guild, member, "presence")

    assert member.removed == [LIVE_ROLE]
    assert "golive.remove_role" in await action_kinds(db)


async def test_a_role_that_cannot_be_removed_is_logged_as_stuck(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_live_role_id", LIVE_ROLE)
    bot.guard = None
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    bot.guard = FakeGuard()
    await cog._end_live(bot.guild, member, "presence")

    assert member.removed == []
    details = json.loads(await action_details(db, "golive.role_stuck"))
    assert details["role_id"] == LIVE_ROLE and details["user_id"] == member.id


async def test_the_role_that_went_on_is_the_one_taken_back_after_the_setting_moves(
    cog, bot, member, db
):
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_live_role_id", LIVE_ROLE)
    bot.guard = None
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")
    assert (await open_session_for(db, GUILD, member.id))["live_role_id"] == LIVE_ROLE

    await bot.store.set(GUILD, "golive_live_role_id", OTHER_LIVE_ROLE)
    await cog._end_live(bot.guild, member, "presence")

    assert member.removed == [LIVE_ROLE]
    assert json.loads(await action_details(db, "golive.remove_role"))["role_id"] == LIVE_ROLE


async def test_a_legacy_row_with_only_the_flag_falls_back_to_the_setting(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_live_role_id", LIVE_ROLE)
    bot.guard = None
    session_id = await start_session(db, GUILD, member.id, "presence", StreamInfo(url="u"), "on")
    await db.conn.execute(
        "UPDATE golive_sessions SET live_role_added = 1, live_role_id = NULL WHERE id = ?",
        (session_id,),
    )
    await db.conn.commit()

    await cog._end_live(bot.guild, member, "presence")

    assert member.removed == [LIVE_ROLE]


async def test_a_session_with_no_role_added_removes_nothing(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_live_role_id", LIVE_ROLE)
    bot.guard = None
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    await cog._end_live(bot.guild, member, "presence")

    assert member.removed == []
    assert "golive.role_stuck" not in await action_kinds(db)


async def test_a_failed_post_is_logged_and_leaves_no_cooldown(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_channel_id", 999)
    bot.guard = None

    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    kinds = await action_kinds(db)
    assert "golive.post_failed" in kinds and "golive.would_announce" not in kinds
    assert json.loads(await action_details(db, "golive.post_failed"))["reason"] == (
        "channel_not_visible"
    )
    assert await latest_session(db, GUILD, member.id) is None

    await bot.store.set(GUILD, "golive_channel_id", CHANNEL)
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    assert len(bot.guild.channel.messages) == 1


async def test_the_announcement_only_allows_the_ping_role_to_be_mentioned(cog, bot, member):
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_ping_role_id", 77)

    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    mentions = bot.guild.channel.messages[0].kwargs["allowed_mentions"]
    assert mentions.everyone is False and mentions.users is False
    assert [role.id for role in mentions.roles] == [77]


def fan_role_spy(monkeypatch, role_id):
    """Count every read of the streamer's own role, so a suppressed announcement can be
    shown never to have asked for one (F14: the query sits after the cooldown gate)."""
    asked = []

    async def fake(bot, guild, user_id, *, notice=True):
        asked.append(user_id)
        return role_id

    monkeypatch.setattr(cog_module.pings, "announced_fan_role", fake)
    return asked


async def test_the_announcement_mentions_the_streamers_own_role_after_the_shared_one(
    cog, bot, member, db, monkeypatch
):
    fan_role_spy(monkeypatch, 4242)
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_ping_role_id", 77)

    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    message = bot.guild.channel.messages[0]
    assert message.content.startswith("<@&77> <@&4242> ")
    mentions = message.kwargs["allowed_mentions"]
    assert [role.id for role in mentions.roles] == [77, 4242]
    assert json.loads(await action_details(db, "golive.announce"))["fan_role_id"] == 4242


async def test_a_streamer_with_no_role_of_their_own_announces_exactly_as_before(
    cog, bot, member, db, monkeypatch
):
    fan_role_spy(monkeypatch, None)
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_ping_role_id", 77)

    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    message = bot.guild.channel.messages[0]
    assert message.content.startswith("<@&77> ") and "<@&None>" not in message.content
    assert [role.id for role in message.kwargs["allowed_mentions"].roles] == [77]
    assert json.loads(await action_details(db, "golive.announce"))["fan_role_id"] is None


async def test_a_suppressed_announcement_never_asks_for_a_fan_role(
    cog, bot, member, db, monkeypatch
):
    asked = fan_role_spy(monkeypatch, 4242)
    await bot.store.set(GUILD, "golive_mode", "on")
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")
    assert asked == [member.id]

    await end_session(db, (await latest_session(db, GUILD, member.id))["id"], now_iso())
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    assert asked == [member.id], "the cooldown suppressed the post but the role was still read"
    assert len(bot.guild.channel.messages) == 1


async def test_an_opted_out_streamer_is_never_asked_about_either(
    cog, bot, member, db, monkeypatch
):
    asked = fan_role_spy(monkeypatch, 4242)
    await bot.store.set(GUILD, "golive_mode", "on")
    await set_optout(db, member.id)

    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    assert asked == [] and bot.guild.channel.messages == []


async def test_the_end_edit_carries_the_fan_role_without_adding_a_mention(
    cog, bot, member, monkeypatch
):
    fan_role_spy(monkeypatch, 4242)
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_end_mode", "edit")
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")
    posted = bot.guild.channel.messages[0].content

    await cog._end_live(bot.guild, member, "presence")

    message = bot.guild.channel.messages[0]
    assert message.content == posted + " — stream ended"
    assert [role.id for role in message.edits[0]["allowed_mentions"].roles] == [4242]


async def test_the_end_edit_also_carries_allowed_mentions(cog, bot, member):
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_end_mode", "edit")
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    await cog._end_live(bot.guild, member, "presence")

    assert bot.guild.channel.messages[0].edits[0]["allowed_mentions"].everyone is False


async def test_two_concurrent_go_lives_produce_one_session(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    info = StreamInfo(url="u", game="Celeste")

    await asyncio.gather(
        cog._go_live(member, info, "presence"),
        cog._go_live(member, info, "twitch"),
    )

    assert len(await open_sessions(db, GUILD)) == 1
    assert len(bot.guild.channel.messages) == 1


async def test_the_per_user_lock_serialises_two_go_lives_without_the_index(cog, bot, member, db):
    await db.conn.execute("DROP INDEX golive_open_session")
    await bot.store.set(GUILD, "golive_mode", "on")
    info = StreamInfo(url="u", game="Celeste")

    await asyncio.gather(
        cog._go_live(member, info, "presence"),
        cog._go_live(member, info, "twitch"),
    )

    assert len(await open_sessions(db, GUILD)) == 1
    assert len(bot.guild.channel.messages) == 1


async def test_a_second_open_session_is_refused_by_the_database(db):
    assert await start_session(db, GUILD, USER, "presence", StreamInfo(), "on") is not None
    assert await start_session(db, GUILD, USER, "twitch", StreamInfo(), "on") is None


async def test_a_failed_end_edit_does_not_abort_the_role_or_the_log(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_end_mode", "edit")
    await bot.store.set(GUILD, "golive_live_role_id", LIVE_ROLE)
    bot.guard = None
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")
    bot.guild.channel.messages.clear()

    await cog._end_live(bot.guild, member, "presence")

    assert member.removed == [LIVE_ROLE]
    assert "golive.end" in await action_kinds(db)
    assert await open_session_for(db, GUILD, member.id) is None


async def test_status_reports_the_last_poll_error(cog, bot, member, db, monkeypatch):
    monkeypatch.setattr(cog_module, "require_staff", _always_staff)
    await set_link(db, member.id, "alice")
    cog.helix = FakeHelix(raises=TwitchError("twitch unreachable: boom"))
    await cog.poll_once()

    interaction = FakeInteraction(bot, member, bot.guild)
    await GoLive.status.callback(cog, interaction)

    assert "**last poll error** — twitch unreachable: boom (1 in a row)" in interaction.sent
    assert "**last good poll** — never" in interaction.sent


async def test_a_run_of_failed_polls_is_logged_once_and_ends_nothing(cog, bot, member, db):
    await set_link(db, member.id, "alice")
    await start_session(db, GUILD, member.id, "twitch", StreamInfo(url="u"), "on")
    cog.helix = FakeHelix(raises=TwitchError("twitch unreachable: boom"))

    for _ in range(cog_module.POLL_FAILURES_BEFORE_DEGRADED + 2):
        await cog.poll_once()

    kinds = await action_kinds(db)
    assert kinds.count("golive.poll_degraded") == 1
    details = json.loads(await action_details(db, "golive.poll_degraded"))
    assert details["failures"] == cog_module.POLL_FAILURES_BEFORE_DEGRADED
    assert details["open_sessions"] == 1
    assert await open_session_for(db, GUILD, member.id) is not None


async def test_a_good_poll_clears_the_run_so_the_next_outage_is_logged_again(
    cog, bot, member, db
):
    await set_link(db, member.id, "alice")
    cog.helix = FakeHelix(raises=TwitchError("boom"))
    for _ in range(cog_module.POLL_FAILURES_BEFORE_DEGRADED):
        await cog.poll_once()

    cog.helix = FakeHelix(streams=[])
    await cog.poll_once()
    assert cog.poll_failures == 0

    cog.helix = FakeHelix(raises=TwitchError("boom"))
    for _ in range(cog_module.POLL_FAILURES_BEFORE_DEGRADED):
        await cog.poll_once()

    assert (await action_kinds(db)).count("golive.poll_degraded") == 2


async def test_status_reports_a_good_poll(cog, bot, member, db, monkeypatch):
    monkeypatch.setattr(cog_module, "require_staff", _always_staff)
    await set_link(db, member.id, "alice")
    cog.helix = FakeHelix(streams=[])
    await cog.poll_once()

    interaction = FakeInteraction(bot, member, bot.guild)
    await GoLive.status.callback(cog, interaction)

    assert "**last poll error** — none" in interaction.sent
    assert "**last good poll** — never" not in interaction.sent


async def test_link_refuses_a_login_another_member_already_uses(cog, bot, db):
    theirs = FakeMember(bot.guild, user_id=1)
    mine = FakeMember(bot.guild, user_id=2)
    await set_link(db, theirs.id, "alice")
    interaction = FakeInteraction(bot, mine, bot.guild)

    await GoLive.link.callback(cog, interaction, "Alice")

    assert "already linked to another member" in interaction.sent
    assert await get_link(db, mine.id) is None


async def test_relinking_your_own_login_still_works(cog, bot, member, db):
    await set_link(db, member.id, "alice")
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.link.callback(cog, interaction, "alice")

    assert "Linked **alice**" in interaction.sent


async def test_link_says_so_when_twitch_could_not_be_checked(cog, bot, member, db):
    cog.helix = FakeHelix(raises=TwitchError("twitch unreachable: boom"))
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.link.callback(cog, interaction, "alice")

    assert "could not be reached to check that the channel name exists" in interaction.sent
    assert (await get_link(db, member.id))["twitch_login"] == "alice"


async def test_the_poller_warns_about_two_members_on_the_same_login(cog, bot, db, caplog):
    first = FakeMember(bot.guild, user_id=1)
    second = FakeMember(bot.guild, user_id=2)
    await set_link(db, first.id, "alice")
    await db.conn.execute(
        "INSERT INTO golive_links(user_id, twitch_login, linked_at) VALUES (?, 'alice', 'x')",
        (second.id,),
    )
    await db.conn.commit()
    cog.helix = FakeHelix(streams=[twitch_stream()])

    with caplog.at_level("WARNING"):
        await cog.poll_once()

    assert "linked to both" in caplog.text
    assert len(await open_sessions(db, GUILD)) == 1


async def test_a_command_says_so_when_the_database_is_unreachable(cog, bot, member, db):
    await db.close()
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.optout.callback(cog, interaction)

    assert "cannot reach its own database" in interaction.sent


async def _always_staff(interaction):
    return True


def test_the_link_command_asks_for_a_channel_name_and_never_says_login():
    assert set(GoLive.link._params) == {"channel"}
    assert str(GoLive.link._params["channel"].description) == (
        "Your Twitch channel name (the part after twitch.tv/)"
    )
    said = " ".join(
        [
            str(GoLive.link.description),
            str(GoLive.link._params["channel"].description),
            cog_module.BAD_LOGIN,
            cog_module.NOT_LINKED,
            cog_module.LINK_NOT_CHECKED,
            cog_module.LINK_TAKEN,
        ]
    )
    assert "login" not in said.lower()
    assert "channel name" in said


async def test_the_announcement_carries_the_sentence_and_the_card(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    info = StreamInfo(
        url="https://www.twitch.tv/alice", game="Hades", title="any%", platform="Twitch"
    )

    await cog._go_live(member, info, "twitch")

    posted = bot.guild.channel.messages[0]
    assert posted.content.startswith("REGULATORS! Mount up! **Alice**")
    assert posted.embed.author.name == "Alice is now live on Twitch!"
    assert posted.embed.title == "any%" and posted.embed.url == "https://www.twitch.tv/alice"
    assert [(f.name, f.value) for f in posted.embed.fields] == [("Game", "Hades")]
    assert posted.embed.footer.text == "Black Bloc · via Twitch"
    assert "icon_url" not in posted.embed.to_dict()["author"]


async def test_the_card_shows_the_games_box_art_from_helix(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    cog.helix = FakeHelix(games=[twitch_game()])

    await cog._go_live(member, from_twitch(twitch_stream()), "twitch")

    assert cog.helix.game_calls == [["1"]]
    assert bot.guild.channel.messages[0].embed.image.url == "https://boxart/1-285x380.jpg"
    assert (await open_session_for(db, GUILD, USER))["game"] == "Hades"


async def test_box_art_is_only_looked_up_once_per_announcement(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    cog.helix = FakeHelix(games=[twitch_game()])
    info = from_twitch(twitch_stream())

    filled = await cog._box_art(bot.guild, info)
    again = await cog._box_art(bot.guild, filled)

    assert filled.box_art_url == "https://boxart/1-285x380.jpg"
    assert again is filled and cog.helix.game_calls == [["1"]]


async def test_a_helix_failure_costs_the_art_and_nothing_else(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    cog.helix = FakeHelix(game_raises=TwitchError("twitch unreachable"))

    await cog._go_live(member, from_twitch(twitch_stream()), "twitch")

    posted = bot.guild.channel.messages[0]
    assert "image" not in posted.embed.to_dict()
    assert posted.embed.author.name == "Alice is now live on Twitch!"
    assert "golive.announce" in await action_kinds(db)


async def test_a_youtube_stream_is_never_asked_about_on_the_games_endpoint(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    cog.helix = FakeHelix(games=[twitch_game()])
    info = StreamInfo(
        url="https://youtu.be/xyz",
        game="Celeste",
        platform="YouTube",
        game_id="1",
        thumbnail_url="https://i.ytimg.com/vi/xyz/hqdefault.jpg",
    )

    await cog._go_live(member, info, "presence")

    assert cog.helix.game_calls == [] and cog.helix.stream_calls == []
    embed = bot.guild.channel.messages[0].embed
    assert embed.image.url == "https://i.ytimg.com/vi/xyz/hqdefault.jpg"
    assert embed.author.name == "Alice is now live on YouTube!"
    assert embed.colour.value == 0xFF0000


async def test_turning_the_card_off_posts_exactly_the_old_sentence(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_embed", False)
    cog.helix = FakeHelix(games=[twitch_game()])

    await cog._go_live(member, from_twitch(twitch_stream()), "twitch")

    posted = bot.guild.channel.messages[0]
    assert posted.embeds == [] and "embed" not in posted.kwargs
    assert posted.content == (
        "REGULATORS! Mount up! **Alice** is currently streaming **Hades**! "
        "Check it out: https://www.twitch.tv/alice"
    )
    assert cog.helix.game_calls == []
    assert "embed" not in json.loads(await action_details(db, "golive.announce"))


async def test_shadow_mode_logs_what_the_card_would_have_said(cog, bot, member, db):
    cog.helix = FakeHelix(games=[twitch_game()])

    await cog._go_live(member, from_twitch(twitch_stream()), "twitch")

    assert bot.guild.channel.messages == []
    details = json.loads(await action_details(db, "golive.would_announce"))
    assert details["embed"] == {
        "author": "Alice is now live on Twitch!",
        "title": "a title",
        "game": "Hades",
        "image": "https://boxart/1-285x380.jpg",
    }


async def test_ending_a_stream_rewrites_the_card_and_keeps_the_art(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_end_mode", "edit")
    cog.helix = FakeHelix(games=[twitch_game()])
    await cog._go_live(member, from_twitch(twitch_stream()), "twitch")

    await cog._end_live(bot.guild, member, "twitch")

    posted = bot.guild.channel.messages[0]
    assert posted.content.endswith(" — stream ended")
    assert posted.embed.author.name == "Alice was live on Twitch"
    assert posted.embed.footer.text == "Black Bloc · via Twitch · stream ended"
    assert posted.embed.image.url == "https://boxart/1-285x380.jpg"
    assert posted.embed.url == "https://www.twitch.tv/alice"


async def test_the_end_wording_a_guild_set_reaches_both_halves_of_the_message(
    cog, bot, member, db
):
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_end_mode", "edit")
    await bot.store.set(GUILD, "golive_end_suffix", " (that's a wrap)")
    cog.helix = FakeHelix(games=[twitch_game()])
    await cog._go_live(member, from_twitch(twitch_stream()), "twitch")

    await cog._end_live(bot.guild, member, "twitch")

    posted = bot.guild.channel.messages[0]
    assert posted.content.endswith(" (that's a wrap)")
    assert posted.embed.footer.text == "Black Bloc · via Twitch · (that's a wrap)"


async def test_ending_a_stream_posted_without_a_card_still_marks_the_sentence(
    cog, bot, member, db
):
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_end_mode", "edit")
    await bot.store.set(GUILD, "golive_embed", False)
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    await cog._end_live(bot.guild, member, "presence")

    posted = bot.guild.channel.messages[0]
    assert posted.content.endswith(" — stream ended") and posted.embeds == []
    assert "embed" not in posted.edits[0]


async def test_golive_test_previews_the_card_for_the_chosen_platform(
    cog, bot, member, db, monkeypatch
):
    monkeypatch.setattr(cog_module, "require_staff", _always_staff)
    cog.helix = FakeHelix(games=[twitch_game()])
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.test.callback(
        cog, interaction, discord.app_commands.Choice(name="Twitch", value="Twitch")
    )

    said = interaction.response.messages[-1]
    embed = said["kwargs"]["embed"]
    assert said["ephemeral"] is True
    assert embed.author.name == "Alice is now live on Twitch!"
    assert [(f.name, f.value) for f in embed.fields] == [("Game", "Just Chatting")]
    assert embed.image.url.endswith("ttv-boxart/509658-285x380.jpg")
    assert embed.footer.text == "Black Bloc · via Twitch"
    assert cog.helix.game_calls == []
    assert "embed" in json.loads(await action_details(db, "golive.test"))


async def test_golive_test_previews_the_youtube_card_with_its_own_artwork(
    cog, bot, member, db, monkeypatch
):
    monkeypatch.setattr(cog_module, "require_staff", _always_staff)
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.test.callback(
        cog, interaction, discord.app_commands.Choice(name="YouTube", value="YouTube")
    )

    embed = interaction.response.messages[-1]["kwargs"]["embed"]
    assert embed.author.name == "Alice is now live on YouTube!"
    assert embed.image.url == "https://i.ytimg.com/vi/aqz-KE-bpKQ/hqdefault.jpg"
    assert embed.footer.text == "Black Bloc · via Discord activity"


async def test_golive_test_shows_no_card_when_the_setting_is_off(cog, bot, member, monkeypatch):
    monkeypatch.setattr(cog_module, "require_staff", _always_staff)
    await bot.store.set(GUILD, "golive_embed", False)
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.test.callback(cog, interaction)

    assert "embed" not in interaction.response.messages[-1]["kwargs"]


async def test_golive_logs_shows_this_features_lines_and_nothing_else(
    cog, bot, member, db, monkeypatch
):
    monkeypatch.setattr(actionlog, "require_staff", _always_staff)
    for kind in ("golive.announce", "poll.created", "golive.post_failed"):
        await log_action(bot, bot.guild, kind, actor=member, target=member)
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.golive_logs.callback(cog, interaction)

    said = interaction.response.messages[-1]
    embed = said["kwargs"]["embed"]
    assert said["ephemeral"] is True
    assert said["kwargs"]["allowed_mentions"].everyone is False
    assert embed.title == "Go-live log"
    assert "`golive.post_failed`" in embed.description
    assert "`golive.announce`" in embed.description
    assert "poll.created" not in embed.description
    assert embed.footer.text.endswith("/golive.html")


async def test_golive_logs_important_only_leaves_out_the_routine_lines(
    cog, bot, member, db, monkeypatch
):
    monkeypatch.setattr(actionlog, "require_staff", _always_staff)
    for kind in ("golive.announce", "golive.post_failed"):
        await log_action(bot, bot.guild, kind)
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.golive_logs.callback(cog, interaction, 50, True)

    embed = interaction.response.messages[-1]["kwargs"]["embed"]
    assert embed.title == "Go-live log — important only"
    assert "`golive.post_failed`" in embed.description
    assert "golive.announce" not in embed.description


async def test_golive_logs_says_so_when_the_database_is_away(cog, bot, member, db, monkeypatch):
    monkeypatch.setattr(actionlog, "require_staff", _always_staff)
    await db.close()
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.golive_logs.callback(cog, interaction)

    assert "cannot reach its own database" in interaction.sent
