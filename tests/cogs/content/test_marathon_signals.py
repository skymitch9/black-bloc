# ruff: noqa: F401, F811
import asyncio
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
from black_bloc.cogs.content.spotlight import open_session, refresh_session_info, start_session
from black_bloc.golive import StreamInfo
from black_bloc.twitch import TwitchError, TwitchGame
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


def gdqueer_runs(*, kirby="0:15:00"):
    text = (FIXTURES / "gdq_hotfix_sheet.csv").read_text(encoding="utf-8")
    text = text.replace("Any% (Normal Mode),0:15:00", f"Any% (Normal Mode),{kirby}")
    return list(hf.parse_hotfix(text, ["GDQueer"])[0].runs)


def at_show(cog, minutes):
    cog.clock = lambda: SHOW + timedelta(minutes=minutes)


@pytest.fixture
def helix(bot):
    made = FakeCategories()
    bot.cogs["GoLive"] = FakeGoLive(made)
    return made


async def gdqueer(bot, cog):
    channel = await gdq_row(bot)
    cog.client.runs_given = gdqueer_runs()
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
