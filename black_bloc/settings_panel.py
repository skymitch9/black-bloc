from __future__ import annotations

from typing import Any, NamedTuple

from .command_visibility import HIDDEN_WHEN_OFF, hidden_names, hiding_is_on
from .logkinds import FEATURE_LABELS, FEATURES, LEVEL_DEFAULT, LEVELS, log_level_key
from .panels import capped_placeholder
from .panels import panel_minutes as _panel_minutes
from .panels import site_page_url as _site_page_url
from .settings_store import (
    HIDE_COMMANDS_WHEN_OFF,
    KEY_HELP,
    KEY_MAX,
    KEY_MIN,
    KEY_TYPES,
    SELFTEST_CHANNEL_ID,
    SELFTEST_ON_BOOT,
    SELFTEST_PURGE_MINUTES,
    SETTINGS_CORE_KEYS_ADMIN_ONLY,
    SETTINGS_PANEL_MINUTES,
    display_value,
    namespace_of,
)

PANEL_MINUTES_KEY = SETTINGS_PANEL_MINUTES
CORE_KEYS_ADMIN_ONLY_KEY = SETTINGS_CORE_KEYS_ADMIN_ONLY
SITE_FEATURE = "core"
PANEL_TITLE = "Black Bloc's settings for this server"
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /settings again"

SELECT_LIMIT = 25
LIST_EDIT_MAX = 25
ROW_LIMIT = 5

CHANNEL_PICKER = "channel_picker"
ROLE_PICKER = "role_picker"
CHANNEL_LIST = "channel_list"
ROLE_LIST = "role_list"
ONE_OF = "one_of"
ANY_OF = "any_of"
NUMBER_MODAL = "number"
TEXT_MODAL = "text"
COLOUR_MODAL = "colour"
TOGGLE = "toggle"
NO_EDITOR = ""

CONTROLS: dict[str, str] = {
    "channel": CHANNEL_PICKER,
    "role": ROLE_PICKER,
    "channels": CHANNEL_LIST,
    "roles": ROLE_LIST,
    "enum": ONE_OF,
    "enums": ANY_OF,
    "int": NUMBER_MODAL,
    "text": TEXT_MODAL,
    "color": COLOUR_MODAL,
    "bool": TOGGLE,
    "json": NO_EDITOR,
}
PICKERS = (CHANNEL_PICKER, ROLE_PICKER, CHANNEL_LIST, ROLE_LIST, ONE_OF, ANY_OF)
LIST_TYPES = ("channels", "roles", "enums")

BUTTON = "button"
SELECT = "select"
LINK = "link"

STAFF_CHANNEL_KEY = "staff_channel_id"
LOG_CHANNEL_KEY = "log_channel_id"
MODLOG_CHANNEL_KEY = "modlog_channel_id"
ROLE_MENU_CHANNEL_KEY = "role_menu_channel_id"
OPERATOR_READ_LOG_KEY = "operator_read_log"
HOSTING_KEY = "cost_hosting_usd"
BIO_KEY = "bot_bio"
STATUS_KEY = "status_prefix"
SKIN_TONE_KEY = "emoji_skin_tone"
RULES_KEY = "automod_rules"
MEMORY_MODE_KEY = "chat_memory_mode"
MODMAIL_ENABLED_KEY = "modmail_enabled"
ROLEMENU_MODE_KEY = "rolemenu_mode"

CORE_CHANNEL_KEYS: tuple[str, ...] = (
    STAFF_CHANNEL_KEY,
    LOG_CHANNEL_KEY,
    MODLOG_CHANNEL_KEY,
    ROLE_MENU_CHANNEL_KEY,
)
KEY_PURPOSE: dict[str, str] = {
    STAFF_CHANNEL_KEY: "Where staff talk — and who counts as staff",
    LOG_CHANNEL_KEY: "Where Black Bloc repeats what it did",
    MODLOG_CHANNEL_KEY: "Where moderation actions are written down",
    ROLE_MENU_CHANNEL_KEY: "Where the role menus are posted",
}

MODMAIL_ANSWERING = "answering DMs"
MODMAIL_NOT_ANSWERING = "not answering DMs"


class FeatureMode(NamedTuple):
    key: str
    command: str
    label: str
    words: tuple[str, ...] = ()


EXTRA_MODES: tuple[FeatureMode, ...] = (
    FeatureMode(MEMORY_MODE_KEY, "memory", "What Black Bloc remembers"),
    FeatureMode(
        MODMAIL_ENABLED_KEY, "modmail", "Modmail", (MODMAIL_ANSWERING, MODMAIL_NOT_ANSWERING)
    ),
    FeatureMode(ROLEMENU_MODE_KEY, "rolemenu", FEATURE_LABELS["rolemenu"]),
)


MODE_LABELS: dict[str, str] = {"frontdoor": "The front door"}


def _hidden_when_off_modes() -> tuple[FeatureMode, ...]:
    found: list[FeatureMode] = []
    for key, names in HIDDEN_WHEN_OFF.items():
        feature = key.removesuffix("_mode")
        label = MODE_LABELS.get(feature) or FEATURE_LABELS.get(feature, feature)
        found.append(FeatureMode(key, names[0], label))
    return tuple(found)


FEATURE_MODES: tuple[FeatureMode, ...] = (*_hidden_when_off_modes(), *EXTRA_MODES)

ROOT_INTRO = (
    "The settings no feature panel owns. All {total} of them are on the site, and every one is "
    "reachable here through **A setting group…**."
)
MODES_HEADER = "**What each feature is doing** — a mode is changed on its own panel:"
MODE_LINE = "**{label}** — {state} · `/{command}` to change"
HIDDEN_SOME = (
    "⚠️ **{count} command(s) are hidden right now** because their feature is off: {names}. "
    "**Turn a feature back on…** brings one back within about a minute."
)
HIDDEN_NONE = "Every command is showing."
HIDING_OFF = (
    "Hiding a command while its feature is off is switched off altogether, so every command is "
    "showing whatever the modes say."
)
STORED_COUNT = "**{stored}** of {total} settings are set away from Black Bloc's own default here."

PICK_A_GROUP = "A setting group…"
PICK_A_SETTING = "A setting…"
BACK_ON_PLACEHOLDER = "Turn a feature back on…"
BACK_ON_OPTION = "{label} — turn it on"
BACK_ON_VALUE = "on"
LOG_LEVEL_PLACEHOLDER = "Which log…"
LOG_LEVEL_OPTION = "{label} — {level}"
PANEL_MINUTES_PLACEHOLDER = "How long a panel stays open…"
PANEL_MINUTES_OPTION = "{key} — {minutes} minute(s)"
SKIN_TONE_PLACEHOLDER = "Skin tone…"

KEY_LINE = "**{key}** — {value}"
KEY_DEFAULT_LINE = "Black Bloc's own default is {value}."
KEY_BOUNDS_BOTH = "It takes a whole number from {low} to {high}."
KEY_BOUNDS_MAX = "It takes a whole number no larger than {high}."
KEY_BOUNDS_MIN = "It takes a whole number of at least {low}."
RULES_ELSEWHERE = (
    "The rule book is edited on `/automod` ▸ **A rule…**, so there is nothing to change here."
)
LIST_TOO_LONG = (
    "⚠️ **{count} are stored**, which is more than one Discord picker can edit at once, so the "
    "list is only editable on the Settings page. Nothing here can change it without silently "
    "dropping the ones the picker could not show — **Clear the list** still works."
)
PUT_BACK_MAKES = "**Put the default back** makes **{key}** {value}."

CONFIRM_TITLE = "Are you sure?"
CONFIRM_KEYS: tuple[str, ...] = (STAFF_CHANNEL_KEY,)
CONFIRM_STAFF_CHANNEL = (
    "Putting the default back points the staff channel at {channel}. That changes who counts as "
    "staff here, and both automod and the honeypot refuse to arm while the staff channel is the "
    "test channel — so two protections stop, quietly. Every other setting's reset is one press."
)

CORE_KEYS_ARE_FOR_A_LEAD = (
    "Re-pointing the staff channel, the log channel, the moderation log or the role-menu channel "
    "is for somebody with Manage Server, so **Roles & channels…** is not drawn for you. The rest "
    "of this panel works as it always did."
)
PRESENCE_NOT_RUNNING = (
    "Black Bloc's presence is not running in this process, so there is nothing to re-apply. The "
    "About Me and the status can still be written here and take effect when it starts again."
)
FIND_TITLE = "Find a setting"
FIND_LABEL = "Part of the setting's name"
NOTHING_MATCHES = (
    "Nothing in **{group}** has **{needle}** in its name, so the list is unchanged. Press **Find "
    "a setting…** again with fewer letters."
)
HIDE_CHANGED = (
    "**{state}** from now on. Discord's own command list catches up within about a minute, so "
    "nothing needs pressing twice."
)
HIDE_ON_STATE = "A feature's command is hidden while it is off"
HIDE_OFF_STATE = "Every command shows all the time"
PANEL_MINUTES_NEXT_TIME = "That applies the next time `/settings` is run, not to this panel."

SELFTEST_TITLE = "The self-test"
SELFTEST_INTRO = (
    "Black Bloc exercises itself against this server: every setting's channel and role, every "
    "read the dashboard makes, and every panel posted as a real card. The cards are deleted "
    "again after {minutes} minute(s); the lines stay on the dashboard's Logs page under **Test**."
)
SELFTEST_BOOT_ON = "**At every boot** — yes, so a deploy proves itself without anybody looking."
SELFTEST_BOOT_OFF = "**At every boot** — no, so it only runs when somebody asks."
SELFTEST_WHERE = "**Where the cards go** — {value}"
SELFTEST_NEVER = "It has not run yet in this server."
SELFTEST_LAST = (
    "**The last run** — started {started} · {ok} ok · {failed} failed · {posted} message(s) posted"
)
SELFTEST_PURGED = "Its messages were deleted {at}."
SELFTEST_WAITING = "{count} message(s) are still waiting to be deleted."
SELFTEST_FAILURE = "⚠️ **{name}** — {detail}"
SELFTEST_IS_RUNNING = "A run is going right now, so **Run the self-test** is not drawn."
SELFTEST_DONE = (
    "The self-test ran: **{ok} ok, {failed} failed**, {posted} message(s) posted. They are "
    "deleted again in {minutes} minute(s)."
)
SELFTEST_ALL_WELL = "Nothing failed."
SELFTEST_NOTHING_TO_PURGE = (
    "The self-test has nothing waiting to be deleted, so nothing was done. Its last run's cards "
    "have already gone."
)
SELFTEST_PURGE_DONE = "{count} self-test message(s) deleted."

HIDE_ON_LABEL = "Hide a feature's command while it is off"
HIDE_OFF_LABEL = "Leave every command showing"
OPERATOR_LOG_ON_LABEL = "Write a line for every operator-token read"
OPERATOR_LOG_OFF_LABEL = "Leave operator-token reads unlogged"
TURN_IT_ON = "Turn {key} on"
TURN_IT_OFF = "Turn {key} off"
TOGGLE_LABELS: dict[str, tuple[str, str]] = {
    HIDE_COMMANDS_WHEN_OFF: (HIDE_OFF_LABEL, HIDE_ON_LABEL),
    OPERATOR_READ_LOG_KEY: (OPERATOR_LOG_OFF_LABEL, OPERATOR_LOG_ON_LABEL),
}
EDITOR_LABELS: dict[str, str] = {
    CHANNEL_PICKER: "Pick a channel…",
    ROLE_PICKER: "Pick a role…",
    CHANNEL_LIST: "Pick the channels…",
    ROLE_LIST: "Pick the roles…",
    ONE_OF: "Pick one…",
    ANY_OF: "Pick any of them…",
    NUMBER_MODAL: "A number…",
    TEXT_MODAL: "The words…",
    COLOUR_MODAL: "The colour…",
}

BACK_ON = "back_on"
GROUP = "group"
KEY_PICK = "key_pick"
FIND = "find"
EDIT = "edit"
CLEAR_LIST = "clear_list"
RESET = "reset"
CONFIRM_RESET = "confirm_reset"
CANCEL = "cancel"
ROLES_CHANNELS = "roles_channels"
CORE_KEY = "core_key"
LOOKS = "looks"
REAPPLY = "reapply"
BIO = "bio"
STATUS = "status"
SKIN_TONE = "skin_tone"
PANELS = "panels"
HIDE_TOGGLE = "hide_toggle"
OPERATOR_TOGGLE = "operator_toggle"
HOSTING = "hosting"
PANEL_MINUTES_PICK = "panel_minutes_pick"
LOG_LEVELS = "log_levels"
LEVEL_PICK = "level_pick"
LEVEL_SET = "level_set"
LOGS = "logs"
SITE = "site"
REFRESH = "refresh"
BACK = "back"
SELFTEST = "selftest"
SELFTEST_RUN = "selftest_run"
SELFTEST_PURGE = "selftest_purge"
SELFTEST_LOGS = "selftest_logs"


class PanelMove(NamedTuple):
    action: str
    label: str
    style: str = "secondary"
    row: int = 0
    kind: str = BUTTON
    modal: bool = False


BACK_ON_MOVE = PanelMove(BACK_ON, BACK_ON_PLACEHOLDER, row=0, kind=SELECT)
GROUP_MOVE = PanelMove(GROUP, PICK_A_GROUP, row=1, kind=SELECT)
ROLES_CHANNELS_MOVE = PanelMove(ROLES_CHANNELS, "Roles & channels…", "primary", row=2)
LOOKS_MOVE = PanelMove(LOOKS, "How Black Bloc looks…", row=2)
PANELS_MOVE = PanelMove(PANELS, "Panels & commands…", row=2)
LOGS_MOVE = PanelMove(LOGS, "Logs", row=2)
SITE_MOVE = PanelMove(SITE, "Open on the site", "link", row=2, kind=LINK)
LOG_LEVELS_MOVE = PanelMove(LOG_LEVELS, "Log levels…", row=3)
SELFTEST_MOVE = PanelMove(SELFTEST, "Self-test…", row=3)
REFRESH_MOVE = PanelMove(REFRESH, "Refresh", row=3)

SELFTEST_RUN_MOVE = PanelMove(SELFTEST_RUN, "Run the self-test", "primary", row=0)
SELFTEST_PURGE_MOVE = PanelMove(SELFTEST_PURGE, "Purge now", "danger", row=0)
SELFTEST_LOGS_MOVE = PanelMove(SELFTEST_LOGS, "Logs", row=0)

BACK_MOVE = PanelMove(BACK, "Back", row=2)
KEY_BACK_LABEL = "Back to the group"

CORE_KEY_MOVES: tuple[PanelMove, ...] = tuple(
    PanelMove(f"{CORE_KEY}:{key}", KEY_PURPOSE[key], row=index, kind=SELECT)
    for index, key in enumerate(CORE_CHANNEL_KEYS)
)

REAPPLY_MOVE = PanelMove(REAPPLY, "Re-apply presence", "primary", row=0)
BIO_MOVE = PanelMove(BIO, "The About Me…", row=0, modal=True)
STATUS_MOVE = PanelMove(STATUS, "The status…", row=0, modal=True)
SKIN_TONE_MOVE = PanelMove(SKIN_TONE, SKIN_TONE_PLACEHOLDER, row=1, kind=SELECT)

HIDE_TOGGLE_MOVE = PanelMove(HIDE_TOGGLE, HIDE_ON_LABEL, "primary", row=0)
PANEL_MINUTES_MOVE = PanelMove(
    PANEL_MINUTES_PICK, PANEL_MINUTES_PLACEHOLDER, row=1, kind=SELECT
)
OPERATOR_TOGGLE_MOVE = PanelMove(OPERATOR_TOGGLE, OPERATOR_LOG_ON_LABEL, row=2)
HOSTING_MOVE = PanelMove(HOSTING, "The hosting bill…", row=2, modal=True)

LEVEL_PICK_MOVE = PanelMove(LEVEL_PICK, LOG_LEVEL_PLACEHOLDER, row=0, kind=SELECT)

KEY_PICK_MOVE = PanelMove(KEY_PICK, PICK_A_SETTING, row=0, kind=SELECT)
FIND_MOVE = PanelMove(FIND, "Find a setting…", row=1, modal=True)

CLEAR_LIST_MOVE = PanelMove(CLEAR_LIST, "Clear the list", row=1)
RESET_MOVE = PanelMove(RESET, "Put the default back", "danger", row=1)
CONFIRM_RESET_MOVE = PanelMove(CONFIRM_RESET, "Yes, put the default back", "danger", row=0)
CANCEL_MOVE = PanelMove(CANCEL, "Leave it as it is", "primary", row=0)

EDITOR_MOVES: tuple[PanelMove, ...] = tuple(
    PanelMove(
        f"{EDIT}:{editor}",
        label,
        "primary",
        row=0,
        kind=SELECT if editor in PICKERS else BUTTON,
        modal=editor not in PICKERS,
    )
    for editor, label in EDITOR_LABELS.items()
)
TOGGLE_MOVE = PanelMove(f"{EDIT}:{TOGGLE}", "", "primary", row=0)

PANEL_MOVES: tuple[PanelMove, ...] = (
    BACK_ON_MOVE,
    GROUP_MOVE,
    ROLES_CHANNELS_MOVE,
    LOOKS_MOVE,
    PANELS_MOVE,
    LOGS_MOVE,
    SITE_MOVE,
    LOG_LEVELS_MOVE,
    SELFTEST_MOVE,
    SELFTEST_RUN_MOVE,
    SELFTEST_PURGE_MOVE,
    SELFTEST_LOGS_MOVE,
    REFRESH_MOVE,
    *CORE_KEY_MOVES,
    REAPPLY_MOVE,
    BIO_MOVE,
    STATUS_MOVE,
    SKIN_TONE_MOVE,
    HIDE_TOGGLE_MOVE,
    PANEL_MINUTES_MOVE,
    OPERATOR_TOGGLE_MOVE,
    HOSTING_MOVE,
    LEVEL_PICK_MOVE,
    KEY_PICK_MOVE,
    FIND_MOVE,
    CLEAR_LIST_MOVE,
    RESET_MOVE,
    CONFIRM_RESET_MOVE,
    CANCEL_MOVE,
    BACK_MOVE,
    *EDITOR_MOVES,
    TOGGLE_MOVE,
)


def control_for(key: str) -> str:
    """The §C type→control table AS DATA; `automod_rules` is the one key with no editor."""
    return CONTROLS.get(KEY_TYPES.get(key, ""), NO_EDITOR)


def has_editor(key: str) -> bool:
    return control_for(key) != NO_EDITOR


def groups() -> tuple[str, ...]:
    return tuple(sorted({namespace_of(key) for key in KEY_TYPES}))


def keys_in(group: str) -> tuple[str, ...]:
    return tuple(key for key in KEY_TYPES if namespace_of(key) == group)


def reachable_on_the_panel(key: str) -> bool:
    """Checklist 33 — `A setting group…` opens this key and its card carries a real editor."""
    return key in keys_in(namespace_of(key)) and has_editor(key)


def matches(key: str, needle: str) -> bool:
    return needle.strip().lower() in key.lower()


class Options(NamedTuple):
    keys: tuple[str, ...]
    total: int
    placeholder: str


def editable_options(group: str, needle: str = "") -> Options:
    found = tuple(key for key in keys_in(group) if matches(key, needle))
    shown = found[:SELECT_LIMIT]
    return Options(
        shown, len(found), capped_placeholder(len(shown), len(found), pick=PICK_A_SETTING)
    )


def needs_find(group: str) -> bool:
    return len(keys_in(group)) > SELECT_LIMIT


def mode_state(store: Any, guild_id: int, row: FeatureMode) -> str:
    value = store.get(guild_id, row.key)
    if row.words:
        return row.words[0] if value else row.words[1]
    return str(value)


def mode_lines(store: Any, guild_id: int) -> list[str]:
    return [
        MODE_LINE.format(
            label=row.label, state=mode_state(store, guild_id, row), command=row.command
        )
        for row in FEATURE_MODES
    ]


def stored_count(store: Any, guild_id: int) -> int:
    return sum(1 for key in KEY_TYPES if store.get(guild_id, key) != store.default(key))


def hidden_line(bot: Any, guild_id: int, hidden: Any) -> str:
    """S4/S5/S6 — 'hiding is switched off' and 'nothing is hidden' are different sentences."""
    if not hiding_is_on(bot, guild_id):
        return HIDING_OFF
    if not hidden:
        return HIDDEN_NONE
    names = ", ".join(f"`/{name}`" for name in sorted(hidden))
    return HIDDEN_SOME.format(count=len(hidden), names=names)


def root_lines(bot: Any, guild: Any, hidden: Any) -> list[str]:
    store = bot.store
    guild_id = guild.id
    total = len(KEY_TYPES)
    return [
        ROOT_INTRO.format(total=total),
        "",
        MODES_HEADER,
        *mode_lines(store, guild_id),
        "",
        hidden_line(bot, guild_id, hidden),
        STORED_COUNT.format(stored=stored_count(store, guild_id), total=total),
    ]


def bounds_line(key: str) -> str:
    low, high = KEY_MIN.get(key), KEY_MAX.get(key)
    if low is not None and high is not None:
        return KEY_BOUNDS_BOTH.format(low=low, high=high)
    if high is not None:
        return KEY_BOUNDS_MAX.format(high=high)
    if low is not None:
        return KEY_BOUNDS_MIN.format(low=low)
    return ""


def list_is_too_long(store: Any, guild_id: int, key: str) -> bool:
    """S7 — a capped picker would drop the ids it could not show on the next submit."""
    if KEY_TYPES.get(key) not in ("channels", "roles"):
        return False
    return len(store.get(guild_id, key) or ()) > LIST_EDIT_MAX


def key_card_lines(store: Any, guild_id: int, key: str) -> list[str]:
    value = store.get(guild_id, key)
    lines = [
        KEY_LINE.format(key=key, value=display_value(key, value)),
        KEY_DEFAULT_LINE.format(value=display_value(key, store.default(key))),
    ]
    if KEY_HELP.get(key):
        lines.append(KEY_HELP[key])
    if bounds_line(key):
        lines.append(bounds_line(key))
    if not has_editor(key):
        lines.append(RULES_ELSEWHERE)
    if list_is_too_long(store, guild_id, key):
        lines.append(LIST_TOO_LONG.format(count=len(value or ())))
    return lines


def default_sentence(store: Any, guild_id: int, key: str) -> str:
    return PUT_BACK_MAKES.format(key=key, value=display_value(key, store.default(key)))


def needs_confirm(key: str) -> bool:
    return key in CONFIRM_KEYS


def confirm_lines(store: Any, guild_id: int, key: str) -> list[str]:
    if not needs_confirm(key):
        return []
    return [CONFIRM_STAFF_CHANNEL.format(channel=display_value(key, store.default(key)))]


class BackOn(NamedTuple):
    key: str
    command: str
    label: str


def back_on_options(bot: Any, guild_id: int) -> tuple[BackOn, ...]:
    """`hidden_names` is the ONE source, so the list cannot miss a feature or invent one."""
    hidden = hidden_names(bot, guild_id)
    return tuple(
        BackOn(row.key, row.command, BACK_ON_OPTION.format(label=row.label))
        for row in FEATURE_MODES
        if row.command in hidden
    )


def level_moves(current: Any) -> tuple[str, ...]:
    now = str(current) if str(current) in LEVELS else LEVEL_DEFAULT
    return tuple(level for level in LEVELS if level != now)


def log_level_options(store: Any, guild_id: int) -> tuple[tuple[str, str], ...]:
    return tuple(
        (
            log_level_key(feature),
            LOG_LEVEL_OPTION.format(
                label=FEATURE_LABELS.get(feature, feature),
                level=store.get(guild_id, log_level_key(feature)),
            ),
        )
        for feature in FEATURES
    )


def panel_minutes_keys() -> tuple[str, ...]:
    return tuple(key for key in KEY_TYPES if key.endswith("_panel_minutes"))


def panel_minutes_options(store: Any, guild_id: int) -> tuple[tuple[str, str], ...]:
    return tuple(
        (key, PANEL_MINUTES_OPTION.format(key=key, minutes=store.get(guild_id, key)))
        for key in panel_minutes_keys()
    )


def may_edit_core_keys(store: Any, guild_id: int, *, manage_guild: bool) -> bool:
    """F-S3 (a): locking the four keys that decide who is staff is access-REDUCING."""
    if not store.get(guild_id, CORE_KEYS_ADMIN_ONLY_KEY):
        return True
    return bool(manage_guild)


def toggle_label(key: str, value: Any) -> str:
    """P3: one button that says what it will DO, never both spellings of one move."""
    words = TOGGLE_LABELS.get(key)
    if words:
        return words[0] if value else words[1]
    return (TURN_IT_OFF if value else TURN_IT_ON).format(key=key)


def editor_move(key: str, value: Any) -> PanelMove | None:
    editor = control_for(key)
    if not editor:
        return None
    if editor == TOGGLE:
        return TOGGLE_MOVE._replace(label=toggle_label(key, value))
    return next(move for move in EDITOR_MOVES if move.action == f"{EDIT}:{editor}")


def root_buttons(
    *, may_turn_back_on: bool, may_edit_core: bool, has_site: bool
) -> tuple[PanelMove, ...]:
    """P3: a control the caller may not use is absent, and the embed says who it is for."""
    found: list[PanelMove] = []
    if may_turn_back_on:
        found.append(BACK_ON_MOVE)
    found.append(GROUP_MOVE)
    if may_edit_core:
        found.append(ROLES_CHANNELS_MOVE)
    found.extend([LOOKS_MOVE, PANELS_MOVE, LOGS_MOVE])
    if has_site:
        found.append(SITE_MOVE)
    found.extend([LOG_LEVELS_MOVE, SELFTEST_MOVE, REFRESH_MOVE])
    return tuple(found)


def selftest_buttons(*, running: bool, has_messages: bool) -> tuple[PanelMove, ...]:
    """P3 again: **Purge now** is drawn only while there is something left to delete."""
    found: list[PanelMove] = []
    if not running:
        found.append(SELFTEST_RUN_MOVE)
    if has_messages:
        found.append(SELFTEST_PURGE_MOVE)
    found.extend([SELFTEST_LOGS_MOVE, BACK_MOVE._replace(row=1)])
    return tuple(found)


def selftest_lines(
    store: Any,
    guild_id: int,
    *,
    last: Any = None,
    failures: Any = (),
    waiting: int = 0,
    running: str = "",
) -> list[str]:
    lines = [
        SELFTEST_INTRO.format(minutes=store.get(guild_id, SELFTEST_PURGE_MINUTES)),
        SELFTEST_BOOT_ON if store.get(guild_id, SELFTEST_ON_BOOT) else SELFTEST_BOOT_OFF,
        SELFTEST_WHERE.format(
            value=display_value(SELFTEST_CHANNEL_ID, store.get(guild_id, SELFTEST_CHANNEL_ID))
        ),
    ]
    if running:
        lines.append(running)
    if last is None:
        lines.append(SELFTEST_NEVER)
        return lines
    lines.append(
        SELFTEST_LAST.format(
            started=last["started_at"],
            ok=last["ok"],
            failed=last["failed"],
            posted=last["posted"],
        )
    )
    lines.append(
        SELFTEST_PURGED.format(at=last["purged_at"])
        if last["purged_at"]
        else SELFTEST_WAITING.format(count=waiting)
    )
    lines.extend(
        SELFTEST_FAILURE.format(name=row["name"], detail=row["detail"]) for row in failures
    )
    return lines


def roles_channels_buttons() -> tuple[PanelMove, ...]:
    return (*CORE_KEY_MOVES, BACK_MOVE._replace(row=4))


def looks_buttons(*, presence_loaded: bool) -> tuple[PanelMove, ...]:
    found: list[PanelMove] = []
    if presence_loaded:
        found.append(REAPPLY_MOVE)
    found.extend([BIO_MOVE, STATUS_MOVE, SKIN_TONE_MOVE, BACK_MOVE._replace(row=2)])
    return tuple(found)


def panels_commands_buttons(
    store: Any, guild_id: int, *, manage_guild: bool
) -> tuple[PanelMove, ...]:
    found = [
        HIDE_TOGGLE_MOVE._replace(
            label=toggle_label(HIDE_COMMANDS_WHEN_OFF, store.get(guild_id, HIDE_COMMANDS_WHEN_OFF))
        ),
        PANEL_MINUTES_MOVE,
    ]
    if manage_guild:
        found.append(
            OPERATOR_TOGGLE_MOVE._replace(
                label=toggle_label(
                    OPERATOR_READ_LOG_KEY, store.get(guild_id, OPERATOR_READ_LOG_KEY)
                )
            )
        )
    found.extend([HOSTING_MOVE, BACK_MOVE._replace(row=3)])
    return tuple(found)


def log_levels_buttons() -> tuple[PanelMove, ...]:
    return (LEVEL_PICK_MOVE, BACK_MOVE._replace(row=2))


def level_buttons(current: Any) -> tuple[PanelMove, ...]:
    """Never three buttons with one greyed out — only the two levels it is not on."""
    moves = tuple(
        PanelMove(f"{LEVEL_SET}:{level}", level, "primary", row=1)
        for level in level_moves(current)
    )
    return (*moves, BACK_MOVE._replace(row=2))


def group_buttons(group: str) -> tuple[PanelMove, ...]:
    found = [KEY_PICK_MOVE]
    if needs_find(group):
        found.append(FIND_MOVE)
    found.append(BACK_MOVE._replace(row=1))
    return tuple(found)


def key_card_buttons(
    store: Any, guild_id: int, key: str, *, stored: bool, confirming: bool = False
) -> tuple[PanelMove, ...]:
    if confirming:
        return (CONFIRM_RESET_MOVE, CANCEL_MOVE)
    found: list[PanelMove] = []
    value = store.get(guild_id, key)
    if not list_is_too_long(store, guild_id, key):
        move = editor_move(key, value)
        if move is not None:
            found.append(move)
    if KEY_TYPES.get(key) in LIST_TYPES and value:
        found.append(CLEAR_LIST_MOVE)
    if stored:
        found.append(RESET_MOVE)
    found.append(BACK_MOVE._replace(label=KEY_BACK_LABEL, row=2))
    return tuple(found)


def panel_minutes(store: Any, guild_id: int) -> int:
    return _panel_minutes(store, guild_id, PANEL_MINUTES_KEY)


def site_page_url(origin: Any) -> str | None:
    return _site_page_url(origin, SITE_FEATURE)


__all__ = [
    "BACK_ON_VALUE",
    "CONFIRM_KEYS",
    "CONFIRM_STAFF_CHANNEL",
    "CONFIRM_TITLE",
    "CORE_CHANNEL_KEYS",
    "CORE_KEYS_ADMIN_ONLY_KEY",
    "CORE_KEYS_ARE_FOR_A_LEAD",
    "EDITOR_LABELS",
    "FEATURE_MODES",
    "FIND_LABEL",
    "FIND_TITLE",
    "HIDDEN_NONE",
    "HIDDEN_SOME",
    "HIDE_CHANGED",
    "HIDE_OFF_STATE",
    "HIDE_ON_STATE",
    "HIDING_OFF",
    "KEY_PURPOSE",
    "LIST_TOO_LONG",
    "NOTHING_MATCHES",
    "NO_EDITOR",
    "PANEL_MINUTES_KEY",
    "PANEL_MINUTES_NEXT_TIME",
    "PANEL_MOVES",
    "PANEL_TIMEOUT_FOOTER",
    "PANEL_TITLE",
    "PRESENCE_NOT_RUNNING",
    "RULES_ELSEWHERE",
    "SELECT_LIMIT",
    "SELFTEST_ALL_WELL",
    "SELFTEST_DONE",
    "SELFTEST_IS_RUNNING",
    "SELFTEST_NOTHING_TO_PURGE",
    "SELFTEST_PURGE_DONE",
    "SELFTEST_TITLE",
    "SITE_FEATURE",
    "BackOn",
    "FeatureMode",
    "Options",
    "PanelMove",
    "back_on_options",
    "bounds_line",
    "confirm_lines",
    "control_for",
    "default_sentence",
    "editable_options",
    "editor_move",
    "group_buttons",
    "groups",
    "has_editor",
    "hidden_line",
    "key_card_buttons",
    "key_card_lines",
    "keys_in",
    "level_buttons",
    "level_moves",
    "list_is_too_long",
    "log_level_options",
    "log_levels_buttons",
    "looks_buttons",
    "matches",
    "may_edit_core_keys",
    "mode_lines",
    "mode_state",
    "needs_confirm",
    "needs_find",
    "panel_minutes",
    "panel_minutes_keys",
    "panel_minutes_options",
    "panels_commands_buttons",
    "reachable_on_the_panel",
    "roles_channels_buttons",
    "root_buttons",
    "root_lines",
    "selftest_buttons",
    "selftest_lines",
    "site_page_url",
    "stored_count",
    "toggle_label",
]
