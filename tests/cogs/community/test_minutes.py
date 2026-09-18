from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from black_bloc import minutes as mins
from black_bloc import minutes_session as session_mod
from black_bloc.cogs.community import minutes as cog
from black_bloc.config import load_settings
from black_bloc.llm import Reply, Usage
from black_bloc.minutes_audio import Chunk
from black_bloc.settings_store import SettingsStore

GUILD = 7
TEST_CHANNEL = 111
NOTES_CHANNEL = 222
VOICE_CHANNEL = 333
STAFF_ROLE = 900
STAFF_ID = 42
BOT_ID = 1


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id
        self.name = "Aunties / Uncles"


class FakeMessage:
    def __init__(self, message_id=9500, **kwargs):
        self.id = message_id
        self.kwargs = dict(kwargs)
        one = kwargs.get("embed")
        self.embeds = list(kwargs.get("embeds") or ([one] if one else []))

    async def edit(self, **kwargs):
        self.kwargs |= kwargs


class FakeChannel:
    def __init__(self, channel_id, name):
        self.id = channel_id
        self.name = name
        self.sent = []

    async def send(self, content=None, **kwargs):
        self.sent.append({"content": content, **kwargs})
        return FakeMessage(**kwargs)


class FakeVoice:
    def __init__(self, members=()):
        self.id = VOICE_CHANNEL
        self.name = "Meeting Room"
        self.voice_states = {one: object() for one in members}
        self.guild = None

    def permissions_for(self, who):
        return SimpleNamespace(connect=True)


class FakeGuild:
    def __init__(self, bot):
        self.id = GUILD
        self.bot = bot
        self.me = SimpleNamespace(id=BOT_ID)
        self.unavailable = False

    def get_channel(self, channel_id):
        return self.bot.channels.get(int(channel_id))

    def get_member(self, user_id):
        return None


class FakeStaff:
    def __init__(self, voice=None):
        self.id = STAFF_ID
        self.name = "Mod"
        self.display_name = "Mod"
        self.roles = [FakeRole(STAFF_ROLE)]
        self.bot = False
        self.voice = SimpleNamespace(channel=voice) if voice is not None else None


class FakeVoiceClient:
    def __init__(self):
        self.listening = False
        self.left = False

    def listen(self, sink):
        self.listening = True

    def stop_listening(self):
        self.listening = False

    async def disconnect(self, force=False):
        self.left = True


class FakeNotes:
    async def reply(self, *, system, messages):
        return Reply(text="Summary.", provider="anthropic", model="m", usage=Usage())


class FakeWhisper:
    async def transcribe(self, audio, *, name="chunk.wav"):
        return "We should ship it."


class FakeBot:
    def __init__(self, db, store, settings):
        self.db = db
        self.store = store
        self.settings = settings
        self.guard = None
        self.user = SimpleNamespace(id=BOT_ID)
        self.channels = {
            TEST_CHANNEL: FakeChannel(TEST_CHANNEL, "blackbloc-logs"),
            NOTES_CHANNEL: FakeChannel(NOTES_CHANNEL, "meeting-notes"),
            VOICE_CHANNEL: FakeChannel(VOICE_CHANNEL, "meeting-room"),
        }
        self.guild = FakeGuild(self)
        self.guilds = [self.guild]
        self.minutes_notes_client = FakeNotes()
        self.minutes_whisper_client = FakeWhisper()

    def get_channel(self, channel_id):
        return self.channels.get(int(channel_id))

    def get_guild(self, guild_id):
        return self.guild if int(guild_id) == GUILD else None

    def get_cog(self, name):
        return None


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.modals = []
        self.done = False

    def is_done(self):
        return self.done

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.done = True
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def send_modal(self, modal):
        self.done = True
        self.modals.append(modal)

    async def defer(self, ephemeral=False, **kwargs):
        self.done = True


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.response.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeInteraction:
    def __init__(self, bot, user):
        self.client = bot
        self.user = user
        self.guild = bot.guild
        self.guild_id = bot.guild.id
        self.channel_id = TEST_CHANNEL
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)
        self.edits = []

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return FakeMessage(**kwargs)

    async def original_response(self):
        return FakeMessage()

    @property
    def said(self):
        found = [one["content"] for one in self.response.messages if one.get("content")]
        return found[-1] if found else None

    @property
    def card(self):
        return self.edits[-1] if self.edits else None


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
    found = FakeBot(db, store, settings)
    store.is_staff = lambda member: getattr(member, "id", None) == STAFF_ID
    return found


@pytest.fixture(autouse=True)
def the_host_can_record(monkeypatch):
    monkeypatch.setattr(mins, "extension_available", lambda: True)
    monkeypatch.setattr(mins, "opus_available", lambda: True)
    client = FakeVoiceClient()

    async def connect(channel):
        return client

    monkeypatch.setattr(session_mod, "connect_to", connect)
    monkeypatch.setattr(session_mod, "build_sink", lambda chunker: SimpleNamespace(chunker=chunker))
    return client


@pytest.fixture
def staff():
    return FakeStaff(FakeVoice([STAFF_ID]))


def labels(view):
    return [one.label for one in view.children if getattr(one, "label", None)]


async def kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def test_the_panel_offers_start_when_nothing_is_running(bot, staff):
    embed, view = await cog.build_panel(bot, bot.guild)
    assert embed.title == mins.PANEL_TITLE
    assert mins.START_LABEL in labels(view)
    assert mins.STOP_LABEL not in labels(view)
    assert mins.SITE_LABEL in labels(view)
    assert mins.PANEL_EMPTY in embed.description


async def test_the_panel_says_minutes_are_off_while_they_are(bot):
    await bot.store.set(GUILD, mins.MODE_KEY, mins.OFF)
    embed, _view = await cog.build_panel(bot, bot.guild)
    assert "turned off" in embed.description


async def test_starting_joins_announces_logs_and_the_panel_flips_to_stop(bot, staff):
    found = await cog.start_meeting(bot, bot.guild, staff)
    assert found.ok
    assert bot.channels[VOICE_CHANNEL].sent[-1]["content"] == mins.start_text(bot.store, GUILD)
    assert await kinds(bot.db) == [mins.STARTED]
    _embed, view = await cog.build_panel(bot, bot.guild)
    assert mins.STOP_LABEL in labels(view)
    await cog.stop_meeting(bot, bot.guild, mins.BY_HAND)


async def test_start_refuses_in_words_when_the_presser_is_in_no_voice_channel(bot):
    found = await cog.start_meeting(bot, bot.guild, FakeStaff())
    assert not found.ok and "not in a voice channel" in found.message
    assert cog.running_in(bot, GUILD) is None


async def test_start_refuses_while_the_mode_is_off(bot, staff):
    await bot.store.set(GUILD, mins.MODE_KEY, mins.OFF)
    found = await cog.start_meeting(bot, bot.guild, staff)
    assert not found.ok and "turned off" in found.message


async def test_stopping_writes_the_notes_and_posts_them(bot, staff):
    await cog.start_meeting(bot, bot.guild, staff)
    session = cog.running_in(bot, GUILD)
    await session.queue.put(Chunk(1, "Ada", session.started_at, 60.0, b"RIFF"))
    found = await cog.stop_meeting(bot, bot.guild, mins.BY_HAND)
    assert found.ok
    row = await mins.get_meeting(bot.db, GUILD, found.value)
    assert row["notes"] == "Summary."
    assert any(one.get("embed") for one in bot.channels[VOICE_CHANNEL].sent)
    assert cog.running_in(bot, GUILD) is None


async def test_stopping_with_nothing_running_refuses_in_words(bot):
    found = await cog.stop_meeting(bot, bot.guild, mins.BY_HAND)
    assert not found.ok and "No meeting is being recorded" in found.message


async def test_the_panel_card_offers_the_staff_moves_once_a_meeting_is_over(bot, staff):
    await cog.start_meeting(bot, bot.guild, staff)
    session = cog.running_in(bot, GUILD)
    await cog.stop_meeting(bot, bot.guild, mins.BY_HAND)
    row = await mins.get_meeting(bot.db, GUILD, session.meeting_id)
    _embed, view = cog.build_card(bot, bot.guild, row)
    assert mins.POST_AGAIN_LABEL in labels(view)
    assert cog.EDIT_LABEL in labels(view)
    assert cog.REWRITE_LABEL in labels(view)
    assert mins.DELETE_LABEL in labels(view)


async def test_a_recording_meetings_card_offers_delete_but_no_notes_moves(bot, staff):
    await cog.start_meeting(bot, bot.guild, staff)
    session = cog.running_in(bot, GUILD)
    row = await mins.get_meeting(bot.db, GUILD, session.meeting_id)
    _embed, view = cog.build_card(bot, bot.guild, row)
    assert mins.POST_AGAIN_LABEL not in labels(view)
    assert mins.DELETE_LABEL in labels(view)
    await cog.stop_meeting(bot, bot.guild, mins.BY_HAND)


async def test_everybody_leaving_the_channel_ends_the_meeting(bot, staff):
    await cog.start_meeting(bot, bot.guild, staff)
    staff.guild = bot.guild
    voice = staff.voice.channel
    bot.channels[VOICE_CHANNEL] = voice
    voice.voice_states = {BOT_ID: object()}
    await cog.Minutes(bot).on_voice_state_update(staff, None, None)
    assert cog.running_in(bot, GUILD) is None


async def test_one_person_left_in_the_channel_keeps_the_meeting_running(bot, staff):
    await cog.start_meeting(bot, bot.guild, staff)
    staff.guild = bot.guild
    voice = staff.voice.channel
    bot.channels[VOICE_CHANNEL] = voice
    voice.voice_states = {BOT_ID: object(), STAFF_ID: object()}
    await cog.Minutes(bot).on_voice_state_update(staff, None, None)
    assert cog.running_in(bot, GUILD) is not None
    await cog.stop_meeting(bot, bot.guild, mins.BY_HAND)


async def test_saying_stop_notes_in_the_meetings_chat_ends_it(bot, staff):
    await cog.start_meeting(bot, bot.guild, staff)
    message = SimpleNamespace(
        guild=bot.guild,
        author=staff,
        content="ok, STOP NOTES please",
        channel=SimpleNamespace(id=VOICE_CHANNEL),
    )
    await cog.Minutes(bot).on_message(message)
    assert cog.running_in(bot, GUILD) is None


async def test_the_same_words_somewhere_else_are_ignored(bot, staff):
    await cog.start_meeting(bot, bot.guild, staff)
    message = SimpleNamespace(
        guild=bot.guild,
        author=staff,
        content="stop notes",
        channel=SimpleNamespace(id=NOTES_CHANNEL),
    )
    await cog.Minutes(bot).on_message(message)
    assert cog.running_in(bot, GUILD) is not None
    await cog.stop_meeting(bot, bot.guild, mins.BY_HAND)


async def test_the_bots_own_message_never_stops_a_meeting(bot, staff):
    await cog.start_meeting(bot, bot.guild, staff)
    message = SimpleNamespace(
        guild=bot.guild,
        author=SimpleNamespace(bot=True),
        content="stop notes",
        channel=SimpleNamespace(id=VOICE_CHANNEL),
    )
    await cog.Minutes(bot).on_message(message)
    assert cog.running_in(bot, GUILD) is not None
    await cog.stop_meeting(bot, bot.guild, mins.BY_HAND)


async def test_the_sweep_ends_a_meeting_that_ran_past_max_hours(bot, staff):
    await cog.start_meeting(bot, bot.guild, staff)
    session = cog.running_in(bot, GUILD)
    session.started_at = datetime.now(UTC) - timedelta(hours=9)
    await cog.Minutes(bot).sweep_guild(bot.guild)
    assert cog.running_in(bot, GUILD) is None
    row = await mins.get_meeting(bot.db, GUILD, session.meeting_id)
    assert row["ended_reason"] == mins.BY_MAX_HOURS


async def test_the_sweep_closes_a_meeting_a_restart_left_open(bot):
    row = await mins.start_row(bot.db, GUILD, VOICE_CHANNEL, STAFF_ID)
    await cog.Minutes(bot).sweep_guild(bot.guild)
    fresh = await mins.get_meeting(bot.db, GUILD, row["id"])
    assert fresh["ended_at"] and fresh["ended_reason"] == mins.BY_SHUTDOWN


async def test_the_sweep_leaves_a_guild_with_nothing_open_alone(bot):
    await cog.Minutes(bot).sweep_guild(bot.guild)
    assert await kinds(bot.db) == []


class PickedChannel(cog.ChannelPick):
    @property
    def values(self):
        return [SimpleNamespace(id=NOTES_CHANNEL)]


async def test_where_notes_go_stores_the_channel_both_doors_read(bot, staff):
    interaction = FakeInteraction(bot, staff)
    pick = PickedChannel()
    pick._view = cog.MinutesView(10)

    await pick.callback(interaction)

    assert bot.store.get(GUILD, mins.CHANNEL_KEY) == NOTES_CHANNEL
    assert "#meeting-notes" in interaction.said


async def test_the_command_refuses_in_a_dm_in_words(bot, staff):
    interaction = FakeInteraction(bot, staff)
    interaction.guild = None
    await cog.Minutes(bot).minutes_panel_command.callback(cog.Minutes(bot), interaction)
    assert "server" in interaction.said


async def test_the_command_opens_one_ephemeral_panel(bot, staff):
    interaction = FakeInteraction(bot, staff)
    one = cog.Minutes(bot)
    await one.minutes_panel_command.callback(one, interaction)
    sent = interaction.response.messages[-1]
    assert sent["ephemeral"] is True
    assert sent["embed"].title == mins.PANEL_TITLE


async def test_a_member_who_is_not_staff_is_refused_in_words(bot):
    plain = FakeStaff()
    plain.id = 5
    interaction = FakeInteraction(bot, plain)
    one = cog.Minutes(bot)
    await one.minutes_panel_command.callback(one, interaction)
    assert "staff only" in interaction.said


async def test_the_meeting_line_names_where_and_when_and_how_it_stands(bot, staff):
    row = await mins.start_row(bot.db, GUILD, VOICE_CHANNEL, STAFF_ID)
    said = cog.meeting_line(bot.guild, row)
    assert "#meeting-room" in said and "recording" in said
