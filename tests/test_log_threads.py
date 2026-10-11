# ruff: noqa: F401, F811
import asyncio
import json
import logging

import discord

from black_bloc import marathon_inbox as mi
from black_bloc.actionlog import log_action
from black_bloc.cogs.content.marathon import create_marathon, get_marathon
from tests.cogs.content.test_marathon import URL, added, bot, cog, threading
from tests.cogs.content.test_spotlight import GUILD, LOG_CHANNEL, FakeActor

MOVED = "marathon.member_run_moved"
OTHER_LOG = 223


async def log_room(bot, channel_id=LOG_CHANNEL):
    room = threading(bot, channel_id)
    await bot.store.set(GUILD, "log_channel_id", channel_id)
    return room


async def moved(bot, marathon, **extra):
    await log_action(bot, bot.guild, MOVED, details={"marathon_id": marathon["id"], **extra})


def titled(channel, kind=MOVED):
    return [one for one in channel.messages if one.embeds and one.embeds[0].title == kind]


async def logged(bot, kind):
    cur = await bot.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id", (kind,)
    )
    return [json.loads(row["details"]) for row in await cur.fetchall()]


async def untracked(bot):
    made = await create_marathon(bot, bot.guild, FakeActor(), name="RGL N64", url=URL)
    assert made.ok, made.message
    return made.value


async def test_a_tracked_marathons_row_goes_to_its_own_thread_under_the_log_channel(bot, cog):
    room = await log_room(bot)
    marathon = await added(bot, cog)

    await moved(bot, marathon)

    assert len(room.threads) == 1 and titled(room) == []
    thread = room.threads[0]
    assert thread.name == "AGDQ 2027"
    assert thread.kwargs["auto_archive_duration"] == mi.AUTO_ARCHIVE_MINUTES
    assert thread.kwargs["type"] == discord.ChannelType.public_thread
    opening = thread.messages[0]
    assert opening.content == (
        "AGDQ 2027 — Black Bloc's log for this marathon. Tracker: "
        f"https://blackbloc.heygabi.ai/schedule.html#marathon-{marathon['id']}"
    )
    assert opening.kwargs["allowed_mentions"].users is False
    assert len(titled(thread)) == 1
    row = await get_marathon(bot.db, GUILD, marathon["id"])
    assert row["log_thread_id"] == thread.id and row["log_thread_channel_id"] == LOG_CHANNEL
    made = await logged(bot, "marathon.log_thread_made")
    assert made[-1]["thread_id"] == thread.id and made[-1]["channel_id"] == LOG_CHANNEL


async def test_the_next_row_reuses_the_same_thread(bot, cog):
    room = await log_room(bot)
    marathon = await added(bot, cog)

    await moved(bot, marathon)
    await moved(bot, marathon, run="two")

    assert len(room.threads) == 1 and len(titled(room.threads[0])) == 2
    assert len(await logged(bot, "marathon.log_thread_made")) == 1


async def test_two_rows_at_once_make_exactly_one_thread(bot, cog):
    room = await log_room(bot)
    marathon = await added(bot, cog)

    await asyncio.gather(*(moved(bot, marathon, run=str(one)) for one in range(4)))

    assert len(room.threads) == 1 and len(titled(room.threads[0])) == 4
    assert len(await logged(bot, "marathon.log_thread_made")) == 1


async def test_an_untracked_marathon_posts_to_the_channel_as_today(bot, cog):
    room = await log_room(bot)
    marathon = await untracked(bot)

    await moved(bot, marathon)

    assert room.threads == [] and len(titled(room)) == 1


async def test_a_row_with_no_marathon_or_another_feature_posts_to_the_channel(bot, cog):
    room = await log_room(bot)
    marathon = await added(bot, cog)

    await log_action(bot, bot.guild, MOVED, details={"run": "one"})
    await log_action(
        bot, bot.guild, "spotlight.set", details={"marathon_id": marathon["id"]}, notify=True
    )

    assert room.threads == []
    assert len(titled(room)) == 1 and len(titled(room, "spotlight.set")) == 1


async def test_the_switch_off_keeps_every_row_in_the_channel(bot, cog):
    room = await log_room(bot)
    await bot.store.set(GUILD, "marathon_log_threads", False)
    marathon = await added(bot, cog)

    await moved(bot, marathon)

    assert room.threads == [] and len(titled(room)) == 1


async def test_the_thread_name_and_opening_come_from_their_keys(bot, cog):
    room = await log_room(bot)
    await bot.store.set(GUILD, "marathon_log_thread_name_template", "log · {marathon} · {when}")
    await bot.store.set(GUILD, "marathon_log_thread_opening_template", "Here: {url}")
    marathon = await added(bot, cog)
    await bot.db.conn.execute(
        "UPDATE marathons SET starts_at = ? WHERE id = ?",
        ("2027-01-05T16:30:00+00:00", marathon["id"]),
    )
    await bot.db.conn.commit()

    await moved(bot, marathon)

    thread = room.threads[0]
    assert thread.name == "log · AGDQ 2027 · 05 Jan 2027"
    assert thread.messages[0].content.endswith(f"schedule.html#marathon-{marathon['id']}")


async def test_an_archived_thread_is_reopened_before_the_row_goes_in(bot, cog):
    room = await log_room(bot)
    marathon = await added(bot, cog)
    await moved(bot, marathon)
    thread = room.threads[0]
    thread.archived = True

    await moved(bot, marathon, run="two")

    assert thread.thread_edits == [{"archived": False}] and len(titled(thread)) == 2
    assert len(room.threads) == 1


async def test_a_deleted_thread_is_logged_lost_and_made_again(bot, cog):
    room = await log_room(bot)
    marathon = await added(bot, cog)
    await moved(bot, marathon)
    gone = room.threads[0]
    del bot.guild.channels[gone.id]

    await moved(bot, marathon, run="two")

    assert len(room.threads) == 2 and len(titled(room.threads[1])) == 1
    lost = await logged(bot, "marathon.log_thread_lost")
    assert lost == [{"marathon_id": marathon["id"], "thread_id": gone.id, "via": "discord"}]
    assert titled(room, "marathon.log_thread_lost") != []
    made = await logged(bot, "marathon.log_thread_made")
    assert made[-1]["replaced"] == gone.id


async def test_a_new_log_channel_gets_a_new_thread_and_the_old_one_is_left_alone(bot, cog):
    room = await log_room(bot)
    marathon = await added(bot, cog)
    await moved(bot, marathon)
    old = room.threads[0]

    other = await log_room(bot, OTHER_LOG)
    await moved(bot, marathon, run="two")

    assert len(other.threads) == 1 and len(titled(other.threads[0])) == 1
    assert len(titled(old)) == 1 and old.thread_edits == []
    row = await get_marathon(bot.db, GUILD, marathon["id"])
    assert row["log_thread_id"] == other.threads[0].id
    assert row["log_thread_channel_id"] == OTHER_LOG


async def test_a_thread_that_cannot_be_made_falls_back_to_the_channel_with_a_warning(
    bot, cog, caplog
):
    room = await log_room(bot)
    room.create_raises = RuntimeError("no permission")
    marathon = await added(bot, cog)

    with caplog.at_level(logging.WARNING):
        await moved(bot, marathon)

    assert room.threads == [] and len(titled(room)) == 1
    assert "no permission" in caplog.text


async def test_a_thread_that_refuses_the_send_falls_back_to_the_channel(bot, cog, caplog):
    room = await log_room(bot)
    marathon = await added(bot, cog)
    await moved(bot, marathon)
    room.threads[0].send_raises = RuntimeError("thread locked")

    with caplog.at_level(logging.WARNING):
        await moved(bot, marathon, run="two")

    assert len(titled(room)) == 1 and "thread locked" in caplog.text


async def test_a_log_channel_that_takes_no_threads_posts_as_today(bot, cog):
    marathon = await added(bot, cog)

    await moved(bot, marathon)

    assert len(titled(bot.guild.channels[LOG_CHANNEL])) == 1
