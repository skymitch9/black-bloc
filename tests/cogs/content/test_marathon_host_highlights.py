# ruff: noqa: F401, F811
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from black_bloc import marathon as mt
from black_bloc import marathon_host_highlights as mhh
from black_bloc import marathon_hosts as mh
from black_bloc.cogs.content import marathon as cogmod
from black_bloc.cogs.content import marathon_announce as announce
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
    FakeRole,
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
DAY = 1500
HIDDEN_HEROES_TOMORROW = [
    a_run(1, DAY, game="Titanfall 2", people=(("clipboard", "cb", "runner"), HOST), length=85),
    a_run(2, DAY + 85, game="VHOLUME", people=(("sorbet", "ts", "runner"), HOST), length=35),
    a_run(
        3, DAY + 120, game="SPRAWL zero", people=(("sylllphie", "sy", "runner"), HOST), length=50
    ),
]
LIVE_MARKS = "1440, 120, 15"
HOSTED = "**anarchy** hosted **Titanfall 2** — Any% today on **Hidden Heroes** · "


async def show(bot, cog, runs, *, clock=0, auto=False):
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


async def marks_logged(bot):
    cur = await bot.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = 'marathon.host_reminded' ORDER BY id"
    )
    return [json.loads(row["details"])["mark"] for row in await cur.fetchall()]


async def opt(bot, marathon, out):
    said = await announce.set_opt_out(bot, bot.guild, FakeActor(), marathon, [ANARCHY], out)
    assert said.ok, said.message
    return said


async def test_hidden_heroes_gets_one_post_per_mark_for_its_block_and_none_per_run(bot, cog):
    await bot.store.set(GUILD, "marathon_reminder_minutes", LIVE_MARKS)
    marathon = await show(bot, cog, HIDDEN_HEROES_TOMORROW)
    await walk(bot, cog, marathon, [30, 59])
    assert heads_ups(bot) == []
    await tick_at(bot, cog, marathon, 60)
    (first,) = heads_ups(bot)
    assert first.content.startswith("<@8101> hosts **Titanfall 2** (Any%) on **Hidden Heroes** <t:")
    assert no_pings(first) and "<@&" not in first.content
    await walk(bot, cog, marathon, [61, 700, 1379])
    assert len(heads_ups(bot)) == 1
    await walk(bot, cog, marathon, [1380, 1484, 1485])
    await walk(bot, cog, marathon, [DAY + 1, DAY + 70, DAY + 85, DAY + 105, DAY + 120, DAY + 200])
    said = heads_ups(bot)
    assert [game_of(one) for one in said] == ["Titanfall 2"] * 3
    assert all(no_pings(one) and "<@&" not in one.content for one in said)
    assert await marks_logged(bot) == [1440, 120, 15]
    assert (await details_of(bot.db, "marathon.host_reminded"))["runs"] == [1, 2, 3]
    assert highlights(bot) == []
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


async def test_no_highlight_while_auto_highlight_is_off(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES)
    await walk(bot, cog, marathon, [45, 61, 146, 181, 231])
    assert highlights(bot) == []
    assert len(heads_ups(bot)) == 1


async def test_auto_highlight_posts_once_at_the_blocks_live_and_edits_it_to_done(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES, auto=True)
    await walk(bot, cog, marathon, [45, 59])
    assert highlights(bot) == []
    await tick_at(bot, cog, marathon, 61)
    (post,) = highlights(bot)
    assert post.content.startswith("**anarchy** hosts **Titanfall 2**")
    assert " · on now · " in post.content and no_pings(post)
    await walk(bot, cog, marathon, [130, 146, 165, 181])
    assert highlights(bot) == [post] and " · on now · " in post.content
    await walk(bot, cog, marathon, [231, 400])
    assert highlights(bot) == [] and post.content.startswith(HOSTED)
    assert " · done · " not in post.content and "<@&" not in post.content
    assert all(edit["allowed_mentions"].roles is False for edit in post.edits)
    assert (await kinds(bot.db)).count("marathon.host_highlight_posted") == 1
    assert len(heads_ups(bot)) == 1
    assert cogmod.counts_of(await runs_of(bot.db, marathon["id"])) == (3, 0)


async def test_staff_marking_a_later_run_live_highlights_the_block_under_auto(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES, auto=True)
    run = await run_named(bot, marathon, "VHOLUME")
    said = await cogmod.mark_live(bot, bot.guild, FakeActor(), marathon, run)
    assert said.ok, said.message
    (post,) = highlights(bot)
    assert game_of(post) == "Titanfall 2"
    await tick_at(bot, cog, marathon, 61)
    assert len(highlights(bot)) == 1


async def test_a_restart_posts_neither_the_highlight_nor_the_heads_up_again(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES, auto=True)
    await walk(bot, cog, marathon, [45, 61])
    restarted = type(cog)(bot)
    restarted.client = cog.client
    restarted.clock = cog.clock
    bot.cogs[cogmod.COG_NAME] = restarted

    await restarted.tick_once()
    await walk(bot, restarted, marathon, [62, 70, 146])
    assert len(heads_ups(bot)) == 1 and len(highlights(bot)) == 1
    assert highlights(bot)[0].edits == []


async def test_the_key_off_posts_nothing(bot, cog):
    await bot.store.set(GUILD, "marathon_host_highlights", False)
    marathon = await show(bot, cog, HIDDEN_HEROES, auto=True)
    await walk(bot, cog, marathon, [45, 61, 130, 146, 165, 181, 231])
    assert heads_ups(bot) == [] and highlights(bot) == []
    assert "marathon.host_highlight_posted" not in await kinds(bot.db)


async def test_the_heads_up_waits_for_public_reminders(bot, cog):
    await bot.store.set(GUILD, "marathon_public_reminders", False)
    marathon = await show(bot, cog, HIDDEN_HEROES)
    await walk(bot, cog, marathon, [45, 130, 165])
    assert heads_ups(bot) == []
    skipped = await details_of(bot.db, "marathon.host_reminder_skipped")
    assert skipped["because"] == "public_reminders_off"


async def test_the_announcements_switch_off_posts_nothing_for_the_host(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES, auto=True)
    said = await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.ANNOUNCE, False)
    assert said.ok and "announces nobody" in said.message
    await walk(bot, cog, marathon, [45, 61, 146, 181, 231])
    assert heads_ups(bot) == [] and highlights(bot) == []
    assert (await details_of(bot.db, "marathon.host_reminder_skipped"))[
        "because"
    ] == "announcements_off"
    assert "marathon.announcements_set" in await kinds(bot.db)


async def test_an_opted_out_host_gets_nothing_and_opting_back_in_resumes_at_the_next_mark(
    bot, cog
):
    await bot.store.set(GUILD, "marathon_reminder_minutes", LIVE_MARKS)
    marathon = await show(bot, cog, HIDDEN_HEROES_TOMORROW, auto=True)
    said = await opt(bot, marathon, True)
    assert "is opted out of **Hidden Heroes**" in said.message
    await walk(bot, cog, marathon, [60, 700, 1380])
    assert heads_ups(bot) == []
    assert (await details_of(bot.db, "marathon.host_reminder_skipped"))["because"] == "opted_out"
    said = await opt(bot, marathon, False)
    assert "is back in" in said.message
    await walk(bot, cog, marathon, [1400, 1484])
    assert heads_ups(bot) == []
    await walk(bot, cog, marathon, [1485, DAY + 1])
    (back,) = heads_ups(bot)
    assert await marks_logged(bot) == [15]
    assert len(highlights(bot)) == 1


async def test_an_opted_out_host_is_never_auto_highlighted(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES, auto=True)
    await opt(bot, marathon, True)
    await walk(bot, cog, marathon, [45, 61, 146, 231])
    assert heads_ups(bot) == [] and highlights(bot) == []


async def test_opting_out_takes_the_highlight_down_and_opting_in_puts_it_back_in_place(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES, auto=True)
    await tick_at(bot, cog, marathon, 61)
    (post,) = highlights(bot)
    await opt(bot, marathon, True)
    assert post.content == "Staff took down the highlight for **anarchy** on **Hidden Heroes**."
    assert (await details_of(bot.db, "marathon.host_highlight_removed"))["edited"] is True
    await tick_at(bot, cog, marathon, 70)
    assert post.content.startswith("Staff took down")
    await opt(bot, marathon, False)
    assert post.content.startswith("**anarchy** hosts **Titanfall 2**")
    assert highlights(bot) == [post]
    assert "marathon.host_highlight_restored" in await kinds(bot.db)
    await walk(bot, cog, marathon, [146, 231, 400])
    assert post.content.startswith(HOSTED) and highlights(bot) == []


async def test_a_heads_up_too_late_is_skipped_not_posted(bot, cog):
    await bot.store.set(GUILD, "marathon_reminder_stale_minutes", 5)
    marathon = await show(bot, cog, HIDDEN_HEROES, clock=20)
    await walk(bot, cog, marathon, [52, 55])
    assert heads_ups(bot) == []
    skipped = await details_of(bot.db, "marathon.host_reminder_skipped")
    assert skipped["because"] == "late" and skipped["game"] == "Titanfall 2"
    assert (await kinds(bot.db)).count("marathon.host_reminder_skipped") == 2


async def test_a_per_run_record_left_by_the_last_build_is_not_heads_upped_twice(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES, clock=-200)
    first = await run_named(bot, marathon, "Titanfall 2")
    old = {
        "run_id": first["id"],
        "hosts": [{"user_id": ANARCHY, "name": "anarchy", "login": None, "part": "host"}],
        "message_id": None,
        "channel_id": None,
        "removed": False,
        "tried": False,
        "reminded": True,
    }
    await update_marathon(bot.db, marathon["id"], host_highlight_posts=json.dumps([old]))
    await walk(bot, cog, marathon, [50, 146, 181])
    assert heads_ups(bot) == []
    (record,) = mhh.records(await get_marathon(bot.db, GUILD, marathon["id"]))
    assert record["start_run_id"] == first["id"] and record["marks"] == [15, 120]
    assert "legacy_reminded" not in record


async def test_a_baf_runners_run_is_unchanged_beside_the_hosted_block(bot, cog):
    marathon = await show(bot, cog, [*HOSTED_ONLY, SKY_SLOT])
    rows = {row["game"]: row for row in await runs_of(bot.db, marathon["id"])}
    assert mt.member_ids(rows["Super Metroid"]) == [SKY]
    assert said_about(bot, "Super Metroid")
    assert cogmod.counts_of(list(rows.values())) == (4, 1)
    await tick_at(bot, cog, marathon, 15)
    (heads,) = heads_ups(bot)
    assert game_of(heads) == "Titanfall 2"
    await walk(bot, cog, marathon, [75, 135, 195])
    assert len(heads_ups(bot)) == 1
    assert not any(one.content.startswith(f"<@{SKY}> hosts") for one in posts(bot))
    assert any(one.content.startswith(f"<@{SKY}> runs **Super Metroid**") for one in posts(bot))


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


async def test_the_sgdq_tracker_posts_one_set_for_thekingsprides_block(bot, cog):
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

    async def at(when):
        cog.clock = lambda: when
        async with cog.lock(marathon["id"]):
            await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))

    for hour, minute in ((19, 50), (19, 58), (21, 0), (21, 43), (22, 30), (23, 6), (23, 30)):
        await at(datetime(2026, 7, 5, hour, minute, tzinfo=UTC))
    await at(datetime(2026, 7, 6, 1, 5, tzinfo=UTC))
    said = heads_ups(bot, member=KINGS)
    assert [game_of(one) for one in said] == ["I Am Your Beast", "I Am Your Beast"]
    assert all("Devil May Cry" not in one.content for one in said)
    assert all("The Checkpoint" not in one.content for one in posts(bot))
    assert highlights(bot, name="TheKingsPride") == []
    assert cogmod.counts_of(await runs_of(bot.db, marathon["id"]))[1] == 0


@pytest.mark.parametrize("stop", ["key", "announcements"])
async def test_a_post_already_up_follows_its_block_to_the_end_after_a_switch_goes_off(
    bot, cog, stop
):
    marathon = await show(bot, cog, HIDDEN_HEROES, auto=True)
    await tick_at(bot, cog, marathon, 61)
    (post,) = highlights(bot)
    if stop == "key":
        await bot.store.set(GUILD, "marathon_host_highlights", False)
    else:
        await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.ANNOUNCE, False)
    await walk(bot, cog, marathon, [130, 146, 181, 231, 400])
    assert post.content.startswith(HOSTED)
    assert highlights(bot) == [] and heads_ups(bot) == []


async def test_a_host_post_already_up_from_the_last_build_is_edited_in_place(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES, clock=-200)
    first = await run_named(bot, marathon, "Titanfall 2")
    old_post = await bot.guild.channels[CHANNEL].send("**anarchy** hosts **Titanfall 2** · old")
    old = {
        "run_id": first["id"],
        "hosts": [{"user_id": ANARCHY, "name": "anarchy", "login": None, "part": "host"}],
        "message_id": old_post.id,
        "channel_id": CHANNEL,
        "removed": False,
        "tried": True,
        "reminded": False,
    }
    await update_marathon(bot.db, marathon["id"], host_highlight_posts=json.dumps([old]))
    count = len(posts(bot))
    await tick_at(bot, cog, marathon, 61)
    assert highlights(bot) == [old_post] and old_post.edits
    assert " · on now · " in old_post.content and len(posts(bot)) == count
    (record,) = mhh.records(await get_marathon(bot.db, GUILD, marathon["id"]))
    assert record["runs"] == [first["id"], first["id"] + 1, first["id"] + 2]


# --- the Marathon role on the block's ping-mark heads-up ------------------------------------------

MARATHON_ROLE = 6100


async def role_pinging(bot, marathon, *, switch=True):
    role = FakeRole(MARATHON_ROLE, "Marathon")
    role.mentionable = True
    bot.guild.roles.append(role)
    await bot.store.set(GUILD, "marathon_role_id", MARATHON_ROLE)
    await update_marathon(bot.db, marathon["id"], ping_role=1 if switch else 0)


def host_copies(bot, member=ANARCHY):
    return [one for one in posts(bot) if f"<@{member}> hosts **" in one.content]


async def host_rows(bot):
    cur = await bot.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = 'marathon.host_reminded' ORDER BY id"
    )
    return [json.loads(row["details"]) for row in await cur.fetchall()]


async def test_the_blocks_fifteen_minute_heads_up_mentions_the_marathon_role_once(bot, cog):
    await bot.store.set(GUILD, "marathon_reminder_minutes", LIVE_MARKS)
    marathon = await show(bot, cog, HIDDEN_HEROES_TOMORROW)
    await role_pinging(bot, marathon)
    await walk(bot, cog, marathon, [60, 1380, 1485, DAY + 1, DAY + 90, DAY + 125])

    said = host_copies(bot)
    assert len(said) == 3
    assert [f"<@&{MARATHON_ROLE}>" in one.content for one in said] == [False, False, True]
    last = said[-1]
    assert last.content.startswith(f"<@&{MARATHON_ROLE}> <@{ANARCHY}> hosts **Titanfall 2**")
    assert last.content.count("<@&") == 1
    mentions = last.kwargs["allowed_mentions"]
    assert [one.id for one in mentions.roles] == [MARATHON_ROLE]
    assert mentions.users is False and mentions.everyone is False
    assert all(no_pings(one) for one in said[:2])
    logged = await host_rows(bot)
    assert [one["mark"] for one in logged] == [1440, 120, 15]
    assert [one["roles"] for one in logged] == [[], [], [MARATHON_ROLE]]
    assert [one["pinged"] for one in logged] == [False, False, True]
    assert logged[-1]["marathon_role"] == MARATHON_ROLE
    assert logged[-1]["marathon_role_reason"] is None
    assert "marathon_role" not in logged[0]


async def test_the_block_heads_up_mentions_no_role_while_the_marathons_switch_is_off(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES)
    await role_pinging(bot, marathon, switch=False)
    await tick_at(bot, cog, marathon, 45)

    (said,) = heads_ups(bot)
    assert no_pings(said) and "<@&" not in said.content
    (logged,) = await host_rows(bot)
    assert (logged["pinged"], logged["roles"]) == (False, [])
    assert (logged["marathon_role"], logged["marathon_role_reason"]) == (None, "switch_off")


async def test_the_block_heads_up_posts_without_a_role_that_is_gone_and_logs_why(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES)
    await role_pinging(bot, marathon)
    bot.guild.roles.clear()
    await tick_at(bot, cog, marathon, 45)

    (said,) = heads_ups(bot)
    assert no_pings(said)
    (logged,) = await host_rows(bot)
    assert (logged["marathon_role"], logged["marathon_role_reason"]) == (None, "gone")


async def test_a_block_that_opens_on_a_baf_run_leaves_the_mention_to_the_runners_copy(bot, cog):
    opening = a_run(
        1, 60, game="Titanfall 2", people=(("Sky", "skyruns", "runner"), HOST), length=85
    )
    marathon = await show(bot, cog, [opening, *HIDDEN_HEROES[1:]])
    await role_pinging(bot, marathon)
    await tick_at(bot, cog, marathon, 45)

    carrying = [one for one in posts(bot) if f"<@&{MARATHON_ROLE}>" in one.content]
    assert len(carrying) == 1 and f"<@{SKY}> runs **Titanfall 2**" in carrying[0].content
    (hosted,) = heads_ups(bot)
    assert no_pings(hosted)
    (logged,) = await host_rows(bot)
    assert (logged["marathon_role"], logged["marathon_role_reason"]) == (None, "runner_copy")
    assert (await details_of(bot.db, "marathon.public_reminded"))["marathon_role"] == MARATHON_ROLE
