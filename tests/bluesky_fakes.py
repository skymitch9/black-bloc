import asyncio
import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import discord

from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "bluesky" / "author_feed.json"
GUILD = 7
LOG = 222
HOME = 333
REAL = 444
ROLE = 555
NOW = datetime(2026, 10, 27, 18, 0, tzinfo=UTC)
NEWEST_URI = "at://did:plc:4lijy65gdkw6gwwctvm6kxoc/app.bsky.feed.post/3myuptyegac23"


def recorded() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class _Response:
    def __init__(self, status):
        self.status = status
        self.reason = "refused"


def refused(status=403):
    return discord.HTTPException(_Response(status), "Missing Access")


class FakeFetch:
    """Answers like the AppView: the recorded feed, or whatever a test sets."""

    def __init__(self, payload=None):
        self.payload = payload if payload is not None else recorded()
        self.status = 200
        self.raises = None
        self.body = None
        self.urls = []

    def feed(self):
        return self.payload["feed"]

    async def __call__(self, url, headers, seconds):
        self.urls.append((url, headers))
        if self.raises is not None:
            raise self.raises
        body = self.body if self.body is not None else json.dumps(self.payload).encode()
        return self.status, body


def with_feed(entries) -> FakeFetch:
    return FakeFetch({"feed": copy.deepcopy(entries)})


class FakeMessage:
    counter = 70000

    def __init__(self, content, kwargs):
        FakeMessage.counter += 1
        self.id = FakeMessage.counter
        self.content = content
        self.kwargs = kwargs


class FakeChannel:
    def __init__(self, channel_id, name="channel"):
        self.id = channel_id
        self.name = name
        self.sent = []
        self.send_raises = None

    async def send(self, content=None, **kwargs):
        if self.send_raises is not None:
            raise self.send_raises
        await asyncio.sleep(0)
        message = FakeMessage(content, kwargs)
        self.sent.append(message)
        return message


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black Bloc"
        self.unavailable = False
        self.channels = {}

    def add(self, channel):
        self.channels[channel.id] = channel
        return channel

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)


class FakeBot:
    def __init__(self, db, store_, settings, guild, fetch):
        self.db = db
        self.store = store_
        self.settings = settings
        self.guard = None
        self.guild = guild
        self.guilds = [guild]
        self.bluesky_fetch = fetch

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)


async def make_bot(db, monkeypatch, fetch=None):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=False)
    settings_store = SettingsStore(db, settings)
    await settings_store.load()
    guild = FakeGuild()
    for channel_id, name in ((LOG, "log"), (HOME, "welcome-test"), (REAL, "bsky-feed")):
        guild.add(FakeChannel(channel_id, name))
    await settings_store.set(GUILD, "log_channel_id", LOG)
    await settings_store.set(GUILD, "shadow_channel_id", HOME)
    await settings_store.set(GUILD, "bluesky_channel_id", REAL)
    return FakeBot(db, settings_store, settings, guild, fetch or FakeFetch())
