"""Entrypoint / orchestrator. Wires settings, logging and the bot together.

Deliberately thin: no feature logic here, ever. See docs/info/architecture.md.
"""

from __future__ import annotations

import asyncio
import sys

import discord

from .bot import BlackBlocBot
from .config import ConfigError, load_settings
from .logging_setup import configure_logging


async def _run(bot: BlackBlocBot, token: str) -> None:
    async with bot:
        await bot.start(token)


def main() -> int:
    try:
        settings = load_settings()
        configure_logging(settings.log_level)
        settings.validate_test_mode()
        token = settings.require_token()
    except ConfigError as exc:
        print(f"black-bloc: {exc}", file=sys.stderr)
        return 2

    bot = BlackBlocBot(settings)
    try:
        asyncio.run(_run(bot, token))
    except KeyboardInterrupt:
        pass
    except discord.LoginFailure:
        print("black-bloc: Discord rejected DISCORD_TOKEN. Reset it in the Developer Portal "
              "(Bot -> Reset Token) and update .env.", file=sys.stderr)
        return 3
    except discord.PrivilegedIntentsRequired:
        print("black-bloc: the Members / Message Content / Presence intents are not enabled "
              "for this application. Developer Portal -> Bot -> Privileged Gateway Intents -> "
              "turn them on, then start again (docs/access/setup.md section 2).", file=sys.stderr)
        return 3
    return 0
