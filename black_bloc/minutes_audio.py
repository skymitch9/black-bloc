from __future__ import annotations

import io
import logging
import sys
import threading
import wave
from array import array
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

log = logging.getLogger(__name__)

SAMPLE_RATE = 48000
CHANNELS = 2
SAMPLE_WIDTH = 2
OUT_RATE = 16000
OUT_CHANNELS = 1
DECIMATION = SAMPLE_RATE // OUT_RATE
BLOCK_SAMPLES = CHANNELS * DECIMATION
BLOCK_BYTES = BLOCK_SAMPLES * SAMPLE_WIDTH

CHUNK_SECONDS_MIN = 30
CHUNK_SECONDS_MAX = 120
CHUNK_SECONDS_DEFAULT = 60

EXTENSION = "discord.ext.voice_recv"

NO_EXTENSION = (
    "The voice-recording extension is not installed on this host, so the bot cannot listen to a "
    "meeting. It is `discord-ext-voice-recv`, and it ships in the bot's image — tell the owner, "
    "because a host without it can never take notes."
)
NO_OPUS = (
    "The Opus audio library is not loaded on this host, so the bot cannot decode what people say. "
    "The image needs `libopus0` installed — tell the owner."
)


@dataclass(frozen=True)
class Chunk:
    """One speaker's WAV for one stretch of a meeting, handed off and then forgotten."""

    speaker_id: int
    speaker_name: str
    started_at: datetime
    seconds: float
    wav: bytes


def utcnow() -> datetime:
    return datetime.now(UTC)


def clean_seconds(value: object, *, default: int = CHUNK_SECONDS_DEFAULT) -> int:
    try:
        asked = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return max(CHUNK_SECONDS_MIN, min(CHUNK_SECONDS_MAX, asked))


def to_mono_16k(pcm: bytes) -> tuple[bytes, bytes]:
    """48 kHz stereo in; 16 kHz mono out, plus the bytes that did not fill a block."""
    usable = len(pcm) - (len(pcm) % BLOCK_BYTES)
    if usable <= 0:
        return b"", bytes(pcm)
    src = array("h")
    src.frombytes(pcm[:usable])
    if sys.byteorder == "big":
        src.byteswap()
    blocks = len(src) // BLOCK_SAMPLES
    out = array("h", bytes(blocks * SAMPLE_WIDTH))
    for index in range(blocks):
        start = index * BLOCK_SAMPLES
        out[index] = sum(src[start : start + BLOCK_SAMPLES]) // BLOCK_SAMPLES
    if sys.byteorder == "big":
        out.byteswap()
    return out.tobytes(), bytes(pcm[usable:])


def wav_bytes(mono: bytes) -> bytes:
    """16-bit mono at 16 kHz, wrapped as a WAV in memory — nothing touches a disk."""
    holder = io.BytesIO()
    with wave.open(holder, "wb") as handle:
        handle.setnchannels(OUT_CHANNELS)
        handle.setsampwidth(SAMPLE_WIDTH)
        handle.setframerate(OUT_RATE)
        handle.writeframes(mono)
    return holder.getvalue()


def seconds_of(mono: bytes) -> float:
    return len(mono) / (OUT_RATE * SAMPLE_WIDTH)


def extension_available() -> bool:
    try:
        __import__(EXTENSION)
    except Exception:
        return False
    return True


def opus_available() -> bool:
    try:
        import discord.opus as opus
    except Exception:
        return False
    if opus.is_loaded():
        return True
    try:
        return bool(opus._load_default())
    except Exception:
        return False


@dataclass
class _Speaker:
    name: str
    mono: bytearray
    spare: bytes
    started_at: datetime


class SpeakerChunker:
    """Per-speaker PCM in, one WAV chunk per speaker per `chunk_seconds` out, then discarded."""

    def __init__(
        self,
        hand_off: Callable[[Chunk], None],
        *,
        chunk_seconds: int = CHUNK_SECONDS_DEFAULT,
        now: Callable[[], datetime] = utcnow,
    ) -> None:
        self._hand_off = hand_off
        self._now = now
        self.chunk_seconds = clean_seconds(chunk_seconds)
        self._target = self.chunk_seconds * OUT_RATE * SAMPLE_WIDTH
        self._speakers: dict[int, _Speaker] = {}
        self._heard: dict[int, str] = {}
        self._lock = threading.Lock()

    @property
    def heard(self) -> dict[int, str]:
        with self._lock:
            return dict(self._heard)

    def feed(self, speaker_id: int, speaker_name: str, pcm: bytes) -> None:
        ready: list[Chunk] = []
        with self._lock:
            who = int(speaker_id)
            self._heard[who] = str(speaker_name)
            held = self._speakers.get(who)
            if held is None:
                held = _Speaker(str(speaker_name), bytearray(), b"", self._now())
                self._speakers[who] = held
            held.name = str(speaker_name)
            mono, held.spare = to_mono_16k(held.spare + bytes(pcm))
            held.mono.extend(mono)
            while len(held.mono) >= self._target:
                ready.append(self._cut(who, held, self._target))
        self._deliver(ready)

    def flush(self) -> None:
        """End of meeting: hand off whatever is left and forget every buffer."""
        ready: list[Chunk] = []
        with self._lock:
            for who, held in list(self._speakers.items()):
                if held.mono:
                    ready.append(self._cut(who, held, len(held.mono)))
            self._speakers.clear()
        self._deliver(ready)

    def _cut(self, who: int, held: _Speaker, size: int) -> Chunk:
        taken = bytes(held.mono[:size])
        del held.mono[:size]
        chunk = Chunk(
            speaker_id=who,
            speaker_name=held.name,
            started_at=held.started_at,
            seconds=seconds_of(taken),
            wav=wav_bytes(taken),
        )
        held.started_at = self._now()
        return chunk

    def _deliver(self, ready: list[Chunk]) -> None:
        for chunk in ready:
            try:
                self._hand_off(chunk)
            except Exception as exc:
                log.warning("minutes: a chunk was not handed off — %s: %s", type(exc).__name__, exc)


def build_sink(chunker: SpeakerChunker):
    """The one place the receive extension is touched; imported late so the bot runs without it."""
    from discord.ext import voice_recv

    class MinutesSink(voice_recv.AudioSink):
        def wants_opus(self) -> bool:
            return False

        def write(self, user, data) -> None:
            if user is None or not getattr(data, "pcm", b""):
                return
            chunker.feed(int(user.id), str(getattr(user, "display_name", user)), data.pcm)

        def cleanup(self) -> None:
            chunker.flush()

    return MinutesSink()
