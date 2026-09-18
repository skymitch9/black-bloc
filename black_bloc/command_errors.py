from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import aiohttp
import discord
from discord import app_commands

from .actionlog import log_action
from .logkinds import ERROR_BUTTON, ERROR_COMMAND, ERROR_MODAL, ERROR_PANEL
from .settings_store import (
    ERROR_RETRY_EXPIRED,
    ERROR_RETRY_EXPIRED_KEY,
    ERROR_RETRY_LABEL,
    ERROR_RETRY_LABEL_KEY,
    ERROR_RETRY_MAX_MINUTES,
    ERROR_RETRY_MIN_MINUTES,
    ERROR_RETRY_MINUTES,
    ERROR_RETRY_MINUTES_KEY,
    ERROR_SENTENCE,
    ERROR_SENTENCE_KEY,
)

log = logging.getLogger(__name__)

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent

COMMAND_FAILED = (
    "Black Bloc hit an error running that command; it has been logged. Try again, and tell a "
    "Lead if it keeps happening."
)
THAT_COMMAND = "that command"

MESSAGE_LIMIT = 200
CUSTOM_ID_LIMIT = 100

NETWORK_ERRORS: tuple[type[BaseException], ...] = (
    discord.HTTPException,
    aiohttp.ClientError,
    asyncio.TimeoutError,
    OSError,
    ValueError,
)


def said(interaction: Any, key: str, fallback: str) -> str:
    """Every word the bot posts is a key; an unreachable store never breaks an error path."""
    try:
        found = interaction.client.store.get(interaction.guild.id, key)
    except Exception:
        return fallback
    return str(found) if found not in (None, "") else fallback


def retry_minutes(interaction: Any) -> int:
    try:
        wanted = int(interaction.client.store.get(interaction.guild.id, ERROR_RETRY_MINUTES_KEY))
    except Exception:
        return ERROR_RETRY_MINUTES
    return max(ERROR_RETRY_MIN_MINUTES, min(ERROR_RETRY_MAX_MINUTES, wanted))


def command_of(interaction: Any) -> str:
    name = getattr(getattr(interaction, "command", None), "qualified_name", "")
    return f"/{name}" if name else THAT_COMMAND


def interaction_of(interaction: Any) -> str:
    """What the member ran or pressed, by name — never anything they typed into it."""
    name = getattr(getattr(interaction, "command", None), "qualified_name", "")
    if name:
        return f"/{name}"
    data = getattr(interaction, "data", None)
    found = data.get("custom_id") if isinstance(data, dict) else None
    return str(found or "")[:CUSTOM_ID_LIMIT]


def step_of(error: BaseException) -> str:
    """The innermost frame inside the package — where it broke, not where it was caught."""
    found = ""
    trace = getattr(error, "__traceback__", None)
    while trace is not None:
        try:
            where = Path(trace.tb_frame.f_code.co_filename).resolve()
            if where.is_relative_to(PACKAGE):
                found = f"{where.relative_to(ROOT).as_posix()}:{trace.tb_lineno}"
        except (OSError, ValueError):
            pass
        trace = trace.tb_next
    return found


def message_of(error: BaseException) -> str:
    """⚠️ Never a member's words: an HTTP failure is reduced to Discord's own code and text."""
    if isinstance(error, discord.HTTPException):
        return f"{getattr(error, 'code', 0)} {getattr(error, 'text', '')}".strip()[:MESSAGE_LIMIT]
    return str(error)[:MESSAGE_LIMIT]


def surface_of(one: Any) -> str:
    if isinstance(one, discord.ui.Modal):
        return ERROR_MODAL
    if isinstance(one, discord.ui.View):
        return ERROR_PANEL
    if isinstance(one, discord.ui.Item):
        return ERROR_BUTTON
    return ERROR_COMMAND


def render_again_of(one: Any) -> Any:
    """The coroutine that puts a member back where they were: this surface's, or its parent's."""
    for found in (one, getattr(one, "previous", None), getattr(one, "view", None)):
        again = getattr(found, "render_again", None)
        if again is not None:
            return again
    return None


async def record(
    bot: Any,
    interaction: discord.Interaction,
    error: BaseException,
    where: str,
    *,
    surface: str = ERROR_COMMAND,
) -> None:
    """One action-log row per failure, so staff who are not the owner can read it on the site."""
    try:
        guild = getattr(interaction, "guild", None)
        if bot is None or getattr(guild, "id", None) is None:
            return
        await log_action(
            bot,
            guild,
            surface,
            actor=getattr(interaction, "user", None),
            details={
                "where": where,
                "error": type(error).__name__,
                "message": message_of(error),
                "step": step_of(error),
                "interaction": interaction_of(interaction),
            },
        )
    except Exception as exc:
        log.warning("command error: %s was not logged — %s: %s", surface, type(exc).__name__, exc)


async def answer(
    interaction: discord.Interaction, message: str = COMMAND_FAILED, view: Any = None
) -> None:
    extra: dict[str, Any] = {"view": view} if view is not None else {}
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True, **extra)
        else:
            await interaction.response.send_message(message, ephemeral=True, **extra)
    except Exception as exc:
        log.warning("command error: could not answer the caller — %s: %s", type(exc).__name__, exc)


class RetryButton(discord.ui.Button):
    def __init__(self, label: str) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.press(interaction)


class RetryView(discord.ui.View):
    """One button on a short-lived ephemeral message; the press re-renders what the member left."""

    def __init__(self, again: Any, origin: Any, *, label: str, expired: str, minutes: int) -> None:
        asked = int(minutes or ERROR_RETRY_MINUTES)
        wanted = max(ERROR_RETRY_MIN_MINUTES, min(ERROR_RETRY_MAX_MINUTES, asked))
        super().__init__(timeout=wanted * 60)
        self.again = again
        self.origin = origin
        self.expired = expired
        self.until = datetime.now(UTC) + timedelta(minutes=wanted)
        self.add_item(RetryButton(label))

    def gone(self) -> bool:
        return datetime.now(UTC) >= self.until

    async def press(self, interaction: discord.Interaction) -> None:
        if self.gone():
            await answer(interaction, self.expired)
            return
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
            await self.again(self.origin)
        except Exception as exc:
            log.warning("try again: could not put them back — %s: %s", type(exc).__name__, exc)
            await answer(interaction, self.expired)
            return
        self.stop()
        try:
            await interaction.delete_original_response()
        except Exception as exc:
            log.info("try again: the error message stayed on screen — %s", exc)


def retry_view(interaction: discord.Interaction, again: Any) -> RetryView:
    return RetryView(
        again,
        interaction,
        label=said(interaction, ERROR_RETRY_LABEL_KEY, ERROR_RETRY_LABEL),
        expired=said(interaction, ERROR_RETRY_EXPIRED_KEY, ERROR_RETRY_EXPIRED).replace(
            "{command}", command_of(interaction)
        ),
        minutes=retry_minutes(interaction),
    )


async def offer(interaction: discord.Interaction, again: Any = None) -> None:
    """The plain sentence when nothing can be re-rendered, the Try-again one when something can."""
    if again is None:
        await answer(interaction)
        return
    await answer(
        interaction,
        said(interaction, ERROR_SENTENCE_KEY, ERROR_SENTENCE),
        view=retry_view(interaction, again),
    )


async def report(
    interaction: discord.Interaction,
    error: Exception,
    where: str = "?",
    *,
    surface: str = ERROR_COMMAND,
    again: Any = None,
) -> None:
    """Log the traceback, write the row, answer the person — with Try again when there is one."""
    log.exception("%s failed", where, exc_info=error)
    await record(getattr(interaction, "client", None), interaction, error, where, surface=surface)
    await offer(interaction, again)


class AnswersErrors:
    """Mixin: a view, modal or item whose failure reaches the clicker as a sentence."""

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: Any = None
    ) -> None:
        await report(
            interaction,
            error,
            type(self).__name__,
            surface=surface_of(self),
            again=render_again_of(self),
        )


class SafeDynamicItem(AnswersErrors):
    """`DynamicItem` failures never reach `View.on_error`, so the callback catches its own."""

    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            await self.on_click(interaction)
        except Exception as exc:
            await self.on_error(interaction, exc)

    async def on_click(self, interaction: discord.Interaction) -> None:
        raise NotImplementedError


async def on_tree_error(interaction: discord.Interaction, error: Exception) -> None:
    if isinstance(error, app_commands.CheckFailure):
        return
    name = getattr(interaction.command, "qualified_name", "?")
    log.exception("command /%s failed", name, exc_info=error)
    await record(
        getattr(interaction, "client", None),
        interaction,
        error,
        f"/{name}",
        surface=ERROR_COMMAND,
    )
    await answer(interaction)


def install(bot: Any) -> None:
    """Answer every unhandled slash-command exception with a sentence instead of silence."""
    tree = getattr(bot, "tree", None)
    if tree is None:
        return
    tree.on_error = on_tree_error  # type: ignore[method-assign]
