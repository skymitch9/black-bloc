from types import SimpleNamespace

from black_bloc import rolegrants as grants
from black_bloc import timed_roles as timed
from black_bloc.cogs.community.role_menus import create_menu

GUILD = 7
LATER = "2099-01-01T00:00:00+00:00"
SOON = "2098-01-01T00:00:00+00:00"


def member(user_id):
    return SimpleNamespace(id=user_id)


async def event(db, name, *, ends_at=None, ended=False):
    menu_id = await create_menu(db, GUILD, name, name.title(), None, "staff")
    await db.conn.execute(
        "UPDATE role_menus SET ends_at = ?, ended_at = ? WHERE id = ?",
        (ends_at, "2020-01-01T00:00:00+00:00" if ended else None, menu_id),
    )
    await db.conn.commit()
    return menu_id


async def assign(db, user_id, role_id, menu_id, until=None):
    return await grants.add_grant(
        db, GUILD, user_id, role_id, grants.STAFF, until=until, menu_id=menu_id
    )


def test_the_plan_takes_every_worn_role_no_other_open_event_holds_and_skips_pings_roles():
    wearing = [(member(1), [10, 11]), (member(2), [10]), (member(3), [12])]

    plan = timed.plan(wearing, {(1, 11)}, skip={12})

    assert [(one.id, roles) for one, roles in plan.take] == [(1, [10]), (2, [10])]
    assert (plan.members, plan.roles, plan.keep) == (2, 1, 1)


async def test_the_list_is_one_per_server_first_label_kept_in_the_order_added(db):
    assert await timed.add(db, GUILD, 10, "Runner") is True
    assert await timed.add(db, GUILD, 11, "Host") is True
    assert await timed.add(db, GUILD, 10, "Speedrunner") is False
    assert await timed.add(db, GUILD + 1, 10, "Other") is True

    assert await timed.labels(db, GUILD) == {10: "Runner", 11: "Host"}
    assert await timed.role_ids(db, GUILD) == [10, 11]
    assert await timed.is_timed(db, GUILD, 11) and not await timed.is_timed(db, GUILD, 12)
    assert await timed.remove(db, GUILD, 11) is True and await timed.remove(db, GUILD, 11) is False


async def test_keepers_are_open_assignments_on_other_events_that_have_not_ended(db):
    a = await event(db, "a", ends_at=SOON)
    b = await event(db, "b")
    over = await event(db, "c", ended=True)
    await assign(db, 1, 10, a)
    await assign(db, 1, 10, b)
    await assign(db, 2, 10, over)
    await assign(db, 3, 11, b)

    assert await timed.keepers(db, GUILD, a) == {(1, 10), (3, 11)}
    assert await timed.assigned_count(db, GUILD, 10) == 2
    assert await timed.assigned_by_role(db, GUILD, b) == {10: 1, 11: 1}
    assert await timed.assigned_people(db, GUILD, b) == 2


async def test_an_events_end_stamps_only_its_own_assignments_and_closing_keeps_the_stuck(db):
    a = await event(db, "a", ends_at=SOON)
    b = await event(db, "b", ends_at=LATER)
    await assign(db, 1, 10, a)
    await assign(db, 2, 10, a)
    other = await assign(db, 1, 10, b, until=LATER)

    assert await timed.stamp_event(db, GUILD, a, SOON) == 2
    assert (await grants.get_grant(db, other))["expires_at"] == LATER
    assert await timed.close_event(db, GUILD, a, grants.EXPIRED, keep={(2, 10)}) == 1
    assert [row["user_id"] for row in await timed.event_grants(db, GUILD, a)] == [2]
    assert await timed.event_grant(db, GUILD, 1, 10, b) is not None


async def test_open_events_come_soonest_first_and_the_next_end_names_its_event(db):
    await timed.add(db, GUILD, 10, "Runner")
    await event(db, "later", ends_at=LATER)
    await event(db, "no-end")
    await event(db, "soon", ends_at=SOON)
    await event(db, "over", ends_at="2001-01-01T00:00:00+00:00", ended=True)

    assert [row["name"] for row in await timed.open_events(db, GUILD)] == [
        "soon",
        "later",
        "no-end",
    ]
    assert [row["name"] for row in await timed.ended_events(db, GUILD)] == ["over"]
    assert await timed.soonest_ends(db, GUILD) == {10: {"ends_at": SOON, "menu": "Soon"}}


async def test_an_assigned_member_keeps_a_role_until_their_latest_open_event(db):
    a = await event(db, "a", ends_at=SOON)
    b = await event(db, "b", ends_at=LATER)
    c = await event(db, "c")
    over = await event(db, "d", ends_at=LATER, ended=True)
    await assign(db, 1, 10, a)
    await assign(db, 1, 10, b)
    await assign(db, 2, 10, a)
    await assign(db, 2, 10, c)
    await assign(db, 3, 10, over)
    await assign(db, 3, 11, a)

    found = await timed.assignment_ends(db, GUILD, [1, 2, 3])

    assert found[(1, 10)] == {"ends_at": LATER, "menu": "B"}
    assert found[(2, 10)] == {"ends_at": None, "menu": "C"}
    assert found[(3, 11)] == {"ends_at": SOON, "menu": "A"}
    assert (3, 10) not in found
    assert await timed.event_titles(db, GUILD) == {a: "A", b: "B", c: "C", over: "D"}
