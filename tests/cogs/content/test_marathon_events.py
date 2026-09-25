import json

import discord
import pytest

from black_bloc import marathon as mt
from black_bloc.cogs.content import marathon as cogmod
from black_bloc.cogs.content import marathon_events as runev
from black_bloc.cogs.content import marathon_feeds as feeds
from black_bloc.cogs.content.marathon import (
    create_marathon,
    get_marathon,
    pair_runner,
    remove_marathon,
    runs_of,
    shout_now,
    unpair_runner,
)
from black_bloc.events import get_event, set_status
from tests.cogs.content.test_marathon import (  # noqa: F401
    NOW,
    SCHEDULE,
    STAFF_ROOM,
    URL,
    a_run,
    at,
    bot,
    cog,
    gdq_row,
    posts,
    proposals,
)
from tests.cogs.content.test_spotlight import (
    GUILD,
    SHADOW_CHANNEL,
    FakeActor,
    FakeChannel,
    details_of,
    kinds,
)

FORUM = 5555


@pytest.fixture(autouse=True)
async def quiet_calendar(bot):  # noqa: F811
    await bot.store.set(GUILD, "events_create_scheduled", False)
    bot.guild.name = "Black and Friends"


async def made(bot, mode=None, url=URL, **given):  # noqa: F811
    outcome = await create_marathon(
        bot, bot.guild, FakeActor(), name="AGDQ 2027", url=url, event_mode=mode, **given
    )
    assert outcome.ok, outcome.message
    return outcome.value


async def runs(bot, marathon):  # noqa: F811
    return {row["game"]: row for row in await runs_of(bot.db, marathon["id"])}


async def rows_of(bot, kind):  # noqa: F811
    cur = await bot.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id", (kind,)
    )
    return [json.loads(row["details"]) for row in await cur.fetchall()]


async def test_the_default_makes_no_event_of_either_kind(bot, cog, proposals):  # noqa: F811
    marathon = await made(bot)

    assert marathon["event_mode"] == "none" and marathon["event_id"] is None
    assert all(row["event_id"] is None for row in await runs_of(bot.db, marathon["id"]))
    assert proposals == [] and "marathon.run_event_made" not in await kinds(bot.db)


async def test_runs_mode_makes_one_approved_event_per_run_of_ours_ahead(
    bot, cog, proposals  # noqa: F811
):
    channel = await gdq_row(bot)
    marathon = await made(bot, "runs", spotlight_id=channel["id"])
    rows = await runs(bot, marathon)

    metroid = rows["Super Metroid"]
    assert metroid["event_id"] and proposals == []
    others = [row for game, row in rows.items() if game != "Super Metroid"]
    assert all(row["event_id"] is None for row in others)
    event = await get_event(bot.db, metroid["event_id"])
    assert event["status"] == "approved" and event["review_channel_id"] is None
    assert event["title"] == "Sky runs Super Metroid at AGDQ 2027"
    assert event["description"] == "Any% · AGDQ 2027 · read from the schedule; times follow it."
    assert event["location"] == "https://twitch.tv/gamesdonequick"
    assert event["starts_at"] == at(30) and event["ends_at"] == at(90)
    made_row = await details_of(bot.db, "marathon.run_event_made")
    assert made_row["reviewed"] is False and made_row["event_id"] == event["id"]
    assert (await details_of(bot.db, "event.created"))["because"] == "marathon_run"
    assert (await get_marathon(bot.db, GUILD, marathon["id"]))["event_id"] is None


async def test_with_no_channel_a_run_event_is_where_its_runner_streams(
    bot, cog, proposals  # noqa: F811
):
    marathon = await made(bot, "runs")
    metroid = (await runs(bot, marathon))["Super Metroid"]
    assert (await get_event(bot.db, metroid["event_id"]))["location"] == (
        "https://twitch.tv/skyruns"
    )


async def test_the_review_key_and_shadow_both_send_run_events_through_the_review(
    bot, cog, proposals  # noqa: F811
):
    await bot.store.set(GUILD, "marathon_run_events_reviewed", True)
    await made(bot, "runs")
    assert len(proposals) == 1
    assert (await details_of(bot.db, "marathon.run_event_made"))["reviewed"] is True

    await bot.store.set(GUILD, "marathon_run_events_reviewed", False)
    await bot.store.set(GUILD, "marathon_mode", "shadow")
    await made(bot, "runs", url="https://gamesdonequick.com/schedule/75")
    assert len(proposals) == 2


async def test_both_makes_the_marathon_event_and_the_run_events(bot, cog, proposals):  # noqa: F811
    marathon = await made(bot, "both")
    fresh = await get_marathon(bot.db, GUILD, marathon["id"])
    assert fresh["event_id"] and len(proposals) == 1
    assert (await runs(bot, marathon))["Super Metroid"]["event_id"]


async def test_a_pairing_makes_a_run_ours_and_its_event_and_unpairing_calls_it_off(
    bot, cog, proposals  # noqa: F811
):
    marathon = await made(bot, "runs")
    kirby = (await runs(bot, marathon))["Kirby Air Riders"]
    assert kirby["event_id"] is None

    await pair_runner(bot, bot.guild, FakeActor(), marathon, "Somebody", 777)
    kirby = (await runs(bot, marathon))["Kirby Air Riders"]
    assert kirby["event_id"]
    event_id = kirby["event_id"]

    pairing = (await cogmod.pairings_of(bot.db, GUILD))[0]
    await unpair_runner(bot, bot.guild, FakeActor(), marathon, pairing)

    assert (await runs(bot, marathon))["Kirby Air Riders"]["event_id"] is None
    assert (await get_event(bot.db, event_id))["status"] == "cancelled"
    cancelled = [one for one in await rows_of(bot, "marathon.run_event_cancelled")]
    assert {one["reason"] for one in cancelled} == {"not_ours"}


async def test_a_moved_run_re_dates_its_event_and_a_dropped_one_calls_it_off(
    bot, cog, proposals  # noqa: F811
):
    marathon = await made(bot, "runs")
    event_id = (await runs(bot, marathon))["Super Metroid"]["event_id"]

    cog.client.runs_given = [
        *SCHEDULE[:2],
        a_run(3, 70, game="Super Metroid", people=(("Sky", "skyruns", "runner"),)),
        *SCHEDULE[3:],
    ]
    await cog.refresh(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    event = await get_event(bot.db, event_id)
    assert event["starts_at"] == at(70) and event["ends_at"] == at(130)
    redated = await details_of(bot.db, "marathon.run_event_redated")
    assert redated["from"]["starts_at"] == at(30) and redated["to"]["starts_at"] == at(70)

    cog.client.runs_given = [one for one in SCHEDULE if one.game != "Super Metroid"]
    await cog.refresh(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert (await get_event(bot.db, event_id))["status"] == "cancelled"
    assert (await details_of(bot.db, "marathon.run_event_cancelled"))["reason"] == "run_dropped"


async def test_removing_the_marathon_calls_its_run_events_off(bot, cog, proposals):  # noqa: F811
    marathon = await made(bot, "runs")
    event_id = (await runs(bot, marathon))["Super Metroid"]["event_id"]
    await remove_marathon(bot, bot.guild, FakeActor(), marathon)
    assert (await get_event(bot.db, event_id))["status"] == "cancelled"
    assert (await details_of(bot.db, "marathon.run_event_cancelled"))["reason"] == (
        "marathon_removed"
    )


async def test_a_mode_change_makes_at_once_and_leaving_calls_off_or_keeps(
    bot, cog, proposals  # noqa: F811
):
    marathon = await made(bot)
    done = await runev.set_event_mode(bot, bot.guild, FakeActor(), marathon, "runs")
    assert done.ok and "1 run event(s) made" in done.message
    set_row = await details_of(bot.db, "marathon.event_mode_set")
    assert set_row["from"] == "none" and set_row["to"] == "runs" and set_row["made"] == 1
    event_id = (await runs(bot, marathon))["Super Metroid"]["event_id"]

    left = await runev.set_event_mode(bot, bot.guild, FakeActor(), marathon, "none")
    assert "1 run event(s) called off" in left.message
    assert (await get_event(bot.db, event_id))["status"] == "cancelled"
    assert (await details_of(bot.db, "marathon.run_event_cancelled"))["reason"] == "mode_changed"

    await bot.store.set(GUILD, "marathon_run_event_cancel_on_leave", False)
    await runev.set_event_mode(bot, bot.guild, FakeActor(), marathon, "runs")
    kept_id = (await runs(bot, marathon))["Super Metroid"]["event_id"]
    kept = await runev.set_event_mode(bot, bot.guild, FakeActor(), marathon, "none")
    assert "left on the calendar" in kept.message
    assert (await get_event(bot.db, kept_id))["status"] == "approved"
    assert (await runs(bot, marathon))["Super Metroid"]["event_id"] is None


async def test_a_mode_that_is_not_a_mode_is_refused_and_the_same_mode_changes_nothing(
    bot, cog, proposals  # noqa: F811
):
    marathon = await made(bot)
    refused = await runev.set_event_mode(bot, bot.guild, FakeActor(), marathon, "sometimes")
    assert not refused.ok and refused.status == 422 and "none, marathon, runs or both" in (
        refused.message
    )
    same = await runev.set_event_mode(bot, bot.guild, FakeActor(), marathon, "none")
    assert same.ok and "nothing was changed" in same.message
    assert "marathon.event_mode_set" not in await kinds(bot.db)


async def test_leaving_the_marathon_mode_calls_the_marathon_event_off(
    bot, cog, proposals  # noqa: F811
):
    marathon = await made(bot, "marathon")
    event_id = (await get_marathon(bot.db, GUILD, marathon["id"]))["event_id"]
    await runev.set_event_mode(bot, bot.guild, FakeActor(), marathon, "runs")
    fresh = await get_marathon(bot.db, GUILD, marathon["id"])
    assert fresh["event_id"] is None and fresh["event_mode"] == "runs"
    assert (await get_event(bot.db, event_id))["status"] == "cancelled"
    assert (await details_of(bot.db, "marathon.event_cancelled"))["reason"] == "mode_changed"


async def test_an_unlinked_run_is_never_given_an_event_again_on_its_own(
    bot, cog, proposals  # noqa: F811
):
    marathon = await made(bot, "runs")
    metroid = (await runs(bot, marathon))["Super Metroid"]
    event_id = metroid["event_id"]

    done = await runev.unlink_run_event(bot, bot.guild, FakeActor(), marathon, metroid)
    assert done.ok and f"#{event_id}" in done.message
    assert (await get_event(bot.db, event_id))["status"] == "approved"
    await cog.refresh(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert (await runs(bot, marathon))["Super Metroid"]["event_id"] == 0
    again = await runev.unlink_run_event(bot, bot.guild, FakeActor(), marathon, metroid)
    assert not again.ok and again.code == "no_run_event"

    remade = await runev.make_run_event_now(bot, bot.guild, FakeActor(), marathon, metroid)
    assert remade.ok and (await runs(bot, marathon))["Super Metroid"]["event_id"] not in (
        0,
        None,
        event_id,
    )
    twice = await runev.make_run_event_now(bot, bot.guild, FakeActor(), marathon, metroid)
    assert not twice.ok and twice.code == "run_event_exists"


async def test_make_it_now_refuses_a_run_that_is_not_ours(bot, cog, proposals):  # noqa: F811
    marathon = await made(bot)
    celeste = (await runs(bot, marathon))["Celeste"]
    refused = await runev.make_run_event_now(bot, bot.guild, FakeActor(), marathon, celeste)
    assert not refused.ok and refused.code == "not_ours"


async def test_a_run_with_an_approved_event_gets_no_shoutout_unless_the_key_or_staff_say(
    bot, cog, proposals  # noqa: F811
):
    await bot.store.set(GUILD, "marathon_channel_id", 900)
    bot.guild.channels[900] = FakeChannel(900)
    marathon = await made(bot, "runs")
    metroid = (await runs(bot, marathon))["Super Metroid"]

    said = await cog.shout(bot.guild, marathon, metroid)
    assert said is None and posts(bot, 900) == []
    skipped = await details_of(bot.db, "marathon.shout_skipped")
    assert skipped["because"] == "run_event" and skipped["event_id"] == metroid["event_id"]

    await bot.store.set(GUILD, "marathon_shout_when_run_has_event", True)
    await cog.shout(bot.guild, marathon, metroid)
    assert len(posts(bot, 900)) == 1

    await bot.store.set(GUILD, "marathon_shout_when_run_has_event", False)
    await set_status(bot.db, metroid["event_id"], "cancelled")
    await cog.shout(bot.guild, marathon, metroid)
    assert len(posts(bot, 900)) == 2


async def test_shout_it_now_posts_even_when_the_run_has_its_event(bot, cog, proposals):  # noqa: F811
    await bot.store.set(GUILD, "marathon_channel_id", 900)
    bot.guild.channels[900] = FakeChannel(900)
    marathon = await made(bot, "runs")
    metroid = (await runs(bot, marathon))["Super Metroid"]
    done = await shout_now(bot, bot.guild, FakeActor(), marathon, metroid)
    shouts = [one for one in posts(bot, 900) if "right now" in str(one.content)]
    assert done.ok and len(shouts) == 1


async def test_the_card_carries_the_mode_select_and_the_run_view_its_event(
    bot, cog, proposals  # noqa: F811
):
    marathon = await made(bot, "runs")
    embed, view = await cogmod.build_card(bot, bot.guild, marathon["id"])
    pick = next(one for one in view.children if isinstance(one, cogmod.EventModePick))
    assert [one.value for one in pick.options if one.default] == ["runs"]
    assert "Event mode: **one event per BaF run" in embed.description
    metroid = (await runs(bot, marathon))["Super Metroid"]
    embed, run_view = await cogmod.build_run(bot, bot.guild, marathon["id"], metroid["id"])
    assert f"event **#{metroid['event_id']}** — approved" in embed.description
    labels = [getattr(one, "label", None) for one in run_view.children]
    assert "Unlink" in labels and "Make it now" not in labels


async def test_the_add_modal_takes_a_mode_word(bot, cog, proposals):  # noqa: F811
    from tests.cogs.content.test_spotlight import FakeInteraction

    modal = cogmod.AddMarathonModal(None, "none")
    modal.name._value = "AGDQ 2027"
    modal.url._value = URL
    modal.login._value = ""
    modal.event._value = "Runs"
    await modal.on_submit(FakeInteraction(bot, FakeActor(), bot.guild))
    rows = await cogmod.list_marathons(bot.db, GUILD)
    assert rows[0]["event_mode"] == "runs"


async def test_the_events_card_line_names_a_run_event_s_run(bot, cog, proposals):  # noqa: F811
    marathon = await made(bot, "runs")
    event_id = (await runs(bot, marathon))["Super Metroid"]["event_id"]
    line = await cogmod.marathon_of_event_line(bot, GUILD, event_id)
    assert line == mt.RUN_OF_EVENT.format(game="Super Metroid", name="AGDQ 2027")


async def test_a_feeds_own_mode_wins_over_the_setting_for_what_it_adds(
    bot, cog, proposals  # noqa: F811
):
    channel = await gdq_row(bot)
    feed_id = await feeds.insert_feed(
        bot.db,
        GUILD,
        source="tracker",
        feed_ref="https://tracker.gamesdonequick.com/tracker",
        spotlight_id=channel["id"],
        name="GDQ",
        action="add",
        added_by=None,
    )
    feed = await feeds.get_feed(bot.db, GUILD, feed_id)
    set_done = await feeds.set_feed(bot, bot.guild, FakeActor(), feed, event_mode="runs")
    assert set_done.ok and "one event per BaF run" in set_done.message
    bad = await feeds.set_feed(bot, bot.guild, FakeActor(), feed, event_mode="often")
    assert not bad.ok and bad.status == 422

    made_one = await create_marathon(
        bot, bot.guild, None, name="AGDQ 2027", url=URL, feed_id=feed_id, spotlight_id=None
    )
    assert made_one.value["event_mode"] == "runs"

    back = await feeds.set_feed(
        bot, bot.guild, FakeActor(), await feeds.get_feed(bot.db, GUILD, feed_id), event_mode=""
    )
    assert back.ok and (await feeds.get_feed(bot.db, GUILD, feed_id))["event_mode"] is None


# --- the staff notice's home (design §D) ------------------------------------------------------


class Tag:
    def __init__(self, tag_id, name):
        self.id = tag_id
        self.name = name


class Post(FakeChannel):
    pass


class Forum:
    def __init__(self, channel_id, guild):
        self.id = channel_id
        self.guild = guild
        self.available_tags = [Tag(1, "pending")]
        self.posts = []
        self.edits = []

    async def edit(self, **kwargs):
        self.edits.append(kwargs)
        self.available_tags = [
            Tag(getattr(one, "id", None) or 99, one.name) for one in kwargs["available_tags"]
        ]

    async def create_thread(self, name, **kwargs):
        post = Post(7000 + len(self.posts))
        message = await post.send(kwargs.get("content"), view=kwargs.get("view"))
        post.name = name
        post.applied_tags = kwargs.get("applied_tags")
        self.posts.append(post)
        self.guild.channels[post.id] = post

        class Made:
            pass

        made = Made()
        made.thread = post
        made.message = message
        return made


async def forum_mode(bot):  # noqa: F811
    forum = Forum(FORUM, bot.guild)
    bot.guild.channels[FORUM] = forum
    bot.guild.channels[STAFF_ROOM] = FakeChannel(STAFF_ROOM)
    await bot.store.set(GUILD, "staff_channel_id", STAFF_ROOM)
    await bot.store.set(GUILD, "events_review_mode", "forum")
    await bot.store.set(GUILD, "events_forum_channel_id", FORUM)
    return forum


async def test_in_forum_mode_the_notice_is_a_tagged_post_in_the_events_forum(
    bot, cog  # noqa: F811
):
    forum = await forum_mode(bot)
    message, channel_id, why = await cog._send_staff(
        bot.guild, "GDQ has a new event", None, title="SGDQ 2027", what={"notice": "feed"}
    )

    assert why is None and len(forum.posts) == 1 and channel_id == forum.posts[0].id
    post = forum.posts[0]
    assert post.name == "New marathon: SGDQ 2027"
    assert [tag.name for tag in post.applied_tags] == ["marathon"]
    assert posts(bot, STAFF_ROOM) == []
    posted = await details_of(bot.db, "marathon.notice_posted")
    assert posted["home"] == "events" and posted["notice"] == "feed"

    await cog._send_staff(bot.guild, "again", None, title="AGDQ 2028")
    assert len(forum.edits) == 1


async def test_room_mode_and_the_staff_key_keep_the_notice_in_the_staff_channel(
    bot, cog  # noqa: F811
):
    forum = await forum_mode(bot)
    await bot.store.set(GUILD, "marathon_notice_home", "staff")
    await cog._send_staff(bot.guild, "one", None, title="X")
    await bot.store.set(GUILD, "marathon_notice_home", "events")
    await bot.store.set(GUILD, "events_review_mode", "room")
    await cog._send_staff(bot.guild, "two", None, title="Y")

    assert forum.posts == [] and len(posts(bot, STAFF_ROOM)) == 2
    assert {one["home"] for one in await rows_of(bot, "marathon.notice_posted")} == {"staff"}


async def test_shadow_still_rehearses_the_notice_in_the_shadow_home(bot, cog):  # noqa: F811
    forum = await forum_mode(bot)
    await bot.store.set(GUILD, "marathon_mode", "shadow")
    await cog._send_staff(bot.guild, "rehearsed", None, title="X")
    assert forum.posts == [] and len(posts(bot, SHADOW_CHANNEL)) == 1
    assert (await details_of(bot.db, "marathon.notice_posted"))["home"] == "shadow"


async def test_a_forum_that_will_not_take_the_post_falls_back_to_the_staff_channel(
    bot, cog  # noqa: F811
):
    forum = await forum_mode(bot)

    async def refuses(name, **kwargs):
        raise discord.HTTPException(type("R", (), {"status": 403, "reason": "no"})(), "no")

    forum.create_thread = refuses
    message, channel_id, why = await cog._send_staff(bot.guild, "text", None, title="X")
    assert why is None and channel_id == STAFF_ROOM
    assert (await details_of(bot.db, "marathon.notice_forum_failed"))["fallback"] == "staff"
    assert NOW

