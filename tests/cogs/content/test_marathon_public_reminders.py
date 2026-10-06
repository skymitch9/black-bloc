# ruff: noqa: F401, F811
import json
from datetime import timedelta

from black_bloc import marathon_hosts as mh
from black_bloc import settings_store
from black_bloc.cogs.content import marathon_announce as announce
from black_bloc.cogs.content import marathon_hosts as hosts
from black_bloc.cogs.content import marathon_public as public
from black_bloc.cogs.content import marathon_public_reminders as reminders
from black_bloc.cogs.content.marathon import create_marathon, pair_runner, update_marathon
from tests.cogs.content.test_marathon import (
    FAN_ROLE,
    NOW,
    SKY,
    URL,
    a_run,
    bot,
    cog,
    threading,
)
from tests.cogs.content.test_marathon_public import highlighted, named, public_posts, ready
from tests.cogs.content.test_marathon_runner_posts import (
    EVENTS,
    events_room,
    follow,
    fresh,
    run_of,
    the_thread,
)
from tests.cogs.content.test_spotlight import (
    CHANNEL,
    GUILD,
    LOG_CHANNEL,
    FakeActor,
    FakeChannel,
    details_of,
    kinds,
)

REMINDERS = 445
HIGHLIGHTS = 446


def reminders_in(channel):
    return [
        one
        for one in channel.messages
        if "**Super Metroid**" in one.content
        and ":R>" in one.content
        and "**Sky**" not in one.content
    ]


def room(bot, channel_id, name):
    made = FakeChannel(channel_id)
    made.name = name
    bot.guild.channels[channel_id] = made
    return made


async def at_fifteen(bot, cog, marathon):
    cog.clock = lambda: NOW + timedelta(minutes=15)
    await follow(bot, cog, marathon)


async def test_a_reminder_posts_in_the_reminder_channel_and_not_in_the_thread(bot, cog):
    marathon = await ready(bot, cog)

    await at_fifteen(bot, cog, marathon)

    assert len(reminders_in(bot.guild.channels[CHANNEL])) == 1
    assert reminders_in(the_thread(bot)) == []
    held = json.loads((await run_of(bot, marathon, "Super Metroid"))["reminder_posts"])["15"]
    assert held["posted"] is True and "public" in held and "staff" not in held
    assert "marathon.public_reminded" in await kinds(bot.db)
    assert "marathon.reminded" not in await kinds(bot.db)


async def test_a_tracked_marathons_reminder_posts_in_the_thread_and_the_reminder_channel(bot, cog):
    marathon = await ready(bot, cog)
    await bot.store.set(GUILD, "marathon_thread_reminders", True)

    await at_fifteen(bot, cog, marathon)

    staff = reminders_in(the_thread(bot))
    shown = reminders_in(bot.guild.channels[CHANNEL])
    assert len(staff) == 1 and len(shown) == 1
    assert shown[0].content == staff[0].content
    mentions = shown[0].kwargs["allowed_mentions"]
    assert mentions.users is False and mentions.roles is False and mentions.everyone is False
    logged = await details_of(bot.db, "marathon.public_reminded")
    assert (logged["mark"], logged["channel_id"], logged["pinged"]) == (15, CHANNEL, False)
    assert "marathon.reminded" in await kinds(bot.db)


async def test_a_reminder_posts_once_even_after_a_restart(bot, cog):
    marathon = await ready(bot, cog)
    await bot.store.set(GUILD, "marathon_thread_reminders", True)
    await at_fifteen(bot, cog, marathon)
    await follow(bot, cog, marathon)
    restarted = type(cog)(bot)
    restarted.client = cog.client
    restarted.clock = cog.clock
    bot.cogs["Marathons"] = restarted

    await restarted.tick_once()

    assert len(reminders_in(bot.guild.channels[CHANNEL])) == 1
    assert len(reminders_in(the_thread(bot))) == 1


async def test_an_untracked_marathon_posts_neither_copy(bot, cog):
    made = await create_marathon(bot, bot.guild, FakeActor(), name="SS4C", url=URL)
    cog.clock = lambda: NOW + timedelta(minutes=15)

    await cog.remind(bot.guild, await fresh(bot, made.value), NOW + timedelta(minutes=15))

    assert reminders_in(bot.guild.channels[CHANNEL]) == []
    assert "marathon.public_reminded" not in await kinds(bot.db)


async def test_the_public_copy_pings_only_while_the_marathon_pings_roles(bot, cog):
    marathon = await ready(bot, cog)
    await update_marathon(bot.db, marathon["id"], ping_role=1)

    await at_fifteen(bot, cog, marathon)

    shown = reminders_in(bot.guild.channels[CHANNEL])[0]
    assert shown.content.startswith(f"<@&{FAN_ROLE}>")
    mentions = shown.kwargs["allowed_mentions"]
    assert [one.id for one in mentions.roles] == [FAN_ROLE] and mentions.users is False
    assert (await details_of(bot.db, "marathon.public_reminded"))["pinged"] is True


async def test_the_public_copy_has_its_own_words(bot, cog):
    marathon = await ready(bot, cog)
    await bot.store.set(GUILD, "marathon_thread_reminders", True)
    await bot.store.set(GUILD, "marathon_public_reminder_template", "{member} on **{game}** {in}!")

    await at_fifteen(bot, cog, marathon)

    shown = reminders_in(bot.guild.channels[CHANNEL])[0]
    assert shown.content.endswith("!") and "on **Super Metroid** <t:" in shown.content
    assert not reminders_in(the_thread(bot))[0].content.endswith("!")


async def test_the_switch_off_keeps_reminders_in_the_thread_only(bot, cog):
    marathon = await ready(bot, cog)
    await bot.store.set(GUILD, "marathon_public_reminders", False)

    await at_fifteen(bot, cog, marathon)

    assert len(reminders_in(the_thread(bot))) == 1
    assert reminders_in(bot.guild.channels[CHANNEL]) == []


async def test_the_three_keys_are_three_rows_and_each_moves_only_its_own_posts(bot, cog):
    for key in ("golive_channel_id", "marathon_public_channel_id", "marathon_reminder_channel_id"):
        assert settings_store.KEY_TYPES[key] == "channel"
    marathon = await ready(bot, cog)
    reminder_room = room(bot, REMINDERS, "baf-reminders")
    highlight_room = room(bot, HIGHLIGHTS, "baf-highlights")
    await bot.store.set(GUILD, "marathon_reminder_channel_id", REMINDERS)

    assert reminders.reminder_channel(bot, GUILD) == REMINDERS
    assert public.public_channel(bot, GUILD) == CHANNEL
    assert bot.store.get(GUILD, "golive_channel_id") == CHANNEL

    await bot.store.set(GUILD, "marathon_public_channel_id", HIGHLIGHTS)
    assert reminders.reminder_channel(bot, GUILD) == REMINDERS
    assert bot.store.get(GUILD, "golive_channel_id") == CHANNEL

    await highlighted(bot, cog, marathon)
    await at_fifteen(bot, cog, marathon)

    assert len(reminders_in(reminder_room)) == 1
    assert reminders_in(highlight_room) == [] and len(public_posts(bot, HIGHLIGHTS)) == 1
    assert reminders_in(bot.guild.channels[CHANNEL]) == []
    assert public_posts(bot) == []

    await bot.store.clear(GUILD, "marathon_reminder_channel_id")
    assert reminders.reminder_channel(bot, GUILD) == CHANNEL
    assert public.public_channel(bot, GUILD) == HIGHLIGHTS



async def public_marks(bot):
    cur = await bot.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = 'marathon.public_reminded' ORDER BY id"
    )
    return [json.loads(row["details"])["mark"] for row in await cur.fetchall()]


async def test_a_baf_runner_gets_the_public_copy_at_every_mark_of_every_run(bot, cog):
    await bot.store.set(GUILD, "marathon_reminder_minutes", "1440, 120, 15")
    cog.client.runs_given = [
        a_run(3, 1500, game="Super Metroid", people=(("Sky", "skyruns", "runner"),)),
        a_run(4, 1560, game="Kirby Air Riders"),
    ]
    marathon = await ready(bot, cog)
    for minutes in (59, 60, 61, 700, 1380, 1485, 1501):
        cog.clock = lambda minutes=minutes: NOW + timedelta(minutes=minutes)
        await follow(bot, cog, marathon)

    shown = reminders_in(bot.guild.channels[CHANNEL])
    assert len(shown) == 3 and reminders_in(the_thread(bot)) == []
    assert await public_marks(bot) == [1440, 120, 15]
    assert all("<@&" not in one.content for one in shown)


async def test_an_opted_out_runner_gets_no_public_copy_and_the_thread_still_does(bot, cog):
    marathon = await ready(bot, cog)
    said = await announce.set_opt_out(bot, bot.guild, FakeActor(), marathon, [SKY], True)
    assert said.ok, said.message

    await at_fifteen(bot, cog, marathon)

    assert len(reminders_in(the_thread(bot))) == 1
    assert reminders_in(bot.guild.channels[CHANNEL]) == []
    skipped = await details_of(bot.db, "marathon.public_reminder_skipped")
    assert skipped["because"] == "opted_out"
    assert "marathon.reminded" in await kinds(bot.db)


async def test_the_announcements_switch_off_stops_the_public_copy(bot, cog):
    marathon = await ready(bot, cog)
    said = await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.ANNOUNCE, False)
    assert said.ok, said.message

    await at_fifteen(bot, cog, marathon)

    assert len(reminders_in(the_thread(bot))) == 1
    assert reminders_in(bot.guild.channels[CHANNEL]) == []
    skipped = await details_of(bot.db, "marathon.public_reminder_skipped")
    assert skipped["because"] == "announcements_off"


async def test_a_co_runner_opted_out_is_left_out_of_the_public_copy(bot, cog):
    cog.client.runs_given = [
        a_run(
            3,
            30,
            game="Super Metroid",
            people=(("Sky", "skyruns", "runner"), ("Rivet", None, "runner")),
        ),
    ]
    marathon = await ready(bot, cog)
    paired = await pair_runner(bot, bot.guild, FakeActor(), marathon, "Rivet", 9002)
    assert paired.ok, paired.message
    await announce.set_opt_out(bot, bot.guild, FakeActor(), marathon, [SKY], True)

    await at_fifteen(bot, cog, marathon)

    (shown,) = reminders_in(bot.guild.channels[CHANNEL])
    assert "<@9002>" in shown.content and f"<@{SKY}>" not in shown.content
    staff = reminders_in(the_thread(bot))
    assert staff and f"<@{SKY}>" in staff[0].content


async def test_shadow_sends_the_public_copy_to_the_public_rehearsal_home(bot, cog):
    marathon = await ready(bot, cog)
    await bot.store.set(GUILD, "marathon_mode", "shadow")
    await bot.store.set(GUILD, "marathon_public_shadow_channel_id", LOG_CHANNEL)
    await bot.store.set(GUILD, "marathon_reminder_channel_id", REMINDERS)
    room(bot, REMINDERS, "baf-reminders")

    await at_fifteen(bot, cog, marathon)

    assert reminders_in(bot.guild.channels[REMINDERS]) == []
    copy = reminders_in(bot.guild.channels[LOG_CHANNEL])[0]
    assert copy.content.startswith(f"Rehearsal — this is where it would go: <#{REMINDERS}>")
    logged = await details_of(bot.db, "marathon.would_remind_public")
    assert logged["shadow_home"] == LOG_CHANNEL


async def test_a_marathon_posting_in_the_reminder_channel_itself_is_not_said_twice(bot, cog):
    await bot.store.set(GUILD, "marathon_track_makes_thread", False)
    marathon = await ready(bot, cog)

    await at_fifteen(bot, cog, marathon)

    assert len(reminders_in(bot.guild.channels[CHANNEL])) == 1
    logged = await details_of(bot.db, "marathon.public_reminder_skipped")
    assert logged["because"] == "same_channel"


async def test_no_channel_at_all_logs_and_the_thread_copy_still_posts(bot, cog, monkeypatch):
    monkeypatch.setattr(reminders, "reminder_channel", lambda bot, guild_id: None)
    marathon = await ready(bot, cog)

    await at_fifteen(bot, cog, marathon)

    assert len(reminders_in(the_thread(bot))) == 1
    assert (await details_of(bot.db, "marathon.public_reminder_failed"))["reason"] == "no_channel"
