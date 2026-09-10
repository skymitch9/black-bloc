from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ... import raidtrain as rt
from ...actionlog import log_action, send_logs, stamp
from ...command_errors import NETWORK_ERRORS, AnswersErrors
from ...events import (
    TEXT_BUTTON,
    TEXT_MODAL_TITLE,
    ZONE_PANEL_BUTTON,
    ZONE_PANEL_INTRO,
    ZONE_PANEL_TITLE,
    clamp,
    guild_zone,
    minute_step,
    scheduled_name,
    stored_zone,
    zone_choices,
    zone_line,
)
from ...events import set_zone as store_zone
from ...golive import now_iso, parse_ts
from ...logkinds import VIA_DISCORD, kind_via
from ...loops import wait_ready
from ...panels import (
    SELECT_OPTION_LIMIT,
    NoteModal,
    Outcome,
    Panel,
    answer,
    capped_placeholder,
    clamped,
    db_up,
    refusal,
    retire,
    site_page_url,
    still_allowed,
    still_staff,
)
from ...panels import opened as panel_opened
from ...raidtrain import (
    CANCELLED,
    CAP_REACHED,
    DESCRIPTION_LIMIT,
    DONE,
    LIVE,
    LOCKED,
    NEEDS_LINK,
    NOT_YOURS,
    OPEN,
    OPEN_STATUSES,
    SLOT_TAKEN,
    SLOT_UNKNOWN,
    STATUS_WORDS,
    TITLE_LIMIT,
    TRAIN_FULL,
    TRAIN_LOCKED,
    cancelled_text,
    caps_ok,
    due_checkins,
    due_reminders,
    live_post_text,
    may_move,
    missed_reminders,
    move_refusal,
    neighbours,
    next_open_position,
    positions_word,
    reminder_text,
    render_lineup,
    slot_at,
    slot_times,
    slots_held,
)
from ...settings_store import (
    DB_UNAVAILABLE,
    GUILD_ONLY,
    RAIDTRAIN_MODES,
    RAIDTRAIN_SCHEDULED_NAME_KEY,
    RAIDTRAIN_SCHEDULED_NAME_TEMPLATE,
    SettingError,
    coerce_value,
)
from ...timezones import unix
from ...when_picker import DaySelect, HourSelect, MinuteSelect, WhenDraft, ZonePanel
from ...when_picker import ZoneModal as WhenZoneModal

log = logging.getLogger(__name__)

SWEEPS_BEFORE_DEGRADED = 3
CHOICE_LIMIT = 25
LIST_LIMIT = 20
MINE_LIMIT = 10

REFUSED = "raidtrain_refused"
NO_SUCH_SLOT_CODE = "no_such_slot"
SLOT_TAKEN_CODE = "slot_taken"
ALREADY_EMPTY_CODE = "already_empty"
NOT_LINKED_CODE = "not_linked"
BAD_MOVE_CODE = "bad_move"

NOT_AN_ORGANIZER = (
    "Building a raid train's lineup is for {who}, so nothing was changed. Ask one of them to "
    "make the change, or to give you the organizer role."
)
NO_SUCH_TRAIN = (
    "Black Bloc has no raid train **{train}** here any more, so nothing was done. Press "
    "**Refresh** and pick again."
)
NOTHING_UPCOMING = (
    "There is no raid train on the calendar right now. An organizer starts one with **Start a "
    "raid train**."
)
NOTHING_HELD = (
    "You do not hold a slot on any raid train. **Back** shows the ones that are coming up."
)
CREATED = (
    "**{title}** is up with {count} slot(s) of {minutes} minutes, starting <t:{when}:F>. "
    "{where} People claim an hour from `/raidtrain`."
)
LINEUP_HERE = "The lineup is in <#{channel_id}>."
LINEUP_NOWHERE = (
    "There is nowhere to put the lineup yet — a Lead picks a channel under **Setup…**, and until "
    "then the train only shows on the dashboard."
)
CLAIMED = (
    "Slot **#{position}** on **{title}** is yours — <t:{when}:F> (<t:{when}:R>). You will get a "
    "DM before it starts saying who raids into you and who you raid next."
)
CLAIMED_SHADOW = " Raid trains are in **shadow** at the moment, so no DM is actually sent."
RELEASED = (
    "Slot **#{position}** on **{title}** is open again, so somebody else can take that hour."
)
ASSIGNED = "Slot **#{position}** on **{title}** now belongs to {who}."
UNASSIGNED = "Slot **#{position}** on **{title}** is open again."
NOBODY_THERE = "Slot **#{position}** is already empty, so there was nothing to take off it."
SWAPPED = "Slots **#{a}** and **#{b}** on **{title}** have changed places."
SAME_SLOT = "Those are the same slot, so nothing was changed."
LOCKED_NOW = "**{title}** is locked — its lineup cannot be changed until it is unlocked."
UNLOCKED_NOW = "**{title}** is open for sign-ups again."
CANCELLED_NOW = "**{title}** is cancelled, and the {count} person/people who held a slot were told."
MEMBER_NOT_LINKED = (
    "**{who}** has no Twitch channel linked, so the lineup cannot say who to raid. They run "
    "`/golive` → **Link my Twitch channel**, or a Lead turns `raidtrain_require_link` off."
)
MODE_SET = "Raid trains are now **{mode}**.{extra}"
NO_CHANNEL_YET = (
    " Nothing has anywhere to be posted yet: neither `raidtrain_channel_id` nor "
    "`events_announce_channel_id` is set. **Setup…** fixes that."
)
SETUP_NOTHING = "Nothing was picked, so nothing changed."
SETUP_DONE = "Raid trains: {parts}."
SETUP_WORDS: dict[str, str] = {
    "raidtrain_channel_id": "lineups go to {}",
    "raidtrain_organizer_role_id": "organizers are {}",
    "raidtrain_ping_role_id": "{} is pinged",
}
SETUP_CLEARED: dict[str, str] = {
    "raidtrain_channel_id": "lineups have nowhere of their own again",
    "raidtrain_organizer_role_id": "only staff may build a lineup again",
    "raidtrain_ping_role_id": "nobody is pinged in front of a lineup",
}
MOVE_KINDS: dict[str, str] = {
    LOCKED: "raidtrain.lock",
    OPEN: "raidtrain.unlock",
    LIVE: "raidtrain.live",
    DONE: "raidtrain.done",
}
MOVED_NOW = "**{title}** is now **{status}**."


def _row(row: Any, key: str, fallback: Any = None) -> Any:
    if row is None:
        return fallback
    try:
        return row[key]
    except (IndexError, KeyError, TypeError):
        return fallback


async def create_train(
    db: Any,
    guild_id: int,
    organizer_id: int,
    *,
    title: str,
    description: str,
    starts_at: datetime,
    slot_minutes: int,
    slot_count: int,
) -> int:
    """One train and every one of its slots, so a swap never has to rewrite a time."""
    at = now_iso()
    cur = await db.conn.execute(
        "INSERT INTO raid_trains(guild_id, organizer_id, title, description, starts_at, "
        "slot_minutes, slot_count, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            guild_id,
            organizer_id,
            title,
            description or None,
            starts_at.astimezone(UTC).isoformat(),
            int(slot_minutes),
            int(slot_count),
            OPEN,
            at,
            at,
        ),
    )
    train_id = int(cur.lastrowid)
    for index, (start, finish) in enumerate(slot_times(starts_at, slot_minutes, slot_count), 1):
        await db.conn.execute(
            "INSERT INTO raid_slots(train_id, position, starts_at, ends_at) VALUES (?, ?, ?, ?)",
            (
                train_id,
                index,
                start.astimezone(UTC).isoformat(),
                finish.astimezone(UTC).isoformat(),
            ),
        )
    await db.conn.commit()
    return train_id


async def get_train(db: Any, guild_id: int, train_id: Any) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM raid_trains WHERE id = ? AND guild_id = ?", (int(train_id), guild_id)
    )
    return await cur.fetchone()


async def list_trains(db: Any, guild_id: int, *, scope: str = "upcoming") -> list[Any]:
    sql = "SELECT * FROM raid_trains WHERE guild_id = ?"
    params: tuple[Any, ...] = (guild_id,)
    if scope == "upcoming":
        sql += " AND status IN ({})".format(",".join("?" * len(OPEN_STATUSES)))
        params += OPEN_STATUSES
    elif scope == "past":
        sql += " AND status IN (?, ?)"
        params += (DONE, CANCELLED)
    cur = await db.conn.execute(sql + " ORDER BY starts_at, id", params)
    return list(await cur.fetchall())


async def slots_for(db: Any, train_id: Any) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM raid_slots WHERE train_id = ? ORDER BY position", (int(train_id),)
    )
    return list(await cur.fetchall())


async def slots_of_member(db: Any, guild_id: int, user_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT s.*, t.title AS train_title, t.id AS train_id, t.status AS train_status "
        "FROM raid_slots s JOIN raid_trains t ON t.id = s.train_id "
        "WHERE t.guild_id = ? AND s.user_id = ? AND t.status != ? ORDER BY s.starts_at",
        (guild_id, user_id, CANCELLED),
    )
    return list(await cur.fetchall())


async def take_slot(db: Any, slot_id: int, user_id: int, login: Any, by: int | None) -> bool:
    """False when another click already had it — the WHERE clause is the race guard."""
    cur = await db.conn.execute(
        "UPDATE raid_slots SET user_id = ?, twitch_login = ?, claimed_at = ?, assigned_by = ? "
        "WHERE id = ? AND user_id IS NULL",
        (user_id, login or None, now_iso(), by, int(slot_id)),
    )
    await db.conn.commit()
    return bool(cur.rowcount)


async def empty_slot(db: Any, slot_id: int) -> bool:
    cur = await db.conn.execute(
        "UPDATE raid_slots SET user_id = NULL, twitch_login = NULL, claimed_at = NULL, "
        "assigned_by = NULL, reminded_at = NULL, checked_in_at = NULL, live_posted_at = NULL "
        "WHERE id = ? AND user_id IS NOT NULL",
        (int(slot_id),),
    )
    await db.conn.commit()
    return bool(cur.rowcount)


async def swap_holders(db: Any, first: Any, second: Any) -> None:
    """Only who is in the seat moves; the times belong to the position, not to the person."""
    carried = ("user_id", "twitch_login", "claimed_at", "assigned_by", "reminded_at")
    for target, source in ((first, second), (second, first)):
        await db.conn.execute(
            "UPDATE raid_slots SET "
            + ", ".join(f"{name} = ?" for name in carried)
            + " WHERE id = ?",
            tuple(_row(source, name) for name in carried) + (int(_row(target, "id")),),
        )
    await db.conn.commit()


async def set_status(db: Any, train_id: int, status: str, *, reason: Any = None) -> None:
    await db.conn.execute(
        "UPDATE raid_trains SET status = ?, cancel_reason = ?, updated_at = ? WHERE id = ?",
        (status, reason, now_iso(), int(train_id)),
    )
    await db.conn.commit()


async def set_lineup(
    db: Any,
    train_id: int,
    *,
    channel_id: int | None = None,
    message_id: int | None = None,
    thread_id: int | None = None,
    scheduled_event_id: int | None = None,
) -> None:
    await db.conn.execute(
        "UPDATE raid_trains SET channel_id = COALESCE(?, channel_id), "
        "lineup_message_id = COALESCE(?, lineup_message_id), "
        "thread_id = COALESCE(?, thread_id), "
        "scheduled_event_id = COALESCE(?, scheduled_event_id), updated_at = ? WHERE id = ?",
        (channel_id, message_id, thread_id, scheduled_event_id, now_iso(), int(train_id)),
    )
    await db.conn.commit()


async def stamp_slot(db: Any, slot_id: int, column: str) -> None:
    if column not in ("reminded_at", "checked_in_at", "live_posted_at"):
        raise ValueError(f"raid slots have no {column!r} to stamp")
    await db.conn.execute(
        f"UPDATE raid_slots SET {column} = ? WHERE id = ?", (now_iso(), int(slot_id))
    )
    await db.conn.commit()


async def twitch_login_of(db: Any, user_id: int) -> str | None:
    cur = await db.conn.execute(
        "SELECT twitch_login FROM golive_links WHERE user_id = ?", (int(user_id),)
    )
    row = await cur.fetchone()
    return str(row["twitch_login"]) if row else None


async def counts(db: Any, guild_id: int) -> dict[str, int]:
    async def scalar(sql: str, params: tuple[Any, ...]) -> int:
        cur = await db.conn.execute(sql, params)
        row = await cur.fetchone()
        return int(row["n"]) if row else 0

    marks = ",".join("?" * len(OPEN_STATUSES))
    return {
        "trains": await scalar(
            "SELECT COUNT(*) AS n FROM raid_trains WHERE guild_id = ?", (guild_id,)
        ),
        "upcoming": await scalar(
            f"SELECT COUNT(*) AS n FROM raid_trains WHERE guild_id = ? AND status IN ({marks})",
            (guild_id, *OPEN_STATUSES),
        ),
        "slots": await scalar(
            "SELECT COUNT(*) AS n FROM raid_slots s JOIN raid_trains t ON t.id = s.train_id "
            "WHERE t.guild_id = ?",
            (guild_id,),
        ),
        "claimed": await scalar(
            "SELECT COUNT(*) AS n FROM raid_slots s JOIN raid_trains t ON t.id = s.train_id "
            "WHERE t.guild_id = ? AND s.user_id IS NOT NULL",
            (guild_id,),
        ),
    }


async def dm(user: Any, text: str) -> bool:
    """Whether the person actually got told; DMs are the one place test mode leaves alone."""
    send = getattr(user, "send", None)
    if send is None:
        return False
    try:
        await send(text, allowed_mentions=discord.AllowedMentions.none())
    except Exception as exc:
        log.info("raidtrain: could not DM %s: %s", getattr(user, "id", "?"), exc)
        return False
    return True


# --- one function per move, called by BOTH doors -------------------------------------------------


def raid_cog(bot: Any) -> Any:
    getter = getattr(bot, "get_cog", None)
    return getter("RaidTrains") if callable(getter) else None


async def redraw(bot: Any, guild: Any, train_id: Any) -> None:
    """The lineup post is cosmetics: a failure here must never undo a committed claim."""
    cog = raid_cog(bot)
    if cog is None:
        return
    await cog._refresh_lineup(guild, int(train_id))


def mode_of(bot: Any, guild_id: int) -> str:
    return str(bot.store.get(guild_id, "raidtrain_mode"))


def actor_id(actor: Any) -> int | None:
    return int(getattr(actor, "id", actor) or 0) or None


def shadow_tail(bot: Any, guild: Any) -> str:
    return "" if mode_of(bot, guild.id) == "on" else CLAIMED_SHADOW


async def claim_slot(
    bot: Any,
    guild: Any,
    actor: Any,
    train: Any,
    position: Any,
    login: Any,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """The caller holds the train's lock; `take_slot`'s WHERE clause is the second half of it."""
    if str(train["status"]) != OPEN:
        return refusal(TRAIN_LOCKED.format(title=train["title"]), REFUSED, 409)
    who = actor_id(actor)
    slots = await slots_for(bot.db, train["id"])
    ceiling = bot.store.get(guild.id, "raidtrain_max_slots_per_member")
    if not caps_ok(slots, who, ceiling):
        return refusal(
            CAP_REACHED.format(held=len(slots_held(slots, who)), title=train["title"]),
            REFUSED,
            409,
        )
    if position is None:
        position = next_open_position(slots)
        if position is None:
            return refusal(TRAIN_FULL.format(title=train["title"]), REFUSED, 409)
    wanted = slot_at(slots, position)
    if wanted is None:
        return refusal(
            SLOT_UNKNOWN.format(position=position, last=len(slots)), NO_SUCH_SLOT_CODE, 404
        )
    if not await take_slot(bot.db, wanted["id"], who, login, None):
        return refusal(SLOT_TAKEN.format(position=position), SLOT_TAKEN_CODE, 409)
    await log_action(
        bot,
        guild,
        kind_via("raidtrain.claim", via),
        actor=actor,
        target=actor,
        details={
            "train_id": train["id"],
            "position": int(position),
            "twitch_login": login,
            "via": via,
        },
    )
    await redraw(bot, guild, train["id"])
    start = parse_ts(wanted["starts_at"])
    said = CLAIMED.format(
        position=position,
        title=train["title"],
        when=unix(start) if start is not None else 0,
    )
    return Outcome(True, said + shadow_tail(bot, guild), value=int(position))


async def release_slot(
    bot: Any, guild: Any, actor: Any, train: Any, position: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    if str(train["status"]) != OPEN:
        return refusal(TRAIN_LOCKED.format(title=train["title"]), REFUSED, 409)
    who = actor_id(actor)
    slots = await slots_for(bot.db, train["id"])
    mine = slots_held(slots, who)
    wanted = slot_at(slots, position) if position is not None else (mine[0] if mine else None)
    if wanted is None or wanted["user_id"] != who:
        return refusal(
            NOT_YOURS.format(position=position if position is not None else "—"), REFUSED, 409
        )
    await empty_slot(bot.db, wanted["id"])
    await log_action(
        bot,
        guild,
        kind_via("raidtrain.release", via),
        actor=actor,
        target=actor,
        details={"train_id": train["id"], "position": wanted["position"], "via": via},
    )
    await redraw(bot, guild, train["id"])
    return Outcome(
        True,
        RELEASED.format(position=wanted["position"], title=train["title"]),
        value=int(wanted["position"]),
    )


async def assign_slot(
    bot: Any,
    guild: Any,
    actor: Any,
    train: Any,
    position: Any,
    member: Any,
    login: Any,
    *,
    named: Any = None,
    via: str = VIA_DISCORD,
) -> Outcome:
    """Assigning ignores the per-member ceiling on purpose — an organizer outranks it."""
    member_id = actor_id(member)
    who = str(named or getattr(member, "display_name", "") or f"member {member_id}")
    if not login and bot.store.get(guild.id, "raidtrain_require_link"):
        return refusal(MEMBER_NOT_LINKED.format(who=who), NOT_LINKED_CODE, 409)
    slots = await slots_for(bot.db, train["id"])
    wanted = slot_at(slots, position)
    if wanted is None:
        return refusal(
            SLOT_UNKNOWN.format(position=position, last=len(slots)), NO_SUCH_SLOT_CODE, 404
        )
    if wanted["user_id"] is not None:
        await empty_slot(bot.db, wanted["id"])
    if not await take_slot(bot.db, wanted["id"], member_id, login, actor_id(actor)):
        return refusal(SLOT_TAKEN.format(position=position), SLOT_TAKEN_CODE, 409)
    await log_action(
        bot,
        guild,
        kind_via("raidtrain.assign", via),
        actor=actor,
        target=member_id,
        details={
            "train_id": train["id"],
            "position": int(position),
            "twitch_login": login,
            "via": via,
        },
    )
    await redraw(bot, guild, train["id"])
    return Outcome(
        True,
        ASSIGNED.format(position=position, title=train["title"], who=who),
        value=int(position),
    )


async def unassign_slot(
    bot: Any, guild: Any, actor: Any, train: Any, position: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    slots = await slots_for(bot.db, train["id"])
    wanted = slot_at(slots, position)
    if wanted is None:
        return refusal(
            SLOT_UNKNOWN.format(position=position, last=len(slots)), NO_SUCH_SLOT_CODE, 404
        )
    held_by = wanted["user_id"]
    if not await empty_slot(bot.db, wanted["id"]):
        return refusal(NOBODY_THERE.format(position=position), ALREADY_EMPTY_CODE, 409)
    await log_action(
        bot,
        guild,
        kind_via("raidtrain.unassign", via),
        actor=actor,
        target=held_by,
        details={"train_id": train["id"], "position": int(position), "via": via},
    )
    await redraw(bot, guild, train["id"])
    return Outcome(
        True,
        UNASSIGNED.format(position=position, title=train["title"]),
        value=int(position),
    )


async def swap_slots(
    bot: Any, guild: Any, actor: Any, train: Any, first: Any, second: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    if int(first) == int(second):
        return refusal(SAME_SLOT, REFUSED, 400)
    slots = await slots_for(bot.db, train["id"])
    one, other = slot_at(slots, first), slot_at(slots, second)
    if one is None or other is None:
        return refusal(
            SLOT_UNKNOWN.format(position=first if one is None else second, last=len(slots)),
            NO_SUCH_SLOT_CODE,
            404,
        )
    await swap_holders(bot.db, one, other)
    await log_action(
        bot,
        guild,
        kind_via("raidtrain.swap", via),
        actor=actor,
        details={"train_id": train["id"], "a": int(first), "b": int(second), "via": via},
    )
    await redraw(bot, guild, train["id"])
    return Outcome(True, SWAPPED.format(a=first, b=second, title=train["title"]))


async def move_train(
    bot: Any, guild: Any, actor: Any, train: Any, to: str, *, via: str = VIA_DISCORD
) -> Outcome:
    """Lock, unlock and the two the clock walks — one function, one transition table."""
    if not may_move(train["status"], to):
        return refusal(move_refusal(train["status"], to), BAD_MOVE_CODE, 409)
    await set_status(bot.db, train["id"], to)
    await log_action(
        bot,
        guild,
        kind_via(MOVE_KINDS[to], via),
        actor=actor,
        details={"train_id": train["id"], "title": train["title"], "via": via},
    )
    await redraw(bot, guild, train["id"])
    if to == LOCKED:
        said = LOCKED_NOW.format(title=train["title"])
    elif to == OPEN:
        said = UNLOCKED_NOW.format(title=train["title"])
    else:
        said = MOVED_NOW.format(title=train["title"], status=to)
    return Outcome(True, said, value=to)


async def create_and_publish(
    bot: Any,
    guild: Any,
    actor: Any,
    *,
    title: str,
    description: str,
    starts_at: datetime,
    slot_minutes: int,
    slot_count: int,
    via: str = VIA_DISCORD,
) -> Outcome:
    train_id = await create_train(
        bot.db,
        guild.id,
        actor_id(actor) or 0,
        title=title,
        description=description,
        starts_at=starts_at,
        slot_minutes=slot_minutes,
        slot_count=slot_count,
    )
    await log_action(
        bot,
        guild,
        kind_via("raidtrain.create", via),
        actor=actor,
        details={
            "train_id": train_id,
            "title": title,
            "slot_minutes": slot_minutes,
            "slot_count": slot_count,
            "starts_at": starts_at.isoformat(),
            "via": via,
        },
    )
    cog = raid_cog(bot)
    if cog is not None:
        await cog.publish_lineup(guild, train_id)
    channel_id = lineup_channel(bot, guild.id)
    where = LINEUP_HERE.format(channel_id=channel_id) if channel_id else LINEUP_NOWHERE
    return Outcome(
        True,
        CREATED.format(
            title=title,
            count=slot_count,
            minutes=slot_minutes,
            when=unix(starts_at),
            where=where,
        ),
        value=train_id,
    )


def lineup_channel(bot: Any, guild_id: int) -> int | None:
    """D7: blank means the events announcement channel, so one place is set up, not two."""
    store = bot.store
    return store.get(guild_id, "raidtrain_channel_id") or store.get(
        guild_id, "events_announce_channel_id"
    )


async def set_mode(
    bot: Any, guild: Any, actor: Any, value: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    try:
        wanted = coerce_value("raidtrain_mode", value)
    except SettingError as exc:
        return refusal(str(exc), REFUSED, 400)
    await bot.store.set(guild.id, "raidtrain_mode", wanted, by=actor_id(actor))
    await log_action(
        bot,
        guild,
        kind_via("raidtrain.mode", via),
        actor=actor,
        details={"mode": wanted, "via": via},
    )
    extra = "" if lineup_channel(bot, guild.id) else NO_CHANNEL_YET
    return Outcome(True, MODE_SET.format(mode=wanted, extra=extra), value=wanted)


async def save_setup(
    bot: Any, guild: Any, actor: Any, fields: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Every field is read before the first write, so a bad one saves none of the others."""
    wanted = {key: value for key, value in (fields or {}).items() if key in SETUP_WORDS}
    if not wanted:
        return refusal(SETUP_NOTHING, REFUSED, 400)
    for key, value in wanted.items():
        if value is None:
            continue
        try:
            coerce_value(key, value)
        except SettingError as exc:
            return refusal(str(exc), REFUSED, 400)
    by = actor_id(actor)
    parts = []
    for key, value in wanted.items():
        if value is None:
            await bot.store.clear(guild.id, key, by=by)
            parts.append(SETUP_CLEARED[key])
            continue
        await bot.store.set(guild.id, key, coerce_value(key, value), by=by)
        parts.append(SETUP_WORDS[key].format(getattr(value, "mention", value)))
    await log_action(
        bot,
        guild,
        kind_via("raidtrain.setup", via),
        actor=actor,
        details={
            "changed": {
                key: (None if value is None else int(coerce_value(key, value)))
                for key, value in wanted.items()
            },
            "via": via,
        },
    )
    return Outcome(True, SETUP_DONE.format(parts=", ".join(parts)), value=wanted)


# --- what renders --------------------------------------------------------------------------------


ROOT = "root"
CARD = "card"
MINE_VIEW = "mine"
SETUP_VIEW = "setup"
PUT_IN_VIEW = "put_in"
SWAP_VIEW = "swap"
GIVE_BACK_VIEW = "give_back"

SELECT_CAP = 25
MODAL_TITLE_LIMIT = 45
DRAFT_BUTTON_ROW = 3

DO_CLAIM = "do_claim"
DO_UNASSIGN = "do_unassign"
DO_RELEASE = "do_release"
DO_FIRST = "do_first"
DO_SECOND = "do_second"
DO_SEAT = "do_seat"

STYLES = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}

SITE_BUTTON = "Open on the site"
CARD_TITLE = "Raid train #{train_id}"
MINE_TITLE = "The hours you hold"
SETUP_TITLE = "Where lineups go, and who may run them"
PUT_IN_TITLE = "Put somebody in"
SWAP_TITLE = "Change two slots round"
GIVE_BACK_TITLE = "Give an hour back"
CANCEL_TITLE = "Call off {title}"
CANCEL_LABEL = "What the people who signed up are told"
LINK_FIRST = "Before you can take an hour"

TRAIN_PLACEHOLDER = "A train…"
TRAIN_CAPPED = "{shown} of {total} — the rest are on the Events page"
MODE_PLACEHOLDER = "Mode…"
CLAIM_PLACEHOLDER = "Take an hour…"
TAKE_OFF_PLACEHOLDER = "Take somebody off…"
SLOT_PLACEHOLDER = "Which slot…"
FIRST_PLACEHOLDER = "First…"
SECOND_PLACEHOLDER = "Second…"
HOUR_PLACEHOLDER = "Which hour…"
WHO_PLACEHOLDER = "Who takes it?"
CHANNEL_PLACEHOLDER = "Where the lineup post lives"
ORGANIZER_PLACEHOLDER = "Who may build a lineup, besides staff"
PING_PLACEHOLDER = "Who is pinged in front of a lineup"
CLEAR_PLACEHOLDER = "Clear…"

MODE_LINE = "Raid trains are **{mode}**."
SHADOW_LINE = (
    "In **shadow** every move is recorded and the lineup post and the DMs are held back."
)
OFF_LINE = "Raid trains are **off**, so nothing new can be started."
OFF_LINE_STAFF = " **Mode…** below is how a Lead turns them on."
TRAIN_LINE = (
    "**#{train_id} {title}** — {when} · {taken}/{total} filled · {status} · open: {free}"
)
LINEUP_CHANNEL = "Lineups go to <#{channel_id}>."
SWEEP_LINE = (
    "The sweep runs every {every} minute(s): {running}, last clean pass {ok}, "
    "{failures} failure(s) in a row."
)
SWEEP_RUNNING = "running"
SWEEP_STOPPED = "**not running**"
SWEEP_NEVER = "never"
SWEEP_TROUBLE = "The last sweep did not finish: {why}."
TOTALS_LINE = (
    "{trains} train(s), {upcoming} still to come · {claimed} of {slots} hour(s) claimed."
)
MINE_LINE = "**#{train_id} {title}** — slot #{position}, {when}"
SETUP_CHANNEL_NOW = "The lineup post goes to {where}."
SETUP_ORGANIZER_NOW = "Organizers are {who}."
SETUP_PING_NOW = "The lineup pings {who}."
SETUP_UNSET = "nobody yet"
SETUP_HOW = (
    "Pick what you want to change and press **Save**. **Clear…** empties one of them again."
)
SETUP_LABELS: dict[str, str] = {
    "raidtrain_channel_id": "The lineup channel",
    "raidtrain_organizer_role_id": "The organizer role",
    "raidtrain_ping_role_id": "The ping role",
}
PUT_IN_HOW = "Pick the hour and the person, then press **Put them in**."
PUT_IN_PICKED = "Hour **#{slot}**, {who}."
PUT_IN_NEEDS_BOTH = "Pick an hour and a person first, then press **Put them in**."
SWAP_HOW = "Pick two hours, then press **Swap them**. The people move; the times do not."
SWAP_PICKED = "First **#{first}**, second **{second}**."
SWAP_NEEDS_BOTH = "Pick two hours first, then press **Swap them**."
GIVE_BACK_HOW = "Pick the hour you would rather not keep. It opens again for somebody else."
NOT_ON_THIS_TRAIN = "You do not hold an hour on this train any more, so nothing was given back."


class RaidPanel(Panel):
    def __init__(self, minutes: int) -> None:
        super().__init__(minutes, footer=rt.PANEL_TIMEOUT_FOOTER)
        self.where = ROOT
        self.train_id: int | None = None
        self.first: int | None = None
        self.second: int | None = None
        self.member_id: int | None = None
        self.setup: dict[str, Any] = {}


def minutes_for(bot: Any, guild_id: int) -> int:
    return rt.panel_minutes(bot.store, guild_id)


def is_organizer(bot: Any, member: Any) -> bool:
    """Staff OR the configured role — three audiences from one command, not two."""
    guild = getattr(member, "guild", None)
    if guild is None:
        return False
    role_id = bot.store.get(guild.id, "raidtrain_organizer_role_id")
    if role_id and any(
        int(getattr(role, "id", 0)) == int(role_id) for role in getattr(member, "roles", ())
    ):
        return True
    return bool(bot.store.is_staff(member))


def organizer_words(bot: Any, guild: Any) -> str:
    role_id = bot.store.get(guild.id, "raidtrain_organizer_role_id")
    return f"staff or <@&{role_id}>" if role_id else "staff"


async def still_organizer(interaction: discord.Interaction) -> bool:
    bot = interaction.client
    return await still_allowed(
        interaction,
        is_organizer(bot, interaction.user),
        NOT_AN_ORGANIZER.format(who=organizer_words(bot, interaction.guild)),
    )


def add_site_button(view: Any, bot: Any, row: int) -> None:
    """No origin, no button — and it is staff-only, because every route behind it is."""
    url = site_page_url(getattr(getattr(bot, "settings", None), "origin", ""), "raidtrain")
    if not url:
        return
    view.add_item(
        discord.ui.Button(style=discord.ButtonStyle.link, label=SITE_BUTTON, url=url, row=row)
    )


def names_in(guild: Any, slots: Any) -> dict[int, str]:
    found: dict[int, str] = {}
    for slot in slots or ():
        user_id = slot["user_id"]
        if user_id is None:
            continue
        member = guild.get_member(int(user_id))
        if member is not None:
            found[int(user_id)] = str(getattr(member, "display_name", ""))
    return found


async def train_lines(bot: Any, rows: Any) -> list[str]:
    lines = []
    for train in list(rows)[:LIST_LIMIT]:
        slots = await slots_for(bot.db, train["id"])
        start = parse_ts(train["starts_at"])
        lines.append(
            TRAIN_LINE.format(
                train_id=train["id"],
                title=train["title"],
                when=f"<t:{unix(start)}:F>" if start is not None else train["starts_at"],
                taken=len([one for one in slots if one["user_id"] is not None]),
                total=len(slots),
                status=STATUS_WORDS.get(str(train["status"]), train["status"]),
                free=positions_word(slots),
            )
        )
    return lines


async def staff_lines(bot: Any, guild: Any) -> list[str]:
    """The status route's own shape, written out always — a warning behind a button is lost."""
    cog = raid_cog(bot)
    channel_id = lineup_channel(bot, guild.id)
    ok_at, error = cog.loop_health("sweep") if cog is not None else (None, None)
    lines = [
        LINEUP_CHANNEL.format(channel_id=channel_id) if channel_id else NO_CHANNEL_YET.strip(),
        SWEEP_LINE.format(
            every=bot.store.get(guild.id, "raidtrain_poll_minutes"),
            running=(
                SWEEP_RUNNING
                if cog is not None and cog.sweep.is_running()
                else SWEEP_STOPPED
            ),
            ok=stamp(ok_at) if ok_at else SWEEP_NEVER,
            failures=int(getattr(cog, "sweep_failures", 0) or 0),
        ),
    ]
    if error:
        lines.append(SWEEP_TROUBLE.format(why=error))
    totals = await counts(bot.db, guild.id)
    lines.append(TOTALS_LINE.format(**totals))
    return lines


async def root_lines(bot: Any, guild: Any, rows: Any, *, mode: str, staff: bool) -> list[str]:
    lines = [MODE_LINE.format(mode=mode)]
    if mode == rt.MODE_OFF:
        lines.append(OFF_LINE + (OFF_LINE_STAFF if staff else ""))
    elif mode == "shadow":
        lines.append(SHADOW_LINE)
    lines.append("")
    lines.extend(await train_lines(bot, rows) or [NOTHING_UPCOMING])
    if staff:
        lines.append("")
        lines.extend(await staff_lines(bot, guild))
    return lines


async def build_panel(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, RaidPanel]:
    """One command, three audiences: member, organizer and staff, split at render time."""
    staff = bool(bot.store.is_staff(actor))
    organizer = is_organizer(bot, actor)
    mode = mode_of(bot, guild.id)
    rows = await list_trains(bot.db, guild.id, scope="upcoming")
    mine = await slots_of_member(bot.db, guild.id, actor.id)
    embed = discord.Embed(
        title=rt.PANEL_TITLE,
        description=clamped(await root_lines(bot, guild, rows, mode=mode, staff=staff)),
    )
    view = RaidPanel(minutes_for(bot, guild.id))
    picks = rt.root_selects(staff=staff, has_trains=bool(rows))
    if rt.TRAIN_SELECT in picks:
        view.add_item(TrainPick(rt.train_options(rows), placeholder=TRAIN_PLACEHOLDER, row=0))
    if rt.MODE_SELECT in picks:
        view.add_item(ModePick(mode, row=1))
    for move in rt.root_buttons(
        organizer=organizer, staff=staff, holds_any=bool(mine), mode=mode
    ):
        view.add_item(MoveButton(move))
    if staff:
        add_site_button(view, bot, row=3)
    return (embed, view)


async def build_card(
    bot: Any, guild: Any, actor: Any, train_id: Any
) -> tuple[discord.Embed | None, RaidPanel | None]:
    train = await get_train(bot.db, guild.id, train_id)
    if train is None:
        return (None, None)
    slots = await slots_for(bot.db, train["id"])
    organizer = is_organizer(bot, actor)
    login = await twitch_login_of(bot.db, actor.id)
    require = bool(bot.store.get(guild.id, "raidtrain_require_link"))
    embed = discord.Embed(
        title=CARD_TITLE.format(train_id=train["id"]),
        description=clamped(render_lineup(train, slots).split("\n")),
    )
    if require and not login and str(train["status"]) == OPEN:
        embed.add_field(name=LINK_FIRST, value=NEEDS_LINK, inline=False)
    view = RaidPanel(minutes_for(bot, guild.id))
    view.where = CARD
    view.train_id = int(train["id"])
    picks = rt.card_selects(
        train["status"],
        organizer=organizer,
        claimable=rt.may_claim(
            train,
            slots,
            actor.id,
            ceiling=bot.store.get(guild.id, "raidtrain_max_slots_per_member"),
            linked=bool(login),
            require_link=require,
        ),
        has_taken=bool(rt.taken_positions(slots)),
    )
    if rt.CLAIM_SELECT in picks:
        view.add_item(SlotPick(slots, rt.OPEN_SLOTS, CLAIM_PLACEHOLDER, DO_CLAIM, row=0))
    if rt.TAKE_OFF_SELECT in picks:
        view.add_item(
            SlotPick(
                slots,
                rt.TAKEN_SLOTS,
                TAKE_OFF_PLACEHOLDER,
                DO_UNASSIGN,
                row=1,
                names=names_in(guild, slots),
            )
        )
    for move in rt.card_buttons(
        train["status"],
        organizer=organizer,
        held=[one["position"] for one in slots_held(slots, actor.id)],
        slot_count=len(slots),
    ):
        view.add_item(MoveButton(move))
    return (embed, view)


async def build_mine(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, RaidPanel]:
    """Cross-train, so it cannot live on a card: the hours you hold, wherever they are."""
    rows = await slots_of_member(bot.db, guild.id, actor.id)
    lines = []
    for row in rows[:MINE_LIMIT]:
        start = parse_ts(row["starts_at"])
        lines.append(
            MINE_LINE.format(
                train_id=row["train_id"],
                title=row["train_title"],
                position=row["position"],
                when=(
                    f"<t:{unix(start)}:F> (<t:{unix(start)}:R>)"
                    if start is not None
                    else row["starts_at"]
                ),
            )
        )
    embed = discord.Embed(title=MINE_TITLE, description=clamped(lines or [NOTHING_HELD]))
    view = RaidPanel(minutes_for(bot, guild.id))
    view.where = MINE_VIEW
    if rows:
        view.add_item(TrainPick(rt.mine_options(rows), placeholder=TRAIN_PLACEHOLDER, row=0))
    view.add_item(MoveButton(rt.BACK_MOVE._replace(row=1)))
    return (embed, view)


def setup_lines(bot: Any, guild: Any) -> list[str]:
    store = bot.store
    channel_id = store.get(guild.id, "raidtrain_channel_id")
    organizer_id = store.get(guild.id, "raidtrain_organizer_role_id")
    ping_id = store.get(guild.id, "raidtrain_ping_role_id")
    return [
        SETUP_CHANNEL_NOW.format(
            where=f"<#{channel_id}>" if channel_id else SETUP_UNSET
        ),
        SETUP_ORGANIZER_NOW.format(
            who=f"staff and <@&{organizer_id}>" if organizer_id else "staff only"
        ),
        SETUP_PING_NOW.format(who=f"<@&{ping_id}>" if ping_id else SETUP_UNSET),
        "",
        SETUP_HOW,
    ]


def set_keys(bot: Any, guild: Any) -> list[str]:
    return [key for key in SETUP_WORDS if bot.store.get(guild.id, key)]


def build_setup(bot: Any, guild: Any) -> tuple[discord.Embed, RaidPanel]:
    """Five rows is Discord's ceiling, so nothing else may ever join this sub-panel."""
    embed = discord.Embed(title=SETUP_TITLE, description=clamped(setup_lines(bot, guild)))
    view = RaidPanel(minutes_for(bot, guild.id))
    view.where = SETUP_VIEW
    view.add_item(LineupChannelPick(row=0))
    view.add_item(SetupRolePick("raidtrain_organizer_role_id", ORGANIZER_PLACEHOLDER, row=1))
    view.add_item(SetupRolePick("raidtrain_ping_role_id", PING_PLACEHOLDER, row=2))
    already = set_keys(bot, guild)
    if already:
        view.add_item(ClearPick(already, row=3))
    view.add_item(MoveButton(rt.SAVE_MOVE))
    view.add_item(MoveButton(rt.BACK_MOVE._replace(row=4)))
    return (embed, view)


async def build_put_in(
    bot: Any, guild: Any, previous: Any
) -> tuple[discord.Embed | None, RaidPanel | None]:
    train = await get_train(bot.db, guild.id, previous.train_id)
    if train is None:
        return (None, None)
    slots = await slots_for(bot.db, train["id"])
    said = [PUT_IN_HOW]
    if previous.first is not None or previous.member_id is not None:
        said.append(
            PUT_IN_PICKED.format(
                slot=previous.first if previous.first is not None else "—",
                who=f"<@{previous.member_id}>" if previous.member_id else "nobody yet",
            )
        )
    embed = discord.Embed(title=PUT_IN_TITLE, description=clamped(said))
    view = RaidPanel(minutes_for(bot, guild.id))
    view.where = PUT_IN_VIEW
    view.train_id = int(train["id"])
    view.first = previous.first
    view.member_id = previous.member_id
    view.add_item(
        SlotPick(
            slots,
            rt.ALL_SLOTS,
            SLOT_PLACEHOLDER,
            DO_SEAT,
            row=0,
            names=names_in(guild, slots),
        )
    )
    view.add_item(WhoPick(row=1))
    view.add_item(MoveButton(rt.PUT_THEM_IN_MOVE))
    view.add_item(MoveButton(rt.BACK_MOVE._replace(row=2)))
    return (embed, view)


async def build_swap(
    bot: Any, guild: Any, previous: Any
) -> tuple[discord.Embed | None, RaidPanel | None]:
    train = await get_train(bot.db, guild.id, previous.train_id)
    if train is None:
        return (None, None)
    slots = await slots_for(bot.db, train["id"])
    said = [SWAP_HOW]
    if previous.first is not None:
        said.append(
            SWAP_PICKED.format(
                first=previous.first,
                second=f"#{previous.second}" if previous.second is not None else "nothing yet",
            )
        )
    embed = discord.Embed(title=SWAP_TITLE, description=clamped(said))
    view = RaidPanel(minutes_for(bot, guild.id))
    view.where = SWAP_VIEW
    view.train_id = int(train["id"])
    view.first = previous.first
    view.second = previous.second
    named = names_in(guild, slots)
    view.add_item(
        SlotPick(slots, rt.ALL_SLOTS, FIRST_PLACEHOLDER, DO_FIRST, row=0, names=named)
    )
    if previous.first is not None:
        rest = [one for one in slots if int(one["position"]) != int(previous.first)]
        view.add_item(
            SlotPick(rest, rt.ALL_SLOTS, SECOND_PLACEHOLDER, DO_SECOND, row=1, names=named)
        )
    view.add_item(MoveButton(rt.SWAP_THEM_MOVE))
    view.add_item(MoveButton(rt.BACK_MOVE._replace(row=2)))
    return (embed, view)


async def build_give_back(
    bot: Any, guild: Any, actor: Any, previous: Any
) -> tuple[discord.Embed | None, RaidPanel | None]:
    train = await get_train(bot.db, guild.id, previous.train_id)
    if train is None:
        return (None, None)
    slots = await slots_for(bot.db, train["id"])
    mine = slots_held(slots, actor.id)
    embed = discord.Embed(
        title=GIVE_BACK_TITLE, description=clamped([GIVE_BACK_HOW if mine else NOT_ON_THIS_TRAIN])
    )
    view = RaidPanel(minutes_for(bot, guild.id))
    view.where = GIVE_BACK_VIEW
    view.train_id = int(train["id"])
    if mine:
        view.add_item(SlotPick(mine, rt.ALL_SLOTS, HOUR_PLACEHOLDER, DO_RELEASE, row=0))
    view.add_item(MoveButton(rt.BACK_MOVE._replace(row=1)))
    return (embed, view)


# --- rendering -----------------------------------------------------------------------------------


async def render(interaction: discord.Interaction, embed: Any, view: Any, previous: Any) -> None:
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def render_root(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = await build_panel(interaction.client, interaction.guild, interaction.user)
    await render(interaction, embed, view, previous)


async def render_card(
    interaction: discord.Interaction, train_id: Any, previous: Any = None
) -> None:
    embed, view = await build_card(
        interaction.client, interaction.guild, interaction.user, train_id
    )
    if view is None:
        await render_root(interaction, previous)
        await answer(interaction, NO_SUCH_TRAIN.format(train=str(train_id)[:40]))
        return
    await render(interaction, embed, view, previous)


async def render_mine(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = await build_mine(interaction.client, interaction.guild, interaction.user)
    await render(interaction, embed, view, previous)


async def render_setup(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = build_setup(interaction.client, interaction.guild)
    await render(interaction, embed, view, previous)


async def render_sub(interaction: discord.Interaction, view: Any, where: str) -> None:
    """The three organizer sub-panels; a train that vanished lands back on the root."""
    bot, guild = interaction.client, interaction.guild
    if where == PUT_IN_VIEW:
        embed, fresh = await build_put_in(bot, guild, view)
    elif where == SWAP_VIEW:
        embed, fresh = await build_swap(bot, guild, view)
    else:
        embed, fresh = await build_give_back(bot, guild, interaction.user, view)
    if fresh is None:
        await render_root(interaction, view)
        await answer(interaction, NO_SUCH_TRAIN.format(train=str(view.train_id)))
        return
    await render(interaction, embed, fresh, view)


async def opened(interaction: discord.Interaction) -> bool:
    """Three audiences share this panel, so the defer and the database ask with no staff gate."""
    return await panel_opened(interaction, staff=False)


async def open_root(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    await render_root(interaction, previous)


async def open_card(
    interaction: discord.Interaction, train_id: Any, previous: Any = None
) -> None:
    if not await opened(interaction):
        return
    await render_card(interaction, train_id, previous)


async def open_mine(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    await render_mine(interaction, previous)


async def open_setup(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction):
        return
    await render_setup(interaction, previous)


async def open_sub(interaction: discord.Interaction, view: Any, where: str) -> None:
    if where != GIVE_BACK_VIEW and not await still_organizer(interaction):
        return
    if not await opened(interaction):
        return
    await render_sub(interaction, view, where)


async def refresh_where(interaction: discord.Interaction, view: Any) -> None:
    if view.where == CARD:
        await open_card(interaction, view.train_id, view)
        return
    if view.where == MINE_VIEW:
        await open_mine(interaction, view)
        return
    if view.where == SETUP_VIEW:
        await open_setup(interaction, view)
        return
    if view.where in (PUT_IN_VIEW, SWAP_VIEW, GIVE_BACK_VIEW):
        await open_sub(interaction, view, view.where)
        return
    await open_root(interaction, view)


async def back_from(interaction: discord.Interaction, view: Any) -> None:
    if view.where in (PUT_IN_VIEW, SWAP_VIEW, GIVE_BACK_VIEW):
        await open_card(interaction, view.train_id, view)
        return
    await open_root(interaction, view)


# --- the panel's moves ---------------------------------------------------------------------------


async def run_move(interaction: discord.Interaction, view: Any, doing: Any) -> None:
    """Every write re-reads the train first: it can be locked, filled or called off mid-card."""
    bot, guild = interaction.client, interaction.guild
    train = await get_train(bot.db, guild.id, view.train_id)
    if train is None:
        await render_root(interaction, view)
        await answer(interaction, NO_SUCH_TRAIN.format(train=str(view.train_id)))
        return
    cog = raid_cog(bot)
    if cog is None:
        outcome = await doing(train)
    else:
        async with cog._lock(int(train["id"])):
            outcome = await doing(train)
    await render_card(interaction, view.train_id, view)
    await answer(interaction, outcome.message)


async def run_claim(interaction: discord.Interaction, view: Any, position: int) -> None:
    if not await opened(interaction):
        return
    bot = interaction.client
    login = await twitch_login_of(bot.db, interaction.user.id)
    if not login and bot.store.get(interaction.guild.id, "raidtrain_require_link"):
        await render_card(interaction, view.train_id, view)
        await answer(interaction, NEEDS_LINK)
        return
    await run_move(
        interaction,
        view,
        lambda train: claim_slot(
            bot, interaction.guild, interaction.user, train, position, login
        ),
    )


async def run_release(interaction: discord.Interaction, view: Any, position: Any) -> None:
    if not await opened(interaction):
        return
    await run_move(
        interaction,
        view,
        lambda train: release_slot(
            interaction.client, interaction.guild, interaction.user, train, position
        ),
    )


async def run_unassign(interaction: discord.Interaction, view: Any, position: int) -> None:
    if not await still_organizer(interaction):
        return
    if not await opened(interaction):
        return
    await run_move(
        interaction,
        view,
        lambda train: unassign_slot(
            interaction.client, interaction.guild, interaction.user, train, position
        ),
    )


async def run_assign(interaction: discord.Interaction, view: Any) -> None:
    if not await still_organizer(interaction):
        return
    if not await opened(interaction):
        return
    if view.first is None or view.member_id is None:
        await render_sub(interaction, view, PUT_IN_VIEW)
        await answer(interaction, PUT_IN_NEEDS_BOTH)
        return
    bot, guild = interaction.client, interaction.guild
    member = guild.get_member(int(view.member_id)) or int(view.member_id)
    login = await twitch_login_of(bot.db, int(view.member_id))
    await run_move(
        interaction,
        view,
        lambda train: assign_slot(
            bot, guild, interaction.user, train, view.first, member, login
        ),
    )


async def run_swap(interaction: discord.Interaction, view: Any) -> None:
    if not await still_organizer(interaction):
        return
    if not await opened(interaction):
        return
    if view.first is None or view.second is None:
        await render_sub(interaction, view, SWAP_VIEW)
        await answer(interaction, SWAP_NEEDS_BOTH)
        return
    await run_move(
        interaction,
        view,
        lambda train: swap_slots(
            interaction.client,
            interaction.guild,
            interaction.user,
            train,
            view.first,
            view.second,
        ),
    )


async def run_lock(interaction: discord.Interaction, view: Any) -> None:
    if not await still_organizer(interaction):
        return
    if not await opened(interaction):
        return

    async def moving(train: Any) -> Any:
        to = LOCKED if str(train["status"]) == OPEN else OPEN
        return await move_train(
            interaction.client, interaction.guild, interaction.user, train, to
        )

    await run_move(interaction, view, moving)


async def run_cancel(interaction: discord.Interaction, view: Any, reason: str) -> None:
    if not await still_organizer(interaction):
        return
    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild

    async def calling_off(train: Any) -> Any:
        cog = raid_cog(bot)
        if cog is None or not may_move(train["status"], CANCELLED):
            return refusal(move_refusal(train["status"], CANCELLED), BAD_MOVE_CODE, 409)
        told = await cog.cancel_train(guild, train, reason, interaction.user)
        return Outcome(True, CANCELLED_NOW.format(title=train["title"], count=told))

    await run_move(interaction, view, calling_off)


async def run_mode(interaction: discord.Interaction, view: Any, wanted: str) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction):
        return
    said = await set_mode(interaction.client, interaction.guild, interaction.user, wanted)
    await render_root(interaction, view)
    await answer(interaction, said.message)


async def run_setup(interaction: discord.Interaction, view: Any, fields: Any) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction):
        return
    said = await save_setup(interaction.client, interaction.guild, interaction.user, fields)
    await render_setup(interaction, view)
    await answer(interaction, said.message)


# --- the Start draft ------------------------------------------------------------------------------


class TrainDraftPanel(Panel):
    """The draft Start writes into: nothing typed is refused, and Start waits until it passes."""

    def __init__(self, minutes: int, fields: rt.TrainDraft) -> None:
        super().__init__(minutes, footer=rt.PANEL_TIMEOUT_FOOTER)
        self.fields = fields

    @property
    def draft(self) -> WhenDraft:
        return self.fields.when

    async def rerender(self, interaction: discord.Interaction) -> None:
        await open_draft(interaction, self.fields, self)

    async def take_later(self, interaction: discord.Interaction, text: str) -> None:
        self.fields.when.later_text = str(text or "").strip()
        self.fields.when.day = None
        await self.rerender(interaction)


class TrainTextModal(AnswersErrors, discord.ui.Modal, title=TEXT_MODAL_TITLE):
    """Four boxes with no failure path; `"abc"` slot minutes are held on the panel, not lost."""

    train_title = discord.ui.TextInput(label="Title", max_length=TITLE_LIMIT, required=False)
    description = discord.ui.TextInput(
        label="What is it?",
        style=discord.TextStyle.paragraph,
        max_length=DESCRIPTION_LIMIT,
        required=False,
    )
    slot_minutes = discord.ui.TextInput(
        label="Minutes per slot", placeholder="60", max_length=4, required=False
    )
    slot_count = discord.ui.TextInput(
        label="How many slots", placeholder="8", max_length=3, required=False
    )

    def __init__(self, previous: Any) -> None:
        super().__init__()
        self.previous = previous
        fields = previous.fields
        self.train_title.default = fields.title or None
        self.description.default = fields.description or None
        self.slot_minutes.default = fields.slot_minutes or None
        self.slot_count.default = fields.slot_count or None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        fields = self.previous.fields
        fields.title = clamp(self.train_title, TITLE_LIMIT)
        fields.description = clamp(self.description, DESCRIPTION_LIMIT)
        fields.slot_minutes = str(self.slot_minutes).strip()
        fields.slot_count = str(self.slot_count).strip()
        await open_draft(interaction, fields, self.previous)


class DraftTextButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label=TEXT_BUTTON, style=discord.ButtonStyle.primary, row=DRAFT_BUTTON_ROW
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_organizer(interaction):
            return
        await interaction.response.send_modal(TrainTextModal(self.view))


class DraftZoneButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label=ZONE_PANEL_BUTTON, style=discord.ButtonStyle.secondary, row=DRAFT_BUTTON_ROW
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        fields = self.view.fields
        await open_zone_panel(
            interaction, self.view, lambda one, prev: open_draft(one, fields, prev)
        )


class StartButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label=rt.START_BUTTON, style=discord.ButtonStyle.success, row=DRAFT_BUTTON_ROW
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await start_draft(interaction, self.view)


class DraftBackButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Back", style=discord.ButtonStyle.secondary, row=DRAFT_BUTTON_ROW)

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_root(interaction, self.view)


async def build_draft(
    bot: Any, guild: Any, actor: Any, fields: rt.TrainDraft
) -> tuple[discord.Embed, TrainDraftPanel]:
    store = bot.store
    now = datetime.now(UTC)
    zone_name, chosen = await stored_zone(bot.db, actor.id, guild_zone(store, guild.id))
    fields.when.zone = zone_name
    checked, why = rt.draft_check(fields, now)
    embed = discord.Embed(
        title=rt.DRAFT_TITLE,
        description=clamped(rt.draft_lines(fields, now, chosen=chosen, why=why)),
    )
    view = TrainDraftPanel(minutes_for(bot, guild.id), fields)
    view.add_item(DaySelect(fields.when, now))
    view.add_item(HourSelect(fields.when))
    view.add_item(MinuteSelect(fields.when, minute_step(store, guild.id)))
    view.add_item(DraftTextButton())
    view.add_item(DraftZoneButton())
    if checked is not None:
        view.add_item(StartButton())
    view.add_item(DraftBackButton())
    return (embed, view)


async def render_draft(
    interaction: discord.Interaction, fields: rt.TrainDraft, previous: Any = None
) -> None:
    embed, view = await build_draft(
        interaction.client, interaction.guild, interaction.user, fields
    )
    await render(interaction, embed, view, previous)


async def open_draft(
    interaction: discord.Interaction, fields: rt.TrainDraft, previous: Any = None
) -> None:
    if not await still_organizer(interaction):
        return
    if not await opened(interaction):
        return
    await render_draft(interaction, fields, previous)


async def start_new_train(interaction: discord.Interaction, previous: Any) -> None:
    """`Start a raid train` on the root: a fresh draft seeded with the server's slot length."""
    bot = interaction.client
    if not await still_organizer(interaction):
        return
    if not await db_up(interaction):
        return
    fields = rt.TrainDraft(
        slot_minutes=str(int(bot.store.get(interaction.guild.id, "raidtrain_slot_minutes")))
    )
    await open_draft(interaction, fields, previous)


async def start_draft(interaction: discord.Interaction, previous: Any) -> None:
    """What `run_create` did from validation onward, with the organizer gate asked again."""
    fields = previous.fields
    if not await still_organizer(interaction):
        return
    if not await opened(interaction):
        return
    checked, why = rt.draft_check(fields, datetime.now(UTC))
    if checked is None:
        await render_draft(interaction, fields, previous)
        await answer(interaction, why)
        return
    made = await create_and_publish(
        interaction.client,
        interaction.guild,
        interaction.user,
        title=checked.title,
        description=checked.description,
        starts_at=checked.starts,
        slot_minutes=checked.slot_minutes,
        slot_count=checked.slot_count,
    )
    await render_root(interaction, previous)
    await answer(interaction, made.message)


async def open_zone_panel(interaction: discord.Interaction, previous: Any, back: Any) -> None:
    """The same dropdown `/event` shows, storing through the same `set_zone`."""
    if not await opened(interaction):
        return
    bot, store = interaction.client, interaction.client.store
    guild_default = guild_zone(store, interaction.guild.id)
    zone_name, chosen = await stored_zone(bot.db, interaction.user.id, guild_default)
    current = zone_name if chosen else ""
    embed = discord.Embed(
        title=ZONE_PANEL_TITLE,
        description=clamped([ZONE_PANEL_INTRO, zone_line(zone_name, chosen=chosen)]),
    )
    view = ZonePanel(
        minutes_for(bot, interaction.guild.id),
        footer=rt.PANEL_TIMEOUT_FOOTER,
        choices=zone_choices(store, interaction.guild.id),
        stored=current or None,
        guild_default=guild_default,
        on_pick=lambda one, name, panel: pick_zone(one, name, panel, back),
        on_other=lambda one, panel: open_zone_modal(one, current, panel, back),
        on_back=back,
    )
    await render(interaction, embed, view, previous)


async def open_zone_modal(
    interaction: discord.Interaction, current: str, previous: Any, back: Any
) -> None:
    await interaction.response.send_modal(TrainZoneModal(current, previous, back))


async def pick_zone(
    interaction: discord.Interaction, given: str, previous: Any, back: Any
) -> None:
    if not await opened(interaction):
        return
    _, said = await store_zone(interaction.client.db, interaction.user.id, given)
    await back(interaction, previous)
    await answer(interaction, said)


class TrainZoneModal(WhenZoneModal):
    def __init__(self, current: str = "", previous: Any = None, back: Any = None) -> None:
        self.previous = previous
        self.back = back
        super().__init__(current=current, on_submit=self.zone_submit)

    async def zone_submit(self, interaction: discord.Interaction, given: str) -> None:
        await pick_zone(interaction, given, self.previous, self.back)


# --- the controls --------------------------------------------------------------------------------


class MoveButton(discord.ui.Button):
    def __init__(self, move: Any) -> None:
        super().__init__(label=move.label, style=STYLES[move.style], row=move.row)
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        action = self.move.action
        if action == rt.REFRESH:
            await refresh_where(interaction, view)
        elif action == rt.BACK:
            await back_from(interaction, view)
        elif action == rt.LOGS:
            await send_logs(interaction, "raidtrain")
        elif action == rt.MINE:
            await open_mine(interaction, view)
        elif action == rt.SETUP:
            await open_setup(interaction, view)
        elif action == rt.PUT_IN:
            await open_sub(interaction, view, PUT_IN_VIEW)
        elif action == rt.SWAP:
            await open_sub(interaction, view, SWAP_VIEW)
        elif action == rt.GIVE_BACK_MANY:
            await open_sub(interaction, view, GIVE_BACK_VIEW)
        elif action == rt.GIVE_BACK:
            await run_release(interaction, view, None)
        elif action == rt.MOVE_TRAIN:
            await run_lock(interaction, view)
        elif action == rt.PUT_THEM_IN:
            await run_assign(interaction, view)
        elif action == rt.SWAP_THEM:
            await run_swap(interaction, view)
        elif action == rt.SAVE:
            await run_setup(interaction, view, dict(view.setup))
        elif action == rt.START_TRAIN:
            await start_new_train(interaction, view)
        else:
            await self.open_modal(interaction, view, action)

    async def open_modal(self, interaction: discord.Interaction, view: Any, action: str) -> None:
        bot = interaction.client
        if not await still_organizer(interaction):
            return
        if not await db_up(interaction):
            return
        train = await get_train(bot.db, interaction.guild.id, view.train_id)
        if train is None:
            await answer(interaction, NO_SUCH_TRAIN.format(train=str(view.train_id)))
            return
        await interaction.response.send_modal(
            NoteModal(
                title=clamp(CANCEL_TITLE.format(title=train["title"]), MODAL_TITLE_LIMIT),
                label=CANCEL_LABEL,
                max_length=DESCRIPTION_LIMIT,
                on_submit=lambda one, text: run_cancel(one, view, text),
            )
        )


class TrainPick(discord.ui.Select):
    def __init__(self, found: Any, *, placeholder: str, row: int) -> None:
        rows = tuple(found)
        shown = rows[:SELECT_CAP]
        super().__init__(
            placeholder=capped_placeholder(
                len(shown), len(rows), pick=placeholder, capped=TRAIN_CAPPED
            ),
            options=[
                discord.SelectOption(label=label[:SELECT_OPTION_LIMIT], value=value)
                for value, label in shown
            ],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_card(interaction, int(self.values[0]), self.view)


class ModePick(discord.ui.Select):
    def __init__(self, current: str, row: int) -> None:
        super().__init__(
            placeholder=MODE_PLACEHOLDER,
            options=[
                discord.SelectOption(label=one, value=one, default=(one == current))
                for one in RAIDTRAIN_MODES
            ],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_mode(interaction, self.view, self.values[0])


class SlotPick(discord.ui.Select):
    """One select class, five jobs — what it does is the `doing` it was built with."""

    def __init__(
        self,
        slots: Any,
        kind: str,
        placeholder: str,
        doing: str,
        *,
        row: int,
        names: Any = None,
    ) -> None:
        self.doing = doing
        super().__init__(
            placeholder=placeholder,
            options=[
                discord.SelectOption(label=label, value=value)
                for value, label in rt.slot_options(slots, kind, names=names)[:SELECT_CAP]
            ],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        position = int(self.values[0])
        if self.doing == DO_CLAIM:
            await run_claim(interaction, view, position)
        elif self.doing == DO_UNASSIGN:
            await run_unassign(interaction, view, position)
        elif self.doing == DO_RELEASE:
            await run_release(interaction, view, position)
        elif self.doing == DO_FIRST:
            view.first = position
            view.second = None
            await open_sub(interaction, view, SWAP_VIEW)
        else:
            await self.remembered(interaction, view, position)

    async def remembered(self, interaction: discord.Interaction, view: Any, position: int) -> None:
        """A pick that is half a move writes nothing; the confirm re-reads both halves."""
        if self.doing == DO_SECOND:
            view.second = position
        else:
            view.first = position
        await interaction.response.defer()


class WhoPick(discord.ui.UserSelect):
    def __init__(self, row: int) -> None:
        super().__init__(placeholder=WHO_PLACEHOLDER, min_values=1, max_values=1, row=row)

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.member_id = int(self.values[0].id)
        await interaction.response.defer()


class LineupChannelPick(discord.ui.ChannelSelect):
    def __init__(self, row: int) -> None:
        super().__init__(
            placeholder=CHANNEL_PLACEHOLDER,
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.setup["raidtrain_channel_id"] = int(self.values[0].id)
        await interaction.response.defer()


class SetupRolePick(discord.ui.RoleSelect):
    def __init__(self, key: str, placeholder: str, row: int) -> None:
        self.key = key
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, row=row)

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.setup[self.key] = int(self.values[0].id)
        await interaction.response.defer()


class ClearPick(discord.ui.Select):
    """Clearing is its own control: an empty submit cannot be told from an untouched one."""

    def __init__(self, keys: Any, row: int) -> None:
        super().__init__(
            placeholder=CLEAR_PLACEHOLDER,
            options=[
                discord.SelectOption(label=SETUP_LABELS[key], value=key) for key in keys
            ],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_setup(interaction, self.view, {self.values[0]: None})


class RaidTrains(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.last_sweep_ok_at: str | None = None
        self.last_sweep_error: str | None = None
        self.sweep_failures = 0
        self._locks: dict[int, asyncio.Lock] = {}

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name != "sweep":
            return (None, None)
        return (self.last_sweep_ok_at, self.last_sweep_error)

    async def cog_load(self) -> None:
        if not self.bot.db.is_connected:
            return
        self.sweep.start()

    async def cog_unload(self) -> None:
        self.sweep.cancel()

    def _lock(self, train_id: int) -> asyncio.Lock:
        """One lock per train: two people claiming the same open slot are serialised here."""
        found = self._locks.get(int(train_id))
        if found is None:
            found = asyncio.Lock()
            self._locks[int(train_id)] = found
        return found

    # --- the sweep ----------------------------------------------------------------------------

    @tasks.loop(minutes=5)
    async def sweep(self) -> None:
        try:
            await self.sweep_once()
        except Exception as exc:
            self.last_sweep_error = f"{type(exc).__name__}: {exc}"
            self.sweep_failures += 1
            log.exception("raidtrain: the sweep failed")
            await self._sweep_degraded()
        self._retime()

    @sweep.before_loop
    async def _before_sweep(self) -> None:
        if await wait_ready(self.bot, self._sweep_stopped):
            self._retime()

    @sweep.error
    async def _sweep_stopped(self, exc: BaseException) -> None:
        """discord.py stops a loop for the life of the process, so it is started again."""
        self.last_sweep_error = f"{type(exc).__name__}: {exc}"
        log.error("raidtrain: the sweep stopped; restarting it", exc_info=exc)
        self.sweep.restart()

    def _retime(self) -> None:
        wanted = self._minutes()
        if self.sweep.minutes != wanted:
            self.sweep.change_interval(minutes=wanted)

    def _minutes(self) -> int:
        guild = next(iter(getattr(self.bot, "guilds", ()) or ()), None)
        if guild is None:
            return 5
        return max(1, int(self.bot.store.get(guild.id, "raidtrain_poll_minutes")))

    async def _sweep_degraded(self) -> None:
        if self.sweep_failures != SWEEPS_BEFORE_DEGRADED:
            return
        for guild in list(getattr(self.bot, "guilds", ())):
            await log_action(
                self.bot,
                guild,
                "raidtrain.poll_degraded",
                details={"sweeps": self.sweep_failures, "reason": self.last_sweep_error},
            )

    async def sweep_once(self) -> None:
        if not self.bot.db.is_connected:
            return
        for guild in list(getattr(self.bot, "guilds", ())):
            if getattr(guild, "unavailable", False):
                continue
            if self._mode(guild.id) == "off":
                continue
            await self._sweep_guild(guild)
        self.last_sweep_ok_at = now_iso()
        self.last_sweep_error = None
        self.sweep_failures = 0

    async def _sweep_guild(self, guild: Any) -> None:
        now = datetime.now(UTC)
        for train in await list_trains(self.bot.db, guild.id, scope="upcoming"):
            async with self._lock(int(train["id"])):
                fresh = await get_train(self.bot.db, guild.id, train["id"])
                if fresh is None:
                    continue
                slots = await slots_for(self.bot.db, fresh["id"])
                moved = await self._run_clock(guild, fresh, slots, now)
                sent = await self._run_reminders(guild, fresh, slots, now)
                seen = await self._run_checkins(
                    guild, fresh, slots, now, status=moved or str(fresh["status"])
                )
                if moved or sent or seen:
                    await self._refresh_lineup(guild, fresh["id"])

    async def _run_clock(self, guild: Any, train: Any, slots: Any, now: datetime) -> str | None:
        """Locks at the start, runs, and finishes; answers with the status it left behind."""
        from ...raidtrain import ends_at as train_ends_at

        starts = parse_ts(train["starts_at"])
        status = str(train["status"])
        if starts is None:
            return None
        details = {"train_id": train["id"], "title": train["title"], "slots": len(slots)}
        if status in (OPEN, LOCKED) and now >= starts:
            if status == OPEN:
                await set_status(self.bot.db, train["id"], LOCKED)
                await log_action(
                    self.bot,
                    guild,
                    "raidtrain.lock",
                    details=details | {"reason": "train_started"},
                )
            await set_status(self.bot.db, train["id"], LIVE)
            await log_action(self.bot, guild, "raidtrain.live", details=details)
            return LIVE
        finish = train_ends_at(train, slots)
        if status == LIVE and finish is not None and now >= finish:
            await set_status(self.bot.db, train["id"], DONE)
            await log_action(self.bot, guild, "raidtrain.done", details=details)
            return DONE
        return None

    async def _run_reminders(self, guild: Any, train: Any, slots: Any, now: datetime) -> bool:
        lead = int(self.bot.store.get(guild.id, "raidtrain_reminder_minutes"))
        touched = False
        for slot in missed_reminders(now, slots):
            await stamp_slot(self.bot.db, slot["id"], "reminded_at")
            log.info(
                "raidtrain: slot %s on train %s started before its reminder was due",
                slot["position"],
                train["id"],
            )
            touched = True
        for slot in due_reminders(now, lead, slots):
            await stamp_slot(self.bot.db, slot["id"], "reminded_at")
            await self._remind(guild, train, slot, slots)
            touched = True
        return touched

    async def _remind(self, guild: Any, train: Any, slot: Any, slots: Any) -> None:
        """The stamp is already on the row, so a failure here loses one DM and never doubles it."""
        before, after = neighbours(slots, slot["position"])
        text = reminder_text(train, slot, before, after, self._jump(train))
        details = {
            "train_id": train["id"],
            "position": slot["position"],
            "user_id": slot["user_id"],
            "text": text,
        }
        mode = self._mode(guild.id)
        if mode != "on":
            await log_action(
                self.bot,
                guild,
                "raidtrain.would_remind",
                target=slot["user_id"],
                details=details | {"reason": f"mode_{mode}"},
            )
            return
        member = guild.get_member(slot["user_id"]) or self.bot.get_user(slot["user_id"])
        if await dm(member, text):
            await log_action(
                self.bot, guild, "raidtrain.remind", target=slot["user_id"], details=details
            )
            return
        await log_action(
            self.bot,
            guild,
            "raidtrain.dm_failed",
            target=slot["user_id"],
            details=details | {"reason": "dm_refused"},
        )

    async def _run_checkins(
        self, guild: Any, train: Any, slots: Any, now: datetime, *, status: str
    ) -> bool:
        """`status` is what the clock just left, so a train that started this tick counts."""
        if not self.bot.store.get(guild.id, "raidtrain_live_posts"):
            return False
        if status != LIVE:
            return False
        from .golive import open_sessions

        live = [int(row["user_id"]) for row in await open_sessions(self.bot.db, guild.id)]
        touched = False
        for slot in due_checkins(now, slots, live):
            await stamp_slot(self.bot.db, slot["id"], "checked_in_at")
            await log_action(
                self.bot,
                guild,
                "raidtrain.checkin",
                target=slot["user_id"],
                details={"train_id": train["id"], "position": slot["position"]},
            )
            await self._say_the_train_moved(guild, train, slot, slots)
            touched = True
        return touched

    async def _say_the_train_moved(self, guild: Any, train: Any, slot: Any, slots: Any) -> None:
        _before, after = neighbours(slots, slot["position"])
        text = live_post_text(train, slot, after)
        details = {"train_id": train["id"], "position": slot["position"], "text": text}
        mode = self._mode(guild.id)
        if mode != "on":
            await log_action(
                self.bot,
                guild,
                "raidtrain.would_post",
                details=details | {"reason": f"mode_{mode}"},
            )
            return
        where = train["thread_id"] or train["channel_id"] or self._channel_id(guild.id)
        message = await self._post(guild, where, text, details)
        if message is not None:
            await stamp_slot(self.bot.db, slot["id"], "live_posted_at")

    # --- posting ------------------------------------------------------------------------------

    def _channel_id(self, guild_id: int) -> int | None:
        return lineup_channel(self.bot, guild_id)

    def _mode(self, guild_id: int) -> str:
        return mode_of(self.bot, guild_id)

    def _mentions(self, guild_id: int) -> discord.AllowedMentions:
        """Only the configured ping role; a display name on the lineup can never ping anybody."""
        role_id = self.bot.store.get(guild_id, "raidtrain_ping_role_id")
        return discord.AllowedMentions(
            everyone=False,
            users=False,
            roles=[discord.Object(role_id)] if role_id else False,
        )

    def _jump(self, train: Any) -> str | None:
        channel_id = _row(train, "channel_id")
        message_id = _row(train, "lineup_message_id")
        if not channel_id or not message_id:
            return None
        return f"https://discord.com/channels/{train['guild_id']}/{channel_id}/{message_id}"

    async def _post(
        self, guild: Any, channel_id: Any, text: str, details: dict[str, Any]
    ) -> Any:
        """The one guarded path anything of this feature takes to a channel."""
        if not channel_id:
            await log_action(
                self.bot,
                guild,
                "raidtrain.post_failed",
                details=details | {"reason": "no_channel_configured"},
            )
            return None
        guard = getattr(self.bot, "guard", None)
        if guard is not None and not guard.allows_channel(int(channel_id)):
            log.warning("raidtrain: TEST MODE — refused to post to channel %s", channel_id)
            await log_action(
                self.bot,
                guild,
                "raidtrain.post_skipped_test_mode",
                details=details | {"channel_id": int(channel_id)},
            )
            return None
        channel = self.bot.get_channel(int(channel_id)) or guild.get_channel(int(channel_id))
        if channel is None:
            await log_action(
                self.bot,
                guild,
                "raidtrain.post_failed",
                details=details | {"reason": "channel_not_visible"},
            )
            return None
        try:
            message = await channel.send(text, allowed_mentions=self._mentions(guild.id))
        except NETWORK_ERRORS as exc:
            log.warning("raidtrain: not posted — %s: %s", type(exc).__name__, exc)
            await log_action(
                self.bot,
                guild,
                "raidtrain.post_failed",
                details=details | {"reason": f"{type(exc).__name__}: {exc}"},
            )
            return None
        await log_action(
            self.bot, guild, "raidtrain.post", details=details | {"message_id": message.id}
        )
        return message

    async def publish_lineup(self, guild: Any, train_id: int) -> None:
        """The first post: the lineup, the thread under it, and Discord's own event if asked."""
        train = await get_train(self.bot.db, guild.id, train_id)
        if train is None:
            return
        slots = await slots_for(self.bot.db, train_id)
        text = render_lineup(
            train, slots, ping_role_id=self.bot.store.get(guild.id, "raidtrain_ping_role_id")
        )
        channel_id = self._channel_id(guild.id)
        details = {"train_id": train_id, "kind": "lineup"}
        if self._mode(guild.id) != "on":
            await log_action(
                self.bot,
                guild,
                "raidtrain.would_post",
                details=details | {"reason": f"mode_{self._mode(guild.id)}", "text": text},
            )
            return
        message = await self._post(guild, channel_id, text, details)
        if message is None:
            return
        await set_lineup(
            self.bot.db, train_id, channel_id=int(channel_id), message_id=int(message.id)
        )
        thread_id = await self._open_thread(guild, train, message)
        if thread_id is not None:
            await set_lineup(self.bot.db, train_id, thread_id=thread_id)
        await self._maybe_scheduled_event(guild, train_id)

    async def _open_thread(self, guild: Any, train: Any, message: Any) -> int | None:
        if not self.bot.store.get(guild.id, "raidtrain_thread"):
            return None
        maker = getattr(message, "create_thread", None)
        if maker is None:
            return None
        try:
            thread = await maker(name=clamp(train["title"], TITLE_LIMIT) or "Raid train")
        except NETWORK_ERRORS as exc:
            log.warning("raidtrain: no thread for train %s — %s", train["id"], exc)
            await log_action(
                self.bot,
                guild,
                "raidtrain.post_failed",
                details={
                    "train_id": train["id"],
                    "kind": "thread",
                    "reason": f"{type(exc).__name__}: {exc}",
                },
            )
            return None
        guard = getattr(self.bot, "guard", None)
        if guard is not None:
            guard.own_channel(thread)
        return int(thread.id)

    async def _maybe_scheduled_event(self, guild: Any, train_id: int) -> None:
        """D13: raid trains make their own, because Phase 4's helper writes to the events table."""
        if not self.bot.store.get(guild.id, "raidtrain_scheduled_event"):
            return
        train = await get_train(self.bot.db, guild.id, train_id)
        slots = await slots_for(self.bot.db, train_id)
        from ...raidtrain import ends_at as train_ends_at

        starts = parse_ts(train["starts_at"])
        finishes = train_ends_at(train, slots)
        details = {"train_id": train_id}
        if starts is None or finishes is None:
            await log_action(
                self.bot,
                guild,
                "raidtrain.create_scheduled_failed",
                details=details | {"reason": "unreadable_times"},
            )
            return
        if getattr(self.bot, "guard", None) is not None:
            log.warning("raidtrain: TEST MODE — no scheduled event made for train %s", train_id)
            await log_action(
                self.bot,
                guild,
                "raidtrain.would_create_scheduled",
                details=details | {"reason": "test_mode"},
            )
            return
        try:
            made = await guild.create_scheduled_event(
                name=scheduled_name(
                    self.bot.store.get(guild.id, RAIDTRAIN_SCHEDULED_NAME_KEY),
                    train["title"],
                    fallback=RAIDTRAIN_SCHEDULED_NAME_TEMPLATE,
                ),
                description=clamp(train["description"], DESCRIPTION_LIMIT) or None,
                start_time=starts,
                end_time=finishes,
                entity_type=discord.EntityType.external,
                location=self._jump(train) or "Twitch",
                privacy_level=discord.PrivacyLevel.guild_only,
                reason=f"Black Bloc raid train {train_id}",
            )
        except NETWORK_ERRORS as exc:
            await log_action(
                self.bot,
                guild,
                "raidtrain.create_scheduled_failed",
                details=details | {"reason": f"{type(exc).__name__}: {exc}"},
            )
            return
        await set_lineup(self.bot.db, train_id, scheduled_event_id=int(made.id))

    async def _drop_scheduled_event(self, guild: Any, train: Any) -> None:
        scheduled_id = _row(train, "scheduled_event_id")
        if not scheduled_id or getattr(self.bot, "guard", None) is not None:
            return
        from ...events import find_scheduled_event

        try:
            found = await find_scheduled_event(guild, int(scheduled_id))
            if found is None:
                return
            if getattr(found, "status", None) is discord.EventStatus.active:
                await found.end(reason="Black Bloc raid train cancelled")
            else:
                await found.cancel(reason="Black Bloc raid train cancelled")
        except NETWORK_ERRORS as exc:
            await log_action(
                self.bot,
                guild,
                "raidtrain.cancel_scheduled_failed",
                details={"train_id": train["id"], "reason": f"{type(exc).__name__}: {exc}"},
            )

    async def _refresh_lineup(self, guild: Any, train_id: int) -> None:
        """The lineup post is edited in place, so one message is the whole record of a train."""
        train = await get_train(self.bot.db, guild.id, train_id)
        if train is None or not train["lineup_message_id"] or not train["channel_id"]:
            return
        slots = await slots_for(self.bot.db, train_id)
        text = render_lineup(
            train, slots, ping_role_id=self.bot.store.get(guild.id, "raidtrain_ping_role_id")
        )
        guard = getattr(self.bot, "guard", None)
        if guard is not None and not guard.allows_channel(int(train["channel_id"])):
            await log_action(
                self.bot,
                guild,
                "raidtrain.post_skipped_test_mode",
                details={"train_id": train_id, "kind": "lineup_edit"},
            )
            return
        channel = self.bot.get_channel(int(train["channel_id"])) or guild.get_channel(
            int(train["channel_id"])
        )
        if channel is None:
            return
        try:
            message = await channel.fetch_message(int(train["lineup_message_id"]))
            await message.edit(content=text, allowed_mentions=self._mentions(guild.id))
        except NETWORK_ERRORS as exc:
            log.warning("raidtrain: could not redraw the lineup for %s: %s", train_id, exc)
            await log_action(
                self.bot,
                guild,
                "raidtrain.post_failed",
                details={
                    "train_id": train_id,
                    "kind": "lineup_edit",
                    "reason": f"{type(exc).__name__}: {exc}",
                },
            )

    async def cancel_train(
        self, guild: Any, train: Any, reason: str, actor: Any, *, via: str = VIA_DISCORD
    ) -> int:
        """The state change first, then the DMs, then the cosmetics — the web calls it too."""
        said = clamp(reason, DESCRIPTION_LIMIT)
        await set_status(self.bot.db, train["id"], CANCELLED, reason=said or None)
        slots = await slots_for(self.bot.db, train["id"])
        holders = [int(one["user_id"]) for one in slots if one["user_id"] is not None]
        await log_action(
            self.bot,
            guild,
            kind_via("raidtrain.cancel", via),
            actor=actor,
            reason=said or None,
            details={
                "train_id": train["id"],
                "title": train["title"],
                "holders": len(holders),
                "via": via,
            },
        )
        told = 0
        if self._mode(guild.id) == "on":
            text = cancelled_text(train, said)
            for user_id in dict.fromkeys(holders):
                member = guild.get_member(user_id) or self.bot.get_user(user_id)
                if await dm(member, text):
                    told += 1
                else:
                    await log_action(
                        self.bot,
                        guild,
                        "raidtrain.dm_failed",
                        target=user_id,
                        details={"train_id": train["id"], "reason": "cancel_dm_refused"},
                    )
        await self._drop_scheduled_event(guild, train)
        await self._refresh_lineup(guild, train["id"])
        return told

    # --- the panel ----------------------------------------------------------------------------

    def is_organizer(self, member: Any) -> bool:
        return is_organizer(self.bot, member)

    @app_commands.command(
        name="raidtrain", description="Raid trains: sign up for an hour and pass the raid on"
    )
    async def raidtrain_panel_command(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return
        if not self.bot.db.is_connected:
            log.warning("raidtrain: refused the panel — the database is not connected")
            await answer(interaction, DB_UNAVAILABLE)
            return
        embed, view = await build_panel(self.bot, interaction.guild, interaction.user)
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RaidTrains(bot))
