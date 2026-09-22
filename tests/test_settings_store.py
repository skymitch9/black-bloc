import json
import pathlib
import re

import pytest

from black_bloc import settings_store
from black_bloc.api.status import mode_keys
from black_bloc.automod import validate_rules
from black_bloc.config import load_settings
from black_bloc.emoji import SKIN_TONE_DEFAULT, SKIN_TONE_NAMES
from black_bloc.logkinds import FEATURES, LEVELS
from black_bloc.settings_store import (
    BIRTHDAY_CHANNEL_ID,
    BIRTHDAY_COLOR,
    BIRTHDAY_TEMPLATE,
    CHANNEL_MODE,
    DEFAULT_TIMEZONE_KEY,
    EVENTS_DEFAULT_MINUTES,
    EVENTS_LATE_CEILING_MINUTES,
    EVENTS_MAX_LATE_MINUTES,
    EVENTS_MOVED_LINE,
    EVENTS_MOVED_LINE_KEY,
    EVENTS_RETENTION_DAYS,
    EVENTS_RETENTION_MAX_DAYS,
    EVENTS_RETENTION_MIN_DAYS,
    EVENTS_SCHEDULED_NAME_KEY,
    EVENTS_SCHEDULED_NAME_TEMPLATE,
    EVENTS_TEST_RETENTION_KEY,
    EVENTS_TEST_RETENTION_MAX_MINUTES,
    EVENTS_TEST_RETENTION_MIN_MINUTES,
    EVENTS_TEST_RETENTION_MINUTES,
    GOLIVE_COSTREAM_AUTHOR,
    GOLIVE_COSTREAM_AUTHOR_KEY,
    GOLIVE_COSTREAM_MODE_KEY,
    GOLIVE_COSTREAM_TEMPLATE,
    GOLIVE_COSTREAM_TEMPLATE_KEY,
    GOLIVE_END_TEMPLATE,
    GOLIVE_LIVE_AUTHOR,
    GOLIVE_LIVE_AUTHOR_KEY,
    GOLIVE_LIVE_FIELD,
    GOLIVE_TEMPLATE,
    HONEYPOT_PURGE_MAX_DAYS,
    KEY_CHOICES,
    KEY_HELP,
    KEY_TYPES,
    LIVE_NOW_CHANNEL_ID,
    LOGS_DEFAULT,
    LOGS_MAX,
    LOGS_MIN,
    MEMBER_ROLE_ID,
    MODMAIL_CATEGORY_ID,
    MODMAIL_LOG_CHANNEL_ID,
    MODMAIL_OPEN_WITH_BUTTON,
    POLL_ARCHIVE_DAYS,
    POLL_ARCHIVE_MAX_DAYS,
    POLL_DEFAULT_HOURS,
    POLL_DRAFT_DAYS,
    POLL_DRAFT_MAX_DAYS,
    POLL_MAX_HOURS,
    POLL_MIN_HOURS,
    POLL_REMINDER_MAX_MINUTES,
    POLL_REMINDER_MINUTES,
    RAIDTRAIN_SCHEDULED_NAME_KEY,
    RAIDTRAIN_SCHEDULED_NAME_TEMPLATE,
    REQUEST_CARD_MOVES,
    REQUEST_FILED,
    REQUEST_FILED_KEY,
    TEMPVOICE_MODES,
    TEMPVOICE_NAME_TEMPLATE,
    TEXT_MAY_BE_BLANK,
    THREAD_MODE,
    TIME_STEP_KEY,
    TIME_STEP_MINUTES,
    TIMEZONE_CHOICES,
    TIMEZONE_CHOICES_KEY,
    TIMEZONE_CHOICES_MAX,
    WHERE_ALIAS_MAX,
    WHERE_ALIASES,
    WHERE_ALIASES_KEY,
    WHERE_CHECK_KEY,
    WHERE_CHECK_MAX_SECONDS,
    WHERE_CHECK_MIN_SECONDS,
    WHERE_CHECK_MODE,
    WHERE_CHECK_MODES,
    WHERE_CHECK_SECONDS,
    WHERE_CHECK_SECONDS_KEY,
    WHERE_HINT,
    WHERE_HINT_KEY,
    SettingError,
    SettingsStore,
    carry_end_wording,
    coerce_value,
    display_value,
    is_staff_command,
    member_is_staff,
    namespace_of,
    parse_value,
    require_staff,
    resolved_staff_roles,
    staff_roles_sentence,
    where_alias_table,
)
from black_bloc.storage.db import Database
from black_bloc.timezones import is_known

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


async def test_the_end_wording_is_one_key_and_v149s_default_is_untouched(store):
    """The two boxes became one, 2026-09-20: no mode, no suffix, {live} in the template.

    ⚠️ The DEFAULT deliberately did not move (conductor, 2026-09-20 — Deviation 1): nobody's
    ended announcement may change at the deploy, so it stays v149's rewrite, which has no
    {live} in it and therefore still rewrites the whole post.
    """
    assert store.get(1, "golive_end_template") == GOLIVE_END_TEMPLATE
    assert GOLIVE_END_TEMPLATE == (
        "**{name}** was streaming **{game}** — the stream has ended. {url}"
    )
    assert GOLIVE_LIVE_FIELD not in GOLIVE_END_TEMPLATE
    assert KEY_TYPES["golive_end_template"] == "text"
    assert GOLIVE_LIVE_FIELD in KEY_HELP["golive_end_template"]
    assert await store.set(1, "golive_end_template", "{live} (over)") == "{live} (over)"
    assert await store.set(1, "golive_end_template", "   ") == ""


async def _store_retired(store, guild_id, key, value):
    await store.db.conn.execute(
        "INSERT OR REPLACE INTO settings(guild_id, key, value, updated_by, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (guild_id, key, json.dumps(value), None, "2026-09-01T00:00:00+00:00"),
    )
    await store.db.conn.commit()


async def _rows(store, guild_id):
    cur = await store.db.conn.execute(
        "SELECT key FROM settings WHERE guild_id = ?", (guild_id,)
    )
    return {row["key"] for row in await cur.fetchall()}


async def test_a_custom_suffix_with_no_template_becomes_the_template(store):
    await _store_retired(store, 1, "golive_end_suffix", " (that's a wrap)")
    await _store_retired(store, 1, "golive_end_mode", "edit")

    said = await carry_end_wording(store, 1)

    assert said == {"carried_suffix": True, "dropped_mode": "edit"}
    assert store.get(1, "golive_end_template") == "{live} (that's a wrap)"
    assert await _rows(store, 1) == {"golive_end_template"}


async def test_a_guild_with_a_template_keeps_it_because_the_suffix_was_never_used(store):
    await store.set(1, "golive_end_template", "{name} was live")
    await _store_retired(store, 1, "golive_end_suffix", " (over)")

    said = await carry_end_wording(store, 1)

    assert said == {"carried_suffix": False, "dropped_mode": None}
    assert store.get(1, "golive_end_template") == "{name} was live"
    assert await _rows(store, 1) == {"golive_end_template"}


async def test_a_guild_that_had_only_the_off_mode_loses_it_and_gets_the_default_wording(store):
    await _store_retired(store, 1, "golive_end_mode", "off")

    said = await carry_end_wording(store, 1)

    assert said == {"carried_suffix": False, "dropped_mode": "off"}
    assert store.get(1, "golive_end_template") == GOLIVE_END_TEMPLATE
    assert await _rows(store, 1) == set()


async def test_a_second_boot_finds_nothing_to_carry_and_says_so(store):
    await _store_retired(store, 1, "golive_end_suffix", " (over)")

    assert await carry_end_wording(store, 1) is not None
    assert await carry_end_wording(store, 1) is None
    assert await carry_end_wording(store, 2) is None


async def test_the_carry_only_touches_the_guild_it_was_asked_about(store):
    await _store_retired(store, 1, "golive_end_suffix", " (one)")
    await _store_retired(store, 2, "golive_end_suffix", " (two)")

    await carry_end_wording(store, 1)

    assert store.get(1, "golive_end_template") == "{live} (one)"
    assert await _rows(store, 2) == {"golive_end_suffix"}


async def test_the_retired_end_keys_are_gone_from_the_registry(store):
    """A stored row is harmless and the boot pass drops it; a key is not."""
    gone = {"golive_end_mode", "golive_end_suffix"}

    assert gone & set(KEY_TYPES) == set()
    assert gone & set(KEY_HELP) == set()
    with pytest.raises(SettingError):
        coerce_value("golive_end_mode", "edit")


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


async def test_tempvoice_has_a_shadow_between_off_and_on(store):
    """The lobby is staff-only in shadow, so the enum has to carry all three."""
    assert TEMPVOICE_MODES == ("off", "shadow", "on")
    assert await store.set(1, "tempvoice_mode", "shadow") == "shadow"
    with pytest.raises(SettingError, match="off, shadow, on"):
        coerce_value("tempvoice_mode", "sideways")


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
    assert store.get(1, "events_where_link_in_description") is True
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


def test_the_member_optout_post_key_is_an_enum_of_three_with_end_as_the_default(store):
    """A member's opt-out ends the announcement that is out; this says what becomes of it."""
    key = settings_store.MEMBER_OPTOUT_POST_KEY
    assert key == "golive_member_optout_post"
    assert KEY_TYPES[key] == "enum"
    assert KEY_CHOICES[key] == ("end", "delete", "leave")
    assert store.get(1, key) == settings_store.MEMBER_OPTOUT_END == "end"
    assert "opts out of" in KEY_HELP[key] and "live role" in KEY_HELP[key]
    assert settings_store.namespace_of(key) == "golive"


def test_the_member_and_channel_optout_posts_are_two_keys_over_one_set_of_words(store):
    """One fact, one home (checklist 15): the member names point AT the channel's values."""
    assert settings_store.MEMBER_OPTOUT_POSTS is settings_store.CHANNEL_OPTOUT_POSTS
    assert settings_store.MEMBER_OPTOUT_DELETE == settings_store.CHANNEL_OPTOUT_DELETE
    assert settings_store.MEMBER_OPTOUT_LEAVE == settings_store.CHANNEL_OPTOUT_LEAVE
    assert settings_store.MEMBER_OPTOUT_POST_KEY != settings_store.CHANNEL_OPTOUT_POST_KEY
    assert store.get(1, settings_store.CHANNEL_OPTOUT_POST_KEY) == "end"


def test_the_test_mode_retention_is_its_own_key_in_minutes(store):
    """Follow-up 3: seven days of test rooms is clutter, so test mode counts in minutes."""
    assert KEY_TYPES[EVENTS_TEST_RETENTION_KEY] == "int"
    assert KEY_HELP[EVENTS_TEST_RETENTION_KEY]
    assert store.get(1, EVENTS_TEST_RETENTION_KEY) == EVENTS_TEST_RETENTION_MINUTES == 5
    assert coerce_value(EVENTS_TEST_RETENTION_KEY, EVENTS_TEST_RETENTION_MIN_MINUTES) == 1
    assert coerce_value(EVENTS_TEST_RETENTION_KEY, EVENTS_TEST_RETENTION_MAX_MINUTES) == 1440


def test_the_test_mode_retention_refuses_both_ends_in_words():
    with pytest.raises(SettingError, match="cannot be less than 1") as too_small:
        coerce_value(EVENTS_TEST_RETENTION_KEY, 0)
    assert "every five minutes" in str(too_small.value)

    with pytest.raises(SettingError, match="cannot be more than 1440") as too_big:
        coerce_value(EVENTS_TEST_RETENTION_KEY, EVENTS_TEST_RETENTION_MAX_MINUTES + 1)
    assert "events_channel_retention_days" in str(too_big.value)


def test_the_shorthand_table_is_a_staff_editable_key(store):
    """Follow-up 4: `ttv/skyaiva` is a decision, so it is a setting and not a hard-coded list."""
    assert KEY_TYPES[WHERE_ALIASES_KEY] == "text"
    assert KEY_HELP[WHERE_ALIASES_KEY]
    assert namespace_of(WHERE_ALIASES_KEY) == "events"
    assert store.get(1, WHERE_ALIASES_KEY) == WHERE_ALIASES
    assert where_alias_table(WHERE_ALIASES)["ttv"] == "https://twitch.tv/{handle}"
    assert where_alias_table(WHERE_ALIASES)["yt"] == "https://youtube.com/@{handle}"


def test_the_shorthand_table_drops_an_entry_it_cannot_read_and_keeps_the_first_spelling():
    kept = coerce_value(
        WHERE_ALIASES_KEY,
        "ttv=https://twitch.tv/{handle}, nonsense, sp ace=https://a.com/{handle}, "
        "http=http://a.com/{handle}, none=https://a.com/there, two=https://a.com/{handle}{handle}, "
        "stray=https://a.com/{who}, ttv=https://nope.example/{handle}",
    )

    assert kept == "ttv=https://twitch.tv/{handle}"


def test_a_shorthand_table_with_nothing_readable_in_it_is_refused_in_words():
    with pytest.raises(SettingError, match="shorthand Black Bloc can read") as caught:
        coerce_value(WHERE_ALIASES_KEY, "nonsense, also nonsense")
    said = str(caught.value)

    assert "{handle}" in said and "ttv=https://twitch.tv/" in said
    assert str(WHERE_ALIAS_MAX) in said


def test_the_shorthand_table_stops_at_thirty_two_entries():
    said = coerce_value(
        WHERE_ALIASES_KEY,
        ", ".join(f"a{one}=https://a.com/{{handle}}" for one in range(WHERE_ALIAS_MAX + 5)),
    )

    assert len(where_alias_table(said)) == WHERE_ALIAS_MAX == 32


def test_whether_a_link_is_tried_first_is_a_three_way_key(store):
    assert KEY_TYPES[WHERE_CHECK_KEY] == "enum"
    assert KEY_HELP[WHERE_CHECK_KEY]
    assert namespace_of(WHERE_CHECK_KEY) == "events"
    assert store.get(1, WHERE_CHECK_KEY) == WHERE_CHECK_MODE == "warn"
    for mode in WHERE_CHECK_MODES:
        assert coerce_value(WHERE_CHECK_KEY, mode) == mode
    with pytest.raises(SettingError, match="off, warn, refuse"):
        coerce_value(WHERE_CHECK_KEY, "maybe")


def test_how_long_the_link_check_waits_is_bounded_by_what_a_modal_has(store):
    assert KEY_TYPES[WHERE_CHECK_SECONDS_KEY] == "int"
    assert KEY_HELP[WHERE_CHECK_SECONDS_KEY]
    assert store.get(1, WHERE_CHECK_SECONDS_KEY) == WHERE_CHECK_SECONDS == 2
    assert coerce_value(WHERE_CHECK_SECONDS_KEY, WHERE_CHECK_MIN_SECONDS) == 1
    assert coerce_value(WHERE_CHECK_SECONDS_KEY, WHERE_CHECK_MAX_SECONDS) == 3

    with pytest.raises(SettingError, match="cannot be less than 1") as too_small:
        coerce_value(WHERE_CHECK_SECONDS_KEY, 0)
    assert "called unreachable" in str(too_small.value)

    with pytest.raises(SettingError, match="cannot be more than 3") as too_big:
        coerce_value(WHERE_CHECK_SECONDS_KEY, WHERE_CHECK_MAX_SECONDS + 1)
    assert "three seconds" in str(too_big.value)


async def test_the_sentence_above_the_channel_picker_is_a_key_both_doors_reach(store):
    """Follow-up 5: every word the bot posts is editable on the site, this one included."""
    assert KEY_TYPES[WHERE_HINT_KEY] == "text"
    assert KEY_HELP[WHERE_HINT_KEY]
    assert namespace_of(WHERE_HINT_KEY) == "events"
    assert store.get(1, WHERE_HINT_KEY) == WHERE_HINT
    assert WHERE_HINT == (
        "If you do not see your channel, start typing the channel name and it should appear."
    )

    await store.set(1, WHERE_HINT_KEY, "Start typing, it is in there.")
    assert store.get(1, WHERE_HINT_KEY) == "Start typing, it is in there."


def test_the_sentence_above_the_channel_picker_may_be_emptied_to_hide_it():
    assert WHERE_HINT_KEY in TEXT_MAY_BE_BLANK
    assert coerce_value(WHERE_HINT_KEY, "") == ""
    assert coerce_value(WHERE_HINT_KEY, "   ") == ""


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


async def test_the_open_a_ticket_with_door_ships_hidden_and_is_a_key_both_doors_reach(store):
    """The owner asked for the door kept but hidden, so the key is a bool defaulting to false
    and the help says which way round it reads."""
    assert KEY_TYPES[MODMAIL_OPEN_WITH_BUTTON] == "bool"
    assert store.get(1, MODMAIL_OPEN_WITH_BUTTON) is False
    assert settings_store.namespace_of(MODMAIL_OPEN_WITH_BUTTON) == "modmail"
    assert "Open a ticket with" in KEY_HELP[MODMAIL_OPEN_WITH_BUTTON]
    with pytest.raises(SettingError, match="true or false"):
        coerce_value(MODMAIL_OPEN_WITH_BUTTON, "sometimes")

    await store.set(1, MODMAIL_OPEN_WITH_BUTTON, True)

    assert store.get(1, MODMAIL_OPEN_WITH_BUTTON) is True


async def test_the_seven_upload_keys_are_gone_from_the_registry_altogether(store):
    """The uploads half was removed 2026-09-18; a stored row is harmless, a key is not."""
    gone = {
        "youtube_mode",
        "youtube_channel_id",
        "youtube_ping_role_id",
        "youtube_ping_fan_roles",
        "youtube_announce_shorts",
        "youtube_template",
        "youtube_poll_minutes",
    }

    assert gone & set(KEY_TYPES) == set()
    assert gone & set(KEY_HELP) == set()
    assert store.get(1, "youtube_log_level") == "important"


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
    assert coerce_value("poll_mode", "shadow") == "shadow"
    assert coerce_value("poll_review_mode", "on") == "on"
    assert coerce_value("poll_who_can_create", "everyone") == "everyone"
    for key, bad in (
        ("poll_mode", "rehearsal"),
        ("poll_review_mode", "shadow"),
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
        "poll_pin",
        "poll_shadow_note",
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


async def test_every_ping_role_decision_is_a_key_the_dashboard_and_the_bot_both_reach(store):
    """F14 D1-D6: none of these is a constant, so every one of them is editable both ways."""
    for key in (
        "pings_mode",
        "pings_events_role_name",
        "pings_fan_role_creation",
        "pings_fan_role_template",
        "pings_fan_role_on_unlink",
        "pings_fan_role_delete",
        "pings_log_level",
        "pings_streamer_stale_days",
        "pings_empty_role_days",
        "pings_onboarding_managed",
        "pings_onboarding_prompt_title",
        "pings_onboarding_option_cap",
    ):
        assert key in KEY_TYPES and KEY_HELP.get(key)
    assert store.get(7, "pings_mode") == "off"
    assert store.get(7, "pings_events_role_name") == "Events"
    # The pings remake made `follow` the default: a role exists only where somebody wants it.
    assert store.get(7, "pings_fan_role_creation") == "follow"
    assert store.get(7, "pings_fan_role_template") == "{name} pings"
    assert store.get(7, "pings_fan_role_on_unlink") == "keep"
    assert store.get(7, "pings_fan_role_delete") is True
    assert store.get(7, "pings_streamer_stale_days") == 90
    assert store.get(7, "pings_empty_role_days") == 30
    assert store.get(7, "pings_onboarding_managed") is True
    assert store.get(7, "pings_onboarding_prompt_title") == "What should ping you?"
    assert store.get(7, "pings_onboarding_option_cap") == 25


def test_the_ping_role_choices_refuse_anything_else():
    assert coerce_value("pings_mode", "on") == "on"
    assert coerce_value("pings_fan_role_creation", "auto") == "auto"
    assert coerce_value("pings_fan_role_on_unlink", "delete") == "delete"
    assert coerce_value("pings_fan_role_delete", False) is False
    assert coerce_value("pings_fan_role_template", "fans of {name}") == "fans of {name}"
    for key, bad in (
        ("pings_mode", "shadow"),
        ("pings_fan_role_creation", "anybody"),
        ("pings_fan_role_on_unlink", "forget"),
        ("pings_fan_role_delete", "yes"),
        ("pings_fan_role_template", ""),
        ("pings_events_role_name", 5),
    ):
        with pytest.raises(SettingError):
            coerce_value(key, bad)


def test_the_ping_role_mode_is_read_as_a_feature_switch_on_the_health_page():
    assert "pings_mode" in mode_keys()


async def test_every_feature_has_a_log_level_key_defaulting_to_important(store):
    keys = [f"{feature}_log_level" for feature in FEATURES]
    assert len(keys) == 21
    assert "request_log_level" in keys
    assert "pings_log_level" in keys
    assert "raidtrain_log_level" in keys
    for key in keys:
        assert KEY_TYPES[key] == "enum"
        assert KEY_CHOICES[key] == LEVELS
        assert KEY_HELP.get(key)
    # The self-test is the one exception, and it is deliberate: the rows are kept on the
    # dashboard under Test, and none of them is repeated into Discord unless staff ask.
    for key in [one for one in keys if one != "selftest_log_level"]:
        assert store.get(7, key) == "important"
        assert store.default(key) == "important"
    assert store.default("selftest_log_level") == "off"
    assert store.get(7, "selftest_log_level") == "off"


def test_a_log_level_takes_only_the_three_levels():
    assert coerce_value("golive_log_level", "off") == "off"
    assert coerce_value("mod_log_level", "all") == "all"
    for bad in ("quiet", "IMPORTANT", "on", 1, None):
        with pytest.raises(SettingError):
            coerce_value("chat_log_level", bad)


def test_no_log_level_key_is_read_as_a_feature_switch():
    """`api/status.py` calls every key ending in `_mode` a feature; none of these does."""
    assert not [key for key in mode_keys() if key.endswith("_log_level")]
    assert all(not key.endswith("_mode") for key in KEY_TYPES if key.endswith("_log_level"))
async def test_requests_ship_on_and_open_to_everyone_with_nothing_auto_approved(store):
    """Nothing approves itself any more (owner, 2026-09-02: 'Even a staff request can be bad')."""
    assert store.get(7, "request_mode") == "on"
    assert store.get(7, "request_who_can_file") == "everyone"
    assert store.get(7, "request_dm_on_decision") is True
    assert "request_auto_approve_staff" not in KEY_TYPES
    for key in (
        "request_mode",
        "request_who_can_file",
        "request_notify_channel_id",
        "request_status_channel_id",
        "request_dm_on_decision",
        "request_channel_moves",
        "request_review_by_other",
        "request_panel_minutes",
        "request_panel_own_list",
        "request_check_fallback_channel",
        "request_check_on_ready",
        "request_post_buttons",
        "request_forum_adopts_posts",
    ):
        assert key in KEY_TYPES and KEY_HELP.get(key)


async def test_every_card_but_done_posts_and_one_pair_of_eyes_is_enough_until_a_lead_says_otherwise(
    store,
):
    """Owner, 2026-09-03: the done card is the site log's business; a second pair of eyes is off."""
    assert store.get(7, "request_channel_moves") == [
        "filed",
        "in_progress",
        "review",
        "sent_back",
        "hold",
        "declined",
    ]
    assert "done" in REQUEST_CARD_MOVES and "check_asked" in REQUEST_CARD_MOVES
    assert len(REQUEST_CARD_MOVES) == 8
    assert store.get(7, "request_review_by_other") is False
    assert KEY_TYPES["request_channel_moves"] == "enums"
    assert KEY_CHOICES["request_channel_moves"] == REQUEST_CARD_MOVES


async def test_the_two_ask_them_to_check_decisions_are_keys_both_ways(store):
    """Checklist 33 — the fallback ping and the auto-ask are settings, never constants."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "request_check_fallback_channel") is True
    assert store.get(7, "request_check_on_ready") is False
    for key in ("request_check_fallback_channel", "request_check_on_ready"):
        assert KEY_TYPES[key] == "bool"
        assert reachable_on_the_panel(key)
        with pytest.raises(SettingError):
            coerce_value(key, "true")
    assert "closed DMs" in KEY_HELP["request_check_fallback_channel"]
    assert "ready to check" in KEY_HELP["request_check_on_ready"]
    await store.set(7, "request_check_on_ready", True)
    assert store.get(7, "request_check_on_ready") is True


async def test_the_post_move_buttons_are_a_key_both_doors_reach(store):
    """Checklist 33 — blackmail-threads §F: drawing the moves on a post is a decision."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert KEY_TYPES["request_post_buttons"] == "bool"
    assert store.get(7, "request_post_buttons") is True
    assert reachable_on_the_panel("request_post_buttons")
    assert "forum post" in KEY_HELP["request_post_buttons"]
    with pytest.raises(SettingError):
        coerce_value("request_post_buttons", "true")
    await store.set(7, "request_post_buttons", False)
    assert store.get(7, "request_post_buttons") is False


async def test_adopting_a_hand_made_forum_post_is_a_key_both_doors_reach(store):
    """Checklist 33 — blackmail-threads §G: whether a post becomes a request is a decision."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert KEY_TYPES["request_forum_adopts_posts"] == "bool"
    assert store.get(7, "request_forum_adopts_posts") is True
    assert reachable_on_the_panel("request_forum_adopts_posts")
    assert "by hand" in KEY_HELP["request_forum_adopts_posts"]
    with pytest.raises(SettingError):
        coerce_value("request_forum_adopts_posts", "true")
    await store.set(7, "request_forum_adopts_posts", False)
    assert store.get(7, "request_forum_adopts_posts") is False


async def test_the_two_send_to_decisions_are_keys_both_doors_reach(store):
    """Checklist 33 — send-to-design §A: the move itself and the member's answer window.

    Both are filed under `request` through NAMESPACE_OVERRIDE, because `/settings` groups
    select is at Discord's cap of 25 and a 26th namespace would drop one off it silently."""
    from black_bloc.settings_panel import namespace_of, reachable_on_the_panel
    from black_bloc.settings_store import (
        HANDOFF_CONFIRM_HOURS,
        HANDOFF_CONFIRM_HOURS_MAX,
        HANDOFF_CONFIRM_HOURS_MIN,
        HANDOFF_MODE,
        HANDOFF_MODES,
    )

    assert (HANDOFF_MODE, HANDOFF_CONFIRM_HOURS) == ("handoff_mode", "handoff_confirm_hours")
    assert KEY_TYPES[HANDOFF_MODE] == "enum" and KEY_CHOICES[HANDOFF_MODE] == HANDOFF_MODES
    assert KEY_TYPES[HANDOFF_CONFIRM_HOURS] == "int"
    assert store.get(7, HANDOFF_MODE) == "on"
    assert store.get(7, HANDOFF_CONFIRM_HOURS) == 24
    for key in (HANDOFF_MODE, HANDOFF_CONFIRM_HOURS):
        assert reachable_on_the_panel(key)
        assert namespace_of(key) == "request"
        assert KEY_HELP.get(key)
    with pytest.raises(SettingError):
        coerce_value(HANDOFF_MODE, "sometimes")
    with pytest.raises(SettingError):
        coerce_value(HANDOFF_CONFIRM_HOURS, HANDOFF_CONFIRM_HOURS_MAX + 1)
    with pytest.raises(SettingError):
        coerce_value(HANDOFF_CONFIRM_HOURS, HANDOFF_CONFIRM_HOURS_MIN - 1)
    await store.set(7, HANDOFF_MODE, "off")
    await store.set(7, HANDOFF_CONFIRM_HOURS, 48)
    assert store.get(7, HANDOFF_MODE) == "off"
    assert store.get(7, HANDOFF_CONFIRM_HOURS) == 48


def test_the_card_moves_key_takes_any_of_the_eight_and_nothing_else():
    assert coerce_value("request_channel_moves", []) == []
    assert coerce_value("request_channel_moves", ["done"]) == ["done"]
    assert coerce_value("request_channel_moves", ["done", "done"]) == ["done"]
    assert coerce_value("request_channel_moves", ["done", "filed"]) == ["filed", "done"]
    assert coerce_value("request_review_by_other", True) is True
    for bad in ("done", ["shipped"], ["done", "shipped"], 1, None):
        with pytest.raises(SettingError):
            coerce_value("request_channel_moves", bad)
    with pytest.raises(SettingError):
        coerce_value("request_review_by_other", "true")


def test_the_card_moves_key_is_typed_in_as_a_comma_list_and_read_back_as_words():
    assert parse_value("request_channel_moves", " done , hold ") == ["done", "hold"]
    assert parse_value("request_channel_moves", "") == []
    assert display_value("request_channel_moves", ["done", "hold"]) == "done, hold"
    assert display_value("request_channel_moves", []) == "none of them"


def test_every_registry_key_is_reachable_from_the_panel_as_well_as_the_dashboard():
    """Checklist 33 — a key `/settings` cannot open is a dashboard-only key. `automod_rules` is
    the one deliberate exception: `/automod` ▸ **A rule…** owns the rule book."""
    from black_bloc.settings_panel import groups, has_editor, keys_in

    opened = {key for group in groups() for key in keys_in(group)}

    assert opened == set(KEY_TYPES)
    assert {key for key in opened if not has_editor(key)} == {"automod_rules"}
    assert "request_channel_moves" in opened and "request_review_by_other" in opened


async def test_the_request_panel_stays_up_ten_minutes_by_default(store):
    """Ten, not fifteen: the footer needs Discord's 15-minute interaction window still open."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "request_panel_minutes") == 10
    assert "15" in KEY_HELP["request_panel_minutes"]
    assert KEY_TYPES["request_panel_minutes"] == "int"
    assert reachable_on_the_panel("request_panel_minutes")
    await store.set(7, "request_panel_minutes", 30)
    assert store.get(7, "request_panel_minutes") == 30
    with pytest.raises(SettingError):
        coerce_value("request_panel_minutes", -1)
    with pytest.raises(SettingError):
        coerce_value("request_panel_minutes", "15")
    assert parse_value("request_panel_minutes", "45") == 45


async def test_the_poll_panel_stays_up_ten_minutes_by_default(store):
    """Same reason as the request panel: 15 loses Discord's interaction window and the footer."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "poll_panel_minutes") == 10
    assert "15" in KEY_HELP["poll_panel_minutes"]
    assert KEY_TYPES["poll_panel_minutes"] == "int"
    assert reachable_on_the_panel("poll_panel_minutes")
    await store.set(7, "poll_panel_minutes", 20)
    assert store.get(7, "poll_panel_minutes") == 20
    with pytest.raises(SettingError):
        coerce_value("poll_panel_minutes", -1)
    with pytest.raises(SettingError):
        coerce_value("poll_panel_minutes", "15")
    assert parse_value("poll_panel_minutes", "45") == 45


async def test_the_mod_panel_stays_up_ten_minutes_by_default(store):
    """Same reason as every other panel: 15 loses Discord's window and the gone-quiet footer."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "mod_panel_minutes") == 10
    assert "15" in KEY_HELP["mod_panel_minutes"]
    assert KEY_TYPES["mod_panel_minutes"] == "int"
    assert reachable_on_the_panel("mod_panel_minutes")
    await store.set(7, "mod_panel_minutes", 20)
    assert store.get(7, "mod_panel_minutes") == 20
    with pytest.raises(SettingError):
        coerce_value("mod_panel_minutes", -1)
    with pytest.raises(SettingError):
        coerce_value("mod_panel_minutes", "15")
    assert parse_value("mod_panel_minutes", "45") == 45


async def test_the_memory_panel_stays_up_ten_minutes_by_default(store):
    """Same reason as every other panel: 15 loses Discord's window and the gone-quiet footer."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "memory_panel_minutes") == 10
    assert "15" in KEY_HELP["memory_panel_minutes"]
    assert KEY_TYPES["memory_panel_minutes"] == "int"
    assert reachable_on_the_panel("memory_panel_minutes")
    await store.set(7, "memory_panel_minutes", 25)
    assert store.get(7, "memory_panel_minutes") == 25
    with pytest.raises(SettingError):
        coerce_value("memory_panel_minutes", -1)
    with pytest.raises(SettingError):
        coerce_value("memory_panel_minutes", "15")
    assert parse_value("memory_panel_minutes", "45") == 45


async def test_the_youtube_panel_stays_up_ten_minutes_by_default(store):
    """Same reason as every other panel: 15 loses Discord's window and the gone-quiet footer."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "youtube_panel_minutes") == 10
    assert "15" in KEY_HELP["youtube_panel_minutes"]
    assert KEY_TYPES["youtube_panel_minutes"] == "int"
    assert reachable_on_the_panel("youtube_panel_minutes")
    await store.set(7, "youtube_panel_minutes", 25)
    assert store.get(7, "youtube_panel_minutes") == 25
    with pytest.raises(SettingError):
        coerce_value("youtube_panel_minutes", -1)
    assert parse_value("youtube_panel_minutes", "45") == 45


async def test_the_pings_panel_stays_up_ten_minutes_by_default(store):
    """Same reason as every other panel: 15 loses Discord's window and the gone-quiet footer."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "voice_panel_minutes") == 10
    assert "15" in KEY_HELP["voice_panel_minutes"]
    assert KEY_TYPES["voice_panel_minutes"] == "int"
    assert reachable_on_the_panel("voice_panel_minutes")
    await store.set(7, "voice_panel_minutes", 25)
    assert store.get(7, "voice_panel_minutes") == 25
    assert parse_value("voice_panel_minutes", "45") == 45
    assert store.get(7, "pings_panel_minutes") == 10
    assert "15" in KEY_HELP["pings_panel_minutes"]
    assert KEY_TYPES["pings_panel_minutes"] == "int"
    assert reachable_on_the_panel("pings_panel_minutes")
    await store.set(7, "pings_panel_minutes", 25)
    assert store.get(7, "pings_panel_minutes") == 25
    with pytest.raises(SettingError):
        coerce_value("pings_panel_minutes", -1)
    assert parse_value("pings_panel_minutes", "45") == 45


async def test_the_honeypot_panel_stays_up_ten_minutes_by_default(store):
    """Same reason as every other panel: 15 loses Discord's window and the gone-quiet footer."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "honeypot_panel_minutes") == 10
    assert "15" in KEY_HELP["honeypot_panel_minutes"]
    assert KEY_TYPES["honeypot_panel_minutes"] == "int"
    assert reachable_on_the_panel("honeypot_panel_minutes")
    await store.set(7, "honeypot_panel_minutes", 25)
    assert store.get(7, "honeypot_panel_minutes") == 25
    with pytest.raises(SettingError):
        coerce_value("honeypot_panel_minutes", -1)
    with pytest.raises(SettingError):
        coerce_value("honeypot_panel_minutes", "15")
    assert parse_value("honeypot_panel_minutes", "45") == 45


async def test_the_settings_panel_stays_up_ten_minutes_by_default(store):
    """Same reason as every other panel: 15 loses Discord's window and the gone-quiet footer."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "settings_panel_minutes") == 10
    assert "15" in KEY_HELP["settings_panel_minutes"]
    assert KEY_TYPES["settings_panel_minutes"] == "int"
    assert reachable_on_the_panel("settings_panel_minutes")
    await store.set(7, "settings_panel_minutes", 25)
    assert store.get(7, "settings_panel_minutes") == 25
    with pytest.raises(SettingError):
        coerce_value("settings_panel_minutes", -1)
    with pytest.raises(SettingError):
        coerce_value("settings_panel_minutes", "15")
    assert parse_value("settings_panel_minutes", "45") == 45


async def test_only_manage_server_re_points_the_core_channels_by_default(store):
    """F-S3 (a): access-REDUCING, so it ships true and the rest of /settings opens either way."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "settings_core_keys_admin_only") is True
    assert KEY_TYPES["settings_core_keys_admin_only"] == "bool"
    assert "Manage Server" in KEY_HELP["settings_core_keys_admin_only"]
    assert reachable_on_the_panel("settings_core_keys_admin_only")
    await store.set(7, "settings_core_keys_admin_only", False)
    assert store.get(7, "settings_core_keys_admin_only") is False
    with pytest.raises(SettingError):
        coerce_value("settings_core_keys_admin_only", "false")
    assert parse_value("settings_core_keys_admin_only", "off") is False


async def test_is_stored_answers_what_clear_would_find_without_deleting_it(store):
    """`Put the default back` renders only on a key with a row, so it must be askable."""
    assert store.get(7, "birthday_role_id") is None
    assert store.is_stored(7, "birthday_role_id") is False

    await store.set(7, "birthday_role_id", 555)
    assert store.is_stored(7, "birthday_role_id") is True
    assert store.is_stored(8, "birthday_role_id") is False

    await store.set(7, "poll_panel_minutes", 10)
    assert store.get(7, "poll_panel_minutes") == store.default("poll_panel_minutes")
    assert store.is_stored(7, "poll_panel_minutes") is True

    assert await store.clear(7, "birthday_role_id") is True
    assert store.is_stored(7, "birthday_role_id") is False
    with pytest.raises(SettingError):
        store.is_stored(7, "not_a_setting")


async def test_both_new_settings_keys_file_under_core_not_a_group_of_their_own(store):
    """Their `settings_` prefix would make a group of their own; CORE_KEYS is what stops it.

    The count is 23 because `logs_count` / `logs_important_only` opened a `logs` group on
    purpose — they belong to every feature's Logs button, not to `/settings`.
    """
    assert namespace_of("settings_panel_minutes") == "core"
    assert namespace_of("settings_core_keys_admin_only") == "core"
    assert len({namespace_of(key) for key in KEY_TYPES}) == 24


async def test_the_automod_panel_stays_up_ten_minutes_by_default(store):
    """Same reason as every other panel: 15 loses Discord's window and the gone-quiet footer."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "automod_panel_minutes") == 10
    assert "15" in KEY_HELP["automod_panel_minutes"]
    assert KEY_TYPES["automod_panel_minutes"] == "int"
    assert reachable_on_the_panel("automod_panel_minutes")
    await store.set(7, "automod_panel_minutes", 25)
    assert store.get(7, "automod_panel_minutes") == 25
    with pytest.raises(SettingError):
        coerce_value("automod_panel_minutes", -1)
    with pytest.raises(SettingError):
        coerce_value("automod_panel_minutes", "15")
    assert parse_value("automod_panel_minutes", "45") == 45


async def test_whether_arming_automod_asks_twice_is_a_setting_not_a_constant(store):
    """Owner fork F-A1 = (a): confirm by default, and a server that finds it tedious may stop it."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "automod_arm_needs_confirm") is True
    assert KEY_TYPES["automod_arm_needs_confirm"] == "bool"
    assert "automod_arm_needs_confirm" in KEY_HELP
    assert reachable_on_the_panel("automod_arm_needs_confirm")
    await store.set(7, "automod_arm_needs_confirm", False)
    assert store.get(7, "automod_arm_needs_confirm") is False
    with pytest.raises(SettingError):
        coerce_value("automod_arm_needs_confirm", "yes")


async def test_the_chat_panel_key_is_picked_up_by_the_prefix_scan_with_no_second_edit(store):
    """`CHAT_KEYS` is `startswith('chat_')` over `KEY_TYPES`, so registering it is the only edit."""
    from black_bloc.cogs.content.chat import CHAT_KEYS
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "chat_panel_minutes") == 10
    assert "15" in KEY_HELP["chat_panel_minutes"]
    assert "/chat panel" in KEY_HELP["chat_panel_minutes"]
    assert KEY_TYPES["chat_panel_minutes"] == "int"
    assert reachable_on_the_panel("chat_panel_minutes")
    assert "chat_panel_minutes" in CHAT_KEYS
    await store.set(7, "chat_panel_minutes", 25)
    assert store.get(7, "chat_panel_minutes") == 25
    with pytest.raises(SettingError):
        coerce_value("chat_panel_minutes", -1)
    with pytest.raises(SettingError):
        coerce_value("chat_panel_minutes", "15")
    assert parse_value("chat_panel_minutes", "45") == 45


async def test_the_raid_train_panel_stays_up_ten_minutes_by_default(store):
    """Same reason as every other panel: 15 loses Discord's window and the gone-quiet footer."""
    from black_bloc.raidtrain import PANEL_MINUTES_KEY
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, PANEL_MINUTES_KEY) == 10
    assert "15" in KEY_HELP[PANEL_MINUTES_KEY]
    assert "/raidtrain panel" in KEY_HELP[PANEL_MINUTES_KEY]
    assert KEY_TYPES[PANEL_MINUTES_KEY] == "int"
    assert reachable_on_the_panel(PANEL_MINUTES_KEY)
    await store.set(7, PANEL_MINUTES_KEY, 25)
    assert store.get(7, PANEL_MINUTES_KEY) == 25
    with pytest.raises(SettingError):
        coerce_value(PANEL_MINUTES_KEY, -1)
    with pytest.raises(SettingError):
        coerce_value(PANEL_MINUTES_KEY, "15")
    assert parse_value(PANEL_MINUTES_KEY, "45") == 45


async def test_how_long_the_rolemenu_panel_stays_live_is_a_setting_both_doors_reach(store):
    from black_bloc.rolemenus import PANEL_MINUTES_KEY
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, PANEL_MINUTES_KEY) == 10
    assert "15" in KEY_HELP[PANEL_MINUTES_KEY]
    assert "/rolemenu panel" in KEY_HELP[PANEL_MINUTES_KEY]
    assert KEY_TYPES[PANEL_MINUTES_KEY] == "int"
    assert reachable_on_the_panel(PANEL_MINUTES_KEY)
    await store.set(7, PANEL_MINUTES_KEY, 25)
    assert store.get(7, PANEL_MINUTES_KEY) == 25
    with pytest.raises(SettingError):
        coerce_value(PANEL_MINUTES_KEY, -1)
    with pytest.raises(SettingError):
        coerce_value(PANEL_MINUTES_KEY, "15")
    assert parse_value(PANEL_MINUTES_KEY, "45") == 45


async def test_whether_staff_unlinking_somebody_dms_them_is_a_setting_not_a_constant(store):
    """Staff-final-say says the person is told; checklist 33 says the server may decide."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "youtube_unlink_dms_them") is True
    assert KEY_TYPES["youtube_unlink_dms_them"] == "bool"
    assert "youtube_unlink_dms_them" in KEY_HELP
    assert reachable_on_the_panel("youtube_unlink_dms_them")
    await store.set(7, "youtube_unlink_dms_them", False)
    assert store.get(7, "youtube_unlink_dms_them") is False
    with pytest.raises(SettingError):
        coerce_value("youtube_unlink_dms_them", "yes")


async def test_the_live_half_ships_off_and_is_reachable_from_both_doors(store):
    """Checklist 33: the three decisions youtube-live adds are registry keys, not constants."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "youtube_live_mode") == "off"
    assert store.get(7, "youtube_live_poll_minutes") == 5
    assert store.get(7, "youtube_live_end_misses") == 2
    for key in ("youtube_live_mode", "youtube_live_poll_minutes", "youtube_live_end_misses"):
        assert KEY_HELP[key] and reachable_on_the_panel(key)
        assert namespace_of(key) == "youtube"
    assert KEY_CHOICES["youtube_live_mode"] == ("off", "shadow", "on")


async def test_the_live_probe_gap_and_the_quiet_probe_count_are_both_bounded(store):
    """A one-minute probe fetches the same page twice; one quiet probe ends a live stream."""
    for key, low, high in (
        ("youtube_live_poll_minutes", 2, 60),
        ("youtube_live_end_misses", 1, 5),
    ):
        assert coerce_value(key, low) == low and coerce_value(key, high) == high
        with pytest.raises(SettingError):
            coerce_value(key, low - 1)
        with pytest.raises(SettingError):
            coerce_value(key, high + 1)
    with pytest.raises(SettingError):
        coerce_value("youtube_live_mode", "sometimes")


async def test_the_youtube_keys_the_panel_only_reads_keep_their_defaults(store):
    """The panel changed the door, not the room: no surviving `youtube_*` default moved."""
    assert store.get(7, "youtube_panel_minutes") == 10
    assert store.get(7, "youtube_unlink_dms_them") is True
    assert store.get(7, "youtube_live_mode") == "off"


async def test_the_eight_chat_memory_keys_are_untouched_by_the_panel(store):
    """The panel changed the door, not the room: no `chat_memory_*` default moved."""
    assert store.get(7, "chat_memory_mode") == "off"
    assert store.get(7, "chat_memory_consent") == "optout"
    assert store.get(7, "chat_memory_retention_days") == 180
    assert store.get(7, "chat_memory_dm_scope") == "separate"
    assert store.get(7, "chat_memory_staff_view") == "counts"
    assert store.get(7, "chat_memory_notes_max") == 6
    assert store.get(7, "chat_memory_threads_max") == 5
    assert store.get(7, "chat_memory_model") == ""
    for key in ("chat_memory_consent", "chat_memory_staff_view"):
        assert "/chat memory" not in KEY_HELP[key]
        assert "/memory" in KEY_HELP[key]


async def test_whoever_started_a_poll_may_close_it_until_a_lead_says_otherwise(store):
    """Owner, 2026-09-03 (design fork I-2): keep today's behaviour, and make it a key."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "poll_creator_may_end") is True
    assert KEY_TYPES["poll_creator_may_end"] == "bool"
    assert "staff can" in KEY_HELP["poll_creator_may_end"]
    assert reachable_on_the_panel("poll_creator_may_end")
    await store.set(7, "poll_creator_may_end", False)
    assert store.get(7, "poll_creator_may_end") is False
    with pytest.raises(SettingError):
        coerce_value("poll_creator_may_end", "false")
    assert parse_value("poll_creator_may_end", "false") is False


async def test_a_half_written_poll_can_be_saved_until_a_lead_turns_drafts_off(store):
    """Owner, 2026-09-06: "B but only save 1 draft per person max" — and it is a key."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "poll_drafts") is True
    assert KEY_TYPES["poll_drafts"] == "bool"
    assert "Save for later" in KEY_HELP["poll_drafts"]
    assert "kept, not deleted" in KEY_HELP["poll_drafts"]
    assert reachable_on_the_panel("poll_drafts")
    await store.set(7, "poll_drafts", False)
    assert store.get(7, "poll_drafts") is False
    with pytest.raises(SettingError):
        coerce_value("poll_drafts", "false")
    assert parse_value("poll_drafts", "false") is False


async def test_a_saved_draft_is_kept_a_fortnight_and_zero_days_keeps_it_for_ever(store):
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "poll_draft_days") == POLL_DRAFT_DAYS == 14
    assert KEY_TYPES["poll_draft_days"] == "int"
    assert "0 keeps it for ever" in KEY_HELP["poll_draft_days"]
    assert reachable_on_the_panel("poll_draft_days")
    await store.set(7, "poll_draft_days", 0)
    assert store.get(7, "poll_draft_days") == 0
    await store.set(7, "poll_draft_days", POLL_DRAFT_MAX_DAYS)
    with pytest.raises(SettingError):
        coerce_value("poll_draft_days", POLL_DRAFT_MAX_DAYS + 1)
    with pytest.raises(SettingError):
        coerce_value("poll_draft_days", -1)
    with pytest.raises(SettingError):
        coerce_value("poll_draft_days", "14")
    assert parse_value("poll_draft_days", "30") == 30


async def test_a_logs_button_opens_on_ten_lines_and_the_bounds_are_the_embeds_room(store):
    """The step Show more adds is the same number, so one setting decides both."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "logs_count") == LOGS_DEFAULT == 10
    assert KEY_TYPES["logs_count"] == "int"
    assert f"from {LOGS_MIN} to {LOGS_MAX}" in KEY_HELP["logs_count"]
    assert "Show more" in KEY_HELP["logs_count"]
    assert reachable_on_the_panel("logs_count")
    await store.set(7, "logs_count", LOGS_MAX)
    assert store.get(7, "logs_count") == LOGS_MAX
    await store.set(7, "logs_count", LOGS_MIN)
    with pytest.raises(SettingError):
        coerce_value("logs_count", LOGS_MAX + 1)
    with pytest.raises(SettingError):
        coerce_value("logs_count", LOGS_MIN - 1)
    with pytest.raises(SettingError):
        coerce_value("logs_count", "10")
    assert parse_value("logs_count", "25") == 25


async def test_a_logs_button_opens_on_everything_until_a_lead_says_otherwise(store):
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "logs_important_only") is False
    assert KEY_TYPES["logs_important_only"] == "bool"
    assert "Show everything" in KEY_HELP["logs_important_only"]
    assert reachable_on_the_panel("logs_important_only")
    await store.set(7, "logs_important_only", True)
    assert store.get(7, "logs_important_only") is True
    with pytest.raises(SettingError):
        coerce_value("logs_important_only", "true")
    assert parse_value("logs_important_only", "true") is True


async def test_the_panel_keeps_a_members_own_requests_to_themselves_until_a_lead_says_otherwise(
    store,
):
    """Owner, 2026-09-03: viewing requests on the panel is staff-only, and it is a key."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "request_panel_own_list") is False
    assert KEY_TYPES["request_panel_own_list"] == "bool"
    assert "staff always see them" in KEY_HELP["request_panel_own_list"]
    assert reachable_on_the_panel("request_panel_own_list")
    await store.set(7, "request_panel_own_list", True)
    assert store.get(7, "request_panel_own_list") is True
    assert coerce_value("request_panel_own_list", True) is True
    with pytest.raises(SettingError):
        coerce_value("request_panel_own_list", "true")
    assert parse_value("request_panel_own_list", "true") is True


async def test_the_birthday_panel_stays_up_ten_minutes_by_default(store):
    """Ten, not fifteen: the footer needs Discord's 15-minute interaction window still open."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "birthday_panel_minutes") == 10
    assert "15" in KEY_HELP["birthday_panel_minutes"]
    assert KEY_TYPES["birthday_panel_minutes"] == "int"
    assert reachable_on_the_panel("birthday_panel_minutes")
    await store.set(7, "birthday_panel_minutes", 30)
    assert store.get(7, "birthday_panel_minutes") == 30
    with pytest.raises(SettingError):
        coerce_value("birthday_panel_minutes", -1)
    assert parse_value("birthday_panel_minutes", "45") == 45


async def test_the_birthday_panel_keeps_todays_behaviour_until_a_lead_says_otherwise(store):
    """F-B1, owner 2026-09-03: the coming-up list and the lookup stay open to members."""
    from black_bloc.settings_panel import reachable_on_the_panel

    for key in ("birthday_panel_next_for_members", "birthday_panel_lookup"):
        assert store.get(7, key) is True
        assert KEY_TYPES[key] == "bool"
        assert reachable_on_the_panel(key)
        assert KEY_HELP.get(key)
        with pytest.raises(SettingError):
            coerce_value(key, "true")
        await store.set(7, key, False)
        assert store.get(7, key) is False
        assert parse_value(key, "true") is True
    assert "staff always see them" in KEY_HELP["birthday_panel_next_for_members"]
    assert "staff always can" in KEY_HELP["birthday_panel_lookup"]


async def test_the_status_channel_is_blank_so_one_channel_carries_both_kinds_of_line(store):
    assert store.get(7, "request_status_channel_id") is None


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
    assert coerce_value("request_notify_channel_id", 12) == 12
    assert coerce_value("request_status_channel_id", 13) == 13
    for key, bad in (
        ("request_mode", "shadow"),
        ("request_who_can_file", "mods"),
        ("request_status_channel_id", "13"),
        ("request_notify_channel_id", "12"),
        ("request_dm_on_decision", 1),
    ):
        with pytest.raises(SettingError):
            coerce_value(key, bad)


async def test_every_memory_decision_is_a_key_the_dashboard_and_the_bot_both_reach(store):
    """Phase 17 D1-D5 plus the three the Fable session settled: none of them is a constant."""
    for key in (
        "chat_memory_mode",
        "chat_memory_consent",
        "chat_memory_retention_days",
        "chat_memory_dm_scope",
        "chat_memory_staff_view",
        "chat_memory_notes_max",
        "chat_memory_threads_max",
        "chat_memory_model",
    ):
        assert key in KEY_TYPES and KEY_HELP.get(key)
    assert store.get(7, "chat_memory_mode") == "off"
    assert store.get(7, "chat_memory_consent") == "optout"
    assert store.get(7, "chat_memory_retention_days") == 180
    assert store.get(7, "chat_memory_dm_scope") == "separate"
    assert store.get(7, "chat_memory_staff_view") == "counts"
    assert store.get(7, "chat_memory_notes_max") == 6
    assert store.get(7, "chat_memory_threads_max") == 5
    assert store.get(7, "chat_memory_model") == ""


def test_the_memory_choices_refuse_anything_else():
    assert coerce_value("chat_memory_mode", "on") == "on"
    assert coerce_value("chat_memory_consent", "optin") == "optin"
    assert coerce_value("chat_memory_dm_scope", "shared") == "shared"
    assert coerce_value("chat_memory_staff_view", "full") == "full"
    assert coerce_value("chat_memory_retention_days", 0) == 0
    assert coerce_value("chat_memory_notes_max", 20) == 20
    for key, bad in (
        ("chat_memory_mode", "shadow"),
        ("chat_memory_consent", "always"),
        ("chat_memory_dm_scope", "both"),
        ("chat_memory_staff_view", "some"),
        ("chat_memory_retention_days", "180"),
        ("chat_memory_notes_max", 21),
        ("chat_memory_threads_max", 21),
        ("chat_memory_model", ""),
    ):
        with pytest.raises(SettingError):
            coerce_value(key, bad)


def test_the_memory_switch_is_a_part_of_chat_rather_than_a_feature_of_its_own():
    """`api/status.py` would otherwise offer a `chat_memory` feature with no page behind it."""
    assert "chat_memory_mode" in KEY_TYPES
    assert "chat_memory_mode" not in mode_keys()

async def test_every_raid_train_decision_is_a_key_both_the_dashboard_and_the_bot_reach(store):
    """Phase 18 D1-D14: not one of them is a constant in the cog."""
    for key in (
        "raidtrain_mode",
        "raidtrain_organizer_role_id",
        "raidtrain_channel_id",
        "raidtrain_ping_role_id",
        "raidtrain_slot_minutes",
        "raidtrain_reminder_minutes",
        "raidtrain_poll_minutes",
        "raidtrain_require_link",
        "raidtrain_thread",
        "raidtrain_live_posts",
        "raidtrain_max_slots_per_member",
        "raidtrain_scheduled_event",
        RAIDTRAIN_SCHEDULED_NAME_KEY,
        "raidtrain_log_level",
    ):
        assert key in KEY_TYPES and KEY_HELP.get(key)
    assert store.get(7, "raidtrain_mode") == "off"
    assert store.get(7, "raidtrain_slot_minutes") == 60
    assert store.get(7, "raidtrain_reminder_minutes") == 30
    assert store.get(7, "raidtrain_poll_minutes") == 5
    assert store.get(7, "raidtrain_require_link") is True
    assert store.get(7, "raidtrain_thread") is True
    assert store.get(7, "raidtrain_live_posts") is True
    assert store.get(7, "raidtrain_max_slots_per_member") == 1
    assert store.get(7, "raidtrain_scheduled_event") is False
    assert store.get(7, RAIDTRAIN_SCHEDULED_NAME_KEY) == RAIDTRAIN_SCHEDULED_NAME_TEMPLATE
    assert store.get(7, "raidtrain_channel_id") is None
    assert store.get(7, "raidtrain_organizer_role_id") is None


def test_a_raid_trains_calendar_name_is_the_plain_title_until_staff_change_it():
    """Owner 2026-09-10: "Leave raid train as it is now but let it be changeable"."""
    assert RAIDTRAIN_SCHEDULED_NAME_TEMPLATE == "{title}"
    assert KEY_TYPES[RAIDTRAIN_SCHEDULED_NAME_KEY] == "text"
    assert namespace_of(RAIDTRAIN_SCHEDULED_NAME_KEY) == "raidtrain"


def test_the_raid_train_calendar_name_is_held_to_the_same_rules_as_an_events():
    assert coerce_value(RAIDTRAIN_SCHEDULED_NAME_KEY, "  BaF: {title}  ") == "BaF: {title}"
    assert (
        coerce_value(RAIDTRAIN_SCHEDULED_NAME_KEY, EVENTS_SCHEDULED_NAME_TEMPLATE)
        == EVENTS_SCHEDULED_NAME_TEMPLATE
    )

    with pytest.raises(SettingError) as caught:
        coerce_value(RAIDTRAIN_SCHEDULED_NAME_KEY, "Feat. BaF")

    assert "{title}" in str(caught.value) and "Nothing was changed" in str(caught.value)

    with pytest.raises(SettingError) as caught:
        coerce_value(RAIDTRAIN_SCHEDULED_NAME_KEY, "{title} on {date}")

    assert "{date}" in str(caught.value) and "{title}" in str(caught.value)


def test_the_raid_train_mode_is_read_as_a_feature_switch_on_the_health_page():
    assert "raidtrain_mode" in mode_keys()


def test_the_raid_train_numbers_refuse_a_figure_that_would_break_the_sweep():
    assert coerce_value("raidtrain_slot_minutes", 15) == 15
    assert coerce_value("raidtrain_max_slots_per_member", 0) == 0
    for key, bad, said in (
        ("raidtrain_slot_minutes", 14, "start a stream"),
        ("raidtrain_slot_minutes", 721, "half a day"),
        ("raidtrain_reminder_minutes", 4, "enough notice"),
        ("raidtrain_reminder_minutes", 1441, "day before"),
        ("raidtrain_poll_minutes", 0, "once every"),
        ("raidtrain_poll_minutes", 61, "miss its own reminder"),
        ("raidtrain_max_slots_per_member", 25, "set it to 0"),
    ):
        with pytest.raises(SettingError) as caught:
            coerce_value(key, bad)
        assert said in str(caught.value)


def test_the_raid_train_switches_only_take_the_words_they_document():
    assert coerce_value("raidtrain_mode", "shadow") == "shadow"
    assert coerce_value("raidtrain_require_link", False) is False
    for key, bad in (
        ("raidtrain_mode", "sometimes"),
        ("raidtrain_thread", "yes"),
        ("raidtrain_live_posts", 1),
        ("raidtrain_scheduled_event", "on"),
        ("raidtrain_channel_id", "12"),
        ("raidtrain_organizer_role_id", "12"),
    ):
        with pytest.raises(SettingError):
            coerce_value(key, bad)

async def test_applications_ship_off_with_a_thirty_day_wait_and_decision_dms_on(store):
    assert store.get(1, "applications_mode") == "off"
    assert store.get(1, "applications_retry_days") == 30
    assert store.get(1, "applications_dm_on_decision") is True
    assert store.get(1, "applications_channel_id") is None
    assert store.get(1, "applications_approver_role_id") is None
    assert store.get(1, "applications_ping_role_id") is None
    assert store.get(1, "applications_log_level") == "important"


async def test_the_application_keys_are_typed_and_the_mode_is_the_three_way_one(store):
    assert KEY_TYPES["applications_mode"] == "enum"
    assert KEY_TYPES["applications_channel_id"] == "channel"
    assert KEY_TYPES["applications_approver_role_id"] == "role"
    assert KEY_TYPES["applications_ping_role_id"] == "role"
    assert KEY_TYPES["applications_retry_days"] == "int"
    assert KEY_TYPES["applications_dm_on_decision"] == "bool"
    for name in ("off", "shadow", "on"):
        assert await store.set(1, "applications_mode", name) == name
    with pytest.raises(SettingError):
        await store.set(1, "applications_mode", "maybe")


async def test_the_roster_shows_people_who_left_until_a_lead_says_otherwise(store):
    assert KEY_TYPES["applications_roster_shows_left"] == "bool"
    assert store.get(1, "applications_roster_shows_left") is True
    assert "marked as gone" in KEY_HELP["applications_roster_shows_left"]
    assert await store.set(1, "applications_roster_shows_left", False) is False
    assert store.get(1, "applications_roster_shows_left") is False
    with pytest.raises(SettingError):
        await store.set(1, "applications_roster_shows_left", "maybe")


async def test_the_show_panel_goes_quiet_after_ten_minutes_unless_a_lead_changes_it(store):
    assert KEY_TYPES["applications_panel_minutes"] == "int"
    assert store.get(1, "applications_panel_minutes") == 10
    assert "15" in KEY_HELP["applications_panel_minutes"]
    assert await store.set(1, "applications_panel_minutes", 5) == 5


async def test_a_member_sees_their_own_applications_until_a_lead_says_otherwise(store):
    """Today's permission is the default (owner, 2026-09-03), and it is a key, not a constant."""
    assert KEY_TYPES["applications_panel_own_list"] == "bool"
    assert store.get(1, "applications_panel_own_list") is True
    assert "staff-only" in KEY_HELP["applications_panel_own_list"]
    assert await store.set(1, "applications_panel_own_list", False) is False
    assert store.get(1, "applications_panel_own_list") is False
    with pytest.raises(SettingError):
        await store.set(1, "applications_panel_own_list", "maybe")


async def test_the_applications_panel_help_names_the_command_that_opens_it(store):
    assert "/apply panel" in KEY_HELP["applications_panel_minutes"]
    assert "15-minute interaction window" in KEY_HELP["applications_panel_minutes"]


async def test_a_wait_longer_than_ten_years_is_refused_with_its_own_sentence(store):
    assert await store.set(1, "applications_retry_days", 0) == 0
    with pytest.raises(SettingError) as caught:
        await store.set(1, "applications_retry_days", 3651)
    assert "permanent no with extra steps" in str(caught.value)


async def test_the_event_panel_stays_up_ten_minutes_by_default(store):
    """Ten, not fifteen: the footer needs Discord's 15-minute interaction window still open."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "event_panel_minutes") == 10
    assert "15" in KEY_HELP["event_panel_minutes"]
    assert KEY_TYPES["event_panel_minutes"] == "int"
    assert reachable_on_the_panel("event_panel_minutes")
    assert namespace_of("event_panel_minutes") == "events"
    await store.set(7, "event_panel_minutes", 30)
    assert store.get(7, "event_panel_minutes") == 30
    with pytest.raises(SettingError):
        coerce_value("event_panel_minutes", -1)
    with pytest.raises(SettingError):
        coerce_value("event_panel_minutes", "15")
    assert parse_value("event_panel_minutes", "45") == 45


async def test_the_golive_panel_stays_up_ten_minutes_by_default(store):
    """Ten, not fifteen: the footer needs Discord's 15-minute interaction window still open."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "golive_panel_minutes") == 10
    assert "15" in KEY_HELP["golive_panel_minutes"]
    assert "/golive panel" in KEY_HELP["golive_panel_minutes"]
    assert KEY_TYPES["golive_panel_minutes"] == "int"
    assert reachable_on_the_panel("golive_panel_minutes")
    await store.set(7, "golive_panel_minutes", 30)
    assert store.get(7, "golive_panel_minutes") == 30
    with pytest.raises(SettingError):
        coerce_value("golive_panel_minutes", -1)
    with pytest.raises(SettingError):
        coerce_value("golive_panel_minutes", "15")
    assert parse_value("golive_panel_minutes", "45") == 45


async def test_the_eleven_golive_keys_the_site_owns_are_untouched(store):
    """The panel WRITES only golive_mode; the rest stay the Go-live page's to edit."""
    wanted = {
        "golive_mode": "shadow",
        "golive_channel_id": None,
        "golive_template": None,
        "golive_end_template": GOLIVE_END_TEMPLATE,
        "golive_live_role_id": None,
        "golive_require_role_id": None,
        "golive_ignore_role_id": None,
        "golive_cooldown_minutes": 60,
        "golive_ping_role_id": None,
        "golive_max_session_hours": 12,
        "golive_embed": True,
    }
    for key, value in wanted.items():
        assert key in KEY_TYPES, key
        assert KEY_HELP[key], key
        if value is not None:
            assert store.get(7, key) == value, key


async def test_the_event_panel_keeps_a_members_own_events_to_themselves_until_a_lead_says_so(
    store,
):
    """Mirrors request_panel_own_list: staff always see the open ones, members opt in."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "event_panel_own_list") is False
    assert KEY_TYPES["event_panel_own_list"] == "bool"
    assert "staff always" in KEY_HELP["event_panel_own_list"]
    assert reachable_on_the_panel("event_panel_own_list")
    assert namespace_of("event_panel_own_list") == "events"
    await store.set(7, "event_panel_own_list", True)
    assert store.get(7, "event_panel_own_list") is True
    assert coerce_value("event_panel_own_list", True) is True
    with pytest.raises(SettingError):
        coerce_value("event_panel_own_list", "true")


async def test_hiding_a_turned_off_features_command_is_on_by_default_and_both_doors_reach_it(
    store,
):
    """Owner, 2026-09-04: turning YouTube off on the portal should take `/youtube` away."""
    from black_bloc.settings_panel import reachable_on_the_panel
    from black_bloc.settings_store import HIDE_COMMANDS_WHEN_OFF

    assert store.get(7, HIDE_COMMANDS_WHEN_OFF) is True
    assert KEY_TYPES[HIDE_COMMANDS_WHEN_OFF] == "bool"
    assert reachable_on_the_panel(HIDE_COMMANDS_WHEN_OFF)
    assert "shadow does not" in KEY_HELP[HIDE_COMMANDS_WHEN_OFF]
    await store.set(7, HIDE_COMMANDS_WHEN_OFF, False)
    assert store.get(7, HIDE_COMMANDS_WHEN_OFF) is False
    assert coerce_value(HIDE_COMMANDS_WHEN_OFF, True) is True
    assert parse_value(HIDE_COMMANDS_WHEN_OFF, "false") is False
    with pytest.raises(SettingError):
        coerce_value(HIDE_COMMANDS_WHEN_OFF, "true")


async def test_the_modmail_panel_stays_up_ten_minutes_by_default(store):
    """Same reason as every other panel: 15 loses Discord's window and the gone-quiet footer."""
    from black_bloc.settings_panel import reachable_on_the_panel

    assert store.get(7, "modmail_panel_minutes") == 10
    assert "15" in KEY_HELP["modmail_panel_minutes"]
    assert KEY_TYPES["modmail_panel_minutes"] == "int"
    assert reachable_on_the_panel("modmail_panel_minutes")
    await store.set(7, "modmail_panel_minutes", 25)
    assert store.get(7, "modmail_panel_minutes") == 25
    assert parse_value("modmail_panel_minutes", "45") == 45
    with pytest.raises(SettingError):
        coerce_value("modmail_panel_minutes", -1)


async def test_the_reply_style_defaults_to_both_and_refuses_a_fourth_word(store):
    """Checklist 33: the Settings page and `/settings` ▸ **A setting group…** both reach it."""
    from black_bloc.settings_panel import reachable_on_the_panel
    from black_bloc.settings_store import MODMAIL_REPLY_STYLES

    assert MODMAIL_REPLY_STYLES == ("buttons", "typing", "both")
    assert store.get(7, "modmail_reply_style") == "both"
    assert KEY_TYPES["modmail_reply_style"] == "enum"
    assert KEY_CHOICES["modmail_reply_style"] == MODMAIL_REPLY_STYLES
    assert reachable_on_the_panel("modmail_reply_style")
    for style in MODMAIL_REPLY_STYLES:
        await store.set(7, "modmail_reply_style", style)
        assert store.get(7, "modmail_reply_style") == style
    with pytest.raises(SettingError):
        coerce_value("modmail_reply_style", "shouting")


async def test_the_three_self_test_keys_are_core_keys_reachable_from_both_doors(store):
    """Checklist 33: every decision the self-test makes is a registry key, so the Settings
    page and `/settings` ▸ **A setting group…** ▸ **core** both reach it."""
    from black_bloc.settings_panel import reachable_on_the_panel
    from black_bloc.settings_store import (
        SELFTEST_CHANNEL_ID,
        SELFTEST_LOG_LEVEL,
        SELFTEST_ON_BOOT,
        SELFTEST_PURGE_MINUTES,
        namespace_of,
    )

    keys = (SELFTEST_ON_BOOT, SELFTEST_CHANNEL_ID, SELFTEST_PURGE_MINUTES, SELFTEST_LOG_LEVEL)
    for key in keys:
        assert namespace_of(key) == "core", key
        assert reachable_on_the_panel(key), key
        assert KEY_HELP.get(key), key
    assert KEY_TYPES[SELFTEST_ON_BOOT] == "bool"
    assert KEY_TYPES[SELFTEST_CHANNEL_ID] == "channel"
    assert KEY_TYPES[SELFTEST_PURGE_MINUTES] == "int"


async def test_the_self_test_runs_at_boot_posts_to_the_test_channel_and_purges_in_a_minute(store):
    """Owner 2026-09-05: 'after 5 minutes purge'; a minute since 2026-09-10 ('last 60s instead')."""
    from black_bloc.settings_store import (
        SELFTEST_CHANNEL_ID,
        SELFTEST_ON_BOOT,
        SELFTEST_PURGE_MINUTES,
    )

    assert store.get(7, SELFTEST_ON_BOOT) is True
    assert store.get(7, SELFTEST_PURGE_MINUTES) == 1
    assert store.get(7, SELFTEST_CHANNEL_ID) == store.settings.test_channel_id
    assert store.default(SELFTEST_CHANNEL_ID) == store.settings.test_channel_id

    await store.set(7, SELFTEST_PURGE_MINUTES, 60)
    assert store.get(7, SELFTEST_PURGE_MINUTES) == 60
    # Zero would delete the cards before anybody could look; a day is the ceiling.
    with pytest.raises(SettingError):
        coerce_value(SELFTEST_PURGE_MINUTES, 0)
    with pytest.raises(SettingError):
        coerce_value(SELFTEST_PURGE_MINUTES, 1441)
    assert parse_value(SELFTEST_PURGE_MINUTES, "15") == 15


async def test_the_boot_run_is_on_by_default_only_while_test_mode_is_on(tmp_path, monkeypatch):
    """Owner 2026-09-20: 'now that we're no longer in test mode, we don't need to have black
    bloc post every panel in logs. Let's leave that as a default when in test mode'."""
    from black_bloc.settings_store import SELFTEST_ON_BOOT

    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    db = Database(tmp_path / "boot.sqlite3")
    await db.connect()
    try:
        rehearsing = SettingsStore(
            db, load_settings(_env_file=None, test_mode=True, test_channel_id=TEST_CH)
        )
        live = SettingsStore(db, load_settings(_env_file=None, test_mode=False))
        await rehearsing.load()
        await live.load()

        assert rehearsing.default(SELFTEST_ON_BOOT) is True
        assert live.default(SELFTEST_ON_BOOT) is False
        assert rehearsing.get(7, SELFTEST_ON_BOOT) is True
        assert live.get(7, SELFTEST_ON_BOOT) is False

        # Either way it is one bool in group core, so staff can say otherwise from both doors.
        await live.set(7, SELFTEST_ON_BOOT, True)
        assert live.get(7, SELFTEST_ON_BOOT) is True
        await live.clear(7, SELFTEST_ON_BOOT)
        assert live.get(7, SELFTEST_ON_BOOT) is False
    finally:
        await db.close()


# `site/public/assets/labels.js` is what the Settings page prints under a key's name. The
# thirteen keys that had no line there were given one on 2026-09-05, so the list is EMPTY and
# the guard below is total: a registry key added without a sentence now fails by name.
NO_LABEL_YET = ()


def test_every_registry_key_the_site_shows_has_a_label():
    """The four `*_panel_minutes` keys the panel waves added sat unlabelled for two days.

    An unlabelled key is not a crash, which is why nobody notices: the Settings page just
    prints `request_panel_minutes` at somebody instead of saying what it does.
    """
    root = pathlib.Path(settings_store.__file__).resolve().parent.parent
    text = (root / "site" / "public" / "assets" / "labels.js").read_text(encoding="utf-8")
    labelled = {found.group(1) for found in re.finditer(r"^\s{2}([a-z_0-9]+):", text, re.M)}
    assert sorted(set(KEY_TYPES) - labelled) == sorted(NO_LABEL_YET)


# The "When?" picker's five keys (`docs/info/when-picker-design.md` §5 and §5b). Every decision
# the draft panels make is here rather than in a cog, so the Settings page and `/settings
# set-value` both reach it — checklist 33.


async def test_every_when_picker_decision_is_a_key_both_doors_reach(store):
    for key in (
        DEFAULT_TIMEZONE_KEY,
        TIMEZONE_CHOICES_KEY,
        TIME_STEP_KEY,
        "events_default_minutes",
        EVENTS_SCHEDULED_NAME_KEY,
    ):
        assert key in KEY_TYPES and KEY_HELP.get(key)
    assert KEY_TYPES[DEFAULT_TIMEZONE_KEY] == "text"
    assert KEY_TYPES[TIMEZONE_CHOICES_KEY] == "text"
    assert KEY_TYPES[EVENTS_SCHEDULED_NAME_KEY] == "text"
    assert KEY_TYPES[TIME_STEP_KEY] == "int"
    assert KEY_TYPES["events_default_minutes"] == "int"
    assert store.get(7, DEFAULT_TIMEZONE_KEY) == "America/Phoenix"
    assert store.get(7, TIME_STEP_KEY) == TIME_STEP_MINUTES == 15
    assert store.get(7, "events_default_minutes") == EVENTS_DEFAULT_MINUTES == 120
    assert store.get(7, EVENTS_SCHEDULED_NAME_KEY) == "{title} Feat. BaF"


async def test_the_where_link_decision_is_a_key_both_doors_reach(store):
    """Checklist 33: the owner said append the link, so both doors can say otherwise."""
    key = "events_where_link_in_description"

    assert KEY_TYPES[key] == "bool" and KEY_HELP.get(key)
    assert namespace_of(key) == "events"
    assert store.get(7, key) is True
    assert parse_value(key, "off") is False


def test_the_three_timezone_keys_are_filed_under_events_and_make_no_group_of_their_own():
    for key in (DEFAULT_TIMEZONE_KEY, TIMEZONE_CHOICES_KEY, TIME_STEP_KEY):
        assert namespace_of(key) == "events"
    assert namespace_of("events_default_minutes") == "events"
    assert namespace_of(EVENTS_SCHEDULED_NAME_KEY) == "events"


async def test_the_zone_dropdown_ships_the_twenty_four_the_design_names(store):
    stored = store.get(7, TIMEZONE_CHOICES_KEY)
    names = [one.strip() for one in stored.split(",")]

    assert len(TIMEZONE_CHOICES) == TIMEZONE_CHOICES_MAX == 24
    assert names == list(TIMEZONE_CHOICES)
    assert names[0] == "America/Phoenix"
    assert all(is_known(one) for one in names)


def test_a_default_timezone_black_bloc_cannot_resolve_is_refused_by_name():
    assert coerce_value(DEFAULT_TIMEZONE_KEY, " Europe/London ") == "Europe/London"

    with pytest.raises(SettingError) as caught:
        coerce_value(DEFAULT_TIMEZONE_KEY, "Phoenix")

    assert "Phoenix" in str(caught.value)
    assert "Did you mean" in str(caught.value)
    assert "America/Phoenix" in str(caught.value)


def test_a_default_timezone_nothing_resembles_is_refused_without_a_guess():
    with pytest.raises(SettingError) as caught:
        coerce_value(DEFAULT_TIMEZONE_KEY, "Middle/Earth")

    assert "Middle/Earth" in str(caught.value)
    assert "Did you mean" not in str(caught.value)


def test_the_zone_list_drops_what_this_machine_cannot_resolve_and_keeps_the_rest():
    kept = coerce_value(TIMEZONE_CHOICES_KEY, "America/Phoenix, Middle/Earth, Europe/London")

    assert kept == "America/Phoenix, Europe/London"


def test_the_zone_list_is_cut_to_the_twenty_four_the_dropdown_can_hold():
    """The 25th slot belongs to `Other — type it…`, which is how the rest are reached."""
    typed = ", ".join([*TIMEZONE_CHOICES, "Europe/Lisbon", "Asia/Manila"])

    kept = coerce_value(TIMEZONE_CHOICES_KEY, typed).split(", ")

    assert len(kept) == TIMEZONE_CHOICES_MAX
    assert "Asia/Manila" not in kept


def test_the_zone_list_never_keeps_the_same_name_twice():
    kept = coerce_value(TIMEZONE_CHOICES_KEY, "Asia/Tokyo, Asia/Tokyo, Europe/London")

    assert kept == "Asia/Tokyo, Europe/London"


def test_a_zone_list_with_nothing_known_in_it_is_refused_rather_than_emptied():
    with pytest.raises(SettingError) as caught:
        coerce_value(TIMEZONE_CHOICES_KEY, "Middle/Earth, Narnia")

    assert "Region/City" in str(caught.value) and "24" in str(caught.value)


def test_the_calendar_name_must_say_which_event_it_is():
    assert coerce_value(EVENTS_SCHEDULED_NAME_KEY, "{title} Feat. BaF") == "{title} Feat. BaF"
    assert coerce_value(EVENTS_SCHEDULED_NAME_KEY, "  BaF: {title}  ") == "BaF: {title}"

    with pytest.raises(SettingError) as caught:
        coerce_value(EVENTS_SCHEDULED_NAME_KEY, "Feat. BaF")

    assert "{title}" in str(caught.value)


def test_a_calendar_name_with_a_placeholder_nothing_can_fill_is_refused_by_name():
    with pytest.raises(SettingError) as caught:
        coerce_value(EVENTS_SCHEDULED_NAME_KEY, "{title} on {date}")

    assert "{date}" in str(caught.value)
    assert "{title}" in str(caught.value)


def test_the_minute_step_and_the_default_length_refuse_a_figure_the_pickers_cannot_render():
    assert coerce_value(TIME_STEP_KEY, 5) == 5
    assert coerce_value(TIME_STEP_KEY, 60) == 60
    assert coerce_value("events_default_minutes", 30) == 30
    for key, bad, said in (
        (TIME_STEP_KEY, 4, "twelve options"),
        (TIME_STEP_KEY, 61, "one option"),
        ("events_default_minutes", 4, "over before"),
        ("events_default_minutes", 10081, "a week"),
    ):
        with pytest.raises(SettingError) as caught:
            coerce_value(key, bad)
        assert said in str(caught.value), key


async def test_a_lead_can_change_all_five_through_the_store_the_settings_page_writes_to(store):
    await store.set(7, DEFAULT_TIMEZONE_KEY, "Europe/London")
    await store.set(7, TIMEZONE_CHOICES_KEY, "Europe/London, Asia/Tokyo")
    await store.set(7, TIME_STEP_KEY, parse_value(TIME_STEP_KEY, "30"))
    await store.set(7, "events_default_minutes", parse_value("events_default_minutes", "90"))
    await store.set(7, EVENTS_SCHEDULED_NAME_KEY, "{title} — Black in a Flash")

    assert store.get(7, DEFAULT_TIMEZONE_KEY) == "Europe/London"
    assert store.get(7, TIMEZONE_CHOICES_KEY) == "Europe/London, Asia/Tokyo"
    assert store.get(7, TIME_STEP_KEY) == 30
    assert store.get(7, "events_default_minutes") == 90
    assert store.get(7, EVENTS_SCHEDULED_NAME_KEY) == "{title} — Black in a Flash"


async def test_the_two_shadow_keys_are_typed_explained_and_defaulted(store):
    """Checklist 33: both reach the Settings page and the /settings panel from the registry."""
    for key in ("poll_pin", "poll_shadow_note"):
        assert key in KEY_TYPES and KEY_HELP.get(key)
    assert KEY_TYPES["poll_pin"] == "bool" and KEY_TYPES["poll_shadow_note"] == "text"
    assert store.get(7, "poll_pin") is True
    assert store.get(7, "poll_shadow_note") == settings_store.POLL_SHADOW_NOTE
    assert "{channel}" in store.get(7, "poll_shadow_note")


def test_the_poll_mode_help_names_all_three_words_it_takes():
    said = KEY_HELP["poll_mode"]

    assert all(word in said for word in ("off", "shadow", "on"))
    assert KEY_CHOICES["poll_mode"] == ("off", "shadow", "on")


def test_the_front_door_mode_takes_all_three_words_and_its_help_names_them():
    said = KEY_HELP[settings_store.FRONTDOOR_MODE]

    assert KEY_CHOICES[settings_store.FRONTDOOR_MODE] == ("off", "shadow", "on")
    assert settings_store.FRONTDOOR_MODES == ("off", "shadow", "on")
    assert all(word in said for word in ("off", "shadow", "on"))
    assert "shadow_channel_id" in said


async def test_the_front_door_still_ships_on_and_stays_in_the_modmail_group(store):
    """A third mode is a wider choice, never a new default and never a 26th group."""
    assert store.get(7, settings_store.FRONTDOOR_MODE) == "on"
    assert settings_store.FRONTDOOR_MODE_DEFAULT == "on"
    assert namespace_of(settings_store.FRONTDOOR_MODE) == "modmail"

    await store.set(7, settings_store.FRONTDOOR_MODE, "shadow")

    assert store.get(7, settings_store.FRONTDOOR_MODE) == "shadow"


async def test_the_rehearsal_home_is_a_core_key_reachable_from_both_doors(store):
    """Checklist 33, and the 25-group cap: `shadow_` would have been a group of its own."""
    for key in (settings_store.SHADOW_CHANNEL, settings_store.REHEARSAL_NOTE):
        assert key in KEY_TYPES and KEY_HELP.get(key)
        assert key in settings_store.CORE_KEYS
        assert namespace_of(key) == "core"
    assert KEY_TYPES[settings_store.SHADOW_CHANNEL] == "channel"
    assert KEY_TYPES[settings_store.REHEARSAL_NOTE] == "text"


async def test_the_rehearsal_home_ships_blank_and_the_note_ships_written(store):
    assert store.get(7, settings_store.SHADOW_CHANNEL) is None
    assert store.get(7, settings_store.REHEARSAL_NOTE) == settings_store.REHEARSAL_NOTE_DEFAULT
    assert "{channel}" in store.get(7, settings_store.REHEARSAL_NOTE)


async def test_the_rehearsal_home_help_says_it_widens_test_mode(store):
    said = KEY_HELP[settings_store.SHADOW_CHANNEL]

    assert "test mode" in said and "one channel" in said


async def test_the_three_boot_status_keys_are_core_and_reachable_from_both_doors(store):
    """Checklist 33, and the 25-group cap: `boot_` and `shutdown_` would each be a group."""
    for key in (
        settings_store.BOOT_STATUS_MODE,
        settings_store.BOOT_STATUS_TEXT_KEY,
        settings_store.SHUTDOWN_STATUS_TEXT_KEY,
    ):
        assert key in KEY_TYPES and KEY_HELP.get(key)
        assert key in settings_store.CORE_KEYS
        assert namespace_of(key) == "core"
    assert KEY_TYPES[settings_store.BOOT_STATUS_MODE] == "enum"
    assert KEY_CHOICES[settings_store.BOOT_STATUS_MODE] == ("off", "on")
    assert KEY_TYPES[settings_store.BOOT_STATUS_TEXT_KEY] == "text"
    assert KEY_TYPES[settings_store.SHUTDOWN_STATUS_TEXT_KEY] == "text"


async def test_the_boot_status_ships_on_with_both_sentences_written(store):
    assert store.get(7, settings_store.BOOT_STATUS_MODE) == "on"
    assert store.get(7, settings_store.BOOT_STATUS_TEXT_KEY) == settings_store.BOOT_STATUS_TEXT
    assert (
        store.get(7, settings_store.SHUTDOWN_STATUS_TEXT_KEY)
        == settings_store.SHUTDOWN_STATUS_TEXT
    )
    assert len(settings_store.CORE_KEYS) == 24


async def test_stored_values_finds_every_guild_that_set_a_key(store):
    assert store.stored_values(settings_store.SHADOW_CHANNEL) == {}

    await store.set(7, settings_store.SHADOW_CHANNEL, 4242)
    await store.set(8, settings_store.SHADOW_CHANNEL, 99)

    assert store.stored_values(settings_store.SHADOW_CHANNEL) == {7: 4242, 8: 99}

    await store.clear(7, settings_store.SHADOW_CHANNEL)
    assert store.stored_values(settings_store.SHADOW_CHANNEL) == {8: 99}


async def test_stored_values_refuses_a_key_that_is_not_a_setting(store):
    with pytest.raises(settings_store.SettingError):
        store.stored_values("never_heard_of_it")


def test_the_moved_line_is_a_text_key_in_the_events_namespace_with_a_default():
    """§H: the words the old room hears are a setting, not a constant only the code knows."""
    assert KEY_TYPES[EVENTS_MOVED_LINE_KEY] == "text"
    assert namespace_of(EVENTS_MOVED_LINE_KEY) == "events"
    assert "{post}" in EVENTS_MOVED_LINE
    assert "{post}" in KEY_HELP[EVENTS_MOVED_LINE_KEY]


def test_the_moved_line_takes_post_and_refuses_any_other_placeholder():
    assert coerce_value(EVENTS_MOVED_LINE_KEY, "  Over in {post} now.  ") == "Over in {post} now."
    assert coerce_value(EVENTS_MOVED_LINE_KEY, "This room is closing.") == "This room is closing."

    with pytest.raises(SettingError) as caught:
        coerce_value(EVENTS_MOVED_LINE_KEY, "Off to {nowhere} we go.")

    assert "{nowhere}" in str(caught.value) and "{post}" in str(caught.value)


# --- the live card's top line (end-wording-design §C2) -----------------------------------------


def test_the_live_author_is_a_golive_text_key_with_help_and_the_words_the_card_reads_today():
    assert KEY_TYPES[GOLIVE_LIVE_AUTHOR_KEY] == "text"
    assert namespace_of(GOLIVE_LIVE_AUTHOR_KEY) == "golive"
    assert "{name}" in KEY_HELP[GOLIVE_LIVE_AUTHOR_KEY]
    assert "{platform}" in KEY_HELP[GOLIVE_LIVE_AUTHOR_KEY]
    assert "{duration}" not in KEY_HELP[GOLIVE_LIVE_AUTHOR_KEY]


async def test_the_live_author_ships_the_line_the_card_already_drew(store):
    assert store.get(7, GOLIVE_LIVE_AUTHOR_KEY) == GOLIVE_LIVE_AUTHOR
    assert GOLIVE_LIVE_AUTHOR == "{name} is now live on {platform}!"


def test_the_live_author_takes_name_and_platform_and_refuses_duration():
    assert coerce_value(GOLIVE_LIVE_AUTHOR_KEY, "  {name} on {platform}  ") == (
        "{name} on {platform}"
    )

    with pytest.raises(SettingError) as caught:
        coerce_value(GOLIVE_LIVE_AUTHOR_KEY, "{name} has streamed {duration}")

    assert "{duration}" in str(caught.value) and "{platform}" in str(caught.value)


def test_the_live_author_may_be_left_blank_so_the_card_keeps_its_own_line():
    assert coerce_value(GOLIVE_LIVE_AUTHOR_KEY, "") == ""
    assert coerce_value(GOLIVE_LIVE_AUTHOR_KEY, GOLIVE_LIVE_AUTHOR) == GOLIVE_LIVE_AUTHOR


# --- co-streaming: the switch and the two wordings (costream-design §B) ------------------------


def test_the_three_co_stream_keys_sit_in_the_golive_namespace_with_help_and_a_default():
    for key in (
        GOLIVE_COSTREAM_MODE_KEY,
        GOLIVE_COSTREAM_TEMPLATE_KEY,
        GOLIVE_COSTREAM_AUTHOR_KEY,
    ):
        assert namespace_of(key) == "golive" and KEY_HELP[key]
    assert KEY_TYPES[GOLIVE_COSTREAM_MODE_KEY] == "enum"
    assert KEY_TYPES[GOLIVE_COSTREAM_TEMPLATE_KEY] == "text"
    assert KEY_TYPES[GOLIVE_COSTREAM_AUTHOR_KEY] == "text"
    assert KEY_CHOICES[GOLIVE_COSTREAM_MODE_KEY] == ("off", "on")


async def test_co_streaming_ships_on_and_the_owner_can_turn_it_off_from_either_door(store):
    assert store.get(7, GOLIVE_COSTREAM_MODE_KEY) == "on"
    assert store.get(7, GOLIVE_COSTREAM_TEMPLATE_KEY) == GOLIVE_COSTREAM_TEMPLATE
    assert store.get(7, GOLIVE_COSTREAM_AUTHOR_KEY) == GOLIVE_COSTREAM_AUTHOR

    await store.set(7, GOLIVE_COSTREAM_MODE_KEY, "off")

    assert store.get(7, GOLIVE_COSTREAM_MODE_KEY) == "off"
    with pytest.raises(SettingError):
        coerce_value(GOLIVE_COSTREAM_MODE_KEY, "shadow")


def test_both_co_stream_wordings_take_the_same_seven_placeholders_and_no_others():
    for key in (GOLIVE_COSTREAM_TEMPLATE_KEY, GOLIVE_COSTREAM_AUTHOR_KEY):
        assert coerce_value(key, "  {name} {game} {title} {url} ") == "{name} {game} {title} {url}"
        assert coerce_value(key, "{platform} {also_url} {also_platform}") == (
            "{platform} {also_url} {also_platform}"
        )

        with pytest.raises(SettingError) as caught:
            coerce_value(key, "and on {duration} too")

        assert "{duration}" in str(caught.value) and "{also_url}" in str(caught.value)


def test_the_shipped_co_stream_wordings_pass_their_own_validator():
    assert coerce_value(GOLIVE_COSTREAM_TEMPLATE_KEY, GOLIVE_COSTREAM_TEMPLATE)
    assert coerce_value(GOLIVE_COSTREAM_AUTHOR_KEY, GOLIVE_COSTREAM_AUTHOR)


def test_the_filed_line_is_a_text_key_in_the_request_namespace_with_the_owners_sentence():
    """Owner, 2026-09-20: no cryptic site — received, and a DM on every status change."""
    assert KEY_TYPES[REQUEST_FILED_KEY] == "text"
    assert namespace_of(REQUEST_FILED_KEY) == "request"
    assert "Request has been received" in REQUEST_FILED
    assert "the site" not in REQUEST_FILED
    assert "{request_id}" in REQUEST_FILED and "{request_id}" in KEY_HELP[REQUEST_FILED_KEY]


def test_the_filed_line_takes_request_id_and_refuses_any_other_placeholder():
    assert coerce_value(REQUEST_FILED_KEY, "  Got it, #{request_id}.  ") == "Got it, #{request_id}."
    assert coerce_value(REQUEST_FILED_KEY, "Got it.") == "Got it."

    with pytest.raises(SettingError) as caught:
        coerce_value(REQUEST_FILED_KEY, "Got it, {who}.")

    assert "{who}" in str(caught.value) and "{request_id}" in str(caught.value)


def test_whether_a_new_raid_train_also_makes_an_event_is_a_key_and_not_a_constant(store):
    """Checklist 33: the default is decided on the Settings page, never in the code."""
    key = settings_store.RAIDTRAIN_EVENT_DEFAULT_KEY
    assert key == "raidtrain_event_default"
    assert KEY_TYPES[key] == "bool"
    assert KEY_HELP[key]
    assert store.get(1, key) is False
    assert coerce_value(key, True) is True
    assert settings_store.namespace_of(key) == "raidtrain"


def test_whether_a_youtube_video_link_is_looked_up_is_a_key_that_ships_off(store):
    """Owner, 2026-09-21: "Let's build it but keep it off for now" — checklist 33."""
    key = settings_store.GOLIVE_AUTOLINK_VIDEO_KEY
    assert key == "golive_autolink_youtube_video"
    assert KEY_TYPES[key] == "bool"
    assert store.get(1, key) is False
    assert settings_store.GOLIVE_AUTOLINK_VIDEO_DEFAULT is False
    assert coerce_value(key, True) is True
    assert settings_store.namespace_of(key) == "golive"


def test_the_video_lookup_key_says_in_words_why_it_is_off():
    said = KEY_HELP[settings_store.GOLIVE_AUTOLINK_VIDEO_KEY]
    assert "Off by default" in said
    assert "reads YouTube's page" in said
    assert "not always the streamer's own" in said


# ⚠️ Owner, 2026-09-21 17:3x: "in the everything else section of golive there are duplicate
# settings it seems, also what each of the settings does isnt clear". The second half is this:
# every key the Go-live page draws must say in plain words what it does. The Settings page,
# `/settings` and the Go-live drawers all read KEY_HELP, so this one guard covers three doors.
GOLIVE_PAGE_NAMESPACES = ("golive", "pings", "youtube")
GOLIVE_PAGE_HELP_MIN_WORDS = 10


def golive_page_keys() -> list[str]:
    return sorted(
        key
        for key in KEY_TYPES
        if settings_store.namespace_of(key) in GOLIVE_PAGE_NAMESPACES
    )


def test_the_golive_page_still_draws_sixty_two_keys():
    """The number the placement fixture in site/mock/golive-join.test.mjs is written against.
    A key added to one of these namespaces has to be added there too, or it lands in the
    Everything else catch-all with nobody noticing."""
    assert len(golive_page_keys()) == 62


def test_every_golive_page_key_says_in_words_what_it_does():
    thin = {
        key: KEY_HELP.get(key, "")
        for key in golive_page_keys()
        if len(KEY_HELP.get(key, "").split()) < GOLIVE_PAGE_HELP_MIN_WORDS
    }
    assert thin == {}


def test_no_golive_page_help_line_is_just_the_key_name_again():
    lazy = [
        key
        for key in golive_page_keys()
        if KEY_HELP[key].strip().lower().rstrip(".") in {key, key.replace("_", " ")}
    ]
    assert lazy == []


def test_every_golive_page_choice_is_named_in_its_own_help():
    """An enum whose help does not name its own options is the row the owner could not read:
    the select shows `end / delete / leave` and nothing says what any of them do."""
    unsaid = {}
    for key in golive_page_keys():
        choices = KEY_CHOICES.get(key)
        if not choices:
            continue
        said = KEY_HELP[key].lower()
        missing = [one for one in choices if one.lower() not in said]
        if missing:
            unsaid[key] = missing
    assert unsaid == {}
