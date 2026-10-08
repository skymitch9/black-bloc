# ruff: noqa: F401, F811
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from black_bloc import brackets_people as people
from black_bloc import brackets_sets as sets
from black_bloc import brackets_store as store_
from black_bloc.logkinds import VIA_WEBSITE
from tests.test_brackets_moves import (
    ADA,
    BEA,
    CY,
    GUILD,
    STAFF,
    TO,
    bot,
    entrant_id,
    guild,
    made,
    moves,
    rows,
    signed_up,
    started,
    the_set,
    who,
)


async def test_signing_up_is_a_members_own_move_and_only_while_signups_are_open(bot, guild):
    tid = await made(bot, guild)
    early = await people.join(bot, guild, who(guild, ADA), tid)
    assert (early.code, "a draft" in early.message) == ("wrong_state", True)
    await moves.open_signups(bot, guild, who(guild, TO), tid)
    assert (await people.join(bot, guild, who(guild, ADA), tid)).ok
    again = await people.join(bot, guild, who(guild, ADA), tid)
    assert again.code == "already_in"
    ada = await store_.entrant_of(bot.db, tid, ADA)
    assert (ada["name"], ada["added_by"], ada["seed"]) == ("Ada", ADA, 1)


async def test_two_sign_ups_at_once_leave_one_entrant(bot, guild):
    tid = await made(bot, guild)
    await moves.open_signups(bot, guild, who(guild, TO), tid)
    first, second = await asyncio.gather(
        people.join(bot, guild, who(guild, ADA), tid), people.join(bot, guild, who(guild, ADA), tid)
    )
    assert sorted([first.ok, second.ok]) == [False, True]
    assert len(await store_.entrants(bot.db, tid)) == 1


async def test_the_cap_stops_sign_ups_but_not_the_to(bot, guild):
    tid = await signed_up(bot, guild, ADA, BEA, entrant_cap=2)
    full = await people.join(bot, guild, who(guild, CY), tid)
    assert (full.code, "full at 2" in full.message) == ("full", True)
    assert (await people.add_entrant(bot, guild, who(guild, TO), tid, user_id=CY)).ok


async def test_leaving_lets_you_back_in_but_a_removal_stands(bot, guild):
    tid = await signed_up(bot, guild, ADA, BEA)
    ada, bea = await entrant_id(bot, tid, ADA), await entrant_id(bot, tid, BEA)
    left = await people.drop(bot, guild, who(guild, ADA), tid, ada)
    assert (left.ok, left.message) == (True, "You have left **Knuck Up 12**.")
    assert (await people.join(bot, guild, who(guild, ADA), tid)).ok
    assert (await people.remove_entrant(bot, guild, who(guild, TO), tid, bea)).ok
    refused = await people.join(bot, guild, who(guild, BEA), tid)
    assert refused.code == "removed"
    assert (await people.restore_entrant(bot, guild, who(guild, TO), tid, bea)).ok
    assert not (await store_.entrant(bot.db, tid, bea))["dropped"]


async def test_nobody_drops_or_checks_in_somebody_else(bot, guild):
    tid = await signed_up(bot, guild, ADA, BEA)
    ada = await entrant_id(bot, tid, ADA)
    outcome = await people.drop(bot, guild, who(guild, BEA), tid, ada)
    assert (outcome.code, outcome.status) == ("not_yours", 403)


async def test_a_guest_is_added_by_hand_and_needs_a_name(bot, guild):
    tid = await signed_up(bot, guild, ADA)
    nameless = await people.add_entrant(bot, guild, who(guild, TO), tid)
    assert nameless.code == "no_name"
    outcome = await people.add_entrant(bot, guild, who(guild, TO), tid, name="Remy (offline)")
    assert outcome.ok
    guest = [one for one in await store_.entrants(bot.db, tid) if one["user_id"] is None]
    assert [(one["name"], one["added_by"]) for one in guest] == [("Remy (offline)", TO)]


async def test_check_in_removes_no_shows_and_checks_guests_in_for_the_to(bot, guild):
    tid = await signed_up(bot, guild, ADA, BEA, CY)
    await people.add_entrant(bot, guild, who(guild, TO), tid, name="Remy")
    assert (await people.open_check_in(bot, guild, who(guild, TO), tid)).ok
    early = await moves.start(bot, guild, who(guild, TO), tid)
    assert early.code == "check_in_open"
    assert (
        await people.set_check_in(bot, guild, who(guild, ADA), tid, await entrant_id(bot, tid, ADA))
    ).ok
    assert (
        await people.set_check_in(bot, guild, who(guild, TO), tid, await entrant_id(bot, tid, BEA))
    ).ok
    closed = await people.close_check_in(bot, guild, who(guild, TO), tid)
    assert closed.message == "Check-in for **Knuck Up 12** is closed — 1 no-show(s) taken out."
    cy = await store_.entrant_of(bot.db, tid, CY)
    assert (cy["dropped"], cy["dropped_why"]) == (1, "no_show")
    assert (await moves.start(bot, guild, who(guild, TO), tid)).ok
    row = await store_.tournament(bot.db, GUILD, tid)
    current = await store_.bracket(bot.db, row)
    names = {one["id"]: one["name"] for one in await store_.entrants(bot.db, tid)}
    assert sorted(names[one] for one in current.entrants) == ["Ada", "Bea", "Remy"]


async def test_check_in_closes_by_itself_once_its_window_passes(bot, guild):
    tid = await signed_up(bot, guild, ADA, BEA)
    await people.open_check_in(bot, guild, who(guild, TO), tid)
    row = await store_.tournament(bot.db, GUILD, tid)
    closes = datetime.fromisoformat(row["check_in_closes_at"])
    assert await people.close_due_check_ins(bot, guild, closes - timedelta(seconds=1)) == []
    assert await people.close_due_check_ins(bot, guild, closes) == [tid]
    assert (await store_.tournament(bot.db, GUILD, tid))["state"] == "seeding"


async def test_a_dq_forfeits_and_lifting_it_keeps_the_forfeit(bot, guild):
    tid = await started(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    bea = await entrant_id(bot, tid, BEA)
    outcome = await people.dq(bot, guild, who(guild, TO), tid, bea)
    assert (
        outcome.message
        == "Bea is disqualified from **Knuck Up 12**; their remaining sets are forfeited."
    )
    match = await the_set(bot, tid, "W1-1")
    assert (match.state, match.forfeit) == ("complete", "dq")
    twice = await people.dq(bot, guild, who(guild, TO), tid, bea)
    assert twice.code == "already_out"
    assert (await people.restore_entrant(bot, guild, who(guild, TO), tid, bea)).ok
    row = await store_.entrant(bot.db, tid, bea)
    assert (row["dq"], (await the_set(bot, tid, "W1-1")).forfeit) == (0, "dq")


async def test_a_player_dropping_mid_bracket_forfeits_their_sets(bot, guild):
    tid = await started(bot, guild, ADA, BEA, format="round_robin")
    ada = await entrant_id(bot, tid, ADA)
    outcome = await people.drop(bot, guild, who(guild, ADA), tid, ada)
    assert outcome.ok
    entrant = await store_.entrant(bot.db, tid, ada)
    assert (entrant["dropped"], entrant["dropped_why"]) == (1, "dropped")
    assert (await the_set(bot, tid, "R1-1")).forfeit == "drop"


async def test_someone_out_before_the_start_cannot_be_put_back_into_a_running_bracket(bot, guild):
    tid = await signed_up(bot, guild, ADA, BEA, CY)
    cy = await entrant_id(bot, tid, CY)
    assert (await people.remove_entrant(bot, guild, who(guild, TO), tid, cy)).ok
    await moves.close_signups(bot, guild, who(guild, TO), tid)
    assert (await moves.start(bot, guild, who(guild, TO), tid)).ok
    outcome = await people.restore_entrant(bot, guild, who(guild, TO), tid, cy)
    assert (outcome.ok, outcome.code, outcome.status) == (False, "not_in_bracket", 409)
    assert outcome.message == "Cy is not playing in **Knuck Up 12**, so nothing was done."
    assert (await store_.entrant(bot.db, tid, cy))["dropped"] == 1
    listed = {row["id"]: row for row in await store_.tournaments(bot.db, GUILD)}
    assert listed[tid]["entrant_count"] == 2


async def test_check_in_opening_tells_the_website_a_plain_time_and_discord_a_timestamp(
    bot, guild
):
    await bot.store.set(GUILD, "default_timezone", "America/Phoenix")
    tid = await signed_up(bot, guild, ADA, BEA)
    site = await people.open_check_in(bot, guild, who(guild, TO), tid, via=VIA_WEBSITE)
    assert "<t:" not in site.message
    row = await store_.tournament(bot.db, GUILD, tid)
    closes = datetime.fromisoformat(row["check_in_closes_at"])
    local = closes.astimezone(ZoneInfo("America/Phoenix"))
    hour = local.hour % 12 or 12
    noon = "am" if local.hour < 12 else "pm"
    assert site.message == (
        f"Check-in for **Knuck Up 12** is open until {hour}:{local.minute:02d} {noon} MST."
    )
    await people.close_check_in(bot, guild, who(guild, TO), tid)
    discord = await people.open_check_in(bot, guild, who(guild, TO), tid)
    assert "<t:" in discord.message


async def test_a_check_in_with_an_unreadable_closing_time_closes_at_the_next_sweep(
    bot, guild, caplog
):
    tid = await signed_up(bot, guild, ADA, BEA)
    await people.open_check_in(bot, guild, who(guild, TO), tid)
    await store_.update(bot.db, tid, {"check_in_closes_at": "soon"})
    assert await people.close_due_check_ins(bot, guild) == [tid]
    assert (await store_.tournament(bot.db, GUILD, tid))["state"] == "seeding"
    assert sum("could not be read" in one.getMessage() for one in caplog.records) == 1


async def test_a_dq_in_pools_forfeits_their_pool_sets_and_keeps_them_out_of_the_final(bot, guild):
    tid = await started(
        bot, guild, ADA, BEA, CY, STAFF, format="double", pools_format="round_robin",
        advance_per_pool=1,
    )
    ada = await entrant_id(bot, tid, ADA)
    outcome = await people.dq(bot, guild, who(guild, TO), tid, ada)
    assert outcome.ok and outcome.changed == ("A.R1-1",)
    match = await the_set(bot, tid, "A.R1-1")
    assert (match.state, match.forfeit, match.loser) == ("complete", "dq", ada)
    await sets.report(bot, guild, who(guild, TO), tid, "B.R1-1", 2, 0)
    assert (await moves.advance(bot, guild, who(guild, TO), tid)).ok
    seated = {
        e
        for one in await store_.sets(bot.db, tid)
        if one["phase"] == "final"
        for e in (one["slot_a"], one["slot_b"])
        if e
    }
    assert ada not in seated and len(seated) == 2
    assert (await people.restore_entrant(bot, guild, who(guild, TO), tid, ada)).ok
