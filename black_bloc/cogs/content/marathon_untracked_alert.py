"""The untracked alert, posted in the marathon inbox as a reply to the marathon's message."""

from __future__ import annotations

from typing import Any

import discord

from ... import marathon_untracked_alert as ua
from ...actionlog import log_action
from ...settings_store import (
    MARATHON_UNTRACKED_ALERT_HOURS_KEY,
    MARATHON_UNTRACKED_ALERT_ROLE_KEY,
    MARATHON_UNTRACKED_ALERT_TEMPLATE_KEY,
)
from ...spotlight import reason_of
from .marathon import (
    MODE_ON,
    TEST_MODE,
    _cell,
    get_marathon,
    mode_of,
    rehearsal_details,
    runs_of,
    update_marathon,
)
from .marathon_inbox import (
    ensure_inbox,
    home_now,
    note_for,
    real_inbox_parent,
    words,
)

SKIPS_ATTR = "untracked_alert_skips"


def role_of(bot: Any, guild: Any) -> tuple[Any, str | None]:
    found = bot.store.get(guild.id, MARATHON_UNTRACKED_ALERT_ROLE_KEY)
    try:
        role_id = int(found) if found else None
    except (TypeError, ValueError):
        role_id = None
    if role_id is None:
        return (None, ua.NO_ROLE)
    getter = getattr(guild, "get_role", None)
    role = getter(role_id) if callable(getter) else None
    return (role, None) if role is not None else (None, ua.ROLE_GONE)


def reply_to(cog: Any, marathon: Any, home: str, thread: Any) -> Any:
    posted = _cell(marathon, "inbox_message_id")
    if not posted or _cell(marathon, "inbox_home") != home:
        return None
    if int(marathon["id"]) in getattr(cog, "inbox_moved", ()):
        return None
    return discord.MessageReference(
        message_id=int(posted), channel_id=int(thread.id), fail_if_not_exists=False
    )


async def skipped_once(cog: Any, guild: Any, details: dict[str, Any], why: str) -> None:
    seen = cog.__dict__.setdefault(SKIPS_ATTR, set())
    key = (int(guild.id), details["marathon_id"], why)
    if key in seen:
        return
    seen.add(key)
    await log_action(
        cog.bot,
        guild,
        "marathon.untracked_alert",
        details=details | {"outcome": ua.SKIPPED, "reason": why},
    )


async def alert_if_due(cog: Any, guild: Any, marathon: Any) -> bool:
    """Called with the marathon's lock held. A missing role waits unstamped; anything else is
    stamped before the send, so a failure is never retried."""
    bot = cog.bot
    hours = int(bot.store.get(guild.id, MARATHON_UNTRACKED_ALERT_HOURS_KEY) or 0)
    home = home_now(bot, guild)
    if not hours or home is None or marathon is None:
        return False
    fresh = await get_marathon(bot.db, guild.id, marathon["id"])
    runs = await runs_of(bot.db, marathon["id"]) if fresh is not None else []
    now = cog.clock()
    if not ua.wanted(fresh, runs, now, hours):
        return False
    details = ua.details_of(fresh, runs, now)
    role, why = role_of(bot, guild)
    if role is None:
        await skipped_once(cog, guild, details, why)
        return False
    await update_marathon(bot.db, fresh["id"], **{ua.COLUMN: now.isoformat()})
    shadow = mode_of(bot, guild.id) != MODE_ON
    details |= {"role_id": str(role.id), "shadow": shadow} | rehearsal_details(bot, guild)
    thread, why = await ensure_inbox(bot, guild)
    guard = getattr(bot, "guard", None)
    if thread is not None and guard is not None and not guard.allows_channel(thread.id):
        thread, why = None, TEST_MODE
    if thread is None:
        await log_action(
            bot,
            guild,
            "marathon.untracked_alert",
            details=details | {"outcome": ua.FAILED, "reason": why},
        )
        return False
    text = words(
        bot,
        guild.id,
        MARATHON_UNTRACKED_ALERT_TEMPLATE_KEY,
        **ua.fields_of(fresh, runs, now, f"<@&{int(role.id)}>"),
    )
    body = note_for(bot, guild, home, real_inbox_parent(bot, guild), text)
    mentions = (
        discord.AllowedMentions.none()
        if shadow
        else discord.AllowedMentions(everyone=False, users=False, roles=[discord.Object(role.id)])
    )
    reference = reply_to(cog, fresh, home, thread)
    extra = {"reference": reference} if reference is not None else {}
    try:
        message = await thread.send(body, allowed_mentions=mentions, **extra)
    except Exception as exc:
        await log_action(
            bot,
            guild,
            "marathon.untracked_alert",
            details=details | {"outcome": ua.FAILED, "reason": reason_of(exc)},
        )
        return False
    await log_action(
        bot,
        guild,
        "marathon.untracked_alert",
        details=details
        | {
            "outcome": ua.POSTED,
            "thread_id": int(thread.id),
            "message_id": str(message.id),
            "reply": reference is not None,
        },
    )
    return True


__all__ = ["alert_if_due", "role_of"]
