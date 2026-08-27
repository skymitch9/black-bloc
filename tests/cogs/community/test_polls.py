from datetime import UTC, datetime, timedelta

import discord
import pytest
from discord import app_commands

from black_bloc import polls as pure
from black_bloc.cogs.community.polls import (
    POLL_MINUTES,
    PollDecisionButton,
    PollDenyModal,
    Polls,
    add_options,
    archive_poll,
    claim_reminder,
    create_poll,
    get_poll,
    options_of,
    poll_for_message,
    results_of,
    set_answer_ids,
    set_posted,
    votes_of,
)
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore
from black_bloc.storage.db import Database

GUILD = 7
TEST_CHANNEL = 111
OTHER_CHANNEL = 112
LOG_CHANNEL = 222
STAFF_ROLE = 555
USER = 900


def choice(value):
    return app_commands.Choice(name=value, value=value)


class _Response:
    def __init__(self, status):
        self.status = status
        self.reason = "refused"


def refused():
    return discord.HTTPException(_Response(403), "no")


class FakeRole:
    def __init__(self, role_id, name=None):
        self.id = role_id
        self.name = name or f"role-{role_id}"
        self.mention = f"<@&{role_id}>"


class FakePerms:
    def __init__(self, manage_guild=False, view_channel=False):
        self.manage_guild = manage_guild
        self.view_channel = view_channel


class FakeAnswer:
    def __init__(self, answer_id, text):
        self.id = answer_id
        self.text = text
        self.vote_count = 0
        self.people = []
        self.voters_raises = None

    async def voters(self, **kwargs):
        if self.voters_raises is not None:
            raise self.voters_raises
        for person in list(self.people):
            yield person


class FakePoll:
    """The bits of `discord.Poll` the cog touches, with the ids Discord itself hands back."""

    def __init__(self, question, duration, multiple=False):
        self.question = question
        self.duration = duration
        self.multiple = multiple
        self.answers = []
        self._finalised = False
        self.expires_at = None

    def add_answer(self, *, text, emoji=None):
        self.answers.append(FakeAnswer(len(self.answers) + 1, text))
        return self

    def is_finalised(self):
        return self._finalised


class FakeThread:
    def __init__(self, thread_id, name):
        self.id = thread_id
        self.name = name


def mirror(poll):
    """Discord re-parses the poll it was sent and hands the message a new one; so does this."""
    if poll is None:
        return None
    made = FakePoll(poll.question, poll.duration, getattr(poll, "multiple", False))
    for found in poll.answers:
        made.add_answer(text=found.text)
    return made


class FakeMessage:
    def __init__(self, message_id, channel, content="", **kwargs):
        self.id = message_id
        self.channel = channel
        self.content = content
        self.kwargs = kwargs
        self.sent_poll = kwargs.get("poll")
        self.poll = mirror(self.sent_poll)
        self.jump_url = f"https://discord.test/{message_id}"
        self.edits = []
        self.ended = False
        self.end_raises = None
        self.thread_raises = None
        self.threads = []
        if self.poll is not None:
            self.poll.expires_at = datetime.now(UTC) + self.poll.duration

    async def edit(self, **kwargs):
        self.edits.append(kwargs)

    async def end_poll(self):
        if self.end_raises is not None:
            raise self.end_raises
        self.ended = True
        if self.poll is not None:
            self.poll._finalised = True
        return self

    async def create_thread(self, *, name, **kwargs):
        if self.thread_raises is not None:
            raise self.thread_raises
        thread = FakeThread(self.id + 5000, name)
        self.threads.append(thread)
        return thread


class FakeText:
    def __init__(self, channel_id, guild=None, name="channel"):
        self.id = channel_id
        self.guild = guild
        self.name = name
        self.mention = f"<#{channel_id}>"
        self.category = None
        self.category_id = None
        self.visible_to = set()
        self.messages = []
        self.send_raises = None
        self.fetch_raises = None

    def permissions_for(self, role):
        return FakePerms(view_channel=role.id in self.visible_to)

    async def send(self, content=None, **kwargs):
        if self.send_raises is not None:
            raise self.send_raises
        message = FakeMessage(self.id * 100 + len(self.messages) + 1, self, content or "", **kwargs)
        self.messages.append(message)
        return message

    async def fetch_message(self, message_id):
        if self.fetch_raises is not None:
            raise self.fetch_raises
        found = next((m for m in self.messages if m.id == message_id), None)
        if found is None:
            raise LookupError(message_id)
        return found

    @property
    def polls(self):
        return [m for m in self.messages if m.poll is not None]


class FakeMember:
    def __init__(self, guild, user_id=USER, display_name="Alice", roles=(), manage_guild=False):
        self.id = user_id
        self.guild = guild
        self.display_name = display_name
        self.name = display_name
        self.mention = f"<@{user_id}>"
        self.roles = [FakeRole(r) for r in roles]
        self.guild_permissions = FakePerms(manage_guild=manage_guild)
        self.dms = []
        guild.members[user_id] = self

    async def send(self, content=None, **kwargs):
        self.dms.append({"content": content, **kwargs})


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black Bloc"
        self.channels = {}
        self.members = {}
        self.roles = []
        self.default_role = FakeRole(GUILD)

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_member(self, user_id):
        return self.members.get(user_id)

    def add(self, channel):
        channel.guild = self
        self.channels[channel.id] = channel
        return channel


class FakeGuard:
    def __init__(self, test_channel_id=TEST_CHANNEL):
        self.test_channel_id = test_channel_id
        self.owned = set()

    def allows_channel(self, channel):
        found = getattr(channel, "id", channel)
        return found == self.test_channel_id or found in self.owned

    def own_channel(self, channel):
        self.owned.add(getattr(channel, "id", channel))

    def refusal_message(self):
        return "Black Bloc is in **test mode**"


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guard = None
        self.guilds = [guild]
        self.guild = guild
        self.dynamic = []

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def get_guild(self, guild_id):
        return self.guild if guild_id == self.guild.id else None

    def add_dynamic_items(self, *items):
        self.dynamic.extend(items)

    async def wait_until_ready(self):
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
        self.messages.append({"content": None, "deferred": True})


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.response.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeInteraction:
    def __init__(self, bot, user, channel=None, message=None):
        self.client = bot
        self.user = user
        self.guild = bot.guild
        self.guild_id = bot.guild.id
        self.channel = channel if channel is not None else bot.guild.get_channel(TEST_CHANNEL)
        self.channel_id = self.channel.id if self.channel is not None else TEST_CHANNEL
        self.message = message
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)

    @property
    def sent(self):
        said = [m["content"] for m in self.response.messages if m["content"] is not None]
        return said[-1] if said else None

    @property
    def embeds(self):
        found = []
        for message in self.response.messages:
            found += list(message.get("embeds") or [])
            if message.get("embed") is not None:
                found.append(message["embed"])
        return found


async def action_kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "p.sqlite3")
    await database.connect()
    try:
        yield database
    finally:
        await database.close()


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOG_CHANNEL)
    guild = FakeGuild()
    guild.roles = [FakeRole(STAFF_ROLE, "Lead")]
    guild.add(FakeText(LOG_CHANNEL, name="log"))
    test_channel = guild.add(FakeText(TEST_CHANNEL, name="test"))
    test_channel.visible_to = {STAFF_ROLE}
    guild.add(FakeText(OTHER_CHANNEL, name="general"))
    made = FakeBot(db, store, settings, guild)
    made.guard = FakeGuard()
    return made


@pytest.fixture
def cog(bot):
    return Polls(bot)


@pytest.fixture
def member(bot):
    return FakeMember(bot.guild)


@pytest.fixture
def lead(bot):
    return FakeMember(bot.guild, user_id=1, display_name="Lead", manage_guild=True)


async def make(cog, bot, who, **kwargs):
    """One `/poll create`, defaulting to a two-option single-choice poll in the test channel."""
    interaction = FakeInteraction(bot, who, channel=kwargs.pop("channel", None))
    await cog.poll_create.callback(
        cog,
        interaction,
        kwargs.pop("question", "Pizza or tacos?"),
        kind=kwargs.pop("kind", None),
        options=kwargs.pop("options", "Pizza | Tacos"),
        **kwargs,
    )
    return interaction


def test_the_poll_loop_runs_often_enough_to_be_a_last_call(cog):
    assert POLL_MINUTES == 5


async def test_a_poll_is_posted_with_the_question_answers_and_length_typed(cog, bot, lead, db):
    interaction = await make(cog, bot, lead, hours=6)

    channel = bot.guild.get_channel(TEST_CHANNEL)
    assert len(channel.polls) == 1
    posted = channel.polls[0].poll
    assert posted.question == "Pizza or tacos?"
    assert [a.text for a in posted.answers] == ["Pizza", "Tacos"]
    assert posted.duration == timedelta(hours=6)
    assert posted.multiple is False
    row = await get_poll(db, 1)
    assert row["status"] == pure.OPEN and row["surface"] == pure.NATIVE
    assert row["message_id"] == channel.polls[0].id
    assert "https://discord.test/" in interaction.sent


async def test_the_payload_discord_receives_is_a_real_poll_with_the_hours_in_it(cog, bot, lead):
    await make(cog, bot, lead, kind=choice(pure.CHECKBOX), options="A | B", hours=48)

    sent = bot.guild.get_channel(TEST_CHANNEL).messages[0].sent_poll
    assert isinstance(sent, discord.Poll)
    payload = sent._to_dict()
    assert payload["duration"] == 48
    assert payload["allow_multiselect"] is True
    assert payload["question"] == {"text": "Pizza or tacos?"}
    assert [item["poll_media"]["text"] for item in payload["answers"]] == ["A", "B"]


async def test_the_answer_ids_are_read_back_off_the_message_not_guessed(cog, bot, lead, db):
    await make(cog, bot, lead, options="A | B | C")

    stored = [row["answer_id"] for row in await options_of(db, 1)]
    posted = bot.guild.get_channel(TEST_CHANNEL).polls[0].poll
    assert stored == [answer.id for answer in posted.answers]


async def test_a_checkbox_poll_lets_people_pick_more_than_one(cog, bot, lead, db):
    await make(cog, bot, lead, kind=choice(pure.CHECKBOX), options="A | B")

    assert bot.guild.get_channel(TEST_CHANNEL).polls[0].poll.multiple is True
    assert (await get_poll(db, 1))["multi"] == 1


async def test_yes_no_and_rating_write_their_own_answers(cog, bot, lead):
    await make(cog, bot, lead, kind=choice(pure.YESNO), options=None)
    await make(cog, bot, lead, kind=choice(pure.RATING), options=None, question="How was it?")

    posted = bot.guild.get_channel(TEST_CHANNEL).polls
    assert [a.text for a in posted[0].poll.answers] == ["Yes", "No"]
    assert [a.text for a in posted[1].poll.answers] == ["1", "2", "3", "4", "5"]


async def test_a_poll_with_one_option_is_refused_and_nothing_is_stored(cog, bot, lead, db):
    interaction = await make(cog, bot, lead, options="Pizza")

    assert "at least 2" in interaction.sent
    assert await get_poll(db, 1) is None
    assert bot.guild.get_channel(TEST_CHANNEL).polls == []


async def test_an_anonymous_poll_is_refused_rather_than_posted_in_the_open(cog, bot, lead, db):
    interaction = await make(cog, bot, lead, anonymous=True)

    assert pure.NEXT_UPDATE in interaction.sent
    assert await get_poll(db, 1) is None


async def test_hiding_results_until_close_is_refused_with_the_same_promise(cog, bot, lead, db):
    interaction = await make(cog, bot, lead, results=choice(pure.AT_CLOSE))

    assert pure.NEXT_UPDATE in interaction.sent
    assert await get_poll(db, 1) is None


async def test_more_than_ten_options_is_refused_before_discord_sees_it(cog, bot, lead, db):
    interaction = await make(cog, bot, lead, options=" | ".join(str(n) for n in range(11)))

    assert pure.NEXT_UPDATE in interaction.sent
    assert await get_poll(db, 1) is None


async def test_a_date_poll_says_it_arrives_with_the_next_update(cog, bot, lead, db):
    interaction = await make(cog, bot, lead, kind=choice(pure.DATE))

    assert pure.NEXT_UPDATE in interaction.sent
    assert await get_poll(db, 1) is None


async def test_polls_turned_off_refuse_every_creation(cog, bot, lead, db):
    await bot.store.set(GUILD, "poll_mode", "off")

    interaction = await make(cog, bot, lead)

    assert "turned off" in interaction.sent
    assert await get_poll(db, 1) is None


async def test_a_member_cannot_start_a_poll_while_polls_are_staff_only(cog, bot, member, db):
    interaction = await make(cog, bot, member)

    assert "staff-only" in interaction.sent
    assert await get_poll(db, 1) is None


async def test_opening_polls_to_everyone_lets_a_member_start_one(cog, bot, member, db):
    await bot.store.set(GUILD, "poll_who_can_create", "everyone")

    await make(cog, bot, member)

    assert (await get_poll(db, 1))["creator_id"] == member.id


async def test_test_mode_refuses_a_poll_outside_the_test_channel(cog, bot, lead, db):
    elsewhere = bot.guild.get_channel(OTHER_CHANNEL)

    interaction = await make(cog, bot, lead, channel=elsewhere)

    assert "test mode" in interaction.sent
    assert await get_poll(db, 1) is None
    assert elsewhere.polls == []


async def test_only_the_configured_role_is_pinged_when_a_poll_opens(cog, bot, lead):
    await bot.store.set(GUILD, "poll_ping_role_id", STAFF_ROLE)

    await make(cog, bot, lead)

    message = bot.guild.get_channel(TEST_CHANNEL).polls[0]
    assert message.content.startswith(f"<@&{STAFF_ROLE}>")
    allowed = message.kwargs["allowed_mentions"]
    assert allowed.everyone is False and [r.id for r in allowed.roles] == [STAFF_ROLE]


async def test_a_thread_is_opened_only_when_the_poll_asked_for_one(cog, bot, lead, db):
    await make(cog, bot, lead)
    assert (await get_poll(db, 1))["thread_id"] is None

    await make(cog, bot, lead, thread=True)
    row = await get_poll(db, 2)
    assert row["thread_id"] is not None
    assert bot.guard.allows_channel(row["thread_id"]) is True


async def test_a_thread_black_bloc_could_not_open_is_said_out_loud(cog, bot, lead, db):
    channel = bot.guild.get_channel(TEST_CHANNEL)
    original = channel.send

    async def send(content=None, **kwargs):
        message = await original(content, **kwargs)
        message.thread_raises = refused()
        return message

    channel.send = send

    interaction = await make(cog, bot, lead, thread=True)

    assert "discussion thread" in interaction.sent
    assert "poll.thread_failed" in await action_kinds(db)


async def test_a_channel_that_refuses_the_post_cancels_the_row_rather_than_leaving_it_open(
    cog, bot, lead, db
):
    bot.guild.get_channel(TEST_CHANNEL).send_raises = refused()

    interaction = await make(cog, bot, lead)

    assert "refused to post" in interaction.sent
    assert (await get_poll(db, 1))["status"] == pure.CANCELLED
    assert "poll.open_failed" in await action_kinds(db)


async def test_review_mode_holds_the_poll_and_shows_two_buttons(cog, bot, lead, db):
    await bot.store.set(GUILD, "poll_review_mode", "on")

    interaction = await make(cog, bot, lead)

    row = await get_poll(db, 1)
    assert row["status"] == pure.PENDING_REVIEW
    assert bot.guild.get_channel(TEST_CHANNEL).polls == []
    card = bot.guild.get_channel(TEST_CHANNEL).messages[0]
    assert [item.item.label for item in card.kwargs["view"].children] == ["Approve", "Deny"]
    assert "approve or deny" in interaction.sent and "<#111>" in interaction.sent
    assert lead.dms


async def test_approving_a_held_poll_posts_it_and_tells_the_creator(cog, bot, lead, member, db):
    await bot.store.set(GUILD, "poll_review_mode", "on")
    await bot.store.set(GUILD, "poll_who_can_create", "everyone")
    await make(cog, bot, member)
    card = bot.guild.get_channel(TEST_CHANNEL).messages[0]

    clicked = FakeInteraction(bot, lead, message=card)
    await PollDecisionButton(1, "approve").on_click(clicked)

    row = await get_poll(db, 1)
    assert row["status"] == pure.OPEN and row["message_id"]
    assert bot.guild.get_channel(TEST_CHANNEL).polls
    assert any("approved" in (dm["content"] or "") for dm in member.dms)
    assert card.edits and card.edits[-1]["view"] is None
    assert "poll.approved" in await action_kinds(db)


async def test_denying_a_held_poll_sends_the_reason_and_posts_nothing(cog, bot, lead, member, db):
    await bot.store.set(GUILD, "poll_review_mode", "on")
    await bot.store.set(GUILD, "poll_who_can_create", "everyone")
    await make(cog, bot, member)
    card = bot.guild.get_channel(TEST_CHANNEL).messages[0]

    clicked = FakeInteraction(bot, lead, message=card)
    modal = PollDenyModal(1)
    modal.reason._value = "not this week"
    await modal.on_submit(clicked)

    row = await get_poll(db, 1)
    assert row["status"] == pure.DENIED and row["deny_reason"] == "not this week"
    assert bot.guild.get_channel(TEST_CHANNEL).polls == []
    assert any("not this week" in (dm["content"] or "") for dm in member.dms)


async def test_the_second_person_to_press_approve_is_told_it_is_already_decided(
    cog, bot, lead, member, db
):
    await bot.store.set(GUILD, "poll_review_mode", "on")
    await bot.store.set(GUILD, "poll_who_can_create", "everyone")
    await make(cog, bot, member)
    card = bot.guild.get_channel(TEST_CHANNEL).messages[0]
    await PollDecisionButton(1, "approve").on_click(FakeInteraction(bot, lead, message=card))

    second = FakeInteraction(bot, lead, message=card)
    await PollDecisionButton(1, "approve").on_click(second)

    assert "already" in second.sent
    assert len(bot.guild.get_channel(TEST_CHANNEL).polls) == 1


async def test_a_member_cannot_press_approve(cog, bot, lead, member, db):
    await bot.store.set(GUILD, "poll_review_mode", "on")
    await make(cog, bot, lead)
    card = bot.guild.get_channel(TEST_CHANNEL).messages[0]

    clicked = FakeInteraction(bot, member, message=card)
    await PollDecisionButton(1, "approve").on_click(clicked)

    assert "staff only" in clicked.sent
    assert (await get_poll(db, 1))["status"] == pure.PENDING_REVIEW


async def vote(channel, answer_index, *people):
    poll = channel.polls[0].poll
    answer = poll.answers[answer_index]
    answer.vote_count += len(people)
    answer.people += list(people)


async def test_ending_a_poll_early_writes_the_result_and_posts_it(cog, bot, lead, db):
    await make(cog, bot, lead)
    channel = bot.guild.get_channel(TEST_CHANNEL)
    await vote(channel, 0, FakeMember(bot.guild, 10, "Ann"), FakeMember(bot.guild, 11, "Bo"))
    await vote(channel, 1, FakeMember(bot.guild, 12, "Cy"))

    interaction = FakeInteraction(bot, lead)
    await cog.poll_end.callback(cog, interaction, "1")

    row = await get_poll(db, 1)
    assert row["status"] == pure.CLOSED and row["total_votes"] == 3
    assert channel.polls[0].ended is True
    stored = await results_of(db, 1)
    assert stored["total_votes"] == 3 and stored["winner_position"] == 0
    assert [item["final_votes"] for item in await options_of(db, 1)] == [2, 1]
    assert "result is posted" in interaction.sent
    assert channel.messages[-1].kwargs["embed"].title == "Pizza or tacos?"
    assert "poll.closed" in await action_kinds(db)


async def test_ending_a_poll_records_who_voted_for_what(cog, bot, lead, db):
    await make(cog, bot, lead)
    channel = bot.guild.get_channel(TEST_CHANNEL)
    await vote(channel, 0, FakeMember(bot.guild, 10, "Ann"))

    await cog.poll_end.callback(cog, FakeInteraction(bot, lead), "1")

    rows = await votes_of(db, 1)
    assert [(row["user_id"], row["label"]) for row in rows] == [(10, "Pizza")]


async def test_an_anonymous_row_is_never_given_a_voter_list(cog, bot, lead, db):
    poll_id = await create_poll(
        db,
        GUILD,
        lead.id,
        question="Q",
        kind=pure.SINGLE,
        surface=pure.NATIVE,
        multi=False,
        anonymous=True,
        results=pure.LIVE,
        hours=1,
        channel_id=TEST_CHANNEL,
        ping_role_id=None,
        status=pure.OPEN,
    )
    await add_options(db, poll_id, ["A", "B"])
    channel = bot.guild.get_channel(TEST_CHANNEL)
    given = FakePoll("Q", timedelta(hours=1))
    given.add_answer(text="A")
    given.add_answer(text="B")
    message = await channel.send("x", poll=given)
    message.poll.answers[0].people = [FakeMember(bot.guild, 10, "Ann")]
    message.poll.answers[0].vote_count = 1
    await set_posted(
        db,
        poll_id,
        channel_id=TEST_CHANNEL,
        message_id=message.id,
        finishes_at=datetime.now(UTC),
    )
    await set_answer_ids(db, poll_id, [a.id for a in message.poll.answers])

    await cog.poll_end.callback(cog, FakeInteraction(bot, lead), str(poll_id))

    assert await votes_of(db, poll_id) == []


async def test_somebody_elses_poll_cannot_be_ended_by_a_bystander(cog, bot, lead, member, db):
    await make(cog, bot, lead)

    interaction = FakeInteraction(bot, member)
    await cog.poll_end.callback(cog, interaction, "1")

    assert "not yours" in interaction.sent
    assert (await get_poll(db, 1))["status"] == pure.OPEN


async def test_a_poll_outside_the_test_channel_cannot_be_ended_by_hand(cog, bot, lead, db):
    await make(cog, bot, lead)
    await db.conn.execute("UPDATE polls SET channel_id = ? WHERE id = 1", (OTHER_CHANNEL,))
    await db.conn.commit()

    interaction = FakeInteraction(bot, lead)
    await cog.poll_end.callback(cog, interaction, "1")

    assert "test mode" in interaction.sent
    assert (await get_poll(db, 1))["status"] == pure.OPEN
    assert bot.guild.get_channel(TEST_CHANNEL).polls[0].ended is False


async def test_a_poll_number_that_is_not_a_number_is_refused_in_words(cog, bot, lead):
    interaction = FakeInteraction(bot, lead)
    await cog.poll_end.callback(cog, interaction, "wibble")
    assert "not a poll number" in interaction.sent


async def test_a_poll_black_bloc_has_never_heard_of_is_said_so(cog, bot, lead):
    interaction = FakeInteraction(bot, lead)
    await cog.poll_end.callback(cog, interaction, "404")
    assert "no record" in interaction.sent


async def test_a_closed_poll_cannot_be_closed_again(cog, bot, lead):
    await make(cog, bot, lead)
    await cog.poll_end.callback(cog, FakeInteraction(bot, lead), "1")

    interaction = FakeInteraction(bot, lead)
    await cog.poll_end.callback(cog, interaction, "1")

    assert "already" in interaction.sent


async def test_cancelling_ends_the_vote_at_discord_but_publishes_no_result(cog, bot, lead, db):
    await make(cog, bot, lead)
    channel = bot.guild.get_channel(TEST_CHANNEL)

    interaction = FakeInteraction(bot, lead)
    await cog.poll_cancel.callback(cog, interaction, "1")

    assert (await get_poll(db, 1))["status"] == pure.CANCELLED
    assert channel.polls[0].ended is True
    assert await results_of(db, 1) is None
    assert "cancelled" in interaction.sent
    assert "poll.cancelled" in await action_kinds(db)


async def test_only_staff_may_cancel_a_poll(cog, bot, member, db):
    await bot.store.set(GUILD, "poll_who_can_create", "everyone")
    await make(cog, bot, member)

    interaction = FakeInteraction(bot, member)
    await cog.poll_cancel.callback(cog, interaction, "1")

    assert "staff only" in interaction.sent
    assert (await get_poll(db, 1))["status"] == pure.OPEN


async def test_results_of_an_open_poll_read_the_live_numbers_and_say_so_far(cog, bot, lead):
    await make(cog, bot, lead)
    await vote(bot.guild.get_channel(TEST_CHANNEL), 0, FakeMember(bot.guild, 10, "Ann"))

    interaction = FakeInteraction(bot, lead)
    await cog.poll_results.callback(cog, interaction, "1")

    embed = interaction.embeds[-1]
    assert "so far" in dict((f.name, f.value) for f in embed.fields)["Votes"]
    assert "Pizza" in embed.description


async def test_results_of_a_closed_poll_come_from_the_stored_totals(cog, bot, lead, db):
    await make(cog, bot, lead)
    await vote(bot.guild.get_channel(TEST_CHANNEL), 1, FakeMember(bot.guild, 10, "Ann"))
    await cog.poll_end.callback(cog, FakeInteraction(bot, lead), "1")
    bot.guild.get_channel(TEST_CHANNEL).fetch_raises = LookupError("gone")

    interaction = FakeInteraction(bot, lead)
    await cog.poll_results.callback(cog, interaction, "1")

    embed = interaction.embeds[-1]
    assert dict((f.name, f.value) for f in embed.fields)["Votes"] == "1"
    assert "Tacos" in embed.description


async def test_the_list_names_every_running_poll_and_says_when_it_closes(cog, bot, lead):
    await make(cog, bot, lead, question="First")
    await make(cog, bot, lead, question="Second")

    interaction = FakeInteraction(bot, lead)
    await cog.poll_list.callback(cog, interaction)

    assert "First" in interaction.sent and "Second" in interaction.sent
    assert "closes <t:" in interaction.sent


async def test_an_empty_list_says_how_to_start_one(cog, bot, lead):
    interaction = FakeInteraction(bot, lead)
    await cog.poll_list.callback(cog, interaction)
    assert "/poll create" in interaction.sent


async def test_the_settings_command_shows_the_switches_and_the_loop_health(cog, bot, lead):
    interaction = FakeInteraction(bot, lead)
    await cog.poll_settings.callback(cog, interaction)

    said = interaction.sent
    assert "**mode** — on" in said and "**staff review** — off" in said
    assert "**last call** — 60 minute(s) before close" in said
    assert "polls loop" in said and "never yet" in said


async def test_changing_the_review_switch_goes_through_the_one_validator_and_is_logged(
    cog, bot, lead, db
):
    interaction = FakeInteraction(bot, lead)
    await cog.poll_settings.callback(cog, interaction, review=choice("on"), reminder_minutes=0)

    assert bot.store.get(GUILD, "poll_review_mode") == "on"
    assert bot.store.get(GUILD, "poll_reminder_minutes") == 0
    assert "**last call** — off" in interaction.sent
    assert "poll.settings" in await action_kinds(db)


async def test_a_member_cannot_change_the_poll_settings(cog, bot, member):
    interaction = FakeInteraction(bot, member)
    await cog.poll_settings.callback(cog, interaction, mode=choice("off"))
    assert "staff only" in interaction.sent
    assert bot.store.get(GUILD, "poll_mode") == "on"


async def test_a_vote_arriving_on_the_gateway_is_recorded_against_the_option(cog, bot, lead, db):
    await make(cog, bot, lead)
    row = await get_poll(db, 1)
    payload = discord.RawPollVoteActionEvent(
        {
            "user_id": "10",
            "channel_id": str(TEST_CHANNEL),
            "message_id": str(row["message_id"]),
            "guild_id": str(GUILD),
            "answer_id": 1,
        }
    )

    await cog.on_raw_poll_vote_add(payload)

    assert [(v["user_id"], v["label"]) for v in await votes_of(db, 1)] == [(10, "Pizza")]

    await cog.on_raw_poll_vote_remove(payload)
    assert await votes_of(db, 1) == []


async def test_a_vote_on_a_message_that_is_not_a_black_bloc_poll_is_ignored(cog, bot, lead, db):
    await make(cog, bot, lead)
    payload = discord.RawPollVoteActionEvent(
        {
            "user_id": "10",
            "channel_id": str(TEST_CHANNEL),
            "message_id": "999999",
            "guild_id": str(GUILD),
            "answer_id": 1,
        }
    )

    await cog.on_raw_poll_vote_add(payload)

    assert await votes_of(db, 1) == []


async def test_a_message_id_finds_the_poll_it_belongs_to(cog, bot, lead, db):
    await make(cog, bot, lead)
    row = await get_poll(db, 1)
    assert (await poll_for_message(db, row["message_id"]))["id"] == 1
    assert await poll_for_message(db, 424242) is None


async def close_soon(db, poll_id, minutes):
    await db.conn.execute(
        "UPDATE polls SET closes_at = ? WHERE id = ?",
        ((datetime.now(UTC) + timedelta(minutes=minutes)).isoformat(), poll_id),
    )
    await db.conn.commit()


async def test_the_loop_posts_one_last_call_and_never_a_second(cog, bot, lead, db):
    await make(cog, bot, lead)
    await close_soon(db, 1, 30)
    channel = bot.guild.get_channel(TEST_CHANNEL)
    before = len(channel.messages)

    await cog.run_due_polls()
    await cog.run_due_polls()

    said = [m for m in channel.messages[before:] if "Last call" in (m.content or "")]
    assert len(said) == 1
    assert (await get_poll(db, 1))["reminded_at"] is not None
    assert (await action_kinds(db)).count("poll.reminded") == 1


async def test_a_poll_still_hours_from_closing_gets_no_last_call_yet(cog, bot, lead, db):
    await make(cog, bot, lead)
    await close_soon(db, 1, 600)
    channel = bot.guild.get_channel(TEST_CHANNEL)
    before = len(channel.messages)

    await cog.run_due_polls()

    assert [m for m in channel.messages[before:] if "Last call" in (m.content or "")] == []
    assert (await get_poll(db, 1))["reminded_at"] is None


async def test_a_last_call_switched_off_stays_off(cog, bot, lead, db):
    await bot.store.set(GUILD, "poll_reminder_minutes", 0)
    await make(cog, bot, lead)
    await close_soon(db, 1, 1)
    channel = bot.guild.get_channel(TEST_CHANNEL)
    before = len(channel.messages)

    await cog.run_due_polls()

    assert [m for m in channel.messages[before:] if "Last call" in (m.content or "")] == []


async def test_a_last_call_that_would_not_send_is_not_marked_as_sent(cog, bot, lead, db):
    await make(cog, bot, lead)
    await close_soon(db, 1, 30)
    bot.guild.get_channel(TEST_CHANNEL).send_raises = refused()

    await cog.run_due_polls()

    assert (await get_poll(db, 1))["reminded_at"] is None
    assert "poll.remind_failed" in await action_kinds(db)


async def test_a_reminder_is_claimed_once_so_a_restart_cannot_double_ping(db):
    poll_id = await create_poll(
        db,
        GUILD,
        1,
        question="Q",
        kind=pure.SINGLE,
        surface=pure.NATIVE,
        multi=False,
        anonymous=False,
        results=pure.LIVE,
        hours=1,
        channel_id=TEST_CHANNEL,
        ping_role_id=None,
        status=pure.OPEN,
    )
    assert await claim_reminder(db, poll_id) is True
    assert await claim_reminder(db, poll_id) is False


async def test_the_loop_closes_a_poll_whose_time_is_up_and_writes_the_result(cog, bot, lead, db):
    await make(cog, bot, lead)
    channel = bot.guild.get_channel(TEST_CHANNEL)
    await vote(channel, 1, FakeMember(bot.guild, 10, "Ann"))
    await close_soon(db, 1, -1)

    await cog.run_due_polls()

    row = await get_poll(db, 1)
    assert row["status"] == pure.CLOSED and row["total_votes"] == 1
    assert channel.polls[0].ended is True
    assert channel.messages[-1].kwargs["embed"].description.count("Tacos") == 1


async def test_a_poll_discord_finished_by_itself_is_archived_without_a_second_end_call(
    cog, bot, lead, db
):
    await make(cog, bot, lead)
    channel = bot.guild.get_channel(TEST_CHANNEL)
    channel.polls[0].poll._finalised = True
    await close_soon(db, 1, -1)

    await cog.run_due_polls()

    assert channel.polls[0].ended is False
    assert (await get_poll(db, 1))["status"] == pure.CLOSED


async def test_a_closed_poll_moves_to_the_archive_and_its_voters_are_forgotten(cog, bot, lead, db):
    await make(cog, bot, lead)
    await vote(bot.guild.get_channel(TEST_CHANNEL), 0, FakeMember(bot.guild, 10, "Ann"))
    await cog.poll_end.callback(cog, FakeInteraction(bot, lead), "1")
    await db.conn.execute(
        "UPDATE polls SET closed_at = ? WHERE id = 1",
        ((datetime.now(UTC) - timedelta(days=400)).isoformat(),),
    )
    await db.conn.commit()

    await cog.run_due_polls()

    assert (await get_poll(db, 1))["status"] == pure.ARCHIVED
    assert await votes_of(db, 1) == []
    stored = await results_of(db, 1)
    assert stored["total_votes"] == 1 and stored["votes_dropped"] == 1
    assert "poll.archived" in await action_kinds(db)


async def test_the_archive_keeps_the_voters_when_the_setting_says_so(cog, bot, lead, db):
    await bot.store.set(GUILD, "poll_archive_drop_votes", False)
    await make(cog, bot, lead)
    await vote(bot.guild.get_channel(TEST_CHANNEL), 0, FakeMember(bot.guild, 10, "Ann"))
    await cog.poll_end.callback(cog, FakeInteraction(bot, lead), "1")
    await db.conn.execute(
        "UPDATE polls SET closed_at = ? WHERE id = 1",
        ((datetime.now(UTC) - timedelta(days=400)).isoformat(),),
    )
    await db.conn.commit()

    await cog.run_due_polls()

    assert (await get_poll(db, 1))["status"] == pure.ARCHIVED
    assert len(await votes_of(db, 1)) == 1


async def test_the_archive_says_nothing_on_a_pass_where_nothing_moved(cog, bot, lead, db):
    await make(cog, bot, lead)
    await cog.poll_end.callback(cog, FakeInteraction(bot, lead), "1")

    await cog.run_due_polls()

    assert "poll.archived" not in await action_kinds(db)


async def test_archiving_by_hand_reports_how_many_votes_it_dropped(db):
    poll_id = await create_poll(
        db,
        GUILD,
        1,
        question="Q",
        kind=pure.SINGLE,
        surface=pure.NATIVE,
        multi=False,
        anonymous=False,
        results=pure.LIVE,
        hours=1,
        channel_id=TEST_CHANNEL,
        ping_role_id=None,
        status=pure.CLOSED,
    )
    await add_options(db, poll_id, ["A", "B"])
    option = (await options_of(db, poll_id))[0]
    await db.conn.execute(
        "INSERT INTO poll_votes(poll_id, option_id, user_id, at) VALUES (?, ?, ?, '2026-01-01')",
        (poll_id, option["id"], 10),
    )
    await db.conn.commit()

    assert await archive_poll(db, poll_id, drop_votes=True) == 1
    assert (await get_poll(db, poll_id))["status"] == pure.ARCHIVED


async def test_the_loop_reports_its_last_success_and_its_last_error(cog):
    assert cog.loop_health("_polls_loop") == (None, None)
    assert cog.loop_health("nothing_like_it") == (None, None)

    await cog.run_due_polls()
    cog.last_ok_at["polls"] = "2026-08-27T00:00:00+00:00"

    assert cog.loop_health("_polls_loop")[0] == "2026-08-27T00:00:00+00:00"


def test_a_loop_that_raised_is_restarted_and_the_failure_is_on_the_record(cog):
    restarted = []

    class Loop:
        def restart(self):
            restarted.append(True)

    cog.loop_failed("polls", ValueError("boom"), Loop())

    assert restarted == [True]
    assert "boom" in cog.last_error["polls"]


async def test_the_decision_buttons_are_registered_so_they_survive_a_restart(cog, bot):
    await cog.cog_load()
    try:
        assert PollDecisionButton in bot.dynamic
    finally:
        await cog.cog_unload()


async def test_forgetting_a_deleted_dashboard_channel(cog, bot, db):
    await bot.store.set(GUILD, "poll_channel_id", OTHER_CHANNEL)

    await cog.on_guild_channel_delete(bot.guild.get_channel(OTHER_CHANNEL))

    assert bot.store.get(GUILD, "poll_channel_id") == TEST_CHANNEL
    assert "poll.channel_forgotten" in await action_kinds(db)
