import json
from datetime import UTC, datetime, timedelta

from black_bloc import marathon as mt
from black_bloc import marathon_host_highlights as mhh
from black_bloc import marathon_overlay as overlay
from black_bloc import marathon_schedule_page as page
from black_bloc import marathon_viewer as mv
from black_bloc.marathon_sources import GDQ, GDQ_HOTFIX

NOW = datetime(2026, 10, 3, 17, 0, tzinfo=UTC)
ZONE = "America/Phoenix"
DAX = 501
CASEY = 502
MARKS = (1440, 120, 15)
BECAUSE = {mt.BY_STAFF: "staff", mt.BY_BOTH: "the stream's title and Twitch category"}


def iso(minutes):
    return (NOW + timedelta(minutes=minutes)).isoformat()


def person(name, part="runner", login=None, **extra):
    return {"name": name, "login": login, "part": part, "user_id": None} | extra


def run(ident, at, length=60, *, state=mt.UPCOMING, sheet=None, people=(), **extra):
    plan = at if sheet is None else sheet
    return {
        "id": ident,
        "order_no": ident,
        "game": f"Game {ident}",
        "category": "Any%",
        "state": state,
        "scheduled_at": iso(at),
        "ends_at": iso(at + length),
        "sheet_at": iso(plan),
        "sheet_ends_at": iso(plan + length),
        "run_seconds": length * 60,
        "live_because": None,
        "actual_started_at": None,
        "actual_ended_at": None,
        "shout_message_id": None,
        "reminders_sent": "[]",
        "people": json.dumps(list(people)),
        **extra,
    }


def marathon(source=GDQ_HOTFIX, **extra):
    return {
        "id": 9,
        "name": "GDQueer",
        "source": source,
        "source_ref": "gdqueer/2026-10-03",
        "schedule_url": "https://gamesdonequick.com/hotfix/schedule",
        "last_fetched_at": iso(-5),
        "overlay_sheet": None,
        mhh.COLUMN: None,
        **extra,
    }


def with_overlay(row):
    state = {"label": "Games Done Queer", "url": "https://docs.example/sheet", "applied": True}
    return row | {"overlay_sheet": overlay.dump(state)}


def read(row, runs, **extra):
    wanted = {"now": NOW, "tz_name": ZONE, "writes": True} | extra
    return page.payload(row, runs, **wanted)


def tags(found):
    return {one["id"]: one["from"] for one in found["rows"]}


# --- the kind of marathon and where its times come from --------------------------------------


def test_a_tracker_marathon_is_read_only_and_every_time_is_the_trackers():
    found = read(marathon(GDQ), [run(1, 30), run(2, 100)])
    assert (found["kind"], found["editable"], found["times_from"]) == ("tracker", False, "tracker")
    assert found["times_from_word"] == "the tracker"
    assert tags(found) == {1: "tracker", 2: "tracker"}
    assert [one["plan_from"] for one in found["rows"]] == ["tracker", "tracker"]
    assert found["days"][0]["drift_minutes"] is None
    assert found["days"][0]["upcoming"] == 2


def test_a_tracker_run_seen_on_stream_shows_what_happened_against_the_trackers_time():
    rows = [run(1, 0, state=mt.LIVE, actual_started_at=iso(6), live_because=mt.BY_BOTH)]
    found = read(marathon(GDQ), rows)
    row = found["rows"][0]
    assert (row["from"], row["off_plan_minutes"]) == ("stream", 6)
    assert row["start_at"] == page._iso(NOW + timedelta(minutes=6))
    assert row["plan_at"] == page._iso(NOW)


def test_a_hotfix_marathon_on_the_buffer_clock_is_tagged_the_source_sheet():
    found = read(marathon(), [run(1, 30), run(2, 97)])
    assert (found["kind"], found["editable"], found["times_from"]) == (
        "clock_kept",
        False,
        "source",
    )
    assert tags(found) == {1: "source", 2: "source"}
    assert found["days"][0]["drift_minutes"] == 0


def test_a_hotfix_marathon_with_the_organisers_sheet_applied_is_tagged_organisers():
    found = read(with_overlay(marathon()), [run(1, 30), run(2, 100)])
    assert found["times_from"] == "organisers"
    assert found["times_from_word"] == "the organisers' sheet"
    assert tags(found) == {1: "organisers", 2: "organisers"}


def test_a_run_seen_on_stream_is_tagged_stream_and_the_runs_after_it_follow():
    rows = [
        run(1, -60, state=mt.DONE),
        run(2, 8, sheet=0, state=mt.LIVE, actual_started_at=iso(8), live_because=mt.BY_CATEGORY),
        run(3, 78, sheet=70),
        run(4, 148, sheet=140),
    ]
    found = read(with_overlay(marathon()), rows)
    assert tags(found) == {1: "organisers", 2: "stream", 3: "follows", 4: "follows"}
    assert [one["off_plan_minutes"] for one in found["rows"]] == [0, 8, 8, 8]
    assert (found["days"][0]["drift_minutes"], found["days"][0]["drift_run_id"]) == (8, 3)


def test_a_run_started_by_staff_reads_differently_from_one_seen_on_stream():
    rows = [run(1, 3, sheet=0, state=mt.LIVE, actual_started_at=iso(3), live_because=mt.BY_STAFF)]
    assert tags(read(marathon(), rows)) == {1: "started"}


def test_a_time_off_the_sheet_with_nothing_before_it_started_is_held_not_follows():
    rows = [run(1, 12, sheet=0, state=mt.DONE), run(2, 70)]
    assert tags(read(marathon(), rows)) == {1: "held", 2: "source"}


def test_a_run_whose_earlier_neighbour_only_has_a_real_end_still_follows():
    rows = [run(1, 0, state=mt.DONE, actual_ended_at=iso(70)), run(2, 77, sheet=67)]
    assert tags(read(marathon(), rows)) == {1: "source", 2: "follows"}


def test_a_dropped_run_has_no_time_and_no_tag_and_is_not_counted():
    rows = [run(1, 30), run(2, 100, state=mt.DROPPED), run(3, 170)]
    found = read(marathon(), rows)
    dropped = found["rows"][1]
    assert (dropped["start_at"], dropped["ends_at"], dropped["from"]) == (None, None, None)
    assert (dropped["state_word"], dropped["off_plan_minutes"]) == ("skipped", None)
    assert found["days"][0]["runs"] == 2


def test_live_and_done_rows_carry_the_contracts_words_and_their_real_times():
    rows = [
        run(1, -70, state=mt.DONE, actual_started_at=iso(-70), actual_ended_at=iso(-12)),
        run(2, -5, state=mt.LIVE, actual_started_at=iso(-5)),
        run(3, 62, sheet=60),
    ]
    found = read(marathon(), rows)
    assert [one["state_word"] for one in found["rows"]] == ["done", "live", "upcoming"]
    assert found["rows"][0]["ends_at"] == page._iso(NOW - timedelta(minutes=12))
    assert [one["next_up"] for one in found["rows"]] == [False, False, True]
    assert found["today"] == found["days"][0]["key"]


# --- what the caller may press ---------------------------------------------------------------


def test_start_and_finish_follow_the_existing_mark_rules_and_every_other_flag_is_false():
    rows = [
        run(1, -120, state=mt.DONE),
        run(2, -5, state=mt.LIVE),
        run(3, 60),
        run(4, 130, state=mt.DROPPED),
    ]
    found = read(marathon(), rows)
    cans = [one["can"] for one in found["rows"]]
    assert [(one["start"], one["finish"]) for one in cans] == [
        (True, False),
        (False, True),
        (True, True),
        (False, False),
    ]
    assert not any(one[key] for one in cans for key in ("set_start", "estimate", "skip", "restore"))
    assert not any(day["can_shift"] or day["can_reset"] for day in found["days"])
    assert found["undo"] == {"available": False, "text": None}


def test_a_caller_who_may_not_write_and_an_archived_marathon_get_no_moves():
    rows = [run(1, -5, state=mt.LIVE), run(2, 60, people=[person("Dax", user_id=DAX)])]
    for found in (
        read(marathon(), rows, writes=False),
        read(marathon(), rows, archived=True, reminds_runs=True, marks=MARKS, ping_mark=15),
    ):
        assert not any(one["can"]["start"] or one["can"]["finish"] for one in found["rows"])
    archived = read(marathon(), rows, archived=True, reminds_runs=True, marks=MARKS, ping_mark=15)
    assert archived["marathon"]["archived"] is True
    assert archived["marathon"]["phase"] == "archived"
    assert archived["marathon"]["next_read_at"] is None
    assert archived["next_posts"] == []


# --- people and their links ------------------------------------------------------------------


def test_a_baf_runner_and_a_baf_host_are_marked_and_a_commentator_who_does_not_count_is_not():
    people = [
        person("The_Mathcat", user_id=DAX),
        person("champrul", "host", user_id=CASEY),
        person("ToastedKat", "commentator", user_id=777, counts=False),
        person("Stranger", "commentator"),
    ]
    found = read(marathon(), [run(1, 30, people=people)], name_of=lambda one: f"member {one}")
    row = found["rows"][0]
    assert [one["baf"] for one in row["people"]] == [True, True, False, False]
    assert row["ours"] is True
    assert row["people"][0]["member_name"] == f"member {DAX}"
    assert row["people"][0]["user_id"] == str(DAX)
    assert row["people"][3]["member_name"] is None
    assert found["days"][0]["baf"] == 1


def test_a_run_with_only_a_commentator_who_does_not_count_is_not_ours():
    people = [person("ToastedKat", "commentator", user_id=777, counts=False)]
    assert read(marathon(), [run(1, 30, people=people)])["rows"][0]["ours"] is False


def test_the_members_own_links_win_over_the_schedules_and_the_host_table_is_last():
    twitch = {DAX: "daxlive", CASEY: "caseyfast"}
    youtube = {CASEY: {"handle": "@caseyfast", "channel_id": "UC" + "a" * 22}}
    people = [
        person("The_Mathcat", login="the_mathcat", user_id=DAX),
        person("champrul", "host", login="champrul_tv", login_from=mv.FROM_VIEWER, user_id=CASEY),
        person("Starwindx9", login="starwindx9"),
        person("Quacksilver", "host", login="quacksilverplays", login_from=mv.FROM_VIEWER),
        person("Nobody", "host"),
    ]
    found = read(marathon(), [run(1, 30, people=people)], twitch=twitch, youtube=youtube)
    got = found["rows"][0]["people"]
    assert (got[0]["twitch_url"], got[0]["twitch_from"]) == (
        "https://www.twitch.tv/daxlive",
        "member",
    )
    assert (got[1]["twitch_from"], got[1]["youtube_from"], got[1]["link_from"]) == (
        "member",
        "member",
        "member",
    )
    assert got[1]["youtube_url"] == "https://www.youtube.com/@caseyfast"
    assert (got[2]["twitch_url"], got[2]["twitch_from"]) == (
        "https://www.twitch.tv/starwindx9",
        "schedule",
    )
    assert (got[3]["twitch_url"], got[3]["twitch_from"]) == (
        "https://www.twitch.tv/quacksilverplays",
        "hosts",
    )
    assert [got[4][key] for key in ("twitch_url", "youtube_url", "link_from")] == [None] * 3


def test_a_youtube_only_member_links_by_channel_id_when_there_is_no_handle():
    youtube = {DAX: {"handle": None, "channel_id": "UC" + "b" * 22}}
    people = [person("The_Mathcat", user_id=DAX)]
    got = read(marathon(), [run(1, 30, people=people)], youtube=youtube)["rows"][0]["people"][0]
    assert got["youtube_url"] == "https://www.youtube.com/channel/UC" + "b" * 22
    assert (got["twitch_url"], got["link_from"]) == (None, "member")


def test_only_real_twitch_and_youtube_addresses_are_ever_emitted():
    assert page.twitch_url("http://evil.example/x") is None
    assert page.twitch_url("a") is None
    assert page.twitch_url("ok_login") == "https://www.twitch.tv/ok_login"
    assert page.twitch_url("name?redirect=1") is None
    assert page.youtube_url({"handle": "@x/../y", "channel_id": "not-an-id"}) is None
    assert page.youtube_url({"handle": "caseyfast", "channel_id": ""}) == (
        "https://www.youtube.com/@caseyfast"
    )
    people = [person("Ramseyfox", login="http://ramseyfox.example/live")]
    got = read(marathon(), [run(1, 30, people=people)])["rows"][0]["people"][0]
    assert (got["twitch_url"], got["link_from"]) == (None, None)


def test_a_staff_fixed_twitch_name_is_not_read_as_the_schedules():
    fixed = person("The_Mathcat", login="fixedbystaff", sheet_login=None, user_id=DAX)
    kept = person("Other", login="fixedbystaff", sheet_login="fromsheet")
    got = read(marathon(), [run(1, 30, people=[fixed, kept])])["rows"][0]["people"]
    assert got[0]["twitch_url"] is None
    assert got[1]["twitch_url"] == "https://www.twitch.tv/fromsheet"


def test_the_header_carries_where_it_airs_and_when_it_is_read():
    found = read(
        marathon(),
        [run(1, 30)],
        channel_login="gdqhotfix",
        next_read_at=iso(10),
        phase="live",
        phase_word="on now",
        refresh_seconds=45,
        setup_minutes=7,
    )
    head = found["marathon"]
    assert head["watch_url"] == "https://www.twitch.tv/gdqhotfix"
    assert head["source_word"] == "GDQ Hotfix"
    assert head["next_read_at"] == page._iso(NOW + timedelta(minutes=10))
    assert head["last_fetched_at"] == page._iso(NOW - timedelta(minutes=5))
    assert (head["phase"], head["phase_word"], head["archived"]) == ("live", "on now", False)
    assert (found["refresh_seconds"], found["setup_minutes"]) == (45, 7)
    assert (found["moves_by"], found["timezone"]) == ("marks", ZONE)
    assert read(marathon(), [run(1, 30)])["marathon"]["watch_url"] is None


# --- days ------------------------------------------------------------------------------------


def test_two_shows_a_night_apart_are_two_days_and_today_is_the_one_with_work_left():
    rows = [run(1, -1500, state=mt.DONE), run(2, -1440, state=mt.DONE), run(3, 30), run(4, 100)]
    found = read(marathon(), rows)
    assert [day["runs"] for day in found["days"]] == [2, 2]
    assert [day["label"] for day in found["days"]] == ["Fri 2 Oct", "Sat 3 Oct"]
    assert found["today"] == found["days"][1]["key"]
    assert {one["day"] for one in found["rows"][2:]} == {found["days"][1]["key"]}
    assert found["days"][0]["drift_minutes"] is None


def test_a_marathon_that_never_stops_is_split_by_calendar_date():
    rows = [run(ident, (ident - 1) * 600, 600) for ident in range(1, 7)]
    found = read(marathon(GDQ), rows)
    assert len(found["days"]) >= 3
    assert len({day["key"] for day in found["days"]}) == len(found["days"])


def test_a_marathon_with_no_runs_is_an_empty_sheet_not_an_error():
    found = read(marathon(), [])
    assert (found["days"], found["rows"], found["today"]) == ([], [], None)


# --- what the bot posts next -----------------------------------------------------------------


def posts(row, runs, **extra):
    wanted = {"marks": MARKS, "ping_mark": 15, "stale_minutes": 10, "reminds_runs": True}
    return read(row, runs, **(wanted | extra))["next_posts"]


def test_an_upcoming_baf_run_lists_each_mark_still_to_fire_with_its_moment():
    rows = [run(1, 300, people=[person("The_Mathcat", user_id=DAX)]), run(2, 400)]
    found = posts(marathon(), rows)
    assert [(one["kind"], one["run_id"], one["minutes"]) for one in found] == [
        ("run", 1, 120),
        ("run", 1, 15),
    ]
    assert found[0]["at"] == page._iso(NOW + timedelta(minutes=180))
    assert found[0]["text"] == "Heads-up: **The_Mathcat** runs **Game 1** in 2 hours."
    assert found[1]["text"].endswith("in 15 minutes.")
    assert not any(one["passed"] for one in found)


def test_a_mark_already_sent_is_not_listed_and_a_stale_one_is_never_promised():
    people = [person("The_Mathcat", user_id=DAX)]
    sent = run(1, 300, people=people, reminders_sent="[120]")
    assert [one["minutes"] for one in posts(marathon(), [sent])] == [15]
    stored = run(
        1,
        300,
        people=people,
        reminders_sent="[120, 15]",
        reminder_posts=json.dumps({"15": {"posted": True}}),
    )
    assert posts(marathon(), [stored]) == []


def test_a_mark_whose_moment_has_come_is_due_and_marked_passed():
    rows = [run(1, 12, people=[person("The_Mathcat", user_id=DAX)])]
    found = posts(marathon(), rows, marks=(15,))
    assert [(one["minutes"], one["passed"]) for one in found] == [(15, True)]


def test_the_ping_mark_carries_the_marathon_role_when_the_verdict_says_so():
    rows = [run(1, 300, people=[person("The_Mathcat", user_id=DAX)])]
    found = posts(marathon(), rows, run_role=lambda row: True)
    assert [(one["minutes"], one["role"]) for one in found] == [(120, False), (15, True)]
    assert not any(one["role"] for one in posts(marathon(), rows))


def test_nothing_is_promised_for_a_marathon_the_tick_does_not_remind():
    rows = [run(1, 300, people=[person("The_Mathcat", user_id=DAX)])]
    assert posts(marathon(), rows, reminds_runs=False) == []


def test_a_live_baf_run_whose_shoutout_is_up_says_so_and_lists_no_mark():
    rows = [
        run(1, -5, state=mt.LIVE, shout_message_id=99, people=[person("The_Mathcat", user_id=DAX)])
    ]
    found = posts(marathon(), rows)
    assert [(one["kind"], one["at"]) for one in found] == [("live", None)]


def host(name="champrul", user_id=CASEY):
    return person(name, "host", user_id=user_id)


def test_a_baf_host_block_is_one_set_of_marks_measured_from_its_first_run():
    rows = [run(1, 300, people=[host()]), run(2, 370, people=[host()]), run(3, 440)]
    found = posts(marathon(), rows, reminds_runs=False, reminds_hosts=True)
    assert [(one["kind"], one["run_id"], one["minutes"]) for one in found] == [
        ("host", 1, 120),
        ("host", 1, 15),
    ]
    assert found[0]["text"] == "Heads-up: **champrul** hosts 2 runs from **Game 1** in 2 hours."


def test_a_host_blocks_record_decides_which_marks_are_left_and_who_carries_the_role():
    rows = [run(1, 300, people=[host()]), run(2, 370, people=[person("x", "host")])]
    record = {
        "start_run_id": 1,
        "runs": [1],
        "marks": [1440, 120],
        "hosts": [{"user_id": CASEY, "name": "champrul"}],
        "reminders": {"120": {"posted": True}},
    }
    row = marathon(**{mhh.COLUMN: mhh.dump([record])})
    found = posts(row, rows, reminds_runs=False, reminds_hosts=True, block_role=lambda block: True)
    assert [(one["minutes"], one["role"]) for one in found] == [(15, True)]
    quiet = posts(
        row, rows, reminds_runs=False, reminds_hosts=True, block_speaks=lambda block: False
    )
    assert quiet == []


def test_a_host_block_that_has_begun_promises_nothing_more():
    rows = [run(1, -5, state=mt.LIVE, people=[host()]), run(2, 60, people=[host()])]
    assert posts(marathon(), rows, reminds_runs=False, reminds_hosts=True) == []


def test_the_heads_up_minutes_are_the_nearest_mark():
    assert read(marathon(), [run(1, 30)], marks=MARKS, ping_mark=15)["heads_up_minutes"] == 15
    assert read(marathon(), [run(1, 30)], ping_mark=20)["heads_up_minutes"] == 20


def test_lead_words_read_hours_as_hours():
    assert [page.lead_words(one) for one in (1440, 120, 60, 15, 1, 90)] == [
        "24 hours",
        "2 hours",
        "1 hour",
        "15 minutes",
        "1 minute",
        "90 minutes",
    ]


# --- moves -----------------------------------------------------------------------------------


def action(ident, kind, details, actor=None, minutes=-10):
    return {"id": ident, "at": iso(minutes), "kind": kind, "actor_id": actor, "details": details}


def moves(actions, **extra):
    wanted = {"actions": actions, "because_words": BECAUSE, "name_of": lambda one: f"m{one}"}
    return read(marathon(), [run(1, 30)], **(wanted | extra))["moves"]


def test_a_retime_reads_as_a_sentence_with_its_moments_as_tokens():
    first = {"run_id": 3, "game": "Bombun", "from": iso(60), "to": iso(68)}
    found = moves([action(5, "marathon.retimed", {"runs": 4, "because": "stream", "first": first})])
    assert found[0]["text"] == (
        "4 runs re-timed after the stream showed a run starting: **Bombun** moved from "
        f"{{{{at:{page._moment(iso(60))}}}}} to {{{{at:{page._moment(iso(68))}}}}}"
    )
    assert (found[0]["kind"], found[0]["by_name"], found[0]["undone"]) == ("retimed", None, False)


def test_staff_moves_name_the_staffer_only_for_a_caller_who_may_see_names():
    rows = [
        action(9, "web.marathon.run_live", {"game": "Spyro", "because": mt.BY_STAFF}, actor=42),
        action(8, "marathon.run_done", {"game": "Hamtaro", "because": mt.BY_BOTH}),
        action(7, "marathon.run_reset", {"game": "Kirby"}, actor=42),
    ]
    found = moves(rows)
    assert [one["text"] for one in found] == [
        "**Spyro** is on now, by staff",
        "**Hamtaro** is done, by the stream's title and Twitch category",
        "**Kirby** was put back to coming up",
    ]
    assert [(one["by_id"], one["by_name"]) for one in found] == [
        ("42", "m42"),
        (None, None),
        ("42", "m42"),
    ]
    hidden = moves(rows, names=False)
    assert [(one["by_id"], one["by_name"]) for one in hidden] == [(None, None)] * 3


def test_reads_overlays_and_sheet_times_have_words_and_unknown_kinds_are_left_out():
    rows = [
        action(6, "marathon.schedule_changed", {"added": 1, "moved": 2, "dropped": 0}),
        action(
            5, "marathon.overlay_applied", {"label": "GDQueer Oct 3-4", "matched": 24, "runs": 24}
        ),
        action(4, "web.marathon.sheet_times", {"runs": 3}, actor=42),
        action(3, "marathon.member_run_moved", {"game": "Dread", "from": iso(0), "to": iso(9)}),
        action(2, "marathon.fetched", {"runs": 24}),
        action(1, "marathon.member_run_moved", {"game": "No times"}),
    ]
    found = moves(rows)
    assert [one["id"] for one in found] == [6, 5, 4, 3]
    assert found[0]["text"] == "The source changed at a read: 1 added, 2 moved, 0 dropped"
    assert found[1]["text"].startswith("The organisers' sheet **GDQueer Oct 3-4** was laid over")
    assert found[2]["text"] == "3 runs put back on the sheet's times"
    assert "{{at:" in found[3]["text"]


def test_moves_are_capped():
    rows = [action(i, "marathon.run_reset", {"game": "G"}) for i in range(100, 0, -1)]
    found = moves(rows)
    assert len(found) == page.MOVES_LIMIT
    assert found[0]["id"] == 100


def test_the_move_kinds_asked_of_the_log_all_have_words():
    for kind in page.MOVE_KINDS:
        assert kind in page.MOVE_WORDS
