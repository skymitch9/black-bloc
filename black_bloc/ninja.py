from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import discord

from . import ninja_store as store
from .actionlog import log_action
from .emoji import TEST_MODE, react_with
from .logkinds import VIA_DISCORD, VIA_WEBSITE, kind_via
from .panels import Outcome, refusal
from .settings_store import (
    DEFAULT_TIMEZONE_KEY,
    KEY_MAX,
    NINJA_DEFAULT_MINUTES,
    NINJA_DEFAULT_POSTS,
    NINJA_DEFAULTS,
    NINJA_EMOJI,
    NINJA_MODE,
    NINJA_MODES,
    QUESTION_CHANNEL,
)
from .timezones import zone

log = logging.getLogger(__name__)

FEATURE = "ninja"
OFF, ON = NINJA_MODES
POSTS = store.POSTS
TIME = store.TIME
STAFF = store.STAFF
MARKED_ATTR = "_ninja_marked"
USER_CONTENT = (discord.MessageType.default, discord.MessageType.reply)
SAME_DAY = timedelta(hours=20)
MOST_POSTS = KEY_MAX[NINJA_DEFAULT_POSTS]
MOST_MINUTES = KEY_MAX[NINJA_DEFAULT_MINUTES]
SITE_TIME = "%Y-%m-%d %H:%M"
KEEP_THE_CARD = ("bad_number", "no_limit")


def moment(now: datetime | None = None) -> datetime:
    return now or datetime.now(UTC)


def stamp_of(when: datetime) -> str:
    return when.astimezone(UTC).isoformat(timespec="seconds")


def parse_when(text: Any) -> datetime | None:
    try:
        found = datetime.fromisoformat(str(text))
    except (TypeError, ValueError):
        return None
    return found if found.tzinfo else found.replace(tzinfo=UTC)


def words(bot_store: Any, guild_id: int, key: str, **fields: Any) -> str:
    """Staff wording when it fills, otherwise the shipped wording."""
    wording = str(bot_store.get(guild_id, key) or "").strip()
    if wording:
        try:
            return wording.format(**fields)
        except Exception as exc:
            log.warning("ninja: %s could not be filled in (%s); shipped wording used", key, exc)
    return str(NINJA_DEFAULTS[key]).format(**fields)


def mode_of(bot_store: Any, guild_id: int) -> str:
    found = str(bot_store.get(guild_id, NINJA_MODE) or "")
    return found if found in NINJA_MODES else OFF


def is_on(bot_store: Any, guild_id: int) -> bool:
    return mode_of(bot_store, guild_id) == ON


def emoji_of(bot_store: Any, guild_id: int) -> str:
    return str(bot_store.get(guild_id, NINJA_EMOJI) or "").strip()


def default_channel(bot_store: Any, guild_id: int) -> int | None:
    found = bot_store.get(guild_id, QUESTION_CHANNEL)
    return int(found) if found else None


def default_limits(bot_store: Any, guild_id: int) -> tuple[str, str]:
    """What the form shows to start with: a 0 default is a blank field."""
    posts = int(bot_store.get(guild_id, NINJA_DEFAULT_POSTS) or 0)
    minutes = int(bot_store.get(guild_id, NINJA_DEFAULT_MINUTES) or 0)
    return (str(posts) if posts else "", str(minutes) if minutes else "")


def is_due(row: Any, now: datetime) -> str | None:
    """Why an active mark is over, or None while it still runs."""
    left = row["posts_left"]
    if left is not None and int(left) <= 0:
        return POSTS
    until = parse_when(row["until"]) if row["until"] else None
    if row["until"] and (until is None or until <= now):
        return TIME
    return None


def until_words(bot_store: Any, guild_id: int, when: datetime, via: str, now: datetime) -> str:
    if via == VIA_WEBSITE:
        tz = zone(bot_store.get(guild_id, DEFAULT_TIMEZONE_KEY)) or UTC
        return when.astimezone(tz).strftime(SITE_TIME)
    style = "t" if when - now < SAME_DAY else "f"
    return f"<t:{int(when.timestamp())}:{style}>"


def left_words(
    bot_store: Any,
    guild_id: int,
    posts: Any,
    until: Any,
    *,
    via: str = VIA_DISCORD,
    now: datetime | None = None,
) -> str:
    when = parse_when(until) if until else None
    if when is None:
        return words(bot_store, guild_id, "ninja_left_posts", posts=posts)
    said = until_words(bot_store, guild_id, when, via, moment(now))
    if posts is None:
        return words(bot_store, guild_id, "ninja_left_until", until=said)
    return words(bot_store, guild_id, "ninja_left_both", posts=posts, until=said)


def who_words(guild: Any, user_ids: list[int], via: str) -> str:
    if via != VIA_WEBSITE:
        return ", ".join(f"<@{one}>" for one in user_ids)
    names = []
    for one in user_ids:
        member = guild.get_member(int(one)) if guild is not None else None
        names.append(f"@{getattr(member, 'display_name', None) or one}")
    return ", ".join(names)


def number(bot_store: Any, guild_id: int, given: Any, what_key: str, most: int) -> int | None:
    """A whole number from 1 to `most`, None for blank or 0; anything else raises a sentence."""
    if given is None:
        return None
    text = str(given).strip()
    if not text or text == "0":
        return None
    if not text.isdigit() or not 0 < int(text) <= most:
        raise ValueError(
            words(
                bot_store,
                guild_id,
                "ninja_bad_number_said",
                given=text[:20],
                what=words(bot_store, guild_id, what_key).lower(),
                most=most,
            )
        )
    return int(text)


def marked(bot: Any) -> dict[tuple[int, int], set[int]]:
    found = getattr(bot, MARKED_ATTR, None)
    if found is None:
        found = {}
        setattr(bot, MARKED_ATTR, found)
    return found


async def reload(bot: Any) -> None:
    """The in-memory map the listener reads, rebuilt from the active rows."""
    rows = await store.active_everywhere(bot.db)
    fresh: dict[tuple[int, int], set[int]] = {}
    for row in rows:
        fresh.setdefault((int(row["guild_id"]), int(row["user_id"])), set()).add(
            int(row["channel_id"])
        )
    held = marked(bot)
    held.clear()
    held.update(fresh)


def might_be_marked(bot: Any, message: Any) -> bool:
    """No database read: the author, the place and the map only."""
    author = getattr(message, "author", None)
    if author is None or getattr(author, "bot", False):
        return False
    if getattr(message, "webhook_id", None) is not None:
        return False
    if getattr(message, "type", discord.MessageType.default) not in USER_CONTENT:
        return False
    guild = getattr(message, "guild", None)
    channel = getattr(message, "channel", None)
    if guild is None or channel is None:
        return False
    channels = marked(bot).get((int(guild.id), int(author.id)))
    return bool(channels) and int(channel.id) in channels


async def mark(
    bot: Any,
    guild: Any,
    actor: Any,
    user_ids: Any,
    channel_id: Any,
    posts: Any,
    minutes: Any,
    *,
    via: str = VIA_DISCORD,
    now: datetime | None = None,
) -> Outcome:
    say = bot.store
    wanted = []
    for one in user_ids or ():
        text = str(getattr(one, "id", one)).strip()
        if text.isdigit() and int(text) not in wanted:
            wanted.append(int(text))
    if not wanted:
        return refusal(words(say, guild.id, "ninja_no_one_said"), "no_one", 400)
    where = str(getattr(channel_id, "id", channel_id) or "").strip()
    if not where.isdigit():
        return refusal(words(say, guild.id, "ninja_no_channel_said"), "no_channel", 400)
    try:
        posts_n = number(say, guild.id, posts, "ninja_posts_field", MOST_POSTS)
        minutes_n = number(say, guild.id, minutes, "ninja_minutes_field", MOST_MINUTES)
    except ValueError as exc:
        return refusal(str(exc), "bad_number", 400)
    if posts_n is None and minutes_n is None:
        return refusal(words(say, guild.id, "ninja_no_limit_said"), "no_limit", 400)
    at = moment(now)
    until = stamp_of(at + timedelta(minutes=minutes_n)) if minutes_n else None
    emoji = emoji_of(say, guild.id)
    made, kept = [], []
    for user_id in wanted:
        mark_id = await store.add(
            bot.db,
            guild.id,
            user_id,
            int(where),
            emoji,
            posts_n,
            until,
            getattr(actor, "id", None),
            stamp_of(at),
        )
        if mark_id is None:
            kept.append(user_id)
            continue
        made.append(user_id)
        await log_action(
            bot,
            guild,
            kind_via("ninja.marked", via),
            actor=actor,
            target=user_id,
            details={
                "via": via,
                "mark_id": mark_id,
                "user_id": user_id,
                "channel_id": int(where),
                "posts": posts_n,
                "minutes": minutes_n,
                "until": until,
                "emoji": emoji,
            },
        )
    await reload(bot)
    channel = f"<#{where}>"
    lines = []
    if made:
        left = left_words(say, guild.id, posts_n, until, via=via, now=at)
        lines.append(
            words(
                say,
                guild.id,
                "ninja_marked_said",
                who=who_words(guild, made, via),
                channel=channel,
                left=left,
            )
        )
    if kept:
        lines.append(
            words(
                say,
                guild.id,
                "ninja_already_said",
                who=who_words(guild, kept, via),
                channel=channel,
            )
        )
    message = "\n".join(lines)
    if not made:
        return refusal(message, "already_marked", 409)
    return Outcome(True, message, value=made)


async def end(
    bot: Any,
    guild: Any,
    actor: Any,
    mark_id: Any,
    *,
    via: str = VIA_DISCORD,
    now: datetime | None = None,
) -> Outcome:
    say = bot.store
    row = await store.get(bot.db, guild.id, int(mark_id))
    if row is None or row["ended_at"] is not None:
        return refusal(words(say, guild.id, "ninja_not_active_said"), "not_active", 409)
    if not await store.end(bot.db, int(row["id"]), STAFF, stamp_of(moment(now))):
        return refusal(words(say, guild.id, "ninja_not_active_said"), "not_active", 409)
    await reload(bot)
    await log_action(
        bot,
        guild,
        kind_via("ninja.ended", via),
        actor=actor,
        target=int(row["user_id"]),
        details=ended_details(row, STAFF) | {"via": via},
    )
    return Outcome(
        True,
        words(
            say,
            guild.id,
            "ninja_ended_said",
            who=who_words(guild, [int(row["user_id"])], via),
            channel=f"<#{int(row['channel_id'])}>",
        ),
        value=int(row["id"]),
    )


def ended_details(row: Any, because: str) -> dict[str, Any]:
    return {
        "mark_id": int(row["id"]),
        "user_id": int(row["user_id"]),
        "channel_id": int(row["channel_id"]),
        "because": because,
    }


async def finish(bot: Any, guild: Any, row: Any, because: str, now: datetime) -> bool:
    """The bot's own end of a spent or timed-out mark; one row however many callers race."""
    if not await store.end(bot.db, int(row["id"]), because, stamp_of(now)):
        return False
    await reload(bot)
    await log_action(
        bot, guild, "ninja.ended", target=int(row["user_id"]), details=ended_details(row, because)
    )
    return True


async def on_post(bot: Any, message: Any, now: datetime | None = None) -> bool:
    """The emote on a marked member's post, one per post; True once it is on."""
    if not might_be_marked(bot, message):
        return False
    guild = message.guild
    if not is_on(bot.store, guild.id):
        return False
    db = getattr(bot, "db", None)
    if db is None or not getattr(db, "is_connected", False):
        return False
    at = moment(now)
    row = await store.active_for(db, guild.id, message.author.id, message.channel.id)
    if row is None:
        await reload(bot)
        return False
    because = is_due(row, at)
    if because is not None:
        await finish(bot, guild, row, because, at)
        return False
    if not await store.claim_post(db, int(row["id"]), stamp_of(at)):
        return False
    why = await react_with(bot, message, str(row["emoji"]))
    if why is not None:
        await store.give_back(db, int(row["id"]))
        if why != TEST_MODE:
            log.warning("ninja: a marked post was not reacted to — %s", why)
            await log_action(
                bot,
                guild,
                "ninja.react_failed",
                target=int(row["user_id"]),
                details={
                    "mark_id": int(row["id"]),
                    "channel_id": int(row["channel_id"]),
                    "message_id": int(message.id),
                    "why": why,
                },
            )
        return False
    left = None if row["posts_left"] is None else int(row["posts_left"]) - 1
    await log_action(
        bot,
        guild,
        "ninja.reacted",
        target=int(row["user_id"]),
        details={
            "user_id": int(row["user_id"]),
            "channel_id": int(row["channel_id"]),
            "message_id": int(message.id),
            "mark_id": int(row["id"]),
            "posts_left": left,
        },
    )
    if left is not None and left <= 0:
        await finish(bot, guild, row, POSTS, at)
    return True


async def settle(bot: Any, now: datetime | None = None) -> int:
    """Ends every spent or timed-out mark whatever ninja_mode says; returns how many."""
    at = moment(now)
    rows = await store.due(bot.db, stamp_of(at))
    guilds = {
        int(guild.id): guild
        for guild in getattr(bot, "guilds", ())
        if not getattr(guild, "unavailable", False)
    }
    done = 0
    for row in rows:
        guild = guilds.get(int(row["guild_id"]))
        if guild is None:
            continue
        because = is_due(row, at) or TIME
        if await finish(bot, guild, row, because, at):
            done += 1
    return done


__all__ = [
    "FEATURE",
    "end",
    "is_due",
    "left_words",
    "mark",
    "might_be_marked",
    "on_post",
    "reload",
    "settle",
    "words",
]
