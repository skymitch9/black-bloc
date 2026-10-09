# ruff: noqa: F401, F811
import discord

from black_bloc import points_announce as announce_
from black_bloc.panels import Outcome
from black_bloc.points_moves import Result
from tests.cogs.moderation.test_modmail import GUILD, FakeGuard, refused
from tests.test_points_tickets import REHEARSAL, SPEED, bot, kinds

LINES = ("Ada is in the top 10 at #1 with 10 speedpoints.", "Bea moved down to #2 (was #1).")


def moved(lines=LINES):
    return Outcome(True, "done", value=Result(1, announce=tuple(lines)))


async def test_shadow_posts_one_rehearsal_to_the_home_and_never_pings(bot):
    await bot.store.set(GUILD, "points_ping_role_id", 777)

    said = await announce_.announce(bot, bot.guild, moved())

    assert said == announce_.REHEARSED
    [post] = bot.guild.channels[REHEARSAL].messages
    assert post.content == f"Rehearsal — this is where it would go: <#{SPEED}>"
    assert post.kwargs["embed"].title == "Leaderboard update"
    assert post.kwargs["embed"].description == "\n".join(LINES)
    assert post.kwargs["allowed_mentions"].to_dict() == discord.AllowedMentions.none().to_dict()
    assert bot.guild.channels[SPEED].messages == []


async def test_the_points_own_shadow_home_wins_over_the_global_one(bot):
    await bot.store.set(GUILD, "points_shadow_channel_id", SPEED)

    await announce_.announce(bot, bot.guild, moved())

    assert len(bot.guild.channels[SPEED].messages) == 1
    assert bot.guild.channels[REHEARSAL].messages == []


async def test_on_posts_once_in_the_points_channel_pinging_only_the_role(bot):
    await bot.store.set(GUILD, "points_mode", "on")
    await bot.store.set(GUILD, "points_ping_role_id", 777)

    said = await announce_.announce(bot, bot.guild, moved())

    assert said == announce_.POSTED
    [post] = bot.guild.channels[SPEED].messages
    assert post.content == "<@&777>"
    allowed = post.kwargs["allowed_mentions"]
    assert [role.id for role in allowed.roles] == [777]
    assert allowed.everyone is False and allowed.users is False


async def test_a_blank_ping_role_posts_with_no_mention_at_all(bot):
    await bot.store.set(GUILD, "points_mode", "on")

    await announce_.announce(bot, bot.guild, moved())

    [post] = bot.guild.channels[SPEED].messages
    assert post.content == ""
    assert post.kwargs["allowed_mentions"].to_dict() == discord.AllowedMentions.none().to_dict()


async def test_a_post_that_fails_while_on_is_its_own_loud_row(bot, db):
    await bot.store.set(GUILD, "points_mode", "on")
    bot.guild.channels[SPEED].send_raises = refused()

    said = await announce_.announce(bot, bot.guild, moved())

    assert said == announce_.NOT_POSTED
    assert await kinds(db, "points.%") == ["points.announce_failed"]


async def test_the_test_mode_guard_refuses_a_real_post_in_words_of_its_own(bot, db):
    await bot.store.set(GUILD, "points_mode", "on")
    bot.guard = FakeGuard()

    await announce_.announce(bot, bot.guild, moved())

    assert bot.guild.channels[SPEED].messages == []
    assert await kinds(db, "points.%") == ["points.announce_failed"]


async def test_nothing_moved_and_off_post_nothing(bot):
    assert await announce_.announce(bot, bot.guild, moved(())) == announce_.NOT_POSTED
    await bot.store.set(GUILD, "points_mode", "off")
    assert await announce_.announce(bot, bot.guild, moved()) == announce_.NOT_POSTED
    assert bot.guild.channels[REHEARSAL].messages == []
