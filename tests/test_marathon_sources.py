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
        "https://horaro.net/-/api/v1/events/esa/schedules",
        "https://oengus.io/LSS26/schedule",
        "https://oengus.io/marathon/LSS26/submit",
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


# --- RPG Limit Break: the same tracker software on another host ------------------------------


@pytest.mark.parametrize(
    ("url", "wanted"),
    [
        ("https://rpglimitbreak.com/schedule", ("rpglb", "latest")),
        ("https://rpglimitbreak.com/tracker/runs/rpglb2026", ("rpglb", "short:rpglb2026")),
        ("https://tracker.rpglimitbreak.com/runs/rpglb2026", ("rpglb", "short:rpglb2026")),
        ("https://tracker.rpglimitbreak.com/event/21", ("rpglb", "21")),
    ],
)
def test_read_url_knows_the_rpglb_forms(url, wanted):
    assert ms.read_url(url) == wanted


def test_a_tracker_base_names_its_source_and_its_event_pages():
    assert ms.tracker_source("https://tracker.rpglimitbreak.com/") == "rpglb"
    assert ms.tracker_source("https://tracker.gamesdonequick.com/tracker") == "gdq"
    assert ms.tracker_source("https://tracker.example.com") is None
    assert ms.event_url(21, "rpglb") == "https://tracker.rpglimitbreak.com/event/21"
    assert ms.read_url(ms.event_url(21, "rpglb")) == ("rpglb", "21")
    assert ms.schedule_page("rpglb", "21") == "https://tracker.rpglimitbreak.com/event/21"


def test_the_rpglb_runs_parse_like_gdq_ones_with_logins_from_stream():
    runs = ms.parse_gdq(fixture("rpglb2026_runs.json"))

    assert len(runs) == 8
    mass = next(one for one in runs if one.external_id == "629")
    assert mass.game == "Mass Effect 3"
    assert mass.starts_at == "2026-05-17T18:02:00+00:00"
    parts = [(one.name, one.login, one.part) for one in mass.people]
    assert ("Sanjan", "sanjan_", "runner") in parts
    assert ("agDeeds", None, "host") in parts


async def test_the_rpglb_client_reads_its_own_api_base():
    request, seen = pages((200, fixture("rpglb2026_runs.json")))
    runs = await ms.ScheduleClient(request=request).runs("rpglb", "21")
    assert len(runs) == 8
    assert seen == ["https://tracker.rpglimitbreak.com/api/v2/events/21/runs/?limit=500"]
    request, seen = pages((200, fixture("rpglb_events_list.json")))
    assert await ms.ScheduleClient(request=request).resolve("rpglb", "latest") == (
        "21",
        "RPG Limit Break 2026",
    )
    assert seen == ["https://tracker.rpglimitbreak.com/api/v2/events/"]


async def test_an_rpglb_failure_names_the_rpglb_tracker():
    request, _ = pages((404, None))
    with pytest.raises(ms.ScheduleError, match="RPG Limit Break tracker has the event") as caught:
        await ms.ScheduleClient(request=request).runs("rpglb", "22")
    assert caught.value.unpublished is True
    request, _ = pages((200, {"count": 0, "results": []}))
    with pytest.raises(ms.ScheduleError, match="lists no event yet"):
        await ms.ScheduleClient(request=request).resolve("rpglb", "latest")


# --- horaro.net (ESA) --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "wanted"),
    [
        ("https://horaro.net/esa/2026-summer2", ("horaro", "esa/2026-summer2")),
        ("https://horaro.net/ESA/2026-Summer2.json", ("horaro", "esa/2026-summer2")),
        ("https://www.horaro.net/esa/2026-winter1/?tz=utc", ("horaro", "esa/2026-winter1")),
    ],
)
def test_read_url_knows_a_horaro_schedule(url, wanted):
    assert ms.read_url(url) == wanted


def test_a_horaro_schedule_parses_by_column_name_with_links_stripped():
    runs = ms.parse_horaro(fixture("horaro_esa_2026_summer2.json"))

    assert len(runs) == 10
    croc = runs[0]
    assert croc.external_id == "s48365c94628"
    assert croc.game == "Croc 2" and croc.display_name == "Croc 2"
    assert croc.category == "Any%"
    assert croc.starts_at == "2026-08-02T13:00:00+00:00"
    assert croc.ends_at == "2026-08-02T14:25:00+00:00"
    assert croc.run_seconds == 5100
    assert croc.people == (ms.Person("hypnoshark", "hypnoshark", "runner"),)


def test_a_bare_player_name_has_no_login_and_players_split_every_way():
    runs = {one.game: one for one in ms.parse_horaro(fixture("horaro_esa_2026_summer2.json"))}
    assert runs["Doronko Wanko"].people == (ms.Person("spaceloz", None, "runner"),)
    assert [one.login for one in runs["Saltwater Sportfishing"].people] == [
        "zingochris",
        "superdave2",
    ]
    assert [(one.name, one.login) for one in runs["The Little Mermaid"].people] == [
        ("hirexen", "hirexen"),
        ("lucha_gym_2", None),
    ]
    assert [one.name for one in ms.horaro_people("Ann & Bob and Cy vs Dee")] == [
        "Ann",
        "Bob",
        "Cy",
        "Dee",
    ]


def test_columns_are_found_by_name_and_an_item_without_an_id_uses_its_place():
    payload = {
        "schedule": {
            "columns": ["Runners", "Game", "Category"],
            "items": [
                {
                    "scheduled_t": 1786000000,
                    "length_t": 600,
                    "data": ["[a](https://twitch.tv/aa)", "X", "Any%"],
                },
                {
                    "scheduled": "2026-08-02T15:00:00+02:00",
                    "length_t": 60,
                    "data": ["b", "Y", None],
                },
                {"scheduled_t": 1786001000, "length_t": 60, "data": ["c", None, None]},
            ],
        }
    }
    runs = ms.parse_horaro(payload)
    assert [(one.external_id, one.game, one.category) for one in runs] == [
        ("#0", "X", "Any%"),
        ("#1", "Y", ""),
    ]
    assert runs[0].people[0].login == "aa"
    assert runs[1].starts_at == "2026-08-02T13:00:00+00:00"
    assert ms.parse_horaro(None) == [] and ms.parse_horaro({"schedule": {}}) == []


def test_a_listed_schedule_spans_from_its_start_to_its_last_items_end():
    rows = fixture("horaro_esa_schedules.json")["data"]
    assert ms.horaro_span(rows[-1]) == (
        "2026-08-02T13:00:00+00:00",
        "2026-08-07T21:56:00+00:00",
    )
    assert ms.horaro_span({}) == (None, None)


async def test_the_horaro_client_reads_the_json_export_and_the_events_list():
    request, seen = pages((200, fixture("horaro_esa_2026_summer2.json")))
    client = ms.ScheduleClient(request=request)
    assert await client.resolve("horaro", "esa/2026-summer2") == (
        "esa/2026-summer2",
        "2026 - Summer (Stream Two)",
    )
    assert seen == ["https://horaro.net/esa/2026-summer2.json"]
    request, seen = pages((200, fixture("horaro_esa_2026_summer2.json")))
    assert len(await ms.ScheduleClient(request=request).runs("horaro", "esa/2026-summer2")) == 10
    request, seen = pages((200, fixture("horaro_esa_schedules.json")))
    listed = await ms.ScheduleClient(request=request).horaro_schedules("esa")
    assert [one["slug"] for one in listed] == ["2026-winter2", "2026-summer1", "2026-summer2"]
    assert seen == ["https://horaro.net/-/api/v1/events/esa/schedules"]
    assert ms.schedule_page("horaro", "esa/2026-summer2") == "https://horaro.net/esa/2026-summer2"


async def test_a_horaro_slug_that_does_not_answer_is_refused_in_words():
    request, _ = pages((404, None))
    with pytest.raises(ms.ScheduleError, match="horaro.net has no event nope"):
        await ms.ScheduleClient(request=request).horaro_schedules("nope")
    with pytest.raises(ms.ScheduleError, match="horaro.net has no event"):
        await ms.ScheduleClient(request=pages()[0]).horaro_schedules("../x")
    request, _ = pages((404, None))
    with pytest.raises(ms.ScheduleError, match="horaro.net has no event esa/gone"):
        await ms.ScheduleClient(request=request).runs("horaro", "esa/gone")


# --- oengus.io (Speed Stuff 4 Charity) ---------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "wanted"),
    [
        ("https://oengus.io/marathon/ss4c8", ("oengus", "ss4c8")),
        ("https://oengus.io/marathon/ss4c8/schedule", ("oengus", "ss4c8")),
        ("https://www.oengus.io/marathon/LSS26/schedule/", ("oengus", "LSS26")),
        ("https://oengus.io/marathon/ss4c8/schedule/2?x=1", ("oengus", "ss4c8/2")),
    ],
)
def test_read_url_knows_every_oengus_form(url, wanted):
    assert ms.read_url(url) == wanted


def test_an_oengus_marathon_has_a_schedule_page_and_a_site_word():
    assert ms.schedule_page("oengus", "ss4c8") == "https://oengus.io/marathon/ss4c8/schedule"
    assert ms.schedule_page("oengus", "ss4c8/2") == "https://oengus.io/marathon/ss4c8/schedule/2"
    assert ms.read_url(ms.schedule_page("oengus", "ss4lhs26")) == ("oengus", "ss4lhs26")
    assert ms.site_of("oengus") == "oengus.io"
    assert ms.SOURCE_WORDS["oengus"] == "Oengus"
    assert "oengus" in ms.SOURCES and "oengus" not in ms.TRACKER_SOURCES


@pytest.mark.parametrize(
    ("text", "seconds"),
    [
        ("PT57M", 3420),
        ("PT1H30M", 5400),
        ("PT2H45M", 9900),
        ("PT0S", 0),
        ("PT7M30S", 450),
        ("P1DT2H", 93600),
        ("", None),
        ("57:00", None),
        ("P", None),
        (None, None),
    ],
)
def test_an_iso_duration_reads_in_seconds(text, seconds):
    assert ms.duration_seconds(text) == seconds


def test_the_oengus_lines_parse_into_runs_with_setup_blocks_left_out():
    runs = ms.parse_oengus(fixture("oengus_lines_ss4c8_1.json"))

    assert [one.external_id for one in runs] == ["10073", "10080", "10092", "10150"]
    zelda = runs[0]
    assert zelda.game == "The Legend of Zelda: Link's Awakening DX"
    assert zelda.category == "Any% (No WW/OoB)"
    assert zelda.order == 2
    assert zelda.starts_at == "2021-09-03T16:10:00+00:00"
    assert zelda.run_seconds == 57 * 60
    assert zelda.ends_at == "2021-09-03T17:14:00+00:00"
    assert zelda.people == (ms.Person("Ryan Ford", "ryan_ford522", "runner"),)


def test_an_oengus_runner_without_a_twitch_connection_is_name_only():
    runs = {one.game: one for one in ms.parse_oengus(fixture("oengus_lines_ss4c8_1.json"))}
    assert runs["TimeSplitters 2"].people == (ms.Person("Realm", None, "runner"),)
    assert runs["Unravel Two"].people == (
        ms.Person("ripwsb_2", "ripwsb", "runner"),
        ms.Person("ceebs5", None, "runner"),
    )
    assert [one.login for one in runs["It Takes Two"].people] == ["lp3cinema", "bamford"]


def test_an_oengus_line_without_a_game_or_a_profile_is_handled_not_raised():
    lines = {
        "lines": [
            {"id": 1, "game": None, "setupBlock": False, "date": "2026-09-26T15:00:00Z"},
            {
                "id": 2,
                "game": "Game",
                "setupBlock": False,
                "date": "2026-09-26T15:00:00Z",
                "estimate": "junk",
                "runners": [{"runnerName": "Solo", "profile": None}, "x", {"runnerName": ""}],
            },
            "not a line",
        ]
    }
    runs = ms.parse_oengus(lines)
    assert len(runs) == 1
    assert runs[0].ends_at is None and runs[0].run_seconds is None
    assert runs[0].people == (ms.Person("Solo", None, "runner"),)
    assert ms.parse_oengus(None) == []


def test_for_home_is_one_list_of_live_next_and_open_each_id_once():
    payload = fixture("oengus_for_home.json")
    payload["open"].append(dict(payload["live"][0]))
    payload["next"].append({"id": "../bad"})
    listed = ms.oengus_home(payload)
    assert [one["id"] for one in listed] == ["LSS26", "ss4lhs26", "uksgblue26", "NDS3"]
    assert ms.oengus_home(None) == []


async def test_the_oengus_reader_takes_the_published_schedule_and_its_lines():
    request, seen = pages(
        (200, fixture("oengus_schedules_ss4c8.json")),
        (200, fixture("oengus_lines_ss4c8_1.json")),
    )
    runs = await ms.ScheduleClient(request=request).runs("oengus", "ss4c8")
    assert len(runs) == 4
    assert seen == [
        "https://oengus.io/api/v2/marathons/ss4c8/schedules",
        "https://oengus.io/api/v2/marathons/ss4c8/schedules/for-slug/1",
    ]


async def test_an_oengus_marathon_with_no_published_schedule_reads_as_unpublished():
    request, seen = pages((200, {"data": [{"id": 9, "slug": "1", "published": False}]}))
    with pytest.raises(ms.ScheduleError) as caught:
        await ms.ScheduleClient(request=request).runs("oengus", "ss4lhs26")
    assert caught.value.unpublished is True
    assert str(caught.value) == "oengus.io has the marathon but has not published its schedule yet"
    assert len(seen) == 1
    request, _ = pages((200, {"data": []}))
    with pytest.raises(ms.ScheduleError) as caught:
        await ms.ScheduleClient(request=request).runs("oengus", "ss4lhs26")
    assert caught.value.unpublished is True


async def test_several_published_schedules_take_the_pasted_slug_else_the_first():
    listed = {
        "data": [
            {"id": 1, "slug": "main", "published": True},
            {"id": 2, "slug": "side", "published": True},
        ]
    }
    lines = fixture("oengus_lines_ss4c8_1.json")
    request, seen = pages((200, listed), (200, lines))
    await ms.ScheduleClient(request=request).runs("oengus", "ss4c8")
    assert seen[-1].endswith("/schedules/for-slug/main")
    request, seen = pages((200, listed), (200, lines))
    await ms.ScheduleClient(request=request).runs("oengus", "ss4c8/side")
    assert seen[-1].endswith("/schedules/for-slug/side")


async def test_an_oengus_marathon_resolves_by_its_v1_record_and_a_missing_one_is_refused():
    request, seen = pages((200, fixture("oengus_marathon_ss4c8.json")))
    client = ms.ScheduleClient(request=request)
    assert await client.resolve("oengus", "ss4c8") == ("ss4c8", "Speed Stuff 4 Charity 8")
    assert seen == ["https://oengus.io/api/v1/marathons/ss4c8"]
    request, _ = pages((404, None))
    with pytest.raises(ms.ScheduleError, match="oengus.io has no event gone"):
        await ms.ScheduleClient(request=request).oengus_marathon("gone")
    with pytest.raises(ms.ScheduleError, match="oengus.io has no event"):
        await ms.ScheduleClient(request=pages()[0]).runs("oengus", "../x")
    request, _ = pages((500, None))
    with pytest.raises(ms.ScheduleError, match="oengus.io answered 500"):
        await ms.ScheduleClient(request=request).oengus_home()


async def test_the_oengus_home_is_read_through_the_same_client():
    request, seen = pages((200, fixture("oengus_for_home.json")))
    listed = await ms.ScheduleClient(request=request).oengus_home()
    assert [one["id"] for one in listed] == ["LSS26", "ss4lhs26", "uksgblue26", "NDS3"]
    assert seen == ["https://oengus.io/api/v2/marathons/for-home"]
