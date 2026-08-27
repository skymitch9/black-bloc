from __future__ import annotations

import logging
from typing import Any

import discord
from discord import app_commands

log = logging.getLogger(__name__)

COMMAND_FAILED = (
    "Black Bloc hit an error running that command; it has been logged. Try again, and tell a "
    "Lead if it keeps happening."
)


async def answer(interaction: discord.Interaction, message: str = COMMAND_FAILED) -> None:
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except Exception as exc:
        log.warning("command error: could not answer the caller — %s: %s", type(exc).__name__, exc)


async def on_tree_error(interaction: discord.Interaction, error: Exception) -> None:
    if isinstance(error, app_commands.CheckFailure):
        return
    name = getattr(interaction.command, "qualified_name", "?")
    log.exception("command /%s failed", name, exc_info=error)
    await answer(interaction)


def install(bot: Any) -> None:
    """Answer every unhandled slash-command exception with a sentence instead of silence."""
    tree = getattr(bot, "tree", None)
    if tree is None:
        return
    tree.on_error = on_tree_error  # type: ignore[method-assign]
