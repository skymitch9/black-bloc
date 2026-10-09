from __future__ import annotations

from black_bloc import points_store as store_
from black_bloc.points.board import Row

GUILD = 4242
OTHER = 5151


async def run_for(db, user_id, *, guild=GUILD, game="Celeste", seconds=60.0):
    return await store_.add_run(
        db, guild, user_id, {"game": game, "seconds": seconds, "proof_url": "https://x.io/a"}
    )


async def test_a_run_goes_in_pending_and_reads_back_only_in_its_own_server(db):
    run_id = await run_for(db, 21)

    row = await store_.run(db, GUILD, run_id)
    assert (row["state"], row["xp"], row["speedpoints"], row["category"]) == ("pending", 0, 0, None)
    assert await store_.run(db, OTHER, run_id) is None


async def test_a_conditional_write_only_lands_in_the_state_it_expects(db):
    run_id = await run_for(db, 21)

    assert await store_.update_run(db, run_id, {"state": "approved"}, when_state="pending")
    assert not await store_.update_run(db, run_id, {"state": "rejected"}, when_state="pending")
    assert (await store_.run(db, GUILD, run_id))["state"] == "approved"
    assert await store_.update_run(db, run_id, {})


async def test_the_pending_queue_is_oldest_first_and_a_members_runs_newest_first(db):
    first, second = await run_for(db, 21), await run_for(db, 22)
    third = await run_for(db, 21)

    assert [row["id"] for row in await store_.runs(db, GUILD, state="pending")] == [
        first,
        second,
        third,
    ]
    assert [row["id"] for row in await store_.runs(db, GUILD, user_id=21)] == [third, first]
    assert await store_.count(db, GUILD, "pending") == 3
    assert await store_.count(db, OTHER, "pending") == 0


async def test_totals_count_only_approved_runs_and_carry_the_last_approval(db):
    one, two, three = await run_for(db, 21), await run_for(db, 21), await run_for(db, 22)
    await run_for(db, 23, guild=OTHER)
    approve = {"state": "approved", "xp": 25, "speedpoints": 10}
    await store_.update_run(db, one, {**approve, "decided_at": "2026-10-09T12:00:00+00:00"})
    await store_.update_run(db, two, {**approve, "decided_at": "2026-10-09T13:00:00+00:00"})
    await store_.update_run(db, three, {"state": "rejected"})

    assert await store_.totals(db, GUILD) == [Row(21, 2, 50, 20, "2026-10-09T13:00:00+00:00")]


async def test_a_bounty_keeps_its_games_as_a_list_and_its_flag_as_a_number(db):
    bounty_id = await store_.add_bounty(
        db,
        GUILD,
        {"name": "B", "games": ["Celeste", "Hades"], "kind": "extra", "amount": 5.0},
        7,
    )

    row = await store_.bounty(db, GUILD, bounty_id)
    assert (store_.games_of(row), row["active"], row["created_by"]) == (["Celeste", "Hades"], 1, 7)
    await store_.update_bounty(db, bounty_id, {"active": False, "games": ["Hades"]})
    row = await store_.bounty(db, GUILD, bounty_id)
    assert (store_.games_of(row), row["active"]) == (["Hades"], 0)
    assert [one["id"] for one in await store_.bounties(db, GUILD, active_only=True)] == []
    assert [one["id"] for one in await store_.bounties(db, GUILD)] == [bounty_id]
    await store_.update_bounty(db, bounty_id, {})


def test_games_that_are_not_a_list_read_as_none():
    assert store_.games_of({"games": "not json"}) == []
    assert store_.games_of({"games": '{"a": 1}'}) == []


async def test_events_are_read_by_id_in_their_own_server(db):
    cur = await db.conn.execute(
        "INSERT INTO events(guild_id, requester_id, title, starts_at, status, created_at) "
        "VALUES (?, 1, 'Run night', '2026-10-09T18:00:00+00:00', 'approved', 'now')",
        (GUILD,),
    )
    await db.conn.commit()
    event_id = int(cur.lastrowid)

    assert list(await store_.events(db, GUILD, [event_id])) == [event_id]
    assert await store_.events(db, OTHER, [event_id]) == {}
    assert await store_.events(db, GUILD, []) == {}


async def test_a_run_is_found_by_the_ticket_it_came_through(db):
    run_id = await store_.add_run(
        db,
        GUILD,
        21,
        {"game": "Celeste", "seconds": 60, "proof_url": "https://x.io/a", "ticket_id": 5},
    )

    assert (await store_.run_by_ticket(db, GUILD, 5))["id"] == run_id
    assert await store_.run_by_ticket(db, OTHER, 5) is None
    assert await store_.run_by_ticket(db, GUILD, 6) is None
