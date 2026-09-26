import json
import pathlib
from datetime import UTC, datetime

import pytest

from black_bloc import marathon_feeds as mf
from black_bloc import marathon_horaro_events as hre
from black_bloc.marathon_sources import ScheduleError

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "marathon"
BEFORE_FPFF3 = datetime(2026, 8, 20, 12, 0, tzinfo=UTC)
SEPT = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
LOGIN = "fastpacedevents"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def events():
    return fixture("horaro_events_search.json")["data"]


def schedules():
    return fixture("horaro_fpff3_schedules.json")["data"]


def feed(**extra):
    row = {
        "id": 4,
        "source": mf.HORARO_EVENTS_FEED,
        "feed_ref": LOGIN,
        "name": "Fast Pace",
        "seen": None,
    }
    return row | extra


class Client:
    def __init__(self, listed=None, by_slug=None):
        self.listed = events() if listed is None else listed
        self.by_slug = {"fpff3": schedules(), "fpfh2023": []} if by_slug is None else by_slug
        self.searched = []
        self.read = []

    async def horaro_events(self, name):
        self.searched.append(name)
        return list(self.listed)

    async def horaro_schedules(self, slug):
        self.read.append(slug)
        if slug not in self.by_slug:
            raise ScheduleError(f"horaro.net has no event {slug}")
        return list(self.by_slug[slug])


def test_twitch_is_matched_whatever_its_case_or_spelling():
    assert hre.twitch_of("FastPacedEvents") == LOGIN
    assert hre.twitch_of("https://www.twitch.tv/FastPacedEvents/") == LOGIN
    assert hre.twitch_of("@fastpacedevents") == LOGIN
    assert hre.twitch_of(None) == ""


def test_ours_keeps_the_channels_events_and_drops_another_channels():
    assert [one["slug"] for one in hre.ours(events(), "FastPacedEvents")] == ["fpff3", "fpfh2023"]
    assert [one["slug"] for one in hre.ours(events(), "tgh_sr")] == ["fpfh"]
    assert hre.ours(events(), "") == []


def test_to_read_skips_an_event_whose_schedule_is_remembered():
    seen = [{"ref": "fpff3", "twitch": LOGIN, "schedule": "schedule"}, {"ref": "fpfh2023"}]
    assert [one["slug"] for one in hre.to_read(events(), hre.seen_of(feed()), LOGIN)] == [
        "fpff3",
        "fpfh2023",
    ]
    remembered = hre.seen_of(feed(seen=json.dumps([seen[0], seen[1] | {"twitch": LOGIN}])))
    assert [one["slug"] for one in hre.to_read(events(), remembered, LOGIN)] == ["fpfh2023"]


def test_a_read_record_is_the_event_and_its_first_schedule():
    record = hre.read_record(events()[0], schedules())
    assert record == {
        "ref": "fpff3",
        "twitch": LOGIN,
        "schedule": "schedule",
        "name": "Fast Pace for Friendspace 3",
        "starts_at": "2026-08-22T14:00:00+00:00",
        "ends_at": "2026-08-23T01:58:00+00:00",
        "url": "https://horaro.net/fpff3/schedule",
    }
    assert hre.read_record(events()[1], []) == {"ref": "fpfh2023", "twitch": LOGIN}


def test_candidates_are_the_channels_events_ahead_one_per_event_by_the_pasted_ref():
    seen = [hre.read_record(events()[0], schedules()), hre.listed_record(events()[2])]
    found = hre.candidates(events(), seen, LOGIN, BEFORE_FPFF3, 1)
    assert [(one.ref, one.name, one.url) for one in found] == [
        ("fpff3/schedule", "Fast Pace for Friendspace 3", "https://horaro.net/fpff3/schedule")
    ]
    assert hre.candidates(events(), seen, LOGIN, SEPT, 1) == []
    assert hre.candidates(events(), seen, "tgh_sr", BEFORE_FPFF3, 1) == []
    assert hre.candidates(events()[1:], seen, LOGIN, BEFORE_FPFF3, 1) == []


def test_remembered_replaces_what_it_said_and_keeps_the_newest_under_the_cap():
    old = [{"ref": "fpff3", "twitch": LOGIN}, {"ref": "x", "twitch": "y"}]
    new = [{"ref": "fpff3", "twitch": LOGIN, "schedule": "schedule"}]
    assert hre.remembered(old, new) == [old[1], new[0]]
    many = [{"ref": f"e{n}", "twitch": ""} for n in range(mf.SEEN_LIMIT + 3)]
    assert len(hre.remembered(many, new)) == mf.SEEN_LIMIT


async def test_a_check_searches_by_name_reads_only_its_channels_events_and_remembers_all():
    client = Client()
    found, seen = await hre.check(client, feed(), LOGIN, BEFORE_FPFF3, 1)
    assert client.searched == ["Fast Pace"]
    assert sorted(client.read) == ["fpff3", "fpfh2023"]
    assert [one.ref for one in found] == ["fpff3/schedule"]
    assert {one["ref"]: one["twitch"] for one in seen} == {
        "fpff3": LOGIN,
        "fpfh2023": LOGIN,
        "fpfh": "tgh_sr",
    }

    client.read.clear()
    again, same = await hre.check(client, feed(seen=json.dumps(seen)), LOGIN, BEFORE_FPFF3, 1)
    assert client.read == ["fpfh2023"] and same is None
    assert [one.ref for one in again] == ["fpff3/schedule"]


async def test_a_schedules_read_that_fails_is_not_remembered_and_a_blank_name_is_refused():
    client = Client(by_slug={"fpfh2023": []})
    found, seen = await hre.check(client, feed(), LOGIN, BEFORE_FPFF3, 1)
    assert found == [] and "fpff3" not in [one["ref"] for one in seen]
    with pytest.raises(ScheduleError, match="searches horaro.net by its name"):
        await hre.check(client, feed(name="  "), LOGIN, BEFORE_FPFF3, 1)
