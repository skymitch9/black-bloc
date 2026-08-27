from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ...actionlog import log_action
from ...command_errors import NETWORK_ERRORS, AnswersErrors, SafeDynamicItem
from ...golive import now_iso, parse_ts
from ...polls import (
    ARCHIVED,
    BUTTONS_UP_TO,
    CADENCES,
    CANCELLED,
    CLOSED,
    DATE,
    DATE_PLAIN,
    DATE_STEPS,
    DEFAULT_HOURS,
    DENIED,
    KINDS,
    LABEL_LIMIT,
    LIVE,
    MAX_HOURS,
    MAX_SLOTS,
    MAX_STEP,
    MIN_HOURS,
    MIN_SLOTS,
    NATIVE,
    NOT_A_RECURRENCE,
    OPEN,
    OPEN_STATUSES,
    PANEL,
    PANEL_CLEAR,
    PANEL_VOTE,
    PENDING_REVIEW,
    PICK_SOMETHING,
    QUESTION_LIMIT,
    RECUR_DELETED,
    RECUR_NONE,
    RECUR_NOT_A_DATE,
    RECUR_PAUSED,
    RECUR_RESUMED,
    RECUR_SAVED,
    RECURRING,
    RESULTS_CHOICES,
    SINGLE,
    STEP_DAYS,
    TERMINAL_STATUSES,
    VOTE_GONE,
    VOTE_NOT_OPEN,
    NeedsPanel,
    cadence_token,
    cadence_trouble,
    can_transition,
    clamp,
    closed_text,
    closes_at,
    counts_from_options,
    date_slots,
    date_trouble,
    describe_cadence,
    describe_hours,
    is_multi,
    mentions,
    next_occurrence,
    open_text,
    options_for,
    panel_embed,
    panel_note,
    reminder_text,
    results_embed,
    review_card,
    surface_for,
    thread_name,
    validate,
    voted_text,
    winners,
)
from ...settings_store import (
    DB_UNAVAILABLE,
    GUILD_ONLY,
    POLL_ARCHIVE_MAX_DAYS,
    POLL_ARCHIVE_MIN_DAYS,
    POLL_CREATORS,
    POLL_DATE_LABEL_FORMS,
    POLL_MODES,
    POLL_REMINDER_MAX_MINUTES,
    POLL_REVIEW_MODES,
    require_staff,
    staff_roles_sentence,
)
from ...timezones import DEFAULT_TZ

log = logging.getLogger(__name__)

DECISION_TEMPLATE = r"poll:(?P<poll_id>[0-9]+):(?P<action>approve|deny)"
VOTE_TEMPLATE = r"poll:v:(?P<poll_id>[0-9]+):(?P<position>[0-9]+)"
VOTE_OPEN_TEMPLATE = r"poll:vm:(?P<poll_id>[0-9]+)"
VOTE_CLEAR_TEMPLATE = r"poll:vc:(?P<poll_id>[0-9]+)"
LOCKS_ATTR = "_poll_locks"
POLL_MINUTES = 5
LOOP_NAMES = ("polls",)
LIST_LIMIT = 25
MODAL_TITLE_LIMIT = 45
LABEL_TEXT_LIMIT = 45
GROUP_OPTIONS_UP_TO = 10

POLLS_OFF = (
    "Polls are turned off on this server, so nothing was posted. A Lead turns them back on with "
    "`/poll settings mode:on` — ask one if you have something to put to the room."
)
NOT_A_CREATOR = (
    "Polls are staff-only on this server right now, so nothing was posted. Ask a Lead to run it "
    "for you, or to open `/poll settings who_can_create:everyone`."
)
NO_CHANNEL = (
    "Black Bloc could not work out which channel this poll would go in, so nothing was posted. "
    "Run the command from the channel you want it in."
)
CANNOT_POST = (
    "Discord refused to post the poll, so nothing went up. Black Bloc needs Send Messages in this "
    "channel — the log says exactly what came back. Tell a Lead, then try again."
)
POSTED = "Your poll is up: {url}"
POSTED_NO_LINK = "Your poll is up in this channel."
THREAD_FAILED = " Black Bloc could not open the discussion thread; the log says why."
SENT_FOR_REVIEW = (
    "**{question}** is in — a Lead will approve or deny it and Black Bloc will DM you either "
    "way. {where}"
)
REVIEW_HERE = "Their card is in {channel}."
REVIEW_NO_CARD = (
    "Black Bloc could not post the review card in {channel} — the log says why, and a Lead can "
    "still decide it there by hand."
)
NO_REVIEW_CHANNEL = (
    "Black Bloc has nowhere to send a poll for review, so nothing was posted. A Lead points it at "
    "one with `/settings set staff_channel_id:<the staff channel>`, or turns the review off with "
    "`/poll settings review:off`."
)
NOT_AN_ID = "**{given}** is not a poll number, so nothing was done. `/poll list` has them."
NO_SUCH_POLL = (
    "Black Bloc has no record of that poll any more, so nothing was done. `/poll list` shows the "
    "ones it still knows about."
)
NOT_OPEN = "Poll #{poll_id} is already **{status}**, so nothing was changed."
NOT_YOURS = (
    "Poll #{poll_id} is not yours, so nothing was closed. Only the person who started it or a "
    "member of staff can close it early."
)
DENIED_SAID = "Denied, and the person who asked has been told why."
APPROVED_POSTED = "Approved and posted: {where}"
APPROVED_NOT_POSTED = (
    "Approved, but nothing was posted, so the poll is marked cancelled — the log says why "
    "(`{reason}`). Ask them to start it again once that is fixed."
)
ENDED = "Poll #{poll_id} is closed and the result is posted."
ENDED_NO_RESULT = (
    "Poll #{poll_id} is marked closed, but Black Bloc could not read the final count back from "
    "Discord — the log says why, and the numbers on the message itself are the real ones."
)
CANCELLED_SAID = (
    "Poll #{poll_id} is cancelled. The vote is closed at Discord and no result was posted."
)
ALREADY_DECIDED = (
    "Somebody got there first — poll #{poll_id} is already **{status}**, so nothing was changed."
)
NO_OPEN_POLLS = "Nothing is running — `/poll create` starts one."
GUARDED = (
    "Black Bloc is in **test mode**, so it will not touch a poll outside <#{channel_id}>. "
    "Nothing was done."
)
DM_APPROVED = "Your poll **{question}** was approved on **{guild}** and is up now."
DM_DENIED = (
    "Your poll **{question}** was not approved on **{guild}**. The reason given was: {reason}. "
    "Ask a Lead there if you want to talk it over — Black Bloc cannot change the decision."
)
DM_APPROVED_NOT_POSTED = (
    "Your poll **{question}** was approved on **{guild}**, but Black Bloc could not post it — "
    "the log says why. Ask a Lead to try it again."
)
NO_STAFF_WARNING = (
    "⚠️ **No staff roles resolve**, so nobody but server admins can press Approve. Point "
    "`staff_channel_id` at a channel only staff can see with `/settings set staff_channel_id`."
)


async def create_poll(
    db: Any,
    guild_id: int,
    creator_id: int,
    *,
    question: str,
    kind: str,
    surface: str,
    multi: bool,
    anonymous: bool,
    results: str,
    hours: int,
    channel_id: int | None,
    ping_role_id: int | None,
    status: str,
    auto_thread: bool = False,
) -> int | None:
    cur = await db.conn.execute(
        "INSERT INTO polls(guild_id, creator_id, question, kind, surface, multi, anonymous, "
        "results, hours, auto_thread, channel_id, ping_role_id, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            guild_id,
            creator_id,
            question,
            kind,
            surface,
            int(bool(multi)),
            int(bool(anonymous)),
            results,
            int(hours),
            int(bool(auto_thread)),
            channel_id,
            ping_role_id,
            status,
            now_iso(),
        ),
    )
    await db.conn.commit()
    return cur.lastrowid


async def add_options(db: Any, poll_id: int, labels: Any, values: Any = None) -> None:
    """`value` is the instant a date slot stands for; every other kind leaves it empty."""
    found = list(labels or ())
    stored = list(values or ()) + [None] * len(found)
    await db.conn.executemany(
        "INSERT INTO poll_options(poll_id, position, label, value) VALUES (?, ?, ?, ?)",
        [(poll_id, at, label, stored[at]) for at, label in enumerate(found)],
    )
    await db.conn.commit()


def poll_plan(store: Any, guild_id: int, **asked: Any) -> tuple[dict[str, Any] | None, str | None]:
    """(what to post, the refusal). The one place a poll's arguments become a poll."""
    kind = str(asked.get("kind") or SINGLE)
    results = str(asked.get("results") or LIVE)
    anonymous = bool(asked.get("anonymous"))
    hours = asked.get("hours")
    length = (
        int(hours)
        if hours is not None
        else int(store.get(guild_id, "poll_default_hours") or DEFAULT_HOURS)
    )
    if kind == DATE:
        unit = str(asked.get("step_unit") or STEP_DAYS)
        trouble = date_trouble(asked.get("start"), asked.get("slots"), asked.get("step"), unit)
        if trouble is not None:
            return (None, trouble)
        made = date_slots(
            asked.get("start"),
            asked.get("slots"),
            asked.get("step"),
            unit,
            form=str(store.get(guild_id, "poll_date_labels") or DATE_PLAIN),
        )
        labels = [row["label"] for row in made]
        values: list[str | None] = [row["value"] for row in made]
    else:
        labels = options_for(kind, asked.get("options"))
        values = [None] * len(labels)
    refusal = validate(asked.get("question"), labels, length)
    if refusal is not None:
        return (None, refusal)
    try:
        surface = surface_for(kind, anonymous, results, len(labels))
    except NeedsPanel as needed:
        return (None, str(needed))
    return (
        {
            "question": clamp(asked.get("question"), QUESTION_LIMIT),
            "kind": kind,
            "labels": labels,
            "values": values,
            "hours": length,
            "surface": surface,
            "multi": is_multi(kind),
            "anonymous": anonymous,
            "results": results,
            "note": panel_note(anonymous, results, len(labels)),
        },
        None,
    )


async def store_poll(
    bot: Any,
    guild: Any,
    creator_id: int,
    plan: dict[str, Any],
    *,
    channel_id: int | None,
    ping_role_id: int | None,
    auto_thread: bool,
    status: str | None = None,
) -> tuple[Any, bool]:
    """A plan written down as a row, its options and one log line: (the row, is it held)."""
    reviewing = status is None and bot.store.get(guild.id, "poll_review_mode") == "on"
    poll_id = await create_poll(
        bot.db,
        guild.id,
        creator_id,
        question=plan["question"],
        kind=plan["kind"],
        surface=plan["surface"],
        multi=plan["multi"],
        anonymous=plan["anonymous"],
        results=plan["results"],
        hours=plan["hours"],
        channel_id=channel_id,
        ping_role_id=ping_role_id,
        status=status or (PENDING_REVIEW if reviewing else OPEN),
        auto_thread=auto_thread,
    )
    await add_options(bot.db, poll_id, plan["labels"], plan.get("values"))
    await log_action(
        bot,
        guild,
        "poll.created",
        actor=creator_id,
        target=creator_id,
        details={
            "poll_id": poll_id,
            "kind": plan["kind"],
            "surface": plan["surface"],
            "options": len(plan["labels"]),
            "hours": plan["hours"],
            "review": reviewing,
        },
    )
    return (await get_poll(bot.db, poll_id), reviewing)


async def get_poll(db: Any, poll_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM polls WHERE id = ?", (poll_id,))
    return await cur.fetchone()


async def options_of(db: Any, poll_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM poll_options WHERE poll_id = ? ORDER BY position", (poll_id,)
    )
    return list(await cur.fetchall())


async def polls_by_status(db: Any, guild_id: int, statuses: Any) -> list[Any]:
    """Polls only: a recurrence is a template that makes them, not one of them."""
    marks = ", ".join("?" for _ in statuses)
    cur = await db.conn.execute(
        f"SELECT * FROM polls WHERE guild_id = ? AND status IN ({marks}) "
        "AND recurrence IS NULL ORDER BY id DESC",
        (guild_id, *statuses),
    )
    return list(await cur.fetchall())


async def recurrences(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM polls WHERE guild_id = ? AND status = ? AND recurrence IS NOT NULL "
        "ORDER BY id DESC",
        (guild_id, RECURRING),
    )
    return list(await cur.fetchall())


async def get_recurrence(db: Any, guild_id: int, poll_id: int) -> Any:
    row = await get_poll(db, poll_id)
    if row is None or row["guild_id"] != guild_id or not row["recurrence"]:
        return None
    return row if row["status"] == RECURRING else None


async def set_recurrence(
    db: Any, poll_id: int, token: str, at_local: str, tz_name: str, next_at: Any
) -> None:
    await db.conn.execute(
        "UPDATE polls SET recurrence = ?, recur_at = ?, recur_tz = ?, recur_next_at = ? "
        "WHERE id = ?",
        (token, at_local, tz_name, next_at, poll_id),
    )
    await db.conn.commit()


async def set_recur_next(db: Any, poll_id: int, next_at: Any) -> None:
    await db.conn.execute(
        "UPDATE polls SET recur_next_at = ? WHERE id = ?", (next_at, poll_id)
    )
    await db.conn.commit()


async def claim_occurrence(db: Any, poll_id: int, was: Any, following: str) -> bool:
    """True only for the pass that moved the clock on, so one due time opens one poll."""
    cur = await db.conn.execute(
        "UPDATE polls SET recur_next_at = ? WHERE id = ? AND recur_next_at = ? AND status = ?",
        (following, poll_id, was, RECURRING),
    )
    await db.conn.commit()
    return bool(cur.rowcount)


async def set_schedule(db: Any, poll_id: int, schedule_id: int) -> None:
    await db.conn.execute(
        "UPDATE polls SET schedule_id = ? WHERE id = ?", (schedule_id, poll_id)
    )
    await db.conn.commit()


async def set_status(
    db: Any,
    poll_id: int,
    status: str,
    *,
    decided_by: int | None = None,
    deny_reason: str | None = None,
    closed: bool = False,
) -> None:
    await db.conn.execute(
        "UPDATE polls SET status = ?, decided_by = COALESCE(?, decided_by), "
        "decided_at = COALESCE(?, decided_at), deny_reason = COALESCE(?, deny_reason), "
        "closed_at = COALESCE(?, closed_at) WHERE id = ?",
        (
            status,
            decided_by,
            now_iso() if decided_by is not None else None,
            deny_reason,
            now_iso() if closed else None,
            poll_id,
        ),
    )
    await db.conn.commit()


async def set_posted(
    db: Any,
    poll_id: int,
    *,
    channel_id: int,
    message_id: int,
    finishes_at: datetime,
    thread_id: int | None = None,
) -> None:
    await db.conn.execute(
        "UPDATE polls SET channel_id = ?, message_id = ?, closes_at = ?, thread_id = ?, "
        "opens_at = COALESCE(opens_at, ?) WHERE id = ?",
        (channel_id, message_id, finishes_at.isoformat(), thread_id, now_iso(), poll_id),
    )
    await db.conn.commit()


async def set_review(db: Any, poll_id: int, channel_id: int | None, message_id: int | None) -> None:
    await db.conn.execute(
        "UPDATE polls SET review_channel_id = ?, review_message_id = ? WHERE id = ?",
        (channel_id, message_id, poll_id),
    )
    await db.conn.commit()


async def set_answer_ids(db: Any, poll_id: int, answer_ids: Any) -> None:
    """Discord owns the answer ids; they are read back off the posted message, never guessed."""
    await db.conn.executemany(
        "UPDATE poll_options SET answer_id = ? WHERE poll_id = ? AND position = ?",
        [(answer_id, poll_id, position) for position, answer_id in enumerate(answer_ids or ())],
    )
    await db.conn.commit()


async def claim_reminder(db: Any, poll_id: int) -> bool:
    """True only for the caller that got there first, so a restart cannot double-ping."""
    cur = await db.conn.execute(
        "UPDATE polls SET reminded_at = ? WHERE id = ? AND reminded_at IS NULL",
        (now_iso(), poll_id),
    )
    await db.conn.commit()
    return bool(cur.rowcount)


async def clear_reminder(db: Any, poll_id: int) -> None:
    await db.conn.execute("UPDATE polls SET reminded_at = NULL WHERE id = ?", (poll_id,))
    await db.conn.commit()


async def save_results(db: Any, poll_id: int, counts: Any, total: int) -> None:
    """One results row per poll, written once, kept when the votes are dropped at archive."""
    await db.conn.executemany(
        "UPDATE poll_options SET final_votes = ? WHERE poll_id = ? AND position = ?",
        [(int(row["votes"]), poll_id, int(row["position"])) for row in counts or ()],
    )
    top = winners(counts)
    await db.conn.execute(
        "INSERT OR REPLACE INTO poll_results(poll_id, closed_at, total_votes, winner_position, "
        "counts) VALUES (?, ?, ?, ?, ?)",
        (
            poll_id,
            now_iso(),
            int(total),
            int(top[0]["position"]) if len(top) == 1 else None,
            json.dumps(list(counts or ())),
        ),
    )
    await db.conn.execute(
        "UPDATE polls SET total_votes = ? WHERE id = ?", (int(total), poll_id)
    )
    await db.conn.commit()


async def results_of(db: Any, poll_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM poll_results WHERE poll_id = ?", (poll_id,))
    return await cur.fetchone()


async def record_vote(db: Any, poll_id: int, option_id: int, user_id: int) -> None:
    await db.conn.execute(
        "INSERT OR IGNORE INTO poll_votes(poll_id, option_id, user_id, at) VALUES (?, ?, ?, ?)",
        (poll_id, option_id, user_id, now_iso()),
    )
    await db.conn.commit()


async def forget_vote(db: Any, poll_id: int, option_id: int, user_id: int) -> None:
    await db.conn.execute(
        "DELETE FROM poll_votes WHERE poll_id = ? AND option_id = ? AND user_id = ?",
        (poll_id, option_id, user_id),
    )
    await db.conn.commit()


async def votes_of(db: Any, poll_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT v.user_id, v.option_id, v.at, o.position, o.label FROM poll_votes v "
        "LEFT JOIN poll_options o ON o.id = v.option_id WHERE v.poll_id = ? "
        "ORDER BY o.position, v.at",
        (poll_id,),
    )
    return list(await cur.fetchall())


def voter_key(row: Any, user_id: Any) -> int:
    """An anonymous poll counts one vote per person without keeping who the person is."""
    if not row["anonymous"]:
        return int(user_id)
    digest = hashlib.sha256(f"{int(row['id'])}:{int(user_id)}".encode()).digest()
    return int.from_bytes(digest[:8], "big") >> 1


async def panel_counts(db: Any, poll_id: int) -> tuple[list[dict[str, Any]], int]:
    """Per-option totals and the number of people who voted — a panel's own tally."""
    options = await options_of(db, poll_id)
    cur = await db.conn.execute(
        "SELECT option_id, COUNT(*) AS votes FROM poll_votes WHERE poll_id = ? GROUP BY option_id",
        (poll_id,),
    )
    tally = {
        int(row["option_id"]): int(row["votes"])
        for row in await cur.fetchall()
        if row["option_id"] is not None
    }
    cur = await db.conn.execute(
        "SELECT COUNT(DISTINCT user_id) AS voters FROM poll_votes WHERE poll_id = ?", (poll_id,)
    )
    counted = await cur.fetchone()
    return (
        [
            {
                "position": int(item["position"]),
                "label": str(item["label"]),
                "votes": tally.get(int(item["id"]), 0),
            }
            for item in options
        ],
        int((counted["voters"] if counted else 0) or 0),
    )


async def my_positions(db: Any, poll_id: int, voter: int) -> list[int]:
    cur = await db.conn.execute(
        "SELECT o.position FROM poll_votes v JOIN poll_options o ON o.id = v.option_id "
        "WHERE v.poll_id = ? AND v.user_id = ? ORDER BY o.position",
        (poll_id, voter),
    )
    return [int(row["position"]) for row in await cur.fetchall()]


async def set_panel_vote(
    db: Any, poll_id: int, voter: int, positions: Any, *, multi: bool
) -> list[str]:
    """One person's whole answer, written as a replacement — never an append."""
    by_position = {int(item["position"]): item for item in await options_of(db, poll_id)}
    wanted = sorted({int(one) for one in positions or () if int(one) in by_position})
    if not multi:
        wanted = wanted[:1]
    await db.conn.execute(
        "DELETE FROM poll_votes WHERE poll_id = ? AND user_id = ?", (poll_id, voter)
    )
    await db.conn.executemany(
        "INSERT OR IGNORE INTO poll_votes(poll_id, option_id, user_id, at) VALUES (?, ?, ?, ?)",
        [(poll_id, by_position[at]["id"], voter, now_iso()) for at in wanted],
    )
    await db.conn.commit()
    return [str(by_position[at]["label"]) for at in wanted]


async def option_for_answer(db: Any, poll_id: int, answer_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM poll_options WHERE poll_id = ? AND answer_id = ?", (poll_id, answer_id)
    )
    return await cur.fetchone()


async def poll_for_message(db: Any, message_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM polls WHERE message_id = ?", (message_id,))
    return await cur.fetchone()


async def due_polls(db: Any, status: str, column: str, before: str) -> list[Any]:
    cur = await db.conn.execute(
        f"SELECT * FROM polls WHERE status = ? AND {column} IS NOT NULL AND {column} <= ? "
        "ORDER BY id",
        (status, before),
    )
    return list(await cur.fetchall())


async def reminders_due(db: Any, before: str) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM polls WHERE status = ? AND reminded_at IS NULL AND closes_at IS NOT NULL "
        "AND closes_at <= ? ORDER BY id",
        (OPEN, before),
    )
    return list(await cur.fetchall())


async def archivable(db: Any, guild_id: int, before: str) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM polls WHERE guild_id = ? AND status IN (?, ?) AND closed_at IS NOT NULL "
        "AND closed_at <= ? ORDER BY id",
        (guild_id, CLOSED, CANCELLED, before),
    )
    return list(await cur.fetchall())


async def archive_poll(db: Any, poll_id: int, *, drop_votes: bool) -> int:
    dropped = 0
    if drop_votes:
        cur = await db.conn.execute("DELETE FROM poll_votes WHERE poll_id = ?", (poll_id,))
        dropped = max(int(cur.rowcount or 0), 0)
        await db.conn.execute(
            "UPDATE poll_results SET votes_dropped = ? WHERE poll_id = ?", (dropped, poll_id)
        )
    await db.conn.execute(
        "UPDATE polls SET status = ?, archived_at = ? WHERE id = ?",
        (ARCHIVED, now_iso(), poll_id),
    )
    await db.conn.commit()
    return dropped


def poll_lock(bot: Any, poll_id: int) -> asyncio.Lock:
    locks = getattr(bot, LOCKS_ATTR, None)
    if locks is None:
        locks = {}
        setattr(bot, LOCKS_ATTR, locks)
    lock = locks.get(poll_id)
    if lock is None:
        lock = locks[poll_id] = asyncio.Lock()
    return lock


def drop_lock(bot: Any, poll_id: int) -> None:
    locks = getattr(bot, LOCKS_ATTR, None)
    if locks is not None:
        locks.pop(poll_id, None)


def decision_id(poll_id: int, action: str) -> str:
    return f"poll:{poll_id}:{action}"


def guard_allows(bot: Any, channel: Any) -> bool:
    """The one place the polls cog asks the guard; `end_poll` and `voters` bypass its patch."""
    guard = getattr(bot, "guard", None)
    return guard is None or guard.allows_channel(channel)


def guard_refusal(bot: Any) -> str:
    guard = getattr(bot, "guard", None)
    if guard is None:
        return GUARDED.format(channel_id="the test channel")
    return guard.refusal_message()


def native_poll(row: Any, labels: Any) -> discord.Poll:
    made = discord.Poll(
        question=clamp(row["question"], 300),
        duration=timedelta(hours=int(row["hours"])),
        multiple=bool(row["multi"]),
    )
    for label in labels:
        made.add_answer(text=label)
    return made


def counts_from_message(message: Any, options: Any) -> tuple[list[dict[str, Any]], int]:
    """The stored options paired with Discord's own counts, which are exact once finalised."""
    poll = getattr(message, "poll", None)
    answers = {int(answer.id): int(answer.vote_count) for answer in getattr(poll, "answers", ())}
    counts = [
        {
            "position": int(row["position"]),
            "label": str(row["label"]),
            "votes": answers.get(int(row["answer_id"] or 0), 0),
        }
        for row in options
    ]
    return counts, sum(row["votes"] for row in counts)


def card_channel(bot: Any, guild: Any) -> Any:
    """Where a review card may go: the staff channel, or the test channel while guarded."""
    guard = getattr(bot, "guard", None)
    if guard is not None:
        return bot.get_channel(guard.test_channel_id) if guard.test_channel_id else None
    channel_id = bot.store.get(guild.id, "staff_channel_id")
    return bot.get_channel(channel_id) if channel_id else None


def review_view(poll_id: int) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(PollDecisionButton(poll_id, "approve"))
    view.add_item(PollDecisionButton(poll_id, "deny"))
    return view


def panel_card(
    row: Any, counts: Any, voters: int, finishes: datetime | None = None
) -> discord.Embed:
    """One home for the panel's card, so the post, every vote and the close agree."""
    return panel_embed(
        poll_id=row["id"],
        question=row["question"],
        counts=counts,
        voters=voters,
        kind=row["kind"],
        multi=bool(row["multi"]),
        anonymous=bool(row["anonymous"]),
        hidden=row["results"] != LIVE,
        status=row["status"],
        closes_at=finishes if finishes is not None else parse_ts(row["closes_at"]),
    )


def panel_view(row: Any, options: Any) -> discord.ui.View:
    """A button per option while there are few enough; one that opens a modal when there are not."""
    view = discord.ui.View(timeout=None)
    found = list(options or ())
    poll_id = int(row["id"])
    if len(found) <= BUTTONS_UP_TO:
        for item in found:
            view.add_item(PollVoteButton(poll_id, int(item["position"]), str(item["label"])))
    else:
        view.add_item(PollOpenVoteButton(poll_id))
    view.add_item(PollClearVoteButton(poll_id))
    return view


async def repaint_panel(bot: Any, row: Any, options: Any = None) -> None:
    """The panel message caught up with the votes; a cosmetic failure never fails a vote."""
    if row["surface"] != PANEL or not row["message_id"]:
        return
    if not guard_allows(bot, row["channel_id"]):
        return
    message = await fetch_poll_message(bot, row)
    if message is None:
        return
    counts, voters = await panel_counts(bot.db, row["id"])
    found = options if options is not None else await options_of(bot.db, row["id"])
    try:
        await message.edit(
            embed=panel_card(row, counts, voters),
            view=panel_view(row, found) if row["status"] == OPEN else None,
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except Exception as exc:
        log.warning("polls: could not repaint the panel of poll %s: %s", row["id"], exc)


async def voting_row(interaction: discord.Interaction, poll_id: int) -> Any:
    """The poll a button press is about, or None with the presser already answered."""
    bot = interaction.client
    if not bot.db.is_connected:
        await answer(interaction, DB_UNAVAILABLE)
        return None
    row = await get_poll(bot.db, poll_id)
    if row is None:
        await answer(interaction, VOTE_GONE)
        return None
    if row["status"] != OPEN:
        await answer(interaction, VOTE_NOT_OPEN.format(status=row["status"]))
        return None
    return row


async def cast_vote(interaction: discord.Interaction, row: Any, positions: Any) -> list[str]:
    bot = interaction.client
    async with poll_lock(bot, row["id"]):
        chosen = await set_panel_vote(
            bot.db, row["id"], voter_key(row, interaction.user.id), positions,
            multi=bool(row["multi"]),
        )
    await repaint_panel(bot, row)
    return chosen


class PollVoteButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=VOTE_TEMPLATE
):
    def __init__(self, poll_id: int, position: int, label: str = "") -> None:
        self.poll_id = poll_id
        self.position = position
        super().__init__(
            discord.ui.Button(
                label=clamp(label, LABEL_LIMIT) or f"Option {position + 1}",
                style=discord.ButtonStyle.secondary,
                custom_id=f"poll:v:{poll_id}:{position}",
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["poll_id"]), int(match["position"]), str(item.label or ""))

    async def on_click(self, interaction: discord.Interaction) -> None:
        row = await voting_row(interaction, self.poll_id)
        if row is None:
            return
        await interaction.response.defer(ephemeral=True)
        wanted = [self.position]
        if row["multi"]:
            standing = await my_positions(
                interaction.client.db, row["id"], voter_key(row, interaction.user.id)
            )
            wanted = [at for at in standing if at != self.position]
            if self.position not in standing:
                wanted.append(self.position)
        chosen = await cast_vote(interaction, row, wanted)
        await answer(interaction, voted_text(chosen, multi=bool(row["multi"])))


class PollClearVoteButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=VOTE_CLEAR_TEMPLATE
):
    def __init__(self, poll_id: int) -> None:
        self.poll_id = poll_id
        super().__init__(
            discord.ui.Button(
                label=PANEL_CLEAR,
                style=discord.ButtonStyle.secondary,
                custom_id=f"poll:vc:{poll_id}",
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["poll_id"]))

    async def on_click(self, interaction: discord.Interaction) -> None:
        row = await voting_row(interaction, self.poll_id)
        if row is None:
            return
        await interaction.response.defer(ephemeral=True)
        await cast_vote(interaction, row, ())
        await answer(interaction, voted_text((), multi=bool(row["multi"])))


class PollOpenVoteButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=VOTE_OPEN_TEMPLATE
):
    def __init__(self, poll_id: int) -> None:
        self.poll_id = poll_id
        super().__init__(
            discord.ui.Button(
                label=PANEL_VOTE,
                style=discord.ButtonStyle.primary,
                custom_id=f"poll:vm:{poll_id}",
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["poll_id"]))

    async def on_click(self, interaction: discord.Interaction) -> None:
        row = await voting_row(interaction, self.poll_id)
        if row is None:
            return
        options = await options_of(interaction.client.db, row["id"])
        standing = await my_positions(
            interaction.client.db, row["id"], voter_key(row, interaction.user.id)
        )
        await interaction.response.send_modal(PollVoteModal(row, options, standing))


def vote_picker(options: Any, *, multi: bool, standing: Any = ()) -> Any:
    """2.7.1's typed modal fields where they fit; a select once there are more than ten."""
    found = list(options or ())
    chosen = {int(at) for at in standing or ()}
    rows = [
        (str(item["position"]), clamp(item["label"], LABEL_LIMIT), int(item["position"]) in chosen)
        for item in found
    ]
    if len(rows) > GROUP_OPTIONS_UP_TO:
        return discord.ui.Select(
            options=[
                discord.SelectOption(label=label, value=value, default=picked)
                for value, label, picked in rows
            ],
            min_values=0,
            max_values=len(rows) if multi else 1,
            required=False,
        )
    if multi:
        return discord.ui.CheckboxGroup(
            options=[
                discord.CheckboxGroupOption(label=label, value=value, default=picked)
                for value, label, picked in rows
            ],
            min_values=0,
            max_values=len(rows),
            required=False,
        )
    return discord.ui.RadioGroup(
        options=[
            discord.RadioGroupOption(label=label, value=value, default=picked)
            for value, label, picked in rows
        ],
        required=False,
    )


def picked_values(picker: Any) -> list[str]:
    values = getattr(picker, "values", None)
    if values is not None:
        return [str(one) for one in values]
    one = getattr(picker, "value", None)
    return [str(one)] if one else []


class PollVoteModal(AnswersErrors, discord.ui.Modal):
    def __init__(self, row: Any, options: Any, standing: Any = ()) -> None:
        super().__init__(title=clamp(row["question"], MODAL_TITLE_LIMIT) or PANEL_VOTE)
        self.poll_id = int(row["id"])
        self.picker = vote_picker(options, multi=bool(row["multi"]), standing=standing)
        self.add_item(
            discord.ui.Label(
                text=clamp(PANEL_VOTE if row["multi"] else "Your vote", LABEL_TEXT_LIMIT),
                component=self.picker,
            )
        )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        row = await voting_row(interaction, self.poll_id)
        if row is None:
            return
        await interaction.response.defer(ephemeral=True)
        wanted = picked_values(self.picker)
        if not wanted:
            await answer(interaction, PICK_SOMETHING)
            return
        chosen = await cast_vote(interaction, row, [int(one) for one in wanted])
        await answer(interaction, voted_text(chosen, multi=bool(row["multi"])))


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
    send = getattr(user, "send", None)
    if send is None:
        return False
    try:
        await send(text, embed=embed, allowed_mentions=discord.AllowedMentions.none())
    except Exception as exc:
        log.info("polls: could not DM %s: %s", getattr(user, "id", "?"), exc)
        return False
    return True


async def fetch_poll_message(bot: Any, row: Any) -> Any:
    """The posted message, or None with the reason already logged."""
    channel_id, message_id = row["channel_id"], row["message_id"]
    if not channel_id or not message_id:
        return None
    channel = bot.get_channel(channel_id)
    if channel is None:
        log.info("polls: channel %s for poll %s is not visible", channel_id, row["id"])
        return None
    try:
        return await channel.fetch_message(message_id)
    except Exception as exc:
        log.info("polls: could not fetch message %s for poll %s: %s", message_id, row["id"], exc)
        return None


async def refresh_voters(bot: Any, row: Any, message: Any, options: Any) -> None:
    """Who voted, read once at close — the gateway events can miss and this cannot."""
    if row["anonymous"]:
        return
    if not guard_allows(bot, row["channel_id"]):
        log.warning("polls: TEST MODE — voters for poll %s were not read", row["id"])
        return
    poll = getattr(message, "poll", None)
    by_answer = {int(item["answer_id"] or 0): item for item in options}
    for found in getattr(poll, "answers", ()):
        option = by_answer.get(int(found.id))
        if option is None:
            continue
        try:
            async for voter in found.voters():
                await record_vote(bot.db, row["id"], option["id"], int(voter.id))
        except Exception as exc:
            log.warning(
                "polls: could not read the voters of poll %s answer %s — %s: %s",
                row["id"],
                found.id,
                type(exc).__name__,
                exc,
            )
            return


async def close_poll(
    bot: Any, guild: Any, row: Any, *, reason: str, actor: Any = None, end_it: bool = True
) -> tuple[bool, bool]:
    """(closed, results written). The status moves even when Discord will not answer."""
    async with poll_lock(bot, row["id"]):
        fresh = await get_poll(bot.db, row["id"])
        if fresh is None or not can_transition(fresh["status"], CLOSED):
            return (False, False)
        if not guard_allows(bot, fresh["channel_id"]):
            await log_action(
                bot,
                guild,
                "poll.would_close",
                details={"poll_id": fresh["id"], "reason": "test_mode"},
            )
            return (False, False)
        await set_status(bot.db, fresh["id"], CLOSED, closed=True)
        drop_lock(bot, fresh["id"])
        await log_action(
            bot,
            guild,
            "poll.closed",
            actor=actor,
            target=fresh["creator_id"],
            reason=reason,
            details={"poll_id": fresh["id"], "question": fresh["question"]},
        )
        written = await _write_results(bot, guild, fresh, end_it=end_it)
        return (True, written)


async def _write_results(bot: Any, guild: Any, row: Any, *, end_it: bool) -> bool:
    if row["surface"] == PANEL:
        return await _write_panel_results(bot, guild, row)
    message = await fetch_poll_message(bot, row)
    if message is None:
        await log_action(
            bot,
            guild,
            "poll.results_failed",
            details={"poll_id": row["id"], "reason": "no_message"},
        )
        return False
    poll = getattr(message, "poll", None)
    if end_it and poll is not None and not poll.is_finalised():
        try:
            message = await message.end_poll()
        except NETWORK_ERRORS as exc:
            log.warning("polls: could not end poll %s at Discord: %s", row["id"], exc)
            await log_action(
                bot,
                guild,
                "poll.end_failed",
                details={"poll_id": row["id"], "reason": f"{type(exc).__name__}: {exc}"},
            )
    options = await options_of(bot.db, row["id"])
    counts, total = counts_from_message(message, options)
    await save_results(bot.db, row["id"], counts, total)
    await refresh_voters(bot, row, message, options)
    await _post_results(bot, guild, row, message, counts, total)
    return True


async def _write_panel_results(bot: Any, guild: Any, row: Any) -> bool:
    """A panel's votes are ours, so the count is read from the rows rather than from Discord."""
    counts, voters = await panel_counts(bot.db, row["id"])
    await save_results(bot.db, row["id"], counts, voters)
    message = await fetch_poll_message(bot, row)
    if message is not None:
        await _shut_panel(bot, row, message, counts, voters)
    await _post_results(bot, guild, row, message, counts, voters)
    return True


async def _shut_panel(bot: Any, row: Any, message: Any, counts: Any, voters: int) -> None:
    """The buttons come off and the final bars go on, even for a poll that had hidden them."""
    settled = await get_poll(bot.db, row["id"])
    try:
        await message.edit(
            embed=panel_card(settled if settled is not None else row, counts, voters),
            view=None,
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except Exception as exc:
        log.warning("polls: could not take the buttons off poll %s: %s", row["id"], exc)


async def _post_results(
    bot: Any, guild: Any, row: Any, message: Any, counts: Any, total: int
) -> None:
    channel = bot.get_channel(row["channel_id"]) if row["channel_id"] else None
    if channel is None or not guard_allows(bot, channel):
        await log_action(
            bot,
            guild,
            "poll.would_post_results",
            details={"poll_id": row["id"], "channel_id": row["channel_id"]},
        )
        return
    embed = results_embed(
        poll_id=row["id"],
        question=row["question"],
        counts=counts,
        total=total,
        status=CLOSED,
        kind=row["kind"],
    )
    try:
        await channel.send(
            closed_text(row["question"]),
            embed=embed,
            reference=message if message is not None else None,
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except Exception as exc:
        log.warning("polls: could not post the result of poll %s: %s", row["id"], exc)
        await log_action(
            bot,
            guild,
            "poll.results_failed",
            details={"poll_id": row["id"], "reason": f"{type(exc).__name__}: {exc}"},
        )


async def cancel_poll(bot: Any, guild: Any, row: Any, *, by: Any = None) -> bool:
    """Stop a poll without publishing a result; the vote is ended at Discord all the same."""
    async with poll_lock(bot, row["id"]):
        fresh = await get_poll(bot.db, row["id"])
        if fresh is None or not can_transition(fresh["status"], CANCELLED):
            return False
        if fresh["message_id"] and not guard_allows(bot, fresh["channel_id"]):
            await log_action(
                bot,
                guild,
                "poll.would_cancel",
                details={"poll_id": fresh["id"], "reason": "test_mode"},
            )
            return False
        await set_status(bot.db, fresh["id"], CANCELLED, closed=True)
        drop_lock(bot, fresh["id"])
        await log_action(
            bot,
            guild,
            "poll.cancelled",
            actor=by,
            target=fresh["creator_id"],
            details={"poll_id": fresh["id"], "question": fresh["question"]},
        )
    if not fresh["message_id"]:
        return True
    message = await fetch_poll_message(bot, fresh)
    if fresh["surface"] == PANEL:
        if message is not None:
            counts, voters = await panel_counts(bot.db, fresh["id"])
            await _shut_panel(bot, fresh, message, counts, voters)
        return True
    poll = getattr(message, "poll", None) if message is not None else None
    if poll is None or poll.is_finalised():
        return True
    try:
        await message.end_poll()
    except NETWORK_ERRORS as exc:
        log.warning("polls: could not end cancelled poll %s: %s", fresh["id"], exc)
        await log_action(
            bot,
            guild,
            "poll.end_failed",
            details={"poll_id": fresh["id"], "reason": f"{type(exc).__name__}: {exc}"},
        )
    return True


async def post_poll(bot: Any, guild: Any, row: Any) -> tuple[Any, str | None]:
    """(the message, the reason there is not one). The one place a poll reaches a channel."""
    channel = bot.get_channel(row["channel_id"]) if row["channel_id"] else None
    if channel is None:
        await log_action(
            bot, guild, "poll.open_failed", details={"poll_id": row["id"], "reason": "no_channel"}
        )
        return (None, "no_channel")
    if not guard_allows(bot, channel):
        await log_action(
            bot, guild, "poll.would_open", details={"poll_id": row["id"], "reason": "test_mode"}
        )
        return (None, "test_mode")
    options = await options_of(bot.db, row["id"])
    labels = [str(item["label"]) for item in options]
    panel = row["surface"] == PANEL
    finishes = closes_at(int(row["hours"]))
    try:
        if panel:
            counts, voters = await panel_counts(bot.db, row["id"])
            message = await channel.send(
                open_text(row["creator_id"], row["ping_role_id"]),
                embed=panel_card(row, counts, voters, finishes),
                view=panel_view(row, options),
                allowed_mentions=mentions(row["ping_role_id"]),
            )
        else:
            message = await channel.send(
                open_text(row["creator_id"], row["ping_role_id"]),
                poll=native_poll(row, labels),
                allowed_mentions=mentions(row["ping_role_id"]),
            )
    except Exception as exc:
        log.warning("polls: could not post poll %s: %s", row["id"], exc)
        await log_action(
            bot,
            guild,
            "poll.open_failed",
            details={"poll_id": row["id"], "reason": f"{type(exc).__name__}: {exc}"},
        )
        return (None, f"{type(exc).__name__}: {exc}")
    thread_id = await _open_thread(bot, guild, row, message)
    await set_posted(
        bot.db,
        row["id"],
        channel_id=channel.id,
        message_id=message.id,
        finishes_at=finishes if panel else _expiry(message, row),
        thread_id=thread_id,
    )
    if not panel:
        await set_answer_ids(bot.db, row["id"], _answer_ids(message, len(labels)))
    await set_status(bot.db, row["id"], OPEN)
    await log_action(
        bot,
        guild,
        "poll.opened",
        target=row["creator_id"],
        details={"poll_id": row["id"], "channel_id": channel.id, "message_id": message.id},
    )
    return (message, None)


def _expiry(message: Any, row: Any) -> datetime:
    """Discord's own expiry when the message carries one; our arithmetic when it does not."""
    poll = getattr(message, "poll", None)
    found = getattr(poll, "expires_at", None)
    if isinstance(found, datetime):
        return found
    return closes_at(int(row["hours"]))


def _answer_ids(message: Any, wanted: int) -> list[int]:
    poll = getattr(message, "poll", None)
    found = [int(item.id) for item in getattr(poll, "answers", ())]
    return found if len(found) == wanted else list(range(1, wanted + 1))


async def _open_thread(bot: Any, guild: Any, row: Any, message: Any) -> int | None:
    """The per-poll flag decides; the setting is only what filled that flag in at creation."""
    if not row["auto_thread"]:
        return None
    make = getattr(message, "create_thread", None)
    if make is None:
        return None
    try:
        thread = await make(name=thread_name(row["question"]))
    except Exception as exc:
        log.warning("polls: could not open a thread under poll %s: %s", row["id"], exc)
        await log_action(
            bot,
            guild,
            "poll.thread_failed",
            details={"poll_id": row["id"], "reason": f"{type(exc).__name__}: {exc}"},
        )
        return None
    guard = getattr(bot, "guard", None)
    if guard is not None:
        guard.own_channel(thread)
    return int(thread.id)


async def apply_decision(
    bot: Any, guild: Any, poll_id: int, status: str, actor: Any, reason: str | None = None
) -> tuple[str, Any]:
    """Approve or deny once, whoever gets the lock first: (what to say, the settled row)."""
    async with poll_lock(bot, poll_id):
        row = await get_poll(bot.db, poll_id)
        if row is None:
            return (NO_SUCH_POLL, None)
        wanted = OPEN if status == OPEN else DENIED
        if not can_transition(row["status"], wanted):
            return (ALREADY_DECIDED.format(poll_id=poll_id, status=row["status"]), None)
        await set_status(
            bot.db,
            poll_id,
            wanted,
            decided_by=getattr(actor, "id", actor),
            deny_reason=reason,
            closed=wanted == DENIED,
        )
        if wanted in TERMINAL_STATUSES:
            drop_lock(bot, poll_id)
        await log_action(
            bot,
            guild,
            "poll.approved" if wanted == OPEN else "poll.denied",
            actor=actor,
            target=row["creator_id"],
            reason=reason,
            details={"poll_id": poll_id, "question": row["question"]},
        )
    fresh = await get_poll(bot.db, poll_id)
    creator = guild.get_member(fresh["creator_id"])
    if wanted == DENIED:
        await dm(
            creator,
            DM_DENIED.format(
                question=fresh["question"], guild=guild.name, reason=reason or "none given"
            ),
            card_for(fresh, await options_of(bot.db, poll_id)),
        )
        return (DENIED_SAID, fresh)
    message, why_not = await post_poll(bot, guild, fresh)
    if message is None:
        await set_status(bot.db, poll_id, CANCELLED, closed=True)
    fresh = await get_poll(bot.db, poll_id)
    said = DM_APPROVED if message is not None else DM_APPROVED_NOT_POSTED
    await dm(creator, said.format(question=fresh["question"], guild=guild.name))
    if message is None:
        return (APPROVED_NOT_POSTED.format(reason=why_not), fresh)
    return (APPROVED_POSTED.format(where=getattr(message, "jump_url", "the channel")), fresh)


def card_for(row: Any, options: Any) -> discord.Embed:
    return review_card(
        poll_id=row["id"],
        question=row["question"],
        creator_id=row["creator_id"],
        kind=row["kind"],
        labels=[str(item["label"]) for item in options],
        hours=row["hours"],
        status=row["status"],
        deny_reason=row["deny_reason"],
    )


async def decision_context(interaction: discord.Interaction, poll_id: int) -> Any:
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
    row = await get_poll(bot.db, poll_id)
    if row is None:
        await interaction.response.send_message(NO_SUCH_POLL, ephemeral=True)
        return None
    return row


async def decide(
    interaction: discord.Interaction, poll_id: int, status: str, reason: str | None = None
) -> None:
    said, fresh = await apply_decision(
        interaction.client, interaction.guild, poll_id, status, interaction.user, reason
    )
    if fresh is not None:
        await _close_card(interaction, fresh, await options_of(interaction.client.db, poll_id))
    await answer(interaction, said)


async def _close_card(interaction: discord.Interaction, row: Any, options: Any) -> None:
    message = getattr(interaction, "message", None)
    if message is None:
        return
    try:
        await message.edit(
            embed=card_for(row, options),
            view=None,
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except Exception as exc:
        log.warning("polls: could not close the card for poll %s: %s", row["id"], exc)


class PollDenyModal(AnswersErrors, discord.ui.Modal, title="Why not?"):
    reason = discord.ui.TextInput(
        label="One line the person who asked will be sent",
        style=discord.TextStyle.paragraph,
        max_length=400,
    )

    def __init__(self, poll_id: int) -> None:
        super().__init__()
        self.poll_id = poll_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await decide(interaction, self.poll_id, DENIED, clamp(self.reason, 400))


class PollDecisionButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=DECISION_TEMPLATE
):
    def __init__(self, poll_id: int, action: str) -> None:
        self.poll_id = poll_id
        self.action = action
        approving = action == "approve"
        super().__init__(
            discord.ui.Button(
                label="Approve" if approving else "Deny",
                style=discord.ButtonStyle.success if approving else discord.ButtonStyle.danger,
                custom_id=decision_id(poll_id, action),
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["poll_id"]), match["action"])

    async def on_click(self, interaction: discord.Interaction) -> None:
        row = await decision_context(interaction, self.poll_id)
        if row is None:
            return
        wanted = OPEN if self.action == "approve" else DENIED
        if not can_transition(row["status"], wanted):
            await interaction.response.send_message(
                ALREADY_DECIDED.format(poll_id=self.poll_id, status=row["status"]), ephemeral=True
            )
            return
        if self.action == "deny":
            await interaction.response.send_modal(PollDenyModal(self.poll_id))
            return
        await interaction.response.defer(ephemeral=True)
        await decide(interaction, self.poll_id, OPEN)


class Polls(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.last_ok_at: dict[str, str | None] = {name: None for name in LOOP_NAMES}
        self.last_error: dict[str, str | None] = {name: None for name in LOOP_NAMES}

    poll = app_commands.Group(name="poll", description="Put something to the room")
    recur = app_commands.Group(
        name="recur", description="Polls that run again on their own", parent=poll
    )

    async def cog_load(self) -> None:
        self.bot.add_dynamic_items(
            PollDecisionButton, PollVoteButton, PollOpenVoteButton, PollClearVoteButton
        )
        if not self.bot.db.is_connected:
            return
        self._polls_loop.start()

    async def cog_unload(self) -> None:
        self._polls_loop.cancel()

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        key = name.removeprefix("_").removesuffix("_loop")
        if key not in LOOP_NAMES:
            return (None, None)
        return (self.last_ok_at[key], self.last_error[key])

    def loop_failed(self, name: str, exc: BaseException, loop: Any) -> None:
        self.last_error[name] = f"{now_iso()} · {type(exc).__name__}: {exc}"
        log.exception("polls: the %s loop raised and is being restarted", name, exc_info=exc)
        loop.restart()

    @tasks.loop(minutes=POLL_MINUTES)
    async def _polls_loop(self) -> None:
        if self.bot.db.is_connected:
            await self.run_due_polls()
        self.last_ok_at["polls"] = now_iso()

    @_polls_loop.before_loop
    async def _before_polls(self) -> None:
        await self.bot.wait_until_ready()

    @_polls_loop.error
    async def _polls_broke(self, exc: BaseException) -> None:
        self.loop_failed("polls", exc, self._polls_loop)

    async def run_due_polls(self) -> None:
        """Occurrences, last calls, closes, then the archive sweep — that order, every pass."""
        now = datetime.now(UTC)
        seen = {guild.id: guild for guild in getattr(self.bot, "guilds", ())}
        for row in await due_polls(self.bot.db, RECURRING, "recur_next_at", now.isoformat()):
            guild = seen.get(row["guild_id"])
            if guild is not None:
                await self._recur(guild, row, now)
        for row in await reminders_due(self.bot.db, self._reminder_horizon(now, seen)):
            guild = seen.get(row["guild_id"])
            if guild is not None:
                await self._remind(guild, row, now)
        for row in await due_polls(self.bot.db, OPEN, "closes_at", now.isoformat()):
            guild = seen.get(row["guild_id"])
            if guild is not None:
                await close_poll(self.bot, guild, row, reason="expired")
        for guild in seen.values():
            await self._archive(guild, now)

    async def _recur(self, guild: Any, row: Any, now: datetime) -> None:
        """One occurrence, claimed before it is opened so a restart cannot post it twice."""
        following = next_occurrence(row["recurrence"], row["recur_at"], row["recur_tz"], now)
        if following is None:
            await set_recur_next(self.bot.db, row["id"], None)
            await log_action(
                self.bot,
                guild,
                "poll.recur_failed",
                details={"recurrence_id": row["id"], "reason": "unreadable_cadence"},
            )
            return
        if not await claim_occurrence(
            self.bot.db, row["id"], row["recur_next_at"], following.isoformat()
        ):
            return
        options = await options_of(self.bot.db, row["id"])
        made, _ = await store_poll(
            self.bot,
            guild,
            row["creator_id"],
            {
                "question": row["question"],
                "kind": row["kind"],
                "labels": [str(item["label"]) for item in options],
                "values": [item["value"] for item in options],
                "hours": int(row["hours"]),
                "surface": row["surface"],
                "multi": bool(row["multi"]),
                "anonymous": bool(row["anonymous"]),
                "results": row["results"],
            },
            channel_id=row["channel_id"],
            ping_role_id=row["ping_role_id"],
            auto_thread=bool(row["auto_thread"]),
            status=OPEN,
        )
        await set_schedule(self.bot.db, made["id"], row["id"])
        message, why_not = await post_poll(self.bot, guild, await get_poll(self.bot.db, made["id"]))
        if message is None:
            await set_status(self.bot.db, made["id"], CANCELLED, closed=True)
        await log_action(
            self.bot,
            guild,
            "poll.recurred",
            target=row["creator_id"],
            details={
                "recurrence_id": row["id"],
                "poll_id": made["id"],
                "posted": message is not None,
                "reason": why_not,
                "next_at": following.isoformat(),
            },
        )

    def _reminder_horizon(self, now: datetime, guilds: Any) -> str:
        """One window wide enough for every guild; each row is re-checked against its own."""
        wanted = (
            int(self.bot.store.get(guild_id, "poll_reminder_minutes") or 0)
            for guild_id in guilds
        )
        widest = max(wanted, default=0)
        return (now + timedelta(minutes=widest)).isoformat()

    async def _remind(self, guild: Any, row: Any, now: datetime) -> None:
        minutes = int(self.bot.store.get(guild.id, "poll_reminder_minutes") or 0)
        finishes = parse_ts(row["closes_at"])
        if not minutes or finishes is None:
            return
        if finishes - now > timedelta(minutes=minutes):
            return
        channel = self.bot.get_channel(row["channel_id"]) if row["channel_id"] else None
        if channel is None or not guard_allows(self.bot, channel):
            await log_action(
                self.bot,
                guild,
                "poll.would_remind",
                details={"poll_id": row["id"], "channel_id": row["channel_id"]},
            )
            return
        if not await claim_reminder(self.bot.db, row["id"]):
            return
        when = f"<t:{int(finishes.timestamp())}:R>"
        try:
            await channel.send(
                reminder_text(row["question"], when),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except Exception as exc:
            log.warning("polls: could not post the last call for %s: %s", row["id"], exc)
            await clear_reminder(self.bot.db, row["id"])
            await log_action(
                self.bot,
                guild,
                "poll.remind_failed",
                details={"poll_id": row["id"], "reason": f"{type(exc).__name__}: {exc}"},
            )
            return
        await log_action(
            self.bot, guild, "poll.reminded", details={"poll_id": row["id"]}
        )

    async def _archive(self, guild: Any, now: datetime) -> None:
        days = int(self.bot.store.get(guild.id, "poll_archive_days") or 0)
        if days <= 0:
            return
        drop = bool(self.bot.store.get(guild.id, "poll_archive_drop_votes"))
        before = (now - timedelta(days=days)).isoformat()
        moved: list[int] = []
        dropped = 0
        for row in await archivable(self.bot.db, guild.id, before):
            dropped += await archive_poll(self.bot.db, row["id"], drop_votes=drop)
            moved.append(int(row["id"]))
        if not moved:
            return
        await log_action(
            self.bot,
            guild,
            "poll.archived",
            details={"polls": moved, "kept_days": days, "votes_dropped": dropped},
        )

    @commands.Cog.listener()
    async def on_raw_poll_vote_add(self, payload: discord.RawPollVoteActionEvent) -> None:
        await self._vote(payload, added=True)

    @commands.Cog.listener()
    async def on_raw_poll_vote_remove(self, payload: discord.RawPollVoteActionEvent) -> None:
        await self._vote(payload, added=False)

    async def _vote(self, payload: Any, *, added: bool) -> None:
        """The raw events are the only ones that always fire; the non-raw pair needs the cache."""
        if not self.bot.db.is_connected:
            return
        row = await poll_for_message(self.bot.db, int(payload.message_id))
        if row is None or row["anonymous"] or row["surface"] != NATIVE:
            return
        option = await option_for_answer(self.bot.db, row["id"], int(payload.answer_id))
        if option is None:
            return
        if added:
            await record_vote(self.bot.db, row["id"], option["id"], int(payload.user_id))
            return
        await forget_vote(self.bot.db, row["id"], option["id"], int(payload.user_id))

    async def _database_ready(self, interaction: discord.Interaction) -> bool:
        if self.bot.db.is_connected:
            return True
        log.warning("polls: refused a command — the database is not connected")
        await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
        return False

    async def _ready(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message(GUILD_ONLY, ephemeral=True)
            return False
        return await self._database_ready(interaction)

    def _may_create(self, interaction: discord.Interaction) -> bool:
        if self.bot.store.get(interaction.guild.id, "poll_who_can_create") == "everyone":
            return True
        return self.bot.store.is_staff(interaction.user)

    @poll.command(name="create", description="Start a poll in this channel")
    @app_commands.describe(
        question="What you are asking",
        kind="single, checkbox (pick several), yesno, rating (1-5) or date",
        options="The answers, separated by `|` — ignored for yes/no, rating and date",
        hours="How long it stays open, in whole hours",
        anonymous="Nobody is told who voted; Black Bloc posts its own panel instead",
        results="live, or close to keep the bars hidden until it ends",
        ping_role="Role mentioned when it opens",
        thread="Open a discussion thread under it",
        start="date polls: the first slot, `2026-09-05` or `2026-09-05 19:00`",
        slots="date polls: how many slots to lay out",
        step="date polls: the gap between two slots",
        step_unit="date polls: whether the gap counts in hours or days",
    )
    @app_commands.choices(
        kind=[app_commands.Choice(name=name, value=name) for name in KINDS],
        results=[app_commands.Choice(name=name, value=name) for name in RESULTS_CHOICES],
        step_unit=[app_commands.Choice(name=name, value=name) for name in DATE_STEPS],
    )
    async def poll_create(
        self,
        interaction: discord.Interaction,
        question: str,
        kind: app_commands.Choice[str] | None = None,
        options: str | None = None,
        hours: app_commands.Range[int, MIN_HOURS, MAX_HOURS] | None = None,
        anonymous: bool = False,
        results: app_commands.Choice[str] | None = None,
        ping_role: discord.Role | None = None,
        thread: bool | None = None,
        start: str | None = None,
        slots: app_commands.Range[int, MIN_SLOTS, MAX_SLOTS] | None = None,
        step: app_commands.Range[int, 1, MAX_STEP] | None = None,
        step_unit: app_commands.Choice[str] | None = None,
    ) -> None:
        if not await self._ready(interaction):
            return
        guild = interaction.guild
        if self.bot.store.get(guild.id, "poll_mode") == "off":
            await answer(interaction, POLLS_OFF)
            return
        if not self._may_create(interaction):
            await answer(interaction, NOT_A_CREATOR)
            return
        plan, refusal = poll_plan(
            self.bot.store,
            guild.id,
            question=question,
            kind=kind.value if kind is not None else SINGLE,
            options=options,
            hours=int(hours) if hours is not None else None,
            anonymous=anonymous,
            results=results.value if results is not None else LIVE,
            start=start,
            slots=int(slots) if slots is not None else None,
            step=int(step) if step is not None else None,
            step_unit=step_unit.value if step_unit is not None else STEP_DAYS,
        )
        if plan is None:
            await answer(interaction, refusal)
            return
        channel = interaction.channel
        if channel is None:
            await answer(interaction, NO_CHANNEL)
            return
        if not guard_allows(self.bot, channel):
            await answer(interaction, guard_refusal(self.bot))
            return
        await interaction.response.defer(ephemeral=True)
        role_id = (
            ping_role.id
            if ping_role is not None
            else self.bot.store.get(guild.id, "poll_ping_role_id")
        )
        wants_thread = (
            bool(thread)
            if thread is not None
            else bool(self.bot.store.get(guild.id, "poll_auto_thread"))
        )
        row, reviewing = await store_poll(
            self.bot,
            guild,
            interaction.user.id,
            plan,
            channel_id=channel.id,
            ping_role_id=role_id,
            auto_thread=wants_thread,
        )
        if reviewing:
            await self._send_for_review(interaction, guild, row, plan["note"])
            return
        await self._post_now(interaction, guild, row, plan["note"])

    async def _post_now(
        self, interaction: discord.Interaction, guild: Any, row: Any, note: str | None = None
    ) -> None:
        message, why_not = await post_poll(self.bot, guild, row)
        if message is None:
            await set_status(self.bot.db, row["id"], CANCELLED, closed=True)
            await answer(
                interaction,
                guard_refusal(self.bot) if why_not == "test_mode" else CANNOT_POST,
            )
            return
        fresh = await get_poll(self.bot.db, row["id"])
        url = getattr(message, "jump_url", None)
        said = POSTED.format(url=url) if url else POSTED_NO_LINK
        if fresh["auto_thread"] and not fresh["thread_id"]:
            said += THREAD_FAILED
        if note:
            said += f"\n\n{note}"
        await answer(interaction, said)

    async def _send_for_review(
        self, interaction: discord.Interaction, guild: Any, row: Any, note: str | None = None
    ) -> None:
        target = card_channel(self.bot, guild)
        if target is None:
            await set_status(self.bot.db, row["id"], CANCELLED, closed=True)
            await answer(interaction, NO_REVIEW_CHANNEL)
            return
        options = await options_of(self.bot.db, row["id"])
        try:
            message = await target.send(
                embed=card_for(row, options),
                view=review_view(row["id"]),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except Exception as exc:
            log.warning("polls: could not post the review card for %s: %s", row["id"], exc)
            await log_action(
                self.bot,
                guild,
                "poll.card_failed",
                details={"poll_id": row["id"], "reason": f"{type(exc).__name__}: {exc}"},
            )
            await answer(
                interaction,
                SENT_FOR_REVIEW.format(
                    question=clamp(row["question"], 80),
                    where=REVIEW_NO_CARD.format(channel=f"<#{target.id}>"),
                ),
            )
            return
        await set_review(self.bot.db, row["id"], target.id, message.id)
        said = SENT_FOR_REVIEW.format(
            question=clamp(row["question"], 80),
            where=REVIEW_HERE.format(channel=f"<#{target.id}>"),
        )
        await answer(interaction, f"{said}\n\n{note}" if note else said)
        await dm(interaction.user, f"Sent for review on **{guild.name}**.", card_for(row, options))

    async def _wanted(self, interaction: discord.Interaction, poll_id: str) -> Any:
        digits = str(poll_id or "").strip().lstrip("#")
        if not digits.isdigit():
            await answer(interaction, NOT_AN_ID.format(given=clamp(poll_id, 40)))
            return None
        row = await get_poll(self.bot.db, int(digits))
        if row is None or row["guild_id"] != interaction.guild.id:
            await answer(interaction, NO_SUCH_POLL)
            return None
        return row

    @poll.command(name="end", description="Close a poll early and post the result")
    @app_commands.describe(poll_id="The number `/poll list` shows")
    async def poll_end(self, interaction: discord.Interaction, poll_id: str) -> None:
        if not await self._ready(interaction):
            return
        row = await self._wanted(interaction, poll_id)
        if row is None:
            return
        if row["creator_id"] != interaction.user.id and not self.bot.store.is_staff(
            interaction.user
        ):
            await answer(interaction, NOT_YOURS.format(poll_id=row["id"]))
            return
        if row["status"] != OPEN:
            await answer(interaction, NOT_OPEN.format(poll_id=row["id"], status=row["status"]))
            return
        if not guard_allows(self.bot, row["channel_id"]):
            await answer(interaction, guard_refusal(self.bot))
            return
        await interaction.response.defer(ephemeral=True)
        closed, written = await close_poll(
            self.bot, interaction.guild, row, reason="ended_early", actor=interaction.user
        )
        if not closed:
            fresh = await get_poll(self.bot.db, row["id"])
            await answer(
                interaction, NOT_OPEN.format(poll_id=row["id"], status=fresh["status"])
            )
            return
        await answer(
            interaction,
            (ENDED if written else ENDED_NO_RESULT).format(poll_id=row["id"]),
        )

    @poll.command(name="cancel", description="Stop a poll without publishing a result")
    @app_commands.describe(poll_id="The number `/poll list` shows")
    async def poll_cancel(self, interaction: discord.Interaction, poll_id: str) -> None:
        if not await require_staff(interaction):
            return
        if not await self._database_ready(interaction):
            return
        row = await self._wanted(interaction, poll_id)
        if row is None:
            return
        if row["status"] not in OPEN_STATUSES:
            await answer(interaction, NOT_OPEN.format(poll_id=row["id"], status=row["status"]))
            return
        if row["message_id"] and not guard_allows(self.bot, row["channel_id"]):
            await answer(interaction, guard_refusal(self.bot))
            return
        await interaction.response.defer(ephemeral=True)
        if not await cancel_poll(self.bot, interaction.guild, row, by=interaction.user):
            fresh = await get_poll(self.bot.db, row["id"])
            await answer(
                interaction, NOT_OPEN.format(poll_id=row["id"], status=fresh["status"])
            )
            return
        await answer(interaction, CANCELLED_SAID.format(poll_id=row["id"]))

    @poll.command(name="results", description="Show how a poll is going, or how it went")
    @app_commands.describe(poll_id="The number `/poll list` shows")
    async def poll_results(self, interaction: discord.Interaction, poll_id: str) -> None:
        if not await self._ready(interaction):
            return
        row = await self._wanted(interaction, poll_id)
        if row is None:
            return
        await interaction.response.defer(ephemeral=True)
        counts, total, approximate = await self.counts_for(row)
        await interaction.followup.send(
            embed=results_embed(
                poll_id=row["id"],
                question=row["question"],
                counts=counts,
                total=total,
                status=row["status"],
                kind=row["kind"],
                closed_at=row["closed_at"],
                approximate=approximate,
            ),
            ephemeral=True,
        )

    async def counts_for(self, row: Any) -> tuple[list[dict[str, Any]], int, bool]:
        """Discord's live numbers while a poll is open; the stored ones once it has closed."""
        if row["surface"] == PANEL and row["status"] == OPEN:
            return (*await panel_counts(self.bot.db, row["id"]), False)
        options = await options_of(self.bot.db, row["id"])
        if row["status"] == OPEN and guard_allows(self.bot, row["channel_id"]):
            message = await fetch_poll_message(self.bot, row)
            if message is not None:
                counts, total = counts_from_message(message, options)
                return (counts, total, True)
        counts = counts_from_options(options)
        return (counts, sum(item["votes"] for item in counts), False)

    @poll.command(name="list", description="Show the polls that are running")
    async def poll_list(self, interaction: discord.Interaction) -> None:
        if not await self._ready(interaction):
            return
        rows = await polls_by_status(self.bot.db, interaction.guild.id, OPEN_STATUSES)
        lines: list[str] = []
        if not rows:
            lines.append(NO_OPEN_POLLS)
        for row in rows[:LIST_LIMIT]:
            finishes = parse_ts(row["closes_at"])
            when = f"closes <t:{int(finishes.timestamp())}:R>" if finishes else "not posted yet"
            where = f" · <#{row['channel_id']}>" if row["channel_id"] else ""
            lines.append(
                f"**#{row['id']}** {clamp(row['question'], 60)} — {row['status']} · {when}"
                f" · {describe_hours(row['hours'])}{where}"
            )
        await interaction.response.send_message(
            "\n".join(lines), ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @recur.command(name="create", description="Set a poll to run again on its own")
    @app_commands.describe(
        question="What it asks, every time",
        every="daily, weekly or monthly",
        at="Time of day on the 24-hour clock, like 19:00",
        day="weekly: mon-sun · monthly: the day of the month, 1-28",
        tz="The zone that time of day is in",
        kind="single, checkbox (pick several), yesno or rating (1-5)",
        options="The answers, separated by `|`",
        hours="How long each one stays open",
        anonymous="Nobody is told who voted",
        results="live, or close to keep the bars hidden until it ends",
        channel="Where each one is posted",
        ping_role="Role mentioned when each one opens",
        thread="Open a discussion thread under each one",
    )
    @app_commands.choices(
        every=[app_commands.Choice(name=name, value=name) for name in CADENCES],
        kind=[app_commands.Choice(name=name, value=name) for name in KINDS],
        results=[app_commands.Choice(name=name, value=name) for name in RESULTS_CHOICES],
    )
    async def recur_create(
        self,
        interaction: discord.Interaction,
        question: str,
        every: app_commands.Choice[str],
        at: str,
        day: str | None = None,
        tz: str | None = None,
        kind: app_commands.Choice[str] | None = None,
        options: str | None = None,
        hours: app_commands.Range[int, MIN_HOURS, MAX_HOURS] | None = None,
        anonymous: bool = False,
        results: app_commands.Choice[str] | None = None,
        channel: discord.TextChannel | None = None,
        ping_role: discord.Role | None = None,
        thread: bool | None = None,
    ) -> None:
        if not await require_staff(interaction):
            return
        if not await self._ready(interaction):
            return
        guild = interaction.guild
        if self.bot.store.get(guild.id, "poll_mode") == "off":
            await answer(interaction, POLLS_OFF)
            return
        wanted = kind.value if kind is not None else SINGLE
        if wanted == DATE:
            await answer(interaction, RECUR_NOT_A_DATE)
            return
        zone_name = str(tz or DEFAULT_TZ)
        trouble = cadence_trouble(every.value, day, at, zone_name)
        if trouble is not None:
            await answer(interaction, trouble)
            return
        plan, refusal = poll_plan(
            self.bot.store,
            guild.id,
            question=question,
            kind=wanted,
            options=options,
            hours=int(hours) if hours is not None else None,
            anonymous=anonymous,
            results=results.value if results is not None else LIVE,
        )
        if plan is None:
            await answer(interaction, refusal)
            return
        target = channel if channel is not None else interaction.channel
        if target is None:
            await answer(interaction, NO_CHANNEL)
            return
        if not guard_allows(self.bot, target):
            await answer(interaction, guard_refusal(self.bot))
            return
        token = cadence_token(every.value, day)
        following = next_occurrence(token, at, zone_name)
        row, _ = await store_poll(
            self.bot,
            guild,
            interaction.user.id,
            plan,
            channel_id=target.id,
            ping_role_id=(
                ping_role.id
                if ping_role is not None
                else self.bot.store.get(guild.id, "poll_ping_role_id")
            ),
            auto_thread=(
                bool(thread)
                if thread is not None
                else bool(self.bot.store.get(guild.id, "poll_auto_thread"))
            ),
            status=RECURRING,
        )
        await set_recurrence(self.bot.db, row["id"], token, at, zone_name, following.isoformat())
        await log_action(
            self.bot,
            guild,
            "poll.recur_created",
            actor=interaction.user,
            details={
                "recurrence_id": row["id"],
                "cadence": token,
                "at": at,
                "tz": zone_name,
                "next_at": following.isoformat(),
            },
        )
        said = RECUR_SAVED.format(
            question=clamp(question, 80),
            cadence=describe_cadence(token, at, zone_name),
            when=int(following.timestamp()),
        )
        await answer(interaction, f"{said}\n\n{plan['note']}" if plan["note"] else said)

    @recur.command(name="list", description="Show the polls that run again on their own")
    async def recur_list(self, interaction: discord.Interaction) -> None:
        if not await self._ready(interaction):
            return
        rows = await recurrences(self.bot.db, interaction.guild.id)
        lines: list[str] = [RECUR_NONE] if not rows else []
        for row in rows[:LIST_LIMIT]:
            following = parse_ts(row["recur_next_at"])
            when = f"next <t:{int(following.timestamp())}:R>" if following else "**paused**"
            lines.append(
                f"**#{row['id']}** {clamp(row['question'], 60)} — "
                f"{describe_cadence(row['recurrence'], row['recur_at'], row['recur_tz'])} · "
                f"{when} · <#{row['channel_id']}>"
            )
        await interaction.response.send_message(
            "\n".join(lines), ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @recur.command(name="pause", description="Stop or start a repeating poll")
    @app_commands.describe(
        poll_id="The number `/poll recur list` shows",
        paused="true stops it opening any more; false starts it again",
    )
    async def recur_pause(
        self, interaction: discord.Interaction, poll_id: str, paused: bool = True
    ) -> None:
        row = await self._wanted_recurrence(interaction, poll_id)
        if row is None:
            return
        if paused:
            await set_recur_next(self.bot.db, row["id"], None)
            await log_action(
                self.bot,
                interaction.guild,
                "poll.recur_paused",
                actor=interaction.user,
                details={"recurrence_id": row["id"]},
            )
            await answer(interaction, RECUR_PAUSED.format(question=clamp(row["question"], 80)))
            return
        following = next_occurrence(row["recurrence"], row["recur_at"], row["recur_tz"])
        if following is None:
            await answer(interaction, NOT_A_RECURRENCE.format(poll_id=row["id"]))
            return
        await set_recur_next(self.bot.db, row["id"], following.isoformat())
        await log_action(
            self.bot,
            interaction.guild,
            "poll.recur_resumed",
            actor=interaction.user,
            details={"recurrence_id": row["id"], "next_at": following.isoformat()},
        )
        await answer(
            interaction,
            RECUR_RESUMED.format(
                question=clamp(row["question"], 80), when=int(following.timestamp())
            ),
        )

    @recur.command(name="delete", description="Stop a poll repeating for good")
    @app_commands.describe(poll_id="The number `/poll recur list` shows")
    async def recur_delete(self, interaction: discord.Interaction, poll_id: str) -> None:
        row = await self._wanted_recurrence(interaction, poll_id)
        if row is None:
            return
        await set_recur_next(self.bot.db, row["id"], None)
        await set_status(self.bot.db, row["id"], CANCELLED, closed=True)
        await log_action(
            self.bot,
            interaction.guild,
            "poll.recur_deleted",
            actor=interaction.user,
            details={"recurrence_id": row["id"], "question": row["question"]},
        )
        await answer(interaction, RECUR_DELETED.format(question=clamp(row["question"], 80)))

    async def _wanted_recurrence(self, interaction: discord.Interaction, poll_id: str) -> Any:
        if not await require_staff(interaction):
            return None
        if not await self._ready(interaction):
            return None
        digits = str(poll_id or "").strip().lstrip("#")
        if not digits.isdigit():
            await answer(interaction, NOT_AN_ID.format(given=clamp(poll_id, 40)))
            return None
        row = await get_recurrence(self.bot.db, interaction.guild.id, int(digits))
        if row is None:
            await answer(interaction, NOT_A_RECURRENCE.format(poll_id=clamp(digits, 20)))
            return None
        return row

    @poll.command(name="settings", description="Show or change how polls are set up")
    @app_commands.describe(
        mode="off, or on",
        who_can_create="staff, or everyone",
        review="on holds every poll for a staff Approve or Deny first",
        default_hours="How long a poll stays open when nobody says otherwise",
        channel="Where a poll made from the dashboard goes",
        ping_role="Role mentioned when a poll opens",
        reminder_minutes="Minutes before close that Black Bloc posts a last call, 0 for none",
        auto_thread="Open a discussion thread under every poll",
        archive_days="Days a closed poll stays on the list",
        archive_drop_votes="Forget who voted when a poll is archived",
        date_labels="How a date poll writes its slots: plain, or a timestamp each reader's clock",
        clear_ping_role="Stop mentioning any role",
        clear_channel="Forget the dashboard's default channel",
    )
    @app_commands.choices(
        mode=[app_commands.Choice(name=name, value=name) for name in POLL_MODES],
        review=[app_commands.Choice(name=name, value=name) for name in POLL_REVIEW_MODES],
        who_can_create=[app_commands.Choice(name=name, value=name) for name in POLL_CREATORS],
        date_labels=[
            app_commands.Choice(name=name, value=name) for name in POLL_DATE_LABEL_FORMS
        ],
    )
    async def poll_settings(
        self,
        interaction: discord.Interaction,
        mode: app_commands.Choice[str] | None = None,
        who_can_create: app_commands.Choice[str] | None = None,
        review: app_commands.Choice[str] | None = None,
        default_hours: app_commands.Range[int, MIN_HOURS, MAX_HOURS] | None = None,
        channel: discord.TextChannel | None = None,
        ping_role: discord.Role | None = None,
        reminder_minutes: app_commands.Range[int, 0, POLL_REMINDER_MAX_MINUTES] | None = None,
        auto_thread: bool | None = None,
        archive_days: (
            app_commands.Range[int, POLL_ARCHIVE_MIN_DAYS, POLL_ARCHIVE_MAX_DAYS] | None
        ) = None,
        archive_drop_votes: bool | None = None,
        date_labels: app_commands.Choice[str] | None = None,
        clear_ping_role: bool = False,
        clear_channel: bool = False,
    ) -> None:
        if not await require_staff(interaction):
            return
        if not await self._database_ready(interaction):
            return
        guild = interaction.guild
        store = self.bot.store
        changed: dict[str, Any] = {}
        for key, value in (
            ("poll_mode", mode.value if mode is not None else None),
            (
                "poll_who_can_create",
                who_can_create.value if who_can_create is not None else None,
            ),
            ("poll_review_mode", review.value if review is not None else None),
            ("poll_default_hours", default_hours),
            ("poll_channel_id", channel),
            ("poll_ping_role_id", ping_role),
            ("poll_reminder_minutes", reminder_minutes),
            ("poll_auto_thread", auto_thread),
            ("poll_archive_days", archive_days),
            ("poll_archive_drop_votes", archive_drop_votes),
            ("poll_date_labels", date_labels.value if date_labels is not None else None),
        ):
            if value is not None:
                changed[key] = await store.set(guild.id, key, value, by=interaction.user.id)
        for wanted, key in (
            (clear_ping_role, "poll_ping_role_id"),
            (clear_channel, "poll_channel_id"),
        ):
            if wanted:
                await store.clear(guild.id, key)
                changed[key] = None
        await interaction.response.send_message(
            "\n".join(self._settings_lines(guild)),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        if changed:
            await log_action(
                self.bot, guild, "poll.settings", actor=interaction.user, details=changed
            )

    def _settings_lines(self, guild: Any) -> list[str]:
        store = self.bot.store
        channel_id = store.get(guild.id, "poll_channel_id")
        role_id = store.get(guild.id, "poll_ping_role_id")
        minutes = int(store.get(guild.id, "poll_reminder_minutes") or 0)
        staff = store.staff_roles(guild)
        lines = [
            f"**mode** — {store.get(guild.id, 'poll_mode')}",
            f"**who can create** — {store.get(guild.id, 'poll_who_can_create')}",
            f"**staff review** — {store.get(guild.id, 'poll_review_mode')}",
            f"**default length** — {describe_hours(store.get(guild.id, 'poll_default_hours'))}",
            "**dashboard channel** — " + (f"<#{channel_id}>" if channel_id else "not set"),
            "**ping role** — " + (f"<@&{role_id}>" if role_id else "nobody"),
            "**last call** — " + (f"{minutes} minute(s) before close" if minutes else "off"),
            f"**discussion threads** — {store.get(guild.id, 'poll_auto_thread')}",
            f"**archived after** — {store.get(guild.id, 'poll_archive_days')} day(s), "
            f"votes dropped: {store.get(guild.id, 'poll_archive_drop_votes')}",
            f"**date slot labels** — {store.get(guild.id, 'poll_date_labels')}",
            f"**staff (who may approve)** — {staff_roles_sentence(staff)}",
            *self._health_lines(),
        ]
        if not staff:
            lines.append(NO_STAFF_WARNING)
        return lines

    def _health_lines(self) -> list[str]:
        """Checklist 9: last success and last error, never `is_running`."""
        lines = []
        for name in LOOP_NAMES:
            ok = self.last_ok_at[name] or "never yet"
            broke = self.last_error[name]
            trouble = f" · last error {broke}" if broke else " · no errors"
            lines.append(f"**{name} loop** — last finished {ok}{trouble}")
        return lines

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        if not self.bot.db.is_connected:
            return
        if channel.id == self.bot.store.get(channel.guild.id, "poll_channel_id"):
            await self.bot.store.clear(channel.guild.id, "poll_channel_id")
            await log_action(
                self.bot,
                channel.guild,
                "poll.channel_forgotten",
                details={"channel_id": channel.id},
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Polls(bot))
