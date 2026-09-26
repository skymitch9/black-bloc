from datetime import UTC, datetime, timedelta

from black_bloc import marathon_spotlight as ms

NOW = datetime(2027, 1, 4, 18, 0, tzinfo=UTC)


def at(minutes):
    return (NOW + timedelta(minutes=minutes)).isoformat()


def a_marathon(start=-60, end=240, **extra):
    return {
        "id": 7,
        "name": "AGDQ 2027",
        "starts_at": at(start),
        "ends_at": at(end),
        "active": 1,
        "spotlight_id": 3,
        "spotlight_mode": None,
        **extra,
    }


def a_row(**extra):
    return {
        "id": 3,
        "twitch_login": "rpglimitbreak",
        "spotlight": 0,
        "expires_at": None,
        "marathons": 1,
        "spotlit_by_marathon": None,
        **extra,
    }


def planned(row=None, marathon=None, *, enabled=True, lead=15, now=NOW):
    return ms.plan(
        a_row() if row is None else row,
        a_marathon() if marathon is None else marathon,
        now,
        enabled=enabled,
        lead_minutes=lead,
    )


def test_a_blank_or_unknown_mode_follows_and_only_off_is_off():
    assert ms.mode_of({"spotlight_mode": None}) == ms.FOLLOW
    assert ms.mode_of({"spotlight_mode": "sometimes"}) == ms.FOLLOW
    assert ms.mode_of({"spotlight_mode": "OFF"}) == ms.OFF
    assert ms.mode_of({}) == ms.FOLLOW


def test_clean_mode_reads_the_words_and_the_booleans_and_refuses_the_rest():
    assert ms.clean_mode("follow") == ms.FOLLOW and ms.clean_mode("on") == ms.FOLLOW
    assert ms.clean_mode(True) == ms.FOLLOW and ms.clean_mode(False) == ms.OFF
    assert ms.clean_mode("off") == ms.OFF
    assert ms.clean_mode("often") is None and ms.clean_mode(None) is None


def test_a_span_that_holds_now_spotlights_the_row_until_its_end():
    assert planned() == {"spotlight": 1, "expires_at": at(240), "spotlit_by_marathon": 7}


def test_a_span_starting_inside_the_lead_spotlights_it_and_one_further_off_does_not():
    assert planned(marathon=a_marathon(start=10, end=300))["spotlight"] == 1
    assert planned(marathon=a_marathon(start=20, end=300)) is None
    assert planned(marathon=a_marathon(start=20, end=300), lead=30)["spotlight"] == 1


def test_a_span_that_is_over_or_has_no_dates_leaves_the_row():
    assert planned(marathon=a_marathon(start=-300, end=-10)) is None
    assert planned(marathon=a_marathon(start=-300, end=0)) is None
    assert planned(marathon={**a_marathon(), "starts_at": None, "ends_at": None}) is None


def test_a_marathon_with_only_a_start_spans_that_moment():
    lone = {**a_marathon(start=5), "ends_at": None}
    assert ms.span_of(lone) == (NOW + timedelta(minutes=5), NOW + timedelta(minutes=5))
    assert planned(marathon=lone)["expires_at"] == at(5)


def test_a_permanent_spotlight_is_never_touched():
    assert planned(row=a_row(spotlight=1, expires_at=None, twitch_login="gamesdonequick")) is None


def test_a_later_expiry_is_never_shortened_and_an_earlier_one_is_carried_to_the_end():
    assert planned(row=a_row(spotlight=1, expires_at=at(9999))) is None
    assert planned(row=a_row(spotlight=1, expires_at=at(240))) is None
    assert planned(row=a_row(spotlight=1, expires_at=at(30))) == {"expires_at": at(240)}


def test_an_unreadable_expiry_on_a_spotlit_row_is_left_alone():
    assert planned(row=a_row(spotlight=1, expires_at="someday")) is None


def test_a_staff_off_a_paused_marathon_an_opted_out_channel_and_the_key_off_all_leave_it():
    assert planned(marathon=a_marathon(spotlight_mode="off")) is None
    assert planned(marathon=a_marathon(active=0)) is None
    assert planned(row=a_row(marathons=0)) is None
    assert planned(enabled=False) is None
    assert ms.plan(None, a_marathon(), NOW, enabled=True, lead_minutes=15) is None


def test_the_lifted_fields_give_the_row_back_off_and_kept():
    assert ms.lifted_fields() == {"spotlight": 0, "expires_at": None, "spotlit_by_marathon": None}
    assert ms.held_by(a_row(spotlit_by_marathon=7)) == 7
    assert ms.held_by(a_row()) is None


def test_dimmed_during_names_only_the_following_marathons_in_reach():
    running = a_marathon()
    stopped = a_marathon(spotlight_mode="off", id=8)
    later = a_marathon(start=600, end=900, id=9)
    paused = a_marathon(active=0, id=10)
    found = ms.dimmed_during([running, stopped, later, paused], NOW, enabled=True, lead_minutes=15)
    assert [one["id"] for one in found] == [7]
    assert ms.dimmed_during([running], NOW, enabled=False, lead_minutes=15) == []


def test_a_seeded_marathon_login_starts_on_the_marathon_ping_default():
    assert ms.is_marathon_login("GamesDoneQuick") and ms.is_marathon_login("fastestfurs")
    assert not ms.is_marathon_login("someStreamer")
    assert ms.new_row_ping_mode("gamesdonequick", True, "events", "always") == "events"
    assert ms.new_row_ping_mode("gamesdonequick", False, "events", "always") == "always"
    assert ms.new_row_ping_mode("somestreamer", True, "events", "always") == "always"
    assert ms.new_row_ping_mode("gamesdonequick", True, "sometimes", "never") == "never"


def test_a_marathon_channel_is_a_seeded_login_or_a_row_with_a_marathon_window():
    assert ms.is_marathon_channel(a_row())
    assert not ms.is_marathon_channel(a_row(marathons=0))
    streamer = a_row(twitch_login="somestreamer")
    assert not ms.is_marathon_channel(streamer, [{"source": "staff"}])
    assert ms.is_marathon_channel(streamer, [{"source": "marathon"}])


def test_the_card_draws_the_one_switch_that_changes_something():
    assert ms.card_moves(a_marathon()) == (ms.OFF_MOVE,)
    assert ms.card_moves(a_marathon(spotlight_mode="off")) == (ms.FOLLOW_MOVE,)
    assert ms.card_moves(a_marathon(spotlight_id=None)) == ()
    assert ms.mode_line(a_marathon(spotlight_mode="off")).endswith("**off**")
