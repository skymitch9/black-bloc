import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from black_bloc import marathon as mt
from black_bloc import marathon_host_highlights as mhh
from black_bloc import marathon_reminder_posts as mrem
from black_bloc.marathon_sources import parse_gdq

FIXTURE = Path(__file__).parent / "fixtures" / "marathon" / "gdq_sgdq2026_runs.json"
BAF = {"JRisJunior": 11, "TheKingsPride": 12, "Quacksilver": 13}
NOW = datetime(2027, 1, 4, 18, 0, tzinfo=UTC)
MARKS = (1440, 120, 15)


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


def shape(found):
    return [(one.run_ids, one.user_ids) for one in found]


def test_the_sgdq_tracker_gives_one_block_per_host_shift():
    assert shape(mhh.blocks(sgdq_rows())) == [
        ([2, 3, 4], [11]),
        ([5, 7], [12]),
        ([8, 9, 10], [13]),
    ]


def test_the_checkpoint_with_no_host_listed_keeps_thekingspride_in_one_block():
    rows = sgdq_rows({"TheKingsPride": 12})
    (block,) = mhh.blocks(rows)
    assert block.run_ids == [5, 7] and block.start_run_id == 5
    assert rows[5]["game"] == "The Checkpoint"
    assert block.hosts == [
        {"user_id": 12, "name": "TheKingsPride", "login": "thekingspride", "part": mt.HOST}
    ]


def test_a_run_someone_else_hosts_ends_the_block():
    rows = [
        a_row(1, 0, [ANARCHY]),
        a_row(2, 60, []),
        a_row(3, 120, [ANARCHY]),
        a_row(4, 180, [OTHER]),
        a_row(5, 240, [ANARCHY]),
        a_row(6, 300, []),
    ]
    assert shape(mhh.blocks(rows)) == [([1, 3], [8101]), ([5], [8101])]


def test_co_hosts_on_the_same_runs_share_one_block_and_differ_otherwise():
    rows = [a_row(1, 0, [ANARCHY, KNOX, OTHER]), a_row(2, 60, [ANARCHY, KNOX])]
    (block,) = mhh.blocks(rows)
    assert block.user_ids == [8101, 8102] and block.names == "anarchy, knox"
    rows.append(a_row(3, 120, [KNOX]))
    assert shape(mhh.blocks(rows)) == [([1, 2], [8101]), ([1, 2, 3], [8102])]


def test_a_dropped_run_is_off_the_schedule():
    rows = [
        a_row(1, 0, [ANARCHY]),
        a_row(2, 60, [OTHER], state=mt.DROPPED),
        a_row(3, 120, [ANARCHY]),
    ]
    assert shape(mhh.blocks(rows)) == [([1, 3], [8101])]


def test_a_block_is_upcoming_then_live_until_its_last_run_is_done():
    rows = [a_row(1, 0, [ANARCHY]), a_row(2, 60, [ANARCHY])]

    def state():
        return mhh.state_of(mhh.blocks(rows)[0])

    assert state() == mhh.UPCOMING
    rows[0]["state"] = mt.LIVE
    assert state() == mhh.LIVE
    rows[0]["state"] = mt.DONE
    assert state() == mhh.LIVE
    rows[1]["state"] = mt.DONE
    assert state() == mhh.DONE
    view = mhh.view_row(mhh.blocks(rows)[0])
    assert view["state"] == mt.DONE and view["game"] == "Game 1"


def test_every_mark_is_due_once_from_the_blocks_start_and_never_late():
    (block,) = mhh.blocks([a_row(1, 1500, [ANARCHY]), a_row(2, 1585, [ANARCHY])])

    def due(minutes, marks=()):
        return mhh.due(
            block, {"marks": list(marks)}, MARKS, NOW + timedelta(minutes=minutes), stale_minutes=30
        )

    assert due(59) == (None, [])
    assert due(60) == (1440, [])
    assert due(60, [1440]) == (None, [])
    assert due(1380, [1440]) == (120, [])
    assert due(1485, [1440, 120]) == (15, [])
    assert due(1570, [1440, 120, 15]) == (None, [])
    assert due(1400) == (120, [1440])


def test_a_block_that_moved_later_forgets_the_marks_ahead_again():
    (block,) = mhh.blocks([a_row(1, 1500, [ANARCHY])])
    record = {"marks": [1440, 120]}
    assert not mhh.rearmed(record, block, NOW + timedelta(minutes=1400))
    assert mhh.rearmed(record, block, NOW + timedelta(minutes=100)) and record["marks"] == [1440]


def test_auto_follows_the_marathons_switch_once_per_block():
    rows = [a_row(1, 0, [ANARCHY], state=mt.LIVE), a_row(2, 60, [ANARCHY])]
    (block,) = mhh.blocks(rows)
    assert mhh.auto_wanted({"public_highlight": 1}, block, None)
    assert not mhh.auto_wanted({"public_highlight": 0}, block, None)
    assert not mhh.auto_wanted({"public_highlight": 1}, block, {"tried": True})
    assert not mhh.auto_wanted({"public_highlight": 1}, block, {"message_id": 5, "removed": True})
    rows[0]["state"] = mt.UPCOMING
    assert not mhh.auto_wanted({"public_highlight": 1}, mhh.blocks(rows)[0], None)


def test_records_survive_a_round_trip_keyed_by_the_blocks_first_run():
    (block,) = mhh.blocks([a_row(4, 0, [ANARCHY]), a_row(5, 60, [ANARCHY])])
    record = mhh.new_record(block) | {"message_id": 77, "channel_id": 5, "tried": True}
    record["marks"] = [15, 120]
    found = mhh.records({mhh.COLUMN: mhh.dump([record])})
    assert found == [record] and found[0]["start_run_id"] == 4 and found[0]["runs"] == [4, 5]
    assert mhh.claim(found, block, set()) is found[0]
    assert mhh.is_up(record) and not mhh.is_up(record | {"removed": True})
    assert mhh.records({mhh.COLUMN: "not json"}) == []
    assert mhh.records({mhh.COLUMN: json.dumps([{"user_id": 1, "runs": [4]}])}) == []


def test_a_per_run_record_from_the_last_build_reads_as_a_one_run_block():
    old = {
        "run_id": 4,
        "hosts": [{"user_id": 8101, "name": "anarchy", "login": None, "part": "host"}],
        "message_id": 77,
        "channel_id": 5,
        "removed": False,
        "tried": True,
        "reminded": True,
    }
    (found,) = mhh.records({mhh.COLUMN: json.dumps([old])})
    assert found["start_run_id"] == 4 and found["runs"] == [4] and found["marks"] == []
    assert found["legacy_reminded"] is True and mhh.is_up(found)
    (block,) = mhh.blocks([a_row(4, 30, [ANARCHY]), a_row(5, 90, [ANARCHY])])
    assert mhh.claim([found], block, set()) is found
    assert mhh.passed_marks(block, MARKS, NOW + timedelta(minutes=20)) == [15, 120, 1440]


def test_a_block_that_grows_or_moves_keeps_its_record():
    (block,) = mhh.blocks([a_row(4, 0, [ANARCHY]), a_row(5, 60, [ANARCHY])])
    record = mhh.new_record(block)
    (grown,) = mhh.blocks([a_row(3, -60, [ANARCHY]), a_row(4, 0, [ANARCHY])])
    used: set[int] = set()
    assert mhh.claim([record], grown, used) is record
    assert mhh.claim([record], grown, used) is None
    assert mhh.attach(record, grown) and record["start_run_id"] == 3 and record["runs"] == [3, 4]
    assert not mhh.attach(record, grown)


def test_a_post_left_behind_follows_its_runs_with_the_hosts_it_named():
    rows = [a_row(4, 0, []), a_row(5, 60, [])]
    record = {
        "start_run_id": 4,
        "runs": [4, 5],
        "hosts": [{"user_id": 8101, "name": "anarchy", "login": None}],
    }
    block = mhh.left_behind(record, rows)
    assert block.run_ids == [4, 5] and block.names == "anarchy"
    assert mhh.left_behind(record | {"runs": [9]}, rows) is None


def test_edit_keeps_a_blocks_posted_marks_and_fires_only_the_ones_that_never_posted():
    (block,) = mhh.blocks([a_row(1, 1500, [ANARCHY])])
    copy = {"channel_id": 9, "message_id": 5, "text": "x", "head": "", "at": None}
    record = {
        "marks": [1440, 120],
        "reminders": {1440: {"posted": True, "public": copy}, 120: {"posted": False}},
    }

    assert mhh.rearmed(record, block, NOW + timedelta(minutes=100), mrem.EDIT)
    assert record["marks"] == [1440]
    assert record["reminders"] == {1440: {"posted": True, "public": copy}}
    legacy = {"marks": [1440, 120]}
    assert not mhh.rearmed(legacy, block, NOW, mrem.EDIT) and legacy["marks"] == [1440, 120]
    again = {"marks": [1440, 120], "reminders": dict(record["reminders"])}
    assert mhh.rearmed(again, block, NOW, mrem.REPOST)
    assert again["marks"] == [] and again["reminders"] == {}


def test_a_record_carries_its_remembered_heads_ups_through_the_column_and_back():
    (block,) = mhh.blocks([a_row(1, 1500, [ANARCHY])])
    record = mhh.new_record(block)
    assert record["reminders"] == {}
    copy = {"channel_id": 9, "message_id": 5, "text": "x", "head": "<@&1> ", "at": "t"}
    record["reminders"][15] = mrem.entry_of(public=copy)

    (back,) = mhh.records({mhh.COLUMN: mhh.dump([record])})

    assert back["reminders"] == {15: {"posted": True, "public": copy}}
    (old,) = mhh.records({mhh.COLUMN: json.dumps([{"run_id": 1, "hosts": [], "reminded": True}])})
    assert old["reminders"] == {}


def test_a_block_is_dropped_only_when_every_run_of_it_is_off_the_schedule():
    rows = [a_row(1, 1500, [ANARCHY]), a_row(2, 1585, [ANARCHY])]
    block = mhh.Block(rows, [])
    assert not mhh.is_dropped(block)
    rows[0]["state"] = mt.DROPPED
    assert not mhh.is_dropped(block)
    rows[1]["state"] = mt.DROPPED
    assert mhh.is_dropped(block) and mhh.dropped_row(block)["state"] == mt.DROPPED


def test_a_record_remembers_who_its_post_names_and_that_its_skip_was_said():
    block = mhh.blocks(runs_for_named_record())[0]
    record = mhh.new_record(block)
    assert record["named"] is None and record["skipped"] is False
    (back,) = mhh.records({mhh.COLUMN: mhh.dump([record])})
    assert back["named"] is None and back["skipped"] is False

    record |= {"named": [{"user_id": 8101, "name": "anarchy", "plain": True}], "skipped": True}
    (back,) = mhh.records({mhh.COLUMN: mhh.dump([record])})
    assert back["skipped"] is True
    assert [(one["user_id"], one["name"], one["plain"]) for one in back["named"]] == [
        (8101, "anarchy", True)
    ]


def runs_for_named_record():
    host = {"name": "anarchy", "user_id": 8101, "login": "anarchyasf", "part": "host"}
    return [
        {
            "id": 1,
            "state": "upcoming",
            "scheduled_at": "2027-01-04T19:00:00+00:00",
            "people": json.dumps([host]),
        }
    ]
