from types import SimpleNamespace

import discord
import pytest

from black_bloc.chat import (
    BUILTIN_ORDER,
    UNKNOWN,
    add_line,
    invalidate,
    lines_for,
    list_intents,
    loaded_intents,
    seed_defaults,
    update_line,
)
from black_bloc.cogs.content.chat import Chat, in_a_thread, mentions_bot
from black_bloc.config import load_settings
from black_bloc.settings_store import CHAT_COOLDOWN_SECONDS, SettingsStore
from black_bloc.storage.db import Database

GUILD = 7
CHANNEL = 111
LOG_CHANNEL = 222
USER = 900
BOT_ID = 55


class StaffRole:
    def __init__(self, role_id, name):
        self.id = role_id
        self.name = name

    def is_default(self):
        return self.id == GUILD

    def is_bot_managed(self):
        return False


class FakePermissions:
    def __init__(self, view_channel):
        self.view_channel = view_channel


class FakeChannel:
    def __init__(self, channel_id=CHANNEL, kind="text"):
        self.id = channel_id
        self.type = SimpleNamespace(name=kind)
        self.mention = f"<#{channel_id}>"
        self.messages = []
        self.viewers = set()

    def permissions_for(self, role):
        return FakePermissions(getattr(role, "id", None) in self.viewers)

    async def send(self, content=None, **kwargs):
        self.messages.append({"content": content, "kwargs": kwargs})
        return None


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.member_count = 12
        self.members = []
        self.roles = []
        self.channels = {CHANNEL: FakeChannel(CHANNEL), LOG_CHANNEL: FakeChannel(LOG_CHANNEL)}

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_role(self, role_id):
        return next((r for r in self.roles if r.id == int(role_id)), None)


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
        self.reactions = []
        self.raises = raises
        self.jump_url = "https://discord.test/1"

    async def reply(self, content=None, **kwargs):
        if self.raises is not None:
            raise self.raises
        self.replies.append({"content": content, "kwargs": kwargs})
        return None

    async def add_reaction(self, emoji):
        self.reactions.append(emoji)


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


async def test_the_cog_seeds_the_code_tables_the_first_time_it_loads(cog, bot, db):
    await cog.cog_load()

    stored = await loaded_intents(db, GUILD)

    assert {row["name"] for row in stored} == set(BUILTIN_ORDER) | {UNKNOWN}
    assert bot.guild.id in cog._seeded
    assert await seed_defaults(db, GUILD) == 0


async def test_seeding_runs_once_per_guild_however_often_on_ready_fires(cog, bot, db):
    await cog.on_ready()
    await cog.on_ready()

    cur = await db.conn.execute(
        "SELECT COUNT(*) AS n FROM chat_intents WHERE guild_id = ?", (GUILD,)
    )
    assert (await cur.fetchone())["n"] == len(BUILTIN_ORDER) + 1


async def test_an_edited_line_is_what_the_member_is_sent(cog, bot, db, member):
    await cog.cog_load()
    greeting = next(r for r in await list_intents(db, GUILD) if r["name"] == "greeting")
    for line in await lines_for(db, greeting["id"]):
        await update_line(db, line["id"], enabled=False)
    await add_line(db, greeting["id"], "Edited hello, {name}.")
    invalidate(bot, GUILD)

    message = pinged(bot, member, "<@55> hi there")
    await cog.on_message(message)

    assert message.replies[0]["content"] == "Edited hello, Nia."


async def test_a_settings_change_drops_the_cached_rows(cog, bot, db, member):
    await cog.cog_load()
    await cog.on_message(pinged(bot, member, "<@55> hi"))
    greeting = next(r for r in await list_intents(db, GUILD) if r["name"] == "greeting")
    for line in await lines_for(db, greeting["id"]):
        await update_line(db, line["id"], enabled=False)
    await add_line(db, greeting["id"], "After the change, {name}.")

    await bot.store.set(GUILD, "chat_reply_in_threads", True)

    other = FakeMember(bot.guild, user_id=905, display_name="Kay")
    message = pinged(bot, other, "<@55> hi")
    await cog.on_message(message)

    assert message.replies[0]["content"] == "After the change, Kay."


async def test_an_ignored_channel_is_never_answered(cog, bot, member):
    await bot.store.set(GUILD, "chat_ignore_channels", [CHANNEL])
    message = pinged(bot, member, "<@55> hi")
    await cog.on_message(message)
    assert message.replies == []


async def test_a_thread_is_answered_unless_the_server_says_otherwise(cog, bot, member):
    thread = FakeChannel(777, kind="public_thread")
    inside = FakeMessage(
        member, "<@55> hi", guild=bot.guild, channel=thread, mentions=[bot.user]
    )
    await cog.on_message(inside)
    assert len(inside.replies) == 1

    await bot.store.set(GUILD, "chat_reply_in_threads", False)
    other = FakeMember(bot.guild, user_id=906, display_name="Sam")
    quiet = FakeMessage(other, "<@55> hi", guild=bot.guild, channel=thread, mentions=[bot.user])
    await cog.on_message(quiet)
    assert quiet.replies == []


async def test_a_bare_hello_gets_a_toned_wave_instead_of_a_sentence(cog, bot, member):
    await bot.store.set(GUILD, "chat_greeting_reaction", True)

    message = pinged(bot, member, "<@55> hi")
    await cog.on_message(message)

    assert message.replies == []
    assert message.reactions == ["\U0001f44b\U0001f3ff"]
    assert USER in cog._answered


async def test_a_greeting_with_a_question_after_it_still_gets_words(cog, bot, member):
    await bot.store.set(GUILD, "chat_greeting_reaction", True)

    message = pinged(bot, member, "<@55> hi, how are you")
    await cog.on_message(message)

    assert len(message.replies) == 1 and message.reactions == []


async def test_the_wave_obeys_the_same_channel_guard_the_reply_does(cog, bot, member):
    await bot.store.set(GUILD, "chat_greeting_reaction", True)
    bot.guard = FakeGuard(allowed=CHANNEL)
    elsewhere = FakeChannel(999)
    message = FakeMessage(
        member, "<@55> hi", guild=bot.guild, channel=elsewhere, mentions=[bot.user]
    )

    await cog.on_message(message)

    assert message.replies == [] and message.reactions == []


async def test_a_data_intent_is_answered_from_live_state(cog, bot, member):
    message = pinged(bot, member, "<@55> how many of us are here")
    await cog.on_message(message)

    assert "12" in message.replies[0]["content"]


async def test_a_data_intent_with_nothing_to_report_uses_its_empty_line(cog, bot, member):
    message = pinged(bot, member, "<@55> whos live")
    await cog.on_message(message)

    assert "Nobody is streaming" in message.replies[0]["content"]


async def test_asking_for_a_mod_with_modmail_on_says_how_and_logs_the_route(cog, bot, member, db):
    await bot.store.set(GUILD, "modmail_enabled", True)

    message = pinged(bot, member, "<@55> i need a mod")
    await cog.on_message(message)

    assert "DM me" in message.replies[0]["content"]
    found = await rows(db, "chat.route")
    assert len(found) == 1 and found[0]["actor_id"] == USER


async def test_asking_for_a_mod_with_modmail_off_names_the_staff_roles(cog, bot, member, db):
    bot.guild.roles = [StaffRole(11, "Aunties / Uncles"), StaffRole(GUILD, "@everyone")]
    bot.guild.channels[LOG_CHANNEL].viewers = {11}
    await bot.store.set(GUILD, "staff_channel_id", LOG_CHANNEL)

    message = pinged(bot, member, "<@55> i need a mod")
    await cog.on_message(message)

    assert "Aunties / Uncles" in message.replies[0]["content"]
    assert len(await rows(db, "chat.route")) == 1


async def test_the_staff_note_is_posted_only_when_the_setting_asks_for_it(cog, bot, member):
    await bot.store.set(GUILD, "modmail_enabled", True)
    await bot.store.set(GUILD, "staff_channel_id", LOG_CHANNEL)
    staff = bot.guild.get_channel(LOG_CHANNEL)

    await cog.on_message(pinged(bot, member, "<@55> i need a mod"))
    assert [m for m in staff.messages if "asked for a mod" in str(m["content"])] == []

    await bot.store.set(GUILD, "chat_route_ping_staff", True)
    other = FakeMember(bot.guild, user_id=907, display_name="Ash")
    await cog.on_message(pinged(bot, other, "<@55> i need a mod"))

    note = [m for m in staff.messages if "asked for a mod" in str(m["content"])]
    assert len(note) == 1
    assert "https://discord.test/1" in note[0]["content"]
    assert note[0]["kwargs"]["allowed_mentions"].everyone is False


async def test_the_staff_note_is_not_posted_while_modmail_is_off(cog, bot, member):
    await bot.store.set(GUILD, "chat_route_ping_staff", True)
    await bot.store.set(GUILD, "staff_channel_id", LOG_CHANNEL)
    staff = bot.guild.get_channel(LOG_CHANNEL)

    await cog.on_message(pinged(bot, member, "<@55> i need a mod"))

    assert [m for m in staff.messages if "asked for a mod" in str(m["content"])] == []


async def test_the_staff_note_obeys_the_guard(cog, bot, member, caplog):
    await bot.store.set(GUILD, "modmail_enabled", True)
    await bot.store.set(GUILD, "chat_route_ping_staff", True)
    await bot.store.set(GUILD, "staff_channel_id", LOG_CHANNEL)
    bot.guard = FakeGuard(allowed=CHANNEL)
    staff = bot.guild.get_channel(LOG_CHANNEL)

    with caplog.at_level("WARNING"):
        await cog.on_message(pinged(bot, member, "<@55> i need a mod"))

    assert [m for m in staff.messages if "asked for a mod" in str(m["content"])] == []
    assert caplog.records == []


def test_a_thread_is_told_apart_from_an_ordinary_channel():
    assert in_a_thread(FakeChannel(1, kind="public_thread")) is True
    assert in_a_thread(FakeChannel(1, kind="private_thread")) is True
    assert in_a_thread(FakeChannel(1)) is False
    assert in_a_thread(None) is False
