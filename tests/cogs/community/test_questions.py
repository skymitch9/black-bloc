import asyncio
from datetime import timedelta

import discord
import pytest

from black_bloc import questions_store as store
from black_bloc.cogs.community import questions as questions_cog
from black_bloc.cogs.community.questions import Questions
from tests.questions_fakes import AFTER_GRACE, GUILD, REAL, SLOT, FakeMember, make_bot


@pytest.fixture
async def bot(db, monkeypatch):
    return await make_bot(db, monkeypatch)


class FakeResponse:
    def __init__(self):
        self.done = False
        self.messages = []

    def is_done(self):
        return self.done

    async def send_message(self, content=None, **kwargs):
        self.done = True
        self.messages.append({"content": content, **kwargs})


class FakeInteraction:
    def __init__(self, client, user, guild=True):
        self.client = client
        self.user = user
        self.guild = client.guild if guild else None
        self.response = FakeResponse()

    async def original_response(self):
        return object()


async def test_two_reconciles_at_boot_post_exactly_one_question(bot):
    """Checklist 37: on_ready and the loop's first tick both land inside the window."""
    cog = Questions(bot)
    await store.add_many(bot.db, GUILD, ["one?", "two?"], 5, SLOT - timedelta(days=3))
    await cog.reconcile(SLOT - timedelta(days=1))

    await asyncio.gather(
        cog._reconciles.run(lambda: cog.reconcile(AFTER_GRACE), skip_if_recent=True),
        cog._reconciles.run(lambda: cog.reconcile(AFTER_GRACE)),
        cog.reconcile(AFTER_GRACE),
    )

    assert len(bot.guild.get_channel(REAL).sent) == 1
    assert [row["body"] for row in await store.queued(bot.db, GUILD)] == ["two?"]


async def test_an_unavailable_server_is_skipped(bot):
    cog = Questions(bot)
    bot.guild.unavailable = True
    await store.add_many(bot.db, GUILD, ["one?"], 5, SLOT - timedelta(days=3))

    await cog.reconcile(AFTER_GRACE)

    assert bot.guild.get_channel(REAL).sent == []


async def test_a_stopped_loop_records_why_and_starts_again(bot, monkeypatch):
    cog = Questions(bot)
    restarted = []
    monkeypatch.setattr(cog._sweep, "restart", lambda: restarted.append(True))

    await cog._sweep_stopped(RuntimeError("boom"))

    assert cog.last_error == "RuntimeError: boom" and restarted == [True]
    assert cog.loop_health("_sweep") == (None, "RuntimeError: boom")


async def test_the_panel_opens_for_staff_and_refuses_anyone_else(bot):
    staff = FakeMember(42)
    staff.guild = bot.guild
    staff.guild_permissions = discord.Permissions(manage_guild=True)
    opened = FakeInteraction(bot, staff)
    await questions_cog.open_panel(opened)
    [sent] = opened.response.messages
    assert sent["ephemeral"] is True and sent["embed"].title == "Weekly questions"

    stranger = FakeMember(77)
    stranger.guild = bot.guild
    refused = FakeInteraction(bot, stranger)
    await questions_cog.open_panel(refused)
    assert "embed" not in refused.response.messages[-1]

    nowhere = FakeInteraction(bot, staff, guild=False)
    await questions_cog.open_panel(nowhere)
    assert nowhere.response.messages[-1]["content"]
