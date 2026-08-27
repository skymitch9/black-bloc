import pytest

from black_bloc.config import load_settings
from black_bloc.settings_store import (
    GOLIVE_CHANNEL_ID,
    GOLIVE_TEMPLATE,
    KEY_TYPES,
    MEMBER_ROLE_ID,
    TEMPVOICE_NAME_TEMPLATE,
    SettingError,
    SettingsStore,
    coerce_value,
    display_value,
    member_is_staff,
    parse_value,
    staff_role_ids_from_overwrites,
)
from black_bloc.storage.db import Database

TEST_CH = 111
STAFF_ROLE = 555


@pytest.fixture
async def store(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=TEST_CH)
    db = Database(tmp_path / "s.sqlite3")
    await db.connect()
    s = SettingsStore(db, settings)
    await s.load()
    try:
        yield s
    finally:
        await db.close()


class _Role:
    def __init__(self, id, default=False):
        self.id = id
        self._default = default

    def is_default(self):
        return self._default


class _Perms:
    def __init__(self, view_channel=None, manage_guild=False):
        self.view_channel = view_channel
        self.manage_guild = manage_guild


class _Member:
    def __init__(self, roles=(), manage_guild=False):
        self.roles = roles
        self.guild_permissions = _Perms(manage_guild=manage_guild)


async def test_defaults_follow_test_mode(store):
    assert store.get(1, "staff_channel_id") == TEST_CH
    assert store.get(1, "log_channel_id") == TEST_CH
    assert store.get(1, "role_menu_channel_id") is None


async def test_set_get_round_trip_survives_reload(store):
    await store.set(1, "log_channel_id", 999, by=42)
    assert store.get(1, "log_channel_id") == 999
    assert store.get(2, "log_channel_id") == TEST_CH
    await store.load()
    assert store.get(1, "log_channel_id") == 999


async def test_all_lists_every_known_key(store):
    await store.set(1, "role_menu_channel_id", 777)
    values = store.all(1)
    assert set(values) == set(KEY_TYPES)
    assert values["log_channel_id"] == TEST_CH
    assert values["staff_channel_id"] == TEST_CH
    assert values["role_menu_channel_id"] == 777


async def test_unknown_key_is_refused(store):
    with pytest.raises(SettingError, match="not a Black Bloc setting"):
        await store.set(1, "nope", 1)
    with pytest.raises(SettingError):
        store.get(1, "nope")


def test_channel_values_are_type_checked():
    assert coerce_value("log_channel_id", 5) == 5
    assert coerce_value("log_channel_id", _Role(6)) == 6
    with pytest.raises(SettingError, match="takes a channel"):
        coerce_value("log_channel_id", "general")
    with pytest.raises(SettingError, match="takes a channel"):
        coerce_value("log_channel_id", True)


def test_staff_roles_come_from_view_overwrites():
    overwrites = {
        _Role(STAFF_ROLE): _Perms(view_channel=True),
        _Role(1, default=True): _Perms(view_channel=True),
        _Role(2): _Perms(view_channel=False),
        _Role(3): _Perms(view_channel=None),
    }
    assert staff_role_ids_from_overwrites(overwrites) == {STAFF_ROLE}


def test_member_is_staff_by_role_or_manage_guild():
    assert member_is_staff(_Member(roles=[_Role(STAFF_ROLE)]), {STAFF_ROLE})
    assert member_is_staff(_Member(manage_guild=True), set())
    assert not member_is_staff(_Member(roles=[_Role(9)]), {STAFF_ROLE})


async def test_golive_defaults(store):
    assert store.get(1, "golive_mode") == "shadow"
    assert store.get(1, "golive_channel_id") == TEST_CH
    assert store.get(1, "golive_template") == GOLIVE_TEMPLATE
    assert store.get(1, "golive_cooldown_minutes") == 60
    assert store.get(1, "golive_live_role_id") is None
    assert store.get(1, "golive_ping_role_id") is None


async def test_golive_channel_defaults_to_live_now_once_test_mode_is_off(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=False, test_channel_id=None)
    db = Database(tmp_path / "g.sqlite3")
    await db.connect()
    try:
        s = SettingsStore(db, settings)
        await s.load()
        assert s.get(1, "golive_channel_id") == GOLIVE_CHANNEL_ID
    finally:
        await db.close()


async def test_golive_settings_round_trip(store):
    assert await store.set(1, "golive_mode", "on") == "on"
    assert await store.set(1, "golive_cooldown_minutes", 15) == 15
    assert await store.set(1, "golive_template", "{name} live: {url}") == "{name} live: {url}"
    assert await store.set(1, "golive_live_role_id", 42) == 42
    await store.load()
    assert store.get(1, "golive_mode") == "on"
    assert store.get(1, "golive_cooldown_minutes") == 15
    assert store.get(1, "golive_live_role_id") == 42


def test_the_new_value_types_are_checked():
    assert coerce_value("golive_mode", "shadow") == "shadow"
    with pytest.raises(SettingError, match="off, shadow, on"):
        coerce_value("golive_mode", "maybe")
    assert coerce_value("golive_live_role_id", _Role(6)) == 6
    with pytest.raises(SettingError, match="takes a role"):
        coerce_value("golive_live_role_id", "mods")
    assert coerce_value("golive_cooldown_minutes", 5) == 5
    with pytest.raises(SettingError, match="whole number"):
        coerce_value("golive_cooldown_minutes", "5")
    with pytest.raises(SettingError, match="cannot be negative"):
        coerce_value("golive_cooldown_minutes", -1)
    assert coerce_value("golive_template", "hi") == "hi"
    with pytest.raises(SettingError, match="takes some text"):
        coerce_value("golive_template", "   ")


def test_typed_in_values_are_parsed_by_type():
    assert parse_value("golive_cooldown_minutes", " 30 ") == 30
    assert parse_value("golive_live_role_id", "<@&123>") == 123
    assert parse_value("log_channel_id", "<#456>") == 456
    assert parse_value("golive_mode", "on") == "on"
    assert parse_value("golive_template", " {name} ") == "{name}"
    with pytest.raises(SettingError, match="whole number"):
        parse_value("golive_cooldown_minutes", "soon")


def test_display_value_renders_by_type():
    assert display_value("log_channel_id", 5) == "<#5>"
    assert display_value("golive_live_role_id", 5) == "<@&5>"
    assert display_value("golive_cooldown_minutes", 60) == "60"
    assert display_value("golive_live_role_id", None) == "not set"


async def test_tempvoice_defaults(store):
    assert store.get(1, "tempvoice_mode") == "on"
    assert store.get(1, "tempvoice_name_template") == TEMPVOICE_NAME_TEMPLATE
    assert store.get(1, "tempvoice_allowed_role_id") == MEMBER_ROLE_ID
    assert store.get(1, "tempvoice_creator_ids") == []


async def test_honeypot_defaults(store):
    assert store.get(1, "honeypot_mode") == "shadow"
    assert store.get(1, "honeypot_purge_days") == 1
    assert store.get(1, "honeypot_channel_ids") == []
    assert store.get(1, "honeypot_exempt_role_ids") == []


def test_role_list_settings_render_as_roles():
    assert coerce_value("honeypot_exempt_role_ids", [_Role(5), 6]) == [5, 6]
    with pytest.raises(SettingError, match="list of roles"):
        coerce_value("honeypot_exempt_role_ids", "mods")
    assert display_value("honeypot_exempt_role_ids", [5]) == "<@&5>"


async def test_a_list_setting_round_trips_and_is_not_shared(store):
    assert await store.set(1, "tempvoice_creator_ids", [5, 6, 5]) == [5, 6]
    await store.load()
    assert store.get(1, "tempvoice_creator_ids") == [5, 6]
    fresh = store.get(2, "tempvoice_creator_ids")
    fresh.append(99)
    assert store.get(2, "tempvoice_creator_ids") == []


def test_list_settings_are_type_checked():
    assert coerce_value("tempvoice_creator_ids", [_Role(5)]) == [5]
    with pytest.raises(SettingError, match="list of channels"):
        coerce_value("tempvoice_creator_ids", 5)
    with pytest.raises(SettingError, match="list of channels"):
        coerce_value("tempvoice_creator_ids", "5,6")
    with pytest.raises(SettingError, match="list of channels"):
        coerce_value("tempvoice_creator_ids", [True])


def test_list_settings_parse_and_display():
    assert parse_value("tempvoice_creator_ids", "<#5>, 6") == [5, 6]
    assert parse_value("tempvoice_creator_ids", "") == []
    with pytest.raises(SettingError, match="ids separated by commas"):
        parse_value("tempvoice_creator_ids", "general")
    assert display_value("tempvoice_creator_ids", [5, 6]) == "<#5>, <#6>"
    assert display_value("tempvoice_creator_ids", []) == "not set"


def test_staff_refusal_names_the_channel(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=TEST_CH)
    s = SettingsStore(Database(tmp_path / "s.sqlite3"), settings)
    message = s.staff_refusal(1)
    assert f"<#{TEST_CH}>" in message and "Manage Server" in message
