from __future__ import annotations

import asyncio
import sys

import discord
from discord.ext import commands

from .config import ConfigError

EXIT_CONFIG = 2
EXIT_LOGIN = 3
EXIT_RESTART = 4

LOGIN_FAILURE = (
    "black-bloc: Discord rejected DISCORD_TOKEN. Reset it in the Developer Portal "
    "(Bot -> Reset Token) and update .env."
)
PRIVILEGED_INTENTS = (
    "black-bloc: the Members / Message Content / Presence intents are not enabled "
    "for this application. Developer Portal -> Bot -> Privileged Gateway Intents -> "
    "turn them on, then start again (docs/access/setup.md section 2)."
)


def config_error_exit(exc: ConfigError) -> int:
    print(f"black-bloc: {exc}", file=sys.stderr)
    return EXIT_CONFIG


async def _start(bot: commands.Bot, token: str) -> None:
    async with bot:
        await bot.start(token)


def run(bot: commands.Bot, token: str) -> int:
    try:
        asyncio.run(_start(bot, token))
    except KeyboardInterrupt:
        pass
    except discord.LoginFailure:
        print(LOGIN_FAILURE, file=sys.stderr)
        return EXIT_LOGIN
    except discord.PrivilegedIntentsRequired:
        print(PRIVILEGED_INTENTS, file=sys.stderr)
        return EXIT_LOGIN
    return 0
