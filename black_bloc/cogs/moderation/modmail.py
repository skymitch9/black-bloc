from __future__ import annotations

import asyncio
import io
import logging
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ...actionlog import log_action
from ...events import clamp
from ...golive import now_iso, parse_ts
from ...modmail import (
    AUTO_ARCHIVE_MINUTES,
    CLOSED,
    CONTENT_LIMIT,
    IN,
    NOTE,
    OPEN,
    OUT,
    SNIPPET_NAME_LIMIT,
    attachment_urls,
    closing_dm,
    count_directions,
    dump_attachments,
    header_embed,
    is_note,
    mentions,
    modes_sentence,
    note_body,
    opening_dm,
    relay_embed,
    thread_invite,
    thread_name,
    ticket_channel_name,
    ticket_topic,
    transcript_embed,
    transcript_filename,
    transcript_text,
    valid_snippet_name,
)
from ...settings_store import (
    CHANNEL_MODE,
    DB_UNAVAILABLE,
    GUILD_ONLY,
    MODMAIL_MODES,
    THREAD_MODE,
    require_staff,
    staff_roles_sentence,
)

log = logging.getLogger(__name__)

LOCKS_ATTR = "_modmail_locks"
RECONCILE_MINUTES = 5
ORPHAN_GRACE_MINUTES = 5
REFUSAL_COOLDOWN_MINUTES = 10
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
NO_CATEGORY = (
    "Black Bloc has nowhere to put ticket channels, so nothing was opened. A Lead points it at a "
    "category with `/modmail settings category:<the ModMail category>`."
)
NOT_A_CATEGORY = (
    "**modmail_category_id** points at something that is not a category, so nothing was opened. A "
    "Lead fixes it with `/modmail settings category:<the ModMail category>`."
)
NO_STAFF_CHANNEL = (
    "Black Bloc has nowhere to put ticket threads, so nothing was opened. A Lead points it at a "
    "channel with `/modmail settings staff_channel:<the staff channel>`, or switches back to "
    "channel mode with `/modmail mode channel`."
)
NO_TICKET_HERE = (
    "This channel is not a modmail ticket, so nothing was sent. Run the command inside a ticket, "
    "or name one with `ticket:<number>` — `/modmail status` lists the open ones."
)
MANY_OPEN = (
    "Black Bloc cannot tell which ticket you mean — {count} are open, so nothing was sent. Name "
    "one with `ticket:<number>`: {ids}."
)
NOT_A_TICKET_ID = "**{given}** is not a ticket number, so nothing was sent."
NO_SUCH_TICKET = (
    "Black Bloc has no record of ticket #{ticket_id} on this server, so nothing was sent. "
    "`/modmail status` lists the open ones."
)
TICKET_CLOSED = "Ticket #{ticket_id} is already closed, so nothing was sent."
NOTHING_TO_SEND = "Type some text or name a snippet — nothing was sent."
NO_SNIPPET = "There is no snippet called **{name}**, so nothing was sent. `/snippet list` has them."
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
BLOCKED_SAID = "**{who}** can no longer open modmail tickets. `/modmail unblock` undoes it."
ALREADY_BLOCKED = "**{who}** was already blocked, so nothing changed."
UNBLOCKED_SAID = "**{who}** can open modmail tickets again."
NOT_BLOCKED = "**{who}** was not blocked, so nothing changed."
NO_BLOCKS = "Nobody is blocked from modmail."
MODE_SET = (
    "New tickets from now on: {what}. The {count} ticket(s) already open keep the mode they were "
    "opened in — that is where their channel or thread already is."
)
BAD_SNIPPET_NAME = (
    "**{given}** is not a snippet name Black Bloc will take. Use lowercase letters, numbers, "
    f"dashes and underscores, up to {SNIPPET_NAME_LIMIT} characters — `ban-appeal`."
)
SNIPPET_SAVED = "Snippet **{name}** saved. `/reply snippet:{name}` sends it."
SNIPPET_GONE = "Snippet **{name}** is gone."
NO_SUCH_SNIPPET = "There is no snippet called **{name}**, so nothing was removed."
NO_SNIPPETS = "There are no snippets yet — `/snippet add` makes one."
NO_STAFF_WARNING = (
    "⚠️ **No staff roles resolve**, so a ticket channel would be visible to server admins only "
    "and a ticket thread would have nobody in it. Point `staff_channel_id` at a channel only "
    "staff can see with `/settings set staff_channel_id`, then run this again."
)


async def create_ticket(db: Any, guild_id: int, user_id: int, mode: str) -> int | None:
    cur = await db.conn.execute(
        "INSERT INTO modmail_tickets(guild_id, user_id, mode, channel_id, status, opened_at) "
        "VALUES (?, ?, ?, 0, ?, ?)",
        (guild_id, user_id, mode, OPEN, now_iso()),
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
    db: Any, ticket_id: int, *, by: int | None, reason: Any, log_message_id: int | None
) -> None:
    await db.conn.execute(
        "UPDATE modmail_tickets SET status = ?, closed_at = ?, closed_by = ?, close_reason = ?, "
        "log_message_id = ? WHERE id = ?",
        (CLOSED, now_iso(), by, clamp(reason, 400) or None, log_message_id, ticket_id),
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
    try:
        message = await target.send(
            content, embed=embed, allowed_mentions=allowed or mentions()
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


async def react(bot: Any, message: Any, emoji: str) -> None:
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(message.channel.id):
        return
    try:
        await message.add_reaction(emoji)
    except Exception as exc:
        log.info("modmail: could not react to %s: %s", getattr(message, "id", "?"), exc)


async def answer(interaction: discord.Interaction, text: str) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(text, ephemeral=True, allowed_mentions=mentions())
        return
    await interaction.response.send_message(text, ephemeral=True, allowed_mentions=mentions())


async def resolve_ticket(bot: Any, guild: Any, channel_id: Any, given: Any) -> tuple[Any, str]:
    """The ticket a staff command means: the one named, the one here, or the only one open."""
    if given:
        digits = str(given).strip().lstrip("#")
        if not digits.isdigit():
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


class Modmail(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._refused: dict[int, datetime] = {}
        self._gone: dict[int, int] = {}
        self.last_ok_at: str | None = None
        self.last_error: str | None = None

    modmail = app_commands.Group(name="modmail", description="Run the modmail inbox")

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
        existing = await open_ticket_for(self.bot.db, guild.id, user.id)
        if existing is not None:
            return existing, False
        mode = self.bot.store.get(guild.id, "modmail_mode")
        try:
            ticket_id = await create_ticket(self.bot.db, guild.id, user.id, mode)
        except sqlite3.IntegrityError:
            return await open_ticket_for(self.bot.db, guild.id, user.id), False
        place, why_not = await self._make_place(guild, user, ticket_id, mode)
        if place is None:
            await self._abandon(guild, user, ticket_id, why_not)
            return None, False
        await set_ticket_place(
            self.bot.db,
            ticket_id,
            place.id if mode == CHANNEL_MODE else getattr(place, "parent_id", place.id),
            place.id if mode == THREAD_MODE else None,
        )
        ticket = await get_ticket(self.bot.db, ticket_id)
        await log_action(
            self.bot,
            guild,
            "modmail.opened",
            target=user,
            details={"ticket_id": ticket_id, "mode": mode, "channel_id": place.id},
        )
        await self._post_header(guild, ticket, user, mode)
        return ticket, True

    async def _make_place(
        self, guild: Any, user: Any, ticket_id: int, mode: str
    ) -> tuple[Any, str | None]:
        if not self.bot.store.staff_roles(guild):
            return None, "no_staff_roles"
        if mode == THREAD_MODE:
            parent, where = thread_parent(self.bot, guild)
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
        category, where = ticket_category(self.bot, guild)
        if category is None:
            return None, where
        staff = self.bot.store.staff_roles(guild)
        try:
            return (
                await guild.create_text_channel(
                    ticket_channel_name(getattr(user, "name", user), ticket_id),
                    category=category,
                    topic=ticket_topic(user.id, ticket_id),
                    overwrites=ticket_overwrites(guild, staff, getattr(guild, "me", None)),
                    reason=f"Black Bloc modmail ticket {ticket_id}",
                ),
                None,
            )
        except discord.HTTPException as exc:
            return None, f"{type(exc).__name__}: {exc}"

    async def _abandon(self, guild: Any, user: Any, ticket_id: int, why_not: Any) -> None:
        await self.bot.db.conn.execute(
            "UPDATE modmail_tickets SET status = 'closed', closed_at = ?, close_reason = ? "
            "WHERE id = ?",
            (now_iso(), f"never_got_a_place: {why_not}", ticket_id),
        )
        await self.bot.db.conn.commit()
        log.warning("modmail: ticket %s got no channel — %s", ticket_id, why_not)
        await log_action(
            self.bot,
            guild,
            "modmail.open_failed",
            target=user,
            details={"ticket_id": ticket_id, "reason": str(why_not)},
        )

    async def _post_header(self, guild: Any, ticket: Any, user: Any, mode: str) -> None:
        member = guild.get_member(user.id)
        prior = max(await count_tickets(self.bot.db, guild.id, user.id) - 1, 0)
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
        role_ids = [role.id for role in self.bot.store.staff_roles(guild)]
        if mode == THREAD_MODE:
            await speak(
                self.bot,
                guild,
                ticket,
                content=thread_invite(
                    role_ids, ticket["id"], getattr(user, "display_name", str(user))
                ),
                embed=embed,
                allowed=mentions(role_ids),
            )
            return
        await speak(self.bot, guild, ticket, embed=embed)

    async def _relay_inbound(
        self, guild: Any, ticket: Any, message: discord.Message
    ) -> str | None:
        urls = attachment_urls(message.attachments)
        await add_message(
            self.bot.db,
            ticket["id"],
            message.author.id,
            IN,
            content=message.content,
            attachments=urls,
        )
        embed = relay_embed(
            IN,
            author_name=getattr(message.author, "display_name", str(message.author)),
            author_id=message.author.id,
            content=message.content,
            attachments=urls,
            icon_url=getattr(getattr(message.author, "display_avatar", None), "url", None),
        )
        _, why_not = await speak(self.bot, guild, ticket, embed=embed)
        if why_not is not None:
            await log_action(
                self.bot,
                guild,
                "modmail.relay_failed",
                target=message.author,
                details={"ticket_id": ticket["id"], "reason": why_not},
            )
        return why_not

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
        if is_note(message.content):
            body = note_body(message.content)
            await add_message(
                self.bot.db,
                ticket["id"],
                message.author.id,
                NOTE,
                content=body,
                attachments=attachment_urls(message.attachments),
            )
            await react(self.bot, message, NOTE_REACTION)
            return
        why_not = await self._send_reply(
            message.guild,
            ticket,
            message.author,
            message.content,
            attachments=attachment_urls(message.attachments),
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
    ) -> str | None:
        """One path for every staff reply, whether it came from a message or a command."""
        user = self.bot.get_user(ticket["user_id"]) or guild.get_member(ticket["user_id"])
        embed = relay_embed(
            OUT,
            author_name=getattr(author, "display_name", str(author)),
            author_id=author.id,
            content=content,
            attachments=attachments,
            anonymous=anonymous,
            colour=None
            if anonymous
            else getattr(getattr(author, "colour", None), "value", None),
            icon_url=None
            if anonymous
            else getattr(getattr(author, "display_avatar", None), "url", None),
        )
        row_id = await add_message(
            self.bot.db,
            ticket["id"],
            author.id,
            OUT,
            content=content,
            attachments=attachments,
            anonymous=anonymous,
        )
        why_not = (
            await deliver_dm(user, embed=embed) if user is not None else "member_not_visible"
        )
        if why_not is not None:
            await mark_undelivered(self.bot.db, row_id)
            await log_action(
                self.bot,
                guild,
                "modmail.dm_failed",
                actor=author,
                target=ticket["user_id"],
                details={"ticket_id": ticket["id"], "reason": why_not},
            )
            await speak(
                self.bot,
                guild,
                ticket,
                content=f"⚠️ Black Bloc could not DM the member — `{clamp(why_not, 200)}`",
                embed=embed,
            )
            return why_not
        if echo:
            await speak(self.bot, guild, ticket, embed=embed)
        return None

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
        if snippet:
            row = await get_snippet(self.bot.db, str(snippet).strip().lower())
            if row is None:
                await answer(interaction, NO_SNIPPET.format(name=clamp(snippet, 40)))
                return None
            return row["content"] if not text else f"{row['content']}\n\n{text}"
        if not str(text or "").strip():
            await answer(interaction, NOTHING_TO_SEND)
            return None
        return str(text)

    @app_commands.command(name="reply", description="Reply to the member in a modmail ticket")
    @app_commands.describe(
        text="What the member is sent",
        snippet="A saved reply to send instead — /snippet list has them",
        ticket="The ticket number, when you are not in its channel",
    )
    async def reply(
        self,
        interaction: discord.Interaction,
        text: str | None = None,
        snippet: str | None = None,
        ticket: str | None = None,
    ) -> None:
        await self._reply(interaction, text, snippet, ticket, anonymous=False)

    @app_commands.command(name="areply", description="Reply as Staff, without naming yourself")
    @app_commands.describe(
        text="What the member is sent",
        snippet="A saved reply to send instead — /snippet list has them",
        ticket="The ticket number, when you are not in its channel",
    )
    async def areply(
        self,
        interaction: discord.Interaction,
        text: str | None = None,
        snippet: str | None = None,
        ticket: str | None = None,
    ) -> None:
        await self._reply(interaction, text, snippet, ticket, anonymous=True)

    async def _reply(
        self,
        interaction: discord.Interaction,
        text: Any,
        snippet: Any,
        ticket: Any,
        *,
        anonymous: bool,
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
        why_not = await self._send_reply(
            interaction.guild, row, interaction.user, body, anonymous=anonymous
        )
        if why_not is not None:
            await answer(interaction, DM_FAILED_SAID)
            return
        await answer(
            interaction,
            SENT.format(who="Staff" if anonymous else interaction.user.display_name),
        )

    @app_commands.command(name="note", description="Leave a private note the member never sees")
    @app_commands.describe(
        text="The note", ticket="The ticket number, when you are not in its channel"
    )
    async def note(
        self, interaction: discord.Interaction, text: str, ticket: str | None = None
    ) -> None:
        if not await self._ready(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        row = await self._resolve(interaction, ticket)
        if row is None:
            return
        await add_message(
            self.bot.db, row["id"], interaction.user.id, NOTE, content=text
        )
        embed = relay_embed(
            NOTE,
            author_name=interaction.user.display_name,
            author_id=interaction.user.id,
            content=text,
        )
        _, why_not = await speak(self.bot, interaction.guild, row, embed=embed)
        said = NOTE_SAVED.format(ticket_id=row["id"])
        await answer(interaction, said if why_not is None else said + RELAY_FAILED_SAID)


    async def _close(
        self,
        guild: Any,
        ticket: Any,
        *,
        by: Any = None,
        reason: Any = None,
        silent: bool = False,
    ) -> tuple[bool, str | None]:
        """Transcript first, then the record, then the member, then the channel."""
        async with user_lock(self.bot, ticket["user_id"]):
            fresh = await get_ticket(self.bot.db, ticket["id"])
            if fresh is None or fresh["status"] != OPEN:
                return False, None
            rows = await ticket_messages(self.bot.db, fresh["id"])
            message_id, why_not = await self._post_transcript(
                guild, fresh, rows, by=by, reason=reason
            )
            await mark_closed(
                self.bot.db,
                fresh["id"],
                by=getattr(by, "id", by),
                reason=reason,
                log_message_id=message_id,
            )
            await log_action(
                self.bot,
                guild,
                "modmail.closed",
                actor=by,
                target=fresh["user_id"],
                reason=clamp(reason, 400) or None,
                details={"ticket_id": fresh["id"], "messages": len(rows)},
            )
            if not silent:
                user = self.bot.get_user(fresh["user_id"]) or guild.get_member(fresh["user_id"])
                if user is not None:
                    await deliver_dm(user, closing_dm(guild.name, reason))
            if why_not is None:
                await self._remove_place(guild, fresh)
            else:
                await log_action(
                    self.bot,
                    guild,
                    "modmail.place_kept",
                    details={"ticket_id": fresh["id"], "reason": why_not},
                )
            return True, why_not

    async def _post_transcript(
        self, guild: Any, ticket: Any, rows: Any, *, by: Any, reason: Any
    ) -> tuple[int | None, str | None]:
        member = guild.get_member(ticket["user_id"])
        label = getattr(member, "display_name", None) or str(ticket["user_id"])
        details = {"ticket_id": ticket["id"]}
        channel_id = self.bot.store.get(guild.id, "modmail_log_channel_id")
        channel = (
            (self.bot.get_channel(channel_id) or guild.get_channel(channel_id))
            if channel_id
            else None
        )
        if channel is None:
            await log_action(
                self.bot,
                guild,
                "modmail.transcript_failed",
                details=details | {"reason": "no_log_channel"},
            )
            return None, "no_log_channel"
        guard = getattr(self.bot, "guard", None)
        if guard is not None and not guard.allows_channel(channel.id):
            await log_action(
                self.bot,
                guild,
                "modmail.would_post_transcript",
                details=details | {"reason": "test_mode", "channel_id": channel.id},
            )
            return None, "test_mode"
        closed_at = now_iso()
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
        )
        file = discord.File(
            io.BytesIO(text.encode("utf-8")), filename=transcript_filename(ticket["id"])
        )
        try:
            message = await channel.send(embed=embed, file=file, allowed_mentions=mentions())
        except Exception as exc:
            log.warning("modmail: could not post the transcript for %s: %s", ticket["id"], exc)
            await log_action(
                self.bot,
                guild,
                "modmail.transcript_failed",
                details=details | {"reason": f"{type(exc).__name__}: {exc}"},
            )
            return None, f"{type(exc).__name__}: {exc}"
        await log_action(
            self.bot,
            guild,
            "modmail.transcript",
            target=ticket["user_id"],
            details=details | {"channel_id": channel.id},
        )
        return message.id, None

    async def _remove_place(self, guild: Any, ticket: Any) -> None:
        place, _ = await resolve_place(self.bot, guild, ticket)
        if place is None:
            return
        if not may_remove(self.bot, place):
            await log_action(
                self.bot,
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
                self.bot,
                guild,
                "modmail.remove_place_failed",
                details={
                    "ticket_id": ticket["id"],
                    "channel_id": place.id,
                    "reason": f"{type(exc).__name__}: {exc}",
                },
            )

    @app_commands.command(name="close", description="Close a ticket and file its transcript")
    @app_commands.describe(
        reason="What the member is told, and what the transcript records",
        silent="Close without telling the member",
        ticket="The ticket number, when you are not in its channel",
    )
    async def close(
        self,
        interaction: discord.Interaction,
        reason: str | None = None,
        silent: bool = False,
        ticket: str | None = None,
    ) -> None:
        if not await self._ready(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        row = await self._resolve(interaction, ticket)
        if row is None:
            return
        closed, why_not = await self._close(
            interaction.guild, row, by=interaction.user, reason=reason, silent=silent
        )
        if not closed:
            await answer(interaction, CLOSE_RACED.format(ticket_id=row["id"]))
            return
        extra = "" if why_not is None else NO_TRANSCRIPT_SAID
        if silent:
            extra += SILENT_SAID
        await answer(interaction, CLOSED_SAID.format(ticket_id=row["id"], extra=extra))

    async def cog_load(self) -> None:
        if not self.bot.db.is_connected:
            return
        await self.reconcile_tickets()
        self._reconcile_loop.start()

    async def cog_unload(self) -> None:
        self._reconcile_loop.cancel()

    @tasks.loop(minutes=RECONCILE_MINUTES)
    async def _reconcile_loop(self) -> None:
        if self.bot.db.is_connected:
            await self.reconcile_tickets()

    @_reconcile_loop.before_loop
    async def _before_reconcile(self) -> None:
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self.bot.db.is_connected:
            await self.reconcile_tickets()

    async def reconcile_tickets(self) -> None:
        """An open ticket whose channel or thread has gone is closed, with the reason recorded."""
        now = datetime.now(UTC)
        for guild in list(getattr(self.bot, "guilds", ())):
            for row in await open_tickets(self.bot.db, guild.id):
                await self._recheck(guild, row, now)

    async def _recheck(self, guild: Any, row: Any, now: datetime) -> None:
        if not row["channel_id"]:
            opened = parse_ts(row["opened_at"])
            if opened is not None and now - opened < timedelta(minutes=ORPHAN_GRACE_MINUTES):
                return
            await self._close(guild, row, reason="never_got_a_place", silent=True)
            return
        place, missing = await resolve_place(self.bot, guild, row)
        if place is None and missing == "gone":
            await self._close(guild, row, reason="ticket_channel_gone", silent=True)

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
        for row in await tickets_in_channel(self.bot.db, channel.id):
            await self._close(guild, row, reason="ticket_channel_deleted", silent=True)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread) -> None:
        if not self.bot.db.is_connected:
            return
        for row in await tickets_in_channel(self.bot.db, thread.id):
            await self._close(thread.guild, row, reason="ticket_thread_deleted", silent=True)

    @modmail.command(name="block", description="Stop someone opening modmail tickets")
    @app_commands.describe(user="Who to block", reason="Why, for the log")
    async def modmail_block(
        self, interaction: discord.Interaction, user: discord.User, reason: str | None = None
    ) -> None:
        if not await self._ready(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        who = getattr(user, "display_name", str(user))
        if await blocked_row(self.bot.db, user.id) is not None:
            await answer(interaction, ALREADY_BLOCKED.format(who=who))
            return
        await add_block(self.bot.db, user.id, interaction.user.id, reason)
        await answer(interaction, BLOCKED_SAID.format(who=who))
        await log_action(
            self.bot,
            interaction.guild,
            "modmail.blocked",
            actor=interaction.user,
            target=user,
            reason=clamp(reason, 400) or None,
        )

    @modmail.command(name="unblock", description="Let someone open modmail tickets again")
    @app_commands.describe(user="Who to unblock")
    async def modmail_unblock(self, interaction: discord.Interaction, user: discord.User) -> None:
        if not await self._ready(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        who = getattr(user, "display_name", str(user))
        if await blocked_row(self.bot.db, user.id) is None:
            await answer(interaction, NOT_BLOCKED.format(who=who))
            return
        await remove_block(self.bot.db, user.id)
        await answer(interaction, UNBLOCKED_SAID.format(who=who))
        await log_action(
            self.bot,
            interaction.guild,
            "modmail.unblocked",
            actor=interaction.user,
            target=user,
        )

    @modmail.command(name="blocked", description="Who cannot open modmail tickets")
    async def modmail_blocked(self, interaction: discord.Interaction) -> None:
        if not await self._ready(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        rows = await blocked_rows(self.bot.db)
        if not rows:
            await answer(interaction, NO_BLOCKS)
            return
        lines = [
            f"<@{row['user_id']}> — {row['reason'] or 'no reason given'} ({row['at'][:10]})"
            for row in rows
        ]
        await answer(interaction, "\n".join(lines))

    @modmail.command(name="mode", description="Whether new tickets are channels or threads")
    @app_commands.choices(
        mode=[app_commands.Choice(name=name, value=name) for name in MODMAIL_MODES]
    )
    async def modmail_mode(
        self, interaction: discord.Interaction, mode: app_commands.Choice[str]
    ) -> None:
        if not await self._ready(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        await self.bot.store.set(guild.id, "modmail_mode", mode.value, by=interaction.user.id)
        await answer(
            interaction,
            MODE_SET.format(
                what=modes_sentence(mode.value),
                count=len(await open_tickets(self.bot.db, guild.id)),
            ),
        )
        await log_action(
            self.bot,
            guild,
            "modmail.settings",
            actor=interaction.user,
            details={"modmail_mode": mode.value},
        )

    @modmail.command(name="status", description="What modmail is doing and where it is set up")
    async def modmail_status(self, interaction: discord.Interaction) -> None:
        if not await self._ready(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        await answer(interaction, "\n".join(await self._status_lines(interaction.guild)))

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

    @modmail.command(name="settings", description="Show or change how modmail is set up")
    @app_commands.describe(
        category="Where ticket channels are made",
        staff_channel="Where ticket threads are made",
        log_channel="Where a closed ticket's transcript is posted",
        enabled="True when Black Bloc answers DMs itself",
        mode="channel (one per ticket) or thread (private threads)",
    )
    @app_commands.choices(
        mode=[app_commands.Choice(name=name, value=name) for name in MODMAIL_MODES]
    )
    async def modmail_settings(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel | None = None,
        staff_channel: discord.TextChannel | None = None,
        log_channel: discord.TextChannel | None = None,
        enabled: bool | None = None,
        mode: app_commands.Choice[str] | None = None,
    ) -> None:
        if not await self._ready(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        changed: dict[str, Any] = {}
        for key, value in (
            ("modmail_category_id", category),
            ("modmail_staff_channel_id", staff_channel),
            ("modmail_log_channel_id", log_channel),
            ("modmail_enabled", enabled),
            ("modmail_mode", mode.value if mode is not None else None),
        ):
            if value is not None:
                changed[key] = await self.bot.store.set(
                    guild.id, key, value, by=interaction.user.id
                )
        await answer(interaction, "\n".join(await self._status_lines(guild)))
        if changed:
            await log_action(
                self.bot, guild, "modmail.settings", actor=interaction.user, details=changed
            )

    snippet = app_commands.Group(name="snippet", description="Saved modmail replies")

    @snippet.command(name="add", description="Save a reply you send often")
    @app_commands.describe(name="What to call it", content="What it says")
    async def snippet_add(
        self, interaction: discord.Interaction, name: str, content: str
    ) -> None:
        if not await self._ready(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        key = str(name).strip().lower()
        if not valid_snippet_name(key):
            await answer(interaction, BAD_SNIPPET_NAME.format(given=clamp(name, 40)))
            return
        await save_snippet(
            self.bot.db, key, clamp(content, CONTENT_LIMIT), interaction.user.id
        )
        await answer(interaction, SNIPPET_SAVED.format(name=key))
        await log_action(
            self.bot,
            interaction.guild,
            "modmail.snippet_saved",
            actor=interaction.user,
            details={"name": key},
        )

    @snippet.command(name="remove", description="Delete a saved reply")
    @app_commands.describe(name="Which one")
    async def snippet_remove(self, interaction: discord.Interaction, name: str) -> None:
        if not await self._ready(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        key = str(name).strip().lower()
        if not await remove_snippet(self.bot.db, key):
            await answer(interaction, NO_SUCH_SNIPPET.format(name=clamp(name, 40)))
            return
        await answer(interaction, SNIPPET_GONE.format(name=key))
        await log_action(
            self.bot,
            interaction.guild,
            "modmail.snippet_removed",
            actor=interaction.user,
            details={"name": key},
        )

    @snippet.command(name="list", description="Show the saved replies")
    async def snippet_list(self, interaction: discord.Interaction) -> None:
        if not await self._ready(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        rows = await all_snippets(self.bot.db)
        if not rows:
            await answer(interaction, NO_SNIPPETS)
            return
        await answer(
            interaction,
            "\n".join(f"**{row['name']}** — {clamp(row['content'], 120)}" for row in rows),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Modmail(bot))
