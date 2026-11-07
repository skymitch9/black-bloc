# ruff: noqa: F401, F811
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from black_bloc import brackets_moves as moves
from black_bloc import brackets_sports as sports
from black_bloc import brackets_sports_sync as live
from black_bloc import brackets_store as store_
from black_bloc import brackets_thread as thread_
from black_bloc.sports import feeds
from black_bloc.sports.model import NHL_API, failed
from tests.test_brackets_moves import GUILD, TO, bot, guild, rows, who
from tests.test_brackets_sports import NHL_ROUTES, imported, nhl_answer, running

NOW = datetime(2026, 4, 20, 18, 0, tzinfo=UTC)


class Calls:
    def __init__(self, answer):
        self.answer = answer
        self.asked: list[tuple[str, str]] = []

    async def __call__(self, league, season, *, fetch=None):
        self.asked.append((league, season))
        return self.answer


def watch(monkeypatch, answer):
    calls = Calls(answer)
    monkeypatch.setattr(feeds, "bracket", calls)
    carded: list[tuple[int, tuple]] = []

    async def cards(bot, guild, row, *, keys=None, **_):
        carded.append((row["id"], keys))

    monkeypatch.setattr(thread_, "sync", cards)
    return calls, carded


async def test_one_feed_call_per_league_and_season_covers_every_bracket_of_it(
    bot, guild, monkeypatch
):
    first, second = await running(bot, guild), await running(bot, guild)
    calls, carded = watch(monkeypatch, nhl_answer())
    owed = await live.sweep(bot, guild, {}, NOW)
    assert calls.asked == [("nhl", "2025-26")]
    assert set(owed) == {first, second}
    assert {one for one, _ in carded} == {first, second}
    assert (await store_.tournament(bot.db, GUILD, first))["feed_ok_at"]


async def test_the_poller_waits_the_idle_minutes_unless_a_set_is_live_or_soon(
    bot, guild, monkeypatch
):
    tid = await running(bot, guild)
    calls, _ = watch(monkeypatch, nhl_answer())
    last: dict = {}
    await live.sweep(bot, guild, last, NOW)
    await live.sweep(bot, guild, last, NOW + timedelta(minutes=5))
    assert len(calls.asked) == 1
    await live.sweep(bot, guild, last, NOW + timedelta(minutes=61))
    assert len(calls.asked) == 2
    await bot.db.conn.execute(
        "UPDATE tournament_sets SET state = 'ready', live_status = 'scheduled', scheduled_at = ? "
        "WHERE tournament_id = ? AND key = 'W1-1'",
        ((NOW + timedelta(minutes=70)).isoformat(), tid),
    )
    await bot.db.conn.commit()
    await live.sweep(bot, guild, last, NOW + timedelta(minutes=62))
    assert len(calls.asked) == 3
    await live.sweep(bot, guild, last, NOW + timedelta(minutes=62, seconds=30))
    assert len(calls.asked) == 3


async def test_nothing_is_read_while_brackets_are_off_or_nothing_runs_with_a_feed(
    bot, guild, monkeypatch
):
    calls, _ = watch(monkeypatch, nhl_answer())
    await imported(bot, guild)
    before = len(calls.asked)
    assert await live.sweep(bot, guild, {}, NOW) == {}
    await running(bot, guild)
    await bot.store.set(GUILD, "brackets_mode", "off")
    before = len(calls.asked)
    assert await live.sweep(bot, guild, {}, NOW) == {}
    assert len(calls.asked) == before


async def test_a_failing_feed_redraws_the_starter_once_as_it_goes_down(bot, guild, monkeypatch):
    tid = await running(bot, guild)
    down = failed("NHL did not answer in time for the 2026 playoff bracket", NHL_API)
    calls, carded = watch(monkeypatch, down)
    await live.sweep(bot, guild, {}, NOW)
    await live.sweep(bot, guild, {}, NOW)
    assert carded == [(tid, ())]
    kinds = [kind for kind, *_ in await rows(bot.db)]
    assert kinds.count("brackets.feed_failed") == 1
