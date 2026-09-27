# ruff: noqa: F401, F811
from datetime import timedelta

from black_bloc import settings_store
from black_bloc.cogs.content import marathon_public as public
from black_bloc.cogs.content import marathon_public_reminders as reminders
from black_bloc.cogs.content.marathon import create_marathon, update_marathon
from tests.cogs.content.test_marathon import FAN_ROLE, NOW, URL, bot, cog, threading
from tests.cogs.content.test_marathon_public import named, public_posts, ready
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


async def test_a_tracked_marathons_reminder_posts_in_the_thread_and_the_reminder_channel(bot, cog):
    marathon = await ready(bot, cog)

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

    await public.press(
        bot,
        bot.guild,
        FakeActor(),
        marathon["id"],
        (await run_of(bot, marathon, "Super Metroid"))["id"],
        "post",
    )
    await at_fifteen(bot, cog, marathon)

    assert len(reminders_in(reminder_room)) == 1
    assert reminders_in(highlight_room) == [] and len(public_posts(bot, HIGHLIGHTS)) == 1
    assert reminders_in(bot.guild.channels[CHANNEL]) == []
    assert public_posts(bot) == []

    await bot.store.clear(GUILD, "marathon_reminder_channel_id")
    assert reminders.reminder_channel(bot, GUILD) == CHANNEL
    assert public.public_channel(bot, GUILD) == HIGHLIGHTS


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
