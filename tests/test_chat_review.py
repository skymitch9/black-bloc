import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from black_bloc import chat_review as review
from black_bloc.chat import create_intent, lines_for, list_intents, named_intent, read_triggers
from black_bloc.chat import seed_defaults as seed_chat
from black_bloc.chat_llm import CLIENTS_ATTR
from black_bloc.chat_memory import set_override
from black_bloc.config import load_settings
from black_bloc.knowledge import add_section, list_sections
from black_bloc.llm import GROQ, IMPORTANT, SIMPLE, LLMError, Reply, Usage, record
from black_bloc.settings_store import SettingsStore

GUILD = 7
CHANNEL = 111
LOG_CHANNEL = 222
MEMBER = 900
OTHER = 901
BOT_ID = 5
NOW = datetime(2026, 9, 23, 18, 0, tzinfo=UTC)

PHRASE_ANSWER = json.dumps(
    {
        "kind": "phrase",
        "intent": "cookout_hours",
        "phrase": "when does the grill start",
        "line": None,
        "why": "they meant the cookout hours",
    }
)


class FakeChannel:
    def __init__(self, channel_id):
        self.id = channel_id
        self.sent = []

    async def send(self, text, **kwargs):
        self.sent.append(text)


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black in a Flash!"
        self.channels = {LOG_CHANNEL: FakeChannel(LOG_CHANNEL)}

    def get_channel(self, channel_id):
        return self.channels.get(int(channel_id))


class FakeGroq:
    model = "openai/gpt-oss-120b"

    def __init__(self, text=PHRASE_ANSWER, raises=None):
        self.text = text
        self.raises = raises
        self.calls = []

    async def reply(self, *, system, messages, json_only=False):
        self.calls.append({"system": system, "messages": messages, "json_only": json_only})
        if self.raises is not None:
            raise self.raises
        return Reply(text=self.text, provider=GROQ, model=self.model, usage=Usage(input_tokens=300))


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guild = guild
        self.guilds = [guild]
        self.user = SimpleNamespace(id=BOT_ID)

    def get_guild(self, guild_id):
        return self.guild if int(guild_id) == self.guild.id else None


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(
        _env_file=None,
        test_mode=False,
        dev_guild_id=GUILD,
        groq_api_key="test-key",
    )
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOG_CHANNEL)
    await store.set(GUILD, "default_timezone", "UTC")
    await seed_chat(db, GUILD)
    await create_intent(db, GUILD, "cookout_hours", ["cookout time"])
    made = FakeBot(db, store, settings, FakeGuild())
    made.scheduled = []
    monkeypatch.setattr(
        review, "schedule_tag", lambda _bot, item_id: made.scheduled.append(item_id)
    )
    return made


def with_client(bot, client):
    setattr(bot, CLIENTS_ATTR, {review.REVIEW_TIER: client})
    return client


def message(text, *, message_id=1, user_id=MEMBER, channel_id=CHANNEL):
    return SimpleNamespace(
        id=message_id,
        content=text,
        guild=SimpleNamespace(id=GUILD),
        channel=SimpleNamespace(id=channel_id),
        author=SimpleNamespace(id=user_id),
    )


def said(text="Try the pinned post.", tier=SIMPLE, intent="unknown"):
    return SimpleNamespace(text=text, tier=tier, trope="cookout", intent=intent)


async def items(db):
    cur = await db.conn.execute("SELECT * FROM chat_review ORDER BY id")
    return list(await cur.fetchall())


async def kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def answered_once(bot, *, tier=SIMPLE, hits=None, text="where is the cookout thing?"):
    if hits is not None:
        review.note_grounding(bot, CHANNEL, MEMBER, hits)
    return await review.answered(
        bot, message(text), SimpleNamespace(id=50), said(tier=tier), now=NOW
    )


# --- detection ---------------------------------------------------------------------------------


async def test_an_important_answer_with_no_note_behind_it_is_queued(bot):
    made = await answered_once(bot, tier=IMPORTANT, hits=())
    rows = await items(bot.db)
    assert made == rows[0]["id"]
    assert rows[0]["reason"] == review.UNGROUNDED
    assert rows[0]["asked"] == "where is the cookout thing?"
    assert rows[0]["answered"] == "Try the pinned post."
    assert rows[0]["status"] == review.OPEN and rows[0]["reply_id"] == 50
    assert "chat.review_opened" in await kinds(bot.db)
    assert bot.scheduled == [made]


async def test_a_grounded_or_a_quick_answer_is_not_queued(bot):
    assert await answered_once(bot, tier=IMPORTANT, hits=("a note",)) is None
    assert await answered_once(bot, tier=SIMPLE, hits=()) is None
    assert await answered_once(bot, tier=IMPORTANT) is None
    assert await items(bot.db) == []


async def test_asking_again_inside_the_window_queues_the_last_answer(bot):
    await answered_once(bot)
    made = await review.heard(
        bot, message("no but where is it", message_id=2), now=NOW + timedelta(seconds=30)
    )
    rows = await items(bot.db)
    assert made is not None and rows[0]["reason"] == review.REASK


async def test_a_thanks_or_a_late_follow_up_is_not_asking_again(bot):
    await answered_once(bot)
    assert await review.heard(bot, message("thanks!! ok", message_id=2), now=NOW) is None
    await answered_once(bot)
    late = NOW + timedelta(seconds=91)
    assert await review.heard(bot, message("another thing", message_id=3), now=late) is None
    assert await items(bot.db) == []


async def test_the_answer_itself_is_never_its_own_follow_up(bot):
    await answered_once(bot)
    assert await review.heard(bot, message("where is the cookout thing?"), now=NOW) is None


async def test_zero_seconds_turns_asking_again_off_but_not_the_not_it_phrases(bot):
    await bot.store.set(GUILD, "chat_review_reask_seconds", 0)
    await answered_once(bot)
    assert await review.heard(bot, message("where though", message_id=2), now=NOW) is None
    await answered_once(bot)
    made = await review.heard(
        bot, message("thats not what I meant", message_id=3), now=NOW + timedelta(seconds=10)
    )
    assert made is not None and (await items(bot.db))[0]["reason"] == review.NOT_IT


async def test_a_not_it_phrase_is_its_own_reason(bot):
    await answered_once(bot)
    await review.heard(bot, message("No I meant the grill", message_id=2), now=NOW)
    assert (await items(bot.db))[0]["reason"] == review.NOT_IT


async def test_the_not_it_phrases_are_a_setting(bot):
    await bot.store.set(GUILD, "chat_review_not_it_phrases", "try again bot")
    await bot.store.set(GUILD, "chat_review_reask_seconds", 0)
    await answered_once(bot)
    await review.heard(bot, message("wrong answer", message_id=2), now=NOW)
    await answered_once(bot)
    await review.heard(bot, message("try again bot please", message_id=3), now=NOW)
    assert [row["reason"] for row in await items(bot.db)] == [review.NOT_IT]


async def test_a_thumbs_down_from_anybody_but_the_bot_queues_the_answer(bot):
    await answered_once(bot)
    ours = SimpleNamespace(guild_id=GUILD, user_id=BOT_ID, message_id=50, emoji="\U0001f44e")
    assert await review.reacted(bot, ours) is None
    other = SimpleNamespace(guild_id=GUILD, user_id=OTHER, message_id=50, emoji="\U0001f44d")
    assert await review.reacted(bot, other) is None
    theirs = SimpleNamespace(guild_id=GUILD, user_id=OTHER, message_id=50, emoji="\U0001f44e")
    assert await review.reacted(bot, theirs) is not None
    assert await review.reacted(bot, theirs) is None
    rows = await items(bot.db)
    assert [row["reason"] for row in rows] == [review.DOWNVOTE]


async def test_the_downvote_emoji_is_a_setting_and_blank_turns_it_off(bot):
    await answered_once(bot)
    await bot.store.set(GUILD, "chat_review_downvote_emoji", "")
    down = SimpleNamespace(guild_id=GUILD, user_id=OTHER, message_id=50, emoji="\U0001f44e")
    assert await review.reacted(bot, down) is None


async def test_somebody_who_opted_out_of_memory_leaves_no_review_row(bot):
    await set_override(bot.db, MEMBER, GUILD)
    assert await answered_once(bot, tier=IMPORTANT, hits=()) is None
    await review.heard(bot, message("not what i meant", message_id=2), now=NOW)
    assert await items(bot.db) == []


async def test_review_mode_off_queues_nothing(bot):
    await bot.store.set(GUILD, "chat_review_mode", "off")
    assert await answered_once(bot, tier=IMPORTANT, hits=()) is None
    assert await items(bot.db) == []


async def test_what_is_kept_is_the_two_messages_clipped_to_a_thousand(bot):
    review.note_grounding(bot, CHANNEL, MEMBER, ())
    await review.answered(
        bot,
        message("x" * 1500),
        SimpleNamespace(id=51),
        said(text="y" * 1500, tier=IMPORTANT),
        now=NOW,
    )
    row = (await items(bot.db))[0]
    assert len(row["asked"]) == 1000 and len(row["answered"]) == 1000


# --- tagging -----------------------------------------------------------------------------------


async def test_tagging_names_an_existing_intent_and_records_the_call(bot):
    client = with_client(bot, FakeGroq())
    made = await answered_once(bot, tier=IMPORTANT, hits=())
    assert await review.tag_one(bot, made) == review.PHRASE
    row = (await items(bot.db))[0]
    assert row["suggested_kind"] == "phrase"
    assert row["suggested_intent"] == "cookout_hours"
    assert row["suggested_intent_id"] == (await named_intent(bot.db, GUILD, "cookout_hours"))["id"]
    assert row["suggested_phrase"] == "when does the grill start"
    assert row["tagged_at"] is not None
    assert client.calls[0]["json_only"] is True
    assert "cookout_hours: cookout time" in client.calls[0]["messages"][0]["content"]
    cur = await bot.db.conn.execute("SELECT tier, outcome, user_id FROM llm_ledger")
    assert [tuple(row) for row in await cur.fetchall()] == [("review", "ok", None)]
    assert "chat.review_tagged" in await kinds(bot.db)
    assert await review.tag_one(bot, made) is None
    assert len(client.calls) == 1


@pytest.mark.parametrize(
    "text",
    [
        "not json at all",
        "[1, 2]",
        json.dumps({"kind": "banana"}),
        json.dumps({"kind": "phrase", "intent": "no_such_intent", "phrase": "hi there"}),
        json.dumps({"kind": "phrase", "intent": "cookout_hours", "phrase": None}),
        json.dumps({"kind": "knowledge", "line": None}),
        json.dumps({"kind": "knowledge", "line": 42}),
        json.dumps({"kind": "knowledge", "line": "x" * 301}),
    ],
)
async def test_an_answer_out_of_shape_is_none_and_nothing_else(bot, text):
    with_client(bot, FakeGroq(text=text))
    made = await answered_once(bot, tier=IMPORTANT, hits=())
    assert await review.tag_one(bot, made) == review.NONE
    row = (await items(bot.db))[0]
    assert row["suggested_kind"] == "none"
    assert row["suggested_why"] == review.BAD_SHAPE


def test_the_parser_reads_the_three_teaching_shapes():
    intents = [{"name": "cookout_hours", "id": 1}]
    fenced = (
        "```json\n"
        + json.dumps(
            {"kind": "knowledge", "line": "The grill starts at six.", "section": "Cookout"}
        )
        + "\n```"
    )
    found = review.parse_tag(fenced, intents)
    assert (found.kind, found.line, found.section) == (
        "knowledge",
        "The grill starts at six.",
        "Cookout",
    )
    made = review.parse_tag(
        json.dumps({"kind": "intent", "intent": "Grill Times!", "phrase": "Grill, times?"}),
        intents,
    )
    assert (made.kind, made.intent, made.phrase) == ("intent", "grill_times", "grill times")
    moved = review.parse_tag(
        json.dumps({"kind": "intent", "intent": "COOKOUT_HOURS", "phrase": "grill time"}),
        intents,
    )
    assert (moved.kind, moved.intent) == ("phrase", "cookout_hours")
    assert review.parse_tag(json.dumps({"kind": "none", "why": "a joke"}), intents).why == "a joke"


async def test_a_failed_call_leaves_the_item_untagged_and_logged_in_the_ledger(bot):
    with_client(bot, FakeGroq(raises=LLMError("unreachable", "down")))
    made = await answered_once(bot, tier=IMPORTANT, hits=())
    assert await review.tag_one(bot, made) is None
    assert (await items(bot.db))[0]["tagged_at"] is None
    cur = await bot.db.conn.execute("SELECT tier, outcome FROM llm_ledger")
    assert [tuple(row) for row in await cur.fetchall()] == [("review", "error")]


async def test_the_monthly_cap_holds_tagging_back_and_says_so(bot):
    client = with_client(bot, FakeGroq())
    await bot.store.set(GUILD, "chat_monthly_cap_usd", 1)
    await record(
        bot.db,
        guild_id=GUILD,
        user_id=MEMBER,
        turn="t",
        provider="anthropic",
        model="claude-haiku-4-5",
        tier=IMPORTANT,
        usage=Usage(input_tokens=1_000_000),
    )
    made = await answered_once(bot, tier=IMPORTANT, hits=())
    assert await review.why_untagged(bot, GUILD) == review.UNTAGGED_CAPPED
    assert await review.tag_one(bot, made) is None
    assert await review.tag_waiting(bot) == 0
    assert client.calls == []
    assert (await review.counts(bot.db, GUILD))["untagged"] == 1


async def test_no_cheap_model_key_means_untagged(bot):
    bot.settings = bot.settings.model_copy(update={"groq_api_key": None})
    assert await review.why_untagged(bot, GUILD) == review.UNTAGGED_NO_KEY


async def test_the_batch_tags_what_the_moment_of_opening_missed(bot):
    client = with_client(bot, FakeGroq())
    await answered_once(bot, tier=IMPORTANT, hits=())
    assert await review.tag_waiting(bot) == 1
    assert len(client.calls) == 1


# --- teaching ----------------------------------------------------------------------------------


async def test_a_phrase_joins_the_intent_it_names(bot):
    taught = await review.teach(
        bot, GUILD, review.Suggestion("phrase", intent="cookout_hours", phrase="grill time"), 1
    )
    row = await named_intent(bot.db, GUILD, "cookout_hours")
    assert read_triggers(row["triggers"]) == ("cookout time", "grill time")
    assert taught.intent == "cookout_hours"


async def test_a_new_intent_gets_the_phrase_and_a_switched_off_placeholder(bot):
    taught = await review.teach(
        bot, GUILD, review.Suggestion("intent", intent="grill_times", phrase="grill hours"), 1
    )
    row = await named_intent(bot.db, GUILD, "grill_times")
    lines = await lines_for(bot.db, row["id"])
    assert taught.made and read_triggers(row["triggers"]) == ("grill hours",)
    assert len(lines) == 1 and not lines[0]["enabled"]
    assert lines[0]["text"].startswith("Write what Black Bloc should say")


async def test_a_new_intent_that_already_exists_takes_the_phrase_instead(bot):
    taught = await review.teach(
        bot, GUILD, review.Suggestion("intent", intent="cookout_hours", phrase="bbq time"), 1
    )
    assert not taught.made and taught.kind == "phrase"
    assert (
        len([one for one in await list_intents(bot.db, GUILD) if one["name"] == "cookout_hours"])
        == 1
    )


async def test_a_fact_goes_to_the_named_note_or_the_from_review_note(bot):
    await add_section(bot.db, GUILD, "Cookout", "It is on Saturdays.")
    first = await review.teach(
        bot,
        GUILD,
        review.Suggestion("knowledge", line="The grill starts at six.", section="cookout"),
        1,
    )
    second = await review.teach(
        bot, GUILD, review.Suggestion("knowledge", line="Bring a chair."), 1
    )
    bodies = {row["title"]: row["body"] for row in await list_sections(bot.db, GUILD)}
    assert first.section == "Cookout"
    assert bodies["Cookout"] == "It is on Saturdays.\nThe grill starts at six."
    assert second.section == "From review" and bodies["From review"] == "Bring a chair."


async def test_a_fact_never_lands_on_a_note_black_bloc_writes_for_itself(bot):
    await add_section(bot.db, GUILD, "Channels", "the list", source="server")
    taught = await review.teach(
        bot, GUILD, review.Suggestion("knowledge", line="x marks it", section="Channels"), 1
    )
    assert taught.section == "From review"


@pytest.mark.parametrize(
    ("found", "key"),
    [
        (review.Suggestion("none"), "chat_review_bad_kind"),
        (review.Suggestion("phrase", intent="cookout_hours"), "chat_review_needs_phrase"),
        (review.Suggestion("knowledge", line="  "), "chat_review_needs_line"),
        (review.Suggestion("phrase", intent="nope", phrase="hi"), "chat_review_no_intent"),
    ],
)
async def test_what_cannot_be_taught_says_which_sentence(bot, found, key):
    with pytest.raises(review.ReviewError) as caught:
        await review.teach(bot, GUILD, found, 1)
    assert caught.value.key == key


async def test_deciding_is_once_and_only_a_dismissal_reopens(bot):
    made = await answered_once(bot, tier=IMPORTANT, hits=())
    assert await review.decide(bot.db, made, review.DISMISSED, 1)
    assert not await review.decide(bot.db, made, review.APPROVED, 2)
    assert await review.reopen(bot.db, made)
    assert await review.decide(bot.db, made, review.APPROVED, 2)
    assert not await review.reopen(bot.db, made)


# --- the digest --------------------------------------------------------------------------------


async def test_the_digest_posts_once_a_local_day_after_the_hour(bot):
    await answered_once(bot, tier=IMPORTANT, hits=())
    early = NOW.replace(hour=8)
    assert not await review.digest(bot, bot.guild, now=early)
    assert await review.digest(bot, bot.guild, now=NOW.replace(hour=9, minute=5))
    assert not await review.digest(bot, bot.guild, now=NOW.replace(hour=15))
    sent = bot.guild.channels[LOG_CHANNEL].sent
    assert len(sent) == 1
    assert sent[0].startswith(
        "**1** chat answer(s) are waiting for review — approve, change or dismiss them on the "
        "Chat page: https://"
    )
    assert sent[0].endswith("/chat.html#sect-review")
    assert (await kinds(bot.db)).count("chat.review_digest") == 1


async def test_the_digest_follows_the_servers_timezone(bot):
    await bot.store.set(GUILD, "default_timezone", "America/Phoenix")
    await answered_once(bot, tier=IMPORTANT, hits=())
    assert not await review.digest(bot, bot.guild, now=NOW.replace(hour=15))
    assert await review.digest(bot, bot.guild, now=NOW.replace(hour=16))


async def test_no_digest_when_nothing_waits_or_the_loop_is_off(bot):
    assert not await review.digest(bot, bot.guild, now=NOW)
    await answered_once(bot, tier=IMPORTANT, hits=())
    await bot.store.set(GUILD, "chat_review_mode", "off")
    assert not await review.digest(bot, bot.guild, now=NOW)
    assert bot.guild.channels[LOG_CHANNEL].sent == []


async def test_the_markdown_export_carries_each_open_item(bot):
    with_client(bot, FakeGroq())
    made = await answered_once(bot, tier=IMPORTANT, hits=())
    await review.tag_one(bot, made)
    rows = await review.list_items(bot.db, GUILD)
    text = review.markdown(bot, GUILD, rows, now=NOW)
    assert text.startswith("# Chat review queue — 1 open")
    assert f"## Item {made} — a real question found no note" in text
    assert '- asked: "where is the cookout thing?"' in text
    assert "- suggestion: add when does the grill start to cookout_hours" in text
    assert "- why: they meant the cookout hours" in text


async def test_opening_an_item_schedules_its_tagging_off_the_reply_path(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, dev_guild_id=GUILD, groq_api_key="test-key")
    store = SettingsStore(db, settings)
    await store.load()
    await create_intent(db, GUILD, "cookout_hours", ["cookout time"])
    real = FakeBot(db, store, settings, FakeGuild())
    client = with_client(real, FakeGroq())
    review.note_grounding(real, CHANNEL, MEMBER, ())
    made = await review.answered(
        real, message("grill?"), SimpleNamespace(id=60), said(tier=IMPORTANT), now=NOW
    )
    for task in list(review.tracker(real).tasks):
        await task
    assert len(client.calls) == 1
    assert (await review.get_item(db, made))["suggested_kind"] == "phrase"
