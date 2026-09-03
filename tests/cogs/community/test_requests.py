import discord
import pytest

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
        self.kwargs = kwargs
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
        self.dms.append({"content": content, **kwargs})


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
        self._cog = None

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
    assert "#1" in interaction.sent and "staff will see it" in interaction.sent
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
    pure.REVIEW: ["Accept", "Send back", "Hold", "Decline"],
    pure.HOLD: ["Resume", "Decline"],
    pure.DONE: [],
    pure.DECLINED: [],
    pure.WITHDRAWN: [],
}


@pytest.mark.parametrize("status", pure.STATUSES)
async def test_the_card_renders_exactly_the_buttons_the_table_says(cog, bot, member, lead, status):
    request_id = await request_at(bot, member, lead, status)
    row = await pure.get_request(bot.db, request_id)

    embed, view = requests_cog.build_card(bot, bot.guild, row, lead)

    assert [item.label for item in view.children] == [*EXPECTED_BUTTONS[status], "Back"]
    if not EXPECTED_BUTTONS[status]:
        assert "finishes" in embed.footer.text


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

    await view.on_timeout()


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
