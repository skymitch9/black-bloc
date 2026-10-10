"""Sticky messages: where a copy goes, when it moves, and the moves staff make on one."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import aiohttp
import discord

from . import posts
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
UNREACHABLE = "unreachable"
OWN_HOME = "own_home"
PIN_REASON = "Black Bloc keeps this sticky message pinned"
PIN_FAILED = "sticky.pin_failed"
PASSING_STATUS = 429
PASSING = (TimeoutError, OSError, aiohttp.ClientError)


def utc_now() -> datetime:
    return datetime.now(UTC)


def passing(exc: BaseException) -> bool:
    """True for an outage that ends by itself; a refusal Discord means is never one."""
    if isinstance(exc, discord.HTTPException):
        return exc.status >= 500 or exc.status == PASSING_STATUS
    return isinstance(exc, PASSING)


def why(exc: BaseException) -> str:
    if isinstance(exc, discord.HTTPException):
        return rules.REFUSED_WHY.format(status=exc.status, text=exc.text or type(exc).__name__)
    said = str(exc).strip()
    return f"{type(exc).__name__}: {said}" if said else type(exc).__name__


def outage_why(exc: BaseException) -> str:
    if isinstance(exc, discord.HTTPException):
        return rules.UNREACHABLE_ANSWERED.format(status=exc.status)
    return type(exc).__name__


def left_words(exc: BaseException) -> str:
    return rules.UNREACHABLE_WHY.format(why=outage_why(exc)) if passing(exc) else why(exc)


def refusal_words(exc: BaseException) -> str:
    if isinstance(exc, discord.HTTPException):
        return rules.TROUBLE_REFUSED.format(
            status=exc.status, text=exc.text or type(exc).__name__
        )
    return rules.TROUBLE_UNEXPECTED.format(reason=why(exc))


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


async def post_message(
    bot: Any, guild: Any, post: Any, note: str = ""
) -> tuple[dict[str, Any], dict[str, Any]]:
    """The post as it is now and every block under it, fresh; the note rides above as content."""
    from .post_blocks import kinds_on, load_kinds, parts_of

    kinds = await kinds_on(bot.db, int(post["id"]))
    await load_kinds(bot, guild, kinds)
    has_words = bool(str(posts.row_value(post, "body", "") or "").strip())
    base = posts.render_message(post) if has_words else {"content": None, "embed": None}
    drawn = parts_of(bot, guild, post, kinds)
    made = posts.with_blocks(base, list(drawn.values()))
    words = made["content"] or ""
    content = rules.fit(note, words) if words else (note or None)
    payload = {"content": content, "embeds": made["embeds"], "view": made["view"]}
    return payload, {kind: parts[2] for kind, parts in drawn.items()}


def is_empty(payload: dict[str, Any]) -> bool:
    return not payload["embeds"] and not str(payload["content"] or "").strip()


async def owner_rule(bot: Any, guild: Any, row: Any) -> tuple[str, str]:
    """The one rule: sticky off stops everything; a post a feature owns follows that feature."""
    from .post_blocks import kinds_on, owner_of

    mode = rules.mode_of(bot.store, guild.id)
    if mode == "off" or row is None or not rules.is_post(row):
        return (mode, rules.FEATURE)
    owner = owner_of(await kinds_on(bot.db, int(row["post_id"])))
    if owner is None:
        return (mode, rules.FEATURE)
    key, feature = owner
    owned = str(bot.store.get(guild.id, key) or "off")
    return (owned if owned in STICKY_MODES else "off", feature)


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
        self.deciding: set[int] = set()
        self.outage: dict[int, str] = {}
        self.tried: dict[int, datetime] = {}
        self.last: dict[int, datetime] = {}
        self.reached: dict[int, datetime] = {}

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
        self.outage.pop(channel_id, None)
        self.tried.pop(channel_id, None)
        self.last.pop(channel_id, None)
        self.reached.pop(channel_id, None)
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
        now = self.now()
        self.heard[channel_id] = self.heard.get(channel_id, 0) + 1
        self.last[channel_id] = now
        needed = 1 if channel_id in self.outage else after
        if self.heard[channel_id] < needed:
            return
        self.reached.setdefault(channel_id, now)
        if channel_id in self.waiting or channel_id in self.deciding:
            return
        self.deciding.add(channel_id)
        try:
            row = await rules.get_row(self.db, guild.id, channel_id)
            if not rules.is_running(row):
                self.forget(channel_id)
                return
            wait = rules.due_in(self._wait(row, gap), self._quiet(guild, channel_id))
            if wait > 0:
                self.waiting[channel_id] = asyncio.create_task(
                    self._later(guild, channel_id, wait), name=f"sticky-{channel_id}"
                )
                return
        finally:
            self.deciding.discard(channel_id)
        await self.place(guild, channel_id)

    def _wait(self, row: Any, gap: int) -> float:
        """Seconds until a copy may move: the gap since the last one, or since a failed try."""
        left = rules.seconds_left(row, self.now(), gap)
        tried = self.tried.get(int(row["channel_id"]))
        if tried is not None:
            left = max(left, float(gap) - (self.now() - tried).total_seconds())
        return max(0.0, left)

    def _quiet(self, guild: Any, channel_id: int) -> float:
        """Talk while waiting pushes the move back, up to the ceiling; an outage owes no quiet."""
        if channel_id in self.outage:
            return 0.0
        quiet, ceiling = rules.numbers_waiting(self.store, guild.id)
        return rules.quiet_left(
            self.now(),
            self.last.get(channel_id),
            self.reached.get(channel_id),
            quiet,
            ceiling,
        )

    async def _later(self, guild: Any, channel_id: int, wait: float) -> None:
        """One timer per channel: it sleeps again while people are still talking."""
        try:
            await self.sleep(wait)
            while (left := self._quiet(guild, channel_id)) > 0:
                await self.sleep(left)
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

    def _target(
        self, guild: Any, row: Any, mode: str, feature: str = rules.FEATURE
    ) -> tuple[Any, int | None, str | None]:
        """The channel a copy goes in and its home; neither and no reason means OWN_HOME."""
        channel_id = int(row["channel_id"])
        real = shadow_home.channel_of(self.bot, guild, channel_id)
        if real is None:
            return (None, None, rules.TROUBLE_CHANNEL_GONE)
        if mode != "shadow":
            return (real, None, None)
        home = shadow_home.channel_id(self.bot, guild, feature=feature)
        if not home:
            return (None, None, rules.TROUBLE_NO_HOME)
        if int(home) == channel_id:
            return (None, int(home), None)
        found = shadow_home.channel_of(self.bot, guild, home)
        if found is None:
            return (None, home, rules.TROUBLE_HOME_GONE.format(home=home))
        return (found, int(home), None)

    def _wanted(
        self, guild: Any, row: Any, mode: str, feature: str = rules.FEATURE
    ) -> int | None:
        """Where the row's copy belongs right now; None when it belongs nowhere."""
        if mode == "off" or row["paused"]:
            return None
        if mode != "shadow":
            return int(row["channel_id"])
        home = shadow_home.channel_id(self.bot, guild, feature=feature)
        if not home or int(home) == int(row["channel_id"]):
            return None
        return int(home)

    def _misplaced(self, guild: Any, row: Any, mode: str, feature: str = rules.FEATURE) -> bool:
        if not row["message_id"]:
            return False
        wanted = self._wanted(guild, row, mode, feature)
        return int(row["posted_channel_id"] or 0) != (wanted or -1)

    async def rule_of(self, guild: Any, row: Any) -> tuple[str, str]:
        return await owner_rule(self.bot, guild, row)

    async def _place(self, guild: Any, channel_id: int, *, first: bool = False) -> str:
        """Called with the channel's lock held, so the row read here is the one acted on."""
        row = await rules.get_row(self.db, guild.id, channel_id)
        mode, feature = await self.rule_of(guild, row)
        if not rules.is_running(row) or mode == "off":
            return NOT_RUNNING
        _, gap, silent = rules.numbers(self.store, guild.id)
        if not first and self._wait(row, gap) > 0:
            return TOO_SOON
        target, home, trouble = self._target(guild, row, mode, feature)
        if trouble is None and target is None:
            return await self._own_home(guild, row)
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
        post = None
        if rules.is_post(row):
            post = await posts.get_post_by_id(self.db, int(row["post_id"]))
            if post is None:
                return await self._stopped(guild, row, rules.TROUBLE_POST_GONE)
        undone = await self._take_down(guild, row)
        if undone is not None:
            return await self._failed(guild, row, undone, old_copy=True)
        note = shadow_home.note_line(self.bot, guild, f"<#{channel_id}>") if home else ""
        stamps: dict[str, Any] = {}
        if post is None:
            payload: dict[str, Any] = {"content": rules.fit(note, row["text"])}
        else:
            payload, stamps = await post_message(self.bot, guild, post, note)
            if is_empty(payload):
                return await self._stopped(guild, row, rules.TROUBLE_POST_EMPTY)
        try:
            sent = await target.send(
                **payload, allowed_mentions=discord.AllowedMentions.none(), silent=silent
            )
        except Exception as exc:
            return await self._failed(guild, row, exc)
        try:
            await rules.write_copy(
                self.db, guild.id, channel_id, sent.id, target.id, moved=not first, at=self.now()
            )
            if post is not None:
                await self._post_copy(post, int(sent.id), bool(home), stamps)
        except BaseException:
            await self._unsend(sent)
            raise
        if post is not None and not home:
            await self._drop_test_copy(guild, post, row["message_id"])
        await self._pin(guild, row, sent)
        self.heard[channel_id] = 0
        self.outage.pop(channel_id, None)
        self.tried.pop(channel_id, None)
        self.last.pop(channel_id, None)
        self.reached.pop(channel_id, None)
        self.watched.add(channel_id)
        if first:
            await self._posted(guild, row, target, home, sent.id)
        return REHEARSED if home else POSTED

    async def _post_copy(self, post: Any, message_id: int, rehearsed: bool, stamps: Any) -> None:
        """The post knows its copy too, so the Posts page and a block redraw find it."""
        from .post_blocks import set_drawn

        write = posts.set_shadow_posted if rehearsed else posts.set_posted
        await write(self.db, int(post["id"]), message_id, posts.hash_of(post))
        await set_drawn(self.db, int(post["id"]), stamps)

    async def _drop_test_copy(self, guild: Any, post: Any, old: Any) -> None:
        """A real copy takes a Post to test copy down; the copy just moved is not one."""
        ghost = posts.shadow_id(post)
        if not ghost or int(ghost) == int(old or 0):
            return
        try:
            await posts.drop_shadow(self.bot, guild, post, None, VIA_DISCORD)
        except Exception as exc:
            log.warning("sticky: a test copy %s was not taken down — %s", ghost, why(exc))

    async def _pin(self, guild: Any, row: Any, sent: Any) -> None:
        """The copy is already stored; a pin that fails leaves it up and is said once."""
        if not rules.pins(self.store, guild.id):
            return
        try:
            await sent.pin(reason=PIN_REASON)
        except Exception as exc:
            channel_id = int(row["channel_id"])
            if (channel_id, PIN_FAILED) in self.said:
                return
            self.said.add((channel_id, PIN_FAILED))
            reason = why(exc)
            log.warning("sticky: the copy in channel %s was not pinned — %s", channel_id, reason)
            await self._safely(
                log_action(
                    self.bot,
                    guild,
                    "sticky.pin_failed",
                    details={
                        "channel_id": channel_id,
                        "message_id": int(sent.id),
                        "reason": reason,
                    },
                )
            )

    async def _unsend(self, sent: Any) -> None:
        """A copy the row never learned of is deleted, so the next one is not a second."""
        try:
            await sent.delete()
        except Exception as exc:
            log.warning(
                "sticky: copy %s in channel %s was posted, not stored and not deleted — %s: %s",
                getattr(sent, "id", "?"),
                getattr(getattr(sent, "channel", None), "id", "?"),
                type(exc).__name__,
                exc,
            )

    async def _own_home(self, guild: Any, row: Any) -> str:
        channel_id = int(row["channel_id"])
        undone = await self._take_down(guild, row)
        if undone is not None:
            return await self._failed(guild, row, undone, old_copy=True)
        await self._would(guild, row, None, None, reason=OWN_HOME, once=True)
        self.heard[channel_id] = 0
        self.watched.add(channel_id)
        return OWN_HOME

    async def _take_down(self, guild: Any, row: Any) -> Exception | None:
        """None when no copy is left anywhere; otherwise what kept the old one up."""
        if not row["message_id"] or not row["posted_channel_id"]:
            return None
        channel = shadow_home.channel_of(self.bot, guild, row["posted_channel_id"])
        if channel is not None:
            try:
                await partial(channel, row["message_id"]).delete()
            except discord.NotFound:
                pass
            except Exception as exc:
                return exc
        await rules.write_copy(self.db, guild.id, row["channel_id"], None, None)
        if rules.is_post(row):
            await posts.clear_posted(self.db, int(row["post_id"]))
        return None

    async def _failed(
        self, guild: Any, row: Any, exc: Exception, *, old_copy: bool = False
    ) -> str:
        if passing(exc):
            return await self._unreachable(guild, row, exc)
        if old_copy:
            return await self._stopped(guild, row, rules.TROUBLE_OLD_COPY.format(reason=why(exc)))
        return await self._stopped(guild, row, refusal_words(exc))

    async def _unreachable(self, guild: Any, row: Any, exc: Exception) -> str:
        """The row stays running; one log row per outage, however many tries it takes."""
        channel_id = int(row["channel_id"])
        known = channel_id in self.outage
        reason = rules.UNREACHABLE_REASON.format(why=outage_why(exc), channel_id=channel_id)
        self.tried[channel_id] = self.now()
        self.outage[channel_id] = reason
        self.watched.add(channel_id)
        if known:
            return UNREACHABLE
        log.warning("sticky: channel %s not reached, will try again — %s", channel_id, reason)
        await self._safely(
            log_action(
                self.bot,
                guild,
                "sticky.post_failed",
                details={"channel_id": channel_id, "reason": reason, "retrying": True},
            )
        )
        return UNREACHABLE

    async def _stopped(self, guild: Any, row: Any, trouble: str) -> str:
        """Said once: the row carries the reason, and only staff or a found home restart it."""
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
        if done == UNREACHABLE:
            return rules.SAVED_UNREACHABLE.format(reason=self.outage.get(channel_id, ""))
        if done == OWN_HOME:
            return rules.SAVED_OWN_HOME.format(channel_id=channel_id)
        if row["paused"]:
            return rules.SAVED_PAUSED
        return rules.SAVED_OFF

    async def _answer(self, guild: Any, channel_id: int, done: str, code: str) -> Outcome:
        row = await rules.get_row(self.db, guild.id, channel_id)
        return Outcome(True, self._placed_words(guild, channel_id, done, row), code, 200, row)

    async def save(
        self,
        guild: Any,
        channel_id: int,
        text: Any,
        actor: Any,
        *,
        via: str = VIA_DISCORD,
        post: Any = None,
    ) -> Outcome:
        if post is not None:
            return await self.save_post(guild, channel_id, post, actor, via=via)
        if text is not None and not isinstance(text, str):
            return refusal(rules.NOT_WORDS, "bad_text", 400)
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
            await self._let_go(guild, existing, None)
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

    async def post_refusal(self, guild: Any, channel_id: int, post: Any) -> Outcome | None:
        """A post is a sticky once, never with the door, and never while posted elsewhere."""
        from .post_blocks import kinds_on

        title = str(posts.row_value(post, "title", ""))
        if posts.carries_door(post):
            return refusal(rules.POST_CARRIES_DOOR.format(title=title), "post_carries_door", 409)
        held = await rules.row_of_post(self.db, int(post["id"]))
        if held is not None and int(held["channel_id"]) != int(channel_id):
            return refusal(
                rules.POST_HELD.format(title=title, channel_id=held["channel_id"]),
                "post_is_a_sticky",
                409,
            )
        if held is None and posts.is_posted(post):
            return refusal(rules.POST_IS_UP.format(title=title), "post_is_posted", 409)
        has_words = str(posts.row_value(post, "body", "") or "").strip()
        if not has_words and not await kinds_on(self.db, int(post["id"])):
            return refusal(rules.POST_IS_EMPTY.format(title=title), "post_is_empty", 400)
        return None

    async def find_post(self, guild: Any, wanted: Any) -> Any:
        if isinstance(wanted, int) and not isinstance(wanted, bool):
            found = await posts.get_post_by_id(self.db, wanted)
            return found if found is not None and int(found["guild_id"]) == guild.id else None
        return await posts.get_post(self.db, guild.id, str(wanted or "").strip())

    async def save_post(
        self, guild: Any, channel_id: int, wanted: Any, actor: Any, *, via: str = VIA_DISCORD
    ) -> Outcome:
        """The sticky keeps a post at the bottom: its words and blocks, drawn fresh each move."""
        post = await self.find_post(guild, wanted)
        if post is None:
            return refusal(
                rules.NO_SUCH_POST.format(slug=str(wanted or "")[:60]), "no_such_post", 404
            )
        channel = shadow_home.channel_of(self.bot, guild, channel_id)
        async with self.lock(channel_id):
            refused = await self.post_refusal(guild, channel_id, post)
            if refused is not None:
                return refused
            existing = await rules.get_row(self.db, guild.id, channel_id)
            if existing is None:
                if channel is None:
                    return refusal(rules.NO_SUCH_CHANNEL, "no_such_channel", 404)
                if not rules.postable(channel):
                    return refusal(
                        rules.NOT_POSTABLE.format(channel_id=channel_id), "not_postable", 400
                    )
            await self._let_go(guild, existing, int(post["id"]))
            by = getattr(actor, "id", actor)
            made = await rules.write_words(
                self.db, guild.id, channel_id, "", by, post_id=int(post["id"])
            )
            await posts.set_post_fields(
                self.db, int(post["id"]), by=posts.actor_id(actor), channel_id=int(channel_id)
            )
            await log_action(
                self.bot,
                guild,
                kind_via("sticky.set" if made else "sticky.edited", via),
                actor=actor,
                details={
                    "channel_id": int(channel_id),
                    "post": str(post["slug"]),
                    "post_id": int(post["id"]),
                    "via": via,
                },
            )
            done = await self._place(guild, channel_id, first=True)
            return await self._answer(guild, channel_id, done, "set" if made else "edited")

    async def _let_go(self, guild: Any, existing: Any, keeps: int | None) -> None:
        """A sticky that stops keeping a post takes its copy down while it still knows it."""
        if existing is None or not rules.is_post(existing):
            return
        if int(existing["post_id"]) != (keeps or 0):
            await self._take_down(guild, existing)

    async def repost(
        self, guild: Any, channel_id: int, actor: Any, *, via: str = VIA_DISCORD
    ) -> Outcome:
        """The Posts page's Update on a sticky's post: a fresh copy at the bottom, at once."""
        async with self.lock(channel_id):
            done = await self._place(guild, channel_id, first=True)
            row = await rules.get_row(self.db, guild.id, channel_id)
            words = self._placed_words(guild, channel_id, done, row)
            post = await posts.get_post_by_id(self.db, int(row["post_id"])) if row else None
            if done in (POSTED, REHEARSED, OWN_HOME, TEST_MODE):
                return Outcome(True, words, "reposted", 200, post)
            return refusal(words, "sticky_not_posted", 409)

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
                details={"channel_id": int(channel_id), "via": via} | self._left_details(row, left),
            )
            words = self._down_words(
                guild, row, left, rules.PAUSED_NOW, rules.PAUSED_COPY_LEFT, rules.PAUSED_NO_COPY
            )
            row = await rules.get_row(self.db, guild.id, channel_id)
            return Outcome(True, words, "paused", 200, row)

    def _left_details(self, row: Any, left: Exception | None) -> dict[str, Any]:
        if left is None:
            return {}
        return {
            "copy_left": left_words(left),
            "left_channel_id": int(row["posted_channel_id"]),
            "left_message_id": int(row["message_id"]),
        }

    def _down_words(
        self, guild: Any, row: Any, left: Exception | None, down: str, kept: str, none: str
    ) -> str:
        """What became of the copy the row had: taken down, still up and why, or never there."""
        channel_id = int(row["channel_id"])
        if not row["message_id"] or not row["posted_channel_id"]:
            return none.format(channel_id=channel_id)
        where = int(row["posted_channel_id"])
        if left is None:
            return down.format(channel_id=channel_id, where=where)
        return kept.format(
            channel_id=channel_id,
            where=where,
            reason=left_words(left),
            link=rules.message_link(guild.id, where, row["message_id"]),
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
                    "text": rules.words_of(row)[: rules.LOGGED_CHARS],
                    "via": via,
                }
                | self._left_details(row, left),
            )
            words = self._down_words(
                guild, row, left, rules.REMOVED_NOW, rules.REMOVED_COPY_LEFT, rules.REMOVED_NOW
            )
            return Outcome(True, words, "removed", 200)

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
                        "text": rules.words_of(row)[: rules.LOGGED_CHARS],
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
        """Every copy is put where the mode says it belongs, and taken down anywhere else."""
        if getattr(guild, "unavailable", False) or not self.db.is_connected:
            return
        for found in await rules.rows_for_guild(self.db, guild.id):
            channel_id = int(found["channel_id"])
            try:
                async with self.lock(channel_id):
                    await self._settle_one(guild, channel_id)
            except Exception as exc:
                log.warning(
                    "sticky: channel %s was not settled — %s: %s",
                    channel_id,
                    type(exc).__name__,
                    exc,
                )

    async def _settle_one(self, guild: Any, channel_id: int) -> None:
        row = await rules.get_row(self.db, guild.id, channel_id)
        if row is None:
            return
        mode, feature = await self.rule_of(guild, row)
        if self._misplaced(guild, row, mode, feature):
            left = await self._take_down(guild, row)
            if left is not None:
                log.warning(
                    "sticky: the copy of channel %s is still up — %s", channel_id, left_words(left)
                )
                return
            row = await rules.get_row(self.db, guild.id, channel_id)
        if mode != "off" and self._home_is_back(guild, row, mode, feature):
            await rules.write_trouble(self.db, guild.id, channel_id, None)
            row = await rules.get_row(self.db, guild.id, channel_id)
        if not rules.is_running(row) or mode == "off":
            return
        self.watched.add(channel_id)
        if row["message_id"]:
            return
        await self._place(guild, channel_id, first=True)

    def _home_is_back(self, guild: Any, row: Any, mode: str, feature: str) -> bool:
        if not rules.is_home_trouble(row["trouble"]):
            return False
        return self._target(guild, row, mode, feature)[2] is None


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
    "OWN_HOME",
    "POSTED",
    "REHEARSED",
    "TEST_MODE",
    "TOO_SOON",
    "is_empty",
    "owner_rule",
    "post_message",
    "UNREACHABLE",
    "Desk",
    "desk_of",
    "missing_permissions",
    "passing",
    "refusal_words",
]
