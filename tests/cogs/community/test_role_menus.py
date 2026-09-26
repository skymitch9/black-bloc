import pathlib
import re
from datetime import UTC, datetime
from types import SimpleNamespace

import discord
import pytest

from black_bloc import rolegrants as grants
from black_bloc import rolemenus as menus
from black_bloc.cogs.community import role_menus as cog_module
from black_bloc.cogs.community.role_menus import (
    APPROVAL_CHANNEL_KEY,
    APPROVER_ROLE_KEY,
    DESCRIPTION_MAX,
    JOY_GAMING,
    LABEL_MAX,
    MODE_KEY,
    MODES,
    OPTIONS_MAX,
    ROLE_MENUS_OFF,
    SEED,
    TITLE_MAX,
    UNSET,
    AssignPick,
    MenuLimitError,
    RequestApproveModal,
    RequestButton,
    RequestDenyModal,
    RoleMenus,
    RoleMenuView,
    add_option,
    audit_actor,
    card_target,
    clear_message,
    create_menu,
    custom_id,
    delete_menu,
    expires_days_of,
    get_menu,
    get_options,
    list_menus,
    max_values_for,
    needs_approval,
    panel_embed,
    parse_custom_id,
    positive_days,
    posted_menus,
    remove_option,
    retry_days_of,
    role_diff,
    seed_default_menus,
    seed_summary,
    select_emoji,
    set_message,
    summary,
    timed_menu_owns,
    unposted_menus,
    update_menu,
)
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore

GUILD = 7
TEST_CHANNEL = 111
LOG_CHANNEL = 222
STAFF_CHANNEL = 333


async def test_menu_crud(db):
    menu_id = await create_menu(db, GUILD, "pronouns", "Pronouns", "pick some", "multiple")
    assert menu_id is not None
    assert await create_menu(db, GUILD, "pronouns", "Pronouns") is None
    assert await create_menu(db, GUILD + 1, "pronouns", "Pronouns") is not None

    menu = await get_menu(db, GUILD, "pronouns")
    assert menu["title"] == "Pronouns" and menu["mode"] == "multiple"
    assert [m["name"] for m in await list_menus(db, GUILD)] == ["pronouns"]

    assert await delete_menu(db, GUILD, "pronouns") is True
    assert await delete_menu(db, GUILD, "pronouns") is False


async def test_option_crud_and_ordering(db):
    menu_id = await create_menu(db, GUILD, "m", "M")
    await add_option(db, menu_id, 1, "He/Him", "❤️")
    await add_option(db, menu_id, 2, "She/Her", "💙")
    await add_option(db, menu_id, 1, "He/Him (edited)", "❤️")

    options = await get_options(db, menu_id)
    assert [(o["role_id"], o["label"]) for o in options] == [
        (1, "He/Him (edited)"),
        (2, "She/Her"),
    ]
    assert await remove_option(db, menu_id, 2) is True
    assert await remove_option(db, menu_id, 2) is False
    assert len(await get_options(db, menu_id)) == 1


async def test_delete_menu_takes_its_options(db):
    menu_id = await create_menu(db, GUILD, "m", "M")
    await add_option(db, menu_id, 1, "One")
    await delete_menu(db, GUILD, "m")
    assert await get_options(db, menu_id) == []


async def test_posted_menus_only_lists_posted_ones(db):
    posted_id = await create_menu(db, GUILD, "posted", "P")
    await create_menu(db, GUILD, "draft", "D")
    await set_message(db, posted_id, 500, 600)
    rows = await posted_menus(db)
    assert [(r["name"], r["channel_id"], r["message_id"]) for r in rows] == [("posted", 500, 600)]


async def test_clearing_the_message_keeps_the_channel_the_panel_was_in(db):
    menu_id = await create_menu(db, GUILD, "posted", "P")
    await add_option(db, menu_id, 1, "One")
    await set_message(db, menu_id, 500, 600)

    await clear_message(db, menu_id)

    menu = await get_menu(db, GUILD, "posted")
    assert menu["message_id"] is None and menu["channel_id"] == 500
    options = await get_options(db, menu_id)
    assert [(row["role_id"], row["label"]) for row in options] == [(1, "One")]
    assert [row["name"] for row in await unposted_menus(db)] == ["posted"]
    assert await posted_menus(db) == []


async def test_unposted_menus_skips_a_menu_that_never_had_a_channel(db):
    await create_menu(db, GUILD, "draft", "D")
    assert await unposted_menus(db) == []


async def test_bad_mode_is_refused(db):
    with pytest.raises(ValueError, match="mode must be"):
        await create_menu(db, GUILD, "m", "M", None, "sometimes")


async def test_seed_is_idempotent(db):
    created, skipped = await seed_default_menus(db, GUILD)
    assert created == [name for name, _, _, _ in SEED] and skipped == []
    menu = await get_menu(db, GUILD, "pronouns")
    assert len(await get_options(db, menu["id"])) == 9

    created_again, skipped_again = await seed_default_menus(db, GUILD)
    assert created_again == [] and skipped_again == [name for name, _, _, _ in SEED]
    assert len(await list_menus(db, GUILD)) == len(SEED)
    assert len(await get_options(db, menu["id"])) == 9


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id
        self.name = f"role-{role_id}"

    def is_assignable(self):
        return True


class FakePerms:
    def __init__(self, manage_guild=False):
        self.manage_guild = manage_guild


class FakeMessage:
    def __init__(self, message_id, channel, **kwargs):
        self.id = message_id
        self.channel = channel
        self.jump_url = f"https://discord.test/{message_id}"
        self.kwargs = kwargs

    async def edit(self, **kwargs):
        self.kwargs |= kwargs

    async def delete(self):
        self.channel.messages = [m for m in self.channel.messages if m.id != self.id]


class FakeChannel:
    def __init__(self, channel_id):
        self.id = channel_id
        self.mention = f"<#{channel_id}>"
        self.overwrites = {}
        self.messages = []
        self.send_raises = None

    async def fetch_message(self, message_id):
        found = next((m for m in self.messages if m.id == message_id), None)
        if found is None:
            raise LookupError(message_id)
        return found

    async def send(self, content=None, **kwargs):
        if self.send_raises is not None:
            raise self.send_raises
        message = FakeMessage(self.id * 100 + len(self.messages), self, content=content, **kwargs)
        self.messages.append(message)
        return message

    def get_partial_message(self, message_id):
        found = next((m for m in self.messages if m.id == message_id), None)
        if found is None:
            raise LookupError(message_id)
        return found


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black in a Flash!"
        self.channels = {
            LOG_CHANNEL: FakeChannel(LOG_CHANNEL),
            TEST_CHANNEL: FakeChannel(TEST_CHANNEL),
            STAFF_CHANNEL: FakeChannel(STAFF_CHANNEL),
        }
        self.members = {}
        self.me = None
        self.audit_entries = []

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_role(self, role_id):
        return FakeRole(role_id)

    def get_member(self, user_id):
        return self.members.get(user_id)

    def audit_logs(self, limit=1, action=None):
        entries = list(self.audit_entries)

        async def walk():
            for entry in entries:
                yield entry

        return walk()


class FakeMember:
    def __init__(self, guild, user_id=900, display_name="Alice", roles=(), manage_guild=False):
        self.id = user_id
        self.guild = guild
        self.display_name = display_name
        self.mention = f"<@{user_id}>"
        self.roles = [FakeRole(r) for r in roles]
        self.guild_permissions = FakePerms(manage_guild=manage_guild)
        self.edits = []
        self.edit_raises = None
        self.dms = []
        guild.members[user_id] = self

    async def edit(self, roles=None, reason=None):
        if self.edit_raises is not None:
            raise self.edit_raises
        self.edits.append([r.id for r in roles])
        self.roles = list(roles)

    async def send(self, content=None, **kwargs):
        self.dms.append(content)


class FakeGuard:
    def __init__(self, allowed=TEST_CHANNEL):
        self.allowed = allowed
        self.test_channel_id = TEST_CHANNEL

    def allows_channel(self, channel_id):
        return channel_id == self.allowed

    def refusal_message(self):
        return "test mode"


class FakeBot:
    def __init__(self, db, store, guild):
        self.db = db
        self.store = store
        self.guild = guild
        self.guilds = [guild]
        self.guard = None
        self.views = []

    def add_view(self, view, *, message_id=None):
        self.views.append((view, message_id))

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def get_guild(self, guild_id):
        return self.guild if guild_id == self.guild.id else None


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.modals = []
        self.deferred = False

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def defer(self, ephemeral=False):
        self.deferred = True

    async def send_modal(self, modal):
        self.modals.append(modal)
        self.deferred = True

    def is_done(self):
        return self.deferred or bool(self.messages)


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.response.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class PanelMessage:
    def __init__(self, message_id, **kwargs):
        self.id = message_id
        self.kwargs = kwargs

    async def edit(self, **kwargs):
        self.kwargs |= kwargs

    @property
    def embeds(self):
        one = self.kwargs.get("embed")
        return [one] if one is not None else list(self.kwargs.get("embeds") or ())


class FakeInteraction:
    def __init__(self, bot, user):
        self.client = bot
        self.user = user
        self.guild = bot.guild
        self.guild_id = bot.guild.id
        self.channel = bot.guild.get_channel(TEST_CHANNEL)
        self.channel_id = TEST_CHANNEL
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)
        self.edits = []

    async def original_response(self):
        return PanelMessage(1)

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return PanelMessage(9500, **kwargs)

    @property
    def said(self):
        return [m["content"] for m in self.response.messages if m.get("content") is not None]

    @property
    def sent(self):
        spoken = self.said
        return spoken[-1] if spoken else None

    @property
    def rendered(self):
        if self.edits:
            return self.edits[-1]
        return self.response.messages[-1] if self.response.messages else {}

    @property
    def embed(self):
        return self.rendered.get("embed")

    @property
    def body(self):
        one = self.embed
        return "" if one is None else str(one.description or "")

    @property
    def view(self):
        return self.rendered.get("view")


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOG_CHANNEL)
    await store.set(GUILD, MODE_KEY, "on")
    return FakeBot(db, store, FakeGuild())


@pytest.fixture
def lead(bot):
    return FakeMember(bot.guild, user_id=1, display_name="Lead", manage_guild=True)


def a_panel(where=cog_module.ROOT, **state):
    view = cog_module.RoleMenuPanel(10)
    view.where = where
    for key, value in state.items():
        setattr(view, key, value)
    return view


def assign_pick(menu_id, options, target, *, remove):
    """The picker as the panel builds it: inside a view that knows which menu it came from."""
    view = a_panel(cog_module.HAND_VIEW, menu_name="runner-status", member_id=target.id)
    view.removing = remove
    pick = AssignPick(menu_id, options, target, remove=remove)
    view.add_item(pick)
    return pick


async def staff_menu(db, name="runner-status"):
    menu_id = await create_menu(db, GUILD, name, "Runner status", None, "staff")
    await add_option(db, menu_id, 10, "Runner")
    await add_option(db, menu_id, 11, "Live Runner")
    return menu_id


async def action_kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def test_assign_applies_the_diff_to_the_target_and_logs_who_did_it(bot, db, lead):
    menu_id = await staff_menu(db)
    target = FakeMember(bot.guild, user_id=900, roles=(10, 99))
    select = assign_pick(menu_id, await get_options(db, menu_id), target, remove=False)
    select._values = ["11"]
    interaction = FakeInteraction(bot, lead)

    await select.callback(interaction)

    assert target.edits == [[99, 11]]
    assert "Added: Live Runner" in interaction.sent and "Removed: Runner" in interaction.sent
    assert "role_menu.assign" in await action_kinds(db)


async def test_unassign_takes_only_the_picked_roles_off(bot, db, lead):
    menu_id = await staff_menu(db)
    target = FakeMember(bot.guild, user_id=900, roles=(10, 11, 99))
    options = [row for row in await get_options(db, menu_id)]
    select = assign_pick(menu_id, options, target, remove=True)
    select._values = ["10"]

    await select.callback(FakeInteraction(bot, lead))

    assert target.edits == [[11, 99]]
    assert "role_menu.unassign" in await action_kinds(db)


async def test_assigning_is_refused_in_test_mode(bot, db, lead):
    menu_id = await staff_menu(db)
    bot.guard = FakeGuard(allowed=LOG_CHANNEL)
    target = FakeMember(bot.guild, user_id=900)
    select = assign_pick(menu_id, await get_options(db, menu_id), target, remove=False)
    select._values = ["10"]
    interaction = FakeInteraction(bot, lead)

    await select.callback(interaction)

    assert target.edits == [] and interaction.sent == "test mode"


async def test_a_refused_role_edit_says_the_member_is_unchanged(bot, db, lead):
    menu_id = await staff_menu(db)
    target = FakeMember(bot.guild, user_id=900, display_name="Bo")
    target.edit_raises = discord.HTTPException(_Refused(403), "no")
    select = assign_pick(menu_id, await get_options(db, menu_id), target, remove=False)
    select._values = ["10"]
    interaction = FakeInteraction(bot, lead)

    await select.callback(interaction)

    assert "still has exactly the roles they had" in interaction.sent
    assert "role_menu.assign" not in await action_kinds(db)


@pytest.fixture
def clicker(monkeypatch, bot):
    """`RoleMenuSelect` insists on a real `discord.Member`; the fake stands in for one."""
    monkeypatch.setattr(discord, "Member", FakeMember)
    return FakeMember(bot.guild, user_id=900, roles=(99,))


async def self_serve_menu(db, name="pronouns"):
    menu_id = await create_menu(db, GUILD, name, "Pronouns", None, "multiple")
    await add_option(db, menu_id, 1, "He/Him")
    await add_option(db, menu_id, 2, "She/Her")
    return menu_id


async def test_a_click_hands_out_roles_while_role_menus_are_on(bot, db, clicker):
    menu_id = await self_serve_menu(db)
    select = RoleMenuView(menu_id, await get_options(db, menu_id), "multiple").children[0]
    select._values = ["1"]
    interaction = FakeInteraction(bot, clicker)

    await select.callback(interaction)

    assert clicker.edits == [[99, 1]]
    assert "Added: He/Him" in interaction.sent
    assert "role_menu.update" in await action_kinds(db)


async def test_a_click_changes_nothing_while_role_menus_are_off(bot, db, clicker):
    menu_id = await self_serve_menu(db)
    await bot.store.set(GUILD, MODE_KEY, "off")
    select = RoleMenuView(menu_id, await get_options(db, menu_id), "multiple").children[0]
    select._values = ["1"]
    interaction = FakeInteraction(bot, clicker)

    await select.callback(interaction)

    assert interaction.sent == ROLE_MENUS_OFF
    assert interaction.response.messages[0]["ephemeral"] is True
    assert clicker.edits == [] and [role.id for role in clicker.roles] == [99]
    assert "role_menu.update" not in await action_kinds(db)


async def test_the_staff_select_still_hands_a_role_over_while_role_menus_are_off(bot, db, lead):
    """Pings remake §C6, reversing this test's own earlier assertion: `rolemenu_mode` governs
    members picking from a posted panel. Staff handing a role over by name has no onboarding
    equivalent, so the mode going off must not take it away."""
    menu_id = await staff_menu(db)
    target = FakeMember(bot.guild, user_id=900, roles=(10,))
    select = assign_pick(menu_id, await get_options(db, menu_id), target, remove=False)
    select._values = ["11"]
    await bot.store.set(GUILD, MODE_KEY, "off")
    interaction = FakeInteraction(bot, lead)

    await select.callback(interaction)

    assert interaction.sent != ROLE_MENUS_OFF
    assert target.edits == [[11]]
    assert "role_menu.assign" in await action_kinds(db)


def test_seed_summary_is_the_one_wording_both_doors_show():
    said = seed_summary(["pronouns"], ["colours"])

    assert "Created: pronouns" in said
    assert "Already there, left alone: colours" in said
    assert "press **Post it**" in said
    assert "Already there" not in seed_summary(["pronouns"], [])


class _Refused:
    def __init__(self, status):
        self.status = status
        self.reason = "refused"


def test_role_diff_only_touches_menu_roles():
    to_add, to_remove = role_diff({1, 2, 99}, [1, 2, 3], [2, 3])
    assert to_add == {3}
    assert to_remove == {1}


def test_role_diff_ignores_selections_outside_the_menu():
    to_add, to_remove = role_diff({1}, [1], [42])
    assert to_add == set() and to_remove == {1}


def test_role_diff_empty_selection_removes_everything_the_menu_owns():
    assert role_diff({1, 2, 99}, [1, 2], []) == (set(), {1, 2})


def test_single_mode_limits_the_picker():
    assert max_values_for("single", 9) == 1
    assert max_values_for("multiple", 9) == 9
    assert max_values_for("multiple", 0) == 1


def test_custom_id_round_trip():
    assert custom_id(12) == "rolemenu:12"
    assert parse_custom_id("rolemenu:12") == 12
    assert parse_custom_id("rolemenu:abc") is None
    assert parse_custom_id("other:12") is None


def test_summary_sentences():
    assert summary(["A"], ["B"]) == "Added: A · Removed: B"
    assert summary(["A"], []) == "Added: A"
    assert "Nothing changed" in summary([], [])


def test_view_is_persistent_and_keyed_by_menu_id():
    options = [
        {"role_id": 1, "label": "One", "emoji": "❤️"},
        {"role_id": 2, "label": "Two", "emoji": None},
    ]
    view = RoleMenuView(3, options, "multiple")
    select = view.children[0]
    assert view.timeout is None and view.is_persistent()
    assert select.custom_id == "rolemenu:3"
    assert select.min_values == 0 and select.max_values == 2
    assert [o.value for o in select.options] == ["1", "2"]
    assert select.role_ids == [1, 2]


def test_single_mode_view_allows_one_pick():
    options = [{"role_id": 1, "label": "One", "emoji": None}]
    assert RoleMenuView(4, options, "single").children[0].max_values == 1


def test_panel_embed_lists_the_options():
    menu = {"title": "Pronouns", "description": None}
    options = [
        {"role_id": 1, "label": "He/Him", "emoji": "❤️"},
        {"role_id": 2, "label": "She/Her", "emoji": None},
    ]
    embed = panel_embed(menu, options)
    assert embed.title == "Pronouns"
    assert embed.fields[0].value == "❤️ He/Him\nShe/Her"


def test_seed_data_is_well_formed():
    names = [name for name, _, _, _ in SEED]
    assert len(names) == len(set(names)) == 6
    for _, _, mode, options in SEED:
        assert mode in MODES
        assert options
        assert len({role_id for _, _, role_id in options}) == len(options)


def test_every_sentence_about_the_seed_counts_the_menus_correctly():
    import inspect

    from black_bloc.cogs.community import role_menus

    source = inspect.getsource(role_menus)
    assert "five" not in source
    assert source.count("six") >= 2
    assert "staff hands them out" in role_menus.BAD_MODE


def test_the_marathons_option_carries_the_incumbents_own_emoji():
    options = dict(
        (label, emoji) for _, _, _, opts in SEED for emoji, label, _ in opts if label == "Marathons"
    )
    assert options["Marathons"] == JOY_GAMING


def test_runner_status_is_a_staff_menu():
    menu = next(entry for entry in SEED if entry[0] == "runner-status")
    assert menu[2] == "staff"
    assert [label for _, label, _ in menu[3]] == ["Runner", "Live Runner", "Commentator"]


def test_custom_emoji_become_partial_emoji_and_plain_ones_do_not():
    assert select_emoji("❤️") == "❤️"
    assert select_emoji(None) is None
    assert select_emoji("") is None
    partial = select_emoji(JOY_GAMING)
    assert isinstance(partial, discord.PartialEmoji)
    assert partial.name == "JoyGAMING" and partial.id == 1337948924844965931


def test_a_broken_emoji_string_shows_nothing_rather_than_breaking_the_panel():
    assert select_emoji("<not an emoji>") is None


def test_the_panel_renders_a_custom_emoji_option():
    options = [{"role_id": 1, "label": "Marathons", "emoji": JOY_GAMING}]
    select = RoleMenuView(9, options, "multiple").children[0]
    assert select.options[0].emoji.id == 1337948924844965931


async def test_a_heading_or_a_line_over_discords_limit_is_refused_not_cut_down(db):
    """The staffer's own words are never truncated behind their back (checklist 22)."""
    with pytest.raises(MenuLimitError, match="256"):
        await create_menu(db, GUILD, "long", "t" * (TITLE_MAX + 1))
    with pytest.raises(MenuLimitError, match="4096"):
        await create_menu(db, GUILD, "long", "Fine", "d" * (DESCRIPTION_MAX + 1))

    assert await create_menu(db, GUILD, "long", "t" * TITLE_MAX) is not None
    assert await get_menu(db, GUILD, "long") is not None


async def test_an_update_over_the_limit_changes_nothing(db):
    menu_id = await create_menu(db, GUILD, "colours", "Colours", "one each")

    with pytest.raises(MenuLimitError):
        await update_menu(db, GUILD, "colours", title="t" * (TITLE_MAX + 1))
    with pytest.raises(MenuLimitError):
        await update_menu(db, GUILD, "colours", description="d" * (DESCRIPTION_MAX + 1))

    menu = await get_menu(db, GUILD, "colours")
    assert (menu["id"], menu["title"], menu["description"]) == (menu_id, "Colours", "one each")


async def test_a_label_over_the_limit_and_a_twenty_sixth_option_are_both_refused(db):
    menu_id = await create_menu(db, GUILD, "colours", "Colours")

    with pytest.raises(MenuLimitError, match="100"):
        await add_option(db, menu_id, 1, "l" * (LABEL_MAX + 1))

    for role_id in range(OPTIONS_MAX):
        await add_option(db, menu_id, role_id, f"role {role_id}")
    with pytest.raises(MenuLimitError, match="25"):
        await add_option(db, menu_id, 999, "one too many")

    assert len(await get_options(db, menu_id)) == OPTIONS_MAX


async def test_a_full_menu_can_still_have_an_existing_option_relabelled(db):
    """The count only bounds NEW rows; editing one of the 25 must not be refused."""
    menu_id = await create_menu(db, GUILD, "colours", "Colours")
    for role_id in range(OPTIONS_MAX):
        await add_option(db, menu_id, role_id, f"role {role_id}")

    await add_option(db, menu_id, 0, "renamed")

    options = await get_options(db, menu_id)
    assert len(options) == OPTIONS_MAX
    assert options[0]["label"] == "renamed"


async def approval_menu(db, name="runner-status", *, expires=None, retry=7):
    menu_id = await create_menu(
        db,
        GUILD,
        name,
        "Runner status",
        None,
        "multiple",
        approval=True,
        expires_days=expires,
        retry_days=retry,
    )
    await add_option(db, menu_id, 10, "Runner")
    await add_option(db, menu_id, 11, "Live Runner")
    return menu_id


async def pick(bot, db, menu_id, member, values):
    select = RoleMenuView(menu_id, await get_options(db, menu_id), "multiple").children[0]
    select._values = list(values)
    interaction = FakeInteraction(bot, member)
    await select.callback(interaction)
    return interaction


async def requests_in(db):
    cur = await db.conn.execute("SELECT * FROM role_requests ORDER BY id")
    return list(await cur.fetchall())


def cards_in(bot, channel_id=TEST_CHANNEL):
    return bot.guild.get_channel(channel_id).messages


async def click(bot, request_id, action, user):
    button = RequestButton(request_id, action)
    interaction = FakeInteraction(bot, user)
    await button.callback(interaction)
    return interaction


async def deny(bot, db, request_id, user, reason):
    interaction = await click(bot, request_id, "deny", user)
    modal = interaction.response.modals[0]
    modal.reason._value = reason
    await modal.on_submit(interaction)
    return interaction


async def test_a_pick_on_an_approval_menu_asks_staff_and_changes_no_roles(bot, db, clicker):
    menu_id = await approval_menu(db)

    interaction = await pick(bot, db, menu_id, clicker, ["10"])

    assert clicker.edits == []
    assert "Sent to staff for approval" in interaction.sent
    rows = await requests_in(db)
    assert len(rows) == 1
    assert (rows[0]["status"], rows[0]["role_id"], rows[0]["user_id"]) == ("pending", 10, 900)
    assert "role.requested" in await action_kinds(db)
    assert len(cards_in(bot)) == 1


async def test_the_request_card_carries_two_buttons_and_pings_the_approver_role(bot, db, clicker):
    menu_id = await approval_menu(db, expires=7)
    await bot.store.set(GUILD, APPROVER_ROLE_KEY, 55)

    await pick(bot, db, menu_id, clicker, ["10"])

    card = cards_in(bot)[0]
    assert card.kwargs["content"] == "<@&55>"
    assert [item.custom_id for item in card.kwargs["view"].children] == [
        "rolereq:1:approve",
        "rolereq:1:deny",
    ]
    assert card.kwargs["allowed_mentions"].roles == [discord.Object(id=55)]
    fields = {field.name: field.value for field in card.kwargs["embed"].fields}
    assert fields["Role"] == "Runner" and fields["Lasts"] == "7 day(s)"
    assert fields["Status"] == "pending"


async def test_the_request_card_is_a_notification_and_ignores_the_log_level(bot, db, clicker):
    """Decision 2: an approval card is its own send, so `off` must not take it away."""
    await bot.store.set(GUILD, "rolemenu_log_level", "off")
    menu_id = await approval_menu(db, expires=7)

    await pick(bot, db, menu_id, clicker, ["10"])

    assert "role.requested" in await action_kinds(db)
    assert len(cards_in(bot)) == 1


async def test_picking_a_pending_role_again_takes_the_request_back(bot, db, clicker):
    menu_id = await approval_menu(db)
    await pick(bot, db, menu_id, clicker, ["10"])

    interaction = await pick(bot, db, menu_id, clicker, ["10"])

    assert "taken back" in interaction.sent
    assert (await requests_in(db))[0]["status"] == "withdrawn"
    assert "role.withdrawn" in await action_kinds(db)
    assert cards_in(bot)[0].kwargs["view"] is None


async def test_a_second_ask_while_one_is_open_is_refused_with_a_sentence(bot, db, clicker):
    from black_bloc.cogs.community.role_menus import submit_request

    menu_id = await approval_menu(db)
    menu = await get_menu(db, GUILD, "runner-status")
    await pick(bot, db, menu_id, clicker, ["10"])

    said = await submit_request(bot, bot.guild, clicker, menu, 10)

    assert "already asked" in said
    assert len(await requests_in(db)) == 1


async def test_a_denial_inside_the_retry_window_refuses_and_names_the_day(bot, db, clicker, lead):
    menu_id = await approval_menu(db, retry=7)
    await pick(bot, db, menu_id, clicker, ["10"])
    await deny(bot, db, 1, lead, "not this month")

    interaction = await pick(bot, db, menu_id, clicker, ["10"])

    assert "Staff said no" in interaction.sent and "you can ask again" in interaction.sent
    assert len(await requests_in(db)) == 1


async def test_a_denial_outside_the_retry_window_lets_them_ask_again(bot, db, clicker, lead):
    menu_id = await approval_menu(db, retry=0)
    await pick(bot, db, menu_id, clicker, ["10"])
    await deny(bot, db, 1, lead, "not this month")

    interaction = await pick(bot, db, menu_id, clicker, ["10"])

    assert "Sent to staff for approval" in interaction.sent
    assert [row["status"] for row in await requests_in(db)] == ["denied", "pending"]


async def test_approve_hands_the_role_over_dms_the_member_and_closes_the_card(
    bot, db, clicker, lead
):
    menu_id = await approval_menu(db)
    await pick(bot, db, menu_id, clicker, ["10"])

    interaction = await click(bot, 1, "approve", lead)

    assert clicker.edits == [[99, 10]]
    assert "Approved" in interaction.sent
    assert (await requests_in(db))[0]["status"] == "approved"
    grant = await grants.open_grant(db, GUILD, clicker.id, 10)
    assert grant["source"] == "approval" and grant["expires_at"] is None
    assert clicker.dms and "Staff approved **Runner**" in clicker.dms[0]
    assert "role.approved" in await action_kinds(db)
    assert cards_in(bot)[0].kwargs["view"] is None


async def test_an_approval_on_a_timed_menu_asks_for_the_days_first(bot, db, clicker, lead):
    menu_id = await approval_menu(db, expires=7)
    await pick(bot, db, menu_id, clicker, ["10"])

    interaction = await click(bot, 1, "approve", lead)

    modal = interaction.response.modals[0]
    assert isinstance(modal, RequestApproveModal) and modal.days.default == "7"
    modal.days._value = "3"
    await modal.on_submit(interaction)

    grant = await grants.open_grant(db, GUILD, clicker.id, 10)
    assert (grants.parse_ts(grant["expires_at"]) - datetime.now(UTC)).days == 2
    assert "It runs out" in clicker.dms[0]


async def test_a_blank_days_box_keeps_the_menus_own_number(bot, db, clicker, lead):
    menu_id = await approval_menu(db, expires=7)
    await pick(bot, db, menu_id, clicker, ["10"])
    interaction = await click(bot, 1, "approve", lead)

    await interaction.response.modals[0].on_submit(interaction)

    grant = await grants.open_grant(db, GUILD, clicker.id, 10)
    assert (grants.parse_ts(grant["expires_at"]) - datetime.now(UTC)).days == 6


async def test_zero_days_means_the_role_never_runs_out(bot, db, clicker, lead):
    menu_id = await approval_menu(db, expires=7)
    await pick(bot, db, menu_id, clicker, ["10"])
    interaction = await click(bot, 1, "approve", lead)
    modal = interaction.response.modals[0]
    modal.days._value = "0"

    await modal.on_submit(interaction)

    assert (await grants.open_grant(db, GUILD, clicker.id, 10))["expires_at"] is None


async def test_days_that_are_not_a_number_decide_nothing(bot, db, clicker, lead):
    menu_id = await approval_menu(db, expires=7)
    await pick(bot, db, menu_id, clicker, ["10"])
    interaction = await click(bot, 1, "approve", lead)
    modal = interaction.response.modals[0]
    modal.days._value = "a fortnight"

    await modal.on_submit(interaction)

    assert "is not a number of days" in interaction.sent
    assert (await requests_in(db))[0]["status"] == "pending"
    assert clicker.edits == []


async def test_deny_takes_a_reason_and_tells_the_member_when_they_may_ask_again(
    bot, db, clicker, lead
):
    menu_id = await approval_menu(db, retry=7)
    await pick(bot, db, menu_id, clicker, ["10"])

    interaction = await deny(bot, db, 1, lead, "not this month")

    row = (await requests_in(db))[0]
    assert row["status"] == "denied" and row["deny_reason"] == "not this month"
    assert clicker.edits == []
    assert "Denied" in interaction.sent
    assert "not this month" in clicker.dms[0] and "You can ask again" in clicker.dms[0]
    assert "role.denied" in await action_kinds(db)


async def test_only_the_first_decision_lands(bot, db, clicker, lead):
    menu_id = await approval_menu(db)
    await pick(bot, db, menu_id, clicker, ["10"])
    await click(bot, 1, "approve", lead)

    second = await click(bot, 1, "approve", lead)

    assert "already **approved**" in second.sent
    assert clicker.edits == [[99, 10]]


async def test_deciding_is_staff_only(bot, db, clicker):
    menu_id = await approval_menu(db)
    await pick(bot, db, menu_id, clicker, ["10"])
    stranger = FakeMember(bot.guild, user_id=901)

    interaction = await click(bot, 1, "approve", stranger)

    assert "staff only" in interaction.sent
    assert (await requests_in(db))[0]["status"] == "pending"


async def test_a_request_nobody_has_is_answered_with_a_sentence(bot, db, lead):
    interaction = await click(bot, 99, "approve", lead)

    assert "no record of that request" in interaction.sent


async def test_the_card_falls_back_to_the_test_channel_and_the_log_says_so(bot, db, clicker):
    menu_id = await approval_menu(db)
    await bot.store.set(GUILD, APPROVAL_CHANNEL_KEY, STAFF_CHANNEL)
    bot.guard = FakeGuard(allowed=TEST_CHANNEL)

    interaction = await pick(bot, db, menu_id, clicker, ["10"])

    assert cards_in(bot, STAFF_CHANNEL) == [] and len(cards_in(bot, TEST_CHANNEL)) == 1
    assert "Test mode is on" in interaction.sent
    cur = await db.conn.execute("SELECT details FROM action_log WHERE kind = 'role.requested'")
    assert '"card": "test_channel"' in (await cur.fetchone())["details"]


async def test_a_card_that_cannot_be_posted_is_a_failure_line_not_a_silent_one(bot, db, clicker):
    menu_id = await approval_menu(db)
    bot.guild.get_channel(TEST_CHANNEL).send_raises = RuntimeError("discord said no")

    interaction = await pick(bot, db, menu_id, clicker, ["10"])

    assert "could not post the card" in interaction.sent
    assert (await requests_in(db))[0]["status"] == "pending"
    assert "role.request_card_failed" in await action_kinds(db)


async def test_no_approval_channel_at_all_is_named_rather_than_guessed(bot, db, clicker):
    menu_id = await approval_menu(db)
    await bot.store.set(GUILD, "staff_channel_id", 4040)

    await pick(bot, db, menu_id, clicker, ["10"])

    cur = await db.conn.execute(
        "SELECT details FROM action_log WHERE kind = 'role.request_card_failed'"
    )
    assert '"reason": "no_approval_channel"' in (await cur.fetchone())["details"]


async def test_giving_up_a_held_role_on_an_approval_menu_needs_nobodys_permission(
    bot, db, monkeypatch
):
    monkeypatch.setattr(discord, "Member", FakeMember)
    menu_id = await approval_menu(db)
    member = FakeMember(bot.guild, user_id=900, roles=(10, 99))

    interaction = await pick(bot, db, menu_id, member, [])

    assert member.edits == [[99]]
    assert "Removed: Runner" in interaction.sent
    assert await requests_in(db) == []


async def test_a_grant_is_written_for_an_ordinary_menu_pick_on_a_timed_menu(bot, db, clicker):
    menu_id = await create_menu(db, GUILD, "timed", "Timed", None, "multiple", expires_days=7)
    await add_option(db, menu_id, 1, "He/Him")

    await pick(bot, db, menu_id, clicker, ["1"])

    grant = await grants.open_grant(db, GUILD, clicker.id, 1)
    assert grant["source"] == "menu" and grant["expires_at"] is not None


async def test_giving_a_menu_role_back_closes_its_grant(bot, db, clicker):
    menu_id = await create_menu(db, GUILD, "timed", "Timed", None, "multiple", expires_days=7)
    await add_option(db, menu_id, 1, "He/Him")
    await pick(bot, db, menu_id, clicker, ["1"])

    await pick(bot, db, menu_id, clicker, [])

    assert await grants.open_grant(db, GUILD, clicker.id, 1) is None
    assert (await grants.grants_for(db, GUILD))[0]["removed_reason"] == "given_up"


async def test_a_staff_assign_starts_the_menus_clock(bot, db, lead):
    menu_id = await create_menu(db, GUILD, "timed", "Timed", None, "staff", expires_days=7)
    await add_option(db, menu_id, 10, "Runner")
    target = FakeMember(bot.guild, user_id=900)
    select = assign_pick(menu_id, await get_options(db, menu_id), target, remove=False)
    select._values = ["10"]

    await select.callback(FakeInteraction(bot, lead))

    grant = await grants.open_grant(db, GUILD, 900, 10)
    assert grant["source"] == "staff" and grant["granted_by"] == lead.id


async def test_a_staff_assign_still_lands_while_the_mode_is_off(bot, db, lead):
    """Pings remake §C6: `rolemenu_mode` off used to refuse this in words, which left the
    staff-assigned sets with no door at all once the owner turned the menus off."""
    await bot.store.set(GUILD, MODE_KEY, "off")
    menu_id = await create_menu(db, GUILD, "timed", "Timed", None, "staff", expires_days=7)
    await add_option(db, menu_id, 10, "Runner")
    target = FakeMember(bot.guild, user_id=902)
    select = assign_pick(menu_id, await get_options(db, menu_id), target, remove=False)
    select._values = ["10"]

    interaction = FakeInteraction(bot, lead)
    await select.callback(interaction)

    assert ROLE_MENUS_OFF not in interaction.sent
    assert await grants.open_grant(db, GUILD, 902, 10) is not None


async def test_a_deleted_menu_takes_its_pending_requests_with_it(bot, db, clicker):
    menu_id = await approval_menu(db)
    await pick(bot, db, menu_id, clicker, ["10"])

    await delete_menu(db, GUILD, "runner-status")

    assert (await requests_in(db))[0]["status"] == "withdrawn"


async def test_a_panel_says_what_picking_a_role_will_actually_do(db):
    menu_id = await approval_menu(db, expires=7)
    menu = await get_menu(db, GUILD, "runner-status")

    embed = panel_embed(menu, await get_options(db, menu_id))

    note = embed.fields[1].value
    assert "asks staff first" in note and "lasts 7 day(s)" in note


def test_a_menu_row_without_the_new_columns_still_renders():
    menu = {"title": "Pronouns", "description": None}
    embed = panel_embed(menu, [{"role_id": 1, "label": "He/Him", "emoji": None}])
    assert len(embed.fields) == 1
    assert needs_approval(menu) is False and expires_days_of(menu) is None
    assert retry_days_of(menu) == 7


def test_days_that_mean_no_end_date_all_read_the_same_way():
    assert positive_days(7) == 7
    assert positive_days(0) is None and positive_days(-1) is None
    assert positive_days(None) is None and positive_days("soon") is None


async def test_an_update_leaves_the_columns_it_was_not_given(db):
    await create_menu(db, GUILD, "m", "M", approval=True, expires_days=7, retry_days=14)

    await update_menu(db, GUILD, "m", title="Menu")

    menu = await get_menu(db, GUILD, "m")
    assert menu["title"] == "Menu"
    assert needs_approval(menu) and expires_days_of(menu) == 7 and retry_days_of(menu) == 14
    assert UNSET is not None


async def test_a_grant_that_is_due_comes_off_and_the_member_is_told(bot, db):
    member = FakeMember(bot.guild, user_id=900, roles=(10, 99))
    await grants.add_grant(db, GUILD, 900, 10, "approval", until="2020-01-01T00:00:00+00:00")

    await RoleMenus(bot).run_due_grants()

    assert member.edits == [[99]]
    assert await grants.open_grant(db, GUILD, 900, 10) is None
    assert (await grants.grants_for(db, GUILD))[0]["removed_reason"] == "expired"
    assert member.dms and "ran out today" in member.dms[0]
    assert "role.expired" in await action_kinds(db)


async def test_a_grant_whose_role_already_went_is_closed_without_an_edit(bot, db):
    member = FakeMember(bot.guild, user_id=900, roles=(99,))
    await grants.add_grant(db, GUILD, 900, 10, "approval", until="2020-01-01T00:00:00+00:00")

    await RoleMenus(bot).run_due_grants()

    assert member.edits == []
    assert await grants.open_grant(db, GUILD, 900, 10) is None
    assert "role.expired" in await action_kinds(db)


async def test_a_refused_removal_leaves_the_grant_open_for_the_next_pass(bot, db):
    member = FakeMember(bot.guild, user_id=900, roles=(10,))
    member.edit_raises = discord.HTTPException(_Refused(403), "no")
    await grants.add_grant(db, GUILD, 900, 10, "approval", until="2020-01-01T00:00:00+00:00")

    await RoleMenus(bot).run_due_grants()

    assert await grants.open_grant(db, GUILD, 900, 10) is not None
    kinds = await action_kinds(db)
    assert "role.expire_failed" in kinds and "role.expired" not in kinds


async def test_a_grant_for_a_member_who_left_is_closed_rather_than_retried_forever(bot, db):
    await grants.add_grant(db, GUILD, 900, 10, "approval", until="2020-01-01T00:00:00+00:00")

    await RoleMenus(bot).run_due_grants()

    assert await grants.open_grant(db, GUILD, 900, 10) is None


async def test_a_role_added_by_hand_is_logged_and_settles_the_request(bot, db, clicker):
    menu_id = await approval_menu(db, expires=7)
    await pick(bot, db, menu_id, clicker, ["10"])
    before = FakeMember(bot.guild, user_id=900, roles=(99,))
    after = FakeMember(bot.guild, user_id=900, roles=(99, 10))

    await RoleMenus(bot).on_member_update(before, after)

    assert "role.changed_by_hand" in await action_kinds(db)
    assert (await requests_in(db))[0]["status"] == "granted_by_hand"
    grant = await grants.open_grant(db, GUILD, 900, 10)
    assert grant["source"] == "manual" and grant["expires_at"] is None
    assert cards_in(bot)[0].kwargs["view"] is None
    assert await timed_menu_owns(db, GUILD, 10) is True


async def test_a_role_the_bot_added_itself_is_not_reported_as_by_hand(bot, db, clicker, lead):
    menu_id = await approval_menu(db)
    await pick(bot, db, menu_id, clicker, ["10"])
    await click(bot, 1, "approve", lead)
    before = FakeMember(bot.guild, user_id=900, roles=(99,))
    after = FakeMember(bot.guild, user_id=900, roles=(99, 10))

    await RoleMenus(bot).on_member_update(before, after)

    assert "role.changed_by_hand" not in await action_kinds(db)


async def test_a_role_taken_off_by_hand_closes_its_grant(bot, db):
    await grants.add_grant(db, GUILD, 900, 10, "approval", until=grants.expires_at(7))
    before = FakeMember(bot.guild, user_id=900, roles=(10,))
    after = FakeMember(bot.guild, user_id=900, roles=())

    await RoleMenus(bot).on_member_update(before, after)

    assert await grants.open_grant(db, GUILD, 900, 10) is None
    assert (await grants.grants_for(db, GUILD))[0]["removed_reason"] == "by_hand"
    assert "role.changed_by_hand" in await action_kinds(db)


async def test_a_manual_add_of_an_untimed_role_keeps_no_clock(bot, db):
    menu_id = await create_menu(db, GUILD, "plain", "Plain")
    await add_option(db, menu_id, 10, "Runner")
    before = FakeMember(bot.guild, user_id=900, roles=())
    after = FakeMember(bot.guild, user_id=900, roles=(10,))

    await RoleMenus(bot).on_member_update(before, after)

    assert await grants.open_grant(db, GUILD, 900, 10) is None
    assert await timed_menu_owns(db, GUILD, 10) is False


async def test_nothing_is_logged_when_no_roles_moved(bot, db):
    member = FakeMember(bot.guild, user_id=900, roles=(10,))

    await RoleMenus(bot).on_member_update(member, member)

    assert await action_kinds(db) == []


class FakeAuditEntry:
    def __init__(self, target, user):
        self.target = target
        self.user = user


async def test_the_audit_log_names_the_actor_when_black_bloc_may_read_it(bot, lead):
    member = FakeMember(bot.guild, user_id=900)
    bot.guild.me = SimpleNamespace(guild_permissions=SimpleNamespace(view_audit_log=True))
    bot.guild.audit_entries = [FakeAuditEntry(member, lead)]

    assert await audit_actor(bot.guild, member) is lead


async def test_without_the_permission_the_actor_is_none_rather_than_a_guess(bot, lead):
    member = FakeMember(bot.guild, user_id=900)
    bot.guild.me = SimpleNamespace(guild_permissions=SimpleNamespace(view_audit_log=False))
    bot.guild.audit_entries = [FakeAuditEntry(member, lead)]

    assert await audit_actor(bot.guild, member) is None
    bot.guild.me = None
    assert await audit_actor(bot.guild, member) is None


async def test_the_sweep_corrects_records_and_never_touches_the_member(bot, db, clicker):
    menu_id = await approval_menu(db)
    await pick(bot, db, menu_id, clicker, ["11"])
    await grants.add_grant(db, GUILD, 900, 10, "approval")
    clicker.roles = [FakeRole(99), FakeRole(11)]

    await RoleMenus(bot).reconcile_records()

    assert clicker.edits == []
    assert await grants.open_grant(db, GUILD, 900, 10) is None
    assert (await requests_in(db))[0]["status"] == "granted_by_hand"
    assert "role.reconciled" in await action_kinds(db)


async def test_the_sweep_says_nothing_when_the_records_already_match(bot, db, clicker):
    await grants.add_grant(db, GUILD, 900, 99, "approval")

    await RoleMenus(bot).reconcile_records()

    assert "role.reconciled" not in await action_kinds(db)


async def test_the_sweep_leaves_an_unavailable_guild_alone(bot, db):
    FakeMember(bot.guild, user_id=900, roles=())
    await grants.add_grant(db, GUILD, 900, 10, "approval")
    bot.guild.unavailable = True

    await RoleMenus(bot).reconcile_records()

    assert await grants.open_grant(db, GUILD, 900, 10) is not None


def test_the_card_goes_to_the_test_channel_only_while_the_guard_would_refuse(bot):
    staff = bot.guild.get_channel(STAFF_CHANNEL)

    assert card_target(bot, staff) == (staff, "approval_channel")
    assert card_target(bot, None) == (None, "no_approval_channel")

    bot.guard = FakeGuard(allowed=TEST_CHANNEL)
    assert card_target(bot, staff)[1] == "test_channel"
    assert card_target(bot, bot.guild.get_channel(TEST_CHANNEL))[1] == "approval_channel"


def test_the_request_buttons_survive_a_restart_by_their_custom_id():
    button = RequestButton(12, "approve")

    assert button.custom_id == "rolereq:12:approve"
    match = button.template.fullmatch("rolereq:12:deny")
    assert match["request_id"] == "12" and match["action"] == "deny"
    assert re.fullmatch(button.template, "rolereq:12:maybe") is None
    assert issubclass(RequestDenyModal, discord.ui.Modal)
    assert issubclass(RequestApproveModal, discord.ui.Modal)


def test_the_expiry_loop_reports_its_own_health(bot):
    cog = RoleMenus(bot)

    assert cog.loop_health("_expiry_loop") == (None, None)
    assert cog.loop_health("not_a_loop_here") == (None, None)

    cog.last_ok_at["expiry"] = "2026-08-27T00:00:00+00:00"
    cog.last_error["expiry"] = "boom"
    assert cog.loop_health("_expiry_loop") == ("2026-08-27T00:00:00+00:00", "boom")


# --- the panel (wave 3) --------------------------------------------------------------------------


def labels(view):
    return [one.label for one in view.children if getattr(one, "label", None)]


def button(view, label):
    return next(one for one in view.children if getattr(one, "label", None) == label)


def picker(view, placeholder):
    return next(
        one for one in view.children if getattr(one, "placeholder", None) == placeholder
    )


def has_picker(view, placeholder):
    return any(getattr(one, "placeholder", None) == placeholder for one in view.children)


async def press(interaction, label, view=None):
    control = button(view if view is not None else interaction.view, label)
    await control.callback(interaction)


async def choose(interaction, placeholder, values, view=None):
    control = picker(view if view is not None else interaction.view, placeholder)
    control._values = list(values)
    await control.callback(interaction)


async def open_the_panel(bot, who):
    interaction = FakeInteraction(bot, who)
    await RoleMenus.rolemenu_panel_command.callback(RoleMenus(bot), interaction)
    return interaction


async def open_a_menu(bot, who, name):
    interaction = await open_the_panel(bot, who)
    await choose(interaction, menus.MENU_PICK, [name])
    return interaction


async def test_rolemenu_opens_one_ephemeral_panel_with_the_root_moves(bot, db, lead):
    await self_serve_menu(db)

    interaction = await open_the_panel(bot, lead)

    assert interaction.response.messages[0]["ephemeral"] is True
    assert labels(interaction.view) == [
        "New menu",
        "Seed the defaults",
        "Grants…",
        menus.MODE_OFF_LABEL,
        "Logs",
        "Refresh",
    ]
    assert has_picker(interaction.view, menus.MENU_PICK)
    assert "**pronouns** — 2 role(s), multiple, not posted" in interaction.body


async def test_rolemenu_is_staff_only_and_never_leaves_a_dead_button(bot, db):
    stranger = FakeMember(bot.guild, user_id=901)

    interaction = await open_the_panel(bot, stranger)

    assert "staff only" in interaction.sent
    assert interaction.view is None


@pytest.mark.parametrize("picking", [True, False])
async def test_the_root_renders_its_row_and_no_other_in_either_mode(bot, db, lead, picking):
    """S1/S2/S3 crossed with the mode: the mode never takes a control off the root."""
    await bot.store.set(GUILD, MODE_KEY, "on" if picking else "off")

    empty = await open_the_panel(bot, lead)
    assert not has_picker(empty.view, menus.MENU_PICK)
    assert menus.NO_MENUS_LINE in empty.body
    assert "Waiting on staff" not in " ".join(labels(empty.view))

    menu_id = await approval_menu(db)
    listed = await open_the_panel(bot, lead)
    assert has_picker(listed.view, menus.MENU_PICK)
    assert "Waiting on staff" not in " ".join(labels(listed.view))

    await grants.create_request(db, GUILD, menu_id, 900, 10)
    waiting = await open_the_panel(bot, lead)
    assert "Waiting on staff (1)…" in labels(waiting.view)

    for one in (empty, listed, waiting):
        assert ((menus.PICKING_IS_OFF in one.body) is not picking)
        wanted = menus.MODE_OFF_LABEL if picking else menus.MODE_ON_LABEL
        assert wanted in labels(one.view)


async def test_the_menu_card_says_what_rolemenu_show_used_to_print(bot, db, lead):
    await self_serve_menu(db)

    interaction = await open_a_menu(bot, lead, "pronouns")

    assert "**pronouns** — Pronouns (multiple, not posted)" in interaction.body
    assert "• He/Him — <@&1>" in interaction.body
    assert labels(interaction.view) == [
        "Add a role…",
        "Words…",
        "Rules…",
        menus.APPROVAL_ON_LABEL,
        menus.POST_LABEL,
        "Hand roles out…",
        "Delete it",
        "Back",
        "Refresh",
    ]


async def test_post_it_is_missing_on_a_staff_menu_and_the_card_says_why(bot, db, lead):
    await staff_menu(db)

    interaction = await open_a_menu(bot, lead, "runner-status")

    assert menus.POST_LABEL not in labels(interaction.view)
    assert menus.NOBODY_PICKS_THESE in interaction.body
    assert "Hand roles out…" in labels(interaction.view)


async def test_post_it_goes_while_the_mode_is_off_and_handing_out_stays(bot, db, lead):
    """Pings remake §C6: the mode is about members picking for themselves, so it takes
    **Post it** away and leaves staff's **Hand roles out…** exactly where it was."""
    await self_serve_menu(db)
    await bot.store.set(GUILD, MODE_KEY, "off")

    interaction = await open_a_menu(bot, lead, "pronouns")

    assert menus.POST_LABEL not in labels(interaction.view)
    assert "Hand roles out…" in labels(interaction.view)
    assert "Words…" in labels(interaction.view) and "Delete it" in labels(interaction.view)
    assert menus.PICKING_IS_OFF in interaction.body


async def test_an_empty_menu_offers_no_post_and_no_way_to_remove_a_role(bot, db, lead):
    await create_menu(db, GUILD, "empty", "Nothing yet")

    interaction = await open_a_menu(bot, lead, "empty")

    assert menus.POST_LABEL not in labels(interaction.view)
    assert not has_picker(interaction.view, menus.REMOVE_PICK)
    assert menus.NO_ROLES_YET in interaction.body


async def test_a_full_menu_stops_offering_another_role_and_says_so(bot, db, lead):
    menu_id = await create_menu(db, GUILD, "full", "Full")
    for role_id in range(OPTIONS_MAX):
        await add_option(db, menu_id, role_id + 1, f"role {role_id}")

    interaction = await open_a_menu(bot, lead, "full")

    assert "Add a role…" not in labels(interaction.view)
    assert "Split it into a second menu" in interaction.body


async def test_take_it_down_renders_only_while_a_panel_is_up(bot, db, lead):
    menu_id = await self_serve_menu(db)
    before = await open_a_menu(bot, lead, "pronouns")
    assert "Take it down" not in labels(before.view)

    await set_message(db, menu_id, TEST_CHANNEL, 5)
    after = await open_a_menu(bot, lead, "pronouns")

    assert "Take it down" in labels(after.view)
    assert menus.MOVE_LABEL in labels(after.view)


async def test_taking_the_panel_down_leaves_the_menu_and_everybody_s_roles(bot, db, lead):
    menu_id = await self_serve_menu(db)
    channel = bot.guild.get_channel(TEST_CHANNEL)
    message = await channel.send(content="panel")
    await set_message(db, menu_id, TEST_CHANNEL, message.id)
    interaction = await open_a_menu(bot, lead, "pronouns")

    await press(interaction, "Take it down")

    assert "panel is down" in interaction.sent
    assert channel.messages == []
    menu = await get_menu(db, GUILD, "pronouns")
    assert menu["message_id"] is None and menu["channel_id"] == TEST_CHANNEL
    assert "role_menu.unposted" in await action_kinds(db)


async def test_posting_asks_where_and_puts_the_panel_in_the_channel_picked(bot, db, lead):
    await self_serve_menu(db)
    interaction = await open_a_menu(bot, lead, "pronouns")

    await press(interaction, menus.POST_LABEL)
    assert has_picker(interaction.view, cog_module.WHERE_PICK)
    await choose(interaction, cog_module.WHERE_PICK, [SimpleNamespace(id=TEST_CHANNEL)])

    channel = bot.guild.get_channel(TEST_CHANNEL)
    assert len(channel.messages) == 1
    assert (await get_menu(db, GUILD, "pronouns"))["message_id"] == channel.messages[0].id
    assert "role_menu.post" in await action_kinds(db)


async def test_posting_anywhere_but_the_test_channel_is_refused_in_words(bot, db, lead):
    await self_serve_menu(db)
    bot.guard = FakeGuard(allowed=TEST_CHANNEL)
    interaction = await open_a_menu(bot, lead, "pronouns")

    await press(interaction, menus.POST_LABEL)
    await choose(interaction, cog_module.WHERE_PICK, [SimpleNamespace(id=LOG_CHANNEL)])

    assert interaction.sent == "test mode"
    assert bot.guild.get_channel(LOG_CHANNEL).messages == []
    assert "role_menu.post" not in await action_kinds(db)


async def test_adding_a_role_black_bloc_cannot_hand_out_is_refused_in_words(bot, db, lead):
    await self_serve_menu(db)
    interaction = await open_a_menu(bot, lead, "pronouns")
    await press(interaction, "Add a role…")

    class Above(FakeRole):
        def is_assignable(self):
            return False

    bot.guild.get_role = lambda role_id: Above(role_id)
    await choose(interaction, menus.ROLE_PICK, [SimpleNamespace(id=42)])
    await press(interaction, "Use the role's own name")

    assert "cannot hand out" in interaction.sent
    menu = await get_menu(db, GUILD, "pronouns")
    assert 42 not in [row["role_id"] for row in await get_options(db, menu["id"])]


async def test_adding_a_role_by_its_own_name_lands_and_leaves_one_log_row(bot, db, lead):
    await self_serve_menu(db)
    interaction = await open_a_menu(bot, lead, "pronouns")

    await press(interaction, "Add a role…")
    await choose(interaction, menus.ROLE_PICK, [SimpleNamespace(id=42)])
    await press(interaction, "Use the role's own name")

    menu = await get_menu(db, GUILD, "pronouns")
    rows = await get_options(db, menu["id"])
    assert (42, "role-42") in [(row["role_id"], row["label"]) for row in rows]
    assert (await action_kinds(db)).count("role_menu.option_added") == 1


async def test_removing_a_role_says_nobody_loses_the_one_they_have(bot, db, lead):
    await self_serve_menu(db)
    interaction = await open_a_menu(bot, lead, "pronouns")

    await choose(interaction, menus.REMOVE_PICK, ["1"])

    assert "Nobody loses the role they already have" in interaction.sent
    menu = await get_menu(db, GUILD, "pronouns")
    assert [row["role_id"] for row in await get_options(db, menu["id"])] == [2]
    assert "role_menu.option_removed" in await action_kinds(db)


async def test_taking_roles_back_renders_only_when_they_hold_one(bot, db, lead):
    await staff_menu(db)
    FakeMember(bot.guild, user_id=900, display_name="Bo")
    FakeMember(bot.guild, user_id=901, display_name="Cy", roles=(10,))
    interaction = await open_a_menu(bot, lead, "runner-status")
    await press(interaction, "Hand roles out…")

    await choose(interaction, menus.WHOSE_ROLES, [SimpleNamespace(id=900)])
    assert "Take roles back…" not in labels(interaction.view)
    assert "Give them roles…" in labels(interaction.view)

    await choose(interaction, menus.WHOSE_ROLES, [SimpleNamespace(id=901)])
    assert "Take roles back…" in labels(interaction.view)


async def test_the_mode_button_flips_it_and_says_what_it_will_do(bot, db, lead):
    interaction = await open_the_panel(bot, lead)

    await press(interaction, menus.MODE_OFF_LABEL)

    assert bot.store.get(GUILD, MODE_KEY) == "off"
    assert "**off**" in interaction.sent
    assert "role_menu.mode" in await action_kinds(db)
    assert menus.MODE_ON_LABEL in labels(interaction.view)


async def test_a_new_menu_arrives_from_a_modal_and_a_bad_mode_saves_nothing(bot, db, lead):
    interaction = await open_the_panel(bot, lead)
    await press(interaction, "New menu")
    modal = interaction.response.modals[-1]

    modal.name._value = "colours"
    modal.heading._value = "Colours"
    modal.description._value = ""
    modal.mode._value = "sometimes"
    await modal.on_submit(interaction)

    assert "is not a way a role menu can work" in interaction.sent
    assert await get_menu(db, GUILD, "colours") is None

    modal.mode._value = "single"
    await modal.on_submit(interaction)

    assert (await get_menu(db, GUILD, "colours"))["mode"] == "single"
    assert "role_menu.create" in await action_kinds(db)


async def test_a_name_already_taken_is_refused_in_words(bot, db, lead):
    await self_serve_menu(db)
    interaction = await open_the_panel(bot, lead)
    await press(interaction, "New menu")
    modal = interaction.response.modals[-1]
    modal.name._value = "pronouns"
    modal.heading._value = "Again"
    modal.description._value = ""
    modal.mode._value = ""

    await modal.on_submit(interaction)

    assert "already has a role menu called **pronouns**" in interaction.sent
    assert len(await list_menus(db, GUILD)) == 1


async def test_the_rules_modal_refuses_a_word_where_a_number_belongs(bot, db, lead):
    await self_serve_menu(db)
    interaction = await open_a_menu(bot, lead, "pronouns")
    await press(interaction, "Rules…")
    modal = interaction.response.modals[-1]
    modal.expires._value = "a week"
    modal.retry._value = "7"

    await modal.on_submit(interaction)

    assert "not a whole number of days" in interaction.sent
    assert expires_days_of(await get_menu(db, GUILD, "pronouns")) is None


async def test_the_rules_modal_sets_the_clocks_and_clears_them_with_zero(bot, db, lead):
    await self_serve_menu(db)
    interaction = await open_a_menu(bot, lead, "pronouns")
    await press(interaction, "Rules…")
    modal = interaction.response.modals[-1]
    modal.expires._value = "7"
    modal.retry._value = "14"
    await modal.on_submit(interaction)

    menu = await get_menu(db, GUILD, "pronouns")
    assert expires_days_of(menu) == 7 and retry_days_of(menu) == 14
    assert "role_menu.edit" in await action_kinds(db)

    modal.expires._value = "0"
    await modal.on_submit(interaction)

    assert expires_days_of(await get_menu(db, GUILD, "pronouns")) is None


async def test_the_approval_button_turns_it_on_and_then_off_again(bot, db, lead):
    await self_serve_menu(db)
    interaction = await open_a_menu(bot, lead, "pronouns")

    await press(interaction, menus.APPROVAL_ON_LABEL)

    assert needs_approval(await get_menu(db, GUILD, "pronouns"))
    assert menus.APPROVAL_OFF_LABEL in labels(interaction.view)

    await press(interaction, menus.APPROVAL_OFF_LABEL)

    assert not needs_approval(await get_menu(db, GUILD, "pronouns"))


async def test_an_edit_refreshes_a_posted_panel_rather_than_posting_a_second(bot, db, lead):
    """Fork F-R3(a): `post_panel` edits the message it already has, so this cannot double-post."""
    menu_id = await self_serve_menu(db)
    channel = bot.guild.get_channel(TEST_CHANNEL)
    message = await channel.send(content="panel")
    await set_message(db, menu_id, TEST_CHANNEL, message.id)
    interaction = await open_a_menu(bot, lead, "pronouns")

    await press(interaction, "Words…")
    modal = interaction.response.modals[-1]
    modal.heading._value = "Your pronouns"
    modal.description._value = ""
    await modal.on_submit(interaction)

    assert len(channel.messages) == 1
    assert channel.messages[0].kwargs["embed"].title == "Your pronouns"
    assert (await action_kinds(db)).count("role_menu.post") == 0


async def test_deleting_a_menu_asks_first_and_keeping_it_changes_nothing(bot, db, lead):
    await self_serve_menu(db)
    interaction = await open_a_menu(bot, lead, "pronouns")

    await press(interaction, "Delete it")
    assert labels(interaction.view) == ["Yes, delete it", "Keep it"]
    await press(interaction, "Keep it")

    assert await get_menu(db, GUILD, "pronouns") is not None

    await press(interaction, "Delete it")
    await press(interaction, "Yes, delete it")

    assert await get_menu(db, GUILD, "pronouns") is None
    assert "role_menu.delete" in await action_kinds(db)


async def test_seeding_asks_first_and_says_what_it_did(bot, db, lead):
    interaction = await open_the_panel(bot, lead)

    await press(interaction, "Seed the defaults")
    assert labels(interaction.view) == ["Yes, make them", "Leave it"]
    await press(interaction, "Yes, make them")

    assert "Created: pronouns" in interaction.sent
    assert len(await list_menus(db, GUILD)) == len(SEED)
    assert "role_menu.seeded" in await action_kinds(db)


# --- the grants audit (design §I-amend) ------------------------------------------------------


async def test_the_grants_sub_panel_opens_as_an_audit_soonest_first(bot, db, lead):
    FakeMember(bot.guild, user_id=900, display_name="Bo")
    FakeMember(bot.guild, user_id=901, display_name="Cy")
    later = await grants.add_grant(db, GUILD, 900, 1, "staff", until=grants.expires_at(9))
    sooner = await grants.add_grant(db, GUILD, 901, 2, "staff", until=grants.expires_at(1))
    forever = await grants.add_grant(db, GUILD, 901, 3, "staff")
    interaction = await open_the_panel(bot, lead)

    await press(interaction, "Grants…")

    assert "**3** timed role(s) running" in interaction.body
    assert interaction.body.index("<@901> · <@&2>") < interaction.body.index("<@900> · <@&1>")
    assert menus.NO_END_DATE in interaction.body
    assert [one.value for one in picker(interaction.view, menus.GRANT_PICK).options] == [
        str(sooner),
        str(later),
        str(forever),
    ]


async def test_whose_roles_narrows_the_audit_to_one_member(bot, db, lead):
    FakeMember(bot.guild, user_id=900, display_name="Bo")
    FakeMember(bot.guild, user_id=901, display_name="Cy")
    await grants.add_grant(db, GUILD, 900, 1, "staff", until=grants.expires_at(9))
    mine = await grants.add_grant(db, GUILD, 901, 2, "staff", until=grants.expires_at(1))
    interaction = await open_the_panel(bot, lead)
    await press(interaction, "Grants…")

    await choose(interaction, menus.WHOSE_ROLES, [SimpleNamespace(id=901)])

    assert "**1** timed role(s) running for that member" in interaction.body
    assert [one.value for one in picker(interaction.view, menus.GRANT_PICK).options] == [
        str(mine)
    ]


async def test_an_empty_audit_says_so_rather_than_offering_a_dead_select(bot, db, lead):
    interaction = await open_the_panel(bot, lead)

    await press(interaction, "Grants…")

    assert menus.NO_GRANTS in interaction.body
    assert not has_picker(interaction.view, menus.GRANT_PICK)
    assert "Give somebody a role…" in labels(interaction.view)


async def test_push_it_back_is_absent_on_a_grant_with_no_end_date(bot, db, lead):
    FakeMember(bot.guild, user_id=900, display_name="Bo")
    forever = await grants.add_grant(db, GUILD, 900, 1, "staff")
    timed = await grants.add_grant(db, GUILD, 900, 2, "staff", until=grants.expires_at(3))
    interaction = await open_the_panel(bot, lead)
    await press(interaction, "Grants…")

    await choose(interaction, menus.GRANT_PICK, [str(forever)])
    assert labels(interaction.view) == ["End it now", "Back"]

    await press(interaction, "Back")
    await choose(interaction, menus.GRANT_PICK, [str(timed)])
    assert labels(interaction.view) == ["Push it back…", "End it now", "Back"]


async def test_a_closed_grant_offers_no_move_at_all(bot, db, lead):
    FakeMember(bot.guild, user_id=900, display_name="Bo")
    grant_id = await grants.add_grant(db, GUILD, 900, 1, "staff", until=grants.expires_at(3))
    await grants.end_grant(db, grant_id, grants.ENDED_BY_STAFF)
    interaction = await open_the_panel(bot, lead)
    await press(interaction, "Grants…")
    view = a_panel(cog_module.GRANTS_VIEW)

    await cog_module.open_grant(interaction, grant_id, view)

    assert labels(interaction.view) == ["Back"]


async def test_end_it_now_asks_first_then_takes_the_role_back_without_a_dm(bot, db, lead):
    """The `/role revoke` four docs promised: a staff reversal, logged, and no DM."""
    member = FakeMember(bot.guild, user_id=900, display_name="Bo", roles=(1, 99))
    grant_id = await grants.add_grant(db, GUILD, 900, 1, "staff", until=grants.expires_at(3))
    interaction = await open_the_panel(bot, lead)
    await press(interaction, "Grants…")
    await choose(interaction, menus.GRANT_PICK, [str(grant_id)])

    await press(interaction, "End it now")
    assert labels(interaction.view) == ["Yes, take it back", "Leave it"]
    await press(interaction, "Yes, take it back")

    assert member.edits == [[99]]
    assert member.dms == []
    row = await grants.get_grant(db, grant_id)
    assert row["removed_at"] and row["removed_reason"] == "ended_by_staff"
    assert "role.ended" in await action_kinds(db)


async def test_leaving_a_grant_alone_changes_nothing(bot, db, lead):
    member = FakeMember(bot.guild, user_id=900, display_name="Bo", roles=(1,))
    grant_id = await grants.add_grant(db, GUILD, 900, 1, "staff", until=grants.expires_at(3))
    interaction = await open_the_panel(bot, lead)
    await press(interaction, "Grants…")
    await choose(interaction, menus.GRANT_PICK, [str(grant_id)])

    await press(interaction, "End it now")
    await press(interaction, "Leave it")

    assert member.edits == []
    assert (await grants.get_grant(db, grant_id))["removed_at"] is None


async def test_back_from_grants_opened_on_rolemenu_still_lands_on_rolemenu(bot, db, lead):
    interaction = await open_the_panel(bot, lead)
    await press(interaction, "Grants…")
    assert interaction.view.home is None

    await press(interaction, "Back")

    assert interaction.embed.title == menus.PANEL_TITLE


async def test_a_door_from_another_panel_keeps_its_way_home_through_a_confirm(bot, db, lead):
    """`/mod` ▸ Role grants… (owner, 2026-09-25 "B"): the same console, Back goes to its door."""
    member = FakeMember(bot.guild, user_id=900, display_name="Bo", roles=(1, 99))
    grant_id = await grants.add_grant(db, GUILD, 900, 1, "staff", until=grants.expires_at(3))
    came_home = []

    async def home(pressed, view):
        came_home.append(view.where)

    interaction = FakeInteraction(bot, lead)
    await cog_module.open_grants_from(interaction, None, home)
    assert interaction.embed.title == menus.GRANTS_TITLE
    await choose(interaction, menus.GRANT_PICK, [str(grant_id)])
    await press(interaction, "End it now")
    await press(interaction, "Yes, take it back")
    await press(interaction, "Back")
    assert came_home == []
    assert interaction.embed.title == menus.GRANTS_TITLE

    await press(interaction, "Back")

    assert came_home == ["grants"]
    assert member.edits == [[99]]


async def test_the_other_door_refuses_a_member_in_words(bot, db, lead):
    somebody = FakeMember(bot.guild, user_id=950, display_name="Di")
    interaction = FakeInteraction(bot, somebody)

    await cog_module.open_grants_from(interaction, None, None)

    assert "staff only" in interaction.sent
    assert interaction.view is None


async def test_push_it_back_moves_the_end_date_from_the_one_it_had(bot, db, lead):
    FakeMember(bot.guild, user_id=900, display_name="Bo", roles=(1,))
    grant_id = await grants.add_grant(db, GUILD, 900, 1, "staff", until=grants.expires_at(3))
    interaction = await open_the_panel(bot, lead)
    await press(interaction, "Grants…")
    await choose(interaction, menus.GRANT_PICK, [str(grant_id)])

    await press(interaction, "Push it back…")
    modal = interaction.response.modals[-1]
    modal.days._value = "4"
    await modal.on_submit(interaction)

    row = await grants.get_grant(db, grant_id)
    assert (grants.parse_ts(row["expires_at"]) - datetime.now(UTC)).days == 6
    assert "role.extended" in await action_kinds(db)


async def test_giving_somebody_a_role_needs_who_and_which_before_it_asks_how_long(bot, db, lead):
    member = FakeMember(bot.guild, user_id=900, display_name="Bo")
    interaction = await open_the_panel(bot, lead)
    await press(interaction, "Grants…")

    await press(interaction, "Give somebody a role…")
    assert "How long for…" not in labels(interaction.view)

    await choose(interaction, menus.WHO_GETS_IT, [SimpleNamespace(id=900)])
    assert "How long for…" not in labels(interaction.view)

    await choose(interaction, menus.WHICH_ROLE, [SimpleNamespace(id=5)])
    assert "How long for…" in labels(interaction.view)

    await press(interaction, "How long for…")
    modal = interaction.response.modals[-1]
    modal.days._value = "7"
    await modal.on_submit(interaction)

    assert member.edits == [[5]]
    row = await grants.open_grant(db, GUILD, 900, 5)
    assert row["expires_at"] is not None and row["granted_by"] == lead.id
    assert "role.granted" in await action_kinds(db)


async def test_a_grant_of_zero_days_never_runs_out(bot, db, lead):
    """Fork F-R2(a): the Days modal takes 0, exactly as the website always has."""
    FakeMember(bot.guild, user_id=900, display_name="Bo")
    interaction = await open_the_panel(bot, lead)
    await press(interaction, "Grants…")
    await press(interaction, "Give somebody a role…")
    await choose(interaction, menus.WHO_GETS_IT, [SimpleNamespace(id=900)])
    await choose(interaction, menus.WHICH_ROLE, [SimpleNamespace(id=5)])

    await press(interaction, "How long for…")
    modal = interaction.response.modals[-1]
    modal.days._value = "0"
    await modal.on_submit(interaction)

    assert (await grants.open_grant(db, GUILD, 900, 5))["expires_at"] is None


async def test_giving_a_role_out_is_refused_outside_the_test_channel(bot, db, lead):
    FakeMember(bot.guild, user_id=900, display_name="Bo")
    bot.guard = FakeGuard(allowed=LOG_CHANNEL)
    interaction = await open_the_panel(bot, lead)
    view = a_panel(cog_module.NEW_GRANT_VIEW, member_id=900, role_id=5)

    await cog_module.run_grant(interaction, 7, view)

    assert interaction.sent == "test mode"
    assert await grants.grants_for(db, GUILD) == []


# --- the requests queue (fork F-R1) ---------------------------------------------------------------


async def test_a_pending_request_can_be_approved_from_the_panel(bot, db, lead):
    member = FakeMember(bot.guild, user_id=900, display_name="Bo")
    menu_id = await approval_menu(db)
    request_id = await grants.create_request(db, GUILD, menu_id, 900, 10)
    interaction = await open_the_panel(bot, lead)

    await press(interaction, "Waiting on staff (1)…")
    await choose(interaction, menus.REQUEST_PICK, [str(request_id)])
    assert labels(interaction.view) == ["Approve", "Deny…", "Back"]
    await press(interaction, "Approve")

    assert member.edits == [[10]]
    assert (await grants.get_request(db, request_id))["status"] == "approved"
    assert "role.approved" in await action_kinds(db)
    assert labels(interaction.view) == ["Back"]


async def test_a_second_press_says_it_was_already_decided_rather_than_acting_twice(bot, db, lead):
    member = FakeMember(bot.guild, user_id=900, display_name="Bo")
    menu_id = await approval_menu(db)
    request_id = await grants.create_request(db, GUILD, menu_id, 900, 10)
    interaction = await open_the_panel(bot, lead)
    await press(interaction, "Waiting on staff (1)…")
    await choose(interaction, menus.REQUEST_PICK, [str(request_id)])
    approve = button(interaction.view, "Approve")
    await approve.callback(interaction)

    await approve.callback(interaction)

    assert "already" in interaction.sent
    assert member.edits == [[10]]


async def test_a_menu_with_a_clock_asks_how_long_before_it_approves(bot, db, lead):
    FakeMember(bot.guild, user_id=900, display_name="Bo")
    menu_id = await approval_menu(db, expires=7)
    request_id = await grants.create_request(db, GUILD, menu_id, 900, 10)
    interaction = await open_the_panel(bot, lead)
    await press(interaction, "Waiting on staff (1)…")
    await choose(interaction, menus.REQUEST_PICK, [str(request_id)])

    assert "Approve for a while…" in labels(interaction.view)
    await press(interaction, "Approve for a while…")
    modal = interaction.response.modals[-1]
    modal.days._value = "3"
    await modal.on_submit(interaction)

    row = await grants.open_grant(db, GUILD, 900, 10)
    assert row["expires_at"] is not None


async def test_denying_from_the_panel_sends_the_reason_and_closes_the_row(bot, db, lead):
    member = FakeMember(bot.guild, user_id=900, display_name="Bo")
    menu_id = await approval_menu(db)
    request_id = await grants.create_request(db, GUILD, menu_id, 900, 10)
    interaction = await open_the_panel(bot, lead)
    await press(interaction, "Waiting on staff (1)…")
    await choose(interaction, menus.REQUEST_PICK, [str(request_id)])

    await press(interaction, "Deny…")
    modal = interaction.response.modals[-1]
    modal.reason._value = "not this month"
    await modal.on_submit(interaction)

    row = await grants.get_request(db, request_id)
    assert row["status"] == "denied" and row["deny_reason"] == "not this month"
    assert any("not this month" in str(one) for one in member.dms)
    assert member.edits == []


async def test_the_requests_sub_panel_says_so_when_nothing_is_waiting(bot, db, lead):
    interaction = await open_the_panel(bot, lead)
    view = a_panel()

    await cog_module.open_requests(interaction, view)

    assert menus.NO_REQUESTS in interaction.body
    assert not has_picker(interaction.view, menus.REQUEST_PICK)


# --- the panel's own guards -----------------------------------------------------------------------


async def test_a_staffer_demoted_mid_card_moves_nothing_and_is_told_why(bot, db, lead):
    await self_serve_menu(db)
    interaction = await open_a_menu(bot, lead, "pronouns")
    lead.guild_permissions = FakePerms(manage_guild=False)

    await press(interaction, "Delete it")

    assert "staff only" in interaction.sent
    assert await get_menu(db, GUILD, "pronouns") is not None


async def test_a_read_re_asks_the_staff_question_too(bot, db, lead):
    await self_serve_menu(db)
    interaction = await open_the_panel(bot, lead)
    lead.guild_permissions = FakePerms(manage_guild=False)

    await press(interaction, "Grants…")

    assert "staff only" in interaction.sent
    assert interaction.edits == []


async def test_a_click_after_the_database_goes_away_answers_a_sentence(bot, db, lead):
    await self_serve_menu(db)
    interaction = await open_the_panel(bot, lead)
    bot.db = FakeDownDatabase()
    interaction.response.deferred = False
    interaction.response.is_done = lambda: interaction.response.deferred

    await press(interaction, "Grants…")

    assert "database" in interaction.sent.lower() or "unavailable" in interaction.sent.lower()
    assert interaction.response.deferred is True


class FakeDownDatabase:
    is_connected = False
    conn = None


async def test_a_re_render_retires_the_view_it_replaced(bot, db, lead):
    await self_serve_menu(db)
    interaction = await open_the_panel(bot, lead)
    first = interaction.view

    await choose(interaction, menus.MENU_PICK, ["pronouns"])

    assert first.replaced is True and first.is_finished()
    assert interaction.view is not first


async def test_a_panel_that_goes_quiet_disables_every_control_and_says_so(bot, db, lead):
    await self_serve_menu(db)
    interaction = await open_the_panel(bot, lead)
    view = interaction.view
    view.message = PanelMessage(1, embed=interaction.embed)

    await view.on_timeout()

    assert all(one.disabled for one in view.children)
    assert view.message.kwargs["embeds"][0].footer.text == menus.PANEL_TIMEOUT_FOOTER


async def test_a_replaced_view_never_writes_over_the_card_that_replaced_it(bot, db, lead):
    await self_serve_menu(db)
    interaction = await open_the_panel(bot, lead)
    first = interaction.view
    first.message = PanelMessage(1)
    await choose(interaction, menus.MENU_PICK, ["pronouns"])
    edits = len(interaction.edits)

    await first.on_timeout()

    assert len(interaction.edits) == edits


async def test_the_panel_stays_live_for_the_minutes_the_setting_says(bot, db, lead):
    await bot.store.set(GUILD, menus.PANEL_MINUTES_KEY, 4)

    interaction = await open_the_panel(bot, lead)

    assert interaction.view.timeout == 4 * 60


async def test_the_panel_never_offers_a_link_when_there_is_no_dashboard(bot, db, lead):
    interaction = await open_the_panel(bot, lead)

    assert not [one for one in interaction.view.children if getattr(one, "url", None)]


async def test_every_control_sits_inside_discords_five_rows(bot, db, lead):
    menu_id = await self_serve_menu(db)
    await set_message(db, menu_id, TEST_CHANNEL, 5)

    root = await open_the_panel(bot, lead)
    card = await open_a_menu(bot, lead, "pronouns")

    for view in (root.view, card.view):
        assert all(0 <= one.row <= 4 for one in view.children)


def test_the_mock_servers_copy_of_the_refusal_has_not_drifted():
    """`site/mock/server.mjs` hand-copies this sentence, and it HAD drifted once already.

    The mock is what the dashboard is developed against, so a drifted copy means the page is
    built to a refusal nobody will ever be sent. Nothing generates the copy, so this is the
    thing that stops it: the JS literal is read back and compared, escaping and all.
    """
    root = pathlib.Path(cog_module.__file__).resolve().parents[3]
    text = (root / "site" / "mock" / "server.mjs").read_text(encoding="utf-8")
    found = re.search(r"^const ROLE_MENUS_OFF = '(.*)';$", text, re.M)
    assert found is not None, "site/mock/server.mjs no longer defines ROLE_MENUS_OFF"
    assert found.group(1).replace("\\'", "'") == ROLE_MENUS_OFF
