# ruff: noqa: F401, F811
from datetime import timedelta

import pytest

from black_bloc.cogs.content import marathon_inbox as inbox
from black_bloc.cogs.content.marathon import (
    Marathons,
    create_marathon,
    get_marathon,
    refresh_marathon,
    runs_of,
)
from tests.cogs.content.test_marathon import (
    NOW,
    SKY,
    URL,
    FakeClient,
    a_run,
    at,
    bot,
    cog,
    threading,
)
from tests.cogs.content.test_spotlight import GUILD, SHADOW_CHANNEL, FakeActor, details_of, kinds

EVENTS = 555
THREADS = 556
BOARD = "BaF on the schedule"
SKY_RUN = (("Sky", "skyruns", "runner"),)


class PinCap(Exception):
    code = 30003


@pytest.fixture(autouse=True)
async def events_room(bot):
    threading(bot, EVENTS)
    await bot.store.set(GUILD, "events_announce_channel_id", EVENTS)
    await bot.store.set(GUILD, "marathon_track_makes_thread", True)
    await bot.store.set(GUILD, "events_create_scheduled", False)


async def tracked(bot):
    made = await create_marathon(bot, bot.guild, FakeActor(), name="SS4C", url=URL)
    assert made.ok, made.message
    done = await inbox.track(bot, bot.guild, FakeActor(), made.value)
    assert done.ok, done.message
    return await fresh(bot, made.value)


async def fresh(bot, marathon):
    return await get_marathon(bot.db, GUILD, marathon["id"])


def the_thread(bot, channel_id=EVENTS):
    return bot.guild.channels[channel_id].threads[-1]


def board_in(thread):
    return [one for one in thread.messages if BOARD in one.content]


def runner_posts(thread, game=None):
    return [
        one
        for one in thread.messages
        if one.content.startswith("**Sky**") and (game is None or f"**{game}**" in one.content)
    ]


async def run_of(bot, marathon, game):
    return next(one for one in await runs_of(bot.db, marathon["id"]) if one["game"] == game)


async def follow(bot, cog, marathon):
    await cog.follow(bot.guild, await fresh(bot, marathon))


# --- the board is a head, each BaF run is its own post -----------------------------------------


async def test_the_board_is_a_head_with_no_run_lines(bot, cog):
    marathon = await tracked(bot)
    await follow(bot, cog, marathon)

    boards = board_in(the_thread(bot))
    assert len(boards) == 1 and boards[0].pinned
    assert boards[0].content.startswith("**SS4C** — BaF on the schedule (1)")
    assert "Super Metroid" not in boards[0].content and "<@" not in boards[0].content
    assert "\n" not in boards[0].content


async def test_a_matched_baf_run_gets_one_pinned_post_under_the_board_naming_never_pinging(
    bot, cog
):
    marathon = await tracked(bot)
    await follow(bot, cog, marathon)

    thread = the_thread(bot)
    posts = runner_posts(thread)
    assert len(posts) == 1 and posts[0].pinned
    post = posts[0]
    assert thread.messages.index(post) > thread.messages.index(board_in(thread)[0])
    assert f"(<@{SKY}>)" in post.content and "**Super Metroid**" in post.content
    assert "Any%" in post.content and f"<t:{int((NOW + timedelta(minutes=30)).timestamp())}:f>" in (
        post.content
    )
    assert "coming up" in post.content
    said = post.kwargs["allowed_mentions"]
    assert said.users is False and said.roles is False and said.everyone is False
    row = await run_of(bot, marathon, "Super Metroid")
    assert row["post_message_id"] == post.id and row["post_channel_id"] == thread.id
    assert row["post_pinned"] == 1
    assert (await details_of(bot.db, "marathon.runner_post_posted"))["run_id"] == row["id"]
    assert (await details_of(bot.db, "marathon.runner_post_pinned"))["run_id"] == row["id"]
    assert post.pins == ["Black Bloc: a BaF run on the marathon"]


async def test_a_second_tick_posts_nothing_new_and_edits_nothing(bot, cog):
    marathon = await tracked(bot)
    await follow(bot, cog, marathon)
    thread = the_thread(bot)
    count = len(thread.messages)
    post = runner_posts(thread)[0]

    await follow(bot, cog, marathon)
    await cog.tick_once()

    assert len(thread.messages) == count and post.edits == []
    assert (await kinds(bot.db)).count("marathon.runner_post_posted") == 1


async def test_a_slot_move_edits_the_post_in_place(bot, cog):
    marathon = await tracked(bot)
    await follow(bot, cog, marathon)
    post = runner_posts(the_thread(bot))[0]
    cog.client.runs_given = [
        a_run(3, 75, game="Super Metroid", people=SKY_RUN),
        a_run(4, 90, game="Kirby Air Riders"),
    ]

    await refresh_marathon(bot, bot.guild, marathon)

    assert len(runner_posts(the_thread(bot))) == 1
    assert f"<t:{int((NOW + timedelta(minutes=75)).timestamp())}:f>" in post.content
    assert post.edits and post.edits[-1]["allowed_mentions"].users is False
    assert "marathon.runner_post_edited" in await kinds(bot.db)


async def test_live_and_done_edit_the_post_and_the_shoutout_stays_its_own_message(bot, cog):
    marathon = await tracked(bot)
    await follow(bot, cog, marathon)
    thread = the_thread(bot)
    post = runner_posts(thread)[0]

    cog.clock = lambda: NOW + timedelta(minutes=31)
    await follow(bot, cog, marathon)
    assert "on now" in post.content
    shouts = [one for one in thread.messages if "right now" in one.content]
    assert len(shouts) == 1 and shouts[0] is not post

    cog.clock = lambda: NOW + timedelta(minutes=200)
    await follow(bot, cog, marathon)
    assert "· done ·" in post.content and post.pinned


async def test_a_dropped_run_is_edited_not_deleted_and_unpinned_a_day_later(bot, cog):
    marathon = await tracked(bot)
    await follow(bot, cog, marathon)
    post = runner_posts(the_thread(bot))[0]
    cog.client.runs_given = [a_run(4, 90, game="Kirby Air Riders"), a_run(5, 300)]

    await refresh_marathon(bot, bot.guild, marathon)

    assert not post.deleted and "off the schedule" in post.content and post.pinned
    cog.clock = lambda: NOW + timedelta(hours=12)
    await cog.tick_once()
    assert post.pinned

    cog.clock = lambda: NOW + timedelta(days=1, minutes=5)
    await cog.tick_once()
    assert post.pinned is False and post.unpins == ["Black Bloc: that BaF run is over"]
    assert (await run_of(bot, marathon, "Super Metroid"))["post_pinned"] == 0
    assert (await details_of(bot.db, "marathon.runner_post_unpinned"))["because"] == "run_over"
    assert board_in(the_thread(bot))[0].pinned


async def test_backfill_posts_every_matched_run_in_schedule_order_on_the_first_tick(bot, cog):
    await bot.store.set(GUILD, "marathon_runner_posts", False)
    cog.client.runs_given = [
        a_run(7, 90, game="Kirby Air Riders", people=SKY_RUN),
        a_run(3, 30, game="Super Metroid", people=SKY_RUN),
        a_run(8, -60, game="Celeste", people=SKY_RUN, length=10),
        a_run(9, -600, game="Halo", people=SKY_RUN, length=10),
    ]
    marathon = await tracked(bot)
    await follow(bot, cog, marathon)
    assert runner_posts(the_thread(bot)) == []
    board = board_in(the_thread(bot))[0]
    assert "Super Metroid" in board.content

    await bot.store.set(GUILD, "marathon_runner_posts", True)
    restarted = Marathons(bot)
    restarted.client = cog.client
    restarted.clock = lambda: NOW
    bot.cogs["Marathons"] = restarted
    await restarted.tick_once()

    games = [one.content.split("**")[3] for one in runner_posts(the_thread(bot))]
    assert games == ["Celeste", "Super Metroid", "Kirby Air Riders"]
    assert "Super Metroid" not in board.content
    assert all(one.pinned for one in runner_posts(the_thread(bot)))


async def test_pins_refused_for_the_cap_are_logged_once_and_the_posts_still_land(bot, cog):
    cog.client.runs_given = [
        a_run(3, 30, game="Super Metroid", people=SKY_RUN),
        a_run(7, 90, game="Kirby Air Riders", people=SKY_RUN),
    ]
    await bot.store.set(GUILD, "marathon_runner_posts", False)
    marathon = await tracked(bot)
    await follow(bot, cog, marathon)
    the_thread(bot).pin_raises = PinCap("Maximum number of pins reached (50)")
    await bot.store.set(GUILD, "marathon_runner_posts", True)

    await follow(bot, cog, marathon)

    posts = runner_posts(the_thread(bot))
    assert len(posts) == 2 and not any(one.pinned for one in posts)
    assert (await kinds(bot.db)).count("marathon.runner_post_pin_capped") == 1
    assert "marathon.runner_post_pin_failed" not in await kinds(bot.db)
    assert all(not one["post_pinned"] for one in await runs_of(bot.db, marathon["id"]))


async def test_with_pinning_off_the_post_is_not_pinned(bot, cog):
    await bot.store.set(GUILD, "marathon_runner_posts_pinned", False)
    marathon = await tracked(bot)
    await follow(bot, cog, marathon)

    posts = runner_posts(the_thread(bot))
    assert len(posts) == 1 and posts[0].pinned is False
    assert "marathon.runner_post_pinned" not in await kinds(bot.db)


async def test_with_runner_posts_off_the_board_lists_the_runs_and_no_post_is_made(bot, cog):
    await bot.store.set(GUILD, "marathon_runner_posts", False)
    marathon = await tracked(bot)
    await follow(bot, cog, marathon)

    board = board_in(the_thread(bot))[0]
    assert "Super Metroid" in board.content and f"<@{SKY}>" in board.content
    assert runner_posts(the_thread(bot)) == []
    assert "marathon.runner_post_posted" not in await kinds(bot.db)


async def test_untrack_takes_every_runner_post_pin_off_with_the_board(bot, cog):
    marathon = await tracked(bot)
    await follow(bot, cog, marathon)
    post = runner_posts(the_thread(bot))[0]

    await inbox.untrack(bot, bot.guild, FakeActor(), marathon)

    assert post.pinned is False and board_in(the_thread(bot))[0].pinned is False
    assert (await details_of(bot.db, "marathon.runner_post_unpinned"))["because"] == "untracked"


async def test_the_day_after_the_marathon_every_pin_comes_off_even_with_posts_off(bot, cog):
    marathon = await tracked(bot)
    await follow(bot, cog, marathon)
    post = runner_posts(the_thread(bot))[0]
    await bot.store.set(GUILD, "marathon_mode", "off")

    cog.clock = lambda: NOW + timedelta(days=3)
    await cog.tick_once()

    assert post.pinned is False
    assert (await details_of(bot.db, "marathon.runner_post_unpinned"))["because"] == "over"


async def test_a_moved_thread_gets_the_posts_fresh_and_pinned_and_the_old_pins_come_off(bot, cog):
    marathon = await tracked(bot)
    await follow(bot, cog, marathon)
    old = the_thread(bot)
    old_post = runner_posts(old)[0]
    threading(bot, THREADS)
    await bot.store.set(GUILD, "marathon_thread_channel_id", THREADS)

    await cog.tick_once()

    new = bot.guild.channels[THREADS].threads[0]
    moved = runner_posts(new)
    assert len(moved) == 1 and moved[0].pinned
    assert new.messages.index(moved[0]) > new.messages.index(board_in(new)[0])
    assert old_post.pinned is False and old.archived
    row = await run_of(bot, marathon, "Super Metroid")
    assert row["post_channel_id"] == new.id and row["post_message_id"] == moved[0].id
    assert row["post_pinned"] == 1

    await cog.tick_once()
    assert len(runner_posts(new)) == 1


async def test_shadow_posts_in_the_shadow_home_and_pins_nothing(bot, cog):
    await bot.store.set(GUILD, "marathon_mode", "shadow")
    marathon = await tracked(bot)
    await follow(bot, cog, marathon)

    thread = bot.guild.channels[SHADOW_CHANNEL].threads[-1]
    posts = [one for one in thread.messages if "**Super Metroid**" in one.content]
    assert len(posts) == 1 and posts[0].pinned is False
    assert "marathon.would_post_runner_post" in await kinds(bot.db)


async def test_an_untracked_marathon_posts_no_runner_post(bot, cog):
    made = await create_marathon(bot, bot.guild, FakeActor(), name="SS4C", url=URL)
    await follow(bot, cog, made.value)
    await cog.tick_once()

    assert "marathon.runner_post_posted" not in await kinds(bot.db)
    assert all(not one["post_message_id"] for one in await runs_of(bot.db, made.value["id"]))
