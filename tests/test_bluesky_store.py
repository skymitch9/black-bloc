from datetime import timedelta

from black_bloc import bluesky as rules
from black_bloc import bluesky_store as store
from tests.bluesky_fakes import GUILD, NOW, recorded


def items():
    return rules.items_of(recorded()["feed"])


async def test_a_claim_is_taken_once(db):
    item = items()[0]

    assert await store.claim(db, GUILD, item, NOW)
    assert not await store.claim(db, GUILD, item, NOW)
    row = await store.get(db, GUILD, item.uri)
    assert row["status"] == rules.CLAIMED and row["text"] == item.text


async def test_a_claim_takes_a_row_back_only_from_the_statuses_it_names(db):
    first, second = items()[:2]
    await store.record(db, GUILD, first, rules.WOULD_POST, NOW)
    await store.claim(db, GUILD, second, NOW)
    await store.settle(db, GUILD, second.uri, rules.POSTED, NOW, channel_id=1, message_id=2)

    assert not await store.claim(db, GUILD, first, NOW, over=(rules.RETRY,))
    assert await store.claim(db, GUILD, first, NOW, over=(rules.WOULD_POST,))
    assert not await store.claim(db, GUILD, second, NOW, over=(rules.WOULD_POST,))


async def test_a_failed_send_goes_back_once_then_fails(db):
    item = items()[0]
    await store.claim(db, GUILD, item, NOW)

    assert await store.let_go(db, GUILD, item.uri, False) == rules.RETRY
    assert await store.claim(db, GUILD, item, NOW, over=(rules.RETRY,))
    assert await store.let_go(db, GUILD, item.uri, True) == rules.FAILED


async def test_record_never_overwrites(db):
    item = items()[0]

    assert await store.record(db, GUILD, item, rules.SKIPPED_OLD, NOW)
    assert not await store.record(db, GUILD, item, rules.SKIPPED_KIND, NOW)
    assert (await store.get(db, GUILD, item.uri))["status"] == rules.SKIPPED_OLD


async def test_prune_keeps_the_newest_rows(db):
    for at, item in enumerate(items()[:5]):
        await store.record(db, GUILD, item, rules.SKIPPED_OLD, NOW + timedelta(seconds=at))
    await store.record(db, GUILD + 1, items()[0], rules.SKIPPED_OLD, NOW)

    assert await store.prune(db, GUILD, 3) == 2
    kept = [row["uri"] for row in await store.recent(db, GUILD, 10)]
    assert kept == [item.uri for item in items()[2:5]][::-1]
    assert await store.get(db, GUILD + 1, items()[0].uri) is not None


async def test_reads_count_failures_and_a_good_read_clears_them(db):
    assert await store.read_failed(db, GUILD, NOW, "Bluesky answered 403") == 1
    assert await store.read_failed(db, GUILD, NOW, "Bluesky answered 403") == 2
    await store.read_ok(db, GUILD, NOW)

    row = await store.get_read(db, GUILD)
    assert row["failures"] == 0 and row["last_error"] is None
    assert row["last_ok_at"] == NOW.isoformat()


async def test_a_standing_error_is_reported_changed_once(db):
    assert await store.set_error(db, GUILD, "no channel")
    assert not await store.set_error(db, GUILD, "no channel")
    assert await store.set_error(db, GUILD, "gone")
