import asyncio
from types import SimpleNamespace

import discord
import pytest

from black_bloc import sticky as rules
from black_bloc.bot import COGS
from black_bloc.cogs.moderation.sticky import MOVES_THE_COPIES, Sticky
from black_bloc.command_visibility import HIDDEN_WHEN_OFF, STAFF_ONLY
from black_bloc.config import load_settings
from black_bloc.logkinds import feature_of, is_important
from black_bloc.settings_store import SettingsStore
from black_bloc.sticky_posts import desk_of

GUILD = 7
RUNS = 333
HOME = 444
OTHER_HOME = 555
WORDS = "How to submit a run."


class FakeMessage:
    def __init__(self, channel, message_id, content):
        self.channel = channel
        self.id = message_id
        self.content = content

    async def pin(self, reason=None):
        self.pinned = True

    async def delete(self):
        if self in self.channel.messages:
            self.channel.messages.remove(self)


class FakeChannel:
    _next = 8000

    def __init__(self, channel_id, name):
        self.id = channel_id
        self.name = name
        self.type = SimpleNamespace(name="text")
        self.messages = []
        self.sends = 0

    async def send(self, content=None, **kwargs):
        self.sends += 1
        await asyncio.sleep(0)
        FakeChannel._next += 1
        message = FakeMessage(self, FakeChannel._next, content)
        self.messages.append(message)
        return message

    def get_partial_message(self, message_id):
        found = next((one for one in self.messages if one.id == int(message_id)), None)
        return found if found is not None else FakeMessage(self, int(message_id), "")


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.roles = []
        self.unavailable = False
        self.channels = {
            RUNS: FakeChannel(RUNS, "runs"),
            HOME: FakeChannel(HOME, "welcome-test"),
            OTHER_HOME: FakeChannel(OTHER_HOME, "other-home"),
        }
        for channel in self.channels.values():
            channel.guild = self

    def get_channel(self, channel_id):
        return self.channels.get(int(channel_id))


class FakeResponse:
    def __init__(self):
        self.messages = []

    def is_done(self):
        return bool(self.messages)

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeInteraction:
    def __init__(self, bot, user, guild=True):
        self.client = bot
        self.user = user
        self.guild = bot.guild if guild else None
        self.response = FakeResponse()

    async def original_response(self):
        return SimpleNamespace(id=1, embeds=[])


def staffer(bot, manage_guild=True):
    return SimpleNamespace(
        id=1,
        guild=bot.guild,
        roles=[],
        guild_permissions=SimpleNamespace(manage_guild=manage_guild),
    )


def person(channel):
    return SimpleNamespace(
        guild=channel.guild,
        channel=channel,
        author=SimpleNamespace(id=900, bot=False),
        webhook_id=None,
        type=discord.MessageType.default,
    )


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    store = SettingsStore(db, load_settings(_env_file=None))
    await store.load()
    await store.set(GUILD, "shadow_channel_id", HOME)
    await store.set(GUILD, "sticky_quiet_seconds", 0)
    guild = FakeGuild()
    return SimpleNamespace(
        db=db,
        store=store,
        settings=SimpleNamespace(origin=""),
        guard=None,
        guild=guild,
        guilds=[guild],
        user=SimpleNamespace(id=42),
        get_channel=guild.get_channel,
        get_guild=lambda guild_id: guild if int(guild_id) == GUILD else None,
    )


@pytest.fixture
async def cog(bot):
    found = Sticky(bot)
    await found.cog_load()
    yield found
    await found.cog_unload()


def channel(bot, channel_id=RUNS):
    return bot.guild.get_channel(channel_id)


async def kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


def test_the_cog_is_registered_and_its_command_hides_with_the_mode():
    assert "black_bloc.cogs.moderation.sticky" in COGS
    assert HIDDEN_WHEN_OFF["sticky_mode"] == ("sticky",)
    assert Sticky.sticky.default_permissions == STAFF_ONLY
    assert Sticky.sticky.name == "sticky"


def test_its_rows_file_under_posts_and_only_the_failures_are_important():
    assert feature_of("sticky.set") == feature_of("web.sticky.removed") == "posts"
    assert is_important("sticky.post_failed") and is_important("sticky.channel_gone")
    for routine in ("set", "edited", "paused", "resumed", "removed", "mode", "posted"):
        assert not is_important(f"sticky.{routine}")
    assert not is_important("sticky.would_post")


async def test_the_command_opens_the_panel_for_staff_only(cog, bot):
    opened = FakeInteraction(bot, staffer(bot))
    await Sticky.sticky.callback(cog, opened)
    shown = opened.response.messages[-1]
    assert shown["ephemeral"] is True and shown["embed"].title == rules.PANEL_TITLE
    assert shown["view"].message is not None

    refused = FakeInteraction(bot, staffer(bot, manage_guild=False))
    await Sticky.sticky.callback(cog, refused)
    assert "staff only" in refused.response.messages[-1]["content"]

    dm = FakeInteraction(bot, staffer(bot), guild=False)
    await Sticky.sticky.callback(cog, dm)
    assert "server" in dm.response.messages[-1]["content"]


async def test_people_talking_moves_it_and_the_listener_never_raises(cog, bot):
    await bot.store.set(GUILD, "sticky_mode", "on")
    await bot.store.set(GUILD, "sticky_min_seconds", 5)
    await cog.desk.save(bot.guild, RUNS, WORDS, 1)
    first = channel(bot).messages[0].id
    await rules.write_copy(bot.db, GUILD, RUNS, first, RUNS)
    await bot.db.conn.execute(
        "UPDATE sticky_messages SET posted_at = '2026-01-01T00:00:00+00:00'"
    )
    await bot.db.conn.commit()

    for _ in range(5):
        await cog.on_message(person(channel(bot)))
    await cog.on_message(SimpleNamespace())

    assert len(channel(bot).messages) == 1 and channel(bot).messages[0].id != first


async def test_two_reconciles_at_boot_post_exactly_one_copy(cog, bot, db):
    await bot.store.set(GUILD, "sticky_mode", "on")
    await rules.write_words(db, GUILD, RUNS, WORDS, 1)

    await asyncio.gather(cog.on_ready(), cog.reconcile(), cog.desk.settle(bot.guild))

    assert channel(bot).sends == 1 and len(channel(bot).messages) == 1
    assert (await kinds(db)).count("sticky.posted") == 1
    assert cog.desk.watched == {RUNS}


async def test_changing_the_mode_moves_the_copies_without_waiting_for_anybody_to_talk(cog, bot):
    await cog.desk.save(bot.guild, RUNS, WORDS, 1)
    assert len(channel(bot, HOME).messages) == 1

    await bot.store.set(GUILD, "sticky_mode", "on")
    assert channel(bot, HOME).messages == [] and len(channel(bot).messages) == 1

    await bot.store.set(GUILD, "sticky_mode", "off")
    assert channel(bot).messages == []
    assert (await rules.get_row(bot.db, GUILD, RUNS))["text"] == WORDS


async def test_moving_the_rehearsal_home_moves_the_rehearsal_copy(cog, bot):
    await cog.desk.save(bot.guild, RUNS, WORDS, 1)

    await bot.store.set(GUILD, "sticky_shadow_channel_id", OTHER_HOME)

    assert channel(bot, HOME).messages == []
    assert len(channel(bot, OTHER_HOME).messages) == 1
    assert set(MOVES_THE_COPIES) == {
        "sticky_mode",
        "sticky_shadow_channel_id",
        "shadow_channel_id",
        "log_channel_id",
        "points_mode",
        "points_shadow_channel_id",
    }


async def test_moving_the_log_channel_moves_a_copy_that_rehearses_in_it(cog, bot):
    await bot.store.clear(GUILD, "shadow_channel_id")
    await bot.store.set(GUILD, "log_channel_id", HOME)
    await cog.desk.save(bot.guild, RUNS, WORDS, 1)
    assert len(channel(bot, HOME).messages) == 1

    await bot.store.set(GUILD, "log_channel_id", OTHER_HOME)

    assert channel(bot, HOME).messages == []
    assert len(channel(bot, OTHER_HOME).messages) == 1


async def test_a_deleted_channel_takes_its_sticky_with_it(cog, bot, db):
    await cog.desk.save(bot.guild, RUNS, WORDS, 1)

    await cog.on_guild_channel_delete(channel(bot))
    await cog.on_guild_channel_delete(channel(bot))

    assert await rules.get_row(db, GUILD, RUNS) is None
    assert (await kinds(db)).count("sticky.channel_gone") == 1


async def test_the_cog_and_the_website_share_one_desk(cog, bot):
    assert cog.desk is desk_of(bot)
