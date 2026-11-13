from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from typing import Any, NamedTuple

from . import panels, timezones
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

NO_MENUS_LINE = "This server has no role menus yet. **New menu** starts one."
NO_ROLES_YET = "No roles on it yet — **Add a role…** puts the first one on."
OPTIONS_ARE_FULL = (
    "This menu is holding all {limit} roles Discord will show, so nothing else fits. Split it "
    "into a second menu."
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

DELETE_QUESTION = (
    "Delete **{name}**? Nobody loses a role they already have, and any panel already posted "
    "stops working."
)
DELETE_YES_LABEL = "Yes, delete it"
KEEP_IT_LABEL = panels.KEEP_IT
END_QUESTION = (
    "Take <@&{role_id}> back off <@{user_id}> now? They are not sent a DM — this is a staff "
    "move, and the log records who made it."
)
END_YES_LABEL = "Yes, take it back"
LEAVE_IT_LABEL = "Leave it"

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
MODE_OFF_YES = "mode_off_yes"
LEAVE_IT = "leave_it"
APPROVE = "approve"
APPROVE_DAYS = "approve_days"
DENY = "deny"
SET_END = "set_end"
END_MENU = "end_menu"
END_MENU_YES = "end_menu_yes"
USE_HELD = "use_held"
USE_HELD_YES = "use_held_yes"
TYPE_DATE = "type_date"
BUFFER = "buffer"
NO_END_MOVE_ACTION = "no_end"
NO_END_YES = "no_end_yes"


class PanelMove(NamedTuple):
    action: str
    label: str
    style: str = "secondary"
    row: int = 0


NEW_MENU_MOVE = PanelMove(NEW_MENU, "New menu", "primary", 1)
GRANTS_MOVE = PanelMove(GRANTS, "Grants…", "secondary", 1)
LOGS_MOVE = PanelMove(LOGS, "Logs", "secondary", 2)
REFRESH_MOVE = PanelMove(REFRESH, "Refresh", "secondary", 2)
BACK_MOVE = PanelMove(BACK, "Back", "secondary", 3)
ADD_ROLE_MOVE = PanelMove(ADD_ROLE, "Add a role…", "primary", 1)
WORDS_MOVE = PanelMove(WORDS, "Words…", "secondary", 1)
HAND_OUT_MOVE = PanelMove(HAND_OUT, "Hand roles out…", "secondary", 1)
DELETE_MOVE = PanelMove(DELETE, "Delete it", "danger", 2)
USE_ROLE_NAME_MOVE = PanelMove(USE_ROLE_NAME, "Use the role's own name", "primary", 1)
LABEL_IT_MOVE = PanelMove(LABEL_IT, "Give it a label…", "secondary", 1)
GIVE_MOVE = PanelMove(GIVE, "Give them roles…", "primary", 1)
TAKE_BACK_MOVE = PanelMove(TAKE_BACK, "Take roles back…", "secondary", 1)
NEW_GRANT_MOVE = PanelMove(NEW_GRANT, "Give somebody a role…", "primary", 2)
HOW_LONG_MOVE = PanelMove(HOW_LONG, "How long for…", "primary", 2)
PUSH_BACK_MOVE = PanelMove(PUSH_BACK, "Push it back…", "primary", 0)
END_NOW_MOVE = PanelMove(END_NOW, "End it now", "danger", 0)


def root_buttons() -> tuple[PanelMove, ...]:
    """The permanent staff control: no seed, no mode switch, no requests (design §3.2)."""
    return (NEW_MENU_MOVE, GRANTS_MOVE, LOGS_MOVE, REFRESH_MOVE)


def menu_buttons(
    *, options: int, options_max: int, held: bool, words: dict[str, str]
) -> tuple[PanelMove, ...]:
    """A menu card's moves; one that needs roles on the menu renders only once it has some."""
    found: list[PanelMove] = []
    if options < options_max:
        found.append(ADD_ROLE_MOVE)
    if options:
        found.append(HAND_OUT_MOVE)
    found.append(PanelMove(SET_END, words[SET_END], "primary", 1))
    found.append(WORDS_MOVE)
    if options:
        found.append(PanelMove(END_MENU, words[END_MENU], "danger", 2))
    if held:
        found.append(PanelMove(USE_HELD, words[USE_HELD], "primary", 2))
    found.append(DELETE_MOVE)
    found.append(BACK_MOVE)
    found.append(REFRESH_MOVE._replace(row=3))
    return tuple(found)


def set_end_buttons(*, source: str, words: dict[str, str]) -> tuple[PanelMove, ...]:
    """Buffer… only for an end that follows a marathon; No end only while there is one."""
    found = [PanelMove(TYPE_DATE, words[TYPE_DATE], "primary", 1)]
    if source == MARATHON_END:
        found.append(PanelMove(BUFFER, words[BUFFER], "secondary", 1))
    if source != NO_END:
        found.append(PanelMove(NO_END_MOVE_ACTION, words[NO_END_MOVE_ACTION], "danger", 1))
    return (*found, BACK_MOVE._replace(row=2), REFRESH_MOVE._replace(row=2))


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


def menu_heading(menu: Any) -> str:
    return f"**{menu['name']}** — {menu['title']}"


def option_line(row: Any) -> str:
    return f"{row['emoji'] or '•'} {row['label']} — <@&{row['role_id']}>"


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


NO_END = "none"
DATE_END = "date"
MARATHON_END = "marathon"
END_SOURCES = (NO_END, DATE_END, MARATHON_END)
END_OF_DAY = time(23, 59)
DATE_FORMAT = "%Y-%m-%d"
BUFFER_MAX = 365
ROLE_MENU_END_RETRIES = 3


def cell(row: Any, key: str, default: Any = None) -> Any:
    try:
        found = row[key]
    except (KeyError, IndexError, TypeError):
        return default
    return default if found is None else found


def utc_iso(when: datetime | None) -> str | None:
    return None if when is None else when.astimezone(UTC).isoformat()


def typed_end(text: Any, tz_name: Any) -> datetime | None:
    """A typed `YYYY-MM-DD` ends at 23:59 guild-local; `YYYY-MM-DD HH:MM` at that minute."""
    words = str(text or "").strip()
    zone = timezones.zone(tz_name) or timezones.zone("UTC")
    for form, whole_day in ((timezones.START_FORMAT, False), (DATE_FORMAT, True)):
        try:
            naive = datetime.strptime(words, form)
        except ValueError:
            continue
        if whole_day:
            naive = datetime.combine(naive.date(), END_OF_DAY)
        return naive.replace(tzinfo=zone).astimezone(UTC)
    return None


def end_source(menu: Any) -> str:
    found = str(cell(menu, "ends_source", NO_END))
    return found if found in END_SOURCES else NO_END


def buffer_of(menu: Any, default_buffer: Any) -> int:
    for value in (cell(menu, "buffer_days"), default_buffer):
        try:
            return max(0, min(int(value), BUFFER_MAX))
        except (TypeError, ValueError):
            continue
    return 0


def ends_at_of(menu: Any, marathon: Any, default_buffer: Any) -> str | None:
    """The one moment everyone loses the menu's roles, as UTC ISO; None when there is none yet."""
    source = end_source(menu)
    if source == NO_END:
        return None
    if source == DATE_END or marathon is None:
        return utc_iso(parse_ts(cell(menu, "ends_at")))
    end = parse_ts(cell(marathon, "ends_at"))
    if end is None:
        return None
    return utc_iso(end + timedelta(days=buffer_of(menu, default_buffer)))


def end_moved(was: Any, now: Any) -> bool:
    before, after = parse_ts(was), parse_ts(now)
    if before is None or after is None:
        return (before is None) != (after is None)
    return before != after


def moved_far(was: Any, now: Any, minutes: Any) -> bool:
    """Whether a move is big enough to tell staff about; an end appearing or going always is."""
    if not end_moved(was, now):
        return False
    before, after = parse_ts(was), parse_ts(now)
    if before is None or after is None:
        return True
    try:
        floor = max(int(minutes), 0)
    except (TypeError, ValueError):
        floor = 0
    return abs((after - before).total_seconds()) >= floor * 60


def pulls_earlier(current: Any, told: Any, candidate: Any, minutes: Any) -> bool:
    """A new end earlier than the current or the last-told end by more than the floor."""
    after = parse_ts(candidate)
    if after is None:
        return False
    try:
        floor = max(int(minutes), 0) * 60
    except (TypeError, ValueError):
        floor = 0
    for was in (current, told):
        before = parse_ts(was)
        if before is not None and (before - after).total_seconds() > floor:
            return True
    return False


def is_due(menu: Any, at: datetime) -> bool:
    """Ended menus and unreadable ends are never due; nobody loses a role on a garbled date."""
    if cell(menu, "ended_at"):
        return False
    end = parse_ts(cell(menu, "ends_at"))
    return end is not None and end <= at


def wearers(members: Any, role_ids: Any) -> list[tuple[Any, list[int]]]:
    """Every member wearing any of these roles, with the ones they wear, in the menu's order."""
    wanted = [int(one) for one in role_ids or ()]
    found: list[tuple[Any, list[int]]] = []
    for member in members or ():
        worn = {int(getattr(role, "id", 0)) for role in getattr(member, "roles", ())}
        theirs = [role_id for role_id in wanted if role_id in worn]
        if theirs:
            found.append((member, theirs))
    return found


def what_ended(menu: Any, marathon_name: Any) -> str:
    if end_source(menu) == MARATHON_END and marathon_name:
        return str(marathon_name)
    return grants.stamp(cell(menu, "ends_at"), "D")


def said(store: Any, guild_id: Any, key: str, **fields: Any) -> str:
    """Checklist 17: staff words that will not fill, or fill to nothing, fall back to ours."""
    try:
        text = str(store.get(guild_id, key)).format_map(fields)
    except Exception:
        text = ""
    return text if text.strip() else str(store.default(key, guild_id)).format_map(fields)


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
    "DATE_END",
    "END_SOURCES",
    "MARATHON_END",
    "NO_END",
    "ROLE_MENU_END_RETRIES",
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
    "MODE_OFF_YES",
    "LOGS",
    "MENU",
    "MODE",
    "NEW_GRANT",
    "NEW_MENU",
    "NO_MENUS_LINE",
    "PANEL_MINUTES_KEY",
    "PANEL_TIMEOUT_FOOTER",
    "PANEL_TITLE",
    "POST",
    "PUSH_BACK",
    "REFRESH",
    "REQUESTS",
    "RULES",
    "SEED",
    "SEED_YES",
    "TAKE_BACK",
    "TAKE_DOWN",
    "USE_ROLE_NAME",
    "WORDS",
    "PanelMove",
    "active_grants",
    "buffer_of",
    "end_moved",
    "end_source",
    "ends_at_of",
    "is_due",
    "moved_far",
    "pulls_earlier",
    "said",
    "typed_end",
    "utc_iso",
    "wearers",
    "what_ended",
    "add_role_buttons",
    "grant_buttons",
    "grant_line",
    "grant_lines",
    "grant_order",
    "grants_buttons",
    "hand_out_buttons",
    "menu_buttons",
    "menu_heading",
    "new_grant_buttons",
    "option_line",
    "panel_minutes",
    "root_buttons",
    "set_end_buttons",
    "site_page_url",
    "time_left",
]
