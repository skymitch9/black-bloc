import json
import pathlib
from datetime import UTC, datetime, timedelta

from black_bloc import marathon as mt
from black_bloc import marathon_feeds as mf
from black_bloc import marathon_host_highlights as mhh
from black_bloc import marathon_hosts as mh
from black_bloc import marathon_hotfix as hf
from black_bloc import marathon_overlay as mo
from black_bloc import marathon_viewer as mv
from black_bloc.cogs.content import marathon as cogmod
from black_bloc.cogs.content import marathon_announce as announce
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
    hotfix_sheet,
    link_twitch,
    logged,
    pair_everywhere,
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
    await pair_everywhere(bot, "anarchy", ANARCHY)
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
    assert (await starts_of(bot, marathon))[1] == "2026-10-03T18:15:00+00:00"
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
    assert (await starts_of(bot, marathon))[1] == "2026-10-03T18:15:00+00:00"
    state = mo.state_of(await fresh_of(bot, marathon))
    assert state["applied"] is False and state["matched"] == 24
    assert await logged(bot, "marathon.overlay_applied") == []


async def test_with_no_viewer_the_gdq_sheet_path_is_exactly_as_it_was(bot, cog):  # noqa: F811
    await bot.store.set(GUILD, KEY, "")
    marathon = await gdqueer_of(bot, cog)
    starts = await starts_of(bot, marathon)
    assert starts[:2] == ["2026-10-03T17:00:00+00:00", "2026-10-03T18:15:00+00:00"]
    fresh = await fresh_of(bot, marathon)
    assert mo.state_of(fresh) is None and overlay_switch(bot, GUILD, fresh) is None
    plain = hf.parse_hotfix(hotfix_sheet(), ["GDQueer"], 7)[0]
    assert starts == [one.starts_at for one in plain.runs]
    assert fresh["ends_at"] == plain.ends_at


async def test_blanking_the_link_takes_the_overlay_off_and_says_so(bot, cog):  # noqa: F811
    ViewerReads(cog.client)
    marathon = await gdqueer_of(bot, cog)
    await bot.store.set(GUILD, KEY, "")
    await reread(bot, marathon)
    assert (await starts_of(bot, marathon))[1] == "2026-10-03T18:15:00+00:00"
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
    assert (await starts_of(bot, marathon))[1] == "2026-10-03T00:42:00+00:00"


# --- merge + review fixes (2026-10-03) ----------------------------------------------------------

JAYENA = 6102
BYSTANDER = 6103
HELD = ("scheduled_at", "ends_at", "reminders_sent", "previous_scheduled_at", "moved_at", "state")


async def test_a_done_or_live_run_is_never_moved_when_the_overlay_is_first_laid_over(bot, cog):  # noqa: F811
    await bot.store.set(GUILD, KEY, "")
    marathon = await gdqueer_of(bot, cog)
    runs = await runs_of(bot.db, marathon["id"])
    seen, over = "2026-10-03T17:04:00+00:00", "2026-10-03T18:12:00+00:00"
    await cogmod.update_run(
        bot.db,
        runs[0]["id"],
        state="done",
        actual_started_at=seen,
        actual_ended_at=over,
        scheduled_at=seen,
        ends_at=over,
    )
    await cogmod.update_run(bot.db, runs[1]["id"], state="done")
    await cogmod.update_run(bot.db, runs[2]["id"], state="live")
    before = [{key: one[key] for key in HELD} for one in await runs_of(bot.db, marathon["id"])]
    ViewerReads(cog.client)
    await bot.store.set(GUILD, KEY, PAGE)
    cog.clock = lambda: SEPT + timedelta(minutes=30)
    await reread(bot, marathon)
    assert mo.applied(await fresh_of(bot, marathon))
    after = await runs_of(bot.db, marathon["id"])
    for index in (0, 1, 2):
        assert {key: after[index][key] for key in HELD} == before[index]
    assert after[1]["sheet_at"] == "2026-10-03T18:18:00+00:00"
    live_ends = datetime.fromisoformat(after[2]["ends_at"])
    assert after[3]["scheduled_at"] == (live_ends + timedelta(minutes=10)).isoformat()
    held_ids = {after[index]["id"] for index in (0, 1, 2)}
    for row in await logged(bot, "marathon.retimed"):
        assert row["first"]["run_id"] not in held_ids
    moved = {one["run_id"] for one in await logged(bot, "marathon.member_run_moved")}
    assert not (moved & held_ids)
    assert await signals.retime(cog, bot.guild, marathon, because="again") == 0


async def test_a_member_who_only_commentates_never_makes_a_run_ours(bot, cog):  # noqa: F811
    ViewerReads(cog.client)
    await pair_everywhere(bot, "jayena", JAYENA)
    marathon = await gdqueer_of(bot, cog)
    dread = (await runs_of(bot.db, marathon["id"]))[-1]
    jayena = next(one for one in mt.people_of(dread) if one["name"] == "jayena")
    assert (jayena["part"], jayena["user_id"], jayena["counts"]) == ("commentator", JAYENA, False)
    assert not mt.is_ours(dread) and mt.member_ids(dread) == []
    assert await announce.baf_people(bot, bot.guild, await fresh_of(bot, marathon)) == {}
    assert mhh.blocks(await runs_of(bot.db, marathon["id"])) == []
    assert await logged(bot, "marathon.run_matched") == []
    assert hf.reasons_of("gdqueer", set(), [jayena | {"counts": None}]) == []
    await reread(bot, marathon)
    again = next(
        one
        for one in mt.people_of((await runs_of(bot.db, marathon["id"]))[-1])
        if one["name"] == "jayena"
    )
    assert again["counts"] is False


async def test_a_lent_login_never_pairs_the_member_who_owns_that_channel(bot, cog):  # noqa: F811
    ViewerReads(cog.client)
    await link_twitch(bot, BYSTANDER, "quacksilverplays")
    marathon = await gdqueer_of(bot, cog)
    quack = [
        one
        for row in await runs_of(bot.db, marathon["id"])
        for one in mt.people_of(row)
        if one["name"] == "Quacksilver"
    ]
    assert len(quack) == 2
    assert {(one["login"], one["login_from"], one["user_id"]) for one in quack} == {
        ("quacksilverplays", "viewer", None)
    }
    assert await logged(bot, "marathon.run_matched") == []


async def test_with_the_overlay_off_a_hotfix_marathon_is_on_the_buffer_clock(bot, cog):  # noqa: F811
    ViewerReads(cog.client)
    await bot.store.set(GUILD, "marathon_hotfix_overlay_default", False)
    marathon = await gdqueer_of(bot, cog)
    runs = await runs_of(bot.db, marathon["id"])
    assert [one["scheduled_at"] for one in runs[:3]] == [
        "2026-10-03T17:00:00+00:00",
        "2026-10-03T18:15:00+00:00",
        "2026-10-03T19:14:00+00:00",
    ]
    late = "2026-10-03T18:30:00+00:00"
    await cogmod.update_run(bot.db, runs[1]["id"], actual_started_at=late, state="live")
    assert await signals.retime(cog, bot.guild, marathon, because="stream") == 12
    starts = await starts_of(bot, marathon)
    assert starts[1:3] == [late, "2026-10-03T19:29:00+00:00"]
    assert starts[13] == "2026-10-04T17:00:00+00:00"


async def test_a_first_run_anchored_early_goes_back_to_the_organisers_times(bot, cog):  # noqa: F811
    ViewerReads(cog.client)
    marathon = await gdqueer_of(bot, cog)
    assert mo.applied(await fresh_of(bot, marathon))
    sheet = await starts_of(bot, marathon)
    runs = await runs_of(bot.db, marathon["id"])
    assert (runs[13]["game"], sheet[13]) == ("Wii Fit U", "2026-10-04T17:00:00+00:00")
    for one in runs[:13]:
        await cogmod.update_run(bot.db, one["id"], state="done")
    early = "2026-10-04T15:41:00+00:00"
    await cogmod.update_run(
        bot.db,
        runs[13]["id"],
        state="live",
        live_at=early,
        live_because=mt.BY_BOTH,
        actual_started_at=early,
    )
    assert await signals.retime(cog, bot.guild, marathon, because="stream") == 11
    assert (await starts_of(bot, marathon))[15] == "2026-10-04T17:44:00+00:00"

    now = datetime(2026, 10, 4, 16, 35, tzinfo=UTC)
    rows = await runs_of(bot.db, marathon["id"])
    assert await signals.undo_early(cog, bot.guild, marathon, rows, now) is True
    after = await runs_of(bot.db, marathon["id"])
    assert await starts_of(bot, marathon) == sheet and sheet[15] == "2026-10-04T19:03:00+00:00"
    assert (after[13]["state"], after[13]["live_because"]) == ("upcoming", None)
    assert (after[13]["actual_started_at"], after[13]["live_at"]) == (None, None)
    assert await signals.undo_early(cog, bot.guild, marathon, after, now) is False
    assert len(await logged(bot, "marathon.early_start_undone")) == 1


async def test_switching_the_overlay_mid_day_snaps_the_times_once_each_way(bot, cog):  # noqa: F811
    ViewerReads(cog.client)
    await bot.store.set(GUILD, "marathon_hotfix_overlay_default", False)
    marathon = await gdqueer_of(bot, cog)
    racers = next(
        one for one in await runs_of(bot.db, marathon["id"]) if one["game"].startswith("Dr. Rob")
    )
    assert racers["scheduled_at"] == "2026-10-04T18:57:00+00:00"
    await cogmod.update_run(
        bot.db,
        racers["id"],
        reminders_sent=json.dumps([15, 120]),
        reminder_posts=json.dumps({"15": {"posted": False}, "120": {"posted": False}}),
    )
    cog.clock = lambda: datetime(2026, 10, 4, 18, 45, tzinfo=UTC)

    async def racers_now():
        row = next(
            one for one in await runs_of(bot.db, marathon["id"]) if one["id"] == racers["id"]
        )
        return (row["scheduled_at"], mt.marks_of(row))

    async def changes():
        return len(await logged(bot, "marathon.schedule_changed"))

    base = await changes()
    on = await set_switch(bot, bot.guild, FakeActor(), marathon, mh.OVERLAY, True)
    assert on.ok
    assert await racers_now() == ("2026-10-04T19:03:00+00:00", [120])
    assert await changes() == base + 1
    cog.clock = lambda: datetime(2026, 10, 4, 18, 46, tzinfo=UTC)
    await reread(bot, marathon)
    assert await racers_now() == ("2026-10-04T19:03:00+00:00", [120])
    assert await changes() == base + 1
    fresh = await fresh_of(bot, marathon)
    assert (await set_switch(bot, bot.guild, FakeActor(), fresh, mh.OVERLAY, False)).ok
    assert await racers_now() == ("2026-10-04T18:57:00+00:00", [120])
    assert await changes() == base + 2
    fresh = await fresh_of(bot, marathon)
    assert (await set_switch(bot, bot.guild, FakeActor(), fresh, mh.OVERLAY, True)).ok
    assert await racers_now() == ("2026-10-04T19:03:00+00:00", [120])
    assert await changes() == base + 3


async def test_back_to_the_sheets_times_means_the_organisers_times_while_laid_over(bot, cog):  # noqa: F811
    ViewerReads(cog.client)
    marathon = await gdqueer_of(bot, cog)
    sheet = await starts_of(bot, marathon)
    runs = await runs_of(bot.db, marathon["id"])
    late = "2026-10-03T19:32:00+00:00"
    await cogmod.update_run(bot.db, runs[2]["id"], actual_started_at=late)
    assert await signals.retime(cog, bot.guild, marathon, because="stream") == 11
    assert (await starts_of(bot, marathon))[3] == "2026-10-03T19:57:00+00:00"
    back = await signals.sheet_times(bot, bot.guild, FakeActor(), marathon)
    assert back.ok and "11 run(s)" in back.message
    assert await starts_of(bot, marathon) == sheet
    assert sheet[1] == "2026-10-03T18:18:00+00:00"
    assert (await runs_of(bot.db, marathon["id"]))[2]["actual_started_at"] is None


# --- the 2026-10-05 typo fix: Metroid Dread renamed while it was on ------------------------------

MINIM = "metroid-dread/minim-items-glitchless"
MINIMUM = "metroid-dread/minimum-items-glitchless"
REAL_START = "2026-10-05T03:19:00+00:00"


async def dread_live(bot, cog):  # noqa: F811
    await cogmod.upsert_pairing(bot.db, GUILD, None, "champrul", CHAMPRUL, 7)
    marathon = await gdqueer_of(bot, cog)
    row = (await runs_of(bot.db, marathon["id"]))[-1]
    assert (row["game"], row["external_id"]) == ("Metroid Dread", MINIM)
    await cogmod.update_run(
        bot.db,
        row["id"],
        state=mt.LIVE,
        live_at=REAL_START,
        live_because="stream",
        actual_started_at=REAL_START,
        reminders_sent="[15, 120]",
    )
    return marathon, (await runs_of(bot.db, marathon["id"]))[-1]


async def typo_fixed(bot, cog, marathon):  # noqa: F811
    cog.client.sheet = cog.client.sheet.replace("Minim Items", "Minimum Items")
    cog.clock = lambda: SEPT + timedelta(minutes=30)
    await reread(bot, marathon)
    return await runs_of(bot.db, marathon["id"])


def hosts_and_voices(row):
    people = [one for one in mt.people_of(row) if one["part"] != "runner"]
    return [(one["name"], one.get("user_id")) for one in people]


async def assert_the_same_run(bot, marathon, before, rows):  # noqa: F811
    after = rows[-1]
    assert len(rows) == 24 and mt.DROPPED not in [one["state"] for one in rows]
    assert (after["id"], after["external_id"], after["state"]) == (before["id"], MINIMUM, mt.LIVE)
    kept = ("live_at", "live_because", "actual_started_at", "reminders_sent", "sheet_at")
    assert [after[key] for key in kept] == [before[key] for key in kept]
    assert after["category"] == "Minimum Items Glitchless"
    assert hosts_and_voices(after) == hosts_and_voices(before)
    changed = (await logged(bot, "marathon.schedule_changed"))[-1]
    assert [changed[key] for key in ("added", "dropped", "renamed")] == [0, 0, 1]
    (row,) = await logged(bot, "marathon.run_renamed")
    assert (row["run_id"], row["from_id"], row["to_id"]) == (before["id"], MINIM, MINIMUM)


async def test_the_typo_fix_keeps_the_live_run_under_the_organisers_sheet(bot, cog):  # noqa: F811
    ViewerReads(cog.client)
    marathon, before = await dread_live(bot, cog)
    assert ("champrul", CHAMPRUL) in hosts_and_voices(before)
    await assert_the_same_run(bot, marathon, before, await typo_fixed(bot, cog, marathon))


async def test_the_typo_fix_keeps_the_live_run_with_no_organisers_sheet(bot, cog):  # noqa: F811
    marathon, before = await dread_live(bot, cog)
    assert mo.state_of(await fresh_of(bot, marathon)) is None
    await assert_the_same_run(bot, marathon, before, await typo_fixed(bot, cog, marathon))


async def test_the_typo_fix_keeps_the_host_while_the_organisers_sheet_cannot_be_had(bot, cog):  # noqa: F811
    reads = ViewerReads(cog.client)
    marathon, before = await dread_live(bot, cog)
    mv.cache_of(cog).viewer = None
    reads.raises = ScheduleError("the Hotfix schedule viewer answered 503")
    rows = await typo_fixed(bot, cog, marathon)
    assert ("champrul", CHAMPRUL) in hosts_and_voices(rows[-1])
    await assert_the_same_run(bot, marathon, before, rows)
    assert mo.state_of(await fresh_of(bot, marathon))["stale"].endswith("answered 503")
