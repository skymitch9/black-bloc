from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import discord

from . import minutes as mins
from . import shadow as shadow_home
from .actionlog import log_action
from .groq import WhisperClient
from .llm import LLMError
from .minutes_audio import Chunk, SpeakerChunker, build_sink
from .panels import Outcome, refusal

log = logging.getLogger(__name__)

QUEUE_MAX = 64
DRAIN_SECONDS = 120


def whisper_client(bot: Any) -> Any:
    made = getattr(bot, "minutes_whisper_client", None)
    if made is not None:
        return made
    made = WhisperClient(bot.settings.groq_api_key)
    bot.minutes_whisper_client = made
    return made


async def connect_to(channel: Any) -> Any:
    """The one place a voice channel is joined; the receive extension is imported here only."""
    from discord.ext import voice_recv

    return await channel.connect(cls=voice_recv.VoiceRecvClient)


class Session:
    """One meeting being recorded: the sink, the transcription queue, and how it ends."""

    def __init__(self, bot: Any, guild: Any, channel: Any, row: Any) -> None:
        self.bot = bot
        self.guild = guild
        self.channel = channel
        self.meeting_id = int(row["id"])
        self.started_at = datetime.now(UTC)
        self.chunks_done = 0
        self.chunks_dropped = 0
        self.last_error: str | None = None
        self.landed_note = ""
        self.ending = False
        self.voice: Any = None
        self.loop = asyncio.get_running_loop()
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_MAX)
        self.chunker = SpeakerChunker(
            self._hand_off, chunk_seconds=mins.chunk_seconds(bot.store, guild.id)
        )
        self.worker: asyncio.Task | None = None

    @property
    def speakers(self) -> list[str]:
        return list(self.chunker.heard.values())

    def _hand_off(self, chunk: Chunk) -> None:
        """Called on the voice reader THREAD, so the queue is reached the thread-safe way."""
        try:
            asyncio.run_coroutine_threadsafe(self.queue.put(chunk), self.loop)
        except RuntimeError as exc:
            self.chunks_dropped += 1
            log.warning("minutes: a chunk was dropped — %s", exc)

    async def start(self) -> Outcome:
        try:
            self.voice = await connect_to(self.channel)
        except discord.ClientException as exc:
            return await self._join_broke(f"{type(exc).__name__}: {exc}")
        except Exception as exc:
            return await self._join_broke(f"{type(exc).__name__}: {exc}")
        try:
            self.voice.listen(build_sink(self.chunker))
        except Exception as exc:
            await self._leave()
            return await self._join_broke(f"{type(exc).__name__}: {exc}")
        self.worker = asyncio.create_task(self._transcribe_forever(), name="minutes-transcribe")
        return Outcome(True, "", value=self)

    async def _join_broke(self, reason: str) -> Outcome:
        await log_action(
            self.bot,
            self.guild,
            mins.JOIN_FAILED,
            details={"meeting": self.meeting_id, "channel": self.channel.id, "reason": reason},
        )
        await mins.delete_row(self.bot.db, self.guild.id, self.meeting_id)
        return refusal(
            mins.JOIN_BROKE.format(
                where=getattr(self.channel, "name", self.channel), reason=reason
            ),
            "join_broke",
            502,
        )

    async def announce(self) -> str:
        """Every meeting says so before a word is recorded; where it landed is returned."""
        wanted = mins.wanted_channel_id(self.bot, self.guild, self.channel)
        where, note = mins.landing(self.bot, self.guild, wanted)
        self.landed_note = note
        if where is None:
            return note or mins.TEST_MODE_NOWHERE
        channel = shadow_home.channel_of(self.bot, self.guild, where)
        if channel is None:
            return note
        try:
            await channel.send(
                mins.start_text(self.bot.store, self.guild.id),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except Exception as exc:
            log.warning("minutes: the announcement was not posted — %s", exc)
            return note
        await mins.save_posted(self.bot.db, self.meeting_id, where, None)
        return note

    async def _transcribe_forever(self) -> None:
        while True:
            chunk = await self.queue.get()
            try:
                await self._transcribe(chunk)
            except Exception as exc:
                log.warning("minutes: the transcriber fell over — %s", exc, exc_info=exc)
            finally:
                self.queue.task_done()

    async def _transcribe(self, chunk: Chunk) -> None:
        """A failure never stops a meeting: one log row, the chunk is dropped, on we go."""
        try:
            said = await whisper_client(self.bot).transcribe(chunk.wav)
        except LLMError as exc:
            self.chunks_dropped += 1
            self.last_error = f"{exc.reason}: {exc}"
            await log_action(
                self.bot,
                self.guild,
                mins.TRANSCRIBE_FAILED,
                details={
                    "meeting": self.meeting_id,
                    "speaker": chunk.speaker_name,
                    "reason": exc.reason,
                },
            )
            return
        self.chunks_done += 1
        self.last_error = None
        await mins.add_line(
            self.bot.db,
            self.meeting_id,
            speaker_id=chunk.speaker_id,
            speaker=chunk.speaker_name,
            started_at=chunk.started_at,
            text=said,
        )

    async def _leave(self) -> None:
        if self.voice is None:
            return
        try:
            self.voice.stop_listening()
        except Exception as exc:
            log.info("minutes: stop_listening complained — %s", exc)
        try:
            await self.voice.disconnect(force=True)
        except Exception as exc:
            log.info("minutes: disconnect complained — %s", exc)
        self.voice = None

    async def stop(self, reason: str) -> Outcome:
        """Leave, drain what is already recorded, close the row, then write the notes."""
        if self.ending:
            return refusal(mins.NO_MEETING_RUNNING, "already_stopping", 409)
        self.ending = True
        self.chunker.flush()
        await self._leave()
        await self._drain()
        if self.worker is not None:
            self.worker.cancel()
            self.worker = None
        await mins.end_row(self.bot.db, self.meeting_id, reason)
        await log_action(
            self.bot,
            self.guild,
            mins.ENDED,
            details={
                "meeting": self.meeting_id,
                "reason": reason,
                "chunks": self.chunks_done,
                "dropped": self.chunks_dropped,
                "speakers": len(self.speakers),
            },
        )
        return Outcome(True, "", value=self.meeting_id)

    async def _drain(self) -> None:
        try:
            await asyncio.wait_for(self.queue.join(), timeout=DRAIN_SECONDS)
        except (TimeoutError, asyncio.CancelledError):
            log.warning(
                "minutes: meeting %s still had chunks waiting after %ss; they were dropped",
                self.meeting_id,
                DRAIN_SECONDS,
            )

    def ran_over(self, hours: int, *, now: datetime | None = None) -> bool:
        return (now or datetime.now(UTC)) - self.started_at >= timedelta(hours=max(1, int(hours)))

    def status_lines(self) -> list[str]:
        heard = self.speakers
        lines = [
            f"Recording **{getattr(self.channel, 'name', self.channel)}** since "
            f"{self.started_at.strftime('%H:%M')} UTC.",
            f"Heard so far: {', '.join(heard) if heard else 'nobody yet'}.",
            f"Chunks transcribed: **{self.chunks_done}**"
            + (f" · dropped: **{self.chunks_dropped}**" if self.chunks_dropped else ""),
        ]
        if self.last_error:
            lines.append(f"Last transcription error: {self.last_error}")
        if self.landed_note:
            lines.append(self.landed_note)
        return lines


async def finish(bot: Any, guild: Any, meeting_id: int) -> Outcome:
    """The one tail every ending shares: write the notes, then post them."""
    row = await mins.get_meeting(bot.db, guild.id, meeting_id)
    if row is None:
        return refusal(mins.NO_SUCH_MEETING.format(meeting_id=meeting_id), "no_such_meeting", 404)
    written = await mins.write_notes(bot, guild, row)
    if not written.ok:
        return written
    fresh = await mins.get_meeting(bot.db, guild.id, meeting_id)
    return await mins.post_notes(bot, guild, fresh)


__all__ = [
    "DRAIN_SECONDS",
    "QUEUE_MAX",
    "Session",
    "connect_to",
    "finish",
    "whisper_client",
]
