import re

import pytest

from black_bloc import marathon_baf_event as baf
from black_bloc import marathon_spotlight as ms
from black_bloc import marathon_thread_controls as mtc


def shape(found):
    return [(one.action, one.to, one.word, one.row) for one in found]


@pytest.mark.parametrize(
    ("mode", "action", "to", "wanted"),
    [
        ("none", "event", "on", "marathon"),
        ("runs", "event", "on", "both"),
        ("both", "event", "off", "runs"),
        ("marathon", "event", "off", "none"),
        ("marathon", "event", "on", "marathon"),
        ("nonsense", "event", "on", "marathon"),
    ],
)
def test_the_marathon_event_button_moves_only_its_half(mode, action, to, wanted):
    assert mtc.wanted_mode(mode, action, to) == wanted


def test_before_and_during_the_show_row_0_is_the_five_switches_and_row_1_the_link_and_baf():
    said = mtc.baf_control(None, baf.Judgement(baf.NO, baf.BY_MIXED, 55, 2))
    found = mtc.controls(
        "none",
        ms.DARK,
        follows=True,
        ping=False,
        announce=True,
        host_announce=False,
        baf=said,
    )
    assert shape(found) == [
        ("announce", "off", "on", 0),
        ("hostannounce", "on", "off", 0),
        ("ping", "on", "off", 0),
        ("spotlight", "off", "on", 0),
        ("event", "on", "off", 0),
        ("link", "", "", 1),
        ("baf", "yes", "off", 1),
    ]
    assert {one.action for one in found}.isdisjoint(mtc.RETIRED)


def test_after_the_show_only_the_link_and_archive_it_are_drawn():
    found = mtc.controls(
        "both", ms.HELD, follows=True, ping=True, announce=True, host_announce=True, over=True
    )
    assert shape(found) == [("link", "", "", 0), ("archive", "on", "archive", 0)]


@pytest.mark.parametrize(
    ("state", "drawn", "line"),
    [
        (ms.HELD, True, "until"),
        (ms.HELD_OTHER, True, "until"),
        (ms.UNTIL, True, "until"),
        (ms.SCHEDULED, True, "starts"),
        (ms.WAITING, True, "starts"),
        (ms.DARK, True, None),
        (ms.KEPT, False, "kept"),
        (ms.NO_CHANNEL, False, "none"),
    ],
)
def test_the_spotlight_switch_follows_the_schedule_and_dates_are_state(state, drawn, line):
    assert bool(mtc.spot_switch(state, True)) is drawn
    assert mtc.spot_line(state) == line


@pytest.mark.parametrize(("follows", "to", "word"), [(True, "off", "on"), (False, "on", "off")])
def test_the_spotlight_switch_reads_the_follow_not_the_row(follows, to, word):
    (spot,) = mtc.spot_switch(ms.HELD, follows)
    assert (spot.action, spot.to, spot.word) == ("spotlight", to, word)


@pytest.mark.parametrize(
    ("own", "judged", "to", "word", "label"),
    [
        (None, baf.Judgement(baf.NO, baf.BY_MIXED, 55, 2), "yes", "off", "said_no"),
        (None, baf.Judgement(baf.YES, baf.BY_NAME, 9, 0, "BiaF"), "no", "on", "said_yes"),
        (None, baf.Judgement(baf.YES, baf.BY_RUNS, 9, 9), "no", "on", "said_yes"),
        (None, baf.Judgement(baf.UNSURE, baf.BY_SHARE, 15, 12), "yes", "off", "said_unsure"),
        (None, baf.Judgement(baf.YES, baf.BY_LEADS, 15, 12), "clear", "on", "answered_yes"),
        (None, baf.Judgement(baf.NO, baf.BY_LEADS, 15, 12), "clear", "off", "answered_no"),
        (True, baf.Judgement(baf.NO, baf.BY_MIXED, 55, 2), "follow", "on", "staff_yes"),
        (False, baf.Judgement(baf.YES, baf.BY_NAME, 9, 0), "follow", "off", "staff_no"),
    ],
)
def test_the_baf_event_is_one_button_carrying_the_reading_and_its_one_reverse(
    own, judged, to, word, label
):
    found = mtc.baf_control(own, judged)
    assert (found.action, found.to, found.word, found.row, found.label) == (
        "baf",
        to,
        word,
        1,
        label,
    )
    hit = re.fullmatch(mtc.TEMPLATE, mtc.custom_id(7, found.action, found.to))
    assert hit and (hit["action"], hit["to"]) == ("baf", to)


@pytest.mark.parametrize(
    ("reason", "said"),
    [
        (baf.BY_NAME, "named"),
        (baf.BY_NO_RUNS, "no_runs"),
        (baf.BY_MIXED, "runs"),
        (baf.BY_SHARE, "runs"),
        (baf.BY_RUNS, "runs"),
        (baf.BY_FEW, "runs"),
        (baf.BY_ACTED, "runs"),
    ],
)
def test_the_baf_reason_is_the_name_or_the_count(reason, said):
    assert mtc.baf_reason(baf.Judgement(baf.NO, reason, 3, 1)) == said


@pytest.mark.parametrize(
    ("action", "to"),
    [
        ("spotlight", "off"),
        ("spotlight", "cancel"),
        ("ping", "on"),
        ("archive", "on"),
        ("runs", "on"),
        ("highlight", "on"),
        ("overlay", "off"),
        ("hostevents", "on"),
    ],
)
def test_every_custom_id_old_or_new_matches_the_template(action, to):
    assert action in mtc.ACTIONS + mtc.RETIRED
    found = re.fullmatch(mtc.TEMPLATE, mtc.custom_id(7, action, to))
    assert found and (found["marathon_id"], found["action"], found["to"]) == ("7", action, to)


def test_the_custom_id_fits_discords_hundred_characters():
    assert len(mtc.custom_id(10**18, "spotlight", "off")) <= 100


def test_a_label_is_clamped_and_never_empty():
    assert mtc.label("x" * 200) == "x" * 80
    assert mtc.label("  ") == "…"


def test_the_tracker_link_is_the_schedule_page_at_the_marathons_hash():
    assert mtc.tracker_url("https://blackbloc.heygabi.ai/", 9) == (
        "https://blackbloc.heygabi.ai/schedule.html#marathon-9"
    )
    assert mtc.tracker_url("", 9) is None
    assert mtc.tracker_url("blackbloc.heygabi.ai", 9) is None


def test_the_baf_answers_have_one_home():
    assert (mtc.FOLLOW, mtc.YES, mtc.NO, mtc.CLEAR) == (baf.FOLLOW, baf.YES, baf.NO, baf.CLEAR)


def test_a_spotlight_this_marathon_does_not_follow_reads_as_running_not_as_its_own():
    assert mtc.spot_line("until", False) == mtc.LINE_RUNNING
    assert mtc.spot_line("held_other", False) == mtc.LINE_RUNNING
    assert mtc.spot_line("until", True) == mtc.LINE_UNTIL
    assert mtc.spot_line("kept", False) == mtc.LINE_KEPT
    assert mtc.spot_line("off", False) is None


def test_no_known_end_is_never_after_the_show():
    from datetime import UTC, datetime

    now = datetime(2027, 1, 4, 18, 0, tzinfo=UTC)
    started = {"starts_at": "2027-01-01T00:00:00+00:00", "ends_at": None}
    assert mtc.after_show(started, now) is False
    assert mtc.after_show({**started, "ends_at": "2027-01-02T00:00:00+00:00"}, now) is True
    assert mtc.after_show({**started, "ends_at": "2027-01-05T00:00:00+00:00"}, now) is False
