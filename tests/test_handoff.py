from datetime import UTC, datetime, timedelta

import pytest

from black_bloc import events as events_pure
from black_bloc import handoff as pure
from black_bloc import requests as requests_pure

GUILD = 7
MEMBER = 900


class Store:
    def __init__(self, **values):
        self.values = values

    def get(self, guild_id, key):
        return self.values.get(key)


ON = Store(handoff_mode="on", handoff_confirm_hours=24)


def test_the_three_things_a_hand_off_moves_between_are_named_once():
    assert pure.KINDS == ("request", "event", "ticket")
    assert set(pure.TABLES) == set(pure.KINDS)
    assert pure.TABLES == {
        "request": "requests",
        "event": "events",
        "ticket": "modmail_tickets",
    }


def test_the_mode_key_is_read_off_the_registry_and_never_out_of_a_cog():
    assert pure.MODE_KEY == "handoff_mode"
    assert pure.CONFIRM_HOURS_KEY == "handoff_confirm_hours"
    assert pure.MODES == ("off", "on")
    assert pure.handoff_on(ON, GUILD) is True
    assert pure.handoff_on(Store(handoff_mode="off"), GUILD) is False
    assert pure.handoff_on(Store(), GUILD) is False


def test_the_confirm_window_is_clamped_to_what_the_registry_bounds():
    assert pure.confirm_hours(ON, GUILD) == 24
    assert pure.confirm_hours(Store(handoff_confirm_hours=0), GUILD) == pure.CONFIRM_HOURS_MIN
    assert pure.confirm_hours(Store(handoff_confirm_hours=999), GUILD) == pure.CONFIRM_HOURS_MAX
    assert pure.confirm_hours(Store(handoff_confirm_hours="nope"), GUILD) == pure.CONFIRM_HOURS
    assert pure.confirm_hours(Store(), GUILD) == pure.CONFIRM_HOURS


def test_one_cell_says_where_a_thing_went_and_reads_straight_back():
    assert pure.trail(pure.EVENT, 12) == "event:12"
    assert pure.read_trail("event:12") == pure.Trail("event", 12, "")
    assert pure.read_trail("request:3").ident == 3
    assert pure.read_trail("ticket:9").kind == "ticket"


def test_a_cell_nothing_wrote_reads_as_nothing_rather_than_raising():
    for bad in (None, "", "event", "event:", "event:abc", "poll:1", "asked:poll:x", "yes:poll"):
        assert pure.read_trail(bad) is None


def test_a_question_waiting_on_a_member_carries_its_own_deadline():
    until = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
    cell = pure.asked_trail(pure.REQUEST, until)

    assert cell == "asked:request:2026-09-18T12:00:00+00:00"
    assert pure.read_trail(cell).kind == pure.ASKED
    assert pure.asked_kind(cell) == pure.REQUEST
    assert pure.waiting_on(cell, until - timedelta(minutes=1)) is not None
    assert pure.waiting_on(cell, until) is None
    assert pure.expired(cell, until + timedelta(seconds=1)) is True
    assert pure.expired(cell, until - timedelta(seconds=1)) is False


def test_no_answer_inside_the_window_counts_as_no_without_anything_sweeping():
    """The read decides, so a question nobody answered simply stops holding the ticket."""
    stale = pure.asked_trail(pure.EVENT, datetime(2020, 1, 1, tzinfo=UTC))

    assert pure.expired(stale, datetime.now(UTC)) is True
    assert pure.waiting_on(stale, datetime.now(UTC)) is None


def test_an_unreadable_deadline_is_treated_as_run_out_rather_than_as_forever():
    assert pure.expired("asked:request:not a time", datetime.now(UTC)) is True
    assert pure.until_stamp("asked:request:not a time") == "soon"
    assert pure.until_stamp("event:4") == "soon"


def test_the_deadline_is_now_plus_the_servers_hours():
    at = datetime(2026, 9, 17, 9, 0, tzinfo=UTC)

    assert pure.deadline(ON, GUILD, at) == at + timedelta(hours=24)
    assert pure.deadline(Store(handoff_confirm_hours=1), GUILD, at) == at + timedelta(hours=1)


def test_a_yes_that_still_owes_a_date_is_its_own_shape():
    assert pure.yes_trail(pure.EVENT) == "yes:event"
    assert pure.read_trail("yes:event") == pure.Trail(pure.YES, 0, pure.EVENT)
    assert pure.asked_kind("yes:event") == pure.EVENT


def test_every_hand_off_has_one_log_kind_naming_both_ends():
    assert pure.handoff_kind(pure.REQUEST, pure.EVENT) == "handoff.request_to_event"
    assert pure.handoff_kind(pure.TICKET, pure.REQUEST) == "handoff.ticket_to_request"


def test_the_log_kinds_land_on_the_request_feature_and_are_all_loud():
    from black_bloc.logkinds import IMPORTANT, feature_of, is_important

    for pair in (
        (pure.REQUEST, pure.EVENT),
        (pure.EVENT, pure.REQUEST),
        (pure.REQUEST, pure.TICKET),
        (pure.TICKET, pure.REQUEST),
        (pure.TICKET, pure.EVENT),
    ):
        kind = pure.handoff_kind(*pair)
        assert feature_of(kind) == "request", kind
        assert kind in IMPORTANT and is_important(kind), kind


def test_a_request_is_refused_in_words_when_the_move_is_off_or_the_row_is_finished():
    open_row = {"id": 4, "status": requests_pure.OPEN}

    assert pure.refusal_for_request(ON, GUILD, open_row) == ""
    off = pure.refusal_for_request(Store(handoff_mode="off"), GUILD, open_row)
    assert "handoff_mode" in off and "A setting group" in off
    for status in requests_pure.FINAL_STATUSES:
        said = pure.refusal_for_request(ON, GUILD, {"id": 4, "status": status})
        assert "#4" in said and "already" in said


def test_an_event_is_refused_in_words_once_it_has_been_decided():
    assert pure.refusal_for_event(ON, GUILD, {"id": 2, "status": events_pure.PENDING}) == ""
    said = pure.refusal_for_event(ON, GUILD, {"id": 2, "status": events_pure.CANCELLED})
    assert "#2" in said and events_pure.CANCELLED in said
    assert pure.refusal_for_event(Store(), GUILD, {"id": 2, "status": events_pure.PENDING})


def test_a_draft_raised_from_a_request_is_filled_in_from_it_and_says_whose_it_was():
    row = {"id": 11, "user_id": MEMBER, "what": "a games night", "why": "the doc is a mess"}

    title, description = pure.prefilled(row, kind=pure.REQUEST)

    assert title == "a games night"
    assert description.splitlines()[0] == f"Filed as request #11 by <@{MEMBER}>"
    assert "the doc is a mess" in description


def test_a_draft_raised_from_a_ticket_has_no_title_of_its_own_and_names_the_ticket():
    title, description = pure.prefilled({"id": 5, "user_id": MEMBER}, kind=pure.TICKET)

    assert title == ""
    assert description == f"Filed from ticket #5 by <@{MEMBER}>"


def test_a_request_with_nothing_in_its_why_still_makes_a_readable_description():
    title, description = pure.prefilled(
        {"id": 1, "user_id": MEMBER, "what": "a thing", "why": None}, kind=pure.REQUEST
    )

    assert title == "a thing"
    assert description == f"Filed as request #1 by <@{MEMBER}>"


def test_the_fields_a_draft_inherits_are_cut_to_what_discord_will_take():
    row = {"id": 1, "user_id": MEMBER, "what": "a" * 500, "why": "b" * 4000}

    title, description = pure.prefilled(row, kind=pure.REQUEST)

    assert len(title) == pure.TITLE_LIMIT <= events_pure.TITLE_LIMIT
    assert len(description) <= pure.BODY_LIMIT + 80


@pytest.mark.parametrize("kind", pure.KINDS)
async def test_the_trail_column_is_written_through_one_allow_listed_table(db, kind):
    await db.conn.execute(
        "INSERT INTO requests(id, guild_id, user_id, what, why, status, created_at) "
        "VALUES (1, 7, 900, 'w', 'y', 'open', '2026-09-17T00:00:00+00:00')"
    )
    await db.conn.execute(
        "INSERT INTO events(id, guild_id, requester_id, title, starts_at, status, created_at) "
        "VALUES (1, 7, 900, 't', '2026-09-18T00:00:00+00:00', 'pending', "
        "'2026-09-17T00:00:00+00:00')"
    )
    await db.conn.execute(
        "INSERT INTO modmail_tickets(id, guild_id, user_id, mode, channel_id, status, opened_at) "
        "VALUES (1, 7, 900, 'channel', 5, 'open', '2026-09-17T00:00:00+00:00')"
    )
    await db.conn.commit()

    await pure.set_moved_to(db, kind, 1, pure.trail(pure.EVENT, 9))
    cur = await db.conn.execute(f"SELECT moved_to FROM {pure.TABLES[kind]} WHERE id = 1")

    assert (await cur.fetchone())["moved_to"] == "event:9"


async def test_a_table_nobody_named_cannot_be_written_through_the_trail(db):
    with pytest.raises(KeyError):
        await pure.set_moved_to(db, "polls", 1, "event:1")


# --- the ticket half: what may be asked, and where the asked wording is kept -------------------


class FakeGuild:
    name = "Black in a Flash!"


def a_ticket(**fields):
    return {"id": 5, "user_id": MEMBER, "guild_id": GUILD, "moved_to": None} | fields


def test_a_ticket_nobody_has_asked_about_can_be_sent_anywhere():
    assert pure.refusal_for_ticket(ON, GUILD, a_ticket()) == ""


def test_the_move_being_off_refuses_a_ticket_by_name_too():
    said = pure.refusal_for_ticket(Store(), GUILD, a_ticket())

    assert "handoff_mode" in said and "A setting group" in said


def test_a_practice_ticket_has_nobody_to_ask_and_says_so():
    """The panel draws the card moves without knowing a ticket is practice, so the MOVE knows."""
    said = pure.refusal_for_ticket(ON, GUILD, a_ticket(practice=1))

    assert "practice" in said and "nothing was filed" in said
    assert pure.refusal_for_ticket(ON, GUILD, a_ticket(practice=0)) == ""


def test_a_ticket_waiting_on_an_answer_refuses_and_names_who_and_when():
    until = datetime.now(UTC) + timedelta(hours=4)
    ticket = a_ticket(moved_to=pure.asked_trail(pure.REQUEST, until))

    said = pure.refusal_for_ticket(ON, GUILD, ticket)

    assert "already asked" in said and f"<@{MEMBER}>" in said
    assert f"<t:{int(until.timestamp())}:f>" in said


def test_a_question_that_has_run_out_stops_blocking_the_ticket():
    stale = pure.asked_trail(pure.REQUEST, datetime(2020, 1, 1, tzinfo=UTC))

    assert pure.refusal_for_ticket(ON, GUILD, a_ticket(moved_to=stale)) == ""


def test_a_yes_that_still_owes_a_date_points_staff_at_the_button_that_finishes_it():
    said = pure.refusal_for_ticket(ON, GUILD, a_ticket(moved_to=pure.yes_trail(pure.EVENT)))

    assert "already said yes" in said and pure.MAKE_THE_EVENT.rstrip("…") in said


def test_a_ticket_already_filed_says_what_it_became():
    said = pure.refusal_for_ticket(ON, GUILD, a_ticket(moved_to=pure.trail(pure.REQUEST, 12)))

    assert "#5" in said and "request" in said and "12" in said


def test_the_confirm_card_says_what_would_be_filed_and_reads_straight_back():
    """One card, one copy of the wording — nothing else stores what staff typed."""
    embed = pure.confirm_embed(FakeGuild(), a_ticket(), pure.EVENT, "Block party", "on Tuesdays")

    assert embed.title == pure.CONFIRM_TITLE
    assert "Block party" in embed.description and "#5" in embed.description
    assert pure.read_ask(embed) == ("Block party", "on Tuesdays")


def test_a_card_with_nothing_in_a_field_reads_back_as_nothing_rather_than_a_dash():
    embed = pure.confirm_embed(FakeGuild(), a_ticket(), pure.REQUEST, "a thing", "")

    assert pure.read_ask(embed) == ("a thing", "")


def test_a_card_that_is_not_one_of_ours_reads_back_as_nothing_at_all():
    assert pure.read_ask(None) == ("", "")
    assert pure.read_ask(object()) == ("", "")


def test_the_wording_a_card_carries_is_cut_to_what_discord_will_take():
    embed = pure.confirm_embed(FakeGuild(), a_ticket(), pure.REQUEST, "a" * 400, "b" * 4000)

    assert len(embed.title) <= 256
    for field in embed.fields:
        assert len(field.value) <= 1024
    assert len(embed.description) <= 4096


def test_where_a_thing_went_is_said_one_way_for_every_surface():
    assert pure.moved_words("event:12") == "event #12"
    assert pure.moved_words("request:3") == "request #3"
    for nothing in (None, "", "ticket:1", "asked:event:x", "yes:event"):
        assert pure.moved_words(nothing) == ""
