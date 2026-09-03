from __future__ import annotations

import logging
import re
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from ... import applications as forms
from ... import rolegrants as grants
from ...actionlog import log_action, send_logs
from ...command_errors import AnswersErrors, SafeDynamicItem
from ...logkinds import VIA_DISCORD, kind_via
from ...panels import (
    NoteModal,
    Panel,
    answer,
    capped_placeholder,
    db_ready,
    retire,
    still_staff,
)
from ...settings_store import DB_UNAVAILABLE, GUILD_ONLY, require_staff
from .role_menus import card_target, change_roles, dm, ping_mentions

log = logging.getLogger(__name__)

FEATURE = "applications"
COG_NAME = "Applications"
APPLY_TEMPLATE = r"applyform:(?P<form_id>[0-9]+)"
DECIDE_TEMPLATE = r"application:(?P<application_id>[0-9]+):(?P<action>approve|deny)"
SHADOW = "shadow"
ON = "on"
SELECT_CAP = 25
COUNT_LIMIT = 500

APPROVAL_FALLBACK_CHANNEL_KEY = "rolemenu_approval_channel_id"
APPROVAL_FALLBACK_ROLE_KEY = "rolemenu_approver_role_id"
STAFF_CHANNEL_KEY = "staff_channel_id"
PANEL_MINUTES_KEY = forms.PANEL_MINUTES_KEY
ROSTER_SHOWS_LEFT_KEY = forms.ROSTER_SHOWS_LEFT_KEY
PANEL_TIMEOUT_FOOTER = forms.PANEL_TIMEOUT_FOOTER
TAKE_OFF_LABEL = "Take off the list"
TAKE_OFF_MODAL_TITLE = "Take them off the list?"
TAKE_OFF_MODAL_LABEL = "One line they will be sent"
DENY_MODAL_TITLE = "Why not?"
DENY_MODAL_LABEL = "One line the applicant will be sent"

NOT_IN_GUILD = (
    "Applications only work inside the server, and this did not come from one, so nothing was "
    "sent. Open the form in a server channel and try again."
)
NOT_AN_APPROVER = (
    "Deciding an application needs <@&{role_id}>, so nothing was changed. Ask somebody who has "
    "that role, or a Lead can point **{name}** at a different one from `/apply` → **A form…** "
    "→ **Edit…**."
)
PANEL_BODY = (
    "**{title}**\n{description}\nPress **Apply** to fill the form in. Staff look at every one "
    "and you get a DM either way."
)
PANEL_POSTED = (
    "The Apply button for **{name}** is up in <#{channel_id}>. Post it again to move it."
)
FORM_CREATED = (
    "Created **{name}**. Put its questions on it with **Questions…** — up to {limit} — then put "
    "the button up with **Post the Apply button**."
)
FORM_SAVED = "Saved **{name}**."
FORM_DELETED = (
    "Deleted **{name}** and its questions. Nobody loses a role they already have, and the "
    "applications already decided stay on the record."
)
QUESTION_ADDED = "Added **{label}** to **{name}** as question {position}."
QUESTION_SAVED = "Saved question {position} on **{name}**."
QUESTION_REMOVED = (
    "Removed question {position} from **{name}**. Answers already sent keep the wording they "
    "were asked in."
)
NO_SUCH_QUESTION = (
    "**{name}** has nothing in slot {position}, so nothing was changed. The list above says "
    "which slots are filled."
)
NOTHING_OF_YOURS = forms.NOTHING_OF_YOURS
YOUR_APPLICATION = forms.YOUR_APPLICATION
STATUS_WAITING = forms.STATUS_WAITING
NOTHING_TO_SHOW = forms.NOTHING_TO_SHOW
REMOVE_IS_FOR_LISTS = (
    "**{name}** hands over <@&{role}>, so there is no list to take them off; `/role revoke` "
    "takes the role back and ends the grant — the approval stays on record."
)
MODE_SAID = {
    "off": (
        "Off. `/apply` still opens, but it says applications are off and offers nobody a form; "
        "the Apply buttons stop working, and nothing is posted or DMed. Nobody loses a role and "
        "no form is changed."
    ),
    SHADOW: (
        "Shadow. Applications are still written down and still show on the dashboard, but no "
        "card is posted, no DM is sent and no role is handed over — the log says what would "
        "have happened."
    ),
    ON: "On. Members can apply, staff decide on the card, and an approval hands the role over.",
}

PANEL_STAFF_ONLY_LINE = "Making and changing forms is for staff."
APPLY_COMMAND_DESCRIPTION = "Apply for something — staff manage the forms here too"
NOTHING_OPEN_TO_APPLY_FOR = "No form is open for applications right now."
NOTHING_WAITING = forms.NOTHING_PENDING
FIND_TITLE = "Find an application"
FIND_LABEL = "The number on the card, like #12"
FIND_LIMIT = 12
NEW_FORM_TITLE = "A new application form"
WORDS_TITLE = "The words on {name}"
NUMBERS_TITLE = "The numbers on {name}"
SETTINGS_NUMBERS_TITLE = "Applications — the numbers"
QUESTION_TITLE = "Question {position} on {name}"
ADD_QUESTION_TITLE = "A new question on {name}"
DELETE_CONFIRM = (
    "Delete **{name}** and its {questions} question(s)? Nobody loses a role they already have."
)
REMOVE_QUESTION_CONFIRM = "Remove question {position}, **{label}**, from **{name}**?"
REORDER_IS_ON_THE_SITE = (
    "Questions are asked in the order below. Dragging them into a different order is on the "
    "Role menus page — Discord has nothing to drag with."
)
ROSTER_EMPTY = "Nobody is on this list yet."
ROSTER_LINE = "<@{user_id}>{gone}{twitch} · on since {stamp}"
ROSTER_GONE = " (left the server)"
NO_QUESTIONS_LINE = "No questions on it yet, so nobody can apply for it."
POST_WHERE = "Where does the Apply button go?"
FILL_IT_IN = "Fill it in"
PICK_A_QUESTION = "A question…"
TAKE_SOMEBODY_OFF = "Take somebody off…"
SETTINGS_TITLE = "Applications — settings"
SETTINGS_MODE_PICK = "Mode…"
SETTINGS_CHANNEL_PICK = "Where cards wait…"
SETTINGS_APPROVER_PICK = "Who decides…"
SETTINGS_PING_PICK = "Who is pinged…"
EDIT_ROLE_PICK = "Role it hands over…"
EDIT_CHANNEL_PICK = "Where its cards wait…"
EDIT_APPROVER_PICK = "Who decides it…"
EDIT_OWNER_PICK = "Who is nudged next…"
CLEARED_BY_EMPTY = "Pick nobody to clear it."
YES_NO = ("yes", "no")
STYLE_HINT = "short or long"
REQUIRED_HINT = "yes or no"


def mode_of(bot: Any, guild_id: int) -> str:
    found = bot.store.get(guild_id, forms.MODE_KEY)
    return found if found in forms.MODES else "off"


def is_on(bot: Any, guild_id: int) -> bool:
    return mode_of(bot, guild_id) in (SHADOW, ON)


def is_live(bot: Any, guild_id: int) -> bool:
    return mode_of(bot, guild_id) == ON


def review_channel(bot: Any, guild: Any, form: Any) -> Any:
    """Where a card waits: the form's own channel, then the two settings, then staff."""
    channel_id = (
        forms.form_value(form, "review_channel_id")
        or bot.store.get(guild.id, forms.CHANNEL_KEY)
        or bot.store.get(guild.id, APPROVAL_FALLBACK_CHANNEL_KEY)
        or bot.store.get(guild.id, STAFF_CHANNEL_KEY)
    )
    if not channel_id:
        return None
    return bot.get_channel(int(channel_id)) or guild.get_channel(int(channel_id))


def approver_role_id(bot: Any, guild_id: int, form: Any) -> int | None:
    found = (
        forms.form_value(form, "approver_role_id")
        or bot.store.get(guild_id, forms.APPROVER_ROLE_KEY)
        or bot.store.get(guild_id, APPROVAL_FALLBACK_ROLE_KEY)
    )
    try:
        return int(found) if found else None
    except (TypeError, ValueError):
        return None


def holds_role(member: Any, role_id: int | None) -> bool:
    if role_id is None:
        return False
    return any(getattr(role, "id", None) == role_id for role in getattr(member, "roles", ()))


def can_decide(bot: Any, guild_id: int, form: Any, user: Any) -> bool:
    """The same question `may_decide` asks, with no refusal sent — for rendering a button."""
    if holds_role(user, approver_role_id(bot, guild_id, form)):
        return True
    return bool(bot.store.is_staff(user))


async def may_decide(interaction: discord.Interaction, form: Any) -> bool:
    """The approver role decides; with none set, staff do. A refusal names what it needs."""
    bot = interaction.client
    guild = interaction.guild
    if guild is None:
        await answer(interaction, NOT_IN_GUILD)
        return False
    role_id = approver_role_id(bot, guild.id, form)
    if holds_role(interaction.user, role_id):
        return True
    if bot.store.is_staff(interaction.user):
        return True
    if role_id is not None:
        await answer(
            interaction,
            NOT_AN_APPROVER.format(
                role_id=role_id, name=forms.form_value(form, "name", "the form")
            ),
        )
        return False
    return await require_staff(interaction)


def dms_on(bot: Any, guild_id: int) -> bool:
    return bool(bot.store.get(guild_id, forms.DM_KEY))


def retry_days_for(bot: Any, guild_id: int, form: Any) -> int:
    """The form's own wait, or the server-wide one when the form does not say."""
    own = forms.form_value(form, "retry_days")
    if own is None:
        return forms.retry_days_of(form, bot.store.get(guild_id, forms.RETRY_DAYS_KEY))
    return forms.retry_days_of(form)


def panel_view(form_id: int) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(ApplyButton(form_id))
    return view


def decision_view(application_id: int) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(DecisionButton(application_id, "approve"))
    view.add_item(DecisionButton(application_id, "deny"))
    return view


def panel_embed(form: Any) -> discord.Embed:
    embed = discord.Embed(
        title=str(forms.form_value(form, "title", "Apply")),
        description=str(forms.form_value(form, "description", "") or "") or None,
    )
    days = forms.expires_days_of(form)
    if days:
        embed.add_field(
            name="If you are approved",
            value=f"The role lasts {days} day(s), then Black Bloc takes it back.",
            inline=False,
        )
    return embed


async def send_dm(bot: Any, guild: Any, member: Any, text: str, details: dict[str, Any]) -> None:
    """One place decides whether a DM goes out, and says in the log when it did not."""
    if not text or member is None:
        return
    if not dms_on(bot, guild.id):
        return
    if mode_of(bot, guild.id) == SHADOW:
        await log_action(bot, guild, "application.would_dm", target=member, details=details)
        return
    if not await dm(member, text):
        await log_action(bot, guild, "application.dm_failed", target=member, details=details)


async def post_card(bot: Any, guild: Any, form: Any, row: Any, member: Any) -> tuple[Any, str]:
    """Where the card actually went, so the applicant's reply can say so."""
    details = {"application_id": row["id"], "form": forms.form_value(form, "name")}
    if mode_of(bot, guild.id) == SHADOW:
        await log_action(bot, guild, "application.would_post", details=details)
        return None, SHADOW
    target, where = card_target(bot, review_channel(bot, guild, form))
    if target is None:
        await log_action(
            bot, guild, "application.post_failed", details=details | {"reason": where}
        )
        return None, where
    if where == "test_channel":
        await log_action(bot, guild, "application.post_skipped_test_mode", details=details)
    role_id = bot.store.get(guild.id, forms.PING_ROLE_KEY)
    try:
        message = await target.send(
            f"<@&{role_id}>" if role_id else None,
            embed=forms.render_card(form, row, member),
            view=decision_view(row["id"]),
            allowed_mentions=ping_mentions(role_id),
        )
    except Exception as exc:
        log.warning("applications: could not post the card for %s: %s", row["id"], exc)
        await log_action(
            bot,
            guild,
            "application.post_failed",
            details=details | {"reason": f"{type(exc).__name__}: {exc}"},
        )
        return None, "failed"
    await forms.set_card(bot.db, row["id"], target.id, message.id)
    return message, where


def nudge_mentions(form: Any) -> discord.AllowedMentions:
    """The one person a decided card may ping: the owner the form names for the next step."""
    owner = forms.owner_of(form)
    if owner is None:
        return discord.AllowedMentions.none()
    return discord.AllowedMentions(
        everyone=False, roles=False, users=[discord.Object(id=owner)]
    )


async def edit_card(bot: Any, guild: Any, form: Any, row: Any, said: str) -> None:
    """Cosmetic, and last: a failure here never undoes the decision above it."""
    channel_id = forms.form_value(row, "card_channel_id")
    message_id = forms.form_value(row, "card_message_id")
    if not channel_id or not message_id:
        return
    channel = bot.get_channel(int(channel_id)) or guild.get_channel(int(channel_id))
    if channel is None:
        log.info("applications: %s has no card channel any more", row["id"])
        return
    partial = getattr(channel, "get_partial_message", None)
    member = guild.get_member(forms.form_value(row, "user_id"))
    try:
        message = (
            partial(int(message_id))
            if partial is not None
            else await channel.fetch_message(int(message_id))
        )
        await message.edit(
            content=said or None,
            embed=forms.render_card(form, row, member),
            view=None,
            allowed_mentions=nudge_mentions(form),
        )
    except Exception as exc:
        log.warning("applications: could not close the card for %s: %s", row["id"], exc)


async def post_panel(bot: Any, guild: Any, form: Any, target: Any) -> Any:
    """The Apply button for one form; posting again moves it and takes the old one down."""
    message = await target.send(
        embed=panel_embed(form),
        view=panel_view(form["id"]),
        allowed_mentions=discord.AllowedMentions.none(),
    )
    await forms.set_panel(bot.db, form["id"], target.id, message.id)
    bot.add_view(panel_view(form["id"]), message_id=message.id)
    return message


async def submit_application(
    bot: Any, guild: Any, member: Any, form_id: int, fields: Any
) -> str:
    """The one place an application is written, carded and logged; returns what to say."""
    form = await forms.get_form_by_id(bot.db, form_id)
    if form is None or form["guild_id"] != guild.id:
        return forms.NOTHING_TO_DECIDE
    if not is_on(bot, guild.id):
        return forms.APPLICATIONS_OFF
    title = forms.form_value(form, "title", "?")
    if not forms.is_open(form):
        return forms.FORM_CLOSED.format(title=title, name=form["name"])
    if await forms.open_application(bot.db, form["id"], member.id) is not None:
        return forms.ALREADY_APPLIED.format(title=title)
    until = await forms.cooling_until(
        bot.db, form, member.id, retry_days_for(bot, guild.id, form)
    )
    if until is not None:
        last = await forms.last_decision(bot.db, form["id"], member.id)
        return forms.TOO_SOON.format(
            title=title,
            when=grants.stamp(last["decided_at"], "D"),
            stamp=grants.stamp(until),
        )
    application_id = await forms.create_application(
        bot.db, guild.id, form["id"], member.id, forms.answers_json(fields)
    )
    if application_id is None:
        return forms.ALREADY_APPLIED.format(title=title)
    row = await forms.get_application(bot.db, application_id)
    message, where = await post_card(bot, guild, form, row, member)
    await log_action(
        bot,
        guild,
        "application.submitted",
        actor=member,
        target=member,
        details={"application_id": application_id, "form": form["name"], "card": where},
    )
    await send_dm(
        bot,
        guild,
        member,
        forms.DM_RECEIVED.format(title=title, guild=guild.name),
        {"application_id": application_id, "form": form["name"]},
    )
    if message is None and where != SHADOW:
        return forms.CARD_NOT_POSTED.format(title=title)
    if where == "test_channel":
        return forms.SENT + forms.CARD_IN_TEST_CHANNEL
    return forms.SENT


async def withdraw_application(bot: Any, guild: Any, member: Any, form: Any) -> str:
    row = await forms.open_application(bot.db, form["id"], member.id)
    title = forms.form_value(form, "title", "?")
    if row is None:
        return forms.NOTHING_TO_WITHDRAW.format(title=title, name=form["name"])
    if not await forms.decide_application(
        bot.db, row["id"], grants.WITHDRAWN, decided_by=member.id
    ):
        fresh = await forms.get_application(bot.db, row["id"])
        return forms.ALREADY_DECIDED.format(status=fresh["status"])
    await log_action(
        bot,
        guild,
        "application.withdrawn",
        actor=member,
        target=member,
        details={"application_id": row["id"], "form": form["name"]},
    )
    fresh = await forms.get_application(bot.db, row["id"])
    card, _ = forms.decision_lines(form, fresh, guild_name=guild.name)
    await edit_card(bot, guild, form, fresh, card)
    return forms.WITHDRAWN_SAID


def actor_id(actor: Any) -> int | None:
    found = getattr(actor, "id", actor)
    return int(found) if isinstance(found, int) else None


async def apply_decision(
    bot: Any,
    guild: Any,
    application_id: int,
    status: str,
    actor: Any,
    *,
    reason: str | None = None,
    via: str = VIA_DISCORD,
) -> tuple[str, Any]:
    """Approve or deny, once, whoever wins the update: (what to say, the settled row)."""
    row = await forms.get_application(bot.db, application_id)
    if row is None:
        return forms.NOTHING_TO_DECIDE, None
    if row["guild_id"] != guild.id:
        return forms.NOT_THIS_SERVER, None
    if row["status"] != grants.PENDING:
        return forms.ALREADY_DECIDED.format(status=row["status"]), None
    form = await forms.get_form_by_id(bot.db, row["form_id"])
    if form is None:
        return forms.NOTHING_TO_DECIDE, None
    if status == grants.DENIED:
        return await _deny(bot, guild, form, row, actor, reason, via)
    member = guild.get_member(row["user_id"])
    if member is None:
        return forms.MEMBER_HAS_GONE.format(name=row["user_id"]), None
    return await _approve(bot, guild, form, row, member, actor, via)


async def _approve(
    bot: Any, guild: Any, form: Any, row: Any, member: Any, actor: Any, via: str
) -> tuple[str, Any]:
    if not await forms.decide_application(
        bot.db, row["id"], grants.APPROVED, decided_by=actor_id(actor)
    ):
        fresh = await forms.get_application(bot.db, row["id"])
        return forms.ALREADY_DECIDED.format(status=fresh["status"]), None
    return await settle_approval(bot, guild, form, row, member, actor, via)


async def settle_approval(
    bot: Any, guild: Any, form: Any, row: Any, member: Any, actor: Any, via: str
) -> tuple[str, Any]:
    """Everything a yes owes once the row says approved: the role, the log, the DM, the card."""
    role = forms.role_of(form)
    until = grants.expires_at(forms.expires_days_of(form)) if role else None
    details = {
        "application_id": row["id"],
        "form": form["name"],
        "role_id": role,
        "via": via,
    }
    fresh = await forms.get_application(bot.db, row["id"])
    granted = (
        await _hand_over(bot, guild, form, fresh, member, actor, until, details)
        if role
        else None
    )
    fresh = await forms.get_application(bot.db, row["id"])
    await log_action(
        bot,
        guild,
        kind_via("application.approved", via),
        actor=actor,
        target=member,
        details=details | {"expires_at": until, "granted": granted},
    )
    card, said = forms.decision_lines(
        form,
        fresh,
        guild_name=guild.name,
        member_name=getattr(member, "display_name", row["user_id"]),
        until=until,
        granted=granted,
    )
    await send_dm(bot, guild, member, said, details)
    await edit_card(bot, guild, form, fresh, card)
    if granted is False and is_live(bot, guild.id):
        return forms.ROLE_REFUSED_AFTER_DECISION.format(role=f"<@&{role}>"), fresh
    return card, fresh


async def reinstate(
    bot: Any, guild: Any, application_id: int, actor: Any, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    """Staff's exit from a no: a denied or taken-off application goes back to approved."""
    row = await forms.get_application(bot.db, application_id)
    if row is None:
        return forms.NOTHING_TO_DECIDE, None
    if row["guild_id"] != guild.id:
        return forms.NOT_THIS_SERVER, None
    if row["status"] not in forms.RESTORABLE:
        return forms.NOT_REINSTATABLE.format(status=row["status"]), None
    form = await forms.get_form_by_id(bot.db, row["form_id"])
    if form is None:
        return forms.NOTHING_TO_DECIDE, None
    member = guild.get_member(row["user_id"])
    if member is None and forms.role_of(form) is not None:
        return forms.MEMBER_HAS_GONE.format(name=row["user_id"]), None
    if not await forms.restore_application(
        bot.db, application_id, decided_by=actor_id(actor)
    ):
        fresh = await forms.get_application(bot.db, application_id)
        return forms.ALREADY_DECIDED.format(status=fresh["status"]), None
    _, fresh = await settle_approval(bot, guild, form, row, member, actor, via)
    return forms.REINSTATED_SAID.format(application_id=application_id), fresh


async def _hand_over(
    bot: Any,
    guild: Any,
    form: Any,
    row: Any,
    member: Any,
    actor: Any,
    until: Any,
    details: dict[str, Any],
) -> bool:
    """The role and its ledger row. Shadow says what it would do and does none of it."""
    if mode_of(bot, guild.id) == SHADOW:
        await log_action(bot, guild, "application.would_grant", target=member, details=details)
        return False
    held = holds_role(member, int(form["role_id"]))
    if not held and not await change_roles(
        bot, member, guild, {form["role_id"]}, set(), f"Black Bloc application approved by {actor}"
    ):
        await log_action(
            bot, guild, "application.grant_failed", actor=actor, target=member, details=details
        )
        return False
    open_grant = await grants.open_grant(bot.db, guild.id, member.id, form["role_id"])
    grant_id = (
        open_grant["id"]
        if open_grant is not None
        else await grants.add_grant(
            bot.db,
            guild.id,
            member.id,
            form["role_id"],
            grants.APPROVAL,
            granted_by=actor_id(actor),
            until=until,
        )
    )
    await forms.set_grant(bot.db, row["id"], grant_id)
    await log_action(
        bot,
        guild,
        "application.granted",
        actor=actor,
        target=member,
        details=details | {"grant_id": grant_id, "expires_at": until},
    )
    return True


async def _deny(
    bot: Any, guild: Any, form: Any, row: Any, actor: Any, reason: Any, via: str
) -> tuple[str, Any]:
    said = grants.clamp(reason, forms.REASON_MAX)
    if not said:
        return forms.DENY_NEEDS_A_REASON, None
    if not await forms.decide_application(
        bot.db, row["id"], grants.DENIED, decided_by=actor_id(actor), deny_reason=said
    ):
        fresh = await forms.get_application(bot.db, row["id"])
        return forms.ALREADY_DECIDED.format(status=fresh["status"]), None
    fresh = await forms.get_application(bot.db, row["id"])
    member = guild.get_member(row["user_id"])
    details = {"application_id": row["id"], "form": form["name"], "via": via}
    await log_action(
        bot,
        guild,
        kind_via("application.denied", via),
        actor=actor,
        target=member if member is not None else row["user_id"],
        reason=said,
        details=details,
    )
    card, dm_said = forms.decision_lines(form, fresh, guild_name=guild.name)
    await send_dm(bot, guild, member, dm_said, details)
    await edit_card(bot, guild, form, fresh, card)
    return forms.DENIED_SAID, fresh


async def remove(
    bot: Any,
    guild: Any,
    application_id: int,
    actor: Any,
    reason: Any,
    *,
    via: str = VIA_DISCORD,
) -> tuple[str, Any]:
    """Staff's way back off an approved list; the role forms keep `/role revoke` instead."""
    row = await forms.get_application(bot.db, application_id)
    if row is None:
        return forms.NOTHING_TO_DECIDE, None
    if row["guild_id"] != guild.id:
        return forms.NOT_THIS_SERVER, None
    form = await forms.get_form_by_id(bot.db, row["form_id"])
    if form is None:
        return forms.NOTHING_TO_DECIDE, None
    role = forms.role_of(form)
    if role is not None:
        return REMOVE_IS_FOR_LISTS.format(name=form["name"], role=role), None
    said = grants.clamp(reason, forms.REASON_MAX)
    if not said:
        return forms.REMOVE_NEEDS_A_REASON, None
    if row["status"] != grants.APPROVED:
        return forms.REMOVE_NOT_APPROVED.format(status=row["status"]), None
    if not await forms.remove_application(
        bot.db, row["id"], decided_by=actor_id(actor), reason=said
    ):
        fresh = await forms.get_application(bot.db, row["id"])
        return forms.REMOVE_NOT_APPROVED.format(status=fresh["status"]), None
    fresh = await forms.get_application(bot.db, row["id"])
    member = guild.get_member(row["user_id"])
    details = {"application_id": row["id"], "form": form["name"], "reason": said, "via": via}
    await log_action(
        bot,
        guild,
        kind_via("application.removed", via),
        actor=actor,
        target=member if member is not None else row["user_id"],
        reason=said,
        details=details,
    )
    card, dm_said = forms.decision_lines(form, fresh, guild_name=guild.name)
    await send_dm(bot, guild, member, dm_said, details)
    await edit_card(bot, guild, form, fresh, card)
    return forms.REMOVED_SAID, fresh


def decides_anything(bot: Any, guild_id: int, forms_: Any, user: Any) -> bool:
    return any(can_decide(bot, guild_id, form, user) for form in forms_ or ())


def decidable(bot: Any, guild_id: int, forms_: Any, user: Any) -> list[Any]:
    return [form for form in forms_ or () if can_decide(bot, guild_id, form, user)]


async def db_up(interaction: discord.Interaction) -> bool:
    """`db_ready` answers a followup; this one is for the reads that happen BEFORE a defer."""
    if interaction.client.db.is_connected:
        return True
    await answer(interaction, DB_UNAVAILABLE)
    return False


async def still_may_decide(interaction: discord.Interaction, form: Any) -> bool:
    """`may_decide` after a defer would answer through `response`; this one always followups."""
    bot = interaction.client
    guild = interaction.guild
    if guild is None:
        await answer(interaction, NOT_IN_GUILD)
        return False
    if can_decide(bot, guild.id, form, interaction.user):
        return True
    role_id = approver_role_id(bot, guild.id, form)
    if role_id is not None:
        await answer(
            interaction,
            NOT_AN_APPROVER.format(
                role_id=role_id, name=forms.form_value(form, "name", "the form")
            ),
        )
        return False
    await answer(interaction, bot.store.staff_refusal(guild.id))
    return False


async def set_mode(
    bot: Any, guild: Any, actor: Any, value: str, *, via: str = VIA_DISCORD
) -> tuple[str, str]:
    """The one write that turns applications off, shadow or on, and the one log row it leaves."""
    await bot.store.set(guild.id, forms.MODE_KEY, value, by=actor_id(actor))
    await log_action(
        bot,
        guild,
        kind_via("application.mode", via),
        actor=actor,
        details={"mode": value, "via": via},
    )
    return MODE_SAID[value], value


async def make_form(
    bot: Any,
    guild: Any,
    actor: Any,
    name: Any,
    title: Any,
    *,
    description: Any = None,
    role_id: Any = None,
    review_channel_id: Any = None,
    approver_role: Any = None,
    via: str = VIA_DISCORD,
) -> tuple[str, Any]:
    """(what to say, the new form) — the one path a form is created by, from either door."""
    try:
        form_id = await forms.create_form(
            bot.db,
            guild.id,
            name,
            title,
            role_id,
            actor_id(actor),
            description=description,
            review_channel_id=review_channel_id,
            approver_role_id=approver_role,
        )
    except forms.ApplicationError as exc:
        return str(exc), None
    if form_id is None:
        return forms.NAME_TAKEN.format(name=str(name or "").strip().lower()), None
    fresh = await forms.get_form_by_id(bot.db, form_id)
    await log_action(
        bot,
        guild,
        kind_via("application.form_created", via),
        actor=actor,
        details={"form": fresh["name"], "role_id": role_id or None, "via": via},
    )
    return (
        FORM_CREATED.format(name=fresh["name"], limit=forms.QUESTIONS_MAX),
        fresh,
    )


async def save_form(
    bot: Any, guild: Any, actor: Any, form: Any, changes: Any, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    """(what to say, the form as it now is) — one update, one log row, from either door."""
    try:
        await forms.update_form(bot.db, guild.id, form["name"], **dict(changes or {}))
    except forms.ApplicationError as exc:
        return str(exc), None
    fresh = await forms.get_form_by_id(bot.db, form["id"])
    await log_action(
        bot,
        guild,
        kind_via("application.form_updated", via),
        actor=actor,
        details={"form": form["name"], "changed": sorted(changes or {}), "via": via},
    )
    return FORM_SAVED.format(name=form["name"]), fresh


async def drop_form(
    bot: Any, guild: Any, actor: Any, form: Any, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    """A form only goes while nobody is waiting on it; the decided applications stay."""
    waiting = await forms.pending_count(bot.db, form["id"])
    if waiting:
        return forms.FORM_HAS_PENDING.format(name=form["name"], count=waiting), None
    await forms.delete_form(bot.db, form["id"])
    await log_action(
        bot,
        guild,
        kind_via("application.form_deleted", via),
        actor=actor,
        details={"form": form["name"], "via": via},
    )
    return FORM_DELETED.format(name=form["name"]), form


async def change_question(
    bot: Any,
    guild: Any,
    actor: Any,
    form: Any,
    what: str,
    *,
    position: Any = None,
    label: Any = None,
    style: Any = None,
    required: Any = None,
    placeholder: Any = None,
    questions: Any = None,
    via: str = VIA_DISCORD,
) -> tuple[str, Any]:
    """Add, edit, remove or replace the whole list — one write, one question_changed row."""
    try:
        if what == "added":
            position = await forms.add_question(
                bot.db, form["id"], label, style or forms.SHORT, required, placeholder
            )
            said = QUESTION_ADDED.format(
                label=label, name=form["name"], position=position
            )
        elif what == "edited":
            if not await forms.edit_question(
                bot.db,
                form["id"],
                position,
                label=label,
                style=style,
                required=required,
                placeholder=placeholder,
            ):
                return NO_SUCH_QUESTION.format(name=form["name"], position=position), None
            said = QUESTION_SAVED.format(position=position, name=form["name"])
        elif what == "removed":
            if not await forms.remove_question(bot.db, form["id"], position):
                return NO_SUCH_QUESTION.format(name=form["name"], position=position), None
            said = QUESTION_REMOVED.format(position=position, name=form["name"])
        else:
            await forms.replace_questions(bot.db, form["id"], questions)
            said = FORM_SAVED.format(name=form["name"])
    except forms.ApplicationError as exc:
        return str(exc), None
    await log_action(
        bot,
        guild,
        kind_via("application.question_changed", via),
        actor=actor,
        details={
            "form": form["name"],
            "position": position,
            "what": what,
            "via": via,
        },
    )
    return said, await forms.questions_for(bot.db, form["id"])


async def put_panel_up(
    bot: Any, guild: Any, actor: Any, form: Any, target: Any, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    """The Apply button, put up from either door; the guard is asked before Discord is."""
    if target is None:
        return forms.PANEL_NOWHERE.format(name=form["name"]), None
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(target.id):
        return guard.refusal_message(), None
    try:
        message = await post_panel(bot, guild, form, target)
    except Exception as exc:
        log.warning("applications: could not post the panel for %s: %s", form["name"], exc)
        await log_action(
            bot,
            guild,
            "application.post_failed",
            actor=actor,
            details={"form": form["name"], "reason": f"{type(exc).__name__}: {exc}"},
        )
        return forms.PANEL_STUCK.format(name=form["name"]), None
    await log_action(
        bot,
        guild,
        kind_via("application.panel_posted", via),
        actor=actor,
        details={
            "form": form["name"],
            "channel_id": target.id,
            "message_id": message.id,
            "via": via,
        },
    )
    return PANEL_POSTED.format(name=form["name"], channel_id=target.id), message


class ApplyModal(AnswersErrors, discord.ui.Modal):
    """Built from `application_questions` at open time, so staff own the wording."""

    def __init__(self, form: Any, questions: Any) -> None:
        super().__init__(title=str(form["title"])[: forms.TITLE_MAX], timeout=None)
        self.form_id = int(form["id"])
        self.asked: list[tuple[str, Any]] = []
        for row in questions:
            item = discord.ui.TextInput(
                label=str(row["label"])[: forms.LABEL_MAX],
                style=(
                    discord.TextStyle.paragraph
                    if row["style"] == forms.LONG
                    else discord.TextStyle.short
                ),
                required=bool(row["required"]),
                placeholder=str(row["placeholder"])[: forms.PLACEHOLDER_MAX]
                if row["placeholder"]
                else None,
                max_length=forms.ANSWER_INPUT_MAX,
            )
            self.add_item(item)
            self.asked.append((str(row["label"]), item))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        said = await submit_application(
            interaction.client,
            interaction.guild,
            interaction.user,
            self.form_id,
            [(label, str(item)) for label, item in self.asked],
        )
        await answer(interaction, said)


class DenyModal(NoteModal):
    """The channel card's Deny — the shared note modal, not a second copy of one."""

    def __init__(self, application_id: int) -> None:
        self.application_id = int(application_id)
        super().__init__(
            title=DENY_MODAL_TITLE,
            label=DENY_MODAL_LABEL,
            max_length=forms.REASON_MAX,
            on_submit=self.denied,
        )

    async def denied(self, interaction: discord.Interaction, note: str) -> None:
        await interaction.response.defer(ephemeral=True)
        said, _ = await apply_decision(
            interaction.client,
            interaction.guild,
            self.application_id,
            grants.DENIED,
            interaction.user,
            reason=note,
        )
        await answer(interaction, said)


async def open_form_modal(interaction: discord.Interaction, form: Any) -> None:
    """Every route into the form meets the same refusals, in the same order."""
    bot = interaction.client
    guild = interaction.guild
    if guild is None:
        await answer(interaction, NOT_IN_GUILD)
        return
    if not is_on(bot, guild.id):
        await answer(interaction, forms.APPLICATIONS_OFF)
        return
    if not bot.db.is_connected:
        await answer(interaction, DB_UNAVAILABLE)
        return
    if not forms.is_open(form):
        await answer(
            interaction,
            forms.FORM_CLOSED.format(
                title=forms.form_value(form, "title", "?"), name=form["name"]
            ),
        )
        return
    questions = await forms.questions_for(bot.db, form["id"])
    if not questions:
        await answer(interaction, forms.NO_QUESTIONS_YET.format(name=form["name"]))
        return
    held = await forms.open_application(bot.db, form["id"], interaction.user.id)
    if held is not None:
        await answer(
            interaction,
            forms.ALREADY_APPLIED.format(title=forms.form_value(form, "title", "?")),
        )
        return
    await interaction.response.send_modal(ApplyModal(form, questions))


class ApplyButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=APPLY_TEMPLATE
):
    def __init__(self, form_id: int) -> None:
        self.form_id = int(form_id)
        super().__init__(
            discord.ui.Button(
                label="Apply",
                style=discord.ButtonStyle.primary,
                custom_id=f"applyform:{form_id}",
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["form_id"]))

    async def on_click(self, interaction: discord.Interaction) -> None:
        bot = interaction.client
        if not bot.db.is_connected:
            await answer(interaction, DB_UNAVAILABLE)
            return
        form = await forms.get_form_by_id(bot.db, self.form_id)
        if form is None:
            await answer(interaction, forms.NOTHING_TO_DECIDE)
            return
        await open_form_modal(interaction, form)


class DecisionButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=DECIDE_TEMPLATE
):
    def __init__(self, application_id: int, action: str) -> None:
        self.application_id = int(application_id)
        self.action = action
        approving = action == "approve"
        super().__init__(
            discord.ui.Button(
                label="Approve" if approving else "Deny",
                style=discord.ButtonStyle.success if approving else discord.ButtonStyle.danger,
                custom_id=f"application:{application_id}:{action}",
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["application_id"]), match["action"])

    async def on_click(self, interaction: discord.Interaction) -> None:
        bot = interaction.client
        guard = getattr(bot, "guard", None)
        if guard is not None and not guard.allows_channel(interaction.channel_id):
            await answer(interaction, guard.refusal_message())
            return
        if not bot.db.is_connected:
            await answer(interaction, DB_UNAVAILABLE)
            return
        row = await forms.get_application(bot.db, self.application_id)
        if row is None:
            await answer(interaction, forms.NOTHING_TO_DECIDE)
            return
        form = await forms.get_form_by_id(bot.db, row["form_id"])
        if form is None:
            await answer(interaction, forms.NOTHING_TO_DECIDE)
            return
        if not await may_decide(interaction, form):
            return
        if row["status"] != grants.PENDING:
            await answer(interaction, forms.ALREADY_DECIDED.format(status=row["status"]))
            return
        if self.action == "deny":
            await interaction.response.send_modal(DenyModal(self.application_id))
            return
        await interaction.response.defer(ephemeral=True)
        said, _ = await apply_decision(
            interaction.client,
            interaction.guild,
            self.application_id,
            grants.APPROVED,
            interaction.user,
        )
        await answer(interaction, said)


class ApplicationsPanel(Panel):
    def __init__(self, minutes: int) -> None:
        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER)


def minutes_for(bot: Any, guild_id: int) -> int:
    return forms.panel_minutes(bot.store, guild_id)


def site_link(bot: Any, row: int) -> Any:
    url = forms.site_page_url(getattr(getattr(bot, "settings", None), "origin", ""))
    if not url:
        return None
    return discord.ui.Button(
        style=discord.ButtonStyle.link, label=forms.SITE_BUTTON, url=url, row=row
    )


def add_site_link(view: Any, bot: Any, row: int) -> None:
    button = site_link(bot, row)
    if button is not None:
        view.add_item(button)


def styles() -> dict[str, discord.ButtonStyle]:
    return {
        "primary": discord.ButtonStyle.primary,
        "secondary": discord.ButtonStyle.secondary,
        "success": discord.ButtonStyle.success,
        "danger": discord.ButtonStyle.danger,
    }


def yes_no(value: Any) -> str:
    return "on" if value else "off"


def read_yes_no(text: Any) -> bool | None:
    """A modal only takes text, so `yes`/`no` is how a checkbox is spelled; blank keeps it."""
    found = str(text or "").strip().lower()
    if not found:
        return None
    return found in ("yes", "y", "true", "1", "on")


async def own_pending(bot: Any, guild: Any, user: Any) -> list[Any]:
    return await forms.applications_for(
        bot.db, guild.id, user_id=user.id, statuses=(grants.PENDING,), limit=SELECT_CAP
    )


async def build_panel(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, Any]:
    """One command, two panels: what a member may do, and what staff may do, from one embed."""
    store = bot.store
    db = bot.db
    staff = bool(store.is_staff(actor))
    held = await forms.list_forms(db, guild.id)
    mine = decidable(bot, guild.id, held, actor)
    decider = staff or bool(mine)
    on = is_on(bot, guild.id)
    own_rows = await forms.applications_for(db, guild.id, user_id=actor.id, limit=SELECT_CAP)
    withdrawable = [row for row in own_rows if row["status"] == grants.PENDING]
    open_forms = [one for one in held if forms.is_open(one)]
    queue: list[Any] = []
    if decider:
        wanted = {one["id"] for one in (held if staff else mine)}
        waiting = await forms.applications_for(
            db, guild.id, statuses=(grants.PENDING,), limit=COUNT_LIMIT
        )
        queue = [row for row in waiting if row["form_id"] in wanted]

    lines = [forms.PANEL_INTRO]
    if decider:
        every = await forms.applications_for(db, guild.id, limit=COUNT_LIMIT)
        lines.append(forms.counts_line(held, every))
    if not on:
        lines.append(forms.APPLICATIONS_OFF)
    elif not open_forms and not staff:
        lines.append(NOTHING_OPEN_TO_APPLY_FOR)
    if staff or forms.panel_shows_own_list(store, guild.id):
        lines.extend(
            forms.own_lines(own_rows, {one["id"]: one for one in held}) or [NOTHING_OF_YOURS]
        )
    if decider and not queue:
        lines.append(NOTHING_WAITING)
    if not staff:
        lines.append(PANEL_STAFF_ONLY_LINE)

    embed = discord.Embed(title=forms.PANEL_TITLE, description="\n".join(lines))
    view = ApplicationsPanel(minutes_for(bot, guild.id))
    if queue:
        view.add_item(QueuePick(queue[:SELECT_CAP], len(queue)))
    if staff:
        if held:
            view.add_item(FormPick(held[:SELECT_CAP], len(held)))
    elif on and open_forms:
        view.add_item(ApplyPick(open_forms[:SELECT_CAP], len(open_forms)))
    if withdrawable:
        view.add_item(WithdrawPick(withdrawable, {one["id"]: one for one in held}))
    if staff:
        view.add_item(NewFormButton())
        view.add_item(FindButton())
        view.add_item(SettingsButton())
        view.add_item(LogsButton())
        view.add_item(RefreshButton(row=3))
        add_site_link(view, bot, 4)
    else:
        view.add_item(RefreshButton(row=3))
        add_site_link(view, bot, 3)
    return embed, view


async def render_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = await build_panel(interaction.client, interaction.guild, interaction.user)
    retire(previous)
    view.message = await interaction.edit_original_response(embed=embed, view=view)


async def back_to_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    await render_panel(interaction, previous)


def card_note(form: Any, row: Any) -> str:
    """The sentence a card owes when there is no button to press — never a dead control."""
    status = str(forms.form_value(row, "status", ""))
    role = forms.role_of(form)
    if status == grants.APPROVED and role is not None:
        return REMOVE_IS_FOR_LISTS.format(name=forms.form_value(form, "name"), role=role)
    if status == grants.WITHDRAWN:
        return forms.WITHDRAWN_IS_THEIRS
    return ""


def build_card(bot: Any, guild: Any, form: Any, row: Any, actor: Any) -> tuple[Any, Any]:
    member = guild.get_member(forms.form_value(row, "user_id"))
    embed = forms.render_card(form, row, member)
    note = card_note(form, row)
    if note:
        embed.add_field(name="Where it can go", value=note, inline=False)
    view = ApplicationsPanel(minutes_for(bot, guild.id))
    moves = forms.card_buttons(
        forms.form_value(row, "status"),
        has_role=forms.role_of(form) is not None,
        may_decide=can_decide(bot, guild.id, form, actor),
    )
    for move in moves:
        view.add_item(CardMoveButton(forms.form_value(row, "id"), form["id"], move))
    view.add_item(BackButton(row=1))
    return embed, view


async def open_card(
    interaction: discord.Interaction, application_id: int, previous: Any = None
) -> None:
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    bot = interaction.client
    guild = interaction.guild
    row = await forms.get_application(bot.db, application_id)
    if row is None or row["guild_id"] != guild.id:
        await answer(interaction, NOTHING_TO_SHOW)
        return
    form = await forms.get_form_by_id(bot.db, row["form_id"])
    if form is None:
        await answer(interaction, forms.NOTHING_TO_DECIDE)
        return
    if not await still_may_decide(interaction, form):
        return
    embed, view = build_card(bot, guild, form, row, interaction.user)
    retire(previous)
    view.message = await interaction.edit_original_response(embed=embed, view=view)


async def finish_card(
    interaction: discord.Interaction,
    application_id: int,
    said: str,
    fresh: Any,
    previous: Any = None,
) -> None:
    bot = interaction.client
    guild = interaction.guild
    row = fresh if fresh is not None else await forms.get_application(bot.db, application_id)
    form = (
        await forms.get_form_by_id(bot.db, row["form_id"]) if row is not None else None
    )
    if row is None or form is None:
        await render_panel(interaction, previous)
    else:
        embed, view = build_card(bot, guild, form, row, interaction.user)
        retire(previous)
        view.message = await interaction.edit_original_response(embed=embed, view=view)
    await answer(interaction, said)


MOVE_FUNCS: dict[str, Any] = {
    "approve": lambda bot, guild, rid, actor, note: apply_decision(
        bot, guild, rid, grants.APPROVED, actor
    ),
    "deny": lambda bot, guild, rid, actor, note: apply_decision(
        bot, guild, rid, grants.DENIED, actor, reason=note
    ),
    "remove": lambda bot, guild, rid, actor, note: remove(bot, guild, rid, actor, note),
    "reinstate": lambda bot, guild, rid, actor, note: reinstate(bot, guild, rid, actor),
}


async def run_move(
    interaction: discord.Interaction,
    application_id: int,
    form_id: int,
    action: str,
    note: Any = None,
    previous: Any = None,
) -> None:
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    bot = interaction.client
    form = await forms.get_form_by_id(bot.db, form_id)
    if form is None:
        await answer(interaction, forms.NOTHING_TO_DECIDE)
        return
    if not await still_may_decide(interaction, form):
        return
    said, fresh = await MOVE_FUNCS[action](
        bot, interaction.guild, application_id, interaction.user, note
    )
    await finish_card(interaction, application_id, said, fresh, previous)


class CardMoveButton(discord.ui.Button):
    def __init__(self, application_id: Any, form_id: int, move: Any) -> None:
        super().__init__(label=move.label, style=styles()[move.style], row=0)
        self.application_id = int(application_id)
        self.form_id = int(form_id)
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.move.needs_modal:
            if not await db_up(interaction):
                return
            bot = interaction.client
            form = await forms.get_form_by_id(bot.db, self.form_id)
            if form is None:
                await answer(interaction, forms.NOTHING_TO_DECIDE)
                return
            if not await still_may_decide(interaction, form):
                return
            await interaction.response.send_modal(
                MoveNoteModal(self.application_id, self.form_id, self.move, self.view)
            )
            return
        await run_move(
            interaction, self.application_id, self.form_id, self.move.action, None, self.view
        )


class MoveNoteModal(NoteModal):
    def __init__(self, application_id: int, form_id: int, move: Any, previous: Any) -> None:
        self.application_id = application_id
        self.form_id = form_id
        self.move = move
        self.previous = previous
        super().__init__(
            title=move.label,
            label=TAKE_OFF_MODAL_LABEL,
            max_length=forms.REASON_MAX,
            on_submit=self.sent,
        )

    async def sent(self, interaction: discord.Interaction, note: str) -> None:
        await run_move(
            interaction,
            self.application_id,
            self.form_id,
            self.move.action,
            note,
            self.previous,
        )


class QueuePick(discord.ui.Select):
    def __init__(self, rows: list[Any], total: int) -> None:
        super().__init__(
            placeholder=capped_placeholder(len(rows), total, pick=forms.PICK_AN_APPLICATION),
            options=[
                discord.SelectOption(
                    label=f"#{row['id']} · {row['status']}"[:100], value=str(row["id"])
                )
                for row in rows
            ],
            min_values=1,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_card(interaction, int(self.values[0]), self.view)


class ApplyPick(discord.ui.Select):
    def __init__(self, rows: list[Any], total: int) -> None:
        super().__init__(
            placeholder=capped_placeholder(len(rows), total, pick=forms.APPLY_FOR),
            options=[
                discord.SelectOption(
                    label=str(row["title"])[:100],
                    value=str(row["id"]),
                    description=str(row["description"] or "")[:100] or None,
                )
                for row in rows
            ],
            min_values=1,
            max_values=1,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await db_up(interaction):
            return
        bot = interaction.client
        form = await forms.get_form_by_id(bot.db, int(self.values[0]))
        if form is None or form["guild_id"] != interaction.guild.id:
            await answer(interaction, forms.NOTHING_TO_DECIDE)
            return
        await open_form_modal(interaction, form)


class WithdrawPick(discord.ui.Select):
    def __init__(self, rows: list[Any], named: Any) -> None:
        super().__init__(
            placeholder=forms.TAKE_ONE_BACK,
            options=[
                discord.SelectOption(
                    label=f"#{row['id']} · "
                    f"{forms.form_value(named.get(row['form_id']), 'title', '?')}"[:100],
                    value=str(row["form_id"]),
                )
                for row in rows
            ],
            min_values=1,
            max_values=1,
            row=2,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_withdraw_confirm(interaction, int(self.values[0]), self.view)


async def open_withdraw_confirm(
    interaction: discord.Interaction, form_id: int, previous: Any = None
) -> None:
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    bot = interaction.client
    form = await forms.get_form_by_id(bot.db, form_id)
    row = (
        await forms.open_application(bot.db, form_id, interaction.user.id)
        if form is not None
        else None
    )
    if form is None or row is None:
        await render_panel(interaction, previous)
        await answer(interaction, NOTHING_TO_SHOW)
        return
    embed = forms.render_card(form, row, interaction.user)
    view = ApplicationsPanel(minutes_for(bot, interaction.guild.id))
    view.add_item(WithdrawYesButton(form_id))
    view.add_item(WithdrawKeepButton())
    retire(previous)
    view.message = await interaction.edit_original_response(embed=embed, view=view)


class WithdrawYesButton(discord.ui.Button):
    def __init__(self, form_id: int) -> None:
        super().__init__(label="Yes, take it back", style=discord.ButtonStyle.danger, row=0)
        self.form_id = int(form_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if not await db_ready(interaction):
            return
        bot = interaction.client
        form = await forms.get_form_by_id(bot.db, self.form_id)
        said = (
            await withdraw_application(bot, interaction.guild, interaction.user, form)
            if form is not None
            else forms.NOTHING_TO_DECIDE
        )
        await render_panel(interaction, self.view)
        await answer(interaction, said)


class WithdrawKeepButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Keep it", style=discord.ButtonStyle.secondary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await back_to_panel(interaction, self.view)


class RefreshButton(discord.ui.Button):
    def __init__(self, row: int = 3) -> None:
        super().__init__(label="Refresh", style=discord.ButtonStyle.secondary, row=row)

    async def callback(self, interaction: discord.Interaction) -> None:
        await back_to_panel(interaction, self.view)


class BackButton(discord.ui.Button):
    def __init__(self, row: int = 0) -> None:
        super().__init__(label="Back", style=discord.ButtonStyle.secondary, row=row)

    async def callback(self, interaction: discord.Interaction) -> None:
        await back_to_panel(interaction, self.view)


class LogsButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Logs", style=discord.ButtonStyle.secondary, row=3)

    async def callback(self, interaction: discord.Interaction) -> None:
        await send_logs(interaction, FEATURE)


class FindButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Find #…", style=discord.ButtonStyle.secondary, row=3)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.send_modal(FindModal(self.view))


class FindModal(NoteModal):
    def __init__(self, previous: Any) -> None:
        self.previous = previous
        super().__init__(
            title=FIND_TITLE, label=FIND_LABEL, max_length=FIND_LIMIT, on_submit=self.found
        )

    async def found(self, interaction: discord.Interaction, text: str) -> None:
        wanted = forms.application_id_from(text)
        if wanted is None:
            await answer(interaction, forms.NOT_A_NUMBER.format(given=str(text)[:40]))
            return
        await open_card(interaction, wanted, self.previous)


class NewFormButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="New form", style=discord.ButtonStyle.primary, row=3)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.send_modal(NewFormModal(self.view))


class NewFormModal(AnswersErrors, discord.ui.Modal, title=NEW_FORM_TITLE):
    name = discord.ui.TextInput(
        label="Short name, like twitch-team", max_length=forms.NAME_MAX
    )
    title_text = discord.ui.TextInput(
        label="The heading on the form", max_length=forms.TITLE_MAX
    )
    description = discord.ui.TextInput(
        label="The line under the heading",
        style=discord.TextStyle.paragraph,
        max_length=forms.DESCRIPTION_MAX,
        required=False,
    )

    def __init__(self, previous: Any) -> None:
        super().__init__()
        self.previous = previous

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.defer()
        if not await db_ready(interaction):
            return
        said, form = await make_form(
            interaction.client,
            interaction.guild,
            interaction.user,
            str(self.name),
            str(self.title_text),
            description=str(self.description) or None,
        )
        if form is None:
            await render_panel(interaction, self.previous)
            await answer(interaction, said)
            return
        await render_form_card(interaction, form["id"], self.previous)
        await answer(interaction, said)


class FormPick(discord.ui.Select):
    def __init__(self, rows: list[Any], total: int) -> None:
        super().__init__(
            placeholder=capped_placeholder(len(rows), total, pick=forms.PICK_A_FORM),
            options=[
                discord.SelectOption(
                    label=f"{row['name']} — {row['title']}"[:100], value=str(row["id"])
                )
                for row in rows
            ],
            min_values=1,
            max_values=1,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.defer()
        if not await db_ready(interaction):
            return
        await render_form_card(interaction, int(self.values[0]), self.view)


def form_lines_for(bot: Any, guild: Any, form: Any, questions: Any, counts: Any) -> list[str]:
    role = forms.role_of(form)
    channel = forms.form_value(form, "review_channel_id")
    approver = approver_role_id(bot, guild.id, form)
    where = forms.form_value(form, "panel_channel_id")
    lines = [
        f"**{form['name']}** — {form['title']}",
        str(forms.form_value(form, "description", "") or ""),
        f"Taking applications: **{'yes' if forms.is_open(form) else 'no'}**",
        f"An approval hands over: {f'<@&{role}>' if role else '**nothing — it keeps a list**'}",
        f"Its cards wait in: {f'<#{channel}>' if channel else 'the applications channel'}",
        f"Decided by: {f'<@&{approver}>' if approver else 'staff'}",
        f"Next step: {forms.owner_nudge(form) or 'nobody is nudged'}",
        f"Role lasts: {forms.expires_days_of(form) or 'forever'} · "
        f"apply again after {forms.retry_days_of(form)} day(s)",
        f"The Apply button is in: {f'<#{where}>' if where else '**nowhere yet**'}",
        forms.COUNTS_LINE.format(
            forms=len(questions), waiting=counts[grants.PENDING], approved=counts[grants.APPROVED]
        ).replace("form(s)", "question(s)"),
    ]
    if not questions:
        lines.append(NO_QUESTIONS_LINE)
    if counts[grants.PENDING]:
        lines.append(
            forms.FORM_HAS_PENDING.format(name=form["name"], count=counts[grants.PENDING])
        )
    return [one for one in lines if one]


async def build_form_card(bot: Any, guild: Any, form: Any, actor: Any) -> tuple[Any, Any]:
    questions = await forms.questions_for(bot.db, form["id"])
    rows = await forms.applications_for(
        bot.db, guild.id, form_id=form["id"], limit=COUNT_LIMIT
    )
    counts = forms.counts_of(rows)
    embed = discord.Embed(
        title=str(form["title"]),
        description="\n".join(form_lines_for(bot, guild, form, questions, counts)),
    )
    view = ApplicationsPanel(minutes_for(bot, guild.id))
    view.add_item(EditButton(form["id"]))
    view.add_item(QuestionsButton(form["id"]))
    view.add_item(OpenCloseButton(form["id"], forms.is_open(form)))
    view.add_item(PostButton(form["id"]))
    view.add_item(BackButton(row=0))
    if forms.role_of(form) is None:
        view.add_item(RosterButton(form["id"]))
    if (
        is_on(bot, guild.id)
        and forms.is_open(form)
        and questions
        and await forms.open_application(bot.db, form["id"], actor.id) is None
    ):
        view.add_item(FillItInButton(form["id"]))
    if not counts[grants.PENDING]:
        view.add_item(DeleteButton(form["id"], len(questions)))
    add_site_link(view, bot, 1)
    return embed, view


async def render_form_card(
    interaction: discord.Interaction, form_id: int, previous: Any = None
) -> None:
    bot = interaction.client
    form = await forms.get_form_by_id(bot.db, form_id)
    if form is None or form["guild_id"] != interaction.guild.id:
        await render_panel(interaction, previous)
        await answer(interaction, forms.NO_SUCH_FORM.format(name=str(form_id)[:40]))
        return
    embed, view = await build_form_card(bot, interaction.guild, form, interaction.user)
    retire(previous)
    view.message = await interaction.edit_original_response(embed=embed, view=view)


class FormButton(discord.ui.Button):
    """Every button on a form card carries the form it belongs to and re-asks for staff."""

    def __init__(self, form_id: int, label: str, style: str, row: int) -> None:
        super().__init__(label=label, style=styles()[style], row=row)
        self.form_id = int(form_id)

    async def form_of(self, interaction: discord.Interaction) -> Any:
        if not await db_up(interaction):
            return None
        form = await forms.get_form_by_id(interaction.client.db, self.form_id)
        if form is None or form["guild_id"] != interaction.guild.id:
            await answer(interaction, forms.NO_SUCH_FORM.format(name=str(self.form_id)[:40]))
            return None
        return form


class EditButton(FormButton):
    def __init__(self, form_id: int) -> None:
        super().__init__(form_id, "Edit…", "secondary", 0)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.defer()
        if not await db_ready(interaction):
            return
        await render_edit(interaction, self.form_id, self.view)


class QuestionsButton(FormButton):
    def __init__(self, form_id: int) -> None:
        super().__init__(form_id, "Questions…", "secondary", 0)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.defer()
        if not await db_ready(interaction):
            return
        await render_questions(interaction, self.form_id, None, self.view)


class OpenCloseButton(FormButton):
    def __init__(self, form_id: int, is_open: bool) -> None:
        super().__init__(form_id, "Close it" if is_open else "Open it", "secondary", 0)
        self.wanted = not is_open

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.defer()
        if not await db_ready(interaction):
            return
        form = await self.form_of(interaction)
        if form is None:
            return
        said, _ = await save_form(
            interaction.client,
            interaction.guild,
            interaction.user,
            form,
            {"open": self.wanted},
        )
        await render_form_card(interaction, self.form_id, self.view)
        await answer(interaction, said)


class PostButton(FormButton):
    def __init__(self, form_id: int) -> None:
        super().__init__(form_id, "Post the Apply button", "primary", 0)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.defer()
        if not await db_ready(interaction):
            return
        await render_post_pick(interaction, self.form_id, self.view)


class RosterButton(FormButton):
    def __init__(self, form_id: int) -> None:
        super().__init__(form_id, "Roster", "secondary", 1)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.defer()
        if not await db_ready(interaction):
            return
        await render_roster(interaction, self.form_id, self.view)


class FillItInButton(FormButton):
    def __init__(self, form_id: int) -> None:
        super().__init__(form_id, FILL_IT_IN, "primary", 1)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await db_up(interaction):
            return
        form = await forms.get_form_by_id(interaction.client.db, self.form_id)
        if form is None or form["guild_id"] != interaction.guild.id:
            await answer(interaction, forms.NOTHING_TO_DECIDE)
            return
        await open_form_modal(interaction, form)


class DeleteButton(FormButton):
    def __init__(self, form_id: int, questions: int) -> None:
        super().__init__(form_id, "Delete", "danger", 1)
        self.questions = questions

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.defer()
        if not await db_ready(interaction):
            return
        form = await self.form_of(interaction)
        if form is None:
            return
        embed = discord.Embed(
            title=str(form["title"]),
            description=DELETE_CONFIRM.format(name=form["name"], questions=self.questions),
        )
        view = ApplicationsPanel(minutes_for(interaction.client, interaction.guild.id))
        view.add_item(DeleteYesButton(self.form_id))
        view.add_item(FormBackButton(self.form_id))
        retire(self.view)
        view.message = await interaction.edit_original_response(embed=embed, view=view)


class DeleteYesButton(FormButton):
    def __init__(self, form_id: int) -> None:
        super().__init__(form_id, "Yes, delete it", "danger", 0)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.defer()
        if not await db_ready(interaction):
            return
        form = await self.form_of(interaction)
        if form is None:
            return
        said, gone = await drop_form(
            interaction.client, interaction.guild, interaction.user, form
        )
        if gone is None:
            await render_form_card(interaction, self.form_id, self.view)
        else:
            await render_panel(interaction, self.view)
        await answer(interaction, said)


class FormBackButton(FormButton):
    def __init__(self, form_id: int, row: int = 0) -> None:
        super().__init__(form_id, "Back", "secondary", row)

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if not await db_ready(interaction):
            return
        await render_form_card(interaction, self.form_id, self.view)


async def render_post_pick(
    interaction: discord.Interaction, form_id: int, previous: Any = None
) -> None:
    bot = interaction.client
    form = await forms.get_form_by_id(bot.db, form_id)
    if form is None:
        await render_panel(interaction, previous)
        return
    embed = discord.Embed(title=str(form["title"]), description=POST_WHERE)
    view = ApplicationsPanel(minutes_for(bot, interaction.guild.id))
    view.add_item(PostChannelPick(form_id))
    view.add_item(FormBackButton(form_id, row=1))
    retire(previous)
    view.message = await interaction.edit_original_response(embed=embed, view=view)


class PostChannelPick(discord.ui.ChannelSelect):
    def __init__(self, form_id: int) -> None:
        super().__init__(
            placeholder=POST_WHERE,
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
            row=0,
        )
        self.form_id = int(form_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.defer()
        if not await db_ready(interaction):
            return
        bot = interaction.client
        form = await forms.get_form_by_id(bot.db, self.form_id)
        if form is None:
            await render_panel(interaction, self.view)
            return
        picked = self.values[0]
        target = bot.get_channel(int(picked.id)) or interaction.guild.get_channel(int(picked.id))
        said, _ = await put_panel_up(
            bot, interaction.guild, interaction.user, form, target
        )
        await render_form_card(interaction, self.form_id, self.view)
        await answer(interaction, said)


async def render_roster(
    interaction: discord.Interaction, form_id: int, previous: Any = None
) -> None:
    bot = interaction.client
    guild = interaction.guild
    form = await forms.get_form_by_id(bot.db, form_id)
    if form is None:
        await render_panel(interaction, previous)
        return
    rows = await forms.applications_for(
        bot.db, guild.id, form_id=form_id, statuses=(grants.APPROVED,), limit=COUNT_LIMIT
    )
    logins = await forms.twitch_logins_for(bot.db, [row["user_id"] for row in rows])
    shows_left = bool(bot.store.get(guild.id, ROSTER_SHOWS_LEFT_KEY))
    lines = []
    shown = []
    for row in rows:
        member = guild.get_member(row["user_id"])
        if member is None and not shows_left:
            continue
        shown.append(row)
        login = logins.get(row["user_id"])
        lines.append(
            ROSTER_LINE.format(
                user_id=row["user_id"],
                gone="" if member is not None else ROSTER_GONE,
                twitch=f" · twitch.tv/{login}" if login else "",
                stamp=grants.stamp(row["decided_at"], "R"),
            )
        )
    embed = discord.Embed(
        title=str(form["title"]), description="\n".join(lines or [ROSTER_EMPTY])[:4000]
    )
    view = ApplicationsPanel(minutes_for(bot, guild.id))
    if shown:
        view.add_item(RosterPick(form_id, shown[:SELECT_CAP], len(shown), guild))
    view.add_item(FormBackButton(form_id, row=1))
    retire(previous)
    view.message = await interaction.edit_original_response(embed=embed, view=view)


class RosterPick(discord.ui.Select):
    def __init__(self, form_id: int, rows: list[Any], total: int, guild: Any) -> None:
        super().__init__(
            placeholder=capped_placeholder(len(rows), total, pick=TAKE_SOMEBODY_OFF),
            options=[
                discord.SelectOption(
                    label=str(
                        getattr(guild.get_member(row["user_id"]), "display_name", None)
                        or row["user_id"]
                    )[:100],
                    value=str(row["id"]),
                )
                for row in rows
            ],
            min_values=1,
            max_values=1,
            row=0,
        )
        self.form_id = int(form_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await db_up(interaction):
            return
        bot = interaction.client
        form = await forms.get_form_by_id(bot.db, self.form_id)
        if form is None:
            await answer(interaction, forms.NOTHING_TO_DECIDE)
            return
        if not await still_may_decide(interaction, form):
            return
        await interaction.response.send_modal(
            RosterOffModal(int(self.values[0]), self.form_id, self.view)
        )


class RosterOffModal(NoteModal):
    def __init__(self, application_id: int, form_id: int, previous: Any) -> None:
        self.application_id = application_id
        self.form_id = form_id
        self.previous = previous
        super().__init__(
            title=TAKE_OFF_MODAL_TITLE,
            label=TAKE_OFF_MODAL_LABEL,
            max_length=forms.REASON_MAX,
            on_submit=self.sent,
        )

    async def sent(self, interaction: discord.Interaction, note: str) -> None:
        bot = interaction.client
        form = await forms.get_form_by_id(bot.db, self.form_id)
        if form is None:
            await answer(interaction, forms.NOTHING_TO_DECIDE)
            return
        if not await still_may_decide(interaction, form):
            return
        await interaction.response.defer()
        if not await db_ready(interaction):
            return
        said, _ = await remove(
            bot, interaction.guild, self.application_id, interaction.user, note
        )
        await render_roster(interaction, self.form_id, self.previous)
        await answer(interaction, said)


async def render_edit(
    interaction: discord.Interaction, form_id: int, previous: Any = None
) -> None:
    bot = interaction.client
    form = await forms.get_form_by_id(bot.db, form_id)
    if form is None:
        await render_panel(interaction, previous)
        return
    questions = await forms.questions_for(bot.db, form_id)
    counts = forms.counts_of(
        await forms.applications_for(
            bot.db, interaction.guild.id, form_id=form_id, limit=COUNT_LIMIT
        )
    )
    embed = discord.Embed(
        title=str(form["title"]),
        description="\n".join(
            [*form_lines_for(bot, interaction.guild, form, questions, counts), CLEARED_BY_EMPTY]
        ),
    )
    view = ApplicationsPanel(minutes_for(bot, interaction.guild.id))
    view.add_item(WordsButton(form_id))
    view.add_item(NumbersButton(form_id))
    view.add_item(FormBackButton(form_id))
    view.add_item(EditRolePick(form_id))
    view.add_item(EditChannelPick(form_id))
    view.add_item(EditApproverPick(form_id))
    view.add_item(EditOwnerPick(form_id))
    retire(previous)
    view.message = await interaction.edit_original_response(embed=embed, view=view)


async def save_and_edit(
    interaction: discord.Interaction, form_id: int, changes: Any, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    bot = interaction.client
    form = await forms.get_form_by_id(bot.db, form_id)
    if form is None or form["guild_id"] != interaction.guild.id:
        await render_panel(interaction, previous)
        await answer(interaction, forms.NO_SUCH_FORM.format(name=str(form_id)[:40]))
        return
    said, _ = await save_form(bot, interaction.guild, interaction.user, form, changes)
    await render_edit(interaction, form_id, previous)
    await answer(interaction, said)


class WordsButton(FormButton):
    def __init__(self, form_id: int) -> None:
        super().__init__(form_id, "Words…", "secondary", 0)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        form = await self.form_of(interaction)
        if form is None:
            return
        await interaction.response.send_modal(WordsModal(form, self.view))


class WordsModal(AnswersErrors, discord.ui.Modal):
    heading = discord.ui.TextInput(label="The heading", max_length=forms.TITLE_MAX)
    description = discord.ui.TextInput(
        label="The line under it",
        style=discord.TextStyle.paragraph,
        max_length=forms.DESCRIPTION_MAX,
        required=False,
    )
    next_step = discord.ui.TextInput(
        label="What happens after a yes",
        style=discord.TextStyle.paragraph,
        max_length=forms.TEXT_MAX,
        required=False,
    )
    approved_text = discord.ui.TextInput(
        label="What an approved applicant is DM'd",
        style=discord.TextStyle.paragraph,
        max_length=forms.TEXT_MAX,
        required=False,
    )

    def __init__(self, form: Any, previous: Any) -> None:
        super().__init__(title=WORDS_TITLE.format(name=form["name"])[:45])
        self.form_id = int(form["id"])
        self.previous = previous
        self.heading.default = str(form["title"])
        self.description.default = str(forms.form_value(form, "description", "") or "") or None
        self.next_step.default = forms.next_step_of(form) or None
        self.approved_text.default = str(forms.form_value(form, "approved_text", "") or "") or None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await save_and_edit(
            interaction,
            self.form_id,
            {
                "title": str(self.heading),
                "description": str(self.description),
                "next_step": str(self.next_step),
                "approved_text": str(self.approved_text),
            },
            self.previous,
        )


class NumbersButton(FormButton):
    def __init__(self, form_id: int) -> None:
        super().__init__(form_id, "Numbers…", "secondary", 0)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        form = await self.form_of(interaction)
        if form is None:
            return
        await interaction.response.send_modal(FormNumbersModal(form, self.view))


class FormNumbersModal(AnswersErrors, discord.ui.Modal):
    expires_days = discord.ui.TextInput(
        label="Days the role lasts, 0 for forever", max_length=4, required=False
    )
    retry_days = discord.ui.TextInput(
        label="Days before somebody may apply again", max_length=4, required=False
    )

    def __init__(self, form: Any, previous: Any) -> None:
        super().__init__(title=NUMBERS_TITLE.format(name=form["name"])[:45])
        self.form_id = int(form["id"])
        self.previous = previous
        self.expires_days.default = str(forms.expires_days_of(form) or 0)
        self.retry_days.default = str(forms.retry_days_of(form))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await save_and_edit(
            interaction,
            self.form_id,
            {
                "expires_days": str(self.expires_days),
                "retry_days": str(self.retry_days),
            },
            self.previous,
        )


class EditRolePick(discord.ui.RoleSelect):
    def __init__(self, form_id: int) -> None:
        super().__init__(placeholder=EDIT_ROLE_PICK, min_values=0, max_values=1, row=1)
        self.form_id = int(form_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        picked = int(self.values[0].id) if self.values else forms.NO_ROLE
        await save_and_edit(interaction, self.form_id, {"role_id": picked}, self.view)


class EditChannelPick(discord.ui.ChannelSelect):
    def __init__(self, form_id: int) -> None:
        super().__init__(
            placeholder=EDIT_CHANNEL_PICK,
            channel_types=[discord.ChannelType.text],
            min_values=0,
            max_values=1,
            row=2,
        )
        self.form_id = int(form_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        picked = int(self.values[0].id) if self.values else forms.NO_ROLE
        await save_and_edit(interaction, self.form_id, {"review_channel_id": picked}, self.view)


class EditApproverPick(discord.ui.RoleSelect):
    def __init__(self, form_id: int) -> None:
        super().__init__(placeholder=EDIT_APPROVER_PICK, min_values=0, max_values=1, row=3)
        self.form_id = int(form_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        picked = int(self.values[0].id) if self.values else forms.NO_ROLE
        await save_and_edit(interaction, self.form_id, {"approver_role_id": picked}, self.view)


class EditOwnerPick(discord.ui.UserSelect):
    def __init__(self, form_id: int) -> None:
        super().__init__(placeholder=EDIT_OWNER_PICK, min_values=0, max_values=1, row=4)
        self.form_id = int(form_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        picked = int(self.values[0].id) if self.values else forms.NO_ROLE
        await save_and_edit(interaction, self.form_id, {"owner_user_id": picked}, self.view)


async def render_questions(
    interaction: discord.Interaction,
    form_id: int,
    position: Any = None,
    previous: Any = None,
) -> None:
    bot = interaction.client
    form = await forms.get_form_by_id(bot.db, form_id)
    if form is None:
        await render_panel(interaction, previous)
        return
    rows = await forms.questions_for(bot.db, form_id)
    picked = next(
        (one for one in rows if int(one["position"]) == int(position or 0)), None
    )
    lines = forms.question_lines(rows) or [NO_QUESTIONS_LINE]
    embed = discord.Embed(
        title=str(form["title"]),
        description="\n".join([*lines, REORDER_IS_ON_THE_SITE]),
    )
    view = ApplicationsPanel(minutes_for(bot, interaction.guild.id))
    if rows:
        view.add_item(QuestionPick(form_id, rows))
    if picked is not None:
        view.add_item(QuestionEditButton(form_id, int(picked["position"])))
        view.add_item(QuestionRemoveButton(form_id, int(picked["position"])))
    if len(rows) < forms.QUESTIONS_MAX:
        view.add_item(QuestionAddButton(form_id))
    view.add_item(FormBackButton(form_id, row=1))
    add_site_link(view, bot, 1)
    retire(previous)
    view.message = await interaction.edit_original_response(embed=embed, view=view)


class QuestionPick(discord.ui.Select):
    def __init__(self, form_id: int, rows: list[Any]) -> None:
        super().__init__(
            placeholder=PICK_A_QUESTION,
            options=[
                discord.SelectOption(
                    label=f"{row['position']}. {row['label']}"[:100],
                    value=str(row["position"]),
                )
                for row in rows
            ],
            min_values=1,
            max_values=1,
            row=0,
        )
        self.form_id = int(form_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.defer()
        if not await db_ready(interaction):
            return
        await render_questions(interaction, self.form_id, int(self.values[0]), self.view)


class QuestionAddButton(FormButton):
    def __init__(self, form_id: int) -> None:
        super().__init__(form_id, "Add…", "primary", 1)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        form = await self.form_of(interaction)
        if form is None:
            return
        await interaction.response.send_modal(QuestionModal(form, None, self.view))


class QuestionEditButton(FormButton):
    def __init__(self, form_id: int, position: int) -> None:
        super().__init__(form_id, "Edit", "secondary", 1)
        self.position = position

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        form = await self.form_of(interaction)
        if form is None:
            return
        rows = await forms.questions_for(interaction.client.db, self.form_id)
        held = next((one for one in rows if int(one["position"]) == self.position), None)
        if held is None:
            await answer(
                interaction,
                NO_SUCH_QUESTION.format(name=form["name"], position=self.position),
            )
            return
        await interaction.response.send_modal(QuestionModal(form, held, self.view))


class QuestionRemoveButton(FormButton):
    def __init__(self, form_id: int, position: int) -> None:
        super().__init__(form_id, "Remove", "danger", 1)
        self.position = position

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.defer()
        if not await db_ready(interaction):
            return
        form = await self.form_of(interaction)
        if form is None:
            return
        rows = await forms.questions_for(interaction.client.db, self.form_id)
        held = next((one for one in rows if int(one["position"]) == self.position), None)
        embed = discord.Embed(
            title=str(form["title"]),
            description=REMOVE_QUESTION_CONFIRM.format(
                position=self.position,
                label=forms.form_value(held, "label", "?"),
                name=form["name"],
            ),
        )
        view = ApplicationsPanel(minutes_for(interaction.client, interaction.guild.id))
        view.add_item(QuestionRemoveYesButton(self.form_id, self.position))
        view.add_item(QuestionsBackButton(self.form_id))
        retire(self.view)
        view.message = await interaction.edit_original_response(embed=embed, view=view)


class QuestionRemoveYesButton(FormButton):
    def __init__(self, form_id: int, position: int) -> None:
        super().__init__(form_id, "Yes, remove it", "danger", 0)
        self.position = position

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.defer()
        if not await db_ready(interaction):
            return
        form = await self.form_of(interaction)
        if form is None:
            return
        said, _ = await change_question(
            interaction.client,
            interaction.guild,
            interaction.user,
            form,
            "removed",
            position=self.position,
        )
        await render_questions(interaction, self.form_id, None, self.view)
        await answer(interaction, said)


class QuestionsBackButton(FormButton):
    def __init__(self, form_id: int) -> None:
        super().__init__(form_id, "Back", "secondary", 0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if not await db_ready(interaction):
            return
        await render_questions(interaction, self.form_id, None, self.view)


class QuestionModal(AnswersErrors, discord.ui.Modal):
    label_text = discord.ui.TextInput(label="What the box is called", max_length=forms.LABEL_MAX)
    style = discord.ui.TextInput(
        label=STYLE_HINT, placeholder=STYLE_HINT, max_length=5, required=False
    )
    required = discord.ui.TextInput(
        label=REQUIRED_HINT, placeholder=REQUIRED_HINT, max_length=3, required=False
    )
    placeholder_text = discord.ui.TextInput(
        label="Grey hint inside the box",
        max_length=forms.PLACEHOLDER_MAX,
        required=False,
    )

    def __init__(self, form: Any, question: Any, previous: Any) -> None:
        title = (
            ADD_QUESTION_TITLE.format(name=form["name"])
            if question is None
            else QUESTION_TITLE.format(
                position=question["position"], name=form["name"]
            )
        )
        super().__init__(title=title[:45])
        self.form_id = int(form["id"])
        self.position = None if question is None else int(question["position"])
        self.previous = previous
        if question is not None:
            self.label_text.default = str(question["label"])
            self.style.default = str(question["style"])
            self.required.default = YES_NO[0] if question["required"] else YES_NO[1]
            self.placeholder_text.default = str(question["placeholder"] or "") or None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.defer()
        if not await db_ready(interaction):
            return
        bot = interaction.client
        form = await forms.get_form_by_id(bot.db, self.form_id)
        if form is None or form["guild_id"] != interaction.guild.id:
            await render_panel(interaction, self.previous)
            await answer(interaction, forms.NO_SUCH_FORM.format(name=str(self.form_id)[:40]))
            return
        said, _ = await change_question(
            bot,
            interaction.guild,
            interaction.user,
            form,
            "added" if self.position is None else "edited",
            position=self.position,
            label=str(self.label_text),
            style=str(self.style) or None,
            required=read_yes_no(self.required)
            if self.position is not None
            else read_yes_no(self.required) is not False,
            placeholder=str(self.placeholder_text) or None,
        )
        await render_questions(interaction, self.form_id, self.position, self.previous)
        await answer(interaction, said)


SETTINGS_LINES = (
    ("Mode", forms.MODE_KEY),
    ("Where cards wait", forms.CHANNEL_KEY),
    ("Who decides", forms.APPROVER_ROLE_KEY),
    ("Who is pinged", forms.PING_ROLE_KEY),
    ("Days before applying again", forms.RETRY_DAYS_KEY),
    ("DM on a decision", forms.DM_KEY),
    ("Roster shows people who left", ROSTER_SHOWS_LEFT_KEY),
    ("Panel minutes", PANEL_MINUTES_KEY),
    ("Members see their own list", forms.PANEL_OWN_LIST_KEY),
)
CHANNEL_KEYS = (forms.CHANNEL_KEY,)
ROLE_KEYS = (forms.APPROVER_ROLE_KEY, forms.PING_ROLE_KEY)
BOOL_KEYS = (forms.DM_KEY, ROSTER_SHOWS_LEFT_KEY, forms.PANEL_OWN_LIST_KEY)


def settings_lines(bot: Any, guild_id: int) -> list[str]:
    found = []
    for name, key in SETTINGS_LINES:
        value = bot.store.get(guild_id, key)
        if key in CHANNEL_KEYS:
            shown = f"<#{value}>" if value else "not set"
        elif key in ROLE_KEYS:
            shown = f"<@&{value}>" if value else "not set"
        elif key in BOOL_KEYS:
            shown = yes_no(value)
        else:
            shown = str(value)
        found.append(f"**{name}:** {shown}")
    return found


async def render_settings(interaction: discord.Interaction, previous: Any = None) -> None:
    bot = interaction.client
    guild = interaction.guild
    embed = discord.Embed(
        title=SETTINGS_TITLE, description="\n".join(settings_lines(bot, guild.id))
    )
    view = ApplicationsPanel(minutes_for(bot, guild.id))
    view.add_item(ModePick(mode_of(bot, guild.id)))
    view.add_item(SettingsChannelPick())
    view.add_item(SettingsApproverPick())
    view.add_item(SettingsPingPick())
    view.add_item(SettingsToggle(forms.DM_KEY, "DMs", bot.store.get(guild.id, forms.DM_KEY)))
    view.add_item(
        SettingsToggle(
            ROSTER_SHOWS_LEFT_KEY,
            "Roster shows people who left",
            bot.store.get(guild.id, ROSTER_SHOWS_LEFT_KEY),
        )
    )
    view.add_item(
        SettingsToggle(
            forms.PANEL_OWN_LIST_KEY,
            "Members see their own list",
            bot.store.get(guild.id, forms.PANEL_OWN_LIST_KEY),
        )
    )
    view.add_item(SettingsNumbersButton())
    view.add_item(BackButton(row=4))
    retire(previous)
    view.message = await interaction.edit_original_response(embed=embed, view=view)


async def save_settings(
    interaction: discord.Interaction, changes: Any, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    bot = interaction.client
    guild = interaction.guild
    for key, value in dict(changes or {}).items():
        if value is None:
            await bot.store.clear(guild.id, key, by=interaction.user.id)
        else:
            await bot.store.set(guild.id, key, value, by=interaction.user.id)
    await render_settings(interaction, previous)


class SettingsButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Settings", style=discord.ButtonStyle.secondary, row=3)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.defer()
        if not await db_ready(interaction):
            return
        await render_settings(interaction, self.view)


class ModePick(discord.ui.Select):
    def __init__(self, current: str) -> None:
        super().__init__(
            placeholder=SETTINGS_MODE_PICK,
            options=[
                discord.SelectOption(label=one, value=one, default=one == current)
                for one in forms.MODES
            ],
            min_values=1,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.defer()
        if not await db_ready(interaction):
            return
        said, _ = await set_mode(
            interaction.client, interaction.guild, interaction.user, str(self.values[0])
        )
        await render_settings(interaction, self.view)
        await answer(interaction, said)


class SettingsChannelPick(discord.ui.ChannelSelect):
    def __init__(self) -> None:
        super().__init__(
            placeholder=SETTINGS_CHANNEL_PICK,
            channel_types=[discord.ChannelType.text],
            min_values=0,
            max_values=1,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        picked = int(self.values[0].id) if self.values else None
        await save_settings(interaction, {forms.CHANNEL_KEY: picked}, self.view)


class SettingsApproverPick(discord.ui.RoleSelect):
    def __init__(self) -> None:
        super().__init__(placeholder=SETTINGS_APPROVER_PICK, min_values=0, max_values=1, row=2)

    async def callback(self, interaction: discord.Interaction) -> None:
        picked = int(self.values[0].id) if self.values else None
        await save_settings(interaction, {forms.APPROVER_ROLE_KEY: picked}, self.view)


class SettingsPingPick(discord.ui.RoleSelect):
    def __init__(self) -> None:
        super().__init__(placeholder=SETTINGS_PING_PICK, min_values=0, max_values=1, row=3)

    async def callback(self, interaction: discord.Interaction) -> None:
        picked = int(self.values[0].id) if self.values else None
        await save_settings(interaction, {forms.PING_ROLE_KEY: picked}, self.view)


class SettingsToggle(discord.ui.Button):
    def __init__(self, key: str, name: str, current: Any) -> None:
        super().__init__(
            label=f"{name}: {yes_no(current)}", style=discord.ButtonStyle.secondary, row=4
        )
        self.key = key
        self.wanted = not current

    async def callback(self, interaction: discord.Interaction) -> None:
        await save_settings(interaction, {self.key: self.wanted}, self.view)


class SettingsNumbersButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Numbers…", style=discord.ButtonStyle.secondary, row=4)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.send_modal(
            SettingsNumbersModal(interaction.client, interaction.guild.id, self.view)
        )


class SettingsNumbersModal(AnswersErrors, discord.ui.Modal, title=SETTINGS_NUMBERS_TITLE):
    retry_days = discord.ui.TextInput(
        label="Days before applying again", max_length=4, required=False
    )
    panel_minutes = discord.ui.TextInput(
        label="Minutes this panel stays live", max_length=4, required=False
    )

    def __init__(self, bot: Any, guild_id: int, previous: Any) -> None:
        super().__init__()
        self.previous = previous
        self.retry_days.default = str(bot.store.get(guild_id, forms.RETRY_DAYS_KEY))
        self.panel_minutes.default = str(bot.store.get(guild_id, PANEL_MINUTES_KEY))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        changes = {}
        for key, field in (
            (forms.RETRY_DAYS_KEY, self.retry_days),
            (PANEL_MINUTES_KEY, self.panel_minutes),
        ):
            try:
                days = forms.whole_days(str(field))
            except forms.ApplicationError as exc:
                await answer(interaction, str(exc))
                return
            if days is not None:
                changes[key] = days
        await save_settings(interaction, changes, self.previous)


class Applications(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_dynamic_items(ApplyButton, DecisionButton)
        if not self.bot.db.is_connected:
            return
        for guild in list(getattr(self.bot, "guilds", ())):
            for form in await forms.list_forms(self.bot.db, guild.id):
                if form["panel_message_id"]:
                    self.bot.add_view(
                        panel_view(form["id"]), message_id=form["panel_message_id"]
                    )
                    log.info(
                        "application form %s re-registered on message %s",
                        form["name"],
                        form["panel_message_id"],
                    )

    async def _ready(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return False
        if self.bot.db.is_connected:
            return True
        log.warning("applications: refused a command — the database is not connected")
        await answer(interaction, DB_UNAVAILABLE)
        return False

    @app_commands.command(name="apply", description=APPLY_COMMAND_DESCRIPTION)
    async def apply(self, interaction: discord.Interaction) -> None:
        if not await self._ready(interaction):
            return
        embed, view = await build_panel(self.bot, interaction.guild, interaction.user)
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Applications(bot))


__all__ = [
    "APPLY_TEMPLATE",
    "DECIDE_TEMPLATE",
    "FEATURE",
    "MODE_SAID",
    "NOT_AN_APPROVER",
    "PANEL_TIMEOUT_FOOTER",
    "REMOVE_IS_FOR_LISTS",
    "TAKE_OFF_LABEL",
    "Applications",
    "ApplicationsPanel",
    "DenyModal",
    "ApplyButton",
    "ApplyModal",
    "ApplyPick",
    "CardMoveButton",
    "DecisionButton",
    "FormPick",
    "LogsButton",
    "QueuePick",
    "WithdrawPick",
    "apply_decision",
    "approver_role_id",
    "build_card",
    "build_form_card",
    "build_panel",
    "can_decide",
    "change_question",
    "decidable",
    "db_up",
    "decides_anything",
    "drop_form",
    "edit_card",
    "is_on",
    "make_form",
    "may_decide",
    "mode_of",
    "nudge_mentions",
    "open_card",
    "open_form_modal",
    "post_panel",
    "put_panel_up",
    "reinstate",
    "remove",
    "render_form_card",
    "render_panel",
    "render_questions",
    "render_roster",
    "render_settings",
    "review_channel",
    "save_form",
    "set_mode",
    "settle_approval",
    "settings_lines",
    "still_may_decide",
    "submit_application",
    "withdraw_application",
]
