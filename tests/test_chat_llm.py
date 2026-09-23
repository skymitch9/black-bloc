from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from black_bloc import chat_llm
from black_bloc.channel_notes import set_note as set_channel_note
from black_bloc.chat_llm import (
    BOT,
    BUDGET_WORDS,
    CAPPED,
    CONVERSATION_TURNS,
    MEMBER,
    OPEN,
    PERSON_FULL,
    QUESTION_WORDS,
    SERVER_FULL,
    TURN_CHARS,
    WINDOW_MINUTES,
    a_conversation,
    a_real_question,
    about_staff,
    allowance,
    as_messages,
    capped_already_logged,
    clip,
    conversational_reply,
    grounded,
    is_a_question,
    ladder,
    llm_turns,
    money,
    month_spend,
    month_start,
    person_turns,
    remember,
    says_a_budget_word,
    server_turns,
    setting,
    spoken,
    sweep_window,
    tier_errors,
    tier_for,
    user_turn,
    window_for,
    window_key,
    word_count,
)
from black_bloc.knowledge import (
    ANY_OF,
    GROUNDING_NOTE,
    add_section,
    search,
)
from black_bloc.llm import (
    ANTHROPIC,
    GROQ,
    IMPORTANT,
    MODEL,
    SIMPLE,
    LLMError,
    Reply,
    Usage,
    record,
)
from black_bloc.personas import BANTER_STYLE
from black_bloc.storage.db import Database

NOW = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)

LONG = "hey can somebody tell me how the role menus work and where I pick my colour?"
SHORT_Q = "you good?"


def turn(tier=None):
    return {"speaker": "bot", "content": "words", "tier": tier}


def test_the_mention_comes_out_but_the_punctuation_stays():
    assert spoken("<@123> what time is it?") == "what time is it?"
    assert spoken("<@!123>   spaced   out  ") == "spaced out"
    assert spoken(None) == ""


def test_a_word_count_ignores_the_mention():
    assert word_count("<@123> one two three") == 3
    assert word_count("<@123>") == 0


def test_a_long_question_needs_both_the_mark_and_the_words():
    assert word_count(LONG) > QUESTION_WORDS
    assert a_real_question(LONG) is True
    assert a_real_question(SHORT_Q) is False
    assert a_real_question(LONG.replace("?", ".")) is False


def test_staff_topics_are_matched_on_whole_words_not_fragments():
    assert about_staff("can a mod look at this") is True
    assert about_staff("I want to report someone") is True
    assert about_staff("modern art is great") is False
    assert about_staff("banner colours") is False


def test_only_a_turn_a_model_answered_counts_towards_a_conversation():
    window = [turn(), turn(IMPORTANT), turn(), turn(SIMPLE)]
    assert llm_turns(window) == 2
    assert llm_turns([]) == 0
    assert a_conversation(window) is True
    assert a_conversation([turn(SIMPLE)]) is False
    assert CONVERSATION_TURNS == 2


NOTES = [
    {
        "id": 1,
        "title": "Cookout hours",
        "body": "The grill is on Friday from six and Sunday from noon.",
        "source": "staff",
        "tag": "rules",
    },
    {
        "id": 2,
        "title": "Channels in this server",
        "body": "#general, #off-topic, #cookout-chat",
        "source": "server",
        "tag": "channel",
    },
]


def looked_up(query):
    """The real search over real notes: a hit's strength is not something a test invents."""
    return search(NOTES, query)


RULES = [
    ("a strong knowledge hit means the answer must be grounded", "cookout hours",
     looked_up("cookout hours"), [], IMPORTANT),
    ("a weak hit rides along as grounding without buying the careful tier", "lol whatever",
     looked_up("lol whatever"), [], SIMPLE),
    ("a long question is a real question", LONG, [], [], IMPORTANT),
    ("a short question is still banter", SHORT_Q, [], [], SIMPLE),
    ("two model turns already means a conversation", "and then?", [],
     [turn(SIMPLE), turn(SIMPLE)], IMPORTANT),
    ("one model turn is not a conversation yet", "ha", [], [turn(SIMPLE)], SIMPLE),
    ("staff topics are never answered by the cheap tier", "is a mod around", [], [], IMPORTANT),
    ("a greeting that slipped past the intents", "heyyy", [], [], SIMPLE),
    ("a one-liner", "lol", [], [], SIMPLE),
    ("an empty message", "", [], [], SIMPLE),
]


@pytest.mark.parametrize(
    "why, message, hits, window, wanted", RULES, ids=[row[0] for row in RULES]
)
def test_the_tier_table(why, message, hits, window, wanted):
    assert tier_for(message, hits, window) == wanted


def test_a_strong_hit_wins_over_everything_else_because_grounding_is_the_point():
    found = looked_up("cookout hours")
    assert found.strong is True
    assert tier_for("lol", found, []) == IMPORTANT


def test_a_casual_message_with_only_weak_hits_stays_on_the_cheap_tier():
    """Measured 2026-09-01: 8 of 8 live calls went IMPORTANT because ANY hit promoted."""
    found = looked_up("cookout parliament")
    assert found.hits and found.matched == ANY_OF
    assert found.strong is False
    assert tier_for("cookout parliament", found, []) == SIMPLE
    assert looked_up("hi").hits == ()


def test_banter_gets_no_notes_and_questions_or_sure_hits_keep_them():
    """2026-09-23: "What up" came back with three notes quoted at the member."""
    weak = looked_up("cookout parliament")
    strong = looked_up("cookout hours")
    assert weak.strong is False and strong.strong is True
    assert grounded(SIMPLE, "sup fam", weak) == ()
    assert grounded(SIMPLE, "cookout parliament", weak) == ()
    assert grounded(SIMPLE, "cookout parliament?", weak) is weak
    assert grounded(SIMPLE, "when is the cookout parliament", weak) is weak
    assert grounded(SIMPLE, "cookout hours", strong) is strong
    assert grounded(IMPORTANT, "cookout parliament", weak) is weak


def test_a_bare_list_of_hits_is_never_strong_because_it_says_which_pass_answered_nothing():
    assert tier_for("lol", ["a hit"], []) == SIMPLE


def test_the_ladder_tries_the_cheap_tier_first_then_one_expensive_attempt():
    assert ladder(SIMPLE, important=True, simple=True) == (SIMPLE, IMPORTANT)


def test_an_important_turn_never_falls_back_to_the_cheap_tier_when_both_exist():
    """A grounded answer from the wrong model is worse than the canned line."""
    assert ladder(IMPORTANT, important=True, simple=True) == (IMPORTANT,)


def test_a_tier_with_no_key_is_simply_not_on_the_list():
    assert ladder(SIMPLE, important=False, simple=True) == (SIMPLE,)
    assert ladder(SIMPLE, important=True, simple=False) == (IMPORTANT,)
    assert ladder(IMPORTANT, important=False, simple=True) == (SIMPLE,)
    assert ladder(IMPORTANT, important=True, simple=False) == (IMPORTANT,)


def test_with_no_keys_at_all_there_is_no_ladder_and_the_canned_line_answers():
    assert ladder(SIMPLE, important=False, simple=False) == ()
    assert ladder(IMPORTANT, important=False, simple=False) == ()


def test_the_forbidden_words_are_found_on_a_word_boundary():
    assert says_a_budget_word("we hit the cap for today") == "cap"
    assert says_a_budget_word("that is my limit") == "limit"
    assert says_a_budget_word("capable people wear caps") is None
    assert says_a_budget_word("Pull up a chair, friend.") is None
    assert set(BUDGET_WORDS) >= {"budget", "cap", "quota", "limit"}


def test_a_remembered_turn_is_clipped_rather_than_stored_whole():
    assert clip("  lots   of   space ") == "lots of space"
    long = clip("z" * (TURN_CHARS + 100))
    assert len(long) == TURN_CHARS and long.endswith("…")


def test_a_window_is_keyed_on_the_place_and_the_person_together():
    assert window_key(11, 900) == "11:900"
    assert window_key(None, 900) == "0:900"


class FakeStore:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, guild_id, key):
        return self.values.get(key)


def test_a_dm_reads_the_registrys_own_default_because_it_has_no_server():
    store = FakeStore({"chat_daily_turns": 5})
    assert setting(store, 7, "chat_daily_turns", 200) == 5
    assert setting(store, None, "chat_daily_turns", 200) == 200
    assert setting(None, 7, "chat_daily_turns", 200) == 200
    assert setting(FakeStore(), 7, "chat_daily_turns", 200) == 200


async def with_db(tmp_path, name="w.sqlite3"):
    db = Database(tmp_path / name)
    await db.connect()
    return db


async def test_the_window_keeps_one_place_and_one_person_in_order(tmp_path):
    db = await with_db(tmp_path)
    try:
        await remember(db, guild_id=7, channel_id=11, user_id=900, speaker=MEMBER,
                       content="first", at=NOW - timedelta(minutes=5))
        await remember(db, guild_id=7, channel_id=11, user_id=900, speaker=BOT,
                       content="second", tier=SIMPLE, at=NOW - timedelta(minutes=4))
        await remember(db, guild_id=7, channel_id=11, user_id=901, speaker=MEMBER,
                       content="somebody else", at=NOW)
        await remember(db, guild_id=7, channel_id=12, user_id=900, speaker=MEMBER,
                       content="another channel", at=NOW)

        window = await window_for(db, 11, 900, now=NOW)

        assert [row["content"] for row in window] == ["first", "second"]
        assert as_messages(window) == [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "second"},
        ]
    finally:
        await db.close()


async def test_a_turn_older_than_the_window_is_not_in_the_conversation(tmp_path):
    db = await with_db(tmp_path)
    try:
        await remember(db, guild_id=7, channel_id=11, user_id=900, speaker=MEMBER,
                       content="ancient", at=NOW - timedelta(minutes=WINDOW_MINUTES + 1))
        await remember(db, guild_id=7, channel_id=11, user_id=900, speaker=MEMBER,
                       content="recent", at=NOW)

        assert [row["content"] for row in await window_for(db, 11, 900, now=NOW)] == ["recent"]
    finally:
        await db.close()


async def test_the_window_holds_at_most_ten_exchanges(tmp_path):
    db = await with_db(tmp_path)
    try:
        for n in range(30):
            await remember(db, guild_id=7, channel_id=11, user_id=900, speaker=MEMBER,
                           content=f"line {n}", at=NOW)

        window = await window_for(db, 11, 900, now=NOW)

        assert len(window) == 20
        assert window[-1]["content"] == "line 29"
    finally:
        await db.close()


async def test_an_empty_turn_is_not_remembered_at_all(tmp_path):
    db = await with_db(tmp_path)
    try:
        await remember(db, guild_id=7, channel_id=11, user_id=900, speaker=MEMBER, content="  ")
        assert await window_for(db, 11, 900) == []
    finally:
        await db.close()


async def test_a_window_that_cannot_be_read_is_empty_rather_than_an_exception():
    class Broken:
        @property
        def conn(self):
            raise RuntimeError("no database")

    assert await window_for(Broken(), 11, 900) == []
    await remember(Broken(), guild_id=7, channel_id=11, user_id=900, speaker=MEMBER, content="hi")


async def test_the_sweep_keeps_an_hour_not_half_of_one(tmp_path):
    db = await with_db(tmp_path)
    try:
        await remember(db, guild_id=7, channel_id=11, user_id=900, speaker=MEMBER,
                       content="forty minutes ago", at=NOW - timedelta(minutes=40))
        await remember(db, guild_id=7, channel_id=11, user_id=900, speaker=MEMBER,
                       content="two hours ago", at=NOW - timedelta(hours=2))

        assert await sweep_window(db, now=NOW) == 1

        cur = await db.conn.execute("SELECT content FROM chat_window")
        assert [row["content"] for row in await cur.fetchall()] == ["forty minutes ago"]
    finally:
        await db.close()


async def spend(db, *, turn, user_id=900, at=NOW, cost_tokens=0):
    await record(
        db,
        guild_id=7,
        user_id=user_id,
        turn=turn,
        provider=ANTHROPIC,
        model=MODEL,
        tier=IMPORTANT,
        usage=Usage(input_tokens=cost_tokens),
        at=at,
    )


async def test_two_calls_in_one_turn_spend_one_turn_not_two(tmp_path):
    """A Groq failure falling through to Haiku is one answer to one person."""
    db = await with_db(tmp_path)
    try:
        await spend(db, turn="t1")
        await spend(db, turn="t1")
        await spend(db, turn="t2")

        since = (NOW - timedelta(hours=1)).isoformat()
        assert await person_turns(db, 900, since) == 2
        assert await server_turns(db, since) == 2
    finally:
        await db.close()


async def test_a_turn_from_last_hour_no_longer_counts_against_this_one(tmp_path):
    db = await with_db(tmp_path)
    try:
        await spend(db, turn="old", at=NOW - timedelta(hours=2))
        await spend(db, turn="new")

        assert await person_turns(db, 900, (NOW - timedelta(hours=1)).isoformat()) == 1
    finally:
        await db.close()


async def test_the_three_counters_are_never_folded_into_one(tmp_path):
    db = await with_db(tmp_path)
    try:
        store = FakeStore(
            {"chat_person_hourly_turns": 2, "chat_daily_turns": 3, "chat_monthly_cap_usd": 20}
        )
        await spend(db, turn="a")
        assert (await allowance(db, store, 7, 900, now=NOW)).why == OPEN
        await spend(db, turn="b")
        mine = await allowance(db, store, 7, 900, now=NOW)
        assert mine.why == PERSON_FULL and mine.ok is False
        assert (await allowance(db, store, 7, 901, now=NOW)).why == OPEN

        await spend(db, turn="c", user_id=901)
        assert (await allowance(db, store, 7, 902, now=NOW)).why == SERVER_FULL
    finally:
        await db.close()


async def test_the_dollar_figure_closes_the_tier_ahead_of_either_turn_counter(tmp_path):
    db = await with_db(tmp_path)
    try:
        store = FakeStore(
            {"chat_person_hourly_turns": 0, "chat_daily_turns": 0, "chat_monthly_cap_usd": 1}
        )
        await spend(db, turn="a", cost_tokens=999_999)
        assert (await allowance(db, store, 7, 900, now=NOW)).why == OPEN

        await spend(db, turn="b", cost_tokens=2)
        closed = await allowance(db, store, 7, 900, now=NOW)
        assert closed.why == CAPPED
        assert closed.spent == 1_000_001
    finally:
        await db.close()


async def test_last_months_spending_does_not_close_this_month(tmp_path):
    db = await with_db(tmp_path)
    try:
        store = FakeStore({"chat_monthly_cap_usd": 1})
        await spend(db, turn="a", cost_tokens=2_000_000, at=NOW - timedelta(days=40))

        assert (await allowance(db, store, 7, 900, now=NOW)).why == OPEN
        assert await month_spend(db, month_start(NOW)) == 0
    finally:
        await db.close()


async def test_a_zero_turn_ceiling_means_no_ceiling_of_its_own(tmp_path):
    db = await with_db(tmp_path)
    try:
        store = FakeStore(
            {"chat_person_hourly_turns": 0, "chat_daily_turns": 0, "chat_monthly_cap_usd": 20}
        )
        for n in range(50):
            await spend(db, turn=f"t{n}")

        assert (await allowance(db, store, 7, 900, now=NOW)).why == OPEN
    finally:
        await db.close()


async def test_a_zero_dollar_figure_stops_the_models_altogether(tmp_path):
    """Zero money means zero calls — the one place zero is a floor, not an absence."""
    db = await with_db(tmp_path)
    try:
        store = FakeStore({"chat_monthly_cap_usd": 0})
        assert (await allowance(db, store, 7, 900, now=NOW)).why == CAPPED
    finally:
        await db.close()


async def test_the_closure_is_logged_once_by_asking_the_log_rather_than_a_flag(tmp_path):
    """A restart must not re-announce a closure that already happened this month."""
    db = await with_db(tmp_path)
    try:
        since = month_start(NOW)
        assert await capped_already_logged(db, 7, since) is False
        await db.conn.execute(
            "INSERT INTO action_log(guild_id, at, kind) VALUES (7, ?, 'chat.llm_capped')",
            (NOW.isoformat(),),
        )
        await db.conn.commit()
        assert await capped_already_logged(db, 7, since) is True
        assert await capped_already_logged(db, 8, since) is False
    finally:
        await db.close()


def test_money_reads_as_dollars_and_cents():
    assert money(0) == "$0.00"
    assert money(1_234_567) == "$1.23"
    assert money(None) == "$0.00"


def test_the_grounding_rides_the_members_own_turn():
    hits = [{"title": "Rules", "body": "Be kind."}]
    said = user_turn("<@55> what are the rules?", hits)
    assert said.startswith("what are the rules?")
    assert GROUNDING_NOTE in said
    assert "never quote, list or bullet them back" in said
    assert "Be kind." in said
    assert user_turn("<@55> hi", []) == "hi"
    staff_wrote = user_turn("<@55> rules?", hits, note="Use these quietly.")
    assert "Use these quietly." in staff_wrote and GROUNDING_NOTE not in staff_wrote


def test_the_people_a_message_named_ride_the_turn_with_the_notes():
    said = user_turn(
        "<@55> can i trust <@4001>",
        [],
        ["Pawpette — holds Aunties / Uncles; staff: yes"],
    )
    assert said.startswith("can i trust")
    assert "this is the truth about them" in said
    assert "Pawpette — holds Aunties / Uncles; staff: yes" in said


def test_a_message_that_named_nobody_carries_no_people_block():
    assert user_turn("just chatting", [], []) == "just chatting"


def test_what_the_bot_remembers_rides_the_turn_beside_the_people_note():
    said = user_turn("just chatting", [], [], "(What you remember: likes short answers)")

    assert said.startswith("just chatting")
    assert "likes short answers" in said
    assert user_turn("just chatting", [], [], "") == "just chatting"


async def test_the_reply_reads_the_profile_only_while_memory_is_on(tmp_path):
    from black_bloc.chat_llm import memory_for
    from black_bloc.chat_memory import Note, Profile, save_profile

    db = await with_db(tmp_path, "mem.sqlite3")
    try:
        await save_profile(
            db,
            900,
            7,
            Profile(
                notes=(
                    Note("likes short answers", "server", "2026-09-02"),
                    Note("prefers she/her", "dm", "2026-09-02"),
                )
            ),
        )
        off = Bot(db, FakeStore({"chat_memory_mode": "off"}), Settings())
        on = Bot(db, FakeStore({"chat_memory_mode": "on"}), Settings())
        on.settings.dev_guild_id = 7

        assert await memory_for(off, db, 7, 900, in_dm=False) == ""
        public = await memory_for(on, db, 7, 900, in_dm=False)
        private = await memory_for(on, db, None, 900, in_dm=True)

        assert "likes short answers" in public and "she/her" not in public
        assert "never claim they are online" in public
        assert "she/her" in private
        assert await memory_for(on, db, 7, 4242, in_dm=False) == ""
    finally:
        await db.close()


async def test_a_dm_with_no_server_at_all_reads_nothing_back(tmp_path):
    from black_bloc.chat_llm import memory_for

    db = await with_db(tmp_path, "nohome.sqlite3")
    try:
        bot = Bot(db, FakeStore({"chat_memory_mode": "on"}), Settings())
        bot.settings.dev_guild_id = None

        assert await memory_for(bot, db, None, 900, in_dm=True) == ""
    finally:
        await db.close()


EVERYONE = SimpleNamespace(id=7, name="@everyone")


def seen_channel(name, topic=None, *, seen=True):
    return SimpleNamespace(
        name=name,
        topic=topic,
        category=None,
        category_id=None,
        permissions_for=lambda role: SimpleNamespace(view_channel=seen),
    )


class FakeGuild:
    def __init__(self, guild_id=7, channels=()):
        self.id = guild_id
        self.default_role = EVERYONE
        self.text_channels = list(channels)


class FakeMember:
    def __init__(self, user_id=900):
        self.id = user_id


class FakeChannel:
    def __init__(self, channel_id=11):
        self.id = channel_id


class Bot:
    def __init__(self, db, store, settings):
        self.db = db
        self.store = store
        self.settings = settings
        self.guild = FakeGuild()
        self.logged: list[tuple[str, dict]] = []


class Settings:
    def __init__(self, *, important=True, simple=True):
        self.anthropic_api_key = "sk-ant-x" if important else None
        self.groq_api_key = "gsk-x" if simple else None

    @property
    def important_tier_configured(self):
        return bool(self.anthropic_api_key)

    @property
    def simple_tier_configured(self):
        return bool(self.groq_api_key)


class Answering:
    def __init__(self, provider, model, text="Pull up a chair.", raises=None):
        self.model = model
        self._provider = provider
        self._text = text
        self._raises = raises
        self.seen: list[dict] = []

    async def reply(self, *, system, messages):
        self.seen.append({"system": system, "messages": messages})
        if self._raises is not None:
            raise self._raises
        return Reply(
            text=self._text,
            provider=self._provider,
            model=self.model,
            usage=Usage(input_tokens=100, output_tokens=20),
        )


@pytest.fixture
async def wired(tmp_path, monkeypatch):
    db = Database(tmp_path / "x.sqlite3")
    await db.connect()
    store = FakeStore(
        {
            "chat_llm_mode": "on",
            "chat_personality": "cookout",
            "chat_simple_model": "llama-3.3-70b-versatile",
            "chat_monthly_cap_usd": 20,
            "chat_person_hourly_turns": 20,
            "chat_daily_turns": 200,
        }
    )
    bot = Bot(db, store, Settings())

    async def note(bot_arg, guild, kind, **kwargs):
        """Writes the row as well as remembering it: "once" is answered by the log itself."""
        bot.logged.append((kind, kwargs.get("details") or {}))
        await db.conn.execute(
            "INSERT INTO action_log(guild_id, at, kind) VALUES (?, ?, ?)",
            (guild.id, datetime.now(UTC).isoformat(), kind),
        )
        await db.conn.commit()

    monkeypatch.setattr(chat_llm, "log_action", note)
    try:
        yield bot
    finally:
        await db.close()


def wire(bot, monkeypatch, *, haiku=None, groq=None):
    monkeypatch.setattr(chat_llm, "haiku", lambda _bot: haiku)
    monkeypatch.setattr(chat_llm, "groq", lambda _bot, model: groq)


async def ask(bot, text="just chatting here"):
    return await conversational_reply(
        bot, guild=bot.guild, member=FakeMember(), channel=FakeChannel(), text=text
    )


async def test_a_simple_turn_goes_to_the_cheap_tier_and_lands_in_the_ledger(wired, monkeypatch):
    quick = Answering(GROQ, "llama-3.3-70b-versatile")
    wire(wired, monkeypatch, haiku=Answering(ANTHROPIC, MODEL), groq=quick)

    said, tier, _tone = await ask(wired)

    assert (said, tier) == ("Pull up a chair.", SIMPLE)
    assert len(quick.seen) == 1
    cur = await wired.db.conn.execute("SELECT provider, tier, outcome FROM llm_ledger")
    assert [tuple(row) for row in await cur.fetchall()] == [(GROQ, SIMPLE, "ok")]


async def test_a_groq_failure_buys_exactly_one_haiku_attempt(wired, monkeypatch):
    careful = Answering(ANTHROPIC, MODEL, text="I have got you.")
    wire(
        wired,
        monkeypatch,
        haiku=careful,
        groq=Answering(GROQ, "llama", raises=LLMError("unreachable", "groq unreachable")),
    )

    said, tier, _tone = await ask(wired)

    assert (said, tier) == ("I have got you.", IMPORTANT)
    assert len(careful.seen) == 1
    cur = await wired.db.conn.execute("SELECT tier, outcome, turn FROM llm_ledger ORDER BY id")
    rows = [tuple(row) for row in await cur.fetchall()]
    assert [(row[0], row[1]) for row in rows] == [(SIMPLE, "error"), (IMPORTANT, "ok")]
    assert rows[0][2] == rows[1][2]
    assert ("chat.llm_error", {"tier": SIMPLE, "why": "unreachable"}) in wired.logged


async def test_both_tiers_failing_leaves_the_canned_line_to_answer(wired, monkeypatch):
    wire(
        wired,
        monkeypatch,
        haiku=Answering(ANTHROPIC, MODEL, raises=LLMError("refused", "anthropic answered 400")),
        groq=Answering(GROQ, "llama", raises=LLMError("rate_limited", "groq is rate limiting")),
    )

    assert await ask(wired) == (None, None, None)
    assert tier_errors(wired) == {SIMPLE: "rate_limited", IMPORTANT: "refused"}


async def test_a_tier_that_answers_again_stops_being_called_down(wired, monkeypatch):
    tier_errors(wired)[SIMPLE] = "unreachable"
    wire(wired, monkeypatch, groq=Answering(GROQ, "llama"))

    await ask(wired)

    assert tier_errors(wired) == {}


async def test_the_models_are_never_called_while_the_mode_is_off(wired, monkeypatch):
    quick = Answering(GROQ, "llama")
    wire(wired, monkeypatch, groq=quick)
    wired.store.values["chat_llm_mode"] = "off"

    assert await ask(wired) == (None, None, None)
    assert quick.seen == []


async def test_a_missing_key_means_that_tier_is_simply_not_tried(wired, monkeypatch):
    wired.settings.groq_api_key = None
    careful = Answering(ANTHROPIC, MODEL)
    wire(wired, monkeypatch, haiku=careful, groq=None)

    said, tier, _tone = await ask(wired)

    assert tier == IMPORTANT and len(careful.seen) == 1


async def test_with_no_keys_at_all_nothing_is_called_and_nothing_is_written(wired, monkeypatch):
    wired.settings.anthropic_api_key = None
    wired.settings.groq_api_key = None
    wire(wired, monkeypatch)

    assert await ask(wired) == (None, None, None)
    cur = await wired.db.conn.execute("SELECT COUNT(*) AS n FROM llm_ledger")
    assert (await cur.fetchone())["n"] == 0


async def test_a_note_that_matches_grounds_the_turn_and_sends_it_to_the_careful_tier(
    wired, monkeypatch
):
    await add_section(wired.db, 7, "Cookout hours", "The cookout runs Friday evenings.")
    careful = Answering(ANTHROPIC, MODEL)
    wire(wired, monkeypatch, haiku=careful, groq=Answering(GROQ, "llama"))

    said, tier, _tone = await ask(wired, "<@1> cookout hours")

    assert tier == IMPORTANT
    asked = careful.seen[0]["messages"][-1]["content"]
    assert "Friday evenings" in asked
    assert GROUNDING_NOTE in asked


async def test_a_short_question_stays_on_the_cheap_tier_and_keeps_its_note(wired, monkeypatch):
    """The measured bug: any hit promoted, so Groq was never once chosen. A short factual
    question is still SIMPLE, and still carries the note, under the silent-use header."""
    await add_section(wired.db, 7, "Cookout hours", "The cookout runs Friday evenings.")
    quick = Answering(GROQ, "llama-3.3-70b-versatile")
    wire(wired, monkeypatch, haiku=Answering(ANTHROPIC, MODEL), groq=quick)

    said, tier, _tone = await ask(wired, "<@1> when is the cookout?")

    assert tier == SIMPLE
    asked = quick.seen[0]["messages"][-1]["content"]
    assert "Friday evenings" in asked and GROUNDING_NOTE in asked


def test_a_question_is_a_question_mark_or_an_opener_as_the_first_word():
    assert is_a_question("<@1> when is the cookout") is True
    assert is_a_question("What's good") is True
    assert is_a_question("What up") is True
    assert is_a_question("sup fam, cookout vibes") is False
    assert is_a_question("I wonder how the cookout went") is False
    assert is_a_question("I wonder how the cookout went?") is True


async def test_what_up_counts_as_a_question_and_still_carries_nothing(wired, monkeypatch):
    await server_notes(wired.db)
    quick = Answering(GROQ, "llama-3.3-70b-versatile")
    wire(wired, monkeypatch, haiku=Answering(ANTHROPIC, MODEL), groq=quick)

    said, tier, _tone = await ask(wired, "<@1> What up")

    assert tier == SIMPLE
    assert quick.seen[0]["messages"][-1]["content"] == "What up"


async def test_a_question_with_no_question_mark_keeps_its_note(wired, monkeypatch):
    """Discord rarely types the `?` (conductor, 2026-09-23)."""
    await add_section(wired.db, 7, "Cookout hours", "The cookout runs Friday evenings.")
    quick = Answering(GROQ, "llama-3.3-70b-versatile")
    wire(wired, monkeypatch, haiku=Answering(ANTHROPIC, MODEL), groq=quick)

    said, tier, _tone = await ask(wired, "<@1> when is the cookout")

    assert tier == SIMPLE
    asked = quick.seen[0]["messages"][-1]["content"]
    assert "Friday evenings" in asked and GROUNDING_NOTE in asked


async def test_a_mid_sentence_how_is_not_a_question_and_a_weak_hit_stays_out(
    wired, monkeypatch
):
    await add_section(wired.db, 7, "Cookout hours", "The cookout runs Friday evenings.")
    quick = Answering(GROQ, "llama-3.3-70b-versatile")
    wire(wired, monkeypatch, haiku=Answering(ANTHROPIC, MODEL), groq=quick)

    said, tier, _tone = await ask(wired, "<@1> I wonder how the cookout went")

    assert tier == SIMPLE
    assert quick.seen[0]["messages"][-1]["content"] == "I wonder how the cookout went"


async def test_small_talk_with_a_weak_accidental_hit_carries_no_notes(wired, monkeypatch):
    await add_section(wired.db, 7, "Cookout hours", "The cookout runs Friday evenings.")
    quick = Answering(GROQ, "llama-3.3-70b-versatile")
    wire(wired, monkeypatch, haiku=Answering(ANTHROPIC, MODEL), groq=quick)

    found = await chat_llm.hits_for(wired.db, 7, "<@1> sup fam, cookout vibes")
    said, tier, _tone = await ask(wired, "<@1> sup fam, cookout vibes")

    assert found.hits and found.strong is False
    assert tier == SIMPLE
    assert quick.seen[0]["messages"][-1]["content"] == "sup fam, cookout vibes"


async def server_notes(db):
    """The three notes "What up" matched live on 2026-09-23, plus the PBs channel."""
    await add_section(
        db, 7, "#upcoming-events", "Upcoming community events and when they happen.",
        tag="channel", source="server",
    )
    await add_section(
        db, 7, "#knuck-up", "Fighting games — matches, tech and trash talk.",
        tag="channel", source="server",
    )
    await add_section(
        db, 7, "Who has the Tech Support role", "Tech Support — 1 member: Raelcun.",
        tag="role", source="server",
    )
    await add_section(
        db, 7, "#speed-and-pbs",
        "Speedrunning records and personal bests — talking about runs, times and PBs, not "
        "general chat.",
        tag="channel", source="server",
    )


async def test_what_up_is_banter_with_no_notes_and_the_short_answer_hint(wired, monkeypatch):
    """Owner 2026-09-23 15:19, of a reply that quoted three notes back: "this response was
    too much"."""
    await server_notes(wired.db)
    quick = Answering(GROQ, "llama-3.3-70b-versatile")
    wire(wired, monkeypatch, haiku=Answering(ANTHROPIC, MODEL), groq=quick)

    found = await chat_llm.hits_for(wired.db, 7, "<@1> What up")
    said, tier, _tone = await ask(wired, "<@1> What up")

    assert found.hits == () and found.terms == ()
    assert tier == SIMPLE
    assert quick.seen[0]["messages"][-1]["content"] == "What up"
    system = quick.seen[0]["system"]
    assert BANTER_STYLE in system
    assert "Raelcun" not in system and "Upcoming community events" not in system


async def test_where_to_post_pbs_finds_the_channel_and_pays_for_a_careful_grounded_answer(
    wired, monkeypatch
):
    await server_notes(wired.db)
    careful = Answering(ANTHROPIC, MODEL)
    wire(wired, monkeypatch, haiku=careful, groq=Answering(GROQ, "llama"))

    found = await chat_llm.hits_for(wired.db, 7, "<@1> where do I post my PBs")
    said, tier, _tone = await ask(wired, "<@1> where do I post my PBs")

    assert found.hits[0].title == "#speed-and-pbs" and found.strong is True
    assert tier == IMPORTANT
    asked = careful.seen[0]["messages"][-1]["content"]
    assert GROUNDING_NOTE in asked and "Speedrunning records" in asked
    assert BANTER_STYLE in careful.seen[0]["system"][0]["text"]


async def test_who_has_the_tech_support_role_still_finds_the_role(wired):
    await server_notes(wired.db)

    found = await chat_llm.hits_for(wired.db, 7, "<@1> who has the tech support role")

    assert found.hits[0].title == "Who has the Tech Support role"
    assert found.strong is True


async def test_the_banter_hint_and_notes_header_staff_wrote_are_the_ones_the_model_reads(
    wired, monkeypatch
):
    await server_notes(wired.db)
    wired.store.values["chat_banter_style"] = "Keep it to one line, fam."
    wired.store.values["chat_grounding_note"] = "Read these, never recite them."
    careful = Answering(ANTHROPIC, MODEL)
    wire(wired, monkeypatch, haiku=careful)
    wired.settings.groq_api_key = None

    await ask(wired, "<@1> where do I post my PBs")

    assert "Keep it to one line, fam." in careful.seen[0]["system"][0]["text"]
    assert BANTER_STYLE not in careful.seen[0]["system"][0]["text"]
    asked = careful.seen[0]["messages"][-1]["content"]
    assert "Read these, never recite them." in asked and GROUNDING_NOTE not in asked


async def test_black_blocs_own_mention_is_not_one_of_the_words_the_notes_are_searched_for(
    wired, monkeypatch
):
    """The id in `<@1>` tokenised as a word that matches no note, so the every-token pass
    could never answer a real @-mention and every call fell to the loose one."""
    await add_section(wired.db, 7, "Cookout hours", "The cookout runs Friday evenings.")
    found = await chat_llm.hits_for(wired.db, 7, "<@1234567890> cookout hours")

    assert "1234567890" not in found.terms
    assert found.strong is True


async def test_the_window_is_carried_into_the_next_turn_and_nothing_older_is(wired, monkeypatch):
    quick = Answering(GROQ, "llama", text="First answer.")
    wire(wired, monkeypatch, groq=quick)

    await ask(wired, "first question")
    await ask(wired, "second question")

    messages = quick.seen[-1]["messages"]
    assert [row["content"] for row in messages] == [
        "first question",
        "First answer.",
        "second question",
    ]


async def test_the_persona_stack_rides_the_system_and_never_the_member_turn(wired, monkeypatch):
    careful = Answering(ANTHROPIC, MODEL)
    wire(wired, monkeypatch, haiku=careful)
    wired.settings.groq_api_key = None

    await ask(wired, "is a mod around")

    system = careful.seen[0]["system"]
    assert system[0]["cache_control"] == {"type": "ephemeral"}
    assert "You are Black Bloc" in system[0]["text"]


async def test_the_closure_is_announced_once_and_the_models_are_not_called(wired, monkeypatch):
    wired.store.values["chat_monthly_cap_usd"] = 0
    quick = Answering(GROQ, "llama")
    wire(wired, monkeypatch, groq=quick)

    assert await ask(wired) == (None, None, None)
    await ask(wired)

    assert quick.seen == []
    assert [kind for kind, _ in wired.logged] == ["chat.llm_capped"]


async def test_a_long_answer_is_clipped_to_something_discord_will_take(wired, monkeypatch):
    wire(wired, monkeypatch, groq=Answering(GROQ, "llama", text="z" * 5000))

    said, _, _ = await ask(wired)

    assert len(said) <= 1900


async def test_the_careful_tier_is_given_the_channel_list_after_the_cached_core(
    wired, monkeypatch
):
    wired.guild = FakeGuild(
        channels=[
            seen_channel("general", "Chat about anything."),
            seen_channel("staff-room", "Staff only.", seen=False),
        ]
    )
    careful = Answering(ANTHROPIC, MODEL)
    wire(wired, monkeypatch, haiku=careful)
    wired.settings.groq_api_key = None

    await ask(wired, "where do I ask about the cookout, exactly, and who do I ask?")

    system = careful.seen[0]["system"]
    assert system[0]["cache_control"] == {"type": "ephemeral"}
    assert "#general — Chat about anything." in system[1]["text"]
    assert "staff-room" not in system[1]["text"]
    assert "cache_control" not in system[1]


async def test_the_quick_tier_gets_the_same_list_as_one_string(wired, monkeypatch):
    wired.guild = FakeGuild(channels=[seen_channel("general", "Chat here.")])
    quick = Answering(GROQ, "llama")
    wire(wired, monkeypatch, groq=quick)

    await ask(wired)

    assert "#general — Chat here." in quick.seen[0]["system"]


async def test_a_stored_channel_note_reaches_the_model_in_place_of_the_topic(wired, monkeypatch):
    """The owner's report: #speed-and-pbs was taken for the general chat."""
    speed = seen_channel("speed-and-pbs", "general chat")
    speed.id = 1076003845232148580
    wired.guild = FakeGuild(channels=[speed])
    await set_channel_note(wired.db, 7, speed.id, "Speedrunning records and PBs.")
    quick = Answering(GROQ, "llama")
    wire(wired, monkeypatch, groq=quick)

    await ask(wired)

    assert "#speed-and-pbs — Speedrunning records and PBs." in quick.seen[0]["system"]
    assert "general chat" not in quick.seen[0]["system"]


async def test_a_channel_the_server_does_not_have_never_reaches_the_member(wired, monkeypatch):
    """The owner's live failure: the bot sent somebody to an invented #black-support-hub."""
    wired.guild = FakeGuild(channels=[seen_channel("general", "Chat.")])
    wire(wired, monkeypatch, groq=Answering(GROQ, "llama", text="Head to #black-support-hub."))

    said, _, _ = await ask(wired)

    assert "black-support-hub" not in said
    assert said == "Head."
    assert wired.logged[0][0] == "chat.reply_reference_fixed"
    assert wired.logged[0][1] == {"channels": ["black-support-hub"], "roles": [], "fixed": 1}


async def test_the_home_channel_is_where_an_invented_one_is_swapped_for(wired, monkeypatch):
    wired.guild = FakeGuild(channels=[seen_channel("general", "Chat.")])
    wired.store.values["chat_home_channel_id"] = 800
    wire(wired, monkeypatch, groq=Answering(GROQ, "llama", text="Ask in #nowhere about it."))

    said, _, _ = await ask(wired)

    assert said == "Ask in <#800> about it."


async def test_a_role_the_server_does_not_have_is_taken_out_and_counted(wired, monkeypatch):
    wired.guild = FakeGuild(channels=[seen_channel("general", "Chat.")])
    wired.guild.roles = [SimpleNamespace(name="Leads")]
    wire(wired, monkeypatch, groq=Answering(GROQ, "llama", text="Ping @Admin about it."))

    said, _, _ = await ask(wired)

    assert said == "Ping about it."
    assert wired.logged[0][1]["roles"] == ["Admin"]


async def test_a_reply_that_names_only_real_things_is_not_logged_as_fixed(wired, monkeypatch):
    wired.guild = FakeGuild(channels=[seen_channel("general", "Chat.")])
    wire(wired, monkeypatch, groq=Answering(GROQ, "llama", text="Ask in #general."))

    said, _, _ = await ask(wired)

    assert said == "Ask in #general."
    assert wired.logged == []


async def test_the_window_remembers_the_fixed_answer_not_the_invented_one(wired, monkeypatch):
    wired.guild = FakeGuild(channels=[seen_channel("general", "Chat.")])
    wire(wired, monkeypatch, groq=Answering(GROQ, "llama", text="Ask in #nowhere."))

    await ask(wired)

    cur = await wired.db.conn.execute(
        "SELECT content FROM chat_window WHERE speaker = ?", (BOT,)
    )
    assert [row["content"] for row in await cur.fetchall()] == ["Ask."]


async def test_a_guild_with_nothing_public_is_told_to_name_no_channel(wired, monkeypatch):
    quick = Answering(GROQ, "llama")
    wire(wired, monkeypatch, groq=quick)

    await ask(wired)

    assert "name no channel at all" in quick.seen[0]["system"]


def test_the_channel_list_the_model_gets_carries_the_staff_note():
    def permissions_for(role):
        return SimpleNamespace(view_channel=True)

    everyone = SimpleNamespace(id=7, name="@everyone")
    speed = SimpleNamespace(
        id=55,
        name="speed-and-pbs",
        topic="general chat",
        category=None,
        category_id=None,
        permissions_for=permissions_for,
    )
    guild = SimpleNamespace(id=7, default_role=everyone, text_channels=[speed])
    bot = SimpleNamespace(store=SimpleNamespace(get=lambda guild_id, key: None))
    said = chat_llm.channels_block(bot, guild, {55: "Speedrunning records and PBs."})
    assert "#speed-and-pbs — Speedrunning records and PBs." in said
    assert "general chat" not in said
    assert "#speed-and-pbs — general chat" in chat_llm.channels_block(bot, guild)


async def tones_ready(bot):
    from black_bloc.personas import sync_tropes

    await sync_tropes(bot.db)


async def ask_in(bot, channel_id, text="just chatting here", user_id=900):
    return await conversational_reply(
        bot,
        guild=bot.guild,
        member=FakeMember(user_id),
        channel=FakeChannel(channel_id),
        text=text,
    )


async def ledger_tropes(db):
    cur = await db.conn.execute("SELECT trope FROM llm_ledger ORDER BY id")
    return [row["trope"] for row in await cur.fetchall()]


async def test_the_cookout_setting_sends_no_tone_and_the_ledger_says_cookout(wired, monkeypatch):
    from black_bloc.personas import COOKOUT_VOICE, TONE_HEADING

    await tones_ready(wired)
    quick = Answering(GROQ, "llama")
    wire(wired, monkeypatch, groq=quick)

    said, _, tone = await ask(wired)

    assert said and tone == "cookout"
    assert COOKOUT_VOICE in quick.seen[0]["system"]
    assert TONE_HEADING not in quick.seen[0]["system"]
    assert await ledger_tropes(wired.db) == ["cookout"]


async def test_a_pinned_member_hears_their_pin_over_the_pool_and_a_named_mood(wired, monkeypatch):
    from black_bloc.chat_voice import pin
    from black_bloc.personas import BY_NAME

    await tones_ready(wired)
    await pin(wired.db, 7, 900, "scholar", by=1)
    for mode in ("pool", "warm"):
        wired.store.values["chat_personality"] = mode
        quick = Answering(GROQ, "llama")
        wire(wired, monkeypatch, groq=quick)
        _, _, tone = await ask(wired)
        assert tone == "scholar"
        assert BY_NAME["scholar"].voice in quick.seen[0]["system"]


async def test_a_named_mood_is_what_an_unpinned_member_hears(wired, monkeypatch):
    await tones_ready(wired)
    wired.store.values["chat_personality"] = "deadpan"
    wire(wired, monkeypatch, groq=Answering(GROQ, "llama"))

    _, _, tone = await ask(wired)

    assert tone == "deadpan"
    assert await ledger_tropes(wired.db) == ["deadpan"]


async def test_the_pool_gives_one_member_the_same_tone_in_two_channels(wired, monkeypatch):
    await tones_ready(wired)
    wired.store.values["chat_personality"] = "pool"
    wire(wired, monkeypatch, groq=Answering(GROQ, "llama"))

    _, _, first = await ask_in(wired, 11)
    _, _, second = await ask_in(wired, 12)

    assert first == second and first != "cookout"
    cur = await wired.db.conn.execute("SELECT trope, turns, since FROM chat_voice")
    stored = [tuple(row) for row in await cur.fetchall()]
    assert len(stored) == 1 and stored[0][0] == first and stored[0][1] == 1


async def test_the_roll_starts_again_only_when_the_members_window_is_empty(wired, monkeypatch):
    await tones_ready(wired)
    wired.store.values["chat_personality"] = "pool"
    wire(wired, monkeypatch, groq=Answering(GROQ, "llama"))

    await ask_in(wired, 11)
    cur = await wired.db.conn.execute("SELECT since FROM chat_voice")
    opened = (await cur.fetchone())["since"]
    await ask_in(wired, 12)
    cur = await wired.db.conn.execute("SELECT since FROM chat_voice")
    assert (await cur.fetchone())["since"] == opened

    old = (datetime.now(UTC) - timedelta(minutes=WINDOW_MINUTES + 5)).isoformat()
    await wired.db.conn.execute("UPDATE chat_window SET at = ?", (old,))
    await wired.db.conn.commit()
    await ask_in(wired, 11)
    cur = await wired.db.conn.execute("SELECT since, turns FROM chat_voice")
    row = await cur.fetchone()
    assert row["since"] != opened and row["turns"] == 0


async def test_the_ledger_carries_the_tone_on_an_error_row_too(wired, monkeypatch):
    await tones_ready(wired)
    wired.store.values["chat_personality"] = "noir"
    wire(
        wired,
        monkeypatch,
        haiku=Answering(ANTHROPIC, MODEL),
        groq=Answering(GROQ, "llama", raises=LLMError("unreachable", "groq unreachable")),
    )

    await ask(wired)

    assert await ledger_tropes(wired.db) == ["noir", "noir"]


async def test_the_sheet_and_the_clause_staff_wrote_are_the_ones_the_model_reads(
    wired, monkeypatch
):
    await tones_ready(wired)
    wired.store.values["chat_personality"] = "noir"
    wired.store.values["chat_cookout_voice"] = "## How you sound\nSay 'bet' a lot."
    wired.store.values["chat_tone_clause"] = "Stay the cookout uncle."
    careful = Answering(ANTHROPIC, MODEL)
    wire(wired, monkeypatch, haiku=careful)
    wired.settings.groq_api_key = None

    await ask(wired)

    blocks = careful.seen[0]["system"]
    assert "Say 'bet' a lot." in blocks[0]["text"]
    assert "Stay the cookout uncle." in blocks[-1]["text"]


async def test_a_dm_keeps_the_per_conversation_roll_and_writes_no_member_row(wired, monkeypatch):
    from black_bloc.chat_voice import voice_row

    await tones_ready(wired)
    wire(wired, monkeypatch, groq=Answering(GROQ, "llama"))
    tone = await chat_llm.mood_for(wired, wired.db, None, 11, 900, [], datetime.now(UTC))
    assert tone is None
    assert await voice_row(wired.db, 7, 900) is None
