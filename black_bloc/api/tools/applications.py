from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ... import applications as forms
from ... import rolegrants as grants
from ...cogs.community.applications import (
    apply_decision,
    mode_of,
    post_panel,
)
from ...logkinds import VIA_WEBSITE
from ..auth import Refused, staff_dependency
from ..names import as_id, avatar_url, resolve_one
from ..writes import (
    actor_for,
    guard_of,
    note,
    refuse_guarded,
    require_db,
    require_guild,
    writer_dependency,
)

log = logging.getLogger(__name__)

NEEDS_A_NAME = (
    "An application form needs a short name, a heading and the role it hands over, so nothing "
    "was created. Fill all three in and try again."
)
NO_SUCH_FORM_ID = (
    "Black Bloc has no application form with that number any more, so nothing was changed. "
    "Reload the Role menus page — somebody may have deleted it."
)
NO_SUCH_APPLICATION = (
    "Black Bloc has no application with that number any more, so nothing was changed. Reload "
    "the Role menus page."
)
NO_SUCH_ROLE = (
    "**{role_id}** is not a role in this server any more, so the form was left as it was. "
    "Refresh the page and pick the role again."
)
UNASSIGNABLE = (
    "Black Bloc cannot hand out **{name}**, so the form was not saved. That role is either "
    "above Black Bloc's own role in Server Settings → Roles, or managed by another app. Ask an "
    "admin to move Black Bloc's role above it, then try again."
)
NO_SUCH_CHANNEL = (
    "**{channel_id}** is not a channel Black Bloc can see, so nothing was posted. Pick one from "
    "the list and try again."
)
UNKNOWN_STATUS = (
    "**{given}** is not a state an application can be in, so nothing was listed. They are "
    "{known}."
)
BAD_DECISION = (
    "**{given}** is not a decision, so nothing was changed. It is `approved` or `denied`."
)
BAD_QUESTIONS = (
    "The questions arrived in a shape Black Bloc could not read, so nothing was changed. It is "
    "a fault in the page rather than in what you typed — reload the Role menus page and try "
    "again."
)


def question_row(row: Any) -> dict[str, Any]:
    return {
        "position": int(row["position"]),
        "label": row["label"],
        "style": row["style"],
        "required": bool(row["required"]),
        "placeholder": row["placeholder"],
    }


def form_row(guild: Any, form: Any, questions: Any, waiting: int = 0) -> dict[str, Any]:
    owner = forms.owner_of(form)
    return {
        "id": form["id"],
        "name": form["name"],
        "title": form["title"],
        "description": form["description"],
        "role_id": str(form["role_id"]),
        "role_name": resolve_one(guild, form["role_id"])["display_name"],
        "review_channel_id": str(form["review_channel_id"]) if form["review_channel_id"] else None,
        "approver_role_id": str(form["approver_role_id"]) if form["approver_role_id"] else None,
        "owner_user_id": str(owner) if owner else None,
        "owner_name": resolve_one(guild, owner)["display_name"] if owner else None,
        "next_step": form["next_step"],
        "approved_text": form["approved_text"],
        "expires_days": forms.expires_days_of(form),
        "retry_days": form["retry_days"],
        "open": forms.is_open(form),
        "panel_channel_id": str(form["panel_channel_id"]) if form["panel_channel_id"] else None,
        "panel_message_id": str(form["panel_message_id"]) if form["panel_message_id"] else None,
        "pending": waiting,
        "questions": [question_row(one) for one in questions],
    }


def application_row(guild: Any, row: Any, form_name: Any = None) -> dict[str, Any]:
    by = row["decided_by"]
    member = guild.get_member(row["user_id"]) if guild is not None else None
    return {
        "id": row["id"],
        "form_id": str(row["form_id"]),
        "form_name": form_name,
        "user_id": str(row["user_id"]),
        "user_name": resolve_one(guild, row["user_id"])["display_name"],
        "user_avatar": avatar_url(member) if member is not None else None,
        "status": row["status"],
        "submitted_at": row["submitted_at"],
        "decided_by_id": str(by) if by else None,
        "decided_by_name": resolve_one(guild, by)["display_name"] if by else None,
        "decided_at": row["decided_at"],
        "deny_reason": row["deny_reason"],
        "grant_id": str(row["grant_id"]) if row["grant_id"] else None,
        "answers": forms.read_answers(row["answers"]),
    }


def wanted_statuses(given: Any) -> tuple[str, ...]:
    wanted = tuple(part for part in str(given or "").split(",") if part)
    for part in wanted:
        if part not in forms.STATUSES:
            raise Refused(
                400,
                "unknown_status",
                UNKNOWN_STATUS.format(given=part, known=", ".join(forms.STATUSES)),
            )
    return wanted or forms.STATUSES


def wanted_role(guild: Any, role_id: Any) -> Any:
    role = guild.get_role(as_id(role_id)) if as_id(role_id) is not None else None
    if role is None:
        raise Refused(400, "no_such_role", NO_SUCH_ROLE.format(role_id=role_id))
    assignable = getattr(role, "is_assignable", None)
    if callable(assignable) and not assignable():
        raise Refused(400, "role_refused", UNASSIGNABLE.format(name=role.name))
    return role


async def checked(call: Any, *args: Any, **kwargs: Any) -> Any:
    """Every wording refusal the slash commands give, given with a 400 instead."""
    try:
        return await call(*args, **kwargs)
    except forms.ApplicationError as exc:
        raise Refused(400, "bad_request", str(exc)) from None


async def read_form(bot: Any, guild: Any, form_id: int) -> Any:
    form = await forms.get_form_by_id(bot.db, form_id)
    if form is None or form["guild_id"] != guild.id:
        raise Refused(404, "no_such_form", NO_SUCH_FORM_ID)
    return form


async def one_form(bot: Any, guild: Any, form: Any) -> dict[str, Any]:
    return form_row(
        guild,
        form,
        await forms.questions_for(bot.db, form["id"]),
        await forms.pending_count(bot.db, form["id"]),
    )


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/applications",
        tags=["applications"],
        dependencies=[Depends(staff_dependency(bot))],
    )

    @router.get("/status")
    async def applications_status() -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        held = await forms.list_forms(bot.db, guild.id)
        waiting = await forms.applications_for(
            bot.db, guild.id, statuses=(grants.PENDING,), limit=500
        )
        return {
            "mode": mode_of(bot, guild.id),
            "forms": len(held),
            "open_forms": len([one for one in held if forms.is_open(one)]),
            "pending": len(waiting),
            "questions_max": forms.QUESTIONS_MAX,
        }

    @router.get("/forms")
    async def applications_forms() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        return [
            await one_form(bot, guild, form)
            for form in await forms.list_forms(bot.db, guild.id)
        ]

    @router.post("/forms")
    async def applications_form_create(
        request: Request, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        name = str(payload.get("name") or "").strip()
        title = str(payload.get("title") or "").strip()
        if not name or not title or payload.get("role_id") in (None, ""):
            raise Refused(400, "bad_request", NEEDS_A_NAME)
        role = wanted_role(guild, payload.get("role_id"))
        form_id = await checked(
            forms.create_form,
            bot.db,
            guild.id,
            name,
            title,
            role.id,
            int(who["id"]),
            description=payload.get("description"),
            review_channel_id=as_id(payload.get("review_channel_id")),
            approver_role_id=as_id(payload.get("approver_role_id")),
        )
        if form_id is None:
            raise Refused(400, "name_taken", forms.NAME_TAKEN.format(name=name))
        await note(
            bot,
            guild,
            "web.application.form_created",
            who,
            details={"form": name, "role_id": role.id},
        )
        return await one_form(bot, guild, await read_form(bot, guild, form_id))

    @router.patch("/forms/{form_id}")
    async def applications_form_update(
        request: Request, form_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        form = await read_form(bot, guild, form_id)
        changes: dict[str, Any] = {
            key: payload[key]
            for key in (
                "title",
                "description",
                "next_step",
                "approved_text",
                "expires_days",
                "retry_days",
                "open",
            )
            if key in payload
        }
        if "role_id" in payload:
            changes["role_id"] = wanted_role(guild, payload["role_id"]).id
        for key, field in (
            ("review_channel_id", "review_channel_id"),
            ("approver_role_id", "approver_role_id"),
            ("owner_user_id", "owner_user_id"),
        ):
            if key in payload:
                changes[field] = as_id(payload[key])
        await checked(forms.update_form, bot.db, guild.id, form["name"], **changes)
        await note(
            bot,
            guild,
            "web.application.form_updated",
            who,
            details={"form": form["name"], "changed": sorted(changes)},
        )
        return await one_form(bot, guild, await read_form(bot, guild, form_id))

    @router.delete("/forms/{form_id}")
    async def applications_form_delete(request: Request, form_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        form = await read_form(bot, guild, form_id)
        waiting = await forms.pending_count(bot.db, form_id)
        if waiting:
            raise Refused(
                409,
                "form_has_pending",
                forms.FORM_HAS_PENDING.format(name=form["name"], count=waiting),
            )
        await forms.delete_form(bot.db, form_id)
        await note(
            bot, guild, "web.application.form_deleted", who, details={"form": form["name"]}
        )
        return {"deleted": True, "id": form_id, "name": form["name"]}

    @router.put("/forms/{form_id}/questions")
    async def applications_questions(
        request: Request, form_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        form = await read_form(bot, guild, form_id)
        wanted = payload.get("questions")
        if not isinstance(wanted, list):
            raise Refused(400, "bad_questions", BAD_QUESTIONS)
        await checked(forms.replace_questions, bot.db, form_id, wanted)
        await note(
            bot,
            guild,
            "web.application.question_changed",
            who,
            details={"form": form["name"], "questions": len(wanted)},
        )
        return await one_form(bot, guild, form)

    @router.post("/forms/{form_id}/panel")
    async def applications_panel(
        request: Request, form_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        form = await read_form(bot, guild, form_id)
        channel_id = as_id(payload.get("channel_id")) or as_id(form["panel_channel_id"])
        target = guild.get_channel(channel_id) if channel_id else None
        if target is None:
            raise Refused(
                400, "no_such_channel", NO_SUCH_CHANNEL.format(channel_id=channel_id)
            )
        guard = guard_of(bot)
        if guard is not None and not guard.allows_channel(target.id):
            refuse_guarded(guard.refusal_message())
        message = await post_panel(bot, guild, form, target)
        await note(
            bot,
            guild,
            "web.application.panel_posted",
            who,
            details={
                "form": form["name"],
                "channel_id": target.id,
                "message_id": message.id,
            },
        )
        return {
            "posted": True,
            "id": form_id,
            "name": form["name"],
            "channel_id": str(target.id),
            "message_id": str(message.id),
        }

    @router.get("")
    async def applications_index(form: str = "", status: str = "") -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        held = {one["id"]: one for one in await forms.list_forms(bot.db, guild.id)}
        wanted = as_id(form) if form else None
        rows = await forms.applications_for(
            bot.db,
            guild.id,
            form_id=wanted,
            statuses=wanted_statuses(status),
        )
        return [
            application_row(
                guild,
                row,
                held[row["form_id"]]["name"] if row["form_id"] in held else None,
            )
            for row in rows
        ]

    @router.get("/{application_id}")
    async def applications_show(application_id: int) -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        row = await forms.get_application(bot.db, application_id)
        if row is None or row["guild_id"] != guild.id:
            raise Refused(404, "no_such_application", NO_SUCH_APPLICATION)
        form = await forms.get_form_by_id(bot.db, row["form_id"])
        return application_row(
            guild, row, forms.form_value(form, "name") if form is not None else None
        )

    @router.post("/{application_id}/decide")
    async def applications_decide(
        request: Request, application_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        status = str(payload.get("status") or "")
        if status not in (grants.APPROVED, grants.DENIED):
            raise Refused(400, "bad_status", BAD_DECISION.format(given=status[:40] or "nothing"))
        reason = grants.clamp(payload.get("reason"), forms.REASON_MAX)
        if status == grants.DENIED and not reason:
            raise Refused(400, "no_reason", forms.DENY_NEEDS_A_REASON)
        row = await forms.get_application(bot.db, application_id)
        if row is None or row["guild_id"] != guild.id:
            raise Refused(404, "no_such_application", NO_SUCH_APPLICATION)
        said, fresh = await apply_decision(
            bot,
            guild,
            application_id,
            status,
            actor_for(bot, who, guild),
            reason=reason or None,
            via=VIA_WEBSITE,
        )
        if fresh is None:
            raise Refused(409, "not_decided", said)
        form = await forms.get_form_by_id(bot.db, fresh["form_id"])
        return {
            "application": application_row(
                guild, fresh, forms.form_value(form, "name") if form is not None else None
            ),
            "message": said,
        }

    return router
