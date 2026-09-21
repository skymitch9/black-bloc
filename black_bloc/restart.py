"""Restarting the bot from the dashboard: the clean shutdown, then a non-zero exit."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .errors import EXIT_RESTART

log = logging.getLogger(__name__)

DOWN_SECONDS = 15
ANSWER_GRACE = 1.0
CLOSE_TIMEOUT = 10.0
TASK_ATTR = "_restart_task"

RESTARTING = (
    "Black Bloc is restarting. This site is served by the bot itself, so it stops answering "
    "for about {seconds} seconds — reload this page then."
)
NOT_A_LEAD = (
    "Restarting Black Bloc needs **Manage Server** in Discord, and none of your roles here "
    "have it, so nothing was done. Ask a server admin to press it, or to add that permission "
    "to one of your roles."
)
CANNOT_RESTART = (
    "This Black Bloc cannot restart itself, so nothing was done. That is a fault in the bot "
    "rather than a problem with your access — restart it where it runs and tell a Lead."
)


def manages_guild(member: Any) -> bool:
    """Manage Server, computed — the permission, never a role name."""
    perms = getattr(member, "guild_permissions", None)
    return bool(getattr(perms, "manage_guild", False))


def can_restart(bot: Any) -> bool:
    """Only a bot that was given a way out; a test double has none unless it asks for one."""
    return callable(getattr(bot, "exit_now", None))


def restarting_said(seconds: int = DOWN_SECONDS) -> str:
    return RESTARTING.format(seconds=seconds)


async def shut_down(
    bot: Any, *, grace: float = ANSWER_GRACE, close_timeout: float = CLOSE_TIMEOUT
) -> None:
    try:
        await asyncio.sleep(grace)
        try:
            await asyncio.wait_for(bot.close(), timeout=close_timeout)
        except Exception as exc:
            log.error("restart: the clean shutdown failed — %s: %s", type(exc).__name__, exc)
    finally:
        log.warning("restart: exiting %s so the host starts a fresh process", EXIT_RESTART)
        bot.exit_now(EXIT_RESTART)


def schedule(bot: Any, *, grace: float = ANSWER_GRACE) -> Any:
    task = asyncio.create_task(shut_down(bot, grace=grace), name="restart")
    setattr(bot, TASK_ATTR, task)
    return task
