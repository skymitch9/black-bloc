"""Sticky messages: the stored rows, the rules and the words, with no Discord in them."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, NamedTuple

import discord

from .panels import SELECT_OPTION_LIMIT
from .panels import panel_minutes as _panel_minutes
from .settings_store import (
    STICKY_AFTER_MESSAGES,
    STICKY_MIN_SECONDS,
    STICKY_MODE,
    STICKY_MODES,
    STICKY_PANEL_MINUTES,
    STICKY_SILENT,
)

FEATURE = "sticky"
LOG_FEATURE = "posts"
SITE_ANCHOR = "#sticky"
TEXT_MAX = 1800
PREVIEW_CHARS = 60
LOGGED_CHARS = 200
COUNTED_TYPES = (discord.MessageType.default, discord.MessageType.reply)
POSTABLE_KINDS = ("text", "news")

COLUMNS = (
    "guild_id, channel_id, text, paused, trouble, message_id, posted_channel_id, posted_at, "
    "reposts, created_by, created_at, updated_by, updated_at"
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
PAUSED_NOW = "Paused. The copy in <#{channel_id}> was taken down and the words are kept."
REMOVED_NOW = "Removed. <#{channel_id}> has no sticky message now."
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
TROUBLE_REFUSED = "Discord refused ({status}): {text}. Press Try again once that is sorted."
TROUBLE_OLD_COPY = (
    "The last copy could not be deleted — {reason} — so a new one was not posted on top of it. "
    "Press Try again once that is sorted."
)
TROUBLE_UNEXPECTED = "It could not be posted — {reason}. Press Try again."


def now_iso(at: datetime | None = None) -> str:
    return (at or datetime.now(UTC)).isoformat()


def clean(text: Any) -> str:
    return str(text or "").strip()


def text_refusal(text: str) -> str | None:
    if not text:
        return NO_WORDS
    if len(text) > TEXT_MAX:
        return TOO_LONG.format(given=len(text), limit=TEXT_MAX)
    return None


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


def state_of(row: Any, mode: str) -> str:
    if row["trouble"]:
        return STOPPED
    if row["paused"]:
        return PAUSED
    if mode == "off":
        return OFF
    if not row["message_id"]:
        return WAITING
    if int(row["posted_channel_id"] or 0) == int(row["channel_id"]):
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


def root_lines(rows: Any, mode: str) -> list[str]:
    lines = [MODE_LINE.format(mode=mode), ""]
    lines += [row_line(row, mode) for row in rows] or [NONE_YET]
    return lines


def mode_options(current: Any) -> list[tuple[str, str, bool]]:
    return [(name, MODE_LABELS[name], name == current) for name in STICKY_MODES]


def sticky_options(rows: Any, names: dict[int, str]) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    for row in rows:
        ident = int(row["channel_id"])
        name = names.get(ident)
        head = f"#{name}" if name else GONE_CHANNEL.format(ident=ident)
        found.append((f"{head} · {preview(row['text'])}"[:SELECT_OPTION_LIMIT], ident))
    return found


def card_buttons(row: Any) -> tuple[StickyMove, ...]:
    """A move the shared function would refuse is absent, never offered and refused."""
    found = [EDIT_MOVE]
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


async def write_words(db: Any, guild_id: int, channel_id: int, text: str, by: Any) -> bool:
    """True when this made the row; the words change and whatever stopped it is forgotten."""
    at = now_iso()
    made = await get_row(db, guild_id, channel_id) is None
    await db.conn.execute(
        "INSERT INTO sticky_messages(guild_id, channel_id, text, created_by, created_at, "
        "updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(guild_id, channel_id) DO UPDATE SET text = excluded.text, trouble = NULL, "
        "updated_by = excluded.updated_by, updated_at = excluded.updated_at",
        (int(guild_id), int(channel_id), text, by, at, by, at),
    )
    await db.conn.commit()
    return made


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


async def write_trouble(db: Any, guild_id: int, channel_id: int, trouble: str) -> None:
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
