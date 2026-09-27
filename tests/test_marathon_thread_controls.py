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
    event, runs, spot, highlight = mtc.controls("marathon", ms.DARK)
    assert (event.to, event.word) == ("off", "on")
    assert (runs.to, runs.word) == ("on", "off")
    assert (spot.to, spot.word, spot.disabled) == ("on", "off", False)
    assert (highlight.action, highlight.to, highlight.word) == ("highlight", "on", "off")
    assert mtc.controls("none", ms.DARK, True)[3][1:3] == ("off", "on")


@pytest.mark.parametrize(
    ("state", "word", "to", "disabled"),
    [
        (ms.HELD, "on", "off", False),
        (ms.HELD_OTHER, "on", "off", False),
        (ms.UNTIL, "on", "off", False),
        (ms.SCHEDULED, "on", "off", False),
        (ms.KEPT, "kept", "off", False),
        (ms.WAITING, "off", "on", False),
        (ms.DARK, "off", "on", False),
        (ms.NO_CHANNEL, "none", "on", True),
    ],
)
def test_the_spotlight_button_reads_the_row_state(state, word, to, disabled):
    spot = mtc.controls("none", state)[2]
    assert (spot.word, spot.to, spot.disabled) == (word, to, disabled)


def test_the_custom_id_matches_the_template():
    found = re.fullmatch(mtc.TEMPLATE, mtc.custom_id(7, "spotlight", "off"))
    assert found and (found["marathon_id"], found["action"], found["to"]) == (
        "7",
        "spotlight",
        "off",
    )
    assert len(mtc.custom_id(10**18, "spotlight", "off")) <= 100


def test_the_highlight_custom_id_matches_the_template():
    found = re.fullmatch(mtc.TEMPLATE, mtc.custom_id(7, "highlight", "on"))
    assert found and (found["action"], found["to"]) == ("highlight", "on")


def test_a_label_is_clamped_and_never_empty():
    assert mtc.label("x" * 200) == "x" * 80
    assert mtc.label("  ") == "…"
