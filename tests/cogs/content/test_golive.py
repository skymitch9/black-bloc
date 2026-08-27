from datetime import UTC, datetime, timedelta

import discord
import pytest

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
from black_bloc.golive import StreamInfo
from black_bloc.settings_store import SettingsStore
from black_bloc.storage.db import Database
from black_bloc.twitch import TwitchStream

GUILD = 7
CHANNEL = 111
LOG_CHANNEL = 222
LIVE_ROLE = 4242
USER = 900


class FakeMessage:
    def __init__(self, message_id, content):
        self.id = message_id
        self.content = content

    async def edit(self, content=None, **kwargs):
        self.content = content


class FakeChannel:
    def __init__(self, channel_id=CHANNEL):
        self.id = channel_id
        self.messages = []

    async def send(self, content=None, **kwargs):
        message = FakeMessage(len(self.messages) + 1, content or "")
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
        return FakeRole(role_id) if role_id == LIVE_ROLE else None

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


class FakeResponse:
    def __init__(self):
        self.messages = []

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral})


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
    def __init__(self, streams=(), users=()):
        self.streams = list(streams)
        self.users = list(users)
        self.stream_calls = []

    async def get_streams(self, logins):
        self.stream_calls.append(list(logins))
        return [s for s in self.streams if s.user_login in {x.lower() for x in logins}]

    async def get_users(self, logins):
        return [u for u in self.users if u.login in {x.lower() for x in logins}]

    async def close(self):
        return None


def streaming_activity(url="https://www.twitch.tv/alice", game="Celeste", details="any%"):
    activity = discord.Streaming(name="Twitch", url=url)
    activity.game = game
    activity.details = details
    return activity


def twitch_stream(login="alice", game="Hades", title="a title"):
    return TwitchStream("1", login, login.title(), game, title, "2026-08-26T12:00:00Z")


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
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    await cog._end_live(bot.guild, member, "presence")

    assert bot.guild.channel.messages[0].content.endswith(" — stream ended")
    assert len(bot.guild.channel.messages) == 1
    assert await open_session_for(db, GUILD, USER) is None
    assert "golive.end" in await action_kinds(db)


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
    assert "does not look like a Twitch name" in interaction.sent

    interaction = FakeInteraction(bot, member, bot.guild)
    await GoLive.unlink.callback(cog, interaction)
    assert await get_link(db, member.id) is None

    interaction = FakeInteraction(bot, member, bot.guild)
    await GoLive.unlink.callback(cog, interaction)
    assert "had no Twitch channel linked" in interaction.sent


async def test_link_refuses_a_login_twitch_does_not_know(cog, bot, member, db):
    cog.helix = FakeHelix(users=[])
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.link.callback(cog, interaction, "ghost")

    assert "Twitch has no channel called **ghost**" in interaction.sent
    assert await get_link(db, member.id) is None


async def test_golive_test_renders_into_the_channel(cog, bot, member, db, monkeypatch):
    monkeypatch.setattr(cog_module, "require_staff", _always_staff)
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.test.callback(cog, interaction)

    assert interaction.sent.startswith("REGULATORS! Mount up! **Alice**")
    assert interaction.response.messages[0]["ephemeral"] is False
    assert await open_sessions(db, GUILD) == []
    assert "golive.test" in await action_kinds(db)


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
    assert "**links** — 1" in interaction.sent


async def _always_staff(interaction):
    return True
