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
from .logkinds import VIA_DISCORD, kind_via
from .pb_feed import (
    AT_THE_CAP,
    BACKING_OFF,
    CHANNEL_GONE,
    FAULT,
    FEATURE,
    LOOKUP,
    MISSED_ONCE,
    MISSED_STAFF,
    MISSES_BEFORE_GONE,
    NO_CHANNEL,
    NO_SHADOW_HOME,
    OFF,
    SHADOW,
    TEST_MODE_REFUSED,
    UNCONFIRMED,
    UNTOLD,
    aimed_at,
    backoff_minutes,
    link_view,
    minutes_until,
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
from .speedrun import EMBED_RETRY_SECONDS, NOT_FOUND, PersonalBest, SpeedrunClient, SpeedrunError

log = logging.getLogger(__name__)

FEED_ATTR = "_pb_feed"
TAKEN = "taken"
RUNNER_GONE = "runner_gone"
LINK_MOVED = "link_moved"
TROUBLE = "trouble"
NOT_NEWS = (pb_news.TOO_OLD, pb_news.BEFORE_BASELINE, pb_news.UNDATED)


@dataclass(frozen=True)
class Kinds:
    """The log kinds one way of posting writes: sent, rehearsed or dry, and failed."""

    posted: str
    rehearsed: str
    failed: str


FRESH = Kinds("pbfeed.posted", "pbfeed.would_post", "pbfeed.post_failed")
AGAIN = Kinds("pbfeed.posted_again", "pbfeed.would_post_again", "pbfeed.post_failed")


@dataclass(frozen=True)
class Sent:
    """Where one send went: its row, the outcome, the channel, and why not, in words."""

    post_id: int
    outcome: str
    channel_id: int | None
    reason: str | None = None
    refused: bool = False


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
        self.booted: set[int] = set()

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

    async def hold(self, guild_id: int, now: datetime) -> str | None:
        """Why a staff move may not ask speedrun.com right now, in words, or None."""
        state = await pb_store.looks(self.bot.db, guild_id)
        until = pb_store.parsed(state["backoff_until"]) if state is not None else None
        if until is not None and now < until:
            return BACKING_OFF.format(minutes=minutes_until(until, now))
        if self.within_cap(guild_id, now):
            return None
        interval = int(self.bot.store.get(guild_id, PB_FEED_INTERVAL))
        return AT_THE_CAP.format(
            cap=int(self.bot.store.get(guild_id, PB_FEED_CYCLE_REQUESTS)),
            interval=interval,
            minutes=minutes_until(self.spent[0] + timedelta(minutes=interval), now),
        )

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

    async def unconfirmed(self, guild: Any) -> int:
        """Once per boot: a claim no look settled is said in words and stops hiding."""
        if guild.id in self.booted:
            return 0
        self.booted.add(guild.id)
        async with self.lock:
            rows = await safely(
                pb_store.settle_stale_claims(self.bot.db, guild.id, UNCONFIRMED), "the claims"
            )
        if not rows:
            return 0
        await safely(
            log_action(
                self.bot,
                guild,
                "pbfeed.unconfirmed",
                details={
                    "runs": len(rows),
                    "run_ids": [str(row["run_id"]) for row in rows][:20],
                    "reason": UNCONFIRMED,
                },
            ),
            "the log row",
        )
        return len(rows)

    async def tick(self, guild: Any, now: datetime | None = None) -> int:
        """One minute's share of one server. Never raises; returns how many members it took."""
        now = now or datetime.now(UTC)
        store, db = self.bot.store, self.bot.db
        if getattr(guild, "unavailable", False):
            return 0
        await self.unconfirmed(guild)
        if mode_of(store, guild.id) == OFF:
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
            except Exception:
                log.exception("pb feed: member %s was not looked at", user_id)
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
        async with self.lock:
            try:
                return await self._lookup(guild, user_id, login, now)
            except SpeedrunError as exc:
                if exc.outage:
                    raise
                await self.worked(guild, 0, now)
                return await self.lookup_trouble(guild, user_id, login, str(exc), now)
            except Exception as exc:
                log.exception("pb feed: member %s was not looked up", user_id)
                reason = FAULT.format(error=type(exc).__name__)
                return await self.lookup_trouble(guild, user_id, login, reason, now)

    async def _lookup(self, guild: Any, user_id: int, login: str | None, now: datetime) -> Any:
        db = self.bot.db
        row = await pb_store.match(db, guild.id, user_id)
        if row is not None and (
            row["state"] in (pb_store.OPTED_OUT, pb_store.BLOCKED) or row["opted_out_at"]
        ):
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

    async def lookup_trouble(
        self, guild: Any, user_id: int, login: str | None, reason: str, now: datetime
    ) -> Any:
        """This member's lookup alone failed: said on their row, and the queue moves on."""
        fresh = await safely(
            pb_store.record_lookup_error(
                self.bot.db, guild.id, user_id, login, reason, TROUBLE, now
            ),
            "the lookup",
        )
        if fresh:
            await safely(
                log_action(
                    self.bot,
                    guild,
                    "pbfeed.look_failed",
                    target=user_id,
                    details={"twitch_login": login, "reason": reason},
                ),
                "the log row",
            )
        return await safely(pb_store.match(self.bot.db, guild.id, user_id), "the lookup")

    async def look(self, guild: Any, user_id: int, *, now: datetime | None = None) -> Looked:
        """One member's personal bests against their baseline; the news is posted, once."""
        now = now or datetime.now(UTC)
        async with self.lock:
            row = await pb_store.match(self.bot.db, guild.id, user_id)
            if row is None or row["state"] != pb_store.MATCHED or not row["src_user_id"]:
                return Looked()
            try:
                return await self._look(guild, row, now)
            except SpeedrunError as exc:
                if exc.outage:
                    raise
                await self.worked(guild, 0, now)
                if exc.kind == NOT_FOUND:
                    return await self.missed(guild, row, now)
                return await self.member_trouble(guild, row, str(exc), now)
            except Exception as exc:
                log.exception("pb feed: member %s was not looked at", user_id)
                return await self.member_trouble(
                    guild, row, FAULT.format(error=type(exc).__name__), now
                )

    async def _look(self, guild: Any, row: Any, now: datetime) -> Looked:
        db, store = self.bot.db, self.bot.store
        user_id = int(row["user_id"])
        before = int(self.client.requests)
        told = getattr(self.client, "plain_since", None) is None
        try:
            fetched = await self.client.personal_bests(str(row["src_user_id"]))
        finally:
            self.count(before, now)
        if told and getattr(self.client, "plain_since", None) is not None:
            await self.untold(guild)
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
        dropped = {why: verdict.counts[why] for why in NOT_NEWS if verdict.counts.get(why)}
        await pb_store.record_look(
            db,
            guild.id,
            user_id,
            seen,
            first=since is None,
            newest=bool(verdict.news),
            quiet=dropped,
            now=now,
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
        if dropped:
            await safely(
                log_action(
                    self.bot,
                    guild,
                    "pbfeed.not_news",
                    target=user_id,
                    details={"runner": row["src_name"], **dropped},
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

    async def untold(self, guild: Any) -> None:
        reason = UNTOLD.format(hours=EMBED_RETRY_SECONDS // 3600)
        log.warning("pb feed: %s", reason)
        await safely(
            log_action(self.bot, guild, "pbfeed.subcategories_untold", details={"reason": reason}),
            "the log row",
        )

    async def missed(self, guild: Any, row: Any, now: datetime) -> Looked:
        """A 404. One is retried; two in a row undo an automatic match and never a staff one."""
        user_id = int(row["user_id"])
        misses = int(row["misses"] or 0) + 1
        staff = row["source"] == pb_store.STAFF
        if misses < MISSES_BEFORE_GONE:
            reason = MISSED_ONCE
        elif staff:
            reason = MISSED_STAFF.format(misses=misses)
        else:
            return await self.runner_gone(guild, row, now)
        await safely(pb_store.record_miss(self.bot.db, guild.id, user_id, reason, now), "the look")
        if staff and misses == MISSES_BEFORE_GONE:
            await safely(
                log_action(
                    self.bot,
                    guild,
                    "pbfeed.runner_missing",
                    target=user_id,
                    details={
                        "runner": row["src_name"],
                        "runner_id": row["src_user_id"],
                        "reason": reason,
                    },
                ),
                "the log row",
            )
        return Looked(trouble=reason)

    async def runner_gone(self, guild: Any, row: Any, now: datetime) -> Looked:
        await pb_store.runner_gone(self.bot.db, guild.id, int(row["user_id"]), RUNNER_GONE, now)
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
        fresh = await safely(
            pb_store.record_look_error(self.bot.db, guild.id, int(row["user_id"]), reason, now),
            "the look",
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

    def details(self, runner: Any, best: PersonalBest, mode: str) -> dict[str, Any]:
        return {
            "mode": mode,
            "runner": runner,
            "run_id": best.run_id,
            "game": best.game,
            "category": best.category,
            "seconds": best.seconds,
            "place": best.place,
            "link": best.weblink,
        }

    async def post(self, guild: Any, row: Any, best: PersonalBest, now: datetime) -> str:
        """Claimed before it is sent, so one run can never be posted twice."""
        db, store = self.bot.db, self.bot.store
        user_id = int(row["user_id"])
        post_id = await pb_store.claim_post(db, guild.id, user_id, best, row["src_name"], now=now)
        if post_id is None:
            return pb_store.CLAIMED
        if mode_of(store, guild.id) == OFF:
            aimed = aimed_at(store, guild.id)
            await pb_store.settle_post(db, post_id, pb_store.DRY, aimed_at=aimed, reason=OFF)
            return pb_store.DRY
        sent = await self.deliver(guild, post_id, user_id, row["src_name"], best)
        return sent.outcome

    async def repost(
        self, guild: Any, source: Any, *, actor: Any, via: str, now: datetime | None = None
    ) -> Sent:
        """A stored post sent again as a new row; the caller holds the lock, the mode is not off."""
        post_id = await pb_store.claim_again(self.bot.db, source, now=now)
        return await self.deliver(
            guild,
            post_id,
            int(source["user_id"]),
            source["src_name"],
            pb_store.best_of(source),
            kinds=AGAIN,
            actor=actor,
            via=via,
            extra={"via": via, "again_of": int(source["id"])},
        )

    async def logged(
        self,
        guild: Any,
        kind: str,
        user_id: int,
        details: dict[str, Any],
        *,
        actor: Any = None,
        via: str = VIA_DISCORD,
    ) -> None:
        await safely(
            log_action(
                self.bot,
                guild,
                kind_via(kind, via),
                actor=actor,
                target=user_id,
                details=details,
            ),
            "the log row",
        )

    async def deliver(
        self,
        guild: Any,
        post_id: int,
        user_id: int,
        runner: Any,
        best: PersonalBest,
        *,
        kinds: Kinds | None = None,
        actor: Any = None,
        via: str = VIA_DISCORD,
        extra: dict[str, Any] | None = None,
    ) -> Sent:
        """Where the mode sends it right now, settled on its row and logged once."""
        bot, db, store = self.bot, self.bot.db, self.bot.store
        kinds = kinds or FRESH
        mode = mode_of(store, guild.id)
        aimed = aimed_at(store, guild.id)
        details = self.details(runner, best, mode) | {"aimed_at": aimed} | (extra or {})
        rehearsing = mode == SHADOW
        home = shadow.channel_id(bot, guild, feature=FEATURE) if rehearsing else aimed
        channel = shadow.channel_of(bot, guild, home)
        who: dict[str, Any] = {"actor": actor, "via": via}
        if channel is None:
            reason = NO_SHADOW_HOME if rehearsing else NO_CHANNEL if aimed is None else CHANNEL_GONE
            return await self.not_posted(
                guild, post_id, user_id, details, home, reason, rehearsing, kinds, who
            )
        guard = getattr(bot, "guard", None)
        if guard is not None and not guard.allows_channel(channel.id):
            return await self.not_posted(
                guild, post_id, user_id, details, home, TEST_MODE_REFUSED, True, kinds, who
            )
        try:
            role = None if rehearsing else ping_role(store, guild.id)
            content = rehearsal_line(bot, guild) if rehearsing else (f"<@&{role}>" if role else "")
            allowed = (
                discord.AllowedMentions(
                    everyone=False, users=False, roles=[discord.Object(id=role)]
                )
                if role
                else discord.AllowedMentions.none()
            )
            sending: dict[str, Any] = {
                "embed": post_embed(
                    store, guild.id, guild.get_member(user_id), user_id, runner, best
                ),
                "allowed_mentions": allowed,
            }
            view = link_view(store, guild.id, best.weblink)
            if view is not None:
                sending["view"] = view
            message = await channel.send(content or None, **sending)
        except Exception as exc:
            reason = send_reason(exc)
            log.warning("pb feed: a personal best was not posted — %s", reason)
            await pb_store.settle_post(
                db, post_id, pb_store.FAILED, channel_id=home, aimed_at=aimed, reason=reason
            )
            await self.logged(
                guild,
                kinds.failed,
                user_id,
                details | {"channel_id": home, "reason": reason},
                **who,
            )
            return Sent(post_id, pb_store.FAILED, home, reason, refused=True)
        message_id = getattr(message, "id", None)
        outcome = pb_store.REHEARSED if rehearsing else pb_store.POSTED
        await pb_store.settle_post(
            db, post_id, outcome, channel_id=home, aimed_at=aimed, message_id=message_id
        )
        placed = details | {"channel_id": home, "message_id": message_id}
        if rehearsing:
            placed |= {"rehearsed": True, "shadow_home": home}
        await self.logged(
            guild, kinds.rehearsed if rehearsing else kinds.posted, user_id, placed, **who
        )
        return Sent(post_id, outcome, home)

    async def not_posted(
        self,
        guild: Any,
        post_id: int,
        user_id: int,
        details: dict[str, Any],
        home: Any,
        reason: str,
        dry: bool,
        kinds: Kinds,
        who: dict[str, Any],
    ) -> Sent:
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
        extra = {"rehearsed": False} if dry else {}
        await self.logged(
            guild,
            kinds.rehearsed if dry else kinds.failed,
            user_id,
            details | extra | {"channel_id": home, "reason": reason},
            **who,
        )
        return Sent(post_id, outcome, home, reason)


def feed_of(bot: Any) -> Feed:
    found = getattr(bot, FEED_ATTR, None)
    if found is None:
        found = Feed(bot)
        setattr(bot, FEED_ATTR, found)
    return found


__all__ = [
    "AGAIN",
    "FEED_ATTR",
    "FRESH",
    "Feed",
    "Kinds",
    "Looked",
    "Sent",
    "feed_of",
    "safely",
]
