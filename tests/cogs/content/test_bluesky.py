import ast
import pathlib
from datetime import timedelta

import pytest

from black_bloc.cogs.content import bluesky as cog_module
from black_bloc.cogs.content.bluesky import Bluesky
from tests.bluesky_fakes import HOME, NOW, make_bot

SOURCE = pathlib.Path(cog_module.__file__)


@pytest.fixture
async def bot(db, monkeypatch):
    return await make_bot(db, monkeypatch)


async def test_run_once_reads_every_server_and_skips_one_discord_has_lost(bot):
    cog = Bluesky(bot)

    await cog.run_once(NOW)
    bot.guild.unavailable = True
    await cog.run_once(NOW + timedelta(minutes=10))

    assert len(bot.guild.get_channel(HOME).sent) == 1
    assert len(bot.bluesky_fetch.urls) == 1


async def test_a_tick_that_blows_up_is_recorded_and_the_next_one_still_runs(bot, monkeypatch):
    cog = Bluesky(bot)

    async def boom(found_bot, guild, now=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(cog_module, "tick", boom)
    await cog._reads.coro(cog)
    assert cog.last_error == "RuntimeError: boom"

    monkeypatch.undo()
    await cog._reads.coro(cog)
    assert cog.last_error is None and cog.last_run_at is not None
    assert cog.loop_health("_reads") == (cog.last_run_at, None)
    assert cog.loop_health("other") == (None, None)


async def test_a_stopped_loop_is_started_again(bot, monkeypatch):
    cog = Bluesky(bot)
    restarted = []
    monkeypatch.setattr(cog._reads, "restart", lambda: restarted.append(True))

    await cog._reads_stopped(RuntimeError("gone"))

    assert restarted == [True] and cog.last_error == "RuntimeError: gone"


async def test_unloading_stops_the_loop(bot):
    cog = Bluesky(bot)

    await cog.cog_unload()

    assert not cog._reads.is_running()


def test_the_cog_is_thin_has_no_command_and_reads_no_environment():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    plain = [node for node in ast.walk(tree) if isinstance(node, ast.Import)]

    assert len(SOURCE.read_text(encoding="utf-8").splitlines()) < 80
    assert "os" not in {alias.name for node in plain for alias in node.names}
    assert "app_commands" not in SOURCE.read_text(encoding="utf-8")
