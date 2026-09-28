from types import SimpleNamespace

from black_bloc.cogs.community.live_blocks import TICK_MINUTES, LiveBlocks, keeper_of


class Store:
    def __init__(self, **saved):
        self.saved = saved

    def get(self, guild_id, key):
        return self.saved.get(key)


class Door:
    def __init__(self):
        self.kept = []

    async def keep_live_now(self, guild):
        self.kept.append(guild.id)
        return True


def a_bot(door=None, guilds=(), **saved):
    cogs = {"FrontDoor": door} if door is not None else {}
    return SimpleNamespace(
        store=Store(**saved),
        guilds=list(guilds),
        db=SimpleNamespace(is_connected=True),
        get_cog=cogs.get,
    )


def test_the_loop_ticks_every_minute_and_reports_its_own_health():
    cog = LiveBlocks(a_bot())

    assert TICK_MINUTES == 1
    assert cog.loop_health("_live_loop") == (None, None)
    assert cog.loop_health("something_else") == (None, None)


async def test_without_the_door_cog_there_is_no_lock_so_nothing_is_redrawn():
    cog = LiveBlocks(a_bot(guilds=[SimpleNamespace(id=1)]))

    assert keeper_of(cog.bot) is None
    assert await cog.sweep(at=0) == 0


async def test_each_guild_is_looked_at_once_per_its_own_interval():
    door = Door()
    one, two = SimpleNamespace(id=1), SimpleNamespace(id=2, unavailable=True)
    cog = LiveBlocks(a_bot(door, [one, two], posts_block_live_minutes=5))

    assert await cog.sweep(at=1000) == 1
    assert await cog.sweep(at=1060) == 0
    assert await cog.sweep(at=1300) == 1

    assert door.kept == [1, 1]
    assert cog.last_ok_at is not None


async def test_a_stopped_loop_records_why_and_starts_again(monkeypatch):
    cog = LiveBlocks(a_bot())
    restarted = []
    monkeypatch.setattr(cog._live_loop, "restart", lambda: restarted.append(True))

    await cog._live_error(RuntimeError("boom"))

    assert cog.last_error == "RuntimeError: boom" and restarted == [True]
