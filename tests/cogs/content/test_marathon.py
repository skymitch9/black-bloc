import json
from datetime import UTC, datetime, timedelta

import pytest

from black_bloc import marathon as mt
from black_bloc.cogs.content import marathon as cogmod
from black_bloc.cogs.content.marathon import (
    Marathons,
    create_marathon,
    get_marathon,
    mark_done,
    pair_runner,
    post_board,
    remove_marathon,
    runs_of,
    set_active,
    set_channel,
    shout_now,
    unpair_runner,
)
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


class FakeClient:
    def __init__(self, runs=None, raises=None):
        self.runs_given = list(runs if runs is not None else SCHEDULE)
        self.raises = raises
        self.calls = 0

    async def resolve(self, source, ref):
        if self.raises is not None and not self.raises.unpublished:
            raise self.raises
        return ("74", "Awesome Games Done Quick 2027")

    async def runs(self, source, ref):
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
    await store.set(GUILD, "spotlight_mode", "on")
    await db.conn.execute(
        "INSERT INTO golive_links(user_id, twitch_login, linked_at) VALUES (?, ?, ?)",
        (SKY, "skyruns", at(-9999)),
    )
    await db.conn.commit()
    made = FakeBot(db, store, settings, FakeGuild())
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
    return outcome.value


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


# --- the cadence ----------------------------------------------------------------------------


async def test_a_near_marathon_is_read_every_poll_gap_and_a_far_one_is_not(bot, cog):
    marathon = await added(bot, cog)
    calls = cog.client.calls
    cog.clock = lambda: NOW + timedelta(minutes=10)
    await cog.tick_marathon(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert cog.client.calls == calls
    cog.clock = lambda: NOW + timedelta(minutes=31)
    await cog.tick_marathon(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert cog.client.calls == calls + 1


async def test_a_far_marathon_waits_the_far_gap(bot, cog):
    cog.client.runs_given = [a_run(1, 60 * 24 * 40)]
    marathon = await added(bot, cog)
    calls = cog.client.calls
    cog.clock = lambda: NOW + timedelta(hours=5)
    await cog.tick_marathon(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert cog.client.calls == calls
    cog.clock = lambda: NOW + timedelta(hours=25)
    await cog.tick_marathon(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert cog.client.calls == calls + 1


# --- the board ------------------------------------------------------------------------------


async def test_the_board_posts_once_pinned_then_edits_in_place(bot, cog):
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
        if "BaF on the schedule" not in one.content and "right now" not in one.content
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
    channel = await gdq_row(bot)
    marathon = await added(bot, cog, channel=channel)
    await set_active(bot, bot.guild, FakeActor(), marathon, False)
    assert await windows_for(bot.db, channel["id"]) == []
    await set_active(bot, bot.guild, FakeActor(), marathon, True)
    assert len(await windows_for(bot.db, channel["id"])) == 1
    await remove_marathon(bot, bot.guild, FakeActor(), marathon)
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
        bot, bot.guild, FakeActor(), name="ESA", url="https://oengus.io/marathon/LSS26/schedule"
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


async def test_the_card_draws_only_the_moves_that_change_something(bot, cog):
    marathon = await added(bot, cog)
    _, view = await cogmod.build_card(bot, bot.guild, marathon["id"])
    labels = [getattr(one, "label", None) for one in view.children]
    assert "Pause" in labels and "Resume" not in labels
    assert "Post the board" in labels and "Pair a runner…" in labels
    await set_active(bot, bot.guild, FakeActor(), marathon, False)
    _, view = await cogmod.build_card(bot, bot.guild, marathon["id"])
    labels = [getattr(one, "label", None) for one in view.children]
    assert "Resume" in labels and "Read it now" not in labels


async def test_the_card_reads_schedule_runs_event_channel_posts_in_that_order(bot, cog):
    marathon = await added(bot, cog)
    embed, _ = await cogmod.build_card(bot, bot.guild, marathon["id"])
    lines = embed.description.splitlines()
    heads = ["**Schedule:**", mt.CARD_RUNS, mt.CARD_EVENT, "**Channel:**", "**Posts:**"]
    found = [next(at for at, one in enumerate(lines) if one.startswith(head)) for head in heads]
    assert found == sorted(found) and found[0] == 1
    assert "GDQ tracker" in lines[1] and "last read <t:" in lines[1]
    assert "next read <t:" in lines[1] and "BaF" in lines[1]


async def test_pairing_from_the_panel_picks_a_schedule_name_then_the_member(bot, cog):
    marathon = await added(bot, cog)
    _, view = await cogmod.build_card(
        bot, bot.guild, marathon["id"], pairing=True, runner="Interview Crew"
    )
    names = next(one for one in view.children if isinstance(one, cogmod.NamePick))
    assert "Interview Crew" in [option.value for option in names.options]
    await pair_runner(bot, bot.guild, FakeActor(), marathon, view.runner, 77)
    assert mt.member_ids((await runs_by_game(bot, marathon))["Blaster Master"]) == [77]


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
    bot.guild.channels[STAFF_ROOM] = FakeChannel(STAFF_ROOM)
    await bot.store.set(GUILD, "staff_channel_id", STAFF_ROOM)


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
    notices = posts(bot, STAFF_ROOM)
    assert len(notices) == 1 and cog.client.event_calls == 1
    assert "AGDQ 2027 is over" in notices[0].content
    assert "**Summer Games Done Quick 2027**" in notices[0].content
    assert record["notice_message_id"] == notices[0].id
    view = notices[0].kwargs["view"]
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
    assert cog.client.event_calls == 0 and posts(bot, STAFF_ROOM) == []


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
    assert len(posts(bot, STAFF_ROOM)) == 1


async def test_nothing_ahead_is_a_none_record_and_is_not_asked_again(bot, cog, over):
    cog.client.events_given = [AGDQ]
    await cog.tick_once()
    record = await record_now(bot, over)
    assert record["event_id"] is None and mt.next_state(record) == mt.NEXT_NONE
    assert "marathon.next_none" in await kinds(bot.db)
    assert posts(bot, STAFF_ROOM) == []
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
    notice = posts(bot, STAFF_ROOM)[0]
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
    assert len(posts(bot, STAFF_ROOM)) == 1


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
    notice = posts(bot, STAFF_ROOM)[0]
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
    assert mt.next_state(record) == mt.NEXT_ADDED and posts(bot, STAFF_ROOM) == []


async def test_shadow_sends_the_notice_to_the_shadow_home_as_would_suggest(bot, cog, over):
    await bot.store.set(GUILD, "marathon_mode", "shadow")
    await cog.tick_once()
    assert posts(bot, STAFF_ROOM) == []
    shadowed = [one for one in posts(bot, SHADOW_CHANNEL) if "is over" in one.content]
    assert len(shadowed) == 1 and f"<#{STAFF_ROOM}>" in shadowed[0].content
    found = await kinds(bot.db)
    assert "marathon.would_suggest_next" in found and "marathon.next_suggested" not in found


async def test_no_staff_channel_is_a_failed_notice_row_and_the_record_stays(bot, cog, over):
    await bot.store.clear(GUILD, "staff_channel_id")
    await cog.tick_once()
    assert mt.next_state(await record_now(bot, over)) == mt.NEXT_OPEN
    failed = await details_of(bot.db, "marathon.next_notice_failed")
    assert "staff_channel_id" in failed["reason"]


async def test_the_notice_buttons_are_staff_only_and_rebuild_from_their_custom_id(bot, cog, over):
    await cog.tick_once()
    notice = posts(bot, STAFF_ROOM)[0]
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


async def test_the_panel_card_offers_next_up_and_the_next_view_its_three_moves(bot, cog, over):
    await cog.tick_once()
    embed, view = await cogmod.build_card(bot, bot.guild, over["id"])
    labels = [getattr(one, "label", None) for one in view.children]
    assert "Next up…" in labels and "Re-read every…" in labels
    assert "Summer Games Done Quick 2027" in embed.description
    embed, view = await cogmod.build_next(bot, bot.guild, over["id"])
    labels = [getattr(one, "label", None) for one in view.children]
    assert labels == ["Add it", "Not this one", "Look again", "Back"]
    cog.clock = lambda: NOW
    _, view = await cogmod.build_card(bot, bot.guild, over["id"])
    assert "Next up…" not in [getattr(one, "label", None) for one in view.children]


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

    await remove_marathon(bot, bot.guild, FakeActor(), marathon)
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

    await remove_marathon(bot, bot.guild, FakeActor(), marathon)

    assert (await get_event(bot.db, event["id"]))["status"] == "denied"
    assert "marathon.event_cancelled" not in await kinds(bot.db)


async def test_pausing_does_nothing_to_the_event(bot, cog, proposals):
    outcome = await with_event(bot, cog)
    marathon, event = await event_of(bot, outcome.value)
    await set_active(bot, bot.guild, FakeActor(), marathon, False)
    fresh, again = await event_of(bot, marathon)
    assert again["status"] == "pending" and fresh["event_id"] == event["id"]


async def test_the_card_says_the_event_and_draws_unlink_or_make_one_now(bot, cog, proposals):
    outcome = await with_event(bot, cog)
    marathon, event = await event_of(bot, outcome.value)
    embed, view = await cogmod.build_card(bot, bot.guild, marathon["id"])
    labels = [getattr(one, "label", None) for one in view.children]
    assert f"Event **#{event['id']}** — pending" in embed.description
    assert mt.UNLINK_EVENT_MOVE.label in labels and mt.MAKE_EVENT_MOVE.label not in labels

    await cogmod.unlink_the_event(bot, bot.guild, FakeActor(), marathon)
    embed, view = await cogmod.build_card(bot, bot.guild, marathon["id"])
    labels = [getattr(one, "label", None) for one in view.children]
    assert mt.EVENT_NONE_LINE in embed.description
    assert mt.MAKE_EVENT_MOVE.label in labels and mt.UNLINK_EVENT_MOVE.label not in labels


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
