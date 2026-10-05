import json
import pathlib
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest

from black_bloc import marathon_hotfix as hf
from black_bloc import marathon_overlay as mo
from black_bloc.marathon_sources import Person, ScheduleError

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "marathon"
ORGANISERS = (FIXTURES / "gdqueer_organisers.csv").read_text(encoding="utf-8")
GDQ_SHEET = (FIXTURES / "gdq_hotfix_sheet.csv").read_text(encoding="utf-8")


def gdqueer():
    return list(hf.parse_hotfix(GDQ_SHEET, ["GDQueer"])[0].runs)


def slots():
    return mo.slots_of(ORGANISERS)


def utc(text):
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


# --- the organisers' sheet --------------------------------------------------------------------


def test_the_sheet_reads_as_24_slots_and_its_separator_rows_are_left_out():
    found = slots()
    assert len(found) == 24
    first = found[0]
    assert first.start.astimezone(UTC) == utc("2026-10-03T17:00:00")
    assert (first.seconds, first.game, first.hosts, first.commentators) == (
        4080,
        "Spyro Reignited Trilogy",
        ("sweetpeebs",),
        ("ToastedKat",),
    )
    absolum = next(one for one in found if one.game == "Absolum")
    assert absolum.runners == ("ProfessorBurtch", "threepup")
    assert (absolum.hosts, absolum.commentators) == (("SYDNEY J",), ("BD", "carrarium"))
    assert [one.game for one in found if not one.hosts] == []
    assert found[-1].start.astimezone(UTC) == utc("2026-10-05T03:19:00")
    days = [mo.show_day(one.start) for one in found]
    assert (days.count(date(2026, 10, 3)), days.count(date(2026, 10, 4))) == (13, 11)


def test_a_time_is_eastern_wall_clock_through_daylight_saving_and_past_midnight():
    assert mo.when_of("2026-10-03 at 1:00PM").astimezone(UTC) == utc("2026-10-03T17:00:00")
    assert mo.when_of("2026-12-05 at 1:00PM").astimezone(UTC) == utc("2026-12-05T18:00:00")
    assert mo.when_of("2026-10-04 at 12:56AM").astimezone(UTC) == utc("2026-10-04T04:56:00")
    assert mo.when_of("2026-10-04 at 12:05 pm").astimezone(UTC) == utc("2026-10-04T16:05:00")
    assert mo.when_of("2026-10-04 14:30").astimezone(UTC) == utc("2026-10-04T18:30:00")
    for bad in ("", "soon", "2026-13-40 at 1:00PM", "2026-10-03 at 13:00PM", "10/3/2026 1:00 PM"):
        assert mo.when_of(bad) is None
    assert mo.show_day(mo.when_of("2026-10-04 at 12:56AM")) == date(2026, 10, 3)


@pytest.mark.parametrize("garbage", ["", "a,b,c\n1,2,3\n", "<html>sign in</html>", "Time\nnoon\n"])
def test_a_sheet_that_is_not_a_schedule_is_refused_in_words(garbage):
    with pytest.raises(ScheduleError, match="no Time and Game columns"):
        mo.slots_of(garbage)


def test_rows_with_a_bad_time_or_no_game_are_left_out_never_a_crash():
    text = "Time (EST),Estimate,Game,Host\nwhenever,0:10:00,A,x\n2026-10-03 at 1:00PM,,B,\n,,,\n"
    found = mo.slots_of(text)
    assert [(one.game, one.seconds, one.hosts) for one in found] == [("B", None, ())]


# --- matching ---------------------------------------------------------------------------------


def test_every_gdqueer_run_pairs_by_title_on_both_days_though_the_names_differ():
    runs = gdqueer()
    pairing = mo.paired(runs, slots())
    assert (len(pairing.slots), pairing.by_title) == (24, 24)
    assert pairing.loose_runs == () and pairing.loose_slots == ()
    assert mo.fits(runs, slots(), pairing)
    racers = next(one for one in runs if one.game.startswith("Dr. Robotnik"))
    assert [one.name for one in racers.people] == ["The_Mathcat"]
    assert pairing.slots[racers.external_id].runners == ("Mathcat",)


def test_a_retitled_run_pairs_by_its_place_in_the_day():
    text = ORGANISERS.replace("Kirby's Dream Land", "Kirby (GB)")
    runs = gdqueer()
    pairing = mo.paired(runs, mo.slots_of(text))
    kirby = next(one for one in runs if one.game == "Kirby's Dream Land")
    assert pairing.how[kirby.external_id] == "order"
    assert pairing.slots[kirby.external_id].game == "Kirby (GB)"
    assert (len(pairing.slots), pairing.by_title) == (24, 23)


def test_a_run_missing_from_one_sheet_stays_loose_and_never_takes_anothers_slot():
    lines = [one for one in ORGANISERS.splitlines() if "Bombun" not in one]
    runs = gdqueer()
    pairing = mo.paired(runs, mo.slots_of("\n".join(lines)))
    bombun = next(one for one in runs if one.game == "Bombun")
    assert pairing.loose_runs == (bombun.external_id,) and len(pairing.slots) == 23
    preshow = "2026-10-04 at 11:00AM,0:20:00,Preshow,Chat,x,sweetpeebs,,"
    extra = "\n".join([ORGANISERS.rstrip(), preshow, ""])
    pairing = mo.paired(runs, mo.slots_of(extra))
    assert [one.game for one in pairing.loose_slots] == ["Preshow"] and len(pairing.slots) == 24
    out = mo.overlaid(runs, mo.paired(runs, mo.slots_of("\n".join(lines))))
    at = runs.index(bombun)
    assert out[at].starts_at == out[at - 1].ends_at
    assert out[at].people == bombun.people
    assert out[at + 1].starts_at == "2026-10-03T22:36:00+00:00"


def test_a_sheet_for_other_days_or_other_games_is_not_this_marathons():
    runs = gdqueer()
    later = ORGANISERS.replace("2026-10-", "2026-11-")
    assert not mo.fits(runs, mo.slots_of(later), mo.paired(runs, mo.slots_of(later)))
    other = "Time,Estimate,Game\n" + "".join(
        f"2026-10-03 at {hour}:00PM,0:30:00,Game {hour}\n" for hour in range(1, 10)
    )
    found = mo.slots_of(other)
    assert not mo.fits(runs, found, mo.paired(runs, found))
    assert not mo.fits([], slots(), mo.paired([], slots()))


# --- the overlay ------------------------------------------------------------------------------


def test_the_overlay_gives_each_run_its_own_start_its_hosts_and_its_commentators():
    runs = gdqueer()
    out = mo.overlaid(runs, mo.paired(runs, slots()))
    assert [one.external_id for one in out] == [one.external_id for one in runs]
    assert [one.starts_at for one in out[:3]] == [
        "2026-10-03T17:00:00+00:00",
        "2026-10-03T18:18:00+00:00",
        "2026-10-03T19:20:00+00:00",
    ]
    assert out[1].ends_at == "2026-10-03T19:10:00+00:00" and out[1].run_seconds == 52 * 60
    assert out[13].starts_at == "2026-10-04T17:00:00+00:00"
    racers = next(one for one in out if one.game.startswith("Dr. Robotnik"))
    assert racers.starts_at == "2026-10-04T19:03:00+00:00"
    assert racers.people == (
        Person("The_Mathcat", "the_mathcat", "runner"),
        Person("SYDNEY J", None, "host"),
    )
    dread = out[-1]
    assert [(one.name, one.part) for one in dread.people[1:]] == [
        ("champrul", "host"),
        ("jayena", "commentator"),
        ("lucyna", "commentator"),
    ]
    hosts = {one.name for run in out for one in run.people if one.part == "host"}
    assert {"champrul", "JRisJunior", "sweetpeebs", "Quacksilver"} <= hosts
    assert "GDQueer" not in hosts


# --- the clock on a sheet with setup between its runs -------------------------------------------


def rows_of(runs, **changes):
    rows = []
    for index, run in enumerate(runs, start=1):
        rows.append(
            {
                "id": index,
                "external_id": run.external_id,
                "order_no": run.order,
                "game": run.game,
                "state": "upcoming",
                "sheet_at": run.starts_at,
                "sheet_ends_at": run.ends_at,
                "scheduled_at": run.starts_at,
                "ends_at": run.ends_at,
                "run_seconds": run.run_seconds,
                "actual_started_at": None,
                "actual_ended_at": None,
                "people": json.dumps(
                    [{"name": p.name, "login": p.login, "part": p.part} for p in run.people]
                ),
            }
            | changes.get(run.external_id, {})
        )
    return rows


def overlaid_rows(**changes):
    runs = gdqueer()
    out = mo.overlaid(runs, mo.paired(runs, slots()))
    return out, rows_of(out, **changes)


def test_the_overlaid_days_are_two_chains_and_nothing_moves_before_a_run_is_seen():
    _out, rows = overlaid_rows()
    assert [len(one) for one in mo.chains(rows)] == [13, 11]
    assert mo.retimed(rows) == []


def test_a_run_seen_starting_late_moves_the_rest_of_its_day_by_the_sheets_own_gaps():
    out, _ = overlaid_rows()
    late = "2026-10-03T19:32:00+00:00"
    _out, rows = overlaid_rows(**{out[2].external_id: {"actual_started_at": late}})
    changes = {one.row["id"]: one for one in mo.retimed(rows)}
    assert sorted(changes) == list(range(3, 14))
    assert (changes[3].starts_at, changes[3].ends_at) == (late, "2026-10-03T19:47:00+00:00")
    assert changes[4].starts_at == "2026-10-03T19:57:00+00:00"
    assert changes[5].starts_at == "2026-10-03T20:42:00+00:00"
    shift = timedelta(minutes=12)
    for row in rows[3:13]:
        moved = datetime.fromisoformat(changes[row["id"]].starts_at)
        assert moved - datetime.fromisoformat(row["sheet_at"]) == shift
    assert 14 not in changes


def test_a_run_that_ended_early_pulls_the_next_one_in_but_keeps_its_setup():
    out, _ = overlaid_rows()
    first = {
        "actual_started_at": "2026-10-04T17:00:00+00:00",
        "actual_ended_at": "2026-10-04T17:15:00+00:00",
        "state": "done",
    }
    _out, rows = overlaid_rows(**{out[13].external_id: first})
    changes = {one.row["id"]: one for one in mo.retimed(rows)}
    assert changes[14].ends_at == "2026-10-04T17:15:00+00:00"
    assert changes[15].starts_at == "2026-10-04T17:25:00+00:00"
    assert all(one > 13 for one in changes)


def test_a_read_without_the_sheet_keeps_what_the_stored_runs_last_held():
    out, rows = overlaid_rows()
    rows[1]["scheduled_at"] = "2026-10-03T18:40:00+00:00"
    kept = mo.kept(gdqueer(), rows)
    assert [(one.starts_at, one.ends_at, one.run_seconds) for one in kept] == [
        (one.starts_at, one.ends_at, one.run_seconds) for one in out
    ]
    assert [[(p.name, p.part) for p in one.people] for one in kept] == [
        [(p.name, p.part) for p in one.people] for one in out
    ]
    fresh = gdqueer()
    assert mo.kept(fresh, []) == fresh


def test_a_renamed_run_keeps_its_overlay_too_once_the_tolerance_is_given():
    out, rows = overlaid_rows()
    fresh = gdqueer()
    fresh[-1] = replace(fresh[-1], external_id="metroid-dread/minimum-items-glitchless")
    alone = mo.kept(fresh, rows)[-1]
    paired = mo.kept(fresh, rows, minutes=5)[-1]
    assert (alone.starts_at, [p.name for p in alone.people]) == (
        fresh[-1].starts_at,
        [p.name for p in fresh[-1].people],
    )
    assert (paired.starts_at, paired.ends_at) == (out[-1].starts_at, out[-1].ends_at)
    assert [(p.name, p.part) for p in paired.people] == [(p.name, p.part) for p in out[-1].people]
    assert paired.external_id == "metroid-dread/minimum-items-glitchless"


def test_what_a_marathon_remembers_about_its_sheet():
    assert mo.state_of({"overlay_sheet": None}) is None and not mo.applied({})
    assert mo.state_of({"overlay_sheet": "{broken"}) is None
    runs = gdqueer()

    class Sheet:
        label = "Games Done Queer"
        page = "https://docs.google.com/spreadsheets/d/e/abc/pubhtml"

    found = mo.state(Sheet, runs, mo.paired(runs, slots()), on=True)
    assert found == {
        "label": "Games Done Queer",
        "url": Sheet.page,
        "runs": 24,
        "matched": 24,
        "by_order": 0,
        "applied": True,
        "stale": None,
    }
    row = {"overlay_sheet": mo.dump(found)}
    assert mo.state_of(row) == found and mo.applied(row)
    assert not mo.applied({"overlay_sheet": mo.dump(found | {"applied": False})})
    assert mo.dump(None) is None


def test_a_live_or_done_run_never_seen_starting_stays_where_it_is():
    out, _ = overlaid_rows()
    stored = {
        out[0].external_id: {
            "state": "done",
            "scheduled_at": "2026-10-03T17:00:00+00:00",
            "ends_at": "2026-10-03T18:08:00+00:00",
        },
        out[1].external_id: {
            "state": "done",
            "scheduled_at": "2026-10-03T18:15:00+00:00",
            "ends_at": "2026-10-03T19:07:00+00:00",
        },
        out[2].external_id: {
            "state": "live",
            "scheduled_at": "2026-10-03T19:14:00+00:00",
            "ends_at": "2026-10-03T19:29:00+00:00",
        },
        out[3].external_id: {
            "scheduled_at": "2026-10-03T19:36:00+00:00",
            "ends_at": "2026-10-03T20:11:00+00:00",
        },
    }
    _out, rows = overlaid_rows(**stored)
    changes = {one.row["id"]: one for one in mo.retimed(rows)}
    assert not ({1, 2, 3} & set(changes))
    assert changes[4].starts_at == "2026-10-03T19:45:00+00:00"
    anchored = stored | {
        out[0].external_id: stored[out[0].external_id]
        | {"actual_started_at": "2026-10-03T17:00:00+00:00"}
    }
    _out, rows = overlaid_rows(**anchored)
    changes = {one.row["id"]: one for one in mo.retimed(rows)}
    assert not ({1, 2, 3} & set(changes))
    assert changes[4].starts_at == "2026-10-03T19:39:00+00:00"
