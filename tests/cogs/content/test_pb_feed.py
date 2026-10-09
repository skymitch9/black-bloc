# ruff: noqa: F401, F811
import ast
import pathlib
from datetime import timedelta
from types import SimpleNamespace

from black_bloc import pb_store
from black_bloc.cogs.content import pb_feed as cog_module
from black_bloc.cogs.content.pb_feed import PbFeed
from black_bloc.command_visibility import HIDDEN_WHEN_OFF
from black_bloc.speedrun import SERVER, SpeedrunError
from tests.test_pb_looks import (
    ADA,
    GUILD,
    NOW,
    REHEARSAL,
    ZFG,
    best,
    bot,
    client,
    feed,
    guild,
    kinds,
    link,
)

SOURCE = pathlib.Path(cog_module.__file__)


async def test_the_loop_matches_takes_the_baseline_and_then_rehearses_the_news(
    bot, guild, feed, client
):
    cog = PbFeed(bot)
    await link(bot.db, ADA, "zfg1")
    client.by_twitch["zfg1"] = [ZFG]
    client.bests[ZFG.id] = [best("r1")]

    await cog.run_once(NOW)
    await cog.run_once(NOW + timedelta(minutes=1))
    later = NOW + timedelta(minutes=70)
    client.bests[ZFG.id] = [best("r9", seconds=90.0, verified_at=later - timedelta(minutes=5))]
    await cog.run_once(later)

    assert cog.feed is feed
    assert len(guild.get_channel(REHEARSAL).sent) == 1
    assert await kinds(bot.db) == [
        "pbfeed.matched",
        "pbfeed.baseline",
        "pbfeed.would_post",
    ]


async def test_an_outage_never_raises_out_of_the_loop_and_health_stays_readable(
    bot, guild, feed, client
):
    cog = PbFeed(bot)
    await link(bot.db, ADA, "zfg1")
    client.raises = SpeedrunError(SERVER, status=503)

    await cog._looks.coro(cog)

    assert cog.last_error is None and cog.last_run_at is not None
    assert cog.loop_health("_looks") == (cog.last_run_at, None)
    assert cog.loop_health("something_else") == (None, None)
    assert await kinds(bot.db) == ["pbfeed.look_failed"]


async def test_a_tick_that_blows_up_is_recorded_and_the_next_one_still_runs(
    bot, guild, feed, monkeypatch
):
    cog = PbFeed(bot)

    async def boom(found_guild, now=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(feed, "tick", boom)
    await cog._looks.coro(cog)
    assert cog.last_error == "RuntimeError: boom"

    monkeypatch.undo()
    await cog._looks.coro(cog)
    assert cog.last_error is None


async def test_a_stopped_loop_is_started_again(bot, feed, monkeypatch):
    cog = PbFeed(bot)
    restarted = []
    monkeypatch.setattr(cog._looks, "restart", lambda: restarted.append(True))

    await cog._looks_stopped(RuntimeError("gone"))

    assert restarted == [True] and cog.last_error == "RuntimeError: gone"


async def test_unloading_stops_the_loop_and_closes_the_client(bot, feed, client):
    cog = PbFeed(bot)

    await cog.cog_unload()

    assert client.closed is True and not cog._looks.is_running()


def test_pb_left_the_feed_cog_for_the_leaderboard_and_the_feed_keeps_its_own_mode():
    """2026-10-09, points L2: `/pb` opens the leaderboard; the feed is its sub-panel."""
    assert not hasattr(PbFeed, "pb")
    assert HIDDEN_WHEN_OFF["points_mode"] == ("pb",)
    assert "pb_feed_mode" not in HIDDEN_WHEN_OFF


def test_the_cog_is_thin_and_reads_no_environment():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    }

    assert len(SOURCE.read_text(encoding="utf-8").splitlines()) < 100
    plain = [node for node in ast.walk(tree) if isinstance(node, ast.Import)]
    assert "os" not in {alias.name for node in plain for alias in node.names}
    assert not any("speedrun" in name or "pb_store" in name for name in imported)
