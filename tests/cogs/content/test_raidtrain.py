from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import discord
import pytest

from black_bloc import raidtrain as rt
from black_bloc.cogs.content import raidtrain as cog_module
from black_bloc.cogs.content.raidtrain import (
    NOT_AN_ORGANIZER,
    RaidTrains,
    assign_slot,
    counts,
    create_train,
    get_train,
    list_trains,
    slots_for,
    slots_of_member,
    take_slot,
    twitch_login_of,
)
from black_bloc.config import load_settings
from black_bloc.events import ZONE_PANEL_TITLE
from black_bloc.raidtrain import CANCELLED, DONE, LIVE, LOCKED, NEEDS_LINK, OPEN
from black_bloc.settings_store import RAIDTRAIN_SCHEDULED_NAME_KEY, SettingsStore
from black_bloc.storage.db import Database
from black_bloc.timezones import get_timezone
from black_bloc.when_picker import (
    DAY_PLACEHOLDER,
    HOUR_PLACEHOLDER,
    LATER_VALUE,
    MINUTE_PLACEHOLDER,
    ZONE_PLACEHOLDER,
    WhenDraft,
    parse_day,
)

GUILD = 7
TEST_CHANNEL = 111
RAID_CHANNEL = 333
ORGANIZER = 500
ALICE = 901
BOB = 902
CARL = 903
START = datetime(2026, 9, 14, 19, 0, tzinfo=UTC)


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id
        self.name = f"role-{role_id}"
        self.mention = f"<@&{role_id}>"


class FakeMessage:
    def __init__(self, message_id, channel):
        self.id = message_id
        self.channel = channel
        self.content = None
        self.threads = []

    async def edit(self, content=None, **kwargs):
        self.content = content

    async def create_thread(self, name=None, **kwargs):
        thread = SimpleNamespace(id=self.id + 1, name=name)
        self.threads.append(thread)
        return thread


class FakeChannel:
    def __init__(self, channel_id):
        self.id = channel_id
        self.mention = f"<#{channel_id}>"
        self.posts = []
        self.messages = {}

    async def send(self, content=None, **kwargs):
        message = FakeMessage(9000 + len(self.posts), self)
        message.content = content
        self.posts.append({"content": content, **kwargs})
        self.messages[message.id] = message
        return message

    async def fetch_message(self, message_id):
        return self.messages[int(message_id)]


class FakeMember:
    def __init__(self, guild, user_id, name="Casey", *, staff=False):
        self.id = user_id
        self.guild = guild
        self.display_name = name
        self.name = name.lower()
        self.mention = f"<@{user_id}>"
        self.bot = False
        self.roles = []
        self.guild_permissions = SimpleNamespace(manage_guild=staff)
        self.dms = []
        self.refuse_dm = False
        guild.members[user_id] = self

    async def send(self, content=None, **kwargs):
        if self.refuse_dm:
            raise RuntimeError("cannot send messages to this user")
        self.dms.append(content)


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black Bloc"
        self.channels = {}
        self.members = {}
        self.roles = []
        self.unavailable = False
        self.scheduled = []

    async def create_scheduled_event(self, **kwargs):
        made = SimpleNamespace(id=7700 + len(self.scheduled), **kwargs)
        self.scheduled.append(made)
        return made

    def add(self, channel):
        self.channels[channel.id] = channel
        return channel

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_member(self, user_id):
        return self.members.get(user_id)


class FakeGuard:
    def __init__(self, allowed):
        self.allowed = set(allowed)

    def allows_channel(self, channel_id):
        return int(channel_id) in self.allowed

    def own_channel(self, channel):
        self.allowed.add(int(getattr(channel, "id", channel)))


class FakeBot:
    def __init__(self, db, store, guild, settings):
        self.db = db
        self.store = store
        self.guild = guild
        self.guilds = [guild]
        self.settings = settings
        self.guard = None
        self.cogs = {}

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def get_user(self, user_id):
        return self.guild.get_member(user_id)

    def get_cog(self, name):
        return self.cogs.get(name)


class PanelMessage:
    def __init__(self, message_id, **kwargs):
        self.id = message_id
        self.kwargs = kwargs

    async def edit(self, **kwargs):
        self.kwargs |= kwargs

    @property
    def embeds(self):
        one = self.kwargs.get("embed")
        return [one] if one is not None else list(self.kwargs.get("embeds") or ())


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.modals = []
        self.deferred = False

    def is_done(self):
        return self.deferred or bool(self.messages)

    async def defer(self, ephemeral=False):
        self.deferred = True

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def send_modal(self, modal):
        self.modals.append(modal)
        self.deferred = True


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
        self.edits = []

    async def original_response(self):
        return PanelMessage(1)

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return PanelMessage(9500, **kwargs)

    @property
    def rendered(self):
        if self.edits:
            return self.edits[-1]
        return self.response.messages[-1] if self.response.messages else {}

    @property
    def view(self):
        return self.rendered.get("view")

    @property
    def embed(self):
        return self.rendered.get("embed")

    @property
    def sent(self):
        spoken = [
            one["content"] for one in self.response.messages if one.get("content") is not None
        ]
        return spoken[-1] if spoken else None


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", TEST_CHANNEL)
    await store.set(GUILD, "raidtrain_channel_id", TEST_CHANNEL)
    await store.set(GUILD, "raidtrain_mode", "on")
    guild = FakeGuild()
    for channel_id in (TEST_CHANNEL, RAID_CHANNEL):
        guild.add(FakeChannel(channel_id))
    return FakeBot(db, store, guild, settings)


@pytest.fixture
def cog(bot):
    made = RaidTrains(bot)
    bot.cogs["RaidTrains"] = made
    return made


@pytest.fixture
def organizer(bot):
    return FakeMember(bot.guild, ORGANIZER, "Robin", staff=True)


@pytest.fixture
def alice(bot):
    return FakeMember(bot.guild, ALICE, "Alice")


@pytest.fixture
def bobby(bot):
    return FakeMember(bot.guild, BOB, "Bob")


async def link(db, user_id, login):
    await db.conn.execute(
        "INSERT OR REPLACE INTO golive_links(user_id, twitch_login, linked_at) VALUES (?, ?, ?)",
        (user_id, login, "2026-09-01T00:00:00+00:00"),
    )
    await db.conn.commit()


async def a_train(db, *, starts=START, count=3, minutes=60):
    return await create_train(
        db,
        GUILD,
        ORGANIZER,
        title="Saturday train",
        description="Everyone welcome.",
        starts_at=starts,
        slot_minutes=minutes,
        slot_count=count,
    )


async def kinds_logged(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def open_session(db, user_id, *, ended=None):
    await db.conn.execute(
        "INSERT INTO golive_sessions(guild_id, user_id, source, started_at, ended_at, mode) "
        "VALUES (?, ?, 'twitch', ?, ?, 'on')",
        (GUILD, user_id, START.isoformat(), ended),
    )
    await db.conn.commit()


async def seat(bot, train_id, member, position, *, by=None):
    """The organizer door, used as a fixture: it is the shared function, not a command."""
    train = await get_train(bot.db, GUILD, train_id)
    login = await twitch_login_of(bot.db, member.id)
    return await assign_slot(
        bot, bot.guild, by or member, train, position, member, login
    )


# --- panel helpers -------------------------------------------------------------------------------


def labels(view):
    return [one.label for one in view.children if getattr(one, "label", None)]


def placeholders(view):
    return [
        one.placeholder for one in view.children if getattr(one, "placeholder", None) is not None
    ]


def button(view, label):
    return next(one for one in view.children if getattr(one, "label", None) == label)


def picker(view, placeholder):
    return next(one for one in view.children if getattr(one, "placeholder", None) == placeholder)


def options(interaction, placeholder):
    return [one.value for one in picker(interaction.view, placeholder).options]


async def press(interaction, label):
    await button(interaction.view, label).callback(interaction)


async def pick_one(interaction, placeholder, value):
    control = picker(interaction.view, placeholder)
    control._values = [value]
    await control.callback(interaction)


async def open_the_panel(cog, bot, who):
    interaction = FakeInteraction(bot, who)
    await RaidTrains.raidtrain_panel_command.callback(cog, interaction)
    return interaction


async def open_the_card(cog, bot, who, train_id):
    """The select is one door onto the card; a finished train is only reachable this way."""
    interaction = await open_the_panel(cog, bot, who)
    await cog_module.open_card(interaction, train_id, interaction.view)
    return interaction


def db_is_down(monkeypatch):
    monkeypatch.setattr(Database, "is_connected", property(lambda self: False))


# --- storage -------------------------------------------------------------------------------------


async def test_a_new_train_gets_every_slot_at_once(db):
    train_id = await a_train(db, count=4)
    slots = await slots_for(db, train_id)
    assert [row["position"] for row in slots] == [1, 2, 3, 4]
    assert slots[0]["starts_at"] == START.isoformat()
    assert slots[1]["starts_at"] == (START + timedelta(hours=1)).isoformat()
    assert all(row["user_id"] is None for row in slots)
    train = await get_train(db, GUILD, train_id)
    assert train["status"] == OPEN
    assert (await counts(db, GUILD))["slots"] == 4


async def test_a_train_from_another_server_is_not_found(db):
    train_id = await a_train(db)
    assert await get_train(db, GUILD + 1, train_id) is None


async def test_the_second_claim_on_one_slot_loses(db):
    train_id = await a_train(db)
    slot = (await slots_for(db, train_id))[0]
    assert await take_slot(db, slot["id"], ALICE, "alice", None) is True
    assert await take_slot(db, slot["id"], BOB, "bob", None) is False
    assert (await slots_for(db, train_id))[0]["user_id"] == ALICE


async def test_the_lists_split_what_is_coming_from_what_is_over(db):
    soon = await a_train(db)
    over = await a_train(db, starts=START - timedelta(days=7))
    await db.conn.execute("UPDATE raid_trains SET status = ? WHERE id = ?", (DONE, over))
    await db.conn.commit()
    assert [row["id"] for row in await list_trains(db, GUILD, scope="upcoming")] == [soon]
    assert [row["id"] for row in await list_trains(db, GUILD, scope="past")] == [over]
    assert len(await list_trains(db, GUILD, scope="all")) == 2


async def test_the_slots_a_member_holds_carry_their_trains_title(db):
    train_id = await a_train(db)
    slot = (await slots_for(db, train_id))[1]
    await take_slot(db, slot["id"], ALICE, "alice", None)
    held = await slots_of_member(db, GUILD, ALICE)
    assert [row["position"] for row in held] == [2]
    assert held[0]["train_title"] == "Saturday train"


async def test_a_twitch_login_is_read_from_the_go_live_link(db):
    await link(db, ALICE, "alicestreams")
    assert await twitch_login_of(db, ALICE) == "alicestreams"
    assert await twitch_login_of(db, BOB) is None


# --- the root ------------------------------------------------------------------------------------


async def test_the_command_opens_one_ephemeral_panel(bot, cog, alice, db):
    await a_train(db)
    interaction = await open_the_panel(cog, bot, alice)
    assert interaction.rendered["ephemeral"] is True
    assert "Saturday train" in interaction.embed.description
    assert "A train…" in placeholders(interaction.view)
    assert labels(interaction.view) == ["Refresh"]


async def test_the_panel_outside_a_server_says_so_rather_than_failing(bot, cog, alice):
    interaction = FakeInteraction(bot, alice)
    interaction.guild = None
    await RaidTrains.raidtrain_panel_command.callback(cog, interaction)
    assert "server" in interaction.sent
    assert interaction.view is None


async def test_the_panel_says_so_when_the_database_is_down(bot, cog, alice, monkeypatch):
    db_is_down(monkeypatch)
    interaction = await open_the_panel(cog, bot, alice)
    assert "database" in interaction.sent.lower()
    assert interaction.view is None


async def test_the_panel_still_opens_while_raid_trains_are_off(bot, cog, alice, db):
    await bot.store.set(GUILD, "raidtrain_mode", "off")
    await a_train(db)
    interaction = await open_the_panel(cog, bot, alice)
    assert "**off**" in interaction.embed.description
    assert "nothing new can be started" in interaction.embed.description
    assert labels(interaction.view) == ["Refresh"]
    assert "Mode…" not in placeholders(interaction.view)


async def test_the_mode_off_panel_still_gives_staff_the_mode_select(bot, cog, organizer):
    """`/raidtrains mode` is gone, so this select is the ONLY door back to `on`."""
    await bot.store.set(GUILD, "raidtrain_mode", "off")
    interaction = await open_the_panel(cog, bot, organizer)
    assert "Mode…" in placeholders(interaction.view)
    assert labels(interaction.view) == ["Setup…", "Logs", "Refresh", "Open on the site"]


async def test_a_shadow_panel_renders_exactly_like_an_on_one_plus_a_line(bot, cog, organizer, db):
    await a_train(db)
    live = await open_the_panel(cog, bot, organizer)
    await bot.store.set(GUILD, "raidtrain_mode", "shadow")
    quiet = await open_the_panel(cog, bot, organizer)
    assert labels(quiet.view) == labels(live.view)
    assert placeholders(quiet.view) == placeholders(live.view)
    assert "held back" in quiet.embed.description
    assert "held back" not in live.embed.description


async def test_a_member_never_reaches_the_staff_half(bot, cog, alice, db):
    await a_train(db)
    interaction = await open_the_panel(cog, bot, alice)
    said = labels(interaction.view)
    assert "Setup…" not in said and "Logs" not in said
    assert "Open on the site" not in said
    assert "Mode…" not in placeholders(interaction.view)


async def test_a_non_organizer_is_never_offered_start_a_raid_train(bot, cog, alice, organizer):
    assert "Start a raid train" not in labels((await open_the_panel(cog, bot, alice)).view)
    assert "Start a raid train" in labels((await open_the_panel(cog, bot, organizer)).view)


async def test_the_organizer_role_stands_in_for_staff(bot, cog, alice):
    role = FakeRole(4242)
    await bot.store.set(GUILD, "raidtrain_organizer_role_id", role.id)
    assert cog.is_organizer(alice) is False
    alice.roles = [role]
    assert cog.is_organizer(alice) is True
    assert "Start a raid train" in labels((await open_the_panel(cog, bot, alice)).view)


async def test_staff_read_the_sweeps_health_on_the_root_rather_than_behind_a_button(
    bot, cog, organizer, db
):
    await a_train(db)
    interaction = await open_the_panel(cog, bot, organizer)
    said = interaction.embed.description
    assert "The sweep runs every 5 minute(s)" in said
    assert "1 train(s), 1 still to come" in said
    assert f"<#{TEST_CHANNEL}>" in said


async def test_my_slots_only_renders_when_the_caller_holds_one(bot, cog, alice, db):
    train_id = await a_train(db)
    assert "My slots…" not in labels((await open_the_panel(cog, bot, alice)).view)
    await take_slot(db, (await slots_for(db, train_id))[1]["id"], ALICE, "alice", None)
    held = await open_the_panel(cog, bot, alice)
    assert "My slots…" in labels(held.view)
    await press(held, "My slots…")
    assert "slot #2" in held.embed.description
    assert labels(held.view) == ["Back"]


async def test_my_slots_says_so_when_there_is_nothing_and_the_train_select_opens_a_card(
    bot, cog, alice, db
):
    train_id = await a_train(db)
    await take_slot(db, (await slots_for(db, train_id))[0]["id"], ALICE, "alice", None)
    interaction = await open_the_panel(cog, bot, alice)
    await press(interaction, "My slots…")
    await pick_one(interaction, "A train…", str(train_id))
    assert "Saturday train" in interaction.embed.description
    assert "Back" in labels(interaction.view)


# --- the card ------------------------------------------------------------------------------------


async def test_the_train_select_opens_the_card_the_room_reads(bot, cog, alice, db):
    train_id = await a_train(db)
    interaction = await open_the_panel(cog, bot, alice)

    await pick_one(interaction, "A train…", str(train_id))

    assert "**Saturday train** — raid train" in interaction.embed.description
    assert "0/3 slot(s) filled" in interaction.embed.description
    assert labels(interaction.view) == ["Back", "Refresh"]

    await press(interaction, "Back")
    assert "A train…" in placeholders(interaction.view)


async def test_a_train_that_vanished_lands_back_on_the_root_in_words(bot, cog, alice, db):
    train_id = await a_train(db)
    interaction = await open_the_panel(cog, bot, alice)
    await db.conn.execute("DELETE FROM raid_trains WHERE id = ?", (train_id,))
    await db.conn.commit()
    await pick_one(interaction, "A train…", str(train_id))
    assert "no raid train" in interaction.sent
    assert "Refresh" in labels(interaction.view)


async def test_an_unlinked_member_gets_a_line_and_never_a_greyed_button(bot, cog, alice, db):
    train_id = await a_train(db)
    interaction = await open_the_card(cog, bot, alice, train_id)
    assert "Take an hour…" not in placeholders(interaction.view)
    assert NEEDS_LINK in [field.value for field in interaction.embed.fields]
    assert "**Link my Twitch channel**" in interaction.embed.fields[0].value


async def test_the_link_requirement_can_be_turned_off(bot, cog, alice, db):
    await bot.store.set(GUILD, "raidtrain_require_link", False)
    train_id = await a_train(db)
    interaction = await open_the_card(cog, bot, alice, train_id)
    assert "Take an hour…" in placeholders(interaction.view)
    assert interaction.embed.fields == []


async def test_taking_an_hour_edits_the_lineup_and_then_the_cap_removes_the_control(
    bot, cog, alice, db
):
    await link(db, ALICE, "alicestreams")
    bot.guard = FakeGuard([TEST_CHANNEL])
    train_id = await a_train(db)
    await cog.publish_lineup(bot.guild, train_id)
    channel = bot.guild.get_channel(TEST_CHANNEL)

    interaction = await open_the_card(cog, bot, alice, train_id)
    assert options(interaction, "Take an hour…") == ["1", "2", "3"]
    await pick_one(interaction, "Take an hour…", "1")

    assert "Slot **#1**" in interaction.sent
    slots = await slots_for(db, train_id)
    assert slots[0]["user_id"] == ALICE and slots[0]["twitch_login"] == "alicestreams"
    assert "raidtrain.claim" in await kinds_logged(db)
    assert len(channel.posts) == 1
    assert "alicestreams" in channel.messages[9000].content
    assert "Take an hour…" not in placeholders(interaction.view)
    assert "Give back slot #1" in labels(interaction.view)


async def test_a_slot_somebody_took_first_is_refused_in_words(bot, cog, alice, bobby, db):
    await link(db, ALICE, "alicestreams")
    await link(db, BOB, "bobstreams")
    train_id = await a_train(db)
    interaction = await open_the_card(cog, bot, bobby, train_id)
    await take_slot(db, (await slots_for(db, train_id))[0]["id"], ALICE, "alicestreams", None)

    await pick_one(interaction, "Take an hour…", "1")

    assert "already belongs to someone else" in interaction.sent
    assert (await slots_for(db, train_id))[0]["user_id"] == ALICE


async def test_the_ceiling_can_be_lifted_and_then_the_button_becomes_a_select(
    bot, cog, alice, db
):
    await bot.store.set(GUILD, "raidtrain_max_slots_per_member", 0)
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db)
    interaction = await open_the_card(cog, bot, alice, train_id)
    await pick_one(interaction, "Take an hour…", "1")
    await pick_one(interaction, "Take an hour…", "2")
    assert [row["user_id"] for row in await slots_for(db, train_id)] == [ALICE, ALICE, None]
    said = labels(interaction.view)
    assert "Give an hour back…" in said
    assert not any(one.startswith("Give back slot") for one in said)


async def test_giving_one_hour_back_reads_its_number_and_opens_it_again(bot, cog, alice, db):
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db)
    interaction = await open_the_card(cog, bot, alice, train_id)
    await pick_one(interaction, "Take an hour…", "2")
    assert "Give back slot #2" in labels(interaction.view)

    await press(interaction, "Give back slot #2")

    assert "open again" in interaction.sent
    assert (await slots_for(db, train_id))[1]["user_id"] is None
    assert "raidtrain.release" in await kinds_logged(db)


async def test_giving_an_hour_back_from_the_sub_panel_lands_on_the_card(bot, cog, alice, db):
    await bot.store.set(GUILD, "raidtrain_max_slots_per_member", 0)
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db)
    interaction = await open_the_card(cog, bot, alice, train_id)
    await pick_one(interaction, "Take an hour…", "1")
    await pick_one(interaction, "Take an hour…", "3")

    await press(interaction, "Give an hour back…")
    assert options(interaction, "Which hour…") == ["1", "3"]
    await pick_one(interaction, "Which hour…", "3")

    assert "open again" in interaction.sent
    assert [row["user_id"] for row in await slots_for(db, train_id)] == [ALICE, None, None]
    assert "**Saturday train** — raid train" in interaction.embed.description


@pytest.mark.parametrize("status", [LOCKED, LIVE, DONE, CANCELLED])
async def test_no_claim_control_survives_the_train_leaving_open(bot, cog, alice, db, status):
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db)
    await db.conn.execute("UPDATE raid_trains SET status = ? WHERE id = ?", (status, train_id))
    await db.conn.commit()
    interaction = await open_the_card(cog, bot, alice, train_id)
    assert "Take an hour…" not in placeholders(interaction.view)
    assert not any(one.startswith("Give back slot") for one in labels(interaction.view))


async def test_lock_and_open_are_one_button_and_never_both(bot, cog, organizer, db):
    train_id = await a_train(db)
    interaction = await open_the_card(cog, bot, organizer, train_id)
    assert "Lock the lineup" in labels(interaction.view)
    assert "Open it for sign-ups" not in labels(interaction.view)

    await press(interaction, "Lock the lineup")

    assert "is locked" in interaction.sent
    assert (await get_train(db, GUILD, train_id))["status"] == LOCKED
    assert "Open it for sign-ups" in labels(interaction.view)
    assert "Lock the lineup" not in labels(interaction.view)

    await press(interaction, "Open it for sign-ups")
    assert (await get_train(db, GUILD, train_id))["status"] == OPEN
    assert {"raidtrain.lock", "raidtrain.unlock"} <= set(await kinds_logged(db))


async def test_a_live_train_offers_an_organizer_no_move_at_all(bot, cog, organizer, db):
    train_id = await a_train(db)
    await db.conn.execute("UPDATE raid_trains SET status = ? WHERE id = ?", (LIVE, train_id))
    await db.conn.commit()
    interaction = await open_the_card(cog, bot, organizer, train_id)
    assert labels(interaction.view) == ["Back", "Refresh"]


async def test_take_somebody_off_lists_only_the_hours_that_are_taken(
    bot, cog, organizer, alice, db
):
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db)
    empty = await open_the_card(cog, bot, organizer, train_id)
    assert "Take somebody off…" not in placeholders(empty.view)

    await seat(bot, train_id, alice, 2, by=organizer)
    interaction = await open_the_card(cog, bot, organizer, train_id)

    assert options(interaction, "Take somebody off…") == ["2"]
    assert "Alice" in picker(interaction.view, "Take somebody off…").options[0].label
    await pick_one(interaction, "Take somebody off…", "2")
    assert "open again" in interaction.sent
    assert (await slots_for(db, train_id))[1]["user_id"] is None
    assert "raidtrain.unassign" in await kinds_logged(db)


async def test_a_member_is_never_offered_an_organizer_move(bot, cog, alice, bobby, db):
    await link(db, BOB, "bobstreams")
    train_id = await a_train(db)
    await seat(bot, train_id, bobby, 1)
    interaction = await open_the_card(cog, bot, alice, train_id)
    said = labels(interaction.view)
    assert said == ["Back", "Refresh"]
    assert "Take somebody off…" not in placeholders(interaction.view)


async def test_no_row_on_a_rendered_card_carries_more_than_five_controls(
    bot, cog, organizer, db
):
    await link(db, ORGANIZER, "robinstreams")
    train_id = await a_train(db, count=4)
    interaction = await open_the_card(cog, bot, organizer, train_id)
    await pick_one(interaction, "Take an hour…", "1")
    counted: dict[int, int] = {}
    for item in interaction.view.children:
        counted[item.row] = counted.get(item.row, 0) + 1
    assert max(counted.values()) <= 5
    assert counted[2] == 4


# --- the organizer sub-panels --------------------------------------------------------------------


async def test_putting_somebody_in_needs_both_picks_and_then_ignores_the_ceiling(
    bot, cog, organizer, alice, db
):
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db)
    interaction = await open_the_card(cog, bot, organizer, train_id)

    await press(interaction, "Put somebody in…")
    await press(interaction, "Put them in")
    assert "Pick an hour and a person" in interaction.sent

    await pick_one(interaction, "Which slot…", "1")
    control = picker(interaction.view, "Who takes it?")
    control._values = [alice]
    await control.callback(interaction)
    await press(interaction, "Put them in")

    assert "now belongs to Alice" in interaction.sent
    slots = await slots_for(db, train_id)
    assert slots[0]["user_id"] == ALICE and slots[0]["assigned_by"] == ORGANIZER
    assert "**Saturday train** — raid train" in interaction.embed.description


async def test_putting_in_somebody_with_no_twitch_is_a_worded_refusal(
    bot, cog, organizer, alice, db
):
    train_id = await a_train(db)
    interaction = await open_the_card(cog, bot, organizer, train_id)
    await press(interaction, "Put somebody in…")
    await pick_one(interaction, "Which slot…", "1")
    control = picker(interaction.view, "Who takes it?")
    control._values = [alice]
    await control.callback(interaction)

    await press(interaction, "Put them in")

    assert "**Link my Twitch channel**" in interaction.sent
    assert (await slots_for(db, train_id))[0]["user_id"] is None


async def test_the_second_swap_select_never_offers_the_first_pick(
    bot, cog, organizer, alice, bobby, db
):
    await link(db, ALICE, "alicestreams")
    await link(db, BOB, "bobstreams")
    train_id = await a_train(db)
    await seat(bot, train_id, alice, 1, by=organizer)
    await seat(bot, train_id, bobby, 2, by=organizer)
    before = [row["starts_at"] for row in await slots_for(db, train_id)]
    interaction = await open_the_card(cog, bot, organizer, train_id)

    await press(interaction, "Change two slots round…")
    await press(interaction, "Swap them")
    assert "Pick two hours" in interaction.sent

    await pick_one(interaction, "First…", "1")
    assert options(interaction, "Second…") == ["2", "3"]
    await pick_one(interaction, "Second…", "2")
    await press(interaction, "Swap them")

    assert "changed places" in interaction.sent
    slots = await slots_for(db, train_id)
    assert [row["user_id"] for row in slots] == [BOB, ALICE, None]
    assert [row["starts_at"] for row in slots] == before


async def test_a_one_slot_train_is_never_offered_a_swap(bot, cog, organizer, db):
    train_id = await a_train(db, count=1)
    interaction = await open_the_card(cog, bot, organizer, train_id)
    assert "Change two slots round…" not in labels(interaction.view)


async def test_calling_a_train_off_is_one_modal_and_the_reason_is_the_confirmation(
    bot, cog, organizer, alice, bobby, db
):
    await link(db, ALICE, "alicestreams")
    await link(db, BOB, "bobstreams")
    train_id = await a_train(db)
    await seat(bot, train_id, alice, 1, by=organizer)
    await seat(bot, train_id, bobby, 2, by=organizer)
    bobby.refuse_dm = True
    interaction = await open_the_card(cog, bot, organizer, train_id)

    await press(interaction, "Call it off…")
    modal = interaction.response.modals[-1]
    assert modal.note.required is True
    modal.note._value = "the venue fell through"
    await modal.on_submit(interaction)

    assert (await get_train(db, GUILD, train_id))["status"] == CANCELLED
    assert "the venue fell through" in alice.dms[0]
    assert bobby.dms == []
    kinds = await kinds_logged(db)
    assert "raidtrain.cancel" in kinds and "raidtrain.dm_failed" in kinds
    assert "1 person/people" in interaction.sent
    assert labels(interaction.view) == ["Back", "Refresh"]


async def test_a_finished_train_cannot_be_called_off_and_has_no_button_for_it(
    bot, cog, organizer, db
):
    train_id = await a_train(db)
    await db.conn.execute("UPDATE raid_trains SET status = ? WHERE id = ?", (DONE, train_id))
    await db.conn.commit()
    interaction = await open_the_card(cog, bot, organizer, train_id)
    assert "Call it off…" not in labels(interaction.view)
    assert (await get_train(db, GUILD, train_id))["status"] == DONE


# --- the staff row -------------------------------------------------------------------------------


async def test_the_mode_select_turns_the_feature_on_and_warns_about_nowhere_to_post(
    bot, cog, organizer
):
    await bot.store.clear(GUILD, "raidtrain_channel_id")
    await bot.store.set(GUILD, "events_announce_channel_id", 0)
    await bot.store.set(GUILD, "raidtrain_mode", "off")
    interaction = await open_the_panel(cog, bot, organizer)

    await pick_one(interaction, "Mode…", "on")

    assert bot.store.get(GUILD, "raidtrain_mode") == "on"
    assert "**Setup…**" in interaction.sent
    assert "raidtrain.mode" in await kinds_logged(bot.db)
    assert "Start a raid train" in labels(interaction.view)


async def test_a_member_never_sees_the_mode_select_and_a_demoted_one_cannot_use_it(
    bot, cog, organizer, alice
):
    assert "Mode…" not in placeholders((await open_the_panel(cog, bot, alice)).view)
    interaction = await open_the_panel(cog, bot, organizer)
    organizer.guild_permissions = SimpleNamespace(manage_guild=False)

    await pick_one(interaction, "Mode…", "off")

    assert "staff" in interaction.sent
    assert bot.store.get(GUILD, "raidtrain_mode") == "on"


async def test_setup_saves_one_row_for_the_whole_form_and_clears_one_key_at_a_time(
    bot, cog, organizer, db
):
    interaction = await open_the_panel(cog, bot, organizer)
    await press(interaction, "Setup…")
    role = FakeRole(4242)
    ping = FakeRole(4343)
    channel = bot.guild.get_channel(RAID_CHANNEL)

    picker(interaction.view, "Where the lineup post lives")._values = [channel]
    await picker(interaction.view, "Where the lineup post lives").callback(interaction)
    picker(interaction.view, "Who may build a lineup, besides staff")._values = [role]
    await picker(interaction.view, "Who may build a lineup, besides staff").callback(interaction)
    picker(interaction.view, "Who is pinged in front of a lineup")._values = [ping]
    await picker(interaction.view, "Who is pinged in front of a lineup").callback(interaction)
    await press(interaction, "Save")

    assert bot.store.get(GUILD, "raidtrain_channel_id") == RAID_CHANNEL
    assert bot.store.get(GUILD, "raidtrain_organizer_role_id") == role.id
    assert bot.store.get(GUILD, "raidtrain_ping_role_id") == ping.id
    assert (await kinds_logged(db)).count("raidtrain.setup") == 1

    await pick_one(interaction, "Clear…", "raidtrain_ping_role_id")

    assert bot.store.get(GUILD, "raidtrain_ping_role_id") is None
    assert bot.store.get(GUILD, "raidtrain_organizer_role_id") == role.id
    assert "nobody is pinged" in interaction.sent


async def test_setup_with_nothing_picked_writes_nothing(bot, cog, organizer, db):
    interaction = await open_the_panel(cog, bot, organizer)
    await press(interaction, "Setup…")
    await press(interaction, "Save")
    assert "Nothing was picked" in interaction.sent
    assert "raidtrain.setup" not in await kinds_logged(db)


async def test_clear_only_offers_the_keys_that_are_actually_set(bot, cog, organizer):
    interaction = await open_the_panel(cog, bot, organizer)
    await press(interaction, "Setup…")
    assert options(interaction, "Clear…") == ["raidtrain_channel_id"]
    await pick_one(interaction, "Clear…", "raidtrain_channel_id")
    assert "Clear…" not in placeholders(interaction.view)


async def test_a_demoted_staffer_opens_no_sub_panel_and_writes_nothing(bot, cog, organizer):
    interaction = await open_the_panel(cog, bot, organizer)
    organizer.guild_permissions = SimpleNamespace(manage_guild=False)
    await press(interaction, "Setup…")
    assert "staff" in interaction.sent
    assert interaction.edits == []


async def test_an_organizer_demoted_mid_card_moves_nothing(bot, cog, organizer, alice, db):
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db)
    interaction = await open_the_card(cog, bot, organizer, train_id)
    organizer.guild_permissions = SimpleNamespace(manage_guild=False)

    await press(interaction, "Lock the lineup")

    assert interaction.sent == NOT_AN_ORGANIZER.format(who="staff")
    assert (await get_train(db, GUILD, train_id))["status"] == OPEN


# --- the create draft -----------------------------------------------------------------------------


def a_draft(**fields):
    """A filled `TrainDraft`; a start the picker could never produce lands as a typed date."""
    when = WhenDraft(zone=fields.pop("tz_name", "UTC"))
    start = fields.pop("start", "2099-09-14 19:30")
    day = parse_day(str(start)[:10])
    clock = str(start)[11:16]
    if day is not None and re.fullmatch(r"\d{2}:\d{2}", clock):
        when.day = day
        when.hour, when.minute = (int(part) for part in clock.split(":"))
    else:
        when.later_text = str(start)
    return rt.TrainDraft(
        when=when,
        title=fields.pop("title", "Saturday train"),
        description=fields.pop("description", ""),
        slot_minutes=fields.pop("slot_minutes", "60"),
        slot_count=fields.pop("slot_count", "4"),
    )


async def start_from(bot, who, **fields):
    view = cog_module.TrainDraftPanel(10, a_draft(**fields))
    interaction = FakeInteraction(bot, who)
    await cog_module.start_draft(interaction, view)
    return interaction


async def open_the_draft(cog, bot, who):
    interaction = await open_the_panel(cog, bot, who)
    await press(interaction, "Start a raid train")
    return interaction


async def test_the_create_draft_is_only_offered_to_organizers(bot, cog, alice, organizer):
    interaction = await open_the_draft(cog, bot, organizer)

    assert interaction.response.modals == []
    assert isinstance(interaction.view, cog_module.TrainDraftPanel)
    assert "Start a raid train" not in labels((await open_the_panel(cog, bot, alice)).view)


async def test_the_draft_opens_with_the_three_dropdowns_and_no_start_yet(bot, cog, organizer):
    interaction = await open_the_draft(cog, bot, organizer)

    assert DAY_PLACEHOLDER in placeholders(interaction.view)
    assert HOUR_PLACEHOLDER in placeholders(interaction.view)
    assert MINUTE_PLACEHOLDER in placeholders(interaction.view)
    assert "Title & details" in labels(interaction.view)
    assert "Time zone" in labels(interaction.view)
    assert "Start" not in labels(interaction.view)


async def test_a_fresh_draft_starts_at_the_slot_length_the_server_uses(bot, cog, organizer):
    await bot.store.set(GUILD, "raidtrain_slot_minutes", 45)

    interaction = await open_the_draft(cog, bot, organizer)

    assert interaction.view.fields.slot_minutes == "45"
    assert "**Minutes per slot** — 45" in interaction.embed.description


async def test_the_text_modal_holds_abc_slot_minutes_on_the_panel_and_keeps_the_title(
    bot, cog, organizer
):
    """The owner's report: an error emptied the form. `"abc"` no longer costs the title."""
    interaction = await open_the_draft(cog, bot, organizer)
    view = interaction.view
    await press(interaction, "Title & details")
    modal = interaction.response.modals[0]

    modal.train_title._value = "Saturday train"
    modal.description._value = "Everyone welcome."
    modal.slot_minutes._value = "abc"
    modal.slot_count._value = "4"
    typed = FakeInteraction(bot, organizer)
    await modal.on_submit(typed)

    said = typed.embed.description
    assert "Saturday train" in said
    assert "Everyone welcome." in said
    assert "**Minutes per slot** — abc" in said
    assert "Start" not in labels(typed.view)
    assert view.fields.slot_minutes == "abc"


async def test_abc_slot_minutes_says_why_once_the_time_is_the_last_thing_settled(
    bot, cog, organizer
):
    """One sentence at a time: the time is asked for first, the numbers when it is there."""
    interaction = await open_the_draft(cog, bot, organizer)
    fields = interaction.view.fields
    fields.title = "Saturday train"
    fields.slot_minutes = "abc"
    fields.when.day = (datetime.now(UTC) + timedelta(days=3)).date()
    fields.when.hour = 19

    await pick_one(interaction, MINUTE_PLACEHOLDER, "30")

    said = interaction.embed.description
    assert "not a whole number" in said
    assert "**Minutes per slot** — abc" in said
    assert "Saturday train" in said
    assert "Start" not in labels(interaction.view)


async def test_the_text_modal_comes_back_with_everything_already_typed(bot, cog, organizer):
    interaction = await open_the_draft(cog, bot, organizer)
    interaction.view.fields.title = "Saturday train"
    interaction.view.fields.slot_count = "4"

    await press(interaction, "Title & details")

    modal = interaction.response.modals[0]
    assert modal.train_title.default == "Saturday train"
    assert modal.slot_count.default == "4"


async def test_start_appears_only_once_the_title_the_time_and_both_numbers_pass(
    bot, cog, organizer
):
    interaction = await open_the_draft(cog, bot, organizer)
    fields = interaction.view.fields
    fields.title = "Saturday train"
    fields.slot_count = "4"

    day = (datetime.now(UTC) + timedelta(days=3)).date()
    await pick_one(interaction, DAY_PLACEHOLDER, day.isoformat())
    assert "Start" not in labels(interaction.view)

    await pick_one(interaction, HOUR_PLACEHOLDER, "19")
    assert "Start" not in labels(interaction.view)

    await pick_one(interaction, MINUTE_PLACEHOLDER, "30")
    assert "Start" in labels(interaction.view)


async def test_a_bad_typed_date_keeps_everything_and_says_so_on_the_panel(bot, cog, organizer):
    interaction = await open_the_draft(cog, bot, organizer)
    interaction.view.fields.title = "Saturday train"

    await pick_one(interaction, DAY_PLACEHOLDER, LATER_VALUE)
    modal = interaction.response.modals[0]
    modal.day._value = "saturday-ish"
    typed = FakeInteraction(bot, organizer)
    await modal.on_submit(typed)

    said = typed.embed.description
    assert "Saturday train" in said
    assert "saturday-ish" in said and "YYYY-MM-DD" in said
    assert "Start" not in labels(typed.view)


async def test_a_start_in_the_past_is_refused_in_words_and_writes_nothing(bot, cog, organizer):
    interaction = await start_from(bot, organizer, start="2020-01-01 10:00")

    assert "already gone by" in interaction.sent
    assert await list_trains(bot.db, GUILD, scope="all") == []


async def test_a_draft_with_no_title_says_the_title_is_what_is_left(bot, cog, organizer):
    interaction = await start_from(bot, organizer, title="")

    assert "needs a name" in interaction.sent
    assert await list_trains(bot.db, GUILD, scope="all") == []


@pytest.mark.parametrize(
    ("minutes", "count", "said"),
    [
        ("ten", "3", "not a whole number"),
        ("60", "many", "not a whole number"),
        ("5", "3", "15 to 720 minutes"),
        ("60", "99", "1 to 24 slots"),
    ],
)
async def test_a_train_nobody_could_post_is_refused_before_it_is_written(
    bot, cog, organizer, minutes, count, said
):
    """Start re-asks the bounds rather than trusting the button that rendered it."""
    interaction = await start_from(bot, organizer, slot_minutes=minutes, slot_count=count)

    assert said in interaction.sent
    assert await list_trains(bot.db, GUILD, scope="all") == []


async def test_a_good_draft_defers_writes_the_train_posts_it_and_lands_on_the_root(
    bot, cog, organizer, db
):
    bot.guard = FakeGuard([TEST_CHANNEL])

    interaction = await start_from(bot, organizer, description="Everyone welcome.")

    assert interaction.response.deferred is True
    trains = await list_trains(db, GUILD, scope="all")
    assert len(trains) == 1
    assert len(await slots_for(db, trains[0]["id"])) == 4
    assert "raidtrain.create" in await kinds_logged(db)
    assert bot.guild.get_channel(TEST_CHANNEL).posts
    assert "The lineup is in" in interaction.sent
    assert "A train…" in placeholders(interaction.view)


async def test_start_is_refused_when_the_organizer_role_goes_while_the_draft_is_open(
    bot, cog, organizer, db
):
    view = cog_module.TrainDraftPanel(10, a_draft())
    organizer.roles = []
    organizer.guild_permissions = SimpleNamespace(manage_guild=False)

    interaction = FakeInteraction(bot, organizer)
    await cog_module.start_draft(interaction, view)

    assert NOT_AN_ORGANIZER.format(who="staff") in interaction.sent
    assert await list_trains(db, GUILD, scope="all") == []


async def test_the_drafts_time_zone_button_stores_through_the_same_door_and_comes_back(
    bot, cog, organizer, db
):
    interaction = await open_the_draft(cog, bot, organizer)
    interaction.view.fields.title = "Saturday train"

    await press(interaction, "Time zone")
    assert interaction.embed.title == ZONE_PANEL_TITLE

    await pick_one(interaction, ZONE_PLACEHOLDER, "Europe/London")

    assert await get_timezone(db, organizer.id) == "Europe/London"
    assert interaction.embed.title == rt.DRAFT_TITLE
    assert "Saturday train" in interaction.embed.description
    assert "Europe/London" in interaction.embed.description


# --- panel discipline ----------------------------------------------------------------------------


async def test_every_move_defers_before_it_touches_discord(bot, cog, organizer, alice, db):
    """Checklist 8 and 24: a lineup edit is a network call, and 3 seconds is not enough."""
    await link(db, ALICE, "alicestreams")
    await link(db, ORGANIZER, "robinstreams")
    train_id = await a_train(db)
    interaction = await open_the_card(cog, bot, organizer, train_id)
    assert interaction.response.deferred is True

    for doing in (
        lambda: pick_one(interaction, "Take an hour…", "1"),
        lambda: press(interaction, "Put somebody in…"),
        lambda: press(interaction, "Back"),
        lambda: press(interaction, "Lock the lineup"),
        lambda: press(interaction, "Refresh"),
    ):
        interaction.response.deferred = False
        await doing()
        assert interaction.response.deferred is True


async def test_a_click_with_the_database_gone_answers_rather_than_crashing(
    bot, cog, alice, db, monkeypatch
):
    train_id = await a_train(db)
    interaction = await open_the_panel(cog, bot, alice)
    db_is_down(monkeypatch)

    await pick_one(interaction, "A train…", str(train_id))

    assert "database" in interaction.sent.lower()
    assert interaction.response.deferred is True
    assert len(interaction.edits) == 0


async def test_every_move_goes_through_the_shared_function_at_its_discord_default(
    bot, cog, alice, db, monkeypatch
):
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db)
    seen = []
    real = cog_module.claim_slot

    async def watched(*args, **kwargs):
        seen.append(kwargs)
        return await real(*args, **kwargs)

    monkeypatch.setattr(cog_module, "claim_slot", watched)
    interaction = await open_the_card(cog, bot, alice, train_id)
    await pick_one(interaction, "Take an hour…", "1")

    assert seen == [{}]
    assert "raidtrain.claim" in await kinds_logged(db)
    assert "web.raidtrain.claim" not in await kinds_logged(db)


async def test_a_re_render_retires_the_view_it_replaced(bot, cog, alice, db):
    train_id = await a_train(db)
    interaction = await open_the_panel(cog, bot, alice)
    first = interaction.view
    await pick_one(interaction, "A train…", str(train_id))
    assert first.replaced is True
    assert first.is_finished() is True
    assert interaction.view.replaced is False


async def test_the_timeout_greys_every_control_and_says_the_panel_went_quiet(bot, cog, alice, db):
    await a_train(db)
    interaction = await open_the_panel(cog, bot, alice)
    view = interaction.view
    view.message = PanelMessage(1, embed=interaction.embed)

    await view.on_timeout()

    assert all(item.disabled for item in view.children)
    assert view.message.kwargs["embeds"][0].footer.text.endswith("run /raidtrain again")


async def test_the_panel_length_is_read_from_the_setting(bot, cog, alice):
    await bot.store.set(GUILD, "raidtrain_panel_minutes", 3)
    interaction = await open_the_panel(cog, bot, alice)
    assert interaction.view.timeout == 180


async def test_the_site_link_is_staff_only_because_every_route_behind_it_is(
    bot, cog, alice, organizer
):
    theirs = await open_the_panel(cog, bot, organizer)
    link_button = next(
        one for one in theirs.view.children if isinstance(one, discord.ui.Button) and one.url
    )
    assert link_button.url.endswith("/events.html")
    assert not [
        one
        for one in (await open_the_panel(cog, bot, alice)).view.children
        if isinstance(one, discord.ui.Button) and getattr(one, "url", None)
    ]


# --- the sweep -----------------------------------------------------------------------------------


async def test_the_sweep_locks_a_train_at_its_start_then_finishes_it(bot, cog, db):
    train_id = await a_train(db, starts=datetime.now(UTC) - timedelta(minutes=1), count=1)
    await cog.sweep_once()
    assert (await get_train(db, GUILD, train_id))["status"] == LIVE
    kinds = await kinds_logged(db)
    assert kinds.count("raidtrain.lock") == 1 and "raidtrain.live" in kinds

    await db.conn.execute(
        "UPDATE raid_slots SET ends_at = ? WHERE train_id = ?",
        ((datetime.now(UTC) - timedelta(minutes=1)).isoformat(), train_id),
    )
    await db.conn.commit()
    await cog.sweep_once()
    assert (await get_train(db, GUILD, train_id))["status"] == DONE
    assert "raidtrain.done" in await kinds_logged(db)


async def test_the_sweep_does_nothing_at_all_while_the_feature_is_off(bot, cog, db):
    await bot.store.set(GUILD, "raidtrain_mode", "off")
    train_id = await a_train(db, starts=datetime.now(UTC) - timedelta(minutes=1))
    await cog.sweep_once()
    assert (await get_train(db, GUILD, train_id))["status"] == OPEN


async def test_a_reminder_goes_out_once_with_both_neighbours_in_it(
    bot, cog, organizer, alice, bobby, db
):
    await link(db, ALICE, "alicestreams")
    await link(db, BOB, "bobstreams")
    train_id = await a_train(db, starts=datetime.now(UTC) + timedelta(minutes=20))
    await seat(bot, train_id, alice, 1, by=organizer)
    await seat(bot, train_id, bobby, 2, by=organizer)

    await cog.sweep_once()
    assert len(alice.dms) == 1
    assert "open the train" in alice.dms[0]
    assert "bobstreams" in alice.dms[0]
    assert bobby.dms == []

    await cog.sweep_once()
    assert len(alice.dms) == 1
    assert (await kinds_logged(db)).count("raidtrain.remind") == 1


async def test_shadow_writes_what_it_would_have_sent_and_sends_nothing(
    bot, cog, organizer, alice, db
):
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db, starts=datetime.now(UTC) + timedelta(minutes=20))
    await seat(bot, train_id, alice, 1, by=organizer)
    await bot.store.set(GUILD, "raidtrain_mode", "shadow")
    await cog.sweep_once()
    assert alice.dms == []
    kinds = await kinds_logged(db)
    assert "raidtrain.would_remind" in kinds and "raidtrain.remind" not in kinds


async def test_a_reminder_whose_slot_has_started_is_stamped_rather_than_sent_late(
    bot, cog, organizer, alice, db
):
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db, starts=datetime.now(UTC) - timedelta(hours=2), count=1)
    slot = (await slots_for(db, train_id))[0]
    await take_slot(db, slot["id"], ALICE, "alicestreams", ORGANIZER)
    await cog.sweep_once()
    assert alice.dms == []
    assert (await slots_for(db, train_id))[0]["reminded_at"] is not None


async def test_a_refused_dm_is_a_logged_fact_and_never_a_silent_one(bot, cog, alice, db):
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db, starts=datetime.now(UTC) + timedelta(minutes=20), count=1)
    slot = (await slots_for(db, train_id))[0]
    await take_slot(db, slot["id"], ALICE, "alicestreams", None)
    alice.refuse_dm = True
    await cog.sweep_once()
    kinds = await kinds_logged(db)
    assert "raidtrain.dm_failed" in kinds and "raidtrain.remind" not in kinds


async def test_a_holder_who_is_already_streaming_is_checked_in_and_the_train_moves(
    bot, cog, organizer, alice, bobby, db
):
    await link(db, ALICE, "alicestreams")
    await link(db, BOB, "bobstreams")
    bot.guard = FakeGuard([TEST_CHANNEL])
    train_id = await a_train(db, starts=datetime.now(UTC) - timedelta(minutes=1))
    await seat(bot, train_id, alice, 1, by=organizer)
    await seat(bot, train_id, bobby, 2, by=organizer)
    await open_session(db, ALICE)

    await cog.sweep_once()
    assert (await get_train(db, GUILD, train_id))["status"] == LIVE

    slots = await slots_for(db, train_id)
    assert slots[0]["checked_in_at"] is not None
    assert "raidtrain.checkin" in await kinds_logged(db)
    posted = bot.guild.get_channel(TEST_CHANNEL).posts
    assert any("alicestreams" in str(one["content"]) for one in posted)
    assert any("bobstreams" in str(one["content"]) for one in posted)


async def test_the_train_moves_line_can_be_turned_off(bot, cog, organizer, alice, db):
    await bot.store.set(GUILD, "raidtrain_live_posts", False)
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db, starts=datetime.now(UTC) - timedelta(minutes=1))
    await seat(bot, train_id, alice, 1, by=organizer)
    await open_session(db, ALICE)
    await cog.sweep_once()
    assert (await slots_for(db, train_id))[0]["checked_in_at"] is None
    assert "raidtrain.checkin" not in await kinds_logged(db)


# --- posting -------------------------------------------------------------------------------------


async def test_the_lineup_is_posted_once_and_edited_in_place_after_that(
    bot, cog, organizer, alice, db
):
    bot.guard = FakeGuard([TEST_CHANNEL])
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db)
    await cog.publish_lineup(bot.guild, train_id)
    channel = bot.guild.get_channel(TEST_CHANNEL)
    assert len(channel.posts) == 1
    train = await get_train(db, GUILD, train_id)
    assert train["lineup_message_id"] and train["thread_id"]

    await seat(bot, train_id, alice, 1, by=organizer)

    assert len(channel.posts) == 1
    message = channel.messages[train["lineup_message_id"]]
    assert "alicestreams" in message.content
    assert "1/3 slot(s) filled" in message.content


async def test_a_channel_test_mode_refuses_is_logged_and_never_raised(bot, cog, db):
    bot.guard = FakeGuard([])
    await bot.store.set(GUILD, "raidtrain_channel_id", RAID_CHANNEL)
    train_id = await a_train(db)
    await cog.publish_lineup(bot.guild, train_id)
    assert bot.guild.get_channel(RAID_CHANNEL).posts == []
    assert "raidtrain.post_skipped_test_mode" in await kinds_logged(db)
    assert (await get_train(db, GUILD, train_id))["lineup_message_id"] is None


async def test_nowhere_to_post_is_a_named_reason_rather_than_a_crash(bot, cog, db):
    await bot.store.clear(GUILD, "raidtrain_channel_id")
    await bot.store.clear(GUILD, "events_announce_channel_id")
    await bot.store.set(GUILD, "events_announce_channel_id", 0)
    train_id = await a_train(db)
    await cog.publish_lineup(bot.guild, train_id)
    assert "raidtrain.post_failed" in await kinds_logged(db)


async def test_shadow_never_puts_a_lineup_in_a_channel(bot, cog, db):
    await bot.store.set(GUILD, "raidtrain_mode", "shadow")
    train_id = await a_train(db)
    await cog.publish_lineup(bot.guild, train_id)
    assert bot.guild.get_channel(TEST_CHANNEL).posts == []
    assert "raidtrain.would_post" in await kinds_logged(db)


async def test_the_calendar_event_is_the_plain_title_until_staff_change_the_key(bot, cog, db):
    """Owner 2026-09-10: raid trains stay as they are, but the wording is a setting now."""
    await bot.store.set(GUILD, "raidtrain_scheduled_event", True)
    train_id = await a_train(db)
    await cog.publish_lineup(bot.guild, train_id)

    assert [one.name for one in bot.guild.scheduled] == ["Saturday train"]
    assert (await get_train(db, GUILD, train_id))["scheduled_event_id"] == 7700


async def test_the_calendar_event_takes_the_wording_staff_typed_on_the_dashboard(bot, cog, db):
    await bot.store.set(GUILD, "raidtrain_scheduled_event", True)
    await bot.store.set(GUILD, RAIDTRAIN_SCHEDULED_NAME_KEY, "{title} Feat. BaF")
    train_id = await a_train(db)
    await cog.publish_lineup(bot.guild, train_id)

    assert [one.name for one in bot.guild.scheduled] == ["Saturday train Feat. BaF"]


async def test_a_wording_that_will_not_render_falls_back_to_the_title_not_to_feat_baf(
    bot, cog, db
):
    """Checklist 17, and the fallback is this feature's own default rather than the events one."""
    await bot.store.set(GUILD, "raidtrain_scheduled_event", True)
    await bot.store.set(GUILD, RAIDTRAIN_SCHEDULED_NAME_KEY, "{title} Feat. BaF")
    await db.conn.execute(
        "UPDATE settings SET value = ? WHERE guild_id = ? AND key = ?",
        ('"{title} on {date}"', GUILD, RAIDTRAIN_SCHEDULED_NAME_KEY),
    )
    await db.conn.commit()
    await bot.store.load()
    train_id = await a_train(db)
    await cog.publish_lineup(bot.guild, train_id)

    assert [one.name for one in bot.guild.scheduled] == ["Saturday train"]


async def test_test_mode_makes_no_calendar_event_however_the_wording_is_set(bot, cog, db):
    bot.guard = FakeGuard([TEST_CHANNEL])
    await bot.store.set(GUILD, "raidtrain_scheduled_event", True)
    await bot.store.set(GUILD, RAIDTRAIN_SCHEDULED_NAME_KEY, "{title} Feat. BaF")
    train_id = await a_train(db)
    await cog.publish_lineup(bot.guild, train_id)

    assert bot.guild.scheduled == []
    assert "raidtrain.would_create_scheduled" in await kinds_logged(db)
    assert (await get_train(db, GUILD, train_id))["scheduled_event_id"] is None


async def test_only_the_ping_role_may_be_mentioned_by_a_lineup(bot, cog):
    await bot.store.set(GUILD, "raidtrain_ping_role_id", 4242)
    mentions = cog._mentions(GUILD)
    assert mentions.everyone is False
    assert mentions.users is False
    assert [role.id for role in mentions.roles] == [4242]


async def test_no_ping_role_means_the_lineup_mentions_nobody(bot, cog):
    assert cog._mentions(GUILD).roles is False


# --- the sweep's own health ----------------------------------------------------------------------


async def test_the_sweep_records_its_health_for_the_status_page(bot, cog):
    assert cog.loop_health("sweep") == (None, None)
    assert cog.loop_health("not_a_loop_here") == (None, None)
    await cog.sweep_once()
    ok_at, error = cog.loop_health("sweep")
    assert ok_at is not None and error is None


async def test_a_sweep_that_keeps_failing_says_so_in_the_log_once(bot, cog, monkeypatch):
    async def explode():
        raise RuntimeError("boom")

    monkeypatch.setattr(cog, "sweep_once", explode)
    for _ in range(4):
        await cog.sweep()
    kinds = await kinds_logged(bot.db)
    assert kinds.count("raidtrain.poll_degraded") == 1
    assert "boom" in cog.last_sweep_error


async def test_a_sweep_in_trouble_says_so_on_the_staff_half_of_the_panel(
    bot, cog, organizer, monkeypatch
):
    async def explode():
        raise RuntimeError("boom")

    monkeypatch.setattr(cog, "sweep_once", explode)
    await cog.sweep()
    interaction = await open_the_panel(cog, bot, organizer)
    assert "did not finish: RuntimeError: boom" in interaction.embed.description


async def test_the_sweep_gap_is_re_read_rather_than_frozen_at_boot(bot, cog):
    assert cog._minutes() == 5
    await bot.store.set(GUILD, "raidtrain_poll_minutes", 2)
    cog._retime()
    assert cog.sweep.minutes == 2


def test_the_test_channel_constants_are_still_what_the_fakes_expect():
    assert CARL not in (ALICE, BOB, ORGANIZER)
