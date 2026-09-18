import json

import discord
import pytest

from black_bloc.cogs.community.events import EVENTS_OFF, ProposeButton
from black_bloc.cogs.community.frontdoor import (
    BELOW_POST,
    GONE,
    MOVED,
    POSTED,
    POSTED_SHADOW,
    TAKEN_DOWN,
    TAKEN_DOWN_SHADOW,
    TICKET_BUTTON_HIDDEN,
    UPDATED_SHADOW,
    WOULD_POST,
    DoorButton,
    DoorPanel,
    EventDoor,
    EventHandoff,
    FrontDoor,
    RequestDoor,
    TicketDoor,
    build_panel,
    post_door,
    shadow_words,
    take_door_down,
)
from black_bloc.cogs.community.requests import REQUESTS_OFF, FileButton
from black_bloc.cogs.moderation.modmail import Modmail, TicketModal
from black_bloc.config import load_settings
from black_bloc.frontdoor import (
    DOOR_GUARDED,
    DOOR_NO_CHANNEL,
    DOOR_NO_HOME,
    DOOR_NOT_UP,
    DOOR_OFF,
    EVENT,
    KINDS,
    REQUEST,
    TICKET,
    custom_id,
    label_for,
)
from black_bloc.settings_store import (
    FRONTDOOR_CHANNEL,
    FRONTDOOR_FOLLOWS_POST,
    FRONTDOOR_MESSAGE,
    FRONTDOOR_MODE,
    FRONTDOOR_REPLACES_TICKET_BUTTON,
    FRONTDOOR_SHADOW_HASH,
    FRONTDOOR_SHADOW_MESSAGE,
    FRONTDOOR_TEXT,
    FRONTDOOR_TICKET_LABEL,
    FRONTDOOR_TITLE,
    MODMAIL_PANEL_CHANNEL,
    MODMAIL_PANEL_MESSAGE,
    SHADOW_CHANNEL,
    SettingsStore,
)

GUILD = 7
TEST_CHANNEL = 111
LOG_CHANNEL = 222
STAFF_ROLE = 555
USER = 900


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
    def __init__(self, message_id, content="", **kwargs):
        self.id = message_id
        self.content = content
        self.kwargs = kwargs
        embed = kwargs.get("embed")
        self.embeds = list(kwargs.get("embeds") or ([embed] if embed is not None else []))
        self.view = kwargs.get("view")

    async def edit(self, **kwargs):
        self.kwargs = {**self.kwargs, **kwargs}
        if "view" in kwargs:
            self.view = kwargs["view"]

    async def delete(self):
        self.deleted = True


class FakeText:
    def __init__(self, channel_id, name="channel"):
        self.id = channel_id
        self.name = name
        self.mention = f"<#{channel_id}>"
        self.visible_to = set()
        self.messages = []
        self.deleted = []
        self.send_raises = None
        self.next_id = channel_id * 100

    def permissions_for(self, role):
        return FakePerms(view_channel=role.id in self.visible_to)

    async def send(self, content=None, **kwargs):
        if self.send_raises is not None:
            raise self.send_raises
        self.next_id += 1
        message = FakeMessage(self.next_id, content or "", **kwargs)
        self.messages.append(message)
        return message

    def _find(self, message_id):
        return next((one for one in self.messages if one.id == int(message_id)), None)

    async def fetch_message(self, message_id):
        found = self._find(message_id)
        if found is None:
            raise discord.NotFound(_Response(404), "gone")
        return found

    def get_partial_message(self, message_id):
        return _Partial(self, int(message_id))


class _Response:
    def __init__(self, status):
        self.status = status
        self.reason = "gone"


class _Partial:
    def __init__(self, channel, message_id):
        self.channel = channel
        self.id = message_id

    async def delete(self):
        found = self.channel._find(self.id)
        if found is None:
            raise discord.NotFound(_Response(404), "gone")
        self.channel.messages.remove(found)
        self.channel.deleted.append(self.id)


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black in a Flash!"
        self.channels = {}
        self.members = {}
        self.roles = [FakeRole(STAFF_ROLE, "Lead")]
        self.me = FakeRole(99, "Black Bloc")
        self.unavailable = False

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_member(self, user_id):
        return self.members.get(user_id)

    def add(self, channel):
        channel.guild = self
        self.channels[channel.id] = channel
        return channel


class FakeMember:
    def __init__(self, guild, user_id=USER, display_name="Ada", roles=()):
        self.id = user_id
        self.guild = guild
        self.name = display_name
        self.display_name = display_name
        self.mention = f"<@{user_id}>"
        self.roles = [FakeRole(one) for one in roles]
        self.guild_permissions = FakePerms()
        self.bot = False
        self.dms = []
        guild.members[user_id] = self

    async def send(self, content=None, **kwargs):
        self.dms.append({"content": content, **kwargs})


class FakeGuard:
    def __init__(self, test_channel_id=TEST_CHANNEL):
        self.test_channel_id = test_channel_id
        self.owned_channel_ids = set()
        self.rehearsal_channel_ids = {}

    def own_channel(self, channel):
        self.owned_channel_ids.add(int(getattr(channel, "id", channel)))

    def rehearse_in(self, guild_id, channel):
        if channel is None:
            self.rehearsal_channel_ids.pop(int(guild_id), None)
            return
        self.rehearsal_channel_ids[int(guild_id)] = int(channel)

    def allows_channel(self, channel):
        here = int(getattr(channel, "id", channel))
        return (
            here == self.test_channel_id
            or here in self.owned_channel_ids
            or here in self.rehearsal_channel_ids.values()
        )

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
        self.cogs_by_name = {}
        self.dynamic_items = []

    def add_dynamic_items(self, *items):
        self.dynamic_items.extend(items)

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def get_guild(self, guild_id):
        return self.guild if guild_id == self.guild.id else None

    def get_user(self, user_id):
        return self.guild.get_member(user_id)

    def get_cog(self, name):
        return self.cogs_by_name.get(name)


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
        self.edits = []
        self._message = None

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        self._message = FakeMessage(9500, kwargs.get("content") or "", **kwargs)
        return self._message

    async def original_response(self):
        last = self.response.messages[-1]
        kept = {k: v for k, v in last.items() if k not in ("ephemeral", "content", "deferred")}
        self._message = FakeMessage(9500, last.get("content") or "", **kept)
        return self._message

    @property
    def sent(self):
        said = [m["content"] for m in self.response.messages if m["content"] is not None]
        return said[-1] if said else None


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
    guild.add(FakeText(TEST_CHANNEL, name="test")).visible_to = {STAFF_ROLE}
    return FakeBot(db, store, settings, guild)


@pytest.fixture
def cog(bot):
    return FrontDoor(bot)


@pytest.fixture
def member(bot):
    return FakeMember(bot.guild)


def labels_on(view):
    return [item.label for item in view.children]


async def test_the_panel_draws_the_three_doors_in_order_with_their_stored_words(bot, member):
    embed, view = build_panel(bot, bot.guild, member)

    assert isinstance(view, DoorPanel)
    assert labels_on(view) == [label_for(bot.store, GUILD, kind) for kind in KINDS]
    assert embed.title and embed.description


async def test_two_of_the_three_buttons_ARE_the_existing_ones_rather_than_copies(bot, member):
    _embed, view = build_panel(bot, bot.guild, member)
    ticket, request, event = view.children

    assert isinstance(ticket, TicketDoor)
    assert isinstance(request, RequestDoor) and isinstance(request, FileButton)
    assert isinstance(event, EventDoor) and isinstance(event, ProposeButton)


async def test_renaming_a_button_renames_it_on_the_card(bot, member):
    await bot.store.set(GUILD, FRONTDOOR_TICKET_LABEL, "Tell a mod")
    _embed, view = build_panel(bot, bot.guild, member)

    assert labels_on(view)[0] == "Tell a mod"


async def test_the_heading_and_line_are_the_stored_ones(bot, member):
    await bot.store.set(GUILD, FRONTDOOR_TITLE, "Stuck?")
    await bot.store.set(GUILD, FRONTDOOR_TEXT, "Pick one.")
    embed, _view = build_panel(bot, bot.guild, member)

    assert (embed.title, embed.description) == ("Stuck?", "Pick one.")


async def test_the_ticket_button_raises_modmails_own_form(bot, member):
    _embed, view = build_panel(bot, bot.guild, member)
    interaction = FakeInteraction(bot, member)

    await view.children[0].callback(interaction)

    assert len(interaction.response.modals) == 1
    assert isinstance(interaction.response.modals[0], TicketModal)


async def test_the_request_button_is_refused_in_requests_own_words_when_requests_are_off(
    bot, member
):
    await bot.store.set(GUILD, "request_mode", "off")
    _embed, view = build_panel(bot, bot.guild, member)
    interaction = FakeInteraction(bot, member)

    await view.children[1].callback(interaction)

    assert interaction.sent == REQUESTS_OFF
    assert not interaction.response.modals


async def test_the_event_button_is_refused_in_events_own_words_when_events_are_off(bot, member):
    await bot.store.set(GUILD, "events_mode", "off")
    _embed, view = build_panel(bot, bot.guild, member)
    interaction = FakeInteraction(bot, member)

    await view.children[2].callback(interaction)

    assert interaction.sent == EVENTS_OFF
    assert not interaction.edits


async def test_ask_opens_one_ephemeral_panel(bot, cog, member):
    interaction = FakeInteraction(bot, member)

    await cog.ask.callback(cog, interaction)

    sent = interaction.response.messages[-1]
    assert sent["ephemeral"] is True
    assert isinstance(sent["view"], DoorPanel)
    assert sent["allowed_mentions"].to_dict() == discord.AllowedMentions.none().to_dict()


async def test_ask_says_why_in_words_when_the_door_is_switched_off(bot, cog, member):
    await bot.store.set(GUILD, FRONTDOOR_MODE, "off")
    interaction = FakeInteraction(bot, member)

    await cog.ask.callback(cog, interaction)

    assert interaction.sent == DOOR_OFF
    assert "frontdoor_mode" in DOOR_OFF and "A setting group" in DOOR_OFF
    assert not any(m.get("view") for m in interaction.response.messages)


async def test_ask_is_a_member_command_and_never_asks_for_staff(bot):
    from black_bloc.settings_store import is_staff_command

    assert not is_staff_command(FrontDoor.ask)


# --- the posted door ------------------------------------------------------------------------


async def kinds_in(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def seed_post(db, *, slug="welcome", channel_id, message_id=None, shadow_message_id=None):
    await db.conn.execute(
        "INSERT INTO posts (guild_id, slug, title, channel_id, body, message_id, "
        "shadow_message_id, updated_at) "
        "VALUES (?, ?, 'Rules', ?, 'be nice', ?, ?, '2026-09-17T00:00:00+00:00')",
        (GUILD, slug, channel_id, message_id, shadow_message_id),
    )
    await db.conn.commit()


def door_message(channel):
    return channel.messages[-1]


def door_labels(message):
    return [item.item.label for item in message.view.children]


@pytest.fixture
def guarded(bot):
    bot.guard = FakeGuard()
    return bot


async def test_posting_the_door_stores_both_keys_and_leaves_one_routine_line(guarded, member):
    channel = guarded.guild.get_channel(TEST_CHANNEL)

    outcome = await post_door(guarded, guarded.guild, member, channel)

    assert outcome.ok and str(TEST_CHANNEL) in outcome.message
    assert guarded.store.get(GUILD, FRONTDOOR_CHANNEL) == TEST_CHANNEL
    assert guarded.store.get(GUILD, FRONTDOOR_MESSAGE) == str(door_message(channel).id)
    assert POSTED in await kinds_in(guarded.db)


async def test_the_posted_message_carries_the_three_persistent_buttons_with_their_words(
    guarded, member
):
    await guarded.store.set(GUILD, FRONTDOOR_TICKET_LABEL, "Tell a mod")
    channel = guarded.guild.get_channel(TEST_CHANNEL)

    await post_door(guarded, guarded.guild, member, channel)
    message = door_message(channel)

    assert [type(one) for one in message.view.children] == [DoorButton] * 3
    assert door_labels(message)[0] == "Tell a mod"
    assert [one.item.custom_id for one in message.view.children] == [
        custom_id(kind, GUILD) for kind in KINDS
    ]
    assert message.view.timeout is None


async def test_a_message_id_is_stored_as_text_because_a_snowflake_is_not_a_js_number(
    guarded, member
):
    channel = guarded.guild.get_channel(TEST_CHANNEL)

    await post_door(guarded, guarded.guild, member, channel)

    assert isinstance(guarded.store.get(GUILD, FRONTDOOR_MESSAGE), str)


async def test_posting_again_moves_it_and_takes_the_old_message_down(guarded, member):
    channel = guarded.guild.get_channel(TEST_CHANNEL)
    await post_door(guarded, guarded.guild, member, channel)
    first = door_message(channel).id

    outcome = await post_door(guarded, guarded.guild, member, channel)

    assert outcome.ok and "moved" in outcome.message
    assert first in channel.deleted
    assert MOVED in await kinds_in(guarded.db)


async def test_taking_it_down_clears_both_keys_so_nothing_puts_it_back(guarded, member):
    channel = guarded.guild.get_channel(TEST_CHANNEL)
    await post_door(guarded, guarded.guild, member, channel)
    message_id = door_message(channel).id

    outcome = await take_door_down(guarded, guarded.guild, member)

    assert outcome.ok
    assert message_id in channel.deleted
    assert not guarded.store.get(GUILD, FRONTDOOR_CHANNEL)
    assert not guarded.store.get(GUILD, FRONTDOOR_MESSAGE)
    assert TAKEN_DOWN in await kinds_in(guarded.db)


async def test_taking_down_a_door_that_is_not_up_is_refused_in_words(guarded, member):
    outcome = await take_door_down(guarded, guarded.guild, member)

    assert not outcome.ok and outcome.status == 404
    assert outcome.message == DOOR_NOT_UP


async def test_a_channel_test_mode_refuses_is_rehearsed_in_the_home_instead(guarded, member):
    """The owner's whole ask: the mods review the real card somewhere they can see it."""
    other = guarded.guild.add(FakeText(777, name="welcome"))
    home = guarded.guild.get_channel(TEST_CHANNEL)

    outcome = await post_door(guarded, guarded.guild, member, other)

    assert outcome.ok and str(TEST_CHANNEL) in outcome.message and "777" in outcome.message
    assert not other.messages
    copy = door_message(home)
    assert door_labels(copy) == [label_for(guarded.store, GUILD, kind) for kind in KINDS]
    assert copy.content == "Rehearsal \u2014 this is where it would go: #welcome"
    assert guarded.store.get(GUILD, FRONTDOOR_SHADOW_MESSAGE) == str(copy.id)
    assert guarded.store.get(GUILD, FRONTDOOR_CHANNEL) == 777
    assert not guarded.store.get(GUILD, FRONTDOOR_MESSAGE)
    assert POSTED_SHADOW in await kinds_in(guarded.db)
    assert POSTED not in await kinds_in(guarded.db)


async def test_the_rehearsal_row_names_both_channels(guarded, member):
    other = guarded.guild.add(FakeText(777, name="welcome"))

    await post_door(guarded, guarded.guild, member, other)

    cur = await guarded.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id DESC", (POSTED_SHADOW,)
    )
    details = json.loads((await cur.fetchone())["details"])
    assert details["channel_id"] == TEST_CHANNEL and details["wanted_channel_id"] == 777


async def test_with_no_rehearsal_home_at_all_the_door_only_writes_a_would_row(bot, member):
    bot.guard = FakeGuard(test_channel_id=None)
    other = bot.guild.add(FakeText(777, name="welcome"))

    outcome = await post_door(bot, bot.guild, member, other)

    assert not outcome.ok and outcome.message == DOOR_GUARDED
    assert WOULD_POST in await kinds_in(bot.db)
    assert not other.messages
    assert not bot.store.get(GUILD, FRONTDOOR_SHADOW_MESSAGE)


async def test_the_rehearsal_copy_is_left_alone_while_nothing_it_draws_has_changed(
    guarded, cog, member
):
    other = guarded.guild.add(FakeText(777, name="welcome"))
    home = guarded.guild.get_channel(TEST_CHANNEL)
    await post_door(guarded, guarded.guild, member, other)
    before = door_message(home).id
    stamp = guarded.store.get(GUILD, FRONTDOOR_SHADOW_HASH)

    await cog.reconcile()

    assert len(home.messages) == 1 and door_message(home).id == before
    assert guarded.store.get(GUILD, FRONTDOOR_SHADOW_HASH) == stamp
    assert UPDATED_SHADOW not in await kinds_in(guarded.db)


async def test_rewording_the_door_edits_the_rehearsal_copy_in_place(guarded, cog, member):
    other = guarded.guild.add(FakeText(777, name="welcome"))
    home = guarded.guild.get_channel(TEST_CHANNEL)
    await post_door(guarded, guarded.guild, member, other)
    before = door_message(home).id
    await guarded.store.set(GUILD, FRONTDOOR_TITLE, "Stuck?")

    await cog.reconcile()

    assert len(home.messages) == 1 and door_message(home).id == before
    assert door_message(home).kwargs["embed"].title == "Stuck?"
    assert UPDATED_SHADOW in await kinds_in(guarded.db)


async def test_a_rehearsal_copy_somebody_deleted_by_hand_is_put_back(guarded, cog, member):
    other = guarded.guild.add(FakeText(777, name="welcome"))
    home = guarded.guild.get_channel(TEST_CHANNEL)
    await post_door(guarded, guarded.guild, member, other)
    home.messages.clear()

    await cog.reconcile()

    assert home.messages
    assert guarded.store.get(GUILD, FRONTDOOR_SHADOW_MESSAGE) == str(door_message(home).id)
    assert GONE in await kinds_in(guarded.db)


async def test_the_rehearsal_copy_follows_the_key_to_a_new_home(guarded, cog, member):
    other = guarded.guild.add(FakeText(777, name="welcome"))
    moved = guarded.guild.add(FakeText(888, name="welcome-test"))
    old_home = guarded.guild.get_channel(TEST_CHANNEL)
    await post_door(guarded, guarded.guild, member, other)
    left_behind = door_message(old_home).id
    await guarded.store.set(GUILD, SHADOW_CHANNEL, 888)
    guarded.guard.rehearse_in(GUILD, 888)

    await cog.reconcile()

    assert moved.messages and not old_home.messages
    assert left_behind in old_home.deleted
    assert guarded.store.get(GUILD, FRONTDOOR_SHADOW_MESSAGE) == str(door_message(moved).id)


async def test_switching_the_door_off_takes_the_rehearsal_copy_down_too(guarded, cog, member):
    other = guarded.guild.add(FakeText(777, name="welcome"))
    home = guarded.guild.get_channel(TEST_CHANNEL)
    await post_door(guarded, guarded.guild, member, other)
    await guarded.store.set(GUILD, FRONTDOOR_MODE, "off")

    await cog.reconcile()

    assert not home.messages
    assert not guarded.store.get(GUILD, FRONTDOOR_SHADOW_MESSAGE)
    assert not guarded.store.get(GUILD, FRONTDOOR_SHADOW_HASH)
    assert TAKEN_DOWN_SHADOW in await kinds_in(guarded.db)


async def test_taking_the_door_down_by_hand_takes_the_rehearsal_copy_with_it(guarded, member):
    other = guarded.guild.add(FakeText(777, name="welcome"))
    home = guarded.guild.get_channel(TEST_CHANNEL)
    await post_door(guarded, guarded.guild, member, other)

    outcome = await take_door_down(guarded, guarded.guild, member)

    assert outcome.ok and "rehearsal copy" in outcome.message
    assert not home.messages
    assert not guarded.store.get(GUILD, FRONTDOOR_SHADOW_MESSAGE)


async def test_the_rehearsal_copy_keeps_its_place_under_the_welcome_posts_own_copy(
    guarded, cog, member
):
    """The order rule applies to the rehearsal copies: the welcome copy is what is compared."""
    other = guarded.guild.add(FakeText(777, name="welcome"))
    home = guarded.guild.get_channel(TEST_CHANNEL)
    await post_door(guarded, guarded.guild, member, other)
    copy_id = door_message(home).id
    await seed_post(guarded.db, channel_id=777, shadow_message_id=copy_id + 10)

    await cog.reconcile()

    said = await kinds_in(guarded.db)
    assert BELOW_POST in said
    assert door_message(home).id > copy_id
    assert guarded.store.get(GUILD, FRONTDOOR_SHADOW_MESSAGE) == str(door_message(home).id)


async def test_the_buttons_on_the_rehearsal_copy_are_the_real_dynamic_ones(guarded, member):
    other = guarded.guild.add(FakeText(777, name="welcome"))
    home = guarded.guild.get_channel(TEST_CHANNEL)

    await post_door(guarded, guarded.guild, member, other)

    copy = door_message(home)
    assert [one.custom_id for one in copy.view.children] == [
        custom_id(kind, GUILD) for kind in KINDS
    ]


async def test_a_blank_note_leaves_the_rehearsal_copy_with_no_line_above_it(guarded, member):
    other = guarded.guild.add(FakeText(777, name="welcome"))
    home = guarded.guild.get_channel(TEST_CHANNEL)
    await guarded.store.set(GUILD, "rehearsal_note", "")

    await post_door(guarded, guarded.guild, member, other)

    assert door_message(home).content == ""


async def test_a_channel_black_bloc_cannot_see_is_refused_in_words(guarded, member):
    outcome = await post_door(guarded, guarded.guild, member, None)

    assert not outcome.ok and outcome.message == DOOR_NO_CHANNEL


async def test_a_door_somebody_deleted_by_hand_is_put_back_by_the_sweep(guarded, cog, member):
    channel = guarded.guild.get_channel(TEST_CHANNEL)
    await post_door(guarded, guarded.guild, member, channel)
    channel.messages.clear()

    await cog.reconcile()

    said = await kinds_in(guarded.db)
    assert GONE in said
    assert channel.messages
    assert guarded.store.get(GUILD, FRONTDOOR_MESSAGE) == str(door_message(channel).id)


async def test_a_door_the_sweep_still_finds_is_left_exactly_where_it_is(guarded, cog, member):
    channel = guarded.guild.get_channel(TEST_CHANNEL)
    await post_door(guarded, guarded.guild, member, channel)
    before = door_message(channel).id

    await cog.reconcile()

    assert door_message(channel).id == before
    assert GONE not in await kinds_in(guarded.db)


async def test_the_door_is_posted_again_when_the_welcome_post_lands_under_it(
    guarded, cog, member
):
    channel = guarded.guild.get_channel(TEST_CHANNEL)
    await post_door(guarded, guarded.guild, member, channel)
    door_id = door_message(channel).id
    await seed_post(guarded.db, channel_id=TEST_CHANNEL, message_id=door_id + 10)

    await cog.reconcile()

    said = await kinds_in(guarded.db)
    assert BELOW_POST in said and MOVED in said
    assert door_message(channel).id > door_id


async def test_none_means_the_door_never_moves_for_a_post(guarded, cog, member):
    channel = guarded.guild.get_channel(TEST_CHANNEL)
    await post_door(guarded, guarded.guild, member, channel)
    door_id = door_message(channel).id
    await seed_post(guarded.db, channel_id=TEST_CHANNEL, message_id=door_id + 10)
    await guarded.store.set(GUILD, FRONTDOOR_FOLLOWS_POST, "none")

    await cog.reconcile()

    assert door_message(channel).id == door_id
    assert BELOW_POST not in await kinds_in(guarded.db)


async def test_the_sweep_takes_the_door_down_when_the_mode_is_switched_off(
    guarded, cog, member
):
    channel = guarded.guild.get_channel(TEST_CHANNEL)
    await post_door(guarded, guarded.guild, member, channel)
    await guarded.store.set(GUILD, FRONTDOOR_MODE, "off")

    await cog.reconcile()

    assert not guarded.store.get(GUILD, FRONTDOOR_CHANNEL)
    assert TAKEN_DOWN in await kinds_in(guarded.db)


async def test_the_sweep_leaves_a_guild_discord_says_is_unavailable_alone(
    guarded, cog, member
):
    channel = guarded.guild.get_channel(TEST_CHANNEL)
    await post_door(guarded, guarded.guild, member, channel)
    channel.messages.clear()
    guarded.guild.unavailable = True

    await cog.reconcile()

    assert not channel.messages


# --- one door per channel -------------------------------------------------------------------


async def put_the_ticket_button_up(bot, channel, message_id=4242):
    await bot.store.set(GUILD, MODMAIL_PANEL_CHANNEL, channel.id)
    await bot.store.set(GUILD, MODMAIL_PANEL_MESSAGE, str(message_id))
    channel.messages.append(FakeMessage(message_id, "open a ticket"))
    return message_id


async def test_the_ticket_button_comes_down_when_the_door_lands_in_its_channel(
    guarded, member
):
    channel = guarded.guild.get_channel(TEST_CHANNEL)
    button_id = await put_the_ticket_button_up(guarded, channel)

    await post_door(guarded, guarded.guild, member, channel)

    assert button_id in channel.deleted
    assert TICKET_BUTTON_HIDDEN in await kinds_in(guarded.db)
    assert not guarded.store.get(GUILD, MODMAIL_PANEL_MESSAGE)
    assert guarded.store.get(GUILD, MODMAIL_PANEL_CHANNEL) == TEST_CHANNEL


async def test_modmails_own_sweep_does_not_put_the_ticket_button_straight_back(
    guarded, member
):
    channel = guarded.guild.get_channel(TEST_CHANNEL)
    await put_the_ticket_button_up(guarded, channel)
    await post_door(guarded, guarded.guild, member, channel)
    before = len(channel.messages)

    await Modmail(guarded)._repanel(guarded.guild)

    assert len(channel.messages) == before
    assert not guarded.store.get(GUILD, MODMAIL_PANEL_MESSAGE)


async def test_moving_the_door_away_lets_modmails_sweep_put_its_button_back(guarded, member):
    channel = guarded.guild.get_channel(TEST_CHANNEL)
    await put_the_ticket_button_up(guarded, channel)
    await post_door(guarded, guarded.guild, member, channel)
    await take_door_down(guarded, guarded.guild, member)

    await Modmail(guarded)._repanel(guarded.guild)

    assert guarded.store.get(GUILD, MODMAIL_PANEL_MESSAGE)
    assert "modmail.panel_posted" in await kinds_in(guarded.db)


async def test_the_ticket_button_is_left_alone_when_the_key_is_off(guarded, member):
    channel = guarded.guild.get_channel(TEST_CHANNEL)
    button_id = await put_the_ticket_button_up(guarded, channel)
    await guarded.store.set(GUILD, FRONTDOOR_REPLACES_TICKET_BUTTON, False)

    await post_door(guarded, guarded.guild, member, channel)

    assert button_id not in channel.deleted
    assert guarded.store.get(GUILD, MODMAIL_PANEL_MESSAGE) == str(button_id)


async def test_a_ticket_button_in_another_channel_is_none_of_the_doors_business(
    guarded, member
):
    channel = guarded.guild.get_channel(TEST_CHANNEL)
    elsewhere = guarded.guild.add(FakeText(778, name="help"))
    button_id = await put_the_ticket_button_up(guarded, elsewhere)

    await post_door(guarded, guarded.guild, member, channel)

    assert button_id not in elsewhere.deleted
    assert guarded.store.get(GUILD, MODMAIL_PANEL_MESSAGE) == str(button_id)


# --- the posted buttons ---------------------------------------------------------------------


async def restored(kind):
    """What a restart leaves: the item rebuilt from a regex match and nothing else."""
    match = {"kind": kind, "guild_id": str(GUILD)}
    return await DoorButton.from_custom_id(None, None, match)


@pytest.mark.parametrize("kind", KINDS)
async def test_a_posted_button_is_rebuilt_from_its_custom_id_alone(kind):
    item = await restored(kind)

    assert isinstance(item, DoorButton)
    assert item.kind == kind and item.guild_id == GUILD
    assert item.item.custom_id == custom_id(kind, GUILD)


async def test_a_posted_ticket_press_raises_modmails_own_form(guarded, member):
    item = await restored(TICKET)
    interaction = FakeInteraction(guarded, member)

    await item.callback(interaction)

    assert isinstance(interaction.response.modals[0], TicketModal)


async def test_a_posted_request_press_is_refused_in_requests_own_words(guarded, member):
    await guarded.store.set(GUILD, "request_mode", "off")
    item = await restored(REQUEST)
    interaction = FakeInteraction(guarded, member)

    await item.callback(interaction)

    assert interaction.sent == REQUESTS_OFF


async def test_a_posted_event_press_opens_a_private_card_and_never_draws_over_the_door(
    guarded, member
):
    item = await restored(EVENT)
    interaction = FakeInteraction(guarded, member)

    await item.callback(interaction)

    sent = interaction.response.messages[-1]
    assert sent["ephemeral"] is True
    assert isinstance(sent["view"], EventHandoff)
    assert isinstance(sent["view"].children[0], ProposeButton)
    assert not interaction.edits


async def test_a_press_on_a_door_left_up_while_the_mode_went_off_is_refused_in_words(
    guarded, member
):
    await guarded.store.set(GUILD, FRONTDOOR_MODE, "off")
    item = await restored(TICKET)
    interaction = FakeInteraction(guarded, member)

    await item.callback(interaction)

    assert interaction.sent == DOOR_OFF
    assert not interaction.response.modals


async def test_the_cog_registers_the_one_dynamic_item_on_load(guarded, cog):
    await cog.cog_load()

    assert DoorButton in guarded.dynamic_items


# --- shadow mode ----------------------------------------------------------------------------


@pytest.fixture
def live(bot):
    """Test mode is lifted, so nothing but the mode itself decides where the door goes."""
    bot.guild.add(FakeText(777, name="welcome"))
    bot.guild.add(FakeText(888, name="welcome-test"))
    return bot


@pytest.fixture
def staffer(live):
    return FakeMember(live.guild, user_id=901, display_name="Lead", roles=(STAFF_ROLE,))


async def aim_the_door(bot, *, channel_id=777, mode="on"):
    await bot.store.set(GUILD, SHADOW_CHANNEL, 888)
    await bot.store.set(GUILD, FRONTDOOR_CHANNEL, channel_id)
    await bot.store.set(GUILD, FRONTDOOR_MODE, mode)


async def test_shadow_posts_the_copy_in_the_rehearsal_home_and_nothing_in_the_real_channel(
    live, member
):
    """The owner's ask: live, and still not in #welcome."""
    welcome = live.guild.get_channel(777)
    home = live.guild.get_channel(888)
    await live.store.set(GUILD, SHADOW_CHANNEL, 888)
    await live.store.set(GUILD, FRONTDOOR_MODE, "shadow")

    outcome = await post_door(live, live.guild, member, welcome)

    assert outcome.ok and not welcome.messages
    copy = door_message(home)
    assert copy.content == "Rehearsal — this is where it would go: #welcome"
    assert door_labels(copy) == [label_for(live.store, GUILD, kind) for kind in KINDS]
    assert live.store.get(GUILD, FRONTDOOR_SHADOW_MESSAGE) == str(copy.id)
    assert live.store.get(GUILD, FRONTDOOR_CHANNEL) == 777
    assert not live.store.get(GUILD, FRONTDOOR_MESSAGE)
    assert POSTED_SHADOW in await kinds_in(live.db)
    assert POSTED not in await kinds_in(live.db)


async def test_the_shadow_sentence_says_shadow_rather_than_test_mode(live, member):
    welcome = live.guild.get_channel(777)
    await live.store.set(GUILD, SHADOW_CHANNEL, 888)
    await live.store.set(GUILD, FRONTDOOR_MODE, "shadow")

    outcome = await post_door(live, live.guild, member, welcome)

    assert "shadow" in outcome.message and "test mode" not in outcome.message
    assert "888" in outcome.message and "777" in outcome.message


async def test_turning_the_door_to_shadow_takes_the_real_one_down_and_puts_a_copy_up(
    live, cog, member
):
    welcome = live.guild.get_channel(777)
    home = live.guild.get_channel(888)
    await aim_the_door(live)
    await post_door(live, live.guild, member, welcome)
    real_id = door_message(welcome).id
    await live.store.set(GUILD, FRONTDOOR_MODE, "shadow")

    await cog.reconcile()

    assert real_id in welcome.deleted and not welcome.messages
    assert not live.store.get(GUILD, FRONTDOOR_MESSAGE)
    assert live.store.get(GUILD, FRONTDOOR_CHANNEL) == 777
    assert live.store.get(GUILD, FRONTDOOR_SHADOW_MESSAGE) == str(door_message(home).id)
    said = await kinds_in(live.db)
    assert TAKEN_DOWN in said and POSTED_SHADOW in said


async def test_turning_it_back_on_takes_the_copy_down_and_posts_the_real_door(
    live, cog, member
):
    welcome = live.guild.get_channel(777)
    home = live.guild.get_channel(888)
    await aim_the_door(live, mode="shadow")
    await cog.reconcile()
    copy_id = door_message(home).id
    await live.store.set(GUILD, FRONTDOOR_MODE, "on")

    await cog.reconcile()

    assert copy_id in home.deleted and not home.messages
    assert not live.store.get(GUILD, FRONTDOOR_SHADOW_MESSAGE)
    assert not live.store.get(GUILD, FRONTDOOR_SHADOW_HASH)
    assert live.store.get(GUILD, FRONTDOOR_MESSAGE) == str(door_message(welcome).id)
    said = await kinds_in(live.db)
    assert TAKEN_DOWN_SHADOW in said and POSTED in said


async def test_a_blank_rehearsal_home_rehearses_in_the_log_channel(live, cog, member):
    welcome = live.guild.get_channel(777)
    log = live.guild.get_channel(LOG_CHANNEL)
    await live.store.set(GUILD, FRONTDOOR_CHANNEL, 777)
    await live.store.set(GUILD, FRONTDOOR_MODE, "shadow")

    await cog.reconcile()

    assert log.messages and not welcome.messages
    assert live.store.get(GUILD, FRONTDOOR_SHADOW_MESSAGE) == str(door_message(log).id)


async def test_shadow_with_nowhere_to_rehearse_at_all_posts_nothing_and_says_why(live, member):
    welcome = live.guild.get_channel(777)
    live.settings = load_settings(_env_file=None, test_mode=False, test_channel_id=None)
    live.store.settings = live.settings
    await live.store.clear(GUILD, "log_channel_id")
    await live.store.set(GUILD, FRONTDOOR_MODE, "shadow")

    outcome = await post_door(live, live.guild, member, welcome)

    assert not outcome.ok and outcome.message == DOOR_NO_HOME
    assert "shadow_channel_id" in outcome.message and "test mode" not in outcome.message
    assert not welcome.messages
    assert WOULD_POST in await kinds_in(live.db)


async def test_the_sweep_keeps_the_copy_current_and_leaves_the_real_channel_alone(
    live, cog, member
):
    welcome = live.guild.get_channel(777)
    home = live.guild.get_channel(888)
    await aim_the_door(live, mode="shadow")
    await cog.reconcile()
    copy_id = door_message(home).id
    await live.store.set(GUILD, FRONTDOOR_TITLE, "Stuck?")

    await cog.reconcile()

    assert len(home.messages) == 1 and door_message(home).id == copy_id
    assert door_message(home).kwargs["embed"].title == "Stuck?"
    assert not welcome.messages
    assert UPDATED_SHADOW in await kinds_in(live.db)


async def test_ask_still_answers_while_the_door_is_rehearsing(live, cog, member):
    await aim_the_door(live, mode="shadow")
    interaction = FakeInteraction(live, member)

    await cog.ask.callback(cog, interaction)

    sent = interaction.response.messages[-1]
    assert sent["ephemeral"] is True and isinstance(sent["view"], DoorPanel)
    assert interaction.sent != DOOR_OFF


async def test_the_ask_panel_tells_a_STAFFER_the_door_is_rehearsing_and_a_member_nothing(
    live, cog, member, staffer
):
    await aim_the_door(live, mode="shadow")

    for_staff, _view = build_panel(live, live.guild, staffer)
    for_member, _also = build_panel(live, live.guild, member)

    said = (for_staff.footer.text or "") if for_staff.footer else ""
    assert said.startswith("shadow") and "rehearsing in #welcome-test" in said
    assert said.endswith("nothing is in #welcome.")
    assert for_member.footer is None or not for_member.footer.text


async def test_the_staff_line_is_empty_while_the_door_is_simply_on(live, staffer):
    await aim_the_door(live)

    embed, _view = build_panel(live, live.guild, staffer)

    assert embed.footer is None or not embed.footer.text
    assert shadow_words(live, live.guild) == ""


async def test_the_ticket_button_follows_the_door_into_shadow(live, cog, member):
    welcome = live.guild.get_channel(777)
    home = live.guild.get_channel(888)
    button_id = await put_the_ticket_button_up(live, welcome)
    await aim_the_door(live, mode="shadow")

    await cog.reconcile()
    await Modmail(live)._repanel(live.guild)

    assert button_id in welcome.deleted and not welcome.messages
    assert not live.store.get(GUILD, MODMAIL_PANEL_MESSAGE)
    assert live.store.get(GUILD, MODMAIL_PANEL_CHANNEL) == 777
    assert len(home.messages) == 1
    assert TICKET_BUTTON_HIDDEN in await kinds_in(live.db)


async def test_a_ticket_button_in_another_channel_follows_the_door_into_shadow_too(
    live, cog, member
):
    """`frontdoor_replaces_ticket_button` is the switch, not the channel it happens to be in."""
    elsewhere = live.guild.add(FakeText(778, name="help"))
    button_id = await put_the_ticket_button_up(live, elsewhere)
    await aim_the_door(live, mode="shadow")

    await cog.reconcile()
    await Modmail(live)._repanel(live.guild)

    assert button_id in elsewhere.deleted and not elsewhere.messages
    assert not live.store.get(GUILD, MODMAIL_PANEL_MESSAGE)


async def test_the_ticket_button_keeps_its_own_rules_in_shadow_when_the_key_is_off(
    live, cog, member
):
    welcome = live.guild.get_channel(777)
    button_id = await put_the_ticket_button_up(live, welcome)
    await aim_the_door(live, mode="shadow")
    await live.store.set(GUILD, FRONTDOOR_REPLACES_TICKET_BUTTON, False)

    await cog.reconcile()
    await Modmail(live)._repanel(live.guild)

    assert button_id not in welcome.deleted
    assert live.store.get(GUILD, MODMAIL_PANEL_MESSAGE) == str(button_id)


async def test_coming_out_of_shadow_lets_modmails_own_sweep_put_its_button_back(
    live, cog, member
):
    welcome = live.guild.get_channel(777)
    elsewhere = live.guild.add(FakeText(778, name="help"))
    await put_the_ticket_button_up(live, elsewhere)
    await aim_the_door(live, mode="shadow")
    await cog.reconcile()
    await live.store.set(GUILD, FRONTDOOR_MODE, "on")

    await cog.reconcile()
    await Modmail(live)._repanel(live.guild)

    assert welcome.messages
    assert live.store.get(GUILD, MODMAIL_PANEL_MESSAGE)
    assert "modmail.panel_posted" in await kinds_in(live.db)
