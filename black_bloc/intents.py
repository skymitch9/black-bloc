from __future__ import annotations

import discord


def build_intents() -> discord.Intents:
    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True
    intents.presences = True
    return intents
