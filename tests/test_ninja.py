import logging
from datetime import timedelta
from types import SimpleNamespace

import discord
import pytest

from black_bloc import ninja
from black_bloc import ninja_store as store
from black_bloc.logkinds import VIA_WEBSITE
from tests.ninja_fakes import (
    ELSEWHERE,
    GUILD,
    NINJA,
    NOW,
    PT,
    REAL,
    STAFF_ID,
    YATO,
    FakePost,
    Untouchable,
    kinds,
    ninja_bot,
)


@pytest.fixture
async def bot(db, monkeypatch):
    return await ninja_bot(db, monkeypatch)


def staff(bot):
    return bot.guild.get_member(STAFF_ID)


async def marked(bot, *users, posts="1", minutes="", channel=REAL, now=NOW):
    return await ninja.mark(
        bot, bot.guild, staff(bot), list(users or (PT,)), channel, posts, minutes, now=now
    )


async def test_a_mark_is_made_with_the_emote_in_use_and_logged_once_per_member(bot):
    outcome = await marked(bot, PT, YATO, posts="2")

    assert outcome.ok and outcome.value == [PT, YATO]
    assert outcome.message == f"<@{PT}>, <@{YATO}> marked in <#{REAL}> · 2 post(s)."
    rows = await store.active(bot.db, GUILD)
    assert [(row["user_id"], row["emoji"], row["posts_left"], row["until"]) for row in rows] == [
        (PT, NINJA, 2, None),
        (YATO, NINJA, 2, None),
    ]
    assert (await kinds(bot.db)).count("ninja.marked") == 2
    assert ninja.marked(bot)[(GUILD, PT)] == {REAL}


async def test_a_marked_members_post_in_the_channel_gets_the_emote_a_log_and_one_less_post(bot):
    await marked(bot, posts="3")
    post = FakePost(PT)

    assert await ninja.on_post(bot, post, now=NOW)

    assert post.reactions == [NINJA]
    [row] = await store.active(bot.db, GUILD)
    assert row["posts_left"] == 2
    cur = await bot.db.conn.execute("SELECT details FROM action_log WHERE kind = 'ninja.reacted'")
    details = (await cur.fetchone())["details"]
    assert f'"message_id": {post.id}' in details and '"posts_left": 2' in details


async def test_the_last_post_ends_the_mark(bot):
    await marked(bot, posts="1")

    assert await ninja.on_post(bot, FakePost(PT), now=NOW)
    second = FakePost(PT)
    assert not await ninja.on_post(bot, second, now=NOW)

    assert second.reactions == []
    assert await store.active(bot.db, GUILD) == []
    [ended] = await store.recent_ended(bot.db, GUILD)
    assert ended["ended_because"] == store.POSTS
    assert (await kinds(bot.db)).count("ninja.ended") == 1
    assert (GUILD, PT) not in ninja.marked(bot)


async def test_another_channel_an_unmarked_member_or_a_bot_touch_nothing(bot):
    await marked(bot)
    bot.db = Untouchable()

    for post in (FakePost(PT, ELSEWHERE), FakePost(YATO), FakePost(PT, bot=True)):
        assert not await ninja.on_post(bot, post, now=NOW)
        assert post.reactions == []
    webhook = FakePost(PT)
    webhook.webhook_id = 9
    assert not ninja.might_be_marked(bot, webhook)
    system = FakePost(PT)
    system.type = discord.MessageType.pins_add
    assert not ninja.might_be_marked(bot, system)
    assert not ninja.might_be_marked(bot, FakePost(PT, guild_id=None))


async def test_ninja_mode_off_reacts_to_nothing_and_counts_no_post(bot):
    await marked(bot, posts="2")
    await bot.store.set(GUILD, "ninja_mode", "off")
    post = FakePost(PT)

    assert not await ninja.on_post(bot, post, now=NOW)

    assert post.reactions == []
    [row] = await store.active(bot.db, GUILD)
    assert row["posts_left"] == 2


async def test_a_time_budget_ends_on_the_sweep_and_no_post_after_it_is_reacted_to(bot):
    await marked(bot, posts="", minutes="10")

    assert await ninja.on_post(bot, FakePost(PT), now=NOW + timedelta(minutes=5))
    assert await ninja.settle(bot, NOW + timedelta(minutes=9)) == 0
    assert await ninja.settle(bot, NOW + timedelta(minutes=10)) == 1
    assert await ninja.settle(bot, NOW + timedelta(minutes=11)) == 0

    [ended] = await store.recent_ended(bot.db, GUILD)
    assert ended["ended_because"] == store.TIME
    late = FakePost(PT)
    assert not await ninja.on_post(bot, late, now=NOW + timedelta(minutes=12))
    assert late.reactions == []


async def test_a_post_after_the_time_is_up_ends_the_mark_without_the_emote(bot):
    await marked(bot, posts="5", minutes="1")
    post = FakePost(PT)

    assert not await ninja.on_post(bot, post, now=NOW + timedelta(minutes=2))

    assert post.reactions == []
    [ended] = await store.recent_ended(bot.db, GUILD)
    assert ended["ended_because"] == store.TIME


async def test_the_sweep_ends_timed_out_marks_while_ninja_mode_is_off(bot):
    await marked(bot, posts="", minutes="1")
    await bot.store.set(GUILD, "ninja_mode", "off")

    assert await ninja.settle(bot, NOW + timedelta(minutes=2)) == 1


async def test_a_duplicate_active_mark_is_refused_and_the_rest_are_still_made(bot):
    await marked(bot, PT)

    outcome = await marked(bot, PT, YATO)

    assert outcome.ok and outcome.value == [YATO]
    assert outcome.message.splitlines() == [
        f"<@{YATO}> marked in <#{REAL}> · 1 post(s).",
        f"<@{PT}> already marked in <#{REAL}>, so left as they are. End that mark first.",
    ]
    refused = await marked(bot, PT)
    assert not refused.ok and refused.code == "already_marked" and refused.status == 409
    assert len(await store.active(bot.db, GUILD)) == 2


async def test_the_same_member_may_be_marked_in_another_channel(bot):
    await marked(bot, PT)
    outcome = await marked(bot, PT, channel=ELSEWHERE)
    assert outcome.ok
    assert ninja.marked(bot)[(GUILD, PT)] == {REAL, ELSEWHERE}


@pytest.mark.parametrize(
    ("users", "channel", "posts", "minutes", "code", "said"),
    [
        ([], REAL, "1", "", "no_one", "Nobody was picked"),
        ([PT], None, "1", "", "no_channel", "No channel was picked"),
        ([PT], REAL, "", "", "no_limit", "Neither posts nor minutes"),
        ([PT], REAL, "0", "0", "no_limit", "Neither posts nor minutes"),
        (
            [PT],
            REAL,
            "three",
            "",
            "bad_number",
            "**three** is not a number of posts from 1 to 1000",
        ),
        ([PT], REAL, "", "-5", "bad_number", "number of minutes from 1 to 43200"),
        ([PT], REAL, "1001", "", "bad_number", "from 1 to 1000"),
    ],
)
async def test_a_mark_that_cannot_be_made_is_refused_in_words(
    bot, users, channel, posts, minutes, code, said
):
    outcome = await ninja.mark(bot, bot.guild, staff(bot), users, channel, posts, minutes)

    assert not outcome.ok and outcome.code == code and said in outcome.message
    assert await store.active(bot.db, GUILD) == []
    assert "ninja.marked" not in await kinds(bot.db)


async def test_a_later_emote_change_leaves_a_running_mark_alone(bot):
    await marked(bot, posts="2")
    await bot.store.set(GUILD, "ninja_emoji", "<:bloc:123456789012345678>")
    post = FakePost(PT)

    await ninja.on_post(bot, post, now=NOW)

    assert post.reactions == [NINJA]


async def test_ending_a_mark_is_a_staff_move_logged_once_and_refused_twice(bot):
    await marked(bot)
    [row] = await store.active(bot.db, GUILD)

    outcome = await ninja.end(bot, bot.guild, staff(bot), row["id"])
    again = await ninja.end(bot, bot.guild, staff(bot), row["id"])

    assert outcome.ok and outcome.message == f"The mark on <@{PT}> in <#{REAL}> is ended."
    assert not again.ok and again.code == "not_active"
    [ended] = await store.recent_ended(bot.db, GUILD)
    assert ended["ended_because"] == store.STAFF
    assert (await kinds(bot.db)).count("ninja.ended") == 1
    post = FakePost(PT)
    assert not await ninja.on_post(bot, post, now=NOW)


async def test_a_reaction_discord_refuses_is_a_warning_a_failed_row_and_the_post_given_back(
    bot, caplog
):
    await marked(bot, posts="1")
    post = FakePost(PT)
    post.raises = discord.HTTPException(SimpleNamespace(status=403, reason="Forbidden"), "no")

    with caplog.at_level(logging.WARNING, logger="black_bloc.ninja"):
        assert not await ninja.on_post(bot, post, now=NOW)

    assert "not reacted to" in caplog.text
    assert "ninja.react_failed" in await kinds(bot.db)
    [row] = await store.active(bot.db, GUILD)
    assert row["posts_left"] == 1


async def test_test_mode_holds_the_emote_back_without_spending_a_post(bot):
    await marked(bot, posts="1")
    bot.guard = SimpleNamespace(allows_channel=lambda channel: False)
    post = FakePost(PT)

    assert not await ninja.on_post(bot, post, now=NOW)

    assert post.reactions == []
    [row] = await store.active(bot.db, GUILD)
    assert row["posts_left"] == 1
    assert "ninja.react_failed" not in await kinds(bot.db)


async def test_the_website_door_names_members_and_logs_under_the_web_head(bot):
    outcome = await ninja.mark(
        bot, bot.guild, staff(bot), [str(PT)], str(REAL), 1, 30, via=VIA_WEBSITE, now=NOW
    )

    assert outcome.ok
    assert outcome.message.startswith(f"@m{PT} marked in <#{REAL}> · 1 post(s) or until ")
    assert "<t:" not in outcome.message
    assert await kinds(bot.db) == ["web.ninja.marked"]


def test_what_is_left_reads_posts_time_or_both():
    store_ = SimpleNamespace(get=lambda guild_id, key: None)
    until = (NOW + timedelta(minutes=30)).isoformat()
    stamp = int((NOW + timedelta(minutes=30)).timestamp())

    assert ninja.left_words(store_, GUILD, 3, None) == "3 post(s)"
    assert ninja.left_words(store_, GUILD, None, until, now=NOW) == f"until <t:{stamp}:t>"
    assert ninja.left_words(store_, GUILD, 2, until, now=NOW) == f"2 post(s) or until <t:{stamp}:t>"
    far = (NOW + timedelta(days=2)).isoformat()
    assert ninja.left_words(store_, GUILD, None, far, now=NOW).endswith(":f>")


def test_is_due_reads_a_spent_count_a_passed_clock_and_a_broken_one():
    row = {"posts_left": 0, "until": None}
    assert ninja.is_due(row, NOW) == store.POSTS
    assert ninja.is_due({"posts_left": None, "until": NOW.isoformat()}, NOW) == store.TIME
    assert ninja.is_due({"posts_left": 1, "until": "not a time"}, NOW) == store.TIME
    later = (NOW + timedelta(minutes=1)).isoformat()
    assert ninja.is_due({"posts_left": 1, "until": later}, NOW) is None


async def test_staff_wording_is_used_and_broken_wording_falls_back(bot):
    await bot.store.set(GUILD, "ninja_none_line", "Nobody wears it.")
    assert ninja.words(bot.store, GUILD, "ninja_none_line") == "Nobody wears it."
    broken = SimpleNamespace(get=lambda guild_id, key: "{nope}")
    assert ninja.words(broken, GUILD, "ninja_left_posts", posts=2) == "2 post(s)"


async def test_the_form_starts_from_the_default_keys_with_zero_as_blank(bot):
    assert ninja.default_limits(bot.store, GUILD) == ("1", "")
    await bot.store.set(GUILD, "ninja_default_posts", 0)
    await bot.store.set(GUILD, "ninja_default_minutes", 60)
    assert ninja.default_limits(bot.store, GUILD) == ("", "60")
    assert ninja.default_channel(bot.store, GUILD) == REAL


async def test_the_map_is_rebuilt_from_the_database(bot):
    await marked(bot, PT)
    ninja.marked(bot).clear()
    await ninja.reload(bot)
    assert ninja.marked(bot) == {(GUILD, PT): {REAL}}
