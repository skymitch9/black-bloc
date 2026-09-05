from __future__ import annotations

from typing import Any, NamedTuple

from .panels import SELECT_OPTION_LIMIT
from .panels import panel_minutes as _panel_minutes
from .settings_store import HONEYPOT_MODES

PANEL_MINUTES_KEY = "honeypot_panel_minutes"
PANEL_TITLE = "The trap that catches spam bots"
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /honeypot again"

EXEMPT_SELECT_MAX = 25
CHANNEL_NAME_MAX = 100

MODE_LABELS: dict[str, str] = {
    "off": "off — nothing posted in the trap is read at all",
    "shadow": "shadow — it deletes the post and logs it, and bans nobody",
    "on": "on — it deletes the post and bans the account that made it",
}

MODE_PLACEHOLDER = "What the trap does…"
EXEMPT_PLACEHOLDER = "Roles the trap ignores…"
FORGET_PLACEHOLDER = "Forget a trap channel…"

TRAP_OPTION = "#{name}"
GONE_CHANNEL = "a channel Discord no longer has ({ident})"

SETUP = "setup"
FORGET = "forget"
FORGET_PICK = "forget_pick"
CLEAR_EXEMPT = "clear_exempt"
SETTINGS = "settings"
REFRESH = "refresh"
LOGS = "logs"
SITE = "site"
BACK = "back"
PANEL_NUMBERS = "panel_numbers"


class HoneypotMove(NamedTuple):
    action: str
    label: str
    style: str = "secondary"
    row: int = 0
    modal: bool = False


SETUP_MOVE = HoneypotMove(SETUP, "Setup…", "primary", row=2, modal=True)
FORGET_MOVE = HoneypotMove(FORGET, "Forget…", "secondary", row=2)
CLEAR_EXEMPT_MOVE = HoneypotMove(CLEAR_EXEMPT, "Exempt nobody", "danger", row=2)
SETTINGS_MOVE = HoneypotMove(SETTINGS, "Settings…", "secondary", row=2)
REFRESH_MOVE = HoneypotMove(REFRESH, "Refresh", "secondary", row=3)
LOGS_MOVE = HoneypotMove(LOGS, "Logs", "secondary", row=3)
SITE_MOVE = HoneypotMove(SITE, "Open on the site", "link", row=3)
PANEL_NUMBERS_MOVE = HoneypotMove(PANEL_NUMBERS, "Numbers…", "secondary", modal=True)
BACK_MOVE = HoneypotMove(BACK, "Back", "secondary", row=1)

PANEL_MOVES = (
    SETUP_MOVE,
    FORGET_MOVE,
    CLEAR_EXEMPT_MOVE,
    SETTINGS_MOVE,
    REFRESH_MOVE,
    LOGS_MOVE,
    SITE_MOVE,
    PANEL_NUMBERS_MOVE,
    BACK_MOVE,
)

NUMBERS_TITLE = "Numbers"
PANEL_MINUTES_LABEL = "Minutes this panel stays live"
PURGE_DAYS_LABEL = "Days of their messages a ban deletes"
TRAP_NAME_TITLE = "The trap channel"
TRAP_NAME_LABEL = "What the trap channel is called"

MODE_SET = "The trap is now **{mode}**."
SETTINGS_NOTHING = "Nothing was given, so nothing changed."
SETTINGS_DONE = (
    "The panel stays live {minutes} minute(s), and a ban deletes {days} day(s) of their messages."
)
NOT_A_NUMBER = (
    "**{given}** is not a whole number, so nothing at all was changed — not even the other box. "
    "{label} takes a whole number."
)
EXEMPT_NOTHING_CHANGED = (
    "Those are already the roles the trap ignores, so nothing changed and nothing was logged."
)
EXEMPT_NOW_NOBODY = "The trap ignores nobody but staff now."
EXEMPT_ADDED = "now ignores {roles}"
EXEMPT_REMOVED = "stops ignoring {roles}"
EXEMPT_TOO_MANY = (
    "⚠️ **{count} roles are exempt**, which is more than one Discord picker can edit at once, so "
    "the list is only editable on the site's Honeypot page. Nothing here can change it without "
    "silently dropping the roles the picker could not show."
)
DEAD_TRAP_LINE = (
    "⚠️ **recorded but gone** — {ids}. Discord no longer has {them}; **Forget…** takes {them} off "
    "the list."
)
ARMED_WITH_NO_TRAP = (
    "The trap is armed, but there is no trap channel yet for anybody to fall into — press "
    "**Setup…**."
)
TEST_MODE_LINE = (
    "⚠️ **Test mode** — the trap is kept inside the test channel's category and nobody will "
    "actually be banned, whatever the mode says."
)
MODE_IS_OFF_WAY_BACK = (
    "While the mode is **off** this command disappears from Discord within about a minute. The "
    "ways back are `/settings set-value honeypot_mode shadow` and the dashboard's Settings page."
)


def root_buttons(
    *, may_setup: bool, may_forget: bool, may_clear: bool, has_site: bool
) -> tuple[HoneypotMove, ...]:
    """P3: a move the shared function would refuse is absent, never offered-and-refused."""
    found: list[HoneypotMove] = []
    if may_setup:
        found.append(SETUP_MOVE)
    if may_forget:
        found.append(FORGET_MOVE)
    if may_clear:
        found.append(CLEAR_EXEMPT_MOVE)
    found.append(SETTINGS_MOVE)
    found.append(REFRESH_MOVE)
    found.append(LOGS_MOVE)
    if has_site:
        found.append(SITE_MOVE)
    return tuple(found)


def settings_buttons() -> tuple[HoneypotMove, ...]:
    return (PANEL_NUMBERS_MOVE, BACK_MOVE)


def forget_buttons() -> tuple[HoneypotMove, ...]:
    return (BACK_MOVE,)


def mode_options(current: Any, may_arm: bool) -> list[tuple[str, str, bool]]:
    """`on` is left off the picker while arming would refuse, never offered-and-refused."""
    return [
        (name, MODE_LABELS[name], name == current)
        for name in HONEYPOT_MODES
        if may_arm or name != "on"
    ]


def trap_options(recorded: Any, names: Any = None) -> list[tuple[str, int, bool]]:
    """Every recorded id gets a row; one Discord no longer has says so instead of vanishing."""
    known = names or {}
    found: list[tuple[str, int, bool]] = []
    for one in recorded or ():
        ident = int(one)
        name = known.get(ident)
        said = TRAP_OPTION.format(name=name) if name else GONE_CHANNEL.format(ident=ident)
        found.append((said[:SELECT_OPTION_LIMIT], ident, name is not None))
    return found


def exempt_defaults(role_ids: Any) -> list[int]:
    """The prefill for the role picker: de-duplicated, order-stable, whole numbers."""
    found: list[int] = []
    for one in role_ids or ():
        ident = int(one)
        if ident not in found:
            found.append(ident)
    return found


def exempt_editable(role_ids: Any) -> bool:
    """Above the cap the picker is withheld: submitting it would delete what it cannot show."""
    return len(exempt_defaults(role_ids)) <= EXEMPT_SELECT_MAX


def exempt_diff(before: Any, after: Any) -> tuple[list[int], list[int]]:
    was = exempt_defaults(before)
    now = exempt_defaults(after)
    return ([one for one in now if one not in was], [one for one in was if one not in now])


def exempt_sentence(added: list[int], removed: list[int]) -> str:
    """What the one write did, in words — the added/removed halves the log row also carries."""
    parts = []
    if added:
        parts.append(EXEMPT_ADDED.format(roles=", ".join(f"<@&{one}>" for one in added)))
    if removed:
        parts.append(EXEMPT_REMOVED.format(roles=", ".join(f"<@&{one}>" for one in removed)))
    if not parts:
        return EXEMPT_NOTHING_CHANGED
    return "The trap " + " and ".join(parts) + "."


def panel_minutes(store: Any, guild_id: int) -> int:
    return _panel_minutes(store, guild_id, PANEL_MINUTES_KEY)


__all__ = [
    "BACK",
    "CHANNEL_NAME_MAX",
    "CLEAR_EXEMPT",
    "EXEMPT_SELECT_MAX",
    "FORGET",
    "FORGET_PICK",
    "LOGS",
    "PANEL_MINUTES_KEY",
    "PANEL_MOVES",
    "PANEL_NUMBERS",
    "PANEL_TIMEOUT_FOOTER",
    "PANEL_TITLE",
    "REFRESH",
    "SETTINGS",
    "SETUP",
    "SITE",
    "HoneypotMove",
    "exempt_defaults",
    "exempt_diff",
    "exempt_editable",
    "exempt_sentence",
    "forget_buttons",
    "mode_options",
    "panel_minutes",
    "root_buttons",
    "settings_buttons",
    "trap_options",
]
