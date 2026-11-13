from types import SimpleNamespace

import pytest

from black_bloc import rolemenu_panels as panels
from black_bloc.cogs.community.role_menus import (
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


async def test_taking_a_panel_down_deletes_it_and_keeps_the_channel(bot, db):
    """Staff (and pings' take-over) can still take an old panel down; nothing else does."""
    menu_id = await a_panel(db)
    menu = await get_menu(db, GUILD, "pronouns")

    assert await panels.unpost(bot, menu, 77) is True

    assert bot.channels[PANEL_CHANNEL].deleted == [600]
    [row] = await unposted_menus(db)
    assert row["id"] == menu_id and row["channel_id"] == PANEL_CHANNEL
    assert "role_menu.unposted" in await kinds(db)


async def test_the_guard_refuses_a_take_down_and_nothing_is_touched(bot, db):
    bot.guard = FakeGuard()
    await a_panel(db)

    assert await panels.unpost(bot, await get_menu(db, GUILD, "pronouns"), 77) is False

    assert bot.channels[PANEL_CHANNEL].deleted == []
    assert "role_menu.would_unpost" in await kinds(db)


async def test_a_panel_is_never_posted_again_once_self_pick_is_retired(bot, db):
    """Request #17: Discord's Channels & Roles owns self-pick, so repost posts nothing."""
    await a_panel(db, message_id=None)
    await seed_default_menus(db, GUILD)
    before = [tuple(row) for row in await list_menus(db, GUILD)]

    for menu in await list_menus(db, GUILD):
        assert await panels.repost(bot, menu, 77) is False

    assert all(channel.sent == [] for channel in bot.channels.values())
    assert bot.views == []
    assert [tuple(row) for row in await list_menus(db, GUILD)] == before
    assert await get_options(db, (await get_menu(db, GUILD, "pronouns"))["id"])


def test_nothing_on_boot_or_on_a_settings_write_reconciles_panels_any_more():
    """The boot sweep took panels down while picking was off; nothing deletes them now."""
    assert not hasattr(panels, "reconcile")
    assert not hasattr(panels, "panels_on_boot")
    assert not hasattr(panels, "install")
