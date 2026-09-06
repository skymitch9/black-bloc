import json
from datetime import UTC, datetime, timedelta

import pytest

from black_bloc import chat_distil as run_it
from black_bloc.chat_llm import CLIENTS_ATTR, remember
from black_bloc.chat_memory import MEMORY_TIER, profile_for, set_override
from black_bloc.config import load_settings
from black_bloc.llm import GROQ, Reply, Usage
from black_bloc.settings_store import SettingsStore

GUILD = 7
CHANNEL = 111
TEST_CHANNEL = 111
MEMBER = 900
OTHER = 901

ANSWER = json.dumps(
    {
        "call_me": "Sky",
        "notes": ["likes short answers"],
        "threads": ["was asking about the cookout"],
    }
)


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id
        self.name = f"role-{role_id}"


class FakeMember:
    def __init__(self, user_id, name):
        self.id = user_id
        self.name = name
        self.display_name = name
        self.bot = False
        self.roles = []


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black in a Flash!"
        self.members = [FakeMember(MEMBER, "Ada"), FakeMember(OTHER, "Namu")]
        self.roles = []
        self.unavailable = False

    def get_channel(self, channel_id):
        return None

    def get_member(self, user_id):
        return next((one for one in self.members if one.id == user_id), None)


class FakeGroq:
    """The injectable client the real one is built to allow; no network, ever."""

    model = "openai/gpt-oss-120b"

    def __init__(self, text=ANSWER, raises=None):
        self.text = text
        self.raises = raises
        self.calls = []

    async def reply(self, *, system, messages, json_only=False):
        self.calls.append({"system": system, "messages": messages, "json_only": json_only})
        if self.raises is not None:
            raise self.raises
        return Reply(
            text=self.text,
            provider=GROQ,
            model=self.model,
            usage=Usage(input_tokens=400, output_tokens=90),
        )


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guild = guild
        self.guilds = [guild]

    def get_guild(self, guild_id):
        return self.guild if int(guild_id) == self.guild.id else None


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(
        _env_file=None,
        test_mode=True,
        test_channel_id=TEST_CHANNEL,
        dev_guild_id=GUILD,
        groq_api_key="test-key",
    )
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "chat_memory_mode", "on")
    return FakeBot(db, store, settings, FakeGuild())


def with_client(bot, client):
    setattr(bot, CLIENTS_ATTR, {MEMORY_TIER: client})
    return client


async def a_conversation(db, *, guild_id=GUILD, user_id=MEMBER, said=None, hours=3):
    at = datetime.now(UTC) - timedelta(hours=hours)
    lines = said or ["I go by Sky", "keep answers short please"]
    for number, one in enumerate(lines):
        await remember(
            db,
            guild_id=guild_id,
            channel_id=CHANNEL,
            user_id=user_id,
            speaker="member",
            content=one,
            at=at + timedelta(seconds=number),
        )
        await remember(
            db,
            guild_id=guild_id,
            channel_id=CHANNEL,
            user_id=user_id,
            speaker="bot",
            content="Noted.",
            tier="simple",
            at=at + timedelta(seconds=number),
        )


async def ledger_rows(db):
    cur = await db.conn.execute("SELECT tier, outcome, model FROM llm_ledger ORDER BY id")
    return [(row["tier"], row["outcome"], row["model"]) for row in await cur.fetchall()]


async def action_kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


def test_a_conversation_is_one_person_in_one_place():
    rows = [
        {"guild_id": GUILD, "channel_id": 1, "user_id": MEMBER, "speaker": "member",
         "content": "a"},
        {"guild_id": GUILD, "channel_id": 1, "user_id": MEMBER, "speaker": "bot", "content": "b"},
        {"guild_id": GUILD, "channel_id": 2, "user_id": MEMBER, "speaker": "member",
         "content": "c"},
        {"guild_id": None, "channel_id": 3, "user_id": MEMBER, "speaker": "member", "content": "d"},
    ]

    found = run_it.conversations(rows)

    assert set(found) == {
        (GUILD, 1, MEMBER),
        (GUILD, 2, MEMBER),
        (None, 3, MEMBER),
    }
    assert len(found[(GUILD, 1, MEMBER)]) == 2


def test_a_conversation_needs_two_member_turns_and_not_one_staff_word():
    two = [
        {"speaker": "member", "content": "I go by Sky"},
        {"speaker": "bot", "content": "Sky it is."},
        {"speaker": "member", "content": "keep it short"},
    ]
    one = [{"speaker": "member", "content": "lol"}, {"speaker": "bot", "content": "Fair."}]
    staff = [
        {"speaker": "member", "content": "I go by Sky"},
        {"speaker": "member", "content": "can I appeal the timeout a mod gave me"},
    ]

    assert run_it.worth_distilling(two) is True
    assert run_it.worth_distilling(one) is False
    assert run_it.worth_distilling(staff) is False
    assert len(run_it.member_turns(two)) == 2


async def test_only_the_turns_the_sweep_is_about_to_delete_are_read(db):
    await a_conversation(db, hours=3)
    await a_conversation(db, user_id=OTHER, hours=0)

    found = await run_it.expiring(db)

    assert {int(row["user_id"]) for row in found} == {MEMBER}


async def test_a_conversation_becomes_a_profile_and_a_ledger_row(bot, db):
    client = with_client(bot, FakeGroq())
    await a_conversation(db)

    found = await run_it.run(bot)
    profile = await profile_for(db, MEMBER, GUILD)

    assert found == {"looked": 1, "distilled": 1, "failed": 0, "expired": 0}
    assert profile is not None
    assert profile.call_me == "Sky"
    assert [one.text for one in profile.notes] == ["likes short answers"]
    assert profile.notes[0].where == "server"
    assert profile.turns_seen == 2
    assert client.calls[0]["json_only"] is True
    assert await ledger_rows(db) == [(MEMORY_TIER, "ok", "openai/gpt-oss-120b")]
    assert "chat.memory_distilled" in await action_kinds(db)


async def test_the_log_line_carries_counts_and_never_the_words_themselves(bot, db):
    with_client(bot, FakeGroq())
    await a_conversation(db)

    await run_it.run(bot)
    cur = await db.conn.execute(
        "SELECT details FROM action_log WHERE kind = 'chat.memory_distilled'"
    )
    details = json.loads((await cur.fetchone())["details"])

    assert details["notes"] == 1 and details["threads"] == 1 and details["dropped"] == 0
    assert details["where"] == "server"
    assert "Sky" not in json.dumps(details) and "short answers" not in json.dumps(details)


async def test_mode_off_distils_nothing_at_all(bot, db):
    client = with_client(bot, FakeGroq())
    await bot.store.set(GUILD, "chat_memory_mode", "off")
    await a_conversation(db)

    found = await run_it.run(bot)

    assert found["looked"] == 0 and client.calls == []
    assert await profile_for(db, MEMBER, GUILD) is None


async def test_somebody_who_opted_out_is_skipped(bot, db):
    client = with_client(bot, FakeGroq())
    await set_override(db, MEMBER, GUILD)
    await a_conversation(db)

    found = await run_it.run(bot)

    assert found["looked"] == 0 and client.calls == []


async def test_a_staff_conversation_is_never_sent(bot, db):
    client = with_client(bot, FakeGroq())
    await a_conversation(
        db, said=["I go by Sky", "can I appeal the timeout a mod gave me last night"]
    )

    found = await run_it.run(bot)

    assert found["looked"] == 0 and client.calls == []
    assert await profile_for(db, MEMBER, GUILD) is None


async def test_a_one_liner_is_not_worth_a_call(bot, db):
    client = with_client(bot, FakeGroq())
    await a_conversation(db, said=["lol"])

    found = await run_it.run(bot)

    assert found["looked"] == 0 and client.calls == []


async def test_a_dm_is_filed_under_the_one_server_with_a_dm_scoped_note(bot, db):
    with_client(bot, FakeGroq())
    await a_conversation(db, guild_id=None)

    await run_it.run(bot)
    profile = await profile_for(db, MEMBER, GUILD)

    assert profile is not None
    assert profile.notes[0].where == "dm"


async def test_a_model_that_does_not_answer_loses_one_conversation_not_a_reply(bot, db):
    from black_bloc.llm import UNREACHABLE, LLMError

    with_client(bot, FakeGroq(raises=LLMError(UNREACHABLE, "groq unreachable")))
    await a_conversation(db)

    found = await run_it.run(bot)

    assert found["distilled"] == 0 and found["failed"] == 1
    assert await profile_for(db, MEMBER, GUILD) is None
    assert await ledger_rows(db) == [(MEMORY_TIER, "error", "openai/gpt-oss-120b")]
    assert "chat.memory_distil_failed" in await action_kinds(db)


async def test_an_answer_in_the_wrong_shape_writes_nothing_at_all(bot, db):
    with_client(bot, FakeGroq(text="I think Sky likes short answers!"))
    await a_conversation(db)

    found = await run_it.run(bot)

    assert found["failed"] == 1
    assert await profile_for(db, MEMBER, GUILD) is None


async def test_a_capped_month_distils_nothing(bot, db):
    client = with_client(bot, FakeGroq())
    await bot.store.set(GUILD, "chat_monthly_cap_usd", 0)
    await a_conversation(db)

    found = await run_it.run(bot)

    assert found["looked"] == 0 and client.calls == []


async def test_a_profile_nobody_has_added_to_expires_on_the_same_sweep(bot, db):
    with_client(bot, FakeGroq())
    from black_bloc.chat_memory import Profile, save_profile

    old = (datetime.now(UTC) - timedelta(days=200)).isoformat()
    await save_profile(
        db, OTHER, GUILD, Profile(call_me="Gone", created_at=old, updated_at=old)
    )

    found = await run_it.run(bot)

    assert found["expired"] == 1
    assert await profile_for(db, OTHER, GUILD) is None
    assert "chat.memory_expired" in await action_kinds(db)


async def test_forever_means_forever(bot, db):
    with_client(bot, FakeGroq())
    from black_bloc.chat_memory import Profile, save_profile

    await bot.store.set(GUILD, "chat_memory_retention_days", 0)
    old = (datetime.now(UTC) - timedelta(days=2000)).isoformat()
    await save_profile(db, OTHER, GUILD, Profile(call_me="Old", created_at=old, updated_at=old))

    found = await run_it.run(bot)

    assert found["expired"] == 0
    assert await profile_for(db, OTHER, GUILD) is not None


async def test_the_prompt_carries_the_profile_already_stored(bot, db):
    from black_bloc.chat_memory import Note, Profile, save_profile

    client = with_client(bot, FakeGroq())
    await save_profile(
        db,
        MEMBER,
        GUILD,
        Profile(call_me="Sky", notes=(Note("hates emoji", "server", "2026-09-01"),)),
    )
    await a_conversation(db)

    await run_it.run(bot)

    assert "hates emoji" in client.calls[0]["messages"][0]["content"]
