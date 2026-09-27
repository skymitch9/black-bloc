from datetime import UTC, datetime, timedelta

from black_bloc.cogs.content.marathon import get_marathon, refresh_marathon, update_marathon
from black_bloc.cogs.content.marathon_spotlight import (
    after_staff_dim,
    follow_spotlight,
    set_spotlight_mode,
    settle_held,
)
from black_bloc.cogs.content.spotlight import (
    Spotlight,
    change_spotlight,
    channel_by_id,
    run_spotlight_move,
    spotlight_channel,
    update_channel,
)
from tests.cogs.content.test_marathon import (  # noqa: F401
    NOW,
    a_run,
    added,
    at,
    bot,
    cog,
    gdq_row,
)
from tests.cogs.content.test_spotlight import GUILD, FakeActor, details_of, kinds


async def quiet_row(bot, login="rpglimitbreak"):  # noqa: F811
    outcome, row = await spotlight_channel(
        bot, bot.guild, FakeActor(), login, keep=True, spotlight=False
    )
    assert outcome == "added"
    return row


async def count(bot, kind):  # noqa: F811
    return (await kinds(bot.db)).count(kind)


async def test_a_fetch_on_a_running_marathon_spotlights_its_channel_until_the_end_once(bot, cog):  # noqa: F811
    row = await quiet_row(bot)
    marathon = await added(bot, cog, channel=row)

    fresh = await channel_by_id(bot.db, row["id"])
    assert fresh["spotlight"] == 1
    assert fresh["expires_at"] == at(270)
    assert fresh["spotlit_by_marathon"] == marathon["id"]
    assert fresh["starts_at"] is None
    said = await details_of(bot.db, "marathon.spotlight_set")
    assert said["marathon_id"] == marathon["id"] and said["span_ends_at"] == at(210)
    assert said["expires_at"] == at(270) and said["tail_minutes"] == 60
    assert said["span_starts_at"] == at(-120) and said["from_expires_at"] is None

    await refresh_marathon(bot, bot.guild, marathon)
    await cog.tick_marathon(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert await count(bot, "marathon.spotlight_set") == 1
    assert await count(bot, "marathon.spotlight_extended") == 0


async def test_a_kept_spotlight_like_gdq_is_never_touched(bot, cog):  # noqa: F811
    row = await gdq_row(bot)
    await added(bot, cog, channel=row)

    fresh = await channel_by_id(bot.db, row["id"])
    assert (fresh["spotlight"], fresh["expires_at"], fresh["spotlit_by_marathon"]) == (
        1,
        None,
        None,
    )
    assert await count(bot, "marathon.spotlight_set") == 0


async def test_a_later_expiry_stays_and_an_earlier_one_is_carried_to_the_end(bot, cog):  # noqa: F811
    later = at(9999)
    row = await quiet_row(bot, "speedstuff4charity")
    await update_channel(bot.db, row["id"], spotlight=1, expires_at=later)
    marathon = await added(bot, cog, channel=row)
    assert (await channel_by_id(bot.db, row["id"]))["expires_at"] == later
    assert await count(bot, "marathon.spotlight_extended") == 0

    await update_channel(bot.db, row["id"], expires_at=at(30))
    await refresh_marathon(bot, bot.guild, marathon)
    fresh = await channel_by_id(bot.db, row["id"])
    assert fresh["expires_at"] == at(270) and fresh["spotlit_by_marathon"] is None
    said = await details_of(bot.db, "marathon.spotlight_extended")
    assert said["from_expires_at"] == at(30) and said["marathon_id"] == marathon["id"]
    assert await count(bot, "marathon.spotlight_set") == 0


async def test_a_marathon_further_off_than_the_lead_waits_for_the_tick(bot, cog):  # noqa: F811
    cog.client.runs_given = [a_run(1, 40), a_run(2, 100)]
    row = await quiet_row(bot)
    marathon = await added(bot, cog, channel=row)
    assert (await channel_by_id(bot.db, row["id"]))["spotlight"] == 0

    cog.clock = lambda: NOW + timedelta(minutes=26)
    await cog.tick_marathon(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    fresh = await channel_by_id(bot.db, row["id"])
    assert fresh["spotlight"] == 1 and fresh["expires_at"] == at(220)


async def test_the_key_off_an_opted_out_channel_and_marathon_mode_off_leave_the_row(bot, cog):  # noqa: F811
    await bot.store.set(GUILD, "marathon_spotlight", False)
    row = await quiet_row(bot)
    marathon = await added(bot, cog, channel=row)
    assert (await channel_by_id(bot.db, row["id"]))["spotlight"] == 0

    await bot.store.set(GUILD, "marathon_spotlight", True)
    await update_channel(bot.db, row["id"], marathons=0)
    fresh = await get_marathon(bot.db, GUILD, marathon["id"])
    assert await follow_spotlight(bot, bot.guild, fresh, NOW) is None

    await update_channel(bot.db, row["id"], marathons=1)
    await bot.store.set(GUILD, "marathon_mode", "off")
    assert await follow_spotlight(bot, bot.guild, fresh, NOW) is None
    await bot.store.set(GUILD, "marathon_mode", "shadow")
    assert await follow_spotlight(bot, bot.guild, fresh, NOW) == "set"


async def test_staff_turning_it_off_during_the_span_stops_that_marathon_for_good(bot, cog):  # noqa: F811
    row = await quiet_row(bot)
    marathon = await added(bot, cog, channel=row)

    said, _ = await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "spotlight_off")

    assert "**AGDQ 2027** will not spotlight it again." in said
    assert (await get_marathon(bot.db, GUILD, marathon["id"]))["spotlight_mode"] == "off"
    fresh = await channel_by_id(bot.db, row["id"])
    assert (fresh["spotlight"], fresh["expires_at"], fresh["spotlit_by_marathon"]) == (
        0,
        None,
        None,
    )
    set_off = await details_of(bot.db, "marathon.spotlight_mode_set")
    assert set_off["because"] == "staff_turned_the_spotlight_off" and set_off["to"] == "off"

    await refresh_marathon(bot, bot.guild, marathon)
    await cog.tick_marathon(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert (await channel_by_id(bot.db, row["id"]))["spotlight"] == 0


async def test_staff_turning_off_a_spotlight_no_marathon_is_running_changes_no_marathon(bot, cog):  # noqa: F811
    cog.client.runs_given = [a_run(1, 600), a_run(2, 700)]
    row = await quiet_row(bot)
    marathon = await added(bot, cog, channel=row)
    await update_channel(bot.db, row["id"], spotlight=1)

    was = await channel_by_id(bot.db, row["id"])
    await update_channel(bot.db, row["id"], spotlight=0)
    stopped = await after_staff_dim(
        bot, bot.guild, FakeActor(), was, await channel_by_id(bot.db, row["id"])
    )
    assert stopped == ""
    assert (await get_marathon(bot.db, GUILD, marathon["id"]))["spotlight_mode"] is None


async def test_the_expiry_sweep_gives_a_marathon_spotlight_back_and_purges_nothing(bot, cog):  # noqa: F811
    sweeper = Spotlight(bot)
    bot.cogs["Spotlight"] = sweeper
    row = await quiet_row(bot)
    marathon = await added(bot, cog, channel=row)
    gone = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    await update_channel(bot.db, row["id"], expires_at=gone)
    cog.clock = lambda: NOW + timedelta(minutes=271)

    await sweeper.sweep_expiries(bot.guild)

    fresh = await channel_by_id(bot.db, row["id"])
    assert fresh is not None
    assert (fresh["spotlight"], fresh["expires_at"], fresh["spotlit_by_marathon"]) == (
        0,
        None,
        None,
    )
    lifted = await details_of(bot.db, "marathon.spotlight_lifted")
    assert lifted["marathon_id"] == marathon["id"] and lifted["because"] == "marathon_over"
    assert await count(bot, "golive.spotlight_expired") == 0


async def test_staff_dates_on_a_marathon_spotlight_make_it_theirs(bot, cog):  # noqa: F811
    row = await quiet_row(bot)
    await added(bot, cog, channel=row)
    await change_spotlight(bot, bot.guild, FakeActor(), row["id"], expires_at=at(5000))
    assert (await channel_by_id(bot.db, row["id"]))["spotlit_by_marathon"] is None


async def test_the_mode_switch_lifts_its_own_spotlight_and_follows_again(bot, cog):  # noqa: F811
    row = await quiet_row(bot)
    marathon = await added(bot, cog, channel=row)

    off = await set_spotlight_mode(bot, bot.guild, FakeActor(), marathon, "off")
    assert off.ok and "no longer spotlights its channel" in off.message
    fresh = await channel_by_id(bot.db, row["id"])
    assert (fresh["spotlight"], fresh["spotlit_by_marathon"]) == (0, None)
    assert (await details_of(bot.db, "marathon.spotlight_lifted"))["because"] == "mode_off"

    same = await set_spotlight_mode(bot, bot.guild, FakeActor(), marathon, "off")
    assert same.ok and "already has that" in same.message
    bad = await set_spotlight_mode(bot, bot.guild, FakeActor(), marathon, "often")
    assert not bad.ok and bad.code == "bad_spotlight_mode"

    on = await set_spotlight_mode(bot, bot.guild, FakeActor(), marathon, "on")
    assert on.ok and "from 15 minutes before" in on.message
    assert (await channel_by_id(bot.db, row["id"]))["spotlight"] == 1


async def test_a_new_marathon_channel_row_pings_only_inside_windows_by_default(bot, cog):  # noqa: F811
    assert (await quiet_row(bot, "fastestfurs"))["ping_mode"] == "events"
    assert (await quiet_row(bot, "somestreamer"))["ping_mode"] == "always"
    await bot.store.set(GUILD, "marathon_channel_ping_mode_default", "never")
    assert (await quiet_row(bot, "ladyarcaders"))["ping_mode"] == "never"


# --- marathon-controls B: the spotlight follows the CURRENT span, plus a tail -----------------


async def test_a_run_appended_past_the_end_keeps_it_spotlit_to_new_end_plus_60(bot, cog):  # noqa: F811
    row = await quiet_row(bot)
    marathon = await added(bot, cog, channel=row)
    assert (await channel_by_id(bot.db, row["id"]))["expires_at"] == at(270)

    cog.client.runs_given = [*cog.client.runs_given, a_run(6, 300)]
    await refresh_marathon(bot, bot.guild, marathon)
    await refresh_marathon(bot, bot.guild, marathon)

    fresh = await channel_by_id(bot.db, row["id"])
    assert fresh["expires_at"] == at(420) and fresh["spotlit_by_marathon"] == marathon["id"]
    assert await count(bot, "marathon.spotlight_extended") == 1
    said = await details_of(bot.db, "marathon.spotlight_extended")
    assert said["from_expires_at"] == at(270) and said["held"] is True
    assert said["span_ends_at"] == at(360) and said["tail_minutes"] == 60

    cog.clock = lambda: NOW + timedelta(minutes=365)
    assert await settle_held(bot, bot.guild, fresh) == "kept"
    cog.clock = lambda: NOW + timedelta(minutes=421)
    assert await settle_held(bot, bot.guild, fresh) == "lifted"
    assert (await channel_by_id(bot.db, row["id"]))["spotlight"] == 0


async def test_the_lift_fires_at_end_plus_tail_not_at_the_end(bot, cog):  # noqa: F811
    row = await quiet_row(bot)
    marathon = await added(bot, cog, channel=row)

    cog.clock = lambda: NOW + timedelta(minutes=215)
    await cog.tick_marathon(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    fresh = await channel_by_id(bot.db, row["id"])
    assert fresh["spotlight"] == 1 and fresh["expires_at"] == at(270)
    assert await settle_held(bot, bot.guild, fresh) == "kept"
    assert await count(bot, "marathon.spotlight_lifted") == 0

    cog.clock = lambda: NOW + timedelta(minutes=270)
    assert await settle_held(bot, bot.guild, fresh) == "lifted"
    assert (await details_of(bot.db, "marathon.spotlight_lifted"))["because"] == "marathon_over"


async def test_tail_zero_is_the_v174_end(bot, cog):  # noqa: F811
    await bot.store.set(GUILD, "marathon_spotlight_tail_minutes", 0)
    row = await quiet_row(bot)
    await added(bot, cog, channel=row)
    fresh = await channel_by_id(bot.db, row["id"])
    assert fresh["expires_at"] == at(210)
    cog.clock = lambda: NOW + timedelta(minutes=210)
    assert await settle_held(bot, bot.guild, fresh) == "lifted"


async def test_the_sweep_reads_the_current_span_and_extends_instead_of_lifting(bot, cog):  # noqa: F811
    sweeper = Spotlight(bot)
    bot.cogs["Spotlight"] = sweeper
    row = await quiet_row(bot)
    marathon = await added(bot, cog, channel=row)
    await update_marathon(bot.db, marathon["id"], ends_at=at(400))
    gone = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    await update_channel(bot.db, row["id"], expires_at=gone)
    cog.clock = lambda: NOW + timedelta(minutes=280)

    await sweeper.sweep_expiries(bot.guild)

    fresh = await channel_by_id(bot.db, row["id"])
    assert fresh["spotlight"] == 1 and fresh["expires_at"] == at(460)
    assert fresh["spotlit_by_marathon"] == marathon["id"]
    assert await count(bot, "marathon.spotlight_lifted") == 0
    assert await count(bot, "marathon.spotlight_extended") == 1
