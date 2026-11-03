from black_bloc import ninja_store as store

GUILD = 7
NINJA = "\U0001f977\U0001f3ff"
AT = "2026-11-02T20:00:00+00:00"
LATER = "2026-11-02T20:30:00+00:00"


async def made(db, user_id=1, channel_id=2, posts=1, until=None):
    return await store.add(db, GUILD, user_id, channel_id, NINJA, posts, until, 9, AT)


async def test_one_active_mark_per_member_and_channel(db):
    first = await made(db)
    assert first is not None
    assert await made(db) is None
    assert await made(db, channel_id=3) is not None
    await store.end(db, first, store.STAFF, AT)
    assert await made(db) is not None


async def test_a_claim_takes_one_post_and_never_the_last_one_twice(db):
    mark_id = await made(db, posts=1)
    assert await store.claim_post(db, mark_id, AT)
    assert not await store.claim_post(db, mark_id, AT)
    assert (await store.get(db, GUILD, mark_id))["posts_left"] == 0
    await store.give_back(db, mark_id)
    assert (await store.get(db, GUILD, mark_id))["posts_left"] == 1


async def test_a_time_only_mark_is_claimed_until_its_clock_passes(db):
    mark_id = await made(db, posts=None, until=LATER)
    assert await store.claim_post(db, mark_id, AT)
    assert (await store.get(db, GUILD, mark_id))["posts_left"] is None
    assert not await store.claim_post(db, mark_id, LATER)


async def test_due_finds_spent_and_timed_out_marks_only(db):
    spent = await made(db, user_id=1, posts=0)
    timed = await made(db, user_id=2, posts=None, until=AT)
    await made(db, user_id=3, posts=2, until=LATER)
    assert [row["id"] for row in await store.due(db, AT)] == [spent, timed]


async def test_end_is_once_and_the_lists_split_active_from_ended(db):
    one = await made(db, user_id=1)
    two = await made(db, user_id=2)
    assert await store.end(db, one, store.TIME, LATER)
    assert not await store.end(db, one, store.STAFF, LATER)
    assert [row["id"] for row in await store.active(db, GUILD)] == [two]
    [ended] = await store.recent_ended(db, GUILD)
    assert (ended["id"], ended["ended_because"]) == (one, store.TIME)
    assert [tuple(row) for row in await store.active_everywhere(db)] == [(GUILD, 2, 2)]
    assert (await store.active_for(db, GUILD, 2, 2))["id"] == two
    assert await store.active_for(db, GUILD, 1, 2) is None
