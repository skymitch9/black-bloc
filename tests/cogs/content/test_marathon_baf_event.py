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
        f"<@&{LEADS}> Is <t:{int((NOW + timedelta(minutes=180)).timestamp())}:D> of **SS4C** "
        "a BaF event? 3 of that day's 4 runs have a BaF runner."
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
    assert asked.content.startswith("Is <t:") and "of **SS4C** a BaF event?" in asked.content
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
    assert asked.content.startswith(f"<@&{LEADS}> Is <t:")
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
        ("BaF event: follow the schedule", True),
        ("BaF event: yes", False),
        ("BaF event: no", False),
    ]

    said = await controls.press(bot, bot.guild, FakeActor(), marathon["id"], "baf", "no")

    assert said.ok and "is not a BaF event now" in said.message
    assert (await fresh(bot, marathon))["baf_event"] == 0
    assert "not a BaF event — the BaF event switch says so." in message.content
    assert switch() == [
        ("BaF event: follow the schedule", False),
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
    role = FakeRole(LEADS, "Leads")
    role.mentionable = True
    bot.guild.roles.append(role)
    await bot.store.set(GUILD, "marathon_baf_event_ask_role_id", LEADS)
    return await event_marathon(
        bot,
        cog,
        [
            *day_of_runs(SKY_RUNS, SKY_RUNS),
            *day_of_runs(SKY_RUNS, SKY_RUNS, SKY_RUNS, SKY_RUNS, OTHER, first=180 + DAY, ident=3),
        ],
    )


async def test_a_no_for_one_day_leaves_every_other_day_alone(bot, cog):
    marathon = await two_day_marathon(bot, cog)
    await at(bot, cog, marathon, 0)
    (asked,) = questions(bot)
    assert asked.content == (
        f"<@&{LEADS}> Is {day_stamp(180 + DAY)} of **SS4C** a BaF event? "
        "4 of that day's 5 runs have a BaF runner."
    )

    lead = await press(bot, marathon, "no")
    await through(bot, cog, marathon, 60, 120, 165)

    assert lead.sent == f"{day_stamp(180 + DAY)} of **SS4C** is not a BaF event now."
    assert (await fresh(bot, marathon))["baf_event"] is None
    one, two = (await line_of(bot, marathon)).split("\n")[-2:]
    assert "a BaF event — all 2 runs have a BaF runner." in one
    assert "not a BaF event — staff answered for this day." in two
    assert (await roles_posted(bot))[0] == ("Game 1", 120, MARATHON_ROLE)
    assert len(carrying(bot)) == 1
    assert asked.content.endswith(f"<@{FakeActor().id}> answered: not a BaF event.")
    logged = await details_of(bot.db, "marathon.baf_event_set")
    assert (logged["from"], logged["to"], logged["by"]) == ("follow", "no", "question")
    assert logged["day"] == (NOW + timedelta(minutes=180 + DAY)).isoformat()
    (said,) = baf.asks_of(await fresh(bot, marathon))
    assert said["answer"] == "no" and len(said["runs"]) == 5


async def test_each_unsure_day_gets_its_own_question_once_and_its_own_answer(bot, cog):
    marathon = await unsure(bot, cog)
    cog.client.runs_given = [
        *day_of_runs(SKY_RUNS, SKY_RUNS, OTHER, SKY_RUNS),
        *day_of_runs(SKY_RUNS, SKY_RUNS, SKY_RUNS, OTHER, first=180 + DAY, ident=5),
    ]
    await cog.refresh(bot.guild, await fresh(bot, marathon))

    await through(bot, cog, marathon, 0, 1, 2, 3)

    first, second = questions(bot)
    assert day_stamp(180) in first.content and day_stamp(180 + DAY) in second.content
    await press(bot, marathon, "yes", second)
    await through(bot, cog, marathon, 4, 5)
    assert len(questions(bot)) == 2
    today, tomorrow = (await line_of(bot, marathon)).split("\n")[-2:]
    assert "not decided — 3 of 4 runs have a BaF runner" in today
    assert "Staff were asked in the thread and have not answered." in today
    assert "a BaF event — staff answered for this day." in tomorrow
    assert second.content.endswith("answered: a BaF event.")
    assert "answered" not in first.content


async def test_the_switch_beats_a_days_answer_and_follow_gives_it_back(bot, cog):
    marathon = await two_day_marathon(bot, cog)
    await at(bot, cog, marathon, 0)
    await press(bot, marathon, "yes")

    await controls.press(bot, bot.guild, FakeActor(), marathon["id"], "baf", "no")
    switched = (await line_of(bot, marathon)).split("\n")
    await controls.press(bot, bot.guild, FakeActor(), marathon["id"], "baf", "follow")
    followed = (await line_of(bot, marathon)).split("\n")

    assert [one for one in switched if "the BaF event switch says so" in one] == switched[-2:]
    assert "all 2 runs have a BaF runner" in followed[-2]
    assert "a BaF event — staff answered for this day." in followed[-1]
    assert len(questions(bot)) == 1


async def test_a_days_answer_survives_the_day_being_re_timed(bot, cog):
    marathon = await two_day_marathon(bot, cog)
    await at(bot, cog, marathon, 0)
    await press(bot, marathon, "yes")
    cog.client.runs_given = [
        *day_of_runs(SKY_RUNS, SKY_RUNS),
        *day_of_runs(SKY_RUNS, SKY_RUNS, SKY_RUNS, SKY_RUNS, OTHER, first=240 + DAY, ident=3),
    ]

    await cog.refresh(bot.guild, await fresh(bot, marathon))
    await through(bot, cog, marathon, 1, 2)

    assert len(questions(bot)) == 1
    assert "a BaF event — staff answered for this day." in await line_of(bot, marathon)


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
    assert "No BaF run is left that day" in await line_of(bot, marathon)

    await through(bot, cog, marathon, 301)
    (logged,) = await rows(bot, "marathon.baf_event_no_ping")
    assert logged["because"] == baf.NO_BAF_RUN


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
    assert asked.content.startswith("Is <t:") and not asked.kwargs["allowed_mentions"].roles
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
