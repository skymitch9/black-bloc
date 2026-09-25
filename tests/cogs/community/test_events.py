import asyncio
import json
import re
from datetime import UTC, datetime, timedelta

import discord
import pytest

from black_bloc import events as events_pure
from black_bloc import logs_panel
from black_bloc import spotlight as spotlight_words
from black_bloc.cogs.community import events as events_cog
from black_bloc.cogs.community.events import (
    FORUM_CHANNEL_PLACEHOLDER,
    GOLIVE_MINUTES,
    RECONCILE_MINUTES,
    REVIEW_MODE_PLACEHOLDER,
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
    build_card,
    build_forum,
    build_rooms,
    decision_id,
    moving_notice_view,
    review_view,
    room_notice_view,
    submit_draft,
)
from black_bloc.cogs.content.spotlight import Spotlight as SpotlightCog
from black_bloc.cogs.content.spotlight import channel_by_login as spotlight_by_login
from black_bloc.cogs.content.spotlight import channels_for as spotlight_rows_for
from black_bloc.config import load_settings
from black_bloc.events import (
    APPROVED,
    CANCELLED,
    DENIED,
    DONE,
    DRAFT_TITLE,
    LIVE,
    MAKE_THE_FORUM,
    MOVE_TO_FORUM_BUTTON,
    PANEL_TITLE,
    PENDING,
    STATUSES,
    WHERE_OTHER,
    WHERE_PANEL_TITLE,
    WHERE_TEXT,
    WHERE_UNSET,
    WHERE_VOICE,
    ZONE_PANEL_TITLE,
    EventDraft,
    Where,
    cancel_event,
    create_event,
    event_for_channel,
    events_by_status,
    get_event,
    make_forum,
    rename_channel,
    set_review,
    set_status,
)
from black_bloc.settings_store import (
    DEFAULT_TIMEZONE_KEY,
    ERROR_RETRY_LABEL,
    ERROR_SENTENCE,
    EVENTS_APPROVER_ROLE_KEY,
    EVENTS_FORUM_CHANNEL_KEY,
    EVENTS_MOVED_LINE_KEY,
    EVENTS_POSTS_WHERE_KEY,
    EVENTS_REVIEW_MODE_KEY,
    EVENTS_ROOM_DELETE_KEY,
    EVENTS_ROOM_NOTICE_KEY,
    EVENTS_TEST_RETENTION_KEY,
    POSTS_ANNOUNCE,
    POSTS_BOTH,
    REVIEW_FORUM,
    ROOM_DELETE_APPROVER,
    TIME_STEP_KEY,
    TIMEZONE_CHOICES_KEY,
    WHERE_ALIASES_KEY,
    WHERE_CHECK_KEY,
    WHERE_CHECK_OFF,
    WHERE_CHECK_REFUSE,
    WHERE_CHECK_SECONDS_KEY,
    WHERE_HINT,
    WHERE_HINT_KEY,
    SettingsStore,
)
from black_bloc.spawned import STAFF_REACH_KEY
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
        self.delete_raises = None

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
        if self.delete_raises is not None:
            raise self.delete_raises
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
        self.owned = set()

    def own_channel(self, channel):
        self.owned.add(getattr(channel, "id", channel))

    def disown_channel(self, channel):
        self.owned.discard(getattr(channel, "id", channel))

    def owns_channel(self, channel):
        return getattr(channel, "id", channel) in self.owned

    def allows_channel(self, channel):
        found = getattr(channel, "id", channel)
        return found == self.test_channel_id or found in self.owned

    def allows_place(self, channel):
        if getattr(channel, "id", channel) == self.test_channel_id:
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
        self.cogs = {}

    def get_cog(self, name):
        return self.cogs.get(name, self._cog)

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


class FakeLinkCheck:
    """The injected `fetch`: what it was asked, and what the page is told to answer."""

    def __init__(self, status=200):
        self.status = status
        self.asked = []

    async def __call__(self, url, *, seconds, headers):
        self.asked.append({"url": url, "seconds": seconds, "headers": headers})
        if isinstance(self.status, Exception):
            raise self.status
        return self.status


@pytest.fixture(autouse=True)
def link_check(monkeypatch):
    fetch = FakeLinkCheck()
    monkeypatch.setattr(events_cog, "LINK_FETCH", fetch)
    return fetch


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


async def test_the_review_channel_is_the_staff_s_to_delete_by_hand(cog, bot, member):
    await submit(cog, bot, member)

    staff = bot.guild.created[0].given_overwrites[bot.guild.roles[0]]
    assert staff.view_channel is True and staff.send_messages is True
    assert staff.manage_channels is True


async def test_with_the_reach_key_off_the_review_channel_is_as_it_was(cog, bot, member):
    await bot.store.set(GUILD, STAFF_REACH_KEY, False)

    await submit(cog, bot, member)

    staff = bot.guild.created[0].given_overwrites[bot.guild.roles[0]]
    assert staff.view_channel is True and staff.send_messages is True
    assert staff.manage_channels is None


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
    # `handoff_mode` ships on, so the room also carries Not an event — make it a request.
    assert ids == [
        decision_id(row["id"], "approve"),
        decision_id(row["id"], "deny"),
        decision_id(row["id"], events_cog.MAKE_REQUEST),
    ]
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


async def test_in_test_mode_the_card_goes_to_the_room_because_black_bloc_made_it(
    cog, bot, member, db
):
    """Part 1A: owning the room is what lets the card land in it rather than in the spam."""
    bot.guard = FakeGuard()

    interaction = await submit(cog, bot, member)

    made = bot.guild.created[0]
    assert bot.guard.owns_channel(made) is True
    assert len(made.messages) == 2
    assert bot.guild.get_channel(TEST_CHANNEL).messages == []
    assert "you can see and post in there too" in interaction.sent
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

    posted = bot.guild.created[0].messages[-1]
    assert posted.kwargs["allowed_mentions"].everyone is False
    assert [r.id for r in posted.kwargs["allowed_mentions"].roles] == [4242]
    assert posted.content.startswith("<@&4242> ")
    assert "event.announce_room" in await action_kinds(db)


async def test_shadow_mode_computes_everything_and_announces_nothing(cog, bot, member, lead, db):
    await bot.store.set(GUILD, "events_mode", "shadow")
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    before = len(bot.guild.created[0].messages)

    await approve(bot, lead, row["id"])

    assert len(bot.guild.created[0].messages) == before
    assert (await get_event(db, row["id"]))["status"] == APPROVED
    assert "event.would_announce_room" in await action_kinds(db)


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
    room = bot.guild.add(FakeText(760, name="approved-alice-block-party"))
    due = await store_event(
        db, status=APPROVED, starts_in=-timedelta(minutes=1), channel_id=room.id
    )
    later = await store_event(db, status=APPROVED, starts_in=timedelta(hours=1))
    unapproved = await store_event(db, status=PENDING, starts_in=-timedelta(minutes=1))

    await cog.run_due_events()

    assert (await get_event(db, due))["status"] == LIVE
    assert (await get_event(db, later))["status"] == APPROVED
    assert (await get_event(db, unapproved))["status"] == PENDING
    assert "Block Party** is starting now!" in room.messages[-1].content


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
    room = bot.guild.add(FakeText(761, name="approved-alice-block-party"))
    event_id = await store_event(
        db, status=APPROVED, starts_in=-timedelta(minutes=2), minutes=180, channel_id=room.id
    )

    await cog.run_due_events()

    assert (await get_event(db, event_id))["status"] == LIVE
    assert "event.go_live_room" in await action_kinds(db)


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

    posted = bot.guild.created[0].messages[-1]
    assert bot.guild.scheduled[0].url in posted.content
    assert "Interested" in posted.content


async def test_the_announcement_promises_no_button_when_there_is_no_scheduled_event(
    cog, bot, member, lead, db
):
    await bot.store.set(GUILD, "events_create_scheduled", False)
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    await approve(bot, lead, row["id"])

    posted = bot.guild.created[0].messages[-1]
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
    await bot.store.set(GUILD, EVENTS_POSTS_WHERE_KEY, POSTS_ANNOUNCE)
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
    await bot.store.set(GUILD, EVENTS_POSTS_WHERE_KEY, POSTS_ANNOUNCE)
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
    assert row["card_channel_id"] == row["review_channel_id"]
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


async def test_the_where_panel_says_to_start_typing_directly_above_the_picker(cog, bot, member):
    """136 channels are allowed here and Discord's picker lists its first page until you type."""
    opened_where, _panel = await open_where(cog, bot, member)

    said = card_embed(opened_where).description
    assert said.endswith(WHERE_HINT)
    assert said.splitlines()[-1] == WHERE_HINT


async def test_the_words_above_the_picker_are_whatever_the_guild_stored(cog, bot, member):
    await bot.store.set(GUILD, WHERE_HINT_KEY, "Start typing, it is in there.")

    opened_where, _panel = await open_where(cog, bot, member)

    said = card_embed(opened_where).description
    assert said.splitlines()[-1] == "Start typing, it is in there."
    assert WHERE_HINT not in said


async def test_an_emptied_hint_leaves_the_where_panel_with_no_such_line(cog, bot, member):
    await bot.store.set(GUILD, WHERE_HINT_KEY, "")

    opened_where, _panel = await open_where(cog, bot, member)

    said = card_embed(opened_where).description
    assert said.splitlines()[-1] == events_pure.WHERE_JOIN_NOTE
    assert "start typing" not in said.lower()


async def test_the_draft_card_carries_the_same_sentence_while_nowhere_is_picked(cog, bot, member):
    opened, _view = await open_draft_panel(cog, bot, member)

    assert f"**Where** — (not set) *{WHERE_HINT}*" in card_embed(opened).description


async def test_an_emptied_hint_leaves_the_draft_where_line_alone(cog, bot, member):
    await bot.store.set(GUILD, WHERE_HINT_KEY, "")

    opened, _view = await open_draft_panel(cog, bot, member)

    assert "**Where** — (not set)" in card_embed(opened).description
    assert "start typing" not in card_embed(opened).description.lower()


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


# Follow-up 4 (`docs/info/where-picker-design.md` § Follow-up 4): a shorthand becomes a link, and
# the link is tried once before it is kept. Every test here injects `fetch` — see `link_check`.


async def type_where(cog, bot, member, typed, *, where=WHERE_UNSET):
    """The Where box on the draft, opened and submitted; the answering interaction comes back."""
    _opened, view = await open_draft_panel(cog, bot, member)
    view.fields.where = where
    _shown, panel = await open_where(cog, bot, member, view)
    button = events_pure.WHERE_LINK_BUTTON if where.channel_id else events_pure.WHERE_OTHER_BUTTON
    opened_modal = await click(bot, member, find_item(panel, button))
    modal = opened_modal.response.modals[0]
    modal.place._value = typed
    answering = FakeInteraction(bot, member)
    await modal.on_submit(answering)
    return view.fields, answering


async def test_a_shorthand_typed_into_the_box_is_stored_as_the_link_it_means(
    cog, bot, member, link_check
):
    fields, answering = await type_where(cog, bot, member, "ttv skyaiva")

    assert fields.where == Where(WHERE_OTHER, None, "https://twitch.tv/skyaiva")
    assert fields.where_note == ""
    assert [one["url"] for one in link_check.asked] == ["https://twitch.tv/skyaiva"]
    assert "[twitch.tv/skyaiva](https://twitch.tv/skyaiva)" in card_embed(answering).description


async def test_warn_keeps_the_link_and_puts_the_reason_on_the_draft(cog, bot, member, link_check):
    link_check.status = 404

    fields, answering = await type_where(cog, bot, member, "yt no-such-handle-xyz")

    assert fields.where == Where(WHERE_OTHER, None, "https://youtube.com/@no-such-handle-xyz")
    assert fields.where_note == events_pure.WHERE_NOTE_MISSING
    assert "⚠️ that page answered 404" in card_embed(answering).description


async def test_warn_says_so_in_words_when_the_page_never_answers(cog, bot, member, link_check):
    link_check.status = TimeoutError()

    fields, answering = await type_where(cog, bot, member, "https://slow.example/x")

    assert fields.where == Where(WHERE_OTHER, None, "https://slow.example/x")
    assert "slow.example did not answer within 2 s" in fields.where_note
    assert "⚠️ slow.example did not answer" in card_embed(answering).description


async def test_the_note_is_cleared_the_next_time_where_is_set(cog, bot, member, link_check):
    link_check.status = 404
    _opened, view = await open_draft_panel(cog, bot, member)
    _shown, panel = await open_where(cog, bot, member, view)
    opened_modal = await click(bot, member, find_item(panel, events_pure.WHERE_OTHER_BUTTON))
    modal = opened_modal.response.modals[0]
    modal.place._value = "yt no-such-handle-xyz"
    await modal.on_submit(FakeInteraction(bot, member))
    assert view.fields.where_note == events_pure.WHERE_NOTE_MISSING

    link_check.status = 200
    _shown, panel = await open_where(cog, bot, member, view)
    again = await click(bot, member, find_item(panel, events_pure.WHERE_OTHER_BUTTON))
    again.response.modals[0].place._value = "the park"
    answering = FakeInteraction(bot, member)
    await again.response.modals[0].on_submit(answering)

    assert view.fields.where == Where(WHERE_OTHER, None, "the park")
    assert view.fields.where_note == ""
    assert "⚠️" not in card_embed(answering).description


async def test_picking_a_channel_clears_a_note_the_box_left_behind(cog, bot, member, link_check):
    """The note belongs to the link that was typed, so any other Where move drops it."""
    with_channels(bot)
    link_check.status = 404
    _opened, view = await open_draft_panel(cog, bot, member)
    _shown, panel = await open_where(cog, bot, member, view)
    opened_modal = await click(bot, member, find_item(panel, events_pure.WHERE_OTHER_BUTTON))
    opened_modal.response.modals[0].place._value = "yt no-such-handle-xyz"
    await opened_modal.response.modals[0].on_submit(FakeInteraction(bot, member))
    assert view.fields.where_note

    _shown, panel = await open_where(cog, bot, member, view)
    await click(bot, member, find_item(panel, events_pure.WHERE_CLEAR_BUTTON))

    assert view.fields.where_note == ""


async def test_refuse_answers_in_words_and_leaves_the_draft_where_it_was(
    cog, bot, member, link_check, db
):
    await bot.store.set(GUILD, WHERE_CHECK_KEY, WHERE_CHECK_REFUSE)
    link_check.status = 404

    fields, answering = await type_where(
        cog, bot, member, "yt no-such-handle-xyz", where=Where(WHERE_OTHER, None, "the park")
    )

    assert fields.where == Where(WHERE_OTHER, None, "the park")
    assert fields.where_note == ""
    said = answering.response.messages[0]["content"]
    assert "https://youtube.com/@no-such-handle-xyz" in said
    assert "404" in said and "events_where_link_check" in said
    assert said.count("\n") == 0 or "nowhere was saved" in said


async def test_refuse_keeps_a_link_that_answers(cog, bot, member, link_check):
    await bot.store.set(GUILD, WHERE_CHECK_KEY, WHERE_CHECK_REFUSE)

    fields, _answering = await type_where(cog, bot, member, "ttv/skyaiva")

    assert fields.where == Where(WHERE_OTHER, None, "https://twitch.tv/skyaiva")
    assert fields.where_note == ""


async def test_off_never_asks_the_page_anything(cog, bot, member, link_check):
    await bot.store.set(GUILD, WHERE_CHECK_KEY, WHERE_CHECK_OFF)

    fields, _answering = await type_where(cog, bot, member, "ttv/skyaiva")

    assert fields.where == Where(WHERE_OTHER, None, "https://twitch.tv/skyaiva")
    assert link_check.asked == []


async def test_a_place_that_is_not_a_link_is_never_asked_about(cog, bot, member, link_check):
    fields, _answering = await type_where(cog, bot, member, "the park, by the fountain")

    assert fields.where == Where(WHERE_OTHER, None, "the park, by the fountain")
    assert link_check.asked == []


async def test_the_check_is_given_the_seconds_the_setting_says(cog, bot, member, link_check):
    await bot.store.set(GUILD, WHERE_CHECK_SECONDS_KEY, 3)

    await type_where(cog, bot, member, "ttv/skyaiva")

    assert [one["seconds"] for one in link_check.asked] == [3]
    assert "Mozilla/5.0" in link_check.asked[0]["headers"]["User-Agent"]


async def test_a_link_typed_beside_a_channel_is_checked_too(cog, bot, member, link_check):
    with_channels(bot)
    link_check.status = 404

    fields, answering = await type_where(
        cog, bot, member, "ttv/skyaiva", where=Where(WHERE_VOICE, VOICE_CHANNEL, "")
    )

    assert fields.where == Where(WHERE_VOICE, VOICE_CHANNEL, "https://twitch.tv/skyaiva")
    assert fields.where_note == events_pure.WHERE_NOTE_MISSING
    assert f"<#{VOICE_CHANNEL}> · [twitch.tv/skyaiva]" in card_embed(answering).description


async def test_a_staff_edited_table_is_what_the_box_reads(cog, bot, member, link_check):
    await bot.store.set(GUILD, WHERE_ALIASES_KEY, "cb=https://caffeine.tv/{handle}")

    fields, _answering = await type_where(cog, bot, member, "cb/skyaiva")

    assert fields.where == Where(WHERE_OTHER, None, "https://caffeine.tv/skyaiva")

    fields, _answering = await type_where(cog, bot, member, "ttv/skyaiva")

    assert fields.where == Where(WHERE_OTHER, None, "ttv/skyaiva")


async def test_a_note_never_reaches_the_stored_event(cog, bot, member, lead, db, link_check):
    """The proposer saw the warning when it mattered; the row is schema 34 and carries none."""
    link_check.status = 404
    with_channels(bot)
    await submit(
        cog, bot, member, where=Where(WHERE_OTHER, None, "https://youtube.com/@no-such-handle")
    )
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    assert row["location"] == "https://youtube.com/@no-such-handle"
    assert "where_note" not in row.keys()


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


# Event rooms (`docs/info/events-rooms-design.md`): the posts land in the event's own room, and
# staff get a Delete button that settles the event before the channel goes.


async def press_delete(bot, who, event_id, channel, note=""):
    """The button, then the box, exactly as a person meets them."""
    pressed = FakeInteraction(bot, who, channel=channel)
    await DecisionButton(event_id, "delete_room").callback(pressed)
    if not pressed.response.modals:
        return pressed, None
    modal = pressed.response.modals[0]
    modal.note._value = note
    submitted = FakeInteraction(bot, who, channel=channel)
    await modal.on_submit(submitted)
    return pressed, submitted


async def test_the_room_carries_a_delete_message_under_the_card(cog, bot, member, db):
    await submit(cog, bot, member)

    room = bot.guild.created[0]
    notice = room.messages[-1]
    assert "goes away on its own" in notice.content
    assert "7 days after it ends" in notice.content
    assert notice.kwargs["view"].children[0].item.label == "Delete this room"


async def test_the_delete_message_counts_in_minutes_while_the_guard_is_on(cog, bot, member, db):
    bot.guard = FakeGuard()

    await submit(cog, bot, member)

    assert "5 minutes after it ends" in bot.guild.created[0].messages[-1].content


async def test_turning_the_notice_off_still_leaves_the_card_and_the_sweep(cog, bot, member, db):
    await bot.store.set(GUILD, EVENTS_ROOM_NOTICE_KEY, False)

    await submit(cog, bot, member)

    room = bot.guild.created[0]
    assert len(room.messages) == 1
    assert room.messages[0].kwargs.get("embed") is not None


async def test_the_announce_value_keeps_the_old_channel_and_leaves_the_room_alone(
    cog, bot, member, lead, db
):
    await bot.store.set(GUILD, EVENTS_POSTS_WHERE_KEY, POSTS_ANNOUNCE)
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    before = len(bot.guild.created[0].messages)

    await approve(bot, lead, row["id"])

    posted = bot.guild.get_channel(TEST_CHANNEL).messages[-1]
    assert len(bot.guild.created[0].messages) == before
    assert "A new event is on the calendar" in posted.content
    kinds = await action_kinds(db)
    assert "event.announce" in kinds and "event.announce_room" not in kinds
    assert (await get_event(db, row["id"]))["announce_message_id"] is not None


async def test_the_both_value_posts_twice_and_only_the_channel_one_is_kept_to_edit(
    cog, bot, member, lead, db
):
    await bot.store.set(GUILD, EVENTS_POSTS_WHERE_KEY, POSTS_BOTH)
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    await approve(bot, lead, row["id"])

    kinds = await action_kinds(db)
    assert "event.announce" in kinds and "event.announce_room" in kinds
    assert "A new event is on the calendar" in bot.guild.created[0].messages[-1].content
    assert (await get_event(db, row["id"]))["announce_message_id"] is not None


async def test_the_room_value_announces_in_the_room_and_says_so_to_whoever_approved(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    interaction = await approve(bot, lead, row["id"])

    assert "the event's own room" in interaction.sent
    assert bot.guild.get_channel(TEST_CHANNEL).messages == []
    assert (await get_event(db, row["id"]))["announce_message_id"] is None


async def test_a_row_with_no_room_left_is_a_failure_not_a_dry_run(cog, bot, member, lead, db):
    event_id = await store_event(db, status=APPROVED, starts_in=-timedelta(minutes=1))

    await cog.run_due_events()

    kinds = await action_kinds(db)
    assert "event.go_live_room_failed" in kinds
    assert "event.would_go_live_room" not in kinds
    assert (await get_event(db, event_id))["status"] == LIVE


async def test_the_ended_line_lands_in_the_room_when_it_finishes(cog, bot, db):
    room = bot.guild.add(FakeText(770, name="approved-alice-block-party"))
    await store_event(
        db, status=LIVE, starts_in=-timedelta(hours=3), minutes=60, channel_id=room.id
    )

    await cog.run_due_events()

    assert "has ended. Thanks for coming." in room.messages[-1].content
    assert room.messages[-1].kwargs["allowed_mentions"].roles is False
    assert "event.ended_room" in await action_kinds(db)


async def test_the_ended_line_is_left_out_when_the_posts_go_to_the_channel(cog, bot, db):
    await bot.store.set(GUILD, EVENTS_POSTS_WHERE_KEY, POSTS_ANNOUNCE)
    room = bot.guild.add(FakeText(771, name="approved-alice-block-party"))
    await store_event(
        db, status=LIVE, starts_in=-timedelta(hours=3), minutes=60, channel_id=room.id
    )

    await cog.run_due_events()

    assert room.messages == []
    assert "event.ended_room" not in await action_kinds(db)


async def test_a_denied_event_is_told_so_in_its_own_room(cog, bot, member, lead, db):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    room = bot.guild.created[0]

    await deny(bot, lead, row["id"], message=room.messages[0])

    assert "clashes with the marathon" in room.messages[-1].content
    assert "event.denied_room" in await action_kinds(db)


async def test_calling_an_event_off_says_so_in_its_room(cog, bot, member, lead, db):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    room = bot.guild.created[0]

    await cog._cancel(bot.guild, await get_event(db, row["id"]), "cancelled_by_1")

    assert "is cancelled and is no longer happening" in room.messages[-1].content
    assert "event.cancelled_room" in await action_kinds(db)


async def test_a_room_that_is_already_gone_is_not_told_its_event_is_off(cog, bot, member, db):
    event_id = await store_event(db, channel_id=4242)

    await cog._cancel(bot.guild, await get_event(db, event_id), "review_channel_gone")

    kinds = await action_kinds(db)
    assert "event.cancelled_room" not in kinds
    assert "event.cancelled_room_failed" not in kinds


async def test_the_host_pressing_delete_is_refused_in_words_and_keeps_the_room(
    cog, bot, member, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    room = bot.guild.created[0]

    pressed, submitted = await press_delete(bot, member, row["id"], room)

    assert submitted is None
    assert "Only staff can remove this room" in pressed.sent
    assert room.deleted is False
    assert (await get_event(db, row["id"]))["status"] == PENDING


async def test_anybody_else_pressing_delete_is_told_what_it_needs(cog, bot, member, db):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    room = bot.guild.created[0]
    stranger = FakeMember(bot.guild, user_id=77, display_name="Stranger")

    pressed, _ = await press_delete(bot, stranger, row["id"], room)

    assert "staff only" in pressed.sent
    assert room.deleted is False


async def test_the_approver_role_may_remove_a_room_when_the_key_says_so(cog, bot, member, db):
    await bot.store.set(GUILD, EVENTS_ROOM_DELETE_KEY, ROOM_DELETE_APPROVER)
    await bot.store.set(GUILD, EVENTS_APPROVER_ROLE_KEY, 4242)
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    room = bot.guild.created[0]
    approver = FakeMember(bot.guild, user_id=78, display_name="Approver", roles=(4242,))

    _, submitted = await press_delete(bot, approver, row["id"], room)

    assert room.deleted is True
    assert "The room is gone." in submitted.sent


async def test_staff_removing_an_open_events_room_cancels_it_first_and_dms_the_note(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    room = bot.guild.created[0]

    _, submitted = await press_delete(bot, lead, row["id"], room, note="we need the space")

    fresh = await get_event(db, row["id"])
    assert fresh["status"] == CANCELLED
    assert fresh["review_channel_id"] is None
    assert room.deleted is True
    assert "staff removed its room" in member.dms[-1]["content"]
    assert "we need the space" in member.dms[-1]["content"]
    assert "is cancelled" in submitted.sent
    details = await action_details(db, "event.channel_deleted")
    assert details["by"] == lead.id and details["cancelled"] is True


async def test_the_listener_does_not_cancel_an_event_the_button_already_settled(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    room = bot.guild.created[0]

    await press_delete(bot, lead, row["id"], room)
    await cog.on_guild_channel_delete(room)

    assert (await action_kinds(db)).count("event.cancelled") == 1


async def test_removing_a_finished_events_room_changes_nothing_but_the_room(
    cog, bot, lead, member, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    room = bot.guild.created[0]
    await set_status(db, row["id"], DONE)

    _, submitted = await press_delete(bot, lead, row["id"], room)

    fresh = await get_event(db, row["id"])
    assert fresh["status"] == DONE and room.deleted is True
    assert not [one for one in member.dms if "cancelled" in str(one["content"])]
    assert "is cancelled" not in submitted.sent
    details = await action_details(db, "event.channel_deleted")
    assert details["cancelled"] is False


async def test_a_room_the_guard_would_not_delete_is_logged_and_the_cancel_is_owned_up_to(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    room = bot.guild.created[0]
    bot.guard = FakeGuard(test_channel_id=TEST_CHANNEL, category_id=None)
    bot.guard.own_channel(room)

    _, submitted = await press_delete(bot, lead, row["id"], room)

    assert room.deleted is False
    assert (await get_event(db, row["id"]))["status"] == CANCELLED
    assert "test mode" in submitted.sent and "is cancelled" in submitted.sent
    details = await action_details(db, "event.would_delete_channel")
    assert details["by"] == lead.id


async def test_a_delete_discord_refuses_says_the_cancel_still_happened(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    room = bot.guild.created[0]
    room.delete_raises = refused()

    _, submitted = await press_delete(bot, lead, row["id"], room)

    assert room.deleted is False
    assert (await get_event(db, row["id"]))["review_channel_id"] == room.id
    assert "would not remove this room" in submitted.sent
    assert "is cancelled" in submitted.sent
    assert "event.room_delete_failed" in await action_kinds(db)


async def test_a_button_pressed_in_a_room_that_is_not_that_events_any_more_says_so(
    cog, bot, member, lead, db
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    room = bot.guild.created[0]
    elsewhere = bot.guild.add(FakeText(780, name="somewhere-else", category=FakeCategory()))
    await set_review(db, row["id"], elsewhere.id, row["review_message_id"])

    _, submitted = await press_delete(bot, lead, row["id"], room)

    assert room.deleted is False and elsewhere.deleted is False
    assert "is not the event this room is for" in submitted.sent


async def test_reconcile_re_owns_every_room_it_can_still_see(cog, bot, member, db):
    bot.guard = FakeGuard()
    await submit(cog, bot, member)
    room = bot.guild.created[0]
    bot.guard = FakeGuard()

    await cog.reconcile_events()

    assert bot.guard.owns_channel(room) is True


async def test_a_swept_row_whose_room_has_gone_stops_carrying_its_id_and_says_so_once(
    cog, bot, db
):
    event_id = await store_event(
        db, status=DENIED, starts_in=-timedelta(days=30), minutes=60, channel_id=4242
    )

    await cog.reconcile_events()
    await cog.reconcile_events()

    assert (await get_event(db, event_id))["review_channel_id"] is None
    assert (await action_kinds(db)).count("event.room_forgotten") == 1


async def test_a_hand_deleted_room_is_forgotten_by_the_guard_as_well(cog, bot, member, db):
    bot.guard = FakeGuard()
    await submit(cog, bot, member)
    room = bot.guild.created[0]

    await cog.on_guild_channel_delete(room)

    assert bot.guard.owns_channel(room) is False


async def test_the_rooms_page_is_reached_from_settings_and_writes_what_is_picked(
    cog, bot, lead, db
):
    settings = await settings_panel(cog, bot, lead)

    opened_rooms = await click(bot, lead, find_item(card_view(settings), "Rooms…"))
    select = find_select(card_view(opened_rooms), events_pure.POSTS_WHERE_PLACEHOLDER)
    picked = await click(bot, lead, pick(select, [POSTS_BOTH]))

    assert "Events — rooms" in card_embed(opened_rooms).title
    assert bot.store.get(GUILD, EVENTS_POSTS_WHERE_KEY) == POSTS_BOTH
    assert "both the room and the announce channel" in card_embed(picked).description
    assert "event.settings" in await action_kinds(db)


async def test_the_delete_button_is_the_same_registration_the_card_buttons_use(cog, bot):
    """One `add_dynamic_items(DecisionButton)`, so the template has to read all three moves."""
    await cog.cog_load()
    match = re.fullmatch(events_cog.DECISION_TEMPLATE, decision_id(12, "delete_room"))
    rebuilt = await DecisionButton.from_custom_id(None, None, match)

    assert events_cog.DecisionButton in bot.dynamic
    assert match["event_id"] == "12" and match["action"] == "delete_room"
    assert rebuilt.event_id == 12 and rebuilt.item.label == "Delete this room"
    assert re.fullmatch(events_cog.DECISION_TEMPLATE, decision_id(12, "deny"))["action"] == "deny"


# --- Send to events… — the second half of a request → event hand-off (send-to-design §A) -------


async def a_request(bot, member, **fields):
    from black_bloc import requests as requests_pure

    return await requests_pure.create_request(
        bot.db,
        GUILD,
        member.id,
        what=fields.get("what", "a games night"),
        why=fields.get("why", "there is nothing to do on Tuesdays"),
        due_on=None,
    )


async def handed_over_draft(bot, lead, request_id):
    """What staff see after Send to events…: the `/event` draft, already filled in."""
    from black_bloc import requests as requests_pure

    row = await requests_pure.get_request(bot.db, request_id)
    opening = FakeInteraction(bot, lead)
    await events_cog.open_request_draft(opening, row)
    return opening, card_view(opening)


def pick_a_time(view, start=None):
    when = draft_fields(start=start or future_start()).when
    view.fields.when = when
    return view


async def submit_the_draft(bot, lead, view):
    interaction = FakeInteraction(bot, lead)
    await submit_draft(interaction, view)
    return interaction


async def test_send_to_events_opens_the_draft_filled_in_from_the_request(bot, lead, member, db):
    request_id = await a_request(bot, member)

    opening, view = await handed_over_draft(bot, lead, request_id)

    assert card_embed(opening).title == DRAFT_TITLE
    assert view.fields.title == "a games night"
    assert f"Filed as request #{request_id} by <@{member.id}>" in view.fields.description
    assert "there is nothing to do on Tuesdays" in view.fields.description
    assert view.fields.requester_id == member.id and view.fields.from_request == request_id
    assert view.fields.when.day is None
    assert not has_item(view, "Submit")


async def test_the_event_a_hand_off_makes_is_filed_in_the_members_name_not_the_staffers(
    cog, bot, lead, member, db
):
    request_id = await a_request(bot, member)
    _opening, view = await handed_over_draft(bot, lead, request_id)

    await submit_the_draft(bot, lead, pick_a_time(view))

    rows = await events_by_status(db, GUILD, (PENDING,))
    assert len(rows) == 1
    assert rows[0]["requester_id"] == member.id
    assert rows[0]["title"] == "a games night"


async def test_submitting_a_handed_over_draft_closes_the_request_as_moved_with_the_trail(
    cog, bot, lead, member, db
):
    from black_bloc import requests as requests_pure

    request_id = await a_request(bot, member)
    _opening, view = await handed_over_draft(bot, lead, request_id)

    said = await submit_the_draft(bot, lead, pick_a_time(view))

    event = (await events_by_status(db, GUILD, (PENDING,)))[0]
    row = await requests_pure.get_request(db, request_id)
    assert row["status"] == requests_pure.MOVED
    assert row["moved_to"] == f"event:{event['id']}"
    assert f"event **#{event['id']}**" in said.response.messages[-1]["content"]


async def test_a_hand_off_leaves_exactly_one_row_naming_both_ends(cog, bot, lead, member, db):
    request_id = await a_request(bot, member)
    _opening, view = await handed_over_draft(bot, lead, request_id)

    await submit_the_draft(bot, lead, pick_a_time(view))

    event = (await events_by_status(db, GUILD, (PENDING,)))[0]
    kinds = await action_kinds(db)
    assert kinds.count("handoff.request_to_event") == 1
    cur = await db.conn.execute(
        "SELECT actor_id, target_id, details FROM action_log WHERE kind = ?",
        ("handoff.request_to_event",),
    )
    logged = await cur.fetchone()
    details = json.loads(logged["details"])
    assert (logged["actor_id"], logged["target_id"]) == (lead.id, member.id)
    assert details["request_id"] == request_id and details["event_id"] == event["id"]


async def test_the_member_is_told_by_dm_that_their_request_is_now_an_event(
    cog, bot, lead, member, db
):
    request_id = await a_request(bot, member)
    _opening, view = await handed_over_draft(bot, lead, request_id)

    await submit_the_draft(bot, lead, pick_a_time(view))

    event = (await events_by_status(db, GUILD, (PENDING,)))[0]
    said = member.dms[-1]["content"]
    assert f"#{request_id}" in said and f"#{event['id']}" in said
    assert "staff will review it there" in said


async def test_a_member_whose_dms_are_shut_leaves_a_row_rather_than_silence(
    cog, bot, lead, member, db
):
    request_id = await a_request(bot, member)
    member.dm_raises = refused()
    _opening, view = await handed_over_draft(bot, lead, request_id)

    await submit_the_draft(bot, lead, pick_a_time(view))

    assert "request.dm_failed" in await action_kinds(db)


async def test_the_staffer_who_handed_it_over_is_not_dmed_as_though_they_proposed_it(
    cog, bot, lead, member, db
):
    request_id = await a_request(bot, member)
    _opening, view = await handed_over_draft(bot, lead, request_id)

    await submit_the_draft(bot, lead, pick_a_time(view))

    assert lead.dms == []
    assert member.dms


async def test_leaving_the_draft_alone_leaves_the_request_exactly_where_it_was(
    cog, bot, lead, member, db
):
    """Cancel on the draft is Back: nothing is created and nothing is closed (§A)."""
    from black_bloc import requests as requests_pure

    request_id = await a_request(bot, member)
    _opening, view = await handed_over_draft(bot, lead, request_id)

    await click(bot, lead, find_item(view, "Back"))

    row = await requests_pure.get_request(db, request_id)
    assert row["status"] == requests_pure.OPEN and row["moved_to"] is None
    assert await events_by_status(db, GUILD, (PENDING,)) == []


async def test_a_draft_that_cannot_be_submitted_yet_changes_nothing_either(
    cog, bot, lead, member, db
):
    from black_bloc import requests as requests_pure

    request_id = await a_request(bot, member)
    _opening, view = await handed_over_draft(bot, lead, request_id)

    said = await submit_the_draft(bot, lead, view)

    assert "Pick a day" in card_embed(said).description
    row = await requests_pure.get_request(db, request_id)
    assert row["status"] == requests_pure.OPEN and row["moved_to"] is None


async def test_an_ordinary_proposal_is_untouched_by_the_hand_off_path(cog, bot, member, db):
    """No `from_request` means no trail, no second DM and the proposer is whoever pressed."""
    said = await submit(cog, bot, member)

    rows = await events_by_status(db, GUILD, (PENDING,))
    assert rows[0]["requester_id"] == member.id
    assert "handoff.request_to_event" not in await action_kinds(db)
    assert member.dms and "Submitted on" in member.dms[-1]["content"]
    assert "review it" in said.response.messages[-1]["content"]
    assert "event **#" not in said.response.messages[-1]["content"]


# --- Not an event — make it a request (send-to-design §A) --------------------------------------


async def hand_it_back(bot, lead, event_id, message=None):
    interaction = FakeInteraction(bot, lead, message=message)
    await DecisionButton(event_id, events_cog.MAKE_REQUEST).callback(interaction)
    return interaction


async def a_pending_event(cog, bot, member, **fields):
    await submit(cog, bot, member, **fields)
    return (await events_by_status(bot.db, GUILD, (PENDING,)))[0]


async def test_the_review_room_offers_the_move_only_while_the_key_is_on(cog, bot, member, db):
    await bot.store.set(GUILD, "handoff_mode", "off")

    await submit(cog, bot, member)

    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    ids = [item.custom_id for item in bot.guild.created[0].messages[0].kwargs["view"].children]
    assert ids == [decision_id(row["id"], "approve"), decision_id(row["id"], "deny")]


async def test_making_it_a_request_files_one_in_the_requesters_name_from_the_events_words(
    cog, bot, member, lead, db
):
    from black_bloc import requests as requests_pure

    row = await a_pending_event(cog, bot, member, title="Games night", description="on Tuesdays")

    await hand_it_back(bot, lead, row["id"])

    filed = await requests_pure.list_requests(db, GUILD)
    assert len(filed) == 1
    assert filed[0]["user_id"] == member.id
    assert (filed[0]["what"], filed[0]["why"]) == ("Games night", "on Tuesdays")
    assert filed[0]["source"] == requests_pure.SOURCE_EVENT
    assert filed[0]["status"] == requests_pure.OPEN


async def test_an_event_with_no_description_still_files_a_request_with_a_why(
    cog, bot, member, lead, db
):
    """`why` is NOT NULL and the modal makes it required, so the hand-off owes one."""
    from black_bloc import requests as requests_pure

    row = await a_pending_event(cog, bot, member, description="")

    await hand_it_back(bot, lead, row["id"])

    filed = (await requests_pure.list_requests(db, GUILD))[0]
    assert filed["why"] == f"(filed from event #{row['id']})"


async def test_the_event_is_cancelled_with_the_trail_pointing_at_the_request(
    cog, bot, member, lead, db
):
    row = await a_pending_event(cog, bot, member)

    said = await hand_it_back(bot, lead, row["id"])

    fresh = await get_event(db, row["id"])
    assert fresh["status"] == CANCELLED
    assert fresh["moved_to"] == "request:1"
    assert "request **#1**" in said.response.messages[-1]["content"]


async def test_the_cancel_dm_names_the_request_it_became(cog, bot, member, lead, db):
    row = await a_pending_event(cog, bot, member)

    await hand_it_back(bot, lead, row["id"])

    said = member.dms[-1]["content"]
    assert "filed it as a request instead" in said
    assert "The reason given was: filed as request #1 instead" in said


async def test_the_hand_off_leaves_exactly_one_row_naming_both_ends(cog, bot, member, lead, db):
    row = await a_pending_event(cog, bot, member)

    await hand_it_back(bot, lead, row["id"])

    kinds = await action_kinds(db)
    assert kinds.count("handoff.event_to_request") == 1
    cur = await db.conn.execute(
        "SELECT actor_id, target_id, details FROM action_log WHERE kind = ?",
        ("handoff.event_to_request",),
    )
    logged = await cur.fetchone()
    details = json.loads(logged["details"])
    assert (logged["actor_id"], logged["target_id"]) == (lead.id, member.id)
    assert (details["event_id"], details["request_id"]) == (row["id"], 1)
    # Nothing else the cancel does changes: its own row is still written beside ours.
    assert "event.cancelled" in kinds


async def test_the_rooms_card_closes_and_the_room_keeps_the_link(cog, bot, member, lead, db):
    row = await a_pending_event(cog, bot, member)
    room = bot.guild.created[0]
    card = room.messages[0]

    await hand_it_back(bot, lead, row["id"], message=card)

    assert card.kwargs["view"] is None
    fields = card.kwargs["embed"].to_dict()["fields"]
    assert {"name": "Now", "value": "request **#1**", "inline": False} in fields
    assert "→ request **#1**" in [one.content for one in room.messages]


async def test_a_second_press_on_a_card_nobody_refreshed_refuses_rather_than_filing_twice(
    cog, bot, member, lead, db
):
    from black_bloc import requests as requests_pure

    row = await a_pending_event(cog, bot, member)
    await hand_it_back(bot, lead, row["id"])

    again = await hand_it_back(bot, lead, row["id"])

    assert "already" in again.response.messages[-1]["content"]
    assert len(await requests_pure.list_requests(db, GUILD)) == 1


async def test_a_press_after_the_key_went_off_refuses_in_words_and_files_nothing(
    cog, bot, member, lead, db
):
    from black_bloc import requests as requests_pure

    row = await a_pending_event(cog, bot, member)
    await bot.store.set(GUILD, "handoff_mode", "off")

    said = await hand_it_back(bot, lead, row["id"])

    assert "handoff_mode" in said.response.messages[-1]["content"]
    assert await requests_pure.list_requests(db, GUILD) == []
    assert (await get_event(db, row["id"]))["status"] == PENDING


async def test_a_member_pressing_make_it_a_request_is_told_which_role_it_needs(
    cog, bot, member, db
):
    from black_bloc import requests as requests_pure

    row = await a_pending_event(cog, bot, member)

    said = await hand_it_back(bot, member, row["id"])

    assert "staff" in said.response.messages[-1]["content"].lower()
    assert await requests_pure.list_requests(db, GUILD) == []


async def test_the_filed_request_reaches_the_request_channel_like_any_other(
    cog, bot, member, lead, db
):
    await bot.store.set(GUILD, "request_notify_channel_id", TEST_CHANNEL)
    row = await a_pending_event(cog, bot, member)

    await hand_it_back(bot, lead, row["id"])

    posted = bot.guild.channels[TEST_CHANNEL].messages
    assert any(
        one.kwargs.get("embed") is not None
        and one.kwargs["embed"].to_dict()["title"] == "New request #1"
        for one in posted
    )


# The 17:15 crash, end to end (`docs/info/errors-design.md`): the zone picker stored the zone,
# handed the same interaction to the draft, and the draft's render raised. The member saw one
# sentence and a stale card with nothing to press.


async def click_and_catch(bot, who, item):
    """discord.py routes an item's failure to its view's `on_error`; a direct call does not."""
    interaction = FakeInteraction(bot, who)
    try:
        await item.callback(interaction)
    except Exception as exc:
        await item.view.on_error(interaction, exc, item)
    return interaction


def raises_once(monkeypatch, name="render_draft"):
    """The render fails the first time and works the second — the shape of the real crash."""
    real = getattr(events_cog, name)
    broken = [True]

    async def once(*args, **kwargs):
        if broken:
            broken.clear()
            raise discord.HTTPException(
                _Response(400), "This interaction has already been responded to"
            )
        return await real(*args, **kwargs)

    monkeypatch.setattr(events_cog, name, once)
    return broken


async def test_a_zone_picker_crash_offers_try_again_and_the_draft_comes_back_with_the_title(
    cog, bot, member, db, monkeypatch
):
    _opened, draft = await open_draft_panel(cog, bot, member)
    draft.fields.title = "Cookout in the park"
    zone = await click(bot, member, find_item(draft, events_pure.ZONE_PANEL_BUTTON))
    picker = pick(find_select(card_view(zone), ZONE_PLACEHOLDER), ["Europe/London"])
    raises_once(monkeypatch)

    failed = await click_and_catch(bot, member, picker)
    said = failed.response.messages[-1]

    assert await get_timezone(db, member.id) == "Europe/London"
    assert said["content"] == ERROR_SENTENCE
    assert [one.label for one in said["view"].children] == [ERROR_RETRY_LABEL]
    assert "error.panel" in await action_kinds(db)

    await said["view"].children[0].callback(FakeInteraction(bot, member))

    assert card_embed(failed).title == DRAFT_TITLE
    assert "Cookout in the park" in card_embed(failed).description
    assert "Europe/London" in card_embed(failed).description


async def test_the_row_a_zone_picker_crash_writes_names_the_panel_and_the_step(
    cog, bot, member, db, monkeypatch
):
    _opened, draft = await open_draft_panel(cog, bot, member)
    zone = await click(bot, member, find_item(draft, events_pure.ZONE_PANEL_BUTTON))
    picker = pick(find_select(card_view(zone), ZONE_PLACEHOLDER), ["Europe/London"])
    raises_once(monkeypatch)

    await click_and_catch(bot, member, picker)

    cur = await db.conn.execute("SELECT details FROM action_log WHERE kind = 'error.panel'")
    details = json.loads((await cur.fetchone())["details"])

    assert details["where"] == "ZonePanel"
    assert details["error"] == "HTTPException"
    assert details["step"].startswith("black_bloc/cogs/community/events.py:")
    assert "already been responded to" in details["message"]


# --- events as a forum post under BlackMail (events-forum-design.md §B–§E) ---------------

FORUM = 770000000000000001


class FakeForumTag:
    def __init__(self, tag_id, name, emoji=None):
        self.id = tag_id
        self.name = name
        self.emoji = emoji


class FakeThreadWithMessage:
    def __init__(self, thread, message):
        self.thread = thread
        self.message = message


class FakeThread(FakeText):
    """A forum post: a channel that sends and deletes, plus tags and an archive flag."""

    def __init__(self, thread_id, guild, parent, name="post"):
        super().__init__(thread_id, guild, None, name=name)
        self.type = discord.ChannelType.public_thread
        self.parent = parent
        self.parent_id = parent.id
        self.category = parent.category
        self.category_id = parent.category_id
        self.applied_tags = []
        self.archived = False

    async def edit(self, **kwargs):
        if self.edit_raises is not None:
            raise self.edit_raises
        self.edits.append(kwargs)
        if "name" in kwargs:
            self.name = kwargs["name"]
        if "applied_tags" in kwargs:
            self.applied_tags = list(kwargs["applied_tags"])
        if "archived" in kwargs:
            self.archived = bool(kwargs["archived"])

    async def delete(self, reason=None):
        if self.delete_raises is not None:
            raise self.delete_raises
        self.deleted = True
        if self.guild is not None:
            self.guild.threads.pop(self.id, None)


class FakeForum:
    def __init__(self, channel_id, guild=None, category=None, name="events", tags=()):
        self.id = channel_id
        self.guild = guild
        self.category = category
        self.category_id = category.id if category else None
        self.name = name
        self.type = discord.ChannelType.forum
        self.mention = f"<#{channel_id}>"
        self.available_tags = list(tags)
        self.threads = []
        self.create_raises = None
        self.given_overwrites = None

    async def create_thread(self, name, **kwargs):
        if self.create_raises is not None:
            raise self.create_raises
        self.guild._next_id += 1
        thread = FakeThread(self.guild._next_id, self.guild, self, name=name)
        thread.applied_tags = list(kwargs.get("applied_tags") or ())
        rest = {k: v for k, v in kwargs.items() if k != "content"}
        message = FakeMessage(1, kwargs.get("content") or "", **rest)
        thread.messages.append(message)
        self.guild.threads[thread.id] = thread
        self.threads.append(thread)
        return FakeThreadWithMessage(thread, message)


async def _create_forum(guild, name, **kwargs):
    if guild.forum_raises is not None:
        raise guild.forum_raises
    guild._next_id += 1
    forum = FakeForum(
        guild._next_id,
        guild,
        kwargs.get("category"),
        name=name,
        tags=kwargs.get("available_tags") or (),
    )
    forum.given_overwrites = kwargs.get("overwrites")
    forum.topic = kwargs.get("topic")
    forum.auto_archive = kwargs.get("default_auto_archive_duration")
    guild.channels[forum.id] = forum
    guild.created.append(forum)
    return forum


def teach_the_guild_about_forums(guild):
    """`FakeGuild` predates forums; these three are everything a post needs of it."""
    guild.threads = {}
    guild.forum_raises = None
    guild.create_forum = lambda name, **kwargs: _create_forum(guild, name, **kwargs)
    guild.get_thread = lambda thread_id: guild.threads.get(thread_id)


@pytest.fixture
def forum(bot):
    teach_the_guild_about_forums(bot.guild)
    made = FakeForum(
        FORUM,
        bot.guild,
        bot.guild.channels[CATEGORY],
        tags=[FakeForumTag(i, name) for i, name in enumerate(STATUSES, start=1)],
    )
    bot.guild.channels[FORUM] = made
    return made


@pytest.fixture
async def in_forum_mode(bot, forum):
    await bot.store.set(GUILD, EVENTS_REVIEW_MODE_KEY, REVIEW_FORUM)
    await bot.store.set(GUILD, EVENTS_FORUM_CHANNEL_KEY, FORUM)
    return forum


def tags_on(thread):
    return [tag.name for tag in thread.applied_tags]


async def test_a_proposal_in_forum_mode_opens_a_post_whose_first_message_is_the_card(
    cog, bot, member, db, in_forum_mode
):
    interaction = await submit(cog, bot, member)

    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    post = in_forum_mode.threads[0]
    assert row["review_channel_id"] == post.id
    assert row["review_kind"] == "post"
    assert row["review_message_id"] == post.messages[0].id
    assert post.name.startswith("Block Party · ")
    assert bot.guild.created == []
    first = post.messages[0]
    assert f"#{row['id']}" in first.content
    assert first.kwargs["embed"].title is not None
    labels = [item.item.label for item in first.kwargs["view"].children]
    assert labels[:2] == ["Approve", "Deny"]
    assert tags_on(post) == [PENDING]
    assert "Block Party" in interaction.sent


async def test_the_post_is_claimed_for_the_guard_so_test_mode_still_speaks_in_it(
    cog, bot, member, db, in_forum_mode
):
    bot.guard = FakeGuard()

    await submit(cog, bot, member)

    post = in_forum_mode.threads[0]
    assert FORUM in bot.guard.owned and post.id in bot.guard.owned


async def test_the_host_gets_no_overwrite_because_a_forum_post_is_staff_side(
    cog, bot, member, db, in_forum_mode
):
    """§C: BlackMail is staff-side, so the host hears by DM as a request's filer does."""
    await submit(cog, bot, member)

    post = in_forum_mode.threads[0]
    assert not hasattr(post, "given_overwrites")
    assert bot.guild.created == []


async def test_the_delete_message_in_a_post_is_labelled_delete_this_post(
    cog, bot, member, db, in_forum_mode
):
    await submit(cog, bot, member)

    post = in_forum_mode.threads[0]
    notice = post.messages[1]
    assert "This post is Black Bloc's" in notice.content
    said = [item.item.label for item in notice.kwargs["view"].children]
    assert said == ["Delete this post"]


async def test_approving_an_event_in_the_forum_moves_its_tag(
    cog, bot, member, lead, db, in_forum_mode
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    await approve(bot, lead, row["id"])

    post = in_forum_mode.threads[0]
    assert tags_on(post) == [APPROVED]
    assert post.archived is False


async def test_denying_an_event_tags_it_and_archives_the_post(
    cog, bot, member, lead, db, in_forum_mode
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    await deny(bot, lead, row["id"])

    post = in_forum_mode.threads[0]
    assert tags_on(post) == [DENIED]
    assert post.archived is True


async def test_calling_an_event_off_tags_and_archives_its_post(
    cog, bot, member, db, in_forum_mode
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    await cancel_event(bot, bot.guild, row, "cancelled_by_1", by=1)

    post = in_forum_mode.threads[0]
    assert tags_on(post) == [CANCELLED]
    assert post.archived is True


async def test_an_event_that_ends_tags_its_post_done_and_archives_it(
    cog, bot, member, lead, db, in_forum_mode
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    await approve(bot, lead, row["id"])
    await set_status(db, row["id"], LIVE)

    await cog._finish(bot.guild, await get_event(db, row["id"]))

    post = in_forum_mode.threads[0]
    assert tags_on(post) == [DONE]
    assert post.archived is True


async def test_a_post_never_gets_renamed_the_way_a_room_does(
    cog, bot, member, lead, db, in_forum_mode
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    named = in_forum_mode.threads[0].name

    await approve(bot, lead, row["id"])

    assert in_forum_mode.threads[0].name == named


async def test_delete_this_post_removes_the_thread_and_settles_the_event(
    cog, bot, member, lead, db, in_forum_mode
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    post = in_forum_mode.threads[0]

    interaction = FakeInteraction(bot, lead, channel=post)
    await DecisionButton(row["id"], "delete_room").callback(interaction)
    modal = interaction.response.modals[0]
    assert modal.title == "Remove this post?"
    modal.note._value = "we are done in here"
    submitted = FakeInteraction(bot, lead, channel=post)
    await modal.on_submit(submitted)

    fresh = await get_event(db, row["id"])
    assert post.deleted is True
    assert fresh["status"] == CANCELLED and fresh["review_channel_id"] is None
    assert "The post is gone." in submitted.sent
    assert "staff removed its post." in member.dms[-1]["content"]


async def test_the_host_pressing_delete_this_post_is_refused_in_words(
    cog, bot, member, db, in_forum_mode
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    post = in_forum_mode.threads[0]

    interaction = FakeInteraction(bot, member, channel=post)
    await DecisionButton(row["id"], "delete_room").callback(interaction)

    said = interaction.response.messages[-1]["content"]
    assert "Only staff can remove this post" in said
    assert post.deleted is False


async def test_a_post_the_cache_has_forgotten_is_not_a_cancelled_event(
    cog, bot, member, db, in_forum_mode
):
    """An open post auto-archives out of the thread cache; that is not a deletion."""
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    bot.guild.threads.clear()

    await cog.reconcile_events()
    await cog.reconcile_events()

    fresh = await get_event(db, row["id"])
    assert fresh["status"] == PENDING
    assert fresh["review_channel_id"] == row["review_channel_id"]


async def test_a_post_somebody_deletes_by_hand_cancels_the_event(
    cog, bot, member, db, in_forum_mode
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    post = in_forum_mode.threads[0]

    await cog.on_thread_delete(post)

    fresh = await get_event(db, row["id"])
    assert fresh["status"] == CANCELLED
    assert "review_channel_deleted" in str(member.dms[-1]["content"]) or member.dms


async def test_a_deleted_post_on_a_settled_event_is_only_forgotten(
    cog, bot, member, lead, db, in_forum_mode
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    await deny(bot, lead, row["id"])
    post = in_forum_mode.threads[0]

    await cog.on_thread_delete(post)

    fresh = await get_event(db, row["id"])
    assert fresh["status"] == DENIED and fresh["review_channel_id"] is None
    assert "event.room_forgotten" in await action_kinds(db)


async def test_retention_archives_a_live_post_where_it_would_delete_a_room(
    cog, bot, member, lead, db, in_forum_mode
):
    """`events_channel_retention_days` is a ROOM rule; a settled post is archived instead."""
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    await deny(bot, lead, row["id"])
    post = in_forum_mode.threads[0]
    post.archived = False
    await db.conn.execute(
        "UPDATE events SET decided_at = ? WHERE id = ?",
        ((datetime.now(UTC) - timedelta(days=400)).isoformat(), row["id"]),
    )
    await db.conn.commit()

    await cog.reconcile_events()

    assert post.deleted is False and post.archived is True
    assert "event.post_archived" in await action_kinds(db)
    assert (await get_event(db, row["id"]))["review_channel_id"] == post.id


async def test_a_test_post_is_deleted_five_minutes_after_the_end_like_a_test_room(
    cog, bot, member, lead, db, in_forum_mode
):
    bot.guard = FakeGuard()
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    await deny(bot, lead, row["id"])
    post = in_forum_mode.threads[0]
    await db.conn.execute(
        "UPDATE events SET decided_at = ? WHERE id = ?",
        ((datetime.now(UTC) - timedelta(hours=1)).isoformat(), row["id"]),
    )
    await db.conn.commit()

    await cog.reconcile_events()

    assert post.deleted is True
    assert (await get_event(db, row["id"]))["review_channel_id"] is None
    assert "event.channel_deleted" in await action_kinds(db)


async def test_forum_mode_with_no_forum_refuses_a_proposal_in_words(cog, bot, member, db):
    await bot.store.set(GUILD, EVENTS_REVIEW_MODE_KEY, REVIEW_FORUM)

    interaction = await submit(cog, bot, member)

    assert "Staff have not set up the events forum yet" in interaction.sent
    assert await events_by_status(db, GUILD, (PENDING,)) == []
    assert bot.guild.created == []


async def test_forum_mode_with_no_forum_tells_staff_which_button_to_press(
    cog, bot, lead, db
):
    await bot.store.set(GUILD, EVENTS_REVIEW_MODE_KEY, REVIEW_FORUM)

    interaction = await submit(cog, bot, lead)

    assert "Make the forum" in interaction.sent
    assert await events_by_status(db, GUILD, (PENDING,)) == []


async def test_a_mode_flip_leaves_an_open_room_a_room(cog, bot, member, lead, db, forum):
    interaction = await submit(cog, bot, member)
    room = bot.guild.created[0]
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    assert row["review_kind"] is None

    await bot.store.set(GUILD, EVENTS_REVIEW_MODE_KEY, REVIEW_FORUM)
    await bot.store.set(GUILD, EVENTS_FORUM_CHANNEL_KEY, FORUM)
    await approve(bot, lead, row["id"])

    assert room.name == "approved-alice-block-party"
    assert forum.threads == []
    assert (await get_event(db, row["id"]))["review_channel_id"] == room.id
    assert "Block Party" in interaction.sent


async def test_make_the_forum_builds_it_under_blackmail_and_writes_the_key(
    cog, bot, lead, db
):
    teach_the_guild_about_forums(bot.guild)
    await bot.store.set(GUILD, "modmail_category_id", CATEGORY)

    outcome = await make_forum(bot, bot.guild, lead)

    made = bot.guild.created[-1]
    assert outcome.ok is True and outcome.value == made.id
    assert made.name == "events" and made.type is discord.ChannelType.forum
    assert [tag.name for tag in made.available_tags] == list(STATUSES)
    assert made.auto_archive == 1440
    assert bot.store.get(GUILD, EVENTS_FORUM_CHANNEL_KEY) == made.id
    assert "event.forum_made" in await action_kinds(db)


async def test_make_the_forum_refuses_a_second_one_in_words(cog, bot, lead, in_forum_mode):
    await bot.store.set(GUILD, "modmail_category_id", CATEGORY)

    outcome = await make_forum(bot, bot.guild, lead)

    assert outcome.ok is False and outcome.code == "forum_exists"
    assert "already the events forum" in outcome.message


async def test_make_the_forum_says_which_key_it_needs(cog, bot, lead):
    teach_the_guild_about_forums(bot.guild)

    outcome = await make_forum(bot, bot.guild, lead)

    assert outcome.ok is False and outcome.code == "no_category"
    assert "modmail_category_id" in outcome.message


async def test_a_server_whose_library_cannot_make_a_forum_is_told_so(cog, bot, lead):
    await bot.store.set(GUILD, "modmail_category_id", CATEGORY)

    outcome = await make_forum(bot, bot.guild, lead)

    assert outcome.ok is False and outcome.code == "no_forum_api"
    assert "Make a forum by hand" in outcome.message


async def test_a_refused_forum_creation_is_answered_in_words_and_logged(cog, bot, lead, db):
    teach_the_guild_about_forums(bot.guild)
    bot.guild.forum_raises = refused()
    await bot.store.set(GUILD, "modmail_category_id", CATEGORY)

    outcome = await make_forum(bot, bot.guild, lead)

    assert outcome.ok is False and outcome.code == "forum_failed"
    assert "Manage Channels" in outcome.message
    assert "event.forum_failed" in await action_kinds(db)


async def test_the_test_mode_note_rides_on_the_reply_when_the_guard_is_on(cog, bot, lead):
    teach_the_guild_about_forums(bot.guild)
    bot.guard = FakeGuard()
    await bot.store.set(GUILD, "modmail_category_id", CATEGORY)

    outcome = await make_forum(bot, bot.guild, lead)

    assert "test mode" in outcome.message
    assert outcome.value in bot.guard.owned


async def test_a_forum_somebody_deletes_is_forgotten_rather_than_kept_as_a_dead_id(
    cog, bot, db, in_forum_mode
):
    await cog.on_guild_channel_delete(in_forum_mode)

    assert bot.store.get(GUILD, EVENTS_FORUM_CHANNEL_KEY) is None
    assert "event.forum_forgotten" in await action_kinds(db)


async def test_the_forum_page_offers_the_mode_the_picker_and_the_make_button(cog, bot, lead):
    teach_the_guild_about_forums(bot.guild)

    _, view = build_forum(bot, bot.guild)

    assert has_item(view, "Make the forum")
    assert find_select(view, REVIEW_MODE_PLACEHOLDER) is not None
    assert find_select(view, FORUM_CHANNEL_PLACEHOLDER) is not None


async def test_the_rooms_page_leads_to_the_forum_page(cog, bot, lead):
    _, view = build_rooms(bot, bot.guild)

    assert has_item(view, "Forum…")


async def test_the_event_card_links_the_post_by_its_own_name(
    cog, bot, member, db, in_forum_mode
):
    await submit(cog, bot, member)
    row = await get_event(db, (await events_by_status(db, GUILD, (PENDING,)))[0]["id"])

    _, view = build_card(bot, bot.guild, row, member)

    assert has_item(view, "The review post")
    assert not has_item(view, "The review channel")


# --- §H: moving an open event's room into the forum ------------------------------------


@pytest.fixture
async def a_room_in_forum_mode(cog, bot, member, db, forum):
    """The owner's case: a room made under room mode, and then the mode flipped to forum."""
    await submit(cog, bot, member)
    room = bot.guild.created[0]
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    await bot.store.set(GUILD, EVENTS_REVIEW_MODE_KEY, REVIEW_FORUM)
    await bot.store.set(GUILD, EVENTS_FORUM_CHANNEL_KEY, FORUM)
    return (row, room)


async def press_move(bot, who, event_id, channel=None):
    interaction = FakeInteraction(bot, who, channel=channel)
    await DecisionButton(event_id, "move_forum").callback(interaction)
    return interaction


def item_labels(view):
    return [item.item.label for item in view.children]


def offers_the_move(view):
    """`has_item` reads `.label`, which a `DynamicItem` keeps on the button it wraps."""
    return any(
        getattr(getattr(item, "item", item), "label", None) == MOVE_TO_FORUM_BUTTON
        for item in view.children
    )


async def test_moving_a_room_opens_a_post_with_the_card_and_the_buttons(
    cog, bot, lead, db, a_room_in_forum_mode, forum
):
    row, room = a_room_in_forum_mode

    await press_move(bot, lead, row["id"], channel=room)

    post = forum.threads[0]
    fresh = await get_event(db, row["id"])
    assert fresh["review_kind"] == "post"
    assert fresh["review_channel_id"] == post.id
    assert fresh["review_message_id"] == post.messages[0].id
    assert tags_on(post) == [PENDING]
    assert item_labels(post.messages[0].kwargs["view"])[:2] == ["Approve", "Deny"]


async def test_the_move_never_settles_the_event_and_never_dms_the_host(
    cog, bot, lead, member, db, a_room_in_forum_mode
):
    """§H: the room goes without the cancel `delete_room` would have done."""
    row, room = a_room_in_forum_mode
    before = list(member.dms)

    interaction = await press_move(bot, lead, row["id"], channel=room)

    fresh = await get_event(db, row["id"])
    assert fresh["status"] == PENDING
    assert room.deleted is True
    assert member.dms == before
    assert "event.cancelled" not in await action_kinds(db)
    assert f"<#{fresh['review_channel_id']}>" in interaction.sent


async def test_the_old_room_is_told_where_it_went_before_it_goes(
    cog, bot, lead, db, a_room_in_forum_mode, forum
):
    row, room = a_room_in_forum_mode

    await press_move(bot, lead, row["id"], channel=room)

    post = forum.threads[0]
    assert room.messages[-1].content == (
        f"This event now lives in its own post: <#{post.id}>. This room is being removed."
    )


async def test_the_moved_line_is_a_settings_key_the_site_can_change(
    cog, bot, lead, db, a_room_in_forum_mode, forum
):
    row, room = a_room_in_forum_mode
    await bot.store.set(GUILD, EVENTS_MOVED_LINE_KEY, "Carry on in {post}, please.")

    await press_move(bot, lead, row["id"], channel=room)

    assert room.messages[-1].content == f"Carry on in <#{forum.threads[0].id}>, please."


async def test_the_post_carries_the_delete_this_post_card(
    cog, bot, lead, db, a_room_in_forum_mode, forum
):
    row, room = a_room_in_forum_mode

    await press_move(bot, lead, row["id"], channel=room)

    assert item_labels(forum.threads[0].messages[-1].kwargs["view"]) == ["Delete this post"]


async def test_an_approved_event_keeps_its_status_and_wears_its_own_tag(
    cog, bot, lead, member, db, forum
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    await approve(bot, lead, row["id"])
    await bot.store.set(GUILD, EVENTS_REVIEW_MODE_KEY, REVIEW_FORUM)
    await bot.store.set(GUILD, EVENTS_FORUM_CHANNEL_KEY, FORUM)

    await press_move(bot, lead, row["id"], channel=bot.guild.created[0])

    assert tags_on(forum.threads[0]) == [APPROVED]
    assert (await get_event(db, row["id"]))["status"] == APPROVED


async def test_the_move_logs_where_it_came_from_and_where_it_went(
    cog, bot, lead, db, a_room_in_forum_mode, forum
):
    row, room = a_room_in_forum_mode

    await press_move(bot, lead, row["id"], channel=room)

    details = await action_details(db, "event.room_moved")
    assert details["from"] == room.id
    assert details["to"] == forum.threads[0].id
    assert details["event_id"] == row["id"]


async def test_the_deleted_room_does_not_cancel_the_event_behind_the_move(
    cog, bot, lead, db, a_room_in_forum_mode
):
    """The row is re-pointed first, so `on_guild_channel_delete` finds nothing to settle."""
    row, room = a_room_in_forum_mode

    await press_move(bot, lead, row["id"], channel=room)
    await cog.on_guild_channel_delete(room)

    assert (await get_event(db, row["id"]))["status"] == PENDING


async def test_a_post_cannot_be_moved_into_the_forum_it_is_already_in(
    cog, bot, lead, member, db, in_forum_mode
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]

    interaction = await press_move(bot, lead, row["id"], channel=in_forum_mode.threads[0])

    assert "already reviewed in a post" in interaction.sent
    assert len(in_forum_mode.threads) == 1


async def test_a_settled_event_is_refused_in_words_and_keeps_its_room(
    cog, bot, lead, member, db, forum
):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    await deny(bot, lead, row["id"])
    await bot.store.set(GUILD, EVENTS_REVIEW_MODE_KEY, REVIEW_FORUM)
    await bot.store.set(GUILD, EVENTS_FORUM_CHANNEL_KEY, FORUM)

    interaction = await press_move(bot, lead, row["id"], channel=bot.guild.created[0])

    assert "is **denied**" in interaction.sent
    assert forum.threads == []


async def test_a_blank_forum_names_the_button_that_makes_one(cog, bot, lead, member, db, forum):
    await submit(cog, bot, member)
    row = (await events_by_status(db, GUILD, (PENDING,)))[0]
    await bot.store.set(GUILD, EVENTS_REVIEW_MODE_KEY, REVIEW_FORUM)

    interaction = await press_move(bot, lead, row["id"], channel=bot.guild.created[0])

    assert MAKE_THE_FORUM in interaction.sent
    assert bot.guild.created[0].deleted is False


async def test_the_host_pressing_move_is_refused_in_words(
    cog, bot, member, db, a_room_in_forum_mode
):
    row, room = a_room_in_forum_mode

    interaction = await press_move(bot, member, row["id"], channel=room)

    said = interaction.response.messages[-1]["content"]
    assert "Only staff can move this event into the forum" in said
    assert room.deleted is False


async def test_the_card_offers_the_move_only_once_the_forum_is_the_mode(
    cog, bot, lead, member, db, forum
):
    await submit(cog, bot, member)
    row = await get_event(db, (await events_by_status(db, GUILD, (PENDING,)))[0]["id"])

    _, before = build_card(bot, bot.guild, row, lead)
    assert not offers_the_move(before)

    await bot.store.set(GUILD, EVENTS_REVIEW_MODE_KEY, REVIEW_FORUM)
    await bot.store.set(GUILD, EVENTS_FORUM_CHANNEL_KEY, FORUM)
    _, after = build_card(bot, bot.guild, row, lead)
    assert offers_the_move(after)

    _, theirs = build_card(bot, bot.guild, row, member)
    assert not offers_the_move(theirs)


async def test_the_notice_card_carries_the_move_only_for_a_room_under_forum_mode(
    cog, bot, db, in_forum_mode
):
    factory = moving_notice_view(bot, bot.guild)

    assert item_labels(room_notice_view(1)) == ["Delete this room"]
    assert item_labels(factory(1, "room")) == ["Delete this room", MOVE_TO_FORUM_BUTTON]
    assert item_labels(factory(1, "post")) == ["Delete this post"]


async def test_a_room_mode_notice_card_never_offers_the_move(cog, bot, db, forum):
    factory = moving_notice_view(bot, bot.guild)

    assert item_labels(factory(1, "room")) == ["Delete this room"]


# --- the boot double-reconcile, 2026-09-18 16:08 ----------------------------------------------


async def test_two_reconciles_at_boot_forget_a_gone_room_once(cog, bot, db):
    """The same race as the front door's, one row instead of one message."""
    event_id = await store_event(
        db, status=DENIED, starts_in=-timedelta(days=30), minutes=60, channel_id=4242
    )

    await asyncio.gather(cog.reconcile_events(), cog.reconcile_events())

    assert (await get_event(db, event_id))["review_channel_id"] is None
    assert (await action_kinds(db)).count("event.room_forgotten") == 1


async def test_every_gone_room_at_boot_leaves_exactly_one_row_of_its_own(cog, bot, db):
    ids = [
        await store_event(
            db,
            status=DENIED,
            starts_in=-timedelta(days=30),
            minutes=60,
            channel_id=4242 + one,
        )
        for one in range(3)
    ]

    await asyncio.gather(cog.reconcile_events(), cog.reconcile_events())

    assert (await action_kinds(db)).count("event.room_forgotten") == len(ids)


async def test_on_ready_does_not_reconcile_again_right_after_cog_load_did(cog, bot, db):
    await cog.cog_load()
    try:
        assert await cog.reconcile_events(skip_if_recent=True) is False
    finally:
        await cog.cog_unload()


# --- Spotlight this stream (spotlight-design §B) ----------------------------------------------


def card_labels(view):
    """A DynamicItem keeps its label on the button it wraps, not on itself."""
    return [
        getattr(one, "label", None) or getattr(getattr(one, "item", None), "label", None)
        for one in view.children
    ]


def card_ids(view):
    return [
        getattr(one, "custom_id", None) or getattr(getattr(one, "item", None), "custom_id", None)
        for one in view.children
    ]


async def a_twitch_event(cog, bot, member, lead, where="twitch.tv/gamesdonequick"):
    """An approved event whose Where IS one twitch.tv address and nothing else."""
    await submit(cog, bot, member, where=Where(WHERE_OTHER, None, where))
    row = (await events_by_status(bot.db, GUILD, (PENDING,)))[0]
    await approve(bot, lead, row["id"])
    return (await events_by_status(bot.db, GUILD, (APPROVED,)))[0]


async def test_an_approved_twitch_event_offers_spotlight_this_stream(cog, bot, member, lead):
    row = await a_twitch_event(cog, bot, member, lead)

    _, view = build_card(bot, bot.guild, row, lead)

    assert spotlight_words.EVENT_SPOTLIGHT_LABEL in card_labels(view)
    assert decision_id(row["id"], events_cog.SPOTLIGHT) in card_ids(view)


async def test_an_event_whose_where_is_not_a_link_offers_nothing_to_spotlight(
    cog, bot, member, lead
):
    await submit(cog, bot, member, where=Where(WHERE_OTHER, None, "the bar at 8"))
    row = (await events_by_status(bot.db, GUILD, (PENDING,)))[0]
    await approve(bot, lead, row["id"])
    fresh = (await events_by_status(bot.db, GUILD, (APPROVED,)))[0]

    _, view = build_card(bot, bot.guild, fresh, lead)

    assert spotlight_words.EVENT_SPOTLIGHT_LABEL not in card_labels(view)


async def test_a_member_never_sees_the_move(cog, bot, member, lead):
    row = await a_twitch_event(cog, bot, member, lead)
    bot.store.is_staff = lambda who: False

    _, view = build_card(bot, bot.guild, row, member)

    assert spotlight_words.EVENT_SPOTLIGHT_LABEL not in card_labels(view)


async def test_pressing_it_spotlights_the_channel_until_the_events_end_plus_the_slack(
    cog, bot, member, lead, db
):
    row = await a_twitch_event(cog, bot, member, lead)
    interaction = FakeInteraction(bot, lead)

    await DecisionButton(row["id"], events_cog.SPOTLIGHT).callback(interaction)

    stored = await spotlight_by_login(db, GUILD, "gamesdonequick")
    assert stored is not None and stored["event_id"] == row["id"]
    assert stored["expires_at"] is not None
    assert "spotlighted until" in interaction.response.messages[-1]["content"]
    assert "golive.spotlight_added" in await action_kinds(db)


async def test_pressing_it_twice_refuses_in_words_and_adds_nothing(
    cog, bot, member, lead, db
):
    row = await a_twitch_event(cog, bot, member, lead)
    await DecisionButton(row["id"], events_cog.SPOTLIGHT).callback(FakeInteraction(bot, lead))
    second = FakeInteraction(bot, lead)

    await DecisionButton(row["id"], events_cog.SPOTLIGHT).callback(second)

    assert len(await spotlight_rows_for(db, GUILD)) == 1
    assert "already on the spotlight list" in second.response.messages[-1]["content"]


async def test_calling_the_event_off_takes_its_spotlight_with_it(cog, bot, member, lead, db):
    row = await a_twitch_event(cog, bot, member, lead)
    await DecisionButton(row["id"], events_cog.SPOTLIGHT).callback(FakeInteraction(bot, lead))
    assert len(await spotlight_rows_for(db, GUILD)) == 1

    bot._cog = SpotlightCog(bot)
    await events_pure.cancel_for(bot, bot.guild, row, lead.id, reason="staff")

    assert await spotlight_rows_for(db, GUILD) == []
    details = await action_details(db, "golive.spotlight_expired")
    assert details["because"] == "event_cancelled"


# --- /event ▸ Marathons… (docs/info/marathon-events-page-design.md §C) --------------------------


@pytest.fixture
def marathons(bot):
    from black_bloc.cogs.content.marathon import COG_NAME, Marathons

    made = Marathons(bot)
    bot.cogs[COG_NAME] = made
    return made


async def test_marathons_opens_the_member_half_of_the_old_marathon_panel_one_level_down(
    cog, bot, marathons, member
):
    from black_bloc import marathon as mt

    panel = await open_panel(cog, bot, member)
    interaction = await click(bot, member, find_item(panel_view(panel), "Marathons…"))

    view = card_view(interaction)
    assert card_embed(interaction).title == mt.PANEL_TITLE
    assert mt.OURS_NEXT in card_embed(interaction).description
    assert has_item(view, "My runs") and has_item(view, "Back")
    assert not has_item(view, "Add a marathon…") and not has_item(view, "Logs")


async def test_marathons_gives_staff_the_list_the_add_and_the_marathon_logs(
    cog, bot, marathons, lead
):
    panel = await open_panel(cog, bot, lead)
    interaction = await click(bot, lead, find_item(panel_view(panel), "Marathons…"))

    view = card_view(interaction)
    assert has_item(view, "Add a marathon…") and has_item(view, "Logs")
    assert "Marathon posts are" in card_embed(interaction).description


async def test_back_on_the_marathons_sub_panel_returns_to_the_event_panel(
    cog, bot, marathons, member
):
    panel = await open_panel(cog, bot, member)
    sub = await click(bot, member, find_item(panel_view(panel), "Marathons…"))

    back = await click(bot, member, find_item(card_view(sub), "Back"))

    assert card_embed(back).title == events_pure.PANEL_TITLE


async def test_with_marathons_off_a_member_sees_no_marathons_button_and_staff_still_do(
    cog, bot, member, lead
):
    await bot.store.set(GUILD, "marathon_mode", "off")

    assert not has_item(panel_view(await open_panel(cog, bot, member)), "Marathons…")
    assert has_item(panel_view(await open_panel(cog, bot, lead)), "Marathons…")
