import dataclasses
import io
import math
import struct
import wave
from datetime import UTC, datetime, timedelta

import pytest

from black_bloc.minutes_audio import (
    BLOCK_BYTES,
    CHANNELS,
    CHUNK_SECONDS_DEFAULT,
    CHUNK_SECONDS_MAX,
    CHUNK_SECONDS_MIN,
    DECIMATION,
    OUT_CHANNELS,
    OUT_RATE,
    SAMPLE_RATE,
    SAMPLE_WIDTH,
    Chunk,
    SpeakerChunker,
    build_sink,
    clean_seconds,
    extension_available,
    opus_available,
    seconds_of,
    to_mono_16k,
    wav_bytes,
)

FRAME_SAMPLES = 960
FRAME_BYTES = FRAME_SAMPLES * CHANNELS * SAMPLE_WIDTH
START = datetime(2026, 9, 17, 18, 0, tzinfo=UTC)


def stereo(samples):
    return b"".join(struct.pack("<hh", left, right) for left, right in samples)


def tone(frames=FRAME_SAMPLES, amplitude=8000, hertz=440.0):
    out = []
    for index in range(frames):
        value = int(amplitude * math.sin(2 * math.pi * hertz * index / SAMPLE_RATE))
        out.append((value, value))
    return stereo(out)


def silence(frames=FRAME_SAMPLES):
    return b"\x00" * frames * CHANNELS * SAMPLE_WIDTH


class Clock:
    def __init__(self, start=START):
        self.at = start

    def __call__(self):
        return self.at

    def tick(self, seconds):
        self.at = self.at + timedelta(seconds=seconds)
        return self.at


def collector():
    got = []
    return got, got.append


def test_a_twenty_millisecond_frame_becomes_three_hundred_twenty_mono_samples():
    mono, spare = to_mono_16k(tone())
    assert spare == b""
    assert len(mono) == (FRAME_SAMPLES // DECIMATION) * SAMPLE_WIDTH


def test_bytes_that_do_not_fill_a_block_are_handed_back_rather_than_dropped():
    mono, spare = to_mono_16k(tone() + b"\x01\x02\x03")
    assert len(spare) == 3
    assert len(mono) == (FRAME_SAMPLES // DECIMATION) * SAMPLE_WIDTH


def test_a_fragment_shorter_than_one_block_yields_nothing_and_keeps_everything():
    mono, spare = to_mono_16k(b"\x01" * (BLOCK_BYTES - 1))
    assert mono == b""
    assert len(spare) == BLOCK_BYTES - 1


def test_the_spare_bytes_of_one_feed_are_used_by_the_next():
    got, hand_off = collector()
    chunker = SpeakerChunker(hand_off, chunk_seconds=CHUNK_SECONDS_MIN, now=Clock())
    half = BLOCK_BYTES // 2
    chunker.feed(1, "Ada", tone()[: FRAME_BYTES - half])
    chunker.feed(1, "Ada", tone()[FRAME_BYTES - half :])
    chunker.flush()
    assert len(got) == 1
    with wave.open(io.BytesIO(got[0].wav), "rb") as handle:
        assert handle.getnframes() == FRAME_SAMPLES // DECIMATION


def test_silence_in_becomes_silence_out_rather_than_noise():
    mono, _spare = to_mono_16k(silence())
    assert set(mono) == {0}


def test_a_wav_chunk_is_sixteen_kilohertz_mono_sixteen_bit():
    holder = io.BytesIO(wav_bytes(b"\x00\x00" * OUT_RATE))
    with wave.open(holder, "rb") as handle:
        assert handle.getnchannels() == OUT_CHANNELS
        assert handle.getframerate() == OUT_RATE
        assert handle.getsampwidth() == SAMPLE_WIDTH
        assert handle.getnframes() == OUT_RATE


def test_one_second_of_mono_reads_as_one_second():
    assert seconds_of(b"\x00\x00" * OUT_RATE) == pytest.approx(1.0)


@pytest.mark.parametrize(
    "asked,wanted",
    [
        (60, 60),
        (30, 30),
        (120, 120),
        (5, CHUNK_SECONDS_MIN),
        (999, CHUNK_SECONDS_MAX),
        ("45", 45),
        ("nonsense", CHUNK_SECONDS_DEFAULT),
        (None, CHUNK_SECONDS_DEFAULT),
    ],
)
def test_a_chunk_length_outside_its_band_is_pulled_back_into_it(asked, wanted):
    assert clean_seconds(asked) == wanted


def test_a_speaker_hands_off_exactly_one_chunk_per_chunk_seconds():
    got, hand_off = collector()
    clock = Clock()
    chunker = SpeakerChunker(hand_off, chunk_seconds=CHUNK_SECONDS_MIN, now=clock)
    frames_per_chunk = CHUNK_SECONDS_MIN * SAMPLE_RATE // FRAME_SAMPLES
    for _ in range(frames_per_chunk):
        chunker.feed(7, "Ada", tone())
    assert len(got) == 1
    assert got[0].speaker_id == 7
    assert got[0].speaker_name == "Ada"
    assert got[0].seconds == pytest.approx(CHUNK_SECONDS_MIN)
    assert got[0].started_at == START


def test_two_speakers_are_chunked_apart_never_mixed():
    got, hand_off = collector()
    chunker = SpeakerChunker(hand_off, chunk_seconds=CHUNK_SECONDS_MIN, now=Clock())
    frames_per_chunk = CHUNK_SECONDS_MIN * SAMPLE_RATE // FRAME_SAMPLES
    for _ in range(frames_per_chunk):
        chunker.feed(1, "Ada", tone())
        chunker.feed(2, "Grace", silence())
    assert [(c.speaker_id, c.speaker_name) for c in got] == [(1, "Ada"), (2, "Grace")]
    loud, quiet = got
    with wave.open(io.BytesIO(loud.wav), "rb") as handle:
        assert set(handle.readframes(handle.getnframes())) != {0}
    with wave.open(io.BytesIO(quiet.wav), "rb") as handle:
        assert set(handle.readframes(handle.getnframes())) == {0}


def test_the_second_chunk_starts_when_the_first_one_was_cut():
    got, hand_off = collector()
    clock = Clock()
    chunker = SpeakerChunker(hand_off, chunk_seconds=CHUNK_SECONDS_MIN, now=clock)
    frames_per_chunk = CHUNK_SECONDS_MIN * SAMPLE_RATE // FRAME_SAMPLES
    for _ in range(frames_per_chunk - 1):
        chunker.feed(1, "Ada", tone())
    cut_at = clock.tick(CHUNK_SECONDS_MIN)
    for _ in range(frames_per_chunk + 1):
        chunker.feed(1, "Ada", tone())
    assert [c.started_at for c in got] == [START, cut_at]


def test_audio_is_forgotten_the_moment_a_chunk_is_handed_off():
    got, hand_off = collector()
    chunker = SpeakerChunker(hand_off, chunk_seconds=CHUNK_SECONDS_MIN, now=Clock())
    frames_per_chunk = CHUNK_SECONDS_MIN * SAMPLE_RATE // FRAME_SAMPLES
    for _ in range(frames_per_chunk):
        chunker.feed(1, "Ada", tone())
    assert len(got) == 1
    assert chunker._speakers[1].mono == bytearray()


def test_flush_hands_off_the_tail_and_empties_every_buffer():
    got, hand_off = collector()
    chunker = SpeakerChunker(hand_off, chunk_seconds=CHUNK_SECONDS_MIN, now=Clock())
    chunker.feed(1, "Ada", tone())
    chunker.feed(2, "Grace", tone())
    chunker.flush()
    assert sorted(c.speaker_id for c in got) == [1, 2]
    assert chunker._speakers == {}


def test_flush_with_nothing_heard_hands_off_nothing():
    got, hand_off = collector()
    SpeakerChunker(hand_off, chunk_seconds=CHUNK_SECONDS_MIN, now=Clock()).flush()
    assert got == []


def test_a_second_flush_repeats_nothing():
    got, hand_off = collector()
    chunker = SpeakerChunker(hand_off, chunk_seconds=CHUNK_SECONDS_MIN, now=Clock())
    chunker.feed(1, "Ada", tone())
    chunker.flush()
    chunker.flush()
    assert len(got) == 1


def test_the_chunker_remembers_who_was_heard_even_after_the_audio_is_gone():
    _got, hand_off = collector()
    chunker = SpeakerChunker(hand_off, chunk_seconds=CHUNK_SECONDS_MIN, now=Clock())
    chunker.feed(1, "Ada", tone())
    chunker.feed(2, "Grace", tone())
    chunker.flush()
    assert chunker.heard == {1: "Ada", 2: "Grace"}


def test_a_speaker_who_renames_mid_meeting_is_chunked_under_the_newer_name():
    got, hand_off = collector()
    chunker = SpeakerChunker(hand_off, chunk_seconds=CHUNK_SECONDS_MIN, now=Clock())
    chunker.feed(1, "Ada", tone())
    chunker.feed(1, "Ada Lovelace", tone())
    chunker.flush()
    assert got[0].speaker_name == "Ada Lovelace"


def test_a_hand_off_that_raises_never_stops_the_meeting():
    seen = []

    def angry(chunk):
        seen.append(chunk)
        raise RuntimeError("the transcriber fell over")

    chunker = SpeakerChunker(angry, chunk_seconds=CHUNK_SECONDS_MIN, now=Clock())
    chunker.feed(1, "Ada", tone())
    chunker.flush()
    chunker.feed(1, "Ada", tone())
    chunker.flush()
    assert len(seen) == 2


def test_a_long_feed_is_cut_into_as_many_chunks_as_it_holds():
    got, hand_off = collector()
    chunker = SpeakerChunker(hand_off, chunk_seconds=CHUNK_SECONDS_MIN, now=Clock())
    seconds = CHUNK_SECONDS_MIN * 2
    chunker.feed(1, "Ada", silence(SAMPLE_RATE * seconds))
    assert len(got) == 2
    assert all(c.seconds == pytest.approx(CHUNK_SECONDS_MIN) for c in got)


def test_a_chunk_is_frozen_so_nothing_downstream_can_rewrite_it():
    chunk = Chunk(1, "Ada", START, 1.0, b"")
    with pytest.raises(dataclasses.FrozenInstanceError):
        chunk.speaker_name = "Grace"


def test_the_receive_extension_installs_and_imports():
    pytest.importorskip(
        "discord.ext.voice_recv",
        reason="discord-ext-voice-recv is not in this venv; it ships in the bot's image",
    )
    assert extension_available() is True


def test_the_sink_feeds_the_chunker_what_a_speaker_said():
    pytest.importorskip(
        "discord.ext.voice_recv",
        reason="discord-ext-voice-recv is not in this venv; it ships in the bot's image",
    )

    class FakeUser:
        id = 11
        display_name = "Ada"

    class FakeData:
        pcm = tone()

    got, hand_off = collector()
    chunker = SpeakerChunker(hand_off, chunk_seconds=CHUNK_SECONDS_MIN, now=Clock())
    sink = build_sink(chunker)
    assert sink.wants_opus() is False
    sink.write(FakeUser(), FakeData())
    sink.cleanup()
    assert [(c.speaker_id, c.speaker_name) for c in got] == [(11, "Ada")]


def test_the_sink_ignores_a_packet_with_no_speaker_and_a_packet_with_no_audio():
    pytest.importorskip(
        "discord.ext.voice_recv",
        reason="discord-ext-voice-recv is not in this venv; it ships in the bot's image",
    )

    class FakeUser:
        id = 11
        display_name = "Ada"

    class Empty:
        pcm = b""

    class Full:
        pcm = tone()

    got, hand_off = collector()
    chunker = SpeakerChunker(hand_off, chunk_seconds=CHUNK_SECONDS_MIN, now=Clock())
    sink = build_sink(chunker)
    sink.write(None, Full())
    sink.write(FakeUser(), Empty())
    chunker.flush()
    assert got == []


def test_opus_says_yes_or_no_rather_than_raising():
    assert opus_available() in (True, False)


def test_a_real_opus_frame_decodes_into_audio_the_chunker_can_use():
    if not opus_available():
        pytest.skip("libopus is not loadable here; the image installs it (Dockerfile)")
    import discord.opus as opus

    encoder = opus.Encoder()
    decoder = opus.Decoder()
    packet = encoder.encode(tone(), FRAME_SAMPLES)
    pcm = decoder.decode(packet)
    assert len(pcm) == FRAME_BYTES

    got, hand_off = collector()
    chunker = SpeakerChunker(hand_off, chunk_seconds=CHUNK_SECONDS_MIN, now=Clock())
    chunker.feed(1, "Ada", pcm)
    chunker.flush()
    with wave.open(io.BytesIO(got[0].wav), "rb") as handle:
        assert handle.getframerate() == OUT_RATE
        assert handle.getnframes() == FRAME_SAMPLES // DECIMATION
        assert set(handle.readframes(handle.getnframes())) != {0}
