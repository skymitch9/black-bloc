import pathlib
from datetime import UTC, datetime, timedelta

import pytest

from black_bloc import marathon_ladyarcaders as la
from black_bloc import marathon_sources as ms

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "marathon"
NOW = datetime(2026, 9, 26, 19, 0, tzinfo=UTC)
CALENDAR = "https://ladyarcaders.com/events/{n}/schedule/calendar/"


def ics(name):
    return (FIXTURES / name).read_bytes().decode("utf-8")


def calendar(*events, head="X-WR-CALNAME:Lady Arcaders Microthon Schedule"):
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", head]
    for one in events:
        lines += ["BEGIN:VEVENT", *one, "END:VEVENT"]
    return "\r\n".join([*lines, "END:VCALENDAR", ""])


def one_run(uid="1", start="20261010T120000", end="20261010T130000"):
    return [
        f"UID:{uid}",
        f"DTSTART;TZID=America/Toronto:{start}",
        f"DTEND;TZID=America/Toronto:{end}",
        "SUMMARY:[LAM26] Celeste (someone)",
        "DESCRIPTION:Celeste (Any%) by someone   Time Estimate: 01:00:00",
    ]


class Site:
    """ladyarcaders.com as a map of URL → (status, body); unknown numbers answer empty."""

    def __init__(self, answers=None):
        self.answers = dict(answers or {})
        self.asked = []

    async def text(self, url):
        self.asked.append(url)
        return self.answers.get(url, (200, ""))


def asked_numbers(site):
    return [int(url.split("/events/")[1].split("/")[0]) for url in site.asked]


# --- the ICS parser ----------------------------------------------------------------------------


def test_folded_lines_join_and_escapes_unescape():
    text = (
        "BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:9\r\n"
        "SUMMARY:[X] Don't Stop\\, Girly\r\n pop! (a\\, b\\; c)\r\n"
        "DESCRIPTION:line one\\nline two \\\\ done\r\n\tand more\r\n"
        "END:VEVENT\r\nEND:VCALENDAR\r\n"
    )
    [event] = la.parse_ics(text)
    assert event["SUMMARY"] == "[X] Don't Stop, Girlypop! (a, b; c)"
    assert event["DESCRIPTION"] == "line one\nline two \\ doneand more"
    assert event["UID"] == "9"


def test_lf_only_files_and_a_bare_cr_parse_the_same():
    body = calendar(one_run())
    assert la.parse_ics(body.replace("\r\n", "\n")) == la.parse_ics(body)
    assert la.parse_ics(body.replace("\r\n", "\r")) == la.parse_ics(body)


@pytest.mark.parametrize(
    ("line", "wanted"),
    [
        ("DTSTART;TZID=America/Toronto:20260903T120500", "2026-09-03T16:05:00+00:00"),
        ("DTSTART;TZID=America/Toronto:20261201T120000", "2026-12-01T17:00:00+00:00"),
        ('DTSTART;TZID="America/Toronto":20260903T120500', "2026-09-03T16:05:00+00:00"),
        ("DTSTART:20260903T160500Z", "2026-09-03T16:05:00+00:00"),
        ("DTSTART;VALUE=DATE:20260903", "2026-09-03T00:00:00+00:00"),
        ("DTSTART:20260903", "2026-09-03T00:00:00+00:00"),
        ("DTSTART;TZID=Nowhere/Nope:20260903T120500", "2026-09-03T12:05:00+00:00"),
        ("DTSTART:not a time", None),
    ],
)
def test_every_start_form_reads_as_utc(line, wanted):
    [event] = la.parse_ics(calendar(["UID:1", line], head="X-WR-CALNAME:x"))
    assert event["DTSTART"] == wanted


def test_a_floating_time_takes_the_calendars_own_zone():
    body = calendar(["UID:1", "DTSTART:20260903T120500"], head="X-WR-TIMEZONE:America/Toronto")
    assert la.parse_ics(body)[0]["DTSTART"] == "2026-09-03T16:05:00+00:00"


def test_an_alarm_inside_an_event_does_not_overwrite_the_event():
    body = calendar(
        [*one_run(), "BEGIN:VALARM", "DESCRIPTION:ring", "UID:alarm", "END:VALARM", "X-AFTER:1"]
    )
    [event] = la.parse_ics(body)
    assert event["UID"] == "1" and event["DESCRIPTION"].startswith("Celeste")
    assert event["X-AFTER"] == "1"


def test_nothing_parses_to_no_events():
    assert la.parse_ics("") == []
    assert la.parse_ics(None) == []
    assert la.parse_ics("<html>nope</html>") == []
    assert la.parse_ics(calendar()) == []


# --- the run mapping ---------------------------------------------------------------------------


def test_the_captured_calendar_maps_to_runs():
    runs = la.parse_ladyarcaders(la.parse_ics(ics("ladyarcaders_24.ics")))
    assert [one.external_id for one in runs] == [
        "1148",
        "1116",
        "1091",
        "1089",
        "1107",
        "1114",
        "1149",
    ]
    saros = runs[1]
    assert (saros.game, saros.category, saros.order) == ("SAROS", "NG+ All Bosses (Modifiers)", 2)
    assert saros.starts_at == "2026-09-03T16:15:00+00:00"
    assert saros.ends_at == "2026-09-03T17:02:00+00:00"
    assert saros.run_seconds == 47 * 60
    assert saros.people == (ms.Person("Nimelya", None, "runner"),)


def test_several_performers_split_on_the_escaped_comma_and_the_org_is_nobody():
    runs = {
        one.game: one for one in la.parse_ladyarcaders(la.parse_ics(ics("ladyarcaders_24.ics")))
    }
    assert [one.name for one in runs["Jackbox Games"].people] == [
        "MiaSchemes",
        "threepup",
        "carrarium",
        "ProfessorBurtch",
    ]
    assert runs["Jackbox Games"].category == "Showcase"
    assert [one.name for one in runs["BirdGut"].people] == ["mechamomo", "sapphire_in_pink"]
    assert all(one.login is None for run in runs.values() for one in run.people)
    welcome = runs["Welcome to LASS 2026!"]
    assert welcome.people == () and welcome.category == "Super Showcase 2026"


def test_a_comma_in_the_title_and_stray_spaces_do_not_confuse_the_category():
    runs = {
        one.game: one for one in la.parse_ladyarcaders(la.parse_ics(ics("ladyarcaders_24.ics")))
    }
    assert runs["Don't Stop, Girlypop!"].category == "Any% Inbounds"
    assert runs["Adventures with Barbie: Ocean Discovery"].category == "Any%"


def test_an_event_without_the_usual_shape_still_reads():
    body = calendar(
        ["UID:a", "DTSTART:20261010T120000Z", "DTEND:20261010T123000Z", "SUMMARY:Plain title"],
        ["UID:b", "DTSTART:20261010T110000Z", "SUMMARY:[T] Game", "DESCRIPTION:Game by Solo"],
        ["UID:c", "DESCRIPTION:no summary at all"],
    )
    runs = la.parse_ladyarcaders(la.parse_ics(body))
    assert [one.external_id for one in runs] == ["b", "a"]
    assert runs[0].people == (ms.Person("Solo", None, "runner"),) and runs[0].category == ""
    assert runs[1].game == "Plain title" and runs[1].run_seconds == 1800
    assert runs[1].people == ()


def test_the_event_name_is_the_calendar_name_else_its_tag_else_words():
    body = ics("ladyarcaders_24.ics")
    assert la.event_name(24, body, la.parse_ics(body)) == "Lady Arcaders Super Showcase 2026"
    bare = calendar(one_run(), head="VERSION:2.0")
    assert la.event_name(25, bare, la.parse_ics(bare)) == "LAM26"
    assert la.event_name(25, "", []) == "Lady Arcaders event 25"


# --- the reader --------------------------------------------------------------------------------


async def test_the_client_reads_the_calendar_as_text_for_runs_and_the_name():
    site = Site({CALENDAR.format(n=24): (200, ics("ladyarcaders_24.ics"))})
    client = ms.ScheduleClient(text_request=site.text)
    assert len(await client.runs("ladyarcaders", "24")) == 7
    assert await client.resolve("ladyarcaders", "24") == (
        "24",
        "Lady Arcaders Super Showcase 2026",
    )
    assert site.asked == [CALENDAR.format(n=24)] * 2


async def test_an_empty_calendar_is_unpublished_like_the_other_readers():
    site = Site({CALENDAR.format(n=25): (200, ics("ladyarcaders_empty.ics"))})
    client = ms.ScheduleClient(text_request=site.text)
    with pytest.raises(ms.ScheduleError) as caught:
        await client.runs("ladyarcaders", "25")
    assert caught.value.unpublished is True
    assert str(caught.value) == "ladyarcaders.com has no schedule published for event 25 yet"
    site.answers[CALENDAR.format(n=26)] = (200, calendar())
    with pytest.raises(ms.ScheduleError) as caught:
        await client.runs("ladyarcaders", "26")
    assert caught.value.unpublished is True
    with pytest.raises(ms.ScheduleError, match="no schedule published for event 25"):
        await client.resolve("ladyarcaders", "25")


async def test_the_reader_refuses_in_words():
    site = Site(
        {
            CALENDAR.format(n=7): (404, ""),
            CALENDAR.format(n=8): (503, ""),
            CALENDAR.format(n=9): (200, "<html>hello</html>"),
        }
    )
    client = ms.ScheduleClient(text_request=site.text)
    with pytest.raises(ms.ScheduleError, match="ladyarcaders.com has no event 7"):
        await client.runs("ladyarcaders", "7")
    with pytest.raises(ms.ScheduleError, match="ladyarcaders.com answered 503"):
        await client.runs("ladyarcaders", "8")
    with pytest.raises(ms.ScheduleError, match="not a schedule"):
        await client.runs("ladyarcaders", "9")
    with pytest.raises(ms.ScheduleError, match="has no event"):
        await client.runs("ladyarcaders", "../x")
    assert len(site.asked) == 3


# --- the probe ---------------------------------------------------------------------------------


def test_the_probe_starts_above_the_floor_the_list_or_the_memory():
    assert la.to_probe([], [], NOW, 6, 24) == [25, 26, 27]
    assert la.to_probe(["30", "short:x", "9"], [], NOW, 6, 24) == [31, 32, 33]
    assert la.to_probe([], [{"ref": "28", "name": "x"}], NOW, 6, 24) == [29, 30, 31]
    empties = [{"ref": "40", "empty_at": NOW.isoformat()}]
    assert la.highest_known([], empties, 24) == 24
    assert la.to_probe([], [], NOW, 6, 40) == [41, 42, 43]


def test_an_empty_number_waits_the_gap_before_it_is_asked_again():
    gap = timedelta(hours=6 * la.EMPTY_RETRY_CHECKS)
    seen = [
        {"ref": "25", "empty_at": (NOW - gap + timedelta(minutes=1)).isoformat()},
        {"ref": "26", "empty_at": (NOW - gap).isoformat()},
        {"ref": "27", "empty_at": "not a time"},
    ]
    assert la.to_probe([], seen, NOW, 6, 24) == [26, 27]
    assert la.retry_gap(6) == timedelta(hours=24)
    assert la.retry_gap(0) == timedelta(hours=la.EMPTY_RETRY_CHECKS)


async def test_the_probe_remembers_found_and_empty_answers_and_stops_at_a_404():
    body = calendar(one_run("1"), one_run("2", "20261011T120000", "20261011T180000"))
    site = Site({CALENDAR.format(n=25): (200, body), CALENDAR.format(n=27): (404, "")})
    read = await la.probe(site, [25, 26, 27, 28], NOW)
    assert asked_numbers(site) == [25, 26, 27]
    assert read == [
        {
            "ref": "25",
            "name": "Lady Arcaders Microthon",
            "starts_at": "2026-10-10T16:00:00+00:00",
            "ends_at": "2026-10-11T22:00:00+00:00",
        },
        {"ref": "26", "empty_at": NOW.isoformat()},
    ]


async def test_a_page_that_is_not_a_calendar_is_empty_and_a_server_error_fails_the_check():
    site = Site({CALENDAR.format(n=25): (200, "<html></html>")})
    assert await la.probe(site, [25], NOW) == [{"ref": "25", "empty_at": NOW.isoformat()}]
    site = Site({CALENDAR.format(n=25): (500, "")})
    with pytest.raises(ms.ScheduleError, match="ladyarcaders.com answered 500"):
        await la.probe(site, [25], NOW)


def test_merged_replaces_the_same_number_and_keeps_the_rest():
    seen = [{"ref": "25", "empty_at": "a"}, {"ref": "26", "empty_at": "a"}]
    fresh = [{"ref": "25", "name": "x", "starts_at": None, "ends_at": None}]
    assert la.merged(seen, fresh) == [seen[1], fresh[0]]
    assert len(la.merged([{"ref": str(n)} for n in range(3000)], [])) == 2000


def test_candidates_are_the_found_events_that_have_not_ended():
    seen = [
        {
            "ref": "25",
            "name": "Microthon",
            "starts_at": "2026-10-10T16:00:00+00:00",
            "ends_at": "2026-10-10T22:00:00+00:00",
        },
        {
            "ref": "24",
            "name": "Old",
            "starts_at": "2026-09-03T16:00:00+00:00",
            "ends_at": "2026-09-07T02:00:00+00:00",
        },
        {
            "ref": "23",
            "name": "Yesterday",
            "starts_at": "2026-09-25T10:00:00+00:00",
            "ends_at": "2026-09-25T22:00:00+00:00",
        },
        {"ref": "26", "empty_at": NOW.isoformat()},
        {"ref": "x", "name": "Not a number", "ends_at": "2026-12-01T00:00:00+00:00"},
    ]
    found = la.candidates(seen, NOW, 1)
    assert [(one.ref, one.name) for one in found] == [("23", "Yesterday"), ("25", "Microthon")]
    assert found[1].url == "https://ladyarcaders.com/events/25/schedule/"
    assert found[1].ends_at == "2026-10-10T22:00:00+00:00"
    assert [one.ref for one in la.candidates(seen, NOW, 0)] == ["25"]
