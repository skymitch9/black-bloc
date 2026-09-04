from __future__ import annotations

from types import SimpleNamespace

import discord
import pytest

from black_bloc import pings as helpers
from black_bloc.cogs.content.golive import set_link
from black_bloc.cogs.content.pings import (
    CARD_ROLE_GONE,
    DELETE_OFF,
    DELETE_ON,
    FOLLOW_PLACEHOLDER,
    GIVE_PLACEHOLDER,
    MAKE_THE_ROLE,
    NAMES_BUTTON,
    NOT_A_NUMBER,
    ROLE_PLACEHOLDER,
    SET_IT_UP,
    SITE_BUTTON,
    STREAMER_PLACEHOLDER,
    UNFOLLOW_PLACEHOLDER,
    ChoicePick,
    FollowPick,
    GivePick,
    NamesModal,
    Pings,
    RolePick,
    StreamerPick,
    build_card,
    build_panel,
    build_settings,
    build_streamers,
    run_own,
    run_settings,
)
from black_bloc.config import load_settings
from black_bloc.settings_store import DB_UNAVAILABLE, SettingsStore
from black_bloc.storage.db import Database

GUILD = 7
LOG_CHANNEL = 222
STREAMER = 900
FAN = 901
STAFF = 5
ORIGIN = "https://blackbloc.test"


class FakeRole:
    def __init__(self, role_id, name):
        self.id = role_id
        self.name = name
        self.members = []
        self.deleted = False

    def is_assignable(self):
        return True

    async def delete(self, reason=None):
        self.deleted = True


class FakeMember:
    def __init__(self, guild, user_id, display_name="Alice", staff=False):
        self.id = user_id
        self.guild = guild
        self.display_name = display_name
        self.name = display_name
        self.bot = False
        self.roles = []
        self.guild_permissions = discord.Permissions(manage_guild=staff)
        guild.members[user_id] = self

    async def add_roles(self, *roles, reason=None):
        self.roles += [role for role in roles if role not in self.roles]
        for role in roles:
            role.members.append(self)

    async def remove_roles(self, *roles, reason=None):
        self.roles = [role for role in self.roles if role not in roles]
        for role in roles:
            role.members = [one for one in role.members if one is not self]


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.roles = []
        self.members = {}
        self.made = []
        self.next_role_id = 1000

    def get_role(self, role_id):
        return next((role for role in self.roles if role.id == int(role_id)), None)

    def get_member(self, user_id):
        return self.members.get(int(user_id))

    def get_channel(self, channel_id):
        return None

    def add_role(self, role):
        self.roles.append(role)
        return role

    async def create_role(self, name=None, mentionable=False, reason=None):
        self.made.append(name)
        self.next_role_id += 1
        return self.add_role(FakeRole(self.next_role_id, name))


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guild = guild
        self.guilds = [guild]
        self.guard = None
        self.views = []

    def add_view(self, view, message_id=None):
        self.views.append((view, message_id))

    def get_channel(self, channel_id):
        return None

    def get_guild(self, guild_id):
        return self.guild if self.guild.id == guild_id else None


class FakeMessage:
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
    def __init__(self, bot, user, guild=True):
        self.client = bot
        self.user = user
        self.guild = bot.guild if guild else None
        self.guild_id = getattr(self.guild, "id", None)
        self.channel_id = LOG_CHANNEL
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)
        self.edits = []

    async def original_response(self):
        return FakeMessage(1)

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return FakeMessage(9500, **kwargs)

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
    def said(self):
        spoken = [
            one["content"] for one in self.response.messages if one.get("content") is not None
        ]
        return spoken[-1] if spoken else None


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "pc.sqlite3")
    await database.connect()
    try:
        yield database
    finally:
        await database.close()


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(
        _env_file=None, test_mode=True, test_channel_id=LOG_CHANNEL, origin=ORIGIN
    )
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOG_CHANNEL)
    await store.set(GUILD, "pings_mode", "on")
    return FakeBot(db, store, settings, FakeGuild())


@pytest.fixture
def cog(bot):
    return Pings(bot)


@pytest.fixture
def streamer(bot):
    return FakeMember(bot.guild, STREAMER, "SuperNamu")


@pytest.fixture
def fan(bot):
    return FakeMember(bot.guild, FAN, "Fan")


@pytest.fixture
def lead(bot):
    return FakeMember(bot.guild, STAFF, "Lead", staff=True)


def staff_is(bot, yes=True):
    bot.store.is_staff = lambda who: yes


def labels(view):
    return [one.label for one in view.children if getattr(one, "label", None)]


def placeholders(view):
    return [
        one.placeholder for one in view.children if getattr(one, "placeholder", None) is not None
    ]


def button(view, label):
    return next(one for one in view.children if getattr(one, "label", None) == label)


def picker(view, kind):
    return next(one for one in view.children if isinstance(one, kind))


async def a_fan_role(bot, member):
    outcome = await helpers.ensure_fan_role(bot, bot.guild, member, by=STAFF, staff=True)
    return bot.guild.get_role(outcome.role_id)


async def kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


# --- the command ---------------------------------------------------------------------------------


async def test_the_command_answers_one_ephemeral_panel_and_nothing_else(cog, bot, fan):
    staff_is(bot, False)
    interaction = FakeInteraction(bot, fan)

    await cog.pings_panel.callback(cog, interaction)

    assert len(interaction.response.messages) == 1
    said = interaction.response.messages[0]
    assert said["ephemeral"] is True
    assert said["embed"].title == helpers.PANEL_TITLE
    assert said["allowed_mentions"].to_dict() == discord.AllowedMentions.none().to_dict()


async def test_the_command_refuses_a_dm_in_words(cog, bot, fan):
    interaction = FakeInteraction(bot, fan, guild=False)

    await cog.pings_panel.callback(cog, interaction)

    assert "has to be run in the server itself" in interaction.said


async def test_the_command_refuses_while_the_database_is_down(cog, bot, fan, db):
    await db.close()
    interaction = FakeInteraction(bot, fan)

    await cog.pings_panel.callback(cog, interaction)

    assert interaction.said == DB_UNAVAILABLE


# --- what renders --------------------------------------------------------------------------------


async def test_a_member_sees_the_two_selects_and_none_of_the_staff_half(bot, streamer, fan):
    staff_is(bot, False)
    role = await a_fan_role(bot, streamer)
    await helpers.setup_events_role(bot, bot.guild, by=STAFF)
    await fan.add_roles(role)

    _embed, view = await build_panel(bot, bot.guild, fan)

    assert placeholders(view) == [FOLLOW_PLACEHOLDER, UNFOLLOW_PLACEHOLDER] or placeholders(
        view
    ) == [UNFOLLOW_PLACEHOLDER]
    assert "Streamers…" not in labels(view)
    assert "Settings" not in labels(view)
    assert "Logs" not in labels(view)
    assert SITE_BUTTON not in labels(view)


async def test_staff_see_every_staff_control_and_a_counts_line(bot, streamer, lead):
    staff_is(bot)
    await a_fan_role(bot, streamer)

    embed, view = await build_panel(bot, bot.guild, lead)

    assert "1** streamer(s)" in embed.description
    assert labels(view)[-5:] == [
        "Streamers…",
        "Set up the Events role",
        "Settings",
        "Logs",
        SITE_BUTTON,
    ]


async def test_staff_keep_their_half_with_the_mode_off(bot, lead):
    staff_is(bot)
    await bot.store.set(GUILD, "pings_mode", "off")

    embed, view = await build_panel(bot, bot.guild, lead)

    assert "**off**" in embed.description
    assert "Set up the Events role" in labels(view)
    assert "Settings" in labels(view)


async def test_no_origin_means_no_site_button_rather_than_a_link_that_goes_nowhere(bot, lead):
    staff_is(bot)
    bot.settings = SimpleNamespace(origin="")

    _embed, view = await build_panel(bot, bot.guild, lead)

    assert SITE_BUTTON not in labels(view)


async def test_the_site_link_is_staff_only_because_every_pings_route_is(bot, fan, streamer):
    staff_is(bot, False)
    await a_fan_role(bot, streamer)

    _embed, view = await build_panel(bot, bot.guild, fan)

    assert SITE_BUTTON not in labels(view)


@pytest.mark.parametrize("mode_on", [False, True])
@pytest.mark.parametrize("own_role", [False, True])
@pytest.mark.parametrize("creation", ["self", "staff"])
@pytest.mark.parametrize("streams", [False, True])
@pytest.mark.parametrize("events", ["unset", "gone", "worn", "not_worn"])
@pytest.mark.parametrize("staff", [False, True])
async def test_every_state_renders_exactly_its_row_of_the_button_table(
    bot, db, mode_on, own_role, creation, streams, events, staff
):
    """Checklist 3 and 12: the table is data, and no state may render a move it forbids."""
    staff_is(bot, staff)
    member = FakeMember(bot.guild, 4242, "Casey")
    await bot.store.set(GUILD, "pings_mode", "on" if mode_on else "off")
    await bot.store.set(GUILD, "pings_fan_role_creation", creation)
    if streams:
        await set_link(db, member.id, "casey", None)
    if own_role:
        await a_fan_role(bot, member)
    if events != "unset":
        await helpers.setup_events_role(bot, bot.guild, by=STAFF)
        role = bot.guild.get_role(bot.store.get(GUILD, "golive_ping_role_id"))
        if events == "gone":
            bot.guild.roles = [one for one in bot.guild.roles if one.id != role.id]
        if events == "worn":
            await member.add_roles(role)

    _embed, view = await build_panel(bot, bot.guild, member)

    state = helpers.panel_state(
        bot, bot.guild, member, await helpers.all_fan_roles(db, GUILD), streams=streams
    )
    wanted = [move.label for move in helpers.panel_buttons(state, staff=staff)]
    assert labels(view) == wanted + ([SITE_BUTTON] if staff else [])


async def test_one_events_toggle_while_the_two_feeds_agree(bot, fan):
    staff_is(bot, False)
    await helpers.setup_events_role(bot, bot.guild, by=STAFF)

    _embed, view = await build_panel(bot, bot.guild, fan)

    assert "Turn event pings on" in labels(view)
    assert "Turn go-live pings on" not in labels(view)


async def test_two_labelled_toggles_once_the_feeds_point_at_different_roles(bot, fan):
    """I2 (b): the button does what its label says, or there are two of them."""
    staff_is(bot, False)
    golive = bot.guild.add_role(FakeRole(71, "Go live"))
    events = bot.guild.add_role(FakeRole(72, "Events"))
    await bot.store.set(GUILD, "golive_ping_role_id", golive.id)
    await bot.store.set(GUILD, "events_ping_role_id", events.id)
    await fan.add_roles(golive)

    _embed, view = await build_panel(bot, bot.guild, fan)

    assert labels(view) == ["Turn go-live pings off", "Turn event pings on", "Refresh"]


async def test_take_my_ping_role_away_still_renders_when_only_staff_may_start_one(bot, streamer):
    """I1 (a): the access-REDUCING move is never hidden from the person who wears it."""
    staff_is(bot, False)
    await a_fan_role(bot, streamer)
    await bot.store.set(GUILD, "pings_fan_role_creation", "staff")

    _embed, view = await build_panel(bot, bot.guild, streamer)

    assert "Take my ping role away" in labels(view)
    assert "Start my own ping role" not in labels(view)


async def test_stop_following_renders_with_the_mode_off_and_follow_does_not(bot, streamer, fan):
    staff_is(bot, False)
    role = await a_fan_role(bot, streamer)
    await fan.add_roles(role)
    await bot.store.set(GUILD, "pings_mode", "off")

    _embed, view = await build_panel(bot, bot.guild, fan)

    assert placeholders(view) == [UNFOLLOW_PLACEHOLDER]


async def test_the_embed_says_why_there_is_no_fan_button(bot, fan):
    staff_is(bot, False)
    await bot.store.set(GUILD, "pings_fan_role_creation", "staff")

    embed, view = await build_panel(bot, bot.guild, fan)

    assert "Only staff start a streamer's ping role" in embed.description
    assert "Start my own ping role" not in labels(view)


async def test_a_member_who_never_streamed_is_told_how_to_link(bot, fan):
    staff_is(bot, False)

    embed, _view = await build_panel(bot, bot.guild, fan)

    assert "**Link my Twitch channel**" in embed.description
    assert "/twitch link" not in embed.description


async def test_the_panel_never_names_a_subcommand_that_is_gone(bot, streamer, lead):
    staff_is(bot)
    await a_fan_role(bot, streamer)
    await bot.store.set(GUILD, "pings_mode", "off")

    embed, _view = await build_panel(bot, bot.guild, lead)

    for dead in ("/pingroles", "/pings follow", "/pings events", "/pings fans", "/pings list"):
        assert dead not in embed.description


async def test_a_capped_select_names_the_streamer_pings_panels_not_the_site(bot, fan):
    staff_is(bot, False)
    for spot in range(30):
        await a_fan_role(bot, FakeMember(bot.guild, 5000 + spot, f"streamer{spot:02d}"))

    _embed, view = await build_panel(bot, bot.guild, fan)

    pick = picker(view, FollowPick)
    assert len(pick.options) == 25
    assert pick.placeholder == "25 of 30 — the rest are on the *Streamer pings* panels"
    assert "site" not in pick.placeholder


# --- the member moves ----------------------------------------------------------------------------


async def test_follow_puts_the_role_on_and_leaves_one_log_row(bot, streamer, fan, db):
    staff_is(bot, False)
    role = await a_fan_role(bot, streamer)
    _embed, view = await build_panel(bot, bot.guild, fan)
    pick = picker(view, FollowPick)
    pick._values = [str(STREAMER)]
    interaction = FakeInteraction(bot, fan)

    await pick.callback(interaction)

    assert fan.roles == [role]
    assert [one for one in await kinds(db) if one == "pings.follow"] == ["pings.follow"]
    assert "SuperNamu" in interaction.said
    assert interaction.edits, "the panel did not re-render"


async def test_unfollow_takes_it_off_even_with_the_mode_turned_off(bot, streamer, fan, db):
    staff_is(bot, False)
    role = await a_fan_role(bot, streamer)
    await fan.add_roles(role)
    await bot.store.set(GUILD, "pings_mode", "off")
    _embed, view = await build_panel(bot, bot.guild, fan)
    pick = picker(view, FollowPick)
    pick._values = [str(STREAMER)]
    interaction = FakeInteraction(bot, fan)

    await pick.callback(interaction)

    assert fan.roles == []
    assert [one for one in await kinds(db) if one == "pings.unfollow"] == ["pings.unfollow"]


async def test_a_stale_follow_select_refuses_in_words_and_writes_nothing(bot, streamer, fan, db):
    staff_is(bot, False)
    await a_fan_role(bot, streamer)
    _embed, view = await build_panel(bot, bot.guild, fan)
    pick = picker(view, FollowPick)
    pick._values = [str(STREAMER)]
    await helpers.remove_fan_role(bot, bot.guild, STREAMER, by=STAFF)
    before = len(await kinds(db))
    interaction = FakeInteraction(bot, fan)

    await pick.callback(interaction)

    assert "Press **Refresh**" in interaction.said
    assert len(await kinds(db)) == before


async def test_the_events_toggle_moves_the_role_both_ways(bot, fan, db):
    staff_is(bot, False)
    await helpers.setup_events_role(bot, bot.guild, by=STAFF)
    role = bot.guild.get_role(bot.store.get(GUILD, "golive_ping_role_id"))
    _embed, view = await build_panel(bot, bot.guild, fan)

    on = FakeInteraction(bot, fan)
    await button(view, "Turn event pings on").callback(on)
    assert fan.roles == [role]

    _embed, view = await build_panel(bot, bot.guild, fan)
    off = FakeInteraction(bot, fan)
    await button(view, "Turn them off").callback(off)

    assert fan.roles == []
    found = await kinds(db)
    assert found.count("pings.events_on") == 1 and found.count("pings.events_off") == 1


async def test_the_events_toggle_is_refused_while_the_mode_is_off(bot, fan, db):
    staff_is(bot, False)
    await helpers.setup_events_role(bot, bot.guild, by=STAFF)
    _embed, view = await build_panel(bot, bot.guild, fan)
    toggle = button(view, "Turn event pings on")
    await bot.store.set(GUILD, "pings_mode", "off")
    interaction = FakeInteraction(bot, fan)

    await toggle.callback(interaction)

    assert "turned off" in interaction.said and fan.roles == []


async def test_start_my_own_ping_role_makes_it_and_take_it_away_asks_first(bot, streamer, db):
    staff_is(bot, False)
    await set_link(db, STREAMER, "supernamu", None)
    _embed, view = await build_panel(bot, bot.guild, streamer)

    made = FakeInteraction(bot, streamer)
    await button(view, "Start my own ping role").callback(made)
    assert bot.guild.made == ["SuperNamu pings"]

    _embed, view = await build_panel(bot, bot.guild, streamer)
    asked = FakeInteraction(bot, streamer)
    await button(view, "Take my ping role away").callback(asked)
    assert "Are you sure?" in [field.name for field in asked.embed.fields]

    gone = FakeInteraction(bot, streamer)
    await button(asked.view, helpers.OWN_DROP_YES).callback(gone)
    assert await helpers.get_fan_role(db, GUILD, STREAMER) is None


async def test_keep_it_changes_nothing(bot, streamer, db):
    staff_is(bot, False)
    await a_fan_role(bot, streamer)
    _embed, view = await build_panel(bot, bot.guild, streamer)
    asked = FakeInteraction(bot, streamer)
    await button(view, "Take my ping role away").callback(asked)

    kept = FakeInteraction(bot, streamer)
    await button(asked.view, helpers.KEEP_IT).callback(kept)

    assert await helpers.get_fan_role(db, GUILD, STREAMER) is not None


async def test_start_my_own_refuses_somebody_black_bloc_never_saw_stream(bot, fan, db):
    staff_is(bot, False)
    interaction = FakeInteraction(bot, fan)

    await run_own(interaction, add=True)

    assert "**Link my Twitch channel**" in interaction.said
    assert await helpers.get_fan_role(db, GUILD, FAN) is None


async def test_every_click_answers_the_database_being_down_in_words(bot, fan, db):
    staff_is(bot, False)
    await helpers.setup_events_role(bot, bot.guild, by=STAFF)
    _embed, view = await build_panel(bot, bot.guild, fan)
    toggle = button(view, "Turn event pings on")
    await db.close()
    interaction = FakeInteraction(bot, fan)

    await toggle.callback(interaction)

    assert interaction.said == DB_UNAVAILABLE
    assert interaction.edits == []


# --- the staff half ------------------------------------------------------------------------------


async def test_streamers_lists_everybody_and_offers_the_two_ways_in(bot, streamer, lead):
    staff_is(bot)
    await a_fan_role(bot, streamer)

    embed, view = await build_streamers(bot, bot.guild)

    assert "SuperNamu pings" in embed.description
    assert "0 follower(s)" in embed.description
    assert placeholders(view) == [STREAMER_PLACEHOLDER, GIVE_PLACEHOLDER]


async def test_streamers_with_nobody_on_it_says_how_to_start_one(bot, lead):
    staff_is(bot)

    embed, view = await build_streamers(bot, bot.guild)

    assert "**Give somebody a ping role…**" in embed.description
    assert placeholders(view) == [GIVE_PLACEHOLDER]


async def test_picking_a_streamer_opens_their_card(bot, streamer, lead):
    staff_is(bot)
    await a_fan_role(bot, streamer)
    _embed, view = await build_streamers(bot, bot.guild)
    pick = picker(view, StreamerPick)
    pick._values = [str(STREAMER)]
    interaction = FakeInteraction(bot, lead)

    await pick.callback(interaction)

    assert "SuperNamu pings" in interaction.embed.description
    assert "Remove their ping role" in labels(interaction.view)


async def test_a_demoted_staffer_moves_nothing_on_the_streamers_panel(bot, streamer, lead):
    staff_is(bot)
    await a_fan_role(bot, streamer)
    _embed, view = await build_panel(bot, bot.guild, lead)
    staff_is(bot, False)
    interaction = FakeInteraction(bot, lead)

    await button(view, "Streamers…").callback(interaction)

    assert "staff only" in interaction.said
    assert interaction.edits == []


async def test_the_streamer_card_offers_make_the_role_again_only_when_it_is_gone(
    bot, streamer, lead
):
    staff_is(bot)
    role = await a_fan_role(bot, streamer)

    _embed, view = await build_card(bot, bot.guild, STREAMER)
    assert "Make the role again" not in labels(view)

    bot.guild.roles = [one for one in bot.guild.roles if one.id != role.id]
    embed, view = await build_card(bot, bot.guild, STREAMER)

    assert CARD_ROLE_GONE in embed.description
    assert "Make the role again" in labels(view)


async def test_make_the_role_again_repairs_a_row_staff_could_otherwise_only_delete(
    bot, streamer, lead, db
):
    staff_is(bot)
    role = await a_fan_role(bot, streamer)
    bot.guild.roles = [one for one in bot.guild.roles if one.id != role.id]
    _embed, view = await build_card(bot, bot.guild, STREAMER)
    interaction = FakeInteraction(bot, lead)

    await button(view, "Make the role again").callback(interaction)

    row = await helpers.get_fan_role(db, GUILD, STREAMER)
    assert row["role_id"] != role.id
    assert bot.guild.get_role(row["role_id"]) is not None


async def test_remove_their_ping_role_asks_first_and_then_removes(bot, streamer, lead, db):
    staff_is(bot)
    role = await a_fan_role(bot, streamer)
    _embed, view = await build_card(bot, bot.guild, STREAMER)

    asked = FakeInteraction(bot, lead)
    await button(view, "Remove their ping role").callback(asked)
    assert "Are you sure?" in [field.name for field in asked.embed.fields]

    gone = FakeInteraction(bot, lead)
    await button(asked.view, helpers.CARD_REMOVE_YES).callback(gone)

    assert await helpers.get_fan_role(db, GUILD, STREAMER) is None
    assert role.deleted is True


async def test_the_role_pick_step_writes_with_and_without_a_role_picked(bot, lead, db):
    staff_is(bot)
    _embed, view = await build_panel(bot, bot.guild, lead)

    opened = FakeInteraction(bot, lead)
    await button(view, "Set up the Events role").callback(opened)
    assert ROLE_PLACEHOLDER in placeholders(opened.view)

    empty = FakeInteraction(bot, lead)
    await button(opened.view, SET_IT_UP).callback(empty)
    assert bot.guild.made == ["Events"]
    first = bot.store.get(GUILD, "golive_ping_role_id")

    chosen = bot.guild.add_role(FakeRole(4242, "Announcements"))
    again = FakeInteraction(bot, lead)
    await button(view, "Set up the Events role").callback(again)
    again.view.picked_role_id = chosen.id
    done = FakeInteraction(bot, lead)
    await button(again.view, SET_IT_UP).callback(done)

    assert bot.store.get(GUILD, "golive_ping_role_id") == 4242 != first


async def test_giving_somebody_a_ping_role_goes_through_the_same_role_pick(bot, streamer, lead, db):
    staff_is(bot)
    _embed, view = await build_streamers(bot, bot.guild)
    pick = picker(view, GivePick)
    pick._values = [streamer]
    opened = FakeInteraction(bot, lead)

    await pick.callback(opened)
    assert isinstance(picker(opened.view, RolePick), RolePick)

    made = FakeInteraction(bot, lead)
    await button(opened.view, MAKE_THE_ROLE).callback(made)

    assert await helpers.get_fan_role(db, GUILD, STREAMER) is not None
    assert bot.guild.made == ["SuperNamu pings"]


async def test_an_empty_role_select_submit_clears_the_pick(bot, lead):
    staff_is(bot)
    _embed, view = await build_panel(bot, bot.guild, lead)
    opened = FakeInteraction(bot, lead)
    await button(view, "Set up the Events role").callback(opened)
    role_pick = picker(opened.view, RolePick)
    role_pick._values = []
    cleared = FakeInteraction(bot, lead)

    await role_pick.callback(cleared)

    assert cleared.view.picked_role_id is None
    assert "a fresh role is made" in cleared.embed.description


async def test_a_demoted_staffer_writes_nothing_from_the_role_pick_step(bot, lead):
    staff_is(bot)
    _embed, view = await build_panel(bot, bot.guild, lead)
    opened = FakeInteraction(bot, lead)
    await button(view, "Set up the Events role").callback(opened)
    staff_is(bot, False)
    interaction = FakeInteraction(bot, lead)

    await button(opened.view, SET_IT_UP).callback(interaction)

    assert "staff only" in interaction.said
    assert bot.guild.made == []


async def test_logs_answers_a_new_followup_and_leaves_the_panel_alone(bot, lead):
    staff_is(bot)
    _embed, view = await build_panel(bot, bot.guild, lead)
    interaction = FakeInteraction(bot, lead)

    await button(view, "Logs").callback(interaction)

    assert interaction.edits == []
    assert interaction.response.messages


async def test_logs_still_refuses_a_demoted_staffer(bot, lead):
    staff_is(bot)
    _embed, view = await build_panel(bot, bot.guild, lead)
    staff_is(bot, False)
    interaction = FakeInteraction(bot, lead)

    await button(view, "Logs").callback(interaction)

    assert "staff only" in interaction.said


# --- settings ------------------------------------------------------------------------------------


async def test_the_settings_panel_shows_every_pings_value(bot, lead):
    staff_is(bot)

    embed, view = build_settings(bot, bot.guild)

    assert "**mode** — on" in embed.description
    assert "**this panel stays live** — 10 minute(s)" in embed.description
    assert placeholders(view) == ["Mode…", "Who may start one…", "On unlink…"]
    assert NAMES_BUTTON in labels(view) and DELETE_ON in labels(view)


async def test_a_settings_select_writes_the_key_and_leaves_one_log_row(bot, lead, db):
    staff_is(bot)
    _embed, view = build_settings(bot, bot.guild)
    pick = next(one for one in view.children if isinstance(one, ChoicePick))
    pick._values = ["off"]
    interaction = FakeInteraction(bot, lead)

    await pick.callback(interaction)

    assert bot.store.get(GUILD, "pings_mode") == "off"
    assert (await kinds(db)).count("pings.settings") == 1


async def test_the_delete_toggle_flips_and_relabels(bot, lead):
    staff_is(bot)
    _embed, view = build_settings(bot, bot.guild)
    interaction = FakeInteraction(bot, lead)

    await button(view, DELETE_ON).callback(interaction)

    assert bot.store.get(GUILD, "pings_fan_role_delete") is False
    assert DELETE_OFF in labels(interaction.view)


async def test_the_names_modal_echoes_the_template_as_it_will_render(bot, lead):
    staff_is(bot)
    modal = NamesModal(bot, GUILD)
    modal.template._value = "fans of {name}!"
    modal.events_name._value = "Events"
    modal.stays._value = "12"
    interaction = FakeInteraction(bot, lead)

    await modal.on_submit(interaction)

    assert "fans of Lead!" in interaction.said
    assert bot.store.get(GUILD, "pings_panel_minutes") == 12


async def test_a_broken_template_is_saved_but_never_pretends_it_worked(bot, lead):
    staff_is(bot)
    modal = NamesModal(bot, GUILD)
    modal.template._value = "{game} pings"
    modal.events_name._value = "Events"
    modal.stays._value = "10"
    interaction = FakeInteraction(bot, lead)

    await modal.on_submit(interaction)

    assert "is not something Black Bloc can fill in" in interaction.said
    assert "Lead pings" in interaction.said


async def test_the_names_modal_refuses_a_minutes_box_that_is_not_a_number(bot, lead):
    staff_is(bot)
    modal = NamesModal(bot, GUILD)
    modal.template._value = "{name} pings"
    modal.events_name._value = "Events"
    modal.stays._value = "soon"
    interaction = FakeInteraction(bot, lead)

    await modal.on_submit(interaction)

    assert interaction.said == NOT_A_NUMBER.format(
        given="soon", label="Minutes this panel stays live"
    )
    assert bot.store.get(GUILD, "pings_events_role_name") == "Events"


async def test_a_demoted_staffer_saves_no_setting(bot, lead):
    staff_is(bot, False)
    interaction = FakeInteraction(bot, lead)

    await run_settings(interaction, {"pings_mode": "off"})

    assert bot.store.get(GUILD, "pings_mode") == "on"
    assert "staff only" in interaction.said


# --- lifetime ------------------------------------------------------------------------------------


async def test_the_panel_waits_for_the_minutes_the_setting_says(bot, fan):
    staff_is(bot, False)
    await bot.store.set(GUILD, "pings_panel_minutes", 3)

    _embed, view = await build_panel(bot, bot.guild, fan)

    assert view.timeout == 180


async def test_the_timeout_disables_every_item_and_says_so(bot, fan):
    staff_is(bot, False)
    embed, view = await build_panel(bot, bot.guild, fan)
    view.message = FakeMessage(1, embed=embed)

    await view.on_timeout()

    assert all(one.disabled for one in view.children)
    assert view.message.kwargs["embeds"][0].footer.text == helpers.PANEL_TIMEOUT_FOOTER


async def test_a_re_render_retires_the_view_it_replaced(bot, streamer, fan):
    staff_is(bot, False)
    await a_fan_role(bot, streamer)
    _embed, view = await build_panel(bot, bot.guild, fan)
    pick = picker(view, FollowPick)
    pick._values = [str(STREAMER)]
    interaction = FakeInteraction(bot, fan)

    await pick.callback(interaction)

    assert view.replaced is True
    assert interaction.view is not view
