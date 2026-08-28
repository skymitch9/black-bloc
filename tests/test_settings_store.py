import pytest

from black_bloc.automod import validate_rules
from black_bloc.config import load_settings
from black_bloc.emoji import SKIN_TONE_DEFAULT, SKIN_TONE_NAMES
from black_bloc.settings_store import (
    BIRTHDAY_CHANNEL_ID,
    BIRTHDAY_COLOR,
    BIRTHDAY_TEMPLATE,
    CHANNEL_MODE,
    EVENTS_LATE_CEILING_MINUTES,
    EVENTS_MAX_LATE_MINUTES,
    EVENTS_RETENTION_DAYS,
    EVENTS_RETENTION_MAX_DAYS,
    EVENTS_RETENTION_MIN_DAYS,
    GOLIVE_END_EDIT,
    GOLIVE_END_MODES,
    GOLIVE_END_OFF,
    GOLIVE_END_SUFFIX,
    GOLIVE_TEMPLATE,
    HONEYPOT_PURGE_MAX_DAYS,
    KEY_HELP,
    KEY_TYPES,
    LIVE_NOW_CHANNEL_ID,
    MEMBER_ROLE_ID,
    MODMAIL_CATEGORY_ID,
    MODMAIL_LOG_CHANNEL_ID,
    POLL_ARCHIVE_DAYS,
    POLL_ARCHIVE_MAX_DAYS,
    POLL_DEFAULT_HOURS,
    POLL_MAX_HOURS,
    POLL_MIN_HOURS,
    POLL_REMINDER_MAX_MINUTES,
    POLL_REMINDER_MINUTES,
    TEMPVOICE_NAME_TEMPLATE,
    THREAD_MODE,
    SettingError,
    SettingsStore,
    coerce_value,
    display_value,
    is_staff_command,
    member_is_staff,
    parse_value,
    require_staff,
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


async def test_a_row_for_a_retired_key_is_ignored_rather_than_fatal(store, caplog):
    await store.db.conn.execute(
        "INSERT OR REPLACE INTO settings(guild_id, key, value, updated_at) VALUES (?, ?, ?, '')",
        (1, "carl_modlog_channel_id", "12345"),
    )
    await store.db.conn.execute(
        "INSERT OR REPLACE INTO settings(guild_id, key, value, updated_at) VALUES (?, ?, ?, '')",
        (1, "log_channel_id", "999"),
    )
    await store.db.conn.commit()

    with caplog.at_level("WARNING"):
        await store.load()

    assert store.get(1, "log_channel_id") == 999
    assert "carl_modlog_channel_id" in caplog.text
    assert "carl_modlog_channel_id" not in store.all(1)
    with pytest.raises(SettingError):
        store.get(1, "carl_modlog_channel_id")


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


async def test_the_stream_end_edit_is_off_until_a_guild_asks_for_it(store):
    assert store.get(1, "golive_end_mode") == GOLIVE_END_OFF == "off"
    assert KEY_TYPES["golive_end_mode"] == "enum"
    assert coerce_value("golive_end_mode", "edit") == GOLIVE_END_EDIT
    for name in GOLIVE_END_MODES:
        assert await store.set(1, "golive_end_mode", name) == name
        assert store.get(1, "golive_end_mode") == name
    with pytest.raises(SettingError):
        coerce_value("golive_end_mode", "delete")


async def test_the_stream_ended_wording_is_a_setting_with_the_hardcoded_text_as_its_default(store):
    assert store.get(1, "golive_end_suffix") == GOLIVE_END_SUFFIX
    assert KEY_TYPES["golive_end_suffix"] == "text"
    assert await store.set(1, "golive_end_suffix", " (over)") == " (over)"
    with pytest.raises(SettingError):
        await store.set(1, "golive_end_suffix", "   ")


async def test_the_emoji_skin_tone_defaults_to_dark_and_takes_only_the_six_tones(store):
    assert store.get(1, "emoji_skin_tone") == SKIN_TONE_DEFAULT == "dark"
    assert KEY_TYPES["emoji_skin_tone"] == "enum"
    assert coerce_value("emoji_skin_tone", "medium-dark") == "medium-dark"
    for name in SKIN_TONE_NAMES:
        assert await store.set(1, "emoji_skin_tone", name) == name
        assert store.get(1, "emoji_skin_tone") == name
    with pytest.raises(SettingError):
        coerce_value("emoji_skin_tone", "teal")


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


async def test_role_menus_ship_turned_off(store):
    """Owner ask, 2026-08-27: role selection is off until somebody turns it on."""
    assert store.get(1, "rolemenu_mode") == "off"
    assert await store.set(1, "rolemenu_mode", "on") == "on"
    assert store.get(1, "rolemenu_mode") == "on"
    with pytest.raises(SettingError, match="off, on"):
        coerce_value("rolemenu_mode", "shadow")


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
    assert store.get(1, "events_max_late_minutes") == EVENTS_MAX_LATE_MINUTES
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


async def test_birthday_defaults(store):
    assert store.get(1, "birthday_mode") == "shadow"
    assert store.get(1, "birthday_channel_id") == TEST_CH
    assert store.get(1, "birthday_template") == BIRTHDAY_TEMPLATE
    assert store.get(1, "birthday_color") == BIRTHDAY_COLOR
    assert store.get(1, "birthday_role_id") is None
    assert store.get(1, "birthday_show_age") is False


async def test_the_birthday_channel_defaults_to_the_incumbent_s_once_test_mode_is_off(
    tmp_path, monkeypatch
):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=False, test_channel_id=None)
    db = Database(tmp_path / "b.sqlite3")
    await db.connect()
    try:
        s = SettingsStore(db, settings)
        await s.load()
        assert s.get(1, "birthday_channel_id") == BIRTHDAY_CHANNEL_ID
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
    assert coerce_value("events_channel_retention_days", EVENTS_RETENTION_MIN_DAYS) == 1
    with pytest.raises(SettingError, match="tidy up") as caught:
        coerce_value("events_channel_retention_days", EVENTS_RETENTION_MAX_DAYS + 1)
    assert "banned account" not in str(caught.value)


def test_a_retention_of_zero_days_is_refused_because_it_deletes_an_unread_record():
    with pytest.raises(SettingError, match="cannot be less than 1") as caught:
        coerce_value("events_channel_retention_days", 0)
    assert "before anybody has read it" in str(caught.value)


def test_how_late_an_announcement_may_be_is_a_capped_whole_number():
    assert coerce_value("events_max_late_minutes", 0) == 0
    assert coerce_value("events_max_late_minutes", EVENTS_LATE_CEILING_MINUTES) == 24 * 60
    with pytest.raises(SettingError, match="already half over"):
        coerce_value("events_max_late_minutes", EVENTS_LATE_CEILING_MINUTES + 1)


def test_the_birthday_values_are_checked_and_parsed():
    assert coerce_value("birthday_mode", "on") == "on"
    with pytest.raises(SettingError, match="off, shadow, on"):
        coerce_value("birthday_mode", "someday")
    assert coerce_value("birthday_show_age", True) is True
    with pytest.raises(SettingError, match="true or false"):
        coerce_value("birthday_show_age", "yes")
    assert parse_value("birthday_show_age", "yes") is True
    assert parse_value("birthday_color", " #4eefff ") == "#4eefff"
    assert coerce_value("birthday_role_id", _Role(6)) == 6


def test_a_colour_that_is_not_a_hex_code_is_refused_with_a_sentence():
    assert coerce_value("birthday_color", "#4EEFFF") == "#4eefff"
    assert coerce_value("birthday_color", " 4eefff ") == "#4eefff"
    for bad in ("blue", "#4eeff", "#4eefffff", "", "#nothex", 4):
        with pytest.raises(SettingError, match="hex colour"):
            coerce_value("birthday_color", bad)


async def test_a_setting_can_be_unset_again(store):
    await store.set(1, "birthday_role_id", 42)
    assert store.get(1, "birthday_role_id") == 42

    assert await store.clear(1, "birthday_role_id", by=9) is True
    assert store.get(1, "birthday_role_id") is None
    assert await store.clear(1, "birthday_role_id") is False

    await store.load()
    assert store.get(1, "birthday_role_id") is None
    with pytest.raises(SettingError, match="not a Black Bloc setting"):
        await store.clear(1, "nonsense_id")


async def test_a_change_hook_hears_every_set_and_clear_of_its_own_key(store):
    heard = []
    store.on_change("rolemenu_mode", lambda *seen: heard.append(seen))

    await store.set(1, "rolemenu_mode", "on", by=9)
    await store.set(1, "birthday_role_id", 42)
    await store.clear(1, "rolemenu_mode", by=9)
    await store.clear(1, "rolemenu_mode")

    assert heard == [(1, "rolemenu_mode", "on", 9), (1, "rolemenu_mode", "off", 9)]


async def test_a_change_hook_may_be_async_and_a_broken_one_does_not_stop_the_write(store):
    heard = []

    async def slow(guild_id, key, value, by):
        heard.append(value)

    def broken(guild_id, key, value, by):
        raise RuntimeError("no")

    store.on_change("rolemenu_mode", broken)
    store.on_change("rolemenu_mode", slow)

    await store.set(1, "rolemenu_mode", "on")

    assert heard == ["on"]
    assert store.get(1, "rolemenu_mode") == "on"
    with pytest.raises(SettingError, match="not a Black Bloc setting"):
        store.on_change("nonsense_mode", broken)


async def test_modmail_defaults_point_nowhere_real_while_test_mode_is_on(store):
    assert store.get(1, "modmail_enabled") is False
    assert store.get(1, "modmail_mode") == CHANNEL_MODE
    assert store.get(1, "modmail_category_id") is None
    assert store.get(1, "modmail_staff_channel_id") is None
    assert store.get(1, "modmail_log_channel_id") == TEST_CH


async def test_the_modmail_places_become_the_real_ones_once_test_mode_is_off(
    tmp_path, monkeypatch
):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=False, test_channel_id=None)
    db = Database(tmp_path / "m.sqlite3")
    await db.connect()
    try:
        s = SettingsStore(db, settings)
        await s.load()
        assert s.get(1, "modmail_category_id") == MODMAIL_CATEGORY_ID
        assert s.get(1, "modmail_log_channel_id") == MODMAIL_LOG_CHANNEL_ID
    finally:
        await db.close()


def test_the_modmail_keys_are_typed_and_the_mode_is_an_enum():
    assert coerce_value("modmail_enabled", True) is True
    assert coerce_value("modmail_mode", THREAD_MODE) == THREAD_MODE
    assert coerce_value("modmail_category_id", _Role(5)) == 5
    with pytest.raises(SettingError, match="channel"):
        coerce_value("modmail_log_channel_id", "the log")
    with pytest.raises(SettingError, match="channel, thread"):
        coerce_value("modmail_mode", "email")
    with pytest.raises(SettingError, match="true or false"):
        coerce_value("modmail_enabled", "yes")
    assert display_value("modmail_staff_channel_id", 7) == "<#7>"
    assert {
        "modmail_enabled",
        "modmail_mode",
        "modmail_category_id",
        "modmail_staff_channel_id",
        "modmail_log_channel_id",
    } <= set(KEY_TYPES)


def test_staff_refusal_names_the_channel(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=TEST_CH)
    s = SettingsStore(Database(tmp_path / "s.sqlite3"), settings)
    message = s.staff_refusal(1)
    assert f"<#{TEST_CH}>" in message and "Manage Server" in message


async def test_the_automod_keys_default_to_the_incumbents_config_in_shadow(store):
    assert store.get(1, "automod_mode") == "shadow"
    assert store.get(1, "mod_dm_on_action") == "server_action_reason"
    assert store.get(1, "automod_warn_threshold") == 8
    assert store.get(1, "modlog_channel_id") == TEST_CH
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


async def gate_in_the_body(interaction):
    if not await require_staff(interaction):
        return


async def no_gate_at_all(interaction):
    await interaction.response.send_message("hello")


class Cog:
    async def _ready(self, interaction):
        return await require_staff(interaction)

    async def _two_hops(self, interaction):
        return await self._ready(interaction)


async def gate_one_call_away(self, interaction):
    if not await self._ready(interaction):
        return


async def gate_two_calls_away(self, interaction):
    if not await self._two_hops(interaction):
        return


class FakeCommand:
    def __init__(self, callback, binding=None, extras=None):
        self.callback = callback
        self.binding = binding
        self.extras = extras or {}


def test_a_command_is_staff_when_its_body_or_the_helper_it_calls_asks_require_staff():
    assert is_staff_command(FakeCommand(gate_in_the_body)) is True
    assert is_staff_command(FakeCommand(gate_one_call_away, binding=Cog())) is True
    assert is_staff_command(FakeCommand(no_gate_at_all)) is False


def test_a_gate_further_away_is_left_unmarked_rather_than_guessed_at():
    assert is_staff_command(FakeCommand(gate_two_calls_away, binding=Cog())) is False


def test_an_explicit_staff_only_extra_beats_reading_the_body():
    assert is_staff_command(FakeCommand(no_gate_at_all, extras={"staff_only": True})) is True
    assert is_staff_command(FakeCommand(gate_in_the_body, extras={"staff_only": False})) is False


async def test_polls_ship_on_with_staff_creating_them_and_no_review(store):
    assert store.get(1, "poll_mode") == "on"
    assert store.get(1, "poll_who_can_create") == "staff"
    assert store.get(1, "poll_review_mode") == "off"
    assert store.get(1, "poll_default_hours") == POLL_DEFAULT_HOURS
    assert store.get(1, "poll_reminder_minutes") == POLL_REMINDER_MINUTES
    assert store.get(1, "poll_auto_thread") is False
    assert store.get(1, "poll_archive_days") == POLL_ARCHIVE_DAYS
    assert store.get(1, "poll_archive_drop_votes") is True
    assert store.get(1, "poll_ping_role_id") is None


async def test_a_dashboard_poll_lands_in_the_test_channel_while_test_mode_is_on(store):
    assert store.get(1, "poll_channel_id") == TEST_CH


def test_a_poll_length_discord_cannot_express_is_refused_at_the_validator():
    assert coerce_value("poll_default_hours", POLL_MIN_HOURS) == POLL_MIN_HOURS
    assert coerce_value("poll_default_hours", POLL_MAX_HOURS) == POLL_MAX_HOURS
    with pytest.raises(SettingError) as caught:
        coerce_value("poll_default_hours", POLL_MAX_HOURS + 1)
    assert "32 days" in str(caught.value)
    with pytest.raises(SettingError):
        coerce_value("poll_default_hours", 0)


def test_a_poll_reminder_may_be_off_but_not_a_fortnight_out():
    assert coerce_value("poll_reminder_minutes", 0) == 0
    with pytest.raises(SettingError):
        coerce_value("poll_reminder_minutes", POLL_REMINDER_MAX_MINUTES + 1)


def test_an_archive_that_fires_the_same_day_is_refused_with_the_reason():
    with pytest.raises(SettingError) as caught:
        coerce_value("poll_archive_days", 0)
    assert "before anybody has read it" in str(caught.value)
    with pytest.raises(SettingError):
        coerce_value("poll_archive_days", POLL_ARCHIVE_MAX_DAYS + 1)


def test_the_poll_switches_only_take_the_words_they_document():
    assert coerce_value("poll_mode", "on") == "on"
    assert coerce_value("poll_review_mode", "on") == "on"
    assert coerce_value("poll_who_can_create", "everyone") == "everyone"
    for key, bad in (
        ("poll_mode", "shadow"),
        ("poll_review_mode", "maybe"),
        ("poll_who_can_create", "role"),
    ):
        with pytest.raises(SettingError):
            coerce_value(key, bad)


def test_every_poll_key_is_typed_so_the_dashboard_can_render_it():
    for key in (
        "poll_mode",
        "poll_who_can_create",
        "poll_review_mode",
        "poll_default_hours",
        "poll_channel_id",
        "poll_ping_role_id",
        "poll_reminder_minutes",
        "poll_auto_thread",
        "poll_archive_days",
        "poll_archive_drop_votes",
    ):
        assert key in KEY_TYPES


async def test_the_chat_manners_keys_are_typed_explained_and_defaulted(store):
    """None of them ends in _mode, so none of them shows up as a feature switch."""
    for key in (
        "chat_ignore_channels",
        "chat_greeting_reaction",
        "chat_reply_in_threads",
        "chat_route_ping_staff",
    ):
        assert key in KEY_TYPES and KEY_HELP.get(key)
        assert not key.endswith("_mode")
    assert store.get(7, "chat_ignore_channels") == []
    assert store.get(7, "chat_greeting_reaction") is False
    assert store.get(7, "chat_reply_in_threads") is True
    assert store.get(7, "chat_route_ping_staff") is False


def test_the_chat_manners_keys_refuse_the_wrong_shape():
    assert coerce_value("chat_ignore_channels", [12, 12, 13]) == [12, 13]
    assert coerce_value("chat_greeting_reaction", True) is True
    for key, bad in (
        ("chat_ignore_channels", "12"),
        ("chat_greeting_reaction", "on"),
        ("chat_reply_in_threads", 1),
        ("chat_route_ping_staff", "yes"),
    ):
        with pytest.raises(SettingError):
            coerce_value(key, bad)


async def test_requests_ship_on_open_to_everyone_and_auto_approving_staff(store):
    assert store.get(7, "request_mode") == "on"
    assert store.get(7, "request_who_can_file") == "everyone"
    assert store.get(7, "request_auto_approve_staff") is True
    assert store.get(7, "request_dm_on_decision") is True
    for key in (
        "request_mode",
        "request_who_can_file",
        "request_auto_approve_staff",
        "request_notify_channel_id",
        "request_dm_on_decision",
    ):
        assert key in KEY_TYPES and KEY_HELP.get(key)


async def test_the_request_notice_lands_in_the_test_channel_while_test_mode_is_on(store):
    assert store.get(7, "request_notify_channel_id") == TEST_CH


async def test_the_request_notice_points_nowhere_once_test_mode_is_off(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=False, test_channel_id=TEST_CH)
    db = Database(tmp_path / "r.sqlite3")
    await db.connect()
    try:
        live = SettingsStore(db, settings)

        assert live.get(7, "request_notify_channel_id") is None
    finally:
        await db.close()


def test_the_request_switches_only_take_the_words_they_document():
    assert coerce_value("request_mode", "off") == "off"
    assert coerce_value("request_who_can_file", "staff") == "staff"
    assert coerce_value("request_auto_approve_staff", False) is False
    assert coerce_value("request_notify_channel_id", 12) == 12
    for key, bad in (
        ("request_mode", "shadow"),
        ("request_who_can_file", "mods"),
        ("request_auto_approve_staff", "yes"),
        ("request_notify_channel_id", "12"),
        ("request_dm_on_decision", 1),
    ):
        with pytest.raises(SettingError):
            coerce_value(key, bad)
