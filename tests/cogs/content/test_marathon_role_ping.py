# ruff: noqa: F401, F811
import json
from datetime import timedelta
from types import SimpleNamespace

import pytest

from black_bloc import marathon_role_ping as mrp
from black_bloc.cogs.content import marathon_announce as announce
from black_bloc.cogs.content import marathon_role_ping as role_ping
from black_bloc.cogs.content import marathon_thread_controls as controls
from black_bloc.cogs.content.marathon import set_channel, update_marathon
from black_bloc.cogs.content.spotlight import set_ping_mode
from tests.cogs.content.test_marathon import (
    FAN_ROLE,
    NOW,
    SKY,
    a_run,
    bot,
    cog,
    gdq_row,
    threading,
)
from tests.cogs.content.test_marathon_public import named, public_posts, ready
from tests.cogs.content.test_marathon_public_reminders import at_fifteen, reminders_in
from tests.cogs.content.test_marathon_runner_posts import (
    events_room,
    follow,
    fresh,
    run_of,
    the_thread,
)
from tests.cogs.content.test_spotlight import (
    CHANNEL,
    GUILD,
    FakeActor,
    FakeRole,
    details_of,
    kinds,
)

MARATHON_ROLE = 6100


def the_role(bot, *, mentionable=True):
    role = FakeRole(MARATHON_ROLE, "Marathon")
    role.mentionable = mentionable
    bot.guild.roles.append(role)
    return role


async def pinging(bot, cog, *, mentionable=True):
    """A tracked marathon with its ping switch on and the Marathon role picked."""
    marathon = await ready(bot, cog)
    the_role(bot, mentionable=mentionable)
    await bot.store.set(GUILD, "marathon_role_id", MARATHON_ROLE)
    await update_marathon(bot.db, marathon["id"], ping_role=1)
    return await fresh(bot, marathon)


def public_copy(bot):
    (shown,) = reminders_in(bot.guild.channels[CHANNEL])
    return shown


def staff_copy(bot):
    (shown,) = reminders_in(the_thread(bot))
    return shown


def allowed(message):
    found = message.kwargs["allowed_mentions"].roles
    return [one.id for one in found] if found else []


async def rows(bot, kind):
    cur = await bot.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id", (kind,)
    )
    return [json.loads(row["details"]) for row in await cur.fetchall()]


# --- the 15-minute heads-up ----------------------------------------------------------------------


async def test_the_public_heads_up_mentions_the_marathon_role_once_and_notifies(bot, cog):
    marathon = await pinging(bot, cog)

    await at_fifteen(bot, cog, marathon)

    shown = public_copy(bot)
    assert shown.content.count(f"<@&{MARATHON_ROLE}>") == 1
    assert shown.content.startswith(f"<@&{FAN_ROLE}> <@&{MARATHON_ROLE}> <@{SKY}> runs ")
    assert allowed(shown) == [FAN_ROLE, MARATHON_ROLE]
    mentions = shown.kwargs["allowed_mentions"]
    assert mentions.users is False and mentions.everyone is False


async def test_the_staff_threads_copy_never_carries_the_marathon_role(bot, cog):
    marathon = await pinging(bot, cog)

    await at_fifteen(bot, cog, marathon)

    staff = staff_copy(bot)
    assert f"<@&{MARATHON_ROLE}>" not in staff.content
    assert staff.content.startswith(f"<@&{FAN_ROLE}> ") and allowed(staff) == [FAN_ROLE]


async def test_both_rows_say_which_roles_went_in_which_message(bot, cog):
    marathon = await pinging(bot, cog)

    await at_fifteen(bot, cog, marathon)

    public = await details_of(bot.db, "marathon.public_reminded")
    assert public["roles"] == [FAN_ROLE, MARATHON_ROLE] and public["pinged"] is True
    assert public["marathon_role"] == MARATHON_ROLE and public["marathon_role_reason"] is None
    assert public["message_id"] == str(public_copy(bot).id) and public["channel_id"] == CHANNEL
    staff = await details_of(bot.db, "marathon.reminded")
    assert staff["roles"] == [FAN_ROLE] and staff["pinged"] is True
    assert staff["public_roles"] == [FAN_ROLE, MARATHON_ROLE]
    assert staff["marathon_role"] == MARATHON_ROLE and staff["marathon_role_reason"] is None
    assert staff["message_id"] == str(staff_copy(bot).id)


async def test_a_channel_row_that_never_pings_and_has_no_role_still_pings_the_marathon_role(
    bot, cog, monkeypatch
):
    async def nobody(bot, guild, ident, *, notice=True):
        return None

    monkeypatch.setattr("black_bloc.pings.announced_fan_role", nobody)
    monkeypatch.setattr("black_bloc.pings.announced_spotlight_fan_role", nobody)
    marathon = await pinging(bot, cog)
    channel = await gdq_row(bot)
    await set_ping_mode(bot, bot.guild, FakeActor(), channel["id"], "never")
    await set_channel(bot, bot.guild, FakeActor(), marathon, channel["id"])

    await at_fifteen(bot, cog, marathon)

    shown = public_copy(bot)
    assert shown.content.startswith(f"<@&{MARATHON_ROLE}> <@{SKY}> runs ")
    assert allowed(shown) == [MARATHON_ROLE]
    assert "<@&" not in staff_copy(bot).content and allowed(staff_copy(bot)) == []
    staff = await details_of(bot.db, "marathon.reminded")
    assert (staff["pinged"], staff["roles"]) == (False, [])
    assert staff["public_roles"] == [MARATHON_ROLE]


async def test_only_the_ping_mark_mentions_it_the_day_and_two_hour_marks_do_not(bot, cog):
    await bot.store.set(GUILD, "marathon_reminder_minutes", "1440, 120, 15")
    cog.client.runs_given = [
        a_run(3, 1500, game="Super Metroid", people=(("Sky", "skyruns", "runner"),)),
    ]
    marathon = await pinging(bot, cog)
    for minutes in (61, 1381, 1486):
        cog.clock = lambda minutes=minutes: NOW + timedelta(minutes=minutes)
        await follow(bot, cog, marathon)

    shown = reminders_in(bot.guild.channels[CHANNEL])
    assert len(shown) == 3
    assert [f"<@&{MARATHON_ROLE}>" in one.content for one in shown] == [False, False, True]
    assert [allowed(one) for one in shown] == [[], [], [FAN_ROLE, MARATHON_ROLE]]
    logged = await rows(bot, "marathon.public_reminded")
    assert [one["mark"] for one in logged] == [1440, 120, 15]
    assert ["marathon_role" in one for one in logged] == [False, False, True]
    assert [one["roles"] for one in logged] == [[], [], [FAN_ROLE, MARATHON_ROLE]]


async def test_the_live_highlight_and_the_shoutout_do_not_mention_the_marathon_role(bot, cog):
    await bot.store.set(GUILD, "marathon_live_pings", True)
    marathon = await pinging(bot, cog)
    await update_marathon(bot.db, marathon["id"], public_highlight=1)
    row = await run_of(bot, marathon, "Super Metroid")

    await cog.shout(bot.guild, await fresh(bot, marathon), row)

    (highlight,) = public_posts(bot)
    assert f"<@&{MARATHON_ROLE}>" not in highlight.content
    assert MARATHON_ROLE not in allowed(highlight)
    assert not any(f"<@&{MARATHON_ROLE}>" in one.content for one in the_thread(bot).messages)
    posted = await details_of(bot.db, "marathon.public_highlight_posted")
    assert posted["roles"] == [FAN_ROLE]
    assert "marathon.shouted" in await kinds(bot.db)


async def test_the_marathons_switch_off_never_mentions_it(bot, cog):
    marathon = await pinging(bot, cog)
    await update_marathon(bot.db, marathon["id"], ping_role=0)

    await at_fifteen(bot, cog, marathon)

    assert "<@&" not in public_copy(bot).content and allowed(public_copy(bot)) == []
    logged = await details_of(bot.db, "marathon.public_reminded")
    assert (logged["pinged"], logged["roles"]) == (False, [])
    assert (logged["marathon_role"], logged["marathon_role_reason"]) == (None, mrp.SWITCH_OFF)


@pytest.mark.parametrize(
    ("key", "reason", "others"),
    [
        ("marathon_role_pings", mrp.ROLE_PINGS_OFF, [FAN_ROLE]),
        ("marathon_reminder_pings", mrp.REMINDER_PINGS_OFF, []),
    ],
)
async def test_a_key_off_posts_without_it_and_says_which_key(bot, cog, key, reason, others):
    marathon = await pinging(bot, cog)
    await bot.store.set(GUILD, key, False)

    await at_fifteen(bot, cog, marathon)

    shown = public_copy(bot)
    assert f"<@&{MARATHON_ROLE}>" not in shown.content and allowed(shown) == others
    logged = await details_of(bot.db, "marathon.public_reminded")
    assert logged["roles"] == others
    assert (logged["marathon_role"], logged["marathon_role_reason"]) == (None, reason)
    assert f"{key} is off" in role_ping.status_line(bot, bot.guild, marathon)


async def test_no_role_picked_posts_without_it_and_logs_unset(bot, cog):
    marathon = await pinging(bot, cog)
    await bot.store.clear(GUILD, "marathon_role_id")

    await at_fifteen(bot, cog, marathon)

    assert allowed(public_copy(bot)) == [FAN_ROLE]
    logged = await details_of(bot.db, "marathon.public_reminded")
    assert (logged["marathon_role"], logged["marathon_role_reason"]) == (None, mrp.UNSET)
    assert "marathon.public_reminder_failed" not in await kinds(bot.db)


async def test_a_deleted_role_posts_without_it_and_logs_gone(bot, cog):
    marathon = await pinging(bot, cog)
    bot.guild.roles.clear()

    await at_fifteen(bot, cog, marathon)

    shown = public_copy(bot)
    assert f"<@&{MARATHON_ROLE}>" not in shown.content and allowed(shown) == [FAN_ROLE]
    logged = await details_of(bot.db, "marathon.public_reminded")
    assert (logged["marathon_role"], logged["marathon_role_reason"]) == (None, mrp.GONE)
    assert (await details_of(bot.db, "marathon.reminded"))["marathon_role_reason"] == mrp.GONE


async def test_a_role_the_bot_cannot_notify_is_left_out_and_the_row_says_so(bot, cog):
    marathon = await pinging(bot, cog, mentionable=False)

    await at_fifteen(bot, cog, marathon)

    shown = public_copy(bot)
    assert f"<@&{MARATHON_ROLE}>" not in shown.content and allowed(shown) == [FAN_ROLE]
    logged = await details_of(bot.db, "marathon.public_reminded")
    assert logged["marathon_role"] is None
    assert logged["marathon_role_reason"] == mrp.NOT_MENTIONABLE


async def test_mention_everyone_lets_the_bot_notify_a_role_that_is_not_mentionable(bot, cog):
    marathon = await pinging(bot, cog, mentionable=False)
    bot.guild.me = SimpleNamespace(guild_permissions=SimpleNamespace(mention_everyone=True))

    await at_fifteen(bot, cog, marathon)

    assert allowed(public_copy(bot)) == [FAN_ROLE, MARATHON_ROLE]


async def test_the_channels_own_overwrite_decides_over_the_server_wide_permission(bot, cog):
    marathon = await pinging(bot, cog, mentionable=False)
    bot.guild.me = SimpleNamespace(guild_permissions=SimpleNamespace(mention_everyone=True))
    bot.guild.channels[CHANNEL].permissions_for = lambda member: SimpleNamespace(
        mention_everyone=False
    )

    assert role_ping.verdict_for(bot, bot.guild, marathon).reason == mrp.NOT_MENTIONABLE
    bot.guild.channels[CHANNEL].permissions_for = lambda member: SimpleNamespace(
        mention_everyone=True
    )
    assert role_ping.verdict_for(bot, bot.guild, marathon).mentions


async def test_the_marathon_role_doubling_as_a_runners_role_is_pinged_in_the_public_copy_only(
    bot, cog, monkeypatch
):
    async def marathon_role(bot, guild, user_id, *, notice=True):
        return MARATHON_ROLE

    monkeypatch.setattr("black_bloc.pings.announced_fan_role", marathon_role)
    marathon = await pinging(bot, cog)

    await at_fifteen(bot, cog, marathon)

    assert public_copy(bot).content.count(f"<@&{MARATHON_ROLE}>") == 1
    assert allowed(public_copy(bot)) == [MARATHON_ROLE]
    assert "<@&" not in staff_copy(bot).content and allowed(staff_copy(bot)) == []


async def test_no_public_copy_means_no_mention_and_the_staff_row_says_why(bot, cog):
    marathon = await pinging(bot, cog)
    said = await announce.set_opt_out(bot, bot.guild, FakeActor(), marathon, [SKY], True)
    assert said.ok, said.message

    await at_fifteen(bot, cog, marathon)

    assert reminders_in(bot.guild.channels[CHANNEL]) == []
    assert f"<@&{MARATHON_ROLE}>" not in staff_copy(bot).content
    skipped = await details_of(bot.db, "marathon.public_reminder_skipped")
    assert skipped["because"] == "opted_out"
    assert (skipped["marathon_role"], skipped["marathon_role_reason"]) == (
        None,
        mrp.NO_PUBLIC_COPY,
    )
    staff = await details_of(bot.db, "marathon.reminded")
    assert staff["public_roles"] == [] and staff["marathon_role_reason"] == mrp.NO_PUBLIC_COPY


async def test_public_reminders_off_is_named_on_the_staff_row(bot, cog):
    marathon = await pinging(bot, cog)
    await bot.store.set(GUILD, "marathon_public_reminders", False)

    await at_fifteen(bot, cog, marathon)

    assert reminders_in(bot.guild.channels[CHANNEL]) == []
    staff = await details_of(bot.db, "marathon.reminded")
    assert staff["roles"] == [FAN_ROLE] and staff["public_roles"] == []
    assert staff["marathon_role_reason"] == mrp.PUBLIC_REMINDERS_OFF


async def test_a_send_that_fails_records_no_role_as_mentioned(bot, cog):
    marathon = await pinging(bot, cog)
    bot.guild.channels[CHANNEL].send_raises = RuntimeError("nope")

    await at_fifteen(bot, cog, marathon)

    failed = await details_of(bot.db, "marathon.public_reminder_failed")
    assert (failed["pinged"], failed["roles"], failed["marathon_role"]) == (False, [], None)
    assert failed["marathon_role_reason"] == mrp.NO_PUBLIC_COPY


# --- what staff read under the switch -------------------------------------------------------------


async def test_the_line_says_what_will_happen_and_is_silent_while_the_switch_is_off(bot, cog):
    marathon = await pinging(bot, cog)

    said = role_ping.status_line(bot, bot.guild, marathon)
    assert said == f"The public heads-up 15 minutes before a BaF run mentions <@&{MARATHON_ROLE}>."
    plain = role_ping.status_line(bot, bot.guild, marathon, mention=False)
    assert plain == "The public heads-up 15 minutes before a BaF run mentions @Marathon."

    await update_marathon(bot.db, marathon["id"], ping_role=0)
    assert role_ping.status_line(bot, bot.guild, await fresh(bot, marathon)) == ""


async def test_each_reason_has_its_own_words_and_the_words_are_settings(bot, cog):
    marathon = await pinging(bot, cog, mentionable=False)
    line = lambda: role_ping.status_line(bot, bot.guild, marathon, mention=False)  # noqa: E731

    assert "@Marathon is not mentionable" in line()
    bot.guild.roles.clear()
    assert "no longer in this server" in line()
    await bot.store.clear(GUILD, "marathon_role_id")
    assert "no role is picked in marathon_role_id" in line()
    await bot.store.set(GUILD, "marathon_role_ping_line_unset", "Pick the role first.")
    assert line() == "Pick the role first."
    await update_marathon(bot.db, marathon["id"], announcements=0)
    marathon = await fresh(bot, marathon)
    assert "BaF announcements are off" in line()
    state = role_ping.state_of(bot, bot.guild, marathon)
    assert state == {"mentions": False, "reason": mrp.ANNOUNCEMENTS_OFF, "line": line()}


async def test_the_thread_controls_carry_the_line_while_the_switch_is_on(bot, cog):
    marathon = await pinging(bot, cog)

    content, _controls, _labels = await controls.rendered(bot, bot.guild, marathon)
    assert content.endswith(
        f"\nThe public heads-up 15 minutes before a BaF run mentions <@&{MARATHON_ROLE}>."
    )

    await bot.store.clear(GUILD, "marathon_role_id")
    content, _controls, _labels = await controls.rendered(bot, bot.guild, marathon)
    assert content.endswith("no role is picked in marathon_role_id.")
    assert await controls.refresh_controls(bot, bot.guild, marathon["id"]) == "edited"
    pinned = next(
        one for one in the_thread(bot).messages if one.id == marathon["controls_message_id"]
    )
    assert pinned.content == content
    assert pinned.edits[-1]["allowed_mentions"].roles is False

    await update_marathon(bot.db, marathon["id"], ping_role=0)
    content, _controls, _labels = await controls.rendered(
        bot, bot.guild, await fresh(bot, marathon)
    )
    assert "marathon_role_id" not in content and "heads-up" not in content
