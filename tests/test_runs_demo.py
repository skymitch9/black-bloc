from __future__ import annotations

import json
import re

import pytest

from black_bloc import baf_runs, runs_genres
from black_bloc.settings_store import RUNS_DEFAULTS

PAGE_READS = (
    "key",
    "how",
    "how_word",
    "date",
    "event",
    "event_source",
    "event_word",
    "game",
    "game_key",
    "series",
    "genre",
    "developer",
    "category",
    "runners",
    "runners_text",
    "note",
    "removed",
    "edited",
    "folded",
    "state",
)
REAL_NAMES = {
    "cosmo",
    "kungfufruitcup",
    "zoast",
    "sinister1",
    "puwexil",
    "mekarazium",
    "kosmicd12",
    "simply",
    "summoningsalt",
    "niftski",
    "distortion2",
    "ludwig",
    "smallant1",
    "bubzia",
    "eddaket",
}
HOTFIX = re.compile(
    r"^(Black in a Flash|Game Masters|GDQueer|Make Your Own Victory|Speed Shots|Classic Catalog) "
)


@pytest.fixture(scope="module")
def demo():
    return json.loads(baf_runs.DEMO_FILE.read_text(encoding="utf-8"))


def test_the_demo_file_is_about_500_runs_under_400_kb(demo):
    assert 450 <= len(demo["rows"]) <= 550
    assert baf_runs.DEMO_FILE.stat().st_size < 400 * 1024
    assert demo["made_by"] == "scripts/scan/make_runs_demo.py"
    assert isinstance(demo["seed"], int)


def test_every_row_has_the_fields_the_page_reads_and_is_marked_test(demo):
    keys = [row["key"] for row in demo["rows"]]
    assert len(set(keys)) == len(keys)
    for row in demo["rows"]:
        assert set(PAGE_READS) <= set(row), row["key"]
        assert re.fullmatch(r"d\d{3}", row["key"])
        assert (row["how"], row["how_word"], row["state"]) == ("demo", "test", "done")
        assert row["removed"] is False and row["edited"] == [] and row["folded"] == []
        assert row["game_key"] == baf_runs.game_key(row["game"])
        assert row["runners_text"] == ", ".join(one["display"] for one in row["runners"])


def test_every_genre_is_in_the_house_spelling_with_at_most_two_entries(demo):
    rule = (
        runs_genres.parse_qualifiers(RUNS_DEFAULTS["runs_genre_qualifiers"]),
        runs_genres.parse_families(RUNS_DEFAULTS["runs_genre_families"]),
        runs_genres.parse_upper(RUNS_DEFAULTS["runs_genre_upper"]),
    )
    for row in demo["rows"]:
        assert runs_genres.genre_format(row["genre"], *rule) == row["genre"], row["genre"]
        assert len(runs_genres.genre_entries(row["genre"])) <= RUNS_DEFAULTS["runs_genre_max"]


def test_every_runner_is_an_invented_handle_from_the_files_own_index(demo):
    index = set(demo["runners_index"])
    used = {one["name"] for row in demo["rows"] for one in row["runners"]}
    assert used == index
    assert len(index) == 60
    assert not {name.lower() for name in index} & REAL_NAMES
    for row in demo["rows"]:
        assert 1 <= len(row["runners"]) <= 2
        for one in row["runners"]:
            assert one["user_id"] is None and one["linked"] is False
            assert one["display"] == one["name"]
    counts: dict[str, int] = {}
    for row in demo["rows"]:
        for one in row["runners"]:
            counts[one["name"]] = counts.get(one["name"], 0) + 1
    assert sum(1 for n in counts.values() if n >= 20) >= 3


def test_events_carry_the_source_their_name_says_and_dates_sit_in_range(demo):
    events = {one["name"]: one["source"] for one in demo["events"]}
    for row in demo["rows"]:
        wanted = "gdq_hotfix" if HOTFIX.match(row["event"]) else "gdq"
        assert row["event_source"] == wanted == events[row["event"]], row["event"]
        assert "2015-01-01" <= row["date"][:10] <= "2026-10-20"
        if row["event"].startswith("AGDQ"):
            assert row["date"][5:7] == "01"
        if row["event"].startswith("SGDQ"):
            assert row["date"][5:7] in ("06", "07")


def test_games_repeat_with_a_spread_and_a_few_rows_carry_a_note(demo):
    times: dict[str, int] = {}
    for row in demo["rows"]:
        times[row["game_key"]] = times.get(row["game_key"], 0) + 1
    assert 100 <= len(times) <= 130
    assert max(times.values()) <= 12 and min(times.values()) >= 1
    assert sum(1 for n in times.values() if n >= 8) >= 3
    noted = sum(1 for row in demo["rows"] if row["note"])
    assert 0.02 <= noted / len(demo["rows"]) <= 0.06
