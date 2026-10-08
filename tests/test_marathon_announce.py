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
    ma.IN: "Announce {name}",
    ma.OUT: "Don't announce {name}",
    ma.DEFAULT: "{name}: back to the default",
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
    ma.WHY_RUNNERS_OFF: "runners are off",
    ma.WHY_HOSTS_OFF: "hosts are off",
}

# the part, Runner announcements, Host announcements, opted out, the run's answer -> (yes, why)
TRUTH = [
    (ma.RUNNER, False, False, False, None, (False, ma.WHY_RUNNERS_OFF)),
    (ma.RUNNER, False, False, False, ma.IN, (True, ma.WHY_RUN)),
    (ma.RUNNER, False, False, False, ma.OUT, (False, ma.WHY_RUN)),
    (ma.RUNNER, False, False, True, None, (False, ma.WHY_MARATHON)),
    (ma.RUNNER, False, False, True, ma.IN, (True, ma.WHY_RUN)),
    (ma.RUNNER, False, False, True, ma.OUT, (False, ma.WHY_RUN)),
    (ma.RUNNER, False, True, False, None, (False, ma.WHY_RUNNERS_OFF)),
    (ma.RUNNER, False, True, False, ma.IN, (True, ma.WHY_RUN)),
    (ma.RUNNER, False, True, False, ma.OUT, (False, ma.WHY_RUN)),
    (ma.RUNNER, False, True, True, None, (False, ma.WHY_MARATHON)),
    (ma.RUNNER, False, True, True, ma.IN, (True, ma.WHY_RUN)),
    (ma.RUNNER, False, True, True, ma.OUT, (False, ma.WHY_RUN)),
    (ma.RUNNER, True, False, False, None, (True, ma.WHY_DEFAULT)),
    (ma.RUNNER, True, False, False, ma.IN, (True, ma.WHY_RUN)),
    (ma.RUNNER, True, False, False, ma.OUT, (False, ma.WHY_RUN)),
    (ma.RUNNER, True, False, True, None, (False, ma.WHY_MARATHON)),
    (ma.RUNNER, True, False, True, ma.IN, (True, ma.WHY_RUN)),
    (ma.RUNNER, True, False, True, ma.OUT, (False, ma.WHY_RUN)),
    (ma.RUNNER, True, True, False, None, (True, ma.WHY_DEFAULT)),
    (ma.RUNNER, True, True, False, ma.IN, (True, ma.WHY_RUN)),
    (ma.RUNNER, True, True, False, ma.OUT, (False, ma.WHY_RUN)),
    (ma.RUNNER, True, True, True, None, (False, ma.WHY_MARATHON)),
    (ma.RUNNER, True, True, True, ma.IN, (True, ma.WHY_RUN)),
    (ma.RUNNER, True, True, True, ma.OUT, (False, ma.WHY_RUN)),
    (ma.HOST, False, False, False, None, (False, ma.WHY_HOSTS_OFF)),
    (ma.HOST, False, False, False, ma.IN, (True, ma.WHY_RUN)),
    (ma.HOST, False, False, False, ma.OUT, (False, ma.WHY_RUN)),
    (ma.HOST, False, False, True, None, (False, ma.WHY_MARATHON)),
    (ma.HOST, False, False, True, ma.IN, (True, ma.WHY_RUN)),
    (ma.HOST, False, False, True, ma.OUT, (False, ma.WHY_RUN)),
    (ma.HOST, False, True, False, None, (True, ma.WHY_DEFAULT)),
    (ma.HOST, False, True, False, ma.IN, (True, ma.WHY_RUN)),
    (ma.HOST, False, True, False, ma.OUT, (False, ma.WHY_RUN)),
    (ma.HOST, False, True, True, None, (False, ma.WHY_MARATHON)),
    (ma.HOST, False, True, True, ma.IN, (True, ma.WHY_RUN)),
    (ma.HOST, False, True, True, ma.OUT, (False, ma.WHY_RUN)),
    (ma.HOST, True, False, False, None, (False, ma.WHY_HOSTS_OFF)),
    (ma.HOST, True, False, False, ma.IN, (True, ma.WHY_RUN)),
    (ma.HOST, True, False, False, ma.OUT, (False, ma.WHY_RUN)),
    (ma.HOST, True, False, True, None, (False, ma.WHY_MARATHON)),
    (ma.HOST, True, False, True, ma.IN, (True, ma.WHY_RUN)),
    (ma.HOST, True, False, True, ma.OUT, (False, ma.WHY_RUN)),
    (ma.HOST, True, True, False, None, (True, ma.WHY_DEFAULT)),
    (ma.HOST, True, True, False, ma.IN, (True, ma.WHY_RUN)),
    (ma.HOST, True, True, False, ma.OUT, (False, ma.WHY_RUN)),
    (ma.HOST, True, True, True, None, (False, ma.WHY_MARATHON)),
    (ma.HOST, True, True, True, ma.IN, (True, ma.WHY_RUN)),
    (ma.HOST, True, True, True, ma.OUT, (False, ma.WHY_RUN)),
]


@pytest.mark.parametrize(("role", "runners_on", "hosts_on", "opted", "answer", "wanted"), TRUTH)
def test_every_row_of_the_truth_table(role, runners_on, hosts_on, opted, answer, wanted):
    said = ma.decide(
        runners_on=runners_on, opted_out=opted, answer=answer, role=role, hosts_on=hosts_on
    )
    assert (said.yes, said.why) == wanted


def test_the_truth_table_is_every_combination_once():
    assert len(TRUTH) == 2 * 2 * 2 * 2 * 3 == len({one[:5] for one in TRUTH})


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
    assert ids(ma.run_people(row, ma.Policy(runners_on=False, hosts_on=True))) == [8101]
    assert ma.run_people(row, ma.Policy(runners_on=False)) == []


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
    hosts_only = ma.Policy(runners_on=False, hosts_on=True)
    assert ids(ma.block_people(a_block(third), hosts_only)) == [8101]
    most = [a_run(one, [HOSTING], {8101: ma.OUT} if one != 2 else None) for one in (1, 2, 3, 4)]
    assert ids(ma.block_people(a_block(most), ma.Policy(hosts_on=True))) == [8101]
    every = [a_run(one, [HOSTING], {8101: ma.OUT}) for one in (1, 2, 3, 4)]
    assert ma.block_people(a_block(every), ma.Policy(hosts_on=True)) == []


def test_a_host_who_also_runs_one_run_of_their_block_does_not_announce_the_block_by_default():
    rows = [a_run(1, [HOSTING]), a_run(2, [HOSTING, HOSTING | {"part": "runner"}])]
    assert ma.block_people(a_block(rows), ma.Policy()) == []
    assert ids(ma.run_people(rows[1], ma.Policy())) == [8101]


def test_a_run_s_own_answer_beats_the_marathon_wide_opt_out_and_the_switch_for_their_part():
    row = a_run(1, [SKY, RIVET], {9001: ma.IN})
    assert ids(ma.run_people(row, out(9001, 9002))) == [9001]
    assert ids(ma.run_people(row, ma.Policy(runners_on=False))) == [9001]
    assert ids(ma.run_people(a_run(1, [SKY], {9001: ma.OUT}), ma.Policy())) == []
    hosted = a_run(1, [HOSTING], {8101: ma.IN})
    assert ids(ma.run_people(hosted, out(8101))) == [8101]
    assert ids(ma.run_people(a_run(1, [HOSTING]), ma.Policy(runners_on=False, hosts_on=True))) == [
        8101
    ]


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


def test_each_person_gets_one_button_the_move_their_state_allows():
    row = a_run(3, [SKY, QUIET_HOST])
    assert moves_of(row) == [
        (9001, ma.OUT, "Don't announce Sky"),
        (8101, ma.IN, "Announce anarchy"),
    ]
    answered = a_run(3, [SKY, QUIET_HOST], {9001: ma.OUT, 8101: ma.IN})
    found = ma.Policy(mentions={9001: ma.PLAIN})
    assert moves_of(answered, found) == [
        (9001, ma.DEFAULT, "Sky: back to the default"),
        (8101, ma.DEFAULT, "anarchy: back to the default"),
    ]
    assert moves_of(row, out(9001))[0] == (9001, ma.IN, "Announce Sky")
    assert moves_of(row, ma.Policy(runners_on=False))[0][1] == ma.IN
    made = ma.moves(7, row, ma.Policy(), LABELS)
    assert made[0].custom_id == "marathon:announce:7:3:9001:out"
    assert re.fullmatch(ma.MOVE_TEMPLATE, made[0].custom_id)["to"] == "out"
    assert not {one.to for one in made} & {ma.PLAIN, ma.MENTION}


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


def test_five_people_fit_as_one_row_of_buttons_and_more_become_one_menu():
    five = a_run(3, crowd(5))
    made = ma.laid_out(7, five, ma.moves(7, five, ma.Policy(), LABELS), "Pick…")
    assert len(made) == 5 and all(isinstance(one, ma.Move) for one in made)
    six = a_run(3, crowd(6))
    (pick,) = ma.laid_out(7, six, ma.moves(7, six, ma.Policy(), LABELS), "Pick…")
    assert isinstance(pick, ma.Pick) and pick.custom_id == "marathon:announce:7:3:pick"
    assert re.fullmatch(ma.PICK_TEMPLATE, pick.custom_id) and pick.label == "Pick…"
    assert len(pick.options) == 6
    assert pick.options[0] == ("9100:out", "Don't announce Runner 0")
    assert ma.option_of(pick.options[1][0]) == (9101, ma.OUT)
    assert ma.option_of("x:out") is None and ma.option_of("9100:shout") is None


def picked(count):
    row = a_run(3, crowd(count))
    made = ma.moves(7, row, ma.Policy(), LABELS)
    return made, ma.laid_out(7, row, made, "x" * 300)


@pytest.mark.parametrize(("count", "sizes"), [(12, [12]), (13, [12, 1]), (20, [12, 8])])
def test_past_twelve_people_the_menu_splits_and_nobody_loses_a_move(count, sizes):
    made, picks = picked(count)
    assert [len(one.options) for one in picks] == sizes
    assert all(len(one.options) <= ma.OPTION_LIMIT and len(one.label) == 100 for one in picks)
    offered = [value for one in picks for value, _ in one.options]
    assert offered == [f"{one.user_id}:{one.to}" for one in made]
    assert len(offered) == count and len(set(offered)) == len(offered)
    assert [one.custom_id for one in picks] == [
        "marathon:announce:7:3:pick",
        "marathon:announce:7:3:pick2",
    ][: len(picks)]
    assert [one.row for one in picks] == [1, 2][: len(picks)]
    assert all(re.fullmatch(ma.PICK_TEMPLATE, one.custom_id) for one in picks)


def test_a_long_name_is_cut_to_what_a_button_takes():
    long = a_run(3, [SKY | {"name": "S" * 200}])
    (move,) = ma.moves(7, long, ma.Policy(), LABELS)
    assert len(move.label) == 80


def test_a_runs_own_answer_where_the_host_runs_is_about_their_run_only():
    runner = HOSTING | {"part": "runner"}
    rows = [
        a_run(1, [HOSTING]),
        a_run(2, [HOSTING, runner], {8101: ma.IN}),
        a_run(3, [HOSTING]),
    ]
    assert ma.runs_it(rows[1], 8101) and not ma.runs_it(rows[0], 8101)
    assert ma.block_people(a_block(rows), out(8101)) == []
    assert ma.block_people(a_block(rows), ma.Policy()) == []
    assert ids(ma.run_people(rows[1], out(8101))) == [8101]
    left_out = [a_run(1, [HOSTING]), a_run(2, [HOSTING, runner], {8101: ma.OUT})]
    assert ids(ma.block_people(a_block(left_out), ma.Policy(hosts_on=True))) == [8101]
    assert ma.run_people(left_out[1], ma.Policy(hosts_on=True)) == []


def test_a_runs_own_answer_where_the_host_only_hosts_is_about_their_block():
    rows = [a_run(1, [HOSTING]), a_run(2, [HOSTING], {8101: ma.IN}), a_run(3, [HOSTING])]
    assert ids(ma.block_people(a_block(rows), out(8101))) == [8101]
    assert ids(ma.block_people(a_block(rows), ma.Policy())) == [8101]


def test_a_post_already_up_keeps_or_loses_names_and_gains_only_who_is_announced():
    row = a_run(1, [SKY, HOSTING])
    off = ma.Policy()
    assert ids(ma.run_standing(row, off, [9001])) == [9001]
    assert ids(ma.run_standing(row, off, [9001, 8101])) == [9001, 8101]
    assert ids(ma.run_standing(row, off, None)) == [9001, 8101]
    assert ids(ma.run_standing(row, off, [])) == [9001]
    assert ids(ma.run_standing(row, ma.Policy(hosts_on=True), [9001])) == [9001, 8101]
    assert ids(ma.run_standing(row, off._replace(runners_on=False), [9001, 8101])) == [9001, 8101]
    assert ma.run_standing(row, off._replace(runners_on=False), []) == []
    assert ids(ma.run_standing(row, off, [9001, 8101], moved=[8101])) == [9001]
    left = a_run(1, [SKY, HOSTING], {9001: ma.OUT})
    assert ids(ma.run_standing(left, off, [9001, 8101])) == [8101]
    assert ma.run_standing(left, off, [9001]) == []
    assert ids(ma.run_standing(row, out(9001), [9001, 8101])) == [8101]
    gone = a_run(1, [HOSTING])
    assert ma.run_standing(gone, off, [9001]) == []


def test_a_block_post_already_up_weighs_only_the_host_a_move_was_aimed_at():
    other = {"name": "bee", "user_id": 8103, "login": None, "part": "host"}
    rows = [a_run(1, [HOSTING, other]), a_run(2, [HOSTING, other])]
    block = SimpleNamespace(runs=rows, hosts=[dict(HOSTING), dict(other)])
    off = ma.Policy()
    assert ids(ma.block_standing(block, off, [8101, 8103])) == [8101, 8103]
    assert ids(ma.block_standing(block, off, [8101, 8103], moved=[8101])) == [8103]
    assert ids(ma.block_standing(block, off, [8103])) == [8103]
    assert ma.block_standing(block, off, []) == []


def test_the_record_of_who_a_post_names_reads_back_and_a_bad_one_reads_as_none():
    kept = ma.named_of(ma.dump_named([SKY | {"plain": "Sky"}, HOSTING]))
    assert [(one["user_id"], one["plain"]) for one in kept] == [(9001, True), (8101, False)]
    assert ma.ids_of(kept) == [9001, 8101] and ma.ids_of(None) is None
    for bad in (None, "", "{", '{"a": 1}', '[{"name": "x"}]'):
        assert ma.named_of(bad) is None
    assert ma.named_of("[]") == []


def test_the_log_names_the_decision_that_emptied_a_post():
    row = a_run(1, [SKY, HOSTING])
    named = ma.as_named([SKY])
    assert ma.run_because(row, out(9001), named) == "opted_out"
    assert ma.run_because(a_run(1, [SKY], {9001: ma.OUT}), ma.Policy(), named) == "run_answer"
    assert ma.run_because(a_run(1, [HOSTING]), ma.Policy(), named) == "not_on_run"
    assert ma.run_because(row, ma.Policy(), ma.as_named([HOSTING]), [8101]) == "hosts_off"
    assert ma.run_because(row, ma.Policy(runners_on=False), []) == "runners_off"
    rows = [a_run(1, [HOSTING]), a_run(2, [HOSTING], {8101: ma.OUT})]
    host = ma.as_named([HOSTING])
    block = SimpleNamespace(runs=rows, hosts=[dict(HOSTING)])
    assert ma.block_because(block, ma.Policy(), host) == "hosts_off"
    assert ma.block_because(block, out(8101), host) == "opted_out"
    assert ma.block_because(block, ma.Policy(runners_on=False, hosts_on=True), []) == "not_on_run"
    every = SimpleNamespace(
        runs=[a_run(one, [HOSTING], {8101: ma.OUT}) for one in (1, 2)], hosts=[dict(HOSTING)]
    )
    assert ma.block_because(every, ma.Policy(hosts_on=True), host) == "run_answer"
    assert ma.block_because(every, ma.Policy(), ma.as_named([SKY])) == "not_on_run"


def test_a_run_that_is_over_says_so_in_words():
    assert ma.over(a_run(1, [SKY]) | {"game": "Alpha"}) is None
    assert ma.over(a_run(1, [SKY], state="live") | {"game": "Alpha"}) is None
    done = ma.over(a_run(1, [SKY], state="done") | {"game": "Alpha"})
    assert done == "**Alpha** is over, so nothing was changed."
    dropped = ma.over(a_run(1, [SKY], state="dropped") | {"game": "Alpha"})
    assert dropped == "**Alpha** is off the schedule, so nothing was changed."


def test_the_state_lines_name_only_the_exceptions_and_why():
    usual = a_run(3, [SKY, RIVET])
    assert ma.state_lines(usual, ma.Policy(), STATE_WORDS) == []
    assert ma.state_lines(usual, ma.Policy(), STATE_WORDS, only=9001) == [
        "Sky: announced — the default"
    ]
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
    assert ma.state_lines(a_run(3, [SKY]), ma.Policy(runners_on=False), STATE_WORDS) == [
        "Sky: not announced — runners are off"
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
        runners_default=True,
        hosts_default=False,
        mention_default=True,
    )
    assert (found.runners_on, found.hosts_on, found.opted) == (True, True, frozenset({9001}))
    assert found.plain(9002) and not found.plain(9001)


def test_a_long_name_is_shortened_in_a_button_label_and_the_move_word_is_kept():
    name = "Somebody With A Very Long Display Name That Goes On And On For Ages XY"
    assert len(name) == 70

    said = ma.named_label("Don't announce {name}", name)

    assert len(said) == 80 and said.startswith("Don't announce Somebody") and said.endswith("…")
    assert ma.named_label("{name}: back to the default", name).endswith("…: back to the default")
    assert ma.named_label("Announce {name}", "Sky") == "Announce Sky"
    assert ma.named_label("Announce {name}", name) == f"Announce {name}"
