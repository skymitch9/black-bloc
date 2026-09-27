from black_bloc import marathon_ping as mp
from black_bloc.cogs.content import marathon as cogmod
from black_bloc.cogs.content.marathon import get_marathon
from black_bloc.cogs.content.marathon_ping import set_ping_role
from black_bloc.cogs.content.spotlight import set_ping_mode, windows_for
from tests.cogs.content.test_marathon import (  # noqa: F401
    CHANNEL_ROLE,
    FAN_ROLE,
    a_run,
    added,
    bot,
    cog,
    gdq_row,
    reminders,
)
from tests.cogs.content.test_spotlight import GUILD, FakeActor, details_of, kinds

SKY_RUN = (("Sky", "skyruns", "runner"),)


async def pinging_channel(bot):  # noqa: F811
    channel = await gdq_row(bot)
    await set_ping_mode(bot, bot.guild, FakeActor(), channel["id"], "events")
    return channel


async def test_a_new_marathon_starts_off_its_reminder_mentions_no_role_and_no_window(bot, cog):  # noqa: F811
    channel = await pinging_channel(bot)
    cog.client.runs_given = [a_run(3, 15, game="Super Metroid", people=SKY_RUN)]
    marathon = await added(bot, cog, channel=channel)

    assert marathon["ping_role"] == 0
    assert await windows_for(bot.db, channel["id"]) == []
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    said = (await reminders(bot))[-1]
    assert "<@&" not in said.content
    assert said.kwargs["allowed_mentions"].roles is False
    assert (await details_of(bot.db, "marathon.reminded"))["pinged"] is False


async def test_the_default_key_on_makes_a_new_marathon_ping(bot, cog):  # noqa: F811
    await bot.store.set(GUILD, "marathon_ping_role_default", True)
    channel = await pinging_channel(bot)
    marathon = await added(bot, cog, channel=channel)
    assert marathon["ping_role"] == 1
    assert len(await windows_for(bot.db, channel["id"])) == 1
    assert (await details_of(bot.db, "marathon.added"))["ping_role"] is True


async def test_switching_it_on_makes_the_window_and_the_mention_and_off_takes_both_away(bot, cog):  # noqa: F811
    channel = await pinging_channel(bot)
    cog.client.runs_given = [a_run(3, 15, game="Super Metroid", people=SKY_RUN)]
    marathon = await added(bot, cog, channel=channel)

    done = await set_ping_role(bot, bot.guild, FakeActor(), marathon, True)
    assert done.ok and "pings again" in done.message and done.value["ping_role"] == 1
    windows = await windows_for(bot.db, channel["id"])
    assert len(windows) == 1 and windows[0]["source_id"] == marathon["id"]
    said = await details_of(bot.db, "marathon.ping_role_set")
    assert (said["from"], said["to"], said["via"]) == (False, True, "discord")
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert (await reminders(bot))[-1].content.startswith(f"<@&{FAN_ROLE}> <@&{CHANNEL_ROLE}> ")

    done = await set_ping_role(bot, bot.guild, FakeActor(), done.value, "off")
    assert done.ok and "pings no role" in done.message
    assert await windows_for(bot.db, channel["id"]) == []
    assert "marathon.window_dropped" in await kinds(bot.db)


async def test_the_same_state_changes_nothing_and_a_bad_word_is_refused(bot, cog):  # noqa: F811
    marathon = await added(bot, cog)
    same = await set_ping_role(bot, bot.guild, FakeActor(), marathon, False)
    assert same.ok and "already has that" in same.message
    assert "marathon.ping_role_set" not in await kinds(bot.db)
    bad = await set_ping_role(bot, bot.guild, FakeActor(), marathon, "sometimes")
    assert not bad.ok and bad.status == 422 and bad.code == mp.BAD_PING_ROLE_CODE


async def test_the_answers_and_the_card_words_are_keys(bot, cog):  # noqa: F811
    await bot.store.set(GUILD, "marathon_ping_role_on_said", "{marathon} rings.")
    await bot.store.set(GUILD, "marathon_ping_role_button_on", "Ring it")
    await bot.store.set(GUILD, "marathon_ping_role_line_off", "Silent")
    marathon = await added(bot, cog, channel=await gdq_row(bot))

    embed, view = await cogmod.build_card(bot, bot.guild, marathon["id"])
    labels = [getattr(one, "label", None) for one in view.children]
    assert "Ring it" in labels and "Silent" in embed.description
    done = await set_ping_role(bot, bot.guild, FakeActor(), marathon, True)
    assert done.message == "AGDQ 2027 rings."
    _, view = await cogmod.build_card(bot, bot.guild, marathon["id"])
    assert "Stop pinging" in [getattr(one, "label", None) for one in view.children]
    assert all(len([one for one in view.children if one.row == row]) <= 5 for row in range(5))
