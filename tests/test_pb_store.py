from datetime import timedelta

import pytest

from black_bloc import pb_store
from tests.test_pb_looks import ADA, BEA, GUILD, NOW, OTHER, ZFG, best, link


async def write(db, user_id=ADA, runner=ZFG, source=pb_store.AUTO, login="zfg1"):
    return await pb_store.write_match(
        db, GUILD, user_id, runner, source=source, twitch_login=login, now=NOW
    )


async def test_links_are_read_case_folded_from_go_lives_own_table(db):
    await link(db, ADA, "ZFG1")

    assert await pb_store.links(db) == {ADA: "zfg1"}


async def test_a_match_is_stored_with_where_it_came_from_and_how(db):
    row = await write(db)

    assert (row["state"], row["source"], row["state_by"]) == (pb_store.MATCHED, "auto", "auto")
    assert (row["src_user_id"], row["src_name"], row["twitch_login"]) == (ZFG.id, "zfg", "zfg1")
    assert row["matched_at"] == NOW.isoformat() and row["baseline_at"] is None
    assert [one["user_id"] for one in await pb_store.matches(db, GUILD)] == [ADA]
    assert await pb_store.holder_of(db, GUILD, ZFG.id) == ADA


async def test_one_runner_belongs_to_one_member_per_server(db):
    await write(db)

    with pytest.raises(pb_store.RunnerTaken) as caught:
        await write(db, BEA)

    assert caught.value.holder_id == ADA
    assert await pb_store.match(db, GUILD, BEA) is None
    await pb_store.write_match(db, GUILD + 1, BEA, ZFG, source="auto", twitch_login="zfg1")


async def test_a_new_identity_wipes_the_baseline(db):
    await write(db)
    await pb_store.record_look(db, GUILD, ADA, [best("r1")], first=True, now=NOW)

    row = await write(db, runner=OTHER, source=pb_store.STAFF)

    assert await pb_store.baseline(db, GUILD, ADA) == {}
    assert row["baseline_at"] is None and row["looked_at"] is None and row["source"] == "staff"


async def test_a_look_upserts_and_never_deletes_a_slot_it_did_not_see(db):
    await write(db)
    await pb_store.record_look(
        db, GUILD, ADA, [best("r1"), best("r2", slot="g2|c1||")], first=True, now=NOW
    )
    later = NOW + timedelta(hours=1)

    await pb_store.record_look(
        db, GUILD, ADA, [best("r9", seconds=90.0)], first=False, newest=True, now=later
    )

    held = await pb_store.baseline(db, GUILD, ADA)
    assert {slot: row["run_id"] for slot, row in held.items()} == {"g1|c1||": "r9", "g2|c1||": "r2"}
    row = await pb_store.match(db, GUILD, ADA)
    assert row["baseline_at"] == NOW.isoformat()
    assert row["looked_at"] == later.isoformat() == row["last_pb_at"]


async def test_an_opt_out_keeps_the_runner_and_a_block_drops_it(db):
    await write(db)
    await pb_store.record_look(db, GUILD, ADA, [best("r1")], first=True, now=NOW)

    out = await pb_store.write_state(
        db, GUILD, ADA, pb_store.OPTED_OUT, state_by=pb_store.MEMBER, set_by=ADA, keep_runner=True
    )
    assert (out["state"], out["state_by"], out["src_user_id"]) == ("opted_out", "member", ZFG.id)
    assert len(await pb_store.baseline(db, GUILD, ADA)) == 1

    blocked = await pb_store.write_state(db, GUILD, ADA, pb_store.BLOCKED, state_by=pb_store.STAFF)
    assert (blocked["state"], blocked["src_user_id"], blocked["source"]) == ("blocked", None, None)
    assert await pb_store.baseline(db, GUILD, ADA) == {}
    assert await pb_store.holder_of(db, GUILD, ZFG.id) is None


async def test_restoring_goes_back_to_the_kept_runner_or_to_be_looked_up(db):
    await write(db)
    await pb_store.write_state(
        db, GUILD, ADA, pb_store.OPTED_OUT, state_by=pb_store.MEMBER, keep_runner=True
    )
    await pb_store.write_state(db, GUILD, BEA, pb_store.BLOCKED, state_by=pb_store.STAFF)

    kept = await pb_store.restore(db, GUILD, ADA, state_by=pb_store.STAFF, set_by=BEA)
    assert (kept["state"], kept["state_by"], kept["set_by"]) == ("opted_out", "member", ADA)
    ada = await pb_store.restore(
        db, GUILD, ADA, state_by=pb_store.MEMBER, set_by=ADA, ends_opt_out=True
    )
    bea = await pb_store.restore(db, GUILD, BEA, state_by=pb_store.STAFF)
    assert ada["opted_out_at"] is None

    assert (ada["state"], ada["state_by"], ada["src_user_id"]) == ("matched", "member", ZFG.id)
    assert (bea["state"], bea["checked_at"]) == ("none", None)
    assert await pb_store.restore(db, GUILD, 12345, state_by=pb_store.STAFF) is None


async def test_a_run_is_claimed_once_for_the_life_of_the_database(db):
    first = await pb_store.claim_post(db, GUILD, ADA, best("r1"), "zfg", now=NOW)
    second = await pb_store.claim_post(db, GUILD, ADA, best("r1"), "zfg", now=NOW)

    assert first is not None and second is None
    assert await pb_store.posts(db, GUILD) == []

    await pb_store.settle_post(
        db, first, pb_store.REHEARSED, channel_id=502, aimed_at=503, message_id=1001
    )
    row = (await pb_store.posts(db, GUILD))[0]
    assert (row["outcome"], row["channel_id"], row["aimed_at"], row["message_id"]) == (
        "rehearsed",
        502,
        503,
        1001,
    )
    assert (row["game"], row["seconds"], row["place"], row["src_name"]) == (
        "Ocarina of Time",
        100.0,
        3,
        "zfg",
    )


async def test_recent_posts_are_newest_first_and_capped(db):
    for at in range(4):
        claimed = await pb_store.claim_post(db, GUILD, ADA, best(f"r{at}"), "zfg", now=NOW)
        await pb_store.settle_post(db, claimed, pb_store.POSTED)

    listed = await pb_store.posts(db, GUILD, 2)

    assert [row["run_id"] for row in listed] == ["r3", "r2"]


async def test_a_members_own_look_error_is_fresh_only_the_first_time(db):
    await write(db)

    assert await pb_store.record_look_error(db, GUILD, ADA, "too large", NOW) is True
    assert await pb_store.record_look_error(db, GUILD, ADA, "too large", NOW) is False

    await pb_store.record_look(db, GUILD, ADA, [], first=True, now=NOW)
    assert (await pb_store.match(db, GUILD, ADA))["look_error"] is None


async def test_an_outage_counts_its_failures_and_one_good_call_ends_it(db):
    until = NOW + timedelta(minutes=5)

    assert await pb_store.record_outage(db, GUILD, "down", until, NOW) == 1
    assert await pb_store.record_outage(db, GUILD, "still down", until, NOW) == 2
    state = await pb_store.looks(db, GUILD)
    assert (state["outcome"], state["reason"], state["outage_since"]) == (
        "failed",
        "still down",
        NOW.isoformat(),
    )
    assert pb_store.parsed(state["backoff_until"]) == until

    assert await pb_store.record_ok(db, GUILD, found=1, now=NOW) is True
    assert await pb_store.record_ok(db, GUILD, found=0, now=NOW) is False
    state = await pb_store.looks(db, GUILD)
    assert (state["failures"], state["backoff_until"], state["outage_since"]) == (0, None, None)
    assert state["last_ok_at"] == NOW.isoformat()


async def test_the_summary_hands_over_its_counts_and_starts_again(db):
    assert await pb_store.take_summary(db, GUILD, NOW) == (0, 0)
    await pb_store.record_ok(db, GUILD, found=0, now=NOW)
    await pb_store.record_ok(db, GUILD, found=2, now=NOW)

    assert await pb_store.take_summary(db, GUILD, NOW + timedelta(hours=1)) == (2, 2)
    assert await pb_store.take_summary(db, GUILD, NOW + timedelta(hours=2)) == (0, 0)


def test_a_timestamp_that_cannot_be_read_is_none_not_a_crash():
    assert pb_store.parsed("not a time") is None and pb_store.parsed(None) is None
    assert pb_store.parsed("2026-10-05T18:00:00").tzinfo is not None


async def test_an_opt_out_is_remembered_under_every_state_staff_put_on_top(db):
    await write(db)
    out = await pb_store.write_state(
        db, GUILD, ADA, pb_store.OPTED_OUT, state_by=pb_store.MEMBER, keep_runner=True, now=NOW
    )

    blocked = await pb_store.write_state(db, GUILD, ADA, pb_store.BLOCKED, state_by=pb_store.STAFF)

    assert out["opted_out_at"] == NOW.isoformat() == blocked["opted_out_at"]
    assert (await pb_store.match(db, GUILD, BEA)) is None


async def test_a_miss_counts_up_and_a_good_look_starts_the_count_again(db):
    await write(db)
    await pb_store.record_look(db, GUILD, ADA, [best("r1")], first=True, now=NOW)

    assert await pb_store.record_miss(db, GUILD, ADA, "nothing there", NOW) == 1
    assert await pb_store.record_miss(db, GUILD, ADA, "nothing there", NOW) == 2
    assert (await pb_store.match(db, GUILD, ADA))["look_error"] == "nothing there"
    assert len(await pb_store.baseline(db, GUILD, ADA)) == 1

    await pb_store.record_look(db, GUILD, ADA, [best("r1")], first=False, now=NOW)
    row = await pb_store.match(db, GUILD, ADA)
    assert (row["misses"], row["look_error"]) == (0, None)


async def test_a_runner_that_went_keeps_the_baseline_for_the_same_runner_only(db):
    await write(db)
    await pb_store.record_look(db, GUILD, ADA, [best("r1")], first=True, now=NOW)

    gone = await pb_store.runner_gone(db, GUILD, ADA, "runner_gone", NOW)
    assert (gone["state"], gone["src_user_id"], gone["gone_src_user_id"]) == ("none", None, ZFG.id)
    assert await pb_store.holder_of(db, GUILD, ZFG.id) is None
    assert len(await pb_store.baseline(db, GUILD, ADA)) == 1

    back = await write(db)
    assert back["baseline_at"] == NOW.isoformat() and back["gone_src_user_id"] is None
    assert len(await pb_store.baseline(db, GUILD, ADA)) == 1

    await pb_store.runner_gone(db, GUILD, ADA, "runner_gone", NOW)
    other = await write(db, runner=OTHER)
    assert other["baseline_at"] is None and await pb_store.baseline(db, GUILD, ADA) == {}


async def test_the_last_runs_recorded_without_a_post_stay_until_the_next_such_look(db):
    await write(db)

    await pb_store.record_look(
        db, GUILD, ADA, [best("r1")], first=True, quiet={"too_old": 2}, now=NOW
    )
    await pb_store.record_look(db, GUILD, ADA, [best("r1")], first=False, now=NOW)

    row = await pb_store.match(db, GUILD, ADA)
    assert pb_store.quiet_of(row) == {"too_old": 2, "at": NOW.isoformat()}
    assert pb_store.quiet_of(None) is None and pb_store.quiet_of({"quiet": "{"}) is None


async def test_stale_claims_become_unconfirmed_once_and_are_listed(db):
    await pb_store.claim_post(db, GUILD, ADA, best("r1"), "zfg", now=NOW)
    settled = await pb_store.claim_post(db, GUILD, ADA, best("r2"), "zfg", now=NOW)
    await pb_store.settle_post(db, settled, pb_store.POSTED)

    first = await pb_store.settle_stale_claims(db, GUILD, "never confirmed")
    second = await pb_store.settle_stale_claims(db, GUILD, "never confirmed")

    assert [row["run_id"] for row in first] == ["r1"] and second == []
    shown = {
        row["run_id"]: (row["outcome"], row["reason"]) for row in await pb_store.posts(db, GUILD)
    }
    assert shown == {"r1": ("unconfirmed", "never confirmed"), "r2": ("posted", None)}
