# ruff: noqa: F401, F811
from datetime import timedelta

import pytest

from black_bloc import pb_moves, pb_store
from black_bloc.logkinds import VIA_WEBSITE
from black_bloc.speedrun import SERVER, UNREACHABLE, Runner, SpeedrunError
from tests.test_pb_looks import (
    ADA,
    BEA,
    GUILD,
    NOW,
    OTHER,
    REHEARSAL,
    STAFFER,
    ZFG,
    best,
    bot,
    client,
    details_of,
    feed,
    guild,
    kinds,
    link,
    matched,
    seen,
    sent,
)


def staffer(guild):
    return guild.get_member(STAFFER)


async def test_a_member_opts_out_and_keeps_their_runner_for_later(bot, guild, feed, client):
    await matched(bot)
    await seen(feed, client, [best("r1")])

    outcome = await pb_moves.opt_out(bot, guild, guild.get_member(ADA))

    assert outcome.ok and "will not post" in outcome.message
    row = await pb_store.match(bot.db, GUILD, ADA)
    assert (row["state"], row["state_by"], row["src_user_id"]) == ("opted_out", "member", ZFG.id)
    found = await details_of(bot.db, "pbfeed.opted_out")
    assert (found["actor_id"], found["target_id"], found["via"]) == (ADA, ADA, "discord")


async def test_a_member_with_no_row_at_all_can_opt_out_before_any_lookup(
    bot, guild, feed, client
):
    await link(bot.db, BEA, "bea_tv")
    client.by_twitch["bea_tv"] = [OTHER]

    await pb_moves.opt_out(bot, guild, guild.get_member(BEA))
    took = await feed.tick(guild, NOW)

    row = await pb_store.match(bot.db, GUILD, BEA)
    assert (row["state"], row["src_user_id"]) == ("opted_out", None)
    assert took == 0 and client.asked == []


async def test_opting_back_in_takes_the_baseline_again_so_nothing_old_is_posted(
    bot, guild, feed, client
):
    await matched(bot)
    await seen(feed, client, [best("r1")])
    await pb_moves.opt_out(bot, guild, guild.get_member(ADA))
    during = NOW + timedelta(hours=1)
    client.bests[ZFG.id] = [best("r9", seconds=50.0, verified_at=during)]

    outcome = await pb_moves.opt_in(bot, guild, guild.get_member(ADA))
    looked = await feed.look(guild, ADA, now=NOW + timedelta(hours=2))

    row = await pb_store.match(bot.db, GUILD, ADA)
    assert outcome.ok and (row["state"], row["state_by"]) == ("matched", "member")
    assert (looked.found, looked.first) == (0, True) and sent(guild) == {}
    assert "pbfeed.opted_in" in await kinds(bot.db)


async def test_opting_in_when_not_opted_out_changes_nothing_and_logs_nothing(bot, guild, feed):
    await matched(bot)

    outcome = await pb_moves.opt_in(bot, guild, guild.get_member(ADA))

    assert outcome.ok and await kinds(bot.db) == []
    assert (await pb_store.match(bot.db, GUILD, ADA))["state"] == "matched"


async def test_a_blocked_member_cannot_opt_their_way_out_of_the_block(bot, guild, feed):
    await pb_moves.block(bot, guild, ADA, staffer(guild))

    for move in (pb_moves.opt_out, pb_moves.opt_in):
        outcome = await move(bot, guild, guild.get_member(ADA))
        assert not outcome.ok and outcome.code == "blocked" and "Staff" in outcome.message

    assert (await pb_store.match(bot.db, GUILD, ADA))["state"] == "blocked"


async def test_staff_set_a_match_by_hand_to_an_exact_name(bot, guild, feed, client):
    client.by_name["zfg"] = [ZFG, Runner("x9", "zfg2", "", None)]

    outcome = await pb_moves.set_by_hand(bot, guild, ADA, " @ZFG ", staffer(guild))

    row = await pb_store.match(bot.db, GUILD, ADA)
    assert outcome.ok and f"<@{ADA}>" in outcome.message and "**zfg**" in outcome.message
    assert (row["state"], row["source"], row["set_by"]) == ("matched", "staff", STAFFER)
    assert row["baseline_at"] is None and client.asked == [("name", "ZFG")]
    found = await details_of(bot.db, "pbfeed.set_by_hand")
    assert (found["actor_id"], found["target_id"], found["runner"]) == (STAFFER, ADA, "zfg")
    assert len(feed.spent) == 1


@pytest.mark.parametrize("given", ["", "   ", "nobody-by-this-name"])
async def test_a_name_that_is_not_exactly_one_account_is_refused_in_words(
    bot, guild, feed, client, given
):
    outcome = await pb_moves.set_by_hand(bot, guild, ADA, given, staffer(guild))

    assert not outcome.ok and "nothing was changed" in outcome.message
    assert await pb_store.match(bot.db, GUILD, ADA) is None and await kinds(bot.db) == []


async def test_a_runner_another_member_holds_is_refused_naming_who(bot, guild, feed, client):
    await matched(bot, ADA)
    client.by_name["zfg"] = [ZFG]

    outcome = await pb_moves.set_by_hand(bot, guild, BEA, "zfg", staffer(guild))

    assert (outcome.ok, outcome.code, outcome.status) == (False, "runner_taken", 409)
    assert f"<@{ADA}>" in outcome.message and await pb_store.match(bot.db, GUILD, BEA) is None


async def test_an_outage_while_setting_by_hand_is_a_network_answer_not_a_permission_one(
    bot, guild, feed, client
):
    client.raises = SpeedrunError(UNREACHABLE, why="TimeoutError")

    outcome = await pb_moves.set_by_hand(bot, guild, ADA, "zfg", staffer(guild))

    assert (outcome.ok, outcome.code, outcome.status) == (False, "could_not_look", 502)
    assert "could not be reached" in outcome.message and "permission" not in outcome.message


async def test_staff_cannot_set_over_an_opt_out_until_they_clear_it(bot, guild, feed, client):
    await pb_moves.opt_out(bot, guild, guild.get_member(ADA))
    client.by_name["zfg"] = [ZFG]

    refused = await pb_moves.set_by_hand(bot, guild, ADA, "zfg", staffer(guild))
    cleared = await pb_moves.clear_opt_out(bot, guild, ADA, staffer(guild))
    done = await pb_moves.set_by_hand(bot, guild, ADA, "zfg", staffer(guild))

    assert (refused.ok, refused.code) == (False, "opted_out")
    assert cleared.ok and done.ok
    found = await details_of(bot.db, "pbfeed.opt_out_cleared")
    assert (found["actor_id"], found["target_id"]) == (STAFFER, ADA)


async def test_unmatch_lets_the_automatic_match_come_back_and_block_does_not(
    bot, guild, feed, client
):
    await matched(bot)
    client.by_twitch["zfg1"] = [ZFG]

    unmatched = await pb_moves.unmatch(bot, guild, ADA, staffer(guild))
    row = await pb_store.match(bot.db, GUILD, ADA)
    assert unmatched.ok and (row["state"], row["src_user_id"], row["state_by"]) == (
        "none",
        None,
        "staff",
    )
    await feed.tick(guild, NOW + timedelta(days=8))
    assert (await pb_store.match(bot.db, GUILD, ADA))["state"] == "matched"

    blocked = await pb_moves.block(bot, guild, ADA, staffer(guild))
    client.asked.clear()
    await feed.tick(guild, NOW + timedelta(days=30))

    row = await pb_store.match(bot.db, GUILD, ADA)
    assert blocked.ok and (row["state"], row["src_user_id"]) == ("blocked", None)
    assert client.asked == []
    assert (await details_of(bot.db, "pbfeed.blocked"))["runner"] == "zfg"


async def test_unblock_puts_a_member_back_to_be_looked_up(bot, guild, feed, client):
    await link(bot.db, ADA, "zfg1")
    client.by_twitch["zfg1"] = [ZFG]
    await pb_moves.block(bot, guild, ADA, staffer(guild))

    outcome = await pb_moves.unblock(bot, guild, ADA, staffer(guild))
    await feed.tick(guild, NOW)

    assert outcome.ok and (await pb_store.match(bot.db, GUILD, ADA))["state"] == "matched"
    assert "pbfeed.unblocked" in await kinds(bot.db)


async def test_staff_can_set_a_blocked_member_by_hand(bot, guild, feed, client):
    await pb_moves.block(bot, guild, ADA, staffer(guild))
    client.by_name["zfg"] = [ZFG]

    outcome = await pb_moves.set_by_hand(bot, guild, ADA, "zfg", staffer(guild))

    assert outcome.ok and (await pb_store.match(bot.db, GUILD, ADA))["state"] == "matched"


@pytest.mark.parametrize(
    "move", [pb_moves.unmatch, pb_moves.unblock, pb_moves.clear_opt_out, pb_moves.look_now]
)
async def test_a_move_that_does_not_apply_says_so_and_writes_nothing(bot, guild, feed, move):
    outcome = await move(bot, guild, ADA, staffer(guild))

    assert (outcome.ok, outcome.code, outcome.status) == (False, "nothing_to_do", 409)
    assert await kinds(bot.db) == []


async def test_a_staff_move_from_the_site_is_one_web_row(bot, guild, feed):
    await matched(bot)

    await pb_moves.unmatch(bot, guild, ADA, staffer(guild), via=VIA_WEBSITE)

    assert await kinds(bot.db) == ["web.pbfeed.unmatched"]
    assert (await details_of(bot.db, "web.pbfeed.unmatched"))["via"] == "website"


async def test_look_now_looks_at_once_and_says_what_it_found(bot, guild, feed, client):
    await matched(bot)
    await seen(feed, client, [best("r1")])
    later = NOW + timedelta(minutes=5)
    client.bests[ZFG.id] = [best("r9", seconds=90.0, verified_at=later)]

    outcome = await pb_moves.look_now(bot, guild, ADA, staffer(guild))

    assert outcome.ok and "1 new personal best(s), 1 on record" in outcome.message
    assert len(guild.get_channel(REHEARSAL).sent) == 1
    assert (await details_of(bot.db, "pbfeed.looked"))["found"] == 1


async def test_look_now_is_refused_in_words_while_the_feed_is_off(bot, guild, feed, client):
    await matched(bot)
    await bot.store.set(GUILD, "pb_feed_mode", "off")

    outcome = await pb_moves.look_now(bot, guild, ADA, staffer(guild))

    assert (outcome.ok, outcome.code) == (False, "pb_feed_off")
    assert "pb_feed_mode" in outcome.message and client.asked == []


async def test_look_now_during_an_outage_answers_with_the_reason(bot, guild, feed, client):
    await matched(bot)
    client.bests[ZFG.id] = SpeedrunError(SERVER, status=503)

    outcome = await pb_moves.look_now(bot, guild, ADA, staffer(guild))

    assert (outcome.ok, outcome.status) == (False, 502)
    assert "fault of its own" in outcome.message
