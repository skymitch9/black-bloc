import discord
import pytest
from discord import app_commands

from black_bloc.bot import COGS, BlackBlocBot
from black_bloc.cogs.core import (
    CLEARABLE_KEYS,
    VALUE_KEYS,
    Core,
    help_lines,
    tree_commands,
)
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore, require_staff
from black_bloc.storage.db import Database

GUILD = 7
TEST_CHANNEL = 111
LOG_CHANNEL = 222
STAFF_ROLE = 555
CAKE_ROLE = 777


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id
        self.name = f"role-{role_id}"
        self.mention = f"<@&{role_id}>"


class FakePerms:
    def __init__(self, manage_guild=False, view_channel=None):
        self.manage_guild = manage_guild
        self.view_channel = view_channel


class FakeChannel:
    def __init__(self, channel_id):
        self.id = channel_id
        self.mention = f"<#{channel_id}>"
        self.messages = []
        self.visible_to = set()

    def permissions_for(self, role):
        return FakePerms(view_channel=role.id in self.visible_to)

    async def send(self, content=None, **kwargs):
        self.messages.append({"content": content, **kwargs})
        return self.messages[-1]


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black Bloc"
        self.channels = {}
        self.members = {}
        self.roles = []
        self.default_role = FakeRole(GUILD)

    def add(self, channel):
        self.channels[channel.id] = channel
        return channel

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_member(self, user_id):
        return self.members.get(user_id)


class FakeMember:
    def __init__(self, guild, user_id=900, manage_guild=False):
        self.id = user_id
        self.guild = guild
        self.display_name = "Lead"
        self.name = "lead"
        self.mention = f"<@{user_id}>"
        self.roles = []
        self.guild_permissions = FakePerms(manage_guild=manage_guild)
        guild.members[user_id] = self


class FakeBot:
    def __init__(self, db, store, guild):
        self.db = db
        self.store = store
        self.guild = guild
        self.guilds = [guild]
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

    @property
    def sent(self):
        return self.response.messages[-1]["content"] if self.response.messages else None


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
    await store.set(GUILD, "log_channel_id", LOG_CHANNEL)
    guild = FakeGuild()
    guild.add(FakeChannel(TEST_CHANNEL))
    guild.add(FakeChannel(LOG_CHANNEL))
    return FakeBot(db, store, guild)


@pytest.fixture
def cog(bot):
    return Core(bot)


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


def test_the_choices_cover_every_key_and_fit_discords_limit():
    assert "birthday_role_id" in CLEARABLE_KEYS and "birthday_channel_id" in CLEARABLE_KEYS
    assert "birthday_color" in VALUE_KEYS
    assert "bot_bio" in VALUE_KEYS and "status_prefix" in VALUE_KEYS
    assert len(CLEARABLE_KEYS) <= 25
    assert len(VALUE_KEYS) <= 25


async def test_settings_show_is_split_into_messages_discord_will_take(bot, cog):
    interaction = FakeInteraction(bot, FakeMember(bot.guild, user_id=1, manage_guild=True))

    await cog.settings_show.callback(cog, interaction)

    said = [message["content"] for message in interaction.response.messages]
    assert len(said) > 1
    assert all(len(chunk) <= 1900 for chunk in said)
    assert all(message["ephemeral"] for message in interaction.response.messages)
    assert "automod_mode" in "\n".join(said)


async def test_settings_show_is_staff_only(bot, cog, member):
    interaction = FakeInteraction(bot, member)

    await cog.settings_show.callback(cog, interaction)

    assert "staff only" in interaction.response.messages[0]["content"]


async def test_clearing_a_setting_is_staff_only(bot, cog, member):
    await bot.store.set(GUILD, "birthday_role_id", CAKE_ROLE)
    interaction = FakeInteraction(bot, member)
    choice = discord.app_commands.Choice(name="birthday_role_id", value="birthday_role_id")

    await cog.settings_clear.callback(cog, interaction, choice)

    assert "staff only" in interaction.sent
    assert bot.store.get(GUILD, "birthday_role_id") == CAKE_ROLE


async def test_clearing_a_setting_puts_the_default_back_and_is_recorded(bot, cog, member):
    give_staff(bot, member)
    await bot.store.set(GUILD, "birthday_role_id", CAKE_ROLE)
    choice = discord.app_commands.Choice(name="birthday_role_id", value="birthday_role_id")
    interaction = FakeInteraction(bot, member)

    await cog.settings_clear.callback(cog, interaction, choice)

    assert bot.store.get(GUILD, "birthday_role_id") is None
    assert "no longer set" in interaction.sent
    assert interaction.response.messages[-1]["ephemeral"] is True
    assert await kinds(bot.db) == ["settings.clear"]


async def test_clearing_something_that_was_never_set_says_so_and_logs_nothing(bot, cog, member):
    give_staff(bot, member)
    choice = discord.app_commands.Choice(name="birthday_role_id", value="birthday_role_id")
    interaction = FakeInteraction(bot, member)

    await cog.settings_clear.callback(cog, interaction, choice)

    assert "was not set" in interaction.sent
    assert await kinds(bot.db) == []


tempvoice = app_commands.Group(name="tempvoice", description="Temporary voice channels")
zoo = app_commands.Group(name="zoo", description="Animals", parent=tempvoice)


@app_commands.command(name="ping", description="Check that Black Bloc is alive")
async def a_plain_command(interaction):
    await interaction.response.send_message("pong")


@tempvoice.command(name="setup", description="Create or repair the join-to-create channel")
async def a_staff_subcommand(interaction):
    if not await require_staff(interaction):
        return


@tempvoice.command(name="claim", description="Take over an abandoned channel")
async def an_open_subcommand(interaction):
    await interaction.response.send_message("yours")


@zoo.command(name="feed", description="Feed the animals")
async def a_nested_subcommand(interaction):
    await interaction.response.send_message("fed")


rolemenu = app_commands.Group(name="rolemenu", description="Self-serve role panels")


@rolemenu.command(name="post", description="Post or refresh a role menu panel")
async def a_rolemenu_subcommand(interaction):
    await interaction.response.send_message("posted")


@app_commands.command(name="here", description="Only this guild has it")
async def a_guild_only_command(interaction):
    await interaction.response.send_message("here")


class FakeTree:
    def __init__(self, everywhere, in_this_guild=()):
        self.everywhere = list(everywhere)
        self.in_this_guild = list(in_this_guild)

    def get_commands(self, guild=None):
        return list(self.in_this_guild) if guild is not None else list(self.everywhere)


@pytest.fixture
def helpful(bot):
    bot.tree = FakeTree([a_plain_command, tempvoice], [a_guild_only_command])
    return bot


def test_help_lines_walk_groups_and_subgroups_under_one_bold_heading():
    lines = help_lines([a_plain_command, tempvoice])

    assert lines == [
        "**/ping** — Check that Black Bloc is alive",
        "**/tempvoice** — Temporary voice channels",
        "/tempvoice claim — Take over an abandoned channel",
        "/tempvoice setup — Create or repair the join-to-create channel (staff)",
        "/tempvoice zoo feed — Feed the animals",
    ]


def test_help_lines_keep_the_heading_when_the_filter_matches_the_group():
    assert help_lines([a_plain_command, tempvoice], "zoo") == [
        "**/tempvoice** — Temporary voice channels",
        "/tempvoice zoo feed — Feed the animals",
    ]
    assert help_lines([a_plain_command, tempvoice], "PING") == [
        "**/ping** — Check that Black Bloc is alive"
    ]
    assert help_lines([a_plain_command, tempvoice], "nothing like this") == []


async def test_help_answers_with_every_command_including_the_guild_s_own(helpful, cog, member):
    interaction = FakeInteraction(helpful, member)

    await cog.help_command.callback(cog, interaction, None)

    said = "\n".join(message["content"] for message in interaction.response.messages)
    assert "**/here** — Only this guild has it" in said
    assert "/tempvoice setup — Create or repair the join-to-create channel (staff)" in said
    assert all(message["ephemeral"] for message in interaction.response.messages)
    assert all(
        message["allowed_mentions"].everyone is False
        for message in interaction.response.messages
    )


async def test_help_omits_a_command_a_feature_mode_is_hiding(bot, cog, member):
    bot.tree = FakeTree([a_plain_command, rolemenu])
    interaction = FakeInteraction(bot, member)

    await cog.help_command.callback(cog, interaction, None)

    said = "\n".join(message["content"] for message in interaction.response.messages)
    assert "/rolemenu" not in said
    assert "**/ping** — Check that Black Bloc is alive" in said


async def test_help_lists_the_command_again_once_the_mode_is_on(bot, cog, member):
    bot.tree = FakeTree([a_plain_command, rolemenu])
    await bot.store.set(GUILD, "rolemenu_mode", "on")
    interaction = FakeInteraction(bot, member)

    await cog.help_command.callback(cog, interaction, None)

    said = "\n".join(message["content"] for message in interaction.response.messages)
    assert "/rolemenu post — Post or refresh a role menu panel" in said


async def test_help_says_so_when_the_filter_matches_nothing(helpful, cog, member):
    interaction = FakeInteraction(helpful, member)

    await cog.help_command.callback(cog, interaction, "quidditch")

    assert "No command matches **quidditch**" in interaction.sent
    assert len(interaction.response.messages) == 1


async def test_help_is_split_into_messages_discord_will_take(helpful, cog, member):
    many = [
        app_commands.Command(
            name=f"c{index}",
            description="A command with a description long enough to fill a page " * 2,
            callback=a_plain_command.callback,
        )
        for index in range(40)
    ]
    helpful.tree = FakeTree(many)
    interaction = FakeInteraction(helpful, member)

    await cog.help_command.callback(cog, interaction, None)

    said = [message["content"] for message in interaction.response.messages]
    assert len(said) > 1
    assert all(len(chunk) <= 1900 for chunk in said)


async def test_help_marks_the_staff_commands_the_real_bot_registers(settings):
    black_bloc = BlackBlocBot(settings)
    for name in COGS:
        await black_bloc.load_extension(name)

    said = "\n".join(help_lines(tree_commands(black_bloc.tree)))
    await black_bloc.close()

    assert "**/help** — List every command Black Bloc can run" in said
    assert "/tempvoice setup — Create or repair the join-to-create channel (staff)" in said
    assert "/settings show — Show Black Bloc's settings for this server (staff)" in said
    assert "**/warn** — " in said and "(staff)" in said.split("**/warn** — ")[1].split("\n")[0]
    assert "**/ping** — Check that Black Bloc is alive" in said
