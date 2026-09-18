from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

RECENT_SECONDS = 60.0


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


class Reconciler:
    """One reconcile at a time per cog, so two at boot cannot both read "nothing is posted"."""

    def __init__(self, recent_seconds: float = RECENT_SECONDS) -> None:
        self._lock = asyncio.Lock()
        self._recent_seconds = float(recent_seconds)
        self._finished_at: float | None = None

    def ran_recently(self) -> bool:
        last = self._finished_at
        return last is not None and (time.monotonic() - last) < self._recent_seconds

    async def run(
        self,
        work: Callable[[], Awaitable[Any]],
        *,
        skip_if_recent: bool = False,
        stamp: bool = True,
    ) -> bool:
        """`work` reads its stored state INSIDE the lock, so the second caller sees what the
        first wrote. True when it ran, False when the window said it had just run."""
        if skip_if_recent and self.ran_recently():
            return False
        async with self._lock:
            if skip_if_recent and self.ran_recently():
                return False
            await work()
            if stamp:
                self._finished_at = time.monotonic()
            return True


__all__ = ["RECENT_SECONDS", "Reconciler", "wait_ready"]
