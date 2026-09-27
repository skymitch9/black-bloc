# ruff: noqa: F401, F811
import asyncio
import json
import re
from datetime import timedelta

import discord
import pytest

from black_bloc import marathon_inbox as mi
from black_bloc.cogs.content import marathon_feeds as feeds
from black_bloc.cogs.content import marathon_inbox as inbox
from black_bloc.cogs.content.marathon import (
    Marathons,
    create_marathon,
    get_marathon,
    post_board,
    refresh_marathon,
    runs_of,
)
from black_bloc.cogs.content.marathon_archive import archive_marathon, restore_marathon
from black_bloc.cogs.content.spotlight import windows_for
from black_bloc.marathon_sources import ScheduleError
from tests.cogs.content.test_marathon import (
    NOW,
    SCHEDULE,
    SKY,
    URL,
    Member,
    bot,
    cog,
    gdq_row,
    inbox_messages,
    threading,
)
from tests.cogs.content.test_spotlight import (
    CHANNEL,
    GUILD,
    LOG_CHANNEL,
    SHADOW_CHANNEL,
    FakeActor,
    FakeInteraction,
    details_of,
    kinds,
)

EVENTS = 555
THREADS = 556


@pytest.fixture(autouse=True)
async def events_room(bot):
    """The inbox lives in the events channel; Track makes threads beside it (owner D2)."""
    threading(bot, EVENTS)
    await bot.store.set(GUILD, "events_announce_channel_id", EVENTS)
    await bot.store.set(GUILD, "marathon_track_makes_thread", True)
    return bot.guild.channels[EVENTS]


async def found(bot, cog, *, channel=None):
    made = await create_marathon(
        bot,
        bot.guild,
        FakeActor(),
        name="AGDQ 2027",
        url=URL,
        spotlight_id=channel["id"] if channel is not None else None,
    )
    assert made.ok, made.message
    return made.value


async def fresh(bot, marathon):
    return await get_marathon(bot.db, GUILD, marathon["id"])


def room(bot, channel_id=EVENTS):
    return bot.guild.channels[channel_id]


def the_inbox(bot, channel_id=EVENTS):
    return room(bot, channel_id).threads[0]


def fields_of(message):
    return {field.name: field.value for field in message.embeds[0].fields}


def labels_of(view):
    return [getattr(child, "item", child).label for child in view.children]


def marathon_thread(bot, channel_id=EVENTS):
    return room(bot, channel_id).threads[1]


async def logged(bot, kind):
    cur = await bot.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id", (kind,)
    )
    return [json.loads(row["details"]) for row in await cur.fetchall()]


# --- the inbox --------------------------------------------------------------------------------


async def test_a_new_marathon_gets_one_inbox_message_in_the_events_inbox_thread(
    bot,
    cog,
):
    marathon = await found(bot, cog, channel=await gdq_row(bot))

    thread = the_inbox(bot)
    assert thread.name == "Marathons — found and tracked" and len(room(bot).threads) == 1
    assert thread.kwargs["auto_archive_duration"] == mi.AUTO_ARCHIVE_MINUTES
    assert thread.messages[0].content.startswith("Every marathon Black Bloc finds")
    messages = inbox_messages(bot, EVENTS)
    assert len(messages) == 1 and (await fresh(bot, marathon))["inbox_message_id"] == messages[0].id
    message = messages[0]
    assert message.embeds[0].title == "AGDQ 2027"
    fields = fields_of(message)
    assert list(fields) == ["When", "Source", "Channel", "Schedule", "Event", "State"]
    assert fields["Schedule"] == "5 runs · 1 BaF"
    assert "twitch.tv/gamesdonequick" in fields["Channel"]
    assert fields["State"].startswith("Found <t:") and fields["State"].endswith("not tracked")
    assert labels_of(message.kwargs["view"])[:2] == ["Track", "Ignore"]
    assert message.kwargs["allowed_mentions"].users is False
    assert (await details_of(bot.db, "marathon.inbox_made"))["channel_id"] == EVENTS
    assert (await details_of(bot.db, "marathon.inbox_posted"))["state"] == "found"


async def test_an_untracked_marathon_reads_matches_and_sets_its_window_but_posts_nothing(
    bot,
    cog,
):
    await bot.store.set(GUILD, "marathon_ping_role_default", True)
    channel = await gdq_row(bot)
    marathon = await found(bot, cog, channel=channel)
    await cog.follow(bot.guild, await fresh(bot, marathon))
    await cog.tick_once()

    rows = {row["game"]: row for row in await runs_of(bot.db, marathon["id"])}
    assert rows["Super Metroid"]["people"] and SKY in [
        one.get("user_id") for one in json.loads(rows["Super Metroid"]["people"])
    ]
    assert await windows_for(bot.db, channel["id"])
    assert room(bot, CHANNEL).messages == [] and len(room(bot).threads) == 1
    assert (await fresh(bot, marathon))["board_message_id"] is None
    found_kinds = await kinds(bot.db)
    assert "marathon.board_posted" not in found_kinds and "marathon.reminded" not in found_kinds
    assert "marathon.board_failed" not in found_kinds
    refused = await post_board(bot, bot.guild, FakeActor(), await fresh(bot, marathon))
    assert refused.code == "not_tracked" and "press **Track** first" in refused.message


async def test_track_makes_the_thread_beside_the_inbox_and_the_board_lands_inside_it(
    bot,
    cog,
):
    marathon = await found(bot, cog, channel=await gdq_row(bot))
    done = await inbox.track(bot, bot.guild, FakeActor(), marathon)

    assert done.ok and "is tracked" in done.message
    row = await fresh(bot, marathon)
    assert row["tracked_at"] and row["tracked_by"] == FakeActor.id and row["thread_home"] == "on"
    thread = marathon_thread(bot)
    assert row["thread_id"] == thread.id and thread.name == "AGDQ 2027"
    assert "post in its own thread, beside the inbox" in done.message
    opening = thread.messages[0].content
    assert (
        opening.startswith(f"AGDQ 2027 — tracked by <@{FakeActor.id}>") and "Schedule:" in opening
    )
    message = inbox_messages(bot, EVENTS)[0]
    assert fields_of(message)["State"].startswith(f"Tracked by <@{FakeActor.id}>")
    labels = labels_of(message.edits[-1]["view"])
    assert labels[0] == "Untrack" and "Open the thread" in labels
    tracked = await details_of(bot.db, "marathon.tracked")
    assert tracked["automatic"] is False and tracked["marathon_id"] == marathon["id"]
    assert (await details_of(bot.db, "marathon.thread_made"))["channel_id"] == EVENTS

    await cog.follow(bot.guild, await fresh(bot, marathon))
    board = [one for one in thread.messages if "BaF on the schedule" in one.content]
    assert len(board) == 1 and board[0].pinned
    assert (await fresh(bot, marathon))["board_channel_id"] == thread.id
    assert room(bot, CHANNEL).messages == []


async def test_the_thread_channel_key_moves_the_threads_and_the_inbox_stays(
    bot,
    cog,
):
    threading(bot, THREADS)
    await bot.store.set(GUILD, "marathon_thread_channel_id", THREADS)
    marathon = await found(bot, cog)
    await inbox.track(bot, bot.guild, FakeActor(), marathon)
    assert len(room(bot).threads) == 1 and len(room(bot, THREADS).threads) == 1
    assert (await fresh(bot, marathon))["thread_id"] == room(bot, THREADS).threads[0].id


async def test_with_the_thread_key_off_track_posts_in_the_marathon_channel_as_before(
    bot,
    cog,
):
    await bot.store.set(GUILD, "marathon_track_makes_thread", False)
    marathon = await found(bot, cog)
    done = await inbox.track(bot, bot.guild, FakeActor(), marathon)
    assert done.ok and "post in the marathon channel" in done.message
    await cog.follow(bot.guild, await fresh(bot, marathon))
    assert [one for one in room(bot, CHANNEL).messages if "BaF on the schedule" in one.content]
    assert len(room(bot).threads) == 1 and (await fresh(bot, marathon))["thread_id"] is None


async def test_untrack_archives_the_thread_unpins_the_board_and_track_reopens_it(
    bot,
    cog,
):
    marathon = await found(bot, cog)
    await inbox.track(bot, bot.guild, FakeActor(), marathon)
    await cog.follow(bot.guild, await fresh(bot, marathon))
    thread = marathon_thread(bot)
    board = next(one for one in thread.messages if "BaF on the schedule" in one.content)

    done = await inbox.untrack(bot, bot.guild, FakeActor(), await fresh(bot, marathon))

    assert done.ok and "not tracked any more" in done.message
    assert thread.archived and board.pinned is False
    row = await fresh(bot, marathon)
    assert row["tracked_at"] is None and row["thread_id"] == thread.id
    assert labels_of(inbox_messages(bot, EVENTS)[0].edits[-1]["view"])[:2] == ["Track", "Ignore"]
    before = len(thread.messages)
    await cog.follow(bot.guild, row)
    assert len(thread.messages) == before

    await inbox.track(bot, bot.guild, FakeActor(), row)
    assert not thread.archived and len(room(bot).threads) == 2
    assert "marathon.untracked" in await kinds(bot.db)


async def test_ignore_keeps_it_on_the_list_posts_nothing_and_reads_it_far(
    bot,
    cog,
):
    marathon = await found(bot, cog)
    done = await inbox.ignore(bot, bot.guild, FakeActor(), marathon, True)

    assert done.ok and "is ignored" in done.message
    row = await fresh(bot, marathon)
    assert row["ignored_at"] and row["ignored_by"] == FakeActor.id and row["tracked_at"] is None
    message = inbox_messages(bot, EVENTS)[0]
    assert fields_of(message)["State"].startswith(f"Ignored by <@{FakeActor.id}>")
    assert labels_of(message.edits[-1]["view"])[0] == "Track anyway"
    calls = cog.client.calls
    cog.clock = lambda: NOW + timedelta(minutes=45)
    await cog.tick_once()
    assert cog.client.calls == calls and room(bot, CHANNEL).messages == []
    cog.clock = lambda: NOW + timedelta(hours=25)
    await cog.tick_once()
    assert cog.client.calls == calls + 1

    anyway = await inbox.run_action(bot, bot.guild, FakeActor(), row, mi.ANYWAY)
    assert anyway.ok and mi.is_tracked(await fresh(bot, marathon))


async def test_ignoring_a_tracked_marathon_stops_it_and_unignore_puts_it_back_to_found(
    bot,
    cog,
):
    marathon = await found(bot, cog)
    await inbox.track(bot, bot.guild, FakeActor(), marathon)
    await inbox.ignore(bot, bot.guild, FakeActor(), await fresh(bot, marathon), True)
    assert marathon_thread(bot).archived
    assert (await details_of(bot.db, "marathon.ignored"))["was_tracked"] is True

    back = await inbox.ignore(bot, bot.guild, FakeActor(), await fresh(bot, marathon), False)
    assert back.ok and "not ignored any more" in back.message
    assert mi.state_of(await fresh(bot, marathon)) == mi.FOUND
    assert "marathon.unignored" in await kinds(bot.db)


async def test_track_refuses_in_words_when_the_channel_is_opted_out(bot, cog):
    channel = await gdq_row(bot)
    marathon = await found(bot, cog, channel=channel)
    await bot.db.conn.execute(
        "UPDATE spotlight_channels SET marathons = 0 WHERE id = ?", (channel["id"],)
    )
    await bot.db.conn.commit()
    refused = await inbox.track(bot, bot.guild, FakeActor(), marathon)
    assert refused.code == "channel_opted_out" and "opted out of marathons" in refused.message
    assert (await fresh(bot, marathon))["tracked_at"] is None


# --- shadow, off, the lost and archived inbox ---------------------------------------------


async def test_shadow_makes_the_inbox_and_the_threads_in_the_shadow_home(bot, cog):
    await bot.store.set(GUILD, "marathon_mode", "shadow")
    marathon = await found(bot, cog)
    await inbox.track(bot, bot.guild, FakeActor(), marathon)

    shadow = room(bot, SHADOW_CHANNEL)
    assert room(bot).threads == [] and len(shadow.threads) == 2
    assert f"<#{EVENTS}>" in shadow.threads[0].messages[0].content
    assert f"<#{EVENTS}>" in shadow.threads[1].messages[0].content
    assert (await fresh(bot, marathon))["thread_home"] == "shadow"

    await bot.store.set(GUILD, "marathon_mode", "on")
    await cog.tick_once()
    assert len(inbox_messages(bot, EVENTS)) == 1
    row = await fresh(bot, marathon)
    assert row["thread_home"] == "on" and len(room(bot).threads) == 2
    assert (await details_of(bot.db, "marathon.thread_made"))["replaced"] == shadow.threads[1].id


async def test_a_feature_shadow_home_takes_the_inbox(bot, cog):
    await bot.store.set(GUILD, "marathon_mode", "shadow")
    await bot.store.set(GUILD, "marathon_shadow_channel_id", LOG_CHANNEL)
    log_room = threading(bot, LOG_CHANNEL)
    await found(bot, cog)
    assert len(log_room.threads) == 1 and room(bot, SHADOW_CHANNEL).threads == []


async def test_off_makes_nothing_and_edits_nothing(bot, cog):
    await bot.store.set(GUILD, "marathon_mode", "off")
    marathon = await found(bot, cog)
    await inbox.track(bot, bot.guild, FakeActor(), marathon)
    assert room(bot).threads == [] and (await fresh(bot, marathon))["tracked_at"]
    assert (await fresh(bot, marathon))["thread_id"] is None


async def test_an_archived_inbox_is_reopened_and_a_deleted_one_is_made_again(
    bot,
    cog,
):
    first = await found(bot, cog)
    old = the_inbox(bot)
    old.archived = True
    await inbox.sync_inbox(bot, bot.guild, await fresh(bot, first), force=True)
    assert old.archived is False and old.thread_edits[-1] == {"archived": False}

    del bot.guild.channels[old.id]
    cog.clock = lambda: NOW + timedelta(minutes=mi.RECHECK_MINUTES + 1)
    await cog.tick_once()
    assert len(room(bot).threads) == 2
    lost = await details_of(bot.db, "marathon.inbox_lost")
    assert lost["thread_id"] == old.id and lost["home"] == "on"
    assert len(inbox_messages(bot, EVENTS)) == 1


async def test_two_passes_at_once_make_exactly_one_inbox(bot, cog):
    """Checklist 37: the stored thread id is re-read after the lock is taken."""
    made = await asyncio.gather(*(inbox.ensure_inbox(bot, bot.guild) for _ in range(3)))
    assert len({thread.id for thread, _why in made}) == 1 and len(room(bot).threads) == 1
    assert (await kinds(bot.db)).count("marathon.inbox_made") == 1


async def test_two_tracks_at_once_make_exactly_one_thread(bot, cog):
    marathon = await found(bot, cog)
    await asyncio.gather(
        inbox.track(bot, bot.guild, FakeActor(), marathon),
        inbox.track(bot, bot.guild, FakeActor(), marathon),
    )
    assert len(room(bot).threads) == 2
    assert (await kinds(bot.db)).count("marathon.tracked") == 1
    assert (await kinds(bot.db)).count("marathon.thread_made") == 1


async def test_a_deleted_marathon_thread_is_made_again_at_the_next_post(bot, cog):
    marathon = await found(bot, cog)
    await inbox.track(bot, bot.guild, FakeActor(), marathon)
    del bot.guild.channels[marathon_thread(bot).id]
    await cog.follow(bot.guild, await fresh(bot, marathon))
    assert len(room(bot).threads) == 3
    assert "marathon.thread_lost" in await kinds(bot.db)
    assert (await fresh(bot, marathon))["board_channel_id"] == room(bot).threads[2].id


async def test_archiving_edits_the_inbox_message_and_archives_the_thread_restore_undoes_it(
    bot,
    cog,
):
    marathon = await found(bot, cog)
    await inbox.track(bot, bot.guild, FakeActor(), marathon)
    await archive_marathon(bot, bot.guild, FakeActor(), await fresh(bot, marathon))

    message = inbox_messages(bot, EVENTS)[0]
    assert fields_of(message)["State"].startswith("Archived ")
    assert all(
        getattr(child, "style", None) == discord.ButtonStyle.link
        for child in (message.edits[-1]["view"] or discord.ui.View()).children
    )
    assert marathon_thread(bot).archived

    restored = await restore_marathon(bot, bot.guild, FakeActor(), marathon["id"])
    assert restored.ok
    assert fields_of(inbox_messages(bot, EVENTS)[0])["State"].startswith("Tracked by")


# --- the feed's auto-track (owner D3) -----------------------------------------------------


async def gdq_feed(bot, auto):
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
        auto_track=auto,
    )
    return channel, feed_id


async def feed_made(bot, cog, auto):
    channel, feed_id = await gdq_feed(bot, auto)
    made = await create_marathon(
        bot, bot.guild, None, name="AGDQ 2027", url=URL, feed_id=feed_id, noticed=False
    )
    return made.value


async def test_an_auto_track_feed_tracks_its_marathon_the_moment_its_schedule_is_out(
    bot,
    cog,
):
    marathon = await feed_made(bot, cog, True)
    await refresh_marathon(bot, bot.guild, marathon)

    row = await fresh(bot, marathon)
    assert mi.is_tracked(row) and row["tracked_by"] is None and row["noticed_at"]
    tracked = await details_of(bot.db, "marathon.tracked")
    assert tracked["automatic"] is True and tracked["feed_id"] == marathon["feed_id"]
    assert fields_of(inbox_messages(bot, EVENTS)[0])["State"].startswith("Tracked by the GDQ feed")
    assert (
        marathon_thread(bot).messages[0].content.startswith("AGDQ 2027 — tracked by the GDQ feed")
    )

    await inbox.untrack(bot, bot.guild, FakeActor(), row)
    await refresh_marathon(bot, bot.guild, await fresh(bot, marathon))
    assert not mi.is_tracked(await fresh(bot, marathon))


async def test_a_feed_with_auto_track_off_leaves_track_to_staff(bot, cog):
    marathon = await feed_made(bot, cog, False)
    await refresh_marathon(bot, bot.guild, marathon)
    row = await fresh(bot, marathon)
    assert row["noticed_at"] and not mi.is_tracked(row)
    assert "marathon.tracked" not in await kinds(bot.db)


async def test_the_auto_track_switch_is_a_feed_change_and_a_new_feed_copies_the_default(
    bot,
    cog,
):
    _channel, feed_id = await gdq_feed(bot, False)
    feed = await feeds.get_feed(bot.db, GUILD, feed_id)
    done = await feeds.set_feed(bot, bot.guild, FakeActor(), feed, auto_track=True)
    assert done.ok and "auto-track is on" in done.message
    assert (await feeds.get_feed(bot.db, GUILD, feed_id))["auto_track"] == 1
    assert (await details_of(bot.db, "marathon.feed_changed"))["auto_track"] is True

    embed, view = await feeds.feed_card(bot, bot.guild, feed_id)
    assert "Auto-track: on" in embed.description
    assert "Auto-track off" in [getattr(one, "label", None) for one in view.children]

    await bot.store.set(GUILD, "marathon_auto_track_default", True)
    other = await feeds.insert_feed(
        bot.db,
        GUILD,
        source="tracker",
        feed_ref="https://tracker.rpglimitbreak.com",
        spotlight_id=999,
        name="RPGLB",
        action="add",
        added_by=None,
        auto_track=bool(bot.store.get(GUILD, "marathon_auto_track_default")),
    )
    assert (await feeds.get_feed(bot.db, GUILD, other))["auto_track"] == 1


# --- the buttons and the panel ------------------------------------------------------------


async def test_the_inbox_buttons_are_staff_only_and_rebuild_from_their_custom_id(
    bot,
    cog,
):
    marathon = await found(bot, cog)
    custom = mi.custom_id(marathon["id"], mi.TRACK)
    button = await inbox.InboxButton.from_custom_id(
        None, None, re.fullmatch(mi.INBOX_TEMPLATE, custom)
    )
    assert (button.marathon_id, button.action) == (marathon["id"], mi.TRACK)

    bot.store.is_staff = lambda member: False
    stranger = FakeInteraction(bot, Member(42), bot.guild)
    await button.on_click(stranger)
    assert "staff only" in stranger.sent and not mi.is_tracked(await fresh(bot, marathon))

    bot.store.is_staff = lambda member: True
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    await button.on_click(lead)
    assert "is tracked" in lead.sent and mi.is_tracked(await fresh(bot, marathon))


async def test_the_inbox_buttons_outlive_a_restart():
    registered = []
    made = Marathons.__new__(Marathons)
    made.bot = type("Bot", (), {"db": type("Db", (), {"is_connected": False})()})()
    made.bot.add_dynamic_items = lambda *items: registered.extend(items)
    await Marathons.cog_load(made)
    assert inbox.InboxButton in registered


async def test_the_panel_card_says_the_state_and_offers_only_valid_moves(bot, cog):
    from black_bloc.cogs.content.marathon import build_card

    marathon = await found(bot, cog)
    embed, view = await build_card(bot, bot.guild, marathon["id"])
    labels = [getattr(one, "label", None) for one in view.children]
    assert "Track" in labels and "Ignore" in labels and "Untrack" not in labels
    assert "not tracked" in embed.description

    await inbox.track(bot, bot.guild, FakeActor(), marathon)
    embed, view = await build_card(bot, bot.guild, marathon["id"])
    labels = [getattr(one, "label", None) for one in view.children]
    assert "Untrack" in labels and "Track" not in labels
    assert "[thread](https://discord.com/channels/" in embed.description


async def test_the_api_row_carries_the_inbox_message_link(bot, cog):
    marathon = await found(bot, cog)
    row = await fresh(bot, marathon)
    url = await inbox.inbox_message_url(bot, bot.guild, row)
    assert (
        url == f"https://discord.com/channels/{GUILD}/{the_inbox(bot).id}/{row['inbox_message_id']}"
    )


# --- marathon-inbox-when: the message waits for the schedule ----------------------------------

LATER_URL = "https://gamesdonequick.com/schedule/75"


async def unpublished(bot, cog, *, name="SGDQ 2027", url=LATER_URL):
    cog.client.runs_given = []
    made = await create_marathon(bot, bot.guild, FakeActor(), name=name, url=url)
    assert made.ok, made.message
    cog.client.runs_given = list(SCHEDULE)
    return made.value


async def test_published_holds_a_staff_added_marathon_until_its_first_read_with_runs(bot, cog):
    marathon = await unpublished(bot, cog)

    assert room(bot).threads == [] and (await fresh(bot, marathon))["inbox_message_id"] is None
    assert (await fresh(bot, marathon))["noticed_at"] is None

    await refresh_marathon(bot, bot.guild, await fresh(bot, marathon))

    messages = inbox_messages(bot, EVENTS)
    row = await fresh(bot, marathon)
    assert len(messages) == 1 and row["inbox_message_id"] == messages[0].id
    assert fields_of(messages[0])["Schedule"] == "5 runs · 1 BaF" and row["noticed_at"]
    published = await logged(bot, "marathon.inbox_published")
    assert len(published) == 1 and published[0]["marathon_id"] == marathon["id"]
    assert "feed_id" not in published[0]

    await refresh_marathon(bot, bot.guild, row)
    assert len(inbox_messages(bot, EVENTS)) == 1
    assert len(await logged(bot, "marathon.inbox_published")) == 1


async def test_a_staff_add_with_a_published_schedule_posts_at_once_and_claims_the_moment(bot, cog):
    marathon = await found(bot, cog)
    assert len(inbox_messages(bot, EVENTS)) == 1 and (await fresh(bot, marathon))["noticed_at"]
    assert len(await logged(bot, "marathon.inbox_published")) == 1


async def test_added_posts_the_inbox_message_the_moment_it_is_on_the_list(bot, cog):
    await bot.store.set(GUILD, "marathon_feed_notice_when", "added")
    marathon = await unpublished(bot, cog)

    messages = inbox_messages(bot, EVENTS)
    assert len(messages) == 1 and fields_of(messages[0])["Schedule"] == "not out yet"
    assert (await fresh(bot, marathon))["noticed_at"] is None

    await refresh_marathon(bot, bot.guild, await fresh(bot, marathon))

    assert len(inbox_messages(bot, EVENTS)) == 1
    assert fields_of(inbox_messages(bot, EVENTS)[0])["Schedule"] == "5 runs · 1 BaF"
    assert len(await logged(bot, "marathon.inbox_published")) == 1


async def test_the_first_tick_after_the_deploy_posts_only_marathons_whose_schedule_has_runs(
    bot, cog
):
    await bot.store.set(GUILD, "marathon_mode", "off")
    with_runs = await found(bot, cog)
    without = await unpublished(bot, cog)
    await bot.db.conn.execute("UPDATE marathons SET noticed_at = added_at")
    await bot.db.conn.commit()
    await bot.store.set(GUILD, "marathon_mode", "on")
    cog.client.raises = ScheduleError("not published", unpublished=True)

    await cog.tick_once()

    messages = inbox_messages(bot, EVENTS)
    assert len(messages) == 1
    assert (await fresh(bot, with_runs))["inbox_message_id"] == messages[0].id
    assert (await fresh(bot, without))["inbox_message_id"] is None
    assert [one["marathon_id"] for one in await logged(bot, "marathon.inbox_posted")] == [
        with_runs["id"]
    ]
