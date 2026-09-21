from __future__ import annotations

import asyncio

from black_bloc import restart
from black_bloc.errors import EXIT_RESTART


class FakeBot:
    def __init__(self, raises: Exception | None = None, hangs: bool = False) -> None:
        self.closed = False
        self.codes: list[int] = []
        self.raises = raises
        self.hangs = hangs

    async def close(self) -> None:
        if self.hangs:
            await asyncio.sleep(3600)
        self.closed = True
        if self.raises is not None:
            raise self.raises

    def exit_now(self, code: int) -> None:
        self.codes.append(code)


def test_only_a_bot_with_a_way_out_may_be_restarted():
    assert restart.can_restart(FakeBot()) is True
    assert restart.can_restart(object()) is False


def test_manage_server_is_the_permission_and_not_a_role_name():
    class Perms:
        def __init__(self, manage_guild):
            self.manage_guild = manage_guild

    class Member:
        def __init__(self, manage_guild):
            self.guild_permissions = Perms(manage_guild)

    assert restart.manages_guild(Member(True)) is True
    assert restart.manages_guild(Member(False)) is False
    assert restart.manages_guild(None) is False


def test_the_sentence_names_how_long_the_site_is_down():
    assert str(restart.DOWN_SECONDS) in restart.restarting_said()


async def test_the_shutdown_closes_cleanly_then_exits_non_zero():
    """A clean exit does NOT restart on Fly (policy on-failure, 10 retries), so the code
    must be non-zero or the button takes the bot down and leaves it down."""
    bot = FakeBot()

    await restart.shut_down(bot, grace=0)

    assert bot.closed is True
    assert bot.codes == [EXIT_RESTART]
    assert EXIT_RESTART != 0


async def test_a_shutdown_that_raises_still_exits():
    bot = FakeBot(raises=RuntimeError("the gateway was already gone"))

    await restart.shut_down(bot, grace=0)

    assert bot.codes == [EXIT_RESTART]


async def test_a_shutdown_that_hangs_still_exits():
    bot = FakeBot(hangs=True)

    await restart.shut_down(bot, grace=0, close_timeout=0.01)

    assert bot.closed is False
    assert bot.codes == [EXIT_RESTART]


async def test_the_task_is_kept_so_it_cannot_be_collected_mid_shutdown():
    bot = FakeBot()

    task = restart.schedule(bot, grace=0)

    assert getattr(bot, restart.TASK_ATTR) is task
    await task
    assert bot.codes == [EXIT_RESTART]
