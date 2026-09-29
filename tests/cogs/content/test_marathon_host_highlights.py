# ruff: noqa: F401, F811
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from black_bloc import marathon as mt
from black_bloc import marathon_host_highlights as mhh
from black_bloc import marathon_hosts as mh
from black_bloc.cogs.content import marathon as cogmod
from black_bloc.cogs.content import marathon_host_highlights as hh
from black_bloc.cogs.content import marathon_hosts as hosts
from black_bloc.cogs.content import marathon_inbox as inbox
from black_bloc.cogs.content.marathon import (
    create_marathon,
    get_marathon,
    pair_runner,
    runs_of,
)
from black_bloc.marathon_sources import parse_gdq
from black_bloc.settings_store import SettingError
from tests.cogs.content.test_marathon import NOW, SKY, URL, FakeClient, bot, proposals, threading
from tests.cogs.content.test_marathon_hosts import (
    ANARCHY,
    HOSTED_ONLY,
    SHOW_ROOM,
    SKY_SLOT,
    cog,
    quiet_calendar,
    said_about,
)
from tests.cogs.content.test_spotlight import (
    CHANNEL,
    GUILD,
    FakeActor,
    FakeChannel,
    details_of,
    kinds,
)

FIXTURE = Path(__file__).parents[2] / "fixtures" / "marathon" / "gdq_sgdq2026_runs.json"
REHEARSAL = 661
KINGS = 8102


async def show(bot, cog, runs, *, scan=True, clock=15):
    threading(bot, SHOW_ROOM)
    await bot.store.set(GUILD, "events_announce_channel_id", SHOW_ROOM)
    await bot.store.set(GUILD, "marathon_track_makes_thread", True)
    cog.client.runs_given = list(runs)
    made = await create_marathon(bot, bot.guild, FakeActor(), name="Hidden Heroes", url=URL)
    assert made.ok, made.message
    paired = await pair_runner(
        bot, bot.guild, FakeActor(), made.value, "anarchy", ANARCHY, everywhere=True
    )
    assert paired.ok, paired.message
    done = await inbox.track(bot, bot.guild, FakeActor(), made.value)
    assert done.ok, done.message
    marathon = await get_marathon(bot.db, GUILD, made.value["id"])
    if scan:
        switched = await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.SCAN, True)
        assert switched.ok, switched.message
    return await tick_at(bot, cog, marathon, clock)


async def tick_at(bot, cog, marathon, minutes):
    cog.clock = lambda: NOW + timedelta(minutes=minutes)
    async with cog.lock(marathon["id"]):
        await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    return await get_marathon(bot.db, GUILD, marathon["id"])


def highlights(bot, channel_id=CHANNEL, name="anarchy"):
    return [
        one
        for one in bot.guild.channels[channel_id].messages
        if f"**{name}**" in one.content and one not in heads_ups(bot, channel_id, name)
    ]


def heads_ups(bot, channel_id=CHANNEL, name="anarchy"):
    return [
        one
        for one in bot.guild.channels[channel_id].messages
        if one.content.startswith(f"**{name}** is hosting") and ":R>" in one.content
    ]


def now_text(message):
    return message.content


def no_pings(message):
    mentions = message.kwargs["allowed_mentions"]
    return mentions.users is False and mentions.roles is False and mentions.everyone is False


async def test_hidden_heroes_gets_one_host_highlight_that_follows_the_block(bot, cog):
    marathon = await show(bot, cog, HOSTED_ONLY)

    posted = [one for one in highlights(bot) if "hosts **Hidden Heroes**" in one.content]
    assert len(posted) == 1
    (post,) = posted
    assert post.content.startswith("**anarchy** hosts **Hidden Heroes** · <t:")
    assert "https://twitch.tv/anarchyasf" in post.content and "<@" not in post.content
    assert no_pings(post)
    (heads,) = heads_ups(bot)
    assert no_pings(heads) and "<t:" in heads.content
    logged = await details_of(bot.db, "marathon.host_highlight_posted")
    assert (logged["member_id"], logged["channel_id"], logged["state"]) == (
        ANARCHY,
        CHANNEL,
        "upcoming",
    )
    assert len(logged["runs"]) == 3
    assert (await details_of(bot.db, "marathon.host_reminded"))["mark"] == 15

    rows = await runs_of(bot.db, marathon["id"])
    assert cogmod.counts_of(rows) == (3, 0)
    for game in ("Titanfall 2", "VHOLUME", "SPRAWL zero"):
        assert said_about(bot, game) == []
    for kind in ("marathon.shouted", "marathon.reminded", "marathon.public_highlight_posted"):
        assert kind not in await kinds(bot.db)

    await tick_at(bot, cog, marathon, 31)
    assert now_text(post).startswith("**anarchy** is hosting **Hidden Heroes** now")
    await tick_at(bot, cog, marathon, 151)
    assert now_text(post).startswith("**anarchy** is hosting **Hidden Heroes** now")
    await tick_at(bot, cog, marathon, 302)
    assert now_text(post).startswith("**anarchy** hosted **Hidden Heroes**")
    assert all(edit["allowed_mentions"].roles is False for edit in post.edits)
    assert len(heads_ups(bot)) == 1
    assert (await kinds(bot.db)).count("marathon.host_highlight_posted") == 1
    assert "marathon.shouted" not in await kinds(bot.db)


async def test_a_restart_posts_neither_the_highlight_nor_the_heads_up_again(bot, cog):
    marathon = await show(bot, cog, HOSTED_ONLY)
    restarted = type(cog)(bot)
    restarted.client = cog.client
    restarted.clock = cog.clock
    bot.cogs[cogmod.COG_NAME] = restarted

    await restarted.tick_once()
    await tick_at(bot, restarted, marathon, 16)

    assert len([one for one in highlights(bot) if "hosts **" in one.content]) == 1
    assert len(heads_ups(bot)) == 1
    post = next(one for one in highlights(bot) if "hosts **" in one.content)
    assert post.edits == []


async def test_the_key_off_posts_nothing_for_hosts(bot, cog):
    await bot.store.set(GUILD, "marathon_host_highlights", False)
    await show(bot, cog, HOSTED_ONLY)
    assert highlights(bot) == [] and heads_ups(bot) == []
    assert "marathon.host_highlight_posted" not in await kinds(bot.db)


async def test_without_scan_hosts_there_is_no_host_to_highlight(bot, cog):
    marathon = await show(bot, cog, HOSTED_ONLY, scan=False)
    assert highlights(bot) == [] and heads_ups(bot) == []
    said = await hh.press(bot, bot.guild, FakeActor(), marathon, ANARCHY, "post")
    assert not said.ok and said.code == mhh.NOT_SCANNED_CODE and "Scan hosts" in said.message


async def test_the_heads_up_waits_for_public_reminders(bot, cog):
    await bot.store.set(GUILD, "marathon_public_reminders", False)
    await show(bot, cog, HOSTED_ONLY)
    assert heads_ups(bot) == [] and len(highlights(bot)) == 1


async def test_a_baf_runners_run_is_unchanged_beside_a_host_block(bot, cog):
    marathon = await show(bot, cog, [*HOSTED_ONLY, SKY_SLOT])
    rows = {row["game"]: row for row in await runs_of(bot.db, marathon["id"])}
    assert mt.member_ids(rows["Super Metroid"]) == [SKY]
    assert said_about(bot, "Super Metroid")
    assert cogmod.counts_of(list(rows.values())) == (4, 1)
    posted = await details_of(bot.db, "marathon.host_highlight_posted")
    assert posted["member_id"] == ANARCHY and rows["Super Metroid"]["id"] not in posted["runs"]
    assert highlights(bot, name="Sky") == []


async def test_staff_take_it_down_and_put_it_back_in_the_same_message(bot, cog):
    marathon = await show(bot, cog, HOSTED_ONLY)
    (post,) = [one for one in highlights(bot) if "hosts **" in one.content]

    down = await hh.press(bot, bot.guild, FakeActor(), marathon, ANARCHY, "remove")
    assert down.ok and "taken down" in down.message
    assert now_text(post) == "Staff took down the highlight for **anarchy** on **Hidden Heroes**."
    await tick_at(bot, cog, marathon, 31)
    assert now_text(post).startswith("Staff took down")
    again = await hh.press(bot, bot.guild, FakeActor(), marathon, ANARCHY, "remove")
    assert again.ok and "nothing to take down" in again.message

    back = await hh.press(bot, bot.guild, FakeActor(), marathon, ANARCHY, "post")
    assert back.ok and "is up in" in back.message
    assert now_text(post).startswith("**anarchy** is hosting **Hidden Heroes** now")
    assert len(bot.guild.channels[CHANNEL].messages) == 2
    assert "marathon.host_highlight_restored" in await kinds(bot.db)
    assert (await details_of(bot.db, "marathon.host_highlight_removed"))["edited"] is True


async def test_a_move_on_someone_who_hosts_nothing_is_refused_in_words(bot, cog):
    marathon = await show(bot, cog, HOSTED_ONLY)
    said = await hh.press(bot, bot.guild, FakeActor(), marathon, SKY, "post")
    assert not said.ok and said.status == 404 and "hosts nothing" in said.message
    said = await hh.press(bot, bot.guild, FakeActor(), marathon, ANARCHY, "shout")
    assert not said.ok and said.status == 422


async def test_shadow_mode_rehearses_it_in_the_public_rehearsal_home(bot, cog):
    await bot.store.set(GUILD, "marathon_mode", "shadow")
    bot.guild.channels[REHEARSAL] = FakeChannel(REHEARSAL)
    await bot.store.set(GUILD, "marathon_public_shadow_channel_id", REHEARSAL)
    await show(bot, cog, HOSTED_ONLY)
    assert highlights(bot) == []
    rehearsed = bot.guild.channels[REHEARSAL].messages
    assert any("hosts **Hidden Heroes**" in one.content for one in rehearsed)
    assert "marathon.would_post_host_highlight" in await kinds(bot.db)
    assert "marathon.would_remind_host" in await kinds(bot.db)


async def test_an_unknown_placeholder_is_refused_in_words(bot):
    for key in (
        "marathon_host_highlight_template",
        "marathon_host_highlight_live_template",
        "marathon_host_highlight_done_template",
        "marathon_host_reminder_template",
    ):
        with pytest.raises(SettingError, match="`{game}` is not something Black Bloc can fill"):
            await bot.store.set(GUILD, key, "{name} on {game}")
        assert await bot.store.set(GUILD, key, "{mention} hosts {show} {link}")


async def test_a_gdq_tracker_host_block_runs_across_a_hostless_segment(bot, cog):
    runs = parse_gdq(json.loads(FIXTURE.read_text("utf-8")))
    cog.client.runs_given = runs
    made = await create_marathon(bot, bot.guild, FakeActor(), name="SGDQ 2026", url=URL)
    assert made.ok, made.message
    paired = await pair_runner(
        bot, bot.guild, FakeActor(), made.value, "TheKingsPride", KINGS, everywhere=True
    )
    assert paired.ok, paired.message
    assert (await inbox.track(bot, bot.guild, FakeActor(), made.value)).ok
    marathon = await get_marathon(bot.db, GUILD, made.value["id"])
    await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.SCAN, True)
    start = datetime(2026, 7, 5, 21, 58, tzinfo=UTC)

    async def at(when):
        cog.clock = lambda: when
        async with cog.lock(marathon["id"]):
            await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))

    await at(start - timedelta(minutes=15))
    posts = highlights(bot, name="TheKingsPride")
    (post,) = [one for one in posts if "hosts **SGDQ 2026**" in one.content]
    assert "https://twitch.tv/thekingspride" in post.content
    assert len(heads_ups(bot, name="TheKingsPride")) == 1
    logged = await details_of(bot.db, "marathon.host_highlight_posted")
    by_id = {row["id"]: row["game"] for row in await runs_of(bot.db, marathon["id"])}
    assert [by_id[one] for one in logged["runs"]] == [
        "I Am Your Beast",
        "Devil May Cry 5: Special Edition",
    ]

    await at(datetime(2026, 7, 5, 23, 10, tzinfo=UTC))
    assert now_text(post).startswith("**TheKingsPride** is hosting **SGDQ 2026** now")
    await at(datetime(2026, 7, 6, 0, 30, tzinfo=UTC))
    assert now_text(post).startswith("**TheKingsPride** is hosting")
    await at(datetime(2026, 7, 6, 1, 5, tzinfo=UTC))
    assert now_text(post).startswith("**TheKingsPride** hosted **SGDQ 2026**")
    assert (await kinds(bot.db)).count("marathon.host_highlight_posted") == 1
    assert cogmod.counts_of(await runs_of(bot.db, marathon["id"]))[1] == 0


@pytest.mark.parametrize("stop", ["key", "scan"])
async def test_a_post_already_up_follows_its_block_to_the_end_after_a_switch_goes_off(
    bot, cog, stop
):
    marathon = await show(bot, cog, HOSTED_ONLY)
    (post,) = highlights(bot)
    if stop == "key":
        await bot.store.set(GUILD, "marathon_host_highlights", False)
    else:
        await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.SCAN, False)

    await tick_at(bot, cog, marathon, 31)
    assert now_text(post).startswith("**anarchy** is hosting **Hidden Heroes** now")
    await tick_at(bot, cog, marathon, 302)
    assert now_text(post).startswith("**anarchy** hosted **Hidden Heroes**")
    assert len(highlights(bot)) == 1
