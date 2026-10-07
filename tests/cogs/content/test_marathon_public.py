# ruff: noqa: F401, F811
import json
import re
from datetime import timedelta
from types import SimpleNamespace

import pytest

from black_bloc import marathon_hosts as mh
from black_bloc import marathon_public as mp
from black_bloc import marathon_thread_controls as mtc
from black_bloc.cogs.content import marathon_hosts as hosts
from black_bloc.cogs.content import marathon_public as public
from black_bloc.cogs.content import marathon_thread_controls as controls
from black_bloc.cogs.content.marathon import (
    Marathons,
    create_marathon,
    get_marathon,
    refresh_marathon,
    update_marathon,
    update_run,
)
from black_bloc.settings_store import SettingError
from tests.cogs.content.test_marathon import (
    FAN_ROLE,
    NOW,
    SKY,
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


OPT_OUT_LABEL = "Opt out of every run on this marathon"


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


async def highlighted(bot, cog, marathon, game="Super Metroid"):
    why, _channel = await public.post_highlight(
        cog, bot.guild, await fresh(bot, marathon), await run_of(bot, marathon, game)
    )
    assert why is None, why
    return public_posts(bot) or None


async def opted(bot, marathon):
    return json.loads((await fresh(bot, marathon))["announce_opt_out"] or "[]")


# --- the button on the runner post: opt out / opt back in ---------------------------------------


async def test_each_runner_post_carries_opt_out_and_it_posts_nothing(bot, cog):
    marathon = await ready(bot, cog)
    post = runner_posts(the_thread(bot))[0]
    row = await run_of(bot, marathon, "Super Metroid")

    button = button_on(post)
    assert button.label == OPT_OUT_LABEL
    assert button.custom_id == f"marathon:highlight:{marathon['id']}:{row['id']}:optout"
    assert public_posts(bot) == []


async def test_opt_out_answers_in_words_flips_the_button_and_opt_back_in_undoes_it(bot, cog):
    marathon = await ready(bot, cog)
    row = await run_of(bot, marathon, "Super Metroid")

    said = await pressed(bot, marathon, row, mp.OPT_OUT)

    assert said.ok and "is opted out of **SS4C**" in said.message
    assert await opted(bot, marathon) == [SKY] and public_posts(bot) == []
    button = button_on(runner_posts(the_thread(bot))[0])
    assert button.label == "Opt back in to this marathon" and button.custom_id.endswith(":optin")
    logged = await details_of(bot.db, "marathon.announce_opted_out")
    assert logged["members"] == [SKY] and logged["via"] == "discord"

    again = await pressed(bot, marathon, row, mp.OPT_OUT)
    assert again.ok and (await kinds(bot.db)).count("marathon.announce_opted_out") == 1

    back = await pressed(bot, marathon, row, mp.OPT_IN)
    assert back.ok and "is back in" in back.message and await opted(bot, marathon) == []
    assert button_on(runner_posts(the_thread(bot))[0]).label == OPT_OUT_LABEL
    assert public_posts(bot) == []


async def test_opting_out_takes_the_highlight_down_and_opting_in_puts_the_same_one_back(bot, cog):
    marathon = await ready(bot, cog)
    (post,) = await highlighted(bot, cog, marathon)
    row = await run_of(bot, marathon, "Super Metroid")

    await pressed(bot, marathon, row, mp.OPT_OUT)

    assert post.content == "Staff took down the highlight for **Sky** on **SS4C**."
    assert not post.deleted
    row = await run_of(bot, marathon, "Super Metroid")
    assert row["public_removed"] == 1 and row["public_message_id"] == post.id
    edits = len(post.edits)
    cog.clock = lambda: NOW + timedelta(minutes=31)
    await follow(bot, cog, marathon)
    assert len(post.edits) == edits and "took down" in post.content
    assert (await details_of(bot.db, "marathon.public_highlight_removed"))["edited"] is True

    await pressed(bot, marathon, row, mp.OPT_IN)

    assert len(public_posts(bot)) == 1 and "**Super Metroid**" in post.content
    assert (await run_of(bot, marathon, "Super Metroid"))["public_removed"] == 0
    assert (await details_of(bot.db, "marathon.public_highlight_restored"))["because"] == "opted_in"


async def test_the_highlight_follows_the_run_as_its_slot_moves_and_it_goes_live(bot, cog):
    marathon = await ready(bot, cog)
    (post,) = await highlighted(bot, cog, marathon)
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


async def test_a_button_posted_before_the_opt_out_still_answers_as_the_toggle(bot, cog):
    marathon = await ready(bot, cog)
    row = await run_of(bot, marathon, "Super Metroid")
    for old, word in ((mp.REMOVE, "opted out"), (mp.POST, "is back in")):
        custom = mp.custom_id(marathon["id"], row["id"], old)
        button = await public.HighlightButton.from_custom_id(
            None, None, re.fullmatch(mp.TEMPLATE, custom)
        )
        lead = FakeInteraction(bot, FakeActor(), bot.guild)
        await button.on_click(lead)
        assert word in lead.sent
    assert await opted(bot, marathon) == [] and public_posts(bot) == []


async def test_a_run_nobody_from_baf_is_on_is_refused_in_words(bot, cog):
    marathon = await ready(bot, cog)
    row = await run_of(bot, marathon, "Kirby Air Riders")
    said = await pressed(bot, marathon, row, mp.OPT_OUT)
    assert not said.ok and said.code == public.NOT_POSTABLE_CODE


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


@pytest.mark.parametrize("why", ["opted_out", "announcements_off"])
async def test_an_opted_out_runner_or_announcements_off_is_never_auto_highlighted(bot, cog, why):
    marathon = await ready(bot, cog)
    await public.set_public_highlight(bot, bot.guild, FakeActor(), marathon, True)
    if why == "opted_out":
        await pressed(bot, marathon, await run_of(bot, marathon, "Super Metroid"), mp.OPT_OUT)
    else:
        await hosts.set_switch(bot, bot.guild, FakeActor(), marathon, mh.ANNOUNCE, False)

    cog.clock = lambda: NOW + timedelta(minutes=31)
    await follow(bot, cog, marathon)

    assert (await run_of(bot, marathon, "Super Metroid"))["state"] == "live"
    assert public_posts(bot) == []


async def test_the_switch_never_puts_back_a_highlight_taken_down(bot, cog):
    marathon = await ready(bot, cog)
    await highlighted(bot, cog, marathon)
    await pressed(bot, marathon, await run_of(bot, marathon, "Super Metroid"), mp.OPT_OUT)
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

    (post,) = await highlighted(bot, cog, marathon)

    assert post.content.startswith(f"<@&{FAN_ROLE}>")
    mentions = post.kwargs["allowed_mentions"]
    assert [one.id for one in mentions.roles] == [FAN_ROLE] and mentions.users is False
    assert (await details_of(bot.db, "marathon.public_highlight_posted"))["pinged"] is True


async def test_changing_the_channel_key_sends_the_next_highlight_there(bot, cog):
    marathon = await ready(bot, cog)
    room = FakeChannel(HIGHLIGHTS)
    room.name = "baf-highlights"
    bot.guild.channels[HIGHLIGHTS] = room
    await bot.store.set(GUILD, "marathon_public_channel_id", HIGHLIGHTS)

    await follow(bot, cog, marathon)
    await highlighted(bot, cog, marathon)

    assert button_on(runner_posts(the_thread(bot))[0]).label == OPT_OUT_LABEL
    assert public_posts(bot) == [] and len(public_posts(bot, HIGHLIGHTS)) == 1
    assert (await run_of(bot, marathon, "Super Metroid"))["public_channel_id"] == HIGHLIGHTS


async def test_no_public_channel_posts_nothing_and_the_opt_out_still_works(bot, cog, monkeypatch):
    monkeypatch.setattr(public, "public_channel", lambda bot, guild_id: None)
    marathon = await ready(bot, cog)
    await public.set_public_highlight(bot, bot.guild, FakeActor(), marathon, True)
    cog.clock = lambda: NOW + timedelta(minutes=31)
    await follow(bot, cog, marathon)

    assert public_posts(bot) == []
    assert button_on(runner_posts(the_thread(bot))[0]).label == OPT_OUT_LABEL
    said = await pressed(bot, marathon, await run_of(bot, marathon, "Super Metroid"), mp.OPT_OUT)
    assert said.ok


async def test_shadow_sends_the_highlight_to_its_own_rehearsal_home_with_the_note(bot, cog):
    marathon = await ready(bot, cog)
    await bot.store.set(GUILD, "marathon_mode", "shadow")
    await bot.store.set(GUILD, "marathon_public_shadow_channel_id", LOG_CHANNEL)

    await highlighted(bot, cog, marathon)

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
    custom = mp.custom_id(marathon["id"], row["id"], mp.OPT_OUT)
    button = await public.HighlightButton.from_custom_id(
        None, None, re.fullmatch(mp.TEMPLATE, custom)
    )
    assert (button.marathon_id, button.run_id, button.to) == (marathon["id"], row["id"], "optout")

    bot.store.is_staff = lambda member: False
    stranger = FakeInteraction(bot, Member(42), bot.guild)
    await button.on_click(stranger)
    assert "staff only" in stranger.sent and await opted(bot, marathon) == []

    bot.store.is_staff = lambda member: True
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    await button.on_click(lead)
    assert "is opted out" in lead.sent and await opted(bot, marathon) == [SKY]
    assert public_posts(bot) == []


async def test_after_a_restart_a_highlight_is_read_once_and_kept_up_to_date(bot, cog):
    marathon = await ready(bot, cog)
    (post,) = await highlighted(bot, cog, marathon)
    restarted = Marathons(bot)
    restarted.client = cog.client
    restarted.clock = lambda: NOW + timedelta(minutes=31)
    bot.cogs["Marathons"] = restarted

    await restarted.tick_once()

    assert "on now" in post.content and len(public_posts(bot)) == 1
    assert button_on(runner_posts(the_thread(bot))[0]).label == OPT_OUT_LABEL


async def test_after_the_upgrade_the_posted_controls_and_runner_post_are_edited_not_resent(
    bot, cog
):
    marathon = await ready(bot, cog)
    thread = the_thread(bot)
    (post,) = runner_posts(thread)
    controls_message = thread.messages[1]
    row = await run_of(bot, marathon, "Super Metroid")
    old = f"marathon:highlight:{marathon['id']}:{row['id']}:post"
    post.components = [
        SimpleNamespace(children=[SimpleNamespace(custom_id=old, label="Highlight in #go-live")])
    ]
    count, post_edits, control_edits = len(thread.messages), len(post.edits), len(
        controls_message.edits
    )
    restarted = Marathons(bot)
    restarted.client = cog.client
    restarted.clock = cog.clock
    bot.cogs["Marathons"] = restarted

    await restarted.tick_once()

    assert len(thread.messages) == count and runner_posts(thread) == [post]
    assert len(post.edits) > post_edits
    button = button_on(post)
    assert button.custom_id.endswith(":optout")
    assert button.label == OPT_OUT_LABEL
    assert len(controls_message.edits) > control_edits
    shown = [getattr(one, "item", one) for one in current_view(controls_message).children]
    assert len(shown) == 11 and shown[7].label == "Marathon tracker ↗"
    shown = [one for one in shown if one.custom_id and ":baf:" not in one.custom_id]
    assert [one.label for one in shown][-3:] == [
        "Ping the marathon role: off · turn on",
        "BaF announcements: on · turn off",
        "Host announcements: off · turn on",
    ]
    assert not any(":hosts:" in one.custom_id or ":hostevents:" in one.custom_id for one in shown)
    assert shown[-2].custom_id == f"marathon:controls:{marathon['id']}:announce:off"
    assert shown[-1].custom_id == f"marathon:controls:{marathon['id']}:hostannounce:on"


async def test_a_highlight_a_person_deleted_is_forgotten_not_posted_again(bot, cog):
    marathon = await ready(bot, cog)
    await highlighted(bot, cog, marathon)
    await public_posts(bot)[0].delete()
    cog.__dict__.get("public_sent", {}).clear()

    await follow(bot, cog, marathon)

    row = await run_of(bot, marathon, "Super Metroid")
    assert row["public_message_id"] is None and public_posts(bot) == []
    assert "marathon.public_highlight_lost" in await kinds(bot.db)


async def test_pinned_the_marathon_cog_registers_its_ten_items_before_the_role_block():
    from black_bloc.cogs.content.marathon import NextButton
    from black_bloc.cogs.content.marathon_feeds import FeedButton, NoticeModePick
    from black_bloc.cogs.content.marathon_inbox import InboxButton
    from black_bloc.cogs.content.marathon_near_miss import NearMissButton
    from black_bloc.cogs.content.marathon_people import PeopleButton
    from black_bloc.cogs.content.marathon_thread_controls import ControlButton

    registered = []
    made = Marathons.__new__(Marathons)
    made.bot = type("Bot", (), {"db": type("Db", (), {"is_connected": False})()})()
    made.bot.add_dynamic_items = lambda *items: registered.extend(items)
    await Marathons.cog_load(made)

    assert registered[:10] == [
        NextButton,
        FeedButton,
        NoticeModePick,
        PeopleButton,
        InboxButton,
        ControlButton,
        public.HighlightButton,
        public.AnnounceButton,
        public.AnnouncePick,
        NearMissButton,
    ]


# --- a finished run's highlight: the past tense, no role mention, nobody notified ----------------

ON_NOW = (
    "**Sky** runs **Super Metroid** — Any% on **SS4C** · "
    f"<t:{int((NOW + timedelta(minutes=30)).timestamp())}:f> "
    f"(<t:{int((NOW + timedelta(minutes=30)).timestamp())}:R>) · on now · https://twitch.tv/skyruns"
)
RAN_TODAY = "**Sky** ran **Super Metroid** — Any% today on **SS4C** · https://twitch.tv/skyruns"
RAN_EARLIER = (
    "**Sky** ran **Super Metroid** — Any% on "
    f"<t:{int((NOW + timedelta(minutes=90)).timestamp())}:D> on **SS4C** · "
    "https://twitch.tv/skyruns"
)


async def at_minute(bot, cog, marathon, minutes):
    cog.clock = lambda: NOW + timedelta(minutes=minutes)
    await follow(bot, cog, marathon)


async def live_with_a_ping(bot, cog):
    """A highlight posted while the marathon pings roles: it opens with the runner's role."""
    marathon = await ready(bot, cog)
    await update_marathon(bot.db, marathon["id"], ping_role=1)
    await at_minute(bot, cog, marathon, 31)
    (post,) = await highlighted(bot, cog, marathon)
    assert post.content == f"<@&{FAN_ROLE}> {ON_NOW}"
    return marathon, post


async def edited_rows(bot):
    cur = await bot.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = 'marathon.public_highlight_edited' "
        "ORDER BY id"
    )
    return [json.loads(row["details"]) for row in await cur.fetchall()]


async def test_a_finished_run_goes_past_tense_loses_its_role_mention_and_notifies_nobody(
    bot, cog
):
    marathon, post = await live_with_a_ping(bot, cog)

    await at_minute(bot, cog, marathon, 91)

    assert post.content == RAN_TODAY
    assert "<@&" not in post.content and " runs " not in post.content
    quiet = post.edits[-1]["allowed_mentions"]
    assert quiet.roles is False and quiet.users is False and quiet.everyone is False
    assert len(public_posts(bot)) == 1
    logged = (await edited_rows(bot))[-1]
    assert logged["state"] == "done" and logged["message_id"] == str(post.id)


async def test_a_done_post_is_edited_once_and_then_left_alone(bot, cog):
    marathon, post = await live_with_a_ping(bot, cog)
    await at_minute(bot, cog, marathon, 91)
    edits = len(post.edits)

    await at_minute(bot, cog, marathon, 120)
    await at_minute(bot, cog, marathon, 200)

    assert len(post.edits) == edits and post.content == RAN_TODAY


async def test_today_becomes_the_date_once_the_servers_day_has_passed(bot, cog):
    marathon, post = await live_with_a_ping(bot, cog)
    await at_minute(bot, cog, marathon, 91)

    await at_minute(bot, cog, marathon, 779)
    assert post.content == RAN_TODAY
    await at_minute(bot, cog, marathon, 781)

    assert post.content == RAN_EARLIER
    assert post.edits[-1]["allowed_mentions"].roles is False


async def test_the_past_tense_words_and_the_done_template_are_settings(bot, cog):
    await bot.store.set(GUILD, "marathon_part_runner_done", "smashed")
    await bot.store.set(GUILD, "marathon_public_day_today", "earlier today")
    await bot.store.set(GUILD, "marathon_public_done_template", "{runner} {part} {game} {day}!")
    marathon, post = await live_with_a_ping(bot, cog)

    await at_minute(bot, cog, marathon, 91)

    assert post.content == "Sky smashed Super Metroid earlier today!"


async def test_the_done_template_refuses_a_word_it_cannot_fill(bot, cog):
    with pytest.raises(SettingError):
        await bot.store.set(GUILD, "marathon_public_done_template", "{runner} {nope}")
    await bot.store.set(GUILD, "marathon_public_done_template", "{runner} {day} {state}")
    with pytest.raises(SettingError):
        await bot.store.set(GUILD, "marathon_public_template", "{runner} {day}")


async def test_a_highlight_posted_for_a_run_already_over_mentions_no_role(bot, cog):
    marathon = await ready(bot, cog)
    await update_marathon(bot.db, marathon["id"], ping_role=1)
    await at_minute(bot, cog, marathon, 91)

    (post,) = await highlighted(bot, cog, marathon)

    assert post.content == RAN_TODAY
    assert post.kwargs["allowed_mentions"].roles is False
    assert (await details_of(bot.db, "marathon.public_highlight_posted"))["roles"] == []


def restarted(bot, cog, minutes):
    again = type(cog)(bot)
    again.client = cog.client
    again.clock = lambda: NOW + timedelta(minutes=minutes)
    bot.cogs["Marathons"] = again
    return again


async def test_a_highlight_up_before_the_restart_gets_the_done_words_when_its_run_ends_after(
    bot, cog
):
    marathon, post = await live_with_a_ping(bot, cog)
    again = restarted(bot, cog, 60)
    await follow(bot, again, marathon)
    assert post.content == f"<@&{FAN_ROLE}> {ON_NOW}"

    await at_minute(bot, again, marathon, 91)

    assert post.content == RAN_TODAY


async def test_a_highlight_already_done_before_the_restart_stays_exactly_as_it_was(bot, cog):
    marathon, post = await live_with_a_ping(bot, cog)
    row = await run_of(bot, marathon, "Super Metroid")
    ended = (NOW + timedelta(minutes=90)).isoformat()
    await update_run(bot.db, row["id"], state="done", done_at=ended)
    before = f"<@&{FAN_ROLE}> " + ON_NOW.replace(" · on now · ", " · done · ")
    post.content = before
    edits = len(post.edits)
    again = restarted(bot, cog, 300)

    await follow(bot, again, marathon)
    await at_minute(bot, again, marathon, 2000)

    assert post.content == before and len(post.edits) == edits
    assert not any(one["state"] == "done" for one in await edited_rows(bot))


async def test_a_run_that_ended_while_the_bot_was_down_is_reworded_at_the_next_boot_with_its_date(
    bot, cog
):
    marathon, post = await live_with_a_ping(bot, cog)
    again = restarted(bot, cog, 2000)

    await follow(bot, again, marathon)

    assert post.content == RAN_EARLIER and "<@&" not in post.content
