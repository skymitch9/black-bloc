"""The public copy of a tracked marathon's reminders, beside the staff thread's."""

from __future__ import annotations

import logging
from typing import Any

from ... import marathon as mt
from ... import marathon_role_ping as mrp
from ... import shadow as shadow_home
from ...actionlog import log_action
from ...golive import ping_prefix
from ...settings_store import (
    MARATHON_PUBLIC_REMINDER_TEMPLATE_KEY,
    MARATHON_PUBLIC_REMINDERS_KEY,
    MARATHON_REMINDER_CHANNEL_KEY,
)
from ...spotlight import reason_of
from .marathon import (
    GOLIVE_CHANNEL_KEY,
    MODE_ON,
    channel_login,
    mode_of,
    said_default,
    words_for,
)
from .marathon_announce import announces
from .marathon_public import people_for, rehearsal_of, send_public

log = logging.getLogger(__name__)


def reminder_channel(bot: Any, guild_id: int) -> int | None:
    """The reminder channel the key names, else go-live."""
    for key in (MARATHON_REMINDER_CHANNEL_KEY, GOLIVE_CHANNEL_KEY):
        found = shadow_home.as_channel_id(bot.store.get(guild_id, key))
        if found is not None:
            return found
    return None


def wanted(bot: Any, guild_id: int) -> bool:
    return bool(bot.store.get(guild_id, MARATHON_PUBLIC_REMINDERS_KEY))


def reminder_text(
    bot: Any, guild: Any, marathon: Any, row: Any, *, url: str, people: Any = None
) -> str:
    """A runner's public reminder, or a host's when `people` names the BaF hosts: one template."""
    said = words_for(bot, guild.id)
    return mt.render(
        said[MARATHON_PUBLIC_REMINDER_TEMPLATE_KEY],
        said_default(MARATHON_PUBLIC_REMINDER_TEMPLATE_KEY),
        **mt.run_fields(row, marathon, said, url=url, people=people),
    ).text


def staff_went_to(cog: Any, guild: Any, staff_channel_id: Any) -> int | None:
    """The real channel the staff copy stands for: its thread, or the marathon channel when it
    has none (whose copy may sit in a rehearsal home)."""
    if not staff_channel_id:
        return None
    if int(staff_channel_id) == cog._target(guild):
        return cog._home(guild)
    return int(staff_channel_id)


async def post_public_reminder(
    cog: Any,
    guild: Any,
    marathon: Any,
    row: Any,
    mark: int,
    roles: list[int],
    *,
    url: str | None,
    staff_channel_id: Any = None,
    marathon_role: mrp.Verdict | None = None,
) -> dict[str, Any]:
    """Rides the staff copy's sent-marker, so a restart never posts it twice; a failure here is
    a log line and never touches the staff copy. It answers what this copy mentioned."""
    bot = cog.bot
    if marathon_role is not None and mode_of(bot, guild.id) != MODE_ON:
        marathon_role = mrp.unsent(marathon_role, mrp.REHEARSAL)
    quiet = mrp.row_fields(
        None if marathon_role is None else mrp.unsent(marathon_role, mrp.NO_PUBLIC_COPY)
    )
    unsent = {"public_roles": []} | quiet
    try:
        if not wanted(bot, guild.id):
            return unsent
        home = reminder_channel(bot, guild.id)
        base = cog.run_details(marathon, row) | {"mark": mark, "public": True} | quiet
        if home is None:
            await log_action(
                bot,
                guild,
                "marathon.public_reminder_failed",
                details=base | {"reason": "no_channel"},
            )
            return unsent
        if staff_went_to(cog, guild, staff_channel_id) == home:
            await log_action(
                bot,
                guild,
                "marathon.public_reminder_skipped",
                details=base | {"because": "same_channel", "channel_id": home},
            )
            return unsent
        people = people_for(marathon, row)
        because = (
            "announcements_off"
            if not announces(bot, guild.id, marathon)
            else ("opted_out" if not people else None)
        )
        if because is not None:
            await log_action(
                bot, guild, "marathon.public_reminder_skipped", details=base | {"because": because}
            )
            return unsent
        if url and people != mt.ours(mt.people_of(row)):
            url = mt.run_url(
                row, await channel_login(bot, marathon), marathon["schedule_url"], people=people
            )
        text = reminder_text(bot, guild, marathon, row, url=url, people=people)
        roles = mrp.with_role(roles, marathon_role)
        message, channel_id, why = await send_public(
            bot, guild, ping_prefix(*roles) + text, roles, home=home
        )
        details = base | {
            "pinged": bool(roles),
            "roles": roles,
            "channel_id": channel_id,
            "message_id": str(getattr(message, "id", "")) or None,
        }
        if message is None:
            await log_action(
                bot,
                guild,
                "marathon.public_reminder_failed",
                details=details | {"reason": why, "pinged": False, "roles": []},
            )
            return unsent
        shadow = mode_of(bot, guild.id) != MODE_ON
        await log_action(
            bot,
            guild,
            "marathon.would_remind_public" if shadow else "marathon.public_reminded",
            details=details | mrp.row_fields(marathon_role) | rehearsal_of(bot, guild),
        )
        return {"public_roles": roles} | mrp.row_fields(marathon_role)
    except Exception as exc:
        log.warning("marathon: the public reminder failed — %s", reason_of(exc))
        return unsent


__all__ = ["post_public_reminder", "reminder_channel", "reminder_text", "staff_went_to", "wanted"]
