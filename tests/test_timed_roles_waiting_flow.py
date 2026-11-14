import re
from datetime import timedelta
from types import SimpleNamespace

import discord

from black_bloc import rolegrants as grants
from black_bloc import timed_roles as timed
from black_bloc import timed_roles_by_hand as hand
from black_bloc import timed_roles_waiting as waits
from black_bloc import timed_roles_waiting_flow as flow
from black_bloc.cogs.community import role_menus as cog_module
from black_bloc.cogs.community.role_menus import RoleMenus
from tests.cogs.community import test_role_menus as base
from tests.cogs.community.test_role_menus import (
    GUILD,
    LATER,
    PAST,
    FakeGuard,
    FakeInteraction,
    FakeMember,
    action_kinds,
    added_by_hand,
    an_event,
    details_of,
    open_grant_on,
    posts,
    store_notice_channel,
    tick,
    timed_list,
)

bot = base.bot
lead = base.lead
no_audit_wait = base.no_audit_wait
LEADS = 4545


def days_ahead(days):
    return waits.iso(waits.now() + timedelta(days=days))[:10]


SOON_DAY = days_ahead(30)


async def put_to_waiting(bot, lead, member, *roles, typed=SOON_DAY):
    await added_by_hand(bot, member, *roles)
    post = posts(bot)[-1]
    later = post.kwargs["view"].children[-1]
    assert type(later).__name__ == "ByHandLater"
    await later.callback(FakeInteraction(bot, lead))
    return post, await submit_date(bot, lead, later, typed)


async def submit_date(bot, lead, item, typed):
    opened = FakeInteraction(bot, lead)
    await item.callback(opened)
    modal = opened.response.modals[-1]
    modal.typed._value = typed
    done = FakeInteraction(bot, lead)
    await modal.on_submit(done)
    return done


async def rows_of(db, user_id=900):
    cur = await db.conn.execute(
        "SELECT * FROM timed_role_waits WHERE user_id = ? ORDER BY id", (user_id,)
    )
    return list(await cur.fetchall())


async def states(db, user_id=900):
    return {int(row["role_id"]): row["state"] for row in await rows_of(db, user_id)}


async def set_until(db, when, user_id=900):
    await db.conn.execute(
        "UPDATE timed_role_waits SET until = ? WHERE user_id = ? AND state = 'waiting'",
        (when, user_id),
    )
    await db.conn.commit()


def ago(days, minutes=1):
    return waits.iso(waits.now() - timedelta(days=days, minutes=minutes))


def wears(member, role_id):
    return role_id in [r.id for r in member.roles]


def kinds_of(view):
    return [type(one).__name__ for one in view.children]


async def waiting_member(bot, lead, *roles, user_id=900):
    await store_notice_channel(bot)
    await timed_list(bot.db, *roles)
    member = FakeMember(bot.guild, user_id=user_id)
    post, done = await put_to_waiting(bot, lead, member, *roles)
    return member, post, done


# --- (none) → waiting: Pick later…


async def test_pick_later_puts_each_worn_role_to_waiting_and_redraws_the_post(bot, db, lead):
    member, post, done = await waiting_member(bot, lead, 10, 11)

    assert await states(db) == {10: waits.WAITING, 11: waits.WAITING}
    assert "waits for an event until" in done.sent and "Reminders go to <@1>" in done.sent
    assert "waiting for an event, expected to end" in post.kwargs["content"]
    assert "Set by <@1>" in post.kwargs["content"]
    assert kinds_of(post.kwargs["view"]) == ["ByHandNew", "WaitMove", "WaitMove"]
    assert [one.item.label for one in post.kwargs["view"].children[1:]] == [
        "Change the date…",
        "Take it off now",
    ]
    [row] = await details_of(db, "role_menu.wait_set")
    assert row["roles"] == [10, 11] and row["assigner"] == 1


async def test_the_rough_date_is_required_readable_future_and_inside_the_ceiling(bot, db, lead):
    await store_notice_channel(bot)
    await timed_list(db, 10)
    member = FakeMember(bot.guild, user_id=900)
    await added_by_hand(bot, member, 10)
    later = posts(bot)[-1].kwargs["view"].children[-1]

    opened = FakeInteraction(bot, lead)
    await later.callback(opened)
    assert opened.response.modals[-1].typed.required is True
    for typed, said in (
        ("someday", "not a date"),
        ("2020-01-01", ""),
        ("2999-01-01", "more than 365 days away"),
    ):
        done = await submit_date(bot, lead, later, typed)
        assert said in done.sent, done.sent
    assert await rows_of(db) == []
    await bot.store.set(GUILD, "rolemenu_wait_max_days", 3650)
    await submit_date(bot, lead, later, waits.iso(waits.now() + timedelta(days=400))[:10])
    assert await states(db) == {10: waits.WAITING}


async def test_the_assigner_is_who_the_audit_log_named_else_who_pressed(bot, db, lead):
    await store_notice_channel(bot)
    await timed_list(db, 10)
    member = FakeMember(bot.guild, user_id=900)
    staffer = FakeMember(bot.guild, user_id=55, display_name="Sky")
    bot.guild.me = SimpleNamespace(id=1, guild_permissions=SimpleNamespace(view_audit_log=True))
    bot.guild.audit_entries = [
        SimpleNamespace(
            target=member,
            user=staffer,
            created_at=waits.now(),
            after=SimpleNamespace(roles=[SimpleNamespace(id=10)]),
        )
    ]
    await put_to_waiting(bot, lead, member, 10)

    [row] = await rows_of(db)
    assert (row["assigner_id"], row["set_by"]) == (55, 1)


async def test_pick_later_on_a_post_whose_member_took_the_role_off_writes_nothing(bot, db, lead):
    await store_notice_channel(bot)
    await timed_list(db, 10)
    member = FakeMember(bot.guild, user_id=900)
    await added_by_hand(bot, member, 10)
    later = posts(bot)[-1].kwargs["view"].children[-1]
    prompt = await hand.get_prompt(db, 1)
    member.roles = []

    ok, said = await flow.put_to_waiting(bot, bot.guild, lead, prompt, waits.now())

    assert not ok and "no longer wears" in said
    assert later is not None and await rows_of(db) == []


# --- protection: no event's end takes a waiting pair


async def test_an_events_end_never_takes_a_waiting_role_and_the_question_says_so(bot, db, lead):
    member, _, _ = await waiting_member(bot, lead, 10)
    other = FakeMember(bot.guild, user_id=901, roles=(10,))
    a = await an_event(db, "a", ends_at=PAST)

    plan = await cog_module.end_plan(bot, bot.guild, a)
    assert (plan.members, plan.waiting) == (1, 1)
    assert "1 are waiting for an event" in cog_module.end_now_question(bot, GUILD, plan)

    await tick(bot)
    assert wears(member, 10) and not wears(other, 10)
    assert await states(db) == {10: waits.WAITING}


async def test_waiting_is_independent_of_an_assignment_on_another_event(bot, db, lead):
    member, _, _ = await waiting_member(bot, lead, 10)
    a = await an_event(db, "a", ends_at=LATER)
    await cog_module.give_event_role(bot, bot.guild, lead, a, 10, [member])

    assert await states(db) == {10: waits.WAITING}
    await db.conn.execute("UPDATE role_menus SET ends_at = ? WHERE id = ?", (PAST, a["id"]))
    await db.conn.commit()
    await tick(bot)

    assert wears(member, 10)
    assert await states(db) == {10: waits.WAITING}
    assert await open_grant_on(db, 900, 10, a["id"]) is None


async def test_take_roles_off_an_event_leaves_a_waiting_role_on(bot, db, lead):
    member, _, _ = await waiting_member(bot, lead, 10)
    a = await an_event(db, "a", ends_at=LATER)
    await cog_module.give_event_role(bot, bot.guild, lead, a, 10, [member])

    found = await cog_module.take_event_role(bot, bot.guild, lead, a, 10, [member])

    assert found["kept"] == [900] and wears(member, 10)
    assert await states(db) == {10: waits.WAITING}


async def test_ending_a_grant_by_hand_leaves_a_waiting_role_on_and_says_why(bot, db, lead):
    member, _, _ = await waiting_member(bot, lead, 10)
    grant_id = await grants.add_grant(db, GUILD, 900, 10, grants.STAFF, granted_by=1, until=LATER)
    row = await grants.get_grant(db, grant_id)

    ok, said = await cog_module.revoke_grant(bot, bot.guild, lead, row)

    assert ok and "they are waiting for an event" in said and wears(member, 10)


async def test_a_role_people_wait_on_cannot_leave_the_timed_list(bot, db, lead):
    await waiting_member(bot, lead, 10)

    refused = await cog_module.drop_timed_role(bot, bot.guild, lead, 10)

    assert "1 people waiting for an event" in refused
    assert await timed.is_timed(db, GUILD, 10)


# --- waiting → came_off / left; already asked


async def test_one_role_coming_off_ends_only_its_own_wait_and_the_post_stays_live(bot, db, lead):
    member, post, _ = await waiting_member(bot, lead, 10, 11)
    before = SimpleNamespace(roles=list(member.roles))
    member.roles = [r for r in member.roles if r.id != 11]

    await RoleMenus(bot).on_member_update(before, member)

    assert await states(db) == {10: waits.WAITING, 11: waits.CAME_OFF}
    assert (await hand.get_prompt(db, 1))["attached_at"] is None
    await added_by_hand(bot, member, 11)
    assert "<@&11> by hand" in posts(bot)[-1].kwargs["content"]
    count = len(posts(bot))
    before = SimpleNamespace(roles=[r for r in member.roles if r.id != 10])
    await RoleMenus(bot).on_member_update(before, member)
    assert len(posts(bot)) == count


async def test_a_member_who_leaves_stops_waiting(bot, db, lead):
    member, _, _ = await waiting_member(bot, lead, 10)

    await RoleMenus(bot).on_member_remove(member)

    assert await states(db) == {10: waits.LEFT}


# --- waiting → attached


async def test_picking_an_event_on_the_waiting_post_attaches_and_ends_the_wait(bot, db, lead):
    a = await an_event(db, "a", ends_at=LATER, title="Back to Black")
    member, post, _ = await waiting_member(bot, lead, 10)
    pick = post.kwargs["view"].children[0]
    assert type(pick).__name__ == "ByHandPick"
    pick.item._values = [str(a["id"])]

    await pick.callback(FakeInteraction(bot, lead))

    assert await states(db) == {10: waits.ATTACHED}
    assert (await rows_of(db))[0]["menu_id"] == a["id"]
    assert (await open_grant_on(db, 900, 10, a["id"]))["source"] == "by_hand_attached"
    assert post.kwargs["view"] is None


async def test_the_entry_card_attaches_after_a_restart_by_its_custom_id(bot, db, lead):
    a = await an_event(db, "a", ends_at=LATER, title="Back to Black")
    await waiting_member(bot, lead, 10, 11)
    custom = waits.pick_id(900)
    item = await flow.WaitEventPick.from_custom_id(
        FakeInteraction(bot, lead),
        discord.ui.Select(custom_id=custom, options=[discord.SelectOption(label="x", value="0")]),
        re.fullmatch(waits.PICK_TEMPLATE, custom),
    )
    item.item._values = [str(a["id"])]
    done = FakeInteraction(bot, lead)

    await item.callback(done)

    assert await states(db) == {10: waits.ATTACHED, 11: waits.ATTACHED}
    assert "Attached <@900> to **Back to Black**" in done.sent
    assert "role_menu.wait_attached" in await action_kinds(db)
    again = FakeInteraction(bot, lead)
    await item.callback(again)
    assert "not waiting for an event any more" in again.sent


async def test_an_attach_that_wrote_nothing_leaves_the_wait_open(bot, db, lead):
    a = await an_event(db, "a", ends_at=PAST)
    await db.conn.execute("UPDATE role_menus SET ended_at = ? WHERE id = ?", (PAST, a["id"]))
    await db.conn.commit()
    await waiting_member(bot, lead, 10)

    ok, said = await flow.attach_entry(
        bot, bot.guild, lead, 900, await cog_module.get_menu_by_id(db, a["id"])
    )

    assert not ok and "still waits" in said
    assert await states(db) == {10: waits.WAITING}


# --- waiting → taken_off, Change the date…


async def test_take_it_off_now_asks_then_takes_the_role_and_finishes_the_post(bot, db, lead):
    member, post, _ = await waiting_member(bot, lead, 10)
    off = post.kwargs["view"].children[-1]
    asked = FakeInteraction(bot, lead)

    await off.callback(asked)
    assert asked.sent == "Take <@&10> off <@900> now?"
    confirm = asked.response.messages[-1]["view"]
    done = FakeInteraction(bot, lead)
    await confirm.children[0].callback(done)

    assert "Took <@&10> off <@900>." in done.sent and not wears(member, 10)
    assert await states(db) == {10: waits.TAKEN_OFF}
    assert "taken off by <@1>" in post.kwargs["content"] and post.kwargs["view"] is None
    await added_by_hand(bot, member, 10)
    assert "<@&10> by hand" in posts(bot)[-1].kwargs["content"]


async def test_take_it_off_now_leaves_a_role_another_open_event_or_pings_holds(
    bot, db, lead, monkeypatch
):
    member, _, _ = await waiting_member(bot, lead, 10, 11)
    a = await an_event(db, "a", ends_at=LATER)
    await cog_module.give_event_role(bot, bot.guild, lead, a, 10, [member])

    async def owned(_bot, _guild_id):
        return {11}

    monkeypatch.setattr(cog_module, "owned_by_pings", owned)
    ok, said = await flow.take_off_now(bot, bot.guild, lead, 900)

    assert ok and wears(member, 10) and wears(member, 11)
    assert "stay on <@900>" in said
    assert await states(db) == {10: waits.TAKEN_OFF, 11: waits.TAKEN_OFF}


async def test_a_refused_take_off_says_so_and_the_role_still_waits(bot, db, lead):
    member, _, _ = await waiting_member(bot, lead, 10)
    member.edit_raises = discord.HTTPException(SimpleNamespace(status=403, reason="no"), "no")

    ok, said = await flow.take_off_now(bot, bot.guild, lead, 900)

    assert not ok and "Discord refused" in said
    assert await states(db) == {10: waits.WAITING}
    assert "role_menu.wait_take_off_failed" in await action_kinds(db)


async def test_change_the_date_moves_the_end_and_resets_the_stage(bot, db, lead):
    _, post, _ = await waiting_member(bot, lead, 10)
    await db.conn.execute("UPDATE timed_role_waits SET stage = 2")
    await db.conn.commit()
    change = post.kwargs["view"].children[1]

    wanted = days_ahead(60)
    done = await submit_date(bot, lead, change, wanted)

    [row] = await rows_of(db)
    assert abs(waits.moment(row["until"]) - waits.moment(wanted + "T12:00:00+00:00")) < timedelta(
        days=1
    )
    assert row["stage"] == 0 and row["state"] == waits.WAITING
    assert "now waits until" in done.sent
    assert "role_menu.wait_date_changed" in await action_kinds(db)


# --- the waiting pass: reminders


async def test_reminders_go_once_per_assigner_and_only_the_latest_stage(bot, db, lead):
    await waiting_member(bot, lead, 10)
    second = FakeMember(bot.guild, user_id=901)
    await put_to_waiting(bot, lead, second, 10)
    await db.conn.execute("UPDATE timed_role_waits SET until = ?", (ago(8),))
    await db.conn.commit()
    count = len(posts(bot))

    done = await flow.waiting_pass(bot, bot.guild)

    [reminder] = posts(bot)[count:]
    assert reminder.kwargs["content"].startswith("<@1>, these are still waiting for an event:")
    assert "<@900>" in reminder.kwargs["content"] and "<@901>" in reminder.kwargs["content"]
    assert [one.id for one in reminder.kwargs["allowed_mentions"].users] == [1]
    assert kinds_of(reminder.kwargs["view"]) == ["ReminderPick"]
    assert done["reminded"] == 2
    assert {row["stage"] for row in await rows_of(db)} == {2}
    await flow.waiting_pass(bot, bot.guild)
    assert len(posts(bot)) == count + 1


async def test_the_reminder_picker_opens_the_entry_card_after_a_restart(bot, db, lead):
    await an_event(db, "a", ends_at=LATER)
    await waiting_member(bot, lead, 10)
    custom = waits.reminder_id(1)
    item = await flow.ReminderPick.from_custom_id(
        FakeInteraction(bot, lead),
        discord.ui.Select(custom_id=custom, options=[discord.SelectOption(label="x", value="0")]),
        re.fullmatch(waits.REMINDER_TEMPLATE, custom),
    )
    item.item._values = ["900"]
    done = FakeInteraction(bot, lead)

    await item.callback(done)

    card = done.response.messages[-1]
    assert card["ephemeral"] and "<@900> · <@&10> · expected to end" in card["content"]
    assert kinds_of(card["view"]) == ["WaitEventPick", "WaitMove", "WaitMove", "WaitMove"]


async def test_a_stranger_is_refused_at_every_waiting_control(bot, db, lead):
    await waiting_member(bot, lead, 10)
    stranger = FakeInteraction(bot, FakeMember(bot.guild, user_id=77))

    await flow.open_entry_card(stranger, 900)
    await flow.WaitMove(900, waits.OFF).callback(stranger)
    await flow.WaitRevert(1).callback(stranger)

    assert stranger.response.modals == []
    assert all(not m.get("view") for m in stranger.response.messages)
    assert await states(db) == {10: waits.WAITING}


# --- the waiting pass: removal → Revert → removal


async def removal_ready(bot, db, lead, *roles):
    member, post, _ = await waiting_member(bot, lead, *roles)
    await bot.store.set(GUILD, "rolemenu_wait_ping_role_id", LEADS)
    await db.conn.execute("UPDATE timed_role_waits SET until = ?, stage = 3", (ago(14),))
    await db.conn.commit()
    return member, post


async def test_the_removal_day_takes_the_role_off_with_one_notice_and_no_dm(bot, db, lead):
    member, post = await removal_ready(bot, db, lead, 10, 11)
    count = len(posts(bot))

    done = await flow.waiting_pass(bot, bot.guild)

    assert not wears(member, 10) and not wears(member, 11) and member.dms == []
    assert await states(db) == {10: waits.REMOVED, 11: waits.REMOVED}
    [notice] = posts(bot)[count:]
    assert notice.kwargs["content"].startswith(f"<@&{LEADS}> <@900> lost <@&10>, <@&11>")
    assert [one.id for one in notice.kwargs["allowed_mentions"].roles] == [LEADS]
    assert kinds_of(notice.kwargs["view"]) == ["WaitRevert"]
    assert done["removed"] == 2
    assert "nobody picked an event" in post.kwargs["content"] and post.kwargs["view"] is None
    assert "role_menu.wait_removed" in await action_kinds(db)


async def test_the_pass_own_removal_echoing_back_stays_removed_and_posts_nothing(bot, db, lead):
    member, _ = await removal_ready(bot, db, lead, 10)
    before = SimpleNamespace(roles=list(member.roles))
    await flow.waiting_pass(bot, bot.guild)
    count = len(posts(bot))

    await RoleMenus(bot).on_member_update(before, member)
    bot._role_grant_ledger = {}
    await RoleMenus(bot).on_member_update(before, member)

    assert await states(db) == {10: waits.REMOVED}
    assert len(posts(bot)) == count


async def test_revert_puts_the_roles_back_and_the_wait_starts_over_then_ends_again(bot, db, lead):
    member, _ = await removal_ready(bot, db, lead, 10)
    await flow.waiting_pass(bot, bot.guild)
    notice = posts(bot)[-1]
    revert = notice.kwargs["view"].children[0]
    custom = revert.item.custom_id
    fresh = await flow.WaitRevert.from_custom_id(
        FakeInteraction(bot, lead),
        discord.ui.Button(custom_id=custom),
        re.fullmatch(waits.REVERT_TEMPLATE, custom),
    )
    before = SimpleNamespace(roles=list(member.roles))
    done = FakeInteraction(bot, lead)

    await fresh.callback(done)

    assert wears(member, 10) and "Put <@&10> back on <@900>" in done.sent
    [row] = await rows_of(db)
    assert (row["state"], row["stage"]) == (waits.WAITING, 0)
    assert waits.moment(row["until"]) > waits.now() + timedelta(days=13)
    assert "got <@&10> back from <@1>" in notice.kwargs["content"]
    assert notice.kwargs["view"] is None
    count = len(posts(bot))
    await RoleMenus(bot).on_member_update(before, member)
    assert len(posts(bot)) == count
    again = FakeInteraction(bot, lead)
    await fresh.callback(again)
    assert "already reverted" in again.sent

    await db.conn.execute("UPDATE timed_role_waits SET until = ?", (ago(14),))
    await db.conn.commit()
    await flow.waiting_pass(bot, bot.guild)
    assert not wears(member, 10) and await states(db) == {10: waits.REMOVED}
    assert kinds_of(posts(bot)[-1].kwargs["view"]) == ["WaitRevert"]


async def test_revert_refuses_a_member_who_left_in_words(bot, db, lead):
    member, _ = await removal_ready(bot, db, lead, 10)
    await flow.waiting_pass(bot, bot.guild)
    del bot.guild.people[900]

    ok, said = await flow.revert(bot, bot.guild, lead, (await rows_of(db))[0]["id"])

    assert not ok and "has left the server" in said
    assert await states(db) == {10: waits.REMOVED}


async def test_the_removal_leaves_on_a_role_an_open_event_holds_and_says_so(bot, db, lead):
    member, _ = await removal_ready(bot, db, lead, 10)
    a = await an_event(db, "a", ends_at=LATER)
    await cog_module.give_event_role(bot, bot.guild, lead, a, 10, [member])

    await flow.waiting_pass(bot, bot.guild)

    assert wears(member, 10)
    assert await states(db) == {10: waits.REMOVED}
    assert "stay on <@900>" in posts(bot)[-1].kwargs["content"]


async def test_a_role_the_bot_cannot_take_is_said_logged_and_retried_without_a_new_notice(
    bot, db, lead
):
    member, _ = await removal_ready(bot, db, lead, 10)
    bot.guild.stuck_roles = {10}
    count = len(posts(bot))

    done = await flow.waiting_pass(bot, bot.guild)
    assert done["wait_failures"] == 1 and wears(member, 10)
    [notice] = posts(bot)[count:]
    assert "could not take <@&10> off <@900>" in notice.kwargs["content"]
    assert notice.kwargs.get("view") is None
    assert await states(db) == {10: waits.WAITING}
    assert "role_menu.wait_remove_failed" in await action_kinds(db)

    await flow.waiting_pass(bot, bot.guild)
    assert len(posts(bot)) == count + 1
    assert len(await details_of(db, "role_menu.wait_remove_failed")) == 2

    bot.guild.stuck_roles = set()
    await flow.waiting_pass(bot, bot.guild)
    assert not wears(member, 10) and await states(db) == {10: waits.REMOVED}


async def test_a_refused_removal_redraws_the_notice_without_revert(bot, db, lead):
    member, _ = await removal_ready(bot, db, lead, 10)
    member.edit_raises = discord.HTTPException(SimpleNamespace(status=403, reason="no"), "no")

    await flow.waiting_pass(bot, bot.guild)

    notice = posts(bot)[-1]
    assert "could not take <@&10>" in notice.kwargs["content"] and notice.kwargs["view"] is None
    assert await states(db) == {10: waits.WAITING}


async def test_with_nowhere_to_post_the_notice_nothing_comes_off(bot, db, lead, monkeypatch):
    member, _ = await removal_ready(bot, db, lead, 10)
    monkeypatch.setattr(cog_module, "by_hand_channel", lambda _bot, _guild: None)

    done = await flow.waiting_pass(bot, bot.guild)

    assert wears(member, 10) and await states(db) == {10: waits.WAITING}
    assert done["wait_failures"] == 1
    assert "role_menu.wait_notice_failed" in await action_kinds(db)


async def test_a_short_member_cache_or_test_mode_touches_nobody(bot, db, lead):
    member, _ = await removal_ready(bot, db, lead, 10)
    bot.guild.member_count = 99

    async def chunk():
        return None

    bot.guild.chunk = chunk
    done = await flow.waiting_pass(bot, bot.guild)
    assert done["wait_failures"] == 1 and wears(member, 10)
    assert await states(db) == {10: waits.WAITING}

    bot.guild.member_count = 0
    bot.guard = FakeGuard()
    await flow.waiting_pass(bot, bot.guild)
    assert wears(member, 10) and await states(db) == {10: waits.WAITING}
    assert "role_menu.wait_would_remove" in await action_kinds(db)


async def test_a_waiting_role_gone_during_downtime_ends_came_off_not_removed(bot, db, lead):
    member, _ = await removal_ready(bot, db, lead, 10)
    member.roles = []

    await flow.waiting_pass(bot, bot.guild)

    assert await states(db) == {10: waits.CAME_OFF}


async def test_the_loop_counts_the_waiting_pass_on_the_health_row(bot, db, lead):
    await removal_ready(bot, db, lead, 10)
    cog = RoleMenus(bot)
    await cog.run_due_menus()
    await cog.run_waits()

    assert cog.loop_counts("_expiry_loop") == (
        "menus due 0 · ended 0 · failures 0 · waiting 0 · reminded 0 · removed 1 · wait failures 0"
    )


# --- a new event: is it for any of these?


async def test_a_new_event_asks_about_everyone_waiting_and_attaches_the_picked(bot, db, lead):
    await waiting_member(bot, lead, 10)
    other = FakeMember(bot.guild, user_id=901)
    await put_to_waiting(bot, lead, other, 10)
    count = len(posts(bot))

    menu = await cog_module.make_event(bot, bot.guild, lead, "Back to Black", ends_at=None)

    [asked] = posts(bot)[count:]
    assert asked.kwargs["content"].startswith("**Back to Black** is new. Is it for any of these?")
    pick = asked.kwargs["view"].children[0]
    assert type(pick).__name__ == "NewEventPick" and pick.item.max_values == 2
    custom = pick.item.custom_id
    item = await flow.NewEventPick.from_custom_id(
        FakeInteraction(bot, lead),
        discord.ui.Select(custom_id=custom, options=[discord.SelectOption(label="x", value="0")]),
        re.fullmatch(waits.EVENT_TEMPLATE, custom),
    )
    item.item._values = ["900"]
    done = FakeInteraction(bot, lead)
    done.message = asked

    await item.callback(done)

    assert await states(db, 900) == {10: waits.ATTACHED}
    assert await states(db, 901) == {10: waits.WAITING}
    assert await open_grant_on(db, 900, 10, menu["id"]) is not None
    assert "<@1> attached <@900> to **Back to Black**." in asked.kwargs["content"]
    assert [one.value for one in asked.kwargs["view"].children[0].item.options] == ["901"]


async def test_new_event_from_a_waiting_entry_attaches_it_and_asks_about_the_others(bot, db, lead):
    _, post, _ = await waiting_member(bot, lead, 10)
    other = FakeMember(bot.guild, user_id=901)
    await put_to_waiting(bot, lead, other, 10)
    count = len(posts(bot))
    opened = FakeInteraction(bot, lead)
    await flow.WaitMove(900, waits.NEW).callback(opened)
    modal = opened.response.modals[-1]
    modal.name._value = "Back to Black 2027"
    modal.typed._value = days_ahead(40)

    await modal.on_submit(FakeInteraction(bot, lead))

    assert await states(db, 900) == {10: waits.ATTACHED}
    [asked] = posts(bot)[count:]
    assert "<@901>" in asked.kwargs["content"] and "<@900>" not in asked.kwargs["content"]
    assert "attached to **Back to Black 2027**" in post.kwargs["content"]


async def test_nobody_waiting_means_no_new_event_post(bot, db, lead):
    await store_notice_channel(bot)
    count = len(posts(bot))

    await cog_module.make_event(bot, bot.guild, lead, "Back to Black")

    assert len(posts(bot)) == count


# --- /rolemenu: Waiting for an event (N)…


async def test_the_root_offers_the_waiting_list_only_while_somebody_waits(bot, db, lead):
    await store_notice_channel(bot)
    _, view = await cog_module.build_panel(bot, bot.guild, lead)
    assert not any(
        "Waiting for an event" in str(getattr(one, "label", "")) for one in view.children
    )

    await waiting_member(bot, lead, 10)
    _, view = await cog_module.build_panel(bot, bot.guild, lead)
    [button] = [one for one in view.children if "Waiting for an event" in str(one.label)]
    assert button.label == "Waiting for an event (1)…"

    embed, waiting = await cog_module.build_waiting(bot, bot.guild)
    assert embed.title == "Waiting for an event"
    assert "<@900> · <@&10>" in embed.description
    assert type(waiting.children[0]).__name__ == "WaitEntryPick"
