import discord
import pytest

from black_bloc import pings as helpers
from black_bloc.cogs.content.golive import set_link
from black_bloc.cogs.content.pings import Pings
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore
from black_bloc.storage.db import Database

GUILD = 7
LOG_CHANNEL = 222
STREAMER = 900
FAN = 901
STAFF = 5


class FakeRole:
    def __init__(self, role_id, name):
        self.id = role_id
        self.name = name
        self.members = []
        self.deleted = False

    def is_assignable(self):
        return True

    async def delete(self, reason=None):
        self.deleted = True


class FakeMember:
    def __init__(self, guild, user_id, display_name="Alice", staff=False):
        self.id = user_id
        self.guild = guild
        self.display_name = display_name
        self.name = display_name
        self.bot = False
        self.roles = []
        self.guild_permissions = discord.Permissions(manage_guild=staff)
        guild.members[user_id] = self

    async def add_roles(self, *roles, reason=None):
        self.roles += [role for role in roles if role not in self.roles]
        for role in roles:
            role.members.append(self)

    async def remove_roles(self, *roles, reason=None):
        self.roles = [role for role in self.roles if role not in roles]
        for role in roles:
            role.members = [one for one in role.members if one is not self]


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.roles = []
        self.members = {}
        self.made = []

    def get_role(self, role_id):
        return next((role for role in self.roles if role.id == int(role_id)), None)

    def get_member(self, user_id):
        return self.members.get(int(user_id))

    def get_channel(self, channel_id):
        return None

    def add_role(self, role):
        self.roles.append(role)
        return role

    async def create_role(self, name=None, mentionable=False, reason=None):
        self.made.append(name)
        return self.add_role(FakeRole(1000 + len(self.roles), name))


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guild = guild
        self.guilds = [guild]
        self.guard = None
        self.views = []

    def add_view(self, view, message_id=None):
        self.views.append((view, message_id))

    def get_channel(self, channel_id):
        return None

    def get_guild(self, guild_id):
        return self.guild if self.guild.id == guild_id else None


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.deferred = False

    def is_done(self):
        return self.deferred or bool(self.messages)

    async def defer(self, ephemeral=False):
        self.deferred = True

    async def send_message(self, content=None, **kwargs):
        self.messages.append({"content": content, "kwargs": kwargs})


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, **kwargs):
        self.response.messages.append({"content": content, "kwargs": kwargs})


class FakeInteraction:
    def __init__(self, bot, user, guild=None):
        self.client = bot
        self.user = user
        self.guild = guild
        self.guild_id = getattr(guild, "id", None)
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)

    @property
    def said(self):
        return self.response.messages[-1]["content"] if self.response.messages else None

    @property
    def kwargs(self):
        return self.response.messages[-1]["kwargs"] if self.response.messages else {}


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "pc.sqlite3")
    await database.connect()
    try:
        yield database
    finally:
        await database.close()


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=LOG_CHANNEL)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOG_CHANNEL)
    await store.set(GUILD, "pings_mode", "on")
    return FakeBot(db, store, settings, FakeGuild())


@pytest.fixture
def cog(bot):
    return Pings(bot)


@pytest.fixture
def streamer(bot):
    return FakeMember(bot.guild, STREAMER, "SuperNamu")


@pytest.fixture
def fan(bot):
    return FakeMember(bot.guild, FAN, "Fan")


@pytest.fixture
def lead(bot):
    return FakeMember(bot.guild, STAFF, "Lead", staff=True)


async def a_fan_role(cog, bot, streamer):
    outcome = await helpers.ensure_fan_role(bot, bot.guild, streamer, by=STAFF, staff=True)
    return bot.guild.get_role(outcome.role_id)


def quiet(interaction):
    """Every reply is ephemeral and pings nobody — the announcement is the only thing that does."""
    kwargs = interaction.kwargs
    return kwargs.get("ephemeral") is True and kwargs["allowed_mentions"].to_dict() == (
        discord.AllowedMentions.none().to_dict()
    )


async def test_follow_puts_the_role_on_and_says_what_happened(cog, bot, streamer, fan, db):
    role = await a_fan_role(cog, bot, streamer)
    interaction = FakeInteraction(bot, fan, bot.guild)

    await cog.follow.callback(cog, interaction, str(STREAMER))

    assert fan.roles == [role]
    assert "SuperNamu" in interaction.said and role.name in interaction.said
    assert quiet(interaction)
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    assert "pings.follow" in [row["kind"] for row in await cur.fetchall()]


async def test_following_twice_changes_nothing(cog, bot, streamer, fan):
    await a_fan_role(cog, bot, streamer)
    await cog.follow.callback(cog, FakeInteraction(bot, fan, bot.guild), str(STREAMER))
    interaction = FakeInteraction(bot, fan, bot.guild)

    await cog.follow.callback(cog, interaction, str(STREAMER))

    assert "already follow" in interaction.said and len(fan.roles) == 1


async def test_unfollow_takes_it_back_off_and_refuses_when_it_was_never_on(
    cog, bot, streamer, fan
):
    await a_fan_role(cog, bot, streamer)
    first = FakeInteraction(bot, fan, bot.guild)
    await cog.unfollow.callback(cog, first, str(STREAMER))
    assert "do not follow" in first.said

    await cog.follow.callback(cog, FakeInteraction(bot, fan, bot.guild), str(STREAMER))
    second = FakeInteraction(bot, fan, bot.guild)
    await cog.unfollow.callback(cog, second, str(STREAMER))

    assert fan.roles == [] and "no longer get" in second.said


async def test_follow_refuses_in_words_while_the_feature_is_off(cog, bot, streamer, fan):
    await a_fan_role(cog, bot, streamer)
    await bot.store.set(GUILD, "pings_mode", "off")
    interaction = FakeInteraction(bot, fan, bot.guild)

    await cog.follow.callback(cog, interaction, str(STREAMER))

    assert "turned off" in interaction.said and "pings_mode on" in interaction.said
    assert fan.roles == []


async def test_follow_with_nobody_to_follow_names_the_two_ways_to_start_one(cog, bot, fan):
    interaction = FakeInteraction(bot, fan, bot.guild)

    await cog.follow.callback(cog, interaction, "anybody")

    assert "/pings fans on" in interaction.said
    assert "/pingroles streamer add" in interaction.said


async def test_follow_of_a_name_nobody_has_says_to_pick_from_the_list(
    cog, bot, streamer, fan
):
    await a_fan_role(cog, bot, streamer)
    interaction = FakeInteraction(bot, fan, bot.guild)

    await cog.follow.callback(cog, interaction, "somebody else")

    assert "pick a name from the list" in interaction.said


async def test_a_display_name_works_as_well_as_the_id_the_picker_sends(
    cog, bot, streamer, fan
):
    role = await a_fan_role(cog, bot, streamer)
    interaction = FakeInteraction(bot, fan, bot.guild)

    await cog.follow.callback(cog, interaction, role.name)

    assert fan.roles == [role]


async def test_the_autocomplete_offers_the_streamers_that_have_a_role(
    cog, bot, streamer, fan
):
    await a_fan_role(cog, bot, streamer)
    interaction = FakeInteraction(bot, fan, bot.guild)

    everything = await cog.follow_names(interaction, "")
    narrowed = await cog.follow_names(interaction, "namu")
    nothing = await cog.follow_names(interaction, "zzz")

    assert [choice.value for choice in everything] == [str(STREAMER)]
    assert [choice.name for choice in narrowed] == ["SuperNamu pings"]
    assert nothing == []


async def test_events_on_needs_the_role_to_exist_first(cog, bot, fan):
    interaction = FakeInteraction(bot, fan, bot.guild)

    await cog.events_on.callback(cog, interaction)

    assert "/pingroles setup" in interaction.said and fan.roles == []


async def test_events_on_and_off_move_the_shared_role(cog, bot, fan, lead, db):
    await helpers.setup_events_role(bot, bot.guild, by=STAFF)
    role = bot.guild.get_role(bot.store.get(GUILD, "golive_ping_role_id"))

    on = FakeInteraction(bot, fan, bot.guild)
    await cog.events_on.callback(cog, on)
    assert fan.roles == [role] and role.name in on.said

    again = FakeInteraction(bot, fan, bot.guild)
    await cog.events_on.callback(cog, again)
    assert "already wear" in again.said

    off = FakeInteraction(bot, fan, bot.guild)
    await cog.events_off.callback(cog, off)
    assert fan.roles == []

    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    kinds = [row["kind"] for row in await cur.fetchall()]
    assert "pings.events_on" in kinds and "pings.events_off" in kinds


async def test_events_on_says_so_when_the_role_was_deleted_by_hand(cog, bot, fan):
    await helpers.setup_events_role(bot, bot.guild, by=STAFF)
    bot.guild.roles = []
    interaction = FakeInteraction(bot, fan, bot.guild)

    await cog.events_on.callback(cog, interaction)

    assert "not a role in this server any more" in interaction.said
    assert "/pingroles setup" in interaction.said


async def test_fans_on_refuses_somebody_black_bloc_has_never_seen_stream(cog, bot, fan):
    interaction = FakeInteraction(bot, fan, bot.guild)

    await cog.fans_on.callback(cog, interaction)

    assert "**Link my Twitch channel**" in interaction.said
    assert await helpers.get_fan_role(bot.db, GUILD, FAN) is None


async def test_fans_on_makes_a_role_for_a_linked_streamer(cog, bot, streamer, db):
    await set_link(db, STREAMER, "supernamu", None)
    interaction = FakeInteraction(bot, streamer, bot.guild)

    await cog.fans_on.callback(cog, interaction)

    assert bot.guild.made == ["SuperNamu pings"]
    assert await helpers.get_fan_role(db, GUILD, STREAMER) is not None
    assert quiet(interaction)


async def test_fans_on_is_refused_when_only_staff_may_start_one(cog, bot, streamer, db):
    await set_link(db, STREAMER, "supernamu", None)
    await bot.store.set(GUILD, "pings_fan_role_creation", "staff")
    interaction = FakeInteraction(bot, streamer, bot.guild)

    await cog.fans_on.callback(cog, interaction)

    assert "/pingroles streamer add" in interaction.said
    assert bot.guild.made == []


async def test_fans_off_takes_the_streamers_own_role_away(cog, bot, streamer, db):
    await set_link(db, STREAMER, "supernamu", None)
    await cog.fans_on.callback(cog, FakeInteraction(bot, streamer, bot.guild))
    interaction = FakeInteraction(bot, streamer, bot.guild)

    await cog.fans_off.callback(cog, interaction)

    assert await helpers.get_fan_role(db, GUILD, STREAMER) is None
    assert "is gone from the server" in interaction.said


async def test_fans_off_with_no_role_says_so(cog, bot, streamer):
    interaction = FakeInteraction(bot, streamer, bot.guild)

    await cog.fans_off.callback(cog, interaction)

    assert "no ping role" in interaction.said


async def test_pings_list_says_both_halves_even_when_there_is_nothing(cog, bot, fan):
    interaction = FakeInteraction(bot, fan, bot.guild)

    await cog.pings_list.callback(cog, interaction)

    assert "have not set up the Events role" in interaction.said
    assert "follow no streamers" in interaction.said
    assert quiet(interaction)


async def test_pings_list_names_what_the_caller_actually_wears(cog, bot, streamer, fan):
    await helpers.setup_events_role(bot, bot.guild, by=STAFF)
    await a_fan_role(cog, bot, streamer)
    await cog.events_on.callback(cog, FakeInteraction(bot, fan, bot.guild))
    await cog.follow.callback(cog, FakeInteraction(bot, fan, bot.guild), str(STREAMER))
    interaction = FakeInteraction(bot, fan, bot.guild)

    await cog.pings_list.callback(cog, interaction)

    assert "**on**" in interaction.said and "SuperNamu pings" in interaction.said


async def test_setup_is_staff_only_and_says_how_to_get_in(cog, bot, fan):
    interaction = FakeInteraction(bot, fan, bot.guild)

    await cog.setup_command.callback(cog, interaction, None)

    assert "staff only" in interaction.said and "Manage Server" in interaction.said
    assert bot.guild.made == []


async def test_setup_makes_the_events_role_for_staff(cog, bot, lead):
    interaction = FakeInteraction(bot, lead, bot.guild)

    await cog.setup_command.callback(cog, interaction, None)

    assert bot.guild.made == ["Events"]
    assert bot.store.get(GUILD, "golive_ping_role_id")
    assert bot.store.get(GUILD, "events_ping_role_id")
    assert quiet(interaction)


async def test_streamer_add_and_remove_are_staff_only(cog, bot, fan, streamer):
    add = FakeInteraction(bot, fan, bot.guild)
    await cog.streamer_add.callback(cog, add, streamer, None)
    assert "staff only" in add.said

    remove = FakeInteraction(bot, fan, bot.guild)
    await cog.streamer_remove.callback(cog, remove, streamer)
    assert "staff only" in remove.said


async def test_staff_can_start_a_role_for_somebody_who_never_linked(
    cog, bot, lead, streamer, db
):
    interaction = FakeInteraction(bot, lead, bot.guild)

    await cog.streamer_add.callback(cog, interaction, streamer, None)

    assert await helpers.get_fan_role(db, GUILD, STREAMER) is not None
    assert bot.guild.made == ["SuperNamu pings"]


async def test_staff_may_hand_an_existing_role_over_instead(cog, bot, lead, streamer, db):
    chosen = bot.guild.add_role(FakeRole(4242, "Namu Squad"))
    interaction = FakeInteraction(bot, lead, bot.guild)

    await cog.streamer_add.callback(cog, interaction, streamer, chosen)

    assert (await helpers.get_fan_role(db, GUILD, STREAMER))["role_id"] == 4242
    assert bot.guild.made == []


async def test_streamer_remove_takes_the_row_and_the_role(cog, bot, lead, streamer, db):
    role = await a_fan_role(cog, bot, streamer)
    interaction = FakeInteraction(bot, lead, bot.guild)

    await cog.streamer_remove.callback(cog, interaction, streamer)

    assert await helpers.get_fan_role(db, GUILD, STREAMER) is None
    assert role.deleted is True


async def test_streamer_list_counts_the_followers_and_names_a_role_that_went(
    cog, bot, lead, streamer, fan
):
    role = await a_fan_role(cog, bot, streamer)
    await cog.follow.callback(cog, FakeInteraction(bot, fan, bot.guild), str(STREAMER))
    interaction = FakeInteraction(bot, lead, bot.guild)

    await cog.streamer_list.callback(cog, interaction)
    assert "1 follower(s)" in interaction.said

    bot.guild.roles = [one for one in bot.guild.roles if one.id != role.id]
    gone = FakeInteraction(bot, lead, bot.guild)
    await cog.streamer_list.callback(cog, gone)

    assert "the role is gone from the server" in gone.said


async def test_streamer_list_with_nobody_on_it_says_how_to_start_one(cog, bot, lead):
    interaction = FakeInteraction(bot, lead, bot.guild)

    await cog.streamer_list.callback(cog, interaction)

    assert "/pingroles streamer add" in interaction.said
    assert "/pings fans on" in interaction.said


async def test_every_command_refuses_a_dm_in_words(cog, bot, fan):
    for call in (
        lambda one: cog.follow.callback(cog, one, "anybody"),
        lambda one: cog.pings_list.callback(cog, one),
        lambda one: cog.events_on.callback(cog, one),
        lambda one: cog.fans_on.callback(cog, one),
    ):
        interaction = FakeInteraction(bot, fan, None)
        await call(interaction)
        assert "has to be run in the server itself" in interaction.said
