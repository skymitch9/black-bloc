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
    update_marathon,
)
from black_bloc.marathon_sources import parse_gdq
from tests.cogs.content.test_marathon import (
    NOW,
    SKY,
    URL,
    FakeClient,
    a_run,
    bot,
    proposals,
    threading,
)
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
HOST = ("anarchy", "anarchyasf", "host")
HIDDEN_HEROES = [
    a_run(1, 60, game="Titanfall 2", people=(("clipboard", "cb", "runner"), HOST), length=85),
    a_run(2, 145, game="VHOLUME", people=(("sorbet", "ts", "runner"), HOST), length=35),
    a_run(3, 180, game="SPRAWL zero", people=(("sylllphie", "sy", "runner"), HOST), length=50),
]


async def show(bot, cog, runs, *, scan=True, clock=0, auto=False):
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
    await update_marathon(bot.db, marathon["id"], public_highlight=1 if auto else 0)
    return await tick_at(bot, cog, marathon, clock)


async def tick_at(bot, cog, marathon, minutes):
    cog.clock = lambda: NOW + timedelta(minutes=minutes)
    async with cog.lock(marathon["id"]):
        await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    return await get_marathon(bot.db, GUILD, marathon["id"])


async def walk(bot, cog, marathon, minutes):
    for one in minutes:
        await tick_at(bot, cog, marathon, one)


def posts(bot, channel_id=CHANNEL):
    return bot.guild.channels[channel_id].messages


def heads_ups(bot, channel_id=CHANNEL, member=ANARCHY):
    said = f"<@{member}> hosts **"
    return [one for one in posts(bot, channel_id) if one.content.startswith(said)]


def highlights(bot, channel_id=CHANNEL, name="anarchy"):
    return [one for one in posts(bot, channel_id) if one.content.startswith(f"**{name}** hosts **")]


def game_of(message):
    parts = message.content.split("**")
    return parts[3] if message.content.startswith("**") else parts[1]


def no_pings(message):
    mentions = message.kwargs["allowed_mentions"]
    return mentions.users is False and mentions.roles is False and mentions.everyone is False


async def run_named(bot, marathon, game):
    return next(one for one in await runs_of(bot.db, marathon["id"]) if one["game"] == game)


async def test_hidden_heroes_gets_three_heads_ups_each_at_its_runs_moment(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES)
    await walk(bot, cog, marathon, [30, 44])
    assert heads_ups(bot) == []
    await tick_at(bot, cog, marathon, 45)
    (first,) = heads_ups(bot)
    assert first.content.startswith(
        "<@8101> hosts **Titanfall 2** (Any%) on **Hidden Heroes** <t:"
    )
    assert no_pings(first)
    await walk(bot, cog, marathon, [61, 129])
    assert len(heads_ups(bot)) == 1
    await walk(bot, cog, marathon, [130, 146, 164])
    assert [game_of(one) for one in heads_ups(bot)] == ["Titanfall 2", "VHOLUME"]
    await walk(bot, cog, marathon, [165, 181, 231, 300])
    said = heads_ups(bot)
    assert [game_of(one) for one in said] == ["Titanfall 2", "VHOLUME", "SPRAWL zero"]
    assert all(no_pings(one) and "<@&" not in one.content for one in said)
    assert highlights(bot) == []
    assert (await kinds(bot.db)).count("marathon.host_reminded") == 3
    logged = await details_of(bot.db, "marathon.host_reminded")
    assert logged["members"] == [ANARCHY] and logged["mark"] == 15
    assert cogmod.counts_of(await runs_of(bot.db, marathon["id"])) == (3, 0)
    for kind in ("marathon.shouted", "marathon.reminded", "marathon.public_highlight_posted"):
        assert kind not in await kinds(bot.db)


async def test_the_heads_up_is_the_runners_public_reminder_with_the_host_word(bot, cog):
    await bot.store.set(GUILD, "marathon_public_reminder_template", "{member} {part} {game} {in}")
    await bot.store.set(GUILD, "marathon_part_host", "will be hosting")
    marathon = await show(bot, cog, HIDDEN_HEROES)
    await tick_at(bot, cog, marathon, 45)
    (said,) = [one for one in posts(bot) if one.content.startswith("<@8101>")]
    assert said.content.startswith("<@8101> will be hosting Titanfall 2 <t:")


async def test_no_highlight_until_staff_press_it_while_auto_highlight_is_off(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES)
    await walk(bot, cog, marathon, [45, 61, 146])
    assert highlights(bot) == []
    run = await run_named(bot, marathon, "VHOLUME")
    done = await hh.press(bot, bot.guild, FakeActor(), marathon, ANARCHY, "post", run_id=run["id"])
    assert done.ok and "is up in" in done.message
    (post,) = highlights(bot)
    assert post.content.startswith("**anarchy** hosts **VHOLUME** — Any%")
    assert " · on now · " in post.content and no_pings(post)
    await tick_at(bot, cog, marathon, 181)
    assert " · done · " in post.content
    assert len(highlights(bot)) == 1


async def test_auto_highlight_on_posts_one_at_each_runs_live_and_edits_it_to_done(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES, auto=True)
    await walk(bot, cog, marathon, [45, 59])
    assert highlights(bot) == []
    await tick_at(bot, cog, marathon, 61)
    (titanfall,) = highlights(bot)
    assert titanfall.content.startswith("**anarchy** hosts **Titanfall 2**")
    assert " · on now · " in titanfall.content and no_pings(titanfall)
    await walk(bot, cog, marathon, [130, 146])
    assert [game_of(one) for one in highlights(bot)] == ["Titanfall 2", "VHOLUME"]
    assert " · done · " in titanfall.content
    await walk(bot, cog, marathon, [165, 181, 231, 400])
    found = highlights(bot)
    assert [game_of(one) for one in found] == ["Titanfall 2", "VHOLUME", "SPRAWL zero"]
    assert [one.content.split(" · ")[2] for one in found] == ["done"] * 3
    assert all(edit["allowed_mentions"].roles is False for one in found for edit in one.edits)
    assert (await kinds(bot.db)).count("marathon.host_highlight_posted") == 3
    assert len(heads_ups(bot)) == 3
    assert cogmod.counts_of(await runs_of(bot.db, marathon["id"])) == (3, 0)


async def test_staff_marking_a_hosted_run_live_highlights_it_under_auto(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES, auto=True)
    run = await run_named(bot, marathon, "VHOLUME")
    said = await cogmod.mark_live(bot, bot.guild, FakeActor(), marathon, run)
    assert said.ok, said.message
    (post,) = highlights(bot)
    assert game_of(post) == "VHOLUME"


async def test_a_restart_posts_neither_the_highlight_nor_the_heads_up_again(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES, auto=True)
    await walk(bot, cog, marathon, [45, 61])
    restarted = type(cog)(bot)
    restarted.client = cog.client
    restarted.clock = cog.clock
    bot.cogs[cogmod.COG_NAME] = restarted

    await restarted.tick_once()
    await walk(bot, restarted, marathon, [62, 70])
    assert len(heads_ups(bot)) == 1 and len(highlights(bot)) == 1
    assert highlights(bot)[0].edits == []


@pytest.mark.parametrize("off", ["key", "scan"])
async def test_the_key_off_or_scan_hosts_off_posts_nothing(bot, cog, off):
    if off == "key":
        await bot.store.set(GUILD, "marathon_host_highlights", False)
    marathon = await show(bot, cog, HIDDEN_HEROES, scan=off != "scan", auto=True)
    await walk(bot, cog, marathon, [45, 61, 130, 146, 165, 181, 231])
    assert heads_ups(bot) == [] and highlights(bot) == []
    assert "marathon.host_highlight_posted" not in await kinds(bot.db)
    if off == "scan":
        said = await hh.press(bot, bot.guild, FakeActor(), marathon, ANARCHY, "post")
        assert not said.ok and said.code == mhh.NOT_SCANNED_CODE and "Scan hosts" in said.message


async def test_the_heads_up_waits_for_public_reminders(bot, cog):
    await bot.store.set(GUILD, "marathon_public_reminders", False)
    marathon = await show(bot, cog, HIDDEN_HEROES)
    await walk(bot, cog, marathon, [45, 130, 165])
    assert heads_ups(bot) == []


async def test_a_heads_up_too_late_is_skipped_not_posted(bot, cog):
    await bot.store.set(GUILD, "marathon_reminder_stale_minutes", 5)
    marathon = await show(bot, cog, HIDDEN_HEROES, clock=20)
    await walk(bot, cog, marathon, [52, 55])
    assert heads_ups(bot) == []
    skipped = await details_of(bot.db, "marathon.host_reminder_skipped")
    assert skipped["because"] == "late" and skipped["game"] == "Titanfall 2"
    assert (await kinds(bot.db)).count("marathon.host_reminder_skipped") == 1


async def test_a_baf_runners_run_is_unchanged_beside_hosted_runs(bot, cog):
    marathon = await show(bot, cog, [*HOSTED_ONLY, SKY_SLOT])
    rows = {row["game"]: row for row in await runs_of(bot.db, marathon["id"])}
    assert mt.member_ids(rows["Super Metroid"]) == [SKY]
    assert said_about(bot, "Super Metroid")
    assert cogmod.counts_of(list(rows.values())) == (4, 1)
    await tick_at(bot, cog, marathon, 15)
    (heads,) = heads_ups(bot)
    assert game_of(heads) == "Titanfall 2"
    await tick_at(bot, cog, marathon, 195)
    assert not any(one.content.startswith(f"<@{SKY}> hosts") for one in posts(bot))
    assert any(one.content.startswith(f"<@{SKY}> runs **Super Metroid**") for one in posts(bot))


async def test_staff_take_it_down_and_put_it_back_in_the_same_message(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES, auto=True)
    await tick_at(bot, cog, marathon, 61)
    (post,) = highlights(bot)
    run_id = (await details_of(bot.db, "marathon.host_highlight_posted"))["run_id"]

    down = await hh.press(bot, bot.guild, FakeActor(), marathon, ANARCHY, "remove")
    assert down.ok and "taken down" in down.message
    assert post.content == "Staff took down the highlight for **anarchy** on **Hidden Heroes**."
    await tick_at(bot, cog, marathon, 70)
    assert post.content.startswith("Staff took down")
    again = await hh.press(bot, bot.guild, FakeActor(), marathon, ANARCHY, "remove", run_id=run_id)
    assert again.ok and "nothing to take down" in again.message

    back = await hh.press(bot, bot.guild, FakeActor(), marathon, ANARCHY, "post", run_id=run_id)
    assert back.ok and "is up in" in back.message
    assert post.content.startswith("**anarchy** hosts **Titanfall 2**")
    assert len(highlights(bot)) == 1
    assert "marathon.host_highlight_restored" in await kinds(bot.db)
    assert (await details_of(bot.db, "marathon.host_highlight_removed"))["edited"] is True


async def test_a_run_staff_took_down_is_never_auto_posted_again(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES, auto=True)
    run_id = (await run_named(bot, marathon, "VHOLUME"))["id"]
    for to in ("post", "remove"):
        said = await hh.press(bot, bot.guild, FakeActor(), marathon, ANARCHY, to, run_id=run_id)
        assert said.ok
    await walk(bot, cog, marathon, [146, 150])
    assert [one for one in highlights(bot) if game_of(one) == "VHOLUME"] == []


async def test_a_move_on_someone_who_hosts_nothing_is_refused_in_words(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES)
    said = await hh.press(bot, bot.guild, FakeActor(), marathon, SKY, "post")
    assert not said.ok and said.status == 404 and "hosts nothing" in said.message
    said = await hh.press(bot, bot.guild, FakeActor(), marathon, ANARCHY, "shout")
    assert not said.ok and said.status == 422


async def test_shadow_mode_rehearses_both_in_the_public_rehearsal_home(bot, cog):
    await bot.store.set(GUILD, "marathon_mode", "shadow")
    bot.guild.channels[REHEARSAL] = FakeChannel(REHEARSAL)
    await bot.store.set(GUILD, "marathon_public_shadow_channel_id", REHEARSAL)
    marathon = await show(bot, cog, HIDDEN_HEROES, auto=True)
    await walk(bot, cog, marathon, [45, 61])
    assert heads_ups(bot) == [] and highlights(bot) == []
    rehearsed = [one.content for one in posts(bot, REHEARSAL)]
    assert any("<@8101> hosts **Titanfall 2**" in one for one in rehearsed)
    assert any("**anarchy** hosts **Titanfall 2**" in one for one in rehearsed)
    assert "marathon.would_post_host_highlight" in await kinds(bot.db)
    assert "marathon.would_remind_host" in await kinds(bot.db)


async def test_the_sgdq_tracker_heads_ups_only_the_runs_the_host_hosts(bot, cog):
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

    async def at(when):
        cog.clock = lambda: when
        async with cog.lock(marathon["id"]):
            await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))

    for hour, minute in ((21, 40), (21, 43), (22, 30), (22, 49), (23, 6), (23, 30)):
        await at(datetime(2026, 7, 5, hour, minute, tzinfo=UTC))
    await at(datetime(2026, 7, 6, 1, 5, tzinfo=UTC))
    said = heads_ups(bot, member=KINGS)
    assert [game_of(one) for one in said] == [
        "I Am Your Beast",
        "Devil May Cry 5: Special Edition",
    ]
    assert all("The Checkpoint" not in one.content for one in posts(bot))
    assert highlights(bot, name="TheKingsPride") == []
    assert cogmod.counts_of(await runs_of(bot.db, marathon["id"]))[1] == 0


@pytest.mark.parametrize("stop", ["key", "scan"])
async def test_a_post_already_up_follows_its_run_to_the_end_after_a_switch_goes_off(
    bot, cog, stop
):
    marathon = await show(bot, cog, HIDDEN_HEROES, auto=True)
    await tick_at(bot, cog, marathon, 61)
    (post,) = highlights(bot)
    if stop == "key":
        await bot.store.set(GUILD, "marathon_host_highlights", False)
    else:
        await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.SCAN, False)
    await walk(bot, cog, marathon, [130, 146, 181])
    assert " · done · " in post.content
    assert len(highlights(bot)) == 1 and heads_ups(bot) == []
