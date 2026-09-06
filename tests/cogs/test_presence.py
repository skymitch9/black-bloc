import asyncio
from types import SimpleNamespace

import discord
import pytest

from black_bloc.cogs.presence import Presence, apply_sentence, reapply_presence
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore

GUILD = 7
TEST_CHANNEL = 111
STAFF_ROLE = 555


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id
        self.name = f"role-{role_id}"


class FakePerms:
    def __init__(self, manage_guild=False, view_channel=None):
        self.manage_guild = manage_guild
        self.view_channel = view_channel


class FakeChannel:
    def __init__(self, channel_id):
        self.id = channel_id
        self.messages = []
        self.visible_to = set()

    def permissions_for(self, role):
        return FakePerms(view_channel=role.id in self.visible_to)

    async def send(self, content=None, **kwargs):
        self.messages.append({"content": content, **kwargs})
        return self.messages[-1]


class FakeGuild:
    def __init__(self, member_count=12, bots=2):
        self.id = GUILD
        self.member_count = member_count
        self.members = [SimpleNamespace(id=n, bot=n < bots) for n in range(member_count)]
        self.channels = {TEST_CHANNEL: FakeChannel(TEST_CHANNEL)}
        self.roles = []

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)


class FakeMember:
    def __init__(self, guild, user_id=900):
        self.id = user_id
        self.guild = guild
        self.mention = f"<@{user_id}>"
        self.roles = []
        self.guild_permissions = FakePerms()


class FakeApp:
    def __init__(self):
        self.description = ""
        self.edits = []

    async def edit(self, **kwargs):
        self.edits.append(kwargs)
        self.description = kwargs.get("description", self.description)
        return self


class FakeBot:
    def __init__(self, db, store, guild, app):
        self.db = db
        self.store = store
        self.settings = store.settings
        self.guild = guild
        self.guilds = [guild]
        self.app = app
        self.presences = []
        self.refuse_presence = None
        self.ready = asyncio.Event()
        self.cog = None

    def get_cog(self, name):
        return self.cog if name == "Presence" else None

    def get_guild(self, guild_id):
        return self.guild if self.guild is not None and self.guild.id == guild_id else None

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id) if self.guild is not None else None

    async def wait_until_ready(self):
        await self.ready.wait()

    async def application_info(self):
        return self.app

    async def change_presence(self, *, activity=None, status=None):
        if self.refuse_presence is not None:
            raise self.refuse_presence
        self.presences.append(activity)


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.deferred = False

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def defer(self, ephemeral=False):
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

    @property
    def sent(self):
        return self.response.messages[-1]["content"] if self.response.messages else None



@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(
        _env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL, dev_guild_id=GUILD
    )
    store = SettingsStore(db, settings)
    await store.load()
    return FakeBot(db, store, FakeGuild(), FakeApp())


@pytest.fixture
async def cog(bot):
    made = Presence(bot)
    bot.cog = made
    try:
        yield made
    finally:
        bot.cog = None
        await made.cog_unload()
        await asyncio.sleep(0)


@pytest.fixture
def member(bot):
    return FakeMember(bot.guild)


def give_staff(bot, member):
    role = FakeRole(STAFF_ROLE)
    bot.guild.roles.append(role)
    bot.guild.get_channel(TEST_CHANNEL).visible_to.add(STAFF_ROLE)
    member.roles.append(role)


async def kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


def test_the_answer_says_what_happened_to_both_halves():
    assert "now says" in apply_sentence(True, "Cookout attendees: 10")
    assert "`Cookout attendees: 10`" in apply_sentence(True, "Cookout attendees: 10")
    assert "left alone" in apply_sentence(False, "Cookout attendees: 10")
    assert "could not be set" in apply_sentence(False, None)


async def test_the_health_tab_asks_by_the_name_it_derives_from_the_loop(bot, cog):
    name = cog.status.coro.__name__

    assert name == "status"
    assert cog.loop_health(name) == (None, None)
    assert cog.loop_health("something else") == (None, None)

    await cog.apply_status()

    last_ok_at, last_error = cog.loop_health(name)
    assert last_ok_at is not None and last_error is None


async def test_a_status_discord_refuses_is_recorded_for_the_health_tab(bot, cog):
    bot.refuse_presence = RuntimeError("the gateway went away")

    assert await cog.apply_status() is None
    assert cog.loop_health("status") == (None, "RuntimeError: the gateway went away")


async def test_a_loop_that_stops_is_recorded_and_started_again(bot, cog):
    await cog._status_stopped(RuntimeError("the gateway went away"))

    assert cog.last_error == "RuntimeError: the gateway went away"


async def test_starting_up_sets_the_status_and_writes_the_bio_once(bot, cog):
    await cog.on_ready()

    assert bot.presences[-1].name == "Cookout attendees: 10"
    assert bot.app.edits == [{"description": bot.store.get(GUILD, "bot_bio")}]
    assert await kinds(bot.db) == ["presence.bio_set"]
    assert cog.status.is_running()

    await cog.on_ready()

    assert len(bot.app.edits) == 1
    assert len(bot.presences) == 2


async def test_someone_joining_or_leaving_refreshes_the_count_once(bot, cog, monkeypatch):
    monkeypatch.setattr("black_bloc.cogs.presence.DEBOUNCE_SECONDS", 0)
    member = FakeMember(bot.guild, user_id=42)

    await cog.on_member_join(member)
    await cog.on_member_join(member)
    await cog.on_member_remove(member)
    await asyncio.sleep(0.05)

    assert [activity.name for activity in bot.presences] == ["Cookout attendees: 10"]


async def test_reapply_presence_says_so_when_the_status_could_not_be_set(bot, cog, monkeypatch):
    """`apply_sentence`'s third outcome, kept from the retired `/presence apply` test."""

    async def refuses(_bot):
        raise RuntimeError("no")

    monkeypatch.setattr("black_bloc.cogs.presence.update_status", refuses)

    said = await reapply_presence(bot)

    assert "now says" in said
    assert "could not be set" in said and "in Black Bloc's own log" in said
    assert cog.last_error.startswith("RuntimeError")


async def test_reapply_presence_is_the_one_implementation_both_doors_call(bot, cog):
    said = await reapply_presence(bot)

    assert "now says" in said and "`Cookout attendees: 10`" in said
    assert isinstance(bot.presences[-1], discord.CustomActivity)
    assert "left alone" in await reapply_presence(bot)


async def test_reapply_presence_answers_nothing_at_all_when_the_cog_is_not_loaded(bot):
    """S8 — the panel does not draw the button, and a cog unloaded mid-card still cannot lie."""
    assert bot.get_cog("Presence") is None
    assert await reapply_presence(bot) is None
    assert bot.presences == [] and bot.app.edits == []
