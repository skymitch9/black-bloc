import asyncio
from datetime import UTC, datetime, timedelta

import discord
import pytest

from black_bloc.cogs.community.tempvoice import (
    RECONCILE_GRACE_SECONDS,
    RECONCILE_MINUTES,
    RENAMED_TOO_OFTEN,
    RenameModal,
    TempVoice,
    TempVoicePanel,
    add_channel,
    bottom_position,
    category_overwrites,
    channel_name,
    clamp_bitrate,
    creator_overwrites,
    creator_position,
    delete_row,
    do_ban,
    do_forget_member,
    do_kick,
    do_privacy,
    do_rename,
    do_transfer,
    get_prefs,
    get_row,
    get_row_by_panel,
    guild_bitrate_ceiling,
    is_panel_owner,
    is_stale,
    lobbies_by_name,
    may_use_voice,
    member_lists,
    not_owner_message,
    owner_overwrites,
    panel_context,
    panel_home,
    panel_id,
    parse_limit,
    pick_row,
    region_choices,
    rows_for_guild,
    save_prefs,
    set_owner,
    set_panel_message,
    spawn_position,
)
from black_bloc.config import load_settings
from black_bloc.settings_store import (
    MEMBER_ROLE_ID,
    TEMPVOICE_CREATOR_NAME,
    SettingsStore,
)
from black_bloc.storage.db import Database

GUILD = 7
TEST_CHANNEL = 111
LOG_CHANNEL = 222
CREATOR = 333
USER = 900


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id
        self.name = f"role-{role_id}"


class FakeCategory:
    def __init__(self, category_id, voice_channels=(), overwrites=None):
        self.id = category_id
        self.name = f"category-{category_id}"
        self.voice_channels = list(voice_channels)
        self.overwrites = dict(overwrites or {})


class FakeMessage:
    def __init__(self, message_id, content, **kwargs):
        self.id = message_id
        self.content = content
        self.kwargs = kwargs


class _Response:
    def __init__(self, status):
        self.status = status
        self.reason = "refused"


def refused():
    return discord.HTTPException(_Response(403), "no")


def too_fast():
    return discord.HTTPException(_Response(429), "slow down")


class FakePerms:
    def __init__(self, manage_guild=False, view_channel=False):
        self.manage_guild = manage_guild
        self.view_channel = view_channel


class FakeText:
    def __init__(self, channel_id, category=None):
        self.id = channel_id
        self.category = category
        self.category_id = category.id if category else None
        self.overwrites = {}
        self.visible_to = set()
        self.messages = []

    def permissions_for(self, role):
        return FakePerms(view_channel=role.id in self.visible_to)

    async def send(self, content=None, **kwargs):
        message = FakeMessage(len(self.messages) + 1, content or "", **kwargs)
        self.messages.append(message)
        return message


class FakeVoice:
    def __init__(self, channel_id, guild, category=None, position=0, members=(), name="voice"):
        self.id = channel_id
        self.guild = guild
        self.name = name
        self.mention = f"<#{channel_id}>"
        self.category = category
        self.category_id = category.id if category else None
        self.position = position
        self.members = list(members)
        self.user_limit = 0
        self.bitrate = 0
        self.rtc_region = None
        self.deleted = False
        self.edits = []
        self.permissions = []
        self.messages = []
        self.overwrites = {}
        self.send_raises = None
        self.edit_raises = None

    async def delete(self, reason=None):
        self.deleted = True
        self.guild.channels.pop(self.id, None)

    async def edit(self, **kwargs):
        if self.edit_raises is not None:
            raise self.edit_raises
        self.edits.append(kwargs)
        if "name" in kwargs:
            self.name = kwargs["name"]
        if "overwrites" in kwargs:
            self.overwrites = dict(kwargs["overwrites"])
        for key in ("user_limit", "bitrate", "rtc_region"):
            if key in kwargs:
                setattr(self, key, kwargs[key])

    async def send(self, content=None, **kwargs):
        if self.send_raises is not None:
            raise self.send_raises
        message = FakeMessage(len(self.messages) + 1, content or "", **kwargs)
        self.messages.append(message)
        return message

    @property
    def voice_states(self):
        return {m.id: None for m in self.members}

    def overwrites_for(self, target):
        return self.overwrites.setdefault(target, discord.PermissionOverwrite())

    async def set_permissions(self, target, overwrite=None, reason=None, **perms):
        self.permissions.append((target, overwrite, perms))


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.channels = {}
        self.members = {}
        self.default_role = FakeRole(GUILD)
        self.roles = []
        self.afk_channel = None
        self.created = []
        self.me = FakeRole(2)
        self._next_id = 1000

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_member(self, user_id):
        return self.members.get(user_id)

    def get_role(self, role_id):
        return next((role for role in self.roles if role.id == role_id), None)

    @property
    def voice_channels(self):
        return [c for c in self.channels.values() if isinstance(c, FakeVoice)]

    def add(self, channel):
        channel.guild = self
        self.channels[channel.id] = channel
        return channel

    async def create_voice_channel(
        self,
        name,
        *,
        category=None,
        position=0,
        overwrites=None,
        user_limit=0,
        bitrate=None,
        reason=None,
    ):
        self._next_id += 1
        channel = FakeVoice(self._next_id, self, category, position, name=name)
        channel.user_limit = user_limit
        channel.bitrate = bitrate or 0
        channel.given_overwrites = overwrites
        self.add(channel)
        self.created.append(channel)
        return channel


class FakeMember:
    def __init__(
        self,
        guild,
        user_id=USER,
        display_name="Alice",
        roles=(MEMBER_ROLE_ID,),
        manage_guild=False,
    ):
        self.id = user_id
        self.guild = guild
        self.display_name = display_name
        self.name = display_name
        self.bot = False
        self.mention = f"<@{user_id}>"
        self.roles = [FakeRole(r) for r in roles]
        self.guild_permissions = FakePerms(manage_guild=manage_guild)
        self.moves = []
        self.dms = []
        self.voice = None
        guild.members[user_id] = self

    async def move_to(self, channel, reason=None):
        self.moves.append(channel)
        if channel is not None and isinstance(channel, FakeVoice):
            channel.members.append(self)

    async def send(self, content=None, **kwargs):
        self.dms.append(content)


class FakeGuard:
    def __init__(self, test_channel_id=TEST_CHANNEL):
        self.test_channel_id = test_channel_id

    def allows_channel(self, channel_id):
        return channel_id == self.test_channel_id

    def refusal_message(self):
        return "test mode"


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guard = None
        self.guilds = [guild]
        self.guild = guild
        self.views = []

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def add_view(self, view, **kwargs):
        self.views.append(view)

    async def wait_until_ready(self):
        return None


class FakeState:
    def __init__(self, channel=None):
        self.channel = channel


def connect(member, channel):
    """Put a fake member in a fake voice channel, the way Discord would report it."""
    member.voice = FakeState(channel)
    if member not in channel.members:
        channel.members.append(member)
    return member


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.modals = []
        self.done = False

    def is_done(self):
        return self.done

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.done = True
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def send_modal(self, modal):
        self.done = True
        self.modals.append(modal)

    async def defer(self, ephemeral=False):
        self.done = True
        self.messages.append({"content": None, "deferred": True})


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.response.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeInteraction:
    def __init__(self, bot, user, channel=None, message=None):
        self.client = bot
        self.user = user
        self.guild = bot.guild
        self.guild_id = bot.guild.id
        self.channel = channel
        self.channel_id = channel.id if channel is not None else TEST_CHANNEL
        self.message = message
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)

    @property
    def sent(self):
        said = [m["content"] for m in self.response.messages if m["content"] is not None]
        return said[-1] if said else None


async def action_kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "v.sqlite3")
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
    await store.set(GUILD, "tempvoice_creator_ids", [CREATOR])
    guild = FakeGuild()
    guild.add(FakeText(LOG_CHANNEL))
    return FakeBot(db, store, settings, guild)


@pytest.fixture
def cog(bot):
    return TempVoice(bot)


@pytest.fixture
def creator(bot):
    return bot.guild.add(FakeVoice(CREATOR, bot.guild, position=4, name=TEMPVOICE_CREATOR_NAME))


@pytest.fixture
def member(bot):
    return FakeMember(bot.guild)


@pytest.fixture
def lead(bot):
    return FakeMember(bot.guild, user_id=1, display_name="Lead", manage_guild=True)


def test_channel_name_uses_the_template_then_the_remembered_name():
    assert channel_name("{user}'s bloc", "Alice") == "Alice's bloc"
    assert channel_name("{user}'s bloc", "Alice", "The Pit") == "The Pit"
    assert channel_name("{user}'s bloc", "Alice", "   ") == "Alice's bloc"


def test_a_broken_name_template_falls_back_instead_of_raising():
    assert channel_name("{nope}'s bloc", "Alice") == "Alice's bloc"
    assert channel_name("{", "Alice") == "Alice's bloc"


def test_channel_names_are_cut_to_discord_s_limit():
    assert len(channel_name("{user}", "A" * 200)) == 100


def test_the_creator_channel_goes_directly_above_the_afk_channel():
    assert creator_position(6, 99) == 6
    assert creator_position(None, 12) == 12
    assert creator_position(-3, 0) == 0


def test_a_spawned_channel_sits_just_under_the_creator():
    assert spawn_position(4) == 5
    assert spawn_position(0) == 1


def test_bottom_position_is_one_past_the_lowest_channel():
    assert bottom_position([0, 3, 2]) == 4
    assert bottom_position([]) == 0


def test_limits_are_zero_to_ninety_nine():
    assert parse_limit(" 5 ") == 5
    assert parse_limit("0") == 0
    assert parse_limit("99") == 99
    assert parse_limit("100") is None
    assert parse_limit("-1") is None
    assert parse_limit("lots") is None


def test_only_the_owner_may_use_the_panel():
    assert is_panel_owner(5, 5) is True
    assert is_panel_owner(5, 6) is False
    assert "<@5>" in not_owner_message(5)


def test_stale_only_after_the_grace_and_unreadable_counts_as_old():
    now = datetime.now(UTC)
    fresh = (now - timedelta(seconds=5)).isoformat()
    old = (now - timedelta(seconds=RECONCILE_GRACE_SECONDS + 5)).isoformat()
    assert is_stale(fresh, now, RECONCILE_GRACE_SECONDS) is False
    assert is_stale(old, now, RECONCILE_GRACE_SECONDS) is True
    assert is_stale("who knows", now, RECONCILE_GRACE_SECONDS) is True
    assert is_stale(None, now, RECONCILE_GRACE_SECONDS) is True


def test_the_owner_gets_the_channel_controls():
    guild = FakeGuild()
    member = FakeMember(guild)
    overwrites = owner_overwrites(guild, member, locked=True, hidden=True)
    assert overwrites[member].manage_channels is True
    assert overwrites[member].move_members is True
    assert overwrites[guild.default_role].connect is False
    assert overwrites[guild.default_role].view_channel is False


def test_an_unlocked_channel_leaves_everyone_alone():
    guild = FakeGuild()
    member = FakeMember(guild)
    everyone = owner_overwrites(guild, member)[guild.default_role]
    assert everyone.connect is None and everyone.view_channel is None


def test_the_panel_is_persistent_and_keyed_by_action():
    view = TempVoicePanel()
    ids = [item.custom_id for item in view.children]
    assert view.timeout is None and view.is_persistent()
    assert ids == [
        panel_id(name)
        for name in ("rename", "limit", "lock", "hide", "kick", "ban", "unban", "permit",
                     "unpermit", "transfer", "claim")
    ]


async def test_prefs_remember_one_field_at_a_time(db):
    assert await get_prefs(db, USER) is None
    await save_prefs(db, USER, name="The Pit")
    await save_prefs(db, USER, user_limit=4)
    await save_prefs(db, USER, locked=True)
    row = await get_prefs(db, USER)
    assert row["name"] == "The Pit" and row["user_limit"] == 4
    assert row["locked"] == 1 and row["hidden"] == 0
    await save_prefs(db, USER, locked=False)
    assert (await get_prefs(db, USER))["locked"] == 0
    assert (await get_prefs(db, USER))["name"] == "The Pit"


async def test_channel_rows_round_trip(db):
    await add_channel(db, 5, GUILD, USER, CREATOR)
    row = await get_row(db, 5)
    assert row["owner_id"] == USER and row["creator_id"] == CREATOR
    await set_panel_message(db, 5, 77)
    await set_owner(db, 5, USER + 1)
    row = await get_row(db, 5)
    assert row["panel_message_id"] == 77 and row["owner_id"] == USER + 1
    assert [r["channel_id"] for r in await rows_for_guild(db, GUILD)] == [5]
    assert await delete_row(db, 5) is True
    assert await delete_row(db, 5) is False


async def test_joining_the_creator_makes_a_channel_and_moves_the_member(cog, bot, creator, member,
                                                                       db):
    await cog._maybe_create(member, creator)

    made = bot.guild.created[0]
    assert made.name == "Alice's bloc"
    assert made.position == 5 and made.category is creator.category
    assert member.moves == [made]
    row = await get_row(db, made.id)
    assert row["owner_id"] == member.id and row["creator_id"] == CREATOR
    assert "tempvoice.create" in await action_kinds(db)


async def test_a_remembered_name_and_limit_are_used_for_the_next_channel(cog, bot, creator, member,
                                                                        db):
    await save_prefs(db, member.id, name="The Pit", user_limit=3, locked=True)

    await cog._maybe_create(member, creator)

    made = bot.guild.created[0]
    assert made.name == "The Pit" and made.user_limit == 3
    assert made.given_overwrites[bot.guild.default_role].connect is False


async def test_a_member_without_the_allowed_role_is_turned_away(cog, bot, creator, db):
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo", roles=())
    bot.guild.afk_channel = bot.guild.add(FakeVoice(444, bot.guild, name="You Still Here?"))

    await cog._maybe_create(stranger, creator)

    assert bot.guild.created == []
    assert stranger.moves == [bot.guild.afk_channel]
    assert f"<@&{MEMBER_ROLE_ID}>" in stranger.dms[0]
    assert "tempvoice.turned_away" in await action_kinds(db)


async def test_mode_off_makes_nothing(cog, bot, creator, member, db):
    await bot.store.set(GUILD, "tempvoice_mode", "off")

    await cog._maybe_create(member, creator)

    assert bot.guild.created == [] and await action_kinds(db) == []


async def test_a_channel_that_is_not_a_creator_is_ignored(cog, bot, member, db):
    other = bot.guild.add(FakeVoice(999, bot.guild))

    await cog._maybe_create(member, other)

    assert bot.guild.created == [] and await action_kinds(db) == []


async def test_test_mode_only_acts_in_the_test_channel_s_category(cog, bot, member):
    category = FakeCategory(50)
    bot.guild.add(FakeText(TEST_CHANNEL, category=category))
    bot.guard = FakeGuard()
    inside = bot.guild.add(FakeVoice(CREATOR, bot.guild, category=category, position=1))
    outside = bot.guild.add(FakeVoice(CREATOR + 1, bot.guild, category=FakeCategory(51)))
    await bot.store.set(GUILD, "tempvoice_creator_ids", [inside.id, outside.id])

    await cog._maybe_create(member, outside)
    assert bot.guild.created == []

    await cog._maybe_create(member, inside)
    assert len(bot.guild.created) == 1


async def test_in_test_mode_the_panel_goes_to_the_test_channel_and_names_the_voice_channel(
    cog, bot, member, db
):
    category = FakeCategory(50)
    test_channel = bot.guild.add(FakeText(TEST_CHANNEL, category=category))
    bot.guard = FakeGuard()
    creator = bot.guild.add(FakeVoice(CREATOR, bot.guild, category=category, position=1))

    await cog._maybe_create(member, creator)

    made = bot.guild.created[0]
    assert made.messages == []
    assert len(test_channel.messages) == 1
    assert test_channel.messages[0].content.startswith(f"Controls for <#{made.id}>")
    assert test_channel.messages[0].kwargs["allowed_mentions"].everyone is False
    row = await get_row(db, made.id)
    assert row["panel_message_id"] == test_channel.messages[0].id
    assert row["panel_channel_id"] == TEST_CHANNEL
    assert "tempvoice.panel_elsewhere" in await action_kinds(db)


async def test_a_panel_with_nowhere_to_go_is_logged_as_a_failure(cog, bot, member, db):
    category = FakeCategory(50)
    bot.guard = FakeGuard(test_channel_id=None)
    creator = bot.guild.add(FakeVoice(CREATOR, bot.guild, category=category, position=1))
    cog._may_act_in = lambda channel: True

    await cog._maybe_create(member, creator)

    made = bot.guild.created[0]
    assert made.messages == []
    assert "tempvoice.panel_failed" in await action_kinds(db)
    assert (await get_row(db, made.id))["panel_message_id"] is None


def test_the_panel_lives_in_the_voice_chat_unless_the_guard_would_refuse_it(bot):
    voice = bot.guild.add(FakeVoice(4321, bot.guild))
    test_channel = bot.guild.add(FakeText(TEST_CHANNEL))

    assert panel_home(bot, voice) is voice

    bot.guard = FakeGuard()
    assert panel_home(bot, voice) is test_channel
    assert panel_home(bot, test_channel) is test_channel

    bot.guard = FakeGuard(test_channel_id=None)
    assert panel_home(bot, voice) is None


async def test_a_click_in_the_test_channel_finds_the_voice_channel_the_panel_names(
    cog, bot, member, db
):
    category = FakeCategory(50)
    test_channel = bot.guild.add(FakeText(TEST_CHANNEL, category=category))
    bot.guard = FakeGuard()
    creator = bot.guild.add(FakeVoice(CREATOR, bot.guild, category=category, position=1))
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    posted = test_channel.messages[0]

    found = await panel_context(
        FakeInteraction(bot, member, channel=test_channel, message=posted)
    )

    assert found.channel is made and found.row["channel_id"] == made.id
    assert (await get_row_by_panel(db, posted.id))["channel_id"] == made.id


async def test_a_click_in_the_test_channel_with_no_panel_row_says_so(cog, bot, member, db):
    test_channel = bot.guild.add(FakeText(TEST_CHANNEL))
    bot.guard = FakeGuard()
    interaction = FakeInteraction(
        bot, member, channel=test_channel, message=FakeMessage(999, "stale")
    )

    assert await panel_context(interaction) is None
    assert "not attached" in interaction.sent


async def test_the_panel_is_posted_and_recorded_when_the_guard_is_off(cog, bot, creator, member,
                                                                     db):
    await cog._maybe_create(member, creator)

    made = bot.guild.created[0]
    assert len(made.messages) == 1
    assert made.messages[0].kwargs["allowed_mentions"].everyone is False
    assert (await get_row(db, made.id))["panel_message_id"] == made.messages[0].id


async def test_a_panel_that_cannot_be_posted_does_not_undo_the_channel(cog, bot, creator, member,
                                                                      db):
    async def raising_create(*args, **kwargs):
        channel = await FakeGuild.create_voice_channel(bot.guild, *args, **kwargs)
        channel.send_raises = refused()
        return channel

    bot.guild.create_voice_channel = raising_create

    await cog._maybe_create(member, creator)

    made = bot.guild.created[0]
    assert await get_row(db, made.id) is not None
    kinds = await action_kinds(db)
    assert "tempvoice.create" in kinds and "tempvoice.panel_failed" in kinds


async def test_the_last_member_leaving_deletes_the_channel(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    made.members.clear()

    await cog._maybe_delete(bot.guild, made)

    assert made.deleted is True
    assert await get_row(db, made.id) is None
    assert "tempvoice.delete" in await action_kinds(db)


async def test_a_channel_someone_is_still_in_is_kept(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]

    await cog._maybe_delete(bot.guild, made)

    assert made.deleted is False and await get_row(db, made.id) is not None


async def test_two_leaves_at_once_delete_the_channel_once(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    made.members.clear()
    deletes = []
    original = made.delete

    async def counting_delete(reason=None):
        deletes.append(reason)
        await original(reason)

    made.delete = counting_delete

    await asyncio.gather(
        cog._maybe_delete(bot.guild, made), cog._maybe_delete(bot.guild, made)
    )

    assert len(deletes) == 1
    assert (await action_kinds(db)).count("tempvoice.delete") == 1


async def test_a_delete_discord_refuses_keeps_the_row_for_next_time(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    made.members.clear()

    async def refusing_delete(reason=None):
        raise refused()

    made.delete = refusing_delete

    await cog._maybe_delete(bot.guild, made)

    assert await get_row(db, made.id) is not None
    assert "tempvoice.delete_failed" in await action_kinds(db)


async def test_reconcile_forgets_channels_that_are_gone(cog, bot, db):
    await add_channel(db, 4242, GUILD, USER, CREATOR)

    await cog.reconcile_channels()

    assert await get_row(db, 4242) is None


async def test_reconcile_deletes_empty_channels_but_not_fresh_or_busy_ones(cog, bot, member, db):
    empty = bot.guild.add(FakeVoice(10, bot.guild))
    fresh = bot.guild.add(FakeVoice(11, bot.guild))
    busy = bot.guild.add(FakeVoice(12, bot.guild, members=[member]))
    for channel in (empty, fresh, busy):
        await add_channel(db, channel.id, GUILD, USER, CREATOR)
    old = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    for channel_id in (empty.id, busy.id):
        await db.conn.execute(
            "UPDATE tempvoice_channels SET created_at = ? WHERE channel_id = ?", (old, channel_id)
        )
    await db.conn.commit()

    await cog.reconcile_channels()

    assert empty.deleted is True and await get_row(db, empty.id) is None
    assert fresh.deleted is False and await get_row(db, fresh.id) is not None
    assert busy.deleted is False and await get_row(db, busy.id) is not None


async def test_setup_puts_the_creator_in_the_test_category_while_test_mode_is_on(cog, bot, lead):
    category = FakeCategory(50, voice_channels=[FakeVoice(60, bot.guild, position=2)])
    bot.guild.add(FakeText(TEST_CHANNEL, category=category))
    bot.guard = FakeGuard()
    interaction = FakeInteraction(bot, lead)

    await cog.setup_channel.callback(cog, interaction, None)

    made = bot.guild.created[0]
    assert made.name == TEMPVOICE_CREATOR_NAME == "join to create a channel"
    assert made.category is category and made.position == 3
    assert bot.store.get(GUILD, "tempvoice_creator_ids") == [CREATOR, made.id]
    assert "test mode is off" in interaction.sent.lower()


async def test_setup_refuses_someone_who_is_not_staff(cog, bot, member):
    interaction = FakeInteraction(bot, member)

    await cog.setup_channel.callback(cog, interaction, None)

    assert bot.guild.created == []
    assert "staff only" in interaction.sent


async def test_setup_refuses_when_test_mode_cannot_see_its_channel(cog, bot, lead):
    bot.guard = FakeGuard()
    interaction = FakeInteraction(bot, lead)

    await cog.setup_channel.callback(cog, interaction, None)

    assert bot.guild.created == []
    assert "test mode" in interaction.sent.lower()


async def test_the_creator_spot_is_above_the_afk_channel_when_the_guard_is_off(cog, bot):
    category = FakeCategory(50)
    afk = bot.guild.add(
        FakeVoice(70, bot.guild, category=category, position=9, name="You Still Here?")
    )
    bot.guild.afk_channel = afk

    assert cog._creator_spot(bot.guild) == (category, 9, "above_afk")


async def test_the_creator_spot_falls_back_to_the_named_afk_channel(cog, bot):
    bot.guild.add(FakeVoice(70, bot.guild, position=9, name="You Still Here?"))

    assert cog._creator_spot(bot.guild) == (None, 9, "above_afk")


async def test_the_creator_spot_falls_back_to_the_bottom(cog, bot):
    bot.guild.add(FakeVoice(70, bot.guild, position=3, name="General"))

    assert cog._creator_spot(bot.guild) == (None, 4, "bottom")


async def test_the_panel_answers_a_click_from_someone_who_does_not_own_the_channel(
    cog, bot, creator, member, db
):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    interaction = FakeInteraction(bot, stranger, channel=made)

    assert await panel_context(interaction) is None
    assert f"<@{member.id}>" in interaction.sent
    assert interaction.response.messages[-1]["allowed_mentions"].users is False


async def test_the_panel_refuses_every_click_while_test_mode_is_on(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    bot.guard = FakeGuard()
    interaction = FakeInteraction(bot, member, channel=made)

    assert await panel_context(interaction) is None
    assert interaction.sent == "test mode"


async def test_a_panel_on_a_channel_black_bloc_forgot_says_so(cog, bot, member):
    orphan = bot.guild.add(FakeVoice(4243, bot.guild))
    interaction = FakeInteraction(bot, member, channel=orphan)

    assert await panel_context(interaction) is None
    assert "not attached" in interaction.sent


async def test_lock_and_unlock_toggle_the_everyone_overwrite_and_are_remembered(
    cog, bot, creator, member, db
):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    panel = TempVoicePanel()

    await panel._toggle(FakeInteraction(bot, member, channel=made), "connect")
    assert made.permissions[-1][1].connect is False
    assert (await get_prefs(db, member.id))["locked"] == 1

    await panel._toggle(FakeInteraction(bot, member, channel=made), "connect")
    assert made.permissions[-1][1].connect is None
    assert (await get_prefs(db, member.id))["locked"] == 0
    kinds = await action_kinds(db)
    assert "tempvoice.lock" in kinds and "tempvoice.unlock" in kinds


async def test_hide_and_show_toggle_view_channel(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]

    await TempVoicePanel()._toggle(FakeInteraction(bot, member, channel=made), "view_channel")

    assert made.permissions[-1][1].view_channel is False
    assert (await get_prefs(db, member.id))["hidden"] == 1
    assert "tempvoice.hide" in await action_kinds(db)


async def test_asking_for_a_state_the_channel_is_already_in_changes_nothing(
    cog, bot, creator, member, db
):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    row = await get_row(db, made.id)
    interaction = FakeInteraction(bot, member, channel=made)

    said = await do_privacy(interaction, made, row, "connect", False)

    assert made.permissions == []
    assert said == "This channel is already unlocked, so nothing was changed."
    assert "tempvoice.unlock" not in await action_kinds(db)


async def test_lock_and_unlock_can_be_asked_for_by_name(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    row = await get_row(db, made.id)

    await do_privacy(FakeInteraction(bot, member, channel=made), made, row, "connect", True)
    assert made.permissions[-1][1].connect is False

    await do_privacy(FakeInteraction(bot, member, channel=made), made, row, "connect", False)
    assert made.permissions[-1][1].connect is None
    assert (await get_prefs(db, member.id))["locked"] == 0


async def test_kicking_someone_who_is_not_here_changes_nothing(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    interaction = FakeInteraction(bot, member, channel=made)

    said = await do_kick(interaction, made, await get_row(db, made.id), stranger)

    assert stranger.moves == []
    assert "not in this channel" in said


async def test_banning_someone_denies_connect_and_moves_them_out(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    made.members.append(stranger)
    interaction = FakeInteraction(bot, member, channel=made)

    await do_ban(interaction, made, await get_row(db, made.id), stranger)

    assert made.permissions[-1][2] == {"connect": False, "view_channel": False}
    assert stranger.moves == [None]
    assert "tempvoice.ban" in await action_kinds(db)


async def test_claiming_is_refused_while_the_owner_is_still_in_the_channel(
    cog, bot, creator, member, db
):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    made.members.append(stranger)
    interaction = FakeInteraction(bot, stranger, channel=made)

    await TempVoicePanel().claim.callback(interaction)

    assert (await get_row(db, made.id))["owner_id"] == member.id
    assert "still belongs to" in interaction.sent


async def test_claiming_an_abandoned_channel_hands_it_over(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    made.members.clear()
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    made.members.append(stranger)
    interaction = FakeInteraction(bot, stranger, channel=made)

    await TempVoicePanel().claim.callback(interaction)

    assert (await get_row(db, made.id))["owner_id"] == stranger.id
    assert made.permissions[-1][0] is stranger
    assert "tempvoice.claim" in await action_kinds(db)


async def test_the_panel_logs_the_action_before_it_answers(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    interaction = FakeInteraction(bot, member, channel=made)
    when_answered = []

    async def watching_followup(content=None, ephemeral=False, **kwargs):
        when_answered.append(await action_kinds(db))

    interaction.followup.send = watching_followup

    await TempVoicePanel()._toggle(interaction, "connect")

    assert when_answered and "tempvoice.lock" in when_answered[0]


async def test_the_rename_defers_before_it_edits_the_channel(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    modal = RenameModal()
    modal.name._value = "The Pit"
    interaction = FakeInteraction(bot, member, channel=made)

    await modal.on_submit(interaction)

    assert interaction.response.messages[0].get("deferred") is True
    assert made.edits == [{"name": "The Pit", "reason": "Black Bloc temp voice"}]
    assert "tempvoice.rename" in await action_kinds(db)


async def test_two_people_claiming_at_once_leaves_one_of_them_told_they_lost(
    cog, bot, creator, member, db
):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    made.members.clear()
    first = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    second = FakeMember(bot.guild, user_id=USER + 2, display_name="Cass")
    made.members += [first, second]
    one = FakeInteraction(bot, first, channel=made)
    two = FakeInteraction(bot, second, channel=made)

    await asyncio.gather(
        TempVoicePanel().claim.callback(one), TempVoicePanel().claim.callback(two)
    )

    said = [one.sent, two.sent]
    assert "This channel is yours now." in said
    assert any("Someone else just claimed" in text for text in said)
    assert (await action_kinds(db)).count("tempvoice.claim") == 1


async def test_claiming_needs_the_clicker_to_be_in_the_channel(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    made.members.clear()
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    interaction = FakeInteraction(bot, stranger, channel=made)

    await TempVoicePanel().claim.callback(interaction)

    assert (await get_row(db, made.id))["owner_id"] == member.id
    assert "connected to this channel" in interaction.sent


async def test_transferring_a_channel_someone_else_already_took_says_so(
    cog, bot, creator, member, db
):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    row = await get_row(db, made.id)
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    await set_owner(db, made.id, stranger.id)
    interaction = FakeInteraction(bot, member, channel=made)

    said = await do_transfer(interaction, made, row, stranger)

    assert "Someone else just claimed" in said
    assert "tempvoice.transfer" not in await action_kinds(db)


async def test_a_banned_member_loses_sight_of_the_channel_too(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    interaction = FakeInteraction(bot, member, channel=made)

    await do_ban(interaction, made, await get_row(db, made.id), stranger)

    assert made.permissions[-1][2]["view_channel"] is False


async def test_unban_clears_the_member_s_own_overwrite(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    row = await get_row(db, made.id)
    await do_ban(FakeInteraction(bot, member, channel=made), made, row, stranger)
    made.overwrites[stranger] = discord.PermissionOverwrite(connect=False, view_channel=False)

    said = await do_forget_member(
        FakeInteraction(bot, member, channel=made), made, row, stranger, "unban"
    )

    assert made.permissions[-1][:2] == (stranger, None)
    assert "may join this channel again" in said
    assert "tempvoice.unban" in await action_kinds(db)


async def test_unpermit_keeps_the_rest_of_a_member_s_overwrite(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    made.overwrites[stranger] = discord.PermissionOverwrite(
        connect=True, view_channel=True, speak=False
    )

    said = await do_forget_member(
        FakeInteraction(bot, member, channel=made), made, await get_row(db, made.id), stranger,
        "unpermit",
    )

    left = made.permissions[-1][1]
    assert left.connect is None and left.view_channel is None and left.speak is False
    assert "no longer has their own way in" in said


async def test_a_rename_discord_rate_limits_says_how_often_it_is_allowed(
    cog, bot, creator, member, db
):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    made.edit_raises = too_fast()

    said = await do_rename(
        FakeInteraction(bot, member, channel=made), made, await get_row(db, made.id), "The Pit"
    )

    assert said == RENAMED_TOO_OFTEN
    assert "twice every 10 minutes" in said
    assert "tempvoice.rename_failed" in await action_kinds(db)


async def test_emptiness_is_read_off_the_voice_states(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    made.members.clear()
    made.members.append(member)

    await cog._maybe_delete(bot.guild, made)
    assert made.deleted is False

    made.members.clear()
    await cog._maybe_delete(bot.guild, made)
    assert made.deleted is True


async def test_the_reconcile_loop_runs_every_five_minutes_and_stops_with_the_cog(cog, bot):
    assert cog._reconcile_loop.minutes == RECONCILE_MINUTES

    await cog.cog_load()
    assert cog._reconcile_loop.is_running()

    await cog.cog_unload()
    await asyncio.sleep(0)
    assert cog._reconcile_loop.is_running() is False


async def test_setup_repairs_the_lobby_it_already_has_instead_of_making_a_second_one(
    cog, bot, lead, creator, db
):
    creator.name = "join"
    interaction = FakeInteraction(bot, lead)

    await cog.setup_channel.callback(cog, interaction, None)

    assert bot.guild.created == []
    assert creator.name == "join to create a channel"
    assert bot.store.get(GUILD, "tempvoice_creator_ids") == [CREATOR]
    assert "repaired" in interaction.sent
    assert "tempvoice.repair" in await action_kinds(db)


async def test_a_repair_that_discord_refuses_says_so_and_is_logged(cog, bot, lead, creator, db):
    creator.edit_raises = refused()
    interaction = FakeInteraction(bot, lead)

    await cog.setup_channel.callback(cog, interaction, None)

    assert "refused" in interaction.sent
    assert "tempvoice.repair_failed" in await action_kinds(db)


async def test_a_repair_names_the_other_lobbies_and_how_to_drop_them(cog, bot, lead, creator):
    second = bot.guild.add(FakeVoice(CREATOR + 1, bot.guild, name="join"))
    await bot.store.set(GUILD, "tempvoice_creator_ids", [CREATOR, second.id])
    interaction = FakeInteraction(bot, lead)

    await cog.setup_channel.callback(cog, interaction, None)

    assert f"<#{second.id}>" in interaction.sent and "/tempvoice forget" in interaction.sent
    assert second.name == "join"


async def test_test_mode_will_not_repair_a_lobby_outside_the_test_category(cog, bot, lead, creator):
    bot.guild.add(FakeText(TEST_CHANNEL, category=FakeCategory(50)))
    bot.guard = FakeGuard()
    interaction = FakeInteraction(bot, lead)

    await cog.setup_channel.callback(cog, interaction, None)

    assert creator.name == "join to create a channel"
    assert creator.edits == []
    assert "test mode" in interaction.sent.lower()


async def test_a_name_given_to_setup_is_remembered_as_the_setting(cog, bot, lead, creator):
    interaction = FakeInteraction(bot, lead)

    await cog.setup_channel.callback(cog, interaction, "Join Here")

    assert bot.store.get(GUILD, "tempvoice_creator_name") == "Join Here"
    assert creator.name == "Join Here"


async def test_forget_drops_a_creator_id_and_refuses_anything_else(cog, bot, lead, db):
    interaction = FakeInteraction(bot, lead)
    await cog.forget.callback(cog, interaction, str(CREATOR))
    assert bot.store.get(GUILD, "tempvoice_creator_ids") == []
    assert "tempvoice.creator_removed" in await action_kinds(db)

    again = FakeInteraction(bot, lead)
    await cog.forget.callback(cog, again, str(CREATOR))
    assert "not one of" in again.sent

    nonsense = FakeInteraction(bot, lead)
    await cog.forget.callback(cog, nonsense, "the lobby")
    assert "not a channel id" in nonsense.sent


async def test_forget_is_staff_only(cog, bot, member):
    interaction = FakeInteraction(bot, member)

    await cog.forget.callback(cog, interaction, str(CREATOR))

    assert bot.store.get(GUILD, "tempvoice_creator_ids") == [CREATOR]
    assert "staff only" in interaction.sent


async def test_deleting_the_lobby_makes_black_bloc_forget_it(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]

    await cog.on_guild_channel_delete(creator)
    await cog.on_guild_channel_delete(made)

    assert bot.store.get(GUILD, "tempvoice_creator_ids") == []
    assert await get_row(db, made.id) is None
    assert "tempvoice.creator_removed" in await action_kinds(db)


async def test_the_setup_reply_never_pings(cog, bot, lead):
    await bot.store.set(GUILD, "tempvoice_creator_ids", [])
    interaction = FakeInteraction(bot, lead)

    await cog.setup_channel.callback(cog, interaction, None)

    assert interaction.response.messages[-1]["allowed_mentions"].everyone is False


def staffed(bot, category=None, staff_role_id=555):
    """One staff role (it can see the staff channel) and the Member role, on the guild."""
    member_role = FakeRole(MEMBER_ROLE_ID)
    staff_role = FakeRole(staff_role_id)
    bot.guild.roles = [member_role, staff_role]
    channel = bot.guild.add(FakeText(TEST_CHANNEL, category=category))
    channel.visible_to = {staff_role_id}
    return member_role, staff_role


def test_a_new_channel_starts_from_a_copy_of_the_category_s_overwrites():
    role = FakeRole(9)
    category = FakeCategory(
        50, overwrites={role: discord.PermissionOverwrite(view_channel=False, connect=False)}
    )

    copied = category_overwrites(category)
    copied[role].connect = True

    assert category.overwrites[role].connect is False
    assert creator_overwrites(category, [role])[role].view_channel is True


async def test_the_lobby_lets_the_allowed_role_staff_and_the_bot_in(cog, bot, lead):
    category = FakeCategory(
        50, overwrites={bot.guild.default_role: discord.PermissionOverwrite(connect=False)}
    )
    member_role, staff_role = staffed(bot, category)
    bot.guard = FakeGuard()

    await cog.setup_channel.callback(cog, FakeInteraction(bot, lead), None)

    given = bot.guild.created[0].given_overwrites
    assert given[member_role].view_channel is True and given[member_role].connect is True
    assert given[staff_role].view_channel is True and given[staff_role].connect is True
    assert given[bot.guild.me].connect is True and given[bot.guild.me].manage_channels is True
    assert given[bot.guild.default_role].connect is False


async def test_a_repair_puts_those_overwrites_on_the_lobby_it_already_has(cog, bot, lead):
    category = FakeCategory(
        50, overwrites={bot.guild.default_role: discord.PermissionOverwrite(connect=False)}
    )
    member_role, staff_role = staffed(bot, category)
    bot.guard = FakeGuard()
    lobby = bot.guild.add(
        FakeVoice(CREATOR, bot.guild, category=category, position=4, name="join")
    )

    await cog.setup_channel.callback(cog, FakeInteraction(bot, lead), None)

    assert lobby.name == "join to create a channel"
    assert lobby.overwrites[member_role].connect is True
    assert lobby.overwrites[staff_role].connect is True
    assert lobby.overwrites[bot.guild.default_role].connect is False


async def test_a_spawned_channel_lets_the_allowed_role_and_staff_in_too(cog, bot, member):
    category = FakeCategory(
        50, overwrites={bot.guild.default_role: discord.PermissionOverwrite(connect=False)}
    )
    member_role, staff_role = staffed(bot, category)
    creator = bot.guild.add(FakeVoice(CREATOR, bot.guild, category=category, position=4))

    await cog._maybe_create(member, creator)

    given = bot.guild.created[0].given_overwrites
    assert given[member_role].connect is True and given[staff_role].connect is True
    assert given[bot.guild.default_role].connect is False
    assert given[member].manage_channels is True


async def test_an_allowed_role_that_no_longer_exists_is_left_out(cog, bot, lead):
    category = FakeCategory(50)
    bot.guild.add(FakeText(TEST_CHANNEL, category=category))
    bot.guard = FakeGuard()

    await cog.setup_channel.callback(cog, FakeInteraction(bot, lead), None)

    assert bot.guild.created[0].given_overwrites == {
        bot.guild.me: discord.PermissionOverwrite(
            view_channel=True, connect=True, manage_channels=True, move_members=True
        )
    }


async def test_the_reconcile_loop_records_its_last_good_run_and_its_last_error(cog, bot):
    assert cog.loop_health("_reconcile_loop") == (None, None)

    await cog._reconcile_loop.coro(cog)

    assert cog.last_ok_at is not None and cog.last_error is None
    assert cog.loop_health("_reconcile_loop") == (cog.last_ok_at, None)
    assert cog.loop_health("poller") == (None, None)

    async def boom():
        raise RuntimeError("the database went away")

    cog.reconcile_channels = boom
    await cog._reconcile_loop.coro(cog)

    assert "the database went away" in cog.last_error


async def test_a_reconcile_loop_that_stopped_records_the_error_and_restarts_itself(
    cog, bot, caplog
):
    restarted = []
    cog._reconcile_loop.restart = lambda *a, **k: restarted.append(True)

    with caplog.at_level("ERROR"):
        await cog._reconcile_stopped(RuntimeError("the gateway went away"))

    assert restarted == [True]
    assert "the gateway went away" in cog.last_error
    assert cog._reconcile_loop._error is not None


def test_the_voice_group_carries_every_control_the_panel_has_and_more():
    groups = {group.name: group for group in TempVoice.__cog_app_commands__}

    assert sorted(command.name for command in groups["voice"].commands) == [
        "ban", "bitrate", "claim", "hide", "info", "kick", "limit", "lock", "permit", "region",
        "rename", "show", "transfer", "unban", "unlock", "unpermit",
    ]
    region = next(c for c in groups["voice"].commands if c.name == "region")
    assert region._params["region"].autocomplete is not None


def test_bitrates_are_clamped_to_discord_s_range_and_the_guild_s_ceiling():
    assert clamp_bitrate(64, 96000) == 64000
    assert clamp_bitrate(96, 64000) == 64000
    assert clamp_bitrate(200, 96000) == 96000
    assert clamp_bitrate(1, 96000) == 8000
    assert clamp_bitrate("lots", 96000) == 96000
    assert clamp_bitrate(64, None) == 64000


def test_the_guild_s_ceiling_falls_back_to_ninety_six_kbps():
    assert guild_bitrate_ceiling(FakeGuild()) == 96000

    boosted = FakeGuild()
    boosted.bitrate_limit = 256000.0
    assert guild_bitrate_ceiling(boosted) == 256000


def test_region_autocomplete_offers_auto_and_matches_what_was_typed():
    assert region_choices("")[0] == "auto"
    assert region_choices("us-") == ["us-central", "us-east", "us-south", "us-west"]
    assert region_choices("nowhere") == []
    assert len(region_choices("")) <= 25


def test_the_allowed_role_is_what_lets_someone_use_the_commands():
    guild = FakeGuild()
    assert may_use_voice(None, FakeMember(guild, roles=())) is True
    assert may_use_voice(MEMBER_ROLE_ID, FakeMember(guild, user_id=1)) is True
    assert may_use_voice(MEMBER_ROLE_ID, FakeMember(guild, user_id=2, roles=())) is False


def test_a_command_acts_on_the_channel_you_are_in_then_the_one_you_own():
    rows = [
        {"channel_id": 10, "owner_id": USER},
        {"channel_id": 11, "owner_id": USER + 1},
    ]
    assert pick_row(rows, USER, 11) is rows[0]
    assert pick_row(rows, USER, 10) is rows[0]
    assert pick_row(rows, USER, None) is rows[0]
    assert pick_row(rows, USER + 2, None) is None
    assert pick_row(rows, USER, 11, owner_only=False) is rows[1]
    assert pick_row(rows, USER, None, owner_only=False) is None


async def test_voice_rename_changes_the_channel_the_caller_owns(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    interaction = FakeInteraction(bot, member)

    await cog.voice_rename.callback(cog, interaction, "The Pit")

    assert made.name == "The Pit"
    assert (await get_prefs(db, member.id))["name"] == "The Pit"
    assert "tempvoice.rename" in await action_kinds(db)
    assert interaction.response.messages[0].get("deferred") is True


async def test_voice_refuses_someone_without_the_allowed_role(cog, bot, creator, db):
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo", roles=())
    interaction = FakeInteraction(bot, stranger)

    await cog.voice_rename.callback(cog, interaction, "The Pit")

    assert f"<@&{MEMBER_ROLE_ID}>" in interaction.sent
    assert interaction.response.messages[-1]["allowed_mentions"].roles is False
    assert await action_kinds(db) == []


async def test_voice_says_how_to_get_a_channel_when_you_have_none(cog, bot, member):
    interaction = FakeInteraction(bot, member)

    await cog.voice_rename.callback(cog, interaction, "The Pit")

    assert "don't own a temp channel" in interaction.sent
    assert "join to create a channel" in interaction.sent


async def test_voice_lock_and_unlock_call_the_same_helper_the_button_does(
    cog, bot, creator, member, db
):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]

    await cog.voice_lock.callback(cog, FakeInteraction(bot, member))
    assert made.permissions[-1][1].connect is False
    assert (await get_prefs(db, member.id))["locked"] == 1

    again = FakeInteraction(bot, member)
    await cog.voice_lock.callback(cog, again)
    assert "already locked" in again.sent
    assert len(made.permissions) == 1

    await cog.voice_unlock.callback(cog, FakeInteraction(bot, member))
    assert made.permissions[-1][1].connect is None
    kinds = await action_kinds(db)
    assert "tempvoice.lock" in kinds and "tempvoice.unlock" in kinds


async def test_voice_kick_moves_the_member_out_and_logs_it(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    stranger = connect(FakeMember(bot.guild, user_id=USER + 1, display_name="Bo"), made)

    await cog.voice_kick.callback(cog, FakeInteraction(bot, member), stranger)

    assert stranger.moves == [None]
    assert "tempvoice.kick" in await action_kinds(db)


async def test_voice_unban_clears_the_overwrite_ban_left(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    await cog.voice_ban.callback(cog, FakeInteraction(bot, member), stranger)
    made.overwrites[stranger] = discord.PermissionOverwrite(connect=False, view_channel=False)

    await cog.voice_unban.callback(cog, FakeInteraction(bot, member), stranger)

    assert made.permissions[-1][:2] == (stranger, None)
    kinds = await action_kinds(db)
    assert "tempvoice.ban" in kinds and "tempvoice.unban" in kinds


async def test_voice_claim_acts_on_the_channel_the_caller_is_in(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    made.members.clear()
    stranger = connect(FakeMember(bot.guild, user_id=USER + 1, display_name="Bo"), made)

    await cog.voice_claim.callback(cog, FakeInteraction(bot, stranger))

    assert (await get_row(db, made.id))["owner_id"] == stranger.id
    assert "tempvoice.claim" in await action_kinds(db)


async def test_voice_claim_needs_you_to_be_in_a_temp_channel(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    interaction = FakeInteraction(bot, stranger)

    await cog.voice_claim.callback(cog, interaction)

    assert "nothing to claim" in interaction.sent
    assert "tempvoice.claim" not in await action_kinds(db)


async def test_voice_bitrate_is_clamped_remembered_and_reused_next_time(
    cog, bot, creator, member, db
):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    interaction = FakeInteraction(bot, member)

    await cog.voice_bitrate.callback(cog, interaction, 96)

    assert made.bitrate == 96000
    assert (await get_prefs(db, member.id))["bitrate"] == 96000
    assert "tempvoice.bitrate" in await action_kinds(db)

    made.members.clear()
    await cog._maybe_delete(bot.guild, made)
    await cog._maybe_create(member, creator)

    assert bot.guild.created[1].bitrate == 96000


async def test_voice_bitrate_says_when_the_boost_level_capped_it(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    bot.guild.bitrate_limit = 64000
    interaction = FakeInteraction(bot, member)

    await cog.voice_bitrate.callback(cog, interaction, 96)

    assert bot.guild.created[0].bitrate == 64000
    assert "64 kbps" in interaction.sent and "boost level" in interaction.sent


async def test_voice_region_sets_and_clears_the_rtc_region(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]

    await cog.voice_region.callback(cog, FakeInteraction(bot, member), "us-west")
    assert made.rtc_region == "us-west"

    auto = FakeInteraction(bot, member)
    await cog.voice_region.callback(cog, auto, "auto")
    assert made.rtc_region is None
    assert "automatic" in auto.sent
    assert (await action_kinds(db)).count("tempvoice.region") == 2


async def test_a_region_discord_refuses_says_which_one(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    made.edit_raises = refused()
    interaction = FakeInteraction(bot, member)

    await cog.voice_region.callback(cog, interaction, "atlantis")

    assert "atlantis" in interaction.sent
    assert "tempvoice.region_failed" in await action_kinds(db)


async def test_voice_info_reports_the_channel_s_own_state(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    banned = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    guest = FakeMember(bot.guild, user_id=USER + 2, display_name="Cass")
    made.overwrites[banned] = discord.PermissionOverwrite(connect=False)
    made.overwrites[guest] = discord.PermissionOverwrite(connect=True)
    made.user_limit = 4
    interaction = FakeInteraction(bot, member)

    await cog.voice_info.callback(cog, interaction)

    said = interaction.sent
    assert f"**owner** — <@{member.id}>" in said
    assert "**limit** — 4 people" in said
    assert "**locked** — no" in said
    assert f"**let in by name** — <@{guest.id}>" in said
    assert f"**kept out by name** — <@{banned.id}>" in said
    assert interaction.response.messages[-1]["allowed_mentions"].users is False


def test_roles_never_count_as_permitted_or_banned_members():
    role = FakeRole(9)
    member = FakeRole(USER)
    owner = FakeRole(1)
    overwrites = {
        role: discord.PermissionOverwrite(connect=True),
        owner: discord.PermissionOverwrite(connect=True),
        member: discord.PermissionOverwrite(connect=False),
    }

    assert member_lists(overwrites, 1, [9]) == ([], [USER])


async def test_status_shows_the_lobby_name_and_the_loop_s_health(cog, bot, lead):
    cog.last_ok_at = "2026-08-26T12:00:00+00:00"

    interaction = FakeInteraction(bot, lead)
    await cog.status.callback(cog, interaction)

    assert "join to create a channel" in interaction.sent
    assert "2026-08-26T12:00:00+00:00" in interaction.sent
    assert "**last error** — none" in interaction.sent


def test_a_lobby_is_recognised_by_its_name_when_the_id_list_does_not_know_it():
    guild = FakeGuild()
    known = FakeVoice(1, guild, name=TEMPVOICE_CREATOR_NAME)
    stray = FakeVoice(2, guild, name="  Join To Create A Channel  ")
    other = FakeVoice(3, guild, name="General")
    category = FakeCategory(50, voice_channels=[known, stray, other])

    assert lobbies_by_name(category, TEMPVOICE_CREATOR_NAME, [1]) == [stray]
    assert lobbies_by_name(category, TEMPVOICE_CREATOR_NAME, [1, 2]) == []
    assert lobbies_by_name(None, TEMPVOICE_CREATOR_NAME, []) == []


def where_the_lobby_belongs(bot, name=TEMPVOICE_CREATOR_NAME, ids=()):
    """Test mode on, a lobby carrying the name in the test channel's category, and no stored id."""
    category = FakeCategory(50)
    lobby = bot.guild.add(FakeVoice(600, bot.guild, category=category, position=2, name=name))
    category.voice_channels = [lobby]
    bot.guild.add(FakeText(TEST_CHANNEL, category=category))
    bot.guard = FakeGuard()
    return category, lobby


async def test_setup_takes_over_a_lobby_it_lost_track_of_instead_of_making_a_second_one(
    cog, bot, lead, db
):
    await bot.store.set(GUILD, "tempvoice_creator_ids", [])
    _, lobby = where_the_lobby_belongs(bot, name="join")
    await bot.store.set(GUILD, "tempvoice_creator_name", "join")
    interaction = FakeInteraction(bot, lead)

    await cog.setup_channel.callback(cog, interaction, None)

    assert bot.guild.created == []
    assert bot.store.get(GUILD, "tempvoice_creator_ids") == [lobby.id]
    assert lobby.edits and lobby.edits[-1]["name"] == "join"
    assert "took it over" in interaction.sent and f"<#{lobby.id}>" in interaction.sent
    kinds = await action_kinds(db)
    assert "tempvoice.adopt" in kinds and "tempvoice.repair" in kinds


async def test_setup_leaves_a_channel_with_another_name_alone_and_makes_its_own(cog, bot, lead):
    await bot.store.set(GUILD, "tempvoice_creator_ids", [])
    _, lobby = where_the_lobby_belongs(bot, name="General")
    interaction = FakeInteraction(bot, lead)

    await cog.setup_channel.callback(cog, interaction, None)

    assert lobby.edits == []
    assert [c.name for c in bot.guild.created] == [TEMPVOICE_CREATOR_NAME]
    assert bot.store.get(GUILD, "tempvoice_creator_ids") == [bot.guild.created[0].id]


async def test_a_lobby_taken_over_is_stored_even_when_discord_refuses_the_repair(
    cog, bot, lead, db
):
    await bot.store.set(GUILD, "tempvoice_creator_ids", [])
    _, lobby = where_the_lobby_belongs(bot)
    lobby.edit_raises = refused()
    interaction = FakeInteraction(bot, lead)

    await cog.setup_channel.callback(cog, interaction, None)

    assert bot.store.get(GUILD, "tempvoice_creator_ids") == [lobby.id]
    assert "refused" in interaction.sent
    assert "tempvoice.repair_failed" in await action_kinds(db)


async def test_status_names_the_lobbies_black_bloc_is_not_keeping_track_of(cog, bot, lead):
    _, lobby = where_the_lobby_belongs(bot)
    interaction = FakeInteraction(bot, lead)

    await cog.status.callback(cog, interaction)

    assert f"<#{lobby.id}>" in interaction.sent
    assert "not kept track of" in interaction.sent
    assert "`/tempvoice setup`" in interaction.sent
    assert interaction.response.messages[-1]["allowed_mentions"].everyone is False
