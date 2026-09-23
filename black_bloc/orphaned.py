from __future__ import annotations

import logging
from typing import Any

import discord

from .actionlog import log_action
from .command_errors import said
from .logkinds import HEADS, PANEL_EXPIRED_CLICK
from .settings_store import PANEL_EXPIRED_TEXT, PANEL_EXPIRED_TEXT_KEY

log = logging.getLogger(__name__)

ORPHANED = "black_bloc.orphaned"
THE_COMMAND = "the command"
PREFIX_LIMIT = 40
SURFACES = {
    discord.InteractionType.component: "component",
    discord.InteractionType.modal_submit: "modal",
}


def view_store(bot: Any) -> Any:
    """discord.py 2.7.1 keeps no public way to ask whether a custom_id has a live owner."""
    return bot._connection._view_store


def custom_id_of(interaction: Any) -> str:
    data = getattr(interaction, "data", None)
    return str(data.get("custom_id") or "") if isinstance(data, dict) else ""


def live_item(store: Any, interaction: Any, custom_id: str) -> bool:
    data = interaction.data
    key = (int(data.get("component_type") or 0), custom_id)
    message = getattr(interaction, "message", None)
    item = None
    if message is not None:
        item = store._views.get(message.id, {}).get(key)
    if item is None:
        item = store._views.get(None, {}).get(key)
    view = getattr(item, "view", None)
    return view is not None and not view.is_finished()


def is_owned(store: Any, interaction: Any) -> bool:
    """The same three lookups `ViewStore.dispatch_view` / `dispatch_modal` make, in their order."""
    custom_id = custom_id_of(interaction)
    if interaction.type is discord.InteractionType.modal_submit:
        return custom_id in store._modals
    if any(pattern.fullmatch(custom_id) for pattern in store._dynamic_items):
        return True
    return live_item(store, interaction, custom_id)


def mark(bot: Any, interaction: Any) -> None:
    """Runs inside `dispatch`, before any handler task has started, so nothing can race it."""
    if getattr(interaction, "type", None) not in SURFACES:
        return
    try:
        if not is_owned(view_store(bot), interaction):
            interaction.extras[ORPHANED] = True
    except Exception as exc:
        log.debug("orphaned: could not read the view store — %s: %s", type(exc).__name__, exc)


def command_named(interaction: Any) -> str:
    """The slash command that opened the message, from Discord's own record of it, else nothing."""
    found = getattr(getattr(interaction, "message", None), "_interaction", None)
    name = str(getattr(found, "name", "") or "").strip()
    return f"/{name}" if name else ""


def feature_of(command: str) -> str:
    head = command.lstrip("/").split(" ", 1)[0]
    return HEADS.get(head, "")


def sentence(interaction: Any, command: str) -> str:
    text = said(interaction, PANEL_EXPIRED_TEXT_KEY, PANEL_EXPIRED_TEXT)
    return text.replace("{command}", command or THE_COMMAND)


async def record(interaction: Any, command: str) -> None:
    guild = getattr(interaction, "guild", None)
    if getattr(guild, "id", None) is None:
        return
    try:
        await log_action(
            interaction.client,
            guild,
            PANEL_EXPIRED_CLICK,
            actor=getattr(interaction, "user", None),
            details={
                "feature": feature_of(command),
                "command": command,
                "surface": SURFACES.get(interaction.type, ""),
                "custom_id": custom_id_of(interaction).split(":", 1)[0][:PREFIX_LIMIT],
            },
        )
    except Exception as exc:
        log.warning("orphaned: the click was not logged — %s: %s", type(exc).__name__, exc)


async def on_interaction(interaction: discord.Interaction) -> None:
    if not interaction.extras.get(ORPHANED) or interaction.response.is_done():
        return
    command = command_named(interaction)
    try:
        await interaction.response.send_message(
            sentence(interaction, command),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except discord.HTTPException as exc:
        log.info("orphaned: could not answer a click on a gone panel — %s", exc)
    await record(interaction, command)


def install(bot: Any) -> None:
    bot.add_listener(on_interaction, "on_interaction")
