from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from .golive import now_iso

log = logging.getLogger(__name__)

FOUND = "found"
SILENT = "silent"
UNREADABLE = "unreadable"
OURS = "ours"
AUDIT_LOOK_BACK = 10
AUDIT_WINDOW = timedelta(minutes=5)
AUDIT_RETRY_SECONDS = 3.0
PICK_TEMPLATE = r"tbh:(?P<prompt_id>[0-9]+)"
NEW_TEMPLATE = r"tbhnew:(?P<prompt_id>[0-9]+)"
LOCKS_ATTR = "_timed_by_hand_locks"


def pick_id(prompt_id: int) -> str:
    return f"tbh:{int(prompt_id)}"


def new_id(prompt_id: int) -> str:
    return f"tbhnew:{int(prompt_id)}"


def role_ids_of(prompt: Any) -> list[int]:
    try:
        found = json.loads(prompt["role_ids"] or "[]")
    except (TypeError, ValueError):
        return []
    return [int(one) for one in found if str(one).isdigit()]


async def waiting_roles(db: Any, guild_id: int, user_id: int) -> set[int]:
    """Roles of this member already asked about and not attached yet: one post each."""
    cur = await db.conn.execute(
        "SELECT role_ids FROM timed_role_prompts WHERE guild_id = ? AND user_id = ? "
        "AND attached_at IS NULL",
        (int(guild_id), int(user_id)),
    )
    found: set[int] = set()
    for row in await cur.fetchall():
        found |= set(role_ids_of(row))
    return found


async def add_prompt(
    db: Any, guild_id: int, user_id: int, role_ids: Any, added_by: Any, audit: str
) -> int:
    cur = await db.conn.execute(
        "INSERT INTO timed_role_prompts(guild_id, user_id, role_ids, added_by, audit, posted_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            int(guild_id),
            int(user_id),
            json.dumps(sorted(int(one) for one in role_ids)),
            added_by,
            audit,
            now_iso(),
        ),
    )
    await db.conn.commit()
    return int(cur.lastrowid)


async def get_prompt(db: Any, prompt_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM timed_role_prompts WHERE id = ?", (int(prompt_id),))
    return await cur.fetchone()


async def set_message(db: Any, prompt_id: int, channel_id: int, message_id: int) -> None:
    await db.conn.execute(
        "UPDATE timed_role_prompts SET channel_id = ?, message_id = ? WHERE id = ?",
        (int(channel_id), int(message_id), int(prompt_id)),
    )
    await db.conn.commit()


async def drop_prompt(db: Any, prompt_id: int) -> None:
    await db.conn.execute("DELETE FROM timed_role_prompts WHERE id = ?", (int(prompt_id),))
    await db.conn.commit()


async def mark_attached(db: Any, prompt_id: int, menu_id: int, by: Any) -> bool:
    """One writer wins: only an unattached post is attached."""
    cur = await db.conn.execute(
        "UPDATE timed_role_prompts SET attached_menu_id = ?, attached_by = ?, attached_at = ? "
        "WHERE id = ? AND attached_at IS NULL",
        (int(menu_id), by, now_iso(), int(prompt_id)),
    )
    await db.conn.commit()
    return bool(cur.rowcount and cur.rowcount > 0)


async def retire_roles(db: Any, guild_id: int, user_id: int, role_ids: Any) -> int:
    """A role that came off closes the post waiting on it, so the next by-hand add asks again."""
    wanted = {int(one) for one in role_ids or ()}
    if not wanted:
        return 0
    cur = await db.conn.execute(
        "SELECT id, role_ids FROM timed_role_prompts WHERE guild_id = ? AND user_id = ? "
        "AND attached_at IS NULL",
        (int(guild_id), int(user_id)),
    )
    retired = 0
    for row in await cur.fetchall():
        if wanted & set(role_ids_of(row)):
            await db.conn.execute(
                "UPDATE timed_role_prompts SET attached_at = ? "
                "WHERE id = ? AND attached_at IS NULL",
                (now_iso(), row["id"]),
            )
            retired += 1
    await db.conn.commit()
    return retired


def entry_roles(entry: Any) -> set[int]:
    after = getattr(entry, "after", None)
    return {int(getattr(role, "id", 0)) for role in getattr(after, "roles", None) or ()}


async def who_added(
    guild: Any, member: Any, role_ids: Any, *, at: datetime | None = None
) -> tuple[int | None, str]:
    """(who, how sure): the audit entry that added these roles to this member, recent and named.

    Never a guess: without View Audit Log, or with no matching entry, nobody is named."""
    me = getattr(guild, "me", None)
    perms = getattr(me, "guild_permissions", None)
    reader = getattr(guild, "audit_logs", None)
    if perms is None or not getattr(perms, "view_audit_log", False) or reader is None:
        return None, UNREADABLE
    import discord

    wanted = {int(one) for one in role_ids or ()}
    now = at or datetime.now(UTC)
    try:
        async for entry in reader(
            limit=AUDIT_LOOK_BACK, action=discord.AuditLogAction.member_role_update
        ):
            if getattr(getattr(entry, "target", None), "id", None) != member.id:
                continue
            when = getattr(entry, "created_at", None)
            if when is not None and now - when > AUDIT_WINDOW:
                continue
            if not wanted & entry_roles(entry):
                continue
            user = getattr(entry, "user", None)
            if user is None:
                return None, SILENT
            if me is not None and int(getattr(user, "id", 0)) == int(getattr(me, "id", -1)):
                return None, OURS
            return int(user.id), FOUND
    except Exception as exc:
        log.info("timed roles: could not read the audit log on %s: %s", guild.id, exc)
        return None, UNREADABLE
    return None, SILENT


async def who_added_soon(guild: Any, member: Any, role_ids: Any) -> tuple[int | None, str]:
    """`who_added`, read once more after a short wait when the entry is not there yet."""
    found = await who_added(guild, member, role_ids)
    if found[1] != SILENT:
        return found
    await asyncio.sleep(AUDIT_RETRY_SECONDS)
    return await who_added(guild, member, role_ids)


def by_hand_locks(bot: Any) -> dict[tuple[int, int], Any]:
    found = getattr(bot, LOCKS_ATTR, None)
    if found is None:
        found = {}
        setattr(bot, LOCKS_ATTR, found)
    return found


__all__ = [
    "FOUND",
    "NEW_TEMPLATE",
    "AUDIT_RETRY_SECONDS",
    "OURS",
    "PICK_TEMPLATE",
    "SILENT",
    "UNREADABLE",
    "add_prompt",
    "by_hand_locks",
    "drop_prompt",
    "entry_roles",
    "get_prompt",
    "mark_attached",
    "new_id",
    "pick_id",
    "retire_roles",
    "role_ids_of",
    "set_message",
    "waiting_roles",
    "who_added",
    "who_added_soon",
]
