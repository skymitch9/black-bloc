from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import chat_panel
from .actionlog import log_action
from .channel_notes import NOTE_CHARS, clean_note, clear_note, get_note, set_note
from .logkinds import VIA_BOOT, VIA_DISCORD, kind_via
from .panels import Outcome, refusal
from .settings_store import (
    CHANNEL_DRAFT_MISSING_KEY,
    CHANNEL_DRAFT_NONE_KEY,
    CHANNEL_DRAFT_RESET_KEY,
    CHANNEL_DRAFT_USED_KEY,
    CHANNEL_NOTE_NOTHING_KEY,
    CHANNEL_NOTE_SAVED_KEY,
    CHANNEL_NOTE_TOO_LONG_KEY,
)

log = logging.getLogger(__name__)

SEED_FILE = Path(__file__).with_name("channel_drafts_seed.json")

DRAFT = "draft"
USED = "used"
REWRITTEN = "rewritten"
NONE = "none"
STATUSES = (DRAFT, USED, REWRITTEN, NONE)
NO_DRAFT_CODE = "no_draft"


def load_seed() -> dict[str, dict[str, Any]]:
    try:
        return dict(json.loads(SEED_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        log.warning("channel drafts: the seed could not be read — %s: %s", type(exc).__name__, exc)
        return {}


def now() -> str:
    return datetime.now(UTC).isoformat()


async def drafts_for(db: Any, guild_id: Any) -> dict[int, Any]:
    cur = await db.conn.execute(
        "SELECT guild_id, channel_id, draft, status, decided_by, decided_at FROM channel_drafts "
        "WHERE guild_id = ?",
        (int(guild_id),),
    )
    return {int(row["channel_id"]): row for row in await cur.fetchall()}


async def get_draft(db: Any, guild_id: Any, channel_id: Any) -> Any:
    cur = await db.conn.execute(
        "SELECT guild_id, channel_id, draft, status, decided_by, decided_at FROM channel_drafts "
        "WHERE guild_id = ? AND channel_id = ?",
        (int(guild_id), int(channel_id)),
    )
    return await cur.fetchone()


async def set_status(db: Any, guild_id: Any, channel_id: Any, status: str, by: Any) -> None:
    decided = status != DRAFT
    await db.conn.execute(
        "UPDATE channel_drafts SET status = ?, decided_by = ?, decided_at = ? "
        "WHERE guild_id = ? AND channel_id = ?",
        (
            status,
            int(by) if decided and by else None,
            now() if decided else None,
            int(guild_id),
            int(channel_id),
        ),
    )
    await db.conn.commit()


def effective(status: Any, draft: Any, note: Any) -> str:
    """The note table is the truth for the text; the stored status only says why it is absent."""
    if note:
        return USED if str(note) == str(draft) else REWRITTEN
    return DRAFT if str(status or DRAFT) == DRAFT else NONE


async def seed_drafts(db: Any, guild: Any) -> tuple[int, int]:
    """Inserts the drafts this guild lacks; a decided row or a staff note is never touched."""
    here = {int(one.id) for one in getattr(guild, "text_channels", ()) or ()}
    made = noted = 0
    for key, entry in load_seed().items():
        channel_id = int(key)
        if channel_id not in here:
            continue
        final = bool(entry.get("final"))
        cur = await db.conn.execute(
            "INSERT OR IGNORE INTO channel_drafts(guild_id, channel_id, draft, status, decided_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                int(guild.id),
                channel_id,
                str(entry["draft"]),
                USED if final else DRAFT,
                now() if final else None,
            ),
        )
        await db.conn.commit()
        if not cur.rowcount:
            continue
        made += 1
        if final and await get_note(db, guild.id, channel_id) is None:
            await set_note(db, guild.id, channel_id, clean_note(entry["draft"]))
            noted += 1
    return made, noted


async def seed_and_log(bot: Any, guild: Any) -> int:
    made, noted = await seed_drafts(bot.db, guild)
    if made:
        await log_action(
            bot,
            guild,
            "chat.channel_drafts_seeded",
            details={"count": made, "notes": noted, "via": VIA_BOOT},
        )
    return made


def review_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    drafted = [row for row in rows if row.get("draft") is not None]
    reviewed = sum(1 for row in drafted if row.get("status") != DRAFT)
    return {"total": len(drafted), "reviewed": reviewed, "drafts_left": len(drafted) - reviewed}


def said(bot: Any, guild: Any, key: str, **values: Any) -> str:
    return chat_panel.words(bot.store, guild.id, key, **values)


async def _decided(
    bot: Any, guild: Any, actor: Any, channel: Any, kind: str, status: str, via: str, **extra: Any
) -> None:
    await set_status(bot.db, guild.id, channel.id, status, chat_panel.actor_id(actor))
    await log_action(
        bot,
        guild,
        kind_via(kind, via),
        actor=actor,
        details={
            "channel_id": str(channel.id),
            "channel": channel.name,
            "status": status,
            "via": via,
            **extra,
        },
    )


async def _found(bot: Any, guild: Any, channel_id: Any) -> tuple[Any, Any, Outcome | None]:
    channel = chat_panel.text_channel(guild, channel_id)
    if channel is None:
        return None, None, chat_panel.no_such_channel(bot, guild, channel_id)
    row = await get_draft(bot.db, guild.id, channel.id)
    return channel, row, None


def no_draft(bot: Any, guild: Any, channel: Any) -> Outcome:
    return refusal(
        said(bot, guild, CHANNEL_DRAFT_MISSING_KEY, channel=channel.name), NO_DRAFT_CODE, 404
    )


async def use_draft(
    bot: Any, guild: Any, actor: Any, channel_id: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    channel, row, refused = await _found(bot, guild, channel_id)
    if refused is not None:
        return refused
    if row is None:
        return no_draft(bot, guild, channel)
    text = clean_note(row["draft"])
    await set_note(bot.db, guild.id, channel.id, text, by=chat_panel.actor_id(actor))
    await _decided(bot, guild, actor, channel, "chat.channel_draft_used", USED, via, note=text)
    return Outcome(True, said(bot, guild, CHANNEL_DRAFT_USED_KEY, channel=channel.name), value=text)


async def save_wording(
    bot: Any, guild: Any, actor: Any, channel_id: Any, text: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Both doors' save: a drafted channel records the decision, any other keeps the plain note."""
    channel, row, refused = await _found(bot, guild, channel_id)
    if refused is not None:
        return refused
    if row is None:
        return await chat_panel.save_channel_note(bot, guild, actor, channel.id, text, via=via)
    note = clean_note(text)
    if not note:
        return await no_note(bot, guild, actor, channel.id, via=via)
    if len(note) > NOTE_CHARS:
        return refusal(
            said(
                bot,
                guild,
                CHANNEL_NOTE_TOO_LONG_KEY,
                length=len(note),
                limit=NOTE_CHARS,
                over=len(note) - NOTE_CHARS,
            ),
            chat_panel.NOTE_TOO_LONG_CODE,
            422,
        )
    await set_note(bot.db, guild.id, channel.id, note, by=chat_panel.actor_id(actor))
    if note == clean_note(row["draft"]):
        await _decided(bot, guild, actor, channel, "chat.channel_draft_used", USED, via, note=note)
        return Outcome(
            True, said(bot, guild, CHANNEL_DRAFT_USED_KEY, channel=channel.name), value=note
        )
    await _decided(
        bot, guild, actor, channel, "chat.channel_draft_rewritten", REWRITTEN, via, note=note
    )
    return Outcome(True, said(bot, guild, CHANNEL_NOTE_SAVED_KEY, channel=channel.name), value=note)


async def no_note(
    bot: Any, guild: Any, actor: Any, channel_id: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    channel, row, refused = await _found(bot, guild, channel_id)
    if refused is not None:
        return refused
    if row is None:
        return await chat_panel.clear_channel_note(bot, guild, actor, channel.id, via=via)
    had = await clear_note(bot.db, guild.id, channel.id)
    if not had and str(row["status"]) == NONE:
        return Outcome(True, said(bot, guild, CHANNEL_NOTE_NOTHING_KEY, channel=channel.name))
    await _decided(bot, guild, actor, channel, "chat.channel_draft_none", NONE, via)
    return Outcome(True, said(bot, guild, CHANNEL_DRAFT_NONE_KEY, channel=channel.name))


async def reset_draft(
    bot: Any, guild: Any, actor: Any, channel_id: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    channel, row, refused = await _found(bot, guild, channel_id)
    if refused is not None:
        return refused
    if row is None:
        return no_draft(bot, guild, channel)
    had = await clear_note(bot.db, guild.id, channel.id)
    if had or str(row["status"]) != DRAFT:
        await _decided(bot, guild, actor, channel, "chat.channel_draft_reset", DRAFT, via)
    return Outcome(True, said(bot, guild, CHANNEL_DRAFT_RESET_KEY, channel=channel.name))


__all__ = [
    "DRAFT",
    "NONE",
    "REWRITTEN",
    "SEED_FILE",
    "STATUSES",
    "USED",
    "drafts_for",
    "effective",
    "get_draft",
    "load_seed",
    "no_note",
    "reset_draft",
    "review_counts",
    "save_wording",
    "seed_and_log",
    "seed_drafts",
    "set_status",
    "use_draft",
]
