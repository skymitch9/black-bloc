from __future__ import annotations

import asyncio
import io
import logging
import re
import sqlite3
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from time import monotonic
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ...actionlog import log_action, send_logs
from ...command_errors import AnswersErrors, SafeDynamicItem
from ...command_visibility import STAFF_ONLY
from ...events import clamp
from ...golive import now_iso, parse_ts
from ...logkinds import VIA_DISCORD, kind_via
from ...loops import wait_ready
from ...modmail import (
    ANONYMOUS_NAME,
    AUTO_ARCHIVE_MINUTES,
    BACK,
    BLOCK_PICK,
    BLOCK_REASON,
    BLOCKED_MOVE,
    BLOCKED_TITLE,
    CARD_ANON,
    CARD_CLOSE,
    CARD_CLOSED_FOOTER,
    CARD_END,
    CARD_MOVES,
    CARD_NOTE,
    CARD_REPLY,
    CARD_SPEAK,
    CATEGORY,
    CLOSED,
    CONTENT_LIMIT,
    DISABLE,
    ENABLE,
    FORGET,
    FORGET_TITLE,
    IN,
    LOGS,
    MEMBER_COMMAND_KEY,
    MEMBER_INTRO,
    MEMBER_TICKET_OPEN,
    MEMBER_TICKET_SEEN,
    MEMBER_TITLE,
    MESSAGE_LIMIT,
    MODE,
    NAME_LIMIT,
    NOTE,
    OPEN,
    OPEN_WITH,
    OUT,
    PANEL_CHANNEL_KEY,
    PANEL_DOWN,
    PANEL_HEADING_KEY,
    PANEL_MESSAGE_KEY,
    PANEL_MOVE_TO,
    PANEL_POST,
    PANEL_TEXT_KEY,
    PANEL_TIMEOUT_FOOTER,
    PANEL_TITLE,
    PICK_A_BLOCK,
    PICK_A_CATEGORY,
    PICK_A_CHANNEL,
    PICK_A_MEMBER,
    PICK_A_MODE,
    PICK_A_PLACE,
    PICK_A_REPLY_STYLE,
    PICK_A_SNIPPET,
    PICK_A_TICKET,
    PICK_SOMEBODY,
    PRACTICE,
    PRACTICE_NO,
    PRACTICE_YES,
    REFRESH,
    REPLY_STYLE,
    REPLY_STYLE_KEY,
    REPLY_STYLE_OPTIONS,
    ROOT_ROW_SELECT,
    SETUP,
    SETUP_TITLE,
    SITE,
    SNIPPET_CHANGE,
    SNIPPET_NAME_LIMIT,
    SNIPPET_REMOVE,
    SNIPPET_REMOVE_NO,
    SNIPPET_REMOVE_YES,
    SNIPPETS,
    SNIPPETS_TITLE,
    SOURCE_CARD,
    SOURCE_COMMAND,
    SOURCE_DM,
    SOURCE_PANEL,
    SOURCE_PRACTICE,
    SOURCE_STAFF,
    SOURCE_TYPED,
    STAFF_CHANNEL,
    TICKET_BUTTON,
    TICKET_BUTTON_TITLE,
    TICKET_MOVE,
    TICKET_OPEN,
    TICKET_SURFACE,
    TRANSCRIPTS,
    UNBLOCK,
    attachment_urls,
    blocked_buttons,
    blocked_lines,
    card_buttons,
    closing_dm,
    count_directions,
    door_buttons,
    dump_attachments,
    field_of,
    first_message,
    forget_buttons,
    header_embed,
    is_note,
    is_practice,
    last_reply_missed,
    mentions,
    modes_sentence,
    note_body,
    opening_dm,
    panel_card_buttons,
    panel_minutes,
    relay_embed,
    relays_typing,
    reply_style_sentence,
    root_buttons,
    setup_buttons,
    snippet_buttons,
    snippet_lines,
    thread_invite,
    thread_name,
    ticket_button_buttons,
    ticket_button_embed,
    ticket_card_embed,
    ticket_channel_name,
    ticket_label,
    ticket_topic,
    transcript_embed,
    transcript_filename,
    transcript_text,
    valid_snippet_name,
)
from ...panels import (
    SELECT_OPTION_LIMIT,
    NoteModal,
    Outcome,
    Panel,
    answer,
    capped_placeholder,
    clamped,
    db_ready,
    db_up,
    opened,
    picked_values,
    refusal,
    retire,
    site_page_url,
    still_staff,
)
from ...settings_store import (
    CHANNEL_MODE,
    DB_UNAVAILABLE,
    GUILD_ONLY,
    MODMAIL_MODES,
    MODMAIL_OPEN_WITH_BUTTON,
    MODMAIL_REPLY_STYLES,
    THREAD_MODE,
    require_staff,
    staff_roles_sentence,
)

log = logging.getLogger(__name__)

LOCKS_ATTR = "_modmail_locks"
CARDS_ATTR = "_modmail_cards"
CARD_ACTIONS = "|".join(re.escape(move.action) for move in CARD_MOVES)
CARD_TEMPLATE = rf"modmail:card:(?P<action>{CARD_ACTIONS}):(?P<ticket_id>[0-9]+)"
TICKET_PANEL_TEMPLATE = r"modmail:ticket:(?P<guild_id>[0-9]+)"
CARD_DEBOUNCE_SECONDS = 2.0
CARD_MIN_GAP_SECONDS = 8.0
CARD_REASON_LIMIT = 200
RECONCILE_MINUTES = 5
ORPHAN_GRACE_MINUTES = 5
REFUSAL_COOLDOWN_MINUTES = 10
GONE_STRIKES = 2
FORGETTABLE = {
    "category": "modmail_category_id",
    "staff": "modmail_staff_channel_id",
    "log": "modmail_log_channel_id",
}
RELAY_TYPES = (discord.MessageType.default, discord.MessageType.reply)
TICKET_REACTION = "\N{WHITE HEAVY CHECK MARK}"
NOTE_REACTION = "\N{MEMO}"
FAILED_REACTION = "\N{WARNING SIGN}"

DISABLED_DM = (
    "Black Bloc is not handling modmail on **{guild}** yet, so staff have not seen this. Send it "
    "to the **ModMail** bot instead — it is still the one on duty — and a moderator will pick it "
    "up there."
)
BLOCKED_DM = (
    "Staff on **{guild}** have stopped Black Bloc from opening modmail tickets for you, so this "
    "message was not passed on. Speak to a moderator there directly if you think that is a "
    "mistake — Black Bloc cannot undo it."
)
NO_GUILD_DM = (
    "Black Bloc only takes modmail from members of the servers it looks after, and it cannot see "
    "you in any of them. Join the server first, then DM again."
)
CANNOT_OPEN_DM = (
    "Black Bloc could not open a ticket for that message, so staff have not seen it. Try again in "
    "a minute, and tell a moderator directly if it keeps failing."
)
NO_TEST_CHANNEL = (
    "Black Bloc is in test mode and cannot see its test channel, so no ticket was made. Set "
    "TEST_CHANNEL_ID to a channel the bot can read, restart it, then try again."
)
NO_STAFF_CHANNEL = (
    "Black Bloc has nowhere to put ticket threads, so nothing was opened. A Lead points it at a "
    "channel with `/modmail` → **Setup…** → **Staff channel…**, or switches back to channel mode "
    "with **Setup…** → **Mode…**."
)
NO_TICKET_HERE = (
    "This channel is not a modmail ticket, so nothing was sent. Run the command inside a ticket, "
    "or name one with `ticket:<number>` — `/modmail` lists the open ones."
)
MANY_OPEN = (
    "Black Bloc cannot tell which ticket you mean — {count} are open, so nothing was sent. Name "
    "one with `ticket:<number>`: {ids}."
)
NOT_A_TICKET_ID = "**{given}** is not a ticket number, so nothing was sent."
NO_SUCH_TICKET = (
    "Black Bloc has no record of ticket #{ticket_id} on this server, so nothing was sent. "
    "`/modmail` lists the open ones."
)
TICKET_CLOSED = "Ticket #{ticket_id} is already closed, so nothing was sent."
NOTHING_TO_SEND = "Type some text or name a snippet — nothing was sent."
NOTHING_TO_NOTE = "A note with nothing in it says nothing, so none was saved."
NO_SNIPPET = (
    "There is no snippet called **{name}**, so nothing was sent. `/modmail` → **Snippets…** has "
    "them."
)
SENT = "Sent to the member as **{who}**."
NOTE_SAVED = "Noted on ticket #{ticket_id} — the member never sees it."
DM_FAILED_SAID = (
    "Black Bloc could not DM the member — they have DMs off or have blocked it. The ticket says "
    "so, and the log says `modmail.dm_failed`."
)
RELAY_FAILED_SAID = " The ticket itself could not be written to; the log says why."
CLOSED_SAID = "Ticket #{ticket_id} is closed.{extra}"
CLOSE_RACED = "Ticket #{ticket_id} was closed by somebody else while you were typing."
NO_TRANSCRIPT_SAID = (
    " The transcript could not be posted, so the ticket channel was left where it is rather than "
    "deleted and the messages are still in the database; the log says why."
)
SILENT_SAID = " The member was not told, because you asked for a silent close."
BLOCKED_SAID = (
    "**{who}** can no longer open modmail tickets. **Unblock them** on `/modmail` → **Blocked…** "
    "undoes it."
)
ALREADY_BLOCKED = "**{who}** was already blocked, so nothing changed."
UNBLOCKED_SAID = "**{who}** can open modmail tickets again."
NOT_BLOCKED = "**{who}** was not blocked, so nothing changed."
NO_BLOCKS = "Nobody is blocked from modmail."
LEFT_NOTE = (
    "**{who}** left the server. The ticket is still open, and a reply still reaches them by DM "
    "while they allow it."
)
FORGOTTEN = (
    "**{key}** is forgotten, so modmail falls back to its default. **Setup…** on `/modmail` "
    "points it somewhere new."
)
POINTED = "**{key}** is now {place}."
ANSWERING = (
    "Black Bloc answers modmail DMs on this server from now on. A member who DMs it gets a "
    "ticket here rather than nothing."
)
NOT_ANSWERING = (
    "Black Bloc has stopped answering modmail DMs here, so the old ModMail bot keeps them. "
    "Tickets already open stay open."
)
MODE_SET = (
    "New tickets from now on: {what}. The {count} ticket(s) already open keep the mode they were "
    "opened in — that is where their channel or thread already is."
)
BAD_SNIPPET_NAME = (
    "**{given}** is not a snippet name Black Bloc will take. Use lowercase letters, numbers, "
    f"dashes and underscores, up to {SNIPPET_NAME_LIMIT} characters — `ban-appeal`."
)
SNIPPET_SAVED = "Snippet **{name}** saved. `/reply snippet:{name}` sends it."
SNIPPET_EXISTS = (
    "There is already a snippet called **{name}**, so nothing was changed. Pick it on "
    "**Snippets…** and press **Change it…** to replace what it says, or use another name."
)
SNIPPET_GONE = "Snippet **{name}** is gone."
NO_SUCH_SNIPPET = "There is no snippet called **{name}**, so nothing was removed."
NO_SNIPPETS = "There are no snippets yet — **Add one…** makes the first."
PRACTICE_OPENED = (
    "Practice ticket #{ticket_id} is open in <#{where}>. **Speak as the member** puts a message "
    "in it, the card moves to the bottom, and **End the practice** files the transcript. Nothing "
    "here reaches anybody."
)
PRACTICE_HEADER = (
    "**This is a practice ticket.** It behaves like a real one except that no DM is ever sent — "
    "it is here so a Lead can try the card, the typed relay and `/reply` before choosing a reply "
    "style."
)
PRACTICE_SAID = "Said it — the card should now be under it."
PRACTICE_ENDED = "Practice ticket #{ticket_id} is over. The transcript is marked PRACTICE."
PRACTICE_REASON = "practice"
PRACTICE_FAILED = (
    "Black Bloc could not make the practice thread, so nothing was opened. The log says why; try "
    "again, and check it can make private threads in the test channel."
)
ALREADY_PRACTISING = (
    "You already have a modmail ticket open, and Black Bloc allows one per person — so no "
    "practice ticket was made. Close that one first."
)
NO_STAFF_TO_PRACTISE = (
    "No staff role resolves, so a practice ticket would have nobody in it and none was made. "
    "Point `staff_channel_id` at a staff-only channel with `/settings` ▸ **Roles & "
    "channels…** "
    "first."
)
NOT_PRACTICE = "That is a real ticket with a real member, so nobody can be spoken for."
NOTHING_TO_SAY = "Type something for the pretend member to say — nothing was added."
NO_STAFF_WARNING = (
    "⚠️ **No staff roles resolve**, so a ticket channel would be visible to server admins only "
    "and a ticket thread would have nobody in it. Point `staff_channel_id` at a channel only "
    "staff can see with `/settings` ▸ **Roles & channels…**, then run this again."
)

TICKET_MODAL_TITLE = "Open a ticket"
TICKET_SUBJECT_LABEL = "What is this about — a few words, if you like"
TICKET_BODY_LABEL = "Tell us what is happening"
STAFF_MODAL_TITLE = "Open a ticket with somebody"
STAFF_BODY_LABEL = "What they are sent — it opens the ticket as your first reply"
TICKET_OPENED_SAID = (
    "Your ticket is open — ticket **#{ticket_id}**. Staff can see it now, and their replies "
    "come back here as a DM from Black Bloc."
)
DMS_ARE_SHUT = (
    " ⚠️ Black Bloc could not DM you, so open DMs from this server or staff's replies will not "
    "reach you."
)
ALREADY_OPEN_SAID = (
    "You already have an open ticket, so nothing new was made. Anything you DM Black Bloc is "
    "added to it, and staff answer there."
)
CANNOT_OPEN_SAID = (
    "Black Bloc could not open a ticket just now, so staff have not seen this. Try again in a "
    "minute, and tell a moderator directly if it keeps failing."
)
A_BOT_SAID = "**{who}** is a bot, and a bot has no DMs to answer, so no ticket was opened."
STAFF_DISABLED_SAID = (
    "Black Bloc is not answering modmail here, so no ticket was opened. **Setup…** → **Answer "
    "DMs on** hands the inbox over first."
)
STAFF_BLOCKED_SAID = (
    "**{who}** is blocked from modmail, so no ticket was opened. **Unblock them** undoes that, "
    "and then this works."
)
STAFF_ALREADY_OPEN = "**{who}** already has an open ticket: <#{where}>. Reply there instead."
OPEN_WITH_OFF = (
    "**Open a ticket with…** is switched off on this server, so no ticket was opened. It needs "
    "**modmail_open_with_button** on — a Lead turns it back on from the dashboard's Settings "
    "page under **modmail**, or with `/settings` ▸ **A setting group…** ▸ modmail — and the "
    "door comes straight back."
)
STAFF_OPENED = (
    "Ticket **#{ticket_id}** with **{who}** is open in <#{where}>, and what you wrote has gone "
    "to them as your first reply."
)
STAFF_NOT_REACHED = (
    " ⚠️ The DM did not reach them — their DMs are shut or Black Bloc is blocked. The ticket "
    "holds what you wrote, and the card says so."
)
MEMBER_DOOR_OFF = (
    "Black Bloc is not answering modmail on **{guild}** yet, so there is no ticket to open. A "
    "moderator can still be reached the way you always have."
)
MEMBER_BLOCKED = (
    "Staff here have stopped Black Bloc from opening modmail tickets for you, so there is no "
    "button. Speak to a moderator directly if you think that is a mistake."
)
PANEL_NOWHERE = (
    "No **Open a ticket** button is up. **Post it…** puts one in a channel of your choosing."
)
PANEL_IS_AT = "The **Open a ticket** button is in <#{where}> — message `{message_id}`."
PANEL_POSTED_SAID = "The **Open a ticket** button is up in <#{where}>."
PANEL_MOVED_SAID = "The **Open a ticket** button is in <#{where}> now; the old message is gone."
PANEL_DOWN_SAID = "The **Open a ticket** button is down. Nothing else changed."
PANEL_NOT_UP = "There is no **Open a ticket** button up, so nothing was taken down."
PANEL_STUCK = (
    "Black Bloc could not post the **Open a ticket** button there — the log says why. Check it "
    "can write in that channel and try again."
)
PANEL_GUARDED = (
    "Black Bloc is in **test mode**, so the only channel it may post the **Open a ticket** "
    "button in is the test channel. Nothing was posted; the log says `modmail.would_post_panel`."
)
PANEL_LINES = (
    "**heading** — {title}\n**says** — {text}\nStaff change both on the Settings page, or with "
    "`/settings set-value modmail_panel_title`."
)


async def create_ticket(
    db: Any,
    guild_id: int,
    user_id: int,
    mode: str,
    *,
    source: str = SOURCE_DM,
    opened_by: Any = None,
) -> int | None:
    cur = await db.conn.execute(
        "INSERT INTO modmail_tickets(guild_id, user_id, mode, channel_id, status, opened_at, "
        "source, opened_by) VALUES (?, ?, ?, 0, ?, ?, ?, ?)",
        (
            guild_id,
            user_id,
            mode,
            OPEN,
            now_iso(),
            source,
            int(opened_by) if opened_by else None,
        ),
    )
    await db.conn.commit()
    return cur.lastrowid


async def get_ticket(db: Any, ticket_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM modmail_tickets WHERE id = ?", (ticket_id,))
    return await cur.fetchone()


async def open_ticket_for(db: Any, guild_id: int, user_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM modmail_tickets WHERE guild_id = ? AND user_id = ? AND status = ?",
        (guild_id, user_id, OPEN),
    )
    return await cur.fetchone()


async def any_open_ticket_for(db: Any, user_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM modmail_tickets WHERE user_id = ? AND status = ? ORDER BY id DESC LIMIT 1",
        (user_id, OPEN),
    )
    return await cur.fetchone()


async def open_tickets(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM modmail_tickets WHERE guild_id = ? AND status = ? ORDER BY id",
        (guild_id, OPEN),
    )
    return list(await cur.fetchall())


async def tickets_by_status(
    db: Any, guild_id: int, status: Any = None, limit: int = 100, *, practice: bool = False
) -> list:
    """Every ticket, or only those in one state; newest first for the web's tables."""
    sql = "SELECT * FROM modmail_tickets WHERE guild_id = ?"
    params: tuple[Any, ...] = (guild_id,)
    if not practice:
        sql += " AND practice = 0"
    if status:
        sql += " AND status = ?"
        params += (status,)
    cur = await db.conn.execute(sql + " ORDER BY id DESC LIMIT ?", (*params, int(limit)))
    return list(await cur.fetchall())


async def ticket_for_channel(db: Any, channel_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM modmail_tickets WHERE (thread_id = ? OR (thread_id IS NULL AND "
        "channel_id = ?)) AND status = ? ORDER BY id DESC LIMIT 1",
        (channel_id, channel_id, OPEN),
    )
    return await cur.fetchone()


async def tickets_in_channel(db: Any, channel_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM modmail_tickets WHERE (channel_id = ? OR thread_id = ?) AND status = ?",
        (channel_id, channel_id, OPEN),
    )
    return list(await cur.fetchall())


async def set_ticket_place(
    db: Any, ticket_id: int, channel_id: int, thread_id: int | None
) -> None:
    await db.conn.execute(
        "UPDATE modmail_tickets SET channel_id = ?, thread_id = ? WHERE id = ?",
        (channel_id, thread_id, ticket_id),
    )
    await db.conn.commit()


async def count_tickets(db: Any, guild_id: int, user_id: int) -> int:
    cur = await db.conn.execute(
        "SELECT COUNT(*) AS n FROM modmail_tickets WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    )
    return int((await cur.fetchone())["n"])


async def add_message(
    db: Any,
    ticket_id: int,
    author_id: int,
    direction: str,
    *,
    content: Any = None,
    attachments: Any = (),
    anonymous: bool = False,
    delivered: bool = True,
) -> int | None:
    cur = await db.conn.execute(
        "INSERT INTO modmail_messages(ticket_id, at, author_id, direction, anonymous, content, "
        "attachments, delivered) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ticket_id,
            now_iso(),
            author_id,
            direction,
            1 if anonymous else 0,
            clamp(content, CONTENT_LIMIT) or None,
            dump_attachments(attachments),
            1 if delivered else 0,
        ),
    )
    await db.conn.commit()
    return cur.lastrowid


async def mark_undelivered(db: Any, message_id: int | None) -> None:
    if message_id is None:
        return
    await db.conn.execute(
        "UPDATE modmail_messages SET delivered = 0 WHERE id = ?", (message_id,)
    )
    await db.conn.commit()


async def ticket_messages(db: Any, ticket_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM modmail_messages WHERE ticket_id = ? ORDER BY id", (ticket_id,)
    )
    return list(await cur.fetchall())


async def mark_closed(
    db: Any,
    ticket_id: int,
    *,
    at: str,
    by: int | None,
    reason: Any,
    log_message_id: int | None = None,
) -> None:
    await db.conn.execute(
        "UPDATE modmail_tickets SET status = ?, closed_at = ?, closed_by = ?, close_reason = ?, "
        "log_message_id = ? WHERE id = ?",
        (CLOSED, at, by, clamp(reason, 400) or None, log_message_id, ticket_id),
    )
    await db.conn.commit()


async def set_log_message(db: Any, ticket_id: int, message_id: int | None) -> None:
    if message_id is None:
        return
    await db.conn.execute(
        "UPDATE modmail_tickets SET log_message_id = ? WHERE id = ?", (message_id, ticket_id)
    )
    await db.conn.commit()


async def blocked_row(db: Any, user_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM modmail_blocks WHERE user_id = ?", (user_id,))
    return await cur.fetchone()


async def blocked_rows(db: Any) -> list[Any]:
    cur = await db.conn.execute("SELECT * FROM modmail_blocks ORDER BY at")
    return list(await cur.fetchall())


async def add_block(db: Any, user_id: int, by: int, reason: Any) -> None:
    await db.conn.execute(
        "INSERT OR REPLACE INTO modmail_blocks(user_id, by, reason, at) VALUES (?, ?, ?, ?)",
        (user_id, by, clamp(reason, 400) or None, now_iso()),
    )
    await db.conn.commit()


async def remove_block(db: Any, user_id: int) -> None:
    await db.conn.execute("DELETE FROM modmail_blocks WHERE user_id = ?", (user_id,))
    await db.conn.commit()


async def get_snippet(db: Any, name: str) -> Any:
    cur = await db.conn.execute("SELECT * FROM modmail_snippets WHERE name = ?", (name,))
    return await cur.fetchone()


async def all_snippets(db: Any) -> list[Any]:
    cur = await db.conn.execute("SELECT * FROM modmail_snippets ORDER BY name")
    return list(await cur.fetchall())


async def save_snippet(db: Any, name: str, content: str, by: int) -> None:
    await db.conn.execute(
        "INSERT OR REPLACE INTO modmail_snippets(name, content, by, at) VALUES (?, ?, ?, ?)",
        (name, content, by, now_iso()),
    )
    await db.conn.commit()


async def remove_snippet(db: Any, name: str) -> bool:
    cur = await db.conn.execute("DELETE FROM modmail_snippets WHERE name = ?", (name,))
    await db.conn.commit()
    return bool(cur.rowcount)


def user_lock(bot: Any, user_id: int) -> asyncio.Lock:
    locks = getattr(bot, LOCKS_ATTR, None)
    if locks is None:
        locks = {}
        setattr(bot, LOCKS_ATTR, locks)
    lock = locks.get(user_id)
    if lock is None:
        lock = locks[user_id] = asyncio.Lock()
    return lock


def staff_parent_id(store: Any, guild_id: int) -> Any:
    return store.get(guild_id, "modmail_staff_channel_id") or store.get(
        guild_id, "staff_channel_id"
    )


def test_channel(bot: Any) -> Any:
    guard = getattr(bot, "guard", None)
    if guard is None or not guard.test_channel_id:
        return None
    return bot.get_channel(guard.test_channel_id)


def ticket_category(bot: Any, guild: Any) -> tuple[Any, str]:
    """Where ticket channels go: the test channel's category while the guard is installed."""
    if getattr(bot, "guard", None) is not None:
        channel = test_channel(bot)
        if channel is None or getattr(channel, "category", None) is None:
            return None, "no_test_channel"
        return channel.category, "test_category"
    category_id = bot.store.get(guild.id, "modmail_category_id")
    if not category_id:
        return None, "no_category"
    category = guild.get_channel(category_id)
    if category is None:
        return None, "no_category"
    if not isinstance(category, discord.CategoryChannel) and not hasattr(category, "channels"):
        return None, "not_a_category"
    return category, "category"


def thread_parent(bot: Any, guild: Any) -> tuple[Any, str]:
    """Where ticket threads go: the test channel itself while the guard is installed."""
    if getattr(bot, "guard", None) is not None:
        channel = test_channel(bot)
        if channel is None:
            return None, "no_test_channel"
        return channel, "test_channel"
    channel_id = staff_parent_id(bot.store, guild.id)
    channel = guild.get_channel(channel_id) if channel_id else None
    if channel is None:
        return None, "no_staff_channel"
    return channel, "staff_channel"


def ticket_overwrites(guild: Any, staff_roles: Any, me: Any = None) -> dict[Any, Any]:
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


def ticket_place(bot: Any, guild: Any, ticket: Any) -> Any:
    """The channel or thread a ticket actually lives in right now, or None if it is gone."""
    if ticket["thread_id"]:
        thread = None
        finder = getattr(guild, "get_thread", None)
        if finder is not None:
            thread = finder(ticket["thread_id"])
        return thread or bot.get_channel(ticket["thread_id"])
    if not ticket["channel_id"]:
        return None
    return guild.get_channel(ticket["channel_id"])


def may_remove(bot: Any, place: Any) -> bool:
    """Deleting a channel is invisible to the guard, so the answer is the PLACE, not the mode."""
    guard = getattr(bot, "guard", None)
    if guard is None:
        return True
    channel = test_channel(bot)
    if channel is None:
        return False
    if getattr(place, "parent_id", None) is not None:
        return place.parent_id == channel.id
    return getattr(place, "category_id", None) == getattr(channel, "category_id", None)


async def resolve_place(bot: Any, guild: Any, ticket: Any) -> tuple[Any, str | None]:
    """The ticket's channel or thread, and — when there is none — whether it is gone or unknown."""
    place = ticket_place(bot, guild, ticket)
    if place is not None:
        return place, None
    target_id = ticket["thread_id"] or ticket["channel_id"]
    if not target_id:
        return None, "gone"
    fetch = getattr(guild, "fetch_channel", None)
    if fetch is None:
        return None, "gone"
    try:
        return await fetch(target_id), None
    except discord.NotFound:
        return None, "gone"
    except Exception as exc:
        log.warning("modmail: could not look up %s for ticket %s: %s", target_id, ticket["id"], exc)
        return None, "unknown"


async def speak(
    bot: Any,
    guild: Any,
    ticket: Any,
    *,
    content: Any = None,
    embed: discord.Embed | None = None,
    allowed: discord.AllowedMentions | None = None,
    view: Any = None,
) -> tuple[Any, str | None]:
    """Everything a ticket says goes through here, so the guard is asked exactly once."""
    target, missing = await resolve_place(bot, guild, ticket)
    if target is None:
        return None, missing or "gone"
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(target.id):
        target = test_channel(bot)
        if target is None:
            return None, "no_test_channel"
    if getattr(target, "archived", False):
        try:
            await target.edit(archived=False)
        except Exception as exc:
            log.info("modmail: could not unarchive %s: %s", getattr(target, "id", "?"), exc)
    extra = {} if view is None else {"view": view}
    try:
        message = await target.send(
            content, embed=embed, allowed_mentions=allowed or mentions(), **extra
        )
    except Exception as exc:
        log.warning("modmail: could not write in ticket %s: %s", ticket["id"], exc)
        return None, f"{type(exc).__name__}: {exc}"
    return message, None


async def deliver_dm(
    user: Any, content: Any = None, embed: discord.Embed | None = None
) -> str | None:
    """The reason the DM did not arrive, or None when it did."""
    send = getattr(user, "send", None)
    if send is None:
        return "no_user"
    try:
        await send(content, embed=embed, allowed_mentions=mentions())
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"
    return None


async def ticket_dm(
    bot: Any, guild: Any, ticket: Any, content: Any = None, embed: discord.Embed | None = None
) -> str | None:
    """A practice ticket DMs nobody, and a DM that was never sent is not one that failed."""
    if is_practice(ticket):
        return None
    user = bot.get_user(ticket["user_id"]) or guild.get_member(ticket["user_id"])
    if user is None:
        return "member_not_visible"
    return await deliver_dm(user, content, embed=embed)


async def react(bot: Any, message: Any, emoji: str) -> None:
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(message.channel.id):
        return
    try:
        await message.add_reaction(emoji)
    except Exception as exc:
        log.info("modmail: could not react to %s: %s", getattr(message, "id", "?"), exc)


async def set_card_message(db: Any, ticket_id: int, message_id: int | None) -> None:
    await db.conn.execute(
        "UPDATE modmail_tickets SET card_message_id = ? WHERE id = ?", (message_id, ticket_id)
    )
    await db.conn.commit()


def card_clock(bot: Any) -> dict[str, dict[int, Any]]:
    """Per-ticket debounce state, kept on the BOT so every door coalesces onto one refresh."""
    clock = getattr(bot, CARDS_ATTR, None)
    if clock is None:
        clock = {"tasks": {}, "last": {}, "dirty": set()}
        setattr(bot, CARDS_ATTR, clock)
    return clock


def card_dirty(clock: Any) -> set[int]:
    return clock.setdefault("dirty", set())


def card_wait(clock: Any, ticket_id: int, now: float) -> float:
    """Coalesce a burst, and never cycle one ticket's card faster than the floor allows."""
    since = now - clock["last"].get(ticket_id, now - CARD_MIN_GAP_SECONDS)
    return max(CARD_DEBOUNCE_SECONDS, CARD_MIN_GAP_SECONDS - since)


async def bump_card(bot: Any, guild: Any, ticket: Any) -> None:
    """Every write into an open ticket asks the card to move; the clock decides when."""
    if ticket is None or ticket["status"] != OPEN:
        return
    clock = card_clock(bot)
    ticket_id = int(ticket["id"])
    if ticket_id in clock["tasks"]:
        card_dirty(clock).add(ticket_id)
        return
    clock["tasks"][ticket_id] = asyncio.ensure_future(_card_later(bot, guild, ticket_id))


async def _card_later(bot: Any, guild: Any, ticket_id: int) -> None:
    """A write that lands while the card is in flight marks it dirty and goes round again."""
    clock = card_clock(bot)
    dirty = card_dirty(clock)
    try:
        while True:
            await asyncio.sleep(card_wait(clock, ticket_id, monotonic()))
            dirty.discard(ticket_id)
            await refresh_card(bot, guild, ticket_id)
            if ticket_id not in dirty:
                return
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        log.warning("modmail: the card for ticket %s could not be moved: %s", ticket_id, exc)
        await card_move_failed(bot, guild, ticket_id, exc)
    finally:
        dirty.discard(ticket_id)
        clock["tasks"].pop(ticket_id, None)


async def card_move_failed(bot: Any, guild: Any, ticket_id: int, exc: BaseException) -> None:
    """Nothing awaits this task, so a silent failure would read exactly like a success."""
    try:
        await log_action(
            bot,
            guild,
            "modmail.card_failed",
            details={
                "ticket_id": ticket_id,
                "reason": clamp(f"{type(exc).__name__}: {exc}", CARD_REASON_LIMIT),
            },
        )
    except Exception as why:
        log.warning("modmail: the failed card for ticket %s went unlogged: %s", ticket_id, why)


async def settle_cards(bot: Any) -> None:
    """Wait out every pending card move, so a caller can read the settled state."""
    for task in list(card_clock(bot)["tasks"].values()):
        with suppress(asyncio.CancelledError, Exception):
            await task


def cancel_cards(bot: Any) -> None:
    clock = card_clock(bot)
    for task in list(clock["tasks"].values()):
        task.cancel()
    clock["tasks"].clear()
    card_dirty(clock).clear()


async def refresh_card(bot: Any, guild: Any, ticket_id: int) -> Any:
    """The debounce and the reconciler both land here, so the ticket's own lock keeps them apart."""
    row = await get_ticket(bot.db, ticket_id)
    if row is None or row["status"] != OPEN:
        return None
    async with user_lock(bot, row["user_id"]):
        return await post_card(bot, guild, ticket_id)


def ticket_member(bot: Any, guild: Any, ticket: Any) -> Any:
    return guild.get_member(ticket["user_id"]) or bot.get_user(ticket["user_id"])


async def card_embed(bot: Any, guild: Any, ticket: Any) -> discord.Embed:
    """One embed for the sticky card and for the panel's copy of it — never two shapes."""
    rows = await ticket_messages(bot.db, ticket["id"])
    blocked = await blocked_row(bot.db, ticket["user_id"]) is not None
    return ticket_card_embed(
        ticket,
        count_directions(rows),
        label=getattr(ticket_member(bot, guild, ticket), "display_name", None),
        blocked=blocked,
        not_reached=last_reply_missed(rows),
    )


async def post_card(bot: Any, guild: Any, ticket_id: int) -> Any:
    """Post the card at the bottom, write its id, and only then delete the one it replaced."""
    fresh = await get_ticket(bot.db, ticket_id)
    if fresh is None or fresh["status"] != OPEN:
        return None
    old_id = field_of(fresh, "card_message_id")
    embed = await card_embed(bot, guild, fresh)
    message, why_not = await speak(bot, guild, fresh, embed=embed, view=card_view(fresh))
    if message is None:
        await log_action(
            bot,
            guild,
            "modmail.card_failed",
            details={"ticket_id": ticket_id, "reason": why_not or "gone"},
        )
        return None
    card_clock(bot)["last"][ticket_id] = monotonic()
    await set_card_message(bot.db, ticket_id, message.id)
    if old_id and int(old_id) != int(message.id):
        await drop_old_card(bot, guild, fresh, message.channel, int(old_id))
    return message


async def drop_old_card(bot: Any, guild: Any, ticket: Any, channel: Any, old_id: int) -> None:
    """Deleting a MESSAGE is a side effect `guard.py` never sees, so this one asks by hand."""
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel.id):
        await log_action(
            bot,
            guild,
            "modmail.would_replace_card",
            details={"ticket_id": ticket["id"], "message_id": old_id, "channel_id": channel.id},
        )
        return
    try:
        await channel.get_partial_message(old_id).delete()
    except discord.NotFound:
        return
    except Exception as exc:
        await log_action(
            bot,
            guild,
            "modmail.card_failed",
            details={"ticket_id": ticket["id"], "reason": f"{type(exc).__name__}: {exc}"},
        )


async def card_is_there(bot: Any, guild: Any, ticket: Any, card_id: int) -> bool:
    """A card a staffer deleted by hand reads as gone, and the reconciler posts another."""
    place, _ = await resolve_place(bot, guild, ticket)
    guard = getattr(bot, "guard", None)
    if place is not None and guard is not None and not guard.allows_channel(place.id):
        place = test_channel(bot)
    if place is None:
        return False
    try:
        await place.fetch_message(card_id)
    except discord.NotFound:
        return False
    except Exception as exc:
        log.info("modmail: could not look up the card %s: %s", card_id, exc)
        return True
    return True


async def drop_card(bot: Any, guild: Any, ticket: Any) -> None:
    """Closing a ticket takes its card with it, so the transcript carries one and not two."""
    old_id = field_of(ticket, "card_message_id")
    if not old_id:
        return
    place, _ = await resolve_place(bot, guild, ticket)
    guard = getattr(bot, "guard", None)
    if place is not None and guard is not None and not guard.allows_channel(place.id):
        place = test_channel(bot)
    await set_card_message(bot.db, ticket["id"], None)
    if place is not None:
        await drop_old_card(bot, guild, ticket, place, int(old_id))


async def add_note(
    bot: Any,
    guild: Any,
    ticket: Any,
    author: Any,
    text: Any,
    *,
    attachments: Any = (),
    echo: bool = True,
    via: str = VIA_DISCORD,
    source: str = SOURCE_COMMAND,
) -> Outcome:
    """One path for every private note, whether it was typed, commanded or pressed."""
    await add_message(
        bot.db, ticket["id"], author.id, NOTE, content=text, attachments=attachments
    )
    why_not = None
    if echo:
        embed = relay_embed(
            NOTE,
            author_name=getattr(author, "display_name", str(author)),
            author_id=author.id,
            content=text,
            attachments=attachments,
        )
        _, why_not = await speak(bot, guild, ticket, embed=embed)
    await log_action(
        bot,
        guild,
        kind_via("modmail.note", via),
        actor=author,
        target=ticket["user_id"],
        details={"ticket_id": ticket["id"], "source": source, "via": via},
    )
    await bump_card(bot, guild, ticket)
    said = NOTE_SAVED.format(ticket_id=ticket["id"])
    return Outcome(True, said if why_not is None else said + RELAY_FAILED_SAID, value=ticket["id"])


async def send_reply(
    bot: Any,
    guild: Any,
    ticket: Any,
    author: Any,
    content: Any,
    *,
    anonymous: bool = False,
    attachments: Any = (),
    echo: bool = True,
    via: str = VIA_DISCORD,
    source: str = SOURCE_COMMAND,
) -> str | None:
    """One path for every staff reply, whether it came from a message, a command or the site."""
    embed = relay_embed(
        OUT,
        author_name=getattr(author, "display_name", str(author)),
        author_id=author.id,
        content=content,
        attachments=attachments,
        anonymous=anonymous,
        colour=None if anonymous else getattr(getattr(author, "colour", None), "value", None),
        icon_url=None
        if anonymous
        else getattr(getattr(author, "display_avatar", None), "url", None),
    )
    row_id = await add_message(
        bot.db,
        ticket["id"],
        author.id,
        OUT,
        content=content,
        attachments=attachments,
        anonymous=anonymous,
    )
    why_not = await ticket_dm(bot, guild, ticket, embed=embed)
    await log_action(
        bot,
        guild,
        kind_via("modmail.reply", via),
        actor=author,
        target=ticket["user_id"],
        details={
            "ticket_id": ticket["id"],
            "anonymous": anonymous,
            "delivered": why_not is None,
            "practice": is_practice(ticket),
            "source": source,
            "via": via,
        },
    )
    if why_not is not None:
        await mark_undelivered(bot.db, row_id)
        await log_action(
            bot,
            guild,
            "modmail.dm_failed",
            actor=author,
            target=ticket["user_id"],
            details={"ticket_id": ticket["id"], "reason": why_not},
        )
        await speak(
            bot,
            guild,
            ticket,
            content=f"⚠️ Black Bloc could not DM the member — `{clamp(why_not, 200)}`",
            embed=embed,
        )
        await bump_card(bot, guild, ticket)
        return why_not
    if echo:
        await speak(bot, guild, ticket, embed=embed)
    await bump_card(bot, guild, ticket)
    return None


async def close_ticket(
    bot: Any,
    guild: Any,
    ticket: Any,
    *,
    by: Any = None,
    reason: Any = None,
    silent: bool = False,
    via: str = VIA_DISCORD,
) -> tuple[bool, str | None]:
    """Transcript first, then the record, then the member, then the channel."""
    async with user_lock(bot, ticket["user_id"]):
        fresh = await get_ticket(bot.db, ticket["id"])
        if fresh is None or fresh["status"] != OPEN:
            return False, None
        await drop_card(bot, guild, fresh)
        rows = await ticket_messages(bot.db, fresh["id"])
        closed_at = now_iso()
        await mark_closed(
            bot.db, fresh["id"], at=closed_at, by=getattr(by, "id", by), reason=reason
        )
        message_id, why_not = await post_transcript(
            bot, guild, fresh, rows, by=by, reason=reason, closed_at=closed_at
        )
        await set_log_message(bot.db, fresh["id"], message_id)
        await log_action(
            bot,
            guild,
            kind_via("modmail.closed", via),
            actor=by,
            target=fresh["user_id"],
            reason=clamp(reason, 400) or None,
            details={
                "ticket_id": fresh["id"],
                "messages": len(rows),
                "practice": is_practice(fresh),
                "via": via,
            },
        )
        if not silent:
            await ticket_dm(bot, guild, fresh, closing_dm(guild.name, reason))
        if why_not is None:
            await remove_place(bot, guild, fresh)
        else:
            await log_action(
                bot,
                guild,
                "modmail.place_kept",
                details={"ticket_id": fresh["id"], "reason": why_not},
            )
        if is_practice(fresh):
            await disown_place(bot, guild, fresh)
        return True, why_not


async def post_transcript(
    bot: Any, guild: Any, ticket: Any, rows: Any, *, by: Any, reason: Any, closed_at: str
) -> tuple[int | None, str | None]:
    member = guild.get_member(ticket["user_id"])
    label = getattr(member, "display_name", None) or str(ticket["user_id"])
    details = {"ticket_id": ticket["id"]}
    channel_id = bot.store.get(guild.id, "modmail_log_channel_id")
    channel = (
        (bot.get_channel(channel_id) or guild.get_channel(channel_id)) if channel_id else None
    )
    if channel is None:
        await log_action(
            bot,
            guild,
            "modmail.transcript_failed",
            details=details | {"reason": "no_log_channel"},
        )
        return None, "no_log_channel"
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel.id):
        await log_action(
            bot,
            guild,
            "modmail.would_post_transcript",
            details=details | {"reason": "test_mode", "channel_id": channel.id},
        )
        return None, "test_mode"
    practice = is_practice(ticket)
    text = transcript_text(
        rows,
        ticket_id=ticket["id"],
        user_id=ticket["user_id"],
        user_label=label,
        guild_name=guild.name,
        mode=ticket["mode"],
        opened_at=ticket["opened_at"],
        closed_at=closed_at,
        closed_by=getattr(by, "id", by),
        reason=reason,
        practice=practice,
    )
    embed = transcript_embed(
        ticket_id=ticket["id"],
        user_id=ticket["user_id"],
        user_label=label,
        mode=ticket["mode"],
        counts=count_directions(rows),
        opened_at=ticket["opened_at"],
        closed_at=closed_at,
        closed_by=getattr(by, "id", by),
        reason=reason,
        practice=practice,
    )
    file = discord.File(
        io.BytesIO(text.encode("utf-8")),
        filename=transcript_filename(ticket["id"], practice=practice),
    )
    try:
        message = await channel.send(embed=embed, file=file, allowed_mentions=mentions())
    except Exception as exc:
        log.warning("modmail: could not post the transcript for %s: %s", ticket["id"], exc)
        await log_action(
            bot,
            guild,
            "modmail.transcript_failed",
            details=details | {"reason": f"{type(exc).__name__}: {exc}"},
        )
        return None, f"{type(exc).__name__}: {exc}"
    await log_action(
        bot,
        guild,
        "modmail.transcript",
        target=ticket["user_id"],
        details=details | {"channel_id": channel.id},
    )
    return message.id, None


async def remove_place(bot: Any, guild: Any, ticket: Any) -> None:
    place, _ = await resolve_place(bot, guild, ticket)
    if place is None:
        return
    if not may_remove(bot, place):
        await log_action(
            bot,
            guild,
            "modmail.would_remove_place",
            details={"ticket_id": ticket["id"], "channel_id": place.id},
        )
        return
    try:
        if ticket["thread_id"]:
            await place.edit(archived=True, locked=True)
        else:
            await place.delete(reason=f"Black Bloc modmail ticket {ticket['id']} closed")
    except Exception as exc:
        log.warning("modmail: could not tidy away %s: %s", place.id, exc)
        await log_action(
            bot,
            guild,
            "modmail.remove_place_failed",
            details={
                "ticket_id": ticket["id"],
                "channel_id": place.id,
                "reason": f"{type(exc).__name__}: {exc}",
            },
        )


async def resolve_ticket(bot: Any, guild: Any, channel_id: Any, given: Any) -> tuple[Any, str]:
    """The ticket a staff command means: the one named, the one here, or the only one open."""
    if given:
        digits = str(given).strip().lstrip("#")
        if not digits.isdecimal():
            return None, NOT_A_TICKET_ID.format(given=clamp(given, 40))
        row = await get_ticket(bot.db, int(digits))
        if row is None or row["guild_id"] != guild.id:
            return None, NO_SUCH_TICKET.format(ticket_id=int(digits))
        if row["status"] != OPEN:
            return None, TICKET_CLOSED.format(ticket_id=row["id"])
        return row, ""
    here = await ticket_for_channel(bot.db, channel_id) if channel_id else None
    if here is not None:
        return here, ""
    rows = await open_tickets(bot.db, guild.id)
    if len(rows) == 1:
        return rows[0], ""
    if not rows:
        return None, NO_TICKET_HERE
    ids = ", ".join(f"#{row['id']}" for row in rows)
    return None, MANY_OPEN.format(count=len(rows), ids=ids)


async def disown_place(bot: Any, guild: Any, ticket: Any) -> None:
    """The practice thread is claimed for the life of the practice and no longer."""
    guard = getattr(bot, "guard", None)
    if guard is None:
        return
    place, _ = await resolve_place(bot, guild, ticket)
    if place is not None:
        guard.disown_channel(place)


def practice_parent(bot: Any, guild: Any) -> tuple[Any, str]:
    """Checklist 1: making a thread is invisible to the guard, so it is asked by hand first."""
    parent, where = thread_parent(bot, guild)
    if parent is None:
        return None, where
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(parent.id):
        return None, "no_test_channel"
    return parent, where


async def create_practice_ticket(db: Any, guild_id: int, user_id: int) -> int | None:
    cur = await db.conn.execute(
        "INSERT INTO modmail_tickets(guild_id, user_id, mode, channel_id, status, opened_at, "
        "practice, source, opened_by) VALUES (?, ?, ?, 0, ?, ?, 1, ?, ?)",
        (guild_id, user_id, THREAD_MODE, OPEN, now_iso(), SOURCE_PRACTICE, user_id),
    )
    await db.conn.commit()
    return cur.lastrowid


async def open_practice(bot: Any, guild: Any, actor: Any, *, via: str = VIA_DISCORD) -> Outcome:
    """The instrument the owner decides `modmail_reply_style` with: a real ticket, no member."""
    if not bot.store.staff_roles(guild):
        return refusal(NO_STAFF_TO_PRACTISE, "no_staff_roles", 409)
    if await open_ticket_for(bot.db, guild.id, actor.id) is not None:
        return refusal(ALREADY_PRACTISING, "already_open", 409)
    parent, where = practice_parent(bot, guild)
    if parent is None:
        return refusal(
            NO_TEST_CHANNEL if where == "no_test_channel" else NO_STAFF_CHANNEL, where, 409
        )
    try:
        ticket_id = await create_practice_ticket(bot.db, guild.id, actor.id)
    except sqlite3.IntegrityError:
        return refusal(ALREADY_PRACTISING, "already_open", 409)
    label = getattr(actor, "display_name", getattr(actor, "name", actor))
    try:
        thread = await parent.create_thread(
            name=thread_name(f"practice · {label}", ticket_id),
            type=discord.ChannelType.private_thread,
            invitable=False,
            auto_archive_duration=AUTO_ARCHIVE_MINUTES,
            reason=f"Black Bloc modmail practice ticket {ticket_id}",
        )
    except Exception as exc:
        await abandon_practice(bot, guild, actor, ticket_id, exc)
        return refusal(PRACTICE_FAILED, "practice_failed", 500)
    guard = getattr(bot, "guard", None)
    if guard is not None:
        guard.own_channel(thread)
    await set_ticket_place(
        bot.db, ticket_id, getattr(thread, "parent_id", parent.id), thread.id
    )
    ticket = await get_ticket(bot.db, ticket_id)
    await log_action(
        bot,
        guild,
        kind_via("modmail.opened", via),
        actor=actor,
        target=actor,
        details={
            "ticket_id": ticket_id,
            "mode": THREAD_MODE,
            "channel_id": thread.id,
            "practice": True,
            "via": via,
        },
    )
    await post_practice_header(bot, guild, ticket, actor)
    await refresh_card(bot, guild, ticket_id)
    return Outcome(
        True, PRACTICE_OPENED.format(ticket_id=ticket_id, where=thread.id), value=ticket_id
    )


async def abandon_practice(bot: Any, guild: Any, actor: Any, ticket_id: int, why: Any) -> None:
    await bot.db.conn.execute(
        "UPDATE modmail_tickets SET status = 'closed', closed_at = ?, close_reason = ? "
        "WHERE id = ?",
        (now_iso(), f"practice_never_got_a_place: {why}", ticket_id),
    )
    await bot.db.conn.commit()
    await log_action(
        bot,
        guild,
        "modmail.open_failed",
        target=actor,
        details={"ticket_id": ticket_id, "practice": True, "reason": str(why)},
    )


async def post_practice_header(bot: Any, guild: Any, ticket: Any, actor: Any) -> None:
    member = guild.get_member(actor.id)
    embed = header_embed(
        ticket_id=ticket["id"],
        user_id=actor.id,
        user_label=getattr(actor, "display_name", str(actor)),
        mode=THREAD_MODE,
        created_at=getattr(actor, "created_at", None),
        joined_at=getattr(member, "joined_at", None),
        roles=[r for r in getattr(member, "roles", ()) if getattr(r, "id", 0) != guild.id],
        prior_tickets=max(await count_tickets(bot.db, guild.id, actor.id) - 1, 0),
    )
    await speak(bot, guild, ticket, content=PRACTICE_HEADER, embed=embed)


async def practice_message(bot: Any, guild: Any, ticket: Any, actor: Any, text: Any) -> Outcome:
    """The three calls `_relay_inbound` makes, with the DM listener replaced by a modal."""
    if not is_practice(ticket):
        return refusal(NOT_PRACTICE, "not_practice", 409)
    if not str(text or "").strip():
        return refusal(NOTHING_TO_SAY, "nothing_to_say", 400)
    body = str(text).strip()
    await add_message(bot.db, ticket["id"], ticket["user_id"], IN, content=body)
    embed = relay_embed(
        IN,
        author_name=getattr(actor, "display_name", str(actor)),
        author_id=ticket["user_id"],
        content=body,
        icon_url=getattr(getattr(actor, "display_avatar", None), "url", None),
    )
    _, why_not = await speak(bot, guild, ticket, embed=embed)
    await bump_card(bot, guild, ticket)
    return Outcome(
        True, PRACTICE_SAID if why_not is None else PRACTICE_SAID + RELAY_FAILED_SAID
    )


async def reply_body(db: Any, text: Any, snippet: Any) -> tuple[Any, str | None]:
    """The body `/reply text: snippet:` builds, so the card's modal builds the same one."""
    if snippet:
        row = await get_snippet(db, str(snippet).strip().lower())
        if row is None:
            return None, NO_SNIPPET.format(name=clamp(snippet, 40))
        return (row["content"] if not text else f"{row['content']}\n\n{text}"), None
    if not str(text or "").strip():
        return None, NOTHING_TO_SEND
    return str(text), None


def who_said(user: Any, user_id: int) -> str:
    return getattr(user, "display_name", None) or f"<@{int(user_id)}>"


async def block_member(
    bot: Any, guild: Any, actor: Any, user: Any, reason: Any = None, *, via: str = VIA_DISCORD
) -> Outcome:
    """One block, one log row, whichever door asked for it."""
    user_id = int(getattr(user, "id", user))
    who = who_said(user, user_id)
    if await blocked_row(bot.db, user_id) is not None:
        return refusal(ALREADY_BLOCKED.format(who=who), "already_blocked", 409)
    await add_block(bot.db, user_id, getattr(actor, "id", actor), reason)
    await log_action(
        bot,
        guild,
        kind_via("modmail.blocked", via),
        actor=actor,
        target=user,
        reason=clamp(reason, 400) or None,
        details={"user_id": user_id, "via": via},
    )
    return Outcome(True, BLOCKED_SAID.format(who=who), value=user_id)


async def unblock_member(
    bot: Any, guild: Any, actor: Any, user: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    user_id = int(getattr(user, "id", user))
    who = who_said(user, user_id)
    if await blocked_row(bot.db, user_id) is None:
        return refusal(NOT_BLOCKED.format(who=who), "not_blocked", 404)
    await remove_block(bot.db, user_id)
    await log_action(
        bot,
        guild,
        kind_via("modmail.unblocked", via),
        actor=actor,
        target=user,
        details={"user_id": user_id, "via": via},
    )
    return Outcome(True, UNBLOCKED_SAID.format(who=who), value=user_id)


async def put_snippet(
    bot: Any,
    guild: Any,
    actor: Any,
    name: Any,
    content: Any,
    *,
    overwrite: bool = False,
    via: str = VIA_DISCORD,
) -> Outcome:
    key = str(name or "").strip().lower()
    if not valid_snippet_name(key):
        return refusal(BAD_SNIPPET_NAME.format(given=clamp(name, 40)), "bad_name", 400)
    if not overwrite and await get_snippet(bot.db, key) is not None:
        return refusal(SNIPPET_EXISTS.format(name=key), "snippet_exists", 409)
    await save_snippet(bot.db, key, clamp(content, CONTENT_LIMIT), getattr(actor, "id", actor))
    await log_action(
        bot,
        guild,
        kind_via("modmail.snippet_saved", via),
        actor=actor,
        details={"name": key, "via": via},
    )
    return Outcome(True, SNIPPET_SAVED.format(name=key), value=key)


async def drop_snippet(
    bot: Any, guild: Any, actor: Any, name: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    key = str(name or "").strip().lower()
    if not await remove_snippet(bot.db, key):
        return refusal(NO_SUCH_SNIPPET.format(name=clamp(name, 40)), "no_such_snippet", 404)
    await log_action(
        bot,
        guild,
        kind_via("modmail.snippet_removed", via),
        actor=actor,
        details={"name": key, "via": via},
    )
    return Outcome(True, SNIPPET_GONE.format(name=key), value=key)


async def settings_written(
    bot: Any, guild: Any, actor: Any, changed: dict[str, Any], via: str
) -> None:
    await log_action(
        bot,
        guild,
        kind_via("modmail.settings", via),
        actor=actor,
        details=changed | {"via": via},
    )


async def point_at(
    bot: Any, guild: Any, actor: Any, key: str, value: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """One of the three places modmail is pointed at, set and recorded once."""
    stored = await bot.store.set(guild.id, key, value, by=getattr(actor, "id", actor))
    await settings_written(bot, guild, actor, {key: stored}, via)
    return Outcome(True, POINTED.format(key=key, place=f"<#{int(stored)}>"), value=stored)


async def forget_place(
    bot: Any, guild: Any, actor: Any, key: str, *, via: str = VIA_DISCORD
) -> Outcome:
    await bot.store.clear(guild.id, key)
    await log_action(
        bot,
        guild,
        kind_via("modmail.forgotten", via),
        actor=actor,
        details={"key": key, "via": via},
    )
    return Outcome(True, FORGOTTEN.format(key=key), value=key)


async def set_mode(
    bot: Any, guild: Any, actor: Any, mode: str, *, via: str = VIA_DISCORD
) -> Outcome:
    await bot.store.set(guild.id, "modmail_mode", mode, by=getattr(actor, "id", actor))
    await settings_written(bot, guild, actor, {"modmail_mode": mode}, via)
    said = MODE_SET.format(
        what=modes_sentence(mode), count=len(await open_tickets(bot.db, guild.id))
    )
    return Outcome(True, said, value=mode)


async def set_enabled(
    bot: Any, guild: Any, actor: Any, value: bool, *, via: str = VIA_DISCORD
) -> Outcome:
    wanted = bool(value)
    await bot.store.set(guild.id, "modmail_enabled", wanted, by=getattr(actor, "id", actor))
    await settings_written(bot, guild, actor, {"modmail_enabled": wanted}, via)
    return Outcome(True, ANSWERING if wanted else NOT_ANSWERING, value=wanted)


async def set_reply_style(
    bot: Any, guild: Any, actor: Any, style: str, *, via: str = VIA_DISCORD
) -> Outcome:
    """`buttons` turns the typed relay off; it never turns a second relay on."""
    await bot.store.set(guild.id, REPLY_STYLE_KEY, style, by=getattr(actor, "id", actor))
    await settings_written(bot, guild, actor, {REPLY_STYLE_KEY: style}, via)
    return Outcome(True, reply_style_sentence(style), value=style)


async def make_place(
    bot: Any, guild: Any, user: Any, ticket_id: int, mode: str, *, subject: Any = None
) -> tuple[Any, str | None]:
    """Where a new ticket lives: a channel in the category, or a private thread."""
    if not bot.store.staff_roles(guild):
        return None, "no_staff_roles"
    if mode == THREAD_MODE:
        parent, where = thread_parent(bot, guild)
        if parent is None:
            return None, where
        try:
            return (
                await parent.create_thread(
                    name=thread_name(getattr(user, "display_name", user.name), ticket_id),
                    type=discord.ChannelType.private_thread,
                    invitable=False,
                    auto_archive_duration=AUTO_ARCHIVE_MINUTES,
                    reason=f"Black Bloc modmail ticket {ticket_id}",
                ),
                None,
            )
        except discord.HTTPException as exc:
            return None, f"{type(exc).__name__}: {exc}"
    category, where = ticket_category(bot, guild)
    if category is None:
        return None, where
    staff = bot.store.staff_roles(guild)
    try:
        return (
            await guild.create_text_channel(
                ticket_channel_name(getattr(user, "name", user), ticket_id),
                category=category,
                topic=ticket_topic(user.id, ticket_id, subject),
                overwrites=ticket_overwrites(guild, staff, getattr(guild, "me", None)),
                reason=f"Black Bloc modmail ticket {ticket_id}",
            ),
            None,
        )
    except discord.HTTPException as exc:
        return None, f"{type(exc).__name__}: {exc}"


async def abandon_ticket(bot: Any, guild: Any, user: Any, ticket_id: int, why_not: Any) -> None:
    await bot.db.conn.execute(
        "UPDATE modmail_tickets SET status = 'closed', closed_at = ?, close_reason = ? "
        "WHERE id = ?",
        (now_iso(), f"never_got_a_place: {why_not}", ticket_id),
    )
    await bot.db.conn.commit()
    log.warning("modmail: ticket %s got no channel — %s", ticket_id, why_not)
    await log_action(
        bot,
        guild,
        "modmail.open_failed",
        target=user,
        details={"ticket_id": ticket_id, "reason": str(why_not)},
    )


async def post_header(bot: Any, guild: Any, ticket: Any, user: Any, mode: str) -> None:
    member = guild.get_member(user.id)
    prior = max(await count_tickets(bot.db, guild.id, user.id) - 1, 0)
    embed = header_embed(
        ticket_id=ticket["id"],
        user_id=user.id,
        user_label=getattr(user, "display_name", str(user)),
        mode=mode,
        created_at=getattr(user, "created_at", None),
        joined_at=getattr(member, "joined_at", None),
        roles=[r for r in getattr(member, "roles", ()) if getattr(r, "id", 0) != guild.id],
        prior_tickets=prior,
    )
    role_ids = [role.id for role in bot.store.staff_roles(guild)]
    if mode == THREAD_MODE:
        await speak(
            bot,
            guild,
            ticket,
            content=thread_invite(
                role_ids, ticket["id"], getattr(user, "display_name", str(user))
            ),
            embed=embed,
            allowed=mentions(role_ids),
        )
        return
    await speak(bot, guild, ticket, embed=embed)


async def open_or_find(
    bot: Any,
    guild: Any,
    user: Any,
    *,
    source: str = SOURCE_DM,
    opened_by: Any = None,
    subject: Any = None,
    via: str = VIA_DISCORD,
) -> tuple[Any, bool]:
    """One open ticket per member, made the same way whichever door asked for it."""
    existing = await open_ticket_for(bot.db, guild.id, user.id)
    if existing is not None:
        return existing, False
    mode = bot.store.get(guild.id, "modmail_mode")
    try:
        ticket_id = await create_ticket(
            bot.db, guild.id, user.id, mode, source=source, opened_by=opened_by
        )
    except sqlite3.IntegrityError:
        return await open_ticket_for(bot.db, guild.id, user.id), False
    place, why_not = await make_place(bot, guild, user, ticket_id, mode, subject=subject)
    if place is None:
        await abandon_ticket(bot, guild, user, ticket_id, why_not)
        return None, False
    await set_ticket_place(
        bot.db,
        ticket_id,
        place.id if mode == CHANNEL_MODE else getattr(place, "parent_id", place.id),
        place.id if mode == THREAD_MODE else None,
    )
    ticket = await get_ticket(bot.db, ticket_id)
    await log_action(
        bot,
        guild,
        kind_via(
            "modmail.opened_by_staff" if source == SOURCE_STAFF else "modmail.opened", via
        ),
        actor=opened_by,
        target=user,
        details={
            "ticket_id": ticket_id,
            "mode": mode,
            "channel_id": place.id,
            "source": source,
            "via": via,
        },
    )
    await post_header(bot, guild, ticket, user, mode)
    return ticket, True


async def record_inbound(
    bot: Any, guild: Any, ticket: Any, author: Any, content: Any, attachments: Any = ()
) -> str | None:
    """The member's words into the ticket: one row, one embed, one card move."""
    await add_message(
        bot.db, ticket["id"], author.id, IN, content=content, attachments=attachments
    )
    embed = relay_embed(
        IN,
        author_name=getattr(author, "display_name", str(author)),
        author_id=author.id,
        content=content,
        attachments=attachments,
        icon_url=getattr(getattr(author, "display_avatar", None), "url", None),
    )
    _, why_not = await speak(bot, guild, ticket, embed=embed)
    if why_not is not None:
        await log_action(
            bot,
            guild,
            "modmail.relay_failed",
            target=author,
            details={"ticket_id": ticket["id"], "reason": why_not},
        )
    await bump_card(bot, guild, ticket)
    return why_not


def ticket_place_id(ticket: Any) -> int:
    return int(ticket["thread_id"] or ticket["channel_id"] or 0)


def open_with_on(store: Any, guild_id: int) -> bool:
    """The one reader of the hide toggle, so the button, the picker and the modal agree."""
    return bool(store.get(guild_id, MODMAIL_OPEN_WITH_BUTTON))


async def refuse_open(
    bot: Any,
    guild: Any,
    user: Any,
    reason: str,
    said: str,
    *,
    status: int = 409,
    actor: Any = None,
    via: str = VIA_DISCORD,
) -> Outcome:
    """A door that will not open says why, in words, and leaves one quiet row saying so."""
    await log_action(
        bot,
        guild,
        kind_via("modmail.open_refused", via),
        actor=actor,
        target=user,
        details={"reason": reason, "user_id": getattr(user, "id", user), "via": via},
    )
    return refusal(said, reason, status)


async def open_a_ticket(
    bot: Any,
    guild: Any,
    user: Any,
    *,
    source: str,
    subject: Any = None,
    text: Any = None,
    actor: Any = None,
    via: str = VIA_DISCORD,
) -> Outcome:
    """The command, the posted button and the staff door, all on the DM path's own rails."""
    staff_door = source == SOURCE_STAFF
    if staff_door and not open_with_on(bot.store, guild.id):
        return await refuse_open(
            bot, guild, user, "open_with_off", OPEN_WITH_OFF, actor=actor, via=via
        )
    if getattr(user, "bot", False):
        return await refuse_open(
            bot, guild, user, "a_bot", A_BOT_SAID, status=400, actor=actor, via=via
        )
    if not bot.store.get(guild.id, "modmail_enabled"):
        said = STAFF_DISABLED_SAID if staff_door else DISABLED_DM.format(guild=guild.name)
        return await refuse_open(bot, guild, user, "disabled", said, actor=actor, via=via)
    blocked = await blocked_row(bot.db, user.id)
    if blocked is not None:
        said = (
            STAFF_BLOCKED_SAID.format(who=who_said(user, user.id))
            if staff_door
            else BLOCKED_DM.format(guild=guild.name)
        )
        return await refuse_open(bot, guild, user, "blocked", said, actor=actor, via=via)
    async with user_lock(bot, user.id):
        existing = await open_ticket_for(bot.db, guild.id, user.id)
        if existing is not None:
            said = (
                STAFF_ALREADY_OPEN.format(
                    who=who_said(user, user.id), where=ticket_place_id(existing)
                )
                if staff_door
                else ALREADY_OPEN_SAID
            )
            return await refuse_open(
                bot, guild, user, "already_open", said, actor=actor, via=via
            )
        ticket, _ = await open_or_find(
            bot,
            guild,
            user,
            source=source,
            opened_by=getattr(actor, "id", actor),
            subject=subject,
            via=via,
        )
        if ticket is None:
            return await refuse_open(
                bot, guild, user, "cannot_open", CANNOT_OPEN_SAID, status=500, actor=actor,
                via=via,
            )
        body = first_message(subject, text)
        if staff_door:
            why_not = await send_reply(
                bot, guild, ticket, actor, body, via=via, source=SOURCE_COMMAND
            )
            said = STAFF_OPENED.format(
                who=who_said(user, user.id),
                ticket_id=ticket["id"],
                where=ticket_place_id(ticket),
            )
            return Outcome(
                True,
                said if why_not is None else said + STAFF_NOT_REACHED,
                value=ticket["id"],
            )
        await record_inbound(bot, guild, ticket, user, body)
        why_not = await deliver_dm(user, opening_dm(guild.name))
        said = TICKET_OPENED_SAID.format(ticket_id=ticket["id"])
        return Outcome(
            True, said if why_not is None else said + DMS_ARE_SHUT, value=ticket["id"]
        )


def ticket_panel_custom_id(guild_id: Any) -> str:
    return f"modmail:ticket:{int(guild_id)}"


def ticket_panel_view(guild_id: Any) -> discord.ui.View:
    """The posted button belongs to the room, so it outlives the process that posted it."""
    view = discord.ui.View(timeout=None)
    view.add_item(TicketButton(guild_id))
    return view


def panel_where(bot: Any, guild: Any) -> tuple[Any, int | None]:
    channel_id = bot.store.get(guild.id, PANEL_CHANNEL_KEY)
    message_id = bot.store.get(guild.id, PANEL_MESSAGE_KEY)
    channel = (
        (guild.get_channel(channel_id) or bot.get_channel(channel_id)) if channel_id else None
    )
    return channel, (int(message_id) if message_id else None)


async def panel_is_there(channel: Any, message_id: int) -> bool:
    """A button somebody deleted by hand reads as gone; anything else leaves it alone."""
    try:
        await channel.fetch_message(message_id)
    except discord.NotFound:
        return False
    except Exception as exc:
        log.info("modmail: could not look up the ticket button %s: %s", message_id, exc)
        return True
    return True


async def drop_panel_message(bot: Any, guild: Any, channel: Any, message_id: int) -> None:
    """Deleting a MESSAGE is a side effect `guard.py` never sees, so this one asks by hand."""
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel.id):
        await log_action(
            bot,
            guild,
            "modmail.would_take_down_panel",
            details={"channel_id": channel.id, "message_id": message_id},
        )
        return
    partial = getattr(channel, "get_partial_message", None)
    try:
        if partial is None:
            await (await channel.fetch_message(message_id)).delete()
        else:
            await partial(message_id).delete()
    except discord.NotFound:
        return
    except Exception as exc:
        log.info("modmail: the old ticket button %s stayed where it was: %s", message_id, exc)


async def post_ticket_panel(
    bot: Any,
    guild: Any,
    actor: Any,
    channel: Any,
    *,
    moving: bool | None = None,
    via: str = VIA_DISCORD,
) -> Outcome:
    """One Open-a-ticket message per guild, posted from Discord or from the website."""
    if channel is None:
        return refusal(PANEL_STUCK, "no_such_channel", 400)
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel.id):
        await log_action(
            bot,
            guild,
            kind_via("modmail.would_post_panel", via),
            actor=actor,
            details={"channel_id": channel.id, "via": via},
        )
        return refusal(PANEL_GUARDED, "test_mode", 409)
    old_channel, old_id = panel_where(bot, guild)
    store = bot.store
    try:
        message = await channel.send(
            embed=ticket_button_embed(
                store.get(guild.id, PANEL_HEADING_KEY), store.get(guild.id, PANEL_TEXT_KEY)
            ),
            view=ticket_panel_view(guild.id),
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except Exception as exc:
        log.warning("modmail: could not post the ticket button: %s", exc)
        await log_action(
            bot,
            guild,
            "modmail.panel_failed",
            actor=actor,
            details={"channel_id": channel.id, "reason": f"{type(exc).__name__}: {exc}"},
        )
        return refusal(PANEL_STUCK, "panel_stuck", 500)
    by = getattr(actor, "id", actor)
    await store.set(guild.id, PANEL_CHANNEL_KEY, channel.id, by=by)
    await store.set(guild.id, PANEL_MESSAGE_KEY, str(message.id), by=by)
    moved = (old_id is not None) if moving is None else moving
    if moved and old_channel is not None and old_id:
        await drop_panel_message(bot, guild, old_channel, old_id)
    await log_action(
        bot,
        guild,
        kind_via("modmail.panel_moved" if moved else "modmail.panel_posted", via),
        actor=actor,
        details={"channel_id": channel.id, "message_id": message.id, "via": via},
    )
    said = (PANEL_MOVED_SAID if moved else PANEL_POSTED_SAID).format(where=channel.id)
    return Outcome(True, said, value=message.id)


async def take_panel_down(
    bot: Any, guild: Any, actor: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Down means down: the message goes and both keys are cleared, so nothing puts it back."""
    channel, message_id = panel_where(bot, guild)
    if not bot.store.get(guild.id, PANEL_CHANNEL_KEY):
        return refusal(PANEL_NOT_UP, "no_panel", 404)
    if channel is not None and message_id:
        await drop_panel_message(bot, guild, channel, message_id)
    await bot.store.clear(guild.id, PANEL_MESSAGE_KEY)
    await bot.store.clear(guild.id, PANEL_CHANNEL_KEY)
    await log_action(
        bot,
        guild,
        kind_via("modmail.panel_taken_down", via),
        actor=actor,
        details={
            "channel_id": getattr(channel, "id", None),
            "message_id": message_id,
            "via": via,
        },
    )
    return Outcome(True, PANEL_DOWN_SAID, value=message_id)


class Modmail(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._refused: dict[int, datetime] = {}
        self._gone: dict[int, int] = {}
        self._panel_shadowed: set[int] = set()
        self.last_ok_at: str | None = None
        self.last_error: str | None = None

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name != "_reconcile_loop":
            return (None, None)
        return (self.last_ok_at, self.last_error)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.webhook_id is not None:
            return
        if getattr(message, "type", None) not in RELAY_TYPES:
            return
        if not self.bot.db.is_connected:
            return
        if message.guild is None:
            await self._inbound(message)
            return
        await self._staff_message(message)

    async def _inbound(self, message: discord.Message) -> None:
        """A DM to the bot: find the member's open ticket or open one, then relay it."""
        author = message.author
        row = await any_open_ticket_for(self.bot.db, author.id)
        guild = None
        if row is not None:
            guild = self.bot.get_guild(row["guild_id"])
        if guild is None:
            guild = self._home_guild(author.id)
        if guild is None:
            if self._anywhere_enabled():
                await self._refuse(author, NO_GUILD_DM)
            return
        if not self.bot.store.get(guild.id, "modmail_enabled"):
            await self._refuse(author, DISABLED_DM.format(guild=guild.name))
            return
        blocked = await blocked_row(self.bot.db, author.id)
        if blocked is not None:
            await self._refuse(author, BLOCKED_DM.format(guild=guild.name))
            await log_action(
                self.bot,
                guild,
                "modmail.blocked_dm",
                target=author,
                reason=blocked["reason"],
            )
            return
        async with user_lock(self.bot, author.id):
            ticket, opened = await self._open_or_find(guild, author)
            if ticket is None:
                await self._refuse(author, CANNOT_OPEN_DM)
                return
            why_not = await self._relay_inbound(guild, ticket, message)
            if opened:
                await deliver_dm(author, opening_dm(guild.name))
        await react(
            self.bot, message, TICKET_REACTION if why_not is None else FAILED_REACTION
        )

    def _home_guild(self, user_id: int) -> Any:
        for guild in getattr(self.bot, "guilds", ()):
            if guild.get_member(user_id) is not None:
                return guild
        return None

    def _anywhere_enabled(self) -> bool:
        return any(
            self.bot.store.get(guild.id, "modmail_enabled")
            for guild in getattr(self.bot, "guilds", ())
        )

    async def _refuse(self, user: Any, text: str) -> None:
        """One refusal DM per member per cooldown: a stranger must not be answered repeatedly."""
        now = datetime.now(UTC)
        cutoff = now - timedelta(minutes=REFUSAL_COOLDOWN_MINUTES)
        self._refused = {uid: at for uid, at in self._refused.items() if at > cutoff}
        if user.id in self._refused:
            return
        self._refused[user.id] = now
        await deliver_dm(user, text)

    async def _open_or_find(self, guild: Any, user: Any) -> tuple[Any, bool]:
        return await open_or_find(self.bot, guild, user, source=SOURCE_DM)

    async def _relay_inbound(
        self, guild: Any, ticket: Any, message: discord.Message
    ) -> str | None:
        return await record_inbound(
            self.bot,
            guild,
            ticket,
            message.author,
            message.content,
            attachment_urls(message.attachments),
        )

    async def _staff_message(self, message: discord.Message) -> None:
        """A plain message in a ticket is a reply; one starting with `=` is a private note."""
        ticket = await ticket_for_channel(self.bot.db, message.channel.id)
        if ticket is None or ticket["guild_id"] != message.guild.id:
            return
        if not self.bot.store.is_staff(message.author):
            return
        prefix = getattr(self.bot.settings, "command_prefix", None)
        if prefix and message.content.startswith(prefix):
            return
        me = getattr(self.bot, "user", None)
        if me is not None and message.content.startswith((f"<@{me.id}>", f"<@!{me.id}>")):
            return
        if is_note(message.content):
            await add_note(
                self.bot,
                message.guild,
                ticket,
                message.author,
                note_body(message.content),
                attachments=attachment_urls(message.attachments),
                echo=False,
                source=SOURCE_TYPED,
            )
            await react(self.bot, message, NOTE_REACTION)
            return
        if not relays_typing(self.bot.store.get(message.guild.id, REPLY_STYLE_KEY)):
            return
        why_not = await self._send_reply(
            message.guild,
            ticket,
            message.author,
            message.content,
            attachments=attachment_urls(message.attachments),
            source=SOURCE_TYPED,
        )
        await react(
            self.bot, message, TICKET_REACTION if why_not is None else FAILED_REACTION
        )

    async def _send_reply(
        self,
        guild: Any,
        ticket: Any,
        author: Any,
        content: Any,
        *,
        anonymous: bool = False,
        attachments: Any = (),
        echo: bool = True,
        source: str = SOURCE_COMMAND,
    ) -> str | None:
        return await send_reply(
            self.bot,
            guild,
            ticket,
            author,
            content,
            anonymous=anonymous,
            attachments=attachments,
            echo=echo,
            source=source,
        )

    async def _ready(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message(GUILD_ONLY, ephemeral=True)
            return False
        if not self.bot.db.is_connected:
            log.warning("modmail: refused a command — the database is not connected")
            await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
            return False
        return await require_staff(interaction)

    async def _resolve(self, interaction: discord.Interaction, ticket: Any) -> Any:
        row, why_not = await resolve_ticket(
            self.bot, interaction.guild, interaction.channel_id, ticket
        )
        if row is None:
            await answer(interaction, why_not)
        return row

    async def _body(self, interaction: discord.Interaction, text: Any, snippet: Any) -> Any:
        body, why_none = await reply_body(self.bot.db, text, snippet)
        if body is None:
            await answer(interaction, why_none)
        return body

    @app_commands.command(name="reply", description="Reply to the member in a modmail ticket")
    @app_commands.default_permissions(STAFF_ONLY)
    @app_commands.describe(
        text="What the member is sent",
        snippet="A saved reply to send instead — /modmail then Snippets… has them",
        ticket="The ticket number, when you are not in its channel",
    )
    async def reply(
        self,
        interaction: discord.Interaction,
        text: str | None = None,
        snippet: str | None = None,
        ticket: str | None = None,
    ) -> None:
        await self._reply(interaction, text, snippet, ticket)

    async def _reply(
        self,
        interaction: discord.Interaction,
        text: Any,
        snippet: Any,
        ticket: Any,
    ) -> None:
        if not await self._ready(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        row = await self._resolve(interaction, ticket)
        if row is None:
            return
        body = await self._body(interaction, text, snippet)
        if body is None:
            return
        why_not = await self._send_reply(interaction.guild, row, interaction.user, body)
        if why_not is not None:
            await answer(interaction, DM_FAILED_SAID)
            return
        await answer(interaction, SENT.format(who=interaction.user.display_name))

    async def _close(
        self,
        guild: Any,
        ticket: Any,
        *,
        by: Any = None,
        reason: Any = None,
        silent: bool = False,
    ) -> tuple[bool, str | None]:
        return await close_ticket(
            self.bot, guild, ticket, by=by, reason=reason, silent=silent
        )

    async def cog_load(self) -> None:
        self.bot.add_dynamic_items(TicketCardButton, TicketButton)
        if not self.bot.db.is_connected:
            return
        await self.reconcile_tickets()
        self._reconcile_loop.start()

    async def cog_unload(self) -> None:
        self._reconcile_loop.cancel()
        cancel_cards(self.bot)

    @tasks.loop(minutes=RECONCILE_MINUTES)
    async def _reconcile_loop(self) -> None:
        if self.bot.db.is_connected:
            await self.reconcile_tickets()

    @_reconcile_loop.before_loop
    async def _before_reconcile(self) -> None:
        await wait_ready(self.bot, self._reconcile_error)

    @_reconcile_loop.error
    async def _reconcile_error(self, error: BaseException) -> None:
        self.last_error = f"{type(error).__name__}: {error}"
        log.exception("modmail: the reconcile loop stopped", exc_info=error)
        self._reconcile_loop.restart()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self.bot.db.is_connected:
            return
        await self.reconcile_tickets()
        if not self._reconcile_loop.is_running():
            self._reconcile_loop.start()

    async def reconcile_tickets(self) -> None:
        """An open ticket whose channel or thread has gone is closed, with the reason recorded."""
        now = datetime.now(UTC)
        for guild in list(getattr(self.bot, "guilds", ())):
            if getattr(guild, "unavailable", False):
                continue
            for row in await open_tickets(self.bot.db, guild.id):
                await self._recheck(guild, row, now)
            await self._repanel(guild)
        self.last_ok_at = now_iso()

    async def _repanel(self, guild: Any) -> None:
        """The posted button belongs to the room, so one deleted by hand is put back."""
        bot = self.bot
        channel, message_id = panel_where(bot, guild)
        if not bot.store.get(guild.id, PANEL_CHANNEL_KEY) or channel is None:
            return
        if message_id and await panel_is_there(channel, message_id):
            self._panel_shadowed.discard(guild.id)
            return
        guard = getattr(bot, "guard", None)
        if guard is not None and not guard.allows_channel(channel.id):
            if guild.id not in self._panel_shadowed:
                self._panel_shadowed.add(guild.id)
                await log_action(
                    bot,
                    guild,
                    "modmail.would_post_panel",
                    details={"channel_id": channel.id, "reason": "reconcile"},
                )
            return
        if message_id:
            await log_action(
                bot,
                guild,
                "modmail.panel_gone",
                details={"channel_id": channel.id, "message_id": message_id},
            )
        outcome = await post_ticket_panel(bot, guild, None, channel, moving=False)
        if outcome.ok:
            self._panel_shadowed.discard(guild.id)

    async def _recheck(self, guild: Any, row: Any, now: datetime) -> None:
        if not row["channel_id"]:
            opened = parse_ts(row["opened_at"])
            if opened is not None and now - opened < timedelta(minutes=ORPHAN_GRACE_MINUTES):
                return
            await self._close(guild, row, reason="never_got_a_place", silent=True)
            return
        place, missing = await resolve_place(self.bot, guild, row)
        if place is not None or missing != "gone":
            self._gone.pop(row["id"], None)
            await self._recard(guild, row, place)
            return
        seen = self._gone.get(row["id"], 0) + 1
        self._gone[row["id"]] = seen
        if seen < GONE_STRIKES:
            return
        self._gone.pop(row["id"], None)
        await self._close(guild, row, reason="ticket_channel_gone")

    async def _recard(self, guild: Any, row: Any, place: Any) -> None:
        """Exactly one card, always last — the part of that promise a restart cannot keep."""
        if place is None:
            return
        card_id = field_of(row, "card_message_id")
        if card_id and await card_is_there(self.bot, guild, row, int(card_id)):
            return
        await refresh_card(self.bot, guild, row["id"])

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        if not self.bot.db.is_connected:
            return
        guild = channel.guild
        for key, kind in (
            ("modmail_category_id", "modmail.category_forgotten"),
            ("modmail_staff_channel_id", "modmail.staff_channel_forgotten"),
            ("modmail_log_channel_id", "modmail.log_channel_forgotten"),
        ):
            if channel.id == self.bot.store.get(guild.id, key):
                await self.bot.store.clear(guild.id, key)
                await log_action(self.bot, guild, kind, details={"channel_id": channel.id})
        if channel.id == self.bot.store.get(guild.id, PANEL_CHANNEL_KEY):
            await self.bot.store.clear(guild.id, PANEL_CHANNEL_KEY)
            await self.bot.store.clear(guild.id, PANEL_MESSAGE_KEY)
            await log_action(
                self.bot, guild, "modmail.panel_gone", details={"channel_id": channel.id}
            )
        for row in await tickets_in_channel(self.bot.db, channel.id):
            await self._close(guild, row, reason="ticket_channel_deleted")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        if not self.bot.db.is_connected:
            return
        guild = member.guild
        ticket = await open_ticket_for(self.bot.db, guild.id, member.id)
        if ticket is None:
            return
        said = LEFT_NOTE.format(who=getattr(member, "display_name", str(member)))
        await add_message(self.bot.db, ticket["id"], member.id, NOTE, content=said)
        await speak(
            self.bot,
            guild,
            ticket,
            embed=relay_embed(NOTE, author_name="Black Bloc", author_id=member.id, content=said),
        )
        await log_action(
            self.bot,
            guild,
            "modmail.member_left",
            target=member,
            details={"ticket_id": ticket["id"]},
        )
        await bump_card(self.bot, guild, ticket)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread) -> None:
        if not self.bot.db.is_connected:
            return
        for row in await tickets_in_channel(self.bot.db, thread.id):
            await self._close(thread.guild, row, reason="ticket_thread_deleted", silent=True)

    @app_commands.command(
        name="modmail",
        description="Open a ticket with the moderators, or run the inbox",
        extras={"staff_only": False},
    )
    async def modmail(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return
        staff = self.bot.store.is_staff(interaction.user)
        if not staff and not self.bot.store.get(interaction.guild.id, MEMBER_COMMAND_KEY):
            await require_staff(interaction)
            return
        if not await db_up(interaction):
            return
        embed, view = await build_root(
            self.bot, interaction.guild, self, actor=interaction.user, staff=staff
        )
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()

    async def _status_lines(self, guild: Any) -> list[str]:
        store = self.bot.store
        staff = store.staff_roles(guild)
        rows = await open_tickets(self.bot.db, guild.id)
        category_id = store.get(guild.id, "modmail_category_id")
        log_id = store.get(guild.id, "modmail_log_channel_id")
        parent_id = staff_parent_id(store, guild.id)
        lines = [
            f"**answering DMs** — {store.get(guild.id, 'modmail_enabled')}",
            f"**mode** — {store.get(guild.id, 'modmail_mode')}",
            "**ticket category** — " + (f"<#{category_id}>" if category_id else "not set"),
            "**thread parent** — " + (f"<#{parent_id}>" if parent_id else "not set"),
            "**transcripts** — " + (f"<#{log_id}>" if log_id else "not set"),
            f"**staff (who sees a ticket)** — {staff_roles_sentence(staff)}",
            f"**blocked** — {len(await blocked_rows(self.bot.db))} member(s)",
            f"**reconciler** — last ok {self.last_ok_at or 'never'} · "
            f"last error {self.last_error or 'none'}",
        ]
        if rows:
            lines += [
                f"**#{row['id']}** <@{row['user_id']}> — {row['mode']} · "
                f"<#{row['thread_id'] or row['channel_id']}>"
                for row in rows
            ]
        else:
            lines.append("No ticket is open.")
        if not staff:
            lines.append(NO_STAFF_WARNING)
        return lines


# --- the panel -----------------------------------------------------------------------------------


STYLES = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "danger": discord.ButtonStyle.danger,
}
SELECT_CAP = 25
FORGET_LABELS = {
    "modmail_category_id": "The ticket category",
    "modmail_staff_channel_id": "The staff channel",
    "modmail_log_channel_id": "The transcripts channel",
}
INCUMBENT_LINE = (
    "Black Bloc is **not** answering DMs here, so the old ModMail bot still holds the inbox. "
    "**Setup…** → **Answer DMs on** hands it over."
)
NOTHING_BLOCKED_HERE = "Nobody is blocked, so there is nobody to let back in."
REALLY_PRACTISE = (
    "**Try a fake ticket?** Black Bloc makes a private thread for you, with the ticket card in "
    "it. Nobody is DMed and no real member is involved."
)
PICKED_BLOCK = "Picked: <@{user_id}>."
PICKED_TO_BLOCK = "About to block <@{user_id}> — **Block them…** asks for the reason."
PICKED_SNIPPET = "Picked: **{name}**."
REALLY_REMOVE = "Remove the snippet **{name}**? Nothing that already went out changes."
BLOCK_REASON_TITLE = "Why they are blocked"
BLOCK_REASON_LABEL = "Why — the log records this, the member is not told"
SNIPPET_TITLE_NEW = "A new saved reply"
SNIPPET_TITLE_EDIT = "Change a saved reply"
SNIPPET_NAME_LABEL = "What to call it — lowercase, dashes, no spaces"
SNIPPET_CONTENT_LABEL = "What it says"


ROOT = "root"


class ModmailPanel(Panel):
    def __init__(self, minutes: int, cog: Any) -> None:
        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER)
        self.cog = cog
        self.surface = ROOT
        self.picked_block: int | None = None
        self.blocking: int | None = None
        self.picked_snippet: str | None = None
        self.picked_ticket: int | None = None
        self.confirming = False
        self.staff = True


def minutes_for(bot: Any, guild_id: int) -> int:
    return panel_minutes(bot.store, guild_id)


def pointed_keys(store: Any, guild: Any) -> list[str]:
    return [key for key in FORGETTABLE.values() if store.get(guild.id, key)]


def new_panel(bot: Any, guild: Any, cog: Any) -> ModmailPanel:
    return ModmailPanel(minutes_for(bot, guild.id), cog)


def setup_lines(bot: Any, guild: Any) -> list[str]:
    store = bot.store
    mode = store.get(guild.id, "modmail_mode")
    category_id = store.get(guild.id, "modmail_category_id")
    log_id = store.get(guild.id, "modmail_log_channel_id")
    parent_id = staff_parent_id(store, guild.id)
    return [
        f"**answering DMs** — {store.get(guild.id, 'modmail_enabled')}",
        f"**mode** — {mode} · {modes_sentence(mode)}",
        "**ticket category** — " + (f"<#{category_id}>" if category_id else "not set"),
        "**staff channel** — " + (f"<#{parent_id}>" if parent_id else "not set"),
        "**transcripts** — " + (f"<#{log_id}>" if log_id else "not set"),
        f"**reply style** — {store.get(guild.id, REPLY_STYLE_KEY)}",
        f"**this panel stays live** — {minutes_for(bot, guild.id)} minute(s)",
    ]


async def door_lines(bot: Any, guild: Any, actor: Any, *, staff: bool) -> tuple[list[str], bool]:
    """The first row of the panel, which is the same question for a member and for a Lead."""
    mine = await open_ticket_for(bot.db, guild.id, actor.id)
    if mine is not None:
        said = (
            MEMBER_TICKET_SEEN.format(where=ticket_place_id(mine))
            if staff
            else MEMBER_TICKET_OPEN
        )
        return [said], False
    if not bot.store.get(guild.id, "modmail_enabled"):
        return ([] if staff else [MEMBER_DOOR_OFF.format(guild=guild.name)]), False
    if await blocked_row(bot.db, actor.id) is not None:
        return [MEMBER_BLOCKED], False
    return [], True


async def build_root(
    bot: Any,
    guild: Any,
    cog: Any,
    *,
    actor: Any,
    staff: bool,
    confirming: bool = False,
    picking: bool = False,
    blocked_pick: int | None = None,
    note: str | None = None,
) -> tuple[discord.Embed, ModmailPanel]:
    mine, may_open = await door_lines(bot, guild, actor, staff=staff)
    if not staff:
        embed = discord.Embed(title=MEMBER_TITLE, description=clamped([MEMBER_INTRO, *mine]))
        view = new_panel(bot, guild, cog)
        view.staff = False
        for move in door_buttons(may_open=may_open, staff=False):
            view.add_item(MoveButton(move))
        return (embed, view)
    lines = [*mine, *await cog._status_lines(guild)]
    if not bot.store.get(guild.id, "modmail_enabled"):
        lines.append(INCUMBENT_LINE)
    if confirming:
        lines.append(REALLY_PRACTISE)
    if note:
        lines.append(note)
    embed = discord.Embed(title=PANEL_TITLE, description=clamped(lines))
    view = new_panel(bot, guild, cog)
    view.confirming = confirming
    view.picked_block = blocked_pick
    if not confirming:
        for move in door_buttons(
            may_open=may_open,
            staff=True,
            picking=picking,
            blocked_pick=blocked_pick is not None,
            open_with=open_with_on(bot.store, guild.id),
        ):
            view.add_item(MoveButton(move))
    if picking:
        view.add_item(MemberPick())
    else:
        tickets = [] if confirming else await open_tickets(bot.db, guild.id)
        if tickets:
            view.add_item(TicketPick(bot, guild, tickets))
    url = site_page_url(getattr(getattr(bot, "settings", None), "origin", ""), "modmail")
    for move in root_buttons(
        has_forget=bool(pointed_keys(bot.store, guild)),
        has_site=url is not None,
        has_practice=bool(bot.store.staff_roles(guild)),
        confirming=confirming,
    ):
        view.add_item(SiteButton(move, url) if move.action == SITE else MoveButton(move))
    return (embed, view)


def panel_lines(bot: Any, guild: Any) -> list[str]:
    store = bot.store
    channel_id = store.get(guild.id, PANEL_CHANNEL_KEY)
    message_id = store.get(guild.id, PANEL_MESSAGE_KEY)
    where = (
        PANEL_IS_AT.format(where=channel_id, message_id=message_id)
        if channel_id and message_id
        else PANEL_NOWHERE
    )
    return [
        where,
        PANEL_LINES.format(
            title=store.get(guild.id, PANEL_HEADING_KEY),
            text=store.get(guild.id, PANEL_TEXT_KEY),
        ),
    ]


def build_ticket_button(
    bot: Any, guild: Any, cog: Any, *, picking: bool = False
) -> tuple[discord.Embed, ModmailPanel]:
    embed = discord.Embed(title=TICKET_BUTTON_TITLE, description=clamped(panel_lines(bot, guild)))
    view = new_panel(bot, guild, cog)
    view.surface = TICKET_BUTTON
    if picking:
        view.add_item(PanelPlacePick())
    for move in ticket_button_buttons(
        posted=bool(bot.store.get(guild.id, PANEL_MESSAGE_KEY)), picking=picking
    ):
        view.add_item(MoveButton(move))
    return (embed, view)


def build_setup(
    bot: Any, guild: Any, cog: Any, picker: str | None = None
) -> tuple[discord.Embed, ModmailPanel]:
    embed = discord.Embed(title=SETUP_TITLE, description=clamped(setup_lines(bot, guild)))
    view = new_panel(bot, guild, cog)
    view.surface = SETUP
    if picker == CATEGORY:
        view.add_item(PlacePick(CATEGORY, "modmail_category_id"))
    elif picker == STAFF_CHANNEL:
        view.add_item(PlacePick(STAFF_CHANNEL, "modmail_staff_channel_id"))
    elif picker == TRANSCRIPTS:
        view.add_item(PlacePick(TRANSCRIPTS, "modmail_log_channel_id"))
    elif picker == MODE:
        view.add_item(ModePick(bot.store.get(guild.id, "modmail_mode")))
    elif picker == REPLY_STYLE:
        view.add_item(ReplyStylePick(bot.store.get(guild.id, REPLY_STYLE_KEY)))
    for move in setup_buttons(enabled=bool(bot.store.get(guild.id, "modmail_enabled"))):
        view.add_item(MoveButton(move))
    return (embed, view)


async def build_blocked(
    bot: Any, guild: Any, cog: Any, *, picked: int | None = None, blocking: int | None = None
) -> tuple[discord.Embed, ModmailPanel]:
    rows = await blocked_rows(bot.db)
    known = {int(row["user_id"]) for row in rows}
    picked = picked if picked in known else None
    lines = blocked_lines(rows) or [NO_BLOCKS]
    if blocking:
        lines.append(PICKED_TO_BLOCK.format(user_id=blocking))
    elif picked is not None:
        lines.append(PICKED_BLOCK.format(user_id=picked))
    embed = discord.Embed(title=BLOCKED_TITLE, description=clamped(lines))
    view = new_panel(bot, guild, cog)
    view.surface = BLOCKED_MOVE
    view.picked_block = picked
    view.blocking = blocking
    if blocking is not None:
        view.add_item(SomebodyPick())
    elif rows:
        view.add_item(BlockedPick(rows, picked))
    for move in blocked_buttons(picked=picked is not None, blocking=bool(blocking)):
        view.add_item(MoveButton(move))
    return (embed, view)


async def build_snippets(
    bot: Any, guild: Any, cog: Any, *, picked: str | None = None, confirming: bool = False
) -> tuple[discord.Embed, ModmailPanel]:
    rows = await all_snippets(bot.db)
    names = {row["name"] for row in rows}
    picked = picked if picked in names else None
    lines = snippet_lines(rows) or [NO_SNIPPETS]
    if confirming and picked is not None:
        lines.append(REALLY_REMOVE.format(name=picked))
    elif picked is not None:
        lines.append(PICKED_SNIPPET.format(name=picked))
    embed = discord.Embed(title=SNIPPETS_TITLE, description=clamped(lines))
    view = new_panel(bot, guild, cog)
    view.surface = SNIPPETS
    view.picked_snippet = picked
    if rows and not confirming:
        view.add_item(SnippetPick(rows, picked))
    for move in snippet_buttons(
        picked=picked is not None, confirming=confirming and picked is not None
    ):
        view.add_item(MoveButton(move))
    return (embed, view)


def build_forget(bot: Any, guild: Any, cog: Any) -> tuple[discord.Embed, ModmailPanel]:
    embed = discord.Embed(title=FORGET_TITLE, description=clamped(setup_lines(bot, guild)))
    view = new_panel(bot, guild, cog)
    view.surface = FORGET
    keys = pointed_keys(bot.store, guild)
    if keys:
        view.add_item(ForgetPick(keys))
    for move in forget_buttons():
        view.add_item(MoveButton(move))
    return (embed, view)


async def build_ticket(
    bot: Any, guild: Any, cog: Any, ticket_id: int
) -> tuple[discord.Embed, ModmailPanel] | None:
    """The sticky card's own embed, on the panel, with the same four moves plus Back."""
    row = await get_ticket(bot.db, ticket_id)
    if row is None or row["guild_id"] != guild.id:
        return None
    embed = await card_embed(bot, guild, row)
    still_open = row["status"] == OPEN
    if not still_open:
        embed.set_footer(text=CARD_CLOSED_FOOTER)
    view = new_panel(bot, guild, cog)
    view.surface = TICKET_SURFACE
    view.picked_ticket = int(row["id"])
    for move in panel_card_buttons(open_ticket=still_open):
        view.add_item(MoveButton(move))
    return (embed, view)


async def show(interaction: discord.Interaction, built: Any, previous: Any) -> None:
    embed, view = built
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


def cog_of(view: Any) -> Any:
    return getattr(view, "cog", None)


async def render_root(
    interaction: discord.Interaction,
    previous: Any = None,
    *,
    confirming: bool = False,
    picking: bool = False,
    blocked_pick: int | None = None,
    note: str | None = None,
) -> None:
    bot = interaction.client
    built = await build_root(
        bot,
        interaction.guild,
        cog_of(previous),
        actor=interaction.user,
        staff=bot.store.is_staff(interaction.user),
        confirming=confirming,
        picking=picking,
        blocked_pick=blocked_pick,
        note=note,
    )
    await show(interaction, built, previous)


async def open_root(
    interaction: discord.Interaction,
    previous: Any = None,
    *,
    confirming: bool = False,
    picking: bool = False,
    staff: bool = True,
) -> None:
    if not await opened(interaction, staff=staff):
        return
    await render_root(interaction, previous, confirming=confirming, picking=picking)


async def run_open_with(interaction: discord.Interaction, previous: Any) -> None:
    """A panel opened while the door was on still draws the button after it is switched off."""
    if not await opened(interaction):
        return
    if not open_with_on(interaction.client.store, interaction.guild.id):
        await render_root(interaction, previous)
        await answer(interaction, OPEN_WITH_OFF)
        return
    await render_root(interaction, previous, picking=True)


async def open_ticket_button(
    interaction: discord.Interaction, previous: Any = None, *, picking: bool = False
) -> None:
    if not await opened(interaction):
        return
    built = build_ticket_button(
        interaction.client, interaction.guild, cog_of(previous), picking=picking
    )
    await show(interaction, built, previous)


async def run_post_panel(
    interaction: discord.Interaction, channel: Any, previous: Any
) -> None:
    if not await opened(interaction):
        return
    outcome = await post_ticket_panel(
        interaction.client, interaction.guild, interaction.user, channel
    )
    built = build_ticket_button(interaction.client, interaction.guild, cog_of(previous))
    await show(interaction, built, previous)
    await answer(interaction, outcome.message)


async def run_take_panel_down(interaction: discord.Interaction, previous: Any) -> None:
    if not await opened(interaction):
        return
    outcome = await take_panel_down(
        interaction.client, interaction.guild, interaction.user
    )
    built = build_ticket_button(interaction.client, interaction.guild, cog_of(previous))
    await show(interaction, built, previous)
    await answer(interaction, outcome.message)


async def open_with_member(interaction: discord.Interaction, user: Any, previous: Any) -> None:
    """A door that will refuse says so BEFORE it asks staff to type a paragraph."""
    bot = interaction.client
    guild = interaction.guild
    if not await still_staff(interaction):
        return
    if not await db_up(interaction):
        return
    why_not = await open_with_refusal(bot, guild, user)
    if why_not is None:
        await interaction.response.send_modal(
            TicketModal(source=SOURCE_STAFF, member=user, previous=previous)
        )
        return
    said, blocked = why_not
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    await render_root(
        interaction, previous, blocked_pick=user.id if blocked else None, note=said
    )
    await answer(interaction, said)


async def open_with_refusal(bot: Any, guild: Any, user: Any) -> tuple[str, bool] | None:
    """The three answers `open_a_ticket` would give, asked before the modal rather than after."""
    who = who_said(user, user.id)
    if not open_with_on(bot.store, guild.id):
        return OPEN_WITH_OFF, False
    if getattr(user, "bot", False):
        return A_BOT_SAID.format(who=who), False
    if not bot.store.get(guild.id, "modmail_enabled"):
        return STAFF_DISABLED_SAID, False
    if await blocked_row(bot.db, user.id) is not None:
        return STAFF_BLOCKED_SAID.format(who=who), True
    existing = await open_ticket_for(bot.db, guild.id, user.id)
    if existing is not None:
        return STAFF_ALREADY_OPEN.format(who=who, where=ticket_place_id(existing)), False
    return None


async def run_open_ticket(
    interaction: discord.Interaction,
    *,
    source: str,
    subject: Any,
    text: Any,
    member: Any = None,
    previous: Any = None,
) -> None:
    """Every door's modal lands here: defer, open, re-render what raised it, answer once."""
    bot = interaction.client
    staff_door = source == SOURCE_STAFF
    if previous is None:
        await interaction.response.defer(ephemeral=True)
        if not await db_ready(interaction):
            return
    elif not await opened(interaction, staff=staff_door):
        return
    outcome = await open_a_ticket(
        bot,
        interaction.guild,
        member if member is not None else interaction.user,
        source=source,
        subject=subject,
        text=text,
        actor=interaction.user if staff_door else None,
    )
    if previous is not None:
        await render_root(interaction, previous)
    await answer(interaction, outcome.message)


async def run_practice(interaction: discord.Interaction, previous: Any) -> None:
    if not await opened(interaction):
        return
    outcome = await open_practice(interaction.client, interaction.guild, interaction.user)
    await render_root(interaction, previous)
    await answer(interaction, outcome.message)


async def open_setup(
    interaction: discord.Interaction, previous: Any = None, picker: str | None = None
) -> None:
    if not await opened(interaction):
        return
    built = build_setup(interaction.client, interaction.guild, cog_of(previous), picker)
    await show(interaction, built, previous)


async def open_blocked(
    interaction: discord.Interaction,
    previous: Any = None,
    *,
    picked: int | None = None,
    blocking: int | None = None,
) -> None:
    if not await opened(interaction):
        return
    built = await build_blocked(
        interaction.client, interaction.guild, cog_of(previous), picked=picked, blocking=blocking
    )
    await show(interaction, built, previous)


async def open_snippets(
    interaction: discord.Interaction,
    previous: Any = None,
    *,
    picked: str | None = None,
    confirming: bool = False,
) -> None:
    if not await opened(interaction):
        return
    built = await build_snippets(
        interaction.client,
        interaction.guild,
        cog_of(previous),
        picked=picked,
        confirming=confirming,
    )
    await show(interaction, built, previous)


async def show_ticket(interaction: discord.Interaction, previous: Any, ticket_id: int) -> bool:
    """A ticket the panel can no longer read falls back to the root rather than a dead card."""
    built = await build_ticket(
        interaction.client, interaction.guild, cog_of(previous), ticket_id
    )
    if built is None:
        await render_root(interaction, previous)
        return False
    await show(interaction, built, previous)
    return True


async def open_ticket_card(
    interaction: discord.Interaction, previous: Any, ticket_id: int
) -> None:
    if not await opened(interaction):
        return
    if not await show_ticket(interaction, previous, ticket_id):
        await answer(interaction, NO_SUCH_TICKET.format(ticket_id=ticket_id))


async def open_forget(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    built = build_forget(interaction.client, interaction.guild, cog_of(previous))
    await show(interaction, built, previous)


async def run_place(
    interaction: discord.Interaction, key: str, value: Any, previous: Any = None
) -> None:
    if not await opened(interaction):
        return
    outcome = await point_at(
        interaction.client, interaction.guild, interaction.user, key, value
    )
    await open_setup_again(interaction, previous, outcome)


async def open_setup_again(
    interaction: discord.Interaction, previous: Any, outcome: Outcome
) -> None:
    built = build_setup(interaction.client, interaction.guild, cog_of(previous))
    await show(interaction, built, previous)
    await answer(interaction, outcome.message)


async def run_mode(interaction: discord.Interaction, value: str, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    outcome = await set_mode(interaction.client, interaction.guild, interaction.user, value)
    await open_setup_again(interaction, previous, outcome)


async def run_reply_style(
    interaction: discord.Interaction, value: str, previous: Any = None
) -> None:
    if not await opened(interaction):
        return
    outcome = await set_reply_style(
        interaction.client, interaction.guild, interaction.user, value
    )
    await open_setup_again(interaction, previous, outcome)


async def run_enabled(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    bot = interaction.client
    wanted = not bot.store.get(interaction.guild.id, "modmail_enabled")
    outcome = await set_enabled(bot, interaction.guild, interaction.user, wanted)
    await open_setup_again(interaction, previous, outcome)


async def run_forget(interaction: discord.Interaction, key: str, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    outcome = await forget_place(
        interaction.client, interaction.guild, interaction.user, key
    )
    if pointed_keys(interaction.client.store, interaction.guild):
        await show(
            interaction,
            build_forget(interaction.client, interaction.guild, cog_of(previous)),
            previous,
        )
    else:
        await render_root(interaction, previous)
    await answer(interaction, outcome.message)


async def run_unblock(interaction: discord.Interaction, previous: Any) -> None:
    if not await opened(interaction):
        return
    picked = getattr(previous, "picked_block", None)
    if picked is None:
        await answer(interaction, NOTHING_BLOCKED_HERE)
        return
    outcome = await unblock_member(
        interaction.client, interaction.guild, interaction.user, picked
    )
    built = await build_blocked(interaction.client, interaction.guild, cog_of(previous))
    await show(interaction, built, previous)
    await answer(interaction, outcome.message)


async def run_block(
    interaction: discord.Interaction, user_id: int, reason: Any, previous: Any
) -> None:
    if not await opened(interaction):
        return
    outcome = await block_member(
        interaction.client, interaction.guild, interaction.user, user_id, reason
    )
    built = await build_blocked(interaction.client, interaction.guild, cog_of(previous))
    await show(interaction, built, previous)
    await answer(interaction, outcome.message)


async def run_put_snippet(
    interaction: discord.Interaction, name: Any, content: Any, previous: Any, *, overwrite: bool
) -> None:
    if not await opened(interaction):
        return
    outcome = await put_snippet(
        interaction.client,
        interaction.guild,
        interaction.user,
        name,
        content,
        overwrite=overwrite,
    )
    built = await build_snippets(
        interaction.client, interaction.guild, cog_of(previous), picked=outcome.value
    )
    await show(interaction, built, previous)
    await answer(interaction, outcome.message)


async def run_drop_snippet(interaction: discord.Interaction, previous: Any) -> None:
    if not await opened(interaction):
        return
    picked = getattr(previous, "picked_snippet", None)
    if picked is None:
        await answer(interaction, NO_SNIPPETS)
        return
    outcome = await drop_snippet(
        interaction.client, interaction.guild, interaction.user, picked
    )
    built = await build_snippets(interaction.client, interaction.guild, cog_of(previous))
    await show(interaction, built, previous)
    await answer(interaction, outcome.message)


# --- the controls --------------------------------------------------------------------------------


class MoveButton(discord.ui.Button):
    def __init__(self, move: Any) -> None:
        super().__init__(label=move.label, style=STYLES[move.style], row=move.row)
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        action = self.move.action
        if action == TICKET_OPEN:
            await open_ticket_modal(interaction, view)
            return
        if action == LOGS:
            await send_logs(interaction, "modmail")
            return
        if action == OPEN_WITH:
            await run_open_with(interaction, view)
            return
        if action == TICKET_BUTTON:
            await open_ticket_button(interaction, view)
            return
        if action in (PANEL_POST, PANEL_MOVE_TO):
            await open_ticket_button(interaction, view, picking=True)
            return
        if action == PANEL_DOWN:
            await run_take_panel_down(interaction, view)
            return
        if action == SETUP:
            await open_setup(interaction, view)
            return
        if action == BLOCKED_MOVE:
            await open_blocked(interaction, view)
            return
        if action == SNIPPETS:
            await open_snippets(interaction, view)
            return
        if action == FORGET:
            await open_forget(interaction, view)
            return
        if action == PRACTICE:
            await open_root(interaction, view, confirming=True)
            return
        if action == PRACTICE_YES:
            await run_practice(interaction, view)
            return
        if action == PRACTICE_NO:
            await open_root(interaction, view)
            return
        if action in (CATEGORY, STAFF_CHANNEL, TRANSCRIPTS, MODE, REPLY_STYLE):
            await open_setup(interaction, view, action)
            return
        if action in (ENABLE, DISABLE):
            await run_enabled(interaction, view)
            return
        if action == BLOCK_PICK:
            await open_blocked(interaction, view, picked=view.picked_block, blocking=0)
            return
        if action == UNBLOCK:
            await run_unblock(interaction, view)
            return
        if action == SNIPPET_REMOVE:
            await open_snippets(
                interaction, view, picked=view.picked_snippet, confirming=True
            )
            return
        if action == SNIPPET_REMOVE_YES:
            await run_drop_snippet(interaction, view)
            return
        if action == SNIPPET_REMOVE_NO:
            await open_snippets(interaction, view, picked=view.picked_snippet)
            return
        if action in (BACK, REFRESH):
            await self.go_back(interaction, view)
            return
        await self.open_modal(interaction, view)

    async def go_back(self, interaction: discord.Interaction, view: Any) -> None:
        """Back is always the root; Refresh redraws the surface the button is sitting on."""
        surface = ROOT if self.move.action == BACK else getattr(view, "surface", ROOT)
        if surface == SETUP:
            await open_setup(interaction, view)
        elif surface == BLOCKED_MOVE:
            await open_blocked(interaction, view, picked=view.picked_block)
        elif surface == SNIPPETS:
            await open_snippets(interaction, view, picked=view.picked_snippet)
        elif surface == FORGET:
            await open_forget(interaction, view)
        elif surface == TICKET_BUTTON:
            await open_ticket_button(interaction, view)
        else:
            await open_root(interaction, view, staff=getattr(view, "staff", True))

    async def open_modal(self, interaction: discord.Interaction, view: Any) -> None:
        if not await still_staff(interaction):
            return
        if not await db_up(interaction):
            return
        if self.move.action in CARD_ACTIONS_ON_THE_PANEL:
            await self.open_card_modal(interaction, view)
            return
        if self.move.action == BLOCK_REASON:
            await interaction.response.send_modal(BlockReasonModal(view.blocking, view))
            return
        if self.move.action == SNIPPET_CHANGE:
            row = await get_snippet(interaction.client.db, str(view.picked_snippet))
            await interaction.response.send_modal(
                SnippetModal(view, name=view.picked_snippet, content=row["content"] if row else "")
            )
            return
        await interaction.response.send_modal(SnippetModal(view))

    async def open_card_modal(self, interaction: discord.Interaction, view: Any) -> None:
        """The panel's copy of a card move opens the SAME modal the card in the channel does."""
        ticket_id = int(getattr(view, "picked_ticket", None) or 0)
        if await card_ticket(interaction, ticket_id) is None:
            return
        await interaction.response.send_modal(
            await card_modal(interaction, self.move.action, ticket_id, previous=view)
        )


class SiteButton(discord.ui.Button):
    def __init__(self, move: Any, url: str) -> None:
        super().__init__(label=move.label, style=discord.ButtonStyle.link, url=url, row=move.row)


class PlacePick(discord.ui.ChannelSelect):
    def __init__(self, action: str, key: str) -> None:
        kinds = (
            [discord.ChannelType.category]
            if action == CATEGORY
            else [discord.ChannelType.text]
        )
        super().__init__(
            placeholder=PICK_A_CATEGORY if action == CATEGORY else PICK_A_CHANNEL,
            channel_types=kinds,
            min_values=1,
            max_values=1,
            row=0,
        )
        self.key = key

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_place(interaction, self.key, self.values[0].id, self.view)


class ModePick(discord.ui.Select):
    def __init__(self, current: str) -> None:
        super().__init__(
            placeholder=PICK_A_MODE,
            options=[
                discord.SelectOption(
                    label=name,
                    value=name,
                    description=modes_sentence(name)[:100],
                    default=name == current,
                )
                for name in MODMAIL_MODES
            ],
            min_values=1,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_mode(interaction, self.values[0], self.view)


class ReplyStylePick(discord.ui.Select):
    def __init__(self, current: str) -> None:
        super().__init__(
            placeholder=PICK_A_REPLY_STYLE,
            options=[
                discord.SelectOption(
                    label=name,
                    value=name,
                    description=REPLY_STYLE_OPTIONS[name][:100],
                    default=name == current,
                )
                for name in MODMAIL_REPLY_STYLES
            ],
            min_values=1,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_reply_style(interaction, self.values[0], self.view)


class BlockedPick(discord.ui.Select):
    def __init__(self, rows: Any, picked: int | None) -> None:
        shown = list(rows)[:SELECT_CAP]
        super().__init__(
            placeholder=capped_placeholder(len(shown), len(rows), pick=PICK_A_BLOCK),
            options=[
                discord.SelectOption(
                    label=str(row["user_id"])[:SELECT_OPTION_LIMIT],
                    value=str(row["user_id"]),
                    description=clamp(row["reason"] or "no reason given", 100),
                    default=int(row["user_id"]) == picked,
                )
                for row in shown
            ],
            min_values=1,
            max_values=1,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_blocked(interaction, self.view, picked=int(self.values[0]))


class SomebodyPick(discord.ui.UserSelect):
    """Somebody past the 25-row cap is still reachable, because blocking is not list-bounded."""

    def __init__(self) -> None:
        super().__init__(placeholder=PICK_SOMEBODY, min_values=1, max_values=1, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_blocked(interaction, self.view, blocking=self.values[0].id)


class SnippetPick(discord.ui.Select):
    def __init__(self, rows: Any, picked: str | None) -> None:
        shown = list(rows)[:SELECT_CAP]
        super().__init__(
            placeholder=capped_placeholder(len(shown), len(rows), pick=PICK_A_SNIPPET),
            options=[
                discord.SelectOption(
                    label=str(row["name"])[:SELECT_OPTION_LIMIT],
                    value=str(row["name"]),
                    description=clamp(row["content"], 100),
                    default=row["name"] == picked,
                )
                for row in shown
            ],
            min_values=1,
            max_values=1,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_snippets(interaction, self.view, picked=self.values[0])


class TicketPick(discord.ui.Select):
    """Row 0 of the root: the open tickets, and picking one draws its card on the panel."""

    def __init__(self, bot: Any, guild: Any, rows: Any) -> None:
        found = list(rows)
        shown = found[:SELECT_CAP]
        super().__init__(
            placeholder=capped_placeholder(len(shown), len(found), pick=PICK_A_TICKET),
            options=[
                discord.SelectOption(
                    label=ticket_label(
                        row, getattr(ticket_member(bot, guild, row), "display_name", None)
                    ),
                    value=str(row["id"]),
                    description=clamp(str(row["opened_at"]), 100),
                )
                for row in shown
            ],
            min_values=1,
            max_values=1,
            row=ROOT_ROW_SELECT,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_ticket_card(interaction, self.view, int(self.values[0]))


class MemberPick(discord.ui.UserSelect):
    """Staff open a ticket WITH somebody, and anybody in the server can be that somebody."""

    def __init__(self) -> None:
        super().__init__(
            placeholder=PICK_A_MEMBER, min_values=1, max_values=1, row=ROOT_ROW_SELECT
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_with_member(interaction, self.values[0], self.view)


class PanelPlacePick(discord.ui.ChannelSelect):
    def __init__(self) -> None:
        super().__init__(
            placeholder=PICK_A_CHANNEL,
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        bot = interaction.client
        picked = self.values[0]
        channel = (
            interaction.guild.get_channel(picked.id) or bot.get_channel(picked.id) or picked
        )
        await run_post_panel(interaction, channel, self.view)


class ForgetPick(discord.ui.Select):
    def __init__(self, keys: list[str]) -> None:
        super().__init__(
            placeholder=PICK_A_PLACE,
            options=[
                discord.SelectOption(label=FORGET_LABELS[key], value=key, description=key)
                for key in keys
            ],
            min_values=1,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_forget(interaction, self.values[0], self.view)


# --- the modals ----------------------------------------------------------------------------------


class BlockReasonModal(NoteModal):
    def __init__(self, user_id: int, previous: Any) -> None:
        super().__init__(
            title=BLOCK_REASON_TITLE,
            label=BLOCK_REASON_LABEL,
            max_length=400,
            on_submit=self.taken,
            required=False,
        )
        self.user_id = int(user_id)
        self.previous = previous

    async def taken(self, interaction: discord.Interaction, text: str) -> None:
        await run_block(interaction, self.user_id, text.strip() or None, self.previous)


class SnippetModal(AnswersErrors, discord.ui.Modal):
    name = discord.ui.TextInput(label=SNIPPET_NAME_LABEL, max_length=SNIPPET_NAME_LIMIT)
    content = discord.ui.TextInput(
        label=SNIPPET_CONTENT_LABEL,
        style=discord.TextStyle.paragraph,
        max_length=CONTENT_LIMIT,
    )

    def __init__(self, previous: Any, *, name: Any = None, content: Any = None) -> None:
        super().__init__(title=(SNIPPET_TITLE_EDIT if name else SNIPPET_TITLE_NEW)[:45])
        self.previous = previous
        self.overwrite = bool(name)
        if name:
            self.name.default = str(name)
        if content:
            self.content.default = clamp(content, CONTENT_LIMIT)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_put_snippet(
            interaction,
            str(self.name),
            clamp(str(self.content), CONTENT_LIMIT),
            self.previous,
            overwrite=self.overwrite,
        )


class TicketModal(AnswersErrors, discord.ui.Modal):
    """One form behind every door: a few words about it, then what is happening."""

    def __init__(self, *, source: str, member: Any = None, previous: Any = None) -> None:
        staff_door = source == SOURCE_STAFF
        super().__init__(title=STAFF_MODAL_TITLE if staff_door else TICKET_MODAL_TITLE)
        self.source = source
        self.member = member
        self.previous = previous
        self.subject = discord.ui.TextInput(max_length=NAME_LIMIT, required=False)
        self.body = discord.ui.TextInput(
            style=discord.TextStyle.paragraph, max_length=MESSAGE_LIMIT
        )
        self.add_item(discord.ui.Label(text=TICKET_SUBJECT_LABEL, component=self.subject))
        self.add_item(
            discord.ui.Label(
                text=STAFF_BODY_LABEL if staff_door else TICKET_BODY_LABEL, component=self.body
            )
        )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_open_ticket(
            interaction,
            source=self.source,
            subject=clamp(str(self.subject), NAME_LIMIT).strip() or None,
            text=clamp(str(self.body), MESSAGE_LIMIT),
            member=self.member,
            previous=self.previous,
        )


async def open_ticket_modal(interaction: discord.Interaction, previous: Any = None) -> None:
    """The one place a member's form is raised, from the panel or from the posted button."""
    if not await db_up(interaction):
        return
    source = SOURCE_COMMAND if previous is not None else SOURCE_PANEL
    await interaction.response.send_modal(TicketModal(source=source, previous=previous))


class TicketButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=TICKET_PANEL_TEMPLATE
):
    """The posted Open a ticket button: persistent, and its whole answer is ephemeral."""

    def __init__(self, guild_id: Any) -> None:
        self.guild_id = int(guild_id)
        super().__init__(
            discord.ui.Button(
                label=TICKET_MOVE.label,
                style=discord.ButtonStyle.primary,
                custom_id=ticket_panel_custom_id(guild_id),
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: Any):
        return cls(int(match["guild_id"]))

    async def on_click(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return
        await open_ticket_modal(interaction)


# --- the sticky ticket card ----------------------------------------------------------------------


SNIPPET_GROUP_UP_TO = 10
CLOSE_REASON_LIMIT = 400

REPLY_TITLE = "Reply to the member"
ANON_REPLY_TITLE = "Reply as Staff"
REPLY_TEXT_LABEL = "What the member is sent"
REPLY_SNIPPET_LABEL = "Or a saved reply — with both, the snippet goes first"
CARD_NOTE_TITLE = "A private note"
CARD_NOTE_LABEL = "Why — the member never sees this"
CLOSE_TITLE = "Close this ticket"
CLOSE_REASON_LABEL = "Why — the member is told this"
CLOSE_SILENT_LABEL = "Or close it quietly"
CLOSE_SILENT_OPTION = "Close without telling them"
SPEAK_TITLE = "Say it as the member"
SPEAK_LABEL = "What the pretend member says — nobody is DMed"
CARD_MOVE_BY_ACTION = {move.action: move for move in CARD_MOVES}
CARD_ACTIONS_ON_THE_PANEL = (CARD_REPLY, CARD_ANON, CARD_NOTE, CARD_CLOSE)
REPLY_ACTIONS = (CARD_REPLY, CARD_ANON)


def card_custom_id(action: str, ticket_id: Any) -> str:
    return f"modmail:card:{action}:{int(ticket_id)}"


def card_view(ticket: Any) -> discord.ui.View:
    """The card belongs to the room, so its buttons outlive the process that posted them."""
    view = discord.ui.View(timeout=None)
    for move in card_buttons(practice=is_practice(ticket)):
        view.add_item(TicketCardButton(move, ticket["id"]))
    return view


def snippet_picker(rows: Any) -> Any:
    """`vote_picker`'s rule: typed fields while they fit, a select once there are too many."""
    found = list(rows or ())[:SELECT_CAP]
    options = [
        (str(row["name"])[:SELECT_OPTION_LIMIT], clamp(row["content"], 100)) for row in found
    ]
    if len(options) > SNIPPET_GROUP_UP_TO:
        return discord.ui.Select(
            placeholder=capped_placeholder(len(found), len(list(rows)), pick=PICK_A_SNIPPET),
            options=[
                discord.SelectOption(label=name, value=name, description=text)
                for name, text in options
            ],
            min_values=0,
            max_values=1,
            required=False,
        )
    return discord.ui.RadioGroup(
        options=[
            discord.RadioGroupOption(label=name, value=name, description=text)
            for name, text in options
        ],
        required=False,
    )


async def card_ticket(interaction: discord.Interaction, ticket_id: int) -> Any:
    """A card outlives a ticket, so every press re-reads the row before it trusts the button."""
    row = await get_ticket(interaction.client.db, ticket_id)
    if row is None or row["guild_id"] != interaction.guild.id:
        await answer(interaction, NO_SUCH_TICKET.format(ticket_id=ticket_id))
        return None
    if row["status"] != OPEN:
        await answer(interaction, TICKET_CLOSED.format(ticket_id=ticket_id))
        return None
    return row


async def card_opened(interaction: discord.Interaction, ticket_id: int) -> Any:
    if not await still_staff(interaction):
        return None
    await interaction.response.defer(ephemeral=True)
    if not await db_ready(interaction):
        return None
    return await card_ticket(interaction, ticket_id)


async def opened_card(interaction: discord.Interaction, ticket_id: int, previous: Any) -> Any:
    """The card in the channel answers ephemerally; the panel's copy defers into its own edit."""
    if previous is None:
        return await card_opened(interaction, ticket_id)
    if not await opened(interaction):
        return None
    return await card_ticket(interaction, ticket_id)


async def card_moved(
    interaction: discord.Interaction, ticket_id: int, previous: Any, said: str
) -> None:
    """The sticky card is the refresher's to move; only the panel's copy is redrawn here."""
    if previous is not None:
        await show_ticket(interaction, previous, ticket_id)
    await answer(interaction, said)


async def run_card_reply(
    interaction: discord.Interaction,
    ticket_id: int,
    text: Any,
    snippet: Any,
    *,
    anonymous: bool,
    previous: Any = None,
) -> None:
    ticket = await opened_card(interaction, ticket_id, previous)
    if ticket is None:
        return
    body, why_none = await reply_body(interaction.client.db, text, snippet)
    if body is None:
        await answer(interaction, why_none)
        return
    why_not = await send_reply(
        interaction.client,
        interaction.guild,
        ticket,
        interaction.user,
        body,
        anonymous=anonymous,
        source=SOURCE_CARD,
    )
    who = ANONYMOUS_NAME if anonymous else interaction.user.display_name
    said = DM_FAILED_SAID if why_not is not None else SENT.format(who=who)
    await card_moved(interaction, ticket_id, previous, said)


async def run_card_note(
    interaction: discord.Interaction, ticket_id: int, text: Any, previous: Any = None
) -> None:
    ticket = await opened_card(interaction, ticket_id, previous)
    if ticket is None:
        return
    if not str(text or "").strip():
        await answer(interaction, NOTHING_TO_NOTE)
        return
    outcome = await add_note(
        interaction.client,
        interaction.guild,
        ticket,
        interaction.user,
        str(text).strip(),
        source=SOURCE_CARD,
    )
    await card_moved(interaction, ticket_id, previous, outcome.message)


async def run_card_close(
    interaction: discord.Interaction,
    ticket_id: int,
    reason: Any,
    silent: bool,
    previous: Any = None,
) -> None:
    ticket = await opened_card(interaction, ticket_id, previous)
    if ticket is None:
        return
    closed, why_not = await close_ticket(
        interaction.client,
        interaction.guild,
        ticket,
        by=interaction.user,
        reason=reason,
        silent=silent,
    )
    if not closed:
        await card_moved(
            interaction, ticket_id, previous, CLOSE_RACED.format(ticket_id=ticket_id)
        )
        return
    extra = "" if why_not is None else NO_TRANSCRIPT_SAID
    if silent:
        extra += SILENT_SAID
    await card_moved(
        interaction, ticket_id, previous, CLOSED_SAID.format(ticket_id=ticket_id, extra=extra)
    )


async def run_practice_message(
    interaction: discord.Interaction, ticket_id: int, text: Any
) -> None:
    ticket = await card_opened(interaction, ticket_id)
    if ticket is None:
        return
    outcome = await practice_message(
        interaction.client, interaction.guild, ticket, interaction.user, text
    )
    await answer(interaction, outcome.message)


async def run_card_end(interaction: discord.Interaction, ticket_id: int) -> None:
    ticket = await card_opened(interaction, ticket_id)
    if ticket is None:
        return
    closed, _ = await close_ticket(
        interaction.client,
        interaction.guild,
        ticket,
        by=interaction.user,
        reason=PRACTICE_REASON,
        silent=True,
    )
    if not closed:
        await answer(interaction, CLOSE_RACED.format(ticket_id=ticket_id))
        return
    await answer(interaction, PRACTICE_ENDED.format(ticket_id=ticket_id))


class SpeakAsMemberModal(AnswersErrors, discord.ui.Modal):
    """Practice only — the modal that stands in for the DM listener a real ticket has."""

    def __init__(self, ticket_id: int) -> None:
        super().__init__(title=SPEAK_TITLE)
        self.ticket_id = int(ticket_id)
        self.text = discord.ui.TextInput(
            style=discord.TextStyle.paragraph, max_length=CONTENT_LIMIT
        )
        self.add_item(discord.ui.Label(text=SPEAK_LABEL, component=self.text))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_practice_message(
            interaction, self.ticket_id, clamp(str(self.text), CONTENT_LIMIT)
        )


class ReplyModal(AnswersErrors, discord.ui.Modal):
    """F-M7: one modal — the snippet and the text COMBINE, exactly as `_body` combines them."""

    def __init__(
        self, ticket_id: int, rows: Any, *, anonymous: bool, previous: Any = None
    ) -> None:
        super().__init__(title=ANON_REPLY_TITLE if anonymous else REPLY_TITLE)
        self.ticket_id = int(ticket_id)
        self.anonymous = anonymous
        self.previous = previous
        self.text = discord.ui.TextInput(
            style=discord.TextStyle.paragraph, max_length=CONTENT_LIMIT, required=False
        )
        self.add_item(discord.ui.Label(text=REPLY_TEXT_LABEL, component=self.text))
        self.picker = snippet_picker(rows) if rows else None
        if self.picker is not None:
            self.add_item(discord.ui.Label(text=REPLY_SNIPPET_LABEL, component=self.picker))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        picked = picked_values(self.picker) if self.picker is not None else []
        await run_card_reply(
            interaction,
            self.ticket_id,
            clamp(str(self.text), CONTENT_LIMIT),
            picked[0] if picked else None,
            anonymous=self.anonymous,
            previous=self.previous,
        )


class CardNoteModal(NoteModal):
    def __init__(self, ticket_id: int, previous: Any = None) -> None:
        super().__init__(
            title=CARD_NOTE_TITLE,
            label=CARD_NOTE_LABEL,
            max_length=CONTENT_LIMIT,
            on_submit=self.taken,
        )
        self.ticket_id = int(ticket_id)
        self.previous = previous

    async def taken(self, interaction: discord.Interaction, text: str) -> None:
        await run_card_note(interaction, self.ticket_id, text, self.previous)


class CloseModal(AnswersErrors, discord.ui.Modal):
    def __init__(self, ticket_id: int, previous: Any = None) -> None:
        super().__init__(title=CLOSE_TITLE)
        self.ticket_id = int(ticket_id)
        self.previous = previous
        self.reason = discord.ui.TextInput(
            style=discord.TextStyle.paragraph, max_length=CLOSE_REASON_LIMIT, required=False
        )
        self.quiet = discord.ui.CheckboxGroup(
            options=[discord.CheckboxGroupOption(label=CLOSE_SILENT_OPTION, value="silent")],
            min_values=0,
            max_values=1,
            required=False,
        )
        self.add_item(discord.ui.Label(text=CLOSE_REASON_LABEL, component=self.reason))
        self.add_item(discord.ui.Label(text=CLOSE_SILENT_LABEL, component=self.quiet))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_card_close(
            interaction,
            self.ticket_id,
            clamp(str(self.reason), CLOSE_REASON_LIMIT).strip() or None,
            bool(picked_values(self.quiet)),
            self.previous,
        )


async def card_modal(
    interaction: discord.Interaction, action: str, ticket_id: int, *, previous: Any = None
) -> Any:
    """One table of which move opens which modal, whichever door the move was pressed on."""
    if action == CARD_NOTE:
        return CardNoteModal(ticket_id, previous)
    if action == CARD_CLOSE:
        return CloseModal(ticket_id, previous)
    if action == CARD_SPEAK:
        return SpeakAsMemberModal(ticket_id)
    rows = await all_snippets(interaction.client.db)
    return ReplyModal(ticket_id, rows, anonymous=action == CARD_ANON, previous=previous)


async def card_pressed(interaction: discord.Interaction, move: Any, ticket_id: int) -> None:
    """Every card move re-asks staff first: a ticket channel is visible to every staff role."""
    if not await still_staff(interaction):
        return
    if not await db_up(interaction):
        return
    if await card_ticket(interaction, ticket_id) is None:
        return
    if move.action == CARD_END:
        await run_card_end(interaction, ticket_id)
        return
    await interaction.response.send_modal(
        await card_modal(interaction, move.action, ticket_id)
    )


class TicketCardButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=CARD_TEMPLATE
):
    def __init__(self, move: Any, ticket_id: Any) -> None:
        self.move = move
        self.ticket_id = int(ticket_id)
        super().__init__(
            discord.ui.Button(
                label=move.label,
                style=STYLES[move.style],
                row=move.row,
                custom_id=card_custom_id(move.action, ticket_id),
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: Any):
        return cls(CARD_MOVE_BY_ACTION[match["action"]], int(match["ticket_id"]))

    async def on_click(self, interaction: discord.Interaction) -> None:
        await card_pressed(interaction, self.move, self.ticket_id)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Modmail(bot))
