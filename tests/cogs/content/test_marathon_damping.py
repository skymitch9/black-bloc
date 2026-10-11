# ruff: noqa: F401, F811
from datetime import timedelta

import pytest

from black_bloc import marathon as mt
from black_bloc import marathon_damping as md
from black_bloc import marathon_reminder_posts as mrem
from black_bloc.cogs.content import marathon_damping as damping
from black_bloc.cogs.content import marathon_retime as retime
from black_bloc.cogs.content import marathon_signals as signals
from black_bloc.cogs.content.marathon import get_marathon, update_run
from tests.cogs.content.test_marathon import NOW, SKY, a_run, at, bot, cog, threading
from tests.cogs.content.test_marathon_host_highlights import DAY, heads_ups, tick_at
from tests.cogs.content.test_marathon_public import ready
from tests.cogs.content.test_marathon_public_reminders import reminders_in
from tests.cogs.content.test_marathon_reminder_posts import (
    GAME,
    block_reads,
    host_show,
    host_words,
    message_of,
    tomorrow,
    words,
)
from tests.cogs.content.test_marathon_role_ping import rows
from tests.cogs.content.test_marathon_runner_posts import (
    SKY_RUN,
    events_room,
    follow,
    fresh,
    run_of,
    runner_posts,
    the_thread,
)
from tests.cogs.content.test_marathon_signals import (
    HAMTARO,
    KIRBY,
    SETUP_KEY,
    SPYRO,
    WARIO,
    at_show,
    gdqueer,
    gdqueer_runs,
    helix,
    tick,
    times,
    z,
)
from tests.cogs.content.test_spotlight import CHANNEL, GUILD, FakeActor, kinds

FAR = 1430
MINUTES = "marathon_move_damping_minutes"
READS = "marathon_move_damping_reads"
MOVED = "marathon.member_run_moved"
EDITED = "marathon.reminder_edited"
HELD = "marathon.move_held"
NOTHING_WAITS = (None, None, None, None)


@pytest.fixture(autouse=True)
async def both_copies(bot):
    await bot.store.set(GUILD, "marathon_thread_reminders", True)


def day(start):
    return [
        a_run(1, 1300, game="Opener"),
        a_run(3, start, game=GAME, people=SKY_RUN),
        a_run(4, 1700, game="Closer"),
    ]


async def far_day(bot, cog, *, start=FAR, marks="1440", stale=240):
    """Sky's run a day away, its 24-hour reminder already posted in both places."""
    await bot.store.set(GUILD, "marathon_reminder_minutes", marks)
    await bot.store.set(GUILD, "marathon_reminder_stale_minutes", stale)
    await bot.store.set(GUILD, "marathon_ping_minutes", 0)
    cog.client.runs_given = day(start)
    return await ready(bot, cog)


async def read(bot, cog, marathon, minute, start, *, runs=None):
    """One read of the schedule at `minute`, then the minute's tick."""
    cog.clock = lambda: NOW + timedelta(minutes=minute)
    cog.client.runs_given = day(start) if runs is None else runs
    found = await cog.refresh(bot.guild, await fresh(bot, marathon))
    assert found.ok, found.message
    await follow(bot, cog, marathon)


async def copies(bot, marathon, mark=1440):
    found = mrem.of_run(await run_of(bot, marathon, GAME))[mark]
    return (message_of(bot, found["public"]), message_of(bot, found["staff"]))


async def waiting(bot, marathon, game=GAME):
    row = await run_of(bot, marathon, game)
    return tuple(row[one] for one in md.COLUMNS)


# --- the hour of 2026-10-11 ----------------------------------------------------------------------


async def test_a_wrong_start_put_right_on_the_next_read_edits_nothing_and_logs_no_move(bot, cog):
    marathon = await far_day(bot, cog)
    public, staff = await copies(bot, marathon)
    assert public.content == staff.content == words(FAR)

    await read(bot, cog, marathon, 1, FAR - 64)

    row = await run_of(bot, marathon, GAME)
    assert row["scheduled_at"] == at(FAR - 64) and row["previous_scheduled_at"] == at(FAR)
    assert await waiting(bot, marathon) == (at(FAR), at(FAR + 60), at(FAR - 64), 1)
    assert (await rows(bot, "marathon.schedule_changed"))[-1]["moved"] == 1
    (held,) = await rows(bot, HELD)
    assert (held["published"], held["candidate"], held["reads_needed"]) == (
        at(FAR),
        at(FAR - 64),
        2,
    )
    assert (held["run_id"], held["game"], held["marathon_id"]) == (row["id"], GAME, marathon["id"])

    await read(bot, cog, marathon, 2, FAR)

    assert public.edits == [] and staff.edits == []
    assert public.content == staff.content == words(FAR)
    seen = await kinds(bot.db)
    assert MOVED not in seen and EDITED not in seen and seen.count(HELD) == 1
    assert (await run_of(bot, marathon, GAME))["scheduled_at"] == at(FAR)
    assert await waiting(bot, marathon) == NOTHING_WAITS


async def test_a_corrected_start_that_holds_is_one_edit_and_one_moved_row(bot, cog):
    marathon = await far_day(bot, cog)
    public, staff = await copies(bot, marathon)

    await read(bot, cog, marathon, 1, FAR - 64)
    await read(bot, cog, marathon, 2, FAR - 10)
    assert public.edits == [] and MOVED not in await kinds(bot.db)
    await read(bot, cog, marathon, 3, FAR - 10)

    assert public.content == staff.content == words(FAR - 10)
    assert len(public.edits) == len(staff.edits) == 1
    (moved,) = await rows(bot, MOVED)
    assert (moved["from"], moved["to"], moved["member_id"]) == (at(FAR), at(FAR - 10), SKY)
    assert [(one["copy"], one["from"], one["to"]) for one in await rows(bot, EDITED)] == [
        ("public", at(FAR), at(FAR - 10)),
        ("staff", at(FAR), at(FAR - 10)),
    ]
    assert await waiting(bot, marathon) == NOTHING_WAITS


async def test_the_four_moves_of_run_63_are_two_edits_and_one_moved_row(bot, cog):
    marathon = await far_day(bot, cog)
    public, _staff = await copies(bot, marathon)
    said = []

    for minute, start in enumerate(
        (FAR - 64, FAR - 4, FAR - 4, FAR + 88, FAR + 38, FAR + 38), start=1
    ):
        await read(bot, cog, marathon, minute, start)
        assert (await run_of(bot, marathon, GAME))["scheduled_at"] == at(start)
        said.append(public.content)

    assert said == [words(FAR)] * 2 + [words(FAR - 4)] * 3 + [words(FAR + 38)]
    assert len(public.edits) == 2
    assert [(one["from"], one["to"]) for one in await rows(bot, MOVED)] == [
        (at(FAR - 4), at(FAR + 38))
    ]


async def test_a_move_under_the_moved_threshold_waits_too_and_leaves_no_held_row(bot, cog):
    marathon = await far_day(bot, cog)
    public, _staff = await copies(bot, marathon)

    await read(bot, cog, marathon, 1, FAR + 3)
    assert public.edits == [] and (await waiting(bot, marathon))[3] == 1
    await read(bot, cog, marathon, 2, FAR + 3)

    assert public.content == words(FAR + 3) and len(public.edits) == 1
    seen = await kinds(bot.db)
    assert HELD not in seen and MOVED not in seen


# --- the keys ------------------------------------------------------------------------------------


async def test_three_reads_are_asked_for_when_the_key_says_three(bot, cog):
    await bot.store.set(GUILD, READS, 3)
    marathon = await far_day(bot, cog)
    public, _staff = await copies(bot, marathon)

    await read(bot, cog, marathon, 1, FAR - 64)
    await read(bot, cog, marathon, 2, FAR - 64)
    assert public.edits == [] and MOVED not in await kinds(bot.db)
    assert (await rows(bot, HELD))[0]["reads_needed"] == 3
    await read(bot, cog, marathon, 3, FAR - 64)

    assert public.content == words(FAR - 64) and len(public.edits) == 1
    assert len(await rows(bot, MOVED)) == 1 and len(await rows(bot, HELD)) == 1


async def test_a_wrong_start_that_stood_two_reads_of_three_goes_back_unseen(bot, cog):
    await bot.store.set(GUILD, READS, 3)
    marathon = await far_day(bot, cog)
    public, staff = await copies(bot, marathon)

    for minute, start in ((1, FAR - 64), (2, FAR - 64), (3, FAR)):
        await read(bot, cog, marathon, minute, start)

    assert public.edits == [] and staff.edits == []
    assert MOVED not in await kinds(bot.db)


async def test_a_candidate_that_changes_is_counted_from_the_start_again(bot, cog):
    await bot.store.set(GUILD, READS, 3)
    marathon = await far_day(bot, cog)
    public, _staff = await copies(bot, marathon)

    for minute, start in ((1, FAR - 64), (2, FAR - 64), (3, FAR - 20), (4, FAR - 20)):
        await read(bot, cog, marathon, minute, start)
    assert public.edits == []
    assert await waiting(bot, marathon) == (at(FAR), at(FAR + 60), at(FAR - 20), 2)
    await read(bot, cog, marathon, 5, FAR - 20)

    assert public.content == words(FAR - 20) and len(public.edits) == 1
    assert [(one["from"], one["to"]) for one in await rows(bot, MOVED)] == [
        (at(FAR), at(FAR - 20))
    ]


async def test_damping_minutes_zero_follows_the_first_read_as_before(bot, cog):
    await bot.store.set(GUILD, MINUTES, 0)
    marathon = await far_day(bot, cog)
    public, staff = await copies(bot, marathon)

    await read(bot, cog, marathon, 1, FAR - 64)

    assert public.content == staff.content == words(FAR - 64)
    assert len(public.edits) == len(staff.edits) == 1
    (moved,) = await rows(bot, MOVED)
    assert (moved["from"], moved["to"]) == (at(FAR), at(FAR - 64))
    assert HELD not in await kinds(bot.db)
    assert await waiting(bot, marathon) == NOTHING_WAITS


async def test_a_run_inside_the_window_follows_the_first_read(bot, cog):
    marathon = await far_day(bot, cog, start=50, marks="15")
    cog.clock = lambda: NOW + timedelta(minutes=36)
    await follow(bot, cog, marathon)
    public, staff = await copies(bot, marathon, 15)

    await read(bot, cog, marathon, 37, 70)

    assert public.content == staff.content == words(70)
    assert len(await rows(bot, MOVED)) == 1 and HELD not in await kinds(bot.db)
    assert await waiting(bot, marathon) == NOTHING_WAITS


async def test_a_far_run_read_into_the_window_follows_at_once(bot, cog):
    marathon = await far_day(bot, cog)
    public, _staff = await copies(bot, marathon)

    await read(bot, cog, marathon, 1, 45)

    assert public.content == words(45) and len(public.edits) == 1
    assert [(one["from"], one["to"]) for one in await rows(bot, MOVED)] == [(at(FAR), at(45))]
    assert await waiting(bot, marathon) == NOTHING_WAITS


async def test_a_run_that_comes_inside_the_window_while_its_move_waits_is_published(bot, cog):
    await bot.store.set(GUILD, MINUTES, 1400)
    await bot.store.set(GUILD, READS, 5)
    marathon = await far_day(bot, cog)
    public, staff = await copies(bot, marathon)
    await read(bot, cog, marathon, 1, FAR - 10)
    assert public.edits == [] and (await waiting(bot, marathon))[0] == at(FAR)

    cog.clock = lambda: NOW + timedelta(minutes=25)
    await follow(bot, cog, marathon)

    assert public.content == staff.content == words(FAR - 10)
    assert len(public.edits) == len(staff.edits) == 1
    assert [(one["from"], one["to"]) for one in await rows(bot, MOVED)] == [
        (at(FAR), at(FAR - 10))
    ]
    assert await waiting(bot, marathon) == NOTHING_WAITS


# --- rows from before the columns ----------------------------------------------------------------


async def test_rows_with_nothing_published_yet_edit_nothing_on_the_first_ticks_and_reads(bot, cog):
    marathon = await far_day(bot, cog)
    public, staff = await copies(bot, marathon)
    assert await waiting(bot, marathon) == NOTHING_WAITS

    for minute in (1, 2, 3):
        await read(bot, cog, marathon, minute, FAR)

    assert public.edits == [] and staff.edits == []
    seen = await kinds(bot.db)
    assert MOVED not in seen and EDITED not in seen and HELD not in seen
    assert await waiting(bot, marathon) == NOTHING_WAITS


# --- a reminder that comes due while a move waits ------------------------------------------------


async def test_a_mark_due_by_the_stored_start_fires_once_while_the_move_waits(bot, cog):
    await bot.store.set(GUILD, READS, 3)
    marathon = await far_day(bot, cog, start=200, marks="120")
    assert reminders_in(bot.guild.channels[CHANNEL]) == []
    await read(bot, cog, marathon, 1, 170)
    assert reminders_in(bot.guild.channels[CHANNEL]) == []

    cog.clock = lambda: NOW + timedelta(minutes=50)
    await follow(bot, cog, marathon)

    (public,) = reminders_in(bot.guild.channels[CHANNEL])
    assert public.content == words(200)
    assert mt.marks_of(await run_of(bot, marathon, GAME)) == [120]

    await read(bot, cog, marathon, 51, 170)
    await read(bot, cog, marathon, 52, 170)
    for minute in (79, 80, 81):
        cog.clock = lambda minute=minute: NOW + timedelta(minutes=minute)
        await follow(bot, cog, marathon)

    assert reminders_in(bot.guild.channels[CHANNEL]) == [public]
    assert public.content == words(170) and len(public.edits) == 1
    assert len(reminders_in(the_thread(bot))) == 1
    assert len(await rows(bot, "marathon.public_reminded")) == 1


async def test_a_mark_skipped_as_late_under_a_wrong_start_is_due_again_once_it_goes_back(bot, cog):
    marathon = await far_day(bot, cog, start=200, marks="120", stale=30)

    await read(bot, cog, marathon, 1, 85)
    assert mt.marks_of(await run_of(bot, marathon, GAME)) == [120]
    assert len(await rows(bot, "marathon.reminder_skipped")) == 1
    await read(bot, cog, marathon, 2, 200)
    assert mt.marks_of(await run_of(bot, marathon, GAME)) == []

    for minute in (79, 80, 81):
        cog.clock = lambda minute=minute: NOW + timedelta(minutes=minute)
        await follow(bot, cog, marathon)

    (public,) = reminders_in(bot.guild.channels[CHANNEL])
    assert public.content == words(200) and public.edits == []
    assert MOVED not in await kinds(bot.db)


# --- the other posts that print the start --------------------------------------------------------


async def test_the_runs_own_post_waits_with_the_reminder(bot, cog):
    marathon = await far_day(bot, cog)
    (post,) = runner_posts(the_thread(bot), GAME)
    before = post.content
    assert mt.stamp_of(at(FAR), "f") in before

    await read(bot, cog, marathon, 1, FAR - 64)
    assert post.content == before
    await read(bot, cog, marathon, 2, FAR - 64)

    assert mt.stamp_of(at(FAR - 64), "f") in post.content


async def test_a_host_blocks_heads_up_waits_with_its_first_run(bot, cog):
    marathon = await host_show(bot, cog, until=(60,))
    (said,) = heads_ups(bot)

    await block_reads(bot, cog, marathon, tomorrow(10), 61)
    assert said.edits == [] and said.content.startswith(host_words(DAY))
    await block_reads(bot, cog, marathon, tomorrow(10), 62)

    assert len(said.edits) == 1 and said.content.startswith(host_words(DAY + 10))
    assert heads_ups(bot) == [said]


async def test_repost_does_not_post_a_host_heads_up_again_for_a_move_that_went_back(bot, cog):
    await bot.store.set(GUILD, "marathon_reminder_on_move", "repost")
    marathon = await host_show(bot, cog, until=(60,))
    (said,) = heads_ups(bot)

    await block_reads(bot, cog, marathon, tomorrow(60), 61)
    await block_reads(bot, cog, marathon, tomorrow(0), 62)
    await tick_at(bot, cog, marathon, 120)

    assert heads_ups(bot) == [said] and said.edits == []


# --- moves a person or the stream made -----------------------------------------------------------


async def held_show(bot, cog):
    """A schedule Black Bloc keeps the clock for, read again with a longer setup: every run
    ahead moved and waits."""
    _channel, marathon = await gdqueer(bot, cog)
    await tick(cog)
    before = await times(bot, marathon)
    await bot.store.set(GUILD, SETUP_KEY, 7)
    cog.client.runs_given = gdqueer_runs(setup=7)
    assert (await cog.refresh(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))).ok
    return marathon, before


async def test_a_staff_start_is_published_at_once_and_leaves_the_other_waits_alone(bot, cog, helix):
    marathon, before = await held_show(bot, cog)
    found = await times(bot, marathon)
    for game in (HAMTARO, KIRBY, WARIO):
        assert found[game]["scheduled_at"] != before[game]["scheduled_at"]
        assert found[game][md.PUBLISHED] == before[game]["scheduled_at"]
        assert md.shown_start(found[game]) == before[game]["scheduled_at"]

    done = await retime.set_start(
        bot, bot.guild, FakeActor(), marathon, found[KIRBY], z(200), "UTC"
    )

    assert done.ok, done.message
    after = await times(bot, marathon)
    for game in (KIRBY, WARIO):
        assert tuple(after[game][one] for one in md.COLUMNS) == NOTHING_WAITS
        assert md.shown_start(after[game]) == after[game]["scheduled_at"]
    assert after[KIRBY]["scheduled_at"] == z(200)
    assert after[HAMTARO][md.PUBLISHED] == before[HAMTARO]["scheduled_at"]


async def test_back_to_the_sheet_is_published_at_once(bot, cog, helix):
    marathon, _before = await held_show(bot, cog)
    kirby = (await times(bot, marathon))[KIRBY]
    assert (await retime.set_start(bot, bot.guild, FakeActor(), marathon, kirby, z(200), "UTC")).ok
    await update_run(
        bot.db, kirby["id"], **{md.PUBLISHED: z(100), md.PENDING: z(200), md.READS: 1}
    )

    back = await signals.sheet_times(bot, bot.guild, FakeActor(), marathon)

    assert back.ok, back.message
    after = (await times(bot, marathon))[KIRBY]
    assert after["scheduled_at"] == after["sheet_at"]
    assert tuple(after[one] for one in md.COLUMNS) == NOTHING_WAITS


async def test_a_start_the_stream_showed_re_times_the_day_at_once(bot, cog, helix):
    _channel, marathon = await gdqueer(bot, cog)
    await tick(cog)
    before = await times(bot, marathon)
    await update_run(bot.db, before[SPYRO]["id"], actual_started_at=z(20))

    moved = await signals.retime(cog, bot.guild, marathon, because="stream")

    after = await times(bot, marathon)
    assert moved and after[HAMTARO]["scheduled_at"] != before[HAMTARO]["scheduled_at"]
    assert tuple(after[HAMTARO][one] for one in md.COLUMNS) == NOTHING_WAITS


async def test_a_move_by_someone_else_while_one_waits_is_let_go_at_the_next_tick(bot, cog):
    marathon = await far_day(bot, cog)
    public, _staff = await copies(bot, marathon)
    await read(bot, cog, marathon, 1, FAR - 64)
    row = await run_of(bot, marathon, GAME)
    await update_run(bot.db, row["id"], scheduled_at=at(FAR + 30), ends_at=at(FAR + 90))

    cog.clock = lambda: NOW + timedelta(minutes=2)
    await follow(bot, cog, marathon)

    assert public.content == words(FAR + 30) and len(public.edits) == 1
    assert await waiting(bot, marathon) == NOTHING_WAITS


async def test_a_run_taken_off_the_schedule_stops_waiting_and_logs_no_move(bot, cog):
    marathon = await far_day(bot, cog)
    await read(bot, cog, marathon, 1, FAR - 64)
    row = await run_of(bot, marathon, GAME)
    await update_run(bot.db, row["id"], state=mt.DROPPED)

    assert md.shown_start(await run_of(bot, marathon, GAME)) == at(FAR - 64)
    assert await damping.settle(cog, bot.guild, marathon, cog.clock(), read=False) == 0

    assert await waiting(bot, marathon) == NOTHING_WAITS
    assert MOVED not in await kinds(bot.db)


async def test_a_write_that_leaves_a_waiting_start_where_it_is_stays_waiting(bot, cog):
    marathon = await far_day(bot, cog)
    await read(bot, cog, marathon, 1, FAR - 64)
    row = await run_of(bot, marathon, GAME)

    same = damping.written(bot, GUILD, row, at(FAR - 64), cog.clock())
    by_hand = damping.written(bot, GUILD, row, at(FAR - 30), cog.clock(), because=mt.BY_STAFF)

    assert same.fields == {} and same.held and not same.public(True, at(FAR - 64), 5)
    assert by_hand.fields == md.CLEARED and not by_hand.held and by_hand.before == at(FAR)
    assert by_hand.public(False, at(FAR - 30), 5) and not by_hand.public(True, at(FAR + 2), 5)
