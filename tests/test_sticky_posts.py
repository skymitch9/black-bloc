import asyncio
import json
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
    OWN_HOME,
    POSTED,
    REHEARSED,
    TEST_MODE,
    TOO_SOON,
    UNREACHABLE,
    Desk,
    desk_of,
    missing_permissions,
    passing,
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
        self.edits = []

    async def edit(self, **kwargs):
        self.edits.append(kwargs)

    async def pin(self, reason=None):
        if self.channel.pin_raises is not None:
            raise self.channel.pin_raises
        self.channel.pinned.append(self.id)

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
        self.pin_raises = None
        self.pinned = []
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

    async def fetch_message(self, message_id):
        found = next((one for one in self.messages if one.id == int(message_id)), None)
        if found is None:
            raise discord.NotFound(_Response(404), "Unknown Message")
        return found


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
    return await make_bot(db)


async def make_bot(db):
    store = SettingsStore(db, load_settings(_env_file=None))
    await store.load()
    guild = FakeGuild()
    for channel in guild.channels.values():
        channel.guild = guild
    await store.set(GUILD, "shadow_channel_id", HOME)
    await store.set(GUILD, "sticky_quiet_seconds", 0)
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


def unavailable():
    return discord.DiscordServerError(_Response(503), "upstream connect error")


async def details_of(db, kind):
    cur = await db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id", (kind,)
    )
    return [json.loads(row["details"]) for row in await cur.fetchall()]


def link_to(channel_id, message_id):
    return f"https://discord.com/channels/{GUILD}/{channel_id}/{message_id}"


@pytest.mark.parametrize("mode", ["off", "shadow"])
async def test_a_stopped_stickys_copy_comes_down_when_the_mode_leaves_on(bot, desk, clock, mode):
    await live(bot, desk)
    first = channel(bot).messages[0].id
    channel(bot).perms.send_messages = False
    clock.tick(600)
    await talk(desk, bot, 5)
    assert (await row_of(bot))["trouble"] and [one.id for one in channel(bot).messages] == [first]

    await bot.store.set(GUILD, "sticky_mode", mode)
    await desk.settle(bot.guild)

    assert channel(bot).messages == [] and channel(bot).deleted == [first]
    row = await row_of(bot)
    assert row["message_id"] is None and row["trouble"]
    assert channel(bot, HOME).messages == []


@pytest.mark.parametrize("mode", ["off", "shadow", "on"])
async def test_a_paused_sticky_whose_copy_would_not_delete_loses_it_at_the_next_settle(
    bot, desk, mode
):
    await live(bot, desk)
    channel(bot).delete_raises = forbidden()
    await desk.pause(bot.guild, RUNS, STAFFER)
    assert len(channel(bot).messages) == 1
    channel(bot).delete_raises = None

    await bot.store.set(GUILD, "sticky_mode", mode)
    await desk.settle(bot.guild)

    assert channel(bot).messages == []
    row = await row_of(bot)
    assert row["message_id"] is None and row["paused"]
    assert channel(bot, HOME).messages == []


@pytest.mark.parametrize("outage", [unavailable, TimeoutError, ConnectionResetError])
async def test_an_outage_leaves_it_running_says_so_once_and_the_next_message_retries(
    bot, desk, clock, db, outage
):
    await live(bot, desk)
    channel(bot).send_raises = outage()
    clock.tick(600)

    await talk(desk, bot, 5)

    row = await row_of(bot)
    assert row["trouble"] is None and rules.is_running(row)
    assert rules.state_of(row, "on") == rules.WAITING
    assert RUNS in desk.watched and channel(bot).messages == []

    clock.tick(600)
    await talk(desk, bot, 1)
    clock.tick(600)
    assert await desk.place(bot.guild, RUNS) == UNREACHABLE

    said = await details_of(db, "sticky.post_failed")
    assert len(said) == 1 and said[0]["retrying"] is True
    assert "could not be reached" in said[0]["reason"]
    assert "refused" not in said[0]["reason"] and "ermission" not in said[0]["reason"]

    channel(bot).send_raises = None
    clock.tick(600)
    await talk(desk, bot, 1)

    assert len(channel(bot).messages) == 1
    assert (await row_of(bot))["message_id"] == channel(bot).messages[0].id
    assert desk.outage == {} and desk.tried == {}


async def test_an_outage_is_retried_no_sooner_than_the_gap(bot, desk, clock):
    await live(bot, desk)
    channel(bot).send_raises = unavailable()
    clock.tick(600)
    await talk(desk, bot, 5)
    channel(bot).send_raises = None
    clock.gate = asyncio.Event()

    await talk(desk, bot, 3)

    assert channel(bot).messages == [] and list(desk.waiting) == [RUNS]
    clock.gate.set()
    await desk.waiting[RUNS]
    assert clock.slept == [30.0] and len(channel(bot).messages) == 1


async def test_a_copy_that_times_out_on_delete_is_kept_on_the_row_and_tried_again(
    bot, desk, clock, db
):
    await live(bot, desk)
    first = channel(bot).messages[0].id
    channel(bot).delete_raises = TimeoutError()
    clock.tick(600)

    await talk(desk, bot, 5)

    row = await row_of(bot)
    assert row["trouble"] is None and row["message_id"] == first
    assert [one.id for one in channel(bot).messages] == [first]

    channel(bot).delete_raises = None
    clock.tick(600)
    await talk(desk, bot, 1)

    assert channel(bot).deleted == [first] and len(channel(bot).messages) == 1


@pytest.mark.parametrize(
    ("raised", "said"),
    [
        (forbidden, "Discord refused (403): Missing Permissions"),
        (lambda: RuntimeError(""), "RuntimeError"),
        (lambda: RuntimeError("no"), "RuntimeError: no"),
    ],
)
async def test_an_old_copy_that_will_not_delete_says_one_sentence_not_two(
    bot, desk, clock, raised, said
):
    await live(bot, desk)
    channel(bot).delete_raises = raised()
    clock.tick(600)

    await talk(desk, bot, 5)

    trouble = (await row_of(bot))["trouble"]
    assert "It could not be posted" not in trouble and trouble.count("Try again") == 1
    assert trouble == rules.TROUBLE_OLD_COPY.format(reason=said)
    assert ": ." not in trouble and ". —" not in trouble


async def test_a_sticky_stopped_for_a_missing_home_comes_back_when_one_is_set(bot, desk, db):
    del bot.guild.channels[HOME]
    await desk.save(bot.guild, RUNS, WORDS, STAFFER)
    await desk.save(bot.guild, LOG, WORDS, STAFFER)
    assert (await row_of(bot))["trouble"] == rules.TROUBLE_HOME_GONE.format(home=HOME)

    await bot.store.set(GUILD, "sticky_shadow_channel_id", OTHER_HOME)
    await desk.settle(bot.guild)

    for channel_id in (RUNS, LOG):
        row = await row_of(bot, channel_id)
        assert row["trouble"] is None and row["posted_channel_id"] == OTHER_HOME
        assert channel_id in desk.watched
    assert len(channel(bot, OTHER_HOME).messages) == 2


async def test_a_sticky_stopped_for_no_home_at_all_comes_back_too_and_no_other_stop_does(
    bot, desk, clock
):
    await bot.store.clear(GUILD, "shadow_channel_id")
    await desk.save(bot.guild, RUNS, WORDS, STAFFER)
    assert (await row_of(bot))["trouble"] == rules.TROUBLE_NO_HOME
    await rules.write_words(bot.db, GUILD, LOG, WORDS, STAFFER)
    refused = rules.TROUBLE_REFUSED.format(status=403, text="no")
    await rules.write_trouble(bot.db, GUILD, LOG, refused)

    await bot.store.set(GUILD, "shadow_channel_id", HOME)
    await desk.settle(bot.guild)

    assert (await row_of(bot))["trouble"] is None
    assert len(channel(bot, HOME).messages) == 1
    assert (await row_of(bot, LOG))["trouble"]


async def test_pause_says_the_copy_is_still_up_when_discord_would_not_delete_it(bot, desk, db):
    await live(bot, desk)
    first = channel(bot).messages[0].id
    channel(bot).delete_raises = forbidden()

    outcome = await desk.pause(bot.guild, RUNS, STAFFER)

    assert outcome.ok and len(channel(bot).messages) == 1
    assert "was taken down" not in outcome.message
    assert "still in" in outcome.message and f"<#{RUNS}>" in outcome.message
    assert "Discord refused (403)" in outcome.message
    assert link_to(RUNS, first) in outcome.message
    row = await row_of(bot)
    assert row["paused"] and row["message_id"] == first
    said = (await details_of(db, "sticky.paused"))[0]
    assert (said["left_channel_id"], said["left_message_id"]) == (RUNS, first)


async def test_remove_names_the_copy_it_could_not_delete_with_a_link(bot, desk, db):
    await live(bot, desk)
    first = channel(bot).messages[0].id
    channel(bot).delete_raises = forbidden()

    outcome = await desk.remove(bot.guild, RUNS, STAFFER)

    assert outcome.ok and len(channel(bot).messages) == 1
    assert outcome.message != rules.REMOVED_NOW.format(channel_id=RUNS)
    assert link_to(RUNS, first) in outcome.message and "still in" in outcome.message
    assert await row_of(bot) is None
    said = (await details_of(db, "sticky.removed"))[0]
    assert (said["left_channel_id"], said["left_message_id"]) == (RUNS, first)
    assert "Discord refused (403)" in said["copy_left"]


async def test_a_pause_in_shadow_names_the_rehearsal_home_the_copy_was_in(bot, desk):
    await desk.save(bot.guild, RUNS, WORDS, STAFFER)

    outcome = await desk.pause(bot.guild, RUNS, STAFFER)

    assert f"<#{HOME}>" in outcome.message and f"<#{RUNS}>" not in outcome.message
    assert outcome.message == rules.PAUSED_NOW.format(where=HOME)
    assert channel(bot, HOME).messages == []


async def test_a_pause_with_no_copy_up_does_not_claim_to_have_taken_one_down(bot, desk):
    await bot.store.set(GUILD, "sticky_mode", "off")
    await desk.save(bot.guild, RUNS, WORDS, STAFFER)

    outcome = await desk.pause(bot.guild, RUNS, STAFFER)

    assert "taken down" not in outcome.message
    assert outcome.message == rules.PAUSED_NO_COPY


async def test_a_rehearsal_home_that_is_the_stickys_own_channel_gets_no_copy_in_shadow(
    bot, desk, clock, db
):
    await bot.store.set(GUILD, "sticky_shadow_channel_id", RUNS)

    outcome = await desk.save(bot.guild, RUNS, WORDS, STAFFER)
    clock.tick(600)
    await talk(desk, bot, 10)

    assert channel(bot).messages == []
    row = await row_of(bot)
    assert row["trouble"] is None and row["message_id"] is None
    assert rules.state_of(row, "shadow") == rules.WAITING
    assert outcome.ok and "rehearsal home itself" in outcome.message
    assert "rehearsal copy is in" not in outcome.message
    assert outcome.message == rules.SAVED_OWN_HOME.format(channel_id=RUNS)
    said = await details_of(db, "sticky.would_post")
    assert [(one["channel_id"], one["reason"]) for one in said] == [(RUNS, OWN_HOME)]


async def test_a_live_copy_comes_down_when_shadow_makes_its_own_channel_the_home(bot, desk):
    await live(bot, desk)
    await bot.store.set(GUILD, "sticky_shadow_channel_id", RUNS)
    await bot.store.set(GUILD, "sticky_mode", "shadow")

    await desk.settle(bot.guild)
    await desk.settle(bot.guild)

    assert channel(bot).messages == []
    assert (await row_of(bot))["message_id"] is None


async def test_a_copy_sent_but_not_stored_is_deleted_so_the_next_one_is_the_only_one(
    bot, desk, clock, monkeypatch
):
    await live(bot, desk)
    first = channel(bot).messages[0].id
    clock.tick(600)
    stored = rules.write_copy

    async def failing(db, guild_id, channel_id, message_id, posted_in, **kwargs):
        if message_id:
            raise RuntimeError("database is locked")
        await stored(db, guild_id, channel_id, message_id, posted_in, **kwargs)

    monkeypatch.setattr(rules, "write_copy", failing)
    with pytest.raises(RuntimeError):
        await desk.place(bot.guild, RUNS)

    assert channel(bot).messages == []
    assert (await row_of(bot))["message_id"] is None

    monkeypatch.setattr(rules, "write_copy", stored)
    assert await desk.place(bot.guild, RUNS) == POSTED
    assert len(channel(bot).messages) == 1 and first in channel(bot).deleted
    assert (await row_of(bot))["message_id"] == channel(bot).messages[0].id


async def test_a_long_rehearsal_note_is_cut_and_the_staff_words_never_are(bot, desk):
    words = "w" * rules.TEXT_MAX
    await bot.store.set(GUILD, "rehearsal_note", "N" * 380 + " {channel}")

    await desk.save(bot.guild, RUNS, words, STAFFER)

    copy = channel(bot, HOME).messages[0]
    assert len(copy.content) <= 2000
    assert rules.DISCORD_LIMIT == 2000
    assert copy.content.endswith("\n" + words)
    assert copy.content.startswith("NNN") and copy.content.split("\n")[0].endswith(rules.CUT)
    assert (await row_of(bot))["trouble"] is None


async def test_six_messages_at_once_make_one_tracked_timer(bot, desk, clock):
    await live(bot, desk)
    clock.tick(10)
    clock.gate = asyncio.Event()
    await talk(desk, bot, 4)

    await asyncio.gather(*(desk.on_message(person(channel(bot))) for _ in range(6)))

    timers = [one for one in asyncio.all_tasks() if one.get_name() == f"sticky-{RUNS}"]
    assert len(timers) == 1 and desk.waiting == {RUNS: timers[0]}
    desk.close()
    await asyncio.gather(*timers, return_exceptions=True)
    assert all(one.cancelled() for one in timers)


@pytest.mark.parametrize("given", [["a", "b"], {"a": 1}, 7, True])
async def test_words_that_are_not_a_string_are_refused_in_words(bot, desk, db, given):
    outcome = await desk.save(bot.guild, RUNS, given, STAFFER)

    assert (outcome.ok, outcome.code, outcome.status) == (False, "bad_text", 400)
    assert outcome.message == rules.NOT_WORDS
    assert await rules.rows_for_guild(db, GUILD) == []


def test_only_an_outage_that_passes_by_itself_is_retried():
    assert passing(unavailable()) and passing(TimeoutError()) and passing(ConnectionError())
    assert passing(discord.HTTPException(_Response(429), "slow down"))
    for status in (400, 403, 404):
        assert not passing(discord.HTTPException(_Response(status), "no"))
    assert not passing(forbidden()) and not passing(ValueError("no"))


# --- a post as the sticky ---------------------------------------------------------------------


async def a_post(bot, slug="leaderboard", *, body="", style="embed", blocks=("leaderboard",)):
    from black_bloc import post_blocks, posts

    post_id = await posts.create_post(
        bot.db, GUILD, slug=slug, title=slug.title(), body=body, style=style, pin=False
    )
    row = await posts.get_post_by_id(bot.db, post_id)
    for kind in blocks:
        await post_blocks.attach(bot.db, row, kind)
    return post_id


async def post_row(bot, post_id):
    from black_bloc import posts

    return await posts.get_post_by_id(bot.db, post_id)


async def points_on(bot):
    await bot.store.set(GUILD, "points_mode", "on")


async def test_a_post_sticky_posts_the_post_pins_it_and_both_rows_know_the_copy(bot, desk, db):
    await points_on(bot)
    post_id = await a_post(bot)

    outcome = await desk.save(bot.guild, RUNS, None, STAFFER, post="leaderboard")

    assert outcome.ok, outcome.message
    copy = channel(bot).messages[0]
    assert copy.content is None
    assert [embed.title for embed in copy.kwargs["embeds"]] == ["Leaderboard"]
    assert copy.kwargs["embeds"][0].description == "No runs have been approved yet."
    assert copy.kwargs["allowed_mentions"].roles is False
    assert channel(bot).pinned == [copy.id]
    row = await row_of(bot)
    assert (row["post_id"], row["message_id"], row["posted_channel_id"]) == (
        post_id,
        copy.id,
        RUNS,
    )
    post = await post_row(bot, post_id)
    assert (post["message_id"], post["channel_id"], post["shadow_message_id"]) == (
        copy.id,
        RUNS,
        None,
    )
    assert await kinds(db) == ["sticky.set", "sticky.posted"]
    assert rules.words_of(row) == "The post **Leaderboard**"


async def test_the_next_move_deletes_and_so_unpins_the_old_copy_first(bot, desk, clock):
    await points_on(bot)
    post_id = await a_post(bot)
    await desk.save(bot.guild, RUNS, None, STAFFER, post=post_id)
    first = channel(bot).messages[0].id
    await bot.store.set(GUILD, "sticky_quiet_seconds", 0)
    clock.tick(600)

    await talk(desk, bot, 5)

    now = channel(bot).messages[0].id
    assert channel(bot).deleted == [first] and len(channel(bot).messages) == 1
    assert channel(bot).pinned == [first, now]
    assert (await post_row(bot, post_id))["message_id"] == now


async def test_a_pin_that_fails_leaves_the_copy_and_is_said_once(bot, desk, db, clock):
    await points_on(bot)
    await a_post(bot)
    channel(bot).pin_raises = forbidden()

    await desk.save(bot.guild, RUNS, None, STAFFER, post="leaderboard")
    await bot.store.set(GUILD, "sticky_quiet_seconds", 0)
    clock.tick(600)
    await talk(desk, bot, 5)

    assert len(channel(bot).messages) == 1 and (await row_of(bot))["trouble"] is None
    assert (await row_of(bot))["reposts"] == 1
    assert (await kinds(db)).count("sticky.pin_failed") == 1


async def test_sticky_pin_copies_off_pins_nothing(bot, desk):
    await bot.store.set(GUILD, "sticky_pin_copies", False)
    await live(bot, desk)

    assert channel(bot).messages and channel(bot).pinned == []


async def test_a_text_sticky_is_pinned_too(bot, desk):
    await live(bot, desk)

    assert channel(bot).pinned == [channel(bot).messages[0].id]


async def test_the_points_mode_decides_where_the_leaderboard_goes_not_the_sticky_mode(bot, desk):
    await bot.store.set(GUILD, "points_shadow_channel_id", OTHER_HOME)
    post_id = await a_post(bot)

    await desk.save(bot.guild, RUNS, None, STAFFER, post=post_id)

    copy = channel(bot, OTHER_HOME).messages[0]
    assert channel(bot).messages == [] and channel(bot, HOME).messages == []
    assert copy.content == f"Rehearsal — this is where it would go: <#{RUNS}>"
    post = await post_row(bot, post_id)
    assert (post["message_id"], post["shadow_message_id"]) == (None, copy.id)

    await bot.store.set(GUILD, "points_mode", "on")
    await desk.settle(bot.guild)

    assert channel(bot, OTHER_HOME).messages == [] and len(channel(bot).messages) == 1
    post = await post_row(bot, post_id)
    assert (post["message_id"], post["shadow_message_id"]) == (channel(bot).messages[0].id, None)


async def test_points_off_or_sticky_off_takes_the_leaderboard_down(bot, desk):
    await points_on(bot)
    await a_post(bot)
    await desk.save(bot.guild, RUNS, None, STAFFER, post="leaderboard")

    await bot.store.set(GUILD, "points_mode", "off")
    await desk.settle(bot.guild)
    assert channel(bot).messages == []

    await points_on(bot)
    await desk.settle(bot.guild)
    assert len(channel(bot).messages) == 1

    await bot.store.set(GUILD, "sticky_mode", "off")
    await desk.settle(bot.guild)
    assert channel(bot).messages == []


async def test_a_post_without_an_owner_follows_the_sticky_mode(bot, desk):
    await a_post(bot, "rules", body="Be kind.", style="plain", blocks=())

    await desk.save(bot.guild, RUNS, None, STAFFER, post="rules")

    copy = channel(bot, HOME).messages[0]
    assert copy.content == f"Rehearsal — this is where it would go: <#{RUNS}>\nBe kind."


async def test_a_deleted_post_stops_the_sticky_in_words(bot, desk):
    from black_bloc import posts

    await points_on(bot)
    post_id = await a_post(bot)
    await desk.save(bot.guild, RUNS, None, STAFFER, post=post_id)
    await desk.pause(bot.guild, RUNS, STAFFER)
    await posts.delete_post(bot.db, post_id)

    outcome = await desk.resume(bot.guild, RUNS, STAFFER)

    assert rules.TROUBLE_POST_GONE in outcome.message
    assert (await row_of(bot))["trouble"] == rules.TROUBLE_POST_GONE


async def test_a_post_is_refused_in_words_when_it_cannot_be_a_sticky(bot, desk):
    from black_bloc import posts

    await a_post(bot, "empty", blocks=())
    door = await a_post(bot, "door", body="Hi", blocks=("frontdoor",))
    up = await a_post(bot, "up", body="Hi", blocks=())
    await posts.set_posted(bot.db, up, 77, "hash")
    await points_on(bot)
    await a_post(bot)
    await desk.save(bot.guild, OTHER_HOME, None, STAFFER, post="leaderboard")

    found = {
        wanted: (await desk.save(bot.guild, RUNS, None, STAFFER, post=wanted)).code
        for wanted in ("nothing", "empty", door, "up", "leaderboard")
    }

    assert found == {
        "nothing": "no_such_post",
        "empty": "post_is_empty",
        door: "post_carries_door",
        "up": "post_is_posted",
        "leaderboard": "post_is_a_sticky",
    }
    assert await row_of(bot) is None


async def test_the_posts_pages_update_reposts_and_take_down_pauses(bot, desk):
    from black_bloc import posts

    await points_on(bot)
    post_id = await a_post(bot)
    bot.sticky_desk = desk
    await desk.save(bot.guild, RUNS, None, STAFFER, post=post_id)
    first = channel(bot).messages[0].id

    updated = await posts.publish_post(bot, bot.guild, await post_row(bot, post_id), STAFFER)

    assert updated.ok and int(updated.value["id"]) == post_id
    assert channel(bot).deleted == [first] and len(channel(bot).messages) == 1

    taken = await posts.take_down_post(bot, bot.guild, await post_row(bot, post_id), STAFFER)

    assert taken.ok and channel(bot).messages == []
    assert (await row_of(bot))["paused"] == 1
    assert not posts.is_posted(await post_row(bot, post_id))


async def test_a_board_change_edits_the_sticky_copy_in_place(bot, desk):
    from black_bloc import post_blocks

    await points_on(bot)
    post_id = await a_post(bot)
    await desk.save(bot.guild, RUNS, None, STAFFER, post=post_id)
    copy = channel(bot).messages[0]
    await bot.store.set(GUILD, "points_board_empty", "Be the first.")

    drew = await post_blocks.redraw_post(bot, bot.guild, await post_row(bot, post_id))

    assert drew is True
    assert copy.edits[-1]["embeds"][0].description == "Be the first."
    assert copy.edits[-1]["content"] is None and len(channel(bot).messages) == 1


# --- the quieter move: the count, then quiet, never past the ceiling --------------------------


def chatty(bot, clock, talks):
    """A desk whose sleeps let people keep talking: `talks` sleeps each end with one message."""
    left = {"talks": talks}
    holder = {}

    async def sleep(seconds):
        clock.slept.append(seconds)
        if left["talks"] > 0:
            left["talks"] -= 1
            clock.tick(seconds - 10)
            await holder["desk"].on_message(person(channel(bot)))
            clock.tick(10)
            return
        clock.tick(seconds)

    holder["desk"] = Desk(bot, now=clock.now, sleep=sleep)
    return holder["desk"]


async def quiet_rule(bot, quiet=300, ceiling=60):
    await bot.store.set(GUILD, "sticky_quiet_seconds", quiet)
    await bot.store.set(GUILD, "sticky_max_buried_minutes", ceiling)


async def settled_timer(desk):
    await desk.waiting[RUNS]


async def test_the_count_then_five_quiet_minutes_moves_it_once(bot, clock):
    desk = chatty(bot, clock, 0)
    await quiet_rule(bot)
    await live(bot, desk)
    clock.tick(600)

    await talk(desk, bot, 5)
    assert len(channel(bot).messages) == 1 and list(desk.waiting) == [RUNS]
    await settled_timer(desk)

    assert clock.slept == [300.0]
    assert len(channel(bot).messages) == 1 and channel(bot).deleted
    assert (await row_of(bot))["reposts"] == 1


async def test_talk_while_waiting_pushes_the_move_back_on_the_same_timer(bot, clock):
    desk = chatty(bot, clock, 1)
    await quiet_rule(bot)
    await live(bot, desk)
    clock.tick(600)

    await talk(desk, bot, 5)
    timer = desk.waiting[RUNS]
    await settled_timer(desk)

    assert clock.slept == [300.0, 290.0]
    assert timer.done() and desk.waiting == {}
    assert (await row_of(bot))["reposts"] == 1


async def test_the_ceiling_moves_it_an_hour_after_the_count_however_busy(bot, clock):
    desk = chatty(bot, clock, 1000)
    await quiet_rule(bot)
    await live(bot, desk)
    clock.tick(600)

    await talk(desk, bot, 5)
    await settled_timer(desk)

    assert sum(clock.slept) == pytest.approx(3600.0)
    assert (await row_of(bot))["reposts"] == 1


async def test_no_ceiling_waits_for_quiet_however_long(bot, clock):
    desk = chatty(bot, clock, 30)
    await quiet_rule(bot, ceiling=0)
    await live(bot, desk)
    clock.tick(600)

    await talk(desk, bot, 5)
    await settled_timer(desk)

    assert sum(clock.slept) > 7200
    assert (await row_of(bot))["reposts"] == 1


async def test_the_gap_since_the_last_copy_is_still_the_floor(bot, clock):
    desk = chatty(bot, clock, 0)
    await quiet_rule(bot, quiet=10)
    await bot.store.set(GUILD, "sticky_min_seconds", 600)
    await live(bot, desk)
    clock.tick(5)

    await talk(desk, bot, 5)
    await settled_timer(desk)

    assert clock.slept == [595.0]


async def test_quiet_zero_is_the_old_rule_and_moves_at_the_count(bot, clock):
    desk = chatty(bot, clock, 0)
    await quiet_rule(bot, quiet=0)
    await live(bot, desk)
    clock.tick(600)

    await talk(desk, bot, 5)

    assert clock.slept == [] and (await row_of(bot))["reposts"] == 1


# --- Post to test on a sticky's post (post-to-test-design.md) ---------------------------------


async def test_a_rehearsing_sticky_answers_that_it_already_rehearses_and_sends_nothing(bot, desk):
    from black_bloc import posts

    await bot.store.set(GUILD, posts.MODE_KEY, posts.ON)
    post_id = await a_post(bot)
    bot.sticky_desk = desk
    await desk.save(bot.guild, RUNS, None, STAFFER, post=post_id)
    before = await post_row(bot, post_id)
    assert len(channel(bot, HOME).messages) == 1, "the leaderboard rehearses in the home"

    found = await posts.rehearse_post(bot, bot.guild, before, STAFFER)

    assert found.ok
    assert found.message == posts.STICKY_ALREADY_REHEARSING.format(shadow="#welcome-test")
    assert len(channel(bot, HOME).messages) == 1 and channel(bot, HOME).messages[0].edits == []
    assert dict(await post_row(bot, post_id)) == dict(before)


async def test_a_live_stickys_test_copy_is_one_plain_message_the_desk_never_counts(
    bot, desk, db, clock
):
    from black_bloc import posts

    await bot.store.set(GUILD, posts.MODE_KEY, posts.ON)
    await points_on(bot)
    post_id = await a_post(bot)
    bot.sticky_desk = desk
    await desk.save(bot.guild, RUNS, None, STAFFER, post=post_id)
    real = channel(bot).messages[0].id
    sticky_before = dict(await row_of(bot))
    stamped = ("message_id", "posted_hash", "posted_at", "posted_by")
    was = await post_row(bot, post_id)
    stamp_before = tuple(was[key] for key in stamped)

    found = await posts.rehearse_post(bot, bot.guild, await post_row(bot, post_id), STAFFER)

    assert found.ok, found.message
    home = channel(bot, HOME)
    assert len(home.messages) == 1 and home.pinned == []
    copy = home.messages[0]
    assert copy.content == f"Rehearsal — this is where it would go: <#{RUNS}>"
    assert [embed.title for embed in copy.kwargs["embeds"]] == ["Leaderboard"]
    assert [one.id for one in channel(bot).messages] == [real], "the sticky copy is untouched"
    assert dict(await row_of(bot)) == sticky_before, "the Desk's row never learns of it"
    post = await post_row(bot, post_id)
    assert post["shadow_message_id"] == copy.id
    assert tuple(post[key] for key in stamped) == stamp_before

    clock.tick(600)
    await talk(desk, bot, 5)

    assert home.messages == [] and home.deleted == [copy.id], "a real copy takes it down"
    post = await post_row(bot, post_id)
    assert post["shadow_message_id"] is None
    assert post["message_id"] == channel(bot).messages[0].id != real
    assert "post.shadow_taken_down" in await kinds(db)


async def test_taking_a_live_stickys_post_down_takes_its_test_copy_too(bot, desk):
    from black_bloc import posts

    await bot.store.set(GUILD, posts.MODE_KEY, posts.ON)
    await points_on(bot)
    post_id = await a_post(bot)
    bot.sticky_desk = desk
    await desk.save(bot.guild, RUNS, None, STAFFER, post=post_id)
    await posts.rehearse_post(bot, bot.guild, await post_row(bot, post_id), STAFFER)

    taken = await posts.take_down_post(bot, bot.guild, await post_row(bot, post_id), STAFFER)

    assert taken.ok
    assert channel(bot, HOME).messages == [] and channel(bot).messages == []
    assert not posts.is_posted(await post_row(bot, post_id))
