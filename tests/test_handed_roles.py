import json

import pytest

from black_bloc import handed_roles
from black_bloc.actionlog import log_action
from black_bloc.cogs.community.role_menus import add_option, create_menu
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore

GUILD = 7
AT = "2026-10-20T09:00:00+00:00"
EVENTS_ROLE = 50
FAN_ROLE = 51
MENU_ROLE = 60
OTHER_ROLE = 61
APPLICATION_ROLE = 62


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id
        self.name = f"role-{role_id}"


class FakeMember:
    def __init__(self, guild, user_id, roles=()):
        self.id = user_id
        self.display_name = f"m{user_id}"
        self.roles = [FakeRole(one) for one in roles]
        self.dms = []
        self.refuses = False
        guild.members[user_id] = self

    def wears(self, role_id):
        return any(role.id == role_id for role in self.roles)

    async def remove_roles(self, role, reason=None):
        if self.refuses:
            raise RuntimeError("missing permissions")
        self.roles = [one for one in self.roles if one.id != role.id]

    async def edit(self, roles=None, reason=None):
        if self.refuses:
            raise RuntimeError("missing permissions")
        self.roles = list(roles)

    async def send(self, content=None, **_kwargs):
        self.dms.append(content)


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black in a Flash!"
        self.members = {}

    def get_member(self, user_id):
        return self.members.get(int(user_id))

    def get_role(self, role_id):
        return FakeRole(int(role_id))

    def get_channel(self, _channel_id):
        return None


class FakeBot:
    def __init__(self, db, store, guild):
        self.db = db
        self.store = store
        self.guild = guild

    def get_guild(self, guild_id):
        return self.guild if guild_id == self.guild.id else None

    def get_channel(self, _channel_id):
        return None


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    store = SettingsStore(db, load_settings(_env_file=None))
    await store.load()
    await store.set(GUILD, "pings_mode", "on")
    return FakeBot(db, store, FakeGuild())


async def pinged(bot, kind, user_id, role_id, *, web=False):
    await log_action(
        bot,
        bot.guild,
        f"web.{kind}" if web else kind,
        actor=user_id,
        target=user_id,
        details={"role_id": role_id},
    )


async def menu_with(bot, *role_ids):
    menu_id = await create_menu(bot.db, GUILD, "interests", "Interests")
    for role_id in role_ids:
        await add_option(bot.db, menu_id, role_id, f"label-{role_id}")
    return menu_id


async def taken_rows(bot, kind):
    cur = await bot.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id", (kind,)
    )
    return [json.loads(row["details"]) for row in await cur.fetchall()]


# --- the dry run --------------------------------------------------------------------------------


async def test_the_pings_dry_run_counts_only_roles_pings_put_on_and_still_worn(bot):
    followed = FakeMember(bot.guild, 1, roles=(FAN_ROLE,))
    events = FakeMember(bot.guild, 2, roles=(EVENTS_ROLE,))
    stopped = FakeMember(bot.guild, 3, roles=(FAN_ROLE,))
    elsewhere = FakeMember(bot.guild, 4, roles=(EVENTS_ROLE, FAN_ROLE))
    dropped_by_hand = FakeMember(bot.guild, 5, roles=())
    await pinged(bot, "pings.follow", followed.id, FAN_ROLE)
    await pinged(bot, "pings.events_on", events.id, EVENTS_ROLE, web=True)
    await pinged(bot, "pings.follow", stopped.id, FAN_ROLE)
    await pinged(bot, "pings.unfollow", stopped.id, FAN_ROLE)
    await pinged(bot, "pings.follow", dropped_by_hand.id, FAN_ROLE)

    found = await handed_roles.held(bot, bot.guild, "pings_mode")

    assert [(one.user_id, one.role_id) for one in found] == [(1, FAN_ROLE), (2, EVENTS_ROLE)]
    assert elsewhere.wears(EVENTS_ROLE), "a role from onboarding or by hand is never counted"
    said = await handed_roles.asked(bot, bot.guild, "pings_mode", "off")
    assert said.startswith("**2** members hold ping roles Black Bloc handed out")


async def test_role_menus_have_no_switch_to_take_roles_back_any_more(bot):
    """Request #17: member self-pick is retired with `rolemenu_mode`; a menu's own end is how
    its roles come off now, so only pings keep a take-back."""
    assert handed_roles.KEYS == ("pings_mode",)
    assert await handed_roles.held(bot, bot.guild, "rolemenu_mode") == []
    assert await handed_roles.asked(bot, bot.guild, "rolemenu_mode", "off") is None


async def test_nothing_held_asks_nothing_and_on_never_asks(bot):
    FakeMember(bot.guild, 1, roles=(FAN_ROLE,))
    await pinged(bot, "pings.follow", 1, FAN_ROLE)

    assert await handed_roles.asked(bot, bot.guild, "pings_mode", "on") is None
    assert await handed_roles.asked(bot, bot.guild, "golive_mode", "off") is None


# --- taking them back ---------------------------------------------------------------------------


async def test_switching_pings_off_takes_back_its_roles_once_with_one_log_row_and_no_dm(bot):
    handed_roles.install(bot)
    followed = FakeMember(bot.guild, 1, roles=(FAN_ROLE, OTHER_ROLE))
    elsewhere = FakeMember(bot.guild, 2, roles=(EVENTS_ROLE,))
    await pinged(bot, "pings.follow", followed.id, FAN_ROLE)

    await bot.store.set(GUILD, "pings_mode", "off", by=99)

    assert [role.id for role in followed.roles] == [OTHER_ROLE]
    assert elsewhere.wears(EVENTS_ROLE)
    assert followed.dms == []
    [row] = await taken_rows(bot, "pings.roles_taken_back")
    assert (row["members"], row["roles"], row["failed"], row["taken"]) == (
        1,
        1,
        0,
        [[1, FAN_ROLE]],
    )
    await bot.store.set(GUILD, "pings_mode", "on")
    assert not followed.wears(FAN_ROLE), "switching back on gives nothing back"
    followed.roles.append(FakeRole(FAN_ROLE))
    assert await handed_roles.held(bot, bot.guild, "pings_mode") == [], (
        "worn again from elsewhere after the take-back, it is no longer pings' to take"
    )


async def test_a_role_discord_refuses_to_remove_is_counted_failed_and_stays_on_the_ledger(bot):
    stuck = FakeMember(bot.guild, 1, roles=(FAN_ROLE,))
    stuck.refuses = True
    await pinged(bot, "pings.follow", stuck.id, FAN_ROLE)

    done = await handed_roles.take_back(bot, bot.guild, "pings_mode", 99)

    assert (done["roles"], done["failed"]) == (0, 1)
    assert [one.user_id for one in await handed_roles.held(bot, bot.guild, "pings_mode")] == [1]


async def test_a_reset_to_the_off_default_takes_them_back_too(bot):
    handed_roles.install(bot)
    followed = FakeMember(bot.guild, 1, roles=(FAN_ROLE,))
    await pinged(bot, "pings.follow", followed.id, FAN_ROLE)

    await bot.store.clear(GUILD, "pings_mode", by=99)

    assert not followed.wears(FAN_ROLE)


async def test_with_the_switch_off_pings_go_off_and_every_role_stays(bot):
    handed_roles.install(bot)
    await bot.store.set(GUILD, "pings_off_takes_roles_back", False)
    followed = FakeMember(bot.guild, 1, roles=(FAN_ROLE,))
    await pinged(bot, "pings.follow", followed.id, FAN_ROLE)

    assert await handed_roles.asked(bot, bot.guild, "pings_mode", "off") is None
    await bot.store.set(GUILD, "pings_mode", "off", by=99)

    assert followed.wears(FAN_ROLE)
    assert await taken_rows(bot, "pings.roles_taken_back") == []


async def test_in_test_mode_the_take_back_is_only_logged(bot):
    bot.guard = object()
    followed = FakeMember(bot.guild, 1, roles=(FAN_ROLE,))
    await pinged(bot, "pings.follow", followed.id, FAN_ROLE)

    assert await handed_roles.take_back(bot, bot.guild, "pings_mode", 99) is None

    assert followed.wears(FAN_ROLE)
    [row] = await taken_rows(bot, "pings.would_take_back")
    assert row["taken"] == [[1, FAN_ROLE]]
