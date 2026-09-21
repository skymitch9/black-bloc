from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request

from ... import posts
from ...logkinds import VIA_WEBSITE
from ..auth import Refused
from ..names import resolve_one
from ..writes import actor_for, reader_dependency, require_db, require_guild, writer_dependency

log = logging.getLogger(__name__)

TEST_MODE_NOTE = (
    "Black Bloc is in test mode, so a post only reaches #{channel} or a channel it made "
    "itself. **Post it** on anything else writes down what it would have sent and sends "
    "nothing."
)
POSTS_ARE_OFF = (
    "Posts are off for this server, so **Post it** and **Take it down** refuse in words and "
    "`/posts` is hidden. Every word written here is kept — a Lead turns them back on from the "
    "Settings page under **posts**."
)
POSTS_ARE_SHADOW = (
    "Posts are in **shadow**: **Post it** sends the real message to {where} and keeps it edited "
    "there, whatever channel a post names, so nothing reaches members yet. Turning posts **on** "
    "is the go-live — the next **Post it** goes to the post's own channel and the shadow copy "
    "is removed."
)
NO_SHADOW_CHANNEL_NOTE = (
    "Posts are in **shadow** and there is nowhere to put a shadow copy: this server has neither "
    "a test channel nor a log channel, so **Post it** refuses. Set **log_channel_id** on the "
    "Settings page, or turn posts on."
)


def now() -> str:
    return datetime.now(UTC).isoformat()


def person(guild: Any, user_id: Any) -> str | None:
    if not user_id:
        return None
    return resolve_one(guild, user_id)["display_name"] or str(user_id)


def post_row(bot: Any, guild: Any, row: Any) -> dict[str, Any]:
    channel_id = posts.row_value(row, "channel_id")
    style = posts.wanted_style(posts.row_value(row, "style", posts.PLAIN))
    return {
        "id": str(row["id"]),
        "slug": str(row["slug"]),
        "title": row["title"],
        "body": posts.row_value(row, "body", ""),
        "style": style,
        "cap": posts.cap_for(style),
        "title_cap": posts.TITLE_MAX,
        "pin": bool(posts.row_value(row, "pin")),
        "channel_id": str(channel_id) if channel_id else None,
        "channel_name": posts.channel_name(guild, channel_id),
        "posted": posts.is_posted(row),
        "posted_where": posts.posted_where(row),
        "pinned": posts.is_posted(row) and bool(posts.row_value(row, "pin")),
        "changes_pending": posts.changes_pending(row),
        "status": posts.status_words(row),
        "move": posts.move_label(row),
        "message_id": str(posts.row_value(row, "message_id"))
        if posts.row_value(row, "message_id")
        else None,
        "shadow_message_id": str(posts.shadow_id(row)) if posts.shadow_id(row) else None,
        "posted_at": posts.row_value(row, "posted_at"),
        "posted_by": str(posts.row_value(row, "posted_by"))
        if posts.row_value(row, "posted_by")
        else None,
        "posted_by_name": person(guild, posts.row_value(row, "posted_by")),
        "seeded": posts.is_seeded(row),
        "updated_at": row["updated_at"],
        "updated_by": str(posts.row_value(row, "updated_by"))
        if posts.row_value(row, "updated_by")
        else None,
        "updated_by_name": person(guild, posts.row_value(row, "updated_by")),
    }


def version_row(
    guild: Any, row: Any, *, current: bool, limit: int, shipped: bool = False
) -> dict[str, Any]:
    channel_id = posts.row_value(row, "channel_id")
    return {
        "n": int(row["n"]),
        "title": row["title"],
        "summary": posts.summary_of(row, limit),
        "style": posts.wanted_style(posts.row_value(row, "style", posts.PLAIN)),
        "channel_id": str(channel_id) if channel_id else None,
        "channel_name": posts.channel_name(guild, channel_id),
        "pin": bool(posts.row_value(row, "pin")),
        "saved_at": row["saved_at"],
        "saved_by": str(posts.row_value(row, "saved_by"))
        if posts.row_value(row, "saved_by")
        else None,
        "saved_by_name": person(guild, posts.row_value(row, "saved_by")),
        "via": posts.row_value(row, "via"),
        "because": posts.row_value(row, "because"),
        "because_said": posts.because_words(
            posts.row_value(row, "because"), shipped=shipped
        ),
        "shipped": shipped,
        "current": current,
    }


def guard_line(bot: Any, guild: Any) -> dict[str, Any]:
    """What the page's "how it will post" line reads; one home for the test-mode sentence."""
    testing = bool(getattr(bot.settings, "test_mode", False))
    channel = guild.get_channel(bot.settings.test_channel_id) if testing and guild else None
    name = getattr(channel, "name", None)
    return {
        "test_mode": testing,
        "test_channel": name,
        "said": TEST_MODE_NOTE.format(channel=name or "the test channel") if testing else None,
    }


def shadow_line(bot: Any, guild: Any) -> dict[str, Any]:
    """Where a shadow copy goes, so the page can say it beside every post."""
    channel_id = posts.shadow_channel_id(bot, guild)
    return {
        "channel_id": str(channel_id) if channel_id else None,
        "channel_name": posts.channel_name(guild, channel_id),
    }


def styles() -> list[dict[str, Any]]:
    return [
        {"style": style, "cap": posts.CAPS[style], "label": posts.STYLE_WORDS[style]}
        for style in posts.STYLES
    ]


def refused(found: Any) -> None:
    """One shape for every move's refusal — the guard's is the same 409 `api/writes.py` uses."""
    raise Refused(found.status or 409, found.code or "refused", found.message)


def build_router(bot: Any) -> APIRouter:
    reader = reader_dependency(bot)
    writer = writer_dependency(bot)
    router = APIRouter(prefix="/api/posts", tags=["posts"])

    async def _staff(request: Request) -> Any:
        await reader(request)
        guild = require_guild(bot)
        require_db(bot)
        return guild

    async def _editor(request: Request) -> tuple[dict[str, Any], Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        return (who, guild)

    async def _wanted(guild: Any, slug: str) -> Any:
        row = await posts.get_post(bot.db, guild.id, slug)
        if row is None:
            raise Refused(404, "no_such_post", posts.NO_SUCH_POST.format(slug=slug[:60]))
        return row

    def _notes(guild: Any) -> list[str]:
        if posts.posts_are_off(bot.store, guild.id):
            return [POSTS_ARE_OFF]
        if not posts.in_shadow(bot.store, guild.id):
            return []
        where = posts.shadow_channel_id(bot, guild)
        if not where:
            return [NO_SHADOW_CHANNEL_NOTE]
        return [POSTS_ARE_SHADOW.format(where=posts.where_words(guild, where))]

    def _whole(guild: Any, row: Any, said: str | None = None) -> dict[str, Any]:
        found = {
            "post": post_row(bot, guild, row),
            "styles": styles(),
            "guard": guard_line(bot, guild),
            "mode": posts.mode_of(bot.store, guild.id),
            "shadow": shadow_line(bot, guild),
            "notes": _notes(guild),
            "read_at": now(),
        }
        return found if said is None else found | {"message": said}

    async def _move(request: Request, slug: str, run: Any, **extra: Any) -> dict[str, Any]:
        """Every write is the same four lines: gate, row, the shared move, the fresh shape."""
        who, guild = await _editor(request)
        row = await _wanted(guild, slug)
        found = await run(
            bot, guild, row, actor_for(bot, who, guild), via=VIA_WEBSITE, **extra
        )
        if not found.ok:
            refused(found)
        fresh = found.value if found.value is not None else row
        return _whole(guild, fresh, found.message)

    @router.get("")
    async def posts_index(request: Request) -> dict[str, Any]:
        guild = await _staff(request)
        rows = await posts.list_posts(bot.db, guild.id)
        return {
            "posts": [post_row(bot, guild, row) for row in rows],
            "mode": posts.mode_of(bot.store, guild.id),
            "may_edit": True,
            "styles": styles(),
            "guard": guard_line(bot, guild),
            "shadow": shadow_line(bot, guild),
            "notes": _notes(guild),
            "checked_at": now(),
        }

    @router.post("")
    async def post_new(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who, guild = await _editor(request)
        found = await posts.make_post(
            bot,
            guild,
            actor_for(bot, who, guild),
            title=payload.get("title"),
            slug=payload.get("slug"),
            via=VIA_WEBSITE,
        )
        if not found.ok:
            refused(found)
        return _whole(guild, found.value, found.message)

    @router.get("/{slug}")
    async def post_one(request: Request, slug: str) -> dict[str, Any]:
        guild = await _staff(request)
        return _whole(guild, await _wanted(guild, slug))

    @router.put("/{slug}")
    async def post_save(request: Request, slug: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await _move(
            request,
            slug,
            posts.save_post,
            title=payload.get("title", ...),
            body=payload.get("body", ...),
            channel_id=payload.get("channel_id", ...),
            style=payload.get("style", ...),
            pin=payload.get("pin", ...),
        )

    @router.post("/{slug}/publish")
    async def post_publish(request: Request, slug: str) -> dict[str, Any]:
        return await _move(request, slug, posts.publish_post)

    @router.post("/{slug}/takedown")
    async def post_takedown(request: Request, slug: str) -> dict[str, Any]:
        return await _move(request, slug, posts.take_down_post)

    async def _versions(guild: Any, row: Any) -> list[dict[str, Any]]:
        rows = await posts.list_versions(bot.db, int(row["id"]))
        limit = posts.summary_chars(bot.store, guild.id)
        top = int(rows[0]["n"]) if rows else None
        return [
            version_row(
                guild,
                one,
                current=int(one["n"]) == top,
                limit=limit,
                shipped=posts.is_shipped_version(row, one),
            )
            for one in rows
        ]

    @router.get("/{slug}/versions")
    async def post_versions(request: Request, slug: str) -> dict[str, Any]:
        guild = await _staff(request)
        row = await _wanted(guild, slug)
        found = await _versions(guild, row)
        return {
            "slug": str(row["slug"]),
            "versions": found,
            "count": len(found),
            "keep": posts.versions_keep(bot.store, guild.id),
            "read_at": now(),
        }

    @router.get("/{slug}/versions/{n}")
    async def post_version(request: Request, slug: str, n: int) -> dict[str, Any]:
        guild = await _staff(request)
        row = await _wanted(guild, slug)
        version = await posts.get_version(bot.db, int(row["id"]), n)
        if version is None:
            raise Refused(
                404,
                "no_such_version",
                posts.NO_SUCH_VERSION.format(n=n, title=str(row["title"])),
            )
        top = await posts.latest_n(bot.db, int(row["id"]))
        limit = posts.summary_chars(bot.store, guild.id)
        return {
            "slug": str(row["slug"]),
            "version": version_row(
                guild,
                version,
                current=int(n) == top,
                limit=limit,
                shipped=posts.is_shipped_version(row, version),
            )
            | {"body": posts.row_value(version, "body", "")},
            "preview": {
                "style": posts.wanted_style(posts.row_value(version, "style", posts.PLAIN)),
                "title": version["title"],
                "body": posts.row_value(version, "body", ""),
                "cap": posts.cap_for(posts.row_value(version, "style", posts.PLAIN)),
            },
            "read_at": now(),
        }

    @router.post("/{slug}/versions/{n}/restore")
    async def post_version_restore(request: Request, slug: str, n: int) -> dict[str, Any]:
        who, guild = await _editor(request)
        row = await _wanted(guild, slug)
        found = await posts.restore_version(
            bot, guild, row, actor_for(bot, who, guild), n, via=VIA_WEBSITE
        )
        if not found.ok:
            refused(found)
        fresh = found.value if found.value is not None else row
        return _whole(guild, fresh, found.message) | {
            "from_version": int(n),
            "versions": await _versions(guild, fresh),
        }

    @router.delete("/{slug}")
    async def post_delete(request: Request, slug: str) -> dict[str, Any]:
        who, guild = await _editor(request)
        row = await _wanted(guild, slug)
        found = await posts.remove_post(
            bot, guild, row, actor_for(bot, who, guild), via=VIA_WEBSITE
        )
        if not found.ok:
            refused(found)
        return {"deleted": slug, "message": found.message}

    return router


__all__ = [
    "build_router",
    "guard_line",
    "post_row",
    "shadow_line",
    "styles",
    "version_row",
]
