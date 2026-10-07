import re

import pytest

from black_bloc import marathon_spotlight as ms
from black_bloc import marathon_thread_controls as mtc


@pytest.mark.parametrize(
    ("marathon_on", "runs_on", "mode"),
    [
        (False, False, "none"),
        (True, False, "marathon"),
        (False, True, "runs"),
        (True, True, "both"),
    ],
)
def test_the_two_halves_make_the_four_modes(marathon_on, runs_on, mode):
    assert mtc.mode_from(marathon_on, runs_on) == mode
    assert mtc.halves(mode) == (marathon_on, runs_on)


@pytest.mark.parametrize(
    ("mode", "action", "to", "wanted"),
    [
        ("none", "event", "on", "marathon"),
        ("none", "runs", "on", "runs"),
        ("marathon", "runs", "on", "both"),
        ("both", "event", "off", "runs"),
        ("runs", "runs", "off", "none"),
        ("marathon", "event", "on", "marathon"),
        ("nonsense", "runs", "on", "runs"),
    ],
)
def test_a_press_moves_one_half_and_keeps_the_other(mode, action, to, wanted):
    assert mtc.wanted_mode(mode, action, to) == wanted


def test_each_button_carries_the_move_it_makes():
    event, runs, spot, highlight, ping, announce, hosts = mtc.controls("marathon", ms.DARK)
    assert (hosts.action, hosts.to, hosts.word) == ("hostannounce", "on", "off")
    hosts_on = mtc.controls("marathon", ms.DARK, host_announce=True)[6]
    assert (hosts_on.action, hosts_on.to, hosts_on.word) == ("hostannounce", "off", "on")
    assert (event.to, event.word) == ("off", "on")
    assert (runs.to, runs.word) == ("on", "off")
    assert (spot.to, spot.word, spot.disabled) == ("on", "off", False)
    assert (highlight.action, highlight.to, highlight.word) == ("highlight", "on", "off")
    assert (ping.action, ping.to, ping.word) == ("ping", "on", "off")
    assert (announce.action, announce.to, announce.word) == ("announce", "off", "on")
    off = mtc.controls("none", ms.DARK, False, False, False)[5]
    assert (off.action, off.to, off.word) == ("announce", "on", "off")
    assert {one.action for one in mtc.controls("both", ms.DARK)}.isdisjoint(mtc.RETIRED)
    assert mtc.controls("none", ms.DARK, True)[3][1:3] == ("off", "on")
    assert mtc.controls("none", ms.DARK, False, True)[4][1:3] == ("off", "on")
    assert mtc.controls("none", ms.DARK, True)[4][1:3] == ("on", "off")




@pytest.mark.parametrize(
    ("state", "word", "to", "disabled"),
    [
        (ms.HELD, "on", "off", False),
        (ms.HELD_OTHER, "on", "off", False),
        (ms.UNTIL, "on", "off", False),
        (ms.SCHEDULED, "on", "off", False),
        (ms.KEPT, "kept", "off", False),
        (ms.WAITING, "waiting", "cancel", False),
        (ms.DARK, "off", "on", False),
        (ms.NO_CHANNEL, "none", "on", True),
    ],
)
def test_the_spotlight_button_reads_the_row_state(state, word, to, disabled):
    spot = mtc.controls("none", state)[2]
    assert (spot.word, spot.to, spot.disabled) == (word, to, disabled)


@pytest.mark.parametrize(
    ("action", "to"),
    [("spotlight", "off"), ("spotlight", "cancel"), ("highlight", "on"), ("ping", "on")],
)
def test_the_custom_id_matches_the_template(action, to):
    assert action in mtc.ACTIONS
    found = re.fullmatch(mtc.TEMPLATE, mtc.custom_id(7, action, to))
    assert found and (found["marathon_id"], found["action"], found["to"]) == ("7", action, to)


def test_the_custom_id_fits_discords_hundred_characters():
    assert len(mtc.custom_id(10**18, "spotlight", "off")) <= 100


def test_a_label_is_clamped_and_never_empty():
    assert mtc.label("x" * 200) == "x" * 80
    assert mtc.label("  ") == "…"


def test_the_event_schedule_button_is_there_only_when_a_sheet_matches():
    assert len(mtc.controls("marathon", ms.DARK)) == 7
    on = mtc.controls("marathon", ms.DARK, overlay=True)[-1]
    assert (on.action, on.to, on.word) == ("overlay", "off", "on")
    off = mtc.controls("marathon", ms.DARK, overlay=False)[-1]
    assert (off.action, off.to, off.word) == ("overlay", "on", "off")
    assert mtc.custom_id(7, mtc.OVERLAY, mtc.OFF) == "marathon:controls:7:overlay:off"


def test_the_tracker_link_is_the_schedule_page_at_the_marathons_hash():
    assert mtc.tracker_url("https://blackbloc.heygabi.ai/", 9) == (
        "https://blackbloc.heygabi.ai/schedule.html#marathon-9"
    )
    assert mtc.tracker_url("", 9) is None
    assert mtc.tracker_url("blackbloc.heygabi.ai", 9) is None


@pytest.mark.parametrize("choice", ["follow", "yes", "no", None])
def test_the_baf_event_switch_is_three_buttons_in_their_own_row_with_the_standing_one_lit(choice):
    found = mtc.baf_controls(choice)
    standing = choice or "follow"
    assert [(one.action, one.to, one.row) for one in found] == [
        ("baf", "follow", 4),
        ("baf", "yes", 4),
        ("baf", "no", 4),
    ]
    assert [one.disabled for one in found] == [one.to == standing for one in found]
    assert [one.word for one in found] == ["on" if one.to == standing else "off" for one in found]
    for one in found:
        hit = re.fullmatch(mtc.TEMPLATE, mtc.custom_id(7, one.action, one.to))
        assert hit and (hit["action"], hit["to"]) == ("baf", one.to)
    assert len(mtc.controls("marathon", ms.DARK)) == 7


def test_the_three_baf_event_answers_have_one_home():
    from black_bloc import marathon_baf_event as baf

    assert mtc.BAF_CHOICES is baf.CHOICES
    assert (mtc.FOLLOW, mtc.YES, mtc.NO) == (baf.FOLLOW, baf.YES, baf.NO)


@pytest.mark.parametrize("choice", ["follow", "yes", "no"])
def test_a_stored_answer_adds_a_clear_button_and_follow_says_it_follows_the_answer(choice):
    found = mtc.baf_controls(choice, True)
    assert [(one.action, one.to, one.row) for one in found] == [
        ("baf", "follow", 4),
        ("baf", "yes", 4),
        ("baf", "no", 4),
        ("baf", "clear", 4),
    ]
    assert [one.label for one in found] == [mtc.FOLLOW_ANSWER, None, None, None]
    assert [one.disabled for one in found] == [one.to == choice for one in found]
    assert len(found) <= 5 and found[-1].word == "off"
    hit = re.fullmatch(mtc.TEMPLATE, mtc.custom_id(7, "baf", "clear"))
    assert hit and (hit["action"], hit["to"]) == ("baf", "clear")
    assert [one.label for one in mtc.baf_controls(choice)] == [None, None, None]
