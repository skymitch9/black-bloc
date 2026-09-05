from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, NamedTuple

from . import rolegrants as grants
from .golive import parse_ts
from .panels import panel_minutes as library_panel_minutes
from .panels import site_page_url as library_site_page_url

PANEL_MINUTES_KEY = "rolemenu_panel_minutes"
SITE_FEATURE = "rolemenu"
STAFF_MODE = "staff"
ON = "on"
AUDIT_MAX = 25

PANEL_TITLE = "Role menus"
MENU_TITLE = "The menu {name}"
ADD_ROLE_TITLE = "Add a role to {name}"
HAND_OUT_TITLE = "Hand out roles from {name}"
GRANTS_TITLE = "Timed roles running right now"
NEW_GRANT_TITLE = "Give somebody a role"
GRANT_TITLE = "Timed role #{grant_id}"
REQUESTS_TITLE = "Requests waiting on staff"
CONFIRM_TITLE = "Are you sure?"
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /rolemenu again"

NO_MENUS_LINE = (
    "This server has no role menus yet. **New menu** starts one, and **Seed the defaults** "
    "brings over the six this server was built with."
)
PICKING_IS_OFF = (
    "Members cannot pick roles from the posted panels right now, so the panels are down and "
    "**Post it** and **Hand roles out…** are missing from every menu. Nobody has lost a role."
)
MENU_LIST_LINE = "**{name}** — {count} role(s), {mode}, {posted}"
NO_ROLES_YET = "No roles on it yet — **Add a role…** puts the first one on."
NOBODY_PICKS_THESE = (
    "Nobody gives themselves these roles, so there is no panel to post — **Hand roles out…** "
    "is how they are handed over."
)
OPTIONS_ARE_FULL = (
    "This menu is holding all {limit} roles Discord will show, so nothing else fits. Split it "
    "into a second menu."
)
NO_ORDERING = (
    "The order the options sit in is set on the Role menus page; Discord has nothing to drag "
    "with, so this panel leaves it alone."
)

GRANTS_HEADER = "**{count}** timed role(s) running, soonest to end first."
GRANTS_FOR_ONE = "**{count}** timed role(s) running for that member, soonest to end first."
NO_GRANTS = (
    "Nothing in this server is on a clock right now. **Give somebody a role…** starts one."
)
NO_GRANTS_FOR_ONE = (
    "That member has no timed role running, so there is nothing to push back or end. "
    "**Give somebody a role…** starts one."
)
GRANTS_CAPPED = "{shown} of {total} — the Timed roles table on the site has the rest"
GRANT_PICK = "A timed role…"
GRANT_LINE = "<@{user_id}> · <@&{role_id}> · {left} · {ends}"
NO_END_DATE = "no end date"
ENDS_NEVER = "no end date"
DUE_NOW = "due now"
UNDER_A_DAY = "under a day left"
DAYS_LEFT = "{days} day(s) left"

NO_REQUESTS = "Nothing is waiting on staff right now."
REQUEST_PICK = "A request…"
REQUESTS_CAPPED = "{shown} of {total} — the Role menus page has the rest"

MENU_PICK = "A menu…"
MENUS_CAPPED = "{shown} of {total} — the Role menus page has the rest"
WHOSE_ROLES = "Whose roles?"
WHO_GETS_IT = "Who gets it?"
WHICH_ROLE = "Which role?"
REMOVE_PICK = "Take a role off this menu…"
ROLE_PICK = "A role to put on the menu…"

MODE_ON_LABEL = "Turn role menus on"
MODE_OFF_LABEL = "Turn role menus off"
APPROVAL_ON_LABEL = "Ask staff first"
APPROVAL_OFF_LABEL = "Hand it over straight away"
POST_LABEL = "Post it"
MOVE_LABEL = "Move it…"

DELETE_QUESTION = (
    "Delete **{name}**? Nobody loses a role they already have, and any panel already posted "
    "stops working."
)
DELETE_YES_LABEL = "Yes, delete it"
KEEP_IT_LABEL = "Keep it"
END_QUESTION = (
    "Take <@&{role_id}> back off <@{user_id}> now? They are not sent a DM — this is a staff "
    "move, and the log records who made it."
)
END_YES_LABEL = "Yes, take it back"
LEAVE_IT_LABEL = "Leave it"
SEED_QUESTION = (
    "Make the six default menus? A menu that already exists is left exactly as it is, options "
    "and all."
)
SEED_YES_LABEL = "Yes, make them"
LEAVE_THEM_LABEL = "Leave it"

MENU = "menu"
NEW_MENU = "new_menu"
SEED = "seed"
SEED_YES = "seed_yes"
GRANTS = "grants"
REQUESTS = "requests"
MODE = "mode"
LOGS = "logs"
REFRESH = "refresh"
BACK = "back"
ADD_ROLE = "add_role"
WORDS = "words"
RULES = "rules"
APPROVAL = "approval"
POST = "post"
TAKE_DOWN = "take_down"
HAND_OUT = "hand_out"
DELETE = "delete"
DELETE_YES = "delete_yes"
KEEP = "keep"
USE_ROLE_NAME = "use_role_name"
LABEL_IT = "label_it"
GIVE = "give"
TAKE_BACK = "take_back"
NEW_GRANT = "new_grant"
HOW_LONG = "how_long"
PUSH_BACK = "push_back"
END_NOW = "end_now"
END_YES = "end_yes"
LEAVE_IT = "leave_it"
APPROVE = "approve"
APPROVE_DAYS = "approve_days"
DENY = "deny"


class PanelMove(NamedTuple):
    action: str
    label: str
    style: str = "secondary"
    row: int = 0


NEW_MENU_MOVE = PanelMove(NEW_MENU, "New menu", "primary", 1)
SEED_MOVE = PanelMove(SEED, "Seed the defaults", "secondary", 1)
GRANTS_MOVE = PanelMove(GRANTS, "Grants…", "secondary", 1)
LOGS_MOVE = PanelMove(LOGS, "Logs", "secondary", 2)
REFRESH_MOVE = PanelMove(REFRESH, "Refresh", "secondary", 2)
BACK_MOVE = PanelMove(BACK, "Back", "secondary", 3)
ADD_ROLE_MOVE = PanelMove(ADD_ROLE, "Add a role…", "primary", 1)
WORDS_MOVE = PanelMove(WORDS, "Words…", "secondary", 1)
RULES_MOVE = PanelMove(RULES, "Rules…", "secondary", 1)
TAKE_DOWN_MOVE = PanelMove(TAKE_DOWN, "Take it down", "secondary", 2)
HAND_OUT_MOVE = PanelMove(HAND_OUT, "Hand roles out…", "secondary", 2)
DELETE_MOVE = PanelMove(DELETE, "Delete it", "danger", 2)
USE_ROLE_NAME_MOVE = PanelMove(USE_ROLE_NAME, "Use the role's own name", "primary", 1)
LABEL_IT_MOVE = PanelMove(LABEL_IT, "Give it a label…", "secondary", 1)
GIVE_MOVE = PanelMove(GIVE, "Give them roles…", "primary", 1)
TAKE_BACK_MOVE = PanelMove(TAKE_BACK, "Take roles back…", "secondary", 1)
NEW_GRANT_MOVE = PanelMove(NEW_GRANT, "Give somebody a role…", "primary", 2)
HOW_LONG_MOVE = PanelMove(HOW_LONG, "How long for…", "primary", 2)
PUSH_BACK_MOVE = PanelMove(PUSH_BACK, "Push it back…", "primary", 0)
END_NOW_MOVE = PanelMove(END_NOW, "End it now", "danger", 0)
DENY_MOVE = PanelMove(DENY, "Deny…", "danger", 0)
APPROVE_MOVE = PanelMove(APPROVE, "Approve", "success", 0)
APPROVE_DAYS_MOVE = PanelMove(APPROVE_DAYS, "Approve for a while…", "success", 0)


def requests_move(pending: int) -> PanelMove:
    return PanelMove(REQUESTS, f"Waiting on staff ({pending})…", "primary", 1)


def mode_move(picking_on: bool) -> PanelMove:
    """One button that says what it will do, never a menu with two spellings of one move."""
    return PanelMove(MODE, MODE_OFF_LABEL if picking_on else MODE_ON_LABEL, "secondary", 2)


def approval_move(approval: bool) -> PanelMove:
    label = APPROVAL_OFF_LABEL if approval else APPROVAL_ON_LABEL
    return PanelMove(APPROVAL, label, "secondary", 1)


def post_move(posted: bool) -> PanelMove:
    return PanelMove(POST, MOVE_LABEL if posted else POST_LABEL, "primary", 2)


def root_buttons(*, has_menus: bool, picking_on: bool, pending: int = 0) -> tuple[PanelMove, ...]:
    """§B's root table as data — the mode never removes a control from the root."""
    found = [NEW_MENU_MOVE, SEED_MOVE, GRANTS_MOVE]
    if pending:
        found.append(requests_move(pending))
    found.append(mode_move(picking_on))
    found.append(LOGS_MOVE)
    found.append(REFRESH_MOVE)
    _ = has_menus
    return tuple(found)


def menu_buttons(
    *,
    posted: bool,
    options: int,
    menu_mode: str,
    picking_on: bool,
    approval: bool,
    options_max: int,
) -> tuple[PanelMove, ...]:
    """§C's menu-card table as data; a control a shared function would refuse is absent."""
    found: list[PanelMove] = []
    if options < options_max:
        found.append(ADD_ROLE_MOVE)
    found.append(WORDS_MOVE)
    found.append(RULES_MOVE)
    found.append(approval_move(approval))
    if picking_on and menu_mode != STAFF_MODE and options:
        found.append(post_move(posted))
    if posted:
        found.append(TAKE_DOWN_MOVE)
    if picking_on and options:
        found.append(HAND_OUT_MOVE)
    found.append(DELETE_MOVE)
    found.append(BACK_MOVE)
    found.append(REFRESH_MOVE._replace(row=3))
    return tuple(found)


def add_role_buttons(*, picked: bool) -> tuple[PanelMove, ...]:
    found = [USE_ROLE_NAME_MOVE, LABEL_IT_MOVE] if picked else []
    return (*found, BACK_MOVE._replace(row=2))


def hand_out_buttons(*, picked: bool, holds_any: bool) -> tuple[PanelMove, ...]:
    """`Take roles back…` needs them to hold one of this menu's roles, so it renders only then."""
    found: list[PanelMove] = []
    if picked:
        found.append(GIVE_MOVE)
        if holds_any:
            found.append(TAKE_BACK_MOVE)
    return (*found, BACK_MOVE._replace(row=3))


def grants_buttons() -> tuple[PanelMove, ...]:
    return (NEW_GRANT_MOVE, BACK_MOVE._replace(row=2), REFRESH_MOVE._replace(row=2))


def new_grant_buttons(*, member: bool, role: bool) -> tuple[PanelMove, ...]:
    found = [HOW_LONG_MOVE] if member and role else []
    return (*found, BACK_MOVE._replace(row=2))


def grant_buttons(*, ends: bool, removed: bool) -> tuple[PanelMove, ...]:
    """A closed grant has nothing to move; a grant with no end date has nothing to push back."""
    found: list[PanelMove] = []
    if not removed:
        if ends:
            found.append(PUSH_BACK_MOVE)
        found.append(END_NOW_MOVE)
    return (*found, BACK_MOVE._replace(row=0))


def request_buttons(status: Any, *, timed: bool) -> tuple[PanelMove, ...]:
    found: list[PanelMove] = []
    if str(status) == grants.PENDING:
        found.append(APPROVE_DAYS_MOVE if timed else APPROVE_MOVE)
        found.append(DENY_MOVE)
    return (*found, BACK_MOVE._replace(row=0))


def requests_list_buttons() -> tuple[PanelMove, ...]:
    return (BACK_MOVE._replace(row=1), REFRESH_MOVE._replace(row=1))


def menu_heading(menu: Any) -> str:
    posted = "posted" if menu["message_id"] else "not posted"
    return f"**{menu['name']}** — {menu['title']} ({menu['mode']}, {posted})"


def option_line(row: Any) -> str:
    return f"{row['emoji'] or '•'} {row['label']} — <@&{row['role_id']}>"


def menu_lines(menu: Any, options: Any, *, note: str = "") -> list[str]:
    """What `/rolemenu show` printed, plus the panel's own 'Before you pick' sentences."""
    rows = list(options or ())
    lines = [menu_heading(menu), *(option_line(row) for row in rows)]
    if not rows:
        lines.append(NO_ROLES_YET)
    if str(menu["mode"]) == STAFF_MODE:
        lines.append(NOBODY_PICKS_THESE)
    if note:
        lines.append(note)
    if len(rows) > 1:
        lines.append(NO_ORDERING)
    return lines


def list_lines(menus: Any, counts: Any) -> list[str]:
    """What `/rolemenu list` printed, from a menu id → option count map."""
    found = dict(counts or {})
    return [
        MENU_LIST_LINE.format(
            name=menu["name"],
            count=int(found.get(menu["id"], 0)),
            mode=menu["mode"],
            posted="posted" if menu["message_id"] else "not posted",
        )
        for menu in menus or ()
    ]


def ends_at(row: Any) -> Any:
    try:
        return row["expires_at"]
    except (KeyError, IndexError, TypeError):
        return None


def grant_order(row: Any) -> tuple[int, str]:
    """Soonest to end first; a grant with no end date sorts last rather than first."""
    when = ends_at(row)
    return (1, "") if not when else (0, str(when))


def time_left(expires_at: Any, *, at: datetime | None = None) -> str:
    if not expires_at:
        return ENDS_NEVER
    when = parse_ts(expires_at)
    if when is None:
        return ENDS_NEVER
    gap = when - (at or datetime.now(UTC))
    seconds = gap.total_seconds()
    if seconds <= 0:
        return DUE_NOW
    days = int(seconds // 86400)
    return DAYS_LEFT.format(days=days) if days else UNDER_A_DAY


def grant_line(row: Any, *, at: datetime | None = None) -> str:
    when = ends_at(row)
    return GRANT_LINE.format(
        user_id=row["user_id"],
        role_id=row["role_id"],
        left=time_left(when, at=at),
        ends=grants.stamp(when, "D") if when else NO_END_DATE,
    )


def grant_lines(
    rows: Any, *, one_member: bool = False, at: datetime | None = None, limit: int = AUDIT_MAX
) -> list[str]:
    """The §I-amend audit: every running timed role, soonest to end first, capped at `limit`."""
    found = list(rows or ())
    if not found:
        return [NO_GRANTS_FOR_ONE if one_member else NO_GRANTS]
    header = GRANTS_FOR_ONE if one_member else GRANTS_HEADER
    lines = [header.format(count=len(found))]
    lines += [grant_line(row, at=at) for row in found[:limit]]
    if len(found) > limit:
        lines.append(GRANTS_CAPPED.format(shown=limit, total=len(found)))
    return lines


async def active_grants(db: Any, guild_id: int, *, user_id: int | None = None) -> list[Any]:
    """Every timed role still running here, soonest to end first — one home, both doors."""
    rows = await grants.grants_for(db, guild_id, user_id=user_id)
    open_now = [row for row in rows if row["removed_at"] is None and row["expires_at"]]
    forever = [row for row in rows if row["removed_at"] is None and not row["expires_at"]]
    return sorted(open_now + forever, key=grant_order)


def panel_minutes(store: Any, guild_id: int) -> int:
    return library_panel_minutes(store, guild_id, PANEL_MINUTES_KEY)


def site_page_url(origin: Any) -> str | None:
    return library_site_page_url(origin, SITE_FEATURE)


__all__ = [
    "ADD_ROLE",
    "APPROVAL",
    "APPROVE",
    "APPROVE_DAYS",
    "AUDIT_MAX",
    "BACK",
    "DELETE",
    "DELETE_QUESTION",
    "DELETE_YES",
    "DENY",
    "END_NOW",
    "END_QUESTION",
    "END_YES",
    "GRANTS",
    "GRANTS_CAPPED",
    "GIVE",
    "HAND_OUT",
    "HOW_LONG",
    "KEEP",
    "LABEL_IT",
    "LEAVE_IT",
    "LOGS",
    "MENU",
    "MODE",
    "NEW_GRANT",
    "NEW_MENU",
    "NO_MENUS_LINE",
    "PANEL_MINUTES_KEY",
    "PANEL_TIMEOUT_FOOTER",
    "PANEL_TITLE",
    "PICKING_IS_OFF",
    "POST",
    "PUSH_BACK",
    "REFRESH",
    "REQUESTS",
    "RULES",
    "SEED",
    "SEED_QUESTION",
    "SEED_YES",
    "TAKE_BACK",
    "TAKE_DOWN",
    "USE_ROLE_NAME",
    "WORDS",
    "PanelMove",
    "active_grants",
    "add_role_buttons",
    "approval_move",
    "grant_buttons",
    "grant_line",
    "grant_lines",
    "grant_order",
    "grants_buttons",
    "hand_out_buttons",
    "list_lines",
    "menu_buttons",
    "menu_heading",
    "menu_lines",
    "mode_move",
    "new_grant_buttons",
    "option_line",
    "panel_minutes",
    "post_move",
    "request_buttons",
    "requests_list_buttons",
    "requests_move",
    "root_buttons",
    "site_page_url",
    "time_left",
]
