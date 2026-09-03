import pytest

from black_bloc import requests as pure
from black_bloc.storage.db import Database

GUILD = 7
OTHER_GUILD = 8
ASKER = 900
STAFFER = 901


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "r.sqlite3")
    await database.connect()
    try:
        yield database
    finally:
        await database.close()


async def file_one(db, **kwargs):
    fields = {
        "what": "a request board",
        "why": "the google doc is a mess",
        "due_on": None,
    } | kwargs
    guild_id = fields.pop("guild_id", GUILD)
    user_id = fields.pop("user_id", ASKER)
    return await pure.create_request(db, guild_id, user_id, **fields)


def test_a_due_date_is_the_shape_it_says_or_a_sentence():
    assert pure.parse_due("2026-09-15") == "2026-09-15"
    assert pure.parse_due("") is None
    assert pure.parse_due(None) is None
    assert pure.parse_due("  2026-09-15 ") == "2026-09-15"
    with pytest.raises(pure.RequestError) as caught:
        pure.parse_due("15/09/2026")

    assert "YYYY-MM-DD" in str(caught.value)
    assert "15/09/2026" in str(caught.value)


def test_a_date_that_is_not_a_day_is_refused_rather_than_rounded():
    for given in ("2026-13-01", "2026-02-30", "next tuesday"):
        with pytest.raises(pure.RequestError):
            pure.parse_due(given)


def test_a_due_date_reads_back_as_a_hammertime_stamp_each_reader_sees_in_their_own_clock():
    stamp = pure.due_stamp("2026-09-15")

    assert stamp is not None and stamp.startswith("<t:") and stamp.endswith(":D>")
    assert pure.due_stamp(None) is None
    assert pure.due_stamp("not a date") is None


def test_the_due_stamp_is_local_midnight_in_the_servers_zone_not_utc():
    """Phoenix is UTC-7 all year, so local midnight is 07:00 UTC — never the day before."""
    from datetime import UTC, datetime

    stamp = pure.due_stamp("2026-09-15")
    at = datetime.fromtimestamp(int(stamp[3:-3]), UTC)

    assert (at.hour, at.minute) == (7, 0)
    assert at.date().isoformat() == "2026-09-15"
    assert pure.due_stamp("2026-09-15", "Europe/London") != stamp


def test_a_stored_due_date_stays_a_plain_date_and_never_becomes_an_instant():
    assert pure.parse_due("2026-09-15") == "2026-09-15"
    assert "T" not in pure.parse_due("2026-09-15")


def test_the_three_fields_are_refused_in_the_order_a_person_meets_them():
    what, why, due = pure.checked_fields(" a board ", " the doc is a mess ", "2026-09-15")

    assert (what, why, due) == ("a board", "the doc is a mess", "2026-09-15")
    with pytest.raises(pure.RequestError) as no_what:
        pure.checked_fields("   ", "", "")
    with pytest.raises(pure.RequestError) as no_why:
        pure.checked_fields("a board", "  ", "")

    assert "what you are asking for" in str(no_what.value)
    assert "why it is worth doing" in str(no_why.value)


def test_what_and_why_are_cut_to_the_length_the_modal_takes():
    what, why, _ = pure.checked_fields("a" * 2000, "b" * 2000, "")

    assert len(what) == pure.WHAT_LIMIT
    assert len(why) == pure.WHY_LIMIT


def test_a_priority_is_a_small_whole_number_or_a_sentence():
    assert pure.wanted_priority(None) is None
    assert pure.wanted_priority("") is None
    assert pure.wanted_priority(3) == 3
    assert pure.wanted_priority("0") == 0
    for bad in ("high", -1, pure.PRIORITY_MAX + 1, True):
        with pytest.raises(pure.RequestError):
            pure.wanted_priority(bad)


def test_only_the_states_staff_can_set_are_settable():
    assert pure.wanted_status("hold") == "hold"
    assert pure.wanted_status(" DONE ") == "done"
    for bad in ("open", "withdrawn", "approved", "planned", "pending", "shipped", ""):
        with pytest.raises(pure.RequestError):
            pure.wanted_status(bad)


def test_one_table_says_where_a_request_may_go_and_every_path_asks_it():
    """`TRANSITIONS` is the whole machine; the helpers only read it."""
    assert pure.moves_from(pure.OPEN) == ("declined", "hold", "in_progress")
    assert pure.moves_from(pure.IN_PROGRESS) == ("declined", "done", "hold")
    assert pure.moves_from(pure.HOLD) == ("declined", "in_progress")
    assert pure.moves_from(pure.DONE) == ()
    assert pure.moves_from(pure.DECLINED) == ()
    assert pure.moves_from(pure.WITHDRAWN) == ()
    assert pure.can_move(pure.OPEN, pure.DONE) is False
    assert pure.can_move(pure.HOLD, pure.IN_PROGRESS) is True
    assert pure.FINAL_STATUSES == (pure.DONE, pure.DECLINED, pure.WITHDRAWN)


def test_a_refused_move_says_which_moves_are_allowed_from_where_it_is():
    with pytest.raises(pure.RequestError) as caught:
        pure.checked_move(4, pure.OPEN, pure.DONE)

    said = str(caught.value)
    assert "**open**" in said and "**done**" in said
    assert "in_progress" in said and "hold" in said

    with pytest.raises(pure.RequestError) as final:
        pure.checked_move(4, pure.DONE, pure.HOLD, "a reason")

    assert "finishes" in str(final.value)


def test_a_move_into_hold_or_declined_needs_the_sentence_the_person_is_sent():
    for wanted in (pure.HOLD, pure.DECLINED):
        with pytest.raises(pure.RequestError) as caught:
            pure.checked_move(4, pure.OPEN, wanted, "  ")
        assert "the person who asked is sent" in str(caught.value)
    assert pure.checked_move(4, pure.OPEN, pure.HOLD, "waiting on the bill") == pure.HOLD
    assert pure.checked_move(4, pure.OPEN, pure.IN_PROGRESS) == pure.IN_PROGRESS


def test_moving_a_row_to_where_it_already_is_says_so():
    with pytest.raises(pure.RequestError) as caught:
        pure.checked_move(4, pure.IN_PROGRESS, pure.IN_PROGRESS)

    assert "already" in str(caught.value)


def test_a_filter_of_no_statuses_means_every_one_and_an_unknown_one_is_refused():
    assert pure.wanted_statuses("") == pure.STATUSES
    assert pure.wanted_statuses("open,done") == ("open", "done")
    with pytest.raises(pure.RequestError):
        pure.wanted_statuses("open,shipped")
    for retired in ("pending", "approved", "planned"):
        with pytest.raises(pure.RequestError):
            pure.wanted_statuses(retired)


def test_a_page_that_is_past_the_end_shows_the_last_one_rather_than_nothing():
    rows = list(range(25))

    assert pure.page_of(rows, 1, 10) == (rows[:10], 1, 3)
    assert pure.page_of(rows, 3, 10) == (rows[20:], 3, 3)
    assert pure.page_of(rows, 99, 10) == (rows[20:], 3, 3)
    assert pure.page_of(rows, 0, 10) == (rows[:10], 1, 3)
    assert pure.page_of([], 1, 10) == ([], 1, 1)


async def test_a_filed_request_starts_open_with_nobody_having_decided(db):
    request_id = await file_one(db, due_on="2026-09-15")
    row = await pure.get_request(db, request_id)

    assert row["status"] == pure.OPEN
    assert row["decided_by"] is None and row["decided_at"] is None
    assert row["held_from"] is None
    assert row["due_on"] == "2026-09-15"
    assert row["created_at"]


async def test_the_list_puts_open_first_and_then_the_newest(db):
    old = await file_one(db, what="old one")
    middle = await file_one(db, what="middle one")
    fresh = await file_one(db, what="fresh one")
    await pure.set_status(db, fresh, pure.IN_PROGRESS, decided_by=STAFFER)
    await pure.set_status(db, old, pure.IN_PROGRESS, decided_by=STAFFER)

    rows = await pure.list_requests(db, GUILD)

    assert [row["id"] for row in rows] == [middle, fresh, old]


async def test_a_list_never_reaches_into_another_server(db):
    mine = await file_one(db)
    await file_one(db, guild_id=OTHER_GUILD)

    rows = await pure.list_requests(db, GUILD)

    assert [row["id"] for row in rows] == [mine]
    assert await pure.count_requests(db, GUILD) == 1


async def test_a_list_filters_by_status_by_asker_by_assignee_and_by_words(db):
    mine = await file_one(db, what="a request board", why="the doc is a mess")
    theirs = await file_one(db, user_id=STAFFER, what="a karaoke night", why="it is fun")
    await pure.set_status(db, theirs, pure.IN_PROGRESS, decided_by=STAFFER)
    await pure.set_fields(db, theirs, assignee_id=STAFFER)

    assert [r["id"] for r in await pure.list_requests(db, GUILD, statuses=(pure.OPEN,))] == [
        mine
    ]
    assert [r["id"] for r in await pure.list_requests(db, GUILD, user_id=STAFFER)] == [theirs]
    assert [r["id"] for r in await pure.list_requests(db, GUILD, assignee_id=STAFFER)] == [theirs]
    assert [r["id"] for r in await pure.list_requests(db, GUILD, query="karaoke")] == [theirs]
    assert await pure.count_requests(db, GUILD, query="karaoke") == 1


async def test_the_unassigned_column_asks_for_assignee_none(db):
    mine = await file_one(db, what="nobody has this")
    theirs = await file_one(db, what="somebody has this")
    await pure.set_fields(db, theirs, assignee_id=STAFFER)

    rows = await pure.list_requests(db, GUILD, assignee_id=pure.UNASSIGNED)

    assert [row["id"] for row in rows] == [mine]
    assert await pure.count_requests(db, GUILD, assignee_id=pure.UNASSIGNED) == 1


async def test_a_search_can_also_match_on_ids_the_caller_resolved_from_names(db):
    theirs = await file_one(db, user_id=STAFFER, what="a karaoke night", why="it is fun")
    await file_one(db, what="a request board", why="the doc is a mess")

    rows = await pure.list_requests(db, GUILD, query="lead", named=[STAFFER])

    assert [row["id"] for row in rows] == [theirs]
    assert await pure.list_requests(db, GUILD, query="lead", named=[]) == []


async def test_a_search_reads_the_notes_as_well_as_the_what_and_the_why(db):
    request_id = await file_one(db)
    await pure.set_fields(db, request_id, notes="waiting on the hosting bill")

    assert [r["id"] for r in await pure.list_requests(db, GUILD, query="hosting")] == [request_id]


async def test_a_page_of_the_list_is_asked_for_in_sql_not_sliced_afterwards(db):
    for number in range(5):
        await file_one(db, what=f"one {number}")

    first = await pure.list_requests(db, GUILD, limit=2, offset=0)
    second = await pure.list_requests(db, GUILD, limit=2, offset=2)

    assert len(first) == 2 and len(second) == 2
    assert {row["id"] for row in first} & {row["id"] for row in second} == set()


async def test_moving_to_done_stamps_when_and_moving_off_declined_forgets_the_reason(db):
    request_id = await file_one(db)
    await pure.set_status(db, request_id, pure.DECLINED, decided_by=STAFFER, decline_reason="no")
    declined = await pure.get_request(db, request_id)

    assert declined["decline_reason"] == "no" and declined["done_at"] is None

    await pure.set_status(db, request_id, pure.DONE, decided_by=STAFFER)
    done = await pure.get_request(db, request_id)

    assert done["done_at"] and done["decline_reason"] is None


async def test_a_decision_that_names_nobody_leaves_the_first_deciders_name_alone(db):
    request_id = await file_one(db)
    await pure.set_status(db, request_id, pure.IN_PROGRESS, decided_by=STAFFER)
    await pure.set_status(db, request_id, pure.DONE)
    row = await pure.get_request(db, request_id)

    assert row["decided_by"] == STAFFER


async def test_held_from_is_written_on_the_way_in_and_cleared_on_the_way_out(db):
    request_id = await file_one(db)
    await pure.set_status(db, request_id, pure.IN_PROGRESS, decided_by=STAFFER)
    await pure.set_status(
        db,
        request_id,
        pure.HOLD,
        decided_by=STAFFER,
        decline_reason="the bill",
        was=pure.IN_PROGRESS,
    )
    parked = await pure.get_request(db, request_id)

    assert parked["held_from"] == pure.IN_PROGRESS
    assert parked["decline_reason"] == "the bill"
    assert pure.held_words(parked) == "being worked on"
    assert pure.resume_target(parked) == pure.IN_PROGRESS
    assert "was: being worked on" in pure.summary_line(parked)

    await pure.set_status(db, request_id, pure.IN_PROGRESS, decided_by=STAFFER)
    back = await pure.get_request(db, request_id)

    assert back["held_from"] is None and back["decline_reason"] is None


async def test_a_hold_that_came_from_open_resumes_into_progress_rather_than_back_to_open(db):
    request_id = await file_one(db)
    await pure.set_status(
        db, request_id, pure.HOLD, decided_by=STAFFER, decline_reason="waiting", was=pure.OPEN
    )
    row = await pure.get_request(db, request_id)

    assert row["held_from"] == pure.OPEN
    assert pure.resume_target(row) == pure.IN_PROGRESS


async def test_only_the_fields_actually_sent_are_written(db):
    request_id = await file_one(db)
    await pure.set_fields(db, request_id, priority=2)
    await pure.set_fields(db, request_id, notes="soon")
    row = await pure.get_request(db, request_id)

    assert row["priority"] == 2 and row["notes"] == "soon" and row["assignee_id"] is None
    assert await pure.set_fields(db, request_id) == []


async def test_a_field_can_be_cleared_again_by_sending_it_as_nothing(db):
    request_id = await file_one(db)
    await pure.set_fields(db, request_id, assignee_id=STAFFER, priority=1)
    await pure.set_fields(db, request_id, assignee_id=None, priority=None)
    row = await pure.get_request(db, request_id)

    assert row["assignee_id"] is None and row["priority"] is None


async def test_comments_come_back_oldest_first_and_are_counted_per_request(db):
    first = await file_one(db)
    second = await file_one(db)
    await pure.add_comment(db, first, STAFFER, "looking at it")
    await pure.add_comment(db, first, ASKER, "thank you")
    await pure.add_comment(db, second, STAFFER, "next week")

    rows = await pure.comments_for(db, first)

    assert [row["text"] for row in rows] == ["looking at it", "thank you"]
    assert await pure.comment_counts(db, [first, second]) == {first: 2, second: 1}
    assert await pure.comment_counts(db, []) == {}


async def test_the_open_count_is_what_the_sidebar_badge_reads(db):
    await file_one(db)
    second = await file_one(db)
    await pure.set_status(db, second, pure.IN_PROGRESS, decided_by=STAFFER)

    assert await pure.open_count(db, GUILD) == 1


async def test_the_notice_message_id_is_kept_so_the_line_can_be_found_again(db):
    request_id = await file_one(db)
    await pure.set_message(db, request_id, 4242)

    assert (await pure.get_request(db, request_id))["message_id"] == 4242


async def test_a_summary_line_names_the_number_the_state_and_the_deadline(db):
    request_id = await file_one(db, due_on="2026-09-15")
    line = pure.summary_line(await pure.get_request(db, request_id))

    assert f"#{request_id}" in line
    assert "open" in line
    assert "<t:" in line
