from datetime import UTC, datetime, timedelta

import discord
import pytest
from discord import app_commands

from black_bloc import polls as pure
from black_bloc.cogs.community import polls as polls_cog
from black_bloc.cogs.community.polls import (
    POLL_MINUTES,
    DenyModal,
    PollClearVoteButton,
    PollDecisionButton,
    PollOpenVoteButton,
    Polls,
    PollVoteButton,
    add_options,
    archive_poll,
    claim_reminder,
    create_poll,
    get_poll,
    my_positions,
    options_of,
    panel_counts,
    poll_for_message,
    recurrences,
    results_of,
    scheme_of,
    set_answer_ids,
    set_posted,
    vote_picker,
    voter_key,
    votes_of,
)
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore

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
        self._cog = None

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def get_guild(self, guild_id):
        return self.guild if guild_id == self.guild.id else None

    def add_dynamic_items(self, *items):
        self.dynamic.extend(items)

    def get_cog(self, name):
        return self._cog

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


class RenderedPanel:
    """The one ephemeral message a panel keeps re-rendering in place."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.edits = []
        self._take(kwargs)

    def _take(self, kwargs):
        embed = kwargs.get("embed")
        if "embeds" in kwargs:
            self.embeds = list(kwargs["embeds"])
        elif embed is not None:
            self.embeds = [embed]
        else:
            self.embeds = []
        self.view = kwargs.get("view")

    async def edit(self, **kwargs):
        self.edits.append(kwargs)
        self.kwargs = kwargs
        self._take(kwargs)


class FakeInteraction:
    def __init__(self, bot, user, channel=None, message=None):
        self.client = bot
        self.user = user
        self.guild = bot.guild
        self.guild_id = bot.guild.id
        self.channel = channel if channel is not None else bot.guild.get_channel(TEST_CHANNEL)
        self.channel_id = self.channel.id if self.channel is not None else TEST_CHANNEL
        self.message = message
        self.rendered = None
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)

    async def edit_original_response(self, **kwargs):
        self.rendered = RenderedPanel(**kwargs)
        return self.rendered

    async def original_response(self):
        last = self.response.messages[-1]
        kept = {k: v for k, v in last.items() if k not in ("ephemeral", "content", "deferred")}
        self.rendered = RenderedPanel(**kept)
        return self.rendered

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
    found = Polls(bot)
    bot._cog = found
    return found


@pytest.fixture
def member(bot):
    return FakeMember(bot.guild)


@pytest.fixture
def lead(bot):
    return FakeMember(bot.guild, user_id=1, display_name="Lead", manage_guild=True)


def value_of(given):
    return getattr(given, "value", given)


def draft_for(bot, interaction, **kwargs):
    """Everything the create modal and the preview would have filled in."""
    hours = kwargs.pop("hours", None)
    thread = kwargs.pop("thread", None)
    role = kwargs.pop("ping_role", None)
    return polls_cog.PollDraft(
        question=kwargs.pop("question", "Pizza or tacos?"),
        options=kwargs.pop("options", "Pizza | Tacos") or "",
        kind=value_of(kwargs.pop("kind", None)) or pure.SINGLE,
        hours="" if hours is None else str(hours),
        anonymous=bool(kwargs.pop("anonymous", False)),
        hidden=value_of(kwargs.pop("results", None)) == pure.AT_CLOSE,
        channel_id=interaction.channel_id,
        ping_role_id=getattr(role, "id", role),
        thread=(
            bool(bot.store.get(GUILD, "poll_auto_thread")) if thread is None else bool(thread)
        ),
        start=kwargs.pop("start", None) or "",
        slots=str(kwargs.pop("slots", "") or ""),
        step=str(kwargs.pop("step", "") or ""),
        step_unit=value_of(kwargs.pop("step_unit", None)) or pure.STEP_DAYS,
        **kwargs,
    )


async def make(cog, bot, who, **kwargs):
    """One poll through the panel — the create modal, the preview, then `Post it`."""
    interaction = FakeInteraction(bot, who, channel=kwargs.pop("channel", None))
    draft = draft_for(bot, interaction, **kwargs)
    await interaction.response.defer()
    await polls_cog.write_draft(interaction, draft)
    return interaction


async def open_panel(cog, bot, who):
    interaction = FakeInteraction(bot, who)
    await cog.poll.callback(cog, interaction)
    return interaction


def panel_view(interaction):
    return interaction.response.messages[-1]["view"]


def panel_embed(interaction):
    return interaction.response.messages[-1]["embed"]


def card_embed(interaction):
    return interaction.rendered.kwargs.get("embed")


def card_view(interaction):
    return interaction.rendered.kwargs.get("view")


def find_item(view, label):
    return next(item for item in view.children if getattr(item, "label", None) == label)


def has_item(view, label):
    return any(getattr(item, "label", None) == label for item in view.children)


async def click(bot, who, item):
    interaction = FakeInteraction(bot, who)
    await item.callback(interaction)
    return interaction


async def open_card_for(cog, bot, who, poll_id):
    """The card a member or a staffer would land on after picking that poll."""
    interaction = FakeInteraction(bot, who)
    await polls_cog.open_card(interaction, poll_id)
    return interaction


def fill(modal, **values):
    """What Discord does to a modal's components before it calls `on_submit`."""
    for name, given in values.items():
        component = getattr(modal, name)
        if isinstance(component, discord.ui.CheckboxGroup):
            component._values = list(given)
        else:
            component._value = given
    return modal


async def card_labels(cog, bot, who, poll_id=1):
    card = await open_card_for(cog, bot, who, poll_id)
    return [getattr(item, "label", None) for item in card_view(card).children]


async def card_move(cog, bot, who, poll_id, label):
    card = await open_card_for(cog, bot, who, poll_id)
    return await click(bot, who, find_item(card_view(card), label))


async def end_poll(cog, bot, who, poll_id=1):
    """The card's End button - what `/poll end` used to be."""
    return await card_move(cog, bot, who, poll_id, "End")


async def cancel_it(cog, bot, who, poll_id=1):
    return await card_move(cog, bot, who, poll_id, "Cancel")


async def open_settings(cog, bot, who):
    interaction = FakeInteraction(bot, who)
    await interaction.response.defer()
    await polls_cog.render_settings(interaction)
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


async def test_an_anonymous_poll_is_a_panel_and_says_why(cog, bot, lead, db):
    interaction = await make(cog, bot, lead, anonymous=True)

    row = await get_poll(db, 1)
    assert row["surface"] == pure.PANEL and row["status"] == pure.OPEN
    assert pure.PANEL_BECAUSE_ANONYMOUS in interaction.sent
    assert bot.guild.get_channel(TEST_CHANNEL).messages[0].sent_poll is None


async def test_hiding_results_until_close_is_a_panel_with_the_bars_withheld(cog, bot, lead, db):
    await make(cog, bot, lead, results=choice(pure.AT_CLOSE))

    row = await get_poll(db, 1)
    assert row["surface"] == pure.PANEL and row["results"] == pure.AT_CLOSE
    embed = bot.guild.get_channel(TEST_CHANNEL).messages[0].kwargs["embed"]
    assert "Pizza" in embed.description and pure.FULL not in embed.description
    assert pure.PANEL_HIDDEN in [field.value for field in embed.fields]


async def test_more_than_ten_options_is_a_panel_rather_than_a_discord_poll(cog, bot, lead, db):
    interaction = await make(cog, bot, lead, options=" | ".join(f"o{n}" for n in range(11)))

    assert (await get_poll(db, 1))["surface"] == pure.PANEL
    assert "11" in interaction.sent and "10" in interaction.sent


async def test_more_options_than_the_panel_carries_is_refused_and_nothing_is_stored(
    cog, bot, lead, db
):
    interaction = await make(cog, bot, lead, options=" | ".join(f"o{n}" for n in range(26)))

    assert "26" in interaction.sent and "25" in interaction.sent
    assert await get_poll(db, 1) is None


async def test_a_date_poll_of_ten_slots_or_fewer_is_a_native_multi_select(cog, bot, lead, db):
    await make(
        cog, bot, lead, kind=choice(pure.DATE), options=None,
        start="2026-09-05", slots=3, step=1,
    )

    row = await get_poll(db, 1)
    assert row["surface"] == pure.NATIVE and row["multi"] == 1
    posted = bot.guild.get_channel(TEST_CHANNEL).polls[0].poll
    assert [a.text for a in posted.answers] == ["Sat 05 Sep", "Sun 06 Sep", "Mon 07 Sep"]
    assert posted.multiple is True
    assert [row["value"] for row in await options_of(db, 1)] == [
        pure.parse_day("2026-09-05").isoformat(),
        pure.parse_day("2026-09-06").isoformat(),
        pure.parse_day("2026-09-07").isoformat(),
    ]


async def test_a_date_poll_of_more_than_ten_slots_goes_to_the_panel(cog, bot, lead, db):
    await make(
        cog, bot, lead, kind=choice(pure.DATE), options=None,
        start="2026-09-05", slots=12, step=1,
    )

    assert (await get_poll(db, 1))["surface"] == pure.PANEL
    assert len(await options_of(db, 1)) == 12


async def test_a_date_poll_writes_timestamps_when_the_server_asks_for_them(cog, bot, lead, db):
    await bot.store.set(GUILD, "poll_date_labels", pure.DATE_TIMESTAMP)

    await make(
        cog, bot, lead, kind=choice(pure.DATE), options=None,
        start="2026-09-05", slots=2, step=1,
    )

    labels = [row["label"] for row in await options_of(db, 1)]
    assert all(label.startswith("<t:") and label.endswith(":D>") for label in labels)


async def test_a_date_poll_with_a_start_nobody_can_read_is_refused(cog, bot, lead, db):
    interaction = await make(
        cog, bot, lead, kind=choice(pure.DATE), options=None,
        start="next tuesday", slots=3, step=1,
    )

    assert "not a date" in interaction.sent
    assert await get_poll(db, 1) is None


async def test_a_date_poll_with_no_start_at_all_says_what_it_needs(cog, bot, lead, db):
    interaction = await make(cog, bot, lead, kind=choice(pure.DATE), options=None)

    assert interaction.sent == pure.DATE_NEEDS_A_START
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
    await DenyModal(1).deny(clicked, "not this week")

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

    interaction = await end_poll(cog, bot, lead)

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

    await end_poll(cog, bot, lead)

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

    await end_poll(cog, bot, lead, poll_id)

    assert await votes_of(db, poll_id) == []


async def test_somebody_elses_poll_cannot_be_ended_by_a_bystander(cog, bot, lead, member, db):
    """P9: the move a bystander may not make is not rendered at all."""
    await make(cog, bot, lead)

    assert await card_labels(cog, bot, member) == ["Back"]

    refused = await click(
        bot, member, polls_cog.CardMoveButton(1, pure.CARD_BUTTONS[pure.OPEN][0])
    )
    assert "not yours" in refused.sent
    assert (await get_poll(db, 1))["status"] == pure.OPEN


async def test_a_poll_outside_the_test_channel_cannot_be_ended_by_hand(cog, bot, lead, db):
    await make(cog, bot, lead)
    await db.conn.execute("UPDATE polls SET channel_id = ? WHERE id = 1", (OTHER_CHANNEL,))
    await db.conn.commit()

    interaction = await end_poll(cog, bot, lead)

    assert "test mode" in interaction.sent
    assert (await get_poll(db, 1))["status"] == pure.OPEN
    assert bot.guild.get_channel(TEST_CHANNEL).polls[0].ended is False


async def test_a_poll_number_that_is_not_a_number_is_refused_in_words(cog, bot, lead):
    interaction = FakeInteraction(bot, lead)
    await fill(polls_cog.FindModal(), number="wibble").on_submit(interaction)
    assert "not a poll number" in interaction.sent


async def test_find_takes_a_hash_in_front_of_the_number(cog, bot, lead, db):
    await make(cog, bot, lead)

    interaction = FakeInteraction(bot, lead)
    await fill(polls_cog.FindModal(), number="#1").on_submit(interaction)

    assert card_embed(interaction).title == "Pizza or tacos?"


async def test_a_poll_black_bloc_has_never_heard_of_is_said_so(cog, bot, lead):
    interaction = await open_card_for(cog, bot, lead, 404)
    assert "no record" in interaction.sent


async def test_a_closed_poll_cannot_be_closed_again(cog, bot, lead):
    """Nothing moves it any more, and the race says so rather than closing it twice."""
    await make(cog, bot, lead)
    await end_poll(cog, bot, lead)

    assert await card_labels(cog, bot, lead) == ["Back"]

    row = await get_poll(bot.db, 1)
    said, _ = await polls_cog.end_poll_now(bot, bot.guild, row, lead)
    assert "already" in said


async def test_cancelling_ends_the_vote_at_discord_but_publishes_no_result(cog, bot, lead, db):
    await make(cog, bot, lead)
    channel = bot.guild.get_channel(TEST_CHANNEL)

    interaction = await cancel_it(cog, bot, lead)

    assert (await get_poll(db, 1))["status"] == pure.CANCELLED
    assert channel.polls[0].ended is True
    assert await results_of(db, 1) is None
    assert "cancelled" in interaction.sent
    assert "poll.cancelled" in await action_kinds(db)


async def test_only_staff_may_cancel_a_poll(cog, bot, member, db):
    """The author gets End; Cancel is a staff move and is never drawn for them."""
    await bot.store.set(GUILD, "poll_who_can_create", "everyone")
    await make(cog, bot, member)

    assert await card_labels(cog, bot, member) == ["End", "Back"]

    refused = await click(
        bot, member, polls_cog.CardMoveButton(1, pure.CARD_BUTTONS[pure.OPEN][1])
    )
    assert "staff only" in refused.sent
    assert (await get_poll(db, 1))["status"] == pure.OPEN


async def test_results_of_an_open_poll_read_the_live_numbers_and_say_so_far(cog, bot, lead):
    await make(cog, bot, lead)
    await vote(bot.guild.get_channel(TEST_CHANNEL), 0, FakeMember(bot.guild, 10, "Ann"))

    embed = card_embed(await open_card_for(cog, bot, lead, 1))

    assert "so far" in dict((f.name, f.value) for f in embed.fields)["Votes"]
    assert "Pizza" in embed.description


async def test_results_of_a_closed_poll_come_from_the_stored_totals(cog, bot, lead, db):
    await make(cog, bot, lead)
    await vote(bot.guild.get_channel(TEST_CHANNEL), 1, FakeMember(bot.guild, 10, "Ann"))
    await end_poll(cog, bot, lead)
    bot.guild.get_channel(TEST_CHANNEL).fetch_raises = LookupError("gone")

    embed = card_embed(await open_card_for(cog, bot, lead, 1))

    assert dict((f.name, f.value) for f in embed.fields)["Votes"] == "1"
    assert "Tacos" in embed.description


async def test_the_list_names_every_running_poll_and_says_when_it_closes(cog, bot, lead):
    await make(cog, bot, lead, question="First")
    await make(cog, bot, lead, question="Second")

    said = panel_embed(await open_panel(cog, bot, lead)).description

    assert "First" in said and "Second" in said
    assert "closes <t:" in said


async def test_an_empty_list_says_how_to_start_one(cog, bot, lead):
    said = panel_embed(await open_panel(cog, bot, lead)).description
    assert polls_cog.NO_OPEN_POLLS in said


async def test_the_settings_command_shows_the_switches_and_the_loop_health(cog, bot, lead):
    interaction = await open_settings(cog, bot, lead)

    said = card_embed(interaction).description
    assert "**mode** — on" in said and "**staff review** — off" in said
    assert "**last call** — 60 minute(s) before close" in said
    assert "polls loop" in said and "never yet" in said


async def test_changing_the_review_switch_goes_through_the_one_validator_and_is_logged(
    cog, bot, lead, db
):
    panel = await open_settings(cog, bot, lead)
    await click(bot, lead, find_item(card_view(panel), "Review: off"))

    numbers = FakeInteraction(bot, lead)
    modal = polls_cog.NumbersModal(bot.store, GUILD)
    modal.fields[1]._value = "0"
    await modal.on_submit(numbers)

    assert bot.store.get(GUILD, "poll_review_mode") == "on"
    assert bot.store.get(GUILD, "poll_reminder_minutes") == 0
    assert "**last call** — off" in card_embed(numbers).description
    assert await action_kinds(db) == ["poll.settings", "poll.settings"]


async def test_a_number_the_registry_would_not_take_is_refused_in_words(cog, bot, lead):
    interaction = FakeInteraction(bot, lead)
    modal = polls_cog.NumbersModal(bot.store, GUILD)
    modal.fields[0]._value = "wibble"

    await modal.on_submit(interaction)

    assert "whole number" in interaction.sent
    assert bot.store.get(GUILD, "poll_default_hours") == 24


async def test_a_member_cannot_change_the_poll_settings(cog, bot, member):
    """P9: no Settings button on a member's panel, and the button itself re-checks."""
    assert not has_item(panel_view(await open_panel(cog, bot, member)), "Settings")

    interaction = await click(bot, member, polls_cog.SettingsButton())

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
    await end_poll(cog, bot, lead)
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
    await end_poll(cog, bot, lead)
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
    await end_poll(cog, bot, lead)

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


async def test_every_persistent_button_is_registered_so_it_survives_a_restart(cog, bot):
    await cog.cog_load()
    try:
        for item in (
            PollDecisionButton, PollVoteButton, PollOpenVoteButton, PollClearVoteButton
        ):
            assert item in bot.dynamic
    finally:
        await cog.cog_unload()


async def panel(cog, bot, who, **kwargs):
    """One panel poll, made the only way a panel is reached: by asking for hidden results."""
    kwargs.setdefault("results", choice(pure.AT_CLOSE))
    return await make(cog, bot, who, **kwargs)


async def press(bot, who, poll_id, position, message=None):
    interaction = FakeInteraction(bot, who, message=message)
    await PollVoteButton(poll_id, position).on_click(interaction)
    return interaction


async def test_a_panel_poll_posts_a_button_for_every_option_and_one_to_clear(cog, bot, lead, db):
    await panel(cog, bot, lead, options="Pizza | Tacos")

    posted = bot.guild.get_channel(TEST_CHANNEL).messages[0]
    labels = [item.item.label for item in posted.kwargs["view"].children]
    assert labels == ["Pizza", "Tacos", pure.PANEL_CLEAR]
    assert posted.sent_poll is None


async def test_more_than_five_options_get_one_vote_button_that_opens_a_modal(cog, bot, lead, db):
    await panel(cog, bot, lead, options=" | ".join(f"o{n}" for n in range(6)))

    posted = bot.guild.get_channel(TEST_CHANNEL).messages[0]
    labels = [item.item.label for item in posted.kwargs["view"].children]
    assert labels == [pure.PANEL_VOTE, pure.PANEL_CLEAR]


async def test_pressing_an_option_records_the_vote_and_repaints_the_panel(cog, bot, lead, db):
    await panel(cog, bot, lead, options="Pizza | Tacos")
    posted = bot.guild.get_channel(TEST_CHANNEL).messages[0]

    interaction = await press(bot, lead, 1, 0)

    assert "Pizza" in interaction.sent
    counts, voters = await panel_counts(db, 1)
    assert [row["votes"] for row in counts] == [1, 0] and voters == 1
    assert posted.edits and posted.edits[-1]["embed"] is not None


async def test_a_second_press_on_a_single_choice_poll_moves_the_vote(cog, bot, lead, db):
    await panel(cog, bot, lead, options="Pizza | Tacos")

    await press(bot, lead, 1, 0)
    await press(bot, lead, 1, 1)

    counts, voters = await panel_counts(db, 1)
    assert [row["votes"] for row in counts] == [0, 1] and voters == 1


async def test_a_checkbox_panel_adds_and_takes_back_one_option_at_a_time(cog, bot, lead, db):
    await panel(cog, bot, lead, kind=choice(pure.CHECKBOX), options="A | B | C")

    await press(bot, lead, 1, 0)
    await press(bot, lead, 1, 2)
    counts, voters = await panel_counts(db, 1)
    assert [row["votes"] for row in counts] == [1, 0, 1] and voters == 1

    interaction = await press(bot, lead, 1, 0)
    counts, _ = await panel_counts(db, 1)
    assert [row["votes"] for row in counts] == [0, 0, 1]
    assert "C" in interaction.sent


async def test_clearing_a_vote_leaves_nothing_of_that_person_behind(cog, bot, lead, db):
    await panel(cog, bot, lead, options="Pizza | Tacos")
    await press(bot, lead, 1, 0)

    interaction = FakeInteraction(bot, lead)
    await PollClearVoteButton(1).on_click(interaction)

    assert interaction.sent == pure.VOTE_CLEARED
    assert await panel_counts(db, 1) == ([
        {"position": 0, "label": "Pizza", "votes": 0},
        {"position": 1, "label": "Tacos", "votes": 0},
    ], 0)


async def test_a_vote_on_a_closed_panel_is_refused_and_counts_nothing(cog, bot, lead, db):
    await panel(cog, bot, lead, options="Pizza | Tacos")
    await end_poll(cog, bot, lead)

    interaction = await press(bot, lead, 1, 0)

    assert pure.CLOSED in interaction.sent
    assert (await panel_counts(db, 1))[1] == 0


async def test_a_vote_on_a_poll_black_bloc_has_forgotten_says_so(cog, bot, lead):
    interaction = await press(bot, lead, 404, 0)

    assert interaction.sent == pure.VOTE_GONE


async def test_an_anonymous_panel_keeps_the_count_without_keeping_the_name(cog, bot, lead, db):
    await make(cog, bot, lead, anonymous=True, options="Pizza | Tacos")

    await press(bot, lead, 1, 0)

    stored = [row["user_id"] for row in await votes_of(db, 1)]
    assert stored and lead.id not in stored
    assert (await panel_counts(db, 1))[1] == 1
    assert await my_positions(db, 1, voter_key(await get_poll(db, 1), lead.id)) == [0]


SECRET = "a-poll-vote-secret-nobody-else-has"


async def test_a_poll_made_while_the_key_is_set_is_written_down_as_keyed(cog, bot, lead, db):
    bot.settings.poll_vote_secret = SECRET

    await make(cog, bot, lead, anonymous=True, options="Pizza | Tacos")

    assert (await get_poll(db, 1))["vote_scheme"] == pure.VOTE_KEYED


async def test_a_poll_made_without_the_key_records_the_old_scheme(cog, bot, lead, db):
    await make(cog, bot, lead, anonymous=True, options="Pizza | Tacos")

    assert (await get_poll(db, 1))["vote_scheme"] == pure.VOTE_HASHED


async def test_a_keyed_anonymous_vote_is_a_mac_and_not_the_bare_hash(cog, bot, lead, db):
    """KI-9: holding the database and a member list is no longer enough to confirm a guess."""
    bot.settings.poll_vote_secret = SECRET
    await make(cog, bot, lead, anonymous=True, options="Pizza | Tacos")

    await press(bot, lead, 1, 0)

    row = await get_poll(db, 1)
    stored = [vote["user_id"] for vote in await votes_of(db, 1)]
    assert stored == [voter_key(row, lead.id, SECRET)]
    assert lead.id not in stored
    assert voter_key(row, lead.id, SECRET) != voter_key(row, lead.id, "some-other-key")


async def test_a_poll_open_before_the_key_arrived_keeps_its_old_scheme(cog, bot, lead, db):
    """The migration risk: a scheme that changed under an open poll would let one person
    vote twice."""
    await make(cog, bot, lead, anonymous=True, options="Pizza | Tacos")
    await press(bot, lead, 1, 0)
    bot.settings.poll_vote_secret = SECRET

    await press(bot, lead, 1, 1)

    row = await get_poll(db, 1)
    assert row["vote_scheme"] == pure.VOTE_HASHED
    assert (await panel_counts(db, 1))[1] == 1
    assert await my_positions(db, 1, voter_key(row, lead.id)) == [1]


async def test_a_keyed_poll_whose_key_has_gone_refuses_the_vote_in_words(cog, bot, lead, db):
    bot.settings.poll_vote_secret = SECRET
    await make(cog, bot, lead, anonymous=True, options="Pizza | Tacos")
    bot.settings.poll_vote_secret = None

    interaction = await press(bot, lead, 1, 0)

    assert interaction.sent == pure.VOTE_KEY_MISSING
    assert await votes_of(db, 1) == []
    assert "POLL_VOTE_SECRET" not in str(await votes_of(db, 1))


def test_voter_key_refuses_to_downgrade_a_keyed_poll():
    keyed = {"id": 1, "anonymous": 1, "vote_scheme": pure.VOTE_KEYED}
    with pytest.raises(ValueError):
        voter_key(keyed, 900)


def test_a_row_from_before_the_column_existed_reads_as_the_old_scheme():
    assert scheme_of({"id": 1, "anonymous": 1}) == pure.VOTE_HASHED
    assert scheme_of({"id": 1, "anonymous": 1, "vote_scheme": None}) == pure.VOTE_HASHED
    assert scheme_of({"id": 1, "anonymous": 1, "vote_scheme": "hmac"}) == pure.VOTE_KEYED


def test_a_named_poll_is_still_the_member_id_whatever_the_scheme():
    named = {"id": 1, "anonymous": 0, "vote_scheme": pure.VOTE_KEYED}
    assert voter_key(named, 900) == 900


def test_the_same_person_is_a_different_number_in_every_keyed_poll():
    first = {"id": 1, "anonymous": 1, "vote_scheme": pure.VOTE_KEYED}
    second = {"id": 2, "anonymous": 1, "vote_scheme": pure.VOTE_KEYED}
    assert voter_key(first, 900, SECRET) != voter_key(second, 900, SECRET)
    assert voter_key(first, 900, SECRET) == voter_key(first, 900, SECRET)


async def test_a_bot_with_no_key_says_so_once_when_the_cog_loads(cog, bot, caplog):
    with caplog.at_level("WARNING"):
        await cog.cog_load()
    await cog.cog_unload()

    assert [line for line in caplog.messages if "POLL_VOTE_SECRET" in line]


async def test_a_bot_with_the_key_says_nothing_at_startup(cog, bot, caplog):
    bot.settings.poll_vote_secret = SECRET
    with caplog.at_level("WARNING"):
        await cog.cog_load()
    await cog.cog_unload()

    assert not [line for line in caplog.messages if "POLL_VOTE_SECRET" in line]


async def test_a_named_panel_keeps_the_voter_so_the_export_can_name_them(cog, bot, lead, db):
    await panel(cog, bot, lead, options="Pizza | Tacos")

    await press(bot, lead, 1, 0)

    assert [row["user_id"] for row in await votes_of(db, 1)] == [lead.id]


async def test_a_hidden_panel_shows_its_bars_only_once_it_has_closed(cog, bot, lead, db):
    await panel(cog, bot, lead, options="Pizza | Tacos")
    await press(bot, lead, 1, 0)
    posted = bot.guild.get_channel(TEST_CHANNEL).messages[0]
    assert pure.FULL not in posted.edits[-1]["embed"].description

    await end_poll(cog, bot, lead)

    assert pure.FULL in posted.edits[-1]["embed"].description
    assert posted.edits[-1]["view"] is None


async def test_closing_a_panel_writes_the_result_from_our_own_rows(cog, bot, lead, member, db):
    await panel(cog, bot, lead, kind=choice(pure.CHECKBOX), options="A | B")
    await press(bot, lead, 1, 0)
    await press(bot, member, 1, 0)
    await press(bot, member, 1, 1)

    await end_poll(cog, bot, lead)

    row = await get_poll(db, 1)
    assert row["status"] == pure.CLOSED and row["total_votes"] == 2
    stored = await results_of(db, 1)
    assert stored["winner_position"] == 0
    assert [item["final_votes"] for item in await options_of(db, 1)] == [2, 1]


async def test_a_panel_is_never_ended_at_discord_because_discord_has_no_poll(cog, bot, lead, db):
    await panel(cog, bot, lead, options="Pizza | Tacos")

    await end_poll(cog, bot, lead)

    assert bot.guild.get_channel(TEST_CHANNEL).messages[0].ended is False


async def test_cancelling_a_panel_takes_the_buttons_off_and_publishes_nothing(cog, bot, lead, db):
    await panel(cog, bot, lead, options="Pizza | Tacos")
    posted = bot.guild.get_channel(TEST_CHANNEL).messages[0]

    await cancel_it(cog, bot, lead)

    assert (await get_poll(db, 1))["status"] == pure.CANCELLED
    assert posted.edits[-1]["view"] is None and posted.ended is False
    assert await results_of(db, 1) is None


async def test_the_modal_uses_a_radio_group_for_one_choice_and_checkboxes_for_many(cog, bot, lead):
    rows = [{"position": n, "label": f"o{n}"} for n in range(6)]

    assert isinstance(vote_picker(rows, multi=False), discord.ui.RadioGroup)
    assert isinstance(vote_picker(rows, multi=True), discord.ui.CheckboxGroup)


async def test_past_ten_options_the_modal_falls_back_to_a_select(cog, bot, lead):
    rows = [{"position": n, "label": f"o{n}"} for n in range(12)]

    picker = vote_picker(rows, multi=True, standing=[3])
    assert isinstance(picker, discord.ui.Select)
    assert picker.max_values == 12 and picker.min_values == 0
    assert [option.value for option in picker.options if option.default] == ["3"]


async def test_the_modal_marks_what_that_person_already_picked(cog, bot, lead, db):
    await panel(cog, bot, lead, kind=choice(pure.CHECKBOX), options=" | ".join("ABCDEF"))
    await press(bot, lead, 1, 1)

    interaction = FakeInteraction(bot, lead)
    await PollOpenVoteButton(1).on_click(interaction)

    picker = interaction.response.modals[0].picker
    assert [option.value for option in picker.options if option.default] == ["1"]


async def test_a_modal_submitted_with_nothing_picked_changes_no_vote(cog, bot, lead, db):
    await panel(cog, bot, lead, kind=choice(pure.CHECKBOX), options=" | ".join("ABCDEF"))
    await press(bot, lead, 1, 1)
    interaction = FakeInteraction(bot, lead)
    await PollOpenVoteButton(1).on_click(interaction)
    modal = interaction.response.modals[0]

    again = FakeInteraction(bot, lead)
    await modal.on_submit(again)

    assert again.sent == pure.PICK_SOMETHING
    assert (await panel_counts(db, 1))[1] == 1


async def recurring(cog, bot, who, **kwargs):
    """One repeating poll: the create modal, then `Repeat...`, then `Post it`."""
    every = value_of(kwargs.pop("every", "daily"))
    at = kwargs.pop("at", "09:00")
    day = kwargs.pop("day", "")
    zone = kwargs.pop("tz", None) or "America/Phoenix"
    interaction = FakeInteraction(bot, who, channel=kwargs.pop("channel", None))
    draft = draft_for(
        bot,
        interaction,
        question=kwargs.pop("question", "Are we running tonight?"),
        options=kwargs.pop("options", "Yes | No"),
        **kwargs,
    )
    asked = FakeInteraction(bot, who)
    cadence = fill(polls_cog.CadenceModal(draft), every=every, at=at, day=day, tz=zone)
    await cadence.on_submit(asked)
    if not draft.repeating:
        return asked
    await interaction.response.defer()
    await polls_cog.write_draft(interaction, draft)
    return interaction


async def test_a_recurrence_is_stored_as_a_template_and_never_posted_on_the_spot(cog, bot, db):
    lead = FakeMember(bot.guild, user_id=1, display_name="Lead", manage_guild=True)

    interaction = await recurring(cog, bot, lead)

    row = await get_poll(db, 1)
    assert row["status"] == pure.RECURRING and row["recurrence"] == "daily"
    assert (row["recur_at"], row["recur_tz"]) == ("09:00", "America/Phoenix")
    assert row["recur_next_at"] is not None
    assert bot.guild.get_channel(TEST_CHANNEL).messages == []
    assert "every day at 09:00" in interaction.sent
    assert "poll.recur_created" in await action_kinds(db)


async def test_a_template_never_shows_up_where_polls_are_listed(cog, bot, lead, db):
    await recurring(cog, bot, lead)

    said = panel_embed(await open_panel(cog, bot, lead)).description

    assert polls_cog.NO_OPEN_POLLS in said


async def test_a_date_poll_is_refused_a_recurrence_because_its_slots_would_go_stale(
    cog, bot, lead, db
):
    interaction = await recurring(cog, bot, lead, kind=choice(pure.DATE))

    assert interaction.sent == pure.RECUR_NOT_A_DATE
    assert await get_poll(db, 1) is None


async def test_a_cadence_nobody_can_read_is_refused_before_anything_is_stored(cog, bot, lead, db):
    interaction = await recurring(cog, bot, lead, every=choice("weekly"), day="funday")

    assert "day of the week" in interaction.sent
    assert await get_poll(db, 1) is None


async def test_a_member_cannot_set_a_poll_to_repeat(cog, bot, member, db):
    await bot.store.set(GUILD, "poll_who_can_create", "everyone")

    interaction = await recurring(cog, bot, member)

    assert "staff only" in interaction.sent
    assert await get_poll(db, 1) is None


async def test_a_due_recurrence_opens_one_poll_and_books_the_next_one(cog, bot, lead, db):
    await recurring(cog, bot, lead)
    await db.conn.execute("UPDATE polls SET recur_next_at = ? WHERE id = 1", ("2020-01-01T00:00",))
    await db.conn.commit()

    await cog.run_due_polls()

    made = await get_poll(db, 2)
    assert made["status"] == pure.OPEN and made["schedule_id"] == 1
    assert made["question"] == "Are we running tonight?"
    assert len(bot.guild.get_channel(TEST_CHANNEL).polls) == 1
    template = await get_poll(db, 1)
    assert template["status"] == pure.RECURRING
    assert template["recur_next_at"] > "2020-01-01T00:00"
    assert "poll.recurred" in await action_kinds(db)


async def test_a_second_pass_at_the_same_due_time_opens_nothing_more(cog, bot, lead, db):
    await recurring(cog, bot, lead)
    await db.conn.execute("UPDATE polls SET recur_next_at = ? WHERE id = 1", ("2020-01-01T00:00",))
    await db.conn.commit()

    await cog.run_due_polls()
    await cog.run_due_polls()

    assert await get_poll(db, 3) is None
    assert len(bot.guild.get_channel(TEST_CHANNEL).polls) == 1


async def test_a_paused_recurrence_is_never_due(cog, bot, lead, db):
    await recurring(cog, bot, lead)

    interaction = await card_move(cog, bot, lead, 1, "Pause")
    await cog.run_due_polls()

    assert (await get_poll(db, 1))["recur_next_at"] is None
    assert "paused" in interaction.sent
    assert await get_poll(db, 2) is None


async def test_starting_a_paused_recurrence_again_books_the_next_one(cog, bot, lead, db):
    await recurring(cog, bot, lead)
    await card_move(cog, bot, lead, 1, "Pause")

    interaction = await card_move(cog, bot, lead, 1, "Resume")

    assert (await get_poll(db, 1))["recur_next_at"] is not None
    assert "running again" in interaction.sent


async def test_deleting_a_recurrence_stops_it_without_touching_what_it_opened(cog, bot, lead, db):
    await recurring(cog, bot, lead)
    await db.conn.execute("UPDATE polls SET recur_next_at = ? WHERE id = 1", ("2020-01-01T00:00",))
    await db.conn.commit()
    await cog.run_due_polls()

    asked = await card_move(cog, bot, lead, 1, "Delete")
    interaction = await click(bot, lead, find_item(card_view(asked), "Yes, stop it repeating"))

    assert (await get_poll(db, 1))["status"] == pure.CANCELLED
    assert (await get_poll(db, 2))["status"] == pure.OPEN
    assert "will not run again" in interaction.sent
    assert await recurrences(db, GUILD) == []


async def test_keeping_a_recurrence_leaves_it_running(cog, bot, lead, db):
    await recurring(cog, bot, lead)
    asked = await card_move(cog, bot, lead, 1, "Delete")

    await click(bot, lead, find_item(card_view(asked), "Keep it"))

    assert (await get_poll(db, 1))["status"] == pure.RECURRING


async def test_a_poll_number_that_is_not_a_recurrence_says_so(cog, bot, lead, db):
    await make(cog, bot, lead)

    interaction = FakeInteraction(bot, lead)
    await polls_cog.run_recur_move(interaction, 1, "delete")

    assert "no repeating poll" in interaction.sent
    assert (await get_poll(db, 1))["status"] == pure.OPEN


async def test_the_list_names_the_cadence_and_says_when_one_is_paused(cog, bot, lead, db):
    await recurring(cog, bot, lead, every=choice("weekly"), day="sat", at="19:00")
    await card_move(cog, bot, lead, 1, "Pause")

    card = await open_card_for(cog, bot, lead, 1)
    said = " ".join(one.value for one in card_embed(card).fields)

    assert "every Saturday at 19:00" in said and "paused" in said


async def test_the_repeating_select_only_shows_up_for_staff_and_only_with_one(
    cog, bot, lead, member
):
    assert not any(
        isinstance(item, polls_cog.RecurrencePick)
        for item in panel_view(await open_panel(cog, bot, lead)).children
    )

    await recurring(cog, bot, lead)

    assert any(
        isinstance(item, polls_cog.RecurrencePick)
        for item in panel_view(await open_panel(cog, bot, lead)).children
    )
    assert not any(
        isinstance(item, polls_cog.RecurrencePick)
        for item in panel_view(await open_panel(cog, bot, member)).children
    )


async def test_a_member_cannot_open_a_repeating_polls_card(cog, bot, lead, member):
    await recurring(cog, bot, lead)

    interaction = await open_card_for(cog, bot, member, 1)

    assert "staff only" in interaction.sent


async def test_forgetting_a_deleted_dashboard_channel(cog, bot, db):
    await bot.store.set(GUILD, "poll_channel_id", OTHER_CHANNEL)

    await cog.on_guild_channel_delete(bot.guild.get_channel(OTHER_CHANNEL))

    assert bot.store.get(GUILD, "poll_channel_id") == TEST_CHANNEL
    assert "poll.channel_forgotten" in await action_kinds(db)


# --- the panel itself ---------------------------------------------------------------------


async def test_the_command_answers_ephemerally_with_a_panel(cog, bot, member):
    interaction = await open_panel(cog, bot, member)

    assert interaction.response.messages[0]["ephemeral"] is True
    assert isinstance(panel_view(interaction), polls_cog.PollPanel)
    assert panel_embed(interaction).title == pure.PANEL_TITLE
    assert pure.PANEL_INTRO in panel_embed(interaction).description


async def test_the_command_run_in_a_dm_says_it_belongs_in_the_server(cog, bot, member):
    interaction = FakeInteraction(bot, member)
    interaction.guild = None

    await cog.poll.callback(cog, interaction)

    assert "in the server itself" in interaction.sent


async def test_the_command_refuses_in_words_when_the_database_is_down(
    cog, bot, member, monkeypatch
):
    monkeypatch.setattr(bot.db, "_conn", None)
    interaction = FakeInteraction(bot, member)

    await cog.poll.callback(cog, interaction)

    assert "cannot reach its own database" in interaction.sent


async def test_a_member_panel_shows_create_find_and_refresh_and_no_staff_controls(
    cog, bot, member
):
    await bot.store.set(GUILD, "poll_who_can_create", "everyone")

    view = panel_view(await open_panel(cog, bot, member))

    assert has_item(view, "Create") and has_item(view, "Find #…") and has_item(view, "Refresh")
    assert not has_item(view, "Settings") and not has_item(view, "Logs")
    assert not any(isinstance(item, polls_cog.RecurrencePick) for item in view.children)


async def test_a_staff_panel_adds_settings_logs_and_the_counts_line(cog, bot, lead):
    await make(cog, bot, lead)

    interaction = await open_panel(cog, bot, lead)
    view = panel_view(interaction)

    assert has_item(view, "Settings") and has_item(view, "Logs")
    assert "**1** running" in panel_embed(interaction).description
    assert any(isinstance(item, polls_cog.PollPick) for item in view.children)


async def test_polls_turned_off_hide_create_and_say_so(cog, bot, lead):
    await bot.store.set(GUILD, "poll_mode", "off")

    interaction = await open_panel(cog, bot, lead)

    assert not has_item(panel_view(interaction), "Create")
    assert polls_cog.POLLS_OFF in panel_embed(interaction).description


async def test_staff_only_polls_hide_create_for_a_member_and_say_why(cog, bot, member, lead):
    interaction = await open_panel(cog, bot, member)

    assert not has_item(panel_view(interaction), "Create")
    assert polls_cog.NOT_A_CREATOR in panel_embed(interaction).description
    assert has_item(panel_view(await open_panel(cog, bot, lead)), "Create")


async def test_the_create_button_still_refuses_by_hand_if_things_changed_underneath_it(
    cog, bot, member
):
    button = polls_cog.CreateButton()

    refused = await click(bot, member, button)
    assert polls_cog.NOT_A_CREATOR in refused.sent

    await bot.store.set(GUILD, "poll_mode", "off")
    off = await click(bot, member, button)
    assert polls_cog.POLLS_OFF in off.sent


async def test_the_pick_select_caps_at_25_and_says_how_many_are_left(cog, bot, lead, db):
    for number in range(27):
        await create_poll(
            db,
            GUILD,
            lead.id,
            question=f"Q{number}",
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

    view = panel_view(await open_panel(cog, bot, lead))
    select = next(item for item in view.children if isinstance(item, polls_cog.PollPick))

    assert len(select.options) == 25
    assert select.placeholder == "25 of 27 — the rest are on the site"


async def test_a_short_list_keeps_the_plain_placeholder_and_names_each_poll(cog, bot, lead):
    await make(cog, bot, lead)

    view = panel_view(await open_panel(cog, bot, lead))
    select = next(item for item in view.children if isinstance(item, polls_cog.PollPick))

    assert select.placeholder == pure.PICK_A_POLL
    assert select.options[0].label == "#1 · open · Pizza or tacos?"


async def test_the_open_site_link_appears_only_when_an_origin_is_set(cog, bot, lead, db):
    link = find_item(panel_view(await open_panel(cog, bot, lead)), pure.SITE_BUTTON)
    assert link.url.endswith("/polls.html")

    bare = load_settings(
        _env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL, site_origin=""
    )
    store = SettingsStore(db, bare)
    await store.load()
    bare_bot = FakeBot(db, store, bare, bot.guild)
    bare_bot.guard = FakeGuard()
    bare_bot._cog = Polls(bare_bot)

    without = await open_panel(bare_bot._cog, bare_bot, lead)

    assert not has_item(panel_view(without), pure.SITE_BUTTON)


async def test_picking_a_poll_opens_its_card(cog, bot, lead):
    await make(cog, bot, lead)
    view = panel_view(await open_panel(cog, bot, lead))
    select = next(item for item in view.children if isinstance(item, polls_cog.PollPick))
    select._values = ["1"]

    interaction = await click(bot, lead, select)

    assert card_embed(interaction).title == "Pizza or tacos?"
    assert [item.label for item in card_view(interaction).children] == ["End", "Cancel", "Back"]


async def test_back_returns_to_the_panel(cog, bot, lead):
    await make(cog, bot, lead)
    card = await open_card_for(cog, bot, lead, 1)

    interaction = await click(bot, lead, find_item(card_view(card), "Back"))

    assert card_embed(interaction).title == pure.PANEL_TITLE


async def test_the_refresh_button_re_renders_the_panel(cog, bot, lead):
    panel = await open_panel(cog, bot, lead)
    await make(cog, bot, lead, question="A fresh one")

    interaction = await click(bot, lead, find_item(panel_view(panel), "Refresh"))

    assert "A fresh one" in card_embed(interaction).description


async def test_a_re_render_stops_the_view_it_replaced(cog, bot, lead):
    """P6: the replaced view's timeout clock must never edit the live card."""
    await make(cog, bot, lead)
    panel = await open_panel(cog, bot, lead)
    was = panel_view(panel)

    await click(bot, lead, find_item(was, "Refresh"))

    assert was.replaced is True and was.is_finished()


# --- the card, one row per status ----------------------------------------------------------

EXPECTED_BUTTONS = {
    pure.DRAFT: ["Post it", "Cancel"],
    pure.PENDING_REVIEW: ["Approve", "Deny", "Cancel"],
    pure.OPEN: ["End", "Cancel"],
    pure.CLOSED: [],
    pure.CANCELLED: [],
    pure.DENIED: ["Post it anyway"],
    pure.ARCHIVED: [],
    pure.RECURRING: [],
}


async def poll_at(bot, lead, status):
    poll_id = await create_poll(
        bot.db,
        GUILD,
        lead.id,
        question="Pizza or tacos?",
        kind=pure.SINGLE,
        surface=pure.NATIVE,
        multi=False,
        anonymous=False,
        results=pure.LIVE,
        hours=1,
        channel_id=TEST_CHANNEL,
        ping_role_id=None,
        status=status,
    )
    await add_options(bot.db, poll_id, ["Pizza", "Tacos"])
    return await get_poll(bot.db, poll_id)


@pytest.mark.parametrize("status", pure.STATUSES)
async def test_the_card_renders_exactly_the_buttons_the_table_says(cog, bot, lead, status):
    row = await poll_at(bot, lead, status)

    embed, view = await polls_cog.build_card(bot, bot.guild, row, lead)

    assert [item.label for item in view.children] == [*EXPECTED_BUTTONS[status], "Back"]
    assert len([item for item in view.children if item.row == 0]) <= 5
    assert find_item(view, "Back").row == 1
    if not EXPECTED_BUTTONS[status]:
        assert pure.NO_MOVES_LEFT.format(status=status) in embed.footer.text
        assert f"Poll #{row['id']}" in embed.footer.text


@pytest.mark.parametrize(
    ("status", "label", "func_name"),
    [
        (pure.OPEN, "End", "close_poll"),
        (pure.OPEN, "Cancel", "cancel_poll"),
        (pure.PENDING_REVIEW, "Approve", "apply_decision"),
        (pure.DENIED, "Post it anyway", "apply_decision"),
        (pure.DRAFT, "Post it", "post_poll"),
    ],
)
async def test_a_move_button_calls_its_shared_function_and_leaves_via_alone(
    cog, bot, lead, monkeypatch, status, label, func_name
):
    row = await poll_at(bot, lead, status)
    _, view = await polls_cog.build_card(bot, bot.guild, row, lead)
    calls = []

    async def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return (True, True) if func_name == "close_poll" else ("moved along", row)

    async def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        return (None, "no_channel")

    monkeypatch.setattr(polls_cog, func_name, fake_post if func_name == "post_poll" else fake)

    await click(bot, lead, find_item(view, label))

    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args[0] is bot and args[1] is bot.guild
    assert "via" not in kwargs


async def test_the_deny_button_opens_a_modal_and_the_modal_calls_apply_decision(
    cog, bot, lead, monkeypatch
):
    row = await poll_at(bot, lead, pure.PENDING_REVIEW)
    _, view = await polls_cog.build_card(bot, bot.guild, row, lead)

    opened = FakeInteraction(bot, lead)
    await find_item(view, "Deny").callback(opened)
    modal = opened.response.modals[0]

    assert isinstance(modal, DenyModal)

    calls = []

    async def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return ("denied", row)

    monkeypatch.setattr(polls_cog, "apply_decision", fake)
    await modal.deny(FakeInteraction(bot, lead), "not this week")

    assert calls[0][0][3] == pure.DENIED and calls[0][0][5] == "not this week"
    assert "via" not in calls[0][1]


@pytest.mark.parametrize(
    ("label", "func_name"),
    [("Pause", "pause_recurrence"), ("Resume", "resume_recurrence")],
)
async def test_a_recurrence_button_calls_the_shared_function_the_dashboard_calls(
    cog, bot, lead, monkeypatch, db, label, func_name
):
    await recurring(cog, bot, lead)
    if label == "Resume":
        await card_move(cog, bot, lead, 1, "Pause")
    row = await get_poll(db, 1)
    calls = []

    async def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return ("done", row)

    monkeypatch.setattr(polls_cog, func_name, fake)
    await card_move(cog, bot, lead, 1, label)

    assert len(calls) == 1
    assert calls[0][0][0] is bot and calls[0][0][1] is bot.guild
    assert "via" not in calls[0][1]


async def test_deleting_a_recurrence_goes_through_the_shared_function(
    cog, bot, lead, monkeypatch, db
):
    await recurring(cog, bot, lead)
    row = await get_poll(db, 1)
    calls = []

    async def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return ("gone", row)

    monkeypatch.setattr(polls_cog, "delete_recurrence", fake)
    asked = await card_move(cog, bot, lead, 1, "Delete")
    await click(bot, lead, find_item(card_view(asked), "Yes, stop it repeating"))

    assert len(calls) == 1 and "via" not in calls[0][1]


async def test_staff_can_still_post_a_poll_they_denied(cog, bot, lead, member, db):
    """Fork I-1: never a terminal state staff cannot leave."""
    await bot.store.set(GUILD, "poll_review_mode", "on")
    await bot.store.set(GUILD, "poll_who_can_create", "everyone")
    await make(cog, bot, member)
    await DenyModal(1).deny(FakeInteraction(bot, lead), "not this week")
    assert (await get_poll(db, 1))["status"] == pure.DENIED

    interaction = await card_move(cog, bot, lead, 1, "Post it anyway")

    assert (await get_poll(db, 1))["status"] == pure.OPEN
    assert len(bot.guild.get_channel(TEST_CHANNEL).polls) == 1
    assert "Approved and posted" in interaction.sent
    assert any("approved" in (dm["content"] or "") for dm in member.dms)


# --- create: one row, one log line, nothing before Post it ---------------------------------


async def fresh_draft(cog, bot, who, **fields):
    """The create modal filled in and submitted — the preview, with nothing written yet."""
    opened = FakeInteraction(bot, who)
    draft = polls_cog.PollDraft(channel_id=TEST_CHANNEL)
    modal = polls_cog.NewPollModal(draft)
    fill(
        modal,
        question=fields.get("question", "Pizza or tacos?"),
        options=fields.get("options", "Pizza | Tacos"),
        hours=fields.get("hours", ""),
        kind=fields.get("kind", pure.SINGLE),
        switches=fields.get("switches", []),
    )
    await modal.on_submit(opened)
    return opened, draft


async def test_the_create_modal_carries_the_five_components_discord_allows(cog, bot, lead):
    modal = polls_cog.NewPollModal(polls_cog.PollDraft())

    assert len(modal.children) == 5
    assert all(isinstance(item, discord.ui.Label) for item in modal.children)
    assert isinstance(modal.kind, discord.ui.RadioGroup)
    assert isinstance(modal.switches, discord.ui.CheckboxGroup)
    assert [one.value for one in modal.kind.options] == list(pure.KNOWN_KINDS)


async def test_the_preview_writes_no_row_at_all_until_post_it(cog, bot, lead, db):
    """Fork I-3: a panel that times out mid-create leaves nothing behind."""
    opened, draft = await fresh_draft(cog, bot, lead)

    assert await get_poll(db, 1) is None
    assert await action_kinds(db) == []
    view = card_view(opened)
    assert has_item(view, "Post it") and has_item(view, "Start over")
    assert card_embed(opened).title == "Pizza or tacos?"


async def test_post_it_writes_exactly_one_row_and_one_log_line(cog, bot, lead, db):
    opened, _ = await fresh_draft(cog, bot, lead)

    interaction = await click(bot, lead, find_item(card_view(opened), "Post it"))

    assert (await get_poll(db, 1))["status"] == pure.OPEN
    assert await get_poll(db, 2) is None
    assert await action_kinds(db) == ["poll.created", "poll.opened"]
    assert "up" in interaction.sent


async def test_a_refusal_keeps_the_preview_and_writes_nothing(cog, bot, lead, db):
    opened, _ = await fresh_draft(cog, bot, lead, options="Pizza")

    assert not has_item(card_view(opened), "Post it")
    assert "at least 2 options" in card_embed(opened).description
    assert await get_poll(db, 1) is None


async def test_a_date_poll_asks_for_its_slots_before_it_can_go_up(cog, bot, lead, db):
    opened, draft = await fresh_draft(cog, bot, lead, kind=pure.DATE, options="")

    assert has_item(card_view(opened), "Date slots…")
    assert not has_item(card_view(opened), "Post it")
    assert polls_cog.DRAFT_NEEDS_SLOTS in " ".join(
        one.value for one in card_embed(opened).fields
    )

    slots = FakeInteraction(bot, lead)
    modal = polls_cog.SlotsModal(draft)
    fill(modal, start="2026-09-05", slots="3", step="1", unit=pure.STEP_DAYS)
    await modal.on_submit(slots)

    assert has_item(card_view(slots), "Post it")
    await click(bot, lead, find_item(card_view(slots), "Post it"))
    assert len(await options_of(db, 1)) == 3


async def test_the_switches_carry_anonymity_and_hidden_results_into_the_row(cog, bot, lead, db):
    opened, _ = await fresh_draft(cog, bot, lead, switches=["anonymous", "hidden"])

    await click(bot, lead, find_item(card_view(opened), "Post it"))

    row = await get_poll(db, 1)
    assert row["anonymous"] == 1 and row["results"] == pure.AT_CLOSE
    assert row["surface"] == pure.PANEL


async def test_start_over_reopens_the_modal_with_what_was_typed(cog, bot, lead):
    opened, _ = await fresh_draft(cog, bot, lead, question="Pizza or tacos?")

    again = FakeInteraction(bot, lead)
    await find_item(card_view(opened), "Start over").callback(again)

    assert str(again.response.modals[0].question.default) == "Pizza or tacos?"


async def test_the_preview_selects_move_the_channel_the_ping_and_the_thread(cog, bot, lead, db):
    opened, draft = await fresh_draft(cog, bot, lead)
    view = card_view(opened)

    await click(bot, lead, find_item(view, "Thread: off"))
    assert draft.thread is True

    channel = next(item for item in view.children if isinstance(item, discord.ui.ChannelSelect))
    channel._values = [bot.guild.get_channel(OTHER_CHANNEL)]
    await click(bot, lead, channel)
    assert draft.channel_id == OTHER_CHANNEL


async def test_giving_up_on_a_draft_goes_back_to_the_panel_with_nothing_stored(cog, bot, lead, db):
    opened, _ = await fresh_draft(cog, bot, lead)

    interaction = await click(bot, lead, find_item(card_view(opened), "Cancel"))

    assert card_embed(interaction).title == pure.PANEL_TITLE
    assert await get_poll(db, 1) is None


# --- staff is re-checked before every staff move -------------------------------------------


class Demoted:
    """A store that says yes at render time and no once the click arrives."""

    def __init__(self, store):
        self._store = store
        self.staff = True

    def __getattr__(self, name):
        return getattr(self._store, name)

    def is_staff(self, member):
        return self.staff


async def test_a_staffer_demoted_while_the_card_is_open_moves_nothing(cog, bot, lead, db):
    await make(cog, bot, lead)
    row = await get_poll(db, 1)
    _, view = await polls_cog.build_card(bot, bot.guild, row, lead)
    bot.store = Demoted(bot.store)
    bot.store.staff = False

    refused = await click(bot, lead, find_item(view, "Cancel"))

    assert "staff only" in refused.sent
    assert (await get_poll(db, 1))["status"] == pure.OPEN


async def test_a_demoted_staffer_submitting_the_deny_modal_is_refused_in_words(cog, bot, lead, db):
    await bot.store.set(GUILD, "poll_review_mode", "on")
    await make(cog, bot, lead)
    bot.store = Demoted(bot.store)
    bot.store.staff = False

    interaction = FakeInteraction(bot, lead)
    await DenyModal(1).deny(interaction, "no")

    assert "staff only" in interaction.sent
    assert (await get_poll(db, 1))["status"] == pure.PENDING_REVIEW


async def test_a_demoted_staffer_opening_settings_is_refused_in_words(cog, bot, lead):
    bot.store = Demoted(bot.store)
    bot.store.staff = False

    interaction = await click(bot, lead, polls_cog.SettingsButton())

    assert "staff only" in interaction.sent


# --- logs ---------------------------------------------------------------------------------


async def test_the_logs_button_answers_with_a_new_ephemeral_message(cog, bot, lead, db):
    await make(cog, bot, lead)
    panel = await open_panel(cog, bot, lead)

    interaction = await click(bot, lead, find_item(panel_view(panel), "Logs"))

    last = interaction.response.messages[-1]
    assert last["ephemeral"] is True
    assert "poll.created" in last["embed"].description
    assert interaction.rendered is None


async def test_the_logs_button_still_refuses_a_demoted_staffer_in_words(cog, bot, member):
    interaction = await click(bot, member, polls_cog.LogsButton())

    assert "staff only" in interaction.sent


# --- the panel goes quiet -------------------------------------------------------------------


async def test_the_panel_disables_every_item_and_says_so_on_timeout(cog, bot, lead):
    view = polls_cog.PollPanel(1)
    view.add_item(polls_cog.RefreshButton())
    embed = discord.Embed(title=pure.PANEL_TITLE, description="x")
    view.message = RenderedPanel(embed=embed, view=view)

    await view.on_timeout()

    assert all(item.disabled for item in view.children)
    assert view.message.embeds[0].footer.text == pure.PANEL_TIMEOUT_FOOTER


async def test_the_panel_minutes_key_is_what_sets_the_clock(cog, bot, lead):
    await bot.store.set(GUILD, "poll_panel_minutes", 3)

    view = panel_view(await open_panel(cog, bot, lead))

    assert view.timeout == 180
