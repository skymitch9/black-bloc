from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ...actionlog import (
    LOGS_DEFAULT,
    LOGS_MAX,
    LOGS_MIN,
    log_action,
    send_logs,
)
from ...command_errors import NETWORK_ERRORS, AnswersErrors, SafeDynamicItem
from ...events import (
    APPROVED,
    BAD_DURATION,
    CANCELLED,
    DEFAULT_DURATION_MINUTES,
    DENIED,
    DESCRIPTION_LIMIT,
    DONE,
    EVENT_NAME_LIMIT,
    LIVE,
    LOCATION_LIMIT,
    OPEN_STATUSES,
    PENDING,
    START_IN_THE_PAST,
    SWEPT_STATUSES,
    TERMINAL_STATUSES,
    TITLE_LIMIT,
    announce_text,
    build_card,
    can_transition,
    channel_name,
    clamp,
    describe_duration,
    ends_at,
    golive_text,
    mentions,
    parse_duration,
    start_error,
)
from ...golive import now_iso, parse_ts
from ...settings_store import (
    DB_UNAVAILABLE,
    EVENTS_LATE_CEILING_MINUTES,
    EVENTS_MODES,
    EVENTS_RETENTION_MAX_DAYS,
    EVENTS_RETENTION_MIN_DAYS,
    GUILD_ONLY,
    require_staff,
    staff_roles_sentence,
)
from ...timezones import (
    AMBIGUOUS,
    CHOICE_LIMIT,
    DEFAULT_TZ,
    GAP,
    START_EXAMPLE,
    clock_trouble,
    get_timezone,
    is_known,
    local_time,
    parse_start,
    set_timezone,
    stored_timezone,
    suggest,
)

log = logging.getLogger(__name__)

DECISION_TEMPLATE = r"event:(?P<event_id>[0-9]+):(?P<action>approve|deny)"
LOCKS_ATTR = "_event_locks"
GOLIVE_MINUTES = 1
RECONCILE_MINUTES = 5
LOOP_NAMES = ("golive", "reconcile")
ORPHAN_GRACE_MINUTES = 5
LOCATION_FALLBACK = "Ask in the server"

UNKNOWN_TZ = (
    "**{given}** is not a time zone Black Bloc knows, so nothing was saved. Start typing a city "
    "— `Phoenix`, `London`, `Tokyo` — and pick one of the suggestions, which are the "
    "`Region/City` names Discord and your phone both use."
)
TZ_SET = (
    "Your time zone is **{tz}**, where it is now **{now}**. Times you type into `/event create` "
    f"are read in that zone, so `{START_EXAMPLE}` means half past seven in the evening for you."
)
TZ_SHOW = "Your time zone is **{tz}**, where it is now **{now}**. `/timezone set` changes it."
TZ_SHOW_DEFAULT = (
    "You have not set a time zone, so Black Bloc reads the times you type as **{tz}**, where it "
    "is now **{now}**. `/timezone set` changes that."
)

EVENTS_OFF = (
    "Event proposals are turned off on this server, so nothing was submitted. A Lead turns them "
    "back on with `/event settings` — ask one if you have something to run."
)
NO_TEST_CHANNEL = (
    "Black Bloc is in test mode and cannot work out where a review channel would be allowed, so "
    "nothing was submitted. Its test channel has to exist AND has to sit inside a category — set "
    "TEST_CHANNEL_ID to a channel the bot can read, put that channel in a category, restart it, "
    "then try again."
)
NO_TITLE = (
    "An event needs a name, so nothing was submitted. Put something in the Title box — it is the "
    "heading everybody sees on the card."
)
DST_GAP = (
    "**{given}** never happens in **{tz}** — the clocks jump forward over that hour, so nothing "
    "was submitted. Pick a time before or after the hour that is skipped, or run `/timezone set` "
    "if that zone is not the one you are in."
)
DST_AMBIGUOUS = (
    "**{given}** happens twice in **{tz}** — the clocks go back and that hour runs again, so "
    "Black Bloc will not guess which of the two you meant and nothing was submitted. Pick a time "
    "an hour either side of it."
)
MODAL_ZONE_HINT = "{example} — read in {tz}; /timezone set changes it"
CANCELLED_ANNOUNCEMENT = "**{title}** is cancelled and is no longer happening."
NO_CATEGORY = (
    "Black Bloc has nowhere to put the review channel, so nothing was submitted. A Lead points it "
    "at a category with `/event settings category:<the Events category>`, then this works."
)
NOT_A_CATEGORY = (
    "**events_category_id** points at something that is not a category, so nothing was "
    "submitted. A Lead fixes it with `/event settings category:<the Events category>`."
)
CANNOT_CREATE = (
    "Discord refused to make the review channel, so nothing was submitted. Black Bloc needs the "
    "Manage Channels permission in that category. Tell a Lead, then try again."
)
SUBMITTED = (
    "**{title}** is in — the mods will review it and Black Bloc will DM you either way. {where}"
)
SUBMITTED_HERE = "Their review card is in {channel}."
SUBMITTED_TEST = (
    "Test mode is on, so the review card is in this channel rather than in {channel}, which is "
    "where it will go once the owner lifts it."
)
SUBMITTED_NO_CARD = (
    "Black Bloc could not post the review card in {channel} — the log says why, and a Lead can "
    "still decide it there by hand."
)
NO_SUCH_EVENT = (
    "Black Bloc has no record of that event any more, so nothing was changed. `/event list` shows "
    "the ones it still knows about."
)
ALREADY_DECIDED = (
    "Somebody got there first — event #{event_id} is already **{status}**, so nothing was "
    "changed. Its card above shows who decided and when."
)
APPROVED_SAID = "Approved. {extra}"
DENIED_SAID = "Denied, and the requester has been told why."
DM_APPROVED = (
    "Your event **{title}** was approved on **{guild}**. It starts {stamp}."
)
DM_DENIED = (
    "Your event **{title}** was not approved on **{guild}**. The reason given was: {reason}. Ask "
    "a Lead there if you want to talk it over — Black Bloc cannot change the decision."
)
DM_CANCELLED = "Your event **{title}** on **{guild}** has been cancelled — {why}"
CANCEL_WHY: dict[str, str] = {
    "never_got_a_channel": (
        "Black Bloc could not finish setting it up, so nobody was ever able to review it. Propose "
        "it again with `/event create`."
    ),
    "review_channel_gone": (
        "the channel the mods were reviewing it in is no longer there. Propose it again with "
        "`/event create` if it should still happen."
    ),
    "review_channel_deleted": (
        "the channel the mods were reviewing it in was deleted. Propose it again with `/event "
        "create` if it should still happen."
    ),
    "unreadable_start": (
        "Black Bloc could not read the start time stored for it. Propose it again with `/event "
        "create` and write the time as `YYYY-MM-DD HH:MM`."
    ),
}
CANCEL_WHY_DEFAULT = (
    "either you or a member of staff called it off. Ask a Lead there if that is a surprise."
)
DM_MISSED = (
    "Your event **{title}** on **{guild}** finished before Black Bloc ever announced it, so "
    "nobody was told it was on. It has been marked done. Sorry — propose it again with `/event "
    "create` if you want another go."
)
NO_ANNOUNCE_CHANNEL = (
    "there is nowhere to announce it — a Lead sets `/event settings announce_channel:`"
)
NOT_YOURS = (
    "Event #{event_id} is not yours, so nothing was cancelled. Only the person who proposed it or "
    "a member of staff can cancel it."
)
CANCELLED_SAID = "Event #{event_id} is cancelled."
NOT_OPEN = (
    "Event #{event_id} is already **{status}**, so there was nothing to cancel."
)
NOT_AN_ID = "**{given}** is not an event number, so nothing was cancelled. `/event list` has them."
NO_STAFF_WARNING = (
    "⚠️ **No staff roles resolve**, so nobody but server admins can see a review channel or press "
    "Approve. Point `staff_channel_id` at a channel only staff can see with `/settings set "
    "staff_channel_id`, then check `/event list` again."
)


async def create_event(
    db: Any,
    guild_id: int,
    requester_id: int,
    *,
    title: str,
    description: str | None,
    location: str | None,
    starts_at: datetime,
    finishes_at: datetime,
) -> int | None:
    cur = await db.conn.execute(
        "INSERT INTO events(guild_id, requester_id, title, description, location, starts_at, "
        "ends_at, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            guild_id,
            requester_id,
            title,
            description or None,
            location or None,
            starts_at.isoformat(),
            finishes_at.isoformat(),
            PENDING,
            now_iso(),
        ),
    )
    await db.conn.commit()
    return cur.lastrowid


async def get_event(db: Any, event_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    return await cur.fetchone()


async def events_by_status(db: Any, guild_id: int, statuses: Any) -> list[Any]:
    marks = ", ".join("?" for _ in statuses)
    cur = await db.conn.execute(
        f"SELECT * FROM events WHERE guild_id = ? AND status IN ({marks}) ORDER BY starts_at",
        (guild_id, *statuses),
    )
    return list(await cur.fetchall())


async def due_events(db: Any, status: str, column: str, before: str) -> list[Any]:
    cur = await db.conn.execute(
        f"SELECT * FROM events WHERE status = ? AND {column} IS NOT NULL AND {column} <= ? "
        "ORDER BY id",
        (status, before),
    )
    return list(await cur.fetchall())


async def set_review(
    db: Any,
    event_id: int,
    channel_id: int | None,
    message_id: int | None,
    card_channel_id: int | None = None,
) -> None:
    await db.conn.execute(
        "UPDATE events SET review_channel_id = ?, review_message_id = ?, card_channel_id = ? "
        "WHERE id = ?",
        (channel_id, message_id, card_channel_id, event_id),
    )
    await db.conn.commit()


async def set_status(
    db: Any,
    event_id: int,
    status: str,
    *,
    decided_by: int | None = None,
    deny_reason: str | None = None,
) -> None:
    await db.conn.execute(
        "UPDATE events SET status = ?, decided_by = COALESCE(?, decided_by), "
        "decided_at = COALESCE(?, decided_at), deny_reason = COALESCE(?, deny_reason) WHERE id = ?",
        (
            status,
            decided_by,
            now_iso() if decided_by is not None else None,
            deny_reason,
            event_id,
        ),
    )
    await db.conn.commit()


async def set_scheduled(db: Any, event_id: int, scheduled_event_id: int) -> None:
    await db.conn.execute(
        "UPDATE events SET scheduled_event_id = ? WHERE id = ?", (scheduled_event_id, event_id)
    )
    await db.conn.commit()


async def set_announced(db: Any, event_id: int, message_id: int) -> None:
    await db.conn.execute(
        "UPDATE events SET announce_message_id = ? WHERE id = ?", (message_id, event_id)
    )
    await db.conn.commit()


async def event_for_channel(db: Any, channel_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM events WHERE review_channel_id = ? ORDER BY id DESC LIMIT 1", (channel_id,)
    )
    return await cur.fetchone()


def event_lock(bot: Any, event_id: int) -> asyncio.Lock:
    locks = getattr(bot, LOCKS_ATTR, None)
    if locks is None:
        locks = {}
        setattr(bot, LOCKS_ATTR, locks)
    lock = locks.get(event_id)
    if lock is None:
        lock = locks[event_id] = asyncio.Lock()
    return lock


def drop_lock(bot: Any, event_id: int) -> None:
    """A settled event will never be raced again, so its lock stops being kept."""
    locks = getattr(bot, LOCKS_ATTR, None)
    if locks is not None:
        locks.pop(event_id, None)


def decision_id(event_id: int, action: str) -> str:
    return f"event:{event_id}:{action}"


def duration_minutes(row: Any) -> int:
    starts = parse_ts(row["starts_at"])
    finishes = parse_ts(row["ends_at"])
    if starts is None or finishes is None:
        return DEFAULT_DURATION_MINUTES
    return max(int((finishes - starts).total_seconds() // 60), 1)


def card_for(row: Any) -> discord.Embed:
    """One place turns a stored event into the card every surface shows."""
    starts = parse_ts(row["starts_at"]) or datetime.now(UTC)
    return build_card(
        event_id=row["id"],
        title=row["title"],
        requester_id=row["requester_id"],
        starts_at=starts,
        minutes=duration_minutes(row),
        location=row["location"],
        description=row["description"],
        status=row["status"],
        deny_reason=row["deny_reason"],
    )


def review_overwrites(guild: Any, staff_roles: Any, me: Any = None) -> dict[Any, Any]:
    overwrites: dict[Any, Any] = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False)
    }
    for role in staff_roles:
        overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
    if me is not None:
        overwrites[me] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_channels=True
        )
    return overwrites


def events_category(bot: Any, guild: Any) -> tuple[Any, str]:
    """Where review channels go: the test channel's category while the guard is installed."""
    guard = getattr(bot, "guard", None)
    if guard is not None:
        test_channel = bot.get_channel(guard.test_channel_id) if guard.test_channel_id else None
        category = getattr(test_channel, "category", None)
        if test_channel is None or category is None:
            return None, "no_test_channel"
        return category, "test_category"
    category_id = bot.store.get(guild.id, "events_category_id")
    if not category_id:
        return None, "no_category"
    category = guild.get_channel(category_id)
    if category is None:
        return None, "no_category"
    if not isinstance(category, discord.CategoryChannel) and not hasattr(category, "channels"):
        return None, "not_a_category"
    return category, "category"


def card_channel(bot: Any, review_channel: Any) -> Any:
    """The review card goes to the test channel while the guard would refuse the review one."""
    guard = getattr(bot, "guard", None)
    if guard is None or guard.allows_channel(review_channel.id):
        return review_channel
    return bot.get_channel(guard.test_channel_id) if guard.test_channel_id else None


def review_view(event_id: int) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(DecisionButton(event_id, "approve"))
    view.add_item(DecisionButton(event_id, "deny"))
    return view


async def answer(interaction: discord.Interaction, text: str) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(
            text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )
        return
    await interaction.response.send_message(
        text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )


async def dm(user: Any, text: str, embed: discord.Embed | None = None) -> bool:
    """Whether the person actually got told."""
    send = getattr(user, "send", None)
    if send is None:
        return False
    try:
        await send(text, embed=embed, allowed_mentions=discord.AllowedMentions.none())
    except Exception as exc:
        log.info("events: could not DM %s: %s", getattr(user, "id", "?"), exc)
        return False
    return True


async def tell_or_log(bot: Any, guild: Any, user: Any, row: Any, text: str) -> None:
    """A DM the requester is owed; a failure is a logged fact, never a silent one."""
    if await dm(user, text, card_for(row)):
        return
    await log_action(
        bot,
        guild,
        "event.dm_failed",
        target=row["requester_id"],
        details={"event_id": row["id"]},
    )


async def rename_channel(bot: Any, guild: Any, row: Any, status: str, user_name: str) -> None:
    channel = guild.get_channel(row["review_channel_id"]) if row["review_channel_id"] else None
    if channel is None:
        return
    wanted = channel_name(status, user_name, row["title"])
    if getattr(channel, "name", None) == wanted:
        return
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_place(channel):
        await log_action(
            bot,
            guild,
            "event.would_rename",
            details={"event_id": row["id"], "channel_id": channel.id, "name": wanted},
        )
        return
    try:
        await channel.edit(name=wanted, reason=f"Black Bloc event {row['id']}")
    except NETWORK_ERRORS as exc:
        log.warning("events: could not rename %s to %s: %s", channel.id, wanted, exc)
        await log_action(
            bot,
            guild,
            "event.rename_failed",
            details={
                "event_id": row["id"],
                "channel_id": channel.id,
                "reason": f"{type(exc).__name__}: {exc}",
            },
        )


async def create_scheduled_event(bot: Any, guild: Any, row: Any) -> tuple[Any, str | None]:
    """The scheduled event Discord made, or the reason there is not one."""
    if not bot.store.get(guild.id, "events_create_scheduled"):
        return None, "turned_off"
    starts = parse_ts(row["starts_at"])
    finishes = parse_ts(row["ends_at"])
    if starts is None:
        return None, "unreadable_start"
    if finishes is None:
        finishes = ends_at(starts, DEFAULT_DURATION_MINUTES)
    if getattr(bot, "guard", None) is not None:
        log.warning("events: TEST MODE — no scheduled event made for event %s", row["id"])
        await log_action(
            bot,
            guild,
            "event.would_create_scheduled",
            target=row["requester_id"],
            details={"event_id": row["id"], "reason": "test_mode"},
        )
        return None, "test_mode"
    try:
        made = await guild.create_scheduled_event(
            name=clamp(row["title"], EVENT_NAME_LIMIT),
            description=clamp(row["description"], DESCRIPTION_LIMIT) or None,
            start_time=starts,
            end_time=finishes,
            entity_type=discord.EntityType.external,
            location=clamp(row["location"], LOCATION_LIMIT) or LOCATION_FALLBACK,
            privacy_level=discord.PrivacyLevel.guild_only,
            reason=f"Black Bloc event {row['id']}",
        )
    except NETWORK_ERRORS as exc:
        log.warning("events: could not make a scheduled event for %s: %s", row["id"], exc)
        await log_action(
            bot,
            guild,
            "event.create_scheduled_failed",
            target=row["requester_id"],
            details={"event_id": row["id"], "reason": f"{type(exc).__name__}: {exc}"},
        )
        return None, f"{type(exc).__name__}: {exc}"
    await set_scheduled(bot.db, row["id"], made.id)
    return made, None


async def find_scheduled_event(guild: Any, scheduled_id: int) -> Any:
    """The cache first, then Discord — a restart empties the cache, not the calendar."""
    cached = getattr(guild, "get_scheduled_event", None)
    found = cached(scheduled_id) if cached is not None else None
    if found is not None:
        return found
    fetch = getattr(guild, "fetch_scheduled_event", None)
    if fetch is None:
        return None
    return await fetch(scheduled_id)


async def cancel_scheduled_event(bot: Any, guild: Any, row: Any) -> None:
    scheduled_id = row["scheduled_event_id"]
    if not scheduled_id:
        return
    details = {"event_id": row["id"], "scheduled_event_id": scheduled_id}
    if getattr(bot, "guard", None) is not None:
        await log_action(
            bot,
            guild,
            "event.would_cancel_scheduled",
            details=details | {"reason": "test_mode"},
        )
        return
    reason = f"Black Bloc event {row['id']} cancelled"
    try:
        event = await find_scheduled_event(guild, scheduled_id)
        if event is None:
            raise ValueError("Discord has no such scheduled event")
        if getattr(event, "status", None) is discord.EventStatus.active:
            await event.end(reason=reason)
        else:
            await event.cancel(reason=reason)
    except NETWORK_ERRORS as exc:
        log.warning("events: could not cancel scheduled event %s: %s", scheduled_id, exc)
        await log_action(
            bot,
            guild,
            "event.cancel_scheduled_failed",
            details=details | {"reason": f"{type(exc).__name__}: {exc}"},
        )


async def post_to_announce(
    bot: Any, guild: Any, row: Any, text: str, embed: discord.Embed | None, kind: str
) -> int | None:
    """The one guarded way anything of this feature reaches a public channel."""
    ping_role_id = bot.store.get(guild.id, "events_ping_role_id")
    details = {"event_id": row["id"]}
    mode = bot.store.get(guild.id, "events_mode")
    if mode != "on":
        await log_action(
            bot, guild, f"event.would_{kind}", details=details | {"reason": f"mode_{mode}"}
        )
        return None
    channel_id = bot.store.get(guild.id, "events_announce_channel_id")
    channel = bot.get_channel(channel_id) if channel_id else None
    if channel is None:
        await log_action(
            bot, guild, f"event.{kind}_failed", details=details | {"reason": "no_channel"}
        )
        return None
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel.id):
        await log_action(
            bot, guild, f"event.would_{kind}", details=details | {"reason": "test_mode"}
        )
        return None
    try:
        message = await channel.send(
            text, embed=embed, allowed_mentions=mentions(ping_role_id)
        )
    except Exception as exc:
        log.warning("events: could not post %s for event %s: %s", kind, row["id"], exc)
        await log_action(
            bot,
            guild,
            f"event.{kind}_failed",
            details=details | {"reason": f"{type(exc).__name__}: {exc}"},
        )
        return None
    await log_action(bot, guild, f"event.{kind}", details=details | {"channel_id": channel.id})
    return message.id


async def edit_announcement(bot: Any, guild: Any, row: Any) -> None:
    """A public post must stop advertising an event that is off."""
    message_id = row["announce_message_id"]
    if not message_id:
        return
    channel_id = bot.store.get(guild.id, "events_announce_channel_id")
    channel = bot.get_channel(channel_id) if channel_id else None
    details = {"event_id": row["id"], "message_id": message_id}
    if channel is None:
        await log_action(
            bot,
            guild,
            "event.edit_announcement_failed",
            details=details | {"reason": "no_channel"},
        )
        return
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel):
        await log_action(bot, guild, "event.would_edit_announcement", details=details)
        return
    partial = getattr(channel, "get_partial_message", None)
    try:
        message = (
            partial(message_id) if partial is not None else await channel.fetch_message(message_id)
        )
        await message.edit(
            content=CANCELLED_ANNOUNCEMENT.format(title=clamp(row["title"], TITLE_LIMIT)),
            embed=card_for(row),
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except NETWORK_ERRORS as exc:
        log.warning("events: could not edit the announcement for %s: %s", row["id"], exc)
        await log_action(
            bot,
            guild,
            "event.edit_announcement_failed",
            details=details | {"reason": f"{type(exc).__name__}: {exc}"},
        )
        return
    await log_action(bot, guild, "event.announcement_edited", details=details)


async def cancel_event(
    bot: Any, guild: Any, row: Any, reason: str, *, by: int | None = None
) -> bool:
    """Cancel one event and undo what it left behind; False when it was past cancelling."""
    async with event_lock(bot, row["id"]):
        fresh = await get_event(bot.db, row["id"])
        if fresh is None or not can_transition(fresh["status"], CANCELLED):
            return False
        await set_status(bot.db, fresh["id"], CANCELLED)
        drop_lock(bot, fresh["id"])
        await log_action(
            bot,
            guild,
            "event.cancelled",
            target=fresh["requester_id"],
            reason=reason,
            details={"event_id": fresh["id"], "title": fresh["title"]},
        )
        await cancel_scheduled_event(bot, guild, fresh)
        fresh = await get_event(bot.db, row["id"])
        await edit_announcement(bot, guild, fresh)
        if by == fresh["requester_id"]:
            return True
        await tell_or_log(
            bot,
            guild,
            guild.get_member(fresh["requester_id"]),
            fresh,
            DM_CANCELLED.format(
                title=fresh["title"],
                guild=guild.name,
                why=CANCEL_WHY.get(reason, CANCEL_WHY_DEFAULT),
            ),
        )
        return True


async def apply_decision(
    bot: Any, guild: Any, event_id: int, status: str, actor: Any, reason: str | None = None
) -> tuple[str, Any]:
    """Approve or deny, once, whoever gets the lock first: (what to say, the settled row)."""
    async with event_lock(bot, event_id):
        row = await get_event(bot.db, event_id)
        if row is None:
            return (NO_SUCH_EVENT, None)
        if not can_transition(row["status"], status):
            return (ALREADY_DECIDED.format(event_id=event_id, status=row["status"]), None)
        await set_status(
            bot.db, event_id, status, decided_by=getattr(actor, "id", actor), deny_reason=reason
        )
        if status in TERMINAL_STATUSES:
            drop_lock(bot, event_id)
        await log_action(
            bot,
            guild,
            f"event.{status}",
            actor=actor,
            target=row["requester_id"],
            reason=reason,
            details={"event_id": event_id, "title": row["title"]},
        )
        fresh = await get_event(bot.db, event_id)
        requester = guild.get_member(row["requester_id"])
        why_not: str | None = None
        message_id: int | None = None
        if status == APPROVED:
            made, why_not = await create_scheduled_event(bot, guild, fresh)
            fresh = await get_event(bot.db, event_id)
            ping_role_id = bot.store.get(guild.id, "events_ping_role_id")
            message_id = await post_to_announce(
                bot,
                guild,
                fresh,
                announce_text(
                    ping_role_id,
                    has_scheduled=made is not None,
                    event_url=getattr(made, "url", None),
                ),
                card_for(fresh),
                "announce",
            )
            if message_id is not None:
                await set_announced(bot.db, event_id, message_id)
                fresh = await get_event(bot.db, event_id)
        await _tell_requester(guild, requester, fresh, status, reason)
        name = getattr(requester, "display_name", str(row["requester_id"]))
        await rename_channel(bot, guild, fresh, status, name)
        if status == DENIED:
            return (DENIED_SAID, fresh)
        return (APPROVED_SAID.format(extra=_approve_extra(why_not, message_id)), fresh)


async def decide(
    interaction: discord.Interaction, event_id: int, status: str, reason: str | None = None
) -> None:
    said, fresh = await apply_decision(
        interaction.client, interaction.guild, event_id, status, interaction.user, reason
    )
    if fresh is not None:
        await _close_card(interaction, fresh)
    await answer(interaction, said)


async def _tell_requester(
    guild: Any, requester: Any, row: Any, status: str, reason: str | None
) -> None:
    if status == DENIED:
        await dm(
            requester,
            DM_DENIED.format(
                title=row["title"], guild=guild.name, reason=reason or "none given"
            ),
            card_for(row),
        )
        return
    starts = parse_ts(row["starts_at"])
    await dm(
        requester,
        DM_APPROVED.format(
            title=row["title"],
            guild=guild.name,
            stamp=f"<t:{int(starts.timestamp())}:F>" if starts else "soon",
        ),
        card_for(row),
    )


def _approve_extra(why_not: str | None, message_id: int | None) -> str:
    parts = []
    if why_not == "test_mode":
        parts.append(
            "Test mode is on, so no real Discord scheduled event was made — the log says "
            "`event.would_create_scheduled`."
        )
    elif why_not == "turned_off":
        parts.append("Scheduled events are turned off in `/event settings`.")
    elif why_not is not None:
        parts.append("Discord refused to make the scheduled event — the log says why.")
    if message_id is None:
        parts.append("Nothing was announced publicly; the log says why.")
    return " ".join(parts) or "The event is announced and the requester has been told."


async def _close_card(interaction: discord.Interaction, row: Any) -> None:
    message = getattr(interaction, "message", None)
    if message is None:
        return
    try:
        await message.edit(
            embed=card_for(row), view=None, allowed_mentions=discord.AllowedMentions.none()
        )
    except Exception as exc:
        log.warning("events: could not close the card for event %s: %s", row["id"], exc)


async def decision_context(interaction: discord.Interaction, event_id: int) -> Any:
    """This click's event row, or None once the clicker has been answered."""
    bot = interaction.client
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(interaction.channel_id):
        await interaction.response.send_message(guard.refusal_message(), ephemeral=True)
        return None
    if not await require_staff(interaction):
        return None
    if not bot.db.is_connected:
        await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
        return None
    row = await get_event(bot.db, event_id)
    if row is None:
        await interaction.response.send_message(NO_SUCH_EVENT, ephemeral=True)
        return None
    return row


class DenyModal(AnswersErrors, discord.ui.Modal, title="Why not?"):
    reason = discord.ui.TextInput(
        label="One line the requester will be sent",
        style=discord.TextStyle.paragraph,
        max_length=400,
    )

    def __init__(self, event_id: int) -> None:
        super().__init__()
        self.event_id = event_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await decide(interaction, self.event_id, DENIED, clamp(self.reason, 400))


class DecisionButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=DECISION_TEMPLATE
):
    def __init__(self, event_id: int, action: str) -> None:
        self.event_id = event_id
        self.action = action
        approving = action == "approve"
        super().__init__(
            discord.ui.Button(
                label="Approve" if approving else "Deny",
                style=discord.ButtonStyle.success if approving else discord.ButtonStyle.danger,
                custom_id=decision_id(event_id, action),
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["event_id"]), match["action"])

    async def on_click(self, interaction: discord.Interaction) -> None:
        row = await decision_context(interaction, self.event_id)
        if row is None:
            return
        wanted = APPROVED if self.action == "approve" else DENIED
        if not can_transition(row["status"], wanted):
            await interaction.response.send_message(
                ALREADY_DECIDED.format(event_id=self.event_id, status=row["status"]),
                ephemeral=True,
            )
            return
        if self.action == "deny":
            await interaction.response.send_modal(DenyModal(self.event_id))
            return
        await interaction.response.defer(ephemeral=True)
        await decide(interaction, self.event_id, APPROVED)


class EventModal(AnswersErrors, discord.ui.Modal, title="Propose an event"):
    event_title = discord.ui.TextInput(label="Title", max_length=TITLE_LIMIT)
    description = discord.ui.TextInput(
        label="What is it?",
        style=discord.TextStyle.paragraph,
        max_length=DESCRIPTION_LIMIT,
        required=False,
    )
    start = discord.ui.TextInput(
        label="Start — YYYY-MM-DD HH:MM", placeholder=START_EXAMPLE, max_length=16
    )
    duration = discord.ui.TextInput(
        label="How long? 1h30m", placeholder="2h", max_length=12, required=False
    )
    location = discord.ui.TextInput(
        label="Where, or a link", max_length=LOCATION_LIMIT, required=False
    )

    def __init__(self, cog: Events, tz_name: str) -> None:
        super().__init__()
        self.cog = cog
        self.tz_name = tz_name
        self.start.placeholder = MODAL_ZONE_HINT.format(example=START_EXAMPLE, tz=tz_name)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.cog.submit(
            interaction,
            tz_name=self.tz_name,
            title=clamp(self.event_title, TITLE_LIMIT),
            description=clamp(self.description, DESCRIPTION_LIMIT),
            start=str(self.start),
            duration=str(self.duration),
            location=clamp(self.location, LOCATION_LIMIT),
        )


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.last_ok_at: dict[str, str | None] = {name: None for name in LOOP_NAMES}
        self.last_error: dict[str, str | None] = {name: None for name in LOOP_NAMES}
        self._missing_since: dict[int, str] = {}

    event = app_commands.Group(name="event", description="Propose and run server events")
    timezone = app_commands.Group(
        name="timezone", description="The zone Black Bloc reads the times you type in"
    )

    async def cog_load(self) -> None:
        self.bot.add_dynamic_items(DecisionButton)
        if not self.bot.db.is_connected:
            return
        await self.reconcile_events()
        self._golive_loop.start()
        self._reconcile_loop.start()

    async def cog_unload(self) -> None:
        self._golive_loop.cancel()
        self._reconcile_loop.cancel()

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        key = name.removeprefix("_").removesuffix("_loop")
        if key not in LOOP_NAMES:
            return (None, None)
        return (self.last_ok_at[key], self.last_error[key])

    def loop_failed(self, name: str, exc: BaseException, loop: Any) -> None:
        """A loop that raised is restarted, and its failure is on the record until it is not."""
        self.last_error[name] = f"{now_iso()} · {type(exc).__name__}: {exc}"
        log.exception("events: the %s loop raised and is being restarted", name, exc_info=exc)
        loop.restart()

    @tasks.loop(minutes=GOLIVE_MINUTES)
    async def _golive_loop(self) -> None:
        if self.bot.db.is_connected:
            await self.run_due_events()
        self.last_ok_at["golive"] = now_iso()

    @_golive_loop.before_loop
    async def _before_golive(self) -> None:
        await self.bot.wait_until_ready()

    @_golive_loop.error
    async def _golive_broke(self, exc: BaseException) -> None:
        self.loop_failed("golive", exc, self._golive_loop)

    @tasks.loop(minutes=RECONCILE_MINUTES)
    async def _reconcile_loop(self) -> None:
        if self.bot.db.is_connected:
            await self.reconcile_events()
        self.last_ok_at["reconcile"] = now_iso()

    @_reconcile_loop.before_loop
    async def _before_reconcile(self) -> None:
        await self.bot.wait_until_ready()

    @_reconcile_loop.error
    async def _reconcile_broke(self, exc: BaseException) -> None:
        self.loop_failed("reconcile", exc, self._reconcile_loop)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self.bot.db.is_connected:
            await self.reconcile_events()

    async def run_due_events(self) -> None:
        """Approved events that have started go live; live ones that have finished are done."""
        now = datetime.now(UTC)
        stamp = now.isoformat()
        seen = {guild.id: guild for guild in getattr(self.bot, "guilds", ())}
        for row in await due_events(self.bot.db, APPROVED, "starts_at", stamp):
            guild = seen.get(row["guild_id"])
            if guild is not None:
                await self._go_live(guild, row, now)
        for row in await due_events(self.bot.db, LIVE, "ends_at", stamp):
            guild = seen.get(row["guild_id"])
            if guild is not None:
                await self._finish(guild, row)

    async def _go_live(self, guild: Any, row: Any, now: datetime) -> None:
        async with event_lock(self.bot, row["id"]):
            fresh = await get_event(self.bot.db, row["id"])
            if fresh is None or not can_transition(fresh["status"], LIVE):
                return
            finishes = parse_ts(fresh["ends_at"])
            if finishes is not None and finishes <= now:
                await self._missed(guild, fresh)
                return
            starts = parse_ts(fresh["starts_at"])
            late = int((now - starts).total_seconds() // 60) if starts is not None else 0
            cap = int(self.bot.store.get(guild.id, "events_max_late_minutes") or 0)
            await set_status(self.bot.db, fresh["id"], LIVE)
            if late > cap:
                await log_action(
                    self.bot,
                    guild,
                    "event.announce_skipped_late",
                    target=fresh["requester_id"],
                    details={
                        "event_id": fresh["id"],
                        "late_minutes": late,
                        "allowed_minutes": cap,
                    },
                )
                return
            await post_to_announce(
                self.bot,
                guild,
                fresh,
                golive_text(fresh["title"], self.bot.store.get(guild.id, "events_ping_role_id")),
                None,
                "go_live",
            )

    async def _missed(self, guild: Any, row: Any) -> None:
        """An approved event whose end has already gone by is never announced, only recorded."""
        await set_status(self.bot.db, row["id"], DONE)
        drop_lock(self.bot, row["id"])
        await log_action(
            self.bot,
            guild,
            "event.missed",
            target=row["requester_id"],
            details={"event_id": row["id"], "title": row["title"]},
        )
        fresh = await get_event(self.bot.db, row["id"])
        member = guild.get_member(row["requester_id"])
        await tell_or_log(
            self.bot,
            guild,
            member,
            fresh,
            DM_MISSED.format(title=row["title"], guild=guild.name),
        )
        await rename_channel(
            self.bot,
            guild,
            fresh,
            DONE,
            getattr(member, "display_name", str(row["requester_id"])),
        )

    async def _finish(self, guild: Any, row: Any) -> None:
        async with event_lock(self.bot, row["id"]):
            fresh = await get_event(self.bot.db, row["id"])
            if fresh is None or not can_transition(fresh["status"], DONE):
                return
            await set_status(self.bot.db, fresh["id"], DONE)
            drop_lock(self.bot, fresh["id"])
            await log_action(
                self.bot,
                guild,
                "event.done",
                target=fresh["requester_id"],
                details={"event_id": fresh["id"]},
            )
            member = guild.get_member(fresh["requester_id"])
            await rename_channel(
                self.bot,
                guild,
                fresh,
                DONE,
                getattr(member, "display_name", str(fresh["requester_id"])),
            )

    async def reconcile_events(self) -> None:
        """Events whose review channel has gone are cancelled; finished ones are tidied away."""
        now = datetime.now(UTC)
        for guild in list(getattr(self.bot, "guilds", ())):
            if getattr(guild, "unavailable", False):
                log.info("events: %s is unavailable, so nothing about it is reconciled", guild.id)
                continue
            for row in await events_by_status(self.bot.db, guild.id, OPEN_STATUSES):
                await self._recheck(guild, row, now)
            await self._sweep_finished(guild, now)

    async def _recheck(self, guild: Any, row: Any, now: datetime) -> None:
        if parse_ts(row["starts_at"]) is None:
            await self._cancel(guild, row, "unreadable_start")
            return
        channel_id = row["review_channel_id"]
        if channel_id is None:
            created = parse_ts(row["created_at"])
            if created is not None and now - created < timedelta(minutes=ORPHAN_GRACE_MINUTES):
                return
            await self._cancel(guild, row, "never_got_a_channel")
            return
        if guild.get_channel(channel_id) is not None:
            self._missing_since.pop(row["id"], None)
            return
        if row["id"] not in self._missing_since:
            self._missing_since[row["id"]] = now_iso()
            log.info(
                "events: channel %s for event %s is missing; deciding at the next pass",
                channel_id,
                row["id"],
            )
            return
        self._missing_since.pop(row["id"], None)
        await self._cancel(guild, row, "review_channel_gone")

    async def _cancel(self, guild: Any, row: Any, reason: str, *, by: int | None = None) -> None:
        await cancel_event(self.bot, guild, row, reason, by=by)

    async def _sweep_finished(self, guild: Any, now: datetime) -> None:
        days = int(self.bot.store.get(guild.id, "events_channel_retention_days") or 0)
        guard = getattr(self.bot, "guard", None)
        for row in await events_by_status(self.bot.db, guild.id, SWEPT_STATUSES):
            channel = (
                guild.get_channel(row["review_channel_id"]) if row["review_channel_id"] else None
            )
            if channel is None:
                continue
            finished = parse_ts(row["ends_at"])
            if finished is None or now - finished < timedelta(days=days):
                continue
            if guard is not None and not guard.allows_place(channel):
                await log_action(
                    self.bot,
                    guild,
                    "event.would_delete_channel",
                    details={"event_id": row["id"], "channel_id": channel.id},
                )
                continue
            try:
                await channel.delete(reason=f"Black Bloc event {row['id']}: kept {days} day(s)")
            except NETWORK_ERRORS as exc:
                log.warning("events: could not delete %s: %s", channel.id, exc)
                continue
            await set_review(
                self.bot.db,
                row["id"],
                None,
                row["review_message_id"],
                row["card_channel_id"],
            )
            await log_action(
                self.bot,
                guild,
                "event.channel_deleted",
                details={"event_id": row["id"], "channel_id": channel.id, "kept_days": days},
            )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        if not self.bot.db.is_connected:
            return
        guild = channel.guild
        for key, kind in (
            ("events_category_id", "event.category_forgotten"),
            ("events_announce_channel_id", "event.announce_channel_forgotten"),
        ):
            if channel.id == self.bot.store.get(guild.id, key):
                await self.bot.store.clear(guild.id, key)
                await log_action(self.bot, guild, kind, details={"channel_id": channel.id})
        row = await event_for_channel(self.bot.db, channel.id)
        if row is not None and row["status"] in OPEN_STATUSES:
            await self._cancel(guild, row, "review_channel_deleted")

    async def _database_ready(self, interaction: discord.Interaction) -> bool:
        if self.bot.db.is_connected:
            return True
        log.warning("events: refused a command — the database is not connected")
        await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
        return False

    async def _ready(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message(GUILD_ONLY, ephemeral=True)
            return False
        return await self._database_ready(interaction)

    @event.command(name="logs", description="The last few events log lines")
    @app_commands.describe(
        count="How many lines, 1 to 50 (10 by default)",
        important_only="True to leave out the dry runs and the housekeeping",
    )
    async def event_logs(
        self,
        interaction: discord.Interaction,
        count: app_commands.Range[int, LOGS_MIN, LOGS_MAX] = LOGS_DEFAULT,
        important_only: bool = False,
    ) -> None:
        await send_logs(interaction, "events", count=count, important_only=important_only)

    @event.command(name="create", description="Propose an event for the mods to review")
    async def event_create(self, interaction: discord.Interaction) -> None:
        if not await self._ready(interaction):
            return
        if self.bot.store.get(interaction.guild.id, "events_mode") == "off":
            await interaction.response.send_message(EVENTS_OFF, ephemeral=True)
            return
        tz_name = await get_timezone(self.bot.db, interaction.user.id)
        await interaction.response.send_modal(EventModal(self, tz_name))

    async def submit(
        self,
        interaction: discord.Interaction,
        *,
        tz_name: str,
        title: str,
        description: str,
        start: str,
        duration: str,
        location: str,
    ) -> None:
        """What the modal does once it is filled in: one row, one channel, one card."""
        if not title:
            await answer(interaction, NO_TITLE)
            return
        starts = parse_start(start, tz_name)
        if starts is None:
            await answer(interaction, start_error(start, tz_name, START_EXAMPLE))
            return
        trouble = clock_trouble(start, tz_name)
        if trouble == GAP:
            await answer(interaction, DST_GAP.format(given=clamp(start, 80), tz=tz_name))
            return
        if trouble == AMBIGUOUS:
            await answer(interaction, DST_AMBIGUOUS.format(given=clamp(start, 80), tz=tz_name))
            return
        if starts <= datetime.now(UTC):
            await answer(
                interaction, START_IN_THE_PAST.format(given=clamp(start, 80), tz=tz_name)
            )
            return
        minutes = parse_duration(duration)
        if minutes is None:
            await answer(interaction, BAD_DURATION.format(given=clamp(duration, 40)))
            return
        guild = interaction.guild
        category, where = events_category(self.bot, guild)
        if where == "no_test_channel":
            await answer(interaction, NO_TEST_CHANNEL)
            return
        if where == "no_category":
            await answer(interaction, NO_CATEGORY)
            return
        if where == "not_a_category":
            await answer(interaction, NOT_A_CATEGORY)
            return
        await interaction.response.defer(ephemeral=True)
        event_id = await create_event(
            self.bot.db,
            guild.id,
            interaction.user.id,
            title=title,
            description=description,
            location=location,
            starts_at=starts,
            finishes_at=ends_at(starts, minutes),
        )
        row = await get_event(self.bot.db, event_id)
        channel = await self._make_review_channel(interaction, guild, row)
        if channel is None:
            return
        await set_review(self.bot.db, event_id, channel.id, None)
        await log_action(
            self.bot,
            guild,
            "event.created",
            actor=interaction.user,
            target=interaction.user,
            details={"event_id": event_id, "title": title, "channel_id": channel.id},
        )
        row = await get_event(self.bot.db, event_id)
        posted = await self._post_review_card(guild, row, channel)
        if posted is None:
            said = SUBMITTED_NO_CARD
        elif posted == channel.id:
            said = SUBMITTED_HERE
        else:
            said = SUBMITTED_TEST
        await answer(
            interaction,
            SUBMITTED.format(title=title, where=said.format(channel=f"<#{channel.id}>")),
        )
        await dm(interaction.user, f"Submitted on **{guild.name}**.", card_for(row))

    async def _make_review_channel(
        self, interaction: discord.Interaction, guild: Any, row: Any
    ) -> Any:
        category, _ = events_category(self.bot, guild)
        staff = self.bot.store.staff_roles(guild)
        if not staff:
            log.warning("events: no staff roles resolve, so %s is admin-only", row["id"])
        try:
            return await guild.create_text_channel(
                channel_name(PENDING, interaction.user.display_name, row["title"]),
                category=category,
                overwrites=review_overwrites(guild, staff, getattr(guild, "me", None)),
                reason=f"Black Bloc event {row['id']}",
            )
        except NETWORK_ERRORS as exc:
            log.warning("events: could not make a review channel for %s: %s", row["id"], exc)
            await set_status(self.bot.db, row["id"], CANCELLED)
            await log_action(
                self.bot,
                guild,
                "event.channel_failed",
                target=interaction.user,
                details={"event_id": row["id"], "reason": f"{type(exc).__name__}: {exc}"},
            )
            await answer(interaction, CANNOT_CREATE)
            return None

    async def _post_review_card(self, guild: Any, row: Any, channel: Any) -> int | None:
        """Where the card actually went, so the reply can say so."""
        target = card_channel(self.bot, channel)
        if target is None:
            await log_action(
                self.bot,
                guild,
                "event.would_post_card",
                details={"event_id": row["id"], "channel_id": channel.id},
            )
            return None
        try:
            message = await target.send(
                embed=card_for(row),
                view=review_view(row["id"]),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except Exception as exc:
            log.warning("events: could not post the card for %s: %s", row["id"], exc)
            await log_action(
                self.bot,
                guild,
                "event.card_failed",
                details={"event_id": row["id"], "reason": f"{type(exc).__name__}: {exc}"},
            )
            return None
        await set_review(self.bot.db, row["id"], channel.id, message.id, target.id)
        return target.id

    @event.command(name="list", description="Show the events waiting on a decision")
    async def event_list(self, interaction: discord.Interaction) -> None:
        if not await require_staff(interaction):
            return
        if not await self._database_ready(interaction):
            return
        guild = interaction.guild
        rows = await events_by_status(self.bot.db, guild.id, OPEN_STATUSES)
        staff = self.bot.store.staff_roles(guild)
        lines = [f"**staff (who may approve)** — {staff_roles_sentence(staff)}"]
        if not rows:
            lines.append("Nothing is waiting — `/event create` proposes one.")
        for row in rows:
            starts = parse_ts(row["starts_at"])
            where = f" · <#{row['review_channel_id']}>" if row["review_channel_id"] else ""
            when = f"<t:{int(starts.timestamp())}:R>" if starts else "at an unreadable time"
            lines.append(
                f"**#{row['id']}** {clamp(row['title'], 60)} — {row['status']} · {when}"
                f" · {describe_duration(duration_minutes(row))}{where}"
            )
        if not staff:
            lines.append(NO_STAFF_WARNING)
        await interaction.response.send_message(
            "\n".join(lines), ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @event.command(name="cancel", description="Call off an event you proposed, or any as staff")
    @app_commands.describe(event_id="The number `/event list` shows")
    async def event_cancel(self, interaction: discord.Interaction, event_id: str) -> None:
        if not await self._ready(interaction):
            return
        digits = event_id.strip().lstrip("#")
        if not digits.isdigit():
            await interaction.response.send_message(
                NOT_AN_ID.format(given=clamp(event_id, 40)),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        guild = interaction.guild
        row = await get_event(self.bot.db, int(digits))
        if row is None or row["guild_id"] != guild.id:
            await interaction.response.send_message(NO_SUCH_EVENT, ephemeral=True)
            return
        if row["requester_id"] != interaction.user.id and not self.bot.store.is_staff(
            interaction.user
        ):
            await interaction.response.send_message(
                NOT_YOURS.format(event_id=row["id"]), ephemeral=True
            )
            return
        if row["status"] not in OPEN_STATUSES:
            await interaction.response.send_message(
                NOT_OPEN.format(event_id=row["id"], status=row["status"]), ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        await self._cancel(
            guild, row, f"cancelled_by_{interaction.user.id}", by=interaction.user.id
        )
        fresh = await get_event(self.bot.db, row["id"])
        if fresh["status"] != CANCELLED:
            await answer(
                interaction, NOT_OPEN.format(event_id=row["id"], status=fresh["status"])
            )
            return
        member = guild.get_member(row["requester_id"])
        await rename_channel(
            self.bot,
            guild,
            fresh,
            CANCELLED,
            getattr(member, "display_name", str(row["requester_id"])),
        )
        await answer(interaction, CANCELLED_SAID.format(event_id=row["id"]))

    @event.command(name="settings", description="Show or change how events are set up")
    @app_commands.describe(
        category="Where review channels are made",
        announce_channel="Where approved events are announced",
        ping_role="Role mentioned when an event is announced or starts",
        create_scheduled="Make a real Discord scheduled event when one is approved",
        retention_days="Days a finished event's channel is kept",
        max_late_minutes="Minutes an event may start late and still be announced",
        mode="off, shadow (no public announcement) or on",
        clear_ping_role="Stop mentioning any role",
        clear_category="Forget the category review channels are made in",
        clear_announce_channel="Forget where approved events are announced",
    )
    @app_commands.choices(
        mode=[app_commands.Choice(name=name, value=name) for name in EVENTS_MODES]
    )
    async def event_settings(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel | None = None,
        announce_channel: discord.TextChannel | None = None,
        ping_role: discord.Role | None = None,
        create_scheduled: bool | None = None,
        retention_days: (
            app_commands.Range[int, EVENTS_RETENTION_MIN_DAYS, EVENTS_RETENTION_MAX_DAYS] | None
        ) = None,
        max_late_minutes: app_commands.Range[int, 0, EVENTS_LATE_CEILING_MINUTES] | None = None,
        mode: app_commands.Choice[str] | None = None,
        clear_ping_role: bool = False,
        clear_category: bool = False,
        clear_announce_channel: bool = False,
    ) -> None:
        if not await require_staff(interaction):
            return
        if not await self._database_ready(interaction):
            return
        guild = interaction.guild
        store = self.bot.store
        changed: dict[str, Any] = {}
        for key, value in (
            ("events_category_id", category),
            ("events_announce_channel_id", announce_channel),
            ("events_ping_role_id", ping_role),
            ("events_create_scheduled", create_scheduled),
            ("events_channel_retention_days", retention_days),
            ("events_max_late_minutes", max_late_minutes),
            ("events_mode", mode.value if mode is not None else None),
        ):
            if value is not None:
                changed[key] = await store.set(guild.id, key, value, by=interaction.user.id)
        for wanted, key in (
            (clear_ping_role, "events_ping_role_id"),
            (clear_category, "events_category_id"),
            (clear_announce_channel, "events_announce_channel_id"),
        ):
            if wanted:
                await store.clear(guild.id, key)
                changed[key] = None
        category_id = store.get(guild.id, "events_category_id")
        announce_id = store.get(guild.id, "events_announce_channel_id")
        role_id = store.get(guild.id, "events_ping_role_id")
        lines = [
            f"**mode** — {store.get(guild.id, 'events_mode')}",
            "**category** — " + (f"<#{category_id}>" if category_id else "not set"),
            "**announce channel** — " + (f"<#{announce_id}>" if announce_id else "not set"),
            "**ping role** — " + (f"<@&{role_id}>" if role_id else "nobody"),
            f"**scheduled events** — {store.get(guild.id, 'events_create_scheduled')}",
            f"**channels kept** — {store.get(guild.id, 'events_channel_retention_days')} day(s)",
            f"**announced up to** — {store.get(guild.id, 'events_max_late_minutes')} minute(s) "
            "after it should have started",
            f"**staff (who may approve)** — "
            f"{staff_roles_sentence(store.staff_roles(guild))}",
            *self._health_lines(),
        ]
        await interaction.response.send_message(
            "\n".join(lines), ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )
        if changed:
            await log_action(
                self.bot,
                guild,
                "event.settings",
                actor=interaction.user,
                details=changed,
            )

    def _health_lines(self) -> list[str]:
        """Checklist 9: the loops report last success and last error, never `is_running`."""
        lines = []
        for name in LOOP_NAMES:
            ok = self.last_ok_at[name] or "never yet"
            broke = self.last_error[name]
            trouble = f" · last error {broke}" if broke else " · no errors"
            lines.append(f"**{name} loop** — last finished {ok}{trouble}")
        return lines

    async def _suggest_timezones(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return [app_commands.Choice(name=name, value=name) for name in suggest(current)][
            :CHOICE_LIMIT
        ]

    @timezone.command(name="set", description="Tell Black Bloc which time zone you are in")
    @app_commands.describe(tz="Start typing a city — Phoenix, London, Tokyo")
    @app_commands.autocomplete(tz=_suggest_timezones)
    async def timezone_set(self, interaction: discord.Interaction, tz: str) -> None:
        if not await self._database_ready(interaction):
            return
        name = tz.strip()
        if not is_known(name):
            await interaction.response.send_message(
                UNKNOWN_TZ.format(given=clamp(name, 60)),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        await set_timezone(self.bot.db, interaction.user.id, name)
        await interaction.response.send_message(
            TZ_SET.format(tz=name, now=local_time(name)),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @timezone.command(name="show", description="Show which time zone Black Bloc has for you")
    async def timezone_show(self, interaction: discord.Interaction) -> None:
        if not await self._database_ready(interaction):
            return
        chosen = await stored_timezone(self.bot.db, interaction.user.id)
        name = chosen or DEFAULT_TZ
        await interaction.response.send_message(
            (TZ_SHOW if chosen else TZ_SHOW_DEFAULT).format(tz=name, now=local_time(name)),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Events(bot))
