import json

import discord
import pytest

from black_bloc import sticky as rules
from black_bloc import sticky_rehearse as testing
from black_bloc.logkinds import VIA_WEBSITE
from black_bloc.sticky_posts import Desk
from tests.test_sticky_posts import (
    GUILD,
    HOME,
    OTHER_HOME,
    RUNS,
    STAFFER,
    WORDS,
    Clock,
    FakeGuard,
    a_post,
    channel,
    forbidden,
    make_bot,
    points_on,
    post_row,
    row_of,
)


class WordedGuard(FakeGuard):
    SAID = "Test mode keeps Black Bloc in the test channel."

    def refusal_message(self):
        return self.SAID


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    return await make_bot(db)


@pytest.fixture
def desk(bot):
    clock = Clock()
    found = Desk(bot, now=clock.now, sleep=clock.sleep)
    bot.sticky_desk = found
    return found


async def rehearsed(db):
    cur = await db.conn.execute(
        "SELECT kind, actor_id, details FROM action_log WHERE kind LIKE '%sticky.rehearsed' "
        "ORDER BY id"
    )
    rows = await cur.fetchall()
    return [(row["kind"], row["actor_id"], json.loads(row["details"])) for row in rows]


async def a_live_words_sticky(bot, desk):
    await bot.store.set(GUILD, "sticky_mode", "on")
    await desk.save(bot.guild, RUNS, WORDS, STAFFER)
    return dict(await row_of(bot))


async def test_a_live_words_sticky_gets_one_plain_copy_and_its_row_never_moves(bot, desk):
    before = await a_live_words_sticky(bot, desk)
    live = list(channel(bot).messages)

    outcome = await testing.rehearse(bot, bot.guild, RUNS, STAFFER, via=VIA_WEBSITE)

    assert outcome.ok and outcome.message == testing.TESTED.format(channel_id=RUNS, home=HOME)
    [copy] = channel(bot, HOME).messages
    assert copy.content == WORDS
    assert copy.kwargs["allowed_mentions"].everyone is False
    assert channel(bot, HOME).pinned == []
    assert channel(bot).messages == live
    assert dict(await row_of(bot)) == before
    assert rules.state_of(await row_of(bot), "on") == rules.LIVE
    [(kind, actor, details)] = await rehearsed(bot.db)
    assert (kind, actor) == ("web.sticky.rehearsed", STAFFER)
    assert details["channel_id"] == RUNS and details["shadow_home"] == HOME
    assert details["message_id"] == copy.id
    assert details["url"] == f"https://discord.com/channels/{GUILD}/{HOME}/{copy.id}"


async def test_a_paused_sticky_can_be_tested_and_stays_paused(bot, desk):
    await a_live_words_sticky(bot, desk)
    await desk.pause(bot.guild, RUNS, STAFFER)
    before = dict(await row_of(bot))

    outcome = await testing.rehearse(bot, bot.guild, RUNS, STAFFER)

    assert outcome.ok
    assert channel(bot).messages == [] and len(channel(bot, HOME).messages) == 1
    assert dict(await row_of(bot)) == before and before["paused"]


async def test_a_post_sticky_sends_the_post_and_never_touches_the_posts_copy_ids(bot, desk):
    await points_on(bot)
    post_id = await a_post(bot)
    await desk.save(bot.guild, RUNS, None, STAFFER, post=post_id)
    post_before = dict(await post_row(bot, post_id))
    sticky_before = dict(await row_of(bot))

    outcome = await testing.rehearse(bot, bot.guild, RUNS, STAFFER)

    assert outcome.ok, outcome.message
    [copy] = channel(bot, HOME).messages
    assert copy.content is None
    assert [embed.title for embed in copy.kwargs["embeds"]] == ["Leaderboard"]
    assert dict(await post_row(bot, post_id)) == post_before
    assert dict(await row_of(bot)) == sticky_before
    [(_, _, details)] = await rehearsed(bot.db)
    assert details["post_id"] == post_id


async def test_a_sticky_already_rehearsing_answers_so_and_sends_nothing(bot, desk):
    await desk.save(bot.guild, RUNS, WORDS, STAFFER)
    assert rules.state_of(await row_of(bot), "shadow") == rules.REHEARSING

    outcome = await testing.rehearse(bot, bot.guild, RUNS, STAFFER)

    assert outcome.ok and outcome.code == "already_rehearsing"
    assert outcome.message == testing.ALREADY.format(home=HOME)
    assert len(channel(bot, HOME).messages) == 1
    assert await rehearsed(bot.db) == []


async def test_refusals_are_worded_and_send_nothing(bot, desk):
    assert (await testing.rehearse(bot, bot.guild, RUNS, STAFFER)).code == "no_sticky"
    await a_live_words_sticky(bot, desk)

    await bot.store.set(GUILD, "sticky_mode", "off")
    off = await testing.rehearse(bot, bot.guild, RUNS, STAFFER)
    assert (off.code, off.message) == ("sticky_off", testing.SWITCHED_OFF.format(key="sticky_mode"))

    await bot.store.set(GUILD, "sticky_mode", "on")
    await bot.store.set(GUILD, "sticky_shadow_channel_id", RUNS)
    own = await testing.rehearse(bot, bot.guild, RUNS, STAFFER)
    assert own.code == "own_home" and f"<#{RUNS}>" in own.message

    await bot.store.set(GUILD, "sticky_shadow_channel_id", OTHER_HOME)
    channel(bot, OTHER_HOME).send_raises = forbidden()
    failed = await testing.rehearse(bot, bot.guild, RUNS, STAFFER)
    assert failed.code == "post_failed" and "403" in failed.message

    bot.guard = WordedGuard(allowed=HOME)
    guarded = await testing.rehearse(bot, bot.guild, RUNS, STAFFER)
    assert (guarded.code, guarded.message) == ("test_mode", WordedGuard.SAID)
    assert channel(bot, HOME).messages == []
    assert await rehearsed(bot.db) == []


async def test_the_button_shows_only_when_a_press_would_send(bot, desk):
    row = await row_of(bot) or None
    assert row is None
    await a_live_words_sticky(bot, desk)
    row = await row_of(bot)

    assert testing.can_test(bot, bot.guild, row, "on", "sticky")
    assert not testing.can_test(bot, bot.guild, row, "off", "sticky")
    assert not testing.can_test(bot, bot.guild, row, "shadow", "sticky")
    await bot.store.set(GUILD, "sticky_shadow_channel_id", RUNS)
    assert not testing.can_test(bot, bot.guild, row, "on", "sticky")
    moves = [move.action for move in rules.card_buttons(row, testable=True)]
    assert moves[-1] == rules.TEST and rules.TEST_MOVE.row == 1
    assert rules.TEST not in [move.action for move in rules.card_buttons(row)]


async def test_the_panel_card_offers_post_to_test_and_answers_in_words(bot, desk):
    from black_bloc import sticky_panel as panel

    await a_live_words_sticky(bot, desk)
    embed, view = await panel.build_card(bot, bot.guild, await row_of(bot))
    labels = [item.label for item in view.children if isinstance(item, discord.ui.Button)]

    assert labels[-1] == "Post to test"
    assert testing.NO_HOME.format(feature="sticky") not in embed.description
