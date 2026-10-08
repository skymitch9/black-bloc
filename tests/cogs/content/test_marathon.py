import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import discord
import pytest

from black_bloc import logkinds
from black_bloc import marathon as mt
from black_bloc.cogs.content import marathon as cogmod
from black_bloc.cogs.content.marathon import (
    Marathons,
    change_link,
    claim_notice,
    create_marathon,
    get_marathon,
    mark_done,
    pair_runner,
    post_board,
    refresh_marathon,
    rename_marathon,
    runs_of,
    set_active,
    set_channel,
    shout_now,
    unpair_runner,
    update_run,
)
from black_bloc.cogs.content.marathon_archive import archive_marathon
from black_bloc.cogs.content.spotlight import (
    delete_channel,
    set_ping_mode,
    spotlight_channel,
    start_session,
    windows_for,
)
from black_bloc.config import load_settings
from black_bloc.golive import StreamInfo
from black_bloc.marathon_sources import Person, Run, ScheduleError
from black_bloc.settings_store import SettingsStore
from tests.cogs.content.test_spotlight import (
    CHANNEL,
    GUILD,
    LOG_CHANNEL,
    SHADOW_CHANNEL,
    FakeActor,
    FakeBot,
    FakeChannel,
    FakeGuild,
    FakeInteraction,
    details_of,
    kinds,
)

NOW = datetime(2027, 1, 4, 18, 0, tzinfo=UTC)
URL = "https://gamesdonequick.com/schedule/74"
SKY = 9001
FAN_ROLE = 5001
CHANNEL_ROLE = 5002
GOLIVE_ROLE = 5003


def at(minutes):
    return (NOW + timedelta(minutes=minutes)).isoformat()


def a_run(ident, start, *, game=None, people=(("Somebody", None, "runner"),), length=60):
    return Run(
        str(ident),
        ident,
        game or f"Game {ident}",
        game or f"Game {ident}",
        "Any%",
        at(start),
        at(start + length),
        length * 60,
        tuple(Person(*one) for one in people),
    )


SCHEDULE = [
    a_run(1, -120),
    a_run(2, -60, game="Celeste"),
    a_run(3, 30, game="Super Metroid", people=(("Sky", "skyruns", "runner"),)),
    a_run(4, 90, game="Kirby Air Riders"),
    a_run(5, 150, game="Blaster Master", people=(("Interview Crew", None, "host"),)),
]


class FakeThread(FakeChannel):
    def __init__(self, thread_id, parent, name, kwargs):
        super().__init__(thread_id)
        self.parent = parent
        self.parent_id = parent.id
        self.name = name
        self.kwargs = kwargs
        self.archived = False
        self.thread_edits = []

    async def edit(self, **kwargs):
        self.thread_edits.append(kwargs)
        if "archived" in kwargs:
            self.archived = bool(kwargs["archived"])


class ThreadParent(FakeChannel):
    """A text channel that takes threads; each thread joins the guild's channels."""

    made = 700000

    def __init__(self, channel_id, guild):
        super().__init__(channel_id)
        self.guild = guild
        self.threads = []
        self.create_raises = None

    async def create_thread(self, *, name, **kwargs):
        if self.create_raises is not None:
            raise self.create_raises
        ThreadParent.made += 1
        thread = FakeThread(ThreadParent.made, self, name, kwargs)
        self.threads.append(thread)
        self.guild.channels[thread.id] = thread
        return thread


def threading(bot, channel_id):
    made = ThreadParent(channel_id, bot.guild)
    bot.guild.channels[channel_id] = made
    return made


def inbox_thread(bot, channel_id):
    found = bot.guild.channels[channel_id]
    return found.threads[0] if getattr(found, "threads", None) else None


def notices_in(bot, channel_id):
    """What went into the inbox thread besides its opening line and the marathons' own
    inbox messages (those carry an embed)."""
    thread = inbox_thread(bot, channel_id)
    return [one for one in thread.messages[1:] if not one.embeds] if thread is not None else []


def inbox_messages(bot, channel_id):
    thread = inbox_thread(bot, channel_id)
    return [one for one in thread.messages if one.embeds] if thread is not None else []


class FakeClient:
    def __init__(self, runs=None, raises=None):
        self.runs_given = list(runs if runs is not None else SCHEDULE)
        self.raises = raises
        self.calls = 0
        self.asked = []

    async def resolve(self, source, ref, **asked):
        self.asked.append(("resolve", source, asked))
        if self.raises is not None and not self.raises.unpublished:
            raise self.raises
        return ("74", "Awesome Games Done Quick 2027")

    async def runs(self, source, ref, **asked):
        self.asked.append(("runs", source, asked))
        self.calls += 1
        if self.raises is not None:
            raise self.raises
        return list(self.runs_given)

    async def close(self):
        return None


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=False)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOG_CHANNEL)
    await store.set(GUILD, "golive_channel_id", CHANNEL)
    await store.set(GUILD, "shadow_channel_id", SHADOW_CHANNEL)
    await store.set(GUILD, "golive_ping_role_id", GOLIVE_ROLE)
    await store.set(GUILD, "marathon_mode", "on")
    await store.set(GUILD, "marathon_event_mode_default", "none")
    await store.set(GUILD, "marathon_track_makes_thread", False)
    await store.set(GUILD, "spotlight_mode", "on")
    await db.conn.execute(
        "INSERT INTO golive_links(user_id, twitch_login, linked_at) VALUES (?, ?, ?)",
        (SKY, "skyruns", at(-9999)),
    )
    await db.conn.commit()
    made = FakeBot(db, store, settings, FakeGuild())
    made.guild.channels[SHADOW_CHANNEL] = ThreadParent(SHADOW_CHANNEL, made.guild)
    made.store.is_staff = lambda member: True

    async def fan_role(bot, guild, user_id, *, notice=True):
        return FAN_ROLE if int(user_id) == SKY else None

    async def channel_role(bot, guild, spotlight_id, *, notice=True):
        return CHANNEL_ROLE

    monkeypatch.setattr("black_bloc.pings.announced_fan_role", fan_role)
    monkeypatch.setattr("black_bloc.pings.announced_spotlight_fan_role", channel_role)
    return made


@pytest.fixture
def cog(bot):
    made = Marathons(bot)
    made.client = FakeClient()
    made.clock = lambda: NOW
    bot.cogs[cogmod.COG_NAME] = made
    return made


async def gdq_row(bot):
    outcome, row = await spotlight_channel(
        bot, bot.guild, FakeActor(), "gamesdonequick", keep=True, spotlight=True
    )
    assert outcome == "added"
    return row


async def added(bot, cog, *, channel=None):
    outcome = await create_marathon(
        bot,
        bot.guild,
        FakeActor(),
        name="AGDQ 2027",
        url=URL,
        spotlight_id=channel["id"] if channel is not None else None,
    )
    assert outcome.ok, outcome.message
    return await tracked(bot, outcome.value)


async def tracked(bot, marathon):
    """These tests are about what a TRACKED marathon posts, in the marathon channel as before
    (marathon_track_makes_thread off); the inbox and the threads are test_marathon_inbox.py's."""
    await bot.db.conn.execute(
        "UPDATE marathons SET tracked_at = ? WHERE id = ?", (at(-9999), marathon["id"])
    )
    await bot.db.conn.commit()
    return await get_marathon(bot.db, GUILD, marathon["id"])


async def runs_by_game(bot, marathon):
    return {row["game"]: row for row in await runs_of(bot.db, marathon["id"])}


def posts(bot, channel_id=CHANNEL):
    return bot.guild.channels[channel_id].messages


# --- reading --------------------------------------------------------------------------------


async def test_a_fetch_inserts_every_run_and_matches_ours_by_the_linked_login(bot, cog):
    marathon = await added(bot, cog)
    rows = await runs_by_game(bot, marathon)

    assert len(rows) == 5
    assert mt.member_ids(rows["Super Metroid"]) == [SKY]
    assert not mt.is_ours(rows["Celeste"])
    fresh = await get_marathon(bot.db, GUILD, marathon["id"])
    assert fresh["starts_at"] == at(-120) and fresh["ends_at"] == at(210)
    assert fresh["last_fetch_ok"] == 1 and fresh["fetch_failures"] == 0
    assert (await details_of(bot.db, "marathon.run_matched"))["member_id"] == SKY
    assert (await details_of(bot.db, "marathon.fetched"))["changed"] is True


async def test_a_refetch_is_a_diff_moved_runs_of_ours_are_important_and_missing_ones_drop(bot, cog):
    marathon = await added(bot, cog)
    cog.client.runs_given = [
        SCHEDULE[0],
        SCHEDULE[1],
        a_run(3, 70, game="Super Metroid", people=(("Sky", "skyruns", "runner"),)),
        SCHEDULE[3],
        a_run(6, 400, game="New Game"),
    ]
    await cog.refresh(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    rows = await runs_by_game(bot, marathon)

    assert rows["Super Metroid"]["scheduled_at"] == at(70)
    assert rows["Super Metroid"]["previous_scheduled_at"] == at(30)
    assert rows["Blaster Master"]["state"] == mt.DROPPED
    assert "New Game" in rows
    moved = await details_of(bot.db, "marathon.member_run_moved")
    assert moved["member_id"] == SKY and moved["from"] == at(30) and moved["to"] == at(70)
    changed = await details_of(bot.db, "marathon.schedule_changed")
    assert (changed["added"], changed["moved"], changed["dropped"]) == (1, 1, 1)


async def test_an_unchanged_fetch_touches_nothing_but_the_read_time(bot, cog):
    marathon = await added(bot, cog)
    await cog.refresh(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert (await details_of(bot.db, "marathon.fetched"))["changed"] is False
    assert (await kinds(bot.db)).count("marathon.schedule_changed") == 1


async def test_a_dropped_run_that_comes_back_is_upcoming_again(bot, cog):
    marathon = await added(bot, cog)
    cog.client.runs_given = SCHEDULE[:4]
    await cog.refresh(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    cog.client.runs_given = SCHEDULE
    await cog.refresh(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert (await runs_by_game(bot, marathon))["Blaster Master"]["state"] == mt.UPCOMING


async def test_a_failed_fetch_keeps_every_run_and_the_third_in_a_row_is_important(bot, cog):
    marathon = await added(bot, cog)
    cog.client.raises = ScheduleError("the GDQ tracker answered 503")
    for _ in range(3):
        read = await cog.refresh(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
        assert not read.ok and "503" in read.message
    fresh = await get_marathon(bot.db, GUILD, marathon["id"])

    assert len(await runs_of(bot.db, marathon["id"])) == 5
    assert fresh["fetch_failures"] == 3 and fresh["last_fetch_ok"] == 0
    assert "503" in fresh["last_error"]
    assert (await kinds(bot.db)).count("marathon.fetch_failed") == 3
    assert (await kinds(bot.db)).count("marathon.schedule_stale") == 1
    cog.client.raises = None
    await cog.refresh(bot.guild, fresh)
    assert (await get_marathon(bot.db, GUILD, marathon["id"]))["fetch_failures"] == 0


async def test_an_unpublished_schedule_is_kept_and_does_not_count_as_a_failure(bot, cog):
    cog.client.raises = ScheduleError("not published", unpublished=True)
    outcome = await create_marathon(bot, bot.guild, FakeActor(), name="AGDQ 2027", url=URL)
    assert outcome.ok
    fresh = outcome.value
    assert fresh["fetch_failures"] == 0 and fresh["last_error"] == "not published"
    assert (await details_of(bot.db, "marathon.fetch_failed"))["unpublished"] is True


async def test_a_staff_added_marathon_counts_as_noticed_and_never_gets_a_held_notice(
    bot, cog
):
    marathon = await added(bot, cog)
    assert marathon["noticed_at"] and marathon["feed_id"] is None
    await refresh_marathon(bot, bot.guild, marathon)
    assert "marathon.notice_posted" not in await kinds(bot.db)


async def test_claim_notice_is_taken_once(bot, cog):
    marathon = await added(bot, cog)
    await bot.db.conn.execute("UPDATE marathons SET noticed_at = NULL")
    assert await claim_notice(bot.db, marathon["id"]) is True
    assert await claim_notice(bot.db, marathon["id"]) is False
    assert (await get_marathon(bot.db, GUILD, marathon["id"]))["noticed_at"]


# --- the cadence ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("starts_in", "early", "due"),
    [
        (None, timedelta(minutes=10), timedelta(minutes=31)),
        (60 * 24 * 40, timedelta(hours=5), timedelta(hours=25)),
    ],
    ids=["near-poll-gap", "far-gap"],
)
async def test_a_marathon_is_read_again_only_once_its_gap_is_up(bot, cog, starts_in, early, due):
    if starts_in is not None:
        cog.client.runs_given = [a_run(1, starts_in)]
    marathon = await added(bot, cog)
    calls = cog.client.calls
    cog.clock = lambda: NOW + early
    await cog.tick_marathon(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert cog.client.calls == calls
    cog.clock = lambda: NOW + due
    await cog.tick_marathon(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert cog.client.calls == calls + 1


# --- the board ------------------------------------------------------------------------------


async def test_with_runner_posts_off_the_board_lists_every_run_pinned_and_edits_in_place(bot, cog):
    await bot.store.set(GUILD, "marathon_hosts_count_as_ours", True)
    await bot.store.set(GUILD, "marathon_runner_posts", False)
    marathon = await added(bot, cog)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    board = [one for one in posts(bot) if "BaF on the schedule" in one.content]
    assert len(board) == 1 and board[0].pinned
    assert "Super Metroid" in board[0].content and "<@9001>" in board[0].content
    assert board[0].kwargs["allowed_mentions"].users is False
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert len([one for one in posts(bot) if "BaF on the schedule" in one.content]) == 1
    await pair_runner(bot, bot.guild, FakeActor(), marathon, "Interview Crew", 42, everywhere=False)
    assert "Blaster Master" in board[0].content and "<@42>" in board[0].content
    assert (await kinds(bot.db)).count("marathon.board_posted") == 1
    assert "marathon.board_refreshed" in await kinds(bot.db)


async def test_the_board_comes_down_a_day_after_the_end(bot, cog):
    marathon = await added(bot, cog)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    board = next(one for one in posts(bot) if "BaF on the schedule" in one.content)
    cog.clock = lambda: NOW + timedelta(days=2)
    await cog.tick_marathon(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert board.pinned is False
    assert (await get_marathon(bot.db, GUILD, marathon["id"]))["board_pinned"] == 0


async def test_staff_post_the_board_even_with_nobody_of_ours_found(bot, cog):
    cog.client.runs_given = SCHEDULE[:2]
    marathon = await added(bot, cog)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert posts(bot) == []
    outcome = await post_board(bot, bot.guild, FakeActor(), marathon)
    assert outcome.ok
    assert "Nobody from BaF" in posts(bot)[0].content


# --- reminders ------------------------------------------------------------------------------


async def reminders(bot):
    return [
        one
        for one in posts(bot)
        if not one.content.startswith("**") and "right now" not in one.content
    ]


async def test_the_two_hour_heads_up_posts_without_a_mention(bot, cog):
    cog.client.runs_given = [
        a_run(3, 120, game="Super Metroid", people=(("Sky", "skyruns", "runner"),))
    ]
    marathon = await added(bot, cog)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    said = await reminders(bot)
    assert len(said) == 1
    assert "<@&" not in said[0].content
    assert said[0].kwargs["allowed_mentions"].roles is False
    assert (await details_of(bot.db, "marathon.reminded"))["mark"] == 120


async def test_the_fifteen_minute_reminder_pings_the_members_role_and_the_channels_in_a_window(
    bot, cog
):
    await bot.store.set(GUILD, "marathon_ping_role_default", True)
    channel = await gdq_row(bot)
    await set_ping_mode(bot, bot.guild, FakeActor(), channel["id"], "events")
    cog.client.runs_given = [
        a_run(3, 15, game="Super Metroid", people=(("Sky", "skyruns", "runner"),))
    ]
    marathon = await added(bot, cog, channel=channel)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    said = (await reminders(bot))[-1]

    assert said.content.startswith(f"<@&{FAN_ROLE}> <@&{CHANNEL_ROLE}> ")
    assert f"<@&{GOLIVE_ROLE}>" not in said.content
    assert sorted(role.id for role in said.kwargs["allowed_mentions"].roles) == [
        FAN_ROLE,
        CHANNEL_ROLE,
    ]
    assert "https://twitch.tv/gamesdonequick" in said.content
    assert (await details_of(bot.db, "marathon.reminded"))["pinged"] is True


async def test_outside_a_window_an_events_channel_role_is_not_pinged(bot, cog):
    await bot.store.set(GUILD, "marathon_ping_role_default", True)
    channel = await gdq_row(bot)
    await set_ping_mode(bot, bot.guild, FakeActor(), channel["id"], "events")
    cog.client.runs_given = [
        a_run(3, 15, game="Super Metroid", people=(("Sky", "skyruns", "runner"),))
    ]
    marathon = await added(bot, cog)
    await set_channel(bot, bot.guild, FakeActor(), marathon, channel["id"])
    await bot.db.conn.execute("DELETE FROM spotlight_ping_windows")
    await bot.db.conn.commit()
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    said = (await reminders(bot))[-1]
    assert said.content.startswith(f"<@&{FAN_ROLE}> ")
    assert f"<@&{CHANNEL_ROLE}>" not in said.content


async def test_a_reminder_fires_once_and_not_before_its_mark(bot, cog):
    cog.client.runs_given = [
        a_run(3, 40, game="Super Metroid", people=(("Sky", "skyruns", "runner"),))
    ]
    marathon = await added(bot, cog)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    heads_up = len(await reminders(bot))
    cog.clock = lambda: NOW + timedelta(minutes=20)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert len(await reminders(bot)) == heads_up
    cog.clock = lambda: NOW + timedelta(minutes=25)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert len(await reminders(bot)) == heads_up + 1


async def test_a_stale_mark_is_skipped_and_logged_never_posted_late(bot, cog):
    cog.client.runs_given = [
        a_run(3, 50, game="Super Metroid", people=(("Sky", "skyruns", "runner"),))
    ]
    marathon = await added(bot, cog)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert await reminders(bot) == []
    assert (await details_of(bot.db, "marathon.reminder_skipped"))["mark"] == 120


async def test_a_spotlight_bump_a_minute_ago_does_not_stop_a_reminder(bot, cog):
    channel = await gdq_row(bot)
    cog.client.runs_given = [
        a_run(3, 15, game="Super Metroid", people=(("Sky", "skyruns", "runner"),))
    ]
    await start_session(bot.db, GUILD, channel["id"], StreamInfo(title="AGDQ"), "on")
    await bot.db.conn.execute("UPDATE spotlight_sessions SET last_bump_at = ?", (at(-1),))
    await bot.db.conn.commit()
    marathon = await added(bot, cog, channel=channel)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert len(await reminders(bot)) == 1


# --- live and the shoutout ------------------------------------------------------------------


async def live_title(bot, channel, title, game=""):
    await start_session(bot.db, GUILD, channel["id"], StreamInfo(title=title, game=game), "on")


async def test_the_title_naming_our_game_flips_it_live_and_shouts_without_a_ping(bot, cog):
    channel = await gdq_row(bot)
    marathon = await added(bot, cog, channel=channel)
    await live_title(bot, channel, "AGDQ 2027 - Super Metroid Any% by Sky !schedule")
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    rows = await runs_by_game(bot, marathon)

    assert rows["Super Metroid"]["state"] == mt.LIVE
    assert rows["Super Metroid"]["live_because"] == mt.BY_TITLE
    shout = next(one for one in posts(bot) if "right now" in one.content)
    assert rows["Super Metroid"]["shout_message_id"] == shout.id
    assert "<@&" not in shout.content
    assert "marathon.shouted" in await kinds(bot.db)


async def test_a_race_with_two_of_baf_on_it_shouts_once_naming_both(bot, cog):
    """B2 of the marathon-people design: one slot, one shoutout, every BaF name in it."""
    await bot.db.conn.execute(
        "INSERT INTO golive_links(user_id, twitch_login, linked_at) VALUES (?, ?, ?)",
        (77, "peasplays", at(-9999)),
    )
    await bot.db.conn.commit()
    race = (
        ("Sky", "skyruns", "runner"),
        ("TheKing", None, "runner"),
        ("Peas", "peasplays", "runner"),
    )
    cog.client.runs_given = [a_run(1, 30, game="Super Mario 64", people=race)]
    marathon = await added(bot, cog)
    cog.clock = lambda: NOW + timedelta(minutes=31)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    shouts = [one for one in posts(bot) if "right now" in one.content]
    assert len(shouts) == 1
    assert "<@9001>" in shouts[0].content and "<@77>" in shouts[0].content


async def test_a_restart_after_the_shout_posts_nothing_again(bot, cog):
    channel = await gdq_row(bot)
    marathon = await added(bot, cog, channel=channel)
    await live_title(bot, channel, "Super Metroid")
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    before = len(posts(bot))
    again = Marathons(bot)
    again.client, again.clock = cog.client, cog.clock
    bot.cogs[cogmod.COG_NAME] = again
    await again.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert len(posts(bot)) == before


async def test_a_later_title_marks_the_earlier_runs_done_and_our_skipped_run_is_important(bot, cog):
    channel = await gdq_row(bot)
    marathon = await added(bot, cog, channel=channel)
    cog.clock = lambda: NOW + timedelta(minutes=80)
    await live_title(bot, channel, "Kirby Air Riders - Air Ride")
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    rows = await runs_by_game(bot, marathon)

    assert rows["Kirby Air Riders"]["state"] == mt.LIVE
    assert rows["Super Metroid"]["state"] == mt.DONE
    assert rows["Super Metroid"]["shout_message_id"] is None
    assert (await details_of(bot.db, "marathon.run_skipped"))["member_id"] == SKY


async def test_with_no_title_a_late_run_waits_the_grace_then_the_schedule_calls_it(bot, cog):
    channel = await gdq_row(bot)
    marathon = await added(bot, cog, channel=channel)
    await live_title(bot, channel, "Nothing on the schedule")
    cog.clock = lambda: NOW + timedelta(minutes=60)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert (await runs_by_game(bot, marathon))["Super Metroid"]["state"] == mt.UPCOMING
    cog.clock = lambda: NOW + timedelta(minutes=121)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    row = (await runs_by_game(bot, marathon))["Super Metroid"]
    assert row["state"] == mt.LIVE and row["live_because"] == mt.BY_SCHEDULE


async def test_the_shout_is_rewritten_in_the_past_tense_when_the_run_is_done(bot, cog):
    marathon = await added(bot, cog)
    cog.clock = lambda: NOW + timedelta(minutes=31)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    shout = next(one for one in posts(bot) if "right now" in one.content)
    cog.clock = lambda: NOW + timedelta(minutes=91)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert "that run is over" in shout.content
    assert (await details_of(bot.db, "marathon.run_done"))["edited"] is True


async def test_staff_shout_a_run_by_hand_and_mark_one_done(bot, cog):
    marathon = await added(bot, cog)
    row = (await runs_by_game(bot, marathon))["Super Metroid"]
    outcome = await shout_now(bot, bot.guild, FakeActor(), marathon, row)
    assert outcome.ok
    again = await shout_now(bot, bot.guild, FakeActor(), marathon, row)
    assert not again.ok and again.code == "not_shoutable"
    done = await mark_done(bot, bot.guild, FakeActor(), marathon, row)
    assert done.ok
    assert (await runs_by_game(bot, marathon))["Super Metroid"]["state"] == mt.DONE
    other = (await runs_by_game(bot, marathon))["Celeste"]
    refused = await shout_now(bot, bot.guild, FakeActor(), marathon, other)
    assert refused.code == "not_ours"


# --- shadow ---------------------------------------------------------------------------------


async def test_shadow_posts_land_in_the_shadow_home_with_the_note_and_log_would(bot, cog):
    await bot.store.set(GUILD, "marathon_mode", "shadow")
    marathon = await added(bot, cog)
    cog.clock = lambda: NOW + timedelta(minutes=31)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))

    assert posts(bot) == []
    shadowed = posts(bot, SHADOW_CHANNEL)
    assert shadowed and all(f"<#{CHANNEL}>" in one.content for one in shadowed)
    assert not any(one.pinned for one in shadowed)
    found = await kinds(bot.db)
    assert "marathon.would_post_board" in found and "marathon.would_shout" in found
    assert "marathon.shouted" not in found and "marathon.board_posted" not in found


async def test_marathons_rehearse_in_their_own_home_over_the_global_one(bot, cog):
    """Owner, 2026-09-25: only the front door rehearses in #welcome-test."""
    await bot.store.set(GUILD, "marathon_mode", "shadow")
    await bot.store.set(GUILD, "marathon_shadow_channel_id", LOG_CHANNEL)
    await bot.store.set(GUILD, "marathon_public_shadow_channel_id", LOG_CHANNEL)
    marathon = await added(bot, cog)
    cog.clock = lambda: NOW + timedelta(minutes=31)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))

    assert posts(bot, SHADOW_CHANNEL) == []
    assert posts(bot, LOG_CHANNEL)
    assert (await details_of(bot.db, "marathon.would_post_board"))["shadow_home"] == LOG_CHANNEL


async def test_off_reads_nothing_and_posts_nothing(bot, cog):
    marathon = await added(bot, cog)
    await bot.store.set(GUILD, "marathon_mode", "off")
    calls = cog.client.calls
    cog.clock = lambda: NOW + timedelta(hours=3)
    await cog.tick_once()
    assert cog.client.calls == calls and posts(bot) == []
    assert marathon is not None


# --- the ping window ------------------------------------------------------------------------


async def test_a_marathon_with_a_channel_opens_one_window_for_its_dates(bot, cog):
    await bot.store.set(GUILD, "marathon_ping_role_default", True)
    channel = await gdq_row(bot)
    marathon = await added(bot, cog, channel=channel)
    windows = await windows_for(bot.db, channel["id"])

    assert len(windows) == 1
    assert windows[0]["source"] == "marathon" and windows[0]["source_id"] == marathon["id"]
    assert windows[0]["starts_at"] == at(-240) and windows[0]["ends_at"] == at(330)
    assert windows[0]["note"] == "AGDQ 2027"
    await cog.refresh(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert len(await windows_for(bot.db, channel["id"])) == 1


async def test_pause_and_remove_close_the_window(bot, cog):
    await bot.store.set(GUILD, "marathon_ping_role_default", True)
    channel = await gdq_row(bot)
    marathon = await added(bot, cog, channel=channel)
    await set_active(bot, bot.guild, FakeActor(), marathon, False)
    assert await windows_for(bot.db, channel["id"]) == []
    await set_active(bot, bot.guild, FakeActor(), marathon, True)
    assert len(await windows_for(bot.db, channel["id"])) == 1
    await archive_marathon(bot, bot.guild, FakeActor(), marathon)
    assert await windows_for(bot.db, channel["id"]) == []
    assert await get_marathon(bot.db, GUILD, marathon["id"]) is None
    assert "marathon.window_dropped" in await kinds(bot.db)


async def test_a_marathon_survives_its_channel_row_being_deleted(bot, cog):
    channel = await gdq_row(bot)
    marathon = await added(bot, cog, channel=channel)
    await delete_channel(bot.db, channel["id"])
    fresh = await get_marathon(bot.db, GUILD, marathon["id"])
    read = await cog.refresh(bot.guild, fresh)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert read.ok
    assert await windows_for(bot.db, channel["id"]) == []


# --- adding and pairing ---------------------------------------------------------------------


async def test_an_unknown_site_a_duplicate_and_an_unreadable_link_are_refused_in_words(bot, cog):
    other = await create_marathon(
        bot, bot.guild, FakeActor(), name="ESA", url="https://example.org/marathon/LSS26/schedule"
    )
    assert other.code == "unknown_site" and "horaro.net schedules" in other.message
    await added(bot, cog)
    twice = await create_marathon(bot, bot.guild, FakeActor(), name="Again", url=URL)
    assert twice.code == "duplicate" and "AGDQ 2027" in twice.message
    cog.client.raises = ScheduleError("the GDQ tracker has no event 99")
    missing = await create_marathon(
        bot, bot.guild, FakeActor(), name="Nope", url="https://gamesdonequick.com/schedule/99"
    )
    assert missing.code == "unreadable" and "no event 99" in missing.message


async def test_a_pairing_wins_and_unpairing_gives_the_automatic_match_back(bot, cog):
    marathon = await added(bot, cog)
    outcome = await pair_runner(bot, bot.guild, FakeActor(), marathon, "Sky", 77)
    assert outcome.ok
    assert mt.member_ids((await runs_by_game(bot, marathon))["Super Metroid"]) == [77]
    cur = await bot.db.conn.execute("SELECT * FROM marathon_people")
    pairing = await cur.fetchone()
    await unpair_runner(bot, bot.guild, FakeActor(), marathon, pairing)
    assert mt.member_ids((await runs_by_game(bot, marathon))["Super Metroid"]) == [SKY]
    assert "marathon.unpaired" in await kinds(bot.db)


async def test_hosts_count_only_while_the_key_says_so(bot, cog):
    await bot.store.set(GUILD, "marathon_hosts_count_as_ours", True)
    await bot.db.conn.execute(
        "INSERT INTO golive_links(user_id, twitch_login, linked_at) VALUES (?, ?, ?)",
        (55, "hostlogin", at(0)),
    )
    await bot.db.conn.commit()
    cog.client.runs_given = [a_run(1, 30, people=(("Host", "hostlogin", "host"),))]
    marathon = await added(bot, cog)
    assert mt.is_ours((await runs_of(bot.db, marathon["id"]))[0])
    await bot.store.set(GUILD, "marathon_match_hosts", False)
    await cog.rematch(bot.guild, marathon)
    assert not mt.is_ours((await runs_of(bot.db, marathon["id"]))[0])


async def test_every_row_a_member_run_writes_carries_the_marathon_the_run_and_the_member(bot, cog):
    marathon = await added(bot, cog)
    cog.clock = lambda: NOW + timedelta(minutes=31)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    for kind in ("marathon.run_live", "marathon.shouted", "marathon.run_matched"):
        found = await details_of(bot.db, kind)
        assert found["marathon_id"] == marathon["id"], kind
        assert found["run_id"] and found["member_id"] == SKY, kind
    assert json.loads((await runs_by_game(bot, marathon))["Super Metroid"]["reminders_sent"]) == []


# --- the /marathon panel --------------------------------------------------------------------


class Member:
    def __init__(self, user_id):
        self.id = user_id
        self.display_name = "Sky"
        self.bot = False


async def test_a_member_sees_ours_next_and_no_staff_moves(bot, cog):
    await added(bot, cog)
    bot.store.is_staff = lambda member: False
    embed, view = await cogmod.build_panel(bot, bot.guild, Member(SKY))

    assert "BaF next" in embed.description and "Super Metroid" in embed.description
    assert "<@9001>" in embed.description
    labels = [getattr(one, "label", None) for one in view.children]
    assert "Add a marathon…" not in labels and "Logs" not in labels
    assert "My runs" in labels
    assert not any(isinstance(one, cogmod.MarathonPick) for one in view.children)
    assert view.render_again is not None


async def test_staff_see_every_marathon_with_its_read_state_and_the_moves(bot, cog):
    await added(bot, cog)
    embed, view = await cogmod.build_panel(bot, bot.guild, FakeActor())
    assert "AGDQ 2027" in embed.description and "1 BaF of 5" in embed.description
    labels = [getattr(one, "label", None) for one in view.children]
    assert {"Add a marathon…", "Logs", "Refresh"} <= set(labels)


async def test_my_runs_lists_only_the_members_own(bot, cog):
    await added(bot, cog)
    embed, _ = await cogmod.build_mine(bot, bot.guild, Member(SKY))
    assert "Super Metroid" in embed.description
    embed, _ = await cogmod.build_mine(bot, bot.guild, Member(42))
    assert mt.NOTHING_MINE in embed.description


def card_buttons(view):
    return [
        (one.label, one.row) for one in view.children if isinstance(one, discord.ui.Button)
    ]


async def test_the_card_is_people_untrack_read_the_links_and_back(bot, cog):
    marathon = await added(bot, cog)
    _, view = await cogmod.build_card(bot, bot.guild, marathon["id"])
    assert card_buttons(view) == [
        ("People…", 2),
        ("Untrack", 2),
        ("Read it now", 2),
        ("Open on the site", 2),
        ("Back", 3),
    ]
    await set_active(bot, bot.guild, FakeActor(), marathon, False)
    _, view = await cogmod.build_card(bot, bot.guild, marathon["id"])
    assert [label for label, _row in card_buttons(view)] == [
        "People…",
        "Untrack",
        "Open on the site",
        "Back",
    ]


async def test_the_card_opens_on_the_two_header_lines_then_baf_then_posts(bot, cog):
    marathon = await added(bot, cog)
    embed, _ = await cogmod.build_card(bot, bot.guild, marathon["id"])
    lines = embed.description.splitlines()
    assert "GDQ tracker" in lines[0] and "<t:" in lines[0]
    assert "last read <t:" in lines[1] and "next read <t:" in lines[1] and "BaF" in lines[1]
    assert lines[2] == "" and any("Super Metroid" in one for one in lines[3:])
    assert lines[-1].startswith("**Posts:**")
    assert not any(one in embed.description for one in ("**Schedule:**", "**Runs**", "**Event**"))


async def test_a_card_for_a_marathon_that_is_gone_is_nothing_to_draw(bot, cog):
    assert await cogmod.build_card(bot, bot.guild, 999) == (None, None)


async def test_a_pinned_board_still_comes_down_after_marathon_posts_are_turned_off(bot, cog):
    """Checklist 38: `off` stops new effects, never the end of one already out."""
    marathon = await added(bot, cog)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    board = next(one for one in posts(bot) if "BaF on the schedule" in one.content)
    assert board.pinned
    await bot.store.set(GUILD, "marathon_mode", "off")
    cog.clock = lambda: NOW + timedelta(days=2)
    await cog.tick_once()
    assert board.pinned is False


# --- the next GDQ event (marathon-next-event) -----------------------------------------------

STAFF_ROOM = 444
AFTER = NOW + timedelta(days=1)
SGDQ = {
    "id": 75,
    "short": "SGDQ2027",
    "name": "Summer Games Done Quick 2027",
    "datetime": "2027-06-27T12:30:00-04:00",
    "archived": False,
    "draft": True,
}
AGDQ = {
    "id": 74,
    "short": "AGDQ2027",
    "name": "Awesome Games Done Quick 2027",
    "datetime": "2027-01-03T11:30:00-05:00",
    "archived": False,
    "draft": True,
}


class EventsClient(FakeClient):
    def __init__(self, events=None, events_raise=None):
        super().__init__()
        self.events_given = list(events if events is not None else [SGDQ, AGDQ])
        self.events_raise = events_raise
        self.event_calls = 0

    async def events(self):
        self.event_calls += 1
        if self.events_raise is not None:
            raise self.events_raise
        return list(self.events_given)


async def staff_room(bot):
    """Notices go into the marathon inbox thread, made in the events channel."""
    threading(bot, STAFF_ROOM)
    await bot.store.set(GUILD, "events_announce_channel_id", STAFF_ROOM)


def notices(bot, channel_id=STAFF_ROOM):
    return notices_in(bot, channel_id)


def booted_cog(bot, client=None):
    made = Marathons(bot)
    made.client = client or EventsClient()
    made.clock = lambda: AFTER
    bot.cogs[cogmod.COG_NAME] = made
    return made


@pytest.fixture
async def over(bot, cog):
    await staff_room(bot)
    cog.client = EventsClient()
    marathon = await added(bot, cog)
    cog.clock = lambda: AFTER
    return marathon


async def fresh(bot, marathon):
    return await get_marathon(bot.db, GUILD, marathon["id"])


async def record_now(bot, marathon):
    return mt.suggestion_of(await fresh(bot, marathon))


async def test_an_over_gdq_marathon_suggests_the_next_event_once_with_one_notice(bot, cog, over):
    await cog.tick_once()
    await cog.tick_once()

    record = await record_now(bot, over)
    assert record["event_id"] == "75" and record["name"] == "Summer Games Done Quick 2027"
    assert record["url"] == "https://tracker.gamesdonequick.com/tracker/event/75"
    found = notices(bot)
    assert len(found) == 1 and cog.client.event_calls == 1
    assert "AGDQ 2027 is over" in found[0].content
    assert "**Summer Games Done Quick 2027**" in found[0].content
    assert record["notice_message_id"] == found[0].id
    view = found[0].kwargs["view"]
    assert [one.item.custom_id for one in view.children] == [
        f"marathon:{over['id']}:next:75:add",
        f"marathon:{over['id']}:next:75:dismiss",
    ]
    found = await details_of(bot.db, "marathon.next_suggested")
    assert found["event"] == "75" and found["short"] == "SGDQ2027"
    assert found["datetime"] == "2027-06-27T16:30:00+00:00"


async def test_a_marathon_that_is_not_over_is_never_looked_up(bot, cog, over):
    cog.clock = lambda: NOW
    await cog.tick_once()
    assert cog.client.event_calls == 0 and await record_now(bot, over) is None


async def test_the_switch_off_suggests_nothing(bot, cog, over):
    await bot.store.set(GUILD, "marathon_suggest_next", False)
    await cog.tick_once()
    assert cog.client.event_calls == 0 and notices(bot) == []


async def test_a_failed_lookup_leaves_null_and_only_the_next_boot_tries_again(bot, cog, over):
    cog.client.events_raise = ScheduleError("the GDQ tracker answered 503")
    await cog.tick_once()
    await cog.tick_once()
    assert cog.client.event_calls == 1
    assert (await fresh(bot, over))["suggested_next"] is None
    assert (await details_of(bot.db, "marathon.next_failed"))["reason"].endswith("503")

    booted = booted_cog(bot)
    await booted.tick_once()
    assert (await record_now(bot, over))["event_id"] == "75"
    assert len(notices(bot)) == 1


async def test_nothing_ahead_is_a_none_record_and_is_not_asked_again(bot, cog, over):
    cog.client.events_given = [AGDQ]
    await cog.tick_once()
    record = await record_now(bot, over)
    assert record["event_id"] is None and mt.next_state(record) == mt.NEXT_NONE
    assert "marathon.next_none" in await kinds(bot.db)
    assert notices(bot) == []
    again = booted_cog(bot)
    await again.tick_once()
    assert again.client.event_calls == 0


async def test_a_non_gdq_marathon_never_gets_a_suggestion(bot, cog, over):
    await bot.db.conn.execute(
        "UPDATE marathons SET source = 'horaro' WHERE id = ?", (over["id"],)
    )
    await bot.db.conn.commit()
    await cog.tick_once()
    assert cog.client.event_calls == 0
    refused = await cogmod.look_again(bot, bot.guild, FakeActor(), await fresh(bot, over))
    assert refused.code == "not_gdq" and "not a GDQ marathon" in refused.message


async def test_not_this_one_dismisses_folds_the_notice_and_is_never_re_suggested(bot, cog, over):
    await cog.tick_once()
    done = await cogmod.dismiss_next(bot, bot.guild, FakeActor(), await fresh(bot, over))
    assert done.ok and "dismissed" in done.message
    assert mt.next_state(await record_now(bot, over)) == mt.NEXT_DISMISSED
    notice = notices(bot)[0]
    assert notice.content.startswith("~~") and notice.content.endswith("~~")
    assert all(one.item.disabled for one in notice.edits[-1]["view"].children)
    booted = booted_cog(bot)
    await booted.tick_once()
    assert booted.client.event_calls == 0
    again = await cogmod.dismiss_next(bot, bot.guild, FakeActor(), await fresh(bot, over))
    assert again.code == "nothing_suggested"


async def test_look_again_after_a_dismissal_suggests_again_without_a_new_notice(bot, cog, over):
    await cog.tick_once()
    await cogmod.dismiss_next(bot, bot.guild, FakeActor(), await fresh(bot, over))
    looked = await cogmod.look_again(bot, bot.guild, FakeActor(), await fresh(bot, over))
    assert looked.ok and "Summer Games Done Quick 2027" in looked.message
    record = await record_now(bot, over)
    assert mt.next_state(record) == mt.NEXT_OPEN and record.get("dismissed_at") is None
    assert len(notices(bot)) == 1


async def test_look_again_refuses_in_words_before_the_marathon_is_over(bot, cog, over):
    cog.clock = lambda: NOW
    refused = await cogmod.look_again(bot, bot.guild, FakeActor(), await fresh(bot, over))
    assert refused.code == "not_over" and refused.status == 409


async def test_add_it_makes_the_next_marathon_on_the_same_channel_and_links_it(bot, cog):
    await staff_room(bot)
    cog.client = EventsClient()
    channel = await gdq_row(bot)
    parent = await added(bot, cog, channel=channel)
    cog.clock = lambda: AFTER
    await cog.tick_once()

    outcome = await cogmod.add_next(
        bot, bot.guild, FakeActor(), await fresh(bot, parent), event_id=75
    )
    assert outcome.ok, outcome.message
    made = outcome.value
    assert made["name"] == "Summer Games Done Quick 2027"
    assert made["schedule_url"] == "https://tracker.gamesdonequick.com/tracker/event/75"
    assert made["spotlight_id"] == channel["id"]
    record = await record_now(bot, parent)
    assert record["added_marathon_id"] == made["id"] and record["added_by"] == FakeActor.id
    found = await details_of(bot.db, "marathon.next_added")
    assert found["marathon_id"] == made["id"] and found["by"] == FakeActor.id
    notice = notices(bot)[0]
    assert notice.content.startswith("Added **Summer Games Done Quick 2027**")
    twice = await cogmod.add_next(bot, bot.guild, FakeActor(), await fresh(bot, parent))
    assert twice.code == "nothing_suggested"


async def test_an_old_notice_for_another_event_changes_nothing(bot, cog, over):
    await cog.tick_once()
    refused = await cogmod.add_next(
        bot, bot.guild, FakeActor(), await fresh(bot, over), event_id=99
    )
    assert refused.code == "suggestion_moved"
    assert mt.next_state(await record_now(bot, over)) == mt.NEXT_OPEN


async def test_an_event_already_on_the_list_is_linked_not_posted(bot, cog, over):
    await bot.db.conn.execute(
        "INSERT INTO marathons(guild_id, name, schedule_url, source, source_ref, added_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (GUILD, "SGDQ 2027", "https://gamesdonequick.com/schedule/75", "gdq", "75", "x"),
    )
    await bot.db.conn.commit()
    await cog.tick_once()
    record = await record_now(bot, over)
    assert mt.next_state(record) == mt.NEXT_ADDED and notices(bot) == []


async def test_shadow_sends_the_notice_to_the_shadow_home_as_would_suggest(bot, cog, over):
    await bot.store.set(GUILD, "marathon_mode", "shadow")
    await cog.tick_once()
    assert notices(bot) == []
    shadowed = [one for one in notices(bot, SHADOW_CHANNEL) if "is over" in one.content]
    assert len(shadowed) == 1 and f"<#{STAFF_ROOM}>" in shadowed[0].content
    found = await kinds(bot.db)
    assert "marathon.would_suggest_next" in found and "marathon.next_suggested" not in found


async def test_an_inbox_it_cannot_make_is_a_failed_notice_row_and_the_record_stays(
    bot, cog, over
):
    await bot.store.set(GUILD, "marathon_inbox_channel_id", 31337)
    await bot.db.conn.execute("DELETE FROM marathon_inbox")
    await bot.db.conn.commit()
    await cog.tick_once()
    assert mt.next_state(await record_now(bot, over)) == mt.NEXT_OPEN
    failed = await details_of(bot.db, "marathon.next_notice_failed")
    assert failed["reason"] == cogmod.NOT_VISIBLE


async def test_the_notice_buttons_are_staff_only_and_rebuild_from_their_custom_id(bot, cog, over):
    await cog.tick_once()
    notice = notices(bot)[0]
    custom = notice.kwargs["view"].children[0].item.custom_id
    match = cogmod.re.fullmatch(cogmod.NEXT_TEMPLATE, custom)
    button = await cogmod.NextButton.from_custom_id(None, None, match)
    assert (button.marathon_id, button.event_id, button.action) == (over["id"], 75, "add")

    bot.store.is_staff = lambda member: False
    stranger = FakeInteraction(bot, Member(42), bot.guild)
    await button.on_click(stranger)
    assert "staff only" in stranger.sent
    assert mt.next_state(await record_now(bot, over)) == mt.NEXT_OPEN

    bot.store.is_staff = lambda member: True
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    await cogmod.NextButton(over["id"], 75, "dismiss").on_click(lead)
    assert "dismissed" in lead.sent
    assert mt.next_state(await record_now(bot, over)) == mt.NEXT_DISMISSED


async def test_the_panel_card_says_the_next_event(bot, cog, over):
    await cog.tick_once()
    embed, _view = await cogmod.build_card(bot, bot.guild, over["id"])
    assert "Summer Games Done Quick 2027" in embed.description


# --- §G: a done run has a way back ----------------------------------------------------------


async def test_mark_it_upcoming_brings_a_done_run_back_and_keeps_its_reminders(bot, cog):
    marathon = await added(bot, cog)
    cog.clock = lambda: NOW + timedelta(minutes=31)
    await cog.follow(bot.guild, await fresh(bot, marathon))
    metroid = (await runs_by_game(bot, marathon))["Super Metroid"]
    await mark_done(bot, bot.guild, FakeActor(), marathon, metroid)
    sent = (await runs_by_game(bot, marathon))["Super Metroid"]["reminders_sent"]

    outcome = await cogmod.mark_upcoming(bot, bot.guild, FakeActor(), marathon, metroid)
    row = (await runs_by_game(bot, marathon))["Super Metroid"]
    assert outcome.ok and row["state"] == mt.UPCOMING
    assert row["live_at"] is None and row["done_at"] is None
    assert row["live_because"] == mt.BY_STAFF and row["reminders_sent"] == sent
    found = await details_of(bot.db, "marathon.run_reset")
    assert found["because"] == "staff" and found["from"] == mt.DONE
    again = await cogmod.mark_upcoming(bot, bot.guild, FakeActor(), marathon, metroid)
    assert again.code == "not_resettable"


async def test_mark_it_live_holds_the_run_and_shouts_one_of_ours_that_never_was(bot, cog):
    marathon = await added(bot, cog)
    metroid = (await runs_by_game(bot, marathon))["Super Metroid"]
    await mark_done(bot, bot.guild, FakeActor(), marathon, metroid)
    before = len(posts(bot))

    outcome = await cogmod.mark_live(bot, bot.guild, FakeActor(), marathon, metroid)
    row = (await runs_by_game(bot, marathon))["Super Metroid"]
    assert outcome.ok and row["state"] == mt.LIVE and row["live_because"] == mt.BY_STAFF
    assert row["shout_message_id"] and len(posts(bot)) > before
    assert (await details_of(bot.db, "marathon.run_live"))["because"] == "staff"
    refused = await cogmod.mark_live(bot, bot.guild, FakeActor(), marathon, metroid)
    assert refused.code == "not_liveable"


async def test_the_card_picks_a_run_and_the_run_view_draws_only_its_moves(bot, cog):
    marathon = await added(bot, cog)
    _, view = await cogmod.build_card(bot, bot.guild, marathon["id"])
    pick = next(one for one in view.children if isinstance(one, cogmod.RunPick))
    assert "Super Metroid" in [option.label for option in pick.options]
    metroid = (await runs_by_game(bot, marathon))["Super Metroid"]
    _, run_view = await cogmod.build_run(bot, bot.guild, marathon["id"], metroid["id"])
    labels = [getattr(one, "label", None) for one in run_view.children]
    assert labels == ["Shout it now", "Mark it live", "Mark done", "Back", "Make it now"]


# --- a marathon is an event (docs/info/marathon-events-page-design.md §B) --------------------


@pytest.fixture
def proposals(monkeypatch):
    """The events review, offline: `propose_from` files the row exactly as the review would."""
    from black_bloc.events import create_event, ends_at, get_event

    made = []

    async def fake(bot, guild, actor, fields, *, requester=None, via="discord"):
        event_id = await create_event(
            bot.db,
            guild.id,
            getattr(actor, "id", actor),
            title=fields.title,
            description=fields.description,
            where=fields.where,
            starts_at=fields.starts,
            finishes_at=ends_at(fields.starts, fields.minutes),
        )
        made.append({"actor": actor, "fields": fields, "via": via})
        return ("proposed", await get_event(bot.db, event_id))

    monkeypatch.setattr("black_bloc.cogs.community.events.propose_from", fake)
    return made


class FakeScheduled:
    def __init__(self):
        self.edits = []

    async def edit(self, **kwargs):
        self.edits.append(kwargs)


async def event_of(bot, marathon):
    from black_bloc.events import get_event

    fresh = await get_marathon(bot.db, GUILD, marathon["id"])
    return fresh, (await get_event(bot.db, fresh["event_id"]) if fresh["event_id"] else None)


async def with_event(bot, cog, **given):
    outcome = await create_marathon(
        bot, bot.guild, FakeActor(), name="AGDQ 2027", url=URL, make_event=True, **given
    )
    assert outcome.ok, outcome.message
    return outcome


async def test_adding_with_the_box_on_puts_one_pending_event_into_review_dated_from_the_schedule(
    bot, cog, proposals
):
    await bot.store.set(GUILD, "marathon_channel_id", CHANNEL)
    channel = await gdq_row(bot)
    outcome = await with_event(bot, cog, spotlight_id=channel["id"])
    marathon, event = await event_of(bot, outcome.value)

    assert len(proposals) == 1 and event["status"] == "pending"
    assert event["title"] == "AGDQ 2027"
    assert event["starts_at"] == at(-120) and event["ends_at"] == at(210)
    assert event["location"] == "https://twitch.tv/gamesdonequick"
    assert event["where_kind"] == "other"
    assert event["description"] == (
        f"AGDQ 2027 — read from the GDQ schedule. BaF runs are boarded in <#{CHANNEL}>."
    )
    assert marathon["event_mode"] == "marathon"
    assert f"#{event['id']}" in outcome.message
    made = await details_of(bot.db, "marathon.event_made")
    assert made["event_id"] == event["id"] and made["marathon_id"] == marathon["id"]


async def test_with_no_channel_the_events_where_is_the_schedule_page(bot, cog, proposals):
    outcome = await with_event(bot, cog)
    _, event = await event_of(bot, outcome.value)
    assert event["location"] == "https://gamesdonequick.com/schedule/74"


async def test_adding_with_the_box_off_makes_no_event_and_does_not_wait_for_one(
    bot, cog, proposals
):
    outcome = await create_marathon(
        bot, bot.guild, FakeActor(), name="AGDQ 2027", url=URL, make_event=False
    )
    marathon, event = await event_of(bot, outcome.value)
    assert event is None and proposals == []
    assert marathon["event_mode"] == "none"
    assert "marathon.event_made" not in await kinds(bot.db)


async def test_the_event_mode_starts_where_marathon_event_mode_default_says(bot, cog, proposals):
    await bot.store.set(GUILD, "marathon_event_mode_default", "marathon")
    outcome = await create_marathon(bot, bot.guild, FakeActor(), name="AGDQ 2027", url=URL)
    assert (await event_of(bot, outcome.value))[1] is not None


async def test_an_unpublished_schedule_makes_no_event_until_the_first_read_with_dates(
    bot, cog, proposals, monkeypatch
):
    monkeypatch.setattr(bot.guild, "get_member", lambda user_id: FakeActor(), raising=False)
    cog.client.runs_given = []
    outcome = await with_event(bot, cog)
    marathon, event = await event_of(bot, outcome.value)
    assert event is None and marathon["event_mode"] == "marathon"
    assert mt.EVENT_WAITING.format(name="AGDQ 2027") in outcome.message
    assert mt.event_line(marathon, None) == mt.EVENT_WAITING_LINE

    cog.client.runs_given = list(SCHEDULE)
    await cog.refresh(bot.guild, marathon)
    marathon, event = await event_of(bot, marathon)

    assert event is not None and event["starts_at"] == at(-120)
    assert len(proposals) == 1 and proposals[0]["actor"].id == FakeActor.id


async def test_a_waiting_marathon_with_nobody_to_propose_as_stops_waiting_and_says_so(
    bot, cog, proposals
):
    cog.client.runs_given = []
    outcome = await with_event(bot, cog)
    cog.client.runs_given = list(SCHEDULE)
    await cog.refresh(bot.guild, await get_marathon(bot.db, GUILD, outcome.value["id"]))
    marathon, event = await event_of(bot, outcome.value)

    assert event is None and marathon["event_mode"] == "none" and proposals == []
    failed = await details_of(bot.db, "marathon.event_make_failed")
    assert "nobody is left to propose it as" in failed["reason"]


async def test_a_read_that_moves_the_dates_re_dates_the_event_and_its_scheduled_event(
    bot, cog, proposals
):
    from black_bloc.events import set_scheduled

    outcome = await with_event(bot, cog)
    marathon, event = await event_of(bot, outcome.value)
    await set_scheduled(bot.db, event["id"], 4242)
    scheduled = FakeScheduled()
    bot.guild.get_scheduled_event = lambda scheduled_id: scheduled if scheduled_id == 4242 else None

    cog.client.runs_given = [a_run(0, -180), *SCHEDULE[1:], a_run(6, 300)]
    await cog.refresh(bot.guild, marathon)
    _, event = await event_of(bot, marathon)

    assert event["starts_at"] == at(-180) and event["ends_at"] == at(360)
    assert event["title"] == "AGDQ 2027" and event["status"] == "pending"
    assert scheduled.edits[0]["start_time"].isoformat() == at(-180)
    assert scheduled.edits[0]["end_time"].isoformat() == at(360)
    redated = await details_of(bot.db, "marathon.event_redated")
    assert redated["from"]["starts_at"] == at(-120) and redated["to"]["starts_at"] == at(-180)
    assert redated["scheduled"] == "moved"


async def test_a_scheduled_event_that_will_not_move_is_its_own_failed_row(bot, cog, proposals):
    from black_bloc.events import set_scheduled

    outcome = await with_event(bot, cog)
    marathon, event = await event_of(bot, outcome.value)
    await set_scheduled(bot.db, event["id"], 4242)
    bot.guild.get_scheduled_event = lambda scheduled_id: None

    cog.client.runs_given = [a_run(0, -180), *SCHEDULE[1:]]
    await cog.refresh(bot.guild, marathon)

    assert (await details_of(bot.db, "marathon.event_redated"))["scheduled"].startswith("failed")
    assert "marathon.scheduled_move_failed" in await kinds(bot.db)


async def test_a_read_that_keeps_the_dates_leaves_the_event_alone(bot, cog, proposals):
    outcome = await with_event(bot, cog)
    await cog.refresh(bot.guild, await get_marathon(bot.db, GUILD, outcome.value["id"]))
    assert "marathon.event_redated" not in await kinds(bot.db)


async def test_a_denied_event_is_left_alone_and_the_link_stays(bot, cog, proposals):
    from black_bloc.events import set_status

    outcome = await with_event(bot, cog)
    marathon, event = await event_of(bot, outcome.value)
    await set_status(bot.db, event["id"], "denied")

    cog.client.runs_given = [a_run(0, -180), *SCHEDULE[1:]]
    await cog.refresh(bot.guild, marathon)
    marathon, event = await event_of(bot, marathon)

    assert event["starts_at"] == at(-120) and marathon["event_id"] == event["id"]
    assert "marathon.event_redated" not in await kinds(bot.db)
    assert mt.event_line(marathon, "denied") == f"Event **#{event['id']}** — denied"


async def test_unlink_clears_the_pointer_and_never_touches_the_event(bot, cog, proposals):
    outcome = await with_event(bot, cog)
    marathon, event = await event_of(bot, outcome.value)

    done = await cogmod.unlink_the_event(bot, bot.guild, FakeActor(), marathon)
    fresh, _ = await event_of(bot, marathon)

    assert done.ok and f"#{event['id']}" in done.message
    assert fresh["event_id"] is None and fresh["event_mode"] == "none"
    from black_bloc.events import get_event

    assert (await get_event(bot.db, event["id"]))["status"] == "pending"
    assert (await details_of(bot.db, "marathon.event_unlinked"))["event_id"] == event["id"]
    again = await cogmod.unlink_the_event(bot, bot.guild, FakeActor(), fresh)
    assert not again.ok and again.status == 409


async def test_make_an_event_now_after_an_unlink_proposes_a_fresh_one(bot, cog, proposals):
    outcome = await with_event(bot, cog)
    marathon, first = await event_of(bot, outcome.value)
    await cogmod.unlink_the_event(bot, bot.guild, FakeActor(), marathon)

    made = await cogmod.make_event_now(bot, bot.guild, FakeActor(), marathon)
    _, second = await event_of(bot, marathon)

    assert made.ok and second["id"] != first["id"]
    refused = await cogmod.make_event_now(
        bot, bot.guild, FakeActor(), await get_marathon(bot.db, GUILD, marathon["id"])
    )
    assert not refused.ok and refused.code == "event_exists"
    assert f"#{second['id']}" in refused.message


async def test_removing_the_marathon_calls_its_event_off_with_the_reason(bot, cog, proposals):
    outcome = await with_event(bot, cog)
    marathon, event = await event_of(bot, outcome.value)

    await archive_marathon(bot, bot.guild, FakeActor(), marathon)
    from black_bloc.events import get_event

    assert (await get_event(bot.db, event["id"]))["status"] == "cancelled"
    assert (await details_of(bot.db, "marathon.event_cancelled"))["event_id"] == event["id"]
    cur = await bot.db.conn.execute(
        "SELECT reason FROM action_log WHERE kind = 'event.cancelled' ORDER BY id DESC LIMIT 1"
    )
    assert (await cur.fetchone())["reason"] == "marathon_removed"


async def test_removing_a_marathon_whose_event_is_settled_leaves_the_event_as_it_is(
    bot, cog, proposals
):
    from black_bloc.events import get_event, set_status

    outcome = await with_event(bot, cog)
    marathon, event = await event_of(bot, outcome.value)
    await set_status(bot.db, event["id"], "denied")

    await archive_marathon(bot, bot.guild, FakeActor(), marathon)

    assert (await get_event(bot.db, event["id"]))["status"] == "denied"
    assert "marathon.event_cancelled" not in await kinds(bot.db)


async def test_pausing_does_nothing_to_the_event(bot, cog, proposals):
    outcome = await with_event(bot, cog)
    marathon, event = await event_of(bot, outcome.value)
    await set_active(bot, bot.guild, FakeActor(), marathon, False)
    fresh, again = await event_of(bot, marathon)
    assert again["status"] == "pending" and fresh["event_id"] == event["id"]


async def test_the_card_says_the_event_and_unlink_takes_it_off(bot, cog, proposals):
    outcome = await with_event(bot, cog)
    marathon, event = await event_of(bot, outcome.value)
    embed, view = await cogmod.build_card(bot, bot.guild, marathon["id"])
    assert f"Event **#{event['id']}** — pending" in embed.description

    await cogmod.unlink_the_event(bot, bot.guild, FakeActor(), marathon)
    embed, view = await cogmod.build_card(bot, bot.guild, marathon["id"])
    assert "Event **#" not in embed.description and mt.EVENT_NONE_LINE not in embed.description


async def test_the_events_card_line_names_the_marathon_and_its_runs_of_ours(bot, cog, proposals):
    outcome = await with_event(bot, cog)
    marathon, event = await event_of(bot, outcome.value)
    line = await cogmod.marathon_of_event_line(bot, GUILD, event["id"])
    assert line == mt.MARATHON_OF_EVENT.format(name="AGDQ 2027", ours=1)
    assert await cogmod.marathon_of_event_line(bot, GUILD, 999) == ""


def test_the_add_modals_fifth_field_reads_a_mode_word_or_yes_or_no_for_one_release():
    from black_bloc import marathon_events as me

    assert me.wanted_mode_answer(" Runs ") == "runs"
    assert me.wanted_mode_answer("Yes") == "marathon"
    assert me.wanted_mode_answer(" no ") == "none"
    assert me.wanted_mode_answer("maybe") is None


async def test_the_add_modal_with_no_makes_the_marathon_and_no_event(bot, cog, proposals):
    modal = cogmod.AddMarathonModal(None, "marathon")
    assert modal.event.default == "marathon"
    modal.name._value = "AGDQ 2027"
    modal.url._value = URL
    modal.login._value = ""
    modal.event._value = "no"
    interaction = FakeInteraction(bot, FakeActor(), bot.guild)

    await modal.on_submit(interaction)

    rows = await cogmod.list_marathons(bot.db, GUILD)
    assert len(rows) == 1 and rows[0]["event_id"] is None and proposals == []


async def test_the_add_modal_refuses_an_answer_that_is_not_yes_or_no(bot, cog, proposals):
    modal = cogmod.AddMarathonModal(None, "none")
    assert modal.event.default == "none"
    modal.name._value = "AGDQ 2027"
    modal.url._value = URL
    modal.login._value = ""
    modal.event._value = "perhaps"
    interaction = FakeInteraction(bot, FakeActor(), bot.guild)

    await modal.on_submit(interaction)

    assert await cogmod.list_marathons(bot.db, GUILD) == []
    assert interaction.sent == mt.BAD_ADD_EVENT


# --- marathon-controls C: the card's Spotlight view ----------------------------------------


def pressed(view, label):
    return next(one for one in view.children if getattr(one, "label", None) == label)


async def test_the_card_says_the_spotlight(bot, cog):
    channel = await gdq_row(bot)
    marathon = await added(bot, cog, channel=channel)
    embed, view = await cogmod.build_card(bot, bot.guild, marathon["id"])
    assert "Spotlit and kept for ever" in embed.description
    assert all(len([one for one in view.children if one.row == row]) <= 5 for row in range(5))


async def test_a_marathon_with_no_channel_draws_no_spotlight_door(bot, cog):
    marathon = await added(bot, cog)
    _, view = await cogmod.build_card(bot, bot.guild, marathon["id"])
    assert "Spotlight…" not in [getattr(one, "label", None) for one in view.children]


# --- marathon-inbox-when: Change the schedule link… ------------------------------------------

HORARO = "https://horaro.net/esa/2026-summer1"


async def test_changing_the_link_keeps_the_marathon_and_reads_the_new_schedule_at_once(bot, cog):
    marathon = await added(bot, cog)
    await bot.db.conn.execute(
        "UPDATE marathons SET event_mode = 'runs', ping_role = 1, spotlight_mode = 'off', "
        "thread_id = 4242, fetch_failures = 3, last_error = 'boom' WHERE id = ?",
        (marathon["id"],),
    )
    await bot.db.conn.commit()
    before = await fresh(bot, marathon)
    calls = cog.client.calls

    done = await change_link(bot, bot.guild, FakeActor(), before, f"  {HORARO} ")

    assert done.ok and "reads its schedule from the new link now" in done.message
    after = await fresh(bot, marathon)
    assert after["id"] == before["id"] and after["schedule_url"] == HORARO
    assert (after["source"], after["source_ref"]) == ("horaro", "74")
    assert after["tracked_at"] == before["tracked_at"] and after["thread_id"] == 4242
    assert (after["event_mode"], after["ping_role"], after["spotlight_mode"]) == ("runs", 1, "off")
    assert after["fetch_failures"] == 0 and after["last_error"] is None
    assert cog.client.calls == calls + 1 and after["last_fetch_ok"] == 1
    logged = await details_of(bot.db, "marathon.link_changed")
    assert logged["old"] == {"url": URL, "source": "gdq", "ref": "74"}
    assert logged["new"] == {"url": HORARO, "source": "horaro", "ref": "74"}
    assert "marathon.link_changed" in logkinds.IMPORTANT


async def test_changing_the_link_refuses_in_words_and_changes_nothing(bot, cog):
    marathon = await added(bot, cog)
    other = await create_marathon(
        bot, bot.guild, FakeActor(), name="ESA Summer", url="https://horaro.net/esa/2026-summer2"
    )
    assert other.ok

    unknown = await change_link(bot, bot.guild, FakeActor(), marathon, "https://example.com/x")
    assert unknown.code == "unknown_site" and "horaro.net schedules, Oengus" in unknown.message
    taken = await change_link(
        bot, bot.guild, FakeActor(), marathon, "https://horaro.net/esa/2026-summer2"
    )
    assert taken.code == "duplicate" and taken.status == 409
    assert "**ESA Summer** already follows that schedule" in taken.message
    same = await change_link(bot, bot.guild, FakeActor(), marathon, URL)
    assert same.code == "same_link" and "already reads that link" in same.message
    cog.client.raises = ScheduleError("horaro.net answered 404")
    unreadable = await change_link(bot, bot.guild, FakeActor(), marathon, HORARO)
    assert unreadable.code == "unreadable" and "horaro.net answered 404" in unreadable.message

    assert (await fresh(bot, marathon))["schedule_url"] == URL
    assert "marathon.link_changed" not in await kinds(bot.db)


async def test_hosts_are_found_with_no_switch_anywhere(bot, cog):
    await bot.store.set(GUILD, "marathon_hosts_count_as_ours", True)
    await bot.db.conn.execute(
        "INSERT INTO golive_links(user_id, twitch_login, linked_at) VALUES (?, ?, ?)",
        (55, "hostlogin", at(0)),
    )
    await bot.db.conn.commit()
    cog.client.runs_given = [a_run(1, 30, people=(("Host", "hostlogin", "host"),))]
    marathon = await added(bot, cog)
    assert mt.people_of((await runs_of(bot.db, marathon["id"]))[0])[0]["user_id"] == 55
    assert mt.is_ours((await runs_of(bot.db, marathon["id"]))[0])


# --- renaming: a hand-set name -------------------------------------------------------------


async def test_a_rename_says_so_refuses_an_empty_name_and_a_same_name_changes_nothing(bot, cog):
    marathon = await added(bot, cog)
    wanted = "  AGDQ   2027: Soul Train "
    done = await rename_marathon(bot, bot.guild, FakeActor(), marathon, wanted, None)
    assert done.ok and done.value["name"] == "AGDQ 2027: Soul Train"
    assert done.message == mt.RENAME_SAID.format(old="AGDQ 2027", name="AGDQ 2027: Soul Train")
    assert (await details_of(bot.db, "marathon.updated"))["name"] == "AGDQ 2027: Soul Train"

    soul = "AGDQ 2027: Soul Train"
    same = await rename_marathon(bot, bot.guild, FakeActor(), done.value, soul, None)
    assert same.ok and same.message == ""
    assert (await kinds(bot.db)).count("marathon.updated") == 1

    empty = await rename_marathon(bot, bot.guild, FakeActor(), done.value, "   ", None)
    assert not empty.ok and empty.message == mt.NO_RENAME and empty.status == 422
    assert (await fresh(bot, marathon))["name"] == "AGDQ 2027: Soul Train"


async def test_a_schedule_read_after_a_rename_leaves_the_hand_set_name_alone(bot, cog):
    marathon = await added(bot, cog)
    await rename_marathon(bot, bot.guild, FakeActor(), marathon, "Tuesday: Soul Train", None)
    cog.client.runs_given = [*SCHEDULE[:3], a_run(7, 500, game="New Game")]
    await cog.refresh(bot.guild, await fresh(bot, marathon))
    assert (await details_of(bot.db, "marathon.schedule_changed"))["added"] == 1
    assert (await fresh(bot, marathon))["name"] == "Tuesday: Soul Train"


async def test_a_renamed_board_and_runner_posts_take_the_new_name_on_the_next_follow(bot, cog):
    marathon = await added(bot, cog)
    await cog.follow(bot.guild, await fresh(bot, marathon))
    before = [one.content for one in posts(bot)]
    assert any("AGDQ 2027" in text for text in before)
    await rename_marathon(bot, bot.guild, FakeActor(), marathon, "Tuesday: Soul Train", None)
    await cog.follow(bot.guild, await fresh(bot, marathon))
    after = [one.content for one in posts(bot)]
    assert len(after) == len(before)
    assert any("Tuesday: Soul Train" in text for text in after)
    assert not any("AGDQ 2027" in text for text in after)


# --- a renamed run keeps its row ------------------------------------------------------------


def renamed(run, key, **changes):
    return replace(run, external_id=key, **changes)


async def reread(bot, cog, marathon, runs, minutes=1):
    cog.client.runs_given = list(runs)
    cog.clock = lambda: NOW + timedelta(minutes=minutes)
    read = await cog.refresh(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert read.ok, read.message
    return await runs_of(bot.db, marathon["id"])


async def all_details(bot, kind):
    cur = await bot.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id", (kind,)
    )
    return [json.loads(row["details"]) for row in await cur.fetchall()]


async def last_change(bot):
    found = (await all_details(bot, "marathon.schedule_changed"))[-1]
    return tuple(found[key] for key in ("added", "moved", "dropped", "renamed"))


async def test_an_upcoming_run_of_ours_renamed_keeps_its_row_its_marks_and_its_match(bot, cog):
    marathon = await added(bot, cog)
    before = (await runs_by_game(bot, marathon))["Super Metroid"]
    await update_run(bot.db, before["id"], reminders_sent="[120]", reminder_posts="{}")
    said = len(posts(bot))
    fixed = renamed(SCHEDULE[2], "3b", category="Any% Glitchless")
    rows = await reread(bot, cog, marathon, [*SCHEDULE[:2], fixed, *SCHEDULE[3:]])

    assert len(rows) == 5
    after = (await runs_by_game(bot, marathon))["Super Metroid"]
    assert (after["id"], after["external_id"], after["state"]) == (before["id"], "3b", mt.UPCOMING)
    assert after["category"] == "Any% Glitchless"
    assert (after["reminders_sent"], after["reminder_posts"]) == ("[120]", "{}")
    assert after["first_seen_at"] == before["first_seen_at"]
    assert after["previous_scheduled_at"] is None and after["moved_at"] is None
    assert mt.member_ids(after) == [SKY]
    assert await last_change(bot) == (0, 0, 0, 1)
    (row,) = await all_details(bot, "marathon.run_renamed")
    assert (row["run_id"], row["from_id"], row["to_id"]) == (before["id"], "3", "3b")
    assert (row["game"], row["category"], row["was_category"]) == (
        "Super Metroid",
        "Any% Glitchless",
        "Any%",
    )
    assert len(await all_details(bot, "marathon.run_matched")) == 1
    assert "marathon.member_run_moved" not in await kinds(bot.db)
    assert len(posts(bot)) == said


async def test_a_live_run_renamed_stays_live_with_its_real_start(bot, cog):
    marathon = await added(bot, cog)
    before = (await runs_by_game(bot, marathon))["Super Metroid"]
    real = at(34)
    await update_run(
        bot.db,
        before["id"],
        state=mt.LIVE,
        live_at=real,
        live_because="stream",
        actual_started_at=real,
        shout_message_id=77,
        shout_channel_id=CHANNEL,
    )
    fixed = renamed(SCHEDULE[2], "3b", category="Any% Glitchless")
    await reread(bot, cog, marathon, [*SCHEDULE[:2], fixed, *SCHEDULE[3:]], minutes=40)

    after = (await runs_by_game(bot, marathon))["Super Metroid"]
    kept = ("id", "state", "live_at", "live_because", "actual_started_at", "shout_message_id")
    assert [after[key] for key in kept] == [before["id"], mt.LIVE, real, "stream", real, 77]
    assert after["external_id"] == "3b"
    assert mt.DROPPED not in [one["state"] for one in await runs_of(bot.db, marathon["id"])]
    assert await last_change(bot) == (0, 0, 0, 1)


async def test_a_done_run_renamed_stays_done_and_is_not_added_again(bot, cog):
    marathon = await added(bot, cog)
    before = (await runs_by_game(bot, marathon))["Celeste"]
    await update_run(bot.db, before["id"], state=mt.DONE, done_at=at(0), actual_ended_at=at(0))
    fixed = renamed(SCHEDULE[1], "2b", category="All Red Berries")
    rows = await reread(bot, cog, marathon, [SCHEDULE[0], fixed, *SCHEDULE[2:]])

    after = (await runs_by_game(bot, marathon))["Celeste"]
    assert len(rows) == 5
    assert (after["id"], after["state"], after["done_at"]) == (before["id"], mt.DONE, at(0))
    assert (after["external_id"], after["actual_ended_at"]) == ("2b", at(0))


async def test_a_game_title_changed_in_the_same_slot_is_a_rename(bot, cog):
    marathon = await added(bot, cog)
    before = (await runs_by_game(bot, marathon))["Super Metroid"]
    title = "Super Metroid Redux"
    fixed = renamed(SCHEDULE[2], "3b", game=title, display_name=title)
    await reread(bot, cog, marathon, [*SCHEDULE[:2], fixed, *SCHEDULE[3:]])

    rows = await runs_by_game(bot, marathon)
    assert "Super Metroid" not in rows and rows["Super Metroid Redux"]["id"] == before["id"]
    assert mt.member_ids(rows["Super Metroid Redux"]) == [SKY]


async def test_another_runner_in_the_same_slot_is_a_drop_and_an_add_as_before(bot, cog):
    marathon = await added(bot, cog)
    before = (await runs_by_game(bot, marathon))["Super Metroid"]
    other = renamed(SCHEDULE[2], "3b", people=(Person("Ash", "ashruns", "runner"),))
    rows = await reread(bot, cog, marathon, [*SCHEDULE[:2], other, *SCHEDULE[3:]])

    assert len(rows) == 6
    by_key = {row["external_id"]: row for row in rows}
    assert (by_key["3"]["id"], by_key["3"]["state"]) == (before["id"], mt.DROPPED)
    assert by_key["3b"]["state"] == mt.UPCOMING and by_key["3b"]["id"] != before["id"]
    assert await last_change(bot) == (1, 0, 1, 0)
    assert await all_details(bot, "marathon.run_renamed") == []


async def test_a_rename_beside_an_unrelated_add_is_counted_as_one_of_each(bot, cog):
    marathon = await added(bot, cog)
    fixed = renamed(SCHEDULE[2], "3b", category="Any% Glitchless")
    extra = a_run(6, 400, game="New Game", people=(("Ash", None, "runner"),))
    rows = await reread(bot, cog, marathon, [*SCHEDULE[:2], fixed, *SCHEDULE[3:], extra])

    assert len(rows) == 6
    assert await last_change(bot) == (1, 0, 0, 1)


async def test_two_runs_swapping_slots_are_moved_and_never_renamed(bot, cog):
    marathon = await added(bot, cog)
    ids = {row["external_id"]: row["id"] for row in await runs_of(bot.db, marathon["id"])}
    third, fourth = SCHEDULE[2], SCHEDULE[3]
    swapped = [
        *SCHEDULE[:2],
        replace(fourth, order=3, starts_at=third.starts_at, ends_at=third.ends_at),
        replace(third, order=4, starts_at=fourth.starts_at, ends_at=fourth.ends_at),
        SCHEDULE[4],
    ]
    rows = await reread(bot, cog, marathon, swapped)

    assert {row["external_id"]: row["id"] for row in rows} == ids
    assert await last_change(bot) == (0, 2, 0, 0)


async def test_a_tracker_id_that_changes_in_the_same_slot_keeps_the_row(bot, cog):
    marathon = await added(bot, cog)
    before = (await runs_by_game(bot, marathon))["Kirby Air Riders"]
    read = [*SCHEDULE[:3], renamed(SCHEDULE[3], "9104"), SCHEDULE[4]]
    rows = await reread(bot, cog, marathon, read)

    after = (await runs_by_game(bot, marathon))["Kirby Air Riders"]
    assert len(rows) == 5 and (after["id"], after["external_id"]) == (before["id"], "9104")


def repeat(key, order, start, category="Any%"):
    run = a_run(order, start, game="Tetris", people=(("Sky", "skyruns", "runner"),))
    return replace(run, external_id=key, category=category)


async def test_the_first_of_two_repeats_renamed_leaves_both_rows_where_they_were(bot, cog):
    cog.client.runs_given = [repeat("tetris/any", 1, 30), repeat("tetris/any#2", 2, 120)]
    marathon = await added(bot, cog)
    first, second = await runs_of(bot.db, marathon["id"])
    read = [repeat("tetris/any-b", 1, 30, "Any% B"), repeat("tetris/any", 2, 120)]
    rows = await reread(bot, cog, marathon, read)

    assert [(row["id"], row["external_id"], row["scheduled_at"], row["state"]) for row in rows] == [
        (first["id"], "tetris/any-b", at(30), mt.UPCOMING),
        (second["id"], "tetris/any", at(120), mt.UPCOMING),
    ]
    assert rows[0]["category"] == "Any% B" and rows[1]["previous_scheduled_at"] is None
    assert await last_change(bot) == (0, 0, 0, 2)


async def test_a_flip_back_to_the_old_spelling_renames_the_same_row_again(bot, cog):
    marathon = await added(bot, cog)
    before = (await runs_by_game(bot, marathon))["Super Metroid"]
    fixed = renamed(SCHEDULE[2], "3b", category="Any% Glitchless")
    await reread(bot, cog, marathon, [*SCHEDULE[:2], fixed, *SCHEDULE[3:]])
    rows = await reread(bot, cog, marathon, SCHEDULE, minutes=2)

    after = (await runs_by_game(bot, marathon))["Super Metroid"]
    assert len(rows) == 5
    assert (after["id"], after["external_id"], after["category"]) == (before["id"], "3", "Any%")
    assert len(await all_details(bot, "marathon.run_renamed")) == 2


async def test_a_flip_back_onto_an_id_a_dropped_row_holds_keeps_the_live_row(bot, cog):
    marathon = await added(bot, cog)
    old = (await runs_by_game(bot, marathon))["Super Metroid"]
    await update_run(bot.db, old["id"], state=mt.DROPPED)
    await bot.db.conn.execute(
        "INSERT INTO marathon_runs(marathon_id, external_id, order_no, game, display_name, "
        "category, runners_text, people, scheduled_at, ends_at, sheet_at, sheet_ends_at, state, "
        "live_at, actual_started_at, first_seen_at, last_seen_at) "
        "SELECT marathon_id, '3b', order_no, game, display_name, 'Any% Glitchless', runners_text, "
        "people, scheduled_at, ends_at, sheet_at, sheet_ends_at, 'live', ?, ?, ?, ? "
        "FROM marathon_runs WHERE id = ?",
        (at(34), at(34), at(34), at(34), old["id"]),
    )
    await bot.db.conn.commit()
    fixed = renamed(SCHEDULE[2], "3b", category="Any% Glitchless")
    rows = await reread(bot, cog, marathon, [*SCHEDULE[:2], fixed, *SCHEDULE[3:]], minutes=39)
    live = next(one for one in rows if one["external_id"] == "3b")
    assert (live["state"], old["id"] != live["id"]) == (mt.LIVE, True)
    rows = await reread(bot, cog, marathon, SCHEDULE, minutes=40)

    by_id = {row["id"]: row for row in rows}
    assert len(rows) == 6
    assert (by_id[live["id"]]["external_id"], by_id[live["id"]]["state"]) == ("3", mt.LIVE)
    assert (by_id[live["id"]]["actual_started_at"], by_id[live["id"]]["category"]) == (
        at(34),
        "Any%",
    )
    assert (by_id[old["id"]]["external_id"], by_id[old["id"]]["state"]) == ("3b", mt.DROPPED)
    assert await last_change(bot) == (0, 0, 0, 1)
    assert not [row for row in rows if row["external_id"].startswith("~")]


async def test_a_rekey_that_fails_leaves_every_id_as_it_was(bot, cog):
    marathon = await added(bot, cog)
    first, second = (await runs_of(bot.db, marathon["id"]))[:2]
    with pytest.raises(Exception, match="UNIQUE"):
        await cogmod.rekey_runs(bot.db, [(first, "x"), (second, "x")])
    rows = await runs_of(bot.db, marathon["id"])
    assert [row["external_id"] for row in rows[:2]] == ["1", "2"]




def dkc2(key, order, start, category):
    run = a_run(order, start, game="Donkey Kong Country 2", people=(("Sky", "skyruns", "runner"),))
    return replace(run, external_id=key, category=category)


@pytest.mark.parametrize("state", [mt.UPCOMING, mt.LIVE, mt.DONE])
async def test_a_run_retitled_as_the_one_before_it_is_deleted_is_a_new_row(bot, cog, state):
    cog.client.runs_given = [
        dkc2("dkc2/102", 1, 30, "102%"),
        dkc2("dkc2/endng", 2, 90, "True Endng"),
    ]
    marathon = await added(bot, cog)
    first, second = await runs_of(bot.db, marathon["id"])
    await update_run(
        bot.db,
        first["id"],
        state=state,
        reminders_sent="[120]",
        actual_started_at=None if state == mt.UPCOMING else at(31),
    )
    rows = await reread(bot, cog, marathon, [dkc2("dkc2/ending", 1, 30, "True Ending")])

    by_key = {row["external_id"]: row for row in rows}
    assert len(rows) == 3 and await all_details(bot, "marathon.run_renamed") == []
    kept = by_key["dkc2/102"]
    assert (kept["id"], kept["category"], kept["reminders_sent"]) == (first["id"], "102%", "[120]")
    assert kept["state"] == (mt.DONE if state == mt.DONE else mt.DROPPED)
    assert (by_key["dkc2/endng"]["id"], by_key["dkc2/endng"]["state"]) == (second["id"], mt.DROPPED)
    new = by_key["dkc2/ending"]
    assert new["id"] not in (first["id"], second["id"])
    assert (new["state"], new["actual_started_at"], new["reminders_sent"]) == (
        mt.UPCOMING,
        None,
        "[]",
    )
    assert await last_change(bot) == (1, 0, 1 if state == mt.DONE else 2, 0)
