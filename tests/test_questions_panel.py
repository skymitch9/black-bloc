from datetime import UTC, datetime

import discord
import pytest

from black_bloc import questions as rules
from black_bloc import questions_panel as panel
from black_bloc import questions_rehearse as testing
from black_bloc import questions_store as store
from tests.questions_fakes import GUILD, HOME, REAL, FakeMember, make_bot


class FakeResponse:
    def __init__(self):
        self.done = False
        self.messages = []
        self.modals = []

    def is_done(self):
        return self.done

    async def defer(self, **kwargs):
        self.done = True

    async def send_message(self, content=None, **kwargs):
        self.done = True
        self.messages.append({"content": content, **kwargs})

    async def send_modal(self, modal):
        self.done = True
        self.modals.append(modal)


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, **kwargs):
        self.response.messages.append({"content": content, **kwargs})


class FakeEdited:
    def __init__(self, kwargs):
        self.embeds = [kwargs.get("embed")]
        self.view = kwargs.get("view")


class FakeInteraction:
    def __init__(self, client, user):
        self.client = client
        self.user = user
        self.guild = client.guild
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)
        self.edits = []

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return FakeEdited(kwargs)

    @property
    def said(self):
        return [one["content"] for one in self.response.messages if one["content"]]


def labels(view):
    return [item.label for item in view.children if isinstance(item, discord.ui.Button)]


@pytest.fixture
async def bot(db, monkeypatch):
    return await make_bot(db, monkeypatch)


@pytest.fixture
def staff(bot):
    member = FakeMember(42)
    member.guild = bot.guild
    member.guild_permissions = discord.Permissions(manage_guild=True)
    bot.guild.members[42] = member
    return member


def test_the_root_buttons_render_only_when_they_can_be_pressed():
    pending = {"status": rules.PENDING, "mode": "shadow", "posted": None}
    assert panel.root_moves(pending, []) == ["add", "skip", "refresh"]
    assert panel.root_moves(pending, [object()]) == ["add", "post", "skip", "refresh"]
    off = pending | {"mode": "off"}
    assert panel.root_moves(off, [object()]) == ["add", "skip", "refresh"]
    skipped = pending | {"status": rules.SKIPPED}
    assert panel.root_moves(skipped, [object()]) == ["add", "post", "unskip", "refresh"]
    by_bot = {"status": rules.POSTED, "mode": "on", "posted": {"posted_by": rules.BY_BOT}}
    assert panel.root_moves(by_bot, [object()]) == ["add", "post", "take_down", "refresh"]
    assert panel.root_moves(by_bot, []) == ["add", "take_down", "refresh"]
    by_owner = by_bot | {"posted": {"posted_by": rules.BY_OWNER}}
    assert panel.root_moves(by_owner, []) == ["add", "refresh"]
    extra = pending | {"extra": {"posted_by": rules.BY_BOT}}
    assert panel.root_moves(extra, []) == ["add", "skip", "take_down", "refresh"]


def test_post_to_test_renders_only_when_it_can_send_a_copy():
    pending = {"status": rules.PENDING, "mode": "on", "posted": None}
    assert panel.root_moves(pending, [], testable=True)[-1] == "test"
    assert "test" not in panel.root_moves(pending, [object()])


def test_a_card_offers_up_and_down_only_where_there_is_room():
    assert panel.card_moves(0, 1) == ["edit", "remove", "back"]
    assert panel.card_moves(0, 3) == ["edit", "remove", "down", "back"]
    assert panel.card_moves(2, 3) == ["edit", "remove", "up", "back"]


async def test_the_panel_shows_the_slot_the_question_and_the_queue(bot):
    await store.add_many(bot.db, GUILD, ["one?", "two?"], 5, datetime(2026, 10, 1, tzinfo=UTC))

    embed, view = await panel.build_root(bot, bot.guild)

    assert "**Question** — one?" in embed.description
    assert "**Queued** — 2" in embed.description
    assert f"<#{REAL}>" in embed.description
    assert rules.NO_OWNER_LINE in embed.description
    assert labels(view) == ["Add", "Post one now", "Skip this week", "Refresh", "Post to test"]
    [test] = [item for item in view.children if getattr(item, "name", "") == "test"]
    assert test.row == 2
    assert any(isinstance(item, panel.QueuePick) for item in view.children)


async def test_add_many_through_the_modal_and_the_panel_redraws(bot, staff):
    interaction = FakeInteraction(bot, staff)
    modal = panel.AddModal()
    modal.typed._value = "one?\ntwo?\n"

    await modal.on_submit(interaction)

    assert [row["body"] for row in await store.queued(bot.db, GUILD)] == ["one?", "two?"]
    assert interaction.said == ["2 question(s) added to the queue."]
    assert "**Queued** — 2" in interaction.edits[-1]["embed"].description


async def test_somebody_who_is_not_staff_is_refused_before_anything_changes(bot):
    stranger = FakeMember(77)
    stranger.guild = bot.guild
    interaction = FakeInteraction(bot, stranger)
    modal = panel.AddModal()
    modal.typed._value = "one?"

    await modal.on_submit(interaction)

    assert await store.queued(bot.db, GUILD) == []
    assert interaction.said


async def test_a_card_for_a_question_gone_from_the_queue_lands_on_the_list(bot, staff):
    interaction = FakeInteraction(bot, staff)
    await panel.open_card(interaction, 999, None)
    assert interaction.edits[-1]["embed"].title == rules.PANEL_TITLE


async def test_post_now_from_the_panel_posts_and_answers_in_words(bot, staff):
    await store.add_many(bot.db, GUILD, ["one?"], 5, datetime(2026, 10, 1, tzinfo=UTC))
    interaction = FakeInteraction(bot, staff)

    await panel.run_post_now(interaction)

    assert interaction.said == [rules.POSTED_EXTRA.format(where=f"<#{REAL}>")]
    assert bot.guild.get_channel(REAL).sent[-1].content.endswith("one?")
    view = interaction.edits[-1]["view"]
    assert "Take it down" in labels(view)
    assert "**This week** — waiting" in interaction.edits[-1]["embed"].description

    [down] = [item for item in view.children if getattr(item, "name", "") == "take_down"]
    assert panel.downable(down.found)["body"] == "one?"


async def test_post_to_test_from_the_panel_sends_a_copy_and_leaves_the_week_alone(bot, staff):
    await store.add_many(bot.db, GUILD, ["one?"], 5, datetime(2026, 10, 1, tzinfo=UTC))
    interaction = FakeInteraction(bot, staff)

    await panel.run_test(interaction)

    assert interaction.said == [testing.TESTED.format(where=HOME)]
    assert bot.guild.get_channel(HOME).sent[-1].content == "one?"
    assert [row["body"] for row in await store.queued(bot.db, GUILD)] == ["one?"]
    assert "**This week** — waiting" in interaction.edits[-1]["embed"].description


async def test_with_no_rehearsal_home_the_panel_says_why_and_offers_no_post_to_test(bot):
    await store.add_many(bot.db, GUILD, ["one?"], 5, datetime(2026, 10, 1, tzinfo=UTC))
    for key in ("shadow_channel_id", "log_channel_id"):
        await bot.store.clear(GUILD, key)

    embed, view = await panel.build_root(bot, bot.guild)

    assert testing.NO_HOME_LINE in embed.description
    assert testing.LABEL not in labels(view)
