from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from black_bloc import points_moves as moves
from black_bloc import points_store as store_
from black_bloc import points_view as view
from black_bloc.settings_store import POINTS_WORDS
from tests.test_points_moves import (
    ADA,
    BEA,
    CY,
    GUILD,
    STAFF,
    approved,
    make_bot,
    make_guild,
    who,
)


@pytest.fixture
def guild():
    return make_guild()


@pytest.fixture
async def bot(db, guild, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    return await make_bot(db, guild)


async def test_the_index_ranks_by_speedpoints_and_switches_to_xp(bot, guild):
    await approved(bot, guild, ADA, time="30:00")
    await approved(bot, guild, BEA, time="1:00")
    await approved(bot, guild, BEA, time="1:00")

    found = await view.index(bot, guild, ADA, verifier=False, staff=False)

    assert (found["mode"], found["by"], found["top_n"], found["members"]) == (
        "shadow",
        "points",
        10,
        2,
    )
    assert [
        (row["name"], row["place"], row["speedpoints"], row["xp"]) for row in found["board"]
    ] == [
        ("Bea", 1, 20, 10),
        ("Ada", 2, 10, 100),
    ]
    assert found["me"]["line"] == (
        "You are #2 with 10 speedpoints. 11 more passes Bea at #1 — about 2 approved run(s)."
    )
    assert found["pending"] is None
    assert set(found["words"]) == set(POINTS_WORDS)
    by_xp = await view.index(bot, guild, ADA, by="xp", verifier=True, staff=True)
    assert [row["name"] for row in by_xp["board"]] == ["Ada", "Bea"]
    assert by_xp["pending"] == 0
    assert (await view.index(bot, guild, ADA, by="nonsense", verifier=False, staff=False))[
        "by"
    ] == "points"


async def test_the_board_shows_the_top_n_and_the_full_board_shows_everyone(bot, guild):
    await bot.store.set(GUILD, "points_top_n", 1)
    await approved(bot, guild, ADA)
    await approved(bot, guild, BEA)

    found = await view.index(bot, guild, CY, verifier=False, staff=False)
    whole = await view.full_board(bot, guild)

    assert [row["name"] for row in found["board"]] == ["Ada"]
    assert [row["name"] for row in whole["rows"]] == ["Ada", "Bea"]
    assert found["me"]["line"] == (
        "You are not on the leaderboard yet. Your first approved run puts you on it."
    )


async def test_first_place_is_told_nobody_is_ahead(bot, guild):
    await approved(bot, guild, ADA)
    found = await view.next_rank_of(bot, guild, ADA)
    assert (found["kind"], found["line"]) == (
        "first",
        "You are #1 with 10 speedpoints. Nobody is ahead of you.",
    )


async def test_a_run_row_carries_its_time_state_and_who_decided(bot, guild):
    run_id = await approved(bot, guild, ADA, time="1:23:45.67")
    row = view.run_row(bot.store, guild, await store_.run(bot.db, GUILD, run_id))
    assert (row["time"], row["state_words"], row["decided_by_name"], row["user_id"]) == (
        "1:23:45.67",
        "approved",
        "Sky",
        str(ADA),
    )


@pytest.mark.parametrize(
    ("kind", "amount", "bonus"), [("multiplier", 1.5, "×1.5"), ("extra", 20, "+20")]
)
async def test_a_bounty_reads_as_one_line_with_its_bonus_and_window(
    bot, guild, kind, amount, bonus
):
    starts = datetime.now(UTC) - timedelta(hours=1)
    ends = datetime(2030, 1, 31, 19, tzinfo=UTC)
    await moves.bounty_create(
        bot,
        guild,
        who(guild, STAFF),
        {
            "name": "Spooky",
            "games": ["Celeste", "Hades"],
            "kind": kind,
            "amount": amount,
            "starts_at": starts.isoformat(),
            "ends_at": ends.isoformat(),
        },
    )

    (found,) = await view.bounties(bot, guild, current_only=True)

    assert found["live"] is True
    assert found["line"] == (
        f"**Spooky** — Celeste, Hades: {bonus} speedpoints, until Jan 31, 12:00."
    )


async def test_an_event_bounty_names_its_event_and_a_past_one_is_not_current(bot, guild):
    at = datetime.now(UTC)
    cur = await bot.db.conn.execute(
        "INSERT INTO events(guild_id, requester_id, title, starts_at, ends_at, status, created_at) "
        "VALUES (?, 1, 'Run night', ?, ?, 'approved', 'now')",
        (
            GUILD,
            (at + timedelta(days=1)).isoformat(),
            (at + timedelta(days=1, hours=2)).isoformat(),
        ),
    )
    await bot.db.conn.commit()
    await moves.bounty_create(
        bot,
        guild,
        who(guild, STAFF),
        {
            "name": "Night",
            "games": ["Celeste"],
            "kind": "extra",
            "amount": 5,
            "event_id": cur.lastrowid,
        },
    )
    await moves.bounty_create(
        bot,
        guild,
        who(guild, STAFF),
        {
            "name": "Old",
            "games": ["Celeste"],
            "kind": "extra",
            "amount": 5,
            "starts_at": "2020-01-01",
            "ends_at": "2020-01-02",
        },
    )

    (found,) = await view.bounties(bot, guild, current_only=True)
    every = await view.bounties(bot, guild)

    assert (found["name"], found["live"], found["event_title"]) == ("Night", False, "Run night")
    assert found["line"] == "**Night** — Celeste: +5 speedpoints, during Run night."
    assert sorted(one["name"] for one in every) == ["Night", "Old"]
