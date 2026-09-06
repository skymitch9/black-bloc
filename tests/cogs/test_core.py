import json
from types import SimpleNamespace

import discord
import pytest
from discord import app_commands

from black_bloc import settings_panel as sp
from black_bloc.bot import COGS, BlackBlocBot
from black_bloc.cogs import core as core_cog
from black_bloc.cogs.core import Core, clear_key, help_lines, set_key, tree_commands
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore, require_staff
from black_bloc.storage.db import Database

GUILD = 7
TEST_CHANNEL = 111
LOG_CHANNEL = 222
STAFF_ROLE = 555
CAKE_ROLE = 777


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id
        self.name = f"role-{role_id}"
        self.mention = f"<@&{role_id}>"


class FakePerms:
    def __init__(self, manage_guild=False, view_channel=None):
        self.manage_guild = manage_guild
        self.view_channel = view_channel


class FakeChannel:
    def __init__(self, channel_id):
        self.id = channel_id
        self.name = f"channel-{channel_id}"
        self.mention = f"<#{channel_id}>"
        self.messages = []
        self.visible_to = set()
        self.deleted = []

    def permissions_for(self, role):
        return FakePerms(view_channel=role.id in self.visible_to)

    async def send(self, content=None, **kwargs):
        self.messages.append(
            SimpleNamespace(id=9000 + len(self.messages), content=content, kwargs=kwargs)
        )
        return self.messages[-1]

    async def delete_messages(self, messages):
        self.deleted += [one.id for one in messages]


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black Bloc"
        self.channels = {}
        self.members = {}
        self.roles = []
        self.default_role = FakeRole(GUILD)

    def add(self, channel):
        self.channels[channel.id] = channel
        return channel

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_member(self, user_id):
        return self.members.get(user_id)


class FakeMember:
    def __init__(self, guild, user_id=900, manage_guild=False):
        self.id = user_id
        self.guild = guild
        self.display_name = "Lead"
        self.name = "lead"
        self.mention = f"<@{user_id}>"
        self.roles = []
        self.guild_permissions = FakePerms(manage_guild=manage_guild)
        guild.members[user_id] = self


class FakePresence:
    def __init__(self, last_ok=None, last_error=None):
        self.last_ok = last_ok
        self.last_error = last_error
        self.applied = 0

    def loop_health(self, name):
        return (self.last_ok, self.last_error)

    async def apply_status(self):
        self.applied += 1
        return "watching 5 people"


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guild = guild
        self.guilds = [guild]
        self.guard = None
        self.cogs_by_name = {}

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def get_cog(self, name):
        return self.cogs_by_name.get(name)


class FakeMessage:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.embeds = list(kwargs.get("embeds") or ())


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.modals = []
        self.deferred = False

    def is_done(self):
        return self.deferred or bool(self.messages)

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def send_modal(self, modal):
        self.modals.append(modal)
        self.deferred = True

    async def defer(self, ephemeral=False):
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
        self.guild_id = bot.guild.id if guild else None
        self.channel_id = TEST_CHANNEL
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)
        self.edits = []

    async def original_response(self):
        return FakeMessage()

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return FakeMessage(**kwargs)

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
        return self.embed.description if self.embed is not None else ""

    @property
    def sent(self):
        spoken = [
            one["content"] for one in self.response.messages if one.get("content") is not None
        ]
        return spoken[-1] if spoken else None


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "core.sqlite3")
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
    guild = FakeGuild()
    guild.add(FakeChannel(TEST_CHANNEL))
    guild.add(FakeChannel(LOG_CHANNEL))
    return FakeBot(db, store, settings, guild)


@pytest.fixture
def cog(bot):
    return Core(bot)


@pytest.fixture
def member(bot):
    return FakeMember(bot.guild)


@pytest.fixture
def lead(bot):
    found = FakeMember(bot.guild, user_id=1, manage_guild=True)
    return found


def give_staff(bot, member):
    role = FakeRole(STAFF_ROLE)
    bot.guild.roles.append(role)
    bot.guild.get_channel(TEST_CHANNEL).visible_to.add(STAFF_ROLE)
    member.roles.append(role)


def take_staff(bot, member):
    bot.guild.get_channel(TEST_CHANNEL).visible_to.discard(STAFF_ROLE)
    member.roles.clear()
    member.guild_permissions = FakePerms(manage_guild=False)


async def kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def details(db):
    cur = await db.conn.execute("SELECT details FROM action_log ORDER BY id")
    return [json.loads(row["details"]) if row["details"] else None for row in await cur.fetchall()]


def labels(view):
    return [getattr(item, "label", None) for item in view.children]


def placeholders(view):
    return [getattr(item, "placeholder", None) for item in view.children]


def button(view, label):
    for item in view.children:
        if getattr(item, "label", None) == label:
            return item
    raise AssertionError(f"no button labelled {label!r} in {labels(view)}")


def picker(view, placeholder):
    for item in view.children:
        if getattr(item, "placeholder", None) == placeholder:
            return item
    raise AssertionError(f"no select placeheld {placeholder!r} in {placeholders(view)}")


def has_button(view, label):
    return any(getattr(item, "label", None) == label for item in view.children)


async def choose(item, interaction, values):
    """`values` is filled from Discord's payload, so a test fills the same private list."""
    item._values = list(values)
    await item.callback(interaction)


def ticked(item):
    return [one.id for one in item._underlying.default_values]


async def all_features_on(store):
    from black_bloc.command_visibility import HIDDEN_WHEN_OFF

    for key in HIDDEN_WHEN_OFF:
        await store.set(GUILD, key, "on")


async def open_panel(cog, bot, who):
    interaction = FakeInteraction(bot, who)
    await cog.settings.callback(cog, interaction)
    return interaction


async def press(view, label, bot, who):
    interaction = FakeInteraction(bot, who)
    await button(view, label).callback(interaction)
    return interaction


# --- the command itself ---------------------------------------------------------------------------


async def test_settings_opens_one_ephemeral_panel_naming_no_retired_subcommand(bot, cog, lead):
    interaction = await open_panel(cog, bot, lead)

    assert len(interaction.response.messages) == 1
    assert interaction.rendered["ephemeral"] is True
    assert interaction.embed.title == sp.PANEL_TITLE
    said = interaction.said
    assert "/settings show" not in said and "/settings set-value" not in said
    assert "`/youtube` to change" in said
    assert "A setting group…" in placeholders(interaction.view)


async def test_settings_is_staff_only_and_opens_nothing_for_a_member(bot, cog, member):
    interaction = await open_panel(cog, bot, member)

    assert "staff only" in interaction.sent
    assert interaction.view is None


async def test_settings_says_so_in_a_dm_rather_than_opening_a_panel(bot, cog, lead):
    interaction = FakeInteraction(bot, lead, guild=False)

    await cog.settings.callback(cog, interaction)

    assert "run in the server itself" in interaction.sent


async def test_settings_will_not_open_while_the_database_is_down(bot, cog, lead, db):
    await db.close()

    interaction = await open_panel(cog, bot, lead)

    assert "cannot reach its own database" in interaction.sent
    assert interaction.view is None
    await db.connect()


async def test_the_root_reads_every_feature_mode_and_never_offers_to_change_one(bot, cog, lead):
    await bot.store.set(GUILD, "youtube_mode", "shadow")

    interaction = await open_panel(cog, bot, lead)

    assert "**YouTube uploads** — shadow · `/youtube` to change" in interaction.said
    assert "**Modmail** — not answering DMs · `/modmail` to change" in interaction.said
    assert not any("mode" in str(one).lower() for one in placeholders(interaction.view))


async def test_the_site_link_is_drawn_only_when_the_bot_knows_its_own_origin(bot, cog, lead):
    with_site = await open_panel(cog, bot, lead)
    assert button(with_site.view, "Open on the site").url.endswith("/settings.html")

    bot.settings = bot.settings.model_copy(update={"site_origin": ""})
    without = await open_panel(cog, bot, lead)

    assert not has_button(without.view, "Open on the site")


# --- S2 / S3, the four core channel keys ---------------------------------------------------------


async def test_roles_and_channels_is_not_drawn_without_manage_server_and_the_embed_says_so(
    bot, cog, member
):
    give_staff(bot, member)

    interaction = await open_panel(cog, bot, member)

    assert not has_button(interaction.view, "Roles & channels…")
    assert sp.CORE_KEYS_ARE_FOR_A_LEAD in interaction.said


async def test_a_lead_gets_roles_and_channels_and_the_card_names_each_key_in_words(bot, cog, lead):
    root = await open_panel(cog, bot, lead)

    opened = await press(root.view, "Roles & channels…", bot, lead)

    assert "staff_channel_id" not in opened.said
    assert "Where staff talk — and who counts as staff" in opened.said
    assert "Where staff talk — and who counts as staff" in placeholders(opened.view)


async def test_plain_staff_can_reach_the_core_keys_once_the_switch_says_they_may(bot, cog, member):
    give_staff(bot, member)
    await bot.store.set(GUILD, sp.CORE_KEYS_ADMIN_ONLY_KEY, False)

    interaction = await open_panel(cog, bot, member)

    assert has_button(interaction.view, "Roles & channels…")
    assert sp.CORE_KEYS_ARE_FOR_A_LEAD not in interaction.said


async def test_a_lead_demoted_while_the_core_card_is_open_moves_nothing(bot, cog, lead, db):
    root = await open_panel(cog, bot, lead)
    card = await press(root.view, "Roles & channels…", bot, lead)
    pick = picker(card.view, "Where staff talk — and who counts as staff")
    lead.guild_permissions = FakePerms(manage_guild=False)
    give_staff(bot, lead)

    pressed = FakeInteraction(bot, lead)
    await choose(pick, pressed, [discord.Object(id=TEST_CHANNEL)])

    assert sp.CORE_KEYS_ARE_FOR_A_LEAD in pressed.sent
    assert await kinds(db) == []


# --- S4 / S5 / S6, the way back for a hidden command --------------------------------------------


async def test_turn_a_feature_back_on_is_absent_while_nothing_is_hidden(bot, cog, lead):
    await all_features_on(bot.store)

    interaction = await open_panel(cog, bot, lead)

    assert sp.BACK_ON_PLACEHOLDER not in placeholders(interaction.view)
    assert sp.HIDDEN_NONE in interaction.said


async def test_turn_a_feature_back_on_lists_what_is_hidden_and_writes_on_once(bot, cog, lead, db):
    await all_features_on(bot.store)
    await bot.store.set(GUILD, "youtube_mode", "off")

    root = await open_panel(cog, bot, lead)
    pick = picker(root.view, sp.BACK_ON_PLACEHOLDER)
    assert [option.value for option in pick.options] == ["youtube_mode"]
    assert "YouTube uploads — turn it on" in [option.label for option in pick.options]

    pressed = FakeInteraction(bot, lead)
    await choose(pick, pressed, ["youtube_mode"])

    assert bot.store.get(GUILD, "youtube_mode") == "on"
    assert await kinds(db) == ["settings.set"]
    assert (await details(db))[0] == {"key": "youtube_mode", "value": "on", "via": "discord"}


async def test_hiding_switched_off_altogether_is_a_different_sentence_from_nothing_hidden(
    bot, cog, lead
):
    await bot.store.set(GUILD, "youtube_mode", "off")
    await bot.store.set(GUILD, sp.HIDE_COMMANDS_WHEN_OFF, False)

    interaction = await open_panel(cog, bot, lead)

    assert sp.HIDING_OFF in interaction.said
    assert sp.HIDDEN_NONE not in interaction.said
    assert sp.BACK_ON_PLACEHOLDER not in placeholders(interaction.view)


# --- the group card and the key card ------------------------------------------------------------


async def test_a_setting_group_reaches_a_key_card_with_its_value_default_and_help(bot, cog, lead):
    root = await open_panel(cog, bot, lead)
    groups = picker(root.view, "A setting group…")

    opened = FakeInteraction(bot, lead)
    await choose(groups, opened, ["birthday"])
    keys = picker(opened.view, "A setting…")

    card = FakeInteraction(bot, lead)
    await choose(keys, card, ["birthday_color"])

    assert "**birthday_color**" in card.said
    assert "Black Bloc's own default is" in card.said
    assert has_button(card.view, "The colour…")


async def test_find_a_setting_is_offered_only_on_the_group_that_outgrew_the_picker(bot, cog, lead):
    root = await open_panel(cog, bot, lead)
    groups = picker(root.view, "A setting group…")

    chat = FakeInteraction(bot, lead)
    await choose(groups, chat, ["chat"])
    birthday = FakeInteraction(bot, lead)
    await choose(groups, birthday, ["birthday"])

    assert has_button(chat.view, "Find a setting…")
    assert not has_button(birthday.view, "Find a setting…")
    assert "25 of 28 — the rest are on the site" in placeholders(chat.view)
    assert "A setting…" in placeholders(birthday.view)


async def test_find_a_setting_filters_and_says_so_when_nothing_matches(bot, cog, lead):
    root = await open_panel(cog, bot, lead)
    groups = picker(root.view, "A setting group…")
    chat = FakeInteraction(bot, lead)
    await choose(groups, chat, ["chat"])

    found = FakeInteraction(bot, lead)
    await core_cog.run_find(found, chat.view, "chat", "memory")
    empty = FakeInteraction(bot, lead)
    await core_cog.run_find(empty, chat.view, "chat", "quidditch")

    assert all("memory" in option.value for option in picker(found.view, "A setting…").options)
    assert "Nothing in **chat** has **quidditch**" in empty.sent
    assert picker(empty.view, "25 of 28 — the rest are on the site") is not None


async def test_the_rule_book_card_carries_no_editor_at_all(bot, cog, lead):
    card = FakeInteraction(bot, lead)
    await core_cog.render_key(card, None, key="automod_rules")

    assert sp.RULES_ELSEWHERE in card.said
    assert labels(card.view) == ["Back to the group"]


async def test_a_bool_key_shows_one_button_that_says_which_way_it_will_go(bot, cog, lead, db):
    card = FakeInteraction(bot, lead)
    await core_cog.render_key(card, None, key="golive_embed")
    assert has_button(card.view, "Turn golive_embed off")
    assert not has_button(card.view, "Turn golive_embed on")

    pressed = await press(card.view, "Turn golive_embed off", bot, lead)

    assert bot.store.get(GUILD, "golive_embed") is False
    assert await kinds(db) == ["settings.set"]
    assert has_button(pressed.view, "Turn golive_embed on")


async def test_an_enum_key_offers_its_choices_with_the_current_one_ticked(bot, cog, lead):
    card = FakeInteraction(bot, lead)
    await core_cog.render_key(card, None, key="golive_mode")
    pick = picker(card.view, "Pick one…")

    assert [option.value for option in pick.options] == ["off", "shadow", "on"]
    assert [option.value for option in pick.options if option.default] == ["shadow"]

    chosen = FakeInteraction(bot, lead)
    await choose(pick, chosen, ["on"])

    assert bot.store.get(GUILD, "golive_mode") == "on"


async def test_a_number_modal_carries_the_bound_and_refuses_past_it_without_writing(
    bot, cog, lead, db
):
    card = FakeInteraction(bot, lead)
    await core_cog.render_key(card, None, key="cost_hosting_usd")
    opened = FakeInteraction(bot, lead)
    await button(card.view, "A number…").callback(opened)
    modal = opened.response.modals[0]
    assert modal.field.label == "A whole number, no more than 10000"
    assert "no larger than 10000" in card.said

    refused = FakeInteraction(bot, lead)
    await core_cog.run_typed(refused, card.view, "cost_hosting_usd", "99999")
    words = FakeInteraction(bot, lead)
    await core_cog.run_typed(words, card.view, "cost_hosting_usd", "loads")

    assert "cannot be more than 10000" in refused.sent
    assert "takes a whole number" in words.sent
    assert not bot.store.is_stored(GUILD, "cost_hosting_usd")
    assert await kinds(db) == []


async def test_a_colour_is_refused_in_words_and_saved_when_it_is_one(bot, cog, lead, db):
    refused = FakeInteraction(bot, lead)
    await core_cog.run_typed(refused, None, "birthday_color", "blue")
    assert "#4eefff" in refused.sent
    assert not bot.store.is_stored(GUILD, "birthday_color")

    saved = FakeInteraction(bot, lead)
    await core_cog.run_typed(saved, None, "birthday_color", "#4EEFFF")

    assert bot.store.get(GUILD, "birthday_color") == "#4eefff"
    assert await kinds(db) == ["settings.set"]
    assert (await details(db))[0]["via"] == "discord"


async def test_a_list_longer_than_a_picker_can_hold_draws_no_picker_but_keeps_clear_the_list(
    bot, cog, lead
):
    await bot.store.set(GUILD, "honeypot_exempt_role_ids", list(range(9000, 9026)))

    card = FakeInteraction(bot, lead)
    await core_cog.render_key(card, None, key="honeypot_exempt_role_ids")

    assert "more than one Discord picker can edit at once" in card.said
    assert not any(isinstance(one, discord.ui.RoleSelect) for one in card.view.children)
    assert has_button(card.view, "Clear the list")


async def test_a_short_list_draws_the_picker_with_what_is_stored_already_ticked(bot, cog, lead):
    await bot.store.set(GUILD, "honeypot_exempt_role_ids", [CAKE_ROLE])

    card = FakeInteraction(bot, lead)
    await core_cog.render_key(card, None, key="honeypot_exempt_role_ids")
    pick = picker(card.view, "Pick the roles…")

    assert ticked(pick) == [CAKE_ROLE]
    assert pick.min_values == 0

    cleared = await press(card.view, "Clear the list", bot, lead)

    assert bot.store.get(GUILD, "honeypot_exempt_role_ids") == []
    assert not has_button(cleared.view, "Clear the list")


# --- Put the default back -----------------------------------------------------------------------


async def test_put_the_default_back_is_absent_until_a_row_is_actually_stored(bot, cog, lead, db):
    empty = FakeInteraction(bot, lead)
    await core_cog.render_key(empty, None, key="birthday_role_id")
    assert not has_button(empty.view, "Put the default back")

    await bot.store.set(GUILD, "birthday_role_id", CAKE_ROLE)
    stored = FakeInteraction(bot, lead)
    await core_cog.render_key(stored, None, key="birthday_role_id")
    assert has_button(stored.view, "Put the default back")

    pressed = await press(stored.view, "Put the default back", bot, lead)

    assert not bot.store.is_stored(GUILD, "birthday_role_id")
    assert await kinds(db) == ["settings.clear"]
    assert not has_button(pressed.view, "Put the default back")


async def test_the_staff_channel_reset_asks_first_and_names_what_stops_working(bot, cog, lead, db):
    await bot.store.set(GUILD, "staff_channel_id", LOG_CHANNEL)

    card = FakeInteraction(bot, lead)
    await core_cog.render_key(card, None, key="staff_channel_id")
    asked = await press(card.view, "Put the default back", bot, lead)

    assert sp.CONFIRM_TITLE in asked.said
    assert "two protections stop, quietly" in asked.said
    assert bot.store.is_stored(GUILD, "staff_channel_id")
    assert await kinds(db) == []

    said_yes = await press(asked.view, "Yes, put the default back", bot, lead)

    assert not bot.store.is_stored(GUILD, "staff_channel_id")
    assert await kinds(db) == ["settings.clear"]
    assert not has_button(said_yes.view, "Yes, put the default back")


async def test_leaving_it_as_it_is_changes_nothing(bot, cog, lead, db):
    await bot.store.set(GUILD, "staff_channel_id", LOG_CHANNEL)
    card = FakeInteraction(bot, lead)
    await core_cog.render_key(card, None, key="staff_channel_id")
    asked = await press(card.view, "Put the default back", bot, lead)

    left = await press(asked.view, "Leave it as it is", bot, lead)

    assert bot.store.get(GUILD, "staff_channel_id") == LOG_CHANNEL
    assert await kinds(db) == []
    assert has_button(left.view, "Put the default back")


# --- the sub-panels -------------------------------------------------------------------------------


async def test_how_black_bloc_looks_says_presence_is_not_running_and_draws_no_re_apply(
    bot, cog, lead
):
    root = await open_panel(cog, bot, lead)

    opened = await press(root.view, "How Black Bloc looks…", bot, lead)

    assert sp.PRESENCE_NOT_RUNNING in opened.said
    assert not has_button(opened.view, "Re-apply presence")
    assert has_button(opened.view, "The About Me…")


async def test_re_apply_presence_runs_the_one_shared_function_and_prints_its_sentence(
    bot, cog, lead, monkeypatch
):
    bot.cogs_by_name["Presence"] = FakePresence(last_ok="2026-09-05T10:00:00+00:00")
    monkeypatch.setattr(core_cog, "reapply_presence", _fake_reapply)
    root = await open_panel(cog, bot, lead)
    looks = await press(root.view, "How Black Bloc looks…", bot, lead)
    assert "the status loop last succeeded" in looks.said

    pressed = await press(looks.view, "Re-apply presence", bot, lead)

    assert pressed.sent == "the About Me and the status are back"


async def _fake_reapply(bot):
    return "the About Me and the status are back"


async def test_panels_and_commands_toggles_the_hiding_switch_and_says_the_sync_takes_a_minute(
    bot, cog, lead, db
):
    root = await open_panel(cog, bot, lead)
    opened = await press(root.view, "Panels & commands…", bot, lead)
    assert sp.HIDE_ON_STATE in opened.said

    pressed = await press(opened.view, "Leave every command showing", bot, lead)

    assert bot.store.get(GUILD, sp.HIDE_COMMANDS_WHEN_OFF) is False
    assert "within about a minute" in pressed.sent
    assert sp.HIDE_OFF_STATE in pressed.said
    assert await kinds(db) == ["settings.set"]


async def test_the_operator_log_toggle_is_only_drawn_for_manage_server(bot, cog, member, lead):
    give_staff(bot, member)
    await bot.store.set(GUILD, sp.CORE_KEYS_ADMIN_ONLY_KEY, False)
    root = await open_panel(cog, bot, member)
    plain = await press(root.view, "Panels & commands…", bot, member)

    lead_root = await open_panel(cog, bot, lead)
    theirs = await press(lead_root.view, "Panels & commands…", bot, lead)

    assert not has_button(plain.view, "Leave operator-token reads unlogged")
    assert not has_button(plain.view, "Write a line for every operator-token read")
    assert core_cog.OPERATOR_LOG_IS_FOR_A_LEAD in plain.said
    assert has_button(theirs.view, "Leave operator-token reads unlogged")


async def test_a_lead_demoted_while_the_panels_card_is_open_cannot_press_the_operator_toggle(
    bot, cog, lead, db
):
    """The button is drawn for Manage Server; the MOVE has to re-ask, or losing it mid-panel
    leaves a live control behind."""
    root = await open_panel(cog, bot, lead)
    card = await press(root.view, "Panels & commands…", bot, lead)
    before = bot.store.get(GUILD, sp.OPERATOR_READ_LOG_KEY)
    lead.guild_permissions = FakePerms(manage_guild=False)
    give_staff(bot, lead)

    pressed = await press(card.view, "Leave operator-token reads unlogged", bot, lead)

    assert core_cog.OPERATOR_LOG_REFUSED in pressed.sent
    assert "Manage Server" in pressed.sent
    assert bot.store.get(GUILD, sp.OPERATOR_READ_LOG_KEY) == before
    assert await kinds(db) == []


async def test_a_lead_who_still_has_manage_server_turns_the_operator_log_on(bot, cog, lead, db):
    root = await open_panel(cog, bot, lead)
    card = await press(root.view, "Panels & commands…", bot, lead)

    pressed = await press(card.view, "Leave operator-token reads unlogged", bot, lead)

    assert bot.store.get(GUILD, sp.OPERATOR_READ_LOG_KEY) is False
    assert core_cog.OPERATOR_LOG_REFUSED not in pressed.sent
    assert await kinds(db) == ["settings.set"]


async def test_the_panel_minutes_picker_opens_the_same_key_card_the_group_path_does(bot, cog, lead):
    root = await open_panel(cog, bot, lead)
    opened = await press(root.view, "Panels & commands…", bot, lead)
    pick = picker(opened.view, "How long a panel stays open…")
    assert "settings_panel_minutes — 10 minute(s)" in [one.label for one in pick.options]

    card = FakeInteraction(bot, lead)
    await choose(pick, card, [sp.PANEL_MINUTES_KEY])

    assert "**settings_panel_minutes**" in card.said
    assert has_button(card.view, "A number…")


async def test_changing_the_panels_own_minutes_says_it_applies_next_time(bot, cog, lead):
    said = FakeInteraction(bot, lead)
    await core_cog.run_typed(said, None, sp.PANEL_MINUTES_KEY, "12")

    assert bot.store.get(GUILD, sp.PANEL_MINUTES_KEY) == 12
    assert sp.PANEL_MINUTES_NEXT_TIME in said.sent


async def test_log_levels_offers_only_the_two_levels_a_feature_is_not_on(bot, cog, lead, db):
    root = await open_panel(cog, bot, lead)
    opened = await press(root.view, "Log levels…", bot, lead)
    pick = picker(opened.view, "Which log…")

    card = FakeInteraction(bot, lead)
    await choose(pick, card, ["chat_log_level"])

    assert labels(card.view) == ["off", "all", "Back"]

    pressed = await press(card.view, "off", bot, lead)

    assert bot.store.get(GUILD, "chat_log_level") == "off"
    assert await kinds(db) == ["settings.set"]
    assert labels(pressed.view) == ["important", "all", "Back"]


async def test_back_from_a_level_card_returns_to_the_log_levels_picker(bot, cog, lead):
    root = await open_panel(cog, bot, lead)
    levels = await press(root.view, "Log levels…", bot, lead)
    card = FakeInteraction(bot, lead)
    await choose(picker(levels.view, "Which log…"), card, ["chat_log_level"])

    back = await press(card.view, "Back", bot, lead)

    assert "Which log…" in placeholders(back.view)


async def test_back_from_a_key_card_returns_to_its_own_group(bot, cog, lead):
    card = FakeInteraction(bot, lead)
    await core_cog.render_key(card, None, key="birthday_color")

    back = await press(card.view, "Back to the group", bot, lead)

    assert back.embed.title == "The birthday settings"


async def test_back_from_a_sub_panel_and_refresh_both_put_the_root_up_again(bot, cog, lead):
    root = await open_panel(cog, bot, lead)
    opened = await press(root.view, "Panels & commands…", bot, lead)

    went_back = await press(opened.view, "Back", bot, lead)
    refreshed = await press(root.view, "Refresh", bot, lead)

    assert went_back.embed.title == sp.PANEL_TITLE
    assert refreshed.embed.title == sp.PANEL_TITLE


# --- Logs, and the gates on every move ----------------------------------------------------------


async def test_logs_answers_a_new_ephemeral_message_and_leaves_the_panel_where_it_is(
    bot, cog, lead
):
    root = await open_panel(cog, bot, lead)

    pressed = await press(root.view, "Logs", bot, lead)

    assert pressed.edits == []
    assert pressed.response.messages[-1]["ephemeral"] is True
    assert pressed.response.messages[-1]["embed"].title.startswith("Core")


async def test_logs_still_refuses_a_staffer_who_was_demoted_since_the_panel_opened(
    bot, cog, member
):
    give_staff(bot, member)
    root = await open_panel(cog, bot, member)
    take_staff(bot, member)

    pressed = await press(root.view, "Logs", bot, member)

    assert "staff only" in pressed.sent


async def test_a_demoted_staffer_cannot_even_open_a_sub_panel(bot, cog, member):
    give_staff(bot, member)
    root = await open_panel(cog, bot, member)
    take_staff(bot, member)

    pressed = await press(root.view, "How Black Bloc looks…", bot, member)

    assert "staff only" in pressed.sent
    assert pressed.edits == []


async def test_a_move_made_while_the_database_is_down_writes_nothing(bot, cog, lead, db):
    root = await open_panel(cog, bot, lead)
    await db.close()

    pressed = await press(root.view, "Panels & commands…", bot, lead)

    assert "cannot reach its own database" in pressed.sent
    assert pressed.edits == []
    await db.connect()


async def test_every_write_the_panel_makes_goes_through_set_key_exactly_once(
    bot, cog, lead, monkeypatch
):
    """Checklist 34 — one door, one write, one row, whatever control was pressed."""
    seen = []

    async def counted(bot_, guild, key, value, actor, *, via=core_cog.VIA_DISCORD):
        seen.append((key, value))
        return await set_key(bot_, guild, key, value, actor, via=via)

    monkeypatch.setattr(core_cog, "set_key", counted)
    card = FakeInteraction(bot, lead)
    await core_cog.render_key(card, None, key="golive_embed")

    await press(card.view, "Turn golive_embed off", bot, lead)
    await core_cog.run_typed(FakeInteraction(bot, lead), None, "birthday_color", "#4eefff")

    assert seen == [("golive_embed", False), ("birthday_color", "#4eefff")]


# --- the shared writers ---------------------------------------------------------------------------


async def test_set_key_writes_once_logs_once_and_answers_in_words(bot, db, member):
    """Checklist 34 — the panel's every editor goes through this one function."""
    found = await set_key(bot, bot.guild, "golive_embed", False, member)

    assert found.ok and found.value is False
    assert found.message == "**golive_embed** is now False."
    assert bot.store.get(GUILD, "golive_embed") is False
    assert await kinds(db) == ["settings.set"]
    assert (await details(db))[0] == {"key": "golive_embed", "value": False, "via": "discord"}


async def test_set_key_records_the_door_it_was_asked_to(bot, db, member):
    """The website reuses the same writer, so `via` is a keyword rather than a constant."""
    await set_key(bot, bot.guild, "golive_embed", False, member, via="website")

    assert (await details(db))[0]["via"] == "website"


async def test_set_key_refuses_a_bad_value_in_words_and_writes_nothing(bot, db, member):
    found = await set_key(bot, bot.guild, "golive_mode", "sideways", member)

    assert not found.ok and found.status == 400
    assert "off, shadow, on" in found.message
    assert bot.store.get(GUILD, "golive_mode") == "shadow"
    assert await kinds(db) == []


async def test_set_key_refuses_a_key_the_registry_does_not_have(bot, db, member):
    found = await set_key(bot, bot.guild, "not_a_setting", 1, member)

    assert not found.ok and "not a Black Bloc setting" in found.message
    assert await kinds(db) == []


async def test_set_key_names_a_channel_the_way_the_card_reads_it(bot, db, member):
    found = await set_key(bot, bot.guild, "staff_channel_id", TEST_CHANNEL, member)

    assert found.message == f"**staff_channel_id** is now <#{TEST_CHANNEL}>."
    assert (await details(db))[0]["value"] == TEST_CHANNEL


async def test_clear_key_puts_the_default_back_and_leaves_one_row(bot, db, member):
    await bot.store.set(GUILD, "birthday_role_id", CAKE_ROLE)
    assert bot.store.is_stored(GUILD, "birthday_role_id")

    found = await clear_key(bot, bot.guild, "birthday_role_id", member)

    assert found.ok and found.value is True
    assert "no longer set" in found.message
    assert not bot.store.is_stored(GUILD, "birthday_role_id")
    assert await kinds(db) == ["settings.clear"]
    assert (await details(db))[0] == {"key": "birthday_role_id", "via": "discord"}


async def test_clear_key_records_the_door_it_was_asked_to(bot, db, member):
    await bot.store.set(GUILD, "birthday_role_id", CAKE_ROLE)

    await clear_key(bot, bot.guild, "birthday_role_id", member, via="website")

    assert (await details(db))[0]["via"] == "website"


async def test_clear_key_on_a_key_with_nothing_stored_says_so_and_logs_nothing(bot, db, member):
    """The panel never renders the button in this state; a second click racing one still answers."""
    found = await clear_key(bot, bot.guild, "birthday_role_id", member)

    assert not found.ok and found.status == 409
    assert "was not set" in found.message
    assert await kinds(db) == []


async def test_clear_key_refuses_a_key_the_registry_does_not_have(bot, db, member):
    found = await clear_key(bot, bot.guild, "not_a_setting", member)

    assert not found.ok and "not a Black Bloc setting" in found.message
    assert await kinds(db) == []


tempvoice = app_commands.Group(name="tempvoice", description="Temporary voice channels")
zoo = app_commands.Group(name="zoo", description="Animals", parent=tempvoice)


@app_commands.command(name="ping", description="Check that Black Bloc is alive")
async def a_plain_command(interaction):
    await interaction.response.send_message("pong")


@tempvoice.command(name="setup", description="Create or repair the join-to-create channel")
async def a_staff_subcommand(interaction):
    if not await require_staff(interaction):
        return


@tempvoice.command(name="claim", description="Take over an abandoned channel")
async def an_open_subcommand(interaction):
    await interaction.response.send_message("yours")


@zoo.command(name="feed", description="Feed the animals")
async def a_nested_subcommand(interaction):
    await interaction.response.send_message("fed")


requests = app_commands.Group(name="request", description="Ask staff for something")


@requests.command(name="file", description="File a request")
async def a_request_subcommand(interaction):
    await interaction.response.send_message("filed")


@app_commands.command(name="here", description="Only this guild has it")
async def a_guild_only_command(interaction):
    await interaction.response.send_message("here")


class FakeTree:
    def __init__(self, everywhere, in_this_guild=()):
        self.everywhere = list(everywhere)
        self.in_this_guild = list(in_this_guild)

    def get_commands(self, guild=None):
        return list(self.in_this_guild) if guild is not None else list(self.everywhere)


@pytest.fixture
def helpful(bot):
    bot.tree = FakeTree([a_plain_command, tempvoice], [a_guild_only_command])
    return bot


def test_help_lines_walk_groups_and_subgroups_under_one_bold_heading():
    lines = help_lines([a_plain_command, tempvoice])

    assert lines == [
        "**/ping** — Check that Black Bloc is alive",
        "**/tempvoice** — Temporary voice channels",
        "/tempvoice claim — Take over an abandoned channel",
        "/tempvoice setup — Create or repair the join-to-create channel (staff)",
        "/tempvoice zoo feed — Feed the animals",
    ]


def test_help_lines_keep_the_heading_when_the_filter_matches_the_group():
    assert help_lines([a_plain_command, tempvoice], "zoo") == [
        "**/tempvoice** — Temporary voice channels",
        "/tempvoice zoo feed — Feed the animals",
    ]
    assert help_lines([a_plain_command, tempvoice], "PING") == [
        "**/ping** — Check that Black Bloc is alive"
    ]
    assert help_lines([a_plain_command, tempvoice], "nothing like this") == []


async def test_help_answers_with_every_command_including_the_guild_s_own(helpful, cog, member):
    interaction = FakeInteraction(helpful, member)

    await cog.help_command.callback(cog, interaction, None)

    said = "\n".join(message["content"] for message in interaction.response.messages)
    assert "**/here** — Only this guild has it" in said
    assert "/tempvoice setup — Create or repair the join-to-create channel (staff)" in said
    assert all(message["ephemeral"] for message in interaction.response.messages)
    assert all(
        message["allowed_mentions"].everyone is False
        for message in interaction.response.messages
    )


async def test_help_omits_a_command_a_feature_mode_is_hiding(bot, cog, member):
    bot.tree = FakeTree([a_plain_command, requests])
    await bot.store.set(GUILD, "request_mode", "off")
    interaction = FakeInteraction(bot, member)

    await cog.help_command.callback(cog, interaction, None)

    said = "\n".join(message["content"] for message in interaction.response.messages)
    assert "/request" not in said
    assert "**/ping** — Check that Black Bloc is alive" in said


async def test_help_says_how_many_commands_are_missing_and_how_to_get_them_back(bot, cog, member):
    bot.tree = FakeTree([a_plain_command, requests])
    await bot.store.set(GUILD, "request_mode", "off")
    interaction = FakeInteraction(bot, member)

    await cog.help_command.callback(cog, interaction, None)

    said = "\n".join(message["content"] for message in interaction.response.messages)
    assert "not listed because their feature is turned off" in said
    assert "`/settings` ▸ **Turn a feature back on…**" in said


async def test_help_leaves_the_missing_commands_note_off_a_filtered_list(bot, cog, member):
    bot.tree = FakeTree([a_plain_command, requests])
    await bot.store.set(GUILD, "request_mode", "off")
    interaction = FakeInteraction(bot, member)

    await cog.help_command.callback(cog, interaction, "ping")

    said = "\n".join(message["content"] for message in interaction.response.messages)
    assert "not listed because their feature is turned off" not in said


async def test_help_lists_everything_again_once_the_hiding_switch_is_off(bot, cog, member):
    from black_bloc.settings_store import HIDE_COMMANDS_WHEN_OFF

    bot.tree = FakeTree([a_plain_command, requests])
    await bot.store.set(GUILD, "request_mode", "off")
    await bot.store.set(GUILD, HIDE_COMMANDS_WHEN_OFF, False)
    interaction = FakeInteraction(bot, member)

    await cog.help_command.callback(cog, interaction, None)

    said = "\n".join(message["content"] for message in interaction.response.messages)
    assert "/request file — File a request" in said
    assert "not listed because their feature is turned off" not in said


async def test_help_lists_the_command_again_once_the_mode_is_on(bot, cog, member):
    bot.tree = FakeTree([a_plain_command, requests])
    await bot.store.set(GUILD, "request_mode", "on")
    interaction = FakeInteraction(bot, member)

    await cog.help_command.callback(cog, interaction, None)

    said = "\n".join(message["content"] for message in interaction.response.messages)
    assert "/request file — File a request" in said


async def test_help_says_so_when_the_filter_matches_nothing(helpful, cog, member):
    interaction = FakeInteraction(helpful, member)

    await cog.help_command.callback(cog, interaction, "quidditch")

    assert "No command matches **quidditch**" in interaction.sent
    assert len(interaction.response.messages) == 1


async def test_help_is_split_into_messages_discord_will_take(helpful, cog, member):
    many = [
        app_commands.Command(
            name=f"c{index}",
            description="A command with a description long enough to fill a page " * 2,
            callback=a_plain_command.callback,
        )
        for index in range(40)
    ]
    helpful.tree = FakeTree(many)
    interaction = FakeInteraction(helpful, member)

    await cog.help_command.callback(cog, interaction, None)

    said = [message["content"] for message in interaction.response.messages]
    assert len(said) > 1
    assert all(len(chunk) <= 1900 for chunk in said)


async def test_help_marks_the_staff_commands_the_real_bot_registers(settings):
    black_bloc = BlackBlocBot(settings)
    for name in COGS:
        await black_bloc.load_extension(name)

    said = "\n".join(help_lines(tree_commands(black_bloc.tree)))
    await black_bloc.close()

    assert "**/help** — List every command Black Bloc can run" in said
    assert "**/voice** — Your temporary voice channel, and everything you can change" in said
    assert (
        "**/settings** — Read and change Black Bloc's settings for this server (staff)" in said
    )
    assert "**/warn** — " in said and "(staff)" in said.split("**/warn** — ")[1].split("\n")[0]
    assert "**/ping** — Check that Black Bloc is alive" in said


# --- the self-test card ---------------------------------------------------------------------------


def one_check(name, detail="fine", fails=False):
    from black_bloc import selftest

    async def body(_one):
        if fails:
            raise selftest.CheckFailed(detail)
        return detail

    return selftest.Check(name, "core", body)


def stub_checks(monkeypatch, *checks):
    from black_bloc import selftest

    monkeypatch.setattr(selftest, "checks_for", lambda _bot: tuple(checks))


async def open_selftest(cog, bot, who):
    panel = await open_panel(cog, bot, who)
    return await press(panel.view, "Self-test…", bot, who)


async def test_the_root_opens_a_self_test_card_saying_what_it_will_do(bot, cog, lead):
    give_staff(bot, lead)
    panel = await open_panel(cog, bot, lead)

    assert has_button(panel.view, "Self-test…")

    card = await press(panel.view, "Self-test…", bot, lead)

    assert card.embed.title == sp.SELFTEST_TITLE
    assert "has not run yet" in card.said
    assert labels(card.view) == ["Run the self-test", "Logs", "Back"]
    # Nothing has been posted, so there is nothing to purge and no button that says so.
    assert not has_button(card.view, "Purge now")


async def test_running_the_self_test_answers_the_counts_and_names_every_failure(
    bot, cog, lead, db, monkeypatch
):
    give_staff(bot, lead)
    stub_checks(
        monkeypatch,
        one_check("config.log_channel_id"),
        one_check("read./api/status", "TypeError: no", fails=True),
    )
    card = await open_selftest(cog, bot, lead)

    pressed = await press(card.view, "Run the self-test", bot, lead)

    assert "**1 ok, 1 failed**" in pressed.sent
    assert "**read./api/status** — " in pressed.sent and "TypeError: no" in pressed.sent
    assert "5 minute(s)" in pressed.sent
    assert [kind for kind in await kinds(db) if kind.startswith("selftest")] == [
        "selftest.started",
        "selftest.check",
        "selftest.check",
        "selftest.finished",
    ]
    # The card is re-rendered under the answer, so the last run is on it straight away.
    assert "1 ok · 1 failed" in pressed.embed.description


async def test_a_run_with_nothing_wrong_says_so_rather_than_leaving_a_blank(
    bot, cog, lead, monkeypatch
):
    give_staff(bot, lead)
    stub_checks(monkeypatch, one_check("config.log_channel_id"))
    card = await open_selftest(cog, bot, lead)

    pressed = await press(card.view, "Run the self-test", bot, lead)

    assert "**1 ok, 0 failed**" in pressed.sent
    assert sp.SELFTEST_ALL_WELL in pressed.sent


async def test_a_second_run_is_not_offered_and_is_refused_in_words_off_a_stale_card(
    bot, cog, lead, monkeypatch
):
    """A card opened during a run does not draw the button at all (P3); the card somebody
    already had open still does, so pressing it answers a sentence rather than a 409."""
    from black_bloc import selftest

    give_staff(bot, lead)
    seen = []

    async def while_running(one):
        fresh = await open_selftest(cog, bot, lead)
        seen.append(fresh)
        seen.append(await press(card.view, "Run the self-test", bot, lead))
        return "fine"

    stub_checks(monkeypatch, selftest.Check("config.one", "core", while_running))
    card = await open_selftest(cog, bot, lead)

    await press(card.view, "Run the self-test", bot, lead)
    fresh, stale = seen

    assert not has_button(fresh.view, "Run the self-test")
    assert sp.SELFTEST_IS_RUNNING in fresh.embed.description
    assert "already running" in stale.sent
    assert "0 of 1 checks done" in stale.sent
    assert "409" not in stale.sent


async def test_purge_now_appears_once_something_is_posted_and_takes_it_down(
    bot, cog, lead, db, monkeypatch
):
    from black_bloc import selftest

    give_staff(bot, lead)

    async def posts(one):
        await one.post(content="a card")
        return "posted"

    stub_checks(monkeypatch, selftest.Check("panel.settings", "core", posts))
    card = await open_selftest(cog, bot, lead)
    ran = await press(card.view, "Run the self-test", bot, lead)

    assert has_button(ran.view, "Purge now")
    assert "1 message(s) are still waiting" in ran.embed.description

    purged = await press(ran.view, "Purge now", bot, lead)

    assert "1 self-test message(s) deleted." == purged.sent
    assert await selftest.waiting_messages(db, GUILD) == []
    assert not has_button(purged.view, "Purge now")


async def test_the_self_test_card_carries_its_own_logs_button_for_the_test_feature(
    bot, cog, lead, db, monkeypatch
):
    """Every feature's Logs is a panel button; the Test feature's lives here, because the
    Logs page leaves those rows out of its default view."""
    from black_bloc import selftest

    give_staff(bot, lead)
    stub_checks(monkeypatch, one_check("config.log_channel_id"))
    card = await open_selftest(cog, bot, lead)
    await press(card.view, "Run the self-test", bot, lead)

    logs = await press(card.view, "Logs", bot, lead)

    assert logs.rendered["ephemeral"] is True
    assert logs.embed.title == "Test log"
    assert "selftest.started" in logs.embed.description
    assert selftest.running(bot, GUILD) is None


async def test_the_purge_loop_is_a_loop_the_health_page_can_see(bot, cog):
    from discord.ext import tasks

    assert isinstance(cog.purge_loop, tasks.Loop)
    assert cog.purge_loop.seconds == 60
    assert cog.loop_health("purge_loop") == (None, None)
    assert cog.loop_health("something_else") == (None, None)

    await cog.purge_loop.coro(cog)

    last_ok, last_error = cog.loop_health("purge_loop")
    assert last_ok and last_error is None
