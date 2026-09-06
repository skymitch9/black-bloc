import asyncio
import json
from types import SimpleNamespace

import discord
import pytest

from black_bloc import command_visibility as cv
from black_bloc.bot import COGS, BlackBlocBot
from black_bloc.config import load_settings
from black_bloc.settings_store import KEY_CHOICES, KEY_TYPES, SettingsStore, parse_value

GUILD = 4242
TEST_CHANNEL = 555
MODE_KEY = "request_mode"
NAMES = ("help", "request", "settings")
DEV_GUILD = discord.Object(id=GUILD)


class FakeCommand:
    def __init__(self, name):
        self.name = name


class FakeTree:
    def __init__(self, names=NAMES):
        self.globals = {name: FakeCommand(name) for name in names}
        self.guilds = {GUILD: dict(self.globals)}
        self.removed = []
        self.added = []
        self.syncs = []

    def _where(self, guild):
        return self.globals if guild is None else self.guilds.setdefault(guild.id, {})

    def remove_command(self, name, *, guild=None):
        found = self._where(guild).pop(name, None)
        if found is not None:
            self.removed.append(name)
        return found

    def add_command(self, command, *, guild=None, override=False):
        self._where(guild)[command.name] = command
        self.added.append(command.name)

    def get_command(self, name, *, guild=None):
        return self._where(guild).get(name)

    async def sync(self, *, guild=None):
        self.syncs.append(guild.id)
        return list(self._where(guild).values())


class FakeGuild:
    def __init__(self):
        self.id = GUILD

    def get_channel(self, channel_id):
        return None


class FakeBot:
    def __init__(self, settings, store, db):
        self.settings = settings
        self.store = store
        self.db = db
        self.tree = FakeTree()
        self.guild = FakeGuild()

    def get_guild(self, guild_id):
        return self.guild if guild_id == GUILD else None

    def get_channel(self, channel_id):
        return None


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(
        _env_file=None, dev_guild_id=GUILD, test_mode=True, test_channel_id=TEST_CHANNEL
    )
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, MODE_KEY, "off")
    return FakeBot(settings, store, db)


@pytest.fixture
async def real_tree(tmp_path, monkeypatch):
    """Every top-level command name the bot really registers, from all of `COGS`."""
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(
        _env_file=None,
        dev_guild_id=GUILD,
        test_mode=True,
        test_channel_id=TEST_CHANNEL,
        database_path=tmp_path / "tree.sqlite3",
    )
    black_bloc = BlackBlocBot(settings)
    for name in COGS:
        await black_bloc.load_extension(name)
    names = {command.name for command in black_bloc.tree.get_commands()}
    await black_bloc.close()
    return names


@pytest.fixture
def waits(monkeypatch):
    """Every debounce and rate-limit wait, held open until the test opens the gate."""
    seen = []
    gate = asyncio.Event()

    async def fake_wait(seconds):
        seen.append(seconds)
        await gate.wait()

    monkeypatch.setattr(cv, "_wait", fake_wait)
    return SimpleNamespace(seen=seen, gate=gate)


async def logged(db):
    cur = await db.conn.execute("SELECT kind, actor_id, details FROM action_log ORDER BY id")
    return [dict(row) for row in await cur.fetchall()]


async def test_a_mode_that_is_off_at_startup_hides_its_commands_and_syncs_once(bot, waits):
    control = cv.install(bot)

    assert bot.tree.removed == ["request"]
    assert bot.tree.get_command("request", guild=DEV_GUILD) is None
    assert bot.tree.syncs == []

    waits.gate.set()
    await control.task

    assert bot.tree.syncs == [GUILD]
    assert waits.seen == [cv.DEBOUNCE_SECONDS]
    rows = await logged(bot.db)
    assert [row["kind"] for row in rows] == [cv.LOG_KIND]
    assert json.loads(rows[0]["details"]) == {
        "commands": 2,
        "hidden": ["request"],
        "shown": [],
        "via": "discord",
    }


async def test_a_mode_that_is_on_leaves_the_commands_alone_and_does_not_sync(bot, waits):
    await bot.store.set(GUILD, MODE_KEY, "on")

    control = cv.install(bot)

    assert bot.tree.removed == [] and bot.tree.added == []
    assert bot.tree.get_command("request", guild=DEV_GUILD) is not None
    assert control.task is None
    assert bot.tree.syncs == []
    assert await logged(bot.db) == []


async def test_flipping_the_setting_syncs_exactly_once_after_the_debounce(bot, waits):
    await bot.store.set(GUILD, MODE_KEY, "on")
    control = cv.install(bot)

    await bot.store.set(GUILD, MODE_KEY, "off", by=77)
    await bot.store.set(GUILD, MODE_KEY, "on", by=77)
    await bot.store.set(GUILD, MODE_KEY, "off", by=77)

    assert bot.tree.syncs == []
    waits.gate.set()
    await control.task

    assert bot.tree.syncs == [GUILD]
    assert waits.seen == [cv.DEBOUNCE_SECONDS]
    assert [row["actor_id"] for row in await logged(bot.db)] == [77]


async def test_turning_it_back_on_puts_the_same_command_object_back(bot, waits):
    original = bot.tree.guilds[GUILD]["request"]
    control = cv.install(bot)

    await bot.store.set(GUILD, MODE_KEY, "on")

    assert bot.tree.get_command("request", guild=DEV_GUILD) is original
    assert bot.tree.added == ["request"]
    waits.gate.set()
    await control.task
    assert bot.tree.syncs == [GUILD]


async def test_the_settings_group_is_never_hidden(bot, waits, monkeypatch):
    monkeypatch.setitem(cv.HIDDEN_WHEN_OFF, MODE_KEY, ("request", "settings"))

    cv.install(bot)

    assert bot.tree.removed == ["request"]
    assert bot.tree.get_command("settings", guild=DEV_GUILD) is not None
    assert "settings" not in cv.hidden_names(bot, GUILD)
    assert "request" in cv.hidden_names(bot, GUILD)


async def test_a_second_change_waits_out_the_rate_limit_window(bot, waits):
    await bot.store.set(GUILD, MODE_KEY, "on")
    control = cv.install(bot)
    control.last_sync = cv._now()

    await bot.store.set(GUILD, MODE_KEY, "off")
    waits.gate.set()
    await control.task

    assert waits.seen[0] == cv.DEBOUNCE_SECONDS
    assert 0 < waits.seen[1] <= cv.MIN_SYNC_SECONDS
    assert bot.tree.syncs == [GUILD]


async def test_a_change_in_another_guild_touches_nothing(bot, waits):
    cv.install(bot)
    bot.tree.removed.clear()

    await bot.store.set(GUILD + 1, MODE_KEY, "on")

    assert bot.tree.removed == [] and bot.tree.added == []


async def test_no_dev_guild_means_no_hiding_at_all(bot, waits, monkeypatch):
    monkeypatch.setattr(bot.settings, "dev_guild_id", None)

    control = cv.install(bot)

    assert bot.tree.removed == [] and control.task is None


def test_hidden_names_reads_the_store_and_needs_a_guild(bot):
    assert "request" in cv.hidden_names(bot, GUILD)
    assert cv.hidden_names(bot, None) == set()


async def test_every_key_in_the_table_is_a_registry_key_whose_choices_include_off():
    for key in cv.HIDDEN_WHEN_OFF:
        assert KEY_TYPES.get(key) == "enum", key
        assert cv.OFF in KEY_CHOICES[key], key


async def test_every_command_in_the_table_is_a_real_top_level_command(real_tree):
    named = {name for names in cv.HIDDEN_WHEN_OFF.values() for name in names}
    assert named <= real_tree
    assert cv.NEVER_HIDDEN[0] == "settings"
    assert set(cv.NEVER_HIDDEN) <= real_tree
    assert named.isdisjoint(cv.NEVER_HIDDEN)


async def test_the_fourteen_features_that_hide_each_map_to_one_command():
    assert cv.HIDDEN_WHEN_OFF == {
        "applications_mode": ("apply",),
        "automod_mode": ("automod",),
        "birthday_mode": ("birthday",),
        "chat_mode": ("chat",),
        "events_mode": ("event",),
        "golive_mode": ("golive",),
        "honeypot_mode": ("honeypot",),
        "pings_mode": ("pings",),
        "poll_mode": ("poll",),
        "raidtrain_mode": ("raidtrain",),
        "request_mode": ("request",),
        "rolemenu_mode": ("rolemenu",),
        "tempvoice_mode": ("voice",),
        "youtube_mode": ("youtube",),
    }
    assert "modmail_mode" not in cv.HIDDEN_WHEN_OFF


async def test_shadow_is_not_off_so_a_shadowed_feature_keeps_its_command(bot):
    """The owner shadows youtube today; only the literal word off takes a command away."""
    await bot.store.set(GUILD, "youtube_mode", "shadow", by=5)

    assert "youtube" not in cv.hidden_names(bot, GUILD)

    await bot.store.set(GUILD, "youtube_mode", "off", by=5)

    assert "youtube" in cv.hidden_names(bot, GUILD)


async def test_the_switch_turns_the_whole_thing_off_and_nothing_is_hidden(bot):
    assert bot.store.get(GUILD, cv.SWITCH_KEY) is True
    assert "request" in cv.hidden_names(bot, GUILD)

    await bot.store.set(GUILD, cv.SWITCH_KEY, False, by=5)

    assert cv.hidden_names(bot, GUILD) == set()


async def test_flipping_the_switch_puts_every_hidden_command_back_and_syncs(bot, waits):
    control = cv.install(bot)
    assert bot.tree.get_command("request", guild=DEV_GUILD) is None

    await bot.store.set(GUILD, cv.SWITCH_KEY, False, by=8)

    assert bot.tree.get_command("request", guild=DEV_GUILD) is not None
    waits.gate.set()
    await control.task

    assert bot.tree.syncs == [GUILD]
    rows = await logged(bot.db)
    assert json.loads(rows[-1]["details"])["shown"] == ["request"]


async def test_turning_the_switch_back_on_hides_the_off_features_again(bot, waits):
    await bot.store.set(GUILD, cv.SWITCH_KEY, False)
    control = cv.install(bot)
    assert bot.tree.get_command("request", guild=DEV_GUILD) is not None

    await bot.store.set(GUILD, cv.SWITCH_KEY, True, by=8)

    assert bot.tree.get_command("request", guild=DEV_GUILD) is None
    waits.gate.set()
    await control.task
    assert bot.tree.syncs == [GUILD]


async def test_the_request_group_is_shown_while_requests_are_on_and_hidden_when_they_are_off(bot):
    assert cv.HIDDEN_WHEN_OFF["request_mode"] == ("request",)
    assert "request" in cv.hidden_names(bot, GUILD)

    await bot.store.set(GUILD, "request_mode", "on", by=5)

    assert "request" not in cv.hidden_names(bot, GUILD)


async def test_every_hidden_feature_can_still_be_turned_back_on_from_discord():
    """`/settings` ▸ **Turn a feature back on…** is the door that survives the command going
    away, and every hidden feature's key is also reachable through **A setting group…**."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert "settings" in cv.NEVER_HIDDEN
    for key in cv.HIDDEN_WHEN_OFF:
        assert reachable_on_the_panel(key), key
        assert parse_value(key, "on") == "on", key
        assert "shadow" not in KEY_CHOICES[key] or parse_value(key, "shadow") == "shadow"


async def test_apply_and_rolemenu_hide_with_the_rest_but_memory_stays(bot):
    """Supersedes two earlier per-feature carve-outs — owner, 2026-09-03: `/apply` "Visible",
    and `/rolemenu` kept because hiding it hid the only way back; `/settings` ▸ **Turn a
    feature back on…** plus `hide_commands_when_off` are the ways back now. `/memory` KEEPS its
    carve-out (fork I-M1, "open it"): turning memory off deletes nothing, the site is
    staff-only, so the panel is a member's only door to notes held about them (KI-14)."""
    assert "chat_memory_mode" not in cv.HIDDEN_WHEN_OFF
    assert all("memory" not in names for names in cv.HIDDEN_WHEN_OFF.values())
    for key, name in (
        ("applications_mode", "apply"),
        ("rolemenu_mode", "rolemenu"),
    ):
        assert bot.store.get(GUILD, key) == "off"
        assert name in cv.hidden_names(bot, GUILD)
        await bot.store.set(GUILD, key, "on", by=5)
        assert name not in cv.hidden_names(bot, GUILD)


async def test_the_real_command_tree_hides_and_gives_back_the_group(tmp_path, monkeypatch, waits):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(
        _env_file=None,
        dev_guild_id=GUILD,
        test_mode=True,
        test_channel_id=TEST_CHANNEL,
        database_path=tmp_path / "real.sqlite3",
    )
    black_bloc = BlackBlocBot(settings)
    await black_bloc.db.connect()
    await black_bloc.store.load()
    await black_bloc.store.set(GUILD, MODE_KEY, "off")
    for name in ("black_bloc.cogs.core", "black_bloc.cogs.community.requests"):
        assert name in COGS
        await black_bloc.load_extension(name)
    black_bloc.tree.copy_global_to(guild=DEV_GUILD)
    group = black_bloc.tree.get_command("request", guild=DEV_GUILD)
    synced = []

    async def fake_sync(*, guild=None):
        synced.append(guild.id)
        return black_bloc.tree.get_commands(guild=guild)

    black_bloc.tree.sync = fake_sync
    control = cv.install(black_bloc)

    in_guild = {command.name for command in black_bloc.tree.get_commands(guild=DEV_GUILD)}
    assert "request" not in in_guild and "settings" in in_guild

    await black_bloc.store.set(GUILD, MODE_KEY, "on", by=5)

    assert black_bloc.tree.get_command("request", guild=DEV_GUILD) is group
    waits.gate.set()
    await control.task
    await black_bloc.close()

    assert synced == [GUILD]


async def test_the_staff_lock_survives_a_copy_to_the_guild_and_a_hide_and_show(
    tmp_path, monkeypatch, waits
):
    """The lock lives on the command object, so removing and re-adding it cannot lose it."""
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(
        _env_file=None,
        dev_guild_id=GUILD,
        test_mode=True,
        test_channel_id=TEST_CHANNEL,
        database_path=tmp_path / "lock.sqlite3",
    )
    black_bloc = BlackBlocBot(settings)
    await black_bloc.db.connect()
    await black_bloc.store.load()
    await black_bloc.load_extension("black_bloc.cogs.community.role_menus")
    black_bloc.tree.copy_global_to(guild=DEV_GUILD)

    control = cv.VisibilitySync(black_bloc)
    assert control._hide(DEV_GUILD, "rolemenu") is True
    assert control._show(DEV_GUILD, "rolemenu") is True

    found = black_bloc.tree.get_command("rolemenu", guild=DEV_GUILD)
    assert found.default_permissions == cv.STAFF_ONLY
    await black_bloc.close()


async def test_a_registered_job_runs_once_with_the_actor_before_the_sync(bot, waits):
    control = cv.install(bot)
    order = []
    control.also(lambda actor: _record(order, actor))
    bot.tree.sync = _syncing(order, bot.tree.sync)

    await bot.store.set(GUILD, MODE_KEY, "on", by=9)
    await bot.store.set(GUILD, MODE_KEY, "off", by=9)

    waits.gate.set()
    await control.task

    assert order == [("job", 9), ("sync", None)]


async def test_a_job_that_raises_does_not_take_the_sync_down_with_it(bot, waits):
    control = cv.install(bot)

    async def broken(actor):
        raise RuntimeError("no")

    control.also(broken)

    waits.gate.set()
    await control.task

    assert bot.tree.syncs == [GUILD]


async def _record(order, actor):
    order.append(("job", actor))


def _syncing(order, original):
    async def sync(*, guild=None):
        order.append(("sync", None))
        return await original(guild=guild)

    return sync


async def test_a_sync_discord_refuses_is_logged_and_leaves_the_window_open(bot, waits):
    async def refuse(*, guild=None):
        raise discord.HTTPException(SimpleNamespace(status=429, reason="rate limited"), "slow down")

    control = cv.install(bot)
    bot.tree.sync = refuse

    waits.gate.set()
    await control.task

    assert control.last_sync is None
    assert await logged(bot.db) == []
