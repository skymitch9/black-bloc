from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ...actionlog import (
    log_action,
    send_logs,
)
from ...command_errors import NETWORK_ERRORS, AnswersErrors, SafeDynamicItem
from ...golive import now_iso, parse_ts
from ...logkinds import VIA_DISCORD, kind_via
from ...panels import (
    KEEP_IT,
    Panel,
    answer,
    capped_placeholder,
    opened,
    option_label,
    panel_minutes,
    picked_values,
    retire,
    still_staff,
)
from ...panels import NoteModal as PanelNoteModal
from ...panels import site_page_url as library_site_page_url
from ...polls import (
    ARCHIVED,
    AT_CLOSE,
    BAD_HOURS,
    BUTTONS_UP_TO,
    CADENCES,
    CANCELLED,
    CLOSED,
    COLOURS,
    CREATOR_MAY_END_KEY,
    DAILY,
    DATE,
    DATE_LABEL_FORMS,
    DATE_PLAIN,
    DATE_STEPS,
    DEFAULT_HOURS,
    DENIED,
    DRAFT,
    FIND_BUTTON,
    KIND_NAMES,
    KNOWN_KINDS,
    LABEL_LIMIT,
    LIVE,
    MAX_HOURS,
    MAX_MONTH_DAY,
    MAX_SLOTS,
    MAX_STEP,
    MIN_HOURS,
    MIN_SLOTS,
    NATIVE,
    NO_MOVES_LEFT,
    NOT_A_RECURRENCE,
    OPEN,
    OPEN_STATUSES,
    PANEL,
    PANEL_CLEAR,
    PANEL_COUNTS,
    PANEL_INTRO,
    PANEL_MINUTES_KEY,
    PANEL_TIMEOUT_FOOTER,
    PANEL_TITLE,
    PANEL_VOTE,
    PENDING_REVIEW,
    PICK_A_POLL,
    PICK_A_RECURRENCE,
    PICK_SOMETHING,
    POLL_SECRET_UNSET,
    QUESTION_LIMIT,
    RECUR_DELETED,
    RECUR_NOT_A_DATE,
    RECUR_PAUSED,
    RECUR_RESUMED,
    RECUR_SAVED,
    RECURRING,
    SINGLE,
    SITE_BUTTON,
    STEP_DAYS,
    TERMINAL_STATUSES,
    VOTE_GONE,
    VOTE_HASHED,
    VOTE_KEY_MISSING,
    VOTE_KEYED,
    VOTE_NOT_OPEN,
    WEEKDAYS,
    NeedsPanel,
    cadence_token,
    cadence_trouble,
    can_transition,
    card_buttons,
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
    poll_id_from,
    recurrence_card,
    reminder_text,
    results_embed,
    review_card,
    summary_line,
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
    "Polls are turned off on this server, so nothing was posted. A Lead turns them back on from "
    "**Settings** on this panel — ask one if you have something to put to the room."
)
NOT_A_CREATOR = (
    "Polls are staff-only on this server right now, so nothing was posted. Ask a Lead to run it "
    "for you, or to open them up to everybody from **Settings** on this panel."
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
    "one with `/settings` ▸ **Roles & channels…**, or turns the review off with "
    "`/poll settings review:off`."
)
NOT_AN_ID = "**{given}** is not a poll number, so nothing was done. This panel lists them."
NO_SUCH_POLL = (
    "Black Bloc has no record of that poll any more, so nothing was done. This panel shows the "
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
NO_OPEN_POLLS = "Nothing is running — **Create** starts one."
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
    "`staff_channel_id` at a channel only staff can see with `/settings` ▸ **Roles & "
    "channels…**."
)

COG_NAME = "Polls"
BUTTON_STYLES: dict[str, discord.ButtonStyle] = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}
CREATE_BUTTON = "Create"
REFRESH_BUTTON = "Refresh"
SETTINGS_BUTTON = "Settings"
LOGS_BUTTON = "Logs"
BACK_BUTTON = "Back"
NUMBERS_BUTTON = "Numbers…"
CLEAR_PING_BUTTON = "Clear ping role"
CLEAR_CHANNEL_BUTTON = "Clear channel"
POST_BUTTON = "Post it"
SLOTS_BUTTON = "Date slots…"
REPEAT_BUTTON = "Repeat…"
START_OVER_BUTTON = "Start over"
GIVE_UP_BUTTON = "Cancel"
DELETE_BUTTON = "Delete"
PAUSE_BUTTON = "Pause"
RESUME_BUTTON = "Resume"
DELETE_YES_BUTTON = "Yes, stop it repeating"
DELETE_KEEP_BUTTON = KEEP_IT
THREAD_ON = "Thread: on"
THREAD_OFF = "Thread: off"
FIND_TITLE = "Find a poll"
FIND_LABEL = "The poll number, like 12"
FIND_LIMIT = 20
CREATE_TITLE = "New poll"
SLOTS_TITLE = "Date slots"
CADENCE_TITLE = "Repeat this poll"
NUMBERS_TITLE = "Poll numbers"
DENY_TITLE = "Why not?"
DENY_LABEL = "One line the person who asked will be sent"
DENY_LIMIT = 400
SETTINGS_TITLE = "Poll settings"
DATE_LABELS_PICK = "Date slot labels…"
SETTINGS_CHANNEL_PICK = "Where dashboard polls go…"
SETTINGS_ROLE_PICK = "Ping role…"
DRAFT_CHANNEL_PICK = "Post it in…"
DRAFT_ROLE_PICK = "Ping…"
DRAFT_INTRO = "Nothing is saved until you press **Post it**."
DRAFT_NEEDS_SLOTS = "A date poll needs its slots before it can go up — press **Date slots…**."
NOT_YOURS_TO_END = (
    "Only staff can close this poll early on this server, so nothing was changed. Ask a Lead."
)
SWITCH_ANONYMOUS = "Nobody is told who voted"
SWITCH_HIDDEN = "Hide the bars until it closes"
KIND_LABEL = "What kind of poll?"
SWITCHES_LABEL = "Anything else?"
CADENCE_LABEL = "How often?"
STEP_UNIT_LABEL = "Counted in"


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
    vote_scheme: str = VOTE_HASHED,
) -> int | None:
    cur = await db.conn.execute(
        "INSERT INTO polls(guild_id, creator_id, question, kind, surface, multi, anonymous, "
        "results, hours, auto_thread, channel_id, ping_role_id, status, vote_scheme, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
            vote_scheme,
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
    via: str = VIA_DISCORD,
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
        vote_scheme=vote_scheme_for(poll_secret(bot)),
    )
    await add_options(bot.db, poll_id, plan["labels"], plan.get("values"))
    await log_action(
        bot,
        guild,
        kind_via("poll.created", via),
        actor=creator_id,
        target=creator_id,
        details={
            "via": via,
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


def vote_scheme_for(secret: Any) -> str:
    return VOTE_KEYED if secret else VOTE_HASHED


def scheme_of(row: Any) -> str:
    """The scheme a poll was created with; a row written before the column is the old one."""
    try:
        stored = row["vote_scheme"]
    except (IndexError, KeyError, TypeError):
        stored = None
    return VOTE_KEYED if str(stored or "") == VOTE_KEYED else VOTE_HASHED


def poll_secret(bot: Any) -> str | None:
    return getattr(getattr(bot, "settings", None), "poll_vote_secret", None)


def can_key(row: Any, secret: Any) -> bool:
    """False only for a keyed poll whose secret has gone — never guess, never downgrade."""
    return not row["anonymous"] or scheme_of(row) != VOTE_KEYED or bool(secret)


def voter_key(row: Any, user_id: Any, secret: Any = None) -> int:
    """An anonymous poll counts one vote per person without keeping who the person is."""
    if not row["anonymous"]:
        return int(user_id)
    preimage = f"{int(row['id'])}:{int(user_id)}".encode()
    if scheme_of(row) == VOTE_KEYED:
        if not secret:
            raise ValueError("this poll's votes are keyed and POLL_VOTE_SECRET is not set")
        digest = hmac.new(str(secret).encode("utf-8"), preimage, hashlib.sha256).digest()
    else:
        digest = hashlib.sha256(preimage).digest()
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
    if not can_key(row, poll_secret(bot)):
        log.warning("polls: poll %s is keyed and POLL_VOTE_SECRET is not set", row["id"])
        await answer(interaction, VOTE_KEY_MISSING)
        return None
    return row


def voter_of(interaction: discord.Interaction, row: Any) -> int:
    return voter_key(row, interaction.user.id, poll_secret(interaction.client))


async def cast_vote(interaction: discord.Interaction, row: Any, positions: Any) -> list[str]:
    bot = interaction.client
    async with poll_lock(bot, row["id"]):
        chosen = await set_panel_vote(
            bot.db, row["id"], voter_of(interaction, row), positions,
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
                interaction.client.db, row["id"], voter_of(interaction, row)
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
            interaction.client.db, row["id"], voter_of(interaction, row)
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
    bot: Any,
    guild: Any,
    row: Any,
    *,
    reason: str,
    actor: Any = None,
    end_it: bool = True,
    via: str = VIA_DISCORD,
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
            kind_via("poll.closed", via),
            actor=actor,
            target=fresh["creator_id"],
            reason=reason,
            details={"poll_id": fresh["id"], "question": fresh["question"], "via": via},
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


async def cancel_poll(
    bot: Any, guild: Any, row: Any, *, by: Any = None, via: str = VIA_DISCORD
) -> bool:
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
            kind_via("poll.cancelled", via),
            actor=by,
            target=fresh["creator_id"],
            details={"poll_id": fresh["id"], "question": fresh["question"], "via": via},
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
    bot: Any,
    guild: Any,
    poll_id: int,
    status: str,
    actor: Any,
    reason: str | None = None,
    *,
    via: str = VIA_DISCORD,
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
            kind_via("poll.approved" if wanted == OPEN else "poll.denied", via),
            actor=actor,
            target=row["creator_id"],
            reason=reason,
            details={"poll_id": poll_id, "question": row["question"], "via": via},
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


async def pause_recurrence(
    bot: Any, guild: Any, row: Any, actor: Any, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    """The panel's Pause button and the dashboard's — the clock stops, the template stays."""
    await set_recur_next(bot.db, row["id"], None)
    await log_action(
        bot,
        guild,
        kind_via("poll.recur_paused", via),
        actor=actor,
        details={"recurrence_id": row["id"], "via": via},
    )
    return (
        RECUR_PAUSED.format(question=clamp(row["question"], 80)),
        await get_poll(bot.db, row["id"]),
    )


async def resume_recurrence(
    bot: Any, guild: Any, row: Any, actor: Any, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    """(what to say, the row) — None for the row when the stored cadence no longer reads."""
    following = next_occurrence(row["recurrence"], row["recur_at"], row["recur_tz"])
    if following is None:
        return (NOT_A_RECURRENCE.format(poll_id=row["id"]), None)
    await set_recur_next(bot.db, row["id"], following.isoformat())
    await log_action(
        bot,
        guild,
        kind_via("poll.recur_resumed", via),
        actor=actor,
        details={
            "recurrence_id": row["id"],
            "next_at": following.isoformat(),
            "via": via,
        },
    )
    return (
        RECUR_RESUMED.format(
            question=clamp(row["question"], 80), when=int(following.timestamp())
        ),
        await get_poll(bot.db, row["id"]),
    )


async def delete_recurrence(
    bot: Any, guild: Any, row: Any, actor: Any, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    """The template stops for good; the polls it already opened are untouched."""
    await set_recur_next(bot.db, row["id"], None)
    await set_status(bot.db, row["id"], CANCELLED, closed=True)
    await log_action(
        bot,
        guild,
        kind_via("poll.recur_deleted", via),
        actor=actor,
        details={"recurrence_id": row["id"], "question": row["question"], "via": via},
    )
    return (
        RECUR_DELETED.format(question=clamp(row["question"], 80)),
        await get_poll(bot.db, row["id"]),
    )


async def save_recurrence(
    bot: Any,
    guild: Any,
    row: Any,
    token: str,
    at_local: str,
    tz_name: str,
    actor: Any,
    *,
    via: str = VIA_DISCORD,
) -> tuple[str, Any]:
    """A stored poll turned into a template: the cadence, the clock and one log line."""
    following = next_occurrence(token, at_local, tz_name)
    if following is None:
        return (NOT_A_RECURRENCE.format(poll_id=row["id"]), None)
    await set_recurrence(bot.db, row["id"], token, at_local, tz_name, following.isoformat())
    await log_action(
        bot,
        guild,
        kind_via("poll.recur_created", via),
        actor=actor,
        details={
            "recurrence_id": row["id"],
            "cadence": token,
            "at": at_local,
            "tz": tz_name,
            "next_at": following.isoformat(),
            "via": via,
        },
    )
    return (
        RECUR_SAVED.format(
            question=clamp(row["question"], 80),
            cadence=describe_cadence(token, at_local, tz_name),
            when=int(following.timestamp()),
        ),
        await get_poll(bot.db, row["id"]),
    )


async def apply_poll_settings(
    bot: Any, guild: Any, actor: Any, changes: Any, clears: Any = ()
) -> dict[str, Any]:
    """Every settings write on this feature: one pass, one `poll.settings` line."""
    changed: dict[str, Any] = {}
    for key, value in dict(changes or {}).items():
        if value is not None:
            changed[key] = await bot.store.set(
                guild.id, key, value, by=getattr(actor, "id", actor)
            )
    for key in clears or ():
        await bot.store.clear(guild.id, key)
        changed[key] = None
    if changed:
        await log_action(bot, guild, "poll.settings", actor=actor, details=changed)
    return changed


async def counts_for(bot: Any, row: Any) -> tuple[list[dict[str, Any]], int, bool]:
    """Discord's live numbers while a poll is open; the stored ones once it has closed."""
    if row["surface"] == PANEL and row["status"] == OPEN:
        return (*await panel_counts(bot.db, row["id"]), False)
    options = await options_of(bot.db, row["id"])
    if row["status"] == OPEN and guard_allows(bot, row["channel_id"]):
        message = await fetch_poll_message(bot, row)
        if message is not None:
            counts, total = counts_from_message(message, options)
            return (counts, total, True)
    counts = counts_from_options(options)
    return (counts, sum(item["votes"] for item in counts), False)


async def post_now(bot: Any, guild: Any, row: Any, note: str | None = None) -> tuple[str, Any]:
    """A stored poll put in its channel: (what to say, the row as it now is)."""
    message, why_not = await post_poll(bot, guild, row)
    if message is None:
        await set_status(bot.db, row["id"], CANCELLED, closed=True)
        said = guard_refusal(bot) if why_not == "test_mode" else CANNOT_POST
        return (said, await get_poll(bot.db, row["id"]))
    fresh = await get_poll(bot.db, row["id"])
    url = getattr(message, "jump_url", None)
    said = POSTED.format(url=url) if url else POSTED_NO_LINK
    if fresh["auto_thread"] and not fresh["thread_id"]:
        said += THREAD_FAILED
    if note:
        said += f"\n\n{note}"
    return (said, fresh)


async def send_for_review(
    bot: Any, guild: Any, row: Any, actor: Any, note: str | None = None
) -> tuple[str, Any]:
    """A stored poll held for a staff decision, and the DM its author is owed."""
    target, message = await send_review_card(bot, guild, row)
    if target is None:
        await set_status(bot.db, row["id"], CANCELLED, closed=True)
        return (NO_REVIEW_CHANNEL, await get_poll(bot.db, row["id"]))
    where = (REVIEW_HERE if message is not None else REVIEW_NO_CARD).format(
        channel=f"<#{target.id}>"
    )
    said = SENT_FOR_REVIEW.format(question=clamp(row["question"], 80), where=where)
    if note:
        said = f"{said}\n\n{note}"
    if message is not None:
        options = await options_of(bot.db, row["id"])
        await dm(actor, f"Sent for review on **{guild.name}**.", card_for(row, options))
    return (said, await get_poll(bot.db, row["id"]))


async def end_poll_now(bot: Any, guild: Any, row: Any, actor: Any) -> tuple[str, Any]:
    closed, written = await close_poll(
        bot, guild, row, reason="ended_early", actor=actor
    )
    fresh = await get_poll(bot.db, row["id"])
    if not closed:
        return (NOT_OPEN.format(poll_id=row["id"], status=fresh["status"]), fresh)
    return ((ENDED if written else ENDED_NO_RESULT).format(poll_id=row["id"]), fresh)


async def cancel_poll_now(bot: Any, guild: Any, row: Any, actor: Any) -> tuple[str, Any]:
    stopped = await cancel_poll(bot, guild, row, by=actor)
    fresh = await get_poll(bot.db, row["id"])
    if not stopped:
        return (NOT_OPEN.format(poll_id=row["id"], status=fresh["status"]), fresh)
    return (CANCELLED_SAID.format(poll_id=row["id"]), fresh)


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


async def send_review_card(bot: Any, guild: Any, row: Any) -> tuple[Any, Any]:
    """(where it went, the card) — the one place a poll reaches staff for a decision."""
    target = card_channel(bot, guild)
    if target is None:
        return (None, None)
    options = await options_of(bot.db, row["id"])
    try:
        message = await target.send(
            embed=card_for(row, options),
            view=review_view(row["id"]),
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except Exception as exc:
        log.warning("polls: could not post the review card for %s: %s", row["id"], exc)
        await log_action(
            bot,
            guild,
            "poll.card_failed",
            details={"poll_id": row["id"], "reason": f"{type(exc).__name__}: {exc}"},
        )
        return (target, None)
    await set_review(bot.db, row["id"], target.id, message.id)
    return (target, message)


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


class PollPanel(Panel):
    def __init__(self, minutes: int) -> None:
        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER)


def minutes_for(store: Any, guild_id: int) -> int:
    return panel_minutes(store, guild_id, PANEL_MINUTES_KEY)


def polls_are_on(store: Any, guild_id: int) -> bool:
    return store.get(guild_id, "poll_mode") != "off"


def may_create(store: Any, guild_id: int, actor: Any) -> bool:
    if not polls_are_on(store, guild_id):
        return False
    if store.get(guild_id, "poll_who_can_create") == "everyone":
        return True
    return store.is_staff(actor)


def creator_may_end(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, CREATOR_MAY_END_KEY))


def site_page_url(origin: Any) -> str | None:
    return library_site_page_url(origin, "poll")


def pick_placeholder(shown: int, total: int) -> str:
    return capped_placeholder(shown, total, pick=PICK_A_POLL)


def recur_placeholder(shown: int, total: int) -> str:
    return capped_placeholder(shown, total, pick=PICK_A_RECURRENCE)


@dataclass
class PollDraft:
    """Everything typed so far. Nothing is written down until `Post it` — fork I-3."""

    question: str = ""
    options: str = ""
    hours: str = ""
    kind: str = SINGLE
    anonymous: bool = False
    hidden: bool = False
    channel_id: int | None = None
    ping_role_id: int | None = None
    thread: bool = False
    start: str = ""
    slots: str = ""
    step: str = ""
    step_unit: str = STEP_DAYS
    cadence: str = ""
    day: str = ""
    at: str = ""
    tz: str = DEFAULT_TZ
    repeating: bool = False

    def asked(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "kind": self.kind,
            "options": self.options,
            "hours": int(self.hours.strip()) if self.hours.strip() else None,
            "anonymous": self.anonymous,
            "results": AT_CLOSE if self.hidden else LIVE,
            "start": self.start or None,
            "slots": whole_or_text(self.slots),
            "step": whole_or_text(self.step),
            "step_unit": self.step_unit,
        }


def whole_or_text(given: Any) -> Any:
    """A number when it is one, the typed text when it is not — so the refusal can quote it."""
    text = str(given or "").strip()
    return int(text) if text.isdigit() else text


def draft_trouble(draft: PollDraft) -> str | None:
    """The one thing `poll_plan` cannot be handed: hours that are not a whole number."""
    typed = draft.hours.strip()
    if typed and not typed.isdigit():
        return BAD_HOURS.format(given=clamp(typed, 40), low=MIN_HOURS, high=MAX_HOURS)
    return None


def draft_plan(store: Any, guild_id: int, draft: PollDraft) -> tuple[Any, str | None]:
    trouble = draft_trouble(draft)
    if trouble is not None:
        return (None, trouble)
    return poll_plan(store, guild_id, **draft.asked())


async def build_panel(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, PollPanel]:
    store, db = bot.store, bot.db
    staff = store.is_staff(actor)
    on = polls_are_on(store, guild.id)
    can_create = may_create(store, guild.id, actor)
    rows = await polls_by_status(db, guild.id, OPEN_STATUSES)
    repeats = await recurrences(db, guild.id) if staff else []
    shown = rows[:LIST_LIMIT]

    lines = [PANEL_INTRO]
    if staff:
        lines.append(
            PANEL_COUNTS.format(
                running=sum(1 for row in rows if row["status"] == OPEN),
                waiting=sum(1 for row in rows if row["status"] == PENDING_REVIEW),
                repeating=len(repeats),
            )
        )
    if shown:
        lines.extend(summary_line(row, parse_ts(row["closes_at"])) for row in shown)
    else:
        lines.append(NO_OPEN_POLLS)
    if not on:
        lines.append(POLLS_OFF)
    elif not can_create:
        lines.append(NOT_A_CREATOR)

    embed = discord.Embed(
        title=PANEL_TITLE,
        description="\n".join(lines),
        colour=discord.Colour(COLOURS[OPEN]),
    )
    view = PollPanel(minutes_for(store, guild.id))
    if can_create:
        view.add_item(CreateButton())
    view.add_item(FindButton())
    view.add_item(RefreshButton())
    if staff:
        view.add_item(SettingsButton())
        view.add_item(LogsButton())
    if shown:
        view.add_item(PollPick(shown, len(rows)))
    if staff and repeats:
        view.add_item(RecurrencePick(repeats[:LIST_LIMIT], len(repeats)))
    page = site_page_url(getattr(bot.settings, "origin", ""))
    if page:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link, label=SITE_BUTTON, url=page, row=3
            )
        )
    return embed, view


async def build_card(
    bot: Any, guild: Any, row: Any, actor: Any
) -> tuple[discord.Embed, PollPanel]:
    counts, total, approximate = await counts_for(bot, row)
    embed = results_embed(
        poll_id=row["id"],
        question=row["question"],
        counts=counts,
        total=total,
        status=row["status"],
        kind=row["kind"],
        closed_at=row["closed_at"],
        approximate=approximate,
    )
    specs = card_buttons(
        row["status"],
        staff=bot.store.is_staff(actor),
        is_creator=row["creator_id"] == getattr(actor, "id", None),
        creator_may_end=creator_may_end(bot.store, guild.id),
    )
    if not specs:
        embed.set_footer(
            text=f"Poll #{row['id']} · {NO_MOVES_LEFT.format(status=row['status'])}"
        )
    view = PollPanel(minutes_for(bot.store, guild.id))
    for spec in specs:
        view.add_item(CardMoveButton(int(row["id"]), spec))
    view.add_item(BackButton())
    return embed, view


async def build_recurrence_card(
    bot: Any, guild: Any, row: Any
) -> tuple[discord.Embed, PollPanel]:
    options = await options_of(bot.db, row["id"])
    following = parse_ts(row["recur_next_at"])
    embed = recurrence_card(
        poll_id=row["id"],
        question=row["question"],
        cadence=describe_cadence(row["recurrence"], row["recur_at"], row["recur_tz"]),
        following=following,
        channel_id=row["channel_id"],
        kind=row["kind"],
        labels=[str(item["label"]) for item in options],
        hours=row["hours"],
    )
    view = PollPanel(minutes_for(bot.store, guild.id))
    if following is not None:
        view.add_item(RecurMoveButton(int(row["id"]), "pause", PAUSE_BUTTON, "secondary"))
    else:
        view.add_item(RecurMoveButton(int(row["id"]), "resume", RESUME_BUTTON, "primary"))
    view.add_item(RecurDeleteButton(int(row["id"])))
    view.add_item(BackButton())
    return embed, view


def preview_embed(bot: Any, actor: Any, draft: PollDraft, plan: Any, trouble: Any) -> discord.Embed:
    if plan is None:
        embed = discord.Embed(
            title=CREATE_TITLE,
            description=str(trouble),
            colour=discord.Colour(COLOURS[DENIED]),
        )
    else:
        embed = review_card(
            poll_id="—",
            question=plan["question"],
            creator_id=getattr(actor, "id", 0),
            kind=plan["kind"],
            labels=plan["labels"],
            hours=plan["hours"],
            status=DRAFT,
        )
    embed.add_field(
        name="Where",
        value=f"<#{draft.channel_id}>" if draft.channel_id else "not set",
        inline=True,
    )
    embed.add_field(
        name="Ping", value=f"<@&{draft.ping_role_id}>" if draft.ping_role_id else "nobody",
        inline=True,
    )
    embed.add_field(name="Thread", value="on" if draft.thread else "off", inline=True)
    if draft.repeating:
        embed.add_field(
            name="Repeats",
            value=describe_cadence(
                cadence_token(draft.cadence, draft.day), draft.at, draft.tz
            ),
            inline=False,
        )
    if draft.kind == DATE and plan is None:
        embed.add_field(name="Slots", value=DRAFT_NEEDS_SLOTS, inline=False)
    embed.set_footer(text=DRAFT_INTRO)
    return embed


class PreviewView(PollPanel):
    def __init__(self, minutes: int, draft: PollDraft, *, postable: bool, staff: bool) -> None:
        super().__init__(minutes)
        self.draft = draft
        if draft.kind == DATE:
            self.add_item(SlotsButton())
        if postable:
            self.add_item(PostButton())
        if staff and draft.kind != DATE:
            self.add_item(RepeatButton())
        self.add_item(StartOverButton())
        self.add_item(GiveUpButton())
        self.add_item(DraftChannelSelect())
        self.add_item(DraftRoleSelect())
        self.add_item(ThreadToggle(draft.thread))


async def render_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    bot = interaction.client
    embed, view = await build_panel(bot, interaction.guild, interaction.user)
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed,
        view=view,
        allowed_mentions=discord.AllowedMentions.none(),
    )


async def render_preview(
    interaction: discord.Interaction, draft: PollDraft, previous: Any = None
) -> None:
    bot = interaction.client
    plan, trouble = draft_plan(bot.store, interaction.guild.id, draft)
    embed = preview_embed(bot, interaction.user, draft, plan, trouble)
    view = PreviewView(
        minutes_for(bot.store, interaction.guild.id),
        draft,
        postable=plan is not None,
        staff=bot.store.is_staff(interaction.user),
    )
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed,
        view=view,
        allowed_mentions=discord.AllowedMentions.none(),
    )


async def open_preview(
    interaction: discord.Interaction, draft: PollDraft, previous: Any = None
) -> None:
    if not await opened(interaction, staff=False):
        return
    await render_preview(interaction, draft, previous)


async def back_to_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction, staff=False):
        return
    await render_panel(interaction, previous)


async def show_row(interaction: discord.Interaction, row: Any, previous: Any = None) -> None:
    bot = interaction.client
    if row["status"] == RECURRING:
        embed, view = await build_recurrence_card(bot, interaction.guild, row)
    else:
        embed, view = await build_card(bot, interaction.guild, row, interaction.user)
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed,
        view=view,
        allowed_mentions=discord.AllowedMentions.none(),
    )


async def said_to(interaction: discord.Interaction, text: str) -> None:
    await interaction.followup.send(
        text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )


async def wanted_poll(interaction: discord.Interaction, poll_id: Any) -> Any:
    """The row a click is about, or None with the caller already told why not."""
    bot = interaction.client
    row = await get_poll(bot.db, int(poll_id))
    if row is None or row["guild_id"] != interaction.guild.id:
        await said_to(interaction, NO_SUCH_POLL)
        return None
    if row["status"] == RECURRING and not bot.store.is_staff(interaction.user):
        await said_to(interaction, bot.store.staff_refusal(interaction.guild.id))
        return None
    return row


async def open_card(
    interaction: discord.Interaction, poll_id: int, previous: Any = None
) -> None:
    if not await opened(interaction, staff=False):
        return
    row = await wanted_poll(interaction, poll_id)
    if row is None:
        return
    await show_row(interaction, row, previous)


async def finish_card(
    interaction: discord.Interaction,
    poll_id: int,
    said: str,
    fresh: Any,
    previous: Any = None,
) -> None:
    row = fresh if fresh is not None else await get_poll(interaction.client.db, poll_id)
    if row is None:
        await render_panel(interaction, previous)
    else:
        await show_row(interaction, row, previous)
    await said_to(interaction, said)


MOVE_FUNCS: dict[str, Any] = {
    "post": lambda bot, guild, row, actor: post_now(bot, guild, row),
    "cancel": cancel_poll_now,
    "end": end_poll_now,
    "approve": lambda bot, guild, row, actor: apply_decision(
        bot, guild, int(row["id"]), OPEN, actor
    ),
    "post_anyway": lambda bot, guild, row, actor: apply_decision(
        bot, guild, int(row["id"]), OPEN, actor
    ),
}

RECUR_FUNCS: dict[str, Any] = {
    "pause": lambda bot, guild, row, actor: pause_recurrence(bot, guild, row, actor),
    "resume": lambda bot, guild, row, actor: resume_recurrence(bot, guild, row, actor),
    "delete": lambda bot, guild, row, actor: delete_recurrence(bot, guild, row, actor),
}


async def run_move(
    interaction: discord.Interaction, poll_id: int, action: str, previous: Any = None
) -> None:
    if not await opened(interaction, staff=False):
        return
    bot = interaction.client
    row = await wanted_poll(interaction, poll_id)
    if row is None:
        return
    if row["channel_id"] and not guard_allows(bot, row["channel_id"]):
        await finish_card(interaction, poll_id, guard_refusal(bot), row, previous)
        return
    said, fresh = await MOVE_FUNCS[action](bot, interaction.guild, row, interaction.user)
    await finish_card(interaction, poll_id, said, fresh, previous)


async def run_recur_move(
    interaction: discord.Interaction, poll_id: int, action: str, previous: Any = None
) -> None:
    if not await opened(interaction, staff=False):
        return
    bot = interaction.client
    row = await get_recurrence(bot.db, interaction.guild.id, int(poll_id))
    if row is None:
        await said_to(interaction, NOT_A_RECURRENCE.format(poll_id=poll_id))
        return
    said, fresh = await RECUR_FUNCS[action](bot, interaction.guild, row, interaction.user)
    await finish_card(interaction, poll_id, said, fresh, previous)


async def may_end(interaction: discord.Interaction, poll_id: int) -> bool:
    """The one non-staff move: staff always, the poll's author while the key allows it."""
    bot = interaction.client
    if bot.store.is_staff(interaction.user):
        return True
    row = await get_poll(bot.db, int(poll_id))
    theirs = row is not None and row["creator_id"] == interaction.user.id
    if theirs and creator_may_end(bot.store, interaction.guild.id):
        return True
    await answer(
        interaction,
        NOT_YOURS_TO_END if theirs else NOT_YOURS.format(poll_id=poll_id),
    )
    return False


async def write_draft(
    interaction: discord.Interaction, draft: PollDraft, previous: Any = None
) -> None:
    """The ONE write the create flow makes — one row, its options and one log line."""
    bot = interaction.client
    guild = interaction.guild
    if not polls_are_on(bot.store, guild.id):
        await render_panel(interaction, previous)
        await said_to(interaction, POLLS_OFF)
        return
    if not may_create(bot.store, guild.id, interaction.user):
        await render_panel(interaction, previous)
        await said_to(interaction, NOT_A_CREATOR)
        return
    if draft.repeating and not bot.store.is_staff(interaction.user):
        await render_panel(interaction, previous)
        await said_to(interaction, bot.store.staff_refusal(guild.id))
        return
    plan, refusal = draft_plan(bot.store, guild.id, draft)
    if plan is None:
        await render_preview(interaction, draft, previous)
        await said_to(interaction, str(refusal))
        return
    channel = bot.get_channel(draft.channel_id) if draft.channel_id else None
    if channel is None:
        await render_preview(interaction, draft, previous)
        await said_to(interaction, NO_CHANNEL)
        return
    if not guard_allows(bot, channel):
        await render_preview(interaction, draft, previous)
        await said_to(interaction, guard_refusal(bot))
        return
    role_id = (
        draft.ping_role_id
        if draft.ping_role_id is not None
        else bot.store.get(guild.id, "poll_ping_role_id")
    )
    row, reviewing = await store_poll(
        bot,
        guild,
        interaction.user.id,
        plan,
        channel_id=channel.id,
        ping_role_id=role_id,
        auto_thread=draft.thread,
        status=RECURRING if draft.repeating else None,
    )
    if draft.repeating:
        said, fresh = await save_recurrence(
            bot,
            guild,
            row,
            cadence_token(draft.cadence, draft.day),
            draft.at,
            draft.tz,
            interaction.user,
        )
    elif reviewing:
        said, fresh = await send_for_review(
            bot, guild, row, interaction.user, plan["note"]
        )
    else:
        said, fresh = await post_now(bot, guild, row, plan["note"])
    await finish_card(interaction, int(row["id"]), said, fresh, previous)


class CreateButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=CREATE_BUTTON, style=discord.ButtonStyle.primary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        bot = interaction.client
        guild = interaction.guild
        if not polls_are_on(bot.store, guild.id):
            await answer(interaction, POLLS_OFF)
            return
        if not may_create(bot.store, guild.id, interaction.user):
            await answer(interaction, NOT_A_CREATOR)
            return
        draft = PollDraft(
            channel_id=interaction.channel_id,
            thread=bool(bot.store.get(guild.id, "poll_auto_thread")),
        )
        await interaction.response.send_modal(NewPollModal(draft, self.view))


class FindButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=FIND_BUTTON, style=discord.ButtonStyle.secondary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(FindModal(self.view))


class RefreshButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=REFRESH_BUTTON, style=discord.ButtonStyle.secondary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await back_to_panel(interaction, self.view)


class SettingsButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=SETTINGS_BUTTON, style=discord.ButtonStyle.secondary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        if not await opened(interaction, staff=False):
            return
        await render_settings(interaction, self.view)


class LogsButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=LOGS_BUTTON, style=discord.ButtonStyle.secondary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await send_logs(interaction, "poll")


class BackButton(discord.ui.Button):
    def __init__(self, row: int = 1) -> None:
        super().__init__(label=BACK_BUTTON, style=discord.ButtonStyle.secondary, row=row)

    async def callback(self, interaction: discord.Interaction) -> None:
        await back_to_panel(interaction, self.view)


class PollPick(discord.ui.Select):
    def __init__(self, rows: list[Any], total: int) -> None:
        super().__init__(
            placeholder=pick_placeholder(len(rows), total),
            options=[
                discord.SelectOption(
                    label=option_label(row["id"], row["status"], row["question"]),
                    value=str(row["id"]),
                )
                for row in rows
            ],
            min_values=1,
            max_values=1,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_card(interaction, int(self.values[0]), self.view)


class RecurrencePick(discord.ui.Select):
    def __init__(self, rows: list[Any], total: int) -> None:
        super().__init__(
            placeholder=recur_placeholder(len(rows), total),
            options=[
                discord.SelectOption(
                    label=option_label(
                        row["id"],
                        "paused" if not row["recur_next_at"] else "repeating",
                        row["question"],
                    ),
                    value=str(row["id"]),
                )
                for row in rows
            ],
            min_values=1,
            max_values=1,
            row=2,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_card(interaction, int(self.values[0]), self.view)


class CardMoveButton(discord.ui.Button):
    def __init__(self, poll_id: int, spec: Any) -> None:
        super().__init__(label=spec.label, style=BUTTON_STYLES[spec.style], row=0)
        self.poll_id = poll_id
        self.spec = spec

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.spec.staff_only:
            if not await still_staff(interaction):
                return
        elif not await may_end(interaction, self.poll_id):
            return
        if self.spec.needs_modal:
            await interaction.response.send_modal(DenyModal(self.poll_id, self.view))
            return
        await run_move(interaction, self.poll_id, self.spec.action, self.view)


class RecurMoveButton(discord.ui.Button):
    def __init__(self, poll_id: int, action: str, label: str, style: str) -> None:
        super().__init__(label=label, style=BUTTON_STYLES[style], row=0)
        self.poll_id = poll_id
        self.action = action

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await run_recur_move(interaction, self.poll_id, self.action, self.view)


class RecurDeleteButton(discord.ui.Button):
    def __init__(self, poll_id: int) -> None:
        super().__init__(label=DELETE_BUTTON, style=discord.ButtonStyle.danger, row=0)
        self.poll_id = poll_id

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        if not await opened(interaction, staff=False):
            return
        bot = interaction.client
        row = await get_recurrence(bot.db, interaction.guild.id, self.poll_id)
        if row is None:
            await said_to(interaction, NOT_A_RECURRENCE.format(poll_id=self.poll_id))
            return
        embed, _ = await build_recurrence_card(bot, interaction.guild, row)
        view = PollPanel(minutes_for(bot.store, interaction.guild.id))
        view.add_item(DeleteYesButton(self.poll_id))
        view.add_item(DeleteKeepButton(self.poll_id))
        retire(self.view)
        view.message = await interaction.edit_original_response(
            embed=embed,
            view=view,
            allowed_mentions=discord.AllowedMentions.none(),
        )


class DeleteYesButton(discord.ui.Button):
    def __init__(self, poll_id: int) -> None:
        super().__init__(label=DELETE_YES_BUTTON, style=discord.ButtonStyle.danger, row=0)
        self.poll_id = poll_id

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await run_recur_move(interaction, self.poll_id, "delete", self.view)


class DeleteKeepButton(discord.ui.Button):
    def __init__(self, poll_id: int) -> None:
        super().__init__(label=DELETE_KEEP_BUTTON, style=discord.ButtonStyle.secondary, row=0)
        self.poll_id = poll_id

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_card(interaction, self.poll_id, self.view)


class PostButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=POST_BUTTON, style=discord.ButtonStyle.success, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction, staff=False):
            return
        await write_draft(interaction, self.view.draft, self.view)


class SlotsButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=SLOTS_BUTTON, style=discord.ButtonStyle.primary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(SlotsModal(self.view.draft, self.view))


class RepeatButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=REPEAT_BUTTON, style=discord.ButtonStyle.secondary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        if self.view.draft.kind == DATE:
            await answer(interaction, RECUR_NOT_A_DATE)
            return
        await interaction.response.send_modal(CadenceModal(self.view.draft, self.view))


class StartOverButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=START_OVER_BUTTON, style=discord.ButtonStyle.secondary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(NewPollModal(self.view.draft, self.view))


class GiveUpButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=GIVE_UP_BUTTON, style=discord.ButtonStyle.danger, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await back_to_panel(interaction, self.view)


class DraftChannelSelect(discord.ui.ChannelSelect):
    def __init__(self) -> None:
        super().__init__(
            placeholder=DRAFT_CHANNEL_PICK,
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.draft.channel_id = int(self.values[0].id)
        await open_preview(interaction, self.view.draft, self.view)


class DraftRoleSelect(discord.ui.RoleSelect):
    def __init__(self) -> None:
        super().__init__(placeholder=DRAFT_ROLE_PICK, min_values=1, max_values=1, row=2)

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.draft.ping_role_id = int(self.values[0].id)
        await open_preview(interaction, self.view.draft, self.view)


class ThreadToggle(discord.ui.Button):
    def __init__(self, on: bool) -> None:
        super().__init__(
            label=THREAD_ON if on else THREAD_OFF,
            style=discord.ButtonStyle.secondary,
            row=3,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.draft.thread = not self.view.draft.thread
        await open_preview(interaction, self.view.draft, self.view)


def radio(options: Any, chosen: Any) -> discord.ui.RadioGroup:
    return discord.ui.RadioGroup(
        options=[
            discord.RadioGroupOption(
                label=str(label), value=str(value), default=str(value) == str(chosen)
            )
            for value, label in options
        ]
    )


class NewPollModal(AnswersErrors, discord.ui.Modal):
    """Step 1 — Discord's five-component cap, used exactly."""

    def __init__(self, draft: PollDraft, previous: Any = None) -> None:
        super().__init__(title=CREATE_TITLE)
        self.draft = draft
        self.previous = previous
        self.question = discord.ui.TextInput(
            max_length=QUESTION_LIMIT, default=draft.question or None
        )
        self.options = discord.ui.TextInput(
            style=discord.TextStyle.paragraph,
            required=False,
            default=draft.options or None,
            placeholder="Pizza | Tacos | Neither",
        )
        self.hours = discord.ui.TextInput(
            required=False, max_length=5, default=draft.hours or None
        )
        self.kind = radio(
            [(one, KIND_NAMES.get(one, one)) for one in KNOWN_KINDS], draft.kind
        )
        self.switches = discord.ui.CheckboxGroup(
            options=[
                discord.CheckboxGroupOption(
                    label=SWITCH_ANONYMOUS, value="anonymous", default=draft.anonymous
                ),
                discord.CheckboxGroupOption(
                    label=SWITCH_HIDDEN, value="hidden", default=draft.hidden
                ),
            ],
            required=False,
            min_values=0,
            max_values=2,
        )
        self.add_item(discord.ui.Label(text="What are you asking?", component=self.question))
        self.add_item(
            discord.ui.Label(text="The answers, separated by |", component=self.options)
        )
        self.add_item(
            discord.ui.Label(
                text="How many hours? (blank for the server default)", component=self.hours
            )
        )
        self.add_item(discord.ui.Label(text=KIND_LABEL, component=self.kind))
        self.add_item(discord.ui.Label(text=SWITCHES_LABEL, component=self.switches))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        picked = picked_values(self.kind)
        chosen = set(picked_values(self.switches))
        self.draft.question = str(self.question)
        self.draft.options = str(self.options)
        self.draft.hours = str(self.hours)
        self.draft.kind = picked[0] if picked else SINGLE
        self.draft.anonymous = "anonymous" in chosen
        self.draft.hidden = "hidden" in chosen
        if self.draft.kind == DATE:
            self.draft.repeating = False
        await open_preview(interaction, self.draft, self.previous)


class SlotsModal(AnswersErrors, discord.ui.Modal):
    """Step 2a — only a date poll ever sees it."""

    def __init__(self, draft: PollDraft, previous: Any = None) -> None:
        super().__init__(title=SLOTS_TITLE)
        self.draft = draft
        self.previous = previous
        self.start = discord.ui.TextInput(
            max_length=20, default=draft.start or None, placeholder="2026-09-05"
        )
        self.slots = discord.ui.TextInput(max_length=3, default=draft.slots or None)
        self.step = discord.ui.TextInput(max_length=4, default=draft.step or None)
        self.unit = radio([(one, one) for one in DATE_STEPS], draft.step_unit)
        self.add_item(
            discord.ui.Label(
                text="First slot — 2026-09-05 or 2026-09-05 19:00", component=self.start
            )
        )
        self.add_item(
            discord.ui.Label(
                text=f"How many slots? ({MIN_SLOTS}-{MAX_SLOTS})", component=self.slots
            )
        )
        self.add_item(
            discord.ui.Label(text=f"Gap between them (1-{MAX_STEP})", component=self.step)
        )
        self.add_item(discord.ui.Label(text=STEP_UNIT_LABEL, component=self.unit))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        picked = picked_values(self.unit)
        self.draft.start = str(self.start)
        self.draft.slots = str(self.slots)
        self.draft.step = str(self.step)
        self.draft.step_unit = picked[0] if picked else STEP_DAYS
        await open_preview(interaction, self.draft, self.previous)


class CadenceModal(AnswersErrors, discord.ui.Modal):
    """`Repeat…` — the same plan, saved as a template instead of posted."""

    def __init__(self, draft: PollDraft, previous: Any = None) -> None:
        super().__init__(title=CADENCE_TITLE)
        self.draft = draft
        self.previous = previous
        self.every = radio([(one, one) for one in CADENCES], draft.cadence or DAILY)
        self.at = discord.ui.TextInput(
            max_length=5, default=draft.at or None, placeholder="19:00"
        )
        self.day = discord.ui.TextInput(max_length=10, required=False, default=draft.day or None)
        self.tz = discord.ui.TextInput(max_length=60, default=draft.tz or DEFAULT_TZ)
        self.add_item(discord.ui.Label(text=CADENCE_LABEL, component=self.every))
        self.add_item(discord.ui.Label(text="Time of day, 24-hour clock", component=self.at))
        self.add_item(
            discord.ui.Label(
                text=f"weekly: {WEEKDAYS[0]}-{WEEKDAYS[-1]} · monthly: 1-{MAX_MONTH_DAY}",
                component=self.day,
            )
        )
        self.add_item(discord.ui.Label(text="Timezone", component=self.tz))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if self.draft.kind == DATE:
            await answer(interaction, RECUR_NOT_A_DATE)
            return
        picked = picked_values(self.every)
        every = picked[0] if picked else DAILY
        trouble = cadence_trouble(every, str(self.day), str(self.at), str(self.tz))
        if trouble is not None:
            await answer(interaction, trouble)
            return
        self.draft.cadence = every
        self.draft.day = str(self.day)
        self.draft.at = str(self.at)
        self.draft.tz = str(self.tz)
        self.draft.repeating = True
        await open_preview(interaction, self.draft, self.previous)


class FindModal(AnswersErrors, discord.ui.Modal):
    """Any poll by number, so a closed or archived one is still reachable."""

    def __init__(self, previous: Any = None) -> None:
        super().__init__(title=FIND_TITLE)
        self.previous = previous
        self.number = discord.ui.TextInput(max_length=FIND_LIMIT)
        self.add_item(discord.ui.Label(text=FIND_LABEL, component=self.number))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        wanted = poll_id_from(str(self.number))
        if wanted is None:
            await answer(interaction, NOT_AN_ID.format(given=clamp(str(self.number), 40)))
            return
        await open_card(interaction, wanted, self.previous)


class DenyModal(PanelNoteModal):
    def __init__(self, poll_id: int, previous: Any = None) -> None:
        self.poll_id = poll_id
        self.previous = previous
        super().__init__(
            title=DENY_TITLE,
            label=DENY_LABEL,
            max_length=DENY_LIMIT,
            on_submit=self.deny,
        )

    async def deny(self, interaction: discord.Interaction, text: str) -> None:
        if not await still_staff(interaction):
            return
        if not await opened(interaction, staff=False):
            return
        said, fresh = await apply_decision(
            interaction.client,
            interaction.guild,
            self.poll_id,
            DENIED,
            interaction.user,
            clamp(text, DENY_LIMIT),
        )
        await finish_card(interaction, self.poll_id, said, fresh, self.previous)


SETTINGS_TOGGLES: tuple[tuple[str, str, Any], ...] = (
    ("poll_mode", "Polls", POLL_MODES),
    ("poll_who_can_create", "Create", POLL_CREATORS),
    ("poll_review_mode", "Review", POLL_REVIEW_MODES),
    ("poll_auto_thread", "Threads", None),
    ("poll_archive_drop_votes", "Drop votes", None),
)
NUMBER_FIELDS: tuple[tuple[str, str, int, int], ...] = (
    ("poll_default_hours", "How long a poll stays open, in hours", MIN_HOURS, MAX_HOURS),
    (
        "poll_reminder_minutes",
        "Last call, minutes before close (0 for none)",
        0,
        POLL_REMINDER_MAX_MINUTES,
    ),
    (
        "poll_archive_days",
        "Days a closed poll stays on the list",
        POLL_ARCHIVE_MIN_DAYS,
        POLL_ARCHIVE_MAX_DAYS,
    ),
    ("poll_panel_minutes", "Minutes this panel stays live", 1, 60),
)
NOT_A_NUMBER = "**{given}** is not a whole number between {low} and {high}, so nothing was saved."


def next_value(store: Any, guild_id: int, key: str, choices: Any) -> Any:
    current = store.get(guild_id, key)
    if choices is None:
        return not bool(current)
    found = list(choices)
    where = found.index(current) if current in found else 0
    return found[(where + 1) % len(found)]


async def render_settings(interaction: discord.Interaction, previous: Any = None) -> None:
    bot = interaction.client
    guild = interaction.guild
    cog = bot.get_cog(COG_NAME)
    lines = cog.settings_lines(guild) if cog is not None else []
    embed = discord.Embed(
        title=SETTINGS_TITLE,
        description="\n".join(lines),
        colour=discord.Colour(COLOURS[OPEN]),
    )
    view = PollPanel(minutes_for(bot.store, guild.id))
    for key, name, choices in SETTINGS_TOGGLES:
        view.add_item(SettingsToggle(bot.store, guild.id, key, name, choices))
    view.add_item(SettingsChannelSelect())
    view.add_item(SettingsRoleSelect())
    view.add_item(DateLabelPick(bot.store.get(guild.id, "poll_date_labels")))
    view.add_item(NumbersButton())
    view.add_item(ClearRoleButton())
    view.add_item(ClearChannelButton())
    view.add_item(BackButton(row=4))
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed,
        view=view,
        allowed_mentions=discord.AllowedMentions.none(),
    )


async def save_settings(
    interaction: discord.Interaction,
    changes: Any,
    clears: Any = (),
    previous: Any = None,
) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    await apply_poll_settings(
        interaction.client, interaction.guild, interaction.user, changes, clears
    )
    await render_settings(interaction, previous)


class SettingsToggle(discord.ui.Button):
    def __init__(self, store: Any, guild_id: int, key: str, name: str, choices: Any) -> None:
        current = store.get(guild_id, key)
        shown = ("on" if current else "off") if choices is None else str(current)
        super().__init__(
            label=f"{name}: {shown}", style=discord.ButtonStyle.secondary, row=0
        )
        self.key = key
        self.choices = choices

    async def callback(self, interaction: discord.Interaction) -> None:
        wanted = next_value(
            interaction.client.store, interaction.guild.id, self.key, self.choices
        )
        await save_settings(interaction, {self.key: wanted}, (), self.view)


class SettingsChannelSelect(discord.ui.ChannelSelect):
    def __init__(self) -> None:
        super().__init__(
            placeholder=SETTINGS_CHANNEL_PICK,
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await save_settings(
            interaction, {"poll_channel_id": int(self.values[0].id)}, (), self.view
        )


class SettingsRoleSelect(discord.ui.RoleSelect):
    def __init__(self) -> None:
        super().__init__(placeholder=SETTINGS_ROLE_PICK, min_values=1, max_values=1, row=2)

    async def callback(self, interaction: discord.Interaction) -> None:
        await save_settings(
            interaction, {"poll_ping_role_id": int(self.values[0].id)}, (), self.view
        )


class DateLabelPick(discord.ui.Select):
    def __init__(self, current: Any) -> None:
        super().__init__(
            placeholder=DATE_LABELS_PICK,
            options=[
                discord.SelectOption(label=one, value=one, default=one == current)
                for one in DATE_LABEL_FORMS
            ],
            min_values=1,
            max_values=1,
            row=3,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await save_settings(
            interaction, {"poll_date_labels": str(self.values[0])}, (), self.view
        )


class NumbersButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=NUMBERS_BUTTON, style=discord.ButtonStyle.secondary, row=4)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.send_modal(
            NumbersModal(interaction.client.store, interaction.guild.id, self.view)
        )


class ClearRoleButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=CLEAR_PING_BUTTON, style=discord.ButtonStyle.secondary, row=4)

    async def callback(self, interaction: discord.Interaction) -> None:
        await save_settings(interaction, {}, ("poll_ping_role_id",), self.view)


class ClearChannelButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=CLEAR_CHANNEL_BUTTON, style=discord.ButtonStyle.secondary, row=4)

    async def callback(self, interaction: discord.Interaction) -> None:
        await save_settings(interaction, {}, ("poll_channel_id",), self.view)


class NumbersModal(AnswersErrors, discord.ui.Modal):
    def __init__(self, store: Any, guild_id: int, previous: Any = None) -> None:
        super().__init__(title=NUMBERS_TITLE)
        self.previous = previous
        self.fields: list[Any] = []
        for key, label, _, _ in NUMBER_FIELDS:
            field = discord.ui.TextInput(
                max_length=8, required=False, default=str(store.get(guild_id, key))
            )
            self.fields.append(field)
            self.add_item(discord.ui.Label(text=label, component=field))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        changes: dict[str, Any] = {}
        for (key, _, low, high), field in zip(NUMBER_FIELDS, self.fields, strict=True):
            typed = str(field).strip()
            if not typed:
                continue
            if not typed.isdigit() or not low <= int(typed) <= high:
                await answer(
                    interaction, NOT_A_NUMBER.format(given=clamp(typed, 20), low=low, high=high)
                )
                return
            changes[key] = int(typed)
        await save_settings(interaction, changes, (), self.previous)


class Polls(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.last_ok_at: dict[str, str | None] = {name: None for name in LOOP_NAMES}
        self.last_error: dict[str, str | None] = {name: None for name in LOOP_NAMES}

    async def cog_load(self) -> None:
        self.bot.add_dynamic_items(
            PollDecisionButton, PollVoteButton, PollOpenVoteButton, PollClearVoteButton
        )
        if not poll_secret(self.bot):
            log.warning(POLL_SECRET_UNSET)
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

    @app_commands.command(
        name="poll", description="Put something to the room, or manage the polls that are up"
    )
    async def poll(self, interaction: discord.Interaction) -> None:
        if not await self._ready(interaction):
            return
        embed, view = await build_panel(self.bot, interaction.guild, interaction.user)
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()

    async def counts_for(self, row: Any) -> tuple[list[dict[str, Any]], int, bool]:
        return await counts_for(self.bot, row)

    def settings_lines(self, guild: Any) -> list[str]:
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
