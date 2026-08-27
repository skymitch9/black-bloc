import asyncio
from datetime import UTC, datetime, timedelta

import discord
import pytest

from black_bloc.cogs.community.events import (
    GOLIVE_MINUTES,
    RECONCILE_MINUTES,
    DecisionButton,
    DenyModal,
    EventModal,
    Events,
    create_event,
    decision_id,
    event_for_channel,
    events_by_status,
    get_event,
    review_view,
    set_review,
    set_status,
)
from black_bloc.config import load_settings
from black_bloc.events import APPROVED, CANCELLED, DENIED, DONE, LIVE, PENDING
from black_bloc.settings_store import SettingsStore
from black_bloc.storage.db import Database
from black_bloc.timezones import DEFAULT_TZ, get_timezone, local_time, set_timezone

GUILD = 7
TEST_CHANNEL = 111
LOG_CHANNEL = 222
CATEGORY = 50
STAFF_ROLE = 555
USER = 900


class FakeRole:
    def __init__(self, role_id, name=None):
        self.id = role_id
        self.name = name or f"role-{role_id}"
        self.mention = f"<@&{role_id}>"


class FakeCategory:
    def __init__(self, category_id=CATEGORY):
        self.id = category_id
        self.name = f"category-{category_id}"
        self.mention = f"<#{category_id}>"
        self.channels = []


class FakeMessage:
    def __init__(self, message_id, content, **kwargs):
        self.id = message_id
        self.content = content
        self.kwargs = kwargs
        self.edits = []

    async def edit(self, **kwargs):
        self.edits.append(kwargs)


class _Response:
    def __init__(self, status):
        self.status = status
        self.reason = "refused"


def refused():
    return discord.HTTPException(_Response(403), "no")


class FakePerms:
    def __init__(self, manage_guild=False, view_channel=False):
        self.manage_guild = manage_guild
        self.view_channel = view_channel


class FakeText:
    def __init__(self, channel_id, guild=None, category=None, name="channel"):
        self.id = channel_id
        self.guild = guild
        self.name = name
        self.mention = f"<#{channel_id}>"
        self.category = category
        self.category_id = category.id if category else None
        self.visible_to = set()
        self.messages = []
        self.edits = []
        self.deleted = False
        self.send_raises = None
        self.edit_raises = None

    def permissions_for(self, role):
        return FakePerms(view_channel=role.id in self.visible_to)

    async def send(self, content=None, **kwargs):
        if self.send_raises is not None:
            raise self.send_raises
        message = FakeMessage(len(self.messages) + 1, content or "", **kwargs)
        self.messages.append(message)
        return message

    async def edit(self, **kwargs):
        if self.edit_raises is not None:
            raise self.edit_raises
        self.edits.append(kwargs)
        if "name" in kwargs:
            self.name = kwargs["name"]

    async def delete(self, reason=None):
        self.deleted = True
        if self.guild is not None:
            self.guild.channels.pop(self.id, None)


class FakeScheduledEvent:
    def __init__(self, event_id, kwargs):
        self.id = event_id
        self.kwargs = kwargs
        self.url = f"https://discord.com/events/{GUILD}/{event_id}"
        self.cancelled = False

    async def cancel(self, reason=None):
        self.cancelled = True

    async def delete(self, reason=None):
        self.cancelled = True


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black Bloc"
        self.channels = {}
        self.members = {}
        self.default_role = FakeRole(GUILD)
        self.roles = []
        self.created = []
        self.scheduled = []
        self.create_raises = None
        self.scheduled_raises = None
        self._next_id = 1000

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_member(self, user_id):
        return self.members.get(user_id)

    @property
    def text_channels(self):
        return [c for c in self.channels.values() if isinstance(c, FakeText)]

    def add(self, channel):
        channel.guild = self
        self.channels[channel.id] = channel
        return channel

    async def create_text_channel(self, name, *, category=None, overwrites=None, reason=None):
        if self.create_raises is not None:
            raise self.create_raises
        self._next_id += 1
        channel = FakeText(self._next_id, self, category, name=name)
        channel.given_overwrites = overwrites
        self.add(channel)
        self.created.append(channel)
        return channel

    async def create_scheduled_event(self, **kwargs):
        if self.scheduled_raises is not None:
            raise self.scheduled_raises
        self._next_id += 1
        event = FakeScheduledEvent(self._next_id, kwargs)
        self.scheduled.append(event)
        return event


class FakeMember:
    def __init__(self, guild, user_id=USER, display_name="Alice", roles=(), manage_guild=False):
        self.id = user_id
        self.guild = guild
        self.display_name = display_name
        self.name = display_name
        self.bot = False
        self.mention = f"<@{user_id}>"
        self.roles = [FakeRole(r) for r in roles]
        self.guild_permissions = FakePerms(manage_guild=manage_guild)
        self.dms = []
        self.dm_raises = None
        guild.members[user_id] = self

    async def send(self, content=None, **kwargs):
        if self.dm_raises is not None:
            raise self.dm_raises
        self.dms.append({"content": content, **kwargs})


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
        self.dynamic = []

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def get_guild(self, guild_id):
        return self.guild if guild_id == self.guild.id else None

    def add_view(self, view, **kwargs):
        self.views.append(view)

    def add_dynamic_items(self, *items):
        self.dynamic.extend(items)

    async def wait_until_ready(self):
        return None


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

    @property
    def embeds(self):
        found = []
        for message in self.response.messages:
            found += list(message.get("embeds") or [])
            if message.get("embed") is not None:
                found.append(message["embed"])
        return found


async def action_kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "e.sqlite3")
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
    category = FakeCategory()
    await store.set(GUILD, "events_category_id", CATEGORY)
    guild = FakeGuild()
    guild.roles = [FakeRole(STAFF_ROLE, "Lead")]
    guild.channels[CATEGORY] = category
    guild.add(FakeText(LOG_CHANNEL, name="log"))
    test_channel = guild.add(FakeText(TEST_CHANNEL, category=category, name="test"))
    test_channel.visible_to = {STAFF_ROLE}
    return FakeBot(db, store, settings, guild)


@pytest.fixture
def cog(bot):
    return Events(bot)


@pytest.fixture
def member(bot):
    return FakeMember(bot.guild)


@pytest.fixture
def lead(bot):
    return FakeMember(bot.guild, user_id=1, display_name="Lead", manage_guild=True)


async def test_setting_a_timezone_confirms_it_with_the_local_time(cog, bot, member, db):
    interaction = FakeInteraction(bot, member)

    await cog.timezone_set.callback(cog, interaction, "Europe/London")

    assert await get_timezone(db, member.id) == "Europe/London"
    assert "Europe/London" in interaction.sent
    assert interaction.response.messages[-1]["ephemeral"] is True


async def test_a_timezone_black_bloc_does_not_know_is_refused_with_an_example(cog, bot, member, db):
    interaction = FakeInteraction(bot, member)

    await cog.timezone_set.callback(cog, interaction, "Middle/Earth")

    assert await get_timezone(db, member.id) == DEFAULT_TZ
    assert "Middle/Earth" in interaction.sent and "Phoenix" in interaction.sent
    assert interaction.response.messages[-1]["allowed_mentions"].everyone is False


async def test_timezone_show_names_the_default_until_someone_chooses(cog, bot, member, db):
    first = FakeInteraction(bot, member)
    await cog.timezone_show.callback(cog, first)
    assert DEFAULT_TZ in first.sent and "not set a time zone" in first.sent

    await set_timezone(db, member.id, "Asia/Tokyo")
    second = FakeInteraction(bot, member)
    await cog.timezone_show.callback(cog, second)
    assert "Asia/Tokyo" in second.sent and "not set a time zone" not in second.sent


async def test_the_autocomplete_offers_at_most_twenty_five_zones(cog, bot, member):
    choices = await cog._suggest_timezones(FakeInteraction(bot, member), "a")

    assert len(choices) == 25
    assert all(choice.name == choice.value for choice in choices)


def future_start(tz_name=DEFAULT_TZ, days=3):
    return local_time(tz_name, datetime.now(UTC) + timedelta(days=days))


async def submit(cog, bot, member, **fields):
    modal = EventModal(cog, fields.pop("tz", DEFAULT_TZ))
    modal.event_title._value = fields.pop("title", "Block Party")
    modal.description._value = fields.pop("description", "bring a chair")
    modal.start._value = fields.pop("start", future_start())
    modal.duration._value = fields.pop("duration", "1h30m")
    modal.location._value = fields.pop("location", "the park")
    interaction = FakeInteraction(bot, member)
    await modal.on_submit(interaction)
    return interaction


async def approve(bot, mod, event_id, message=None):
    interaction = FakeInteraction(bot, mod, message=message)
    await DecisionButton(event_id, "approve").callback(interaction)
    return interaction


async def deny(bot, mod, event_id, reason="clashes with the marathon", message=None):
    interaction = FakeInteraction(bot, mod, message=message)
    await DecisionButton(event_id, "deny").callback(interaction)
    if not interaction.response.modals:
        return interaction
    modal = interaction.response.modals[0]
    modal.reason._value = reason
    submitted = FakeInteraction(bot, mod, message=message)
    await modal.on_submit(submitted)
    return submitted


async def store_event(db, *, status=PENDING, starts_in=None, minutes=60, channel_id=None):
    starts = datetime.now(UTC) + (starts_in or timedelta(days=1))
    event_id = await create_event(
        db,
        GUILD,
        USER,
        title="Block Party",
        description=None,
        location="the park",
        starts_at=starts,
        finishes_at=starts + timedelta(minutes=minutes),
    )
    if channel_id is not None:
        await set_review(db, event_id, channel_id, 1)
    if status != PENDING:
        await set_status(db, event_id, status)
    return event_id


async def test_a_proposal_makes_a_row_a_channel_and_a_card(cog, bot, member, db):
    interaction = await submit(cog, bot, member)

    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    made = bot.guild.created[0]
    assert made.name == "pending-alice-block-party"
    assert row["review_channel_id"] == made.id and row["review_message_id"] is not None
    assert row["title"] == "Block Party" and row["location"] == "the park"
    assert "event.created" in await action_kinds(db)
    assert "Block Party" in interaction.sent
    assert interaction.response.messages[0].get("deferred") is True


async def test_the_review_channel_is_staff_only_and_leaves_the_requester_out(cog, bot, member):
    await submit(cog, bot, member)

    overwrites = bot.guild.created[0].given_overwrites
    assert overwrites[bot.guild.default_role].view_channel is False
    assert overwrites[bot.guild.roles[0]].view_channel is True
    assert member not in overwrites


async def test_the_review_card_carries_approve_and_deny_buttons_keyed_by_the_event(
    cog, bot, member, db
):
    await submit(cog, bot, member)

    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    posted = bot.guild.created[0].messages[0]
    ids = [item.custom_id for item in posted.kwargs["view"].children]
    assert ids == [decision_id(row["id"], "approve"), decision_id(row["id"], "deny")]
    assert posted.kwargs["view"].timeout is None
    assert posted.kwargs["allowed_mentions"].everyone is False


async def test_a_start_black_bloc_cannot_read_is_refused_with_an_example(cog, bot, member, db):
    interaction = await submit(cog, bot, member, start="next tuesday")

    assert await events_by_status(db, GUILD, (PENDING,)) == []
    assert bot.guild.created == []
    assert "YYYY-MM-DD HH:MM" in interaction.sent and DEFAULT_TZ in interaction.sent


async def test_a_start_that_has_already_gone_by_is_refused(cog, bot, member, db):
    gone = local_time(DEFAULT_TZ, datetime.now(UTC) - timedelta(days=1))

    interaction = await submit(cog, bot, member, start=gone)

    assert await events_by_status(db, GUILD, (PENDING,)) == []
    assert "already gone by" in interaction.sent


async def test_a_duration_black_bloc_cannot_read_is_refused(cog, bot, member, db):
    interaction = await submit(cog, bot, member, duration="a while")

    assert await events_by_status(db, GUILD, (PENDING,)) == []
    assert "1h30m" in interaction.sent


async def test_the_start_is_read_in_the_requester_s_own_zone(cog, bot, member, db):
    typed = local_time("Asia/Tokyo", datetime.now(UTC) + timedelta(days=2))

    await submit(cog, bot, member, tz="Asia/Tokyo", start=typed)

    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    assert local_time("Asia/Tokyo", datetime.fromisoformat(row["starts_at"])) == typed


async def test_create_is_refused_while_events_are_turned_off(cog, bot, member, db):
    await bot.store.set(GUILD, "events_mode", "off")
    interaction = FakeInteraction(bot, member)

    await cog.event_create.callback(cog, interaction)

    assert interaction.response.modals == []
    assert "turned off" in interaction.sent


async def test_create_refuses_when_there_is_no_category_to_put_it_in(cog, bot, member, db):
    await bot.store.clear(GUILD, "events_category_id")

    interaction = await submit(cog, bot, member)

    assert bot.guild.created == []
    assert "/event settings category" in interaction.sent


async def test_a_channel_discord_refuses_cancels_the_row_rather_than_stranding_it(
    cog, bot, member, db
):
    bot.guild.create_raises = refused()

    interaction = await submit(cog, bot, member)

    rows = await events_by_status(db, GUILD, (CANCELLED,))
    assert len(rows) == 1
    assert "event.channel_failed" in await action_kinds(db)
    assert "Manage Channels" in interaction.sent


async def test_in_test_mode_the_card_goes_to_the_test_channel_not_the_review_one(
    cog, bot, member, db
):
    bot.guard = FakeGuard()

    interaction = await submit(cog, bot, member)

    made = bot.guild.created[0]
    assert made.messages == []
    assert len(bot.guild.get_channel(TEST_CHANNEL).messages) == 1
    assert "Test mode is on" in interaction.sent
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    assert row["review_channel_id"] == made.id


async def test_in_test_mode_the_review_channel_goes_in_the_test_channel_s_category(
    cog, bot, member, db
):
    bot.guard = FakeGuard()
    await bot.store.set(GUILD, "events_category_id", 999)

    await submit(cog, bot, member)

    assert bot.guild.created[0].category is bot.guild.get_channel(TEST_CHANNEL).category


async def test_in_test_mode_a_bot_that_cannot_see_its_test_channel_makes_nothing(
    cog, bot, member, db
):
    bot.guard = FakeGuard(test_channel_id=404)

    interaction = await submit(cog, bot, member)

    assert bot.guild.created == []
    assert "TEST_CHANNEL_ID" in interaction.sent


async def test_approving_renames_the_channel_announces_and_tells_the_requester(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    made = bot.guild.created[0]
    card = made.messages[0]

    interaction = await approve(bot, lead, row["id"], message=card)

    fresh = await get_event(db, row["id"])
    assert fresh["status"] == APPROVED and fresh["decided_by"] == lead.id
    assert made.name == "approved-alice-block-party"
    assert card.edits[-1]["view"] is None
    assert member.dms and "approved" in member.dms[-1]["content"]
    assert "event.approved" in await action_kinds(db)
    assert "Approved" in interaction.sent


async def test_approving_makes_a_real_scheduled_event_when_the_guard_is_off(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    await approve(bot, lead, row["id"], message=bot.guild.created[0].messages[0])

    made = bot.guild.scheduled[0]
    assert made.kwargs["entity_type"] is discord.EntityType.external
    assert made.kwargs["privacy_level"] is discord.PrivacyLevel.guild_only
    assert made.kwargs["end_time"] > made.kwargs["start_time"]
    assert made.kwargs["location"] == "the park"
    assert made.kwargs["reason"] == f"Black Bloc event {row['id']}"
    assert (await get_event(db, row["id"]))["scheduled_event_id"] == made.id


async def test_in_test_mode_no_scheduled_event_is_made_and_the_log_says_so(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    bot.guard = FakeGuard()

    interaction = await approve(bot, lead, row["id"])

    assert bot.guild.scheduled == []
    kinds = await action_kinds(db)
    assert "event.would_create_scheduled" in kinds
    assert "event.create_scheduled_failed" not in kinds
    assert "Test mode is on" in interaction.sent


async def test_the_scheduled_event_toggle_turns_it_off_without_touching_the_approval(
    cog, bot, member, lead, db
):
    await bot.store.set(GUILD, "events_create_scheduled", False)
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    await approve(bot, lead, row["id"])

    assert bot.guild.scheduled == []
    assert (await get_event(db, row["id"]))["status"] == APPROVED


async def test_a_scheduled_event_discord_refuses_is_a_failure_not_a_dry_run(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    bot.guild.scheduled_raises = refused()

    await approve(bot, lead, row["id"])

    kinds = await action_kinds(db)
    assert "event.create_scheduled_failed" in kinds
    assert "event.would_create_scheduled" not in kinds
    assert (await get_event(db, row["id"]))["status"] == APPROVED


async def test_the_announcement_only_lets_the_configured_role_ping(cog, bot, member, lead, db):
    await bot.store.set(GUILD, "events_ping_role_id", 4242)
    await submit(cog, bot, member, title="@everyone come here")
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    await approve(bot, lead, row["id"])

    posted = bot.guild.get_channel(TEST_CHANNEL).messages[-1]
    assert posted.kwargs["allowed_mentions"].everyone is False
    assert [r.id for r in posted.kwargs["allowed_mentions"].roles] == [4242]
    assert posted.content.startswith("<@&4242> ")
    assert "event.announce" in await action_kinds(db)


async def test_shadow_mode_computes_everything_and_announces_nothing(cog, bot, member, lead, db):
    await bot.store.set(GUILD, "events_mode", "shadow")
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    before = len(bot.guild.get_channel(TEST_CHANNEL).messages)

    await approve(bot, lead, row["id"])

    assert len(bot.guild.get_channel(TEST_CHANNEL).messages) == before
    assert (await get_event(db, row["id"]))["status"] == APPROVED
    assert "event.would_announce" in await action_kinds(db)


async def test_denying_asks_for_a_reason_and_sends_it_to_the_requester(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    made = bot.guild.created[0]

    await deny(bot, lead, row["id"], message=made.messages[0])

    fresh = await get_event(db, row["id"])
    assert fresh["status"] == DENIED
    assert fresh["deny_reason"] == "clashes with the marathon"
    assert made.name == "denied-alice-block-party"
    assert "clashes with the marathon" in member.dms[-1]["content"]
    assert bot.guild.scheduled == []
    assert "event.denied" in await action_kinds(db)


async def test_someone_who_is_not_staff_cannot_decide(cog, bot, member, db):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    interaction = await approve(bot, member, row["id"])

    assert (await get_event(db, row["id"]))["status"] == PENDING
    assert "staff only" in interaction.sent


async def test_two_mods_deciding_at_once_leave_one_of_them_told_they_lost(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    other = FakeMember(bot.guild, user_id=2, display_name="Other", manage_guild=True)
    one = FakeInteraction(bot, lead)
    two = FakeInteraction(bot, other)

    await asyncio.gather(
        DecisionButton(row["id"], "approve").callback(one),
        DecisionButton(row["id"], "approve").callback(two),
    )

    said = [one.sent, two.sent]
    assert any(text and text.startswith("Approved") for text in said)
    assert any(text and "already **approved**" in text for text in said)
    assert (await action_kinds(db)).count("event.approved") == 1


async def test_a_decided_event_refuses_the_other_button(cog, bot, member, lead, db):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    await approve(bot, lead, row["id"])

    interaction = await deny(bot, lead, row["id"])

    assert interaction.response.modals == []
    assert "already **approved**" in interaction.sent
    assert (await get_event(db, row["id"]))["status"] == APPROVED


async def test_a_click_on_an_event_black_bloc_forgot_says_so(cog, bot, lead):
    interaction = await approve(bot, lead, 4242)

    assert "no record of that event" in interaction.sent


async def test_the_buttons_are_refused_from_outside_the_test_channel(cog, bot, member, lead, db):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    bot.guard = FakeGuard(test_channel_id=404)
    interaction = FakeInteraction(bot, lead)

    await DecisionButton(row["id"], "approve").callback(interaction)

    assert interaction.sent == "test mode"
    assert (await get_event(db, row["id"]))["status"] == PENDING


async def test_the_go_live_loop_picks_exactly_the_events_that_have_started(cog, bot, db):
    due = await store_event(db, status=APPROVED, starts_in=-timedelta(minutes=1))
    later = await store_event(db, status=APPROVED, starts_in=timedelta(hours=1))
    unapproved = await store_event(db, status=PENDING, starts_in=-timedelta(minutes=1))

    await cog.run_due_events()

    assert (await get_event(db, due))["status"] == LIVE
    assert (await get_event(db, later))["status"] == APPROVED
    assert (await get_event(db, unapproved))["status"] == PENDING
    posted = bot.guild.get_channel(TEST_CHANNEL).messages[-1]
    assert "Block Party** is starting now!" in posted.content


async def test_an_event_that_is_over_becomes_done_and_its_channel_is_renamed(cog, bot, db):
    channel = bot.guild.add(FakeText(700, name="approved-alice-block-party"))
    event_id = await store_event(
        db, status=LIVE, starts_in=-timedelta(hours=3), minutes=60, channel_id=channel.id
    )

    await cog.run_due_events()

    assert (await get_event(db, event_id))["status"] == DONE
    assert channel.name == "done-900-block-party"
    assert "event.done" in await action_kinds(db)


async def test_a_review_channel_that_is_gone_cancels_its_event(cog, bot, db):
    event_id = await store_event(db, channel_id=4242)

    await cog.reconcile_events()

    assert (await get_event(db, event_id))["status"] == CANCELLED
    assert "event.cancelled" in await action_kinds(db)


async def test_an_event_whose_channel_is_still_there_is_left_alone(cog, bot, db):
    channel = bot.guild.add(FakeText(700, name="pending-alice-block-party"))
    event_id = await store_event(db, channel_id=channel.id)

    await cog.reconcile_events()

    assert (await get_event(db, event_id))["status"] == PENDING


async def test_a_row_that_never_got_a_channel_is_cancelled_only_once_it_is_stale(cog, bot, db):
    event_id = await store_event(db)

    await cog.reconcile_events()
    assert (await get_event(db, event_id))["status"] == PENDING

    await db.conn.execute(
        "UPDATE events SET created_at = ? WHERE id = ?",
        ((datetime.now(UTC) - timedelta(hours=1)).isoformat(), event_id),
    )
    await db.conn.commit()
    await cog.reconcile_events()

    assert (await get_event(db, event_id))["status"] == CANCELLED


async def test_a_finished_event_s_channel_is_deleted_once_the_retention_has_passed(cog, bot, db):
    old = bot.guild.add(FakeText(700, name="done-alice-old"))
    fresh = bot.guild.add(FakeText(701, name="done-alice-fresh"))
    stale_id = await store_event(
        db, status=DONE, starts_in=-timedelta(days=10), minutes=60, channel_id=old.id
    )
    await store_event(
        db, status=DONE, starts_in=-timedelta(hours=2), minutes=60, channel_id=fresh.id
    )

    await cog.reconcile_events()

    assert old.deleted is True and fresh.deleted is False
    assert (await get_event(db, stale_id))["review_channel_id"] is None
    assert "event.channel_deleted" in await action_kinds(db)


async def test_a_retention_of_zero_days_deletes_a_finished_channel_at_once(cog, bot, db):
    await bot.store.set(GUILD, "events_channel_retention_days", 0)
    channel = bot.guild.add(FakeText(700, name="done-alice-block-party"))
    await store_event(
        db, status=DONE, starts_in=-timedelta(minutes=90), minutes=60, channel_id=channel.id
    )

    await cog.reconcile_events()

    assert channel.deleted is True


async def test_deleting_the_events_category_makes_black_bloc_forget_it(cog, bot, db):
    category = bot.guild.get_channel(CATEGORY)
    category.guild = bot.guild

    await cog.on_guild_channel_delete(category)

    assert bot.store.get(GUILD, "events_category_id") is None
    assert "event.category_forgotten" in await action_kinds(db)


async def test_deleting_a_review_channel_cancels_its_event_without_waiting_for_the_loop(
    cog, bot, member, db
):
    await submit(cog, bot, member)
    made = bot.guild.created[0]
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    await cog.on_guild_channel_delete(made)

    assert (await get_event(db, row["id"]))["status"] == CANCELLED
    assert await event_for_channel(db, made.id) is not None


async def test_the_requester_may_cancel_their_own_event_and_a_stranger_may_not(
    cog, bot, member, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")

    refusal = FakeInteraction(bot, stranger)
    await cog.event_cancel.callback(cog, refusal, str(row["id"]))
    assert (await get_event(db, row["id"]))["status"] == PENDING
    assert "not yours" in refusal.sent.lower()

    mine = FakeInteraction(bot, member)
    await cog.event_cancel.callback(cog, mine, str(row["id"]))
    assert (await get_event(db, row["id"]))["status"] == CANCELLED
    assert bot.guild.created[0].name == "cancelled-alice-block-party"


async def test_staff_may_cancel_anybody_s_event_and_the_requester_is_told(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    interaction = FakeInteraction(bot, lead)
    await cog.event_cancel.callback(cog, interaction, f"#{row['id']}")

    assert (await get_event(db, row["id"]))["status"] == CANCELLED
    assert "cancelled" in member.dms[-1]["content"]
    assert str(row["id"]) in interaction.sent


async def test_cancelling_something_already_settled_says_so(cog, bot, member, lead, db):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    await deny(bot, lead, row["id"])

    interaction = FakeInteraction(bot, lead)
    await cog.event_cancel.callback(cog, interaction, str(row["id"]))

    assert "already **denied**" in interaction.sent


async def test_cancel_refuses_something_that_is_not_a_number(cog, bot, member):
    interaction = FakeInteraction(bot, member)

    await cog.event_cancel.callback(cog, interaction, "the block party")

    assert "not an event number" in interaction.sent


async def test_the_list_names_the_staff_who_may_approve_and_what_is_waiting(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)

    interaction = FakeInteraction(bot, lead)
    await cog.event_list.callback(cog, interaction)

    assert "Lead" in interaction.sent and "Block Party" in interaction.sent
    assert interaction.response.messages[-1]["allowed_mentions"].everyone is False


async def test_the_list_warns_loudly_when_no_staff_role_resolves(cog, bot, lead, db):
    bot.guild.get_channel(TEST_CHANNEL).visible_to = set()

    interaction = FakeInteraction(bot, lead)
    await cog.event_list.callback(cog, interaction)

    assert "No staff roles resolve" in interaction.sent


async def test_the_list_is_staff_only(cog, bot, member):
    interaction = FakeInteraction(bot, member)

    await cog.event_list.callback(cog, interaction)

    assert "staff only" in interaction.sent


async def test_settings_shows_everything_and_changes_only_what_was_given(cog, bot, lead, db):
    interaction = FakeInteraction(bot, lead)

    await cog.event_settings.callback(cog, interaction, retention_days=3)

    assert bot.store.get(GUILD, "events_channel_retention_days") == 3
    assert bot.store.get(GUILD, "events_category_id") == CATEGORY
    assert "3 day(s)" in interaction.sent
    assert "event.settings" in await action_kinds(db)


async def test_settings_can_stop_pinging_anybody(cog, bot, lead):
    await bot.store.set(GUILD, "events_ping_role_id", 4242)

    interaction = FakeInteraction(bot, lead)
    await cog.event_settings.callback(cog, interaction, clear_ping_role=True)

    assert bot.store.get(GUILD, "events_ping_role_id") is None
    assert "nobody" in interaction.sent


async def test_settings_is_staff_only(cog, bot, member):
    interaction = FakeInteraction(bot, member)

    await cog.event_settings.callback(cog, interaction, retention_days=3)

    assert bot.store.get(GUILD, "events_channel_retention_days") != 3
    assert "staff only" in interaction.sent


async def test_the_review_view_is_persistent_and_registered_for_restarts(cog, bot):
    view = review_view(9)

    assert view.timeout is None
    assert [item.custom_id for item in view.children] == ["event:9:approve", "event:9:deny"]

    await cog.cog_load()
    try:
        assert DecisionButton in bot.dynamic
    finally:
        await cog.cog_unload()


async def test_the_two_loops_run_at_their_own_pace_and_stop_with_the_cog(cog, bot):
    assert cog._golive_loop.minutes == GOLIVE_MINUTES
    assert cog._reconcile_loop.minutes == RECONCILE_MINUTES

    await cog.cog_load()
    assert cog._golive_loop.is_running() and cog._reconcile_loop.is_running()

    await cog.cog_unload()
    await asyncio.sleep(0)
    assert cog._golive_loop.is_running() is False
    assert cog._reconcile_loop.is_running() is False


async def test_the_decision_is_recorded_before_the_mod_is_answered(cog, bot, member, lead, db):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    interaction = FakeInteraction(bot, lead)
    when_answered = []

    async def watching_followup(content=None, ephemeral=False, **kwargs):
        when_answered.append((await get_event(db, row["id"]))["status"])

    interaction.followup.send = watching_followup
    await DecisionButton(row["id"], "approve").callback(interaction)

    assert when_answered == [APPROVED]


async def test_a_scheduled_event_is_made_before_the_cosmetic_rename(cog, bot, member, lead, db):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    made = bot.guild.created[0]
    order = []
    original_edit = made.edit

    async def watching_edit(**kwargs):
        order.append("rename")
        await original_edit(**kwargs)

    original_create = bot.guild.create_scheduled_event

    async def watching_create(**kwargs):
        order.append("scheduled")
        return await original_create(**kwargs)

    made.edit = watching_edit
    bot.guild.create_scheduled_event = watching_create

    await approve(bot, lead, row["id"])

    assert order == ["scheduled", "rename"]


async def test_a_rename_discord_refuses_does_not_undo_the_approval(cog, bot, member, lead, db):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    bot.guild.created[0].edit_raises = refused()

    await approve(bot, lead, row["id"])

    assert (await get_event(db, row["id"]))["status"] == APPROVED
    assert "event.rename_failed" in await action_kinds(db)


async def test_a_deny_modal_carries_the_event_it_was_opened_for(cog, bot, member, lead, db):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    interaction = FakeInteraction(bot, lead)

    await DecisionButton(row["id"], "deny").callback(interaction)

    modal = interaction.response.modals[0]
    assert isinstance(modal, DenyModal) and modal.event_id == row["id"]
