import discord
import pytest

from black_bloc.cogs.content.chat import Chat, mentions_bot
from black_bloc.config import load_settings
from black_bloc.settings_store import CHAT_COOLDOWN_SECONDS, SettingsStore
from black_bloc.storage.db import Database

GUILD = 7
CHANNEL = 111
LOG_CHANNEL = 222
USER = 900
BOT_ID = 55


class FakeChannel:
    def __init__(self, channel_id=CHANNEL):
        self.id = channel_id
        self.messages = []

    async def send(self, content=None, **kwargs):
        self.messages.append({"content": content, "kwargs": kwargs})
        return None


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.member_count = 12
        self.members = []
        self.channels = {CHANNEL: FakeChannel(CHANNEL), LOG_CHANNEL: FakeChannel(LOG_CHANNEL)}

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)


class FakeMember:
    def __init__(self, guild, user_id=USER, display_name="Nia", bot=False):
        self.id = user_id
        self.guild = guild
        self.display_name = display_name
        self.name = display_name
        self.bot = bot
        self.mention = f"<@{user_id}>"


class FakeMessage:
    def __init__(
        self,
        author,
        content,
        *,
        guild=None,
        channel=None,
        mentions=None,
        mention_everyone=False,
        kind=discord.MessageType.default,
        webhook_id=None,
        raises=None,
    ):
        self.author = author
        self.content = content
        self.guild = guild
        self.channel = channel or FakeChannel()
        self.mentions = mentions if mentions is not None else []
        self.mention_everyone = mention_everyone
        self.type = kind
        self.webhook_id = webhook_id
        self.replies = []
        self.raises = raises

    async def reply(self, content=None, **kwargs):
        if self.raises is not None:
            raise self.raises
        self.replies.append({"content": content, "kwargs": kwargs})
        return None


class FakeUser:
    def __init__(self, user_id=BOT_ID):
        self.id = user_id


class FakeGuard:
    def __init__(self, allowed=CHANNEL):
        self.allowed = allowed

    def allows_channel(self, channel):
        return getattr(channel, "id", channel) == self.allowed


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guild = guild
        self.guilds = [guild]
        self.user = FakeUser()
        self.guard = None

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "c.sqlite3")
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
    return Chat(bot)


@pytest.fixture
def member(bot):
    return FakeMember(bot.guild)


def pinged(bot, member, content="hi", **kwargs):
    kwargs.setdefault("mentions", [bot.user])
    return FakeMessage(
        member,
        content,
        guild=member.guild,
        channel=bot.guild.get_channel(CHANNEL),
        **kwargs,
    )


async def rows(db, kind):
    cur = await db.conn.execute("SELECT * FROM action_log WHERE kind = ?", (kind,))
    return await cur.fetchall()


def test_mentions_bot_ignores_everyone_and_role_pings():
    me = FakeUser()
    assert mentions_bot(FakeMessage(None, "hi", mentions=[me]), me) is True
    assert mentions_bot(FakeMessage(None, "hi", mentions=[]), me) is False
    assert (
        mentions_bot(FakeMessage(None, "hi", mentions=[me], mention_everyone=True), me) is False
    )
    assert mentions_bot(FakeMessage(None, "hi", mentions=[me]), None) is False


async def test_an_at_mention_gets_a_reply_that_pings_nobody(cog, bot, member):
    message = pinged(bot, member, "<@55> hi there")
    await cog.on_message(message)

    assert len(message.replies) == 1
    reply = message.replies[0]
    assert "Nia" in reply["content"]
    assert reply["kwargs"]["mention_author"] is False
    assert reply["kwargs"]["allowed_mentions"].everyone is False
    assert reply["kwargs"]["allowed_mentions"].users is False
    assert reply["kwargs"]["allowed_mentions"].roles is False


async def test_another_bot_is_never_answered(cog, bot):
    other = FakeMember(bot.guild, user_id=41, display_name="OtherBot", bot=True)
    message = pinged(bot, other)
    await cog.on_message(message)
    assert message.replies == []


async def test_a_message_without_the_mention_is_ignored(cog, bot, member):
    message = pinged(bot, member, "hi everyone", mentions=[])
    await cog.on_message(message)
    assert message.replies == []


async def test_a_webhook_or_system_message_is_ignored(cog, bot, member):
    hook = pinged(bot, member, "<@55> hi", webhook_id=99)
    await cog.on_message(hook)
    system = pinged(bot, member, "<@55> hi", kind=discord.MessageType.pins_add)
    await cog.on_message(system)
    assert hook.replies == [] and system.replies == []


async def test_chat_mode_off_says_nothing(cog, bot, member):
    await bot.store.set(GUILD, "chat_mode", "off")
    message = pinged(bot, member, "<@55> hi")
    await cog.on_message(message)
    assert message.replies == []


async def test_the_cooldown_is_honoured_and_the_cooled_down_user_gets_nothing(cog, bot, member):
    first = pinged(bot, member, "<@55> hi")
    await cog.on_message(first)
    second = pinged(bot, member, "<@55> hi again")
    await cog.on_message(second)

    assert len(first.replies) == 1
    assert second.replies == []


async def test_the_cooldown_is_per_user(cog, bot, member):
    await cog.on_message(pinged(bot, member, "<@55> hi"))
    other = FakeMember(bot.guild, user_id=901, display_name="Sam")
    second = pinged(bot, other, "<@55> hi")
    await cog.on_message(second)
    assert len(second.replies) == 1


async def test_a_zero_cooldown_answers_every_time(cog, bot, member):
    await bot.store.set(GUILD, "chat_cooldown_seconds", 5)
    cog._answered[USER] = -1000.0
    message = pinged(bot, member, "<@55> hi")
    await cog.on_message(message)
    assert len(message.replies) == 1


async def test_test_mode_outside_the_test_channel_is_silent_not_an_error(cog, bot, member, caplog):
    bot.guard = FakeGuard(allowed=CHANNEL)
    elsewhere = FakeChannel(999)
    message = FakeMessage(
        member,
        "<@55> hi",
        guild=bot.guild,
        channel=elsewhere,
        mentions=[bot.user],
    )
    with caplog.at_level("WARNING"):
        await cog.on_message(message)

    assert message.replies == []
    assert caplog.records == []


async def test_the_test_channel_is_still_answered_under_the_guard(cog, bot, member):
    bot.guard = FakeGuard(allowed=CHANNEL)
    message = pinged(bot, member, "<@55> hey")
    await cog.on_message(message)
    assert len(message.replies) == 1


async def test_an_insult_writes_an_action_row_and_a_greeting_does_not(cog, bot, member, db):
    await cog.on_message(pinged(bot, member, "<@55> you suck"))
    found = await rows(db, "chat.insult")
    assert len(found) == 1
    assert found[0]["actor_id"] == USER
    assert '"intent": "insult"' in found[0]["details"]

    other = FakeMember(bot.guild, user_id=902, display_name="Kay")
    await cog.on_message(pinged(bot, other, "<@55> hi"))
    assert len(await rows(db, "chat.insult")) == 1


async def test_a_failed_reply_leaves_no_cooldown_and_no_action_row(cog, bot, member, db):
    message = pinged(bot, member, "<@55> you suck", raises=RuntimeError("boom"))
    await cog.on_message(message)

    assert USER not in cog._answered
    assert await rows(db, "chat.insult") == []


async def test_a_reply_in_a_dm_needs_no_guild_setting_but_still_cools_down(cog, bot):
    lone = FakeMember(None, user_id=903, display_name="Ana")
    lone.guild = None
    first = FakeMessage(lone, "<@55> hi", guild=None, mentions=[bot.user])
    await cog.on_message(first)
    second = FakeMessage(lone, "<@55> hi", guild=None, mentions=[bot.user])
    await cog.on_message(second)

    assert len(first.replies) == 1
    assert second.replies == []
    assert cog.cooldown_seconds(None) == CHAT_COOLDOWN_SECONDS
