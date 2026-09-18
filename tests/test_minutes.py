from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from black_bloc import minutes as mins
from black_bloc.config import load_settings
from black_bloc.llm import BROKEN, LLMError, Reply, Usage
from black_bloc.settings_store import SettingsStore

GUILD = 7
TEST_CHANNEL = 111
NOTES_CHANNEL = 222
VOICE_CHANNEL = 333
OPT_OUT_ROLE = 555
STAFF_ID = 42


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id


class FakeMember:
    def __init__(self, user_id, name, roles=()):
        self.id = user_id
        self.display_name = name
        self.roles = [FakeRole(one) for one in roles]


class FakeMessage:
    def __init__(self, channel, message_id, **kwargs):
        self.channel = channel
        self.id = message_id
        self.kwargs = dict(kwargs)


class FakeChannel:
    def __init__(self, channel_id, name):
        self.id = channel_id
        self.name = name
        self.sent = []
        self.next_id = 9000
        self.raises = None

    async def send(self, content=None, **kwargs):
        if self.raises is not None:
            raise self.raises
        self.next_id += 1
        self.sent.append({"content": content, **kwargs})
        return FakeMessage(self, self.next_id, **kwargs)


class FakeVoice:
    def __init__(self, members=(), connect=True):
        self.id = VOICE_CHANNEL
        self.name = "Meeting Room"
        self.voice_states = {one.id: object() for one in members}
        self.guild = None
        self._members = {one.id: one for one in members}
        self._connect = connect

    def permissions_for(self, who):
        return SimpleNamespace(connect=self._connect)


class FakeGuild:
    def __init__(self, bot):
        self.id = GUILD
        self.bot = bot
        self.me = SimpleNamespace(id=1)
        self.unavailable = False
        self.members = {}

    def get_channel(self, channel_id):
        return self.bot.channels.get(int(channel_id))

    def get_member(self, user_id):
        return self.members.get(int(user_id))


class FakeGuard:
    def __init__(self, allowed):
        self.test_channel_id = TEST_CHANNEL
        self.allowed = set(allowed)

    def allows_channel(self, channel_id):
        return int(channel_id) in self.allowed


class FakeNotes:
    def __init__(self, text="Summary.\nDecisions: none.", raises=None):
        self.text = text
        self.raises = raises
        self.calls = []

    async def reply(self, *, system, messages):
        self.calls.append((list(system), list(messages)))
        if self.raises is not None:
            raise self.raises
        return Reply(text=self.text, provider="anthropic", model="m", usage=Usage())


class FakeBot:
    def __init__(self, db, store, settings):
        self.db = db
        self.store = store
        self.settings = settings
        self.guard = None
        self.channels = {
            TEST_CHANNEL: FakeChannel(TEST_CHANNEL, "blackbloc-logs"),
            NOTES_CHANNEL: FakeChannel(NOTES_CHANNEL, "meeting-notes"),
            VOICE_CHANNEL: FakeChannel(VOICE_CHANNEL, "meeting-room"),
        }
        self.guild = FakeGuild(self)
        self.guilds = [self.guild]
        self.minutes_notes_client = FakeNotes()

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
        site_origin="https://x.test",
        groq_api_key="g" * 10,
        anthropic_api_key="a" * 10,
    )
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "staff_channel_id", TEST_CHANNEL)
    await store.set(GUILD, mins.MODE_KEY, mins.ON)
    return FakeBot(db, store, settings)


@pytest.fixture(autouse=True)
def the_host_can_record(monkeypatch):
    """The main venv has no receive extension, so the suite says what a bot image would."""
    monkeypatch.setattr(mins, "extension_available", lambda: True)
    monkeypatch.setattr(mins, "opus_available", lambda: True)


@pytest.fixture
def staff():
    return FakeMember(STAFF_ID, "Mod")


async def kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def a_meeting(bot, *, lines=(), channel_id=VOICE_CHANNEL):
    row = await mins.start_row(bot.db, GUILD, channel_id, STAFF_ID)
    for speaker_id, speaker, at, text in lines:
        await mins.add_line(
            bot.db,
            int(row["id"]),
            speaker_id=speaker_id,
            speaker=speaker,
            started_at=at,
            text=text,
        )
    return await mins.get_meeting(bot.db, GUILD, row["id"])


THREE_LINES = (
    (1, "Ada", datetime(2026, 9, 17, 18, 0, tzinfo=UTC), "We should ship it."),
    (2, "Grace", datetime(2026, 9, 17, 18, 1, tzinfo=UTC), "I will write the notes."),
    (1, "Ada", datetime(2026, 9, 17, 18, 2, tzinfo=UTC), "Agreed."),
)


async def test_a_meeting_starts_recording_and_is_the_one_open_row(bot):
    row = await a_meeting(bot)
    assert row["status"] == mins.RECORDING
    assert row["ended_at"] is None
    found = await mins.open_meeting(bot.db, GUILD)
    assert int(found["id"]) == int(row["id"])


async def test_start_refuses_while_the_mode_is_off_and_says_where_to_turn_it_on(bot, staff):
    await bot.store.set(GUILD, mins.MODE_KEY, mins.OFF)
    found = await mins.may_start(bot, bot.guild, staff, FakeVoice([staff]))
    assert not found.ok
    assert found.code == "minutes_off"
    assert "turned off" in found.message and "events" in found.message


async def test_start_refuses_when_the_presser_is_in_no_voice_channel(bot, staff):
    found = await mins.may_start(bot, bot.guild, staff, None)
    assert not found.ok and found.code == "not_in_voice"
    assert "not in a voice channel" in found.message


async def test_start_refuses_without_a_speech_to_text_key_and_names_it(bot, staff, monkeypatch):
    monkeypatch.setattr(mins, "transcribe_configured", lambda bot: False)
    found = await mins.may_start(bot, bot.guild, staff, FakeVoice([staff]))
    assert not found.ok and found.code == "no_transcriber"
    assert "GROQ_API_KEY" in found.message


async def test_start_refuses_without_the_receive_extension_and_never_pretends(
    bot, staff, monkeypatch
):
    monkeypatch.setattr(mins, "extension_available", lambda: False)
    found = await mins.may_start(bot, bot.guild, staff, FakeVoice([staff]))
    assert not found.ok and found.code == "no_extension"
    assert "discord-ext-voice-recv" in found.message


async def test_start_refuses_without_opus(bot, staff, monkeypatch):
    monkeypatch.setattr(mins, "opus_available", lambda: False)
    found = await mins.may_start(bot, bot.guild, staff, FakeVoice([staff]))
    assert not found.ok and found.code == "no_opus"
    assert "libopus0" in found.message


async def test_start_refuses_while_a_meeting_is_already_running_and_says_where(bot, staff):
    await a_meeting(bot)
    found = await mins.may_start(bot, bot.guild, staff, FakeVoice([staff]))
    assert not found.ok and found.code == "already_running"
    assert "already taking notes" in found.message


async def test_start_refuses_when_somebody_present_wears_the_opt_out_role_and_names_them(
    bot, staff
):
    await bot.store.set(GUILD, mins.OPT_OUT_KEY, OPT_OUT_ROLE)
    shy = FakeMember(99, "Casey", roles=[OPT_OUT_ROLE])
    bot.guild.members = {staff.id: staff, shy.id: shy}
    voice = FakeVoice([staff, shy])
    voice.guild = bot.guild
    found = await mins.may_start(bot, bot.guild, staff, voice)
    assert not found.ok and found.code == "opt_out_present"
    assert "**Casey**" in found.message and "did not join" in found.message


async def test_two_opt_out_wearers_are_both_named(bot, staff):
    await bot.store.set(GUILD, mins.OPT_OUT_KEY, OPT_OUT_ROLE)
    one = FakeMember(98, "Casey", roles=[OPT_OUT_ROLE])
    two = FakeMember(97, "Robin", roles=[OPT_OUT_ROLE])
    bot.guild.members = {one.id: one, two.id: two, staff.id: staff}
    voice = FakeVoice([staff, one, two])
    voice.guild = bot.guild
    found = await mins.may_start(bot, bot.guild, staff, voice)
    assert "**Casey** and **Robin**" in found.message and " are " in found.message


async def test_start_refuses_without_the_connect_permission_and_never_asks_for_speak(bot, staff):
    voice = FakeVoice([staff], connect=False)
    voice.guild = bot.guild
    found = await mins.may_start(bot, bot.guild, staff, voice)
    assert not found.ok and found.code == "cannot_connect"
    assert "**Connect**" in found.message and "never needs Speak" in found.message


async def test_every_refusal_is_a_sentence_and_never_a_bare_status(bot, staff, monkeypatch):
    monkeypatch.setattr(mins, "transcribe_configured", lambda bot: False)
    found = await mins.may_start(bot, bot.guild, staff, FakeVoice([staff]))
    assert found.status == 503
    assert len(found.message.split()) > 10
    assert not found.message.strip().isdigit()


async def test_a_clear_start_answers_ok_with_the_channel_it_would_join(bot, staff):
    voice = FakeVoice([staff])
    voice.guild = bot.guild
    found = await mins.may_start(bot, bot.guild, staff, voice)
    assert found.ok and found.value is voice


async def test_the_transcript_is_ordered_by_when_it_was_said_and_labelled_by_speaker(bot):
    row = await a_meeting(bot, lines=THREE_LINES)
    rows = await mins.lines_of(bot.db, int(row["id"]))
    assert mins.transcript_text(rows) == (
        "Ada: We should ship it.\nGrace: I will write the notes.\nAda: Agreed."
    )
    assert mins.speakers_of(rows) == ["Ada", "Grace"]


async def test_a_line_that_is_only_whitespace_is_never_stored(bot):
    row = await a_meeting(bot)
    written = await mins.add_line(
        bot.db, int(row["id"]), speaker_id=1, speaker="Ada", started_at="2026", text="   "
    )
    assert written is None
    assert await mins.count_lines(bot.db, int(row["id"])) == 0


async def test_the_notes_prompt_is_the_key_and_the_transcript_is_the_message(bot):
    system, messages = mins.prompt_messages(bot.store, GUILD, "Ada: Hello.")
    assert system == [mins.notes_prompt(bot.store, GUILD)]
    assert messages == [{"role": "user", "content": "Ada: Hello."}]


async def test_a_very_long_transcript_is_trimmed_to_its_tail_rather_than_refused(bot):
    long = "x" * (mins.TRANSCRIPT_CHARS_MAX + 5)
    _system, messages = mins.prompt_messages(bot.store, GUILD, long)
    assert len(messages[0]["content"]) == mins.TRANSCRIPT_CHARS_MAX


async def test_writing_the_notes_stores_them_and_logs_one_row(bot):
    row = await a_meeting(bot, lines=THREE_LINES)
    found = await mins.write_notes(bot, bot.guild, row)
    assert found.ok
    fresh = await mins.get_meeting(bot.db, GUILD, row["id"])
    assert fresh["notes"] == "Summary.\nDecisions: none."
    assert fresh["status"] == mins.DONE
    assert await kinds(bot.db) == [mins.NOTES_WRITTEN]


async def test_a_meeting_nobody_spoke_in_writes_no_notes_and_says_so(bot):
    row = await a_meeting(bot)
    found = await mins.write_notes(bot, bot.guild, row)
    assert not found.ok and found.code == "nothing_heard"
    assert "no transcript" in found.message
    assert await kinds(bot.db) == []


async def test_without_a_writing_key_the_transcript_is_kept_and_the_key_is_named(bot):
    bot.settings = load_settings(
        _env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL, groq_api_key="g" * 10
    )
    row = await a_meeting(bot, lines=THREE_LINES)
    found = await mins.write_notes(bot, bot.guild, row)
    assert not found.ok and found.code == "no_notes_writer"
    assert "ANTHROPIC_API_KEY" in found.message
    assert await mins.count_lines(bot.db, int(row["id"])) == 3
    assert await kinds(bot.db) == [mins.NOTES_FAILED]


async def test_a_model_that_falls_over_leaves_the_transcript_and_a_failed_row(bot):
    bot.minutes_notes_client = FakeNotes(raises=LLMError(BROKEN, "it broke"))
    row = await a_meeting(bot, lines=THREE_LINES)
    found = await mins.write_notes(bot, bot.guild, row)
    assert not found.ok and found.code == "notes_broke"
    fresh = await mins.get_meeting(bot.db, GUILD, row["id"])
    assert fresh["status"] == mins.FAILED
    assert await mins.count_lines(bot.db, int(row["id"])) == 3
    assert await kinds(bot.db) == [mins.NOTES_FAILED]


async def test_a_model_that_answers_with_nothing_is_a_failure_not_empty_notes(bot):
    bot.minutes_notes_client = FakeNotes(text="   ")
    row = await a_meeting(bot, lines=THREE_LINES)
    found = await mins.write_notes(bot, bot.guild, row)
    assert not found.ok and found.code == "empty"


async def test_posting_the_notes_sends_an_embed_and_the_transcript_and_records_where(bot):
    await bot.store.set(GUILD, mins.CHANNEL_KEY, NOTES_CHANNEL)
    row = await a_meeting(bot, lines=THREE_LINES)
    await mins.write_notes(bot, bot.guild, row)
    fresh = await mins.get_meeting(bot.db, GUILD, row["id"])
    found = await mins.post_notes(bot, bot.guild, fresh)
    assert found.ok
    sent = bot.channels[NOTES_CHANNEL].sent[-1]
    assert sent["embed"].title == mins.notes_title(bot.store, GUILD)
    assert sent["file"].filename == f"meeting-{int(row['id'])}-transcript.txt"
    after = await mins.get_meeting(bot.db, GUILD, row["id"])
    assert int(after["notes_channel_id"]) == NOTES_CHANNEL
    assert after["notes_message_id"]


async def test_the_notes_embed_names_the_people_it_heard(bot):
    row = await a_meeting(bot, lines=THREE_LINES)
    await mins.write_notes(bot, bot.guild, row)
    fresh = await mins.get_meeting(bot.db, GUILD, row["id"])
    rows = await mins.lines_of(bot.db, int(row["id"]))
    embed = mins.notes_embed(bot, bot.guild, fresh, rows)
    assert [one.value for one in embed.fields if one.name == "Heard"] == ["Ada, Grace"]


async def test_a_post_discord_refuses_leaves_the_notes_on_the_site_and_logs_it(bot):
    await bot.store.set(GUILD, mins.CHANNEL_KEY, NOTES_CHANNEL)
    bot.channels[NOTES_CHANNEL].raises = RuntimeError("nope")
    row = await a_meeting(bot, lines=THREE_LINES)
    await mins.write_notes(bot, bot.guild, row)
    fresh = await mins.get_meeting(bot.db, GUILD, row["id"])
    found = await mins.post_notes(bot, bot.guild, fresh)
    assert not found.ok and found.code == "post_broke"
    assert mins.POST_FAILED in await kinds(bot.db)


async def test_test_mode_lands_the_notes_in_the_guarded_channel_and_says_where_they_went(bot):
    bot.guard = FakeGuard({TEST_CHANNEL})
    await bot.store.set(GUILD, mins.CHANNEL_KEY, NOTES_CHANNEL)
    row = await a_meeting(bot, lines=THREE_LINES)
    await mins.write_notes(bot, bot.guild, row)
    fresh = await mins.get_meeting(bot.db, GUILD, row["id"])
    found = await mins.post_notes(bot, bot.guild, fresh)
    assert found.ok
    assert bot.channels[NOTES_CHANNEL].sent == []
    assert bot.channels[TEST_CHANNEL].sent
    assert "test mode" in found.message


async def test_landing_leaves_a_channel_the_guard_allows_exactly_where_it_was(bot):
    bot.guard = FakeGuard({NOTES_CHANNEL})
    where, note = mins.landing(bot, bot.guild, NOTES_CHANNEL)
    assert where == NOTES_CHANNEL and note == ""


async def test_with_no_guard_at_all_a_message_goes_to_the_channel_it_named(bot):
    where, note = mins.landing(bot, bot.guild, NOTES_CHANNEL)
    assert where == NOTES_CHANNEL and note == ""


async def test_the_wanted_channel_is_the_key_when_set_and_the_voice_chat_otherwise(bot):
    voice = FakeVoice()
    assert mins.wanted_channel_id(bot, bot.guild, voice) == VOICE_CHANNEL
    await bot.store.set(GUILD, mins.CHANNEL_KEY, NOTES_CHANNEL)
    assert mins.wanted_channel_id(bot, bot.guild, voice) == NOTES_CHANNEL


async def test_staff_can_rewrite_the_notes_and_the_edit_leaves_one_row(bot, staff):
    row = await a_meeting(bot, lines=THREE_LINES)
    await mins.write_notes(bot, bot.guild, row)
    fresh = await mins.get_meeting(bot.db, GUILD, row["id"])
    found = await mins.edit_notes(bot, bot.guild, fresh, staff, "Staff said this instead.")
    assert found.ok
    after = await mins.get_meeting(bot.db, GUILD, row["id"])
    assert after["notes"] == "Staff said this instead."
    assert await kinds(bot.db) == [mins.NOTES_WRITTEN, mins.NOTES_EDITED]


async def test_blank_notes_are_refused_in_words(bot, staff):
    row = await a_meeting(bot, lines=THREE_LINES)
    found = await mins.edit_notes(bot, bot.guild, row, staff, "   ")
    assert not found.ok and found.code == "notes_blank"
    assert "cannot be empty" in found.message


async def test_notes_past_the_cap_are_refused_with_the_count_to_take_out(bot, staff):
    row = await a_meeting(bot, lines=THREE_LINES)
    found = await mins.edit_notes(bot, bot.guild, row, staff, "x" * (mins.NOTES_MAX + 3))
    assert not found.ok and found.code == "notes_too_long"
    assert "Take 3 characters out" in found.message


async def test_deleting_a_meeting_takes_its_transcript_with_it(bot, staff):
    row = await a_meeting(bot, lines=THREE_LINES)
    found = await mins.delete_meeting(bot, bot.guild, row, staff)
    assert found.ok
    assert await mins.get_meeting(bot.db, GUILD, row["id"]) is None
    assert await mins.count_lines(bot.db, int(row["id"])) == 0
    assert await kinds(bot.db) == [mins.DELETED]


async def test_a_website_move_writes_the_web_spelling_of_the_kind(bot, staff):
    from black_bloc.logkinds import VIA_WEBSITE

    row = await a_meeting(bot, lines=THREE_LINES)
    await mins.delete_meeting(bot, bot.guild, row, staff, via=VIA_WEBSITE)
    assert await kinds(bot.db) == ["web.minutes.deleted"]


async def test_the_purge_takes_the_words_and_leaves_the_meeting_and_its_notes(bot):
    row = await a_meeting(bot, lines=THREE_LINES)
    await mins.write_notes(bot, bot.guild, row)
    await bot.db.conn.execute(
        "UPDATE meetings SET started_at = ? WHERE id = ?",
        ((datetime.now(UTC) - timedelta(days=400)).isoformat(), int(row["id"])),
    )
    await bot.db.conn.commit()
    gone = await mins.purge_old_lines(bot.db, GUILD, mins.keep_days(bot.store, GUILD))
    assert gone == 3
    assert await mins.count_lines(bot.db, int(row["id"])) == 0
    kept = await mins.get_meeting(bot.db, GUILD, row["id"])
    assert kept is not None and kept["notes"]


async def test_a_recent_meeting_is_never_purged(bot):
    row = await a_meeting(bot, lines=THREE_LINES)
    assert await mins.purge_old_lines(bot.db, GUILD, mins.keep_days(bot.store, GUILD)) == 0
    assert await mins.count_lines(bot.db, int(row["id"])) == 3


async def test_ending_a_meeting_closes_the_row_and_names_why(bot):
    row = await a_meeting(bot)
    await mins.end_row(bot.db, int(row["id"]), mins.BY_MAX_HOURS)
    fresh = await mins.get_meeting(bot.db, GUILD, row["id"])
    assert fresh["ended_at"] and fresh["ended_reason"] == mins.BY_MAX_HOURS
    assert fresh["status"] == mins.WRITING
    assert await mins.open_meeting(bot.db, GUILD) is None


async def test_the_mode_is_stored_both_ways_and_logged(bot, staff):
    said = await mins.set_mode(bot, bot.guild, staff, mins.ON)
    assert bot.store.get(GUILD, mins.MODE_KEY) == mins.ON
    assert "prototype" in said
    assert await kinds(bot.db) == [mins.MODE_SET]


async def test_a_mode_nobody_recognises_falls_back_to_off_rather_than_storing_it(bot, staff):
    await mins.set_mode(bot, bot.guild, staff, "sideways")
    assert bot.store.get(GUILD, mins.MODE_KEY) == mins.OFF


async def test_the_site_link_is_the_minutes_page_and_blank_origin_means_no_link(bot):
    assert mins.site_page_url("https://x.test") == "https://x.test/minutes.html"
    assert mins.site_page_url("") is None


async def test_the_start_announcement_may_never_be_blank(bot):
    from black_bloc.settings_store import SettingError

    with pytest.raises(SettingError):
        await bot.store.set(GUILD, mins.START_TEXT_KEY, "   ")


@pytest.mark.parametrize(
    "key,bad",
    [
        (mins.CHUNK_SECONDS_KEY, 5),
        (mins.CHUNK_SECONDS_KEY, 500),
        (mins.MAX_HOURS_KEY, 0),
        (mins.MAX_HOURS_KEY, 99),
        (mins.KEEP_DAYS_KEY, 0),
        (mins.KEEP_DAYS_KEY, 5000),
    ],
)
async def test_a_value_outside_its_band_is_refused_with_the_reason(bot, key, bad):
    from black_bloc.settings_store import SettingError

    with pytest.raises(SettingError) as found:
        await bot.store.set(GUILD, key, bad)
    assert "nothing was changed" in str(found.value)


async def test_the_status_word_tracks_the_row(bot):
    row = await a_meeting(bot)
    assert mins.status_words(row) == "recording"
    await mins.end_row(bot.db, int(row["id"]), mins.BY_HAND)
    assert mins.status_words(await mins.get_meeting(bot.db, GUILD, row["id"])) == (
        "writing the notes"
    )


async def test_the_list_is_newest_first(bot):
    first = await a_meeting(bot)
    await mins.end_row(bot.db, int(first["id"]), mins.BY_HAND)
    second = await a_meeting(bot)
    rows = await mins.list_meetings(bot.db, GUILD)
    assert [int(one["id"]) for one in rows] == [int(second["id"]), int(first["id"])]


async def test_a_meeting_id_that_is_not_a_number_answers_nothing_rather_than_raising(bot):
    assert await mins.get_meeting(bot.db, GUILD, "banana") is None
