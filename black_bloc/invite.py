from __future__ import annotations

import discord

INVITE_PERMISSIONS = discord.Permissions(
    view_channel=True,
    send_messages=True,
    send_messages_in_threads=True,
    embed_links=True,
    attach_files=True,
    read_message_history=True,
    mention_everyone=True,
    manage_messages=True,
    kick_members=True,
    ban_members=True,
    moderate_members=True,
    manage_roles=True,
    manage_channels=True,
    move_members=True,
    manage_events=True,
)


def invite_url(bot: discord.Client) -> str:
    assert bot.application_id is not None, "invite_url() needs a logged-in client"
    return discord.utils.oauth_url(
        bot.application_id,
        permissions=INVITE_PERMISSIONS,
        scopes=("bot", "applications.commands"),
    )
