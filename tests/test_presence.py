from types import SimpleNamespace

import discord
import pytest

from black_bloc.config import load_settings
from black_bloc.presence import (
    BIO_LIMIT,
    STATUS_LIMIT,
    bio_text,
    ensure_bio,
    human_count,
    status_guild,
    status_text,
    update_status,
)
from black_bloc.settings_store import BOT_BIO_TEMPLATE, STATUS_PREFIX, SettingsStore

GUILD = 7
OTHER_GUILD = 8
TEST_CHANNEL = 111


class FakeChannel:
    def __init__(self, channel_id):
        self.id = channel_id
        self.messages = []

    async def send(self, content=None, **kwargs):
        self.messages.append({"content": content, **kwargs})
        return self.messages[-1]


class FakeGuild:
    def __init__(self, guild_id=GUILD, member_count=12, bots=2):
        self.id = guild_id
        self.member_count = member_count
        self.members = [SimpleNamespace(id=n, bot=n < bots) for n in range(member_count)]
        self.channels = {TEST_CHANNEL: FakeChannel(TEST_CHANNEL)}

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)


class FakeApp:
    def __init__(self, description=""):
        self.description = description
        self.edits = []
        self.refuses = None

    async def edit(self, **kwargs):
        if self.refuses is not None:
            raise self.refuses
        self.edits.append(kwargs)
        self.description = kwargs.get("description", self.description)
        return self


class FakeBot:
    def __init__(self, db, store, guild, app):
        self.db = db
        self.store = store
        self.settings = store.settings
        self.guild = guild
        self.guilds = [guild] if guild is not None else []
        self.app = app
        self.presences = []
        self.info_calls = 0

    def get_guild(self, guild_id):
        if self.guild is not None and self.guild.id == guild_id:
            return self.guild
        return None

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id) if self.guild is not None else None

    async def application_info(self):
        self.info_calls += 1
        return self.app

    async def change_presence(self, *, activity=None, status=None):
        self.presences.append(activity)


def refusal(status=403):
    return discord.HTTPException(
        SimpleNamespace(status=status, reason="Forbidden"), "Missing Access"
    )


@pytest.fixture
async def store(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(
        _env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL, dev_guild_id=GUILD
    )
    made = SettingsStore(db, settings)
    await made.load()
    return made


@pytest.fixture
def app():
    return FakeApp()


@pytest.fixture
def bot(db, store, app):
    return FakeBot(db, store, FakeGuild(), app)


async def kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


def test_the_status_reads_as_the_owner_asked_for_it():
    assert status_text("Cookout attendees", 412) == "Cookout attendees: 412"
    assert status_text("  Cookout attendees  ", 0) == "Cookout attendees: 0"
    assert status_text(None, 3) == ": 3"


def test_a_long_prefix_or_bio_is_trimmed_rather_than_refused_by_discord():
    assert len(status_text("x" * 500, 1)) == STATUS_LIMIT
    assert len(bio_text("y" * 900)) == BIO_LIMIT
    assert bio_text("  spaced  ") == "spaced"
    assert bio_text(None) == ""


def test_the_head_count_leaves_the_bots_out():
    assert human_count(FakeGuild(member_count=12, bots=2)) == 10
    assert human_count(FakeGuild(member_count=1, bots=0)) == 1


def test_a_server_that_has_not_said_how_many_members_it_has_counts_as_unknown():
    assert human_count(SimpleNamespace(members=[])) is None
    assert human_count(SimpleNamespace(member_count=True, members=[])) is None
    assert human_count(None) is None


def test_the_dev_guild_is_counted_and_anything_else_is_the_fallback(bot):
    assert status_guild(bot) is bot.guild

    bot.guild.id = OTHER_GUILD
    assert status_guild(bot) is bot.guild

    bot.guild = None
    bot.guilds = []
    assert status_guild(bot) is None


def test_the_default_bio_carries_the_dashboard_link_the_owner_asked_for(store):
    assert store.default("bot_bio") == (
        "Black Bloc — moderation & content bot for Black in a Flash!. "
        "Staff dashboard: https://blackbloc.heygabi.ai"
    )
    assert store.default("bot_bio") == BOT_BIO_TEMPLATE.format(site=store.settings.origin)
    assert store.default("status_prefix") == STATUS_PREFIX


async def test_the_status_is_a_custom_activity_built_from_the_setting(bot):
    text = await update_status(bot)

    assert text == "Cookout attendees: 10"
    assert isinstance(bot.presences[-1], discord.CustomActivity)
    assert bot.presences[-1].name == "Cookout attendees: 10"


async def test_the_prefix_is_a_setting_a_lead_can_change(bot):
    await bot.store.set(GUILD, "status_prefix", "Regulators")

    assert await update_status(bot) == "Regulators: 10"


async def test_nothing_is_set_when_there_is_no_server_or_no_count_yet(bot):
    bot.guild.member_count = None
    assert await update_status(bot) is None

    bot.guild = None
    bot.guilds = []
    assert await update_status(bot) is None
    assert bot.presences == []


async def test_the_bio_is_written_once_and_recorded_in_the_action_log(bot, app):
    assert await ensure_bio(bot) is True

    assert app.edits == [{"description": bot.store.get(GUILD, "bot_bio")}]
    assert await kinds(bot.db) == ["presence.bio_set"]
    assert bot.guild.get_channel(TEST_CHANNEL).messages == []


async def test_the_bio_line_reaches_discord_when_core_logging_is_turned_up(bot, app):
    """`presence.bio_set` is routine, so `core_log_level` is what decides."""
    await bot.store.set(GUILD, "core_log_level", "all")

    assert await ensure_bio(bot) is True

    assert await kinds(bot.db) == ["presence.bio_set"]
    assert bot.guild.get_channel(TEST_CHANNEL).messages


async def test_a_bio_that_already_matches_is_left_alone(bot, app):
    app.description = bot.store.get(GUILD, "bot_bio")

    assert await ensure_bio(bot) is False
    assert app.edits == []
    assert await kinds(bot.db) == []


async def test_a_bio_discord_refuses_is_a_warning_and_never_a_raise(bot, app, caplog):
    app.refuses = refusal()

    with caplog.at_level("WARNING"):
        assert await ensure_bio(bot) is False

    assert "would not take the About Me" in caplog.text
    assert await kinds(bot.db) == []


async def test_an_empty_bio_setting_does_not_wipe_the_profile(bot, app):
    await bot.store.set(GUILD, "bot_bio", "   x   ")
    await bot.db.conn.execute(
        "UPDATE settings SET value = ? WHERE guild_id = ? AND key = ?", ('"   "', GUILD, "bot_bio")
    )
    await bot.store.load()

    assert await ensure_bio(bot) is False
    assert app.edits == []
