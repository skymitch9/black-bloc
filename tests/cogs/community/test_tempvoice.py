import asyncio
import json
from datetime import UTC, datetime, timedelta

import discord
import pytest
from discord import app_commands

from black_bloc import tempvoice as voice
from black_bloc.cogs.community.tempvoice import (
    MEMBER_MEMORY_MAX,
    RECONCILE_GRACE_SECONDS,
    RECONCILE_MINUTES,
    RENAMED_TOO_OFTEN,
    SITE_BUTTON,
    BitrateModal,
    ChannelPick,
    LimitModal,
    LobbyPick,
    NewOwnerPick,
    RegionPick,
    RenameModal,
    SetupModal,
    TempVoice,
    TempVoicePanel,
    UndoPick,
    VoicePanel,
    act_on_own,
    add_channel,
    apply_remembered_members,
    bottom_position,
    build_panel,
    build_people,
    category_overwrites,
    channel_name,
    clamp_bitrate,
    creator_overwrites,
    creator_position,
    delete_row,
    do_ban,
    do_bitrate,
    do_forget_member,
    do_kick,
    do_permit,
    do_privacy,
    do_rename,
    do_transfer,
    get_prefs,
    get_row,
    get_row_by_panel,
    guild_bitrate_ceiling,
    id_list,
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
    privacy_of,
    remembered_lines,
    rows_for_guild,
    run_claim,
    run_forget_lobby,
    run_forget_prefs,
    run_people_move,
    run_region,
    run_setup,
    save_prefs,
    set_owner,
    set_panel_message,
    spawn_position,
    with_member,
)
from black_bloc.command_errors import AnswersErrors
from black_bloc.config import load_settings
from black_bloc.settings_store import (
    DB_UNAVAILABLE,
    MEMBER_ROLE_ID,
    TEMPVOICE_CREATOR_NAME,
    SettingsStore,
)

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

    async def edit(self, **kwargs):
        self.kwargs |= kwargs

    @property
    def embeds(self):
        one = self.kwargs.get("embed")
        return [one] if one is not None else list(self.kwargs.get("embeds") or ())


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
        rtc_region=None,
        reason=None,
    ):
        self._next_id += 1
        channel = FakeVoice(self._next_id, self, category, position, name=name)
        channel.user_limit = user_limit
        channel.bitrate = bitrate or 0
        channel.rtc_region = rtc_region
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
        self.owned_channel_ids = set()

    def own_channel(self, channel_id):
        self.owned_channel_ids.add(int(channel_id))

    def disown_channel(self, channel_id):
        self.owned_channel_ids.discard(int(channel_id))

    def owns_channel(self, channel_id):
        return int(channel_id) in self.owned_channel_ids

    def allows_channel(self, channel_id):
        return channel_id == self.test_channel_id or self.owns_channel(channel_id)

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
        self.cogs = {}

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def get_cog(self, name):
        return self.cogs.get(name)

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
    def __init__(self, bot, user, channel=None, message=None, guild=True):
        self.client = bot
        self.user = user
        self.guild = bot.guild if guild else None
        self.guild_id = getattr(self.guild, "id", None)
        self.channel = channel
        self.channel_id = channel.id if channel is not None else TEST_CHANNEL
        self.message = message
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)
        self.edits = []

    async def original_response(self):
        return FakeMessage(1, "")

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return FakeMessage(9500, "", **kwargs)

    @property
    def sent(self):
        said = [m["content"] for m in self.response.messages if m["content"] is not None]
        return said[-1] if said else None

    @property
    def rendered(self):
        if self.edits:
            return self.edits[-1]
        return self.response.messages[-1] if self.response.messages else {}

    @property
    def view(self):
        return self.rendered.get("view")

    @property
    def shown(self):
        embed = self.rendered.get("embed")
        return embed.description if embed is not None else ""


def labels(view):
    return [one.label for one in view.children if getattr(one, "label", None)]


def button(view, label):
    return next(one for one in view.children if getattr(one, "label", None) == label)


def picker(view, kind):
    return next(one for one in view.children if isinstance(one, kind))


def placeholders(view):
    return [
        one.placeholder for one in view.children if getattr(one, "placeholder", None) is not None
    ]


async def panel_for(bot, actor):
    return await build_panel(bot, bot.guild, actor)


async def press(bot, actor, view, label):
    """One click on a live panel, the way Discord dispatches it."""
    interaction = FakeInteraction(bot, actor)
    await button(view, label).callback(interaction)
    return interaction


async def choose(bot, actor, view, kind, value):
    interaction = FakeInteraction(bot, actor)
    control = picker(view, kind)
    control._values = [value if not isinstance(value, (int, str)) else str(value)]
    await control.callback(interaction)
    return interaction


async def action_kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]



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


async def test_in_test_mode_the_panel_goes_in_the_voice_channel_s_own_chat(cog, bot, member, db):
    category = FakeCategory(50)
    test_channel = bot.guild.add(FakeText(TEST_CHANNEL, category=category))
    bot.guard = FakeGuard()
    creator = bot.guild.add(FakeVoice(CREATOR, bot.guild, category=category, position=1))

    await cog._maybe_create(member, creator)

    made = bot.guild.created[0]
    assert test_channel.messages == []
    assert len(made.messages) == 1
    assert not made.messages[0].content.startswith("Controls for")
    assert str(TEST_CHANNEL) not in made.messages[0].content
    assert made.messages[0].kwargs["allowed_mentions"].everyone is False
    row = await get_row(db, made.id)
    assert row["panel_message_id"] == made.messages[0].id
    assert row["panel_channel_id"] == made.id
    assert "tempvoice.panel_elsewhere" not in await action_kinds(db)


async def test_a_panel_for_a_channel_black_bloc_does_not_own_still_falls_back(cog, bot, member, db):
    category = FakeCategory(50)
    test_channel = bot.guild.add(FakeText(TEST_CHANNEL, category=category))
    bot.guard = FakeGuard()
    stray = bot.guild.add(FakeVoice(4321, bot.guild, category=category))

    await cog._post_panel(bot.guild, stray, member)

    assert stray.messages == []
    assert len(test_channel.messages) == 1
    assert test_channel.messages[0].content.startswith(f"Controls for <#{stray.id}>")
    assert "tempvoice.panel_elsewhere" in await action_kinds(db)


async def test_a_panel_with_nowhere_to_go_is_logged_as_a_failure(cog, bot, member, db):
    bot.guard = FakeGuard(test_channel_id=None)
    stray = bot.guild.add(FakeVoice(4321, bot.guild, category=FakeCategory(50)))
    await add_channel(db, stray.id, GUILD, member.id, CREATOR)

    await cog._post_panel(bot.guild, stray, member)

    assert stray.messages == []
    assert "tempvoice.panel_failed" in await action_kinds(db)
    assert (await get_row(db, stray.id))["panel_message_id"] is None


def test_the_panel_lives_in_the_voice_chat_unless_the_guard_would_refuse_it(bot):
    voice = bot.guild.add(FakeVoice(4321, bot.guild))
    test_channel = bot.guild.add(FakeText(TEST_CHANNEL))

    assert panel_home(bot, voice) is voice

    bot.guard = FakeGuard()
    assert panel_home(bot, voice) is test_channel
    assert panel_home(bot, test_channel) is test_channel

    bot.guard.own_channel(voice.id)
    assert panel_home(bot, voice) is voice

    bot.guard = FakeGuard(test_channel_id=None)
    assert panel_home(bot, voice) is None


async def test_a_click_in_the_voice_chat_finds_the_channel_the_panel_belongs_to(
    cog, bot, member, db
):
    category = FakeCategory(50)
    bot.guild.add(FakeText(TEST_CHANNEL, category=category))
    bot.guard = FakeGuard()
    creator = bot.guild.add(FakeVoice(CREATOR, bot.guild, category=category, position=1))
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    posted = made.messages[0]

    found = await panel_context(FakeInteraction(bot, member, channel=made, message=posted))

    assert found.channel is made and found.row["channel_id"] == made.id
    assert (await get_row_by_panel(db, posted.id))["channel_id"] == made.id


async def test_a_click_in_a_channel_black_bloc_does_not_own_is_refused(cog, bot, member, db):
    category = FakeCategory(50)
    bot.guild.add(FakeText(TEST_CHANNEL, category=category))
    bot.guard = FakeGuard()
    creator = bot.guild.add(FakeVoice(CREATOR, bot.guild, category=category, position=1))
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    stray = bot.guild.add(FakeVoice(4321, bot.guild, category=category))
    bot.guard.disown_channel(made.id)

    interaction = FakeInteraction(bot, member, channel=stray, message=made.messages[0])

    assert await panel_context(interaction) is None
    assert interaction.sent == "test mode"


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


async def test_a_spawned_channel_is_one_the_guard_lets_black_bloc_speak_in(cog, bot, member, db):
    category = FakeCategory(50)
    bot.guild.add(FakeText(TEST_CHANNEL, category=category))
    bot.guard = FakeGuard()
    creator = bot.guild.add(FakeVoice(CREATOR, bot.guild, category=category, position=1))

    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    assert bot.guard.owned_channel_ids == {made.id}

    made.members.clear()
    await cog._maybe_delete(bot.guild, made)
    assert bot.guard.owned_channel_ids == set()


async def test_a_delete_discord_refuses_keeps_the_channel_speakable(cog, bot, member, db):
    category = FakeCategory(50)
    bot.guild.add(FakeText(TEST_CHANNEL, category=category))
    bot.guard = FakeGuard()
    creator = bot.guild.add(FakeVoice(CREATOR, bot.guild, category=category, position=1))
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    made.members.clear()

    async def refusing_delete(reason=None):
        raise refused()

    made.delete = refusing_delete
    await cog._maybe_delete(bot.guild, made)

    assert bot.guard.owned_channel_ids == {made.id}


async def test_deleting_the_channel_in_discord_takes_away_the_allowance(cog, bot, member, db):
    category = FakeCategory(50)
    bot.guild.add(FakeText(TEST_CHANNEL, category=category))
    bot.guard = FakeGuard()
    creator = bot.guild.add(FakeVoice(CREATOR, bot.guild, category=category, position=1))
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]

    await cog.on_guild_channel_delete(made)

    assert bot.guard.owned_channel_ids == set()


async def test_reconcile_gives_back_the_allowance_after_a_restart_and_drops_dead_rows(
    cog, bot, member, db
):
    bot.guard = FakeGuard()
    busy = bot.guild.add(FakeVoice(10, bot.guild, members=[member]))
    await add_channel(db, busy.id, GUILD, USER, CREATOR)
    await add_channel(db, 4242, GUILD, USER, CREATOR)
    bot.guard.own_channel(4242)

    await cog.reconcile_channels()

    assert bot.guard.owned_channel_ids == {busy.id}
    assert await get_row(db, 4242) is None


async def test_setup_puts_the_creator_in_the_test_category_while_test_mode_is_on(cog, bot, lead):
    category = FakeCategory(50, voice_channels=[FakeVoice(60, bot.guild, position=2)])
    bot.guild.add(FakeText(TEST_CHANNEL, category=category))
    bot.guard = FakeGuard()
    interaction = FakeInteraction(bot, lead)

    await run_setup(interaction, None)

    made = bot.guild.created[0]
    assert made.name == TEMPVOICE_CREATOR_NAME == "join to create a channel"
    assert made.category is category and made.position == 3
    assert bot.store.get(GUILD, "tempvoice_creator_ids") == [CREATOR, made.id]
    assert "test mode is off" in interaction.sent.lower()


async def test_setup_refuses_someone_who_is_not_staff(cog, bot, member):
    interaction = FakeInteraction(bot, member)

    await run_setup(interaction, None)

    assert bot.guild.created == []
    assert "staff only" in interaction.sent


async def test_setup_refuses_when_test_mode_cannot_see_its_channel(cog, bot, lead):
    bot.guard = FakeGuard()
    interaction = FakeInteraction(bot, lead)

    await run_setup(interaction, None)

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

    await run_setup(interaction, None)

    assert bot.guild.created == []
    assert creator.name == "join to create a channel"
    assert bot.store.get(GUILD, "tempvoice_creator_ids") == [CREATOR]
    assert "repaired" in interaction.sent
    assert "tempvoice.repair" in await action_kinds(db)


async def test_a_repair_that_discord_refuses_says_so_and_is_logged(cog, bot, lead, creator, db):
    creator.edit_raises = refused()
    interaction = FakeInteraction(bot, lead)

    await run_setup(interaction, None)

    assert "refused" in interaction.sent
    assert "tempvoice.repair_failed" in await action_kinds(db)


async def test_a_repair_names_the_other_lobbies_and_how_to_drop_them(cog, bot, lead, creator):
    second = bot.guild.add(FakeVoice(CREATOR + 1, bot.guild, name="join"))
    await bot.store.set(GUILD, "tempvoice_creator_ids", [CREATOR, second.id])
    interaction = FakeInteraction(bot, lead)

    await run_setup(interaction, None)

    assert f"<#{second.id}>" in interaction.sent and "Forget a lobby…" in interaction.sent
    assert second.name == "join"


async def test_test_mode_will_not_repair_a_lobby_outside_the_test_category(cog, bot, lead, creator):
    bot.guild.add(FakeText(TEST_CHANNEL, category=FakeCategory(50)))
    bot.guard = FakeGuard()
    interaction = FakeInteraction(bot, lead)

    await run_setup(interaction, None)

    assert creator.name == "join to create a channel"
    assert creator.edits == []
    assert "test mode" in interaction.sent.lower()


async def test_a_name_given_to_setup_is_remembered_as_the_setting(cog, bot, lead, creator):
    interaction = FakeInteraction(bot, lead)

    await run_setup(interaction, "Join Here")

    assert bot.store.get(GUILD, "tempvoice_creator_name") == "Join Here"
    assert creator.name == "Join Here"


async def test_forget_drops_a_creator_id_and_refuses_anything_else(cog, bot, lead, db):
    interaction = FakeInteraction(bot, lead)
    await run_forget_lobby(interaction, CREATOR)
    assert bot.store.get(GUILD, "tempvoice_creator_ids") == []
    assert "tempvoice.creator_removed" in await action_kinds(db)

    again = FakeInteraction(bot, lead)
    await run_forget_lobby(again, CREATOR)
    assert "not one of" in again.sent

    embed, view = await panel_for(bot, lead)
    assert "Forget a lobby…" not in labels(view)


async def test_forget_is_staff_only(cog, bot, member):
    interaction = FakeInteraction(bot, member)

    await run_forget_lobby(interaction, CREATOR)

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

    await run_setup(interaction, None)

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

    await run_setup(FakeInteraction(bot, lead), None)

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

    await run_setup(FakeInteraction(bot, lead), None)

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
    assert given[bot.guild.me].view_channel is True
    assert given[bot.guild.me].manage_channels is True


async def test_a_hidden_channel_still_lets_black_bloc_post_its_panel(cog, bot, member, db):
    category = FakeCategory(50)
    bot.guild.add(FakeText(TEST_CHANNEL, category=category))
    bot.guard = FakeGuard()
    creator = bot.guild.add(FakeVoice(CREATOR, bot.guild, category=category, position=1))
    await save_prefs(db, member.id, hidden=True, locked=True)

    await cog._maybe_create(member, creator)

    made = bot.guild.created[0]
    assert made.given_overwrites[bot.guild.default_role].view_channel is False
    assert made.given_overwrites[bot.guild.me].view_channel is True
    assert len(made.messages) == 1


async def test_an_allowed_role_that_no_longer_exists_is_left_out(cog, bot, lead):
    category = FakeCategory(50)
    bot.guild.add(FakeText(TEST_CHANNEL, category=category))
    bot.guard = FakeGuard()

    await run_setup(FakeInteraction(bot, lead), None)

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


def test_the_cog_carries_one_member_visible_command_and_no_group_at_all():
    found = list(TempVoice.__cog_app_commands__)

    assert [one.name for one in found] == ["voice"]
    assert not isinstance(found[0], app_commands.Group)
    assert found[0].default_permissions is None


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


async def test_the_rename_modal_changes_the_channel_the_caller_owns(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    _embed, view = await panel_for(bot, member)
    interaction = FakeInteraction(bot, member)

    await button(view, "Rename").callback(interaction)
    modal = interaction.response.modals[0]
    modal.name._value = "The Pit"
    submit = FakeInteraction(bot, member)
    await modal.on_submit(submit)

    assert isinstance(modal, RenameModal)
    assert made.name == "The Pit"
    assert (await get_prefs(db, member.id))["name"] == "The Pit"
    assert "tempvoice.rename" in await action_kinds(db)
    assert submit.response.messages[0].get("deferred") is True


async def test_someone_without_the_allowed_role_is_told_why_and_offered_nothing(
    cog, bot, creator, db
):
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo", roles=())

    embed, view = await panel_for(bot, stranger)

    assert f"<@&{MEMBER_ROLE_ID}>" in embed.description
    assert labels(view) == ["Refresh"]
    assert await action_kinds(db) == []


async def test_the_panel_says_how_to_get_a_channel_when_you_have_none(cog, bot, member):
    embed, view = await panel_for(bot, member)

    assert "don't own a temp channel" in embed.description
    assert "join to create a channel" in embed.description
    assert labels(view) == ["Refresh"]


async def test_voice_lock_and_unlock_call_the_same_helper_the_button_does(
    cog, bot, creator, member, db
):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]

    await act_on_own(FakeInteraction(bot, member), do_privacy, "connect", True)
    assert made.permissions[-1][1].connect is False
    assert (await get_prefs(db, member.id))["locked"] == 1

    again = FakeInteraction(bot, member)
    await act_on_own(again, do_privacy, "connect", True)
    assert "already locked" in again.sent
    assert len(made.permissions) == 1

    await act_on_own(FakeInteraction(bot, member), do_privacy, "connect", False)
    assert made.permissions[-1][1].connect is None
    kinds = await action_kinds(db)
    assert "tempvoice.lock" in kinds and "tempvoice.unlock" in kinds


async def test_voice_kick_moves_the_member_out_and_logs_it(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    stranger = connect(FakeMember(bot.guild, user_id=USER + 1, display_name="Bo"), made)

    await run_people_move(FakeInteraction(bot, member), do_kick, stranger)

    assert stranger.moves == [None]
    assert "tempvoice.kick" in await action_kinds(db)


async def test_voice_unban_clears_the_overwrite_ban_left(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    await run_people_move(FakeInteraction(bot, member), do_ban, stranger)
    made.overwrites[stranger] = discord.PermissionOverwrite(connect=False, view_channel=False)

    await run_people_move(FakeInteraction(bot, member), do_forget_member, stranger, "unban")

    assert made.permissions[-1][:2] == (stranger, None)
    kinds = await action_kinds(db)
    assert "tempvoice.ban" in kinds and "tempvoice.unban" in kinds


async def test_voice_claim_acts_on_the_channel_the_caller_is_in(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    made.members.clear()
    stranger = connect(FakeMember(bot.guild, user_id=USER + 1, display_name="Bo"), made)

    await run_claim(FakeInteraction(bot, stranger))

    assert (await get_row(db, made.id))["owner_id"] == stranger.id
    assert "tempvoice.claim" in await action_kinds(db)


async def test_voice_claim_needs_you_to_be_in_a_temp_channel(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    interaction = FakeInteraction(bot, stranger)

    await run_claim(interaction)

    assert "nothing to claim" in interaction.sent
    assert "tempvoice.claim" not in await action_kinds(db)


async def test_voice_bitrate_is_clamped_remembered_and_reused_next_time(
    cog, bot, creator, member, db
):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    interaction = FakeInteraction(bot, member)

    await act_on_own(interaction, do_bitrate, 96)

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

    await act_on_own(interaction, do_bitrate, 96)

    assert bot.guild.created[0].bitrate == 64000
    assert "64 kbps" in interaction.sent and "boost level" in interaction.sent


async def test_voice_region_sets_and_clears_the_rtc_region(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]

    await run_region(FakeInteraction(bot, member), "us-west")
    assert made.rtc_region == "us-west"

    auto = FakeInteraction(bot, member)
    await run_region(auto, "auto")
    assert made.rtc_region is None
    assert "automatic" in auto.sent
    assert (await action_kinds(db)).count("tempvoice.region") == 2


async def test_a_region_discord_refuses_says_which_one(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    made.edit_raises = refused()
    interaction = FakeInteraction(bot, member)

    await run_region(interaction, "atlantis")

    assert "atlantis" in interaction.sent
    assert "tempvoice.region_failed" in await action_kinds(db)


async def test_the_owner_card_reports_the_channel_s_own_state(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    banned = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    guest = FakeMember(bot.guild, user_id=USER + 2, display_name="Cass")
    made.overwrites[banned] = discord.PermissionOverwrite(connect=False)
    made.overwrites[guest] = discord.PermissionOverwrite(connect=True)
    made.user_limit = 4

    embed, _view = await panel_for(bot, member)

    said = embed.description
    assert f"**owner** — <@{member.id}>" in said
    assert "**limit** — 4 people" in said
    assert "**locked** — no" in said
    assert f"**let in by name** — <@{guest.id}>" in said
    assert f"**kept out by name** — <@{banned.id}>" in said


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


async def test_the_staff_block_shows_the_lobby_name_and_the_loop_s_health(cog, bot, lead):
    cog.last_ok_at = "2026-08-26T12:00:00+00:00"
    bot.cogs["TempVoice"] = cog

    embed, _view = await panel_for(bot, lead)

    assert "join to create a channel" in embed.description
    assert "2026-08-26T12:00:00+00:00" in embed.description
    assert "**last error** — none" in embed.description


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

    await run_setup(interaction, None)

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

    await run_setup(interaction, None)

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

    await run_setup(interaction, None)

    assert bot.store.get(GUILD, "tempvoice_creator_ids") == [lobby.id]
    assert "refused" in interaction.sent
    assert "tempvoice.repair_failed" in await action_kinds(db)


async def test_the_staff_block_names_the_lobbies_black_bloc_is_not_keeping_track_of(
    cog, bot, lead
):
    _, lobby = where_the_lobby_belongs(bot)

    embed, _view = await panel_for(bot, lead)

    assert f"<#{lobby.id}>" in embed.description
    assert "not kept track of" in embed.description
    assert "**Setup**" in embed.description


def test_a_stored_id_list_survives_junk_and_never_grows_forever():
    assert id_list('[1, "2", 2, null, "no"]') == [1, 2]
    assert id_list("not json") == [] and id_list(None) == [] and id_list('{"a": 1}') == []

    assert id_list(with_member('[7]', 8, True)) == [7, 8]
    assert id_list(with_member('[7, 8]', 8, False)) == [7]
    assert id_list(with_member('[8]', 8, True)) == [8]
    assert len(id_list(with_member(json.dumps(list(range(200))), 999, True))) == MEMBER_MEMORY_MAX


def test_the_remembered_lists_skip_the_owner_and_anyone_who_left():
    guild = FakeGuild()
    owner = FakeMember(guild, user_id=USER)
    guest = FakeMember(guild, user_id=USER + 1, display_name="Bo")
    shut_out = FakeMember(guild, user_id=USER + 2, display_name="Cass")

    found = apply_remembered_members(
        {}, guild, [guest.id, owner.id, 4242], [shut_out.id], owner.id
    )

    assert found[guest].connect is True and found[guest].view_channel is True
    assert found[shut_out].connect is False and found[shut_out].view_channel is False
    assert owner not in found and len(found) == 2


async def test_permit_and_ban_are_remembered_and_put_back_on_the_next_channel(
    cog, bot, creator, member, db
):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    guest = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    pest = FakeMember(bot.guild, user_id=USER + 2, display_name="Cass")

    await run_people_move(FakeInteraction(bot, member), do_permit, guest)
    await run_people_move(FakeInteraction(bot, member), do_ban, pest)

    prefs = await get_prefs(db, member.id)
    assert id_list(prefs["permitted_ids"]) == [guest.id]
    assert id_list(prefs["banned_ids"]) == [pest.id]

    made.members.clear()
    await cog._maybe_delete(bot.guild, made)
    await cog._maybe_create(member, creator)

    given = bot.guild.created[1].given_overwrites
    assert given[guest].connect is True
    assert given[pest].connect is False and given[pest].view_channel is False


async def test_unpermit_and_unban_are_forgotten_for_next_time_too(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    guest = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    pest = FakeMember(bot.guild, user_id=USER + 2, display_name="Cass")
    await run_people_move(FakeInteraction(bot, member), do_permit, guest)
    await run_people_move(FakeInteraction(bot, member), do_ban, pest)

    await run_people_move(FakeInteraction(bot, member), do_forget_member, guest, "unpermit")
    await run_people_move(FakeInteraction(bot, member), do_forget_member, pest, "unban")

    prefs = await get_prefs(db, member.id)
    assert id_list(prefs["permitted_ids"]) == [] and id_list(prefs["banned_ids"]) == []


async def test_a_remembered_region_is_used_for_the_next_channel(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]

    await run_region(FakeInteraction(bot, member), "us-west")

    assert (await get_prefs(db, member.id))["region"] == "us-west"

    made.members.clear()
    await cog._maybe_delete(bot.guild, made)
    await cog._maybe_create(member, creator)

    assert bot.guild.created[1].rtc_region == "us-west"

    await run_region(FakeInteraction(bot, member), "auto")
    second = bot.guild.created[1]
    second.members.clear()
    await cog._maybe_delete(bot.guild, second)
    await cog._maybe_create(member, creator)

    assert bot.guild.created[2].rtc_region is None


async def test_forgetting_the_settings_drops_everything_and_says_so(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    await act_on_own(FakeInteraction(bot, member), do_rename, "The Pit")
    nobody = FakeMember(bot.guild, user_id=USER + 5, display_name="Dee")

    _embed, view = await panel_for(bot, nobody)
    assert "Forget my settings" not in labels(view)

    interaction = FakeInteraction(bot, member)
    await run_forget_prefs(interaction)

    assert await get_prefs(db, member.id) is None
    assert "Forgotten" in interaction.sent
    assert "tempvoice.prefs_reset" in await action_kinds(db)
    assert bot.guild.created[0].name == "The Pit"


async def test_the_owner_card_says_what_is_remembered(cog, bot, creator, member, db):
    await cog._maybe_create(member, creator)
    guest = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    await run_people_move(FakeInteraction(bot, member), do_permit, guest)
    await run_region(FakeInteraction(bot, member), "us-west")

    embed, _view = await panel_for(bot, member)

    said = embed.description
    assert "remembered for next time" in said
    assert "us-west" in said and f"<@{guest.id}>" in said
    assert "**Forget my settings**" in said


def test_remembered_lines_say_so_when_nothing_is_remembered_yet():
    said = "\n".join(remembered_lines(None))

    assert "nothing yet" in said and "kept" in said


# --- the panel ------------------------------------------------------------------------------


class DatabaseDown:
    """The database dropping mid-panel, which a property cannot be set to."""

    def __init__(self, db):
        self.conn = db.conn
        self.is_connected = False


async def a_channel(cog, bot, creator, member):
    await bot.store.set(GUILD, "tempvoice_mode", "on")
    await cog._maybe_create(member, creator)
    made = bot.guild.created[0]
    connect(member, made)
    return made


async def test_the_command_answers_one_ephemeral_panel_and_nothing_else(cog, bot, member):
    interaction = FakeInteraction(bot, member)

    await cog.voice_panel.callback(cog, interaction)

    assert len(interaction.response.messages) == 1
    said = interaction.response.messages[0]
    assert said["ephemeral"] is True
    assert said["embed"].title == voice.PANEL_TITLE
    assert said["allowed_mentions"].everyone is False


async def test_the_command_refuses_a_direct_message_and_a_database_that_is_down(cog, bot, member):
    outside = FakeInteraction(bot, member, guild=False)
    await cog.voice_panel.callback(cog, outside)
    assert "server" in outside.sent

    bot.db = DatabaseDown(bot.db)
    down = FakeInteraction(bot, member)
    await cog.voice_panel.callback(cog, down)
    assert down.sent == DB_UNAVAILABLE
    assert down.response.messages[0].get("embed") is None


@pytest.mark.parametrize("mode", ["off", "on"])
@pytest.mark.parametrize("state", ["blocked", "none", "owner", "orphan", "guest"])
@pytest.mark.parametrize("staff", [False, True])
async def test_every_state_renders_exactly_its_row_of_the_button_table(
    cog, bot, creator, db, mode, state, staff
):
    """Checklist 3 and 12: the table is data, and no state may render a move it forbids."""
    actor = FakeMember(
        bot.guild,
        user_id=USER,
        roles=() if state == "blocked" else (MEMBER_ROLE_ID,),
        manage_guild=staff,
    )
    owner = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    if state == "owner":
        await a_channel(cog, bot, creator, actor)
    elif state in ("orphan", "guest"):
        made = await a_channel(cog, bot, creator, owner)
        made.members.clear()
        owner.voice = None
        connect(actor, made)
        if state == "guest":
            connect(owner, made)
    await bot.store.set(GUILD, "tempvoice_mode", mode)

    _embed, view = await panel_for(bot, actor)
    said = labels(view)

    wanted = [
        move.label
        for move in voice.card_buttons(
            state if state != "blocked" or not staff else "blocked",
            has_prefs=await get_prefs(db, actor.id) is not None,
            staff=staff,
            mode_on=mode == "on",
            has_lobbies=True,
        )
    ]
    assert said == wanted + ([SITE_BUTTON] if staff else [])


async def test_a_staffer_without_the_allowed_role_still_gets_the_staff_row_and_is_told_why(
    cog, bot
):
    lead = FakeMember(bot.guild, user_id=3, display_name="Lead", roles=(), manage_guild=True)

    embed, view = await panel_for(bot, lead)

    assert "Setup" in labels(view) and "Logs" in labels(view)
    assert f"<@&{MEMBER_ROLE_ID}>" in embed.description
    assert "Rename" not in labels(view)


async def test_a_member_is_never_offered_the_staff_half_or_the_site(cog, bot, creator, member):
    await a_channel(cog, bot, creator, member)

    _embed, view = await panel_for(bot, member)

    for staff_only in ("Setup", "Forget a lobby…", "Logs", SITE_BUTTON):
        assert staff_only not in labels(view)
    assert "Turn join-to-create off" not in labels(view)
    assert not [one for one in view.children if isinstance(one, ChannelPick)]


async def test_lock_and_unlock_are_one_button_that_says_what_it_will_do(
    cog, bot, creator, member, db
):
    made = await a_channel(cog, bot, creator, member)

    _embed, view = await panel_for(bot, member)
    assert "Lock" in labels(view) and "Unlock" not in labels(view)
    assert "Hide" in labels(view) and "Show" not in labels(view)

    await press(bot, member, view, "Lock")
    await press(bot, member, view, "Hide")

    _embed, again = await panel_for(bot, member)
    assert "Unlock" in labels(again) and "Lock" not in labels(again)
    assert "Show" in labels(again) and "Hide" not in labels(again)
    assert privacy_of(made) == (True, True)
    kinds = await action_kinds(db)
    assert "tempvoice.lock" in kinds and "tempvoice.hide" in kinds


async def test_claim_renders_only_where_the_owner_has_gone(cog, bot, creator, member, db):
    made = await a_channel(cog, bot, creator, member)
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")

    _embed, mine = await panel_for(bot, member)
    assert "Claim" not in labels(mine)

    connect(stranger, made)
    _embed, visiting = await panel_for(bot, stranger)
    assert "Claim" not in labels(visiting)

    made.members = [stranger]
    member.voice = None
    _embed, alone = await panel_for(bot, stranger)
    assert "Claim" in labels(alone)

    await press(bot, stranger, alone, "Claim")
    assert (await get_row(db, made.id))["owner_id"] == stranger.id
    assert "tempvoice.claim" in await action_kinds(db)


async def test_move_someone_out_is_absent_until_somebody_else_is_in_the_channel(
    cog, bot, creator, member
):
    made = await a_channel(cog, bot, creator, member)

    _embed, alone = await build_people(bot, bot.guild, member)
    assert voice.PICK_KICK not in placeholders(alone)

    connect(FakeMember(bot.guild, user_id=USER + 1, display_name="Bo"), made)
    _embed, crowded = await build_people(bot, bot.guild, member)
    assert voice.PICK_KICK in placeholders(crowded)


async def test_undo_for_carries_the_right_word_for_each_name_and_is_absent_with_none(
    cog, bot, creator, member, db
):
    made = await a_channel(cog, bot, creator, member)
    guest = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    pest = FakeMember(bot.guild, user_id=USER + 2, display_name="Cass")

    _embed, empty = await build_people(bot, bot.guild, member)
    assert voice.PICK_UNDO not in placeholders(empty)

    made.overwrites[guest] = discord.PermissionOverwrite(connect=True)
    made.overwrites[pest] = discord.PermissionOverwrite(connect=False)
    _embed, view = await build_people(bot, bot.guild, member)
    undo = picker(view, UndoPick)

    assert {one.value for one in undo.options} == {
        f"unpermit:{guest.id}",
        f"unban:{pest.id}",
    }
    assert "let them back in" in next(
        one.label for one in undo.options if one.value.startswith("unban")
    )

    await choose(bot, member, view, UndoPick, f"unban:{pest.id}")
    assert "tempvoice.unban" in await action_kinds(db)


async def test_the_region_select_holds_every_named_region_and_automatic_is_its_own_button(
    cog, bot, creator, member, db
):
    made = await a_channel(cog, bot, creator, member)
    _embed, panel = await panel_for(bot, member)
    opened = await press(bot, member, panel, "Region…")
    view = opened.view

    assert len(picker(view, RegionPick).options) == 25
    assert "auto" not in [one.value for one in picker(view, RegionPick).options]

    await choose(bot, member, view, RegionPick, "us-west")
    assert made.rtc_region == "us-west"

    back = await press(bot, member, view, "Automatic")
    assert made.rtc_region is None
    assert "automatic" in back.sent


async def test_hand_it_over_moves_the_stored_owner_through_the_shared_function(
    cog, bot, creator, member, db
):
    made = await a_channel(cog, bot, creator, member)
    friend = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    _embed, panel = await panel_for(bot, member)

    opened = await press(bot, member, panel, "Hand it over…")
    handed = await choose(bot, member, opened.view, NewOwnerPick, friend)

    assert (await get_row(db, made.id))["owner_id"] == friend.id
    assert "tempvoice.transfer" in await action_kinds(db)
    assert friend.display_name in handed.sent
    assert member.dms == []


async def test_staff_can_reassign_any_open_channel_and_the_displaced_owner_is_told(
    cog, bot, creator, member, lead, db
):
    made = await a_channel(cog, bot, creator, member)
    friend = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    _embed, panel = await panel_for(bot, lead)

    card = await choose(bot, lead, panel, ChannelPick, made.id)
    opened = await press(bot, lead, card.view, "Hand it over…")
    await choose(bot, lead, opened.view, NewOwnerPick, friend)

    assert (await get_row(db, made.id))["owner_id"] == friend.id
    assert member.dms and friend.display_name in member.dms[0]
    assert "tempvoice.transfer" in await action_kinds(db)


async def test_a_staffer_demoted_while_a_card_is_open_moves_nothing(cog, bot, lead, db):
    _embed, view = await panel_for(bot, lead)
    bot.store.is_staff = lambda who: False

    for label in ("Setup", "Turn join-to-create off", "Forget a lobby…"):
        refused = await press(bot, lead, view, label)
        assert "staff only" in refused.sent

    assert bot.store.get(GUILD, "tempvoice_mode") == "on"
    assert await action_kinds(db) == []


async def test_the_mode_button_says_what_it_will_do_and_logs_which_door_asked(cog, bot, lead, db):
    _embed, view = await panel_for(bot, lead)
    assert "Turn join-to-create off" in labels(view)

    said = await press(bot, lead, view, "Turn join-to-create off")

    assert bot.store.get(GUILD, "tempvoice_mode") == "off"
    assert "off" in said.sent
    assert "tempvoice.mode" in await action_kinds(db)
    _embed, again = await panel_for(bot, lead)
    assert "Turn join-to-create on" in labels(again)


async def test_setup_defers_before_it_creates_a_channel(cog, bot, lead):
    await bot.store.set(GUILD, "tempvoice_creator_ids", [])
    _embed, view = await panel_for(bot, lead)

    opened = await press(bot, lead, view, "Setup")
    modal = opened.response.modals[0]
    assert isinstance(modal, SetupModal)
    assert modal.name.default == TEMPVOICE_CREATOR_NAME

    modal.name._value = "Join Here"
    submit = FakeInteraction(bot, lead)
    await modal.on_submit(submit)

    assert submit.response.messages[0].get("deferred") is True
    assert bot.store.get(GUILD, "tempvoice_creator_name") == "Join Here"
    assert bot.guild.created


async def test_forget_a_lobby_drops_it_from_the_list_and_says_so(cog, bot, lead, creator, db):
    _embed, view = await panel_for(bot, lead)

    opened = await press(bot, lead, view, "Forget a lobby…")
    dropped = await choose(bot, lead, opened.view, LobbyPick, CREATOR)

    assert bot.store.get(GUILD, "tempvoice_creator_ids") == []
    assert str(CREATOR) in dropped.sent
    assert "tempvoice.creator_removed" in await action_kinds(db)


async def test_the_limit_and_bitrate_modals_refuse_what_discord_would(
    cog, bot, creator, member, db
):
    await a_channel(cog, bot, creator, member)
    before = await action_kinds(db)

    limit = LimitModal(previous=object())
    limit.limit._value = "nope"
    said = FakeInteraction(bot, member)
    await limit.on_submit(said)
    assert "between 0 and 99" in said.sent

    bitrate = BitrateModal(previous=object())
    bitrate.kbps._value = "loud"
    told = FakeInteraction(bot, member)
    await bitrate.on_submit(told)
    assert "8" in told.sent and "96" in told.sent
    assert await action_kinds(db) == before


async def test_the_bitrate_modal_writes_through_the_shared_function(cog, bot, creator, member, db):
    made = await a_channel(cog, bot, creator, member)
    _embed, view = await panel_for(bot, member)

    opened = await press(bot, member, view, "Bitrate")
    modal = opened.response.modals[0]
    modal.kbps._value = "96"
    await modal.on_submit(FakeInteraction(bot, member))

    assert made.bitrate == 96000
    assert (await get_prefs(db, member.id))["bitrate"] == 96000
    assert "tempvoice.bitrate" in await action_kinds(db)


async def test_the_limit_modal_writes_through_the_shared_function(cog, bot, creator, member, db):
    made = await a_channel(cog, bot, creator, member)
    _embed, view = await panel_for(bot, member)

    opened = await press(bot, member, view, "Limit")
    modal = opened.response.modals[0]
    modal.limit._value = "4"
    await modal.on_submit(FakeInteraction(bot, member))

    assert made.user_limit == 4
    assert "tempvoice.limit" in await action_kinds(db)


async def test_logs_answers_a_new_message_and_still_refuses_a_demoted_staffer(cog, bot, lead):
    _embed, view = await panel_for(bot, lead)

    shown = await press(bot, lead, view, "Logs")
    assert shown.edits == []
    assert shown.response.messages[-1]["embed"] is not None

    bot.store.is_staff = lambda who: False
    lead.guild_permissions = FakePerms(manage_guild=False)
    refused = await press(bot, lead, view, "Logs")
    assert "staff only" in refused.sent


async def test_every_click_re_checks_the_database_after_its_own_defer(
    cog, bot, creator, member, db
):
    await a_channel(cog, bot, creator, member)
    _embed, view = await panel_for(bot, member)
    bot.db = DatabaseDown(bot.db)

    interaction = FakeInteraction(bot, member)
    await button(view, "Refresh").callback(interaction)

    assert interaction.response.messages[0].get("deferred") is True
    assert interaction.sent == DB_UNAVAILABLE
    assert interaction.edits == []


async def test_a_re_render_retires_the_view_it_replaced_and_a_timeout_disables_every_item(
    cog, bot, creator, member
):
    await a_channel(cog, bot, creator, member)
    _embed, view = await panel_for(bot, member)

    interaction = await press(bot, member, view, "Refresh")

    assert view.replaced is True and view.is_finished()
    fresh = interaction.view
    assert fresh.replaced is False

    fresh.message = FakeMessage(1, "", embed=discord.Embed(title="x"))
    fresh.last_interaction = interaction
    await fresh.on_timeout()

    assert all(item.disabled for item in fresh.children if hasattr(item, "disabled"))
    assert interaction.edits[-1]["embeds"][0].footer.text == voice.PANEL_TIMEOUT_FOOTER


async def test_a_move_on_a_channel_that_was_handed_away_mid_card_changes_nothing(
    cog, bot, creator, member, db
):
    made = await a_channel(cog, bot, creator, member)
    _embed, view = await panel_for(bot, member)
    friend = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")
    await set_owner(db, made.id, friend.id)

    interaction = await press(bot, member, view, "Lock")

    assert "not yours any more" in interaction.sent
    assert made.permissions == []


async def details_for(db, kind):
    cur = await db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id DESC LIMIT 1", (kind,)
    )
    row = await cur.fetchone()
    return json.loads(row["details"]) if row is not None else None


async def test_the_bitrate_modal_bounds_what_the_range_used_to(cog, bot, creator, member, db):
    """Checklist 22: a modal has no `app_commands.Range`, so it has to say no itself."""
    made = await a_channel(cog, bot, creator, member)
    before = await action_kinds(db)

    for given in ("0", "500", "-8"):
        modal = BitrateModal(previous=object())
        modal.kbps._value = given
        told = FakeInteraction(bot, member)
        await modal.on_submit(told)
        assert "8" in told.sent and "96" in told.sent

    assert await action_kinds(db) == before
    assert made.bitrate == 0


async def test_every_panel_move_leaves_a_discord_row_and_never_a_website_one(
    cog, bot, creator, member, lead, db
):
    """Checklist 34: the panel writes nothing itself, so `via` stays at its Discord default."""
    await a_channel(cog, bot, creator, member)
    _embed, view = await panel_for(bot, member)
    await press(bot, member, view, "Lock")
    _embed, staff = await panel_for(bot, lead)
    await press(bot, lead, staff, "Turn join-to-create off")

    kinds = await action_kinds(db)
    assert not [one for one in kinds if one.startswith("web.")]
    assert (await details_for(db, "tempvoice.lock"))["via"] == "discord"
    assert (await details_for(db, "tempvoice.mode"))["via"] == "discord"


def test_every_view_and_modal_answers_its_own_errors(cog):
    """Checklist 8 and 30: components never reach `tree.on_error`."""
    for shape in (VoicePanel, RenameModal, LimitModal, BitrateModal, SetupModal, TempVoicePanel):
        assert issubclass(shape, AnswersErrors), shape.__name__
