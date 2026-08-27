from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

import discord

from .events import clamp, slugify
from .golive import parse_ts
from .settings_store import CHANNEL_MODE, THREAD_MODE
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
TRANSCRIPT_BYTES = 7_000_000

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
NO_TEXT = "(no text)"

SNIPPET_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")


def ticket_channel_name(user_name: Any, ticket_id: Any) -> str:
    """The incumbent's shape: the member's name, lowercased to Discord's rules."""
    slug = slugify(user_name)[:NAME_LIMIT].strip("-")
    return slug or f"ticket-{ticket_id}"


def ticket_topic(user_id: Any, ticket_id: Any) -> str:
    return TOPIC_TEMPLATE.format(user_id=int(user_id), ticket_id=int(ticket_id))


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
    shown = ANONYMOUS_NAME if direction == OUT and anonymous else str(author_name or "someone")
    embed = discord.Embed(
        title=TITLES.get(direction, direction),
        description=clamp(content, CONTENT_LIMIT) or f"*{NO_TEXT}*",
        colour=int(colour) if colour else COLOURS.get(direction, COLOURS[IN]),
        timestamp=at or datetime.now(UTC),
    )
    embed.set_author(name=clamp(shown, NAME_LIMIT), icon_url=icon_url or None)
    urls = attachment_urls(attachments)
    if urls:
        embed.add_field(name="Attachments", value=attachment_field(urls), inline=False)
    if not (direction == OUT and anonymous):
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
) -> str:
    """The whole ticket as plain text, chronological, notes marked, attachments as links."""
    counts = count_directions(rows)
    head = [
        f"Black Bloc modmail transcript — ticket #{ticket_id}",
        f"Server: {guild_name}",
        f"Member: {user_label} ({user_id})",
        f"Mode: {mode}",
        f"Opened: {opened_at or 'unknown'}",
        f"Closed: {closed_at or 'unknown'}"
        + (f" by {closed_by}" if closed_by else "")
        + (f" — {reason}" if reason else ""),
        f"Messages: {counts[IN]} from the member, {counts[OUT]} sent, {counts[NOTE]} note(s)",
        "-" * 60,
        "",
    ]
    body = [transcript_line(row) for row in rows or ()]
    if not body:
        body = ["(nothing was said)"]
    text = "\n".join(head + body) + "\n"
    return text[:TRANSCRIPT_BYTES]


def transcript_filename(ticket_id: Any) -> str:
    return TRANSCRIPT_NAME.format(ticket_id=ticket_id)


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
) -> discord.Embed:
    """The summary that sits next to the transcript file in the log channel."""
    tally = counts or dict.fromkeys(DIRECTIONS, 0)
    embed = discord.Embed(
        title=f"Ticket #{ticket_id} closed",
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
    return "new tickets are **channels** in the modmail category"
