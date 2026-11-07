import json
from datetime import UTC, date, datetime

from black_bloc import sports_names as names
from black_bloc.sports import espn, mlb, ncaa
from black_bloc.sports.model import Player, Team
from tests.questions_fakes import make_bot
from tests.sports_fakes import Recorded, payload

NOVEMBER = date(2026, 11, 6)
AT_FOUR = datetime(2026, 11, 6, 11, 5, tzinfo=UTC)
AT_THREE = datetime(2026, 11, 6, 10, 55, tzinfo=UTC)


async def seeded(db, now=None):
    nba = espn.parse_teams(payload("espn_teams_nba"), "nba")
    await names.upsert(db, "team", "nba", "espn", nba, now=now)
    await names.upsert(
        db, "team", "ncaam", "espn", espn.parse_teams(payload("espn_teams_ncaam"), "ncaam")
    )
    await names.upsert(db, "school", "", "ncaa", ncaa.parse_schools(payload("henrygd_schools")))
    await names.upsert(
        db, "player", "nba", "espn", espn.parse_roster(payload("espn_roster_nba"), "nba", "2")
    )


async def logged(db):
    cur = await db.conn.execute("SELECT kind, details FROM action_log ORDER BY id")
    return [(row["kind"], json.loads(row["details"] or "{}")) for row in await cur.fetchall()]


async def test_a_prefix_beats_a_word_beats_an_alias_beats_anywhere(db):
    await seeded(db)
    await names.upsert(
        db,
        "team",
        "nba",
        "espn",
        [Team("90", "Celtic Rovers", "CR", "nba"), Team("91", "Old Bostonians", None, "nba")],
    )
    found = await names.search(db, "team", "nba", "bos")
    assert [one["name"] for one in found] == ["Boston Celtics", "Old Bostonians"]
    found = await names.search(db, "team", "nba", "celt")
    assert [one["name"] for one in found] == ["Celtic Rovers", "Boston Celtics"]


async def test_search_is_case_blind_and_reads_short_names_and_aliases(db):
    await seeded(db)
    assert [one["ext_id"] for one in await names.search(db, "team", "ncaam", "DUKE")] == ["150"]
    assert [one["ext_id"] for one in await names.search(db, "team", "ncaam", "tar heels")] == [
        "153"
    ]
    schools = await names.search(db, "school", "", "university of conn")
    assert [one["ext_id"] for one in schools] == ["uconn"]


async def test_one_answer_row_carries_what_the_page_draws(db):
    await seeded(db)
    (conley,) = await names.search(db, "player", "nba", "conley")
    assert conley == {
        "ext_id": "3195",
        "name": "Mike Conley",
        "short": "M. Conley",
        "league": "nba",
        "team": "Boston Celtics",
        "source": "espn",
        "kind": "player",
    }


async def test_search_is_scoped_by_kind_and_league_and_capped(db):
    await seeded(db)
    assert await names.search(db, "team", "nfl", "bos") == []
    assert await names.search(db, "player", "", "carter") != []
    assert await names.search(db, "nonsense", "", "bos") == []
    assert await names.search(db, "team", "", "") == []
    many = [Player(str(at), f"Smith {at}", None, "nfl") for at in range(40)]
    await names.upsert(db, "player", "nfl", "espn", many)
    assert len(await names.search(db, "player", "nfl", "smith")) == 25
    assert len(await names.search(db, "player", "nfl", "smith", limit=3)) == 3


async def test_a_percent_or_underscore_is_typed_text_not_a_pattern(db):
    await seeded(db)
    assert await names.search(db, "team", "nba", "%") == []
    assert await names.search(db, "team", "nba", "_") == []


async def test_an_upsert_refreshes_in_place_and_keeps_a_name_the_feed_dropped(db):
    await seeded(db, now="2026-11-07T10:00:00+00:00")
    renamed = [Team("2", "Boston Celts", "BOS", "nba")]
    await names.upsert(db, "team", "nba", "espn", renamed, now="2026-11-07T11:00:00+00:00")
    held = await names.counts(db)
    assert held["team:nba"]["rows"] == 2
    assert held["team:nba"]["updated_at"] == "2026-11-07T11:00:00+00:00"
    assert (await names.known(db, "espn", "2"))["name"] == "Boston Celts"
    assert (await names.known(db, "espn", "24"))["name"] == "San Antonio Spurs"


async def test_a_refresh_writes_every_list_that_answered_and_keeps_the_rest(db, monkeypatch):
    bot = await make_bot(db, monkeypatch)
    await names.upsert(db, "team", "nfl", "espn", [Team("12", "Kansas City Chiefs", "KC", "nfl")])
    found = await names.refresh(bot, [bot.guild], fetch=Recorded(), today=NOVEMBER)
    assert found["refreshed"]["team:nba"] == 2
    assert found["refreshed"]["school"] == 6
    assert found["refreshed"]["player:nba"] == 6
    assert found["refreshed"]["player:mlb"] == 3
    assert found["failed"]["team:nfl"] == "ESPN had nothing at that address for the NFL teams"
    assert (await names.known(db, "espn", "12"))["name"] == "Kansas City Chiefs"
    assert (await names.known(db, "mlb", "592450"))["name"] == "Aaron Judge"


async def test_a_failing_list_is_logged_once_a_streak_and_again_after_it_recovers(db, monkeypatch):
    bot = await make_bot(db, monkeypatch)
    fetch = Recorded()
    for _ in range(2):
        await names.refresh(bot, [bot.guild], fetch=fetch, today=NOVEMBER)
    rows = await logged(db)
    nfl = [details for kind, details in rows if details.get("list") == "team:nfl"]
    assert len(nfl) == 1
    assert nfl[0]["why"] == "ESPN had nothing at that address for the NFL teams"
    assert [kind for kind, _ in rows].count("sports.names_refreshed") == 2
    fetch.routes["football/nfl/teams"] = "espn_teams_nba"
    await names.refresh(bot, [bot.guild], fetch=fetch, today=NOVEMBER)
    del fetch.routes["football/nfl/teams"]
    await names.refresh(bot, [bot.guild], fetch=fetch, today=NOVEMBER)
    nfl = [details for kind, details in await logged(db) if details.get("list") == "team:nfl"]
    assert len(nfl) == 2


async def test_status_names_each_list_with_its_count_and_its_failure(db, monkeypatch):
    bot = await make_bot(db, monkeypatch)
    await names.refresh(bot, [bot.guild], fetch=Recorded(), today=NOVEMBER)
    shown = await names.status(bot)
    lists = {one["list"]: one for one in shown["lists"]}
    assert len(lists) == 11
    assert (lists["team:nba"]["rows"], lists["team:nba"]["sources"]) == (2, ["ESPN"])
    assert lists["team:nba"]["why"] is None
    assert lists["player:mlb"]["sources"] == ["MLB"]
    assert lists["team:nfl"]["rows"] == 0
    assert lists["team:nfl"]["why"] == "ESPN had nothing at that address for the NFL teams"
    assert lists["team:nfl"]["failed_at"]
    assert shown["running"] is False


async def test_one_refresh_at_a_time_from_the_website(db, monkeypatch):
    bot = await make_bot(db, monkeypatch)
    first = names.start_refresh(bot, [bot.guild], fetch=Recorded(), today=NOVEMBER)
    assert first is not None
    assert names.start_refresh(bot, [bot.guild], fetch=Recorded(), today=NOVEMBER) is None
    assert (await first)["refreshed"]
    assert names.running(bot) is None


async def test_the_refresh_is_due_once_a_day_from_the_hour_when_stale(db, monkeypatch):
    bot = await make_bot(db, monkeypatch)
    guild = bot.guild
    assert names.due(bot, guild, AT_THREE, None, None) is True
    old = "2026-11-05T11:00:00+00:00"
    assert names.due(bot, guild, AT_THREE, old, None) is False
    assert names.due(bot, guild, AT_FOUR, old, None) is True
    assert names.due(bot, guild, AT_FOUR, old, date(2026, 11, 6)) is False
    assert names.due(bot, guild, AT_FOUR, "2026-11-06T10:00:00+00:00", None) is False
    assert names.due(bot, guild, AT_FOUR, "not a time", None) is True
    await bot.store.set(guild.id, "brackets_names_refresh_hour", 5)
    assert names.due(bot, guild, AT_FOUR, old, None) is False
    await bot.store.set(guild.id, "brackets_mode", "off")
    assert names.due(bot, guild, AT_FOUR, None, None) is False


async def test_mlb_players_keep_their_team_link_for_the_answer(db):
    await names.upsert(db, "team", "mlb", "mlb", mlb.parse_teams(payload("mlb_teams")))
    await names.upsert(db, "player", "mlb", "mlb", mlb.parse_players(payload("mlb_players")))
    (abbott,) = await names.search(db, "player", "mlb", "abbott")
    assert (abbott["team"], abbott["short"]) == (None, "A Abbott")


async def test_typed_words_match_in_any_order_across_name_and_aliases(db):
    await seeded(db)
    found = await names.search(db, "team", "ncaam", "heels carolina")
    assert [one["ext_id"] for one in found] == ["153"]
    assert [one["ext_id"] for one in await names.search(db, "team", "nba", "san spurs")] == ["24"]
    assert await names.search(db, "team", "nba", "boston spurs") == []
