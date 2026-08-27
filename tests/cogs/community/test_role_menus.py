import discord
import pytest

from black_bloc.cogs.community.role_menus import (
    DESCRIPTION_MAX,
    JOY_GAMING,
    LABEL_MAX,
    MODES,
    NO_MENUS_YET,
    OPTIONS_MAX,
    SEED,
    TITLE_MAX,
    MenuLimitError,
    RoleMenus,
    RoleMenuView,
    StaffAssignSelect,
    add_option,
    create_menu,
    custom_id,
    delete_menu,
    get_menu,
    get_options,
    list_menus,
    max_values_for,
    menu_heading,
    option_line,
    panel_embed,
    parse_custom_id,
    posted_menus,
    remove_option,
    role_diff,
    seed_default_menus,
    select_emoji,
    set_message,
    summary,
    update_menu,
)
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore
from black_bloc.storage.db import Database

GUILD = 7
TEST_CHANNEL = 111
LOG_CHANNEL = 222


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "r.sqlite3")
    await database.connect()
    try:
        yield database
    finally:
        await database.close()


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


class FakePerms:
    def __init__(self, manage_guild=False):
        self.manage_guild = manage_guild


class FakeChannel:
    def __init__(self, channel_id):
        self.id = channel_id
        self.overwrites = {}
        self.messages = []

    async def send(self, content=None, **kwargs):
        self.messages.append({"content": content, **kwargs})
        return self


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.channels = {LOG_CHANNEL: FakeChannel(LOG_CHANNEL)}

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_role(self, role_id):
        return FakeRole(role_id)


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

    async def edit(self, roles=None, reason=None):
        if self.edit_raises is not None:
            raise self.edit_raises
        self.edits.append([r.id for r in roles])
        self.roles = list(roles)


class FakeGuard:
    def __init__(self, allowed=TEST_CHANNEL):
        self.allowed = allowed

    def allows_channel(self, channel_id):
        return channel_id == self.allowed

    def refusal_message(self):
        return "test mode"


class FakeBot:
    def __init__(self, db, store, guild):
        self.db = db
        self.store = store
        self.guild = guild
        self.guard = None

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)


class FakeResponse:
    def __init__(self):
        self.messages = []

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


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

    @property
    def said(self):
        return [m["content"] for m in self.response.messages]

    @property
    def sent(self):
        return self.response.messages[-1]["content"] if self.response.messages else None

    @property
    def view(self):
        return self.response.messages[-1].get("view")


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOG_CHANNEL)
    return FakeBot(db, store, FakeGuild())


@pytest.fixture
def lead(bot):
    return FakeMember(bot.guild, user_id=1, display_name="Lead", manage_guild=True)


async def staff_menu(db, name="runner-status"):
    menu_id = await create_menu(db, GUILD, name, "Runner status", None, "staff")
    await add_option(db, menu_id, 10, "Runner")
    await add_option(db, menu_id, 11, "Live Runner")
    return menu_id


async def action_kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def test_a_staff_menu_refuses_to_be_posted_and_says_what_to_use(bot, db, lead):
    await staff_menu(db)
    interaction = FakeInteraction(bot, lead)

    await RoleMenus.post.callback(RoleMenus(bot), interaction, "runner-status", None)

    assert "staff-assigned" in interaction.sent
    assert "/rolemenu assign" in interaction.sent
    assert (await get_menu(db, GUILD, "runner-status"))["message_id"] is None


async def test_assign_offers_the_menu_s_roles_with_the_ones_they_have_preselected(bot, db, lead):
    await staff_menu(db)
    target = FakeMember(bot.guild, user_id=900, roles=(10,))
    interaction = FakeInteraction(bot, lead)

    await RoleMenus.assign.callback(RoleMenus(bot), interaction, "runner-status", target)

    select = interaction.view.children[0]
    assert [option.value for option in select.options] == ["10", "11"]
    assert [option.default for option in select.options] == [True, False]


async def test_assign_applies_the_diff_to_the_target_and_logs_who_did_it(bot, db, lead):
    menu_id = await staff_menu(db)
    target = FakeMember(bot.guild, user_id=900, roles=(10, 99))
    select = StaffAssignSelect(menu_id, await get_options(db, menu_id), target, remove=False)
    select._values = ["11"]
    interaction = FakeInteraction(bot, lead)

    await select.callback(interaction)

    assert target.edits == [[99, 11]]
    assert "Added: Live Runner" in interaction.sent and "Removed: Runner" in interaction.sent
    assert "role_menu.assign" in await action_kinds(db)


async def test_unassign_only_offers_what_they_actually_have(bot, db, lead):
    await staff_menu(db)
    target = FakeMember(bot.guild, user_id=900, roles=(11,))
    interaction = FakeInteraction(bot, lead)

    await RoleMenus.unassign.callback(RoleMenus(bot), interaction, "runner-status", target)

    assert [option.value for option in interaction.view.children[0].options] == ["11"]


async def test_unassign_says_so_when_they_have_none_of_them(bot, db, lead):
    await staff_menu(db)
    target = FakeMember(bot.guild, user_id=900, display_name="Bo")
    interaction = FakeInteraction(bot, lead)

    await RoleMenus.unassign.callback(RoleMenus(bot), interaction, "runner-status", target)

    assert "nothing to take off" in interaction.sent
    assert interaction.view is None


async def test_unassign_takes_only_the_picked_roles_off(bot, db, lead):
    menu_id = await staff_menu(db)
    target = FakeMember(bot.guild, user_id=900, roles=(10, 11, 99))
    options = [row for row in await get_options(db, menu_id)]
    select = StaffAssignSelect(menu_id, options, target, remove=True)
    select._values = ["10"]

    await select.callback(FakeInteraction(bot, lead))

    assert target.edits == [[11, 99]]
    assert "role_menu.unassign" in await action_kinds(db)


async def test_assigning_is_refused_in_test_mode(bot, db, lead):
    menu_id = await staff_menu(db)
    bot.guard = FakeGuard(allowed=LOG_CHANNEL)
    target = FakeMember(bot.guild, user_id=900)
    select = StaffAssignSelect(menu_id, await get_options(db, menu_id), target, remove=False)
    select._values = ["10"]
    interaction = FakeInteraction(bot, lead)

    await select.callback(interaction)

    assert target.edits == [] and interaction.sent == "test mode"


async def test_a_refused_role_edit_says_the_member_is_unchanged(bot, db, lead):
    menu_id = await staff_menu(db)
    target = FakeMember(bot.guild, user_id=900, display_name="Bo")
    target.edit_raises = discord.HTTPException(_Refused(403), "no")
    select = StaffAssignSelect(menu_id, await get_options(db, menu_id), target, remove=False)
    select._values = ["10"]
    interaction = FakeInteraction(bot, lead)

    await select.callback(interaction)

    assert "still has exactly the roles they had" in interaction.sent
    assert "role_menu.assign" not in await action_kinds(db)


async def test_assign_is_staff_only(bot, db):
    await staff_menu(db)
    plain = FakeMember(bot.guild, user_id=900)
    interaction = FakeInteraction(bot, plain)

    await RoleMenus.assign.callback(RoleMenus(bot), interaction, "runner-status", plain)

    assert "staff only" in interaction.sent


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
    describe = RoleMenus.create.parameters[3]
    assert "staff" in describe.description


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


async def test_showall_lists_every_menu_with_its_options_and_never_pings(bot, db, lead):
    await staff_menu(db)
    posted_id = await create_menu(db, GUILD, "pronouns", "Pronouns", None, "multiple")
    await add_option(db, posted_id, 20, "He/Him", "❤️")
    await add_option(db, posted_id, 21, "She/Her")
    await set_message(db, posted_id, 500, 600)
    await create_menu(db, GUILD, "empty", "Nothing here yet")
    interaction = FakeInteraction(bot, lead)

    await RoleMenus.showall.callback(RoleMenus(bot), interaction)

    said = "\n".join(interaction.said)
    assert "**pronouns** — Pronouns (multiple, posted)" in said
    assert "**runner-status** — Runner status (staff, not posted)" in said
    assert "❤️ He/Him — <@&20>" in said and "• She/Her — <@&21>" in said
    assert "• Runner — <@&10>" in said and "• Live Runner — <@&11>" in said
    assert "no roles yet" in said
    assert all(m["ephemeral"] for m in interaction.response.messages)
    assert all(m["allowed_mentions"].roles is False for m in interaction.response.messages)


async def test_showall_splits_a_long_list_over_several_messages(bot, db, lead):
    """Four full menus rather than one over-full one — Discord shows 25 options at most."""
    for menu in range(4):
        menu_id = await create_menu(db, GUILD, f"big{menu}", "Big")
        for option in range(OPTIONS_MAX):
            role_id = menu * OPTIONS_MAX + option
            await add_option(db, menu_id, role_id, f"role name number {role_id} " + "x" * 40)
    interaction = FakeInteraction(bot, lead)

    await RoleMenus.showall.callback(RoleMenus(bot), interaction)

    assert len(interaction.said) > 1
    assert all(len(page) <= 1900 for page in interaction.said)


async def test_showall_is_staff_only_and_says_so_when_there_is_nothing(bot, db, lead):
    stranger = FakeMember(bot.guild, user_id=900)
    refused = FakeInteraction(bot, stranger)
    await RoleMenus.showall.callback(RoleMenus(bot), refused)
    assert "staff only" in refused.sent

    empty = FakeInteraction(bot, lead)
    await RoleMenus.showall.callback(RoleMenus(bot), empty)
    assert empty.sent == NO_MENUS_YET


def test_a_menu_heading_and_an_option_line_have_one_home_each():
    menu = {"name": "pronouns", "title": "Pronouns", "mode": "multiple", "message_id": None}
    assert menu_heading(menu) == "**pronouns** — Pronouns (multiple, not posted)"
    assert menu_heading(menu | {"message_id": 5}).endswith("(multiple, posted)")
    assert option_line({"emoji": None, "label": "Runner", "role_id": 10}) == "• Runner — <@&10>"
    assert option_line({"emoji": "❤️", "label": "He/Him", "role_id": 1}) == "❤️ He/Him — <@&1>"


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
