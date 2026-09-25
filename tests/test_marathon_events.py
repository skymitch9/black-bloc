from black_bloc import marathon_events as me


def test_a_mode_word_is_read_and_anything_else_is_not():
    assert me.clean_mode(" Both ") == "both"
    assert me.clean_mode("sometimes") is None
    assert me.mode_of({"event_mode": None}) == "none"


def test_the_two_halves_of_a_mode():
    assert [me.makes_marathon_event(one) for one in me.MODES] == [False, True, False, True]
    assert [me.makes_run_events(one) for one in me.MODES] == [False, False, True, True]
    assert me.with_marathon_event("runs", True) == "both"
    assert me.with_marathon_event("both", False) == "runs"
    assert me.with_marathon_event("none", True) == "marathon"


def test_waiting_is_the_mode_asking_for_an_event_it_does_not_have_yet():
    assert me.waiting({"event_mode": "marathon", "event_id": None})
    assert not me.waiting({"event_mode": "marathon", "event_id": 4})
    assert not me.waiting({"event_mode": "runs", "event_id": None})


def test_the_run_fields_join_every_member_of_ours_on_the_run():
    row = {
        "game": "Celeste",
        "category": "Any%",
        "people": [
            {"name": "Sky", "login": "skyruns", "part": "runner", "user_id": 1},
            {"name": "Moth", "login": None, "part": "runner", "user_id": 2},
            {"name": "Nobody", "login": None, "part": "runner", "user_id": None},
        ],
    }
    fields = me.run_event_fields(row, {"name": "AGDQ 2027"}, {1: "Sky Here"})
    assert fields == {
        "member": "Sky Here & Moth",
        "game": "Celeste",
        "category": "Any%",
        "marathon": "AGDQ 2027",
    }
    assert me.run_logins(row) == ["skyruns"]


def test_a_run_offers_make_it_now_or_unlink_never_both():
    ours = {"people": [{"name": "Sky", "part": "runner", "user_id": 1}], "state": "upcoming"}
    assert me.run_event_moves(ours | {"event_id": None, "scheduled_at": "2027"}) == (
        me.MAKE_RUN_EVENT_MOVE,
    )
    assert me.run_event_moves(ours | {"event_id": 5}) == (me.UNLINK_RUN_EVENT_MOVE,)
    assert me.run_event_moves({"people": [], "state": "upcoming", "event_id": None}) == ()
