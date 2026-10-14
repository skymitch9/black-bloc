# ruff: noqa: F401, F811
from datetime import timedelta

import discord
import pytest

from black_bloc import logkinds
from black_bloc.cogs.content import marathon_inbox as inbox
from black_bloc.cogs.content.marathon import (
    create_marathon,
    get_marathon,
    set_active,
    update_marathon,
)
from black_bloc.cogs.content.marathon_untracked_alert import alert_if_due
from tests.cogs.content.test_marathon import (
    NOW,
    URL,
    FakeClient,
    a_run,
    at,
    bot,
    cog,
    inbox_messages,
    inbox_thread,
    threading,
)
from tests.cogs.content.test_spotlight import (
    GUILD,
    SHADOW_CHANNEL,
    FakeActor,
    FakeRole,
    details_of,
    kinds,
)

EVENTS = 555
AUNTIES = 1073711363337236601
HOST = 9002
KIND = "marathon.untracked_alert"
HOURS = "marathon_untracked_alert_hours"
ROLE = "marathon_untracked_alert_role_id"
SKY_RUN = ("Sky", "skyruns", "runner")
HOST_PART = ("anarchy", "anarchyasf", "host")
NOBODY = ("Somebody", None, "runner")


def schedule(hours, *people):
    start = int(hours * 60)
    return [
        a_run(1, start, people=people or (NOBODY,)),
        a_run(2, start + 60, game="Celeste"),
    ]


@pytest.fixture(autouse=True)
async def room(bot):
    threading(bot, EVENTS)
    await bot.store.set(GUILD, "events_announce_channel_id", EVENTS)
    await bot.store.set(GUILD, ROLE, AUNTIES)
    bot.guild.roles.append(FakeRole(AUNTIES, "Aunties / Uncles"))
    await bot.db.conn.execute(
        "INSERT INTO golive_links(user_id, twitch_login, linked_at) VALUES (?, ?, ?)",
        (HOST, "anarchyasf", at(-9999)),
    )
    await bot.db.conn.commit()


async def found(bot, cog, runs):
    cog.client = FakeClient(runs=runs)
    made = await create_marathon(bot, bot.guild, FakeActor(), name="AGDQ 2027", url=URL)
    assert made.ok, made.message
    return made.value


async def fresh(bot, marathon):
    return await get_marathon(bot.db, GUILD, marathon["id"])


def alerts(bot, channel_id=EVENTS):
    thread = inbox_thread(bot, channel_id)
    return [one for one in thread.messages if not one.embeds][1:] if thread else []


async def tick_at(cog, hours):
    cog.clock = lambda: NOW + timedelta(hours=hours)
    await cog.tick_once()


async def test_an_untracked_marathon_with_a_baf_runner_36_hours_out_is_flagged_once(bot, cog):
    marathon = await found(bot, cog, schedule(30, SKY_RUN))
    await cog.tick_once()

    said = alerts(bot)
    assert len(said) == 1
    message = said[0]
    assert message.content.startswith(f"<@&{AUNTIES}> **AGDQ 2027** starts <t:")
    assert message.content.endswith("and is not tracked. 1 BaF on it.")
    reply = message.kwargs["reference"]
    assert reply.message_id == inbox_messages(bot, EVENTS)[0].id
    assert reply.channel_id == inbox_thread(bot, EVENTS).id
    mentions = message.kwargs["allowed_mentions"]
    assert [one.id for one in mentions.roles] == [AUNTIES]
    assert mentions.everyone is False and mentions.users is False
    assert (await fresh(bot, marathon))["untracked_alert_at"] == NOW.isoformat()
    details = await details_of(bot.db, KIND)
    assert details == details | {
        "marathon_id": marathon["id"],
        "name": "AGDQ 2027",
        "hours_left": 30.0,
        "baf_runners": 1,
        "baf_hosts": 0,
        "outcome": "posted",
        "reply": True,
        "role_id": str(AUNTIES),
        "shadow": False,
    }
    assert logkinds.is_important(KIND) and logkinds.feature_of(KIND) == "marathon"

    await tick_at(cog, 1)
    await tick_at(cog, 2)
    assert len(alerts(bot)) == 1 and (await kinds(bot.db)).count(KIND) == 1


async def test_it_waits_until_36_hours_before_the_start(bot, cog):
    marathon = await found(bot, cog, schedule(40, SKY_RUN))
    await cog.tick_once()
    await tick_at(cog, 3.9)
    assert alerts(bot) == [] and (await fresh(bot, marathon))["untracked_alert_at"] is None

    await tick_at(cog, 4)
    assert len(alerts(bot)) == 1
    assert (await details_of(bot.db, KIND))["hours_left"] == 36.0


async def test_the_hours_key_moves_the_line(bot, cog):
    await bot.store.set(GUILD, HOURS, 48)
    await found(bot, cog, schedule(40, SKY_RUN))
    await cog.tick_once()
    assert len(alerts(bot)) == 1


async def test_zero_hours_never_flags(bot, cog):
    await bot.store.set(GUILD, HOURS, 0)
    marathon = await found(bot, cog, schedule(1, SKY_RUN))
    await cog.tick_once()
    assert alerts(bot) == [] and KIND not in await kinds(bot.db)
    assert (await fresh(bot, marathon))["untracked_alert_at"] is None


async def test_a_baf_host_alone_is_enough(bot, cog):
    await found(bot, cog, schedule(10, NOBODY, HOST_PART))
    await cog.tick_once()
    assert len(alerts(bot)) == 1
    assert alerts(bot)[0].content.endswith("1 BaF on it.")
    details = await details_of(bot.db, KIND)
    assert (details["baf_runners"], details["baf_hosts"]) == (0, 1)


async def test_no_baf_on_it_means_no_alert(bot, cog):
    marathon = await found(bot, cog, schedule(10))
    await cog.tick_once()
    assert alerts(bot) == [] and KIND not in await kinds(bot.db)
    assert (await fresh(bot, marathon))["untracked_alert_at"] is None


async def test_tracked_ignored_paused_or_started_marathons_are_never_flagged(bot, cog):
    marathon = await found(bot, cog, schedule(10, SKY_RUN))
    await inbox.track(bot, bot.guild, FakeActor(), marathon)
    await cog.tick_once()
    await inbox.untrack(bot, bot.guild, FakeActor(), await fresh(bot, marathon))
    await inbox.ignore(bot, bot.guild, FakeActor(), await fresh(bot, marathon), True)
    await cog.tick_once()
    assert KIND not in await kinds(bot.db)

    await update_marathon(bot.db, marathon["id"], ignored_at=None, ignored_by=None)
    await set_active(bot, bot.guild, FakeActor(), await fresh(bot, marathon), False)
    await cog.tick_once()
    assert KIND not in await kinds(bot.db)

    await update_marathon(bot.db, marathon["id"], active=1)
    await tick_at(cog, 10.5)
    assert KIND not in await kinds(bot.db)
    assert (await fresh(bot, marathon))["untracked_alert_at"] is None


async def test_found_late_is_flagged_on_the_first_tick(bot, cog):
    await found(bot, cog, schedule(0.5, SKY_RUN))
    await cog.tick_once()
    assert len(alerts(bot)) == 1
    assert (await details_of(bot.db, KIND))["hours_left"] == 0.5


async def test_no_role_waits_unstamped_and_says_so_once_then_posts_when_one_is_set(bot, cog):
    await bot.store.clear(GUILD, ROLE)
    marathon = await found(bot, cog, schedule(10, SKY_RUN))
    await cog.tick_once()
    await tick_at(cog, 0.1)
    assert alerts(bot) == [] and (await fresh(bot, marathon))["untracked_alert_at"] is None
    assert (await kinds(bot.db)).count(KIND) == 1
    skipped = await details_of(bot.db, KIND)
    assert skipped["outcome"] == "skipped" and "marathon_untracked_alert_role_id" in skipped["reason"]

    await bot.store.set(GUILD, ROLE, 4242)
    await tick_at(cog, 0.2)
    assert (await kinds(bot.db)).count(KIND) == 2
    assert (await details_of(bot.db, KIND))["reason"] == "the role is not on the server"

    await bot.store.set(GUILD, ROLE, AUNTIES)
    await tick_at(cog, 0.3)
    assert len(alerts(bot)) == 1
    assert (await details_of(bot.db, KIND))["outcome"] == "posted"


async def test_a_send_that_fails_is_stamped_logged_as_failed_and_never_retried(bot, cog):
    marathon = await found(bot, cog, schedule(10, SKY_RUN))
    inbox_thread(bot, EVENTS).send_raises = RuntimeError("discord is down")
    await cog.tick_once()
    assert (await fresh(bot, marathon))["untracked_alert_at"] == NOW.isoformat()
    failed = await details_of(bot.db, KIND)
    assert failed["outcome"] == "failed" and "discord is down" in failed["reason"]

    inbox_thread(bot, EVENTS).send_raises = None
    await tick_at(cog, 1)
    assert alerts(bot) == [] and (await kinds(bot.db)).count(KIND) == 1


async def test_with_no_inbox_message_it_posts_in_the_thread_without_a_reply(bot, cog):
    marathon = await found(bot, cog, schedule(10, SKY_RUN))
    await update_marathon(bot.db, marathon["id"], inbox_message_id=None, inbox_home=None)
    async with cog.lock(marathon["id"]):
        assert await alert_if_due(cog, bot.guild, await fresh(bot, marathon)) is True
    said = alerts(bot)
    assert len(said) == 1 and "reference" not in said[0].kwargs
    assert (await details_of(bot.db, KIND))["reply"] is False


async def test_an_archived_inbox_thread_is_reopened_for_the_alert(bot, cog):
    await found(bot, cog, schedule(10, SKY_RUN))
    thread = inbox_thread(bot, EVENTS)
    thread.archived = True
    await cog.tick_once()
    assert thread.archived is False and len(alerts(bot)) == 1


async def test_shadow_posts_in_the_rehearsal_inbox_and_pings_nobody(bot, cog):
    await bot.store.set(GUILD, "marathon_mode", "shadow")
    await found(bot, cog, schedule(10, SKY_RUN))
    await cog.tick_once()
    said = alerts(bot, SHADOW_CHANNEL)
    assert len(said) == 1 and f"<#{EVENTS}>" in said[0].content
    assert said[0].kwargs["allowed_mentions"].roles is False
    details = await details_of(bot.db, KIND)
    assert details["shadow"] is True and details["shadow_home"] == SHADOW_CHANNEL


async def test_the_words_are_the_template_key(bot, cog):
    await bot.store.set(
        GUILD, "marathon_untracked_alert_template", "{role} {name}: {runners}r {hosts}h {hours}"
    )
    await found(bot, cog, schedule(10, SKY_RUN, HOST_PART))
    await cog.tick_once()
    assert alerts(bot)[0].content == f"<@&{AUNTIES}> AGDQ 2027: 1r 1h 10.0"
