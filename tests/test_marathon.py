import json
from datetime import UTC, datetime, timedelta

import pytest

from black_bloc import marathon as mt
from black_bloc.marathon_sources import Person, Run
from black_bloc.settings_store import (
    MARATHON_BOARD_LINE_KEY,
    MARATHON_BOARD_TEMPLATE_KEY,
    MARATHON_DEFAULTS,
    MARATHON_DONE_TEMPLATE_KEY,
    MARATHON_LIVE_TEMPLATE_KEY,
    MARATHON_REMINDER_TEMPLATE_KEY,
    MARATHON_WORDS,
    SettingError,
    coerce_value,
)

NOW = datetime(2027, 1, 4, 18, 0, tzinfo=UTC)


def iso(minutes: int) -> str:
    return (NOW + timedelta(minutes=minutes)).isoformat()


def row(ident, *, at, state=mt.UPCOMING, game="Game", people=None, order=None, **extra):
    return {
        "id": ident,
        "external_id": str(ident),
        "order_no": order if order is not None else ident,
        "game": game,
        "display_name": game,
        "twitch_game": extra.pop("twitch_game", ""),
        "category": "Any%",
        "scheduled_at": iso(at),
        "ends_at": iso(at + extra.pop("length", 60)),
        "state": state,
        "people": json.dumps(people or []),
        "reminders_sent": json.dumps(extra.pop("sent", [])),
        **extra,
    }


def run(ident, *, at, game="Game", people=()):
    return Run(str(ident), ident, game, game, "Any%", iso(at), iso(at + 60), 3600, tuple(people))


OURS = [{"name": "Sky", "login": "sky", "part": "runner", "user_id": 9}]


# --- matching ---------------------------------------------------------------------------------


def test_a_runner_is_ours_through_their_linked_twitch_login_whatever_its_case():
    found = mt.match_people([Person("Sky", "SkyRuns", "runner")], {"skyruns": 9}, [])
    assert found == [{"name": "Sky", "login": "SkyRuns", "part": "runner", "user_id": 9}]


def test_a_name_with_no_login_is_ours_through_a_staff_pairing():
    found = mt.match_people(
        [Person("Interview Crew", None, "host")],
        {},
        [{"marathon_id": None, "runner_name": "interview crew", "user_id": 5}],
    )
    assert found[0]["user_id"] == 5


def test_a_pairing_wins_over_the_automatic_match_and_this_marathons_wins_over_everywhere():
    people = [Person("Sky", "sky", "runner")]
    pairings = [
        {"marathon_id": None, "runner_name": "sky", "user_id": 2},
        {"marathon_id": 7, "runner_name": "sky", "user_id": 3},
        {"marathon_id": 8, "runner_name": "sky", "user_id": 4},
    ]
    assert mt.match_people(people, {"sky": 9}, pairings, marathon_id=7)[0]["user_id"] == 3
    assert mt.match_people(people, {"sky": 9}, pairings[:1], marathon_id=7)[0]["user_id"] == 2


def test_hosts_and_commentators_are_matched_only_while_the_key_says_so():
    people = [Person("Host", "hostlogin", "host"), Person("Com", "comlogin", "commentator")]
    links = {"hostlogin": 1, "comlogin": 2}
    assert [one["user_id"] for one in mt.match_people(people, links, [])] == [1, 2]
    off = mt.match_people(people, links, [], match_hosts=False)
    assert [one["user_id"] for one in off] == [None, None]


def test_ours_is_one_line_per_member_with_the_runner_part_first():
    people = [
        {"name": "Sky", "part": "commentator", "user_id": 9},
        {"name": "Sky", "part": "runner", "user_id": 9},
        {"name": "Other", "part": "runner", "user_id": None},
    ]
    assert mt.ours(people) == [{"name": "Sky", "part": "runner", "user_id": 9}]


def test_unmatched_names_are_every_name_nobody_owns_once():
    rows = [
        row(1, at=0, people=[{"name": "Gelly", "user_id": None}, {"name": "Sky", "user_id": 9}]),
        row(2, at=60, people=[{"name": "gelly", "user_id": None}]),
    ]
    assert mt.unmatched_names(rows) == ["Gelly"]


# --- the diff ---------------------------------------------------------------------------------


def test_a_new_run_is_inserted_and_a_known_one_is_updated_in_place():
    plan = mt.diff([row(1, at=0)], [run(1, at=0), run(2, at=60)], move_minutes=5)
    assert [one.external_id for one in plan.inserts] == ["2"]
    assert [(one[0]["id"], one[2]) for one in plan.updates] == [(1, False)]


def test_a_move_under_the_threshold_is_not_a_move_and_one_at_it_is():
    under = mt.diff([row(1, at=0)], [run(1, at=4)], move_minutes=5)
    at = mt.diff([row(1, at=0)], [run(1, at=5)], move_minutes=5)
    earlier = mt.diff([row(1, at=0)], [run(1, at=-40)], move_minutes=5)
    assert under.moved == []
    assert len(at.moved) == 1
    assert len(earlier.moved) == 1


def test_a_run_missing_from_the_fetch_is_dropped_and_a_done_one_is_left_as_history():
    plan = mt.diff([row(1, at=0), row(2, at=-120, state=mt.DONE)], [], move_minutes=5)
    assert [one["id"] for one in plan.dropped] == [1]


def test_a_dropped_run_that_reappears_is_named_so_it_goes_back_to_upcoming():
    plan = mt.diff([row(1, at=0, state=mt.DROPPED)], [run(1, at=0)], move_minutes=5)
    assert [one["id"] for one in plan.reappeared] == [1]
    assert plan.dropped == []


def test_the_hash_moves_with_the_schedule_and_not_otherwise():
    first = mt.schedule_hash([run(1, at=0)])
    assert first == mt.schedule_hash([run(1, at=0)])
    assert first != mt.schedule_hash([run(1, at=10)])


def test_span_is_the_first_start_and_the_last_end():
    assert mt.span([run(2, at=60), run(1, at=0)]) == (iso(0), iso(120))
    assert mt.span([]) == (None, None)


# --- phase and cadence ------------------------------------------------------------------------


def marathon(**extra):
    return {"id": 1, "active": 1, "starts_at": iso(0), "ends_at": iso(600), **extra}


@pytest.mark.parametrize(
    ("moment", "wanted"),
    [
        (timedelta(days=-8), mt.FAR),
        (timedelta(days=-6), mt.NEAR),
        (timedelta(minutes=30), mt.ON),
        (timedelta(minutes=700), mt.OVER),
    ],
)
def test_the_phase_follows_the_clock(moment, wanted):
    assert mt.phase(marathon(), NOW + moment, lead_days=7) == wanted


def test_a_paused_marathon_is_paused_and_never_due():
    row_ = marathon(active=0)
    assert mt.phase(row_, NOW, lead_days=7) == mt.PAUSED
    assert not mt.fetch_due(row_, NOW, poll_minutes=30, far_hours=24, lead_days=7)


def test_a_fresh_marathon_is_read_at_once():
    assert mt.fetch_due(marathon(), NOW, poll_minutes=30, far_hours=24, lead_days=7)


def test_near_ones_read_every_poll_gap_and_far_ones_every_far_gap():
    near = marathon(last_fetched_at=(NOW - timedelta(minutes=31)).isoformat())
    assert mt.fetch_due(near, NOW, poll_minutes=30, far_hours=24, lead_days=7)
    fresh = marathon(last_fetched_at=(NOW - timedelta(minutes=29)).isoformat())
    assert not mt.fetch_due(fresh, NOW, poll_minutes=30, far_hours=24, lead_days=7)
    own = marathon(poll_minutes=10, last_fetched_at=(NOW - timedelta(minutes=11)).isoformat())
    assert mt.fetch_due(own, NOW, poll_minutes=30, far_hours=24, lead_days=7)
    far = marathon(
        starts_at=(NOW + timedelta(days=30)).isoformat(),
        ends_at=(NOW + timedelta(days=37)).isoformat(),
        last_fetched_at=(NOW - timedelta(hours=2)).isoformat(),
    )
    assert not mt.fetch_due(far, NOW, poll_minutes=30, far_hours=24, lead_days=7)


def test_a_day_after_the_end_the_marathon_is_far_again_and_its_board_comes_down():
    later = NOW + timedelta(minutes=600) + timedelta(days=1, minutes=1)
    assert not mt.is_near(marathon(), later, lead_days=7)
    assert mt.board_due_off(marathon(), later)
    assert not mt.board_due_off(marathon(), NOW)


def test_the_window_is_the_marathon_padded_by_the_slack():
    assert mt.window_bounds(marathon(), 2) == (iso(-120), iso(720))
    assert mt.window_bounds({"starts_at": None}, 2) is None


# --- the live title ---------------------------------------------------------------------------


def test_the_title_naming_a_game_finds_that_run():
    rows = [row(1, at=0, game="Super Mario 64"), row(2, at=60, game="Celeste")]
    title = "AGDQ 2027 benefiting PCF - Celeste - Any% by @someone"
    assert mt.title_hit(title, "Celeste", rows, NOW + timedelta(minutes=55))["id"] == 2


def test_a_runners_name_breaks_a_tie_between_two_runs_of_one_game():
    rows = [
        row(1, at=0, game="Celeste", people=[{"name": "Alpha", "part": "runner"}]),
        row(2, at=60, game="Celeste", people=[{"name": "Beta", "part": "runner"}]),
    ]
    found = mt.title_hit("Celeste Any% ft. Beta", "", rows, NOW)
    assert found["id"] == 2


def test_the_nearest_scheduled_run_wins_when_nothing_else_does():
    rows = [row(1, at=-300, game="Celeste"), row(2, at=30, game="Celeste")]
    assert mt.title_hit("Celeste", "", rows, NOW)["id"] == 2


def test_the_stream_category_matches_the_runs_twitch_game():
    rows = [row(1, at=0, game="Devil May Cry 5: Special Edition", twitch_game="Devil May Cry 5")]
    assert mt.title_hit("AGDQ 2027 Day 2 !schedule", "Devil May Cry 5", rows, NOW)["id"] == 1


def test_a_title_that_names_nothing_on_the_schedule_is_no_hit():
    rows = [row(1, at=0, game="Celeste")]
    assert mt.title_hit("[Rerun] Flame Fatales 2026 - Day 5 !schedule", "", rows, NOW) is None
    assert mt.title_hit("Celeste", "", rows, NOW + timedelta(hours=13)) is None


def test_a_short_game_name_never_matches_inside_a_word():
    rows = [row(1, at=0, game="Go")]
    assert mt.title_hit("Going fast", "", rows, NOW) is None


# --- states -----------------------------------------------------------------------------------


def moves(changes):
    return [(one.row["id"], one.to, one.because, one.skipped) for one in changes]


def test_a_title_hit_goes_live_and_every_earlier_upcoming_run_is_done_without_a_shout():
    rows = [row(1, at=-120), row(2, at=-60, state=mt.LIVE), row(3, at=0), row(4, at=60)]
    changes = mt.advance(rows, NOW, hit=rows[2], watching=True, grace_minutes=90)
    assert moves(changes) == [
        (3, mt.LIVE, mt.BY_TITLE, False),
        (1, mt.DONE, mt.BY_TITLE, True),
        (2, mt.DONE, mt.BY_TITLE, False),
    ]


def test_with_the_title_watched_a_late_run_waits_out_the_grace():
    rows = [row(1, at=-30, length=300)]
    assert mt.advance(rows, NOW, watching=True, grace_minutes=90) == []
    later = mt.advance(rows, NOW + timedelta(minutes=61), watching=True, grace_minutes=90)
    assert moves(later) == [(1, mt.LIVE, mt.BY_SCHEDULE, False)]


def test_without_a_title_the_schedule_alone_decides_at_the_start():
    rows = [row(1, at=-60, state=mt.LIVE), row(2, at=0), row(3, at=60)]
    assert moves(mt.advance(rows, NOW, watching=False, grace_minutes=90)) == [
        (2, mt.LIVE, mt.BY_SCHEDULE, False),
        (1, mt.DONE, mt.BY_SCHEDULE, False),
    ]


def test_a_run_whose_whole_slot_went_by_is_aged_out_not_shouted():
    rows = [row(1, at=-400, length=60)]
    assert moves(mt.advance(rows, NOW, watching=False, grace_minutes=90)) == [
        (1, mt.DONE, mt.BY_SCHEDULE, True)
    ]


def test_a_live_run_ends_at_its_end_plus_the_grace_when_nothing_else_moves_it():
    rows = [row(1, at=-200, length=60, state=mt.LIVE)]
    assert moves(mt.advance(rows, NOW, watching=True, grace_minutes=90)) == [
        (1, mt.DONE, mt.BY_SCHEDULE, False)
    ]
    assert mt.advance(rows, NOW - timedelta(minutes=60), watching=True, grace_minutes=90) == []


def test_a_dropped_run_never_moves():
    assert (
        mt.advance([row(1, at=-30, state=mt.DROPPED)], NOW, watching=False, grace_minutes=0) == []
    )


# --- reminders --------------------------------------------------------------------------------


def test_the_ping_mark_is_always_one_of_the_marks():
    assert mt.reminder_marks("120, 15", 15) == (120, 15)
    assert mt.reminder_marks("120", 15) == (120, 15)
    assert mt.reminder_marks("garbage", 10) == (10,)


def test_each_mark_fires_once_at_its_moment_and_not_before():
    upcoming = row(1, at=120)
    assert mt.due_marks(upcoming, (120, 15), NOW - timedelta(minutes=1), stale_minutes=30) == (
        None,
        [],
    )
    assert mt.due_marks(upcoming, (120, 15), NOW, stale_minutes=30) == (120, [])
    sent = row(1, at=120, sent=[120])
    assert mt.due_marks(sent, (120, 15), NOW, stale_minutes=30) == (None, [])


def test_a_stale_mark_is_skipped_never_posted_late():
    late = row(1, at=10)
    assert mt.due_marks(late, (120, 15), NOW, stale_minutes=30) == (15, [120])


def test_the_latest_of_two_marks_due_together_is_the_one_posted():
    both = row(1, at=10)
    assert mt.due_marks(both, (120, 15), NOW, stale_minutes=200) == (15, [120])


def test_a_run_that_is_not_upcoming_gets_no_reminder():
    assert mt.due_marks(row(1, at=10, state=mt.LIVE), (15,), NOW, stale_minutes=30) == (None, [])


def test_a_run_moved_later_re_arms_the_marks_now_in_the_future():
    assert mt.rearmed([120, 15], iso(200), NOW) == []
    assert mt.rearmed([120, 15], iso(60), NOW) == [120]


def test_the_marks_setting_refuses_anything_but_one_to_six_minutes():
    assert coerce_value("marathon_reminder_minutes", "15, 120, 15") == "120, 15"
    for bad in ("", "0", "1441", "a, b", "1,2,3,4,5,6,7", "15;30"):
        with pytest.raises(SettingError):
            coerce_value("marathon_reminder_minutes", bad)


# --- words ------------------------------------------------------------------------------------

WORDS = {key: default for key, (default, _, _) in MARATHON_WORDS.items()}
M = {"name": "AGDQ 2027", "starts_at": iso(0), "ends_at": iso(600)}


def test_every_post_fills_every_placeholder_it_takes():
    one = row(1, at=15, game="Celeste", people=OURS)
    fields = mt.run_fields(one, M, WORDS, url="https://twitch.tv/gamesdonequick")
    for key in (
        MARATHON_REMINDER_TEMPLATE_KEY,
        MARATHON_LIVE_TEMPLATE_KEY,
        MARATHON_DONE_TEMPLATE_KEY,
    ):
        said = mt.render(WORDS[key], WORDS[key], **fields)
        assert said.fell_back is False
        assert "<@9>" in said.text and "Celeste" in said.text and "{" not in said.text
    assert fields["part"] == "runs"
    assert fields["in"] == f"<t:{int((NOW + timedelta(minutes=15)).timestamp())}:R>"


def test_a_template_that_will_not_fill_falls_back_to_the_shipped_words():
    said = mt.render("{nope} {game}", "{game}!", game="Celeste")
    assert said == mt.Rendered("Celeste!", True)


def test_the_board_lists_only_runs_of_ours_in_schedule_order():
    rows = [
        row(2, at=60, game="Second", people=OURS),
        row(1, at=0, game="First", people=OURS),
        row(3, at=30, game="Nobody's", people=[{"name": "x", "user_id": None}]),
    ]
    said = mt.board_text(
        M,
        rows,
        WORDS,
        head=WORDS[MARATHON_BOARD_TEMPLATE_KEY],
        head_default=WORDS[MARATHON_BOARD_TEMPLATE_KEY],
        line=WORDS[MARATHON_BOARD_LINE_KEY],
        line_default=WORDS[MARATHON_BOARD_LINE_KEY],
        empty="nobody",
        url="",
    )
    lines = said.text.splitlines()
    assert "(2)" in lines[0] and "AGDQ 2027" in lines[0]
    assert "First" in lines[1] and "Second" in lines[2] and len(lines) == 3
    assert "coming up" in lines[1]


def test_an_empty_board_says_so_and_a_long_one_stays_inside_one_message():
    empty = mt.board_text(
        M,
        [],
        WORDS,
        head="h",
        head_default="h",
        line="l",
        line_default="l",
        empty="nobody yet",
        url="",
    )
    assert empty.text == "h\nnobody yet"
    many = [row(i, at=i, game="G" * 80, people=OURS) for i in range(1, 60)]
    long = mt.board_text(
        M,
        many,
        WORDS,
        head="h",
        head_default="h",
        line=WORDS[MARATHON_BOARD_LINE_KEY],
        line_default=WORDS[MARATHON_BOARD_LINE_KEY],
        empty="",
        url="",
    )
    assert len(long.text) <= mt.MESSAGE_LIMIT


def test_the_url_is_the_channel_then_the_runners_own_twitch():
    one = row(1, at=0, people=OURS)
    assert mt.run_url(one, "gamesdonequick") == "https://twitch.tv/gamesdonequick"
    assert mt.run_url(one, None) == "https://twitch.tv/sky"
    assert mt.run_url(row(2, at=0), None, "fallback") == "fallback"


def test_ours_next_is_the_next_five_runs_of_ours_still_to_come():
    rows = [row(i, at=i * 60, people=OURS) for i in range(8)]
    rows.append(row(99, at=-500, people=OURS))
    assert [one["id"] for one in mt.next_runs(rows, NOW)] == [0, 1, 2, 3, 4]


def test_a_template_with_a_stranger_placeholder_is_refused_in_words():
    with pytest.raises(SettingError, match="nope"):
        coerce_value("marathon_live_template", "{member} {nope}")
    assert (
        coerce_value("marathon_live_template", "{member} is on {game}") == "{member} is on {game}"
    )


def test_the_shipped_words_are_the_registrys_defaults():
    assert MARATHON_DEFAULTS["marathon_mode"] == "shadow"
    assert MARATHON_DEFAULTS["marathon_ping_minutes"] == 15
    assert MARATHON_DEFAULTS["marathon_live_pings"] is False


def test_only_moves_that_change_something_are_drawn():
    active = mt.card_moves({"active": 1, "board_message_id": None}, has_unmatched=False)
    assert mt.PAUSE_MOVE in active and mt.RESUME_MOVE not in active
    assert mt.BOARD_POST_MOVE in active and mt.PAIR_MOVE not in active
    paused = mt.card_moves({"active": 0, "board_message_id": 5}, has_unmatched=True)
    assert mt.RESUME_MOVE in paused and mt.READ_MOVE not in paused
    assert mt.BOARD_REFRESH_MOVE in paused and mt.PAIR_MOVE in paused
    assert mt.ADD_MOVE not in mt.root_moves(staff=False)


# --- staff holds (marathon-next-event §G) ---------------------------------------------------


def test_a_run_staff_marked_live_is_never_closed_by_a_title_hit_on_another_run():
    rows = [row(1, at=-60, state=mt.LIVE, live_because=mt.BY_STAFF), row(2, at=0)]
    changes = mt.advance(rows, NOW, hit=rows[1], watching=True, grace_minutes=90)
    assert moves(changes) == [(2, mt.LIVE, mt.BY_TITLE, False)]


def test_a_run_staff_marked_upcoming_is_not_skipped_by_a_later_hit_or_a_later_start():
    held = row(1, at=-30, length=120, live_because=mt.BY_STAFF)
    rows = [held, row(2, at=-5)]
    assert moves(mt.advance(rows, NOW, hit=rows[1], watching=True, grace_minutes=90)) == [
        (2, mt.LIVE, mt.BY_TITLE, False)
    ]
    assert (1, mt.DONE, mt.BY_SCHEDULE, True) not in moves(
        mt.advance(rows, NOW, watching=False, grace_minutes=90)
    )


def test_a_held_run_still_ends_on_the_clock():
    rows = [row(1, at=-300, length=60, state=mt.LIVE, live_because=mt.BY_STAFF)]
    assert moves(mt.advance(rows, NOW, watching=True, grace_minutes=90)) == [
        (1, mt.DONE, mt.BY_SCHEDULE, False)
    ]


def test_the_run_moves_are_only_the_ones_that_change_something():
    ours = row(1, at=30, people=OURS)
    assert mt.run_moves(ours)[:3] == (mt.SHOUT_MOVE, mt.MARK_LIVE_MOVE, mt.MARK_DONE_MOVE)
    done = row(2, at=-300, state=mt.DONE)
    assert mt.run_moves(done) == (mt.MARK_LIVE_MOVE, mt.MARK_UPCOMING_MOVE, mt.BACK_MOVE)
    live = row(3, at=-10, state=mt.LIVE, shout_message_id=5, people=OURS)
    assert mt.run_moves(live) == (mt.MARK_DONE_MOVE, mt.BACK_MOVE)
    assert mt.run_moves(row(4, at=0, state=mt.DROPPED)) == (mt.BACK_MOVE,)


# --- the next GDQ event ---------------------------------------------------------------------

EVENT = {
    "id": 75,
    "short": "SGDQ2027",
    "name": "Summer Games  Done Quick 2027",
    "datetime": "2027-06-27T12:30:00-04:00",
}


def over(**extra):
    return marathon(**{"source": "gdq", "starts_at": iso(-900), "ends_at": iso(-60), **extra})


def test_a_suggestion_is_wanted_once_for_an_over_gdq_marathon_with_no_record():
    assert mt.wants_suggestion(over(), NOW)
    assert not mt.wants_suggestion(over(suggested_next=json.dumps(mt.none_record(NOW))), NOW)
    assert not mt.wants_suggestion(over(source="horaro"), NOW)
    assert not mt.wants_suggestion(over(active=0), NOW)
    assert not mt.wants_suggestion(marathon(source="gdq"), NOW)
    assert not mt.wants_suggestion(marathon(source="gdq", starts_at=None, ends_at=None), NOW)


def test_a_record_reads_open_then_dismissed_or_added_and_a_none_record_is_none():
    record = mt.suggestion_record(EVENT, NOW)
    assert record["name"] == "Summer Games Done Quick 2027"
    assert record["url"] == "https://tracker.gamesdonequick.com/tracker/event/75"
    assert record["datetime"] == "2027-06-27T16:30:00+00:00"
    assert mt.next_state(record) == mt.NEXT_OPEN
    assert mt.next_state(record | {"dismissed_at": iso(0)}) == mt.NEXT_DISMISSED
    assert mt.next_state(record | {"added_marathon_id": 4}) == mt.NEXT_ADDED
    assert mt.next_state(mt.none_record(NOW)) == mt.NEXT_NONE
    assert mt.next_state(None) is None
    assert mt.suggestion_of({"suggested_next": json.dumps(record)}) == record
    assert mt.suggestion_of({"suggested_next": "not json"}) is None


def test_every_next_word_fills_and_the_date_is_a_discord_stamp():
    record = mt.suggestion_record(EVENT, NOW)
    fields = mt.next_fields(M, record)
    for key in ("marathon_next_template", "marathon_next_added_template"):
        said = mt.render(WORDS[key], WORDS[key], **fields)
        assert said.fell_back is False and "{" not in said.text
    assert "**Summer Games Done Quick 2027**" in mt.render(
        WORDS["marathon_next_template"], "", **fields
    ).text
    assert fields["when"].endswith(":D>") and fields["relative"].endswith(":R>")
    assert mt.render(WORDS["marathon_next_none_template"], "", **fields).text.startswith(
        "AGDQ 2027 is over"
    )


def test_the_next_moves_offer_add_and_dismiss_only_while_the_suggestion_is_open():
    record = mt.suggestion_record(EVENT, NOW)
    assert mt.next_moves(record, over=True) == (
        mt.ADD_NEXT_MOVE,
        mt.DISMISS_NEXT_MOVE,
        mt.LOOK_AGAIN_MOVE,
        mt.BACK_MOVE,
    )
    dismissed = record | {"dismissed_at": iso(0)}
    assert mt.next_moves(dismissed, over=True) == (mt.LOOK_AGAIN_MOVE, mt.BACK_MOVE)
    assert mt.next_moves(None, over=False) == (mt.BACK_MOVE,)
    card = mt.card_moves({"active": 1}, has_unmatched=False, has_next=True)
    assert mt.NEXT_MOVE in card and mt.POLL_MOVE in card
    assert mt.NEXT_MOVE not in mt.card_moves({"active": 1}, has_unmatched=False)
