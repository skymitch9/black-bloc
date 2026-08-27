from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ...automod import (
    DEFAULT_RULES,
    RULE_HELP,
    RULE_ORDER,
    TIMEOUT_MAX_SECONDS,
    RuleError,
    rule_config,
)
from ...cogs.moderation.automod import apply_case, save_rule
from ...cogs.moderation.modcmds import (
    NOT_BANNED,
    REFUSED,
    TIMEOUT_TOO_LONG,
    ban_member,
    kick_member,
    refuse_in_test_mode,
    timeout_member,
    unban_member,
    untimeout_member,
    warn_member,
)
from ...modcases import (
    CASES_PER_PAGE,
    cases_for,
    count_all_cases,
    count_cases,
    duration_error,
    from_list_json,
    get_case,
    parse_duration,
    recent_cases,
    row_value,
)
from ..auth import Refused, staff_dependency
from ..names import resolve_one
from ..writes import (
    actor_for,
    guard_of,
    note,
    reader_dependency,
    refuse_guarded,
    require_db,
    require_guild,
    wanted_id,
    writer_dependency,
)

log = logging.getLogger(__name__)

REASON_LIMIT = 500
PURGE_DAYS_MAX = 7

WORDING = {
    "timeout": "time out",
    "untimeout": "lift anyone's timeout",
    "kick": "kick",
    "ban": "ban",
    "unban": "lift anyone's ban",
}
NOT_A_MEMBER = (
    "**{user_id}** is not a member of this server, so nothing was done. Pick somebody from the "
    "member list, or use their id if they have left and you are lifting a ban."
)
NO_SUCH_CASE = (
    "Black Bloc has no case **#{case_id}**, so there is nothing to show. The cases table lists "
    "the ones it has."
)
APPLY_REFUSED = {
    "no_such_case": (404, "no_such_case"),
    "member_gone": (409, "member_gone"),
    "already": (409, "already_applied"),
    "raced": (409, "already_applied"),
    "test_mode": (409, "test_mode"),
    "refused": (502, "discord_refused"),
}
NO_REASON = "no reason given"
BAD_PURGE_DAYS = (
    "**{given}** is not a number of days of messages to delete, so nobody was banned. It is a "
    "whole number from 0 to 7 — Discord will not delete more than a week of a banned member's "
    "messages."
)


def wanted_purge_days(given: Any) -> int:
    if given is None or given == "":
        return 0
    try:
        days = int(str(given).strip())
    except (TypeError, ValueError):
        days = None
    if days is None or not 0 <= days <= PURGE_DAYS_MAX:
        raise Refused(400, "bad_purge_days", BAD_PURGE_DAYS.format(given=str(given)[:40]))
    return days


def case_row(guild: Any, row: Any) -> dict[str, Any]:
    user_id = row["user_id"]
    moderator_id = row["moderator_id"]
    return {
        "id": row["id"],
        "kind": row["kind"],
        "user_id": str(user_id) if user_id else None,
        "user_name": resolve_one(guild, user_id)["display_name"] if user_id else None,
        "moderator_id": str(moderator_id) if moderator_id else None,
        "moderator_name": (
            resolve_one(guild, moderator_id)["display_name"] if moderator_id else None
        ),
        "reason": row["reason"],
        "duration_s": row["duration_s"],
        "at": row["at"],
        "mode": row["mode"],
        "applied": bool(row["applied"]),
        "actions": from_list_json(row_value(row, "actions")),
        "done": from_list_json(row_value(row, "done")),
        "failed": from_list_json(row_value(row, "failed")),
        "channel_id": (
            str(row_value(row, "channel_id")) if row_value(row, "channel_id") else None
        ),
    }


def rule_row(rules: Any, name: str) -> dict[str, Any]:
    return {"name": name, "help": RULE_HELP.get(name, "")} | rule_config(rules, name)


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    reader = reader_dependency(bot)
    router = APIRouter(
        prefix="/api/mod", tags=["mod"], dependencies=[Depends(staff_dependency(bot))]
    )

    async def _refuse_under_guard(guild: Any, target: Any, kind: str, actor: Any, reason: Any):
        said = await refuse_in_test_mode(
            bot, guild, target, kind, WORDING[kind], moderator=actor, reason=reason
        )
        refuse_guarded(said)

    async def _punish(request: Request, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        user_id = wanted_id(payload.get("user_id"))
        reason = str(payload.get("reason") or "").strip()[:REASON_LIMIT] or None
        actor = actor_for(bot, who, guild)
        seconds = None
        purge_days = 0
        if kind == "timeout":
            seconds = parse_duration(payload.get("duration"))
            if seconds is None:
                raise Refused(400, "bad_duration", duration_error(payload.get("duration")))
            if seconds > TIMEOUT_MAX_SECONDS:
                raise Refused(400, "too_long", TIMEOUT_TOO_LONG)
        if kind == "ban":
            purge_days = wanted_purge_days(payload.get("purge_days"))
        if kind != "warn" and guard_of(bot) is not None:
            await _refuse_under_guard(guild, user_id, kind, actor, reason)
        member = guild.get_member(user_id)
        if member is None and kind != "unban":
            raise Refused(404, "not_a_member", NOT_A_MEMBER.format(user_id=user_id))
        if kind == "warn":
            said = await warn_member(bot, guild, member, actor, reason or NO_REASON)
        elif kind == "timeout":
            said = await timeout_member(bot, guild, member, actor, seconds, reason)
        elif kind == "untimeout":
            said = await untimeout_member(bot, guild, member, actor, reason)
        elif kind == "kick":
            said = await kick_member(bot, guild, member, actor, reason)
        elif kind == "ban":
            said = await ban_member(bot, guild, member, actor, reason, purge_days)
        else:
            said = await unban_member(bot, guild, user_id, actor, reason)
            if said == NOT_BANNED.format(user_id=user_id):
                raise Refused(404, "not_banned", said)
        if said == REFUSED.get(kind):
            raise Refused(502, "discord_refused", said)
        await note(bot, guild, f"web.mod.{kind}", who, target=user_id, reason=reason)
        return {"done": True, "kind": kind, "user_id": str(user_id), "message": said}

    @router.get("/cases", dependencies=[Depends(reader)])
    async def mod_cases(user_id: str = "", page: int = 1) -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(user_id) if user_id else None
        total = (
            await count_cases(bot.db, guild.id, wanted)
            if wanted is not None
            else await count_all_cases(bot.db, guild.id)
        )
        pages = max(1, -(-total // CASES_PER_PAGE))
        at = max(1, min(int(page or 1), pages))
        offset = (at - 1) * CASES_PER_PAGE
        rows = (
            await cases_for(bot.db, guild.id, wanted, CASES_PER_PAGE, offset)
            if wanted is not None
            else await recent_cases(bot.db, guild.id, CASES_PER_PAGE, offset)
        )
        return {
            "cases": [case_row(guild, row) for row in rows],
            "total": total,
            "page": at,
            "pages": pages,
            "per_page": CASES_PER_PAGE,
        }

    @router.get("/cases/{case_id}")
    async def mod_case(case_id: int) -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        row = await get_case(bot.db, case_id)
        if row is None or row["guild_id"] != guild.id:
            raise Refused(404, "no_such_case", NO_SUCH_CASE.format(case_id=case_id))
        return case_row(guild, row)

    @router.post("/cases/{case_id}/apply")
    async def mod_case_apply(request: Request, case_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await get_case(bot.db, case_id)
        if row is None or row["guild_id"] != guild.id:
            raise Refused(404, "no_such_case", NO_SUCH_CASE.format(case_id=case_id))
        outcome, said = await apply_case(bot, guild, case_id, actor_for(bot, who, guild))
        if outcome != "applied":
            status, error = APPLY_REFUSED.get(outcome, (409, "apply_refused"))
            raise Refused(status, error, said)
        await note(
            bot,
            guild,
            "web.mod.apply",
            who,
            target=row["user_id"],
            details={"case_id": case_id},
        )
        return {"applied": True, "case_id": case_id, "message": said}

    @router.post("/warn")
    async def mod_warn(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        return await _punish(request, "warn", payload)

    @router.post("/timeout")
    async def mod_timeout(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        return await _punish(request, "timeout", payload)

    @router.post("/untimeout")
    async def mod_untimeout(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        return await _punish(request, "untimeout", payload)

    @router.post("/kick")
    async def mod_kick(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        return await _punish(request, "kick", payload)

    @router.post("/ban")
    async def mod_ban(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        return await _punish(request, "ban", payload)

    @router.post("/unban")
    async def mod_unban(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        return await _punish(request, "unban", payload)

    @router.get("/rules")
    async def mod_rules() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        rules = bot.store.get(guild.id, "automod_rules")
        return [rule_row(rules, name) for name in RULE_ORDER]

    @router.put("/rules/{name}")
    async def mod_rule_set(
        request: Request, name: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        known = DEFAULT_RULES.get(name, {})
        changes = {key: value for key, value in payload.items() if key in known}
        try:
            rule = await save_rule(bot, guild, name, changes, actor_for(bot, who, guild))
        except (RuleError, ValueError) as exc:
            raise Refused(400, "bad_rule", str(exc)) from None
        await note(bot, guild, "web.mod.rule", who, details={"rule": name} | changes)
        return {"name": name, "help": RULE_HELP.get(name, "")} | rule

    return router
