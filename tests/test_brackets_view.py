from __future__ import annotations

from black_bloc import brackets_store as store_
from black_bloc import brackets_view
from black_bloc.brackets import play, pools
from black_bloc.brackets.model import DOUBLE, ROUND_ROBIN, SINGLE, Options, Plan

GUILD = 4242
NOW = "2026-10-07T12:00:00+00:00"


async def seeded(db, fmt, count):
    tid = await store_.create(db, GUILD, {"name": "Knuck Up", "format": fmt}, created_by=7)
    ids = [
        await store_.add_entrant(db, tid, f"P{n}", user_id=100 + n, added_by=7)
        for n in range(count)
    ]
    built = play.build(ids, Options(format=fmt, best_of_finals=3), NOW)
    await store_.save(db, tid, built.bracket, built.changed, [])
    await store_.update(db, tid, {"state": "running"})
    return tid, ids, built.bracket


async def test_the_full_view_names_both_slots_and_says_when_a_report_stands(db):
    tid, ids, bracket = await seeded(db, SINGLE, 2)
    reported = play.report(bracket, "W1-1", "a", 2, 0, 100, NOW)
    await store_.save(db, tid, reported.bracket, reported.changed, [])
    row = await store_.tournament(db, GUILD, tid)
    found = await brackets_view.full(db, row, viewer=101, runs=False)
    assert (found["mine"], found["may_run"], found["finished"]) == (ids[1], False, False)
    (only,) = found["sets"]
    assert (only["a_name"], only["b_name"], only["state"]) == ("P0", "P1", "reported")
    assert only["confirms_at"] == "2026-10-07T12:12:00+00:00"
    assert found["options"]["grand_final_reset"] is True
    assert [one["what"] for one in found["waiting_on"]] == ["opponent_confirms", "confirm"]
    assert [one["user_id"] for one in found["entrants"]] == ["100", "101"]


async def test_round_robin_standings_hold_the_table_and_place_only_when_done(db):
    tid, ids, bracket = await seeded(db, ROUND_ROBIN, 3)
    row = await store_.tournament(db, GUILD, tid)
    found = await brackets_view.full(db, row)
    assert [one["place"] for one in found["standings"]] == [None, None, None]
    assert set(found["standings"][0]) >= {"set_wins", "game_wins", "opponents_rate", "rank"}


async def test_before_the_start_the_view_has_no_sets(db):
    tid = await store_.create(db, GUILD, {"name": "x", "format": SINGLE}, created_by=7)
    found = await brackets_view.full(db, await store_.tournament(db, GUILD, tid))
    assert (found["sets"], found["standings"], found["waiting_on"]) == ([], [], [])
    assert brackets_view.summary(await store_.tournament(db, GUILD, tid))["entrant_count"] is None

async def test_each_set_shows_its_card_and_whether_it_is_a_rematch(db):
    tid, ids, bracket = await seeded(db, SINGLE, 2)
    row = await store_.tournament(db, GUILD, tid)
    (only,) = (await brackets_view.full(db, row))["sets"]
    assert (only["message_id"], only["card_at"], only["rematch"]) == (None, None, False)
    await store_.set_card(db, tid, "W1-1", 12345678901234567, NOW)
    (only,) = (await brackets_view.full(db, row))["sets"]
    assert (only["message_id"], only["card_at"]) == ("12345678901234567", NOW)


async def pooled_view(db, advanced=False):
    tid = await store_.create(
        db,
        GUILD,
        {"name": "Pools", "format": DOUBLE, "pools_format": ROUND_ROBIN, "pool_count": 2},
        created_by=7,
    )
    ids = [
        await store_.add_entrant(db, tid, f"P{n}", user_id=100 + n, added_by=7) for n in range(8)
    ]
    plan = Plan(ROUND_ROBIN, 2, 2)
    built = pools.build(ids, Options(format=DOUBLE, best_of_finals=3), plan, NOW).bracket
    while True:
        ready = [one for one in built.ordered() if one.state == "ready"]
        if not ready:
            break
        a_wins = ready[0].slot_a < ready[0].slot_b
        score = {"score_a": 2, "score_b": 0} if a_wins else {"score_a": 0, "score_b": 2}
        built = pools.override(built, ready[0].key, 7, NOW, **score).bracket
    if advanced:
        built = pools.advance(built, NOW).bracket
    await store_.save(db, tid, built, list(built.matches), [])
    await store_.update(db, tid, {"state": "running" if advanced else "pools"})
    return await store_.tournament(db, GUILD, tid), ids


async def test_a_pools_view_carries_each_pool_its_table_and_who_goes_through(db):
    row, ids = await pooled_view(db)
    found = await brackets_view.full(db, row)
    assert (found["phase"], found["pools_finished"], found["sets"]) == ("pools", True, [])
    first, second = found["pools"]
    assert (first["letter"], first["cut"], len(first["sets"])) == ("A", 2, 6)
    assert first["entrants"] == [ids[0], ids[3], ids[4], ids[7]]
    assert first["sets"][0]["key"] == "A.R1-1" and first["sets"][0]["pool"] == 1
    assert len(first["advancing"]) == 2 and first["tied"] == []
    assert [one["rank"] for one in first["standings"]] == [1, 2, 3, 4]
    assert found["options"]["pools_format"] == "round_robin"
    assert {one["what"] for one in found["waiting_on"]} == {"final"}


async def test_a_dqd_pool_leader_is_marked_and_not_through(db):
    row, ids = await pooled_view(db)
    leader = ids[0]
    await store_.update_entrant(db, leader, {"dq": 1})
    first = (await brackets_view.full(db, row))["pools"][0]
    assert first["advancing"] == [ids[3], ids[4]]
    marks = {one["entrant"]: one["withdrawn"] for one in first["standings"]}
    assert marks[leader] is True and not any(marks[one] for one in ids[3:5])


async def test_a_pool_still_playing_reports_no_tie(db):
    tid = await store_.create(
        db,
        GUILD,
        {"name": "Early", "format": DOUBLE, "pools_format": ROUND_ROBIN, "pool_count": 2},
        created_by=7,
    )
    ids = [await store_.add_entrant(db, tid, f"E{n}", user_id=None, added_by=7) for n in range(8)]
    built = pools.build(ids, Options(format=DOUBLE), Plan(ROUND_ROBIN, 2, 2), NOW).bracket
    await store_.save(db, tid, built, list(built.matches), [])
    await store_.update(db, tid, {"state": "pools"})
    row = await store_.tournament(db, GUILD, tid)
    first = (await brackets_view.full(db, row))["pools"][0]
    assert first["finished"] is False
    assert pools.tie_of(pools.pool_parts(built)[0], 2, 1) != []
    assert first["tied"] == []


async def test_once_advanced_the_view_draws_the_final_as_its_sets(db):
    row, ids = await pooled_view(db, advanced=True)
    found = await brackets_view.full(db, row)
    assert found["phase"] == "final"
    assert {one["phase"] for one in found["sets"]} == {"final"}
    assert all("." not in one["key"] for one in found["sets"])
    assert len(found["pools"]) == 2
    placed = {one["entrant"]: one["place"] for one in found["standings"]}
    assert len(placed) == 8
