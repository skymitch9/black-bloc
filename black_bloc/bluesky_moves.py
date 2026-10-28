from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import discord

from . import bluesky as rules
from . import bluesky_store as store
from . import shadow as shadow_home
from .actionlog import log_action
from .bluesky_feed import read_feed
from .logkinds import VIA_DISCORD, kind_via
from .panels import Outcome, refusal
from .settings_store import BLUESKY_SEED_COUNT, KEY_MAX

log = logging.getLogger(__name__)

LOCKS_ATTR = "_bluesky_locks"
FETCH_ATTR = "bluesky_fetch"
RECLAIM_FOR_CHANNEL = (
    rules.RETRY,
    rules.WOULD_POST,
    rules.SKIPPED_OLD,
    rules.SKIPPED_KIND,
    rules.FAILED,
)


@dataclass(frozen=True)
class Target:
    channel: Any
    rehearsing: bool
    aimed: int | None
    why: str | None = None


def lock_of(bot: Any, guild_id: int) -> asyncio.Lock:
    locks = getattr(bot, LOCKS_ATTR, None)
    if locks is None:
        locks = {}
        setattr(bot, LOCKS_ATTR, locks)
    found = locks.get(int(guild_id))
    if found is None:
        found = locks[int(guild_id)] = asyncio.Lock()
    return found


def moment(now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


def reach(bot: Any, guild: Any, channel_id: int | None, *, missing: str) -> tuple[Any, str | None]:
    if channel_id is None:
        return None, missing
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel_id):
        return None, rules.TEST_MODE_REFUSED.format(channel=channel_id)
    found = shadow_home.channel_of(bot, guild, channel_id)
    if found is None:
        return None, rules.CHANNEL_GONE.format(channel=channel_id)
    return found, None


def target_of(bot: Any, guild: Any, rehearsing: bool) -> Target:
    aimed = rules.channel_of(bot.store, guild.id)
    if rehearsing:
        home = shadow_home.channel_id(bot, guild)
        channel, why = reach(bot, guild, home, missing=rules.NO_TEST_HOME)
    else:
        channel, why = reach(bot, guild, aimed, missing=rules.NO_CHANNEL)
    return Target(channel, rehearsing, aimed, why)


async def fetch_feed(bot: Any, guild: Any) -> Any:
    handle = rules.handle_of(bot.store, guild.id)
    return await read_feed(handle, rules.FEED_LIMIT, fetch=getattr(bot, FETCH_ATTR, None))


def send_why(exc: BaseException) -> str:
    if isinstance(exc, discord.HTTPException):
        return f"{exc.status} {exc.text}".strip()
    return f"{type(exc).__name__}: {exc}"


async def send_item(
    bot: Any, guild: Any, item: rules.Item, target: Target, *, ping: bool
) -> tuple[Any, str | None]:
    role = rules.ping_role(bot.store, guild.id) if ping and not target.rehearsing else None
    content, embed = rules.message_of(
        bot.store,
        guild.id,
        item,
        rehearsal_for=target.aimed,
        rehearsing=target.rehearsing,
        role=role,
    )
    try:
        message = await target.channel.send(
            content, embed=embed, allowed_mentions=rules.post_mentions(role)
        )
    except (discord.HTTPException, AttributeError, TypeError, ValueError) as exc:
        return None, send_why(exc)
    return message, None


def item_details(item: rules.Item) -> dict[str, Any]:
    return {"uri": item.uri, "kind": item.kind, "url": item.url}


async def tick(bot: Any, guild: Any, now: datetime | None = None) -> str | None:
    """One pass for one server under its lock; what it did, or None while off or not due."""
    async with lock_of(bot, guild.id):
        return await _tick(bot, guild, moment(now))


async def _tick(bot: Any, guild: Any, now: datetime) -> str | None:
    mode = rules.mode_of(bot.store, guild.id)
    if mode == rules.OFF:
        return None
    target = target_of(bot, guild, mode == rules.SHADOW)
    if target.channel is None:
        if await store.set_error(bot.db, guild.id, target.why):
            await log_action(
                bot,
                guild,
                "bluesky.post_failed",
                details={"mode": mode, "why": target.why, "channel": target.aimed},
            )
        return "nowhere"
    row = await store.get_read(bot.db, guild.id)
    if not rules.is_due(row, rules.interval(bot.store, guild.id), now):
        return None
    done = await read_and_post(bot, guild, target, mode, now)
    return "read" if done is not None else "failed"


async def read_and_post(
    bot: Any, guild: Any, target: Target, mode: str, now: datetime
) -> dict[str, int] | None:
    """A read and every new post sent; None when the read failed (logged once per streak)."""
    found = await fetch_feed(bot, guild)
    if not found.ok:
        failures = await store.read_failed(bot.db, guild.id, now, found.why)
        if failures == 1:
            await log_action(
                bot,
                guild,
                "bluesky.read_failed",
                details={"status": found.status, "why": found.why, "failures": failures},
            )
        return None
    await store.read_ok(bot.db, guild.id, now)
    counts = await walk(bot, guild, target, mode, rules.oldest_first(found.feed), now)
    await store.prune(bot.db, guild.id, rules.keep(bot.store, guild.id))
    return counts | {"seen": len(found.feed)}


async def walk(
    bot: Any, guild: Any, target: Target, mode: str, items: list[rules.Item], now: datetime
) -> dict[str, int]:
    rows = await store.known(bot.db, guild.id, [item.uri for item in items])
    age = rules.max_age(bot.store, guild.id)
    old: list[str] = []
    unwanted: list[str] = []
    sent = new = 0
    for item in items:
        row = rows.get(item.uri)
        if row is not None and row["status"] != rules.RETRY:
            continue
        if row is None:
            new += 1
            if not rules.wanted(bot.store, guild.id, item.kind):
                if await store.record(bot.db, guild.id, item, rules.SKIPPED_KIND, now):
                    unwanted.append(item.uri)
                continue
            if rules.too_old(item, now, age):
                if await store.record(bot.db, guild.id, item, rules.SKIPPED_OLD, now):
                    old.append(item.uri)
                continue
        over = store.RECLAIMABLE_BY_LOOP if row is not None else ()
        if not await store.claim(bot.db, guild.id, item, now, over=over):
            continue
        if await post_one(bot, guild, item, target, mode, now, retried=row is not None):
            sent += 1
    if old:
        await log_action(
            bot, guild, "bluesky.skipped_old", details={"count": len(old), "uris": old}
        )
    if unwanted:
        await log_action(
            bot, guild, "bluesky.skipped_kind", details={"count": len(unwanted), "uris": unwanted}
        )
    return {"new": new, "sent": sent}


async def post_one(
    bot: Any,
    guild: Any,
    item: rules.Item,
    target: Target,
    mode: str,
    now: datetime,
    *,
    retried: bool,
) -> bool:
    message, why = await send_item(bot, guild, item, target, ping=True)
    details = item_details(item) | {"channel": int(target.channel.id), "mode": mode}
    if message is None:
        status = await store.let_go(bot.db, guild.id, item.uri, retried)
        await log_action(
            bot, guild, "bluesky.post_failed", details=details | {"why": why, "row": status}
        )
        return False
    status = rules.WOULD_POST if target.rehearsing else rules.POSTED
    await store.settle(
        bot.db, guild.id, item.uri, status, now, channel_id=target.channel.id, message_id=message.id
    )
    details["message_id"] = int(message.id)
    if target.rehearsing:
        await log_action(
            bot, guild, "bluesky.would_post", details=details | {"aimed_at": target.aimed}
        )
    else:
        await log_action(bot, guild, "bluesky.posted", details=details)
    return True


async def read_now(
    bot: Any, guild: Any, actor: Any, *, via: str = VIA_DISCORD, now: datetime | None = None
) -> Outcome:
    async with lock_of(bot, guild.id):
        when = moment(now)
        mode = rules.mode_of(bot.store, guild.id)
        if mode == rules.OFF:
            return refusal(rules.MODE_OFF, "bluesky_off", 409)
        target = target_of(bot, guild, mode == rules.SHADOW)
        if target.channel is None:
            return refusal(target.why or rules.NO_CHANNEL, "no_channel", 409)
        counts = await read_and_post(bot, guild, target, mode, when)
        if counts is None:
            row = await store.get_read(bot.db, guild.id)
            why = row["last_error"] if row is not None else "unknown"
            return refusal(rules.READ_FAILED.format(why=why), "read_failed", 502)
        await log_action(
            bot,
            guild,
            kind_via("bluesky.read_now", via),
            actor=actor,
            details={"via": via, "mode": mode} | counts,
        )
        handle = rules.handle_of(bot.store, guild.id)
        return Outcome(True, rules.READ_SAID.format(handle=handle, **counts), value=counts)


async def post_latest(
    bot: Any,
    guild: Any,
    actor: Any,
    count: Any,
    where: Any,
    *,
    via: str = VIA_DISCORD,
    now: datetime | None = None,
) -> Outcome:
    """The newest `count` mirrorable posts, oldest first; one staff press."""
    most = int(KEY_MAX[BLUESKY_SEED_COUNT])
    try:
        wanted = int(count)
    except (TypeError, ValueError):
        wanted = 0
    if not 1 <= wanted <= most:
        return refusal(rules.BAD_COUNT.format(most=most), "bad_count", 400)
    if where not in rules.WHERES:
        return refusal(rules.BAD_WHERE, "bad_where", 400)
    async with lock_of(bot, guild.id):
        return await _post_latest(bot, guild, actor, wanted, str(where), via, moment(now))


async def _post_latest(
    bot: Any, guild: Any, actor: Any, count: int, where: str, via: str, now: datetime
) -> Outcome:
    rehearsing = where == rules.TEST
    target = target_of(bot, guild, rehearsing)
    if target.channel is None:
        return refusal(target.why or rules.NO_CHANNEL, "no_channel", 409)
    found = await fetch_feed(bot, guild)
    if not found.ok:
        return refusal(rules.READ_FAILED.format(why=found.why), "read_failed", 502)
    eligible = [
        item for item in rules.items_of(found.feed) if rules.wanted(bot.store, guild.id, item.kind)
    ][:count]
    handle = rules.handle_of(bot.store, guild.id)
    if not eligible:
        return refusal(rules.NOTHING_ELIGIBLE.format(handle=handle), "nothing", 409)
    posted: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []
    why = None
    for item in reversed(eligible):
        if not rehearsing and not await store.claim(
            bot.db, guild.id, item, now, over=RECLAIM_FOR_CHANNEL
        ):
            skipped.append(item.uri)
            continue
        message, why_not = await send_item(bot, guild, item, target, ping=False)
        if message is None:
            why = why_not
            failed.append(item.uri)
            if not rehearsing:
                await store.let_go(bot.db, guild.id, item.uri, True)
            continue
        posted.append(item.uri)
        if not rehearsing:
            await store.settle(
                bot.db,
                guild.id,
                item.uri,
                rules.POSTED,
                now,
                channel_id=target.channel.id,
                message_id=message.id,
            )
    details = {
        "via": via,
        "count": count,
        "where": where,
        "channel": int(target.channel.id),
        "posted": len(posted),
        "skipped": len(skipped),
        "failed": len(failed),
        "uris": posted,
    }
    if rehearsing:
        await log_action(
            bot, guild, kind_via("bluesky.rehearsed", via), actor=actor, details=details
        )
    else:
        await log_action(
            bot, guild, kind_via("bluesky.posted_latest", via), actor=actor, details=details
        )
    if not posted and failed:
        return refusal(rules.POST_REFUSED.format(why=why), "not_posted", 502)
    said = rules.POSTED_LATEST.format(posted=len(posted), channel=int(target.channel.id))
    if skipped:
        said += rules.ALREADY_UP.format(skipped=len(skipped))
    if failed:
        said += rules.POST_FAILED_PART.format(failed=len(failed), why=why)
    return Outcome(True, said, value=details)


async def rehearse(
    bot: Any, guild: Any, actor: Any, *, via: str = VIA_DISCORD, now: datetime | None = None
) -> Outcome:
    """Post to test: Post the latest with one post, the test channel."""
    return await post_latest(bot, guild, actor, 1, rules.TEST, via=via, now=now)


async def status(bot: Any, guild: Any, now: datetime | None = None) -> dict[str, Any]:
    """What the site's section reads."""
    when = moment(now)
    mode = rules.mode_of(bot.store, guild.id)
    row = await store.get_read(bot.db, guild.id)
    upcoming = rules.next_read(row, rules.interval(bot.store, guild.id))
    rows = await store.recent(bot.db, guild.id, rules.RECENT_ROWS)
    home = shadow_home.channel_id(bot, guild)
    aimed = rules.channel_of(bot.store, guild.id)
    return {
        "mode": mode,
        "handle": rules.handle_of(bot.store, guild.id),
        "channel_id": str(aimed) if aimed else None,
        "test_home": str(home) if home else None,
        "seed_count": rules.seed_count(bot.store, guild.id),
        "last_read_at": row["last_read_at"] if row is not None else None,
        "last_ok_at": row["last_ok_at"] if row is not None else None,
        "failures": int(row["failures"] or 0) if row is not None else 0,
        "last_error": row["last_error"] if row is not None else None,
        "next_read_at": (None if mode == rules.OFF else (upcoming or when).isoformat()),
        "recent": [recent_row(guild, one) for one in rows],
    }


def recent_row(guild: Any, row: Any) -> dict[str, Any]:
    channel = row["channel_id"]
    message = row["message_id"]
    link = (
        f"https://discord.com/channels/{int(guild.id)}/{int(channel)}/{int(message)}"
        if channel and message
        else None
    )
    return {
        "uri": row["uri"],
        "kind": row["kind"],
        "status": row["status"],
        "text": str(row["text"] or "")[:80],
        "url": rules.post_url(str(row["author_handle"] or ""), str(row["uri"])),
        "channel_id": str(channel) if channel else None,
        "message_url": link,
        "seen_at": row["seen_at"],
        "posted_at": row["posted_at"],
    }
