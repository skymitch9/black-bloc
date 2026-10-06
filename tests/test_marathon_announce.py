import json

import pytest

from black_bloc import marathon_announce as ma

SKY = {"name": "Sky", "user_id": 9001, "login": "skyruns", "part": "runner"}
RIVET = {"name": "Rivet", "user_id": 9002, "login": None, "part": "runner"}


def test_the_switch_follows_the_setting_until_the_marathon_says_otherwise():
    assert ma.announces({"announcements": None}, True)
    assert not ma.announces({"announcements": None}, False)
    assert not ma.announces({"announcements": 0}, True)
    assert ma.announces({"announcements": 1}, False)
    assert ma.announces({}, True)


def test_the_opt_outs_read_back_as_ids_and_a_bad_column_reads_as_nobody():
    assert ma.opted_out({ma.OPTED: ma.dump([9002, "9001", 9001])}) == {9001, 9002}
    assert ma.opted_out({ma.OPTED: "not json"}) == set()
    assert ma.opted_out({ma.OPTED: json.dumps(["x", 5])}) == {5}
    assert ma.opted_out({}) == set()


def test_toggling_adds_or_takes_away_only_the_people_named():
    assert ma.toggled({1}, [2, 3], True) == {1, 2, 3}
    assert ma.toggled({1, 2}, [2], False) == {1}


def out(*ids):
    return ma.Policy(opted=frozenset(ids))


def test_a_runs_public_names_leave_out_whoever_opted_out():
    row = {"people": json.dumps([SKY, RIVET, {"name": "Nobody", "part": "runner"}])}
    assert [one["user_id"] for one in ma.run_people(row, ma.Policy())] == [9001, 9002]
    assert [one["user_id"] for one in ma.run_people(row, out(9001))] == [9002]
    assert ma.run_people(row, out(9001, 9002)) == []
    assert ma.all_out([9001, 9002], {9001, 9002}) and not ma.all_out([9001, 9002], {9001})
    assert not ma.all_out([], {9001})


@pytest.mark.parametrize(
    ("given", "wanted"),
    [(True, True), ("out", True), ("optout", True), ("remove", True), (False, False),
     ("in", False), ("optin", False), ("post", False), ("maybe", None), (None, None)],
)
def test_a_move_word_is_out_or_in(given, wanted):
    assert ma.clean_opt(given) is wanted
