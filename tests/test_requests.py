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
    assert pure.moves_from(pure.IN_PROGRESS) == ("declined", "hold", "review")
    assert pure.moves_from(pure.REVIEW) == ("declined", "done", "hold", "in_progress")
    assert pure.moves_from(pure.HOLD) == ("declined", "in_progress", "review")
    assert pure.moves_from(pure.DONE) == ()
    assert pure.moves_from(pure.DECLINED) == ()
    assert pure.moves_from(pure.WITHDRAWN) == ()
    assert pure.can_move(pure.OPEN, pure.DONE) is False
    assert pure.can_move(pure.HOLD, pure.IN_PROGRESS) is True
    assert pure.FINAL_STATUSES == (pure.DONE, pure.DECLINED, pure.WITHDRAWN)


def test_done_is_reachable_only_from_review_and_nothing_else_reaches_it():
    """Owner, 2026-09-03: an acceptance step, so every done card has substance behind it."""
    for where in (pure.OPEN, pure.IN_PROGRESS, pure.HOLD):
        assert pure.can_move(where, pure.DONE) is False
    assert pure.can_move(pure.REVIEW, pure.DONE) is True
    assert [one for one in pure.TRANSITIONS if pure.DONE in pure.TRANSITIONS[one]] == [pure.REVIEW]


def test_a_request_being_checked_cannot_be_taken_back_by_the_person_who_asked():
    assert pure.WITHDRAWABLE == (pure.OPEN, pure.HOLD)
    assert pure.REVIEW not in pure.WITHDRAWABLE


def test_a_refused_move_says_which_moves_are_allowed_from_where_it_is():
    with pytest.raises(pure.RequestError) as caught:
        pure.checked_move(4, pure.OPEN, pure.REVIEW, built="a thing")

    said = str(caught.value)
    assert "**open**" in said and "**review**" in said
    assert "in_progress" in said and "hold" in said

    with pytest.raises(pure.RequestError) as final:
        pure.checked_move(4, pure.DONE, pure.HOLD, "a reason")

    assert "finishes" in str(final.value)


def test_asking_for_done_from_a_live_state_names_the_ready_step_rather_than_the_table():
    for where in (pure.OPEN, pure.IN_PROGRESS, pure.HOLD):
        with pytest.raises(pure.RequestError) as caught:
            pure.checked_move(4, where, pure.DONE)
        said = str(caught.value)
        assert "checked it" in said
        assert "/request ready 4" in said and "Ready to check" in said


def test_a_finished_request_still_says_it_is_finished_rather_than_offering_the_ready_step():
    with pytest.raises(pure.RequestError) as caught:
        pure.checked_move(4, pure.DECLINED, pure.DONE)

    assert "finishes" in str(caught.value)


def test_entering_review_needs_the_line_saying_what_was_built():
    for blank in ("", "   ", None):
        with pytest.raises(pure.RequestError) as caught:
            pure.checked_move(4, pure.IN_PROGRESS, pure.REVIEW, built=blank)
        assert "what was actually built" in str(caught.value)
    assert pure.checked_move(4, pure.IN_PROGRESS, pure.REVIEW, built="the board") == pure.REVIEW


def test_sending_one_back_needs_the_line_saying_what_is_still_to_do():
    for blank in ("", "   ", None):
        with pytest.raises(pure.RequestError) as caught:
            pure.checked_move(4, pure.REVIEW, pure.IN_PROGRESS, note=blank)
        assert "what is still to do" in str(caught.value)
    assert pure.checked_move(4, pure.REVIEW, pure.IN_PROGRESS, note="the CSV") == pure.IN_PROGRESS


def test_picking_a_fresh_request_up_needs_no_note_because_it_is_not_a_send_back():
    assert pure.checked_move(4, pure.OPEN, pure.IN_PROGRESS) == pure.IN_PROGRESS
    assert pure.look_of(pure.OPEN, pure.IN_PROGRESS) == pure.IN_PROGRESS
    assert pure.look_of(pure.REVIEW, pure.IN_PROGRESS) == pure.SENT_BACK
    assert pure.look_of(pure.IN_PROGRESS, pure.REVIEW) == pure.REVIEW


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


async def test_the_ready_move_stamps_who_marked_it_and_forgets_the_last_send_back(db):
    request_id = await file_one(db)
    await pure.set_fields(db, request_id, built="a board", how_to_test="press it")
    await pure.set_status(
        db, request_id, pure.REVIEW, decided_by=STAFFER, was=pure.IN_PROGRESS, ready_by=STAFFER
    )
    row = await pure.get_request(db, request_id)

    assert row["status"] == pure.REVIEW and row["ready_by"] == STAFFER
    assert row["built"] == "a board" and row["how_to_test"] == "press it"
    assert row["sent_back_reason"] is None


async def test_a_send_back_writes_its_note_and_keeps_who_marked_it_ready(db):
    request_id = await file_one(db)
    await pure.set_status(
        db, request_id, pure.REVIEW, decided_by=STAFFER, was=pure.IN_PROGRESS, ready_by=STAFFER
    )
    await pure.set_status(
        db,
        request_id,
        pure.IN_PROGRESS,
        decided_by=ASKER,
        was=pure.REVIEW,
        sent_back_reason="the CSV is missing",
    )
    row = await pure.get_request(db, request_id)

    assert row["status"] == pure.IN_PROGRESS
    assert row["sent_back_reason"] == "the CSV is missing"
    assert row["ready_by"] == STAFFER


async def test_a_hold_taken_from_review_resumes_back_into_review(db):
    request_id = await file_one(db)
    await pure.set_status(
        db, request_id, pure.REVIEW, decided_by=STAFFER, was=pure.IN_PROGRESS, ready_by=STAFFER
    )
    await pure.set_status(
        db, request_id, pure.HOLD, decided_by=STAFFER, decline_reason="waiting", was=pure.REVIEW
    )
    row = await pure.get_request(db, request_id)

    assert row["held_from"] == pure.REVIEW
    assert pure.resume_target(row) == pure.REVIEW


async def test_built_and_how_to_test_are_editable_afterwards_without_a_state_change(db):
    request_id = await file_one(db)
    await pure.set_fields(db, request_id, built="a board", how_to_test="press it")
    changed = await pure.set_fields(db, request_id, how_to_test="press it twice")
    row = await pure.get_request(db, request_id)

    assert changed == ["how_to_test"]
    assert row["built"] == "a board" and row["how_to_test"] == "press it twice"
    assert row["status"] == pure.OPEN


CARD_ROW = {
    "id": 7,
    "what": "a request board",
    "why": "the google doc is a mess",
    "due_on": "2026-09-15",
    "user_id": ASKER,
    "assignee_id": STAFFER,
    "built": "the board, with a CSV export",
    "how_to_test": "open /requests and press Export",
    "ready_by": STAFFER,
    "decided_by": 902,
    "sent_back_reason": "the CSV has no header row",
    "decline_reason": "we already have one",
    "held_from": pure.IN_PROGRESS,
    "created_at": "2026-09-03T01:00:00+00:00",
    "decided_at": "2026-09-03T02:00:00+00:00",
    "check_asked_by": STAFFER,
    "check_asked_at": "2026-09-03T02:30:00+00:00",
}

CARD_FIELDS = {
    pure.FILED_LOOK: ["Asked for", "Why", "Requested by", "Due"],
    pure.IN_PROGRESS: ["Asked for", "Requested by", "Assignee"],
    pure.REVIEW: [
        "Asked for",
        "What was built",
        "How to test",
        "Marked ready by",
        "Requested by",
        "Asked to check",
    ],
    pure.SENT_BACK: ["Asked for", "What needs doing", "Sent back by", "Marked ready by"],
    pure.DONE: [
        "Asked for",
        "What was built",
        "How to test",
        "Accepted by",
        "Requested by",
        "Asked to check",
    ],
    pure.HOLD: ["Asked for", "Why it is waiting", "Was", "Requested by"],
    pure.DECLINED: ["Asked for", "Why", "Requested by"],
    pure.CHECK_ASKED: [
        "Asked for",
        "What was built",
        "How to test",
        "Marked ready by",
        "Asked by",
    ],
}


@pytest.mark.parametrize("look", pure.LOOKS)
def test_one_builder_draws_each_of_the_eight_looks_with_its_own_title_colour_and_fields(look):
    card = pure.request_embed(
        CARD_ROW, move=look, origin="https://blackbloc.test", guild=None
    ).to_dict()

    assert card["title"] == pure.EMBED_TITLES[look].format(request_id=7)
    assert card["color"] == pure.EMBED_COLOURS[look]
    assert [field["name"] for field in card["fields"]] == CARD_FIELDS[look]
    assert card["footer"]["text"] == "Black Bloc · requests"
    assert card["timestamp"]


def test_the_card_is_stamped_when_the_move_happened_not_when_it_rendered():
    filed = pure.request_embed(CARD_ROW, move=pure.FILED_LOOK).to_dict()
    done = pure.request_embed(CARD_ROW, move=pure.DONE).to_dict()

    assert filed["timestamp"].startswith("2026-09-03T01:00:00")
    assert done["timestamp"].startswith("2026-09-03T02:00:00")


def test_a_card_leaves_off_a_field_that_has_nothing_in_it_rather_than_printing_nothing():
    bare = dict(CARD_ROW) | {"how_to_test": None, "assignee_id": None, "due_on": None}

    review = pure.request_embed(bare, move=pure.REVIEW).to_dict()
    working = pure.request_embed(bare, move=pure.IN_PROGRESS).to_dict()
    filed = pure.request_embed(bare, move=pure.FILED_LOOK).to_dict()

    assert "How to test" not in [field["name"] for field in review["fields"]]
    assert "Assignee" not in [field["name"] for field in working["fields"]]
    assert "Due" not in [field["name"] for field in filed["fields"]]


@pytest.mark.parametrize("look", pure.LOOKS)
def test_no_card_field_or_title_can_outgrow_what_discord_will_take(look):
    """A long `why` is the one that would silently 400 the whole post (§J)."""
    huge = dict(CARD_ROW) | {
        "what": "a board " * 400,
        "why": "because " * 400,
        "built": "built " * 400,
        "how_to_test": "test " * 400,
        "sent_back_reason": "note " * 400,
        "decline_reason": "reason " * 400,
    }
    card = pure.request_embed(huge, move=look, origin="https://blackbloc.test").to_dict()

    assert len(card["title"]) <= 256
    for field in card["fields"]:
        assert len(field["value"]) <= 1024, field["name"]
        assert len(field["name"]) <= 256


def test_the_card_carries_the_server_name_so_a_dm_says_which_server_it_came_from():
    class Server:
        name = "Black in a Flash!"

    card = pure.request_embed(CARD_ROW, move=pure.DONE, guild=Server()).to_dict()

    assert card["author"]["name"] == "Black in a Flash!"
    assert "author" not in pure.request_embed(CARD_ROW, move=pure.DONE, guild=None).to_dict()


def test_every_card_carries_one_link_button_to_the_request_on_the_site():
    view = pure.site_view("https://blackbloc.test/", 7)

    assert len(view.children) == 1
    assert view.children[0].url == "https://blackbloc.test/requests.html#r-7"
    assert view.children[0].label == "Open on the site"
    assert pure.request_url("https://blackbloc.test", 7) == "https://blackbloc.test/requests.html#r-7"


def test_no_origin_means_no_button_rather_than_a_link_that_goes_nowhere():
    assert pure.site_view("", 7) is None
    assert pure.site_view(None, 7) is None


def test_the_plain_line_survives_for_the_log_when_a_card_is_never_posted():
    for look in pure.LOOKS:
        line = pure.move_line(CARD_ROW, look)
        assert "#7" in line and f"<@{ASKER}>" in line
    assert pure.move_line(CARD_ROW, "not a look") == ""


def test_the_check_asked_look_is_last_and_every_look_has_a_colour_title_and_fields():
    """Sixth pass: a look, not a state — the row stays `review` while the card says otherwise."""
    assert pure.LOOKS[-1] == pure.CHECK_ASKED == "check_asked"
    assert pure.CHECK_ASKED not in pure.STATUSES
    assert pure.CHECK_ASKED not in pure.DM_LOOKS
    for look in pure.LOOKS:
        assert look in pure.EMBED_COLOURS and look in pure.EMBED_TITLES
        assert look in pure.EMBED_FIELDS and look in pure.MOVE_LINE


def test_the_asked_field_is_absent_until_somebody_has_asked_and_then_says_who_and_when():
    nobody = dict(CARD_ROW) | {"check_asked_by": None, "check_asked_at": None}

    assert pure.field_value(nobody, "asked") == ""
    assert pure.field_value(nobody, "asked_by") == ""

    said = pure.field_value(CARD_ROW, "asked")

    assert said.startswith(f"<@{STAFFER}> · <t:") and said.endswith(":R>")
    assert pure.field_value(CARD_ROW, "asked_by") == f"<@{STAFFER}>"
    assert "Asked to check" not in [
        field["name"] for field in pure.request_embed(nobody, move=pure.REVIEW).to_dict()["fields"]
    ]


def test_a_stamp_the_bot_cannot_read_still_names_who_asked_rather_than_crashing():
    broken = dict(CARD_ROW) | {"check_asked_at": "sometime last week"}

    assert pure.field_value(broken, "asked") == f"<@{STAFFER}>"


def test_the_check_asked_card_is_the_only_one_that_carries_a_line_of_its_own():
    card = pure.request_embed(CARD_ROW, move=pure.CHECK_ASKED, guild=None).to_dict()

    assert "ready for you to try" in card["title"]
    assert card["description"].startswith(f"Try it and tell <@{STAFFER}> how it went")
    assert "description" not in pure.request_embed(CARD_ROW, move=pure.REVIEW).to_dict()
    nobody = dict(CARD_ROW) | {"check_asked_by": None}
    said = pure.request_embed(nobody, move=pure.CHECK_ASKED).to_dict()["description"]
    assert said.startswith("Try it and tell staff how it went")


def test_the_refusal_names_the_button_rather_than_a_subcommand_that_no_longer_exists():
    """The fourth pass took `/request ready` away; this sentence still recommended it."""
    said = pure.NOT_READY_TO_CHECK.format(
        request_id=7, status="being worked on", doing="ask them to check"
    )

    assert "/request ready" not in said
    assert "**Ready to check** on its card is what puts one there." in said
    assert "ask them to check" in said


class Store:
    def __init__(self, **values):
        self.values = values

    def get(self, guild_id, key):
        return self.values.get(key)


def test_the_two_check_settings_read_off_the_registry_and_never_out_of_the_cog():
    assert pure.CHECK_FALLBACK_KEY == "request_check_fallback_channel"
    assert pure.CHECK_ON_READY_KEY == "request_check_on_ready"
    assert pure.check_falls_back(Store(request_check_fallback_channel=True), GUILD) is True
    assert pure.check_falls_back(Store(request_check_fallback_channel=False), GUILD) is False
    assert pure.checks_on_ready(Store(request_check_on_ready=True), GUILD) is True
    assert pure.checks_on_ready(Store(), GUILD) is False


async def test_asking_again_overwrites_who_asked_and_when_rather_than_stacking_rows(db):
    request_id = await file_one(db)

    await pure.set_check_asked(db, request_id, STAFFER, "2026-09-03T02:30:00+00:00")
    row = await pure.get_request(db, request_id)

    assert row["check_asked_by"] == STAFFER
    assert row["check_asked_at"] == "2026-09-03T02:30:00+00:00"

    await pure.set_check_asked(db, request_id, ASKER, "2026-09-03T03:00:00+00:00")
    again = await pure.get_request(db, request_id)

    assert (again["check_asked_by"], again["check_asked_at"]) == (
        ASKER,
        "2026-09-03T03:00:00+00:00",
    )
    assert again["status"] == pure.OPEN


def test_every_move_posts_a_card_until_the_server_says_otherwise():
    assert pure.channel_moves(Store(), GUILD) == pure.LOOKS
    assert pure.posts_a_card(Store(), GUILD, pure.REVIEW) is True

    picked = Store(request_channel_moves=["done", "declined", "not a look"])

    assert pure.channel_moves(picked, GUILD) == ("done", "declined")
    assert pure.posts_a_card(picked, GUILD, pure.REVIEW) is False
    assert pure.posts_a_card(Store(request_channel_moves=[]), GUILD, pure.DONE) is False


def test_a_second_pair_of_eyes_is_asked_for_only_when_the_server_says_so():
    row = {"ready_by": STAFFER}
    them = type("Who", (), {"id": ASKER})()
    same = type("Who", (), {"id": STAFFER})()

    assert pure.may_accept(Store(), GUILD, row, same) is True
    assert pure.may_accept(Store(request_review_by_other=True), GUILD, row, same) is False
    assert pure.may_accept(Store(request_review_by_other=True), GUILD, row, them) is True
    assert pure.may_accept(Store(request_review_by_other=True), GUILD, {}, same) is True


@pytest.mark.parametrize("status", pure.STATUSES)
def test_every_status_maps_to_the_move_buttons_the_panel_design_names(status):
    """The fourth pass — one table, and the parametrised cog test checks the SAME table."""
    found = pure.card_buttons(status)
    actions = [one.action for one in found]

    expected = {
        pure.OPEN: ["pickup", "hold", "decline"],
        pure.IN_PROGRESS: ["ready", "hold", "decline"],
        pure.REVIEW: ["accept", "check", "sendback", "hold", "decline"],
        pure.HOLD: ["resume", "decline"],
        pure.DONE: [],
        pure.DECLINED: [],
        pure.WITHDRAWN: [],
    }[status]
    assert actions == expected
    for spec in found:
        assert spec.style in ("primary", "secondary", "success", "danger")
    if status == pure.REVIEW:
        assert [one.style for one in found] == [
            "success",
            "primary",
            "secondary",
            "secondary",
            "danger",
        ]
        assert [one.needs_modal for one in found] == [False, False, True, True, True]


def test_accept_drops_out_when_the_card_says_somebody_else_must_check():
    with_accept = [one.action for one in pure.card_buttons(pure.REVIEW, may_accept_here=True)]
    without = [one.action for one in pure.card_buttons(pure.REVIEW, may_accept_here=False)]

    assert "accept" in with_accept and "accept" not in without
    assert [one for one in without] == ["check", "sendback", "hold", "decline"]


def test_the_card_footer_says_who_may_accept_when_this_staffer_may_not():
    said = pure.card_footer_override(pure.REVIEW, STAFFER, False)

    assert said is not None and f"<@{STAFFER}>" in said
    assert pure.card_footer_override(pure.REVIEW, STAFFER, True) is None


@pytest.mark.parametrize("status", (pure.DONE, pure.DECLINED, pure.WITHDRAWN))
def test_the_card_footer_says_a_finished_request_is_finished(status):
    said = pure.card_footer_override(status, None, True)

    assert said is not None and "finishes" in said


def test_the_card_footer_is_the_default_when_there_is_nothing_extra_to_say():
    assert pure.card_footer_override(pure.OPEN, None, True) is None
    assert pure.card_footer_override(pure.IN_PROGRESS, None, True) is None


def test_open_reads_as_filed_on_a_card_and_every_other_status_reads_as_itself():
    assert pure.look_for_status(pure.OPEN) == pure.FILED_LOOK
    for status in (pure.IN_PROGRESS, pure.REVIEW, pure.HOLD, pure.DONE, pure.DECLINED):
        assert pure.look_for_status(status) == status


def test_a_select_option_label_carries_the_id_the_status_and_the_what_clamped_to_the_cap():
    row = {"id": 7, "status": pure.REVIEW, "what": "a" * 200}

    with_status = pure.option_label(row)
    without_status = pure.option_label(row, with_status=False)

    assert with_status.startswith("#7 · ready to check · ")
    assert without_status.startswith("#7 · ") and "ready to check" not in without_status
    assert len(with_status) <= pure.SELECT_OPTION_LIMIT
    assert len(without_status) <= pure.SELECT_OPTION_LIMIT


def test_the_pick_placeholder_says_how_many_are_left_off_only_when_some_are():
    assert pure.pick_placeholder(10, 10) == pure.PICK_A_REQUEST
    assert pure.pick_placeholder(25, 40) == "25 of 40 — the rest are on the site"


def test_the_counts_line_names_all_four_open_statuses_in_order():
    line = pure.counts_line({pure.OPEN: 3, pure.IN_PROGRESS: 1, pure.REVIEW: 0, pure.HOLD: 2})

    assert line == "**3** open · **1** being worked on · **0** ready to check · **2** on hold"
    empty = "**0** open · **0** being worked on · **0** ready to check · **0** on hold"
    assert pure.counts_line({}) == empty


def test_the_site_page_url_is_the_requests_page_with_no_anchor():
    assert pure.site_page_url("https://blackbloc.test/") == "https://blackbloc.test/requests.html"
    assert pure.site_page_url("https://blackbloc.test") == "https://blackbloc.test/requests.html"
    assert pure.site_page_url("") is None
    assert pure.site_page_url(None) is None


def test_panel_minutes_reads_the_settings_key():
    assert pure.panel_minutes(Store(request_panel_minutes=15), GUILD) == 15
    assert pure.panel_minutes(Store(request_panel_minutes=30), GUILD) == 30


def test_the_panel_only_shows_a_member_their_own_list_when_the_key_says_so():
    assert pure.PANEL_OWN_LIST_KEY == "request_panel_own_list"
    assert pure.panel_shows_own_list(Store(request_panel_own_list=True), GUILD) is True
    assert pure.panel_shows_own_list(Store(request_panel_own_list=False), GUILD) is False
    assert pure.panel_shows_own_list(Store(), GUILD) is False


class FakeBot:
    def __init__(self, db):
        self.db = db
        self.store = Store()

    def get_channel(self, channel_id):
        return None


class FakeGuild:
    def __init__(self, guild_id=GUILD):
        self.id = guild_id

    def get_channel(self, channel_id):
        return None


async def test_withdraw_request_takes_back_an_open_row_and_logs_one_row(db):
    request_id = await file_one(db)
    bot, guild = FakeBot(db), FakeGuild()
    row = await pure.get_request(db, request_id)

    said, fresh = await pure.withdraw_request(bot, guild, row, actor=None)

    assert fresh is not None and fresh["status"] == pure.WITHDRAWN
    assert f"#{request_id}" in said and "withdrawn" in said
    cur = await db.conn.execute("SELECT kind FROM action_log")
    assert [r["kind"] for r in await cur.fetchall()] == ["request.withdrawn"]


async def test_withdraw_request_takes_back_a_held_row_too(db):
    request_id = await file_one(db)
    await pure.set_status(
        db, request_id, pure.HOLD, decided_by=STAFFER, decline_reason="waiting", was=pure.OPEN
    )
    bot, guild = FakeBot(db), FakeGuild()
    row = await pure.get_request(db, request_id)

    said, fresh = await pure.withdraw_request(bot, guild, row, actor=None)

    assert fresh["status"] == pure.WITHDRAWN


async def test_withdraw_request_refuses_a_row_that_is_not_open_or_held(db):
    request_id = await file_one(db)
    await pure.set_status(db, request_id, pure.IN_PROGRESS, decided_by=STAFFER)
    bot, guild = FakeBot(db), FakeGuild()
    row = await pure.get_request(db, request_id)

    said, fresh = await pure.withdraw_request(bot, guild, row, actor=None)

    assert fresh is None
    assert "nothing to withdraw" in said
    assert (await pure.get_request(db, request_id))["status"] == pure.IN_PROGRESS
    assert await db.conn.execute("SELECT kind FROM action_log")


async def test_withdraw_request_via_website_writes_the_web_headed_kind(db):
    from black_bloc.logkinds import VIA_WEBSITE

    request_id = await file_one(db)
    bot, guild = FakeBot(db), FakeGuild()
    row = await pure.get_request(db, request_id)

    await pure.withdraw_request(bot, guild, row, actor=None, via=VIA_WEBSITE)

    cur = await db.conn.execute("SELECT kind FROM action_log")
    assert [r["kind"] for r in await cur.fetchall()] == ["web.request.withdrawn"]
