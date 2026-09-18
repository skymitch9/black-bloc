from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request

from ... import minutes as mins
from ...logkinds import VIA_WEBSITE
from ..auth import Refused
from ..names import resolve_one
from ..writes import actor_for, reader_dependency, require_db, require_guild, writer_dependency

log = logging.getLogger(__name__)

MINUTES_ARE_OFF = (
    "Meeting minutes are off for this server, so `/minutes` is hidden and Start refuses in "
    "words. This is a prototype and it ships off on purpose. Every meeting already recorded is "
    "kept — a Lead turns it on from the Settings page under **events**."
)
TEST_MODE_NOTE = (
    "Black Bloc is in test mode, so a meeting's announcement and its notes land in "
    "#{channel} rather than the channel they name. **Post again** obeys the same rule."
)
NO_TRANSCRIBER_NOTE = (
    "There is no speech-to-text key on this host, so Start refuses in words. The key is named "
    "`GROQ_API_KEY` and only the owner can set it."
)
NO_EXTENSION_NOTE = (
    "The voice-recording extension is not installed on this host, so Start refuses in words. It "
    "ships in the bot's image; a host without it can never take notes."
)


def now() -> str:
    return datetime.now(UTC).isoformat()


def person(guild: Any, user_id: Any) -> str | None:
    if not user_id:
        return None
    return resolve_one(guild, user_id)["display_name"] or str(user_id)


def meeting_row(guild: Any, row: Any, *, lines: int = 0) -> dict[str, Any]:
    channel_id = mins.row_value(row, "channel_id")
    notes_channel = mins.row_value(row, "notes_channel_id")
    return {
        "id": str(row["id"]),
        "channel_id": str(channel_id) if channel_id else None,
        "channel_name": mins.where_words(guild, channel_id),
        "started_by": str(mins.row_value(row, "started_by") or ""),
        "started_by_name": person(guild, mins.row_value(row, "started_by")),
        "started_at": row["started_at"],
        "ended_at": mins.row_value(row, "ended_at"),
        "ended_reason": mins.row_value(row, "ended_reason"),
        "status": str(mins.row_value(row, "status", mins.RECORDING)),
        "status_words": mins.status_words(row),
        "notes": str(mins.row_value(row, "notes", "")),
        "notes_cap": mins.NOTES_MAX,
        "notes_channel_id": str(notes_channel) if notes_channel else None,
        "notes_channel_name": mins.where_words(guild, notes_channel),
        "notes_message_id": str(mins.row_value(row, "notes_message_id") or "") or None,
        "posted": bool(mins.row_value(row, "notes_message_id")),
        "lines": lines,
    }


def transcript_rows(rows: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": str(row["id"]),
            "speaker": str(row["speaker"]),
            "speaker_id": str(row["speaker_id"]),
            "started_at": row["started_at"],
            "text": str(row["text"]),
        }
        for row in rows
    ]


def guard_line(bot: Any, guild: Any) -> dict[str, Any]:
    testing = bool(getattr(bot.settings, "test_mode", False))
    channel = guild.get_channel(bot.settings.test_channel_id) if testing and guild else None
    name = getattr(channel, "name", None)
    return {
        "test_mode": testing,
        "test_channel": name,
        "said": TEST_MODE_NOTE.format(channel=name or "the test channel") if testing else None,
    }


def host_line(bot: Any) -> dict[str, Any]:
    """What this host can actually do, so the page never promises what it cannot deliver."""
    return {
        "extension": mins.extension_available(),
        "opus": mins.opus_available(),
        "transcriber": mins.transcribe_configured(bot),
        "notes_writer": mins.notes_configured(bot),
    }


def notes_for(bot: Any, guild: Any) -> list[str]:
    found: list[str] = []
    if mins.minutes_are_off(bot.store, guild.id):
        found.append(MINUTES_ARE_OFF)
    if not mins.extension_available():
        found.append(NO_EXTENSION_NOTE)
    if not mins.transcribe_configured(bot):
        found.append(NO_TRANSCRIBER_NOTE)
    return found


def refused(found: Any) -> None:
    raise Refused(found.status or 409, found.code or "refused", found.message)


def build_router(bot: Any) -> APIRouter:
    reader = reader_dependency(bot)
    writer = writer_dependency(bot)
    router = APIRouter(prefix="/api/minutes", tags=["minutes"])

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

    async def _wanted(guild: Any, meeting_id: str) -> Any:
        row = await mins.get_meeting(bot.db, guild.id, meeting_id)
        if row is None:
            raise Refused(
                404,
                "no_such_meeting",
                mins.NO_SUCH_MEETING.format(meeting_id=str(meeting_id)[:20]),
            )
        return row

    async def _whole(guild: Any, row: Any, said: str | None = None) -> dict[str, Any]:
        rows = await mins.lines_of(bot.db, int(row["id"]))
        found = {
            "meeting": meeting_row(guild, row, lines=len(rows)),
            "transcript": transcript_rows(rows),
            "speakers": mins.speakers_of(rows),
            "mode": mins.mode_of(bot.store, guild.id),
            "guard": guard_line(bot, guild),
            "host": host_line(bot),
            "notes": notes_for(bot, guild),
            "read_at": now(),
        }
        return found if said is None else found | {"message": said}

    @router.get("")
    async def minutes_index(request: Request) -> dict[str, Any]:
        guild = await _staff(request)
        rows = await mins.list_meetings(bot.db, guild.id)
        return {
            "meetings": [meeting_row(guild, row) for row in rows],
            "mode": mins.mode_of(bot.store, guild.id),
            "may_edit": True,
            "guard": guard_line(bot, guild),
            "host": host_line(bot),
            "notes": notes_for(bot, guild),
            "checked_at": now(),
        }

    @router.get("/{meeting_id}")
    async def minutes_one(request: Request, meeting_id: str) -> dict[str, Any]:
        guild = await _staff(request)
        return await _whole(guild, await _wanted(guild, meeting_id))

    @router.put("/{meeting_id}")
    async def minutes_save(
        request: Request, meeting_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who, guild = await _editor(request)
        row = await _wanted(guild, meeting_id)
        found = await mins.edit_notes(
            bot, guild, row, actor_for(bot, who, guild), payload.get("notes"), via=VIA_WEBSITE
        )
        if not found.ok:
            refused(found)
        return await _whole(guild, await _wanted(guild, meeting_id), found.message)

    @router.post("/{meeting_id}/write")
    async def minutes_write(request: Request, meeting_id: str) -> dict[str, Any]:
        _who, guild = await _editor(request)
        row = await _wanted(guild, meeting_id)
        if str(mins.row_value(row, "status", mins.RECORDING)) == mins.RECORDING:
            raise Refused(
                409, "still_recording", mins.STILL_RECORDING.format(meeting_id=row["id"])
            )
        found = await mins.write_notes(bot, guild, row, via=VIA_WEBSITE)
        if not found.ok:
            refused(found)
        return await _whole(guild, await _wanted(guild, meeting_id), found.message)

    @router.post("/{meeting_id}/post")
    async def minutes_post(request: Request, meeting_id: str) -> dict[str, Any]:
        _who, guild = await _editor(request)
        row = await _wanted(guild, meeting_id)
        if str(mins.row_value(row, "status", mins.RECORDING)) == mins.RECORDING:
            raise Refused(
                409, "still_recording", mins.STILL_RECORDING.format(meeting_id=row["id"])
            )
        found = await mins.post_notes(bot, guild, row, via=VIA_WEBSITE)
        if not found.ok:
            refused(found)
        return await _whole(guild, await _wanted(guild, meeting_id), found.message)

    @router.delete("/{meeting_id}")
    async def minutes_delete(request: Request, meeting_id: str) -> dict[str, Any]:
        who, guild = await _editor(request)
        row = await _wanted(guild, meeting_id)
        found = await mins.delete_meeting(
            bot, guild, row, actor_for(bot, who, guild), via=VIA_WEBSITE
        )
        if not found.ok:
            refused(found)
        return {"deleted": str(meeting_id), "message": found.message}

    return router


__all__ = ["build_router", "guard_line", "host_line", "meeting_row", "transcript_rows"]
