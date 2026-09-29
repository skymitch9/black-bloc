import json

import pytest

from black_bloc import marathon as mt
from black_bloc import marathon_host_highlights as mhh
from black_bloc import marathon_hosts as mh
from black_bloc.marathon_sources import Person, Run

START = "2026-10-02T23:00:00+00:00"
HOST = {"name": "anarchy", "login": "anarchyasf", "part": "host", "user_id": 8}
RUNNER = {"name": "Sky", "login": "skyruns", "part": "runner", "user_id": 9}
OTHER_HOST = {"name": "Mo", "login": "mohosts", "part": "host"}


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


def rows():
    return [
        a_row(2, "2026-10-03T00:00:00+00:00", "2026-10-03T00:30:00+00:00", [HOST]),
        a_row(1, START, "2026-10-02T23:40:00+00:00", [RUNNER, HOST]),
        a_row(3, "2026-10-03T01:00:00+00:00", "2026-10-03T01:30:00+00:00", [HOST]),
        a_row(4, "2026-10-03T02:00:00+00:00", "2026-10-03T03:00:00+00:00", [OTHER_HOST]),
        a_row(5, "2026-10-03T03:00:00+00:00", "2026-10-03T03:30:00+00:00", [HOST]),
    ]


def test_a_switch_is_on_off_or_follows_the_setting():
    assert mh.clean_switch(True) == (True, True)
    assert mh.clean_switch("off") == (True, False)
    assert mh.clean_switch(None) == (True, None)
    assert mh.clean_switch("follow") == (True, None)
    assert mh.clean_switch("maybe")[0] is False
    assert mh.clean_switch(2)[0] is False
    assert mh.switch_on({"announcements": None}, "announcements", True) is True
    assert mh.switch_on({"announcements": 0}, "announcements", True) is False


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


def test_a_host_block_has_one_span_and_its_event_words():
    first, second = mhh.blocks(rows())
    assert first.run_ids == [1, 2, 3] and second.run_ids == [5]
    starts, ends = mh.span_of(first)
    assert starts.isoformat() == START
    assert ends.isoformat() == "2026-10-03T01:30:00+00:00"
    assert mh.event_fields(first, {"name": "Hidden Heroes"}) == {
        "member": "anarchy",
        "marathon": "Hidden Heroes",
        "games": "Game 1, Game 2, Game 3",
        "runs": "3",
    }
    assert mh.is_runner_run(rows()[1]) and not mh.is_runner_run(rows()[0])


def test_block_records_round_trip_and_bad_cells_read_empty():
    first, _second = mhh.blocks(rows())
    record = {"event_id": 41, "runs": first.run_ids, "hosts": first.user_ids}
    (read,) = mh.event_records({"host_event_ids": mh.dump_records([record])})
    assert read == {"event_id": 41, "start_run_id": 1, "runs": [1, 2, 3], "hosts": [8]}
    for bad in (None, "", "[1]", "{not json", '{"x": "y"}', "7"):
        assert mh.event_records({"host_event_ids": bad}) == []


def test_a_per_host_record_from_before_blocks_is_claimed_by_that_hosts_first_block():
    first, second = mhh.blocks(rows())
    found = mh.event_records({"host_event_ids": json.dumps({"8": 41})})
    assert found == [{"event_id": 41, "start_run_id": None, "runs": [], "hosts": [8]}]
    used: set[int] = set()
    assert mh.claim(found, first, used) is found[0]
    assert mh.claim(found, second, used) is None
    mh.fit(found[0], first)
    assert found[0]["runs"] == [1, 2, 3] and found[0]["start_run_id"] == 1


def test_a_block_that_grows_or_moves_keeps_its_record():
    first, _second = mhh.blocks(rows())
    moved = [{"event_id": 5, "start_run_id": 9, "runs": [9, 2], "hosts": [8]}]
    assert mh.claim(moved, first, set()) is moved[0]
    stranger = [{"event_id": 5, "start_run_id": 9, "runs": [9], "hosts": [8]}]
    assert mh.claim(stranger, first, set()) is None


def test_only_a_person_who_hosts_and_never_runs_takes_the_host_note():
    assert mh.host_only(["host"]) and mh.host_only(["host", "commentator"])
    assert not mh.host_only(["runner", "host"]) and not mh.host_only([])


def test_the_part_tag_is_the_part_keys_words_joined():
    words = {"marathon_part_runner": "runs", "marathon_part_host": "hosts"}
    assert mh.part_tag(["runner"], words) == "runs"
    assert mh.part_tag(["host"], words) == "hosts"
    assert mh.part_tag(["runner", "host"], words) == "runs + hosts"


def test_match_people_reads_a_schedule_run_s_people_too():
    run = Run("1", 1, "G", "G", "Any%", START, None, 60, (Person("Jr", "Jr", "runner"),))
    fixed = [{"marathon_id": None, "runner_name": "jr", "user_id": 5, "twitch_login": "junior_sm"}]
    assert mt.match_people(run.people, {}, fixed)[0]["sheet_login"] == "Jr"
