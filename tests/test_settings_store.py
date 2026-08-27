import pytest

from black_bloc.automod import validate_rules
from black_bloc.config import load_settings
from black_bloc.settings_store import (
    CARL_MODLOG_CHANNEL_ID,
    EVENTS_RETENTION_DAYS,
    EVENTS_RETENTION_MAX_DAYS,
    GOLIVE_TEMPLATE,
    HONEYPOT_PURGE_MAX_DAYS,
    KEY_TYPES,
    LIVE_NOW_CHANNEL_ID,
    MEMBER_ROLE_ID,
    TEMPVOICE_NAME_TEMPLATE,
    SettingError,
    SettingsStore,
    coerce_value,
    display_value,
    member_is_staff,
    parse_value,
    resolved_staff_roles,
    staff_roles_sentence,
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
    def __init__(self, id, default=False, bot_managed=False):
        self.id = id
        self.name = f"role-{id}"
        self._default = default
        self._bot_managed = bot_managed

    def is_default(self):
        return self._default

    def is_bot_managed(self):
        return self._bot_managed


class _Channel:
    """A staff channel that answers `permissions_for`, overwrites or not."""

    def __init__(self, channel_id, visible_to):
        self.id = channel_id
        self.overwrites = {}
        self._visible = set(visible_to)

    def permissions_for(self, role):
        return _Perms(view_channel=role.id in self._visible)


class _Guild:
    def __init__(self, roles, channels=()):
        self.id = 1
        self.roles = list(roles)
        self.channels = {c.id: c for c in channels}

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)


class _Perms:
    def __init__(self, view_channel=None, manage_guild=False):
        self.view_channel = view_channel
        self.manage_guild = manage_guild


class _Member:
    def __init__(self, roles=(), manage_guild=False, guild=None):
        self.roles = roles
        self.guild = guild
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


def test_staff_roles_are_computed_not_read_off_the_overwrites():
    everyone = _Role(1, default=True)
    mods = _Role(STAFF_ROLE)
    members = _Role(2)
    a_bot = _Role(3, bot_managed=True)
    channel = _Channel(9, visible_to={everyone.id, STAFF_ROLE, a_bot.id})
    guild = _Guild([everyone, mods, members, a_bot], [channel])

    assert channel.overwrites == {}
    assert [role.id for role in resolved_staff_roles(guild, channel)] == [STAFF_ROLE]
    assert resolved_staff_roles(guild, None) == []


def test_a_role_that_can_only_see_the_channel_by_inheritance_still_counts():
    mods = _Role(STAFF_ROLE)
    guild = _Guild([mods])
    inherited = {STAFF_ROLE}

    resolved = resolved_staff_roles(
        guild,
        _Channel(9, visible_to=set()),
        perms_for=lambda role: _Perms(view_channel=role.id in inherited),
    )

    assert [role.id for role in resolved] == [STAFF_ROLE]


def test_a_role_whose_permissions_cannot_be_worked_out_is_skipped():
    def boom(role):
        raise RuntimeError("no idea")

    guild = _Guild([_Role(STAFF_ROLE)])
    assert resolved_staff_roles(guild, _Channel(9, visible_to=set()), perms_for=boom) == []


def test_the_staff_sentence_names_the_roles_or_says_there_are_none():
    assert staff_roles_sentence([]) == "no roles at all"
    assert "1 role(s)" in staff_roles_sentence([_Role(STAFF_ROLE)])
    assert f"role-{STAFF_ROLE}" in staff_roles_sentence([_Role(STAFF_ROLE)])


async def test_the_store_resolves_staff_from_the_staff_channel(store):
    mods = _Role(STAFF_ROLE)
    guild = _Guild([mods], [_Channel(TEST_CH, visible_to={STAFF_ROLE})])

    assert store.staff_role_ids(guild) == {STAFF_ROLE}
    assert store.is_staff(_Member(roles=[mods], guild=guild))


async def test_a_staff_channel_black_bloc_cannot_see_resolves_to_nobody(store):
    guild = _Guild([_Role(STAFF_ROLE)])

    assert store.staff_role_ids(guild) == set()
    assert store.staff_roles(guild) == []


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
        assert s.get(1, "golive_channel_id") == LIVE_NOW_CHANNEL_ID
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


def test_the_purge_window_is_clamped_to_discord_s_maximum():
    assert coerce_value("honeypot_purge_days", HONEYPOT_PURGE_MAX_DAYS) == HONEYPOT_PURGE_MAX_DAYS
    assert coerce_value("honeypot_purge_days", 0) == 0
    with pytest.raises(SettingError, match=f"cannot be more than {HONEYPOT_PURGE_MAX_DAYS}"):
        coerce_value("honeypot_purge_days", HONEYPOT_PURGE_MAX_DAYS + 1)
    with pytest.raises(SettingError, match="cannot be negative"):
        coerce_value("honeypot_purge_days", -1)
    assert coerce_value("golive_cooldown_minutes", 9999) == 9999


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


async def test_clearing_a_scalar_setting_puts_the_default_back(store):
    await store.set(1, "events_ping_role_id", 42)
    assert store.get(1, "events_ping_role_id") == 42

    await store.clear(1, "events_ping_role_id")
    assert store.get(1, "events_ping_role_id") is None

    await store.load()
    assert store.get(1, "events_ping_role_id") is None
    await store.clear(1, "events_ping_role_id")
    with pytest.raises(SettingError, match="not a Black Bloc setting"):
        await store.clear(1, "events_ping_role")


async def test_events_defaults(store):
    assert store.get(1, "events_mode") == "on"
    assert store.get(1, "events_announce_channel_id") == TEST_CH
    assert store.get(1, "events_create_scheduled") is True
    assert store.get(1, "events_channel_retention_days") == EVENTS_RETENTION_DAYS
    assert store.get(1, "events_category_id") is None
    assert store.get(1, "events_ping_role_id") is None


async def test_the_announce_channel_becomes_live_now_once_test_mode_is_off(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=False, test_channel_id=None)
    db = Database(tmp_path / "e.sqlite3")
    await db.connect()
    try:
        s = SettingsStore(db, settings)
        await s.load()
        assert s.get(1, "events_announce_channel_id") == LIVE_NOW_CHANNEL_ID
    finally:
        await db.close()


def test_the_create_scheduled_toggle_is_a_real_boolean():
    assert coerce_value("events_create_scheduled", False) is False
    assert parse_value("events_create_scheduled", "off") is False
    assert parse_value("events_create_scheduled", "yes") is True
    with pytest.raises(SettingError, match="true or false"):
        coerce_value("events_create_scheduled", 1)
    with pytest.raises(SettingError, match="true or false"):
        parse_value("events_create_scheduled", "sometimes")


def test_retention_is_capped_with_its_own_sentence_not_the_ban_one():
    assert coerce_value("events_channel_retention_days", 0) == 0
    with pytest.raises(SettingError, match="tidy up") as caught:
        coerce_value("events_channel_retention_days", EVENTS_RETENTION_MAX_DAYS + 1)
    assert "banned account" not in str(caught.value)


def test_staff_refusal_names_the_channel(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=TEST_CH)
    s = SettingsStore(Database(tmp_path / "s.sqlite3"), settings)
    message = s.staff_refusal(1)
    assert f"<#{TEST_CH}>" in message and "Manage Server" in message


async def test_the_automod_keys_default_to_carls_config_in_shadow(store):
    assert store.get(1, "automod_mode") == "shadow"
    assert store.get(1, "mod_dm_on_action") == "server_action_reason"
    assert store.get(1, "automod_warn_threshold") == 8
    assert store.get(1, "modlog_channel_id") == TEST_CH
    assert store.get(1, "carl_modlog_channel_id") == CARL_MODLOG_CHANNEL_ID
    assert store.get(1, "automod_exempt_role_ids") == []
    book = store.get(1, "automod_rules")
    assert book["mention_spam"]["threshold"] == 5
    book["mention_spam"]["threshold"] = 99
    assert store.get(1, "automod_rules")["mention_spam"]["threshold"] == 5


async def test_the_rule_book_is_validated_on_the_way_in(store):
    await store.set(1, "automod_rules", {"mention_spam": {"threshold": 3}})
    assert store.get(1, "automod_rules")["mention_spam"]["threshold"] == 3
    assert store.get(1, "automod_rules")["slowmode"]["window_s"] == 4
    with pytest.raises(SettingError, match="automod rules"):
        await store.set(1, "automod_rules", {"nonsense": {}})
    with pytest.raises(SettingError, match="28 days|between"):
        await store.set(1, "automod_rules", {"mention_spam": {"timeout_s": 99999999}})


def test_a_rule_book_reads_back_as_a_summary_not_as_json():
    shown = display_value("automod_rules", validate_rules({}))
    assert "mention_spam 5/30s delete+warn+timeout" in shown
    assert "{" not in shown
