"""Sticky messages: where a copy goes, when it moves, and the moves staff make on one."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import discord

from . import shadow as shadow_home
from . import sticky as rules
from .actionlog import log_action
from .logkinds import VIA_DISCORD, kind_via
from .panels import Outcome, refusal
from .settings_store import STICKY_MODE, STICKY_MODES

log = logging.getLogger(__name__)

DESK_ATTR = "sticky_desk"
NEEDED = (("view_channel", "View Channel"), ("send_messages", "Send Messages"))

POSTED = "posted"
REHEARSED = "rehearsed"
TEST_MODE = "test_mode"
NOT_RUNNING = "not_running"
TOO_SOON = "too_soon"
FAILED = "failed"


def utc_now() -> datetime:
    return datetime.now(UTC)


def refusal_words(exc: BaseException) -> str:
    if isinstance(exc, discord.HTTPException):
        return rules.TROUBLE_REFUSED.format(
            status=exc.status, text=exc.text or type(exc).__name__
        )
    return rules.TROUBLE_UNEXPECTED.format(reason=f"{type(exc).__name__}: {exc}")


def missing_permissions(guild: Any, channel: Any) -> list[str]:
    """Empty when nothing is known to be missing; the send itself is the backstop."""
    me = getattr(guild, "me", None)
    asked = getattr(channel, "permissions_for", None)
    if me is None or not callable(asked):
        return []
    perms = asked(me)
    return [words for name, words in NEEDED if getattr(perms, name, True) is False]


def partial(channel: Any, message_id: int) -> Any:
    return channel.get_partial_message(int(message_id))


class Desk:
    """One per bot: the counts, the timers and the one-at-a-time lock for every channel."""

    def __init__(
        self,
        bot: Any,
        *,
        now: Callable[[], datetime] = utc_now,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
    ) -> None:
        self.bot = bot
        self.now = now
        self.sleep = sleep
        self.watched: set[int] = set()
        self.heard: dict[int, int] = {}
        self.waiting: dict[int, asyncio.Task] = {}
        self.locks: dict[int, asyncio.Lock] = {}
        self.said: set[tuple[int, str]] = set()

    def lock(self, channel_id: int) -> asyncio.Lock:
        return self.locks.setdefault(int(channel_id), asyncio.Lock())

    @property
    def db(self) -> Any:
        return self.bot.db

    @property
    def store(self) -> Any:
        return self.bot.store

    async def load(self) -> None:
        self.watched = {channel_id for _, channel_id in await rules.running_channels(self.db)}

    def close(self) -> None:
        for task in self.waiting.values():
            task.cancel()
        self.waiting.clear()

    def forget(self, channel_id: int) -> None:
        self.watched.discard(channel_id)
        self.heard.pop(channel_id, None)
        task = self.waiting.pop(channel_id, None)
        if task is not None and task is not asyncio.current_task():
            task.cancel()

    async def on_message(self, message: Any) -> None:
        channel_id = getattr(getattr(message, "channel", None), "id", None)
        if channel_id not in self.watched or not rules.counts(message):
            return
        guild = message.guild
        if rules.mode_of(self.store, guild.id) == "off" or not self.db.is_connected:
            return
        after, gap, _ = rules.numbers(self.store, guild.id)
        self.heard[channel_id] = self.heard.get(channel_id, 0) + 1
        if self.heard[channel_id] < after or channel_id in self.waiting:
            return
        row = await rules.get_row(self.db, guild.id, channel_id)
        if not rules.is_running(row):
            self.forget(channel_id)
            return
        wait = rules.seconds_left(row, self.now(), gap)
        if wait > 0:
            self.waiting[channel_id] = asyncio.create_task(
                self._later(guild, channel_id, wait), name=f"sticky-{channel_id}"
            )
            return
        await self.place(guild, channel_id)

    async def _later(self, guild: Any, channel_id: int, wait: float) -> None:
        try:
            await self.sleep(wait)
            self.waiting.pop(channel_id, None)
            await self.place(guild, channel_id)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.warning("sticky: a waiting copy was not posted — %s: %s", type(exc).__name__, exc)
        finally:
            if self.waiting.get(channel_id) is asyncio.current_task():
                self.waiting.pop(channel_id, None)

    async def place(self, guild: Any, channel_id: int, *, first: bool = False) -> str:
        async with self.lock(channel_id):
            return await self._place(guild, channel_id, first=first)

    def _target(self, guild: Any, row: Any, mode: str) -> tuple[Any, int | None, str | None]:
        """The channel a copy goes in, the rehearsal home when it is one, or why neither."""
        channel_id = int(row["channel_id"])
        real = shadow_home.channel_of(self.bot, guild, channel_id)
        if real is None:
            return (None, None, rules.TROUBLE_CHANNEL_GONE)
        if mode != "shadow":
            return (real, None, None)
        home = shadow_home.channel_id(self.bot, guild, feature=rules.FEATURE)
        if not home:
            return (None, None, rules.TROUBLE_NO_HOME)
        found = shadow_home.channel_of(self.bot, guild, home)
        if found is None:
            return (None, home, rules.TROUBLE_HOME_GONE.format(home=home))
        return (found, int(home), None)

    async def _place(self, guild: Any, channel_id: int, *, first: bool = False) -> str:
        """Called with the channel's lock held, so the row read here is the one acted on."""
        row = await rules.get_row(self.db, guild.id, channel_id)
        mode = rules.mode_of(self.store, guild.id)
        if not rules.is_running(row) or mode == "off":
            return NOT_RUNNING
        _, gap, silent = rules.numbers(self.store, guild.id)
        if not first and rules.seconds_left(row, self.now(), gap) > 0:
            return TOO_SOON
        target, home, trouble = self._target(guild, row, mode)
        if trouble is None:
            missing = missing_permissions(guild, target)
            if missing:
                trouble = rules.TROUBLE_PERMISSION.format(
                    missing=" and ".join(missing), channel_id=target.id
                )
        if trouble is not None:
            return await self._stopped(guild, row, trouble)
        guard = getattr(self.bot, "guard", None)
        if guard is not None and not guard.allows_channel(target.id):
            await self._would(guild, row, target, home, reason=TEST_MODE, once=True)
            self.heard[channel_id] = 0
            return TEST_MODE
        undone = await self._take_down(guild, row)
        if undone is not None:
            return await self._stopped(
                guild, row, rules.TROUBLE_OLD_COPY.format(reason=undone)
            )
        note = shadow_home.note_line(self.bot, guild, f"<#{channel_id}>") if home else ""
        body = f"{note}\n{row['text']}" if note else row["text"]
        try:
            sent = await target.send(
                body, allowed_mentions=discord.AllowedMentions.none(), silent=silent
            )
        except Exception as exc:
            return await self._stopped(guild, row, refusal_words(exc))
        await rules.write_copy(
            self.db, guild.id, channel_id, sent.id, target.id, moved=not first, at=self.now()
        )
        self.heard[channel_id] = 0
        self.watched.add(channel_id)
        if first:
            await self._posted(guild, row, target, home, sent.id)
        return REHEARSED if home else POSTED

    async def _take_down(self, guild: Any, row: Any) -> str | None:
        """None when no copy is left anywhere; otherwise why the old one is still up."""
        if not row["message_id"] or not row["posted_channel_id"]:
            return None
        channel = shadow_home.channel_of(self.bot, guild, row["posted_channel_id"])
        if channel is not None:
            try:
                await partial(channel, row["message_id"]).delete()
            except discord.NotFound:
                pass
            except Exception as exc:
                return refusal_words(exc)
        await rules.write_copy(self.db, guild.id, row["channel_id"], None, None)
        return None

    async def _stopped(self, guild: Any, row: Any, trouble: str) -> str:
        """Said once: the row carries the reason, and a stopped row is never tried again."""
        channel_id = int(row["channel_id"])
        await rules.write_trouble(self.db, guild.id, channel_id, trouble)
        self.forget(channel_id)
        log.warning("sticky: channel %s stopped — %s", channel_id, trouble)
        await self._safely(
            log_action(
                self.bot,
                guild,
                "sticky.post_failed",
                details={"channel_id": channel_id, "reason": trouble},
            )
        )
        return FAILED

    async def _posted(
        self, guild: Any, row: Any, target: Any, home: int | None, message_id: int
    ) -> None:
        if home:
            await self._would(guild, row, target, home, message_id=message_id)
            return
        await self._safely(
            log_action(
                self.bot,
                guild,
                "sticky.posted",
                details={"channel_id": int(row["channel_id"]), "message_id": message_id},
            )
        )

    async def _would(
        self,
        guild: Any,
        row: Any,
        target: Any,
        home: int | None,
        *,
        reason: str | None = None,
        message_id: int | None = None,
        once: bool = False,
    ) -> None:
        channel_id = int(row["channel_id"])
        if once:
            if (channel_id, reason or "") in self.said:
                return
            self.said.add((channel_id, reason or ""))
        details: dict[str, Any] = {"channel_id": channel_id}
        if reason:
            details["reason"] = reason
        if home and message_id:
            details |= {"rehearsed": True, "shadow_home": home, "message_id": message_id}
        await self._safely(
            log_action(self.bot, guild, "sticky.would_post", details=details)
        )

    async def _safely(self, writing: Any) -> None:
        try:
            await writing
        except Exception as exc:
            log.warning("sticky: log row not written — %s: %s", type(exc).__name__, exc)

    def _placed_words(self, guild: Any, channel_id: int, done: str, row: Any) -> str:
        if done == POSTED:
            return rules.SAVED_LIVE.format(channel_id=channel_id)
        if done == REHEARSED:
            return rules.SAVED_REHEARSED.format(
                channel_id=channel_id, home=row["posted_channel_id"]
            )
        if done == TEST_MODE:
            return rules.SAVED_TEST_MODE
        if done == FAILED:
            return rules.SAVED_BUT.format(trouble=row["trouble"])
        if row["paused"]:
            return rules.SAVED_PAUSED
        return rules.SAVED_OFF

    async def _answer(self, guild: Any, channel_id: int, done: str, code: str) -> Outcome:
        row = await rules.get_row(self.db, guild.id, channel_id)
        return Outcome(True, self._placed_words(guild, channel_id, done, row), code, 200, row)

    async def save(
        self, guild: Any, channel_id: int, text: Any, actor: Any, *, via: str = VIA_DISCORD
    ) -> Outcome:
        words = rules.clean(text)
        refused = rules.text_refusal(words)
        if refused is not None:
            return refusal(refused, "bad_text", 400)
        channel = shadow_home.channel_of(self.bot, guild, channel_id)
        async with self.lock(channel_id):
            existing = await rules.get_row(self.db, guild.id, channel_id)
            if existing is None:
                if channel is None:
                    return refusal(rules.NO_SUCH_CHANNEL, "no_such_channel", 404)
                if not rules.postable(channel):
                    return refusal(
                        rules.NOT_POSTABLE.format(channel_id=channel_id), "not_postable", 400
                    )
            made = await rules.write_words(
                self.db, guild.id, channel_id, words, getattr(actor, "id", actor)
            )
            await log_action(
                self.bot,
                guild,
                kind_via("sticky.set" if made else "sticky.edited", via),
                actor=actor,
                details={
                    "channel_id": int(channel_id),
                    "text": words[: rules.LOGGED_CHARS],
                    "via": via,
                },
            )
            done = await self._place(guild, channel_id, first=True)
            return await self._answer(guild, channel_id, done, "set" if made else "edited")

    async def pause(
        self, guild: Any, channel_id: int, actor: Any, *, via: str = VIA_DISCORD
    ) -> Outcome:
        async with self.lock(channel_id):
            row = await rules.get_row(self.db, guild.id, channel_id)
            if row is None:
                return refusal(rules.NO_STICKY, "no_sticky", 404)
            if row["paused"]:
                return refusal(rules.ALREADY_PAUSED, "already_paused", 409)
            await rules.write_paused(
                self.db, guild.id, channel_id, True, getattr(actor, "id", actor)
            )
            self.forget(channel_id)
            left = await self._take_down(guild, row)
            await log_action(
                self.bot,
                guild,
                kind_via("sticky.paused", via),
                actor=actor,
                details={"channel_id": int(channel_id), "via": via}
                | ({"copy_left": left} if left else {}),
            )
            row = await rules.get_row(self.db, guild.id, channel_id)
            return Outcome(
                True, rules.PAUSED_NOW.format(channel_id=channel_id), "paused", 200, row
            )

    async def resume(
        self, guild: Any, channel_id: int, actor: Any, *, via: str = VIA_DISCORD
    ) -> Outcome:
        async with self.lock(channel_id):
            row = await rules.get_row(self.db, guild.id, channel_id)
            if row is None:
                return refusal(rules.NO_STICKY, "no_sticky", 404)
            if rules.is_running(row):
                return refusal(rules.NOT_PAUSED, "not_paused", 409)
            await rules.write_paused(
                self.db, guild.id, channel_id, False, getattr(actor, "id", actor)
            )
            await log_action(
                self.bot,
                guild,
                kind_via("sticky.resumed", via),
                actor=actor,
                details={"channel_id": int(channel_id), "via": via},
            )
            done = await self._place(guild, channel_id, first=True)
            return await self._answer(guild, channel_id, done, "resumed")

    async def remove(
        self, guild: Any, channel_id: int, actor: Any, *, via: str = VIA_DISCORD
    ) -> Outcome:
        async with self.lock(channel_id):
            row = await rules.get_row(self.db, guild.id, channel_id)
            if row is None:
                return refusal(rules.NO_STICKY, "no_sticky", 404)
            self.forget(channel_id)
            left = await self._take_down(guild, row)
            await rules.delete_row(self.db, guild.id, channel_id)
            await log_action(
                self.bot,
                guild,
                kind_via("sticky.removed", via),
                actor=actor,
                details={
                    "channel_id": int(channel_id),
                    "text": str(row["text"])[: rules.LOGGED_CHARS],
                    "via": via,
                }
                | ({"copy_left": left} if left else {}),
            )
            return Outcome(
                True, rules.REMOVED_NOW.format(channel_id=channel_id), "removed", 200
            )

    async def channel_deleted(self, guild: Any, channel_id: int) -> bool:
        """Discord already took the copy with the channel, so only the row is left to go."""
        async with self.lock(channel_id):
            row = await rules.get_row(self.db, guild.id, channel_id)
            if row is None:
                return False
            self.forget(channel_id)
            await rules.delete_row(self.db, guild.id, channel_id)
            await self._safely(
                log_action(
                    self.bot,
                    guild,
                    "sticky.channel_gone",
                    details={
                        "channel_id": int(channel_id),
                        "text": str(row["text"])[: rules.LOGGED_CHARS],
                    },
                )
            )
            return True

    async def set_mode(
        self, guild: Any, value: str, actor: Any, *, via: str = VIA_DISCORD
    ) -> Outcome:
        if value not in STICKY_MODES:
            return refusal(
                f"Sticky messages take one of {', '.join(STICKY_MODES)}, so nothing was changed.",
                "bad_mode",
                400,
            )
        await self.store.set(guild.id, STICKY_MODE, value, by=getattr(actor, "id", actor))
        await log_action(
            self.bot,
            guild,
            kind_via("sticky.mode", via),
            actor=actor,
            details={"mode": value, "via": via},
        )
        return Outcome(True, rules.MODE_SET.format(mode=value), "set", 200, value)

    async def settle(self, guild: Any) -> None:
        """Every running sticky is put where the mode says it belongs, and nowhere else."""
        if getattr(guild, "unavailable", False) or not self.db.is_connected:
            return
        mode = rules.mode_of(self.store, guild.id)
        for found in await rules.rows_for_guild(self.db, guild.id):
            channel_id = int(found["channel_id"])
            async with self.lock(channel_id):
                row = await rules.get_row(self.db, guild.id, channel_id)
                if not rules.is_running(row):
                    continue
                if mode == "off":
                    await self._take_down(guild, row)
                    continue
                self.watched.add(channel_id)
                if self._in_place(guild, row, mode):
                    continue
                await self._place(guild, channel_id, first=True)

    def _in_place(self, guild: Any, row: Any, mode: str) -> bool:
        if not row["message_id"]:
            return False
        if mode == "shadow":
            wanted = shadow_home.channel_id(self.bot, guild, feature=rules.FEATURE)
        else:
            wanted = row["channel_id"]
        return bool(wanted) and int(row["posted_channel_id"] or 0) == int(wanted)


def desk_of(bot: Any) -> Desk:
    found = getattr(bot, DESK_ATTR, None)
    if found is None:
        found = Desk(bot)
        setattr(bot, DESK_ATTR, found)
    return found


__all__ = [
    "DESK_ATTR",
    "FAILED",
    "NOT_RUNNING",
    "POSTED",
    "REHEARSED",
    "TEST_MODE",
    "TOO_SOON",
    "Desk",
    "desk_of",
    "missing_permissions",
    "refusal_words",
]
