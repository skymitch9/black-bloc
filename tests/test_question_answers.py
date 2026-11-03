import logging
from datetime import UTC, datetime
from types import SimpleNamespace

import discord
import pytest

from black_bloc import question_answers as answers
from black_bloc import questions as rules
from black_bloc import questions_store
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore

GUILD = 7
QOTW = 333
ELSEWHERE = 111
POST = 4444
BOT_ID = 55
NOW = datetime(2026, 11, 2, 16, 5, tzinfo=UTC)


class Message:
    def __init__(self, content="", *, channel=QOTW, to=POST, guild=GUILD):
        self.id = 9001
        self.content = content
        self.guild = SimpleNamespace(id=guild) if guild is not None else None
        self.channel = SimpleNamespace(id=channel)
        self.reference = SimpleNamespace(message_id=to) if to is not None else None
        self.reactions = []
        self.raises = None

    async def add_reaction(self, emoji):
        if self.raises is not None:
            raise self.raises
        self.reactions.append(emoji)


class Guard:
    def allows_channel(self, channel):
        return False


class Untouchable:
    is_connected = True

    @property
    def conn(self):
        raise AssertionError("the database was read")


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "question_channel_id", QOTW)
    return SimpleNamespace(db=db, store=store, guard=None, user=SimpleNamespace(id=BOT_ID))


async def posted(bot, message_id=POST, by=rules.BY_BOT):
    [found] = await questions_store.add_many(bot.db, GUILD, ["What song?"], 1, NOW)
    await questions_store.mark_posted(bot.db, found, None, by, QOTW, message_id, NOW)
    return found


def test_only_a_typed_mention_names_the_bot():
    me = SimpleNamespace(id=BOT_ID)
    assert answers.names_bot(Message("<@55> mine is this"), me)
    assert answers.names_bot(Message("hey <@!55>"), me)
    assert not answers.names_bot(Message("https://youtu.be/x"), me)
    assert not answers.names_bot(Message("<@555> mine"), me)
    assert not answers.names_bot(Message("<@55>"), None)


async def test_a_reply_to_the_posted_question_in_its_channel_is_an_answer(bot):
    await posted(bot)
    assert await answers.is_answer(bot, Message("https://youtu.be/x"))


async def test_a_reply_to_the_owners_own_post_is_an_answer_too(bot):
    await posted(bot, message_id=5555, by=rules.BY_OWNER)
    assert await answers.is_answer(bot, Message("this one", to=5555))


async def test_anything_else_is_not_an_answer(bot):
    await posted(bot)
    assert not await answers.is_answer(bot, Message("x", channel=ELSEWHERE))
    assert not await answers.is_answer(bot, Message("x", to=None))
    assert not await answers.is_answer(bot, Message("x", to=7777))
    assert not await answers.is_answer(bot, Message("x", guild=None))
    await bot.store.clear(GUILD, "question_channel_id")
    assert not await answers.is_answer(bot, Message("x"))


async def test_the_database_is_read_only_for_a_reply_in_the_question_channel(bot):
    bot.db = Untouchable()
    assert not await answers.is_answer(bot, Message("x", to=None))
    assert not await answers.is_answer(bot, Message("x", channel=ELSEWHERE))


async def test_an_answer_gets_the_configured_reaction(bot):
    message = Message()
    assert await answers.react(bot, message)
    assert [str(one) for one in message.reactions] == ["\U0001f3b5"]


async def test_a_server_emoji_is_reacted_with_as_itself(bot):
    await bot.store.set(GUILD, "question_answer_reaction", "<:bloc:123456789012345678>")
    message = Message()
    assert await answers.react(bot, message)
    [emoji] = message.reactions
    assert isinstance(emoji, discord.PartialEmoji) and emoji.id == 123456789012345678


async def test_blank_or_switched_off_reacts_with_nothing(bot):
    await bot.store.set(GUILD, "question_answer_reaction", "")
    message = Message()
    assert not await answers.react(bot, message)
    await bot.store.set(GUILD, "question_answer_reaction", "\U0001f525")
    await bot.store.set(GUILD, "question_answer_react", False)
    assert not await answers.react(bot, message)
    assert message.reactions == []


async def test_the_test_mode_guard_holds_the_reaction_back(bot):
    bot.guard = Guard()
    message = Message()
    assert not await answers.react(bot, message)
    assert message.reactions == []


async def test_a_reaction_discord_refuses_is_a_warning_not_a_crash(bot, caplog):
    message = Message()
    message.raises = discord.HTTPException(SimpleNamespace(status=403, reason="Forbidden"), "no")
    with caplog.at_level(logging.WARNING, logger="black_bloc.question_answers"):
        assert not await answers.react(bot, message)
    assert "not reacted to" in caplog.text
