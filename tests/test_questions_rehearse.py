import json
from datetime import timedelta

import pytest

from black_bloc import questions as rules
from black_bloc import questions_moves as moves
from black_bloc import questions_rehearse as testing
from black_bloc import questions_store as store
from black_bloc.logkinds import VIA_WEBSITE
from tests.questions_fakes import (
    AFTER_GRACE,
    BODY,
    GUILD,
    HOME,
    LOG,
    REAL,
    SLOT,
    FakeMember,
    make_bot,
    refused,
)

EARLY = SLOT - timedelta(days=2)


@pytest.fixture
async def bot(db, monkeypatch):
    return await make_bot(db, monkeypatch)


async def details_of(db, kind):
    cur = await db.conn.execute(
        "SELECT details, actor_id FROM action_log WHERE kind = ? ORDER BY id", (kind,)
    )
    return [(json.loads(row["details"]), row["actor_id"]) for row in await cur.fetchall()]


async def slots(db):
    cur = await db.conn.execute(
        "SELECT slot_at, status, question_id, note FROM weekly_question_slots ORDER BY slot_at"
    )
    return [tuple(row) for row in await cur.fetchall()]


async def questions(db):
    cur = await db.conn.execute(
        "SELECT id, position, status, slot_at, posted_by, channel_id, message_id "
        "FROM weekly_questions ORDER BY id"
    )
    return [tuple(row) for row in await cur.fetchall()]


async def queue(bot, *bodies):
    return await store.add_many(bot.db, GUILD, list(bodies or [BODY]), 5, SLOT - timedelta(days=3))


async def test_a_test_copy_of_the_top_question_goes_to_the_home_and_nothing_else_moves(bot):
    await bot.store.set(GUILD, "posts_mode", "on")
    await bot.store.set(GUILD, "question_template", "QOTW: {question}")
    await queue(bot, BODY, "second?")
    await moves.tick(bot, bot.guild, EARLY)
    slots_before, questions_before = await slots(bot.db), await questions(bot.db)
    staff = FakeMember(42)

    outcome = await testing.rehearse(bot, bot.guild, staff, via=VIA_WEBSITE, now=EARLY)

    assert outcome.ok and outcome.message == testing.TESTED.format(where=HOME)
    [copy] = bot.guild.get_channel(HOME).sent
    assert copy.content == f"QOTW: {BODY}"
    assert bot.guild.get_channel(REAL).sent == []
    assert await slots(bot.db) == slots_before
    assert await questions(bot.db) == questions_before
    [(details, actor)] = await details_of(bot.db, "web.question.rehearsed")
    assert actor == 42
    assert details["question_id"] == outcome.value and details["question"] == BODY
    assert details["shadow_home"] == HOME and details["message_id"] == copy.id
    assert details["url"] == f"https://discord.com/channels/{GUILD}/{HOME}/{copy.id}"


def test_a_posted_week_tests_the_question_that_went_up_not_the_next_one():
    posted, queued = {"body": "up?"}, {"body": "next?"}
    week = {"status": rules.POSTED, "posted": posted, "question": queued}

    assert testing.this_weeks_question(week) is posted
    assert testing.this_weeks_question(week | {"status": rules.PENDING}) is queued
    assert testing.this_weeks_question(week | {"posted": None}) is queued
    assert testing.this_weeks_question({"status": rules.PENDING, "question": None}) is None


async def test_the_question_this_week_shows_is_the_one_sent(bot):
    await queue(bot, BODY, "second?")
    await moves.tick(bot, bot.guild, SLOT - timedelta(days=1))
    await moves.tick(bot, bot.guild, AFTER_GRACE)

    outcome = await testing.rehearse(bot, bot.guild, None, now=AFTER_GRACE + timedelta(minutes=1))

    assert outcome.ok
    assert bot.guild.get_channel(HOME).sent[-1].content == "second?"


async def test_off_an_empty_queue_and_no_home_are_refused_in_words(bot):
    assert (await testing.rehearse(bot, bot.guild, None, now=EARLY)).message == (
        testing.NOTHING_TO_TEST
    )
    await queue(bot)
    await bot.store.set(GUILD, "posts_mode", "off")
    off = await testing.rehearse(bot, bot.guild, None, now=EARLY)
    assert (off.ok, off.code, off.message) == (False, "questions_off", testing.TEST_OFF)
    await bot.store.set(GUILD, "posts_mode", "on")
    for key in ("shadow_channel_id", "log_channel_id"):
        await bot.store.clear(GUILD, key)

    nowhere = await testing.rehearse(bot, bot.guild, None, now=EARLY)

    assert (nowhere.code, nowhere.message) == ("no_shadow_channel", rules.NO_REHEARSAL)
    assert all(not channel.sent for channel in bot.guild.channels.values())
    assert await details_of(bot.db, "question.rehearsed") == []


async def test_the_test_channel_takes_it_and_discord_refusing_is_said(bot):
    await queue(bot)
    await bot.store.set(GUILD, "shadow_channel_id", LOG)
    bot.guild.get_channel(LOG).send_raises = refused(403)

    outcome = await testing.rehearse(bot, bot.guild, None, now=EARLY)

    assert (outcome.ok, outcome.code) == (False, "not_posted")
    assert outcome.message == rules.POST_REFUSED.format(why="403 no")
    assert bot.guild.get_channel(HOME).sent == []


async def test_can_test_needs_a_mode_a_question_and_a_home(bot):
    await queue(bot)
    found = await moves.week(bot, bot.guild, EARLY)
    assert testing.can_test(bot, bot.guild, found)
    assert not testing.can_test(bot, bot.guild, found | {"mode": rules.OFF})
    assert not testing.can_test(bot, bot.guild, found | {"question": None})
    for key in ("shadow_channel_id", "log_channel_id"):
        await bot.store.clear(GUILD, key)
    assert not testing.can_test(bot, bot.guild, found)
