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
    assert await pings_of(bot, marathon) == [] and questions(bot) == []


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
    assert await pings_of(bot, marathon) == []
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


async def unsure(bot, cog):
    role = FakeRole(LEADS, "Leads")
    role.mentionable = True
    bot.guild.roles.append(role)
    await bot.store.set(GUILD, "marathon_baf_event_ask_role_id", LEADS)
    return await event_marathon(bot, cog, day_of_runs(SKY_RUNS, SKY_RUNS, OTHER, SKY_RUNS))


async def test_a_day_at_the_share_asks_leads_once_in_the_thread_and_really_mentions_them(
    bot, cog
):
    marathon = await unsure(bot, cog)

    await through(bot, cog, marathon, 0, 1, 2)
    await cog.tick_once()

    (asked,) = questions(bot)
    assert asked.content == (
        f"<@&{LEADS}> Is **SS4C** a BaF event? 3 of the 4 runs on "
        f"<t:{int((NOW + timedelta(minutes=180)).timestamp())}:D> have a BaF runner."
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
    assert baf.ask_of(await fresh(bot, marathon))["message_id"] == asked.id


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
    assert await pings_of(bot, marathon) == []


async def test_yes_inside_the_last_two_hours_pings_once_at_the_next_heads_up(bot, cog):
    marathon = await unsure(bot, cog)
    await through(bot, cog, marathon, 0, 60)
    (asked,) = questions(bot)
    button = await event.AskButton.from_custom_id(
        None, None, re.fullmatch(event.ASK_TEMPLATE, f"marathon:bafevent:{marathon['id']}:yes")
    )
    lead = FakeInteraction(bot, FakeActor(), bot.guild)

    await button.on_click(lead)
    await through(bot, cog, marathon, 120, 165, 225, 240, 345)

    assert "is a BaF event now" in lead.sent
    assert (await fresh(bot, marathon))["baf_event"] == 1
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
    assert (await fresh(bot, marathon))["baf_event"] is None
    assert "marathon.baf_event_set" not in await kinds(bot.db)

    bot.store.is_staff = lambda member: True
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    await button.on_click(lead)

    assert "is not a BaF event now" in lead.sent
    assert (await fresh(bot, marathon))["baf_event"] == 0
    assert questions(bot)[0].content.endswith("answered: not a BaF event.")


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
    assert logged["because"] == "no_heads_up_left" and logged["reason"] == baf.BY_STAFF
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
        ("BaF event: follow the schedule", True),
        ("BaF event: yes", False),
        ("BaF event: no", False),
    ]

    said = await controls.press(bot, bot.guild, FakeActor(), marathon["id"], "baf", "no")

    assert said.ok and "is not a BaF event now" in said.message
    assert (await fresh(bot, marathon))["baf_event"] == 0
    assert "not a BaF event — staff said so." in message.content
    assert switch() == [
        ("BaF event: follow the schedule", False),
        ("BaF event: yes", False),
        ("BaF event: no", True),
    ]
    back = await controls.press(bot, bot.guild, FakeActor(), marathon["id"], "baf", "follow")
    assert back.ok and (await fresh(bot, marathon))["baf_event"] is None
