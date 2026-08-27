from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import discord

from .actionlog import log_action

log = logging.getLogger(__name__)

HIDDEN_WHEN_OFF: dict[str, tuple[str, ...]] = {"rolemenu_mode": ("rolemenu",)}
NEVER_HIDDEN: tuple[str, ...] = ("settings",)
OFF = "off"
DEBOUNCE_SECONDS = 5.0
MIN_SYNC_SECONDS = 60.0
LOG_KIND = "commands.visibility"


async def _wait(seconds: float) -> None:
    await asyncio.sleep(seconds)


def _now() -> float:
    return time.monotonic()


def dev_guild(bot: Any) -> discord.Object | None:
    guild_id = getattr(getattr(bot, "settings", None), "dev_guild_id", None)
    return discord.Object(id=guild_id) if guild_id else None


def hidden_names(bot: Any, guild_id: int | None) -> set[str]:
    """Top-level command names that a feature's mode is hiding right now."""
    if guild_id is None:
        return set()
    found: set[str] = set()
    for key, names in HIDDEN_WHEN_OFF.items():
        if bot.store.get(guild_id, key) == OFF:
            found.update(name for name in names if name not in NEVER_HIDDEN)
    return found


class VisibilitySync:
    def __init__(self, bot: Any) -> None:
        self.bot = bot
        self.removed: dict[str, Any] = {}
        self.task: asyncio.Task | None = None
        self.last_sync: float | None = None
        self.actor: Any = None
        self.installed = False
        self.jobs: list[Any] = []

    def also(self, job: Any) -> None:
        """Run `await job(actor)` in the same debounced run, before the tree sync."""
        if job not in self.jobs:
            self.jobs.append(job)

    def schedule(self, *, actor: Any = None) -> None:
        if actor is not None:
            self.actor = actor
        self._schedule()

    def apply(self, *, actor: Any = None) -> bool:
        """Match the dev guild's tree to the stored modes; True when it had to change."""
        guild = dev_guild(self.bot)
        if guild is None:
            return False
        wanted = hidden_names(self.bot, guild.id)
        changed = False
        for names in HIDDEN_WHEN_OFF.values():
            for name in names:
                if name in NEVER_HIDDEN:
                    continue
                step = self._hide if name in wanted else self._show
                changed = step(guild, name) or changed
        if not changed:
            return False
        if actor is not None:
            self.actor = actor
        self._schedule()
        return True

    def _hide(self, guild: Any, name: str) -> bool:
        command = self.bot.tree.remove_command(name, guild=guild)
        if command is None:
            return False
        self.removed[name] = command
        log.info("command visibility: /%s hidden in guild %s", name, guild.id)
        return True

    def _show(self, guild: Any, name: str) -> bool:
        if self.bot.tree.get_command(name, guild=guild) is not None:
            return False
        command = self.removed.pop(name, None)
        if command is None:
            command = self.bot.tree.get_command(name)
        if command is None:
            log.warning("command visibility: /%s is not in the tree, so it cannot come back", name)
            return False
        self.bot.tree.add_command(command, guild=guild, override=True)
        log.info("command visibility: /%s shown again in guild %s", name, guild.id)
        return True

    def _schedule(self) -> None:
        if self.task is not None and not self.task.done():
            return
        try:
            self.task = asyncio.get_running_loop().create_task(
                self._run(), name="command-visibility"
            )
        except RuntimeError:
            log.warning("command visibility: no running loop, so the tree was not synced")

    async def _run(self) -> None:
        try:
            await _wait(DEBOUNCE_SECONDS)
            await self._jobs()
            gap = self._cooldown()
            if gap > 0:
                await _wait(gap)
            await self.sync_now()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.error("command visibility: sync failed — %s: %s", type(exc).__name__, exc)

    async def _jobs(self) -> None:
        for job in self.jobs:
            try:
                await job(self.actor)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.error("mode flip: %r failed — %s: %s", job, type(exc).__name__, exc)

    def _cooldown(self) -> float:
        if self.last_sync is None:
            return 0.0
        return max(0.0, MIN_SYNC_SECONDS - (_now() - self.last_sync))

    async def sync_now(self) -> None:
        guild = dev_guild(self.bot)
        if guild is None:
            return
        try:
            synced = await self.bot.tree.sync(guild=guild)
        except discord.HTTPException as exc:
            log.error("command visibility: guild %s refused the sync: %s", guild.id, exc)
            return
        self.last_sync = _now()
        actor, self.actor = self.actor, None
        log.info(
            "command visibility: %d command(s) in guild %s; hidden: %s",
            len(synced),
            guild.id,
            ", ".join(sorted(self.removed)) or "none",
        )
        await self._record(guild, len(synced), actor)

    async def _record(self, guild: Any, count: int, actor: Any) -> None:
        db = getattr(self.bot, "db", None)
        if db is None or not db.is_connected:
            return
        try:
            await log_action(
                self.bot,
                self.bot.get_guild(guild.id) or guild,
                LOG_KIND,
                actor=actor,
                details={"commands": count, "hidden": sorted(self.removed)},
            )
        except Exception as exc:
            log.warning("command visibility: not logged — %s: %s", type(exc).__name__, exc)


def controller(bot: Any) -> VisibilitySync:
    found = getattr(bot, "command_visibility", None)
    if found is None:
        found = VisibilitySync(bot)
        bot.command_visibility = found
    return found


def apply_visibility(bot: Any, *, actor: Any = None) -> bool:
    return controller(bot).apply(actor=actor)


def _changed(bot: Any) -> Any:
    def changed(guild_id: int, key: str, value: Any, by: int | None) -> None:
        guild = dev_guild(bot)
        if guild is None or guild_id != guild.id:
            return
        apply_visibility(bot, actor=by)

    return changed


def install(bot: Any) -> VisibilitySync:
    """Register the one trigger path — every change of a registry key — and apply now."""
    found = controller(bot)
    if not found.installed:
        callback = _changed(bot)
        for key in HIDDEN_WHEN_OFF:
            bot.store.on_change(key, callback)
        found.installed = True
    found.apply()
    return found
