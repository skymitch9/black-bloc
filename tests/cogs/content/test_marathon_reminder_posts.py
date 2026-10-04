# ruff: noqa: F401, F811
import json
from datetime import timedelta
from types import SimpleNamespace

import discord

from black_bloc import marathon as mt
from black_bloc import marathon_reminder_posts as mrem
from black_bloc.cogs.content import marathon_reminder_posts as following
from black_bloc.cogs.content.marathon import update_marathon, update_run
from black_bloc.marathon_sources import GDQ_HOTFIX
from tests.cogs.content.test_marathon import (
    FAN_ROLE,
    NOW,
    SCHEDULE,
    SKY,
    a_run,
    at,
    bot,
    cog,
    threading,
)
from tests.cogs.content.test_marathon_public import ready
from tests.cogs.content.test_marathon_public_reminders import at_fifteen, reminders_in
from tests.cogs.content.test_marathon_role_ping import MARATHON_ROLE, allowed, pinging, rows
from tests.cogs.content.test_marathon_runner_posts import (
    SKY_RUN,
    events_room,
    follow,
    fresh,
    run_of,
    the_thread,
    tracked,
)
from tests.cogs.content.test_spotlight import (
    CHANNEL,
    GUILD,
    SHADOW_CHANNEL,
    details_of,
    kinds,
)

GAME = "Super Metroid"


def stamps(minutes):
    return (mt.stamp_of(at(minutes), "R"), mt.stamp_of(at(minutes), "f"))


def words(minutes, *, head=""):
    relative, when = stamps(minutes)
    return (
        f"{head}<@{SKY}> runs **{GAME}** (Any%) on **SS4C** {relative} — {when}. "
        "https://twitch.tv/skyruns"
    )


async def reads(bot, cog, marathon, start=None, *, runs=None):
    """The schedule is read again with Sky's run at `start` (None: off the schedule)."""
    if runs is None:
        mine = [] if start is None else [a_run(3, start, game=GAME, people=SKY_RUN)]
        runs = [*SCHEDULE[:2], *mine, *SCHEDULE[3:]]
    cog.client.runs_given = runs
    read = await cog.refresh(bot.guild, await fresh(bot, marathon))
    assert read.ok, read.message


async def moved(bot, cog, marathon, start):
    await reads(bot, cog, marathon, start)
    await follow(bot, cog, marathon)


async def posts_of(bot, marathon, game=GAME):
    return mrem.of_run(await run_of(bot, marathon, game))


async def sent_of(bot, marathon, game=GAME):
    return mt.marks_of(await run_of(bot, marathon, game))


def message_of(bot, copy):
    channel = bot.guild.channels[copy["channel_id"]]
    return next(one for one in channel.messages if one.id == copy["message_id"])


async def copies(bot, marathon, mark=15):
    found = (await posts_of(bot, marathon))[mark]
    return (message_of(bot, found["public"]), message_of(bot, found["staff"]))


def count(bot):
    return len(bot.guild.channels[CHANNEL].messages) + len(the_thread(bot).messages)


async def reminded(bot, cog):
    marathon = await ready(bot, cog)
    await at_fifteen(bot, cog, marathon)
    return marathon


# --- what is remembered --------------------------------------------------------------------------


async def test_each_copy_of_a_reminder_is_remembered_and_a_skipped_mark_is_not_posted(bot, cog):
    marathon = await reminded(bot, cog)

    found = await posts_of(bot, marathon)
    (public,) = reminders_in(bot.guild.channels[CHANNEL])
    (staff,) = reminders_in(the_thread(bot))
    assert found[15]["posted"] is True and found[120] == {"posted": False}
    assert (found[15]["public"]["channel_id"], found[15]["public"]["message_id"]) == (
        CHANNEL,
        public.id,
    )
    assert (found[15]["staff"]["channel_id"], found[15]["staff"]["message_id"]) == (
        the_thread(bot).id,
        staff.id,
    )
    assert found[15]["public"]["text"] == public.content == words(30)
    assert found[15]["public"]["at"] == found[15]["staff"]["at"] == at(30)
    assert await sent_of(bot, marathon) == [15, 120]


async def test_the_role_mention_in_front_of_a_copy_is_remembered_as_its_head(bot, cog):
    marathon = await pinging(bot, cog)
    await at_fifteen(bot, cog, marathon)

    found = (await posts_of(bot, marathon))[15]
    assert found["public"]["head"] == f"<@&{FAN_ROLE}> <@&{MARATHON_ROLE}> "
    assert found["staff"]["head"] == f"<@&{FAN_ROLE}> "
    assert found["public"]["text"] == words(30)


# --- a move edits in place -----------------------------------------------------------------------


async def test_a_run_that_moves_later_edits_each_copy_once_and_posts_nothing_new(bot, cog):
    marathon = await reminded(bot, cog)
    before = count(bot)

    await moved(bot, cog, marathon, 50)

    public, staff = await copies(bot, marathon)
    assert public.content == staff.content == words(50)
    assert len(public.edits) == len(staff.edits) == 1
    assert count(bot) == before
    assert 15 in await sent_of(bot, marathon)
    edited = await rows(bot, "marathon.reminder_edited")
    assert [(one["copy"], one["mark"], one["from"], one["to"]) for one in edited] == [
        ("public", 15, at(30), at(50)),
        ("staff", 15, at(30), at(50)),
    ]
    assert edited[0]["message_id"] == str(public.id) and edited[0]["dropped"] is False
    assert edited[0]["run_id"] == (await run_of(bot, marathon, GAME))["id"]
    assert (await posts_of(bot, marathon))[15]["public"]["at"] == at(50)


async def test_the_edited_public_copy_reads_exactly_like_this_before_and_after(bot, cog):
    marathon = await reminded(bot, cog)
    public, _staff = await copies(bot, marathon)
    assert public.content == (
        f"<@{SKY}> runs **{GAME}** (Any%) on **SS4C** <t:1799087400:R> — <t:1799087400:f>. "
        "https://twitch.tv/skyruns"
    )

    await moved(bot, cog, marathon, 50)

    assert public.content == (
        f"<@{SKY}> runs **{GAME}** (Any%) on **SS4C** <t:1799088600:R> — <t:1799088600:f>. "
        "https://twitch.tv/skyruns"
    )


async def test_a_posted_mark_never_posts_or_pings_a_second_time_after_a_move_later(bot, cog):
    marathon = await pinging(bot, cog)
    await at_fifteen(bot, cog, marathon)
    await moved(bot, cog, marathon, 60)
    before = count(bot)

    for minutes in (44, 45, 46, 59):
        cog.clock = lambda minutes=minutes: NOW + timedelta(minutes=minutes)
        await follow(bot, cog, marathon)

    assert len(reminders_in(bot.guild.channels[CHANNEL])) == 1
    assert len(reminders_in(the_thread(bot))) == 1
    assert count(bot) == before
    assert len(await rows(bot, "marathon.public_reminded")) == 1


async def test_a_run_that_moves_earlier_edits_the_same_way(bot, cog):
    marathon = await reminded(bot, cog)

    await moved(bot, cog, marathon, 22)

    public, staff = await copies(bot, marathon)
    assert public.content == staff.content == words(22)
    assert len(public.edits) == len(staff.edits) == 1


async def test_a_three_minute_slip_inside_the_window_corrects_the_time_shown(bot, cog):
    marathon = await reminded(bot, cog)
    before = count(bot)

    await moved(bot, cog, marathon, 33)

    public, staff = await copies(bot, marathon)
    assert public.content == staff.content == words(33)
    assert count(bot) == before
    assert "marathon.member_run_moved" not in await kinds(bot.db)
    assert len(await rows(bot, "marathon.reminder_edited")) == 2


async def test_an_edit_notifies_nobody_and_keeps_the_role_mention_it_was_posted_with(bot, cog):
    marathon = await pinging(bot, cog)
    await at_fifteen(bot, cog, marathon)
    public, staff = await copies(bot, marathon)
    assert allowed(public) == [FAN_ROLE, MARATHON_ROLE]

    await moved(bot, cog, marathon, 50)

    assert public.content == words(50, head=f"<@&{FAN_ROLE}> <@&{MARATHON_ROLE}> ")
    assert staff.content == words(50, head=f"<@&{FAN_ROLE}> ")
    for message in (public, staff):
        (edit,) = message.edits
        mentions = edit["allowed_mentions"]
        assert (mentions.roles, mentions.users, mentions.everyone) == (False, False, False)


async def test_an_unchanged_run_costs_no_edit_however_often_it_is_followed(bot, cog):
    marathon = await reminded(bot, cog)

    await reads(bot, cog, marathon, 30)
    for _ in range(3):
        await follow(bot, cog, marathon)

    public, staff = await copies(bot, marathon)
    assert public.edits == [] and staff.edits == []
    assert "marathon.reminder_edited" not in await kinds(bot.db)


async def test_one_move_is_one_edit_however_many_ticks_follow(bot, cog):
    marathon = await reminded(bot, cog)

    await moved(bot, cog, marathon, 50)
    for _ in range(3):
        await follow(bot, cog, marathon)

    public, staff = await copies(bot, marathon)
    assert len(public.edits) == len(staff.edits) == 1


async def test_a_mark_that_never_posted_fires_at_its_new_moment_and_is_remembered(bot, cog):
    marathon = await reminded(bot, cog)
    assert (await posts_of(bot, marathon))[120] == {"posted": False}

    await moved(bot, cog, marathon, 200)
    assert await sent_of(bot, marathon) == [15]
    before = count(bot)
    cog.clock = lambda: NOW + timedelta(minutes=80)
    await follow(bot, cog, marathon)

    found = await posts_of(bot, marathon)
    assert count(bot) == before + 2
    assert found[120]["posted"] is True
    assert message_of(bot, found[120]["public"]).content == words(200)
    assert message_of(bot, found[120]["staff"]).edits == []
    cog.clock = lambda: NOW + timedelta(minutes=185)
    await follow(bot, cog, marathon)
    assert count(bot) == before + 2
    assert len(await rows(bot, "marathon.reminded")) == 2


# --- a whole day shifts --------------------------------------------------------------------------


async def test_a_whole_day_that_shifts_is_one_edit_per_post_ten_a_minute_soonest_first(bot, cog):
    await bot.store.set(GUILD, "marathon_reminder_minutes", "1440")
    await bot.store.set(GUILD, "marathon_reminder_stale_minutes", 240)
    await bot.store.set(GUILD, "marathon_ping_minutes", 0)

    def day(shift):
        return [
            a_run(10 + one, 1440 - 10 * one + shift, game=f"Game {one}", people=SKY_RUN, length=5)
            for one in range(1, 13)
        ]

    cog.client.runs_given = day(0)
    marathon = await ready(bot, cog)
    posted = [
        message_of(bot, copy)
        for one in range(1, 13)
        for _mark, _name, copy in mrem.standing(await posts_of(bot, marathon, f"Game {one}"))
    ]
    assert len(posted) == 24

    await reads(bot, cog, marathon, runs=day(3))
    seen = []
    for _ in range(4):
        await follow(bot, cog, marathon)
        seen.append(len(await rows(bot, "marathon.reminder_edited")))

    assert seen == [10, 20, 24, 24]
    assert [len(one.edits) for one in posted] == [1] * 24
    first = (await rows(bot, "marathon.reminder_edited"))[:10]
    assert [one["game"] for one in first] == [
        f"Game {one}" for one in (12, 11, 10, 9, 8) for _ in range(2)
    ]


async def test_the_edit_limit_is_the_keys(bot, cog):
    await bot.store.set(GUILD, "marathon_reminder_edit_limit", 1)
    marathon = await reminded(bot, cog)
    await reads(bot, cog, marathon, 50)

    budget = await following.sync_reminders(cog, bot.guild, marathon)

    public, staff = await copies(bot, marathon)
    assert (len(public.edits), len(staff.edits)) == (1, 0)
    assert (budget.left, budget.waiting) == (0, 1)
    await follow(bot, cog, marathon)
    assert len(staff.edits) == 1


# --- the message is gone -------------------------------------------------------------------------


async def test_a_deleted_copy_is_logged_once_forgotten_and_never_reposted(bot, cog):
    marathon = await reminded(bot, cog)
    public, staff = await copies(bot, marathon)
    await public.delete()
    before = count(bot)

    await moved(bot, cog, marathon, 60)
    await moved(bot, cog, marathon, 70)
    cog.clock = lambda: NOW + timedelta(minutes=56)
    await follow(bot, cog, marathon)

    (lost,) = await rows(bot, "marathon.reminder_lost")
    assert (lost["copy"], lost["reason"], lost["message_id"]) == (
        "public",
        "message_gone",
        str(public.id),
    )
    found = (await posts_of(bot, marathon))[15]
    assert found["posted"] is True and "public" not in found
    assert staff.content == words(70) and len(staff.edits) == 2
    assert count(bot) == before
    assert await sent_of(bot, marathon) == [15, 120]


async def test_a_copy_black_bloc_may_no_longer_edit_and_a_channel_that_is_gone_are_lost(bot, cog):
    marathon = await reminded(bot, cog)
    public, _staff = await copies(bot, marathon)
    bot.guild.channels[CHANNEL].edit_raises = discord.Forbidden(
        SimpleNamespace(status=403, reason="Forbidden"), "Missing Permissions"
    )
    thread_id = the_thread(bot).id
    del bot.guild.channels[thread_id]

    await reads(bot, cog, marathon, 50)
    await following.sync_reminders(cog, bot.guild, marathon)
    await following.sync_reminders(cog, bot.guild, marathon)

    lost = await rows(bot, "marathon.reminder_lost")
    assert [(one["copy"], one["reason"]) for one in lost] == [
        ("public", "no_permission"),
        ("staff", "channel_gone"),
    ]
    assert (await posts_of(bot, marathon))[15] == {"posted": True}
    assert public.content == words(30)


async def test_an_edit_discord_refuses_for_now_is_logged_once_and_tried_again_later(bot, cog):
    marathon = await reminded(bot, cog)
    public, staff = await copies(bot, marathon)
    bot.guild.channels[CHANNEL].edit_raises = RuntimeError("503 upstream")

    await reads(bot, cog, marathon, 50)
    for _ in range(3):
        await following.sync_reminders(cog, bot.guild, marathon)

    (failed,) = await rows(bot, "marathon.reminder_edit_failed")
    assert failed["copy"] == "public" and "503 upstream" in failed["reason"]
    assert failed["from"] == at(30) and failed["to"] == at(50)
    assert staff.content == words(50) and public.content == words(30)
    assert (await posts_of(bot, marathon))[15]["public"]["message_id"] == public.id
    bot.guild.channels[CHANNEL].edit_raises = None
    await following.sync_reminders(cog, bot.guild, marathon)
    assert public.content == words(30)
    cog.clock = lambda: NOW + timedelta(minutes=15) + following.RETRY_AFTER
    await following.sync_reminders(cog, bot.guild, marathon)
    assert public.content == words(50) and len(public.edits) == 1
    assert len(await rows(bot, "marathon.reminder_edit_failed")) == 1


# --- a run taken off the schedule ----------------------------------------------------------------


async def test_a_dropped_run_says_so_in_the_existing_words_and_comes_back_with_its_time(bot, cog):
    marathon = await pinging(bot, cog)
    await at_fifteen(bot, cog, marathon)
    public, staff = await copies(bot, marathon)
    before = count(bot)

    await moved(bot, cog, marathon, None)

    said = f"<@{SKY}> runs **{GAME}** (Any%) on **SS4C** — off the schedule."
    assert (await run_of(bot, marathon, GAME))["state"] == mt.DROPPED
    assert public.content == f"<@&{FAN_ROLE}> <@&{MARATHON_ROLE}> {said}"
    assert staff.content == f"<@&{FAN_ROLE}> {said}"
    assert bot.store.get(GUILD, "marathon_state_dropped") == "off the schedule"
    assert [one["dropped"] for one in await rows(bot, "marathon.reminder_edited")] == [True, True]
    await follow(bot, cog, marathon)
    assert len(public.edits) == len(staff.edits) == 1 and count(bot) == before

    await moved(bot, cog, marathon, 40)

    assert public.content == words(40, head=f"<@&{FAN_ROLE}> <@&{MARATHON_ROLE}> ")
    assert len(public.edits) == 2 and count(bot) == before


async def test_the_dropped_words_are_staffs_to_change(bot, cog):
    await bot.store.set(GUILD, "marathon_state_dropped", "pulled")
    await bot.store.set(
        GUILD, "marathon_reminder_dropped_template", "{game} on {marathon} is {state}"
    )
    marathon = await reminded(bot, cog)

    await moved(bot, cog, marathon, None)

    public, staff = await copies(bot, marathon)
    assert public.content == staff.content == f"{GAME} on SS4C is pulled"


# --- what is left alone --------------------------------------------------------------------------


async def test_a_reminder_posted_before_posts_were_remembered_is_never_posted_twice(bot, cog):
    marathon = await reminded(bot, cog)
    row = await run_of(bot, marathon, GAME)
    await bot.db.conn.execute(
        "UPDATE marathon_runs SET reminder_posts = NULL WHERE id = ?", (row["id"],)
    )
    await bot.db.conn.commit()
    before = count(bot)
    (public,) = reminders_in(bot.guild.channels[CHANNEL])

    await moved(bot, cog, marathon, 200)
    for minutes in (80, 185, 186):
        cog.clock = lambda minutes=minutes: NOW + timedelta(minutes=minutes)
        await follow(bot, cog, marathon)

    assert await sent_of(bot, marathon) == [15, 120]
    assert count(bot) == before and public.edits == [] and public.content == words(30)
    assert "marathon.reminder_edited" not in await kinds(bot.db)


async def test_a_live_or_done_runs_reminder_stays_as_it_was_posted(bot, cog):
    marathon = await reminded(bot, cog)
    public, staff = await copies(bot, marathon)
    row = await run_of(bot, marathon, GAME)

    for state in (mt.LIVE, mt.DONE):
        await update_run(bot.db, row["id"], state=state, scheduled_at=at(50))
        await following.sync_reminders(cog, bot.guild, marathon)

    assert public.edits == [] and staff.edits == []


async def test_a_public_copy_whose_runner_opted_out_since_is_left_alone(bot, cog):
    marathon = await reminded(bot, cog)
    public, staff = await copies(bot, marathon)
    await update_marathon(bot.db, marathon["id"], announce_opt_out=json.dumps([SKY]))

    await moved(bot, cog, marathon, 50)

    assert public.edits == [] and staff.content == words(50)


async def test_marathon_mode_off_edits_nothing(bot, cog):
    marathon = await reminded(bot, cog)
    await reads(bot, cog, marathon, 50)
    await bot.store.set(GUILD, "marathon_mode", "off")

    assert await following.sync_reminders(cog, bot.guild, marathon) is None

    public, staff = await copies(bot, marathon)
    assert public.edits == [] and staff.edits == []


# --- a rehearsal ---------------------------------------------------------------------------------


async def test_a_rehearsal_copy_keeps_its_note_and_the_row_is_a_would_row(bot, cog):
    marathon = await ready(bot, cog)
    await bot.store.set(GUILD, "marathon_mode", "shadow")
    await at_fifteen(bot, cog, marathon)
    found = (await posts_of(bot, marathon))[15]
    public = message_of(bot, found["public"])
    assert found["public"]["channel_id"] == SHADOW_CHANNEL
    assert found["public"]["head"] and public.content == found["public"]["head"] + words(30)

    await moved(bot, cog, marathon, 50)

    assert public.content == found["public"]["head"] + words(50)
    would = await rows(bot, "marathon.would_edit_reminder")
    assert len(would) == len(mrem.standing({15: found}))
    assert would[0]["shadow_home"] == SHADOW_CHANNEL
    assert "marathon.reminder_edited" not in await kinds(bot.db)


# --- the key at repost is the behaviour before ---------------------------------------------------


async def test_repost_leaves_the_old_post_and_posts_again_at_the_new_time(bot, cog):
    await bot.store.set(GUILD, "marathon_reminder_on_move", "repost")
    marathon = await reminded(bot, cog)
    public, staff = await copies(bot, marathon)
    before = count(bot)

    await moved(bot, cog, marathon, 60)

    assert await sent_of(bot, marathon) == [120]
    assert await posts_of(bot, marathon) == {120: {"posted": False}}
    assert public.edits == [] and staff.edits == [] and public.content == words(30)
    assert count(bot) == before
    cog.clock = lambda: NOW + timedelta(minutes=45)
    await follow(bot, cog, marathon)
    assert len(reminders_in(bot.guild.channels[CHANNEL])) == 2
    assert len(reminders_in(the_thread(bot))) == 2
    again, _staff = await copies(bot, marathon)
    assert again is not public and again.content == words(60)
    assert len(await rows(bot, "marathon.public_reminded")) == 2
    assert "marathon.reminder_edited" not in await kinds(bot.db)


async def test_repost_does_nothing_for_a_slip_inside_the_window(bot, cog):
    await bot.store.set(GUILD, "marathon_reminder_on_move", "repost")
    marathon = await reminded(bot, cog)
    before = count(bot)

    await moved(bot, cog, marathon, 33)

    public, staff = await copies(bot, marathon)
    assert public.content == staff.content == words(30)
    assert count(bot) == before and await sent_of(bot, marathon) == [15, 120]


async def test_a_stream_retime_keeps_a_posted_mark_and_the_copy_follows(bot, cog):
    from black_bloc.cogs.content import marathon_signals as signals

    cog.client.runs_given = [
        a_run(2, -30, game="Celeste"),
        a_run(3, 30, game=GAME, people=SKY_RUN),
    ]
    marathon = await reminded(bot, cog)
    await bot.db.conn.execute(
        "UPDATE marathons SET source = ? WHERE id = ?", (GDQ_HOTFIX, marathon["id"])
    )
    first = await run_of(bot, marathon, "Celeste")
    await update_run(bot.db, first["id"], state=mt.LIVE, actual_started_at=at(-20))
    before = count(bot)

    changed = await signals.retime(cog, bot.guild, await fresh(bot, marathon), because="stream")
    await following.sync_reminders(cog, bot.guild, marathon)

    row = await run_of(bot, marathon, GAME)
    assert changed == 2 and row["scheduled_at"] == at(47)
    assert mt.marks_of(row) == [15, 120]
    public, staff = await copies(bot, marathon)
    assert public.content == staff.content == words(47)
    cog.clock = lambda: NOW + timedelta(minutes=33)
    await cog.remind(bot.guild, await fresh(bot, marathon), cog.clock())
    assert count(bot) == before
