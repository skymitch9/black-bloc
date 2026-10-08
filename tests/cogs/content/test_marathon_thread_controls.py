# ruff: noqa: F401, F811
import re
from datetime import timedelta

import pytest

from black_bloc import marathon_thread_controls as mtc
from black_bloc.cogs.content import marathon_events as runev
from black_bloc.cogs.content import marathon_inbox as inbox
from black_bloc.cogs.content import marathon_thread_controls as controls
from black_bloc.cogs.content.marathon import (
    Marathons,
    create_marathon,
    get_marathon,
    make_event_now,
    update_marathon,
)
from black_bloc.cogs.content.marathon_spotlight import set_spotlight_mode, settle_held
from black_bloc.cogs.content.spotlight import (
    change_spotlight,
    changed_spotlight,
    channel_by_id,
    run_spotlight_move,
    spotlight_channel,
)
from tests.cogs.content.test_marathon import (
    NOW,
    URL,
    Member,
    at,
    bot,
    cog,
    gdq_row,
    proposals,
    threading,
)
from tests.cogs.content.test_spotlight import (
    GUILD,
    FakeActor,
    FakeInteraction,
    details_of,
    kinds,
)

EVENTS = 555
THREADS = 556


@pytest.fixture(autouse=True)
async def events_room(bot):
    threading(bot, EVENTS)
    await bot.store.set(GUILD, "events_announce_channel_id", EVENTS)
    await bot.store.set(GUILD, "marathon_track_makes_thread", True)
    await bot.store.set(GUILD, "events_create_scheduled", False)
    bot.guild.name = "Black and Friends"


async def quiet_row(bot, login="rpglimitbreak"):
    outcome, row = await spotlight_channel(
        bot, bot.guild, FakeActor(), login, keep=True, spotlight=False
    )
    assert outcome == "added"
    return row


async def tracked_marathon(bot, cog, *, channel=None):
    made = await create_marathon(
        bot,
        bot.guild,
        FakeActor(),
        name="AGDQ 2027",
        url=URL,
        spotlight_id=channel["id"] if channel is not None else None,
    )
    assert made.ok, made.message
    done = await inbox.track(bot, bot.guild, FakeActor(), made.value)
    assert done.ok, done.message
    return await fresh(bot, made.value)


async def fresh(bot, marathon):
    return await get_marathon(bot.db, GUILD, marathon["id"])


def the_thread(bot, channel_id=EVENTS):
    return bot.guild.channels[channel_id].threads[-1]


def controls_in(thread):
    return [
        one
        for one in thread.messages
        if any(
            str(getattr(getattr(item, "item", item), "custom_id", "")).startswith(
                "marathon:controls:"
            )
            for item in (current_view(one).children if current_view(one) else ())
        )
    ]


def current_view(message):
    for edit in reversed(message.edits):
        if "view" in edit:
            return edit["view"]
    return message.kwargs.get("view")


def labels(message):
    return [getattr(one, "item", one).label for one in current_view(message).children]


def buttons(message):
    return [getattr(one, "item", one) for one in current_view(message).children]


async def pressed(bot, marathon, action, to):
    return await controls.press(bot, bot.guild, FakeActor(), marathon["id"], action, to)


def spot_label(message):
    return next((one for one in labels(message) if one.startswith("Spotlight")), None)


def spot_button(message):
    return next(
        (one for one in buttons(message) if ":spotlight:" in str(one.custom_id or "")), None
    )


def event_label(message):
    return next(one for one in labels(message) if one.startswith("Marathon event"))


ON_SWITCH = "Spotlight follows the schedule: on · turn off"
OFF_SWITCH = "Spotlight follows the schedule: off · turn on"


# --- the message --------------------------------------------------------------------------------


async def test_track_posts_one_pinned_control_message_right_after_the_opening(bot, cog):
    marathon = await tracked_marathon(bot, cog, channel=await quiet_row(bot))

    thread = the_thread(bot)
    assert thread.messages[0].content.startswith("AGDQ 2027 — tracked by")
    message = thread.messages[1]
    assert controls_in(thread) == [message] and message.pinned
    assert marathon["controls_message_id"] == message.id
    assert message.content.splitlines()[0].startswith("Spotlight: on now until <t:")
    assert "Staff:" not in message.content
    assert labels(message) == [
        "Runner announcements: on · turn off",
        "Host announcements: off · turn on",
        "Ping the marathon role: off · turn on",
        ON_SWITCH,
        "Marathon event: off · turn on",
        "Marathon tracker ↗",
        "BaF event: no (1 of 5 runs) · say yes",
    ]
    ids = [one.custom_id for one in buttons(message)]
    assert ids == [
        f"marathon:controls:{marathon['id']}:announce:off",
        f"marathon:controls:{marathon['id']}:hostannounce:on",
        f"marathon:controls:{marathon['id']}:ping:on",
        f"marathon:controls:{marathon['id']}:spotlight:off",
        f"marathon:controls:{marathon['id']}:event:on",
        None,
        f"marathon:controls:{marathon['id']}:baf:yes",
    ]
    assert [one.row for one in buttons(message)] == [0, 0, 0, 0, 0, 1, 1]
    assert not any(one.disabled for one in buttons(message))
    assert message.kwargs["allowed_mentions"].users is False
    posted = await details_of(bot.db, "marathon.controls_posted")
    assert posted["pinned"] is True and posted["message_id"] == message.id


async def test_a_tracked_thread_with_no_controls_gets_them_once_on_the_tick(bot, cog):
    marathon = await tracked_marathon(bot, cog, channel=await quiet_row(bot))
    thread = the_thread(bot)
    thread.messages.remove(thread.messages[1])
    await update_marathon(bot.db, marathon["id"], controls_message_id=None)
    cog.__dict__.get("controls_shown", {}).clear()

    await cog.tick_once()
    await cog.tick_once()

    found = controls_in(thread)
    assert len(found) == 1 and found[0].pinned
    assert (await fresh(bot, marathon))["controls_message_id"] == found[0].id
    assert (await kinds(bot.db)).count("marathon.controls_posted") == 2


async def test_a_deleted_control_message_is_noticed_and_posted_again(bot, cog):
    marathon = await tracked_marathon(bot, cog, channel=await quiet_row(bot))
    thread = the_thread(bot)
    thread.messages.remove(thread.messages[1])
    cog.__dict__.get("controls_shown", {}).clear()

    await cog.tick_once()

    assert "marathon.controls_lost" in await kinds(bot.db)
    assert len(controls_in(thread)) == 1
    assert (await fresh(bot, marathon))["controls_message_id"] == controls_in(thread)[0].id


async def test_an_unchanged_marathon_costs_no_discord_write_on_the_tick(bot, cog):
    marathon = await tracked_marathon(bot, cog, channel=await quiet_row(bot))
    await cog.tick_once()
    message = controls_in(the_thread(bot))[0]
    before = (len(message.edits), len(the_thread(bot).messages))

    await cog.tick_once()
    await cog.tick_once()

    assert (len(message.edits), len(the_thread(bot).messages)) == before
    assert marathon["controls_message_id"] == message.id


async def test_the_state_lines_and_labels_are_keys_and_an_edit_re_renders(bot, cog):
    await tracked_marathon(bot, cog, channel=await quiet_row(bot))
    await bot.store.set(GUILD, "marathon_controls_event_off", "Whole-marathon event: off")
    await bot.store.set(GUILD, "marathon_controls_spotlight_until_line", "Lit until {until}")

    await cog.tick_once()

    message = controls_in(the_thread(bot))[0]
    assert "Whole-marathon event: off" in labels(message)
    assert message.content.splitlines()[0].startswith("Lit until <t:")


async def test_after_the_show_only_the_tracker_and_archive_it_are_drawn(bot, cog):
    marathon = await tracked_marathon(bot, cog, channel=await quiet_row(bot))
    message = controls_in(the_thread(bot))[0]
    cog.clock = lambda: NOW + timedelta(minutes=230)

    await controls.refresh_controls(bot, bot.guild, marathon["id"])

    assert labels(message) == ["Marathon tracker ↗", "Archive it"]
    assert [one.row for one in buttons(message)] == [0, 0]
    assert buttons(message)[1].custom_id == f"marathon:controls:{marathon['id']}:archive:on"
    assert message.content.startswith("Spotlight: on now until <t:")


async def test_archive_it_moves_the_marathon_to_the_archive_and_restore_brings_the_buttons_back(
    bot, cog
):
    from black_bloc.cogs.content.marathon_archive import archived_marathon, restore_marathon

    marathon = await tracked_marathon(bot, cog, channel=await quiet_row(bot))
    message = controls_in(the_thread(bot))[0]
    cog.clock = lambda: NOW + timedelta(minutes=230)
    await controls.refresh_controls(bot, bot.guild, marathon["id"])

    said = await pressed(bot, marathon, "archive", "on")

    assert said.ok
    assert await fresh(bot, marathon) is None
    assert (await archived_marathon(bot.db, GUILD, marathon["id"]))["archived_why"] == "staff"
    assert current_view(message) is None
    assert "marathon.archived" in await kinds(bot.db)

    back = await restore_marathon(bot, bot.guild, FakeActor(), marathon["id"])
    assert back.ok
    await controls.refresh_controls(bot, bot.guild, marathon["id"])
    assert labels(message) == ["Marathon tracker ↗", "Archive it"]


def edits_refused_once_archived(thread, message):
    real = message.edit
    seen = []

    async def edit(content=None, **kwargs):
        seen.append(thread.archived)
        if thread.archived:
            raise RuntimeError("Thread is archived")
        return await real(content, **kwargs)

    message.edit = edit
    return seen


async def an_ended_marathon(bot, cog):
    marathon = await tracked_marathon(bot, cog, channel=await quiet_row(bot))
    thread = the_thread(bot)
    message = controls_in(thread)[0]
    cog.clock = lambda: NOW + timedelta(minutes=230)
    await controls.refresh_controls(bot, bot.guild, marathon["id"])
    return marathon, thread, message, edits_refused_once_archived(thread, message)


async def test_archive_it_on_the_thread_clears_the_buttons_before_the_thread_is_archived(bot, cog):
    marathon, thread, message, seen = await an_ended_marathon(bot, cog)

    assert (await pressed(bot, marathon, "archive", "on")).ok

    assert seen and True not in seen and current_view(message) is None and thread.archived


async def test_the_sites_archive_clears_the_buttons_before_the_thread_is_archived(bot, cog):
    from black_bloc.cogs.content.marathon_archive import archive_marathon

    marathon, thread, message, seen = await an_ended_marathon(bot, cog)

    done = await archive_marathon(bot, bot.guild, FakeActor(), marathon, via="website")

    assert (
        done.ok and seen and True not in seen and current_view(message) is None and thread.archived
    )


async def test_the_automatic_archive_clears_the_buttons_before_the_thread_is_archived(bot, cog):
    marathon, thread, message, seen = await an_ended_marathon(bot, cog)
    await bot.store.set(GUILD, "marathon_archive_after_days", 1)
    cog.clock = lambda: NOW + timedelta(days=3)

    await cog.tick_once()

    assert await fresh(bot, marathon) is None
    assert seen and True not in seen and current_view(message) is None and thread.archived


async def test_an_already_archived_thread_is_opened_to_clear_the_buttons_and_archived_again(
    bot, cog
):
    from black_bloc.cogs.content.marathon_archive import archive_marathon

    marathon, thread, message, seen = await an_ended_marathon(bot, cog)
    thread.archived = True

    await archive_marathon(bot, bot.guild, FakeActor(), marathon, via="website")

    assert seen and True not in seen and current_view(message) is None and thread.archived


# --- the marathon event button ------------------------------------------------------------------


async def test_the_marathon_event_button_moves_its_half_through_set_event_mode(
    bot, cog, proposals, monkeypatch
):
    marathon = await tracked_marathon(bot, cog)
    seen = []
    real = runev.set_event_mode

    async def spy(bot, guild, actor, marathon, mode, *, via="discord"):
        seen.append(mode)
        return await real(bot, guild, actor, marathon, mode, via=via)

    monkeypatch.setattr(controls, "set_event_mode", spy)
    message = controls_in(the_thread(bot))[0]

    await pressed(bot, marathon, "event", "on")
    assert (await fresh(bot, marathon))["event_mode"] == "marathon"
    assert event_label(message) == "Marathon event: on · turn off"
    await real(bot, bot.guild, FakeActor(), await fresh(bot, marathon), "both", via="website")
    await pressed(bot, marathon, "event", "off")
    assert (await fresh(bot, marathon))["event_mode"] == "runs"
    assert event_label(message) == "Marathon event: off · turn on"

    assert seen == ["marathon", "runs"]


async def test_a_stale_label_never_does_the_opposite(bot, cog, proposals):
    marathon = await tracked_marathon(bot, cog)
    await runev.set_event_mode(bot, bot.guild, FakeActor(), marathon, "marathon")

    said = await pressed(bot, marathon, "event", "on")

    assert said.ok and "already makes" in said.message
    assert (await fresh(bot, marathon))["event_mode"] == "marathon"


async def test_a_mode_change_from_the_drawer_or_the_card_re_renders_the_message(
    bot, cog, proposals
):
    marathon = await tracked_marathon(bot, cog)
    message = controls_in(the_thread(bot))[0]

    await runev.set_event_mode(bot, bot.guild, FakeActor(), marathon, "runs", via="website")
    assert event_label(message) == "Marathon event: off · turn on"

    await make_event_now(bot, bot.guild, FakeActor(), await fresh(bot, marathon))
    assert event_label(message) == "Marathon event: on · turn off"


# --- the spotlight switch -----------------------------------------------------------------------


async def test_turn_off_during_the_show_stops_following_and_lifts_only_what_the_schedule_lit(
    bot, cog
):
    row = await quiet_row(bot)
    marathon = await tracked_marathon(bot, cog, channel=row)
    assert (await channel_by_id(bot.db, row["id"]))["spotlit_by_marathon"] == marathon["id"]

    said = await pressed(bot, marathon, "spotlight", "off")

    assert said.ok and "**AGDQ 2027** no longer spotlights its channel." in said.message
    lit = await channel_by_id(bot.db, row["id"])
    assert (lit["spotlight"], lit["spotlit_by_marathon"]) == (0, None)
    assert (await fresh(bot, marathon))["spotlight_mode"] == "off"
    assert "marathon.spotlight_mode_set" in await kinds(bot.db)
    message = controls_in(the_thread(bot))[0]
    assert spot_label(message) == OFF_SWITCH
    assert spot_button(message).custom_id == f"marathon:controls:{marathon['id']}:spotlight:on"
    assert not message.content.startswith("Spotlight:")


async def test_turn_off_during_the_show_leaves_a_staff_spotlight_running_and_says_so(bot, cog):
    row = await quiet_row(bot)
    marathon = await tracked_marathon(bot, cog, channel=row)
    await update_channel_held(bot, row)
    await change_spotlight(
        bot, bot.guild, FakeActor(), row["id"], spotlight=True, expires_at=at(400)
    )
    staff = await channel_by_id(bot.db, row["id"])
    assert staff["spotlight"] == 1 and staff["spotlit_by_marathon"] is None

    said = await pressed(bot, marathon, "spotlight", "off")

    assert said.ok and said.message == (
        "**AGDQ 2027** no longer follows the schedule. twitch.tv/rpglimitbreak stays spotlit — "
        "stop it on Go-live."
    )
    assert (await fresh(bot, marathon))["spotlight_mode"] == "off"
    still = await channel_by_id(bot.db, row["id"])
    assert (still["spotlight"], still["expires_at"]) == (1, at(400))
    message = controls_in(the_thread(bot))[0]
    assert spot_label(message) == OFF_SWITCH
    until = int((NOW + timedelta(minutes=400)).timestamp())
    assert message.content.splitlines()[0] == (
        f"Spotlight: on until <t:{until}:f> · not following the schedule · stop it on Go-live"
    )


async def update_channel_held(bot, row):
    from black_bloc.cogs.content.spotlight import update_channel

    await update_channel(bot.db, int(row["id"]), spotlit_by_marathon=None)


async def test_turn_off_on_a_held_marathon_not_in_reach_still_stops_it(bot, cog):
    row = await quiet_row(bot)
    marathon = await tracked_marathon(bot, cog, channel=row)
    await update_marathon(bot.db, marathon["id"], starts_at=at(5000), ends_at=at(6000))

    await pressed(bot, marathon, "spotlight", "off")

    assert (await fresh(bot, marathon))["spotlight_mode"] == "off"
    assert (await channel_by_id(bot.db, row["id"]))["spotlight"] == 0


async def test_turn_on_holds_the_row_for_this_marathon_and_the_lift_ends_it_at_span_end_plus_tail(
    bot, cog
):
    await bot.store.set(GUILD, "marathon_spotlight", False)
    row = await quiet_row(bot)
    marathon = await tracked_marathon(bot, cog, channel=row)
    assert (await channel_by_id(bot.db, row["id"]))["spotlight"] == 0

    said = await pressed(bot, marathon, "spotlight", "on")

    lit = await channel_by_id(bot.db, row["id"])
    assert (lit["spotlight"], lit["expires_at"], lit["spotlit_by_marathon"]) == (
        1,
        at(270),
        marathon["id"],
    )
    assert said.ok and "twitch.tv/rpglimitbreak is spotlit for **AGDQ 2027**" in said.message
    assert "plus 60 minutes" in said.message
    updated = await details_of(bot.db, "golive.spotlight_updated")
    assert updated["spotlight"] == 1 and updated["spotlit_by_marathon"] == marathon["id"]
    message = controls_in(the_thread(bot))[0]
    assert spot_label(message) == ON_SWITCH
    assert message.content.startswith("Spotlight: on now until <t:")

    cog.clock = lambda: NOW + timedelta(minutes=215)
    assert await settle_held(bot, bot.guild, lit) == "kept"
    cog.clock = lambda: NOW + timedelta(minutes=270)
    assert await settle_held(bot, bot.guild, lit) == "lifted"
    assert (await channel_by_id(bot.db, row["id"]))["spotlight"] == 0
    assert not message.content.startswith("Spotlight:")


async def test_turn_on_after_a_staff_off_sets_the_follow_back_and_the_follow_spotlights_it(
    bot, cog
):
    row = await quiet_row(bot)
    marathon = await tracked_marathon(bot, cog, channel=row)
    await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "spotlight_off")
    assert (await fresh(bot, marathon))["spotlight_mode"] == "off"
    assert spot_label(controls_in(the_thread(bot))[0]) == OFF_SWITCH

    said = await pressed(bot, marathon, "spotlight", "on")

    assert (await fresh(bot, marathon))["spotlight_mode"] == "follow"
    lit = await channel_by_id(bot.db, row["id"])
    assert (lit["spotlight"], lit["spotlit_by_marathon"]) == (1, marathon["id"])
    assert "spotlights its channel while it runs again" in said.message
    assert spot_label(controls_in(the_thread(bot))[0]) == ON_SWITCH


async def test_turn_on_while_a_staff_spotlight_is_up_sets_the_follow_and_leaves_the_row(bot, cog):
    row, marathon = await far_off_marathon(bot, cog)
    await change_spotlight(bot, bot.guild, FakeActor(), row["id"], spotlight=True)

    said = await pressed(bot, marathon, "spotlight", "on")

    assert said.ok and "already spotlit" in said.message
    assert (await fresh(bot, marathon))["spotlight_mode"] == "follow"
    assert (await channel_by_id(bot.db, row["id"]))["spotlit_by_marathon"] is None


async def test_turn_on_with_no_span_ahead_is_refused_in_words(bot, cog):
    await bot.store.set(GUILD, "marathon_spotlight", False)
    row = await quiet_row(bot)
    marathon = await tracked_marathon(bot, cog, channel=row)
    cog.clock = lambda: NOW + timedelta(minutes=9000)

    said = await pressed(bot, marathon, "spotlight", "on")

    assert not said.ok and said.code == "no_end" and "no end to hold the spotlight" in said.message
    assert (await channel_by_id(bot.db, row["id"]))["spotlight"] == 0


async def test_a_kept_spotlight_draws_no_switch_says_so_and_an_old_stop_is_refused(bot, cog):
    row = await gdq_row(bot)
    marathon = await tracked_marathon(bot, cog, channel=row)
    message = controls_in(the_thread(bot))[0]
    assert spot_label(message) is None and spot_button(message) is None
    assert message.content.splitlines()[0] == "Spotlight: kept on Go-live"

    said = await pressed(bot, marathon, "spotlight", "off")

    assert not said.ok and said.code == "kept" and "kept for ever" in said.message
    lit = await channel_by_id(bot.db, row["id"])
    assert (lit["spotlight"], lit["expires_at"]) == (1, None)
    assert (await fresh(bot, marathon))["spotlight_mode"] in (None, "follow")


async def test_no_channel_draws_no_switch_and_says_so_in_the_state_line(bot, cog):
    marathon = await tracked_marathon(bot, cog)
    message = controls_in(the_thread(bot))[0]

    assert spot_label(message) is None and spot_button(message) is None
    assert message.content.splitlines()[0] == "Spotlight: no channel to spotlight"
    said = await pressed(bot, marathon, "spotlight", "on")
    assert not said.ok and said.code == "no_channel"


async def test_a_go_live_change_to_the_row_re_renders_the_message(bot, cog):
    row = await quiet_row(bot)
    await tracked_marathon(bot, cog, channel=row)
    message = controls_in(the_thread(bot))[0]

    await change_spotlight(bot, bot.guild, FakeActor(), row["id"], expires_at=None)

    assert spot_label(message) is None
    assert message.content.splitlines()[0] == "Spotlight: kept on Go-live"


async def test_the_follow_switch_from_the_drawer_re_renders_the_message(bot, cog):
    row = await quiet_row(bot)
    marathon = await tracked_marathon(bot, cog, channel=row)
    message = controls_in(the_thread(bot))[0]

    await set_spotlight_mode(bot, bot.guild, FakeActor(), marathon, "off", via="website")

    assert spot_label(message) == OFF_SWITCH


async def far_off_marathon(bot, cog, *, follow=False):
    row = await quiet_row(bot)
    marathon = await tracked_marathon(bot, cog, channel=row)
    await update_marathon(bot.db, marathon["id"], starts_at=at(5000), ends_at=at(6000))
    await set_spotlight_mode(bot, bot.guild, FakeActor(), await fresh(bot, marathon), "off")
    if follow:
        await set_spotlight_mode(bot, bot.guild, FakeActor(), await fresh(bot, marathon), "on")
    lit = await channel_by_id(bot.db, row["id"])
    assert (lit["spotlight"], lit["spotlit_by_marathon"]) == (0, None)
    return row, await fresh(bot, marathon)


async def test_turn_on_before_the_lead_window_leaves_the_row_and_sets_the_follow(bot, cog):
    row, marathon = await far_off_marathon(bot, cog)
    assert (await fresh(bot, marathon))["spotlight_mode"] == "off"
    await controls.refresh_controls(bot, bot.guild, marathon["id"])
    assert spot_label(controls_in(the_thread(bot))[0]) == OFF_SWITCH

    said = await pressed(bot, marathon, "spotlight", "on")

    opening = int((NOW + timedelta(minutes=5000 - 15)).timestamp())
    assert said.ok and said.message == (
        f"Spotlight is set to start 15 minutes before the first run — <t:{opening}:f> — and "
        "end 60 minutes after the last."
    )
    lit = await channel_by_id(bot.db, row["id"])
    assert (lit["spotlight"], lit["expires_at"], lit["spotlit_by_marathon"]) == (0, None, None)
    assert (await fresh(bot, marathon))["spotlight_mode"] == "follow"
    message = controls_in(the_thread(bot))[0]
    assert spot_label(message) == ON_SWITCH
    assert spot_button(message).custom_id == f"marathon:controls:{marathon['id']}:spotlight:off"
    assert message.content.splitlines()[0] == f"Spotlight: starts <t:{opening}:f>"

    cog.clock = lambda: NOW + timedelta(minutes=5000 - 16)
    assert await cog.follow_spotlight(bot.guild, marathon["id"]) is None
    cog.clock = lambda: NOW + timedelta(minutes=5000 - 15)
    assert await cog.follow_spotlight(bot.guild, marathon["id"]) == "set"
    lit = await channel_by_id(bot.db, row["id"])
    assert (lit["spotlight"], lit["expires_at"], lit["spotlit_by_marathon"]) == (
        1,
        at(6060),
        marathon["id"],
    )
    assert message.content.startswith("Spotlight: on now until <t:")


async def test_turn_on_before_the_lead_window_on_a_following_marathon_changes_nothing(bot, cog):
    row, marathon = await far_off_marathon(bot, cog, follow=True)

    said = await pressed(bot, marathon, "spotlight", "on")

    assert said.ok and said.message.startswith("Spotlight is set to start 15 minutes")
    assert (await channel_by_id(bot.db, row["id"]))["spotlight"] == 0
    assert (await kinds(bot.db)).count("marathon.spotlight_mode_set") == 2


async def test_the_starts_line_is_a_key(bot, cog):
    _row, marathon = await far_off_marathon(bot, cog, follow=True)
    await bot.store.set(GUILD, "marathon_controls_spotlight_starts_line", "Waits for {starts}")

    await controls.refresh_controls(bot, bot.guild, marathon["id"])

    opening = int((NOW + timedelta(minutes=5000 - 15)).timestamp())
    assert controls_in(the_thread(bot))[0].content.splitlines()[0] == (f"Waits for <t:{opening}:f>")


async def test_turn_on_inside_the_lead_window_turns_it_on_now_and_holds_it(bot, cog):
    await bot.store.set(GUILD, "marathon_spotlight", False)
    row = await quiet_row(bot)
    marathon = await tracked_marathon(bot, cog, channel=row)
    await update_marathon(bot.db, marathon["id"], starts_at=at(10), ends_at=at(100))

    said = await pressed(bot, marathon, "spotlight", "on")

    assert said.ok and "is spotlit for **AGDQ 2027**" in said.message
    lit = await channel_by_id(bot.db, row["id"])
    assert (lit["spotlight"], lit["expires_at"], lit["spotlit_by_marathon"]) == (
        1,
        at(160),
        marathon["id"],
    )
    assert spot_label(controls_in(the_thread(bot))[0]) == ON_SWITCH


async def test_turn_off_before_the_show_cancels_the_follow_and_leaves_the_row(bot, cog):
    row, marathon = await far_off_marathon(bot, cog, follow=True)
    await controls.refresh_controls(bot, bot.guild, marathon["id"])

    said = await pressed(bot, marathon, "spotlight", "off")

    assert said.ok and said.message == (
        "**AGDQ 2027** will not spotlight twitch.tv/rpglimitbreak after all — the start that "
        "was set is cancelled."
    )
    assert (await fresh(bot, marathon))["spotlight_mode"] == "off"
    lit = await channel_by_id(bot.db, row["id"])
    assert (lit["spotlight"], lit["expires_at"], lit["spotlit_by_marathon"]) == (0, None, None)
    assert spot_label(controls_in(the_thread(bot))[0]) == OFF_SWITCH
    cog.clock = lambda: NOW + timedelta(minutes=5000)
    assert await cog.follow_spotlight(bot.guild, marathon["id"]) is None
    assert (await channel_by_id(bot.db, row["id"]))["spotlight"] == 0


@pytest.mark.parametrize("to", ["off", "cancel"])
async def test_turn_off_before_the_show_leaves_a_staff_spotlight_alone(bot, cog, to):
    row, marathon = await far_off_marathon(bot, cog, follow=True)
    await change_spotlight(
        bot, bot.guild, FakeActor(), row["id"], spotlight=True, expires_at=at(200)
    )
    staff = await channel_by_id(bot.db, row["id"])
    assert staff["spotlight"] == 1 and staff["spotlit_by_marathon"] is None

    said = await pressed(bot, marathon, "spotlight", to)

    assert said.ok and (await fresh(bot, marathon))["spotlight_mode"] == "off"
    assert (await channel_by_id(bot.db, row["id"]))["spotlight"] == 1


async def test_turn_on_before_the_lead_window_with_nothing_to_start_it_is_refused(bot, cog):
    row, marathon = await far_off_marathon(bot, cog)
    await bot.store.set(GUILD, "marathon_spotlight", False)

    said = await pressed(bot, marathon, "spotlight", "on")

    assert not said.ok and said.code == "cannot_wait"
    assert "its spotlight cannot start itself" in said.message
    assert (await fresh(bot, marathon))["spotlight_mode"] == "off"
    assert (await channel_by_id(bot.db, row["id"]))["spotlight"] == 0


async def test_a_kept_spotlight_before_the_lead_window_is_still_refused_on_stop(bot, cog):
    row = await gdq_row(bot)
    marathon = await tracked_marathon(bot, cog, channel=row)
    await update_marathon(bot.db, marathon["id"], starts_at=at(5000), ends_at=at(6000))
    await controls.refresh_controls(bot, bot.guild, marathon["id"])
    assert spot_label(controls_in(the_thread(bot))[0]) is None

    said = await pressed(bot, marathon, "spotlight", "off")

    assert not said.ok and said.code == "kept"
    assert (await channel_by_id(bot.db, row["id"]))["spotlight"] == 1


# --- the ping button ----------------------------------------------------------------------------


async def test_the_ping_button_flips_ping_role_through_its_writer_and_relabels(bot, cog):
    marathon = await tracked_marathon(bot, cog)
    message = controls_in(the_thread(bot))[0]
    assert (await fresh(bot, marathon))["ping_role"] == 0

    said = await pressed(bot, marathon, "ping", "on")

    assert said.ok and "pings again" in said.message
    assert (await fresh(bot, marathon))["ping_role"] == 1
    assert labels(message)[2] == "Ping the marathon role: on · turn off"
    assert buttons(message)[2].custom_id == f"marathon:controls:{marathon['id']}:ping:off"
    logged = await details_of(bot.db, "marathon.ping_role_set")
    assert (logged["from"], logged["to"]) == (False, True)

    again = await pressed(bot, marathon, "ping", "off")
    assert again.ok and (await fresh(bot, marathon))["ping_role"] == 0
    assert labels(message)[2] == "Ping the marathon role: off · turn on"


async def test_a_ping_change_from_the_drawer_re_renders_the_ping_button(bot, cog):
    from black_bloc.cogs.content.marathon_ping import set_ping_role

    marathon = await tracked_marathon(bot, cog)
    message = controls_in(the_thread(bot))[0]

    await set_ping_role(bot, bot.guild, FakeActor(), marathon, "on", via="website")

    assert labels(message)[2] == "Ping the marathon role: on · turn off"


async def test_the_ping_labels_are_keys(bot, cog):
    marathon = await tracked_marathon(bot, cog)
    message = controls_in(the_thread(bot))[0]
    await bot.store.set(GUILD, "marathon_controls_ping_off", "Role pings: off")

    await controls.refresh_controls(bot, bot.guild, marathon["id"])

    assert labels(message)[2] == "Role pings: off"


# --- the BaF event button -----------------------------------------------------------------------


def baf_label(message):
    return labels(message)[-1]


def baf_id(message):
    return buttons(message)[-1].custom_id


async def test_the_baf_event_button_says_its_reading_and_moves_once_each_way(bot, cog):
    marathon = await tracked_marathon(bot, cog)
    message = controls_in(the_thread(bot))[0]
    assert baf_label(message) == "BaF event: no (1 of 5 runs) · say yes"
    assert baf_id(message) == f"marathon:controls:{marathon['id']}:baf:yes"

    said = await pressed(bot, marathon, "baf", "yes")

    assert said.ok and (await fresh(bot, marathon))["baf_event"] == 1
    assert baf_label(message) == "BaF event: yes (staff) · clear"
    assert baf_id(message) == f"marathon:controls:{marathon['id']}:baf:follow"

    back = await pressed(bot, marathon, "baf", "follow")

    assert back.ok and (await fresh(bot, marathon))["baf_event"] is None
    assert baf_label(message) == "BaF event: no (1 of 5 runs) · say yes"


async def test_a_name_reading_says_say_no_and_a_second_press_forces_no(bot, cog):
    await bot.store.set(GUILD, "marathon_baf_event_names", "AGDQ")
    marathon = await tracked_marathon(bot, cog)
    message = controls_in(the_thread(bot))[0]
    assert baf_label(message) == "BaF event: yes (named AGDQ) · say no"

    await pressed(bot, marathon, "baf", "no")

    assert (await fresh(bot, marathon))["baf_event"] == 0
    assert baf_label(message) == "BaF event: no (staff) · clear"


async def test_a_leads_answer_reads_answered_and_the_button_clears_it(bot, cog):
    import json

    marathon = await tracked_marathon(bot, cog)
    asks = [{"message_id": 77, "answer": "yes", "answered_by": 1, "answered_at": NOW.isoformat()}]
    await update_marathon(bot.db, marathon["id"], baf_event_ask=json.dumps(asks))
    await controls.refresh_controls(bot, bot.guild, marathon["id"])
    message = controls_in(the_thread(bot))[0]
    assert baf_label(message) == "BaF event: yes (answered) · clear"
    assert baf_id(message) == f"marathon:controls:{marathon['id']}:baf:clear"

    said = await pressed(bot, marathon, "baf", "clear")

    assert said.ok
    assert baf_label(message) == "BaF event: no (1 of 5 runs) · say yes"


async def test_the_baf_event_labels_and_reasons_are_keys(bot, cog):
    marathon = await tracked_marathon(bot, cog)
    await bot.store.set(GUILD, "marathon_controls_baf_said_no", "Not BaF [{reason}]")
    await bot.store.set(GUILD, "marathon_controls_baf_runs", "{baf}/{runs}")

    await controls.refresh_controls(bot, bot.guild, marathon["id"])

    assert baf_label(controls_in(the_thread(bot))[0]) == "Not BaF [1/5]"


# --- the buttons ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("action", "column", "before", "after", "said"),
    [
        ("event", "event_mode", "none", "marathon", "now makes one event for the whole marathon"),
        ("ping", "ping_role", 0, 1, "pings again"),
    ],
    ids=["events-button", "ping-button"],
)
async def test_the_buttons_are_staff_only_and_rebuild_from_their_custom_id(
    bot, cog, proposals, action, column, before, after, said
):
    marathon = await tracked_marathon(bot, cog)
    custom = mtc.custom_id(marathon["id"], action, "on")
    button = await controls.ControlButton.from_custom_id(
        None, None, re.fullmatch(mtc.TEMPLATE, custom)
    )
    assert (button.marathon_id, button.action, button.to) == (marathon["id"], action, "on")

    bot.store.is_staff = lambda member: False
    stranger = FakeInteraction(bot, Member(42), bot.guild)
    await button.on_click(stranger)
    assert "staff only" in stranger.sent
    assert (await fresh(bot, marathon))[column] == before

    bot.store.is_staff = lambda member: True
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    await button.on_click(lead)
    assert said in lead.sent
    assert (await fresh(bot, marathon))[column] == after


# --- the thread moves ----------------------------------------------------------------------------


async def test_a_moved_thread_carries_a_fresh_pinned_control_message(bot, cog):
    marathon = await tracked_marathon(bot, cog, channel=await quiet_row(bot))
    old = the_thread(bot)
    threading(bot, THREADS)
    await bot.store.set(GUILD, "marathon_thread_channel_id", THREADS)

    await cog.tick_once()

    new = bot.guild.channels[THREADS].threads[0]
    moved = controls_in(new)
    assert len(moved) == 1 and moved[0].pinned and new.messages[1] is moved[0]
    assert (await fresh(bot, marathon))["controls_message_id"] == moved[0].id
    assert old.archived and len(controls_in(old)) == 1

    before = len(moved[0].edits)
    await cog.tick_once()
    assert len(moved[0].edits) == before and len(controls_in(new)) == 1


async def test_an_untracked_marathon_keeps_its_message_and_it_is_not_edited(bot, cog, proposals):
    marathon = await tracked_marathon(bot, cog)
    message = controls_in(the_thread(bot))[0]
    await inbox.untrack(bot, bot.guild, FakeActor(), marathon)
    edits = len(message.edits)

    await runev.set_event_mode(bot, bot.guild, FakeActor(), marathon, "runs")
    await cog.tick_once()

    assert len(message.edits) == edits and the_thread(bot).archived


async def logged(bot, kind):
    import json

    cur = await bot.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id", (kind,)
    )
    return [json.loads(row["details"]) for row in await cur.fetchall()]


# --- the retired buttons -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("action", "to", "said"),
    [
        ("hosts", "on", "hosts are always found now"),
        ("hosts", "off", "hosts are always found now"),
        ("hostevents", "on", "follow BaF run/host events in the marathon's drawer on the site"),
        ("hostevents", "off", "follow BaF run/host events in the marathon's drawer on the site"),
        ("runs", "on", "BaF run/host events left the thread controls"),
        ("runs", "off", "BaF run/host events left the thread controls"),
        ("overlay", "on", "Event schedule left the thread controls"),
        ("overlay", "off", "Event schedule left the thread controls"),
        ("highlight", "on", "Auto-highlight is part of Runner announcements now"),
        ("highlight", "off", "Auto-highlight is part of Runner announcements now"),
    ],
)
async def test_a_retired_button_answers_in_words_and_changes_nothing(bot, cog, action, to, said):
    marathon = await tracked_marathon(bot, cog)
    message = controls_in(the_thread(bot))[0]
    before = dict(await fresh(bot, marathon))

    answered = await pressed(bot, marathon, action, to)

    assert not answered.ok and said in answered.message
    after = dict(await fresh(bot, marathon))
    assert after == before
    assert len(labels(message)) == 6


async def test_a_removed_host_button_clicked_in_discord_answers_in_words(bot, cog):
    marathon = await tracked_marathon(bot, cog)
    button = controls.ControlButton(marathon["id"], "hostevents", "on")
    interaction = FakeInteraction(bot, FakeActor(), bot.guild)
    await button.on_click(interaction)
    assert "BaF run/host events" in interaction.sent


async def test_a_host_button_rebuilds_from_its_custom_id():
    found = re.fullmatch(mtc.TEMPLATE, "marathon:controls:12:hostevents:off")
    assert found and (found["action"], found["to"]) == ("hostevents", "off")


async def test_a_rename_re_renders_the_controls_and_the_inbox_post_but_not_the_threads_title(
    bot, cog
):
    from black_bloc.cogs.content.marathon import rename_marathon

    marathon = await tracked_marathon(bot, cog, channel=await quiet_row(bot))
    thread = the_thread(bot)
    message = controls_in(thread)[0]
    opening = thread.messages[0].content
    assert "**AGDQ 2027** is not a BaF event" in message.content

    soul = "AGDQ 2027: Soul Train"
    done = await rename_marathon(bot, bot.guild, FakeActor(), marathon, soul, None)
    assert done.ok

    assert "**AGDQ 2027: Soul Train** is not a BaF event" in message.content
    assert thread.messages[0].content == opening
    await cog.tick_once()
    assert controls_in(thread) == [message]
    inbox_thread = bot.guild.channels[EVENTS].threads[0]
    posted = [one for one in inbox_thread.messages if one.embeds]
    assert [one.embeds[-1].title for one in posted] == ["AGDQ 2027: Soul Train"]
    assert thread.name == "AGDQ 2027"


# --- the Marathon tracker link ------------------------------------------------------------------


def link_of(message):
    return [one for one in buttons(message) if getattr(one, "url", None)]


async def test_the_controls_carry_one_link_to_the_marathons_tracker_page(bot, cog):
    marathon = await tracked_marathon(bot, cog, channel=await quiet_row(bot))
    message = controls_in(the_thread(bot))[0]

    found = link_of(message)

    assert [one.label for one in found] == ["Marathon tracker ↗"]
    assert found[0].url == f"{bot.settings.origin}/schedule.html#marathon-{marathon['id']}"
    assert [one for one in buttons(message) if one.row == 1][0] is found[0]
    assert len(buttons(message)) <= 25 and not found[0].custom_id


async def test_the_link_label_is_a_key_and_a_posted_message_takes_it_on_the_tick(bot, cog):
    await tracked_marathon(bot, cog, channel=await quiet_row(bot))
    await cog.tick_once()
    message = controls_in(the_thread(bot))[0]
    before = len(message.edits)

    await bot.store.set(GUILD, "marathon_controls_tracker", "Open the tracker")
    await cog.tick_once()

    assert [one.label for one in link_of(message)] == ["Open the tracker"]
    assert len(message.edits) == before + 1
    await cog.tick_once()
    assert len(message.edits) == before + 1


async def test_controls_posted_before_the_link_existed_gain_it_on_the_next_tick(bot, cog):
    marathon = await tracked_marathon(bot, cog, channel=await quiet_row(bot))
    message = controls_in(the_thread(bot))[0]
    content, shown, said = await controls.rendered(bot, bot.guild, marathon)
    await message.edit(content=content, view=controls.view_of(marathon["id"], shown, said))
    controls.shown_cache(cog)[int(marathon["id"])] = (
        int(marathon["thread_id"]),
        int(message.id),
        (content, shown, said),
    )
    assert link_of(message) == []

    await cog.tick_once()

    assert [one.label for one in link_of(message)] == ["Marathon tracker ↗"]


async def test_the_host_announcements_button_moves_the_marathons_own_switch(bot, cog):
    marathon = await tracked_marathon(bot, cog, channel=await quiet_row(bot))
    message = the_thread(bot).messages[1]
    assert "Host announcements: off · turn on" in labels(message)

    on = await pressed(bot, marathon, mtc.HOST_ANNOUNCE, mtc.ON)

    assert on.ok and "announces its BaF hosts publicly now" in on.message
    assert (await fresh(bot, marathon))["host_announcements"] == 1
    assert "Host announcements: on · turn off" in labels(message)
    assert f"marathon:controls:{marathon['id']}:hostannounce:off" in [
        one.custom_id for one in buttons(message)
    ]
    logged = await details_of(bot.db, "marathon.host_announcements_set")
    assert (logged["from"], logged["to"], logged["via"]) == (None, True, "discord")
    off = await pressed(bot, marathon, mtc.HOST_ANNOUNCE, mtc.OFF)
    assert off.ok and "no longer announces its BaF hosts" in off.message
    assert (await fresh(bot, marathon))["host_announcements"] == 0
    assert (await fresh(bot, marathon))["announcements"] is None


async def test_the_host_events_retired_answer_is_a_key(bot, cog):
    marathon = await tracked_marathon(bot, cog)
    await bot.store.set(GUILD, "marathon_host_events_gone_said", "Host events: see the drawer.")

    answered = await pressed(bot, marathon, "hostevents", "on")

    assert not answered.ok and answered.message == "Host events: see the drawer."
