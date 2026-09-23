from collections import Counter

import pytest

from black_bloc.command_visibility import HIDDEN_WHEN_OFF
from black_bloc.config import load_settings
from black_bloc.logkinds import FEATURES, LEVELS
from black_bloc.settings_panel import (
    BACK,
    BACK_ON,
    CLEAR_LIST,
    CONTROLS,
    CORE_CHANNEL_KEYS,
    EXTRA_MODES,
    GROUP,
    HIDDEN_NONE,
    HIDE_OFF_LABEL,
    HIDE_ON_LABEL,
    HIDING_OFF,
    KEY_PICK,
    LOG_LEVELS,
    LOGS,
    MODMAIL_ANSWERING,
    MODMAIL_NOT_ANSWERING,
    NO_EDITOR,
    PANEL_MOVES,
    PANEL_TIMEOUT_FOOTER,
    PANEL_TITLE,
    REFRESH,
    RESET,
    ROLES_CHANNELS,
    RULES_ELSEWHERE,
    SELECT_LIMIT,
    SITE,
    TOGGLE,
    FeatureMode,
    back_on_options,
    bounds_line,
    confirm_lines,
    control_for,
    default_sentence,
    editable_options,
    editor_move,
    group_buttons,
    groups,
    has_editor,
    hidden_line,
    key_card_buttons,
    key_card_lines,
    keys_in,
    level_buttons,
    level_moves,
    list_is_too_long,
    log_level_options,
    looks_buttons,
    may_edit_core_keys,
    mode_lines,
    needs_confirm,
    needs_find,
    panel_minutes,
    panel_minutes_keys,
    panel_minutes_options,
    panels_commands_buttons,
    roles_channels_buttons,
    root_buttons,
    root_lines,
    site_page_url,
    stored_count,
    toggle_label,
)
from black_bloc.settings_store import HIDE_COMMANDS_WHEN_OFF, KEY_TYPES, SettingsStore
from black_bloc.storage.db import Database

GUILD = 7
TEST_CH = 111
GROUP_COUNT = 24


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


class FakeStore:
    """`get` and `default` are the only two the pure module ever asks for."""

    def __init__(self, values=None, defaults=None):
        self.values = dict(values or {})
        self.defaults = dict(defaults or {})

    def get(self, guild_id, key):
        if key in self.values:
            return self.values[key]
        return self.default(key)

    def default(self, key):
        return self.defaults.get(key)


class FakeGuild:
    def __init__(self, guild_id=GUILD):
        self.id = guild_id


class FakeBot:
    def __init__(self, store):
        self.store = store


def actions(moves):
    return [move.action for move in moves]


def test_every_panel_move_is_distinct_and_every_label_is_plain_text():
    assert len({move.action for move in PANEL_MOVES}) == len(PANEL_MOVES)
    for move in PANEL_MOVES:
        assert move.label == move.label.strip()
        assert not set(move.label) & set("*_`~|#")
    assert PANEL_TITLE and PANEL_TIMEOUT_FOOTER.endswith("run /settings again")


@pytest.mark.parametrize("key", sorted(KEY_TYPES))
def test_every_registry_key_resolves_to_exactly_one_control(key):
    """The §C type→control table is DATA, so a new key cannot arrive with no editor by accident."""
    kind = KEY_TYPES[key]
    assert kind in CONTROLS, f"{key} is a {kind!r}, which no control knows how to render"
    assert control_for(key) == CONTROLS[kind]
    assert has_editor(key) is (CONTROLS[kind] != NO_EDITOR)


def test_automod_rules_is_the_only_key_in_the_registry_with_no_editor():
    assert {key for key in KEY_TYPES if not has_editor(key)} == {"automod_rules"}


def test_the_mode_block_is_the_hide_table_plus_exactly_three_hand_added_rows():
    """Derived, so the mode block and the hide table can never drift apart. `rolemenu_mode`
    joined the hand-added three at the pings remake (§C6) — it stopped hiding its command."""
    from black_bloc.settings_panel import FEATURE_MODES

    assert len(FEATURE_MODES) == len(HIDDEN_WHEN_OFF) + len(EXTRA_MODES) == 19
    assert "rolemenu_mode" in {row.key for row in EXTRA_MODES}
    assert {row.key for row in FEATURE_MODES} == set(HIDDEN_WHEN_OFF) | {
        row.key for row in EXTRA_MODES
    }
    for row in FEATURE_MODES:
        assert isinstance(row, FeatureMode) and row.command and row.label


def test_the_mode_block_says_modmail_in_words_and_never_as_on_or_off():
    store = FakeStore({"modmail_enabled": True, "youtube_live_mode": "shadow"})
    lines = mode_lines(store, GUILD)
    said = "\n".join(lines)

    assert len(lines) == 19
    assert any(line.startswith("**The front door** —") and "`/ask`" in line for line in lines)
    assert f"**Modmail** — {MODMAIL_ANSWERING} · `/modmail` to change" in lines
    assert "**YouTube** — shadow · `/youtube` to change" in lines

    store.values["modmail_enabled"] = False
    assert MODMAIL_NOT_ANSWERING in "\n".join(mode_lines(store, GUILD))
    assert "**Modmail** — True" not in said


def test_every_key_lands_in_exactly_one_of_the_twenty_four_groups():
    found = groups()
    assert len(found) == GROUP_COUNT
    counted = Counter(key for group in found for key in keys_in(group))
    assert set(counted) == set(KEY_TYPES)
    assert set(counted.values()) == {1}


def test_no_group_is_the_singular_of_another_one():
    """Owner, 2026-09-20: "there are 2 events areas, event and events. find all and combine them."

    `event_panel_minutes` / `event_panel_own_list` named their prefix after the `/event`
    command, so `namespace_of` opened an `event` group of two beside the `events` group of
    37 — two Events sections on the Settings page and two entries in `/settings` ▸ **A
    setting group…**. Both are NAMESPACE_OVERRIDE'd onto `events`; this is what stops the
    next `*_panel_*` key doing it again."""
    found = groups()
    twins = [group for group in found if f"{group}s" in found]

    assert twins == [], (
        f"{twins} each have a plural group beside them, so the Settings page draws two "
        "sections for one feature and /settings offers two groups. Put the odd keys under "
        "the existing namespace with settings_store.NAMESPACE_OVERRIDE."
    )


def test_the_settings_groups_fit_the_select():
    """The cap that nearly cost `youtube` its whole Discord door (front-door deviation 3).

    `cogs/core.py:GroupPick` builds its select from `groups()[:SELECT_LIMIT]`, which is
    Discord's own hard limit — so group 26 is not refused, it is silently dropped, and every
    key in it becomes unreachable from Discord with nothing anywhere saying so. The front
    door was filed under `modmail` through NAMESPACE_OVERRIDE for exactly this reason, and
    so were the two Send to... keys. This is the guard the next namespace fails instead."""
    found = groups()

    assert len(found) <= SELECT_LIMIT, (
        f"{len(found)} settings groups and the select holds {SELECT_LIMIT}: "
        f"{sorted(found[SELECT_LIMIT:])} would be dropped off /settings > A setting group... "
        "with no refusal anywhere. File the new keys under an existing namespace with "
        "settings_store.NAMESPACE_OVERRIDE, as frontdoor_* and handoff_* are."
    )


def test_three_groups_are_over_the_cap_and_find_is_what_reaches_the_rest():
    """`events` joined them when meeting minutes filed its eleven keys there, and `golive` when
    spotlight filed its nine — the group select is at its 25-cap, so a `spotlight` namespace
    would have been dropped silently instead. `core` joined at `panel_expired_text`."""
    over = [group for group in groups() if needs_find(group)]
    assert over == ["chat", "core", "events", "golive", "modmail"]

    every = editable_options("chat")
    assert len(every.keys) == SELECT_LIMIT
    assert every.total == 70
    assert "25 of 70" in every.placeholder

    filtered = editable_options("chat", "memory")
    assert filtered.total == len(filtered.keys) < SELECT_LIMIT
    assert all("memory" in key for key in filtered.keys)
    assert "of" not in filtered.placeholder


@pytest.mark.parametrize("total,capped", [(24, False), (25, False), (26, True)])
def test_the_setting_picker_caps_at_twenty_five_and_says_so_only_when_it_had_to(
    monkeypatch, total, capped
):
    import black_bloc.settings_panel as panel

    monkeypatch.setattr(panel, "keys_in", lambda group: tuple(f"x_{n}" for n in range(total)))
    found = panel.editable_options("x")

    assert len(found.keys) == min(total, SELECT_LIMIT) and found.total == total
    assert (f"of {total}" in found.placeholder) is capped


def test_a_needle_matching_nothing_returns_an_empty_list_rather_than_everything():
    found = editable_options("chat", "zzzz")
    assert found.keys == () and found.total == 0


def test_the_root_says_what_is_hidden_and_says_hiding_off_as_a_different_sentence():
    """S4/S5/S6 — 'nothing is hidden' and 'hiding is switched off' mean different things."""
    on = FakeStore({HIDE_COMMANDS_WHEN_OFF: True})
    bot = FakeBot(on)

    assert HIDDEN_NONE in hidden_line(bot, GUILD, set())
    said = hidden_line(bot, GUILD, {"youtube", "poll"})
    assert "2 command(s) are hidden" in said and "`/poll`" in said and "`/youtube`" in said

    off = FakeBot(FakeStore({HIDE_COMMANDS_WHEN_OFF: False}))
    assert hidden_line(off, GUILD, set()) == HIDING_OFF
    assert hidden_line(off, GUILD, {"youtube"}) == HIDING_OFF


async def test_the_root_counts_what_this_server_has_moved_off_the_default(store):
    bot = FakeBot(store)
    total = len(KEY_TYPES)

    assert stored_count(store, GUILD) == 0
    lines = root_lines(bot, FakeGuild(), set())
    assert f"**0** of {total} settings" in "\n".join(lines)

    await store.set(GUILD, "youtube_live_mode", "on")
    assert stored_count(store, GUILD) == 1
    assert f"**1** of {total} settings" in "\n".join(root_lines(bot, FakeGuild(), set()))
    assert any("A setting group" in line for line in lines)


def test_the_root_renders_exactly_its_row_and_no_other_control():
    every = root_buttons(may_turn_back_on=True, may_edit_core=True, has_site=True)
    assert actions(every) == [
        BACK_ON,
        GROUP,
        ROLES_CHANNELS,
        "looks",
        "panels",
        LOGS,
        SITE,
        LOG_LEVELS,
        "selftest",
        REFRESH,
    ]

    bare = root_buttons(may_turn_back_on=False, may_edit_core=False, has_site=False)
    assert actions(bare) == [GROUP, "looks", "panels", LOGS, LOG_LEVELS, "selftest", REFRESH]
    assert BACK_ON not in actions(bare) and ROLES_CHANNELS not in actions(bare)


def test_row_two_never_grows_past_the_five_controls_discord_allows():
    every = root_buttons(may_turn_back_on=True, may_edit_core=True, has_site=True)
    rows = Counter(move.row for move in every)
    assert rows[2] == 5
    assert max(rows.values()) <= 5


@pytest.mark.parametrize(
    "hidden,expected",
    [(set(), 0), ({"youtube"}, 1), ({names[0] for names in HIDDEN_WHEN_OFF.values()}, 16)],
)
def test_turn_a_feature_back_on_lists_exactly_what_is_hidden_and_never_more(hidden, expected):
    values = {HIDE_COMMANDS_WHEN_OFF: True}
    for key, names in HIDDEN_WHEN_OFF.items():
        values[key] = "off" if names[0] in hidden else "on"
    bot = FakeBot(FakeStore(values))

    found = back_on_options(bot, GUILD)
    assert len(found) == expected
    assert {row.command for row in found} == hidden
    assert all(row.label.endswith("turn it on") for row in found)


def test_turn_a_feature_back_on_is_empty_while_hiding_itself_is_switched_off():
    values = {HIDE_COMMANDS_WHEN_OFF: False}
    values.update({key: "off" for key in HIDDEN_WHEN_OFF})
    assert back_on_options(FakeBot(FakeStore(values)), GUILD) == ()


@pytest.mark.parametrize("current", [*LEVELS, "nonsense"])
def test_a_log_level_card_offers_only_the_two_levels_it_is_not_on(current):
    found = level_moves(current)
    assert len(found) == 2 and current not in found
    assert set(found) < set(LEVELS)

    buttons = level_buttons(current)
    assert actions(buttons) == [f"level_set:{one}" for one in found] + [BACK]


def test_every_log_level_fits_one_select_and_shows_the_level_it_is_on():
    store = FakeStore(defaults={f"{feature}_log_level": "important" for feature in FEATURES})
    found = log_level_options(store, GUILD)

    assert len(found) == len(FEATURES) == 21 <= SELECT_LIMIT
    assert all(label.endswith("— important") for _, label in found)


def test_every_panel_minutes_key_fits_one_select_including_the_panels_own():
    found = panel_minutes_keys()
    assert "settings_panel_minutes" in found
    assert len(found) == 21 <= SELECT_LIMIT

    store = FakeStore(defaults=dict.fromkeys(found, 10))
    assert all(label.endswith("— 10 minute(s)") for _, label in panel_minutes_options(store, GUILD))


async def test_the_key_card_says_the_value_the_default_the_help_and_the_bounds(store):
    lines = key_card_lines(store, GUILD, "chat_cooldown_seconds")
    said = "\n".join(lines)

    assert "**chat_cooldown_seconds** — 20" in said
    assert "Black Bloc's own default is 20." in said
    assert "It takes a whole number from 5 to 600." in said
    assert RULES_ELSEWHERE not in said


def test_a_key_with_only_one_bound_says_only_that_one_and_an_unbounded_one_says_nothing():
    assert bounds_line("cost_hosting_usd").startswith("It takes a whole number no larger than")
    assert bounds_line("youtube_live_end_misses").startswith("It takes a whole number ")
    assert bounds_line("bot_bio") == ""


async def test_the_rule_book_card_carries_no_editor_at_all_and_says_where_it_is_edited(store):
    said = "\n".join(key_card_lines(store, GUILD, "automod_rules"))
    assert RULES_ELSEWHERE in said

    buttons = key_card_buttons(store, GUILD, "automod_rules", stored=False)
    assert actions(buttons) == [BACK]


async def test_put_the_default_back_is_absent_on_a_key_with_nothing_stored(store):
    unset = key_card_buttons(store, GUILD, "youtube_live_mode", stored=False)
    assert RESET not in actions(unset)

    set_here = key_card_buttons(store, GUILD, "youtube_live_mode", stored=True)
    assert actions(set_here) == ["edit:one_of", RESET, BACK]


async def test_a_bool_key_shows_one_button_that_says_which_way_it_will_go(store):
    on = key_card_buttons(store, GUILD, HIDE_COMMANDS_WHEN_OFF, stored=False)
    assert [move.label for move in on] == [HIDE_OFF_LABEL, "Back to the group"]

    await store.set(GUILD, HIDE_COMMANDS_WHEN_OFF, False)
    off = key_card_buttons(store, GUILD, HIDE_COMMANDS_WHEN_OFF, stored=True)
    assert [move.label for move in off][0] == HIDE_ON_LABEL
    assert HIDE_OFF_LABEL not in [move.label for move in off]


def test_a_toggle_with_no_written_pair_still_names_the_move_it_will_make():
    assert toggle_label("poll_creator_may_end", True) == "Turn poll_creator_may_end off"
    assert toggle_label("poll_creator_may_end", False) == "Turn poll_creator_may_end on"
    assert control_for("poll_creator_may_end") == TOGGLE


async def test_a_list_longer_than_a_picker_can_hold_draws_no_picker_but_keeps_clear_the_list(
    store,
):
    """S7 — a capped picker would silently drop the ids it could not show on the next submit."""
    key = "honeypot_exempt_role_ids"
    await store.set(GUILD, key, list(range(1000, 1026)))

    assert list_is_too_long(store, GUILD, key)
    said = "\n".join(key_card_lines(store, GUILD, key))
    assert "26 are stored" in said and "Settings page" in said
    assert actions(key_card_buttons(store, GUILD, key, stored=True)) == [CLEAR_LIST, RESET, BACK]

    await store.set(GUILD, key, list(range(1000, 1025)))
    assert not list_is_too_long(store, GUILD, key)
    assert actions(key_card_buttons(store, GUILD, key, stored=True)) == [
        "edit:role_list",
        CLEAR_LIST,
        RESET,
        BACK,
    ]


async def test_an_empty_list_key_offers_the_picker_but_nothing_to_clear(store):
    buttons = key_card_buttons(store, GUILD, "honeypot_exempt_role_ids", stored=False)
    assert actions(buttons) == ["edit:role_list", BACK]


async def test_putting_the_staff_channel_back_names_the_test_channel_and_asks_first(store):
    """F-S2 (a): its default is the test channel on every guild, which disarms two gates."""
    said = default_sentence(store, GUILD, "staff_channel_id")
    assert f"<#{TEST_CH}>" in said

    assert needs_confirm("staff_channel_id")
    warned = "\n".join(confirm_lines(store, GUILD, "staff_channel_id"))
    assert f"<#{TEST_CH}>" in warned and "who counts as staff" in warned

    assert not needs_confirm("log_channel_id")
    assert confirm_lines(store, GUILD, "log_channel_id") == []

    resetting = key_card_buttons(store, GUILD, "staff_channel_id", stored=True, confirming=True)
    assert actions(resetting) == ["confirm_reset", "cancel"]


def test_only_manage_server_reaches_the_core_channels_while_the_key_says_so():
    locked = FakeStore({"settings_core_keys_admin_only": True})
    assert not may_edit_core_keys(locked, GUILD, manage_guild=False)
    assert may_edit_core_keys(locked, GUILD, manage_guild=True)

    open_to_staff = FakeStore({"settings_core_keys_admin_only": False})
    assert may_edit_core_keys(open_to_staff, GUILD, manage_guild=False)


def test_the_core_channel_card_names_each_key_in_words_never_the_raw_key():
    found = roles_channels_buttons()
    assert len(found) == len(CORE_CHANNEL_KEYS) + 1
    assert actions(found)[-1] == BACK
    for key, move in zip(CORE_CHANNEL_KEYS, found, strict=False):
        assert move.action == f"core_key:{key}"
        assert key not in move.label and move.label


def test_re_apply_presence_is_absent_when_the_presence_cog_is_not_loaded():
    running = looks_buttons(presence_loaded=True)
    assert actions(running) == ["reapply", "bio", "status", "skin_tone", BACK]

    stopped = looks_buttons(presence_loaded=False)
    assert "reapply" not in actions(stopped)


def test_the_operator_log_toggle_is_absent_without_manage_server():
    store = FakeStore({HIDE_COMMANDS_WHEN_OFF: True, "operator_read_log": False})

    lead = panels_commands_buttons(store, GUILD, manage_guild=True)
    assert actions(lead) == [
        "hide_toggle",
        "panel_minutes_pick",
        "operator_toggle",
        "hosting",
        BACK,
    ]

    staff = panels_commands_buttons(store, GUILD, manage_guild=False)
    assert "operator_toggle" not in actions(staff)


def test_find_a_setting_is_offered_only_where_a_group_outgrew_the_picker():
    assert actions(group_buttons("chat")) == [KEY_PICK, "find", BACK]
    assert actions(group_buttons("core")) == [KEY_PICK, "find", BACK]
    assert actions(group_buttons("birthday")) == [KEY_PICK, BACK]


async def test_the_panel_reads_its_own_minutes_and_its_own_site_page(store):
    assert panel_minutes(store, GUILD) == 10
    await store.set(GUILD, "settings_panel_minutes", 20)
    assert panel_minutes(store, GUILD) == 20

    assert site_page_url("https://x.test") == "https://x.test/settings.html"
    assert site_page_url("") is None


def test_an_editor_move_is_a_select_for_a_picker_and_a_modal_for_typed_text():
    assert editor_move("automod_rules", None) is None
    assert editor_move("staff_channel_id", None).kind == "select"
    assert editor_move("bot_bio", "x").modal is True
    assert editor_move("birthday_color", "#4eefff").action == "edit:colour"


def test_the_self_test_card_draws_purge_now_only_while_there_is_something_to_delete():
    """P3 again: never a button that answers 'there was nothing to purge'."""
    from black_bloc.settings_panel import selftest_buttons

    idle = selftest_buttons(running=False, has_messages=False)
    assert actions(idle) == ["selftest_run", "selftest_logs", BACK]

    waiting = selftest_buttons(running=False, has_messages=True)
    assert actions(waiting) == ["selftest_run", "selftest_purge", "selftest_logs", BACK]

    # A run already going: **Run the self-test** is absent rather than offered and refused.
    going = selftest_buttons(running=True, has_messages=True)
    assert actions(going) == ["selftest_purge", "selftest_logs", BACK]
    assert max(Counter(move.row for move in waiting).values()) <= 5


async def test_the_self_test_card_says_what_it_will_do_before_it_has_ever_run(store):
    from black_bloc.settings_panel import SELFTEST_IS_RUNNING, selftest_lines

    said = "\n".join(selftest_lines(store, GUILD))

    assert "deleted again after 1 minute(s)" in said
    assert "under **Test**" in said
    assert "**At every boot** — yes" in said
    assert f"<#{TEST_CH}>" in said
    assert "has not run yet" in said
    assert SELFTEST_IS_RUNNING not in said

    await store.set(GUILD, "selftest_on_boot", False)
    assert "**At every boot** — no" in "\n".join(selftest_lines(store, GUILD))


async def test_the_self_test_card_names_the_last_run_and_every_failure(store):
    from black_bloc.settings_panel import selftest_lines

    last = {
        "started_at": "2026-09-05T14:03:00+00:00",
        "ok": 79,
        "failed": 2,
        "posted": 18,
        "purged_at": None,
    }
    failures = [
        {"name": "config.birthday_channel_id", "detail": "missing embed_links"},
        {"name": "read./api/costs", "detail": "TypeError: no"},
    ]

    said = "\n".join(
        selftest_lines(store, GUILD, last=last, failures=failures, waiting=18, running="")
    )

    assert "79 ok · 2 failed · 18 message(s) posted" in said
    assert "18 message(s) are still waiting to be deleted." in said
    assert "**config.birthday_channel_id** — missing embed_links" in said
    assert "**read./api/costs** — TypeError: no" in said

    purged = dict(last)
    purged["purged_at"] = "2026-09-05T14:09:00+00:00"
    after = "\n".join(selftest_lines(store, GUILD, last=purged))

    assert "were deleted 2026-09-05T14:09:00+00:00" in after
    assert "waiting to be deleted" not in after
