from __future__ import annotations

from types import SimpleNamespace

import pytest

from black_bloc import points_post as board_post
from black_bloc import post_blocks, preview
from tests.test_points_moves import ADA, BEA, CY, GUILD, approved, make_bot, make_guild


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
