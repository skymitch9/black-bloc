# ruff: noqa: F401, F811
import re
from datetime import timedelta

import pytest

from black_bloc import marathon_public as mp
from black_bloc import marathon_thread_controls as mtc
from black_bloc.cogs.content import marathon_public as public
from black_bloc.cogs.content import marathon_thread_controls as controls
from black_bloc.cogs.content.marathon import (
    Marathons,
    create_marathon,
    get_marathon,
    refresh_marathon,
    update_marathon,
)
from tests.cogs.content.test_marathon import (
    FAN_ROLE,
    NOW,
    URL,
    FakeClient,
    Member,
    a_run,
    bot,
    cog,
    threading,
)
from tests.cogs.content.test_marathon_runner_posts import (
    EVENTS,
    SKY_RUN,
    events_room,
    follow,
    fresh,
    run_of,
    runner_posts,
    the_thread,
    tracked,
)
from tests.cogs.content.test_spotlight import (
    CHANNEL,
    GUILD,
    LOG_CHANNEL,
    FakeActor,
    FakeChannel,
    FakeInteraction,
    details_of,
    kinds,
)

HIGHLIGHTS = 444


@pytest.fixture(autouse=True)
def named(bot):
    bot.guild.channels[CHANNEL].name = "go-live"


def current_view(message):
    for edit in reversed(message.edits):
        if "view" in edit:
            return edit["view"]
    return message.kwargs.get("view")


def button_on(message):
    view = current_view(message)
    if view is None:
        return None
    found = [getattr(one, "item", one) for one in view.children]
    return found[0] if found else None


def public_posts(bot, channel_id=CHANNEL):
    return [one for one in bot.guild.channels[channel_id].messages if "**Sky**" in one.content]


async def ready(bot, cog):
    marathon = await tracked(bot)
    await follow(bot, cog, marathon)
    return await fresh(bot, marathon)


async def pressed(bot, marathon, row, to, actor=None):
    return await public.press(bot, bot.guild, actor or FakeActor(), marathon["id"], row["id"], to)


# --- the button on the runner post --------------------------------------------------------------


async def test_each_runner_post_carries_highlight_naming_the_public_channel(bot, cog):
    marathon = await ready(bot, cog)
    post = runner_posts(the_thread(bot))[0]
    row = await run_of(bot, marathon, "Super Metroid")

    button = button_on(post)
    assert button.label == "Highlight in #go-live"
    assert button.custom_id == f"marathon:highlight:{marathon['id']}:{row['id']}:post"
    assert public_posts(bot) == []


async def test_highlight_posts_publicly_now_and_the_button_becomes_remove(bot, cog):
    marathon = await ready(bot, cog)
    row = await run_of(bot, marathon, "Super Metroid")

    said = await pressed(bot, marathon, row, mp.POST)

    assert said.ok and "highlight is up in <#111>" in said.message
    posts = public_posts(bot)
    assert len(posts) == 1
    assert "**Super Metroid**" in posts[0].content and "coming up" in posts[0].content
    assert "on **SS4C**" in posts[0].content
    mentions = posts[0].kwargs["allowed_mentions"]
    assert mentions.users is False and mentions.roles is False and mentions.everyone is False
    row = await run_of(bot, marathon, "Super Metroid")
    assert (row["public_message_id"], row["public_channel_id"], row["public_removed"]) == (
        posts[0].id,
        CHANNEL,
        0,
    )
    button = button_on(runner_posts(the_thread(bot))[0])
    assert button.label == "Remove the highlight" and button.custom_id.endswith(":remove")
    assert (await details_of(bot.db, "marathon.public_highlight_posted"))["run_id"] == row["id"]

    again = await pressed(bot, marathon, row, mp.POST)
    assert "already up" in again.message and len(public_posts(bot)) == 1


async def test_the_highlight_follows_the_run_as_its_slot_moves_and_it_goes_live(bot, cog):
    marathon = await ready(bot, cog)
    await pressed(bot, marathon, await run_of(bot, marathon, "Super Metroid"), mp.POST)
    post = public_posts(bot)[0]
    cog.client.runs_given = [
        a_run(3, 75, game="Super Metroid", people=SKY_RUN),
        a_run(4, 90, game="Kirby Air Riders"),
    ]

    await refresh_marathon(bot, bot.guild, marathon)

    assert f"<t:{int((NOW + timedelta(minutes=75)).timestamp())}:f>" in post.content
    assert post.edits[-1]["allowed_mentions"].roles is False
    cog.clock = lambda: NOW + timedelta(minutes=76)
    await follow(bot, cog, marathon)
    assert "on now" in post.content and len(public_posts(bot)) == 1
    assert "marathon.public_highlight_edited" in await kinds(bot.db)


async def test_remove_edits_it_to_the_key_sentence_and_stops_updating_it(bot, cog):
    marathon = await ready(bot, cog)
    row = await run_of(bot, marathon, "Super Metroid")
    await pressed(bot, marathon, row, mp.POST)
    post = public_posts(bot)[0]

    said = await pressed(bot, marathon, row, mp.REMOVE)

    assert "taken down" in said.message
    assert post.content == "Staff took down the highlight for **Sky** on **SS4C**."
    assert not post.deleted
    row = await run_of(bot, marathon, "Super Metroid")
    assert row["public_removed"] == 1 and row["public_message_id"] == post.id
    edits = len(post.edits)
    cog.clock = lambda: NOW + timedelta(minutes=31)
    await follow(bot, cog, marathon)
    assert len(post.edits) == edits and "took down" in post.content
    assert button_on(runner_posts(the_thread(bot))[0]).label == "Highlight in #go-live"
    removed = await details_of(bot.db, "marathon.public_highlight_removed")
    assert removed["edited"] is True

    nothing = await pressed(bot, marathon, row, mp.REMOVE)
    assert "nothing to take down" in nothing.message


async def test_highlight_after_remove_puts_the_same_message_back(bot, cog):
    marathon = await ready(bot, cog)
    row = await run_of(bot, marathon, "Super Metroid")
    await pressed(bot, marathon, row, mp.POST)
    await pressed(bot, marathon, row, mp.REMOVE)
    post = public_posts(bot)[0]

    said = await pressed(bot, marathon, await run_of(bot, marathon, "Super Metroid"), mp.POST)

    assert said.ok and len(public_posts(bot)) == 1
    assert "**Super Metroid**" in post.content
    assert (await run_of(bot, marathon, "Super Metroid"))["public_removed"] == 0
    assert "marathon.public_highlight_restored" in await kinds(bot.db)


# --- the auto switch ----------------------------------------------------------------------------


async def test_with_the_switch_off_going_live_posts_nothing_public(bot, cog):
    marathon = await ready(bot, cog)
    assert marathon["public_highlight"] == 0

    cog.clock = lambda: NOW + timedelta(minutes=31)
    await follow(bot, cog, marathon)

    assert (await run_of(bot, marathon, "Super Metroid"))["state"] == "live"
    assert public_posts(bot) == []


async def test_with_the_switch_on_going_live_posts_the_highlight_at_the_shoutout(bot, cog):
    marathon = await ready(bot, cog)
    done = await public.set_public_highlight(bot, bot.guild, FakeActor(), marathon, True)
    assert done.ok and "the moment it goes live" in done.message

    cog.clock = lambda: NOW + timedelta(minutes=31)
    await follow(bot, cog, marathon)

    posts = public_posts(bot)
    assert len(posts) == 1 and "on now" in posts[0].content
    assert (await details_of(bot.db, "marathon.public_highlight_posted"))["auto"] is True


async def test_the_switch_never_puts_back_a_highlight_staff_took_down(bot, cog):
    marathon = await ready(bot, cog)
    row = await run_of(bot, marathon, "Super Metroid")
    await pressed(bot, marathon, row, mp.POST)
    await pressed(bot, marathon, row, mp.REMOVE)
    await public.set_public_highlight(bot, bot.guild, FakeActor(), marathon, True)

    await public.auto_highlight(
        cog, bot.guild, await fresh(bot, marathon), await run_of(bot, marathon, "Super Metroid")
    )

    assert len(public_posts(bot)) == 1 and "took down" in public_posts(bot)[0].content


async def test_a_new_marathon_copies_the_default_and_the_switch_writes_both_ways(bot, cog):
    await bot.store.set(GUILD, "marathon_public_highlight_default", True)
    made = await create_marathon(bot, bot.guild, FakeActor(), name="SS4C", url=URL)
    assert made.value["public_highlight"] == 1

    off = await public.set_public_highlight(bot, bot.guild, FakeActor(), made.value, "off")
    same = await public.set_public_highlight(bot, bot.guild, FakeActor(), made.value, False)
    bad = await public.set_public_highlight(bot, bot.guild, FakeActor(), made.value, "loud")

    assert off.ok and (await fresh(bot, made.value))["public_highlight"] == 0
    assert "already works that way" in same.message
    assert not bad.ok and bad.code == "bad_public_highlight"
    logged = await details_of(bot.db, "marathon.public_highlight_set")
    assert (logged["from"], logged["to"]) == (True, False)


async def test_the_fourth_control_button_flips_the_switch_and_relabels(bot, cog):
    marathon = await ready(bot, cog)

    said = await controls.press(bot, bot.guild, FakeActor(), marathon["id"], mtc.HIGHLIGHT, "on")

    assert said.ok and (await fresh(bot, marathon))["public_highlight"] == 1
    message = the_thread(bot).messages[1]
    labels = [getattr(one, "item", one).label for one in current_view(message).children]
    assert labels[3] == "Auto-highlight BaF runners when live: on · turn off"


# --- pings, channel, shadow ---------------------------------------------------------------------


async def test_a_highlight_pings_the_role_only_while_the_marathon_pings_roles(bot, cog):
    marathon = await ready(bot, cog)
    await update_marathon(bot.db, marathon["id"], ping_role=1)
    row = await run_of(bot, marathon, "Super Metroid")

    await pressed(bot, marathon, row, mp.POST)

    post = public_posts(bot)[0]
    assert post.content.startswith(f"<@&{FAN_ROLE}>")
    mentions = post.kwargs["allowed_mentions"]
    assert [one.id for one in mentions.roles] == [FAN_ROLE] and mentions.users is False
    assert (await details_of(bot.db, "marathon.public_highlight_posted"))["pinged"] is True


async def test_changing_the_channel_key_relabels_the_button_and_the_next_post_goes_there(bot, cog):
    marathon = await ready(bot, cog)
    room = FakeChannel(HIGHLIGHTS)
    room.name = "baf-highlights"
    bot.guild.channels[HIGHLIGHTS] = room
    await bot.store.set(GUILD, "marathon_public_channel_id", HIGHLIGHTS)

    await follow(bot, cog, marathon)

    post = runner_posts(the_thread(bot))[0]
    assert button_on(post).label == "Highlight in #baf-highlights"
    await pressed(bot, marathon, await run_of(bot, marathon, "Super Metroid"), mp.POST)
    assert public_posts(bot) == [] and len(public_posts(bot, HIGHLIGHTS)) == 1
    assert (await run_of(bot, marathon, "Super Metroid"))["public_channel_id"] == HIGHLIGHTS


async def test_no_public_channel_hides_the_button_and_refuses_in_words(bot, cog, monkeypatch):
    monkeypatch.setattr(public, "public_channel", lambda bot, guild_id: None)
    marathon = await ready(bot, cog)
    row = await run_of(bot, marathon, "Super Metroid")

    assert button_on(runner_posts(the_thread(bot))[0]) is None
    said = await pressed(bot, marathon, row, mp.POST)
    assert not said.ok and "no public channel" in said.message


async def test_shadow_sends_the_highlight_to_its_own_rehearsal_home_with_the_note(bot, cog):
    marathon = await ready(bot, cog)
    await bot.store.set(GUILD, "marathon_mode", "shadow")
    await bot.store.set(GUILD, "marathon_public_shadow_channel_id", LOG_CHANNEL)

    await pressed(bot, marathon, await run_of(bot, marathon, "Super Metroid"), mp.POST)

    assert public_posts(bot) == []
    copy = public_posts(bot, LOG_CHANNEL)[0]
    assert copy.content.startswith("Rehearsal — this is where it would go: <#111>")
    row = await run_of(bot, marathon, "Super Metroid")
    assert row["public_channel_id"] == LOG_CHANNEL
    logged = await details_of(bot.db, "marathon.would_post_public_highlight")
    assert logged["shadow_home"] == LOG_CHANNEL


# --- the button itself --------------------------------------------------------------------------


async def test_the_button_is_staff_only_and_rebuilds_from_its_custom_id(bot, cog):
    marathon = await ready(bot, cog)
    row = await run_of(bot, marathon, "Super Metroid")
    custom = mp.custom_id(marathon["id"], row["id"], mp.POST)
    button = await public.HighlightButton.from_custom_id(
        None, None, re.fullmatch(mp.TEMPLATE, custom)
    )
    assert (button.marathon_id, button.run_id, button.to) == (marathon["id"], row["id"], "post")

    bot.store.is_staff = lambda member: False
    stranger = FakeInteraction(bot, Member(42), bot.guild)
    await button.on_click(stranger)
    assert "staff only" in stranger.sent and public_posts(bot) == []

    bot.store.is_staff = lambda member: True
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    await button.on_click(lead)
    assert "highlight is up" in lead.sent and len(public_posts(bot)) == 1


async def test_the_button_outlives_a_restart():
    registered = []
    made = Marathons.__new__(Marathons)
    made.bot = type("Bot", (), {"db": type("Db", (), {"is_connected": False})()})()
    made.bot.add_dynamic_items = lambda *items: registered.extend(items)
    await Marathons.cog_load(made)
    assert public.HighlightButton in registered


async def test_after_a_restart_a_highlight_is_read_once_and_kept_up_to_date(bot, cog):
    marathon = await ready(bot, cog)
    await pressed(bot, marathon, await run_of(bot, marathon, "Super Metroid"), mp.POST)
    post = public_posts(bot)[0]
    restarted = Marathons(bot)
    restarted.client = cog.client
    restarted.clock = lambda: NOW + timedelta(minutes=31)
    bot.cogs["Marathons"] = restarted

    await restarted.tick_once()

    assert "on now" in post.content and len(public_posts(bot)) == 1
    assert button_on(runner_posts(the_thread(bot))[0]).label == "Remove the highlight"


async def test_a_highlight_a_person_deleted_is_forgotten_not_posted_again(bot, cog):
    marathon = await ready(bot, cog)
    await pressed(bot, marathon, await run_of(bot, marathon, "Super Metroid"), mp.POST)
    await public_posts(bot)[0].delete()
    cog.__dict__.get("public_sent", {}).clear()

    await follow(bot, cog, marathon)

    row = await run_of(bot, marathon, "Super Metroid")
    assert row["public_message_id"] is None and public_posts(bot) == []
    assert "marathon.public_highlight_lost" in await kinds(bot.db)
