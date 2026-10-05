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
NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


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
        {
            "guild_id": GUILD,
            "channel_id": 1,
            "user_id": MEMBER,
            "speaker": "member",
            "content": "a",
        },
        {"guild_id": GUILD, "channel_id": 1, "user_id": MEMBER, "speaker": "bot", "content": "b"},
        {
            "guild_id": GUILD,
            "channel_id": 2,
            "user_id": MEMBER,
            "speaker": "member",
            "content": "c",
        },
        {"guild_id": None, "channel_id": 3, "user_id": MEMBER, "speaker": "member", "content": "d"},
    ]

    found = run_it.conversations(rows)

    assert set(found) == {
        (GUILD, 1, MEMBER),
        (GUILD, 2, MEMBER),
        (None, 3, MEMBER),
    }
    assert len(found[(GUILD, 1, MEMBER)]) == 2


def test_a_conversation_needs_enough_member_turns_and_not_one_staff_word():
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
    assert run_it.worth_distilling(one) is True
    assert run_it.worth_distilling(one, 2) is False
    assert run_it.worth_distilling(staff) is False
    assert run_it.why_skipped(one, 2) == "short"
    assert run_it.why_skipped(staff) == "staff"
    assert run_it.why_skipped([{"speaker": "bot", "content": "Hello."}]) == "short"
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

    assert (found["seen"], found["looked"], found["distilled"]) == (1, 1, 1)
    assert (found["failed"], found["nothing"], found["expired"]) == (0, 0, 0)
    assert found["reasons"] == {} and found["skipped"] == {}
    assert found["lines"] == {"names": 1, "notes": 1, "threads": 1, "rapport": 0}
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


async def _memory_off(bot, db):
    await bot.store.set(GUILD, "chat_memory_mode", "off")


async def _opted_out(bot, db):
    await set_override(db, MEMBER, GUILD)


async def _month_capped(bot, db):
    await bot.store.set(GUILD, "chat_monthly_cap_usd", 0)


async def _nothing(bot, db):
    return None


async def _two_turns_at_least(bot, db):
    await bot.store.set(GUILD, "chat_memory_min_turns", 2)


@pytest.mark.parametrize(
    ("before", "said"),
    [
        (_memory_off, None),
        (_opted_out, None),
        (_nothing, ["I go by Sky", "can I appeal the timeout a mod gave me last night"]),
        (_two_turns_at_least, ["lol"]),
        (_month_capped, None),
    ],
    ids=["mode-off", "opted-out", "staff-conversation-never-sent", "one-liner", "month-capped"],
)
async def test_a_conversation_the_sweep_must_not_send_is_never_looked_at(bot, db, before, said):
    client = with_client(bot, FakeGroq())
    await before(bot, db)
    await a_conversation(db, said=said)

    found = await run_it.run(bot)

    assert found["looked"] == 0 and client.calls == []
    assert await profile_for(db, MEMBER, GUILD) is None


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


async def test_a_profile_nobody_has_added_to_expires_on_the_same_sweep(bot, db):
    with_client(bot, FakeGroq())
    from black_bloc.chat_memory import Profile, save_profile

    old = (datetime.now(UTC) - timedelta(days=200)).isoformat()
    await save_profile(db, OTHER, GUILD, Profile(call_me="Gone", created_at=old, updated_at=old))

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


async def turns_at(db, said, *, guild_id=GUILD, user_id=MEMBER, channel_id=CHANNEL, at=None):
    """A conversation on a pinned clock, two hours before NOW, so the sweep is about to take it."""
    started = at or NOW - timedelta(hours=2)
    for number, (speaker, words) in enumerate(said):
        await remember(
            db,
            guild_id=guild_id,
            channel_id=channel_id,
            user_id=user_id,
            speaker=speaker,
            content=words,
            tier="simple" if speaker == "bot" else None,
            at=started + timedelta(seconds=number),
        )


async def details_of(db, kind):
    cur = await db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id DESC LIMIT 1", (kind,)
    )
    row = await cur.fetchone()
    return None if row is None else json.loads(row["details"])


SHORT_BANTER = [
    ("member", "lol you are such a toaster"),
    ("bot", "A toaster with opinions."),
]
TWO_TURNS = [
    ("member", "yo"),
    ("bot", "Yo."),
    ("member", "what games do people play here"),
    ("bot", "Mostly speedruns and fighting games."),
]
A_PREFERENCE = [
    ("member", "hey call me Sky from now on"),
    ("bot", "Sky it is."),
    ("member", "also keep it brief, walls of text lose me"),
    ("bot", "Brief. Got it."),
]
ONLY_JOKES = [
    ("member", "why did the speedrunner cross the road"),
    ("bot", "To clip through it."),
    ("member", "LMAO ok that was good"),
    ("bot", "I have my moments."),
]
EMPTY_ANSWER = json.dumps({"call_me": None, "notes": [], "threads": [], "rapport": []})


def test_the_distiller_gets_room_to_think_which_the_reply_client_never_had(bot):
    """Measured 2026-10-05: gpt-oss-120b spent 153-307 of a 400-token ceiling on reasoning."""
    from black_bloc.groq import GroqClient
    from black_bloc.llm import MAX_TOKENS

    cramped = GroqClient("test-key", model="openai/gpt-oss-120b")
    assert cramped.max_tokens == MAX_TOKENS == 400
    setattr(bot, CLIENTS_ATTR, {MEMORY_TIER: cramped})

    found = run_it.distiller(bot, "openai/gpt-oss-120b")

    assert found is not cramped
    assert found.max_tokens == run_it.DISTIL_MAX_TOKENS == 1200
    assert run_it.distiller(bot, "openai/gpt-oss-120b") is found
    assert run_it.distiller(bot, "llama-3.3-70b-versatile").model == "llama-3.3-70b-versatile"


async def test_the_live_failure_json_cut_off_at_the_token_ceiling_now_says_why(
    bot, db, monkeypatch
):
    """Groq answers 400 `json_validate_failed` when the ceiling is hit; that is a refusal."""
    from black_bloc.groq import GroqClient

    asked = []

    async def cut_off(url, *, headers, json):
        asked.append(json)
        return 400, {"error": {"code": "json_validate_failed"}}

    cramped = GroqClient("test-key", model="openai/gpt-oss-120b", request=cut_off)
    monkeypatch.setattr(run_it, "distiller", lambda bot, model: cramped)
    await turns_at(db, A_PREFERENCE)

    found = await run_it.run(bot, now=NOW)

    assert asked[0]["max_tokens"] == 400
    assert asked[0]["response_format"] == {"type": "json_object"}
    assert (found["looked"], found["distilled"], found["failed"]) == (1, 0, 1)
    assert found["reasons"] == {"no_answer": 1} and found["no_answer"] == {"refused": 1}
    failed = await details_of(db, "chat.memory_distil_failed")
    assert failed["conversations"] == 1
    assert failed["reasons"] == {"no_answer": 1} and failed["no_answer"] == {"refused": 1}
    assert await profile_for(db, MEMBER, GUILD) is None


@pytest.mark.parametrize(
    ("said", "answer", "wanted"),
    [
        (SHORT_BANTER, EMPTY_ANSWER, {"nothing": 1, "distilled": 0}),
        (TWO_TURNS, EMPTY_ANSWER, {"nothing": 1, "distilled": 0}),
        (A_PREFERENCE, ANSWER, {"nothing": 0, "distilled": 1}),
        (
            ONLY_JOKES,
            json.dumps({"call_me": None, "notes": [], "threads": [], "rapport": ["enjoys puns"]}),
            {"nothing": 0, "distilled": 1},
        ),
    ],
    ids=["short-banter", "two-turns", "a-preference", "only-jokes"],
)
async def test_real_shaped_conversations_each_end_in_a_named_outcome(
    bot, db, said, answer, wanted
):
    client = with_client(bot, FakeGroq(text=answer))
    await turns_at(db, said)

    found = await run_it.run(bot, now=NOW)

    assert len(client.calls) == 1 and found["looked"] == 1 and found["failed"] == 0
    assert {key: found[key] for key in wanted} == wanted
    swept = await details_of(db, "chat.memory_sweep")
    assert swept["seen"] == 1 and swept["ran_at"] == NOW.isoformat()
    assert await details_of(db, "chat.memory_distil_failed") is None


async def test_nothing_worth_keeping_is_a_routine_row_and_never_a_failure(bot, db):
    with_client(bot, FakeGroq(text=EMPTY_ANSWER))
    await turns_at(db, SHORT_BANTER)

    found = await run_it.run(bot, now=NOW)

    assert (found["nothing"], found["failed"], found["dropped"]) == (1, 0, 0)
    assert await profile_for(db, MEMBER, GUILD) is None
    kinds = await action_kinds(db)
    assert "chat.memory_sweep" in kinds and "chat.memory_distil_failed" not in kinds
    assert "chat.memory_distilled" not in kinds


async def test_a_sweep_with_no_conversation_in_front_of_it_writes_no_row(bot, db):
    with_client(bot, FakeGroq())

    found = await run_it.run(bot, now=NOW)

    assert found == run_it.EMPTY_RUN
    assert await action_kinds(db) == []
    assert await run_it.last_run(db, GUILD) is None


async def test_everything_dropped_by_a_rule_names_the_rule_and_stores_nothing(bot, db):
    """KI-14's shape: a conversation about other people, written up as lines about them."""
    gossip = json.dumps(
        {
            "call_me": None,
            "notes": ["Namu said the mods are unfair", "thinks someone else should run events"],
            "threads": ["namu quitting the server"],
            "rapport": ["jokes about what his friend did"],
        }
    )
    with_client(bot, FakeGroq(text=gossip))
    await turns_at(
        db,
        [
            ("member", "did you hear what Namu told everybody about the tournament"),
            ("bot", "I did not."),
            ("member", "Namu is quitting the server over it apparently"),
            ("bot", "That is a lot."),
        ],
    )

    found = await run_it.run(bot, now=NOW)

    assert (found["dropped"], found["distilled"], found["failed"]) == (1, 0, 0)
    assert found["reasons"] == {"all_dropped": 1}
    assert found["rules"] == {"third_person": 4}
    assert await profile_for(db, MEMBER, GUILD) is None
    failed = await details_of(db, "chat.memory_distil_failed")
    assert failed["reasons"] == {"all_dropped": 1} and failed["rules"] == {"third_person": 4}
    assert "namu" not in json.dumps(failed).lower()


async def test_closed_models_are_counted_by_why_and_one_full_person_does_not_stop_the_rest(
    bot, db
):
    from black_bloc.llm import record

    client = with_client(bot, FakeGroq())
    await bot.store.set(GUILD, "chat_person_hourly_turns", 1)
    await record(
        db,
        guild_id=GUILD,
        user_id=MEMBER,
        turn="t1",
        provider=GROQ,
        model="m",
        tier="simple",
        at=NOW - timedelta(minutes=5),
    )
    await turns_at(db, A_PREFERENCE)
    await turns_at(db, A_PREFERENCE, user_id=OTHER)

    found = await run_it.run(bot, now=NOW)

    assert (found["seen"], found["closed"], found["looked"], found["distilled"]) == (2, 1, 1, 1)
    assert found["reasons"] == {"models_closed": 1} and found["closed_why"] == {"person": 1}
    assert len(client.calls) == 1
    assert await profile_for(db, MEMBER, GUILD) is None
    assert await profile_for(db, OTHER, GUILD) is not None


async def test_a_bot_with_no_model_key_says_so(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    settings = load_settings(
        _env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL, dev_guild_id=GUILD
    )
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "chat_memory_mode", "on")
    keyless = FakeBot(db, store, settings, FakeGuild())
    assert settings.simple_tier_configured is False
    await turns_at(db, A_PREFERENCE)

    found = await run_it.run(keyless, now=NOW)

    assert found["failed"] == 1 and found["reasons"] == {"no_model": 1}


async def test_the_skips_are_counted_by_reason(bot, db):
    client = with_client(bot, FakeGroq())
    await bot.store.set(GUILD, "chat_memory_min_turns", 2)
    await set_override(db, OTHER, GUILD)
    await turns_at(db, SHORT_BANTER)
    await turns_at(db, A_PREFERENCE, user_id=OTHER)
    await turns_at(
        db,
        [("member", "I go by Sky"), ("member", "can I appeal the timeout a mod gave me")],
        channel_id=222,
    )

    found = await run_it.run(bot, now=NOW)

    assert found["seen"] == 3 and found["looked"] == 0 and client.calls == []
    assert found["skipped"] == {"short": 1, "opted_out": 1, "staff": 1}
    assert (await details_of(db, "chat.memory_sweep"))["skipped"] == found["skipped"]


async def test_an_empty_answer_leaves_a_standing_profile_and_its_clock_alone(bot, db):
    from black_bloc.chat_memory import Profile, save_profile

    with_client(bot, FakeGroq(text=EMPTY_ANSWER))
    old = (NOW - timedelta(days=30)).isoformat()
    await save_profile(db, MEMBER, GUILD, Profile(call_me="Sky", created_at=old, updated_at=old))
    await turns_at(db, SHORT_BANTER)

    found = await run_it.run(bot, now=NOW)
    profile = await profile_for(db, MEMBER, GUILD)

    assert found["nothing"] == 1
    assert profile.updated_at == old and profile.turns_seen == 0


async def test_the_last_sweep_reads_back_off_the_log_as_counts(bot, db):
    with_client(bot, FakeGroq())
    await turns_at(db, A_PREFERENCE)
    await run_it.run(bot, now=NOW)

    found = await run_it.last_run(db, GUILD)

    assert found["at"] == NOW.isoformat()
    assert (found["seen"], found["distilled"], found["failed"]) == (1, 1, 0)
    assert found["lines"] == {"names": 1, "notes": 1, "threads": 1, "rapport": 0}
    assert "Sky" not in json.dumps(found)
