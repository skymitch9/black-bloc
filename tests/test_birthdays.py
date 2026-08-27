from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from black_bloc.birthdays import (
    DATA_FILE,
    DESCRIPTION_LIMIT,
    FALLBACK_ZONE,
    ImportRow,
    age,
    celebrates_today,
    clamp_month_day,
    date_problem,
    import_as_of_year,
    load_import_rows,
    local_today,
    member_zone_name,
    month_day_text,
    next_occurrence,
    observed,
    parse_color,
    parse_export,
    render_description,
    resolve,
    score_member,
    score_members,
    stamp,
    strip_tags,
    upcoming,
    year_from_age,
    year_problem,
)
from black_bloc.settings_store import BIRTHDAY_TEMPLATE, BIRTHDAY_TZ
from black_bloc.storage.db import Database

PHOENIX = ZoneInfo(BIRTHDAY_TZ)
NEW_YORK = ZoneInfo("America/New_York")
TOKYO = ZoneInfo("Asia/Tokyo")

SAMPLE_EXPORT = """
| Month | Day | Display name (as exported) | Age shown |
|---|---|---|---|
| January | 2 | [Straight Hands] ShinDarkShadow | |
| August | 10 | [Tired of Planes] PT | 39 |
| July | 26 | (Umazing) nadia | |
| December | 12 | milkywaymatcha | |
| December | 12 | nbobbit | |
| Smarch | 4 | nobody | |
"""


class FakeMember:
    def __init__(self, user_id, display_name, username=None):
        self.id = user_id
        self.display_name = display_name
        self.name = username or display_name


def test_clamp_keeps_every_pair_inside_a_real_calendar():
    assert clamp_month_day(2, 29) == (2, 29)
    assert clamp_month_day(2, 30) == (2, 29)
    assert clamp_month_day(13, 40) == (12, 31)
    assert clamp_month_day(0, 0) == (1, 1)
    assert clamp_month_day(4, 31) == (4, 30)
    assert clamp_month_day("nope", 1) == (1, 1)


def test_impossible_dates_are_refused_with_a_sentence_not_clamped():
    assert date_problem(6, 17) is None
    assert date_problem(2, 29) is None
    assert "no day" in date_problem(2, 30)
    assert "no month" in date_problem(13, 1)
    assert date_problem("x", 1).startswith("A birthday needs")


def test_the_birth_year_is_bounded():
    today = date(2026, 8, 26)
    assert year_problem(None, today) is None
    assert year_problem(1994, today) is None
    assert "not a birth year" in year_problem(2027, today)
    assert "not a birth year" in year_problem(1899, today)
    assert "whole number" in year_problem("soon", today)


def test_february_29_is_observed_on_the_28th_in_ordinary_years():
    assert observed(2, 29, 2024) == (2, 29)
    assert observed(2, 29, 2026) == (2, 28)
    assert observed(3, 1, 2026) == (3, 1)
    assert celebrates_today(2, 29, date(2026, 2, 28))
    assert not celebrates_today(2, 29, date(2026, 3, 1))
    assert celebrates_today(2, 29, date(2024, 2, 29))
    assert not celebrates_today(2, 29, date(2024, 2, 28))


def test_next_occurrence_is_local_midnight_and_rolls_into_next_year():
    now = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    when = next_occurrence(12, 24, PHOENIX, now)
    assert when == datetime(2026, 12, 24, 0, 0, tzinfo=PHOENIX)

    passed = next_occurrence(1, 2, PHOENIX, now)
    assert passed == datetime(2027, 1, 2, 0, 0, tzinfo=PHOENIX)

    today = next_occurrence(8, 26, PHOENIX, now)
    assert today == datetime(2026, 8, 26, 0, 0, tzinfo=PHOENIX)


def test_next_occurrence_of_a_leap_day_lands_on_the_28th_in_ordinary_years():
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    assert next_occurrence(2, 29, PHOENIX, now) == datetime(2026, 2, 28, 0, 0, tzinfo=PHOENIX)
    leap = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    assert next_occurrence(2, 29, PHOENIX, leap) == datetime(2024, 2, 29, 0, 0, tzinfo=PHOENIX)


def test_a_utc_minus_four_member_celebrates_the_evening_before_in_phoenix():
    moment = datetime(2026, 8, 10, 4, 30, tzinfo=UTC)

    assert local_today(NEW_YORK, moment) == date(2026, 8, 10)
    assert local_today(PHOENIX, moment) == date(2026, 8, 9)
    assert celebrates_today(8, 10, local_today(NEW_YORK, moment))
    assert not celebrates_today(8, 10, local_today(PHOENIX, moment))


def test_a_member_east_of_utc_celebrates_before_everyone_else():
    moment = datetime(2026, 8, 9, 15, 30, tzinfo=UTC)
    assert local_today(TOKYO, moment) == date(2026, 8, 10)
    assert celebrates_today(8, 10, local_today(TOKYO, moment))
    assert not celebrates_today(8, 10, local_today(PHOENIX, moment))


def test_an_unusable_zone_name_falls_back_to_the_server_zone():
    moment = datetime(2026, 8, 10, 4, 30, tzinfo=UTC)
    assert local_today("Mars/Olympus", moment) == local_today(PHOENIX, moment)
    assert local_today(None, moment) == local_today(PHOENIX, moment)
    assert FALLBACK_ZONE.utcoffset(None).total_seconds() == -7 * 3600


def test_age_is_the_years_they_turn_this_year():
    today = date(2026, 8, 26)
    assert age(1994, today) == 32
    assert age(None, today) is None
    assert age("", today) is None
    assert age("nope", today) is None
    assert age(2030, today) is None
    ahead = next_occurrence(1, 2, PHOENIX, datetime(2026, 8, 26, 12, 0, tzinfo=UTC))
    assert age(1990, ahead.date()) == 37
    assert age(1990, today) == 36
    assert year_from_age(39, 2026) == 1987
    assert year_from_age(None, 2026) is None
    assert year_from_age(-2, 2026) is None


def test_the_colour_falls_back_when_it_is_not_a_hex_code():
    assert parse_color("#4eefff") == 0x4EEFFF
    assert parse_color("4eefff") == 0x4EEFFF
    assert parse_color("blue") == 0x4EEFFF
    assert parse_color(None) == 0x4EEFFF


def test_a_broken_template_falls_back_to_the_default_wording():
    assert render_description(BIRTHDAY_TEMPLATE, "PT") == "Happy Birthday **PT**!"
    assert render_description("{name} turns {age}!", "PT", 39) == "PT turns 39!"
    assert render_description("{nope}", "PT") == "Happy Birthday **PT**!"
    assert "@everyone" in render_description(BIRTHDAY_TEMPLATE, "@everyone")
    assert len(render_description("{name}", "x" * 5000)) == DESCRIPTION_LIMIT


def test_bracket_and_paren_prefixes_are_stripped():
    assert strip_tags("[Straight Hands] ShinDarkShadow") == "ShinDarkShadow"
    assert strip_tags("(Umazing) nadia") == "nadia"
    assert strip_tags("[40] PT") == "PT"
    assert strip_tags("[Canadian] PopNoTartsEh 🇨🇦") == "PopNoTartsEh 🇨🇦"
    assert strip_tags("itsmeowkie") == "itsmeowkie"
    assert strip_tags("[all tag]") == "[all tag]"


def test_scoring_is_three_two_one():
    assert score_member("PT", "PT", "pt_the_pilot") == 3
    assert score_member("PT", "Something", "pt") == 2
    assert score_member("PT", "Something", "someone", "pt") == 2
    assert score_member("PT", "[40] PT", "someone") == 2
    assert score_member("PT", "PTolemy", "someone") == 1
    assert score_member("PT", "nobody", "nobody") == 0
    assert score_member("", "PT", "PT") == 0
    assert score_member("pt", "PT", "x") == 3


def test_a_tagged_nickname_is_matched_on_the_name_inside_the_tag():
    row = ImportRow("[Straight Hands] ShinDarkShadow", 1, 2, None)
    tagged = FakeMember(11, "[Straight Hands] ShinDarkShadow", "shin_dark")
    assert score_member("ShinDarkShadow", tagged.display_name, tagged.name) == 2
    assert resolve(row, [tagged]).member_id == 11


def test_a_unique_best_of_two_or_more_imports_and_everything_else_is_reported():
    row = ImportRow("[Tired of Planes] PT", 8, 10, 39)

    matched = resolve(row, [FakeMember(1, "PT"), FakeMember(2, "PTolemy")])
    assert matched.status == "matched" and matched.member_id == 1

    by_username = resolve(row, [FakeMember(3, "Peaches", "pt")])
    assert by_username.status == "matched" and by_username.member_id == 3

    ambiguous = resolve(row, [FakeMember(4, "PT"), FakeMember(5, "PT")])
    assert ambiguous.status == "ambiguous" and len(ambiguous.candidates) == 2
    assert ambiguous.member_id is None

    tagged = resolve(row, [FakeMember(6, "[40] PT")])
    assert tagged.status == "matched" and tagged.member_id == 6

    weak = resolve(row, [FakeMember(10, "PTolemy")])
    assert weak.status == "ambiguous" and weak.candidates[0].user_id == 10

    assert resolve(row, [FakeMember(7, "nobody")]).status == "not_found"
    assert resolve(row, []).status == "not_found"


def test_the_paren_shape_resolves_the_same_way():
    row = ImportRow("(Umazing) nadia", 7, 26, None)
    assert resolve(row, [FakeMember(8, "nadia"), FakeMember(9, "nadja")]).member_id == 8


def test_candidates_come_back_best_first():
    hits = score_members("PT", [FakeMember(1, "[40] PT"), FakeMember(2, "PT")])
    assert [c.user_id for c in hits] == [2, 1]
    assert [c.score for c in hits] == [3, 2]


def test_the_export_parser_reads_the_table_and_splits_a_shared_day():
    rows = parse_export(SAMPLE_EXPORT)
    assert [(r.month, r.day) for r in rows] == [(1, 2), (8, 10), (7, 26), (12, 12), (12, 12)]
    assert rows[1].age_shown == 39
    assert rows[0].age_shown is None
    assert rows[3].display_name == "milkywaymatcha" and rows[4].display_name == "nbobbit"
    assert parse_export("") == []


def test_the_shipped_seed_file_is_the_thirty_nine_row_export():
    rows = load_import_rows()
    assert len(rows) == 39
    assert import_as_of_year() == 2026
    assert [r.display_name for r in rows if r.month == 12 and r.day == 12] == [
        "milkywaymatcha",
        "nbobbit",
    ]
    pt = next(r for r in rows if r.display_name == "[Tired of Planes] PT")
    assert (pt.month, pt.day, pt.age_shown) == (8, 10, 39)
    assert year_from_age(pt.age_shown, import_as_of_year()) == 1987
    assert all(date_problem(r.month, r.day) is None for r in rows)
    assert DATA_FILE.exists()


def test_an_unreadable_seed_file_is_no_rows_not_a_crash(tmp_path):
    assert load_import_rows(tmp_path / "missing.json") == []
    broken = tmp_path / "broken.json"
    broken.write_text('{"exported": "2026-08-05", "rows": [{"day": 1}]}', encoding="utf-8")
    assert load_import_rows(broken) == []
    assert import_as_of_year(broken) == 2026


def test_upcoming_orders_by_the_next_local_midnight():
    now = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    entries = [
        {"user_id": 1, "month": 12, "day": 24, "tz": BIRTHDAY_TZ, "year": 2002},
        {"user_id": 2, "month": 9, "day": 3, "tz": BIRTHDAY_TZ, "year": None},
        {"user_id": 3, "month": 1, "day": 2, "tz": BIRTHDAY_TZ, "year": None},
        {"user_id": 4, "month": 8, "day": 26, "tz": BIRTHDAY_TZ, "year": None},
    ]

    order = [u.user_id for u in upcoming(entries, now, limit=3)]

    assert order == [4, 2, 1]
    assert len(upcoming(entries, now, limit=0)) == 4
    assert stamp(next_occurrence(9, 3, PHOENIX, now)) == (
        f"<t:{int(datetime(2026, 9, 3, tzinfo=PHOENIX).timestamp())}:D>"
    )


def test_month_day_reads_as_words():
    assert month_day_text(9, 3) == "September 3"
    assert month_day_text(99, 99) == "December 31"


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "b.sqlite3")
    await database.connect()
    try:
        yield database
    finally:
        await database.close()


async def test_the_zone_lookup_prefers_the_member_s_own_zone(db):
    assert await member_zone_name(db, 5) == BIRTHDAY_TZ

    await db.conn.execute(
        "INSERT INTO user_timezones(user_id, tz, set_at) VALUES (5, 'America/New_York', 'now')"
    )
    await db.conn.commit()

    assert await member_zone_name(db, 5) == "America/New_York"
    assert await member_zone_name(db, 6) == BIRTHDAY_TZ


async def test_a_database_that_cannot_answer_still_gives_a_zone():
    class Broken:
        @property
        def conn(self):
            raise RuntimeError("not connected")

    assert await member_zone_name(Broken(), 1) == BIRTHDAY_TZ
