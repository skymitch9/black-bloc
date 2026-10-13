from datetime import timedelta

import pytest

from black_bloc import logkinds
from black_bloc.cogs.content import marathon as cogmod
from black_bloc.cogs.content import marathon_feeds as feeds
from black_bloc.cogs.content.marathon import (
    Marathons,
    get_marathon,
    list_marathons,
    refresh_marathon,
    runs_of,
    set_active,
    update_marathon,
)
from black_bloc.cogs.content.marathon_archive import (
    archive_marathon,
    archived_marathon,
    build_archive,
    restore_marathon,
)
from black_bloc.cogs.content.marathon_stale import try_again
from black_bloc.marathon_sources import ScheduleError
from tests.cogs.content.test_marathon import (  # noqa: F401
    NOW,
    SCHEDULE,
    added,
    bot,
    cog,
)
from tests.cogs.content.test_marathon_feeds import SEPT, FeedClient, later, seeded
from tests.cogs.content.test_spotlight import GUILD, FakeActor, details_of, kinds

READS = "marathon_stale_archive_reads"
HOURS = "marathon_stale_archive_hours"
ARCHIVED = "marathon.stale_archived"
RESTORED = "marathon.stale_restored"
DOWN = ScheduleError("oengus.io answered 401")
NOT_OUT = ScheduleError("not published", unpublished=True)


async def read_at(bot, cog, marathon, hours):  # noqa: F811
    """One due read of the marathon by the tick, `hours` after NOW."""
    cog.clock = lambda: NOW + timedelta(hours=hours)
    await update_marathon(bot.db, marathon["id"], last_fetched_at=None)
    await cog.tick_once()


async def important(bot):  # noqa: F811
    return [kind for kind in await kinds(bot.db) if logkinds.is_important(kind)]


async def test_three_failed_reads_and_a_day_archive_it_as_stale(bot, cog):  # noqa: F811
    marathon = await added(bot, cog)
    cog.client.raises = DOWN
    for hours in (1, 2, 3):
        await read_at(bot, cog, marathon, hours)
    kept = await get_marathon(bot.db, GUILD, marathon["id"])
    assert kept["fetch_failures"] == 3 and kept["stale_clock_at"] == NOW.isoformat()
    assert ARCHIVED not in await kinds(bot.db)

    await read_at(bot, cog, marathon, 23)
    assert (await get_marathon(bot.db, GUILD, marathon["id"]))["fetch_failures"] == 4

    await read_at(bot, cog, marathon, 24)

    assert await get_marathon(bot.db, GUILD, marathon["id"]) is None
    moved = await archived_marathon(bot.db, GUILD, marathon["id"])
    assert (moved["archived_why"], moved["archived_by"]) == ("stale", None)
    assert moved["last_error"] == "oengus.io answered 401" and moved["fetch_failures"] == 5
    assert len(await runs_of(bot.db, marathon["id"])) == 0
    assert (await kinds(bot.db)).count(ARCHIVED) == 1
    assert await details_of(bot.db, ARCHIVED) == {
        "marathon_id": marathon["id"],
        "name": "AGDQ 2027",
        "reason": "oengus.io answered 401",
        "failures": 5,
        "unreadable_since": NOW.isoformat(),
        "hours": 24,
        "via": "discord",
    }
    assert logkinds.is_important(ARCHIVED) and logkinds.is_important(RESTORED)
    assert logkinds.feature_of(ARCHIVED) == "marathon"
    assert (await kinds(bot.db)).count("marathon.schedule_stale") == 1


async def test_the_stale_row_is_logged_while_the_marathon_is_still_on_the_list(
    bot,  # noqa: F811
    cog,  # noqa: F811
    monkeypatch,
):
    marathon = await added(bot, cog)
    await bot.store.set(GUILD, HOURS, 0)
    await bot.store.set(GUILD, READS, 1)
    seen = []
    real = cogmod.log_action

    async def spy(bot, guild, kind, **kwargs):  # noqa: F811
        if kind == ARCHIVED:
            seen.append(await get_marathon(bot.db, GUILD, marathon["id"]) is not None)
        return await real(bot, guild, kind, **kwargs)

    monkeypatch.setattr("black_bloc.cogs.content.marathon_stale.log_action", spy)
    cog.client.raises = DOWN
    await read_at(bot, cog, marathon, 1)
    assert seen == [True]
    assert await get_marathon(bot.db, GUILD, marathon["id"]) is None


async def test_it_moves_by_the_one_archive_path_with_every_knock_on(bot, cog, monkeypatch):  # noqa: F811
    marathon = await added(bot, cog)
    await bot.store.set(GUILD, HOURS, 0)
    called = []

    def spy(name):
        async def one(*args, **kwargs):
            called.append(name)

        return one

    monkeypatch.setattr(
        "black_bloc.cogs.content.marathon_archive.cancel_linked_event", spy("event")
    )
    monkeypatch.setattr(
        "black_bloc.cogs.content.marathon_events.cancel_every_run_event", spy("run events")
    )
    monkeypatch.setattr("black_bloc.cogs.content.marathon_inbox.archived_inbox", spy("inbox"))
    monkeypatch.setattr(
        "black_bloc.cogs.content.marathon_thread_controls.archived_controls", spy("controls")
    )
    cog.client.raises = DOWN
    for hours in (1, 2, 3):
        await read_at(bot, cog, marathon, hours)

    assert called == ["event", "run events", "controls", "inbox"]
    said = await details_of(bot.db, "marathon.archived")
    assert said["archived_why"] == "stale" and said["runs"] == 5
    assert (await kinds(bot.db)).count("marathon.archived") == 1


async def test_reads_alone_do_not_archive_and_hours_alone_do_not(bot, cog):  # noqa: F811
    marathon = await added(bot, cog)
    cog.client.raises = DOWN
    for hours in (1, 2, 3, 4, 5, 6):
        await read_at(bot, cog, marathon, hours)
    assert (await get_marathon(bot.db, GUILD, marathon["id"]))["fetch_failures"] == 6

    cog.client.raises = None
    await read_at(bot, cog, marathon, 7)
    cog.client.raises = DOWN
    await read_at(bot, cog, marathon, 40)
    await read_at(bot, cog, marathon, 41)
    kept = await get_marathon(bot.db, GUILD, marathon["id"])
    assert kept is not None and kept["fetch_failures"] == 2
    assert kept["stale_clock_at"] == (NOW + timedelta(hours=7)).isoformat()
    assert ARCHIVED not in await kinds(bot.db)


async def test_reads_at_zero_never_archives_an_unreadable_marathon(bot, cog):  # noqa: F811
    marathon = await added(bot, cog)
    await bot.store.set(GUILD, READS, 0)
    await bot.store.set(GUILD, HOURS, 0)
    cog.client.raises = DOWN
    for hours in (1, 30, 60, 90):
        await read_at(bot, cog, marathon, hours)
    assert (await get_marathon(bot.db, GUILD, marathon["id"]))["fetch_failures"] == 4
    assert await archived_marathon(bot.db, GUILD, marathon["id"]) is None


async def test_an_unpublished_read_never_counts_and_never_archives(bot, cog):  # noqa: F811
    marathon = await added(bot, cog)
    cog.client.raises = NOT_OUT
    for hours in (1, 30, 60, 90):
        await read_at(bot, cog, marathon, hours)
    kept = await get_marathon(bot.db, GUILD, marathon["id"])
    assert kept["fetch_failures"] == 0
    assert kept["stale_clock_at"] == (NOW + timedelta(hours=90)).isoformat()

    cog.client.raises = DOWN
    for hours in (91, 92, 93):
        await read_at(bot, cog, marathon, hours)
    await update_marathon(
        bot.db, marathon["id"], stale_clock_at=(NOW - timedelta(days=9)).isoformat()
    )
    cog.client.raises = NOT_OUT
    await read_at(bot, cog, marathon, 94)
    kept = await get_marathon(bot.db, GUILD, marathon["id"])
    assert kept is not None and kept["fetch_failures"] == 3
    assert ARCHIVED not in await kinds(bot.db)


async def test_a_row_from_before_the_column_is_not_archived_at_the_first_tick(bot, cog):  # noqa: F811
    marathon = await added(bot, cog)
    await bot.db.conn.execute(
        "UPDATE marathons SET fetch_failures = 3, last_fetch_ok = 0, stale_clock_at = NULL, "
        "added_at = ? WHERE id = ?",
        ((NOW - timedelta(days=60)).isoformat(), marathon["id"]),
    )
    await bot.db.conn.commit()
    cog.client.raises = DOWN

    await read_at(bot, cog, marathon, 1)

    kept = await get_marathon(bot.db, GUILD, marathon["id"])
    assert kept is not None and kept["fetch_failures"] == 4
    assert kept["stale_clock_at"] == (NOW + timedelta(hours=1)).isoformat()
    await read_at(bot, cog, marathon, 24)
    assert await get_marathon(bot.db, GUILD, marathon["id"]) is not None
    await read_at(bot, cog, marathon, 25)
    assert await get_marathon(bot.db, GUILD, marathon["id"]) is None
    assert (await details_of(bot.db, ARCHIVED))["unreadable_since"] == kept["stale_clock_at"]


async def test_a_paused_or_ignored_marathon_is_never_archived_by_the_rule(bot, cog):  # noqa: F811
    marathon = await added(bot, cog)
    await bot.store.set(GUILD, HOURS, 0)
    await bot.store.set(GUILD, READS, 1)
    await bot.db.conn.execute(
        "UPDATE marathons SET ignored_at = ?, tracked_at = NULL WHERE id = ?",
        (NOW.isoformat(), marathon["id"]),
    )
    await bot.db.conn.commit()
    cog.client.raises = DOWN
    await read_at(bot, cog, marathon, 1)
    kept = await get_marathon(bot.db, GUILD, marathon["id"])
    assert kept is not None and kept["fetch_failures"] == 1

    await bot.db.conn.execute(
        "UPDATE marathons SET ignored_at = NULL, active = 0 WHERE id = ?", (marathon["id"],)
    )
    await bot.db.conn.commit()
    await read_at(bot, cog, marathon, 2)
    kept = await get_marathon(bot.db, GUILD, marathon["id"])
    assert kept is not None and kept["fetch_failures"] == 1


async def test_a_staff_read_that_fails_archives_nothing(bot, cog):  # noqa: F811
    marathon = await added(bot, cog)
    await bot.store.set(GUILD, HOURS, 0)
    await bot.store.set(GUILD, READS, 1)
    cog.client.raises = DOWN
    read = await refresh_marathon(bot, bot.guild, marathon)
    assert not read.ok
    assert (await get_marathon(bot.db, GUILD, marathon["id"]))["fetch_failures"] == 1


async def test_resume_restarts_the_clock(bot, cog):  # noqa: F811
    marathon = await added(bot, cog)
    assert marathon["stale_clock_at"] == NOW.isoformat()
    cog.clock = lambda: NOW + timedelta(days=2)
    await set_active(bot, bot.guild, FakeActor(), marathon, False)
    assert (await get_marathon(bot.db, GUILD, marathon["id"]))["stale_clock_at"] == NOW.isoformat()
    cog.clock = lambda: NOW + timedelta(days=3)
    await set_active(bot, bot.guild, FakeActor(), marathon, True)
    kept = await get_marathon(bot.db, GUILD, marathon["id"])
    assert kept["stale_clock_at"] == (NOW + timedelta(days=3)).isoformat()


async def staled(bot, cog, marathon):  # noqa: F811
    cog.client.raises = DOWN
    for hours in (1, 2, 30):
        await read_at(bot, cog, marathon, hours)
    assert (await archived_marathon(bot.db, GUILD, marathon["id"]))["archived_why"] == "stale"


async def test_staff_restore_clears_the_mark_and_restarts_the_clock(bot, cog):  # noqa: F811
    marathon = await added(bot, cog)
    await staled(bot, cog, marathon)
    cog.clock = lambda: NOW + timedelta(hours=40)

    done = await restore_marathon(bot, bot.guild, FakeActor(), marathon["id"])

    assert done.ok
    back = await get_marathon(bot.db, GUILD, marathon["id"])
    assert (back["active"], back["fetch_failures"]) == (0, 0)
    assert back["stale_clock_at"] == (NOW + timedelta(hours=40)).isoformat()
    assert await archived_marathon(bot.db, GUILD, marathon["id"]) is None
    assert RESTORED not in await kinds(bot.db)
    assert (await details_of(bot.db, "marathon.restored"))["archived_why"] == "stale"

    await set_active(bot, bot.guild, FakeActor(), back, True)
    for hours in (41, 42, 43, 63):
        await read_at(bot, cog, marathon, hours)
    kept = await get_marathon(bot.db, GUILD, marathon["id"])
    assert kept is not None and kept["fetch_failures"] == 4
    await read_at(bot, cog, marathon, 64)
    assert (await archived_marathon(bot.db, GUILD, marathon["id"]))["archived_why"] == "stale"
    assert (await kinds(bot.db)).count(ARCHIVED) == 2


async def test_a_hand_archive_restored_keeps_its_count_and_restarts_the_clock(bot, cog):  # noqa: F811
    marathon = await added(bot, cog)
    await bot.store.set(GUILD, HOURS, 100)
    cog.client.raises = DOWN
    for hours in (1, 2, 3):
        await read_at(bot, cog, marathon, hours)
    await archive_marathon(
        bot, bot.guild, FakeActor(), await get_marathon(bot.db, GUILD, marathon["id"])
    )
    cog.clock = lambda: NOW + timedelta(days=5)
    await restore_marathon(bot, bot.guild, FakeActor(), marathon["id"])
    back = await get_marathon(bot.db, GUILD, marathon["id"])
    assert back["fetch_failures"] == 3
    assert back["stale_clock_at"] == (NOW + timedelta(days=5)).isoformat()


async def test_the_archive_card_says_the_stale_word_from_its_setting(bot, cog):  # noqa: F811
    marathon = await added(bot, cog)
    await staled(bot, cog, marathon)
    embed, view = await build_archive(bot, bot.guild)
    assert "· could not be read <t:" in embed.description
    assert view.children[0].options[0].description == "could not be read"
    await bot.store.set(GUILD, "marathon_archived_stale_word", "schedule went away")
    embed, _ = await build_archive(bot, bot.guild)
    assert "· schedule went away <t:" in embed.description


# --- the feed lists it again ------------------------------------------------------------------


class Flaky(FeedClient):
    def __init__(self):
        super().__init__()
        self.down = {}
        self.read = []

    async def runs(self, source, ref, **asked):
        self.read.append((source, str(ref)))
        if (source, str(ref)) in self.down:
            raise self.down[(source, str(ref))]
        return await super().runs(source, ref, **asked)


@pytest.fixture
def feed_cog(bot):  # noqa: F811
    made = Marathons(bot)
    made.client = Flaky()
    made.clock = lambda: SEPT
    bot.cogs[cogmod.COG_NAME] = made
    return made


async def agdq_of(bot):  # noqa: F811
    return next(one for one in await list_marathons(bot.db, GUILD) if one["source_ref"] == "74")


async def stale_from_the_feed(bot, feed_cog):  # noqa: F811
    """AGDQ (gdq 74), added by the GDQ feed, then archived for staleness."""
    await seeded(bot, feed_cog)
    await feed_cog.tick_once()
    agdq = await agdq_of(bot)
    feed_cog.client.down[("gdq", "74")] = DOWN
    for hours in (25, 26, 27):
        later(feed_cog, hours)
        await update_marathon(bot.db, agdq["id"], last_fetched_at=None)
        async with feed_cog.lock(agdq["id"]):
            await feed_cog.tick_marathon(
                bot.guild, await get_marathon(bot.db, GUILD, agdq["id"])
            )
    assert (await archived_marathon(bot.db, GUILD, agdq["id"]))["archived_why"] == "stale"
    return agdq


async def test_a_listed_stale_marathon_is_restored_once_by_a_read_that_works(bot, feed_cog):  # noqa: F811
    agdq = await stale_from_the_feed(bot, feed_cog)
    del feed_cog.client.down[("gdq", "74")]
    feed_cog.client.runs_by_ref[("gdq", "74")] = SCHEDULE
    feed_cog.client.read.clear()

    later(feed_cog, 40)
    await feed_cog.tick_once()

    back = await get_marathon(bot.db, GUILD, agdq["id"])
    assert (back["active"], back["fetch_failures"], back["last_fetch_ok"]) == (1, 0, 1)
    assert back["last_error"] is None
    assert back["stale_clock_at"] == (SEPT + timedelta(hours=40)).isoformat()
    assert len(await runs_of(bot.db, agdq["id"])) == 5
    assert await archived_marathon(bot.db, GUILD, agdq["id"]) is None
    assert feed_cog.client.read.count(("gdq", "74")) == 1
    assert await details_of(bot.db, RESTORED) == {
        "marathon_id": agdq["id"],
        "name": agdq["name"],
        "runs": 5,
        "via": "discord",
    }
    assert (await details_of(bot.db, "marathon.restored"))["archived_why"] == "stale"
    cur = await bot.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = 'marathon.feed_checked' "
        "AND details LIKE '%\"stale_restored\": 1%'"
    )
    assert len(await cur.fetchall()) == 1

    later(feed_cog, 80)
    await feed_cog.tick_once()
    logged = await kinds(bot.db)
    assert logged.count(RESTORED) == logged.count("marathon.restored") == 1
    names = [one["name"] for one in await list_marathons(bot.db, GUILD)]
    assert names.count(agdq["name"]) == 1


async def test_three_polls_of_a_still_failing_source_restore_nothing(bot, feed_cog):  # noqa: F811
    agdq = await stale_from_the_feed(bot, feed_cog)
    before = await important(bot)
    feed_cog.client.read.clear()

    for hours in (40, 50, 60):
        later(feed_cog, hours)
        await feed_cog.tick_once()

    assert feed_cog.client.read.count(("gdq", "74")) == 3
    assert await get_marathon(bot.db, GUILD, agdq["id"]) is None
    assert (await archived_marathon(bot.db, GUILD, agdq["id"]))["archived_why"] == "stale"
    assert await important(bot) == before
    logged = await kinds(bot.db)
    assert logged.count(RESTORED) == logged.count("marathon.restored") == 0
    assert logged.count(ARCHIVED) == 1


async def test_an_unpublished_trial_read_leaves_it_archived(bot, feed_cog):  # noqa: F811
    agdq = await stale_from_the_feed(bot, feed_cog)
    feed_cog.client.down[("gdq", "74")] = NOT_OUT
    later(feed_cog, 40)
    await feed_cog.tick_once()
    assert await get_marathon(bot.db, GUILD, agdq["id"]) is None
    assert RESTORED not in await kinds(bot.db)


async def test_a_hand_archived_marathon_is_never_read_or_restored_by_the_poll(bot, feed_cog):  # noqa: F811
    await seeded(bot, feed_cog)
    await feed_cog.tick_once()
    agdq = await agdq_of(bot)
    await archive_marathon(bot, bot.guild, FakeActor(), agdq)
    feed_cog.client.read.clear()

    for hours in (10, 20, 30):
        later(feed_cog, hours)
        await feed_cog.tick_once()

    assert ("gdq", "74") not in feed_cog.client.read
    assert await get_marathon(bot.db, GUILD, agdq["id"]) is None
    assert (await archived_marathon(bot.db, GUILD, agdq["id"]))["archived_why"] == "staff"
    assert await try_again(bot, bot.guild, agdq["id"]) is False
    assert "74" not in {one["source_ref"] for one in await list_marathons(bot.db, GUILD)}


async def test_a_stale_marathon_no_feed_lists_stays_archived(bot, cog):  # noqa: F811
    marathon = await added(bot, cog)
    await staled(bot, cog, marathon)
    cog.client.raises = None
    for hours in (60, 90, 120):
        cog.clock = lambda hours=hours: NOW + timedelta(hours=hours)
        await cog.tick_once()
    assert await get_marathon(bot.db, GUILD, marathon["id"]) is None


async def test_the_poll_tells_a_stale_archive_from_a_hand_archive(bot, feed_cog):  # noqa: F811
    agdq = await stale_from_the_feed(bot, feed_cog)
    known = await feeds.marathons_by_ref(bot.db, GUILD, "gdq")
    assert (known["74"]["archived"], known["74"]["archived_why"]) == (1, "stale")
    assert known["74"]["id"] == agdq["id"]
    live = next(row for row in known.values() if not row["archived"])
    assert live["archived_why"] is None
