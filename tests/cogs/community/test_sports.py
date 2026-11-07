import asyncio
from datetime import UTC, datetime

from black_bloc import sports_names as names
from black_bloc.bot import COGS
from black_bloc.cogs.community.sports import Sports
from tests.questions_fakes import make_bot
from tests.sports_fakes import Recorded

AT_FOUR = datetime(2026, 11, 6, 11, 5, tzinfo=UTC)
LATER = datetime(2026, 11, 6, 15, 0, tzinfo=UTC)
NEXT_DAY = datetime(2026, 11, 7, 11, 30, tzinfo=UTC)


async def sports_bot(db, monkeypatch):
    bot = await make_bot(db, monkeypatch)
    bot.sports_fetch = Recorded()
    return bot


async def rows(db):
    cur = await db.conn.execute("SELECT COUNT(*) AS n FROM sports_names")
    return int((await cur.fetchone())["n"])


async def refreshed(db):
    cur = await db.conn.execute(
        "SELECT COUNT(*) AS n FROM action_log WHERE kind = 'sports.names_refreshed'"
    )
    return int((await cur.fetchone())["n"])


def test_the_cog_is_loaded_with_the_rest():
    assert "black_bloc.cogs.community.sports" in COGS


async def test_an_empty_cache_is_filled_at_the_first_tick_and_not_again_that_day(db, monkeypatch):
    bot = await sports_bot(db, monkeypatch)
    cog = Sports(bot)
    await cog.reconcile(LATER)
    assert await rows(db) > 0
    assert await refreshed(db) == 1
    await cog.reconcile(LATER)
    assert await refreshed(db) == 1


async def test_a_stale_cache_waits_for_the_hour_then_refreshes_once(db, monkeypatch):
    bot = await sports_bot(db, monkeypatch)
    cog = Sports(bot)
    await cog.reconcile(LATER)
    await db.conn.execute("UPDATE sports_names SET updated_at = '2026-11-06T00:00:00+00:00'")
    await db.conn.commit()
    await cog.reconcile(datetime(2026, 11, 7, 10, 30, tzinfo=UTC))
    assert await refreshed(db) == 1
    await cog.reconcile(NEXT_DAY)
    assert await refreshed(db) == 2


async def test_two_reconciles_at_boot_refresh_once(db, monkeypatch):
    bot = await sports_bot(db, monkeypatch)
    cog = Sports(bot)
    await asyncio.gather(
        cog._reconciles.run(lambda: cog.reconcile(AT_FOUR)),
        cog._reconciles.run(lambda: cog.reconcile(AT_FOUR), skip_if_recent=True),
    )
    assert await refreshed(db) == 1


async def test_the_sweep_leaves_a_refresh_the_website_started(db, monkeypatch):
    bot = await sports_bot(db, monkeypatch)
    cog = Sports(bot)
    task = names.start_refresh(bot, [bot.guild], fetch=bot.sports_fetch)
    await cog.reconcile(AT_FOUR)
    await task
    assert await refreshed(db) == 1


async def test_brackets_off_refreshes_nothing(db, monkeypatch):
    bot = await sports_bot(db, monkeypatch)
    await bot.store.set(bot.guild.id, "brackets_mode", "off")
    await Sports(bot).reconcile(AT_FOUR)
    assert await rows(db) == 0
    assert bot.sports_fetch.asked == []


async def test_the_loop_reports_its_health(db, monkeypatch):
    cog = Sports(await sports_bot(db, monkeypatch))
    assert cog.loop_health("_sweep") == (None, None)
    assert cog.loop_health("other") == (None, None)
