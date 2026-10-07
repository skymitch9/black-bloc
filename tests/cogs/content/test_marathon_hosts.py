# ruff: noqa: F811
import asyncio
import json
from datetime import timedelta

import pytest

from black_bloc import marathon as mt
from black_bloc import marathon_hosts as mh
from black_bloc import marathon_public as mp
from black_bloc import settings_store
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


def host_records(marathon):
    return mh.event_records(marathon)


async def events_on(bot, marathon, mode="runs"):  # noqa: F811
    outcome = await set_event_mode(bot, bot.guild, FakeActor(), marathon, mode)
    assert outcome.ok, outcome.message
    return outcome


async def test_hosts_are_found_with_no_switch_anywhere(bot, cog):  # noqa: F811
    assert "marathon_scan_hosts_default" not in settings_store.KEY_TYPES
    marathon = await hidden_heroes(bot)
    anarchy = named((await board(bot, marathon))["baf"], "anarchy")
    assert anarchy["user_id"] == ANARCHY and anarchy["parts"] == [mt.HOST]
    assert len(anarchy["runs"]) == 3
    await bot.db.conn.execute("UPDATE marathons SET scan_hosts = 0 WHERE id = ?", (marathon["id"],))
    await bot.db.conn.commit()
    await cog.rematch(bot.guild, marathon)
    assert named((await board(bot, marathon))["baf"], "anarchy") is not None


async def test_a_switch_word_that_is_not_one_is_refused_in_words(bot, cog):  # noqa: F811
    marathon = await hidden_heroes(bot)
    outcome = await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.ANNOUNCE, "maybe")
    assert not outcome.ok and outcome.message == (
        "Say on, off or follow for **BaF announcements**, so nothing was changed."
    )


async def test_spotlight_a_host_gets_the_host_note_and_their_hosted_span(
    bot,
    cog,  # noqa: F811
):
    marathon = await hidden_heroes(bot)
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
    outcome = await people.spotlight_runner(bot, bot.guild, FakeActor(), marathon, "skyruns")
    assert outcome.ok, outcome.message
    assert (await channel_by_login(bot.db, GUILD, "skyruns"))["note"] == "Sky at Hidden Heroes"


async def test_one_events_switch_makes_runner_events_per_run_and_host_events_per_block(
    bot,
    cog,
    proposals,  # noqa: F811
):
    marathon = await hidden_heroes(bot)
    assert "marathon.host_event_made" not in await kinds(bot.db)
    outcome = await events_on(bot, marathon)
    assert "BaF host block" in outcome.message
    fresh = await get_marathon(bot.db, GUILD, marathon["id"])
    (record,) = host_records(fresh)
    assert record["runs"] == [row["id"] for row in await runs_of(bot.db, marathon["id"])]
    assert record["hosts"] == [ANARCHY]
    event = await get_event(bot.db, record["event_id"])
    assert event["title"] == "anarchy hosts Hidden Heroes"
    assert event["description"] == (
        "anarchy hosts 3 run(s) on Hidden Heroes: Mega Man X, Metroid Fusion, Shovel Knight. "
        "Read from the schedule; times follow it."
    )
    assert event["starts_at"] == at(60) and event["ends_at"] == at(240)
    assert event["location"] == "https://twitch.tv/anarchyasf"
    made = await details_of(bot.db, "marathon.host_event_made")
    assert made["members"] == [ANARCHY] and len(made["runs"]) == 3
    rows = {row["game"]: row for row in await runs_of(bot.db, marathon["id"])}
    assert rows["Metroid Fusion"]["event_id"]
    assert rows["Mega Man X"]["event_id"] is None and rows["Shovel Knight"]["event_id"] is None

    await hosts.sync_host_events(bot, bot.guild, fresh)
    assert (await kinds(bot.db)).count("marathon.host_event_made") == 1


async def test_a_host_with_two_blocks_gets_an_event_for_each(bot, cog, proposals):  # noqa: F811
    cog.client.runs_given = [
        *HIDDEN_HEROES,
        a_run(4, 240, game="Celeste", people=(("Mo", "mohosts", "host"),)),
        a_run(5, 300, game="Hades", people=(("anarchy", "anarchyasf", "host"),)),
    ]
    marathon = await hidden_heroes(bot)
    await events_on(bot, marathon)
    found = host_records(await get_marathon(bot.db, GUILD, marathon["id"]))
    assert [len(one["runs"]) for one in found] == [3, 1]
    assert len({one["event_id"] for one in found}) == 2


async def test_gdqueers_shape_a_stored_host_events_on_with_runner_events_off_makes_nothing(
    bot,
    cog,
    proposals,  # noqa: F811
):
    marathon = await hidden_heroes(bot)
    await bot.db.conn.execute(
        "UPDATE marathons SET host_events = 1, event_mode = 'none' WHERE id = ?",
        (marathon["id"],),
    )
    await bot.db.conn.commit()
    fresh = await get_marathon(bot.db, GUILD, marathon["id"])
    assert await hosts.sync_host_events(bot, bot.guild, fresh) == {
        "made": 0,
        "redated": 0,
        "cancelled": 0,
        "failed": 0,
    }
    assert host_records(await get_marathon(bot.db, GUILD, marathon["id"])) == []
    assert all(not row["event_id"] for row in await runs_of(bot.db, marathon["id"]))
    await events_on(bot, fresh)
    assert len(host_records(await get_marathon(bot.db, GUILD, marathon["id"]))) == 1


async def test_a_per_host_event_from_v190_is_kept_and_claimed_by_the_first_block(
    bot,
    cog,
    proposals,  # noqa: F811
):
    marathon = await hidden_heroes(bot)
    await events_on(bot, marathon)
    (record,) = host_records(await get_marathon(bot.db, GUILD, marathon["id"]))
    legacy = json.dumps({str(ANARCHY): record["event_id"]})
    await bot.db.conn.execute(
        "UPDATE marathons SET host_event_ids = ? WHERE id = ?", (legacy, marathon["id"])
    )
    await bot.db.conn.commit()
    await hosts.sync_host_events(bot, bot.guild, marathon)
    (again,) = host_records(await get_marathon(bot.db, GUILD, marathon["id"]))
    assert again["event_id"] == record["event_id"] and len(again["runs"]) == 3
    assert (await kinds(bot.db)).count("marathon.host_event_made") == 1


async def test_events_off_calls_the_host_event_off_and_removal_does_too(
    bot,
    cog,
    proposals,  # noqa: F811
):
    marathon = await hidden_heroes(bot)
    await events_on(bot, marathon)
    (record,) = host_records(await get_marathon(bot.db, GUILD, marathon["id"]))
    await events_on(bot, marathon, "none")
    assert (await get_event(bot.db, record["event_id"]))["status"] == "cancelled"
    assert (await details_of(bot.db, "marathon.host_event_cancelled"))["reason"] == "switched_off"
    assert host_records(await get_marathon(bot.db, GUILD, marathon["id"])) == []

    await events_on(bot, marathon)
    (again,) = host_records(await get_marathon(bot.db, GUILD, marathon["id"]))
    assert again["event_id"] != record["event_id"]
    removed = await remove_marathon(
        bot, bot.guild, FakeActor(), await get_marathon(bot.db, GUILD, marathon["id"])
    )
    assert removed.ok
    assert (await get_event(bot.db, again["event_id"]))["status"] == "cancelled"


async def test_a_host_only_run_gets_no_run_event_of_its_own(
    bot,
    cog,
    proposals,  # noqa: F811
):
    await bot.store.set(GUILD, "marathon_hosts_count_as_ours", True)
    marathon = await hidden_heroes(bot)
    await events_on(bot, marathon)
    rows = {row["game"]: row for row in await runs_of(bot.db, marathon["id"])}
    assert rows["Metroid Fusion"]["event_id"]
    title = (await get_event(bot.db, rows["Metroid Fusion"]["event_id"]))["title"]
    assert title.startswith("Sky") and "Metroid Fusion" in title
    assert rows["Mega Man X"]["event_id"] is None and rows["Shovel Knight"]["event_id"] is None
    assert mt.is_ours(rows["Mega Man X"])


async def test_two_presses_at_once_leave_one_host_event_under_the_marathon_lock(
    bot,
    cog,
    proposals,  # noqa: F811
):
    marathon = await hidden_heroes(bot)

    async def the_tick():
        async with cog.lock(marathon["id"]):
            await hosts.sync_host_events(bot, bot.guild, marathon, actor=FakeActor())

    await asyncio.gather(
        set_event_mode(bot, bot.guild, FakeActor(), marathon, "runs"),
        set_event_mode(bot, bot.guild, FakeActor(), marathon, "runs"),
        the_tick(),
    )
    assert (await kinds(bot.db)).count("marathon.host_event_made") == 1
    assert len(host_records(await get_marathon(bot.db, GUILD, marathon["id"]))) == 1


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
HOST_POSTS = (f"<@{ANARCHY}> hosts **", "**anarchy** hosts **")
HOSTED_GAMES = ("Titanfall 2", "VHOLUME", "SPRAWL zero")
SKY_SLOT = a_run(4, 210, game="Super Metroid", people=(("Sky", "skyruns", "runner"),))


async def hosted_show(bot, cog, runs, *, count):  # noqa: F811
    await bot.store.set(GUILD, "marathon_hosts_count_as_ours", count)
    await bot.store.set(GUILD, "marathon_host_announcements_default", True)
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
    cog.clock = lambda: NOW + timedelta(minutes=15)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    return await get_marathon(bot.db, GUILD, marathon["id"])


def said_about(bot, game):  # noqa: F811
    places = [bot.guild.channels[SHOW_ROOM].threads[-1], bot.guild.channels[CHANNEL]]
    return [
        one
        for place in places
        for one in place.messages
        if f"**{game}**" in one.content and not one.content.startswith(HOST_POSTS)
    ]


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
    assert "marathon.public_reminded" in await kinds(bot.db)


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
async def test_host_events_follow_the_one_events_switch_whatever_the_key(
    bot,
    cog,
    proposals,  # noqa: F811
    count,
):
    marathon = await hosted_show(bot, cog, HOSTED_ONLY, count=count)
    assert host_records(await get_marathon(bot.db, GUILD, marathon["id"])) == []
    await events_on(bot, marathon)
    (record,) = host_records(await get_marathon(bot.db, GUILD, marathon["id"]))
    assert record["hosts"] == [ANARCHY]
    event = await get_event(bot.db, record["event_id"])
    assert event["starts_at"] == at(30) and event["ends_at"] == at(210)
