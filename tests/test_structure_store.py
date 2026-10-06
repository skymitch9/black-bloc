from datetime import UTC, datetime, timedelta

from black_bloc import structure_store
from black_bloc.structure import DAILY, FAILED, MANUAL, SAVED, UNCHANGED, body_of, digest

GUILD = 7
OTHER = 8
NOON = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


def body(extra_roles=0):
    roles = [{"id": "7", "name": "@everyone", "permissions": 1024, "position": 0}]
    roles += [
        {"id": str(100 + n), "name": f"role-{n}", "permissions": 0, "position": n + 1}
        for n in range(extra_roles)
    ]
    return {
        "guild": {"id": "7", "name": "Black Bloc"},
        "roles": roles,
        "channels": [
            {"id": "40", "name": "Lobby", "type": "category"},
            {
                "id": "41",
                "name": "general",
                "type": "text",
                "parent_id": "40",
                "overwrites": [{"target_id": "7", "target_type": "role", "allow": 0, "deny": 1}],
            },
        ],
    }


async def keep(db, guild_id, found, **extra):
    extra.setdefault("source", DAILY)
    extra.setdefault("keep", 60)
    return await structure_store.store(db, guild_id, found, **extra)


async def test_the_first_structure_is_stored_with_its_counts_and_digest(db):
    stored = await keep(db, GUILD, body(), taken_by=900, now=NOON)

    assert stored.outcome == SAVED and stored.previous is None and stored.pruned == 0
    row = stored.row
    assert (row["roles"], row["categories"], row["channels"], row["overwrites"]) == (1, 1, 1, 1)
    assert row["digest"] == digest(body())
    assert (row["source"], row["taken_by"], row["checks"]) == (DAILY, 900, 0)
    assert row["taken_at"] == row["checked_at"] == NOON.isoformat()
    assert body_of(row)["roles"][0]["name"] == "@everyone"


async def test_an_unchanged_structure_stores_no_second_copy_and_records_the_look(db):
    first = await keep(db, GUILD, body(), now=NOON)

    again = await keep(db, GUILD, body(), source=MANUAL, now=NOON + timedelta(days=1))

    assert again.outcome == UNCHANGED
    assert again.row["id"] == first.row["id"]
    assert again.row["checks"] == 1
    assert again.row["checked_at"] == (NOON + timedelta(days=1)).isoformat()
    assert again.row["taken_at"] == NOON.isoformat()
    assert await structure_store.count(db, GUILD) == 1


async def test_a_changed_structure_is_a_new_row_that_names_the_one_before(db):
    first = await keep(db, GUILD, body())

    second = await keep(db, GUILD, body(extra_roles=1))

    assert second.outcome == SAVED
    assert second.previous["id"] == first.row["id"]
    assert second.row["id"] > first.row["id"]
    assert (await structure_store.latest(db, GUILD))["id"] == second.row["id"]


async def test_a_structure_that_went_back_to_an_older_shape_is_still_a_new_snapshot(db):
    await keep(db, GUILD, body())
    await keep(db, GUILD, body(extra_roles=1))

    back = await keep(db, GUILD, body())

    assert back.outcome == SAVED and await structure_store.count(db, GUILD) == 3


async def test_only_the_newest_are_kept_and_the_count_says_how_many_went(db):
    for n in range(4):
        await keep(db, GUILD, body(extra_roles=n), keep=60)

    last = await keep(db, GUILD, body(extra_roles=9), keep=2)

    assert last.pruned == 3
    rows = await structure_store.listed(db, GUILD)
    assert [row["roles"] for row in rows] == [10, 4]
    assert rows[0]["id"] == last.row["id"]


async def test_one_servers_snapshots_never_touch_anothers(db):
    await keep(db, GUILD, body())
    await keep(db, OTHER, body(extra_roles=1), keep=1)

    assert await structure_store.count(db, GUILD) == 1
    assert await structure_store.count(db, OTHER) == 1
    mine = await structure_store.latest(db, GUILD)
    assert await structure_store.get(db, OTHER, mine["id"]) is None
    assert (await structure_store.get(db, GUILD, mine["id"]))["id"] == mine["id"]


async def test_the_list_comes_newest_first_without_the_bodies(db):
    await keep(db, GUILD, body())
    await keep(db, GUILD, body(extra_roles=1))

    rows = await structure_store.listed(db, GUILD)

    assert [row["roles"] for row in rows] == [2, 1]
    assert "body" not in rows[0].keys()
    assert len(await structure_store.listed(db, GUILD, limit=1)) == 1


async def test_nothing_is_due_twice_on_one_day_after_a_look_that_worked(db):
    assert structure_store.daily_due(None, "2026-10-05", retries=3)

    await structure_store.record_look(db, GUILD, UNCHANGED, day="2026-10-05", now=NOON)
    found = await structure_store.look(db, GUILD)

    assert (found["outcome"], found["last_day"], found["attempts"]) == (UNCHANGED, "2026-10-05", 0)
    assert found["last_at"] == NOON.isoformat()
    assert not structure_store.daily_due(found, "2026-10-05", retries=3)
    assert structure_store.daily_due(found, "2026-10-06", retries=3)


async def test_a_failed_daily_look_is_due_again_until_its_tries_run_out(db):
    for attempt in (1, 2, 3):
        await structure_store.record_look(
            db, GUILD, FAILED, day="2026-10-05", reason="Discord said no"
        )
        found = await structure_store.look(db, GUILD)
        assert found["attempts"] == attempt and found["reason"] == "Discord said no"
        assert structure_store.daily_due(found, "2026-10-05", retries=3) is (attempt < 3)

    assert structure_store.daily_due(found, "2026-10-06", retries=3)
    await structure_store.record_look(db, GUILD, FAILED, day="2026-10-06", reason="again")
    assert (await structure_store.look(db, GUILD))["attempts"] == 1


async def test_a_look_that_works_clears_the_failure_it_followed(db):
    await structure_store.record_look(db, GUILD, FAILED, day="2026-10-05", reason="no")
    await structure_store.record_look(db, GUILD, SAVED, day="2026-10-05")

    found = await structure_store.look(db, GUILD)

    assert (found["outcome"], found["reason"], found["attempts"]) == (SAVED, None, 0)


async def test_a_look_by_hand_never_spends_the_days_turn(db):
    await structure_store.record_look(db, GUILD, SAVED)

    found = await structure_store.look(db, GUILD)

    assert found["last_day"] is None
    assert structure_store.daily_due(found, "2026-10-05", retries=3)
