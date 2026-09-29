import json
import re
from types import SimpleNamespace

import pytest

from black_bloc import marathon_public as mp

SKY = json.dumps([{"name": "Sky", "user_id": 9001, "login": "skyruns", "part": "runner"}])
NOBODY = json.dumps([{"name": "Somebody", "user_id": None, "login": None, "part": "runner"}])


def a_row(state="upcoming", people=SKY, **fields):
    return {"id": 3, "state": state, "people": people, "game": "Celeste"} | fields


@pytest.mark.parametrize("to", [mp.OPT_OUT, mp.OPT_IN, mp.POST, mp.REMOVE])
def test_the_custom_id_matches_the_template_and_fits(to):
    found = re.fullmatch(mp.TEMPLATE, mp.custom_id(7, 3, to))
    assert found and (found["marathon_id"], found["run_id"], found["to"]) == ("7", "3", to)
    assert len(mp.custom_id(10**18, 10**18, mp.OPT_OUT)) <= 100


def test_a_button_posted_before_the_opt_out_maps_to_the_toggle():
    assert mp.move_of(mp.POST) == mp.OPT_IN and mp.move_of(mp.REMOVE) == mp.OPT_OUT
    assert mp.move_of(mp.OPT_OUT) == mp.OPT_OUT and mp.move_of(mp.OPT_IN) == mp.OPT_IN


def test_the_button_is_opt_out_until_everyone_on_the_run_is_out_and_none_for_nobody():
    kwargs = {"out_label": "Opt out of highlight", "in_label": "Opt back in"}
    assert mp.button_for(7, a_row(), opted=set(), **kwargs) == mp.Button(
        "marathon:highlight:7:3:optout", "Opt out of highlight", "optout"
    )
    assert mp.button_for(7, a_row(), opted={9001}, **kwargs) == mp.Button(
        "marathon:highlight:7:3:optin", "Opt back in", "optin"
    )
    up = a_row(public_message_id=55, public_channel_id=111)
    assert mp.button_for(7, up, opted=set(), **kwargs).to == mp.OPT_OUT
    assert mp.button_for(7, a_row(people=NOBODY), opted=set(), **kwargs) is None


def test_auto_wants_a_switched_on_marathon_and_a_run_never_highlighted():
    on, off = {"public_highlight": 1}, {"public_highlight": 0}
    assert mp.auto_wanted(on, a_row(state="live"))
    assert not mp.auto_wanted(off, a_row(state="live"))
    assert not mp.auto_wanted({}, a_row(state="live"))
    removed = a_row(state="live", public_message_id=55, public_removed=1)
    assert not mp.auto_wanted(on, removed)


@pytest.mark.parametrize(
    ("given", "wanted"),
    [
        (True, True),
        (False, False),
        ("on", True),
        ("Off", False),
        (1, True),
        (0, False),
        ("loud", None),
        (2, None),
    ],
)
def test_the_switch_takes_on_and_off_in_any_spelling(given, wanted):
    assert mp.clean_switch(given) is wanted


def test_a_fetched_message_says_which_button_it_carries():
    button = SimpleNamespace(custom_id="marathon:highlight:7:3:remove", label="Remove")
    message = SimpleNamespace(components=[SimpleNamespace(children=[button])])
    assert mp.shown_button(message) == mp.Button(
        "marathon:highlight:7:3:remove", "Remove", "remove"
    )
    assert mp.shown_button(SimpleNamespace(components=[])) is None
    assert mp.shown_button(SimpleNamespace()) is False


def test_a_label_is_clamped_and_never_empty():
    assert mp.label("x" * 200) == "x" * 80
    assert mp.label("  ") == "…"
