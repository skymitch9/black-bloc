"""Sticky messages: the stored rows, the rules and the words, with no Discord in them."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, NamedTuple

import discord

from .panels import SELECT_OPTION_LIMIT
from .panels import panel_minutes as _panel_minutes
from .settings_store import (
    STICKY_AFTER_MESSAGES,
    STICKY_MAX_BURIED_MINUTES,
    STICKY_MIN_SECONDS,
    STICKY_MODE,
    STICKY_MODES,
    STICKY_PANEL_MINUTES,
    STICKY_PIN_COPIES,
    STICKY_QUIET_SECONDS,
    STICKY_SILENT,
)

FEATURE = "sticky"
LOG_FEATURE = "posts"
SITE_ANCHOR = "#sect-sticky"
TEXT_MAX = 1800
PREVIEW_CHARS = 60
LOGGED_CHARS = 200
COUNTED_TYPES = (discord.MessageType.default, discord.MessageType.reply)
POSTABLE_KINDS = ("text", "news")
DISCORD_LIMIT = 2000
CUT = "…"
MESSAGE_LINK = "https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"

COLUMNS = (
    "guild_id, channel_id, text, paused, trouble, message_id, posted_channel_id, posted_at, "
    "reposts, created_by, created_at, updated_by, updated_at, post_id, "
    "(SELECT title FROM posts WHERE posts.id = sticky_messages.post_id) AS post_title, "
    "(SELECT slug FROM posts WHERE posts.id = sticky_messages.post_id) AS post_slug"
)

LIVE = "live"
REHEARSING = "rehearsing"
WAITING = "waiting"
PAUSED = "paused"
STOPPED = "stopped"
OFF = "off"
STATE_WORDS: dict[str, str] = {
    LIVE: "live",
    REHEARSING: "rehearsing",
    WAITING: "waiting",
    PAUSED: "paused",
    STOPPED: "stopped",
    OFF: "off",
}

PANEL_TITLE = "Sticky messages"
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /sticky again"
NONE_YET = "No channel has a sticky message."
MODE_LINE = "**mode** — {mode}"
ROW_LINE = "<#{channel_id}> — {state}"
ROW_MOVED = " · moved {n}×"
ROW_SINCE = " · <t:{at}:R>"
ROW_TROUBLE = " — {trouble}"
GONE_CHANNEL = "a channel Discord no longer has ({ident})"
CARD_TITLE = "#{name}"

MODE_LABELS: dict[str, str] = {
    "off": "off — every copy is taken down, the words are kept",
    "shadow": "shadow — copies go to the rehearsal home only",
    "on": "on — each one is kept at the bottom of its channel",
}
MODE_PLACEHOLDER = "What sticky messages do…"
POST_PLACEHOLDER = "Keep a post at the bottom of a channel…"
SWAP_PLACEHOLDER = "Keep a different post here…"
WHERE_PLACEHOLDER = "The channel it stays at the bottom of…"
WHERE_TITLE = "{title}"
PICK_PLACEHOLDER = "A sticky message…"
ADD_PLACEHOLDER = "Add or edit one in a channel…"
WORDS_TITLE = "Sticky message"
WORDS_LABEL = "What it says"

EDIT = "edit"
PAUSE = "pause"
RESUME = "resume"
RETRY = "retry"
REMOVE = "remove"
BACK = "back"
REFRESH = "refresh"
LOGS = "logs"
SITE = "site"


class StickyMove(NamedTuple):
    action: str
    label: str
    style: str = "secondary"
    row: int = 0


EDIT_MOVE = StickyMove(EDIT, "Edit…", "primary")
PAUSE_MOVE = StickyMove(PAUSE, "Pause")
RESUME_MOVE = StickyMove(RESUME, "Resume", "success")
RETRY_MOVE = StickyMove(RETRY, "Try again", "success")
REMOVE_MOVE = StickyMove(REMOVE, "Remove", "danger")
BACK_MOVE = StickyMove(BACK, "Back", row=1)
REFRESH_MOVE = StickyMove(REFRESH, "Refresh", row=3)
LOGS_MOVE = StickyMove(LOGS, "Logs", row=3)
SITE_MOVE = StickyMove(SITE, "Open on the site", "link", row=3)

REMOVE_QUESTION = "Remove the sticky message from <#{channel_id}>? Its words are deleted too."
REMOVE_YES = "Remove it"

MODE_SET = "Sticky messages are now **{mode}**."
SAVED_LIVE = "Saved. It is at the bottom of <#{channel_id}> now."
SAVED_REHEARSED = (
    "Saved. Sticky messages are in **shadow**, so nothing was posted in <#{channel_id}> — the "
    "rehearsal copy is in <#{home}>."
)
SAVED_PAUSED = "Saved. It is paused, so nothing was posted — press **Resume** when it should run."
SAVED_OFF = (
    "Saved. Sticky messages are **off**, so nothing was posted — set `sticky_mode` to shadow or "
    "on when it should run."
)
SAVED_TEST_MODE = (
    "Saved. Black Bloc is in test mode, so it refused to post outside the test channel and "
    "logged what it would have done."
)
SAVED_BUT = "Saved, but it could not be posted: {trouble}"
SAVED_UNREACHABLE = "Saved, but it is not posted yet: {reason}"
SAVED_OWN_HOME = (
    "Saved. Sticky messages are in **shadow** and <#{channel_id}> is the rehearsal home itself, "
    "so nothing was posted there. Set `sticky_shadow_channel_id` to another channel to see a "
    "rehearsal copy, or set `sticky_mode` to on."
)
PAUSED_NOW = "Paused. The copy in <#{where}> was taken down and the words are kept."
PAUSED_NO_COPY = "Paused. No copy was up, and the words are kept."
PAUSED_COPY_LEFT = (
    "Paused, so it will not move again, but the copy is still in <#{where}>: {reason}. Delete "
    "it by hand — {link} — or give Black Bloc what it is missing there and press **Resume**, "
    "then **Pause**."
)
REMOVED_NOW = "Removed. <#{channel_id}> has no sticky message now."
REMOVED_COPY_LEFT = (
    "Removed, and the words are deleted, but its last copy is still in <#{where}>: {reason}. "
    "Black Bloc no longer tracks that message, so delete it by hand — {link}"
)
NO_STICKY = (
    "That channel has no sticky message, so nothing was changed. The list on this panel and on "
    "the Posts page is every channel that has one."
)
ALREADY_PAUSED = "That sticky message is already paused, so nothing was changed."
NOT_PAUSED = (
    "That sticky message is already running, so nothing was changed. **Pause** is the move that "
    "takes it down."
)
NO_WORDS = (
    "A sticky message needs some words, so nothing was saved. Type what it should say and save "
    "again."
)
NOT_WORDS = (
    "The words of a sticky message have to be plain text, so nothing was saved. Type what it "
    "should say and save again."
)
TOO_LONG = (
    "That is {given} characters and a sticky message holds {limit}, so nothing was saved. "
    "Shorten it and save again."
)
NO_SUCH_CHANNEL = (
    "Black Bloc cannot find that channel in this server, so nothing was saved. Pick a channel it "
    "can see."
)
NOT_POSTABLE = (
    "<#{channel_id}> is not a text channel, so a sticky message cannot sit in it and nothing was "
    "saved. Pick a text or announcement channel."
)

POST_WORDS = "The post **{title}**"
POST_GONE_WORDS = "a post that has been deleted"
NO_SUCH_POST = (
    "There is no post called **{slug}**, so nothing was saved. Pick one from the Posts page's list."
)
POST_CARRIES_DOOR = (
    "**{title}** carries the front door, which keeps its own place, so it cannot be a sticky "
    "message and nothing was saved."
)
POST_HELD = (
    "**{title}** is already the sticky message in <#{channel_id}>, so nothing was saved. Remove it "
    "there first."
)
POST_IS_UP = (
    "**{title}** is posted already, so nothing was saved. Take it down on the Posts page first; "
    "the sticky message then posts it here."
)
POST_IS_EMPTY = (
    "**{title}** has no words and no block to show, so nothing was saved. Give it some on the "
    "Posts page first."
)
POST_REPLACED = "{channel} now keeps the post **{title}** at the bottom."
TROUBLE_POST_GONE = "Its post has been deleted. Pick another post or remove this sticky message."
TROUBLE_POST_EMPTY = (
    "Its post has no words and no block to show. Give it some on the Posts page, then press Try "
    "again."
)
TROUBLE_CHANNEL_GONE = "Discord no longer has that channel. Remove this sticky message."
TROUBLE_NO_HOME = (
    "There is no rehearsal home to post the copy in. Set `shadow_channel_id` or "
    "`sticky_shadow_channel_id`, then press Try again."
)
TROUBLE_HOME_GONE = (
    "The rehearsal home <#{home}> cannot be found. Set `sticky_shadow_channel_id` to a channel "
    "Black Bloc can see, then press Try again."
)
TROUBLE_PERMISSION = (
    "Black Bloc is missing {missing} in <#{channel_id}>. Give it that permission there, then "
    "press Try again."
)
REFUSED_WHY = "Discord refused ({status}): {text}"
TROUBLE_REFUSED = REFUSED_WHY + ". Press Try again once that is sorted."
TROUBLE_OLD_COPY = (
    "The last copy could not be deleted — {reason} — so a new one was not posted on top of it. "
    "Press Try again once that is sorted."
)
TROUBLE_UNEXPECTED = "It could not be posted — {reason}. Press Try again."
UNREACHABLE_WHY = "Discord could not be reached ({why})"
UNREACHABLE_ANSWERED = "it answered {status}"
UNREACHABLE_REASON = (
    UNREACHABLE_WHY + ". Black Bloc tries again by itself at the next message in <#{channel_id}>."
)
HOME_TROUBLES = re.compile(
    "|".join(
        re.escape(words).replace(re.escape("{home}"), r"\d+")
        for words in (TROUBLE_NO_HOME, TROUBLE_HOME_GONE)
    )
)


def now_iso(at: datetime | None = None) -> str:
    return (at or datetime.now(UTC)).isoformat()


def is_post(row: Any) -> bool:
    return bool(row["post_id"])


def words_of(row: Any) -> str:
    """What a sticky shows: staff's own words, or which post it keeps at the bottom."""
    if not is_post(row):
        return str(row["text"] or "")
    title = row["post_title"]
    return POST_WORDS.format(title=title) if title else POST_GONE_WORDS


def clean(text: Any) -> str:
    return str(text or "").strip()


def text_refusal(text: str) -> str | None:
    if not text:
        return NO_WORDS
    if len(text) > TEXT_MAX:
        return TOO_LONG.format(given=len(text), limit=TEXT_MAX)
    return None


def is_home_trouble(trouble: Any) -> bool:
    return bool(trouble) and HOME_TROUBLES.fullmatch(str(trouble)) is not None


def fit(note: str, words: str, limit: int = DISCORD_LIMIT) -> str:
    """The note shortens to make room; the words staff wrote are never cut."""
    if not note:
        return words
    room = limit - len(words) - 1
    if room < len(CUT) + 1:
        return words
    if len(note) > room:
        note = note[: room - len(CUT)].rstrip() + CUT
    return f"{note}\n{words}"


def message_link(guild_id: Any, channel_id: Any, message_id: Any) -> str:
    return MESSAGE_LINK.format(
        guild_id=int(guild_id), channel_id=int(channel_id), message_id=int(message_id)
    )


def postable(channel: Any) -> bool:
    kind = getattr(getattr(channel, "type", None), "name", None)
    if kind is None:
        return callable(getattr(channel, "send", None))
    return kind in POSTABLE_KINDS


def counts(message: Any) -> bool:
    """A person's own message, and nothing a bot, a webhook or Discord itself wrote."""
    if getattr(message, "guild", None) is None:
        return False
    if getattr(message, "webhook_id", None) is not None:
        return False
    if getattr(message, "type", None) not in COUNTED_TYPES:
        return False
    return not getattr(getattr(message, "author", None), "bot", False)


def is_running(row: Any) -> bool:
    return row is not None and not row["paused"] and not row["trouble"]


def seconds_since(row: Any, now: datetime) -> float | None:
    """None when there is no usable time on the row, which never holds a copy back."""
    try:
        posted = datetime.fromisoformat(str(row["posted_at"]))
    except (TypeError, ValueError):
        return None
    if posted.tzinfo is None:
        posted = posted.replace(tzinfo=UTC)
    return (now - posted).total_seconds()


def seconds_left(row: Any, now: datetime, gap: int) -> float:
    since = seconds_since(row, now)
    if since is None or since < 0:
        return 0.0
    return max(0.0, float(gap) - since)


def quiet_left(
    now: datetime,
    heard_at: datetime | None,
    reached_at: datetime | None,
    quiet: int,
    ceiling_minutes: int,
) -> float:
    """Seconds of quiet still owed since the last counted message; the ceiling cuts it short."""
    if quiet <= 0 or heard_at is None:
        return 0.0
    left = float(quiet) - (now - heard_at).total_seconds()
    if ceiling_minutes > 0 and reached_at is not None:
        left = min(left, float(ceiling_minutes) * 60 - (now - reached_at).total_seconds())
    return max(0.0, left)


def due_in(floor_left: float, quiet: float) -> float:
    """The gap since the last copy is a floor that neither the quiet nor the ceiling lowers."""
    return max(0.0, float(floor_left), float(quiet))


def state_of(row: Any, mode: str) -> str:
    if row["trouble"]:
        return STOPPED
    if row["paused"]:
        return PAUSED
    if mode == "off":
        return OFF
    if not row["message_id"]:
        return WAITING
    if mode != "shadow" and int(row["posted_channel_id"] or 0) == int(row["channel_id"]):
        return LIVE
    return REHEARSING


def preview(text: Any, limit: int = PREVIEW_CHARS) -> str:
    flat = " ".join(str(text or "").split())
    return flat if len(flat) <= limit else flat[: max(0, limit - 1)] + "…"


def posted_epoch(row: Any) -> int | None:
    try:
        return int(datetime.fromisoformat(str(row["posted_at"])).timestamp())
    except (TypeError, ValueError):
        return None


def numbers_waiting(store: Any, guild_id: int) -> tuple[int, int]:
    return (
        int(store.get(guild_id, STICKY_QUIET_SECONDS)),
        int(store.get(guild_id, STICKY_MAX_BURIED_MINUTES)),
    )


def pins(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, STICKY_PIN_COPIES))


def row_line(row: Any, mode: str) -> str:
    state = state_of(row, mode)
    line = ROW_LINE.format(channel_id=row["channel_id"], state=STATE_WORDS[state])
    if state in (LIVE, REHEARSING):
        at = posted_epoch(row)
        if at is not None:
            line += ROW_SINCE.format(at=at)
        if row["reposts"]:
            line += ROW_MOVED.format(n=row["reposts"])
    if row["trouble"]:
        line += ROW_TROUBLE.format(trouble=row["trouble"])
    return line


def root_lines(rows: Any, mode: str, modes: dict[int, str] | None = None) -> list[str]:
    """Each row is read against its own mode; a post owned by another feature follows that one."""
    each = modes or {}
    lines = [MODE_LINE.format(mode=mode), ""]
    lines += [row_line(row, each.get(int(row["channel_id"]), mode)) for row in rows] or [NONE_YET]
    return lines


def mode_options(current: Any) -> list[tuple[str, str, bool]]:
    return [(name, MODE_LABELS[name], name == current) for name in STICKY_MODES]


def sticky_options(rows: Any, names: dict[int, str]) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    for row in rows:
        ident = int(row["channel_id"])
        name = names.get(ident)
        head = f"#{name}" if name else GONE_CHANNEL.format(ident=ident)
        found.append((f"{head} · {preview(words_of(row))}"[:SELECT_OPTION_LIMIT], ident))
    return found


def post_options(rows: Any, but: Any = None) -> list[tuple[str, int]]:
    """Posts a sticky may keep: not the front door's carrier, not the one already here."""
    return [
        (str(row["title"] or row["slug"])[:SELECT_OPTION_LIMIT], int(row["id"]))
        for row in rows
        if not row["carries_door"] and int(row["id"]) != int(but or 0)
    ]


def card_buttons(row: Any) -> tuple[StickyMove, ...]:
    """A move the shared function would refuse is absent; a post's words are edited as a post."""
    found = [] if is_post(row) else [EDIT_MOVE]
    if row["trouble"]:
        found.append(RETRY_MOVE)
    elif row["paused"]:
        found.append(RESUME_MOVE)
    else:
        found.append(PAUSE_MOVE)
    found += [REMOVE_MOVE, BACK_MOVE]
    return tuple(found)


def root_buttons(*, has_site: bool) -> tuple[StickyMove, ...]:
    found = [REFRESH_MOVE, LOGS_MOVE]
    if has_site:
        found.append(SITE_MOVE)
    return tuple(found)


def panel_minutes(store: Any, guild_id: int) -> int:
    return _panel_minutes(store, guild_id, STICKY_PANEL_MINUTES)


def numbers(store: Any, guild_id: int) -> tuple[int, int, bool]:
    return (
        int(store.get(guild_id, STICKY_AFTER_MESSAGES)),
        int(store.get(guild_id, STICKY_MIN_SECONDS)),
        bool(store.get(guild_id, STICKY_SILENT)),
    )


def mode_of(store: Any, guild_id: int) -> str:
    return str(store.get(guild_id, STICKY_MODE))


async def get_row(db: Any, guild_id: int, channel_id: int) -> Any:
    cur = await db.conn.execute(
        f"SELECT {COLUMNS} FROM sticky_messages WHERE guild_id = ? AND channel_id = ?",
        (int(guild_id), int(channel_id)),
    )
    return await cur.fetchone()


async def rows_for_guild(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        f"SELECT {COLUMNS} FROM sticky_messages WHERE guild_id = ? ORDER BY created_at, channel_id",
        (int(guild_id),),
    )
    return list(await cur.fetchall())


async def running_channels(db: Any) -> list[tuple[int, int]]:
    cur = await db.conn.execute(
        "SELECT guild_id, channel_id FROM sticky_messages WHERE paused = 0 AND trouble IS NULL"
    )
    return [(int(row["guild_id"]), int(row["channel_id"])) for row in await cur.fetchall()]


async def write_words(
    db: Any, guild_id: int, channel_id: int, text: str, by: Any, *, post_id: Any = None
) -> bool:
    """True when this made the row; the words (or the post) change and any stop is forgotten."""
    at = now_iso()
    made = await get_row(db, guild_id, channel_id) is None
    await db.conn.execute(
        "INSERT INTO sticky_messages(guild_id, channel_id, text, post_id, created_by, created_at, "
        "updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(guild_id, channel_id) DO UPDATE SET text = excluded.text, "
        "post_id = excluded.post_id, trouble = NULL, "
        "updated_by = excluded.updated_by, updated_at = excluded.updated_at",
        (int(guild_id), int(channel_id), text, int(post_id) if post_id else None, by, at, by, at),
    )
    await db.conn.commit()
    return made


async def row_of_post(db: Any, post_id: Any) -> Any:
    """The sticky that keeps this post at the bottom, if one does."""
    cur = await db.conn.execute(
        f"SELECT {COLUMNS} FROM sticky_messages WHERE post_id = ? LIMIT 1", (int(post_id),)
    )
    return await cur.fetchone()


async def write_paused(db: Any, guild_id: int, channel_id: int, paused: bool, by: Any) -> None:
    await db.conn.execute(
        "UPDATE sticky_messages SET paused = ?, trouble = NULL, updated_by = ?, updated_at = ? "
        "WHERE guild_id = ? AND channel_id = ?",
        (1 if paused else 0, by, now_iso(), int(guild_id), int(channel_id)),
    )
    await db.conn.commit()


async def write_copy(
    db: Any,
    guild_id: int,
    channel_id: int,
    message_id: int | None,
    posted_channel_id: int | None,
    *,
    moved: bool = False,
    at: datetime | None = None,
) -> None:
    await db.conn.execute(
        "UPDATE sticky_messages SET message_id = ?, posted_channel_id = ?, posted_at = ?, "
        "reposts = reposts + ? WHERE guild_id = ? AND channel_id = ?",
        (
            message_id,
            posted_channel_id,
            now_iso(at) if message_id else None,
            1 if moved else 0,
            int(guild_id),
            int(channel_id),
        ),
    )
    await db.conn.commit()


async def write_trouble(db: Any, guild_id: int, channel_id: int, trouble: str | None) -> None:
    await db.conn.execute(
        "UPDATE sticky_messages SET trouble = ? WHERE guild_id = ? AND channel_id = ?",
        (trouble, int(guild_id), int(channel_id)),
    )
    await db.conn.commit()


async def delete_row(db: Any, guild_id: int, channel_id: int) -> bool:
    cur = await db.conn.execute(
        "DELETE FROM sticky_messages WHERE guild_id = ? AND channel_id = ?",
        (int(guild_id), int(channel_id)),
    )
    await db.conn.commit()
    return bool(cur.rowcount)
