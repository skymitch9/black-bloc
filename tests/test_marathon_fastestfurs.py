import json
import pathlib
from datetime import UTC, datetime

import pytest

from black_bloc import marathon_fastestfurs as ff
from black_bloc import marathon_sources as ms

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "marathon"
SEPT = datetime(2026, 9, 26, 19, 0, tzinfo=UTC)
EVENTS = "https://cheetah.fastestfurs.com/api/events"
SCHEDULE = "https://cheetah.fastestfurs.com/api/public/schedules/event/21"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def pages(*answers):
    seen = []

    async def request(url):
        seen.append(url)
        return answers[len(seen) - 1]

    return request, seen


@pytest.mark.parametrize(
    ("url", "wanted"),
    [
        ("https://fastestfurs.com/schedule/21", "21"),
        ("https://www.fastestfurs.com/schedule/21/", "21"),
        ("https://fastestfurs.com/schedule/21?tab=runs", "21"),
        ("https://cheetah.fastestfurs.com/api/public/schedules/event/21", "21"),
        ("https://fastestfurs.com/schedule", None),
        ("https://fastestfurs.com/schedule/x21", None),
        ("https://cheetah.fastestfurs.com/api/events", None),
        ("https://example.com/schedule/21", None),
        (None, None),
    ],
)
def test_read_ref_takes_the_schedule_page_and_the_api_link(url, wanted):
    assert ff.read_ref(url) == wanted


def test_the_schedule_page_is_the_sites_own_route_and_a_bad_ref_has_none():
    assert ff.schedule_page("21") == "https://fastestfurs.com/schedule/21"
    assert ff.schedule_page("../x") == ""


def test_the_schedule_walks_from_its_start_by_duration_and_setup_and_skips_breaks():
    runs = ff.parse_fastestfurs(fixture("fastestfurs_schedule_21.json"))
    assert [one.order for one in runs] == [1, 2, 3, 4, 5, 6, 7, 9]
    first = runs[0]
    assert (first.external_id, first.game, first.category) == (
        "843",
        "Kena: Bridge of Spirits",
        "Any% No Major Glitches",
    )
    assert first.starts_at == "2026-10-08T14:00:00+00:00"
    assert first.ends_at == "2026-10-08T14:45:00+00:00"
    assert first.run_seconds == 35 * 60
    assert runs[1].starts_at == first.ends_at
    after_break = runs[-1]
    assert after_break.game == "Resident Evil 2: Remake"
    assert after_break.starts_at == "2026-10-08T20:32:00+00:00"


def test_runners_are_name_only_split_like_horaro_players_and_hosts_follow():
    runs = ff.parse_fastestfurs(fixture("fastestfurs_schedule_21.json"))
    race = next(one for one in runs if one.game == "Racin' Ratz")
    assert race.people == (
        ms.Person("karma_dragoness", None, ms.RUNNER),
        ms.Person("winnerbit", None, ms.RUNNER),
        ms.Person("ClockworkOphelia", None, ms.HOST),
    )
    assert all(person.login is None for run in runs for person in run.people)


def test_a_broken_item_is_handled_not_raised():
    payload = {
        "startDateTime": None,
        "scheduleItems": [
            {"itemType": "run", "duration": 10, "runs": {"id": 1, "name": "", "runners": "x"}},
            {"itemType": "run", "duration": "ten", "runs": {"name": "Game", "runners": None}},
            "not an item",
        ],
    }
    runs = ff.parse_fastestfurs(payload)
    assert len(runs) == 1
    assert (runs[0].starts_at, runs[0].ends_at, runs[0].run_seconds) == (None, None, None)
    assert runs[0].people == ()
    assert ff.parse_fastestfurs(None) == []


def test_candidates_are_the_events_not_over_yet_with_their_page():
    found = ff.candidates(fixture("fastestfurs_events.json"), SEPT, 1)
    assert found == [
        ff.Candidate(
            "21",
            "Fastest Furs Fall Fest 2026",
            "2026-10-08T12:00:00+00:00",
            "2026-10-12T00:00:00+00:00",
            "https://fastestfurs.com/schedule/21",
        )
    ]


def test_an_event_counts_through_its_last_day_and_recent_days_after():
    rows = fixture("fastestfurs_events.json")
    last_day = datetime(2026, 10, 11, 23, 0, tzinfo=UTC)
    assert [one.ref for one in ff.candidates(rows, last_day, 0)] == ["21"]
    next_day = datetime(2026, 10, 12, 18, 0, tzinfo=UTC)
    assert ff.candidates(rows, next_day, 0) == []
    assert [one.ref for one in ff.candidates(rows, next_day, 1)] == ["21"]


def test_a_row_without_a_usable_id_or_date_is_not_a_candidate():
    rows = [{"id": "../x", "startDate": "2027-01-01"}, {"id": 30, "name": "No dates"}, "junk"]
    assert ff.candidates(rows, SEPT, 1) == []
    assert ff.event_rows({"not": "a list"}) == []


async def test_the_events_list_is_one_read_and_a_non_list_is_refused():
    request, seen = pages((200, fixture("fastestfurs_events.json")))
    listed = await ms.ScheduleClient(request=request).fastestfurs_events()
    assert [one["id"] for one in listed] == [21, 19, 16]
    assert seen == [EVENTS]
    request, _ = pages((200, {"events": []}))
    with pytest.raises(ms.ScheduleError, match="fastestfurs.com answered with something"):
        await ms.ScheduleClient(request=request).fastestfurs_events()
    request, _ = pages((503, None))
    with pytest.raises(ms.ScheduleError, match="fastestfurs.com answered 503"):
        await ms.ScheduleClient(request=request).fastestfurs_events()


async def test_the_reader_reads_the_public_schedule():
    request, seen = pages((200, fixture("fastestfurs_schedule_21.json")))
    runs = await ms.ScheduleClient(request=request).runs("fastestfurs", "21")
    assert len(runs) == 8 and seen == [SCHEDULE]


@pytest.mark.parametrize(
    "answer",
    [(404, None), (200, {"startDateTime": "2026-10-08T14:00:00.000Z", "scheduleItems": []})],
)
async def test_no_schedule_or_no_runs_yet_reads_as_unpublished(answer):
    request, _ = pages(answer)
    with pytest.raises(ms.ScheduleError) as caught:
        await ms.ScheduleClient(request=request).runs("fastestfurs", "21")
    assert caught.value.unpublished is True
    assert str(caught.value) == ff.NOT_PUBLISHED.format(site="fastestfurs.com")


async def test_a_bad_answer_is_a_failure_not_unpublished():
    request, _ = pages((500, None))
    with pytest.raises(ms.ScheduleError) as caught:
        await ms.ScheduleClient(request=request).runs("fastestfurs", "21")
    assert caught.value.unpublished is False
    with pytest.raises(ms.ScheduleError, match="fastestfurs.com has no event"):
        await ms.ScheduleClient(request=pages()[0]).runs("fastestfurs", "../x")


async def test_an_event_resolves_by_the_list_even_before_its_schedule_is_out():
    request, seen = pages((200, fixture("fastestfurs_events.json")))
    client = ms.ScheduleClient(request=request)
    assert await client.resolve("fastestfurs", "21") == ("21", "Fastest Furs Fall Fest 2026")
    assert seen == [EVENTS]
    request, _ = pages((200, fixture("fastestfurs_events.json")))
    with pytest.raises(ms.ScheduleError, match="fastestfurs.com has no event 99"):
        await ms.ScheduleClient(request=request).resolve("fastestfurs", "99")


def by_game(runs):
    return {one.game: one for one in runs}


def test_a_finished_item_moves_the_clock_by_its_actual_duration_not_the_plan():
    runs = by_game(ff.parse_fastestfurs(fixture("fastestfurs_schedule_actuals.json")))
    planned = by_game(
        ff.parse_fastestfurs(fixture("fastestfurs_schedule_actuals.json"), use_actuals=False)
    )
    mathcat = runs["Dr. Robotnik's Ring Racers"]
    assert planned["Dr. Robotnik's Ring Racers"].starts_at == "2026-10-09T22:20:00+00:00"
    assert mathcat.starts_at == "2026-10-09T21:27:42+00:00"
    assert mathcat.ends_at == "2026-10-09T23:27:42+00:00"
    assert (mathcat.timed_by_actuals, mathcat.actual_seconds) == (True, None)
    yakuza = runs["Yakuza Kiwami 2"]
    assert (yakuza.starts_at, yakuza.ends_at) == (
        "2026-10-09T19:30:59+00:00",
        "2026-10-09T21:27:42+00:00",
    )
    assert (yakuza.actual_seconds, yakuza.run_seconds) == (7003, 108 * 60)
    puyo = runs["Super Puyo Puyo"]
    assert puyo.starts_at == "2026-10-09T23:27:42+00:00"
    assert puyo.timed_by_actuals is False
    assert runs["Kena: Bridge of Spirits"].timed_by_actuals is False
    assert runs["Devil May Cry 3"].timed_by_actuals is False


def test_a_planned_only_schedule_walks_exactly_as_before():
    payload = fixture("fastestfurs_schedule_21.json")
    assert ff.parse_fastestfurs(payload) == ff.parse_fastestfurs(payload, use_actuals=False)
    assert all(not one.timed_by_actuals for one in ff.parse_fastestfurs(payload))


def item(order, duration, setup, actual, name=None):
    return {
        "itemType": "run" if name else "break",
        "orderIndex": order,
        "duration": duration,
        "setupTime": setup,
        "actualDuration": actual,
        "runs": {"id": order, "name": name, "runners": "x"} if name else None,
    }


SMALL = {
    "startDateTime": "2026-10-09T14:00:00.000Z",
    "scheduleItems": [
        item(0, 30, 10, 1800, "First"),
        item(1, 15, 0, 600, None),
        item(2, 60, 10, None, "Live"),
        item(3, 20, 5, None, "Later"),
    ],
}


def test_actual_includes_setup_is_a_switch_both_ways():
    inside = by_game(ff.parse_fastestfurs(SMALL))
    assert inside["Live"].starts_at == "2026-10-09T14:40:00+00:00"
    assert inside["Later"].starts_at == "2026-10-09T15:50:00+00:00"
    after = by_game(ff.parse_fastestfurs(SMALL, actual_includes_setup=False))
    assert after["First"].ends_at == "2026-10-09T14:40:00+00:00"
    assert after["Live"].starts_at == "2026-10-09T14:50:00+00:00"
    assert after["Later"].starts_at == "2026-10-09T16:00:00+00:00"
    assert inside["Live"].timed_by_actuals and after["Live"].timed_by_actuals


def test_an_actual_duration_of_zero_is_finished_and_takes_no_time():
    payload = {
        "startDateTime": SMALL["startDateTime"],
        "scheduleItems": [item(0, 30, 10, 0, "Skipped"), item(1, 20, 5, None, "Next")],
    }
    runs = by_game(ff.parse_fastestfurs(payload))
    assert (runs["Skipped"].starts_at, runs["Skipped"].ends_at) == (
        "2026-10-09T14:00:00+00:00",
        "2026-10-09T14:00:00+00:00",
    )
    assert runs["Skipped"].actual_seconds == 0
    assert runs["Next"].starts_at == "2026-10-09T14:00:00+00:00"
    assert runs["Next"].timed_by_actuals is True


def test_a_broken_actual_duration_is_read_as_not_finished():
    payload = {
        "startDateTime": SMALL["startDateTime"],
        "scheduleItems": [item(0, 30, 10, "soon", "Odd"), item(1, 20, 5, -5, "Odder")],
    }
    runs = by_game(ff.parse_fastestfurs(payload))
    assert runs["Odd"].actual_seconds is None
    assert runs["Odder"].starts_at == "2026-10-09T14:40:00+00:00"
    assert runs["Odder"].actual_seconds is None
