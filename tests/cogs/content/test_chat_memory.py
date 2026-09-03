import pytest

from black_bloc.chat_memory import (
    Note,
    Profile,
    overridden,
    profile_for,
    remembers,
    save_profile,
    set_override,
)
from black_bloc.cogs.content.chat_memory import ChatMemory, profile_words
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore
from black_bloc.storage.db import Database

GUILD = 7
TEST_CHANNEL = 111
MEMBER = 900
AT = "2026-09-02T00:00:00+00:00"


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id
        self.name = f"role-{role_id}"


class FakePerms:
    def __init__(self, manage_guild=False, view_channel=False):
        self.manage_guild = manage_guild
        self.view_channel = view_channel


class FakeText:
    def __init__(self, channel_id):
        self.id = channel_id
        self.messages = []

    def permissions_for(self, role):
        return FakePerms()

    async def send(self, content=None, **kwargs):
        self.messages.append(content)


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black in a Flash!"
        self.roles = []
        self.channels = {TEST_CHANNEL: FakeText(TEST_CHANNEL)}
        self.members = []

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_member(self, user_id):
        return None


class FakeMember:
    def __init__(self, guild, user_id=MEMBER):
        self.id = user_id
        self.guild = guild
        self.name = "Ada"
        self.display_name = "Ada"
        self.mention = f"<@{user_id}>"
        self.roles = []
        self.guild_permissions = FakePerms()


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guild = guild
        self.guilds = [guild]
        self.guard = None

    def get_guild(self, guild_id):
        return self.guild if int(guild_id) == self.guild.id else None

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.done = False

    def is_done(self):
        return self.done

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.done = True
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeInteraction:
    def __init__(self, bot, user, *, guild=True):
        self.client = bot
        self.user = user
        self.guild = bot.guild if guild else None
        self.response = FakeResponse()

    @property
    def sent(self):
        said = [m["content"] for m in self.response.messages if m["content"] is not None]
        return said[-1] if said else None

    @property
    def ephemeral(self):
        return all(m["ephemeral"] for m in self.response.messages)


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "m.sqlite3")
    await database.connect()
    try:
        yield database
    finally:
        await database.close()


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(
        _env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL, dev_guild_id=GUILD
    )
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "chat_memory_mode", "on")
    return FakeBot(db, store, settings, FakeGuild())


@pytest.fixture
def cog(bot):
    return ChatMemory(bot)


@pytest.fixture
def member(bot):
    return FakeMember(bot.guild)


async def a_profile(db, *, notes=None, threads=None, call_me="Sky"):
    await save_profile(
        db,
        MEMBER,
        GUILD,
        Profile(
            call_me=call_me,
            notes=notes if notes is not None else (Note("likes short answers", "server", AT),),
            threads=(
                threads if threads is not None else (Note("was asking about it", "server", AT),)
            ),
            turns_seen=4,
            created_at=AT,
            updated_at=AT,
        ),
    )


async def action_kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


def test_the_words_a_person_reads_back_are_plain_and_marked_by_scope():
    lines = profile_words(
        Profile(
            call_me="Sky",
            notes=(Note("likes short answers", "server", AT), Note("prefers she/her", "dm", AT)),
            threads=(Note("was asking about the cookout", "server", AT),),
        )
    )
    said = "\n".join(lines)

    assert "Nobody else can read this" in said
    assert "calls you **Sky**" in said
    assert "likes short answers" in said
    assert "learned in a DM" in said
    assert "still open" in said
    assert "/memory forget-this" in said


async def test_show_reads_the_profile_back_and_only_to_that_person(cog, bot, member, db):
    await a_profile(db)
    interaction = FakeInteraction(bot, member)

    await cog.memory_show.callback(cog, interaction)

    assert "likes short answers" in interaction.sent
    assert interaction.ephemeral is True


async def test_show_says_so_when_there_is_nothing_written_down(cog, bot, member):
    interaction = FakeInteraction(bot, member)

    await cog.memory_show.callback(cog, interaction)

    assert "not written anything down about you yet" in interaction.sent


async def test_every_command_is_refused_in_words_while_memory_is_off(cog, bot, member, db):
    await bot.store.set(GUILD, "chat_memory_mode", "off")
    await a_profile(db)

    for call, args in (
        (cog.memory_show, ()),
        (cog.memory_forget, ()),
        (cog.memory_forget_this, ("emoji",)),
        (cog.memory_off, ()),
        (cog.memory_on, ()),
    ):
        interaction = FakeInteraction(bot, member)
        await call.callback(cog, interaction, *args)
        assert "not remembering anybody here" in interaction.sent
        assert "chat_memory_mode on" in interaction.sent

    assert await profile_for(db, MEMBER, GUILD) is not None


async def test_forget_clears_the_lot_and_logs_who_asked(cog, bot, member, db):
    await a_profile(db)
    interaction = FakeInteraction(bot, member)

    await cog.memory_forget.callback(cog, interaction)

    assert await profile_for(db, MEMBER, GUILD) is None
    assert "remembers nothing about you" in interaction.sent
    assert "chat.memory_forgot" in await action_kinds(db)


async def test_forget_with_nothing_to_forget_says_so(cog, bot, member, db):
    interaction = FakeInteraction(bot, member)

    await cog.memory_forget.callback(cog, interaction)

    assert "nothing was cleared" in interaction.sent
    assert "chat.memory_forgot" not in await action_kinds(db)


async def test_forget_this_drops_one_line_by_a_few_of_its_words(cog, bot, member, db):
    await a_profile(
        db,
        notes=(Note("likes short answers", "server", AT), Note("hates emoji", "server", AT)),
    )
    interaction = FakeInteraction(bot, member)

    await cog.memory_forget_this.callback(cog, interaction, "emoji")
    profile = await profile_for(db, MEMBER, GUILD)

    assert [one.text for one in profile.notes] == ["likes short answers"]
    assert "Dropped **1**" in interaction.sent


async def test_forget_this_that_matches_nothing_changes_nothing(cog, bot, member, db):
    await a_profile(db)
    interaction = FakeInteraction(bot, member)

    await cog.memory_forget_this.callback(cog, interaction, "nothing like this")
    profile = await profile_for(db, MEMBER, GUILD)

    assert len(profile.notes) == 1
    assert "matches" in interaction.sent


async def test_off_stops_the_writing_and_clears_what_there_was(cog, bot, member, db):
    await a_profile(db)
    interaction = FakeInteraction(bot, member)

    await cog.memory_off.callback(cog, interaction)

    assert await profile_for(db, MEMBER, GUILD) is None
    assert await remembers(db, MEMBER, GUILD, consent="optout") is False
    assert "will not write anything down" in interaction.sent
    assert "chat.memory_optout" in await action_kinds(db)


async def test_off_twice_says_nothing_changed(cog, bot, member, db):
    await set_override(db, MEMBER, GUILD)
    interaction = FakeInteraction(bot, member)

    await cog.memory_off.callback(cog, interaction)

    assert "already not remembering you" in interaction.sent


async def test_on_lets_it_start_again_and_says_what_it_will_keep(cog, bot, member, db):
    await set_override(db, MEMBER, GUILD)
    interaction = FakeInteraction(bot, member)

    await cog.memory_on.callback(cog, interaction)

    assert await remembers(db, MEMBER, GUILD, consent="optout") is True
    assert await overridden(db, MEMBER, GUILD) is False
    assert "never what you said" in interaction.sent
    assert "chat.memory_optin" in await action_kinds(db)


async def test_on_under_an_optin_server_writes_the_row_rather_than_removing_one(
    cog, bot, member, db
):
    await bot.store.set(GUILD, "chat_memory_consent", "optin")
    interaction = FakeInteraction(bot, member)

    await cog.memory_on.callback(cog, interaction)

    assert await overridden(db, MEMBER, GUILD) is True
    assert await remembers(db, MEMBER, GUILD, consent="optin") is True


async def test_show_says_so_to_somebody_who_has_turned_it_off(cog, bot, member, db):
    await set_override(db, MEMBER, GUILD)
    interaction = FakeInteraction(bot, member)

    await cog.memory_show.callback(cog, interaction)

    assert "not remembering you" in interaction.sent


async def test_a_dm_files_under_the_one_server_black_bloc_knows(cog, bot, member, db):
    await a_profile(db)
    interaction = FakeInteraction(bot, member, guild=False)

    await cog.memory_show.callback(cog, interaction)

    assert "likes short answers" in interaction.sent


async def test_a_dm_with_no_home_server_at_all_says_so(cog, bot, member, db, monkeypatch):
    monkeypatch.setattr(bot.settings, "dev_guild_id", None)
    interaction = FakeInteraction(bot, member, guild=False)

    await cog.memory_show.callback(cog, interaction)

    assert "not in one it knows" in interaction.sent


async def test_leaving_the_server_forgets_the_profile_at_once(cog, bot, member, db):
    await a_profile(db)

    await cog.on_member_remove(member)

    assert await profile_for(db, MEMBER, GUILD) is None
    assert "chat.memory_forgot" in await action_kinds(db)


async def test_a_leaver_with_nothing_written_down_logs_nothing(cog, bot, member, db):
    await cog.on_member_remove(member)

    assert await action_kinds(db) == []
