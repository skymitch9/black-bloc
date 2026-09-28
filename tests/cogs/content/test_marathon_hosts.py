# ruff: noqa: F811
import asyncio
from datetime import timedelta

import pytest

from black_bloc import marathon as mt
from black_bloc import marathon_hosts as mh
from black_bloc import marathon_public as mp
from black_bloc.cogs.content import marathon as cogmod
from black_bloc.cogs.content import marathon_hosts as hosts
from black_bloc.cogs.content import marathon_inbox as inbox
from black_bloc.cogs.content import marathon_people as people
from black_bloc.cogs.content.marathon import (
    create_marathon,
    get_marathon,
    pair_runner,
    remove_marathon,
    runs_of,
)
from black_bloc.cogs.content.marathon_events import set_event_mode
from black_bloc.cogs.content.spotlight import channel_by_login
from black_bloc.events import get_event
from tests.cogs.content.test_marathon import (  # noqa: F401
    NOW,
    SKY,
    URL,
    FakeClient,
    a_run,
    at,
    bot,
    proposals,
    threading,
    tracked,
)
from tests.cogs.content.test_spotlight import CHANNEL, GUILD, FakeActor, details_of, kinds

ANARCHY = 8101
HIDDEN_HEROES = [
    a_run(
        1,
        60,
        game="Mega Man X",
        people=(("Quill", "quillruns", "runner"), ("anarchy", "anarchyasf", "host")),
    ),
    a_run(
        2,
        120,
        game="Metroid Fusion",
        people=(("Sky", "skyruns", "runner"), ("anarchy", "anarchyasf", "host")),
    ),
    a_run(
        3,
        180,
        game="Shovel Knight",
        people=(("Rook", "rookplays", "runner"), ("anarchy", "anarchyasf", "host")),
    ),
]


@pytest.fixture(autouse=True)
async def quiet_calendar(bot):  # noqa: F811
    await bot.store.set(GUILD, "events_create_scheduled", False)


@pytest.fixture
def cog(bot):  # noqa: F811
    made = cogmod.Marathons(bot)
    made.client = FakeClient(runs=HIDDEN_HEROES)
    made.clock = lambda: NOW
    bot.cogs[cogmod.COG_NAME] = made
    return made


async def hidden_heroes(bot, mode=None):  # noqa: F811
    outcome = await create_marathon(
        bot, bot.guild, FakeActor(), name="Hidden Heroes", url=URL, event_mode=mode
    )
    assert outcome.ok, outcome.message
    marathon = await tracked(bot, outcome.value)
    paired = await pair_runner(
        bot, bot.guild, FakeActor(), marathon, "anarchy", ANARCHY, everywhere=True
    )
    assert paired.ok, paired.message
    return await get_marathon(bot.db, GUILD, marathon["id"])


async def board(bot, marathon):  # noqa: F811
    fresh = await get_marathon(bot.db, GUILD, marathon["id"])
    return await people.people_state(bot, bot.guild, fresh)


def named(rows, name):
    return next((one for one in rows if one["name"] == name), None)


async def scan_on(bot, marathon):  # noqa: F811
    outcome = await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.SCAN, True)
    assert outcome.ok, outcome.message
    return outcome


async def test_with_hosts_not_scanned_anarchy_is_not_baf(bot, cog):  # noqa: F811
    marathon = await hidden_heroes(bot)
    state = await board(bot, marathon)
    assert named(state["baf"], "anarchy") is None
    assert named(state["others"], "anarchy")["parts"] == [mt.HOST]
    assert not any(
        mt.is_ours(row)
        for row in await runs_of(bot.db, marathon["id"])
        if row["game"] != "Metroid Fusion"
    )


async def test_scan_hosts_on_makes_the_host_baf_marked_host_and_off_takes_it_back(
    bot,
    cog,  # noqa: F811
):
    marathon = await hidden_heroes(bot)
    outcome = await scan_on(bot, marathon)
    assert outcome.message.startswith("**Hidden Heroes** scans its hosts now")
    assert (await get_marathon(bot.db, GUILD, marathon["id"]))["scan_hosts"] == 1
    anarchy = named((await board(bot, marathon))["baf"], "anarchy")
    assert anarchy["user_id"] == ANARCHY and anarchy["parts"] == [mt.HOST]
    assert len(anarchy["runs"]) == 3
    row = await details_of(bot.db, "marathon.scan_hosts_set")
    assert (row["from"], row["to"], row["on"]) == (None, True, True)

    off = await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.SCAN, "off")
    assert off.ok and "no longer scans" in off.message
    assert named((await board(bot, marathon))["baf"], "anarchy") is None


async def test_a_marathon_that_follows_the_setting_scans_when_the_setting_says(
    bot,
    cog,  # noqa: F811
):
    marathon = await hidden_heroes(bot)
    await bot.store.set(GUILD, "marathon_scan_hosts_default", True)
    await cog.rematch(bot.guild, marathon)
    assert named((await board(bot, marathon))["baf"], "anarchy") is not None
    kept = await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.SCAN, False)
    assert kept.ok
    assert named((await board(bot, marathon))["baf"], "anarchy") is None
    back = await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.SCAN, "follow")
    assert back.ok
    fresh = await get_marathon(bot.db, GUILD, marathon["id"])
    assert fresh["scan_hosts"] is None
    assert named((await board(bot, marathon))["baf"], "anarchy") is not None


async def test_a_switch_word_that_is_not_one_is_refused_in_words(bot, cog):  # noqa: F811
    marathon = await hidden_heroes(bot)
    outcome = await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.SCAN, "maybe")
    assert not outcome.ok and outcome.message == (
        "Say on, off or follow for **Scan hosts**, so nothing was changed."
    )


async def test_spotlight_a_host_gets_the_host_note_and_their_hosted_span(
    bot,
    cog,  # noqa: F811
):
    marathon = await hidden_heroes(bot)
    await scan_on(bot, marathon)
    outcome = await people.spotlight_runner(bot, bot.guild, FakeActor(), marathon, "anarchyasf")
    assert outcome.ok, outcome.message
    row = await channel_by_login(bot.db, GUILD, "anarchyasf")
    assert (
        row is not None
        and row["spotlight"] == 1
        and row["note"] == ("anarchy hosting Hidden Heroes")
    )
    assert row["starts_at"] is None
    assert row["expires_at"] == (NOW + timedelta(minutes=180 + 60 + 120)).isoformat()
    assert (await details_of(bot.db, "marathon.runner_spotlit"))["hosting"] is True
    anarchy = named((await board(bot, marathon))["baf"], "anarchy")
    assert anarchy["spotlight_id"] == row["id"]
    stopped = await people.unspotlight_runner(bot, bot.guild, FakeActor(), marathon, "anarchy")
    assert stopped.ok and await channel_by_login(bot.db, GUILD, "anarchyasf") is None


async def test_the_host_note_is_a_key(bot, cog):  # noqa: F811
    marathon = await hidden_heroes(bot)
    await bot.store.set(GUILD, "marathon_spotlight_host_note_template", "{name} on the mic")
    outcome = await people.spotlight_runner(bot, bot.guild, FakeActor(), marathon, "anarchy")
    assert outcome.ok, outcome.message
    assert (await channel_by_login(bot.db, GUILD, "anarchyasf"))["note"] == "anarchy on the mic"


async def test_a_runner_spotlight_keeps_the_runner_note(bot, cog):  # noqa: F811
    marathon = await hidden_heroes(bot)
    await scan_on(bot, marathon)
    outcome = await people.spotlight_runner(bot, bot.guild, FakeActor(), marathon, "skyruns")
    assert outcome.ok, outcome.message
    assert (await channel_by_login(bot.db, GUILD, "skyruns"))["note"] == "Sky at Hidden Heroes"


async def test_host_events_make_one_event_over_the_hosts_span(bot, cog, proposals):  # noqa: F811
    marathon = await hidden_heroes(bot)
    await scan_on(bot, marathon)
    assert "marathon.host_event_made" not in await kinds(bot.db)
    outcome = await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.EVENTS, True)
    assert outcome.ok and "an event for each BaF host" in outcome.message
    fresh = await get_marathon(bot.db, GUILD, marathon["id"])
    ids = mh.event_ids(fresh)
    assert list(ids) == [ANARCHY]
    event = await get_event(bot.db, ids[ANARCHY])
    assert event["title"] == "anarchy hosts Hidden Heroes"
    assert event["description"] == (
        "anarchy hosts 3 run(s) on Hidden Heroes: Mega Man X, Metroid Fusion, Shovel Knight. "
        "Read from the schedule; times follow it."
    )
    assert event["starts_at"] == at(60) and event["ends_at"] == at(240)
    assert event["location"] == "https://twitch.tv/anarchyasf"
    made = await details_of(bot.db, "marathon.host_event_made")
    assert made["member_id"] == ANARCHY and len(made["runs"]) == 3

    await hosts.sync_host_events(bot, bot.guild, fresh)
    assert (await kinds(bot.db)).count("marathon.host_event_made") == 1


async def test_host_events_need_the_host_scanned(bot, cog, proposals):  # noqa: F811
    marathon = await hidden_heroes(bot)
    await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.EVENTS, True)
    assert mh.event_ids(await get_marathon(bot.db, GUILD, marathon["id"])) == {}


async def test_host_events_off_calls_the_event_off_and_removal_does_too(
    bot,
    cog,
    proposals,  # noqa: F811
):
    marathon = await hidden_heroes(bot)
    await scan_on(bot, marathon)
    await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.EVENTS, True)
    event_id = mh.event_ids(await get_marathon(bot.db, GUILD, marathon["id"]))[ANARCHY]
    await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.EVENTS, False)
    assert (await get_event(bot.db, event_id))["status"] == "cancelled"
    assert (await details_of(bot.db, "marathon.host_event_cancelled"))["reason"] == "switched_off"

    await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.EVENTS, True)
    again = mh.event_ids(await get_marathon(bot.db, GUILD, marathon["id"]))[ANARCHY]
    assert again != event_id
    removed = await remove_marathon(
        bot, bot.guild, FakeActor(), await get_marathon(bot.db, GUILD, marathon["id"])
    )
    assert removed.ok
    assert (await get_event(bot.db, again))["status"] == "cancelled"


async def test_runner_events_are_unchanged_and_a_host_only_run_gets_none(
    bot,
    cog,
    proposals,  # noqa: F811
):
    await bot.store.set(GUILD, "marathon_hosts_count_as_ours", True)
    marathon = await hidden_heroes(bot)
    await scan_on(bot, marathon)
    await set_event_mode(bot, bot.guild, FakeActor(), marathon, "runs")
    rows = {row["game"]: row for row in await runs_of(bot.db, marathon["id"])}
    assert rows["Metroid Fusion"]["event_id"]
    title = (await get_event(bot.db, rows["Metroid Fusion"]["event_id"]))["title"]
    assert title.startswith("Sky") and "Metroid Fusion" in title
    assert rows["Mega Man X"]["event_id"] is None and rows["Shovel Knight"]["event_id"] is None
    assert mt.is_ours(rows["Mega Man X"])


async def test_two_switch_presses_at_once_leave_one_event_under_the_marathon_lock(
    bot,
    cog,
    proposals,  # noqa: F811
):
    marathon = await hidden_heroes(bot)
    await scan_on(bot, marathon)

    async def the_tick():
        async with cog.lock(marathon["id"]):
            await hosts.sync_host_events(bot, bot.guild, marathon)

    await asyncio.gather(
        hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.EVENTS, True),
        hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.EVENTS, True),
        the_tick(),
    )
    assert (await kinds(bot.db)).count("marathon.host_event_made") == 1
    assert len(mh.event_ids(await get_marathon(bot.db, GUILD, marathon["id"]))) == 1


SHOW_ROOM = 557
HOSTED_ONLY = [
    a_run(
        1,
        30,
        game="Titanfall 2",
        people=(("Pilot", "pilotruns", "runner"), ("anarchy", "anarchyasf", "host")),
    ),
    a_run(
        2,
        90,
        game="VHOLUME",
        people=(("Vee", "veeruns", "runner"), ("anarchy", "anarchyasf", "host")),
    ),
    a_run(
        3,
        150,
        game="SPRAWL zero",
        people=(("Spry", "spryruns", "runner"), ("anarchy", "anarchyasf", "host")),
    ),
]
HOSTED_GAMES = ("Titanfall 2", "VHOLUME", "SPRAWL zero")
SKY_SLOT = a_run(4, 210, game="Super Metroid", people=(("Sky", "skyruns", "runner"),))


async def hosted_show(bot, cog, runs, *, count):  # noqa: F811
    await bot.store.set(GUILD, "marathon_hosts_count_as_ours", count)
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
    await scan_on(bot, marathon)
    cog.clock = lambda: NOW + timedelta(minutes=15)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    return await get_marathon(bot.db, GUILD, marathon["id"])


def said_about(bot, game):  # noqa: F811
    places = [bot.guild.channels[SHOW_ROOM].threads[-1], bot.guild.channels[CHANNEL]]
    return [one for place in places for one in place.messages if f"**{game}**" in one.content]


async def test_a_scanned_host_is_shown_and_spotlit_but_makes_no_run_ours(bot, cog):  # noqa: F811
    marathon = await hosted_show(bot, cog, HOSTED_ONLY, count=False)
    anarchy = named((await board(bot, marathon))["baf"], "anarchy")
    assert anarchy["user_id"] == ANARCHY and anarchy["parts"] == [mt.HOST]
    rows = await runs_of(bot.db, marathon["id"])
    assert cogmod.counts_of(rows) == (3, 0)
    for row in rows:
        assert not mt.is_ours(row) and mt.member_ids(row) == []
        assert mt.SHOUT_MOVE not in mt.run_moves(row)
        assert not mp.postable(row)
    for game in HOSTED_GAMES:
        assert said_about(bot, game) == []
    assert "marathon.run_matched" not in await kinds(bot.db)
    assert "marathon.reminded" not in await kinds(bot.db)
    outcome = await people.spotlight_runner(bot, bot.guild, FakeActor(), marathon, "anarchy")
    assert outcome.ok, outcome.message
    assert (await channel_by_login(bot.db, GUILD, "anarchyasf"))["note"] == (
        "anarchy hosting Hidden Heroes"
    )


async def test_with_the_key_on_a_host_makes_the_run_ours_again(bot, cog):  # noqa: F811
    marathon = await hosted_show(bot, cog, HOSTED_ONLY, count=True)
    rows = await runs_of(bot.db, marathon["id"])
    assert cogmod.counts_of(rows) == (3, 3)
    assert all(mt.member_ids(row) == [ANARCHY] for row in rows)
    assert all(mp.postable(row) for row in rows)
    assert said_about(bot, "Titanfall 2")
    assert "marathon.reminded" in await kinds(bot.db)


async def test_turning_the_key_off_takes_the_runs_back_at_the_next_rematch(bot, cog):  # noqa: F811
    marathon = await hosted_show(bot, cog, HOSTED_ONLY, count=True)
    await bot.store.set(GUILD, "marathon_hosts_count_as_ours", False)
    await cog.rematch(bot.guild, marathon)
    rows = await runs_of(bot.db, marathon["id"])
    assert cogmod.counts_of(rows) == (3, 0)
    assert all(
        one["user_id"] == ANARCHY
        for row in rows
        for one in mt.people_of(row)
        if one["part"] == mt.HOST
    )


@pytest.mark.parametrize("count", [False, True])
async def test_a_baf_runners_run_is_the_same_either_way(bot, cog, count):  # noqa: F811
    marathon = await hosted_show(bot, cog, [*HOSTED_ONLY, SKY_SLOT], count=count)
    rows = {row["game"]: row for row in await runs_of(bot.db, marathon["id"])}
    assert mt.member_ids(rows["Super Metroid"]) == [SKY]
    assert mp.postable(rows["Super Metroid"])
    assert said_about(bot, "Super Metroid")
    assert cogmod.counts_of(list(rows.values())) == (4, 4 if count else 1)


@pytest.mark.parametrize("count", [False, True])
async def test_host_events_follow_their_switch_whatever_the_key(
    bot,
    cog,
    proposals,  # noqa: F811
    count,
):
    marathon = await hosted_show(bot, cog, HOSTED_ONLY, count=count)
    assert mh.event_ids(await get_marathon(bot.db, GUILD, marathon["id"])) == {}
    await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.EVENTS, True)
    ids = mh.event_ids(await get_marathon(bot.db, GUILD, marathon["id"]))
    assert list(ids) == [ANARCHY]
    event = await get_event(bot.db, ids[ANARCHY])
    assert event["starts_at"] == at(30) and event["ends_at"] == at(210)
