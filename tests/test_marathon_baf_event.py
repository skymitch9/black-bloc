import json
from datetime import UTC, datetime, timedelta

import pytest

from black_bloc import marathon as mt
from black_bloc import marathon_baf_event as baf
from black_bloc import marathon_role_ping as mrp

NOW = datetime(2027, 1, 4, 18, 0, tzinfo=UTC)
RUNNER = {"name": "Sky", "user_id": 9001, "part": "runner"}
STRANGER = {"name": "Somebody", "user_id": None, "part": "runner"}
HOST = {"name": "Kai", "user_id": 9002, "part": "host"}
MARKS = (1440, 120, 15)


def at(minutes):
    return (NOW + timedelta(minutes=minutes)).isoformat()


def run(ident, start, people=(RUNNER,), *, state=mt.UPCOMING, sent=(), length=60):
    return {
        "id": ident,
        "order_no": ident,
        "game": f"Game {ident}",
        "people": json.dumps(list(people)),
        "scheduled_at": at(start),
        "ends_at": at(start + length),
        "sheet_at": at(start),
        "sheet_ends_at": at(start + length),
        "state": state,
        "reminders_sent": json.dumps(list(sent)),
    }


def day(*people, first=180):
    return [run(index + 1, first + index * 60, one) for index, one in enumerate(people)]


def marathon(**fields):
    return {"id": 1, "name": "SS4C", "source": "horaro", "source_ref": "ss4c"} | fields


def reading(rows, **fields):
    return baf.reading(
        marathon(**fields),
        rows,
        marks=MARKS,
        ping_mark=15,
        wanted_mark=120,
        names=("Black in a Flash",),
        min_runs=2,
        ask_percent=75,
    )


def judged(rows, **fields):
    return baf.judge(
        marathon(**fields), rows, names=("Black in a Flash",), min_runs=2, ask_percent=75
    )


# --- the judgement -------------------------------------------------------------------------------


def test_every_run_with_a_baf_runner_is_a_baf_event():
    found = judged(day((RUNNER,), (RUNNER,), (RUNNER,), (RUNNER,)))
    assert (found.answer, found.reason, found.runs, found.baf) == (baf.YES, baf.BY_RUNS, 4, 4)


def test_one_all_baf_run_is_too_few_to_be_an_event():
    found = judged(day((RUNNER,)))
    assert (found.answer, found.reason) == (baf.NO, baf.BY_FEW)


@pytest.mark.parametrize(
    ("baf_runs", "runs", "answer", "reason"),
    [
        (3, 4, baf.UNSURE, baf.BY_SHARE),
        (9, 10, baf.UNSURE, baf.BY_SHARE),
        (2, 4, baf.NO, baf.BY_MIXED),
        (74, 100, baf.NO, baf.BY_MIXED),
        (75, 100, baf.UNSURE, baf.BY_SHARE),
        (0, 3, baf.NO, baf.BY_MIXED),
    ],
)
def test_the_share_decides_between_asking_and_no(baf_runs, runs, answer, reason):
    rows = day(*[(RUNNER,)] * baf_runs, *[(STRANGER,)] * (runs - baf_runs))
    found = judged(rows)
    assert (found.answer, found.reason, found.baf, found.runs) == (answer, reason, baf_runs, runs)


def test_a_baf_host_never_makes_a_run_a_baf_run():
    found = judged(day((RUNNER,), (STRANGER, HOST), (RUNNER,), (RUNNER,)))
    assert (found.answer, found.baf, found.runs) == (baf.UNSURE, 3, 4)
    assert baf.has_runner(run(1, 0, (STRANGER, HOST))) is False
    assert baf.has_runner(run(1, 0, (RUNNER | {"counts": False},))) is False


def test_a_dropped_run_is_not_counted():
    rows = day((RUNNER,), (RUNNER,), (STRANGER,))
    rows[2]["state"] = mt.DROPPED
    assert judged(rows).answer == baf.YES


@pytest.mark.parametrize(
    "name",
    ["Black in a Flash", "black in a flash", "BlackInAFlash", "Black in a Flash: Soul Train"],
)
def test_the_shows_name_makes_it_a_baf_event_whatever_its_runs(name):
    found = judged(day((STRANGER,), (STRANGER,)), name=name)
    assert (found.answer, found.reason, found.name) == (baf.YES, baf.BY_NAME, "Black in a Flash")


def test_a_hotfix_shows_own_name_counts_after_staff_rename_the_marathon():
    found = judged(
        day((STRANGER,)),
        name="Our autumn show",
        source="gdq_hotfix",
        source_ref="black-in-a-flash/2026-10-06",
    )
    assert (found.answer, found.reason) == (baf.YES, baf.BY_NAME)
    assert judged(day((STRANGER,)), name="Flash in the pan").answer == baf.NO


def test_the_staff_answer_beats_every_rule_both_ways():
    said_no = judged(day((RUNNER,), (RUNNER,)), name="Black in a Flash", baf_event=0)
    said_yes = judged(day((STRANGER,), (STRANGER,)), baf_event=1)
    assert (said_no.answer, said_no.reason) == (baf.NO, baf.BY_STAFF)
    assert (said_yes.answer, said_yes.reason) == (baf.YES, baf.BY_STAFF)
    assert (said_yes.runs, said_yes.baf) == (2, 0)


@pytest.mark.parametrize(
    ("given", "understood", "value"),
    [
        ("yes", True, True),
        ("No", True, False),
        ("follow", True, None),
        (None, True, None),
        (True, True, True),
        (0, True, False),
        ("", True, None),
        ("maybe", False, None),
        (7, False, None),
    ],
)
def test_the_three_answers_and_nothing_else_are_understood(given, understood, value):
    assert baf.clean(given) == (understood, value)


def test_the_names_list_drops_blanks_and_repeats():
    assert baf.names_of(" Black in a Flash , , black  in a flash, Soul Train ") == (
        "Black in a Flash",
        "Soul Train",
    )


# --- show-days -----------------------------------------------------------------------------------


def test_each_show_day_is_judged_by_itself():
    rows = [*day((RUNNER,), (RUNNER,)), *day((STRANGER,), (STRANGER,), first=180 + 1440)]
    rows[2]["id"], rows[3]["id"] = 3, 4
    found = reading(rows)
    assert len(found.days) == 2
    answers = [baf.judgement_of(found, one).answer for one in found.days]
    assert answers == [baf.YES, baf.NO]


# --- which heads-up carries it -------------------------------------------------------------------


def test_the_two_hour_heads_up_of_the_first_baf_run_carries_it_and_nothing_else_does():
    rows = day((RUNNER,), (RUNNER,), (RUNNER,))
    found = reading(rows)
    kinds = {
        (row["id"], mark): baf.plan(found, row, mark).kind for row in rows for mark in MARKS
    }
    assert kinds[(1, 120)] == baf.CARRY
    assert kinds[(1, 1440)] == baf.QUIET
    assert {kinds[(2, mark)] for mark in MARKS} | {kinds[(3, mark)] for mark in MARKS} == {
        baf.QUIET
    }
    assert baf.plan(found, rows[1], 15).reason == mrp.BAF_EVENT_DAY


def test_a_day_that_is_not_a_baf_event_is_left_to_the_per_run_rule():
    rows = day((RUNNER,), (STRANGER,), (STRANGER,))
    assert {baf.plan(reading(rows), rows[0], mark).kind for mark in MARKS} == {baf.PER_RUN}


def test_after_the_two_hour_mark_the_next_heads_up_of_the_first_run_carries_it():
    rows = day((RUNNER,), (RUNNER,))
    rows[0]["reminders_sent"] = json.dumps([1440, 120])
    found = reading(rows)
    assert baf.plan(found, rows[0], 15).kind == baf.CARRY
    assert baf.plan(found, rows[1], 120).kind == baf.QUIET


def test_a_first_run_live_or_done_hands_it_to_the_next_baf_run():
    rows = day((RUNNER,), (STRANGER,), (RUNNER,))
    rows[0]["state"] = mt.LIVE
    found = reading(rows, baf_event=1)
    assert baf.plan(found, rows[2], 120).kind == baf.CARRY
    rows[0]["state"] = mt.DONE
    assert baf.plan(reading(rows, baf_event=1), rows[2], 15).kind == baf.CARRY


def test_a_first_run_with_nobody_to_name_publicly_is_passed_over():
    rows = day((RUNNER,), (RUNNER,))
    found = reading(rows)
    assert baf.plan(found, rows[1], 120, speaks=lambda row: row["id"] != 1).kind == baf.CARRY
    assert baf.plan(found, rows[0], 120, speaks=lambda row: row["id"] != 1).kind == baf.QUIET


def test_a_stored_ping_closes_the_day_whatever_the_judgement_says_now():
    rows = day((RUNNER,), (RUNNER,))
    record = baf.record_for(rows, rows[0], 120, NOW)
    found = reading(rows, baf_event=0, baf_event_pings=json.dumps([record]))
    plans = [baf.plan(found, row, 15) for row in rows]
    assert {one.kind for one in plans} == {baf.QUIET}
    assert {one.reason for one in plans} == {mrp.BAF_EVENT_PINGED}


def test_a_ping_still_covers_the_day_when_its_first_run_is_dropped_or_re_made():
    rows = day((RUNNER,), (RUNNER,), (RUNNER,))
    record = baf.record_for(rows, rows[0], 120, NOW)
    dropped = [dict(rows[0], state=mt.DROPPED), *rows[1:]]
    assert baf.pinged([record], baf.days_of(dropped)[0]) == record
    remade = [dict(one, id=one["id"] + 100) for one in rows]
    assert baf.pinged([record], baf.days_of(remade)[0]) == record
    tomorrow = [dict(one, id=one["id"] + 10) for one in day((RUNNER,), (RUNNER,), first=1620)]
    assert baf.pinged([record], tomorrow) is None


def test_a_missed_row_never_blocks_a_later_ping():
    rows = day((RUNNER,), (RUNNER,))
    gone = baf.record_for(rows, None, None, NOW, missed=True)
    assert baf.pinged([gone], rows) is None and baf.missed([gone], rows) == gone
    assert baf.plan(reading(rows, baf_event_pings=json.dumps([gone])), rows[0], 120).kind == (
        baf.CARRY
    )


def test_a_claim_is_given_back_or_kept_with_its_message():
    rows = day((RUNNER,), (RUNNER,))
    claim = baf.record_for(rows, rows[0], 120, NOW)
    other = baf.record_for(day((RUNNER,), first=3000), None, None, NOW, missed=True)
    assert baf.without([other, claim], claim) == [other]
    (kept, done) = baf.sent([other, claim], claim, message_id=5)
    assert kept == other and (done["sent"], done["message_id"], done["mark"]) == (True, 5, 120)
    assert baf.pings_of({"baf_event_pings": baf.dump_pings([done])}) == [done]
    assert baf.dump_pings([]) is None and baf.pings_of({"baf_event_pings": "{"}) == []


@pytest.mark.parametrize(
    ("marks", "wanted", "mark", "fell_back"),
    [
        ((1440, 120, 15), 120, 120, False),
        ((1440, 60, 15), 120, 60, True),
        ((1440, 15), 120, 15, True),
        ((1440, 240), 120, 240, True),
        ((), 120, 120, False),
    ],
)
def test_a_ping_mark_that_is_not_a_reminder_mark_falls_back(marks, wanted, mark, fell_back):
    assert baf.event_mark(marks, wanted) == (mark, fell_back)


def test_a_heads_up_still_to_come_is_predicted_only_for_the_carriers_next_mark():
    rows = day((RUNNER,), (RUNNER,))
    found = reading(rows)
    assert baf.predicts(found, rows[0], 120) is True
    assert baf.predicts(found, rows[0], 15) is False
    assert baf.predicts(found, rows[1], 120) is False
    mixed = day((RUNNER,), (STRANGER,), (STRANGER,))
    assert baf.predicts(reading(mixed), mixed[0], 15) is None


def test_a_host_blocks_heads_up_is_quiet_on_a_baf_event_day_and_on_a_pinged_one():
    rows = day((RUNNER,), (RUNNER,))
    assert baf.quiet_reason(reading(rows), rows[0]) == mrp.BAF_EVENT_DAY
    record = baf.record_for(rows, rows[0], 120, NOW)
    pinged = reading(rows, baf_event=0, baf_event_pings=json.dumps([record]))
    assert baf.quiet_reason(pinged, rows[0]) == mrp.BAF_EVENT_PINGED
    mixed = day((RUNNER,), (STRANGER,), (STRANGER,))
    assert baf.quiet_reason(reading(mixed), mixed[0]) is None


# --- what staff read -----------------------------------------------------------------------------


def test_the_day_states_say_who_carries_it_what_was_worked_out_and_when_it_is_over():
    rows = [*day((RUNNER,), (RUNNER,)), *day((RUNNER,), (STRANGER,), first=180 + 1440)]
    rows[2]["id"], rows[3]["id"] = 3, 4
    rows[0]["state"] = rows[1]["state"] = mt.DONE
    one, two = baf.day_states(reading(rows, baf_event=1))
    assert (one.over, one.carrier, one.judgement.reason) == (True, None, baf.BY_STAFF)
    assert (one.worked.answer, two.worked.answer) == (baf.YES, baf.NO)
    assert (two.over, two.carrier["id"], two.carrier_mark, two.governed) == (False, 3, 120, True)
    assert baf.current([one, two]) is two and baf.asks([one, two]) is None


def test_the_first_unsure_day_still_to_come_is_the_one_asked_about():
    rows = day((RUNNER,), (RUNNER,), (RUNNER,), (STRANGER,))
    (state,) = baf.day_states(reading(rows))
    assert baf.asks([state]) is state
    assert baf.asks(baf.day_states(reading(rows, baf_event=0))) is None


def test_a_show_that_never_stops_is_one_day_per_calendar_date_in_the_servers_zone():
    rows = [run(index + 1, index * 360, length=360) for index in range(8)]
    utc = baf.days_of(rows, "UTC")
    assert [[one["id"] for one in day] for day in utc] == [[1], [2, 3, 4, 5], [6, 7, 8]]
    phoenix = baf.days_of(rows, "America/Phoenix")
    assert [[one["id"] for one in day] for day in phoenix] == [[1, 2, 3], [4, 5, 6, 7], [8]]
    assert baf.days_of(rows[:4], "UTC") == [rows[:4]]
    record = baf.record_for(utc[1], rows[1], 120, NOW)
    assert baf.pinged([record], utc[1]) == record
    assert baf.pinged([dict(record, runs=[])], utc[0]) is None
    assert baf.pinged([dict(record, runs=[])], utc[2]) is None


# --- review fixes 2026-10-06 ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "answer"),
    [
        ("Black in a Flash", baf.YES),
        ("Black in a Flash: Soul Train", baf.YES),
        ("Not Black in a Flash", baf.NO),
        ("Black in a Flashback", baf.NO),
    ],
)
def test_a_show_name_matches_on_whole_words_from_its_start(name, answer):
    assert judged(day((STRANGER,), (STRANGER,)), name=name).answer == answer


def test_a_per_run_mention_closes_the_day_only_once_it_is_a_baf_event():
    rows = day((RUNNER,), (STRANGER,), (STRANGER,), (RUNNER,))
    record = baf.record_for(rows, rows[0], 15, NOW, per_run=True, sent=True)
    stored = json.dumps([record])
    mixed = reading(rows, baf_event_pings=stored)
    assert baf.plan(mixed, rows[3], 15).kind == baf.PER_RUN
    assert baf.quiet_reason(mixed, rows[1]) is None and baf.predicts(mixed, rows[3], 15) is None
    assert baf.day_states(mixed)[0].record is None and not baf.day_states(mixed)[0].governed
    event = reading(rows, baf_event=1, baf_event_pings=stored)
    plans = [baf.plan(event, rows[3], mark) for mark in (120, 15)]
    assert {(one.kind, one.reason) for one in plans} == {(baf.QUIET, mrp.BAF_EVENT_PINGED)}
    assert baf.quiet_reason(event, rows[1]) == mrp.BAF_EVENT_PINGED
    assert baf.predicts(event, rows[3], 120) is False
    assert baf.day_states(event)[0].record == record
    back = reading(rows, baf_event=0, baf_event_pings=stored)
    assert baf.plan(back, rows[3], 15).kind == baf.PER_RUN


def test_a_days_own_ping_is_read_before_a_per_run_one():
    rows = day((RUNNER,), (RUNNER,))
    early = baf.record_for(rows, rows[0], 15, NOW, per_run=True, sent=True)
    own = baf.record_for(rows, rows[1], 120, NOW, sent=True)
    found = reading(rows, baf_event=1, baf_event_pings=json.dumps([early, own]))
    assert baf.day_states(found)[0].record == own


def two_days():
    later = [run(11 + index, 1620 + index * 60, one) for index, one in enumerate(
        ((RUNNER,), (RUNNER,), (RUNNER,), (RUNNER,), (STRANGER,))
    )]
    return [*day((RUNNER,), (RUNNER,)), *later]


def test_a_days_own_answer_decides_that_day_only_and_the_switch_beats_it():
    rows = two_days()
    said = baf.record_for(baf.days_of(rows)[1], None, None, NOW) | {"answer": baf.NO}
    asked = json.dumps([said])
    one, two = baf.day_states(reading(rows, baf_event_ask=asked))
    assert (one.judgement.answer, one.judgement.reason) == (baf.YES, baf.BY_RUNS)
    assert (two.judgement.answer, two.judgement.reason) == (baf.NO, baf.BY_LEADS)
    assert (two.worked.answer, two.ask) == (baf.UNSURE, said)
    switched = baf.day_states(reading(rows, baf_event=1, baf_event_ask=asked))
    assert [one.judgement.reason for one in switched] == [baf.BY_STAFF, baf.BY_STAFF]
    assert baf.unsure(baf.day_states(reading(rows))) == [baf.day_states(reading(rows))[1]]
    assert baf.unsure([one, two]) == []


def test_a_days_own_answer_survives_a_re_read_that_re_keys_its_runs():
    rows = two_days()
    said = baf.record_for(baf.days_of(rows)[1], None, None, NOW) | {"answer": baf.YES}
    remade = [dict(one, id=one["id"] + 100) for one in rows]
    one, two = baf.day_states(reading(remade, baf_event_ask=json.dumps([said])))
    assert (one.judgement.reason, one.ask) == (baf.BY_RUNS, None)
    assert (two.judgement.answer, two.judgement.reason) == (baf.YES, baf.BY_LEADS)


def test_the_question_records_round_trip_and_a_broken_column_reads_as_none():
    assert baf.asks_of({"baf_event_ask": baf.dump_asks([{"message_id": 5}])}) == [
        {"message_id": 5}
    ]
    assert baf.asks_of({"baf_event_ask": json.dumps({"message_id": 5})}) == [{"message_id": 5}]
    assert baf.asks_of({"baf_event_ask": "["}) == [] and baf.dump_asks([]) is None
    assert baf.asks_of({}) == []


def never_stops():
    return [run(1, 0, length=390), run(2, 360, length=1200), run(3, 1560, length=60)]


def test_a_ping_never_closes_the_next_calendar_day_when_the_estimates_overlap():
    rows = never_stops()
    days = baf.days_of(rows, "UTC")
    assert [[one["id"] for one in each] for each in days] == [[1], [2, 3]]
    record = baf.record_for(days[0], rows[0], 120, NOW)
    found = reading(rows, baf_event_pings=json.dumps([record]))
    assert baf.plan(found, rows[1], 120).kind == baf.CARRY
    one, two = baf.day_states(found)
    assert (one.record, two.record) == (record, None)


def test_a_re_keyed_day_is_still_its_own_and_never_its_neighbours():
    rows = never_stops()
    record = baf.record_for(baf.days_of(rows, "UTC")[0], rows[0], 120, NOW)
    remade = [dict(one, id=one["id"] + 100) for one in rows]
    one, two = baf.day_states(reading(remade, baf_event_pings=json.dumps([record])))
    assert (one.record, two.record) == (record, None)


def test_why_nothing_carries_the_ping_is_one_of_three_causes():
    spent = day((RUNNER,), (STRANGER,))
    spent[0]["state"] = mt.LIVE
    unmatched = day((STRANGER,), (STRANGER,))
    named = day((RUNNER,), (RUNNER,))
    assert baf.day_states(reading(spent, baf_event=1))[0].cause == baf.MARKS_SPENT
    assert baf.day_states(reading(unmatched, baf_event=1))[0].cause == baf.NO_BAF_RUN
    hidden = baf.day_states(reading(named, baf_event=1), speaks=lambda row: False)[0]
    assert (hidden.carrier, hidden.cause) == (None, baf.NOBODY_TO_NAME)
    assert baf.day_states(reading(named, baf_event=1))[0].cause is None
    assert baf.CAUSES == (baf.NOBODY_TO_NAME, baf.NO_BAF_RUN, baf.MARKS_SPENT)


def test_a_host_only_first_run_carries_the_ping_while_hosts_count_as_ours():
    rows = day((HOST,), (RUNNER,))
    assert baf.plan(reading(rows, baf_event=1), rows[0], 120).kind == baf.CARRY
    rows[0]["people"] = json.dumps([HOST | {"counts": False}])
    found = reading(rows, baf_event=1)
    assert baf.plan(found, rows[0], 120).kind == baf.QUIET
    assert baf.plan(found, rows[1], 120).kind == baf.CARRY


def posted(head="", **entry):
    copy = {"channel_id": 1, "message_id": 77, "text": "words", "head": head, "at": at(0)}
    return json.dumps({"120": {"posted": True, "public": copy} | entry})


def test_an_unsent_claim_is_confirmed_from_what_its_run_remembers_posting():
    rows = day((RUNNER,), (RUNNER,))
    claim = baf.record_for(rows, rows[0], 120, NOW)
    with_role = [dict(rows[0], reminder_posts=posted("<@&6100> ")), rows[1]]
    assert baf.proof_of(claim, with_role, 6100) == (baf.SENT, 77, 1)
    quiet = [dict(rows[0], reminder_posts=posted("<@&5> ")), rows[1]]
    assert baf.proof_of(claim, quiet, 6100)[0] == baf.UNKNOWN
    skipped = [dict(rows[0], reminder_posts=json.dumps({"120": {"posted": False}})), rows[1]]
    assert baf.proof_of(claim, skipped, 6100)[0] == baf.GIVE_BACK
    assert baf.proof_of(claim, rows, 6100)[0] == baf.UNKNOWN
    assert baf.proof_of(claim, rows[1:], 6100)[0] == baf.UNKNOWN
    assert baf.proof_of(claim, with_role, None)[0] == baf.UNKNOWN
