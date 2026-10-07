from __future__ import annotations

import sqlite3

import pytest

from black_bloc import brackets_store as store_
from black_bloc.brackets import play
from black_bloc.brackets.model import DOUBLE, Options

GUILD = 4242


async def tournament(db, **values):
    return await store_.create(
        db, GUILD, {"name": "Knuck Up", "format": DOUBLE, **values}, created_by=7
    )


async def test_a_new_tournament_is_a_draft_of_our_own(db):
    tid = await tournament(db, best_of=5, game="Tekken 8")
    row = await store_.tournament(db, GUILD, tid)
    assert (row["state"], row["source"], row["best_of"], row["game"]) == (
        "draft",
        "own",
        5,
        "Tekken 8",
    )
    assert row["thread_id"] is None and row["channel_id"] is None and row["message_id"] is None
    assert await store_.tournament(db, 1, tid) is None


async def test_entrants_get_the_next_seed_and_a_member_joins_once(db):
    tid = await tournament(db)
    first = await store_.add_entrant(db, tid, "Ada", user_id=21, added_by=21)
    guest = await store_.add_entrant(db, tid, "Remy", user_id=None, added_by=7)
    other = await store_.add_entrant(db, tid, "Rio", user_id=None, added_by=7)
    assert [one["seed"] for one in await store_.entrants(db, tid)] == [1, 2, 3]
    assert (await store_.entrant(db, tid, guest))["user_id"] is None
    assert first != other
    with pytest.raises(sqlite3.IntegrityError):
        await store_.add_entrant(db, tid, "Ada again", user_id=21, added_by=21)


async def test_a_bracket_goes_in_and_comes_back_the_same(db):
    tid = await tournament(db)
    ids = [
        await store_.add_entrant(db, tid, f"P{n}", user_id=100 + n, added_by=7) for n in range(5)
    ]
    built = play.build(ids, Options(format=DOUBLE), "2026-10-07T00:00:00+00:00")
    await store_.save(db, tid, built.bracket, built.changed, [])
    after = play.override(
        built.bracket, "W1-2", 7, "2026-10-07T00:01:00+00:00", score_a=2, score_b=1
    )
    await store_.save(db, tid, after.bracket, after.changed, after.removed)
    await store_.update_entrant(db, ids[4], {"dq": 1})
    loaded = await store_.bracket(db, await store_.tournament(db, GUILD, tid))
    assert loaded.matches == after.bracket.matches
    assert loaded.entrants == ids
    assert loaded.withdrawn == {ids[4]: "dq"}
    assert loaded.options == Options(format=DOUBLE)


async def test_no_bracket_before_the_start(db):
    tid = await tournament(db)
    assert await store_.bracket(db, await store_.tournament(db, GUILD, tid)) is None


async def test_removed_sets_are_deleted_and_the_final_order_is_read_back(db):
    tid = await tournament(db, format="swiss")
    ids = [await store_.add_entrant(db, tid, f"P{n}", user_id=None, added_by=7) for n in range(4)]
    built = play.build(ids, Options(format="swiss"))
    await store_.save(db, tid, built.bracket, built.changed, [])
    await store_.save(db, tid, built.bracket, [], ["S1-2"])
    assert [row["key"] for row in await store_.sets(db, tid)] == ["S1-1"]
    await store_.write_final_order(db, tid, [ids[2], ids[0]])
    loaded = await store_.bracket(db, await store_.tournament(db, GUILD, tid))
    assert loaded.final_order == [ids[2], ids[0]]


async def test_placements_and_seeds_are_written_per_entrant(db):
    tid = await tournament(db)
    ids = [await store_.add_entrant(db, tid, f"P{n}", user_id=None, added_by=7) for n in range(3)]
    await store_.write_seeds(db, tid, list(reversed(ids)))
    await store_.write_placements(db, tid, {ids[0]: 1})
    found = {one["id"]: (one["seed"], one["placement"]) for one in await store_.entrants(db, tid)}
    assert found == {ids[0]: (3, 1), ids[1]: (2, None), ids[2]: (1, None)}


async def test_the_list_counts_the_entrants_still_in(db):
    tid = await tournament(db)
    await store_.add_entrant(db, tid, "A", user_id=None, added_by=7)
    gone = await store_.add_entrant(db, tid, "B", user_id=None, added_by=7)
    await store_.update_entrant(db, gone, {"dropped": 1})
    assert [(row["id"], row["entrant_count"]) for row in await store_.tournaments(db, GUILD)] == [
        (tid, 1)
    ]


async def test_a_set_card_is_kept_across_saves_until_the_set_is_removed(db):
    tid = await tournament(db)
    ids = [
        await store_.add_entrant(db, tid, f"P{n}", user_id=100 + n, added_by=7) for n in range(4)
    ]
    built = play.build(ids, Options(format=DOUBLE), "2026-10-07T00:00:00+00:00")
    await store_.save(db, tid, built.bracket, built.changed, [])
    await store_.set_card(db, tid, "W1-1", 9001, "2026-10-07T00:00:30+00:00")
    after = play.override(
        built.bracket, "W1-1", 7, "2026-10-07T00:01:00+00:00", score_a=2, score_b=1
    )
    assert await store_.save(db, tid, after.bracket, after.changed, after.removed) == {}
    assert await store_.cards(db, tid) == {"W1-1": (9001, "2026-10-07T00:00:30+00:00")}
    assert await store_.save(db, tid, after.bracket, [], ["W1-1"]) == {"W1-1": 9001}
    assert await store_.cards(db, tid) == {}
