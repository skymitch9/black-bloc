import json
from datetime import UTC, datetime, timedelta

from black_bloc import marathon as mt
from black_bloc import marathon_people as mp

NOW = datetime(2027, 1, 12, 20, 0, tzinfo=UTC)


def at(minutes):
    return (NOW + timedelta(minutes=minutes)).isoformat()


def run(ident, start, game, people, state=mt.UPCOMING):
    return {
        "id": ident,
        "order_no": ident,
        "game": game,
        "category": "Any%",
        "scheduled_at": at(start),
        "ends_at": at(start + 60),
        "state": state,
        "people": json.dumps(
            [{"name": n, "login": lg, "part": p, "user_id": u} for n, lg, p, u in people]
        ),
    }


RUNS = [
    run(1, -300, "Halo 2", [("Casey", "caseyfast", "runner", 7)], mt.DONE),
    run(
        2,
        -20,
        "Super Metroid",
        [
            ("Casey", "caseyfast", "runner", 7),
            ("TheKing", "thekingspride", "runner", None),
            ("Peas", "peasplays", "runner", 8),
            ("Bobbeigh", "bobbeigh_tv", "runner", None),
            ("Host Person", None, "host", None),
        ],
        mt.LIVE,
    ),
    run(3, 120, "Celeste", [("Rivet", "rivetplays", "host", 9), ("Gz", None, "runner", None)]),
    run(4, 1500, "Kirby", [("CaseyAlt", None, "commentator", 7)]),
    run(5, 3000, "Dropped", [("Ghost", "ghost", "runner", 10)], mt.DROPPED),
]


def test_one_line_per_person_a_member_across_every_name_parts_joined_runs_counted():
    entries = {one["name"]: one for one in mp.group_people(RUNS)}
    casey = entries["Casey"]
    assert casey["user_id"] == 7 and [one["id"] for one in casey["runs"]] == [1, 2, 4]
    assert casey["parts"] == ["runner", "commentator"]
    assert casey["live"] is True and casey["done"] is False
    assert "Ghost" not in entries
    assert entries["TheKing"]["key"] == "thekingspride"
    assert entries["Host Person"]["key"] == "host person"


def test_baf_is_on_now_first_then_the_soonest_and_the_rest_by_name():
    baf, others = mp.split_people(mp.group_people(RUNS))
    assert [one["name"] for one in baf] == ["Casey", "Peas", "Rivet"]
    assert [one["name"] for one in others] == ["Bobbeigh", "Gz", "Host Person", "TheKing"]


def test_a_member_whose_runs_are_all_done_sinks_below_the_ones_still_to_come():
    rows = [
        run(1, -300, "Old", [("Done Dan", "dan", "runner", 3)], mt.DONE),
        run(2, 60, "New", [("Soon Sue", "sue", "runner", 4)]),
    ]
    baf, _ = mp.split_people(mp.group_people(rows))
    assert [one["name"] for one in baf] == ["Soon Sue", "Done Dan"]
    assert baf[1]["done"] is True


def test_how_a_member_matched_a_pairing_here_beats_one_everywhere_then_the_link():
    entries = {one["name"]: one for one in mp.group_people(RUNS)}
    pairings = [
        {"id": 5, "runner_name": "peas", "marathon_id": None, "user_id": 8},
        {"id": 6, "runner_name": "peas", "marathon_id": 1, "user_id": 8},
    ]
    assert mp.matched_by(entries["Peas"], pairings, {}, marathon_id=1) == (mp.BY_PAIRING, 6)
    links = {"caseyfast": 7}
    assert mp.matched_by(entries["Casey"], [], links, marathon_id=1) == (mp.BY_LINK, None)
    assert mp.matched_by(entries["Rivet"], [], {}, marathon_id=1) == (mp.BY_NAME, None)
    assert mp.matched_by(entries["TheKing"], pairings, links, marathon_id=1) == (None, None)


def test_near_miss_names_are_one_edit_away_or_the_head_of_an_underscored_name():
    usernames = {"bobbeigh": 1, "gz_hero": 2, "thekingspride": 3, "zz": 4}
    entries = {one["name"]: one for one in mp.group_people(RUNS)}
    assert mp.looks_like(entries["Bobbeigh"], usernames) == ("bobbeigh", 1)
    assert mp.looks_like(entries["Gz"], usernames) == ("gz_hero", 2)
    assert mp.looks_like(entries["TheKing"], usernames) == ("thekingspride", 3)
    assert mp.looks_like(entries["Host Person"], usernames) is None
    assert mp.looks_like(entries["Casey"], usernames) is None
    assert mp.one_edit("bobbeigh", "bobbeig") and mp.one_edit("abcd", "abce")
    assert not mp.one_edit("abcd", "abcd") and not mp.one_edit("abcd", "ab")


def test_the_spotlight_span_is_the_whole_run_list_or_the_one_slot_or_the_marathon():
    entries = {one["name"]: one for one in mp.group_people(RUNS)}
    marathon = {"starts_at": at(-600), "ends_at": at(4000)}
    whole = mp.spotlight_span(entries["Casey"]["runs"], marathon, lead_hours=2, slack_hours=1)
    assert whole == (at(-300 - 120), at(1500 + 60 + 60))
    one = mp.spotlight_span(
        entries["Casey"]["runs"], marathon, lead_hours=2, slack_hours=1, run_id=2
    )
    assert one == (at(-20 - 120), at(-20 + 60 + 60))
    none = mp.spotlight_span([], marathon, lead_hours=2, slack_hours=1)
    assert none == (marathon["starts_at"], marathon["ends_at"])


def test_the_schedule_goes_by_day_in_the_guilds_zone_a_race_is_one_slot():
    days = mp.days_of(RUNS, "America/Phoenix", NOW)
    assert [one.label for one in days] == ["Tue 12 Jan", "Wed 13 Jan"]
    assert [len(one.runs) for one in days] == [3, 1]
    assert days[1].baf == 1 and not days[1].today
    assert days[0].today and not days[0].past and days[0].baf == 3
    assert mp.day_label(days[0]) == "Tue 12 Jan · 3 slot(s) · 3 BaF"
    assert mp.slot_label(RUNS[1], "America/Phoenix") == "12:40 · Super Metroid"
    assert mp.slot_people(RUNS[1]).startswith("Casey ✦BaF, TheKing, Peas ✦BaF")


def test_a_person_is_found_by_login_or_name_and_a_slot_maps_back_to_its_entry():
    entries = mp.group_people(RUNS)
    assert mp.find_entry(entries, "BOBBEIGH_TV")["name"] == "Bobbeigh"
    assert mp.find_entry(entries, "host  person")["name"] == "Host Person"
    assert mp.find_entry(entries, "nobody") is None
    person = mt.people_of(RUNS[1])[2]
    assert mp.entry_for(entries, 2, person)["name"] == "Peas"
