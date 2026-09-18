import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from black_bloc import minutes as mins
from black_bloc import minutes_session as session_mod
from black_bloc.config import load_settings
from black_bloc.llm import RATE_LIMITED, LLMError
from black_bloc.minutes_audio import Chunk
from black_bloc.minutes_session import Session, finish
from black_bloc.settings_store import SettingsStore

GUILD = 7
TEST_CHANNEL = 111
VOICE_CHANNEL = 333
STAFF_ID = 42
START = datetime(2026, 9, 17, 18, 0, tzinfo=UTC)


class FakeMessage:
    def __init__(self, message_id=9001, **kwargs):
        self.id = message_id
        self.kwargs = dict(kwargs)


class FakeChannel:
    def __init__(self, channel_id, name):
        self.id = channel_id
        self.name = name
        self.sent = []
        self.raises = None

    async def send(self, content=None, **kwargs):
        if self.raises is not None:
            raise self.raises
        self.sent.append({"content": content, **kwargs})
        return FakeMessage(**kwargs)


class FakeVoiceClient:
    def __init__(self):
        self.sink = None
        self.listening = False
        self.left = False
        self.listen_raises = None

    def listen(self, sink):
        if self.listen_raises is not None:
            raise self.listen_raises
        self.sink = sink
        self.listening = True

    def stop_listening(self):
        self.listening = False

    async def disconnect(self, force=False):
        self.left = True


class FakeVoice:
    def __init__(self):
        self.id = VOICE_CHANNEL
        self.name = "Meeting Room"
        self.voice_states = {}

    def permissions_for(self, who):
        return SimpleNamespace(connect=True)


class FakeGuild:
    def __init__(self, bot):
        self.id = GUILD
        self.bot = bot
        self.me = SimpleNamespace(id=1)
        self.unavailable = False

    def get_channel(self, channel_id):
        return self.bot.channels.get(int(channel_id))

    def get_member(self, user_id):
        return None


class FakeWhisper:
    def __init__(self, text="Hello everyone.", raises=None):
        self.text = text
        self.raises = raises
        self.seen = []

    async def transcribe(self, audio, *, name="chunk.wav"):
        self.seen.append(audio)
        if self.raises is not None:
            raise self.raises
        return self.text


class FakeBot:
    def __init__(self, db, store, settings):
        self.db = db
        self.store = store
        self.settings = settings
        self.guard = None
        self.channels = {
            TEST_CHANNEL: FakeChannel(TEST_CHANNEL, "blackbloc-logs"),
            VOICE_CHANNEL: FakeChannel(VOICE_CHANNEL, "meeting-room"),
        }
        self.guild = FakeGuild(self)
        self.guilds = [self.guild]
        self.minutes_whisper_client = FakeWhisper()
        self.minutes_notes_client = None

    def get_channel(self, channel_id):
        return self.channels.get(int(channel_id))

    def get_guild(self, guild_id):
        return self.guild if int(guild_id) == GUILD else None


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(
        _env_file=None,
        test_mode=True,
        test_channel_id=TEST_CHANNEL,
        groq_api_key="g" * 10,
        anthropic_api_key="a" * 10,
    )
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, mins.MODE_KEY, mins.ON)
    return FakeBot(db, store, settings)


@pytest.fixture(autouse=True)
def the_bot_can_join(monkeypatch):
    """The main venv has no receive extension, so the join and the sink are stood in for."""
    client = FakeVoiceClient()

    async def connect(channel):
        return client

    monkeypatch.setattr(session_mod, "connect_to", connect)
    monkeypatch.setattr(session_mod, "build_sink", lambda chunker: SimpleNamespace(chunker=chunker))
    return client


async def a_session(bot, channel=None):
    voice = channel or FakeVoice()
    row = await mins.start_row(bot.db, GUILD, voice.id, STAFF_ID)
    return Session(bot, bot.guild, voice, row)


async def kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


def a_chunk(speaker_id=1, name="Ada"):
    return Chunk(speaker_id, name, START, 60.0, b"RIFF....")


async def settled(session):
    """The worker is a task, so a test waits for the queue rather than guessing."""
    await asyncio.wait_for(session.queue.join(), timeout=5)


async def test_starting_joins_the_channel_and_listens(bot, the_bot_can_join):
    session = await a_session(bot)
    found = await session.start()
    assert found.ok
    assert the_bot_can_join.listening is True
    await session.stop(mins.BY_HAND)


async def test_a_join_discord_refuses_deletes_the_row_and_says_so_in_words(bot, monkeypatch):
    async def refuse(channel):
        raise RuntimeError("missing permissions")

    monkeypatch.setattr(session_mod, "connect_to", refuse)
    session = await a_session(bot)
    found = await session.start()
    assert not found.ok and found.code == "join_broke"
    assert "could not join" in found.message
    assert await mins.get_meeting(bot.db, GUILD, session.meeting_id) is None
    assert await kinds(bot.db) == [mins.JOIN_FAILED]


async def test_a_sink_that_will_not_attach_leaves_the_channel_again(bot, the_bot_can_join):
    the_bot_can_join.listen_raises = RuntimeError("no opus")
    session = await a_session(bot)
    found = await session.start()
    assert not found.ok and found.code == "join_broke"
    assert the_bot_can_join.left is True


async def test_a_meeting_announces_itself_before_a_word_is_recorded(bot):
    session = await a_session(bot)
    await session.start()
    await session.announce()
    assert bot.channels[VOICE_CHANNEL].sent[-1]["content"] == mins.start_text(bot.store, GUILD)
    await session.stop(mins.BY_HAND)


async def test_the_announcement_goes_to_the_key_when_one_is_set(bot):
    await bot.store.set(GUILD, mins.CHANNEL_KEY, TEST_CHANNEL)
    session = await a_session(bot)
    await session.start()
    await session.announce()
    assert bot.channels[TEST_CHANNEL].sent
    assert bot.channels[VOICE_CHANNEL].sent == []
    await session.stop(mins.BY_HAND)


async def test_an_announcement_discord_refuses_never_stops_the_meeting(bot):
    bot.channels[VOICE_CHANNEL].raises = RuntimeError("nope")
    session = await a_session(bot)
    await session.start()
    await session.announce()
    assert await mins.get_meeting(bot.db, GUILD, session.meeting_id) is not None
    await session.stop(mins.BY_HAND)


async def test_a_chunk_becomes_one_transcript_line_with_its_speaker(bot):
    session = await a_session(bot)
    await session.start()
    await session.queue.put(a_chunk())
    await settled(session)
    rows = await mins.lines_of(bot.db, session.meeting_id)
    assert [(row["speaker"], row["text"]) for row in rows] == [("Ada", "Hello everyone.")]
    assert session.chunks_done == 1
    await session.stop(mins.BY_HAND)


async def test_a_transcription_failure_is_a_log_row_and_the_chunk_is_dropped(bot):
    bot.minutes_whisper_client = FakeWhisper(raises=LLMError(RATE_LIMITED, "slow down"))
    session = await a_session(bot)
    await session.start()
    await session.queue.put(a_chunk())
    await settled(session)
    assert await mins.count_lines(bot.db, session.meeting_id) == 0
    assert session.chunks_dropped == 1
    assert session.last_error and "rate_limited" in session.last_error
    assert mins.TRANSCRIBE_FAILED in await kinds(bot.db)
    await session.stop(mins.BY_HAND)


async def test_a_failure_never_stops_the_meeting_and_the_next_chunk_still_lands(bot):
    angry = FakeWhisper(raises=LLMError(RATE_LIMITED, "slow down"))
    bot.minutes_whisper_client = angry
    session = await a_session(bot)
    await session.start()
    await session.queue.put(a_chunk())
    await settled(session)
    bot.minutes_whisper_client = FakeWhisper("Second try.")
    await session.queue.put(a_chunk(2, "Grace"))
    await settled(session)
    rows = await mins.lines_of(bot.db, session.meeting_id)
    assert [row["text"] for row in rows] == ["Second try."]
    await session.stop(mins.BY_HAND)


async def test_silence_transcribed_as_nothing_writes_no_line(bot):
    bot.minutes_whisper_client = FakeWhisper("   ")
    session = await a_session(bot)
    await session.start()
    await session.queue.put(a_chunk())
    await settled(session)
    assert await mins.count_lines(bot.db, session.meeting_id) == 0
    assert session.chunks_done == 1
    await session.stop(mins.BY_HAND)


async def test_stopping_leaves_the_channel_closes_the_row_and_logs_why(bot, the_bot_can_join):
    session = await a_session(bot)
    await session.start()
    found = await session.stop(mins.BY_EMPTY)
    assert found.ok
    assert the_bot_can_join.left is True
    row = await mins.get_meeting(bot.db, GUILD, session.meeting_id)
    assert row["ended_at"] and row["ended_reason"] == mins.BY_EMPTY
    assert mins.ENDED in await kinds(bot.db)


async def test_stopping_twice_refuses_the_second_time_rather_than_doubling_up(bot):
    session = await a_session(bot)
    await session.start()
    await session.stop(mins.BY_HAND)
    again = await session.stop(mins.BY_HAND)
    assert not again.ok and again.code == "already_stopping"


async def test_a_chunk_already_queued_is_transcribed_before_the_meeting_closes(bot):
    session = await a_session(bot)
    await session.start()
    await session.queue.put(a_chunk())
    await session.stop(mins.BY_HAND)
    assert await mins.count_lines(bot.db, session.meeting_id) == 1


async def test_max_hours_is_measured_from_when_the_meeting_started(bot):
    session = await a_session(bot)
    session.started_at = datetime.now(UTC) - timedelta(hours=4)
    assert session.ran_over(3) is True
    assert session.ran_over(6) is False


async def test_the_status_lines_say_who_was_heard_and_what_broke(bot):
    session = await a_session(bot)
    await session.start()
    session.chunker.feed(1, "Ada", b"\x00" * 3840)
    session.last_error = "rate_limited: slow down"
    said = "\n".join(session.status_lines())
    assert "Ada" in said and "Last transcription error" in said
    await session.stop(mins.BY_HAND)


async def test_a_hand_off_from_the_reader_thread_reaches_the_queue(bot):
    session = await a_session(bot)
    await session.start()
    await asyncio.to_thread(session._hand_off, a_chunk())
    await settled(session)
    assert await mins.count_lines(bot.db, session.meeting_id) == 1
    await session.stop(mins.BY_HAND)


async def test_finish_writes_the_notes_and_then_posts_them(bot):
    from black_bloc.llm import Reply, Usage

    class FakeNotes:
        async def reply(self, *, system, messages):
            return Reply(text="Summary.", provider="anthropic", model="m", usage=Usage())

    bot.minutes_notes_client = FakeNotes()
    session = await a_session(bot)
    await session.start()
    await session.queue.put(a_chunk())
    await session.stop(mins.BY_HAND)
    found = await finish(bot, bot.guild, session.meeting_id)
    assert found.ok
    row = await mins.get_meeting(bot.db, GUILD, session.meeting_id)
    assert row["notes"] == "Summary." and row["notes_message_id"]
    assert bot.channels[VOICE_CHANNEL].sent[-1]["embed"].description == "Summary."


async def test_finish_on_a_meeting_that_is_gone_refuses_in_words(bot):
    found = await finish(bot, bot.guild, 9999)
    assert not found.ok and found.code == "no_such_meeting"
    assert "no meeting" in found.message


async def test_finish_never_posts_when_there_was_nothing_to_write_up(bot):
    session = await a_session(bot)
    await session.start()
    await session.stop(mins.BY_HAND)
    found = await finish(bot, bot.guild, session.meeting_id)
    assert not found.ok and found.code == "nothing_heard"
    assert [one for one in bot.channels[VOICE_CHANNEL].sent if one.get("embed")] == []
