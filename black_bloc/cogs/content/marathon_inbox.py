from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import Any

import discord

from ... import marathon as mt
from ... import marathon_events as me
from ... import marathon_feeds as mf
from ... import marathon_inbox as mi
from ... import shadow as shadow_home
from ...actionlog import log_action
from ...command_errors import SafeDynamicItem
from ...golive import now_iso, parse_ts
from ...logkinds import VIA_DISCORD, kind_via
from ...marathon_channels import takes_marathons
from ...panels import Outcome, answer, refusal, site_page_url, still_staff
from ...settings_store import (
    DB_UNAVAILABLE,
    MARATHON_ARCHIVED_WORD_KEY,
    MARATHON_FEED_ADDED_TEMPLATE_KEY,
    MARATHON_FEED_NOTICE_WHEN_KEY,
    MARATHON_IGNORED_SAID_KEY,
    MARATHON_INBOX_AUTO_WHO_KEY,
    MARATHON_INBOX_BUTTON_ANYWAY_KEY,
    MARATHON_INBOX_BUTTON_IGNORE_KEY,
    MARATHON_INBOX_BUTTON_SITE_KEY,
    MARATHON_INBOX_BUTTON_THREAD_KEY,
    MARATHON_INBOX_BUTTON_TRACK_KEY,
    MARATHON_INBOX_BUTTON_UNTRACK_KEY,
    MARATHON_INBOX_CHANNEL_KEY,
    MARATHON_INBOX_LABEL_CHANNEL_KEY,
    MARATHON_INBOX_LABEL_EVENT_KEY,
    MARATHON_INBOX_LABEL_SCHEDULE_KEY,
    MARATHON_INBOX_LABEL_SOURCE_KEY,
    MARATHON_INBOX_LABEL_STATE_KEY,
    MARATHON_INBOX_LABEL_WHEN_KEY,
    MARATHON_INBOX_NO_CHANNEL_KEY,
    MARATHON_INBOX_NO_DATES_KEY,
    MARATHON_INBOX_NO_SCHEDULE_KEY,
    MARATHON_INBOX_OPENING_KEY,
    MARATHON_INBOX_OPTED_OUT_KEY,
    MARATHON_INBOX_SCHEDULE_KEY,
    MARATHON_INBOX_STATE_FOUND_KEY,
    MARATHON_INBOX_STATE_IGNORED_KEY,
    MARATHON_INBOX_STATE_TRACKED_KEY,
    MARATHON_INBOX_THREAD_NAME_KEY,
    MARATHON_THREAD_CHANNEL_KEY,
    MARATHON_THREAD_NAME_KEY,
    MARATHON_THREAD_OPENING_KEY,
    MARATHON_TRACK_MAKES_THREAD_KEY,
    MARATHON_TRACK_REFUSED_KEY,
    MARATHON_TRACKED_SAID_KEY,
    MARATHON_UNIGNORED_SAID_KEY,
    MARATHON_UNTRACKED_SAID_KEY,
)
from ...spotlight import reason_of
from ...timezones import unix
from .marathon import (
    FEATURE,
    MODE_IS_OFF,
    NO_CHANNEL,
    NO_SUCH,
    NOT_VISIBLE,
    OPTED_OUT_CODE,
    TEST_MODE,
    _cell,
    actor_id,
    channel_login,
    cog_of,
    counts_of,
    event_status_of,
    get_marathon,
    mode_of,
    rehearsal_home,
    runs_of,
    said_default,
    source_of,
    update_marathon,
)
from .spotlight import channel_by_id

log = logging.getLogger(__name__)

EVENTS_ANNOUNCE_KEY = "events_announce_channel_id"
LABELS = {
    mi.TRACK: MARATHON_INBOX_BUTTON_TRACK_KEY,
    mi.IGNORE: MARATHON_INBOX_BUTTON_IGNORE_KEY,
    mi.UNTRACK: MARATHON_INBOX_BUTTON_UNTRACK_KEY,
    mi.ANYWAY: MARATHON_INBOX_BUTTON_ANYWAY_KEY,
}
STYLES = {
    mi.TRACK: discord.ButtonStyle.primary,
    mi.IGNORE: discord.ButtonStyle.secondary,
    mi.UNTRACK: discord.ButtonStyle.secondary,
    mi.ANYWAY: discord.ButtonStyle.primary,
}


def words(bot: Any, guild_id: int, key: str, **fields: Any) -> str:
    return mt.render(bot.store.get(guild_id, key), said_default(key), **fields).text


# --- the inbox table --------------------------------------------------------------------------


async def inbox_row(db: Any, guild_id: int, home: str) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM marathon_inbox WHERE guild_id = ? AND home = ?", (int(guild_id), home)
    )
    return await cur.fetchone()


async def save_inbox(db: Any, guild_id: int, home: str, channel_id: int, thread_id: int) -> None:
    await db.conn.execute(
        "INSERT OR REPLACE INTO marathon_inbox(guild_id, home, channel_id, thread_id, made_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (int(guild_id), home, int(channel_id), int(thread_id), now_iso()),
    )
    await db.conn.commit()


async def forget_inbox(db: Any, guild_id: int, home: str) -> None:
    await db.conn.execute(
        "DELETE FROM marathon_inbox WHERE guild_id = ? AND home = ?", (int(guild_id), home)
    )
    await db.conn.commit()


# --- where things go --------------------------------------------------------------------------


def home_now(bot: Any, guild: Any) -> str | None:
    return mi.home_of(mode_of(bot, guild.id))


def _as_id(value: Any) -> int | None:
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def real_inbox_parent(bot: Any, guild: Any) -> int | None:
    store = bot.store
    return _as_id(store.get(guild.id, MARATHON_INBOX_CHANNEL_KEY)) or _as_id(
        store.get(guild.id, EVENTS_ANNOUNCE_KEY)
    )


def inbox_parent(bot: Any, guild: Any, home: str) -> int | None:
    if home == mi.HOME_ON:
        return real_inbox_parent(bot, guild)
    return rehearsal_home(bot, guild)


def real_thread_parent(bot: Any, guild: Any) -> int | None:
    return _as_id(bot.store.get(guild.id, MARATHON_THREAD_CHANNEL_KEY)) or real_inbox_parent(
        bot, guild
    )


def thread_parent(bot: Any, guild: Any, home: str) -> int | None:
    if home == mi.HOME_ON:
        return real_thread_parent(bot, guild)
    return rehearsal_home(bot, guild)


def note_for(bot: Any, guild: Any, home: str, real: int | None, text: str) -> str:
    if home == mi.HOME_ON:
        return text
    said = shadow_home.note_line(bot, guild, f"<#{real}>" if real else "#?")
    return f"{said}\n{text}" if said else text


async def find_channel(bot: Any, guild: Any, channel_id: Any) -> tuple[Any, bool]:
    """`(channel, lost)`: an archived thread is not cached, so it is fetched; lost only on a
    NotFound, never on a network hiccup."""
    if not channel_id:
        return (None, True)
    found = shadow_home.channel_of(bot, guild, channel_id)
    if found is not None:
        return (found, False)
    fetch = getattr(guild, "fetch_channel", None)
    if fetch is None:
        return (None, True)
    try:
        return (await fetch(int(channel_id)), False)
    except discord.NotFound:
        return (None, True)
    except Exception as exc:
        log.info("marathon: could not read channel %s — %s", channel_id, reason_of(exc))
        return (None, False)


async def reopened(thread: Any) -> Any:
    if getattr(thread, "archived", False):
        try:
            await thread.edit(archived=False)
        except Exception as exc:
            log.warning("marathon: could not reopen thread %s — %s", thread.id, reason_of(exc))
    return thread


async def make_thread(
    bot: Any, parent: Any, name: str, opening: str, *, reason: str
) -> tuple[Any, Any]:
    """A forum takes its first message with the thread; a text channel gets a public thread
    and the message after it."""
    quiet = discord.AllowedMentions.none()
    if getattr(parent, "type", None) == discord.ChannelType.forum:
        made = await parent.create_thread(
            name=mi.thread_name(name),
            content=opening,
            auto_archive_duration=mi.AUTO_ARCHIVE_MINUTES,
            allowed_mentions=quiet,
            reason=reason,
        )
        thread, first = getattr(made, "thread", made), getattr(made, "message", None)
    else:
        thread = await parent.create_thread(
            name=mi.thread_name(name),
            type=discord.ChannelType.public_thread,
            auto_archive_duration=mi.AUTO_ARCHIVE_MINUTES,
            reason=reason,
        )
        first = await thread.send(opening, allowed_mentions=quiet)
    guard = getattr(bot, "guard", None)
    if guard is not None and hasattr(guard, "own_channel"):
        guard.own_channel(thread)
    return (thread, first)


async def parent_of(bot: Any, guild: Any, channel_id: int | None, missing: str) -> tuple[Any, Any]:
    if channel_id is None:
        return (None, missing)
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel_id):
        return (None, TEST_MODE)
    parent = shadow_home.channel_of(bot, guild, channel_id)
    if parent is None:
        return (None, NOT_VISIBLE)
    if not hasattr(parent, "create_thread"):
        return (None, mi.CANNOT_THREAD)
    return (parent, None)


# --- the inbox thread -------------------------------------------------------------------------


async def ensure_inbox(bot: Any, guild: Any) -> tuple[Any, str | None]:
    """The one inbox thread for this home, made once and re-opened when Discord archived it;
    the stored id is re-read under the lock (checklist 37)."""
    home = home_now(bot, guild)
    if home is None:
        return (None, MODE_IS_OFF)
    cog = cog_of(bot)
    async with cog.inbox_lock(guild.id):
        row = await inbox_row(bot.db, guild.id, home)
        if row is not None:
            thread, lost = await find_channel(bot, guild, row["thread_id"])
            if thread is not None:
                return (await reopened(thread), None)
            if not lost:
                return (None, mi.NOT_READ)
            await forget_inbox(bot.db, guild.id, home)
            await log_action(
                bot,
                guild,
                "marathon.inbox_lost",
                details={
                    "home": home,
                    "channel_id": row["channel_id"],
                    "thread_id": row["thread_id"],
                },
            )
        wanted = inbox_parent(bot, guild, home)
        parent, why = await parent_of(bot, guild, wanted, mi.NO_INBOX_CHANNEL)
        if parent is None:
            return (None, why)
        opening = note_for(
            bot,
            guild,
            home,
            real_inbox_parent(bot, guild),
            words(bot, guild.id, MARATHON_INBOX_OPENING_KEY),
        )
        try:
            thread, _first = await make_thread(
                bot,
                parent,
                words(bot, guild.id, MARATHON_INBOX_THREAD_NAME_KEY),
                opening,
                reason=mi.INBOX_REASON,
            )
        except Exception as exc:
            return (None, reason_of(exc))
        await save_inbox(bot.db, guild.id, home, int(parent.id), int(thread.id))
        await log_action(
            bot,
            guild,
            "marathon.inbox_made",
            details={"home": home, "channel_id": int(parent.id), "thread_id": int(thread.id)},
        )
        return (thread, None)


async def inbox_failed(bot: Any, guild: Any, why: Any, marathon: Any = None) -> None:
    """Once per reason per boot: a missing channel must not write a row every minute."""
    cog = cog_of(bot)
    key = (int(guild.id), str(why))
    if why == MODE_IS_OFF or key in cog.inbox_failures:
        return
    cog.inbox_failures.add(key)
    await log_action(
        bot,
        guild,
        "marathon.inbox_failed",
        details={"reason": str(why), "marathon_id": _cell(marathon, "id")},
    )


# --- the inbox message ------------------------------------------------------------------------


def who_word(bot: Any, guild: Any, user_id: Any, feed: Any = None) -> str:
    if user_id:
        return f"<@{int(user_id)}>"
    if feed is not None:
        return words(bot, guild.id, MARATHON_INBOX_AUTO_WHO_KEY, feed=feed["name"])
    return mi.AUTO_WHO_BOT


async def feed_of(bot: Any, guild: Any, marathon: Any) -> Any:
    from .marathon_feeds import get_feed

    feed_id = _cell(marathon, "feed_id")
    return await get_feed(bot.db, guild.id, feed_id) if feed_id else None


def state_words(bot: Any, guild: Any, marathon: Any, state: str, feed: Any) -> str:
    if state == mi.ARCHIVED:
        return words(
            bot,
            guild.id,
            MARATHON_ARCHIVED_WORD_KEY,
            when=mi.date_of(_cell(marathon, "archived_at")),
        )
    if state == mi.TRACKED:
        return words(
            bot,
            guild.id,
            MARATHON_INBOX_STATE_TRACKED_KEY,
            who=who_word(bot, guild, _cell(marathon, "tracked_by"), feed),
            when=mi.when_of(_cell(marathon, "tracked_at")),
        )
    if state == mi.IGNORED:
        return words(
            bot,
            guild.id,
            MARATHON_INBOX_STATE_IGNORED_KEY,
            who=who_word(bot, guild, _cell(marathon, "ignored_by")),
            when=mi.when_of(_cell(marathon, "ignored_at")),
        )
    return words(
        bot, guild.id, MARATHON_INBOX_STATE_FOUND_KEY, when=mi.when_of(_cell(marathon, "added_at"))
    )


def when_words(bot: Any, guild: Any, marathon: Any) -> str:
    starts = parse_ts(_cell(marathon, "starts_at"))
    if starts is None:
        return words(bot, guild.id, MARATHON_INBOX_NO_DATES_KEY)
    ends = parse_ts(_cell(marathon, "ends_at")) or starts
    return mf.NOTICE_WHEN_RANGE.format(starts=unix(starts), ends=unix(ends))


async def channel_words(bot: Any, guild: Any, marathon: Any) -> str:
    spotlight_id = _cell(marathon, "spotlight_id")
    row = await channel_by_id(bot.db, int(spotlight_id)) if spotlight_id else None
    if row is None:
        return words(bot, guild.id, MARATHON_INBOX_NO_CHANNEL_KEY)
    login = str(row["twitch_login"])
    said = f"[twitch.tv/{login}](https://twitch.tv/{login})"
    if not takes_marathons(row):
        said = f"{said} · {words(bot, guild.id, MARATHON_INBOX_OPTED_OUT_KEY)}"
    return said


async def event_words(bot: Any, marathon: Any) -> str:
    said = me.MODE_WORDS.get(me.mode_of(marathon), me.MODE_WORDS[me.NONE])
    if not _cell(marathon, "event_id"):
        return said
    return f"{said}\n{mt.event_line(marathon, await event_status_of(bot, marathon))}"


async def inbox_embed(
    bot: Any, guild: Any, marathon: Any, state: str, feed: Any, runs: Any = None
) -> Any:
    if runs is None:
        runs = await runs_of(bot.db, marathon["id"]) if state != mi.ARCHIVED else []
    total, baf = counts_of(runs)
    source, url = source_of(marathon)
    source = str(_cell(feed, "name") or source)
    schedule = (
        words(bot, guild.id, MARATHON_INBOX_SCHEDULE_KEY, runs=total, baf=baf)
        if total
        else words(bot, guild.id, MARATHON_INBOX_NO_SCHEDULE_KEY)
    )
    embed = discord.Embed(title=str(marathon["name"])[:256])
    fields = (
        (MARATHON_INBOX_LABEL_WHEN_KEY, when_words(bot, guild, marathon)),
        (MARATHON_INBOX_LABEL_SOURCE_KEY, f"[{source}]({url})" if url else source),
        (MARATHON_INBOX_LABEL_CHANNEL_KEY, await channel_words(bot, guild, marathon)),
        (MARATHON_INBOX_LABEL_SCHEDULE_KEY, schedule),
        (MARATHON_INBOX_LABEL_EVENT_KEY, await event_words(bot, marathon)),
        (MARATHON_INBOX_LABEL_STATE_KEY, state_words(bot, guild, marathon, state, feed)),
    )
    for key, value in fields:
        embed.add_field(name=words(bot, guild.id, key)[:256], value=str(value)[:1024] or "—")
    return embed


def site_link(bot: Any, marathon_id: Any) -> str | None:
    url = site_page_url(getattr(getattr(bot, "settings", None), "origin", ""), FEATURE)
    return f"{url}#marathon-{int(marathon_id)}" if url else None


def inbox_view(bot: Any, guild: Any, marathon: Any, state: str) -> Any:
    view = discord.ui.View(timeout=None)
    for action in mi.MOVES_BY_STATE[state]:
        view.add_item(
            InboxButton(int(marathon["id"]), action, words(bot, guild.id, LABELS[action]))
        )
    thread = mi.channel_url(guild.id, _cell(marathon, "thread_id"))
    if state == mi.TRACKED and thread:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link,
                label=words(bot, guild.id, MARATHON_INBOX_BUTTON_THREAD_KEY)[:80],
                url=thread,
            )
        )
    url = site_link(bot, marathon["id"])
    if url:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link,
                label=words(bot, guild.id, MARATHON_INBOX_BUTTON_SITE_KEY)[:80],
                url=url,
            )
        )
    return view if view.children else None


async def inbox_content(bot: Any, guild: Any, marathon: Any, home: str, feed: Any) -> str:
    text = ""
    if feed is not None:
        login = await channel_login(bot, marathon)
        record = {
            "name": marathon["name"],
            "starts_at": _cell(marathon, "starts_at"),
            "url": _cell(marathon, "schedule_url"),
        }
        text = words(
            bot,
            guild.id,
            MARATHON_FEED_ADDED_TEMPLATE_KEY,
            **mf.notice_fields(feed, record, login or ""),
        )
    if home == mi.HOME_ON:
        return text
    return note_for(bot, guild, home, real_inbox_parent(bot, guild), text).strip()


def fresh_enough(sent: Any, shown: Any, now: Any) -> bool:
    """Nothing changed and it was looked at within the hour: a deleted thread is still
    noticed, without a fetch every minute."""
    if not sent or sent[0] != shown:
        return False
    return now - sent[1] < timedelta(minutes=mi.RECHECK_MINUTES)


async def find_message(channel: Any, message_id: Any) -> tuple[Any, bool]:
    try:
        return (await channel.fetch_message(int(message_id)), False)
    except (discord.NotFound, LookupError):
        return (None, True)
    except Exception as exc:
        log.info("marathon: could not read inbox message %s — %s", message_id, reason_of(exc))
        return (None, False)


def posts_at_add(bot: Any, guild: Any) -> bool:
    return bot.store.get(guild.id, MARATHON_FEED_NOTICE_WHEN_KEY) == mi.WHEN_ADDED


async def sync_inbox(
    bot: Any,
    guild: Any,
    marathon: Any,
    *,
    force: bool = False,
    early: bool = False,
    actor: Any = None,
    via: str = VIA_DISCORD,
) -> Any:
    """Post the marathon's inbox message once its schedule has runs (at once under `added`, or
    `early` at a staff press), then edit it in place whenever what it shows changes. `off`
    posts and edits nothing. Called with the marathon's lock held."""
    home = home_now(bot, guild)
    if marathon is None or home is None:
        return None
    cog = cog_of(bot)
    state = mi.state_of(marathon)
    archived = state == mi.ARCHIVED
    key = int(marathon["id"])
    posted = _cell(marathon, "inbox_message_id")
    here = posted and _cell(marathon, "inbox_home") == home
    if archived and not here:
        return None
    runs = await runs_of(bot.db, key) if not archived else []
    if not here and not early and not posts_at_add(bot, guild) and not counts_of(runs)[0]:
        return None
    feed = await feed_of(bot, guild, marathon)
    embed = await inbox_embed(bot, guild, marathon, state, feed, runs)
    content = await inbox_content(bot, guild, marathon, home, feed)
    shown = (home, mi.comparable(content, [embed]), state, _cell(marathon, "thread_id"))
    now = cog.clock()
    if not force and here and fresh_enough(cog.inbox_sent.get(key), shown, now):
        return None
    thread, why = await ensure_inbox(bot, guild)
    if thread is None:
        await inbox_failed(bot, guild, why, marathon)
        return None
    view = inbox_view(bot, guild, marathon, state)
    if here:
        message, gone = await find_message(thread, posted)
        if message is None and not gone:
            return None
        if message is not None:
            same = mi.comparable(
                getattr(message, "content", ""), getattr(message, "embeds", None)
            ) == mi.comparable(content, [embed])
            if not same or force:
                try:
                    await message.edit(
                        content=content or None,
                        embed=embed,
                        view=view,
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                except Exception as exc:
                    log.warning("marathon: could not edit an inbox message — %s", reason_of(exc))
                    return None
            cog.inbox_sent[key] = (shown, now)
            return message
        if archived:
            return None
    try:
        message = await thread.send(
            content or None,
            embed=embed,
            view=view,
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except Exception as exc:
        await inbox_failed(bot, guild, reason_of(exc), marathon)
        return None
    await update_marathon(bot.db, key, inbox_message_id=int(message.id), inbox_home=home)
    cog.inbox_sent[key] = (shown, now)
    await log_action(
        bot,
        guild,
        kind_via("marathon.inbox_posted", via),
        actor=actor,
        details={
            "marathon_id": key,
            "name": marathon["name"],
            "home": home,
            "thread_id": int(thread.id),
            "message_id": str(message.id),
            "state": state,
            "early": early,
        },
    )
    return message


async def inbox_message_url(bot: Any, guild: Any, marathon: Any) -> str | None:
    home = _cell(marathon, "inbox_home")
    if not _cell(marathon, "inbox_message_id") or not home:
        return None
    row = await inbox_row(bot.db, guild.id, home)
    if row is None:
        return None
    return mi.message_url(guild.id, row["thread_id"], marathon["inbox_message_id"])


# --- the marathon's own thread ----------------------------------------------------------------


def wants_thread(bot: Any, guild: Any, marathon: Any) -> bool:
    return bool(_cell(marathon, "thread_id")) or bool(
        bot.store.get(guild.id, MARATHON_TRACK_MAKES_THREAD_KEY)
    )


async def ensure_thread(bot: Any, guild: Any, marathon: Any) -> tuple[Any, str | None]:
    """The tracked marathon's thread in this home, re-read from the row (the caller holds the
    marathon's lock), re-opened when archived, made again when a person deleted it."""
    home = home_now(bot, guild)
    if home is None:
        return (None, MODE_IS_OFF)
    fresh = await get_marathon(bot.db, guild.id, marathon["id"]) or marathon
    if not wants_thread(bot, guild, fresh):
        return (None, mi.NO_THREAD_WANTED)
    stored = _cell(fresh, "thread_id")
    if stored and _cell(fresh, "thread_home") == home:
        thread, lost = await find_channel(bot, guild, stored)
        if thread is not None:
            return (await reopened(thread), None)
        if not lost:
            return (None, mi.NOT_READ)
        await log_action(
            bot,
            guild,
            "marathon.thread_lost",
            details={"marathon_id": fresh["id"], "thread_id": stored, "home": home},
        )
    wanted = thread_parent(bot, guild, home)
    parent, why = await parent_of(bot, guild, wanted, mi.NO_THREAD_CHANNEL)
    if parent is None:
        return (None, why)
    login = await channel_login(bot, fresh) or ""
    feed = await feed_of(bot, guild, fresh)
    fields = {
        "marathon": fresh["name"],
        "channel": login,
        "when": mi.date_of(_cell(fresh, "starts_at")),
    }
    opening = words(
        bot,
        guild.id,
        MARATHON_THREAD_OPENING_KEY,
        **fields,
        who=who_word(bot, guild, _cell(fresh, "tracked_by"), feed),
        url=source_of(fresh)[1],
    )
    try:
        thread, _first = await make_thread(
            bot,
            parent,
            words(bot, guild.id, MARATHON_THREAD_NAME_KEY, **fields),
            note_for(bot, guild, home, real_thread_parent(bot, guild), opening),
            reason=mi.THREAD_REASON,
        )
    except Exception as exc:
        return (None, reason_of(exc))
    await update_marathon(bot.db, fresh["id"], thread_id=int(thread.id), thread_home=home)
    await log_action(
        bot,
        guild,
        "marathon.thread_made",
        details={
            "marathon_id": fresh["id"],
            "name": fresh["name"],
            "home": home,
            "channel_id": int(parent.id),
            "thread_id": int(thread.id),
            "replaced": stored or None,
        },
    )
    return (thread, None)


async def post_place(bot: Any, guild: Any, marathon: Any) -> tuple[int | None, str | None]:
    """Where a marathon's own post goes: nowhere untracked, its thread, or the marathon channel
    when it was tracked without one."""
    fresh = await get_marathon(bot.db, guild.id, marathon["id"]) or marathon
    if not mi.is_tracked(fresh):
        return (None, mi.NOT_TRACKED)
    thread, why = await ensure_thread(bot, guild, fresh)
    if thread is not None:
        return (int(thread.id), None)
    if why != mi.NO_THREAD_WANTED:
        return (None, why)
    cog = cog_of(bot)
    if cog._home(guild) is None:
        return (None, NO_CHANNEL)
    return (cog._target(guild), None)


async def archive_thread(bot: Any, guild: Any, marathon: Any) -> bool:
    """Kept, not deleted: the thread is archived on Discord."""
    stored = _cell(marathon, "thread_id")
    if not stored:
        return False
    thread, _lost = await find_channel(bot, guild, stored)
    if thread is None or getattr(thread, "archived", False):
        return False
    try:
        await thread.edit(archived=True, reason=mi.THREAD_ARCHIVE_REASON)
    except Exception as exc:
        log.warning("marathon: could not archive thread %s — %s", stored, reason_of(exc))
        return False
    return True


def where_words(marathon: Any, channel_id: Any) -> str:
    """Words, not a mention: the same sentence answers on Discord and on the site."""
    if not channel_id:
        return mi.NOWHERE
    return mi.WHERE_THREAD if _cell(marathon, "thread_id") else mi.WHERE_CHANNEL


# --- the moves: the inbox buttons, the panel and the site all come in by these ----------------


def refused_track(bot: Any, guild: Any, marathon: Any) -> Outcome:
    return refusal(
        words(bot, guild.id, MARATHON_TRACK_REFUSED_KEY, marathon=marathon["name"]),
        OPTED_OUT_CODE,
        409,
    )


def details_of(marathon: Any, via: str, **extra: Any) -> dict[str, Any]:
    return {"marathon_id": marathon["id"], "name": marathon["name"], "via": via} | extra


async def track_held(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon_id: Any,
    *,
    via: str = VIA_DISCORD,
    automatic: bool = False,
) -> Outcome:
    """Called with the marathon's lock held: the row first, then the log, then the thread and
    the inbox edit (checklist 12)."""
    fresh = await get_marathon(bot.db, guild.id, marathon_id)
    if fresh is None:
        return refusal(mt.NO_SUCH_MARATHON.format(given=str(marathon_id)[:40]), NO_SUCH, 404)
    spotlight_id = _cell(fresh, "spotlight_id")
    row = await channel_by_id(bot.db, int(spotlight_id)) if spotlight_id else None
    if row is not None and not takes_marathons(row):
        return refused_track(bot, guild, fresh)
    if not mi.is_tracked(fresh):
        await update_marathon(
            bot.db,
            fresh["id"],
            tracked_at=now_iso(),
            tracked_by=None if automatic else actor_id(actor),
            ignored_at=None,
            ignored_by=None,
        )
        await log_action(
            bot,
            guild,
            kind_via("marathon.tracked", via),
            actor=None if automatic else actor,
            details=details_of(fresh, via, automatic=automatic, feed_id=_cell(fresh, "feed_id")),
        )
    fresh = await get_marathon(bot.db, guild.id, fresh["id"])
    where, _why = await post_place(bot, guild, fresh)
    fresh = await get_marathon(bot.db, guild.id, fresh["id"])
    await sync_inbox(bot, guild, fresh, force=True)
    return Outcome(
        True,
        words(
            bot,
            guild.id,
            MARATHON_TRACKED_SAID_KEY,
            marathon=fresh["name"],
            where=where_words(fresh, where),
        ),
        value=fresh,
    )


async def track(
    bot: Any, guild: Any, actor: Any, marathon: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    async with cog_of(bot).lock(marathon["id"]):
        return await track_held(bot, guild, actor, marathon["id"], via=via)


async def stop_posting(bot: Any, guild: Any, marathon: Any) -> None:
    """The in-flight effects end with the tracking: the pin comes off, the thread is archived."""
    await cog_of(bot).unpin_board(guild, marathon, because=mi.UNTRACK_BECAUSE)
    await archive_thread(bot, guild, marathon)


async def untrack(
    bot: Any, guild: Any, actor: Any, marathon: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    async with cog_of(bot).lock(marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return refusal(mt.NO_SUCH_MARATHON.format(given=marathon["id"]), NO_SUCH, 404)
        if _cell(fresh, "tracked_at"):
            await update_marathon(bot.db, fresh["id"], tracked_at=None, tracked_by=None)
            await log_action(
                bot,
                guild,
                kind_via("marathon.untracked", via),
                actor=actor,
                details=details_of(fresh, via),
            )
            await stop_posting(bot, guild, fresh)
        fresh = await get_marathon(bot.db, guild.id, fresh["id"])
        await sync_inbox(bot, guild, fresh, force=True)
    return Outcome(
        True, words(bot, guild.id, MARATHON_UNTRACKED_SAID_KEY, marathon=fresh["name"]), value=fresh
    )


async def ignore(
    bot: Any, guild: Any, actor: Any, marathon: Any, on: bool, *, via: str = VIA_DISCORD
) -> Outcome:
    """Ignoring is a choice about posting: the row stays on the list and is read; the feed's
    own ignore list is not touched."""
    async with cog_of(bot).lock(marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return refusal(mt.NO_SUCH_MARATHON.format(given=marathon["id"]), NO_SUCH, 404)
        if on and not mi.is_ignored(fresh):
            was_tracked = bool(_cell(fresh, "tracked_at"))
            await update_marathon(
                bot.db,
                fresh["id"],
                ignored_at=now_iso(),
                ignored_by=actor_id(actor),
                tracked_at=None,
                tracked_by=None,
            )
            await log_action(
                bot,
                guild,
                kind_via("marathon.ignored", via),
                actor=actor,
                details=details_of(fresh, via, was_tracked=was_tracked),
            )
            if was_tracked:
                await stop_posting(bot, guild, fresh)
        elif not on and mi.is_ignored(fresh):
            await update_marathon(bot.db, fresh["id"], ignored_at=None, ignored_by=None)
            await log_action(
                bot,
                guild,
                kind_via("marathon.unignored", via),
                actor=actor,
                details=details_of(fresh, via),
            )
        fresh = await get_marathon(bot.db, guild.id, fresh["id"])
        await sync_inbox(bot, guild, fresh, force=True)
    key = MARATHON_IGNORED_SAID_KEY if on else MARATHON_UNIGNORED_SAID_KEY
    return Outcome(True, words(bot, guild.id, key, marathon=fresh["name"]), value=fresh)


async def auto_track(bot: Any, guild: Any, marathon_id: Any, feed: Any) -> bool:
    """The schedule-out moment of a feed whose auto-track is on; the caller holds the lock and
    has already claimed noticed_at, so it runs once."""
    if feed is None or not _cell(feed, "auto_track"):
        return False
    fresh = await get_marathon(bot.db, guild.id, marathon_id)
    if fresh is None or mi.is_ignored(fresh) or mi.is_tracked(fresh):
        return False
    done = await track_held(bot, guild, None, marathon_id, via=mf.VIA_FEED, automatic=True)
    return done.ok


async def archived_inbox(bot: Any, guild: Any, marathon: Any, archived_at: str) -> None:
    """At the archive move: the inbox message reads Archived with only the site link, and the
    marathon's thread is archived on Discord."""
    await archive_thread(bot, guild, marathon)
    await sync_inbox(bot, guild, {**dict(marathon), "archived_at": archived_at}, force=True)


async def run_action(
    bot: Any, guild: Any, actor: Any, marathon: Any, action: str, *, via: str = VIA_DISCORD
) -> Outcome:
    if action in (mi.TRACK, mi.ANYWAY):
        return await track(bot, guild, actor, marathon, via=via)
    if action == mi.UNTRACK:
        return await untrack(bot, guild, actor, marathon, via=via)
    if action == mi.UNIGNORE:
        return await ignore(bot, guild, actor, marathon, False, via=via)
    return await ignore(bot, guild, actor, marathon, True, via=via)


# --- the inbox message's buttons (KI-20: they outlive a restart) -----------------------------


class InboxButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=mi.INBOX_TEMPLATE
):
    def __init__(self, marathon_id: int, action: str, label: str | None = None) -> None:
        self.marathon_id = int(marathon_id)
        self.action = action
        super().__init__(
            discord.ui.Button(
                label=(label or mi.DEFAULT_LABELS[action])[:80],
                style=STYLES[action],
                custom_id=mi.custom_id(marathon_id, action),
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["marathon_id"]), match["action"])

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
        marathon = await get_marathon(bot.db, interaction.guild.id, self.marathon_id)
        if marathon is None:
            await answer(interaction, mf.NOTICE_GONE)
            return
        outcome = await run_action(bot, interaction.guild, interaction.user, marathon, self.action)
        await answer(interaction, outcome.message)


__all__ = [
    "InboxButton",
    "archived_inbox",
    "auto_track",
    "ensure_inbox",
    "ensure_thread",
    "ignore",
    "inbox_message_url",
    "post_place",
    "sync_inbox",
    "track",
    "track_held",
    "untrack",
]
