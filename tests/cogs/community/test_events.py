import asyncio
import json
import re
from datetime import UTC, datetime, timedelta

import discord
import pytest

from black_bloc import events as events_pure
from black_bloc import logs_panel
from black_bloc.cogs.community import events as events_cog
from black_bloc.cogs.community.events import (
    GOLIVE_MINUTES,
    RECONCILE_MINUTES,
    CallOffPick,
    DecisionButton,
    DenyModal,
    EventDraftPanel,
    EventPick,
    Events,
    EventTextModal,
    EventView,
    ForgetPick,
    LogsButton,
    NoteModal,
    NumbersModal,
    ProposeButton,
    SettingsButton,
    WhereModal,
    WherePanel,
    ZoneModal,
    decision_id,
    review_view,
    submit_draft,
)
from black_bloc.config import load_settings
from black_bloc.events import (
    APPROVED,
    CANCELLED,
    DENIED,
    DONE,
    DRAFT_TITLE,
    LIVE,
    PANEL_TITLE,
    PENDING,
    WHERE_OTHER,
    WHERE_PANEL_TITLE,
    WHERE_TEXT,
    WHERE_UNSET,
    WHERE_VOICE,
    ZONE_PANEL_TITLE,
    EventDraft,
    Where,
    create_event,
    event_for_channel,
    events_by_status,
    get_event,
    rename_channel,
    set_review,
    set_status,
)
from black_bloc.settings_store import (
    DEFAULT_TIMEZONE_KEY,
    EVENTS_TEST_RETENTION_KEY,
    TIME_STEP_KEY,
    TIMEZONE_CHOICES_KEY,
    SettingsStore,
)
from black_bloc.timezones import (
    DEFAULT_TZ,
    get_timezone,
    local_time,
    set_timezone,
    stored_timezone,
)
from black_bloc.when_picker import (
    DAY_PLACEHOLDER,
    DURATION_PLACEHOLDER,
    HOUR_PLACEHOLDER,
    LATER_VALUE,
    MINUTE_PLACEHOLDER,
    OTHER_VALUE,
    ZONE_PLACEHOLDER,
    WhenDraft,
    parse_day,
)

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
        embed = kwargs.get("embed")
        self.embeds = list(kwargs.get("embeds") or ([embed] if embed is not None else []))
        self.view = kwargs.get("view")

    async def edit(self, **kwargs):
        self.edits.append(kwargs)
        self.kwargs = kwargs
        if "embeds" in kwargs:
            self.embeds = list(kwargs["embeds"])
        elif kwargs.get("embed") is not None:
            self.embeds = [kwargs["embed"]]
        if "view" in kwargs:
            self.view = kwargs["view"]


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
        self.type = discord.ChannelType.text
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

    def get_partial_message(self, message_id):
        return next((m for m in self.messages if m.id == message_id), FakeMessage(message_id, ""))

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


class FakeVoice:
    """A voice or stage channel — what the Where picker points a scheduled event at."""

    def __init__(self, channel_id, name="Raid Night", stage=False):
        self.id = channel_id
        self.name = name
        self.guild = None
        self.category = None
        self.category_id = None
        self.mention = f"<#{channel_id}>"
        self.type = discord.ChannelType.stage_voice if stage else discord.ChannelType.voice


class FakeScheduledEvent:
    def __init__(self, event_id, kwargs, status=discord.EventStatus.scheduled):
        self.id = event_id
        self.kwargs = kwargs
        self.url = f"https://discord.com/events/{GUILD}/{event_id}"
        self.status = status
        self.cancelled = False
        self.ended = False

    async def cancel(self, reason=None):
        if self.status is not discord.EventStatus.scheduled:
            raise ValueError("This scheduled event is already running.")
        self.cancelled = True

    async def end(self, reason=None):
        if self.status is not discord.EventStatus.active:
            raise ValueError("This scheduled event is not active.")
        self.ended = True

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
        self.fetch_raises = None
        self.cached_scheduled = True
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

    def get_scheduled_event(self, event_id):
        if not self.cached_scheduled:
            return None
        return next((e for e in self.scheduled if e.id == event_id), None)

    async def fetch_scheduled_event(self, event_id):
        if self.fetch_raises is not None:
            raise self.fetch_raises
        return next((e for e in self.scheduled if e.id == event_id), None)


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
    def __init__(self, test_channel_id=TEST_CHANNEL, category_id=CATEGORY):
        self.test_channel_id = test_channel_id
        self.category_id = category_id

    def allows_channel(self, channel):
        return getattr(channel, "id", channel) == self.test_channel_id

    def allows_place(self, channel):
        if self.allows_channel(channel):
            return True
        found = getattr(channel, "category_id", None)
        return found is not None and found == self.category_id

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
        self._cog = None

    def get_cog(self, name):
        return self._cog

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
        self._edited = None
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)

    async def edit_original_response(self, **kwargs):
        self._edited = FakeMessage(9500, kwargs.get("content") or "", **kwargs)
        return self._edited

    async def original_response(self):
        last = self.response.messages[-1]
        kept = {k: v for k, v in last.items() if k not in ("ephemeral", "content", "deferred")}
        self._edited = FakeMessage(9500, last.get("content") or "", **kept)
        return self._edited

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
    found = Events(bot)
    bot._cog = found
    return found


@pytest.fixture
def member(bot):
    return FakeMember(bot.guild)


@pytest.fixture
def lead(bot):
    return FakeMember(bot.guild, user_id=1, display_name="Lead", manage_guild=True)


async def open_panel(cog, bot, who):
    interaction = FakeInteraction(bot, who)
    await cog.event.callback(cog, interaction)
    return interaction


def panel_view(interaction):
    return interaction.response.messages[-1]["view"]


def panel_embed(interaction):
    return interaction.response.messages[-1]["embed"]


def find_select(view, placeholder):
    return next(
        item for item in view.children if getattr(item, "placeholder", None) == placeholder
    )


def find_item(view, label):
    return next(item for item in view.children if getattr(item, "label", None) == label)


def has_item(view, label):
    return any(getattr(item, "label", None) == label for item in view.children)


async def click(bot, who, item):
    interaction = FakeInteraction(bot, who)
    await item.callback(interaction)
    return interaction


def card_embed(interaction):
    return interaction._edited.kwargs.get("embed")


def card_view(interaction):
    return interaction._edited.kwargs.get("view")


class FakePicked:
    """What a ChannelSelect/RoleSelect hands its callback: something with an id."""

    def __init__(self, picked_id, kind=None):
        self.id = picked_id
        self.type = discord.ChannelType[kind] if kind else None


def pick(select, values):
    select._values = list(values)
    return select


async def zone_modal(cog, bot, who, typed):
    modal = ZoneModal(cog)
    modal.zone._value = typed
    interaction = FakeInteraction(bot, who)
    await modal.on_submit(interaction)
    return interaction


async def test_setting_a_timezone_confirms_it_with_the_local_time(cog, bot, member, db):
    interaction = await zone_modal(cog, bot, member, "Europe/London")

    assert await get_timezone(db, member.id) == "Europe/London"
    assert "Europe/London" in interaction.sent
    assert interaction.response.messages[-1]["ephemeral"] is True


async def test_a_timezone_black_bloc_does_not_know_is_refused_with_a_suggestion(
    cog, bot, member, db
):
    interaction = await zone_modal(cog, bot, member, "Phoenix")

    assert await get_timezone(db, member.id) == DEFAULT_TZ
    assert "Phoenix" in interaction.sent and "Did you mean" in interaction.sent
    assert "America/Phoenix" in interaction.sent
    assert interaction.response.messages[-1]["allowed_mentions"].everyone is False


async def test_a_zone_nothing_resembles_is_refused_without_a_guess(cog, bot, member, db):
    interaction = await zone_modal(cog, bot, member, "Middle/Earth")

    assert await get_timezone(db, member.id) == DEFAULT_TZ
    assert "Middle/Earth" in interaction.sent and "Did you mean" not in interaction.sent


async def test_the_panel_names_the_default_zone_until_someone_chooses(cog, bot, member, db):
    first = await open_panel(cog, bot, member)
    assert DEFAULT_TZ in panel_embed(first).description
    assert "not set a time zone" in panel_embed(first).description

    await set_timezone(db, member.id, "Asia/Tokyo")
    second = await open_panel(cog, bot, member)
    assert "Asia/Tokyo" in panel_embed(second).description
    assert "not set a time zone" not in panel_embed(second).description


async def test_my_time_zone_opens_the_dropdown_with_the_stored_zone_already_picked(
    cog, bot, member, db
):
    await set_timezone(db, member.id, "Asia/Tokyo")
    panel = await open_panel(cog, bot, member)

    interaction = await click(bot, member, find_item(panel_view(panel), "My time zone"))

    picker = find_select(card_view(interaction), ZONE_PLACEHOLDER)
    assert [one.value for one in picker.options if one.default] == ["Asia/Tokyo"]
    assert picker.options[-1].value == OTHER_VALUE
    assert interaction.response.modals == []


async def test_other_type_it_opens_the_typed_door_prefilled_with_the_stored_zone(
    cog, bot, member, db
):
    await set_timezone(db, member.id, "Asia/Tokyo")
    panel = await open_panel(cog, bot, member)
    opened = await click(bot, member, find_item(panel_view(panel), "My time zone"))

    picker = pick(find_select(card_view(opened), ZONE_PLACEHOLDER), [OTHER_VALUE])
    typed = await click(bot, member, picker)

    assert isinstance(typed.response.modals[0], ZoneModal)
    assert typed.response.modals[0].zone.default == "Asia/Tokyo"


async def test_picking_a_zone_from_the_dropdown_stores_it_and_goes_back_to_the_panel(
    cog, bot, member, db
):
    panel = await open_panel(cog, bot, member)
    opened = await click(bot, member, find_item(panel_view(panel), "My time zone"))

    picker = pick(find_select(card_view(opened), ZONE_PLACEHOLDER), ["Europe/London"])
    picked = await click(bot, member, picker)

    assert await get_timezone(db, member.id) == "Europe/London"
    assert "Europe/London" in picked.sent
    assert card_embed(picked).title == PANEL_TITLE


async def test_the_zone_dropdown_offers_what_the_setting_names_and_nothing_else(
    cog, bot, member
):
    await bot.store.set(GUILD, TIMEZONE_CHOICES_KEY, "Europe/London, Asia/Tokyo")
    panel = await open_panel(cog, bot, member)

    opened = await click(bot, member, find_item(panel_view(panel), "My time zone"))

    picker = find_select(card_view(opened), ZONE_PLACEHOLDER)
    assert [one.value for one in picker.options] == [
        "Europe/London",
        "Asia/Tokyo",
        OTHER_VALUE,
    ]


async def test_the_zone_button_only_shows_where_a_member_types_a_time(cog, bot, member):
    on = await open_panel(cog, bot, member)
    assert has_item(panel_view(on), "My time zone")

    await bot.store.set(GUILD, "events_mode", "off")
    off = await open_panel(cog, bot, member)
    assert not has_item(panel_view(off), "My time zone")
    assert not has_item(panel_view(off), "Propose an event")


def future_start(tz_name=DEFAULT_TZ, days=3):
    return local_time(tz_name, datetime.now(UTC) + timedelta(days=days))


def future_day(days=3):
    return (datetime.now(UTC) + timedelta(days=days)).date()


def draft_fields(**fields):
    """A filled `EventDraft`; a start the picker could never produce lands as a typed date."""
    when = WhenDraft(zone=fields.pop("tz", DEFAULT_TZ))
    start = fields.pop("start", future_start())
    day = parse_day(str(start)[:10])
    clock = str(start)[11:16]
    if day is not None and re.fullmatch(r"\d{2}:\d{2}", clock):
        when.day = day
        when.hour, when.minute = (int(part) for part in clock.split(":"))
    else:
        when.later_text = str(start)
    return EventDraft(
        when=when,
        title=fields.pop("title", "Block Party"),
        description=fields.pop("description", "bring a chair"),
        where=fields.pop("where", Where(WHERE_OTHER, None, "the park")),
        duration=fields.pop("duration", "1h30m"),
    )


def draft_panel(fields):
    return EventDraftPanel(10, fields)


async def open_draft_panel(cog, bot, member):
    panel = await open_panel(cog, bot, member)
    opened = await click(bot, member, find_item(panel_view(panel), "Propose an event"))
    return opened, card_view(opened)


async def submit(cog, bot, member, **fields):
    """Every proposal goes through the panel's own Submit path, gate and all."""
    view = draft_panel(draft_fields(**fields))
    interaction = FakeInteraction(bot, member)
    await submit_draft(interaction, view)
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
        where=Where(WHERE_OTHER, None, "the park"),
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


async def test_the_review_channel_is_staff_only_plus_the_person_who_proposed_it(
    cog, bot, member
):
    await submit(cog, bot, member)

    overwrites = bot.guild.created[0].given_overwrites
    assert overwrites[bot.guild.default_role].view_channel is False
    assert overwrites[bot.guild.roles[0]].view_channel is True
    mine = overwrites[member]
    assert mine.view_channel is True and mine.send_messages is True
    assert mine.read_message_history is True


async def test_a_rename_leaves_the_requesters_overwrite_alone(cog, bot, member, db):
    await submit(cog, bot, member)
    made = bot.guild.created[0]
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    await rename_channel(bot, bot.guild, row, DONE, member.display_name)

    assert made.name.startswith("done-")
    assert made.given_overwrites[member].view_channel is True


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


async def test_a_typed_date_black_bloc_cannot_read_is_refused_with_an_example(
    cog, bot, member, db
):
    interaction = await submit(cog, bot, member, start="next tuesday")

    assert await events_by_status(db, GUILD, (PENDING,)) == []
    assert bot.guild.created == []
    assert "next tuesday" in interaction.sent and "YYYY-MM-DD" in interaction.sent


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
    panel = await open_panel(cog, bot, member)
    assert "turned off" in panel_embed(panel).description

    button = ProposeButton()
    interaction = await click(bot, member, button)

    assert interaction.response.modals == []
    assert "turned off" in interaction.sent


async def test_create_refuses_when_there_is_no_category_to_put_it_in(cog, bot, member, db):
    await bot.store.clear(GUILD, "events_category_id")

    interaction = await submit(cog, bot, member)

    assert bot.guild.created == []
    assert "Settings" in interaction.sent and "category" in interaction.sent


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
    bot.guard = FakeGuard(test_channel_id=404, category_id=None)

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
    bot.guard = FakeGuard(test_channel_id=404, category_id=None)
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


async def test_a_review_channel_that_is_gone_twice_running_cancels_its_event(cog, bot, db):
    event_id = await store_event(db, channel_id=4242)

    await cog.reconcile_events()
    assert (await get_event(db, event_id))["status"] == PENDING

    await cog.reconcile_events()

    assert (await get_event(db, event_id))["status"] == CANCELLED
    assert "event.cancelled" in await action_kinds(db)


async def test_a_channel_that_comes_back_before_the_second_pass_is_not_cancelled(cog, bot, db):
    event_id = await store_event(db, channel_id=700)

    await cog.reconcile_events()
    bot.guild.add(FakeText(700, name="pending-alice-block-party"))
    await cog.reconcile_events()
    await cog.reconcile_events()

    assert (await get_event(db, event_id))["status"] == PENDING


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


async def test_the_shortest_retention_is_one_day_and_it_deletes_a_day_old_channel(cog, bot, db):
    await bot.store.set(GUILD, "events_channel_retention_days", 1)
    channel = bot.guild.add(FakeText(700, name="done-alice-block-party"))
    await store_event(
        db, status=DONE, starts_in=-timedelta(days=2), minutes=60, channel_id=channel.id
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


async def call_off_from_panel(cog, bot, who, event_id):
    """The member's own `Call one off…` select, then `Yes, call it off`."""
    panel = await open_panel(cog, bot, who)
    select = next(
        item for item in panel_view(panel).children if isinstance(item, CallOffPick)
    )
    select._values = [str(event_id)]
    picked = await click(bot, who, select)
    return await click(bot, who, find_item(card_view(picked), "Yes, call it off"))


async def test_the_yes_re_asks_may_cancel_rather_than_trusting_the_opener(cog, bot, member, db):
    """A gate can close while a card is open, so the Yes re-asks instead of trusting the pin."""
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    stranger = FakeMember(bot.guild, user_id=USER + 7, display_name="Bo")
    interaction = FakeInteraction(bot, stranger)

    await events_cog.confirm_cancel(interaction, row["id"])

    assert (await get_event(db, row["id"]))["status"] == PENDING
    assert "already" in interaction.response.messages[-1]["content"]


async def test_the_call_off_confirm_card_silences_mentions(cog, bot, member, db):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    panel = await open_panel(cog, bot, member)
    select = next(item for item in panel_view(panel).children if isinstance(item, CallOffPick))
    select._values = [str(row["id"])]

    picked = await click(bot, member, select)
    allowed = picked._edited.kwargs.get("allowed_mentions")

    assert [item.label for item in card_view(picked).children] == [
        "Yes, call it off",
        "Keep it",
    ]
    assert allowed is not None
    assert (allowed.everyone, allowed.users, allowed.roles) == (False, False, False)


async def test_the_requester_may_call_their_own_event_off_and_a_stranger_never_sees_it(
    cog, bot, member, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    stranger = FakeMember(bot.guild, user_id=USER + 1, display_name="Bo")

    theirs = await open_panel(cog, bot, stranger)
    assert not any(isinstance(one, CallOffPick) for one in panel_view(theirs).children)

    interaction = await call_off_from_panel(cog, bot, member, row["id"])

    assert (await get_event(db, row["id"]))["status"] == CANCELLED
    assert bot.guild.created[0].name == "cancelled-alice-block-party"
    assert str(row["id"]) in interaction.sent


async def test_staff_may_call_anybody_s_event_off_with_a_line_the_requester_is_sent(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    _, view = events_cog.build_card(bot, bot.guild, await get_event(db, row["id"]), lead)

    opened = await click(bot, lead, find_item(view, "Call it off"))
    modal = opened.response.modals[0]
    modal.note._value = "the park is shut"
    interaction = FakeInteraction(bot, lead)
    await modal.on_submit(interaction)

    assert (await get_event(db, row["id"]))["status"] == CANCELLED
    assert "cancelled" in member.dms[-1]["content"]
    assert "the park is shut" in member.dms[-1]["content"]
    assert str(row["id"]) in interaction.sent


async def test_the_staff_note_is_optional_and_an_empty_one_still_calls_it_off(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    modal = NoteModal(cog, row["id"], "cancel")
    modal.note._value = ""

    interaction = FakeInteraction(bot, lead)
    await modal.on_submit(interaction)

    assert modal.note.required is False
    assert (await get_event(db, row["id"]))["status"] == CANCELLED
    assert "The reason given was" not in member.dms[-1]["content"]


async def test_calling_off_something_already_settled_says_so(cog, bot, member, lead, db):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    await deny(bot, lead, row["id"])
    modal = NoteModal(cog, row["id"], "cancel")
    modal.note._value = ""

    interaction = FakeInteraction(bot, lead)
    await modal.on_submit(interaction)

    assert "already **denied**" in interaction.sent


async def test_a_number_nobody_proposed_is_read_as_nothing(cog, bot):
    assert events_pure.wanted_event_id("the block party") is None
    assert events_pure.wanted_event_id("#12") == 12
    assert events_pure.wanted_event_id(" 12 ") == 12


async def test_the_staff_panel_names_the_staff_who_may_approve_and_what_is_waiting(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)

    interaction = await open_panel(cog, bot, lead)

    assert "Block Party" in panel_embed(interaction).description
    assert "1 pending" in panel_embed(interaction).description.replace("**", "")
    assert interaction.response.messages[-1]["allowed_mentions"].everyone is False


async def test_the_staff_panel_warns_loudly_when_no_staff_role_resolves(cog, bot, lead, db):
    bot.guild.get_channel(TEST_CHANNEL).visible_to = set()

    interaction = await open_panel(cog, bot, lead)

    assert "No staff roles resolve" in panel_embed(interaction).description


async def test_a_member_never_sees_the_staff_half_of_the_panel(cog, bot, member, db):
    await submit(cog, bot, member)

    interaction = await open_panel(cog, bot, member)
    view = panel_view(interaction)

    assert not any(isinstance(one, EventPick) for one in view.children)
    assert not any(isinstance(one, LogsButton) for one in view.children)
    assert not has_item(view, "Settings")
    assert "Block Party" not in panel_embed(interaction).description


async def test_a_member_sees_their_own_events_only_when_the_key_is_on(cog, bot, member, db):
    await submit(cog, bot, member)

    off = await open_panel(cog, bot, member)
    assert "Block Party" not in panel_embed(off).description

    await bot.store.set(GUILD, "event_panel_own_list", True)
    on = await open_panel(cog, bot, member)
    assert "Block Party" in panel_embed(on).description


async def settings_panel(cog, bot, lead):
    panel = await open_panel(cog, bot, lead)
    return await click(bot, lead, find_item(panel_view(panel), "Settings"))


async def test_the_settings_sub_panel_shows_everything_and_writes_one_key_at_a_time(
    cog, bot, lead, db
):
    opened = await settings_panel(cog, bot, lead)
    modal = NumbersModal(cog, 1, 30)
    modal.retention._value = "3"
    modal.late._value = "30"

    interaction = FakeInteraction(bot, lead)
    await modal.on_submit(interaction)

    assert "Events — settings" in card_embed(opened).title
    assert bot.store.get(GUILD, "events_channel_retention_days") == 3
    assert bot.store.get(GUILD, "events_category_id") == CATEGORY
    assert "3 day(s)" in card_embed(interaction).description
    assert "event.settings" in await action_kinds(db)


async def test_a_number_outside_its_bounds_is_refused_in_words_and_changes_nothing(
    cog, bot, lead, db
):
    modal = NumbersModal(cog, 1, 30)
    modal.retention._value = "9999"
    modal.late._value = "30"

    interaction = FakeInteraction(bot, lead)
    await modal.on_submit(interaction)

    assert bot.store.get(GUILD, "events_channel_retention_days") != 9999
    assert "9999" in interaction.sent and "between" in interaction.sent


async def test_an_empty_channel_select_clears_the_key_it_owns(cog, bot, lead, db):
    await bot.store.set(GUILD, "events_announce_channel_id", 900)
    select = events_cog.AnnounceSelect()
    select._values = []

    interaction = await click(bot, lead, select)

    assert bot.store.get(GUILD, "events_announce_channel_id") == TEST_CHANNEL
    assert "<#900>" not in card_embed(interaction).description


async def test_a_channel_select_with_a_pick_stores_it(cog, bot, lead, db):
    select = events_cog.AnnounceSelect()
    select._values = [FakePicked(900)]

    interaction = await click(bot, lead, select)

    assert bot.store.get(GUILD, "events_announce_channel_id") == 900
    assert "<#900>" in card_embed(interaction).description


async def test_the_forget_select_clears_the_key_a_client_that_will_not_send_an_empty_one_left(
    cog, bot, lead, db
):
    await bot.store.set(GUILD, "events_ping_role_id", 4242)
    select = ForgetPick()
    select._values = ["events_ping_role_id"]

    interaction = await click(bot, lead, select)

    assert bot.store.get(GUILD, "events_ping_role_id") is None
    assert "nobody" in card_embed(interaction).description


async def test_the_settings_sub_panel_is_staff_only(cog, bot, member, db):
    interaction = await click(bot, member, SettingsButton())

    assert "staff" in interaction.sent.lower()
    assert interaction._edited is None


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


async def test_a_scheduled_event_already_running_is_ended_rather_than_cancelled(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    await approve(bot, lead, row["id"])
    running = bot.guild.scheduled[0]
    running.status = discord.EventStatus.active

    await cog._cancel(bot.guild, await get_event(db, row["id"]), "review_channel_gone")

    assert running.ended is True and running.cancelled is False
    assert "event.cancel_scheduled_failed" not in await action_kinds(db)


async def test_a_scheduled_event_discord_will_not_cancel_is_logged_not_raised(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    await approve(bot, lead, row["id"])
    bot.guild.scheduled[0].status = discord.EventStatus.completed

    await cog._cancel(bot.guild, await get_event(db, row["id"]), "review_channel_gone")

    assert (await get_event(db, row["id"]))["status"] == CANCELLED
    assert "event.cancel_scheduled_failed" in await action_kinds(db)


async def test_a_scheduled_event_missing_from_the_cache_is_fetched_from_discord(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    await approve(bot, lead, row["id"])
    bot.guild.cached_scheduled = False

    await cog._cancel(bot.guild, await get_event(db, row["id"]), "review_channel_gone")

    assert bot.guild.scheduled[0].cancelled is True
    assert "event.cancel_scheduled_failed" not in await action_kinds(db)


async def test_in_test_mode_a_scheduled_event_is_never_cancelled_only_logged(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    await approve(bot, lead, row["id"])
    made = bot.guild.scheduled[0]
    bot.guard = FakeGuard()

    await cog._cancel(bot.guild, await get_event(db, row["id"]), "review_channel_gone")

    assert made.cancelled is False and made.ended is False
    assert "event.would_cancel_scheduled" in await action_kinds(db)


async def test_the_cancel_is_recorded_before_discord_is_asked_to_undo_anything(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    await approve(bot, lead, row["id"])
    seen = []
    made = bot.guild.scheduled[0]

    async def watching_cancel(reason=None):
        seen.append(await action_kinds(db))

    made.cancel = watching_cancel
    await cog._cancel(bot.guild, await get_event(db, row["id"]), "review_channel_gone")

    assert seen and "event.cancelled" in seen[0]


async def test_a_loop_that_raises_records_the_error_and_restarts_itself(cog, bot, caplog):
    restarted = []
    cog._golive_loop.restart = lambda *a, **k: restarted.append(True)

    with caplog.at_level("ERROR"):
        await cog._golive_broke(RuntimeError("the database went away"))

    assert restarted == [True]
    assert "the database went away" in cog.last_error["golive"]
    assert cog.last_error["reconcile"] is None
    assert "the golive loop raised" in caplog.text


async def test_both_loops_carry_their_own_error_handler(cog, bot):
    assert cog._golive_loop._error is not None
    assert cog._reconcile_loop._error is not None


async def test_settings_shows_when_each_loop_last_finished_and_its_last_error(cog, bot, lead):
    cog.last_ok_at["golive"] = "2026-08-26T12:00:00+00:00"
    cog.last_error["reconcile"] = "2026-08-26T11:00:00+00:00 - RuntimeError: boom"

    interaction = await settings_panel(cog, bot, lead)
    said = card_embed(interaction).description

    assert "**golive loop**" in said
    assert "2026-08-26T12:00:00+00:00" in said
    assert "no errors" in said
    assert "**reconcile loop**" in said
    assert "never yet" in said
    assert "RuntimeError: boom" in said


async def test_the_golive_loop_records_when_it_last_finished(cog, bot, db):
    assert cog.last_ok_at["golive"] is None

    await cog._golive_loop.coro(cog)

    assert cog.last_ok_at["golive"] is not None


async def test_an_approved_event_that_already_finished_is_marked_done_and_never_announced(
    cog, bot, member, db
):
    channel = bot.guild.add(FakeText(700, name="approved-alice-block-party"))
    event_id = await store_event(
        db, status=APPROVED, starts_in=-timedelta(hours=5), minutes=60, channel_id=channel.id
    )
    before = len(bot.guild.get_channel(TEST_CHANNEL).messages)

    await cog.run_due_events()

    assert (await get_event(db, event_id))["status"] == DONE
    assert len(bot.guild.get_channel(TEST_CHANNEL).messages) == before
    kinds = await action_kinds(db)
    assert "event.missed" in kinds
    assert "event.go_live" not in kinds
    assert "finished before Black Bloc ever announced it" in member.dms[-1]["content"]
    assert channel.name == "done-alice-block-party"


async def test_an_event_that_started_too_long_ago_goes_live_without_the_announcement(
    cog, bot, member, db
):
    await bot.store.set(GUILD, "events_max_late_minutes", 15)
    event_id = await store_event(
        db, status=APPROVED, starts_in=-timedelta(minutes=40), minutes=180
    )
    before = len(bot.guild.get_channel(TEST_CHANNEL).messages)

    await cog.run_due_events()

    assert (await get_event(db, event_id))["status"] == LIVE
    assert len(bot.guild.get_channel(TEST_CHANNEL).messages) == before
    assert "event.announce_skipped_late" in await action_kinds(db)


async def test_an_event_that_started_a_moment_ago_is_still_announced(cog, bot, db):
    event_id = await store_event(
        db, status=APPROVED, starts_in=-timedelta(minutes=2), minutes=180
    )

    await cog.run_due_events()

    assert (await get_event(db, event_id))["status"] == LIVE
    assert "event.go_live" in await action_kinds(db)


async def test_a_finished_channel_outside_the_test_category_is_logged_not_deleted(cog, bot, db):
    bot.guard = FakeGuard()
    outside = bot.guild.add(FakeText(700, name="done-alice-elsewhere"))
    await store_event(
        db, status=DONE, starts_in=-timedelta(days=10), minutes=60, channel_id=outside.id
    )

    await cog.reconcile_events()

    assert outside.deleted is False
    assert "event.would_delete_channel" in await action_kinds(db)


async def test_an_unreadable_end_time_keeps_the_channel_rather_than_deleting_it(cog, bot, db):
    channel = bot.guild.add(FakeText(700, name="done-alice-block-party"))
    event_id = await store_event(
        db, status=DONE, starts_in=-timedelta(days=10), minutes=60, channel_id=channel.id
    )
    await db.conn.execute("UPDATE events SET ends_at = 'whenever' WHERE id = ?", (event_id,))
    await db.conn.commit()

    await cog.reconcile_events()

    assert channel.deleted is False
    assert "event.channel_deleted" not in await action_kinds(db)


async def test_denied_and_cancelled_channels_are_swept_on_the_same_retention(cog, bot, db):
    denied = bot.guild.add(FakeText(700, name="denied-alice-old"))
    cancelled = bot.guild.add(FakeText(701, name="cancelled-alice-old"))
    await store_event(
        db, status=DENIED, starts_in=-timedelta(days=10), minutes=60, channel_id=denied.id
    )
    await store_event(
        db, status=CANCELLED, starts_in=-timedelta(days=10), minutes=60, channel_id=cancelled.id
    )

    await cog.reconcile_events()

    assert denied.deleted is True and cancelled.deleted is True


async def test_a_rename_outside_the_test_category_is_logged_rather_than_done(cog, bot, db):
    bot.guard = FakeGuard()
    outside = bot.guild.add(FakeText(700, name="approved-alice-block-party"))
    event_id = await store_event(
        db, status=LIVE, starts_in=-timedelta(hours=3), minutes=60, channel_id=outside.id
    )

    await cog.run_due_events()

    assert (await get_event(db, event_id))["status"] == DONE
    assert outside.name == "approved-alice-block-party"
    assert "event.would_rename" in await action_kinds(db)


async def test_the_announcement_links_the_scheduled_event_when_there_is_one(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    await approve(bot, lead, row["id"])

    posted = bot.guild.get_channel(TEST_CHANNEL).messages[-1]
    assert bot.guild.scheduled[0].url in posted.content
    assert "Interested" in posted.content


async def test_the_announcement_promises_no_button_when_there_is_no_scheduled_event(
    cog, bot, member, lead, db
):
    await bot.store.set(GUILD, "events_create_scheduled", False)
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    await approve(bot, lead, row["id"])

    posted = bot.guild.get_channel(TEST_CHANNEL).messages[-1]
    assert "Interested" not in posted.content
    assert "watch this channel" in posted.content


async def test_an_auto_cancelled_event_tells_the_requester_why(cog, bot, member, db):
    event_id = await store_event(db, channel_id=4242)

    await cog._cancel(bot.guild, await get_event(db, event_id), "review_channel_gone")

    assert (await get_event(db, event_id))["status"] == CANCELLED
    assert "no longer there" in member.dms[-1]["content"]
    assert member.dms[-1]["allowed_mentions"].everyone is False


async def test_a_requester_who_cannot_be_dmed_is_a_logged_fact_not_a_silence(cog, bot, member, db):
    member.dm_raises = refused()
    event_id = await store_event(db, channel_id=4242)

    await cog._cancel(bot.guild, await get_event(db, event_id), "review_channel_gone")

    assert "event.dm_failed" in await action_kinds(db)


async def test_cancelling_your_own_event_does_not_dm_you_about_it(cog, bot, member, db):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    before = len(member.dms)

    await call_off_from_panel(cog, bot, member, row["id"])

    assert len(member.dms) == before
    assert (await get_event(db, row["id"]))["status"] == CANCELLED


async def test_a_button_that_explodes_answers_the_clicker_instead_of_dying_silently(
    cog, bot, member, lead, db, monkeypatch, caplog
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    async def explode(*args, **kwargs):
        raise RuntimeError("discord fell over")

    monkeypatch.setattr("black_bloc.cogs.community.events.decide", explode)
    with caplog.at_level("ERROR"):
        interaction = await approve(bot, lead, row["id"])

    assert "hit an error running that command" in interaction.sent
    assert "discord fell over" in caplog.text


async def test_the_deny_modal_answers_a_failure_rather_than_leaving_it_hanging(cog, bot, lead):
    interaction = FakeInteraction(bot, lead)

    await DenyModal(1).on_error(interaction, RuntimeError("discord fell over"))

    assert "hit an error running that command" in interaction.sent


async def test_settings_can_change_how_late_an_announcement_may_be(cog, bot, lead, db):
    modal = NumbersModal(cog, 1, 30)
    modal.retention._value = "1"
    modal.late._value = "45"

    interaction = FakeInteraction(bot, lead)
    await modal.on_submit(interaction)

    assert bot.store.get(GUILD, "events_max_late_minutes") == 45
    assert "45 minute(s)" in card_embed(interaction).description


async def test_an_unavailable_guild_is_left_entirely_alone(cog, bot, db):
    event_id = await store_event(db, channel_id=4242)
    bot.guild.unavailable = True

    await cog.reconcile_events()
    await cog.reconcile_events()

    assert (await get_event(db, event_id))["status"] == PENDING
    assert await action_kinds(db) == []


async def test_an_event_whose_start_cannot_be_read_is_cancelled_and_the_requester_told(
    cog, bot, member, db
):
    channel = bot.guild.add(FakeText(700, name="pending-alice-block-party"))
    event_id = await store_event(db, channel_id=channel.id)
    await db.conn.execute("UPDATE events SET starts_at = 'whenever' WHERE id = ?", (event_id,))
    await db.conn.commit()

    await cog.reconcile_events()

    assert (await get_event(db, event_id))["status"] == CANCELLED
    assert "could not read the start time" in member.dms[-1]["content"]


async def test_cancelling_an_approved_event_edits_its_announcement(cog, bot, member, lead, db):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    await approve(bot, lead, row["id"])
    announced = bot.guild.get_channel(TEST_CHANNEL).messages[-1]

    await cog._cancel(bot.guild, await get_event(db, row["id"]), "review_channel_gone")

    assert "is cancelled" in announced.edits[-1]["content"]
    assert "event.announcement_edited" in await action_kinds(db)


async def test_an_announcement_in_a_channel_the_guard_refuses_is_logged_not_edited(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    await approve(bot, lead, row["id"])
    announced = bot.guild.get_channel(TEST_CHANNEL).messages[-1]
    bot.guard = FakeGuard(test_channel_id=999, category_id=None)

    await cog._cancel(bot.guild, await get_event(db, row["id"]), "review_channel_gone")

    assert announced.edits == []
    assert "event.would_edit_announcement" in await action_kinds(db)


async def test_an_event_that_was_never_announced_edits_nothing(cog, bot, member, db):
    event_id = await store_event(db, channel_id=4242)

    await cog._cancel(bot.guild, await get_event(db, event_id), "review_channel_gone")

    kinds = await action_kinds(db)
    assert "event.announcement_edited" not in kinds
    assert "event.edit_announcement_failed" not in kinds


async def test_in_test_mode_the_card_channel_is_recorded_beside_the_message(cog, bot, member, db):
    bot.guard = FakeGuard()

    await submit(cog, bot, member)

    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    assert row["review_channel_id"] == bot.guild.created[0].id
    assert row["card_channel_id"] == TEST_CHANNEL
    assert row["review_message_id"] is not None


async def test_the_card_channel_is_the_review_channel_when_the_guard_is_off(cog, bot, member, db):
    await submit(cog, bot, member)

    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    assert row["card_channel_id"] == row["review_channel_id"]


async def test_a_test_channel_with_no_category_refuses_rather_than_making_a_loose_channel(
    cog, bot, member, db
):
    bot.guild.get_channel(TEST_CHANNEL).category = None
    bot.guild.get_channel(TEST_CHANNEL).category_id = None
    bot.guard = FakeGuard()

    interaction = await submit(cog, bot, member)

    assert bot.guild.created == []
    assert "TEST_CHANNEL_ID" in interaction.sent


async def test_a_title_that_is_only_spaces_is_refused(cog, bot, member, db):
    interaction = await submit(cog, bot, member, title="   ")

    assert await events_by_status(db, GUILD, (PENDING,)) == []
    assert "needs a name" in interaction.sent


async def test_a_local_time_the_clocks_skip_is_refused_by_name(cog, bot, member, db):
    interaction = await submit(
        cog, bot, member, tz="America/New_York", start="2027-03-14 02:30"
    )

    assert await events_by_status(db, GUILD, (PENDING,)) == []
    assert "never happens" in interaction.sent and "America/New_York" in interaction.sent


async def test_a_local_time_that_happens_twice_is_refused_by_name(cog, bot, member, db):
    interaction = await submit(
        cog, bot, member, tz="America/New_York", start="2027-11-07 01:30"
    )

    assert await events_by_status(db, GUILD, (PENDING,)) == []
    assert "happens twice" in interaction.sent


async def test_the_draft_says_which_zone_the_time_is_read_in(cog, bot, member):
    opened, view = await open_draft_panel(cog, bot, member)

    said = card_embed(opened).description
    assert DEFAULT_TZ in said and "Time zone" in said
    assert card_embed(opened).title == DRAFT_TITLE
    assert has_item(view, "Time zone")


async def test_a_settled_event_stops_being_kept_a_lock(cog, bot, member, lead, db):
    """`denied` keeps its lock now that staff can approve after all; `cancelled` never moves."""
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    await deny(bot, lead, row["id"], message=bot.guild.created[0].messages[0])
    assert row["id"] in getattr(bot, "_event_locks", {})

    await submit(cog, bot, member, title="Second Party")
    second = (await events_by_status(db, GUILD, (PENDING,)))[0]
    await call_off_from_panel(cog, bot, member, second["id"])
    assert second["id"] not in getattr(bot, "_event_locks", {})


async def test_an_approved_event_keeps_its_lock_until_it_is_over(cog, bot, member, lead, db):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    await approve(bot, lead, row["id"])

    assert row["id"] in getattr(bot, "_event_locks", {})


async def test_deleting_the_announce_channel_makes_black_bloc_forget_it(cog, bot, db):
    await bot.store.set(GUILD, "events_announce_channel_id", 900)
    gone = bot.guild.add(FakeText(900, name="live-now"))

    await cog.on_guild_channel_delete(gone)

    assert bot.store.get(GUILD, "events_announce_channel_id") == TEST_CHANNEL
    assert "event.announce_channel_forgotten" in await action_kinds(db)


async def test_settings_can_forget_the_category_and_the_announce_channel(cog, bot, lead, db):
    await bot.store.set(GUILD, "events_announce_channel_id", 900)
    category = events_cog.CategorySelect()
    category._values = []
    announce = events_cog.AnnounceSelect()
    announce._values = []

    await click(bot, lead, category)
    await click(bot, lead, announce)

    assert bot.store.get(GUILD, "events_category_id") is None
    assert bot.store.get(GUILD, "events_announce_channel_id") == TEST_CHANNEL


# --- the panel itself (wave 1) -----------------------------------------------------------------


async def test_the_command_answers_ephemerally_with_a_panel(cog, bot, member):
    interaction = await open_panel(cog, bot, member)

    assert interaction.response.messages[0]["ephemeral"] is True
    assert isinstance(panel_view(interaction), EventView)
    assert panel_embed(interaction).title == events_pure.PANEL_TITLE


async def test_the_command_run_in_a_dm_says_it_belongs_in_the_server(cog, bot, member):
    interaction = FakeInteraction(bot, member)
    interaction.guild = None

    await cog.event.callback(cog, interaction)

    assert "in the server itself" in interaction.sent


async def test_the_command_refuses_in_words_when_the_database_is_down(
    cog, bot, member, monkeypatch
):
    monkeypatch.setattr(bot.db, "_conn", None)
    interaction = FakeInteraction(bot, member)

    await cog.event.callback(cog, interaction)

    assert "cannot reach its own database" in interaction.sent


async def test_a_member_panel_shows_propose_the_zone_and_refresh_and_no_staff_controls(
    cog, bot, member
):
    interaction = await open_panel(cog, bot, member)
    view = panel_view(interaction)

    assert has_item(view, "Propose an event")
    assert has_item(view, "My time zone")
    assert has_item(view, "Refresh")
    assert has_item(view, events_pure.SITE_BUTTON)
    assert not any(isinstance(one, EventPick) for one in view.children)


async def test_a_staff_panel_adds_the_counts_the_select_settings_and_logs(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)

    interaction = await open_panel(cog, bot, lead)
    view = panel_view(interaction)

    assert any(isinstance(one, EventPick) for one in view.children)
    assert any(isinstance(one, LogsButton) for one in view.children)
    assert has_item(view, "Settings")
    assert "pending" in panel_embed(interaction).description


async def test_a_staff_panel_with_nothing_open_says_so_and_drops_the_select(cog, bot, lead):
    interaction = await open_panel(cog, bot, lead)

    assert not any(isinstance(one, EventPick) for one in panel_view(interaction).children)
    assert events_pure.NOTHING_OPEN in panel_embed(interaction).description


async def test_the_staff_select_caps_at_25_and_says_how_many_are_left(cog, bot, lead, db):
    for _ in range(30):
        await store_event(db, channel_id=TEST_CHANNEL)

    interaction = await open_panel(cog, bot, lead)
    select = next(one for one in panel_view(interaction).children if isinstance(one, EventPick))

    assert len(select.options) == 25
    assert select.placeholder == "25 of 30 — the rest are on the site"


async def test_the_open_site_link_appears_only_when_an_origin_is_set(cog, bot, member, db):
    bare = load_settings(
        _env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL, site_origin=""
    )
    bare_bot = FakeBot(db, bot.store, bare, bot.guild)
    bare_bot._cog = Events(bare_bot)

    without = await open_panel(bare_bot._cog, bare_bot, member)

    assert not has_item(panel_view(without), events_pure.SITE_BUTTON)


async def test_the_refresh_button_re_renders_the_panel(cog, bot, member, db):
    await bot.store.set(GUILD, "event_panel_own_list", True)
    panel = await open_panel(cog, bot, member)
    button = find_item(panel_view(panel), "Refresh")
    await submit(cog, bot, member, title="A Fresh One")

    interaction = await click(bot, member, button)

    assert "A Fresh One" in card_embed(interaction).description


# --- the card: exactly the buttons the table says ----------------------------------------------

EXPECTED_BUTTONS = {
    PENDING: ["Approve", "Deny", "Call it off"],
    APPROVED: ["Call it off"],
    LIVE: ["Call it off"],
    DENIED: ["Approve after all"],
    DONE: [],
    CANCELLED: [],
}


@pytest.mark.parametrize("status", events_pure.STATUSES)
async def test_the_card_renders_exactly_the_buttons_the_table_says(cog, bot, lead, db, status):
    event_id = await store_event(db, status=status, channel_id=TEST_CHANNEL)
    row = await get_event(db, event_id)

    embed, view = events_cog.build_card(bot, bot.guild, row, lead)

    labels = [one.label for one in view.children]
    assert labels[: len(EXPECTED_BUTTONS[status])] == EXPECTED_BUTTONS[status]
    assert "Back" in labels
    if not EXPECTED_BUTTONS[status]:
        assert "nothing moves it now" in embed.footer.text
    assert len([one for one in view.children if one.row == 0]) <= 5


async def test_a_denied_card_whose_room_is_gone_says_so_instead_of_offering_a_move(
    cog, bot, lead, db
):
    event_id = await store_event(db, status=DENIED, channel_id=4242)
    row = await get_event(db, event_id)

    embed, view = events_cog.build_card(bot, bot.guild, row, lead)

    assert [one.label for one in view.children] == ["Back"]
    assert "cleaned up" in embed.footer.text


async def test_picking_an_event_opens_its_card(cog, bot, member, lead, db):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    panel = await open_panel(cog, bot, lead)
    select = next(one for one in panel_view(panel).children if isinstance(one, EventPick))
    select._values = [str(row["id"])]

    interaction = await click(bot, lead, select)

    assert card_embed(interaction).title == "Block Party"
    assert [one.label for one in card_view(interaction).children][:3] == EXPECTED_BUTTONS[PENDING]


async def test_picking_a_number_nobody_proposed_says_so_and_stays_on_the_panel(cog, bot, lead):
    select = EventPick([], 0)
    select._values = ["99"]

    interaction = await click(bot, lead, select)

    assert "no record of that event" in interaction.sent


async def test_back_returns_to_the_panel(cog, bot, lead, db):
    event_id = await store_event(db, channel_id=TEST_CHANNEL)
    row = await get_event(db, event_id)
    _, view = events_cog.build_card(bot, bot.guild, row, lead)

    interaction = await click(bot, lead, find_item(view, "Back"))

    assert card_embed(interaction).title == events_pure.PANEL_TITLE


# --- each move calls the shared function, `via` untouched --------------------------------------


async def test_approve_on_the_card_calls_apply_decision_and_leaves_via_alone(
    cog, bot, lead, db, monkeypatch
):
    event_id = await store_event(db, channel_id=TEST_CHANNEL)
    row = await get_event(db, event_id)
    _, view = events_cog.build_card(bot, bot.guild, row, lead)
    calls = []

    async def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return ("moved along", row)

    monkeypatch.setattr(events_cog, "apply_decision", fake)

    interaction = await click(bot, lead, find_item(view, "Approve"))

    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args[0] is bot and args[1] is bot.guild and args[3] == APPROVED
    assert "via" not in kwargs
    assert interaction.sent == "moved along"


async def test_deny_on_the_card_opens_the_note_modal_and_submits_through_apply_decision(
    cog, bot, lead, db, monkeypatch
):
    event_id = await store_event(db, channel_id=TEST_CHANNEL)
    row = await get_event(db, event_id)
    _, view = events_cog.build_card(bot, bot.guild, row, lead)
    opened = await click(bot, lead, find_item(view, "Deny"))
    modal = opened.response.modals[0]
    assert isinstance(modal, NoteModal) and modal.note.required is True
    modal.note._value = "clashes with the marathon"
    calls = []

    async def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return ("denied", row)

    monkeypatch.setattr(events_cog, "apply_decision", fake)

    interaction = FakeInteraction(bot, lead)
    await modal.on_submit(interaction)

    args, kwargs = calls[0]
    assert args[3] == DENIED and args[5] == "clashes with the marathon"
    assert "via" not in kwargs
    assert interaction.sent == "denied"


async def test_call_it_off_on_the_card_submits_through_cancel_for(
    cog, bot, lead, db, monkeypatch
):
    event_id = await store_event(db, channel_id=TEST_CHANNEL)
    row = await get_event(db, event_id)
    modal = NoteModal(cog, event_id, "cancel")
    modal.note._value = "the park is shut"
    calls = []

    async def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return ("called off", row)

    monkeypatch.setattr(events_cog, "cancel_for", fake)

    interaction = FakeInteraction(bot, lead)
    await modal.on_submit(interaction)

    args, kwargs = calls[0]
    assert args[0] is bot and args[1] is bot.guild
    assert kwargs == {"note": "the park is shut"}
    assert interaction.sent == "called off"


async def test_the_panel_and_the_review_card_reach_the_same_decision(cog, bot, member, lead, db):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    _, view = events_cog.build_card(bot, bot.guild, await get_event(db, row["id"]), lead)

    await click(bot, lead, find_item(view, "Approve"))

    assert (await get_event(db, row["id"]))["status"] == APPROVED
    assert "event.approved" in await action_kinds(db)
    assert bot.guild.created[0].name.startswith("approved-")
    assert "approved" in member.dms[-1]["content"]


# --- the gates every click re-asks -------------------------------------------------------------


async def test_a_staffer_demoted_while_a_card_is_open_is_refused_the_move(cog, bot, lead, db):
    event_id = await store_event(db, channel_id=TEST_CHANNEL)
    row = await get_event(db, event_id)
    _, view = events_cog.build_card(bot, bot.guild, row, lead)
    button = find_item(view, "Approve")
    lead.guild_permissions = FakePerms(manage_guild=False)

    interaction = await click(bot, lead, button)

    assert (await get_event(db, event_id))["status"] == PENDING
    assert "staff" in interaction.sent.lower()


async def test_a_database_that_drops_mid_panel_answers_in_words(
    cog, bot, member, monkeypatch
):
    panel = await open_panel(cog, bot, member)
    button = find_item(panel_view(panel), "Refresh")
    monkeypatch.setattr(bot.db, "_conn", None)

    interaction = await click(bot, member, button)

    assert "cannot reach its own database" in interaction.sent


async def test_the_logs_button_answers_a_new_message_and_keeps_its_own_staff_gate(
    cog, bot, member, lead, db
):
    refused_one = await click(bot, member, LogsButton())
    assert "staff" in refused_one.sent.lower()
    assert refused_one._edited is None

    allowed = await click(bot, lead, LogsButton())
    last = allowed.response.messages[-1]
    assert last["ephemeral"] is True
    assert [item.label for item in last["view"].children] == [logs_panel.ONLY_IMPORTANT]


async def test_a_panel_that_goes_quiet_disables_every_item_and_says_so(cog, bot, member):
    interaction = await open_panel(cog, bot, member)
    view = panel_view(interaction)
    view.message = await interaction.original_response()

    await view.on_timeout()

    assert all(item.disabled for item in view.children if hasattr(item, "disabled"))
    assert "gone quiet" in view.message.embeds[0].footer.text


async def test_a_replaced_panel_never_edits_the_render_that_replaced_it(cog, bot, member):
    interaction = await open_panel(cog, bot, member)
    view = panel_view(interaction)
    view.message = await interaction.original_response()

    await click(bot, member, find_item(view, "Refresh"))
    await view.on_timeout()

    assert view.replaced is True
    assert view.message.embeds == [] or "gone quiet" not in str(
        view.message.embeds[0].footer.text
    )


# --- proposing through the panel ---------------------------------------------------------------


async def test_the_submitted_line_shows_both_readings_of_the_time_that_was_typed(
    cog, bot, member, db
):
    interaction = await submit(cog, bot, member)

    assert "your time (America/Phoenix)" in interaction.sent
    assert "<t:" in interaction.sent


async def test_proposing_through_the_panel_still_files_exactly_as_before(cog, bot, member, db):
    opened, view = await open_draft_panel(cog, bot, member)

    assert isinstance(view, EventDraftPanel)
    assert opened.response.modals == []

    await submit(cog, bot, member)
    rows = await events_by_status(db, GUILD, (PENDING,))

    assert len(rows) == 1 and rows[0]["requester_id"] == member.id
    assert "event.created" in await action_kinds(db)


# The draft panel (`docs/info/when-picker-design.md` §2 and §4): a modal that never refuses, a
# panel that says what is still needed, and a Submit that renders only once everything passes.


async def test_propose_opens_a_draft_with_the_four_dropdowns_and_no_submit_yet(
    cog, bot, member
):
    opened, view = await open_draft_panel(cog, bot, member)

    placeholders = [getattr(one, "placeholder", None) for one in view.children]
    assert DAY_PLACEHOLDER in placeholders
    assert HOUR_PLACEHOLDER in placeholders
    assert MINUTE_PLACEHOLDER in placeholders
    assert DURATION_PLACEHOLDER in placeholders
    assert has_item(view, "Title & details") and has_item(view, "Back")
    assert not has_item(view, "Submit")
    assert "(needed)" in card_embed(opened).description


async def test_a_fresh_draft_starts_at_the_length_the_setting_names(cog, bot, member):
    await bot.store.set(GUILD, "events_default_minutes", 90)

    opened, view = await open_draft_panel(cog, bot, member)

    picker = find_select(view, DURATION_PLACEHOLDER)
    assert [one.value for one in picker.options if one.default] == ["1h30m"]
    assert "1h 30m" in card_embed(opened).description


async def test_the_minute_dropdown_steps_by_what_the_setting_says(cog, bot, member):
    await bot.store.set(GUILD, TIME_STEP_KEY, 30)

    _opened, view = await open_draft_panel(cog, bot, member)

    picker = find_select(view, MINUTE_PLACEHOLDER)
    assert [one.label for one in picker.options] == [":00", ":30"]


async def test_the_text_modal_stores_what_was_typed_and_never_refuses(cog, bot, member):
    _opened, view = await open_draft_panel(cog, bot, member)
    opened_modal = await click(bot, member, find_item(view, "Title & details"))
    modal = opened_modal.response.modals[0]
    assert isinstance(modal, EventTextModal)

    modal.event_title._value = "Cookout at the park"
    modal.description._value = "bring a chair"
    typed = FakeInteraction(bot, member)
    await modal.on_submit(typed)

    said = card_embed(typed).description
    assert "Cookout at the park" in said and "bring a chair" in said
    assert "(needed)" not in said


async def test_the_text_modal_comes_back_prefilled_with_everything_already_typed(
    cog, bot, member
):
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.title = "Cookout at the park"
    view.fields.description = "bring a chair"

    reopened = await click(bot, member, find_item(view, "Title & details"))

    modal = reopened.response.modals[0]
    assert modal.event_title.default == "Cookout at the park"
    assert modal.description.default == "bring a chair"


async def test_submit_appears_only_once_the_title_and_the_whole_time_are_there(
    cog, bot, member
):
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.title = "Cookout at the park"

    day = future_day(3)
    picked = await click(bot, member, pick(find_select(view, DAY_PLACEHOLDER), [day.isoformat()]))
    view = card_view(picked)
    assert not has_item(view, "Submit")

    picked = await click(bot, member, pick(find_select(view, HOUR_PLACEHOLDER), ["19"]))
    view = card_view(picked)
    assert not has_item(view, "Submit")

    picked = await click(bot, member, pick(find_select(view, MINUTE_PLACEHOLDER), ["30"]))
    view = card_view(picked)
    assert has_item(view, "Submit")
    assert "Still needed" not in card_embed(picked).description


async def test_a_draft_with_a_time_but_no_title_says_the_title_is_what_is_left(
    cog, bot, member
):
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.when.day = future_day(3)
    view.fields.when.hour, view.fields.when.minute = 19, 30

    shown = await click(bot, member, pick(find_select(view, HOUR_PLACEHOLDER), ["19"]))

    assert "needs a name" in card_embed(shown).description
    assert not has_item(card_view(shown), "Submit")


async def test_a_bad_typed_date_keeps_the_title_and_says_so_on_the_panel(cog, bot, member):
    """The owner's report was that an error emptied the form. It cannot any more."""
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.title = "Cookout at the park"

    later = await click(bot, member, pick(find_select(view, DAY_PLACEHOLDER), [LATER_VALUE]))
    modal = later.response.modals[0]
    modal.day._value = "next tuesday"
    typed = FakeInteraction(bot, member)
    await modal.on_submit(typed)

    said = card_embed(typed).description
    assert "Cookout at the park" in said
    assert "next tuesday" in said and "YYYY-MM-DD" in said
    assert not has_item(card_view(typed), "Submit")


async def test_the_typed_date_comes_back_prefilled_so_editing_is_the_same_as_retrying(
    cog, bot, member
):
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.when.later_text = "next tuesday"

    later = await click(bot, member, pick(find_select(view, DAY_PLACEHOLDER), [LATER_VALUE]))

    assert later.response.modals[0].day.default == "next tuesday"


async def test_a_typed_date_that_reads_lands_on_the_panel_as_the_chosen_day(cog, bot, member):
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.title = "Cookout at the park"
    view.fields.when.hour, view.fields.when.minute = 19, 30

    later = await click(bot, member, pick(find_select(view, DAY_PLACEHOLDER), [LATER_VALUE]))
    modal = later.response.modals[0]
    modal.day._value = future_day(40).isoformat()
    typed = FakeInteraction(bot, member)
    await modal.on_submit(typed)

    assert "7:30 PM" in card_embed(typed).description
    assert has_item(card_view(typed), "Submit")


async def test_submit_from_the_button_files_exactly_one_event_and_one_log_row(
    cog, bot, member, db
):
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.title = "Cookout at the park"
    view.fields.when.day = future_day(3)
    view.fields.when.hour, view.fields.when.minute = 19, 30
    ready = card_view(await click(bot, member, pick(find_select(view, MINUTE_PLACEHOLDER), ["30"])))

    filed = FakeInteraction(bot, member)
    await find_item(ready, "Submit").callback(filed)

    rows = await events_by_status(db, GUILD, (PENDING,))
    kinds = await action_kinds(db)
    assert len(rows) == 1 and rows[0]["title"] == "Cookout at the park"
    assert kinds.count("event.created") == 1
    assert card_embed(filed).title == PANEL_TITLE
    assert "Cookout at the park" in filed.sent


async def test_back_leaves_the_draft_behind_and_writes_nothing(cog, bot, member, db):
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.title = "Cookout at the park"

    back = await click(bot, member, find_item(view, "Back"))

    assert card_embed(back).title == PANEL_TITLE
    assert await events_by_status(db, GUILD, (PENDING,)) == []
    assert "Cookout at the park" not in card_embed(back).description


async def test_the_drafts_time_zone_button_goes_to_the_dropdown_and_back_to_the_draft(
    cog, bot, member, db
):
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.title = "Cookout at the park"

    zone = await click(bot, member, find_item(view, "Time zone"))
    assert card_embed(zone).title == ZONE_PANEL_TITLE

    picker = pick(find_select(card_view(zone), ZONE_PLACEHOLDER), ["Europe/London"])
    picked = await click(bot, member, picker)

    assert await get_timezone(db, member.id) == "Europe/London"
    assert card_embed(picked).title == DRAFT_TITLE
    assert "Cookout at the park" in card_embed(picked).description
    assert "Europe/London" in card_embed(picked).description


async def test_back_on_the_zone_panel_returns_to_the_draft_without_storing_anything(
    cog, bot, member, db
):
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.title = "Cookout at the park"
    zone = await click(bot, member, find_item(view, "Time zone"))

    back = await click(bot, member, find_item(card_view(zone), "Back"))

    assert card_embed(back).title == DRAFT_TITLE
    assert await stored_timezone(db, member.id) is None


async def test_a_member_who_never_chose_reads_times_in_the_guilds_default(cog, bot, member):
    await bot.store.set(GUILD, DEFAULT_TIMEZONE_KEY, "Europe/London")

    opened, _view = await open_draft_panel(cog, bot, member)

    assert "Europe/London" in card_embed(opened).description
    assert "the server's default" in card_embed(opened).description


async def test_a_stored_zone_beats_the_guilds_default_and_drops_the_hint(cog, bot, member, db):
    await bot.store.set(GUILD, DEFAULT_TIMEZONE_KEY, "Europe/London")
    await set_timezone(db, member.id, "Asia/Tokyo")

    opened, _view = await open_draft_panel(cog, bot, member)

    assert "Asia/Tokyo" in card_embed(opened).description
    assert "the server's default" not in card_embed(opened).description


async def test_submit_re_checks_rather_than_trusting_the_button_that_rendered_it(
    cog, bot, member, db
):
    """A duration the dropdown can never produce still has to be refused in words."""
    interaction = await submit(cog, bot, member, duration="a while")

    assert await events_by_status(db, GUILD, (PENDING,)) == []
    assert "1h30m" in interaction.sent


async def test_submit_is_refused_when_events_go_off_while_the_draft_is_open(
    cog, bot, member, db
):
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.title = "Cookout at the park"
    view.fields.when.day = future_day(3)
    view.fields.when.hour, view.fields.when.minute = 19, 30
    await bot.store.set(GUILD, "events_mode", "off")

    filed = FakeInteraction(bot, member)
    await submit_draft(filed, view)

    assert await events_by_status(db, GUILD, (PENDING,)) == []
    assert "turned off" in filed.sent


# The "Where?" picker (`docs/info/where-picker-design.md` §4-§6): the fifth button on the draft's
# row, Discord's own channel picker behind it, and the kind mapping the calendar reads.

VOICE_CHANNEL = 610
STAGE_CHANNEL = 611
TEXT_CHANNEL_ID = 612


def with_channels(bot):
    bot.guild.add(FakeVoice(VOICE_CHANNEL, "Raid Night"))
    bot.guild.add(FakeVoice(STAGE_CHANNEL, "The Stage", stage=True))
    bot.guild.add(FakeText(TEXT_CHANNEL_ID, name="general"))
    return bot


def find_where(view):
    """The Where button, whatever the current pick has done to its label."""
    return next(
        one for one in view.children if str(getattr(one, "label", "")).startswith("Where")
    )


async def open_where(cog, bot, member, view=None):
    if view is None:
        _opened, view = await open_draft_panel(cog, bot, member)
    clicked = await click(bot, member, find_where(view))
    return clicked, card_view(clicked)


async def a_full_draft(cog, bot, member):
    """A draft Submit renders on, so the button row is at Discord's cap of five."""
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.title = "Cookout at the park"
    view.fields.when.day = future_day(3)
    view.fields.when.hour = 19
    picked = await click(bot, member, pick(find_select(view, MINUTE_PLACEHOLDER), ["30"]))
    return picked, card_view(picked)


async def test_the_draft_carries_a_fifth_where_button_on_the_button_row(cog, bot, member):
    _picked, view = await a_full_draft(cog, bot, member)

    where = find_where(view)
    row = [one for one in view.children if getattr(one, "row", None) == where.row]
    assert len(row) == 5
    assert [one.label for one in row] == [
        "Title & details",
        "Where",
        "Time zone",
        "Submit",
        "Back",
    ]


async def test_the_where_button_label_carries_the_channel_by_name(cog, bot, member):
    with_channels(bot)
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.where = Where(WHERE_VOICE, VOICE_CHANNEL, "")

    shown = await click(bot, member, find_item(view, "Title & details"))
    typed = FakeInteraction(bot, member)
    await shown.response.modals[0].on_submit(typed)

    assert has_item(card_view(typed), "Where: 🔊 Raid Night")


async def test_the_where_button_label_carries_a_typed_place_too(cog, bot, member):
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.where = Where(WHERE_OTHER, None, "twitch.tv/blackbloc")

    shown = await click(bot, member, find_item(view, "Title & details"))
    typed = FakeInteraction(bot, member)
    await shown.response.modals[0].on_submit(typed)

    assert has_item(card_view(typed), "Where: twitch.tv/blackbloc")


async def test_the_where_panel_opens_with_the_channel_picker_and_the_two_other_doors(
    cog, bot, member
):
    opened_where, panel = await open_where(cog, bot, member)

    assert isinstance(panel, WherePanel)
    assert card_embed(opened_where).title == WHERE_PANEL_TITLE
    assert "Join" in card_embed(opened_where).description
    assert isinstance(find_select(panel, events_pure.WHERE_PLACEHOLDER), discord.ui.ChannelSelect)
    assert has_item(panel, events_pure.WHERE_OTHER_BUTTON)
    assert has_item(panel, "Back")


async def test_the_channel_picker_offers_voice_stage_and_text_and_nothing_else(cog, bot, member):
    _opened_where, panel = await open_where(cog, bot, member)

    picker = find_select(panel, events_pure.WHERE_PLACEHOLDER)
    assert set(picker.channel_types) == {
        discord.ChannelType.voice,
        discord.ChannelType.stage_voice,
        discord.ChannelType.text,
    }
    assert picker.min_values == 0 and picker.max_values == 1


async def test_clear_only_renders_once_something_is_set(cog, bot, member):
    _opened, view = await open_draft_panel(cog, bot, member)
    _shown, panel = await open_where(cog, bot, member, view)
    assert not has_item(panel, events_pure.WHERE_CLEAR_BUTTON)

    view.fields.where = Where(WHERE_OTHER, None, "the park")
    _shown, panel = await open_where(cog, bot, member, view)
    assert has_item(panel, events_pure.WHERE_CLEAR_BUTTON)


@pytest.mark.parametrize(
    ("channel_id", "kind", "wanted"),
    [
        (VOICE_CHANNEL, "voice", WHERE_VOICE),
        (STAGE_CHANNEL, "stage_voice", WHERE_VOICE),
        (TEXT_CHANNEL_ID, "text", WHERE_TEXT),
    ],
)
async def test_picking_a_channel_stores_the_kind_the_channel_is(
    cog, bot, member, channel_id, kind, wanted
):
    with_channels(bot)
    _opened, view = await open_draft_panel(cog, bot, member)
    _shown, panel = await open_where(cog, bot, member, view)

    picker = find_select(panel, events_pure.WHERE_PLACEHOLDER)
    back = await click(bot, member, pick(picker, [FakePicked(channel_id, kind)]))

    assert view.fields.where == Where(wanted, channel_id, "")
    assert f"<#{channel_id}>" in card_embed(back).description
    assert card_embed(back).title == DRAFT_TITLE


async def test_an_empty_channel_pick_leaves_the_draft_with_nowhere(cog, bot, member):
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.where = Where(WHERE_VOICE, VOICE_CHANNEL, "")
    _shown, panel = await open_where(cog, bot, member, view)

    back = await click(bot, member, pick(find_select(panel, events_pure.WHERE_PLACEHOLDER), []))

    assert view.fields.where == WHERE_UNSET
    assert "**Where** — (not set)" in card_embed(back).description


async def test_the_channel_picker_opens_on_the_one_already_chosen(cog, bot, member):
    with_channels(bot)
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.where = Where(WHERE_VOICE, VOICE_CHANNEL, "")

    _shown, panel = await open_where(cog, bot, member, view)

    picker = find_select(panel, events_pure.WHERE_PLACEHOLDER)
    assert [one.id for one in picker.default_values] == [VOICE_CHANNEL]


async def test_other_types_a_place_and_an_empty_box_clears_it(cog, bot, member):
    _opened, view = await open_draft_panel(cog, bot, member)
    _shown, panel = await open_where(cog, bot, member, view)

    opened_modal = await click(bot, member, find_item(panel, events_pure.WHERE_OTHER_BUTTON))
    modal = opened_modal.response.modals[0]
    assert isinstance(modal, WhereModal)
    modal.place._value = "twitch.tv/blackbloc"
    typed = FakeInteraction(bot, member)
    await modal.on_submit(typed)

    assert view.fields.where == Where(WHERE_OTHER, None, "twitch.tv/blackbloc")
    assert "twitch.tv/blackbloc" in card_embed(typed).description
    assert card_embed(typed).title == DRAFT_TITLE

    _shown, panel = await open_where(cog, bot, member, view)
    reopened = await click(bot, member, find_item(panel, events_pure.WHERE_OTHER_BUTTON))
    empty = reopened.response.modals[0]
    assert empty.place.default == "twitch.tv/blackbloc"
    empty.place._value = ""
    await empty.on_submit(FakeInteraction(bot, member))

    assert view.fields.where == WHERE_UNSET


async def test_clear_puts_the_draft_back_to_nowhere(cog, bot, member):
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.where = Where(WHERE_OTHER, None, "the park")
    _shown, panel = await open_where(cog, bot, member, view)

    back = await click(bot, member, find_item(panel, events_pure.WHERE_CLEAR_BUTTON))

    assert view.fields.where == WHERE_UNSET
    assert card_embed(back).title == DRAFT_TITLE


# The follow-up (`docs/info/where-picker-design.md` § Follow-up): the box stays open beside a
# channel, so a raid can be in a voice channel AND on Twitch at once.


async def test_the_box_is_called_a_link_once_a_channel_is_picked(cog, bot, member):
    with_channels(bot)
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.where = WHERE_UNSET
    _shown, panel = await open_where(cog, bot, member, view)
    assert has_item(panel, events_pure.WHERE_OTHER_BUTTON)

    view.fields.where = Where(WHERE_VOICE, VOICE_CHANNEL, "")
    _shown, beside = await open_where(cog, bot, member, view)

    assert has_item(beside, events_pure.WHERE_LINK_BUTTON)
    assert not has_item(beside, events_pure.WHERE_OTHER_BUTTON)


async def test_picking_a_channel_keeps_the_link_that_was_already_typed(cog, bot, member):
    with_channels(bot)
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.where = Where(WHERE_OTHER, None, "twitch.tv/blackbloc")
    _shown, panel = await open_where(cog, bot, member, view)

    picker = find_select(panel, events_pure.WHERE_PLACEHOLDER)
    back = await click(bot, member, pick(picker, [FakePicked(VOICE_CHANNEL, "voice")]))

    assert view.fields.where == Where(WHERE_VOICE, VOICE_CHANNEL, "twitch.tv/blackbloc")
    assert f"<#{VOICE_CHANNEL}> · [twitch.tv/blackbloc](https://twitch.tv/blackbloc)" in (
        card_embed(back).description
    )


async def test_the_box_beside_a_channel_stores_both_and_leaves_the_channel_alone(
    cog, bot, member
):
    with_channels(bot)
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.where = Where(WHERE_VOICE, VOICE_CHANNEL, "")
    _shown, panel = await open_where(cog, bot, member, view)

    opened_modal = await click(bot, member, find_item(panel, events_pure.WHERE_LINK_BUTTON))
    modal = opened_modal.response.modals[0]
    assert isinstance(modal, WhereModal)
    modal.place._value = "twitch.tv/blackbloc"
    typed = FakeInteraction(bot, member)
    await modal.on_submit(typed)

    assert view.fields.where == Where(WHERE_VOICE, VOICE_CHANNEL, "twitch.tv/blackbloc")
    assert f"<#{VOICE_CHANNEL}> · [twitch.tv/blackbloc](https://twitch.tv/blackbloc)" in (
        card_embed(typed).description
    )


async def test_the_box_beside_a_channel_opens_on_what_is_already_there_and_empties_to_nothing(
    cog, bot, member
):
    with_channels(bot)
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.where = Where(WHERE_VOICE, VOICE_CHANNEL, "twitch.tv/blackbloc")
    _shown, panel = await open_where(cog, bot, member, view)

    opened_modal = await click(bot, member, find_item(panel, events_pure.WHERE_LINK_BUTTON))
    modal = opened_modal.response.modals[0]
    assert modal.place.default == "twitch.tv/blackbloc"
    modal.place._value = ""
    await modal.on_submit(FakeInteraction(bot, member))

    assert view.fields.where == Where(WHERE_VOICE, VOICE_CHANNEL, "")


async def test_dropping_the_channel_keeps_the_link_as_somewhere_else(cog, bot, member):
    """Nobody loses what they typed, so an emptied picker leaves the words behind."""
    with_channels(bot)
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.where = Where(WHERE_VOICE, VOICE_CHANNEL, "twitch.tv/blackbloc")
    _shown, panel = await open_where(cog, bot, member, view)

    back = await click(bot, member, pick(find_select(panel, events_pure.WHERE_PLACEHOLDER), []))

    assert view.fields.where == Where(WHERE_OTHER, None, "twitch.tv/blackbloc")
    assert "twitch.tv/blackbloc" in card_embed(back).description


async def test_clear_wipes_the_channel_and_the_link_together(cog, bot, member):
    with_channels(bot)
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.where = Where(WHERE_VOICE, VOICE_CHANNEL, "twitch.tv/blackbloc")
    _shown, panel = await open_where(cog, bot, member, view)

    back = await click(bot, member, find_item(panel, events_pure.WHERE_CLEAR_BUTTON))

    assert view.fields.where == WHERE_UNSET
    assert "**Where** — (not set)" in card_embed(back).description


async def test_a_channel_and_a_link_are_both_stored_on_the_row(cog, bot, member, db):
    with_channels(bot)
    await submit(cog, bot, member, where=Where(WHERE_VOICE, VOICE_CHANNEL, "twitch.tv/blackbloc"))

    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    assert row["where_kind"] == WHERE_VOICE
    assert row["where_channel_id"] == VOICE_CHANNEL
    assert row["location"] == "twitch.tv/blackbloc"


async def test_the_calendar_entry_carries_the_link_in_its_description(cog, bot, member, lead, db):
    with_channels(bot)
    await submit(cog, bot, member, where=Where(WHERE_VOICE, VOICE_CHANNEL, "twitch.tv/blackbloc"))
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    await approve(bot, lead, row["id"])

    made = bot.guild.scheduled[0].kwargs
    assert made["description"] == "bring a chair\n\nhttps://twitch.tv/blackbloc"
    assert made["entity_type"] is discord.EntityType.voice
    assert "location" not in made


async def test_the_link_stays_out_of_the_description_when_the_key_is_off(
    cog, bot, member, lead, db
):
    with_channels(bot)
    await bot.store.set(GUILD, "events_where_link_in_description", False)
    await submit(cog, bot, member, where=Where(WHERE_VOICE, VOICE_CHANNEL, "twitch.tv/blackbloc"))
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    await approve(bot, lead, row["id"])

    assert bot.guild.scheduled[0].kwargs["description"] == "bring a chair"


async def test_a_typed_place_is_still_only_the_location_and_never_the_description(
    cog, bot, member, lead, db
):
    with_channels(bot)
    await submit(cog, bot, member, where=Where(WHERE_OTHER, None, "twitch.tv/blackbloc"))
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    await approve(bot, lead, row["id"])

    made = bot.guild.scheduled[0].kwargs
    assert made["description"] == "bring a chair"
    assert made["location"] == "twitch.tv/blackbloc"


async def test_back_from_the_where_panel_changes_nothing(cog, bot, member):
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.where = Where(WHERE_OTHER, None, "the park")
    _shown, panel = await open_where(cog, bot, member, view)

    back = await click(bot, member, find_item(panel, "Back"))

    assert view.fields.where == Where(WHERE_OTHER, None, "the park")
    assert card_embed(back).title == DRAFT_TITLE


async def test_a_draft_with_nowhere_still_submits(cog, bot, member, db):
    """Where is never needed, so nothing about it may hold Submit back."""
    interaction = await submit(cog, bot, member, where=WHERE_UNSET)

    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    assert row["location"] is None and row["where_kind"] is None
    assert "Block Party" in interaction.sent


async def test_the_text_modal_keeps_two_boxes_now_that_where_has_its_own_panel(cog, bot, member):
    _opened, view = await open_draft_panel(cog, bot, member)
    opened_modal = await click(bot, member, find_item(view, "Title & details"))

    modal = opened_modal.response.modals[0]
    assert len(modal.children) == 2
    assert [modal.event_title, modal.description] == list(modal.children)


async def test_a_channel_where_is_stored_as_a_channel_not_as_text(cog, bot, member, db):
    with_channels(bot)
    await submit(cog, bot, member, where=Where(WHERE_VOICE, VOICE_CHANNEL, ""))

    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    assert row["where_kind"] == WHERE_VOICE
    assert row["where_channel_id"] == VOICE_CHANNEL
    assert row["location"] is None


@pytest.mark.parametrize(
    ("where", "entity", "channel_id", "location"),
    [
        (Where(WHERE_VOICE, VOICE_CHANNEL, ""), discord.EntityType.voice, VOICE_CHANNEL, None),
        (
            Where(WHERE_VOICE, STAGE_CHANNEL, ""),
            discord.EntityType.stage_instance,
            STAGE_CHANNEL,
            None,
        ),
        (Where(WHERE_TEXT, TEXT_CHANNEL_ID, ""), discord.EntityType.external, None, "#general"),
        (
            Where(WHERE_OTHER, None, "twitch.tv/blackbloc"),
            discord.EntityType.external,
            None,
            "twitch.tv/blackbloc",
        ),
        (WHERE_UNSET, discord.EntityType.external, None, "Ask in the server"),
    ],
)
async def test_the_calendar_entry_follows_the_kind_that_was_picked(
    cog, bot, member, lead, db, where, entity, channel_id, location
):
    with_channels(bot)
    await submit(cog, bot, member, where=where)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    await approve(bot, lead, row["id"])

    made = bot.guild.scheduled[0].kwargs
    assert made["entity_type"] is entity
    assert getattr(made.get("channel"), "id", None) == channel_id
    assert made.get("location") == location
    assert ("location" in made) is (location is not None)


async def test_a_channel_that_has_gone_falls_back_to_words_and_says_so_in_the_log(
    cog, bot, member, lead, db
):
    with_channels(bot)
    await submit(cog, bot, member, where=Where(WHERE_VOICE, VOICE_CHANNEL, ""))
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    bot.guild.channels.pop(VOICE_CHANNEL)

    await approve(bot, lead, row["id"])

    made = bot.guild.scheduled[0].kwargs
    assert made["entity_type"] is discord.EntityType.external
    assert made["location"] == "Ask in the server"
    assert "event.where_channel_gone" in await action_kinds(db)


async def test_no_scheduled_event_is_made_under_the_guard_whatever_the_where_is(
    cog, bot, member, lead, db
):
    """TEST_MODE: the kind mapping is proven by the test above, never by a real calendar entry."""
    with_channels(bot)
    await submit(cog, bot, member, where=Where(WHERE_VOICE, VOICE_CHANNEL, ""))
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    bot.guard = FakeGuard()

    await approve(bot, lead, row["id"])

    assert bot.guild.scheduled == []
    assert "event.would_create_scheduled" in await action_kinds(db)


async def open_staff_card(cog, bot, who, event_id):
    interaction = FakeInteraction(bot, who)
    await events_cog.open_card(interaction, event_id)
    return interaction, card_view(interaction)


async def test_staff_get_a_where_button_on_the_review_card_and_a_member_does_not(
    cog, bot, member, lead, db
):
    with_channels(bot)
    await submit(cog, bot, member, where=Where(WHERE_OTHER, None, "the park"))
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    _staff, staff_view = await open_staff_card(cog, bot, lead, row["id"])
    _theirs, member_view = await open_staff_card(cog, bot, member, row["id"])

    assert has_item(staff_view, "Where: the park")
    assert not [
        one
        for one in member_view.children
        if str(getattr(one, "label", "")).startswith("Where")
    ]


async def test_staff_can_set_any_kind_on_a_card_and_the_write_leaves_one_log_row(
    cog, bot, member, lead, db
):
    with_channels(bot)
    await submit(cog, bot, member, where=Where(WHERE_OTHER, None, "the park"))
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    _staff, staff_view = await open_staff_card(cog, bot, lead, row["id"])
    before = (await action_kinds(db)).count("event.edited")

    _shown, panel = await open_where(cog, bot, lead, staff_view)
    picker = find_select(panel, events_pure.WHERE_PLACEHOLDER)
    back = await click(bot, lead, pick(picker, [FakePicked(STAGE_CHANNEL, "stage_voice")]))

    fresh = await get_event(db, row["id"])
    assert fresh["where_kind"] == WHERE_VOICE and fresh["where_channel_id"] == STAGE_CHANNEL
    assert fresh["location"] == "the park"
    assert (await action_kinds(db)).count("event.edited") == before + 1
    assert f"<#{STAGE_CHANNEL}> · the park" in [one.value for one in card_embed(back).fields]


async def test_staff_can_clear_a_where_off_a_card_altogether(cog, bot, member, lead, db):
    with_channels(bot)
    await submit(cog, bot, member, where=Where(WHERE_OTHER, None, "the park"))
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    _staff, staff_view = await open_staff_card(cog, bot, lead, row["id"])

    _shown, panel = await open_where(cog, bot, lead, staff_view)
    back = await click(bot, lead, find_item(panel, events_pure.WHERE_CLEAR_BUTTON))

    fresh = await get_event(db, row["id"])
    assert fresh["where_kind"] is None and fresh["location"] is None
    assert "Where" not in [one.name for one in card_embed(back).fields]


async def test_a_member_who_is_not_staff_cannot_store_a_where_on_somebody_elses_card(
    cog, bot, member, db
):
    await submit(cog, bot, member, where=Where(WHERE_OTHER, None, "the park"))
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    interaction = FakeInteraction(bot, member)
    await events_cog.store_card_where(interaction, row["id"], WHERE_UNSET, None)

    fresh = await get_event(db, row["id"])
    assert fresh["location"] == "the park"


async def test_a_channel_that_has_gone_is_not_sent_back_as_a_pre_selected_default(
    cog, bot, member
):
    """Discord is handed a default it may not be able to resolve, so it is not handed one."""
    with_channels(bot)
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.where = Where(WHERE_VOICE, VOICE_CHANNEL, "")
    bot.guild.channels.pop(VOICE_CHANNEL)

    _shown, panel = await open_where(cog, bot, member, view)

    assert find_select(panel, events_pure.WHERE_PLACEHOLDER).default_values == []
    assert has_item(panel, events_pure.WHERE_CLEAR_BUTTON)


# Follow-up 2 B (`docs/info/where-picker-design.md` § Follow-up 2): an "Open link" button.


def find_open_link(view):
    return next(
        (
            one
            for one in view.children
            if getattr(one, "label", None) == events_pure.WHERE_OPEN_LINK_BUTTON
        ),
        None,
    )


async def test_the_card_carries_an_open_link_button_for_every_viewer_when_the_place_is_a_link(
    cog, bot, member, db
):
    await submit(cog, bot, member, where=Where(WHERE_OTHER, None, "https://twitch.tv/bb"))
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    _theirs, view = await open_staff_card(cog, bot, member, row["id"])

    button = find_open_link(view)
    assert button is not None and button.style is discord.ButtonStyle.link
    assert button.url == "https://twitch.tv/bb" and button.row == 1


async def test_a_card_whose_place_is_words_gets_no_open_link_button(cog, bot, member, db):
    await submit(cog, bot, member, where=Where(WHERE_OTHER, None, "the park"))
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    _theirs, view = await open_staff_card(cog, bot, member, row["id"])

    assert find_open_link(view) is None


async def a_draft_with_a_link(cog, bot, member, *, full):
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.where = Where(WHERE_OTHER, None, "https://twitch.tv/bb")
    if full:
        view.fields.title = "Cookout at the park"
        view.fields.when.day = future_day(3)
        view.fields.when.hour = 19
    picked = await click(bot, member, pick(find_select(view, MINUTE_PLACEHOLDER), ["30"]))
    return picked, card_view(picked)


async def test_the_draft_never_gets_the_open_link_button_because_it_would_come_and_go(
    cog, bot, member
):
    """Submit takes the row's fifth slot once the draft is ready; the masked line has the link."""
    for full in (False, True):
        picked, view = await a_draft_with_a_link(cog, bot, member, full=full)
        assert find_open_link(view) is None
        assert "[twitch.tv/bb](https://twitch.tv/bb)" in card_embed(picked).description


# Follow-up 3 (`docs/info/where-picker-design.md` § Follow-up 3): a refused room counts from the
# decision, and a test room goes in minutes rather than days.


async def action_details(db, kind):
    cur = await db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id DESC LIMIT 1", (kind,)
    )
    row = await cur.fetchone()
    return json.loads(row["details"]) if row and row["details"] else {}


async def decided_long_ago(db, event_id, ago):
    await db.conn.execute(
        "UPDATE events SET decided_at = ? WHERE id = ?",
        ((datetime.now(UTC) - ago).isoformat(), event_id),
    )
    await db.conn.commit()


async def test_a_denied_room_goes_a_retention_after_the_decision_not_after_the_start(
    cog, bot, db
):
    """A proposal refused today for next month kept its room until next month plus seven days."""
    channel = bot.guild.add(FakeText(700, name="denied-alice-block-party"))
    event_id = await store_event(
        db, status=DENIED, starts_in=timedelta(days=30), minutes=60, channel_id=channel.id
    )
    await decided_long_ago(db, event_id, timedelta(days=10))

    await cog.reconcile_events()

    assert channel.deleted is True
    assert (await get_event(db, event_id))["review_channel_id"] is None


async def test_a_denied_room_decided_a_moment_ago_is_still_kept(cog, bot, db):
    channel = bot.guild.add(FakeText(701, name="denied-alice-block-party"))
    event_id = await store_event(
        db, status=DENIED, starts_in=-timedelta(days=30), minutes=60, channel_id=channel.id
    )
    await decided_long_ago(db, event_id, timedelta(minutes=1))

    await cog.reconcile_events()

    assert channel.deleted is False


async def test_a_finished_room_still_counts_from_the_end_whatever_the_decision_said(cog, bot, db):
    channel = bot.guild.add(FakeText(702, name="done-alice-block-party"))
    event_id = await store_event(
        db, status=DONE, starts_in=-timedelta(days=10), minutes=60, channel_id=channel.id
    )
    await decided_long_ago(db, event_id, timedelta(minutes=1))

    await cog.reconcile_events()

    assert channel.deleted is True


async def test_in_test_mode_a_room_goes_after_the_minutes_key_and_the_log_says_minutes(
    cog, bot, db
):
    bot.guard = FakeGuard()
    channel = bot.guild.add(FakeText(703, name="denied-alice-block-party"))
    channel.category_id = CATEGORY
    event_id = await store_event(
        db, status=DENIED, starts_in=timedelta(days=30), minutes=60, channel_id=channel.id
    )
    await decided_long_ago(db, event_id, timedelta(minutes=6))

    await cog.reconcile_events()

    assert channel.deleted is True
    details = await action_details(db, "event.channel_deleted")
    assert details["kept_minutes"] == 5 and "kept_days" not in details


async def test_in_test_mode_a_room_younger_than_the_minutes_key_is_left_alone(cog, bot, db):
    bot.guard = FakeGuard()
    channel = bot.guild.add(FakeText(704, name="denied-alice-block-party"))
    channel.category_id = CATEGORY
    event_id = await store_event(
        db, status=DENIED, starts_in=-timedelta(days=30), minutes=60, channel_id=channel.id
    )
    await decided_long_ago(db, event_id, timedelta(minutes=2))

    await cog.reconcile_events()

    assert channel.deleted is False
    assert "event.channel_deleted" not in await action_kinds(db)


async def test_the_minutes_key_is_what_test_mode_reads_and_the_days_key_is_left_alone(
    cog, bot, db
):
    bot.guard = FakeGuard()
    await bot.store.set(GUILD, EVENTS_TEST_RETENTION_KEY, 60)
    channel = bot.guild.add(FakeText(705, name="denied-alice-block-party"))
    channel.category_id = CATEGORY
    event_id = await store_event(
        db, status=DENIED, starts_in=-timedelta(days=30), minutes=60, channel_id=channel.id
    )
    await decided_long_ago(db, event_id, timedelta(minutes=30))

    await cog.reconcile_events()

    assert channel.deleted is False

    await decided_long_ago(db, event_id, timedelta(minutes=90))
    await cog.reconcile_events()

    assert channel.deleted is True


async def test_with_no_guard_the_days_key_is_what_counts_and_the_log_says_days(cog, bot, db):
    channel = bot.guild.add(FakeText(706, name="done-alice-block-party"))
    await store_event(
        db, status=DONE, starts_in=-timedelta(days=10), minutes=60, channel_id=channel.id
    )

    await cog.reconcile_events()

    assert channel.deleted is True
    details = await action_details(db, "event.channel_deleted")
    assert details["kept_days"] == 7 and "kept_minutes" not in details


async def test_a_room_outside_the_test_category_is_still_only_logged_never_deleted(cog, bot, db):
    """Follow-up 3 changes WHEN a room goes; the guard still decides WHERE it may."""
    bot.guard = FakeGuard()
    outside = bot.guild.add(FakeText(707, name="denied-alice-block-party"))
    event_id = await store_event(
        db, status=DENIED, starts_in=timedelta(days=30), minutes=60, channel_id=outside.id
    )
    await decided_long_ago(db, event_id, timedelta(minutes=30))

    await cog.reconcile_events()

    assert outside.deleted is False
    assert "event.would_delete_channel" in await action_kinds(db)
