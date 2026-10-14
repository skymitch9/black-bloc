import json
from datetime import UTC, datetime, timedelta

from black_bloc import marathon_untracked_alert as ua

NOW = datetime(2027, 1, 4, 18, 0, tzinfo=UTC)


def hours(n):
    return (NOW + timedelta(hours=n)).isoformat()


def run(*people, state="upcoming", at=None):
    return {"state": state, "scheduled_at": at, "people": json.dumps(list(people))}


def person(user_id, part="runner", **extra):
    return {"name": f"p{user_id}", "part": part, "user_id": user_id} | extra


def marathon(**over):
    return {
        "id": 1,
        "name": "AGDQ 2027",
        "active": 1,
        "starts_at": hours(30),
        "tracked_at": None,
        "ignored_at": None,
        "untracked_alert_at": None,
    } | over


RUNS = [run(person(5)), run(person(5), person(6, "host"))]


def test_baf_counts_members_and_hosts_once_each_and_leaves_out_dropped_runs():
    runs = [
        run(person(5), person(6, "host", counts=False)),
        run(person(5), person(7, "commentator", counts=False), {"name": "x", "part": "runner"}),
        run(person(8), state="dropped"),
    ]
    assert ua.baf_of(runs) == ({5}, {6})


def test_the_start_is_the_marathons_else_its_first_live_run():
    assert ua.start_of(marathon(), []) == NOW + timedelta(hours=30)
    runs = [run(at=hours(9)), run(at=hours(4)), run(at=hours(1), state="dropped")]
    assert ua.start_of(marathon(starts_at=None), runs) == NOW + timedelta(hours=4)
    assert ua.start_of(marathon(starts_at=None), [run()]) is None


def test_wanted_only_inside_the_window_and_before_the_start():
    assert ua.wanted(marathon(), RUNS, NOW, 36) is True
    assert ua.wanted(marathon(starts_at=hours(36)), RUNS, NOW, 36) is True
    assert ua.wanted(marathon(starts_at=hours(36.1)), RUNS, NOW, 36) is False
    assert ua.wanted(marathon(starts_at=hours(0)), RUNS, NOW, 36) is False
    assert ua.wanted(marathon(starts_at=hours(-1)), RUNS, NOW, 36) is False
    assert ua.wanted(marathon(starts_at=None), RUNS, NOW, 36) is False


def test_wanted_never_for_off_stamped_tracked_ignored_paused_or_no_baf():
    assert ua.wanted(marathon(), RUNS, NOW, 0) is False
    assert ua.wanted(marathon(untracked_alert_at=hours(-1)), RUNS, NOW, 36) is False
    assert ua.wanted(marathon(tracked_at=hours(-1)), RUNS, NOW, 36) is False
    assert ua.wanted(marathon(ignored_at=hours(-1)), RUNS, NOW, 36) is False
    assert ua.wanted(marathon(active=0), RUNS, NOW, 36) is False
    assert ua.wanted(marathon(), [run({"name": "x", "part": "runner"})], NOW, 36) is False
    assert ua.wanted(None, RUNS, NOW, 36) is False


def test_the_fields_and_details():
    fields = ua.fields_of(marathon(), RUNS, NOW, "<@&9>", "a, b")
    at = int((NOW + timedelta(hours=30)).timestamp())
    assert fields == {
        "role": "<@&9>",
        "name": "AGDQ 2027",
        "when": f"<t:{at}:f>",
        "relative": f"<t:{at}:R>",
        "hours": 30.0,
        "baf": 2,
        "runners": 1,
        "hosts": 1,
        "who": "a, b",
    }
    assert ua.who_of(RUNS, "{} running".format, "{} hosting".format) == ", ".join(
        f"<@{uid}> {'hosting' if part == 'host' else 'running'}" for uid, part in ua.parts_of(RUNS)
    )
    assert len(ua.parts_of(RUNS + RUNS)) == len(ua.parts_of(RUNS)) == 2
    assert ua.details_of(marathon(), RUNS, NOW) == {
        "marathon_id": 1,
        "name": "AGDQ 2027",
        "starts_at": hours(30),
        "hours_left": 30.0,
        "baf_runners": 1,
        "baf_hosts": 1,
    }
