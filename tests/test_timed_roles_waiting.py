from datetime import timedelta

import pytest

from black_bloc import timed_roles_waiting as waits

GUILD = 7


def test_day_offsets_read_commas_in_any_order_and_refuse_anything_else():
    assert waits.day_offsets("13, 0 ,7") == [0, 7, 13]
    assert waits.day_offsets("0;7") == [0, 7]
    assert waits.day_offsets("7, 7") == [7]
    assert waits.day_offsets("") == []
    assert waits.day_offsets("a, 7") is None
    assert waits.day_offsets("-1") is None
    assert waits.day_offsets("400") is None
    assert waits.day_offsets(",".join(str(n) for n in range(11))) is None


def test_an_offset_at_or_past_the_removal_day_is_ignored_and_a_broken_key_reminds_never():
    assert waits.live_offsets("0, 7, 13, 14, 20", 14) == [0, 7, 13]
    assert waits.live_offsets("nonsense", 14) == []


def test_after_downtime_only_the_latest_due_stage_is_sent():
    start = waits.now() - timedelta(days=8)
    row = {"until": waits.iso(start), "stage": 0}
    assert waits.due_stage(row["until"], [0, 7, 13]) == 2
    assert waits.reminder_due(row, [0, 7, 13]) == 2
    assert waits.reminder_due({**row, "stage": 2}, [0, 7, 13]) is None
    future = {"until": waits.iso(waits.now() + timedelta(days=1)), "stage": 0}
    assert waits.reminder_due(future, [0, 7, 13]) is None


def test_removal_is_due_on_the_removal_day_counted_from_the_rough_end():
    start = waits.now() - timedelta(days=14, minutes=1)
    assert waits.removal_due({"until": waits.iso(start)}, 14)
    assert not waits.removal_due({"until": waits.iso(start)}, 15)
    assert waits.removal_at("nonsense", 14) is None


async def test_one_open_wait_per_member_and_role(db):
    until = waits.now() + timedelta(days=3)
    first = await waits.put(db, GUILD, 900, [10, 11], prompt_id=1, assigner_id=5, until=until, by=5)
    again = await waits.put(db, GUILD, 900, [10, 12], prompt_id=2, assigner_id=5, until=until, by=5)

    assert len(first) == 2 and len(again) == 1
    assert await waits.pairs(db, GUILD) == {(900, 10), (900, 11), (900, 12)}
    assert await waits.count_on_role(db, GUILD, 10) == 1


async def test_ending_moves_only_an_open_row_so_one_writer_wins(db):
    until = waits.now() + timedelta(days=3)
    [wait_id] = await waits.put(db, GUILD, 900, [10], prompt_id=1, assigner_id=5, until=until, by=5)

    assert await waits.end(db, [wait_id], waits.ATTACHED, by=1, menu_id=3) == [wait_id]
    assert await waits.end(db, [wait_id], waits.CAME_OFF) == []
    row = await waits.get(db, wait_id)
    assert (row["state"], row["menu_id"], row["ended_by"]) == (waits.ATTACHED, 3, 1)
    with pytest.raises(ValueError):
        await waits.end(db, [wait_id], waits.WAITING)


async def test_one_role_coming_off_ends_only_that_roles_wait(db):
    until = waits.now() + timedelta(days=3)
    await waits.put(db, GUILD, 900, [10, 11], prompt_id=1, assigner_id=5, until=until, by=5)

    ended = await waits.end_pairs(db, GUILD, 900, [11], waits.CAME_OFF)

    assert len(ended) == 1
    assert await waits.roles_waiting(db, GUILD, 900) == {10}


async def test_a_new_date_recomputes_the_stage_and_clears_failures(db):
    until = waits.now() - timedelta(days=8)
    [wait_id] = await waits.put(
        db, GUILD, 900, [10], prompt_id=1, assigner_id=5, until=until, by=5, offsets=[0, 7, 13]
    )
    assert (await waits.get(db, wait_id))["stage"] == 2
    await waits.failed_removal(db, [wait_id])

    later = waits.now() + timedelta(days=2)
    assert await waits.set_until(db, [wait_id], later, [0, 7, 13], 6) == 1
    row = await waits.get(db, wait_id)
    assert (row["stage"], row["remove_failures"], row["set_by"]) == (0, 0, 6)


async def test_revert_waits_again_once_and_never_beside_a_newer_wait(db):
    until = waits.now() - timedelta(days=20)
    [one, two] = await waits.put(
        db, GUILD, 900, [10, 11], prompt_id=1, assigner_id=5, until=until, by=5
    )
    await waits.mark_removed(db, [one, two])
    await waits.set_notice(db, [one, two], 333, 4444)
    lead = await waits.get(db, one)
    assert [row["id"] for row in await waits.notice_rows(db, lead)] == [one, two]
    await waits.put(db, GUILD, 900, [11], prompt_id=2, assigner_id=5, until=until, by=5)

    again = waits.now() + timedelta(days=14)
    assert await waits.wait_again(db, [one, two], again, 1) == [one]
    assert await waits.wait_again(db, [one, two], again, 1) == []
    row = await waits.get(db, one)
    assert (row["state"], row["stage"]) == (waits.WAITING, 0)
    assert (await waits.get(db, two))["state"] == waits.REMOVED


async def test_entries_are_one_per_member_with_their_soonest_end(db):
    soon = waits.now() + timedelta(days=1)
    later = waits.now() + timedelta(days=5)
    await waits.put(db, GUILD, 900, [10], prompt_id=1, assigner_id=5, until=later, by=5)
    await waits.put(db, GUILD, 900, [11], prompt_id=2, assigner_id=5, until=soon, by=5)
    await waits.put(db, GUILD, 901, [10], prompt_id=3, assigner_id=6, until=later, by=6)

    found = waits.entries(await waits.waiting(db, GUILD))

    assert [one["user_id"] for one in found] == [900, 901]
    assert sorted(found[0]["role_ids"]) == [10, 11]
    assert found[0]["until"] == waits.iso(soon)
    assert sorted(found[0]["prompt_ids"]) == [1, 2]
    assert await waits.people_waiting(db, GUILD) == 2
    assert await waits.guilds_waiting(db) == [GUILD]


async def test_a_member_who_leaves_stops_waiting_on_every_role(db):
    until = waits.now() + timedelta(days=3)
    await waits.put(db, GUILD, 900, [10, 11], prompt_id=1, assigner_id=5, until=until, by=5)

    assert len(await waits.end_member(db, GUILD, 900, waits.LEFT)) == 2
    assert await waits.waiting(db, GUILD) == []


def test_custom_ids_round_trip_through_their_templates():
    import re

    assert re.fullmatch(waits.LATER_TEMPLATE, waits.later_id(4))["prompt_id"] == "4"
    found = re.fullmatch(waits.MOVE_TEMPLATE, waits.move_id(900, waits.OFF))
    assert (found["user_id"], found["move"]) == ("900", "off")
    assert re.fullmatch(waits.PICK_TEMPLATE, waits.pick_id(900))["user_id"] == "900"
    assert re.fullmatch(waits.REMINDER_TEMPLATE, waits.reminder_id(None))["assigner_id"] == "0"
    assert re.fullmatch(waits.EVENT_TEMPLATE, waits.event_id(3))["menu_id"] == "3"
    assert re.fullmatch(waits.REVERT_TEMPLATE, waits.revert_id(8))["wait_id"] == "8"
