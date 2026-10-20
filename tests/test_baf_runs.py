import json
from datetime import UTC, datetime

import pytest

from black_bloc import baf_runs as runs
from black_bloc.logkinds import VIA_WEBSITE
from black_bloc.settings_store import RUNS_PARTS, RUNS_SOURCES
from tests.baf_runs_fakes import (
    GUILD,
    HOST_ID,
    OTHER_ID,
    RUNNER_ID,
    FakeClient,
    add_marathon,
    add_run,
    count,
    kinds,
    make_bot,
    person,
    tracker_run,
)

NOW = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)


@pytest.fixture
async def bot(db, monkeypatch):
    return await make_bot(db, monkeypatch)


async def seed(bot):
    db = bot.db
    gdq = await add_marathon(db, "SGDQ 2026")
    hotfix = await add_marathon(db, "Hidden Heroes", "gdq_hotfix", "hh")
    horaro = await add_marathon(db, "RGLtv", "horaro", "rgl/x")
    old = await add_marathon(db, "AGDQ 2026", archived=True, mid=900)
    ids = {
        "ours": await add_run(
            db, gdq, 1, "Shredder's Revenge", [person("kaizo_kat", user_id=RUNNER_ID)]
        ),
        "host": await add_run(
            db, gdq, 2, "Hosted Game", [person("x"), person("hostess", "host", HOST_ID)]
        ),
        "upcoming": await add_run(
            db, gdq, 3, "Later", [person("kaizo_kat", user_id=RUNNER_ID)], state="upcoming"
        ),
        "hotfix": await add_run(
            db,
            hotfix,
            "a",
            "Celeste",
            [person("kaizo_kat", user_id=RUNNER_ID)],
            state="live",
            at="2026-10-05T18:00:00+00:00",
        ),
        "horaro": await add_run(
            db, horaro, 9, "Horaro Game", [person("kaizo_kat", user_id=RUNNER_ID)]
        ),
        "archived": await add_run(
            db,
            old,
            4,
            "shredder's   revenge",
            [person("kaizo_kat", user_id=RUNNER_ID)],
            at="2026-01-08T18:00:00+00:00",
            archived=True,
            rid=5000,
        ),
    }
    return {"gdq": gdq, "hotfix": hotfix, "old": old, **ids}


async def hand_sql_count(db, sources, parts):
    marks = ", ".join("?" for _ in sources)
    pmarks = ", ".join("?" for _ in parts)
    total = 0
    for runs_table, marathons in (
        ("marathon_runs", "marathons"),
        ("marathon_runs_archive", "marathons_archive"),
    ):
        cur = await db.conn.execute(
            f"SELECT count(DISTINCT r.id) AS n FROM {runs_table} r "
            f"JOIN {marathons} m ON m.id = r.marathon_id, json_each(r.people) p "
            f"WHERE m.guild_id = ? AND m.source IN ({marks}) AND r.state IN ('done', 'live') "
            f"AND json_extract(p.value, '$.user_id') IS NOT NULL "
            f"AND json_extract(p.value, '$.part') IN ({pmarks})",
            (GUILD, *sources, *parts),
        )
        total += (await cur.fetchone())["n"]
    cur = await db.conn.execute("SELECT count(*) AS n FROM baf_runs WHERE guild_id = ?", (GUILD,))
    return total + (await cur.fetchone())["n"]


async def test_the_view_counts_runs_by_ours_in_gdq_sources_done_or_live_archive_included(bot):
    ids = await seed(bot)

    rows = await runs.view(bot, bot.guild)

    assert [row["key"] for row in rows] == [
        f"t{ids['hotfix']}",
        f"t{ids['ours']}",
        f"t{ids['archived']}",
    ]
    assert len(rows) == await hand_sql_count(bot.db, ["gdq", "gdq_hotfix"], ["runner"])
    first = rows[1]
    assert first["runners_text"] == "Kat (kaizo_kat)"
    assert first["event"] == "SGDQ 2026" and first["event_word"] == "GDQ"
    assert first["marathon_id"] == ids["gdq"] and first["how"] == "tracked"
    assert rows[2]["marathon_id"] is None and rows[2]["event"] == "AGDQ 2026"
    assert rows[0]["event_word"] == "GDQ Hotfix" and rows[0]["state"] == "live"


async def test_a_host_who_is_ours_counts_only_when_runs_parts_says_so(bot):
    ids = await seed(bot)
    await bot.store.set(GUILD, RUNS_PARTS, ["runner", "host"], by=1)
    await bot.store.set(GUILD, RUNS_SOURCES, ["gdq"], by=1)

    keys = {row["key"] for row in await runs.view(bot, bot.guild)}

    assert keys == {f"t{ids['ours']}", f"t{ids['host']}", f"t{ids['archived']}"}
    assert len(keys) == await hand_sql_count(bot.db, ["gdq"], ["runner", "host"])


async def test_games_group_on_the_trimmed_lowered_name_and_answer_the_four_questions(bot):
    await seed(bot)

    found = runs.games(await runs.view(bot, bot.guild))

    shredder = next(one for one in found if one["game_key"] == "shredder's revenge")
    assert shredder["times"] == 2
    assert shredder["last_date"].startswith("2026-10-02")
    assert shredder["last_event"] == "SGDQ 2026"
    assert shredder["runners"] == ["Kat"] and shredder["categories"] == ["Any%"]


async def test_an_edit_to_a_tracked_run_survives_the_next_schedule_read_and_clears(bot):
    ids = await seed(bot)
    key = f"t{ids['ours']}"

    done = await runs.edit(
        bot,
        bot.guild,
        bot.guild.members[2],
        key,
        {"game": "TMNT: Shredder's Revenge"},
        via=VIA_WEBSITE,
    )
    assert done.ok
    await bot.db.conn.execute(
        "UPDATE marathon_runs SET game = ?, category = ? WHERE id = ?",
        ("Shredders Revenge", "Any% Co-op", ids["ours"]),
    )
    await bot.db.conn.commit()

    row = await runs.find(bot, bot.guild, key)
    assert row["game"] == "TMNT: Shredder's Revenge" and row["category"] == "Any% Co-op"
    assert row["edited"] == ["game"] and row["tracked"] == {"game": "Shredders Revenge"}
    assert (await count(bot.db, "marathon_runs")) == 5

    same = await runs.edit(bot, bot.guild, None, key, {"game": "TMNT: Shredder's Revenge"})
    assert not same.ok and same.status == 409
    cleared = await runs.edit(bot, bot.guild, None, key, {"clear": True}, via=VIA_WEBSITE)
    assert cleared.ok
    assert (await runs.find(bot, bot.guild, key))["game"] == "Shredders Revenge"
    assert (await kinds(bot.db)).count("web.runs.edited") == 2


async def test_remove_and_restore_a_tracked_run_never_touch_the_marathon_tables(bot):
    ids = await seed(bot)
    key = f"t{ids['ours']}"
    before = await count(bot.db, "marathon_runs")

    assert (await runs.remove(bot, bot.guild, None, key, via=VIA_WEBSITE)).ok
    assert (await runs.find(bot, bot.guild, key))["removed"] is True
    assert not (await runs.remove(bot, bot.guild, None, key)).ok
    assert all(
        one["game_key"] != "shredder's revenge" or one["times"] == 1
        for one in runs.games(await runs.view(bot, bot.guild))
    )
    assert (await runs.restore(bot, bot.guild, None, key, via=VIA_WEBSITE)).ok
    assert (await runs.find(bot, bot.guild, key))["removed"] is False
    refused = await runs.restore(bot, bot.guild, None, key)
    assert not refused.ok and refused.code == "not_removed"
    assert await count(bot.db, "marathon_runs") == before
    assert "web.runs.removed" in await kinds(bot.db)
    assert "web.runs.restored" in await kinds(bot.db)


async def test_a_run_added_by_hand_is_edited_then_deleted_and_cannot_be_restored(bot):
    ids = await seed(bot)
    added = await runs.add(
        bot,
        bot.guild,
        None,
        {
            "date": "2025-06-30",
            "marathon_id": ids["gdq"],
            "game": "Celeste",
            "category": "Any%",
            "runners": [{"user_id": str(RUNNER_ID)}],
            "runner_names": "SomeoneElse",
            "series": "Celeste",
            "note": "BtB",
        },
        via=VIA_WEBSITE,
    )
    assert added.ok
    key = added.value
    row = await runs.find(bot, bot.guild, key)
    assert row["how"] == "hand" and row["series"] == "Celeste"
    assert row["marathon_id"] == ids["gdq"] and row["event"] == "SGDQ 2026"
    assert row["runners_text"] == "Kat, SomeoneElse"
    assert [one["linked"] for one in row["runners"]] == [True, False]

    assert (await runs.edit(bot, bot.guild, None, key, {"category": "100%"})).ok
    assert (await runs.find(bot, bot.guild, key))["category"] == "100%"
    assert (await runs.remove(bot, bot.guild, None, key)).ok
    assert await runs.find(bot, bot.guild, key) is None
    assert (await runs.restore(bot, bot.guild, None, key)).code == "not_restorable"


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"game": " "}, "no_game"),
        ({"game": "x", "date": "tomorrowish"}, "bad_date"),
        ({"game": "x", "marathon_id": 98765}, "no_such_event"),
    ],
)
async def test_a_bad_add_is_refused_in_words_and_writes_nothing(bot, payload, code):
    outcome = await runs.add(bot, bot.guild, None, payload)

    assert not outcome.ok and outcome.code == code and "nothing was saved" in outcome.message
    assert await count(bot.db, "baf_runs") == 0


async def test_a_series_is_set_cleared_and_logged_per_game(bot):
    await seed(bot)

    assert (await runs.set_series(bot, bot.guild, None, "Shredder's Revenge", "TMNT")).ok
    rows = await runs.view(bot, bot.guild)
    assert {row["series"] for row in rows if row["game_key"] == "shredder's revenge"} == {"TMNT"}
    assert not (await runs.set_series(bot, bot.guild, None, "shredder's revenge", "TMNT")).ok
    assert (await runs.set_series(bot, bot.guild, None, "shredder's revenge", "")).ok
    assert await count(bot.db, "baf_series") == 0
    assert (await kinds(bot.db)).count("runs.series_set") == 2


async def test_filters_match_what_the_page_chips_do(bot):
    ids = await seed(bot)
    every = await runs.view(bot, bot.guild)

    assert [row["key"] for row in runs.filtered(every, year="2026", event="agdq 2026")] == [
        f"t{ids['archived']}"
    ]
    assert len(runs.filtered(every, runner=str(RUNNER_ID))) == 3
    assert len(runs.filtered(every, q="celeste")) == 1
    assert runs.filtered(every, how="hand") == []


CSV = """Date,Event,Game,Category,Runners,Series
2025-06-30,BtB 2025,Shovel Knight,Any%,Kat,Shovel Knight
2025-06-30,BtB 2025,Shovel Knight,Any%,Kat,
07/02/2025,Frost 2025,Celeste,Any%,Stranger;PT,
,BtB 2025,,Any%,Kat,
"""


async def test_csv_dry_run_writes_nothing_then_the_real_import_writes_exactly_its_count(bot):
    dry = await runs.import_csv(bot, bot.guild, None, CSV, dry_run=True)
    assert dry.ok
    assert dry.value["would_add"] == 2 and dry.value["skipped"] == 1
    assert dry.value["need_match"] == 1 and dry.value["unreadable"] == 1
    assert await count(bot.db, "baf_runs") == 0
    assert await kinds(bot.db) == []

    real = await runs.import_csv(bot, bot.guild, None, CSV, dry_run=False, via=VIA_WEBSITE)
    assert real.value["added"] == 2 and await count(bot.db, "baf_runs") == 2
    again = await runs.import_csv(bot, bot.guild, None, CSV, dry_run=False)
    assert again.value["added"] == 0 and again.value["skipped"] == 3
    assert (await kinds(bot.db)).count("web.runs.imported") == 1

    rows = await runs.view(bot, bot.guild)
    shovel = next(row for row in rows if row["game"] == "Shovel Knight")
    assert shovel["how"] == "imported" and shovel["series"] == "Shovel Knight"
    assert shovel["runners"][0]["user_id"] == str(RUNNER_ID)
    celeste = next(row for row in rows if row["game"] == "Celeste")
    assert [one["user_id"] for one in celeste["runners"]] == [None, str(OTHER_ID)]


async def test_export_then_import_round_trips_with_nothing_added(bot):
    await seed(bot)
    await runs.import_csv(bot, bot.guild, None, CSV, dry_run=False)
    before = await count(bot.db, "baf_runs")

    text = runs.export_csv(await runs.view(bot, bot.guild))
    back = await runs.import_csv(bot, bot.guild, None, text, dry_run=False)

    assert text.splitlines()[0].split(",") == list(runs.CSV_COLUMNS)
    assert back.value["added"] == 0 and back.value["skipped"] == len(text.splitlines()) - 1
    assert await count(bot.db, "baf_runs") == before


@pytest.mark.parametrize(
    ("text", "code"),
    [("", "bad_csv"), ("name,when\nx,y\n", "bad_csv"), ("game\n" + "x\n" * 2002, "bad_csv")],
)
async def test_an_unreadable_csv_is_refused_in_words(bot, text, code):
    outcome = await runs.import_csv(bot, bot.guild, None, text, dry_run=True)

    assert not outcome.ok and outcome.code == code and "nothing was imported" in outcome.message


def tracker_runs():
    return [
        tracker_run(1, "Shredder's Revenge", ["kaizo_kat"]),
        tracker_run(2, "Someone Else's Game", ["Stranger"]),
        tracker_run(3, "Hosted", ["Stranger"], host="hostess"),
        tracker_run(4, "Not Yet", ["kaizo_kat"], at="2027-01-01T00:00:00+00:00"),
        tracker_run(5, "Paired Later", ["Gamer2025"]),
    ]


async def test_the_gdq_importer_dry_runs_then_writes_exactly_that_and_never_makes_a_marathon(bot):
    client = FakeClient(tracker_runs())
    url = "https://tracker.gamesdonequick.com/tracker/event/50"

    dry = await runs.import_event(bot, bot.guild, None, url, dry_run=True, client=client, now=NOW)
    assert dry.ok
    assert dry.value["would_add"] == 1 and dry.value["not_run_yet"] == 1
    assert [one["name"] for one in dry.value["unmatched"]] == ["Gamer2025", "Stranger"]
    assert await count(bot.db, "baf_runs") == 0

    real = await runs.import_event(
        bot,
        bot.guild,
        None,
        url,
        dry_run=False,
        pairs={"Gamer2025": str(OTHER_ID)},
        client=client,
        now=NOW,
        via=VIA_WEBSITE,
    )
    assert real.value["added"] == 2
    assert await count(bot.db, "baf_runs") == 2
    again = await runs.import_event(
        bot, bot.guild, None, url, dry_run=False, client=client, now=NOW
    )
    assert again.value["added"] == 0 and again.value["skipped"] == 1
    assert await count(bot.db, "marathons") == 0 and await count(bot.db, "marathon_runs") == 0
    assert await count(bot.db, "marathon_people") == 0
    assert (await kinds(bot.db)).count("web.runs.imported") == 1
    rows = await runs.view(bot, bot.guild)
    assert {row["event"] for row in rows} == {"SGDQ 2025"}
    assert all(row["how"] == "imported" for row in rows)
    assert not client.closed


async def test_a_run_already_tracked_is_skipped_by_the_importer(bot):
    marathon = await add_marathon(bot.db, "SGDQ 2025", ref="50")
    await add_run(
        bot.db, marathon, 1, "Shredder's Revenge", [person("kaizo_kat", user_id=RUNNER_ID)]
    )
    client = FakeClient(tracker_runs())

    found = await runs.import_event(
        bot,
        bot.guild,
        None,
        "https://tracker.gamesdonequick.com/tracker/event/50",
        dry_run=True,
        client=client,
        now=NOW,
    )

    assert found.value["would_add"] == 0 and found.value["skipped"] == 1


async def test_a_link_that_is_not_a_gdq_tracker_event_is_refused_before_any_read(bot):
    client = FakeClient(tracker_runs())

    outcome = await runs.import_event(
        bot, bot.guild, None, "https://horaro.net/rgl/x", dry_run=True, client=client
    )

    assert not outcome.ok and outcome.code == "not_gdq" and client.reads == 0


async def test_a_tracker_that_cannot_be_read_is_said_in_words(bot):
    from black_bloc.marathon_sources import ScheduleError

    class Down(FakeClient):
        async def runs(self, source, ref, **kwargs):
            raise ScheduleError("GDQ tracker answered 500")

    outcome = await runs.import_event(
        bot,
        bot.guild,
        None,
        "https://tracker.gamesdonequick.com/tracker/event/50",
        dry_run=False,
        client=Down([]),
    )

    assert not outcome.ok and outcome.status == 502 and "answered 500" in outcome.message
    assert await count(bot.db, "baf_runs") == 0


async def test_lookup_finds_games_by_part_of_their_name_and_logs_one_row(bot):
    await seed(bot)

    found = await runs.lookup(bot, bot.guild, bot.guild.members[2], "shredder")
    none = await runs.lookup(bot, bot.guild, None, "zelda")

    assert [one["game_key"] for one in found] == ["shredder's revenge"]
    assert found[0]["times"] == 2 and len(found[0]["runs"]) == 2 and found[0]["more"] == 0
    assert none == []
    assert (await kinds(bot.db)).count("runs.lookup") == 2


def test_keys_dates_and_the_page_address_parse_the_way_the_page_writes_them():
    assert runs.parse_key("t12") == ("tracked", 12)
    assert runs.parse_key("h3") == ("hand", 3)
    assert runs.parse_key("x3") is None and runs.parse_key("t") is None
    assert runs.parse_date("2025-06-30") == (True, "2025-06-30T00:00:00+00:00")
    assert runs.parse_date("2025-06-30 18:30") == (True, "2025-06-30T18:30:00+00:00")
    assert runs.parse_date("7/2/2025") == (True, "2025-07-02T00:00:00+00:00")
    assert runs.parse_date("") == (True, None)
    assert runs.parse_date("soon")[0] is False
    assert runs.page_url("https://bb.example/", "Shredder's Revenge") == (
        "https://bb.example/runs.html#q=Shredder%27s%20Revenge"
    )
    assert runs.page_url("", "x") is None


def test_the_people_json_of_a_hand_row_reads_like_a_marathon_run():
    assert runs.people_json(json.dumps([person("a")])) == [person("a")]
    assert runs.people_json("not json") == []
