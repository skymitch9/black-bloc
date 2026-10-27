from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import discord

from . import questions as rules
from . import questions_store as store
from . import shadow as shadow_home
from .actionlog import log_action
from .logkinds import VIA_DISCORD, kind_via
from .panels import Outcome, refusal

log = logging.getLogger(__name__)

LOCKS_ATTR = "_question_locks"
DELETE_GONE = (discord.NotFound,)


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


def actor_id(actor: Any) -> int | None:
    found = getattr(actor, "id", actor)
    try:
        return int(found) if found is not None else None
    except (TypeError, ValueError):
        return None


def target_id(bot: Any, guild: Any, mode: str) -> tuple[int | None, str | None]:
    """Where the question goes, or the sentence for why it cannot go anywhere."""
    if mode != rules.ON:
        return (None, rules.QUESTIONS_OFF)
    found = rules.real_channel(bot.store, guild.id)
    return (found, None) if found else (None, rules.NO_CHANNEL)


def channel_for(bot: Any, guild: Any, channel_id: int) -> tuple[Any, str | None]:
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel_id):
        return None, rules.TEST_MODE_REFUSED.format(channel=channel_id)
    found = shadow_home.channel_of(bot, guild, channel_id)
    if found is None:
        return None, rules.CHANNEL_GONE.format(channel=channel_id)
    return found, None


async def send_question(bot: Any, guild: Any, mode: str, body: str) -> tuple[Any, Any, str | None]:
    """(channel, message, None) once posted, or (None, None, why not)."""
    wanted, why = target_id(bot, guild, mode)
    if wanted is None:
        return None, None, why
    channel, why = channel_for(bot, guild, wanted)
    if channel is None:
        return None, None, why
    try:
        message = await channel.send(
            rules.posted_text(bot.store, guild.id, body),
            allowed_mentions=rules.posted_mentions(bot.store, guild.id),
        )
    except discord.HTTPException as exc:
        return None, None, rules.POST_REFUSED.format(why=f"{exc.status} {exc.text}".strip())
    return channel, message, None


async def find_owner_post(
    channel: Any, owner: int, body: str, since: datetime
) -> tuple[Any, str | None]:
    """The owner's post of the question since `since`, and why the look failed if it did."""
    try:
        messages = [one async for one in channel.history(limit=rules.OWNER_SCAN_LIMIT, after=since)]
    except (discord.HTTPException, AttributeError) as exc:
        return None, f"{type(exc).__name__}: {exc}"
    return rules.owner_post(messages, owner, body, since), None


async def open_thread(
    bot: Any, guild: Any, message: Any, body: str, slot_at: str | None
) -> None:
    if not rules.threads_on(bot.store, guild.id):
        return
    try:
        await message.create_thread(name=rules.thread_name(bot.store, guild.id, body))
    except (discord.HTTPException, AttributeError, ValueError) as exc:
        await log_action(
            bot,
            guild,
            "question.thread_failed",
            details={"slot_at": slot_at, "why": f"{type(exc).__name__}: {exc}"},
        )


def slot_details(slot: datetime, schedule: rules.Schedule, mode: str) -> dict[str, Any]:
    return {
        "slot_at": rules.slot_key(slot),
        "local": f"{rules.day_word(slot, schedule)} {rules.time_word(slot, schedule)}",
        "mode": mode,
    }


async def tick(bot: Any, guild: Any, now: datetime | None = None) -> str | None:
    """One pass for one server; the stored slot is re-read inside the lock (checklist 37)."""
    async with lock_of(bot, guild.id):
        return await _tick(bot, guild, moment(now))


async def _tick(bot: Any, guild: Any, now: datetime) -> str | None:
    mode = rules.mode_of(bot.store, guild.id)
    if mode == rules.OFF:
        return None
    schedule = rules.schedule_of(bot.store, guild.id)
    last, following = rules.slots_around(now, schedule)
    await store.ensure_slot(bot.db, guild.id, rules.slot_key(following), now)
    await warn_if_empty(bot, guild, schedule, following, now, mode)
    return await resolve(bot, guild, schedule, last, now, mode)


async def resolve(
    bot: Any, guild: Any, schedule: rules.Schedule, slot: datetime, now: datetime, mode: str
) -> str | None:
    key = rules.slot_key(slot)
    row = await store.get_slot(bot.db, guild.id, key)
    if row is None:
        if now >= slot + schedule.catchup:
            return None
        row = await store.ensure_slot(bot.db, guild.id, key, now)
    if row["status"] != rules.PENDING:
        return str(row["status"])
    if now < slot + schedule.grace:
        return rules.PENDING
    details = slot_details(slot, schedule, mode)
    if now >= slot + schedule.catchup:
        await store.set_slot(bot.db, guild.id, key, rules.MISSED, now)
        await log_action(bot, guild, "question.missed", details=details)
        return rules.MISSED
    question = await store.first_queued(bot.db, guild.id)
    if question is None:
        await store.set_slot(bot.db, guild.id, key, rules.SKIPPED_EMPTY, now)
        await log_action(bot, guild, "question.skipped_empty", details=details)
        return rules.SKIPPED_EMPTY
    details |= {"question_id": int(question["id"]), "question": question["body"]}
    owner = rules.owner_of(bot.store, guild.id)
    if owner is not None:
        wanted, why = target_id(bot, guild, mode)
        channel = None
        if wanted is not None:
            channel, why = channel_for(bot, guild, wanted)
        if channel is not None:
            found, why = await find_owner_post(
                channel, owner, question["body"], slot - rules.LOOKBACK
            )
            if found is not None:
                await store.mark_posted(
                    bot.db, question["id"], key, rules.BY_OWNER, channel.id, found.id, now
                )
                await store.set_slot(
                    bot.db, guild.id, key, rules.POSTED, now, question_id=int(question["id"])
                )
                await log_action(
                    bot,
                    guild,
                    "question.posted_by_owner",
                    target=owner,
                    details=details | {"channel_id": channel.id, "message_id": found.id},
                )
                await open_thread(bot, guild, found, question["body"], key)
                return rules.POSTED
        if why:
            details["owner_look_failed"] = why
        details["reason"] = (
            f"the owner's post was not seen by {rules.time_word(slot + schedule.grace, schedule)}"
        )
    else:
        details["reason"] = "question_owner_user_id is not set"
    channel, message, why = await send_question(bot, guild, mode, question["body"])
    if message is None:
        if row["note"] != why:
            await store.set_note(bot.db, guild.id, key, why)
            await log_action(bot, guild, "question.post_failed", details=details | {"why": why})
        return rules.PENDING
    await store.mark_posted(bot.db, question["id"], key, rules.BY_BOT, channel.id, message.id, now)
    await store.set_slot(bot.db, guild.id, key, rules.POSTED, now, question_id=int(question["id"]))
    await log_action(
        bot,
        guild,
        "question.posted_by_bot",
        details=details | {"channel_id": channel.id, "message_id": message.id},
    )
    await open_thread(bot, guild, message, question["body"], key)
    return rules.POSTED


async def warn_if_empty(
    bot: Any, guild: Any, schedule: rules.Schedule, slot: datetime, now: datetime, mode: str
) -> bool:
    """Once per slot, stamped first so a crash part-way cannot warn twice."""
    if slot - now > timedelta(days=rules.warn_days(bot.store, guild.id)):
        return False
    if await store.first_queued(bot.db, guild.id) is not None:
        return False
    key = rules.slot_key(slot)
    row = await store.get_slot(bot.db, guild.id, key)
    if row is None or row["warned_at"] or row["status"] != rules.PENDING:
        return False
    await store.set_warned(bot.db, guild.id, key, now)
    text = rules.warn_text(bot.store, guild.id, slot, schedule)
    details = slot_details(slot, schedule, mode)
    details["line"] = await warn_line(bot, guild, mode, text)
    details["dm"] = await warn_owner(bot, guild, mode, text, key)
    await log_action(bot, guild, "question.warned_empty", details=details)
    return True


async def warn_line(bot: Any, guild: Any, mode: str, text: str) -> str:
    wanted = bot.store.get(guild.id, shadow_home.LOG_CHANNEL_KEY) if mode == rules.ON else None
    if not wanted:
        return "no channel"
    channel, why = channel_for(bot, guild, int(wanted))
    if channel is None:
        return why or "no channel"
    try:
        await channel.send(text, allowed_mentions=discord.AllowedMentions.none())
    except discord.HTTPException as exc:
        return f"{exc.status} {exc.text}".strip()
    return "sent"


async def warn_owner(bot: Any, guild: Any, mode: str, text: str, slot_at: str) -> str:
    if not rules.warn_dm(bot.store, guild.id):
        return "off"
    owner = rules.owner_of(bot.store, guild.id)
    if owner is None:
        return "no owner"
    if mode != rules.ON:
        return "off"
    user = guild.get_member(owner) or bot.get_user(owner)
    why = None
    if user is None:
        why = "the owner account is not in this server"
    else:
        try:
            await user.send(text, allowed_mentions=discord.AllowedMentions.none())
        except (discord.HTTPException, AttributeError) as exc:
            why = f"{type(exc).__name__}: {exc}"
    if why is None:
        return "sent"
    await log_action(
        bot,
        guild,
        "error.dm",
        target=owner,
        details={"where": "question.warned_empty", "slot_at": slot_at, "error": why},
    )
    return "failed"


async def candidate(bot: Any, guild: Any, now: datetime) -> tuple[datetime, Any]:
    schedule = rules.schedule_of(bot.store, guild.id)
    last, _ = rules.slots_around(now, schedule)
    last_row = await store.get_slot(bot.db, guild.id, rules.slot_key(last))
    slot = rules.current_slot(now, schedule, last_row)
    row = await store.ensure_slot(bot.db, guild.id, rules.slot_key(slot), now)
    return slot, row


async def week(bot: Any, guild: Any, now: datetime | None = None) -> dict[str, Any]:
    """What the panel, the page and the operator read: this week's slot and its question."""
    when = moment(now)
    schedule = rules.schedule_of(bot.store, guild.id)
    last, _ = rules.slots_around(when, schedule)
    last_row = await store.get_slot(bot.db, guild.id, rules.slot_key(last))
    slot = rules.current_slot(when, schedule, last_row)
    row = await store.get_slot(bot.db, guild.id, rules.slot_key(slot))
    status = str(row["status"]) if row is not None else rules.PENDING
    question = await store.first_queued(bot.db, guild.id)
    posted = None
    if row is not None and row["question_id"]:
        posted = await store.get(bot.db, guild.id, int(row["question_id"]))
    extra = await store.latest_posted(bot.db, guild.id)
    if extra is not None and (extra["slot_at"] or extra["posted_by"] != rules.BY_BOT):
        extra = None
    return {
        "slot": slot,
        "schedule": schedule,
        "status": status,
        "question": question,
        "posted": posted,
        "extra": extra,
        "mode": rules.mode_of(bot.store, guild.id),
    }


async def plan(bot: Any, guild: Any, found: dict[str, Any], count: int) -> list[datetime | None]:
    """When each queued question goes up as things stand; None for all while off."""
    if found["mode"] == rules.OFF:
        return [None] * count
    start = found["slot"]
    taken = await store.settled_from(bot.db, guild.id, rules.slot_key(start))
    return rules.planned(start, found["schedule"], count, taken)


async def add(
    bot: Any,
    guild: Any,
    actor: Any,
    text: Any,
    *,
    via: str = VIA_DISCORD,
    now: datetime | None = None,
) -> Outcome:
    bodies = rules.split_lines(text)
    if not bodies:
        return refusal(rules.NOTHING_TO_ADD, "nothing_to_add", 400)
    ids = await store.add_many(bot.db, guild.id, bodies, actor_id(actor), moment(now))
    await log_action(
        bot,
        guild,
        kind_via("question.added", via),
        actor=actor,
        details={"via": via, "count": len(ids), "ids": ids},
    )
    return Outcome(True, rules.ADDED.format(n=len(ids)), value=ids)


async def queued_one(bot: Any, guild: Any, question_id: Any) -> tuple[Any, Outcome | None]:
    row = await store.get(bot.db, guild.id, int(question_id))
    if row is None:
        return None, refusal(rules.NO_SUCH, "no_question", 404)
    if row["status"] != rules.QUEUED:
        return None, refusal(rules.NOT_QUEUED.format(status=row["status"]), "not_queued", 409)
    return row, None


async def edit(
    bot: Any, guild: Any, actor: Any, question_id: Any, text: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    body = " ".join(rules.split_lines(text))[: rules.BODY_LIMIT]
    if not body:
        return refusal(rules.NOTHING_TO_ADD, "nothing_to_add", 400)
    row, refused = await queued_one(bot, guild, question_id)
    if refused is not None:
        return refused
    await store.edit_body(bot.db, row["id"], body)
    await log_action(
        bot,
        guild,
        kind_via("question.edited", via),
        actor=actor,
        details={"via": via, "question_id": int(row["id"]), "before": row["body"], "after": body},
    )
    return Outcome(True, rules.EDITED, value=int(row["id"]))


async def remove(
    bot: Any,
    guild: Any,
    actor: Any,
    question_id: Any,
    *,
    via: str = VIA_DISCORD,
    now: datetime | None = None,
) -> Outcome:
    row, refused = await queued_one(bot, guild, question_id)
    if refused is not None:
        return refused
    await store.set_removed(bot.db, row["id"], moment(now))
    await log_action(
        bot,
        guild,
        kind_via("question.removed", via),
        actor=actor,
        details={"via": via, "question_id": int(row["id"]), "question": row["body"]},
    )
    return Outcome(True, rules.REMOVED_SAID, value=int(row["id"]))


async def move(
    bot: Any, guild: Any, actor: Any, question_id: Any, direction: str, *, via: str = VIA_DISCORD
) -> Outcome:
    row, refused = await queued_one(bot, guild, question_id)
    if refused is not None:
        return refused
    rows = await store.queued(bot.db, guild.id)
    at = next(place for place, one in enumerate(rows) if one["id"] == row["id"])
    other = at - 1 if direction == "up" else at + 1
    if direction not in ("up", "down") or not 0 <= other < len(rows):
        end = "top" if direction == "up" else "bottom"
        return refusal(rules.NOT_MOVED.format(end=end), "not_moved", 409)
    await store.swap(bot.db, rows[at], rows[other])
    await log_action(
        bot,
        guild,
        kind_via("question.moved", via),
        actor=actor,
        details={"via": via, "question_id": int(row["id"]), "direction": direction},
    )
    return Outcome(True, rules.MOVED.format(direction=direction), value=int(row["id"]))


async def requeue(
    bot: Any, guild: Any, actor: Any, question_id: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    row = await store.get(bot.db, guild.id, int(question_id))
    if row is None:
        return refusal(rules.NO_SUCH, "no_question", 404)
    if row["status"] != rules.REMOVED:
        return refusal(rules.NOT_REMOVED.format(status=row["status"]), "not_removed", 409)
    await store.back_in_queue(bot.db, guild.id, row["id"], top=False)
    await log_action(
        bot,
        guild,
        kind_via("question.requeued", via),
        actor=actor,
        details={"via": via, "question_id": int(row["id"]), "question": row["body"]},
    )
    return Outcome(True, rules.REQUEUED, value=int(row["id"]))


async def post_now(
    bot: Any, guild: Any, actor: Any, *, via: str = VIA_DISCORD, now: datetime | None = None
) -> Outcome:
    async with lock_of(bot, guild.id):
        return await _post_now(bot, guild, actor, via, moment(now))


async def _post_now(bot: Any, guild: Any, actor: Any, via: str, now: datetime) -> Outcome:
    mode = rules.mode_of(bot.store, guild.id)
    if mode == rules.OFF:
        return refusal(rules.QUESTIONS_OFF, "questions_off", 409)
    question = await store.first_queued(bot.db, guild.id)
    if question is None:
        return refusal(rules.QUEUE_EMPTY, "queue_empty", 409)
    slot, row = await candidate(bot, guild, now)
    due = slot <= now and row["status"] == rules.PENDING
    channel, message, why = await send_question(bot, guild, mode, question["body"])
    if message is None:
        return refusal(why or rules.POST_REFUSED.format(why="unknown"), "not_posted", 409)
    key = rules.slot_key(slot) if due else None
    await store.mark_posted(bot.db, question["id"], key, rules.BY_BOT, channel.id, message.id, now)
    details = {
        "via": via,
        "question_id": int(question["id"]),
        "question": question["body"],
        "channel_id": channel.id,
        "message_id": message.id,
        "mode": mode,
    }
    if due:
        await store.set_slot(
            bot.db, guild.id, key, rules.POSTED, now, question_id=int(question["id"])
        )
        schedule = rules.schedule_of(bot.store, guild.id)
        details = slot_details(slot, schedule, mode) | details | {"reason": "posted now by staff"}
    if due:
        await log_action(
            bot, guild, kind_via("question.posted_by_bot", via), actor=actor, details=details
        )
    else:
        await log_action(
            bot, guild, kind_via("question.posted_extra", via), actor=actor, details=details
        )
    await open_thread(bot, guild, message, question["body"], key)
    said = rules.POSTED_NOW if due else rules.POSTED_EXTRA
    return Outcome(True, said.format(where=f"<#{channel.id}>"), value=int(question["id"]))


async def skip(
    bot: Any, guild: Any, actor: Any, *, via: str = VIA_DISCORD, now: datetime | None = None
) -> Outcome:
    async with lock_of(bot, guild.id):
        when = moment(now)
        slot, row = await candidate(bot, guild, when)
        if row["status"] not in (rules.PENDING, rules.SKIPPED_EMPTY):
            state = rules.STATE_WORDS.get(str(row["status"]), str(row["status"]))
            return refusal(rules.NOT_SKIPPABLE.format(state=state), "not_skippable", 409)
        key = rules.slot_key(slot)
        await store.set_slot(bot.db, guild.id, key, rules.SKIPPED, when)
        schedule = rules.schedule_of(bot.store, guild.id)
        await log_action(
            bot,
            guild,
            kind_via("question.skipped", via),
            actor=actor,
            details=slot_details(slot, schedule, rules.mode_of(bot.store, guild.id)) | {"via": via},
        )
        return Outcome(True, rules.SKIPPED_SAID, value=key)


async def unskip(
    bot: Any, guild: Any, actor: Any, *, via: str = VIA_DISCORD, now: datetime | None = None
) -> Outcome:
    async with lock_of(bot, guild.id):
        when = moment(now)
        slot, row = await candidate(bot, guild, when)
        schedule = rules.schedule_of(bot.store, guild.id)
        if slot <= when or row["status"] != rules.SKIPPED:
            if await skipped_and_passed(bot, guild, schedule, when):
                return refusal(rules.SKIP_PASSED, "slot_passed", 409)
            return refusal(rules.NOT_SKIPPED, "not_skipped", 409)
        key = rules.slot_key(slot)
        await store.set_slot(bot.db, guild.id, key, rules.PENDING, when)
        await log_action(
            bot,
            guild,
            kind_via("question.unskipped", via),
            actor=actor,
            details=slot_details(slot, schedule, rules.mode_of(bot.store, guild.id)) | {"via": via},
        )
        return Outcome(True, rules.UNSKIPPED, value=key)


async def skipped_and_passed(
    bot: Any, guild: Any, schedule: rules.Schedule, now: datetime
) -> bool:
    last, _ = rules.slots_around(now, schedule)
    row = await store.get_slot(bot.db, guild.id, rules.slot_key(last))
    return row is not None and row["status"] == rules.SKIPPED


async def take_down(
    bot: Any,
    guild: Any,
    actor: Any,
    question_id: Any,
    *,
    via: str = VIA_DISCORD,
    now: datetime | None = None,
) -> Outcome:
    async with lock_of(bot, guild.id):
        return await _take_down(bot, guild, actor, question_id, via, moment(now))


async def _take_down(
    bot: Any, guild: Any, actor: Any, question_id: Any, via: str, now: datetime
) -> Outcome:
    row = await store.get(bot.db, guild.id, int(question_id))
    if row is None:
        return refusal(rules.NO_SUCH, "no_question", 404)
    if row["status"] != rules.POSTED:
        return refusal(rules.NOT_POSTED.format(status=row["status"]), "not_posted", 409)
    if row["posted_by"] != rules.BY_BOT:
        return refusal(rules.NOT_BOTS, "not_bots", 409)
    gone = await delete_post(bot, guild, row)
    if gone is not None:
        return refusal(rules.DELETE_REFUSED.format(why=gone), "not_deleted", 409)
    await store.back_in_queue(bot.db, guild.id, row["id"], top=True)
    if row["slot_at"]:
        await store.set_slot(
            bot.db, guild.id, row["slot_at"], rules.TAKEN_DOWN, now, question_id=int(row["id"])
        )
    await log_action(
        bot,
        guild,
        kind_via("question.taken_down", via),
        actor=actor,
        details={
            "via": via,
            "question_id": int(row["id"]),
            "question": row["body"],
            "slot_at": row["slot_at"],
            "channel_id": row["channel_id"],
            "message_id": row["message_id"],
        },
    )
    return Outcome(True, rules.TAKEN_DOWN_SAID, value=int(row["id"]))


async def delete_post(bot: Any, guild: Any, row: Any) -> str | None:
    """None once the bot's message is gone (or already was); otherwise Discord's reason."""
    channel = shadow_home.channel_of(bot, guild, row["channel_id"])
    if channel is None or not row["message_id"]:
        return None
    try:
        await channel.get_partial_message(int(row["message_id"])).delete()
    except DELETE_GONE:
        return None
    except discord.HTTPException as exc:
        return f"{exc.status} {exc.text}".strip()
    return None
