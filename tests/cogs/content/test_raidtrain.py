from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from black_bloc.cogs.content.raidtrain import (
    FEATURE_OFF,
    NOT_AN_ORGANIZER,
    RaidTrains,
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
from black_bloc.raidtrain import CANCELLED, DONE, LIVE, LOCKED, NEEDS_LINK, OPEN
from black_bloc.settings_store import SettingsStore
from black_bloc.storage.db import Database

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

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def get_user(self, user_id):
        return self.guild.get_member(user_id)


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.deferred = False
        self.modals = []

    async def defer(self, ephemeral=False):
        self.deferred = True

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def send_modal(self, modal):
        self.modals.append(modal)


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
        self.namespace = SimpleNamespace(train=None)

    @property
    def sent(self):
        return self.response.messages[-1]["content"] if self.response.messages else None


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "rt.sqlite3")
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
    await store.set(GUILD, "log_channel_id", TEST_CHANNEL)
    await store.set(GUILD, "raidtrain_channel_id", TEST_CHANNEL)
    await store.set(GUILD, "raidtrain_mode", "on")
    guild = FakeGuild()
    for channel_id in (TEST_CHANNEL, RAID_CHANNEL):
        guild.add(FakeChannel(channel_id))
    return FakeBot(db, store, guild, settings)


@pytest.fixture
def cog(bot):
    return RaidTrains(bot)


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


# --- storage -----------------------------------------------------------------------------------


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


# --- the mode gate -----------------------------------------------------------------------------


async def test_every_member_command_refuses_in_words_while_the_feature_is_off(bot, cog, alice):
    await bot.store.set(GUILD, "raidtrain_mode", "off")
    interaction = FakeInteraction(bot, alice)
    await cog.list_command.callback(cog, interaction)
    assert interaction.sent == FEATURE_OFF.format(mode="off")
    assert "`/raidtrains mode on`" in interaction.sent


async def test_a_command_outside_a_server_says_so_rather_than_failing(bot, cog, alice):
    interaction = FakeInteraction(bot, alice)
    interaction.guild = None
    await cog.list_command.callback(cog, interaction)
    assert "server" in interaction.sent


# --- claiming ----------------------------------------------------------------------------------


async def test_claiming_without_a_twitch_link_names_the_command_that_fixes_it(bot, cog, alice, db):
    train_id = await a_train(db)
    interaction = FakeInteraction(bot, alice)
    await cog.claim_command.callback(cog, interaction, str(train_id))
    assert interaction.sent == NEEDS_LINK
    assert "`/twitch link" in interaction.sent
    assert all(row["user_id"] is None for row in await slots_for(db, train_id))


async def test_claiming_with_the_link_requirement_off_takes_the_slot_anyway(bot, cog, alice, db):
    await bot.store.set(GUILD, "raidtrain_require_link", False)
    train_id = await a_train(db)
    interaction = FakeInteraction(bot, alice)
    await cog.claim_command.callback(cog, interaction, str(train_id))
    assert (await slots_for(db, train_id))[0]["user_id"] == ALICE


async def test_a_claim_takes_the_next_open_slot_and_says_when_it_is(bot, cog, alice, db):
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db)
    interaction = FakeInteraction(bot, alice)
    await cog.claim_command.callback(cog, interaction, str(train_id))
    assert "Slot **#1**" in interaction.sent
    slots = await slots_for(db, train_id)
    assert slots[0]["user_id"] == ALICE and slots[0]["twitch_login"] == "alicestreams"
    assert "raidtrain.claim" in await kinds_logged(db)


async def test_a_second_claim_is_refused_by_the_one_slot_ceiling(bot, cog, alice, db):
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db)
    first = FakeInteraction(bot, alice)
    await cog.claim_command.callback(cog, first, str(train_id))
    second = FakeInteraction(bot, alice)
    await cog.claim_command.callback(cog, second, str(train_id), 2)
    assert "as many as this server allows" in second.sent
    assert (await slots_for(db, train_id))[1]["user_id"] is None


async def test_the_ceiling_can_be_lifted_altogether(bot, cog, alice, db):
    await bot.store.set(GUILD, "raidtrain_max_slots_per_member", 0)
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db)
    for position in (1, 2):
        interaction = FakeInteraction(bot, alice)
        await cog.claim_command.callback(cog, interaction, str(train_id), position)
    assert [row["user_id"] for row in await slots_for(db, train_id)] == [ALICE, ALICE, None]


async def test_a_slot_somebody_else_holds_is_refused_in_words(bot, cog, alice, bobby, db):
    await link(db, ALICE, "alicestreams")
    await link(db, BOB, "bobstreams")
    train_id = await a_train(db)
    await cog.claim_command.callback(cog, FakeInteraction(bot, alice), str(train_id), 1)
    interaction = FakeInteraction(bot, bobby)
    await cog.claim_command.callback(cog, interaction, str(train_id), 1)
    assert "already belongs to someone else" in interaction.sent


async def test_a_slot_number_that_does_not_exist_says_how_many_there_are(bot, cog, alice, db):
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db, count=3)
    interaction = FakeInteraction(bot, alice)
    await cog.claim_command.callback(cog, interaction, str(train_id), 9)
    assert "#1 to #3" in interaction.sent


async def test_a_locked_train_refuses_a_claim_and_says_who_unlocks_it(bot, cog, alice, db):
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db)
    await db.conn.execute("UPDATE raid_trains SET status = ? WHERE id = ?", (LOCKED, train_id))
    await db.conn.commit()
    interaction = FakeInteraction(bot, alice)
    await cog.claim_command.callback(cog, interaction, str(train_id))
    assert "`/raidtrain unlock`" in interaction.sent
    assert all(row["user_id"] is None for row in await slots_for(db, train_id))


async def test_an_unknown_train_is_refused_before_anything_is_read(bot, cog, alice, db):
    interaction = FakeInteraction(bot, alice)
    await cog.claim_command.callback(cog, interaction, "404")
    assert "no raid train" in interaction.sent


async def test_a_release_opens_the_hour_again_and_only_its_holder_may_do_it(
    bot, cog, alice, bobby, db
):
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db)
    await cog.claim_command.callback(cog, FakeInteraction(bot, alice), str(train_id), 1)
    theirs = FakeInteraction(bot, bobby)
    await cog.release_command.callback(cog, theirs, str(train_id), 1)
    assert "not yours" in theirs.sent
    mine = FakeInteraction(bot, alice)
    await cog.release_command.callback(cog, mine, str(train_id))
    assert "open again" in mine.sent
    assert (await slots_for(db, train_id))[0]["user_id"] is None


async def test_mine_lists_what_somebody_holds_and_says_so_when_it_is_nothing(
    bot, cog, alice, db
):
    empty = FakeInteraction(bot, alice)
    await cog.mine_command.callback(cog, empty)
    assert "do not hold a slot" in empty.sent
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db)
    await cog.claim_command.callback(cog, FakeInteraction(bot, alice), str(train_id), 2)
    held = FakeInteraction(bot, alice)
    await cog.mine_command.callback(cog, held)
    assert "slot #2" in held.sent


async def test_the_list_and_the_status_read_the_lineup_without_pinging_anybody(
    bot, cog, alice, db
):
    nothing = FakeInteraction(bot, alice)
    await cog.list_command.callback(cog, nothing)
    assert "no raid train on the calendar" in nothing.sent
    train_id = await a_train(db)
    listed = FakeInteraction(bot, alice)
    await cog.list_command.callback(cog, listed)
    assert "0/3 filled" in listed.sent
    assert "open: #1, #2, #3" in listed.sent
    shown = FakeInteraction(bot, alice)
    await cog.status_command.callback(cog, shown, str(train_id))
    assert "Saturday train" in shown.sent
    assert shown.response.messages[-1]["ephemeral"] is True


# --- organizers --------------------------------------------------------------------------------


async def test_an_ordinary_member_cannot_build_a_lineup(bot, cog, alice, db):
    train_id = await a_train(db)
    interaction = FakeInteraction(bot, alice)
    await cog.lock_command.callback(cog, interaction, str(train_id))
    assert interaction.sent == NOT_AN_ORGANIZER.format(who="staff")
    assert (await get_train(db, GUILD, train_id))["status"] == OPEN


async def test_the_organizer_role_stands_in_for_staff(bot, cog, alice, db):
    role = FakeRole(4242)
    await bot.store.set(GUILD, "raidtrain_organizer_role_id", role.id)
    assert cog.is_organizer(alice) is False
    alice.roles = [role]
    assert cog.is_organizer(alice) is True
    interaction = FakeInteraction(bot, alice)
    interaction.user.roles = []
    await cog.lock_command.callback(cog, interaction, str(await a_train(db)))
    assert f"<@&{role.id}>" in interaction.sent


async def test_locking_and_unlocking_move_the_train_and_are_refused_when_they_cannot(
    bot, cog, organizer, db
):
    train_id = await a_train(db)
    locked = FakeInteraction(bot, organizer)
    await cog.lock_command.callback(cog, locked, str(train_id))
    assert "is locked" in locked.sent
    assert (await get_train(db, GUILD, train_id))["status"] == LOCKED
    again = FakeInteraction(bot, organizer)
    await cog.lock_command.callback(cog, again, str(train_id))
    assert "cannot be marked **locked**" in again.sent
    opened = FakeInteraction(bot, organizer)
    await cog.unlock_command.callback(cog, opened, str(train_id))
    assert (await get_train(db, GUILD, train_id))["status"] == OPEN
    assert {"raidtrain.lock", "raidtrain.unlock"} <= set(await kinds_logged(db))


async def test_an_organizer_assigns_a_slot_over_the_ceiling(bot, cog, organizer, alice, db):
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db)
    for position in (1, 2):
        interaction = FakeInteraction(bot, organizer)
        await cog.assign_command.callback(cog, interaction, str(train_id), position, alice)
        assert "now belongs to Alice" in interaction.sent
    assert [row["user_id"] for row in await slots_for(db, train_id)] == [ALICE, ALICE, None]
    assert (await slots_for(db, train_id))[0]["assigned_by"] == ORGANIZER


async def test_assigning_somebody_with_no_link_says_which_command_they_run(
    bot, cog, organizer, alice, db
):
    train_id = await a_train(db)
    interaction = FakeInteraction(bot, organizer)
    await cog.assign_command.callback(cog, interaction, str(train_id), 1, alice)
    assert "`/twitch link`" in interaction.sent
    assert (await slots_for(db, train_id))[0]["user_id"] is None


async def test_unassign_empties_a_slot_and_says_so_when_it_was_empty(
    bot, cog, organizer, alice, db
):
    await link(db, ALICE, "alicestreams")
    train_id = await a_train(db)
    await cog.assign_command.callback(
        cog, FakeInteraction(bot, organizer), str(train_id), 1, alice
    )
    taken = FakeInteraction(bot, organizer)
    await cog.unassign_command.callback(cog, taken, str(train_id), 1)
    assert "open again" in taken.sent
    empty = FakeInteraction(bot, organizer)
    await cog.unassign_command.callback(cog, empty, str(train_id), 1)
    assert "already empty" in empty.sent


async def test_a_swap_moves_the_people_and_never_the_times(bot, cog, organizer, alice, bobby, db):
    await link(db, ALICE, "alicestreams")
    await link(db, BOB, "bobstreams")
    train_id = await a_train(db)
    await cog.assign_command.callback(
        cog, FakeInteraction(bot, organizer), str(train_id), 1, alice
    )
    await cog.assign_command.callback(
        cog, FakeInteraction(bot, organizer), str(train_id), 2, bobby
    )
    before = [row["starts_at"] for row in await slots_for(db, train_id)]
    interaction = FakeInteraction(bot, organizer)
    await cog.swap_command.callback(cog, interaction, str(train_id), 1, 2)
    assert "changed places" in interaction.sent
    slots = await slots_for(db, train_id)
    assert [row["user_id"] for row in slots] == [BOB, ALICE, None]
    assert [row["twitch_login"] for row in slots] == ["bobstreams", "alicestreams", None]
    assert [row["starts_at"] for row in slots] == before


async def test_swapping_a_slot_with_itself_changes_nothing(bot, cog, organizer, db):
    train_id = await a_train(db)
    interaction = FakeInteraction(bot, organizer)
    await cog.swap_command.callback(cog, interaction, str(train_id), 2, 2)
    assert "same slot" in interaction.sent


async def test_cancelling_dms_every_holder_and_records_the_one_that_refused(
    bot, cog, organizer, alice, bobby, db
):
    await link(db, ALICE, "alicestreams")
    await link(db, BOB, "bobstreams")
    train_id = await a_train(db)
    await cog.assign_command.callback(
        cog, FakeInteraction(bot, organizer), str(train_id), 1, alice
    )
    await cog.assign_command.callback(
        cog, FakeInteraction(bot, organizer), str(train_id), 2, bobby
    )
    bobby.refuse_dm = True
    interaction = FakeInteraction(bot, organizer)
    await cog.cancel_command.callback(cog, interaction, str(train_id), "the venue fell through")

    assert (await get_train(db, GUILD, train_id))["status"] == CANCELLED
    assert "the venue fell through" in alice.dms[0]
    assert bobby.dms == []
    kinds = await kinds_logged(db)
    assert "raidtrain.cancel" in kinds and "raidtrain.dm_failed" in kinds
    assert "1 person/people" in interaction.sent


async def test_a_finished_train_cannot_be_cancelled_and_says_what_it_can_be(
    bot, cog, organizer, db
):
    train_id = await a_train(db)
    await db.conn.execute("UPDATE raid_trains SET status = ? WHERE id = ?", (DONE, train_id))
    await db.conn.commit()
    interaction = FakeInteraction(bot, organizer)
    await cog.cancel_command.callback(cog, interaction, str(train_id), "never mind")
    assert "end of the line" in interaction.sent
    assert (await get_train(db, GUILD, train_id))["status"] == DONE


# --- the sweep ---------------------------------------------------------------------------------


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
    await cog.assign_command.callback(
        cog, FakeInteraction(bot, organizer), str(train_id), 1, alice
    )
    await cog.assign_command.callback(
        cog, FakeInteraction(bot, organizer), str(train_id), 2, bobby
    )

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
    await cog.assign_command.callback(
        cog, FakeInteraction(bot, organizer), str(train_id), 1, alice
    )
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
    await cog.assign_command.callback(
        cog, FakeInteraction(bot, organizer), str(train_id), 1, alice
    )
    await cog.assign_command.callback(
        cog, FakeInteraction(bot, organizer), str(train_id), 2, bobby
    )
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
    await cog.assign_command.callback(
        cog, FakeInteraction(bot, organizer), str(train_id), 1, alice
    )
    await open_session(db, ALICE)
    await cog.sweep_once()
    assert (await slots_for(db, train_id))[0]["checked_in_at"] is None
    assert "raidtrain.checkin" not in await kinds_logged(db)


# --- posting -----------------------------------------------------------------------------------


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

    await cog.assign_command.callback(
        cog, FakeInteraction(bot, organizer), str(train_id), 1, alice
    )
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


async def test_only_the_ping_role_may_be_mentioned_by_a_lineup(bot, cog):
    await bot.store.set(GUILD, "raidtrain_ping_role_id", 4242)
    mentions = cog._mentions(GUILD)
    assert mentions.everyone is False
    assert mentions.users is False
    assert [role.id for role in mentions.roles] == [4242]


async def test_no_ping_role_means_the_lineup_mentions_nobody(bot, cog):
    assert cog._mentions(GUILD).roles is False


# --- the sweep's own health --------------------------------------------------------------------


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


async def test_the_sweep_gap_is_re_read_rather_than_frozen_at_boot(bot, cog):
    assert cog._minutes() == 5
    await bot.store.set(GUILD, "raidtrain_poll_minutes", 2)
    cog._retime()
    assert cog.sweep.minutes == 2


# --- staff commands ----------------------------------------------------------------------------


async def test_the_mode_command_warns_when_nothing_has_anywhere_to_go(bot, cog, organizer):
    await bot.store.clear(GUILD, "raidtrain_channel_id")
    await bot.store.set(GUILD, "events_announce_channel_id", 0)
    interaction = FakeInteraction(bot, organizer)
    await cog.mode_command.callback(
        cog, interaction, SimpleNamespace(name="on", value="on")
    )
    assert "`/raidtrains setup channel:#somewhere`" in interaction.sent
    assert bot.store.get(GUILD, "raidtrain_mode") == "on"


async def test_setup_with_nothing_given_changes_nothing_and_says_how_to_use_it(
    bot, cog, organizer
):
    interaction = FakeInteraction(bot, organizer)
    await cog.setup_command.callback(cog, interaction)
    assert "Nothing was given" in interaction.sent


async def test_setup_stores_each_thing_it_was_given(bot, cog, organizer):
    channel = bot.guild.get_channel(RAID_CHANNEL)
    role = FakeRole(4242)
    interaction = FakeInteraction(bot, organizer)
    await cog.setup_command.callback(cog, interaction, channel, role, None)
    assert bot.store.get(GUILD, "raidtrain_channel_id") == RAID_CHANNEL
    assert bot.store.get(GUILD, "raidtrain_organizer_role_id") == role.id
    assert "raidtrain.setup" in await kinds_logged(bot.db)


async def test_a_member_cannot_change_the_mode(bot, cog, alice):
    interaction = FakeInteraction(bot, alice)
    await cog.mode_command.callback(
        cog, interaction, SimpleNamespace(name="on", value="on")
    )
    assert "staff only" in interaction.sent
    assert bot.store.get(GUILD, "raidtrain_mode") == "on"


# --- the create modal --------------------------------------------------------------------------


async def test_the_create_form_is_only_offered_to_organizers(bot, cog, alice, organizer):
    refused = FakeInteraction(bot, alice)
    await cog.create_command.callback(cog, refused)
    assert refused.response.modals == []
    allowed = FakeInteraction(bot, organizer)
    await cog.create_command.callback(cog, allowed)
    assert len(allowed.response.modals) == 1


async def test_a_start_in_the_past_is_refused_in_words(bot, cog, organizer):
    interaction = FakeInteraction(bot, organizer)
    await cog.submit_train(
        interaction,
        tz_name="UTC",
        title="Old train",
        description="",
        start="2020-01-01 10:00",
        slot_minutes="60",
        slot_count="3",
    )
    assert "already gone by" in interaction.sent
    assert await list_trains(bot.db, GUILD, scope="all") == []


async def test_a_start_nobody_can_read_names_the_shape_it_wants(bot, cog, organizer):
    interaction = FakeInteraction(bot, organizer)
    await cog.submit_train(
        interaction,
        tz_name="UTC",
        title="Bad train",
        description="",
        start="saturday-ish",
        slot_minutes="60",
        slot_count="3",
    )
    assert "YYYY-MM-DD HH:MM" in interaction.sent


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
    interaction = FakeInteraction(bot, organizer)
    await cog.submit_train(
        interaction,
        tz_name="UTC",
        title="Long train",
        description="",
        start="2099-09-14 19:30",
        slot_minutes=minutes,
        slot_count=count,
    )
    assert said in interaction.sent
    assert await list_trains(bot.db, GUILD, scope="all") == []


async def test_every_command_that_touches_discord_defers_before_it_does(
    bot, cog, organizer, alice, db
):
    """Checklist 8 and 24: a lineup edit is a network call, and the 3-second window is not it."""
    await link(db, ALICE, "alicestreams")
    await link(db, ORGANIZER, "robinstreams")
    train_id = await a_train(db)
    calls = (
        (cog.claim_command, (str(train_id),)),
        (cog.assign_command, (str(train_id), 2, alice)),
        (cog.unassign_command, (str(train_id), 2)),
        (cog.swap_command, (str(train_id), 1, 2)),
        (cog.lock_command, (str(train_id),)),
        (cog.unlock_command, (str(train_id),)),
        (cog.cancel_command, (str(train_id), "never mind")),
    )
    for command, args in calls:
        interaction = FakeInteraction(bot, organizer)
        await command.callback(cog, interaction, *args)
        assert interaction.response.deferred is True, command.name
        assert interaction.sent


async def test_the_create_form_answers_after_the_lineup_has_been_posted(
    bot, cog, organizer, db
):
    interaction = FakeInteraction(bot, organizer)
    await cog.submit_train(
        interaction,
        tz_name="UTC",
        title="Deferred train",
        description="",
        start="2099-09-14 19:30",
        slot_minutes="60",
        slot_count="2",
    )
    assert interaction.response.deferred is True
    assert "is up with 2 slot(s)" in interaction.sent


async def test_a_form_that_is_refused_never_defers(bot, cog, organizer):
    interaction = FakeInteraction(bot, organizer)
    await cog.submit_train(
        interaction,
        tz_name="UTC",
        title="Refused train",
        description="",
        start="saturday-ish",
        slot_minutes="60",
        slot_count="2",
    )
    assert interaction.response.deferred is False


async def test_a_good_form_writes_the_train_and_posts_its_lineup(bot, cog, organizer, db):
    bot.guard = FakeGuard([TEST_CHANNEL])
    interaction = FakeInteraction(bot, organizer)
    await cog.submit_train(
        interaction,
        tz_name="UTC",
        title="Saturday train",
        description="Everyone welcome.",
        start="2099-09-14 19:30",
        slot_minutes="60",
        slot_count="4",
    )
    trains = await list_trains(db, GUILD, scope="all")
    assert len(trains) == 1
    assert len(await slots_for(db, trains[0]["id"])) == 4
    assert "raidtrain.create" in await kinds_logged(db)
    assert bot.guild.get_channel(TEST_CHANNEL).posts
    assert "The lineup is in" in interaction.sent
