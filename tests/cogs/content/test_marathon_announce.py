# ruff: noqa: F401, F811
import json
import re
from datetime import timedelta
from types import SimpleNamespace

import discord
import pytest

from black_bloc import marathon as mt
from black_bloc import marathon_announce as ma
from black_bloc import marathon_hosts as mh
from black_bloc.cogs.content import marathon as cogmod
from black_bloc.cogs.content import marathon_announce as announce
from black_bloc.cogs.content import marathon_hosts as hosts
from black_bloc.cogs.content import marathon_public as public
from black_bloc.cogs.content.marathon import pair_runner
from tests.cogs.content.test_marathon import NOW, SKY, Member, a_run, bot, cog
from tests.cogs.content.test_marathon_host_highlights import (
    ANARCHY,
    HIDDEN_HEROES,
    game_of,
    heads_ups,
    highlights,
    no_pings,
    posts,
    run_named,
    show,
    tick_at,
    walk,
)
from tests.cogs.content.test_marathon_hosts import SHOW_ROOM
from tests.cogs.content.test_marathon_public import current_view
from tests.cogs.content.test_marathon_runner_posts import fresh
from tests.cogs.content.test_spotlight import (
    GUILD,
    FakeActor,
    FakeInteraction,
    details_of,
    kinds,
)


async def test_the_people_a_marathon_can_announce_are_its_baf_runners_and_hosts(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES)
    assert await announce.baf_people(bot, bot.guild, marathon) == {ANARCHY: "anarchy"}


async def test_the_writer_refuses_in_words_and_writes_once(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES)
    bad = await announce.set_opt_out(bot, bot.guild, FakeActor(), marathon, [ANARCHY], "maybe")
    assert not bad.ok and bad.status == 422 and bad.code == ma.BAD_OPT_CODE
    stranger = await announce.set_opt_out(bot, bot.guild, FakeActor(), marathon, [SKY], True)
    assert not stranger.ok and stranger.status == 404 and "Hidden Heroes" in stranger.message

    for _ in range(2):
        said = await announce.set_opt_out(bot, bot.guild, FakeActor(), marathon, [ANARCHY], "out")
        assert said.ok and "**anarchy** is opted out of **Hidden Heroes**" in said.message
    assert ma.opted_out(await fresh(bot, marathon)) == {ANARCHY}
    assert (await kinds(bot.db)).count("marathon.announce_opted_out") == 1

    said = await announce.set_opt_out(bot, bot.guild, FakeActor(), marathon, [ANARCHY], "in")
    assert said.ok and ma.opted_out(await fresh(bot, marathon)) == set()
    assert "marathon.announce_opted_in" in await kinds(bot.db)


async def test_the_switch_follows_the_default_key(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES)
    assert announce.announces(bot, GUILD, marathon)
    await bot.store.set(GUILD, "marathon_announcements_default", False)
    assert not announce.announces(bot, GUILD, marathon)


# --- announce overrides: hosts off by default, a run's own answer, the no-@ choice --------------

HOST = ("anarchy", "anarchyasf", "host")
SKY_RUNS = ("Sky", "skyruns", "runner")
MO = 8202
FOUR = [
    a_run(1, 60, game="Alpha", people=(SKY_RUNS, HOST), length=85),
    a_run(2, 145, game="Beta", people=(SKY_RUNS, HOST), length=35),
    a_run(3, 180, game="Gamma", people=(("sorbet", "ts", "runner"), HOST), length=50),
    a_run(4, 230, game="Delta", people=(("sy", "sy", "runner"), HOST), length=30),
]
PAIR = [a_run(1, 60, game="Alpha", people=(SKY_RUNS, ("Mo", "moruns", "runner")), length=85)]
FANCY = "Sky_*Aiva*"
ESCAPED = "Sky\\_\\*Aiva\\*"
WRITTEN = "Sky"
WITH_MENTION = "{mention} {part} **{game}** on **{marathon}** · {state} · {url}"
DONE_WITH_MENTION = "{mention} {part} **{game}** {day} on **{marathon}** · {url}"


async def answer(bot, marathon, game, user_id, to, actor=None):
    row = await run_named(bot, marathon, game)
    return await announce.set_run_answer(
        bot, bot.guild, actor or FakeActor(), await fresh(bot, marathon), row["id"], user_id, to
    )


async def mention(bot, marathon, user_id, to):
    return await announce.set_mention(
        bot, bot.guild, FakeActor(), await fresh(bot, marathon), user_id, to
    )


def said_of(bot, start):
    return [one for one in posts(bot) if one.content.startswith(start)]


def runner_heads_ups(bot, game, member=SKY):
    return said_of(bot, f"<@{member}> runs **{game}**")


def runner_highlights(bot, game):
    return said_of(bot, f"**Sky** runs **{game}**") + said_of(bot, f"**Sky** ran **{game}**")


def fancy_names(bot):
    bot.guild.get_member = lambda user_id: SimpleNamespace(id=user_id, display_name=FANCY)


async def skipped_because(bot):
    cur = await bot.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = 'marathon.host_reminder_skipped' ORDER BY id"
    )
    return [json.loads(row["details"])["because"] for row in await cur.fetchall()]


async def test_a_host_following_the_defaults_gets_no_public_post_and_the_runner_still_does(
    bot, cog
):
    marathon = await show(bot, cog, FOUR, auto=True, hosts=False)
    assert not announce.policy_of(bot, GUILD, marathon).hosts_on

    await walk(bot, cog, marathon, [45, 61])

    assert heads_ups(bot) == [] and highlights(bot) == []
    assert len(runner_heads_ups(bot, "Alpha")) == 1 and len(runner_highlights(bot, "Alpha")) == 1
    assert "host_announcements_off" in await skipped_because(bot)
    assert "marathon.host_reminded" not in await kinds(bot.db)
    assert await announce.baf_people(bot, bot.guild, marathon) == {SKY: "Sky", ANARCHY: "anarchy"}


async def test_host_announcements_on_for_the_marathon_brings_the_hosts_posts_back(bot, cog):
    marathon = await show(bot, cog, FOUR, auto=True, hosts=False)

    said = await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.HOST_ANNOUNCE, True)
    await walk(bot, cog, marathon, [45, 61])

    assert said.ok and "announces its BaF hosts publicly now" in said.message
    assert [game_of(one) for one in heads_ups(bot)] == ["Alpha"]
    assert [game_of(one) for one in highlights(bot)] == ["Alpha"]
    assert len(runner_heads_ups(bot, "Alpha")) == 1
    logged = await details_of(bot.db, "marathon.host_announcements_set")
    assert (logged["from"], logged["to"], logged["on"], logged["via"]) == (
        None,
        True,
        True,
        "discord",
    )
    back = await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.HOST_ANNOUNCE, None)
    assert back.ok and (await fresh(bot, marathon))["host_announcements"] is None
    bad = await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.HOST_ANNOUNCE, "eh")
    assert not bad.ok and "Host announcements" in bad.message


async def test_both_switches_off_is_everyone_off_by_default(bot, cog):
    marathon = await show(bot, cog, FOUR, auto=True, hosts=False)
    await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.ANNOUNCE, False)

    await walk(bot, cog, marathon, [45, 61])

    assert heads_ups(bot) == [] and highlights(bot) == []
    assert runner_heads_ups(bot, "Alpha") == [] and runner_highlights(bot, "Alpha") == []
    assert "host_announcements_off" in await skipped_because(bot)


async def test_a_runs_own_yes_beats_both_switches_off(bot, cog):
    marathon = await show(bot, cog, FOUR, auto=True, hosts=False)
    assert (await answer(bot, marathon, "Alpha", ANARCHY, "in")).ok
    assert (await answer(bot, marathon, "Alpha", SKY, "in")).ok
    await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.ANNOUNCE, False)

    await walk(bot, cog, marathon, [45, 61])

    assert [game_of(one) for one in heads_ups(bot)] == ["Alpha"] and len(highlights(bot)) == 1
    assert len(runner_heads_ups(bot, "Alpha")) == 1 and len(runner_highlights(bot, "Alpha")) == 1


async def test_runner_announcements_off_still_announces_hosts(bot, cog):
    marathon = await show(bot, cog, FOUR, auto=True, hosts=True)
    await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.ANNOUNCE, False)

    await walk(bot, cog, marathon, [45, 61])

    assert [game_of(one) for one in heads_ups(bot)] == ["Alpha"] and len(highlights(bot)) == 1
    assert runner_heads_ups(bot, "Alpha") == [] and runner_highlights(bot, "Alpha") == []


async def test_a_host_announced_for_one_run_of_a_four_run_block_gets_the_block_once(bot, cog):
    marathon = await show(bot, cog, FOUR, auto=True, hosts=False)

    said = await answer(bot, marathon, "Gamma", ANARCHY, "in")
    await walk(bot, cog, marathon, [45, 61, 130, 146, 165, 181, 215, 231])

    assert said.ok and "**anarchy** is announced for **Gamma**" in said.message
    assert [game_of(one) for one in heads_ups(bot)] == ["Alpha"]
    assert len(highlights(bot)) == 1
    logged = await details_of(bot.db, "marathon.announce_run_set")
    assert (logged["member"], logged["from"], logged["to"], logged["via"]) == (
        ANARCHY,
        "default",
        "in",
        "discord",
    )


async def test_a_host_left_out_of_every_run_of_their_block_is_silent(bot, cog):
    marathon = await show(bot, cog, FOUR, auto=True)
    for game in ("Alpha", "Beta", "Gamma", "Delta"):
        assert (await answer(bot, marathon, game, ANARCHY, "out")).ok

    await walk(bot, cog, marathon, [45, 61])

    assert heads_ups(bot) == [] and highlights(bot) == []
    assert "opted_out" in await skipped_because(bot)
    assert (await answer(bot, marathon, "Delta", ANARCHY, "default")).ok
    await walk(bot, cog, marathon, [146])
    assert [game_of(one) for one in highlights(bot)] == ["Alpha"] and heads_ups(bot) == []


async def test_a_runner_left_out_of_one_run_keeps_their_other_runs(bot, cog):
    marathon = await show(bot, cog, FOUR, auto=True, hosts=False)

    said = await answer(bot, marathon, "Alpha", SKY, "out")
    await walk(bot, cog, marathon, [45, 61, 130, 146])

    assert said.ok and "Their other runs are unchanged" in said.message
    assert runner_heads_ups(bot, "Alpha") == [] and runner_highlights(bot, "Alpha") == []
    assert len(runner_heads_ups(bot, "Beta")) == 2 and len(runner_highlights(bot, "Beta")) == 1
    assert ma.run_answers(await run_named(bot, marathon, "Beta")) == {}
    assert ma.opted_out(await fresh(bot, marathon)) == set()


async def test_two_people_on_one_run_each_follow_their_own_answer(bot, cog):
    marathon = await show(bot, cog, PAIR, auto=True, hosts=False)
    paired = await pair_runner(bot, bot.guild, FakeActor(), marathon, "Mo", MO, everywhere=True)
    assert paired.ok, paired.message
    assert (await answer(bot, marathon, "Alpha", MO, "out")).ok

    await walk(bot, cog, marathon, [45])

    (heads,) = runner_heads_ups(bot, "Alpha")
    assert f"<@{MO}>" not in heads.content
    assert (await answer(bot, marathon, "Alpha", MO, "default")).ok
    assert (await mention(bot, marathon, MO, "plain")).ok
    assert heads.content.startswith(f"<@{SKY}>, Mo run")
    assert len(said_of(bot, f"<@{SKY}>")) == 1
    await walk(bot, cog, marathon, [61])
    (post,) = said_of(bot, "**Sky, Mo** run")
    assert (await answer(bot, marathon, "Alpha", SKY, "out")).ok
    assert post.content.startswith("**Mo** runs **Alpha**") and len(said_of(bot, "**")) == 1


async def test_a_runs_own_yes_gets_past_the_marathon_wide_opt_out(bot, cog):
    marathon = await show(bot, cog, FOUR, hosts=False)
    out = await announce.set_opt_out(bot, bot.guild, FakeActor(), marathon, [SKY], True)
    assert out.ok and (await answer(bot, marathon, "Beta", SKY, "in")).ok

    await walk(bot, cog, marathon, [45, 130])

    assert runner_heads_ups(bot, "Alpha") == [] and len(runner_heads_ups(bot, "Beta")) == 2


async def test_the_run_answer_refuses_in_words_and_writes_once(bot, cog):
    marathon = await show(bot, cog, FOUR, hosts=False)

    bad = await answer(bot, marathon, "Alpha", SKY, "maybe")
    assert not bad.ok and (bad.status, bad.code) == (422, ma.BAD_RUN_CODE)
    stranger = await answer(bot, marathon, "Gamma", SKY, "out")
    assert not stranger.ok and stranger.status == 404 and "**Gamma**" in stranger.message
    gone = await announce.set_run_answer(bot, bot.guild, FakeActor(), marathon, 999, SKY, "out")
    assert not gone.ok and gone.status == 404
    for _ in range(2):
        assert (await answer(bot, marathon, "Alpha", SKY, "out")).ok
    assert (await kinds(bot.db)).count("marathon.announce_run_set") == 1
    assert ma.run_answers(await run_named(bot, marathon, "Alpha")) == {SKY: "out"}
    back = await answer(bot, marathon, "Alpha", SKY, "default")
    assert back.ok and "follows the defaults again" in back.message
    assert (await run_named(bot, marathon, "Alpha"))["announce_people"] is None


async def test_a_highlight_follows_a_runs_answer_in_place_and_is_never_posted_anew(bot, cog):
    marathon = await show(bot, cog, FOUR, auto=True, hosts=False)
    await walk(bot, cog, marathon, [45, 61])
    (post,) = runner_highlights(bot, "Alpha")
    count = len(posts(bot))

    assert (await answer(bot, marathon, "Alpha", SKY, "out")).ok
    assert post.content == "Staff took down the highlight for **Sky** on **Hidden Heroes**."
    await tick_at(bot, cog, marathon, 70)
    assert post.content.startswith("Staff took down")
    assert (await answer(bot, marathon, "Alpha", SKY, "default")).ok

    assert post.content.startswith("**Sky** runs **Alpha**") and len(posts(bot)) == count
    assert "marathon.public_highlight_restored" in await kinds(bot.db)
    assert len(runner_heads_ups(bot, "Alpha")) == 1


async def test_a_hosts_highlight_follows_a_runs_answer_in_place(bot, cog):
    marathon = await show(bot, cog, FOUR, auto=True, hosts=False)
    assert (await answer(bot, marathon, "Alpha", ANARCHY, "in")).ok
    await walk(bot, cog, marathon, [45, 61])
    (post,) = highlights(bot)
    count = len(posts(bot))

    assert (await answer(bot, marathon, "Alpha", ANARCHY, "default")).ok
    assert post.content == "Staff took down the highlight for **anarchy** on **Hidden Heroes**."
    assert (await answer(bot, marathon, "Beta", ANARCHY, "in")).ok

    assert post.content.startswith("**anarchy** hosts **Alpha**") and len(posts(bot)) == count
    assert len(heads_ups(bot)) == 1


async def test_a_taken_down_highlight_comes_back_on_a_runs_yes_while_runners_are_off(bot, cog):
    marathon = await show(bot, cog, FOUR, auto=True, hosts=False)
    await walk(bot, cog, marathon, [45, 61])
    (post,) = runner_highlights(bot, "Alpha")
    assert (await answer(bot, marathon, "Alpha", SKY, "out")).ok
    await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.ANNOUNCE, False)
    assert (await answer(bot, marathon, "Alpha", SKY, "default")).ok
    assert post.content.startswith("Staff took down")

    assert (await answer(bot, marathon, "Alpha", SKY, "in")).ok

    assert post.content.startswith("**Sky** runs **Alpha**")


async def test_host_announcements_going_off_carries_a_highlight_already_up_to_done(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES, auto=True)
    await walk(bot, cog, marathon, [45, 61])
    (post,) = highlights(bot)

    await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.HOST_ANNOUNCE, False)
    await walk(bot, cog, marathon, [130, 146, 181, 231, 400])

    assert post.content.startswith("**anarchy** hosted **Titanfall 2**")
    assert highlights(bot) == [] and len(heads_ups(bot)) == 1


# --- the no-@ choice ----------------------------------------------------------------------------


async def test_a_plain_name_is_written_on_the_reminder_and_survives_a_move(bot, cog):
    fancy_names(bot)
    marathon = await show(bot, cog, FOUR, hosts=False)
    said = await mention(bot, marathon, SKY, "plain")
    await walk(bot, cog, marathon, [45])

    (heads,) = said_of(bot, f"{WRITTEN} runs **Alpha**")
    assert said.ok and f"**{FANCY}** is written by name, with no @" in said.message
    assert f"<@{SKY}>" not in heads.content and no_pings(heads)
    assert json.loads((await fresh(bot, marathon))["mention_people"]) == {str(SKY): "plain"}
    logged = await details_of(bot.db, "marathon.mention_set")
    assert (logged["member"], logged["from"], logged["to"]) == (SKY, "mention", "plain")

    moved = [a_run(1, 75, game="Alpha", people=(SKY_RUNS, HOST), length=70), *FOUR[1:]]
    cog.client.runs_given = moved
    assert (await cog.refresh(bot.guild, await fresh(bot, marathon))).ok
    await tick_at(bot, cog, marathon, 46)

    assert heads.content.startswith(f"{WRITTEN} runs **Alpha**")
    assert mt.stamp_of(NOW + timedelta(minutes=75), "f") in heads.content
    assert (
        len(said_of(bot, f"{WRITTEN} runs **Alpha**")) == 1 and runner_heads_ups(bot, "Alpha") == []
    )


async def test_a_plain_name_is_written_on_the_highlight_and_on_the_finished_one(bot, cog):
    fancy_names(bot)
    await bot.store.set(GUILD, "marathon_public_template", WITH_MENTION)
    await bot.store.set(GUILD, "marathon_public_done_template", DONE_WITH_MENTION)
    marathon = await show(bot, cog, FOUR, auto=True, hosts=False)
    assert (await mention(bot, marathon, SKY, "plain")).ok

    await walk(bot, cog, marathon, [61])
    (post,) = said_of(bot, f"{WRITTEN} runs **Alpha** on")
    await walk(bot, cog, marathon, [146, 300])

    assert post.content.startswith(f"{WRITTEN} ran **Alpha** today on **Hidden Heroes**")
    assert f"<@{SKY}>" not in post.content


async def test_changing_the_choice_rewrites_what_is_up_in_place_and_posts_nothing(bot, cog):
    fancy_names(bot)
    await bot.store.set(GUILD, "marathon_public_template", WITH_MENTION)
    marathon = await show(bot, cog, FOUR, auto=True)
    await walk(bot, cog, marathon, [45, 61, 130])
    (highlight,) = said_of(bot, f"<@{SKY}> runs **Alpha** on")
    heads = runner_heads_ups(bot, "Beta")[-1]
    (host_heads,) = said_of(bot, f"<@{ANARCHY}> hosts **Alpha** (Any%)")
    count = len(posts(bot))

    assert (await mention(bot, marathon, SKY, "plain")).ok
    assert (await mention(bot, marathon, ANARCHY, "plain")).ok

    assert highlight.content.startswith(f"{WRITTEN} runs **Alpha** on")
    assert heads.content.startswith(f"{WRITTEN} runs **Beta**")
    assert host_heads.content.startswith(f"<@{ANARCHY}> hosts")
    assert len(said_of(bot, "anarchy hosts **Alpha** on")) == 1
    assert len(runner_heads_ups(bot, "Alpha")) == 1
    assert len(posts(bot)) == count
    assert heads.edits[-1]["allowed_mentions"].users is False

    assert (await mention(bot, marathon, SKY, "mention")).ok
    assert highlight.content.startswith(f"<@{SKY}> runs **Alpha** on")
    assert heads.content.startswith(f"<@{SKY}> runs **Beta**") and len(posts(bot)) == count
    assert (await fresh(bot, marathon))["mention_people"] == json.dumps({str(ANARCHY): "plain"})
    assert (await kinds(bot.db)).count("marathon.mention_set") == 3


async def test_a_hosts_plain_name_is_written_on_their_blocks_posts(bot, cog):
    fancy_names(bot)
    marathon = await show(bot, cog, FOUR, hosts=True)
    assert (await mention(bot, marathon, ANARCHY, "plain")).ok

    await walk(bot, cog, marathon, [45])

    assert len(said_of(bot, "anarchy hosts **Alpha**")) == 1 and heads_ups(bot) == []


async def test_the_server_can_write_everyone_plain_and_one_person_can_still_be_an_at(bot, cog):
    await bot.store.set(GUILD, "marathon_mention_people", False)
    marathon = await show(bot, cog, PAIR, hosts=False)
    paired = await pair_runner(bot, bot.guild, FakeActor(), marathon, "Mo", MO, everywhere=True)
    assert paired.ok, paired.message
    assert (await mention(bot, marathon, MO, "mention")).ok
    assert (await mention(bot, marathon, SKY, "plain")).ok

    await walk(bot, cog, marathon, [45])

    assert len(said_of(bot, f"Sky, <@{MO}> runs **Alpha**")) == 1
    assert json.loads((await fresh(bot, marathon))["mention_people"]) == {str(MO): "mention"}
    assert (await kinds(bot.db)).count("marathon.mention_set") == 1


async def test_the_mention_writer_refuses_in_words(bot, cog):
    marathon = await show(bot, cog, FOUR, hosts=False)
    bad = await mention(bot, marathon, SKY, "loud")
    assert not bad.ok and (bad.status, bad.code) == (422, ma.BAD_MENTION_CODE)
    stranger = await mention(bot, marathon, 424242, "plain")
    assert not stranger.ok and stranger.status == 404 and "Hidden Heroes" in stranger.message


# --- the doors on the run's post ----------------------------------------------------------------


def staff_post(bot, game):
    thread = bot.guild.channels[SHOW_ROOM].threads[-1]
    return next(
        one for one in thread.messages if one.content.startswith("**Sky**") and game in one.content
    )


def items_on(message):
    return [getattr(one, "item", one) for one in current_view(message).children]


def labels_on(message):
    return [one.label for one in items_on(message)]


async def test_a_runs_post_carries_each_persons_moves_and_says_who_is_announced(bot, cog):
    marathon = await show(bot, cog, FOUR, hosts=False)
    post = staff_post(bot, "Alpha")
    row = await run_named(bot, marathon, "Alpha")

    assert labels_on(post) == [
        "Do not announce Sky for this run",
        "No @ for Sky",
        "Announce anarchy for this run",
        "No @ for anarchy",
    ]
    assert [one.custom_id for one in items_on(post)] == [
        f"marathon:announce:{marathon['id']}:{row['id']}:{SKY}:out",
        f"marathon:announce:{marathon['id']}:{row['id']}:{SKY}:plain",
        f"marathon:announce:{marathon['id']}:{row['id']}:{ANARCHY}:in",
        f"marathon:announce:{marathon['id']}:{row['id']}:{ANARCHY}:plain",
    ]
    assert post.content.endswith(
        "\nSky: announced for this run — the default"
        "\nanarchy: not announced for this run — host announcements are off for this marathon"
    )
    count = len(bot.guild.channels[SHOW_ROOM].threads[-1].messages)

    assert (await answer(bot, marathon, "Alpha", ANARCHY, "in")).ok
    assert (await mention(bot, marathon, SKY, "plain")).ok

    assert labels_on(post) == [
        "Do not announce Sky for this run",
        "@ Sky again",
        "anarchy: back to the default for this run",
        "No @ for anarchy",
    ]
    assert post.content.endswith(
        "\nSky: announced for this run — the default · written without an @"
        "\nanarchy: announced for this run — set for this run"
    )
    assert len(bot.guild.channels[SHOW_ROOM].threads[-1].messages) == count
    assert post.edits[-1]["allowed_mentions"].users is False
    await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.ANNOUNCE, False)
    await tick_at(bot, cog, marathon, 1)
    assert "Sky: not announced for this run — runner announcements are off" in post.content
    assert "anarchy: announced for this run — set for this run" in post.content
    assert labels_on(post)[0] == "Announce Sky for this run"


async def test_a_runs_post_never_carries_the_whole_marathon_opt_out(bot, cog):
    marathon = await show(bot, cog, FOUR, hosts=False)
    post = staff_post(bot, "Alpha")
    assert not any(one.startswith("Opt ") for one in labels_on(post))
    assert not any(one.custom_id.startswith("marathon:highlight:") for one in items_on(post))

    await announce.set_opt_out(bot, bot.guild, FakeActor(), marathon, [SKY], True)

    assert labels_on(post)[0] == "Announce Sky for this run"
    assert not any(one.startswith("Opt ") for one in labels_on(post))
    assert (
        "Sky: not announced for this run — opted out of every run on this marathon" in post.content
    )


@pytest.mark.parametrize("to", ["optout", "optin", "post", "remove"])
async def test_the_retired_whole_marathon_button_answers_in_words_and_changes_nothing(
    bot, cog, to
):
    marathon = await show(bot, cog, FOUR, hosts=False)
    row = await run_named(bot, marathon, "Alpha")
    custom = f"marathon:highlight:{marathon['id']}:{row['id']}:{to}"
    button = await public.HighlightButton.from_custom_id(
        None, None, re.fullmatch(public.mp.TEMPLATE, custom)
    )
    lead = FakeInteraction(bot, FakeActor(), bot.guild)

    await button.on_click(lead)

    assert public.WHOLE_MARATHON_GONE in lead.sent
    assert ma.opted_out(await fresh(bot, marathon)) == set()
    assert "marathon.announce_opted_out" not in await kinds(bot.db)


async def test_a_persons_button_works_after_a_restart_and_refuses_a_stranger_in_words(bot, cog):
    marathon = await show(bot, cog, FOUR, hosts=False)
    row = await run_named(bot, marathon, "Alpha")
    custom = f"marathon:announce:{marathon['id']}:{row['id']}:{SKY}:out"
    restarted = cogmod.Marathons(bot)
    restarted.client, restarted.clock = cog.client, cog.clock
    bot.cogs[cogmod.COG_NAME] = restarted
    button = await public.AnnounceButton.from_custom_id(
        None, None, re.fullmatch(ma.MOVE_TEMPLATE, custom)
    )
    assert (button.marathon_id, button.run_id, button.user_id, button.to) == (
        marathon["id"],
        row["id"],
        SKY,
        "out",
    )
    assert button.item.custom_id == custom

    bot.store.is_staff = lambda member: False
    stranger = FakeInteraction(bot, Member(42), bot.guild)
    await button.on_click(stranger)
    assert "staff only" in stranger.sent
    assert ma.run_answers(await run_named(bot, marathon, "Alpha")) == {}

    bot.store.is_staff = lambda member: True
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    await button.on_click(lead)
    assert "**Sky** is not announced for **Alpha**" in lead.sent
    assert ma.run_answers(await run_named(bot, marathon, "Alpha")) == {SKY: "out"}
    assert "Sky: back to the default for this run" in labels_on(staff_post(bot, "Alpha"))

    plain = await public.AnnounceButton.from_custom_id(
        None, None, re.fullmatch(ma.MOVE_TEMPLATE, custom.replace(":out", ":plain"))
    )
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    await plain.on_click(lead)
    assert "with no @" in lead.sent


CROWD = [
    a_run(
        1,
        60,
        game="Alpha",
        people=tuple((f"Runner{one}", f"runner{one}", "runner") for one in range(6)),
        length=85,
    )
]


async def test_a_run_with_more_people_than_buttons_fit_carries_one_menu(bot, cog):
    marathon = await show(bot, cog, CROWD, hosts=False)
    for one in range(6):
        paired = await pair_runner(
            bot, bot.guild, FakeActor(), marathon, f"Runner{one}", 9300 + one, everywhere=True
        )
        assert paired.ok, paired.message
    await tick_at(bot, cog, marathon, 1)
    thread = bot.guild.channels[SHOW_ROOM].threads[-1]
    post = next(one for one in thread.messages if one.content.startswith("**Runner0"))
    row = await run_named(bot, marathon, "Alpha")

    (pick,) = items_on(post)
    assert isinstance(pick, discord.ui.Select)
    assert pick.custom_id == f"marathon:announce:{marathon['id']}:{row['id']}:pick"
    assert pick.placeholder == "Announcements for a person on this run…"
    assert len(pick.options) == 12
    assert (pick.options[0].value, pick.options[0].label) == (
        "9300:out",
        "Do not announce Runner0 for this run",
    )
    assert len(current_view(post).to_components()) == 1

    chosen = await public.AnnouncePick.from_custom_id(
        None, None, re.fullmatch(ma.PICK_TEMPLATE, pick.custom_id)
    )
    chosen.item._values = ["9303:out"]
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    await chosen.on_click(lead)
    assert "**Runner3** is not announced for **Alpha**" in lead.sent
    assert ma.run_answers(await run_named(bot, marathon, "Alpha")) == {9303: "out"}
    assert items_on(post)[0].options[6].label == "Runner3: back to the default for this run"
    chosen.item._values = ["nonsense"]
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    await chosen.on_click(lead)
    assert "nothing was changed" in lead.sent


# --- review fixes 2026-10-06: a post already up only keeps or loses names -----------------------

BEE = 8103
ZED_RUNS = ("Zed", "zedruns", "runner")
CO_HOST = ("bee", "beehosts", "host")
SHARED = [
    a_run(1, 60, game="Alpha", people=(("clipboard", "cb", "runner"), HOST, CO_HOST), length=85),
    a_run(2, 145, game="Beta", people=(("sorbet", "ts", "runner"), HOST, CO_HOST), length=35),
]
RUNS_ONE = [
    a_run(1, 60, game="Alpha", people=(("clipboard", "cb", "runner"), HOST), length=85),
    a_run(2, 145, game="Beta", people=(("anarchy", "anarchyasf", "runner"), HOST), length=35),
    a_run(3, 180, game="Gamma", people=(("sorbet", "ts", "runner"), HOST), length=50),
    a_run(4, 230, game="Delta", people=(("sy", "sy", "runner"), HOST), length=30),
]


async def counted(bot, cog, runs, **given):
    await bot.store.set(GUILD, "marathon_hosts_count_as_ours", True)
    return await show(bot, cog, runs, **given)


def said_publicly(bot):
    return "\n".join(one.content for one in posts(bot))


def names_the_host(bot):
    said = said_publicly(bot)
    return "anarchy" in said or str(ANARCHY) in said


async def because_of(bot, kind):
    cur = await bot.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id", (kind,)
    )
    return [json.loads(row["details"]).get("because") for row in await cur.fetchall()]


async def reread(bot, cog, marathon, runs):
    cog.client.runs_given = list(runs)
    assert (await cog.refresh(bot.guild, await fresh(bot, marathon))).ok


async def test_a_reminder_already_up_never_gains_a_host_who_is_not_announced(bot, cog):
    marathon = await counted(bot, cog, FOUR, hosts=False)
    await walk(bot, cog, marathon, [45])
    (heads,) = runner_heads_ups(bot, "Alpha")
    assert mt.is_ours(await run_named(bot, marathon, "Alpha")) and not names_the_host(bot)

    assert (await answer(bot, marathon, "Alpha", SKY, "out")).ok
    await walk(bot, cog, marathon, [46, 47])

    assert heads.content.startswith(f"<@{SKY}> runs **Alpha**") and heads.edits == []
    assert not names_the_host(bot)


async def test_a_reminder_remembers_who_it_named(bot, cog):
    marathon = await counted(bot, cog, FOUR, hosts=False)

    await walk(bot, cog, marathon, [45])

    row = await run_named(bot, marathon, "Alpha")
    assert json.loads(row["reminder_posts"])["15"]["public"]["people"] == [SKY]


async def test_a_moved_reminder_is_rewritten_without_the_host_who_is_not_announced(bot, cog):
    marathon = await counted(bot, cog, FOUR, hosts=False)
    await walk(bot, cog, marathon, [45])
    (heads,) = runner_heads_ups(bot, "Alpha")

    await reread(
        bot,
        cog,
        marathon,
        [a_run(1, 75, game="Alpha", people=(SKY_RUNS, HOST), length=70), *FOUR[1:]],
    )
    await tick_at(bot, cog, marathon, 46)

    assert heads.content.startswith(f"<@{SKY}> runs **Alpha**") and len(heads.edits) == 1
    assert mt.stamp_of(NOW + timedelta(minutes=75), "f") in heads.content
    assert not names_the_host(bot)


async def test_a_highlight_whose_runner_left_the_schedule_never_names_the_host_instead(bot, cog):
    marathon = await counted(bot, cog, FOUR, auto=True, hosts=False)
    await walk(bot, cog, marathon, [45, 61])
    (post,) = runner_highlights(bot, "Alpha")

    await reread(
        bot,
        cog,
        marathon,
        [a_run(1, 60, game="Alpha", people=(ZED_RUNS, HOST), length=85), *FOUR[1:]],
    )
    await walk(bot, cog, marathon, [62, 63])

    assert post.content == "Staff took down the highlight for **Sky** on **Hidden Heroes**."
    assert not names_the_host(bot)
    assert await because_of(bot, "marathon.public_highlight_removed") == ["not_on_run"]


async def test_the_taken_down_line_names_only_who_the_post_named(bot, cog):
    marathon = await counted(bot, cog, FOUR, auto=True, hosts=False)
    await walk(bot, cog, marathon, [45, 61])
    (post,) = runner_highlights(bot, "Alpha")

    assert (await answer(bot, marathon, "Alpha", SKY, "out")).ok

    assert post.content == "Staff took down the highlight for **Sky** on **Hidden Heroes**."
    assert not names_the_host(bot)
    assert (await answer(bot, marathon, "Alpha", SKY, "default")).ok
    assert post.content.startswith("**Sky** runs **Alpha**") and not names_the_host(bot)


async def test_a_finished_highlight_never_names_a_host_who_is_not_announced(bot, cog):
    marathon = await counted(bot, cog, FOUR, auto=True, hosts=False)

    await walk(bot, cog, marathon, [45, 61, 130, 146, 181, 231, 400])

    assert len(said_of(bot, "**Sky** ran **Alpha**")) == 1
    assert len(said_of(bot, "**Sky** ran **Beta**")) == 1
    assert heads_ups(bot) == [] and highlights(bot) == [] and not names_the_host(bot)


async def test_a_host_block_stays_silent_while_hosts_count_as_ours_and_are_not_announced(bot, cog):
    marathon = await counted(bot, cog, HIDDEN_HEROES, auto=True, hosts=False)

    await walk(bot, cog, marathon, [45, 61, 130, 146, 181, 231, 400])

    assert posts(bot) == []


async def test_a_host_who_counts_as_ours_joins_a_post_only_once_announced(bot, cog):
    marathon = await counted(bot, cog, FOUR, auto=True, hosts=False)
    await walk(bot, cog, marathon, [45, 61])
    (post,) = runner_highlights(bot, "Alpha")

    assert (await answer(bot, marathon, "Alpha", ANARCHY, "in")).ok

    assert post.content.startswith("**Sky, anarchy** runs **Alpha**")
    assert (await answer(bot, marathon, "Alpha", ANARCHY, "default")).ok
    assert post.content.startswith("**Sky** runs **Alpha**")


async def test_a_highlight_remembers_who_it_named_and_one_from_before_keeps_its_names(bot, cog):
    marathon = await counted(bot, cog, FOUR, auto=True, hosts=True)
    await walk(bot, cog, marathon, [45, 61])
    (post,) = said_of(bot, "**Sky, anarchy** runs **Alpha**")
    row = await run_named(bot, marathon, "Alpha")
    assert [one["user_id"] for one in json.loads(row["public_people"])] == [SKY, ANARCHY]
    await bot.db.conn.execute(
        "UPDATE marathon_runs SET public_people = NULL WHERE id = ?", (row["id"],)
    )
    await bot.db.conn.commit()
    await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.HOST_ANNOUNCE, False)

    await walk(bot, cog, marathon, [62])

    assert post.content.startswith("**Sky, anarchy** runs **Alpha**")
    row = await run_named(bot, marathon, "Alpha")
    assert [one["user_id"] for one in json.loads(row["public_people"])] == [SKY, ANARCHY]


async def co_hosted(bot, cog):
    marathon = await show(bot, cog, SHARED, auto=True, hosts=True)
    paired = await pair_runner(bot, bot.guild, FakeActor(), marathon, "bee", BEE, everywhere=True)
    assert paired.ok, paired.message
    await walk(bot, cog, marathon, [45, 61])
    (post,) = said_of(bot, "**anarchy, bee** hosts **Alpha**")
    return marathon, post


async def test_a_move_on_one_co_host_leaves_the_other_on_the_post(bot, cog):
    marathon, post = await co_hosted(bot, cog)
    await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.HOST_ANNOUNCE, False)
    await tick_at(bot, cog, marathon, 62)
    assert post.content.startswith("**anarchy, bee** hosts **Alpha**")

    assert (await answer(bot, marathon, "Alpha", ANARCHY, "in")).ok
    assert post.content.startswith("**anarchy, bee** hosts **Alpha**")
    assert (await answer(bot, marathon, "Alpha", ANARCHY, "default")).ok

    assert post.content.startswith("**bee** hosts **Alpha**")
    await tick_at(bot, cog, marathon, 63)
    assert post.content.startswith("**bee** hosts **Alpha**")
    assert "marathon.host_highlight_removed" not in await kinds(bot.db)


async def test_a_co_host_left_out_of_every_run_leaves_the_other_and_the_line_names_who_was_up(
    bot, cog
):
    marathon, post = await co_hosted(bot, cog)

    for game in ("Alpha", "Beta"):
        assert (await answer(bot, marathon, game, ANARCHY, "out")).ok
    assert post.content.startswith("**bee** hosts **Alpha**")
    for game in ("Alpha", "Beta"):
        assert (await answer(bot, marathon, game, BEE, "out")).ok

    assert post.content == "Staff took down the highlight for **bee** on **Hidden Heroes**."


async def test_a_runs_own_yes_where_the_host_runs_never_announces_their_block(bot, cog):
    marathon = await show(bot, cog, RUNS_ONE, auto=True, hosts=True)
    out = await announce.set_opt_out(bot, bot.guild, FakeActor(), marathon, [ANARCHY], True)
    assert out.ok

    assert (await answer(bot, marathon, "Beta", ANARCHY, "in")).ok
    await walk(bot, cog, marathon, [45, 61, 130, 146, 165, 181, 215, 231])

    assert heads_ups(bot) == [] and highlights(bot) == []
    assert len(said_of(bot, f"<@{ANARCHY}> runs **Beta**")) == 2
    assert len(said_of(bot, "**anarchy** ran **Beta**")) == 1
    assert "hosts **" not in said_publicly(bot) and "hosted **" not in said_publicly(bot)


async def test_a_runs_own_yes_where_the_host_only_hosts_announces_their_block(bot, cog):
    marathon = await show(bot, cog, RUNS_ONE, auto=True, hosts=True)
    out = await announce.set_opt_out(bot, bot.guild, FakeActor(), marathon, [ANARCHY], True)
    assert out.ok

    assert (await answer(bot, marathon, "Gamma", ANARCHY, "in")).ok
    await walk(bot, cog, marathon, [45, 61])

    assert [game_of(one) for one in heads_ups(bot)] == ["Alpha"]
    assert [game_of(one) for one in highlights(bot)] == ["Alpha"]


async def test_a_run_that_is_over_refuses_its_own_answer_in_words_and_changes_nothing(bot, cog):
    marathon = await show(bot, cog, FOUR, auto=True, hosts=False)
    await walk(bot, cog, marathon, [45, 61, 146])
    (post,) = said_of(bot, "**Sky** ran **Alpha**")
    row = await run_named(bot, marathon, "Alpha")
    assert row["state"] == mt.DONE

    said = await answer(bot, marathon, "Alpha", SKY, "out")

    assert not said.ok and said.status == 409
    assert said.message == "**Alpha** is over, so nothing was changed."
    assert post.content.startswith("**Sky** ran **Alpha**")
    assert ma.run_answers(await run_named(bot, marathon, "Alpha")) == {}
    assert "marathon.announce_run_set" not in await kinds(bot.db)
    assert "marathon.public_highlight_removed" not in await kinds(bot.db)

    stale = await public.AnnounceButton.from_custom_id(
        None,
        None,
        re.fullmatch(ma.MOVE_TEMPLATE, f"marathon:announce:{marathon['id']}:{row['id']}:{SKY}:out"),
    )
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    await stale.on_click(lead)
    assert "**Alpha** is over, so nothing was changed." in lead.sent
    assert post.content.startswith("**Sky** ran **Alpha**")


async def test_a_finished_highlight_keeps_how_its_names_were_written(bot, cog):
    await bot.store.set(GUILD, "marathon_public_template", WITH_MENTION)
    await bot.store.set(GUILD, "marathon_public_done_template", DONE_WITH_MENTION)
    marathon = await show(bot, cog, FOUR, auto=True, hosts=False)
    await walk(bot, cog, marathon, [61, 146])
    (done,) = said_of(bot, f"<@{SKY}> ran **Alpha**")
    (live,) = said_of(bot, f"<@{SKY}> runs **Beta**")
    edits = len(done.edits)

    assert (await mention(bot, marathon, SKY, "plain")).ok
    await tick_at(bot, cog, marathon, 147)

    assert done.content.startswith(f"<@{SKY}> ran **Alpha**") and len(done.edits) == edits
    assert live.content.startswith("Sky runs **Beta**")


async def test_a_host_highlight_skipped_for_the_host_default_leaves_one_row_a_block(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES, auto=True, hosts=False)

    await walk(bot, cog, marathon, [45, 61, 62, 146, 147, 181, 182])

    assert highlights(bot) == []
    assert await because_of(bot, "marathon.host_highlight_skipped") == ["host_announcements_off"]
    logged = await details_of(bot.db, "marathon.host_highlight_skipped")
    assert logged["members"] == [ANARCHY] and logged["game"] == "Titanfall 2"


async def test_a_skipped_host_highlight_still_goes_up_once_hosts_are_announced(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES, auto=True, hosts=False)
    await walk(bot, cog, marathon, [45, 61])
    assert highlights(bot) == []

    await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.HOST_ANNOUNCE, True)
    await walk(bot, cog, marathon, [146])

    assert len(highlights(bot)) == 1


async def test_the_log_says_which_decision_took_a_post_down(bot, cog):
    marathon = await show(bot, cog, FOUR, auto=True, hosts=True)
    await walk(bot, cog, marathon, [45, 61])

    await announce.set_opt_out(bot, bot.guild, FakeActor(), marathon, [SKY], True)
    await announce.set_opt_out(bot, bot.guild, FakeActor(), marathon, [ANARCHY], True)

    assert await because_of(bot, "marathon.public_highlight_removed") == ["opted_out"]
    assert await because_of(bot, "marathon.host_highlight_removed") == ["opted_out"]


async def test_a_runs_own_no_says_so_in_the_log(bot, cog):
    marathon = await show(bot, cog, FOUR, auto=True, hosts=True)
    await walk(bot, cog, marathon, [45, 61])

    assert (await answer(bot, marathon, "Alpha", SKY, "out")).ok
    for game in ("Alpha", "Beta", "Gamma", "Delta"):
        assert (await answer(bot, marathon, game, ANARCHY, "out")).ok

    assert await because_of(bot, "marathon.public_highlight_removed") == ["run_answer"]
    assert await because_of(bot, "marathon.host_highlight_removed") == ["run_answer"]


async def test_back_to_the_default_with_hosts_off_says_so_in_the_log(bot, cog):
    marathon = await show(bot, cog, FOUR, auto=True, hosts=False)
    assert (await answer(bot, marathon, "Alpha", ANARCHY, "in")).ok
    await walk(bot, cog, marathon, [45, 61])
    assert len(highlights(bot)) == 1

    assert (await answer(bot, marathon, "Alpha", ANARCHY, "default")).ok

    assert await because_of(bot, "marathon.host_highlight_removed") == ["hosts_off"]


def test_a_plain_name_is_the_schedules_name_and_never_links():
    found = ma.Policy(mentions={SKY: ma.PLAIN, MO: ma.PLAIN})
    people = [
        {"user_id": SKY, "name": "Sky_*Aiva*", "part": "runner"},
        {"user_id": MO, "name": "see https://evil.example/x @everyone", "part": "runner"},
        {"user_id": BEE, "name": "bee", "part": "runner"},
    ]

    first, second, third = announce.named(found, people)

    assert first["plain"] == ESCAPED
    assert "https://" not in second["plain"] and "evil.example/x" in second["plain"]
    assert "@everyone" not in second["plain"]
    assert "plain" not in third


async def crowded(bot, cog, count):
    runs = [
        a_run(
            1,
            60,
            game="Alpha",
            people=tuple((f"Runner{one}", f"runner{one}", "runner") for one in range(count)),
            length=85,
        )
    ]
    marathon = await show(bot, cog, runs, hosts=False)
    for one in range(count):
        paired = await pair_runner(
            bot, bot.guild, FakeActor(), marathon, f"Runner{one}", 9300 + one, everywhere=True
        )
        assert paired.ok, paired.message
    await tick_at(bot, cog, marathon, 1)
    thread = bot.guild.channels[SHOW_ROOM].threads[-1]
    return marathon, next(one for one in thread.messages if one.content.startswith("**Runner0"))


@pytest.mark.parametrize(("count", "sizes"), [(13, [24, 2]), (20, [24, 16])])
async def test_past_twelve_people_a_runs_post_carries_a_menu_for_every_twelve(
    bot, cog, count, sizes
):
    marathon, post = await crowded(bot, cog, count)
    row = await run_named(bot, marathon, "Alpha")

    picks = items_on(post)

    assert [len(one.options) for one in picks] == sizes
    assert [one.custom_id for one in picks] == [
        f"marathon:announce:{marathon['id']}:{row['id']}:pick",
        f"marathon:announce:{marathon['id']}:{row['id']}:pick2",
    ]
    offered = [option.value for one in picks for option in one.options]
    for member in range(9300, 9300 + count):
        assert f"{member}:out" in offered and f"{member}:plain" in offered
    assert len(current_view(post).to_components()) == 2
    edits = len(post.edits)
    await walk(bot, cog, marathon, [2, 3])
    assert len(post.edits) == edits

    last = await public.AnnouncePick.from_custom_id(
        None, None, re.fullmatch(ma.PICK_TEMPLATE, picks[1].custom_id)
    )
    assert last.item.custom_id == picks[1].custom_id
    last.item._values = [f"{9300 + count - 1}:out"]
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    await last.on_click(lead)
    assert f"**Runner{count - 1}** is not announced for **Alpha**" in lead.sent
    assert ma.run_answers(await run_named(bot, marathon, "Alpha")) == {9300 + count - 1: "out"}


async def test_a_move_on_one_co_host_leaves_the_other_on_the_blocks_reminder(bot, cog):
    marathon = await show(bot, cog, SHARED, hosts=True)
    paired = await pair_runner(bot, bot.guild, FakeActor(), marathon, "bee", BEE, everywhere=True)
    assert paired.ok, paired.message
    await walk(bot, cog, marathon, [45])
    (heads,) = said_of(bot, f"<@{ANARCHY}>, <@{BEE}> hosts **Alpha**")
    await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.HOST_ANNOUNCE, False)
    assert (await answer(bot, marathon, "Alpha", ANARCHY, "in")).ok
    assert (await answer(bot, marathon, "Alpha", ANARCHY, "default")).ok

    await reread(
        bot,
        cog,
        marathon,
        [
            a_run(
                1,
                75,
                game="Alpha",
                people=(("clipboard", "cb", "runner"), HOST, CO_HOST),
                length=70,
            ),
            SHARED[1],
        ],
    )
    await tick_at(bot, cog, marathon, 46)

    assert heads.content.startswith(f"<@{BEE}> hosts **Alpha**") and len(heads.edits) == 1
    assert mt.stamp_of(NOW + timedelta(minutes=75), "f") in heads.content


async def test_a_host_reminder_already_up_is_carried_when_host_announcements_go_off(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES, hosts=True)
    await walk(bot, cog, marathon, [45])
    (heads,) = heads_ups(bot)
    await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.HOST_ANNOUNCE, False)

    moved = [
        a_run(1, 75, game="Titanfall 2", people=(("clipboard", "cb", "runner"), HOST), length=70),
        *HIDDEN_HEROES[1:],
    ]
    await reread(bot, cog, marathon, moved)
    await tick_at(bot, cog, marathon, 46)

    assert heads.content.startswith(f"<@{ANARCHY}> hosts **Titanfall 2**")
    assert mt.stamp_of(NOW + timedelta(minutes=75), "f") in heads.content
    assert len(posts(bot)) == 1


async def test_a_finished_highlight_whose_runner_left_the_schedule_is_left_as_it_stands(bot, cog):
    marathon = await counted(bot, cog, FOUR, auto=True, hosts=False)
    await walk(bot, cog, marathon, [45, 61, 146])
    (post,) = said_of(bot, "**Sky** ran **Alpha**")
    edits = len(post.edits)
    row = await run_named(bot, marathon, "Alpha")
    people = [one for one in mt.people_of(row) if one.get("user_id") != SKY]
    await bot.db.conn.execute(
        "UPDATE marathon_runs SET people = ? WHERE id = ?", (json.dumps(people), row["id"])
    )
    await bot.db.conn.commit()

    await walk(bot, cog, marathon, [147, 148])

    assert post.content.startswith("**Sky** ran **Alpha**") and len(post.edits) == edits
    assert not names_the_host(bot)
    assert "marathon.public_highlight_removed" not in await kinds(bot.db)
