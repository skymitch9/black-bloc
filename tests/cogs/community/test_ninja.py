import asyncio
from datetime import timedelta

import discord
import pytest

from black_bloc import ninja
from black_bloc import ninja_store as store
from black_bloc.cogs.community import ninja as ninja_cog
from black_bloc.cogs.community.ninja import Ninja
from tests.ninja_fakes import (
    ELSEWHERE,
    GUILD,
    NINJA,
    NOW,
    PT,
    REAL,
    STAFF_ID,
    YATO,
    FakeInteraction,
    FakePost,
    Untouchable,
    kinds,
    ninja_bot,
)
from tests.questions_fakes import FakeMember


@pytest.fixture
async def bot(db, monkeypatch):
    return await ninja_bot(db, monkeypatch)


async def mark(bot, posts="1", minutes=""):
    staff = bot.guild.get_member(STAFF_ID)
    return await ninja.mark(bot, bot.guild, staff, [PT], REAL, posts, minutes, now=NOW)


async def test_the_listener_puts_the_emote_on_a_marked_post(bot):
    cog = Ninja(bot)
    await mark(bot, posts="2")
    post = FakePost(PT)

    await cog.on_message(post)

    assert post.reactions == [NINJA]
    assert "ninja.reacted" in await kinds(bot.db)


async def test_the_listener_reads_nothing_for_a_post_nobody_marked(bot):
    cog = Ninja(bot)
    await mark(bot)
    bot.db = Untouchable()

    for post in (FakePost(YATO), FakePost(PT, ELSEWHERE), FakePost(PT, bot=True)):
        await cog.on_message(post)
        assert post.reactions == []


async def test_a_listener_failure_is_a_warning_never_a_crash(bot, monkeypatch, caplog):
    cog = Ninja(bot)
    await mark(bot)

    async def broken(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(ninja, "on_post", broken)
    await cog.on_message(FakePost(PT))
    assert "not handled" in caplog.text


async def test_the_sweep_ends_a_time_budget_and_reloads_the_map(bot):
    cog = Ninja(bot)
    await mark(bot, posts="", minutes="5")

    await cog.reconcile(NOW + timedelta(minutes=6))

    [ended] = await store.recent_ended(bot.db, GUILD)
    assert ended["ended_because"] == store.TIME
    assert (GUILD, PT) not in ninja.marked(bot)


async def test_two_reconciles_at_boot_end_a_mark_once(bot):
    """Checklist 37: on_ready and the loop's first tick both land inside the window."""
    cog = Ninja(bot)
    await mark(bot, posts="", minutes="1")
    late = NOW + timedelta(minutes=2)

    await asyncio.gather(
        cog._reconciles.run(lambda: cog.reconcile(late), skip_if_recent=True),
        cog._reconciles.run(lambda: cog.reconcile(late)),
        cog.reconcile(late),
    )

    assert (await kinds(bot.db)).count("ninja.ended") == 1


async def test_an_unavailable_server_is_skipped_by_the_sweep(bot):
    cog = Ninja(bot)
    await mark(bot, posts="", minutes="1")
    bot.guild.unavailable = True

    await cog.reconcile(NOW + timedelta(minutes=2))

    assert len(await store.active(bot.db, GUILD)) == 1


async def test_the_sweep_reports_its_health_and_survives_a_failure(bot, monkeypatch):
    cog = Ninja(bot)

    async def broken(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(ninja, "settle", broken)
    await cog._sweep.coro(cog)
    assert cog.loop_health("_sweep")[1] == "RuntimeError: boom"
    monkeypatch.undo()
    await cog._sweep.coro(cog)
    last_ok, error = cog.loop_health("_sweep")
    assert last_ok and error is None
    assert cog.loop_health("other") == (None, None)


async def test_slash_ninja_opens_the_panel_for_staff_and_refuses_anyone_else(bot):
    staff = bot.guild.get_member(STAFF_ID)
    interaction = FakeInteraction(bot, staff)

    await ninja_cog.open_panel(interaction)

    [sent] = interaction.response.messages
    assert sent["ephemeral"] is True and sent["embed"].title == "Ninja marks"

    stranger = FakeMember(77)
    stranger.guild = bot.guild
    refused = FakeInteraction(bot, stranger)
    await ninja_cog.open_panel(refused)
    assert refused.response.messages[0].get("embed") is None
    assert "staff only" in refused.said[0]


async def test_slash_ninja_is_staff_locked():
    command = Ninja.ninja
    assert command.name == "ninja"
    assert command.default_permissions == discord.Permissions(manage_messages=True)
