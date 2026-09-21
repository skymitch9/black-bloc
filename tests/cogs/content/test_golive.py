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
    PostResult,
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
from black_bloc.golive import (
    CHANGE_CHANNEL,
    LINK_CHANNEL,
    SITE_BUTTON,
    StreamInfo,
    from_twitch,
    now_iso,
    panel_buttons,
)
from black_bloc.settings_store import SettingsStore
from black_bloc.twitch import TwitchError, TwitchGame, TwitchStream, TwitchUser

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
        self.by_id = {}
        self.chunked = True

    @property
    def members(self):
        """A real guild hands the boot sweep a list, so the fake does too."""
        return list(self.by_id.values())

    @property
    def channel(self):
        return self.channels[CHANNEL]

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_role(self, role_id):
        return FakeRole(role_id) if role_id in (LIVE_ROLE, OTHER_LIVE_ROLE) else None

    def get_member(self, user_id):
        return self.by_id.get(user_id)


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
        guild.by_id[user_id] = self

    async def add_roles(self, *roles, reason=None):
        self.added += [role.id for role in roles]

    async def remove_roles(self, *roles, reason=None):
        self.removed += [role.id for role in roles]


class FakeGuard:
    def __init__(self, allowed=CHANNEL):
        self.allowed = allowed
        self.test_channel_id = CHANNEL

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
        self.cog = None

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def get_cog(self, name):
        return self.cog

    async def wait_until_ready(self):
        return None


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.modals = []
        self.deferred = False

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, "kwargs": kwargs})

    async def defer(self, ephemeral=False):
        self.deferred = True

    async def send_modal(self, modal):
        self.modals.append(modal)
        self.deferred = True

    def is_done(self):
        return self.deferred or bool(self.messages)


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.response.messages.append(
            {"content": content, "ephemeral": ephemeral, "kwargs": kwargs}
        )


class FakePanelMessage:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.embeds = [kwargs["embed"]] if kwargs.get("embed") is not None else []
        self.edits = []

    async def edit(self, **kwargs):
        self.edits.append(kwargs)


class FakeInteraction:
    def __init__(self, bot, user, guild=None):
        self.client = bot
        self.user = user
        self.guild = guild
        self.guild_id = guild.id if guild else None
        self.channel_id = CHANNEL
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)
        self.edits = []

    @property
    def sent(self):
        said = [
            one["content"] for one in self.response.messages if one.get("content") is not None
        ]
        return said[-1] if said else None

    async def original_response(self):
        return FakePanelMessage()

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return FakePanelMessage(**kwargs)

    @property
    def rendered(self):
        """What the panel last put on the screen — an edit if there was one, else the send."""
        if self.edits:
            return self.edits[-1]
        if not self.response.messages:
            return {}
        return self.response.messages[-1]["kwargs"]

    @property
    def view(self):
        return self.rendered.get("view")

    @property
    def embed(self):
        return self.rendered.get("embed")

    @property
    def words(self):
        found = self.embed
        return "" if found is None else str(found.description or "")

    def labels(self):
        found = self.view
        return [] if found is None else [getattr(one, "label", None) for one in found.children]

    def placeholders(self):
        found = self.view
        return [] if found is None else [
            getattr(one, "placeholder", None) for one in found.children
        ]


def child(view, label):
    return next(one for one in view.children if getattr(one, "label", None) == label)


def picker(view, placeholder):
    return next(one for one in view.children if getattr(one, "placeholder", None) == placeholder)


def as_staff(bot, yes=True):
    """The one staff question, answered without building a role tree in every test."""
    bot.store.is_staff = lambda member: yes


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
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=CHANNEL)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOG_CHANNEL)
    return FakeBot(db, store, settings, FakeGuild())


@pytest.fixture
def cog(bot):
    made = GoLive(bot)
    bot.cog = made
    return made


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
    """Pings remake C1: the ANNOUNCEMENT opt-out and the streamer list are different things,
    so somebody who has stopped announcements still lands on the list and can still be
    followed. `/pings` ▸ **Take me off the streamer list** is the other opt-out."""
    await set_optout(db, member.id)

    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    assert await open_session_for(db, GUILD, USER) is None
    assert await action_kinds(db) == ["pings.streamer_seen"]


async def test_a_first_go_live_lists_the_streamer_and_a_second_adds_no_row(cog, bot, member, db):
    """C1: the listener is the door, and `_go_live_once` is the ONE place both doors meet."""
    from black_bloc import pings

    info = StreamInfo(url="https://twitch.tv/casey", game="Celeste")
    await cog._go_live(member, info, "presence")

    rows = await pings.all_streamers(db, GUILD)
    assert len(rows) == 1 and rows[0]["user_id"] == USER
    assert rows[0]["live_count"] == 1 and rows[0]["listed"] == 1
    assert rows[0]["login"] == "casey" and rows[0]["platform"] == "Twitch"

    await cog._go_live(member, StreamInfo(url="https://twitch.tv/casey", game="Hades"), "twitch")

    rows = await pings.all_streamers(db, GUILD)
    assert len(rows) == 1 and rows[0]["live_count"] == 2
    assert (await action_kinds(db)).count("pings.streamer_seen") == 1


async def test_a_hidden_streamer_stays_hidden_across_a_go_live(cog, bot, member, db):
    from black_bloc import pings

    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")
    await pings.hide_streamer(bot, bot.guild, USER, by=USER)

    await cog._go_live(member, StreamInfo(url="u", game="Hades"), "presence")

    row = await pings.get_streamer(db, GUILD, USER)
    assert row["listed"] == 0 and row["live_count"] == 2


async def test_the_go_live_mode_being_off_lists_nobody(cog, bot, member, db):
    from black_bloc import pings

    await bot.store.set(GUILD, "golive_mode", "off")

    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    assert await pings.all_streamers(db, GUILD) == []


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
    posted = bot.guild.channel.messages[0]
    said = posted.content

    await cog._end_live(bot.guild, member, "presence")

    assert posted.content == said + " — stream ended"
    assert len(bot.guild.channel.messages) == 1
    assert await open_session_for(db, GUILD, USER) is None
    assert "golive.end" in await action_kinds(db)
    assert "announcement" not in json.loads(await action_details(db, "golive.end"))


async def test_the_announcement_is_edited_with_no_mode_left_to_turn_it_off(cog, bot, member, db):
    """The off/edit toggle went 2026-09-20; every ended stream now gets its post edited."""
    await bot.store.set(GUILD, "golive_mode", "on")
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")
    posted = bot.guild.channel.messages[0]
    said = posted.content

    await cog._end_live(bot.guild, member, "presence")

    assert posted.edits != []
    assert posted.content == said + " — stream ended"
    assert await open_session_for(db, GUILD, USER) is None
    assert "announcement" not in json.loads(await action_details(db, "golive.end"))


async def test_ending_a_session_still_takes_the_live_role_back(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_live_role_id", LIVE_ROLE)
    bot.guard = None
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")
    assert member.added == [LIVE_ROLE]

    await cog._end_live(bot.guild, member, "presence")

    assert member.removed == [LIVE_ROLE]
    assert bot.guild.channel.messages[0].edits != []


async def test_a_reconciled_session_edits_its_announcement_too(cog, bot, member, db):
    await bot.store.set(GUILD, "golive_mode", "on")
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    await cog.reconcile_open_sessions()

    posted = bot.guild.channel.messages[0]
    assert posted.edits != []
    details = json.loads(await action_details(db, "golive.end"))
    assert details["reason"] == "reconciled_on_start" and "announcement" not in details


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
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")
    posted = bot.guild.channel.messages[0].content

    await cog._end_live(bot.guild, member, "presence")

    message = bot.guild.channel.messages[0]
    assert posted.startswith("<@&4242> ")
    assert message.content == posted.removeprefix("<@&4242> ") + " — stream ended"
    assert [role.id for role in message.edits[0]["allowed_mentions"].roles] == [4242]


async def test_the_end_edit_keeps_the_mention_when_the_guild_asks_for_it(
    cog, bot, member, monkeypatch
):
    fan_role_spy(monkeypatch, 4242)
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_end_keep_mention", True)
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")
    posted = bot.guild.channel.messages[0].content

    await cog._end_live(bot.guild, member, "presence")

    assert posted.startswith("<@&4242> ")
    assert bot.guild.channel.messages[0].content == posted + " — stream ended"


async def test_the_end_edit_also_carries_allowed_mentions(cog, bot, member):
    await bot.store.set(GUILD, "golive_mode", "on")
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
    await bot.store.set(GUILD, "golive_live_role_id", LIVE_ROLE)
    bot.guard = None
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")
    bot.guild.channel.messages.clear()

    await cog._end_live(bot.guild, member, "presence")

    assert member.removed == [LIVE_ROLE]
    assert "golive.end" in await action_kinds(db)
    assert await open_session_for(db, GUILD, member.id) is None


async def test_a_message_that_cannot_be_fetched_leaves_a_log_line_and_nothing_else(
    cog, bot, member, db, caplog
):
    await bot.store.set(GUILD, "golive_mode", "on")
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")
    bot.guild.channel.messages.clear()

    with caplog.at_level("INFO"):
        await cog._end_live(bot.guild, member, "presence")

    assert "could not mark message" in caplog.text
    assert bot.guild.channel.messages == []
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
async def _always_staff(interaction):
    return True
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
    cog.helix = FakeHelix(games=[twitch_game()])
    await cog._go_live(member, from_twitch(twitch_stream()), "twitch")

    await cog._end_live(bot.guild, member, "twitch")

    posted = bot.guild.channel.messages[0]
    assert posted.content.endswith(" — stream ended")
    assert "**Hades**" in posted.content
    assert posted.embed.author.name == "Alice was live on Twitch"
    assert posted.embed.footer.text == "Black Bloc · via Twitch · stream ended"
    assert posted.embed.image.url == "https://boxart/1-285x380.jpg"
    assert posted.embed.url == "https://www.twitch.tv/alice"


async def test_the_end_wording_a_guild_set_reaches_both_halves_of_the_message(
    cog, bot, member, db
):
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_end_template", "{live} (that's a wrap)")
    cog.helix = FakeHelix(games=[twitch_game()])
    await cog._go_live(member, from_twitch(twitch_stream()), "twitch")

    await cog._end_live(bot.guild, member, "twitch")

    posted = bot.guild.channel.messages[0]
    assert posted.content.endswith(" (that's a wrap)")
    assert posted.embed.footer.text == "Black Bloc · via Twitch · (that's a wrap)"


async def test_the_end_template_and_author_a_guild_set_reach_the_edit_with_the_length(
    cog, bot, member, db
):
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(
        GUILD, "golive_end_template", "{name} streamed {game} for {duration}. {url}"
    )
    await bot.store.set(GUILD, "golive_end_author", "{name} streamed for {duration}")
    cog.helix = FakeHelix(games=[twitch_game()])
    await cog._go_live(member, from_twitch(twitch_stream()), "twitch")
    await db.conn.execute(
        "UPDATE golive_sessions SET started_at = ?",
        ((datetime.now(UTC) - timedelta(minutes=130)).isoformat(),),
    )
    await db.conn.commit()

    await cog._end_live(bot.guild, member, "twitch")

    posted = bot.guild.channel.messages[0]
    assert posted.content == (
        "Alice streamed Hades for 2 h 10 min. https://www.twitch.tv/alice"
    )
    assert posted.embed.author.name == "Alice streamed for 2 h 10 min"


async def test_ending_a_stream_posted_without_a_card_still_marks_the_sentence(
    cog, bot, member, db
):
    await bot.store.set(GUILD, "golive_mode", "on")
    await bot.store.set(GUILD, "golive_embed", False)
    await cog._go_live(member, StreamInfo(url="u", game="Celeste"), "presence")

    await cog._end_live(bot.guild, member, "presence")

    posted = bot.guild.channel.messages[0]
    assert posted.content.endswith(" — stream ended") and posted.embeds == []
    assert "embed" not in posted.edits[0]


async def open_panel(cog, bot, who):
    interaction = FakeInteraction(bot, who, bot.guild)
    await GoLive.golive.callback(cog, interaction)
    return interaction


async def press(bot, who, view, label):
    interaction = FakeInteraction(bot, who, bot.guild)
    await child(view, label).callback(interaction)
    return interaction


async def choose(bot, who, view, placeholder, value):
    interaction = FakeInteraction(bot, who, bot.guild)
    select = picker(view, placeholder)
    select._values = [str(value)]
    await select.callback(interaction)
    return interaction


async def submit_link(bot, who, view, given):
    """Press the link/change button, then submit the modal it opened."""
    opened = await press(bot, who, view, child_label(view))
    modal = opened.response.modals[-1]
    modal.channel._value = given
    interaction = FakeInteraction(bot, who, bot.guild)
    await modal.on_submit(interaction)
    return interaction


def child_label(view):
    for wanted in (LINK_CHANNEL.label, CHANGE_CHANNEL.label):
        if any(getattr(one, "label", None) == wanted for one in view.children):
            return wanted
    raise AssertionError("no link control on this panel")


def moves(interaction):
    """The panel's buttons; a select has no label and the site link is a plain URL."""
    return [one for one in interaction.labels() if one and one != SITE_BUTTON]


async def test_golive_opens_one_ephemeral_panel_a_member_can_use(cog, bot, member, db):
    interaction = await open_panel(cog, bot, member)

    said = interaction.response.messages[-1]
    assert said["ephemeral"] is True
    assert said["kwargs"]["allowed_mentions"].everyone is False
    assert interaction.embed.title == "Go-live"
    assert "none linked yet" in interaction.words
    assert "announced here whenever" in interaction.words
    assert moves(interaction) == [
        "Link my Twitch channel",
        "Stop announcing my streams",
        "Refresh",
    ]
    assert set(interaction.placeholders()) == {None}
    assert SITE_BUTTON in interaction.labels()


@pytest.mark.parametrize("linked", [False, True])
@pytest.mark.parametrize("opted_out", [False, True])
@pytest.mark.parametrize("staff", [False, True])
async def test_the_panel_renders_exactly_the_row_the_table_says(
    cog, bot, member, db, linked, opted_out, staff
):
    """The button table is DATA, and every one of the eight states is proved against it."""
    if linked:
        await set_link(db, member.id, "alice", "42")
    if opted_out:
        await set_optout(db, member.id)
    as_staff(bot, staff)

    interaction = await open_panel(cog, bot, member)

    wanted = [
        move.label
        for move in panel_buttons(linked=linked, opted_out=opted_out, staff=staff)
    ]
    assert moves(interaction) == wanted
    staff_only = {"Logs", "Streamers…"}
    assert bool(staff_only & set(moves(interaction))) is staff
    assert (cog_module.PREVIEW_PICK in interaction.placeholders()) is staff
    assert (cog_module.MODE_PICK in interaction.placeholders()) is staff
    assert ("**mode** — shadow" in interaction.words) is staff
    assert (cog_module.STAFF_ONLY_LINE in interaction.words) == (not staff)


async def test_the_member_panel_says_when_test_mode_is_why_nothing_is_announced(
    cog, bot, member, db
):
    bot.guard = FakeGuard()
    await bot.store.set(GUILD, "golive_channel_id", 999)

    interaction = await open_panel(cog, bot, member)

    assert f"test mode means nothing is posted outside <#{CHANNEL}>" in interaction.words
    assert interaction.words.startswith("Your Twitch channel, and whether")


async def test_the_staff_panel_is_the_member_panel_plus_the_status_lines(
    cog, bot, member, db
):
    as_staff(bot)
    await set_link(db, member.id, "alice", "42")

    interaction = await open_panel(cog, bot, member)

    assert "twitch.tv/alice" in interaction.words
    assert "**mode** — shadow" in interaction.words
    assert f"**channel** — <#{CHANNEL}>" in interaction.words
    assert '**stream end** — edited (appended: "{live} — stream ended")' in interaction.words
    assert "no Twitch credentials" in interaction.words
    assert "ages sessions out" in interaction.words
    assert "**links** — 1" in interaction.words
    assert "**last good poll** — never" in interaction.words
    assert "**last poll error** — none" in interaction.words


async def test_the_status_channel_line_says_test_mode_is_why_nothing_real_posts(
    cog, bot, member, db
):
    as_staff(bot)
    bot.guard = FakeGuard()
    await bot.store.set(GUILD, "golive_channel_id", 999)

    interaction = await open_panel(cog, bot, member)

    assert "**channel** — <#999> — but test mode means nothing is posted" in interaction.words


async def test_the_status_lines_quote_the_end_wording_that_appends(cog, bot, member, db):
    as_staff(bot)
    await bot.store.set(GUILD, "golive_end_template", "{live} (that's a wrap)")

    interaction = await open_panel(cog, bot, member)

    assert "**stream end** — edited (appended: \"{live} (that's a wrap)\")" in interaction.words


async def test_the_status_lines_quote_the_rewrite_when_one_is_set(cog, bot, member, db):
    as_staff(bot)
    await bot.store.set(GUILD, "golive_end_template", "**{name}** was streaming **{game}**")

    interaction = await open_panel(cog, bot, member)

    assert (
        '**stream end** — edited (rewritten: "**{name}** was streaming **{game}**")'
        in interaction.words
    )


async def test_the_status_lines_say_the_sentence_stays_when_the_end_wording_is_blank(
    cog, bot, member, db
):
    as_staff(bot)
    await bot.store.set(GUILD, "golive_end_template", "")

    interaction = await open_panel(cog, bot, member)

    assert "**stream end** — edited (the sentence as posted, nothing added)" in interaction.words


async def test_the_status_lines_name_the_platform_of_everyone_live(cog, bot, member, db):
    as_staff(bot)
    await start_session(
        db, GUILD, member.id, "presence", StreamInfo(url="u", platform="YouTube"), "on"
    )
    stranger = FakeMember(bot.guild, user_id=4242, display_name="Bo")
    await start_session(db, GUILD, stranger.id, "presence", StreamInfo(url="u"), "on")

    interaction = await open_panel(cog, bot, member)

    assert "• Alice on YouTube" in interaction.words
    assert "• Bo on an unknown platform" in interaction.words


async def test_the_status_lines_report_the_last_poll_error(cog, bot, member, db):
    as_staff(bot)
    await set_link(db, member.id, "alice")
    cog.helix = FakeHelix(raises=TwitchError("twitch unreachable: boom"))
    await cog.poll_once()

    interaction = await open_panel(cog, bot, member)

    assert "**last poll error** — twitch unreachable: boom (1 in a row)" in interaction.words
    assert "**last good poll** — never" in interaction.words


async def test_the_status_lines_report_a_good_poll(cog, bot, member, db):
    as_staff(bot)
    await set_link(db, member.id, "alice")
    cog.helix = FakeHelix(streams=[])
    await cog.poll_once()

    interaction = await open_panel(cog, bot, member)

    assert "**last poll error** — none" in interaction.words
    assert "**last good poll** — never" not in interaction.words


async def test_the_status_lines_say_so_when_the_cog_is_not_loaded(cog, bot, member, db):
    as_staff(bot)
    bot.cog = None

    interaction = await open_panel(cog, bot, member)

    assert "the go-live cog is not loaded" in interaction.words


async def test_opting_out_and_back_in_from_the_panel(cog, bot, member, db):
    panel = await open_panel(cog, bot, member)

    out = await press(bot, member, panel.view, "Stop announcing my streams")

    assert await is_opted_out(db, member.id) is True
    assert "will not announce" in out.sent
    assert child(out.view, "Announce my streams again") is not None

    back = await press(bot, member, out.view, "Announce my streams again")

    assert await is_opted_out(db, member.id) is False
    assert "again" in back.sent
    assert await action_kinds(db) == ["golive.optout", "golive.optin"]


async def test_linking_and_unlinking_from_the_panel(cog, bot, member, db):
    panel = await open_panel(cog, bot, member)

    said = await submit_link(bot, member, panel.view, "https://www.twitch.tv/Alice")

    assert (await get_link(db, member.id))["twitch_login"] == "alice"
    assert "Linked **alice**" in said.sent
    assert "twitch.tv/alice" in said.words
    assert child(said.view, "Change my channel") is not None

    gone = await press(bot, member, said.view, "Unlink")

    assert await get_link(db, member.id) is None
    assert "forgotten your Twitch channel" in gone.sent
    assert await action_kinds(db) == ["golive.link", "golive.unlink"]


async def test_change_my_channel_opens_the_modal_already_filled_in(cog, bot, member, db):
    await set_link(db, member.id, "alice", "42")
    panel = await open_panel(cog, bot, member)

    opened = await press(bot, member, panel.view, "Change my channel")

    modal = opened.response.modals[-1]
    assert modal.channel.default == "alice"
    assert modal.title == "Your Twitch channel"
    assert modal.channel.max_length == 25


async def test_the_modal_refuses_a_login_that_is_not_one(cog, bot, member, db):
    panel = await open_panel(cog, bot, member)

    said = await submit_link(bot, member, panel.view, "not a login")

    assert "does not look like a Twitch channel name" in said.sent
    assert await get_link(db, member.id) is None
    assert await action_kinds(db) == []


async def test_the_modal_refuses_a_login_another_member_already_holds(cog, bot, db):
    theirs = FakeMember(bot.guild, user_id=1, display_name="Bo")
    mine = FakeMember(bot.guild, user_id=2, display_name="Cy")
    await set_link(db, theirs.id, "alice")
    panel = await open_panel(cog, bot, mine)

    said = await submit_link(bot, mine, panel.view, "Alice")

    assert "already linked to another member" in said.sent
    assert "Bo" not in said.sent
    assert await get_link(db, mine.id) is None


async def test_relinking_your_own_login_still_works(cog, bot, member, db):
    await set_link(db, member.id, "alice")
    panel = await open_panel(cog, bot, member)

    said = await submit_link(bot, member, panel.view, "alice")

    assert "Linked **alice**" in said.sent


async def test_the_panel_says_so_when_twitch_could_not_be_checked(cog, bot, member, db):
    cog.helix = FakeHelix(raises=TwitchError("twitch unreachable: boom"))
    panel = await open_panel(cog, bot, member)

    said = await submit_link(bot, member, panel.view, "alice")

    assert "could not be reached to check that the channel name exists" in said.sent
    assert (await get_link(db, member.id))["twitch_login"] == "alice"
    assert "not verified with Twitch" in said.words


async def test_the_panel_refuses_a_login_twitch_does_not_know(cog, bot, member, db):
    cog.helix = FakeHelix(users=[])
    panel = await open_panel(cog, bot, member)

    said = await submit_link(bot, member, panel.view, "ghost")

    assert "Twitch has no channel called **ghost**" in said.sent
    assert await get_link(db, member.id) is None


async def test_a_link_makes_a_ping_role_only_when_the_setting_says_auto(
    cog, bot, member, db, monkeypatch
):
    """F14: `pings_fan_role_creation` is the whole gate, and its default is `self`."""
    asked = []

    async def fake(bot_, guild, who, *, by, via="discord"):
        asked.append((guild.id, who.id, by))
        return cog_module.pings.Outcome(True, "Made **Alice pings**.")

    monkeypatch.setattr(cog_module.pings, "maybe_auto_create", fake)
    panel = await open_panel(cog, bot, member)

    said = await submit_link(bot, member, panel.view, "alice")

    assert asked == [(GUILD, member.id, member.id)]
    assert said.sent.endswith("Made **Alice pings**.")
    assert said.response.messages[-1]["kwargs"]["allowed_mentions"].roles is False


async def test_unlink_and_optout_ask_what_should_happen_to_the_streamers_own_role(
    cog, bot, member, db, monkeypatch
):
    asked = []

    async def fake(bot_, guild, user_id, *, by, via="discord"):
        asked.append(user_id)
        return cog_module.pings.Outcome(True, "The role is gone.")

    monkeypatch.setattr(cog_module.pings, "on_streamer_left", fake)
    await set_link(db, member.id, "alice", None)

    panel = await open_panel(cog, bot, member)
    gone = await press(bot, member, panel.view, "Unlink")
    assert gone.sent.endswith("The role is gone.")

    out = await press(bot, member, gone.view, "Stop announcing my streams")
    assert out.sent.endswith("The role is gone.")
    assert asked == [member.id, member.id]


async def test_the_default_keep_setting_says_nothing_extra_at_all(cog, bot, member, db):
    await set_link(db, member.id, "alice", None)
    panel = await open_panel(cog, bot, member)

    gone = await press(bot, member, panel.view, "Unlink")

    assert gone.sent.endswith("stops that too.")


async def test_the_mode_select_writes_the_mode_and_leaves_one_row(cog, bot, member, db):
    as_staff(bot)
    panel = await open_panel(cog, bot, member)

    said = await choose(bot, member, panel.view, cog_module.MODE_PICK, "on")

    assert bot.store.get(GUILD, "golive_mode") == "on"
    assert await action_kinds(db) == ["golive.mode"]
    assert "now **on**" in said.sent
    assert "**mode** — on" in said.words
    chosen = [one.value for one in picker(said.view, cog_module.MODE_PICK).options if one.default]
    assert chosen == ["on"]


async def test_the_preview_answers_a_new_message_and_posts_nothing(cog, bot, member, db):
    as_staff(bot)
    await bot.store.set(GUILD, "golive_ping_role_id", 77)
    panel = await open_panel(cog, bot, member)

    said = await choose(bot, member, panel.view, cog_module.PREVIEW_PICK, "Twitch")

    answered = said.response.messages[-1]
    assert answered["ephemeral"] is True
    assert answered["content"].startswith("REGULATORS! Mount up! **Alice**")
    assert "<@&77>" not in answered["content"]
    assert answered["kwargs"]["allowed_mentions"].everyone is False
    assert said.edits == []
    assert bot.guild.channel.messages == []
    assert await open_sessions(db, GUILD) == []
    assert await action_kinds(db) == ["golive.test"]


async def test_the_preview_never_reaches_the_post_path(cog, bot, member, db, monkeypatch):
    as_staff(bot)
    posted = []

    async def never(self, *args, **kwargs):
        posted.append(args)
        return PostResult()

    monkeypatch.setattr(GoLive, "_post", never)
    panel = await open_panel(cog, bot, member)

    await choose(bot, member, panel.view, cog_module.PREVIEW_PICK, "Twitch")

    assert posted == []


async def test_the_preview_can_fake_a_youtube_stream(cog, bot, member, db):
    as_staff(bot)
    await bot.store.set(GUILD, "golive_template", "{name} on {platform}: {url}")
    panel = await open_panel(cog, bot, member)

    said = await choose(bot, member, panel.view, cog_module.PREVIEW_PICK, "YouTube")

    assert said.sent == "Alice on YouTube: https://www.youtube.com/watch?v=blackblocbaf"


async def test_the_preview_uses_your_own_stream_when_you_pick_as_you_are_now(cog, bot, db):
    as_staff(bot)
    await bot.store.set(GUILD, "golive_template", "{platform}: {url}")
    live = FakeMember(bot.guild, activities=(youtube_activity(),))
    panel = await open_panel(cog, bot, live)

    said = await choose(
        bot, live, panel.view, cog_module.PREVIEW_PICK, cog_module.PREVIEW_SELF
    )

    assert said.sent == "YouTube: https://www.youtube.com/watch?v=xyz"


async def test_the_preview_falls_back_to_twitch_when_you_are_not_streaming(cog, bot, member, db):
    as_staff(bot)
    await bot.store.set(GUILD, "golive_template", "{platform}: {url}")
    panel = await open_panel(cog, bot, member)

    said = await choose(
        bot, member, panel.view, cog_module.PREVIEW_PICK, cog_module.PREVIEW_SELF
    )

    assert said.sent == "Twitch: https://www.twitch.tv/blackbloc"


async def test_the_preview_carries_the_card_for_the_chosen_platform(cog, bot, member, db):
    as_staff(bot)
    cog.helix = FakeHelix(games=[twitch_game()])
    panel = await open_panel(cog, bot, member)

    said = await choose(bot, member, panel.view, cog_module.PREVIEW_PICK, "Twitch")

    answered = said.response.messages[-1]
    embed = answered["kwargs"]["embed"]
    assert answered["ephemeral"] is True
    assert embed.author.name == "Alice is now live on Twitch!"
    assert [(f.name, f.value) for f in embed.fields] == [("Game", "Just Chatting")]
    assert embed.image.url.endswith("ttv-boxart/509658-285x380.jpg")
    assert embed.footer.text == "Black Bloc · via Twitch"
    assert cog.helix.game_calls == []
    assert "embed" in json.loads(await action_details(db, "golive.test"))


async def test_the_preview_carries_the_youtube_card_with_its_own_artwork(cog, bot, member, db):
    as_staff(bot)
    panel = await open_panel(cog, bot, member)

    said = await choose(bot, member, panel.view, cog_module.PREVIEW_PICK, "YouTube")

    embed = said.response.messages[-1]["kwargs"]["embed"]
    assert embed.author.name == "Alice is now live on YouTube!"
    assert embed.image.url == "https://i.ytimg.com/vi/aqz-KE-bpKQ/hqdefault.jpg"
    assert embed.footer.text == "Black Bloc · via Discord activity"


async def test_the_preview_shows_no_card_when_the_setting_is_off(cog, bot, member, db):
    as_staff(bot)
    await bot.store.set(GUILD, "golive_embed", False)
    panel = await open_panel(cog, bot, member)

    said = await choose(bot, member, panel.view, cog_module.PREVIEW_PICK, "Twitch")

    assert "embed" not in said.response.messages[-1]["kwargs"]


async def test_logs_answers_a_new_message_and_the_panel_stays(cog, bot, member, db, monkeypatch):
    monkeypatch.setattr(actionlog, "require_staff", _always_staff)
    as_staff(bot)
    for kind in ("golive.announce", "poll.created", "golive.post_failed"):
        await log_action(bot, bot.guild, kind, actor=member, target=member)
    panel = await open_panel(cog, bot, member)

    said = await press(bot, member, panel.view, "Logs")

    answered = said.response.messages[-1]
    embed = answered["kwargs"]["embed"]
    assert answered["ephemeral"] is True
    assert answered["kwargs"]["allowed_mentions"].everyone is False
    assert said.edits == []
    assert embed.title == "Go-live log"
    assert "`golive.post_failed`" in embed.description
    assert "`golive.announce`" in embed.description
    assert "poll.created" not in embed.description
    assert embed.footer.text.endswith("/golive.html")


async def test_logs_still_refuses_a_staffer_who_was_demoted(cog, bot, member, db):
    as_staff(bot)
    panel = await open_panel(cog, bot, member)
    as_staff(bot, False)

    said = await press(bot, member, panel.view, "Logs")

    assert "for staff only" in said.sent


async def test_a_staffer_demoted_mid_panel_moves_nothing(cog, bot, member, db):
    as_staff(bot)
    panel = await open_panel(cog, bot, member)
    as_staff(bot, False)

    mode = await choose(bot, member, panel.view, cog_module.MODE_PICK, "on")
    streamers = await press(bot, member, panel.view, "Streamers…")
    shown = await choose(bot, member, panel.view, cog_module.PREVIEW_PICK, "Twitch")

    assert bot.store.get(GUILD, "golive_mode") == "shadow"
    assert await action_kinds(db) == []
    for said in (mode, streamers, shown):
        assert "for staff only" in said.sent
        assert said.edits == []


async def test_every_move_says_so_when_the_database_is_away(cog, bot, member, db):
    panel = await open_panel(cog, bot, member)
    await db.close()

    pressed = await press(bot, member, panel.view, "Stop announcing my streams")
    modal = await press(bot, member, panel.view, "Link my Twitch channel")

    assert "cannot reach its own database" in pressed.sent
    assert pressed.response.deferred is True
    assert "cannot reach its own database" in modal.sent
    assert modal.response.modals == []


async def test_the_command_says_so_when_the_database_is_unreachable(cog, bot, member, db):
    await db.close()
    interaction = FakeInteraction(bot, member, bot.guild)

    await GoLive.golive.callback(cog, interaction)

    assert "cannot reach its own database" in interaction.sent


async def test_a_re_render_retires_the_view_it_replaced(cog, bot, member, db):
    panel = await open_panel(cog, bot, member)
    first = panel.view

    second = await press(bot, member, first, "Refresh")

    assert first.replaced is True
    assert first.is_finished() is True
    assert second.view.replaced is False


async def test_the_timeout_disables_every_control_and_writes_the_footer(cog, bot, member, db):
    panel = await open_panel(cog, bot, member)
    view = panel.view
    view.message = FakePanelMessage(embed=panel.embed)

    await view.on_timeout()

    assert all(one.disabled for one in view.children)
    assert view.message.edits[-1]["embeds"][0].footer.text == (
        "This panel has gone quiet — run /golive again"
    )


async def test_the_panel_carries_the_site_link_only_with_an_origin(cog, bot, member, db):
    said = await open_panel(cog, bot, member)
    assert child(said.view, SITE_BUTTON).url.endswith("/golive.html")

    bot.settings = load_settings(
        _env_file=None, test_mode=True, test_channel_id=CHANNEL, site_origin=""
    )
    without = await open_panel(cog, bot, member)

    assert SITE_BUTTON not in without.labels()


async def test_the_streamers_panel_lists_everyone_who_linked_a_channel(cog, bot, member, db):
    as_staff(bot)
    other = FakeMember(bot.guild, user_id=4242, display_name="Bo")
    await set_link(db, member.id, "alice", "42")
    await set_link(db, other.id, "bo", None)
    panel = await open_panel(cog, bot, member)

    shown = await press(bot, member, panel.view, "Streamers…")

    assert shown.embed.title == "Streamers"
    options = picker(shown.view, cog_module.PICK_A_STREAMER).options
    assert [one.label for one in options] == [
        "Alice — twitch.tv/alice",
        "Bo — twitch.tv/bo",
    ]
    assert moves(shown) == ["Back"]


async def test_the_streamers_select_says_how_many_it_could_not_show(cog, bot, member, db):
    as_staff(bot)
    for number in range(30):
        await set_link(db, 1000 + number, f"s{number:02d}", None)
    panel = await open_panel(cog, bot, member)

    shown = await press(bot, member, panel.view, "Streamers…")

    assert picker(shown.view, "25 of 30 — the rest are on the site") is not None


async def test_staff_unlink_somebody_else_through_the_same_function(cog, bot, member, db):
    as_staff(bot)
    other = FakeMember(bot.guild, user_id=4242, display_name="Bo")
    await set_link(db, other.id, "bo", None)
    panel = await open_panel(cog, bot, member)
    shown = await press(bot, member, panel.view, "Streamers…")

    card = await choose(bot, member, shown.view, cog_module.PICK_A_STREAMER, other.id)
    assert "**Bo** — twitch.tv/bo — not verified with Twitch" in card.words

    asked = await press(bot, member, card.view, "Unlink them")
    assert "Unlink **Bo** from twitch.tv/bo?" in asked.words

    done = await press(bot, member, asked.view, "Yes, unlink them")

    assert await get_link(db, other.id) is None
    assert "**Bo** is no longer linked" in done.sent
    assert await action_kinds(db) == ["golive.unlink"]


async def test_staff_opt_somebody_else_out_and_back_in(cog, bot, member, db):
    as_staff(bot)
    other = FakeMember(bot.guild, user_id=4242, display_name="Bo")
    await set_link(db, other.id, "bo", "9")
    panel = await open_panel(cog, bot, member)
    shown = await press(bot, member, panel.view, "Streamers…")
    card = await choose(bot, member, shown.view, cog_module.PICK_A_STREAMER, other.id)

    out = await press(bot, member, card.view, "Opt them out")
    assert await is_opted_out(db, other.id) is True
    assert "no stream of **Bo**'s is announced" in out.sent
    assert "Opted out" in out.words

    back = await press(bot, member, out.view, "Opt them back in")
    assert await is_opted_out(db, other.id) is False
    assert "**Bo**'s streams can be announced again" in back.sent
    assert await action_kinds(db) == ["golive.optout", "golive.optin"]


async def test_back_returns_to_the_root_panel(cog, bot, member, db):
    as_staff(bot)
    await set_link(db, member.id, "alice", "42")
    panel = await open_panel(cog, bot, member)
    shown = await press(bot, member, panel.view, "Streamers…")

    said = await press(bot, member, shown.view, "Back")

    assert said.embed.title == "Go-live"
    assert "**mode** — shadow" in said.words


async def test_a_link_with_twitch_turned_off_never_claims_it_was_checked(
    cog, bot, member, db
):
    """Checklist 10: with no Twitch client nothing was verified, and the row says so —
    but the sentence does not blame Twitch for being unreachable, because nobody asked it."""
    assert cog.helix is None
    panel = await open_panel(cog, bot, member)

    said = await submit_link(bot, member, panel.view, "alice")

    assert "could not be reached" not in said.sent
    assert "Linked **alice**" in said.sent
    assert json.loads(await action_details(db, "golive.link"))["checked"] is False
    assert "not verified with Twitch" in said.words


async def test_a_checked_link_says_so_in_the_row_and_on_the_card(cog, bot, member, db):
    cog.helix = FakeHelix(users=[TwitchUser("42", "alice", "Alice")])
    panel = await open_panel(cog, bot, member)

    said = await submit_link(bot, member, panel.view, "alice")

    assert (await get_link(db, member.id))["twitch_user_id"] == "42"
    assert json.loads(await action_details(db, "golive.link"))["checked"] is True
    assert "not verified" not in said.words


async def test_every_panel_move_leaves_exactly_one_log_row(cog, bot, member, db):
    """Checklist 34, counted rather than merely named."""
    panel = await open_panel(cog, bot, member)

    linked = await submit_link(bot, member, panel.view, "alice")
    out = await press(bot, member, linked.view, "Stop announcing my streams")
    back = await press(bot, member, out.view, "Announce my streams again")
    await press(bot, member, back.view, "Unlink")

    assert await action_kinds(db) == [
        "golive.link",
        "golive.optout",
        "golive.optin",
        "golive.unlink",
    ]


async def test_every_panel_move_records_which_door_it_came_through(cog, bot, member, db):
    panel = await open_panel(cog, bot, member)

    await submit_link(bot, member, panel.view, "alice")

    assert json.loads(await action_details(db, "golive.link"))["via"] == "discord"


# --- co-streaming: one announcement, both platforms, edited in place ---------------------------


TWITCH_INFO = StreamInfo(
    url="https://www.twitch.tv/alice", game="Celeste", title="Any%", platform="Twitch"
)
YOUTUBE_INFO = StreamInfo(
    url="https://www.youtube.com/watch?v=xyz", title="Live now", platform="YouTube"
)
COSTREAM_SENTENCE = (
    "**Alice** is streaming on **Twitch** and **YouTube**! "
    "Watch on Twitch: https://www.twitch.tv/alice · "
    "also live on YouTube: <https://www.youtube.com/watch?v=xyz>"
)


class FakeYouTube:
    """The YouTube cog as the reconcile sees it: one question, three answers."""

    def __init__(self, live=True):
        self.live = live
        self.asked = []

    async def is_live_now(self, user_id):
        self.asked.append(user_id)
        return self.live


async def announcing(bot):
    await bot.store.set(GUILD, "golive_mode", "on")


async def only_session(db):
    rows = await open_sessions(db, GUILD)
    assert len(rows) == 1
    return rows[0]


async def test_a_youtube_stream_joins_the_twitch_announcement_instead_of_being_refused(
    cog, bot, member, db
):
    await announcing(bot)
    await cog._go_live(member, TWITCH_INFO, "twitch")
    posted = bot.guild.channel.messages[0]

    await cog.add_platform(member, YOUTUBE_INFO, "youtube")

    row = await only_session(db)
    assert row["source"] == "twitch" and row["platform"] == "Twitch"
    assert row["also_source"] == "youtube" and row["also_platform"] == "YouTube"
    assert row["also_url"] == YOUTUBE_INFO.url and row["also_started_at"]
    assert len(bot.guild.channel.messages) == 1
    assert len(posted.edits) == 1
    assert posted.content == COSTREAM_SENTENCE
    kinds = await action_kinds(db)
    assert kinds.count("golive.announce") == 1
    assert "golive.costream_added" in kinds
    details = json.loads(await action_details(db, "golive.costream_added"))
    assert details["source"] == "youtube" and details["first"] == "Twitch"
    assert details["edited"] is True


async def test_the_second_platform_is_an_edit_and_never_a_second_ping(
    cog, bot, member, db, monkeypatch
):
    asked = fan_role_spy(monkeypatch, 4242)
    await announcing(bot)
    await bot.store.set(GUILD, "golive_ping_role_id", 5151)
    await cog._go_live(member, TWITCH_INFO, "twitch")
    posted = bot.guild.channel.messages[0]
    assert posted.content.startswith("<@&5151> <@&4242> ")

    await cog.add_platform(member, YOUTUBE_INFO, "youtube")

    assert len(bot.guild.channel.messages) == 1
    assert posted.content.startswith("<@&5151> <@&4242> ")
    assert posted.content.count("<@&5151>") == 1
    assert asked == [USER, USER]


async def test_a_twitch_stream_arriving_second_still_reads_twitch_first(cog, bot, member, db):
    await announcing(bot)
    await cog._go_live(member, YOUTUBE_INFO, "youtube")
    posted = bot.guild.channel.messages[0]

    await cog._go_live(member, TWITCH_INFO, "twitch")

    row = await only_session(db)
    assert row["source"] == "youtube" and row["also_source"] == "twitch"
    assert len(bot.guild.channel.messages) == 1
    assert posted.content == COSTREAM_SENTENCE
    assert posted.embed.title == "Any%"
    assert posted.embed.author.name == "Alice is live on Twitch and YouTube"
    assert posted.embed.footer.text == "Black Bloc · via Twitch + YouTube"


async def test_the_card_keeps_the_twitch_art_when_youtube_joins_it(cog, bot, member, db):
    await announcing(bot)
    cog.helix = FakeHelix(games=[twitch_game("1", "Celeste", "https://boxart/celeste.jpg")])
    await cog._go_live(
        member,
        StreamInfo(
            url="https://www.twitch.tv/alice",
            game="Celeste",
            title="Any%",
            platform="Twitch",
            game_id="1",
        ),
        "twitch",
    )
    posted = bot.guild.channel.messages[0]
    art = posted.embed.image.url

    await cog.add_platform(member, YOUTUBE_INFO, "youtube")

    assert art == "https://boxart/celeste.jpg"
    assert posted.embed.image.url == art
    assert posted.embed.footer.text == "Black Bloc · via Twitch + YouTube"


async def test_the_also_side_ending_puts_the_message_back_on_one_platform(cog, bot, member, db):
    await announcing(bot)
    await cog._go_live(member, TWITCH_INFO, "twitch")
    await cog.add_platform(member, YOUTUBE_INFO, "youtube")
    posted = bot.guild.channel.messages[0]

    await cog._end_live(bot.guild, member, "youtube")

    row = await only_session(db)
    assert row["ended_at"] is None
    assert row["source"] == "twitch" and row["also_source"] is None
    assert posted.content == (
        "REGULATORS! Mount up! **Alice** is currently streaming **Celeste**! "
        "Check it out: https://www.twitch.tv/alice"
    )
    assert posted.embed.author.name == "Alice is now live on Twitch!"
    assert posted.embed.footer.text == "Black Bloc · via Twitch"
    details = json.loads(await action_details(db, "golive.costream_dropped"))
    assert details["promoted"] is False and details["side"] == "also"
    assert details["source"] == "youtube" and details["platform"] == "Twitch"
    assert "golive.end" not in await action_kinds(db)


async def test_the_primary_ending_first_promotes_the_other_and_leaves_the_session_open(
    cog, bot, member, db
):
    await announcing(bot)
    await cog._go_live(member, TWITCH_INFO, "twitch")
    await cog.add_platform(member, YOUTUBE_INFO, "youtube")
    posted = bot.guild.channel.messages[0]

    await cog._end_live(bot.guild, member, "twitch")

    row = await only_session(db)
    assert row["ended_at"] is None
    assert row["source"] == "youtube" and row["platform"] == "YouTube"
    assert row["url"] == YOUTUBE_INFO.url and row["also_source"] is None
    assert posted.content.endswith("Check it out: https://www.youtube.com/watch?v=xyz")
    assert posted.embed.author.name == "Alice is now live on YouTube!"
    assert posted.embed.footer.text == "Black Bloc · via YouTube"
    details = json.loads(await action_details(db, "golive.costream_dropped"))
    assert details["promoted"] is True and details["side"] == "primary"
    assert "golive.end" not in await action_kinds(db)


async def test_the_last_platform_ending_is_todays_ended_path(cog, bot, member, db):
    await announcing(bot)
    await cog._go_live(member, TWITCH_INFO, "twitch")
    await cog.add_platform(member, YOUTUBE_INFO, "youtube")

    await cog._end_live(bot.guild, member, "twitch")
    await cog._end_live(bot.guild, member, "youtube")

    assert await open_session_for(db, GUILD, USER) is None
    ended = bot.guild.channel.messages[0].content
    assert ended.endswith(" — stream ended") and "youtube.com/watch?v=xyz" in ended
    assert "golive.end" in await action_kinds(db)


async def test_with_the_mode_off_the_second_platform_is_held_back_as_before(
    cog, bot, member, db
):
    await announcing(bot)
    await bot.store.set(GUILD, "golive_costream_mode", "off")
    await cog._go_live(member, TWITCH_INFO, "twitch")
    posted = bot.guild.channel.messages[0]

    await cog.add_platform(member, YOUTUBE_INFO, "youtube")
    await cog._go_live(member, YOUTUBE_INFO, "youtube")

    row = await only_session(db)
    assert row["also_source"] is None
    assert posted.edits == []
    assert len(bot.guild.channel.messages) == 1
    assert "golive.costream_added" not in await action_kinds(db)


async def test_the_same_platform_twice_is_still_a_duplicate_and_changes_nothing(
    cog, bot, member, db
):
    await announcing(bot)
    await cog._go_live(member, TWITCH_INFO, "twitch")
    posted = bot.guild.channel.messages[0]

    await cog._go_live(member, TWITCH_INFO, "presence")

    assert (await only_session(db))["also_source"] is None
    assert posted.edits == [] and len(bot.guild.channel.messages) == 1


async def test_a_session_with_no_announcement_records_the_platform_and_edits_nothing(
    cog, bot, member, db
):
    await bot.store.set(GUILD, "golive_mode", "shadow")
    await cog._go_live(member, TWITCH_INFO, "twitch")

    await cog.add_platform(member, YOUTUBE_INFO, "youtube")

    row = await only_session(db)
    assert row["announced_message_id"] is None
    assert row["also_source"] == "youtube"
    assert bot.guild.channel.messages == []
    assert json.loads(await action_details(db, "golive.costream_added"))["edited"] is False


async def test_the_reconcile_reads_one_dead_side_as_a_drop_and_not_as_the_end(
    cog, bot, member, db
):
    await announcing(bot)
    cog.helix = FakeHelix(streams=[])
    await cog._go_live(member, TWITCH_INFO, "twitch")
    await cog.add_platform(member, YOUTUBE_INFO, "youtube")
    await set_link(db, USER, "alice")
    bot.cog = FakeYouTube(live=True)

    await cog.reconcile_open_sessions()

    row = await only_session(db)
    assert row["ended_at"] is None
    assert row["source"] == "youtube" and row["also_source"] is None
    assert "golive.end" not in await action_kinds(db)
    assert "golive.costream_dropped" in await action_kinds(db)


async def test_the_reconcile_closes_a_co_stream_only_when_neither_side_is_live(
    cog, bot, member, db
):
    await announcing(bot)
    cog.helix = FakeHelix(streams=[])
    await cog._go_live(member, TWITCH_INFO, "twitch")
    await cog.add_platform(member, YOUTUBE_INFO, "youtube")
    await set_link(db, USER, "alice")
    bot.cog = FakeYouTube(live=False)

    await cog.reconcile_open_sessions()

    assert await open_session_for(db, GUILD, USER) is None
    assert "golive.end" in await action_kinds(db)


async def test_the_reconcile_leaves_a_co_stream_alone_while_both_sides_are_live(
    cog, bot, member, db
):
    await announcing(bot)
    cog.helix = FakeHelix(streams=[twitch_stream("alice")])
    await cog._go_live(member, TWITCH_INFO, "twitch")
    await cog.add_platform(member, YOUTUBE_INFO, "youtube")
    await set_link(db, USER, "alice")
    bot.cog = FakeYouTube(live=True)

    await cog.reconcile_open_sessions()

    row = await only_session(db)
    assert row["ended_at"] is None and row["also_source"] == "youtube"


async def test_the_twitch_sweep_adds_itself_to_a_youtube_session_and_ends_only_its_own_side(
    cog, bot, member, db
):
    await announcing(bot)
    await set_link(db, USER, "alice")
    cog.helix = FakeHelix(streams=[twitch_stream("alice", game="Hades")])
    await cog._go_live(member, YOUTUBE_INFO, "youtube")

    await cog.poll_once()

    row = await only_session(db)
    assert row["source"] == "youtube" and row["also_source"] == "twitch"

    cog.helix = FakeHelix(streams=[])
    await cog.poll_once()

    row = await only_session(db)
    assert row["ended_at"] is None and row["also_source"] is None
    assert row["source"] == "youtube"


# --- the boot sweep: nobody is missed because the bot was restarting ---------------------------
# Design: docs/info/golive-boot-sweep-design.md. The five §A tests are the PROOF of what a reboot
# already gets right — they boot the cog rather than calling the reconcile by hand.


async def boot_row(db):
    return json.loads(await action_details(db, "golive.boot_swept"))


async def _retired_row(db, guild_id, key, value):
    await db.conn.execute(
        "INSERT OR REPLACE INTO settings(guild_id, key, value, updated_by, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (guild_id, key, json.dumps(value), None, "2026-09-01T00:00:00+00:00"),
    )
    await db.conn.commit()


async def test_the_boot_pass_carries_the_end_wording_over_and_says_what_it_did(cog, bot, db):
    await _retired_row(db, GUILD, "golive_end_suffix", " (that's a wrap)")
    await _retired_row(db, GUILD, "golive_end_mode", "off")

    await cog.boot_pass()

    assert bot.store.get(GUILD, "golive_end_template") == "{live} (that's a wrap)"
    details = json.loads(await action_details(db, "golive.end_wording_migrated"))
    assert details["carried_suffix"] is True and details["dropped_mode"] == "off"


async def test_a_second_boot_leaves_no_second_migration_row(cog, bot, db):
    await _retired_row(db, GUILD, "golive_end_suffix", " (over)")

    await cog.boot_pass()
    await cog.boot_pass()

    kinds = await action_kinds(db)
    assert kinds.count("golive.end_wording_migrated") == 1


async def test_a_guild_with_nothing_to_carry_leaves_no_migration_row(cog, bot, db):
    await cog.boot_pass()

    assert "golive.end_wording_migrated" not in await action_kinds(db)


async def test_a_twitch_login_live_across_a_reboot_is_announced_by_the_first_poll(cog, bot, db):
    await announcing(bot)
    live = FakeMember(bot.guild)
    await set_link(db, live.id, "alice")
    cog.helix = FakeHelix(streams=[twitch_stream()])

    await cog.boot_pass()
    await cog.poll_once()

    row = await only_session(db)
    assert row["source"] == "twitch" and row["game"] == "Hades"
    assert len(bot.guild.channel.messages) == 1

    await cog._end_live(bot.guild, live, "twitch")
    await cog.boot_pass()
    await cog.poll_once()

    assert len(bot.guild.channel.messages) == 1
    assert await open_session_for(db, GUILD, live.id) is None


async def test_a_boot_keeps_an_open_session_whose_streamer_is_still_live(cog, bot, db):
    live = FakeMember(bot.guild, activities=(streaming_activity(),))
    await start_session(db, GUILD, live.id, "presence", StreamInfo(url="u"), "on")

    await cog.boot_pass()

    assert await open_session_for(db, GUILD, live.id) is not None
    details = await boot_row(db)
    assert details["sessions_kept"] == 1 and details["sessions_closed"] == 0
    assert details["presence_skipped"] == {"open_session": 1}


async def test_a_boot_closes_a_session_whose_streamer_went_offline_and_marks_it_ended(
    cog, bot, member, db
):
    await announcing(bot)
    await bot.store.set(GUILD, "golive_live_role_id", LIVE_ROLE)
    await cog._go_live(member, TWITCH_INFO, "presence")
    posted = bot.guild.channel.messages[0]
    assert member.added == [LIVE_ROLE]

    await cog.boot_pass()

    assert await open_session_for(db, GUILD, member.id) is None
    assert posted.content.endswith(" — stream ended")
    assert member.removed == [LIVE_ROLE]
    assert json.loads(await action_details(db, "golive.end"))["reason"] == "reconciled_on_start"
    details = await boot_row(db)
    assert details["sessions_closed"] == 1 and details["sessions_kept"] == 0


async def test_a_boot_drops_the_co_stream_side_that_ended_in_the_downtime(cog, bot, member, db):
    await announcing(bot)
    cog.helix = FakeHelix(streams=[])
    await cog._go_live(member, TWITCH_INFO, "twitch")
    await cog.add_platform(member, YOUTUBE_INFO, "youtube")
    await set_link(db, USER, "alice")
    bot.cog = FakeYouTube(live=True)

    await cog.boot_pass()

    row = await only_session(db)
    assert row["source"] == "youtube" and row["also_source"] is None
    assert "golive.end" not in await action_kinds(db)
    details = await boot_row(db)
    assert details["sessions_dropped"] == 1 and details["sessions_closed"] == 0


async def test_the_boot_sweep_announces_somebody_already_streaming_with_no_link(cog, bot, db):
    await announcing(bot)
    live = FakeMember(bot.guild, activities=(streaming_activity(),))

    await cog.boot_pass()

    row = await only_session(db)
    assert row["source"] == "presence" and row["user_id"] == live.id
    assert len(bot.guild.channel.messages) == 1
    details = await boot_row(db)
    assert details["presence_found"] == 1 and details["presence_announced"] == 1
    assert details["presence_skipped"] == {} and details["swept"] is True


async def test_the_boot_sweep_leaves_somebody_who_already_has_a_session_alone(cog, bot, db):
    await announcing(bot)
    live = FakeMember(bot.guild, activities=(streaming_activity(),))
    await cog._go_live(live, TWITCH_INFO, "presence")

    await cog.boot_pass()

    assert len(bot.guild.channel.messages) == 1
    assert len(await open_sessions(db, GUILD)) == 1
    assert (await boot_row(db))["presence_skipped"] == {"open_session": 1}


async def test_the_boot_sweep_honours_the_cooldown_after_a_bounce(cog, bot, db):
    await announcing(bot)
    live = FakeMember(bot.guild, activities=(streaming_activity(),))
    await cog._go_live(live, TWITCH_INFO, "presence")
    await cog._end_live(bot.guild, live, "presence")

    await cog.boot_pass()

    assert len(bot.guild.channel.messages) == 1
    details = await boot_row(db)
    assert details["presence_announced"] == 0
    assert details["presence_skipped"] == {"cooldown": 1}


async def test_the_boot_sweep_does_nothing_at_all_when_the_key_is_off(cog, bot, db):
    await announcing(bot)
    await bot.store.set(GUILD, "golive_boot_sweep", False)
    FakeMember(bot.guild, activities=(streaming_activity(),))

    await cog.boot_pass()

    assert await open_sessions(db, GUILD) == []
    assert bot.guild.channel.messages == []
    details = await boot_row(db)
    assert details["swept"] is False and details["members_walked"] == 0
    assert details["presence_found"] == 0


async def test_one_boot_swept_row_is_written_per_boot_with_every_count(cog, bot, db):
    await announcing(bot)
    FakeMember(bot.guild, user_id=1, activities=(streaming_activity(),))
    gone = FakeMember(bot.guild, user_id=2)
    await start_session(db, GUILD, gone.id, "presence", StreamInfo(url="u"), "on")
    still = FakeMember(bot.guild, user_id=3, activities=(streaming_activity(),))
    await start_session(db, GUILD, still.id, "presence", StreamInfo(url="u"), "on")

    await cog.boot_pass()

    assert (await action_kinds(db)).count("golive.boot_swept") == 1
    assert await boot_row(db) == {
        "sessions_kept": 1,
        "sessions_closed": 1,
        "sessions_dropped": 0,
        "swept": True,
        "members_walked": 3,
        "members_cached": True,
        "presence_found": 2,
        "presence_announced": 1,
        "presence_skipped": {"open_session": 1},
        "via": "discord",
    }


async def test_the_row_says_why_each_streaming_member_was_passed_over(cog, bot, db):
    await announcing(bot)
    await bot.store.set(GUILD, "golive_ignore_role_id", 77)
    FakeMember(bot.guild, user_id=1, roles=(77,), activities=(streaming_activity(),))
    quiet = FakeMember(bot.guild, user_id=2, activities=(streaming_activity(),))
    await set_optout(db, quiet.id)

    await cog.boot_pass()

    details = await boot_row(db)
    assert details["presence_skipped"] == {"role_filter": 1, "opted_out": 1}
    assert details["presence_announced"] == 0


async def test_the_boot_sweep_never_announces_a_bot(cog, bot, db):
    await announcing(bot)
    robot = FakeMember(bot.guild, user_id=5, activities=(streaming_activity(),))
    robot.bot = True

    await cog.boot_pass()

    assert await open_sessions(db, GUILD) == []
    details = await boot_row(db)
    assert details["members_walked"] == 1 and details["presence_found"] == 0


async def test_a_guild_whose_members_are_not_all_cached_says_so_on_the_row(cog, bot, db):
    bot.guild.chunked = False

    await cog.boot_pass()

    assert (await boot_row(db))["members_cached"] is False


async def test_two_boots_at_once_sweep_once_and_write_one_row(cog, bot, db):
    await announcing(bot)
    FakeMember(bot.guild, activities=(streaming_activity(),))

    await cog.cog_load()
    try:
        await cog.on_ready()
    finally:
        await cog.cog_unload()

    assert len(bot.guild.channel.messages) == 1
    assert len(await open_sessions(db, GUILD)) == 1
    assert (await action_kinds(db)).count("golive.boot_swept") == 1


async def test_a_cog_load_with_no_guilds_yet_leaves_the_boot_to_on_ready(cog, bot, db):
    """`setup_hook` loads the cogs before IDENTIFY, so `bot.guilds` is empty at `cog_load`.

    A pass over nothing must not close the 60-second window, or the one pass that HAS guilds
    is the one that gets skipped.
    """
    await announcing(bot)
    guild = bot.guild
    FakeMember(guild, activities=(streaming_activity(),))
    bot.guilds = []

    await cog.cog_load()
    try:
        assert await open_sessions(db, GUILD) == []
        bot.guilds = [guild]
        await cog.on_ready()
    finally:
        await cog.cog_unload()

    assert len(await open_sessions(db, GUILD)) == 1
    assert (await action_kinds(db)).count("golive.boot_swept") == 1
