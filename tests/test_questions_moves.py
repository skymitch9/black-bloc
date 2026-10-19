import asyncio
import json
from datetime import timedelta

import pytest

from black_bloc import questions as rules
from black_bloc import questions_moves as moves
from black_bloc import questions_store as store
from black_bloc.logkinds import VIA_WEBSITE
from tests.questions_fakes import (
    AFTER_GRACE,
    BODY,
    GUILD,
    HOME,
    LOG,
    OTHER,
    OWNER,
    REAL,
    SLOT,
    FakeChannel,
    FakeMember,
    FakeMessage,
    make_bot,
    refused,
)


@pytest.fixture
async def bot(db, monkeypatch):
    return await make_bot(db, monkeypatch)


async def kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def details_of(db, kind):
    cur = await db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id", (kind,)
    )
    return [json.loads(row["details"]) for row in await cur.fetchall()]


def home(bot):
    return bot.guild.get_channel(HOME)


def real(bot):
    return bot.guild.get_channel(REAL)


async def queue(bot, *bodies):
    return await store.add_many(bot.db, GUILD, list(bodies or [BODY]), 5, SLOT - timedelta(days=3))


async def seen_before(bot):
    """The loop met the slot ahead of time, the way it does every week."""
    await moves.tick(bot, bot.guild, SLOT - timedelta(days=1))


async def test_shadow_ships_by_default_and_rehearses_in_the_home_with_the_note(bot):
    await queue(bot)
    await seen_before(bot)

    assert await moves.tick(bot, bot.guild, AFTER_GRACE) == rules.POSTED

    assert rules.mode_of(bot.store, GUILD) == rules.SHADOW
    assert real(bot).sent == []
    [post] = home(bot).sent
    assert BODY in post.content and f"<#{REAL}>" in post.content
    row = await store.first_queued(bot.db, GUILD)
    assert row is None
    [details] = await details_of(bot.db, "question.posted_by_bot")
    assert details["mode"] == "shadow" and details["reason"] == "question_owner_user_id is not set"


async def test_nothing_is_posted_inside_the_grace_window(bot):
    await queue(bot)
    await seen_before(bot)

    assert await moves.tick(bot, bot.guild, SLOT + timedelta(minutes=4)) == rules.PENDING
    assert home(bot).sent == []


async def test_the_owners_own_post_with_extra_words_is_found_and_the_bot_stays_quiet(bot):
    await bot.store.set(GUILD, "question_mode", "on")
    await bot.store.set(GUILD, "question_owner_user_id", str(OWNER))
    await queue(bot)
    await seen_before(bot)
    posted = FakeMessage(
        f"QOTW time! **{BODY.upper()}**  tell us below", author=FakeMember(OWNER), at=SLOT
    )
    real(bot).seen.append(posted)

    assert await moves.tick(bot, bot.guild, AFTER_GRACE) == rules.POSTED

    assert real(bot).sent == []
    row = (await store.history(bot.db, GUILD))[0]
    assert (row["posted_by"], row["message_id"]) == (rules.BY_OWNER, posted.id)
    assert "question.posted_by_owner" in await kinds(bot.db)


async def test_someone_else_posting_the_same_words_is_not_the_owner_so_the_bot_posts(bot):
    await bot.store.set(GUILD, "question_mode", "on")
    await bot.store.set(GUILD, "question_owner_user_id", str(OWNER))
    await queue(bot)
    await seen_before(bot)
    real(bot).seen.append(FakeMessage(BODY, author=FakeMember(OTHER), at=SLOT))

    assert await moves.tick(bot, bot.guild, AFTER_GRACE) == rules.POSTED

    [post] = real(bot).sent
    assert post.content == BODY
    [details] = await details_of(bot.db, "question.posted_by_bot")
    assert details["reason"] == "the owner's post was not seen by 09:05"


async def test_two_passes_at_once_post_exactly_one_question(bot):
    """Checklist 37: the boot's on_ready and the loop's first tick both land in the window."""
    await queue(bot, "one?", "two?")
    await seen_before(bot)

    await asyncio.gather(*(moves.tick(bot, bot.guild, AFTER_GRACE) for _ in range(3)))

    assert [post.content.splitlines()[-1] for post in home(bot).sent] == ["one?"]
    assert (await kinds(bot.db)).count("question.posted_by_bot") == 1
    assert [row["body"] for row in await store.queued(bot.db, GUILD)] == ["two?"]


async def test_an_empty_queue_skips_the_week_and_warns_once_ahead(bot):
    await bot.store.set(GUILD, "question_mode", "on")
    for days in (5, 3, 2, 2, 1):
        await moves.tick(bot, bot.guild, SLOT - timedelta(days=days))
    for minutes in (6, 7, 30):
        await moves.tick(bot, bot.guild, SLOT + timedelta(minutes=minutes))

    found = await kinds(bot.db)
    assert found.count("question.warned_empty") == 1
    assert found.count("question.skipped_empty") == 1
    [line] = [
        m.content for m in bot.guild.get_channel(LOG).sent if "queue is empty" in (m.content or "")
    ]
    assert "Monday" in line and "09:00" in line
    assert real(bot).sent == []


async def test_a_question_added_after_the_warning_still_goes_up(bot):
    await moves.tick(bot, bot.guild, SLOT - timedelta(days=2))
    await queue(bot)
    assert await moves.tick(bot, bot.guild, AFTER_GRACE) == rules.POSTED


async def test_a_failed_warning_dm_is_an_error_row_never_silent(bot):
    await bot.store.set(GUILD, "question_mode", "on")
    await bot.store.set(GUILD, "question_owner_user_id", str(OWNER))
    owner = FakeMember(OWNER)
    owner.dm_raises = refused()
    bot.guild.members[OWNER] = owner

    await moves.tick(bot, bot.guild, SLOT - timedelta(days=1))

    [error] = await details_of(bot.db, "error.dm")
    assert error["where"] == "question.warned_empty"
    [warned] = await details_of(bot.db, "question.warned_empty")
    assert warned["dm"] == "failed"


async def test_the_warning_dm_reaches_the_owner_when_it_can(bot):
    await bot.store.set(GUILD, "question_mode", "on")
    await bot.store.set(GUILD, "question_owner_user_id", str(OWNER))
    owner = FakeMember(OWNER)
    bot.guild.members[OWNER] = owner

    await moves.tick(bot, bot.guild, SLOT - timedelta(days=1))

    assert len(owner.dms) == 1 and "error.dm" not in await kinds(bot.db)


async def test_a_restart_inside_the_catch_up_window_still_posts(bot):
    await queue(bot)
    await seen_before(bot)

    assert await moves.tick(bot, bot.guild, SLOT + timedelta(hours=20)) == rules.POSTED


async def test_past_the_catch_up_window_the_week_is_missed_and_never_posted_late(bot):
    await queue(bot)
    await seen_before(bot)

    assert await moves.tick(bot, bot.guild, SLOT + timedelta(hours=25)) == rules.MISSED
    assert await moves.tick(bot, bot.guild, SLOT + timedelta(hours=26)) == rules.MISSED

    assert home(bot).sent == []
    assert (await kinds(bot.db)).count("question.missed") == 1
    assert len(await store.queued(bot.db, GUILD)) == 1


async def test_a_slot_the_bot_never_knew_about_is_not_reported_missed(bot):
    """Checklist 43's cousin: a first boot after the feature lands starts the clock now."""
    await queue(bot)

    assert await moves.tick(bot, bot.guild, SLOT + timedelta(days=2)) is None
    assert "question.missed" not in await kinds(bot.db)
    assert home(bot).sent == []


async def test_off_resolves_nothing_and_posts_nothing(bot):
    await bot.store.set(GUILD, "question_mode", "off")
    await queue(bot)

    assert await moves.tick(bot, bot.guild, AFTER_GRACE) is None
    assert home(bot).sent == [] and real(bot).sent == []
    assert (await moves.post_now(bot, bot.guild, None, now=AFTER_GRACE)).code == "questions_off"


async def test_on_with_no_channel_says_so_once_and_posts_when_one_is_set(bot):
    await bot.store.set(GUILD, "question_mode", "on")
    await bot.store.clear(GUILD, "question_channel_id")
    await queue(bot)
    await seen_before(bot)

    for minutes in (6, 7, 8):
        assert await moves.tick(bot, bot.guild, SLOT + timedelta(minutes=minutes)) == rules.PENDING
    assert (await kinds(bot.db)).count("question.post_failed") == 1

    await bot.store.set(GUILD, "question_channel_id", REAL)
    assert await moves.tick(bot, bot.guild, SLOT + timedelta(minutes=9)) == rules.POSTED


async def test_take_it_down_deletes_the_bots_post_and_puts_the_question_back_on_top(bot):
    first, second = await queue(bot, "one?", "two?")
    await seen_before(bot)
    await moves.tick(bot, bot.guild, AFTER_GRACE)
    [post] = home(bot).sent

    outcome = await moves.take_down(bot, bot.guild, None, first, via=VIA_WEBSITE, now=AFTER_GRACE)

    assert outcome.ok and home(bot).deleted == [post.id]
    assert [row["id"] for row in await store.queued(bot.db, GUILD)] == [first, second]
    slot = await store.get_slot(bot.db, GUILD, rules.slot_key(SLOT))
    assert slot["status"] == rules.TAKEN_DOWN
    assert await moves.tick(bot, bot.guild, AFTER_GRACE + timedelta(minutes=1)) == (
        rules.TAKEN_DOWN
    )
    assert len(home(bot).sent) == 1
    assert "web.question.taken_down" in await kinds(bot.db)

    again = await moves.post_now(bot, bot.guild, None, now=AFTER_GRACE + timedelta(minutes=2))
    assert again.ok and home(bot).sent[-1].content.endswith("one?")


async def test_the_owners_own_post_is_never_taken_down(bot):
    await bot.store.set(GUILD, "question_owner_user_id", str(OWNER))
    [first] = await queue(bot)
    await seen_before(bot)
    home(bot).seen.append(FakeMessage(BODY, author=FakeMember(OWNER), at=SLOT))
    await moves.tick(bot, bot.guild, AFTER_GRACE)

    outcome = await moves.take_down(bot, bot.guild, None, first, now=AFTER_GRACE)

    assert not outcome.ok and outcome.message == rules.NOT_BOTS
    assert home(bot).deleted == []


async def test_a_refused_delete_changes_nothing(bot):
    [first] = await queue(bot)
    await seen_before(bot)
    await moves.tick(bot, bot.guild, AFTER_GRACE)
    home(bot).delete_raises = refused()

    outcome = await moves.take_down(bot, bot.guild, None, first, now=AFTER_GRACE)

    assert not outcome.ok and outcome.code == "not_deleted"
    assert (await store.get(bot.db, GUILD, first))["status"] == rules.POSTED


async def test_post_now_goes_up_ahead_of_the_slot_and_the_slot_then_rests(bot):
    await queue(bot, "one?", "two?")
    early = SLOT - timedelta(days=2)

    outcome = await moves.post_now(bot, bot.guild, None, now=early)
    assert outcome.ok
    again = await moves.post_now(bot, bot.guild, None, now=early)
    assert again.message == rules.ALREADY_UP

    assert await moves.tick(bot, bot.guild, AFTER_GRACE) == rules.POSTED
    assert len(home(bot).sent) == 1
    [details] = await details_of(bot.db, "question.posted_by_bot")
    assert details["reason"] == "posted now by staff"


async def test_skip_leaves_the_question_queued_and_undo_brings_the_week_back(bot):
    await queue(bot)
    await seen_before(bot)

    assert (await moves.skip(bot, bot.guild, None, now=SLOT - timedelta(hours=1))).ok
    assert await moves.tick(bot, bot.guild, AFTER_GRACE) == rules.SKIPPED
    assert home(bot).sent == [] and len(await store.queued(bot.db, GUILD)) == 1
    assert not (await moves.skip(bot, bot.guild, None, now=AFTER_GRACE)).ok

    assert (await moves.unskip(bot, bot.guild, None, now=AFTER_GRACE)).ok
    assert await moves.tick(bot, bot.guild, AFTER_GRACE) == rules.POSTED
    assert not (await moves.unskip(bot, bot.guild, None, now=AFTER_GRACE)).ok


async def test_a_thread_opens_on_the_question_when_threads_are_on(bot):
    await bot.store.set(GUILD, "question_thread", True)
    await queue(bot, "x" * 300)
    await seen_before(bot)

    await moves.tick(bot, bot.guild, AFTER_GRACE)

    [post] = home(bot).sent
    assert post.threads == ["x" * 100]


async def test_a_thread_that_cannot_open_is_logged_and_the_post_stands(bot):
    await bot.store.set(GUILD, "question_thread", True)
    await queue(bot)
    await seen_before(bot)
    original = FakeChannel.send

    async def sending(self, content=None, **kwargs):
        message = await original(self, content, **kwargs)
        message.thread_raises = refused()
        return message

    FakeChannel.send = sending
    try:
        assert await moves.tick(bot, bot.guild, AFTER_GRACE) == rules.POSTED
    finally:
        FakeChannel.send = original
    assert "question.thread_failed" in await kinds(bot.db)


async def test_add_edit_move_remove_and_put_back(bot):
    added = await moves.add(bot, bot.guild, None, "one?\n\ntwo?\nthree?")
    first, second, third = added.value
    assert added.message == "3 question(s) added to the queue."
    assert not (await moves.add(bot, bot.guild, None, "  \n ")).ok

    assert (await moves.edit(bot, bot.guild, None, second, "two, edited?")).ok
    assert (await moves.move(bot, bot.guild, None, third, "up")).ok
    assert (await moves.move(bot, bot.guild, None, first, "up")).code == "not_moved"
    order = [row["body"] for row in await store.queued(bot.db, GUILD)]
    assert order == ["one?", "three?", "two, edited?"]

    assert (await moves.remove(bot, bot.guild, None, first)).ok
    assert (await moves.edit(bot, bot.guild, None, first, "nope")).code == "not_queued"
    assert (await moves.requeue(bot, bot.guild, None, first)).ok
    assert [row["body"] for row in await store.queued(bot.db, GUILD)][-1] == "one?"
    assert (await moves.requeue(bot, bot.guild, None, first)).code == "not_removed"
    assert (await moves.remove(bot, bot.guild, None, 999)).code == "no_question"


async def test_the_week_reads_this_weeks_slot_and_its_question(bot):
    await queue(bot)
    await seen_before(bot)
    found = await moves.week(bot, bot.guild, SLOT - timedelta(hours=1))
    assert found["slot"] == SLOT and found["status"] == rules.PENDING
    assert found["question"]["body"] == BODY
