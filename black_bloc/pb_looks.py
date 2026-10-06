"""The personal best feed at work: looking members up, looking at their runs, posting the news."""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import discord

from . import pb_match, pb_news, pb_store, shadow
from .actionlog import log_action
from .pb_feed import (
    CHANNEL_GONE,
    FEATURE,
    LOOKUP,
    NO_CHANNEL,
    NO_SHADOW_HOME,
    OFF,
    SHADOW,
    TEST_MODE_REFUSED,
    aimed_at,
    backoff_minutes,
    link_view,
    mode_of,
    per_tick,
    ping_role,
    population,
    post_embed,
    rehearsal_line,
    send_reason,
    work_list,
)
from .settings_store import (
    PB_FEED_AUTO_MATCH,
    PB_FEED_CYCLE_REQUESTS,
    PB_FEED_INTERVAL,
    PB_FEED_MAX_AGE_DAYS,
    PB_FEED_MAX_POSTS,
)
from .speedrun import NOT_FOUND, TOO_LARGE, PersonalBest, SpeedrunClient, SpeedrunError

log = logging.getLogger(__name__)

FEED_ATTR = "_pb_feed"
TAKEN = "taken"
RUNNER_GONE = "runner_gone"
LINK_MOVED = "link_moved"


@dataclass(frozen=True)
class Looked:
    """What one look at one member came to."""

    found: int = 0
    seen: int = 0
    first: bool = False
    gone: bool = False
    trouble: str = ""


async def safely(writing: Any, what: str) -> Any:
    try:
        return await writing
    except Exception as exc:
        log.warning("pb feed: %s not written — %s: %s", what, type(exc).__name__, exc)
        return None


class Feed:
    """One per bot: the client, the lock every look and move takes, and the request count."""

    def __init__(self, bot: Any, client: Any = None) -> None:
        self.bot = bot
        origin = getattr(getattr(bot, "settings", None), "origin", None)
        self.client = client or SpeedrunClient(origin=origin)
        self.lock = asyncio.Lock()
        self.spent: deque[datetime] = deque()
        self.cap_said_at: dict[int, datetime] = {}

    async def close(self) -> None:
        await self.client.close()

    def count(self, before: int, now: datetime) -> None:
        for _ in range(max(0, int(self.client.requests) - before)):
            self.spent.append(now)

    def within_cap(self, guild_id: int, now: datetime) -> bool:
        store = self.bot.store
        window = timedelta(minutes=int(store.get(guild_id, PB_FEED_INTERVAL)))
        while self.spent and now - self.spent[0] >= window:
            self.spent.popleft()
        return len(self.spent) < int(store.get(guild_id, PB_FEED_CYCLE_REQUESTS))

    async def cap_reached(self, guild: Any, now: datetime) -> None:
        window = timedelta(minutes=int(self.bot.store.get(guild.id, PB_FEED_INTERVAL)))
        last = self.cap_said_at.get(guild.id)
        if last is not None and now - last < window:
            return
        self.cap_said_at[guild.id] = now
        await safely(
            log_action(
                self.bot,
                guild,
                "pbfeed.cap_reached",
                details={
                    "requests": len(self.spent),
                    "cap": int(self.bot.store.get(guild.id, PB_FEED_CYCLE_REQUESTS)),
                },
            ),
            "the log row",
        )

    async def tick(self, guild: Any, now: datetime | None = None) -> int:
        """One minute's share of one server. Never raises; returns how many members it took."""
        now = now or datetime.now(UTC)
        store, db = self.bot.store, self.bot.db
        if mode_of(store, guild.id) == OFF or getattr(guild, "unavailable", False):
            return 0
        state = await pb_store.looks(db, guild.id)
        until = pb_store.parsed(state["backoff_until"]) if state is not None else None
        if until is not None and now < until:
            return 0
        rows = {int(row["user_id"]): row for row in await pb_store.matches(db, guild.id)}
        links = await pb_store.links(db)
        present = {
            user_id for user_id in set(rows) | set(links) if guild.get_member(user_id) is not None
        }
        work = work_list(rows, links, present, store=store, guild_id=guild.id, now=now)
        take = per_tick(
            population(rows, links, present), int(store.get(guild.id, PB_FEED_INTERVAL))
        )
        taken = 0
        for what, user_id in work[:take]:
            if not self.within_cap(guild.id, now):
                await self.cap_reached(guild, now)
                break
            try:
                if what == LOOKUP:
                    await self.lookup(guild, user_id, links.get(user_id), now=now)
                else:
                    await self.look(guild, user_id, now=now)
            except SpeedrunError as exc:
                await self.outage(guild, exc, now)
                break
            except Exception as exc:
                log.exception("pb feed: member %s was not looked at", user_id)
                await self.outage(guild, exc, now)
                break
            taken += 1
        await self.summary(guild, now)
        return taken

    async def outage(self, guild: Any, exc: BaseException, now: datetime) -> None:
        """The first failure of an outage is logged; the ones after it only push the wait out."""
        reason = str(exc) if isinstance(exc, SpeedrunError) else f"{type(exc).__name__}: {exc}"
        before = await pb_store.looks(self.bot.db, guild.id)
        failures = int(before["failures"] or 0) + 1 if before is not None else 1
        until = now + timedelta(minutes=backoff_minutes(failures))
        log.warning("pb feed: could not look for guild %s — %s", guild.id, reason)
        await safely(pb_store.record_outage(self.bot.db, guild.id, reason, until, now), "the look")
        if failures == 1:
            await safely(
                log_action(
                    self.bot,
                    guild,
                    "pbfeed.look_failed",
                    details={"reason": reason, "asks_again_at": until.isoformat()},
                ),
                "the log row",
            )

    async def worked(self, guild: Any, found: int, now: datetime) -> None:
        ended = await safely(
            pb_store.record_ok(self.bot.db, guild.id, found=found, now=now), "the look"
        )
        if ended:
            await safely(log_action(self.bot, guild, "pbfeed.recovered"), "the log row")

    async def summary(self, guild: Any, now: datetime) -> None:
        state = await pb_store.looks(self.bot.db, guild.id)
        since = pb_store.parsed(state["summary_at"]) if state is not None else None
        window = timedelta(minutes=int(self.bot.store.get(guild.id, PB_FEED_INTERVAL)))
        if since is None or now - since < window:
            return
        looks, found = await pb_store.take_summary(self.bot.db, guild.id, now)
        if looks and not found:
            await safely(
                log_action(self.bot, guild, "pbfeed.nothing_new", details={"looks": looks}),
                "the log row",
            )

    async def lookup(
        self, guild: Any, user_id: int, login: str | None, *, now: datetime | None = None
    ) -> Any:
        """A member's speedrun.com account from their Twitch login: exactly one, or none."""
        now = now or datetime.now(UTC)
        db = self.bot.db
        async with self.lock:
            row = await pb_store.match(db, guild.id, user_id)
            if row is not None and row["state"] in (pb_store.OPTED_OUT, pb_store.BLOCKED):
                return row
            if row is not None and row["state"] == pb_store.MATCHED:
                if row["source"] != pb_store.AUTO or (row["twitch_login"] or "") == (login or ""):
                    return row
                row = await pb_store.write_state(
                    db,
                    guild.id,
                    user_id,
                    pb_store.NONE,
                    state_by=pb_store.AUTO,
                    reason=LINK_MOVED,
                    twitch_login=login,
                    now=now,
                )
                await safely(
                    log_action(
                        self.bot,
                        guild,
                        "pbfeed.unmatched",
                        target=user_id,
                        details={"why": LINK_MOVED, "twitch_login": login},
                    ),
                    "the log row",
                )
            if not login or not self.bot.store.get(guild.id, PB_FEED_AUTO_MATCH):
                return row
            before = int(self.client.requests)
            try:
                answer = await pb_match.by_twitch(self.client, login)
            finally:
                self.count(before, now)
            await self.worked(guild, 0, now)
            if answer.outcome != pb_match.FOUND:
                return await pb_store.write_state(
                    db,
                    guild.id,
                    user_id,
                    pb_store.NONE,
                    state_by=pb_store.AUTO,
                    reason=answer.outcome,
                    twitch_login=login,
                    now=now,
                )
            runner = answer.runner
            try:
                row = await pb_store.write_match(
                    db,
                    guild.id,
                    user_id,
                    runner,
                    source=pb_store.AUTO,
                    twitch_login=login,
                    now=now,
                )
            except pb_store.RunnerTaken as exc:
                await safely(
                    log_action(
                        self.bot,
                        guild,
                        "pbfeed.match_refused",
                        target=user_id,
                        details={
                            "runner": runner.name,
                            "runner_id": runner.id,
                            "held_by": exc.holder_id,
                            "twitch_login": login,
                        },
                    ),
                    "the log row",
                )
                return await pb_store.write_state(
                    db,
                    guild.id,
                    user_id,
                    pb_store.NONE,
                    state_by=pb_store.AUTO,
                    reason=TAKEN,
                    twitch_login=login,
                    now=now,
                )
            await safely(
                log_action(
                    self.bot,
                    guild,
                    "pbfeed.matched",
                    target=user_id,
                    details={
                        "runner": runner.name,
                        "runner_id": runner.id,
                        "twitch_login": login,
                        "source": pb_store.AUTO,
                    },
                ),
                "the log row",
            )
            return row

    async def look(self, guild: Any, user_id: int, *, now: datetime | None = None) -> Looked:
        """One member's personal bests against their baseline; the news is posted, once."""
        now = now or datetime.now(UTC)
        db, store = self.bot.db, self.bot.store
        async with self.lock:
            row = await pb_store.match(db, guild.id, user_id)
            if row is None or row["state"] != pb_store.MATCHED or not row["src_user_id"]:
                return Looked()
            before = int(self.client.requests)
            try:
                fetched = await self.client.personal_bests(str(row["src_user_id"]))
            except SpeedrunError as exc:
                if exc.kind == NOT_FOUND:
                    return await self.runner_gone(guild, row, now)
                if exc.kind == TOO_LARGE:
                    return await self.member_trouble(guild, row, str(exc), now)
                raise
            finally:
                self.count(before, now)
            since = pb_store.parsed(row["baseline_at"])
            verdict = pb_news.news(
                await pb_store.baseline(db, guild.id, user_id),
                fetched,
                since=since,
                now=now,
                max_age_days=int(store.get(guild.id, PB_FEED_MAX_AGE_DAYS)),
                max_posts=int(store.get(guild.id, PB_FEED_MAX_POSTS)),
            )
            for best in verdict.news:
                await self.post(guild, row, best, now)
            held = 0
            for best in verdict.held:
                claimed = await pb_store.claim_post(
                    db, guild.id, user_id, best, row["src_name"], outcome=pb_store.HELD, now=now
                )
                held += 1 if claimed else 0
            seen = [*(one.best for one in verdict.quiet), *verdict.news, *verdict.held]
            await pb_store.record_look(
                db, guild.id, user_id, seen, first=since is None, newest=bool(verdict.news), now=now
            )
            await self.worked(guild, len(verdict.news), now)
            if since is None:
                await safely(
                    log_action(
                        self.bot,
                        guild,
                        "pbfeed.baseline",
                        target=user_id,
                        details={"runner": row["src_name"], "runs": len(seen)},
                    ),
                    "the log row",
                )
            if held:
                await safely(
                    log_action(
                        self.bot,
                        guild,
                        "pbfeed.held_back",
                        target=user_id,
                        details={"runner": row["src_name"], "runs": held},
                    ),
                    "the log row",
                )
            return Looked(found=len(verdict.news), seen=len(seen), first=since is None)

    async def runner_gone(self, guild: Any, row: Any, now: datetime) -> Looked:
        await pb_store.write_state(
            self.bot.db,
            guild.id,
            int(row["user_id"]),
            pb_store.NONE,
            state_by=pb_store.AUTO,
            reason=RUNNER_GONE,
            twitch_login=row["twitch_login"],
            now=now,
        )
        await safely(
            log_action(
                self.bot,
                guild,
                "pbfeed.runner_gone",
                target=int(row["user_id"]),
                details={"runner": row["src_name"], "runner_id": row["src_user_id"]},
            ),
            "the log row",
        )
        return Looked(gone=True)

    async def member_trouble(self, guild: Any, row: Any, reason: str, now: datetime) -> Looked:
        fresh = await pb_store.record_look_error(
            self.bot.db, guild.id, int(row["user_id"]), reason, now
        )
        if fresh:
            await safely(
                log_action(
                    self.bot,
                    guild,
                    "pbfeed.look_failed",
                    target=int(row["user_id"]),
                    details={"runner": row["src_name"], "reason": reason},
                ),
                "the log row",
            )
        return Looked(trouble=reason)

    def details(self, row: Any, best: PersonalBest, mode: str) -> dict[str, Any]:
        return {
            "mode": mode,
            "runner": row["src_name"],
            "run_id": best.run_id,
            "game": best.game,
            "category": best.category,
            "seconds": best.seconds,
            "place": best.place,
            "link": best.weblink,
        }

    async def post(self, guild: Any, row: Any, best: PersonalBest, now: datetime) -> str:
        """Claimed before it is sent, so one run can never be posted twice."""
        bot, db, store = self.bot, self.bot.db, self.bot.store
        user_id = int(row["user_id"])
        post_id = await pb_store.claim_post(db, guild.id, user_id, best, row["src_name"], now=now)
        if post_id is None:
            return pb_store.CLAIMED
        mode = mode_of(store, guild.id)
        aimed = aimed_at(store, guild.id)
        details = self.details(row, best, mode) | {"aimed_at": aimed}
        if mode == OFF:
            await pb_store.settle_post(db, post_id, pb_store.DRY, aimed_at=aimed, reason=OFF)
            return pb_store.DRY
        rehearsing = mode == SHADOW
        home = shadow.channel_id(bot, guild, feature=FEATURE) if rehearsing else aimed
        channel = shadow.channel_of(bot, guild, home)
        if channel is None:
            reason = NO_SHADOW_HOME if rehearsing else NO_CHANNEL if aimed is None else CHANNEL_GONE
            return await self.not_posted(guild, post_id, user_id, details, home, reason, rehearsing)
        guard = getattr(bot, "guard", None)
        if guard is not None and not guard.allows_channel(channel.id):
            return await self.not_posted(
                guild, post_id, user_id, details, home, TEST_MODE_REFUSED, True
            )
        role = None if rehearsing else ping_role(store, guild.id)
        content = rehearsal_line(bot, guild) if rehearsing else (f"<@&{role}>" if role else "")
        allowed = (
            discord.AllowedMentions(everyone=False, users=False, roles=[discord.Object(id=role)])
            if role
            else discord.AllowedMentions.none()
        )
        sending: dict[str, Any] = {
            "embed": post_embed(
                store, guild.id, guild.get_member(user_id), user_id, row["src_name"], best
            ),
            "allowed_mentions": allowed,
        }
        view = link_view(store, guild.id, best.weblink)
        if view is not None:
            sending["view"] = view
        try:
            message = await channel.send(content or None, **sending)
        except Exception as exc:
            reason = send_reason(exc)
            log.warning("pb feed: a personal best was not posted — %s", reason)
            await pb_store.settle_post(
                db, post_id, pb_store.FAILED, channel_id=home, aimed_at=aimed, reason=reason
            )
            await safely(
                log_action(
                    bot,
                    guild,
                    "pbfeed.post_failed",
                    target=user_id,
                    details=details | {"channel_id": home, "reason": reason},
                ),
                "the log row",
            )
            return pb_store.FAILED
        message_id = getattr(message, "id", None)
        outcome = pb_store.REHEARSED if rehearsing else pb_store.POSTED
        await pb_store.settle_post(
            db, post_id, outcome, channel_id=home, aimed_at=aimed, message_id=message_id
        )
        placed = details | {"channel_id": home, "message_id": message_id}
        if rehearsing:
            placed |= {"rehearsed": True, "shadow_home": home}
        await safely(
            log_action(
                bot,
                guild,
                "pbfeed.would_post" if rehearsing else "pbfeed.posted",
                target=user_id,
                details=placed,
            ),
            "the log row",
        )
        return outcome

    async def not_posted(
        self,
        guild: Any,
        post_id: int,
        user_id: int,
        details: dict[str, Any],
        home: Any,
        reason: str,
        dry: bool,
    ) -> str:
        """A rehearsal with nowhere to go is a dry run; a real post with nowhere to go failed."""
        outcome = pb_store.DRY if dry else pb_store.FAILED
        await pb_store.settle_post(
            self.bot.db,
            post_id,
            outcome,
            channel_id=home,
            aimed_at=details.get("aimed_at"),
            reason=reason,
        )
        kind = "pbfeed.would_post" if dry else "pbfeed.post_failed"
        extra = {"rehearsed": False} if dry else {}
        await safely(
            log_action(
                self.bot,
                guild,
                kind,
                target=user_id,
                details=details | extra | {"channel_id": home, "reason": reason},
            ),
            "the log row",
        )
        return outcome


def feed_of(bot: Any) -> Feed:
    found = getattr(bot, FEED_ATTR, None)
    if found is None:
        found = Feed(bot)
        setattr(bot, FEED_ATTR, found)
    return found


__all__ = ["FEED_ATTR", "Feed", "Looked", "feed_of", "safely"]
