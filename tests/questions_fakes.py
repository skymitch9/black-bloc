import asyncio
from datetime import UTC, datetime, timedelta

import discord

from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore

GUILD = 7
LOG = 222
HOME = 333
REAL = 444
OWNER = 123456789012345678
OTHER = 223456789012345678
SLOT = datetime(2026, 10, 19, 16, 0, tzinfo=UTC)
AFTER_GRACE = SLOT + timedelta(minutes=6)
BODY = "What game got you into speedrunning?"


class _Response:
    def __init__(self, status):
        self.status = status
        self.reason = "refused"


def refused(status=403):
    return discord.HTTPException(_Response(status), "no")


class FakeMessage:
    counter = 9000

    def __init__(self, content, author=None, at=None, channel=None):
        FakeMessage.counter += 1
        self.id = FakeMessage.counter
        self.content = content
        self.author = author
        self.type = discord.MessageType.default
        self.created_at = at or SLOT
        self.channel = channel
        self.threads = []
        self.thread_raises = None

    async def create_thread(self, name, **kwargs):
        if self.thread_raises is not None:
            raise self.thread_raises
        self.threads.append(name)


class Partial:
    def __init__(self, channel, message_id):
        self.channel = channel
        self.message_id = message_id

    async def delete(self):
        if self.channel.delete_raises is not None:
            raise self.channel.delete_raises
        self.channel.deleted.append(self.message_id)


class FakeChannel:
    def __init__(self, channel_id, name="channel"):
        self.id = channel_id
        self.name = name
        self.sent = []
        self.mentions = []
        self.seen = []
        self.deleted = []
        self.send_raises = None
        self.delete_raises = None
        self.history_raises = None

    async def send(self, content=None, **kwargs):
        if self.send_raises is not None:
            raise self.send_raises
        await asyncio.sleep(0)
        message = FakeMessage(content, channel=self)
        self.sent.append(message)
        self.mentions.append(kwargs.get("allowed_mentions"))
        return message

    def history(self, limit=100, after=None):
        if self.history_raises is not None:
            raise self.history_raises

        async def walk():
            for one in self.seen[:limit]:
                if after is None or one.created_at > after:
                    yield one

        return walk()

    def get_partial_message(self, message_id):
        return Partial(self, message_id)


class FakeMember:
    def __init__(self, user_id):
        self.id = user_id
        self.display_name = f"m{user_id}"
        self.name = self.display_name
        self.dms = []
        self.dm_raises = None
        self.roles = []
        self.guild = None
        self.guild_permissions = discord.Permissions.none()

    async def send(self, content=None, **kwargs):
        if self.dm_raises is not None:
            raise self.dm_raises
        self.dms.append(content)


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black Bloc"
        self.unavailable = False
        self.channels = {}
        self.members = {}

    def add(self, channel):
        self.channels[channel.id] = channel
        return channel

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_member(self, user_id):
        return self.members.get(user_id)


class FakeBot:
    def __init__(self, db, store_, settings, guild):
        self.db = db
        self.store = store_
        self.settings = settings
        self.guard = None
        self.guild = guild
        self.guilds = [guild]

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def get_user(self, user_id):
        return None

    def get_cog(self, name):
        return None


async def make_bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=False)
    settings_store = SettingsStore(db, settings)
    await settings_store.load()
    guild = FakeGuild()
    for channel_id, name in ((LOG, "log"), (HOME, "welcome-test"), (REAL, "qotw")):
        guild.add(FakeChannel(channel_id, name))
    await settings_store.set(GUILD, "log_channel_id", LOG)
    await settings_store.set(GUILD, "shadow_channel_id", HOME)
    await settings_store.set(GUILD, "question_channel_id", REAL)
    return FakeBot(db, settings_store, settings, guild)
