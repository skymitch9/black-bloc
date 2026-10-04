import pathlib
from datetime import timedelta

from black_bloc import marathon as mt
from black_bloc import marathon_feeds as mf
from black_bloc import marathon_host_highlights as mhh
from black_bloc import marathon_hosts as mh
from black_bloc import marathon_overlay as mo
from black_bloc import marathon_viewer as mv
from black_bloc.cogs.content import marathon as cogmod
from black_bloc.cogs.content import marathon_feeds as feeds
from black_bloc.cogs.content import marathon_signals as signals
from black_bloc.cogs.content import marathon_viewer as viewers
from black_bloc.cogs.content.marathon import get_marathon, refresh_marathon, runs_of
from black_bloc.cogs.content.marathon_hosts import set_switch
from black_bloc.cogs.content.marathon_thread_controls import overlay_switch
from black_bloc.marathon_sources import ScheduleError
from tests.cogs.content.test_marathon import bot  # noqa: F401
from tests.cogs.content.test_marathon_feeds import (  # noqa: F401
    ANARCHY,
    SEPT,
    all_feeds,
    by_ref,
    cog,
    hotfix_feed,
    link_twitch,
    logged,
)
from tests.cogs.content.test_spotlight import GUILD, FakeActor

FIXTURES = pathlib.Path(__file__).parents[2] / "fixtures" / "marathon"
PAGE = "https://ogndrahcir.github.io/ScheduleViewer/"
KEY = "marathon_hotfix_viewer_url"
SHEET_PAGE = "https://docs.google.com/spreadsheets/d/e/abcdefghijklmnopqrstuvwxyz/pubhtml"


def the_viewer(page=PAGE, rows=None):
    script = (FIXTURES / "hotfix_viewer_schedule.js").read_text(encoding="utf-8")
    sheet = mv.EventSheet(
        "Games Done Queer 📅 Oct 3-4",
        "https://gdq.gg/schedule/gdqueer",
        SHEET_PAGE,
        "https://docs.google.com/spreadsheets/d/e/abcdefghijklmnopqrstuvwxyz/pub?output=csv",
        (FIXTURES / "gdqueer_organisers.csv").read_text(encoding="utf-8"),
    )
    return mv.Viewer(
        page=page,
        data_url="https://script.google.com/macros/s/abcdefghijklmnopqrstuvwxyz/exec",
        hosts=mv.hosts_of(script),
        sheets=(sheet,),
        skipped=(("Games Done Hitless", "goes to gamesdonequick.com, which is not a sheet"),),
        rows=rows,
    )


class ViewerReads:
    def __init__(self, client):
        self.calls = []
        self.raises = None
        self.answer = the_viewer
        client.viewer = self

    async def __call__(self, page_url, *, with_rows=False):
        self.calls.append((page_url, with_rows))
        if self.raises is not None:
            raise self.raises
        return self.answer(page_url, 61 if with_rows else None)


async def test_the_viewer_is_read_once_and_kept_for_five_minutes(bot, cog):  # noqa: F811
    reads = ViewerReads(cog.client)
    first, trouble = await viewers.viewer_of(bot, bot.guild)
    again, _ = await viewers.viewer_of(bot, bot.guild)
    assert trouble is None and first is again and len(first.hosts) == 19
    assert reads.calls == [(PAGE, False)]
    cog.clock = lambda: SEPT + timedelta(seconds=301)
    await viewers.viewer_of(bot, bot.guild)
    assert len(reads.calls) == 2


async def test_a_blank_link_turns_the_viewer_off_and_asks_nothing(bot, cog):  # noqa: F811
    reads = ViewerReads(cog.client)
    await bot.store.set(GUILD, KEY, "")
    assert await viewers.viewer_of(bot, bot.guild) == (None, None)
    assert reads.calls == []


async def test_a_client_that_cannot_read_a_viewer_reads_as_no_viewer(bot, cog):  # noqa: F811
    assert await viewers.viewer_of(bot, bot.guild) == (None, None)
    assert await logged(bot, "marathon.viewer_failed") == []


async def test_a_failed_read_keeps_the_last_copy_and_logs_the_reason_once(bot, cog):  # noqa: F811
    reads = ViewerReads(cog.client)
    good, _ = await viewers.viewer_of(bot, bot.guild)
    reads.raises = ScheduleError("the Hotfix schedule viewer answered 503")
    cog.clock = lambda: SEPT + timedelta(seconds=400)
    kept, trouble = await viewers.viewer_of(bot, bot.guild)
    assert kept is good and "answered 503" in trouble
    again, trouble = await viewers.viewer_of(bot, bot.guild)
    assert again is good and "answered 503" in trouble
    assert len(reads.calls) == 2
    cog.clock = lambda: SEPT + timedelta(seconds=800)
    await viewers.viewer_of(bot, bot.guild)
    assert len(reads.calls) == 3
    rows = await logged(bot, "marathon.viewer_failed")
    assert [(one["page"], one["reason"], one["kept_copy"]) for one in rows] == [
        (PAGE, "the Hotfix schedule viewer answered 503", True)
    ]


async def test_a_read_that_breaks_any_other_way_is_a_failure_too_never_a_crash(bot, cog):  # noqa: F811
    reads = ViewerReads(cog.client)
    reads.raises = RuntimeError("boom")
    assert await viewers.viewer_of(bot, bot.guild) == (None, "RuntimeError")
    assert [one["kept_copy"] for one in await logged(bot, "marathon.viewer_failed")] == [False]


async def test_a_changed_link_never_answers_the_old_pages_copy(bot, cog):  # noqa: F811
    reads = ViewerReads(cog.client)
    await viewers.viewer_of(bot, bot.guild)
    await bot.store.set(GUILD, KEY, "https://schedule.example.org/v/")
    found, _ = await viewers.viewer_of(bot, bot.guild)
    assert found.page == "https://schedule.example.org/v/"
    assert [page for page, _ in reads.calls] == [PAGE, "https://schedule.example.org/v/"]


async def test_read_it_now_says_what_was_found_and_logs_it(bot, cog):  # noqa: F811
    _row, feed = await hotfix_feed(bot, cog)
    reads = ViewerReads(cog.client)
    await viewers.viewer_of(bot, bot.guild)
    done = await viewers.read_now(bot, bot.guild, FakeActor(), feed)
    assert done.ok and reads.calls[-1] == (PAGE, True)
    assert done.message == (
        "Read the viewer: 61 schedule row(s), 19 host(s) with Twitch names, 1 event schedule(s). "
        "**Games Done Queer 📅 Oct 3-4** has its own schedule sheet. "
        "**Games Done Hitless** was not read — it goes to gamesdonequick.com, which is not a "
        "sheet."
    )
    assert (done.value["rows"], done.value["hosts"]) == (61, 19)
    assert done.value["events"][0]["sheet_url"] == SHEET_PAGE
    row = (await logged(bot, "marathon.viewer_read"))[-1]
    assert (row["rows"], row["hosts"], row["events"]) == (61, 19, ["Games Done Queer 📅 Oct 3-4"])


async def test_read_it_now_says_in_words_what_failed_or_that_it_is_off(bot, cog):  # noqa: F811
    _row, feed = await hotfix_feed(bot, cog)
    reads = ViewerReads(cog.client)
    reads.raises = ScheduleError("the Hotfix schedule viewer could not be reached (timeout)")
    failed = await viewers.read_now(bot, bot.guild, FakeActor(), feed)
    assert (failed.ok, failed.status, failed.code) == (False, 502, "unreadable")
    assert "could not be reached (timeout)" in failed.message
    assert "GDQ sheet is still read" in failed.message
    await bot.store.set(GUILD, KEY, "")
    off = await viewers.read_now(bot, bot.guild, FakeActor(), feed)
    assert (off.ok, off.status, off.code) == (False, 409, "viewer_off")
    other = next(one for one in await all_feeds(bot) if one["source"] != mf.HOTFIX_FEED)
    refused = await viewers.read_now(bot, bot.guild, FakeActor(), other)
    assert (refused.status, refused.code) == (409, "not_hotfix")


async def test_the_feed_card_names_the_viewer_link_or_says_it_is_off(bot, cog):  # noqa: F811
    _row, feed = await hotfix_feed(bot, cog)
    lines = feeds.shows_lines(bot, bot.guild, feed)
    assert lines[1].startswith(f"**Viewer:** <{PAGE}>")
    await bot.store.set(GUILD, KEY, "")
    assert "off (the link is blank)" in feeds.shows_lines(bot, bot.guild, feed)[1]


# --- hosts take their Twitch names ------------------------------------------------------------

HEROES = "hidden-heroes/2026-10-02"


async def heroes_of(bot, cog):  # noqa: F811
    await bot.store.set(GUILD, "marathon_hotfix_shows", "Hidden Heroes")
    await hotfix_feed(bot, cog)
    return (await by_ref(bot))[HEROES]


async def hosts_of(bot, marathon):  # noqa: F811
    return [
        person
        for row in await runs_of(bot.db, marathon["id"])
        for person in mt.people_of(row)
        if person["part"] == "host"
    ]


async def reread(bot, marathon):  # noqa: F811
    read = await refresh_marathon(bot, bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    assert read.ok, read.message


async def test_a_hotfix_host_takes_the_viewers_twitch_name_and_it_is_logged_once(bot, cog):  # noqa: F811
    ViewerReads(cog.client)
    await link_twitch(bot, ANARCHY, "anarchyasf")
    marathon = await heroes_of(bot, cog)
    hosts = await hosts_of(bot, marathon)
    assert len(hosts) == 3
    assert {(one["name"], one["login"], one["login_from"], one["user_id"]) for one in hosts} == {
        ("anarchy", "anarchyasf", "viewer", ANARCHY)
    }
    await reread(bot, marathon)
    rows = [one for one in await logged(bot, "marathon.viewer_logins")]
    assert [(one["marathon_id"], one["hosts"]) for one in rows] == [
        (marathon["id"], [{"name": "anarchy", "login": "anarchyasf"}])
    ]


async def test_a_staff_set_twitch_name_beats_the_viewers(bot, cog):  # noqa: F811
    ViewerReads(cog.client)
    await cogmod.upsert_pairing(bot.db, GUILD, None, "anarchy", ANARCHY, 7, "anarchy_own")
    marathon = await heroes_of(bot, cog)
    hosts = await hosts_of(bot, marathon)
    assert {(one["login"], one["sheet_login"], one["user_id"]) for one in hosts} == {
        ("anarchy_own", "anarchyasf", ANARCHY)
    }
    pairing = (await cogmod.pairings_of(bot.db, GUILD))[0]
    cleared = await cogmod.set_pairing_login(
        bot, bot.guild, FakeActor(), await get_marathon(bot.db, GUILD, marathon["id"]), pairing, ""
    )
    assert cleared.ok
    assert {(one["login"], one.get("sheet_login")) for one in await hosts_of(bot, marathon)} == {
        ("anarchyasf", None)
    }


async def test_with_the_link_blank_a_host_has_no_twitch_name_as_before(bot, cog):  # noqa: F811
    reads = ViewerReads(cog.client)
    await bot.store.set(GUILD, KEY, "")
    marathon = await heroes_of(bot, cog)
    assert {(one["login"], one.get("login_from")) for one in await hosts_of(bot, marathon)} == {
        (None, None)
    }
    assert reads.calls == [] and await logged(bot, "marathon.viewer_logins") == []


async def test_a_viewer_that_is_down_never_breaks_the_sheet_read_and_keeps_stored_names(bot, cog):  # noqa: F811
    reads = ViewerReads(cog.client)
    marathon = await heroes_of(bot, cog)
    assert {one["login"] for one in await hosts_of(bot, marathon)} == {"anarchyasf"}
    mv.cache_of(cog).viewer = None
    reads.raises = ScheduleError("the Hotfix schedule viewer answered 503")
    cog.clock = lambda: SEPT + timedelta(minutes=30)
    cog.client.sheet = cog.client.sheet.replace(
        "Titanfall 2,Any%,1:25:00", "Titanfall 2,Any%,1:35:00"
    )
    await reread(bot, marathon)
    runs = await runs_of(bot.db, marathon["id"])
    assert runs[0]["run_seconds"] == 95 * 60
    assert {one["login"] for one in await hosts_of(bot, marathon)} == {"anarchyasf"}
    fresh = await get_marathon(bot.db, GUILD, marathon["id"])
    assert fresh["last_fetch_ok"] == 1 and fresh["fetch_failures"] == 0


async def test_a_viewer_down_from_the_start_reads_the_sheet_alone(bot, cog):  # noqa: F811
    reads = ViewerReads(cog.client)
    reads.raises = ScheduleError("the Hotfix schedule viewer answered 503")
    marathon = await heroes_of(bot, cog)
    assert len(await runs_of(bot.db, marathon["id"])) == 3
    assert {one["login"] for one in await hosts_of(bot, marathon)} == {None}


# --- the event's own schedule sheet, laid over a Hotfix marathon --------------------------------

GDQUEER = "gdqueer/2026-10-03"
CHAMPRUL = 6101


async def gdqueer_of(bot, cog):  # noqa: F811
    await hotfix_feed(bot, cog)
    return (await by_ref(bot))[GDQUEER]


async def fresh_of(bot, marathon):  # noqa: F811
    return await get_marathon(bot.db, GUILD, marathon["id"])


async def starts_of(bot, marathon):  # noqa: F811
    return [one["scheduled_at"] for one in await runs_of(bot.db, marathon["id"])]


async def test_gdqueer_takes_the_organisers_times_hosts_and_commentators(bot, cog):  # noqa: F811
    ViewerReads(cog.client)
    marathon = await gdqueer_of(bot, cog)
    runs = await runs_of(bot.db, marathon["id"])
    assert [one["scheduled_at"] for one in runs[:3]] == [
        "2026-10-03T17:00:00+00:00",
        "2026-10-03T18:18:00+00:00",
        "2026-10-03T19:20:00+00:00",
    ]
    assert runs[1]["sheet_at"] == "2026-10-03T18:18:00+00:00"
    dread = [(one["name"], one["part"]) for one in mt.people_of(runs[-1])]
    assert dread == [
        ("araneacharlotte", "runner"),
        ("champrul", "host"),
        ("jayena", "commentator"),
        ("lucyna", "commentator"),
    ]
    quack = next(one for one in mt.people_of(runs[-2]) if one["part"] == "host")
    assert (quack["name"], quack["login"], quack["login_from"]) == (
        "Quacksilver",
        "quacksilverplays",
        "viewer",
    )
    state = mo.state_of(await fresh_of(bot, marathon))
    assert (state["label"], state["url"], state["runs"], state["matched"], state["applied"]) == (
        "Games Done Queer 📅 Oct 3-4",
        SHEET_PAGE,
        24,
        24,
        True,
    )
    await reread(bot, marathon)
    applied = await logged(bot, "marathon.overlay_applied")
    assert [(one["marathon_id"], one["matched"]) for one in applied] == [(marathon["id"], 24)]
    fresh = await fresh_of(bot, marathon)
    assert (fresh["starts_at"], fresh["ends_at"]) == (
        "2026-10-03T17:00:00+00:00",
        "2026-10-05T04:49:00+00:00",
    )


async def test_a_baf_host_on_the_organisers_sheet_is_found_like_any_host(bot, cog):  # noqa: F811
    ViewerReads(cog.client)
    await cogmod.upsert_pairing(bot.db, GUILD, None, "champrul", CHAMPRUL, 7)
    marathon = await gdqueer_of(bot, cog)
    hosted = [
        row["game"]
        for row in await runs_of(bot.db, marathon["id"])
        for one in mt.people_of(row)
        if one["part"] == "host" and one.get("user_id") == CHAMPRUL
    ]
    assert hosted == ["Isopod: A Webbed Spin-off", "Yakuza Kiwami 3 & Dark Ties", "Metroid Dread"]
    blocks = mhh.blocks(await runs_of(bot.db, marathon["id"]))
    assert [[one["game"] for one in block.runs] for block in blocks] == [
        ["Isopod: A Webbed Spin-off", "Yakuza Kiwami 3 & Dark Ties"],
        ["Metroid Dread"],
    ]


async def test_staff_switch_the_event_schedule_off_and_on_again(bot, cog):  # noqa: F811
    ViewerReads(cog.client)
    marathon = await gdqueer_of(bot, cog)
    off = await set_switch(bot, bot.guild, FakeActor(), marathon, mh.OVERLAY, False)
    assert off.ok and "keeps GDQ's sheet times" in off.message
    assert (await starts_of(bot, marathon))[1] == "2026-10-03T18:08:00+00:00"
    runs = await runs_of(bot.db, marathon["id"])
    assert [one["part"] for one in mt.people_of(runs[0])] == ["runner"]
    fresh = await fresh_of(bot, marathon)
    assert fresh["overlay"] == 0 and mo.state_of(fresh)["applied"] is False
    assert overlay_switch(bot, GUILD, fresh) is False
    dropped = await logged(bot, "marathon.overlay_dropped")
    assert [one["because"] for one in dropped] == ["switched_off"]
    assert [(one["from"], one["to"]) for one in await logged(bot, "marathon.overlay_set")] == [
        (None, False)
    ]
    back = await set_switch(bot, bot.guild, FakeActor(), fresh, mh.OVERLAY, "follow")
    assert back.ok and "from the event's own schedule sheet" in back.message
    assert (await starts_of(bot, marathon))[1] == "2026-10-03T18:18:00+00:00"
    assert overlay_switch(bot, GUILD, await fresh_of(bot, marathon)) is True
    assert not (await set_switch(bot, bot.guild, FakeActor(), fresh, mh.OVERLAY, "maybe")).ok


async def test_the_default_key_off_leaves_a_matching_sheet_named_but_not_laid_over(bot, cog):  # noqa: F811
    ViewerReads(cog.client)
    await bot.store.set(GUILD, "marathon_hotfix_overlay_default", False)
    marathon = await gdqueer_of(bot, cog)
    assert (await starts_of(bot, marathon))[1] == "2026-10-03T18:08:00+00:00"
    state = mo.state_of(await fresh_of(bot, marathon))
    assert state["applied"] is False and state["matched"] == 24
    assert await logged(bot, "marathon.overlay_applied") == []


async def test_with_no_viewer_the_gdq_sheet_path_is_exactly_as_it_was(bot, cog):  # noqa: F811
    await bot.store.set(GUILD, KEY, "")
    marathon = await gdqueer_of(bot, cog)
    starts = await starts_of(bot, marathon)
    assert starts[:2] == ["2026-10-03T17:00:00+00:00", "2026-10-03T18:08:00+00:00"]
    fresh = await fresh_of(bot, marathon)
    assert mo.state_of(fresh) is None and overlay_switch(bot, GUILD, fresh) is None
    assert fresh["ends_at"] == "2026-10-05T03:09:00+00:00"


async def test_blanking_the_link_takes_the_overlay_off_and_says_so(bot, cog):  # noqa: F811
    ViewerReads(cog.client)
    marathon = await gdqueer_of(bot, cog)
    await bot.store.set(GUILD, KEY, "")
    await reread(bot, marathon)
    assert (await starts_of(bot, marathon))[1] == "2026-10-03T18:08:00+00:00"
    assert mo.state_of(await fresh_of(bot, marathon)) is None
    assert [one["because"] for one in await logged(bot, "marathon.overlay_dropped")] == [
        "viewer_off"
    ]


async def test_a_sheet_that_cannot_be_had_keeps_the_overlay_until_staff_switch_it_off(bot, cog):  # noqa: F811
    reads = ViewerReads(cog.client)
    marathon = await gdqueer_of(bot, cog)
    before = await starts_of(bot, marathon)
    mv.cache_of(cog).viewer = None
    reads.raises = ScheduleError("the Hotfix schedule viewer answered 503")
    cog.clock = lambda: SEPT + timedelta(minutes=30)
    await reread(bot, marathon)
    assert await starts_of(bot, marathon) == before
    assert mo.state_of(await fresh_of(bot, marathon))["stale"].endswith("answered 503")
    reads.raises = None
    reads.answer = lambda page, rows: mv.Viewer(page=page)
    cog.clock = lambda: SEPT + timedelta(minutes=60)
    await reread(bot, marathon)
    assert await starts_of(bot, marathon) == before
    fresh = await fresh_of(bot, marathon)
    assert mo.state_of(fresh)["stale"] == mo.NO_LONGER_LINKED and mo.applied(fresh)
    assert len(await logged(bot, "marathon.overlay_kept")) == 1
    assert await logged(bot, "marathon.overlay_dropped") == []
    hosts = {
        one["name"]
        for row in await runs_of(bot.db, marathon["id"])
        for one in mt.people_of(row)
        if one["part"] == "host"
    }
    assert "champrul" in hosts and "Quacksilver" in hosts


async def test_a_run_seen_live_keeps_its_real_start_and_later_runs_follow_by_the_gaps(bot, cog):  # noqa: F811
    ViewerReads(cog.client)
    marathon = await gdqueer_of(bot, cog)
    runs = await runs_of(bot.db, marathon["id"])
    late = "2026-10-03T19:32:00+00:00"
    await cogmod.update_run(bot.db, runs[2]["id"], actual_started_at=late, state="live")
    moved = await signals.retime(cog, bot.guild, marathon, because="stream")
    assert moved == 11
    starts = await starts_of(bot, marathon)
    assert starts[:5] == [
        "2026-10-03T17:00:00+00:00",
        "2026-10-03T18:18:00+00:00",
        late,
        "2026-10-03T19:57:00+00:00",
        "2026-10-03T20:42:00+00:00",
    ]
    assert starts[13] == "2026-10-04T17:00:00+00:00"
    cog.client.sheet = cog.client.sheet.replace("Any% NG+,0:46:00", "Any% NG+,0:47:00")
    cog.clock = lambda: SEPT + timedelta(minutes=30)
    await reread(bot, marathon)
    again = await starts_of(bot, marathon)
    assert again[:5] == starts[:5] and again[13] == starts[13]
    rows = await runs_of(bot.db, marathon["id"])
    assert rows[3]["sheet_at"] == "2026-10-03T19:45:00+00:00"


async def test_a_gdq_sheet_marathon_without_a_sheet_keeps_the_old_clock(bot, cog):  # noqa: F811
    ViewerReads(cog.client)
    marathon = await heroes_of(bot, cog)
    fresh = await fresh_of(bot, marathon)
    assert mo.state_of(fresh) is None and overlay_switch(bot, GUILD, fresh) is None
    runs = await runs_of(bot.db, marathon["id"])
    late = "2026-10-02T23:10:00+00:00"
    await cogmod.update_run(bot.db, runs[0]["id"], actual_started_at=late, state="live")
    assert await signals.retime(cog, bot.guild, marathon, because="stream") == 3
    assert (await starts_of(bot, marathon))[1] == "2026-10-03T00:35:00+00:00"
