from datetime import UTC, datetime, timedelta

import pytest

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
    tier_for,
    window_for,
    window_key,
    word_count,
)
from black_bloc.llm import ANTHROPIC, IMPORTANT, MODEL, SIMPLE, Usage, record
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


RULES = [
    ("a knowledge hit means the answer must be grounded", "when is the cookout", ["a hit"], [],
     IMPORTANT),
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


def test_a_hit_wins_over_everything_else_because_grounding_is_the_point():
    assert tier_for("lol", ["a hit"], []) == IMPORTANT


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
