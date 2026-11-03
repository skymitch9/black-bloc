from datetime import UTC, datetime
from types import SimpleNamespace

import discord

from tests.questions_fakes import GUILD, LOG, REAL, FakeMember, make_bot

NINJA = "\U0001f977\U0001f3ff"
NOW = datetime(2026, 11, 2, 20, 0, tzinfo=UTC)
PT = 311111111111111111
YATO = 322222222222222222
ELSEWHERE = 555
STAFF_ID = 42


class Untouchable:
    is_connected = True

    @property
    def conn(self):
        raise AssertionError("the database was read")


class FakePost:
    counter = 70000

    def __init__(self, author_id, channel_id=REAL, *, bot=False, guild_id=GUILD):
        FakePost.counter += 1
        self.id = FakePost.counter
        self.author = SimpleNamespace(id=author_id, bot=bot)
        self.guild = SimpleNamespace(id=guild_id) if guild_id is not None else None
        self.channel = SimpleNamespace(id=channel_id)
        self.type = discord.MessageType.default
        self.webhook_id = None
        self.reactions = []
        self.raises = None

    async def add_reaction(self, emoji):
        if self.raises is not None:
            raise self.raises
        self.reactions.append(str(emoji))


class FakeResponse:
    def __init__(self):
        self.done = False
        self.messages = []
        self.modals = []

    def is_done(self):
        return self.done

    async def defer(self, **kwargs):
        self.done = True

    async def send_message(self, content=None, **kwargs):
        self.done = True
        self.messages.append({"content": content, **kwargs})

    async def send_modal(self, modal):
        self.done = True
        self.modals.append(modal)


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, **kwargs):
        self.response.messages.append({"content": content, **kwargs})


class FakeEdited:
    def __init__(self, kwargs):
        self.embeds = [kwargs.get("embed")]
        self.view = kwargs.get("view")


class FakeInteraction:
    def __init__(self, client, user):
        self.client = client
        self.user = user
        self.guild = client.guild
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)
        self.edits = []

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return FakeEdited(kwargs)

    async def original_response(self):
        return FakeEdited({})

    @property
    def said(self):
        return [one["content"] for one in self.response.messages if one["content"]]


async def ninja_bot(db, monkeypatch):
    bot = await make_bot(db, monkeypatch)
    bot.user = SimpleNamespace(id=1)
    for member_id in (PT, YATO, STAFF_ID):
        member = FakeMember(member_id)
        member.guild = bot.guild
        bot.guild.members[member_id] = member
    bot.guild.members[STAFF_ID].guild_permissions = discord.Permissions(manage_guild=True)
    return bot


async def kinds(db):
    cur = await db.conn.execute("SELECT kind, details FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


__all__ = [
    "ELSEWHERE",
    "GUILD",
    "LOG",
    "NINJA",
    "NOW",
    "PT",
    "REAL",
    "STAFF_ID",
    "YATO",
    "FakeInteraction",
    "FakePost",
    "Untouchable",
    "kinds",
    "ninja_bot",
]
