# ruff: noqa: F401, F811
import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from black_bloc import marathon as mt
from black_bloc import marathon_hotfix as hf
from black_bloc.cogs.content import marathon as cogmod
from black_bloc.cogs.content import marathon_signals as signals
from black_bloc.cogs.content.marathon import (
    get_marathon,
    mark_done,
    mark_live,
    mark_upcoming,
    runs_of,
)
from black_bloc.cogs.content.spotlight import (
    Spotlight,
    open_session,
    refresh_session_info,
    start_session,
)
from black_bloc.golive import StreamInfo
from black_bloc.twitch import TwitchError, TwitchGame, TwitchStream
from tests.cogs.content.test_marathon import (
    GUILD,
    added,
    at,
    bot,
    cog,
    create_marathon,
    gdq_row,
    posts,
    runs_by_game,
    tracked,
)
from tests.cogs.content.test_spotlight import (
    FakeActor,
    FakeGoLive,
    FakeInteraction,
    details_of,
    kinds,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "marathon"
HOTFIX_URL = "https://gamesdonequick.com/hotfix/schedule#gdqueer/2026-10-03"
SHOW = datetime(2026, 10, 3, 17, 0, tzinfo=UTC)
SPYRO = "Spyro Reignited Trilogy"
HAMTARO = "Hamtaro: Ham-Hams Unite!"
KIRBY = "Kirby's Dream Land"
WARIO = "WarioWare: Touched!"
DENSHA = "Denshattack!"
BOMBUN = "Bombun"
KILAFLOW = "Kilaflow"
CATEGORIES = {SPYRO: "1", HAMTARO: "2", KIRBY: "3", WARIO: "4", KILAFLOW: "5"}
RETRO_ID = "27284"
SETUP_KEY = "marathon_setup_minutes"


def z(minutes):
    return (SHOW + timedelta(minutes=minutes)).isoformat()


class FakeCategories:
    def __init__(self, known=None, raises=None):
        self.known = {
            name.lower(): TwitchGame(game_id, name, "")
            for name, game_id in (known if known is not None else CATEGORIES).items()
        }
        self.raises = raises
        self.calls = []

    async def games_named(self, names):
        self.calls.append(("named", list(names)))
        if self.raises is not None:
            raise self.raises
        return {
            name.lower(): self.known[name.lower()] for name in names if name.lower() in self.known
        }

    async def search_categories(self, query):
        self.calls.append(("search", query))
        return []

    async def close(self):
        return None


def gdqueer_runs(*, kirby="0:15:00", setup=0):
    text = (FIXTURES / "gdq_hotfix_sheet.csv").read_text(encoding="utf-8")
    text = text.replace("Any% (Normal Mode),0:15:00", f"Any% (Normal Mode),{kirby}")
    return list(hf.parse_hotfix(text, ["GDQueer"], setup)[0].runs)


def at_show(cog, minutes):
    cog.clock = lambda: SHOW + timedelta(minutes=minutes)


@pytest.fixture
def helix(bot):
    made = FakeCategories()
    bot.cogs["GoLive"] = FakeGoLive(made)
    return made


async def gdqueer(bot, cog, *, setup=0):
    await bot.store.set(GUILD, SETUP_KEY, setup)
    channel = await gdq_row(bot)
    cog.client.runs_given = gdqueer_runs(setup=setup)
    at_show(cog, -60)
    outcome = await create_marathon(
        bot, bot.guild, FakeActor(), name="GDQueer", url=HOTFIX_URL, spotlight_id=channel["id"]
    )
    assert outcome.ok, outcome.message
    marathon = await tracked(bot, outcome.value)
    assert marathon["source"] == "gdq_hotfix"
    return channel, marathon


async def stream(bot, channel, *, title="GDQueer 2026 !schedule", game="", game_id=""):
    session = await open_session(bot.db, channel["id"])
    if session is None:
        info = StreamInfo(title=title, game=game or None, game_id=game_id or None)
        await start_session(bot.db, GUILD, channel["id"], info, "on")
        return
    await refresh_session_info(bot.db, session["id"], game, title, game_id)


async def tick(cog):
    await cog._reconciler.run(cog.tick_once)


async def times(bot, marathon):
    return {row["game"]: row for row in await runs_of(bot.db, marathon["id"])}


# --- the category lookup ----------------------------------------------------------------------


async def test_each_run_is_looked_up_on_twitch_once_and_none_found_is_kept(bot, cog, helix):
    _channel, marathon = await gdqueer(bot, cog)
    await tick(cog)
    rows = await times(bot, marathon)
    assert (rows[SPYRO]["twitch_game_id"], rows[SPYRO]["twitch_category"]) == ("1", SPYRO)
    assert rows[BOMBUN]["twitch_game_id"] is None and rows[BOMBUN]["twitch_looked_at"]
    asked = len(helix.calls)
    await tick(cog)
    assert len(helix.calls) == asked
    found = await details_of(bot.db, "marathon.categories_found")
    assert found["found"] == 5 and found["none"] == 19


async def test_a_lookup_twitch_refuses_is_logged_and_tried_again_only_after_a_while(bot, cog):
    refusing = FakeCategories(raises=TwitchError("Twitch answered 500 for games"))
    bot.cogs["GoLive"] = FakeGoLive(refusing)
    _channel, marathon = await gdqueer(bot, cog)
    await tick(cog)
    assert "marathon.category_lookup_failed" in await kinds(bot.db)
    assert all(row["twitch_looked_at"] is None for row in await runs_of(bot.db, marathon["id"]))
    await tick(cog)
    assert len(refusing.calls) == 1
    refusing.raises = None
    cog.clock = lambda: SHOW - timedelta(minutes=29)
    await tick(cog)
    assert len(refusing.calls) >= 2
    assert (await times(bot, marathon))[SPYRO]["twitch_game_id"] == "1"


# --- the third signal and the clock -----------------------------------------------------------


async def test_spyro_seen_20_minutes_late_by_its_category_re_times_hamtaro_to_its_start_plus_1_08(
    bot, cog, helix
):
    channel, marathon = await gdqueer(bot, cog)
    await tick(cog)
    await stream(bot, channel, game="Just Chatting", game_id="509658")
    at_show(cog, 10)
    await tick(cog)
    assert (await times(bot, marathon))[SPYRO]["state"] == mt.UPCOMING

    await stream(bot, channel, game=SPYRO, game_id="1")
    at_show(cog, 20)
    await tick(cog)

    rows = await times(bot, marathon)
    spyro, hamtaro, kirby = rows[SPYRO], rows[HAMTARO], rows[KIRBY]
    assert (spyro["state"], spyro["live_because"]) == (mt.LIVE, mt.BY_CATEGORY)
    assert spyro["actual_started_at"] == z(20)
    assert (spyro["scheduled_at"], spyro["ends_at"]) == (z(20), z(88))
    assert (hamtaro["scheduled_at"], hamtaro["ends_at"]) == (z(88), z(140))
    assert hamtaro["sheet_at"] == z(68)
    assert kirby["scheduled_at"] == z(140)
    day_two = rows["Wii Fit U"]
    assert day_two["scheduled_at"] == day_two["sheet_at"] == "2026-10-04T17:00:00+00:00"
    said = await details_of(bot.db, "marathon.retimed")
    assert said["because"] == "stream" and said["runs"] == 13


async def test_a_run_with_no_category_is_matched_by_the_retro_category_and_one_with_its_own_is_not(
    bot, cog, helix
):
    channel, marathon = await gdqueer(bot, cog)
    await tick(cog)
    await stream(bot, channel, game="Retro", game_id=RETRO_ID)
    at_show(cog, 232)
    await tick(cog)
    rows = await times(bot, marathon)
    assert (rows[BOMBUN]["state"], rows[BOMBUN]["live_because"]) == (mt.LIVE, mt.BY_CATEGORY)
    assert rows[KILAFLOW]["state"] == mt.UPCOMING
    assert rows[DENSHA]["state"] == mt.DONE
    assert rows[KILAFLOW]["scheduled_at"] == z(232 + 46)


async def test_the_title_alone_goes_live_by_title(bot, cog, helix):
    channel, marathon = await gdqueer(bot, cog)
    await tick(cog)
    await stream(bot, channel, title=f"GDQueer - {HAMTARO} Any%", game="Just Chatting", game_id="9")
    at_show(cog, 75)
    await tick(cog)
    rows = await times(bot, marathon)
    assert (rows[HAMTARO]["state"], rows[HAMTARO]["live_because"]) == (mt.LIVE, mt.BY_TITLE)
    assert rows[SPYRO]["state"] == mt.DONE
    assert rows[KIRBY]["scheduled_at"] == z(75 + 52)


async def test_title_and_category_together_are_certain(bot, cog, helix):
    channel, marathon = await gdqueer(bot, cog)
    await tick(cog)
    await stream(bot, channel, title=f"GDQueer: {SPYRO} 80 Dragons", game=SPYRO, game_id="1")
    at_show(cog, 3)
    await tick(cog)
    spyro = (await times(bot, marathon))[SPYRO]
    assert spyro["live_because"] == mt.BY_BOTH and spyro["actual_started_at"] == z(3)


async def test_a_run_live_by_one_signal_becomes_certain_when_the_other_agrees(bot, cog, helix):
    channel, marathon = await gdqueer(bot, cog)
    await tick(cog)
    await stream(bot, channel, game=SPYRO, game_id="1")
    at_show(cog, 2)
    await tick(cog)
    await stream(bot, channel, title=f"GDQueer: {SPYRO}", game=SPYRO, game_id="1")
    at_show(cog, 7)
    await tick(cog)
    spyro = (await times(bot, marathon))[SPYRO]
    assert spyro["live_because"] == mt.BY_BOTH and spyro["actual_started_at"] == z(2)


async def test_disagreeing_signals_trust_a_direct_category_and_are_logged_once(bot, cog, helix):
    channel, marathon = await gdqueer(bot, cog)
    await tick(cog)
    await stream(bot, channel, title=f"Up next: {HAMTARO}", game=SPYRO, game_id="1")
    at_show(cog, 5)
    await tick(cog)
    at_show(cog, 6)
    await tick(cog)
    rows = await times(bot, marathon)
    assert (rows[SPYRO]["state"], rows[SPYRO]["live_because"]) == (mt.LIVE, mt.BY_CATEGORY)
    assert rows[HAMTARO]["state"] == mt.UPCOMING
    assert (await kinds(bot.db)).count("marathon.signals_disagree") == 1
    said = await details_of(bot.db, "marathon.signals_disagree")
    assert said["title_run"]["game"] == HAMTARO and said["category_run"]["game"] == SPYRO
    assert said["trusted"] == mt.BY_CATEGORY


async def test_disagreeing_with_retro_the_title_wins(bot, cog, helix):
    channel, marathon = await gdqueer(bot, cog)
    await tick(cog)
    await stream(bot, channel, title=f"GDQueer - {WARIO}", game="Retro", game_id=RETRO_ID)
    at_show(cog, 140)
    await tick(cog)
    rows = await times(bot, marathon)
    assert (rows[WARIO]["state"], rows[WARIO]["live_because"]) == (mt.LIVE, mt.BY_TITLE)
    assert rows[DENSHA]["state"] == mt.UPCOMING
    assert (await details_of(bot.db, "marathon.signals_disagree"))["trusted"] == mt.BY_TITLE


async def test_with_the_category_key_off_the_category_decides_nothing(bot, cog, helix):
    await bot.store.set(GUILD, "marathon_category_confirms", False)
    channel, marathon = await gdqueer(bot, cog)
    await tick(cog)
    await stream(bot, channel, game=SPYRO, game_id="1")
    at_show(cog, 20)
    await tick(cog)
    rows = await times(bot, marathon)
    assert rows[SPYRO]["state"] == mt.UPCOMING and rows[SPYRO]["twitch_looked_at"] is None
    assert helix.calls == []


async def test_a_gdq_tracker_marathon_is_never_re_timed_by_this(bot, cog, helix):
    channel = await gdq_row(bot)
    marathon = await added(bot, cog, channel=channel)
    await stream(bot, channel, title="Super Metroid Any%")
    cog.clock = lambda: datetime.fromisoformat(at(50))
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    rows = await runs_by_game(bot, marathon)
    assert rows["Super Metroid"]["state"] == mt.LIVE
    assert rows["Super Metroid"]["actual_started_at"] == at(50)
    assert rows["Kirby Air Riders"]["scheduled_at"] == at(90)
    assert "marathon.retimed" not in await kinds(bot.db)


async def test_the_setup_buffer_is_asked_for_only_where_black_bloc_keeps_the_clock(bot, cog, helix):
    assert bot.store.get(GUILD, SETUP_KEY) == 7
    assert signals.setup_for(bot, GUILD, "gdq_hotfix") == {"setup_minutes": 7}
    for source in ("gdq", "rpglb", "horaro", "oengus", "fastestfurs", "ladyarcaders"):
        assert signals.setup_for(bot, GUILD, source) == {}
    await bot.store.set(GUILD, SETUP_KEY, 30)
    channel = await gdq_row(bot)
    marathon = await added(bot, cog, channel=channel)
    before = {one["game"]: one["scheduled_at"] for one in await runs_of(bot.db, marathon["id"])}
    await stream(bot, channel, title="Super Metroid Any%")
    cog.clock = lambda: datetime.fromisoformat(at(50))
    await cog.refresh(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    await cog.follow(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert cog.client.asked and all(asked == {} for _what, _source, asked in cog.client.asked)
    after = {one["game"]: one["scheduled_at"] for one in await runs_of(bot.db, marathon["id"])}
    assert after == before
    assert "marathon.retimed" not in await kinds(bot.db)


async def test_spyro_seen_20_minutes_late_puts_hamtaro_7_minutes_after_spyro_should_end(
    bot, cog, helix
):
    channel, marathon = await gdqueer(bot, cog, setup=7)
    assert cog.client.asked[-1] == ("runs", "gdq_hotfix", {"setup_minutes": 7})
    rows = await times(bot, marathon)
    assert (rows[SPYRO]["scheduled_at"], rows[HAMTARO]["scheduled_at"]) == (z(0), z(75))
    await tick(cog)
    await stream(bot, channel, game=SPYRO, game_id="1")
    at_show(cog, 20)
    await tick(cog)
    rows = await times(bot, marathon)
    assert (rows[SPYRO]["scheduled_at"], rows[SPYRO]["ends_at"]) == (z(20), z(88))
    assert (rows[HAMTARO]["scheduled_at"], rows[HAMTARO]["ends_at"]) == (z(95), z(147))
    assert rows[HAMTARO]["sheet_at"] == z(75)
    assert (rows[KIRBY]["scheduled_at"], rows[WARIO]["scheduled_at"]) == (z(154), z(176))
    day_two = rows["Wii Fit U"]
    assert day_two["scheduled_at"] == day_two["sheet_at"] == "2026-10-04T17:00:00+00:00"


async def test_a_changed_buffer_is_used_by_the_next_re_time_before_any_schedule_read(
    bot, cog, helix
):
    channel, marathon = await gdqueer(bot, cog)
    await tick(cog)
    await bot.store.set(GUILD, SETUP_KEY, 7)
    await stream(bot, channel, game=SPYRO, game_id="1")
    at_show(cog, 20)
    await tick(cog)
    rows = await times(bot, marathon)
    assert rows[SPYRO]["scheduled_at"] == z(20)
    assert (rows[HAMTARO]["scheduled_at"], rows[HAMTARO]["sheet_at"]) == (z(95), z(68))
    assert rows[KIRBY]["scheduled_at"] == z(154)


async def test_a_changed_buffer_moves_the_runs_ahead_at_the_next_read_and_never_a_live_or_done_one(
    bot, cog, helix
):
    channel, marathon = await gdqueer(bot, cog)
    await tick(cog)
    await stream(bot, channel, game=SPYRO, game_id="1")
    at_show(cog, 20)
    await tick(cog)
    await stream(bot, channel, game=HAMTARO, game_id="2")
    at_show(cog, 90)
    await tick(cog)
    rows = await times(bot, marathon)
    assert (rows[SPYRO]["state"], rows[HAMTARO]["state"]) == (mt.DONE, mt.LIVE)
    assert (rows[HAMTARO]["scheduled_at"], rows[KIRBY]["scheduled_at"]) == (z(90), z(142))

    await bot.store.set(GUILD, SETUP_KEY, 7)
    cog.client.runs_given = gdqueer_runs(setup=7)
    await cog.refresh(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert cog.client.asked[-1] == ("runs", "gdq_hotfix", {"setup_minutes": 7})
    rows = await times(bot, marathon)
    assert (rows[SPYRO]["state"], rows[SPYRO]["scheduled_at"]) == (mt.DONE, z(20))
    assert (rows[HAMTARO]["scheduled_at"], rows[HAMTARO]["ends_at"]) == (z(90), z(142))
    assert rows[HAMTARO]["sheet_at"] == z(75) and rows[HAMTARO]["moved_at"] is None
    assert (rows[KIRBY]["scheduled_at"], rows[KIRBY]["sheet_at"]) == (z(149), z(134))
    assert rows[WARIO]["scheduled_at"] == z(171)
    assert rows["Wii Fit U"]["scheduled_at"] == "2026-10-04T17:00:00+00:00"
    assert rows["Inazuma Eleven: Victory Road"]["scheduled_at"] == "2026-10-04T17:30:00+00:00"
    fresh = await get_marathon(bot.db, GUILD, marathon["id"])
    assert fresh["ends_at"] == "2026-10-05T04:19:00+00:00"


async def test_a_run_live_or_done_by_the_clock_alone_is_not_moved_by_a_changed_buffer(
    bot, cog, helix
):
    await bot.store.set(GUILD, "marathon_title_confirms", False)
    await bot.store.set(GUILD, "marathon_category_confirms", False)
    _channel, marathon = await gdqueer(bot, cog)
    at_show(cog, 70)
    await tick(cog)
    rows = await times(bot, marathon)
    assert (rows[SPYRO]["state"], rows[HAMTARO]["state"]) == (mt.DONE, mt.LIVE)
    assert rows[HAMTARO]["actual_started_at"] is None

    await bot.store.set(GUILD, SETUP_KEY, 7)
    cog.client.runs_given = gdqueer_runs(setup=7)
    await cog.refresh(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    rows = await times(bot, marathon)
    assert (rows[SPYRO]["scheduled_at"], rows[SPYRO]["ends_at"]) == (z(0), z(68))
    assert (rows[HAMTARO]["scheduled_at"], rows[HAMTARO]["ends_at"]) == (z(68), z(120))
    assert rows[HAMTARO]["sheet_at"] == z(75) and rows[HAMTARO]["moved_at"] is None
    assert (rows[KIRBY]["scheduled_at"], rows[KIRBY]["moved_at"] is not None) == (z(134), True)
    assert "marathon.retimed" not in await kinds(bot.db)


async def test_a_sheet_refresh_keeps_the_re_timing_of_runs_already_seen(bot, cog, helix):
    channel, marathon = await gdqueer(bot, cog)
    await tick(cog)
    await stream(bot, channel, game=SPYRO, game_id="1")
    at_show(cog, 20)
    await tick(cog)
    cog.client.runs_given = gdqueer_runs(kirby="0:20:00")
    await cog.refresh(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    rows = await times(bot, marathon)
    assert rows[SPYRO]["scheduled_at"] == z(20)
    assert rows[HAMTARO]["scheduled_at"] == z(88) and rows[HAMTARO]["sheet_at"] == z(68)
    assert rows[KIRBY]["scheduled_at"] == z(140)
    assert rows[WARIO]["scheduled_at"] == z(160) and rows[WARIO]["sheet_at"] == z(140)
    assert (await details_of(bot.db, "marathon.retimed"))["because"] == "schedule_read"


async def test_staff_put_the_runs_back_on_the_sheets_times_and_can_move_the_clock_themselves(
    bot, cog, helix
):
    channel, marathon = await gdqueer(bot, cog)
    await tick(cog)
    await stream(bot, channel, game=SPYRO, game_id="1")
    at_show(cog, 20)
    await tick(cog)

    back = await signals.sheet_times(bot, bot.guild, FakeActor(), marathon)
    assert back.ok and "sheet's times" in back.message
    rows = await times(bot, marathon)
    assert rows[SPYRO]["scheduled_at"] == z(0) and rows[SPYRO]["actual_started_at"] is None
    assert rows[HAMTARO]["scheduled_at"] == z(68)
    assert rows[SPYRO]["state"] == mt.LIVE
    again = await signals.sheet_times(bot, bot.guild, FakeActor(), marathon)
    assert not again.ok and again.code == "not_retimed"
    assert "marathon.sheet_times" in await kinds(bot.db)
    at_show(cog, 25)
    await tick(cog)
    assert (await times(bot, marathon))[HAMTARO]["scheduled_at"] == z(68)

    at_show(cog, 70)
    hamtaro = (await times(bot, marathon))[HAMTARO]
    assert (await mark_live(bot, bot.guild, FakeActor(), marathon, hamtaro)).ok
    rows = await times(bot, marathon)
    assert rows[HAMTARO]["actual_started_at"] == z(70) and rows[KIRBY]["scheduled_at"] == z(122)
    at_show(cog, 100)
    assert (await mark_done(bot, bot.guild, FakeActor(), marathon, rows[HAMTARO])).ok
    assert (await times(bot, marathon))[KIRBY]["scheduled_at"] == z(100)
    hamtaro = (await times(bot, marathon))[HAMTARO]
    assert (await mark_upcoming(bot, bot.guild, FakeActor(), marathon, hamtaro)).ok
    rows = await times(bot, marathon)
    assert rows[HAMTARO]["actual_started_at"] is None and rows[KIRBY]["scheduled_at"] == z(120)


async def test_two_ticks_at_once_flip_and_re_time_exactly_once(bot, cog, helix):
    channel, marathon = await gdqueer(bot, cog)
    await tick(cog)
    await stream(bot, channel, game=SPYRO, game_id="1")
    at_show(cog, 20)
    await asyncio.gather(
        cog._reconciler.run(cog.tick_once),
        cog._reconciler.run(cog.tick_once, skip_if_recent=True),
        cog._reconciler.run(cog.tick_once),
    )
    found = await kinds(bot.db)
    assert found.count("marathon.retimed") == 1
    assert (await times(bot, marathon))[HAMTARO]["scheduled_at"] == z(88)


async def test_a_run_of_ours_seen_by_its_category_is_shouted_without_a_ping(bot, cog, helix):
    await bot.db.conn.execute(
        "INSERT INTO golive_links(user_id, twitch_login, linked_at) VALUES (77, 'toronite', ?)",
        (z(-9999),),
    )
    await bot.db.conn.commit()
    channel, marathon = await gdqueer(bot, cog)
    await tick(cog)
    await stream(bot, channel, game=SPYRO, game_id="1")
    at_show(cog, 20)
    await tick(cog)
    assert "<@&" not in "".join(one.content for one in posts(bot))
    assert (await details_of(bot.db, "marathon.run_live"))["because"] == mt.BY_CATEGORY


async def test_the_discord_schedule_view_says_the_clock_and_puts_it_back_on_the_sheet(
    bot, cog, helix
):
    channel, marathon = await gdqueer(bot, cog)
    embed, view = await cogmod.build_schedule(bot, bot.guild, marathon["id"])
    assert "Back to the sheet's times" not in [getattr(one, "label", None) for one in view.children]
    await tick(cog)
    await stream(bot, channel, game=SPYRO, game_id="1")
    at_show(cog, 20)
    await tick(cog)

    embed, view = await cogmod.build_schedule(bot, bot.guild, marathon["id"])
    assert "13 run(s) re-timed from the stream" in embed.description
    interaction = FakeInteraction(bot, FakeActor(), bot.guild)
    button = next(
        one for one in view.children if getattr(one, "label", None) == "Back to the sheet's times"
    )
    await button.callback(interaction)
    assert interaction.view.where == cogmod.SCHEDULE_VIEW
    assert "re-timed" not in interaction.words
    assert "web.marathon.sheet_times" not in await kinds(bot.db)
    assert "marathon.sheet_times" in await kinds(bot.db)
    assert (await times(bot, marathon))[HAMTARO]["scheduled_at"] == z(68)


async def test_a_schedule_read_after_a_rename_leaves_a_hotfix_marathons_name_alone(bot, cog, helix):
    from black_bloc.cogs.content.marathon import rename_marathon

    _channel, marathon = await gdqueer(bot, cog, setup=7)
    done = await rename_marathon(
        bot, bot.guild, FakeActor(), marathon, "Black in a Flash: Soul Train", None
    )
    assert done.ok
    cog.client.runs_given = gdqueer_runs(setup=7)[:-1]
    at_show(cog, 30)
    await cog.refresh(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert (await get_marathon(bot.db, GUILD, marathon["id"]))["name"] == (
        "Black in a Flash: Soul Train"
    )


# --- a replay mid-stream ends the live run (spotlight-design.md, Follow-up 2026-10-04) ---------

HALO = "Halo Infinite"
WII_FIT = "Wii Fit U"
GDQ_LOGIN = "gamesdonequick"
STARTED = "2026-10-03T16:52:00Z"
DAY_TWO = datetime(2026, 10, 4, 17, 0, tzinfo=UTC)
GDQUEER_REPLAY = "[Replay] GDQueer Day 1 - tune in live for Day 2 starting at 1pm Eastern!"


class FakeTwitch(FakeCategories):
    def __init__(self):
        super().__init__()
        self.streams = []

    async def get_streams(self, logins):
        return [one for one in self.streams if one.user_login in {x.lower() for x in logins}]

    async def get_games(self, ids):
        return []


def showing(title, game="Games Done Quick", game_id="509663"):
    return [
        TwitchStream("10", GDQ_LOGIN, "GamesDoneQuick", game, title, STARTED, game_id, "", "live")
    ]


def spot_at(spot, when):
    spot._now = lambda: when


async def day_one_over_but_halo_live(bot, cog):
    """Yesterday's broadcast never went offline: pinned post up, every day-1 run done but the
    last, which is still live because nothing followed it."""
    twitch = FakeTwitch()
    bot.cogs["GoLive"] = FakeGoLive(twitch)
    channel, marathon = await gdqueer(bot, cog)
    spot = Spotlight(bot)
    bot.cogs["Spotlight"] = spot
    twitch.streams = showing("GDQueer 2026 !schedule")
    spot_at(spot, SHOW - timedelta(minutes=8))
    await spot.poll_once()
    session = await open_session(bot.db, channel["id"])
    halo = (await times(bot, marathon))[HALO]
    await bot.db.conn.execute(
        "UPDATE spotlight_sessions SET started_at = ? WHERE id = ?",
        ((datetime.now(UTC) - timedelta(hours=20)).isoformat(), session["id"]),
    )
    await bot.db.conn.execute(
        "UPDATE marathon_runs SET state = 'done', done_at = sheet_ends_at "
        "WHERE marathon_id = ? AND sheet_at < ? AND id != ?",
        (marathon["id"], DAY_TWO.isoformat(), halo["id"]),
    )
    await bot.db.conn.execute(
        "UPDATE marathon_runs SET state = 'live', live_at = sheet_at, live_because = 'title', "
        "actual_started_at = sheet_at WHERE id = ?",
        (halo["id"],),
    )
    await bot.db.conn.commit()
    return channel, marathon, spot, twitch


def day_two_of(rows):
    return {
        game: (row["state"], row["scheduled_at"], row["ends_at"])
        for game, row in rows.items()
        if row["sheet_at"] >= DAY_TWO.isoformat()
    }


async def test_the_morning_after_the_replay_ends_the_spotlight_and_the_live_show_brings_it_back(
    bot, cog
):
    channel, marathon, spot, twitch = await day_one_over_but_halo_live(bot, cog)
    pinned = posts(bot)[0]
    before = await times(bot, marathon)
    assert pinned.pinned is True and before[HALO]["state"] == mt.LIVE
    assert len(day_two_of(before)) == 11

    twitch.streams = showing(GDQUEER_REPLAY)
    spot_at(spot, datetime(2026, 10, 4, 13, 40, tzinfo=UTC))
    await spot.poll_once()
    assert pinned.pinned is True and (await times(bot, marathon))[HALO]["state"] == mt.LIVE
    for _ in range(4):
        await spot.poll_once()

    session = await open_session(bot.db, channel["id"])
    assert session["replay_reason"] == "tag:replay" and session["replay_cleared"] is None
    assert posts(bot) == [pinned] and pinned.pinned is False and pinned.embed is None
    assert pinned.content.startswith("**GamesDoneQuick** is showing a replay — [Replay] GDQueer")
    assert "<@&" not in pinned.content
    assert pinned.edits[-1]["allowed_mentions"].roles is False
    seen = await kinds(bot.db)
    assert "golive.spotlight_bumped" not in seen and seen.count("golive.replay_began") == 1
    after = await times(bot, marathon)
    assert after[HALO]["state"] == mt.DONE and after[HALO]["actual_ended_at"] is None
    assert (await details_of(bot.db, "marathon.run_done"))["because"] == "replay"
    assert day_two_of(after) == day_two_of(before)
    assert "marathon.retimed" not in seen
    cog.clock = lambda: datetime(2026, 10, 4, 13, 45, tzinfo=UTC)
    await tick(cog)
    assert (await times(bot, marathon))[HALO]["state"] == mt.DONE

    twitch.streams = showing("GDQueer 2026 Day 2 - starting soon !schedule")
    spot_at(spot, datetime(2026, 10, 4, 16, 55, tzinfo=UTC))
    await spot.poll_once()
    assert posts(bot) == [pinned]
    for _ in range(3):
        await spot.poll_once()
    live = posts(bot)
    assert len(live) == 1 and live[0] is not pinned and pinned.deleted is True
    assert live[0].pinned is True and live[0].embed is not None
    seen = await kinds(bot.db)
    assert seen.count("golive.replay_upgraded") == 1 and "golive.spotlight_bumped" not in seen
    assert (await open_session(bot.db, channel["id"]))["replay_cleared"] == "title"

    twitch.streams = showing("GDQueer 2026 - Wii Fit U", game=WII_FIT, game_id="77")
    spot_at(spot, datetime(2026, 10, 4, 17, 2, tzinfo=UTC))
    await spot.poll_once()
    cog.clock = lambda: datetime(2026, 10, 4, 17, 2, tzinfo=UTC)
    await tick(cog)
    wii = (await times(bot, marathon))[WII_FIT]
    assert wii["state"] == mt.LIVE and wii["live_because"] in mt.BY_STREAM
    assert wii["actual_started_at"] == "2026-10-04T17:02:00+00:00"
    assert len(posts(bot)) == 1 and (await open_session(bot.db, channel["id"])) is not None


async def test_a_fuzzy_replay_word_is_live_while_a_run_is_around_and_a_replay_overnight(bot, cog):
    channel, _marathon, spot, _twitch = await day_one_over_but_halo_live(bot, cog)
    info = StreamInfo(title="GDQueer Day 1 rerun")

    spot_at(spot, SHOW + timedelta(minutes=30))
    during = await spot._verdict(bot.guild, channel, info, "live")
    assert not during.replay and during.overruled == "marathon"

    spot_at(spot, datetime(2026, 10, 4, 13, 40, tzinfo=UTC))
    assert (await spot._verdict(bot.guild, channel, info, "live")).reason == "title:rerun"

    await bot.store.set(GUILD, "golive_replay_marathon_runs", False)
    whole = await spot._verdict(bot.guild, channel, info, "live")
    assert not whole.replay and whole.overruled == "marathon"


async def test_a_replay_ends_only_the_live_run_and_a_channel_with_no_marathon_ends_none(bot, cog):
    channel, marathon, _spot, _twitch = await day_one_over_but_halo_live(bot, cog)
    before = await times(bot, marathon)

    assert await signals.replay_began(bot, bot.guild, channel["id"]) == 1
    assert await signals.replay_began(bot, bot.guild, channel["id"]) == 0
    assert await signals.replay_began(bot, bot.guild, 9999) == 0

    after = await times(bot, marathon)
    assert after[HALO]["state"] == mt.DONE
    moved = [game for game in after if after[game]["scheduled_at"] != before[game]["scheduled_at"]]
    assert moved == [] and after[WII_FIT]["state"] == mt.UPCOMING


# --- a show-day's first run, shown too early ----------------------------------------------------

WII = "Wii Fit U"
RACERS = "Dr. Robotnik's Ring Racers"
EARLY_KEY = "marathon_early_start_minutes"
DAY = 1440


async def day_two_ahead(bot, cog):
    channel, marathon = await gdqueer(bot, cog)
    await tick(cog)
    await bot.db.conn.execute(
        "UPDATE marathon_runs SET state = 'done', done_at = sheet_ends_at "
        "WHERE marathon_id = ? AND sheet_at < ?",
        (marathon["id"], DAY_TWO.isoformat()),
    )
    await bot.db.conn.commit()
    return channel, marathon


async def set_up_for(bot, channel, game):
    await stream(bot, channel, title=f"GDQueer - {game}", game=game, game_id="77")


async def held_rows(bot):
    return (await kinds(bot.db)).count("marathon.early_match_held")


async def undone_rows(bot):
    return (await kinds(bot.db)).count("marathon.early_start_undone")


def off_the_sheet(rows):
    return [
        game
        for game, row in rows.items()
        if (row["scheduled_at"], row["ends_at"]) != (row["sheet_at"], row["sheet_ends_at"])
    ]


async def test_a_days_first_run_shown_80_minutes_early_is_held_and_logged_once(bot, cog, helix):
    channel, marathon = await day_two_ahead(bot, cog)
    await set_up_for(bot, channel, WII)
    for minutes in (-80, -79, -60):
        at_show(cog, DAY + minutes)
        await tick(cog)
        rows = await times(bot, marathon)
        assert (rows[WII]["state"], rows[WII]["actual_started_at"]) == (mt.UPCOMING, None)
        assert off_the_sheet(rows) == []
    assert await held_rows(bot) == 1
    said = await details_of(bot.db, "marathon.early_match_held")
    assert (said["game"], said["early_minutes"], said["allowed_minutes"]) == (WII, 80, 10)
    assert said["planned_at"] == z(DAY) and said["because"] == mt.BY_BOTH
    assert "marathon.retimed" not in await kinds(bot.db)


async def test_a_days_first_run_shown_10_minutes_early_is_live_as_before(bot, cog, helix):
    channel, marathon = await day_two_ahead(bot, cog)
    await set_up_for(bot, channel, WII)
    at_show(cog, DAY - 80)
    await tick(cog)
    at_show(cog, DAY - 10)
    await tick(cog)
    rows = await times(bot, marathon)
    assert (rows[WII]["state"], rows[WII]["live_because"]) == (mt.LIVE, mt.BY_BOTH)
    assert rows[WII]["actual_started_at"] == rows[WII]["scheduled_at"] == z(DAY - 10)
    assert await held_rows(bot) == 1 and await undone_rows(bot) == 0


async def test_a_later_run_of_the_day_shown_40_minutes_early_is_followed(bot, cog, helix):
    channel, marathon = await day_two_ahead(bot, cog)
    await bot.db.conn.execute(
        "UPDATE marathon_runs SET state = 'done' WHERE marathon_id = ? AND game = ?",
        (marathon["id"], WII),
    )
    await bot.db.conn.commit()
    racers = (await times(bot, marathon))[RACERS]
    early = datetime.fromisoformat(racers["sheet_at"]) - timedelta(minutes=40)
    await set_up_for(bot, channel, RACERS)
    cog.clock = lambda: early
    await tick(cog)
    racers = (await times(bot, marathon))[RACERS]
    assert (racers["state"], racers["actual_started_at"]) == (mt.LIVE, early.isoformat())
    assert await held_rows(bot) == 0


def second_of_day_two(rows):
    day = sorted(
        (row for row in rows.values() if row["sheet_at"] >= DAY_TWO.isoformat()),
        key=lambda row: row["sheet_at"],
    )
    assert day[0]["game"] == WII
    return day[1]


async def test_a_day_opening_with_its_second_run_at_the_days_start_is_live_at_once(bot, cog, helix):
    channel, marathon = await day_two_ahead(bot, cog)
    second = second_of_day_two(await times(bot, marathon))
    assert datetime.fromisoformat(second["sheet_at"]) > DAY_TWO + timedelta(minutes=15)
    await set_up_for(bot, channel, second["game"])
    at_show(cog, DAY)
    await tick(cog)
    rows = await times(bot, marathon)
    now = rows[second["game"]]
    assert (now["state"], now["actual_started_at"], now["scheduled_at"]) == (
        mt.LIVE,
        z(DAY),
        z(DAY),
    )
    assert rows[WII]["state"] == mt.DONE and await held_rows(bot) == 0


async def test_a_days_second_run_shown_60_minutes_before_the_days_start_is_held(bot, cog, helix):
    channel, marathon = await day_two_ahead(bot, cog)
    second = second_of_day_two(await times(bot, marathon))
    await set_up_for(bot, channel, second["game"])
    at_show(cog, DAY - 60)
    await tick(cog)
    rows = await times(bot, marathon)
    assert (rows[second["game"]]["state"], rows[WII]["state"]) == (mt.UPCOMING, mt.UPCOMING)
    assert off_the_sheet(rows) == []
    said = await details_of(bot.db, "marathon.early_match_held")
    assert (said["game"], said["early_minutes"]) == (second["game"], 60)
    assert (said["day_starts_at"], said["planned_at"]) == (z(DAY), second["sheet_at"])
    at_show(cog, DAY - 10)
    await tick(cog)
    now = (await times(bot, marathon))[second["game"]]
    assert (now["state"], now["actual_started_at"]) == (mt.LIVE, z(DAY - 10))
    assert await held_rows(bot) == 1


async def test_with_the_early_key_at_0_the_stream_is_believed_at_once(bot, cog, helix):
    await bot.store.set(GUILD, EARLY_KEY, 0)
    channel, marathon = await day_two_ahead(bot, cog)
    await set_up_for(bot, channel, WII)
    at_show(cog, DAY - 80)
    await tick(cog)
    await tick(cog)
    rows = await times(bot, marathon)
    assert (rows[WII]["state"], rows[WII]["scheduled_at"]) == (mt.LIVE, z(DAY - 80))
    assert len(off_the_sheet(rows)) == len(day_two_of(rows))
    assert await held_rows(bot) == 0 and await undone_rows(bot) == 0


async def test_staff_calling_a_days_first_run_live_80_minutes_early_is_never_held(bot, cog, helix):
    channel, marathon = await day_two_ahead(bot, cog)
    await set_up_for(bot, channel, WII)
    at_show(cog, DAY - 80)
    wii = (await times(bot, marathon))[WII]
    assert (await mark_live(bot, bot.guild, FakeActor(), marathon, wii)).ok
    await tick(cog)
    rows = await times(bot, marathon)
    assert (rows[WII]["state"], rows[WII]["live_because"]) == (mt.LIVE, mt.BY_STAFF)
    assert rows[WII]["actual_started_at"] == z(DAY - 80)
    assert await undone_rows(bot) == 0


async def reminder_rows(bot):
    cur = await bot.db.conn.execute(
        "SELECT kind, details FROM action_log "
        "WHERE kind IN ('marathon.reminded', 'marathon.would_remind') ORDER BY id"
    )
    return [(row["kind"], json.loads(row["details"])) for row in await cur.fetchall()]


async def test_the_early_key_is_10_by_default(bot, cog, helix):
    assert bot.store.get(GUILD, EARLY_KEY) == 10
    assert bot.store.get(GUILD, "marathon_ping_minutes") == 15


async def test_a_held_opener_of_ours_gets_its_15_minute_reminder_before_it_goes_live(
    bot, cog, helix
):
    await bot.store.set(GUILD, EARLY_KEY, 15)
    await bot.db.conn.execute(
        "INSERT INTO golive_links(user_id, twitch_login, linked_at) VALUES (4242, ?, ?)",
        ("dragonz4477", z(-9999)),
    )
    channel, marathon = await day_two_ahead(bot, cog)
    await set_up_for(bot, channel, WII)
    at_show(cog, DAY - 60)
    await tick(cog)
    wii = (await times(bot, marathon))[WII]
    assert mt.is_ours(wii) and wii["state"] == mt.UPCOMING
    assert await held_rows(bot) == 1 and await reminder_rows(bot) == []
    at_show(cog, DAY - 15)
    await tick(cog)
    wii = (await times(bot, marathon))[WII]
    assert (wii["state"], wii["actual_started_at"]) == (mt.LIVE, z(DAY - 15))
    assert mt.marks_of(wii) == [15, 120]
    said = await reminder_rows(bot)
    assert [(kind, details["mark"]) for kind, details in said] == [("marathon.reminded", 15)]
    assert said[0][1]["run_id"] == wii["id"] and said[0][1]["scheduled_at"] == z(DAY)
    logged = await kinds(bot.db)
    assert logged.index("marathon.reminded") < logged.index("marathon.run_live")
    at_show(cog, DAY - 14)
    await tick(cog)
    assert len(await reminder_rows(bot)) == 1


async def anchored_79_minutes_early(bot, cog):
    """The morning it happened: the channel set up for day 2 and the day was re-timed early;
    one of ours later in the day has its 2-hour reminder up."""
    await bot.store.set(GUILD, EARLY_KEY, 0)
    channel, marathon = await day_two_ahead(bot, cog)
    await set_up_for(bot, channel, WII)
    at_show(cog, DAY - 79)
    await tick(cog)
    await bot.store.set(GUILD, EARLY_KEY, 15)
    rows = await times(bot, marathon)
    assert rows[WII]["state"] == mt.LIVE and len(off_the_sheet(rows)) == len(day_two_of(rows))
    racers = rows[RACERS]
    people = [one | {"user_id": 4242} for one in mt.people_of(racers)]
    await cogmod.update_run(
        bot.db,
        racers["id"],
        people=json.dumps(people),
        reminders_sent=json.dumps([120, 1440]),
        reminder_posts=json.dumps({"120": {"posted": True}}),
    )
    return channel, marathon


async def test_a_first_run_anchored_79_minutes_early_is_put_back_and_nothing_is_posted(
    bot, cog, helix
):
    _channel, marathon = await anchored_79_minutes_early(bot, cog)
    assert mt.is_ours((await times(bot, marathon))[RACERS])
    for minutes in (-75, -74):
        at_show(cog, DAY + minutes)
        await tick(cog)
        rows = await times(bot, marathon)
        wii = rows[WII]
        assert (wii["state"], wii["live_because"]) == (mt.UPCOMING, None)
        assert (wii["actual_started_at"], wii["live_at"]) == (None, None)
        assert off_the_sheet(rows) == []
        assert mt.marks_of(rows[RACERS]) == [120, 1440]
        assert json.loads(rows[RACERS]["reminder_posts"]) == {"120": {"posted": True}}
        said = [one.content for chan in bot.guild.channels.values() for one in chan.messages]
        assert not any("<@&" in one or "Heads-up" in one for one in said)
        assert not [one for one in await kinds(bot.db) if "reminder" in one]
        assert await undone_rows(bot) == 1 and await held_rows(bot) == 0
    said = await details_of(bot.db, "marathon.early_start_undone")
    assert (said["game"], said["started_at"], said["planned_at"]) == (WII, z(DAY - 79), z(DAY))
    assert (await details_of(bot.db, "marathon.retimed"))["because"] == "early_start"

    at_show(cog, DAY - 5)
    await tick(cog)
    wii = (await times(bot, marathon))[WII]
    assert (wii["state"], wii["actual_started_at"]) == (mt.LIVE, z(DAY - 5))


async def test_a_first_run_anchored_early_stays_live_once_the_show_is_about_to_start(
    bot, cog, helix
):
    _channel, marathon = await anchored_79_minutes_early(bot, cog)
    before = day_two_of(await times(bot, marathon))
    at_show(cog, DAY - 15)
    await tick(cog)
    rows = await times(bot, marathon)
    assert rows[WII]["state"] == mt.LIVE and rows[WII]["actual_started_at"] == z(DAY - 79)
    assert day_two_of(rows) == before
    assert await undone_rows(bot) == 0
