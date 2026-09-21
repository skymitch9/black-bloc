import json
import re

import discord
import pytest

from black_bloc import handoff as pure_handoff
from black_bloc import requests as pure
from black_bloc.cogs.community import requests as requests_cog
from black_bloc.cogs.community.requests import (
    LogsButton,
    NoteModal,
    ReadyModal,
    RequestModal,
    RequestPick,
    Requests,
    RequestView,
    WithdrawPick,
)
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore

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
        if "embeds" in kwargs:
            self.embeds = list(kwargs["embeds"])
        elif kwargs.get("embed") is not None:
            self.embeds = [kwargs["embed"]]
        if "view" in kwargs:
            self.view = kwargs["view"]


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


class FakeForumPost(FakeText):
    def __init__(self, thread_id, parent, name, **kwargs):
        super().__init__(thread_id, name=name)
        self.parent = parent
        self.parent_id = parent.id
        self.applied_tags = list(kwargs.get("applied_tags") or ())
        self.kwargs = kwargs
        self.archived = False

    async def edit(self, **kwargs):
        if "applied_tags" in kwargs:
            self.applied_tags = list(kwargs["applied_tags"] or ())
        self.archived = kwargs.get("archived", self.archived)

    def get_partial_message(self, message_id):
        return next((one for one in self.messages if one.id == message_id), None)


class FakeForum:
    def __init__(self, channel_id, guild=None, category=None, name="requests", **kwargs):
        self.id = channel_id
        self.guild = guild
        self.name = name
        self.mention = f"<#{channel_id}>"
        self.category = category
        self.available_tags = list(kwargs.get("available_tags") or ())
        self.topic = kwargs.get("topic")
        self.given_overwrites = kwargs.get("overwrites")
        self.kwargs = kwargs
        self.posts = []
        self.thread_raises = None

    async def create_thread(self, *, name, **kwargs):
        if self.thread_raises is not None:
            raise self.thread_raises
        post = FakeForumPost(7000 + len(self.posts), self, name, **kwargs)
        starter = {k: v for k, v in kwargs.items() if k != "content"}
        message = FakeMessage(9000 + len(self.posts), kwargs.get("content") or "", **starter)
        post.messages.append(message)
        self.posts.append(post)
        if self.guild is not None:
            self.guild.threads[post.id] = post
        return discord.channel.ThreadWithMessage(thread=post, message=message)


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black in a Flash!"
        self.channels = {}
        self.threads = {}
        self.members = {}
        self.roles = [FakeRole(STAFF_ROLE, "Lead")]
        self.me = FakeRole(99, "Black Bloc")
        self.create_raises = None
        self._next_id = 6000

    def get_channel(self, channel_id):
        return self.channels.get(channel_id) or self.threads.get(channel_id)

    def get_thread(self, thread_id):
        return self.threads.get(thread_id)

    def get_member(self, user_id):
        return self.members.get(user_id)

    async def create_forum(self, name, **kwargs):
        if self.create_raises is not None:
            raise self.create_raises
        self._next_id += 1
        category = kwargs.pop("category", None)
        forum = FakeForum(self._next_id, self, category, name=name, **kwargs)
        self.add(forum)
        return forum

    def add(self, channel):
        channel.guild = self
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
        self.dms.append({"content": content, **kwargs})


class FakeGuard:
    def __init__(self, test_channel_id=TEST_CHANNEL):
        self.test_channel_id = test_channel_id
        self.owned_channel_ids = set()

    def own_channel(self, channel):
        self.owned_channel_ids.add(int(getattr(channel, "id", channel)))

    def disown_channel(self, channel):
        self.owned_channel_ids.discard(int(getattr(channel, "id", channel)))

    def owns_channel(self, channel):
        return int(getattr(channel, "id", channel)) in self.owned_channel_ids

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
        self.user = guild.me
        self.guard = None
        self._cog = None
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
        return self._cog


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
        self.messages.append(
            {"content": None, "deferred": True, "ephemeral": ephemeral, **kwargs}
        )


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
        self._message = None

    async def edit_original_response(self, **kwargs):
        self._message = FakeMessage(9500, kwargs.get("content") or "", **kwargs)
        return self._message

    async def original_response(self):
        last = self.response.messages[-1]
        kept = {k: v for k, v in last.items() if k not in ("ephemeral", "content", "deferred")}
        self._message = FakeMessage(9500, last.get("content") or "", **kept)
        return self._message

    @property
    def message(self):
        return self._message

    @property
    def sent(self):
        said = [m["content"] for m in self.response.messages if m["content"] is not None]
        return said[-1] if said else None


async def action_kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


def card_of(sent):
    """The embed a channel post or a DM carried, as the dict Discord would have been sent."""
    embed = (sent.kwargs if hasattr(sent, "kwargs") else sent)["embed"]
    assert embed is not None
    return embed.to_dict()


def words_in(card):
    """Every word on one card, so a test can say what it must mention without naming a field."""
    return " ".join(
        [card.get("title", ""), *[one["value"] for one in card.get("fields", [])]]
    )


def link_of(sent):
    view = (sent.kwargs if hasattr(sent, "kwargs") else sent)["view"]
    return view.children[0].url if view is not None else None


def view_of(sent):
    return (sent.kwargs if hasattr(sent, "kwargs") else sent).get("view")


def inner(item):
    """A `DynamicItem` wraps its button rather than being one; the label lives inside."""
    return getattr(item, "item", item)


def post_labels(sent):
    view = view_of(sent)
    return [] if view is None else [getattr(inner(one), "label", None) for one in view.children]


def post_button(sent, label):
    return next(
        one for one in view_of(sent).children if getattr(inner(one), "label", None) == label
    )


def site_link_of(sent):
    view = view_of(sent)
    if view is None:
        return None
    urls = [getattr(inner(one), "url", None) for one in view.children]
    return next((one for one in urls if one), None)


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
    found = Requests(bot)
    bot._cog = found
    return found


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


async def request_at(bot, member, lead, status):
    """A fresh request, moved through the shared functions to land on `status`."""
    request_id = await pure.create_request(
        bot.db, GUILD, member.id, what="a request board", why="because", due_on=None
    )
    if status == pure.OPEN:
        return request_id
    if status in (pure.IN_PROGRESS, pure.REVIEW, pure.DONE):
        await requests_cog.apply_decision(bot, bot.guild, request_id, pure.IN_PROGRESS, lead)
    if status in (pure.REVIEW, pure.DONE):
        await requests_cog.mark_ready(bot, bot.guild, request_id, lead, "a board", "press it")
    if status == pure.DONE:
        await requests_cog.accept(bot, bot.guild, request_id, lead)
    if status == pure.HOLD:
        await requests_cog.apply_decision(
            bot, bot.guild, request_id, pure.HOLD, lead, reason="waiting"
        )
    if status == pure.MOVED:
        await pure.set_status(bot.db, request_id, pure.MOVED)
    if status == pure.DECLINED:
        await requests_cog.apply_decision(
            bot, bot.guild, request_id, pure.DECLINED, lead, reason="no"
        )
    if status == pure.WITHDRAWN:
        row = await pure.get_request(bot.db, request_id)
        await pure.withdraw_request(bot, bot.guild, row, member)
    return request_id


async def open_panel(cog, bot, who):
    interaction = FakeInteraction(bot, who)
    await cog.request.callback(cog, interaction)
    return interaction


def panel_view(interaction):
    return interaction.response.messages[-1]["view"]


def panel_embed(interaction):
    return interaction.response.messages[-1]["embed"]


def find_item(view, label):
    return next(item for item in view.children if getattr(item, "label", None) == label)


async def click(bot, who, item):
    interaction = FakeInteraction(bot, who)
    await item.callback(interaction)
    return interaction


def card_embed(interaction):
    return interaction.message.kwargs.get("embed")


def card_view(interaction):
    return interaction.message.kwargs.get("view")


# --- the top-level command and its two panels ------------------------------------------------


async def test_the_command_answers_ephemerally_with_a_panel(cog, bot, member):
    interaction = await open_panel(cog, bot, member)

    assert interaction.response.messages[0]["ephemeral"] is True
    assert isinstance(panel_view(interaction), RequestView)
    assert panel_embed(interaction).title == pure.PANEL_TITLE


async def test_the_command_run_in_a_dm_says_it_belongs_in_the_server(cog, bot, member):
    interaction = FakeInteraction(bot, member, guild=False)

    await cog.request.callback(cog, interaction)

    assert "in the server itself" in interaction.sent


async def test_the_command_refuses_in_words_when_the_database_is_down(
    cog, bot, member, monkeypatch
):
    monkeypatch.setattr(bot.db, "_conn", None)
    interaction = FakeInteraction(bot, member)

    await cog.request.callback(cog, interaction)

    assert "cannot reach its own database" in interaction.sent


async def test_a_member_panel_shows_file_and_refresh_and_no_staff_controls(cog, bot, member):
    interaction = await open_panel(cog, bot, member)
    view = panel_view(interaction)
    labels = [getattr(item, "label", None) for item in view.children]

    assert "File a request" in labels
    assert "Refresh" in labels
    assert not any(isinstance(item, RequestPick) for item in view.children)
    assert not any(isinstance(item, LogsButton) for item in view.children)


async def test_a_member_with_nothing_filed_is_told_so_when_the_list_is_on(cog, bot, member):
    await bot.store.set(GUILD, "request_panel_own_list", True)

    interaction = await open_panel(cog, bot, member)

    assert pure.PANEL_EMPTY in panel_embed(interaction).description


async def test_a_member_sees_their_own_requests_summarised_when_the_list_is_on(cog, bot, member):
    await bot.store.set(GUILD, "request_panel_own_list", True)
    await file_one(cog, bot, member, what="a request board")

    interaction = await open_panel(cog, bot, member)

    assert "request board" in panel_embed(interaction).description


async def test_a_member_is_not_shown_their_own_requests_by_default(cog, bot, member):
    await file_one(cog, bot, member, what="a request board")

    interaction = await open_panel(cog, bot, member)

    assert "request board" not in panel_embed(interaction).description
    assert pure.PANEL_EMPTY not in panel_embed(interaction).description
    assert pure.PANEL_INTRO in panel_embed(interaction).description


async def test_a_member_with_nothing_filed_is_told_nothing_by_default(cog, bot, member):
    interaction = await open_panel(cog, bot, member)

    assert pure.PANEL_EMPTY not in panel_embed(interaction).description


async def test_a_member_keeps_filing_and_taking_one_back_with_the_list_hidden(cog, bot, member):
    await file_one(cog, bot, member, what="a request board")

    interaction = await open_panel(cog, bot, member)
    view = panel_view(interaction)
    labels = [getattr(item, "label", None) for item in view.children]

    assert "File a request" in labels
    assert any(isinstance(item, WithdrawPick) for item in view.children)


async def test_staff_see_their_own_requests_whatever_the_key_says(cog, bot, lead):
    await file_one(cog, bot, lead, what="a request board")

    off = await open_panel(cog, bot, lead)
    assert "request board" in panel_embed(off).description

    await bot.store.set(GUILD, "request_panel_own_list", True)
    on = await open_panel(cog, bot, lead)
    assert "request board" in panel_embed(on).description


async def test_staff_with_nothing_of_their_own_are_told_so_whatever_the_key_says(
    cog, bot, lead, member
):
    await file_one(cog, bot, member)

    off = await open_panel(cog, bot, lead)
    assert pure.PANEL_EMPTY in panel_embed(off).description

    await bot.store.set(GUILD, "request_panel_own_list", True)
    on = await open_panel(cog, bot, lead)
    assert pure.PANEL_EMPTY in panel_embed(on).description


async def test_a_staff_panel_adds_the_select_and_logs(cog, bot, lead, member):
    await file_one(cog, bot, member)
    interaction = await open_panel(cog, bot, lead)
    view = panel_view(interaction)

    assert any(isinstance(item, RequestPick) for item in view.children)
    assert any(isinstance(item, LogsButton) for item in view.children)
    assert "open" in panel_embed(interaction).description


async def test_a_staff_panel_with_nothing_open_says_so_and_drops_the_select(cog, bot, lead):
    interaction = await open_panel(cog, bot, lead)
    view = panel_view(interaction)

    assert not any(isinstance(item, RequestPick) for item in view.children)
    assert pure.NOTHING_OPEN in panel_embed(interaction).description


async def test_the_staff_select_caps_at_25_and_says_how_many_are_left(cog, bot, lead, member):
    for number in range(30):
        await pure.create_request(
            bot.db, GUILD, member.id, what=f"one {number}", why="because", due_on=None
        )
    interaction = await open_panel(cog, bot, lead)
    select = next(
        item for item in panel_view(interaction).children if isinstance(item, RequestPick)
    )

    assert len(select.options) == 25
    assert select.placeholder == "25 of 30 — the rest are on the site"


async def test_a_full_select_names_the_status_and_the_id_on_every_option(cog, bot, lead, member):
    await file_one(cog, bot, member)
    interaction = await open_panel(cog, bot, lead)
    select = next(
        item for item in panel_view(interaction).children if isinstance(item, RequestPick)
    )

    assert select.options[0].label.startswith("#1 · open · ")


async def test_the_open_site_link_appears_only_when_an_origin_is_set(cog, bot, member, db):
    with_origin = await open_panel(cog, bot, member)
    with_labels = [getattr(item, "label", None) for item in panel_view(with_origin).children]
    assert pure.SITE_BUTTON in with_labels

    bare_settings = load_settings(
        _env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL, site_origin=""
    )
    bare_bot = FakeBot(db, bot.store, bare_settings, bot.guild)
    bare_bot._cog = Requests(bare_bot)
    without_origin = await open_panel(bare_bot._cog, bare_bot, member)
    assert not any(
        getattr(item, "label", None) == pure.SITE_BUTTON
        for item in panel_view(without_origin).children
    )


# --- gates -------------------------------------------------------------------------------------


async def test_requests_off_hides_file_and_says_so(cog, bot, member):
    await bot.store.set(GUILD, "request_mode", "off")
    interaction = await open_panel(cog, bot, member)
    view = panel_view(interaction)

    assert not any(getattr(item, "label", None) == "File a request" for item in view.children)
    assert pure.REQUESTS_OFF in panel_embed(interaction).description


async def test_staff_only_filing_hides_file_for_a_member_and_says_why(cog, bot, member, lead):
    await bot.store.set(GUILD, "request_who_can_file", "staff")
    member_interaction = await open_panel(cog, bot, member)
    lead_interaction = await open_panel(cog, bot, lead)

    assert not any(
        getattr(item, "label", None) == "File a request"
        for item in panel_view(member_interaction).children
    )
    assert pure.STAFF_ONLY_FILES in panel_embed(member_interaction).description
    assert any(
        getattr(item, "label", None) == "File a request"
        for item in panel_view(lead_interaction).children
    )


async def test_the_file_button_still_refuses_by_hand_if_things_changed_underneath_it(
    cog, bot, member
):
    interaction = await open_panel(cog, bot, member)
    button = find_item(panel_view(interaction), "File a request")
    await bot.store.set(GUILD, "request_mode", "off")

    clicked = FakeInteraction(bot, member)
    await button.callback(clicked)

    assert not clicked.response.modals
    assert "turned off" in clicked.sent


async def test_the_file_button_opens_the_existing_modal_unchanged(cog, bot, member):
    interaction = await open_panel(cog, bot, member)
    button = find_item(panel_view(interaction), "File a request")

    clicked = FakeInteraction(bot, member)
    await button.callback(clicked)

    assert len(clicked.response.modals) == 1
    assert isinstance(clicked.response.modals[0], RequestModal)


async def test_filing_through_the_panel_still_files_exactly_as_before(cog, bot, member, db):
    interaction = await file_one(cog, bot, member, due="2026-09-15")
    row = await pure.get_request(db, 1)

    assert row["status"] == pure.OPEN and row["user_id"] == member.id
    assert "#1" in interaction.sent and "Request has been received" in interaction.sent
    assert "request.filed" in await action_kinds(db)


async def test_the_refresh_button_re_renders_the_panel(cog, bot, member):
    await bot.store.set(GUILD, "request_panel_own_list", True)
    interaction = await open_panel(cog, bot, member)
    button = find_item(panel_view(interaction), "Refresh")
    await file_one(cog, bot, member, what="a fresh one")

    clicked = FakeInteraction(bot, member)
    await button.callback(clicked)

    assert "a fresh one" in card_embed(clicked).description


# --- the card: exactly the buttons the table says ----------------------------------------------

EXPECTED_BUTTONS = {
    pure.OPEN: ["Pick up", "Hold", "Decline"],
    pure.IN_PROGRESS: ["Ready to check", "Hold", "Decline"],
    pure.REVIEW: ["Accept", "Ask them to check", "Send back", "Hold", "Decline"],
    pure.HOLD: ["Resume", "Decline"],
    pure.DONE: [],
    pure.DECLINED: [],
    pure.WITHDRAWN: [],
    pure.MOVED: [],
}
# `handoff_mode` ships on, so every state a request can still move from also carries the
# Send to... row; a final one carries none, which is what refuses a stale press.
HANDOFF_BUTTONS = {
    status: (
        []
        if status in pure.FINAL_STATUSES
        else [pure_handoff.SEND_TO_EVENTS, pure_handoff.OPEN_A_TICKET]
    )
    for status in pure.STATUSES
}


@pytest.mark.parametrize("status", pure.STATUSES)
async def test_the_card_renders_exactly_the_buttons_the_table_says(cog, bot, member, lead, status):
    request_id = await request_at(bot, member, lead, status)
    row = await pure.get_request(bot.db, request_id)

    embed, view = requests_cog.build_card(bot, bot.guild, row, lead)

    assert [item.label for item in view.children] == [
        *EXPECTED_BUTTONS[status],
        *HANDOFF_BUTTONS[status],
        "Back",
    ]
    if not EXPECTED_BUTTONS[status]:
        assert "finishes" in embed.footer.text
    # Discord takes five items an action row; review's fifth move filled the first one, so
    # Back sits on its own below rather than making a sixth.
    assert len([item for item in view.children if item.row == 0]) <= 5
    assert find_item(view, "Back").row == 1


async def test_accept_is_not_rendered_when_the_server_asks_for_a_second_pair_of_eyes(
    cog, bot, member, lead
):
    await bot.store.set(GUILD, "request_review_by_other", True)
    request_id = await request_at(bot, member, lead, pure.REVIEW)
    row = await pure.get_request(bot.db, request_id)

    embed, view = requests_cog.build_card(bot, bot.guild, row, lead)

    labels = [item.label for item in view.children]
    assert "Accept" not in labels
    assert f"<@{lead.id}>" in embed.footer.text


async def test_picking_a_request_opens_its_card(cog, bot, member, lead):
    request_id = await request_at(bot, member, lead, pure.OPEN)
    panel = await open_panel(cog, bot, lead)
    select = next(item for item in panel_view(panel).children if isinstance(item, RequestPick))
    select._values = [str(request_id)]

    interaction = await click(bot, lead, select)

    assert card_embed(interaction).title == f"New request #{request_id}"
    assert [item.label for item in card_view(interaction).children] == [
        *EXPECTED_BUTTONS[pure.OPEN],
        *HANDOFF_BUTTONS[pure.OPEN],
        "Back",
    ]


async def test_picking_a_number_nobody_filed_says_so_and_stays_on_the_panel(cog, bot, lead):
    select = RequestPick([], 0)
    select._values = ["99"]

    interaction = await click(bot, lead, select)

    assert "no request" in interaction.sent


async def test_back_returns_to_the_panel(cog, bot, member, lead):
    request_id = await request_at(bot, member, lead, pure.OPEN)
    row = await pure.get_request(bot.db, request_id)
    _, card = requests_cog.build_card(bot, bot.guild, row, lead)
    back = find_item(card, "Back")

    interaction = await click(bot, lead, back)

    assert card_embed(interaction).title == pure.PANEL_TITLE


# --- each button calls the right shared function, `via` untouched ------------------------------


@pytest.mark.parametrize(
    ("status", "label", "func_name"),
    [
        (pure.OPEN, "Pick up", "apply_decision"),
        (pure.HOLD, "Resume", "resume_request"),
        (pure.REVIEW, "Accept", "accept"),
        (pure.REVIEW, "Ask them to check", "ask_check"),
    ],
)
async def test_a_direct_move_button_calls_its_shared_function_and_leaves_via_alone(
    cog, bot, member, lead, monkeypatch, status, label, func_name
):
    request_id = await request_at(bot, member, lead, status)
    row = await pure.get_request(bot.db, request_id)
    _, view = requests_cog.build_card(bot, bot.guild, row, lead)
    button = find_item(view, label)

    calls = []

    async def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return ("moved along", row)

    monkeypatch.setattr(requests_cog, func_name, fake)

    interaction = await click(bot, lead, button)

    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args[0] is bot and args[1] is bot.guild
    assert "via" not in kwargs
    assert interaction.sent == "moved along"
    assert card_embed(interaction) is not None


@pytest.mark.parametrize(
    ("status", "label", "modal_cls"),
    [
        (pure.OPEN, "Hold", NoteModal),
        (pure.OPEN, "Decline", NoteModal),
        (pure.IN_PROGRESS, "Ready to check", ReadyModal),
        (pure.REVIEW, "Send back", NoteModal),
    ],
)
async def test_a_note_or_ready_button_opens_the_right_modal(
    cog, bot, member, lead, status, label, modal_cls
):
    request_id = await request_at(bot, member, lead, status)
    row = await pure.get_request(bot.db, request_id)
    _, view = requests_cog.build_card(bot, bot.guild, row, lead)
    button = find_item(view, label)

    interaction = FakeInteraction(bot, lead)
    await button.callback(interaction)

    assert len(interaction.response.modals) == 1
    assert isinstance(interaction.response.modals[0], modal_cls)


async def test_the_ready_modal_carries_the_rows_existing_text_as_its_default(
    cog, bot, member, lead
):
    request_id = await request_at(bot, member, lead, pure.IN_PROGRESS)
    row = await pure.get_request(bot.db, request_id)
    _, view = requests_cog.build_card(bot, bot.guild, row, lead)
    button = find_item(view, "Ready to check")

    interaction = FakeInteraction(bot, lead)
    await button.callback(interaction)
    modal = interaction.response.modals[0]

    assert modal.built.required is True and modal.how_to_test.required is False


async def test_the_ready_modal_submits_through_mark_ready_and_re_renders(
    cog, bot, member, lead, monkeypatch
):
    request_id = await request_at(bot, member, lead, pure.IN_PROGRESS)
    row = await pure.get_request(bot.db, request_id)
    calls = []

    async def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return ("ready to check", row)

    monkeypatch.setattr(requests_cog, "mark_ready", fake)
    modal = ReadyModal(cog, request_id, row)
    modal.built._value = "a board"
    modal.how_to_test._value = "press it"

    interaction = FakeInteraction(bot, lead)
    await modal.on_submit(interaction)

    assert calls[0][0] == (bot, bot.guild, request_id, lead, "a board", "press it")
    assert "via" not in calls[0][1]
    assert interaction.sent == "ready to check"
    assert card_embed(interaction) is not None


@pytest.mark.parametrize(
    ("kind", "func_name", "kwarg"),
    [("hold", "apply_decision", "reason"), ("decline", "apply_decision", "reason"),
     ("sendback", "send_back", None)],
)
async def test_the_note_modal_submits_through_the_right_shared_function(
    cog, bot, member, lead, monkeypatch, kind, func_name, kwarg
):
    request_id = await request_at(
        bot, member, lead, pure.REVIEW if kind == "sendback" else pure.OPEN
    )
    calls = []

    async def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return ("noted", None)

    monkeypatch.setattr(requests_cog, func_name, fake)
    modal = NoteModal(cog, request_id, kind)
    modal.note._value = "the reason"

    interaction = FakeInteraction(bot, lead)
    await modal.on_submit(interaction)

    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args[0] is bot and args[1] is bot.guild
    assert "via" not in kwargs
    if kwarg:
        assert kwargs[kwarg] == "the reason"
    else:
        assert args[-1] == "the reason"
    assert interaction.sent == "noted"


async def test_the_note_modal_labels_name_who_the_note_is_sent_to():
    hold = NoteModal(None, 1, "hold")
    decline = NoteModal(None, 1, "decline")
    sendback = NoteModal(None, 1, "sendback")

    assert len(hold.note.label) <= 45 and "asker" in hold.note.label
    assert len(decline.note.label) <= 45 and "asker" in decline.note.label
    assert len(sendback.note.label) <= 45 and "ready" in sendback.note.label
    assert hold.note.max_length == pure.REASON_LIMIT
    assert sendback.note.max_length == pure.SENT_BACK_LIMIT


# --- gates the move buttons still respect (unchanged, exercised through the panel) -------------


async def test_a_declined_request_carries_its_reason_into_the_dm_through_the_panel(
    cog, bot, member, lead, db
):
    request_id = await request_at(bot, member, lead, pure.OPEN)
    row = await pure.get_request(bot.db, request_id)
    _, view = requests_cog.build_card(bot, bot.guild, row, lead)
    button = find_item(view, "Decline")
    interaction = FakeInteraction(bot, lead)
    await button.callback(interaction)
    modal = interaction.response.modals[0]
    modal.note._value = "we already have one"

    submitted = FakeInteraction(bot, lead)
    await modal.on_submit(submitted)
    row = await pure.get_request(db, request_id)

    assert row["status"] == pure.DECLINED and row["decline_reason"] == "we already have one"
    assert "we already have one" in words_in(card_of(member.dms[-1]))


async def test_the_same_staffer_may_not_accept_their_own_review_once_the_server_says_so(
    cog, bot, member, lead, db
):
    request_id = await request_at(bot, member, lead, pure.REVIEW)
    await bot.store.set(GUILD, "request_review_by_other", True)
    row = await pure.get_request(bot.db, request_id)

    embed, view = requests_cog.build_card(bot, bot.guild, row, lead)

    assert "Accept" not in [item.label for item in view.children]
    assert (await pure.get_request(db, request_id))["status"] == pure.REVIEW


# --- withdraw select, confirm/keep ---------------------------------------------------------------


async def test_the_withdraw_select_only_appears_when_something_can_be_taken_back(cog, bot, member):
    empty = await open_panel(cog, bot, member)
    assert not any(
        isinstance(item, WithdrawPick) for item in panel_view(empty).children
    )

    await file_one(cog, bot, member)
    filled = await open_panel(cog, bot, member)
    assert any(isinstance(item, WithdrawPick) for item in panel_view(filled).children)


async def test_choosing_one_to_withdraw_shows_its_card_and_a_yes_keep_choice(cog, bot, member):
    await file_one(cog, bot, member)
    panel = await open_panel(cog, bot, member)
    select = next(item for item in panel_view(panel).children if isinstance(item, WithdrawPick))
    select._values = ["1"]

    interaction = await click(bot, member, select)
    view = card_view(interaction)

    assert card_embed(interaction).title == "New request #1"
    assert [item.label for item in view.children] == ["Yes, take it back", "Keep it"]


async def test_every_panel_re_render_silences_mentions(cog, bot, member):
    await file_one(cog, bot, member)
    panel = await open_panel(cog, bot, member)
    select = next(item for item in panel_view(panel).children if isinstance(item, WithdrawPick))
    select._values = ["1"]
    confirm = await click(bot, member, select)
    back = await click(bot, member, find_item(card_view(confirm), "Keep it"))

    for interaction in (confirm, back):
        allowed = interaction.message.kwargs.get("allowed_mentions")
        assert allowed is not None
        assert (allowed.everyone, allowed.users, allowed.roles) == (False, False, False)


async def test_confirming_a_withdraw_calls_the_same_code_the_route_calls(
    cog, bot, member, db, monkeypatch
):
    await file_one(cog, bot, member)
    panel = await open_panel(cog, bot, member)
    select = next(item for item in panel_view(panel).children if isinstance(item, WithdrawPick))
    select._values = ["1"]
    confirm = await click(bot, member, select)
    yes = find_item(card_view(confirm), "Yes, take it back")

    calls = []
    real = requests_cog.withdraw_request

    async def spying(*args, **kwargs):
        calls.append((args, kwargs))
        return await real(*args, **kwargs)

    monkeypatch.setattr(requests_cog, "withdraw_request", spying)

    interaction = await click(bot, member, yes)

    assert len(calls) == 1
    assert (await pure.get_request(db, 1))["status"] == pure.WITHDRAWN
    assert "withdrawn" in interaction.sent
    assert card_embed(interaction).title == pure.PANEL_TITLE


async def test_keeping_it_leaves_the_request_untouched(cog, bot, member, db):
    await file_one(cog, bot, member)
    panel = await open_panel(cog, bot, member)
    select = next(item for item in panel_view(panel).children if isinstance(item, WithdrawPick))
    select._values = ["1"]
    confirm = await click(bot, member, select)
    keep = find_item(card_view(confirm), "Keep it")

    interaction = await click(bot, member, keep)

    assert (await pure.get_request(db, 1))["status"] == pure.OPEN
    assert card_embed(interaction).title == pure.PANEL_TITLE


async def test_a_withdraw_race_that_is_no_longer_withdrawable_is_caught_in_words(
    cog, bot, member, lead, db
):
    await file_one(cog, bot, member)
    panel = await open_panel(cog, bot, member)
    select = next(item for item in panel_view(panel).children if isinstance(item, WithdrawPick))
    select._values = ["1"]
    await requests_cog.apply_decision(bot, bot.guild, 1, pure.IN_PROGRESS, lead)

    interaction = await click(bot, member, select)

    assert "nothing to withdraw" in interaction.sent
    assert card_embed(interaction).title == pure.PANEL_TITLE


# --- timeout -------------------------------------------------------------------------------------


async def test_the_view_disables_every_item_and_says_so_on_timeout():
    view = RequestView(15)
    view.add_item(requests_cog.FileButton())
    view.add_item(requests_cog.RefreshButton())
    message = FakeMessage(1, embed=discord.Embed(title=pure.PANEL_TITLE))
    view.message = message

    await view.on_timeout()

    assert all(item.disabled for item in view.children)
    assert message.embeds[0].footer.text == pure.PANEL_TIMEOUT_FOOTER


async def test_a_view_with_no_message_yet_does_nothing_on_timeout():
    view = RequestView(15)
    view.add_item(requests_cog.RefreshButton())
    token = FakeToken()
    view.last_interaction = token

    await view.on_timeout()

    assert token.edits == []
    assert not any(item.disabled for item in view.children)


# --- a replaced view stops; the survivor writes its footer through the freshest token ----------


class FakeToken:
    """Only what `on_timeout` reaches for — the interaction token's own original response."""

    def __init__(self, raises=None):
        self.edits = []
        self.raises = raises

    async def edit_original_response(self, **kwargs):
        if self.raises is not None:
            raise self.raises
        self.edits.append(kwargs)


class DeafMessage(FakeMessage):
    async def edit(self, **kwargs):
        raise refused()


async def test_a_re_render_stops_the_view_it_replaced(cog, bot, member, lead):
    request_id = await request_at(bot, member, lead, pure.OPEN)
    panel = await open_panel(cog, bot, lead)
    replaced = panel_view(panel)
    select = next(item for item in replaced.children if isinstance(item, RequestPick))
    select._values = [str(request_id)]

    interaction = await click(bot, lead, select)

    assert replaced.is_finished() and replaced.replaced is True
    assert card_view(interaction) is not replaced
    assert card_view(interaction).replaced is False


async def test_the_view_a_re_render_replaced_never_edits_the_message_again(cog, bot, member):
    await file_one(cog, bot, member)
    panel = await open_panel(cog, bot, member)
    replaced = panel_view(panel)
    message = FakeMessage(1, embed=discord.Embed(title=pure.PANEL_TITLE))
    replaced.message = message
    select = next(item for item in replaced.children if isinstance(item, WithdrawPick))
    select._values = ["1"]

    await click(bot, member, select)
    await replaced.on_timeout()

    assert message.embeds[0].footer.text is None
    assert message.view is None
    assert not any(item.disabled for item in replaced.children)


async def test_a_view_that_was_replaced_does_nothing_on_timeout():
    view = RequestView(10)
    view.add_item(requests_cog.RefreshButton())
    message = FakeMessage(1, embed=discord.Embed(title=pure.PANEL_TITLE))
    view.message = message
    requests_cog.retire(view)

    await view.on_timeout()

    assert view.is_finished()
    assert message.embeds[0].footer.text is None


async def test_the_check_records_the_freshest_interaction_and_lets_the_click_through():
    view = RequestView(10)
    token = FakeToken()

    assert await view.interaction_check(token) is True
    assert view.last_interaction is token


async def test_the_timeout_footer_goes_through_the_freshest_interaction_token():
    view = RequestView(10)
    view.add_item(requests_cog.RefreshButton())
    message = FakeMessage(1, embed=discord.Embed(title=pure.PANEL_TITLE))
    view.message = message
    token = FakeToken()
    await view.interaction_check(token)

    await view.on_timeout()

    assert token.edits[0]["embeds"][0].footer.text == pure.PANEL_TIMEOUT_FOOTER
    assert all(item.disabled for item in token.edits[0]["view"].children)
    assert message.view is None


async def test_the_timeout_footer_falls_back_to_the_message_when_no_token_was_recorded():
    view = RequestView(10)
    view.add_item(requests_cog.RefreshButton())
    message = FakeMessage(1, embed=discord.Embed(title=pure.PANEL_TITLE))
    view.message = message

    await view.on_timeout()

    assert view.last_interaction is None
    assert message.embeds[0].footer.text == pure.PANEL_TIMEOUT_FOOTER


async def test_the_timeout_footer_falls_back_to_the_message_when_the_token_has_expired():
    view = RequestView(10)
    view.add_item(requests_cog.RefreshButton())
    message = FakeMessage(1, embed=discord.Embed(title=pure.PANEL_TITLE))
    view.message = message
    await view.interaction_check(FakeToken(raises=refused()))

    await view.on_timeout()

    assert message.embeds[0].footer.text == pure.PANEL_TIMEOUT_FOOTER


async def test_a_timeout_discord_refuses_outright_is_logged_not_raised():
    view = RequestView(10)
    view.add_item(requests_cog.RefreshButton())
    view.message = DeafMessage(1, embed=discord.Embed(title=pure.PANEL_TITLE))
    await view.interaction_check(FakeToken(raises=refused()))

    await view.on_timeout()

    assert all(item.disabled for item in view.children)


# --- staff demoted while a card is open ---------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "label"),
    [
        (pure.OPEN, "Pick up"),
        (pure.OPEN, "Hold"),
        (pure.IN_PROGRESS, "Ready to check"),
        (pure.HOLD, "Resume"),
    ],
)
async def test_a_staffer_demoted_while_the_card_is_open_moves_nothing(
    cog, bot, member, lead, monkeypatch, db, status, label
):
    request_id = await request_at(bot, member, lead, status)
    row = await pure.get_request(bot.db, request_id)
    _, view = requests_cog.build_card(bot, bot.guild, row, lead)
    button = find_item(view, label)
    calls = []

    async def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return ("moved along", row)

    for name in ("apply_decision", "mark_ready", "resume_request", "accept", "send_back"):
        monkeypatch.setattr(requests_cog, name, fake)
    stranger = FakeMember(bot.guild, user_id=950, display_name="Ex")

    interaction = await click(bot, stranger, button)

    assert not calls
    assert not interaction.response.modals
    assert "staff only" in interaction.sent
    assert (await pure.get_request(db, request_id))["status"] == status


async def test_a_demoted_staffer_submitting_the_ready_modal_is_refused_in_words(
    cog, bot, member, lead, monkeypatch, db
):
    request_id = await request_at(bot, member, lead, pure.IN_PROGRESS)
    row = await pure.get_request(bot.db, request_id)
    calls = []

    async def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return ("ready to check", row)

    monkeypatch.setattr(requests_cog, "mark_ready", fake)
    modal = ReadyModal(cog, request_id, row)
    modal.built._value = "a board"
    stranger = FakeMember(bot.guild, user_id=951, display_name="Ex")

    interaction = FakeInteraction(bot, stranger)
    await modal.on_submit(interaction)

    assert not calls
    assert "staff only" in interaction.sent
    assert (await pure.get_request(db, request_id))["status"] == pure.IN_PROGRESS


@pytest.mark.parametrize("kind", ["hold", "decline", "sendback"])
async def test_a_demoted_staffer_submitting_a_note_modal_is_refused_in_words(
    cog, bot, member, lead, monkeypatch, db, kind
):
    status = pure.REVIEW if kind == "sendback" else pure.OPEN
    request_id = await request_at(bot, member, lead, status)
    calls = []

    async def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return ("noted", None)

    monkeypatch.setattr(requests_cog, "apply_decision", fake)
    monkeypatch.setattr(requests_cog, "send_back", fake)
    modal = NoteModal(cog, request_id, kind)
    modal.note._value = "the reason"
    stranger = FakeMember(bot.guild, user_id=952, display_name="Ex")

    interaction = FakeInteraction(bot, stranger)
    await modal.on_submit(interaction)

    assert not calls
    assert "staff only" in interaction.sent
    assert (await pure.get_request(db, request_id))["status"] == status


async def test_the_logs_button_still_refuses_a_demoted_staffer_in_words(cog, bot, member):
    button = LogsButton()

    interaction = await click(bot, member, button)

    assert "staff only" in interaction.sent
    assert not any(m.get("embed") for m in interaction.response.messages)


# --- the last ten log lines ------------------------------------------------------------------


async def test_the_logs_button_answers_with_a_new_ephemeral_message(cog, bot, lead, member, db):
    await file_one(cog, bot, member)
    interaction = await open_panel(cog, bot, lead)
    button = next(item for item in panel_view(interaction).children if isinstance(item, LogsButton))

    clicked = FakeInteraction(bot, lead)
    await button.callback(clicked)

    assert clicked.response.messages[0]["embed"].title.startswith("Request")
    assert clicked.response.messages[0]["ephemeral"] is True


# --- sixth pass: Ask them to check -------------------------------------------------------------


async def check_rows(db):
    cur = await db.conn.execute(
        "SELECT kind, details FROM action_log WHERE kind LIKE '%check_asked%' ORDER BY id"
    )
    return [(row["kind"], json.loads(row["details"] or "{}")) for row in await cur.fetchall()]


async def test_asking_them_to_check_dms_the_requester_and_leaves_the_request_where_it_is(
    cog, bot, member, lead, db
):
    request_id = await request_at(bot, member, lead, pure.REVIEW)
    member.dms.clear()

    said, fresh = await requests_cog.ask_check(bot, bot.guild, request_id, lead)

    assert f"#{request_id}" in said and "asked by DM" in said
    assert fresh["status"] == pure.REVIEW
    assert fresh["check_asked_by"] == lead.id and fresh["check_asked_at"]
    assert len(member.dms) == 1
    card = card_of(member.dms[0])
    assert card["title"] == f"Request #{request_id} is ready for you to try 🙌"
    assert "Try it and tell" in card["description"]
    assert "a board" in words_in(card)
    rows = await check_rows(db)
    assert [kind for kind, _ in rows] == ["request.check_asked"]
    assert rows[0][1] == {"request_id": request_id, "told": "dm", "via": "discord"}


async def test_the_check_dm_carries_the_site_button_like_every_other_card(
    cog, bot, member, lead
):
    """It goes through the same `card()` builder, so the DM opens on the request's own anchor."""
    request_id = await request_at(bot, member, lead, pure.REVIEW)
    member.dms.clear()

    await requests_cog.ask_check(bot, bot.guild, request_id, lead)

    assert link_of(member.dms[0]) == pure.request_url(bot.settings.origin, request_id)


async def test_a_closed_dm_pings_the_requester_in_the_request_channel_instead(
    cog, bot, member, lead, db
):
    request_id = await request_at(bot, member, lead, pure.REVIEW)
    channel = bot.guild.get_channel(TEST_CHANNEL)
    channel.messages.clear()
    member.dm_raises = refused()

    said, _ = await requests_cog.ask_check(bot, bot.guild, request_id, lead)

    assert "DMs are closed" in said and "pinged in the request channel" in said
    assert len(channel.messages) == 1
    sent = channel.messages[0]
    assert sent.content == f"<@{member.id}>"
    assert [one.id for one in sent.kwargs["allowed_mentions"].users] == [member.id]
    assert card_of(sent)["title"].endswith("ready for you to try 🙌")
    kinds = await action_kinds(db)
    assert kinds.count("request.dm_failed") == 1
    rows = await check_rows(db)
    assert rows[-1][1]["told"] == "channel"


async def test_the_fallback_ping_is_the_only_place_this_cog_mentions_anybody(
    cog, bot, member, lead
):
    """Every other send is AllowedMentions.none(); this one names exactly one person."""
    request_id = await request_at(bot, member, lead, pure.REVIEW)
    channel = bot.guild.get_channel(TEST_CHANNEL)
    channel.messages.clear()

    await requests_cog.ask_check(bot, bot.guild, request_id, lead)

    assert channel.messages == []
    assert member.dms[-1]["allowed_mentions"].everyone is False


async def test_with_the_fallback_off_nobody_is_told_and_the_reply_names_the_key(
    cog, bot, member, lead, db
):
    await bot.store.set(GUILD, "request_check_fallback_channel", False)
    request_id = await request_at(bot, member, lead, pure.REVIEW)
    channel = bot.guild.get_channel(TEST_CHANNEL)
    channel.messages.clear()
    member.dm_raises = refused()

    said, _ = await requests_cog.ask_check(bot, bot.guild, request_id, lead)

    assert "nobody was told" in said and "request_check_fallback_channel" in said
    assert channel.messages == []
    rows = await check_rows(db)
    assert rows[-1][1]["told"] == "nobody"


async def test_asking_on_something_that_is_not_ready_to_check_is_refused_in_words(
    cog, bot, member, lead, db
):
    request_id = await request_at(bot, member, lead, pure.IN_PROGRESS)
    member.dms.clear()

    said, fresh = await requests_cog.ask_check(bot, bot.guild, request_id, lead)

    assert fresh is None
    assert "not ready to check" in said and "ask them to check" in said
    assert "/request ready" not in said
    assert member.dms == []
    assert await check_rows(db) == []
    row = await pure.get_request(db, request_id)
    assert row["check_asked_at"] is None


async def test_a_number_nobody_filed_is_a_sentence_rather_than_a_crash(cog, bot, lead, db):
    said, fresh = await requests_cog.ask_check(bot, bot.guild, 404, lead)

    assert fresh is None and "no request" in said
    assert await check_rows(db) == []


async def test_the_channel_copy_is_off_by_default_and_never_doubles_the_ping(
    cog, bot, member, lead
):
    await bot.store.set(GUILD, "request_channel_moves", ["check_asked"])
    request_id = await request_at(bot, member, lead, pure.REVIEW)
    channel = bot.guild.get_channel(TEST_CHANNEL)
    channel.messages.clear()

    await requests_cog.ask_check(bot, bot.guild, request_id, lead)

    assert len(channel.messages) == 1
    assert channel.messages[0].content == ""

    channel.messages.clear()
    member.dm_raises = refused()
    await requests_cog.ask_check(bot, bot.guild, request_id, lead)

    assert len(channel.messages) == 1
    assert channel.messages[0].content == f"<@{member.id}>"


def log_titles(bot):
    return [
        message.kwargs["embed"].title
        for message in bot.guild.get_channel(LOG_CHANNEL).messages
        if message.kwargs.get("embed") is not None
    ]


async def test_the_done_card_is_the_discord_record_not_the_raw_log_line(
    cog, bot, member, lead, db
):
    await bot.store.set(GUILD, "request_channel_moves", list(pure.CHANNEL_LOOKS))
    request_id = await request_at(bot, member, lead, pure.REVIEW)
    channel = bot.guild.get_channel(TEST_CHANNEL)
    channel.messages.clear()
    bot.guild.get_channel(LOG_CHANNEL).messages.clear()

    await requests_cog.accept(bot, bot.guild, request_id, lead)

    assert len(channel.messages) == 1
    assert log_titles(bot) == []
    assert (await action_kinds(db))[-1] == "request.done"

    await bot.store.set(GUILD, "request_log_level", "all")
    second = await request_at(bot, member, lead, pure.REVIEW)
    bot.guild.get_channel(LOG_CHANNEL).messages.clear()

    await requests_cog.accept(bot, bot.guild, second, lead)

    assert log_titles(bot) == ["request.done"]


async def test_a_move_without_a_card_still_reaches_the_log_channel(cog, bot, member, lead):
    await bot.store.set(GUILD, "request_channel_moves", [])
    request_id = await request_at(bot, member, lead, pure.REVIEW)
    bot.guild.get_channel(LOG_CHANNEL).messages.clear()

    await requests_cog.accept(bot, bot.guild, request_id, lead)

    assert log_titles(bot) == ["request.done"]


async def test_marking_ready_asks_automatically_only_when_the_server_says_so(
    cog, bot, member, lead, db
):
    request_id = await request_at(bot, member, lead, pure.IN_PROGRESS)
    member.dms.clear()

    await requests_cog.mark_ready(bot, bot.guild, request_id, lead, "a board", "press it")

    assert await check_rows(db) == []
    assert member.dms == []

    await bot.store.set(GUILD, "request_check_on_ready", True)
    second = await request_at(bot, member, lead, pure.IN_PROGRESS)
    member.dms.clear()

    said, fresh = await requests_cog.mark_ready(
        bot, bot.guild, second, lead, "a board", "press it"
    )

    assert "ready to check" in said
    assert fresh["status"] == pure.REVIEW and fresh["check_asked_by"] == lead.id
    assert len(member.dms) == 1
    kinds = await action_kinds(db)
    assert kinds[-2:] == ["request.review", "request.check_asked"]


async def test_the_card_shows_who_asked_and_when_so_nobody_asks_twice_by_accident(
    cog, bot, member, lead
):
    request_id = await request_at(bot, member, lead, pure.REVIEW)
    row = await pure.get_request(bot.db, request_id)
    before, _ = requests_cog.build_card(bot, bot.guild, row, lead)

    assert "Asked to check" not in [field.name for field in before.fields]

    await requests_cog.ask_check(bot, bot.guild, request_id, lead)
    fresh = await pure.get_request(bot.db, request_id)
    after, view = requests_cog.build_card(bot, bot.guild, fresh, lead)
    asked = next(field for field in after.fields if field.name == "Asked to check")

    assert asked.value.startswith(f"<@{lead.id}> · <t:")
    assert "Ask them to check" in [item.label for item in view.children]


async def test_the_first_pair_of_eyes_may_still_ask_the_requester(cog, bot, member, lead):
    """`may_accept` takes Accept away; asking the person who filed it is nobody else's job."""
    await bot.store.set(GUILD, "request_review_by_other", True)
    request_id = await request_at(bot, member, lead, pure.REVIEW)
    row = await pure.get_request(bot.db, request_id)

    _, view = requests_cog.build_card(bot, bot.guild, row, lead)
    labels = [item.label for item in view.children]

    assert "Accept" not in labels and "Ask them to check" in labels


async def test_the_button_records_the_panel_via_and_re_renders_the_card(
    cog, bot, member, lead, db
):
    request_id = await request_at(bot, member, lead, pure.REVIEW)
    row = await pure.get_request(bot.db, request_id)
    _, view = requests_cog.build_card(bot, bot.guild, row, lead)
    member.dms.clear()

    interaction = await click(bot, lead, find_item(view, "Ask them to check"))

    assert "asked by DM" in interaction.sent
    assert card_embed(interaction) is not None
    rows = await check_rows(db)
    assert [kind for kind, _ in rows] == ["request.check_asked"]
    assert rows[0][1]["via"] == "discord"


async def test_a_staffer_demoted_while_the_review_card_is_open_asks_nobody(
    cog, bot, member, lead, db
):
    request_id = await request_at(bot, member, lead, pure.REVIEW)
    row = await pure.get_request(bot.db, request_id)
    _, view = requests_cog.build_card(bot, bot.guild, row, lead)
    member.dms.clear()

    interaction = await click(bot, member, find_item(view, "Ask them to check"))

    assert "staff only" in interaction.sent
    assert member.dms == []
    assert await check_rows(db) == []


# --- the request forum (blackmail-threads §B) ------------------------------------------------


BLACKMAIL = 5050
FORUM = 5151


async def make_the_forum(cog, bot, lead):
    opened = await open_panel(cog, bot, lead)
    item = find_item(panel_view(opened), requests_cog.MAKE_THE_FORUM)
    return await click(bot, lead, item)


def forum_of(bot):
    return bot.guild.get_channel(bot.store.get(GUILD, "request_forum_channel_id"))


async def point_at_a_forum(bot, *, tags=True):
    """The forum staff already have, with the tags Make-the-forum would have given it."""
    made = pure.forum_tags() if tags else []
    forum = bot.guild.add(FakeForum(FORUM, bot.guild, available_tags=made))
    await bot.store.set(GUILD, "request_forum_channel_id", forum.id)
    if bot.guard is not None:
        bot.guard.own_channel(forum)
    return forum


def tags_on(post):
    return [tag.name for tag in post.applied_tags]


async def test_a_filed_request_opens_its_own_post_tagged_open(cog, bot, member, db):
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot)

    await file_one(cog, bot, member, what="a request board")

    post = forum.posts[0]
    assert post.name == "#1 a request board"
    assert tags_on(post) == ["open"]
    assert post.kwargs["auto_archive_duration"] == 1440
    row = await pure.get_request(db, 1)
    assert row["thread_id"] == post.id and row["message_id"] == post.messages[0].id
    assert card_of(post.messages[0])["title"] == "New request #1"


async def test_a_forum_post_carries_the_cards_link_button(cog, bot, member):
    """SINCE v122 the link shares the row with the moves — §F; it is no longer child zero."""
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot)

    await file_one(cog, bot, member)

    assert site_link_of(forum.posts[0].messages[0]) is not None


async def test_every_move_lands_in_the_requests_own_post_not_the_status_channel(
    cog, bot, member, lead, db
):
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot)
    await bot.store.set(GUILD, "request_notify_channel_id", TEST_CHANNEL)
    await file_one(cog, bot, member)

    await requests_cog.apply_decision(bot, bot.guild, 1, pure.IN_PROGRESS, lead)

    post = forum.posts[0]
    assert [card_of(one)["title"] for one in post.messages] == [
        "New request #1",
        "Request #1 is being worked on",
    ]
    assert bot.guild.get_channel(TEST_CHANNEL).messages == []
    assert tags_on(post) == ["picked up"]


async def test_a_request_moving_through_the_board_re_tags_its_own_post_each_time(
    cog, bot, member, lead
):
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot)
    await file_one(cog, bot, member)
    post = forum.posts[0]

    await requests_cog.apply_decision(bot, bot.guild, 1, pure.IN_PROGRESS, lead)
    assert tags_on(post) == ["picked up"]

    await requests_cog.mark_ready(bot, bot.guild, 1, lead, "a board", "press it")
    assert tags_on(post) == ["ready to check"]

    await requests_cog.apply_decision(bot, bot.guild, 1, pure.HOLD, lead, reason="waiting")
    assert tags_on(post) == ["on hold"]
    assert post.archived is False


async def test_a_done_request_is_tagged_done_and_its_post_archived(cog, bot, member, lead):
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot)
    await file_one(cog, bot, member)
    await requests_cog.apply_decision(bot, bot.guild, 1, pure.IN_PROGRESS, lead)
    await requests_cog.mark_ready(bot, bot.guild, 1, lead, "a board", "press it")

    await requests_cog.accept(bot, bot.guild, 1, lead)

    post = forum.posts[0]
    assert tags_on(post) == ["done"] and post.archived is True
    assert not bot.guard.owns_channel(post)
    # `done` is not in `request_channel_moves` by default, so the tag is the only record.
    assert card_of(post.messages[-1])["title"] == "Request #1 is ready to check 🔎"


async def test_a_declined_request_is_tagged_declined_and_its_post_archived(
    cog, bot, member, lead
):
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot)
    await file_one(cog, bot, member)

    await requests_cog.apply_decision(bot, bot.guild, 1, pure.DECLINED, lead, reason="no")

    post = forum.posts[0]
    assert tags_on(post) == ["declined"] and post.archived is True


async def test_a_forum_with_no_matching_tag_still_posts_and_still_archives(
    cog, bot, member, lead
):
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot, tags=False)
    await file_one(cog, bot, member)

    await requests_cog.apply_decision(bot, bot.guild, 1, pure.DECLINED, lead, reason="no")

    post = forum.posts[0]
    assert post.applied_tags == [] and post.archived is True


async def test_a_blank_forum_key_keeps_todays_notify_channel(cog, bot, member, lead, db):
    bot.guard = FakeGuard()
    await bot.store.set(GUILD, "request_notify_channel_id", TEST_CHANNEL)

    await file_one(cog, bot, member)
    await requests_cog.apply_decision(bot, bot.guild, 1, pure.IN_PROGRESS, lead)

    titles = [card_of(one)["title"] for one in bot.guild.get_channel(TEST_CHANNEL).messages]
    assert titles == ["New request #1", "Request #1 is being worked on"]
    assert (await pure.get_request(db, 1))["thread_id"] is None


async def test_a_keyed_forum_is_claimed_for_the_guard_so_test_mode_still_posts(
    cog, bot, member, db
):
    bot.guard = FakeGuard()
    bot.guild.add(FakeForum(FORUM, bot.guild, available_tags=pure.forum_tags()))
    await bot.store.set(GUILD, "request_forum_channel_id", FORUM)

    await file_one(cog, bot, member)

    assert bot.guard.owns_channel(FORUM)
    assert len(bot.guild.get_channel(FORUM).posts) == 1
    assert (await pure.get_request(db, 1))["thread_id"] is not None
    assert "request.notify_skipped_test_mode" not in await action_kinds(db)


async def test_a_forum_discord_refuses_leaves_the_request_filed_and_says_so_in_the_log(
    cog, bot, member, db
):
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot)
    forum.thread_raises = refused()

    await file_one(cog, bot, member)

    row = await pure.get_request(db, 1)
    assert row is not None and row["thread_id"] is None
    assert "request.notify_failed" in await action_kinds(db)


async def test_the_post_is_claimed_again_whenever_black_bloc_writes_to_it(
    cog, bot, member, lead
):
    """A guard claim dies with the process; a restart must not drop the move cards."""
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot)
    await file_one(cog, bot, member)
    post = forum.posts[0]
    bot.guard.owned_channel_ids = {forum.id}

    await requests_cog.apply_decision(bot, bot.guild, 1, pure.IN_PROGRESS, lead)

    assert len(post.messages) == 2 and tags_on(post) == ["picked up"]


async def test_staff_make_the_request_forum_under_blackmail_with_every_tag(
    cog, bot, lead, db
):
    bot.guard = FakeGuard()
    category = bot.guild.add(FakeText(BLACKMAIL, name="Blackmail"))
    category.overwrites = {FakeRole(STAFF_ROLE): "staff see it"}
    await bot.store.set(GUILD, "modmail_category_id", BLACKMAIL)

    said = await make_the_forum(cog, bot, lead)

    forum = forum_of(bot)
    assert forum.name == "requests" and forum.category is category
    assert [tag.name for tag in forum.available_tags] == [
        "open",
        "picked up",
        "ready to check",
        "on hold",
        "done",
        "declined",
        "moved",
    ]
    assert [getattr(who, "id", who) for who in forum.given_overwrites] == [
        STAFF_ROLE,
        bot.guild.me.id,
    ]
    assert "test mode" in said.sent and "request.forum_made" in await action_kinds(db)


async def test_the_make_the_forum_button_goes_once_the_forum_is_there(cog, bot, lead):
    bot.guard = FakeGuard()
    await point_at_a_forum(bot)

    opened = await open_panel(cog, bot, lead)

    labels = [getattr(one, "label", None) for one in panel_view(opened).children]
    assert requests_cog.MAKE_THE_FORUM not in labels


async def test_a_member_is_never_offered_make_the_forum(cog, bot, member):
    bot.guard = FakeGuard()

    opened = await open_panel(cog, bot, member)

    labels = [getattr(one, "label", None) for one in panel_view(opened).children]
    assert requests_cog.MAKE_THE_FORUM not in labels


async def test_the_request_forum_needs_the_blackmail_category_and_says_which_key(
    cog, bot, lead
):
    bot.guard = FakeGuard()

    said = await make_the_forum(cog, bot, lead)

    assert "modmail_category_id" in said.sent and "Ticket category…" in said.sent
    assert bot.store.get(GUILD, "request_forum_channel_id") is None


async def test_a_refused_request_forum_is_said_in_words_and_logged(cog, bot, lead, db):
    bot.guard = FakeGuard()
    bot.guild.add(FakeText(BLACKMAIL, name="Blackmail"))
    await bot.store.set(GUILD, "modmail_category_id", BLACKMAIL)
    bot.guild.create_raises = refused()

    said = await make_the_forum(cog, bot, lead)

    assert "could not make the forum" in said.sent
    assert bot.store.get(GUILD, "request_forum_channel_id") is None
    assert "request.forum_failed" in await action_kinds(db)


async def test_a_deleted_request_forum_is_forgotten_rather_than_kept_as_a_dead_id(
    cog, bot, db
):
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot)

    await cog.on_guild_channel_delete(forum)

    assert bot.store.get(GUILD, "request_forum_channel_id") is None
    assert "request.forum_forgotten" in await action_kinds(db)


# --- the staff moves on the post itself (blackmail-threads §F) --------------------------------


async def posted(cog, bot, member, **fields):
    """One filed request, its forum, and the first message of its own post."""
    forum = await point_at_a_forum(bot)
    await file_one(cog, bot, member, **fields)
    return forum.posts[0]


async def submit_modal(bot, who, modal):
    interaction = FakeInteraction(bot, who)
    await modal.on_submit(interaction)
    return interaction


async def test_the_posts_first_message_carries_the_moves_for_where_the_request_is(
    cog, bot, member
):
    bot.guard = FakeGuard()

    post = await posted(cog, bot, member)

    assert post_labels(post.messages[0]) == [
        "Pick up",
        "Hold",
        "Decline",
        pure_handoff.SEND_TO_EVENTS,
        pure_handoff.OPEN_A_TICKET,
        pure.SITE_BUTTON,
    ]
    assert site_link_of(post.messages[0]) is not None


async def test_the_posts_buttons_are_the_same_table_the_panel_card_draws(cog, bot, member, lead):
    """One table, two surfaces: §F asks for `card_buttons`, not a second list."""
    bot.guard = FakeGuard()
    post = await posted(cog, bot, member)
    await requests_cog.apply_decision(bot, bot.guild, 1, pure.IN_PROGRESS, lead)
    row = await pure.get_request(bot.db, 1)

    _, card = requests_cog.build_card(bot, bot.guild, row, lead)

    on_the_card = [one.label for one in card.children if hasattr(one, "spec")]
    assert post_labels(post.messages[0])[:-3] == on_the_card


async def test_a_staff_press_on_the_post_moves_the_request_and_answers_only_them(
    cog, bot, member, lead, db
):
    bot.guard = FakeGuard()
    post = await posted(cog, bot, member)

    said = await click(bot, lead, post_button(post.messages[0], "Pick up"))

    assert (await pure.get_request(db, 1))["status"] == pure.IN_PROGRESS
    assert "is now **being worked on**" in said.sent
    assert said.response.messages[-1]["ephemeral"] is True
    assert "request.in_progress" in await action_kinds(db)


async def test_a_staff_press_re_draws_the_first_messages_buttons_for_the_new_status(
    cog, bot, member, lead
):
    bot.guard = FakeGuard()
    post = await posted(cog, bot, member)

    await click(bot, lead, post_button(post.messages[0], "Pick up"))

    assert post_labels(post.messages[0]) == [
        "Ready to check",
        "Hold",
        "Decline",
        pure_handoff.SEND_TO_EVENTS,
        pure_handoff.OPEN_A_TICKET,
        pure.SITE_BUTTON,
    ]


async def test_a_staff_press_still_posts_the_move_line_into_the_post(cog, bot, member, lead):
    bot.guard = FakeGuard()
    post = await posted(cog, bot, member)

    await click(bot, lead, post_button(post.messages[0], "Pick up"))

    assert [card_of(one)["title"] for one in post.messages] == [
        "New request #1",
        "Request #1 is being worked on",
    ]
    assert tags_on(post) == ["picked up"]


async def test_a_members_press_on_the_post_is_refused_in_words_naming_what_it_needs(
    cog, bot, member, db
):
    """Nothing is hidden by rendering — a forum post is one message for everybody."""
    bot.guard = FakeGuard()
    post = await posted(cog, bot, member)

    said = await click(bot, member, post_button(post.messages[0], "Pick up"))

    assert "for staff only" in said.sent
    assert "Manage Server" in said.sent and "Ask a server admin" in said.sent
    assert said.response.messages[-1]["ephemeral"] is True
    assert (await pure.get_request(db, 1))["status"] == pure.OPEN


async def test_a_decided_request_keeps_the_link_and_loses_every_move(cog, bot, member, lead):
    bot.guard = FakeGuard()
    post = await posted(cog, bot, member)

    await requests_cog.apply_decision(bot, bot.guild, 1, pure.DECLINED, lead, reason="no")

    assert post_labels(post.messages[0]) == [pure.SITE_BUTTON]
    assert post.archived is True


async def test_a_move_that_needs_a_note_opens_the_modal_and_finishes_on_the_post(
    cog, bot, member, lead, db
):
    bot.guard = FakeGuard()
    post = await posted(cog, bot, member)

    opening = await click(bot, lead, post_button(post.messages[0], "Hold"))
    modal = opening.response.modals[0]
    assert modal.on_post is True
    modal.note._value = "waiting on art"
    said = await submit_modal(bot, lead, modal)

    assert (await pure.get_request(db, 1))["status"] == pure.HOLD
    assert post_labels(post.messages[0]) == [
        "Resume",
        "Decline",
        pure_handoff.SEND_TO_EVENTS,
        pure_handoff.OPEN_A_TICKET,
        pure.SITE_BUTTON,
    ]
    assert said.response.messages[-1]["ephemeral"] is True


async def test_the_ready_modal_from_a_post_answers_the_presser_not_the_post(
    cog, bot, member, lead, db
):
    bot.guard = FakeGuard()
    post = await posted(cog, bot, member)
    await click(bot, lead, post_button(post.messages[0], "Pick up"))

    opening = await click(bot, lead, post_button(post.messages[0], "Ready to check"))
    modal = opening.response.modals[0]
    modal.built._value = "a request board"
    modal.how_to_test._value = "press it"
    said = await submit_modal(bot, lead, modal)

    assert (await pure.get_request(db, 1))["status"] == pure.REVIEW
    assert said.message is None
    assert "ready to check" in said.sent


async def test_a_post_button_rebuilds_itself_from_its_custom_id_after_a_restart(
    cog, bot, member, lead, db
):
    """The proof §F asks for: nothing but the id survives a deploy, and the press still works."""
    bot.guard = FakeGuard()
    await posted(cog, bot, member)
    custom_id = pure.post_move_custom_id(1, "pickup")
    match = re.fullmatch(requests_cog.MOVE_TEMPLATE, custom_id)
    assert match is not None

    fresh = await requests_cog.PostMoveButton.from_custom_id(None, None, match)
    said = await click(bot, lead, fresh)

    assert fresh.request_id == 1 and fresh.spec.action == "pickup"
    assert fresh.custom_id == custom_id
    assert (await pure.get_request(db, 1))["status"] == pure.IN_PROGRESS
    assert "is now **being worked on**" in said.sent


async def test_every_move_in_the_table_has_a_custom_id_the_template_reads_back():
    for action, spec in pure.MOVE_BY_ACTION.items():
        match = re.fullmatch(requests_cog.MOVE_TEMPLATE, pure.post_move_custom_id(12, action))
        assert match is not None, action
        assert match["action"] == action and match["request_id"] == "12"
        assert pure.MOVE_BY_ACTION[match["action"]] is spec


async def test_the_cog_registers_the_post_button_so_a_restart_can_dispatch_it(cog, bot):
    await cog.cog_load()

    assert bot.dynamic_items == [
        requests_cog.PostMoveButton,
        requests_cog.PostHandoffButton,
    ]


async def test_the_review_row_puts_the_site_link_on_a_second_row(cog, bot, member, lead):
    bot.guard = FakeGuard()
    post = await posted(cog, bot, member)
    await requests_cog.apply_decision(bot, bot.guild, 1, pure.IN_PROGRESS, lead)
    await requests_cog.mark_ready(bot, bot.guild, 1, lead, "a board", "press it")

    view = view_of(post.messages[0])
    assert len(post_labels(post.messages[0])) == 8
    assert [one.row for one in view.children][-1] == 1


async def test_the_key_off_leaves_the_post_exactly_what_it_was_before(cog, bot, member, lead):
    bot.guard = FakeGuard()
    await bot.store.set(GUILD, "request_post_buttons", False)

    post = await posted(cog, bot, member)
    await requests_cog.apply_decision(bot, bot.guild, 1, pure.IN_PROGRESS, lead)

    assert post_labels(post.messages[0]) == [pure.SITE_BUTTON]
    assert [card_of(one)["title"] for one in post.messages] == [
        "New request #1",
        "Request #1 is being worked on",
    ]


async def test_the_panel_card_is_untouched_by_the_post_buttons(cog, bot, member, lead):
    """§F leaves the panel a panel: its moves stay ordinary items with no custom id of ours."""
    request_id = await request_at(bot, member, lead, pure.OPEN)
    row = await pure.get_request(bot.db, request_id)

    _, view = requests_cog.build_card(bot, bot.guild, row, lead)

    moves = [one for one in view.children if isinstance(one, requests_cog.CardMoveButton)]
    assert [one.label for one in moves] == ["Pick up", "Hold", "Decline"]
    assert not any(isinstance(one, requests_cog.PostMoveButton) for one in view.children)


# --- a post somebody starts by hand becomes a request (blackmail-threads §G) ------------------


def a_post_by_hand(bot, forum, who, *, name="a request board", said="the doc is a mess"):
    """What Discord hands `on_thread_create`: somebody else's post, with its opening message."""
    post = FakeForumPost(7700 + len(forum.posts), forum, name)
    post.guild = bot.guild
    post.owner_id = getattr(who, "id", who)
    starter = FakeMessage(9700 + len(forum.posts), said)
    starter.author = who
    post.messages.append(starter)
    post.starter_message = starter
    forum.posts.append(post)
    bot.guild.threads[post.id] = post
    return post


async def answers(value):
    return value


async def raises(exc):
    raise exc


async def via_of_filed(db):
    cur = await db.conn.execute(
        "SELECT details FROM action_log WHERE kind = 'request.filed' ORDER BY id"
    )
    return [json.loads(row["details"])["via"] for row in await cur.fetchall()]


async def test_a_post_started_by_hand_becomes_a_request_filed_by_whoever_started_it(
    cog, bot, member, db
):
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot)
    post = a_post_by_hand(bot, forum, member)

    await cog.on_thread_create(post)

    row = await pure.get_request(db, 1)
    assert row["user_id"] == member.id and row["thread_id"] == post.id
    assert (row["what"], row["why"]) == ("a request board", "the doc is a mess")
    assert row["status"] == pure.OPEN and row["source"] == pure.SOURCE_FORUM
    assert tags_on(post) == ["open"] and post.archived is False
    assert await via_of_filed(db) == ["forum"]


async def test_the_bot_replies_in_the_post_with_the_filed_card_and_the_staff_moves(
    cog, bot, member, db
):
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot)
    post = a_post_by_hand(bot, forum, member)

    await cog.on_thread_create(post)

    reply = post.messages[-1]
    assert reply is not post.messages[0]
    assert card_of(reply)["title"] == "New request #1"
    assert post_labels(reply) == [
        "Pick up",
        "Hold",
        "Decline",
        pure_handoff.SEND_TO_EVENTS,
        pure_handoff.OPEN_A_TICKET,
        pure.SITE_BUTTON,
    ]
    assert (await pure.get_request(db, 1))["message_id"] == reply.id


async def test_the_person_who_started_the_post_is_dmed_the_card(cog, bot, member):
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot)
    post = a_post_by_hand(bot, forum, member)

    await cog.on_thread_create(post)

    assert len(member.dms) == 1
    assert card_of(member.dms[0])["title"] == "New request #1"


async def test_a_post_with_nothing_written_in_it_still_files_with_a_why(cog, bot, member, db):
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot)
    post = a_post_by_hand(bot, forum, member, said="")

    await cog.on_thread_create(post)

    assert (await pure.get_request(db, 1))["why"] == pure.ADOPTED_WHY


async def test_a_post_that_already_carries_a_row_is_never_filed_twice(cog, bot, member, db):
    """`notify` made this one seconds ago; the row is what says so."""
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot)
    await file_one(cog, bot, member)
    post = forum.posts[0]

    await cog.on_thread_create(post)

    assert await pure.count_requests(db, GUILD) == 1
    assert len(post.messages) == 1


async def test_a_bot_post_with_no_row_yet_is_still_left_alone(cog, bot, db):
    """The gateway can beat `set_thread`; who wrote the post is what makes that harmless."""
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot)
    post = a_post_by_hand(bot, forum, bot.guild.me)

    await cog.on_thread_create(post)

    assert await pure.get_request(db, 1) is None
    assert len(post.messages) == 1


async def test_the_same_post_firing_twice_files_one_request_and_replies_once(
    cog, bot, member, db
):
    """Idempotence: `on_thread_create` can arrive again after a restart (§G)."""
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot)
    post = a_post_by_hand(bot, forum, member)

    await cog.on_thread_create(post)
    await cog.on_thread_create(post)

    assert await pure.get_request(db, 2) is None
    assert len(post.messages) == 2
    assert await via_of_filed(db) == ["forum"]
    assert len(member.dms) == 1


async def test_a_post_by_somebody_who_may_not_file_is_answered_in_words_and_left_alone(
    cog, bot, member, db
):
    bot.guard = FakeGuard()
    await bot.store.set(GUILD, "request_who_can_file", "staff")
    forum = await point_at_a_forum(bot)
    post = a_post_by_hand(bot, forum, member)

    await cog.on_thread_create(post)

    assert await pure.get_request(db, 1) is None
    said = post.messages[-1].content
    assert "only staff may file" in said and "`/request`" in said and "ask staff" in said
    assert member.mention in said
    assert tags_on(post) == [] and post.archived is False
    assert "request.filed" not in await action_kinds(db)


async def test_a_staffers_post_is_adopted_even_when_filing_is_staff_only(cog, bot, lead, db):
    bot.guard = FakeGuard()
    await bot.store.set(GUILD, "request_who_can_file", "staff")
    forum = await point_at_a_forum(bot)
    post = a_post_by_hand(bot, forum, lead)

    await cog.on_thread_create(post)

    assert (await pure.get_request(db, 1))["user_id"] == lead.id


async def test_a_post_started_while_requests_are_off_is_answered_rather_than_filed(
    cog, bot, member, db
):
    bot.guard = FakeGuard()
    await bot.store.set(GUILD, "request_mode", "off")
    forum = await point_at_a_forum(bot)
    post = a_post_by_hand(bot, forum, member)

    await cog.on_thread_create(post)

    assert await pure.get_request(db, 1) is None
    assert "turned off" in post.messages[-1].content


async def test_the_key_off_leaves_a_hand_made_post_completely_alone(cog, bot, member, db):
    bot.guard = FakeGuard()
    await bot.store.set(GUILD, "request_forum_adopts_posts", False)
    forum = await point_at_a_forum(bot)
    post = a_post_by_hand(bot, forum, member)

    await cog.on_thread_create(post)

    assert await pure.get_request(db, 1) is None
    assert len(post.messages) == 1 and tags_on(post) == []


async def test_a_thread_somewhere_else_is_not_a_request(cog, bot, member, db):
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot)
    elsewhere = bot.guild.add(FakeForum(FORUM + 1, bot.guild, available_tags=[]))
    post = a_post_by_hand(bot, elsewhere, member)

    await cog.on_thread_create(post)

    assert await pure.get_request(db, 1) is None
    assert len(post.messages) == 1 and forum.posts == []


async def test_a_hand_made_post_with_no_forum_key_at_all_is_not_a_request(cog, bot, member, db):
    bot.guard = FakeGuard()
    forum = bot.guild.add(FakeForum(FORUM, bot.guild, available_tags=pure.forum_tags()))
    post = a_post_by_hand(bot, forum, member)

    await cog.on_thread_create(post)

    assert await pure.get_request(db, 1) is None
    assert len(post.messages) == 1


async def test_the_adopted_post_is_claimed_so_test_mode_still_lets_the_card_land(
    cog, bot, member
):
    """The guard only ever claimed posts the bot MADE; an adopted one has to be claimed too."""
    bot.guard = FakeGuard()
    forum = bot.guild.add(FakeForum(FORUM, bot.guild, available_tags=pure.forum_tags()))
    await bot.store.set(GUILD, "request_forum_channel_id", FORUM)
    post = a_post_by_hand(bot, forum, member)

    await cog.on_thread_create(post)

    assert bot.guard.owns_channel(post) and bot.guard.owns_channel(FORUM)
    assert len(post.messages) == 2


async def test_an_adopted_request_moves_exactly_like_any_other_one(cog, bot, member, lead, db):
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot)
    post = a_post_by_hand(bot, forum, member)
    await cog.on_thread_create(post)

    await click(bot, lead, post_button(post.messages[1], "Pick up"))

    assert (await pure.get_request(db, 1))["status"] == pure.IN_PROGRESS
    assert post_labels(post.messages[1]) == [
        "Ready to check",
        "Hold",
        "Decline",
        pure_handoff.SEND_TO_EVENTS,
        pure_handoff.OPEN_A_TICKET,
        pure.SITE_BUTTON,
    ]
    assert tags_on(post) == ["picked up"]
    assert [card_of(one)["title"] for one in post.messages[1:]] == [
        "New request #1",
        "Request #1 is being worked on",
    ]


async def test_a_post_whose_starter_has_to_be_fetched_is_still_adopted(cog, bot, member, db):
    """discord.py leaves `starter_message` empty unless that message is cached."""
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot)
    post = a_post_by_hand(bot, forum, member)
    starter = post.starter_message
    post.starter_message = None
    post.fetch_message = lambda message_id: answers(starter)

    await cog.on_thread_create(post)

    assert (await pure.get_request(db, 1))["why"] == "the doc is a mess"


async def test_a_post_whose_first_message_cannot_be_read_is_filed_from_its_owner(
    cog, bot, member, db
):
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot)
    post = a_post_by_hand(bot, forum, member)
    post.starter_message = None
    post.fetch_message = lambda message_id: raises(refused())

    await cog.on_thread_create(post)

    row = await pure.get_request(db, 1)
    assert row["user_id"] == member.id and row["why"] == pure.ADOPTED_WHY


async def test_the_listener_does_nothing_at_all_with_no_database(cog, bot, member):
    bot.guard = FakeGuard()
    forum = await point_at_a_forum(bot)
    post = a_post_by_hand(bot, forum, member)
    await bot.db.close()

    await cog.on_thread_create(post)

    assert len(post.messages) == 1


# --- Send to events… — the press half of a request → event hand-off (send-to-design §A) --------


def handoff_button(view, label=None):
    wanted = label or pure_handoff.SEND_TO_EVENTS
    return next(
        one
        for one in view.children
        if getattr(inner(one), "label", None) == wanted
    )


async def test_the_panel_card_carries_send_to_events_on_its_second_row(cog, bot, member, lead):
    request_id = await request_at(bot, member, lead, pure.OPEN)
    row = await pure.get_request(bot.db, request_id)

    _embed, view = requests_cog.build_card(bot, bot.guild, row, lead)

    button = handoff_button(view)
    assert button.row == 1 and button.action == pure_handoff.EVENT
    assert handoff_button(view, pure_handoff.OPEN_A_TICKET).row == 1
    assert [one.row for one in view.children if one.row == 0] == [0, 0, 0]


async def test_a_final_request_carries_no_send_to_move_at_all(cog, bot, member, lead):
    request_id = await request_at(bot, member, lead, pure.DECLINED)
    row = await pure.get_request(bot.db, request_id)

    _embed, view = requests_cog.build_card(bot, bot.guild, row, lead)

    assert [one.label for one in view.children] == ["Back"]


async def test_the_move_is_not_drawn_at_all_when_the_key_is_off(cog, bot, member, lead):
    await bot.store.set(GUILD, "handoff_mode", "off")
    request_id = await request_at(bot, member, lead, pure.OPEN)
    row = await pure.get_request(bot.db, request_id)

    _embed, view = requests_cog.build_card(bot, bot.guild, row, lead)

    assert pure_handoff.SEND_TO_EVENTS not in [one.label for one in view.children]
    assert post_labels_of(requests_cog.post_view(bot, bot.guild, row)) == [
        "Pick up",
        "Hold",
        "Decline",
        pure.SITE_BUTTON,
    ]


def post_labels_of(view):
    return [] if view is None else [getattr(inner(one), "label", None) for one in view.children]


async def test_a_press_on_the_panel_card_draws_the_event_draft_over_the_panel(
    cog, bot, member, lead
):
    request_id = await request_at(bot, member, lead, pure.OPEN)
    panel = await open_panel(cog, bot, lead)
    select = next(item for item in panel_view(panel).children if isinstance(item, RequestPick))
    select._values = [str(request_id)]
    opened = await click(bot, lead, select)

    pressed = await click(bot, lead, handoff_button(card_view(opened)))

    assert card_embed(pressed).title == "Propose an event — draft"
    assert card_view(pressed).fields.from_request == request_id
    assert card_view(pressed).fields.requester_id == member.id
    assert pressed.response.messages[0]["deferred"] is True
    assert pressed.response.messages[0].get("thinking") is None


async def test_a_press_on_the_public_post_answers_in_a_new_ephemeral_and_never_edits_the_post(
    cog, bot, member, lead
):
    """The §F / front-door lesson: a component defer on a public message would edit the post."""
    bot.guard = FakeGuard()
    post = await posted(cog, bot, member)
    before = len(post.messages)

    pressed = await click(bot, lead, post_button(post.messages[0], pure_handoff.SEND_TO_EVENTS))

    deferred = pressed.response.messages[0]
    assert deferred["deferred"] is True
    assert deferred["ephemeral"] is True and deferred["thinking"] is True
    assert card_embed(pressed).title == "Propose an event — draft"
    assert len(post.messages) == before


async def test_a_member_pressing_send_to_events_is_told_which_role_it_needs(
    cog, bot, member, lead
):
    bot.guard = FakeGuard()
    post = await posted(cog, bot, member)

    pressed = await click(bot, member, post_button(post.messages[0], pure_handoff.SEND_TO_EVENTS))

    assert "staff" in pressed.sent.lower()
    assert pressed.response.messages[-1]["ephemeral"] is True


async def test_a_stale_press_after_the_key_went_off_refuses_in_words(cog, bot, member, lead):
    bot.guard = FakeGuard()
    post = await posted(cog, bot, member)
    button = post_button(post.messages[0], pure_handoff.SEND_TO_EVENTS)
    await bot.store.set(GUILD, "handoff_mode", "off")

    pressed = await click(bot, lead, button)

    assert "handoff_mode" in pressed.sent
    assert "A setting group" in pressed.sent


async def test_a_stale_press_on_a_request_that_has_been_decided_refuses_in_words(
    cog, bot, member, lead, db
):
    bot.guard = FakeGuard()
    post = await posted(cog, bot, member)
    button = post_button(post.messages[0], pure_handoff.SEND_TO_EVENTS)
    await requests_cog.apply_decision(bot, bot.guild, 1, pure.DECLINED, lead, reason="no")

    pressed = await click(bot, lead, button)

    assert "already **declined**" in pressed.sent
    assert (await pure.get_request(db, 1))["moved_to"] is None


async def test_a_press_on_a_request_that_is_gone_says_so_rather_than_raising(cog, bot, lead):
    interaction = FakeInteraction(bot, lead)

    await requests_cog.send_to_events(interaction, 999, on_post=True)

    assert "no request **#999**" in interaction.sent


async def test_the_send_to_button_rebuilds_itself_from_its_custom_id_after_a_restart(
    cog, bot, member, lead
):
    bot.guard = FakeGuard()
    await posted(cog, bot, member)
    custom_id = requests_cog.handoff_custom_id(1, pure_handoff.EVENT)
    match = re.fullmatch(requests_cog.HANDOFF_TEMPLATE, custom_id)
    assert match is not None

    fresh = await requests_cog.PostHandoffButton.from_custom_id(None, None, match)
    pressed = await click(bot, lead, fresh)

    assert fresh.request_id == 1 and fresh.action == pure_handoff.EVENT
    assert fresh.custom_id == custom_id
    assert card_embed(pressed).title == "Propose an event — draft"


async def test_the_move_template_never_answers_for_a_status_move_and_the_other_way_round():
    """Two dynamic templates share the `request:` idea; neither may swallow the other's press."""
    handoff_id = requests_cog.handoff_custom_id(12, pure_handoff.EVENT)
    move_id = pure.post_move_custom_id(12, "pickup")

    assert re.fullmatch(requests_cog.MOVE_TEMPLATE, handoff_id) is None
    assert re.fullmatch(requests_cog.HANDOFF_TEMPLATE, move_id) is None


# --- Open a ticket with them… — a conversation beside a request, never a move (§A) -------------


def fake_door(calls, *, ok=True, said="Opened."):
    async def open_a_ticket(bot, guild, user, **kwargs):
        from black_bloc.panels import Outcome, refusal

        calls.append({"user": user, **kwargs})
        return Outcome(True, said, value=77) if ok else refusal(said, "blocked", 409)

    return open_a_ticket


async def test_the_card_and_the_post_both_carry_open_a_ticket_with_them(cog, bot, member, lead):
    bot.guard = FakeGuard()
    post = await posted(cog, bot, member)
    row = await pure.get_request(bot.db, 1)

    _embed, card = requests_cog.build_card(bot, bot.guild, row, lead)

    assert pure_handoff.OPEN_A_TICKET in [one.label for one in card.children]
    assert pure_handoff.OPEN_A_TICKET in post_labels(post.messages[0])


async def test_the_door_quotes_the_request_and_ignores_the_hide_toggle(
    cog, bot, member, lead, db, monkeypatch
):
    """A hand-off is a staff decision, so `modmail_open_with_button` does not gate it (§A)."""
    calls = []
    monkeypatch.setattr(
        "black_bloc.cogs.moderation.modmail.open_a_ticket", fake_door(calls)
    )
    await bot.store.set(GUILD, "modmail_open_with_button", False)
    request_id = await request_at(bot, member, lead, pure.OPEN)
    panel = await open_panel(cog, bot, lead)
    select = next(item for item in panel_view(panel).children if isinstance(item, RequestPick))
    select._values = [str(request_id)]
    opened = await click(bot, lead, select)

    pressed = await click(bot, lead, handoff_button(card_view(opened), pure_handoff.OPEN_A_TICKET))

    assert len(calls) == 1
    asked = calls[0]
    assert asked["user"].id == member.id
    assert asked["source"] == "staff" and asked["check_toggle"] is False
    assert asked["subject"] == f"Request #{request_id}"
    assert "a request board" in asked["text"] and "because" in asked["text"]
    assert "Opened." in pressed.sent


async def test_the_door_leaves_the_request_exactly_where_it_was(
    cog, bot, member, lead, db, monkeypatch
):
    monkeypatch.setattr("black_bloc.cogs.moderation.modmail.open_a_ticket", fake_door([]))
    bot.guard = FakeGuard()
    post = await posted(cog, bot, member)

    await click(bot, lead, post_button(post.messages[0], pure_handoff.OPEN_A_TICKET))

    row = await pure.get_request(db, 1)
    assert row["status"] == pure.OPEN and row["moved_to"] is None


async def test_the_door_leaves_one_row_naming_the_request_and_the_ticket(
    cog, bot, member, lead, db, monkeypatch
):
    monkeypatch.setattr("black_bloc.cogs.moderation.modmail.open_a_ticket", fake_door([]))
    bot.guard = FakeGuard()
    post = await posted(cog, bot, member)

    await click(bot, lead, post_button(post.messages[0], pure_handoff.OPEN_A_TICKET))

    kinds = await action_kinds(db)
    assert kinds.count("handoff.request_to_ticket") == 1
    cur = await db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ?", ("handoff.request_to_ticket",)
    )
    details = json.loads((await cur.fetchone())["details"])
    assert (details["request_id"], details["ticket_id"]) == (1, 77)


async def test_a_door_that_refuses_says_so_and_leaves_no_hand_off_row(
    cog, bot, member, lead, db, monkeypatch
):
    monkeypatch.setattr(
        "black_bloc.cogs.moderation.modmail.open_a_ticket",
        fake_door([], ok=False, said="They are blocked."),
    )
    bot.guard = FakeGuard()
    post = await posted(cog, bot, member)

    pressed = await click(bot, lead, post_button(post.messages[0], pure_handoff.OPEN_A_TICKET))

    assert "They are blocked." in pressed.sent
    assert "handoff.request_to_ticket" not in await action_kinds(db)


async def test_a_requester_who_has_left_is_named_rather_than_crashed_into(
    cog, bot, lead, db, monkeypatch
):
    monkeypatch.setattr("black_bloc.cogs.moderation.modmail.open_a_ticket", fake_door([]))
    request_id = await pure.create_request(
        bot.db, GUILD, 4040, what="a board", why="because", due_on=None
    )
    interaction = FakeInteraction(bot, lead)

    await requests_cog.open_a_ticket_with_them(interaction, request_id, on_post=True)

    assert "not somebody Black Bloc can see" in interaction.sent
    assert "handoff.request_to_ticket" not in await action_kinds(db)
