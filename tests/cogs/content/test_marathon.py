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
    FakeGuild,
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
    board = [one for one in posts(bot) if "our people" in one.content]
    assert len(board) == 1 and board[0].pinned
    assert "Super Metroid" in board[0].content and "<@9001>" in board[0].content
    assert board[0].kwargs["allowed_mentions"].users is False
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert len([one for one in posts(bot) if "our people" in one.content]) == 1
    await pair_runner(bot, bot.guild, FakeActor(), marathon, "Interview Crew", 42, everywhere=False)
    assert "Blaster Master" in board[0].content and "<@42>" in board[0].content
    assert (await kinds(bot.db)).count("marathon.board_posted") == 1
    assert "marathon.board_refreshed" in await kinds(bot.db)


async def test_the_board_comes_down_a_day_after_the_end(bot, cog):
    marathon = await added(bot, cog)
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    board = next(one for one in posts(bot) if "our people" in one.content)
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
    assert "Nobody from here" in posts(bot)[0].content


# --- reminders ------------------------------------------------------------------------------


async def reminders(bot):
    return [
        one
        for one in posts(bot)
        if "our people" not in one.content and "right now" not in one.content
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
        bot, bot.guild, FakeActor(), name="ESA", url="https://horaro.net/esa/2027"
    )
    assert other.code == "unknown_site" and "GDQ schedule only" in other.message
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

    assert "Ours next" in embed.description and "Super Metroid" in embed.description
    assert "<@9001>" in embed.description
    labels = [getattr(one, "label", None) for one in view.children]
    assert "Add a marathon…" not in labels and "Logs" not in labels
    assert "My runs" in labels
    assert not any(isinstance(one, cogmod.MarathonPick) for one in view.children)
    assert view.render_again is not None


async def test_staff_see_every_marathon_with_its_read_state_and_the_moves(bot, cog):
    await added(bot, cog)
    embed, view = await cogmod.build_panel(bot, bot.guild, FakeActor())
    assert "AGDQ 2027" in embed.description and "ours 1 of 5" in embed.description
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
    assert "Resume" in labels and "Refresh now" not in labels


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
    board = next(one for one in posts(bot) if "our people" in one.content)
    assert board.pinned
    await bot.store.set(GUILD, "marathon_mode", "off")
    cog.clock = lambda: NOW + timedelta(days=2)
    await cog.tick_once()
    assert board.pinned is False
