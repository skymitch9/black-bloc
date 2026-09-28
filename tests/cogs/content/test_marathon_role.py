import json

import discord
import pytest

from black_bloc.cogs.content import marathon_role as cog_role
from black_bloc.cogs.content.marathon import Marathons
from black_bloc.config import load_settings
from black_bloc.pings import FORBIDDEN
from black_bloc.settings_store import SettingsStore

GUILD = 7
CHANNEL = 111
ROLE = 55


class FakeRole:
    def __init__(self, role_id=ROLE, name="Marathon", **perms):
        self.id = role_id
        self.name = name
        self.managed = False
        self.permissions = discord.Permissions(**perms)

    def is_default(self):
        return False


class FakeMember:
    def __init__(self, user_id=900, refuse=False):
        self.id = user_id
        self.roles = []
        self.refuse = refuse
        self.reasons = []

    async def add_roles(self, *roles, reason=None):
        if self.refuse:
            raise discord.Forbidden(FakeHttp(), "Missing Permissions")
        self.reasons.append(reason)
        self.roles += [role for role in roles if role not in self.roles]

    async def remove_roles(self, *roles, reason=None):
        self.reasons.append(reason)
        self.roles = [role for role in self.roles if role not in roles]


class FakeHttp:
    status = 403
    reason = "Forbidden"


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.roles = {}

    def get_role(self, role_id):
        return self.roles.get(int(role_id))

    def get_channel(self, channel_id):
        return None

    def get_member(self, user_id):
        return None


class FakeGuard:
    def allows_channel(self, channel_id):
        return False

    def refusal_message(self):
        return "Only in the test channel while testing."


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guild = guild
        self.guilds = [guild]
        self.guard = None

    def get_channel(self, channel_id):
        return None

    def get_guild(self, guild_id):
        return self.guild


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.deferred = None

    def is_done(self):
        return self.deferred is not None or bool(self.messages)

    async def defer(self, ephemeral=False, thinking=False):
        self.deferred = {"ephemeral": ephemeral, "thinking": thinking}

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.response.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeInteraction:
    def __init__(self, bot, user, guild=True):
        self.client = bot
        self.user = user
        self.guild = bot.guild if guild else None
        self.channel_id = CHANNEL
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)

    @property
    def said(self):
        return self.response.messages[-1]["content"]


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=CHANNEL)
    store = SettingsStore(db, settings)
    await store.load()
    return FakeBot(db, store, settings, FakeGuild())


@pytest.fixture
async def role(bot):
    found = FakeRole()
    bot.guild.roles[ROLE] = found
    await bot.store.set(GUILD, "marathon_role_id", ROLE)
    return found


async def logged(db):
    cur = await db.conn.execute("SELECT kind, details FROM action_log ORDER BY id")
    return [(row["kind"], json.loads(row["details"] or "{}")) for row in await cur.fetchall()]


async def test_the_first_press_gives_the_role_and_says_so_privately(bot, role, db):
    member = FakeMember()
    pressed = FakeInteraction(bot, member)

    await cog_role.toggle_marathon_role(pressed)

    assert member.roles == [role]
    sent = pressed.response.messages[-1]
    assert sent["ephemeral"] is True and "**Marathon**" in sent["content"]
    assert sent["allowed_mentions"].to_dict() == discord.AllowedMentions.none().to_dict()
    assert [kind for kind, _ in await logged(db)] == ["marathon.role_joined"]


async def test_the_next_press_takes_it_back(bot, role, db):
    member = FakeMember()
    member.roles = [role]
    pressed = FakeInteraction(bot, member)

    await cog_role.toggle_marathon_role(pressed)

    assert member.roles == []
    assert "off you now" in pressed.said
    assert [kind for kind, _ in await logged(db)] == ["marathon.role_left"]


async def test_with_no_role_picked_the_press_says_staff_have_not_set_it_up(bot, db):
    member = FakeMember()
    pressed = FakeInteraction(bot, member)

    await cog_role.toggle_marathon_role(pressed)

    assert "not set up the Marathon role" in pressed.said
    assert member.roles == [] and await logged(db) == []


async def test_a_role_with_staff_permissions_is_refused_and_staff_see_why(bot, db):
    bot.guild.roles[ROLE] = FakeRole(administrator=True)
    await bot.store.set(GUILD, "marathon_role_id", ROLE)
    member = FakeMember()
    pressed = FakeInteraction(bot, member)

    await cog_role.toggle_marathon_role(pressed)

    assert member.roles == [] and "not set up" in pressed.said
    assert await logged(db) == [
        ("marathon.role_failed", {"role_id": ROLE, "reason": "unsafe", "via": "discord"}),
    ]


async def test_discord_refusing_the_change_is_a_failed_row_and_a_sentence(bot, role, db):
    member = FakeMember(refuse=True)
    pressed = FakeInteraction(bot, member)

    await cog_role.toggle_marathon_role(pressed)

    assert pressed.said == FORBIDDEN.format(role="Marathon")
    kinds = [kind for kind, _ in await logged(db)]
    assert kinds == ["marathon.role_failed"]


async def test_a_dm_press_is_refused_in_words(bot, role):
    pressed = FakeInteraction(bot, FakeMember(), guild=False)

    await cog_role.toggle_marathon_role(pressed)

    assert "server itself" in pressed.said


async def test_the_guard_is_asked_before_a_role_changes(bot, role):
    bot.guard = FakeGuard()
    member = FakeMember()
    pressed = FakeInteraction(bot, member)

    await cog_role.toggle_marathon_role(pressed)

    assert member.roles == [] and pressed.said == "Only in the test channel while testing."


async def test_the_block_is_one_card_and_one_guild_keyed_button(bot):
    embed, view, stamp = cog_role.block_parts(bot, bot.guild, None)

    (press,) = view.children
    assert isinstance(press, cog_role.MarathonRoleButton)
    assert press.custom_id == f"marathonrole:toggle:{GUILD}"
    assert press.item.label == "Get or drop the Marathon role"
    assert embed.title == "The Marathon role" and view.timeout is None and stamp


async def test_the_block_s_button_is_the_toggle(bot, role):
    member = FakeMember()
    pressed = FakeInteraction(bot, member)

    await cog_role.MarathonRoleButton(GUILD).callback(pressed)

    assert member.roles == [role]


async def test_the_button_is_registered_by_the_marathon_cog_so_it_outlives_a_restart():
    registered = []
    made = Marathons.__new__(Marathons)
    made.bot = type("Bot", (), {"db": type("Db", (), {"is_connected": False})()})()
    made.bot.add_dynamic_items = lambda *items: registered.extend(items)

    await Marathons.cog_load(made)

    assert registered[-1] is cog_role.MarathonRoleButton
