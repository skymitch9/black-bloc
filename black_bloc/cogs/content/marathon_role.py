from __future__ import annotations

import logging
from typing import Any

import discord

from ... import button_block
from ... import marathon_role as helpers
from ...actionlog import log_action
from ...command_errors import SafeDynamicItem
from ...panels import answer
from ...pings import FORBIDDEN
from ...settings_store import BUTTON_BLOCK_DEFAULTS, GUILD_ONLY, MARATHON_BLOCK_LABEL

log = logging.getLogger(__name__)

LABEL_DEFAULT = str(BUTTON_BLOCK_DEFAULTS[MARATHON_BLOCK_LABEL])


async def toggle_marathon_role(interaction: discord.Interaction) -> None:
    """The block's one press: the Marathon role on if the member lacks it, off if they wear it."""
    bot = interaction.client
    guild = interaction.guild
    member = interaction.user
    if guild is None or not hasattr(member, "roles"):
        await answer(interaction, GUILD_ONLY)
        return
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(interaction.channel_id):
        await answer(interaction, guard.refusal_message())
        return
    role, why = helpers.usable_role(bot.store, guild)
    if role is None:
        if why != helpers.UNSET:
            await log_action(
                bot,
                guild,
                helpers.FAILED,
                actor=member,
                target=member,
                details={"role_id": helpers.role_id_of(bot.store, guild.id), "reason": why},
            )
        await answer(interaction, helpers.unset_said(bot.store, guild.id))
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    adding = not helpers.wears(member, role)
    try:
        if adding:
            await member.add_roles(role, reason=helpers.ROLE_REASON)
        else:
            await member.remove_roles(role, reason=helpers.ROLE_REASON)
    except discord.HTTPException as exc:
        log.warning("marathon role: could not change %s for %s: %s", role.id, member.id, exc)
        await log_action(
            bot,
            guild,
            helpers.FAILED,
            actor=member,
            target=member,
            details={
                "role_id": int(role.id),
                "action": "add" if adding else "remove",
                "reason": f"{type(exc).__name__}: {exc}",
            },
        )
        await answer(interaction, FORBIDDEN.format(role=role.name))
        return
    await log_action(
        bot,
        guild,
        helpers.JOINED if adding else helpers.LEFT,
        actor=member,
        target=member,
        details={"role_id": int(role.id)},
    )
    said = helpers.added_said if adding else helpers.removed_said
    await answer(interaction, said(bot.store, guild.id, role))


class MarathonRoleButton(
    SafeDynamicItem,
    discord.ui.DynamicItem[discord.ui.Button],
    template=button_block.template(helpers.BLOCK_HEAD),
):
    """The Marathon role block's button: persistent, guild-keyed, answered privately."""

    def __init__(self, guild_id: Any, label: str | None = None) -> None:
        self.guild_id = int(guild_id)
        super().__init__(
            discord.ui.Button(
                label=label or LABEL_DEFAULT,
                style=discord.ButtonStyle.primary,
                custom_id=button_block.custom_id(helpers.BLOCK_HEAD, guild_id),
                row=0,
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: Any):
        return cls(int(match["guild_id"]))

    async def on_click(self, interaction: discord.Interaction) -> None:
        await toggle_marathon_role(interaction)


def block_parts(bot: Any, guild: Any, row: Any) -> tuple[discord.Embed, Any, str] | None:
    if not helpers.block_drawn(bot.store, guild.id):
        return None
    look = helpers.block_look(bot.store, guild.id)
    return button_block.parts(look, MarathonRoleButton(guild.id, look.label))


__all__ = ["MarathonRoleButton", "block_parts", "toggle_marathon_role"]
