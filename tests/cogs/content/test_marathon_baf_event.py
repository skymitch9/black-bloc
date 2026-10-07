# ruff: noqa: F401, F811
import json
import re
from datetime import timedelta

import pytest

from black_bloc import marathon_baf_event as baf
from black_bloc import marathon_role_ping as mrp
from black_bloc.cogs.content import marathon as cogmod
from black_bloc.cogs.content import marathon_baf_event as event
from black_bloc.cogs.content import marathon_role_ping as role_ping
from black_bloc.cogs.content import marathon_thread_controls as controls
from black_bloc.cogs.content.marathon import Marathons, runs_of, update_marathon
from tests.cogs.content.test_marathon import (
    NOW,
    SKY,
    FakeClient,
    Member,
    a_run,
    bot,
    cog,
    threading,
)
from tests.cogs.content.test_marathon_runner_posts import (
    events_room,
    follow,
    fresh,
    the_thread,
    tracked,
)
from tests.cogs.content.test_spotlight import (
    CHANNEL,
    GUILD,
    FakeActor,
    FakeInteraction,
    FakeRole,
    details_of,
    kinds,
)

MARATHON_ROLE = 6100
LEADS = 6200
SKY_RUNS = (("Sky", "skyruns", "runner"),)
OTHER = (("Somebody", None, "runner"),)
DAY = 1440


@pytest.fixture(autouse=True)
async def marks(bot):
    await bot.store.set(GUILD, "marathon_reminder_minutes", "1440, 120, 15")


def day_of_runs(*people, first=180, gap=60, ident=1):
    return [
        a_run(ident + index, first + index * gap, game=f"Game {ident + index}", people=one)
        for index, one in enumerate(people)
    ]


async def event_marathon(bot, cog, runs, *, ping=True, name=None):
    """A tracked marathon with a thread, the Marathon role picked and its ping switch on."""
    cog.client.runs_given = list(runs)
    marathon = await tracked(bot)
    role = FakeRole(MARATHON_ROLE, "Marathon")
    role.mentionable = True
    bot.guild.roles.append(role)
    await bot.store.set(GUILD, "marathon_role_id", MARATHON_ROLE)
    await update_marathon(bot.db, marathon["id"], ping_role=1 if ping else 0)
    if name:
        await update_marathon(bot.db, marathon["id"], name=name)
    return await fresh(bot, marathon)


async def at(bot, cog, marathon, minutes):
    cog.clock = lambda: NOW + timedelta(minutes=minutes)
    await follow(bot, cog, marathon)


async def through(bot, cog, marathon, *minutes):
    for one in minutes:
        await at(bot, cog, marathon, one)


def carrying(bot):
    return [
        one
        for one in bot.guild.channels[CHANNEL].messages
        if f"<@&{MARATHON_ROLE}>" in one.content
    ]


def allowed(message):
    found = message.kwargs["allowed_mentions"].roles
    return [one.id for one in found] if found else []


async def rows(bot, kind):
    cur = await bot.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id", (kind,)
    )
    return [json.loads(row["details"]) for row in await cur.fetchall()]


def questions(bot):
    return [one for one in the_thread(bot).messages if "a BaF event?" in one.content]


async def pings_of(bot, marathon):
    return baf.pings_of(await fresh(bot, marathon))


# --- one ping a day ------------------------------------------------------------------------------


async def test_a_four_run_all_baf_day_pings_once_at_the_first_runs_two_hour_heads_up(bot, cog):
    marathon = await event_marathon(bot, cog, day_of_runs(*[SKY_RUNS] * 4))

    await through(bot, cog, marathon, 0, 60, 120, 165, 180, 225, 240, 285, 300, 345)

    posted = await rows(bot, "marathon.public_reminded")
    assert [(one["game"], one["mark"]) for one in posted] == [
        ("Game 1", 120),
        ("Game 2", 120),
        ("Game 1", 15),
        ("Game 3", 120),
        ("Game 2", 15),
        ("Game 4", 120),
        ("Game 3", 15),
        ("Game 4", 15),
    ]
    assert [one.get("marathon_role") for one in posted] == [MARATHON_ROLE] + [None] * 7
    (pinged,) = carrying(bot)
    assert "**Game 1**" in pinged.content and allowed(pinged)[-1] == MARATHON_ROLE
    assert pinged.content.count(f"<@&{MARATHON_ROLE}>") == 1
    fifteens = [one for one in posted if one["mark"] == 15]
    assert len(fifteens) == 4
    assert {one["marathon_role_reason"] for one in fifteens} == {mrp.BAF_EVENT_PINGED}
    (stored,) = await pings_of(bot, marathon)
    assert (stored["game"], stored["mark"], stored["sent"]) == ("Game 1", 120, True)
    assert stored["message_id"] == pinged.id
    assert not any(
        f"<@&{MARATHON_ROLE}>" in one.content for one in the_thread(bot).messages if one.content
    )


async def test_a_mixed_day_under_the_share_pings_each_baf_run_at_fifteen_as_before(bot, cog):
    marathon = await event_marathon(bot, cog, day_of_runs(SKY_RUNS, OTHER, OTHER, SKY_RUNS))

    await through(bot, cog, marathon, 0, 60, 165, 240, 345)

    posted = await rows(bot, "marathon.public_reminded")
    assert [(one["game"], one["mark"], one.get("marathon_role")) for one in posted] == [
        ("Game 1", 120, None),
        ("Game 1", 15, MARATHON_ROLE),
        ("Game 4", 120, None),
        ("Game 4", 15, MARATHON_ROLE),
    ]
    assert ["marathon_role" in one for one in posted] == [False, True, False, True]
    assert not any("baf_event_day" in one for one in posted)
    assert questions(bot) == []
    stored = await pings_of(bot, marathon)
    assert [(one["game"], one["per_run"], one["sent"]) for one in stored] == [
        ("Game 1", True, True),
        ("Game 4", True, True),
    ]


async def test_a_show_named_black_in_a_flash_is_a_baf_event_whatever_its_runs(bot, cog):
    marathon = await event_marathon(
        bot,
        cog,
        day_of_runs(OTHER, SKY_RUNS, OTHER, SKY_RUNS),
        name="Black in a Flash: Soul Train",
    )

    await through(bot, cog, marathon, 0, 120, 225, 240, 345)

    posted = await rows(bot, "marathon.public_reminded")
    assert [(one["game"], one["mark"], one.get("marathon_role")) for one in posted] == [
        ("Game 2", 120, MARATHON_ROLE),
        ("Game 2", 15, None),
        ("Game 4", 120, None),
        ("Game 4", 15, None),
    ]
    assert questions(bot) == []
    said = role_ping.status_line(
        bot, bot.guild, await fresh(bot, marathon), rows=await runs_of(bot.db, marathon["id"])
    )
    assert "the show is named Black in a Flash" in said


async def test_staff_no_beats_an_all_baf_day_and_staff_yes_beats_a_mixed_one(bot, cog):
    marathon = await event_marathon(bot, cog, day_of_runs(*[SKY_RUNS] * 3))
    said = await event.set_baf_event(bot, bot.guild, FakeActor(), marathon, "no")
    assert said.ok and "is not a BaF event now" in said.message

    await through(bot, cog, marathon, 0, 60, 165)

    posted = await rows(bot, "marathon.public_reminded")
    assert [(one["mark"], one.get("marathon_role")) for one in posted] == [
        (120, None),
        (15, MARATHON_ROLE),
    ]
    assert [one["per_run"] for one in await pings_of(bot, marathon)] == [True]
    logged = await details_of(bot.db, "marathon.baf_event_set")
    assert (logged["from"], logged["to"], logged["via"]) == ("follow", "no", "discord")


async def test_staff_yes_makes_a_mixed_day_ping_once(bot, cog):
    marathon = await event_marathon(bot, cog, day_of_runs(SKY_RUNS, OTHER, OTHER, SKY_RUNS))
    await event.set_baf_event(bot, bot.guild, FakeActor(), marathon, True)

    await through(bot, cog, marathon, 0, 60, 165, 240, 345)

    posted = await rows(bot, "marathon.public_reminded")
    assert [(one["game"], one["mark"], one.get("marathon_role")) for one in posted] == [
        ("Game 1", 120, MARATHON_ROLE),
        ("Game 1", 15, None),
        ("Game 4", 120, None),
        ("Game 4", 15, None),
    ]


async def test_a_word_that_is_not_follow_yes_or_no_is_refused_in_words(bot, cog):
    marathon = await event_marathon(bot, cog, day_of_runs(*[SKY_RUNS] * 3))

    said = await event.set_baf_event(bot, bot.guild, FakeActor(), marathon, "maybe")

    assert not said.ok and said.status == 422
    assert "Say follow, yes or no" in said.message and "nothing was changed" in said.message
    assert (await fresh(bot, marathon))["baf_event"] is None


# --- asking Leads --------------------------------------------------------------------------------


async def asking(bot, cog, runs):
    role = FakeRole(LEADS, "Leads")
    role.mentionable = True
    bot.guild.roles.append(role)
    await bot.store.set(GUILD, "marathon_baf_event_ask_role_id", LEADS)
    return await event_marathon(bot, cog, runs)


async def unsure(bot, cog):
    return await asking(bot, cog, day_of_runs(SKY_RUNS, SKY_RUNS, OTHER, SKY_RUNS))


async def test_a_day_at_the_share_asks_leads_once_in_the_thread_and_really_mentions_them(
    bot, cog
):
    marathon = await unsure(bot, cog)

    await through(bot, cog, marathon, 0, 1, 2)
    await cog.tick_once()

    (asked,) = questions(bot)
    assert asked.content == (
        f"<@&{LEADS}> Is **SS4C** a BaF event? 3 of its 4 runs have a BaF runner."
    )
    mentions = asked.kwargs["allowed_mentions"]
    assert [one.id for one in mentions.roles] == [LEADS]
    assert mentions.everyone is False and mentions.users is False
    buttons = [getattr(one, "item", one) for one in asked.kwargs["view"].children]
    assert [one.label for one in buttons] == ["Yes, a BaF event", "No, not a BaF event"]
    assert [one.custom_id for one in buttons] == [
        f"marathon:bafevent:{marathon['id']}:yes",
        f"marathon:bafevent:{marathon['id']}:no",
    ]
    (logged,) = await rows(bot, "marathon.baf_event_asked")
    assert (logged["baf"], logged["runs"], logged["role"]) == (3, 4, LEADS)
    assert logged["message_id"] == asked.id and logged["notifies"] is True
    assert baf.asks_of(await fresh(bot, marathon))[0]["message_id"] == asked.id


async def test_no_ask_role_still_posts_the_question_and_mentions_nobody(bot, cog):
    marathon = await unsure(bot, cog)
    await bot.store.clear(GUILD, "marathon_baf_event_ask_role_id")

    await at(bot, cog, marathon, 0)

    (asked,) = questions(bot)
    assert asked.content.startswith("Is **SS4C** a BaF event?")
    assert not asked.kwargs["allowed_mentions"].roles
    assert (await details_of(bot.db, "marathon.baf_event_asked"))["role"] is None


async def test_an_unanswered_day_behaves_as_before_and_a_restart_never_asks_twice(bot, cog):
    marathon = await unsure(bot, cog)
    await through(bot, cog, marathon, 0, 60)
    again = Marathons(bot)
    again.client, again.clock = cog.client, cog.clock
    bot.cogs[cogmod.COG_NAME] = again

    await through(bot, again, marathon, 61, 120, 165, 225)

    assert len(questions(bot)) == 1
    posted = await rows(bot, "marathon.public_reminded")
    assert [(one["game"], one["mark"], one.get("marathon_role")) for one in posted] == [
        ("Game 1", 120, None),
        ("Game 2", 120, None),
        ("Game 1", 15, MARATHON_ROLE),
        ("Game 2", 15, MARATHON_ROLE),
    ]
    assert {one["per_run"] for one in await pings_of(bot, marathon)} == {True}


async def test_yes_inside_the_last_two_hours_pings_once_at_the_next_heads_up(bot, cog):
    marathon = await unsure(bot, cog)
    await through(bot, cog, marathon, 0, 60)
    (asked,) = questions(bot)
    button = await event.AskButton.from_custom_id(
        None, None, re.fullmatch(event.ASK_TEMPLATE, f"marathon:bafevent:{marathon['id']}:yes")
    )
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    lead.message = asked

    await button.on_click(lead)
    await through(bot, cog, marathon, 120, 165, 225, 240, 345)

    assert "is a BaF event now" in lead.sent
    assert (await fresh(bot, marathon))["baf_event"] is None
    assert baf.asks_of(await fresh(bot, marathon))[0]["answer"] == "yes"
    assert asked.content.endswith(f"<@{FakeActor().id}> answered: a BaF event.")
    assert asked.content.startswith(f"<@&{LEADS}> Is **SS4C** a BaF event?")
    assert asked.edits[-1]["allowed_mentions"].roles in (None, [], False) or not asked.edits[-1][
        "allowed_mentions"
    ].roles
    posted = await rows(bot, "marathon.public_reminded")
    assert [(one["game"], one["mark"], one.get("marathon_role")) for one in posted] == [
        ("Game 1", 120, None),
        ("Game 2", 120, None),
        ("Game 1", 15, MARATHON_ROLE),
        ("Game 2", 15, None),
        ("Game 4", 120, None),
        ("Game 4", 15, None),
    ]
    assert len(carrying(bot)) == 1 and len(questions(bot)) == 1
    logged = await details_of(bot.db, "marathon.baf_event_set")
    assert (logged["to"], logged["by"], logged["via"]) == ("yes", "question", "discord")
    assert logged["actor"] if "actor" in logged else True


async def test_the_questions_buttons_work_after_a_restart_and_refuse_a_non_staff_press(bot, cog):
    marathon = await unsure(bot, cog)
    await at(bot, cog, marathon, 0)
    custom = questions(bot)[0].kwargs["view"].children[1].item.custom_id
    button = await event.AskButton.from_custom_id(
        None, None, re.fullmatch(event.ASK_TEMPLATE, custom)
    )
    assert (button.marathon_id, button.to) == (marathon["id"], "no")

    bot.store.is_staff = lambda member: False
    stranger = FakeInteraction(bot, Member(42), bot.guild)
    await button.on_click(stranger)

    assert "staff only" in stranger.sent and "nothing was changed" in stranger.sent
    assert "answer" not in baf.asks_of(await fresh(bot, marathon))[0]
    assert "marathon.baf_event_set" not in await kinds(bot.db)

    bot.store.is_staff = lambda member: True
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    await button.on_click(lead)

    assert "is not a BaF event now" in lead.sent
    assert (await fresh(bot, marathon))["baf_event"] is None
    assert baf.asks_of(await fresh(bot, marathon))[0]["answer"] == "no"
    assert questions(bot)[0].content.endswith("answered: not a BaF event.")
    again = FakeInteraction(bot, FakeActor(), bot.guild)
    await button.on_click(again)
    assert "is already not a BaF event, so nothing was changed" in again.sent
    lost = FakeInteraction(bot, FakeActor(), bot.guild)
    lost.message = the_thread(bot).messages[0]
    await button.on_click(lost)
    assert "is not one the bot still holds" in lost.sent and "BaF event switch" in lost.sent


async def test_a_schedule_change_after_the_answer_never_asks_again(bot, cog):
    marathon = await unsure(bot, cog)
    await at(bot, cog, marathon, 0)
    await event.answered(bot, bot.guild, FakeActor(), marathon["id"], "no")
    await event.set_baf_event(bot, bot.guild, FakeActor(), await fresh(bot, marathon), None)
    cog.client.runs_given = day_of_runs(SKY_RUNS, SKY_RUNS, OTHER, SKY_RUNS, SKY_RUNS)

    await cog.refresh(bot.guild, await fresh(bot, marathon))
    await through(bot, cog, marathon, 1, 2)

    assert len(questions(bot)) == 1
    assert (await kinds(bot.db)).count("marathon.baf_event_asked") == 1


async def test_a_question_that_cannot_be_posted_is_logged_and_tried_again_later(bot, cog):
    marathon = await unsure(bot, cog)
    the_thread(bot).send_raises = RuntimeError("no")

    await through(bot, cog, marathon, 0, 1, 2)

    assert questions(bot) == []
    assert (await kinds(bot.db)).count("marathon.baf_event_ask_failed") == 1
    the_thread(bot).send_raises = None
    await through(bot, cog, marathon, 5, 11, 12)
    assert len(questions(bot)) == 1


# --- once is a stored fact -----------------------------------------------------------------------


async def pinged_day(bot, cog, runs=None):
    marathon = await event_marathon(bot, cog, runs or day_of_runs(*[SKY_RUNS] * 4))
    await through(bot, cog, marathon, 0, 60)
    assert len(carrying(bot)) == 1
    return marathon


async def test_a_restart_between_the_ping_and_the_next_tick_never_pings_again(bot, cog):
    marathon = await pinged_day(bot, cog)
    again = Marathons(bot)
    again.client, again.clock = cog.client, cog.clock
    bot.cogs[cogmod.COG_NAME] = again

    await through(bot, again, marathon, 60, 61, 120, 165, 225)

    assert len(carrying(bot)) == 1
    assert len(await pings_of(bot, marathon)) == 1


async def test_a_claim_left_by_a_crash_before_the_send_closes_the_day(bot, cog):
    marathon = await event_marathon(bot, cog, day_of_runs(*[SKY_RUNS] * 4))
    await at(bot, cog, marathon, 0)
    runs = await runs_of(bot.db, marathon["id"])
    found = event.reading_for(bot, GUILD, marathon, runs)
    claim = baf.record_for(found.days[0], runs[0], 120, NOW)
    await update_marathon(bot.db, marathon["id"], baf_event_pings=baf.dump_pings([claim]))

    await through(bot, cog, marathon, 60, 165, 225)

    assert carrying(bot) == []
    posted = await rows(bot, "marathon.public_reminded")
    assert {one["marathon_role_reason"] for one in posted} == {mrp.BAF_EVENT_PINGED}


@pytest.mark.parametrize("on_move", ["edit", "repost"])
@pytest.mark.parametrize("moved_to", [230, 170], ids=["later", "earlier"])
async def test_the_first_run_re_timed_after_the_ping_never_pings_again(
    bot, cog, on_move, moved_to
):
    await bot.store.set(GUILD, "marathon_reminder_on_move", on_move)
    marathon = await pinged_day(bot, cog)
    (first,) = carrying(bot)
    cog.client.runs_given = [
        a_run(1, moved_to, game="Game 1", people=SKY_RUNS),
        *day_of_runs(*[SKY_RUNS] * 3, first=moved_to + 60, ident=2),
    ]

    await cog.refresh(bot.guild, await fresh(bot, marathon))
    await through(bot, cog, marathon, 61, 110, 155, 215, 275)

    assert carrying(bot) == [first]
    assert first.content.startswith(f"<@&{MARATHON_ROLE}> ")
    assert len(await pings_of(bot, marathon)) == 1
    later = [one for one in await rows(bot, "marathon.public_reminded") if one != {}][1:]
    assert all(one.get("marathon_role") is None for one in later)


async def test_the_first_run_dropped_after_the_ping_leaves_the_day_pinged(bot, cog):
    marathon = await pinged_day(bot, cog)
    cog.client.runs_given = day_of_runs(*[SKY_RUNS] * 3, first=240, ident=2)

    await cog.refresh(bot.guild, await fresh(bot, marathon))
    await through(bot, cog, marathon, 61, 120, 225, 285)

    assert len(carrying(bot)) == 1
    posted = await rows(bot, "marathon.public_reminded")
    assert [one.get("marathon_role") for one in posted[1:]] == [None] * (len(posted) - 1)
    assert {one["marathon_role_reason"] for one in posted[1:] if one["mark"] == 15} == {
        mrp.BAF_EVENT_PINGED
    }


async def test_a_flip_to_no_after_the_ping_brings_no_second_ping_that_day(bot, cog):
    marathon = await pinged_day(bot, cog)

    await event.set_baf_event(bot, bot.guild, FakeActor(), marathon, False)
    await through(bot, cog, marathon, 120, 165, 225, 285, 345)

    assert len(carrying(bot)) == 1
    fifteens = [
        one for one in await rows(bot, "marathon.public_reminded") if one["mark"] == 15
    ]
    assert len(fifteens) == 4
    assert {one["marathon_role_reason"] for one in fifteens} == {mrp.BAF_EVENT_PINGED}


async def test_a_flip_to_no_before_any_ping_goes_back_to_one_ping_a_run(bot, cog):
    marathon = await event_marathon(bot, cog, day_of_runs(*[SKY_RUNS] * 2))
    await at(bot, cog, marathon, 0)
    await event.set_baf_event(bot, bot.guild, FakeActor(), marathon, False)

    await through(bot, cog, marathon, 60, 120, 165, 225)

    posted = await rows(bot, "marathon.public_reminded")
    assert [(one["game"], one["mark"], one.get("marathon_role")) for one in posted] == [
        ("Game 1", 120, None),
        ("Game 2", 120, None),
        ("Game 1", 15, MARATHON_ROLE),
        ("Game 2", 15, MARATHON_ROLE),
    ]


async def test_a_two_day_event_pings_once_each_day(bot, cog):
    marathon = await event_marathon(
        bot,
        cog,
        [
            *day_of_runs(*[SKY_RUNS] * 2),
            *day_of_runs(*[SKY_RUNS] * 2, first=180 + DAY, ident=3),
        ],
    )

    await through(
        bot, cog, marathon, 0, 60, 120, 165, 180, 225, 240, 300, 360, 400,
        DAY + 60, DAY + 120, DAY + 165, DAY + 225,
    )  # fmt: skip

    posted = await rows(bot, "marathon.public_reminded")
    carried = [(one["game"], one["mark"]) for one in posted if one.get("marathon_role")]
    assert carried == [("Game 1", 120), ("Game 3", 120)]
    assert [one["game"] for one in await pings_of(bot, marathon)] == ["Game 1", "Game 3"]
    assert len(carrying(bot)) == 2


async def test_a_first_run_already_live_hands_the_ping_to_the_next_runs_next_heads_up(bot, cog):
    marathon = await event_marathon(bot, cog, day_of_runs(SKY_RUNS, OTHER, OTHER, SKY_RUNS))
    await through(bot, cog, marathon, 0, 60, 165, 181)
    assert len(carrying(bot)) == 1
    await update_marathon(bot.db, marathon["id"], baf_event_pings=None)

    await event.set_baf_event(bot, bot.guild, FakeActor(), marathon, True)
    await through(bot, cog, marathon, 200, 240, 345)

    posted = await rows(bot, "marathon.public_reminded")
    assert [(one["game"], one["mark"], one.get("marathon_role")) for one in posted][-2:] == [
        ("Game 4", 120, MARATHON_ROLE),
        ("Game 4", 15, None),
    ]


async def test_nothing_left_that_day_pings_nobody_and_one_row_says_so(bot, cog):
    marathon = await event_marathon(bot, cog, day_of_runs(SKY_RUNS, OTHER, OTHER))
    await through(bot, cog, marathon, 0, 60, 165, 181)
    before = len(carrying(bot))
    await update_marathon(bot.db, marathon["id"], baf_event_pings=None)

    await event.set_baf_event(bot, bot.guild, FakeActor(), marathon, True)
    await through(bot, cog, marathon, 200, 201, 240)

    assert len(carrying(bot)) == before
    (logged,) = await rows(bot, "marathon.baf_event_no_ping")
    assert logged["because"] == baf.MARKS_SPENT and logged["reason"] == baf.BY_STAFF
    said = role_ping.status_line(
        bot, bot.guild, await fresh(bot, marathon), rows=await runs_of(bot.db, marathon["id"])
    )
    assert "Every heads-up of that day's BaF runs has gone" in said
    assert logged["name"] == "SS4C" and logged["runs"] == 3


# --- the gates still gate it ---------------------------------------------------------------------


async def test_the_ping_switch_off_pings_nobody_and_the_row_says_why(bot, cog):
    marathon = await event_marathon(bot, cog, day_of_runs(*[SKY_RUNS] * 3), ping=False)

    await through(bot, cog, marathon, 0, 60, 120, 165, 180, 225)

    assert carrying(bot) == []
    posted = await rows(bot, "marathon.public_reminded")
    assert len(posted) == 5
    marked = [one for one in posted if "marathon_role_reason" in one]
    assert marked and {one["marathon_role_reason"] for one in marked} == {mrp.SWITCH_OFF}
    assert await pings_of(bot, marathon) == []
    assert "marathon.baf_event_no_ping" not in await kinds(bot.db)


async def test_marathon_role_pings_off_pings_nobody_and_the_line_says_which_key(bot, cog):
    marathon = await event_marathon(bot, cog, day_of_runs(*[SKY_RUNS] * 3))
    await bot.store.set(GUILD, "marathon_role_pings", False)

    await through(bot, cog, marathon, 0, 60, 165)

    assert carrying(bot) == []
    posted = await rows(bot, "marathon.public_reminded")
    assert posted[0]["marathon_role_reason"] == mrp.ROLE_PINGS_OFF
    assert await pings_of(bot, marathon) == []
    said = role_ping.status_line(
        bot, bot.guild, await fresh(bot, marathon), rows=await runs_of(bot.db, marathon["id"])
    )
    assert "marathon_role_pings is off" in said and "a BaF event" in said


async def test_a_ping_mark_staff_removed_falls_back_and_the_line_says_so(bot, cog):
    await bot.store.set(GUILD, "marathon_reminder_minutes", "1440, 60, 15")
    marathon = await event_marathon(bot, cog, day_of_runs(*[SKY_RUNS] * 3))

    await at(bot, cog, marathon, 0)
    said = role_ping.status_line(
        bot, bot.guild, await fresh(bot, marathon), rows=await runs_of(bot.db, marathon["id"])
    )
    await through(bot, cog, marathon, 120, 165)

    assert "on the heads-up 60 minutes before **Game 1**" in said
    assert "marathon_baf_event_ping_minutes is 120, which is not one of" in said
    posted = await rows(bot, "marathon.public_reminded")
    assert [(one["mark"], one.get("marathon_role")) for one in posted[:1]] == [(60, MARATHON_ROLE)]
    assert len(carrying(bot)) == 1


# --- what staff read -----------------------------------------------------------------------------


async def test_the_line_says_which_heads_up_carries_it_and_then_which_one_did(bot, cog):
    marathon = await event_marathon(bot, cog, day_of_runs(*[SKY_RUNS] * 4))
    await at(bot, cog, marathon, 0)
    runs = await runs_of(bot.db, marathon["id"])

    before = role_ping.status_line(bot, bot.guild, await fresh(bot, marathon), rows=runs)
    await at(bot, cog, marathon, 60)
    after = role_ping.status_line(
        bot, bot.guild, await fresh(bot, marathon), rows=await runs_of(bot.db, marathon["id"])
    )

    assert "a BaF event — all 4 runs have a BaF runner." in before
    assert f"<@&{MARATHON_ROLE}> is mentioned once, on the heads-up 120 minutes before" in before
    assert "15 minutes before a BaF run" not in before
    assert f"<@&{MARATHON_ROLE}> was mentioned once, on the heads-up 120 minutes before" in after
    assert "**Game 1**" in after


async def test_the_thread_controls_carry_the_line_and_the_three_way_switch(bot, cog):
    marathon = await event_marathon(bot, cog, day_of_runs(*[SKY_RUNS] * 4))
    await cog.tick_once()
    message = next(
        one
        for one in the_thread(bot).messages
        if one.id == (marathon["controls_message_id"])
    )

    def switch():
        view = next(
            (edit["view"] for edit in reversed(message.edits) if "view" in edit),
            message.kwargs.get("view"),
        )
        found = [getattr(one, "item", one) for one in view.children]
        return [
            (one.label, one.disabled)
            for one in found
            if ":baf:" in str(getattr(one, "custom_id", "") or "")
        ]

    assert "a BaF event — all 4 runs have a BaF runner." in message.content
    assert switch() == [
        ("BaF event: follow the schedule (a BaF event)", True),
        ("BaF event: yes", False),
        ("BaF event: no", False),
    ]

    said = await controls.press(bot, bot.guild, FakeActor(), marathon["id"], "baf", "no")

    assert said.ok and "is not a BaF event now" in said.message
    assert (await fresh(bot, marathon))["baf_event"] == 0
    assert "not a BaF event — the BaF event switch says so." in message.content
    assert switch() == [
        ("BaF event: follow the schedule (a BaF event)", False),
        ("BaF event: yes", False),
        ("BaF event: no", True),
    ]
    back = await controls.press(bot, bot.guild, FakeActor(), marathon["id"], "baf", "follow")
    assert back.ok and (await fresh(bot, marathon))["baf_event"] is None


# --- review fixes 2026-10-06 ---------------------------------------------------------------------


class Crash(BaseException):
    pass


async def press(bot, marathon, to, asked=None):
    button = await event.AskButton.from_custom_id(
        None, None, re.fullmatch(event.ASK_TEMPLATE, f"marathon:bafevent:{marathon['id']}:{to}")
    )
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    lead.message = asked or questions(bot)[0]
    await button.on_click(lead)
    return lead


async def line_of(bot, marathon):
    return role_ping.status_line(
        bot, bot.guild, await fresh(bot, marathon), rows=await runs_of(bot.db, marathon["id"])
    )


async def roles_posted(bot):
    posted = await rows(bot, "marathon.public_reminded")
    return [(one["game"], one["mark"], one.get("marathon_role")) for one in posted]


def day_stamp(minutes):
    return f"<t:{int((NOW + timedelta(minutes=minutes)).timestamp())}:D>"


STANDS = "the answer stands until the BaF event switch changes it."


async def test_leads_answering_yes_after_a_per_run_ping_brings_no_second_ping(bot, cog):
    marathon = await unsure(bot, cog)
    await through(bot, cog, marathon, 0, 60, 120, 165)
    assert len(carrying(bot)) == 1

    await press(bot, marathon, "yes")
    await through(bot, cog, marathon, 180, 225, 240, 345)

    assert await roles_posted(bot) == [
        ("Game 1", 120, None),
        ("Game 2", 120, None),
        ("Game 1", 15, MARATHON_ROLE),
        ("Game 2", 15, None),
        ("Game 4", 120, None),
        ("Game 4", 15, None),
    ]
    assert len(carrying(bot)) == 1
    said = await line_of(bot, marathon)
    assert f"<@&{MARATHON_ROLE}> was mentioned once, on the heads-up 15 minutes before" in said
    assert "**Game 1**" in said
    (stored,) = await pings_of(bot, marathon)
    assert (stored["per_run"], stored["sent"], stored["mark"]) == (True, True, 15)


async def test_yes_then_no_then_yes_around_a_per_run_ping_never_adds_a_ping(bot, cog):
    marathon = await unsure(bot, cog)
    await through(bot, cog, marathon, 0, 60, 120, 165)
    for to in ("yes", "no", "yes"):
        await press(bot, marathon, to)

    await through(bot, cog, marathon, 180, 225)

    assert len(carrying(bot)) == 1
    await press(bot, marathon, "no")
    await through(bot, cog, marathon, 240, 345)
    assert (await roles_posted(bot))[-1] == ("Game 4", 15, MARATHON_ROLE)
    await press(bot, marathon, "yes")
    assert "was mentioned once" in await line_of(bot, marathon)


MIXED_SAID = [([], 0), ([5001, MARATHON_ROLE], 2), ([], 0), ([5001, MARATHON_ROLE], 2)]
MIXED_ROWS = [
    (120, None, [], False),
    (15, MARATHON_ROLE, [5001, MARATHON_ROLE], True),
    (120, None, [], False),
    (15, MARATHON_ROLE, [5001, MARATHON_ROLE], True),
]
QUIET_FIELDS = [
    "channel_id",
    "game",
    "marathon_id",
    "mark",
    "member_id",
    "members",
    "message_id",
    "pinged",
    "public",
    "roles",
    "run_id",
    "scheduled_at",
    "via",
]
PINGED_FIELDS = sorted([*QUIET_FIELDS, "marathon_role", "marathon_role_reason"])
MIXED_FIELDS = [QUIET_FIELDS, PINGED_FIELDS, QUIET_FIELDS, PINGED_FIELDS]


def mixed_text(game, start, head=""):
    stamp = int((NOW + timedelta(minutes=start)).timestamp())
    return (
        f"{head}<@{SKY}> runs **{game}** (Any%) on **SS4C** <t:{stamp}:R> — <t:{stamp}:f>. "
        "https://twitch.tv/skyruns"
    )


MIXED_HEAD = f"<@&5001> <@&{MARATHON_ROLE}> "
MIXED_TEXT = [
    mixed_text("Game 1", 180),
    mixed_text("Game 1", 180, MIXED_HEAD),
    mixed_text("Game 4", 360),
    mixed_text("Game 4", 360, MIXED_HEAD),
]


@pytest.mark.parametrize("built", ["as_main", "branch"])
async def test_a_day_that_is_not_a_baf_event_posts_what_main_posts(bot, cog, monkeypatch, built):
    if built == "as_main":
        ping_mark = int(bot.store.get(GUILD, "marathon_ping_minutes"))

        async def per_run(cog, guild, marathon, row, mark):
            return (
                role_ping.verdict_for(cog.bot, guild, marathon) if mark == ping_mark else None,
                None,
            )

        async def nothing(*_given, **_named):
            return None

        monkeypatch.setattr(event, "heads_up_role", per_run)
        monkeypatch.setattr(event, "settle", nothing)
        monkeypatch.setattr(event, "sync", nothing)
    marathon = await event_marathon(bot, cog, day_of_runs(SKY_RUNS, OTHER, OTHER, SKY_RUNS))

    await through(bot, cog, marathon, 0, 60, 165, 181, 240, 345, 361)

    said = [(one.content, allowed(one)) for one in bot.guild.channels[CHANNEL].messages]
    logged = await rows(bot, "marathon.public_reminded")
    assert [(roles, text.count("<@&")) for text, roles in said] == MIXED_SAID
    assert [text for text, _roles in said] == MIXED_TEXT
    assert [sorted(one) for one in logged] == MIXED_FIELDS
    assert [
        (one["mark"], one.get("marathon_role"), one["roles"], one["pinged"]) for one in logged
    ] == MIXED_ROWS
    assert not any(":bafevent:" in str(one.kwargs) for one in the_thread(bot).messages)


async def two_day_marathon(bot, cog):
    return await asking(
        bot,
        cog,
        [
            *day_of_runs(SKY_RUNS, SKY_RUNS),
            *day_of_runs(SKY_RUNS, SKY_RUNS, SKY_RUNS, SKY_RUNS, OTHER, first=180 + DAY, ident=3),
        ],
    )


async def test_a_no_to_the_question_is_the_answer_for_every_day_of_the_event(bot, cog):
    marathon = await two_day_marathon(bot, cog)
    await through(bot, cog, marathon, 0, 1, 2)
    (asked,) = questions(bot)
    assert asked.content == (
        f"<@&{LEADS}> Is **SS4C** a BaF event? 6 of its 7 runs have a BaF runner."
    )

    lead = await press(bot, marathon, "no")
    await through(bot, cog, marathon, 60, 120, 165)

    assert lead.sent == "**SS4C** is not a BaF event now."
    assert (await fresh(bot, marathon))["baf_event"] is None
    switch, said = (await line_of(bot, marathon)).split("\n")
    assert "15 minutes before a BaF run" in switch
    assert said == (
        "**SS4C** is not a BaF event — staff answered the question in the thread "
        f"(6 of 7 runs have a BaF runner); {STANDS}"
    )
    assert (await roles_posted(bot))[:3] == [
        ("Game 1", 120, None),
        ("Game 2", 120, None),
        ("Game 1", 15, MARATHON_ROLE),
    ]
    assert asked.content.endswith(f"<@{FakeActor().id}> answered: not a BaF event.")
    logged = await details_of(bot.db, "marathon.baf_event_set")
    assert (logged["from"], logged["to"], logged["by"]) == ("follow", "no", "question")
    assert "day" not in logged
    (said,) = baf.asks_of(await fresh(bot, marathon))
    assert (said["event"], said["answer"], len(said["runs"])) == (True, "no", 7)


async def test_two_days_at_the_share_get_one_question_and_one_answer_between_them(bot, cog):
    marathon = await asking(
        bot,
        cog,
        [
            *day_of_runs(SKY_RUNS, SKY_RUNS, OTHER, SKY_RUNS),
            *day_of_runs(SKY_RUNS, SKY_RUNS, SKY_RUNS, OTHER, first=180 + DAY, ident=5),
        ],
    )

    await through(bot, cog, marathon, 0, 1, 2, 3)

    (asked,) = questions(bot)
    assert "6 of its 8 runs have a BaF runner" in asked.content
    waiting = await line_of(bot, marathon)
    assert "**SS4C** is not decided — 6 of 8 runs have a BaF runner, too few to be sure." in (
        waiting
    )
    assert "Staff were asked in the thread and have not answered." in waiting
    await press(bot, marathon, "yes")
    await through(bot, cog, marathon, 4, 5)
    assert len(questions(bot)) == 1
    event_line, today, tomorrow = (await line_of(bot, marathon)).split("\n")
    assert event_line.startswith("**SS4C** is a BaF event — staff answered the question")
    assert today.startswith(f"{day_stamp(180)}: <@&{MARATHON_ROLE}> is mentioned once")
    assert "**Game 1**" in today and "**Game 5**" in tomorrow
    assert tomorrow.startswith(f"{day_stamp(180 + DAY)}: <@&{MARATHON_ROLE}> is mentioned once")
    assert asked.content.endswith("answered: a BaF event.")


async def test_the_switch_beats_the_answer_and_follow_gives_it_back(bot, cog):
    marathon = await two_day_marathon(bot, cog)
    await at(bot, cog, marathon, 0)
    await press(bot, marathon, "yes")

    await controls.press(bot, bot.guild, FakeActor(), marathon["id"], "baf", "no")
    switched = (await line_of(bot, marathon)).split("\n")
    await controls.press(bot, bot.guild, FakeActor(), marathon["id"], "baf", "follow")
    followed = (await line_of(bot, marathon)).split("\n")

    assert switched[-1] == "**SS4C** is not a BaF event — the BaF event switch says so."
    assert "15 minutes before a BaF run" in switched[0] and len(switched) == 2
    assert followed[0].startswith("**SS4C** is a BaF event — staff answered the question")
    assert len(followed) == 3 and len(questions(bot)) == 1


async def test_the_answer_survives_the_event_being_re_timed_and_re_counted(bot, cog):
    marathon = await two_day_marathon(bot, cog)
    await at(bot, cog, marathon, 0)
    await press(bot, marathon, "yes")
    cog.client.runs_given = [
        *day_of_runs(SKY_RUNS, SKY_RUNS),
        *day_of_runs(SKY_RUNS, OTHER, OTHER, OTHER, OTHER, first=240 + DAY, ident=3),
    ]

    await cog.refresh(bot.guild, await fresh(bot, marathon))
    await through(bot, cog, marathon, 1, 2)

    assert len(questions(bot)) == 1
    assert (
        "**SS4C** is a BaF event — staff answered the question in the thread "
        f"(3 of 7 runs have a BaF runner); {STANDS}"
    ) in await line_of(bot, marathon)


async def test_a_no_stands_when_the_schedule_later_becomes_all_ours(bot, cog):
    marathon = await unsure(bot, cog)
    await at(bot, cog, marathon, 0)
    await press(bot, marathon, "no")
    cog.client.runs_given = day_of_runs(*[SKY_RUNS] * 4)

    await cog.refresh(bot.guild, await fresh(bot, marathon))
    await through(bot, cog, marathon, 1, 60, 165)

    assert len(questions(bot)) == 1
    assert (
        "**SS4C** is not a BaF event — staff answered the question in the thread "
        f"(4 of 4 runs have a BaF runner); {STANDS}"
    ) in await line_of(bot, marathon)
    assert await roles_posted(bot) == [("Game 1", 120, None), ("Game 1", 15, MARATHON_ROLE)]


# --- measured by the whole event 2026-10-06 ------------------------------------------------------


def event_runs(*shape):
    """One show-day per `(runs with a BaF runner, runs)`, a day apart."""
    found = []
    for index, (ours, runs) in enumerate(shape):
        found += day_of_runs(
            *[SKY_RUNS] * ours,
            *[OTHER] * (runs - ours),
            first=180 + index * DAY,
            ident=len(found) + 1,
        )
    return found


async def carried(bot):
    posted = await rows(bot, "marathon.public_reminded")
    return [(one["game"], one["mark"]) for one in posted if one.get("marathon_role")]


async def state_now(bot, marathon):
    return event.state_of(
        bot,
        bot.guild,
        await fresh(bot, marathon),
        await runs_of(bot.db, marathon["id"]),
        mention=True,
    )


async def test_twelve_of_fifteen_over_three_days_asks_once_about_the_event_then_pings_each_day(
    bot, cog
):
    marathon = await asking(bot, cog, event_runs((5, 5), (5, 5), (2, 5)))

    await through(bot, cog, marathon, 0, 1, 2, 3)

    (asked,) = questions(bot)
    assert asked.content == (
        f"<@&{LEADS}> Is **SS4C** a BaF event? 12 of its 15 runs have a BaF runner."
    )
    (logged,) = await rows(bot, "marathon.baf_event_asked")
    assert (logged["baf"], logged["runs"]) == (12, 15) and "day" not in logged
    assert await carried(bot) == []

    lead = await press(bot, marathon, "yes")
    await through(
        bot, cog, marathon, 60, 165, 225, DAY + 60, DAY + 165, 2 * DAY + 60, 2 * DAY + 165,
        2 * DAY + 225,
    )  # fmt: skip

    assert lead.sent == "**SS4C** is a BaF event now."
    assert await carried(bot) == [("Game 1", 120), ("Game 6", 120), ("Game 11", 120)]
    assert len(carrying(bot)) == 3 and len(questions(bot)) == 1
    (said,) = baf.asks_of(await fresh(bot, marathon))
    assert (said["event"], said["answer"], len(said["runs"])) == (True, "yes", 15)


async def test_fifteen_of_fifteen_over_three_days_asks_nothing_and_pings_once_a_day(bot, cog):
    marathon = await asking(bot, cog, event_runs((5, 5), (5, 5), (5, 5)))

    await through(
        bot, cog, marathon, 0, 60, 165, 225, DAY + 60, DAY + 165, 2 * DAY + 60, 2 * DAY + 165
    )

    assert questions(bot) == [] and "marathon.baf_event_asked" not in await kinds(bot.db)
    assert await carried(bot) == [("Game 1", 120), ("Game 6", 120), ("Game 11", 120)]
    found = await state_now(bot, marathon)
    assert (found["answer"], found["reason"], found["baf"], found["runs"]) == (
        "yes",
        "all_runs",
        15,
        15,
    )
    assert found["line"] == "**SS4C** is a BaF event — all 15 runs have a BaF runner."


OUTSIDE_ROWS = [
    ("Game 1", 120, None),
    ("Game 2", 120, None),
    ("Game 1", 15, MARATHON_ROLE),
    ("Game 3", 120, None),
    ("Game 2", 15, MARATHON_ROLE),
    ("Game 4", 120, None),
    ("Game 3", 15, MARATHON_ROLE),
    ("Game 5", 120, None),
    ("Game 4", 15, MARATHON_ROLE),
    ("Game 5", 15, MARATHON_ROLE),
]


@pytest.mark.parametrize("built", ["as_main", "branch"])
async def test_an_all_ours_day_of_an_event_that_is_not_baf_posts_what_a_mixed_day_posts(
    bot, cog, monkeypatch, built
):
    if built == "as_main":
        ping_mark = int(bot.store.get(GUILD, "marathon_ping_minutes"))

        async def per_run(cog, guild, marathon, row, mark):
            return (
                role_ping.verdict_for(cog.bot, guild, marathon) if mark == ping_mark else None,
                None,
            )

        async def nothing(*_given, **_named):
            return None

        monkeypatch.setattr(event, "heads_up_role", per_run)
        monkeypatch.setattr(event, "settle", nothing)
        monkeypatch.setattr(event, "sync", nothing)
    marathon = await asking(bot, cog, event_runs((5, 5), (0, 13), (1, 11)))

    await through(bot, cog, marathon, 0, 60, 120, 165, 180, 225, 240, 285, 300, 345, 405)

    said = [(one.content, allowed(one)) for one in bot.guild.channels[CHANNEL].messages]
    logged = await rows(bot, "marathon.public_reminded")
    assert [(one["game"], one["mark"], one.get("marathon_role")) for one in logged] == (
        OUTSIDE_ROWS
    )
    assert [(roles, text.count("<@&")) for text, roles in said] == [
        ([5001, MARATHON_ROLE], 2) if role else ([], 0) for _game, _mark, role in OUTSIDE_ROWS
    ]
    assert [sorted(one) for one in logged] == [
        PINGED_FIELDS if role else QUIET_FIELDS for _game, _mark, role in OUTSIDE_ROWS
    ]
    assert not any(":bafevent:" in str(one.kwargs) for one in the_thread(bot).messages)
    if built == "branch":
        found = await state_now(bot, marathon)
        assert (found["answer"], found["reason"], found["baf"], found["runs"]) == (
            "no",
            "mixed",
            6,
            29,
        )
        assert found["lines"] == ["**SS4C** is not a BaF event — 6 of 29 runs have a BaF runner."]
        assert [one["ping"] for one in found["days"]] == ["per_run"] * 3


async def test_a_day_of_a_baf_event_with_no_baf_run_gets_no_ping_and_its_line_says_so(bot, cog):
    marathon = await asking(bot, cog, event_runs((4, 4), (4, 4), (0, 2)))
    await at(bot, cog, marathon, 0)
    assert "8 of its 10 runs have a BaF runner" in questions(bot)[0].content
    await press(bot, marathon, "yes")

    found = await state_now(bot, marathon)
    await through(bot, cog, marathon, 60, DAY + 60, 2 * DAY + 60, 2 * DAY + 165, 2 * DAY + 170)

    assert [one["ping"] for one in found["days"]] == ["will", "will", "no_baf_run"]
    assert [(one["baf"], one["runs"]) for one in found["days"]] == [(4, 4), (4, 4), (0, 2)]
    assert found["lines"][0].startswith("**SS4C** is a BaF event — staff answered the question")
    assert found["lines"][3] == (
        f"{day_stamp(180 + 2 * DAY)}: No BaF run is on that day, so <@&{MARATHON_ROLE}> is not "
        "mentioned."
    )
    assert await carried(bot) == [("Game 1", 120), ("Game 5", 120)]
    assert "marathon.baf_event_no_baf_run" not in await kinds(bot.db)
    await through(bot, cog, marathon, 2 * DAY + 241, 2 * DAY + 242)
    (missed,) = await rows(bot, "marathon.baf_event_no_baf_run")
    assert "marathon.baf_event_no_ping" not in await kinds(bot.db)
    assert (missed["because"], missed["runs"]) == (baf.NO_BAF_RUN, 2)
    assert len(carrying(bot)) == 2


def old_day_answer(bot, said, **fields):
    return {
        "runs": [991, 992],
        "starts_at": (NOW - timedelta(days=2)).isoformat(),
        "ends_at": (NOW - timedelta(days=2, hours=-4)).isoformat(),
        "baf": 3,
        "asked_at": (NOW - timedelta(days=3)).isoformat(),
        "tries": 1,
        "message_id": 7700,
        "channel_id": the_thread(bot).id,
        "text": "Is Sat 2 Jan of **SS4C** a BaF event? 3 of that day's 4 runs have a BaF runner.",
    } | ({"answer": said, "answered_by": 5, "answered_at": NOW.isoformat()} if said else {}) | (
        fields
    )


async def test_a_per_day_answer_stored_before_is_the_events_answer_and_is_never_asked_again(
    bot, cog
):
    marathon = await unsure(bot, cog)
    old = old_day_answer(bot, "yes")
    await update_marathon(bot.db, marathon["id"], baf_event_ask=baf.dump_asks([old]))

    await through(bot, cog, marathon, 0, 1, 2, 60, 165)

    assert questions(bot) == [] and "marathon.baf_event_asked" not in await kinds(bot.db)
    assert baf.asks_of(await fresh(bot, marathon)) == [old]
    assert await carried(bot) == [("Game 1", 120)]
    found = await state_now(bot, marathon)
    assert (found["answer"], found["reason"], found["ask"]) == ("yes", "leads", "answered")
    assert found["line"].startswith("**SS4C** is a BaF event — staff answered the question")


async def test_per_day_answers_that_disagree_read_as_the_latest_one_given(bot, cog):
    marathon = await unsure(bot, cog)
    early = old_day_answer(bot, "yes", answered_at=(NOW - timedelta(hours=5)).isoformat())
    late = old_day_answer(bot, "no", message_id=7701, runs=[993])
    await update_marathon(bot.db, marathon["id"], baf_event_ask=baf.dump_asks([late, early]))

    await through(bot, cog, marathon, 0, 1, 60, 165)

    assert questions(bot) == []
    assert (await state_now(bot, marathon))["answer"] == "no"
    assert await carried(bot) == [("Game 1", 15)]
    assert len(baf.asks_of(await fresh(bot, marathon))) == 2


async def test_an_unanswered_per_day_question_is_kept_and_the_event_is_still_asked_once(bot, cog):
    marathon = await unsure(bot, cog)
    old = old_day_answer(bot, None)
    await update_marathon(bot.db, marathon["id"], baf_event_ask=baf.dump_asks([old]))

    await through(bot, cog, marathon, 0, 1, 2)

    (asked,) = questions(bot)
    kept, new = baf.asks_of(await fresh(bot, marathon))
    assert kept == old and (new["event"], new["message_id"]) == (True, asked.id)
    await press(bot, marathon, "yes", asked)
    assert (await state_now(bot, marathon))["answer"] == "yes"


async def test_a_marathon_with_no_schedule_yet_is_not_an_event_and_asks_and_logs_nothing(bot, cog):
    marathon = await asking(bot, cog, [])

    await through(bot, cog, marathon, 0, 1, 500)

    found = await state_now(bot, marathon)
    assert (found["answer"], found["reason"], found["days"]) == ("no", "no_runs", [])
    assert found["lines"] == ["**SS4C** is not a BaF event — no run is on the schedule."]
    assert questions(bot) == []
    logged = await kinds(bot.db)
    assert not [one for one in logged if "baf_event" in one]


async def stranded(bot, cog, posts):
    from black_bloc.cogs.content.marathon import update_run

    marathon = await event_marathon(bot, cog, day_of_runs(*[SKY_RUNS] * 4))
    await at(bot, cog, marathon, 0)
    runs = await runs_of(bot.db, marathon["id"])
    found = event.reading_for(bot, GUILD, marathon, runs)
    claim = baf.record_for(found.days[0], runs[0], 120, NOW)
    await update_marathon(bot.db, marathon["id"], baf_event_pings=baf.dump_pings([claim]))
    await update_run(
        bot.db,
        runs[0]["id"],
        reminders_sent=json.dumps([1440, 120]),
        reminder_posts=json.dumps(posts) if posts else None,
    )
    return marathon


async def test_a_claim_nothing_confirms_says_so_once_and_keeps_the_day_closed(bot, cog):
    from black_bloc import logkinds

    marathon = await stranded(bot, cog, None)

    await through(bot, cog, marathon, 60, 61, 62, 165, 225)

    assert carrying(bot) == []
    (logged,) = await rows(bot, "marathon.baf_event_ping_unconfirmed")
    assert (logged["game"], logged["mark"], logged["name"]) == ("Game 1", 120, "SS4C")
    said = await line_of(bot, marathon)
    assert "was mentioned once" not in said
    assert f"<@&{MARATHON_ROLE}> may have been mentioned on the heads-up 120 minutes" in said
    assert "the bot stopped before it could confirm it" in said
    assert "marathon.baf_event_ping_unconfirmed" in logkinds.IMPORTANT


async def test_a_claim_whose_heads_up_never_went_public_is_given_back(bot, cog):
    marathon = await stranded(bot, cog, {"120": {"posted": False}})

    await through(bot, cog, marathon, 60, 165, 225)

    assert (await roles_posted(bot))[0] == ("Game 1", 15, MARATHON_ROLE)
    assert len(carrying(bot)) == 1
    assert "marathon.baf_event_ping_unconfirmed" not in await kinds(bot.db)
    (stored,) = await pings_of(bot, marathon)
    assert (stored["mark"], stored["sent"]) == (15, True)


async def test_a_claim_whose_public_copy_carries_the_role_is_marked_sent(bot, cog):
    marathon = await pinged_day(bot, cog)
    (stored,) = await pings_of(bot, marathon)
    bare = {key: value for key, value in stored.items() if key not in ("sent", "message_id")}
    await update_marathon(bot.db, marathon["id"], baf_event_pings=baf.dump_pings([bare]))
    assert "may have been mentioned" in await line_of(bot, marathon)

    await at(bot, cog, marathon, 61)

    (again,) = await pings_of(bot, marathon)
    assert again["sent"] is True and again["message_id"] == carrying(bot)[0].id
    assert "was mentioned once" in await line_of(bot, marathon)
    assert "marathon.baf_event_ping_unconfirmed" not in await kinds(bot.db)


async def test_a_question_claimed_and_never_posted_is_asked_after_the_retry_gap(bot, cog):
    marathon = await unsure(bot, cog)
    the_thread(bot).send_raises = Crash()
    with pytest.raises(Crash):
        await at(bot, cog, marathon, 0)
    the_thread(bot).send_raises = None

    await through(bot, cog, marathon, 1, 5, 9)
    assert questions(bot) == []
    await through(bot, cog, marathon, 10, 11, 12)

    assert len(questions(bot)) == 1
    assert (await kinds(bot.db)).count("marathon.baf_event_asked") == 1


async def test_a_question_that_never_posts_backs_off_and_stops_after_three_tries(bot, cog):
    marathon = await unsure(bot, cog)
    the_thread(bot).send_raises = RuntimeError("Missing Access")

    await through(bot, cog, marathon, *range(0, 121, 5))

    failed = await rows(bot, "marathon.baf_event_ask_failed")
    assert [(one["try"], one["gave_up"]) for one in failed] == [(1, False), (2, False), (3, True)]
    said = await line_of(bot, marathon)
    assert "The question could not be posted in the thread" in said
    assert "answer with the BaF event switch" in said
    the_thread(bot).send_raises = None
    await through(bot, cog, marathon, 125, 130)
    assert questions(bot) == []

    cog.client.runs_given = day_of_runs(SKY_RUNS, SKY_RUNS, OTHER, SKY_RUNS, SKY_RUNS)
    await cog.refresh(bot.guild, await fresh(bot, marathon))
    await at(bot, cog, marathon, 131)

    assert len(questions(bot)) == 1


async def test_setting_the_switch_back_to_follow_lets_a_given_up_question_be_asked(bot, cog):
    marathon = await unsure(bot, cog)
    the_thread(bot).send_raises = RuntimeError("Missing Access")
    await through(bot, cog, marathon, *range(0, 61, 5))
    the_thread(bot).send_raises = None

    await controls.press(bot, bot.guild, FakeActor(), marathon["id"], "baf", "no")
    await controls.press(bot, bot.guild, FakeActor(), marathon["id"], "baf", "follow")
    await at(bot, cog, marathon, 62)

    assert len(questions(bot)) == 1


async def test_a_day_whose_runners_are_not_matched_yet_writes_no_missed_row(bot, cog):
    marathon = await event_marathon(
        bot, cog, day_of_runs(OTHER, OTHER, OTHER), name="Black in a Flash"
    )

    await through(bot, cog, marathon, 0, 61, 100, 170)

    assert "marathon.baf_event_no_ping" not in await kinds(bot.db)
    assert "No BaF run is on that day" in await line_of(bot, marathon)

    await through(bot, cog, marathon, 301)
    (logged,) = await rows(bot, "marathon.baf_event_no_baf_run")
    assert logged["because"] == baf.NO_BAF_RUN
    assert "marathon.baf_event_no_ping" not in await kinds(bot.db)


async def test_an_unsure_day_with_no_thread_to_ask_in_says_so(bot, cog):
    marathon = await unsure(bot, cog)
    thread = the_thread(bot)
    bot.guard = type("Guard", (), {"allows_channel": lambda self, found: found != thread.id})()

    await through(bot, cog, marathon, 0, 1)

    assert questions(bot) == []
    said = await line_of(bot, marathon)
    assert "staff have not answered" not in said
    assert "There is no thread to ask in, so answer with the BaF event switch." in said
    assert "marathon.baf_event_ask_failed" not in await kinds(bot.db)


async def test_leads_are_not_mentioned_when_the_marathon_role_could_not_be(bot, cog):
    marathon = await unsure(bot, cog)
    await update_marathon(bot.db, marathon["id"], ping_role=0)

    await at(bot, cog, marathon, 0)

    (asked,) = questions(bot)
    assert asked.content.startswith("Is **SS4C**")
    assert not asked.kwargs["allowed_mentions"].roles
    logged = await details_of(bot.db, "marathon.baf_event_asked")
    assert (logged["role"], logged["notifies"]) == (None, False)


@pytest.mark.parametrize("counted", [True, False], ids=["counted", "as_before"])
async def test_a_host_blocks_role_mention_counts_once_the_day_is_a_baf_event(
    bot, cog, monkeypatch, counted
):
    from tests.cogs.content import test_marathon_host_highlights as hosts

    if not counted:

        async def unchanged(cog, guild, marathon, found, rows):
            return found

        monkeypatch.setattr(event, "note_host_pings", unchanged)
    ours = (("anarchy", "an", "runner"),)
    marathon = await hosts.show(
        bot,
        cog,
        [
            hosts.HIDDEN_HEROES[0],
            a_run(2, 145, game="VHOLUME", people=ours, length=35),
            a_run(3, 180, game="SPRAWL zero", people=ours, length=50),
        ],
    )
    await hosts.role_pinging(bot, marathon)
    await hosts.walk(bot, cog, marathon, [0, 45, 46])
    mentioned = [one for one in hosts.posts(bot) if f"<@&{hosts.MARATHON_ROLE}>" in one.content]
    assert len(mentioned) == 1 and mentioned[0].content.count("hosts **") == 1

    await event.set_baf_event(bot, bot.guild, FakeActor(), marathon, True)
    await hosts.walk(bot, cog, marathon, [47, 60, 130, 145, 165, 180])

    again = [one for one in hosts.posts(bot) if f"<@&{hosts.MARATHON_ROLE}>" in one.content]
    assert len(again) == (1 if counted else 2)
    if counted:
        (stored,) = [one for one in await pings_of(bot, marathon) if one.get("host")]
        assert (stored["per_run"], stored["sent"], stored["mark"]) == (True, True, 15)
        assert stored["message_id"] == mentioned[0].id
async def test_words_staff_stored_for_the_per_day_question_fall_back_to_the_shipped_ones(bot, cog):
    marathon = await unsure(bot, cog)
    bot.store._cache[(GUILD, "marathon_baf_event_question")] = "Is {day} of {marathon} ours?"
    bot.store._cache[(GUILD, "marathon_baf_event_answer_line")] = "{day}: {answer} — {reason}."

    await at(bot, cog, marathon, 0)

    (asked,) = questions(bot)
    assert asked.content == (
        f"<@&{LEADS}> Is **SS4C** a BaF event? 3 of its 4 runs have a BaF runner."
    )
    assert "**SS4C** is not decided — 3 of 4 runs have a BaF runner" in await line_of(bot, marathon)


# --- review fixes (whole event) 2026-10-06 -------------------------------------------------------


def baf_buttons(bot, marathon):
    message = next(
        one for one in the_thread(bot).messages if one.id == marathon["controls_message_id"]
    )
    view = next(
        (edit["view"] for edit in reversed(message.edits) if "view" in edit),
        message.kwargs.get("view"),
    )
    found = [getattr(one, "item", one) for one in view.children]
    return [one for one in found if ":baf:" in str(getattr(one, "custom_id", "") or "")]


async def announced_then_unsure(bot, cog):
    """Fifteen of fifteen, day 1 pinged at two hours, then an outside run joins day 2."""
    marathon = await asking(bot, cog, event_runs((5, 5), (5, 5), (5, 5)))
    await through(bot, cog, marathon, 0, 60)
    assert await carried(bot) == [("Game 1", 120)]
    cog.client.runs_given = [
        *event_runs((5, 5), (5, 5), (5, 5)),
        a_run(16, 180 + DAY + 300, game="Game 16", people=OTHER),
    ]
    await cog.refresh(bot.guild, await fresh(bot, marathon))
    await through(bot, cog, marathon, 61, 62)
    return marathon


async def test_an_event_already_announced_as_baf_keeps_one_ping_a_day_while_leads_are_asked(
    bot, cog
):
    marathon = await announced_then_unsure(bot, cog)
    (asked,) = questions(bot)
    assert "15 of its 16 runs have a BaF runner" in asked.content

    await through(bot, cog, marathon, DAY + 60, DAY + 120, DAY + 165, DAY + 225)

    assert await carried(bot) == [("Game 1", 120), ("Game 6", 120)]
    assert len(carrying(bot)) == 2 and len(questions(bot)) == 1
    found = await state_now(bot, marathon)
    assert (found["answer"], found["reason"], found["ask"]) == ("yes", "acted", "pending")
    assert found["line"] == (
        "**SS4C** is a BaF event — 15 of 16 runs have a BaF runner now; it was a BaF event "
        "when a day's one mention went out, so it stays one until staff answer. Staff were "
        "asked in the thread and have not answered."
    )


async def test_a_no_after_the_days_ping_leaves_that_day_closed_and_later_days_per_run(bot, cog):
    marathon = await announced_then_unsure(bot, cog)
    await at(bot, cog, marathon, DAY + 60)
    assert await carried(bot) == [("Game 1", 120), ("Game 6", 120)]

    await press(bot, marathon, "no")
    await through(
        bot, cog, marathon, DAY + 120, DAY + 165, DAY + 225, 2 * DAY + 60, 2 * DAY + 165,
        2 * DAY + 225,
    )  # fmt: skip

    assert await carried(bot) == [
        ("Game 1", 120),
        ("Game 6", 120),
        ("Game 11", 15),
        ("Game 12", 15),
    ]
    assert (await state_now(bot, marathon))["reason"] == "leads"


async def test_an_announced_event_that_drops_under_the_ask_percent_reads_no_at_once(bot, cog):
    marathon = await asking(bot, cog, event_runs((5, 5), (5, 5), (5, 5)))
    await through(bot, cog, marathon, 0, 60)
    cog.client.runs_given = [
        *event_runs((5, 5), (5, 5), (5, 5)),
        *[
            a_run(16 + index, 180 + DAY + 300 + index * 60, game=f"Game {16 + index}", people=OTHER)
            for index in range(6)
        ],
    ]

    await cog.refresh(bot.guild, await fresh(bot, marathon))
    await through(bot, cog, marathon, 61, DAY + 60, DAY + 165)

    found = await state_now(bot, marathon)
    assert (found["answer"], found["reason"], found["baf"], found["runs"]) == (
        "no",
        "mixed",
        15,
        21,
    )
    assert questions(bot) == []
    assert await carried(bot) == [("Game 1", 120), ("Game 6", 15)]


async def test_the_follow_choice_says_what_following_gives_and_that_it_is_the_answer(bot, cog):
    marathon = await unsure(bot, cog)
    await at(bot, cog, marathon, 0)
    before = await state_now(bot, marathon)
    await press(bot, marathon, "yes")
    await controls.press(bot, bot.guild, FakeActor(), marathon["id"], "baf", "no")

    switched = await state_now(bot, marathon)
    label = baf_buttons(bot, marathon)[0].label
    await controls.press(bot, bot.guild, FakeActor(), marathon["id"], "baf", "follow")
    followed = await state_now(bot, marathon)

    assert (before["worked_out"]["answer"], before["worked_out"]["reason"]) == ("unsure", "share")
    assert (switched["answer"], switched["reason"]) == ("no", "staff")
    assert (switched["worked_out"]["answer"], switched["worked_out"]["reason"]) == ("yes", "leads")
    assert switched["worked_out"]["answer_word"] == "a BaF event"
    assert switched["worked_out"]["reason_word"].startswith("staff answered the question")
    assert label == "BaF event: follow the answer (a BaF event)"
    assert (followed["answer"], followed["reason"]) == (
        switched["worked_out"]["answer"],
        switched["worked_out"]["reason"],
    )
    assert followed["answer_word"] == switched["worked_out"]["answer_word"]


async def test_staff_clear_the_answer_from_the_thread_and_the_question_is_asked_once_more(
    bot, cog
):
    marathon = await unsure(bot, cog)
    await at(bot, cog, marathon, 0)
    (asked,) = questions(bot)
    assert [one.custom_id.rsplit(":", 1)[1] for one in baf_buttons(bot, marathon)] == [
        "follow",
        "yes",
        "no",
    ]
    await press(bot, marathon, "yes")
    shown = baf_buttons(bot, marathon)
    assert [(one.label, one.row, one.disabled) for one in shown] == [
        ("BaF event: follow the answer (a BaF event)", 4, True),
        ("BaF event: yes", 4, False),
        ("BaF event: no", 4, False),
        ("Clear the answer", 4, False),
    ]
    assert shown[-1].custom_id == f"marathon:controls:{marathon['id']}:baf:clear"

    said = await controls.press(bot, bot.guild, FakeActor(), marathon["id"], "baf", "clear")

    assert said.ok and said.message == "The answer was cleared, so **SS4C** is not decided now."
    (record,) = baf.asks_of(await fresh(bot, marathon))
    assert "answer" not in record and "answered_by" not in record
    assert (record["cleared"], record["cleared_by"]) == (True, FakeActor().id)
    logged = (await rows(bot, "marathon.baf_event_set"))[-1]
    assert (logged["from"], logged["to"], logged["by"], logged["cleared"], logged["via"]) == (
        "yes",
        "follow",
        "question",
        True,
        "discord",
    )
    assert asked.content.endswith(f"<@{FakeActor().id}> cleared the answer.")
    assert "answered:" not in asked.content
    assert [one.label for one in baf_buttons(bot, marathon)] == [
        "BaF event: follow the schedule (not decided)",
        "BaF event: yes",
        "BaF event: no",
    ]
    found = await state_now(bot, marathon)
    assert (found["answer"], found["reason"], found["ask"]) == ("unsure", "share", None)

    await through(bot, cog, marathon, 1, 2, 3)

    again = questions(bot)
    assert len(again) == 2 and again[0] is asked
    assert (await kinds(bot.db)).count("marathon.baf_event_asked") == 2
    old, new = baf.asks_of(await fresh(bot, marathon))
    assert old["cleared"] and (new["event"], new["message_id"]) == (True, again[1].id)
    assert (await state_now(bot, marathon))["ask"] == "pending"
    nothing = await controls.press(bot, bot.guild, FakeActor(), marathon["id"], "baf", "clear")
    assert nothing.ok and nothing.message == (
        "**SS4C** has no answer to clear, so nothing was changed."
    )
    assert (await kinds(bot.db)).count("marathon.baf_event_set") == 2


async def test_a_cleared_answer_gives_the_name_and_the_runs_back_the_say(bot, cog):
    marathon = await unsure(bot, cog)
    await at(bot, cog, marathon, 0)
    await press(bot, marathon, "no")
    cog.client.runs_given = day_of_runs(*[SKY_RUNS] * 4)
    await cog.refresh(bot.guild, await fresh(bot, marathon))
    await controls.press(bot, bot.guild, FakeActor(), marathon["id"], "baf", "yes")

    said = await event.clear_answer(bot, bot.guild, FakeActor(), await fresh(bot, marathon))
    await controls.press(bot, bot.guild, FakeActor(), marathon["id"], "baf", "follow")
    await through(bot, cog, marathon, 1, 2)

    assert said.message == "The answer was cleared, so **SS4C** is a BaF event now."
    found = await state_now(bot, marathon)
    assert (found["answer"], found["reason"]) == ("yes", "all_runs")
    assert len(questions(bot)) == 1


async def test_every_question_the_marathon_holds_says_the_one_answer_that_stands(bot, cog):
    marathon = await unsure(bot, cog)
    words = "Is Sat 2 Jan of **SS4C** a BaF event? 3 of that day's 4 runs have a BaF runner."
    earlier = await the_thread(bot).send(words)
    old = old_day_answer(bot, None, message_id=earlier.id, text=words)
    await update_marathon(bot.db, marathon["id"], baf_event_ask=baf.dump_asks([old]))
    await through(bot, cog, marathon, 0, 1)
    asked = questions(bot)[-1]
    assert asked is not earlier
    who = f"<@{FakeActor().id}>"

    await press(bot, marathon, "yes", asked)
    assert asked.content.endswith(f"{who} answered: a BaF event.")
    assert earlier.content == f"{words}\n{who} answered: a BaF event."

    await press(bot, marathon, "no", earlier)
    assert earlier.content == f"{words}\n{who} answered: not a BaF event."
    assert asked.content.endswith(f"{who} answered: not a BaF event.")
    assert asked.content.count("answered:") == 1

    await event.clear_answer(bot, bot.guild, FakeActor(), await fresh(bot, marathon))
    assert earlier.content == f"{words}\n{who} cleared the answer."
    assert asked.content.endswith(f"{who} cleared the answer.")


async def test_a_question_message_that_is_gone_does_not_stop_the_others_being_edited(bot, cog):
    marathon = await unsure(bot, cog)
    gone = old_day_answer(bot, None)
    await update_marathon(bot.db, marathon["id"], baf_event_ask=baf.dump_asks([gone]))
    await through(bot, cog, marathon, 0, 1)
    (asked,) = questions(bot)
    assert [one.get("message_id") for one in baf.asks_of(await fresh(bot, marathon))] == [
        7700,
        asked.id,
    ]

    await press(bot, marathon, "yes", asked)

    assert asked.content.endswith("answered: a BaF event.")


async def test_a_day_with_no_baf_run_is_a_routine_row_written_once_even_after_the_day_is_over(
    bot, cog
):
    from black_bloc import logkinds

    marathon = await event_marathon(
        bot, cog, day_of_runs(OTHER, OTHER, OTHER), name="Black in a Flash"
    )
    await at(bot, cog, marathon, 0)
    await bot.db.conn.execute(
        "UPDATE marathon_runs SET state = 'done' WHERE marathon_id = ?", (marathon["id"],)
    )
    await bot.db.conn.commit()
    cog.clock = lambda: NOW + timedelta(minutes=900)

    for _tick in range(3):
        await event.sync(cog, bot.guild, await fresh(bot, marathon), cog.clock())

    (logged,) = await rows(bot, "marathon.baf_event_no_baf_run")
    assert (logged["because"], logged["runs"], logged["reason"]) == (baf.NO_BAF_RUN, 3, "name")
    assert "marathon.baf_event_no_ping" not in await kinds(bot.db)
    assert not logkinds.is_important("marathon.baf_event_no_baf_run")
    assert "marathon.baf_event_no_baf_run" in logkinds.ROUTINE
    assert logkinds.is_important("marathon.baf_event_no_ping")


async def test_a_value_stored_under_a_re_worded_keys_old_name_is_not_read(bot, cog):
    from black_bloc import settings_store

    stale = {
        "marathon_baf_event_reason_leads": "staff answered for this day",
        "marathon_baf_event_ask_text": "Is that day ours?",
        "marathon_baf_event_line": "That day is {answer} — {reason}.",
        "marathon_baf_event_ping_no_run": "No BaF run is left that day.",
    }
    for key, value in stale.items():
        await bot.db.conn.execute(
            "INSERT OR REPLACE INTO settings (guild_id, key, value, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (GUILD, key, json.dumps(value), NOW.isoformat()),
        )
    await bot.db.conn.commit()
    await bot.store.load()
    await bot.store.set(GUILD, "marathon_reminder_minutes", "1440, 120, 15")
    marathon = await unsure(bot, cog)

    await at(bot, cog, marathon, 0)
    (asked,) = questions(bot)
    await press(bot, marathon, "yes")

    assert asked.content.startswith(
        f"<@&{LEADS}> Is **SS4C** a BaF event? 3 of its 4 runs have a BaF runner."
    )
    assert (await line_of(bot, marathon)).split("\n")[-2] == (
        "**SS4C** is a BaF event — staff answered the question in the thread "
        f"(3 of 4 runs have a BaF runner); {STANDS}"
    )
    assert not set(stale) & set(settings_store.KEY_TYPES)
