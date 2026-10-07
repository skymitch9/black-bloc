from __future__ import annotations

from black_bloc import brackets_store as store_
from black_bloc import brackets_view
from black_bloc.brackets import play
from black_bloc.brackets.model import ROUND_ROBIN, SINGLE, Options

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
