import json
import pathlib
from datetime import UTC, date, datetime, time, timedelta

import pytest

from black_bloc import marathon_viewer as mv
from black_bloc.doc_import import DocImportError, Hop
from black_bloc.marathon_sources import ScheduleClient, ScheduleError

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "marathon"
PAGE_HTML = (FIXTURES / "hotfix_viewer_page.html").read_text(encoding="utf-8")
SCRIPT = (FIXTURES / "hotfix_viewer_schedule.js").read_text(encoding="utf-8")
FEED = (FIXTURES / "hotfix_viewer_feed.json").read_text(encoding="utf-8")
ORGANISERS = (FIXTURES / "gdqueer_organisers.csv").read_text(encoding="utf-8")
PAGE = "https://ogndrahcir.github.io/ScheduleViewer/"
SCRIPT_URL = "https://ogndrahcir.github.io/ScheduleViewer/js/schedule.js"
DATA = (
    "https://script.google.com/macros/s/AKfycbyxanGFzAWbQV4Fso__LJh5eOb4GDjBYHx6sK79FTu3ww6z0sYs60"
    "3UbQeEr-aKRoK7/exec"
)
ECHO = "https://script.googleusercontent.com/macros/echo?user_content_key=abc"
SHORT = "https://gdq.gg/schedule/gdqueer"
SHORT_GDH = "https://gdq.gg/schedule/gdh"
KEY = "2PACX-1vSDxkXigxTofZG9IR7q8t2uXCOgR6zZnife29BUSnjQbJK1_a8L1jfu1RVXI4_M0zyikGniTx7zyEVz"
PUBHTML = f"https://docs.google.com/spreadsheets/u/1/d/e/{KEY}/pubhtml"
SHEET_PAGE = f"https://docs.google.com/spreadsheets/d/e/{KEY}/pubhtml"
CSV = f"https://docs.google.com/spreadsheets/d/e/{KEY}/pub?single=true&output=csv"
CONTENT = "https://doc-0g-3g-sheets.googleusercontent.com/pub/abc/def"
TRACKER = "https://gamesdonequick.com/schedule/71"


class Fake:
    def __init__(self, answers):
        self.answers = answers
        self.asked = []

    async def __call__(self, url, *, seconds, limit, agent):
        self.asked.append(url)
        found = self.answers.get(url)
        if isinstance(found, Exception):
            raise found
        return found or Hop(404)


def ok(text, kind="text/html"):
    return Hop(200, None, kind, text.encode("utf-8"))


def to(url, status=307):
    return Hop(status, url)


def live(**changes):
    answers = {
        PAGE: ok(PAGE_HTML),
        SCRIPT_URL: ok(SCRIPT, "application/javascript"),
        SHORT: to(PUBHTML),
        SHORT_GDH: to(TRACKER),
        CSV: to(CONTENT),
        CONTENT: ok(ORGANISERS, "text/csv"),
        DATA: to(ECHO, 302),
        ECHO: ok(FEED, "application/json"),
    }
    return Fake(answers | changes)


# --- the extractors, on the real page ---------------------------------------------------------


def test_the_page_names_its_own_script_and_never_one_from_another_host():
    assert mv.script_urls(PAGE_HTML, PAGE) == [SCRIPT_URL]
    elsewhere = '<script src="https://evil.example/x.js"></script><script src="js/a.js"></script>'
    assert mv.script_urls(elsewhere, PAGE) == [f"{PAGE}js/a.js"]


def test_the_script_names_its_feed_and_the_hosts_twitch_names():
    assert mv.data_url_of(SCRIPT) == DATA
    hosts = mv.hosts_of(SCRIPT)
    assert len(hosts) == 19
    assert hosts["anarchy"] == "anarchyasf"
    assert hosts["satanherself"] == "satanisntherself"
    assert hosts["helix"] == "helix13_"
    assert "creature corner" not in hosts


def test_the_footer_links_are_the_event_schedules_with_their_labels():
    assert mv.event_links(PAGE_HTML) == [
        mv.EventLink("Games Done Queer 📅 Oct 3-4", SHORT),
        mv.EventLink("Games Done Hitless 📅 Oct 23-25", SHORT_GDH),
    ]


@pytest.mark.parametrize(
    "garbage",
    ["", "<<<>>>", "const hostLinks = {", "hostLinks = { 'a': 5, b: 'twitch.tv/x' }", "\x00" * 50],
)
def test_garbage_reads_as_nothing_found_and_never_raises(garbage):
    assert mv.script_urls(garbage, PAGE) == []
    assert mv.data_url_of(garbage) is None
    assert mv.hosts_of(garbage) == {}
    assert mv.event_links(garbage) == []


def test_a_host_link_that_is_not_a_twitch_channel_is_left_out():
    script = (
        'const hostLinks = { "a": "https://youtube.com/@a", "b": "https://twitch.tv/b b", '
        '"c": "https://twitch.tv/Cee_1", "C": "https://twitch.tv/other" };'
    )
    assert mv.hosts_of(script) == {"c": "cee_1"}


def test_only_gdq_short_links_and_google_sheets_count_as_event_links():
    page = (
        '<a href="https://evil.example/x">Evil</a>'
        '<a class="b" href="http://gdq.gg/schedule/x"><b>An  event</b> &amp; more</a>'
        f'<a href="{PUBHTML}">Sheet</a><a href="javascript:alert(1)">x</a>'
    )
    assert mv.event_links(page) == [
        mv.EventLink("An event & more", "https://gdq.gg/schedule/x"),
        mv.EventLink("Sheet", PUBHTML),
    ]


def test_a_published_sheet_link_gives_its_page_and_csv_and_keeps_the_tab():
    assert mv.sheet_of(PUBHTML) == (SHEET_PAGE, CSV)
    tabbed = mv.sheet_of(
        f"https://docs.google.com/spreadsheets/d/e/{KEY}/pubhtml?gid=12&single=true"
    )
    assert tabbed == (
        f"{SHEET_PAGE}?gid=12",
        f"https://docs.google.com/spreadsheets/d/e/{KEY}/pub?gid=12&single=true&output=csv",
    )
    for other in (
        TRACKER,
        "https://docs.google.com/document/d/abc",
        f"http://docs.google.com/{KEY}",
        "",
    ):
        assert mv.sheet_of(other) is None


# --- the Sheets serials -----------------------------------------------------------------------


def test_a_show_date_is_midnight_eastern_in_summer_and_in_winter():
    assert mv.serial_day("2026-10-03T04:00:00.000Z") == date(2026, 10, 3)
    assert mv.serial_day("2026-03-01T05:00:00.000Z") == date(2026, 3, 1)
    assert mv.serial_day("2026-12-05T05:00:00.000Z") == date(2026, 12, 5)
    assert mv.serial_day("not a date") is None and mv.serial_day(None) is None


def test_a_start_serial_is_always_five_hours_ahead_and_may_cross_midnight():
    assert mv.serial_clock("1899-12-30T18:00:00.000Z") == time(13, 0)
    assert mv.serial_clock("1899-12-31T00:00:00.000Z") == time(19, 0)
    assert mv.serial_clock("1899-12-31T03:00:00.000Z") == time(22, 0)
    assert mv.serial_clock("1899-12-30T04:30:00.000Z") == time(23, 30)
    assert mv.serial_clock("") is None


def test_an_estimate_serial_is_a_length_not_a_clock():
    assert mv.serial_seconds("1899-12-30T06:08:00.000Z") == 68 * 60
    assert mv.serial_seconds("1899-12-30T07:15:30.000Z") == 2 * 3600 + 15 * 60 + 30
    assert mv.serial_seconds("1899-12-30T05:00:00.000Z") == 0
    assert mv.serial_seconds("x") is None


def test_the_feed_rows_read_with_their_eastern_starts_through_daylight_saving():
    rows = mv.feed_rows(json.loads(FEED))
    assert len(rows) == 30
    hidden = rows[0]
    assert (hidden.show, hidden.host, hidden.game, hidden.seconds) == (
        "Hidden Heroes",
        "anarchy",
        "Titanfall 2",
        85 * 60,
    )
    assert mv.starts_at(hidden).astimezone(UTC) == datetime(2026, 10, 2, 23, 0, tzinfo=UTC)
    spyro = next(one for one in rows if one.show == "GDQueer")
    assert mv.starts_at(spyro).astimezone(UTC) == datetime(2026, 10, 3, 17, 0, tzinfo=UTC)
    winter = mv.feed_rows(
        [
            {
                "Show Date": "2026-12-05T05:00:00.000Z",
                "Show Start (Eastern)": "1899-12-30T18:00:00.000Z",
                "Show": "GDQueer",
                "Game": "Spyro",
            }
        ]
    )
    assert mv.starts_at(winter[0]).astimezone(UTC) == datetime(2026, 12, 5, 18, 0, tzinfo=UTC)


def test_a_feed_that_is_not_a_list_is_refused_and_odd_rows_are_left_out():
    with pytest.raises(ScheduleError, match="list of rows"):
        mv.feed_rows({"error": "nope"})
    assert mv.feed_rows([1, "x", {}, {"Show": "A"}, {"Show": "A", "Game": "G"}]) == [
        mv.FeedRow("A", None, None, "", "G", "", None, "", "")
    ]


# --- the walk ---------------------------------------------------------------------------------


async def test_a_read_finds_the_hosts_the_feed_link_and_the_one_event_sheet():
    fake = live()
    viewer = await mv.read_viewer(fake, "agent", PAGE)
    assert viewer.data_url == DATA and len(viewer.hosts) == 19
    assert [(one.label, one.page, one.csv_url) for one in viewer.sheets] == [
        ("Games Done Queer 📅 Oct 3-4", SHEET_PAGE, CSV)
    ]
    assert viewer.sheets[0].text == ORGANISERS
    assert viewer.skipped == (
        (
            "Games Done Hitless 📅 Oct 23-25",
            "goes to gamesdonequick.com, which is not a published Google Sheet",
        ),
    )
    assert viewer.rows is None
    assert fake.asked == [PAGE, SCRIPT_URL, SHORT, CSV, CONTENT, SHORT_GDH]
    assert TRACKER not in fake.asked and DATA not in fake.asked


async def test_read_it_now_also_counts_the_feeds_rows_through_googles_redirect():
    fake = live()
    viewer = await mv.read_viewer(fake, "agent", PAGE, with_rows=True)
    assert viewer.rows == 30 and viewer.rows_trouble is None
    assert fake.asked[-2:] == [DATA, ECHO]
    assert mv.summary(viewer) == {
        "page": PAGE,
        "rows": 30,
        "rows_trouble": None,
        "feed": True,
        "hosts": 19,
        "events": [
            {"label": "Games Done Queer 📅 Oct 3-4", "href": SHORT, "sheet_url": SHEET_PAGE}
        ],
        "skipped": [
            {
                "label": "Games Done Hitless 📅 Oct 23-25",
                "why": "goes to gamesdonequick.com, which is not a published Google Sheet",
            }
        ],
    }


@pytest.mark.parametrize(
    "elsewhere",
    [
        "https://evil.example/feed",
        "http://script.googleusercontent.com/macros/echo",
        "https://script.googleusercontent.com.evil.example/x",
        "https://script.googleusercontent.com:8443/x",
        "https://169.254.169.254/latest/meta-data",
        "https://user@script.googleusercontent.com/x",
    ],
)
async def test_a_feed_redirect_off_the_list_is_refused_in_words_and_never_fetched(elsewhere):
    fake = live(**{DATA: to(elsewhere, 302)})
    viewer = await mv.read_viewer(fake, "agent", PAGE, with_rows=True)
    assert viewer.rows is None
    assert "which it does not fetch" in viewer.rows_trouble
    assert elsewhere not in fake.asked
    assert len(viewer.hosts) == 19 and len(viewer.sheets) == 1


async def test_a_page_redirect_off_the_list_is_refused_in_words():
    fake = live(**{PAGE: to("https://evil.example/")})
    with pytest.raises(ScheduleError, match="sent Black Bloc to evil.example, which it does not"):
        await mv.read_viewer(fake, "agent", PAGE)
    assert fake.asked == [PAGE]


async def test_a_sheet_redirect_off_the_list_skips_that_event_and_keeps_the_rest():
    fake = live(**{CSV: to("https://evil.example/sheet.csv")})
    viewer = await mv.read_viewer(fake, "agent", PAGE)
    assert viewer.sheets == ()
    assert viewer.skipped[0][0] == "Games Done Queer 📅 Oct 3-4"
    assert "evil.example, which it does not fetch" in viewer.skipped[0][1]
    assert "https://evil.example/sheet.csv" not in fake.asked
    assert len(viewer.hosts) == 19


async def test_a_short_link_that_does_not_redirect_or_cannot_be_reached_is_skipped():
    fake = live(**{SHORT: ok("hello"), SHORT_GDH: DocImportError(502, "timeout", "x")})
    viewer = await mv.read_viewer(fake, "agent", PAGE)
    assert viewer.sheets == ()
    assert viewer.skipped == (
        ("Games Done Queer 📅 Oct 3-4", "answered 200 instead of sending on to a sheet"),
        ("Games Done Hitless 📅 Oct 23-25", "timeout"),
    )


async def test_a_page_with_no_script_and_no_links_reads_as_nothing_found():
    fake = Fake({PAGE: ok("<html><body>moved</body></html>")})
    viewer = await mv.read_viewer(fake, "agent", PAGE, with_rows=True)
    assert (viewer.data_url, viewer.hosts, viewer.links, viewer.sheets) == (None, {}, (), ())
    assert viewer.rows is None and "names no schedule feed" in viewer.rows_trouble


async def test_a_script_that_cannot_be_read_still_gives_the_event_sheets():
    fake = live(**{SCRIPT_URL: Hop(500)})
    viewer = await mv.read_viewer(fake, "agent", PAGE)
    assert viewer.hosts == {} and len(viewer.sheets) == 1


async def test_a_page_that_is_down_or_too_big_is_a_failure_in_words():
    with pytest.raises(ScheduleError, match="Hotfix schedule viewer answered 503"):
        await mv.read_viewer(Fake({PAGE: Hop(503)}), "agent", PAGE)
    big = Hop(200, None, "text/html", b"x", True)
    with pytest.raises(ScheduleError, match="more than 1024 KB"):
        await mv.read_viewer(Fake({PAGE: big}), "agent", PAGE)


async def test_another_page_host_is_allowed_only_for_itself():
    other = "https://schedule.example.org/viewer/"
    fake = Fake(
        {
            other: ok('<script src="/s.js"></script>'),
            "https://schedule.example.org/s.js": ok(SCRIPT),
        }
    )
    viewer = await mv.read_viewer(fake, "agent", other)
    assert len(viewer.hosts) == 19
    allow = mv.allow_for(other)
    assert allow("https://schedule.example.org/x") and allow("https://gdq.gg/schedule/x")
    assert not allow(PAGE) and not allow("https://example.org/") and not allow("http://gdq.gg/x")


async def test_the_client_reads_the_viewer_through_its_own_hop():
    fake = live()
    client = ScheduleClient(hop_request=fake)
    viewer = await client.viewer(PAGE)
    assert viewer.page == PAGE and len(viewer.sheets) == 1


# --- the cache --------------------------------------------------------------------------------


def test_the_cache_is_fresh_for_five_minutes_for_the_same_page_and_waits_after_a_failure():
    now = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)
    cache = mv.ViewerCache()
    assert not cache.fresh(PAGE, now) and cache.copy_for(PAGE) is None
    cache.keep(mv.Viewer(page=PAGE), now)
    assert cache.fresh(PAGE, now + timedelta(seconds=299))
    assert not cache.fresh(PAGE, now + timedelta(seconds=300))
    assert not cache.fresh("https://other.example/", now)
    assert cache.copy_for("https://other.example/") is None
    cache.failed(PAGE, "down", now)
    assert cache.waiting(PAGE, now + timedelta(seconds=10))
    assert not cache.waiting(PAGE, now + timedelta(seconds=301))
    assert not cache.waiting("https://other.example/", now)
    cache.keep(mv.Viewer(page=PAGE), now)
    assert not cache.waiting(PAGE, now) and cache.trouble is None
