import asyncio
from types import SimpleNamespace

import discord
import pytest

from black_bloc import command_visibility as cv
from black_bloc import rolemenu_panels as panels
from black_bloc.cogs.community.role_menus import (
    MODE_KEY,
    add_option,
    clear_message,
    create_menu,
    get_menu,
    get_options,
    list_menus,
    seed_default_menus,
    set_message,
    unposted_menus,
)
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore

GUILD = 7
OTHER_GUILD = 8
TEST_CHANNEL = 111
LOG_CHANNEL = 222
PANEL_CHANNEL = 333
GONE_CHANNEL = 444


class _Refused:
    def __init__(self, status):
        self.status = status
        self.reason = "refused"


class FakeMessage:
    def __init__(self, channel, message_id, raises):
        self.channel = channel
        self.id = message_id
        self._raises = raises

    async def delete(self):
        if self._raises is not None:
            raise self._raises
        self.channel.deleted.append(self.id)


class FakeChannel:
    def __init__(self, channel_id):
        self.id = channel_id
        self.sent = []
        self.deleted = []
        self.delete_raises = None
        self.send_raises = None
        self.next_id = 9000

    def get_partial_message(self, message_id):
        return FakeMessage(self, message_id, self.delete_raises)

    async def send(self, **kwargs):
        if self.send_raises is not None:
            raise self.send_raises
        self.next_id += 1
        self.sent.append(kwargs)
        return SimpleNamespace(id=self.next_id, jump_url="https://example.invalid/1")


class FakeGuard:
    def __init__(self, allowed=TEST_CHANNEL):
        self.allowed = allowed

    def allows_channel(self, channel_id):
        return channel_id == self.allowed

    def refusal_message(self):
        return "test mode"


class FakeGuild:
    def __init__(self, guild_id):
        self.id = guild_id

    def get_channel(self, channel_id):
        return None


class FakeBot:
    def __init__(self, db, store):
        self.db = db
        self.store = store
        self.guard = None
        self.views = []
        self.channels = {
            LOG_CHANNEL: FakeChannel(LOG_CHANNEL),
            TEST_CHANNEL: FakeChannel(TEST_CHANNEL),
            PANEL_CHANNEL: FakeChannel(PANEL_CHANNEL),
        }

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_guild(self, guild_id):
        return FakeGuild(guild_id)

    def add_view(self, view, *, message_id=None):
        self.views.append((view, message_id))


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOG_CHANNEL)
    await store.set(GUILD, MODE_KEY, "on")
    return FakeBot(db, store)


async def a_panel(db, name="pronouns", channel_id=PANEL_CHANNEL, message_id=600, guild=GUILD):
    menu_id = await create_menu(db, guild, name, "Pronouns", None, "multiple")
    await add_option(db, menu_id, 1, "He/Him")
    await add_option(db, menu_id, 2, "She/Her")
    await set_message(db, menu_id, channel_id, message_id or 1)
    if message_id is None:
        await clear_message(db, menu_id)
    return menu_id


async def logged(db):
    cur = await db.conn.execute("SELECT kind, actor_id, details FROM action_log ORDER BY id")
    return [dict(row) for row in await cur.fetchall()]


async def kinds(db):
    return [row["kind"] for row in await logged(db)]


async def test_turning_it_off_takes_the_panel_down_and_keeps_the_channel(bot, db):
    menu_id = await a_panel(db)
    await bot.store.set(GUILD, MODE_KEY, "off")

    done = await panels.reconcile(bot)

    assert done == {"unposted": 1, "reposted": 0}
    assert bot.channels[PANEL_CHANNEL].deleted == [600]
    menu = await get_menu(db, GUILD, "pronouns")
    assert menu["message_id"] is None and menu["channel_id"] == PANEL_CHANNEL
    assert panels.UNPOSTED in await kinds(db)
    assert [row["role_id"] for row in await get_options(db, menu_id)] == [1, 2]


async def test_turning_it_on_posts_every_remembered_menu_in_its_channel(bot, db):
    await a_panel(db, message_id=None)

    done = await panels.reconcile(bot, actor=77)

    assert done == {"unposted": 0, "reposted": 1}
    channel = bot.channels[PANEL_CHANNEL]
    assert len(channel.sent) == 1 and channel.sent[0]["view"].is_persistent()
    menu = await get_menu(db, GUILD, "pronouns")
    assert menu["message_id"] == channel.next_id and menu["channel_id"] == PANEL_CHANNEL
    assert bot.views == [(channel.sent[0]["view"], channel.next_id)]
    assert panels.REPOSTED in await kinds(db)
    assert [row["actor_id"] for row in await logged(db)][-1] == 77


async def test_a_menu_that_was_never_posted_is_left_alone_when_it_comes_back_on(bot, db):
    await create_menu(db, GUILD, "draft", "Draft", None, "multiple")

    done = await panels.reconcile(bot)

    assert done == {"unposted": 0, "reposted": 0}
    assert bot.channels[PANEL_CHANNEL].sent == []


async def test_the_guard_refuses_the_delete_and_nothing_is_touched(bot, db):
    await a_panel(db)
    bot.guard = FakeGuard(allowed=TEST_CHANNEL)
    await bot.store.set(GUILD, MODE_KEY, "off")

    done = await panels.reconcile(bot)

    assert done == {"unposted": 0, "reposted": 0}
    assert bot.channels[PANEL_CHANNEL].deleted == []
    assert (await get_menu(db, GUILD, "pronouns"))["message_id"] == 600
    assert await kinds(db) == [panels.WOULD_UNPOST]


async def test_the_guard_refuses_the_repost_and_nothing_is_posted(bot, db):
    await a_panel(db, message_id=None)
    bot.guard = FakeGuard(allowed=TEST_CHANNEL)

    done = await panels.reconcile(bot)

    assert done == {"unposted": 0, "reposted": 0}
    assert bot.channels[PANEL_CHANNEL].sent == []
    assert (await get_menu(db, GUILD, "pronouns"))["message_id"] is None
    assert panels.WOULD_REPOST in await kinds(db)


async def test_an_http_failure_is_logged_and_the_next_menu_still_comes_down(bot, db):
    await a_panel(db, name="pronouns", channel_id=GONE_CHANNEL, message_id=601)
    await a_panel(db, name="playstyle", message_id=602)
    bot.channels[GONE_CHANNEL] = FakeChannel(GONE_CHANNEL)
    bot.channels[GONE_CHANNEL].delete_raises = discord.HTTPException(_Refused(403), "no")
    await bot.store.set(GUILD, MODE_KEY, "off")

    done = await panels.reconcile(bot)

    assert done == {"unposted": 1, "reposted": 0}
    assert bot.channels[PANEL_CHANNEL].deleted == [602]
    assert (await get_menu(db, GUILD, "pronouns"))["message_id"] == 601
    assert (await get_menu(db, GUILD, "playstyle"))["message_id"] is None
    assert await kinds(db) == [panels.UNPOST_FAILED, panels.UNPOSTED]


async def test_a_panel_somebody_already_deleted_is_simply_forgotten(bot, db):
    await a_panel(db)
    bot.channels[PANEL_CHANNEL].delete_raises = discord.NotFound(_Refused(404), "gone")
    await bot.store.set(GUILD, MODE_KEY, "off")

    done = await panels.reconcile(bot)

    assert done == {"unposted": 1, "reposted": 0}
    assert (await get_menu(db, GUILD, "pronouns"))["message_id"] is None
    assert await kinds(db) == [panels.UNPOSTED]


async def test_a_channel_the_bot_cannot_see_is_a_failure_not_a_silent_success(bot, db):
    await a_panel(db, channel_id=GONE_CHANNEL, message_id=601)
    await bot.store.set(GUILD, MODE_KEY, "off")

    done = await panels.reconcile(bot)

    assert done == {"unposted": 0, "reposted": 0}
    assert (await get_menu(db, GUILD, "pronouns"))["message_id"] == 601
    assert await kinds(db) == [panels.UNPOST_FAILED]


async def test_a_send_discord_refuses_leaves_the_row_unposted_and_says_so(bot, db):
    await a_panel(db, message_id=None)
    bot.channels[PANEL_CHANNEL].send_raises = discord.HTTPException(_Refused(403), "no")

    done = await panels.reconcile(bot)

    assert done == {"unposted": 0, "reposted": 0}
    assert (await get_menu(db, GUILD, "pronouns"))["message_id"] is None
    assert panels.REPOST_FAILED in await kinds(db)


async def test_a_staff_menu_and_an_empty_menu_are_never_posted(bot, db):
    staff_id = await create_menu(db, GUILD, "runner-status", "Runner", None, "staff")
    await add_option(db, staff_id, 10, "Runner")
    await set_message(db, staff_id, PANEL_CHANNEL, 700)
    await clear_message(db, staff_id)
    empty_id = await create_menu(db, GUILD, "empty", "Empty", None, "multiple")
    await set_message(db, empty_id, PANEL_CHANNEL, 701)
    await clear_message(db, empty_id)

    done = await panels.reconcile(bot)

    assert done == {"unposted": 0, "reposted": 0}
    assert bot.channels[PANEL_CHANNEL].sent == []
    assert len(await unposted_menus(db)) == 2


async def test_another_guild_that_is_still_on_keeps_its_panel(bot, db):
    await a_panel(db, name="pronouns")
    await a_panel(db, name="pronouns", message_id=650, guild=OTHER_GUILD)
    await bot.store.set(OTHER_GUILD, MODE_KEY, "on")
    await bot.store.set(GUILD, MODE_KEY, "off")

    done = await panels.reconcile(bot)

    assert done == {"unposted": 1, "reposted": 0}
    assert bot.channels[PANEL_CHANNEL].deleted == [600]
    assert (await get_menu(db, OTHER_GUILD, "pronouns"))["message_id"] == 650


async def test_the_switch_never_changes_a_menu_row_an_option_or_the_seed(bot, db):
    await seed_default_menus(db, GUILD)
    menu = await get_menu(db, GUILD, "pronouns")
    await set_message(db, menu["id"], PANEL_CHANNEL, 600)

    def snapshot(rows):
        return [
            {key: row[key] for key in row.keys() if key != "message_id"} for row in rows
        ]

    async def whole(database):
        menus = await list_menus(database, GUILD)
        return snapshot(menus), {
            row["name"]: snapshot(await get_options(database, row["id"])) for row in menus
        }

    before = await whole(db)
    await bot.store.set(GUILD, MODE_KEY, "off")
    await panels.reconcile(bot)
    await bot.store.set(GUILD, MODE_KEY, "on")
    await panels.reconcile(bot)

    assert await whole(db) == before


async def test_nothing_at_all_happens_without_a_database(bot, db):
    await a_panel(db)
    await bot.store.set(GUILD, MODE_KEY, "off")
    bot.db = SimpleNamespace(is_connected=False)

    assert await panels.reconcile(bot) == {"unposted": 0, "reposted": 0}
    assert bot.channels[PANEL_CHANNEL].deleted == []


async def test_the_boot_reconcile_takes_panels_down_but_never_posts_one(bot, db):
    """A restart mid-flip converges one way only: nothing is posted behind the owner's back."""
    await a_panel(db, name="pronouns")
    await a_panel(db, name="playstyle", message_id=None, guild=OTHER_GUILD)
    await bot.store.set(OTHER_GUILD, MODE_KEY, "on")
    await bot.store.set(GUILD, MODE_KEY, "off")

    done = await panels.panels_on_boot(bot)

    assert done == {"unposted": 1, "reposted": 0}
    assert bot.channels[PANEL_CHANNEL].deleted == [600]
    assert bot.channels[PANEL_CHANNEL].sent == []
    assert len(await unposted_menus(db)) == 2
    assert panels.controller(bot).ready is True


@pytest.fixture
def waits(monkeypatch):
    seen = []
    gate = asyncio.Event()

    async def fake_wait(seconds):
        seen.append(seconds)
        await gate.wait()

    monkeypatch.setattr(cv, "_wait", fake_wait)
    return SimpleNamespace(seen=seen, gate=gate)


async def test_a_burst_of_flips_costs_one_run_and_the_last_state_wins(bot, db, waits):
    await a_panel(db)
    control = panels.install(bot)
    control.ready = True
    flips = cv.controller(bot)

    await bot.store.set(GUILD, MODE_KEY, "off", by=5)
    await bot.store.set(GUILD, MODE_KEY, "on", by=5)
    await bot.store.set(GUILD, MODE_KEY, "off", by=5)

    assert bot.channels[PANEL_CHANNEL].deleted == []
    waits.gate.set()
    await flips.task

    assert bot.channels[PANEL_CHANNEL].deleted == [600]
    assert bot.channels[PANEL_CHANNEL].sent == []
    assert (await get_menu(db, GUILD, "pronouns"))["message_id"] is None
    assert [row["actor_id"] for row in await logged(db)] == [5]


async def test_the_panels_wait_for_the_gateway_before_the_first_run(bot, db, waits):
    await a_panel(db)
    panels.install(bot)
    flips = cv.controller(bot)

    await bot.store.set(GUILD, MODE_KEY, "off")
    waits.gate.set()
    await flips.task

    assert bot.channels[PANEL_CHANNEL].deleted == []
    assert (await get_menu(db, GUILD, "pronouns"))["message_id"] == 600


async def test_installing_twice_registers_one_job_and_one_hook(bot):
    first = panels.install(bot)
    second = panels.install(bot)

    assert first is second
    assert cv.controller(bot).jobs == [first.run]
    assert len(bot.store._hooks[MODE_KEY]) == 1
