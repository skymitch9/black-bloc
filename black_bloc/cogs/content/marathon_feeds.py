from __future__ import annotations

import json
import logging
import re
import sqlite3
from typing import Any

import discord

from ... import marathon as mt
from ... import marathon_feeds as mf
from ...actionlog import log_action
from ...command_errors import AnswersErrors, SafeDynamicItem
from ...golive import now_iso
from ...logkinds import VIA_DISCORD, kind_via
from ...marathon_sources import HORARO_SLUG, ScheduleError
from ...panels import (
    KEEP_IT,
    Outcome,
    answer,
    clamped,
    confirm,
    confirm_items,
    opened,
    refusal,
    still_staff,
)
from ...settings_store import (
    DB_UNAVAILABLE,
    MARATHON_FEED_ACTION_KEY,
    MARATHON_FEED_ADDED_TEMPLATE_KEY,
    MARATHON_FEED_HOURS_KEY,
    MARATHON_FEED_RECENT_KEY,
    MARATHON_FEED_SUGGEST_TEMPLATE_KEY,
    MARATHON_FEEDS_KEY,
)
from .marathon import (
    MODE_OFF,
    MODE_ON,
    UNREADABLE,
    MarathonPanel,
    actor_id,
    add_moves,
    cog_of,
    create_marathon,
    get_marathon,
    minutes_for,
    mode_of,
    open_root,
    remove_marathon,
    render,
    said_default,
    set_active,
    update_marathon,
)
from .spotlight import channel_by_id

log = logging.getLogger(__name__)

NO_CHANNEL_CODE = "no_channel"
CHANNEL_HAS_FEED_CODE = "channel_has_feed"
DUPLICATE_FEED_CODE = "duplicate_feed"
UNKNOWN_PICK_CODE = "unknown_source"
NO_SLUG_CODE = "no_slug"
SLUG_UNREADABLE_CODE = "slug_unreadable"
NO_SUCH_FEED_CODE = "no_such_feed"
BAD_ACTION_CODE = "bad_action"
BAD_NAME_CODE = "bad_name"
SUGGESTION_GONE_CODE = "suggestion_gone"
NOTHING_IGNORED_CODE = "nothing_ignored"
FEED_TEMPLATE = (
    r"marathon:feed:(?P<feed_id>[0-9]+):(?P<ref>[A-Za-z0-9_./-]{1,60}):"
    r"(?P<action>pause|remove|add|dismiss)"
)
REF_LIMIT = 60
PAUSE = "pause"
REMOVE = "remove"
TAKE = "add"
DISMISS = "dismiss"
FEEDS_VIEW = "feeds"
FEED_VIEW = "feed"
SUGGESTION_VIEW = "suggestion"
CHANNEL_VIEW = "feed_channel"
FEED_VIEWS = (FEEDS_VIEW, FEED_VIEW, SUGGESTION_VIEW, CHANNEL_VIEW)
SELECT_CAP = 25
MARATHONS_SHOWN = 10
FEED_COLUMNS = {
    "name",
    "spotlight_id",
    "action",
    "active",
    "last_checked_at",
    "last_ok",
    "last_error",
    "checks_failed",
    "suggested",
    "ignored",
}


def _cell(row: Any, key: str, fallback: Any = None) -> Any:
    if row is None:
        return fallback
    try:
        return row[key]
    except (IndexError, KeyError):
        return fallback


# --- the tables -------------------------------------------------------------------------------


async def list_feeds(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM marathon_feeds WHERE guild_id = ? ORDER BY id", (int(guild_id),)
    )
    return list(await cur.fetchall())


async def get_feed(db: Any, guild_id: int, feed_id: Any) -> Any:
    try:
        wanted = int(feed_id)
    except (TypeError, ValueError):
        return None
    cur = await db.conn.execute(
        "SELECT * FROM marathon_feeds WHERE id = ? AND guild_id = ?", (wanted, int(guild_id))
    )
    return await cur.fetchone()


async def feed_by_channel(db: Any, guild_id: int, spotlight_id: Any) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM marathon_feeds WHERE guild_id = ? AND spotlight_id = ?",
        (int(guild_id), int(spotlight_id)),
    )
    return await cur.fetchone()


async def insert_feed(
    db: Any,
    guild_id: int,
    *,
    source: str,
    feed_ref: str,
    spotlight_id: int,
    name: str,
    action: str,
    added_by: int | None,
) -> int:
    cur = await db.conn.execute(
        "INSERT INTO marathon_feeds(guild_id, source, feed_ref, spotlight_id, name, action, "
        "added_by, added_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (int(guild_id), source, feed_ref, int(spotlight_id), name, action, added_by, now_iso()),
    )
    await db.conn.commit()
    return int(cur.lastrowid)


async def update_feed(db: Any, feed_id: int, **fields: Any) -> None:
    wanted = {key: value for key, value in fields.items() if key in FEED_COLUMNS}
    if not wanted:
        return
    sets = ", ".join(f"{key} = ?" for key in wanted)
    await db.conn.execute(
        f"UPDATE marathon_feeds SET {sets} WHERE id = ?", (*wanted.values(), int(feed_id))
    )
    await db.conn.commit()


async def delete_feed(db: Any, feed_id: int) -> None:
    await db.conn.execute("UPDATE marathons SET feed_id = NULL WHERE feed_id = ?", (int(feed_id),))
    await db.conn.execute("DELETE FROM marathon_feeds WHERE id = ?", (int(feed_id),))
    await db.conn.commit()


async def marathons_of_feed(db: Any, feed_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM marathons WHERE feed_id = ? ORDER BY COALESCE(starts_at, '9999'), id",
        (int(feed_id),),
    )
    return list(await cur.fetchall())


async def marathons_by_ref(db: Any, guild_id: int, source: str) -> dict[str, Any]:
    cur = await db.conn.execute(
        "SELECT * FROM marathons WHERE guild_id = ? AND source = ? ORDER BY id",
        (int(guild_id), source),
    )
    found: dict[str, Any] = {}
    for row in await cur.fetchall():
        found.setdefault(str(row["source_ref"]), row)
    return found


async def is_seeded(db: Any, guild_id: int, login: str) -> bool:
    cur = await db.conn.execute(
        "SELECT 1 FROM marathon_feed_seeds WHERE guild_id = ? AND twitch_login = ?",
        (int(guild_id), login),
    )
    return await cur.fetchone() is not None


async def mark_seeded(db: Any, guild_id: int, login: str) -> None:
    await db.conn.execute(
        "INSERT OR IGNORE INTO marathon_feed_seeds(guild_id, twitch_login, seeded_at) "
        "VALUES (?, ?, ?)",
        (int(guild_id), login, now_iso()),
    )
    await db.conn.commit()


async def channel_rows(db: Any, guild_id: int) -> list[Any]:
    """The channel-only rows: a watched channel nobody here has linked as their own."""
    cur = await db.conn.execute(
        "SELECT * FROM spotlight_channels WHERE guild_id = ? AND lower(twitch_login) NOT IN "
        "(SELECT lower(twitch_login) FROM golive_links) "
        "ORDER BY lower(COALESCE(display_name, twitch_login)), id",
        (int(guild_id),),
    )
    return list(await cur.fetchall())


async def channel_by_login_in(db: Any, guild_id: int, login: str) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM spotlight_channels WHERE guild_id = ? AND lower(twitch_login) = ?",
        (int(guild_id), login.lower()),
    )
    return await cur.fetchone()


def channel_word(row: Any) -> str:
    if row is None:
        return mf.CHANNEL_GONE
    return str(_cell(row, "display_name") or _cell(row, "twitch_login") or "?")


async def channel_of(db: Any, feed: Any) -> Any:
    return await channel_by_id(db, int(feed["spotlight_id"]))


# --- small reads ------------------------------------------------------------------------------


def hours_of(bot: Any, guild_id: int) -> int:
    return int(bot.store.get(guild_id, MARATHON_FEED_HOURS_KEY))


def words(bot: Any, guild: Any, key: str, fields: dict[str, Any]) -> str:
    return mt.render(bot.store.get(guild.id, key), said_default(key), **fields).text


def feed_details(feed: Any, via: str, **extra: Any) -> dict[str, Any]:
    return {
        "feed_id": feed["id"],
        "feed": feed["name"],
        "source": mf.marathon_source(feed),
        "spotlight_id": feed["spotlight_id"],
        "automatic": via == mf.VIA_FEED,
        "via": via,
    } | extra


def notice_custom_id(feed_id: Any, ref: Any, action: str) -> str:
    return f"marathon:feed:{int(feed_id)}:{ref}:{action}"


def buttonable(ref: Any) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_./-]{1,60}", str(ref or "")))


# --- the check --------------------------------------------------------------------------------


async def candidates_of(bot: Any, guild: Any, feed: Any, now: Any) -> list[mf.Candidate]:
    cog = cog_of(bot)
    recent = int(bot.store.get(guild.id, MARATHON_FEED_RECENT_KEY))
    source = mf.marathon_source(feed)
    if feed["source"] == mf.HORARO_FEED:
        rows = await cog.client.horaro_schedules(str(feed["feed_ref"]))
        return mf.horaro_candidates(str(feed["feed_ref"]), feed["name"], rows, now, recent)
    if source is None:
        raise ScheduleError(mf.UNKNOWN_PICK.format(given=str(feed["feed_ref"])[:60]))
    return mf.tracker_candidates(source, await cog.client.events(source), now, recent)


async def check_failed(
    bot: Any, guild: Any, feed: Any, exc: Exception, now: Any, *, actor: Any, via: str
) -> Outcome:
    why = str(exc)[:300] if isinstance(exc, ScheduleError) else type(exc).__name__
    failures = int(feed["checks_failed"] or 0) + 1
    await update_feed(
        bot.db,
        feed["id"],
        last_checked_at=now.isoformat(),
        last_ok=0,
        last_error=why,
        checks_failed=failures,
    )
    details = feed_details(feed, via, reason=why, failures=failures)
    await log_action(
        bot, guild, kind_via("marathon.feed_failed", via), actor=actor, details=details
    )
    if failures == mf.FAILURES_IMPORTANT:
        await log_action(bot, guild, "marathon.feed_stale", details=details)
    return refusal(mf.FEED_CHECK_FAILED.format(name=feed["name"], why=why), UNREADABLE, 502)


async def run_check(
    bot: Any, guild: Any, feed: Any, *, actor: Any = None, via: str = VIA_DISCORD
) -> Outcome:
    """One read of the feed's list; every new event is added or suggested, never twice.
    Called with the feed's lock held."""
    cog = cog_of(bot)
    now = cog.clock()
    try:
        candidates = await candidates_of(bot, guild, feed, now)
    except Exception as exc:
        return await check_failed(bot, guild, feed, exc, now, actor=actor, via=via)
    source = mf.marathon_source(feed)
    known = await marathons_by_ref(bot.db, guild.id, source)
    adopted = 0
    for candidate in candidates:
        row = known.get(candidate.ref)
        if row is not None and row["feed_id"] is None:
            await update_marathon(bot.db, row["id"], feed_id=int(feed["id"]))
            adopted += 1
    records = mf.suggested_of(feed)
    new = mf.fresh(
        candidates,
        known=set(known),
        ignored=mf.ignored_of(feed),
        seen=[str(one.get("ref")) for one in records],
    )
    added = suggested = 0
    for candidate in new:
        if feed["action"] == mf.SUGGEST:
            records.append(await suggest(bot, guild, feed, candidate, now))
            await update_feed(bot.db, feed["id"], suggested=json.dumps(records))
            suggested += 1
        elif await add_candidate(bot, guild, feed, candidate):
            added += 1
    await update_feed(
        bot.db,
        feed["id"],
        last_checked_at=now.isoformat(),
        last_ok=1,
        last_error=None,
        checks_failed=0,
    )
    await log_action(
        bot,
        guild,
        kind_via("marathon.feed_checked", via),
        actor=actor,
        details=feed_details(
            feed,
            via,
            found=len(candidates),
            new=len(new),
            added=added,
            suggested=suggested,
            adopted=adopted,
        ),
    )
    said = mf.FEED_CHECKED.format(
        name=feed["name"], found=len(candidates), added=added, suggested=suggested
    )
    return Outcome(True, said, value={"found": len(candidates), "added": added})


async def add_candidate(bot: Any, guild: Any, feed: Any, candidate: mf.Candidate) -> bool:
    """`add` mode: the marathon exactly as a staff Add makes it, then ONE staff notice."""
    made = await create_marathon(
        bot,
        guild,
        None,
        name=candidate.name,
        url=candidate.url,
        spotlight_id=feed["spotlight_id"],
        via=mf.VIA_FEED,
        feed_id=int(feed["id"]),
    )
    details = feed_details(feed, mf.VIA_FEED, event=candidate.ref, name=candidate.name)
    if not made.ok:
        await log_action(
            bot, guild, "marathon.feed_add_failed", details=details | {"reason": made.message}
        )
        return False
    marathon = made.value
    shadow = mode_of(bot, guild.id) != MODE_ON
    await log_action(
        bot,
        guild,
        "marathon.would_feed_add" if shadow else "marathon.feed_added",
        details=details | {"marathon_id": marathon["id"], "starts_at": candidate.starts_at},
    )
    record = {"ref": candidate.ref, "name": candidate.name, "starts_at": candidate.starts_at}
    record["url"] = candidate.url
    text = words(bot, guild, MARATHON_FEED_ADDED_TEMPLATE_KEY, await fields_of(bot, feed, record))
    ref = str(marathon["id"])
    view = notice_view(feed["id"], ref, (PAUSE, REMOVE))
    await post_notice(bot, guild, feed, text, view, details | {"marathon_id": marathon["id"]})
    return True


async def suggest(
    bot: Any, guild: Any, feed: Any, candidate: mf.Candidate, now: Any
) -> dict[str, Any]:
    """`suggest` mode: the record first, then the log row, then the notice (checklist 12)."""
    record = mf.suggestion_record(candidate, now)
    shadow = mode_of(bot, guild.id) != MODE_ON
    details = feed_details(
        feed,
        mf.VIA_FEED,
        event=candidate.ref,
        name=candidate.name,
        starts_at=candidate.starts_at,
    )
    await log_action(
        bot,
        guild,
        "marathon.would_feed_suggest" if shadow else "marathon.feed_suggested",
        details=details,
    )
    text = words(bot, guild, MARATHON_FEED_SUGGEST_TEMPLATE_KEY, await fields_of(bot, feed, record))
    view = notice_view(feed["id"], candidate.ref, (TAKE, DISMISS))
    message, channel_id = await post_notice(bot, guild, feed, text, view, details)
    if message is not None:
        record |= {"notice_channel_id": channel_id, "notice_message_id": int(message.id)}
    return record


async def fields_of(bot: Any, feed: Any, record: Any) -> dict[str, Any]:
    return mf.notice_fields(feed, record, channel_word(await channel_of(bot.db, feed)))


async def post_notice(
    bot: Any, guild: Any, feed: Any, text: str, view: Any, details: dict[str, Any]
) -> tuple[Any, int | None]:
    if mode_of(bot, guild.id) == MODE_OFF:
        return (None, None)
    message, channel_id, why = await cog_of(bot)._send_staff(guild, text, view)
    if message is None:
        await log_action(
            bot, guild, "marathon.feed_notice_failed", details=details | {"reason": why}
        )
    return (message, channel_id)


async def fold_notice(bot: Any, guild: Any, record: Any, line: str, *, struck: bool) -> None:
    """Cosmetic, last: the notice keeps its words, gains the outcome, loses its buttons."""
    if not isinstance(record, dict) or not record.get("notice_message_id"):
        return
    message = await cog_of(bot)._fetch(
        guild, record.get("notice_channel_id"), record.get("notice_message_id")
    )
    if message is None:
        return
    await fold_message(message, line, struck=struck)


async def fold_message(message: Any, line: str, *, struck: bool) -> None:
    body = str(getattr(message, "content", "") or "")
    if struck and body and not body.startswith("~~"):
        body = f"~~{body}~~"
    try:
        await message.edit(
            content=f"{body}\n{line}" if body else line,
            view=None,
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except Exception as exc:
        log.warning("marathon: could not fold a feed notice — %s", type(exc).__name__)


# --- the tick and the seed --------------------------------------------------------------------


async def tick_feeds(cog: Any, guild: Any) -> None:
    bot = cog.bot
    if not bot.store.get(guild.id, MARATHON_FEEDS_KEY):
        return
    if int(guild.id) not in cog.feeds_seeded:
        cog.feeds_seeded.add(int(guild.id))
        await seed_feeds(bot, guild)
    hours = hours_of(bot, guild.id)
    for row in await list_feeds(bot.db, guild.id):
        try:
            async with cog.feed_lock(row["id"]):
                fresh = await get_feed(bot.db, guild.id, row["id"])
                if fresh is not None and mf.check_due(fresh, cog.clock(), hours):
                    await run_check(bot, guild, fresh, via=mf.VIA_FEED)
        except Exception:
            log.exception("marathon: the check of feed %s failed", row["id"])


async def seed_feeds(bot: Any, guild: Any) -> list[str]:
    """Once per channel, ever: a seeded feed staff remove stays removed."""
    made: list[str] = []
    action = str(bot.store.get(guild.id, MARATHON_FEED_ACTION_KEY))
    for seed in mf.SEEDS:
        if await is_seeded(bot.db, guild.id, seed.login):
            continue
        channel = await channel_by_login_in(bot.db, guild.id, seed.login)
        if channel is None:
            continue
        if await feed_by_channel(bot.db, guild.id, channel["id"]) is None:
            try:
                await insert_feed(
                    bot.db,
                    guild.id,
                    source=seed.source,
                    feed_ref=seed.feed_ref,
                    spotlight_id=int(channel["id"]),
                    name=seed.name,
                    action=action if action in mf.ACTIONS else mf.ADD,
                    added_by=None,
                )
                made.append(seed.name)
            except sqlite3.IntegrityError:
                log.info("marathon: %s already has a feed; not seeding it", seed.login)
        await mark_seeded(bot.db, guild.id, seed.login)
    if made:
        await log_action(
            bot, guild, "marathon.feed_seeded", details={"feeds": made, "action": action}
        )
    return made


# --- the shared moves: the routes and the panel both come in by these -------------------------


async def create_feed(
    bot: Any,
    guild: Any,
    actor: Any,
    *,
    spotlight_id: Any,
    pick: Any,
    slug: Any = None,
    name: Any = None,
    action: Any = None,
    via: str = VIA_DISCORD,
) -> Outcome:
    channel = None
    if spotlight_id not in (None, "", 0, "0"):
        try:
            channel = await channel_by_id(bot.db, int(spotlight_id))
        except (TypeError, ValueError):
            channel = None
    if channel is None or int(channel["guild_id"]) != int(guild.id):
        return refusal(mf.NO_CHANNEL, NO_CHANNEL_CODE, 404)
    existing = await feed_by_channel(bot.db, guild.id, channel["id"])
    if existing is not None:
        return refusal(
            mf.CHANNEL_HAS_FEED.format(channel=channel_word(channel), name=existing["name"]),
            CHANNEL_HAS_FEED_CODE,
            409,
        )
    picked = mf.pick_of(pick)
    if picked is None:
        return refusal(mf.UNKNOWN_PICK.format(given=str(pick or "")[:40]), UNKNOWN_PICK_CODE, 422)
    source, feed_ref = picked
    if source == mf.HORARO_FEED:
        feed_ref = str(slug or "").strip().lower().strip("/")
        if not HORARO_SLUG.match(feed_ref):
            return refusal(mf.NO_SLUG, NO_SLUG_CODE, 422)
        try:
            await cog_of(bot).client.horaro_schedules(feed_ref)
        except ScheduleError as exc:
            return refusal(
                mf.SLUG_UNREADABLE.format(slug=feed_ref[:60], why=str(exc)[:200]),
                SLUG_UNREADABLE_CODE,
                422,
            )
    wanted_action = str(action or bot.store.get(guild.id, MARATHON_FEED_ACTION_KEY))
    if wanted_action not in mf.ACTIONS:
        return refusal(mf.BAD_ACTION, BAD_ACTION_CODE, 422)
    wanted_name = (
        mf.clean_name(name)
        or mf.PICK_NAMES.get(str(pick).strip().lower())
        or mf.clean_name(channel_word(channel))
    )
    try:
        feed_id = await insert_feed(
            bot.db,
            guild.id,
            source=source,
            feed_ref=str(feed_ref),
            spotlight_id=int(channel["id"]),
            name=wanted_name,
            action=wanted_action,
            added_by=actor_id(actor),
        )
    except sqlite3.IntegrityError:
        return refusal(mf.SAME_FEED.format(name=wanted_name), DUPLICATE_FEED_CODE, 409)
    feed = await get_feed(bot.db, guild.id, feed_id)
    await log_action(
        bot,
        guild,
        kind_via("marathon.feed_created", via),
        actor=actor,
        details=feed_details(feed, via, action=wanted_action, feed_ref=feed["feed_ref"]),
    )
    async with cog_of(bot).feed_lock(feed_id):
        checked = await run_check(bot, guild, feed, actor=actor, via=via)
    said = mf.FEED_ADDED.format(
        name=wanted_name,
        source=mf.source_word(feed),
        channel=channel_word(channel),
        action=mf.ACTION_WORDS[wanted_action],
        checked=checked.message,
    )
    return Outcome(True, said, value=await get_feed(bot.db, guild.id, feed_id))


async def remove_feed(
    bot: Any,
    guild: Any,
    actor: Any,
    feed: Any,
    *,
    because: str = mf.BECAUSE_STAFF,
    via: str = VIA_DISCORD,
) -> Outcome:
    async with cog_of(bot).feed_lock(feed["id"]):
        made = len(await marathons_of_feed(bot.db, feed["id"]))
        await delete_feed(bot.db, feed["id"])
    await log_action(
        bot,
        guild,
        kind_via("marathon.feed_removed", via),
        actor=actor,
        details=feed_details(feed, via, because=because, marathons=made),
    )
    return Outcome(True, mf.FEED_REMOVED.format(name=feed["name"]))


async def drop_feeds_of_channel(bot: Any, guild: Any, spotlight_id: Any, actor: Any = None) -> int:
    """A channel row that goes takes its feed with it; the marathons stay, as history."""
    if not getattr(getattr(bot, "db", None), "is_connected", False) or cog_of(bot) is None:
        return 0
    feed = await feed_by_channel(bot.db, guild.id, spotlight_id)
    if feed is None:
        return 0
    await remove_feed(bot, guild, actor, feed, because=mf.BECAUSE_CHANNEL)
    return 1


async def set_feed(
    bot: Any,
    guild: Any,
    actor: Any,
    feed: Any,
    *,
    active: Any = None,
    action: Any = None,
    name: Any = None,
    spotlight_id: Any = None,
    via: str = VIA_DISCORD,
) -> Outcome:
    """PATCH in words: each field given is one change and one log row."""
    said: list[str] = []
    async with cog_of(bot).feed_lock(feed["id"]):
        fresh = await get_feed(bot.db, guild.id, feed["id"])
        if fresh is None:
            return refusal(mf.NO_SUCH_FEED.format(given=feed["id"]), NO_SUCH_FEED_CODE, 404)
        if action is not None and action != fresh["action"]:
            if action not in mf.ACTIONS:
                return refusal(mf.BAD_ACTION, BAD_ACTION_CODE, 422)
            await update_feed(bot.db, fresh["id"], action=action)
            await log_action(
                bot,
                guild,
                kind_via("marathon.feed_changed", via),
                actor=actor,
                details=feed_details(fresh, via, action=action),
            )
            said.append(
                mf.FEED_ACTION_SET.format(name=fresh["name"], action=mf.ACTION_WORDS[action])
            )
        if name is not None:
            wanted = mf.clean_name(name)
            if not wanted:
                return refusal(mf.BAD_NAME, BAD_NAME_CODE, 422)
            if wanted != fresh["name"]:
                await update_feed(bot.db, fresh["id"], name=wanted)
                await log_action(
                    bot,
                    guild,
                    kind_via("marathon.feed_changed", via),
                    actor=actor,
                    details=feed_details(fresh, via, renamed=wanted),
                )
                said.append(mf.FEED_RENAMED.format(name=wanted))
        if spotlight_id is not None and int(spotlight_id) != int(fresh["spotlight_id"]):
            channel = await channel_by_id(bot.db, int(spotlight_id))
            if channel is None or int(channel["guild_id"]) != int(guild.id):
                return refusal(mf.NO_CHANNEL, NO_CHANNEL_CODE, 404)
            other = await feed_by_channel(bot.db, guild.id, channel["id"])
            if other is not None:
                return refusal(
                    mf.CHANNEL_HAS_FEED.format(channel=channel_word(channel), name=other["name"]),
                    CHANNEL_HAS_FEED_CODE,
                    409,
                )
            await update_feed(bot.db, fresh["id"], spotlight_id=int(channel["id"]))
            await log_action(
                bot,
                guild,
                kind_via("marathon.feed_changed", via),
                actor=actor,
                details=feed_details(fresh, via, moved_to=int(channel["id"])),
            )
            said.append(mf.FEED_MOVED.format(name=fresh["name"], channel=channel_word(channel)))
        if active is not None and bool(active) != bool(fresh["active"]):
            await update_feed(bot.db, fresh["id"], active=1 if active else 0)
            await log_action(
                bot,
                guild,
                kind_via("marathon.feed_resumed" if active else "marathon.feed_paused", via),
                actor=actor,
                details=feed_details(fresh, via),
            )
            said.append((mf.FEED_RESUMED if active else mf.FEED_PAUSED).format(name=fresh["name"]))
    return Outcome(True, " ".join(said), value=await get_feed(bot.db, guild.id, feed["id"]))


async def check_now(
    bot: Any, guild: Any, actor: Any, feed: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    async with cog_of(bot).feed_lock(feed["id"]):
        fresh = await get_feed(bot.db, guild.id, feed["id"])
        if fresh is None:
            return refusal(mf.NO_SUCH_FEED.format(given=feed["id"]), NO_SUCH_FEED_CODE, 404)
        return await run_check(bot, guild, fresh, actor=actor, via=via)


async def look_again(
    bot: Any, guild: Any, actor: Any, feed: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Dismissals are forgotten, then the feed checks at once."""
    async with cog_of(bot).feed_lock(feed["id"]):
        fresh = await get_feed(bot.db, guild.id, feed["id"])
        if fresh is None:
            return refusal(mf.NO_SUCH_FEED.format(given=feed["id"]), NO_SUCH_FEED_CODE, 404)
        dropped = mf.dismissed_of(fresh)
        await update_feed(bot.db, fresh["id"], suggested=json.dumps(mf.open_suggestions(fresh)))
        await log_action(
            bot,
            guild,
            kind_via("marathon.feed_looked", via),
            actor=actor,
            details=feed_details(fresh, via, forgot=[one.get("ref") for one in dropped]),
        )
        checked = await run_check(
            bot, guild, await get_feed(bot.db, guild.id, fresh["id"]), actor=actor, via=via
        )
    said = mf.FEED_LOOKED.format(name=fresh["name"], count=len(dropped))
    return Outcome(checked.ok, f"{said} {checked.message}", checked.code, checked.status)


async def forget_ignored(
    bot: Any, guild: Any, actor: Any, feed: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    async with cog_of(bot).feed_lock(feed["id"]):
        fresh = await get_feed(bot.db, guild.id, feed["id"])
        if fresh is None:
            return refusal(mf.NO_SUCH_FEED.format(given=feed["id"]), NO_SUCH_FEED_CODE, 404)
        ignored = mf.ignored_of(fresh)
        if not ignored:
            return refusal(
                mf.FEED_NOTHING_TO_FORGET.format(name=fresh["name"]), NOTHING_IGNORED_CODE, 409
            )
        await update_feed(bot.db, fresh["id"], ignored="[]")
        await log_action(
            bot,
            guild,
            kind_via("marathon.feed_forgot", via),
            actor=actor,
            details=feed_details(fresh, via, forgot=ignored),
        )
    return Outcome(True, mf.FEED_FORGOT.format(name=fresh["name"], count=len(ignored)))


async def open_record(bot: Any, guild: Any, feed: Any, ref: Any) -> Any:
    fresh = await get_feed(bot.db, guild.id, feed["id"])
    if fresh is None:
        return refusal(mf.NO_SUCH_FEED.format(given=feed["id"]), NO_SUCH_FEED_CODE, 404)
    wanted = str(ref or "")
    for record in mf.open_suggestions(fresh):
        if str(record.get("ref")) == wanted:
            return (fresh, record)
    return refusal(
        mf.SUGGESTION_GONE.format(event=wanted[:60], name=fresh["name"]),
        SUGGESTION_GONE_CODE,
        409,
    )


async def take_suggestion(
    bot: Any, guild: Any, actor: Any, feed: Any, ref: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Add it: the event becomes a marathon on the feed's channel; the record goes."""
    async with cog_of(bot).feed_lock(feed["id"]):
        found = await open_record(bot, guild, feed, ref)
        if isinstance(found, Outcome):
            return found
        fresh, record = found
        known = await marathons_by_ref(bot.db, guild.id, mf.marathon_source(fresh))
        existing = known.get(str(record["ref"]))
        if existing is not None:
            added, said = existing, mf.SUGGESTION_ALREADY.format(
                event=record["name"], marathon=existing["name"]
            )
        else:
            made = await create_marathon(
                bot,
                guild,
                actor,
                name=record["name"],
                url=record["url"],
                spotlight_id=fresh["spotlight_id"],
                via=via,
                feed_id=int(fresh["id"]),
            )
            if not made.ok:
                return made
            added, said = made.value, made.message
        left = [one for one in mf.suggested_of(fresh) if str(one.get("ref")) != str(record["ref"])]
        await update_feed(bot.db, fresh["id"], suggested=json.dumps(left))
        await log_action(
            bot,
            guild,
            kind_via("marathon.feed_taken", via),
            actor=actor,
            details=feed_details(
                fresh,
                via,
                event=record["ref"],
                name=record["name"],
                marathon_id=int(added["id"]),
                created=existing is None,
            ),
        )
    await fold_notice(bot, guild, record, mf.NOTICE_ADDED.format(who=who_of(actor)), struck=False)
    return Outcome(True, said, value=added)


async def dismiss_suggestion(
    bot: Any, guild: Any, actor: Any, feed: Any, ref: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    async with cog_of(bot).feed_lock(feed["id"]):
        found = await open_record(bot, guild, feed, ref)
        if isinstance(found, Outcome):
            return found
        fresh, record = found
        stamped = cog_of(bot).clock().isoformat()
        kept = [
            one | {"dismissed_at": stamped, "dismissed_by": actor_id(actor)}
            if str(one.get("ref")) == str(record["ref"])
            else one
            for one in mf.suggested_of(fresh)
        ]
        await update_feed(bot.db, fresh["id"], suggested=json.dumps(kept))
        await log_action(
            bot,
            guild,
            kind_via("marathon.feed_dismissed", via),
            actor=actor,
            details=feed_details(fresh, via, event=record["ref"], name=record["name"]),
        )
    line = mf.NOTICE_DISMISSED.format(who=who_of(actor))
    await fold_notice(bot, guild, record, line, struck=True)
    return Outcome(True, mf.SUGGESTION_DISMISSED.format(event=record["name"], name=fresh["name"]))


async def ignore_removed(
    bot: Any, guild: Any, actor: Any, marathon: Any, *, via: str = VIA_DISCORD
) -> None:
    """Remove on a marathon a feed made: the feed remembers the ref and never adds it again."""
    feed_id = _cell(marathon, "feed_id")
    if not feed_id:
        return
    ref = str(marathon["source_ref"])
    cur = await bot.db.conn.execute(
        "UPDATE marathon_feeds SET ignored = json_insert(COALESCE(NULLIF(ignored, ''), '[]'), "
        "'$[#]', ?) WHERE id = ? AND NOT EXISTS (SELECT 1 FROM json_each(COALESCE(NULLIF("
        "marathon_feeds.ignored, ''), '[]')) WHERE value = ?)",
        (ref, int(feed_id), ref),
    )
    await bot.db.conn.commit()
    if not cur.rowcount:
        return
    feed = await get_feed(bot.db, guild.id, feed_id)
    if feed is None:
        return
    await log_action(
        bot,
        guild,
        kind_via("marathon.feed_ignored", via),
        actor=actor,
        details=feed_details(feed, via, event=ref, marathon_id=marathon["id"]),
    )


def who_of(actor: Any) -> str:
    found = actor_id(actor)
    return f"<@{found}>" if found else "staff"


# --- the staff notice's buttons (KI-20: they outlive a restart) --------------------------------


class FeedButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=FEED_TEMPLATE
):
    LABELS = {
        PAUSE: ("Pause it", discord.ButtonStyle.secondary),
        REMOVE: ("Remove it", discord.ButtonStyle.danger),
        TAKE: ("Add it", discord.ButtonStyle.primary),
        DISMISS: ("Not this one", discord.ButtonStyle.secondary),
    }

    def __init__(self, feed_id: int, ref: str, action: str, *, disabled: bool = False) -> None:
        self.feed_id = int(feed_id)
        self.ref = str(ref)
        self.action = action
        label, style = self.LABELS[action]
        super().__init__(
            discord.ui.Button(
                label=label,
                style=style,
                custom_id=notice_custom_id(feed_id, ref, action),
                disabled=disabled,
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["feed_id"]), match["ref"], match["action"])

    async def on_click(self, interaction: discord.Interaction) -> None:
        bot = interaction.client
        guard = getattr(bot, "guard", None)
        if guard is not None and not guard.allows_channel(interaction.channel_id):
            await answer(interaction, guard.refusal_message())
            return
        if not await still_staff(interaction):
            return
        if not bot.db.is_connected:
            await answer(interaction, DB_UNAVAILABLE)
            return
        await interaction.response.defer(ephemeral=True)
        guild, user = interaction.guild, interaction.user
        if self.action in (PAUSE, REMOVE):
            marathon = await get_marathon(bot.db, guild.id, self.ref)
            if marathon is None:
                await fold_message(interaction.message, mf.NOTICE_GONE, struck=True)
                await answer(interaction, mf.NOTICE_GONE)
                return
            if self.action == PAUSE:
                outcome = await set_active(bot, guild, user, marathon, False)
                line = mf.NOTICE_PAUSED.format(who=who_of(user))
            else:
                outcome = await remove_marathon(bot, guild, user, marathon)
                line = mf.NOTICE_REMOVED.format(who=who_of(user))
            if outcome.ok:
                await fold_message(interaction.message, line, struck=self.action == REMOVE)
            await answer(interaction, outcome.message)
            return
        feed = await get_feed(bot.db, guild.id, self.feed_id)
        if feed is None:
            await answer(interaction, mf.NO_SUCH_FEED.format(given=self.feed_id))
            return
        doing = take_suggestion if self.action == TAKE else dismiss_suggestion
        outcome = await doing(bot, guild, user, feed, self.ref)
        await answer(interaction, outcome.message)


def notice_view(feed_id: Any, ref: Any, actions: tuple[str, ...]) -> Any:
    """No buttons for a ref too long for a custom id; the page and the panel still reach it."""
    if not buttonable(ref):
        return None
    view = discord.ui.View(timeout=None)
    for action in actions:
        view.add_item(FeedButton(int(feed_id), str(ref), action))
    return view


# --- /event ▸ Marathons… ▸ Feeds… --------------------------------------------------------------


async def feeds_card(bot: Any, guild: Any) -> tuple[Any, Any]:
    feeds = await list_feeds(bot.db, guild.id)
    hours = hours_of(bot, guild.id)
    lines: list[str] = []
    if not bot.store.get(guild.id, MARATHON_FEEDS_KEY):
        lines.append(mf.FEED_OFF)
    for feed in feeds[:SELECT_CAP]:
        channel = await channel_of(bot.db, feed)
        lines.append(mf.feed_line(feed, channel_word(channel), hours))
        waiting = mf.open_suggestions(feed)
        if waiting:
            lines.append(f"  {mf.WAITING_HEAD} " + ", ".join(one["name"] for one in waiting))
    if not feeds:
        lines.append(mf.NO_FEEDS)
    embed = discord.Embed(title=mf.FEEDS_TITLE, description=clamped(lines))
    view = MarathonPanel(minutes_for(bot, guild.id), FEEDS_VIEW)
    if feeds:
        view.add_item(FeedPick(feeds))
    open_channels = await free_channels(bot, guild)
    add_moves(view, ((mf.FEED_ADD_MOVE,) if open_channels else ()) + (mf.FEED_BACK_MOVE,))
    return (embed, view)


async def free_channels(bot: Any, guild: Any) -> list[Any]:
    taken = {int(one["spotlight_id"]) for one in await list_feeds(bot.db, guild.id)}
    return [row for row in await channel_rows(bot.db, guild.id) if int(row["id"]) not in taken]


async def feed_card(bot: Any, guild: Any, feed_id: Any) -> tuple[Any, Any]:
    feed = await get_feed(bot.db, guild.id, feed_id)
    if feed is None:
        return (None, None)
    channel = await channel_of(bot.db, feed)
    lines = [mf.feed_line(feed, channel_word(channel), hours_of(bot, guild.id))]
    ignored = mf.ignored_of(feed)
    if ignored:
        lines.append(mf.IGNORED_LINE.format(count=len(ignored)))
    waiting = mf.open_suggestions(feed)
    if waiting:
        lines += ["", mf.WAITING_HEAD] + [mf.suggestion_line(one) for one in waiting]
    made = await marathons_of_feed(bot.db, feed["id"])
    if made:
        lines += [""] + [f"· {one['name']}" for one in made[:MARATHONS_SHOWN]]
    embed = discord.Embed(title=feed["name"], description=clamped(lines))
    view = MarathonPanel(minutes_for(bot, guild.id), FEED_VIEW)
    view.feed_id = int(feed["id"])
    if waiting:
        view.add_item(SuggestionPick(waiting))
    add_moves(view, mf.feed_moves(feed))
    return (embed, view)


async def suggestion_card(bot: Any, guild: Any, feed_id: Any, ref: Any) -> tuple[Any, Any]:
    feed = await get_feed(bot.db, guild.id, feed_id)
    record = next(
        (one for one in mf.open_suggestions(feed) if str(one.get("ref")) == str(ref)), None
    ) if feed is not None else None
    if record is None:
        return (None, None)
    lines = [mf.suggestion_line(record), record.get("url") or ""]
    embed = discord.Embed(title=feed["name"], description=clamped([one for one in lines if one]))
    view = MarathonPanel(minutes_for(bot, guild.id), SUGGESTION_VIEW)
    view.feed_id = int(feed["id"])
    view.ref = str(record["ref"])
    add_moves(view, mf.suggestion_moves())
    return (embed, view)


async def channel_card(bot: Any, guild: Any) -> tuple[Any, Any]:
    rows = await free_channels(bot, guild)
    embed = discord.Embed(
        title=mf.ADD_FEED_TITLE, description=mf.NO_CHANNEL if rows else mf.NO_CHANNELS
    )
    view = MarathonPanel(minutes_for(bot, guild.id), CHANNEL_VIEW)
    if rows:
        view.add_item(ChannelPick(rows))
    add_moves(view, (mf.FEED_BACK_MOVE,))
    return (embed, view)


async def show(interaction: discord.Interaction, embed: Any, view: Any, previous: Any) -> None:
    await render(interaction, embed, view, previous)


async def open_feeds(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    embed, view = await feeds_card(interaction.client, interaction.guild)
    await show(interaction, embed, view, previous)


async def open_feed(interaction: discord.Interaction, feed_id: Any, previous: Any) -> None:
    if not await opened(interaction):
        return
    embed, view = await feed_card(interaction.client, interaction.guild, feed_id)
    if view is None:
        await open_feeds(interaction, previous)
        await answer(interaction, mf.NO_SUCH_FEED.format(given=str(feed_id)[:40]))
        return
    await show(interaction, embed, view, previous)


async def open_suggestion(
    interaction: discord.Interaction, feed_id: Any, ref: Any, previous: Any
) -> None:
    if not await opened(interaction):
        return
    embed, view = await suggestion_card(interaction.client, interaction.guild, feed_id, ref)
    if view is None:
        await open_feed(interaction, feed_id, previous)
        return
    await show(interaction, embed, view, previous)


async def open_channels(interaction: discord.Interaction, previous: Any) -> None:
    if not await opened(interaction):
        return
    embed, view = await channel_card(interaction.client, interaction.guild)
    await show(interaction, embed, view, previous)


async def reopen_feeds(interaction: discord.Interaction, previous: Any) -> None:
    where = getattr(previous, "where", FEEDS_VIEW)
    feed_id = getattr(previous, "feed_id", None)
    if where == SUGGESTION_VIEW and feed_id:
        await open_suggestion(interaction, feed_id, getattr(previous, "ref", None), previous)
    elif where == FEED_VIEW and feed_id:
        await open_feed(interaction, feed_id, previous)
    elif where == CHANNEL_VIEW:
        await open_channels(interaction, previous)
    else:
        await open_feeds(interaction, previous)


async def feed_run(interaction: discord.Interaction, view: Any, doing: Any) -> None:
    """Every staff move re-reads the feed first: another door may have removed it."""
    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    feed = await get_feed(bot.db, guild.id, getattr(view, "feed_id", None))
    if feed is None:
        await open_feeds(interaction, view)
        await answer(interaction, mf.NO_SUCH_FEED.format(given=str(view.feed_id)[:40]))
        return
    outcome = await doing(bot, guild, interaction.user, feed)
    if await get_feed(bot.db, guild.id, feed["id"]) is None:
        await open_feeds(interaction, view)
    else:
        await open_feed(interaction, feed["id"], view)
    if outcome.message:
        await answer(interaction, outcome.message)


async def ask_remove_feed(interaction: discord.Interaction, view: Any) -> None:
    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    embed, fresh = await feed_card(bot, guild, getattr(view, "feed_id", None))
    if fresh is None:
        await open_feeds(interaction, view)
        return
    fresh.clear_items()
    feed_id = view.feed_id

    async def yes(one: discord.Interaction, card: Any) -> None:
        card.feed_id = feed_id
        await feed_run(one, card, lambda b, g, a, feed: remove_feed(b, g, a, feed))

    async def no(one: discord.Interaction, card: Any) -> None:
        await open_feed(one, feed_id, card)

    await confirm(
        interaction,
        fresh,
        embed,
        confirm_items(yes=mf.FEED_REMOVE_MOVE.label, no=KEEP_IT, on_yes=yes, on_no=no),
        view,
        question=mf.REMOVE_FEED_QUESTION.format(name=embed.title),
    )


async def feed_move(interaction: discord.Interaction, view: Any, action: str) -> None:
    where = getattr(view, "where", None)
    if action == mt.FEEDS:
        await open_feeds(interaction, view)
    elif action == mf.FEED_ADD:
        await open_channels(interaction, view)
    elif action == mf.FEED_BACK:
        if where == SUGGESTION_VIEW:
            await open_feed(interaction, view.feed_id, view)
        elif where in (FEED_VIEW, CHANNEL_VIEW):
            await open_feeds(interaction, view)
        else:
            await open_root(interaction, view)
    elif action == mf.FEED_CHECK:
        await feed_run(interaction, view, check_now)
    elif action in (mf.FEED_PAUSE, mf.FEED_RESUME):
        wanted = action == mf.FEED_RESUME
        await feed_run(
            interaction,
            view,
            lambda bot, guild, actor, feed: set_feed(bot, guild, actor, feed, active=wanted),
        )
    elif action == mf.FEED_ACTION:
        await feed_run(
            interaction,
            view,
            lambda bot, guild, actor, feed: set_feed(
                bot,
                guild,
                actor,
                feed,
                action=mf.SUGGEST if feed["action"] == mf.ADD else mf.ADD,
            ),
        )
    elif action == mf.FEED_LOOK:
        await feed_run(interaction, view, look_again)
    elif action == mf.FEED_FORGET:
        await feed_run(interaction, view, forget_ignored)
    elif action == mf.FEED_REMOVE:
        await ask_remove_feed(interaction, view)
    elif action in (mf.FEED_TAKE, mf.FEED_DISMISS):
        ref = getattr(view, "ref", None)
        shared = take_suggestion if action == mf.FEED_TAKE else dismiss_suggestion
        await feed_run(
            interaction,
            view,
            lambda bot, guild, actor, feed: shared(bot, guild, actor, feed, ref),
        )


class FeedPick(discord.ui.Select):
    def __init__(self, feeds: list[Any]) -> None:
        super().__init__(
            placeholder=mf.PICK_FEED,
            options=[
                discord.SelectOption(
                    label=str(one["name"])[:100],
                    value=str(one["id"]),
                    description=mf.source_word(one)[:100],
                )
                for one in feeds[:SELECT_CAP]
            ],
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_feed(interaction, self.values[0], self.view)


class SuggestionPick(discord.ui.Select):
    def __init__(self, records: list[dict[str, Any]]) -> None:
        super().__init__(
            placeholder=mf.PICK_SUGGESTION,
            options=[
                discord.SelectOption(
                    label=str(one.get("name") or one.get("ref"))[:100],
                    value=str(one.get("ref"))[:100],
                )
                for one in records[:SELECT_CAP]
            ],
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_suggestion(interaction, self.view.feed_id, self.values[0], self.view)


class ChannelPick(discord.ui.Select):
    def __init__(self, rows: list[Any]) -> None:
        super().__init__(
            placeholder=mf.PICK_CHANNEL,
            options=[
                discord.SelectOption(
                    label=channel_word(row)[:100],
                    value=str(row["id"]),
                    description=f"twitch.tv/{row['twitch_login']}"[:100],
                )
                for row in rows[:SELECT_CAP]
            ],
            row=0,
        )
        self.logins = {str(row["id"]): str(row["twitch_login"]) for row in rows[:SELECT_CAP]}

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        picked = self.values[0]
        login = self.logins.get(picked, "")
        await interaction.response.send_modal(AddFeedModal(self.view, picked, guess_pick(login)))


def guess_pick(login: str) -> str:
    for seed in mf.SEEDS:
        if seed.login == str(login).lower():
            return mf.pick_for(seed._asdict()) or mf.PICK_GDQ
    return mf.PICK_HORARO if str(login).lower() == "esamarathon" else mf.PICK_GDQ


class AddFeedModal(AnswersErrors, discord.ui.Modal, title=mf.ADD_FEED_TITLE):
    source = discord.ui.TextInput(label=mf.ADD_FEED_SOURCE, max_length=10)
    slug = discord.ui.TextInput(
        label=mf.ADD_FEED_SLUG, placeholder=mf.ADD_FEED_SLUG_HINT, required=False, max_length=60
    )
    name = discord.ui.TextInput(label=mf.ADD_FEED_NAME, required=False, max_length=mf.NAME_LIMIT)

    def __init__(self, previous: Any, spotlight_id: Any, pick: str) -> None:
        super().__init__()
        self.previous = previous
        self.spotlight_id = spotlight_id
        self.source.default = pick
        if pick == mf.PICK_HORARO:
            self.slug.default = "esa"

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        outcome = await create_feed(
            interaction.client,
            interaction.guild,
            interaction.user,
            spotlight_id=self.spotlight_id,
            pick=str(self.source),
            slug=str(self.slug),
            name=str(self.name),
        )
        if outcome.ok:
            await open_feed(interaction, outcome.value["id"], self.previous)
        else:
            await open_feeds(interaction, self.previous)
        await answer(interaction, outcome.message)


__all__ = [
    "FEED_VIEWS",
    "FeedButton",
    "check_now",
    "create_feed",
    "dismiss_suggestion",
    "drop_feeds_of_channel",
    "feed_move",
    "forget_ignored",
    "get_feed",
    "ignore_removed",
    "list_feeds",
    "look_again",
    "remove_feed",
    "reopen_feeds",
    "run_check",
    "seed_feeds",
    "set_feed",
    "take_suggestion",
    "tick_feeds",
]
