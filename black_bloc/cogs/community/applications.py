from __future__ import annotations

import logging
import re
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from ... import applications as forms
from ... import rolegrants as grants
from ...actionlog import (
    LOGS_DEFAULT,
    LOGS_MAX,
    LOGS_MIN,
    log_action,
    send_logs,
)
from ...command_errors import AnswersErrors, SafeDynamicItem
from ...command_visibility import STAFF_ONLY
from ...logkinds import VIA_DISCORD, kind_via
from ...panels import NoteModal, Panel, panel_minutes
from ...settings_store import DB_UNAVAILABLE, require_staff
from .role_menus import answer, card_target, change_roles, dm, ping_mentions

log = logging.getLogger(__name__)

FEATURE = "applications"
APPLY_TEMPLATE = r"applyform:(?P<form_id>[0-9]+)"
DECIDE_TEMPLATE = r"application:(?P<application_id>[0-9]+):(?P<action>approve|deny)"
SHADOW = "shadow"
ON = "on"

APPROVAL_FALLBACK_CHANNEL_KEY = "rolemenu_approval_channel_id"
APPROVAL_FALLBACK_ROLE_KEY = "rolemenu_approver_role_id"
STAFF_CHANNEL_KEY = "staff_channel_id"
PANEL_MINUTES_KEY = "applications_panel_minutes"
ROSTER_SHOWS_LEFT_KEY = "applications_roster_shows_left"
PANEL_TIMEOUT_FOOTER = "This panel went quiet. Run /applications show again to bring it back."
TAKE_OFF_LABEL = "Take off the list"
TAKE_OFF_MODAL_TITLE = "Take them off the list?"
TAKE_OFF_MODAL_LABEL = "One line they will be sent"

NOT_IN_GUILD = (
    "Applications only work inside the server, and this did not come from one, so nothing was "
    "sent. Open the form in a server channel and try again."
)
NOT_AN_APPROVER = (
    "Deciding an application needs <@&{role_id}>, so nothing was changed. Ask somebody who has "
    "that role, or a Lead can point the form at a different one with `/applications edit "
    "{name} approver_role:@role`."
)
PANEL_BODY = (
    "**{title}**\n{description}\nPress **Apply** to fill the form in. Staff look at every one "
    "and you get a DM either way."
)
PANEL_POSTED = (
    "The Apply button for **{name}** is up in <#{channel_id}>. Post it again to move it."
)
FORM_CREATED = (
    "Created **{name}**. Add its questions with `/applications question add {name} <label>` — up "
    "to {limit} — then put the button up with `/applications panel {name}`."
)
FORM_SAVED = "Saved **{name}**."
FORM_DELETED = (
    "Deleted **{name}** and its questions. Nobody loses a role they already have, and the "
    "applications already decided stay on the record."
)
QUESTION_ADDED = (
    "Added **{label}** to **{name}** as question {position}. `/applications question list "
    "{name}` shows the whole form."
)
QUESTION_SAVED = "Saved question {position} on **{name}**."
QUESTION_REMOVED = (
    "Removed question {position} from **{name}**. Answers already sent keep the wording they "
    "were asked in."
)
NO_SUCH_QUESTION = (
    "**{name}** has nothing in slot {position}, so nothing was changed. `/applications question "
    "list {name}` says which slots are filled."
)
NOTHING_OF_YOURS = (
    "You have not applied for anything here yet. `/apply start` lists the forms that are open."
)
YOUR_APPLICATION = "**{title}** — {status}{extra}"
STATUS_WAITING = ", waiting on staff"
NOTHING_TO_SHOW = (
    "Black Bloc has no application with that number, so there was nothing to show. "
    "`/applications list` names the ones it has."
)
REMOVE_IS_FOR_LISTS = (
    "**{name}** hands over <@&{role}>, so there is no list to take them off; `/role revoke` "
    "takes the role back and ends the grant — the approval stays on record."
)
ROLE_OR_NO_ROLE = (
    "Pick a role or say `no_role:true`, not both, so nothing was changed. `no_role:true` clears "
    "the role and the form keeps a list instead."
)
MODE_SAID = {
    "off": (
        "Off. `/apply` disappears from Discord, the Apply buttons stop working, and nothing is "
        "posted or DMed. Nobody loses a role and no form is changed."
    ),
    SHADOW: (
        "Shadow. Applications are still written down and still show on the dashboard, but no "
        "card is posted, no DM is sent and no role is handed over — the log says what would "
        "have happened."
    ),
    ON: "On. Members can apply, staff decide on the card, and an approval hands the role over.",
}


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
    role = forms.role_of(form)
    until = grants.expires_at(forms.expires_days_of(form)) if role else None
    details = {
        "application_id": row["id"],
        "form": form["name"],
        "role_id": role,
        "via": via,
    }
    if not await forms.decide_application(
        bot.db, row["id"], grants.APPROVED, decided_by=actor_id(actor)
    ):
        fresh = await forms.get_application(bot.db, row["id"])
        return forms.ALREADY_DECIDED.format(status=fresh["status"]), None
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


class DenyModal(AnswersErrors, discord.ui.Modal, title="Why not?"):
    reason = discord.ui.TextInput(
        label="One line the applicant will be sent",
        style=discord.TextStyle.paragraph,
        max_length=forms.REASON_MAX,
    )

    def __init__(self, application_id: int) -> None:
        super().__init__()
        self.application_id = application_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        said, _ = await apply_decision(
            interaction.client,
            interaction.guild,
            self.application_id,
            grants.DENIED,
            interaction.user,
            reason=str(self.reason),
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


class ShowPanel(Panel):
    def __init__(self, minutes: int) -> None:
        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER)


class TakeOffButton(discord.ui.Button):
    """Rendered only on an approved application on a form that keeps a list."""

    def __init__(self, application_id: int) -> None:
        super().__init__(label=TAKE_OFF_LABEL, style=discord.ButtonStyle.danger, row=0)
        self.application_id = int(application_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        bot = interaction.client
        if not bot.db.is_connected:
            await answer(interaction, DB_UNAVAILABLE)
            return
        row = await forms.get_application(bot.db, self.application_id)
        form = (
            await forms.get_form_by_id(bot.db, row["form_id"]) if row is not None else None
        )
        if row is None or form is None:
            await answer(interaction, forms.NOTHING_TO_DECIDE)
            return
        if not await may_decide(interaction, form):
            return
        if row["status"] != grants.APPROVED:
            await answer(interaction, forms.REMOVE_NOT_APPROVED.format(status=row["status"]))
            return
        await interaction.response.send_modal(
            NoteModal(
                title=TAKE_OFF_MODAL_TITLE,
                label=TAKE_OFF_MODAL_LABEL,
                max_length=forms.REASON_MAX,
                on_submit=self.take_off,
            )
        )

    async def take_off(self, interaction: discord.Interaction, note: str) -> None:
        await interaction.response.defer(ephemeral=True)
        said, _ = await remove(
            interaction.client,
            interaction.guild,
            self.application_id,
            interaction.user,
            note,
        )
        await answer(interaction, said)


def show_panel(bot: Any, guild_id: int, form: Any, row: Any, user: Any) -> ShowPanel | None:
    """A panel only when there is a move on it; otherwise the embed goes out bare, as before."""
    if str(forms.form_value(row, "status", "")) != grants.APPROVED:
        return None
    if forms.role_of(form) is not None:
        return None
    if not can_decide(bot, guild_id, form, user):
        return None
    view = ShowPanel(panel_minutes(bot.store, guild_id, PANEL_MINUTES_KEY))
    view.add_item(TakeOffButton(forms.form_value(row, "id")))
    return view


class Applications(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    apply = app_commands.Group(
        name="apply", description="Apply for something staff hand out"
    )
    applications = app_commands.Group(
        name="applications",
        description="The forms members apply on, and the applications waiting",
        default_permissions=STAFF_ONLY,
    )

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

    async def form_choices(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await self._choices(interaction, current, open_only=True)

    async def any_form_choices(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await self._choices(interaction, current, open_only=False)

    async def _choices(
        self, interaction: discord.Interaction, current: str, *, open_only: bool
    ) -> list[app_commands.Choice[str]]:
        if interaction.guild is None or not self.bot.db.is_connected:
            return []
        wanted = str(current or "").lower()
        found = await forms.list_forms(self.bot.db, interaction.guild.id, open_only=open_only)
        return [
            app_commands.Choice(name=f"{row['name']} — {row['title']}"[:100], value=row["name"])
            for row in found
            if wanted in row["name"].lower() or wanted in str(row["title"]).lower()
        ][:25]

    async def _form(self, interaction: discord.Interaction, name: str) -> Any:
        """The named form, or None once the caller has been told there is no such thing."""
        if interaction.guild is None:
            await answer(interaction, NOT_IN_GUILD)
            return None
        if not self.bot.db.is_connected:
            await answer(interaction, DB_UNAVAILABLE)
            return None
        form = await forms.get_form(self.bot.db, interaction.guild.id, name)
        if form is None:
            await answer(interaction, forms.NO_SUCH_FORM.format(name=str(name)[:40]))
        return form

    @apply.command(name="start", description="Fill in an application form")
    @app_commands.describe(form="Which form to fill in")
    async def apply_start(self, interaction: discord.Interaction, form: str) -> None:
        found = await self._form(interaction, form)
        if found is None:
            return
        await open_form_modal(interaction, found)

    @apply_start.autocomplete("form")
    async def _apply_start_forms(self, interaction: discord.Interaction, current: str):
        return await self.form_choices(interaction, current)

    @apply.command(name="status", description="Where your own applications are")
    async def apply_status(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await answer(interaction, NOT_IN_GUILD)
            return
        if not self.bot.db.is_connected:
            await answer(interaction, DB_UNAVAILABLE)
            return
        rows = await forms.applications_for(
            self.bot.db, interaction.guild.id, user_id=interaction.user.id, limit=25
        )
        if not rows:
            await answer(interaction, NOTHING_OF_YOURS)
            return
        named = {
            row["id"]: row for row in await forms.list_forms(self.bot.db, interaction.guild.id)
        }
        lines = []
        for row in rows:
            form = named.get(row["form_id"])
            extra = STATUS_WAITING if row["status"] == grants.PENDING else ""
            if row["deny_reason"]:
                extra = f" — {row['deny_reason']}"
            lines.append(
                YOUR_APPLICATION.format(
                    title=forms.form_value(form, "title", f"form #{row['form_id']}"),
                    status=row["status"],
                    extra=extra,
                )
            )
        await answer(interaction, "\n".join(lines)[:2000])

    @apply.command(name="withdraw", description="Take an application back while it is waiting")
    @app_commands.describe(form="Which form to take your application back from")
    async def apply_withdraw(self, interaction: discord.Interaction, form: str) -> None:
        found = await self._form(interaction, form)
        if found is None:
            return
        await answer(
            interaction,
            await withdraw_application(
                self.bot, interaction.guild, interaction.user, found
            ),
        )

    @apply_withdraw.autocomplete("form")
    async def _apply_withdraw_forms(self, interaction: discord.Interaction, current: str):
        return await self.any_form_choices(interaction, current)

    @applications.command(name="mode", description="Turn applications off, shadow or on")
    @app_commands.choices(
        value=[app_commands.Choice(name=one, value=one) for one in forms.MODES]
    )
    async def applications_mode(
        self, interaction: discord.Interaction, value: app_commands.Choice[str]
    ) -> None:
        if not await require_staff(interaction):
            return
        await self.bot.store.set(
            interaction.guild.id, forms.MODE_KEY, value.value, by=interaction.user.id
        )
        await log_action(
            interaction.client,
            interaction.guild,
            "application.mode",
            actor=interaction.user,
            details={"mode": value.value},
        )
        await answer(interaction, MODE_SAID[value.value])

    @applications.command(name="create", description="Make a new application form")
    @app_commands.describe(
        name="Short name the other commands use, like twitch-team",
        title="The heading on the form and on its card",
        role="The role an approved application hands over; leave it out to keep a list instead",
        channel="Where its cards wait; blank uses the applications channel setting",
        approver_role="Who may decide it; blank uses the setting, then staff",
    )
    async def applications_create(
        self,
        interaction: discord.Interaction,
        name: str,
        title: str,
        role: discord.Role | None = None,
        channel: discord.TextChannel | None = None,
        approver_role: discord.Role | None = None,
    ) -> None:
        if not await require_staff(interaction):
            return
        try:
            form_id = await forms.create_form(
                self.bot.db,
                interaction.guild.id,
                name,
                title,
                role.id if role else None,
                interaction.user.id,
                review_channel_id=channel.id if channel else None,
                approver_role_id=approver_role.id if approver_role else None,
            )
        except forms.ApplicationError as exc:
            await answer(interaction, str(exc))
            return
        if form_id is None:
            await answer(interaction, forms.NAME_TAKEN.format(name=name))
            return
        await log_action(
            self.bot,
            interaction.guild,
            "application.form_created",
            actor=interaction.user,
            details={"form": name, "role_id": role.id if role else None},
        )
        await answer(
            interaction,
            FORM_CREATED.format(name=name.lower(), limit=forms.QUESTIONS_MAX),
        )

    @applications.command(name="edit", description="Change one application form")
    @app_commands.describe(
        form="Which form to change",
        title="The heading on the form",
        description="The line under the heading on the Apply panel",
        open="False stops it taking applications; True lets them in again",
        role="The role an approved application hands over",
        no_role="True clears the role so the form keeps a list instead",
        owner="Who is nudged to take the next step after an approval",
        next_step="What that person has to do, in one line",
        approved_text="What an approved applicant is DM'd",
        expires_days="Days the role lasts; 0 means it never runs out",
        retry_days="Days somebody waits after a decision before applying again",
    )
    async def applications_edit(
        self,
        interaction: discord.Interaction,
        form: str,
        title: str | None = None,
        description: str | None = None,
        open: bool | None = None,
        role: discord.Role | None = None,
        no_role: bool | None = None,
        owner: discord.Member | None = None,
        next_step: str | None = None,
        approved_text: str | None = None,
        expires_days: app_commands.Range[int, 0, forms.DAYS_MAX] | None = None,
        retry_days: app_commands.Range[int, 0, forms.DAYS_MAX] | None = None,
    ) -> None:
        if not await require_staff(interaction):
            return
        if role is not None and no_role:
            await answer(interaction, ROLE_OR_NO_ROLE)
            return
        found = await self._form(interaction, form)
        if found is None:
            return
        try:
            await forms.update_form(
                self.bot.db,
                interaction.guild.id,
                found["name"],
                title=title,
                description=description,
                open=open,
                role_id=role.id if role else (forms.NO_ROLE if no_role else None),
                owner_user_id=owner.id if owner else None,
                next_step=next_step,
                approved_text=approved_text,
                expires_days=expires_days,
                retry_days=retry_days,
            )
        except forms.ApplicationError as exc:
            await answer(interaction, str(exc))
            return
        await log_action(
            self.bot,
            interaction.guild,
            "application.form_updated",
            actor=interaction.user,
            details={"form": found["name"]},
        )
        await answer(interaction, FORM_SAVED.format(name=found["name"]))

    @applications_edit.autocomplete("form")
    async def _edit_forms(self, interaction: discord.Interaction, current: str):
        return await self.any_form_choices(interaction, current)

    @applications.command(name="delete", description="Remove an application form")
    @app_commands.describe(form="Which form to remove")
    async def applications_delete(self, interaction: discord.Interaction, form: str) -> None:
        if not await require_staff(interaction):
            return
        found = await self._form(interaction, form)
        if found is None:
            return
        waiting = await forms.pending_count(self.bot.db, found["id"])
        if waiting:
            await answer(
                interaction,
                forms.FORM_HAS_PENDING.format(name=found["name"], count=waiting),
            )
            return
        await forms.delete_form(self.bot.db, found["id"])
        await log_action(
            self.bot,
            interaction.guild,
            "application.form_deleted",
            actor=interaction.user,
            details={"form": found["name"]},
        )
        await answer(interaction, FORM_DELETED.format(name=found["name"]))

    @applications_delete.autocomplete("form")
    async def _delete_forms(self, interaction: discord.Interaction, current: str):
        return await self.any_form_choices(interaction, current)

    question = app_commands.Group(
        name="question",
        description="The boxes one application form asks",
        parent=applications,
    )

    @question.command(name="add", description="Add a question to a form")
    @app_commands.describe(
        form="Which form to add to",
        label="What the box is called; Discord shows 45 characters",
        style="short for one line, long for a paragraph",
        required="False lets somebody leave it blank",
        placeholder="Grey hint text inside the box",
    )
    @app_commands.choices(
        style=[app_commands.Choice(name=one, value=one) for one in forms.STYLES]
    )
    async def question_add(
        self,
        interaction: discord.Interaction,
        form: str,
        label: str,
        style: app_commands.Choice[str] | None = None,
        required: bool = True,
        placeholder: str | None = None,
    ) -> None:
        if not await require_staff(interaction):
            return
        found = await self._form(interaction, form)
        if found is None:
            return
        try:
            position = await forms.add_question(
                self.bot.db,
                found["id"],
                label,
                style.value if style else forms.SHORT,
                required,
                placeholder,
            )
        except forms.ApplicationError as exc:
            await answer(interaction, str(exc))
            return
        await log_action(
            self.bot,
            interaction.guild,
            "application.question_changed",
            actor=interaction.user,
            details={"form": found["name"], "position": position, "what": "added"},
        )
        await answer(
            interaction,
            QUESTION_ADDED.format(label=label, name=found["name"], position=position),
        )

    @question.command(name="edit", description="Change one question on a form")
    @app_commands.describe(
        form="Which form",
        position="Which slot, 1 to 5",
        label="What the box is called",
        style="short for one line, long for a paragraph",
        required="False lets somebody leave it blank",
        placeholder="Grey hint text inside the box",
    )
    @app_commands.choices(
        style=[app_commands.Choice(name=one, value=one) for one in forms.STYLES]
    )
    async def question_edit(
        self,
        interaction: discord.Interaction,
        form: str,
        position: app_commands.Range[int, 1, forms.QUESTIONS_MAX],
        label: str | None = None,
        style: app_commands.Choice[str] | None = None,
        required: bool | None = None,
        placeholder: str | None = None,
    ) -> None:
        if not await require_staff(interaction):
            return
        found = await self._form(interaction, form)
        if found is None:
            return
        try:
            changed = await forms.edit_question(
                self.bot.db,
                found["id"],
                position,
                label=label,
                style=style.value if style else None,
                required=required,
                placeholder=placeholder,
            )
        except forms.ApplicationError as exc:
            await answer(interaction, str(exc))
            return
        if not changed:
            await answer(
                interaction,
                NO_SUCH_QUESTION.format(name=found["name"], position=position),
            )
            return
        await log_action(
            self.bot,
            interaction.guild,
            "application.question_changed",
            actor=interaction.user,
            details={"form": found["name"], "position": position, "what": "edited"},
        )
        await answer(
            interaction, QUESTION_SAVED.format(position=position, name=found["name"])
        )

    @question.command(name="remove", description="Take a question off a form")
    @app_commands.describe(form="Which form", position="Which slot, 1 to 5")
    async def question_remove(
        self,
        interaction: discord.Interaction,
        form: str,
        position: app_commands.Range[int, 1, forms.QUESTIONS_MAX],
    ) -> None:
        if not await require_staff(interaction):
            return
        found = await self._form(interaction, form)
        if found is None:
            return
        if not await forms.remove_question(self.bot.db, found["id"], position):
            await answer(
                interaction, NO_SUCH_QUESTION.format(name=found["name"], position=position)
            )
            return
        await log_action(
            self.bot,
            interaction.guild,
            "application.question_changed",
            actor=interaction.user,
            details={"form": found["name"], "position": position, "what": "removed"},
        )
        await answer(
            interaction, QUESTION_REMOVED.format(position=position, name=found["name"])
        )

    @question.command(name="list", description="The questions one form asks")
    @app_commands.describe(form="Which form")
    async def question_list(self, interaction: discord.Interaction, form: str) -> None:
        if not await require_staff(interaction):
            return
        found = await self._form(interaction, form)
        if found is None:
            return
        rows = await forms.questions_for(self.bot.db, found["id"])
        if not rows:
            await answer(interaction, forms.NO_QUESTIONS_YET.format(name=found["name"]))
            return
        lines = [
            f"**{row['position']}.** {row['label']} — {row['style']}"
            f"{'' if row['required'] else ', optional'}"
            for row in rows
        ]
        await answer(interaction, "\n".join(lines)[:2000])

    @question_add.autocomplete("form")
    async def _qadd_forms(self, interaction: discord.Interaction, current: str):
        return await self.any_form_choices(interaction, current)

    @question_edit.autocomplete("form")
    async def _qedit_forms(self, interaction: discord.Interaction, current: str):
        return await self.any_form_choices(interaction, current)

    @question_remove.autocomplete("form")
    async def _qremove_forms(self, interaction: discord.Interaction, current: str):
        return await self.any_form_choices(interaction, current)

    @question_list.autocomplete("form")
    async def _qlist_forms(self, interaction: discord.Interaction, current: str):
        return await self.any_form_choices(interaction, current)

    @applications.command(name="panel", description="Put a form's Apply button in a channel")
    @app_commands.describe(form="Which form", channel="Where the button goes")
    async def applications_panel(
        self,
        interaction: discord.Interaction,
        form: str,
        channel: discord.TextChannel | None = None,
    ) -> None:
        if not await require_staff(interaction):
            return
        found = await self._form(interaction, form)
        if found is None:
            return
        target = channel or interaction.channel
        if target is None:
            await answer(interaction, forms.PANEL_NOWHERE.format(name=found["name"]))
            return
        guard = getattr(self.bot, "guard", None)
        if guard is not None and not guard.allows_channel(target.id):
            await answer(interaction, guard.refusal_message())
            return
        try:
            message = await post_panel(self.bot, interaction.guild, found, target)
        except Exception as exc:
            log.warning("applications: could not post the panel for %s: %s", found["name"], exc)
            await log_action(
                self.bot,
                interaction.guild,
                "application.post_failed",
                actor=interaction.user,
                details={"form": found["name"], "reason": f"{type(exc).__name__}: {exc}"},
            )
            await answer(interaction, forms.PANEL_STUCK.format(name=found["name"]))
            return
        await log_action(
            self.bot,
            interaction.guild,
            "application.panel_posted",
            actor=interaction.user,
            details={
                "form": found["name"],
                "channel_id": target.id,
                "message_id": message.id,
            },
        )
        await answer(
            interaction,
            PANEL_POSTED.format(name=found["name"], channel_id=target.id),
        )

    @applications_panel.autocomplete("form")
    async def _panel_forms(self, interaction: discord.Interaction, current: str):
        return await self.any_form_choices(interaction, current)

    @applications.command(name="list", description="The forms, and what is waiting on them")
    @app_commands.describe(form="Only this form", status="Only applications in this state")
    @app_commands.choices(
        status=[app_commands.Choice(name=one, value=one) for one in forms.STATUSES]
    )
    async def applications_list(
        self,
        interaction: discord.Interaction,
        form: str | None = None,
        status: app_commands.Choice[str] | None = None,
    ) -> None:
        if not await require_staff(interaction):
            return
        if not self.bot.db.is_connected:
            await answer(interaction, DB_UNAVAILABLE)
            return
        held = await forms.list_forms(self.bot.db, interaction.guild.id)
        if not held:
            await answer(interaction, forms.NO_FORMS_YET)
            return
        wanted = next((one for one in held if one["name"] == str(form or "").lower()), None)
        if form and wanted is None:
            await answer(interaction, forms.NO_SUCH_FORM.format(name=str(form)[:40]))
            return
        rows = await forms.applications_for(
            self.bot.db,
            interaction.guild.id,
            form_id=wanted["id"] if wanted is not None else None,
            statuses=(status.value,) if status else None,
            limit=25,
        )
        named = {one["id"]: one["name"] for one in held}
        listed = {one["id"] for one in held if forms.role_of(one) is None}
        lines = [
            f"**{one['name']}** — {'open' if forms.is_open(one) else 'closed'}, "
            f"{f'<@&{forms.role_of(one)}>' if forms.role_of(one) else 'list'}"
            for one in held
            if wanted is None or one["id"] == wanted["id"]
        ]
        logins = await forms.twitch_logins_for(
            self.bot.db,
            [
                row["user_id"]
                for row in rows
                if row["form_id"] in listed and row["status"] == grants.APPROVED
            ],
        )
        lines.append("")
        lines.extend(
            f"`#{row['id']}` <@{row['user_id']}> · {named.get(row['form_id'], '?')} · "
            f"{row['status']} · {grants.stamp(row['submitted_at'], 'R')}"
            + (
                f" · twitch.tv/{logins[row['user_id']]}"
                if row["form_id"] in listed
                and row["status"] == grants.APPROVED
                and row["user_id"] in logins
                else ""
            )
            for row in rows
        )
        if not rows:
            lines.append(forms.NOTHING_PENDING)
        await answer(interaction, "\n".join(lines)[:2000])

    @applications_list.autocomplete("form")
    async def _list_forms(self, interaction: discord.Interaction, current: str):
        return await self.any_form_choices(interaction, current)

    @applications.command(name="show", description="One application and its answers")
    @app_commands.describe(application_id="The number on the card")
    async def applications_show(
        self, interaction: discord.Interaction, application_id: int
    ) -> None:
        if not await require_staff(interaction):
            return
        if not self.bot.db.is_connected:
            await answer(interaction, DB_UNAVAILABLE)
            return
        row = await forms.get_application(self.bot.db, application_id)
        if row is None or row["guild_id"] != interaction.guild.id:
            await answer(interaction, NOTHING_TO_SHOW)
            return
        form = await forms.get_form_by_id(self.bot.db, row["form_id"])
        view = show_panel(self.bot, interaction.guild.id, form, row, interaction.user)
        await interaction.response.send_message(
            embed=forms.render_card(form, row, interaction.guild.get_member(row["user_id"])),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
            **({"view": view} if view is not None else {}),
        )
        if view is not None:
            view.message = await interaction.original_response()

    @applications.command(
        name="approve",
        description="Say yes to one application",
        extras={"staff_only": True},
    )
    @app_commands.describe(application_id="The number on the card")
    async def applications_approve(
        self, interaction: discord.Interaction, application_id: int
    ) -> None:
        await self._decide(interaction, application_id, grants.APPROVED, None)

    @applications.command(
        name="deny",
        description="Say no to one application, with a reason",
        extras={"staff_only": True},
    )
    @app_commands.describe(
        application_id="The number on the card", reason="One line the applicant is sent"
    )
    async def applications_deny(
        self, interaction: discord.Interaction, application_id: int, reason: str
    ) -> None:
        await self._decide(interaction, application_id, grants.DENIED, reason)

    async def _decide(
        self, interaction: discord.Interaction, application_id: int, status: str, reason: Any
    ) -> None:
        if interaction.guild is None:
            await answer(interaction, NOT_IN_GUILD)
            return
        if not self.bot.db.is_connected:
            await answer(interaction, DB_UNAVAILABLE)
            return
        row = await forms.get_application(self.bot.db, application_id)
        if row is None or row["guild_id"] != interaction.guild.id:
            await answer(interaction, forms.NOTHING_TO_DECIDE)
            return
        form = await forms.get_form_by_id(self.bot.db, row["form_id"])
        if form is None:
            await answer(interaction, forms.NOTHING_TO_DECIDE)
            return
        if not await may_decide(interaction, form):
            return
        said, _ = await apply_decision(
            self.bot, interaction.guild, application_id, status, interaction.user, reason=reason
        )
        await answer(interaction, said)

    @applications.command(name="logs", description="The last few application log lines")
    @app_commands.describe(
        count="How many lines, 1 to 50 (10 by default)",
        important_only="True to leave out the dry runs and the housekeeping",
    )
    async def applications_logs(
        self,
        interaction: discord.Interaction,
        count: app_commands.Range[int, LOGS_MIN, LOGS_MAX] = LOGS_DEFAULT,
        important_only: bool = False,
    ) -> None:
        await send_logs(interaction, FEATURE, count=count, important_only=important_only)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Applications(bot))
