import pytest

from black_bloc.cogs.core import Core
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore
from black_bloc.storage.db import Database

GUILD = 7
TEST_CHANNEL = 111
STAFF_ROLE = 600


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
        self.mention = f"<#{channel_id}>"
        self.visible_to = set()

    def permissions_for(self, role):
        return FakePerms(view_channel=role.id in self.visible_to)


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black Bloc"
        self.roles = []
        self.default_role = FakeRole(GUILD)
        self.channels = {TEST_CHANNEL: FakeChannel(TEST_CHANNEL)}

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)


class FakeMember:
    def __init__(self, guild, user_id=1, manage_guild=True):
        self.id = user_id
        self.guild = guild
        self.display_name = f"member-{user_id}"
        self.roles = []
        self.guild_permissions = FakePerms(manage_guild=manage_guild)


class FakeBot:
    def __init__(self, db, store, guild):
        self.db = db
        self.store = store
        self.guild = guild
        self.guard = None

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)


class FakeResponse:
    def __init__(self):
        self.messages = []

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


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "core.sqlite3")
    await database.connect()
    try:
        yield database
    finally:
        await database.close()


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL)
    store = SettingsStore(db, settings)
    await store.load()
    return FakeBot(db, store, FakeGuild())


async def test_settings_show_is_split_into_messages_discord_will_take(bot):
    cog = Core(bot)
    interaction = FakeInteraction(bot, FakeMember(bot.guild))

    await cog.settings_show.callback(cog, interaction)

    said = [message["content"] for message in interaction.response.messages]
    assert len(said) > 1
    assert all(len(chunk) <= 1900 for chunk in said)
    assert all(message["ephemeral"] for message in interaction.response.messages)
    assert "automod_mode" in "\n".join(said)


async def test_settings_show_is_staff_only(bot):
    cog = Core(bot)
    stranger = FakeMember(bot.guild, user_id=900, manage_guild=False)
    interaction = FakeInteraction(bot, stranger)

    await cog.settings_show.callback(cog, interaction)

    assert "staff only" in interaction.response.messages[0]["content"]
