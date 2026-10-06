import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import discord
import pytest

from black_bloc import sticky as rules
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore
from black_bloc.sticky_posts import (
    FAILED,
    NOT_RUNNING,
    POSTED,
    REHEARSED,
    TEST_MODE,
    TOO_SOON,
    Desk,
    desk_of,
    missing_permissions,
)

GUILD = 7
RUNS = 333
HOME = 444
LOG = 222
OTHER_HOME = 555
VOICE = 666
STAFFER = 1
BOT_ID = 42
WORDS = "How to submit a run: post the link and your time."


class _Response:
    def __init__(self, status):
        self.status = status
        self.reason = "refused"


def forbidden():
    return discord.Forbidden(_Response(403), "Missing Permissions")


class FakeMessage:
    def __init__(self, channel, message_id, content, kwargs):
        self.channel = channel
        self.id = message_id
        self.content = content
        self.kwargs = kwargs

    async def delete(self):
        if self.channel.delete_raises is not None:
            raise self.channel.delete_raises
        if self not in self.channel.messages:
            raise discord.NotFound(_Response(404), "Unknown Message")
        self.channel.messages.remove(self)
        self.channel.deleted.append(self.id)


class FakeChannel:
    _next = 5000

    def __init__(self, channel_id, name="runs", kind="text"):
        self.id = channel_id
        self.name = name
        self.type = SimpleNamespace(name=kind)
        self.messages = []
        self.deleted = []
        self.send_raises = None
        self.delete_raises = None
        self.perms = SimpleNamespace(view_channel=True, send_messages=True)

    def permissions_for(self, who):
        return self.perms

    async def send(self, content=None, **kwargs):
        if self.send_raises is not None:
            raise self.send_raises
        FakeChannel._next += 1
        message = FakeMessage(self, FakeChannel._next, content, kwargs)
        self.messages.append(message)
        return message

    def get_partial_message(self, message_id):
        found = next((one for one in self.messages if one.id == int(message_id)), None)
        return found if found is not None else FakeMessage(self, int(message_id), "", {})


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.me = SimpleNamespace(id=BOT_ID)
        self.unavailable = False
        self.channels = {}
        for channel_id, name, kind in (
            (RUNS, "runs", "text"),
            (HOME, "welcome-test", "text"),
            (LOG, "blackbloc-logs", "text"),
            (OTHER_HOME, "other-home", "text"),
            (VOICE, "voice", "voice"),
        ):
            self.channels[channel_id] = FakeChannel(channel_id, name, kind)

    def get_channel(self, channel_id):
        return self.channels.get(int(channel_id))


class FakeGuard:
    def __init__(self, allowed):
        self.test_channel_id = allowed

    def allows_channel(self, channel_id):
        return int(getattr(channel_id, "id", channel_id)) == self.test_channel_id


class Clock:
    def __init__(self):
        self.at = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
        self.slept = []
        self.gate = None

    def now(self):
        return self.at

    def tick(self, seconds):
        self.at += timedelta(seconds=seconds)

    async def sleep(self, seconds):
        self.slept.append(seconds)
        if self.gate is not None:
            await self.gate.wait()
        self.tick(seconds)


def person(channel, *, bot=False, webhook=None, kind=discord.MessageType.default):
    return SimpleNamespace(
        guild=channel.guild,
        channel=channel,
        author=SimpleNamespace(id=900, bot=bot),
        webhook_id=webhook,
        type=kind,
    )


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    store = SettingsStore(db, load_settings(_env_file=None))
    await store.load()
    guild = FakeGuild()
    for channel in guild.channels.values():
        channel.guild = guild
    await store.set(GUILD, "shadow_channel_id", HOME)
    return SimpleNamespace(
        db=db,
        store=store,
        guard=None,
        guild=guild,
        guilds=[guild],
        user=SimpleNamespace(id=BOT_ID),
        get_channel=guild.get_channel,
        get_guild=lambda _id: guild,
    )


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def desk(bot, clock):
    return Desk(bot, now=clock.now, sleep=clock.sleep)


def channel(bot, channel_id=RUNS):
    return bot.guild.get_channel(channel_id)


async def kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def row_of(bot, channel_id=RUNS):
    return await rules.get_row(bot.db, GUILD, channel_id)


async def talk(desk, bot, times, channel_id=RUNS):
    for _ in range(times):
        await desk.on_message(person(channel(bot, channel_id)))


async def live(bot, desk):
    await bot.store.set(GUILD, "sticky_mode", "on")
    return await desk.save(bot.guild, RUNS, WORDS, STAFFER)


async def test_the_mode_ships_shadow_and_a_save_rehearses_in_the_home_with_the_note(bot, desk, db):
    assert bot.store.get(GUILD, "sticky_mode") == "shadow"

    outcome = await desk.save(bot.guild, RUNS, WORDS, STAFFER)

    assert outcome.ok and outcome.code == "set"
    assert channel(bot).messages == []
    copy = channel(bot, HOME).messages[0]
    assert copy.content == f"Rehearsal — this is where it would go: <#{RUNS}>\n{WORDS}"
    assert copy.kwargs["allowed_mentions"].everyone is False
    assert copy.kwargs["silent"] is True
    row = await row_of(bot)
    assert (row["message_id"], row["posted_channel_id"]) == (copy.id, HOME)
    assert rules.state_of(row, "shadow") == rules.REHEARSING
    assert await kinds(db) == ["sticky.set", "sticky.would_post"]
    assert f"<#{HOME}>" in outcome.message and f"<#{RUNS}>" in outcome.message


async def test_the_features_own_home_wins_over_the_global_one(bot, desk):
    await bot.store.set(GUILD, "sticky_shadow_channel_id", OTHER_HOME)

    await desk.save(bot.guild, RUNS, WORDS, STAFFER)

    assert channel(bot, HOME).messages == []
    assert len(channel(bot, OTHER_HOME).messages) == 1


async def test_on_posts_the_words_alone_at_the_bottom_of_its_own_channel(bot, desk, db):
    outcome = await live(bot, desk)

    assert [one.content for one in channel(bot).messages] == [WORDS]
    assert channel(bot, HOME).messages == []
    assert await kinds(db) == ["sticky.set", "sticky.posted"]
    assert outcome.message == rules.SAVED_LIVE.format(channel_id=RUNS)
    assert rules.state_of(await row_of(bot), "on") == rules.LIVE


async def test_it_moves_only_after_both_the_count_and_the_gap(bot, desk, clock, db):
    await live(bot, desk)
    first = channel(bot).messages[0].id

    await talk(desk, bot, 4)
    clock.tick(600)
    assert [one.id for one in channel(bot).messages] == [first]

    await talk(desk, bot, 1)

    assert channel(bot).deleted == [first]
    assert len(channel(bot).messages) == 1 and channel(bot).messages[0].id != first
    row = await row_of(bot)
    assert row["reposts"] == 1 and row["message_id"] == channel(bot).messages[0].id
    assert await kinds(db) == ["sticky.set", "sticky.posted"]


async def test_a_busy_channel_waits_out_the_gap_and_then_posts_once(bot, desk, clock):
    await live(bot, desk)
    first = channel(bot).messages[0].id
    clock.tick(10)
    clock.gate = asyncio.Event()

    await talk(desk, bot, 40)

    assert [one.id for one in channel(bot).messages] == [first]
    assert list(desk.waiting) == [RUNS]
    clock.gate.set()
    await desk.waiting[RUNS]

    assert clock.slept == [20.0]
    assert len(channel(bot).messages) == 1 and channel(bot).deleted == [first]
    assert (await row_of(bot))["reposts"] == 1
    assert desk.waiting == {} and desk.heard[RUNS] == 0


async def test_two_triggers_at_once_never_leave_two_copies(bot, desk, clock):
    await live(bot, desk)
    clock.tick(600)

    await asyncio.gather(desk.place(bot.guild, RUNS), desk.place(bot.guild, RUNS))

    assert len(channel(bot).messages) == 1
    assert (await row_of(bot))["reposts"] == 1
    assert await desk.place(bot.guild, RUNS) == TOO_SOON


async def test_bots_webhooks_system_messages_and_other_channels_do_not_count(bot, desk, clock):
    await live(bot, desk)
    clock.tick(600)
    runs = channel(bot)

    for message in (
        person(runs, bot=True),
        person(runs, webhook=77),
        person(runs, kind=discord.MessageType.pins_add),
        person(channel(bot, LOG)),
    ) * 5:
        await desk.on_message(message)

    assert desk.heard.get(RUNS, 0) == 0
    assert len(runs.messages) == 1 and runs.deleted == []


async def test_the_numbers_come_from_the_settings(bot, desk, clock):
    await bot.store.set(GUILD, "sticky_after_messages", 2)
    await bot.store.set(GUILD, "sticky_min_seconds", 5)
    await bot.store.set(GUILD, "sticky_silent", False)
    await live(bot, desk)
    clock.tick(6)

    await talk(desk, bot, 2)

    assert (await row_of(bot))["reposts"] == 1
    assert channel(bot).messages[0].kwargs["silent"] is False


async def test_a_restart_keeps_the_stored_copy_and_replaces_it_rather_than_adding_one(
    bot, desk, clock
):
    await live(bot, desk)
    first = channel(bot).messages[0].id
    clock.tick(600)

    again = Desk(bot, now=clock.now, sleep=clock.sleep)
    await again.load()
    assert again.watched == {RUNS}
    await again.settle(bot.guild)
    assert [one.id for one in channel(bot).messages] == [first]

    await talk(again, bot, 5)

    assert len(channel(bot).messages) == 1 and channel(bot).deleted == [first]


async def test_a_copy_somebody_deleted_by_hand_is_simply_posted_again(bot, desk, clock):
    await live(bot, desk)
    channel(bot).messages.clear()
    clock.tick(600)

    await talk(desk, bot, 5)

    assert len(channel(bot).messages) == 1
    assert (await row_of(bot))["trouble"] is None


async def test_a_lost_permission_stops_it_once_in_words_and_is_not_tried_again(
    bot, desk, clock, db
):
    await live(bot, desk)
    first = channel(bot).messages[0].id
    channel(bot).perms.send_messages = False
    clock.tick(600)

    await talk(desk, bot, 30)

    row = await row_of(bot)
    assert "Send Messages" in row["trouble"] and f"<#{RUNS}>" in row["trouble"]
    assert rules.state_of(row, "on") == rules.STOPPED
    assert [one.id for one in channel(bot).messages] == [first]
    assert (await kinds(db)).count("sticky.post_failed") == 1
    assert RUNS not in desk.watched


async def test_a_refused_send_never_raises_and_try_again_brings_it_back(bot, desk, clock, db):
    await live(bot, desk)
    channel(bot).send_raises = forbidden()
    clock.tick(600)

    await talk(desk, bot, 5)

    stopped = await row_of(bot)
    assert "Discord refused (403)" in stopped["trouble"] and stopped["message_id"] is None
    assert channel(bot).messages == []

    channel(bot).send_raises = None
    outcome = await desk.resume(bot.guild, RUNS, STAFFER)

    assert outcome.ok and len(channel(bot).messages) == 1
    assert (await row_of(bot))["trouble"] is None
    assert (await kinds(db))[-3:] == ["sticky.post_failed", "sticky.resumed", "sticky.posted"]


async def test_an_old_copy_that_will_not_delete_is_never_posted_on_top_of(bot, desk, clock):
    await live(bot, desk)
    channel(bot).delete_raises = forbidden()
    clock.tick(600)

    await talk(desk, bot, 5)

    assert len(channel(bot).messages) == 1
    assert "could not be deleted" in (await row_of(bot))["trouble"]


async def test_a_channel_discord_no_longer_has_is_logged_once_and_forgotten(bot, desk, db):
    await live(bot, desk)

    assert await desk.channel_deleted(bot.guild, RUNS) is True
    assert await desk.channel_deleted(bot.guild, RUNS) is False

    assert await row_of(bot) is None and RUNS not in desk.watched
    assert (await kinds(db)).count("sticky.channel_gone") == 1


async def test_a_channel_that_vanished_without_the_event_stops_in_words(bot, desk, clock, db):
    await live(bot, desk)
    del bot.guild.channels[RUNS]
    clock.tick(600)

    assert await desk.place(bot.guild, RUNS) == FAILED
    assert (await row_of(bot))["trouble"] == rules.TROUBLE_CHANNEL_GONE
    assert await desk.place(bot.guild, RUNS) == NOT_RUNNING
    assert (await kinds(db)).count("sticky.post_failed") == 1


async def test_shadow_with_no_home_at_all_says_which_setting_to_set(bot, desk):
    await bot.store.clear(GUILD, "shadow_channel_id")

    outcome = await desk.save(bot.guild, RUNS, WORDS, STAFFER)

    assert outcome.ok and "shadow_channel_id" in outcome.message
    assert (await row_of(bot))["trouble"] == rules.TROUBLE_NO_HOME


async def test_pause_takes_the_copy_down_and_resume_puts_it_back(bot, desk, clock, db):
    await live(bot, desk)

    paused = await desk.pause(bot.guild, RUNS, STAFFER)
    assert paused.ok and channel(bot).messages == []
    assert rules.state_of(await row_of(bot), "on") == rules.PAUSED
    assert (await desk.pause(bot.guild, RUNS, STAFFER)).code == "already_paused"
    clock.tick(600)
    await talk(desk, bot, 20)
    assert channel(bot).messages == []

    resumed = await desk.resume(bot.guild, RUNS, STAFFER)

    assert resumed.ok and len(channel(bot).messages) == 1
    assert (await desk.resume(bot.guild, RUNS, STAFFER)).code == "not_paused"
    assert (await kinds(db))[2:] == ["sticky.paused", "sticky.resumed", "sticky.posted"]


async def test_remove_takes_the_copy_and_the_words_whatever_the_mode_is_now(bot, desk, db):
    await live(bot, desk)
    await bot.store.set(GUILD, "sticky_mode", "off")

    outcome = await desk.remove(bot.guild, RUNS, STAFFER)

    assert outcome.ok and channel(bot).messages == []
    assert await row_of(bot) is None
    assert (await desk.remove(bot.guild, RUNS, STAFFER)).status == 404
    assert (await kinds(db))[-1] == "sticky.removed"


async def test_an_edit_replaces_the_copy_and_keeps_a_paused_one_down(bot, desk, db):
    await live(bot, desk)

    edited = await desk.save(bot.guild, RUNS, "New words.", STAFFER)

    assert edited.code == "edited"
    assert [one.content for one in channel(bot).messages] == ["New words."]
    await desk.pause(bot.guild, RUNS, STAFFER)
    quiet = await desk.save(bot.guild, RUNS, "Newer words.", STAFFER)
    assert quiet.message == rules.SAVED_PAUSED and channel(bot).messages == []
    assert (await row_of(bot))["text"] == "Newer words."


async def test_a_save_refuses_in_words_and_writes_nothing(bot, desk, db):
    blank = await desk.save(bot.guild, RUNS, "   ", STAFFER)
    long = await desk.save(bot.guild, RUNS, "x" * (rules.TEXT_MAX + 1), STAFFER)
    nowhere = await desk.save(bot.guild, 999, WORDS, STAFFER)
    voice = await desk.save(bot.guild, VOICE, WORDS, STAFFER)

    assert (blank.code, long.code) == ("bad_text", "bad_text")
    assert (nowhere.code, nowhere.status) == ("no_such_channel", 404)
    assert voice.code == "not_postable" and f"<#{VOICE}>" in voice.message
    assert await rules.rows_for_guild(db, GUILD) == [] and await kinds(db) == []


async def test_a_website_save_leaves_one_row_under_the_web_head(bot, desk, db):
    await desk.save(bot.guild, RUNS, WORDS, STAFFER, via="website")

    assert (await kinds(db))[0] == "web.sticky.set"


async def test_the_test_mode_guard_refuses_and_says_so_once(bot, desk, clock, db):
    bot.guard = FakeGuard(LOG)
    await bot.store.set(GUILD, "sticky_mode", "on")

    outcome = await desk.save(bot.guild, RUNS, WORDS, STAFFER)
    clock.tick(600)
    await talk(desk, bot, 10)

    assert outcome.message == rules.SAVED_TEST_MODE
    assert channel(bot).messages == []
    assert await desk.place(bot.guild, RUNS) == TEST_MODE
    assert (await kinds(db)) == ["sticky.set", "sticky.would_post"]
    assert (await row_of(bot))["trouble"] is None


async def test_settle_moves_every_copy_to_where_the_mode_says(bot, desk, db):
    await desk.save(bot.guild, RUNS, WORDS, STAFFER)
    rehearsal = channel(bot, HOME).messages[0].id

    await bot.store.set(GUILD, "sticky_mode", "on")
    await desk.settle(bot.guild)
    await desk.settle(bot.guild)

    assert channel(bot, HOME).messages == [] and channel(bot, HOME).deleted == [rehearsal]
    assert len(channel(bot).messages) == 1

    await bot.store.set(GUILD, "sticky_mode", "off")
    await desk.settle(bot.guild)

    assert channel(bot).messages == []
    row = await row_of(bot)
    assert row["message_id"] is None and rules.state_of(row, "off") == rules.OFF
    await talk(desk, bot, 20)
    assert channel(bot).messages == []

    await bot.store.set(GUILD, "sticky_mode", "shadow")
    await desk.settle(bot.guild)
    assert len(channel(bot, HOME).messages) == 1 and channel(bot).messages == []


async def test_set_mode_logs_the_change_and_refuses_a_word_that_is_not_a_mode(bot, desk, db):
    done = await desk.set_mode(bot.guild, "on", STAFFER)
    bad = await desk.set_mode(bot.guild, "loud", STAFFER)

    assert done.ok and bot.store.get(GUILD, "sticky_mode") == "on"
    assert not bad.ok and bad.code == "bad_mode"
    assert await kinds(db) == ["sticky.mode"]


async def test_a_place_reports_what_it_did(bot, desk, clock):
    assert await desk.place(bot.guild, RUNS) == NOT_RUNNING
    await desk.save(bot.guild, RUNS, WORDS, STAFFER)
    clock.tick(600)
    assert await desk.place(bot.guild, RUNS) == REHEARSED
    await bot.store.set(GUILD, "sticky_mode", "on")
    clock.tick(600)
    assert await desk.place(bot.guild, RUNS) == POSTED


def test_the_desk_is_one_per_bot():
    bot = SimpleNamespace()
    assert desk_of(bot) is desk_of(bot)


def test_missing_permissions_names_them_and_trusts_what_it_cannot_ask():
    guild = SimpleNamespace(me=SimpleNamespace(id=BOT_ID))
    blind = FakeChannel(1)
    blind.perms = SimpleNamespace(view_channel=False, send_messages=False)

    assert missing_permissions(guild, blind) == ["View Channel", "Send Messages"]
    assert missing_permissions(guild, FakeChannel(2)) == []
    assert missing_permissions(SimpleNamespace(), blind) == []
