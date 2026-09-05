from types import SimpleNamespace

import discord
import pytest

from black_bloc import selftest, selftest_panels
from black_bloc.bot import COGS, BlackBlocBot
from black_bloc.config import load_settings
from black_bloc.storage.db import Database

GUILD = 4242
TEST_CHANNEL = 111
STAFF_ROLE = 555
PING_ROLE = 556
BOT_ID = 900
ACTOR_ID = 7


class Perms:
    def __init__(self, **granted):
        self.granted = granted

    def __getattr__(self, name):
        return self.granted.get(name, True)


class Role:
    def __init__(self, role_id, name):
        self.id = role_id
        self.name = name
        self.mention = f"<@&{role_id}>"
        self.position = 1
        self.managed = False
        self.color = 0
        self.colour = 0
        self.members = []
        self.permissions = Perms(manage_guild=False)

    def is_assignable(self):
        return True


class Message:
    def __init__(self, message_id, channel, kwargs):
        self.id = message_id
        self.channel = channel
        self.kwargs = kwargs
        self.embeds = [kwargs["embed"]] if kwargs.get("embed") else []


class Channel:
    def __init__(self, channel_id, name, kind="text"):
        self.id = channel_id
        self.name = name
        self.mention = f"<#{channel_id}>"
        self.type = SimpleNamespace(name=kind)
        self.position = 0
        self.category = None
        self.category_id = None
        self.messages = []
        self.voice_states = {}
        self.overwrites = {}
        self.guild = None

    def permissions_for(self, who):
        return Perms()

    async def send(self, **kwargs):
        self.messages.append(Message(9000 + len(self.messages), self, kwargs))
        return self.messages[-1]

    async def delete_messages(self, messages):
        wanted = {getattr(one, "id", one) for one in messages}
        self.messages = [one for one in self.messages if one.id not in wanted]


class Member:
    def __init__(self, user_id, guild, roles):
        self.id = user_id
        self.name = f"user{user_id}"
        self.display_name = self.name.title()
        self.mention = f"<@{user_id}>"
        self.guild = guild
        self.roles = roles
        self.guild_permissions = Perms(manage_guild=True)
        self.display_avatar = SimpleNamespace(url="https://cdn.test/a.png")
        self.bot = False


class Guild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black in a Flash!"
        self.owner_id = 999
        self.roles = [Role(STAFF_ROLE, "Aunties / Uncles"), Role(PING_ROLE, "Events")]
        self.channels = [Channel(TEST_CHANNEL, "mute-me-bot-test-spam")]
        for channel in self.channels:
            channel.guild = self
        self.members = {}
        self.default_role = Role(GUILD, "@everyone")
        self.me = Member(BOT_ID, self, list(self.roles))
        self.members[BOT_ID] = self.me
        self.members[ACTOR_ID] = Member(ACTOR_ID, self, list(self.roles))
        self.scheduled_events = []
        self.emojis = []

    def get_channel(self, channel_id):
        return next((one for one in self.channels if one.id == int(channel_id)), None)

    def get_role(self, role_id):
        return next((one for one in self.roles if one.id == int(role_id)), None)

    def get_member(self, user_id):
        return self.members.get(int(user_id))

    @property
    def text_channels(self):
        return [one for one in self.channels if one.type.name == "text"]

    @property
    def voice_channels(self):
        return []

    @property
    def categories(self):
        return []


@pytest.fixture
async def live(tmp_path, monkeypatch):
    """A REAL bot with every cog loaded — the panel family is only proof if the builders
    are the ones the command handlers call, so nothing here is stubbed."""
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(
        _env_file=None,
        database_path=tmp_path / "panels.sqlite3",
        test_mode=True,
        test_channel_id=TEST_CHANNEL,
        dev_guild_id=GUILD,
    )
    bot = BlackBlocBot(settings)
    bot.db = Database(tmp_path / "panels.sqlite3")
    await bot.db.connect()
    bot.store.db = bot.db
    await bot.store.load()
    guild = Guild()
    bot._connection.user = SimpleNamespace(id=BOT_ID, bot=True)
    monkeypatch.setattr(type(bot), "guilds", property(lambda _self: [guild]), raising=False)
    monkeypatch.setattr(
        type(bot), "get_channel", lambda _self, cid: guild.get_channel(cid), raising=False
    )
    for name in COGS:
        await bot.load_extension(name)
    try:
        yield (bot, guild)
    finally:
        await bot.db.close()
        await bot.close()


async def a_run(bot, guild):
    one = selftest.Run(bot=bot, guild=guild, actor=guild.get_member(ACTOR_ID))
    one.run_id = await selftest.open_run(bot.db, one)
    return one


def test_every_command_that_opens_a_panel_has_a_door_and_nothing_else_does():
    """The table is the whole claim: 18 of the 29 commands open a panel, and the other 11
    take an argument and act (`/ban`) or answer one line (`/ping`)."""
    commands = {door.command for door in selftest_panels.PANELS}

    assert len(selftest_panels.PANELS) == 18
    assert len(commands) == 18
    assert commands == {
        "settings",
        "automod",
        "honeypot",
        "mod",
        "modmail",
        "event",
        "poll",
        "birthday",
        "rolemenu",
        "voice",
        "request",
        "apply",
        "chat",
        "memory",
        "golive",
        "youtube",
        "pings",
        "raidtrain",
    }
    assert {check.name for check in selftest_panels.panel_checks()} == {
        f"panel.{name}" for name in commands
    }


async def test_every_panel_builder_is_the_one_the_command_handler_calls(live):
    """No copies: the module attribute the table names is exactly what the command's own
    body calls, so a card that renders here is the card a person is shown."""
    import ast
    import importlib
    import pathlib

    bot, _guild = live
    for door in selftest_panels.PANELS:
        module = importlib.import_module(door.module)
        assert callable(getattr(module, door.builder, None)), door.command
        source = pathlib.Path(module.__file__).read_text(encoding="utf-8")
        called = {
            node.func.id
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert door.builder in called, f"{door.module} never calls {door.builder}"
    assert bot is not None


@pytest.mark.parametrize("door", selftest_panels.PANELS, ids=lambda one: one.command)
async def test_a_panels_root_card_builds_and_posts_as_a_real_message(live, door):
    """F-ST3: the card goes out WITH its view, so the buttons are real for the few
    minutes it lives. A panel needing a target renders its empty state, which is a card."""
    bot, guild = live
    one = await a_run(bot, guild)
    check = selftest_panels.panel_check(door)

    said = await check.run(one)

    channel = guild.get_channel(TEST_CHANNEL)
    assert len(channel.messages) == 1
    posted = channel.messages[0].kwargs
    assert isinstance(posted["embed"], discord.Embed)
    assert isinstance(posted["view"], discord.ui.View)
    assert posted["embed"].title or posted["embed"].description
    assert said.startswith("posted; ")
    assert one.posted == 1


@pytest.mark.parametrize(
    "check", selftest_panels.send_checks(), ids=lambda one: one.name.split(".")[1]
)
async def test_every_feature_that_posts_on_a_schedule_renders_its_own_announcement(live, check):
    """The synthetic record goes through the feature's OWN renderer, so a template that
    stopped rendering is caught here rather than by nobody."""
    bot, guild = live
    one = await a_run(bot, guild)

    said = await check.run(one)

    channel = guild.get_channel(TEST_CHANNEL)
    assert len(channel.messages) == 1
    posted = channel.messages[0].kwargs
    embed = posted.get("embed")
    words = [str(posted.get("content") or "")]
    if embed is not None:
        words += [str(embed.title or ""), str(embed.description or "")]
    assert "".join(words).strip(), f"{check.name} posted an empty announcement"
    for said_here in words:
        assert "{" not in said_here, f"{check.name} left a placeholder unrendered: {said_here}"
    assert said.startswith("posted; ")


async def test_the_cards_a_panel_posts_are_counted_and_written_down(live):
    bot, guild = live
    one = await a_run(bot, guild)
    await selftest_panels.panel_check(selftest_panels.PANELS[0]).run(one)
    await selftest_panels.panel_check(selftest_panels.PANELS[1]).run(one)

    waiting = await selftest.waiting_messages(bot.db, GUILD)

    assert one.posted == 2
    assert len(waiting) == 2
    assert {row["channel_id"] for row in waiting} == {TEST_CHANNEL}


def test_a_view_is_counted_as_buttons_and_selects_rather_than_children():
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Go"))
    view.add_item(discord.ui.Select(options=[discord.SelectOption(label="One")]))
    view.add_item(discord.ui.Button(label="Back"))

    assert selftest_panels.counted(view) == {"buttons": 2, "selects": 1}


async def test_the_actor_is_whoever_asked_and_the_bot_itself_at_boot(live):
    bot, guild = live

    asked = selftest.Run(bot=bot, guild=guild, actor=guild.get_member(ACTOR_ID))
    assert selftest_panels.panel_actor(asked).id == ACTOR_ID

    booted = selftest.Run(bot=bot, guild=guild)
    assert selftest_panels.panel_actor(booted).id == BOT_ID
