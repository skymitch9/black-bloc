from __future__ import annotations

from types import SimpleNamespace

import pytest

from black_bloc import points_post as board_post
from black_bloc import post_blocks, posts, preview
from black_bloc import sticky as sticky_rules
from black_bloc.sticky_posts import Desk
from tests.test_points_moves import ADA, BEA, CY, GUILD, approved, make_bot, make_guild
from tests.test_sticky_posts import GUILD as ROOM


@pytest.fixture
def guild():
    return make_guild()


@pytest.fixture
async def bot(db, guild, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    return await make_bot(db, guild)


async def drawn(bot, guild):
    await post_blocks.load_kinds(bot, guild, [post_blocks.LEADERBOARD])
    return post_blocks.KINDS[post_blocks.LEADERBOARD].parts(bot, guild, None)


async def test_the_block_draws_the_top_n_in_the_boards_own_words(bot, guild):
    await bot.store.set(GUILD, "points_top_n", 2)
    await approved(bot, guild, ADA, time="30:00")
    await approved(bot, guild, BEA, time="1:00")
    await approved(bot, guild, BEA, time="1:00")
    await approved(bot, guild, CY, time="1:00")

    embed, view, stamp = await drawn(bot, guild)

    assert embed.title == "Leaderboard"
    assert embed.description.splitlines() == [
        "#1 Bea — 2 runs · 10 XP · 20 speedpoints",
        "#2 Ada — 1 runs · 100 XP · 10 speedpoints",
    ]
    assert view is None and stamp


async def test_the_board_order_switches_the_heading_and_the_ranking(bot, guild):
    await approved(bot, guild, ADA, time="30:00")
    await approved(bot, guild, BEA, time="1:00")
    await approved(bot, guild, BEA, time="1:00")
    await bot.store.set(GUILD, "points_board_order", "xp")

    embed, _, _ = await drawn(bot, guild)

    assert embed.title == "Leaderboard by XP"
    assert [line.split(" — ")[0] for line in embed.description.splitlines()] == ["#1 Ada", "#2 Bea"]


async def test_an_empty_board_says_so_and_staff_words_are_used(bot, guild):
    await bot.store.set(GUILD, "points_board_empty", "Be the first.")

    embed, _, _ = await drawn(bot, guild)

    assert embed.description == "Be the first."


async def test_the_stamp_moves_only_when_the_board_does(bot, guild):
    await approved(bot, guild, ADA)
    _, _, before = await drawn(bot, guild)
    _, _, again = await drawn(bot, guild)
    await approved(bot, guild, BEA)
    _, _, after = await drawn(bot, guild)

    assert before == again and after != before


async def test_nothing_is_drawn_while_points_are_off(bot, guild):
    await approved(bot, guild, ADA)
    await bot.store.set(GUILD, "points_mode", "off")

    assert await drawn(bot, guild) is None
    assert await board_post.block_rows(bot, guild) == []


def test_a_board_of_twenty_five_fits_one_card():
    store = SimpleNamespace(get=lambda guild_id, key: 25 if key == "points_top_n" else None)
    rows = [
        {"place": at, "shown": "x" * 32, "runs": 999, "xp": 99999, "speedpoints": 99999}
        for at in range(1, 26)
    ]

    found = board_post.board_look(store, GUILD, rows)

    assert len(found.text.splitlines()) == 25
    assert post_blocks.KINDS[post_blocks.LEADERBOARD].footprint == (1, 0, 0)


def test_the_leaderboard_is_a_live_kind_owned_by_the_point_system():
    found = post_blocks.KINDS[post_blocks.LEADERBOARD]

    assert post_blocks.LEADERBOARD in post_blocks.LIVE_KINDS
    assert not found.exclusive and found.load is post_blocks.leaderboard_load
    assert found.owner == ("points_mode", "points")
    assert post_blocks.owner_of(["links", "leaderboard"]) == ("points_mode", "points")
    assert post_blocks.owner_of(["links"]) is None


async def test_the_preview_draws_the_sample_board_and_nothing_while_points_are_off(bot, guild):
    full = preview.render(bot, guild, "post", None, {"blocks": "leaderboard", "always": "true"})
    await bot.store.set(GUILD, "points_mode", "off")
    off = preview.render(bot, guild, "post", None, {"blocks": "leaderboard"})

    assert full.embeds[0]["title"] == "Leaderboard"
    assert "#1 Moth" in full.embeds[0]["description"]
    assert off.embeds == ()


async def test_redraw_asks_the_door_cogs_keeper_and_never_raises(bot, guild):
    asked = []

    async def keep(found):
        asked.append(found)
        return True

    async def broken(found):
        raise RuntimeError("no")

    cog = SimpleNamespace(keep_live_now=keep)
    bot.get_cog = lambda name: cog if name == "FrontDoor" else None
    assert await board_post.redraw(bot, guild) is True
    cog.keep_live_now = broken
    assert await board_post.redraw(bot, guild) is False
    bot.get_cog = lambda name: None
    assert await board_post.redraw(bot, guild) is False
    assert asked == [guild]


# --- Pin the leaderboard here ------------------------------------------------------------------


@pytest.fixture
async def room(db, monkeypatch):
    from tests.test_sticky_posts import RUNS, Clock
    from tests.test_sticky_posts import make_bot as sticky_bot

    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    made = await sticky_bot(db)
    await made.store.set(ROOM, "points_channel_id", RUNS)
    await made.store.set(ROOM, "points_mode", "on")
    clock = Clock()
    made.sticky_desk = Desk(made, now=clock.now, sleep=clock.sleep)
    return made


async def test_pin_makes_the_post_and_the_sticky_once_and_again_is_safe(room):
    from tests.test_sticky_posts import RUNS

    first = await board_post.pin_board(room, room.guild, 1)
    again = await board_post.pin_board(room, room.guild, 1)

    assert first.ok and first.code == "pinned", first.message
    assert again.ok and again.code == "already"
    post = await posts.get_post(room.db, ROOM, "leaderboard")
    assert (post["title"], post["style"], post["pin"]) == ("Leaderboard", "embed", 0)
    assert await post_blocks.kinds_on(room.db, int(post["id"])) == ["leaderboard"]
    assert len(room.guild.get_channel(RUNS).messages) == 1
    found = await board_post.board_state(room, room.guild)
    assert int(found["sticky"]["channel_id"]) == RUNS and found["other"] is None
    assert found["channel"] == "#runs"


async def test_a_channel_with_another_sticky_is_refused_until_staff_replace_it(room):
    from tests.test_sticky_posts import RUNS, WORDS

    await room.sticky_desk.save(room.guild, RUNS, WORDS, 1)

    refused = await board_post.pin_board(room, room.guild, 1)
    replaced = await board_post.pin_board(room, room.guild, 1, replace=True)

    assert not refused.ok and refused.code == "channel_has_sticky"
    assert "How to submit a run" in refused.message
    assert replaced.ok, replaced.message
    messages = room.guild.get_channel(RUNS).messages
    assert len(messages) == 1 and messages[0].content is None
    row = await sticky_rules.get_row(room.db, ROOM, RUNS)
    assert row["post_id"] and row["text"] == ""


async def test_a_new_channel_moves_the_leaderboard_there(room):
    from tests.test_sticky_posts import OTHER_HOME, RUNS

    await board_post.pin_board(room, room.guild, 1)
    await room.store.set(ROOM, "points_channel_id", OTHER_HOME)

    moved = await board_post.pin_board(room, room.guild, 1)

    assert moved.ok, moved.message
    assert room.guild.get_channel(RUNS).messages == []
    assert len(room.guild.get_channel(OTHER_HOME).messages) == 1
    assert await sticky_rules.get_row(room.db, ROOM, RUNS) is None


async def test_a_channel_black_bloc_cannot_see_is_refused_in_words(room):
    await room.store.clear(ROOM, "points_channel_id")

    found = await board_post.pin_board(room, room.guild, 1)

    assert not found.ok and found.code == "channel_gone" and "points_channel_id" in found.message
    assert await posts.get_post(room.db, ROOM, "leaderboard") is None
