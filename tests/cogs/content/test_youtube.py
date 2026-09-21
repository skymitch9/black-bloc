from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import discord
import pytest

from black_bloc.cogs.content import youtube as youtube_cog
from black_bloc.cogs.content.golive import GoLive
from black_bloc.cogs.content.youtube import (
    FEATURE_MISSING,
    LINK_LABEL,
    LIVE_MODE_PLACEHOLDER,
    NOT_LINKED,
    PICK_A_CHANNEL,
    SITE_BUTTON,
    LinkedPick,
    LinkModal,
    LiveModePick,
    WhoPick,
    YouTube,
    build_panel,
    counts,
    get_link,
    live_health,
    run_link,
    run_live_mode,
    set_link,
    set_live_mode,
    unlink_channel,
)
from black_bloc.config import load_settings
from black_bloc.golive import EMBED_NO_TITLE, EMBED_SOURCE_YOUTUBE
from black_bloc.logkinds import FEATURE_PAGES, is_important
from black_bloc.settings_store import DB_UNAVAILABLE, SettingsStore
from black_bloc.youtube import (
    CANNOT_RESOLVE,
    KEEP_IT,
    PANEL_TIMEOUT_FOOTER,
    PANEL_TITLE,
    UNLINK_QUESTION,
    UNLINK_YES,
    YouTubeError,
    card_buttons,
)
from black_bloc.youtube_live import UNREADABLE_EVERY_SECONDS, Confirm, read_page

CHANNEL = "UCsXVk37bltHxD1rDPwtNM8Q"
GUILD = 7
TEST_CHANNEL = 111
GOLIVE_CHANNEL = 222
OTHER_CHANNEL = 333
STREAMER = 900
FAN_ROLE = 4242
PING_ROLE = 5151


# --- the doubles -------------------------------------------------------------------------------


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id
        self.name = f"role-{role_id}"
        self.mention = f"<@&{role_id}>"


class FakeMessage:
    def __init__(self, message_id, **kwargs):
        self.id = message_id
        self.kwargs = kwargs

    async def edit(self, **kwargs):
        self.kwargs |= kwargs

    @property
    def embeds(self):
        held = self.kwargs.get("embeds")
        if held is not None:
            return list(held)
        one = self.kwargs.get("embed")
        return [one] if one is not None else []


class FakeChannel:
    def __init__(self, channel_id):
        self.id = channel_id
        self.mention = f"<#{channel_id}>"
        self.posts = []
        self.explode = None

    async def send(self, content=None, **kwargs):
        if self.explode is not None:
            raise self.explode
        self.posts.append({"content": content, **kwargs})
        return FakeMessage(9000 + len(self.posts))


class FakeMember:
    def __init__(self, guild, user_id=STREAMER, name="Casey"):
        self.id = user_id
        self.guild = guild
        self.display_name = name
        self.name = name.lower()
        self.mention = f"<@{user_id}>"
        self.bot = False
        self.roles = []
        self.dms = []
        self.dm_error = None
        guild.by_id[user_id] = self

    async def send(self, content=None, **kwargs):
        if self.dm_error is not None:
            raise self.dm_error
        self.dms.append({"content": content, **kwargs})
        return FakeMessage(len(self.dms))


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black Bloc"
        self.channels = {}
        self.by_id = {}
        self.chunked = True
        self.roles = [FakeRole(FAN_ROLE), FakeRole(PING_ROLE)]
        self.unavailable = False

    def add(self, channel):
        self.channels[channel.id] = channel
        return channel

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    @property
    def members(self):
        """A real guild hands the go-live boot sweep a list, so the fake does too."""
        return list(self.by_id.values())

    def get_member(self, user_id):
        return self.by_id.get(user_id)

    def get_role(self, role_id):
        return next((role for role in self.roles if role.id == role_id), None)


class FakeGuard:
    def __init__(self, allowed):
        self.allowed = allowed

    def allows_channel(self, channel_id):
        return int(channel_id) in self.allowed


class FakeBot:
    def __init__(self, db, store, guild, settings):
        self.db = db
        self.store = store
        self.guild = guild
        self.guilds = [guild]
        self.settings = settings
        self.guard = None
        self.cogs = {}

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def get_cog(self, name):
        return self.cogs.get(name)

    def get_user(self, user_id):
        return self.guild.get_member(user_id)


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
    def __init__(self, bot, user):
        self.client = bot
        self.user = user
        self.guild = bot.guild
        self.guild_id = bot.guild.id
        self.channel_id = TEST_CHANNEL
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
    def sent(self):
        said = [
            one["content"] for one in self.response.messages if one.get("content") is not None
        ]
        return said[-1] if said else None

    @property
    def ephemeral(self):
        return all(one["ephemeral"] for one in self.response.messages)


class _Client:
    """A stand-in YouTubeClient: answers `resolve` with whatever the test wants."""

    def __init__(self, *, keyed=False, resolves=None):
        self.keyed = keyed
        self.resolves = resolves
        self.asked: list[str] = []
        self.closed = False

    async def resolve(self, text):
        self.asked.append(str(text))
        if isinstance(self.resolves, Exception):
            raise self.resolves
        return self.resolves or (CHANNEL, "Kurzgesagt")

    async def close(self):
        self.closed = True


# --- fixtures ----------------------------------------------------------------------------------


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", TEST_CHANNEL)
    await store.set(GUILD, "golive_channel_id", GOLIVE_CHANNEL)
    guild = FakeGuild()
    for channel_id in (TEST_CHANNEL, GOLIVE_CHANNEL, OTHER_CHANNEL):
        guild.add(FakeChannel(channel_id))
    return FakeBot(db, store, guild, settings)


@pytest.fixture
def cog(bot):
    made = YouTube(bot)
    bot.cogs["YouTube"] = made
    return made


@pytest.fixture
def member(bot):
    return FakeMember(bot.guild)


async def kinds_logged(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def details_logged(db, kind):
    cur = await db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id", (kind,)
    )
    return [json.loads(row["details"]) for row in await cur.fetchall() if row["details"]]


async def linked(db, cog, client=None):
    await set_link(db, STREAMER, CHANNEL, None, "Kurzgesagt")
    if client is not None:
        cog.client = client
    return await get_link(db, STREAMER)


async def live_mode(bot, mode="on"):
    await bot.store.set(GUILD, "youtube_live_mode", mode)


# --- one channel, two members ------------------------------------------------------------------


async def test_a_channel_linked_twice_is_probed_once_and_warns(bot, cog, db, member, caplog):
    await set_link(db, STREAMER, CHANNEL, None, "Kurzgesagt")
    await set_link(db, STREAMER + 1, CHANNEL, None, "Kurzgesagt")

    rows = await cog._pollable()

    assert [row["channel_id"] for row in rows] == [CHANNEL]
    assert "linked to both" in caplog.text


# --- the panel: what renders ---------------------------------------------------------------------


def _staff(bot, yes=True):
    bot.store.is_staff = lambda who: yes


def labels(view):
    return [one.label for one in view.children if getattr(one, "label", None)]


def placeholders(view):
    return [
        one.placeholder for one in view.children if getattr(one, "placeholder", None) is not None
    ]


def button(view, label):
    return next(one for one in view.children if getattr(one, "label", None) == label)


async def test_the_command_answers_one_ephemeral_panel_and_nothing_else(bot, cog, db, member):
    interaction = FakeInteraction(bot, member)

    await cog.youtube.callback(cog, interaction)

    assert len(interaction.response.messages) == 1
    said = interaction.response.messages[0]
    assert said["ephemeral"] is True
    assert said["embed"].title == PANEL_TITLE
    assert said["allowed_mentions"].everyone is False


async def test_a_member_sees_their_own_card_and_none_of_the_staff_half(bot, cog, db, member):
    _staff(bot, False)
    await linked(db, cog)
    interaction = FakeInteraction(bot, member)

    embed, view = await build_panel(bot, bot.guild, member)

    assert "Kurzgesagt" in embed.description
    assert labels(view) == ["Relink…", "Unlink", "Refresh", SITE_BUTTON]
    assert placeholders(view) == []
    assert "last probe" not in embed.description
    assert interaction.response.messages == []


async def test_staff_see_the_health_lines_who_is_linked_and_every_staff_control(
    bot, cog, db, member
):
    _staff(bot)
    await linked(db, cog)

    embed, view = await build_panel(bot, bot.guild, member)

    assert "last probe" in embed.description
    assert "not set (the live page alone)" in embed.description
    assert "Kurzgesagt" in embed.description
    assert labels(view) == [
        "Relink…",
        "Unlink",
        "Refresh",
        "Link for somebody…",
        "Logs",
        SITE_BUTTON,
    ]
    assert placeholders(view) == [PICK_A_CHANNEL, LIVE_MODE_PLACEHOLDER]


async def test_a_member_is_never_told_who_else_has_a_channel_linked(bot, cog, db, member):
    _staff(bot, False)
    other = FakeMember(bot.guild, user_id=STREAMER + 1, name="Rivet")
    await set_link(db, other.id, CHANNEL, None, "Kurzgesagt")

    embed, _view = await build_panel(bot, bot.guild, member)

    assert "Rivet" not in embed.description
    assert "Kurzgesagt" not in embed.description


@pytest.mark.parametrize("mode", ["off", "shadow", "on"])
@pytest.mark.parametrize("is_linked", [False, True])
@pytest.mark.parametrize("staff", [False, True])
async def test_every_state_renders_exactly_its_row_of_the_button_table(
    bot, cog, db, member, mode, is_linked, staff
):
    """Checklist 3 and 12: the table is data, and no state may render a move it forbids."""
    _staff(bot, staff)
    await live_mode(bot, mode)
    if is_linked:
        await linked(db, cog)

    _embed, view = await build_panel(bot, bot.guild, member)

    wanted = [move.label for move in card_buttons(linked=is_linked, mine=True, staff=staff)]
    assert labels(view) == wanted + [SITE_BUTTON]


async def test_with_the_live_mode_off_the_embed_says_so_and_link_my_channel_still_renders(
    bot, cog, db, member
):
    _staff(bot, False)
    await live_mode(bot, "off")

    embed, view = await build_panel(bot, bot.guild, member)

    assert "**off**" in embed.description
    assert "Live streams are…" in embed.description
    assert "Link my channel" in labels(view)


async def test_the_off_line_never_tells_anybody_to_run_a_command_that_is_gone(
    bot, cog, db, member
):
    embed, _view = await build_panel(bot, bot.guild, member)

    assert "/uploads" not in embed.description
    assert "/youtube link" not in embed.description


async def test_the_panel_never_mentions_an_upload_any_more(bot, cog, db, member):
    _staff(bot)
    await linked(db, cog)

    embed, _view = await build_panel(bot, bot.guild, member)

    assert "upload" not in embed.description.lower()
    assert "Shorts" not in embed.description


async def test_no_origin_means_no_site_button_rather_than_a_link_that_goes_nowhere(
    bot, cog, db, member
):
    bot.settings = SimpleNamespace(origin="", youtube_api_key=None)

    _embed, view = await build_panel(bot, bot.guild, member)

    assert SITE_BUTTON not in labels(view)


async def test_the_picker_caps_at_twenty_five_and_the_placeholder_says_where_the_rest_are(
    bot, cog, db, member
):
    _staff(bot)
    for spot in range(30):
        await set_link(db, STREAMER + 10 + spot, f"UC{spot:022d}", None, f"channel {spot}")

    _embed, view = await build_panel(bot, bot.guild, member)

    pick = next(one for one in view.children if isinstance(one, LinkedPick))
    assert len(pick.options) == 25
    assert pick.placeholder == "25 of 30 — the rest are on the site"


# --- the panel: linking --------------------------------------------------------------------------


async def test_link_my_channel_opens_the_modal_and_a_relink_arrives_prefilled(
    bot, cog, db, member
):
    await linked(db, cog)
    _embed, view = await build_panel(bot, bot.guild, member)
    interaction = FakeInteraction(bot, member)

    await button(view, "Relink…").callback(interaction)

    modal = interaction.response.modals[0]
    assert isinstance(modal, LinkModal)
    assert modal.channel.default == CHANNEL
    assert modal.channel.label == LINK_LABEL


async def test_the_link_modal_refuses_to_open_while_the_database_is_down(bot, cog, db, member):
    _embed, view = await build_panel(bot, bot.guild, member)
    await db.close()
    interaction = FakeInteraction(bot, member)

    await button(view, "Link my channel").callback(interaction)

    assert interaction.response.modals == []
    assert interaction.sent == DB_UNAVAILABLE


async def test_linking_stores_the_channel_renders_the_card_and_leaves_one_row(
    bot, cog, db, member
):
    cog.client = _Client(resolves=(CHANNEL, "Kurzgesagt"))
    interaction = FakeInteraction(bot, member)

    await run_link(interaction, member, "@kurzgesagt", mine=True)

    assert (await get_link(db, STREAMER))["channel_id"] == CHANNEL
    assert "Kurzgesagt" in interaction.sent
    assert (await kinds_logged(db)).count("youtube.link") == 1
    assert "Kurzgesagt" in interaction.embed.description


async def test_linking_never_claims_anything_was_counted_as_seen(bot, cog, db, member):
    """Nothing reads the uploads feed any more, so nothing may say it was read."""
    cog.client = _Client(resolves=(CHANNEL, "Kurzgesagt"))
    interaction = FakeInteraction(bot, member)

    await run_link(interaction, member, CHANNEL, mine=True)

    assert "counted as seen" not in interaction.sent
    assert "upload" not in interaction.sent.lower()


async def test_linking_says_out_loud_that_live_announcements_are_off(bot, cog, db, member):
    cog.client = _Client(resolves=(CHANNEL, "Kurzgesagt"))
    interaction = FakeInteraction(bot, member)

    await run_link(interaction, member, CHANNEL, mine=True)

    assert "off" in interaction.sent
    assert "Live streams are…" in interaction.sent


async def test_the_two_ways_a_link_can_fail_each_get_their_own_sentence(
    bot, cog, db, member
):
    cog.client = _Client(resolves=YouTubeError(CANNOT_RESOLVE.format(given="nonsense")))
    bad = FakeInteraction(bot, member)
    await run_link(bad, member, "nonsense", mine=True)

    await set_link(db, STREAMER + 1, CHANNEL, None, "Kurzgesagt")
    cog.client = _Client(resolves=(CHANNEL, "Kurzgesagt"))
    taken = FakeInteraction(bot, member)
    await run_link(taken, member, CHANNEL, mine=True)

    assert "could not turn" in bad.sent
    assert "already linked to another member" in taken.sent
    assert bad.sent != taken.sent
    assert await get_link(db, STREAMER) is None


async def test_a_bad_paste_and_an_outage_are_told_apart_on_the_row_not_by_the_message(
    bot, cog, db, member
):
    cog.client = _Client(resolves=YouTubeError("nope"))
    await run_link(FakeInteraction(bot, member), member, "nonsense", mine=True)
    cog.client = _Client(resolves=YouTubeError("down", network=True))
    await run_link(FakeInteraction(bot, member), member, "nonsense", mine=True)

    rows = await details_logged(db, "youtube.resolve_failed")
    assert [row["network"] for row in rows] == [False, True]


async def test_a_channel_somebody_else_owns_leaves_no_row_and_changes_nothing(
    bot, cog, db, member
):
    """Checklist 16: two members must not silently claim one external identity."""
    await set_link(db, STREAMER + 1, CHANNEL, None, "Kurzgesagt")
    cog.client = _Client(resolves=(CHANNEL, "Kurzgesagt"))
    interaction = FakeInteraction(bot, member)

    await run_link(interaction, member, CHANNEL, mine=True)

    assert "ask a Lead" in interaction.sent
    assert await get_link(db, STREAMER) is None


# --- the panel: unlinking ------------------------------------------------------------------------


async def test_unlink_asks_first_and_keeping_it_changes_nothing(bot, cog, db, member):
    await linked(db, cog)
    _embed, view = await build_panel(bot, bot.guild, member)
    asking = FakeInteraction(bot, member)

    await button(view, "Unlink").callback(asking)

    assert UNLINK_QUESTION in [field.value for field in asking.embed.fields]
    keeping = FakeInteraction(bot, member)
    await button(asking.view, KEEP_IT).callback(keeping)
    assert await get_link(db, STREAMER) is not None


async def test_saying_yes_forgets_the_channel_and_puts_the_link_button_back(
    bot, cog, db, member
):
    await linked(db, cog)
    _embed, view = await build_panel(bot, bot.guild, member)
    asking = FakeInteraction(bot, member)
    await button(view, "Unlink").callback(asking)
    confirming = FakeInteraction(bot, member)

    await button(asking.view, UNLINK_YES).callback(confirming)

    assert await get_link(db, STREAMER) is None
    assert (await kinds_logged(db)).count("youtube.unlink") == 1
    assert "Link my channel" in labels(confirming.view)


async def test_unlinking_yourself_is_never_dmed(bot, cog, db, member):
    await linked(db, cog)
    member.dms = []

    await unlink_channel(bot, bot.guild, member, member)

    assert member.dms == []


async def test_unlink_without_a_link_says_so_without_naming_a_retired_command(
    bot, cog, db, member
):
    said, _row = await unlink_channel(bot, bot.guild, member, member)

    assert said == NOT_LINKED
    assert "/youtube link" not in said


# --- the panel: the staff half -------------------------------------------------------------------


async def test_picking_somebody_opens_their_card_with_the_staff_moves_only(
    bot, cog, db, member
):
    _staff(bot)
    other = FakeMember(bot.guild, user_id=STREAMER + 1, name="Rivet")
    await set_link(db, other.id, CHANNEL, None, "Kurzgesagt")
    _embed, view = await build_panel(bot, bot.guild, member)
    pick = next(one for one in view.children if isinstance(one, LinkedPick))
    pick._values = [str(other.id)]
    interaction = FakeInteraction(bot, member)

    await pick.callback(interaction)

    assert "Rivet" in interaction.embed.description
    assert labels(interaction.view) == [
        "Relink for…",
        "Unlink for",
        "Refresh",
        "Back",
        SITE_BUTTON,
    ]


async def test_link_for_somebody_draws_the_member_picker_only_after_it_is_asked_for(
    bot, cog, db, member
):
    _staff(bot)
    _embed, view = await build_panel(bot, bot.guild, member)
    assert not any(isinstance(one, WhoPick) for one in view.children)
    interaction = FakeInteraction(bot, member)

    await button(view, "Link for somebody…").callback(interaction)

    assert any(isinstance(one, WhoPick) for one in interaction.view.children)


async def test_linking_for_somebody_stores_it_and_names_them(bot, cog, db, member):
    _staff(bot)
    other = FakeMember(bot.guild, user_id=STREAMER + 1, name="Rivet")
    cog.client = _Client(resolves=(CHANNEL, "Kurzgesagt"))
    interaction = FakeInteraction(bot, member)

    await run_link(interaction, other, CHANNEL, mine=False)

    assert (await get_link(db, other.id))["channel_id"] == CHANNEL
    assert "Rivet" in interaction.sent
    assert (await kinds_logged(db)).count("youtube.link") == 1


async def test_unlink_for_dms_the_member_the_reason_and_leaves_one_row(bot, cog, db, member):
    _staff(bot)
    other = FakeMember(bot.guild, user_id=STREAMER + 1, name="Rivet")
    await set_link(db, other.id, CHANNEL, None, "Kurzgesagt")

    said, _row = await unlink_channel(bot, bot.guild, member, other, note="wrong channel")

    assert "Rivet" in said
    assert len(other.dms) == 1
    assert "wrong channel" in other.dms[0]["content"]
    assert (await kinds_logged(db)).count("youtube.unlink") == 1


async def test_the_dm_is_a_setting_and_off_means_off(bot, cog, db, member):
    _staff(bot)
    await bot.store.set(GUILD, "youtube_unlink_dms_them", False)
    other = FakeMember(bot.guild, user_id=STREAMER + 1, name="Rivet")
    await set_link(db, other.id, CHANNEL, None, "Kurzgesagt")

    await unlink_channel(bot, bot.guild, member, other, note="wrong channel")

    assert other.dms == []
    assert (await kinds_logged(db)).count("youtube.unlink") == 1


async def test_a_dm_that_cannot_be_delivered_is_a_detail_never_a_second_row(
    bot, cog, db, member
):
    """Checklist 34: one move leaves one row, whatever else went wrong along the way."""
    _staff(bot)
    other = FakeMember(bot.guild, user_id=STREAMER + 1, name="Rivet")
    other.dm_error = RuntimeError("dms are closed")
    await set_link(db, other.id, CHANNEL, None, "Kurzgesagt")

    await unlink_channel(bot, bot.guild, member, other, note="wrong channel")

    assert (await kinds_logged(db)).count("youtube.unlink") == 1
    assert (await details_logged(db, "youtube.unlink"))[0]["dm_failed"] is True


async def test_unlink_for_somebody_with_no_link_says_so_and_writes_nothing(
    bot, cog, db, member
):
    _staff(bot)
    other = FakeMember(bot.guild, user_id=STREAMER + 1, name="Rivet")

    said, _row = await unlink_channel(bot, bot.guild, member, other)

    assert "has no YouTube channel linked" in said
    assert await kinds_logged(db) == []


# --- the panel: staff, logs and the database -----------------------------------------------------


async def test_logs_answers_a_new_message_and_leaves_the_panel_where_it_was(
    bot, cog, db, member
):
    _staff(bot)
    _embed, view = await build_panel(bot, bot.guild, member)
    interaction = FakeInteraction(bot, member)

    await button(view, "Logs").callback(interaction)

    assert interaction.edits == []
    assert interaction.response.messages
    assert interaction.ephemeral


async def test_logs_still_refuses_a_staffer_who_was_demoted_since_the_panel_opened(
    bot, cog, db, member
):
    _staff(bot)
    _embed, view = await build_panel(bot, bot.guild, member)
    _staff(bot, False)
    interaction = FakeInteraction(bot, member)

    await button(view, "Logs").callback(interaction)

    assert "staff only" in interaction.sent


@pytest.mark.parametrize("label", ["Link for somebody…"])
async def test_a_staffer_demoted_while_the_panel_is_open_moves_nothing(
    bot, cog, db, member, label
):
    _staff(bot)
    _embed, view = await build_panel(bot, bot.guild, member)
    _staff(bot, False)
    interaction = FakeInteraction(bot, member)

    await button(view, label).callback(interaction)

    assert "staff only" in interaction.sent
    assert interaction.edits == []


async def test_the_mode_select_re_asks_whether_the_clicker_is_still_staff(bot, cog, db, member):
    _staff(bot)
    _embed, view = await build_panel(bot, bot.guild, member)
    pick = next(one for one in view.children if isinstance(one, LiveModePick))
    pick._values = ["on"]
    _staff(bot, False)
    interaction = FakeInteraction(bot, member)

    await pick.callback(interaction)

    assert bot.store.get(GUILD, "youtube_live_mode") == "off"
    assert "staff only" in interaction.sent


async def test_every_click_re_checks_the_database_after_it_has_deferred(bot, cog, db, member):
    _embed, view = await build_panel(bot, bot.guild, member)
    await db.close()
    interaction = FakeInteraction(bot, member)

    await button(view, "Refresh").callback(interaction)

    assert interaction.sent == DB_UNAVAILABLE
    assert interaction.edits == []


async def test_the_command_refuses_in_words_while_the_database_is_down(bot, cog, db, member):
    await db.close()
    interaction = FakeInteraction(bot, member)

    await cog.youtube.callback(cog, interaction)

    assert interaction.sent == DB_UNAVAILABLE


# --- the panel: the view's own life ---------------------------------------------------------------


async def test_a_re_render_retires_the_view_it_replaced(bot, cog, db, member):
    _embed, first = await build_panel(bot, bot.guild, member)
    interaction = FakeInteraction(bot, member)

    await button(first, "Refresh").callback(interaction)

    assert first.replaced is True
    assert first.is_finished() is True
    assert interaction.view is not first


async def test_a_timeout_disables_every_control_and_says_the_panel_went_quiet(
    bot, cog, db, member
):
    _embed, view = await build_panel(bot, bot.guild, member)
    view.message = FakeMessage(1, embed=discord.Embed(title=PANEL_TITLE, description="x"))

    await view.on_timeout()

    assert all(one.disabled for one in view.children)
    assert view.message.embeds[0].footer.text == PANEL_TIMEOUT_FOOTER
    assert "/youtube" in PANEL_TIMEOUT_FOOTER


async def test_the_panel_minutes_key_is_what_the_view_waits_for(bot, cog, db, member):
    await bot.store.set(GUILD, "youtube_panel_minutes", 4)

    _embed, view = await build_panel(bot, bot.guild, member)

    assert view.timeout == 240


# --- the store helpers ----------------------------------------------------------------------------


async def test_counts_are_read_off_the_table_not_kept_in_memory(bot, cog, db, member):
    await linked(db, cog)

    assert await counts(db) == {"links": 1}


async def test_closing_the_cog_closes_the_client_session(bot, cog):
    cog.client = _Client()

    await cog.cog_unload()

    assert cog.client.closed is True


async def test_the_cog_has_no_uploads_sweep_left_on_it(bot, cog):
    """The poll loop, its health and its counters went with the uploads half."""
    for name in ("poller", "poll_once", "link_and_seed", "last_poll_ok_at", "fetches"):
        assert not hasattr(cog, name), name
    assert cog.loop_health("poller") == (None, None)


def test_the_site_link_is_the_shared_one_and_no_origin_is_still_an_empty_string():
    """The cog kept its own copy; the page it names now has one home, in `logkinds`."""
    assert youtube_cog.site_page_url("https://example.test/") == (
        f"https://example.test/{FEATURE_PAGES[youtube_cog.FEATURE]}"
    )
    assert youtube_cog.site_page_url("") == ""
    assert youtube_cog.site_page_url(None) == ""


# --- the live probe: youtube-live-design.md §A–§E ------------------------------------------------


LIVE_PAGE = (Path(__file__).resolve().parents[2] / "fixtures" / "youtube_live_page.html").read_text(
    encoding="utf-8"
)
OFFLINE_PAGE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "youtube_not_live_page.html"
).read_text(encoding="utf-8")
UPCOMING_PAGE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "youtube_upcoming_page.html"
).read_text(encoding="utf-8")
LIVE_VIDEO = "3PFJ9SETS4M"
LIVE_WATCH = f"https://www.youtube.com/watch?v={LIVE_VIDEO}"
UNREADABLE_PAGE = "<html><body>maintenance</body></html>"
BOTCHECK_LIVE_PAGE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "youtube_botcheck_live_page.html"
).read_text(encoding="utf-8")
BOTCHECK_OFFLINE_PAGE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "youtube_botcheck_offline_page.html"
).read_text(encoding="utf-8")
SEARCHED_VIDEO = "ZZZZZZZZZZZ"
CHANNEL_LIVE_URL = f"https://www.youtube.com/channel/{CHANNEL}/live"


class _Live:
    """A stand-in YouTubeClient for the probe: canned pages, canned confirms, nothing fetched."""

    def __init__(self, *pages, keyed=False, confirms=None, searches=None):
        self.pages = list(pages)
        self.keyed = keyed
        self.confirms = list(confirms or [])
        self.searches = list(searches or [])
        self.probed = []
        self.confirmed = []
        self.searched = []
        self.closed = False

    async def probe_live(self, channel_id):
        self.probed.append(channel_id)
        reply = self.pages.pop(0) if self.pages else OFFLINE_PAGE
        if isinstance(reply, Exception):
            raise reply
        return read_page(reply)

    async def confirm_live(self, video_id):
        self.confirmed.append(video_id)
        reply = self.confirms.pop(0) if self.confirms else None
        if isinstance(reply, Exception):
            raise reply
        return reply

    async def search_live(self, channel_id):
        self.searched.append(channel_id)
        reply = self.searches.pop(0) if self.searches else None
        if isinstance(reply, Exception):
            raise reply
        return reply

    async def fetch_feed(self, channel_id, etag=None):
        return (200, None, [])

    async def classify(self, video_ids):
        return {}

    async def close(self):
        self.closed = True


@pytest.fixture
def golive(bot):
    made = GoLive(bot)
    bot.cogs["GoLive"] = made
    return made


async def live_on(bot, mode="on", golive_mode="on"):
    await bot.store.set(GUILD, "youtube_live_mode", mode)
    await bot.store.set(GUILD, "golive_mode", golive_mode)


async def live_linked(db, cog, *pages, keyed=False, confirms=None, searches=None):
    await set_link(db, STREAMER, CHANNEL, None, "Kurzgesagt")
    await db.conn.execute("UPDATE youtube_links SET seeded = 1 WHERE user_id = ?", (STREAMER,))
    await db.conn.commit()
    cog.client = _Live(*pages, keyed=keyed, confirms=confirms, searches=searches)
    return cog.client


async def sessions(db):
    cur = await db.conn.execute("SELECT * FROM golive_sessions ORDER BY id")
    return list(await cur.fetchall())


async def test_a_linked_channel_going_live_is_announced_once_through_the_go_live_path(
    bot, cog, golive, db, member
):
    await live_on(bot)
    await live_linked(db, cog, LIVE_PAGE)

    await cog.probe_all()

    rows = await sessions(db)
    assert len(rows) == 1
    assert rows[0]["source"] == "youtube" and rows[0]["platform"] == "YouTube"
    assert rows[0]["url"] == LIVE_WATCH
    posts = bot.guild.get_channel(GOLIVE_CHANNEL).posts
    assert len(posts) == 1 and LIVE_WATCH in posts[0]["content"]
    assert (await details_logged(db, "golive.announce"))[0]["source"] == "youtube"


async def test_a_channel_live_across_a_reboot_is_announced_by_the_first_probe(
    bot, cog, golive, db, member
):
    """Row 2 of `info/golive-boot-sweep-design.md` §A: the probe is what catches a YouTube
    stream that was already running while the bot was down — the presence sweep never sees it."""
    await live_on(bot)
    await live_linked(db, cog, LIVE_PAGE)

    await golive.cog_load()
    try:
        await cog.probe_all()
    finally:
        await golive.cog_unload()

    rows = await sessions(db)
    assert len(rows) == 1 and rows[0]["source"] == "youtube" and rows[0]["ended_at"] is None
    posts = bot.guild.get_channel(GOLIVE_CHANNEL).posts
    assert len(posts) == 1 and LIVE_WATCH in posts[0]["content"]
    swept = await details_logged(db, "golive.boot_swept")
    assert len(swept) == 1 and swept[0]["presence_found"] == 0


async def test_a_second_probe_while_the_stream_is_live_announces_nothing_more(
    bot, cog, golive, db, member
):
    await live_on(bot)
    await live_linked(db, cog, LIVE_PAGE, LIVE_PAGE, LIVE_PAGE)

    await cog.probe_all()
    await cog.probe_all()
    await cog.probe_all()

    assert len(await sessions(db)) == 1
    assert len(bot.guild.get_channel(GOLIVE_CHANNEL).posts) == 1


async def test_one_quiet_probe_does_not_end_a_stream_and_two_do(bot, cog, golive, db, member):
    await live_on(bot)
    await live_linked(db, cog, LIVE_PAGE, OFFLINE_PAGE, OFFLINE_PAGE)

    await cog.probe_all()
    await cog.probe_all()
    assert (await sessions(db))[0]["ended_at"] is None

    await cog.probe_all()

    assert (await sessions(db))[0]["ended_at"] is not None
    assert "golive.end" in await kinds_logged(db)


async def test_how_many_quiet_probes_end_a_stream_is_a_setting(bot, cog, golive, db, member):
    await live_on(bot)
    await bot.store.set(GUILD, "youtube_live_end_misses", 1)
    await live_linked(db, cog, LIVE_PAGE, OFFLINE_PAGE)

    await cog.probe_all()
    await cog.probe_all()

    assert (await sessions(db))[0]["ended_at"] is not None


async def test_without_a_key_nothing_is_confirmed_and_the_card_title_is_live_now(
    bot, cog, golive, db, member
):
    await live_on(bot)
    client = await live_linked(db, cog, LIVE_PAGE, keyed=False)

    await cog.probe_all()

    assert client.confirmed == []
    assert (await sessions(db))[0]["title"] is None
    embed = bot.guild.get_channel(GOLIVE_CHANNEL).posts[0]["embed"]
    assert embed.title == EMBED_NO_TITLE
    assert embed.footer.text.endswith(EMBED_SOURCE_YOUTUBE)
    assert cog.confirms == 0


async def test_with_a_key_one_unit_is_spent_and_the_card_carries_the_real_title(
    bot, cog, golive, db, member
):
    await live_on(bot)
    client = await live_linked(
        db,
        cog,
        LIVE_PAGE,
        keyed=True,
        confirms=[Confirm(started=True, title="lofi radio", thumbnail="https://i/x.jpg")],
    )

    await cog.probe_all()

    assert client.confirmed == [LIVE_VIDEO]
    assert cog.confirms == 1
    assert (await sessions(db))[0]["title"] == "lofi radio"
    assert bot.guild.get_channel(GOLIVE_CHANNEL).posts[0]["embed"].title == "lofi radio"


async def test_a_broadcast_the_api_says_has_already_ended_is_not_announced(
    bot, cog, golive, db, member
):
    await live_on(bot)
    await live_linked(
        db, cog, LIVE_PAGE, keyed=True, confirms=[Confirm(started=True, ended=True)]
    )

    await cog.probe_all()

    assert await sessions(db) == []
    assert bot.guild.get_channel(GOLIVE_CHANNEL).posts == []


async def test_a_confirm_that_refuses_is_said_out_loud_and_the_stream_is_still_announced(
    bot, cog, golive, db, member
):
    """Checklist 10: a check that could not run is named, never quietly claimed."""
    await live_on(bot)
    await live_linked(
        db, cog, LIVE_PAGE, keyed=True, confirms=[YouTubeError("quota exceeded", network=True)]
    )

    await cog.probe_all()

    assert "youtube.live_confirm_failed" in await kinds_logged(db)
    assert len(await sessions(db)) == 1
    assert (await details_logged(db, "youtube.live_seen"))[0]["confirmed"] is False


async def test_with_the_live_half_off_nothing_is_probed_at_all(bot, cog, golive, db, member):
    await live_on(bot, mode="off")
    client = await live_linked(db, cog, LIVE_PAGE)

    await cog.probe_all()

    assert client.probed == []
    assert await sessions(db) == []


async def test_in_shadow_the_go_live_path_still_runs_and_the_probe_row_is_a_would_row(
    bot, cog, golive, db, member
):
    """C: youtube_live_mode shadows its OWN row; golive_mode decides whether anything posts."""
    await live_on(bot, mode="shadow", golive_mode="shadow")
    await live_linked(db, cog, LIVE_PAGE)

    await cog.probe_all()

    kinds = await kinds_logged(db)
    assert "youtube.would_live_seen" in kinds and "youtube.live_seen" not in kinds
    assert "golive.would_announce" in kinds
    assert len(await sessions(db)) == 1
    assert bot.guild.get_channel(GOLIVE_CHANNEL).posts == []


async def test_an_upcoming_stream_is_not_announced(bot, cog, golive, db, member):
    await live_on(bot)
    await live_linked(db, cog, UPCOMING_PAGE)

    await cog.probe_all()

    assert await sessions(db) == []


async def test_a_page_that_changed_shape_says_so_once_an_hour_and_never_raises(
    bot, cog, golive, db, member
):
    await live_on(bot)
    await live_linked(db, cog, UNREADABLE_PAGE, UNREADABLE_PAGE)

    await cog.probe_all()
    await cog.probe_all()

    assert (await kinds_logged(db)).count("youtube.probe_unreadable") == 1
    assert await sessions(db) == []
    assert is_important("youtube.probe_unreadable")


async def test_an_unreadable_page_says_so_again_once_the_hour_is_up(bot, cog, golive, db, member):
    await live_on(bot)
    await live_linked(db, cog, UNREADABLE_PAGE, UNREADABLE_PAGE)

    await cog.probe_all()
    cog.unreadable_at[CHANNEL] = datetime.now(UTC) - timedelta(
        seconds=UNREADABLE_EVERY_SECONDS + 1
    )
    await cog.probe_all()

    assert (await kinds_logged(db)).count("youtube.probe_unreadable") == 2


async def test_a_probe_that_cannot_be_reached_is_not_a_quiet_probe(bot, cog, golive, db, member):
    """A hiccup is not an ending: an unreachable page leaves the session exactly as it was."""
    await live_on(bot)
    await live_linked(
        db,
        cog,
        LIVE_PAGE,
        YouTubeError("youtube unreachable", network=True),
        YouTubeError("youtube unreachable", network=True),
        YouTubeError("youtube unreachable", network=True),
    )

    for _ in range(4):
        await cog.probe_all()

    assert (await sessions(db))[0]["ended_at"] is None
    assert cog.last_probe_error == "youtube unreachable"


async def test_the_go_live_cog_missing_is_a_failure_row_not_a_silent_skip(bot, cog, db, member):
    await live_on(bot)
    await live_linked(db, cog, LIVE_PAGE)

    await cog.probe_all()

    assert "youtube.live_announce_failed" in await kinds_logged(db)
    assert await sessions(db) == []


async def test_the_probe_gap_follows_the_setting(bot, cog):
    await bot.store.set(GUILD, "youtube_live_poll_minutes", 30)

    cog._retime_live()

    assert cog.live_poller.minutes == 30


async def test_closing_the_cog_stops_the_live_probe(bot, cog):
    cog.client = _Live()

    await cog.cog_unload()

    assert cog.live_poller.is_running() is False


async def test_the_live_probe_reports_its_own_health(bot, cog, golive, db, member):
    await live_on(bot)
    await live_linked(db, cog, LIVE_PAGE)

    await cog.probe_all()
    health = await live_health(bot, bot.guild)

    assert health["mode"] == "on" and health["probed"] == 1 and health["open"] == 1
    assert health["last_probe_at"] and health["last_probe_error"] is None


async def test_the_health_lines_answer_even_with_the_cog_unloaded(bot, db):
    found = await live_health(bot, bot.guild)

    assert found["mode"] == "off" and found["last_probe_error"] == FEATURE_MISSING


async def test_the_staff_panel_says_what_the_live_probe_is_doing(bot, cog, golive, db, member):
    await live_on(bot)
    await live_linked(db, cog, LIVE_PAGE)
    _staff(bot)

    embed, view = await build_panel(bot, bot.guild, member)

    assert "**live streams** — on" in embed.description
    assert "**last probe** — never" in embed.description
    assert any(isinstance(one, LiveModePick) for one in view.children)


async def test_the_live_mode_select_writes_the_key_and_leaves_one_row(bot, cog, db, member):
    _staff(bot)
    interaction = FakeInteraction(bot, member)

    await run_live_mode(interaction, "shadow")

    assert bot.store.get(GUILD, "youtube_live_mode") == "shadow"
    assert (await kinds_logged(db)).count("youtube.live_mode") == 1
    assert "**shadow**" in interaction.sent


async def test_switching_the_live_half_on_says_when_go_live_would_not_post(bot, cog, db, member):
    await bot.store.set(GUILD, "golive_mode", "shadow")

    said, _row = await set_live_mode(bot, bot.guild, member, "on")

    assert "shadow" in said and "golive_mode" in said


async def test_go_lives_reconcile_asks_youtube_before_closing_a_youtube_session(
    bot, cog, golive, db, member
):
    """Checklist 4: a deploy inside a stream must not strand the session or re-announce it."""
    await live_on(bot)
    await live_linked(db, cog, LIVE_PAGE, LIVE_PAGE)
    await cog.probe_all()

    await golive.reconcile_open_sessions()
    assert (await sessions(db))[0]["ended_at"] is None

    cog.client = _Live(OFFLINE_PAGE)
    await golive.reconcile_open_sessions()

    assert (await sessions(db))[0]["ended_at"] is not None


async def test_an_unanswerable_probe_leaves_a_session_open_on_reconcile(
    bot, cog, golive, db, member
):
    await live_on(bot)
    await live_linked(db, cog, LIVE_PAGE)
    await cog.probe_all()
    cog.client = _Live(YouTubeError("youtube unreachable", network=True))

    await golive.reconcile_open_sessions()

    assert (await sessions(db))[0]["ended_at"] is None


async def test_a_member_nobody_can_see_is_not_probed(bot, cog, db):
    await live_on(bot)
    client = await live_linked(db, cog, LIVE_PAGE)

    await cog.probe_all()

    assert client.probed == []


# --- the datacenter bot-check page: live, id unknown (KI-30) --------------------------------------


async def test_a_live_channel_behind_the_bot_check_wall_is_announced_with_the_searched_id(
    bot, cog, golive, db, member
):
    """The page says live and carries no canonical link, so one 100-unit search finds the id."""
    await live_on(bot)
    client = await live_linked(
        db,
        cog,
        BOTCHECK_LIVE_PAGE,
        keyed=True,
        searches=[SEARCHED_VIDEO],
        confirms=[Confirm(started=True, title="the stream")],
    )

    await cog.probe_all()

    assert client.searched == [CHANNEL] and client.confirmed == [SEARCHED_VIDEO]
    rows = await sessions(db)
    assert len(rows) == 1
    assert rows[0]["url"] == f"https://www.youtube.com/watch?v={SEARCHED_VIDEO}"
    assert rows[0]["title"] == "the stream"
    searched = (await details_logged(db, "youtube.live_id_searched"))[0]
    assert searched["channel_id"] == CHANNEL and searched["units"] == 100
    assert searched["video_id"] == SEARCHED_VIDEO
    seen = (await details_logged(db, "youtube.live_seen"))[0]
    assert seen["video_id"] == SEARCHED_VIDEO and seen["botcheck"] is True


async def test_the_search_is_one_per_broadcast_and_not_one_per_probe(bot, cog, golive, db, member):
    await live_on(bot)
    client = await live_linked(
        db,
        cog,
        BOTCHECK_LIVE_PAGE,
        BOTCHECK_LIVE_PAGE,
        BOTCHECK_LIVE_PAGE,
        keyed=True,
        searches=[SEARCHED_VIDEO],
        confirms=[Confirm(started=True)],
    )

    await cog.probe_all()
    await cog.probe_all()
    await cog.probe_all()

    assert client.searched == [CHANNEL]
    assert len(await sessions(db)) == 1
    assert len(bot.guild.get_channel(GOLIVE_CHANNEL).posts) == 1


async def test_one_stream_spotted_behind_the_wall_costs_a_hundred_and_one_units(
    bot, cog, golive, db, member
):
    await live_on(bot)
    await live_linked(
        db,
        cog,
        BOTCHECK_LIVE_PAGE,
        BOTCHECK_LIVE_PAGE,
        keyed=True,
        searches=[SEARCHED_VIDEO],
        confirms=[Confirm(started=True)],
    )

    await cog.probe_all()
    await cog.probe_all()

    assert cog.confirms == 101


async def test_without_a_key_the_wall_is_announced_as_the_channels_own_live_page(
    bot, cog, golive, db, member
):
    await live_on(bot)
    client = await live_linked(db, cog, BOTCHECK_LIVE_PAGE, keyed=False)

    await cog.probe_all()

    assert client.searched == [] and client.confirmed == []
    assert cog.confirms == 0
    rows = await sessions(db)
    assert len(rows) == 1 and rows[0]["url"] == CHANNEL_LIVE_URL
    embed = bot.guild.get_channel(GOLIVE_CHANNEL).posts[0]["embed"]
    assert embed.title == EMBED_NO_TITLE
    assert embed.url == CHANNEL_LIVE_URL
    assert embed.image.url is None
    assert (await details_logged(db, "youtube.live_seen"))[0]["video_id"] is None


async def test_a_search_that_refuses_still_announces_the_stream_and_says_so(
    bot, cog, golive, db, member
):
    """Checklist 10: the id could not be read AND could not be searched — never silence."""
    await live_on(bot)
    await live_linked(
        db,
        cog,
        BOTCHECK_LIVE_PAGE,
        keyed=True,
        searches=[YouTubeError("quota exceeded", network=True)],
    )

    await cog.probe_all()

    kinds = await kinds_logged(db)
    assert "youtube.live_search_failed" in kinds and is_important("youtube.live_search_failed")
    assert (await sessions(db))[0]["url"] == CHANNEL_LIVE_URL


async def test_the_same_wall_for_an_offline_channel_is_a_quiet_probe(bot, cog, golive, db, member):
    await live_on(bot)
    client = await live_linked(
        db, cog, BOTCHECK_OFFLINE_PAGE, BOTCHECK_OFFLINE_PAGE, keyed=True
    )

    await cog.probe_all()
    await cog.probe_all()

    assert await sessions(db) == []
    assert client.searched == [] and cog.confirms == 0
    assert "youtube.probe_unreadable" not in await kinds_logged(db)


async def test_a_stream_behind_the_wall_ends_on_quiet_probes_exactly_as_any_other(
    bot, cog, golive, db, member
):
    await live_on(bot)
    await live_linked(
        db,
        cog,
        BOTCHECK_LIVE_PAGE,
        BOTCHECK_OFFLINE_PAGE,
        BOTCHECK_OFFLINE_PAGE,
        keyed=True,
        searches=[SEARCHED_VIDEO],
        confirms=[Confirm(started=True)],
    )

    await cog.probe_all()
    await cog.probe_all()
    assert (await sessions(db))[0]["ended_at"] is None

    await cog.probe_all()

    assert (await sessions(db))[0]["ended_at"] is not None


async def test_the_reconcile_reads_the_wall_as_live_rather_than_closing_the_session(
    bot, cog, golive, db, member
):
    await live_on(bot)
    await live_linked(db, cog, LIVE_PAGE)
    await cog.probe_all()
    cog.client = _Live(BOTCHECK_LIVE_PAGE)

    await golive.reconcile_open_sessions()

    assert (await sessions(db))[0]["ended_at"] is None


async def test_the_health_reading_says_the_last_probe_met_the_bot_check(
    bot, cog, golive, db, member
):
    await live_on(bot)
    await live_linked(db, cog, BOTCHECK_OFFLINE_PAGE, OFFLINE_PAGE, keyed=True)
    assert (await live_health(bot, bot.guild))["botcheck"] is False

    await cog.probe_all()
    assert (await live_health(bot, bot.guild))["botcheck"] is True

    await cog.probe_all()
    assert (await live_health(bot, bot.guild))["botcheck"] is False


async def test_the_staff_panel_says_when_a_probe_was_served_the_bot_check(
    bot, cog, golive, db, member
):
    await live_on(bot)
    await live_linked(db, cog, BOTCHECK_OFFLINE_PAGE, keyed=True)
    await cog.probe_all()
    _staff(bot)

    embed, _view = await build_panel(bot, bot.guild, member)

    assert "**bot check** — yes" in embed.description


# --- a probe that reads live while another source's session is open (the silent path) -------------


async def open_twitch_session(db):
    await db.conn.execute(
        "INSERT INTO golive_sessions(guild_id, user_id, source, platform, started_at, mode) "
        "VALUES (?, ?, 'twitch', 'Twitch', '2026-09-17T18:00:00+00:00', 'on')",
        (GUILD, STREAMER),
    )
    await db.conn.commit()


async def no_costreaming(bot):
    await bot.store.set(GUILD, "golive_costream_mode", "off")


async def test_a_stream_read_live_while_their_twitch_session_is_open_leaves_a_row_saying_so(
    bot, cog, golive, db, member
):
    """The probe worked; the one-announcement-per-person rule is why nothing was posted."""
    await live_on(bot)
    await no_costreaming(bot)
    await open_twitch_session(db)
    client = await live_linked(db, cog, BOTCHECK_LIVE_PAGE, keyed=True)

    await cog.probe_all()

    seen = await details_logged(db, "youtube.live_seen")
    assert len(seen) == 1
    assert seen[0]["announced"] is False
    assert seen[0]["because"] == "open_session:twitch"
    assert seen[0]["channel_id"] == CHANNEL and seen[0]["video_id"] is None
    assert seen[0]["botcheck"] is True and seen[0]["mode"] == "on"
    assert client.searched == [] and client.confirmed == [] and cog.confirms == 0
    assert len(await sessions(db)) == 1
    assert bot.guild.get_channel(GOLIVE_CHANNEL).posts == []
    assert "golive.announce" not in await kinds_logged(db)


async def test_that_row_is_written_once_per_stream_and_not_once_per_probe(
    bot, cog, golive, db, member
):
    await live_on(bot)
    await no_costreaming(bot)
    await open_twitch_session(db)
    await live_linked(
        db, cog, BOTCHECK_LIVE_PAGE, BOTCHECK_LIVE_PAGE, BOTCHECK_LIVE_PAGE, keyed=True
    )

    await cog.probe_all()
    await cog.probe_all()
    await cog.probe_all()

    assert len(await details_logged(db, "youtube.live_seen")) == 1


async def test_the_row_shadows_with_the_live_half_exactly_as_the_announcing_one_does(
    bot, cog, golive, db, member
):
    await live_on(bot, mode="shadow")
    await no_costreaming(bot)
    await open_twitch_session(db)
    await live_linked(db, cog, BOTCHECK_LIVE_PAGE, keyed=True)

    await cog.probe_all()

    assert await details_logged(db, "youtube.live_seen") == []
    would = await details_logged(db, "youtube.would_live_seen")
    assert len(would) == 1 and would[0]["because"] == "open_session:twitch"
    assert would[0]["announced"] is False and would[0]["mode"] == "shadow"


async def test_the_announcing_row_says_it_announced_and_gives_no_reason_not_to(
    bot, cog, golive, db, member
):
    await live_on(bot)
    await live_linked(db, cog, LIVE_PAGE)

    await cog.probe_all()

    seen = (await details_logged(db, "youtube.live_seen"))[0]
    assert seen["announced"] is True and "because" not in seen
    assert seen["video_id"] == LIVE_VIDEO and seen["url"] == LIVE_WATCH


async def test_the_health_counts_the_channels_the_probe_reads_as_live_right_now(
    bot, cog, golive, db, member
):
    """`live_now` counts YouTube-source sessions only, so a silent probe needs its own number."""
    await live_on(bot)
    await open_twitch_session(db)
    await live_linked(db, cog, BOTCHECK_LIVE_PAGE, OFFLINE_PAGE, OFFLINE_PAGE, keyed=True)
    assert (await live_health(bot, bot.guild))["reading_live"] == 0

    await cog.probe_all()

    health = await live_health(bot, bot.guild)
    assert health["reading_live"] == 1
    assert health["reading_live_channels"] == [CHANNEL]
    assert health["open"] == 0

    await cog.probe_all()
    assert (await live_health(bot, bot.guild))["reading_live"] == 1

    await cog.probe_all()
    assert (await live_health(bot, bot.guild))["reading_live"] == 0


async def test_the_staff_panel_says_how_many_channels_read_as_live(bot, cog, golive, db, member):
    await live_on(bot)
    await open_twitch_session(db)
    await live_linked(db, cog, BOTCHECK_LIVE_PAGE, keyed=True)
    await cog.probe_all()
    _staff(bot)

    embed, _view = await build_panel(bot, bot.guild, member)

    assert "**reading live now** — 1" in embed.description


# --- a probe that reads live while a Twitch session is open, with co-streaming on ----------------


async def test_a_second_platform_joins_the_open_session_instead_of_being_held_back(
    bot, cog, golive, db, member
):
    """`golive_costream_mode` on: the hand-off is `add_platform`, and the row says why."""
    await live_on(bot)
    await open_twitch_session(db)
    await live_linked(db, cog, BOTCHECK_LIVE_PAGE, keyed=True)

    await cog.probe_all()

    seen = await details_logged(db, "youtube.live_seen")
    assert len(seen) == 1
    assert seen[0]["announced"] is True and seen[0]["because"] == "joined_session"
    rows = await sessions(db)
    assert len(rows) == 1
    assert rows[0]["source"] == "twitch" and rows[0]["also_source"] == "youtube"
    assert rows[0]["also_platform"] == "YouTube" and rows[0]["ended_at"] is None
    assert "golive.announce" not in await kinds_logged(db)
    assert "golive.costream_added" in await kinds_logged(db)
    assert bot.guild.get_channel(GOLIVE_CHANNEL).posts == []


async def test_a_missing_go_live_cog_cannot_add_a_platform_and_says_so(
    bot, cog, golive, db, member
):
    await live_on(bot)
    await open_twitch_session(db)
    await live_linked(db, cog, BOTCHECK_LIVE_PAGE, keyed=True)
    bot.cogs.pop("GoLive")

    await cog.probe_all()

    failed = await details_logged(db, "youtube.live_announce_failed")
    assert len(failed) == 1 and failed[0]["reason"] == "golive_cog_missing"
    assert (await sessions(db))[0]["also_source"] is None


# --- the sweep walks channel rows too --------------------------------------------------------
# docs/info/channel-streamers-design.md §A: a streamer with no member is still a streamer, so a
# channel row with a youtube_channel_id is probed beside the member links.


async def a_channel_row(bot, *, youtube=CHANNEL, spotlight=False, announce=True):
    from black_bloc.cogs.content.spotlight import spotlight_channel, update_channel

    outcome, row = await spotlight_channel(
        bot, bot.guild, None, "gamesdonequick", keep=True, spotlight=spotlight
    )
    assert outcome == "added"
    await update_channel(
        bot.db,
        row["id"],
        youtube_channel_id=youtube,
        announce=1 if announce else 0,
    )
    from black_bloc.cogs.content.spotlight import channel_by_id

    return await channel_by_id(bot.db, row["id"])


def a_spotlight_cog(bot):
    from black_bloc.cogs.content.spotlight import Spotlight

    made = Spotlight(bot)
    bot.cogs["Spotlight"] = made
    return made


async def channel_sessions(db):
    cur = await db.conn.execute("SELECT * FROM spotlight_sessions ORDER BY id")
    return list(await cur.fetchall())


async def test_the_sweep_probes_a_channel_row_and_announces_it_once(bot, cog, db):
    await live_on(bot)
    a_spotlight_cog(bot)
    await bot.store.set(GUILD, "spotlight_mode", "on")
    row = await a_channel_row(bot)
    cog.client = _Live(LIVE_PAGE)

    await cog.probe_all()

    assert cog.client.probed == [CHANNEL]
    open_rows = await channel_sessions(db)
    assert len(open_rows) == 1 and open_rows[0]["spotlight_id"] == row["id"]
    assert open_rows[0]["url"] == LIVE_WATCH
    posts = bot.guild.get_channel(GOLIVE_CHANNEL).posts
    assert len(posts) == 1 and LIVE_WATCH in posts[0]["content"]


async def test_a_channel_row_with_no_youtube_channel_is_not_probed(bot, cog, db):
    await live_on(bot)
    a_spotlight_cog(bot)
    await a_channel_row(bot, youtube=None)
    cog.client = _Live(LIVE_PAGE)

    await cog.probe_all()

    assert cog.client.probed == []


async def test_an_opted_out_channel_row_is_probed_but_never_announced(bot, cog, db):
    await live_on(bot)
    a_spotlight_cog(bot)
    await bot.store.set(GUILD, "spotlight_mode", "on")
    await a_channel_row(bot, announce=False)
    cog.client = _Live(LIVE_PAGE)

    await cog.probe_all()

    assert await channel_sessions(db) == []
    assert bot.guild.get_channel(GOLIVE_CHANNEL).posts == []


async def test_a_channel_already_live_on_twitch_joins_rather_than_announcing_twice(bot, cog, db):
    from black_bloc.golive import StreamInfo

    await live_on(bot)
    spot = a_spotlight_cog(bot)
    await bot.store.set(GUILD, "spotlight_mode", "on")
    row = await a_channel_row(bot)
    await spot.announce_info(
        bot.guild,
        row,
        StreamInfo(url="https://www.twitch.tv/gamesdonequick", platform="Twitch"),
        "GamesDoneQuick",
    )
    before = len(bot.guild.get_channel(GOLIVE_CHANNEL).posts)
    cog.client = _Live(LIVE_PAGE)

    await cog.probe_all()

    assert len(await channel_sessions(db)) == 1
    assert len(bot.guild.get_channel(GOLIVE_CHANNEL).posts) == before
    said = [one for one in await details_logged(db, "youtube.live_seen") if "because" in one]
    assert said and said[-1]["announced"] is False


async def test_the_youtube_side_ends_the_session_it_opened(bot, cog, db):
    await live_on(bot)
    a_spotlight_cog(bot)
    await bot.store.set(GUILD, "spotlight_mode", "on")
    await bot.store.set(GUILD, "youtube_live_end_misses", 1)
    row = await a_channel_row(bot)
    cog.client = _Live(LIVE_PAGE, OFFLINE_PAGE, OFFLINE_PAGE)

    await cog.probe_all()
    assert len(await channel_sessions(db)) == 1
    await cog.probe_all()
    await cog.probe_all()

    rows = await channel_sessions(db)
    assert rows[0]["ended_at"] is not None
    assert row is not None
