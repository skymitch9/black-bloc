import json

import pytest

from black_bloc import marathon as mt
from black_bloc import marathon_hosts as mh
from black_bloc.marathon_sources import Person, Run

START = "2026-10-02T23:00:00+00:00"


def a_row(ident, starts, ends, people, state=mt.UPCOMING):
    return {
        "id": ident,
        "game": f"Game {ident}",
        "scheduled_at": starts,
        "ends_at": ends,
        "state": state,
        "order_no": ident,
        "people": json.dumps(people),
    }


def test_a_switch_is_on_off_or_follows_the_setting():
    assert mh.clean_switch(True) == (True, True)
    assert mh.clean_switch("off") == (True, False)
    assert mh.clean_switch(None) == (True, None)
    assert mh.clean_switch("follow") == (True, None)
    assert mh.clean_switch("maybe")[0] is False
    assert mh.clean_switch(2)[0] is False
    assert mh.scans_hosts({"scan_hosts": None}, True) is True
    assert mh.scans_hosts({"scan_hosts": 0}, True) is False
    assert mh.makes_host_events({"host_events": 1}, False) is True
    assert mh.makes_host_events({}, False) is False


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("junior_sm", (True, "junior_sm")),
        ("https://www.twitch.tv/Junior_SM", (True, "junior_sm")),
        ("", (True, None)),
        ("  ", (True, None)),
        ("not a name!", (False, None)),
    ],
)
def test_a_twitch_fix_is_a_login_a_link_or_a_blank(given, expected):
    assert mh.clean_login(given) == expected


def test_each_baf_host_has_one_span_over_the_runs_they_host():
    host = {"name": "anarchy", "login": "anarchyasf", "part": "host", "user_id": 8}
    runner = {"name": "Sky", "login": "skyruns", "part": "runner", "user_id": 9}
    rows = [
        a_row(2, "2026-10-03T00:00:00+00:00", "2026-10-03T00:30:00+00:00", [host]),
        a_row(1, START, "2026-10-02T23:40:00+00:00", [runner, host]),
        a_row(3, "2026-10-03T01:00:00+00:00", "2026-10-03T01:30:00+00:00", [host]),
        a_row(4, "2026-10-03T02:00:00+00:00", "2026-10-03T03:00:00+00:00", [host], mt.DROPPED),
    ]
    (span,) = mh.hosted(rows)
    assert span.user_id == 8 and span.name == "anarchy"
    assert [row["id"] for row in span.runs] == [1, 2, 3]
    assert span.starts.isoformat() == START
    assert span.ends.isoformat() == "2026-10-03T01:30:00+00:00"
    fields = mh.event_fields(span, {"name": "Hidden Heroes"})
    assert fields == {
        "member": "anarchy",
        "marathon": "Hidden Heroes",
        "games": "Game 1, Game 2, Game 3",
        "runs": "3",
    }
    assert mh.is_runner_run(rows[1]) and not mh.is_runner_run(rows[0])


def test_the_host_event_ids_survive_a_round_trip_and_bad_cells_read_empty():
    assert mh.event_ids({"host_event_ids": mh.dump_ids({8: 41, 9: 0})}) == {8: 41, 9: 0}
    for bad in (None, "", "[1]", "{not json", '{"x": "y"}'):
        assert mh.event_ids({"host_event_ids": bad}) == {}


def test_only_a_person_who_hosts_and_never_runs_takes_the_host_note():
    assert mh.host_only(["host"]) and mh.host_only(["host", "commentator"])
    assert not mh.host_only(["runner", "host"]) and not mh.host_only([])


def test_match_people_reads_a_schedule_run_s_people_too():
    run = Run("1", 1, "G", "G", "Any%", START, None, 60, (Person("Jr", "Jr", "runner"),))
    fixed = [{"marathon_id": None, "runner_name": "jr", "user_id": 5, "twitch_login": "junior_sm"}]
    assert mt.match_people(run.people, {}, fixed)[0]["sheet_login"] == "Jr"
