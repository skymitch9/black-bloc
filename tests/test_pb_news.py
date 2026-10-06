from datetime import UTC, datetime, timedelta

from black_bloc import pb_news
from black_bloc.pb_news import (
    BASELINE,
    BEFORE_BASELINE,
    NOT_FASTER,
    OVER_THE_CAP,
    SAME_RUN,
    TOO_OLD,
    UNDATED,
    news,
)
from black_bloc.speedrun import PersonalBest

SINCE = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
NOW = SINCE + timedelta(days=2)
RECENT = NOW - timedelta(hours=1)


def best(run_id, slot="g|c||", seconds=100.0, *, status="verified", verified_at=RECENT, place=1):
    return PersonalBest(
        run_id=run_id,
        slot=slot,
        game="Game",
        category="Any%",
        seconds=seconds,
        place=place,
        weblink="",
        status=status,
        verified_at=verified_at,
    )


def stored(run_id, seconds):
    return {"run_id": run_id, "seconds": seconds}


def judged(baseline, fetched, *, since=SINCE, max_age_days=7, max_posts=5):
    return news(
        baseline, fetched, since=since, now=NOW, max_age_days=max_age_days, max_posts=max_posts
    )


def reasons(verdict):
    return {one.best.run_id: one.why for one in verdict.quiet}


def test_the_first_sight_is_all_quiet_however_fresh_the_runs_are():
    verdict = judged({}, [best("r1"), best("r2", "g2|c||")], since=None)

    assert verdict.news == () and verdict.held == ()
    assert reasons(verdict) == {"r1": BASELINE, "r2": BASELINE}
    assert verdict.counts == {BASELINE: 2}


def test_a_new_slot_verified_after_the_baseline_is_news():
    verdict = judged({"g|c||": stored("r1", 100.0)}, [best("r1"), best("r2", "g2|c||")])

    assert [one.run_id for one in verdict.news] == ["r2"]
    assert reasons(verdict) == {"r1": SAME_RUN}


def test_a_faster_run_in_a_known_slot_is_news():
    verdict = judged({"g|c||": stored("r1", 100.0)}, [best("r2", seconds=99.999)])

    assert [one.run_id for one in verdict.news] == ["r2"]


def test_the_same_run_with_a_better_place_is_not_news():
    verdict = judged({"g|c||": stored("r1", 100.0)}, [best("r1", place=1)])

    assert verdict.news == () and reasons(verdict) == {"r1": SAME_RUN}


def test_a_different_run_that_is_not_faster_is_not_news():
    held = {"g|c||": stored("r1", 100.0)}

    assert reasons(judged(held, [best("r0", seconds=100.0)])) == {"r0": NOT_FASTER}
    assert reasons(judged(held, [best("r0", seconds=120.0)])) == {"r0": NOT_FASTER}


def test_only_verified_runs_are_read_at_all():
    verdict = judged(
        {}, [best("r1", status="new", verified_at=None), best("r2", status="rejected")]
    )

    assert verdict.news == () and verdict.quiet == () and verdict.unverified == 2


def test_a_run_with_no_verify_date_is_recorded_and_not_posted():
    verdict = judged({}, [best("r1", verified_at=None)])

    assert verdict.news == () and reasons(verdict) == {"r1": UNDATED}


def test_a_run_verified_before_the_baseline_is_never_news_even_in_a_new_slot():
    """A leaderboard reorganised under new category ids shows old runs in slots never seen."""
    old = best("r1", "new-game|new-category||", verified_at=SINCE - timedelta(days=400))

    assert reasons(judged({}, [old])) == {"r1": BEFORE_BASELINE}


def test_a_run_verified_long_ago_is_too_old_to_post():
    since = NOW - timedelta(days=30)
    stale = best("r1", verified_at=NOW - timedelta(days=8))
    fresh = best("r2", "g2|c||", verified_at=NOW - timedelta(days=6))

    verdict = judged({}, [stale, fresh], since=since)

    assert [one.run_id for one in verdict.news] == ["r2"]
    assert reasons(verdict) == {"r1": TOO_OLD}


def test_a_run_already_stored_under_another_slot_is_the_same_run():
    verdict = judged({"old|slot||": stored("r1", 100.0)}, [best("r1", "new|slot||")])

    assert verdict.news == () and reasons(verdict) == {"r1": SAME_RUN}


def test_news_past_the_cap_is_held_oldest_first_kept():
    fetched = [
        best(f"r{at}", f"g{at}|c||", verified_at=RECENT + timedelta(minutes=at))
        for at in (3, 1, 2, 0)
    ]

    verdict = judged({}, fetched, max_posts=2)

    assert [one.run_id for one in verdict.news] == ["r0", "r1"]
    assert [one.run_id for one in verdict.held] == ["r2", "r3"]
    assert verdict.counts == {OVER_THE_CAP: 2}


def test_an_empty_answer_is_no_news_and_nothing_to_record():
    verdict = judged({"g|c||": stored("r1", 100.0)}, [])

    assert verdict == pb_news.Verdict()


def test_a_stored_row_with_no_readable_time_does_not_block_a_new_run():
    verdict = judged({"g|c||": {"run_id": "r1", "seconds": None}}, [best("r2")])

    assert [one.run_id for one in verdict.news] == ["r2"]
