import json
import pathlib
from datetime import UTC, datetime

import pytest

from black_bloc import marathon_sources as ms

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "marathon"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("url", "wanted"),
    [
        ("https://gamesdonequick.com/schedule/74", ("gdq", "74")),
        ("https://www.gamesdonequick.com/schedule/74/", ("gdq", "74")),
        ("https://gamesdonequick.com/schedule/74?tz=utc", ("gdq", "74")),
        ("https://tracker.gamesdonequick.com/tracker/event/74", ("gdq", "74")),
        ("https://tracker.gamesdonequick.com/tracker/event/AGDQ2027", ("gdq", "short:AGDQ2027")),
        ("  AGDQ2027 ", ("gdq", "short:AGDQ2027")),
    ],
)
def test_read_url_knows_every_gdq_form(url, wanted):
    assert ms.read_url(url) == wanted


@pytest.mark.parametrize(
    "url",
    [
        "https://horaro.net/esa/2026-one",
        "https://oengus.io/marathon/LSS26/schedule",
        "https://example.com/schedule/74",
        "",
        None,
        "74",
    ],
)
def test_read_url_refuses_everything_else(url):
    assert ms.read_url(url) is None


def test_the_captured_page_parses_into_runs_with_utc_times_and_every_part():
    runs = ms.parse_gdq(fixture("gdq_sgdq2026_runs.json"))

    assert len(runs) == 11
    dmc = next(one for one in runs if one.external_id == "7564")
    assert dmc.game == "Devil May Cry 5: Special Edition"
    assert dmc.category == "NG (Human)"
    assert dmc.order == 7
    assert dmc.starts_at == "2026-07-05T23:21:00+00:00"
    assert dmc.ends_at == "2026-07-06T01:00:00+00:00"
    assert dmc.run_seconds == 4035
    assert dmc.twitch_game == "Devil May Cry 5"
    parts = [(one.name, one.login, one.part) for one in dmc.people]
    assert ("DECosmic", "decosmic", "runner") in parts
    assert ("TheKingsPride", "thekingspride", "host") in parts
    assert [one.part for one in dmc.people].count("commentator") == 3


def test_a_person_without_a_stream_has_no_login_but_keeps_their_name():
    runs = ms.parse_gdq(fixture("gdq_sgdq2026_runs.json"))
    preshow = next(one for one in runs if one.order == 1)
    assert preshow.people[0] == ms.Person("Interview Crew", None, "runner")


def test_a_row_without_an_id_or_a_name_is_skipped_not_raised():
    assert ms.parse_gdq({"results": [{"id": None}, {"id": 3, "name": ""}, "junk"]}) == []
    assert ms.parse_gdq(None) == []


def test_seconds_and_times_read_what_the_tracker_writes():
    assert ms.seconds_of("1:07:15") == 4035
    assert ms.seconds_of("0") == 0
    assert ms.seconds_of("") is None
    assert ms.utc_iso("2027-01-03T11:30:00-05:00") == "2027-01-03T16:30:00+00:00"
    assert ms.utc_iso("not a date") is None


def test_an_event_short_resolves_through_the_events_listing():
    assert ms.event_from(fixture("gdq_events_agdq2027.json"))["id"] == 74


def pages(*answers):
    seen = []

    async def request(url):
        seen.append(url)
        return answers[len(seen) - 1]

    return request, seen


async def test_the_client_follows_the_pages_and_reads_the_event_runs_route():
    data = fixture("gdq_sgdq2026_runs.json")
    first = {**data, "results": data["results"][:5], "next": "https://next.example/p2"}
    second = {**data, "results": data["results"][5:], "next": None}
    request, seen = pages((200, first), (200, second))

    runs = await ms.ScheduleClient(request=request).runs("gdq", "66")

    assert len(runs) == 11
    assert seen == [
        "https://tracker.gamesdonequick.com/tracker/api/v2/events/66/runs/?limit=500",
        "https://next.example/p2",
    ]


async def test_an_unpublished_schedule_is_a_404_the_client_names():
    request, _ = pages((404, None))
    with pytest.raises(ms.ScheduleError) as caught:
        await ms.ScheduleClient(request=request).runs("gdq", "74")
    assert caught.value.unpublished is True
    assert "not published" in str(caught.value)


async def test_a_page_that_is_not_json_is_refused_in_words():
    request, _ = pages((200, None))
    with pytest.raises(ms.ScheduleError, match="not a schedule"):
        await ms.ScheduleClient(request=request).runs("gdq", "74")


async def test_resolve_reads_a_short_once_and_an_id_by_its_event():
    request, seen = pages((200, fixture("gdq_events_agdq2027.json")))
    assert await ms.ScheduleClient(request=request).resolve("gdq", "short:AGDQ2027") == (
        "74",
        "Awesome Games Done Quick 2027",
    )
    assert seen == ["https://tracker.gamesdonequick.com/tracker/api/v2/events/?short=AGDQ2027"]
    request, _ = pages((200, {"id": 74, "name": "Awesome Games Done Quick 2027"}))
    assert await ms.ScheduleClient(request=request).resolve("gdq", "74") == (
        "74",
        "Awesome Games Done Quick 2027",
    )
    request, _ = pages((404, None))
    with pytest.raises(ms.ScheduleError, match="no event 99"):
        await ms.ScheduleClient(request=request).resolve("gdq", "99")


async def test_a_short_nobody_has_is_refused_in_words():
    request, _ = pages((200, {"count": 0, "results": []}))
    with pytest.raises(ms.ScheduleError, match="no event NOPE"):
        await ms.ScheduleClient(request=request).resolve("gdq", "short:NOPE")


def test_only_a_numeric_gdq_ref_has_a_schedule_page():
    assert ms.schedule_page("gdq", "74") == "https://gamesdonequick.com/schedule/74"
    assert ms.schedule_page("gdq", "short:AGDQ2027") == ""


# --- the next GDQ event ---------------------------------------------------------------------

SEPT = datetime(2026, 9, 25, 18, 0, tzinfo=UTC)


def events():
    return fixture("gdq_events_list.json")["results"]


def test_the_live_list_is_newest_first_and_every_announced_event_is_a_draft():
    rows = events()
    stamps = [one["datetime"] for one in rows]
    assert stamps == sorted(stamps, reverse=True)
    ahead = [one for one in rows if ms.utc_iso(one["datetime"]) > SEPT.isoformat()]
    assert ahead and all(one["draft"] for one in ahead)


def test_the_next_event_is_the_soonest_ahead_even_while_it_is_a_draft():
    found = ms.next_gdq_event(events(), "69", SEPT)
    assert found["id"] == 71 and found["short"] == "GDHitless2026"


def test_the_next_event_skips_the_marathon_itself_and_anything_past():
    found = ms.next_gdq_event(events(), "73", datetime(2026, 12, 1, tzinfo=UTC))
    assert found["id"] == 74
    found = ms.next_gdq_event(events(), "71", SEPT)
    assert found["id"] == 72


def test_an_archived_event_is_never_suggested():
    rows = [dict(one, datetime="2027-06-01T12:00:00-04:00") for one in events() if one["archived"]]
    assert rows and ms.next_gdq_event(rows, "1", SEPT) is None


def test_nothing_ahead_or_nothing_listed_is_none():
    assert ms.next_gdq_event(events(), "74", datetime(2027, 2, 1, tzinfo=UTC)) is None
    assert ms.next_gdq_event([], "74", SEPT) is None
    assert ms.next_gdq_event([{"id": 9, "datetime": "soon"}, "junk"], "1", SEPT) is None


def test_ties_break_on_the_id_so_the_answer_never_flickers():
    one = {"id": 80, "datetime": "2027-03-01T12:00:00-05:00", "archived": False}
    two = {"id": 79, "datetime": "2027-03-01T12:00:00-05:00", "archived": False}
    assert ms.next_gdq_event([one, two], "1", SEPT)["id"] == 79


def test_the_suggested_link_is_the_tracker_form_the_reader_accepts():
    assert ms.event_url(71) == "https://tracker.gamesdonequick.com/tracker/event/71"
    assert ms.read_url(ms.event_url(71)) == ("gdq", "71")


async def test_the_events_list_is_read_through_the_same_client_and_follows_next():
    data = fixture("gdq_events_list.json")
    first = {**data, "results": data["results"][:3], "next": "https://next.example/e2"}
    second = {**data, "results": data["results"][3:], "next": None}
    request, seen = pages((200, first), (200, second))

    found = await ms.ScheduleClient(request=request).events()

    assert [one["id"] for one in found] == [74, 73, 72, 71, 69, 68]
    assert seen == [
        "https://tracker.gamesdonequick.com/tracker/api/v2/events/",
        "https://next.example/e2",
    ]


async def test_an_events_list_that_will_not_read_is_refused_in_words():
    request, _ = pages((503, None))
    with pytest.raises(ms.ScheduleError, match="answered 503"):
        await ms.ScheduleClient(request=request).events()
