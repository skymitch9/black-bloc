import json

import pytest

from black_bloc import runs_genre_format as migration
from black_bloc.settings_store import RUNS_GENRE_UPPER
from tests.baf_runs_fakes import GUILD, make_bot

LIVE_GENRES = {
    "donkey kong country 2": "2D platformer",
    "sekiro": "Action-adventure",
    "street fighter": "Fighting",
    "slay the spire": "Roguelike",
    "hades": "Action roguelike",
    "gears of war": "Third-person shooter",
    "mario kart 8": "Kart racing",
    "super mario 64": "3D platformer",
}


@pytest.fixture
async def bot(db, monkeypatch):
    return await make_bot(db, monkeypatch)


async def seed(db, genres=LIVE_GENRES, guild_id=GUILD):
    for key, genre in genres.items():
        await db.conn.execute(
            "INSERT INTO baf_series(guild_id, game_key, series, genre, by, at) "
            "VALUES (?, ?, '', ?, NULL, 'x')",
            (guild_id, key, genre),
        )
    await db.conn.commit()


async def genres_of(db):
    cur = await db.conn.execute("SELECT game_key, genre FROM baf_series ORDER BY game_key")
    return {row["game_key"]: row["genre"] for row in await cur.fetchall()}


async def migrated_rows(db):
    cur = await db.conn.execute(
        "SELECT guild_id, details FROM action_log WHERE kind = 'runs.migrated' ORDER BY id"
    )
    return [(row["guild_id"], json.loads(row["details"])) for row in await cur.fetchall()]


async def test_the_dry_run_on_the_eight_live_genres_names_exactly_two_and_writes_nothing(bot):
    await seed(bot.db)

    found = await migration.dry_run(bot.db, bot.store)

    assert [(one["game_key"], one["before"], one["after"]) for one in found] == [
        ("gears of war", "Third-person shooter", "Third person shooter"),
        ("sekiro", "Action-adventure", "Action adventure"),
    ]
    assert await genres_of(bot.db) == LIVE_GENRES
    assert await migrated_rows(bot.db) == []


async def test_apply_rewrites_once_logs_one_row_and_a_second_boot_writes_nothing(bot, caplog):
    await seed(bot.db)
    caplog.set_level("INFO")

    done = await migration.apply(bot)

    assert len(done) == 2
    after = await genres_of(bot.db)
    assert after == LIVE_GENRES | {
        "sekiro": "Action adventure",
        "gears of war": "Third person shooter",
    }
    assert "runs genre format: 2 game(s) rewritten" in caplog.text
    assert await migrated_rows(bot.db) == [
        (
            GUILD,
            {
                "build": "runs-genre-format",
                "rewritten": 2,
                "genres": {
                    "gears of war": ["Third-person shooter", "Third person shooter"],
                    "sekiro": ["Action-adventure", "Action adventure"],
                },
                "via": "discord",
            },
        )
    ]

    assert await migration.apply(bot) == []
    assert await genres_of(bot.db) == after
    assert len(await migrated_rows(bot.db)) == 1


async def test_a_list_is_formatted_whole_and_never_cut_to_the_cap(bot):
    await seed(bot.db, {"celeste": "platformer,puzzle , rogue-lite, Roguelike"})

    await migration.apply(bot)

    assert await genres_of(bot.db) == {"celeste": "Platformer, Puzzle, Rogue lite"}


async def test_each_guild_is_formatted_by_its_own_capitals_words(bot):
    await bot.store.set(GUILD, RUNS_GENRE_UPPER, "", by=1)
    await seed(bot.db, {"doom": "fps"})

    found = await migration.dry_run(bot.db, bot.store)

    assert [(one["before"], one["after"]) for one in found] == [("fps", "Fps")]
