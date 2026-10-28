"""The Bluesky mirror's rules and words: kinds, the age guard, links and the message."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import discord

from .block_look import LABEL_MAX
from .settings_store import (
    BLUESKY_CHANNEL,
    BLUESKY_DEFAULTS,
    BLUESKY_FOOTER,
    BLUESKY_HANDLE,
    BLUESKY_INTERVAL,
    BLUESKY_KEEP,
    BLUESKY_MAX_AGE,
    BLUESKY_MODE,
    BLUESKY_MODES,
    BLUESKY_OPEN_LABEL,
    BLUESKY_PING_ROLE,
    BLUESKY_PROFILE_LABEL,
    BLUESKY_REHEARSAL_LINE,
    BLUESKY_REPLIES,
    BLUESKY_REPOST_LINE,
    BLUESKY_REPOSTS,
    BLUESKY_SEED_COUNT,
    BLUESKY_TEMPLATE,
)

log = logging.getLogger(__name__)

OFF = "off"
SHADOW = "shadow"
ON = "on"

OWN = "own"
REPOST = "repost"
REPLY = "reply"
KINDS = (OWN, REPOST, REPLY)
REPOST_REASON = "app.bsky.feed.defs#reasonRepost"
LINK_FACET = "app.bsky.richtext.facet#link"

CLAIMED = "claimed"
POSTED = "posted"
WOULD_POST = "would_post"
SKIPPED_OLD = "skipped_old"
SKIPPED_KIND = "skipped_kind"
RETRY = "retry"
FAILED = "failed"

CHANNEL = "channel"
TEST = "test"
WHERES = (CHANNEL, TEST)

FEED_LIMIT = 30
BACKOFF_MAX_MINUTES = 60
RECENT_ROWS = 30
MESSAGE_LIMIT = 2000
DESCRIPTION_LIMIT = 4096
AUTHOR_LIMIT = 256
TITLE_LIMIT = 256
FOOTER_LIMIT = 2048
FIELD_NAME_LIMIT = 256
FIELD_VALUE_LIMIT = 1024
EMBED_COLOUR = 0x1185FE
POST_URL = "https://bsky.app/profile/{handle}/post/{rkey}"
PROFILE_URL = "https://bsky.app/profile/{handle}"
FOOTER_ICON = "/assets/bluesky.png"
FRACTION = re.compile(r"\.(\d+)")

NO_CHANNEL = (
    "bluesky_channel_id is blank, so there is nowhere to post. Pick the channel under Bluesky "
    "on the Posts page."
)
NO_TEST_HOME = (
    "No test channel is set, so there is nowhere to send a test copy. Pick the Test channel "
    "(shadow_channel_id) in Settings."
)
CHANNEL_GONE = (
    "Black Bloc cannot see channel {channel}, so nothing was posted. Pick the channel again "
    "under Bluesky on the Posts page."
)
TEST_MODE_REFUSED = "Test mode keeps Black Bloc out of channel {channel}, so nothing was posted."
POST_REFUSED = "Discord refused the post ({why}), so it was not posted."
MODE_OFF = "bluesky_mode is off, so Bluesky is not read. Turn it to test or on first."
READ_FAILED = (
    "Bluesky could not be read just now ({why}), so nothing was posted. That is the network or "
    "Bluesky, not a setting here; try again in a minute."
)
READ_SAID = "Read {seen} post(s) from @{handle}: {new} new, {sent} sent."
BAD_COUNT = "Post the latest takes 1 to {most} posts, so nothing was posted."
BAD_WHERE = "Post the latest goes to the channel or the test channel, so nothing was posted."
NOTHING_ELIGIBLE = "@{handle} has no post Black Bloc may mirror right now, so nothing was posted."
POSTED_LATEST = "{posted} post(s) are up in <#{channel}>."
ALREADY_UP = " {skipped} were already up, so they were not posted again."
NOT_SEEN = "Black Bloc has not seen that post, so nothing was posted. Press Read now first."
GONE = "Bluesky no longer has that post, so nothing was posted."
POST_FAILED_PART = " {failed} could not be posted ({why})."


@dataclass(frozen=True)
class Item:
    uri: str
    cid: str
    kind: str
    handle: str
    author: str
    avatar: str | None
    indexed_at: str
    seen_from: str
    text: str
    url: str
    embed: dict[str, Any]
    account: str


def mode_of(store: Any, guild_id: int) -> str:
    found = str(store.get(guild_id, BLUESKY_MODE))
    return found if found in BLUESKY_MODES else OFF


def handle_of(store: Any, guild_id: int) -> str:
    return str(store.get(guild_id, BLUESKY_HANDLE) or BLUESKY_DEFAULTS[BLUESKY_HANDLE])


def channel_of(store: Any, guild_id: int) -> int | None:
    return as_id(store.get(guild_id, BLUESKY_CHANNEL))


def ping_role(store: Any, guild_id: int) -> int | None:
    return as_id(store.get(guild_id, BLUESKY_PING_ROLE))


def interval(store: Any, guild_id: int) -> int:
    return int(store.get(guild_id, BLUESKY_INTERVAL))


def max_age(store: Any, guild_id: int) -> timedelta:
    return timedelta(hours=int(store.get(guild_id, BLUESKY_MAX_AGE)))


def keep(store: Any, guild_id: int) -> int:
    return int(store.get(guild_id, BLUESKY_KEEP))


def seed_count(store: Any, guild_id: int) -> int:
    return int(store.get(guild_id, BLUESKY_SEED_COUNT))


def as_id(value: Any) -> int | None:
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def parsed(text: Any) -> datetime | None:
    """Bluesky stamps carry up to nine fractional digits; Python reads six."""
    raw = str(text or "").strip()
    if not raw:
        return None
    raw = FRACTION.sub(lambda match: "." + match.group(1)[:6].ljust(6, "0"), raw, count=1)
    try:
        found = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return found if found.tzinfo else found.replace(tzinfo=UTC)


def kind_of(entry: dict[str, Any]) -> str:
    reason = entry.get("reason") or {}
    if reason.get("$type") == REPOST_REASON:
        return REPOST
    record = (entry.get("post") or {}).get("record") or {}
    return REPLY if record.get("reply") else OWN


def wanted(store: Any, guild_id: int, kind: str) -> bool:
    if kind == REPOST:
        return bool(store.get(guild_id, BLUESKY_REPOSTS))
    if kind == REPLY:
        return bool(store.get(guild_id, BLUESKY_REPLIES))
    return True


def seen_from(entry: dict[str, Any]) -> str:
    """When the item entered the feed: the repost's moment for a repost."""
    reason = entry.get("reason") or {}
    if reason.get("$type") == REPOST_REASON and reason.get("indexedAt"):
        return str(reason["indexedAt"])
    return str((entry.get("post") or {}).get("indexedAt") or "")


def too_old(item: Item, now: datetime, age: timedelta) -> bool:
    when = parsed(item.seen_from)
    return when is None or now - when > age


def rkey_of(uri: str) -> str:
    return str(uri or "").rstrip("/").rsplit("/", 1)[-1]


def post_url(handle: str, uri: str) -> str:
    return POST_URL.format(handle=handle, rkey=rkey_of(uri))


def expanded_text(record: dict[str, Any]) -> str:
    """The post's text with each link facet put back to its full address."""
    text = str(record.get("text") or "")
    data = text.encode("utf-8")
    spans: list[tuple[int, int, str]] = []
    for facet in record.get("facets") or ():
        index = facet.get("index") or {}
        for feature in facet.get("features") or ():
            if feature.get("$type") == LINK_FACET and feature.get("uri"):
                spans.append(
                    (int(index.get("byteStart", 0)), int(index.get("byteEnd", 0)), feature["uri"])
                )
    for start, end, uri in sorted(spans, reverse=True):
        if 0 <= start < end <= len(data):
            data = data[:start] + str(uri).encode("utf-8") + data[end:]
    return data.decode("utf-8", errors="replace")


def embed_of(view: Any) -> dict[str, Any]:
    """What one post's embed view carries that a Discord embed can show."""
    found: dict[str, Any] = {}
    if not isinstance(view, dict):
        return found
    kind = str(view.get("$type") or "")
    if kind.startswith("app.bsky.embed.recordWithMedia"):
        found |= embed_of(view.get("media"))
        found |= embed_of({"$type": "app.bsky.embed.record#view", "record": view.get("record")})
        return found
    if kind.startswith("app.bsky.embed.images"):
        images = view.get("images") or []
        if images and images[0].get("fullsize"):
            found["image"] = images[0]["fullsize"]
    elif kind.startswith("app.bsky.embed.video"):
        if view.get("thumbnail"):
            found["image"] = view["thumbnail"]
    elif kind.startswith("app.bsky.embed.external"):
        card = view.get("external") or {}
        if card.get("uri"):
            found["external"] = {"title": str(card.get("title") or card["uri"]), "uri": card["uri"]}
            if card.get("thumb"):
                found.setdefault("image", card["thumb"])
    elif kind.startswith("app.bsky.embed.record"):
        record = view.get("record") or {}
        if "record" in record and isinstance(record.get("record"), dict) and "value" not in record:
            record = record["record"]
        quoted = record.get("value") or {}
        author = record.get("author") or {}
        if quoted.get("text") is not None and author.get("handle"):
            found["quote"] = {
                "author": str(author.get("displayName") or author["handle"]),
                "handle": str(author["handle"]),
                "text": expanded_text(quoted),
            }
    return found


def item_of(entry: dict[str, Any]) -> Item | None:
    """One feed entry read into what the mirror needs, or None when it is not a post."""
    post = entry.get("post") or {}
    uri = str(post.get("uri") or "")
    author = post.get("author") or {}
    handle = str(author.get("handle") or "")
    if not uri or not handle:
        return None
    by = (entry.get("reason") or {}).get("by") or {}
    return Item(
        uri=uri,
        cid=str(post.get("cid") or ""),
        kind=kind_of(entry),
        handle=handle,
        author=str(author.get("displayName") or handle),
        avatar=author.get("avatar") or None,
        indexed_at=str(post.get("indexedAt") or ""),
        seen_from=seen_from(entry),
        text=expanded_text(post.get("record") or {}),
        url=post_url(handle, uri),
        embed=embed_of(post.get("embed")),
        account=str(by.get("displayName") or by.get("handle") or ""),
    )


def items_of(feed: list[dict[str, Any]]) -> list[Item]:
    """Feed order, newest first, each uri once (a repost of a post already listed is dropped)."""
    found: list[Item] = []
    seen: set[str] = set()
    for entry in feed:
        item = item_of(entry)
        if item is None or item.uri in seen:
            continue
        seen.add(item.uri)
        found.append(item)
    return found


def oldest_first(feed: list[dict[str, Any]]) -> list[Item]:
    """Walked from the bottom, so a post and a later repost of it keep the earlier one."""
    found: list[Item] = []
    seen: set[str] = set()
    for entry in reversed(feed):
        item = item_of(entry)
        if item is None or item.uri in seen:
            continue
        seen.add(item.uri)
        found.append(item)
    return found


def said(store: Any, guild_id: int, key: str, **fields: Any) -> str:
    """Staff wording first; a template that cannot be filled falls back to the shipped one."""
    wording = str(store.get(guild_id, key) or "")
    if wording.strip():
        try:
            return wording.format(**fields)
        except (IndexError, KeyError, ValueError):
            log.warning("bluesky: %s could not be filled in; the shipped wording was used", key)
    return str(BLUESKY_DEFAULTS[key]).format(**fields)


def worded(store: Any, guild_id: int, key: str, **fields: Any) -> str:
    """A blank key says nothing; anything else is filled like `said`."""
    if not str(store.get(guild_id, key) or "").strip():
        return ""
    return said(store, guild_id, key, **fields)


def profile_url(handle: str) -> str:
    return PROFILE_URL.format(handle=handle)


def account_of(item: Item) -> str:
    return item.account or item.author


def message_of(
    store: Any,
    guild_id: int,
    item: Item,
    *,
    rehearsal_for: Any = None,
    rehearsing: bool = False,
    role: int | None = None,
    icon: str | None = None,
) -> tuple[str, discord.Embed]:
    """The content line(s) and the embed for one post."""
    lines: list[str] = []
    if rehearsing:
        where = f"<#{int(rehearsal_for)}>" if rehearsal_for else "no channel"
        lines.append(said(store, guild_id, BLUESKY_REHEARSAL_LINE, channel=where))
    elif role:
        lines.append(f"<@&{int(role)}>")
    account = account_of(item)
    if item.kind == REPOST:
        lines.append(
            worded(store, guild_id, BLUESKY_REPOST_LINE, account=account, handle=item.handle)
        )
    else:
        lines.append(
            worded(
                store,
                guild_id,
                BLUESKY_TEMPLATE,
                text=item.text,
                url=item.url,
                author=item.author,
                handle=item.handle,
                account=account,
            )
        )
    content = "\n".join(line for line in lines if line.strip())[:MESSAGE_LIMIT]
    footer = worded(store, guild_id, BLUESKY_FOOTER)
    return content, embed_for(item, footer=footer, icon=icon)


def embed_for(item: Item, *, footer: str = "", icon: str | None = None) -> discord.Embed:
    embed = discord.Embed(
        title=item.author[:TITLE_LIMIT],
        description=item.text[:DESCRIPTION_LIMIT] or None,
        url=item.url,
        colour=EMBED_COLOUR,
        timestamp=parsed(item.indexed_at),
    )
    embed.set_author(
        name=f"@{item.handle}"[:AUTHOR_LIMIT], url=profile_url(item.handle), icon_url=item.avatar
    )
    found = item.embed
    if found.get("image"):
        embed.set_image(url=found["image"])
    quote = found.get("quote")
    if quote:
        embed.add_field(
            name=f"{quote['author']} · @{quote['handle']}"[:FIELD_NAME_LIMIT],
            value=(quote["text"] or "—")[:FIELD_VALUE_LIMIT],
            inline=False,
        )
    external = found.get("external")
    if external:
        embed.add_field(
            name=external["title"][:FIELD_NAME_LIMIT],
            value=external["uri"][:FIELD_VALUE_LIMIT],
            inline=False,
        )
    if footer:
        embed.set_footer(text=footer[:FOOTER_LIMIT], icon_url=icon)
    return embed


def view_for(store: Any, guild_id: int, item: Item) -> discord.ui.View | None:
    """The link buttons under a post: the post, then its author's profile."""
    buttons = [
        (worded(store, guild_id, BLUESKY_OPEN_LABEL), item.url),
        (
            worded(store, guild_id, BLUESKY_PROFILE_LABEL, handle=item.handle),
            profile_url(item.handle),
        ),
    ]
    shown = [(label.strip()[:LABEL_MAX], url) for label, url in buttons if label.strip()]
    if not shown:
        return None
    view = discord.ui.View(timeout=None)
    for label, url in shown:
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label=label, url=url))
    return view


def icon_of(origin: str) -> str:
    return str(origin or "").rstrip("/") + FOOTER_ICON


def post_mentions(role: int | None) -> discord.AllowedMentions:
    if not role:
        return discord.AllowedMentions.none()
    return discord.AllowedMentions(
        everyone=False, users=False, roles=[discord.Object(id=int(role))], replied_user=False
    )


def backoff_minutes(minutes: int, failures: int) -> int:
    if failures <= 0:
        return max(1, int(minutes))
    return int(min(BACKOFF_MAX_MINUTES, max(1, int(minutes)) * (2 ** min(int(failures), 16))))


def next_read(row: Any, minutes: int) -> datetime | None:
    """None when the account has never been read, so the first tick reads it."""
    if row is None:
        return None
    last = parsed(row["last_read_at"])
    if last is None:
        return None
    return last + timedelta(minutes=backoff_minutes(minutes, int(row["failures"] or 0)))


def is_due(row: Any, minutes: int, now: datetime) -> bool:
    found = next_read(row, minutes)
    return found is None or now >= found


__all__ = [
    "CHANNEL",
    "CLAIMED",
    "FAILED",
    "FEED_LIMIT",
    "Item",
    "KINDS",
    "OFF",
    "ON",
    "OWN",
    "POSTED",
    "REPLY",
    "REPOST",
    "RETRY",
    "SHADOW",
    "SKIPPED_KIND",
    "SKIPPED_OLD",
    "TEST",
    "WHERES",
    "WOULD_POST",
    "backoff_minutes",
    "embed_of",
    "expanded_text",
    "icon_of",
    "is_due",
    "item_of",
    "items_of",
    "kind_of",
    "message_of",
    "mode_of",
    "next_read",
    "oldest_first",
    "post_url",
    "profile_url",
    "seed_count",
    "too_old",
    "view_for",
    "wanted",
]
