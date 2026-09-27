import json
from datetime import UTC, datetime, timedelta

from black_bloc import marathon as mt
from black_bloc import marathon_runner_posts as mrp

NOW = datetime(2026, 9, 26, 20, 0, tzinfo=UTC)
WORDS = {
    "marathon_part_runner": "runs",
    "marathon_state_upcoming": "coming up",
    "marathon_state_live": "on now",
    "marathon_state_done": "done",
    "marathon_state_dropped": "off the schedule",
}
TEMPLATE = "{runner} ({mention}) {part} {game} — {category} · {when} · {state} · {url}"
CHAMPRUL = [{"name": "champrul", "login": "champrul", "part": "runner", "user_id": 77}]


def at(minutes):
    return (NOW + timedelta(minutes=minutes)).isoformat()


def run(ident, start, *, state=mt.UPCOMING, people=CHAMPRUL, **more):
    return {
        "id": ident,
        "order_no": ident,
        "game": f"Game {ident}",
        "category": "Any%",
        "scheduled_at": at(start),
        "ends_at": at(start + 60),
        "state": state,
        "people": json.dumps(people),
        "runners_text": "champrul",
        "post_message_id": None,
        "post_channel_id": None,
        "post_pinned": 0,
        "last_seen_at": at(0),
        **more,
    }


def text(row):
    return mrp.post_text(
        row,
        {"name": "SS4C"},
        WORDS,
        template=TEMPLATE,
        default=TEMPLATE,
        url="https://twitch.tv/x",
        unlisted="no longer counted as BaF",
    ).text


def test_wanted_is_every_posted_run_and_every_baf_run_still_ahead_in_schedule_order():
    rows = [
        run(3, 90),
        run(1, 30),
        run(2, -300, state=mt.DONE),
        run(4, 10, people=[{"name": "x", "login": None, "part": "runner", "user_id": None}]),
        run(5, -400, state=mt.DROPPED, post_message_id=9),
        run(6, 0, state=mt.LIVE),
    ]
    assert [one["id"] for one in mrp.wanted(rows)] == [5, 6, 1, 3]


def test_the_post_names_the_runner_with_the_mention_as_text_and_the_state_word():
    said = text(run(1, 30))
    assert said.startswith("champrul (<@77>) runs Game 1 — Any% · <t:")
    assert ":f> · coming up · https://twitch.tv/x" in said
    assert "· on now ·" in text(run(1, 30, state=mt.LIVE))
    assert "· off the schedule ·" in text(run(1, 30, state=mt.DROPPED))


def test_a_run_nobody_from_baf_is_on_any_more_reads_unlisted_under_its_schedule_names():
    row = run(1, 30, people=[{"name": "champrul", "login": None, "part": "runner"}])
    said = text(row)
    assert said.startswith("champrul () runs") and "no longer counted as BaF" in said


def test_a_template_that_will_not_fill_falls_back_to_the_shipped_words():
    found = mrp.post_text(
        run(1, 30),
        {"name": "SS4C"},
        WORDS,
        template="{nope}",
        default=TEMPLATE,
        url="u",
        unlisted="x",
    )
    assert found.fell_back and found.text.startswith("champrul (<@77>)")


def test_the_pin_comes_off_a_day_after_the_run_is_over_or_dropped_and_at_once_when_unlisted():
    done = run(1, -120, state=mt.DONE, post_pinned=1)
    assert mrp.unpin_because(done, NOW) is None
    assert mrp.unpin_because(done, NOW + timedelta(days=1)) == mrp.BECAUSE_OVER
    dropped = run(2, 300, state=mt.DROPPED, post_pinned=1, last_seen_at=at(-60))
    assert mrp.unpin_because(dropped, NOW + timedelta(hours=22)) is None
    assert mrp.unpin_because(dropped, NOW + timedelta(hours=23, minutes=1)) == mrp.BECAUSE_OVER
    assert mrp.unpin_because(run(3, -600, state=mt.LIVE, post_pinned=1), NOW) is None
    unlisted = run(4, 30, post_pinned=1, people=[{"name": "a", "part": "runner"}])
    assert mrp.unpin_because(unlisted, NOW) == mrp.BECAUSE_UNLISTED
    assert mrp.unpin_because(run(5, -600, state=mt.DONE), NOW + timedelta(days=9)) is None


def test_only_the_pin_cap_code_counts_as_the_cap():
    class Capped(Exception):
        code = 30003

    class Other(Exception):
        code = 50013

    assert mrp.is_pin_cap(Capped()) and not mrp.is_pin_cap(Other())
    assert not mrp.is_pin_cap(RuntimeError())
