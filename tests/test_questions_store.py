from datetime import UTC, datetime

from black_bloc import questions as rules
from black_bloc import questions_store as store

GUILD = 7
NOW = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)


async def test_many_questions_queue_in_the_order_they_were_written(db):
    ids = await store.add_many(db, GUILD, ["one?", "two?", "three?"], 5, NOW)
    more = await store.add_many(db, GUILD, ["four?"], 5, NOW)

    rows = await store.queued(db, GUILD)
    assert [row["body"] for row in rows] == ["one?", "two?", "three?", "four?"]
    assert [row["id"] for row in rows] == ids + more
    assert (await store.first_queued(db, GUILD))["body"] == "one?"
    assert await store.queued(db, GUILD + 1) == []


async def test_a_swap_trades_two_places_and_back_in_queue_goes_first_or_last(db):
    first, second, third = await store.add_many(db, GUILD, ["a", "b", "c"], 5, NOW)
    rows = await store.queued(db, GUILD)
    await store.swap(db, rows[0], rows[1])
    assert [row["body"] for row in await store.queued(db, GUILD)] == ["b", "a", "c"]

    await store.mark_posted(db, third, "2026-10-19T16:00:00+00:00", rules.BY_BOT, 1, 2, NOW)
    assert [row["body"] for row in await store.queued(db, GUILD)] == ["b", "a"]
    await store.back_in_queue(db, GUILD, third, top=True)
    row = await store.get(db, GUILD, third)
    assert row["status"] == rules.QUEUED and row["message_id"] is None and row["slot_at"] is None
    assert [row["body"] for row in await store.queued(db, GUILD)] == ["c", "b", "a"]

    await store.set_removed(db, first, NOW)
    await store.back_in_queue(db, GUILD, first, top=False)
    assert [row["body"] for row in await store.queued(db, GUILD)] == ["c", "b", "a"]
    assert second


async def test_the_history_is_everything_not_queued_newest_first(db):
    one, two = await store.add_many(db, GUILD, ["a", "b"], 5, NOW)
    await store.set_removed(db, one, datetime(2026, 10, 1, tzinfo=UTC))
    await store.mark_posted(db, two, "x", rules.BY_OWNER, 1, 2, datetime(2026, 10, 2, tzinfo=UTC))

    assert [row["id"] for row in await store.history(db, GUILD)] == [two, one]
    assert (await store.latest_posted(db, GUILD))["id"] == two


async def test_a_slot_row_is_made_once_and_keeps_its_first_sighting(db):
    first = await store.ensure_slot(db, GUILD, "s1", NOW)
    again = await store.ensure_slot(db, GUILD, "s1", datetime(2026, 10, 20, tzinfo=UTC))
    assert first["status"] == rules.PENDING and again["seen_at"] == first["seen_at"]

    await store.set_note(db, GUILD, "s1", "no channel")
    await store.set_warned(db, GUILD, "s1", NOW)
    await store.set_slot(db, GUILD, "s1", rules.POSTED, NOW, question_id=4)
    row = await store.get_slot(db, GUILD, "s1")
    assert (row["status"], row["question_id"], row["note"]) == (rules.POSTED, 4, None)
    assert row["warned_at"] == NOW.isoformat() and row["resolved_at"] == NOW.isoformat()
    assert (await store.slot_of_question(db, GUILD, 4))["slot_at"] == "s1"

    await store.set_slot(db, GUILD, "s1", rules.PENDING, NOW)
    assert (await store.get_slot(db, GUILD, "s1"))["resolved_at"] is None
