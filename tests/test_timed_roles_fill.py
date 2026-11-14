from black_bloc import timed_roles_fill as fill


def entry(name, parts, user_id=None):
    return {"name": name, "parts": list(parts), "user_id": user_id}


def test_each_part_lists_its_matched_members_the_missing_ones_and_the_unmatched_names():
    entries = [
        entry("Ada", ["runner"], 900),
        entry("Bo", ["runner", "commentator"], 901),
        entry("Stranger", ["runner"]),
        entry("Gone", ["runner"], 999),
        entry("Hosty", ["host"], 902),
    ]
    roles = {"runner": 10, "commentator": 11, "host": None}

    lines = fill.plan_fill(entries, roles, [10, 11], [900, 901, 902], {(900, 10)})

    runner, couch, host = lines
    assert (runner.matched, runner.missing, runner.unmatched) == (
        [900, 901],
        [901],
        ["Gone", "Stranger"],
    )
    assert (couch.role_id, couch.missing) == (11, [901])
    assert (host.role_id, host.timed, host.missing, host.matched) == (None, False, [], [902])
    assert fill.missing_count(lines) == 2


def test_a_part_whose_role_is_not_on_the_timed_list_gives_nothing():
    [runner, *_] = fill.plan_fill([entry("Ada", ["runner"], 900)], {"runner": 10}, [], [900], ())

    assert runner.timed is False and runner.matched == [900] and runner.missing == []
