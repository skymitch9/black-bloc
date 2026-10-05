import json
import logging
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from black_bloc import chat_feedback as feedback
from black_bloc import tone_keys
from black_bloc.chat_feedback import Verdict, parse_verdict
from black_bloc.chat_llm import CLIENTS_ATTR
from black_bloc.chat_memory import set_override
from black_bloc.chat_voice import FEEDBACK, ROLLED, SET, heard_for, pin, set_tone, voice_row
from black_bloc.config import load_settings
from black_bloc.llm import GROQ, SIMPLE, LLMError, Reply, Usage, record
from black_bloc.personas import POOL, list_tropes, set_enabled, sync_tropes
from black_bloc.settings_store import SettingsStore

GUILD = 7
CHANNEL = 111
MEMBER = 900
NOW = datetime(2026, 10, 5, 19, 0, tzinfo=UTC)
ANSWER = "Fine, fine, cousin, since you asked nice. The cookout is Saturday at four."


def verdict(reaction, genuine, cue=None):
    return json.dumps({"reaction": reaction, "genuine": genuine, "cue": cue})


GENUINE_MEAN = (
    ("that was really rude, i just asked a question", verdict("mean", True, "really rude")),
    ("wow ok that actually hurt my feelings", verdict("mean", True, "hurt my feelings")),
    ("no need to be so harsh with me, not cool", verdict("mean", True, "so harsh with me")),
)
GENUINE_WRONG = (
    ("that's wrong, the cookout is on sunday", verdict("wrong", True, "that's wrong")),
    ("that is not true, you made that up", verdict("wrong", True, "you made that up")),
    ("incorrect — the rules say three strikes, not two", verdict("wrong", True, "incorrect")),
)
BANTER = (
    ("lol rude", verdict("mean", False, "lol rude")),
    ("you're so mean 😂", verdict("mean", False, "so mean")),
    ("wrong again grill man, you love to see it 💀", verdict("wrong", False, "wrong again")),
)
NOT_ABOUT_THE_BOT = (
    ("the ref was wrong about that call last night", verdict("none", False, None)),
    ("my boss was so rude to me today", verdict("none", False, None)),
)


class FakeGroq:
    model = "openai/gpt-oss-120b"

    def __init__(self, text=None, raises=None):
        self.text = verdict("mean", True, "rude") if text is None else text
        self.raises = raises
        self.calls = []

    async def reply(self, *, system, messages, json_only=False):
        self.calls.append({"system": system, "messages": messages, "json_only": json_only})
        if self.raises is not None:
            raise self.raises
        return Reply(text=self.text, provider=GROQ, model=self.model, usage=Usage(input_tokens=90))


class FakeGuild:
    id = GUILD
    name = "Black in a Flash!"

    def get_channel(self, channel_id):
        return None


class FakeBot:
    def __init__(self, db, store, settings):
        self.db = db
        self.store = store
        self.settings = settings
        self.guild = FakeGuild()
        self.guilds = [self.guild]
        self.user = SimpleNamespace(id=5)

    def get_guild(self, guild_id):
        return self.guild if int(guild_id) == GUILD else None

    def get_channel(self, channel_id):
        return None


async def a_bot(db, monkeypatch, **given):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=False, dev_guild_id=GUILD, **given)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "chat_personality", POOL)
    await sync_tropes(db)
    return FakeBot(db, store, settings)


@pytest.fixture
async def bot(db, monkeypatch):
    return await a_bot(db, monkeypatch, groq_api_key="test-key")


def with_client(bot, client):
    setattr(bot, CLIENTS_ATTR, {feedback.FEEDBACK_TIER: client})
    return client


def message(
    text, *, message_id=2, user_id=MEMBER, channel_id=CHANNEL, reply_to=None, mention=True
):
    """Said TO the bot unless a test says otherwise: an @-mention, or a reply to an answer."""
    return SimpleNamespace(
        id=message_id,
        content=text,
        mentions=[SimpleNamespace(id=5)] if mention else [],
        mention_everyone=False,
        guild=SimpleNamespace(id=GUILD),
        channel=SimpleNamespace(id=channel_id),
        author=SimpleNamespace(id=user_id),
        reference=SimpleNamespace(message_id=reply_to) if reply_to is not None else None,
    )


async def answered(bot, tone="tsundere", *, user_id=MEMBER, at=NOW, tier=SIMPLE, settled=9):
    """A member with a stored tone who was just answered by a model, in an open conversation."""
    await set_tone(bot.db, GUILD, user_id, tone, by=1, now=at - timedelta(days=30))
    await bot.db.conn.execute(
        "UPDATE chat_voice SET settled = ? WHERE user_id = ?", (settled, user_id)
    )
    await heard_for(
        bot.db, POOL, await list_tropes(bot.db), guild_id=GUILD, user_id=user_id, now=at,
        settle=feedback_never(),
    )
    feedback.answered(
        bot,
        message("what time is the cookout", message_id=1, user_id=user_id),
        SimpleNamespace(id=500),
        SimpleNamespace(text=ANSWER, tier=tier),
        now=at,
    )


def feedback_never():
    from black_bloc.chat_voice import Settle

    return Settle(start=0.0, halves=4, floor=0.0)


async def rows_of(db, kind_prefix="chat.voice_feedback"):
    cur = await db.conn.execute("SELECT kind, target_id, details FROM action_log ORDER BY id")
    found = []
    for row in await cur.fetchall():
        if row["kind"].startswith(kind_prefix):
            details = json.loads(row["details"] or "{}")
            details.pop("via", None)
            found.append((row["kind"], details))
    return found


async def ledger(db):
    cur = await db.conn.execute("SELECT tier, outcome, user_id FROM llm_ledger ORDER BY id")
    return [tuple(row) for row in await cur.fetchall()]


# --- the parser ------------------------------------------------------------------------------


@pytest.mark.parametrize(("said", "answer"), GENUINE_MEAN)
def test_a_genuine_mean_verdict_moves(said, answer):
    found = parse_verdict(answer)
    assert (found.reaction, found.genuine, found.moves) == ("mean", True, True)
    assert found.cue and found.shaped


@pytest.mark.parametrize(("said", "answer"), GENUINE_WRONG)
def test_a_genuine_wrong_verdict_moves(said, answer):
    found = parse_verdict(answer)
    assert (found.reaction, found.genuine, found.moves) == ("wrong", True, True)


@pytest.mark.parametrize(("said", "answer"), BANTER)
def test_banter_is_a_verdict_that_moves_nothing(said, answer):
    found = parse_verdict(answer)
    assert found.reaction in ("mean", "wrong")
    assert (found.genuine, found.moves, found.shaped) == (False, False, True)


@pytest.mark.parametrize(("said", "answer"), NOT_ABOUT_THE_BOT)
def test_a_verdict_of_none_is_nothing_at_all(said, answer):
    assert parse_verdict(answer) == Verdict()


@pytest.mark.parametrize(
    "garbage",
    [
        "",
        "the member seems upset",
        "[1, 2]",
        json.dumps({"reaction": "furious", "genuine": True}),
        json.dumps({"reaction": "mean", "genuine": "yes"}),
        json.dumps({"reaction": "mean", "genuine": 1}),
        json.dumps({"reaction": "mean"}),
        json.dumps({"reaction": None, "genuine": True}),
        json.dumps({"reaction": "wrong", "genuine": True, "cue": 7}),
        json.dumps({"genuine": True, "cue": "rude"}),
    ],
)
def test_anything_out_of_shape_moves_nothing(garbage):
    found = parse_verdict(garbage)
    assert (found.reaction, found.genuine, found.moves, found.shaped) == (
        "none", False, False, False)


def test_a_cue_is_tidied_and_clipped_and_a_none_keeps_no_cue():
    long = parse_verdict(verdict("mean", True, "  so   rude " + "x" * 200))
    assert long.cue.startswith("so rude x") and len(long.cue) == feedback.CUE_CHARS
    assert parse_verdict(verdict("none", True, "rude")) == Verdict()
    assert parse_verdict(verdict(" MEAN ", True, None)) == Verdict("mean", True, "")


def test_the_cue_list_lets_every_example_through_and_holds_back_plain_talk(bot):
    for said, _ in (*GENUINE_MEAN, *GENUINE_WRONG, *BANTER, *NOT_ABOUT_THE_BOT):
        assert feedback.cue_in(bot, GUILD, said), said
    for said in ("thanks fam", "what time is it then", "ok bet", "who is bringing the ribs"):
        assert not feedback.cue_in(bot, GUILD, said), said


# --- the move --------------------------------------------------------------------------------


@pytest.mark.parametrize(("said", "answer"), GENUINE_MEAN)
async def test_a_genuine_mean_moves_the_tone_one_step_gentler_and_unsettles_it(
    bot, db, said, answer
):
    client = with_client(bot, FakeGroq(answer))
    await answered(bot, "tsundere")
    at = NOW + timedelta(minutes=1)

    moved = await feedback.heard(bot, message(said), now=at)

    kept = await voice_row(db, GUILD, MEMBER)
    assert moved == "mischievous"
    assert (kept["tone"], kept["how"], kept["moved_from"], kept["moved_why"]) == (
        "mischievous", FEEDBACK, "tsundere", "mean")
    assert (kept["settled"], kept["heard"], kept["moved_at"]) == (5, 0, at.isoformat())
    assert (kept["avoid"], kept["avoid_left"]) == ("tsundere", 8)
    assert len(client.calls) == 1 and client.calls[0]["json_only"] is True
    asked = client.calls[0]["messages"][0]["content"]
    assert ANSWER in asked and said in asked
    found = await rows_of(db)
    assert found == [
        (
            "chat.voice_feedback",
            {
                "member": str(MEMBER),
                "why": "mean",
                "cue": json.loads(answer)["cue"],
                "cue_kept": True,
                "message_id": "2",
                "from": "tsundere",
                "tone": "mischievous",
            },
        )
    ]
    assert await ledger(db) == [("feedback", "ok", MEMBER)]


@pytest.mark.parametrize(("said", "answer"), GENUINE_WRONG)
async def test_a_genuine_wrong_moves_the_tone_one_step_more_careful(bot, db, said, answer):
    with_client(bot, FakeGroq(answer))
    await answered(bot, "dramatic")

    moved = await feedback.heard(bot, message(said), now=NOW + timedelta(minutes=1))

    kept = await voice_row(db, GUILD, MEMBER)
    assert moved == "mischievous"
    assert (kept["tone"], kept["how"], kept["moved_why"]) == ("mischievous", FEEDBACK, "wrong")
    assert (await rows_of(db))[0][1]["why"] == "wrong"


@pytest.mark.parametrize(("said", "answer"), (*BANTER, *NOT_ABOUT_THE_BOT))
async def test_banter_and_talk_about_something_else_leave_the_tone_alone(bot, db, said, answer):
    client = with_client(bot, FakeGroq(answer))
    await answered(bot, "tsundere")

    moved = await feedback.heard(bot, message(said), now=NOW + timedelta(minutes=1))

    kept = await voice_row(db, GUILD, MEMBER)
    assert moved is None and len(client.calls) == 1
    assert (kept["tone"], kept["how"], kept["settled"]) == ("tsundere", SET, 9)
    assert await rows_of(db) == []


async def test_a_message_with_no_cue_word_is_never_handed_to_a_model(bot, db):
    client = with_client(bot, FakeGroq())
    await answered(bot, "tsundere")

    for n, said in enumerate(("thanks fam", "ok what about sunday", "bet")):
        assert await feedback.heard(
            bot, message(said, message_id=10 + n), now=NOW + timedelta(minutes=1)
        ) is None

    assert client.calls == [] and await ledger(db) == []


async def test_only_one_move_per_member_per_conversation(bot, db):
    client = with_client(bot, FakeGroq(verdict("mean", True, "rude")))
    await answered(bot, "tsundere")

    first = await feedback.heard(bot, message("that was rude"), now=NOW + timedelta(minutes=1))
    again = await feedback.heard(
        bot, message("still rude honestly", message_id=3), now=NOW + timedelta(minutes=2)
    )

    assert (first, again) == ("mischievous", None)
    assert len(client.calls) == 1
    assert (await voice_row(db, GUILD, MEMBER))["tone"] == "mischievous"
    assert len(await rows_of(db)) == 1


async def test_two_complaints_judged_at_once_still_move_the_tone_once(bot, db):
    """Both pass the checks before either verdict is back; the second finds the first's stamp."""
    import asyncio

    with_client(bot, FakeGroq(verdict("mean", True, "rude")))
    await answered(bot, "tsundere")
    at = NOW + timedelta(minutes=1)

    found = await asyncio.gather(
        feedback.heard(bot, message("that was rude"), now=at),
        feedback.heard(bot, message("so rude", message_id=3), now=at),
    )

    assert sorted(found, key=str) == [None, "mischievous"]
    assert (await voice_row(db, GUILD, MEMBER))["tone"] == "mischievous"
    assert len(await rows_of(db)) == 1


async def test_after_a_mean_move_drift_never_walks_back_to_the_tone_complained_about(bot, db):
    """mischievous neighbours tsundere on the graph; for eight conversations it is out of reach."""
    from black_bloc.chat_voice import Settle, stored_tone
    from black_bloc.personas import DRIFT_EVERY_TURNS, enabled_tropes

    with_client(bot, FakeGroq(verdict("mean", True, "rude")))
    await answered(bot, "tsundere")
    await feedback.heard(bot, message("that was rude"), now=NOW + timedelta(minutes=1))
    pool = enabled_tropes(await list_tropes(db))
    always = Settle(start=1.0, halves=4, floor=1.0)

    for conversation in range(8):
        at = NOW + timedelta(days=conversation + 1)
        await db.conn.execute(
            "UPDATE chat_voice SET tone = 'mischievous', heard = ?", (DRIFT_EVERY_TURNS - 1,)
        )
        kept = await voice_row(db, GUILD, MEMBER)
        if conversation < 8:
            assert kept["avoid"] == "tsundere"
        landed = set()
        for seed in range(60):
            found = stored_tone(pool, kept, key=f"s{seed}", fresh=True, turns=0,
                                since=at.isoformat(), now=at, settle=always)
            landed.add(found.name)
        if kept["avoid_left"] > 1:
            assert "tsundere" not in landed and landed, (conversation, landed)
        await heard_for(db, POOL, await list_tropes(db), guild_id=GUILD, user_id=MEMBER, now=at,
                        settle=feedback_never())

    kept = await voice_row(db, GUILD, MEMBER)
    assert kept["avoid_left"] == 0
    await db.conn.execute(
        "UPDATE chat_voice SET tone = 'mischievous', heard = ?", (DRIFT_EVERY_TURNS - 1,)
    )
    kept = await voice_row(db, GUILD, MEMBER)
    after = {
        stored_tone(pool, kept, key=f"s{seed}", fresh=False, turns=3, since=kept["since"],
                    now=NOW + timedelta(days=20), settle=always).name
        for seed in range(60)
    }
    assert "tsundere" in after


async def test_the_next_conversation_may_move_it_again(bot, db):
    with_client(bot, FakeGroq(verdict("mean", True, "rude")))
    await answered(bot, "tsundere")
    await feedback.heard(bot, message("that was rude"), now=NOW + timedelta(minutes=1))
    tomorrow = NOW + timedelta(days=1)
    await heard_for(
        db, POOL, await list_tropes(db), guild_id=GUILD, user_id=MEMBER, now=tomorrow,
        settle=feedback_never(),
    )
    feedback.answered(
        bot, message("hey", message_id=20), SimpleNamespace(id=501),
        SimpleNamespace(text=ANSWER, tier=SIMPLE), now=tomorrow,
    )

    moved = await feedback.heard(
        bot, message("rude again", message_id=21), now=tomorrow + timedelta(minutes=1)
    )

    assert moved == "deadpan"
    assert [one[1]["tone"] for one in await rows_of(db)] == ["mischievous", "deadpan"]


async def test_a_pinned_members_complaint_costs_no_model_call_and_one_row_a_conversation(
    bot, db
):
    client = with_client(bot, FakeGroq(verdict("mean", True, "rude")))
    await answered(bot, "tsundere")
    await pin(db, GUILD, MEMBER, "noir", by=1)

    moved = await feedback.heard(bot, message("that was rude"), now=NOW + timedelta(minutes=1))
    again = await feedback.heard(
        bot, message("so rude", message_id=3), now=NOW + timedelta(minutes=2)
    )

    kept = await voice_row(db, GUILD, MEMBER)
    assert moved is None and again is None
    assert client.calls == [] and await ledger(db) == []
    assert (kept["pinned"], kept["tone"], kept["how"], kept["settled"]) == (
        "noir", "tsundere", SET, 9)
    assert await rows_of(db) == [
        (
            "chat.voice_feedback_held",
            {"member": str(MEMBER), "why": None, "cue": None, "cue_kept": False,
             "judged": False, "message_id": "2", "tone": "noir", "held": "pinned"},
        )
    ]


async def test_a_pin_made_while_the_verdict_was_out_still_holds(bot, db):
    class Pinning(FakeGroq):
        async def reply(self, **given):
            await pin(db, GUILD, MEMBER, "noir", by=1)
            return await super().reply(**given)

    with_client(bot, Pinning(verdict("mean", True, "rude")))
    await answered(bot, "tsundere")

    moved = await feedback.heard(bot, message("that was rude"), now=NOW + timedelta(minutes=1))

    assert moved is None and (await voice_row(db, GUILD, MEMBER))["tone"] == "tsundere"
    assert (await rows_of(db))[0][1]["held"] == "pinned"


async def test_the_verdicts_count_against_the_member_who_caused_them_and_nobody_else(bot, db):
    """Three turns an hour: two already spent on answers, one verdict, then the fuse is shut."""
    client = with_client(bot, FakeGroq(verdict("mean", False, "rude")))
    await bot.store.set(GUILD, "chat_person_hourly_turns", 3)
    for turn in ("a", "b"):
        await record(db, guild_id=GUILD, user_id=MEMBER, turn=turn, provider=GROQ, model="m",
                     tier=SIMPLE, at=NOW)
    await answered(bot, "tsundere")
    await answered(bot, "noir", user_id=901)

    for n in range(6):
        await answered(bot, "tsundere", at=NOW + timedelta(seconds=n))
        await feedback.heard(
            bot, message("lol rude", message_id=10 + n), now=NOW + timedelta(seconds=30 + n)
        )
    assert len(client.calls) == 1
    assert [one for one in await ledger(db) if one[0] == "feedback"] == [
        ("feedback", "ok", MEMBER)]

    await feedback.heard(
        bot, message("lol rude", message_id=40, user_id=901), now=NOW + timedelta(seconds=50)
    )
    assert len(client.calls) == 2
    assert (await ledger(db))[-1] == ("feedback", "ok", 901)


async def test_with_no_gentler_tone_switched_on_it_stays_and_says_why(bot, db, caplog):
    with_client(bot, FakeGroq(verdict("mean", True, "rude")))
    await answered(bot, "cozy")
    await set_enabled(db, "warm", False)

    with caplog.at_level(logging.INFO, logger="black_bloc.chat_feedback"):
        moved = await feedback.heard(
            bot, message("that was rude"), now=NOW + timedelta(minutes=1)
        )

    kept = await voice_row(db, GUILD, MEMBER)
    assert moved is None and (kept["tone"], kept["how"], kept["settled"]) == ("cozy", SET, 9)
    assert (await rows_of(db))[0] == (
        "chat.voice_feedback_held",
        {"member": str(MEMBER), "why": "mean", "cue": "rude", "cue_kept": True,
         "message_id": "2", "tone": "cozy", "held": "no_step"},
    )
    assert "keeps cozy (no_step)" in caplog.text


async def test_a_step_skips_a_tone_that_is_switched_off(bot, db):
    with_client(bot, FakeGroq(verdict("mean", True, "rude")))
    await answered(bot, "tsundere")
    await set_enabled(db, "mischievous", False)

    moved = await feedback.heard(bot, message("that was rude"), now=NOW + timedelta(minutes=1))

    assert moved == "deadpan"


async def test_the_order_is_staffs_to_change(bot, db):
    with_client(bot, FakeGroq(verdict("wrong", True, "wrong")))
    await bot.store.set(GUILD, tone_keys.CAREFUL_ORDER_KEY, "shy, tsundere")
    await answered(bot, "tsundere")

    moved = await feedback.heard(bot, message("that is wrong"), now=NOW + timedelta(minutes=1))

    assert moved == "shy"


@pytest.mark.parametrize("setting", ["cookout", "deadpan"])
async def test_nothing_is_judged_while_the_server_is_not_on_the_pool(bot, db, setting):
    client = with_client(bot, FakeGroq())
    await answered(bot, "tsundere")
    await bot.store.set(GUILD, "chat_personality", setting)

    assert await feedback.heard(
        bot, message("that was rude"), now=NOW + timedelta(minutes=1)
    ) is None
    assert client.calls == [] and (await voice_row(db, GUILD, MEMBER))["tone"] == "tsundere"


async def test_switched_off_nothing_is_judged(bot, db):
    client = with_client(bot, FakeGroq())
    await bot.store.set(GUILD, tone_keys.FEEDBACK_MODE_KEY, "off")
    await answered(bot, "tsundere")

    assert await feedback.heard(
        bot, message("that was rude"), now=NOW + timedelta(minutes=1)
    ) is None
    assert client.calls == []


# --- which message counts --------------------------------------------------------------------


async def test_words_not_said_to_the_bot_never_leave_the_server(bot, db, caplog):
    """A member telling a FRIEND "nah that's wrong lol" a minute after an answer, same channel."""
    client = with_client(bot, FakeGroq())
    await answered(bot, "tsundere")

    with caplog.at_level(logging.DEBUG, logger="black_bloc.chat_feedback"):
        for n, said in enumerate(("nah that's wrong lol", "that was rude", "so mean, not cool")):
            found = await feedback.heard(
                bot, message(said, message_id=10 + n, mention=False),
                now=NOW + timedelta(minutes=1),
            )
            assert found is None

    assert client.calls == [] and await ledger(db) == []
    assert await rows_of(db, "chat.") == [] and caplog.text == ""
    kept = await voice_row(db, GUILD, MEMBER)
    assert (kept["tone"], kept["settled"], kept["fed_since"]) == ("tsundere", 9, None)


async def test_a_reply_to_the_bots_answer_is_judged_with_or_without_the_ping(bot, db):
    client = with_client(bot, FakeGroq(verdict("none", False)))
    await answered(bot, "tsundere")
    at = NOW + timedelta(minutes=12)

    await feedback.heard(
        bot, message("that was rude", message_id=5, reply_to=500, mention=False), now=at
    )
    assert len(client.calls) == 1
    await feedback.heard(
        bot, message("that was rude", message_id=6, reply_to=500, channel_id=222), now=at
    )
    assert len(client.calls) == 2 and await ledger(db) == [("feedback", "ok", MEMBER)] * 2


async def test_an_at_mention_is_judged_and_a_role_or_everyone_ping_is_not(bot, db):
    client = with_client(bot, FakeGroq(verdict("none", False)))
    await answered(bot, "tsundere")
    at = NOW + timedelta(minutes=12)

    everyone = message("that was rude", message_id=4)
    everyone.mention_everyone = True
    await feedback.heard(bot, everyone, now=at)
    assert client.calls == []

    await feedback.heard(bot, message("that was rude", message_id=5), now=at)
    assert len(client.calls) == 1


async def test_a_reply_to_the_bots_answer_to_somebody_else_is_not_judged_for_the_replier(
    bot, db
):
    """Replying pings the bot, so the mention is there — the reply is still about HER answer."""
    client = with_client(bot, FakeGroq())
    await answered(bot, "tsundere")
    await answered(bot, "noir", user_id=901)
    feedback.tracker(bot).answers[(GUILD, 901)].reply_id = 777

    found = await feedback.heard(
        bot, message("that was rude", message_id=8, reply_to=777), now=NOW + timedelta(minutes=1)
    )
    other = await feedback.heard(
        bot, message("that was rude", message_id=9, reply_to=4242),
        now=NOW + timedelta(minutes=1),
    )

    assert found is None and other is None and client.calls == []
    assert (await voice_row(db, GUILD, MEMBER))["tone"] == "tsundere"
    assert (await voice_row(db, GUILD, 901))["tone"] == "noir"


async def test_nothing_is_judged_once_the_half_hour_has_passed(bot, db):
    client = with_client(bot, FakeGroq())
    await answered(bot, "tsundere")
    late = NOW + timedelta(minutes=31)

    await feedback.heard(bot, message("that was rude", message_id=7, reply_to=500), now=late)
    await feedback.heard(bot, message("that was rude", message_id=8), now=late)

    assert client.calls == []


async def test_the_verdict_lands_before_the_answer_but_never_holds_it_for_long(
    bot, db, monkeypatch
):
    import asyncio

    release = asyncio.Event()
    seen = []

    async def slow(_bot, _message, **_):
        seen.append("judging")
        await release.wait()
        seen.append("judged")

    monkeypatch.setattr(feedback, "heard", slow)
    await feedback.before_reply(bot, message("that was rude", user_id=4242), seconds=0.01)
    assert seen == []
    await answered(bot, "tsundere")

    await feedback.before_reply(bot, message("that was rude"), seconds=0.01)

    assert seen == ["judging"]
    release.set()
    await asyncio.gather(*feedback.tracker(bot).tasks)
    assert seen == ["judging", "judged"]

    async def quick(_bot, _message, **_):
        seen.append("quick")

    monkeypatch.setattr(feedback, "heard", quick)
    await feedback.before_reply(bot, message("that was rude", message_id=3), seconds=5)
    assert seen[-1] == "quick"


async def test_at_most_two_messages_are_judged_after_one_answer(bot, db):
    client = with_client(bot, FakeGroq(verdict("mean", False, "rude")))
    await answered(bot, "tsundere")

    for n in range(5):
        await feedback.heard(
            bot, message("lol rude", message_id=10 + n), now=NOW + timedelta(seconds=10 * n + 5)
        )

    assert len(client.calls) == feedback.JUDGED_PER_ANSWER == 2


async def test_a_written_line_is_not_a_model_answer_and_the_question_itself_is_not_feedback(
    bot, db
):
    client = with_client(bot, FakeGroq())
    await answered(bot, "tsundere", tier=None)
    assert feedback.tracker(bot).answers == {}
    await feedback.heard(bot, message("that was rude"), now=NOW + timedelta(minutes=1))

    await answered(bot, "tsundere", user_id=901)
    same = message("rude", message_id=1, user_id=901)
    assert await feedback.heard(bot, same, now=NOW + timedelta(minutes=1)) is None
    stranger = message("that was rude", user_id=902)
    assert await feedback.heard(bot, stranger, now=NOW + timedelta(minutes=1)) is None
    dm = SimpleNamespace(id=9, content="rude", guild=None, author=SimpleNamespace(id=901))
    assert await feedback.heard(bot, dm, now=NOW) is None
    assert client.calls == []


async def test_a_member_with_no_stored_tone_is_not_judged(bot, db):
    client = with_client(bot, FakeGroq())
    feedback.answered(
        bot, message("hi", message_id=1), SimpleNamespace(id=500),
        SimpleNamespace(text=ANSWER, tier=SIMPLE), now=NOW,
    )

    assert await feedback.heard(
        bot, message("that was rude"), now=NOW + timedelta(minutes=1)
    ) is None
    assert client.calls == []


# --- the spend cap and the tiers ---------------------------------------------------------------


async def test_when_the_month_is_spent_nothing_is_judged_and_it_is_logged_once(bot, db, caplog):
    client = with_client(bot, FakeGroq())
    await answered(bot, "tsundere")
    cap = int(bot.store.get(GUILD, "chat_monthly_cap_usd"))
    await db.conn.execute(
        "INSERT INTO llm_ledger(at, guild_id, turn, provider, model, tier, outcome, "
        "cost_microdollars) VALUES (?, ?, 't', 'anthropic', 'm', 'important', 'ok', ?)",
        (NOW.replace(day=2).isoformat(), GUILD, cap * 1_000_000),
    )
    await db.conn.commit()

    with caplog.at_level(logging.INFO, logger="black_bloc.chat_feedback"):
        for n in range(3):
            assert await feedback.heard(
                bot, message("that was rude", message_id=10 + n),
                now=NOW + timedelta(seconds=30 + n),
            ) is None

    assert client.calls == []
    assert (await voice_row(db, GUILD, MEMBER))["tone"] == "tsundere"
    assert caplog.text.count("nothing is judged in 7 for now (capped)") == 1
    assert await rows_of(db) == []


async def test_when_the_day_is_full_nothing_is_judged(bot, db):
    client = with_client(bot, FakeGroq())
    await answered(bot, "tsundere")
    await bot.store.set(GUILD, "chat_daily_turns", 1)
    await record(db, guild_id=GUILD, user_id=1, turn="a", provider=GROQ, model="m", tier=SIMPLE,
                 at=NOW)

    assert await feedback.heard(
        bot, message("that was rude"), now=NOW + timedelta(minutes=1)
    ) is None
    assert client.calls == []


async def test_with_no_key_for_the_quick_model_nothing_is_judged_and_it_is_logged_once(
    db, monkeypatch, caplog
):
    bot = await a_bot(db, monkeypatch)
    await answered(bot, "tsundere")

    with caplog.at_level(logging.INFO, logger="black_bloc.chat_feedback"):
        for n in range(2):
            assert await feedback.heard(
                bot, message("that was rude", message_id=10 + n),
                now=NOW + timedelta(seconds=30 + n),
            ) is None

    assert caplog.text.count("(no_key)") == 1
    assert (await voice_row(db, GUILD, MEMBER))["how"] == SET


async def test_the_models_opening_again_lets_the_next_closing_be_said_again(bot, db, caplog):
    with caplog.at_level(logging.INFO, logger="black_bloc.chat_feedback"):
        feedback.said_once(bot, GUILD, "capped")
        feedback.said_once(bot, GUILD, "capped")
        feedback.said_once(bot, GUILD, None)
        feedback.said_once(bot, GUILD, "capped")
    assert caplog.text.count("(capped)") == 2


async def test_a_model_error_is_a_ledger_row_and_no_move(bot, db):
    with_client(bot, FakeGroq(raises=LLMError("timeout", "the quick model timed out")))
    await answered(bot, "tsundere")

    moved = await feedback.heard(bot, message("that was rude"), now=NOW + timedelta(minutes=1))

    assert moved is None and await ledger(db) == [("feedback", "error", MEMBER)]
    assert (await voice_row(db, GUILD, MEMBER))["tone"] == "tsundere"


async def test_an_answer_out_of_shape_moves_nothing_and_is_warned_about(bot, db, caplog):
    with_client(bot, FakeGroq("they seem upset, mean: yes"))
    await answered(bot, "tsundere")

    with caplog.at_level(logging.WARNING, logger="black_bloc.chat_feedback"):
        moved = await feedback.heard(
            bot, message("that was rude"), now=NOW + timedelta(minutes=1)
        )

    assert moved is None and "out of shape" in caplog.text
    assert (await voice_row(db, GUILD, MEMBER))["how"] == SET


async def test_a_member_who_opted_out_of_memory_is_judged_and_leaves_no_words_anywhere(bot, db):
    """Their message goes to the provider for the reply anyway; nothing of it is kept here."""
    client = with_client(bot, FakeGroq(verdict("mean", True, "really rude")))
    await answered(bot, "tsundere")
    await set_override(db, MEMBER, GUILD)

    moved = await feedback.heard(
        bot, message("that was really rude of you"), now=NOW + timedelta(minutes=1)
    )

    assert moved == "mischievous" and len(client.calls) == 1
    assert await rows_of(db) == [
        (
            "chat.voice_feedback",
            {"member": str(MEMBER), "why": "mean", "cue": None, "cue_kept": False,
             "message_id": "2", "from": "tsundere", "tone": "mischievous"},
        )
    ]
    for table in ("action_log", "chat_voice", "llm_ledger", "chat_review"):
        cur = await db.conn.execute(f"SELECT * FROM {table}")
        for row in await cur.fetchall():
            assert "really rude" not in " ".join(str(one) for one in tuple(row))


async def test_a_rolled_tone_moves_the_same_way(bot, db):
    with_client(bot, FakeGroq(verdict("mean", True, "rude")))
    await answered(bot, "noir")
    await db.conn.execute("UPDATE chat_voice SET how = ?", (ROLLED,))

    moved = await feedback.heard(bot, message("that was rude"), now=NOW + timedelta(minutes=1))

    assert moved == "flirty"


async def test_scheduling_skips_a_member_with_no_answer_and_a_failure_never_escapes(
    bot, db, monkeypatch, caplog
):
    seen = []

    async def boom(_bot, _message, **_):
        seen.append(1)
        raise RuntimeError("no")

    monkeypatch.setattr(feedback, "heard", boom)
    feedback.schedule(bot, message("that was rude", user_id=4242))
    assert feedback.tracker(bot).tasks == set()
    await answered(bot, "tsundere")
    feedback.schedule(bot, message("that was rude"))
    tasks = list(feedback.tracker(bot).tasks)
    assert len(tasks) == 1
    with caplog.at_level(logging.WARNING, logger="black_bloc.chat_feedback"):
        await tasks[0]
    assert seen == [1] and "was not weighed" in caplog.text
