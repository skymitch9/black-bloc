import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from black_bloc import baf_runs as runs
from black_bloc.logkinds import VIA_WEBSITE
from black_bloc.settings_store import (
    RUNS_GENRE_FAMILIES,
    RUNS_GENRE_QUALIFIERS,
    RUNS_PARTS,
    RUNS_SAME_RUN_MINUTES,
    RUNS_SOURCES,
    SettingError,
)
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


async def shredder(bot):
    return next(one for one in await runs.view(bot, bot.guild) if one["game_key"] == SHREDDER)


SHREDDER = "shredder's revenge"


async def test_a_genre_is_set_beside_the_series_cleared_alone_and_logged_per_game(bot):
    await seed(bot)

    assert (await runs.set_series(bot, bot.guild, None, "Shredder's Revenge", "TMNT")).ok
    set_genre = await runs.set_genre(bot, bot.guild, None, "shredder's revenge", "Beat 'em up")
    assert set_genre.ok and "genre **Beat 'em up**" in set_genre.message
    row = await shredder(bot)
    assert (row["series"], row["genre"]) == ("TMNT", "Beat 'em up")
    every = runs.games(await runs.view(bot, bot.guild))
    game = next(one for one in every if one["game_key"] == row["game_key"])
    assert (game["series"], game["genre"]) == ("TMNT", "Beat 'em up")
    assert not (await runs.set_genre(bot, bot.guild, None, "Shredder's Revenge", "Beat 'em up")).ok

    assert (await runs.set_series(bot, bot.guild, None, "Shredder's Revenge", "")).ok
    assert await count(bot.db, "baf_series") == 1
    row = await shredder(bot)
    assert (row["series"], row["genre"]) == ("", "Beat 'em up")
    cleared = await runs.set_genre(bot, bot.guild, None, "Shredder's Revenge", " ")
    assert cleared.ok and cleared.message == "**Shredder's Revenge** has no genre now."
    assert await count(bot.db, "baf_series") == 0
    assert (await kinds(bot.db)).count("runs.genre_set") == 2


async def test_the_row_editor_writes_genre_and_series_and_a_blank_clears_on_edit(bot):
    ids = await seed(bot)
    added = await runs.add(
        bot,
        bot.guild,
        None,
        {"game": "Ember Knights", "genre": "Roguelite", "series": ""},
        via=VIA_WEBSITE,
    )
    row = await runs.find(bot, bot.guild, added.value)
    assert (row["series"], row["genre"]) == ("", "Roguelite")

    edited = await runs.edit(bot, bot.guild, None, f"t{ids['ours']}", {"genre": "Beat 'em up"})
    assert edited.ok
    tracked = await runs.find(bot, bot.guild, f"t{ids['ours']}")
    assert tracked["genre"] == "Beat 'em up"
    assert (await runs.edit(bot, bot.guild, None, added.value, {"genre": ""})).ok
    assert (await runs.find(bot, bot.guild, added.value))["genre"] == ""
    assert (await kinds(bot.db)).count("runs.edited") == 2


async def test_filters_and_search_reach_the_genre(bot):
    await seed(bot)
    await runs.set_genre(bot, bot.guild, None, "Celeste", "Platformer")
    every = await runs.view(bot, bot.guild)

    assert [row["game"] for row in runs.filtered(every, genre="platformer")] == ["Celeste"]
    assert [row["game"] for row in runs.filtered(every, q="platf")] == ["Celeste"]


GENRE_CSV = """Date,Event,Game,Category,Runners,Series,Genre
2025-06-30,BtB 2025,Celeste,Any%,Kat,,Platformer
2025-07-01,BtB 2025,Shredder's Revenge,Any%,Kat,TMNT,Fighting
"""


async def test_a_csv_genre_fills_a_blank_and_never_overwrites_a_set_one(bot):
    await seed(bot)
    await runs.set_genre(bot, bot.guild, None, "Shredder's Revenge", "Beat 'em up")

    assert (await runs.import_csv(bot, bot.guild, None, GENRE_CSV, dry_run=False)).ok

    rows = {row["game"]: row for row in await runs.view(bot, bot.guild)}
    assert rows["Celeste"]["genre"] == "Platformer"
    assert rows["Shredder's Revenge"]["genre"] == "Beat 'em up"
    assert rows["Shredder's Revenge"]["series"] == "TMNT"
    text = runs.export_csv(await runs.view(bot, bot.guild))
    head = text.splitlines()[0].split(",")
    assert head[head.index("series") + 1] == "genre"
    assert "Celeste,,Platformer," in text


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
    assert {row["runners_text"] for row in rows} == {"Kat (kaizo_kat)", "PT (Gamer2025)"}
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

    assert [one["game_key"] for one in found.games] == ["shredder's revenge"]
    first = found.games[0]
    assert first["times"] == 2 and len(first["runs"]) == 2 and first["more"] == 0
    assert found.suggestions == []
    assert none.games == []
    assert (await kinds(bot.db)).count("runs.lookup") == 2


async def lookup_details(bot):
    cur = await bot.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = 'runs.lookup' ORDER BY id DESC LIMIT 1"
    )
    return json.loads((await cur.fetchone())["details"])


async def test_lookup_finds_a_game_by_initials_words_in_any_order_runner_and_event(bot):
    await seed(bot)
    await add_genre(bot, "Donkey Kong Country 2", "Platformer")
    await add_genre(bot, "Sekiro: Shadows Die Twice", "Action-adventure")

    async def games_for(query):
        return [one["game"] for one in (await runs.lookup(bot, bot.guild, None, query)).games]

    assert await games_for("DKC2") == ["Donkey Kong Country 2"]
    assert await games_for("donkey 2") == ["Donkey Kong Country 2"]
    assert await games_for("kong country donkey") == ["Donkey Kong Country 2"]
    assert await games_for("dkc3") == []
    assert await games_for("sekiro shadow die") == ["Sekiro: Shadows Die Twice"]
    assert await games_for("sekrio") == ["Sekiro: Shadows Die Twice"]
    assert set(await games_for("kaizo")) == {"Shredder's Revenge", "Celeste"}
    assert await games_for("hidden heroes") == ["Celeste"]
    assert await games_for("") == []


async def test_nothing_found_suggests_up_to_three_close_names_and_logs_how_many(bot):
    await seed(bot)

    near = await runs.lookup(bot, bot.guild, None, "shredding reverb")
    assert near.games == [] and near.suggestions == ["Shredder's Revenge"]
    assert (await lookup_details(bot))["suggested"] == 1

    far = await runs.lookup(bot, bot.guild, None, "qqqqqq")
    assert far == runs.Found([], [])
    assert (await lookup_details(bot)) | {"query": ""} == {
        "query": "",
        "games": 0,
        "suggested": 0,
        "via": "discord",
    }


async def test_one_haystack_carries_every_searchable_field_one_per_line(bot):
    ids = await seed(bot)
    await runs.set_series(bot, bot.guild, None, "Celeste", "Celeste")
    await runs.set_genre(bot, bot.guild, None, "Celeste", "Kart racer")
    row = await runs.find(bot, bot.guild, f"t{ids['hotfix']}")
    rule = runs.genre_rule(bot, GUILD)

    lines = runs.text_of(row, rule).splitlines()
    assert lines[:3] == ["Celeste", "Kart racer", "racing"]
    assert {"racer", "kart racing", "Any%", "kaizo_kat", "Hidden Heroes"} <= set(lines)
    every = await runs.view(bot, bot.guild)
    assert next(one for one in every if one["key"] == row["key"])["search"] == runs.text_of(
        row, rule
    )


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


GENRE_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "runs" / "genre_families.json").read_text(
        encoding="utf-8"
    )
)


@pytest.mark.parametrize(("text", "family"), GENRE_FIXTURE["cases"])
def test_the_family_rule_answers_the_fixture_the_page_shares(text, family):
    rule = (
        runs.parse_qualifiers(GENRE_FIXTURE["qualifiers"]),
        runs.parse_families(GENRE_FIXTURE["families"]),
    )
    assert runs.genre_family(text, *rule) == family


async def add_genre(bot, game, genre):
    added = await runs.add(bot, bot.guild, None, {"game": game, "genre": genre, "event": "BtB"})
    assert added.ok
    return added.value


async def test_rows_and_games_carry_the_family_beside_the_genre_as_typed(bot):
    await seed(bot)
    await runs.set_genre(bot, bot.guild, None, "Celeste", "2D platformer")
    every = await runs.view(bot, bot.guild)

    row = next(one for one in every if one["game"] == "Celeste")
    game = next(one for one in runs.games(every) if one["game_key"] == "celeste")
    assert (row["genre"], row["genre_family"]) == ("2D platformer", "platformer")
    assert (game["genre"], game["genre_family"]) == ("2D platformer", "platformer")
    assert {one["genre_family"] for one in every if not one["genre"]} == {""}
    assert "genre_family" not in runs.export_csv(every).splitlines()[0]


async def test_racer_finds_a_kart_racer_and_a_racer_by_family_search_and_lookup(bot):
    await seed(bot)
    await add_genre(bot, "Mario Kart 8", "Kart racer")
    await add_genre(bot, "F-Zero GX", "Racing")
    await add_genre(bot, "Hades", "Action roguelike")
    every = await runs.view(bot, bot.guild)
    rule = runs.genre_rule(bot, GUILD)

    racing = {"Mario Kart 8", "F-Zero GX"}
    for wanted in ("racing", "Kart racer", "RACER"):
        assert {one["game"] for one in runs.filtered(every, genre=wanted, rule=rule)} == racing
    assert {one["game"] for one in runs.filtered(every, q="racer", rule=rule)} == racing
    assert {one["game"] for one in runs.filtered(every, q="rogue-lite", rule=rule)} == {"Hades"}
    assert {one["game"] for one in runs.filtered(every, q="roguelite", rule=rule)} == {"Hades"}
    assert {one["genre"] for one in every if one["game"] in racing} == {"Kart racer", "Racing"}
    found = await runs.lookup(bot, bot.guild, None, "racer")
    assert {one["game"] for one in found.games} == racing


async def test_a_families_edit_takes_effect_on_the_next_read(bot):
    await seed(bot)
    await add_genre(bot, "Tetris", "Puzzle")
    assert {one["genre_family"] for one in await runs.view(bot, bot.guild)} >= {"puzzle"}

    await bot.store.set(GUILD, RUNS_GENRE_FAMILIES, "brainy: puzzle, logic", by=1)
    await bot.store.set(GUILD, RUNS_GENRE_QUALIFIERS, "", by=1)

    every = await runs.view(bot, bot.guild)
    assert next(one for one in every if one["game"] == "Tetris")["genre_family"] == "brainy"
    assert runs.families_shown(runs.genre_rule(bot, GUILD)) == [
        {"family": "brainy", "aliases": ["puzzle", "logic"]}
    ]
    with pytest.raises(SettingError, match="Line 2"):
        await bot.store.set(GUILD, RUNS_GENRE_FAMILIES, "brainy: puzzle\nno colon", by=1)


async def test_a_word_from_the_note_finds_the_run_in_the_search_and_in_lookup(bot):
    await seed(bot)
    added = await runs.add(
        bot, bot.guild, None, {"game": "Tetris", "event": "BtB", "note": "Played blindfolded"}
    )
    assert added.ok
    every = await runs.view(bot, bot.guild)

    assert [row["game"] for row in runs.filtered(every, q="blindfold")] == ["Tetris"]
    assert (await runs.find(bot, bot.guild, added.value))["search"].endswith("Played blindfolded")
    found = await runs.lookup(bot, bot.guild, None, "blindfolded tetris")
    assert [one["game"] for one in found.games] == ["Tetris"]


DKC2 = "Donkey Kong Country 2"


async def game_masters(bot, *, second=None, gap_hours=0):
    db = bot.db
    show = await add_marathon(db, "Game Masters", "gdq_hotfix", "game-masters", mid=12)
    ryan = [person("ryan_ford", user_id=RUNNER_ID)]
    shape = (
        (171, "dkc2/12:28:48-am", "12:28:48 AM", "dropped", "2026-10-10T02:28:00+00:00",
         "2026-10-10T03:35:00+00:00"),
        (172, "dkc2/true-ending", "True Ending", "done", "2026-10-10T02:30:00+00:00",
         "2026-10-10T03:22:05+00:00"),
        (173, "dkc2/102%", "102%", "done", "2026-10-10T02:33:00+00:00",
         "2026-10-10T03:25:33+00:00"),
    )
    for rid, external, category, state, at, ends in shape:
        if rid == 173 and gap_hours:
            at, ends = f"2026-10-10T{2 + gap_hours:02d}:33:00+00:00", None
        people = second if rid == 173 and second else ryan
        await add_run(
            db, show, external, DKC2, people, state=state, at=at, category=category, rid=rid
        )
        await db.conn.execute(
            "UPDATE marathon_runs SET actual_ended_at = ?, ends_at = ? WHERE id = ?",
            (ends, ends, rid),
        )
    await db.conn.commit()
    return show


def dkc2_rows(rows):
    return [row for row in rows if row["game_key"] == DKC2.lower()]


async def test_a_run_the_sheet_renamed_mid_show_is_one_row_and_the_newest_id_wins(bot):
    await game_masters(bot)

    rows = dkc2_rows(await runs.view(bot, bot.guild))

    assert [row["key"] for row in rows] == ["t173"]
    assert rows[0]["category"] == "102%" and rows[0]["state"] == "done"
    assert rows[0]["folded"] == ["t172"] and rows[0]["carried"] == []
    assert await runs.find(bot, bot.guild, "t172") is None
    refused = await runs.edit(bot, bot.guild, None, "t172", {"note": "x"})
    assert not refused.ok and refused.status == 404


async def test_the_same_game_by_different_runners_stays_two_rows(bot):
    await game_masters(bot, second=[person("hostess", user_id=HOST_ID)])

    rows = dkc2_rows(await runs.view(bot, bot.guild))

    assert sorted(row["key"] for row in rows) == ["t172", "t173"]
    assert all(row["folded"] == [] for row in rows)


async def test_the_same_runner_three_hours_later_is_a_second_run(bot):
    await game_masters(bot, gap_hours=3)

    rows = dkc2_rows(await runs.view(bot, bot.guild))

    assert sorted(row["key"] for row in rows) == ["t172", "t173"]


async def test_runs_same_run_minutes_at_0_folds_nothing(bot):
    await game_masters(bot)
    await bot.store.set(GUILD, RUNS_SAME_RUN_MINUTES, 0, by=1)

    rows = dkc2_rows(await runs.view(bot, bot.guild))

    assert sorted(row["key"] for row in rows) == ["t172", "t173"]
    assert runs.games(rows)[0]["times"] == 2


async def test_starts_within_the_minutes_fold_even_when_the_windows_do_not_overlap(bot):
    await game_masters(bot, gap_hours=1)
    await bot.db.conn.execute("UPDATE marathon_runs SET actual_ended_at = NULL, ends_at = NULL")
    await bot.db.conn.commit()

    assert [row["key"] for row in dkc2_rows(await runs.view(bot, bot.guild))] == ["t173"]
    await bot.store.set(GUILD, RUNS_SAME_RUN_MINUTES, 30, by=1)
    assert len(dkc2_rows(await runs.view(bot, bot.guild))) == 2


async def test_an_older_row_staff_removed_stays_removed_and_restorable(bot):
    await game_masters(bot)
    await bot.store.set(GUILD, RUNS_SAME_RUN_MINUTES, 0, by=1)
    assert (await runs.remove(bot, bot.guild, None, "t172", via=VIA_WEBSITE)).ok
    await bot.store.set(GUILD, RUNS_SAME_RUN_MINUTES, 90, by=1)

    rows = dkc2_rows(await runs.view(bot, bot.guild))

    shown = {row["key"]: row for row in rows}
    assert set(shown) == {"t172", "t173"}
    assert shown["t172"]["removed"] is True and shown["t173"]["removed"] is False
    assert shown["t173"]["folded"] == []
    assert runs.games(rows)[0]["times"] == 1
    assert (await runs.restore(bot, bot.guild, None, "t172", via=VIA_WEBSITE)).ok
    assert [row["key"] for row in dkc2_rows(await runs.view(bot, bot.guild))] == ["t173"]


async def test_removing_the_surviving_row_removes_the_whole_run(bot):
    await game_masters(bot)

    assert (await runs.remove(bot, bot.guild, None, "t173", via=VIA_WEBSITE)).ok
    rows = dkc2_rows(await runs.view(bot, bot.guild))

    assert [(row["key"], row["removed"], row["folded"]) for row in rows] == [
        ("t173", True, ["t172"])
    ]
    assert runs.games(rows) == []
    assert (await runs.restore(bot, bot.guild, None, "t173", via=VIA_WEBSITE)).ok
    assert [row["removed"] for row in dkc2_rows(await runs.view(bot, bot.guild))] == [False]


async def test_a_hand_edit_on_the_older_row_carries_only_where_the_newer_has_none(bot):
    await game_masters(bot)
    await bot.store.set(GUILD, RUNS_SAME_RUN_MINUTES, 0, by=1)
    older = {"category": "True Ending (glitchless)", "note": "from the VOD"}
    assert (await runs.edit(bot, bot.guild, None, "t172", older, via=VIA_WEBSITE)).ok
    assert (await runs.edit(bot, bot.guild, None, "t173", {"note": "mine"})).ok
    await bot.store.set(GUILD, RUNS_SAME_RUN_MINUTES, 90, by=1)

    row = (dkc2_rows(await runs.view(bot, bot.guild)))[0]

    assert row["key"] == "t173" and row["folded"] == ["t172"]
    assert row["category"] == "True Ending (glitchless)" and row["note"] == "mine"
    assert row["carried"] == ["category"] and row["tracked"]["category"] == "102%"
    assert row["edited"] == ["note"]
    pinned = await runs.edit(bot, bot.guild, None, "t173", {"category": "102%"})
    assert pinned.ok
    row = (dkc2_rows(await runs.view(bot, bot.guild)))[0]
    assert row["category"] == "102%" and row["carried"] == []


async def test_games_export_and_lookup_count_a_renamed_run_once(bot):
    await game_masters(bot)
    every = await runs.view(bot, bot.guild)

    game = next(one for one in runs.games(every) if one["game_key"] == DKC2.lower())
    found = await runs.lookup(bot, bot.guild, None, "dkc2")

    assert game["times"] == 1 and game["keys"] == ["t173"] and game["categories"] == ["102%"]
    assert [(one["game"], len(one["runs"])) for one in found.games] == [(DKC2, 1)]
    assert [row["key"] for row in runs.filtered(every, q="dkc2")] == ["t173"]
    assert runs.export_csv(every).count(DKC2) == 1
