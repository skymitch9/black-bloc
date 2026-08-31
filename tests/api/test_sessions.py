from __future__ import annotations

from datetime import UTC, datetime, timedelta

from black_bloc.api import sessions

USER_ID = 7
DAY = 24 * 60 * 60


async def rows_in(db) -> list:
    cur = await db.conn.execute("SELECT * FROM sessions ORDER BY rowid")
    return list(await cur.fetchall())


async def test_a_started_session_is_written_down_and_alive(web):
    sid = await sessions.start(web, USER_ID, ttl=DAY)

    rows = await rows_in(web.db)
    assert len(rows) == 1 and rows[0]["id"] == sid
    assert rows[0]["user_id"] == USER_ID and rows[0]["revoked_at"] is None
    assert await sessions.alive(web, sid) is True


async def test_ending_a_session_revokes_the_row_and_the_cache_at_once(web):
    sid = await sessions.start(web, USER_ID, ttl=DAY)
    await sessions.end(web, sid)

    assert await sessions.alive(web, sid) is False
    assert (await rows_in(web.db))[0]["revoked_at"] is not None
    assert sessions.cache_for(web).get(sid) is False


async def test_ending_a_session_twice_keeps_the_first_revocation(web):
    sid = await sessions.start(web, USER_ID, ttl=DAY)
    await sessions.end(web, sid)
    first = (await rows_in(web.db))[0]["revoked_at"]
    await sessions.end(web, sid)

    assert (await rows_in(web.db))[0]["revoked_at"] == first


async def test_an_id_nobody_wrote_down_is_not_alive(web):
    assert await sessions.alive(web, "never-issued") is False


async def test_a_cookie_with_no_session_id_is_not_alive(web):
    for missing in (None, "", 7, {}):
        assert await sessions.alive(web, missing) is False


async def test_an_expired_row_is_not_alive_even_though_it_is_there(web):
    sid = await sessions.start(web, USER_ID, ttl=DAY)
    await web.db.conn.execute(
        "UPDATE sessions SET expires_at = ? WHERE id = ?",
        ((datetime.now(UTC) - timedelta(seconds=1)).isoformat(), sid),
    )
    await web.db.conn.commit()
    sessions.cache_for(web).forget(sid)

    assert await sessions.alive(web, sid) is False


async def test_an_unreadable_expiry_counts_as_expired(web):
    sid = await sessions.start(web, USER_ID, ttl=DAY)
    await web.db.conn.execute("UPDATE sessions SET expires_at = 'soon' WHERE id = ?", (sid,))
    await web.db.conn.commit()
    sessions.cache_for(web).forget(sid)

    assert await sessions.alive(web, sid) is False


async def test_starting_a_session_clears_out_ones_that_have_run_out(web):
    old = await sessions.start(web, USER_ID, ttl=DAY)
    await web.db.conn.execute(
        "UPDATE sessions SET expires_at = ? WHERE id = ?",
        ((datetime.now(UTC) - timedelta(days=30)).isoformat(), old),
    )
    await web.db.conn.commit()

    await sessions.start(web, USER_ID, ttl=DAY)

    assert [row["id"] for row in await rows_in(web.db)] != [old]
    assert len(await rows_in(web.db)) == 1


async def test_a_database_that_cannot_be_reached_is_not_a_sign_out(web, wf):
    """The data routes refuse on their own (`require_db`); a blip must not log everybody out."""
    headless = wf.Bot(web.settings, web.guild, None, web.store)

    assert sessions.database_of(headless) is None
    assert await sessions.alive(headless, "anything") is True
    assert await sessions.alive(headless, None) is True
    sid = await sessions.start(headless, USER_ID, ttl=DAY)
    assert sid
    await sessions.end(headless, sid)


def test_the_cache_forgets_a_verdict_when_its_ttl_runs_out():
    cache = sessions.SessionCache(ttl=30)
    cache.put("a", True, now=0)

    assert cache.get("a", now=29) is True
    assert cache.get("a", now=30) is None


def test_the_cache_cannot_grow_without_bound():
    cache = sessions.SessionCache(limit=10)
    for n in range(25):
        cache.put(str(n), True, now=0)

    assert len(cache._seen) == 10
    assert cache.get("0", now=0) is None
    assert cache.get("24", now=0) is True


def test_every_session_id_is_its_own():
    assert len({sessions.new_id() for _ in range(50)}) == 50
