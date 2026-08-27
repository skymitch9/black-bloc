from __future__ import annotations

import logging

import discord
from discord.ext import commands

from .invite import invite_url

log = logging.getLogger(__name__)


async def sync_dev_guild(bot: commands.Bot, dev_guild_id: int | None) -> None:
    if not dev_guild_id:
        log.info("DEV_GUILD_ID not set; skipping command sync (see docs/info/gotchas.md)")
        return

    guild = discord.Object(id=dev_guild_id)
    bot.tree.copy_global_to(guild=guild)
    try:
        synced = await bot.tree.sync(guild=guild)
    except discord.Forbidden:
        log.error(
            "cannot sync commands to guild %s: the bot is not in that server "
            "(or was invited without the applications.commands scope). "
            "Invite it with: %s",
            guild.id,
            invite_url(bot),
        )
        return
    log.info("synced %d app commands to dev guild %s", len(synced), guild.id)
