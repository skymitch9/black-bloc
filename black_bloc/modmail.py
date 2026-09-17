from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any, NamedTuple

import discord

from .events import clamp, slugify
from .golive import parse_ts
from .panels import KEEP_IT
from .settings_store import (
    CHANNEL_MODE,
    FORUM_MODE,
    MODMAIL_BOTH,
    MODMAIL_BUTTONS,
    MODMAIL_PANEL_TEXT_DEFAULT,
    MODMAIL_PANEL_TITLE_DEFAULT,
    MODMAIL_TYPING,
    THREAD_MODE,
)
from .timezones import stamp

IN = "in"
OUT = "out"
NOTE = "note"
DIRECTIONS = (IN, OUT, NOTE)

OPEN = "open"
CLOSED = "closed"

NOTE_PREFIX = "="
ANONYMOUS_NAME = "Staff"
AUTO_ARCHIVE_MINUTES = 1440

CONTENT_LIMIT = 3800
FIELD_LIMIT = 1024
NAME_LIMIT = 100
SNIPPET_NAME_LIMIT = 40
MESSAGE_LIMIT = 1900
TRANSCRIPT_BYTES = 7_000_000
TRUNCATED_MARK = "\n\n… truncated — this ticket is longer than one transcript file can hold.\n"
UNDELIVERED_MARK = "(not delivered)"
ATTACHMENTS_EXPIRE = "Attachment links stop working about 24 hours after they were posted."

COLOURS: dict[str, int] = {IN: 0x5865F2, OUT: 0x57F287, NOTE: 0x99AAB5}
TITLES: dict[str, str] = {
    IN: "From the member",
    OUT: "Sent to the member",
    NOTE: "Private note",
}
LABELS: dict[str, str] = {IN: "MEMBER", OUT: "STAFF", NOTE: "NOTE"}

TOPIC_TEMPLATE = "Black Bloc modmail | user {user_id} | ticket {ticket_id}"
TOPIC_PATTERN = re.compile(r"Black Bloc modmail \| user (\d+) \| ticket (\d+)")
THREAD_NAME_TEMPLATE = "{name} · #{ticket_id}"
TRANSCRIPT_NAME = "modmail-ticket-{ticket_id}.txt"
PRACTICE_TRANSCRIPT_NAME = "modmail-practice-ticket-{ticket_id}.txt"
PRACTICE_MARK = "PRACTICE — a fake ticket. Nothing in it reached a member and no DM was sent."
NO_TEXT = "(no text)"

SNIPPET_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")


def chunk_lines(lines: Any, limit: int = MESSAGE_LIMIT) -> list[str]:
    """Discord refuses a message over 2000 characters, so a long list becomes several."""
    chunks: list[str] = []
    current = ""
    for line in lines or ():
        piece = clamp(line, limit)
        if current and len(current) + 1 + len(piece) > limit:
            chunks.append(current)
            current = piece
        else:
            current = f"{current}\n{piece}" if current else piece
    if current:
        chunks.append(current)
    return chunks


def field_of(row: Any, key: str, default: Any = None) -> Any:
    """One column of a row that may predate it, without pretending a missing column is False."""
    try:
        value = row[key]
    except (KeyError, IndexError):
        return default
    return default if value is None else value


def clamp_bytes(text: Any, limit: int = TRANSCRIPT_BYTES) -> str:
    """Discord bounds an upload in BYTES, so the cut is made in bytes and said out loud."""
    body = str(text or "")
    raw = body.encode("utf-8")
    if len(raw) <= limit:
        return body
    mark = TRUNCATED_MARK.encode("utf-8")
    return raw[: max(limit - len(mark), 0)].decode("utf-8", "ignore") + TRUNCATED_MARK


def ticket_channel_name(user_name: Any, ticket_id: Any) -> str:
    """The incumbent's shape: the member's name, lowercased to Discord's rules."""
    slug = slugify(user_name)[:NAME_LIMIT].strip("-")
    return slug or f"ticket-{ticket_id}"


def ticket_topic(user_id: Any, ticket_id: Any, subject: Any = None) -> str:
    """What the member called it goes first; `parse_topic` still finds the ids behind it."""
    line = TOPIC_TEMPLATE.format(user_id=int(user_id), ticket_id=int(ticket_id))
    said = clamp(str(subject or "").strip(), NAME_LIMIT)
    return f"{said} — {line}" if said else line


def parse_topic(topic: Any) -> tuple[int, int] | None:
    """The user and ticket ids a ticket channel carries, or None if it is not ours."""
    match = TOPIC_PATTERN.search(str(topic or ""))
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def thread_name(user_name: Any, ticket_id: Any) -> str:
    name = str(user_name or "").strip() or f"ticket-{ticket_id}"
    return THREAD_NAME_TEMPLATE.format(name=name, ticket_id=ticket_id)[:NAME_LIMIT]


def is_note(content: Any) -> bool:
    return str(content or "").lstrip().startswith(NOTE_PREFIX)


def note_body(content: Any) -> str:
    text = str(content or "").lstrip()
    return text[len(NOTE_PREFIX) :].strip() if text.startswith(NOTE_PREFIX) else text.strip()


def valid_snippet_name(name: Any) -> bool:
    return SNIPPET_NAME_PATTERN.match(str(name or "").strip().lower()) is not None


def attachment_urls(attachments: Any) -> list[str]:
    urls: list[str] = []
    for item in attachments or ():
        url = getattr(item, "url", None) or (item if isinstance(item, str) else None)
        if url:
            urls.append(str(url))
    return urls


def dump_attachments(urls: Any) -> str | None:
    found = [str(u) for u in urls or ()]
    return json.dumps(found) if found else None


def load_attachments(raw: Any) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list | tuple):
        return [str(u) for u in raw]
    try:
        parsed = json.loads(str(raw))
    except (TypeError, ValueError):
        return []
    return [str(u) for u in parsed] if isinstance(parsed, list) else []


def attachment_field(urls: Any) -> str:
    return clamp("\n".join(str(u) for u in urls or ()), FIELD_LIMIT)


def mentions(role_ids: Any = ()) -> discord.AllowedMentions:
    """Nothing a member or a staffer typed may ping; only the staff roles named here may."""
    roles = [discord.Object(int(role_id)) for role_id in role_ids or ()]
    return discord.AllowedMentions(everyone=False, users=False, roles=roles or False)


def staff_ping(role_ids: Any = ()) -> str:
    return " ".join(f"<@&{int(role_id)}>" for role_id in role_ids or ())


def relay_embed(
    direction: str,
    *,
    author_name: Any,
    author_id: Any,
    content: Any = None,
    attachments: Any = (),
    anonymous: bool = False,
    colour: Any = None,
    icon_url: Any = None,
    at: datetime | None = None,
) -> discord.Embed:
    """The one embed every relayed message becomes, whichever way it is going."""
    hidden = direction == OUT and anonymous
    shown = ANONYMOUS_NAME if hidden else str(author_name or "someone")
    embed = discord.Embed(
        title=TITLES.get(direction, direction),
        description=clamp(content, CONTENT_LIMIT) or f"*{NO_TEXT}*",
        colour=int(colour) if colour and not hidden else COLOURS.get(direction, COLOURS[IN]),
        timestamp=at or datetime.now(UTC),
    )
    embed.set_author(name=clamp(shown, NAME_LIMIT), icon_url=icon_url or None)
    urls = attachment_urls(attachments)
    if urls:
        embed.add_field(name="Attachments", value=attachment_field(urls), inline=False)
    if not hidden:
        embed.set_footer(text=f"{shown} · {author_id}")
    return embed


def header_embed(
    *,
    ticket_id: Any,
    user_id: Any,
    user_label: Any,
    mode: str = CHANNEL_MODE,
    created_at: datetime | None = None,
    joined_at: datetime | None = None,
    roles: Any = (),
    prior_tickets: int = 0,
) -> discord.Embed:
    """Who this is, posted once at the top of a ticket."""
    embed = discord.Embed(
        title=f"Ticket #{ticket_id}",
        description=f"<@{int(user_id)}> — {clamp(user_label, NAME_LIMIT)}",
        colour=COLOURS[IN],
    )
    embed.add_field(
        name="Account made",
        value=stamp(created_at) if created_at else "unknown",
        inline=False,
    )
    embed.add_field(
        name="Joined the server",
        value=stamp(joined_at) if joined_at else "not in the server",
        inline=False,
    )
    embed.add_field(name="Roles", value=role_field(roles), inline=False)
    embed.add_field(name="Earlier tickets", value=str(int(prior_tickets)), inline=True)
    embed.add_field(name="Mode", value=mode, inline=True)
    embed.set_footer(text=f"user {int(user_id)}")
    return embed


def role_field(roles: Any) -> str:
    names = [f"<@&{int(getattr(role, 'id', role))}>" for role in roles or ()]
    return clamp(", ".join(names), FIELD_LIMIT) if names else "none"


def count_directions(rows: Any) -> dict[str, int]:
    counts = dict.fromkeys(DIRECTIONS, 0)
    for row in rows or ():
        direction = str(row["direction"])
        if direction in counts:
            counts[direction] += 1
    return counts


def transcript_line(row: Any) -> str:
    when = parse_ts(row["at"])
    shown = when.strftime("%Y-%m-%d %H:%M:%S UTC") if when else str(row["at"])
    direction = str(row["direction"])
    who = f"{LABELS.get(direction, direction)} {row['author_id']}"
    if direction == OUT and row["anonymous"]:
        who = f"{who} (anonymous)"
    if direction == OUT and not field_of(row, "delivered", 1):
        who = f"{who} {UNDELIVERED_MARK}"
    body = str(row["content"] or "").strip() or NO_TEXT
    lines = [f"[{shown}] {who}: {body}"]
    lines += [f"    attachment: {url}" for url in load_attachments(row["attachments"])]
    return "\n".join(lines)


def transcript_text(
    rows: Any,
    *,
    ticket_id: Any,
    user_id: Any,
    user_label: Any,
    guild_name: Any,
    mode: str = CHANNEL_MODE,
    opened_at: Any = None,
    closed_at: Any = None,
    closed_by: Any = None,
    reason: Any = None,
    practice: bool = False,
) -> str:
    """The whole ticket as plain text, chronological, notes marked, attachments as links."""
    counts = count_directions(rows)
    head = [PRACTICE_MARK] if practice else []
    head += [
        f"Black Bloc modmail transcript — ticket #{ticket_id}",
        f"Server: {guild_name}",
        f"Member: {user_label} ({user_id})",
        f"Mode: {mode}",
        f"Opened: {opened_at or 'unknown'}",
        f"Closed: {closed_at or 'unknown'}"
        + (f" by {closed_by}" if closed_by else "")
        + (f" — {reason}" if reason else ""),
        f"Messages: {counts[IN]} from the member, {counts[OUT]} sent, {counts[NOTE]} note(s)",
        ATTACHMENTS_EXPIRE,
        "-" * 60,
        "",
    ]
    body = [transcript_line(row) for row in rows or ()]
    if not body:
        body = ["(nothing was said)"]
    return clamp_bytes("\n".join(head + body) + "\n")


def transcript_filename(ticket_id: Any, *, practice: bool = False) -> str:
    name = PRACTICE_TRANSCRIPT_NAME if practice else TRANSCRIPT_NAME
    return name.format(ticket_id=ticket_id)


def transcript_embed(
    *,
    ticket_id: Any,
    user_id: Any,
    user_label: Any,
    mode: str = CHANNEL_MODE,
    counts: Any = None,
    opened_at: Any = None,
    closed_at: Any = None,
    closed_by: Any = None,
    reason: Any = None,
    practice: bool = False,
) -> discord.Embed:
    """The summary that sits next to the transcript file in the log channel."""
    tally = counts or dict.fromkeys(DIRECTIONS, 0)
    embed = discord.Embed(
        title=f"{'Practice ticket' if practice else 'Ticket'} #{ticket_id} closed",
        description=f"<@{int(user_id)}> — {clamp(user_label, NAME_LIMIT)}",
        colour=COLOURS[NOTE],
    )
    embed.add_field(name="Opened", value=str(opened_at or "unknown"), inline=False)
    embed.add_field(name="Closed", value=str(closed_at or "unknown"), inline=False)
    embed.add_field(
        name="Closed by",
        value=f"<@{int(closed_by)}>" if closed_by else "Black Bloc",
        inline=True,
    )
    embed.add_field(name="Mode", value=mode, inline=True)
    embed.add_field(
        name="Messages",
        value=f"{tally.get(IN, 0)} in · {tally.get(OUT, 0)} out · {tally.get(NOTE, 0)} note(s)",
        inline=False,
    )
    if practice:
        embed.add_field(name="Practice", value=PRACTICE_MARK, inline=False)
    if reason:
        embed.add_field(name="Reason", value=clamp(reason, FIELD_LIMIT), inline=False)
    embed.set_footer(text=f"user {int(user_id)}")
    return embed


def opening_dm(guild_name: Any) -> str:
    return (
        f"Thanks — the staff of **{guild_name}** can see this now, and their replies come back "
        "here as a DM from Black Bloc. Anything else you send in this DM is added to the same "
        "ticket until it is closed."
    )


def closing_dm(guild_name: Any, reason: Any = None) -> str:
    why = f" The reason given was: {clamp(reason, 400)}" if reason else ""
    return (
        f"Your modmail ticket on **{guild_name}** has been closed.{why} DM Black Bloc again if "
        "you need anything else and a new ticket is opened."
    )


def thread_invite(role_ids: Any, ticket_id: Any, user_label: Any) -> str:
    ping = staff_ping(role_ids)
    who = clamp(user_label, NAME_LIMIT) or "a member"
    if not ping:
        return f"Ticket #{ticket_id} — **{who}**. No staff role resolves, so nobody was added."
    return f"{ping} — ticket #{ticket_id} from **{who}**."


def modes_sentence(mode: str) -> str:
    if mode == THREAD_MODE:
        return "new tickets are **private threads** in the staff channel"
    if mode == FORUM_MODE:
        return "new tickets are **posts** in the modmail forum"
    return "new tickets are **channels** in the modmail category"


THREADED_MODES = (THREAD_MODE, FORUM_MODE)

FORUM_OPEN_TAG = "open"
FORUM_CLOSED_TAG = "closed"
FORUM_TAG_NAMES = (FORUM_OPEN_TAG, FORUM_CLOSED_TAG)
FORUM_TAG_EMOJI: dict[str, str] = {
    FORUM_OPEN_TAG: "\N{LARGE GREEN CIRCLE}",
    FORUM_CLOSED_TAG: "\N{MEDIUM BLACK CIRCLE}",
}
FORUM_CHANNEL_NAME = "modmail"
FORUM_TOPIC = (
    "Black Bloc modmail — one post per ticket. Only staff can see this; the member never does."
)


def forum_tags(names: Any = FORUM_TAG_NAMES) -> list[discord.ForumTag]:
    """The tags a modmail forum is made with; their ids live in the forum, never in a key."""
    return [
        discord.ForumTag(name=name, emoji=discord.PartialEmoji(name=FORUM_TAG_EMOJI[name]))
        for name in names
    ]


def tag_named(forum: Any, name: str) -> Any:
    """The forum's own tag by NAME, because a tag id is Discord's to hand out, not ours."""
    for tag in getattr(forum, "available_tags", None) or ():
        if str(getattr(tag, "name", "")).lower() == name.lower():
            return tag
    return None


def applied_tags(forum: Any, name: str, *, wanted: bool = True) -> list[Any]:
    """The one tag a ticket post wears, or nothing at all when tags are off or absent."""
    if not wanted:
        return []
    found = tag_named(forum, name)
    return [found] if found is not None else []


PANEL_MINUTES_KEY = "modmail_panel_minutes"
PANEL_TITLE = "The modmail inbox"
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /modmail again"
SETUP_TITLE = "Where modmail is set up"
BLOCKED_TITLE = "Who cannot open modmail tickets"
SNIPPETS_TITLE = "Saved replies"
FORGET_TITLE = "Forget where modmail has been pointed"

PANEL_LIST_CAP = 25
MORE_BLOCKED = "…and {rest} more — the Modmail page on the site lists every one."
MORE_SNIPPETS = "…and {rest} more — the Modmail page on the site lists every one."
PICK_A_BLOCK = "Somebody…"
PICK_A_SNIPPET = "A snippet…"
PICK_A_TICKET = "A ticket…"
PICK_A_PLACE = "Which place to forget…"
PICK_A_MODE = "How new tickets are made…"
PICK_A_REPLY_STYLE = "How staff answer a ticket…"
PICK_A_CHANNEL = "Pick a channel…"
PICK_A_CATEGORY = "Pick a category…"
PICK_A_FORUM = "Pick a forum…"
PICK_SOMEBODY = "Who to block…"

SOURCE_CARD = "card"
SOURCE_TYPED = "typed"
SOURCE_COMMAND = "command"
SOURCE_WEB = "web"
SOURCES = (SOURCE_CARD, SOURCE_TYPED, SOURCE_COMMAND, SOURCE_WEB)

SOURCE_DM = "dm"
SOURCE_PANEL = "panel"
SOURCE_STAFF = "staff"
SOURCE_PRACTICE = "practice"
TICKET_SOURCES = (SOURCE_DM, SOURCE_COMMAND, SOURCE_PANEL, SOURCE_STAFF, SOURCE_PRACTICE)
SOURCE_WORDS: dict[str, str] = {
    SOURCE_DM: "a DM to Black Bloc",
    SOURCE_COMMAND: "/modmail",
    SOURCE_PANEL: "the Open a ticket button",
    SOURCE_STAFF: "staff",
    SOURCE_PRACTICE: "practice",
}


def ticket_source(ticket: Any) -> str:
    """A ticket that predates the column came in by DM, because that was the only door."""
    found = str(field_of(ticket, "source", SOURCE_DM) or SOURCE_DM)
    return found if found in TICKET_SOURCES else SOURCE_DM


def first_line(text: Any) -> str:
    """The first thing somebody typed, or nothing at all."""
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    return lines[0] if lines else ""


def open_embed(
    *,
    ticket_id: Any,
    user_id: Any,
    user_label: Any = None,
    source: str = SOURCE_DM,
    opened_by: Any = None,
    subject: Any = None,
    opened_at: Any = None,
) -> discord.Embed:
    """The New-ticket card the transcripts channel gets the moment a ticket opens."""
    label = clamp(str(user_label or user_id), NAME_LIMIT)
    embed = discord.Embed(
        title=f"New ticket #{ticket_id}",
        description=f"<@{int(user_id)}> — {label}",
        colour=COLOURS[IN],
    )
    embed.add_field(name="Opened", value=str(opened_at or "just now"), inline=True)
    embed.add_field(name="Came in by", value=SOURCE_WORDS.get(source, source), inline=True)
    if source == SOURCE_STAFF and opened_by:
        embed.add_field(name="Opened by", value=f"<@{int(opened_by)}>", inline=True)
    said = first_line(subject)
    if said:
        embed.add_field(name="About", value=clamp(said, FIELD_LIMIT), inline=False)
    embed.set_footer(text=f"{label} | {int(user_id)}")
    return embed


SETUP = "setup"
BLOCKED_MOVE = "blocked"
SNIPPETS = "snippets"
FORGET = "forget"
LOGS = "logs"
PRACTICE = "practice"
PRACTICE_YES = "practice_yes"
PRACTICE_NO = "practice_no"
REFRESH = "refresh"
SITE = "site"
BACK = "back"
CATEGORY = "category"
STAFF_CHANNEL = "staff_channel"
FORUM = "forum"
MAKE_FORUM = "make_forum"
TRANSCRIPTS = "transcripts"
MODE = "mode"
REPLY_STYLE = "reply_style"
ENABLE = "enable"
DISABLE = "disable"
UNBLOCK = "unblock"
BLOCK_PICK = "block_pick"
BLOCK_REASON = "block_reason"
SNIPPET_ADD = "snippet_add"
SNIPPET_CHANGE = "snippet_change"
SNIPPET_REMOVE = "snippet_remove"
SNIPPET_REMOVE_YES = "snippet_remove_yes"
SNIPPET_REMOVE_NO = "snippet_remove_no"

TICKET_OPEN = "ticket_open"
OPEN_WITH = "open_with"
TICKET_BUTTON = "ticket_button"
PANEL_POST = "panel_post"
PANEL_MOVE_TO = "panel_move"
PANEL_DOWN = "panel_down"

MEMBER_COMMAND_KEY = "modmail_member_command"
PANEL_CHANNEL_KEY = "modmail_panel_channel_id"
PANEL_MESSAGE_KEY = "modmail_panel_message_id"
PANEL_HEADING_KEY = "modmail_panel_title"
PANEL_TEXT_KEY = "modmail_panel_text"

MEMBER_TITLE = "Modmail"
MEMBER_INTRO = "Modmail is how you reach staff privately. Nobody else sees what you write."
MEMBER_TICKET_OPEN = (
    "**Your ticket is open.** Staff can see it, and their replies come back as a DM from Black "
    "Bloc. Anything you DM Black Bloc is added to the same ticket."
)
MEMBER_TICKET_SEEN = "**Your ticket is open:** <#{where}>. Staff answer there, and by DM."
TICKET_BUTTON_TITLE = "The Open a ticket button"
PICK_A_MEMBER = "Who to open a ticket with…"


class ModmailMove(NamedTuple):
    action: str
    label: str
    style: str = "secondary"
    row: int = 0
    modal: bool = False


SETUP_MOVE = ModmailMove(SETUP, "Setup…", "secondary", 1)
BLOCKED_MOVE_BUTTON = ModmailMove(BLOCKED_MOVE, "Blocked…", "secondary", 1)
SNIPPETS_MOVE = ModmailMove(SNIPPETS, "Snippets…", "secondary", 1)
FORGET_MOVE = ModmailMove(FORGET, "Forget…", "secondary", 1)
PRACTICE_MOVE = ModmailMove(PRACTICE, "Try a fake ticket", "secondary", 1)
PRACTICE_YES_MOVE = ModmailMove(PRACTICE_YES, "Yes, open one", "primary", 1)
PRACTICE_NO_MOVE = ModmailMove(PRACTICE_NO, "No", "secondary", 1)
LOGS_MOVE = ModmailMove(LOGS, "Logs", "secondary", 2)
REFRESH_MOVE = ModmailMove(REFRESH, "Refresh", "secondary", 2)
SITE_MOVE = ModmailMove(SITE, "Open on the site", "link", 2)

CATEGORY_MOVE = ModmailMove(CATEGORY, "Ticket category…", "secondary", 1)
STAFF_CHANNEL_MOVE = ModmailMove(STAFF_CHANNEL, "Staff channel…", "secondary", 1)
FORUM_MOVE = ModmailMove(FORUM, "Forum channel…", "secondary", 3)
MAKE_FORUM_MOVE = ModmailMove(MAKE_FORUM, "Make the forum", "primary", 3)
TRANSCRIPTS_MOVE = ModmailMove(TRANSCRIPTS, "Transcripts…", "secondary", 1)
MODE_MOVE = ModmailMove(MODE, "Mode…", "secondary", 1)
ANSWER_ON_MOVE = ModmailMove(ENABLE, "Answer DMs on", "primary", 1)
ANSWER_OFF_MOVE = ModmailMove(DISABLE, "Answer DMs off", "secondary", 1)
REPLY_STYLE_MOVE = ModmailMove(REPLY_STYLE, "Reply style…", "secondary", 2)
SETUP_BACK_MOVE = ModmailMove(BACK, "Back", "secondary", 2)
SETUP_REFRESH_MOVE = ModmailMove(REFRESH, "Refresh", "secondary", 2)

UNBLOCK_MOVE = ModmailMove(UNBLOCK, "Unblock them", "danger", 2)
BLOCK_PICK_MOVE = ModmailMove(BLOCK_PICK, "Block someone…", "secondary", 2)
BLOCK_REASON_MOVE = ModmailMove(BLOCK_REASON, "Block them…", "danger", 2, modal=True)
BLOCKED_BACK_MOVE = ModmailMove(BACK, "Back", "secondary", 3)
BLOCKED_REFRESH_MOVE = ModmailMove(REFRESH, "Refresh", "secondary", 3)

SNIPPET_REMOVE_MOVE = ModmailMove(SNIPPET_REMOVE, "Remove it", "danger", 2)
SNIPPET_ADD_MOVE = ModmailMove(SNIPPET_ADD, "Add one…", "secondary", 2, modal=True)
SNIPPET_CHANGE_MOVE = ModmailMove(SNIPPET_CHANGE, "Change it…", "secondary", 2, modal=True)
SNIPPET_YES_MOVE = ModmailMove(SNIPPET_REMOVE_YES, "Yes, remove it", "danger", 2)
SNIPPET_NO_MOVE = ModmailMove(SNIPPET_REMOVE_NO, KEEP_IT, "secondary", 2)
SNIPPETS_BACK_MOVE = ModmailMove(BACK, "Back", "secondary", 3)
SNIPPETS_REFRESH_MOVE = ModmailMove(REFRESH, "Refresh", "secondary", 3)

FORGET_BACK_MOVE = ModmailMove(BACK, "Back", "secondary", 1)
FORGET_REFRESH_MOVE = ModmailMove(REFRESH, "Refresh", "secondary", 1)

ROOT_ROW_DOORS = 0
ROOT_ROW_SELECT = 1
ROOT_ROW_MOVES = 2
ROOT_ROW_TAIL = 3

TICKET_MOVE = ModmailMove(TICKET_OPEN, "Open a ticket", "primary", ROOT_ROW_DOORS, modal=True)
OPEN_WITH_MOVE = ModmailMove(OPEN_WITH, "Open a ticket with…", "secondary", ROOT_ROW_DOORS)
ROOT_UNBLOCK_MOVE = ModmailMove(UNBLOCK, "Unblock them", "danger", ROOT_ROW_DOORS)

TICKET_BUTTON_MOVE = ModmailMove(TICKET_BUTTON, "Ticket button…", "secondary", 2)
PANEL_POST_MOVE = ModmailMove(PANEL_POST, "Post it…", "primary", 1)
PANEL_MOVE_MOVE = ModmailMove(PANEL_MOVE_TO, "Move it…", "secondary", 1)
PANEL_DOWN_MOVE = ModmailMove(PANEL_DOWN, "Take it down", "danger", 1)
PANEL_BACK_MOVE = ModmailMove(BACK, "Back", "secondary", 2)
PANEL_REFRESH_MOVE = ModmailMove(REFRESH, "Refresh", "secondary", 2)

PANEL_MOVES = (
    TICKET_MOVE,
    OPEN_WITH_MOVE,
    TICKET_BUTTON_MOVE,
    PANEL_POST_MOVE,
    PANEL_MOVE_MOVE,
    PANEL_DOWN_MOVE,
    PANEL_BACK_MOVE,
    PANEL_REFRESH_MOVE,
    SETUP_MOVE,
    BLOCKED_MOVE_BUTTON,
    SNIPPETS_MOVE,
    FORGET_MOVE,
    PRACTICE_MOVE,
    PRACTICE_YES_MOVE,
    PRACTICE_NO_MOVE,
    LOGS_MOVE,
    REFRESH_MOVE,
    SITE_MOVE,
    CATEGORY_MOVE,
    STAFF_CHANNEL_MOVE,
    FORUM_MOVE,
    MAKE_FORUM_MOVE,
    TRANSCRIPTS_MOVE,
    MODE_MOVE,
    ANSWER_ON_MOVE,
    ANSWER_OFF_MOVE,
    REPLY_STYLE_MOVE,
    SETUP_BACK_MOVE,
    SETUP_REFRESH_MOVE,
    UNBLOCK_MOVE,
    BLOCK_PICK_MOVE,
    BLOCK_REASON_MOVE,
    BLOCKED_BACK_MOVE,
    BLOCKED_REFRESH_MOVE,
    SNIPPET_REMOVE_MOVE,
    SNIPPET_ADD_MOVE,
    SNIPPET_CHANGE_MOVE,
    SNIPPET_YES_MOVE,
    SNIPPET_NO_MOVE,
    SNIPPETS_BACK_MOVE,
    SNIPPETS_REFRESH_MOVE,
    FORGET_BACK_MOVE,
    FORGET_REFRESH_MOVE,
)


def door_buttons(
    *,
    may_open: bool,
    staff: bool,
    picking: bool = False,
    blocked_pick: bool = False,
    open_with: bool = False,
) -> tuple[ModmailMove, ...]:
    """The first row everybody sees: one Open a ticket, and for staff the one they open FOR."""
    found: list[ModmailMove] = []
    if may_open:
        found.append(TICKET_MOVE)
    if staff and open_with and not picking:
        found.append(OPEN_WITH_MOVE)
    if staff and blocked_pick:
        found.append(ROOT_UNBLOCK_MOVE)
    return tuple(found)


def root_buttons(
    *,
    has_forget: bool,
    has_site: bool,
    has_practice: bool = False,
    confirming: bool = False,
) -> tuple[ModmailMove, ...]:
    """Forget… is drawn only where something is pointed, so it can never answer 'nothing to do'."""
    if confirming:
        return (
            PRACTICE_YES_MOVE._replace(row=ROOT_ROW_MOVES),
            PRACTICE_NO_MOVE._replace(row=ROOT_ROW_MOVES),
        )
    found = [SETUP_MOVE, BLOCKED_MOVE_BUTTON, SNIPPETS_MOVE]
    if has_forget:
        found.append(FORGET_MOVE)
    if has_practice:
        found.append(PRACTICE_MOVE)
    tail = [LOGS_MOVE, REFRESH_MOVE]
    if has_site:
        tail.append(SITE_MOVE)
    return tuple(
        [move._replace(row=ROOT_ROW_MOVES) for move in found]
        + [move._replace(row=ROOT_ROW_TAIL) for move in tail]
    )


def setup_buttons(*, enabled: bool, has_forum: bool = False) -> tuple[ModmailMove, ...]:
    """One button that names its own effect, never two spellings of the same switch."""
    return (
        CATEGORY_MOVE,
        STAFF_CHANNEL_MOVE,
        TRANSCRIPTS_MOVE,
        MODE_MOVE,
        ANSWER_OFF_MOVE if enabled else ANSWER_ON_MOVE,
        REPLY_STYLE_MOVE,
        TICKET_BUTTON_MOVE,
        SETUP_BACK_MOVE,
        SETUP_REFRESH_MOVE,
        FORUM_MOVE,
        *(() if has_forum else (MAKE_FORUM_MOVE,)),
    )


def ticket_button_buttons(*, posted: bool, picking: bool) -> tuple[ModmailMove, ...]:
    """Post it while nothing is up, Move it… and Take it down once something is."""
    found: list[ModmailMove] = []
    if not picking:
        found.append(PANEL_MOVE_MOVE if posted else PANEL_POST_MOVE)
    if posted:
        found.append(PANEL_DOWN_MOVE)
    found += [PANEL_BACK_MOVE, PANEL_REFRESH_MOVE]
    return tuple(found)


def blocked_buttons(*, picked: bool, blocking: bool) -> tuple[ModmailMove, ...]:
    found: list[ModmailMove] = []
    if picked:
        found.append(UNBLOCK_MOVE)
    found.append(BLOCK_REASON_MOVE if blocking else BLOCK_PICK_MOVE)
    found += [BLOCKED_BACK_MOVE, BLOCKED_REFRESH_MOVE]
    return tuple(found)


def snippet_buttons(*, picked: bool, confirming: bool) -> tuple[ModmailMove, ...]:
    if confirming:
        return (SNIPPET_YES_MOVE, SNIPPET_NO_MOVE, SNIPPETS_BACK_MOVE)
    found: list[ModmailMove] = []
    if picked:
        found += [SNIPPET_REMOVE_MOVE, SNIPPET_CHANGE_MOVE]
    found.append(SNIPPET_ADD_MOVE)
    found += [SNIPPETS_BACK_MOVE, SNIPPETS_REFRESH_MOVE]
    return tuple(found)


def forget_buttons() -> tuple[ModmailMove, ...]:
    return (FORGET_BACK_MOVE, FORGET_REFRESH_MOVE)


def block_line(row: Any) -> str:
    reason = row["reason"] or "no reason given"
    return f"<@{row['user_id']}> — {reason} ({str(row['at'])[:10]})"


def snippet_line(row: Any) -> str:
    return f"**{row['name']}** — {clamp(row['content'], 120)}"


def capped_lines(rows: Any, shape: Any, more: str, cap: int = PANEL_LIST_CAP) -> list[str]:
    """A panel embed shows a page, and says in words where the rest of the list lives."""
    found = list(rows or ())
    lines = [shape(row) for row in found[:cap]]
    if len(found) > cap:
        lines.append(more.format(rest=len(found) - cap))
    return lines


def blocked_lines(rows: Any, cap: int = PANEL_LIST_CAP) -> list[str]:
    return capped_lines(rows, block_line, MORE_BLOCKED, cap)


def snippet_lines(rows: Any, cap: int = PANEL_LIST_CAP) -> list[str]:
    return capped_lines(rows, snippet_line, MORE_SNIPPETS, cap)


def panel_minutes(store: Any, guild_id: int) -> int:
    from .panels import panel_minutes as _minutes

    return _minutes(store, guild_id, PANEL_MINUTES_KEY)


CARD_REPLY = "card_reply"
CARD_ANON = "card_areply"
CARD_NOTE = "card_note"
CARD_CLOSE = "card_close"
CARD_SPEAK = "card_speak"
CARD_END = "card_end"

CARD_TITLE = "Ticket #{ticket_id}"
CARD_PRACTICE_TITLE = "Practice ticket #{ticket_id}"
CARD_BLOCKED_LINE = "⚠️ **They are blocked** — a new ticket cannot be opened after this one."
CARD_PRACTICE_LINE = (
    "This ticket is **practice**. Nothing here reaches a member: no DM is sent and no reply "
    "leaves Discord. **End the practice** closes it and files a transcript marked PRACTICE."
)
CARD_COUNTS = "**messages** — {inbound} from them · {outbound} sent · {notes} note(s)"
CARD_OPENED_BY_STAFF = "**opened by staff** — <@{who}>"
CARD_NOT_REACHED = (
    "⚠️ **The last reply did not reach them** — their DMs are shut or Black Bloc is blocked. "
    "The ticket has it either way."
)
PANEL_HEADING_DEFAULT = MODMAIL_PANEL_TITLE_DEFAULT
PANEL_TEXT_DEFAULT = MODMAIL_PANEL_TEXT_DEFAULT


class CardMove(NamedTuple):
    action: str
    label: str
    style: str = "secondary"
    row: int = 0


REPLY_MOVE = CardMove(CARD_REPLY, "Reply", "primary", 0)
ANON_MOVE = CardMove(CARD_ANON, "Reply as Staff", "secondary", 0)
CARD_NOTE_MOVE = CardMove(CARD_NOTE, "Private note", "secondary", 0)
CARD_CLOSE_MOVE = CardMove(CARD_CLOSE, "Close…", "danger", 0)
SPEAK_MOVE = CardMove(CARD_SPEAK, "Speak as the member", "secondary", 1)
END_MOVE = CardMove(CARD_END, "End the practice", "danger", 1)

CARD_MOVES = (REPLY_MOVE, ANON_MOVE, CARD_NOTE_MOVE, CARD_CLOSE_MOVE, SPEAK_MOVE, END_MOVE)
CARD_ROW_LIMIT = 5


def card_buttons(*, practice: bool) -> tuple[CardMove, ...]:
    """The four moves every open ticket has, plus the two only a practice ticket can offer."""
    found = [REPLY_MOVE, ANON_MOVE, CARD_NOTE_MOVE, CARD_CLOSE_MOVE]
    if practice:
        found += [SPEAK_MOVE, END_MOVE]
    return tuple(found)


TICKET_SURFACE = "ticket"
TICKET_BACK_MOVE = ModmailMove(BACK, "Back", "secondary", 2)
CARD_CLOSED_FOOTER = "This ticket is closed — Back goes to the inbox."
CARD_ROW = 1


def panel_card_buttons(*, open_ticket: bool) -> tuple[ModmailMove, ...]:
    """The panel redraws the card's own moves, so there is one label table and never two."""
    found = [
        ModmailMove(move.action, move.label, move.style, CARD_ROW, modal=True)
        for move in (card_buttons(practice=False) if open_ticket else ())
    ]
    found.append(TICKET_BACK_MOVE)
    return tuple(found)


def ticket_label(ticket: Any, label: Any = None) -> str:
    """One open ticket as one select option: its number, its mode, then whose it is."""
    from .panels import option_label

    return option_label(ticket["id"], ticket["mode"], label or ticket["user_id"])


REPLY_STYLE_KEY = "modmail_reply_style"
REPLY_STYLE_OPTIONS = {
    MODMAIL_BUTTONS: "only the card's Reply and /reply reach the member",
    MODMAIL_TYPING: "a plain message in a ticket is relayed, as it always has been",
    MODMAIL_BOTH: "both — today's behaviour, with the card added",
}
REPLY_STYLE_SET = "Staff answer tickets by **{style}** from now on. {what}"
REPLY_STYLE_WORDS = {
    MODMAIL_BUTTONS: (
        "A message typed in a ticket now stays in the ticket — only the card's **Reply** and "
        "`/reply` reach the member."
    ),
    MODMAIL_TYPING: (
        "⚠️ From now on, anything staff type in a ticket goes to the member. The card's buttons "
        "still work."
    ),
    MODMAIL_BOTH: (
        "⚠️ From now on, anything staff type in a ticket goes to the member, and the card's "
        "buttons work too."
    ),
}


def relays_typing(style: Any) -> bool:
    """`buttons` is the only style that stops a typed message reaching the member."""
    return str(style or MODMAIL_BOTH) != MODMAIL_BUTTONS


def reply_style_sentence(style: str) -> str:
    return REPLY_STYLE_SET.format(style=style, what=REPLY_STYLE_WORDS.get(style, ""))


def is_practice(ticket: Any) -> bool:
    return bool(field_of(ticket, "practice", 0))


def ticket_card_lines(
    ticket: Any,
    counts: Any = None,
    *,
    label: Any = None,
    blocked: bool = False,
    not_reached: bool = False,
):
    tally = counts or dict.fromkeys(DIRECTIONS, 0)
    source = ticket_source(ticket)
    opener = field_of(ticket, "opened_by")
    lines = [
        f"<@{int(ticket['user_id'])}> — {clamp(label or ticket['user_id'], NAME_LIMIT)}",
        f"**opened** — {ticket['opened_at']}",
        f"**came in by** — {SOURCE_WORDS.get(source, source)}",
        f"**mode** — {ticket['mode']}",
        CARD_COUNTS.format(
            inbound=tally.get(IN, 0), outbound=tally.get(OUT, 0), notes=tally.get(NOTE, 0)
        ),
    ]
    if source == SOURCE_STAFF and opener:
        lines.insert(3, CARD_OPENED_BY_STAFF.format(who=int(opener)))
    if not_reached:
        lines.append(CARD_NOT_REACHED)
    if blocked:
        lines.append(CARD_BLOCKED_LINE)
    if is_practice(ticket):
        lines.append(CARD_PRACTICE_LINE)
    return lines


def ticket_card_embed(
    ticket: Any,
    counts: Any = None,
    *,
    label: Any = None,
    blocked: bool = False,
    not_reached: bool = False,
) -> discord.Embed:
    """The controls' own embed — the header card upstairs is the dossier, this is the state."""
    practice = is_practice(ticket)
    title = (CARD_PRACTICE_TITLE if practice else CARD_TITLE).format(ticket_id=ticket["id"])
    return discord.Embed(
        title=title,
        description="\n".join(
            ticket_card_lines(
                ticket, counts, label=label, blocked=blocked, not_reached=not_reached
            )
        ),
        colour=COLOURS[NOTE] if practice else COLOURS[IN],
    )


def first_message(subject: Any, text: Any) -> str:
    """The subject is a heading on the paragraph, so the transcript keeps both."""
    said = clamp(str(subject or "").strip(), NAME_LIMIT)
    body = clamp(str(text or "").strip(), MESSAGE_LIMIT)
    return f"**{said}**\n{body}" if said else body


def ticket_button_embed(title: Any, text: Any) -> discord.Embed:
    """The one message that sits in a channel with the Open a ticket button under it."""
    return discord.Embed(
        title=clamp(title, NAME_LIMIT) or PANEL_HEADING_DEFAULT,
        description=clamp(text, CONTENT_LIMIT) or PANEL_TEXT_DEFAULT,
        colour=COLOURS[IN],
    )


def last_reply_missed(rows: Any) -> bool:
    """True when the newest thing sent to the member never arrived — the card says so."""
    for row in reversed(list(rows or ())):
        if str(row["direction"]) != OUT:
            continue
        return not field_of(row, "delivered", 1)
    return False
