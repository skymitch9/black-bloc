from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from black_bloc import marathon as mt
from black_bloc import marathon_signals as sig
from black_bloc.marathon_sources import GDQ, GDQ_HOTFIX, retimes_itself

NOW = datetime(2026, 10, 3, 17, 0, tzinfo=UTC)


def iso(minutes):
    return (NOW + timedelta(minutes=minutes)).isoformat()


def row(ident, at, length=60, *, state=mt.UPCOMING, game=None, **extra):
    name = game or f"Game {ident}"
    return {
        "id": ident,
        "order_no": ident,
        "game": name,
        "display_name": name,
        "twitch_game": "",
        "state": state,
        "scheduled_at": iso(at),
        "ends_at": iso(at + length),
        "sheet_at": iso(at),
        "sheet_ends_at": iso(at + length),
        "run_seconds": length * 60,
        "live_because": None,
        "people": "[]",
        **extra,
    }


def looked(one, game_id=None, name=None):
    return one | {"twitch_game_id": game_id, "twitch_category": name, "twitch_looked_at": iso(-600)}


# --- the category ----------------------------------------------------------------------------


def test_a_run_whose_category_id_is_the_streams_is_a_direct_hit():
    rows = [looked(row(1, 0, game="Spyro Reignited Trilogy"), "1", "Spyro Reignited Trilogy")]
    found = sig.category_matches("1", "Spyro Reignited Trilogy", rows, NOW, retro="Retro")
    assert found == [sig.Match(rows[0], True)]


def test_a_looked_up_run_with_another_id_is_no_hit_even_when_the_names_overlap():
    rows = [looked(row(1, 0, game="Kirby's Dream Land"), "5", "Kirby's Dream Land")]
    assert sig.category_matches("6", "Kirby", rows, NOW, retro="Retro") == []


def test_before_a_lookup_the_names_decide_by_equality_or_containment():
    rows = [row(1, 0, game="Spyro Reignited Trilogy"), row(2, 68, game="Hamtaro: Ham-Hams Unite!")]
    found = sig.category_matches("", "spyro reignited trilogy", rows, NOW, retro="Retro")
    assert [one.row["id"] for one in found] == [1]
    found = sig.category_matches("", "Hamtaro", rows, NOW, retro="Retro")
    assert [one.row["id"] for one in found] == [2]


def test_retro_stands_only_for_runs_twitch_has_no_category_for():
    rows = [
        looked(row(1, 0, game="Bombun")),
        looked(row(2, 46, game="Kilaflow"), "77", "Kilaflow"),
        row(3, 96, game="Retro City Rampage"),
    ]
    found = sig.category_matches("27284", "retro", rows, NOW, retro="Retro")
    assert found == [sig.Match(rows[0], False)]


def test_the_retro_name_is_the_setting_whatever_its_capitals():
    rows = [looked(row(1, 0, game="Bombun"))]
    assert sig.category_matches("9", "Old Games", rows, NOW, retro="old games")
    assert not sig.category_matches("9", "Retro", rows, NOW, retro="old games")


def test_done_dropped_and_far_off_runs_are_never_the_category():
    rows = [
        looked(row(1, 0, state=mt.DONE), "1"),
        looked(row(2, 0, state=mt.DROPPED), "1"),
        looked(row(3, 13 * 60), "1"),
    ]
    assert sig.category_matches("1", "x", rows, NOW, retro="Retro") == []


# --- the decision ----------------------------------------------------------------------------


def test_title_and_category_on_one_run_is_certain():
    spyro = looked(row(1, 0), "1")
    verdict = sig.decide(spyro, [sig.Match(spyro, True)], NOW)
    assert (verdict.row, verdict.because, verdict.disagree) == (spyro, mt.BY_BOTH, False)


def test_title_only_and_category_only():
    spyro = row(1, 0)
    assert sig.decide(spyro, [], NOW).because == mt.BY_TITLE
    verdict = sig.decide(None, [sig.Match(spyro, True)], NOW)
    assert (verdict.row, verdict.because) == (spyro, mt.BY_CATEGORY)
    assert sig.decide(None, [], NOW) is None


def test_apart_a_direct_category_wins_and_the_title_wins_over_retro():
    spyro, hamtaro = row(1, 0), row(2, 68)
    verdict = sig.decide(spyro, [sig.Match(hamtaro, True)], NOW)
    assert (verdict.row, verdict.because, verdict.disagree) == (hamtaro, mt.BY_CATEGORY, True)
    assert (verdict.title_row, verdict.category_row) == (spyro, hamtaro)
    verdict = sig.decide(spyro, [sig.Match(hamtaro, False)], NOW)
    assert (verdict.row, verdict.because, verdict.disagree) == (spyro, mt.BY_TITLE, True)


def test_the_title_picks_among_several_runs_the_category_stands_for():
    first, second = looked(row(1, 0)), looked(row(2, 50))
    verdict = sig.decide(second, [sig.Match(first, False), sig.Match(second, False)], NOW)
    assert (verdict.row, verdict.because) == (second, mt.BY_BOTH)


def test_the_run_already_on_keeps_the_category_over_the_next_one_of_the_same_game():
    on = row(1, -50, state=mt.LIVE)
    later = row(2, 5)
    best = sig.best_match([sig.Match(on, True), sig.Match(later, True)], NOW)
    assert best.row is on


def test_a_run_live_by_the_clock_is_re_recorded_when_the_stream_confirms_it():
    on = row(1, -95, state=mt.LIVE, live_because=mt.BY_SCHEDULE)
    changes = mt.advance([on], NOW, hit=on, watching=True, grace_minutes=90, because=mt.BY_BOTH)
    assert changes == [mt.Change(on, mt.LIVE, mt.BY_BOTH, confirmed=True)]
    by_title = on | {"live_because": mt.BY_TITLE}
    assert (
        mt.advance(
            [by_title], NOW, hit=by_title, watching=True, grace_minutes=90, because=mt.BY_CATEGORY
        )
        == []
    )


# --- keeping the clock -----------------------------------------------------------------------


def test_a_run_seen_20_minutes_late_moves_every_later_run_of_its_day():
    rows = [row(1, 0, 68), row(2, 68, 52), row(3, 120, 15), row(4, 24 * 60, 23)]
    rows[0] |= {"state": mt.LIVE, "actual_started_at": iso(20)}
    found = {one.row["id"]: (one.starts_at, one.ends_at) for one in sig.retimed(rows)}
    assert found == {
        1: (iso(20), iso(88)),
        2: (iso(88), iso(140)),
        3: (iso(140), iso(155)),
    }


def test_a_run_staff_ended_early_pulls_the_next_ones_forward():
    rows = [row(1, 0, 60), row(2, 60, 30)]
    rows[0] |= {"actual_started_at": iso(0), "actual_ended_at": iso(45)}
    found = {one.row["id"]: (one.starts_at, one.ends_at) for one in sig.retimed(rows)}
    assert found == {1: (iso(0), iso(45)), 2: (iso(45), iso(75))}


def spaced(setup, *lengths, at=0):
    rows, cursor = [], at
    for ident, length in enumerate(lengths, start=1):
        rows.append(row(ident, cursor, length))
        cursor += length + setup
    return rows


def test_no_setup_buffer_re_times_exactly_as_before():
    rows = [row(1, 0, 68), row(2, 68, 52), row(3, 120, 15)]
    rows[0] |= {"state": mt.LIVE, "actual_started_at": iso(20)}
    assert sig.retimed(rows, 0) == sig.retimed(rows)
    assert [(one.starts_at, one.ends_at) for one in sig.retimed(rows, -3)] == [
        (iso(20), iso(88)),
        (iso(88), iso(140)),
        (iso(140), iso(155)),
    ]


def test_a_setup_buffer_is_added_before_each_run_after_the_one_seen_starting():
    rows = [*spaced(7, 68, 52, 15), row(4, 24 * 60, 23)]
    rows[0] |= {"state": mt.LIVE, "actual_started_at": iso(20)}
    found = {one.row["id"]: (one.starts_at, one.ends_at) for one in sig.retimed(rows, 7)}
    assert found == {
        1: (iso(20), iso(88)),
        2: (iso(95), iso(147)),
        3: (iso(154), iso(169)),
    }


def test_the_runs_before_the_one_seen_starting_and_the_done_ones_are_left_alone():
    rows = spaced(7, 60, 30, 40, 20)
    rows[0] |= {"state": mt.DONE}
    rows[1] |= {"state": mt.DONE, "actual_started_at": iso(70), "scheduled_at": iso(70)}
    rows[1] |= {"ends_at": iso(100)}
    rows[2] |= {"state": mt.LIVE, "actual_started_at": iso(110)}
    found = {one.row["id"]: (one.starts_at, one.ends_at) for one in sig.retimed(rows, 7)}
    assert found == {3: (iso(110), iso(150)), 4: (iso(157), iso(177))}


def test_a_run_live_or_done_by_the_clock_alone_stays_where_it_is():
    rows = spaced(0, 60, 30, 40)
    rows[0] |= {"state": mt.DONE, "actual_started_at": iso(0)}
    rows[1] |= {"state": mt.LIVE}
    found = {one.row["id"]: (one.starts_at, one.ends_at) for one in sig.retimed(rows, 7)}
    assert found == {3: (iso(97), iso(137))}
    rows[1] |= {"state": mt.UPCOMING}
    found = {one.row["id"]: (one.starts_at, one.ends_at) for one in sig.retimed(rows, 7)}
    assert found == {2: (iso(67), iso(97)), 3: (iso(104), iso(144))}
    alone = row(1, 0, 60, state=mt.DONE) | {"scheduled_at": iso(9), "ends_at": iso(69)}
    assert sig.retimed([alone, row(2, 60, 30)], 7) == []


def test_a_run_staff_ended_is_followed_by_the_setup_buffer():
    rows = spaced(7, 60, 30)
    rows[0] |= {"actual_started_at": iso(0), "actual_ended_at": iso(45)}
    found = {one.row["id"]: (one.starts_at, one.ends_at) for one in sig.retimed(rows, 7)}
    assert found == {1: (iso(0), iso(45)), 2: (iso(52), iso(82))}


def test_runs_a_setup_buffer_apart_are_one_chain_whatever_the_key_says_now():
    for sheet in (0, 7, 30):
        rows = [*spaced(sheet, 60, 30, 40), row(4, 24 * 60, 23)]
        assert [[one["id"] for one in chain] for chain in sig.chains(rows)] == [[1, 2, 3], [4]]
        rows[0] |= {"state": mt.LIVE, "actual_started_at": iso(5)}
        found = {one.row["id"]: one.starts_at for one in sig.retimed(rows, 10)}
        assert (found[2], found[3]) == (iso(75), iso(115))
        assert 4 not in found
    apart = [row(1, 0, 60), row(2, 60 + 32, 30)]
    assert len(sig.chains(apart)) == 2
    overlapping = [row(1, 0, 60), row(2, 58, 30)]
    assert len(sig.chains(overlapping)) == 2


def test_with_no_anchor_every_run_goes_back_to_the_sheet():
    moved = row(2, 68) | {"scheduled_at": iso(88), "ends_at": iso(148)}
    found = sig.retimed([row(1, 0, 68), moved])
    assert [(one.row["id"], one.starts_at, one.ends_at) for one in found] == [
        (2, iso(68), iso(128))
    ]


def test_runs_already_where_the_stream_puts_them_are_left_alone():
    rows = [row(1, 0, 68) | {"actual_started_at": iso(0)}, row(2, 68, 52)]
    assert sig.retimed(rows) == []


def test_a_retimed_count_and_the_way_back_to_the_sheet():
    live = row(1, 0, 68) | {"actual_started_at": iso(20), "scheduled_at": iso(20)}
    later = row(2, 68, 52) | {"scheduled_at": iso(88), "ends_at": iso(140)}
    assert sig.retimed_count([live, later]) == 2
    back = {one.row["id"]: (one.starts_at, one.ends_at) for one in sig.on_the_sheet([live, later])}
    assert back == {1: (iso(0), iso(68)), 2: (iso(68), iso(120))}


def test_the_hotfix_sheet_does_not_move_itself_and_the_gdq_tracker_does():
    assert retimes_itself(GDQ_HOTFIX) is False
    assert retimes_itself(GDQ) is True


def test_a_category_is_found_by_exact_name_first_then_by_a_search_with_the_same_name():
    spyro = row(1, 0, game="Spyro Reignited Trilogy")
    hamtaro = row(2, 68, game="Hamtaro: Ham-Hams Unite!")
    game = SimpleNamespace(id="1", name="Spyro Reignited Trilogy")
    near = SimpleNamespace(id="8", name="Hamtaro - Ham Hams Unite")
    wrong = SimpleNamespace(id="9", name="Hamtaro: Rainbow Rescue")
    assert sig.found_in(spyro, {"spyro reignited trilogy": game}, {}) is game
    searched = {"Hamtaro: Ham-Hams Unite!": [wrong, near]}
    assert sig.found_in(hamtaro, {}, searched) is near
    assert sig.found_in(hamtaro, {}, {"Hamtaro: Ham-Hams Unite!": [wrong]}) is None


def test_the_early_line_is_the_days_first_planned_start_whichever_run_is_asked_about():
    days = [[row(1, 0, 45), row(2, 45, 30)], [row(3, 24 * 60, 30)]]
    for one in days[0]:
        assert sig.day_line(one, days, 15) == NOW - timedelta(minutes=15)
    assert sig.day_line(days[1][0], days, 15) == NOW + timedelta(minutes=24 * 60 - 15)
    assert sig.day_line(days[0][1], days, 0) is None
    assert sig.day_line(row(9, 0), days, 15) is None


def test_the_early_line_is_gone_once_another_run_of_the_day_is_live_or_done():
    for state in (mt.LIVE, mt.DONE):
        days = [[row(1, 0, 45, state=state), row(2, 45, 30)]]
        assert sig.day_line(days[0][1], days, 15) is None
        assert sig.day_line(days[0][0], days, 15) == NOW - timedelta(minutes=15)


def early_opener(started, **extra):
    opener = row(1, 0, 45, state=mt.LIVE) | {"actual_started_at": iso(started)}
    return opener | {"live_because": mt.BY_BOTH} | extra


def test_an_opener_the_stream_started_before_the_line_is_put_back_then_moved_to_the_line():
    line = NOW - timedelta(minutes=15)
    days = [[early_opener(-79), row(2, 45, 30)]]
    opener = days[0][0]
    assert sig.early_repair(opener, days, NOW - timedelta(minutes=16), 15) == ("put_back", line)
    assert sig.early_repair(opener, days, line, 15) == ("moved_to_line", line)
    assert sig.early_repair(opener, days, NOW + timedelta(minutes=30), 15) == (
        "moved_to_line",
        line,
    )
    assert sig.early_repair(opener, days, NOW, 0) is None


def test_an_opener_at_the_line_by_staff_or_with_the_day_under_way_needs_no_repair():
    days = [[early_opener(-15), row(2, 45, 30)]]
    assert sig.early_repair(days[0][0], days, NOW, 15) is None
    days = [[early_opener(-79, live_because=mt.BY_STAFF), row(2, 45, 30)]]
    assert sig.early_repair(days[0][0], days, NOW, 15) is None
    days = [[early_opener(-79), row(2, 45, 30, state=mt.LIVE)]]
    assert sig.early_repair(days[0][0], days, NOW, 15) is None
    days = [[row(1, 0, 45), row(2, 45, 30)]]
    assert sig.early_repair(days[0][0], days, NOW, 15) is None


def test_an_early_opener_a_replay_ended_comes_back_until_the_days_planned_end():
    line = NOW - timedelta(minutes=15)
    days = [[early_opener(-79, state=mt.DONE), row(2, 45, 30)]]
    opener = days[0][0]
    for minutes in (-70, 0, 74):
        assert sig.early_repair(opener, days, NOW + timedelta(minutes=minutes), 15) == (
            "put_back",
            line,
        )
    assert sig.early_repair(opener, days, NOW + timedelta(minutes=75), 15) is None
    ended = [[opener | {"actual_ended_at": iso(-60)}, row(2, 45, 30)]]
    assert sig.early_repair(ended[0][0], ended, NOW, 15) is None
    on_time = [[early_opener(-5, state=mt.DONE), row(2, 45, 30)]]
    assert sig.early_repair(on_time[0][0], on_time, NOW, 15) is None
