import json
import pathlib
from datetime import UTC, datetime

from black_bloc import marathon_feeds as mf

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "marathon"
SEPT = datetime(2026, 9, 25, 18, 0, tzinfo=UTC)
GDQ_BASE = "https://tracker.gamesdonequick.com/tracker"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def feed(**extra):
    row = {
        "id": 1,
        "source": mf.TRACKER,
        "feed_ref": GDQ_BASE,
        "name": "GDQ",
        "action": mf.ADD,
        "active": 1,
        "last_checked_at": None,
        "last_ok": None,
        "last_error": None,
        "suggested": "[]",
        "ignored": "[]",
    }
    return row | extra


def test_a_feed_names_the_marathon_source_it_makes():
    assert mf.marathon_source(feed()) == "gdq"
    assert mf.marathon_source(feed(feed_ref="https://tracker.rpglimitbreak.com")) == "rpglb"
    assert mf.marathon_source(feed(source=mf.HORARO_FEED, feed_ref="esa")) == "horaro"
    assert mf.marathon_source(feed(feed_ref="https://tracker.example.com")) is None
    assert mf.source_word(feed(source=mf.HORARO_FEED, feed_ref="esa")) == "horaro.net/esa"
    assert mf.source_word(feed()) == "GDQ tracker"


def test_the_three_seeds_are_the_gdq_rpglb_and_esa_channel_rows():
    assert [(one.login, mf.marathon_source(one._asdict())) for one in mf.SEEDS] == [
        ("gamesdonequick", "gdq"),
        ("rpglimitbreak", "rpglb"),
        ("esamarathon", "horaro"),
    ]


def test_tracker_candidates_are_the_events_ahead_drafts_kept_archived_dropped():
    found = mf.tracker_candidates("gdq", fixture("gdq_events_list.json")["results"], SEPT, 1)
    assert [one.ref for one in found] == ["71", "72", "73", "74"]
    agdq = found[-1]
    assert agdq.name == "Awesome Games Done Quick 2027"
    assert agdq.url == "https://tracker.gamesdonequick.com/tracker/event/74"


def test_a_tracker_event_that_began_within_the_recent_days_still_counts():
    rows = [{"id": 5, "name": "Now", "datetime": "2026-09-25T06:00:00+00:00"}]
    assert [one.ref for one in mf.tracker_candidates("gdq", rows, SEPT, 1)] == ["5"]
    assert mf.tracker_candidates("gdq", rows, SEPT, 0) == []
    archived = [dict(rows[0], archived=True)]
    assert mf.tracker_candidates("gdq", archived, SEPT, 1) == []


def test_rpglb_2026_is_behind_us_so_the_rpglb_feed_finds_nothing_today():
    rows = fixture("rpglb_events_list.json")["results"]
    assert mf.tracker_candidates("rpglb", rows, SEPT, 1) == []
    found = mf.tracker_candidates("rpglb", rows, datetime(2026, 5, 1, tzinfo=UTC), 1)
    assert [(one.ref, one.url) for one in found] == [
        ("21", "https://tracker.rpglimitbreak.com/event/21")
    ]


def test_horaro_candidates_are_the_schedules_that_have_not_ended():
    rows = fixture("horaro_esa_schedules.json")["data"]
    assert mf.horaro_candidates("esa", "ESA", rows, SEPT, 1) == []
    found = mf.horaro_candidates("esa", "ESA", rows, datetime(2026, 8, 5, tzinfo=UTC), 1)
    assert [(one.ref, one.name) for one in found] == [
        ("esa/2026-summer1", "ESA 2026 - Summer (Stream One)"),
        ("esa/2026-summer2", "ESA 2026 - Summer (Stream Two)"),
    ]
    assert found[1].url == "https://horaro.net/esa/2026-summer2"
    assert found[1].ends_at == "2026-08-07T21:56:00+00:00"


def test_fresh_never_offers_a_known_an_ignored_or_a_seen_event_twice():
    found = mf.tracker_candidates("gdq", fixture("gdq_events_list.json")["results"], SEPT, 1)
    left = mf.fresh(found, known={"74"}, ignored=["73"], seen=["72"])
    assert [one.ref for one in left] == ["71"]


def test_a_feed_is_due_when_never_checked_or_its_gap_has_passed_and_never_when_paused():
    assert mf.check_due(feed(), SEPT, 6)
    assert not mf.check_due(feed(last_checked_at="2026-09-25T13:00:00+00:00"), SEPT, 6)
    assert mf.check_due(feed(last_checked_at="2026-09-25T12:00:00+00:00"), SEPT, 6)
    assert not mf.check_due(feed(active=0), SEPT, 6)


def test_suggestions_split_into_open_and_dismissed_and_ignored_reads_a_list():
    records = [{"ref": "71", "dismissed_at": None}, {"ref": "72", "dismissed_at": "x"}]
    row = feed(suggested=json.dumps(records), ignored='["73", ""]')
    assert [one["ref"] for one in mf.open_suggestions(row)] == ["71"]
    assert [one["ref"] for one in mf.dismissed_of(row)] == ["72"]
    assert mf.ignored_of(row) == ["73"]
    assert mf.suggested_of(feed(suggested="not json")) == []


def test_the_moves_only_offer_what_changes_something():
    labels = [one.action for one in mf.feed_moves(feed())]
    assert mf.FEED_LOOK not in labels and mf.FEED_FORGET not in labels
    assert mf.FEED_PAUSE in labels
    busy = feed(active=0, action=mf.SUGGEST, ignored='["74"]', suggested='[{"ref": "1", '
                '"dismissed_at": "x"}]')
    labels = [one.action for one in mf.feed_moves(busy)]
    assert {mf.FEED_RESUME, mf.FEED_LOOK, mf.FEED_FORGET} <= set(labels)
    assert mf.FEED_TO_ADD_MOVE in mf.feed_moves(busy)


def test_a_pick_word_is_a_source_and_a_feed_reads_back_its_pick():
    assert mf.pick_of(" GDQ ") == (mf.TRACKER, GDQ_BASE)
    assert mf.pick_of("horaro") == (mf.HORARO_FEED, None)
    assert mf.pick_of("oengus") is None
    assert mf.pick_for(feed()) == "gdq"
    assert mf.pick_for(feed(source=mf.HORARO_FEED, feed_ref="esa")) == "horaro"


def test_the_feed_line_says_what_it_reads_and_when_it_last_did():
    line = mf.feed_line(feed(), "GamesDoneQuick", 6)
    assert "**GDQ** · GDQ tracker · GamesDoneQuick · adds · every 6 h · not checked yet" == line
    failed = feed(last_checked_at=SEPT.isoformat(), last_ok=0, last_error="boom", active=0)
    assert "could not be checked since" in mf.feed_line(failed, "x", 6)
    assert mf.feed_line(failed, "x", 6).endswith("· **paused**")
