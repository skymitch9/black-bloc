# ruff: noqa: F401, F811
import re
from datetime import timedelta

import discord

from black_bloc import marathon_retime as rt
from black_bloc import marathon_thread_controls as mtc
from black_bloc.cogs.content import marathon_retime as retime
from black_bloc.cogs.content import marathon_signals as signals
from black_bloc.cogs.content import marathon_thread_controls as controls
from black_bloc.cogs.content.marathon import get_marathon, mark_live
from black_bloc.golive import parse_ts
from black_bloc.marathon_signals import sheet_end, sheet_start
from tests.cogs.content.test_marathon import GUILD, bot, cog
from tests.cogs.content.test_marathon_signals import (
    HAMTARO,
    KIRBY,
    SPYRO,
    WARIO,
    at_show,
    gdqueer,
    helix,
    stream,
    tick,
    times,
    z,
)
from tests.cogs.content.test_spotlight import FakeActor, FakeInteraction, details_of, kinds


async def show(bot, cog, helix):
    channel, marathon = await gdqueer(bot, cog)
    await tick(cog)
    return channel, marathon


async def test_set_start_anchors_the_run_and_the_rest_of_its_day_walks_after_it(bot, cog, helix):
    _channel, marathon = await show(bot, cog, helix)
    before = await times(bot, marathon)
    length = (sheet_end(before[HAMTARO]) - sheet_start(before[HAMTARO])) // timedelta(minutes=1)

    done = await retime.set_start(
        bot, bot.guild, FakeActor(), marathon, before[HAMTARO], z(90), "UTC"
    )

    assert done.ok, done.message
    rows = await times(bot, marathon)
    assert rows[HAMTARO]["staff_start_at"] == z(90) and rows[HAMTARO]["scheduled_at"] == z(90)
    assert rows[HAMTARO]["staff_start_by"] == FakeActor.id
    assert rows[KIRBY]["scheduled_at"] == z(90 + length)
    assert rows[SPYRO]["scheduled_at"] == before[SPYRO]["scheduled_at"]
    assert "**Hamtaro: Ham-Hams Unite!** now starts at <t:" in done.message
    said = await details_of(bot.db, "marathon.start_set")
    assert (said["run_id"], said["from"], said["to"]) == (rows[HAMTARO]["id"], z(68), z(90))
    assert said["minutes"] is None and said["actor"] == FakeActor.id and said["via"] == "discord"
    assert (await details_of(bot.db, "marathon.retimed"))["because"] == "staff"


async def test_shift_the_day_is_a_start_at_its_current_time_plus_the_minutes(bot, cog, helix):
    _channel, marathon = await show(bot, cog, helix)
    before = await times(bot, marathon)
    was = parse_ts(before[KIRBY]["scheduled_at"])

    done = await retime.shift_day(bot, bot.guild, FakeActor(), marathon, before[KIRBY], "+10")

    assert done.ok, done.message
    rows = await times(bot, marathon)
    assert parse_ts(rows[KIRBY]["staff_start_at"]) == was + timedelta(minutes=10)
    assert rows[HAMTARO]["staff_start_at"] is None
    assert rows[WARIO]["scheduled_at"] > before[WARIO]["scheduled_at"]
    said = await details_of(bot.db, "marathon.day_shifted")
    assert (said["minutes"], said["run_id"]) == (10, rows[KIRBY]["id"])
    assert "moved +10 min" in done.message


async def test_a_real_start_later_beats_the_staff_start(bot, cog, helix):
    _channel, marathon = await show(bot, cog, helix)
    hamtaro = (await times(bot, marathon))[HAMTARO]
    assert (await retime.set_start(bot, bot.guild, FakeActor(), marathon, hamtaro, z(90), "UTC")).ok

    at_show(cog, 80)
    assert (await mark_live(bot, bot.guild, FakeActor(), marathon, hamtaro)).ok

    rows = await times(bot, marathon)
    assert rows[HAMTARO]["actual_started_at"] == z(80) and rows[HAMTARO]["scheduled_at"] == z(80)


async def test_back_to_the_sheet_clears_every_staff_start(bot, cog, helix):
    _channel, marathon = await show(bot, cog, helix)
    hamtaro = (await times(bot, marathon))[HAMTARO]
    assert (await retime.set_start(bot, bot.guild, FakeActor(), marathon, hamtaro, z(90), "UTC")).ok

    back = await signals.sheet_times(bot, bot.guild, FakeActor(), marathon)

    assert back.ok, back.message
    rows = await times(bot, marathon)
    assert rows[HAMTARO]["staff_start_at"] is None and rows[HAMTARO]["scheduled_at"] == z(68)
    assert rows[HAMTARO]["staff_start_by"] is None and rows[HAMTARO]["staff_start_set_at"] is None


async def test_a_schedule_that_moves_itself_is_refused_in_words(bot, cog, helix):
    _channel, marathon = await show(bot, cog, helix)
    await bot.db.conn.execute("UPDATE marathons SET source = 'gdq' WHERE id = ?", (marathon["id"],))
    await bot.db.conn.commit()
    hamtaro = (await times(bot, marathon))[HAMTARO]

    for done in (
        await retime.set_start(bot, bot.guild, FakeActor(), marathon, hamtaro, z(90), "UTC"),
        await retime.shift_day(bot, bot.guild, FakeActor(), marathon, hamtaro, "10"),
    ):
        assert not done.ok and done.code == "retimes_itself" and done.status == 409
        assert "publishes its own times, so nothing was changed" in done.message
    assert (await times(bot, marathon))[HAMTARO]["staff_start_at"] is None
    found = await retime.form_for(bot, bot.guild, marathon["id"], rt.START)
    assert not isinstance(found, discord.ui.Modal) and found.code == "retimes_itself"
    fresh = await get_marathon(bot.db, GUILD, marathon["id"])
    shown, _labels = controls.labelled(
        bot, bot.guild, fresh, await signals_rows(bot, marathon), "none", over=False
    )
    assert not any(one.action == mtc.RETIME for one in shown)


async def signals_rows(bot, marathon):
    return list((await times(bot, marathon)).values())


async def test_every_wrong_move_is_refused_in_words_and_changes_nothing(bot, cog, helix):
    channel, marathon = await show(bot, cog, helix)
    await stream(bot, channel, game=SPYRO, game_id="1")
    at_show(cog, 20)
    await tick(cog)
    rows = await times(bot, marathon)
    actor = FakeActor()

    live = await retime.set_start(bot, bot.guild, actor, marathon, rows[SPYRO], z(30), "UTC")
    assert (live.code, live.status) == ("not_upcoming", 409) and "is live" in live.message
    bad = await retime.set_start(bot, bot.guild, actor, marathon, rows[KIRBY], "soonish", "UTC")
    assert (bad.code, bad.status) == (
        "bad_time",
        400,
    ) and "**soonish** is not a time" in bad.message
    same = await retime.set_start(
        bot, bot.guild, actor, marathon, rows[KIRBY], rows[KIRBY]["scheduled_at"], "UTC"
    )
    assert same.code == "same_time"
    early = await retime.set_start(bot, bot.guild, actor, marathon, rows[KIRBY], z(10), "UTC")
    assert early.code == "before_the_run_ahead" and SPYRO in early.message
    for typed in ("0", "ten", "100000"):
        minutes = await retime.shift_day(bot, bot.guild, actor, marathon, rows[KIRBY], typed)
        assert (minutes.code, minutes.status) == ("bad_minutes", 400)
    assert all(one["staff_start_at"] is None for one in (await times(bot, marathon)).values())
    assert "marathon.start_set" not in await kinds(bot.db)


async def test_the_thread_controls_carry_set_start_and_shift_the_day_for_a_clock_kept_show(
    bot, cog, helix
):
    _channel, marathon = await show(bot, cog, helix)
    fresh = await get_marathon(bot.db, GUILD, marathon["id"])

    shown, labels = controls.labelled(
        bot, bot.guild, fresh, await signals_rows(bot, marathon), "none", over=False
    )

    moves = [
        (one.to, text, one.row)
        for one, text in zip(shown, labels, strict=True)
        if one.action == mtc.RETIME
    ]
    assert moves == [("start", "Set start…", 1), ("shift", "Shift the day…", 1)]
    view = controls.view_of(fresh["id"], shown, labels)
    ids = [getattr(one, "custom_id", None) for one in view.children]
    assert f"marathon:retime:{fresh['id']}:start" in ids
    assert f"marathon:retime:{fresh['id']}:shift" in ids
    switches = controls.drawer_switches(
        bot, bot.guild, fresh, await signals_rows(bot, marathon), "none"
    )
    assert not any(one["action"] == mtc.RETIME for one in switches)


async def test_the_set_start_button_opens_a_form_and_its_answer_moves_the_run(bot, cog, helix):
    _channel, marathon = await show(bot, cog, helix)
    custom = retime.custom_id(marathon["id"], rt.START)
    button = await retime.RetimeButton.from_custom_id(
        None, None, re.fullmatch(retime.TEMPLATE, custom)
    )
    bot.store.is_staff = lambda member: False
    stranger = FakeInteraction(bot, FakeActor(), bot.guild)
    await button.on_click(stranger)
    assert "staff only" in stranger.sent and not stranger.response.modals

    bot.store.is_staff = lambda member: True
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    await button.on_click(lead)
    form = lead.response.modals[0]
    assert isinstance(form, retime.RetimeModal) and form.title == "Set a run's start"
    options = [one.value for one in form.run.options]
    rows = await times(bot, marathon)
    assert options[0] == str(rows[SPYRO]["id"]) and len(options) <= rt.PICK_LIMIT

    done = await retime.submitted(
        bot, bot.guild, FakeActor(), marathon["id"], rt.START, rows[HAMTARO]["id"], z(95)
    )
    assert done.ok, done.message
    assert (await times(bot, marathon))[HAMTARO]["scheduled_at"] == z(95)

    shifted = await retime.submitted(
        bot, bot.guild, FakeActor(), marathon["id"], rt.SHIFT, rows[KIRBY]["id"], "-5"
    )
    assert shifted.ok, shifted.message


async def test_with_every_run_started_the_button_says_so_and_opens_nothing(bot, cog, helix):
    _channel, marathon = await show(bot, cog, helix)
    await bot.db.conn.execute(
        "UPDATE marathon_runs SET state = 'done' WHERE marathon_id = ?", (marathon["id"],)
    )
    await bot.db.conn.commit()

    found = await retime.form_for(bot, bot.guild, marathon["id"], rt.SHIFT)

    assert not isinstance(found, discord.ui.Modal) and found.code == "nothing_upcoming"
