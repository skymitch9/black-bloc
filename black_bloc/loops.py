from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


async def wait_ready(
    bot: Any, failed: Callable[[BaseException], Awaitable[Any]]
) -> bool:
    """discord.py runs `before_loop` outside the `error` handler's reach, so hand it over here."""
    try:
        await bot.wait_until_ready()
    except Exception as exc:
        await failed(exc)
        return False
    return True
