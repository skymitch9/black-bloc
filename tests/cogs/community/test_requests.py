import discord
import pytest
from discord import app_commands

from black_bloc import requests as pure
from black_bloc.cogs.community.requests import (
    RequestModal,
    Requests,
    apply_decision,
    notify,
)
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore
from black_bloc.storage.db import Database

GUILD = 7
TEST_CHANNEL = 111
OTHER_CHANNEL = 112
LOG_CHANNEL = 222
NOTIFY_CHANNEL = 333
STAFF_ROLE = 555
USER = 900
LEAD = 901


class _Response:
    def __init__(self, status):
        self.status = status
        self.reason = "refused"


def refused():
    return discord.HTTPException(_Response(403), "no")


def choice(value):
    return app_commands.Choice(name=value, value=value)


class FakeRole:
    def __init__(self, role_id, name=None):
        self.id = role_id
        self.name = name or f"role-{role_id}"
        self.mention = f"<@&{role_id}>"


class FakePerms:
    def __init__(self, manage_guild=False, view_channel=False):
        self.manage_guild = manage_guild
        self.view_channel = view_channel


class FakeMessage:
    def __init__(self, message_id, content, **kwargs):
        self.id = message_id
        self.content = content
        self.kwargs = kwargs


class FakeText:
    def __init__(self, channel_id, name="channel"):
        self.id = channel_id
        self.name = name
        self.mention = f"<#{channel_id}>"
        self.visible_to = set()
        self.messages = []
        self.send_raises = None

    def permissions_for(self, role):
        return FakePerms(view_channel=role.id in self.visible_to)

    async def send(self, content=None, **kwargs):
        if self.send_raises is not None:
            raise self.send_raises
        message = FakeMessage(8000 + len(self.messages), content or "", **kwargs)
        self.messages.append(message)
        return message


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black in a Flash!"
        self.channels = {}
        self.members = {}
        self.roles = [FakeRole(STAFF_ROLE, "Lead")]

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_member(self, user_id):
        return self.members.get(user_id)

    def add(self, channel):
        self.channels[channel.id] = channel
        return channel


class FakeMember:
    def __init__(self, guild, user_id=USER, display_name="Ada", roles=(), manage_guild=False):
        self.id = user_id
        self.guild = guild
        self.name = display_name
        self.display_name = display_name
        self.mention = f"<@{user_id}>"
        self.roles = [FakeRole(r) for r in roles]
        self.guild_permissions = FakePerms(manage_guild=manage_guild)
        self.dms = []
        self.dm_raises = None
        guild.members[user_id] = self

    async def send(self, content=None, **kwargs):
        if self.dm_raises is not None:
            raise self.dm_raises
        self.dms.append(content)


class FakeGuard:
    def __init__(self, test_channel_id=TEST_CHANNEL):
        self.test_channel_id = test_channel_id

    def allows_channel(self, channel):
        return int(getattr(channel, "id", channel)) == self.test_channel_id

    def refusal_message(self):
        return "Black Bloc is in **test mode**"


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guild = guild
        self.guilds = [guild]
        self.guard = None

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def get_guild(self, guild_id):
        return self.guild if guild_id == self.guild.id else None

    def get_user(self, user_id):
        return self.guild.get_member(user_id)


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

    async def defer(self, ephemeral=False, **kwargs):
        self.done = True
        self.messages.append({"content": None, "deferred": True, "ephemeral": ephemeral})


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.response.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeInteraction:
    def __init__(self, bot, user, *, channel_id=TEST_CHANNEL, guild=True):
        self.client = bot
        self.user = user
        self.guild = bot.guild if guild else None
        self.guild_id = bot.guild.id if guild else None
        self.channel_id = channel_id
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
    database = Database(tmp_path / "r.sqlite3")
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
    await store.set(GUILD, "staff_channel_id", TEST_CHANNEL)
    guild = FakeGuild()
    guild.add(FakeText(LOG_CHANNEL, name="log"))
    test_channel = guild.add(FakeText(TEST_CHANNEL, name="test"))
    test_channel.visible_to = {STAFF_ROLE}
    guild.add(FakeText(OTHER_CHANNEL, name="general"))
    guild.add(FakeText(NOTIFY_CHANNEL, name="features"))
    return FakeBot(db, store, settings, guild)


@pytest.fixture
def cog(bot):
    return Requests(bot)


@pytest.fixture
def member(bot):
    return FakeMember(bot.guild)


@pytest.fixture
def lead(bot):
    return FakeMember(bot.guild, user_id=LEAD, display_name="Lead", roles=(STAFF_ROLE,))


async def file_one(cog, bot, who, **fields):
    interaction = FakeInteraction(bot, who)
    await cog.submit(
        interaction,
        what=fields.get("what", "a request board"),
        why=fields.get("why", "the google doc is a mess"),
        due=fields.get("due", ""),
    )
    return interaction


async def test_the_command_opens_the_modal_when_requests_are_on(cog, bot, member):
    interaction = FakeInteraction(bot, member)

    await cog.request_create.callback(cog, interaction)

    assert len(interaction.response.modals) == 1
    assert isinstance(interaction.response.modals[0], RequestModal)


async def test_the_command_is_refused_with_a_sentence_while_requests_are_off(cog, bot, member):
    await bot.store.set(GUILD, "request_mode", "off")
    interaction = FakeInteraction(bot, member)

    await cog.request_create.callback(cog, interaction)

    assert not interaction.response.modals
    assert "turned off" in interaction.sent


async def test_a_member_is_told_who_may_file_when_the_server_says_staff_only(cog, bot, member):
    await bot.store.set(GUILD, "request_who_can_file", "staff")
    interaction = FakeInteraction(bot, member)

    await cog.request_create.callback(cog, interaction)

    assert not interaction.response.modals
    assert "Only staff may file" in interaction.sent


async def test_staff_may_still_file_when_the_server_says_staff_only(cog, bot, lead):
    await bot.store.set(GUILD, "request_who_can_file", "staff")
    interaction = FakeInteraction(bot, lead)

    await cog.request_create.callback(cog, interaction)

    assert len(interaction.response.modals) == 1


async def test_the_command_run_in_a_dm_says_it_belongs_in_the_server(cog, bot, member):
    interaction = FakeInteraction(bot, member, guild=False)

    await cog.request_create.callback(cog, interaction)

    assert not interaction.response.modals
    assert "in the server itself" in interaction.sent


async def test_the_modal_hands_its_three_boxes_to_the_cog(cog, bot, member):
    modal = RequestModal(cog)
    modal.what._value = "a request board"
    modal.why._value = "the doc is a mess"
    modal.due._value = "2026-09-15"
    interaction = FakeInteraction(bot, member)

    await modal.on_submit(interaction)
    row = await pure.get_request(bot.db, 1)

    assert row["what"] == "a request board" and row["due_on"] == "2026-09-15"


async def test_a_filed_request_is_stored_pending_and_confirmed_by_its_number(cog, bot, member, db):
    interaction = await file_one(cog, bot, member, due="2026-09-15")
    row = await pure.get_request(db, 1)

    assert row["status"] == pure.PENDING and row["user_id"] == member.id
    assert row["due_on"] == "2026-09-15"
    assert "#1" in interaction.sent and "staff will see it on the site" in interaction.sent
    assert interaction.response.messages[0]["deferred"] is True
    assert "request.filed" in await action_kinds(db)


async def test_a_staffers_request_is_approved_on_the_spot_and_says_so(cog, bot, lead, db):
    interaction = await file_one(cog, bot, lead)
    row = await pure.get_request(db, 1)

    assert row["status"] == pure.APPROVED and row["decided_by"] == lead.id
    assert "approved straight away" in interaction.sent
    kinds = await action_kinds(db)

    assert "request.filed" in kinds and "request.auto_approved" in kinds


async def test_a_staffers_request_waits_like_anyone_elses_once_auto_approve_is_off(
    cog, bot, lead, db
):
    await bot.store.set(GUILD, "request_auto_approve_staff", False)

    await file_one(cog, bot, lead)
    row = await pure.get_request(db, 1)

    assert row["status"] == pure.PENDING
    assert "request.auto_approved" not in await action_kinds(db)


async def test_a_date_the_bot_cannot_read_is_refused_and_nothing_is_filed(cog, bot, member, db):
    interaction = await file_one(cog, bot, member, due="15/09/2026")

    assert await pure.count_requests(db, GUILD) == 0
    assert "YYYY-MM-DD" in interaction.sent


async def test_an_empty_box_is_refused_before_anything_is_written(cog, bot, member, db):
    interaction = await file_one(cog, bot, member, why="   ")

    assert await pure.count_requests(db, GUILD) == 0
    assert "why it is worth doing" in interaction.sent


async def test_a_modal_sent_from_outside_the_test_channel_is_refused_by_hand(cog, bot, member, db):
    bot.guard = FakeGuard()
    interaction = FakeInteraction(bot, member, channel_id=OTHER_CHANNEL)

    await cog.submit(interaction, what="a board", why="because", due="")

    assert await pure.count_requests(db, GUILD) == 0
    assert "test mode" in interaction.sent


async def test_a_modal_sent_from_the_test_channel_goes_through_while_the_guard_is_on(
    cog, bot, member, db
):
    bot.guard = FakeGuard()

    await file_one(cog, bot, member)

    assert await pure.count_requests(db, GUILD) == 1


async def test_one_line_lands_in_the_notice_channel_and_its_message_is_remembered(
    cog, bot, member, db
):
    await bot.store.set(GUILD, "request_notify_channel_id", NOTIFY_CHANNEL)

    await file_one(cog, bot, member)
    channel = bot.guild.get_channel(NOTIFY_CHANNEL)
    row = await pure.get_request(db, 1)

    assert len(channel.messages) == 1 and "#1" in channel.messages[0].content
    assert row["message_id"] == channel.messages[0].id


async def test_the_notice_is_skipped_rather_than_raised_when_the_guard_refuses_that_channel(
    cog, bot, member, db
):
    bot.guard = FakeGuard()
    await bot.store.set(GUILD, "request_notify_channel_id", NOTIFY_CHANNEL)

    interaction = await file_one(cog, bot, member)

    assert bot.guild.get_channel(NOTIFY_CHANNEL).messages == []
    assert (await pure.get_request(db, 1))["message_id"] is None
    assert "#1" in interaction.sent


async def test_nothing_is_posted_when_no_notice_channel_is_set(cog, bot, member):
    await bot.store.clear(GUILD, "request_notify_channel_id")

    await file_one(cog, bot, member)

    assert bot.guild.get_channel(NOTIFY_CHANNEL).messages == []


async def test_a_notice_channel_that_refuses_the_post_is_logged_not_swallowed(cog, bot, member, db):
    await bot.store.set(GUILD, "request_notify_channel_id", NOTIFY_CHANNEL)
    bot.guild.get_channel(NOTIFY_CHANNEL).send_raises = refused()

    interaction = await file_one(cog, bot, member)

    assert "request.notify_failed" in await action_kinds(db)
    assert "#1" in interaction.sent


async def test_a_notice_channel_the_bot_cannot_see_is_left_alone(cog, bot, member, db):
    await bot.store.set(GUILD, "request_notify_channel_id", 4242)

    await file_one(cog, bot, member)

    assert (await pure.get_request(db, 1))["message_id"] is None


async def test_the_list_shows_your_own_by_default_and_says_so_when_there_are_none(
    cog, bot, member, lead
):
    await file_one(cog, bot, lead)
    interaction = FakeInteraction(bot, member)

    await cog.request_list.callback(cog, interaction)

    assert "not filed a request yet" in interaction.sent


async def test_the_list_can_show_the_pending_ones_or_every_one(cog, bot, member, lead):
    await file_one(cog, bot, member, what="a request board")
    await file_one(cog, bot, lead, what="a karaoke night")

    pending = FakeInteraction(bot, member)
    await cog.request_list.callback(cog, pending, choice("pending"))
    everything = FakeInteraction(bot, member)
    await cog.request_list.callback(cog, everything, choice("all"))

    assert "request board" in pending.sent and "karaoke" not in pending.sent
    assert "request board" in everything.sent and "karaoke" in everything.sent


async def test_the_list_pages_ten_at_a_time_and_names_the_next_page(cog, bot, member):
    for number in range(12):
        await file_one(cog, bot, member, what=f"request number {number}")

    first = FakeInteraction(bot, member)
    await cog.request_list.callback(cog, first)
    second = FakeInteraction(bot, member)
    await cog.request_list.callback(cog, second, None, 2)

    assert first.sent.count("**#") == pure.LIST_PAGE
    assert "Page 1 of 2" in first.sent
    assert "Page 2 of 2" in second.sent
    assert first.response.messages[-1]["ephemeral"] is True


async def test_nothing_pending_says_so_rather_than_showing_an_empty_list(cog, bot, member, lead):
    await file_one(cog, bot, lead)
    interaction = FakeInteraction(bot, member)

    await cog.request_list.callback(cog, interaction, choice("pending"))

    assert "Nothing is waiting" in interaction.sent


async def test_a_member_withdraws_their_own_pending_request(cog, bot, member, db):
    await file_one(cog, bot, member)
    interaction = FakeInteraction(bot, member)

    await cog.request_withdraw.callback(cog, interaction, "1")

    assert (await pure.get_request(db, 1))["status"] == pure.WITHDRAWN
    assert "withdrawn" in interaction.sent
    assert "request.withdrawn" in await action_kinds(db)


async def test_a_hash_in_front_of_the_number_is_taken_as_the_number(cog, bot, member, db):
    await file_one(cog, bot, member)
    interaction = FakeInteraction(bot, member)

    await cog.request_withdraw.callback(cog, interaction, "#1")

    assert (await pure.get_request(db, 1))["status"] == pure.WITHDRAWN


async def test_somebody_elses_request_is_not_yours_to_withdraw(cog, bot, member, lead, db):
    await file_one(cog, bot, lead)
    interaction = FakeInteraction(bot, member)

    await cog.request_withdraw.callback(cog, interaction, "1")

    assert (await pure.get_request(db, 1))["status"] != pure.WITHDRAWN
    assert "not yours" in interaction.sent


async def test_a_request_already_decided_cannot_be_withdrawn(cog, bot, member, lead, db):
    await file_one(cog, bot, member)
    await pure.set_status(db, 1, pure.APPROVED, decided_by=lead.id)
    interaction = FakeInteraction(bot, member)

    await cog.request_withdraw.callback(cog, interaction, "1")

    assert (await pure.get_request(db, 1))["status"] == pure.APPROVED
    assert "already" in interaction.sent


async def test_withdrawing_something_that_is_not_a_number_names_what_was_typed(cog, bot, member):
    interaction = FakeInteraction(bot, member)

    await cog.request_withdraw.callback(cog, interaction, "the board one")

    assert "the board one" in interaction.sent


async def test_withdrawing_a_number_nobody_filed_says_so(cog, bot, member):
    interaction = FakeInteraction(bot, member)

    await cog.request_withdraw.callback(cog, interaction, "99")

    assert "no request" in interaction.sent


async def test_only_staff_may_move_a_request_along(cog, bot, member, lead, db):
    await file_one(cog, bot, member)
    interaction = FakeInteraction(bot, member)

    await cog.request_set.callback(cog, interaction, "1", choice(pure.APPROVED))

    assert (await pure.get_request(db, 1))["status"] == pure.PENDING
    assert "staff only" in interaction.sent


async def test_staff_approve_a_request_and_the_person_who_asked_is_dmed(cog, bot, member, lead, db):
    await file_one(cog, bot, member)
    interaction = FakeInteraction(bot, lead)

    await cog.request_set.callback(cog, interaction, "1", choice(pure.APPROVED))
    row = await pure.get_request(db, 1)

    assert row["status"] == pure.APPROVED and row["decided_by"] == lead.id
    assert member.dms and "approved" in member.dms[-1]
    assert "request.approved" in await action_kinds(db)


async def test_a_decline_needs_a_line_the_person_is_sent(cog, bot, member, lead, db):
    await file_one(cog, bot, member)
    interaction = FakeInteraction(bot, lead)

    await cog.request_set.callback(cog, interaction, "1", choice(pure.DECLINED))

    assert (await pure.get_request(db, 1))["status"] == pure.PENDING
    assert "needs one line" in interaction.sent
    assert member.dms == []


async def test_a_declined_request_carries_its_reason_into_the_dm(cog, bot, member, lead, db):
    await file_one(cog, bot, member)
    interaction = FakeInteraction(bot, lead)

    await cog.request_set.callback(
        cog, interaction, "1", choice(pure.DECLINED), "we already have one"
    )
    row = await pure.get_request(db, 1)

    assert row["status"] == pure.DECLINED and row["decline_reason"] == "we already have one"
    assert "we already have one" in member.dms[-1]


async def test_finishing_a_request_stamps_when_and_tells_the_person(cog, bot, member, lead, db):
    await file_one(cog, bot, member)
    interaction = FakeInteraction(bot, lead)

    await cog.request_set.callback(cog, interaction, "1", choice(pure.DONE))
    row = await pure.get_request(db, 1)

    assert row["status"] == pure.DONE and row["done_at"]
    assert "done" in member.dms[-1]


async def test_the_middle_states_move_the_row_without_a_dm(cog, bot, member, lead, db):
    await file_one(cog, bot, member)
    for status in (pure.APPROVED, pure.PLANNED, pure.IN_PROGRESS):
        await cog.request_set.callback(cog, FakeInteraction(bot, lead), "1", choice(status))

    assert (await pure.get_request(db, 1))["status"] == pure.IN_PROGRESS
    assert len(member.dms) == 1


async def test_a_request_already_in_that_state_is_left_alone(cog, bot, member, lead, db):
    await file_one(cog, bot, member)
    await cog.request_set.callback(cog, FakeInteraction(bot, lead), "1", choice(pure.APPROVED))
    again = FakeInteraction(bot, lead)

    await cog.request_set.callback(cog, again, "1", choice(pure.APPROVED))

    assert "already" in again.sent
    assert len(member.dms) == 1


async def test_a_number_from_another_server_is_not_found_here(cog, bot, lead, db):
    await pure.create_request(db, 99, USER, what="elsewhere", why="elsewhere", due_on=None)
    interaction = FakeInteraction(bot, lead)

    await cog.request_set.callback(cog, interaction, "1", choice(pure.APPROVED))

    assert "no request" in interaction.sent
    assert (await pure.get_request(db, 1))["status"] == pure.PENDING


async def test_the_dm_is_skipped_when_the_server_has_turned_them_off(cog, bot, member, lead, db):
    await bot.store.set(GUILD, "request_dm_on_decision", False)
    await file_one(cog, bot, member)

    await cog.request_set.callback(cog, FakeInteraction(bot, lead), "1", choice(pure.APPROVED))

    assert member.dms == []
    assert (await pure.get_request(db, 1))["status"] == pure.APPROVED


async def test_a_dm_that_bounces_is_logged_rather_than_lost(cog, bot, member, lead, db):
    await file_one(cog, bot, member)
    member.dm_raises = refused()

    await cog.request_set.callback(cog, FakeInteraction(bot, lead), "1", choice(pure.APPROVED))

    assert "request.dm_failed" in await action_kinds(db)
    assert (await pure.get_request(db, 1))["status"] == pure.APPROVED


async def test_a_requester_who_has_left_is_a_logged_fact_not_a_crash(cog, bot, member, lead, db):
    await file_one(cog, bot, member)
    bot.guild.members.pop(member.id)

    await cog.request_set.callback(cog, FakeInteraction(bot, lead), "1", choice(pure.APPROVED))

    assert "request.dm_failed" in await action_kinds(db)


async def test_the_shared_decision_path_is_what_the_site_calls_too(cog, bot, member, lead, db):
    await file_one(cog, bot, member)

    said, fresh = await apply_decision(bot, bot.guild, 1, pure.PLANNED, lead)

    assert fresh is not None and fresh["status"] == pure.PLANNED
    assert "#1" in said
    said, fresh = await apply_decision(bot, bot.guild, 99, pure.PLANNED, lead)

    assert fresh is None and "no request" in said


async def test_the_notice_helper_says_nothing_when_the_bot_has_no_guild_channel(bot, member, db):
    await bot.store.set(GUILD, "request_notify_channel_id", NOTIFY_CHANNEL)
    request_id = await pure.create_request(
        db, GUILD, member.id, what="a board", why="because", due_on=None
    )
    row = await pure.get_request(db, request_id)

    await notify(bot, bot.guild, row, member)

    assert len(bot.guild.get_channel(NOTIFY_CHANNEL).messages) == 1
