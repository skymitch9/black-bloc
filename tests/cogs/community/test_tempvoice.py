import asyncio
from datetime import UTC, datetime, timedelta

import discord
import pytest

from black_bloc.cogs.community.tempvoice import (
    CREATOR_NAME,
    RECONCILE_GRACE_SECONDS,
    MemberPick,
    TempVoice,
    TempVoicePanel,
    add_channel,
    bottom_position,
    channel_name,
    creator_position,
    delete_row,
    get_prefs,
    get_row,
    is_panel_owner,
    is_stale,
    not_owner_message,
    owner_overwrites,
    panel_context,
    panel_id,
    parse_limit,
    rows_for_guild,
    save_prefs,
    set_owner,
    set_panel_message,
    spawn_position,
)
from black_bloc.config import load_settings
from black_bloc.settings_store import MEMBER_ROLE_ID, SettingsStore
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
    def __init__(self, category_id, voice_channels=()):
        self.id = category_id
        self.name = f"category-{category_id}"
        self.voice_channels = list(voice_channels)


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


class FakePerms:
    def __init__(self, manage_guild=False):
        self.manage_guild = manage_guild


class FakeText:
    def __init__(self, channel_id, category=None):
        self.id = channel_id
        self.category = category
        self.category_id = category.id if category else None
        self.overwrites = {}
        self.messages = []

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
        self.deleted = False
        self.edits = []
        self.permissions = []
        self.messages = []
        self.overwrites = {}
        self.send_raises = None

    async def delete(self, reason=None):
        self.deleted = True
        self.guild.channels.pop(self.id, None)

    async def edit(self, **kwargs):
        self.edits.append(kwargs)

    async def send(self, content=None, **kwargs):
        if self.send_raises is not None:
            raise self.send_raises
        message = FakeMessage(len(self.messages) + 1, content or "", **kwargs)
        self.messages.append(message)
        return message

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
        self.afk_channel = None
        self.created = []
        self._next_id = 1000

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_member(self, user_id):
        return self.members.get(user_id)

    @property
    def voice_channels(self):
        return [c for c in self.channels.values() if isinstance(c, FakeVoice)]

    def add(self, channel):
        self.channels[channel.id] = channel
        return channel

    async def create_voice_channel(
        self, name, *, category=None, position=0, overwrites=None, user_limit=0, reason=None
    ):
        self._next_id += 1
        channel = FakeVoice(self._next_id, self, category, position, name=name)
        channel.user_limit = user_limit
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


class FakeState:
    def __init__(self):
        self.channel = None


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.modals = []

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def send_modal(self, modal):
        self.modals.append(modal)

    async def defer(self, ephemeral=False):
        self.messages.append({"content": None, "deferred": True})


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.response.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeInteraction:
    def __init__(self, bot, user, channel=None):
        self.client = bot
        self.user = user
        self.guild = bot.guild
        self.guild_id = bot.guild.id
        self.channel = channel
        self.channel_id = channel.id if channel is not None else TEST_CHANNEL
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)

    @property
    def sent(self):
        return self.response.messages[-1]["content"] if self.response.messages else None


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
    return bot.guild.add(FakeVoice(CREATOR, bot.guild, position=4, name=CREATOR_NAME))


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
        for name in ("rename", "limit", "lock", "hide", "kick", "ban", "permit", "transfer",
                     "claim")
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


async def test_in_test_mode_the_panel_is_logged_instead_of_posted(cog, bot, member, db):
    category = FakeCategory(50)
    bot.guild.add(FakeText(TEST_CHANNEL, category=category))
    bot.guard = FakeGuard()
    creator = bot.guild.add(FakeVoice(CREATOR, bot.guild, category=category, position=1))

    await cog._maybe_create(member, creator)

    made = bot.guild.created[0]
    assert made.messages == []
    assert "tempvoice.would_post_panel" in await action_kinds(db)
    assert (await get_row(db, made.id))["panel_message_id"] is None


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
    assert made.name == CREATOR_NAME and made.category is category and made.position == 3
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
    row = await get_row(db, made.id)

    await panel._toggle(FakeInteraction(bot, member, channel=made), row, "connect")
    assert made.permissions[-1][1].connect is False
    assert (await get_prefs(db, member.id))["locked"] == 1

    await panel._toggle(FakeInteraction(bot, member, channel=made), row, "connect")
    assert made.permissions[-1][1].connect is None
    assert (await get_prefs(db, member.id))["locked"] == 0
    kinds = await action_kinds(db)
    assert "tempvoice.lock" in kinds and "tempvoice.unlock" in kinds


async def test_hide_and_show_toggle_view_channel(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    row = await get_row(db, made.id)

    await TempVoicePanel()._toggle(FakeInteraction(bot, member, channel=made), row, "view_channel")

    assert made.permissions[-1][1].view_channel is False
    assert (await get_prefs(db, member.id))["hidden"] == 1
    assert "tempvoice.hide" in await action_kinds(db)


async def test_kicking_someone_who_is_not_here_changes_nothing(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    interaction = FakeInteraction(bot, member, channel=made)

    await MemberPick("kick", "who")._kick(interaction, made, stranger, await get_row(db, made.id))

    assert stranger.moves == []
    assert "not in this channel" in interaction.sent


async def test_banning_someone_denies_connect_and_moves_them_out(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    made.members.append(stranger)
    interaction = FakeInteraction(bot, member, channel=made)

    await MemberPick("ban", "who")._ban(interaction, made, stranger, await get_row(db, made.id))

    assert made.permissions[-1][2] == {"connect": False}
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
