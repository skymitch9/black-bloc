import json
from datetime import UTC, datetime, timedelta

import pytest

from black_bloc.chat_memory import forget, forget_everywhere
from black_bloc.chat_voice import (
    NAMED,
    PINNED,
    ROLLED,
    Heard,
    heard_for,
    heard_from,
    hears_now,
    pin,
    roster,
    talking_now,
    unpin,
    voice_key,
    voice_row,
    voice_rows,
    window_turns,
)
from black_bloc.personas import BY_NAME, COOKOUT, POOL, TROPE_NAMES, from_the_pool
from black_bloc.storage.db import Database

GUILD = 7
NOW = datetime(2026, 9, 23, 18, 0, tzinfo=UTC)


def rows(*names, enabled=True):
    return [
        {
            "name": name,
            "label": BY_NAME[name].label,
            "voice": BY_NAME[name].voice,
            "neighbours": json.dumps(list(BY_NAME[name].neighbours)),
            "enabled": 1 if enabled else 0,
        }
        for name in names
    ]


def row(**given):
    found = {"trope": None, "turns": 0, "since": None, "pinned": None, "pinned_by": None,
             "pinned_at": None, "user_id": 900}
    found.update(given)
    return found


@pytest.fixture
async def db(tmp_path):
    found = Database(tmp_path / "v.sqlite3")
    await found.connect()
    try:
        yield found
    finally:
        await found.close()


async def a_turn(db, user_id, channel_id, at, tier="simple"):
    await db.conn.execute(
        "INSERT INTO chat_window(guild_id, channel_id, user_id, at, speaker, content, tier) "
        "VALUES (?, ?, ?, ?, 'bot', 'hi', ?)",
        (GUILD, channel_id, user_id, at.isoformat(), tier),
    )
    await db.conn.commit()


def test_the_cookout_setting_is_no_tone_for_anybody_even_a_pinned_member():
    found = heard_from(COOKOUT, rows(*TROPE_NAMES), row(pinned="noir"), guild_id=GUILD,
                       user_id=900, turns=3, now=NOW)
    assert found == Heard(None)
    assert found.name == COOKOUT


def test_a_pin_beats_a_named_mood_and_the_pool():
    for setting in (POOL, "warm"):
        found = heard_from(setting, rows(*TROPE_NAMES), row(pinned="noir"), guild_id=GUILD,
                           user_id=900, turns=0, now=NOW)
        assert (found.name, found.source) == ("noir", PINNED)


def test_a_pin_to_a_mood_that_is_off_falls_through_to_the_setting():
    pool = rows("warm") + rows("noir", enabled=False)
    found = heard_from("warm", pool, row(pinned="noir"), guild_id=GUILD, user_id=900, turns=0,
                       now=NOW)
    assert (found.name, found.source) == ("warm", NAMED)


def test_a_named_mood_is_that_mood_for_everybody_without_a_pin():
    found = heard_from("deadpan", rows(*TROPE_NAMES), None, guild_id=GUILD, user_id=900, turns=0,
                       now=NOW)
    assert (found.name, found.source) == ("deadpan", NAMED)


def test_the_roll_is_seeded_by_guild_member_and_when_their_window_opened():
    pool = rows(*TROPE_NAMES)
    found = heard_from(POOL, pool, None, guild_id=GUILD, user_id=900, turns=0, now=NOW)
    assert found.source == ROLLED
    assert found.since == NOW.isoformat()
    from black_bloc.personas import enabled_tropes

    wanted = from_the_pool(enabled_tropes(pool), voice_key(GUILD, 900, NOW.isoformat()), 0)
    assert found.name == wanted.name


def test_an_open_window_keeps_its_start_and_drifts_with_the_turns():
    pool = rows(*TROPE_NAMES)
    since = (NOW - timedelta(minutes=10)).isoformat()
    kept = row(since=since, trope="warm")
    found = heard_from(POOL, pool, kept, guild_id=GUILD, user_id=900, turns=8, now=NOW)
    from black_bloc.personas import enabled_tropes

    assert found.since == since and found.turns == 8
    assert found.name == from_the_pool(enabled_tropes(pool), voice_key(GUILD, 900, since), 8).name


def test_an_empty_window_rolls_again_from_now():
    since = (NOW - timedelta(hours=2)).isoformat()
    found = heard_from(POOL, rows(*TROPE_NAMES), row(since=since), guild_id=GUILD, user_id=900,
                       turns=0, now=NOW)
    assert found.since == NOW.isoformat() and found.turns == 0


def test_an_empty_pool_is_the_cookout_voice():
    found = heard_from(POOL, [], None, guild_id=GUILD, user_id=900, turns=0, now=NOW)
    assert found.trope is None and found.source == COOKOUT


async def test_the_window_counts_model_turns_in_every_channel_and_nothing_older(db):
    await a_turn(db, 900, 11, NOW - timedelta(minutes=5))
    await a_turn(db, 900, 12, NOW - timedelta(minutes=20))
    await a_turn(db, 900, 12, NOW - timedelta(minutes=45))
    await a_turn(db, 900, 11, NOW - timedelta(minutes=1), tier=None)
    await a_turn(db, 901, 11, NOW - timedelta(minutes=1))
    assert await window_turns(db, GUILD, 900, now=NOW) == 2
    assert await talking_now(db, GUILD, now=NOW) == {900: 2, 901: 1}


async def test_the_tone_is_written_down_and_a_pin_survives_the_next_reply(db):
    first = await heard_for(db, POOL, rows(*TROPE_NAMES), guild_id=GUILD, user_id=900, now=NOW)
    stored = await voice_row(db, GUILD, 900)
    assert stored["trope"] == first.name and stored["since"] == NOW.isoformat()

    await pin(db, GUILD, 900, "scholar", by=7)
    again = await heard_for(db, POOL, rows(*TROPE_NAMES), guild_id=GUILD, user_id=900, now=NOW)
    stored = await voice_row(db, GUILD, 900)
    assert again.name == "scholar"
    assert (stored["pinned"], stored["pinned_by"], stored["trope"]) == ("scholar", 7, "scholar")


async def test_the_cookout_setting_writes_nothing_down(db):
    found = await heard_for(db, COOKOUT, rows(*TROPE_NAMES), guild_id=GUILD, user_id=900, now=NOW)
    assert found.trope is None
    assert await voice_row(db, GUILD, 900) is None


async def test_clearing_a_pin_leaves_the_roll_and_says_whether_there_was_one(db):
    await pin(db, GUILD, 900, "noir", by=7)
    assert await unpin(db, GUILD, 900) is True
    assert await unpin(db, GUILD, 900) is False
    stored = await voice_row(db, GUILD, 900)
    assert stored["pinned"] is None and stored["pinned_by"] is None


async def test_forgetting_a_members_memory_never_clears_their_pin(db):
    """`/memory` "forget the lot" is about what the bot knows, not the tone staff chose."""
    await pin(db, GUILD, 900, "noir", by=7)
    await forget(db, 900, GUILD)
    await forget_everywhere(db, 900)
    assert (await voice_row(db, GUILD, 900))["pinned"] == "noir"


async def test_the_roster_lists_pins_first_and_says_who_is_talking_now(db):
    await heard_for(db, POOL, rows(*TROPE_NAMES), guild_id=GUILD, user_id=901, now=NOW)
    await pin(db, GUILD, 900, "noir", by=7)
    found = roster(await voice_rows(db, GUILD), POOL, TROPE_NAMES, {901: 1})
    assert [one["user_id"] for one in found] == [900, 901]
    assert found[0]["trope"] == "noir" and found[0]["pinned_by"] == 7
    assert found[0]["active"] is False and found[1]["active"] is True


def test_what_a_member_hears_now_follows_the_same_precedence():
    kept = row(trope="warm", pinned="noir")
    assert hears_now(COOKOUT, kept, set(TROPE_NAMES)) == COOKOUT
    assert hears_now(POOL, kept, set(TROPE_NAMES)) == "noir"
    assert hears_now(POOL, kept, {"warm"}) == "warm"
    assert hears_now("deadpan", row(trope="warm"), set(TROPE_NAMES)) == "deadpan"
    assert hears_now("deadpan", row(trope="warm"), {"warm"}) == COOKOUT


def test_a_pin_to_a_mood_that_is_off_is_listed_as_waiting():
    found = roster([row(pinned="noir", trope="warm")], POOL, {"warm"}, {})
    assert found[0]["waiting"] is True and found[0]["trope"] == "warm"
