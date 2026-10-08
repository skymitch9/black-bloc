import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from black_bloc import marathon as mt
from black_bloc.marathon_sources import Person, Run
from black_bloc.settings_store import (
    MARATHON_BOARD_LINE_KEY,
    MARATHON_BOARD_TEMPLATE_KEY,
    MARATHON_DEFAULTS,
    MARATHON_DONE_TEMPLATE_KEY,
    MARATHON_LIVE_TEMPLATE_KEY,
    MARATHON_REMINDER_TEMPLATE_KEY,
    MARATHON_WORDS,
    SettingError,
    coerce_value,
)

NOW = datetime(2027, 1, 4, 18, 0, tzinfo=UTC)


def iso(minutes: int) -> str:
    return (NOW + timedelta(minutes=minutes)).isoformat()


def row(ident, *, at, state=mt.UPCOMING, game="Game", people=None, order=None, **extra):
    return {
        "id": ident,
        "external_id": str(ident),
        "order_no": order if order is not None else ident,
        "game": game,
        "display_name": game,
        "twitch_game": extra.pop("twitch_game", ""),
        "category": "Any%",
        "scheduled_at": iso(at),
        "ends_at": iso(at + extra.pop("length", 60)),
        "state": state,
        "people": json.dumps(people or []),
        "reminders_sent": json.dumps(extra.pop("sent", [])),
        **extra,
    }


def run(ident, *, at, game="Game", people=()):
    return Run(str(ident), ident, game, game, "Any%", iso(at), iso(at + 60), 3600, tuple(people))


OURS = [{"name": "Sky", "login": "sky", "part": "runner", "user_id": 9}]


# --- matching ---------------------------------------------------------------------------------


def test_a_runner_is_ours_through_their_linked_twitch_login_whatever_its_case():
    found = mt.match_people([Person("Sky", "SkyRuns", "runner")], {"skyruns": 9}, [])
    assert found == [{"name": "Sky", "login": "SkyRuns", "part": "runner", "user_id": 9}]


def test_a_name_with_no_login_is_ours_through_a_staff_pairing():
    found = mt.match_people(
        [Person("Interview Crew", None, "host")],
        {},
        [{"marathon_id": None, "runner_name": "interview crew", "user_id": 5}],
    )
    assert found[0]["user_id"] == 5


def test_a_host_is_matched_only_while_hosts_are_scanned_and_a_commentator_is_not_affected():
    people = [Person("Crew", None, "host"), Person("Couch", None, "commentator")]
    pairings = [
        {"marathon_id": None, "runner_name": "crew", "user_id": 5},
        {"marathon_id": None, "runner_name": "couch", "user_id": 6},
    ]
    off = mt.match_people(people, {}, pairings, scan_hosts=False)
    assert [one["user_id"] for one in off] == [None, 6]
    on = mt.match_people(people, {}, pairings, scan_hosts=True)
    assert [one["user_id"] for one in on] == [5, 6]


def test_a_scanned_host_is_matched_but_makes_the_run_ours_only_while_hosts_count():
    people = [Person("Pilot", None, "runner"), Person("anarchy", None, "host")]
    pairings = [{"marathon_id": None, "runner_name": "anarchy", "user_id": 5}]
    shown = mt.match_people(people, {}, pairings, scan_hosts=True, hosts_count=False)
    assert [one["user_id"] for one in shown] == [None, 5]
    assert shown[1]["counts"] is False and "counts" not in shown[0]
    assert mt.ours(shown) == [] and not mt.is_ours({"people": json.dumps(shown)})
    counted = mt.match_people(people, {}, pairings, scan_hosts=True, hosts_count=True)
    assert "counts" not in counted[1]
    assert [one["user_id"] for one in mt.ours(counted)] == [5]


def test_a_runner_counts_whatever_hosts_count_says():
    people = [Person("Sky", None, "runner"), Person("anarchy", None, "host")]
    pairings = [
        {"marathon_id": None, "runner_name": "sky", "user_id": 4},
        {"marathon_id": None, "runner_name": "anarchy", "user_id": 5},
    ]
    for count in (False, True):
        found = mt.match_people(people, {}, pairings, scan_hosts=True, hosts_count=count)
        assert mt.ours(found)[0]["user_id"] == 4
        assert [one["user_id"] for one in mt.ours(found)] == ([4, 5] if count else [4])


def test_a_pairing_wins_over_the_automatic_match_and_this_marathons_wins_over_everywhere():
    people = [Person("Sky", "sky", "runner")]
    pairings = [
        {"marathon_id": None, "runner_name": "sky", "user_id": 2},
        {"marathon_id": 7, "runner_name": "sky", "user_id": 3},
        {"marathon_id": 8, "runner_name": "sky", "user_id": 4},
    ]
    assert mt.match_people(people, {"sky": 9}, pairings, marathon_id=7)[0]["user_id"] == 3
    assert mt.match_people(people, {"sky": 9}, pairings[:1], marathon_id=7)[0]["user_id"] == 2


def test_a_pairings_twitch_fix_replaces_the_sheets_login_and_clearing_it_restores_it():
    sheet = [Person("Jr", "Jr", "runner")]
    fixed = [{"marathon_id": 9, "runner_name": "jr", "user_id": 5, "twitch_login": "junior_sm"}]
    found = mt.match_people(sheet, {}, fixed, marathon_id=9)
    assert found == [
        {"name": "Jr", "login": "junior_sm", "part": "runner", "user_id": 5, "sheet_login": "Jr"}
    ]
    again = mt.match_people(found, {}, fixed, marathon_id=9)
    assert again == found
    cleared = [dict(fixed[0], twitch_login=None)]
    back = mt.match_people(found, {}, cleared, marathon_id=9)
    assert back == [{"name": "Jr", "login": "Jr", "part": "runner", "user_id": 5}]


def test_an_everywhere_fix_applies_on_every_schedule_and_matches_the_go_live_link():
    sheet = [Person("Jr", "Jr", "runner")]
    fixed = [{"marathon_id": None, "runner_name": "jr", "user_id": 5, "twitch_login": "junior_sm"}]
    for marathon_id in (3, 9):
        assert mt.match_people(sheet, {}, fixed, marathon_id=marathon_id)[0]["login"] == "junior_sm"
    here = [{"marathon_id": 9, "runner_name": "jr", "user_id": 5}]
    assert mt.match_people(sheet, {}, here, marathon_id=9)[0]["login"] == "Jr"
    assert mt.pairing_login({"twitch_login": " Junior_SM "}) == "junior_sm"
    assert mt.pairing_login(None) is None


def test_hosts_and_commentators_are_matched_only_while_the_key_says_so():
    people = [Person("Host", "hostlogin", "host"), Person("Com", "comlogin", "commentator")]
    links = {"hostlogin": 1, "comlogin": 2}
    assert [one["user_id"] for one in mt.match_people(people, links, [])] == [1, 2]
    off = mt.match_people(people, links, [], match_hosts=False)
    assert [one["user_id"] for one in off] == [None, None]


def test_ours_is_one_line_per_member_with_the_runner_part_first():
    people = [
        {"name": "Sky", "part": "commentator", "user_id": 9},
        {"name": "Sky", "part": "runner", "user_id": 9},
        {"name": "Other", "part": "runner", "user_id": None},
    ]
    assert mt.ours(people) == [{"name": "Sky", "part": "runner", "user_id": 9}]


def test_unmatched_names_are_every_name_nobody_owns_once():
    rows = [
        row(1, at=0, people=[{"name": "Gelly", "user_id": None}, {"name": "Sky", "user_id": 9}]),
        row(2, at=60, people=[{"name": "gelly", "user_id": None}]),
    ]
    assert mt.unmatched_names(rows) == ["Gelly"]


# --- the diff ---------------------------------------------------------------------------------


def test_a_new_run_is_inserted_and_a_known_one_is_updated_in_place():
    plan = mt.diff([row(1, at=0)], [run(1, at=0), run(2, at=60)], move_minutes=5)
    assert [one.external_id for one in plan.inserts] == ["2"]
    assert [(one[0]["id"], one[2]) for one in plan.updates] == [(1, False)]


def test_a_move_under_the_threshold_is_not_a_move_and_one_at_it_is():
    under = mt.diff([row(1, at=0)], [run(1, at=4)], move_minutes=5)
    at = mt.diff([row(1, at=0)], [run(1, at=5)], move_minutes=5)
    earlier = mt.diff([row(1, at=0)], [run(1, at=-40)], move_minutes=5)
    assert under.moved == []
    assert len(at.moved) == 1
    assert len(earlier.moved) == 1


def test_a_run_missing_from_the_fetch_is_dropped_and_a_done_one_is_left_as_history():
    plan = mt.diff([row(1, at=0), row(2, at=-120, state=mt.DONE)], [], move_minutes=5)
    assert [one["id"] for one in plan.dropped] == [1]


def test_a_dropped_run_that_reappears_is_named_so_it_goes_back_to_upcoming():
    plan = mt.diff([row(1, at=0, state=mt.DROPPED)], [run(1, at=0)], move_minutes=5)
    assert [one["id"] for one in plan.reappeared] == [1]
    assert plan.dropped == []


def runners(*names):
    return [{"name": name, "login": None, "part": "runner", "user_id": None} for name in names]


def kept(ident, key, *, at, order, names=("Sky",), game="Dread", state=mt.UPCOMING, **extra):
    people = runners(*names) + extra.pop("others", [])
    found = row(ident, at=at, state=state, game=game, people=people, order=order, **extra)
    return found | {"external_id": key, "sheet_at": iso(at)}


def fresh(key, *, at, order, names=("Sky",), game="Dread", others=()):
    people = tuple(Person(name, None, "runner") for name in names) + tuple(others)
    return Run(key, order, game, game, "Any%", iso(at), iso(at + 60), 3600, people)


def pairs(found):
    return [
        (one["id"], other.external_id if isinstance(other, Run) else other) for one, other in found
    ]


def test_a_row_dropped_beside_its_own_slots_new_id_is_the_same_run_renamed():
    live = kept(2, "dread/minim", at=60, order=2, state=mt.LIVE)
    stored = [kept(1, "a/any", at=0, order=1), live]
    read = [fresh("a/any", at=0, order=1), fresh("dread/minimum", at=60, order=2)]
    plan = mt.diff(stored, read, move_minutes=5)
    assert pairs(plan.renamed) == [(2, "dread/minimum")]
    assert pairs(plan.rekeyed) == [(2, "dread/minimum")]
    assert plan.inserts == [] and plan.dropped == [] and plan.reappeared == []
    assert [(one[0]["id"], one[1].external_id, one[2]) for one in plan.updates] == [
        (1, "a/any", False),
        (2, "dread/minimum", False),
    ]


def test_nothing_is_paired_when_nothing_is_both_dropped_and_added():
    stored = [kept(1, "a", at=0, order=1), kept(2, "b", at=60, order=2)]
    more = [fresh("a", at=0, order=1), fresh("c", at=0, order=1)]
    assert mt.renames(stored, [fresh("a", at=0, order=1)], minutes=5) == []
    assert mt.renames(stored[:1], more, minutes=5) == []


@pytest.mark.parametrize(
    ("at", "order", "same"),
    [
        (60, 9, True),
        (64, 9, True),
        (65, 9, False),
        (65, 2, True),
        (60 + 11 * 60, 2, True),
        (60 + 12 * 60, 2, False),
    ],
)
def test_the_slot_is_the_planned_start_or_the_place_in_one_day(at, order, same):
    stored = kept(2, "b", at=60, order=2)
    assert mt.same_slot(stored, fresh("c", at=at, order=order), minutes=5) is same


def test_a_slot_with_no_times_goes_by_the_order_alone():
    bare = kept(2, "b", at=60, order=2) | {"sheet_at": None, "scheduled_at": None}
    assert mt.same_slot(bare, fresh("c", at=999, order=2), minutes=5)
    assert not mt.same_slot(bare, fresh("c", at=60, order=3), minutes=5)


def test_the_runners_decide_and_hosts_and_commentators_take_no_part():
    host = [{"name": "Champ", "login": None, "part": "host", "user_id": 7}]
    stored = kept(2, "b", at=60, order=2, names=("Sky", "  RIVER "), others=host)
    voice = (Person("Other", None, "commentator"),)
    same = fresh("c", at=60, order=2, names=("river", "sky"), others=voice)
    assert mt.same_slot(stored, same, minutes=5)
    assert not mt.same_slot(stored, fresh("c", at=60, order=2, names=("Sky",)), minutes=5)
    assert not mt.same_slot(stored, fresh("c", at=60, order=2, names=("Sky", "Ash")), minutes=5)


def test_with_no_runners_on_either_side_the_titles_must_be_alike():
    stored = kept(2, "b", at=60, order=2, names=(), game="Super Metroid")

    def read(game, names=()):
        return fresh("c", at=60, order=2, names=names, game=game)

    assert mt.same_slot(stored, read("Super Metriod!"), minutes=5)
    assert not mt.same_slot(stored, read("Celeste"), minutes=5)
    assert not mt.same_slot(stored, read("Super Metroid", ("Sky",)), minutes=5)
    blank = kept(3, "d", at=60, order=2, names=(), game="")
    assert not mt.same_slot(blank, read(""), minutes=5)


def test_a_new_runner_in_the_same_slot_is_a_drop_and_an_add():
    read = [fresh("c", at=60, order=2, names=("Ash",))]
    plan = mt.diff([kept(2, "b", at=60, order=2)], read, move_minutes=5)
    assert plan.renamed == [] and plan.rekeyed == []
    assert [one.external_id for one in plan.inserts] == ["c"]
    assert [one["id"] for one in plan.dropped] == [2]


def test_one_row_fitting_two_runs_is_paired_with_neither():
    stored = [kept(2, "b", at=60, order=2)]
    read = [fresh("c", at=60, order=2), fresh("d", at=62, order=3)]
    plan = mt.diff(stored, read, move_minutes=5)
    assert plan.renamed == []
    assert [one.external_id for one in plan.inserts] == ["c", "d"]
    assert [one["id"] for one in plan.dropped] == [2]


def test_two_rows_fitting_one_run_are_paired_with_nothing():
    stored = [kept(2, "b", at=60, order=2), kept(3, "c", at=62, order=3)]
    plan = mt.diff(stored, [fresh("d", at=61, order=2)], move_minutes=5)
    assert plan.renamed == []
    assert [one["id"] for one in plan.dropped] == [2, 3]


def test_one_ambiguous_row_does_not_stop_a_clear_pair():
    stored = [kept(1, "a", at=0, order=1, names=("Ash",)), kept(2, "b", at=600, order=5)]
    read = [
        fresh("a2", at=0, order=1, names=("Ash",)),
        fresh("c", at=600, order=5),
        fresh("d", at=602, order=6),
    ]
    plan = mt.diff(stored, read, move_minutes=5)
    assert pairs(plan.renamed) == [(1, "a2")]
    assert [one["id"] for one in plan.dropped] == [2]


def test_two_runs_swapping_slots_keep_their_ids_and_are_only_moved():
    stored = [kept(1, "a", at=0, order=1), kept(2, "b", at=60, order=2, names=("Ash",))]
    read = [fresh("b", at=0, order=1, names=("Ash",)), fresh("a", at=60, order=2)]
    plan = mt.diff(stored, read, move_minutes=5)
    assert plan.renamed == [] and plan.inserts == [] and plan.dropped == []
    assert sorted((one[0]["id"], one[1].external_id, one[2]) for one in plan.updates) == [
        (1, "a", True),
        (2, "b", True),
    ]


def test_two_renamed_runs_each_keep_their_own_slot():
    stored = [kept(1, "a", at=0, order=1, game="Celeste"), kept(2, "b", at=60, order=2)]
    read = [fresh("a2", at=0, order=1, game="Celeste"), fresh("b2", at=60, order=2)]
    assert pairs(mt.renames(stored, read, minutes=5)) == [(1, "a2"), (2, "b2")]


def test_a_rename_beside_an_unrelated_add_is_one_of_each():
    stored = [kept(1, "a", at=0, order=1)]
    read = [fresh("a2", at=0, order=1), fresh("z", at=60, order=2, names=("Ash",))]
    plan = mt.diff(stored, read, move_minutes=5)
    assert pairs(plan.renamed) == [(1, "a2")]
    assert [one.external_id for one in plan.inserts] == ["z"]
    assert plan.dropped == []


def test_a_done_run_renamed_keeps_its_row_and_is_not_added_again():
    stored = [kept(1, "a", at=-120, order=1, state=mt.DONE)]
    plan = mt.diff(stored, [fresh("a2", at=-120, order=1)], move_minutes=5)
    assert pairs(plan.renamed) == [(1, "a2")]
    assert plan.inserts == [] and plan.dropped == []


def test_a_dropped_row_is_never_renamed_and_still_comes_back_under_its_own_id():
    stored = [kept(1, "a", at=0, order=1, state=mt.DROPPED)]
    gone = mt.diff(stored, [fresh("a2", at=0, order=1)], move_minutes=5)
    back = mt.diff(stored, [fresh("a", at=0, order=1)], move_minutes=5)
    assert gone.renamed == [] and [one.external_id for one in gone.inserts] == ["a2"]
    assert back.renamed == [] and [one["id"] for one in back.reappeared] == [1]


def test_a_flip_back_onto_a_dropped_rows_id_keeps_the_live_row_and_swaps_the_ids():
    stored = [
        kept(163, "dread/minim", at=60, order=2, state=mt.DROPPED),
        kept(176, "dread/minimum", at=60, order=2, state=mt.LIVE),
    ]
    plan = mt.diff(stored, [fresh("dread/minim", at=60, order=2)], move_minutes=5)
    assert pairs(plan.renamed) == [(176, "dread/minim")]
    assert pairs(plan.rekeyed) == [(176, "dread/minim"), (163, "dread/minimum")]
    assert [(one[0]["id"], one[1].external_id) for one in plan.updates] == [(176, "dread/minim")]
    assert plan.reappeared == [] and plan.dropped == [] and plan.inserts == []


def test_the_first_of_two_repeats_renamed_leaves_both_rows_in_their_slots():
    stored = [kept(1, "g/c", at=0, order=1), kept(2, "g/c#2", at=60, order=2)]
    read = [fresh("g/cc", at=0, order=1), fresh("g/c", at=60, order=2)]
    plan = mt.diff(stored, read, move_minutes=5)
    assert sorted(pairs(plan.renamed)) == [(1, "g/cc"), (2, "g/c")]
    assert sorted(pairs(plan.rekeyed)) == [(1, "g/cc"), (2, "g/c")]
    assert plan.inserts == [] and plan.dropped == [] and plan.moved == []


def test_the_first_of_three_repeats_renamed_leaves_all_three_in_their_slots():
    old, new = ("g/c", "g/c#2", "g/c#3"), ("g/cc", "g/c", "g/c#2")
    stored = [kept(n, key, at=60 * n, order=n) for n, key in enumerate(old, 1)]
    read = [fresh(key, at=60 * n, order=n) for n, key in enumerate(new, 1)]
    plan = mt.diff(stored, read, move_minutes=5)
    assert sorted(pairs(plan.renamed)) == [(1, "g/cc"), (2, "g/c"), (3, "g/c#2")]
    assert plan.inserts == [] and plan.dropped == [] and plan.moved == []


def test_the_second_of_two_repeats_renamed_is_one_plain_rename():
    stored = [kept(1, "g/c", at=0, order=1), kept(2, "g/c#2", at=60, order=2)]
    read = [fresh("g/c", at=0, order=1), fresh("g/cc", at=60, order=2)]
    assert pairs(mt.diff(stored, read, move_minutes=5).renamed) == [(2, "g/cc")]


def test_a_repeat_removed_beside_an_unrelated_add_is_left_as_it_was():
    stored = [kept(1, "g/c", at=0, order=1), kept(2, "g/c#2", at=60, order=2)]
    read = [fresh("g/c", at=60, order=1), fresh("z", at=300, order=2, names=("Ash",))]
    plan = mt.diff(stored, read, move_minutes=5)
    assert plan.renamed == []
    assert [one["id"] for one in plan.dropped] == [2]
    assert [(one[0]["id"], one[2]) for one in plan.updates] == [(1, True)]
    assert [one.external_id for one in plan.inserts] == ["z"]


def test_a_displaced_dropped_row_takes_an_id_the_renames_left_free():
    stored = [kept(1, "a", at=0, order=1), kept(9, "b", at=0, order=1, state=mt.DROPPED)]
    found = mt.rekeys(stored, [(stored[0], fresh("b", at=0, order=1))])
    assert pairs(found) == [(1, "b"), (9, "a")]


def worded(found, category):
    if isinstance(found, Run):
        return replace(found, category=category)
    return found | {"category": category}


@pytest.mark.parametrize(
    ("was", "now", "same"),
    [
        (
            ("Metroid Dread", "Minim Items Glitchless"),
            ("Metroid Dread", "Minimum Items Glitchless"),
            True,
        ),
        (("Donkey Kong Country 2", "102%"), ("Donkey Kong Country 2", "True Ending"), False),
        (("Donkey Kong Country 2", "102%"), ("Donkey Kong Country 2", "Any%"), False),
        (("Tetris", "Any%"), ("tetris", "ANY %"), True),
        (("", ""), ("", ""), False),
    ],
)
def test_words_are_alike_for_a_typo_and_not_for_another_category(was, now, same):
    stored = worded(kept(1, "a", at=0, order=1, game=was[0]), was[1])
    read = worded(fresh("b", at=0, order=1, game=now[0]), now[1])
    assert mt.same_words(stored, read) is same


@pytest.mark.parametrize("state", [mt.UPCOMING, mt.LIVE, mt.DONE])
def test_a_run_retitled_as_the_one_before_it_is_deleted_never_takes_that_runs_row(state):
    game = "Donkey Kong Country 2"
    first = worded(kept(1, "dkc2/102", at=0, order=1, game=game, state=state, sent=[120]), "102%")
    second = worded(kept(2, "dkc2/true-endng", at=60, order=2, game=game), "True Endng")
    read = [worded(fresh("dkc2/true-ending", at=0, order=1, game=game), "True Ending")]
    plan = mt.diff([first, second], read, move_minutes=5)
    assert plan.renamed == [] and plan.rekeyed == [] and plan.updates == []
    assert [one.external_id for one in plan.inserts] == ["dkc2/true-ending"]
    assert [one["id"] for one in plan.dropped] == ([2] if state == mt.DONE else [1, 2])


def test_of_two_lost_rows_by_one_runner_the_one_that_reads_alike_in_the_slot_is_paired():
    game = "Donkey Kong Country 2"
    first = worded(kept(1, "dkc2/102", at=0, order=1, game=game), "102%")
    second = worded(kept(2, "dkc2/true-endng", at=60, order=2, game=game), "True Endng")
    read = [worded(fresh("dkc2/true-ending", at=60, order=2, game=game), "True Ending")]
    plan = mt.diff([first, second], read, move_minutes=5)
    assert pairs(plan.renamed) == [(2, "dkc2/true-ending")]
    assert [one["id"] for one in plan.dropped] == [1] and plan.inserts == []


def test_two_lost_rows_by_one_runner_that_both_read_alike_are_paired_with_nothing():
    stored = [kept(1, "a", at=0, order=1), kept(2, "b", at=60, order=2)]
    read = [fresh("a2", at=0, order=1), fresh("b2", at=60, order=2)]
    plan = mt.diff(stored, read, move_minutes=5)
    assert plan.renamed == [] and [one["id"] for one in plan.dropped] == [1, 2]


def test_a_lone_lost_row_needs_no_words_alike_so_a_new_game_in_its_slot_is_a_rename():
    stored = [worded(kept(1, "a", at=0, order=1, game="Celeste"), "Any%")]
    read = [worded(fresh("b", at=0, order=1, game="Hollow Knight"), "112%")]
    assert pairs(mt.diff(stored, read, move_minutes=5).renamed) == [(1, "b")]


def test_the_hash_moves_with_the_schedule_and_not_otherwise():
    first = mt.schedule_hash([run(1, at=0)])
    assert first == mt.schedule_hash([run(1, at=0)])
    assert first != mt.schedule_hash([run(1, at=10)])


def test_span_is_the_first_start_and_the_last_end():
    assert mt.span([run(2, at=60), run(1, at=0)]) == (iso(0), iso(120))
    assert mt.span([]) == (None, None)


# --- phase and cadence ------------------------------------------------------------------------


def marathon(**extra):
    return {"id": 1, "active": 1, "starts_at": iso(0), "ends_at": iso(600), **extra}


@pytest.mark.parametrize(
    ("moment", "wanted"),
    [
        (timedelta(days=-8), mt.FAR),
        (timedelta(days=-6), mt.NEAR),
        (timedelta(minutes=30), mt.ON),
        (timedelta(minutes=700), mt.OVER),
    ],
)
def test_the_phase_follows_the_clock(moment, wanted):
    assert mt.phase(marathon(), NOW + moment, lead_days=7) == wanted


def test_a_paused_marathon_is_paused_and_never_due():
    row_ = marathon(active=0)
    assert mt.phase(row_, NOW, lead_days=7) == mt.PAUSED
    assert not mt.fetch_due(row_, NOW, poll_minutes=30, far_hours=24, lead_days=7)


def test_a_fresh_marathon_is_read_at_once():
    assert mt.fetch_due(marathon(), NOW, poll_minutes=30, far_hours=24, lead_days=7)


def test_near_ones_read_every_poll_gap_and_far_ones_every_far_gap():
    near = marathon(last_fetched_at=(NOW - timedelta(minutes=31)).isoformat())
    assert mt.fetch_due(near, NOW, poll_minutes=30, far_hours=24, lead_days=7)
    fresh = marathon(last_fetched_at=(NOW - timedelta(minutes=29)).isoformat())
    assert not mt.fetch_due(fresh, NOW, poll_minutes=30, far_hours=24, lead_days=7)
    own = marathon(poll_minutes=10, last_fetched_at=(NOW - timedelta(minutes=11)).isoformat())
    assert mt.fetch_due(own, NOW, poll_minutes=30, far_hours=24, lead_days=7)
    far = marathon(
        starts_at=(NOW + timedelta(days=30)).isoformat(),
        ends_at=(NOW + timedelta(days=37)).isoformat(),
        last_fetched_at=(NOW - timedelta(hours=2)).isoformat(),
    )
    assert not mt.fetch_due(far, NOW, poll_minutes=30, far_hours=24, lead_days=7)


def test_the_next_read_is_the_last_read_plus_the_gap_fetch_due_uses():
    gaps = {"poll_minutes": 30, "far_hours": 24, "lead_days": 7}
    last = NOW - timedelta(minutes=20)
    near = marathon(last_fetched_at=last.isoformat())
    assert mt.next_read_at(near, NOW, **gaps) == last + timedelta(minutes=30)
    own = marathon(poll_minutes=10, last_fetched_at=last.isoformat())
    assert mt.next_read_at(own, NOW, **gaps) == last + timedelta(minutes=10)
    far = marathon(
        starts_at=(NOW + timedelta(days=30)).isoformat(),
        ends_at=(NOW + timedelta(days=37)).isoformat(),
        last_fetched_at=last.isoformat(),
    )
    assert mt.next_read_at(far, NOW, **gaps) == last + timedelta(hours=24)
    assert mt.next_read_at(marathon(), NOW, **gaps) == NOW
    assert mt.next_read_at(marathon(active=0), NOW, **gaps) is None


def test_a_day_after_the_end_the_marathon_is_far_again_and_its_board_comes_down():
    later = NOW + timedelta(minutes=600) + timedelta(days=1, minutes=1)
    assert not mt.is_near(marathon(), later, lead_days=7)
    assert mt.board_due_off(marathon(), later)
    assert not mt.board_due_off(marathon(), NOW)


def test_the_window_is_the_marathon_padded_by_the_slack():
    assert mt.window_bounds(marathon(), 2) == (iso(-120), iso(720))
    assert mt.window_bounds({"starts_at": None}, 2) is None


# --- the live title ---------------------------------------------------------------------------


def test_the_title_naming_a_game_finds_that_run():
    rows = [row(1, at=0, game="Super Mario 64"), row(2, at=60, game="Celeste")]
    title = "AGDQ 2027 benefiting PCF - Celeste - Any% by @someone"
    assert mt.title_hit(title, "Celeste", rows, NOW + timedelta(minutes=55))["id"] == 2


def test_a_runners_name_breaks_a_tie_between_two_runs_of_one_game():
    rows = [
        row(1, at=0, game="Celeste", people=[{"name": "Alpha", "part": "runner"}]),
        row(2, at=60, game="Celeste", people=[{"name": "Beta", "part": "runner"}]),
    ]
    found = mt.title_hit("Celeste Any% ft. Beta", "", rows, NOW)
    assert found["id"] == 2


def test_the_nearest_scheduled_run_wins_when_nothing_else_does():
    rows = [row(1, at=-300, game="Celeste"), row(2, at=30, game="Celeste")]
    assert mt.title_hit("Celeste", "", rows, NOW)["id"] == 2


def test_the_stream_category_matches_the_runs_twitch_game():
    rows = [row(1, at=0, game="Devil May Cry 5: Special Edition", twitch_game="Devil May Cry 5")]
    assert mt.title_hit("AGDQ 2027 Day 2 !schedule", "Devil May Cry 5", rows, NOW)["id"] == 1


def test_a_title_that_names_nothing_on_the_schedule_is_no_hit():
    rows = [row(1, at=0, game="Celeste")]
    assert mt.title_hit("[Rerun] Flame Fatales 2026 - Day 5 !schedule", "", rows, NOW) is None
    assert mt.title_hit("Celeste", "", rows, NOW + timedelta(hours=13)) is None


def test_a_short_game_name_never_matches_inside_a_word():
    rows = [row(1, at=0, game="Go")]
    assert mt.title_hit("Going fast", "", rows, NOW) is None


# --- states -----------------------------------------------------------------------------------


def moves(changes):
    return [(one.row["id"], one.to, one.because, one.skipped) for one in changes]


def test_a_title_hit_goes_live_and_every_earlier_upcoming_run_is_done_without_a_shout():
    rows = [row(1, at=-120), row(2, at=-60, state=mt.LIVE), row(3, at=0), row(4, at=60)]
    changes = mt.advance(rows, NOW, hit=rows[2], watching=True, grace_minutes=90)
    assert moves(changes) == [
        (3, mt.LIVE, mt.BY_TITLE, False),
        (1, mt.DONE, mt.BY_TITLE, True),
        (2, mt.DONE, mt.BY_TITLE, False),
    ]


def test_with_the_title_watched_a_late_run_waits_out_the_grace():
    rows = [row(1, at=-30, length=300)]
    assert mt.advance(rows, NOW, watching=True, grace_minutes=90) == []
    later = mt.advance(rows, NOW + timedelta(minutes=61), watching=True, grace_minutes=90)
    assert moves(later) == [(1, mt.LIVE, mt.BY_SCHEDULE, False)]


def test_without_a_title_the_schedule_alone_decides_at_the_start():
    rows = [row(1, at=-60, state=mt.LIVE), row(2, at=0), row(3, at=60)]
    assert moves(mt.advance(rows, NOW, watching=False, grace_minutes=90)) == [
        (2, mt.LIVE, mt.BY_SCHEDULE, False),
        (1, mt.DONE, mt.BY_SCHEDULE, False),
    ]


def test_a_run_whose_whole_slot_went_by_is_aged_out_not_shouted():
    rows = [row(1, at=-400, length=60)]
    assert moves(mt.advance(rows, NOW, watching=False, grace_minutes=90)) == [
        (1, mt.DONE, mt.BY_SCHEDULE, True)
    ]


def test_a_live_run_ends_at_its_end_plus_the_grace_when_nothing_else_moves_it():
    rows = [row(1, at=-200, length=60, state=mt.LIVE)]
    assert moves(mt.advance(rows, NOW, watching=True, grace_minutes=90)) == [
        (1, mt.DONE, mt.BY_SCHEDULE, False)
    ]
    assert mt.advance(rows, NOW - timedelta(minutes=60), watching=True, grace_minutes=90) == []


def test_a_dropped_run_never_moves():
    assert (
        mt.advance([row(1, at=-30, state=mt.DROPPED)], NOW, watching=False, grace_minutes=0) == []
    )


# --- reminders --------------------------------------------------------------------------------


def test_the_ping_mark_is_always_one_of_the_marks():
    assert mt.reminder_marks("120, 15", 15) == (120, 15)
    assert mt.reminder_marks("120", 15) == (120, 15)
    assert mt.reminder_marks("garbage", 10) == (10,)


def test_each_mark_fires_once_at_its_moment_and_not_before():
    upcoming = row(1, at=120)
    assert mt.due_marks(upcoming, (120, 15), NOW - timedelta(minutes=1), stale_minutes=30) == (
        None,
        [],
    )
    assert mt.due_marks(upcoming, (120, 15), NOW, stale_minutes=30) == (120, [])
    sent = row(1, at=120, sent=[120])
    assert mt.due_marks(sent, (120, 15), NOW, stale_minutes=30) == (None, [])


def test_a_stale_mark_is_skipped_never_posted_late():
    late = row(1, at=10)
    assert mt.due_marks(late, (120, 15), NOW, stale_minutes=30) == (15, [120])


def test_the_latest_of_two_marks_due_together_is_the_one_posted():
    both = row(1, at=10)
    assert mt.due_marks(both, (120, 15), NOW, stale_minutes=200) == (15, [120])


def test_a_run_that_is_not_upcoming_gets_no_reminder():
    assert mt.due_marks(row(1, at=10, state=mt.LIVE), (15,), NOW, stale_minutes=30) == (None, [])


def test_a_run_moved_later_re_arms_the_marks_now_in_the_future():
    assert mt.rearmed([120, 15], iso(200), NOW) == []
    assert mt.rearmed([120, 15], iso(60), NOW) == [120]


def test_the_marks_setting_refuses_anything_but_one_to_six_minutes():
    assert coerce_value("marathon_reminder_minutes", "15, 120, 15") == "120, 15"
    for bad in ("", "0", "1441", "a, b", "1,2,3,4,5,6,7", "15;30"):
        with pytest.raises(SettingError):
            coerce_value("marathon_reminder_minutes", bad)


# --- words ------------------------------------------------------------------------------------

WORDS = {key: default for key, (default, _, _) in MARATHON_WORDS.items()}
M = {"name": "AGDQ 2027", "starts_at": iso(0), "ends_at": iso(600)}


def test_every_post_fills_every_placeholder_it_takes():
    one = row(1, at=15, game="Celeste", people=OURS)
    fields = mt.run_fields(one, M, WORDS, url="https://twitch.tv/gamesdonequick")
    for key in (
        MARATHON_REMINDER_TEMPLATE_KEY,
        MARATHON_LIVE_TEMPLATE_KEY,
        MARATHON_DONE_TEMPLATE_KEY,
    ):
        said = mt.render(WORDS[key], WORDS[key], **fields)
        assert said.fell_back is False
        assert "<@9>" in said.text and "Celeste" in said.text and "{" not in said.text
    assert fields["part"] == "runs"
    assert fields["in"] == f"<t:{int((NOW + timedelta(minutes=15)).timestamp())}:R>"


def test_a_race_with_two_baf_runners_names_both_in_one_post():
    """B2 of the marathon-people design: a race shouts once, {member} joins every BaF name."""
    race = [
        {"name": "Casey", "login": "caseyfast", "part": "runner", "user_id": 7},
        {"name": "TheKing", "login": "thekingspride", "part": "runner", "user_id": None},
        {"name": "Peas", "login": "peasplays", "part": "runner", "user_id": 8},
    ]
    one = row(1, at=15, game="Super Mario 64", people=race)
    fields = mt.run_fields(one, M, WORDS, url="")
    assert fields["member"] == "<@7>, <@8>"
    said = mt.render(WORDS[MARATHON_LIVE_TEMPLATE_KEY], "", **fields).text
    assert said.count("<@") == 2 and mt.member_ids(one) == [7, 8]


def test_a_template_that_will_not_fill_falls_back_to_the_shipped_words():
    said = mt.render("{nope} {game}", "{game}!", game="Celeste")
    assert said == mt.Rendered("Celeste!", True)


def test_the_board_lists_only_runs_of_ours_in_schedule_order():
    rows = [
        row(2, at=60, game="Second", people=OURS),
        row(1, at=0, game="First", people=OURS),
        row(3, at=30, game="Nobody's", people=[{"name": "x", "user_id": None}]),
    ]
    said = mt.board_text(
        M,
        rows,
        WORDS,
        head=WORDS[MARATHON_BOARD_TEMPLATE_KEY],
        head_default=WORDS[MARATHON_BOARD_TEMPLATE_KEY],
        line=WORDS[MARATHON_BOARD_LINE_KEY],
        line_default=WORDS[MARATHON_BOARD_LINE_KEY],
        empty="nobody",
        url="",
    )
    lines = said.text.splitlines()
    assert "(2)" in lines[0] and "AGDQ 2027" in lines[0]
    assert "First" in lines[1] and "Second" in lines[2] and len(lines) == 3
    assert "coming up" in lines[1]


def test_with_runner_posts_the_board_is_its_head_alone_and_still_says_when_nobody_is_found():
    rows = [row(1, at=0, game="First", people=OURS), row(2, at=60, game="Second", people=OURS)]
    kwargs = dict(
        head=WORDS[MARATHON_BOARD_TEMPLATE_KEY],
        head_default=WORDS[MARATHON_BOARD_TEMPLATE_KEY],
        line=WORDS[MARATHON_BOARD_LINE_KEY],
        line_default=WORDS[MARATHON_BOARD_LINE_KEY],
        empty="nobody yet",
        url="",
        lines=False,
    )
    said = mt.board_text(M, rows, WORDS, **kwargs).text
    assert "(2)" in said and len(said.splitlines()) == 1 and "First" not in said
    assert mt.board_text(M, [], WORDS, **kwargs).text.splitlines()[1] == "nobody yet"


def test_an_empty_board_says_so_and_a_long_one_stays_inside_one_message():
    empty = mt.board_text(
        M,
        [],
        WORDS,
        head="h",
        head_default="h",
        line="l",
        line_default="l",
        empty="nobody yet",
        url="",
    )
    assert empty.text == "h\nnobody yet"
    many = [row(i, at=i, game="G" * 80, people=OURS) for i in range(1, 60)]
    long = mt.board_text(
        M,
        many,
        WORDS,
        head="h",
        head_default="h",
        line=WORDS[MARATHON_BOARD_LINE_KEY],
        line_default=WORDS[MARATHON_BOARD_LINE_KEY],
        empty="",
        url="",
    )
    assert len(long.text) <= mt.MESSAGE_LIMIT


def test_the_url_is_the_channel_then_the_runners_own_twitch():
    one = row(1, at=0, people=OURS)
    assert mt.run_url(one, "gamesdonequick") == "https://twitch.tv/gamesdonequick"
    assert mt.run_url(one, None) == "https://twitch.tv/sky"
    assert mt.run_url(row(2, at=0), None, "fallback") == "fallback"


def test_ours_next_is_the_next_five_runs_of_ours_still_to_come():
    rows = [row(i, at=i * 60, people=OURS) for i in range(8)]
    rows.append(row(99, at=-500, people=OURS))
    assert [one["id"] for one in mt.next_runs(rows, NOW)] == [0, 1, 2, 3, 4]


def test_a_template_with_a_stranger_placeholder_is_refused_in_words():
    with pytest.raises(SettingError, match="nope"):
        coerce_value("marathon_live_template", "{member} {nope}")
    assert (
        coerce_value("marathon_live_template", "{member} is on {game}") == "{member} is on {game}"
    )


def test_the_shipped_words_are_the_registrys_defaults():
    assert MARATHON_DEFAULTS["marathon_mode"] == "shadow"
    assert MARATHON_DEFAULTS["marathon_ping_minutes"] == 15
    assert MARATHON_DEFAULTS["marathon_live_pings"] is False


def test_the_card_is_people_the_tracking_move_and_read_it_now_while_active():
    track = (mt.MarathonMove("track", "Track", "primary", 2),)
    assert mt.card_moves({"active": 1}, track) == (mt.PEOPLE_MOVE, *track, mt.READ_MOVE)
    assert mt.card_moves({"active": 0}) == (mt.PEOPLE_MOVE,)
    assert not hasattr(mt, "REMOVE_MOVE")
    assert mt.ADD_MOVE not in mt.root_moves(staff=False)


# --- staff holds (marathon-next-event §G) ---------------------------------------------------


def test_a_run_staff_marked_live_is_never_closed_by_a_title_hit_on_another_run():
    rows = [row(1, at=-60, state=mt.LIVE, live_because=mt.BY_STAFF), row(2, at=0)]
    changes = mt.advance(rows, NOW, hit=rows[1], watching=True, grace_minutes=90)
    assert moves(changes) == [(2, mt.LIVE, mt.BY_TITLE, False)]


def test_a_run_staff_marked_upcoming_is_not_skipped_by_a_later_hit_or_a_later_start():
    held = row(1, at=-30, length=120, live_because=mt.BY_STAFF)
    rows = [held, row(2, at=-5)]
    assert moves(mt.advance(rows, NOW, hit=rows[1], watching=True, grace_minutes=90)) == [
        (2, mt.LIVE, mt.BY_TITLE, False)
    ]
    assert (1, mt.DONE, mt.BY_SCHEDULE, True) not in moves(
        mt.advance(rows, NOW, watching=False, grace_minutes=90)
    )


def test_a_held_run_still_ends_on_the_clock():
    rows = [row(1, at=-300, length=60, state=mt.LIVE, live_because=mt.BY_STAFF)]
    assert moves(mt.advance(rows, NOW, watching=True, grace_minutes=90)) == [
        (1, mt.DONE, mt.BY_SCHEDULE, False)
    ]


def test_the_run_moves_are_only_the_ones_that_change_something():
    ours = row(1, at=30, people=OURS)
    assert mt.run_moves(ours)[:3] == (mt.SHOUT_MOVE, mt.MARK_LIVE_MOVE, mt.MARK_DONE_MOVE)
    done = row(2, at=-300, state=mt.DONE)
    assert mt.run_moves(done) == (mt.MARK_LIVE_MOVE, mt.MARK_UPCOMING_MOVE, mt.BACK_MOVE)
    live = row(3, at=-10, state=mt.LIVE, shout_message_id=5, people=OURS)
    assert mt.run_moves(live) == (mt.MARK_DONE_MOVE, mt.BACK_MOVE)
    assert mt.run_moves(row(4, at=0, state=mt.DROPPED)) == (mt.BACK_MOVE,)


# --- the next GDQ event ---------------------------------------------------------------------

EVENT = {
    "id": 75,
    "short": "SGDQ2027",
    "name": "Summer Games  Done Quick 2027",
    "datetime": "2027-06-27T12:30:00-04:00",
}


def over(**extra):
    return marathon(**{"source": "gdq", "starts_at": iso(-900), "ends_at": iso(-60), **extra})


def test_a_suggestion_is_wanted_once_for_an_over_gdq_marathon_with_no_record():
    assert mt.wants_suggestion(over(), NOW)
    assert not mt.wants_suggestion(over(suggested_next=json.dumps(mt.none_record(NOW))), NOW)
    assert not mt.wants_suggestion(over(source="horaro"), NOW)
    assert not mt.wants_suggestion(over(active=0), NOW)
    assert not mt.wants_suggestion(marathon(source="gdq"), NOW)
    assert not mt.wants_suggestion(marathon(source="gdq", starts_at=None, ends_at=None), NOW)


def test_a_record_reads_open_then_dismissed_or_added_and_a_none_record_is_none():
    record = mt.suggestion_record(EVENT, NOW)
    assert record["name"] == "Summer Games Done Quick 2027"
    assert record["url"] == "https://tracker.gamesdonequick.com/tracker/event/75"
    assert record["datetime"] == "2027-06-27T16:30:00+00:00"
    assert mt.next_state(record) == mt.NEXT_OPEN
    assert mt.next_state(record | {"dismissed_at": iso(0)}) == mt.NEXT_DISMISSED
    assert mt.next_state(record | {"added_marathon_id": 4}) == mt.NEXT_ADDED
    assert mt.next_state(mt.none_record(NOW)) == mt.NEXT_NONE
    assert mt.next_state(None) is None
    assert mt.suggestion_of({"suggested_next": json.dumps(record)}) == record
    assert mt.suggestion_of({"suggested_next": "not json"}) is None


def test_every_next_word_fills_and_the_date_is_a_discord_stamp():
    record = mt.suggestion_record(EVENT, NOW)
    fields = mt.next_fields(M, record)
    for key in ("marathon_next_template", "marathon_next_added_template"):
        said = mt.render(WORDS[key], WORDS[key], **fields)
        assert said.fell_back is False and "{" not in said.text
    assert (
        "**Summer Games Done Quick 2027**"
        in mt.render(WORDS["marathon_next_template"], "", **fields).text
    )
    assert fields["when"].endswith(":D>") and fields["relative"].endswith(":R>")
    assert mt.render(WORDS["marathon_next_none_template"], "", **fields).text.startswith(
        "AGDQ 2027 is over"
    )


def test_the_next_moves_offer_add_and_dismiss_only_while_the_suggestion_is_open():
    record = mt.suggestion_record(EVENT, NOW)
    assert mt.next_moves(record, over=True) == (
        mt.ADD_NEXT_MOVE,
        mt.DISMISS_NEXT_MOVE,
        mt.LOOK_AGAIN_MOVE,
        mt.BACK_MOVE,
    )
    dismissed = record | {"dismissed_at": iso(0)}
    assert mt.next_moves(dismissed, over=True) == (mt.LOOK_AGAIN_MOVE, mt.BACK_MOVE)
    assert mt.next_moves(None, over=False) == (mt.BACK_MOVE,)


def test_a_login_lent_by_the_viewer_never_costs_a_name_match_and_a_staff_login_beats_it():
    host = {"name": "anarchy", "login": "anarchyasf", "part": "host", "login_from": "viewer"}
    by_name = mt.match_people([host], {}, [], usernames={"anarchy": 7})
    assert by_name == [host | {"user_id": 7}]
    never = mt.match_people([host], {"anarchyasf": 9}, [], usernames={"anarchy": 7})
    assert never[0]["user_id"] == 7
    assert mt.match_people([host], {"anarchyasf": 9}, [])[0]["user_id"] is None
    given = {"name": "anarchy", "login": "anarchyasf", "part": "host"}
    assert mt.match_people([given], {}, [], usernames={"anarchy": 7})[0]["user_id"] is None
    pairing = {"runner_name": "anarchy", "marathon_id": None, "user_id": 5, "twitch_login": "own"}
    fixed = mt.match_people([host], {"anarchyasf": 9}, [pairing], usernames={"anarchy": 7})
    assert fixed == [
        {
            "name": "anarchy",
            "login": "own",
            "part": "host",
            "user_id": 5,
            "sheet_login": "anarchyasf",
            "login_from": "viewer",
        }
    ]
