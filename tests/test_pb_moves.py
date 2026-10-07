# ruff: noqa: F401, F811
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import discord
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
    PBS,
    PING,
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
    await feed.tick(guild, datetime.now(UTC) + timedelta(days=8))
    assert (await pb_store.match(bot.db, GUILD, ADA))["state"] == "matched"

    blocked = await pb_moves.block(bot, guild, ADA, staffer(guild))
    client.asked.clear()
    await feed.tick(guild, datetime.now(UTC) + timedelta(days=30))

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

    assert await kinds(bot.db) == ["web.pbfeed.unmatched", "pbfeed.would_dm"]
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


async def asked_after(feed, guild, client, *days):
    client.asked.clear()
    for day in days:
        await feed.tick(guild, NOW + timedelta(days=day))
        await feed.tick(guild, NOW + timedelta(days=day, minutes=1))
    return list(client.asked)


async def test_an_opt_out_survives_a_block_and_an_unblock(bot, guild, feed, client):
    await matched(bot)
    client.by_twitch["zfg1"] = [ZFG]
    client.bests[ZFG.id] = [best("r1")]
    await pb_moves.opt_out(bot, guild, guild.get_member(ADA))

    blocked = await pb_moves.block(bot, guild, ADA, staffer(guild))
    unblocked = await pb_moves.unblock(bot, guild, ADA, staffer(guild))
    asked = await asked_after(feed, guild, client, 1, 8, 30)

    row = await pb_store.match(bot.db, GUILD, ADA)
    assert blocked.ok and unblocked.ok
    assert (row["state"], row["state_by"]) == ("opted_out", "member") and row["opted_out_at"]
    assert asked == [] and sent(guild) == {}
    assert "still stands" in unblocked.message
    assert (await details_of(bot.db, "pbfeed.unblocked"))["still_opted_out"] is True


async def test_staff_cannot_set_an_account_over_an_opt_out_hidden_under_a_block(
    bot, guild, feed, client
):
    client.by_name["zfg"] = [ZFG]
    await pb_moves.opt_out(bot, guild, guild.get_member(ADA))
    await pb_moves.block(bot, guild, ADA, staffer(guild))

    refused = await pb_moves.set_by_hand(bot, guild, ADA, "zfg", staffer(guild))

    assert (refused.ok, refused.code) == (False, "opted_out") and client.asked == []
    assert (await pb_store.match(bot.db, GUILD, ADA))["state"] == "blocked"


@pytest.mark.parametrize("ender", ["member", "staff"])
async def test_only_the_member_or_the_explicit_staff_move_ends_an_opt_out(
    bot, guild, feed, client, ender
):
    await link(bot.db, ADA, "zfg1")
    client.by_twitch["zfg1"] = [ZFG]
    await pb_moves.opt_out(bot, guild, guild.get_member(ADA))
    await pb_moves.block(bot, guild, ADA, staffer(guild))
    await pb_moves.unblock(bot, guild, ADA, staffer(guild))

    if ender == "member":
        done = await pb_moves.opt_in(bot, guild, guild.get_member(ADA))
    else:
        done = await pb_moves.clear_opt_out(bot, guild, ADA, staffer(guild))
    row = await pb_store.match(bot.db, GUILD, ADA)

    assert done.ok and (row["state"], row["opted_out_at"]) == ("none", None)
    assert (await asked_after(feed, guild, client, 1))[0] == ("twitch", "zfg1")


async def staff_move(bot, guild, client, move, reason="wrong account"):
    staff = staffer(guild)
    if move == "set_by_hand":
        client.by_name["zfg"] = [ZFG]
        return await pb_moves.set_by_hand(bot, guild, ADA, "zfg", staff, reason=reason)
    if move == "opt_out_cleared":
        await pb_moves.opt_out(bot, guild, guild.get_member(ADA))
        return await pb_moves.clear_opt_out(bot, guild, ADA, staff, reason=reason)
    act = {"unmatched": pb_moves.unmatch, "blocked": pb_moves.block}[move]
    return await act(bot, guild, ADA, staff, reason=reason)


DM_MOVES = [
    ("set_by_hand", "matched you to **zfg**"),
    ("unmatched", "removed your match to **zfg**"),
    ("blocked", "turned the personal best feed off for you"),
    ("opt_out_cleared", "put you back in"),
]


@pytest.mark.parametrize(("move", "words"), DM_MOVES)
async def test_a_staff_move_that_affects_a_member_dms_them_the_reason_once(
    bot, guild, feed, client, move, words
):
    await bot.store.set(GUILD, "pb_feed_mode", "on")
    if move != "set_by_hand":
        await matched(bot)

    outcome = await staff_move(bot, guild, client, move)

    dms = guild.get_member(ADA).dms
    assert outcome.ok and len(dms) == 1
    text = dms[0]["content"]
    assert words in text and "Their reason: wrong account" in text and "**Black Bloc**" in text
    assert dms[0]["allowed_mentions"].to_dict() == discord.AllowedMentions.none().to_dict()
    assert "is posted" not in text
    if move != "blocked":
        assert "/pb" in text
    logged = await kinds(bot.db)
    assert "pbfeed.dm_failed" not in logged and "pbfeed.would_dm" not in logged
    assert (await details_of(bot.db, f"pbfeed.{move}"))["reason"] == "wrong account"


@pytest.mark.parametrize(("move", "words"), DM_MOVES)
async def test_closed_dms_are_logged_in_words_and_never_block_the_move(
    bot, guild, feed, client, move, words
):
    await bot.store.set(GUILD, "pb_feed_mode", "on")
    if move != "set_by_hand":
        await matched(bot)
    guild.get_member(ADA).dms_closed = True

    outcome = await staff_move(bot, guild, client, move, reason="")

    found = await details_of(bot.db, "pbfeed.dm_failed")
    assert outcome.ok and guild.get_member(ADA).dms == []
    assert found["target_id"] == ADA and found["move"] == move
    assert "Discord would not deliver the DM" in found["reason"]
    assert "The move itself was made" in found["reason"]
    assert words in found["text"] and "Their reason: none was given." in found["text"]


@pytest.mark.parametrize("mode", ["shadow", "off"])
async def test_while_the_feed_is_not_on_the_dm_is_logged_and_never_sent(
    bot, guild, feed, client, mode
):
    await matched(bot)
    await bot.store.set(GUILD, "pb_feed_mode", mode)

    outcome = await pb_moves.block(bot, guild, ADA, staffer(guild), reason="spam runs")

    found = await details_of(bot.db, "pbfeed.would_dm")
    assert outcome.ok and guild.get_member(ADA).dms == []
    assert found["target_id"] == ADA and "Their reason: spam runs" in found["text"]
    assert f"pb_feed_mode is {mode}" in found["reason"]


async def test_a_dm_never_carries_markdown_or_a_ping_from_the_reason(bot, guild, feed, client):
    await bot.store.set(GUILD, "pb_feed_mode", "on")
    await matched(bot)

    loud = "**loud**\n\n@everyone " + "x" * 900
    await pb_moves.block(bot, guild, ADA, staffer(guild), reason=loud)

    text = guild.get_member(ADA).dms[0]["content"]
    assert "**loud**" not in text and "\\*\\*loud" in text and len(text) < 1000


async def test_look_now_has_a_cooldown_for_each_member(bot, guild, feed, client):
    await matched(bot)
    await matched(bot, BEA, OTHER, login="bea_tv")
    client.bests[ZFG.id] = [best("r1")]
    client.bests[OTHER.id] = [best("b1")]
    staff = staffer(guild)

    first = await pb_moves.look_now(bot, guild, ADA, staff, now=NOW)
    presses = [
        await pb_moves.look_now(bot, guild, ADA, staff, now=NOW + timedelta(seconds=at))
        for at in range(1, 200)
    ]
    other = await pb_moves.look_now(bot, guild, BEA, staff, now=NOW + timedelta(minutes=1))
    later = await pb_moves.look_now(bot, guild, ADA, staff, now=NOW + timedelta(minutes=5))

    assert first.ok and other.ok and later.ok and client.requests == 3
    assert {(one.ok, one.code, one.status) for one in presses} == {(False, "not_yet", 429)}
    assert "looked at 0 minute(s) ago" in presses[0].message
    assert "Try again in about 5 minute(s)" in presses[0].message
    assert "Try again in about 2 minute(s)" in presses[-1].message


async def test_look_now_respects_an_outage_backoff_and_starts_one(bot, guild, feed, client):
    await matched(bot)
    client.bests[ZFG.id] = SpeedrunError(SERVER, status=503)
    staff = staffer(guild)

    first = await pb_moves.look_now(bot, guild, ADA, staff, now=NOW)
    presses = [
        await pb_moves.look_now(bot, guild, ADA, staff, now=NOW + timedelta(seconds=at))
        for at in range(1, 100)
    ]

    assert (first.ok, first.status) == (False, 502) and client.requests == 1
    assert {(one.code, one.status) for one in presses} == {("not_yet", 429)}
    assert "the network or their site, not a setting here" in presses[0].message
    assert "Try again in about 5 minute(s)" in presses[0].message
    assert await kinds(bot.db) == ["pbfeed.look_failed"]
    assert await feed.tick(guild, NOW + timedelta(minutes=1)) == 0


async def test_look_now_and_set_by_hand_stop_at_the_request_cap(bot, guild, feed, client):
    await bot.store.set(GUILD, "pb_feed_cycle_requests", 2)
    client.by_name["zfg"] = [ZFG]
    client.bests[ZFG.id] = [best("r1")]
    staff = staffer(guild)

    done = await pb_moves.set_by_hand(bot, guild, ADA, "zfg", staff, now=NOW)
    looked = await pb_moves.look_now(bot, guild, ADA, staff, now=NOW + timedelta(minutes=1))
    soon = NOW + timedelta(minutes=2)
    refused = await pb_moves.set_by_hand(bot, guild, BEA, "zfg", staff, now=soon)
    again = await pb_moves.look_now(bot, guild, ADA, staff, now=NOW + timedelta(minutes=10))

    assert done.ok and looked.ok and client.requests == 2
    assert (refused.code, again.code) == ("not_yet", "not_yet")
    assert "2 requests in the last 60 minutes" in again.message
    assert "pb_feed_cycle_requests" in again.message and "about 50 minute(s)" in again.message


async def test_set_by_hand_asks_speedrun_nothing_while_the_feed_is_off(bot, guild, feed, client):
    await bot.store.set(GUILD, "pb_feed_mode", "off")
    client.by_name["zfg"] = [ZFG]

    outcome = await pb_moves.set_by_hand(bot, guild, ADA, "zfg", staffer(guild))

    assert (outcome.ok, outcome.code, outcome.status) == (False, "pb_feed_off", 409)
    assert "pb_feed_mode" in outcome.message and client.asked == []
    assert await pb_store.match(bot.db, GUILD, ADA) is None


async def a_post(bot, guild, feed, client):
    """One personal best that went out as a rehearsal, the way the feed posts one."""
    await bot.store.set(GUILD, "pb_feed_channel_id", PBS)
    await matched(bot)
    await seen(feed, client, [best("r1", seconds=100.0)])
    later = NOW + timedelta(hours=2)
    client.bests[ZFG.id] = [best("r9", seconds=95.5, place=2, verified_at=later)]
    await feed.look(guild, ADA, now=later)
    return (await pb_store.posts(bot.db, GUILD))[0]


async def test_post_again_rehearses_a_stored_post_exactly_as_a_fresh_one_in_shadow(
    bot, guild, feed, client
):
    source = await a_post(bot, guild, feed, client)
    fresh = guild.get_channel(REHEARSAL).sent[0]
    asked = list(client.asked)
    baseline = await pb_store.baseline(bot.db, GUILD, ADA)
    before = dict(await pb_store.match(bot.db, GUILD, ADA))

    outcome = await pb_moves.post_again(bot, guild, source["id"], staffer(guild))

    assert outcome.ok and f"<#{REHEARSAL}>" in outcome.message and "<@900>" in outcome.message
    copies = guild.get_channel(REHEARSAL).sent
    assert len(copies) == 2 and guild.get_channel(PBS).sent == []
    again = copies[1]
    assert again["content"] == fresh["content"]
    assert again["embed"].to_dict() == fresh["embed"].to_dict()
    assert again["allowed_mentions"].to_dict() == fresh["allowed_mentions"].to_dict()
    assert [one.url for one in again["view"].children] == [
        one.url for one in fresh["view"].children
    ]
    rows = await pb_store.posts(bot.db, GUILD)
    assert [(row["outcome"], row["again_of"]) for row in rows] == [
        (pb_store.REHEARSED, source["id"]),
        (pb_store.REHEARSED, None),
    ]
    assert dict(rows[1]) == dict(source)
    assert rows[0]["message_id"] == 1002 and rows[0]["channel_id"] == REHEARSAL
    assert outcome.value["id"] == rows[0]["id"]
    found = await details_of(bot.db, "pbfeed.would_post_again")
    assert (found["actor_id"], found["target_id"], found["via"]) == (STAFFER, ADA, "discord")
    assert (found["again_of"], found["run_id"], found["rehearsed"]) == (source["id"], "r9", True)
    assert (await kinds(bot.db)).count("pbfeed.would_post_again") == 1
    assert client.asked == asked
    assert await pb_store.baseline(bot.db, GUILD, ADA) == baseline
    assert dict(await pb_store.match(bot.db, GUILD, ADA)) == before


async def test_post_again_goes_to_the_feed_channel_with_the_ping_while_on(
    bot, guild, feed, client
):
    source = await a_post(bot, guild, feed, client)
    await bot.store.set(GUILD, "pb_feed_mode", "on")
    await bot.store.set(GUILD, "pb_feed_ping_role_id", PING)

    outcome = await pb_moves.post_again(
        bot, guild, source["id"], staffer(guild), via=VIA_WEBSITE
    )

    post = guild.get_channel(PBS).sent[0]
    assert outcome.ok and f"<#{PBS}>" in outcome.message
    assert post["content"] == f"<@&{PING}>"
    assert [role.id for role in post["allowed_mentions"].roles] == [PING]
    assert post["allowed_mentions"].users is False
    assert post["embed"].description == (
        "**Ada** ran **Ocarina of Time** — Any% in **1:35.500** — #2 on the leaderboard."
    )
    assert (await pb_store.posts(bot.db, GUILD))[0]["outcome"] == pb_store.POSTED
    found = await details_of(bot.db, "web.pbfeed.posted_again")
    wanted = (STAFFER, "website", source["id"])
    assert (found["actor_id"], found["via"], found["again_of"]) == wanted


async def test_post_again_uses_the_wording_and_the_name_of_now(bot, guild, feed, client):
    source = await a_post(bot, guild, feed, client)
    await bot.store.set(GUILD, "pb_feed_post_text", "{name} did {game} in {time}")
    await bot.store.set(GUILD, "pb_feed_link_label", "See it")
    guild.get_member(ADA).display_name = "Ada Lovelace"

    await pb_moves.post_again(bot, guild, source["id"], staffer(guild))

    again = guild.get_channel(REHEARSAL).sent[-1]
    assert again["embed"].description == "Ada Lovelace did Ocarina of Time in 1:35.500"
    assert again["embed"].author.name == "Ada Lovelace"
    assert [one.label for one in again["view"].children] == ["See it"]


async def test_post_again_is_refused_in_words_while_the_feed_is_off(bot, guild, feed, client):
    source = await a_post(bot, guild, feed, client)
    await bot.store.set(GUILD, "pb_feed_mode", "off")
    logged = await kinds(bot.db)

    outcome = await pb_moves.post_again(bot, guild, source["id"], staffer(guild))

    assert (outcome.ok, outcome.code, outcome.status) == (False, "pb_feed_off", 409)
    assert "shadow or on" in outcome.message and "nothing was posted" in outcome.message
    assert len(guild.get_channel(REHEARSAL).sent) == 1
    assert len(await pb_store.posts(bot.db, GUILD)) == 1 and await kinds(bot.db) == logged


async def test_post_again_on_a_post_that_does_not_exist_is_a_404_in_words(bot, guild, feed):
    outcome = await pb_moves.post_again(bot, guild, 4242, staffer(guild))

    assert (outcome.ok, outcome.code, outcome.status) == (False, "no_such_post", 404)
    assert "4242" in outcome.message and "nothing was posted" in outcome.message
    assert await kinds(bot.db) == []


@pytest.mark.parametrize(
    ("move", "words"),
    [("unmatch", "not matched"), ("opt_out", "opted out"), ("block", "blocked")],
)
async def test_post_again_still_posts_for_a_member_out_of_the_feed_and_says_so(
    bot, guild, feed, client, move, words
):
    source = await a_post(bot, guild, feed, client)
    if move == "opt_out":
        await pb_moves.opt_out(bot, guild, guild.get_member(ADA))
    else:
        await getattr(pb_moves, move)(bot, guild, ADA, staffer(guild))
    before = dict(await pb_store.match(bot.db, GUILD, ADA))

    outcome = await pb_moves.post_again(bot, guild, source["id"], staffer(guild))

    assert outcome.ok and words in outcome.message
    assert len(guild.get_channel(REHEARSAL).sent) == 2
    assert dict(await pb_store.match(bot.db, GUILD, ADA)) == before


async def test_post_again_with_nowhere_to_go_is_a_new_failed_row_and_a_refusal_in_words(
    bot, guild, feed, client
):
    source = await a_post(bot, guild, feed, client)
    await bot.store.set(GUILD, "pb_feed_mode", "on")
    await bot.store.clear(GUILD, "pb_feed_channel_id")

    outcome = await pb_moves.post_again(bot, guild, source["id"], staffer(guild))

    assert (outcome.ok, outcome.status) == (False, 409)
    assert "pb_feed_channel_id is blank" in outcome.message
    rows = await pb_store.posts(bot.db, GUILD)
    assert [(row["outcome"], row["again_of"]) for row in rows] == [
        (pb_store.FAILED, source["id"]),
        (pb_store.REHEARSED, None),
    ]
    found = await details_of(bot.db, "pbfeed.post_failed")
    assert (found["again_of"], found["actor_id"]) == (source["id"], STAFFER)


async def test_post_again_that_discord_refuses_is_a_502_in_words(bot, guild, feed, client):
    source = await a_post(bot, guild, feed, client)
    guild.get_channel(REHEARSAL).send_raises = discord.HTTPException(
        SimpleNamespace(status=500, reason="boom"), "Internal Server Error"
    )

    outcome = await pb_moves.post_again(bot, guild, source["id"], staffer(guild))

    assert (outcome.ok, outcome.status) == (False, 502) and "Nothing was posted" in outcome.message
    assert (await pb_store.posts(bot.db, GUILD))[0]["outcome"] == pb_store.FAILED
