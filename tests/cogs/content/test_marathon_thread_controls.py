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


# --- the message --------------------------------------------------------------------------------


async def test_track_posts_one_pinned_control_message_right_after_the_opening(bot, cog):
    marathon = await tracked_marathon(bot, cog, channel=await quiet_row(bot))

    thread = the_thread(bot)
    assert thread.messages[0].content.startswith("AGDQ 2027 — tracked by")
    message = thread.messages[1]
    assert controls_in(thread) == [message] and message.pinned
    assert marathon["controls_message_id"] == message.id
    assert message.content.startswith("Staff: these buttons set **AGDQ 2027**'s events")
    assert labels(message) == [
        "Marathon event: off · turn on",
        "BaF run events: off · turn on",
        "Spotlight: on · stop",
        "Auto-highlight BaF runners when live: off · turn on",
        "Ping the marathon role: off · turn on",
    ]
    ids = [one.custom_id for one in buttons(message)]
    assert ids == [
        f"marathon:controls:{marathon['id']}:event:on",
        f"marathon:controls:{marathon['id']}:runs:on",
        f"marathon:controls:{marathon['id']}:spotlight:off",
        f"marathon:controls:{marathon['id']}:highlight:on",
        f"marathon:controls:{marathon['id']}:ping:on",
    ]
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


async def test_the_help_line_and_labels_are_keys_and_an_edit_re_renders(bot, cog):
    await tracked_marathon(bot, cog, channel=await quiet_row(bot))
    await bot.store.set(GUILD, "marathon_controls_event_off", "Whole-marathon event: off")
    await bot.store.set(GUILD, "marathon_controls_help", "Controls for {marathon}.")

    await cog.tick_once()

    message = controls_in(the_thread(bot))[0]
    assert labels(message)[0] == "Whole-marathon event: off"
    assert message.content == "Controls for AGDQ 2027."


# --- the events buttons -------------------------------------------------------------------------


async def test_each_events_button_moves_one_half_through_set_event_mode(
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
    assert labels(message)[:2] == ["Marathon event: on · turn off", "BaF run events: off · turn on"]
    await pressed(bot, marathon, "runs", "on")
    assert (await fresh(bot, marathon))["event_mode"] == "both"
    await pressed(bot, marathon, "event", "off")
    assert (await fresh(bot, marathon))["event_mode"] == "runs"
    assert labels(message)[:2] == ["Marathon event: off · turn on", "BaF run events: on · turn off"]
    await pressed(bot, marathon, "runs", "off")
    assert (await fresh(bot, marathon))["event_mode"] == "none"

    assert seen == ["marathon", "both", "runs", "none"]
    moves = [(one["from"], one["to"]) for one in await logged(bot, "marathon.event_mode_set")]
    assert moves == [
        ("none", "marathon"),
        ("marathon", "both"),
        ("both", "runs"),
        ("runs", "none"),
    ]


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
    assert labels(message)[1] == "BaF run events: on · turn off"

    await make_event_now(bot, bot.guild, FakeActor(), await fresh(bot, marathon))
    assert labels(message)[0] == "Marathon event: on · turn off"


# --- the spotlight button -----------------------------------------------------------------------


async def test_stop_turns_the_row_off_as_staff_off_does_and_the_marathon_stops_following(bot, cog):
    row = await quiet_row(bot)
    marathon = await tracked_marathon(bot, cog, channel=row)
    assert (await channel_by_id(bot.db, row["id"]))["spotlit_by_marathon"] == marathon["id"]

    said = await pressed(bot, marathon, "spotlight", "off")

    assert said.ok and "**AGDQ 2027** will not spotlight it again." in said.message
    lit = await channel_by_id(bot.db, row["id"])
    assert (lit["spotlight"], lit["expires_at"], lit["spotlit_by_marathon"]) == (0, None, None)
    assert (await fresh(bot, marathon))["spotlight_mode"] == "off"
    updated = await details_of(bot.db, "golive.spotlight_updated")
    assert updated["spotlight"] == 0 and updated["spotlight_id"] == row["id"]
    assert labels(controls_in(the_thread(bot))[0])[2] == "Spotlight: off · start"


async def test_stop_on_a_marathon_not_in_reach_still_sets_its_follow_off(bot, cog):
    row = await quiet_row(bot)
    marathon = await tracked_marathon(bot, cog, channel=row)
    await update_marathon(bot.db, marathon["id"], starts_at=at(5000), ends_at=at(6000))

    await pressed(bot, marathon, "spotlight", "off")

    assert (await fresh(bot, marathon))["spotlight_mode"] == "off"
    assert (await channel_by_id(bot.db, row["id"]))["spotlight"] == 0


async def test_start_holds_the_row_for_this_marathon_and_the_lift_ends_it_at_span_end_plus_tail(
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
    assert labels(controls_in(the_thread(bot))[0])[2] == "Spotlight: on · stop"

    cog.clock = lambda: NOW + timedelta(minutes=215)
    assert await settle_held(bot, bot.guild, lit) == "kept"
    cog.clock = lambda: NOW + timedelta(minutes=270)
    assert await settle_held(bot, bot.guild, lit) == "lifted"
    assert (await channel_by_id(bot.db, row["id"]))["spotlight"] == 0
    assert labels(controls_in(the_thread(bot))[0])[2] == "Spotlight: off · start"


async def test_start_after_a_staff_off_sets_the_follow_back_and_the_follow_spotlights_it(bot, cog):
    row = await quiet_row(bot)
    marathon = await tracked_marathon(bot, cog, channel=row)
    await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "spotlight_off")
    assert (await fresh(bot, marathon))["spotlight_mode"] == "off"
    assert labels(controls_in(the_thread(bot))[0])[2] == "Spotlight: off · start"

    said = await pressed(bot, marathon, "spotlight", "on")

    assert (await fresh(bot, marathon))["spotlight_mode"] == "follow"
    lit = await channel_by_id(bot.db, row["id"])
    assert (lit["spotlight"], lit["spotlit_by_marathon"]) == (1, marathon["id"])
    assert "spotlights its channel while it runs again" in said.message
    assert labels(controls_in(the_thread(bot))[0])[2] == "Spotlight: on · stop"


async def test_start_with_no_span_ahead_is_refused_in_words(bot, cog):
    await bot.store.set(GUILD, "marathon_spotlight", False)
    row = await quiet_row(bot)
    marathon = await tracked_marathon(bot, cog, channel=row)
    cog.clock = lambda: NOW + timedelta(minutes=9000)

    said = await pressed(bot, marathon, "spotlight", "on")

    assert not said.ok and said.code == "no_end" and "no end to hold the spotlight" in said.message
    assert (await channel_by_id(bot.db, row["id"]))["spotlight"] == 0


async def test_a_kept_spotlight_shows_kept_and_refuses_in_words(bot, cog):
    row = await gdq_row(bot)
    marathon = await tracked_marathon(bot, cog, channel=row)
    message = controls_in(the_thread(bot))[0]
    assert labels(message)[2] == "Spotlight: kept (permanent)"
    assert not buttons(message)[2].disabled

    said = await pressed(bot, marathon, "spotlight", "off")

    assert not said.ok and said.code == "kept" and "kept for ever" in said.message
    lit = await channel_by_id(bot.db, row["id"])
    assert (lit["spotlight"], lit["expires_at"]) == (1, None)
    assert (await fresh(bot, marathon))["spotlight_mode"] in (None, "follow")


async def test_no_channel_row_shows_the_button_disabled_with_a_key_sentence(bot, cog):
    marathon = await tracked_marathon(bot, cog)
    message = controls_in(the_thread(bot))[0]

    assert labels(message)[2] == "Spotlight: no channel"
    assert buttons(message)[2].disabled
    assert "has no channel yet, so there is no spotlight to start" in message.content
    said = await pressed(bot, marathon, "spotlight", "on")
    assert not said.ok and said.code == "no_channel"


async def test_a_go_live_change_to_the_row_re_renders_the_message(bot, cog):
    row = await quiet_row(bot)
    await tracked_marathon(bot, cog, channel=row)
    message = controls_in(the_thread(bot))[0]

    await change_spotlight(bot, bot.guild, FakeActor(), row["id"], expires_at=None)

    assert labels(message)[2] == "Spotlight: kept (permanent)"


async def test_the_follow_switch_from_the_drawer_re_renders_the_message(bot, cog):
    row = await quiet_row(bot)
    marathon = await tracked_marathon(bot, cog, channel=row)
    message = controls_in(the_thread(bot))[0]

    await set_spotlight_mode(bot, bot.guild, FakeActor(), marathon, "off", via="website")

    assert labels(message)[2] == "Spotlight: off · start"


# --- the ping button ----------------------------------------------------------------------------


async def test_the_fifth_button_flips_ping_role_through_its_writer_and_relabels(bot, cog):
    marathon = await tracked_marathon(bot, cog)
    message = controls_in(the_thread(bot))[0]
    assert (await fresh(bot, marathon))["ping_role"] == 0

    said = await pressed(bot, marathon, "ping", "on")

    assert said.ok and "pings again" in said.message
    assert (await fresh(bot, marathon))["ping_role"] == 1
    assert labels(message)[4] == "Ping the marathon role: on · turn off"
    assert buttons(message)[4].custom_id == f"marathon:controls:{marathon['id']}:ping:off"
    logged = await details_of(bot.db, "marathon.ping_role_set")
    assert (logged["from"], logged["to"]) == (False, True)

    again = await pressed(bot, marathon, "ping", "off")
    assert again.ok and (await fresh(bot, marathon))["ping_role"] == 0
    assert labels(message)[4] == "Ping the marathon role: off · turn on"


async def test_a_ping_change_from_the_drawer_re_renders_the_fifth_button(bot, cog):
    from black_bloc.cogs.content.marathon_ping import set_ping_role

    marathon = await tracked_marathon(bot, cog)
    message = controls_in(the_thread(bot))[0]

    await set_ping_role(bot, bot.guild, FakeActor(), marathon, "on", via="website")

    assert labels(message)[4] == "Ping the marathon role: on · turn off"


async def test_the_ping_labels_are_keys(bot, cog):
    marathon = await tracked_marathon(bot, cog)
    message = controls_in(the_thread(bot))[0]
    await bot.store.set(GUILD, "marathon_controls_ping_off", "Role pings: off")

    await controls.refresh_controls(bot, bot.guild, marathon["id"])

    assert labels(message)[4] == "Role pings: off"


async def test_the_ping_button_is_staff_only(bot, cog):
    marathon = await tracked_marathon(bot, cog)
    button = await controls.ControlButton.from_custom_id(
        None, None, re.fullmatch(mtc.TEMPLATE, mtc.custom_id(marathon["id"], "ping", "on"))
    )
    bot.store.is_staff = lambda member: False
    stranger = FakeInteraction(bot, Member(42), bot.guild)
    await button.on_click(stranger)
    assert "staff only" in stranger.sent and (await fresh(bot, marathon))["ping_role"] == 0

    bot.store.is_staff = lambda member: True
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    await button.on_click(lead)
    assert "pings again" in lead.sent and (await fresh(bot, marathon))["ping_role"] == 1


# --- the buttons ---------------------------------------------------------------------------------


async def test_the_buttons_are_staff_only_and_rebuild_from_their_custom_id(bot, cog, proposals):
    marathon = await tracked_marathon(bot, cog)
    custom = mtc.custom_id(marathon["id"], "event", "on")
    button = await controls.ControlButton.from_custom_id(
        None, None, re.fullmatch(mtc.TEMPLATE, custom)
    )
    assert (button.marathon_id, button.action, button.to) == (marathon["id"], "event", "on")

    bot.store.is_staff = lambda member: False
    stranger = FakeInteraction(bot, Member(42), bot.guild)
    await button.on_click(stranger)
    assert "staff only" in stranger.sent
    assert (await fresh(bot, marathon))["event_mode"] == "none"

    bot.store.is_staff = lambda member: True
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    await button.on_click(lead)
    assert "now makes one event for the whole marathon" in lead.sent
    assert (await fresh(bot, marathon))["event_mode"] == "marathon"


async def test_the_buttons_outlive_a_restart():
    registered = []
    made = Marathons.__new__(Marathons)
    made.bot = type("Bot", (), {"db": type("Db", (), {"is_connected": False})()})()
    made.bot.add_dynamic_items = lambda *items: registered.extend(items)
    await Marathons.cog_load(made)
    assert controls.ControlButton in registered


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
