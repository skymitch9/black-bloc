# ruff: noqa: F401, F811
from datetime import timedelta

import pytest

from black_bloc import marathon as mt
from black_bloc.cogs.content import marathon_inbox as inbox
from black_bloc.cogs.content.marathon import (
    create_marathon,
    get_marathon,
    runs_of,
    set_active,
    shout_now,
)
from black_bloc.cogs.content.marathon_archive import archive_marathon, restore_marathon
from tests.cogs.content.test_marathon import NOW, SCHEDULE, URL, a_run, bot, cog
from tests.cogs.content.test_marathon_public import public_posts
from tests.cogs.content.test_marathon_runner_posts import (
    SKY_RUN,
    events_room,
    follow,
    fresh,
    run_of,
)
from tests.cogs.content.test_spotlight import GUILD, FakeActor, details_of, kinds

GAME = "Super Metroid"


def shouts(bot):
    found = []
    for channel in list(bot.guild.channels.values()):
        found += [one for one in channel.messages if "right now" in (one.content or "")]
    return found


async def found(bot):
    made = await create_marathon(bot, bot.guild, FakeActor(), name="Game Masters", url=URL)
    assert made.ok, made.message
    return await fresh(bot, made.value)


def at(cog, minutes):
    cog.clock = lambda: NOW + timedelta(minutes=minutes)


async def live_untracked(bot, cog, minutes=31):
    """The incident's shape: the run flips live on the tick while nobody has tracked it yet."""
    marathon = await found(bot)
    at(cog, minutes)
    await follow(bot, cog, marathon)
    row = await run_of(bot, marathon, GAME)
    assert row["state"] == mt.LIVE and not row["shout_message_id"]
    assert shouts(bot) == [] and public_posts(bot) == []
    return marathon


async def track(bot, marathon):
    done = await inbox.track(bot, bot.guild, FakeActor(), marathon)
    assert done.ok, done.message
    return await fresh(bot, marathon)


async def test_tracking_while_our_run_is_live_posts_its_highlight_and_shout_once(bot, cog):
    marathon = await live_untracked(bot, cog)

    at(cog, 60)
    marathon = await track(bot, marathon)
    await follow(bot, cog, marathon)

    assert len(shouts(bot)) == 1 and len(public_posts(bot)) == 1
    row = await run_of(bot, marathon, GAME)
    assert row["shout_message_id"] == shouts(bot)[0].id
    assert row["public_message_id"] == public_posts(bot)[0].id
    assert (await details_of(bot.db, "marathon.public_highlight_posted"))["auto"] is True

    at(cog, 61)
    await follow(bot, cog, marathon)
    await follow(bot, cog, marathon)

    assert len(shouts(bot)) == 1 and len(public_posts(bot)) == 1
    assert (await kinds(bot.db)).count("marathon.shouted") == 1
    assert (await fresh(bot, marathon))["late_shout_due"] == 0


async def test_a_run_already_done_at_tracking_gets_nothing(bot, cog):
    marathon = await live_untracked(bot, cog)
    at(cog, 200)
    await follow(bot, cog, marathon)
    assert (await run_of(bot, marathon, GAME))["state"] == mt.DONE

    marathon = await track(bot, marathon)
    await follow(bot, cog, marathon)

    assert shouts(bot) == [] and public_posts(bot) == []
    assert "marathon.late_shout_skipped" not in await kinds(bot.db)


@pytest.fixture
def long_run(cog):
    cog.client.runs_given = [a_run(3, 30, game=GAME, people=SKY_RUN, length=600)]


async def test_a_run_live_longer_than_the_cap_is_left_alone_and_logged_once(bot, cog, long_run):
    marathon = await live_untracked(bot, cog)

    at(cog, 31 + 240)
    marathon = await track(bot, marathon)
    await follow(bot, cog, marathon)
    await follow(bot, cog, marathon)

    assert shouts(bot) == [] and public_posts(bot) == []
    assert (await kinds(bot.db)).count("marathon.late_shout_skipped") == 1
    logged = await details_of(bot.db, "marathon.late_shout_skipped")
    assert (logged["age_minutes"], logged["cap_minutes"], logged["game"]) == (240, 180, GAME)


async def test_the_cap_at_zero_always_announces_the_live_run(bot, cog, long_run):
    await bot.store.set(GUILD, "marathon_late_track_shout_minutes", 0)
    marathon = await live_untracked(bot, cog)

    at(cog, 31 + 240)
    marathon = await track(bot, marathon)
    await follow(bot, cog, marathon)

    assert len(shouts(bot)) == 1 and len(public_posts(bot)) == 1


async def test_a_feed_adopting_a_marathon_with_our_run_live_announces_it(bot, cog):
    marathon = await live_untracked(bot, cog)

    at(cog, 60)
    assert await inbox.auto_track(bot, bot.guild, marathon["id"], {"auto_track": 1})
    await follow(bot, cog, marathon)

    assert len(shouts(bot)) == 1 and len(public_posts(bot)) == 1


async def test_track_anyway_from_ignored_announces_the_live_run(bot, cog):
    marathon = await live_untracked(bot, cog)
    ignored = await inbox.ignore(bot, bot.guild, FakeActor(), marathon, True)
    assert ignored.ok

    at(cog, 60)
    done = await inbox.run_action(bot, bot.guild, FakeActor(), marathon, "anyway")
    assert done.ok, done.message
    await follow(bot, cog, marathon)

    assert len(shouts(bot)) == 1 and len(public_posts(bot)) == 1


async def test_a_restored_tracked_marathon_announces_its_live_run_once_resumed(bot, cog):
    marathon = await live_untracked(bot, cog)
    await bot.db.conn.execute(
        "UPDATE marathons SET tracked_at = ? WHERE id = ?", (NOW.isoformat(), marathon["id"])
    )
    await bot.db.conn.commit()
    assert (await archive_marathon(bot, bot.guild, FakeActor(), marathon)).ok
    assert (await restore_marathon(bot, bot.guild, FakeActor(), marathon["id"])).ok
    assert (await set_active(bot, bot.guild, FakeActor(), marathon, True)).ok

    at(cog, 60)
    await follow(bot, cog, marathon)

    assert len(shouts(bot)) == 1


async def test_untracked_ticks_never_arm_the_late_shout(bot, cog):
    marathon = await live_untracked(bot, cog)
    await follow(bot, cog, marathon)

    assert (await fresh(bot, marathon))["late_shout_due"] == 0
    assert shouts(bot) == []


async def test_an_upcoming_run_past_its_start_at_tracking_goes_live_and_is_announced_once(
    bot, cog
):
    marathon = await found(bot)

    at(cog, 35)
    marathon = await track(bot, marathon)
    await follow(bot, cog, marathon)
    await follow(bot, cog, marathon)

    row = await run_of(bot, marathon, GAME)
    assert row["state"] == mt.LIVE and row["live_because"] == mt.BY_SCHEDULE
    assert len(shouts(bot)) == 1 and len(public_posts(bot)) == 1


async def test_shout_it_now_answers_with_the_runs_game(bot, cog):
    marathon = await live_untracked(bot, cog)
    marathon = await track(bot, marathon)
    row = await run_of(bot, marathon, GAME)

    said = await shout_now(bot, bot.guild, FakeActor(), marathon, row)

    assert said.ok and said.message == f"The shoutout for **{GAME}** is out."
