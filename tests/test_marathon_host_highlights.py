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
OTHER = ("Someone", None, None)


def test_the_sgdq_tracker_gives_one_block_per_host_shift():
    found = {one.name: one for one in mhh.spans(sgdq_rows())}
    assert set(found) == set(BAF)
    assert found["JRisJunior"].run_ids == [2, 3, 4]
    assert found["TheKingsPride"].run_ids == [5, 7]
    assert found["Quacksilver"].run_ids == [8, 9, 10]
    kings = found["TheKingsPride"]
    assert kings.starts.isoformat() == "2026-07-05T21:58:00+00:00"
    assert kings.ends.isoformat() == "2026-07-06T01:00:00+00:00"
    assert kings.login == "thekingspride" and found["JRisJunior"].login is None


def test_only_baf_hosts_get_a_block():
    found = mhh.spans(sgdq_rows({"TheKingsPride": 12}))
    assert [(one.user_id, one.run_ids) for one in found] == [(12, [5, 7])]


def test_a_run_someone_else_hosts_ends_the_block():
    rows = [a_row(1, 0, [ANARCHY]), a_row(2, 60, [OTHER]), a_row(3, 120, [ANARCHY])]
    assert [one.run_ids for one in mhh.spans(rows)] == [[1], [3]]


def test_a_run_with_no_host_keeps_the_block_going_and_a_co_host_does_too():
    rows = [
        a_row(1, 0, [ANARCHY]),
        a_row(2, 60, []),
        a_row(3, 120, [ANARCHY, OTHER]),
        a_row(4, 180, []),
    ]
    (block,) = mhh.spans(rows)
    assert block.run_ids == [1, 3]
    assert block.ends == NOW + timedelta(minutes=180)


def test_a_dropped_run_is_off_the_schedule():
    rows = [
        a_row(1, 0, [ANARCHY]),
        a_row(2, 60, [OTHER], state=mt.DROPPED),
        a_row(3, 120, [ANARCHY]),
    ]
    assert [one.run_ids for one in mhh.spans(rows)] == [[1, 3]]


def test_the_block_is_upcoming_then_on_now_then_done():
    rows = [a_row(1, 0, [ANARCHY]), a_row(2, 60, [ANARCHY])]
    assert mhh.state_of(mhh.spans(rows)[0]) == mhh.UPCOMING
    rows[0]["state"] = mt.LIVE
    assert mhh.state_of(mhh.spans(rows)[0]) == mhh.LIVE
    rows[0]["state"] = mt.DONE
    assert mhh.state_of(mhh.spans(rows)[0]) == mhh.LIVE
    rows[1]["state"] = mt.DONE
    assert mhh.state_of(mhh.spans(rows)[0]) == mhh.DONE


def test_the_heads_up_is_once_before_the_first_run_and_never_late():
    (block,) = mhh.spans([a_row(1, 30, [ANARCHY]), a_row(2, 90, [ANARCHY])])
    due = lambda now, record=None: mhh.heads_up_due(  # noqa: E731
        block, record, now, minutes=15, stale_minutes=30
    )
    assert due(NOW) is None
    assert due(NOW + timedelta(minutes=15)) == mhh.SEND
    assert due(NOW + timedelta(minutes=15), {"reminded": True}) is None
    assert due(NOW + timedelta(minutes=46)) == mhh.SKIP


def test_records_survive_a_round_trip_and_follow_a_block_that_moved():
    (block,) = mhh.spans([a_row(1, 0, [ANARCHY]), a_row(2, 60, [ANARCHY])])
    record = mhh.new_record(block) | {"message_id": 77, "channel_id": 5, "tried": True}
    found = mhh.records({mhh.COLUMN: mhh.dump([record])})
    assert found == [record]
    (grown,) = mhh.spans([a_row(2, 60, [ANARCHY]), a_row(3, 120, [ANARCHY])])
    assert mhh.record_for(found, grown) == record
    assert mhh.is_up(record) and not mhh.is_up(record | {"removed": True})
    assert mhh.records({mhh.COLUMN: "not json"}) == []


def test_the_fields_name_the_host_and_link_their_own_channel_first():
    (block,) = mhh.spans([a_row(1, 0, [ANARCHY])])
    fields = mhh.fields_of(block, {"name": "Hidden Heroes"}, url="https://twitch.tv/hotfix")
    assert fields["name"] == "anarchy" and fields["mention"] == "<@8101>"
    assert fields["show"] == "Hidden Heroes" and fields["link"] == "https://twitch.tv/anarchyasf"
    assert fields["when"].startswith("<t:") and fields["until"].endswith(":t>")
    (plain,) = mhh.spans([a_row(1, 0, [("anarchy", None, 8101)])])
    assert mhh.fields_of(plain, {"name": "x"}, url="https://u")["link"] == "https://u"


def test_a_move_word_is_post_or_remove():
    assert mhh.clean_move(" Post ") == mhh.POST and mhh.clean_move("remove") == mhh.REMOVE
    assert mhh.clean_move("maybe") is None
