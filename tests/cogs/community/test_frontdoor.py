import discord
import pytest

from black_bloc.cogs.community.events import EVENTS_OFF, ProposeButton
from black_bloc.cogs.community.frontdoor import (
    DoorPanel,
    EventDoor,
    FrontDoor,
    RequestDoor,
    TicketDoor,
    build_panel,
)
from black_bloc.cogs.community.requests import REQUESTS_OFF, FileButton
from black_bloc.cogs.moderation.modmail import TicketModal
from black_bloc.config import load_settings
from black_bloc.frontdoor import DOOR_OFF, KINDS, label_for
from black_bloc.settings_store import (
    FRONTDOOR_MODE,
    FRONTDOOR_TEXT,
    FRONTDOOR_TICKET_LABEL,
    FRONTDOOR_TITLE,
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

    def own_channel(self, channel):
        self.owned_channel_ids.add(int(getattr(channel, "id", channel)))

    def allows_channel(self, channel):
        here = int(getattr(channel, "id", channel))
        return here == self.test_channel_id or here in self.owned_channel_ids

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
