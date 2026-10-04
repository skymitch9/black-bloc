import pathlib
from datetime import timedelta

from black_bloc import marathon_feeds as mf
from black_bloc import marathon_viewer as mv
from black_bloc.cogs.content import marathon_feeds as feeds
from black_bloc.cogs.content import marathon_viewer as viewers
from black_bloc.marathon_sources import ScheduleError
from tests.cogs.content.test_marathon import bot  # noqa: F401
from tests.cogs.content.test_marathon_feeds import (  # noqa: F401
    SEPT,
    all_feeds,
    cog,
    hotfix_feed,
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
