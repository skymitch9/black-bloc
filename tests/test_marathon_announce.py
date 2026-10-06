import json
import re
from types import SimpleNamespace

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
    [
        (True, True),
        ("out", True),
        ("optout", True),
        ("remove", True),
        (False, False),
        ("in", False),
        ("optin", False),
        ("post", False),
        ("maybe", None),
        (None, None),
    ],
)
def test_a_move_word_is_out_or_in(given, wanted):
    assert ma.clean_opt(given) is wanted


# --- announce overrides: the decision, one run at a time ----------------------------------------

HOSTING = {"name": "anarchy", "user_id": 8101, "login": "anarchyasf", "part": "host"}
QUIET_HOST = HOSTING | {"counts": False}
LABELS = {
    ma.IN: "Announce {name} for this run",
    ma.OUT: "Do not announce {name} for this run",
    ma.DEFAULT: "{name}: back to the default for this run",
    ma.PLAIN: "No @ for {name}",
    ma.MENTION: "@ {name} again",
}
STATE_WORDS = {
    "line": "{name}: {state} — {why}{plain}",
    "yes": "announced",
    "no": "not announced",
    ma.PLAIN: " · no @",
    ma.WHY_DEFAULT: "the default",
    ma.WHY_RUN: "set for this run",
    ma.WHY_MARATHON: "opted out of the marathon",
    ma.WHY_OFF: "the marathon is off",
    ma.WHY_HOSTS_OFF: "hosts are off",
}

# master, opted out of the marathon, the run's answer, the part, Host announcements -> (yes, why)
TRUTH = [
    (False, False, None, ma.RUNNER, False, (False, ma.WHY_OFF)),
    (False, False, None, ma.RUNNER, True, (False, ma.WHY_OFF)),
    (False, False, ma.IN, ma.RUNNER, False, (False, ma.WHY_OFF)),
    (False, False, ma.IN, ma.RUNNER, True, (False, ma.WHY_OFF)),
    (False, False, ma.OUT, ma.RUNNER, False, (False, ma.WHY_OFF)),
    (False, False, ma.OUT, ma.RUNNER, True, (False, ma.WHY_OFF)),
    (False, True, None, ma.RUNNER, False, (False, ma.WHY_OFF)),
    (False, True, None, ma.RUNNER, True, (False, ma.WHY_OFF)),
    (False, True, ma.IN, ma.RUNNER, False, (False, ma.WHY_OFF)),
    (False, True, ma.IN, ma.RUNNER, True, (False, ma.WHY_OFF)),
    (False, True, ma.OUT, ma.RUNNER, False, (False, ma.WHY_OFF)),
    (False, True, ma.OUT, ma.RUNNER, True, (False, ma.WHY_OFF)),
    (False, False, None, ma.HOST, False, (False, ma.WHY_OFF)),
    (False, False, None, ma.HOST, True, (False, ma.WHY_OFF)),
    (False, False, ma.IN, ma.HOST, False, (False, ma.WHY_OFF)),
    (False, False, ma.IN, ma.HOST, True, (False, ma.WHY_OFF)),
    (False, False, ma.OUT, ma.HOST, False, (False, ma.WHY_OFF)),
    (False, False, ma.OUT, ma.HOST, True, (False, ma.WHY_OFF)),
    (False, True, None, ma.HOST, False, (False, ma.WHY_OFF)),
    (False, True, None, ma.HOST, True, (False, ma.WHY_OFF)),
    (False, True, ma.IN, ma.HOST, False, (False, ma.WHY_OFF)),
    (False, True, ma.IN, ma.HOST, True, (False, ma.WHY_OFF)),
    (False, True, ma.OUT, ma.HOST, False, (False, ma.WHY_OFF)),
    (False, True, ma.OUT, ma.HOST, True, (False, ma.WHY_OFF)),
    (True, False, None, ma.RUNNER, False, (True, ma.WHY_DEFAULT)),
    (True, False, None, ma.RUNNER, True, (True, ma.WHY_DEFAULT)),
    (True, False, ma.IN, ma.RUNNER, False, (True, ma.WHY_RUN)),
    (True, False, ma.IN, ma.RUNNER, True, (True, ma.WHY_RUN)),
    (True, False, ma.OUT, ma.RUNNER, False, (False, ma.WHY_RUN)),
    (True, False, ma.OUT, ma.RUNNER, True, (False, ma.WHY_RUN)),
    (True, True, None, ma.RUNNER, False, (False, ma.WHY_MARATHON)),
    (True, True, None, ma.RUNNER, True, (False, ma.WHY_MARATHON)),
    (True, True, ma.IN, ma.RUNNER, False, (True, ma.WHY_RUN)),
    (True, True, ma.IN, ma.RUNNER, True, (True, ma.WHY_RUN)),
    (True, True, ma.OUT, ma.RUNNER, False, (False, ma.WHY_MARATHON)),
    (True, True, ma.OUT, ma.RUNNER, True, (False, ma.WHY_MARATHON)),
    (True, False, None, ma.HOST, False, (False, ma.WHY_HOSTS_OFF)),
    (True, False, None, ma.HOST, True, (True, ma.WHY_DEFAULT)),
    (True, False, ma.IN, ma.HOST, False, (True, ma.WHY_RUN)),
    (True, False, ma.IN, ma.HOST, True, (True, ma.WHY_RUN)),
    (True, False, ma.OUT, ma.HOST, False, (False, ma.WHY_RUN)),
    (True, False, ma.OUT, ma.HOST, True, (False, ma.WHY_RUN)),
    (True, True, None, ma.HOST, False, (False, ma.WHY_MARATHON)),
    (True, True, None, ma.HOST, True, (False, ma.WHY_MARATHON)),
    (True, True, ma.IN, ma.HOST, False, (True, ma.WHY_RUN)),
    (True, True, ma.IN, ma.HOST, True, (True, ma.WHY_RUN)),
    (True, True, ma.OUT, ma.HOST, False, (False, ma.WHY_MARATHON)),
    (True, True, ma.OUT, ma.HOST, True, (False, ma.WHY_MARATHON)),
]


@pytest.mark.parametrize(("master", "opted", "answer", "role", "hosts_on", "wanted"), TRUTH)
def test_every_row_of_the_truth_table(master, opted, answer, role, hosts_on, wanted):
    said = ma.decide(master=master, opted_out=opted, answer=answer, role=role, hosts_on=hosts_on)
    assert (said.yes, said.why) == wanted


def test_the_truth_table_is_every_combination_once():
    assert len(TRUTH) == 2 * 2 * 3 * 2 * 2 == len({one[:5] for one in TRUTH})


def a_run(ident, people, answers=None, state="upcoming"):
    return {
        "id": ident,
        "state": state,
        "people": json.dumps(people),
        ma.RUN_ANSWERS: ma.dump_answers(answers or {}),
    }


def ids(people):
    return [one["user_id"] for one in people]


def test_a_host_is_not_named_by_default_and_a_runner_is():
    row = a_run(1, [SKY, HOSTING])
    assert ids(ma.run_people(row, ma.Policy())) == [9001]
    assert ids(ma.run_people(row, ma.Policy(hosts_on=True))) == [9001, 8101]
    assert ids(ma.run_people(a_run(1, [SKY, HOSTING], {8101: ma.IN}), ma.Policy())) == [9001, 8101]
    assert ma.run_people(row, ma.Policy(master=False, hosts_on=True)) == []


def test_someone_who_runs_and_hosts_a_run_is_a_runner_for_it():
    both = [SKY, SKY | {"part": "host"}]
    (person,) = ma.baf_on(a_run(1, both))
    assert person["role"] == ma.RUNNER
    assert ids(ma.run_people(a_run(1, both), ma.Policy())) == [9001]


def test_a_host_who_does_not_make_the_run_ours_is_still_someone_the_run_can_announce():
    found = ma.baf_on(a_run(1, [SKY, QUIET_HOST, {"name": "Nobody", "part": "runner"}]))
    assert [(one["user_id"], one["role"]) for one in found] == [
        (9001, ma.RUNNER),
        (8101, ma.HOST),
    ]
    assert ids(ma.run_people(a_run(1, [SKY, QUIET_HOST]), ma.Policy(hosts_on=True))) == [9001]


def a_block(rows):
    return SimpleNamespace(runs=rows, hosts=[dict(HOSTING)])


def test_a_block_is_announced_when_its_host_is_announced_for_any_run_of_it():
    four = [a_run(one, [HOSTING]) for one in (1, 2, 3, 4)]
    assert ma.block_people(a_block(four), ma.Policy()) == []
    assert ids(ma.block_people(a_block(four), ma.Policy(hosts_on=True))) == [8101]
    third = [a_run(one, [HOSTING], {8101: ma.IN} if one == 3 else None) for one in (1, 2, 3, 4)]
    assert ids(ma.block_people(a_block(third), ma.Policy())) == [8101]
    assert ma.block_people(a_block(third), ma.Policy(master=False)) == []
    most = [a_run(one, [HOSTING], {8101: ma.OUT} if one != 2 else None) for one in (1, 2, 3, 4)]
    assert ids(ma.block_people(a_block(most), ma.Policy(hosts_on=True))) == [8101]
    every = [a_run(one, [HOSTING], {8101: ma.OUT}) for one in (1, 2, 3, 4)]
    assert ma.block_people(a_block(every), ma.Policy(hosts_on=True)) == []


def test_a_host_who_also_runs_one_run_of_their_block_does_not_announce_the_block_by_default():
    rows = [a_run(1, [HOSTING]), a_run(2, [HOSTING, HOSTING | {"part": "runner"}])]
    assert ma.block_people(a_block(rows), ma.Policy()) == []
    assert ids(ma.run_people(rows[1], ma.Policy())) == [8101]


def test_a_run_s_own_yes_gets_past_the_marathon_wide_opt_out_and_nothing_gets_past_the_master():
    row = a_run(1, [SKY, RIVET], {9001: ma.IN})
    assert ids(ma.run_people(row, out(9001, 9002))) == [9001]
    assert ma.run_people(row, out(9001, 9002)._replace(master=False)) == []
    assert ids(ma.run_people(row, ma.standing(out(9001, 9002)._replace(master=False)))) == [9001]


def test_the_answers_read_back_and_a_bad_column_reads_as_no_answer():
    assert ma.run_answers({ma.RUN_ANSWERS: '{"9001": "in", "x": "out", "9002": "maybe"}'}) == {
        9001: ma.IN
    }
    assert ma.run_answers({ma.RUN_ANSWERS: "not json"}) == {} == ma.run_answers({})
    assert ma.dump_answers({}) is None
    assert ma.answered({9001: ma.IN}, 9001, None) == {}
    assert ma.answered({}, "9001", ma.OUT) == {9001: ma.OUT}
    assert ma.mentions({ma.MENTIONS: '{"9001": "plain", "9002": "loud"}'}) == {9001: ma.PLAIN}


@pytest.mark.parametrize(
    ("given", "wanted"),
    [
        ("in", (True, ma.IN)),
        (True, (True, ma.IN)),
        ("OUT", (True, ma.OUT)),
        (False, (True, ma.OUT)),
        ("default", (True, None)),
        (None, (True, None)),
        ("follow", (True, None)),
        ("maybe", (False, None)),
    ],
)
def test_a_runs_answer_is_in_out_or_the_default(given, wanted):
    assert ma.clean_run(given) == wanted


def test_how_a_name_is_written_follows_the_server_until_the_person_has_their_own():
    assert ma.clean_mention("plain") == ma.PLAIN and ma.clean_mention("@") == ma.MENTION
    assert ma.clean_mention(False) == ma.PLAIN and ma.clean_mention("maybe") is None
    assert not ma.Policy().plain(9001) and ma.Policy(mention_default=False).plain(9001)
    assert ma.Policy(mentions={9001: ma.PLAIN}).plain(9001)
    assert not ma.Policy(mentions={9001: ma.MENTION}, mention_default=False).plain(9001)
    assert ma.mention_stored(ma.PLAIN, True) == ma.PLAIN
    assert ma.mention_stored(ma.MENTION, True) is None
    assert ma.mention_stored(ma.PLAIN, False) is None
    assert ma.mention_stored(ma.MENTION, False) == ma.MENTION


def moves_of(row, found=None):
    return [
        (one.user_id, one.to, one.label) for one in ma.moves(7, row, found or ma.Policy(), LABELS)
    ]


def test_each_person_gets_the_one_move_their_state_allows_and_the_one_for_their_at():
    row = a_run(3, [SKY, QUIET_HOST])
    assert moves_of(row) == [
        (9001, ma.OUT, "Do not announce Sky for this run"),
        (9001, ma.PLAIN, "No @ for Sky"),
        (8101, ma.IN, "Announce anarchy for this run"),
        (8101, ma.PLAIN, "No @ for anarchy"),
    ]
    answered = a_run(3, [SKY, QUIET_HOST], {9001: ma.OUT, 8101: ma.IN})
    found = ma.Policy(mentions={9001: ma.PLAIN})
    assert moves_of(answered, found) == [
        (9001, ma.DEFAULT, "Sky: back to the default for this run"),
        (9001, ma.MENTION, "@ Sky again"),
        (8101, ma.DEFAULT, "anarchy: back to the default for this run"),
        (8101, ma.PLAIN, "No @ for anarchy"),
    ]
    assert moves_of(row, out(9001))[0] == (9001, ma.IN, "Announce Sky for this run")
    assert moves_of(row, ma.Policy(master=False))[0][1] == ma.OUT
    made = ma.moves(7, row, ma.Policy(), LABELS)
    assert made[0].custom_id == "marathon:announce:7:3:9001:out"
    assert re.fullmatch(ma.MOVE_TEMPLATE, made[0].custom_id)["to"] == "out"
    assert len({one.custom_id for one in made}) == len(made)


def test_a_run_that_is_over_carries_no_moves_and_no_state():
    for state in ("done", "dropped"):
        row = a_run(3, [SKY], state=state)
        assert ma.moves(7, row, ma.Policy(), LABELS) == ()
        assert ma.state_lines(row, ma.Policy(), STATE_WORDS) == []


def crowd(count):
    return [
        {"name": f"Runner {one}", "user_id": 9100 + one, "login": None, "part": "runner"}
        for one in range(count)
    ]


def test_four_people_fit_as_buttons_and_more_become_one_menu():
    four = a_run(3, crowd(4))
    made = ma.laid_out(7, four, ma.moves(7, four, ma.Policy(), LABELS), "Pick…")
    assert len(made) == 8 and all(isinstance(one, ma.Move) for one in made)
    five = a_run(3, crowd(5))
    (pick,) = ma.laid_out(7, five, ma.moves(7, five, ma.Policy(), LABELS), "Pick…")
    assert isinstance(pick, ma.Pick) and pick.custom_id == "marathon:announce:7:3:pick"
    assert re.fullmatch(ma.PICK_TEMPLATE, pick.custom_id) and pick.label == "Pick…"
    assert len(pick.options) == 10
    assert pick.options[0] == ("9100:out", "Do not announce Runner 0 for this run")
    assert ma.option_of(pick.options[1][0]) == (9100, ma.PLAIN)
    assert ma.option_of("x:out") is None and ma.option_of("9100:shout") is None


def test_a_menu_never_carries_more_than_discord_takes_and_a_long_name_is_cut():
    many = a_run(3, crowd(20))
    (pick,) = ma.laid_out(7, many, ma.moves(7, many, ma.Policy(), LABELS), "x" * 300)
    assert len(pick.options) == 25 and len(pick.label) == 100
    long = a_run(3, [SKY | {"name": "S" * 200}])
    (move, _) = ma.moves(7, long, ma.Policy(), LABELS)
    assert len(move.label) == 80


def test_the_state_line_says_who_is_announced_and_why():
    row = a_run(3, [SKY, RIVET, QUIET_HOST], {9002: ma.OUT})
    found = ma.Policy(opted=frozenset({9001}), mentions={9002: ma.PLAIN})
    assert ma.state_lines(row, found, STATE_WORDS) == [
        "Sky: not announced — opted out of the marathon",
        "Rivet: not announced — set for this run · no @",
        "anarchy: not announced — hosts are off",
    ]
    assert ma.state_lines(row, ma.Policy(hosts_on=True), STATE_WORDS, only=8101) == [
        "anarchy: announced — the default"
    ]
    assert ma.state_lines(a_run(3, [SKY]), ma.Policy(master=False), STATE_WORDS) == [
        "Sky: not announced — the marathon is off"
    ]
    assert ma.state_lines(a_run(3, [SKY], {9001: ma.IN}), out(9001), STATE_WORDS) == [
        "Sky: announced — set for this run"
    ]


def test_host_announcements_follow_their_own_setting():
    assert not ma.announces_hosts({ma.HOSTS: None}, False)
    assert ma.announces_hosts({ma.HOSTS: None}, True)
    assert ma.announces_hosts({ma.HOSTS: 1}, False) and not ma.announces_hosts({ma.HOSTS: 0}, True)
    found = ma.policy(
        {ma.HOSTS: 1, ma.OPTED: "[9001]", ma.MENTIONS: '{"9002": "plain"}'},
        master_default=True,
        hosts_default=False,
        mention_default=True,
    )
    assert (found.master, found.hosts_on, found.opted) == (True, True, frozenset({9001}))
    assert found.plain(9002) and not found.plain(9001)
