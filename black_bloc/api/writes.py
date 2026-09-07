from __future__ import annotations

import logging
from typing import Any

from fastapi import Request

from ..actionlog import log_action
from .auth import (
    MEMBER_UNKNOWN,
    NOT_A_MEMBER,
    OPERATOR_WHO,
    READ_BUCKET_ATTR,
    READ_RATE,
    READ_WINDOW_SECONDS,
    TOO_MANY_READS,
    Refused,
    TokenBucket,
    _bucket,
    current_session,
    guild_of,
    member_state,
    read_bucket_for,
    staff_dependency,
)
from .status import DB_UNREACHABLE

log = logging.getLogger(__name__)

WRITE_RATE = 60
WRITE_WINDOW_SECONDS = 60
BUCKET_ATTR = "_api_write_bucket"

MEMBER_RATE = 10
MEMBER_WINDOW_SECONDS = 60
MEMBER_BUCKET_ATTR = "_api_member_bucket"

TOO_MANY_WRITES = (
    "That is more changes than Black Bloc will take in a minute, so this one was not made. "
    "Nothing is wrong with your account — wait a minute and try again."
)
TOO_MANY_MEMBER_WRITES = (
    "That is more requests than Black Bloc will take from one person in a minute, so this one "
    "was not filed. Nothing is wrong with your account — wait a minute and send it again."
)
NO_GUILD = (
    "Black Bloc is not in a server it can change anything in yet, so nothing was done. That is a "
    "setup step, not a fault with your access."
)
FEATURE_OFF = (
    "The {feature} part of Black Bloc is not loaded right now, so nothing was done. That is a "
    "fault in the bot rather than a problem with your access — tell a Lead if it lasts."
)
NOT_A_NUMBER = (
    "**{given}** is not an id Black Bloc can read, so nothing was done. Ids are the long numbers "
    "Discord shows under Copy ID."
)


class WebActor:
    """The signed-in staffer, shaped like the member the cogs' helpers expect."""

    def __init__(self, user_id: int, name: str) -> None:
        self.id = int(user_id)
        self.name = name or str(user_id)
        self.display_name = self.name
        self.mention = f"<@{self.id}>"

    def __str__(self) -> str:
        return self.display_name


def bucket_for(bot: Any) -> TokenBucket:
    """One bucket per bot, so the limit is per session and not per router."""
    return _bucket(bot, BUCKET_ATTR, WRITE_RATE, WRITE_WINDOW_SECONDS)


def member_bucket_for(bot: Any) -> TokenBucket:
    return _bucket(bot, MEMBER_BUCKET_ATTR, MEMBER_RATE, MEMBER_WINDOW_SECONDS)


def member_dependency(bot: Any):
    """Signed in AND in the server — the only gate on the site that is not staff-only."""

    async def dependency(request: Request) -> dict[str, Any]:
        who = await current_session(request, bot)
        state = member_state(who)
        if state == "member_unknown":
            raise Refused(503, "member_unknown", MEMBER_UNKNOWN)
        if state == "not_a_member":
            raise Refused(403, "not_a_member", NOT_A_MEMBER)
        if not member_bucket_for(bot).take(str(who["id"])):
            log.warning("api: rate-limited member writes from %s", who["id"])
            raise Refused(429, "slow_down", TOO_MANY_MEMBER_WRITES)
        return who

    return dependency


def writer_dependency(bot: Any):
    staff = staff_dependency(bot)

    async def dependency(request: Request) -> dict[str, Any]:
        who = await staff(request)
        if not bucket_for(bot).take(str(who["id"])):
            log.warning("api: rate-limited writes from %s", who["id"])
            raise Refused(429, "slow_down", TOO_MANY_WRITES)
        return who

    return dependency


def reader_dependency(bot: Any):
    staff = staff_dependency(bot)

    async def dependency(request: Request) -> dict[str, Any]:
        who = await staff(request)
        if str(who["id"]) == OPERATOR_WHO["id"]:
            return who
        if not read_bucket_for(bot).take(str(who["id"])):
            log.warning("api: rate-limited reads from %s", who["id"])
            raise Refused(429, "slow_down", TOO_MANY_READS)
        return who

    return dependency


def require_guild(bot: Any) -> Any:
    guild = guild_of(bot)
    if guild is None:
        raise Refused(503, "no_guild", NO_GUILD)
    return guild


def require_db(bot: Any) -> Any:
    db = getattr(bot, "db", None)
    if db is None or not db.is_connected:
        raise Refused(503, "database_unavailable", DB_UNREACHABLE)
    return db


def require_cog(bot: Any, name: str, feature: str) -> Any:
    cog = bot.get_cog(name) if callable(getattr(bot, "get_cog", None)) else None
    if cog is None:
        log.warning("api: %s is not loaded, so a write was refused", name)
        raise Refused(503, "feature_unavailable", FEATURE_OFF.format(feature=feature))
    return cog


def guard_of(bot: Any) -> Any:
    return getattr(bot, "guard", None)


def refuse_guarded(sentence: str) -> None:
    """Every destructive route says the same thing the slash command says, with 409."""
    raise Refused(409, "test_mode", sentence)


def actor_for(bot: Any, who: dict[str, Any], guild: Any = None) -> Any:
    """The cached member when Discord knows them here, otherwise the session itself."""
    user_id = int(who["id"])
    home = guild if guild is not None else guild_of(bot)
    member = home.get_member(user_id) if home is not None else None
    return member if member is not None else WebActor(user_id, str(who.get("name") or ""))


def wanted_id(given: Any) -> int:
    digits = str(given or "").strip().lstrip("<#@&!").rstrip(">")
    if not digits.isdigit():
        raise Refused(400, "bad_request", NOT_A_NUMBER.format(given=str(given or "")[:40]))
    return int(digits)


async def note(
    bot: Any,
    guild: Any,
    kind: str,
    who: dict[str, Any],
    *,
    target: Any = None,
    reason: Any = None,
    details: dict[str, Any] | None = None,
) -> None:
    """The `web.*` line every write leaves, so the log tells web from slash."""
    await log_action(
        bot,
        guild,
        kind,
        actor=actor_for(bot, who, guild),
        target=target,
        reason=reason,
        details=details,
    )


__all__ = [
    "FEATURE_OFF",
    "MEMBER_RATE",
    "NO_GUILD",
    "READ_BUCKET_ATTR",
    "READ_RATE",
    "READ_WINDOW_SECONDS",
    "TOO_MANY_MEMBER_WRITES",
    "TOO_MANY_READS",
    "TOO_MANY_WRITES",
    "WRITE_RATE",
    "WebActor",
    "actor_for",
    "bucket_for",
    "guard_of",
    "member_bucket_for",
    "member_dependency",
    "note",
    "read_bucket_for",
    "reader_dependency",
    "refuse_guarded",
    "require_cog",
    "require_db",
    "require_guild",
    "wanted_id",
    "writer_dependency",
]
