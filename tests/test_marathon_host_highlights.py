import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from black_bloc import marathon as mt
from black_bloc import marathon_host_highlights as mhh
from black_bloc.marathon_sources import parse_gdq

FIXTURE = Path(__file__).parent / "fixtures" / "marathon" / "gdq_sgdq2026_runs.json"
BAF = {"JRisJunior": 11, "TheKingsPride": 12, "Quacksilver": 13}
NOW = datetime(2027, 1, 4, 18, 0, tzinfo=UTC)


def sgdq_rows(baf=BAF):
    rows = []
    for ident, run in enumerate(parse_gdq(json.loads(FIXTURE.read_text("utf-8"))), 1):
        people = [
            {"name": one.name, "login": one.login, "part": one.part}
            | ({"user_id": baf[one.name]} if one.part == mt.HOST and one.name in baf else {})
            for one in run.people
        ]
        rows.append(
            {
                "id": ident,
                "order_no": run.order,
                "game": run.game,
                "scheduled_at": run.starts_at,
                "ends_at": run.ends_at,
                "state": mt.UPCOMING,
                "people": json.dumps(people),
            }
        )
    return rows


def a_row(ident, start, hosts, *, state=mt.UPCOMING, length=60):
    people = [{"name": "Runner", "login": None, "part": mt.RUNNER}] + [
        {"name": name, "login": login, "part": mt.HOST}
        | ({"user_id": user_id} if user_id else {})
        for name, login, user_id in hosts
    ]
    return {
        "id": ident,
        "order_no": ident,
        "game": f"Game {ident}",
        "scheduled_at": (NOW + timedelta(minutes=start)).isoformat(),
        "ends_at": (NOW + timedelta(minutes=start + length)).isoformat(),
        "state": state,
        "people": json.dumps(people),
    }


ANARCHY = ("anarchy", "anarchyasf", 8101)
KNOX = ("knox", None, 8102)
OTHER = ("Someone", None, None)


def test_the_sgdq_tracker_gives_one_item_per_hosted_run():
    found = [(one.run_id, one.user_ids) for one in mhh.hosted(sgdq_rows())]
    assert found == [
        (2, [11]),
        (3, [11]),
        (4, [11]),
        (5, [12]),
        (7, [12]),
        (8, [13]),
        (9, [13]),
        (10, [13]),
    ]


def test_only_baf_hosts_count_and_a_run_without_one_is_skipped():
    found = mhh.hosted(sgdq_rows({"TheKingsPride": 12}))
    assert [one.run_id for one in found] == [5, 7]
    assert found[0].hosts == [
        {"user_id": 12, "name": "TheKingsPride", "login": "thekingspride", "part": mt.HOST}
    ]


def test_two_baf_hosts_on_one_run_are_one_item_naming_both():
    (item,) = mhh.hosted([a_row(1, 0, [ANARCHY, KNOX, OTHER])])
    assert item.user_ids == [8101, 8102] and item.names == "anarchy, knox"


def test_a_dropped_run_is_off_the_schedule():
    rows = [
        a_row(1, 0, [ANARCHY]),
        a_row(2, 60, [ANARCHY], state=mt.DROPPED),
        a_row(3, 120, [ANARCHY]),
    ]
    assert [one.run_id for one in mhh.hosted(rows)] == [1, 3]


def test_each_run_is_upcoming_then_live_then_done():
    row = a_row(1, 0, [ANARCHY])
    assert mhh.state_of(mhh.hosted([row])[0]) == mhh.UPCOMING
    row["state"] = mt.LIVE
    assert mhh.state_of(mhh.hosted([row])[0]) == mhh.LIVE
    row["state"] = mt.DONE
    assert mhh.state_of(mhh.hosted([row])[0]) == mhh.DONE


def test_the_heads_up_is_once_per_run_at_its_moment_and_never_late():
    first, second = mhh.hosted([a_row(1, 30, [ANARCHY]), a_row(2, 90, [ANARCHY])])

    def due(item, now, record=None):
        return mhh.heads_up_due(item, record, now, minutes=15, stale_minutes=30)

    assert due(first, NOW) is None
    assert due(first, NOW + timedelta(minutes=15)) == mhh.SEND
    assert due(first, NOW + timedelta(minutes=15), {"reminded": True}) is None
    assert due(second, NOW + timedelta(minutes=15)) is None
    assert due(second, NOW + timedelta(minutes=75)) == mhh.SEND
    assert due(second, NOW + timedelta(minutes=89)) == mhh.SEND
    assert due(second, NOW + timedelta(minutes=106)) == mhh.SKIP


def test_a_run_that_moved_later_is_due_again_like_a_runners_reminder():
    (item,) = mhh.hosted([a_row(1, 30, [ANARCHY])])
    record = {"reminded": True}
    assert not mhh.rearm(record, item, NOW + timedelta(minutes=16), minutes=15)
    assert mhh.rearm(record, item, NOW, minutes=15)
    assert not mhh.rearm({"reminded": False}, item, NOW, minutes=15)


def test_auto_follows_the_marathons_switch_at_live_once():
    row = a_row(1, 0, [ANARCHY], state=mt.LIVE)
    (item,) = mhh.hosted([row])
    assert mhh.auto_wanted({"public_highlight": 1}, item, None)
    assert not mhh.auto_wanted({"public_highlight": 0}, item, None)
    assert not mhh.auto_wanted({"public_highlight": 1}, item, {"tried": True})
    assert not mhh.auto_wanted({"public_highlight": 1}, item, {"message_id": 5, "removed": True})
    row["state"] = mt.UPCOMING
    assert not mhh.auto_wanted({"public_highlight": 1}, mhh.hosted([row])[0], None)


def test_records_survive_a_round_trip_keyed_by_run():
    (item,) = mhh.hosted([a_row(4, 0, [ANARCHY])])
    record = mhh.new_record(item) | {"message_id": 77, "channel_id": 5, "tried": True}
    found = mhh.records({mhh.COLUMN: mhh.dump([record])})
    assert found == [record] and found[0]["run_id"] == 4
    assert mhh.record_for(found, item) == record
    assert mhh.is_up(record) and not mhh.is_up(record | {"removed": True})
    assert mhh.records({mhh.COLUMN: "not json"}) == []
    assert mhh.records({mhh.COLUMN: json.dumps([{"user_id": 1, "runs": [4]}])}) == []


def test_a_post_left_behind_follows_its_run_with_the_hosts_it_named():
    row = a_row(4, 0, [])
    record = {"run_id": 4, "hosts": [{"user_id": 8101, "name": "anarchy", "login": None}]}
    item = mhh.left_behind(record, [row])
    assert item.run_id == 4 and item.names == "anarchy"
    assert mhh.left_behind(record | {"run_id": 9}, [row]) is None


def test_a_move_word_is_post_or_remove():
    assert mhh.clean_move(" Post ") == mhh.POST and mhh.clean_move("remove") == mhh.REMOVE
    assert mhh.clean_move("maybe") is None
