import json
import re
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import discord
import pytest

from black_bloc import rolegrants as grants
from black_bloc import rolemenus as menus
from black_bloc import timed_roles as timed
from black_bloc.cogs.community import role_menus as cog_module
from black_bloc.cogs.community.role_menus import (
    APPROVAL_CHANNEL_KEY,
    APPROVER_ROLE_KEY,
    DESCRIPTION_MAX,
    JOY_GAMING,
    MODES,
    SEED,
    TITLE_MAX,
    MenuLimitError,
    RequestButton,
    RoleMenus,
    RoleMenuView,
    add_option,
    audit_actor,
    card_target,
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
    retry_days_of,
    role_diff,
    seed_default_menus,
    select_emoji,
    set_message,
    summary,
    unposted_menus,
    update_menu,
)
from black_bloc.config import load_settings
from black_bloc.settings_store import DB_UNAVAILABLE, SettingsStore

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


async def test_posted_menus_only_lists_posted_ones(db):
    posted_id = await create_menu(db, GUILD, "posted", "P")
    await create_menu(db, GUILD, "draft", "D")
    await set_message(db, posted_id, 500, 600)
    rows = await posted_menus(db)
    assert [(r["name"], r["channel_id"], r["message_id"]) for r in rows] == [("posted", 500, 600)]


async def test_unposted_menus_skips_a_menu_that_never_had_a_channel(db):
    await create_menu(db, GUILD, "draft", "D")
    assert await unposted_menus(db) == []


async def test_bad_mode_is_refused(db):
    with pytest.raises(ValueError, match="mode must be"):
        await create_menu(db, GUILD, "m", "M", None, "sometimes")


class FakeRole:
    def __init__(self, role_id, assignable=True):
        self.id = role_id
        self.name = f"role-{role_id}"
        self.assignable = assignable

    def is_assignable(self):
        return self.assignable


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
        self.people = {}
        self.stuck_roles = set()
        self.me = None
        self.audit_entries = []

    @property
    def members(self):
        return list(self.people.values())

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_role(self, role_id):
        return FakeRole(role_id, assignable=role_id not in self.stuck_roles)

    def get_member(self, user_id):
        return self.people.get(user_id)

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
        guild.people[user_id] = self

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


async def staff_menu(db, name="runner-status"):
    menu_id = await create_menu(db, GUILD, name, "Runner status", None, "staff")
    await timed.add(db, GUILD, 10, "Runner")
    await timed.add(db, GUILD, 11, "Live Runner")
    return menu_id


async def action_kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


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


class _Refused:
    def __init__(self, status):
        self.status = status
        self.reason = "refused"


@pytest.mark.parametrize(
    ("held", "menu", "picked", "wanted"),
    [
        ({1, 2, 99}, [1, 2, 3], [2, 3], ({3}, {1})),
        ({1}, [1], [42], (set(), {1})),
        ({1, 2, 99}, [1, 2], [], (set(), {1, 2})),
    ],
    ids=[
        "only-menu-roles-move",
        "a-pick-outside-the-menu-is-ignored",
        "an-empty-pick-removes-everything-the-menu-owns",
    ],
)
def test_role_diff_moves_only_the_roles_the_menu_owns(held, menu, picked, wanted):
    assert role_diff(held, menu, picked) == wanted


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


async def test_a_role_taken_off_by_hand_closes_its_grant(bot, db):
    await grants.add_grant(db, GUILD, 900, 10, "approval", until=grants.expires_at(7))
    before = FakeMember(bot.guild, user_id=900, roles=(10,))
    after = FakeMember(bot.guild, user_id=900, roles=())

    await RoleMenus(bot).on_member_update(before, after)

    assert await grants.open_grant(db, GUILD, 900, 10) is None
    assert (await grants.grants_for(db, GUILD))[0]["removed_reason"] == "by_hand"
    assert "role.changed_by_hand" in await action_kinds(db)


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


async def test_the_sweep_corrects_records_and_never_touches_the_member(bot, db):
    member = FakeMember(bot.guild, user_id=900, roles=(99, 11))
    await grants.add_grant(db, GUILD, 900, 10, "approval")

    await RoleMenus(bot).reconcile_records()

    assert member.edits == []
    assert await grants.open_grant(db, GUILD, 900, 10) is None
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
    await choose(interaction, "An event…", [name])
    return interaction


async def test_rolemenu_is_staff_only_and_never_leaves_a_dead_button(bot, db):
    stranger = FakeMember(bot.guild, user_id=901)

    interaction = await open_the_panel(bot, stranger)

    assert "staff only" in interaction.sent
    assert interaction.view is None


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


async def test_a_read_re_asks_the_staff_question_too(bot, db, lead):
    await self_serve_menu(db)
    interaction = await open_the_panel(bot, lead)
    shown = len(interaction.edits)
    lead.guild_permissions = FakePerms(manage_guild=False)

    await press(interaction, "Grants…")

    assert "staff only" in interaction.sent
    assert len(interaction.edits) == shown


async def test_a_click_after_the_database_goes_away_answers_a_sentence(bot, db, lead):
    await self_serve_menu(db)
    interaction = await open_the_panel(bot, lead)
    bot.db = FakeDownDatabase()
    interaction.response.deferred = False
    interaction.response.is_done = lambda: interaction.response.deferred

    await press(interaction, "Grants…")

    assert interaction.sent == DB_UNAVAILABLE
    assert interaction.response.deferred is True


class FakeDownDatabase:
    is_connected = False
    conn = None


async def test_a_panel_that_goes_quiet_disables_every_control_and_says_so(bot, db, lead):
    await self_serve_menu(db)
    interaction = await open_the_panel(bot, lead)
    view = interaction.view
    view.message = PanelMessage(1, embed=interaction.embed)

    await view.on_timeout()

    assert all(one.disabled for one in view.children)
    assert view.message.kwargs["embeds"][0].footer.text == menus.PANEL_TIMEOUT_FOOTER


async def test_the_panel_stays_live_for_the_minutes_the_setting_says(bot, db, lead):
    await bot.store.set(GUILD, menus.PANEL_MINUTES_KEY, 4)

    interaction = await open_the_panel(bot, lead)

    assert interaction.view.timeout == 4 * 60


async def test_the_panel_never_offers_a_link_when_there_is_no_dashboard(bot, db, lead):
    interaction = await open_the_panel(bot, lead)

    assert not [one for one in interaction.view.children if getattr(one, "url", None)]


# --- switching role menus off takes back what members picked, asked first (small-fixes) ---------


# --- temporary roles: a menu's end takes its roles off everyone (request #17) ---------------------

PAST = "2020-01-01T00:00:00+00:00"
LATER = "2099-01-01T00:00:00+00:00"
APPROVER = 4242


async def end_menu_with(db, *, ends_at=PAST, name="btb-2027", roles=(10, 11), passes=0):
    menu_id = await create_menu(db, GUILD, name, "Back to Black 2027", None, "staff")
    for role_id in roles:
        await timed.add(db, GUILD, role_id, f"Role {role_id}")
    await db.conn.execute(
        "UPDATE role_menus SET ends_source = 'date', ends_at = ?, end_passes = ? WHERE id = ?",
        (ends_at, passes, menu_id),
    )
    await db.conn.commit()
    return menu_id


async def menu_row(db, menu_id):
    return await cog_module.get_menu_by_id(db, menu_id)


async def details_of(db, kind):
    cur = await db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id", (kind,)
    )
    return [json.loads(row["details"]) for row in await cur.fetchall()]


async def every_row(db, table):
    cur = await db.conn.execute(f"SELECT * FROM {table} ORDER BY rowid")
    return [tuple(row) for row in await cur.fetchall()]


async def tick(bot):
    """The hourly loop's body, in its order: menus first, then the grants."""
    cog = RoleMenus(bot)
    await cog.run_due_menus()
    await cog.run_due_grants()
    return cog


async def store_notice_channel(bot, *, approver=None):
    await bot.store.set(GUILD, APPROVAL_CHANNEL_KEY, STAFF_CHANNEL)
    if approver is not None:
        await bot.store.set(GUILD, APPROVER_ROLE_KEY, approver)


async def test_a_tick_over_menus_with_no_end_removes_nothing_and_writes_nothing(bot, db):
    """The 1a deploy: every live menu has no end, so the hourly tick touches nobody."""
    await seed_default_menus(db, GUILD)
    wearer = FakeMember(bot.guild, user_id=900, roles=(1285785434131005474, 1285361896383320074))
    await grants.add_grant(db, GUILD, 900, 1285361896383320074, "staff", until=None)
    before = {table: await every_row(db, table) for table in ("role_menus", "role_grants")}
    logged = await action_kinds(db)

    cog = RoleMenus(bot)
    await cog._expiry_loop.coro(cog)

    assert wearer.edits == [] and wearer.dms == []
    assert {table: await every_row(db, table) for table in before} == before
    assert await action_kinds(db) == logged
    assert all(row["ends_source"] == "none" for row in await list_menus(db, GUILD))


async def test_every_wearer_loses_the_menus_roles_including_one_added_by_hand(bot, db):
    menu_id = await end_menu_with(db)
    granted = FakeMember(bot.guild, user_id=900, roles=(10, 99))
    by_hand = FakeMember(bot.guild, user_id=901, roles=(10, 11))
    bystander = FakeMember(bot.guild, user_id=902, roles=(99,))
    await grants.add_grant(db, GUILD, 900, 10, "staff", until=PAST)

    await tick(bot)

    assert granted.edits == [[99]] and by_hand.edits == [[]] and bystander.edits == []
    assert await grants.open_grant(db, GUILD, 900, 10) is None
    assert (await grants.grants_for(db, GUILD))[0]["removed_reason"] == "expired"
    menu = await menu_row(db, menu_id)
    assert menu["ended_at"] and menu["end_passes"] == 1 and menu["end_failures"] is None
    [ended] = await details_of(db, "role_menu.ended")
    assert (ended["members"], ended["failures"]) == (2, 0)
    assert "role.expired" not in await action_kinds(db)


async def test_one_dm_per_member_names_every_role_that_ended(bot, db):
    await end_menu_with(db)
    member = FakeMember(bot.guild, user_id=900, roles=(10, 11))
    await grants.add_grant(db, GUILD, 900, 10, "staff", until=PAST)
    await grants.add_grant(db, GUILD, 900, 11, "staff", until=PAST)

    await tick(bot)

    assert len(member.dms) == 1
    assert "**Role 10**, **Role 11**" in member.dms[0] and bot.guild.name in member.dms[0]


async def test_the_grant_path_leaves_a_due_menus_roles_to_the_end_pass(bot, db):
    """cog_load runs the grant path on its own; it must not take a menu role off one by one."""
    await end_menu_with(db)
    member = FakeMember(bot.guild, user_id=900, roles=(10,))
    await grants.add_grant(db, GUILD, 900, 10, "staff", until=PAST)

    await RoleMenus(bot).run_due_grants()

    assert member.edits == [] and member.dms == []
    assert await grants.open_grant(db, GUILD, 900, 10) is not None


async def test_the_pass_goes_through_change_roles_one_call_per_member(bot, db, monkeypatch):
    await end_menu_with(db)
    FakeMember(bot.guild, user_id=900, roles=(10, 11))
    FakeMember(bot.guild, user_id=901, roles=(11,))
    calls = []
    real = cog_module.change_roles

    async def spy(bot_, member, guild, to_add, to_remove, reason):
        calls.append((member.id, set(to_add), set(to_remove)))
        return await real(bot_, member, guild, to_add, to_remove, reason)

    monkeypatch.setattr(cog_module, "change_roles", spy)
    await tick(bot)

    assert calls == [(900, set(), {10, 11}), (901, set(), {11})]
    assert grants.was_ours(bot, GUILD, 900, 10, grants.REMOVED)


async def test_a_refusal_is_logged_retried_and_the_menu_ends_after_the_cap(bot, db):
    await store_notice_channel(bot)
    menu_id = await end_menu_with(db)
    stuck = FakeMember(bot.guild, user_id=900, display_name="Stuck", roles=(10,))
    fine = FakeMember(bot.guild, user_id=901, roles=(11,))
    stuck.edit_raises = discord.HTTPException(_Refused(403), "no")

    await tick(bot)
    menu = await menu_row(db, menu_id)
    assert menu["ended_at"] is None and menu["end_passes"] == 1
    assert fine.edits == [[]] and len(fine.dms) == 1
    [failed] = await details_of(db, "role_menu.end_failed")
    assert failed["user"] == 900 and failed["roles"] == [10]
    assert "role_menu.ended" not in await action_kinds(db)

    await tick(bot)
    assert (await menu_row(db, menu_id))["ended_at"] is None
    await tick(bot)
    menu = await menu_row(db, menu_id)
    assert menu["ended_at"] and menu["end_passes"] == 3
    assert json.loads(menu["end_failures"]) == [[900, [10]]]
    assert len(await details_of(db, "role_menu.end_failed")) == 3
    [ended] = await details_of(db, "role_menu.ended")
    assert ended["failures"] == 1 and ended["passes"] == 3
    assert (ended["members"], ended["this_pass"], menu["end_members"]) == (1, 0, 1)
    assert len(fine.dms) == 1 and stuck.dms == []
    [notice] = bot.guild.channels[STAFF_CHANNEL].messages
    assert "Stuck still wears **Role 10**" in notice.kwargs["content"]
    assert "taken off 1 people" in notice.kwargs["content"]

    await tick(bot)
    assert len(await details_of(db, "role_menu.end_failed")) == 3


async def test_a_role_above_the_bot_is_a_failure_and_the_rest_still_come_off(bot, db):
    await end_menu_with(db)
    bot.guild.stuck_roles.add(11)
    member = FakeMember(bot.guild, user_id=900, roles=(10, 11, 99))

    await tick(bot)

    assert member.edits == [[11, 99]]
    [failed] = await details_of(db, "role_menu.end_failed")
    assert failed["roles"] == [11]
    assert "**Role 10**" in member.dms[0] and "Role 11" not in member.dms[0]


async def test_the_ended_notice_pings_only_the_approver_role(bot, db):
    await store_notice_channel(bot, approver=APPROVER)
    await end_menu_with(db)
    FakeMember(bot.guild, user_id=900, display_name="@everyone", roles=(10,))

    await tick(bot)

    [message] = bot.guild.channels[STAFF_CHANNEL].messages
    assert message.kwargs["content"].startswith(f"<@&{APPROVER}> **Back to Black 2027** ended")
    mentions = message.kwargs["allowed_mentions"]
    assert mentions.everyone is False and mentions.users is False
    assert [role.id for role in mentions.roles] == [APPROVER]


async def test_the_ended_notice_can_be_switched_off(bot, db):
    await store_notice_channel(bot)
    await bot.store.set(GUILD, "rolemenu_ended_notice", False)
    await end_menu_with(db)
    FakeMember(bot.guild, user_id=900, roles=(10,))

    await tick(bot)

    assert bot.guild.channels[STAFF_CHANNEL].messages == []
    assert "role_menu.ended" in await action_kinds(db)


async def test_the_end_pass_needs_no_switch_turned_on(bot, db):
    await end_menu_with(db)
    member = FakeMember(bot.guild, user_id=900, roles=(10,))

    await tick(bot)

    assert member.edits == [[]]


async def test_in_test_mode_the_pass_only_says_what_it_would_do(bot, db):
    bot.guard = FakeGuard()
    menu_id = await end_menu_with(db)
    member = FakeMember(bot.guild, user_id=900, roles=(10,))

    await tick(bot)

    assert member.edits == [] and member.dms == []
    [would] = await details_of(db, "role_menu.would_end")
    assert would["wearers"] == [[900, [10]]]
    menu = await menu_row(db, menu_id)
    assert menu["ended_at"] is None and menu["end_passes"] == 0


async def test_a_member_cache_that_will_not_fill_is_never_a_clean_pass(bot, db):
    bot.guild.member_count = 50

    async def chunk():
        return None

    bot.guild.chunk = chunk
    menu_id = await end_menu_with(db)
    FakeMember(bot.guild, user_id=900, roles=(10,))

    await tick(bot)

    menu = await menu_row(db, menu_id)
    assert menu["ended_at"] is None and menu["end_passes"] == 0
    [failed] = await details_of(db, "role_menu.end_failed")
    assert failed["reason"] == "members_not_loaded"


async def test_a_menu_ends_once_and_a_second_pass_finds_nothing(bot, db):
    await end_menu_with(db)
    member = FakeMember(bot.guild, user_id=900, roles=(10,))

    await tick(bot)
    member.roles.append(FakeRole(10))
    await tick(bot)

    assert member.edits == [[]] and len(member.dms) == 1
    assert len(await details_of(db, "role_menu.ended")) == 1


async def test_end_it_now_takes_the_roles_off_at_once(bot, db, lead):
    menu_id = await end_menu_with(db, ends_at=LATER)
    member = FakeMember(bot.guild, user_id=900, roles=(11,))

    found = await cog_module.end_menu_now(bot, bot.guild, lead, await menu_row(db, menu_id))

    assert found["members"] == 1 and member.edits == [[]]
    menu = await menu_row(db, menu_id)
    assert menu["ended_at"] and menu["ends_source"] == "date" and menu["ends_set_by"] == lead.id
    [ended] = await details_of(db, "role_menu.ended")
    assert ended["members"] == 1


async def test_a_new_end_on_an_ended_menu_starts_it_over(bot, db, lead):
    menu_id = await end_menu_with(db)
    await tick(bot)
    assert (await menu_row(db, menu_id))["ended_at"]

    await cog_module.set_menu_end(
        bot, bot.guild, lead, await menu_row(db, menu_id), source="date", ends_at=LATER
    )

    menu = await menu_row(db, menu_id)
    assert menu["ended_at"] is None and menu["end_passes"] == 0 and menu["ends_at"] == LATER


async def marathon_with(db, ends_at):
    cur = await db.conn.execute(
        "INSERT INTO marathons(guild_id, name, source, source_ref, schedule_url, added_by, "
        "added_at, ends_at) VALUES (?, 'Back to Black 2027', 'gdq', 'x', 'https://x', 1, ?, ?)",
        (GUILD, PAST, ends_at),
    )
    await db.conn.commit()
    return cur.lastrowid


async def bound_menu(bot, db, lead, marathon_id, name="btb-2027"):
    menu_id = await create_menu(db, GUILD, name, "Back to Black 2027", None, "staff")
    await timed.add(db, GUILD, 10, "Runner")
    end = await cog_module.set_menu_end(
        bot,
        bot.guild,
        lead,
        await menu_row(db, menu_id),
        source="marathon",
        marathon_id=marathon_id,
    )
    return menu_id, end


async def test_an_ended_menu_does_not_follow_its_marathon_any_more(bot, db, lead):
    marathon_id = await marathon_with(db, "2020-01-01T00:00:00+00:00")
    menu_id, end = await bound_menu(bot, db, lead, marathon_id)
    await tick(bot)
    assert (await menu_row(db, menu_id))["ended_at"]

    await db.conn.execute(
        "UPDATE marathons SET ends_at = '2027-02-28T06:10:00+00:00' WHERE id = ?", (marathon_id,)
    )
    await cog_module.follow_marathon(bot, bot.guild, marathon_id)

    assert (await menu_row(db, menu_id))["ends_at"] == end


async def test_a_marathon_leaving_the_list_leaves_its_menu_on_a_date(bot, db, lead):
    await store_notice_channel(bot)
    marathon_id = await marathon_with(db, "2027-02-28T05:00:00+00:00")
    menu_id, _ = await bound_menu(bot, db, lead, marathon_id)

    await cog_module.unbind_marathon(
        bot, bot.guild, {"id": marathon_id, "name": "Back to Black 2027"}
    )

    menu = await menu_row(db, menu_id)
    assert menu["ends_source"] == "date" and menu["ends_marathon_id"] is None
    assert menu["ends_at"] == "2027-03-01T05:00:00+00:00"
    [unbound] = await details_of(db, "role_menu.end_unbound")
    assert unbound["menu"] == "btb-2027"
    [notice] = bot.guild.channels[STAFF_CHANNEL].messages
    assert "left the marathon list" in notice.kwargs["content"]


async def test_a_marathon_with_no_end_yet_binds_and_unbinds_to_no_end(bot, db, lead):
    marathon_id = await marathon_with(db, None)
    menu_id, end = await bound_menu(bot, db, lead, marathon_id, name="halo")
    assert end is None and (await menu_row(db, menu_id))["ends_source"] == "marathon"

    await cog_module.unbind_marathon(bot, bot.guild, {"id": marathon_id, "name": "Halo Fest"})

    assert (await menu_row(db, menu_id))["ends_source"] == "none"


async def test_end_it_now_in_test_mode_changes_nothing_and_arms_nothing(bot, db, lead):
    bot.guard = FakeGuard()
    menu_id = await end_menu_with(db, ends_at=LATER)
    before = tuple(await menu_row(db, menu_id))
    member = FakeMember(bot.guild, user_id=900, roles=(10,))

    found = await cog_module.end_menu_now(bot, bot.guild, lead, await menu_row(db, menu_id))

    assert found is None and member.edits == []
    assert tuple(await menu_row(db, menu_id)) == before
    assert len(await details_of(db, "role_menu.would_end")) == 1


# --- temporary roles 1b: a grant on a menu role never outlasts the menu ---------------------------


# --- an end that moves EARLIER waits for staff (conductor's safety, 1b) ---------------------------


async def move_marathon(db, marathon_id, ends_at):
    await db.conn.execute("UPDATE marathons SET ends_at = ? WHERE id = ?", (ends_at, marathon_id))
    await db.conn.commit()


async def test_an_earlier_marathon_end_is_held_and_never_makes_the_menu_due(bot, db, lead):
    await store_notice_channel(bot)
    marathon_id = await marathon_with(db, "2027-02-28T05:00:00+00:00")
    menu_id, end = await bound_menu(bot, db, lead, marathon_id)
    wearer = FakeMember(bot.guild, user_id=900, roles=(10,))

    await move_marathon(db, marathon_id, PAST)
    await cog_module.follow_marathon(bot, bot.guild, marathon_id)
    await cog_module.follow_marathon(bot, bot.guild, marathon_id)
    await tick(bot)

    menu = await menu_row(db, menu_id)
    assert menu["ends_at"] == end and menu["ended_at"] is None
    assert menu["ends_held_at"] == "2020-01-02T00:00:00+00:00"
    assert wearer.edits == [] and [r.id for r in wearer.roles] == [10]
    [held] = await details_of(db, "role_menu.end_held")
    assert (held["ends_at"], held["held"]) == (end, "2020-01-02T00:00:00+00:00")
    [notice] = bot.guild.channels[STAFF_CHANNEL].messages
    assert "**Back to Black 2027**'s marathon now ends earlier" in notice.kwargs["content"]
    assert await details_of(db, "role_menu.end_moved") == []


async def test_use_the_earlier_end_takes_the_held_end_in_one_row(bot, db, lead):
    marathon_id = await marathon_with(db, "2027-02-28T05:00:00+00:00")
    menu_id, _ = await bound_menu(bot, db, lead, marathon_id)
    await move_marathon(db, marathon_id, "2027-02-20T05:00:00+00:00")
    await cog_module.follow_marathon(bot, bot.guild, marathon_id)
    before = len(await details_of(db, "role_menu.end_set"))

    end = await cog_module.use_held_end(bot, bot.guild, lead, await menu_row(db, menu_id))

    menu = await menu_row(db, menu_id)
    assert end == menu["ends_at"] == "2027-02-21T05:00:00+00:00"
    assert menu["ends_held_at"] is None and menu["ends_source"] == "marathon"
    assert len(await details_of(db, "role_menu.end_set")) == before + 1
    assert await cog_module.use_held_end(bot, bot.guild, lead, menu) is None


async def test_a_later_read_that_no_longer_pulls_earlier_clears_the_hold(bot, db, lead):
    marathon_id = await marathon_with(db, "2027-02-28T05:00:00+00:00")
    menu_id, _ = await bound_menu(bot, db, lead, marathon_id)
    await move_marathon(db, marathon_id, "2027-02-20T05:00:00+00:00")
    await cog_module.follow_marathon(bot, bot.guild, marathon_id)
    assert (await menu_row(db, menu_id))["ends_held_at"]

    await move_marathon(db, marathon_id, "2027-02-28T07:00:00+00:00")
    await cog_module.follow_marathon(bot, bot.guild, marathon_id)

    menu = await menu_row(db, menu_id)
    assert menu["ends_held_at"] is None
    assert menu["ends_at"] == "2027-03-01T07:00:00+00:00"
    [cleared] = await details_of(db, "role_menu.end_hold_cleared")
    assert cleared["held"] == "2027-02-21T05:00:00+00:00"


async def test_with_the_hold_off_an_earlier_end_applies_at_once(bot, db, lead):
    await bot.store.set(GUILD, "rolemenu_end_earlier_holds", False)
    marathon_id = await marathon_with(db, "2027-02-28T05:00:00+00:00")
    menu_id, _ = await bound_menu(bot, db, lead, marathon_id)

    await move_marathon(db, marathon_id, "2027-02-20T05:00:00+00:00")
    await cog_module.follow_marathon(bot, bot.guild, marathon_id)

    menu = await menu_row(db, menu_id)
    assert menu["ends_at"] == "2027-02-21T05:00:00+00:00" and menu["ends_held_at"] is None
    assert await details_of(db, "role_menu.end_held") == []


async def test_small_earlier_moves_apply_until_they_add_up_past_the_floor(bot, db, lead):
    marathon_id = await marathon_with(db, "2027-02-28T05:00:00+00:00")
    menu_id, _ = await bound_menu(bot, db, lead, marathon_id)

    await move_marathon(db, marathon_id, "2027-02-28T04:30:00+00:00")
    await cog_module.follow_marathon(bot, bot.guild, marathon_id)
    assert (await menu_row(db, menu_id))["ends_at"] == "2027-03-01T04:30:00+00:00"

    await move_marathon(db, marathon_id, "2027-02-28T03:50:00+00:00")
    await cog_module.follow_marathon(bot, bot.guild, marathon_id)
    menu = await menu_row(db, menu_id)
    assert menu["ends_at"] == "2027-03-01T04:30:00+00:00"
    assert menu["ends_held_at"] == "2027-03-01T03:50:00+00:00"


async def test_a_staff_typed_end_or_end_it_now_is_never_held(bot, db, lead):
    marathon_id = await marathon_with(db, "2027-02-28T05:00:00+00:00")
    menu_id, _ = await bound_menu(bot, db, lead, marathon_id)

    end = await cog_module.set_menu_end(
        bot, bot.guild, lead, await menu_row(db, menu_id), source="date",
        ends_at="2027-01-01T00:00:00+00:00",
    )

    assert (await menu_row(db, menu_id))["ends_at"] == end == "2027-01-01T00:00:00+00:00"
    assert await details_of(db, "role_menu.end_held") == []


async def test_the_tick_counts_menus_due_ended_and_failures_for_the_health_tab(bot, db):
    await end_menu_with(db)
    FakeMember(bot.guild, user_id=900, roles=(10,))

    cog = await tick(bot)

    assert cog.loop_counts("_expiry_loop") == "menus due 1 · ended 1 · failures 0"
    assert cog.loop_counts("_other_loop") is None


# --- /rolemenu's Set the end…, End it now, Delete, the audit and the retired doors (1b) ---------


async def btb_card(bot, db, lead, *, wearers=((900, (10, 11)), (901, (10,)))):
    menu_id = await create_menu(db, GUILD, "btb-2027", "Back to Black 2027", None, "staff")
    await timed.add(db, GUILD, 10, "Runner")
    await timed.add(db, GUILD, 11, "Host")
    people = [FakeMember(bot.guild, user_id=uid, roles=roles) for uid, roles in wearers]
    return menu_id, people, await open_a_menu(bot, lead, "btb-2027")


async def test_a_posted_panel_from_before_answers_the_retired_sentence_and_changes_nothing(
    bot, db
):
    menu_id = await self_serve_menu(db)
    member = FakeMember(bot.guild, user_id=900, roles=(1,))
    interaction = FakeInteraction(bot, member)
    select = cog_module.RoleMenuSelect(menu_id, await get_options(db, menu_id), "multiple")
    select._values = ["2"]

    await select.callback(interaction)
    retired = cog_module.RetiredMenuPick(menu_id)
    await retired.callback(interaction)

    assert interaction.said == ["Roles are picked in Discord's own Channels & Roles now."] * 2
    assert member.edits == [] and await action_kinds(db) == []
    assert re.fullmatch(cog_module.custom_id_template(), cog_module.custom_id(menu_id))


async def test_nothing_re_registers_a_posted_panel_on_boot(bot, db):
    menu_id = await self_serve_menu(db)
    await set_message(db, menu_id, TEST_CHANNEL, 5000)
    added = []
    bot.add_dynamic_items = lambda *items: added.extend(items)

    cog = RoleMenus(bot)
    cog._expiry_loop.start = lambda: None
    await cog.cog_load()

    assert bot.views == []
    assert cog_module.RetiredMenuPick in added and RequestButton in added


def test_failure_lines_name_each_member_and_the_roles_still_on_them(bot):
    FakeMember(bot.guild, user_id=900, roles=(10, 11))

    lines = cog_module.failure_lines(
        bot, bot.guild, [[900, [10, 11]], [901, [11]]], {10: "Runner", 11: "Host"}
    )

    assert lines[1] == "901 still wears **Host**"
    assert lines[0].endswith(" still wears **Runner**, **Host**")
    assert cog_module.failure_lines(bot, bot.guild, [], {}) == []


# --- a role `/pings` hands out never sits on a menu that ends (2026-11-13) ------------------------

PINGS_SAID = "belongs to `/pings`, so nothing was changed"


async def a_fan_role(db, role_id=10, user_id=900):
    from black_bloc import pings

    await pings.set_fan_role(db, GUILD, user_id, role_id, 1)


# --- timed roles per event (event-roles-design.md §7) --------------------------------------------

SOON = "2099-02-01T00:00:00+00:00"


async def an_event(db, name, *, ends_at=None, title=None):
    menu_id = await create_menu(db, GUILD, name, title or name.title(), None, "staff")
    if ends_at is not None:
        await db.conn.execute(
            "UPDATE role_menus SET ends_source = 'date', ends_at = ? WHERE id = ?",
            (ends_at, menu_id),
        )
        await db.conn.commit()
    return await menu_row(db, menu_id)


async def timed_list(db, *role_ids):
    for role_id in role_ids:
        await timed.add(db, GUILD, role_id, f"Role {role_id}")


async def give(bot, lead, event, role_id, *members):
    return await cog_module.give_event_role(bot, bot.guild, lead, event, role_id, list(members))


async def open_grant_on(db, user_id, role_id, menu_id):
    return await timed.event_grant(db, GUILD, user_id, role_id, menu_id)


async def test_overlapping_events_a_b_assignee_keeps_the_role_and_a_by_hand_holder_loses_it(
    bot, db, lead
):
    await timed_list(db, 10)
    a = await an_event(db, "a", ends_at=LATER)
    b = await an_event(db, "b", ends_at=SOON)
    only_a = FakeMember(bot.guild, user_id=900)
    both = FakeMember(bot.guild, user_id=901)
    by_hand = FakeMember(bot.guild, user_id=902, roles=(10,))
    await give(bot, lead, a, 10, only_a, both)
    await give(bot, lead, b, 10, both)
    assert await open_grant_on(db, 901, 10, a["id"]) and await open_grant_on(db, 901, 10, b["id"])

    await db.conn.execute("UPDATE role_menus SET ends_at = ? WHERE id = ?", (PAST, a["id"]))
    await db.conn.commit()
    await tick(bot)

    assert 10 not in [r.id for r in only_a.roles] and 10 not in [r.id for r in by_hand.roles]
    assert 10 in [r.id for r in both.roles]
    assert await open_grant_on(db, 901, 10, a["id"]) is None
    assert await open_grant_on(db, 901, 10, b["id"]) is not None
    [ended] = await details_of(db, "role_menu.ended")
    assert (ended["this_pass"], ended["kept"], ended["failures"]) == (2, 1, 0)

    await db.conn.execute("UPDATE role_menus SET ends_at = ? WHERE id = ?", (PAST, b["id"]))
    await db.conn.commit()
    await tick(bot)

    assert 10 not in [r.id for r in both.roles]
    assert await open_grant_on(db, 901, 10, b["id"]) is None


async def test_the_grant_path_never_strips_an_event_assignment_or_a_timed_role_at_cog_load(
    bot, db, lead
):
    await timed_list(db, 10, 11)
    b = await an_event(db, "b", ends_at=LATER)
    member = FakeMember(bot.guild, user_id=900, roles=(11,))
    await give(bot, lead, b, 10, member)
    await db.conn.execute("UPDATE role_grants SET expires_at = ?", (PAST,))
    await grants.add_grant(db, GUILD, 900, 11, "staff", until=PAST)
    await db.conn.commit()

    await RoleMenus(bot).run_due_grants()

    assert {r.id for r in member.roles} == {10, 11}
    assert "role.expired" not in await action_kinds(db)


async def test_a_role_pings_owns_is_never_taken_even_when_it_sits_on_the_list(bot, db, lead):
    from black_bloc import pings

    await timed_list(db, 10, 12)
    await bot.store.set(GUILD, "raidtrain_ping_role_id", 12)
    await pings.set_fan_role(db, GUILD, 905, 10, 1)
    await an_event(db, "a", ends_at=PAST)
    fan = FakeMember(bot.guild, user_id=900, roles=(10, 12))

    await tick(bot)

    assert {r.id for r in fan.roles} == {10, 12} and fan.dms == []
    assert 12 in await pings.owned_role_ids(bot, GUILD)


async def test_end_it_now_asks_with_the_count_the_pass_then_takes(bot, db, lead):
    await timed_list(db, 10, 11)
    a = await an_event(db, "a", ends_at=LATER, title="Back to Black")
    b = await an_event(db, "b", ends_at=LATER)
    kept = FakeMember(bot.guild, user_id=900, roles=(10, 11))
    gone = [FakeMember(bot.guild, user_id=uid, roles=(10,)) for uid in (901, 902)]
    await give(bot, lead, b, 11, kept)
    interaction = await open_a_menu(bot, lead, "a")

    await press(interaction, "End it now")

    question = interaction.body
    assert question == "Take 1 role(s) off 3 people now? 1 keep a role through another event."
    plan = await cog_module.end_plan(bot, bot.guild, a)
    await press(interaction, "Yes, take them off")

    [ended] = await details_of(db, "role_menu.ended")
    assert ended["this_pass"] == plan.members == 3 and ended["kept"] == plan.keep == 1
    assert {r.id for r in kept.roles} == {11} and all(not one.roles for one in gone)


async def test_an_ad_hoc_grant_or_push_back_on_a_timed_role_is_refused_in_words(bot, db, lead):
    await timed_list(db, 10)
    member = FakeMember(bot.guild, user_id=900)

    grant_id, said = await cog_module.grant_role(
        bot, bot.guild, lead, member, bot.guild.get_role(10), 7
    )

    assert grant_id is None and "is a timed role, so it is given from an event" in said
    assert member.edits == []
    a = await an_event(db, "a", ends_at=LATER, title="Back to Black")
    await give(bot, lead, a, 10, member)
    row = await open_grant_on(db, 900, 10, a["id"])
    until, said = await cog_module.extend_role(bot, bot.guild, lead, row, 3)
    assert until is None and "ends with **Back to Black**" in said


async def test_ending_one_assignment_keeps_the_role_another_event_holds(bot, db, lead):
    await timed_list(db, 10)
    a = await an_event(db, "a", ends_at=LATER)
    b = await an_event(db, "b", ends_at=LATER, title="Fall Fest")
    member = FakeMember(bot.guild, user_id=900)
    await give(bot, lead, a, 10, member)
    await give(bot, lead, b, 10, member)

    done, said = await cog_module.revoke_grant(
        bot, bot.guild, lead, await open_grant_on(db, 900, 10, a["id"])
    )

    assert done and "keeps **role-10** through **Fall Fest**" in said
    assert 10 in [r.id for r in member.roles]
    found = await cog_module.take_event_role(bot, bot.guild, lead, b, 10, [member])
    assert found["given"] == [900] and 10 not in [r.id for r in member.roles]


async def test_the_root_opens_on_open_events_with_the_ended_ones_folded(bot, db, lead):
    await timed_list(db, 10)
    a = await an_event(db, "a", ends_at=LATER, title="Back to Black")
    await an_event(db, "z", title="Old one")
    await db.conn.execute("UPDATE role_menus SET ended_at = ? WHERE name = 'z'", (PAST,))
    await db.conn.commit()
    await give(bot, lead, a, 10, FakeMember(bot.guild, user_id=900))

    interaction = await open_the_panel(bot, lead)

    assert interaction.embed.title == "Timed roles"
    assert "**Back to Black** · ends <t:" in interaction.body and "· 1 people" in interaction.body
    assert "Old one" not in interaction.body
    assert labels(interaction.view) == [
        "New event…",
        "Timed roles…",
        "Grants…",
        "Ended (1)…",
        "Logs",
        "Refresh",
    ]
    await press(interaction, "Ended (1)…")
    assert "**Old one** · ended" in interaction.body


async def another_marathon(db, ends_at, url):
    cur = await db.conn.execute(
        "INSERT INTO marathons(guild_id, name, source, source_ref, schedule_url, added_by, "
        "added_at, ends_at) VALUES (?, 'Fall Fest', 'gdq', 'y', ?, 1, ?, ?)",
        (GUILD, url, PAST, ends_at),
    )
    await db.conn.commit()
    return cur.lastrowid


async def test_new_event_offers_marathons_without_one_and_a_typed_event(bot, db, lead):
    await timed_list(db, 10)
    taken = await another_marathon(db, LATER, "https://taken")
    free = await marathon_with(db, SOON)
    await cog_module.make_event(bot, bot.guild, lead, "Taken", marathon_id=taken)
    interaction = await open_the_panel(bot, lead)
    await press(interaction, "New event…")

    offered = picker(interaction.view, "Ends with a marathon…")
    assert [one.value for one in offered.options] == [str(free)]
    await choose(interaction, "Ends with a marathon…", [str(free)])
    assert interaction.embed.title == "Back to Black 2027"
    assert "Fill from the schedule" in labels(interaction.view)
    assert "Attach a marathon…" not in labels(interaction.view)

    await press(interaction, "Back")
    await press(interaction, "New event…")
    await press(interaction, "No marathon yet…")
    modal = interaction.response.modals[-1]
    modal.name._value = "Back to Black 2027"
    modal.typed._value = "2099-02-28"
    await modal.on_submit(interaction)
    made = await get_menu(db, GUILD, "back-to-black-2027-2")
    assert made is not None and made["ends_source"] == "date"
    assert "(date, no marathon)" in interaction.body
    assert "Attach a marathon…" in labels(interaction.view)


async def test_the_timed_list_refuses_a_role_it_could_not_strip_and_keeps_one_still_assigned(
    bot, db, lead
):
    await timed_list(db, 10)
    a = await an_event(db, "a", ends_at=LATER)
    await give(bot, lead, a, 10, FakeMember(bot.guild, user_id=900))
    bot.guild.stuck_roles = {13}
    interaction = await open_the_panel(bot, lead)
    await press(interaction, "Timed roles…")

    await choose(interaction, "Add a role…", [SimpleNamespace(id=13)])
    assert "could not take **role-13** off anybody" in interaction.sent
    await choose(interaction, "Add a role…", [SimpleNamespace(id=14)])
    assert "**role-14** is a timed role now." == interaction.sent
    await choose(interaction, "Remove a role…", ["10"])
    assert "still assigned 1 time(s)" in interaction.sent
    assert await timed.role_ids(db, GUILD) == [10, 14]
    await choose(interaction, "Remove a role…", ["14"])
    assert await timed.role_ids(db, GUILD) == [10]


async def test_give_roles_takes_twenty_five_a_batch_and_keeps_a_running_count(bot, db, lead):
    await timed_list(db, 10)
    await an_event(db, "a", ends_at=LATER)
    people = [FakeMember(bot.guild, user_id=900 + n) for n in range(3)]
    interaction = await open_a_menu(bot, lead, "a")
    await press(interaction, "Give roles…")

    await choose(interaction, "A timed role…", ["10"])
    who = picker(interaction.view, "Up to 25 people…")
    assert who.max_values == 25
    await choose(interaction, "Up to 25 people…", people[:2])
    assert "<@&10> · given to 2" in interaction.body
    await choose(interaction, "Up to 25 people…", people[1:])
    assert "<@&10> · given to 3" in interaction.body
    assert "1 already assigned" in interaction.sent
    assert all(10 in [r.id for r in one.roles] for one in people)
    assert all(row["menu_id"] for row in await grants.open_grants(db, GUILD))


async def schedule_runs(db, marathon_id, people):
    await db.conn.execute(
        "INSERT INTO marathon_runs(marathon_id, external_id, game, people, scheduled_at, "
        "first_seen_at, last_seen_at) VALUES (?, 'r1', 'Game', ?, ?, ?, ?)",
        (marathon_id, json.dumps(people), SOON, PAST, PAST),
    )
    await db.conn.commit()


async def test_fill_from_the_schedule_previews_counts_and_unmatched_and_a_rerun_adds_the_missing(
    bot, db, lead
):
    await timed_list(db, 10, 11)
    await bot.store.set(GUILD, "rolemenu_fill_runner_role_id", 10)
    await bot.store.set(GUILD, "rolemenu_fill_commentator_role_id", 11)
    marathon_id = await marathon_with(db, LATER)
    await schedule_runs(
        db,
        marathon_id,
        [
            {"name": "Ada", "part": "runner", "user_id": 900},
            {"name": "Stranger", "part": "runner"},
            {"name": "Couch", "part": "commentator", "user_id": 901},
            {"name": "Hosty", "part": "host", "user_id": 902},
        ],
    )
    ada = FakeMember(bot.guild, user_id=900)
    FakeMember(bot.guild, user_id=901)
    FakeMember(bot.guild, user_id=902)
    event = await cog_module.make_event(bot, bot.guild, lead, "BtB", marathon_id=marathon_id)
    interaction = await open_a_menu(bot, lead, event["name"])
    await press(interaction, "Fill from the schedule")

    assert "1 matched · 1 to give <@&10>" in interaction.body
    assert "not matched to a member (1): Stranger" in interaction.body
    assert "no role set (rolemenu_fill_host_role_id), skipped" in interaction.body
    assert await timed.event_grants(db, GUILD, event["id"]) == []
    await press(interaction, "Give them the roles")
    assert "2 given" in interaction.sent
    rows = await timed.event_grants(db, GUILD, event["id"])
    assert {(r["user_id"], r["role_id"], r["source"]) for r in rows} == {
        (900, 10, "schedule"),
        (901, 11, "schedule"),
    }
    assert "Give them the roles" not in labels(interaction.view)

    await timed.close_member_roles(db, GUILD, 900, [10], "by_hand")
    ada.roles = []
    await press(interaction, "Refresh")
    assert "1 matched · 1 to give <@&10>" in interaction.body
    await press(interaction, "Give them the roles")
    assert len(await timed.event_grants(db, GUILD, event["id"])) == 2


async def test_attach_a_marathon_that_ends_earlier_holds_the_earlier_end_for_staff(
    bot, db, lead
):
    await store_notice_channel(bot)
    await timed_list(db, 10)
    marathon_id = await marathon_with(db, "2099-01-10T05:00:00+00:00")
    event = await an_event(db, "a", ends_at="2099-02-28T06:59:00+00:00")
    interaction = await open_a_menu(bot, lead, "a")
    await press(interaction, "Attach a marathon…")

    await choose(interaction, "Ends with a marathon…", [str(marathon_id)])

    fresh = await menu_row(db, event["id"])
    assert fresh["ends_source"] == "marathon" and fresh["ends_marathon_id"] == marathon_id
    assert fresh["ends_at"] == "2099-02-28T06:59:00+00:00"
    assert fresh["ends_held_at"] == "2099-01-11T05:00:00+00:00"
    assert "Use the earlier end" in labels(interaction.view)
    assert "Held:" in interaction.sent
    assert bot.guild.channels[STAFF_CHANNEL].messages
    assert "role_menu.end_held" in await action_kinds(db)


async def test_attach_a_marathon_that_ends_later_follows_it_at_once(bot, db, lead):
    await timed_list(db, 10)
    marathon_id = await marathon_with(db, "2099-03-10T05:00:00+00:00")
    event = await an_event(db, "a", ends_at="2099-02-28T06:59:00+00:00")

    end = await cog_module.attach_marathon(bot, bot.guild, lead, event, marathon_id)

    assert end == "2099-03-11T05:00:00+00:00"
    assert (await menu_row(db, event["id"]))["ends_held_at"] is None


async def test_delete_is_refused_while_people_are_assigned_to_an_end_still_to_come(
    bot, db, lead
):
    await timed_list(db, 10)
    a = await an_event(db, "a", ends_at=LATER)
    await give(bot, lead, a, 10, FakeMember(bot.guild, user_id=900))
    interaction = await open_a_menu(bot, lead, "a")

    await press(interaction, "Delete it")

    assert "1 people are assigned to it" in interaction.sent
    assert await get_menu(db, GUILD, "a") is not None


async def test_every_event_card_control_sits_inside_discords_five_rows(bot, db, lead):
    await timed_list(db, 10)
    marathon_id = await marathon_with(db, LATER)
    event = await cog_module.make_event(bot, bot.guild, lead, "BtB", marathon_id=marathon_id)
    await give(bot, lead, event, 10, FakeMember(bot.guild, user_id=900))
    await db.conn.execute("UPDATE role_menus SET ends_held_at = ?", (SOON,))
    await db.conn.commit()

    card = await open_a_menu(bot, lead, event["name"])

    assert all(0 <= one.row <= 4 for one in card.view.children)
    for label in ("Give roles…", "Fill from the schedule", "Take roles off…"):
        assert label in labels(card.view)
    assert "Use the earlier end" in labels(card.view)


# --- a timed role added by hand ------------------------------------------------------------------


def audit_entry(target, user, role_ids, *, ago=1):
    return SimpleNamespace(
        target=target,
        user=user,
        created_at=datetime.now(UTC) - timedelta(minutes=ago),
        after=SimpleNamespace(roles=[SimpleNamespace(id=one) for one in role_ids]),
    )


async def added_by_hand(bot, member, *role_ids):
    before = SimpleNamespace(roles=list(member.roles))
    member.roles = [*member.roles, *(FakeRole(one) for one in role_ids)]
    await RoleMenus(bot).on_member_update(before, member)


def posts(bot):
    return bot.guild.channels[STAFF_CHANNEL].messages


async def test_a_timed_role_added_by_hand_pings_who_added_it_with_the_open_events(bot, db, lead):
    await store_notice_channel(bot)
    await timed_list(db, 10, 11)
    await an_event(db, "a", ends_at=LATER, title="Back to Black")
    member = FakeMember(bot.guild, user_id=900)
    bot.guild.me = SimpleNamespace(id=1, guild_permissions=SimpleNamespace(view_audit_log=True))
    staffer = FakeMember(bot.guild, user_id=55, display_name="Sky")
    bot.guild.audit_entries = [audit_entry(member, staffer, (10, 11))]

    await added_by_hand(bot, member, 10, 11)

    [post] = posts(bot)
    assert post.kwargs["content"].startswith("<@55> gave <@900> <@&10>, <@&11> by hand.")
    assert [one.id for one in post.kwargs["allowed_mentions"].users] == [55]
    [pick, new] = post.kwargs["view"].children
    assert [one.label for one in pick.item.options] == ["Back to Black"]
    assert new.item.label == "New event…"

    await added_by_hand(bot, member)
    before = SimpleNamespace(roles=[r for r in member.roles if r.id != 10])
    await RoleMenus(bot).on_member_update(before, member)
    assert len(posts(bot)) == 1


async def test_without_the_audit_log_the_post_names_nobody_and_says_why(bot, db, lead):
    await store_notice_channel(bot)
    await timed_list(db, 10)
    member = FakeMember(bot.guild, user_id=900)
    bot.guild.me = SimpleNamespace(id=1, guild_permissions=SimpleNamespace(view_audit_log=False))

    await added_by_hand(bot, member, 10)

    [post] = posts(bot)
    assert post.kwargs["content"].startswith("Somebody gave <@900> <@&10> by hand.")
    assert "cannot read the audit log" in post.kwargs["content"]
    assert "No event is open" in post.kwargs["content"]
    assert post.kwargs["allowed_mentions"].users is False
    assert [type(one).__name__ for one in post.kwargs["view"].children] == ["ByHandNew"]


async def test_a_silent_audit_log_or_the_bots_own_add_is_handled_honestly(bot, db, lead):
    await store_notice_channel(bot)
    await timed_list(db, 10, 11)
    member = FakeMember(bot.guild, user_id=900)
    me = SimpleNamespace(id=1, guild_permissions=SimpleNamespace(view_audit_log=True))
    bot.guild.me = me
    bot.guild.audit_entries = [
        audit_entry(member, me, (11,)),
        audit_entry(member, lead, (10,), ago=30),
    ]

    await added_by_hand(bot, member, 10)
    assert "The audit log did not say who added it." in posts(bot)[0].kwargs["content"]

    await added_by_hand(bot, member, 11)
    assert len(posts(bot)) == 1


async def test_picking_an_event_attaches_the_role_even_after_a_restart(bot, db, lead):
    await store_notice_channel(bot)
    await timed_list(db, 10)
    a = await an_event(db, "a", ends_at=LATER, title="Back to Black")
    member = FakeMember(bot.guild, user_id=900)
    await added_by_hand(bot, member, 10)
    [post] = posts(bot)
    custom = post.kwargs["view"].children[0].item.custom_id

    match = re.fullmatch(cog_module.hand.PICK_TEMPLATE, custom)
    fresh = discord.ui.Select(
        custom_id=custom, options=[discord.SelectOption(label="x", value="0")]
    )
    item = await cog_module.ByHandPick.from_custom_id(FakeInteraction(bot, lead), fresh, match)
    item.item._values = [str(a["id"])]
    interaction = FakeInteraction(bot, lead)
    await item.callback(interaction)

    row = await open_grant_on(db, 900, 10, a["id"])
    assert row is not None and row["source"] == "by_hand_attached"
    assert "Attached to **Back to Black**" in interaction.sent
    assert "attached to **Back to Black** by <@1>" in post.kwargs["content"]
    assert post.kwargs["view"] is None

    again = FakeInteraction(bot, lead)
    await item.callback(again)
    assert "already attached to **Back to Black**" in again.sent

    stranger = FakeInteraction(bot, FakeMember(bot.guild, user_id=77))
    await item.callback(stranger)
    assert len(await timed.event_grants(db, GUILD, a["id"])) == 1


async def test_new_event_on_a_by_hand_post_makes_the_event_and_attaches_to_it(bot, db, lead):
    await store_notice_channel(bot)
    await timed_list(db, 10)
    member = FakeMember(bot.guild, user_id=900)
    await added_by_hand(bot, member, 10)
    [post] = posts(bot)
    new = post.kwargs["view"].children[-1]
    interaction = FakeInteraction(bot, lead)

    await new.callback(interaction)
    modal = interaction.response.modals[-1]
    modal.name._value = "Back to Black 2027"
    modal.typed._value = "2099-02-28"
    await modal.on_submit(FakeInteraction(bot, lead))

    event = await get_menu(db, GUILD, "back-to-black-2027")
    assert event is not None and await open_grant_on(db, 900, 10, event["id"]) is not None


async def test_a_role_that_came_off_asks_again_the_next_time_it_is_added_by_hand(bot, db, lead):
    await store_notice_channel(bot)
    await timed_list(db, 10)
    member = FakeMember(bot.guild, user_id=900)
    await added_by_hand(bot, member, 10)
    await an_event(db, "a", ends_at=PAST)

    await tick(bot)
    assert 10 not in [r.id for r in member.roles]
    await added_by_hand(bot, member, 10)

    asked = [one for one in posts(bot) if "by hand." in str(one.kwargs.get("content"))]
    assert len(asked) == 2


async def test_a_give_discord_refuses_logs_a_failure_and_never_the_success_kind(bot, db, lead):
    await timed_list(db, 10)
    a = await an_event(db, "a", ends_at=LATER)
    member = FakeMember(bot.guild, user_id=900, display_name="Bo")
    member.edit_raises = discord.HTTPException(_Refused(403), "no")

    found = await give(bot, lead, a, 10, member)

    assert found["refused"] == [900] and "1 refused" in found["said"]
    kinds = await action_kinds(db)
    assert "role_menu.assign_failed" in kinds and "role_menu.assign" not in kinds
    assert await open_grant_on(db, 900, 10, a["id"]) is None
