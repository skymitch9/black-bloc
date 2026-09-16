from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import discord

from .actionlog import log_action
from .logkinds import FEATURE_PAGES, VIA_BOOT, VIA_DISCORD, kind_via
from .panels import Outcome, refusal

log = logging.getLogger(__name__)

SEED_FILE = Path(__file__).with_name("posts_seed.json")
PAGE = FEATURE_PAGES["posts"]
FEATURE = "posts"

MODE_KEY = "posts_mode"
PANEL_MINUTES_KEY = "posts_panel_minutes"
ON = "on"
OFF = "off"

PLAIN = "plain"
EMBED = "embed"
STYLES = (PLAIN, EMBED)
CAPS: dict[str, int] = {PLAIN: 2000, EMBED: 4096}
STYLE_WORDS: dict[str, str] = {PLAIN: "a plain message", EMBED: "an embed"}
TITLE_MAX = 256
SLUG_MAX = 60
PREVIEW_MAX = 300
SLUG_SHAPE = re.compile(r"[^a-z0-9-]+")
ROLE_MENTION = re.compile(r"<@&(\d+)>")

SAVED = "post.saved"
POSTED = "post.posted"
UPDATED = "post.updated"
WOULD_POST = "post.would_post"
POST_FAILED = "post.post_failed"
TAKEN_DOWN = "post.taken_down"
WOULD_TAKE_DOWN = "post.would_take_down"
PINNED = "post.pinned"
PIN_FAILED = "post.pin_failed"
MESSAGE_GONE = "post.message_gone"
RESET = "post.reset"
CREATED = "post.created"
DELETED = "post.deleted"

NO_SUCH_POST = (
    "There is no post called **{slug}**, so nothing was done. It may have been renamed — open "
    "the Posts page and pick it from the list."
)
POSTS_OFF = (
    "Posts are turned off for this server, so nothing was done. A Lead turns them back on from "
    "the dashboard's Settings page under **posts**, or with `/settings` ▸ **Turn a feature back "
    "on…**."
)
BODY_TOO_LONG = (
    "That post is {count} characters and {style_word} holds {limit}, so nothing was {doing}. "
    "Take {over} character{s} out{switch}."
)
SWITCH_TO_EMBED = " — or set the style to an embed, which holds 4096"
TITLE_TOO_LONG = (
    "An embed's title holds {limit} characters and that one is {count}, so nothing was saved. "
    "Take {over} character{s} out of the title, or set the style back to a plain message, where "
    "the title is never sent."
)
NO_CHANNEL_YET = (
    "**{title}** has no channel to go in yet, so there is nothing to post it to. Pick one under "
    "**Channel**, press Save Changes, then press Post it."
)
UNKNOWN_CHANNEL = (
    "**{given}** is not a channel Black Bloc can see in this server, so nothing was saved. Pick "
    "one from the list under **Channel**."
)
NOTHING_TO_POST = (
    "**{title}** has nothing written in it yet, so there is nothing to post. Write the message "
    "in the box, save it, then press Post it."
)
NOT_POSTED = (
    "**{title}** is not posted anywhere right now, so there is nothing to take down. Press Post "
    "it first."
)
CHANNEL_GONE = "the channel is not one Black Bloc can see any more"
POST_FAILED_SAID = (
    "Discord would not take that post, so **{title}** is unchanged: {reason}. That is a fault "
    "between Black Bloc and Discord rather than a problem with your access — try again, and "
    "tell a Lead if it keeps happening."
)
TAKE_DOWN_FAILED_SAID = (
    "Discord would not remove that message, so **{title}** is still posted: {reason}. Try "
    "again, and tell a Lead if it keeps happening."
)
SEEDED_CANNOT_BE_DELETED = (
    "**{slug}** is the post Black Bloc ships with, so it cannot be deleted — a deploy would "
    "only put it back. Press **Take it down** instead: the message goes and every word you have "
    "written is kept."
)
NOT_SEEDED = (
    "**{slug}** was written here rather than shipped with Black Bloc, so there is no original to "
    "put back. Nothing was changed."
)
POSTED_CANNOT_BE_DELETED = (
    "**{title}** is still posted in Discord, so it was not deleted. Press **Take it down** "
    "first — every word is kept either way."
)
SLUG_TAKEN = (
    "There is already a post at **{slug}**, so nothing was made. Give this one a different "
    "title, or edit the one that is there."
)
SLUG_NEEDED = (
    "A post needs a title Black Bloc can turn into a web address, and that one came out empty, "
    "so nothing was made. Use some letters or numbers in the title."
)
TITLE_NEEDED = "A post needs a title, so nothing was saved. Fill it in and save again."

SAVED_SAID = "**{title}** is saved."
CREATED_SAID = "**{title}** is made. Nothing is in Discord until you press Post it."
POSTED_SAID = "**{title}** is posted in {where}."
UPDATED_SAID = "**{title}** is updated where it was already posted, in {where}."
TAKEN_DOWN_SAID = "**{title}** is taken down. Every word is still here."
RESET_SAID = "**{title}** is back to the words it shipped with."
DELETED_SAID = "**{title}** is gone."
MODE_ON_SAID = "Posts are on. Staff can post from the site and from `/posts`."
MODE_OFF_SAID = "Posts are off. `/posts` disappears within about a minute; the text is all kept."

PANEL_TITLE = "Posts"
PANEL_INTRO = "The messages Black Bloc keeps current in this server."
PANEL_EMPTY = "There are no posts yet."
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run `/posts` again."
SITE_BUTTON = "Open on the site"
POST_IT = "Post it"
UPDATE_THE_POST = "Update the post"
TAKE_IT_DOWN = "Take it down"
PUT_THE_ORIGINAL_BACK = "Put the original back"
PIN_IT = "Pin it"
DO_NOT_PIN_IT = "Do not pin it"

STATUS_POSTED = "posted"
STATUS_PINNED = "pinned"
STATUS_NOT_POSTED = "not posted"
STATUS_PENDING = "changes not yet posted"


def now() -> str:
    return datetime.now(UTC).isoformat()


def slugify(text: Any) -> str:
    """The web address and the panel's own key, from the title a staffer typed."""
    lowered = str(text or "").strip().lower().replace("’", "").replace("'", "")
    return SLUG_SHAPE.sub("-", lowered).strip("-")[:SLUG_MAX].strip("-")


def clamp(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def row_value(row: Any, key: str, fallback: Any = None) -> Any:
    try:
        found = row[key]
    except (IndexError, KeyError, TypeError):
        return fallback
    return fallback if found is None else found


def cap_for(style: Any) -> int:
    return CAPS.get(str(style or PLAIN), CAPS[PLAIN])


def wanted_style(given: Any, fallback: str = PLAIN) -> str:
    text = str(given or "").strip().lower()
    return text if text in STYLES else fallback


def body_hash(style: Any, title: Any, body: Any) -> str:
    """What was SENT, so `changes_pending` compares the row against the message, not the clock."""
    payload = json.dumps(
        [str(style or PLAIN), str(title or ""), str(body or "")], ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def hash_of(row: Any) -> str:
    return body_hash(
        row_value(row, "style", PLAIN), row_value(row, "title"), row_value(row, "body")
    )


def is_posted(row: Any) -> bool:
    return bool(row_value(row, "message_id"))


def changes_pending(row: Any) -> bool:
    if not is_posted(row):
        return False
    return str(row_value(row, "posted_hash", "")) != hash_of(row)


def is_seeded(row: Any) -> bool:
    return bool(row_value(row, "seed_hash"))


def too_long(count: int, limit: int, style: str, doing: str) -> str:
    over = count - limit
    return BODY_TOO_LONG.format(
        count=count,
        style_word=STYLE_WORDS.get(style, STYLE_WORDS[PLAIN]),
        limit=limit,
        over=over,
        s="" if over == 1 else "s",
        doing=doing,
        switch=SWITCH_TO_EMBED if style == PLAIN else "",
    )


def refused_body(body: Any, style: str, doing: str) -> str | None:
    limit = cap_for(style)
    count = len(str(body or ""))
    return None if count <= limit else too_long(count, limit, style, doing)


def refused_title(title: Any, style: str) -> str | None:
    if style != EMBED:
        return None
    count = len(str(title or ""))
    if count <= TITLE_MAX:
        return None
    over = count - TITLE_MAX
    return TITLE_TOO_LONG.format(
        limit=TITLE_MAX, count=count, over=over, s="" if over == 1 else "s"
    )


def posts_are_on(store: Any, guild_id: int) -> bool:
    return str(store.get(guild_id, MODE_KEY)) == ON


def panel_minutes(store: Any, guild_id: int) -> int:
    return max(1, int(store.get(guild_id, PANEL_MINUTES_KEY) or 1))


def site_page_url(origin: Any) -> str | None:
    text = str(origin or "").strip()
    return f"{text.rstrip('/')}/{PAGE}" if text else None


def channel_name(guild: Any, channel_id: Any) -> str | None:
    channel = guild.get_channel(int(channel_id)) if guild is not None and channel_id else None
    return getattr(channel, "name", None)


def where_words(guild: Any, channel_id: Any) -> str:
    name = channel_name(guild, channel_id)
    return f"#{name}" if name else "that channel"


def status_words(row: Any) -> list[str]:
    """The pills both doors wear, in one place so they cannot be spelled two ways."""
    if not is_posted(row):
        return [STATUS_NOT_POSTED]
    found = [STATUS_POSTED]
    if row_value(row, "pin"):
        found.append(STATUS_PINNED)
    if changes_pending(row):
        found.append(STATUS_PENDING)
    return found


def move_label(row: Any) -> str:
    return UPDATE_THE_POST if is_posted(row) else POST_IT


def preview_of(row: Any) -> str:
    text = str(row_value(row, "body", "") or "").strip()
    return text if len(text) <= PREVIEW_MAX else f"{text[:PREVIEW_MAX]}…"


def render_message(row: Any) -> dict[str, Any]:
    """One rendering for the send, the edit and the site's `style`/`cap` contract.

    Both keys are always present so an edit from embed back to plain clears the embed."""
    style = wanted_style(row_value(row, "style", PLAIN))
    body = str(row_value(row, "body", "") or "")
    if style == EMBED:
        return {
            "content": None,
            "embed": discord.Embed(
                title=clamp(row_value(row, "title"), TITLE_MAX) or None, description=body
            ),
        }
    return {"content": body, "embed": None}


def allowed_mentions_for(guild: Any, body: Any, actor: Any) -> discord.AllowedMentions:
    """Checklist 11: nothing pings unless the body names a role this actor may actually ping."""
    perms = getattr(actor, "guild_permissions", None)
    may_ping_any = bool(getattr(perms, "mention_everyone", False))
    wanted: list[Any] = []
    for found in ROLE_MENTION.findall(str(body or "")):
        role = guild.get_role(int(found)) if guild is not None else None
        if role is None:
            continue
        if may_ping_any or bool(getattr(role, "mentionable", False)):
            wanted.append(role)
    return discord.AllowedMentions(
        everyone=False, users=False, roles=wanted, replied_user=False
    )


# --- the rows ---------------------------------------------------------------------------------


async def count_posts(db: Any, guild_id: int) -> int:
    cur = await db.conn.execute(
        "SELECT COUNT(*) AS n FROM posts WHERE guild_id = ?", (int(guild_id),)
    )
    row = await cur.fetchone()
    return int(row["n"]) if row else 0


async def list_posts(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM posts WHERE guild_id = ? ORDER BY id", (int(guild_id),)
    )
    return list(await cur.fetchall())


async def posted_posts(db: Any) -> list[Any]:
    cur = await db.conn.execute("SELECT * FROM posts WHERE message_id IS NOT NULL ORDER BY id")
    return list(await cur.fetchall())


async def get_post(db: Any, guild_id: int, slug: str) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM posts WHERE guild_id = ? AND slug = ?", (int(guild_id), str(slug))
    )
    return await cur.fetchone()


async def get_post_by_id(db: Any, post_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM posts WHERE id = ?", (int(post_id),))
    return await cur.fetchone()


async def create_post(
    db: Any,
    guild_id: int,
    *,
    slug: str,
    title: str,
    body: str = "",
    channel_id: Any = None,
    style: str = PLAIN,
    pin: bool = True,
    seed_hash: Any = None,
    by: int | None = None,
) -> int:
    cur = await db.conn.execute(
        "INSERT INTO posts(guild_id, slug, title, channel_id, body, style, pin, seed_hash, "
        "updated_at, updated_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            int(guild_id),
            str(slug),
            str(title),
            int(channel_id) if channel_id else None,
            str(body or ""),
            wanted_style(style),
            1 if pin else 0,
            seed_hash,
            now(),
            by,
        ),
    )
    await db.conn.commit()
    return int(cur.lastrowid)


async def delete_post(db: Any, post_id: int) -> None:
    await db.conn.execute("DELETE FROM posts WHERE id = ?", (int(post_id),))
    await db.conn.commit()


async def set_post_fields(db: Any, post_id: int, *, by: int | None = None, **fields: Any) -> None:
    columns = [name for name in fields if fields[name] is not ...]
    if not columns:
        return
    sets = ", ".join(f"{name} = ?" for name in columns)
    await db.conn.execute(
        f"UPDATE posts SET {sets}, updated_at = ?, updated_by = ? WHERE id = ?",
        (*[fields[name] for name in columns], now(), by, int(post_id)),
    )
    await db.conn.commit()


async def set_posted(
    db: Any, post_id: int, message_id: int, digest: str, *, by: int | None = None
) -> None:
    await db.conn.execute(
        "UPDATE posts SET message_id = ?, posted_hash = ?, posted_at = ?, posted_by = ? "
        "WHERE id = ?",
        (int(message_id), str(digest), now(), by, int(post_id)),
    )
    await db.conn.commit()


async def clear_posted(db: Any, post_id: int) -> None:
    await db.conn.execute(
        "UPDATE posts SET message_id = NULL, posted_hash = NULL, posted_at = NULL, "
        "posted_by = NULL WHERE id = ?",
        (int(post_id),),
    )
    await db.conn.commit()


# --- the seed ---------------------------------------------------------------------------------


def load_seed() -> dict[str, Any]:
    try:
        return json.loads(SEED_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        log.warning("posts: the seed could not be read — %s: %s", type(exc).__name__, exc)
        return {"version": 0, "posts": []}


def seed_entries() -> list[dict[str, Any]]:
    return list(load_seed().get("posts") or ())


def seed_entry(slug: Any) -> dict[str, Any] | None:
    return next((one for one in seed_entries() if one["slug"] == str(slug)), None)


def seed_hash(entry: dict[str, Any]) -> str:
    body = json.dumps(entry, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def known_channel(guild: Any, channel_id: Any) -> int | None:
    """§C6: the shipped channel id is verified against this guild before it is stored."""
    if not channel_id:
        return None
    try:
        wanted = int(channel_id)
    except (TypeError, ValueError):
        return None
    found = guild.get_channel(wanted) if guild is not None else None
    return wanted if found is not None else None


async def seed_posts(bot: Any, guild: Any) -> int:
    """Once per guild, when there is no post at all; a later boot never comes back here."""
    made = 0
    for entry in seed_entries():
        if await get_post(bot.db, guild.id, entry["slug"]) is not None:
            continue
        wanted = known_channel(guild, entry.get("channel_id"))
        if wanted is None and entry.get("channel_id"):
            await log_action(
                bot,
                guild,
                "post.seed_channel_unknown",
                details={
                    "slug": entry["slug"],
                    "channel_id": str(entry.get("channel_id")),
                    "via": VIA_BOOT,
                },
            )
        await create_post(
            bot.db,
            guild.id,
            slug=entry["slug"],
            title=entry["title"],
            body=entry.get("body", ""),
            channel_id=wanted,
            style=wanted_style(entry.get("style")),
            pin=bool(entry.get("pin", True)),
            seed_hash=seed_hash(entry),
        )
        made += 1
    return made


async def refresh_seeds(db: Any, guild_id: int) -> int:
    """What **Put the original back** restores, brought up to the shipped seed. Staff text is
    never touched."""
    changed = 0
    for entry in seed_entries():
        row = await get_post(db, guild_id, entry["slug"])
        if row is None:
            continue
        fresh = seed_hash(entry)
        if row_value(row, "seed_hash") == fresh:
            continue
        await db.conn.execute(
            "UPDATE posts SET seed_hash = ? WHERE id = ?", (fresh, int(row["id"]))
        )
        changed += 1
    await db.conn.commit()
    return changed


# --- the moves --------------------------------------------------------------------------------


def actor_id(actor: Any) -> int | None:
    found = getattr(actor, "id", None)
    return int(found) if found else None


async def note(
    bot: Any, guild: Any, row: Any, kind: str, actor: Any, *, via: str, **extra: Any
) -> None:
    """Every kind this module writes goes through here, so `via` can never be forgotten."""
    try:
        await log_action(
            bot,
            guild,
            kind_via(kind, via),
            actor=actor,
            details={
                "slug": row_value(row, "slug"),
                "post_id": row_value(row, "id"),
                "channel_id": row_value(row, "channel_id"),
                "via": via,
                **extra,
            },
        )
    except Exception as exc:
        log.warning("posts: %s not logged — %s: %s", kind, type(exc).__name__, exc)


async def make_post(
    bot: Any,
    guild: Any,
    actor: Any,
    *,
    title: Any,
    slug: Any = None,
    via: str = VIA_DISCORD,
) -> Outcome:
    """A new, empty post; posting it is somebody's press, never this."""
    kept = clamp(title, TITLE_MAX)
    if not kept:
        return refusal(TITLE_NEEDED, "no_title", 400)
    wanted = slugify(slug or kept)
    if not wanted:
        return refusal(SLUG_NEEDED, "no_slug", 400)
    if await get_post(bot.db, guild.id, wanted) is not None:
        return refusal(SLUG_TAKEN.format(slug=wanted), "slug_taken", 409)
    post_id = await create_post(
        bot.db, guild.id, slug=wanted, title=kept, by=actor_id(actor)
    )
    row = await get_post_by_id(bot.db, post_id)
    await note(bot, guild, row, CREATED, actor, via=via)
    return Outcome(True, CREATED_SAID.format(title=kept), value=row)


async def save_post(
    bot: Any,
    guild: Any,
    row: Any,
    actor: Any,
    *,
    title: Any = ...,
    body: Any = ...,
    channel_id: Any = ...,
    style: Any = ...,
    pin: Any = ...,
    via: str = VIA_DISCORD,
) -> Outcome:
    """The one write both doors make. Anything left out keeps what the row already says."""
    wanted_title = row_value(row, "title") if title is ... else clamp(title, TITLE_MAX)
    wanted_body = str(row_value(row, "body", "")) if body is ... else str(body or "")
    kept_style = (
        wanted_style(row_value(row, "style", PLAIN))
        if style is ...
        else wanted_style(style, wanted_style(row_value(row, "style", PLAIN)))
    )
    kept_pin = bool(row_value(row, "pin")) if pin is ... else bool(pin)
    if not wanted_title:
        return refusal(TITLE_NEEDED, "no_title", 400)
    if channel_id is ...:
        kept_channel = row_value(row, "channel_id")
    elif not channel_id:
        kept_channel = None
    else:
        kept_channel = known_channel(guild, channel_id)
        if kept_channel is None:
            return refusal(
                UNKNOWN_CHANNEL.format(given=str(channel_id)[:40]), "unknown_channel", 400
            )
    said = refused_title(wanted_title, kept_style)
    if said is not None:
        return refusal(said, "title_too_long", 400)
    said = refused_body(wanted_body, kept_style, "saved")
    if said is not None:
        return refusal(said, "body_too_long", 400)
    await set_post_fields(
        bot.db,
        int(row["id"]),
        by=actor_id(actor),
        title=wanted_title,
        body=wanted_body,
        channel_id=kept_channel,
        style=kept_style,
        pin=1 if kept_pin else 0,
    )
    fresh = await get_post_by_id(bot.db, int(row["id"]))
    await note(bot, guild, fresh, SAVED, actor, via=via, pending=changes_pending(fresh))
    return Outcome(True, SAVED_SAID.format(title=wanted_title), value=fresh)


def guard_allows(bot: Any, channel_id: Any) -> bool:
    guard = getattr(bot, "guard", None)
    return guard is None or guard.allows_channel(channel_id)


def guard_refusal(bot: Any) -> str:
    guard = getattr(bot, "guard", None)
    return guard.refusal_message() if guard is not None else ""


def channel_of(bot: Any, guild: Any, channel_id: Any) -> Any:
    if not channel_id:
        return None
    found = bot.get_channel(int(channel_id))
    if found is None and guild is not None:
        found = guild.get_channel(int(channel_id))
    return found


async def _existing_message(bot: Any, guild: Any, row: Any, channel: Any, actor: Any, via: str):
    """The message this row already has, or None once a 404 has been written down."""
    message_id = row_value(row, "message_id")
    if not message_id:
        return None
    try:
        return await channel.fetch_message(int(message_id))
    except discord.NotFound:
        await clear_posted(bot.db, int(row["id"]))
        await note(bot, guild, row, MESSAGE_GONE, actor, via=via, message_id=int(message_id))
        return None


async def _pin(bot: Any, guild: Any, row: Any, message: Any, actor: Any, via: str) -> None:
    """Checklist 12: the row is already written; a pin that fails never undoes the post."""
    if not row_value(row, "pin") or bool(getattr(message, "pinned", False)):
        return
    try:
        await message.pin(reason="Black Bloc keeps this post pinned")
    except discord.HTTPException as exc:
        await note(bot, guild, row, PIN_FAILED, actor, via=via, reason=str(exc))
        return
    await note(bot, guild, row, PINNED, actor, via=via, message_id=int(message.id))


async def publish_post(
    bot: Any, guild: Any, row: Any, actor: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Post it the first time, edit it in place every time after — never a second copy."""
    title = str(row_value(row, "title", ""))
    channel_id = row_value(row, "channel_id")
    if not channel_id:
        return refusal(NO_CHANNEL_YET.format(title=title), "no_channel", 409)
    body = str(row_value(row, "body", "") or "")
    style = wanted_style(row_value(row, "style", PLAIN))
    if not body.strip():
        return refusal(NOTHING_TO_POST.format(title=title), "nothing_to_post", 409)
    said = refused_title(title, style)
    if said is not None:
        return refusal(said, "title_too_long", 400)
    said = refused_body(body, style, "posted")
    if said is not None:
        return refusal(said, "body_too_long", 400)
    if not guard_allows(bot, channel_id):
        await note(
            bot, guild, row, WOULD_POST, actor, via=via, channel=where_words(guild, channel_id)
        )
        return refusal(guard_refusal(bot), "test_mode", 409)
    channel = channel_of(bot, guild, channel_id)
    if channel is None:
        await note(bot, guild, row, POST_FAILED, actor, via=via, reason=CHANNEL_GONE)
        return refusal(
            POST_FAILED_SAID.format(title=title, reason=CHANNEL_GONE), "post_failed", 409
        )
    payload = render_message(row) | {
        "allowed_mentions": allowed_mentions_for(guild, body, actor)
    }
    message = await _existing_message(bot, guild, row, channel, actor, via)
    try:
        if message is not None:
            await message.edit(**payload)
            kind, said = UPDATED, UPDATED_SAID
        else:
            message = await channel.send(**payload)
            kind, said = POSTED, POSTED_SAID
    except discord.HTTPException as exc:
        await note(bot, guild, row, POST_FAILED, actor, via=via, reason=str(exc))
        return refusal(
            POST_FAILED_SAID.format(title=title, reason=str(exc)), "post_failed", 409
        )
    await set_posted(bot.db, int(row["id"]), int(message.id), hash_of(row), by=actor_id(actor))
    await note(bot, guild, row, kind, actor, via=via, message_id=int(message.id))
    await _pin(bot, guild, row, message, actor, via)
    fresh = await get_post_by_id(bot.db, int(row["id"]))
    return Outcome(
        True, said.format(title=title, where=where_words(guild, channel_id)), value=fresh
    )


async def take_down_post(
    bot: Any, guild: Any, row: Any, actor: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """The message goes; every word stays on the row."""
    title = str(row_value(row, "title", ""))
    message_id = row_value(row, "message_id")
    if not message_id:
        return refusal(NOT_POSTED.format(title=title), "not_posted", 409)
    channel_id = row_value(row, "channel_id")
    if not guard_allows(bot, channel_id):
        await note(
            bot,
            guild,
            row,
            WOULD_TAKE_DOWN,
            actor,
            via=via,
            message_id=int(message_id),
            channel=where_words(guild, channel_id),
        )
        return refusal(guard_refusal(bot), "test_mode", 409)
    channel = channel_of(bot, guild, channel_id)
    if channel is not None:
        try:
            message = await channel.fetch_message(int(message_id))
            await message.delete()
        except discord.NotFound:
            log.info("posts: %s had already lost its message", row_value(row, "slug"))
        except discord.HTTPException as exc:
            await note(bot, guild, row, POST_FAILED, actor, via=via, reason=str(exc))
            return refusal(
                TAKE_DOWN_FAILED_SAID.format(title=title, reason=str(exc)), "post_failed", 409
            )
    await clear_posted(bot.db, int(row["id"]))
    await note(bot, guild, row, TAKEN_DOWN, actor, via=via, message_id=int(message_id))
    fresh = await get_post_by_id(bot.db, int(row["id"]))
    return Outcome(True, TAKEN_DOWN_SAID.format(title=title), value=fresh)


async def reset_post(
    bot: Any, guild: Any, row: Any, actor: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """The words it shipped with, back. The channel a staffer chose is left alone."""
    entry = seed_entry(row_value(row, "slug"))
    if entry is None or not is_seeded(row):
        return refusal(
            NOT_SEEDED.format(slug=row_value(row, "slug")), "not_seeded", 409
        )
    await set_post_fields(
        bot.db,
        int(row["id"]),
        by=actor_id(actor),
        title=entry["title"],
        body=entry.get("body", ""),
        style=wanted_style(entry.get("style")),
        pin=1 if entry.get("pin", True) else 0,
        seed_hash=seed_hash(entry),
    )
    fresh = await get_post_by_id(bot.db, int(row["id"]))
    await note(bot, guild, fresh, RESET, actor, via=via)
    return Outcome(True, RESET_SAID.format(title=entry["title"]), value=fresh)


async def remove_post(
    bot: Any, guild: Any, row: Any, actor: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """A post staff wrote here, and only while nothing of it is in Discord."""
    title = str(row_value(row, "title", ""))
    if is_seeded(row):
        return refusal(
            SEEDED_CANNOT_BE_DELETED.format(slug=row_value(row, "slug")), "seeded_post", 409
        )
    if is_posted(row):
        return refusal(POSTED_CANNOT_BE_DELETED.format(title=title), "still_posted", 409)
    await note(bot, guild, row, DELETED, actor, via=via)
    await delete_post(bot.db, int(row["id"]))
    return Outcome(True, DELETED_SAID.format(title=title), value=None)


async def set_mode(
    bot: Any, guild: Any, actor: Any, value: Any, *, via: str = VIA_DISCORD
) -> str:
    await bot.store.set(guild.id, MODE_KEY, value, by=actor_id(actor))
    await log_action(
        bot,
        guild,
        kind_via("post.mode", via),
        actor=actor,
        details={"mode": value, "via": via},
    )
    return MODE_ON_SAID if value == ON else MODE_OFF_SAID


# --- the sweep --------------------------------------------------------------------------------


async def reconcile_posts(bot: Any) -> dict[str, int]:
    """Checklist 4/25: a message somebody deleted by hand is forgotten, and a pin put back."""
    done = {"gone": 0, "pinned": 0}
    db = getattr(bot, "db", None)
    if db is None or not getattr(db, "is_connected", False):
        return done
    known = {int(guild.id): guild for guild in list(getattr(bot, "guilds", ()) or ())}
    for row in await posted_posts(db):
        guild = known.get(int(row["guild_id"]))
        if guild is None or bool(getattr(guild, "unavailable", False)):
            continue
        channel = channel_of(bot, guild, row_value(row, "channel_id"))
        if channel is None:
            continue
        try:
            message = await channel.fetch_message(int(row["message_id"]))
        except discord.NotFound:
            await clear_posted(db, int(row["id"]))
            await note(
                bot,
                guild,
                row,
                MESSAGE_GONE,
                None,
                via=VIA_BOOT,
                message_id=int(row["message_id"]),
            )
            done["gone"] += 1
            continue
        except discord.HTTPException as exc:
            log.warning("posts: %s could not be re-read — %s", row_value(row, "slug"), exc)
            continue
        if row_value(row, "pin") and not bool(getattr(message, "pinned", False)):
            before = done["pinned"]
            await _pin(bot, guild, row, message, None, VIA_BOOT)
            done["pinned"] = before + (1 if bool(getattr(message, "pinned", False)) else 0)
    return done


__all__ = [
    "CAPS",
    "CREATED",
    "DELETED",
    "EMBED",
    "MESSAGE_GONE",
    "MODE_KEY",
    "MODE_OFF_SAID",
    "MODE_ON_SAID",
    "NOT_POSTED",
    "NOTHING_TO_POST",
    "NO_CHANNEL_YET",
    "NO_SUCH_POST",
    "OFF",
    "ON",
    "PAGE",
    "PANEL_EMPTY",
    "PANEL_INTRO",
    "PANEL_MINUTES_KEY",
    "PANEL_TIMEOUT_FOOTER",
    "PANEL_TITLE",
    "PINNED",
    "PIN_FAILED",
    "PIN_IT",
    "PLAIN",
    "POSTED",
    "POSTED_CANNOT_BE_DELETED",
    "POSTS_OFF",
    "POST_FAILED",
    "POST_IT",
    "PUT_THE_ORIGINAL_BACK",
    "RESET",
    "SAVED",
    "SEEDED_CANNOT_BE_DELETED",
    "SITE_BUTTON",
    "SLUG_NEEDED",
    "SLUG_TAKEN",
    "STATUS_PENDING",
    "STYLES",
    "TAKEN_DOWN",
    "TAKE_IT_DOWN",
    "TITLE_MAX",
    "TITLE_NEEDED",
    "UNKNOWN_CHANNEL",
    "UPDATED",
    "UPDATE_THE_POST",
    "WOULD_POST",
    "WOULD_TAKE_DOWN",
    "allowed_mentions_for",
    "body_hash",
    "cap_for",
    "changes_pending",
    "channel_name",
    "clamp",
    "clear_posted",
    "count_posts",
    "create_post",
    "delete_post",
    "get_post",
    "get_post_by_id",
    "guard_allows",
    "guard_refusal",
    "hash_of",
    "is_posted",
    "is_seeded",
    "known_channel",
    "list_posts",
    "load_seed",
    "make_post",
    "move_label",
    "panel_minutes",
    "posted_posts",
    "posts_are_on",
    "preview_of",
    "publish_post",
    "reconcile_posts",
    "refresh_seeds",
    "refused_body",
    "refused_title",
    "remove_post",
    "render_message",
    "reset_post",
    "row_value",
    "save_post",
    "seed_entries",
    "seed_entry",
    "seed_hash",
    "seed_posts",
    "set_mode",
    "set_post_fields",
    "set_posted",
    "site_page_url",
    "slugify",
    "status_words",
    "take_down_post",
    "too_long",
    "wanted_style",
    "where_words",
]
