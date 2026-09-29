import pathlib
from datetime import UTC, date, datetime

import pytest

from black_bloc import marathon_hotfix as hf
from black_bloc.doc_import import DocImportError, Hop
from black_bloc.marathon_sources import GDQ_HOTFIX, ScheduleClient, ScheduleError

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "marathon"
SHEET = (FIXTURES / "gdq_hotfix_sheet.csv").read_text(encoding="utf-8")
PAGE_HTML = (FIXTURES / "gdq_hotfix_page.html").read_text(encoding="utf-8")
CSV = (
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vSxkh22kZxarTgwzgy3xn-g9xqmDYWfpawKBRHv4vBHf"
    "rA81gKx9jCqb8FILZ-riUO1hu0d77s3MDNV/pub?gid=728340068&single=true&output=csv"
)
SEPT = datetime(2026, 9, 28, 21, 0, tzinfo=UTC)


class Fake:
    def __init__(self, answers):
        self.answers = answers
        self.asked = []
        self.agents = set()

    async def __call__(self, url, *, seconds, limit, agent):
        self.asked.append(url)
        self.agents.add(agent)
        found = self.answers.get(url)
        if isinstance(found, Exception):
            raise found
        return found or Hop(404)


def ok(text, kind="text/html"):
    return Hop(200, None, kind, text.encode("utf-8"))


def gdqueer():
    return hf.parse_hotfix(SHEET, ["GDQueer"])


# --- the sheet --------------------------------------------------------------------------------


def test_gdqueer_is_one_block_of_24_runs_across_two_days():
    blocks = gdqueer()
    assert len(blocks) == 1
    block = blocks[0]
    assert (block.show, block.ref) == ("GDQueer", "gdqueer/2026-10-03")
    assert (block.first, block.last) == (date(2026, 10, 3), date(2026, 10, 4))
    assert len(block.runs) == 24
    assert [one.order for one in block.runs] == list(range(1, 25))
    assert len([one for one in block.runs if one.starts_at < "2026-10-04T12"]) == 13


def test_the_clock_progresses_by_the_estimates_and_restarts_each_day_at_the_show_start():
    runs = gdqueer()[0].runs
    assert [one.starts_at for one in runs[:3]] == [
        "2026-10-03T17:00:00+00:00",
        "2026-10-03T18:08:00+00:00",
        "2026-10-03T19:00:00+00:00",
    ]
    assert runs[12].ends_at == "2026-10-04T02:46:00+00:00"
    assert runs[13].game == "Wii Fit U" and runs[13].starts_at == "2026-10-04T17:00:00+00:00"
    last = runs[-1]
    assert (last.game, last.starts_at, last.ends_at) == (
        "Metroid Dread",
        "2026-10-05T01:39:00+00:00",
        "2026-10-05T03:09:00+00:00",
    )
    for before, after in zip(runs[:12], runs[1:13], strict=True):
        assert before.ends_at == after.starts_at


def test_eastern_time_follows_daylight_saving():
    winter = SHEET.replace("10/3/2026,", "12/5/2026,").replace("10/4/2026,", "12/6/2026,")
    runs = hf.parse_hotfix(winter, ["gdqueer"])[0].runs
    assert runs[0].starts_at == "2026-12-05T18:00:00+00:00"
    assert runs[13].starts_at == "2026-12-06T18:00:00+00:00"


def test_a_run_carries_game_category_estimate_and_runners_with_their_logins():
    runs = gdqueer()[0].runs
    spyro = runs[0]
    assert (spyro.game, spyro.category, spyro.run_seconds) == (
        "Spyro Reignited Trilogy",
        "Spyro the Dragon: 80 Dragons NBS",
        4080,
    )
    assert [(one.name, one.login, one.part) for one in spyro.people] == [
        ("Toronite", "toronite", "runner")
    ]
    coop = next(one for one in runs if one.game == "Absolum")
    assert [(one.name, one.login) for one in coop.people] == [
        ("ProfessorBurtch", "professorburtch"),
        ("threepup", "threepup"),
    ]
    assert len({one.external_id for one in runs}) == 24


def test_a_host_who_is_not_the_show_is_a_host_and_the_shows_other_blocks_are_their_own():
    blocks = {one.ref: one for one in hf.blocks_of(SHEET)}
    special = blocks["special-event/2026-09-25"]
    assert (special.first, special.last) == (date(2026, 9, 25), date(2026, 9, 27))
    assert ("ChurchnSarge", None, "host") in {
        (one.name, one.login, one.part) for one in special.runs[0].people
    }
    assert all(one.part == "runner" for run in gdqueer()[0].runs for one in run.people)


def test_a_block_weeks_later_is_a_second_block_of_the_same_show():
    later = SHEET + "\n11/14/2026,01:00:00 PM,GDQueer,GDQueer,Celeste,Any%,0:30:00,a,twitch.tv/a"
    blocks = hf.parse_hotfix(later, [" gdqueer "])
    assert [one.ref for one in blocks] == ["gdqueer/2026-10-03", "gdqueer/2026-11-14"]
    assert len(blocks[1].runs) == 1


def test_only_the_listed_shows_by_name_whatever_the_capitals():
    assert hf.parse_hotfix(SHEET, ["GDQUEER"])[0].ref == "gdqueer/2026-10-03"
    assert hf.parse_hotfix(SHEET, ["GDQ"]) == []
    assert [one.ref for one in hf.parse_hotfix(SHEET, ["Fast Travel"])] == [
        "fast-travel/2026-09-25"
    ]


def test_a_sheet_without_its_columns_is_refused_in_words():
    with pytest.raises(ScheduleError, match="Show Date, Show and Game"):
        hf.parse_hotfix("Date,Name\n10/3/2026,x\n", ["GDQueer"])


def test_the_shows_setting_reads_as_a_list():
    assert hf.shows_of(" GDQueer , gdqueer, Fast  Travel,, ") == ["GDQueer", "Fast Travel"]
    assert hf.shows_of("") == []


# --- the refs and the candidates --------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "ref"),
    [
        ("https://gamesdonequick.com/hotfix/schedule", ""),
        ("https://www.gamesdonequick.com/hotfix/schedule/", ""),
        ("https://gamesdonequick.com/hotfix/schedule#GDQueer", "gdqueer"),
        ("https://gamesdonequick.com/hotfix#Fast%20Travel", "fast-travel"),
        ("https://gamesdonequick.com/hotfix/schedule#gdqueer/2026-10-03", "gdqueer/2026-10-03"),
    ],
)
def test_the_hotfix_page_reads_as_a_ref(url, ref):
    assert hf.read_ref(url) == ref


def test_other_pages_are_not_the_hotfix_page():
    assert hf.read_ref("https://gamesdonequick.com/schedule/74") is None
    assert hf.read_ref("https://evil.example/hotfix/schedule") is None


def test_a_block_is_found_by_its_ref_and_a_bare_show_by_the_next_block():
    blocks = hf.blocks_of(SHEET)
    assert hf.block_for(blocks, "gdqueer/2026-10-03", SEPT).ref == "gdqueer/2026-10-03"
    assert hf.block_for(blocks, "gdqueer/2026-10-04", SEPT).ref == "gdqueer/2026-10-03"
    assert hf.block_for(blocks, "gdqueer", SEPT).ref == "gdqueer/2026-10-03"
    with pytest.raises(ScheduleError, match="after a #"):
        hf.block_for(blocks, "", SEPT)
    with pytest.raises(ScheduleError) as gone:
        hf.block_for(blocks, "gdqueer/2026-12-01", SEPT)
    assert gone.value.unpublished and "does not list gdqueer" in str(gone.value)


def test_candidates_are_the_blocks_not_over_named_by_the_show():
    found = hf.candidates(gdqueer(), SEPT, 1, set())
    assert [(one.ref, one.name, one.starts_at, one.ends_at, one.url) for one in found] == [
        (
            "gdqueer/2026-10-03",
            "GDQueer",
            "2026-10-03T17:00:00+00:00",
            "2026-10-05T03:09:00+00:00",
            "https://gamesdonequick.com/hotfix/schedule#gdqueer/2026-10-03",
        )
    ]
    assert hf.candidates(gdqueer(), datetime(2026, 10, 7, tzinfo=UTC), 1, set()) == []
    assert len(hf.candidates(gdqueer(), datetime(2026, 10, 5, 12, tzinfo=UTC), 1, set())) == 1


def test_a_name_already_taken_or_a_second_block_gets_its_month():
    taken = hf.candidates(gdqueer(), SEPT, 1, {"gdqueer"})
    assert taken[0].name == "GDQueer (Oct 2026)"
    later = SHEET + "\n11/14/2026,01:00:00 PM,GDQueer,GDQueer,Celeste,Any%,0:30:00,a,twitch.tv/a"
    names = [one.name for one in hf.candidates(hf.parse_hotfix(later, ["GDQueer"]), SEPT, 1, set())]
    assert names == ["GDQueer (Oct 2026)", "GDQueer (Nov 2026)"]


# --- the page, the sheet and the guard --------------------------------------------------------


def test_the_page_names_its_sheet_and_the_csv_keeps_the_tab():
    assert hf.sheet_url_of(PAGE_HTML) == CSV
    assert hf.sheet_url_of("<html><body>no sheet</body></html>") is None


async def test_a_read_asks_the_page_then_the_csv_it_built():
    fake = Fake({hf.PAGE: ok(PAGE_HTML), CSV: ok(SHEET, "text/csv")})
    text, url = await hf.read_sheet(fake, "agent", hf.PAGE)
    assert (text, url) == (SHEET, CSV)
    assert fake.asked == [hf.PAGE, CSV] and fake.agents == {"agent"}


async def test_google_sending_the_csv_to_its_content_host_is_followed():
    there = "https://doc-0s-4k-sheets.googleusercontent.com/pub/abc?output=csv"
    fake = Fake({hf.PAGE: ok(PAGE_HTML), CSV: Hop(307, there), there: ok(SHEET, "text/csv")})
    assert (await hf.read_sheet(fake, "agent"))[0] == SHEET
    assert fake.asked == [hf.PAGE, CSV, there]


@pytest.mark.parametrize(
    "elsewhere",
    [
        "https://evil.example/sheet.csv",
        "https://docs.google.com.evil.example/x",
        "http://docs.google.com/spreadsheets/d/e/x/pub",
        "https://googleusercontent.com.evil.example/x",
        "https://docs.google.com:8443/x",
        "http://169.254.169.254/latest/meta-data/",
        "https://drive.google.com/uc?id=x",
        "https://user:pw@docs.google.com/x",
    ],
)
async def test_a_hop_outside_the_allowlist_is_never_fetched(elsewhere):
    fake = Fake({hf.PAGE: ok(PAGE_HTML), CSV: Hop(302, elsewhere)})
    with pytest.raises(ScheduleError, match="does not fetch"):
        await hf.read_sheet(fake, "agent")
    assert fake.asked == [hf.PAGE, CSV]


async def test_a_page_with_no_sheet_is_a_failure_in_words():
    fake = Fake({hf.PAGE: ok("<html>the schedule moved</html>")})
    with pytest.raises(ScheduleError, match="no longer embeds a schedule sheet"):
        await hf.read_sheet(fake, "agent", hf.PAGE, CSV)
    assert fake.asked == [hf.PAGE]


async def test_a_page_hiccup_falls_back_to_the_last_good_sheet():
    fake = Fake({hf.PAGE: Hop(503), CSV: ok(SHEET, "text/csv")})
    assert await hf.read_sheet(fake, "agent", hf.PAGE, CSV) == (SHEET, CSV)
    assert fake.asked == [hf.PAGE, CSV]
    with pytest.raises(ScheduleError, match="answered 503"):
        await hf.read_sheet(Fake({hf.PAGE: Hop(503)}), "agent", hf.PAGE, None)


async def test_a_fallback_outside_the_allowlist_is_never_fetched():
    fake = Fake({hf.PAGE: Hop(503)})
    with pytest.raises(ScheduleError, match="answered 503"):
        await hf.read_sheet(fake, "agent", hf.PAGE, "https://evil.example/x.csv")
    assert fake.asked == [hf.PAGE]


async def test_too_big_unreachable_and_not_a_sheet_are_said_in_words():
    big = Fake({hf.PAGE: Hop(200, None, "text/html", b"", True)})
    with pytest.raises(ScheduleError, match="more than 1024 KB"):
        await hf.read_sheet(big, "agent")
    down = Fake({hf.PAGE: DocImportError(502, "doc_unreachable", "x")})
    with pytest.raises(ScheduleError, match="could not be reached"):
        await hf.read_sheet(down, "agent")
    wrong = Fake({hf.PAGE: ok(PAGE_HTML), CSV: ok("<html>sign in</html>")})
    with pytest.raises(ScheduleError, match="Show Date, Show and Game"):
        await hf.read_sheet(wrong, "agent")


async def test_the_client_reads_runs_and_resolves_a_bare_show_and_remembers_the_sheet():
    fake = Fake({hf.PAGE: ok(PAGE_HTML), CSV: ok(SHEET, "text/csv")})
    client = ScheduleClient(hop_request=fake)
    ref, name = await client.resolve(GDQ_HOTFIX, "gdqueer")
    assert (ref, name) == ("gdqueer/2026-10-03", "GDQueer")
    runs = await client.runs(GDQ_HOTFIX, ref)
    assert len(runs) == 24 and runs[0].game == "Spyro Reignited Trilogy"
    fake.answers[hf.PAGE] = Hop(500)
    assert len(await client.runs(GDQ_HOTFIX, ref)) == 24
    assert fake.asked[-2:] == [hf.PAGE, CSV]
    with pytest.raises(ScheduleError, match="after a #"):
        await client.resolve(GDQ_HOTFIX, "")


def test_the_sheet_reads_the_same_with_either_line_ending():
    lf = SHEET.replace("\r\n", "\n")
    crlf = lf.replace("\n", "\r\n")
    assert hf.parse_hotfix(lf, ["GDQueer"]) == hf.parse_hotfix(crlf, ["GDQueer"])
    assert len(hf.parse_hotfix(crlf, ["GDQueer"])[0].runs) == 24


# --- the show picker and the runner/host tracker -----------------------------------------------

ANARCHY = 501
MATHCAT = 502


def everywhere(name, user_id):
    return {"runner_name": name.lower(), "user_id": user_id, "marathon_id": None}


def matched(links=None, pairings=(), hosts=True):
    return {
        one.ref: hf.matched_of(one, links or {}, pairings, match_hosts=hosts)
        for one in hf.blocks_of(SHEET)
    }


def test_the_picker_reads_every_show_block_on_the_sheet_with_its_days_and_hosts():
    rows = hf.picker_rows(hf.blocks_of(SHEET), ["GDQueer"], {}, "America/Phoenix")
    assert len(rows) == 11
    assert len({one["show"] for one in rows}) == 11
    assert sum(len(one["days"]) for one in rows) == 14
    special = next(one for one in rows if one["show"] == "Special Event")
    assert [day["date"] for day in special["days"]] == ["2026-09-25", "2026-09-26", "2026-09-27"]
    heroes = next(one for one in rows if one["show"] == "Hidden Heroes")
    assert (heroes["ref"], heroes["hosts"], heroes["runs"]) == (
        "hidden-heroes/2026-10-02",
        ["anarchy"],
        3,
    )
    assert (heroes["starts_at"], heroes["starts_local"]) == (
        "2026-10-02T23:00:00+00:00",
        "Fri 2 Oct 16:00",
    )
    assert (heroes["listed"], heroes["tracked"], heroes["because"]) == (False, False, [])
    queer = next(one for one in rows if one["show"] == "GDQueer")
    assert (queer["hosts"], queer["tracked"], queer["because"]) == ([], True, [{"kind": "listed"}])


def test_anarchy_paired_everywhere_tracks_hidden_heroes_because_a_baf_person_hosts_it():
    people = matched(pairings=[everywhere("anarchy", ANARCHY)])
    chosen = hf.tracked(hf.blocks_of(SHEET), ["GDQueer"], people)
    assert [(block.ref, why) for block, why in chosen] == [
        (
            "hidden-heroes/2026-10-02",
            [{"kind": "hosts", "name": "anarchy", "user_id": ANARCHY}],
        ),
        ("gdqueer/2026-10-03", [{"kind": "listed"}]),
    ]
    assert hf.because_of(chosen[0][1]) == {"hosts": "anarchy"}
    assert hf.because_of(chosen[1][1]) == {}


def test_a_host_counts_only_while_hosts_count_as_people_and_is_always_scanned():
    people = matched(pairings=[everywhere("anarchy", ANARCHY)], hosts=False)
    assert hf.tracked(hf.blocks_of(SHEET), [], people) == []
    people = matched(pairings=[everywhere("anarchy", ANARCHY)], hosts=True)
    assert hf.tracked(hf.blocks_of(SHEET), [], people) != []


def test_a_pairing_made_for_one_marathon_does_not_track_a_show():
    pairing = {"runner_name": "anarchy", "user_id": ANARCHY, "marathon_id": 9}
    people = matched(pairings=[pairing])
    assert hf.tracked(hf.blocks_of(SHEET), [], people) == []


def test_mathcat_by_twitch_link_tracks_gdqueer_even_when_it_is_not_listed():
    people = matched(links={"the_mathcat": MATHCAT})
    chosen = hf.tracked(hf.blocks_of(SHEET), ["Fast Travel"], people)
    assert [(block.ref, why) for block, why in chosen] == [
        ("fast-travel/2026-09-25", [{"kind": "listed"}]),
        ("gdqueer/2026-10-03", [{"kind": "runs", "name": "The_Mathcat", "user_id": MATHCAT}]),
    ]


def test_the_name_rule_is_exact_so_a_mathcat_pairing_is_not_the_mathcat():
    blocks = hf.blocks_of(SHEET)
    assert hf.tracked(blocks, [], matched(pairings=[everywhere("mathcat", MATHCAT)])) == []
    chosen = hf.tracked(blocks, [], matched(pairings=[everywhere("The_Mathcat", MATHCAT)]))
    assert [block.ref for block, _ in chosen] == ["gdqueer/2026-10-03"]


def test_the_tracker_off_leaves_only_the_listed_shows():
    chosen = hf.tracked(hf.blocks_of(SHEET), ["GDQueer", "Hidden Heroes"], {})
    assert [block.ref for block, _ in chosen] == ["hidden-heroes/2026-10-02", "gdqueer/2026-10-03"]


def test_listed_and_a_person_on_the_same_block_is_one_candidate_with_both_reasons():
    people = matched(links={"the_mathcat": MATHCAT})
    chosen = hf.tracked(hf.blocks_of(SHEET), ["GDQueer"], people)
    assert chosen[0][1] == [
        {"kind": "listed"},
        {"kind": "runs", "name": "The_Mathcat", "user_id": MATHCAT},
    ]
    because = {block.ref: why for block, why in chosen}
    found = hf.candidates([block for block, _ in chosen], SEPT, 1, set(), because)
    assert [one.ref for one in found] == ["gdqueer/2026-10-03"]
    assert hf.because_of(found[0].because) == {}


def test_a_listed_name_the_sheet_does_not_hold_is_missing():
    blocks = hf.blocks_of(SHEET)
    assert hf.missing_shows(blocks, ["GDQueer", "Speedrun Sandwich"]) == ["Speedrun Sandwich"]


def test_the_sheet_cache_is_fresh_for_five_minutes():
    cache = hf.SheetCache()
    assert not cache.fresh(SEPT)
    cache.keep(SHEET, CSV, SEPT)
    assert cache.fresh(SEPT.replace(minute=4))
    assert not cache.fresh(SEPT.replace(minute=5))
    owner = type("Owner", (), {})()
    assert hf.cache_of(owner) is hf.cache_of(owner)
