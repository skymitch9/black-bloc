from __future__ import annotations

import json
import logging
import re
import sqlite3
from dataclasses import dataclass
from typing import Any

import discord

from .golive import now_iso
from .logkinds import FEATURE_PAGES
from .panels import panel_minutes as library_panel_minutes
from .rolegrants import (
    APPROVED,
    DENIED,
    PENDING,
    WITHDRAWN,
    clamp,
    retry_at,
    stamp,
    still_cooling,
)
from .settings_store import APPLICATIONS_MODES as MODES
from .settings_store import APPLICATIONS_RETRY_DAYS as RETRY_DAYS_DEFAULT

log = logging.getLogger(__name__)

MODE_KEY = "applications_mode"
CHANNEL_KEY = "applications_channel_id"
APPROVER_ROLE_KEY = "applications_approver_role_id"
PING_ROLE_KEY = "applications_ping_role_id"
RETRY_DAYS_KEY = "applications_retry_days"
DM_KEY = "applications_dm_on_decision"
ROSTER_SHOWS_LEFT_KEY = "applications_roster_shows_left"
PANEL_MINUTES_KEY = "applications_panel_minutes"
PANEL_OWN_LIST_KEY = "applications_panel_own_list"

REMOVED = "removed"
NO_ROLE = 0

STATUSES = (PENDING, APPROVED, DENIED, WITHDRAWN, REMOVED)
SETTLED = (APPROVED, DENIED, WITHDRAWN, REMOVED)
TRANSITIONS: dict[str, tuple[str, ...]] = {
    PENDING: (APPROVED, DENIED, WITHDRAWN),
    APPROVED: (REMOVED,),
    DENIED: (APPROVED,),
    WITHDRAWN: (),
    REMOVED: (APPROVED,),
}
RESTORABLE = tuple(one for one in (DENIED, REMOVED) if APPROVED in TRANSITIONS[one])

SHORT = "short"
LONG = "long"
STYLES = (SHORT, LONG)

QUESTIONS_MAX = 5
LABEL_MAX = 45
PLACEHOLDER_MAX = 100
TITLE_MAX = 45
NAME_MAX = 32
DESCRIPTION_MAX = 1000
TEXT_MAX = 1000
ANSWER_MAX = 1024
ANSWER_INPUT_MAX = 1024
REASON_MAX = 400
DAYS_MAX = 3650
NAME_SHAPE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

CARD_HEADING = "Application #{application_id} — {title}"
NO_ANSWER = "(left blank)"
DEFAULT_APPROVED_TEXT = "You're in — staff said yes."

FORM_NAME_SHAPE = (
    "**{given}** is not a name Black Bloc can use, so nothing was changed. Use lower-case "
    "letters, numbers, `-` and `_`, start with a letter or a number, and keep it under "
    "{limit} characters — `twitch-team` is the shape."
)
TOO_LONG = (
    "That {what} is {given} characters and Discord will not show more than {limit}, so nothing "
    "was changed. Shorten it and try again — Black Bloc will not cut down words you typed."
)
BAD_STYLE = (
    "**{given}** is not a kind of answer box, so nothing was changed. It is `short` (one line) "
    "or `long` (a paragraph)."
)
TOO_MANY_QUESTIONS = (
    "Discord shows at most {limit} boxes on one form and this would be number {given}, so "
    "nothing was added. Take one off with **Questions…** → **Remove** first."
)
BAD_POSITION = (
    "**{given}** is not a slot on this form, so nothing was changed. The slots are 1 to {limit} "
    "and **Questions…** says which are filled."
)
BAD_DAYS = (
    "**{given}** is not a number of days, so nothing was changed. Type a whole number from 0 to "
    "{limit} — 0 means it never runs out."
)

NO_SUCH_FORM = (
    "This server has no application form called **{name}**, so nothing was changed. "
    "`/apply` → **A form…** names the ones it has, and **New form** makes one."
)
NAME_TAKEN = (
    "This server already has an application form called **{name}**, so nothing was created. "
    "Pick another name, or change that one from `/apply` → **A form…** → **Edit…**."
)
NO_QUESTIONS_YET = (
    "**{name}** has no questions on it yet, so there is nothing to fill in. Staff add them with "
    "`/apply` → **A form…** → **Questions…**, then it can be applied for."
)
FORM_CLOSED = (
    "**{title}** is not taking applications right now, so nothing was sent. Staff reopen it with "
    "`/apply` → **A form…** → **Open it**."
)
APPLICATIONS_OFF = (
    "Applications are turned off right now, so nothing was sent. A Lead turns them on from the "
    "dashboard's Role menus tab or with `/settings set-value applications_mode on`."
)
ALREADY_APPLIED = (
    "You already have an application waiting on **{title}**, so nothing was sent twice. "
    "`/apply` says where it is, and its **Take one back…** picker withdraws it."
)
TOO_SOON = (
    "Staff decided your last **{title}** application on {when}, so you can apply again {stamp}. "
    "Nothing was sent."
)
SENT = (
    "Sent to staff — you'll get a DM either way. `/apply` says where it is, and its "
    "**Take one back…** picker withdraws it while it is still waiting."
)
CARD_NOT_POSTED = (
    "Your application for **{title}** is saved, but Black Bloc could not put the card in front "
    "of staff — the log says why. Tell a Lead so they can look at it by hand."
)
CARD_IN_TEST_CHANNEL = (
    " Test mode is on, so the card for staff is in the test channel rather than in the review "
    "channel."
)
NOTHING_TO_WITHDRAW = (
    "You have nothing waiting on **{title}**, so there was nothing to take back. `/apply` "
    "sends one."
)
NOT_YOUR_APPLICATION = (
    "That application belongs to somebody else, so nothing was changed. `/apply` lists your "
    "own."
)
NOTHING_TO_DECIDE = (
    "Black Bloc has no record of that application any more, so nothing was changed. The Role "
    "menus page lists the ones it still has."
)
ALREADY_DECIDED = (
    "Somebody got there first — that application is already **{status}**, so nothing was "
    "changed. The card above says who decided and when."
)
NOT_THIS_SERVER = (
    "That application belongs to somebody else's server, so nothing was changed."
)
MEMBER_HAS_GONE = (
    "**{name}** is not in this server any more, so the role could not be handed over and the "
    "application is still waiting. Deny it if it should be closed."
)
DENY_NEEDS_A_REASON = (
    "A denied application needs one line the person is sent, so nothing was done. Say why and "
    "send it again."
)
REMOVE_NEEDS_A_REASON = (
    "Taking somebody off the list needs one line they are sent, so nothing was done. Say why "
    "and send it again."
)
REMOVE_NOT_APPROVED = (
    "That application is **{status}**, not approved, so there was nobody to take off the list. "
    "`/apply` → **A form…** → **Roster** says who is on it."
)
ROLE_REFUSED_AFTER_DECISION = (
    "The application is marked approved, but Discord refused to add **{role}** — Black Bloc "
    "needs Manage Roles and its own role has to sit above it in Server Settings → Roles. Fix "
    "that, then hand it over with `/role grant`."
)
NO_REVIEW_CHANNEL = "no_review_channel"
NOTHING_PENDING = "Nobody is waiting on staff right now."
NO_FORMS_YET = (
    "This server has no application forms yet. `/apply` → **New form** makes the "
    "first one."
)
FORM_HAS_PENDING = (
    "**{name}** still has {count} application(s) waiting on staff, so it was not deleted. "
    "Decide them first, or close the form with **Close it** on its card."
)
PANEL_NOWHERE = (
    "Black Bloc has nowhere to put the Apply button, so nothing was posted. Say which channel "
    "with **Post the Apply button** on its card."
)
PANEL_STUCK = (
    "Black Bloc could not put the Apply button up for **{name}** — the log says why. It needs to "
    "see that channel and be able to post in it."
)
APPROVED_SAID = "Approved — **{name}** has **{role}** now.{extra}"
APPROVED_ON_RECORD = "Approved — **{name}** is on the **{title}** list now."
DENIED_SAID = "Denied, and they have been told why."
REMOVED_SAID = "Taken off the list, and they have been told why."
WITHDRAWN_SAID = "Taken back — staff will not be deciding it. Apply again whenever you want."
OWNER_NUDGE = "<@{owner_id}> — next step: {next_step}"
NEXT_STEP_UNOWNED = "Next step: {next_step}"
DM_APPROVED = "**{title}** on **{guild}** — approved. {said}"
DM_DENIED = (
    "**{title}** on **{guild}** — staff said no. The reason given was: {reason}. You can apply "
    "again {stamp}."
)
DM_REMOVED = (
    "**{title}** on **{guild}** — staff took you off the list. The reason given was: {reason}. "
    "You can apply again {stamp}."
)
DM_RECEIVED = (
    "Your **{title}** application on **{guild}** is with staff now. You'll get a DM either way."
)
EXPIRES_EXTRA = " The role runs out {stamp}."
GRANT_FAILED_ON_CARD = (
    "Discord refused to add the role, so it is still off them — hand it over with `/role grant`."
)

PANEL_TITLE = "Applications"
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /apply again"
PANEL_INTRO = (
    "Apply for what this server hands out, and see where what you already sent has got to."
)
NOTHING_OF_YOURS = "You have not applied for anything here yet."
YOUR_APPLICATION = "**{title}** — {status}{extra}"
STATUS_WAITING = ", waiting on staff"
NOTHING_TO_SHOW = (
    "Black Bloc has no application with that number, so there was nothing to show. Pick one "
    "from **A form…** instead, or open the Role menus page."
)
COUNTS_LINE = "**{forms}** form(s) · **{waiting}** waiting · **{approved}** on a list"
PICK_A_FORM = "A form…"
PICK_AN_APPLICATION = "Pick an application…"
APPLY_FOR = "Apply for…"
TAKE_ONE_BACK = "Take one back…"
SITE_BUTTON = "Open on the site"
NOT_A_NUMBER = (
    "**{given}** is not an application number, so nothing was looked up. They look like `#12`, "
    "and the number is on the card."
)
WITHDRAWN_IS_THEIRS = (
    "The person took this back themselves, so there is nothing for staff to move. They may "
    "apply again whenever they like."
)
REINSTATED_SAID = "**#{application_id}** is approved again, and they have been told."
NOT_REINSTATABLE = (
    "That application is **{status}**, so there was nothing to put back. Only a denied one or "
    "somebody taken off a list can be approved after the fact."
)


@dataclass(frozen=True)
class MoveButton:
    """One button on an application card: what it says, and which shared function it calls."""

    label: str
    style: str
    action: str
    needs_modal: bool = False


APPROVE = MoveButton("Approve", "success", "approve")
DENY = MoveButton("Deny", "danger", "deny", needs_modal=True)
TAKE_OFF = MoveButton("Take off the list", "danger", "remove", needs_modal=True)
APPROVE_AFTER_ALL = MoveButton("Approve after all", "success", "reinstate")
PUT_BACK = MoveButton("Put them back on the list", "success", "reinstate")

CARD_BUTTONS: dict[str, tuple[MoveButton, ...]] = {
    PENDING: (APPROVE, DENY),
    APPROVED: (TAKE_OFF,),
    DENIED: (APPROVE_AFTER_ALL,),
    WITHDRAWN: (),
    REMOVED: (PUT_BACK,),
}
MOVE_TARGETS: dict[str, str] = {
    "approve": APPROVED,
    "deny": DENIED,
    "remove": REMOVED,
    "reinstate": APPROVED,
}


class ApplicationError(ValueError):
    """A form, a question or a decision arrived in a shape Black Bloc will not store."""


def may_move(current: Any, wanted: str) -> bool:
    return wanted in TRANSITIONS.get(str(current or ""), ())


def card_buttons(
    status: Any, *, has_role: bool = False, may_decide: bool = True
) -> tuple[MoveButton, ...]:
    """The moves this card actually offers — never one the shared function would refuse."""
    if not may_decide:
        return ()
    found = str(status or "")
    if found == APPROVED and has_role:
        return ()
    return CARD_BUTTONS.get(found, ())


def check_length(what: str, value: str, limit: int) -> str:
    if len(value) > limit:
        raise ApplicationError(TOO_LONG.format(what=what, given=len(value), limit=limit))
    return value


def check_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text or len(text) > NAME_MAX or NAME_SHAPE.match(text) is None:
        raise ApplicationError(
            FORM_NAME_SHAPE.format(given=str(value or "")[:40], limit=NAME_MAX)
        )
    return text


def check_title(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise ApplicationError(TOO_LONG.format(what="heading", given=0, limit=TITLE_MAX))
    return check_length("heading", text, TITLE_MAX)


def check_style(value: Any) -> str:
    text = str(value or SHORT).strip().lower()
    if text not in STYLES:
        raise ApplicationError(BAD_STYLE.format(given=str(value or "")[:40]))
    return text


def check_position(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 0
    if number < 1 or number > QUESTIONS_MAX:
        raise ApplicationError(
            BAD_POSITION.format(given=str(value)[:40], limit=QUESTIONS_MAX)
        )
    return number


def whole_days(value: Any) -> int | None:
    """A number of days, or None when nothing usable was given."""
    if value is None or value == "":
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ApplicationError(
            BAD_DAYS.format(given=str(value)[:40], limit=DAYS_MAX)
        ) from None
    if number < 0 or number > DAYS_MAX:
        raise ApplicationError(BAD_DAYS.format(given=str(value)[:40], limit=DAYS_MAX))
    return number


def positive_days(value: Any) -> int | None:
    days = whole_days(value)
    return days if days else None


def validate_question(
    label: Any,
    style: Any = SHORT,
    required: Any = True,
    placeholder: Any = None,
    *, position: Any = None,
) -> dict[str, Any]:
    """One question row, checked against Discord's own limits before it is stored."""
    text = str(label or "").strip()
    if not text:
        raise ApplicationError(TOO_LONG.format(what="question", given=0, limit=LABEL_MAX))
    check_length("question", text, LABEL_MAX)
    hint = str(placeholder or "").strip() or None
    if hint is not None:
        check_length("hint", hint, PLACEHOLDER_MAX)
    found = {
        "label": text,
        "style": check_style(style),
        "required": int(bool(required)),
        "placeholder": hint,
    }
    if position is not None:
        found["position"] = check_position(position)
    return found


def validate_questions(items: Any) -> list[dict[str, Any]]:
    """The whole ordered list a form ends up holding; positions are 1..n as given."""
    rows = list(items or ())
    if len(rows) > QUESTIONS_MAX:
        raise ApplicationError(
            TOO_MANY_QUESTIONS.format(limit=QUESTIONS_MAX, given=len(rows))
        )
    found: list[dict[str, Any]] = []
    for at, item in enumerate(rows, start=1):
        row = item if isinstance(item, dict) else {"label": item}
        found.append(
            validate_question(
                row.get("label"),
                row.get("style", SHORT),
                row.get("required", True),
                row.get("placeholder"),
                position=at,
            )
        )
    return found


def answers_json(fields: Any) -> str:
    """The snapshot: labels travel with the answers, so editing a question never rewrites it."""
    found = []
    for label, answer in fields or ():
        found.append(
            {"label": str(label)[:LABEL_MAX], "answer": str(answer or "")[:ANSWER_INPUT_MAX]}
        )
    return json.dumps(found)


def read_answers(raw: Any) -> list[dict[str, str]]:
    if isinstance(raw, list):
        found = raw
    else:
        try:
            found = json.loads(raw or "[]")
        except (TypeError, ValueError):
            log.warning("applications: an answers snapshot was unreadable and shows as empty")
            return []
    if not isinstance(found, list):
        return []
    return [
        {"label": str(one.get("label", "")), "answer": str(one.get("answer", ""))}
        for one in found
        if isinstance(one, dict)
    ]


def form_value(form: Any, key: str, default: Any = None) -> Any:
    """A column an older row may not carry; a fixture shaped like a dict works too."""
    try:
        found = form[key]
    except (KeyError, IndexError, TypeError):
        return default
    return default if found is None else found


def role_of(form: Any) -> int | None:
    """The role an approval hands over, or None when the form only keeps a list."""
    found = form_value(form, "role_id")
    try:
        return int(found) if found else None
    except (TypeError, ValueError):
        return None


def retry_days_of(form: Any, fallback: Any = RETRY_DAYS_DEFAULT) -> int:
    try:
        days = int(form_value(form, "retry_days", fallback))
    except (TypeError, ValueError):
        days = RETRY_DAYS_DEFAULT
    return max(0, min(days, DAYS_MAX))


def expires_days_of(form: Any) -> int | None:
    try:
        days = int(form_value(form, "expires_days", 0) or 0)
    except (TypeError, ValueError):
        return None
    return min(days, DAYS_MAX) if days > 0 else None


def is_open(form: Any) -> bool:
    return bool(form_value(form, "open", 1))


def approved_text_of(form: Any) -> str:
    return str(form_value(form, "approved_text", DEFAULT_APPROVED_TEXT))


def next_step_of(form: Any) -> str:
    return str(form_value(form, "next_step", "") or "")


def owner_of(form: Any) -> int | None:
    found = form_value(form, "owner_user_id")
    try:
        return int(found) if found else None
    except (TypeError, ValueError):
        return None


def owner_nudge(form: Any) -> str:
    """The named human step after an approval; empty when the form asks for none."""
    step = next_step_of(form)
    if not step:
        return ""
    owner = owner_of(form)
    if owner is None:
        return NEXT_STEP_UNOWNED.format(next_step=step)
    return OWNER_NUDGE.format(owner_id=owner, next_step=step)


def render_card(form: Any, row: Any, member: Any = None, answers: Any = None) -> discord.Embed:
    """One place turns a stored application into the card every surface shows."""
    found = read_answers(answers if answers is not None else form_value(row, "answers", "[]"))
    who = form_value(row, "user_id")
    role = role_of(form)
    title = str(form_value(form, "title", "?"))
    embed = discord.Embed(
        title=CARD_HEADING.format(application_id=form_value(row, "id", "?"), title=title),
        description=(
            f"<@{who}> applied for <@&{role}>" if role else f"<@{who}> applied for **{title}**"
        ),
    )
    name = getattr(member, "display_name", None)
    if name:
        embed.add_field(name="Applicant", value=str(name)[:256], inline=True)
    embed.add_field(name="Sent", value=stamp(form_value(row, "submitted_at"), "R"), inline=True)
    embed.add_field(name="Status", value=str(form_value(row, "status", PENDING)), inline=True)
    for one in found:
        embed.add_field(
            name=str(one["label"])[:256] or "—",
            value=(one["answer"] or NO_ANSWER)[:ANSWER_MAX],
            inline=False,
        )
    if form_value(row, "decided_by"):
        embed.add_field(
            name="Decided by", value=f"<@{form_value(row, 'decided_by')}>", inline=True
        )
    if form_value(row, "deny_reason"):
        embed.add_field(
            name="Reason", value=str(form_value(row, "deny_reason"))[:ANSWER_MAX], inline=False
        )
    embed.set_footer(text=f"#{form_value(row, 'id', '?')} · {form_value(form, 'name', '?')}")
    return embed


def decision_lines(
    form: Any,
    row: Any,
    *,
    guild_name: str = "the server",
    member_name: Any = None,
    until: Any = None,
    granted: bool | None = True,
) -> tuple[str, str]:
    """(what the card and the decider are told, what the applicant is DM'd)."""
    status = str(form_value(row, "status", PENDING))
    title = str(form_value(form, "title", "?"))
    role = role_of(form)
    if status == APPROVED:
        extra = EXPIRES_EXTRA.format(stamp=stamp(until)) if until and role else ""
        if role:
            said = APPROVED_SAID.format(
                name=member_name or form_value(row, "user_id"),
                role=f"<@&{role}>",
                extra=extra,
            )
            if granted is False:
                said = f"{said} {GRANT_FAILED_ON_CARD}"
        else:
            said = APPROVED_ON_RECORD.format(
                name=member_name or form_value(row, "user_id"), title=title
            )
        nudge = owner_nudge(form)
        card = f"{said} {nudge}".strip()
        body = f"{approved_text_of(form)}{extra}"
        step = next_step_of(form)
        if step:
            body = f"{body} Next: {step}"
        return card, DM_APPROVED.format(title=title, guild=guild_name, said=body.strip())
    if status == DENIED:
        when = retry_at(form_value(row, "decided_at"), retry_days_of(form))
        return (
            DENIED_SAID,
            DM_DENIED.format(
                title=title,
                guild=guild_name,
                reason=str(form_value(row, "deny_reason", "none given")),
                stamp=stamp(when) if when else "whenever you like",
            ),
        )
    if status == REMOVED:
        when = retry_at(form_value(row, "decided_at"), retry_days_of(form))
        return (
            REMOVED_SAID,
            DM_REMOVED.format(
                title=title,
                guild=guild_name,
                reason=str(form_value(row, "deny_reason", "none given")),
                stamp=stamp(when) if when else "whenever you like",
            ),
        )
    if status == WITHDRAWN:
        return WITHDRAWN_SAID, ""
    return "", ""


def application_id_from(text: Any) -> int | None:
    """`#12`, `12` or ` #12 ` — the number on a card, or None when it is not one."""
    found = str(text or "").strip().lstrip("#").strip()
    if not found.isdigit():
        return None
    try:
        return int(found)
    except ValueError:
        return None


def panel_minutes(store: Any, guild_id: int) -> int:
    return library_panel_minutes(store, guild_id, PANEL_MINUTES_KEY)


def panel_shows_own_list(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, PANEL_OWN_LIST_KEY))


def site_page_url(origin: Any) -> str | None:
    text = str(origin or "").strip()
    if not text:
        return None
    return f"{text.rstrip('/')}/{FEATURE_PAGES['applications']}"


def own_lines(rows: Any, forms_by_id: Any) -> list[str]:
    """A member's own applications, one line each — the block the panel writes for them."""
    found = []
    for row in rows or ():
        form = (forms_by_id or {}).get(form_value(row, "form_id"))
        extra = STATUS_WAITING if form_value(row, "status") == PENDING else ""
        if form_value(row, "deny_reason"):
            extra = f" — {form_value(row, 'deny_reason')}"
        found.append(
            YOUR_APPLICATION.format(
                title=form_value(form, "title", f"form #{form_value(row, 'form_id')}"),
                status=form_value(row, "status"),
                extra=extra,
            )
        )
    return found


def form_lines(forms_: Any) -> list[str]:
    """One line per form: whether it is open, and what an approval hands over."""
    found = []
    for one in forms_ or ():
        role = role_of(one)
        found.append(
            f"**{form_value(one, 'name')}** — {'open' if is_open(one) else 'closed'}, "
            f"{f'<@&{role}>' if role else 'list'}"
        )
    return found


def application_lines(rows: Any, names: Any, listed: Any = (), logins: Any = None) -> list[str]:
    """The queue, one line each; a Twitch login rides along where the form keeps a list."""
    known = logins or {}
    on_a_list = set(listed or ())
    found = []
    for row in rows or ():
        who = form_value(row, "user_id")
        form_id = form_value(row, "form_id")
        extra = (
            f" · twitch.tv/{known[who]}"
            if form_id in on_a_list
            and form_value(row, "status") == APPROVED
            and who in known
            else ""
        )
        found.append(
            f"`#{form_value(row, 'id')}` <@{who}> · {(names or {}).get(form_id, '?')} · "
            f"{form_value(row, 'status')} · {stamp(form_value(row, 'submitted_at'), 'R')}{extra}"
        )
    return found


def question_lines(rows: Any) -> list[str]:
    found = []
    for row in rows or ():
        optional = "" if form_value(row, "required") else ", optional"
        found.append(
            f"**{form_value(row, 'position')}.** {form_value(row, 'label')} — "
            f"{form_value(row, 'style')}{optional}"
        )
    return found


def counts_of(rows: Any) -> dict[str, int]:
    found = dict.fromkeys(STATUSES, 0)
    for row in rows or ():
        status = str(form_value(row, "status", ""))
        if status in found:
            found[status] += 1
    return found


def counts_line(forms_: Any, rows: Any) -> str:
    counts = counts_of(rows)
    return COUNTS_LINE.format(
        forms=len(list(forms_ or ())), waiting=counts[PENDING], approved=counts[APPROVED]
    )


async def create_form(
    db: Any,
    guild_id: int,
    name: str,
    title: str,
    role_id: int | None,
    created_by: int,
    *,
    description: Any = None,
    review_channel_id: Any = None,
    approver_role_id: Any = None,
) -> int | None:
    """The form's row id, or None when that name is already taken in this guild."""
    slug = check_name(name)
    heading = check_title(title)
    if description is not None:
        check_length("description", str(description), DESCRIPTION_MAX)
    if await get_form(db, guild_id, slug) is not None:
        return None
    at = now_iso()
    cur = await db.conn.execute(
        "INSERT INTO application_forms(guild_id, name, title, description, role_id, "
        "review_channel_id, approver_role_id, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            guild_id,
            slug,
            heading,
            str(description) if description else None,
            int(role_id) if role_id else None,
            int(review_channel_id) if review_channel_id else None,
            int(approver_role_id) if approver_role_id else None,
            int(created_by),
            at,
            at,
        ),
    )
    await db.conn.commit()
    return cur.lastrowid


async def get_form(db: Any, guild_id: int, name: str) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM application_forms WHERE guild_id = ? AND name = ?",
        (guild_id, str(name or "").strip().lower()),
    )
    return await cur.fetchone()


async def get_form_by_id(db: Any, form_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM application_forms WHERE id = ?", (form_id,))
    return await cur.fetchone()


async def list_forms(db: Any, guild_id: int, *, open_only: bool = False) -> list[Any]:
    sql = "SELECT * FROM application_forms WHERE guild_id = ?"
    if open_only:
        sql += " AND open = 1"
    cur = await db.conn.execute(sql + " ORDER BY name", (guild_id,))
    return list(await cur.fetchall())


FORM_FIELDS = (
    "title",
    "description",
    "role_id",
    "review_channel_id",
    "approver_role_id",
    "owner_user_id",
    "next_step",
    "approved_text",
    "expires_days",
    "retry_days",
    "open",
)
CLEARABLE_IDS = ("role_id", "review_channel_id", "approver_role_id", "owner_user_id")


async def update_form(db: Any, guild_id: int, name: str, **changes: Any) -> bool:
    """Change one form; whatever is not named is left exactly as it is."""
    form = await get_form(db, guild_id, name)
    if form is None:
        return False
    wanted = {key: value for key, value in changes.items() if value is not None}
    for key in CLEARABLE_IDS:
        if wanted.get(key) == NO_ROLE:
            wanted[key] = None
    if "title" in wanted:
        wanted["title"] = check_title(wanted["title"])
    if "description" in wanted:
        wanted["description"] = (
            check_length("description", str(wanted["description"]), DESCRIPTION_MAX) or None
        )
    for key in ("next_step", "approved_text"):
        if key in wanted:
            wanted[key] = check_length(key.replace("_", " "), str(wanted[key]), TEXT_MAX) or None
    if "expires_days" in wanted:
        wanted["expires_days"] = whole_days(wanted["expires_days"])
    if "retry_days" in wanted:
        wanted["retry_days"] = whole_days(wanted["retry_days"])
    if "open" in wanted:
        wanted["open"] = int(bool(wanted["open"]))
    kept = {key: value for key, value in wanted.items() if key in FORM_FIELDS}
    if not kept:
        return True
    sets = ", ".join(
        f"{key} = NULL" if value is None else f"{key} = ?" for key, value in kept.items()
    )
    values = tuple(value for value in kept.values() if value is not None)
    await db.conn.execute(
        f"UPDATE application_forms SET {sets}, updated_at = ? WHERE id = ?",
        (*values, now_iso(), form["id"]),
    )
    await db.conn.commit()
    return True


async def delete_form(db: Any, form_id: int) -> None:
    await db.conn.execute("DELETE FROM application_questions WHERE form_id = ?", (form_id,))
    await db.conn.execute("DELETE FROM application_forms WHERE id = ?", (form_id,))
    await db.conn.commit()


async def set_panel(db: Any, form_id: int, channel_id: Any, message_id: Any) -> None:
    await db.conn.execute(
        "UPDATE application_forms SET panel_channel_id = ?, panel_message_id = ?, "
        "updated_at = ? WHERE id = ?",
        (channel_id, message_id, now_iso(), form_id),
    )
    await db.conn.commit()


async def questions_for(db: Any, form_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM application_questions WHERE form_id = ? ORDER BY position",
        (form_id,),
    )
    return list(await cur.fetchall())


async def add_question(
    db: Any,
    form_id: int,
    label: Any,
    style: Any = SHORT,
    required: Any = True,
    placeholder: Any = None,
) -> int:
    """The slot the question landed in; the next free one, and never past Discord's five."""
    held = await questions_for(db, form_id)
    if len(held) >= QUESTIONS_MAX:
        raise ApplicationError(
            TOO_MANY_QUESTIONS.format(limit=QUESTIONS_MAX, given=len(held) + 1)
        )
    row = validate_question(label, style, required, placeholder)
    taken = {int(one["position"]) for one in held}
    position = next(at for at in range(1, QUESTIONS_MAX + 1) if at not in taken)
    await db.conn.execute(
        "INSERT INTO application_questions(form_id, position, label, style, required, "
        "placeholder) VALUES (?, ?, ?, ?, ?, ?)",
        (form_id, position, row["label"], row["style"], row["required"], row["placeholder"]),
    )
    await db.conn.commit()
    return position


async def edit_question(db: Any, form_id: int, position: Any, **changes: Any) -> bool:
    slot = check_position(position)
    cur = await db.conn.execute(
        "SELECT * FROM application_questions WHERE form_id = ? AND position = ?",
        (form_id, slot),
    )
    held = await cur.fetchone()
    if held is None:
        return False
    row = validate_question(
        changes.get("label") if changes.get("label") is not None else held["label"],
        changes.get("style") if changes.get("style") is not None else held["style"],
        changes.get("required") if changes.get("required") is not None else held["required"],
        (
            changes.get("placeholder")
            if changes.get("placeholder") is not None
            else held["placeholder"]
        ),
    )
    await db.conn.execute(
        "UPDATE application_questions SET label = ?, style = ?, required = ?, placeholder = ? "
        "WHERE form_id = ? AND position = ?",
        (row["label"], row["style"], row["required"], row["placeholder"], form_id, slot),
    )
    await db.conn.commit()
    return True


async def remove_question(db: Any, form_id: int, position: Any) -> bool:
    slot = check_position(position)
    cur = await db.conn.execute(
        "DELETE FROM application_questions WHERE form_id = ? AND position = ?", (form_id, slot)
    )
    await db.conn.commit()
    return bool(cur.rowcount)


async def replace_questions(db: Any, form_id: int, items: Any) -> list[dict[str, Any]]:
    """The whole ordered list at once — the dashboard's editor saves this way."""
    rows = validate_questions(items)
    await db.conn.execute("DELETE FROM application_questions WHERE form_id = ?", (form_id,))
    for row in rows:
        await db.conn.execute(
            "INSERT INTO application_questions(form_id, position, label, style, required, "
            "placeholder) VALUES (?, ?, ?, ?, ?, ?)",
            (
                form_id,
                row["position"],
                row["label"],
                row["style"],
                row["required"],
                row["placeholder"],
            ),
        )
    await db.conn.commit()
    return rows


async def create_application(
    db: Any, guild_id: int, form_id: int, user_id: int, answers: str
) -> int | None:
    """The new application's id, or None when one is already open for that person and form."""
    if await open_application(db, form_id, user_id) is not None:
        return None
    try:
        cur = await db.conn.execute(
            "INSERT INTO applications(guild_id, form_id, user_id, answers, status, submitted_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, form_id, user_id, answers, PENDING, now_iso()),
        )
    except sqlite3.IntegrityError:
        log.info("applications: %s already had one open on form %s", user_id, form_id)
        return None
    await db.conn.commit()
    return cur.lastrowid


async def get_application(db: Any, application_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM applications WHERE id = ?", (application_id,))
    return await cur.fetchone()


async def open_application(db: Any, form_id: int, user_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM applications WHERE form_id = ? AND user_id = ? AND status = ?",
        (form_id, user_id, PENDING),
    )
    return await cur.fetchone()


async def last_decision(db: Any, form_id: int, user_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM applications WHERE form_id = ? AND user_id = ? AND status IN (?, ?, ?) "
        "ORDER BY id DESC LIMIT 1",
        (form_id, user_id, APPROVED, DENIED, REMOVED),
    )
    return await cur.fetchone()


async def twitch_logins_for(db: Any, user_ids: Any) -> dict[int, str]:
    """One query for the whole roster, so a list of thirty is not thirty round trips."""
    wanted = list(dict.fromkeys(int(one) for one in user_ids or ()))
    if not wanted:
        return {}
    marks = ", ".join("?" for _ in wanted)
    cur = await db.conn.execute(
        f"SELECT user_id, twitch_login FROM golive_links WHERE user_id IN ({marks})", wanted
    )
    return {
        int(row["user_id"]): str(row["twitch_login"])
        for row in await cur.fetchall()
        if row["twitch_login"]
    }


async def applications_for(
    db: Any,
    guild_id: int,
    *,
    form_id: int | None = None,
    user_id: int | None = None,
    statuses: Any = None,
    limit: int = 200,
) -> list[Any]:
    """Pending first, newest first inside each group — the order the queue is worked in."""
    wanted = tuple(statuses or STATUSES)
    marks = ", ".join("?" for _ in wanted)
    sql = f"SELECT * FROM applications WHERE guild_id = ? AND status IN ({marks})"
    args: tuple[Any, ...] = (guild_id, *wanted)
    if form_id is not None:
        sql += " AND form_id = ?"
        args += (form_id,)
    if user_id is not None:
        sql += " AND user_id = ?"
        args += (user_id,)
    cur = await db.conn.execute(
        sql + " ORDER BY (status = 'pending') DESC, id DESC LIMIT ?", (*args, limit)
    )
    return list(await cur.fetchall())


async def pending_count(db: Any, form_id: int) -> int:
    cur = await db.conn.execute(
        "SELECT COUNT(*) AS n FROM applications WHERE form_id = ? AND status = ?",
        (form_id, PENDING),
    )
    return int((await cur.fetchone())["n"])


async def decide_application(
    db: Any,
    application_id: int,
    status: str,
    *,
    decided_by: int | None = None,
    deny_reason: str | None = None,
) -> bool:
    """One writer wins: the update only lands while the application is still pending."""
    if not may_move(PENDING, status):
        raise ApplicationError(f"{status!r} is not somewhere a pending application may go")
    cur = await db.conn.execute(
        "UPDATE applications SET status = ?, decided_by = ?, decided_at = ?, deny_reason = ? "
        "WHERE id = ? AND status = ?",
        (status, decided_by, now_iso(), deny_reason, application_id, PENDING),
    )
    await db.conn.commit()
    return bool(cur.rowcount)


async def remove_application(
    db: Any, application_id: int, *, decided_by: int | None = None, reason: str | None = None
) -> bool:
    """Off an approved list, and only off an approved one: staff's way back out of a yes."""
    said = str(reason or "").strip()
    if not said:
        raise ApplicationError(REMOVE_NEEDS_A_REASON)
    cur = await db.conn.execute(
        "UPDATE applications SET status = ?, decided_by = ?, decided_at = ?, deny_reason = ? "
        "WHERE id = ? AND status = ?",
        (REMOVED, decided_by, now_iso(), said, application_id, APPROVED),
    )
    await db.conn.commit()
    return bool(cur.rowcount)


async def restore_application(
    db: Any, application_id: int, *, decided_by: int | None = None
) -> bool:
    """Staff's exit from a no: denied or taken-off goes back to approved, and only from those."""
    if not RESTORABLE:
        raise ApplicationError("nothing may be approved after the fact")
    marks = ", ".join("?" for _ in RESTORABLE)
    cur = await db.conn.execute(
        f"UPDATE applications SET status = ?, decided_by = ?, decided_at = ?, deny_reason = NULL "
        f"WHERE id = ? AND status IN ({marks})",
        (APPROVED, decided_by, now_iso(), application_id, *RESTORABLE),
    )
    await db.conn.commit()
    return bool(cur.rowcount)


async def set_card(db: Any, application_id: int, channel_id: Any, message_id: Any) -> None:
    await db.conn.execute(
        "UPDATE applications SET card_channel_id = ?, card_message_id = ? WHERE id = ?",
        (channel_id, message_id, application_id),
    )
    await db.conn.commit()


async def set_grant(db: Any, application_id: int, grant_id: Any) -> None:
    await db.conn.execute(
        "UPDATE applications SET grant_id = ? WHERE id = ?", (grant_id, application_id)
    )
    await db.conn.commit()


async def cooling_until(db: Any, form: Any, user_id: int, retry_days: Any = None) -> Any:
    """When they may apply again, or None when they already may."""
    last = await last_decision(db, form["id"], user_id)
    if last is None:
        return None
    days = retry_days_of(form) if retry_days is None else retry_days
    return still_cooling(last["decided_at"], days)


__all__ = [
    "APPROVER_ROLE_KEY",
    "CARD_BUTTONS",
    "CHANNEL_KEY",
    "COUNTS_LINE",
    "DAYS_MAX",
    "DM_KEY",
    "LABEL_MAX",
    "LONG",
    "MODES",
    "MODE_KEY",
    "MOVE_TARGETS",
    "NOTHING_OF_YOURS",
    "NOTHING_TO_SHOW",
    "NOT_A_NUMBER",
    "NOT_REINSTATABLE",
    "NO_ROLE",
    "PANEL_INTRO",
    "PANEL_MINUTES_KEY",
    "PANEL_OWN_LIST_KEY",
    "PANEL_TIMEOUT_FOOTER",
    "PANEL_TITLE",
    "PING_ROLE_KEY",
    "PLACEHOLDER_MAX",
    "QUESTIONS_MAX",
    "REINSTATED_SAID",
    "REMOVED",
    "RESTORABLE",
    "RETRY_DAYS_DEFAULT",
    "RETRY_DAYS_KEY",
    "ROSTER_SHOWS_LEFT_KEY",
    "SETTLED",
    "SHORT",
    "SITE_BUTTON",
    "STATUSES",
    "STATUS_WAITING",
    "STYLES",
    "TRANSITIONS",
    "WITHDRAWN_IS_THEIRS",
    "YOUR_APPLICATION",
    "ApplicationError",
    "MoveButton",
    "add_question",
    "answers_json",
    "application_id_from",
    "application_lines",
    "applications_for",
    "approved_text_of",
    "card_buttons",
    "counts_line",
    "counts_of",
    "check_name",
    "check_position",
    "check_style",
    "check_title",
    "clamp",
    "cooling_until",
    "create_application",
    "create_form",
    "decide_application",
    "decision_lines",
    "delete_form",
    "edit_question",
    "expires_days_of",
    "form_lines",
    "form_value",
    "get_application",
    "get_form",
    "get_form_by_id",
    "is_open",
    "last_decision",
    "list_forms",
    "may_move",
    "next_step_of",
    "open_application",
    "own_lines",
    "owner_nudge",
    "owner_of",
    "panel_minutes",
    "panel_shows_own_list",
    "pending_count",
    "positive_days",
    "question_lines",
    "questions_for",
    "read_answers",
    "remove_application",
    "remove_question",
    "render_card",
    "replace_questions",
    "restore_application",
    "retry_days_of",
    "role_of",
    "set_card",
    "site_page_url",
    "set_grant",
    "set_panel",
    "twitch_logins_for",
    "update_form",
    "validate_question",
    "validate_questions",
    "whole_days",
]
