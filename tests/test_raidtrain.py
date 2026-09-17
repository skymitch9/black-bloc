from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest

from black_bloc import raidtrain as rt
from black_bloc.raidtrain import (
    ALL_SLOTS,
    CANCELLED,
    CARD_MOVES,
    CLAIM_SELECT,
    DONE,
    LIVE,
    LOCKED,
    MODE_SELECT,
    OPEN,
    OPEN_SLOTS,
    PANEL_MINUTES_KEY,
    PANEL_TIMEOUT_FOOTER,
    SLOT_COUNT_MAX,
    STATUS_WORDS,
    STATUSES,
    TAKE_OFF_SELECT,
    TAKEN_SLOTS,
    TERMINAL_STATUSES,
    TRAIN_SELECT,
    TRANSITIONS,
    allowed_moves,
    cancelled_text,
    caps_ok,
    card_buttons,
    card_selects,
    due_checkins,
    due_reminders,
    ends_at,
    filled,
    live_post_text,
    may_claim,
    may_move,
    mine_options,
    missed_reminders,
    move_refusal,
    neighbours,
    next_open_position,
    open_positions,
    panel_minutes,
    positions_word,
    reminder_text,
    render_lineup,
    root_buttons,
    root_selects,
    slot_at,
    slot_label,
    slot_options,
    slot_times,
    slots_held,
    taken_positions,
    train_options,
    twitch_url,
)
from black_bloc.when_picker import WhenDraft

START = datetime(2026, 9, 14, 19, 0, tzinfo=UTC)
SELECT_CAP = 25


def iso(when):
    return when.isoformat()


def train(**over):
    row = {
        "id": 1,
        "title": "Saturday train",
        "description": "Everyone welcome.",
        "starts_at": iso(START),
        "slot_minutes": 60,
        "slot_count": 3,
        "status": OPEN,
        "cancel_reason": None,
    }
    row.update(over)
    return row


def slot(position, **over):
    start = START + timedelta(minutes=60 * (position - 1))
    row = {
        "id": position,
        "train_id": 1,
        "position": position,
        "starts_at": iso(start),
        "ends_at": iso(start + timedelta(minutes=60)),
        "user_id": None,
        "twitch_login": None,
        "claimed_at": None,
        "assigned_by": None,
        "locked": 0,
        "reminded_at": None,
        "checked_in_at": None,
        "live_posted_at": None,
    }
    row.update(over)
    return row


def lineup():
    return [
        slot(1, user_id=11, twitch_login="alpha"),
        slot(2, user_id=22, twitch_login="beta"),
        slot(3),
    ]


def test_slots_run_back_to_back_from_the_start():
    times = slot_times(START, 60, 3)
    assert len(times) == 3
    assert times[0] == (START, START + timedelta(hours=1))
    assert times[1][0] == times[0][1]
    assert times[2][1] == START + timedelta(hours=3)


def test_a_train_with_no_slots_has_no_times():
    assert slot_times(START, 60, 0) == []


def test_the_end_of_a_train_comes_from_its_own_rows_first():
    rows = lineup()
    assert ends_at(train(), rows) == START + timedelta(hours=3)
    assert ends_at(train(slot_count=5), None) == START + timedelta(hours=5)
    assert ends_at({"starts_at": "not a time"}, None) is None


def test_only_the_named_moves_are_allowed():
    assert may_move(OPEN, LOCKED) is True
    assert may_move(LOCKED, OPEN) is True
    assert may_move(LOCKED, LIVE) is True
    assert may_move(LIVE, DONE) is True
    assert may_move(DONE, LIVE) is False
    assert may_move(CANCELLED, OPEN) is False
    assert may_move("nonsense", OPEN) is False
    assert set(TERMINAL_STATUSES) == {DONE, CANCELLED}
    assert set(TRANSITIONS) == set(STATUSES)
    assert set(STATUS_WORDS) == set(STATUSES)
    for allowed in TRANSITIONS.values():
        assert set(allowed) <= set(STATUSES)


def test_a_refusal_says_what_is_allowed_instead_of_printing_a_status_list():
    said = move_refusal(LIVE, OPEN)
    assert "**live**" in said and "**done**" in said
    assert "cannot be marked **open**" in said
    assert allowed_moves(LIVE) == "**done**"
    assert allowed_moves(OPEN) == "**locked**, **live** or **cancelled**"
    assert allowed_moves(DONE) == "nothing"
    assert "end of the line" in move_refusal(DONE, OPEN)


def test_the_cap_counts_what_a_member_already_holds_and_zero_means_no_ceiling():
    rows = lineup()
    assert caps_ok(rows, 11, 1) is False
    assert caps_ok(rows, 33, 1) is True
    assert caps_ok(rows, 11, 0) is True
    assert caps_ok(rows, 11, 2) is True
    assert [row["position"] for row in slots_held(rows, 11)] == [1]


def test_the_open_slots_are_found_in_order():
    rows = [slot(1), slot(2, user_id=22), slot(3)]
    assert open_positions(rows) == [1, 3]
    assert next_open_position(rows) == 1
    assert positions_word(rows) == "#1, #3"
    assert next_open_position([slot(1, user_id=1)]) is None
    assert positions_word([slot(1, user_id=1)]) == "none"
    assert filled(rows) == 1


def test_a_slot_is_found_by_position_and_knows_its_neighbours():
    rows = lineup()
    assert slot_at(rows, 2)["user_id"] == 22
    assert slot_at(rows, 9) is None
    before, after = neighbours(rows, 2)
    assert before["position"] == 1 and after["position"] == 3
    assert neighbours(rows, 1)[0] is None


def test_the_lineup_names_the_ping_role_only_and_reads_every_slot():
    text = render_lineup(train(), lineup(), ping_role_id=77)
    assert text.startswith("<@&77> ")
    assert "**Saturday train**" in text
    assert "2/3 slot(s) filled" in text
    assert "https://twitch.tv/alpha" in text
    assert "<@11>" in text and "_open_" in text
    assert "**Take an hour…**" in text
    assert "/raidtrain claim" not in text


def test_a_locked_lineup_stops_inviting_claims_and_a_cancelled_one_says_so():
    locked = render_lineup(train(status=LOCKED), lineup())
    assert "**Take an hour…**" not in locked
    assert "locked" in locked
    off = render_lineup(train(status=CANCELLED, cancel_reason="the venue fell through"), lineup())
    assert "**This train is cancelled.**" in off
    assert "the venue fell through" in off


def test_a_checked_in_slot_is_marked_on_the_lineup():
    rows = lineup()
    rows[0]["checked_in_at"] = iso(START)
    assert "✅" in render_lineup(train(), rows)


def test_the_reminder_names_who_raids_in_and_who_to_raid_next():
    rows = lineup()
    before, after = neighbours(rows, 2)
    said = reminder_text(train(), rows[1], before, after, link="https://discord.com/x")
    assert "**Saturday train**" in said
    assert "slot **#2**" in said
    assert "<@11>" in said and "https://twitch.tv/alpha" in said
    assert "raid" in said
    assert "https://discord.com/x" in said


def test_the_first_and_last_holders_are_told_they_open_and_close_the_train():
    rows = lineup()
    opener = reminder_text(train(), rows[0], *neighbours(rows, 1))
    assert "you open the train" in opener
    closer = reminder_text(train(), rows[1], *neighbours(rows, 2))
    assert "you close the train" in closer


def test_a_cancellation_dm_names_the_train_and_the_reason_when_there_is_one():
    assert "no longer happening" in cancelled_text(train())
    assert "the venue fell through" in cancelled_text(train(), "the venue fell through")


def test_a_reminder_is_due_inside_the_lead_window_and_only_once():
    rows = lineup()
    now = START - timedelta(minutes=20)
    assert [row["position"] for row in due_reminders(now, 30, rows)] == [1]
    rows[0]["reminded_at"] = iso(now)
    assert due_reminders(now, 30, rows) == []


def test_an_unclaimed_slot_is_never_reminded():
    rows = [slot(1)]
    assert due_reminders(START - timedelta(minutes=5), 30, rows) == []


def test_a_reminder_whose_slot_has_gone_by_ages_out_instead_of_arriving_late():
    rows = lineup()
    now = START + timedelta(minutes=40)
    assert [row["position"] for row in due_reminders(now, 30, rows)] == [2]
    assert [row["position"] for row in missed_reminders(now, rows)] == [1]
    assert missed_reminders(START - timedelta(minutes=5), rows) == []


def test_a_check_in_needs_an_open_session_inside_the_slots_own_window():
    rows = lineup()
    assert [row["position"] for row in due_checkins(START, rows, [11])] == [1]
    assert due_checkins(START, rows, [22]) == []
    assert due_checkins(START - timedelta(minutes=30), rows, [11]) == []
    early = START - timedelta(minutes=10)
    assert [row["position"] for row in due_checkins(early, rows, [11])] == [1]
    rows[0]["checked_in_at"] = iso(START)
    assert due_checkins(START, rows, [11]) == []


def test_the_train_moves_line_names_who_is_on_air_and_who_is_next():
    rows = lineup()
    said = live_post_text(train(), rows[0], rows[1])
    assert "**alpha**" in said and "**beta**" in said
    assert "https://twitch.tv/alpha" in said
    last = live_post_text(train(), rows[1], rows[2])
    assert "last booked slot" in last


def test_the_moved_line_mentions_the_two_roles_once_each_and_nothing_else():
    """C3: the on-air streamer's fan role and the raid-train opt-in role, each once."""
    rows = lineup()
    said = live_post_text(train(), rows[0], rows[1], fan_role_id=11, raid_role_id=22)

    assert said.count("<@&11>") == 1 and said.count("<@&22>") == 1
    assert said.count("<@&") == 2
    assert rt.moved_mentions(11, 22) == [11, 22]


def test_one_role_playing_both_parts_is_mentioned_once():
    rows = lineup()
    said = live_post_text(train(), rows[0], rows[1], fan_role_id=11, raid_role_id=11)

    assert said.count("<@&11>") == 1
    assert rt.moved_mentions(11, 11) == [11]


def test_the_moved_line_mentions_nobody_when_neither_role_exists():
    rows = lineup()
    assert "<@&" not in live_post_text(train(), rows[0], rows[1])
    assert rt.moved_mentions(None, None) == []
    assert rt.moved_mentions(None, 22) == [22]
    assert rt.moved_mentions(11, None) == [11]


def test_a_twitch_url_survives_an_at_sign():
    assert twitch_url("@name") == "https://twitch.tv/name"
    assert twitch_url(None) == "https://twitch.tv/"


@pytest.mark.parametrize("status", [OPEN, LOCKED, LIVE, DONE, CANCELLED])
def test_every_status_renders_a_lineup_rather_than_raising(status):
    assert render_lineup(train(status=status), lineup())


# --- the panel tables, as data -------------------------------------------------------------------


def test_a_slot_select_can_never_cap_because_a_train_is_shorter_than_the_ceiling():
    """§D rests on this: 24 slots is a message-length limit, and it is below Discord's 25."""
    assert SLOT_COUNT_MAX < SELECT_CAP
    assert len(slot_options([slot(one) for one in range(1, SLOT_COUNT_MAX + 1)])) < SELECT_CAP


def test_taken_positions_is_the_mirror_of_the_open_ones():
    rows = lineup()
    assert taken_positions(rows) == [1, 2]
    assert open_positions(rows) == [3]
    assert taken_positions([]) == []


@pytest.mark.parametrize(
    ("status", "linked", "require", "ceiling", "who", "wanted"),
    [
        (OPEN, True, True, 1, 99, True),
        (LOCKED, True, True, 1, 99, False),
        (LIVE, True, True, 1, 99, False),
        (DONE, True, True, 1, 99, False),
        (CANCELLED, True, True, 1, 99, False),
        (OPEN, False, True, 1, 99, False),
        (OPEN, False, False, 1, 99, True),
        (OPEN, True, True, 1, 11, False),
        (OPEN, True, True, 0, 11, True),
    ],
)
def test_the_claim_select_renders_on_four_conditions_and_no_others(
    status, linked, require, ceiling, who, wanted
):
    assert (
        may_claim(
            train(status=status),
            lineup(),
            who,
            ceiling=ceiling,
            linked=linked,
            require_link=require,
        )
        is wanted
    )


def test_a_full_train_offers_no_claim_even_while_it_is_open():
    full = [slot(one, user_id=100 + one) for one in (1, 2, 3)]
    assert may_claim(train(), full, 99, ceiling=0, linked=True, require_link=True) is False


@pytest.mark.parametrize("status", [OPEN, LOCKED, LIVE, DONE, CANCELLED])
def test_every_state_renders_its_own_card_row_and_no_other(status):
    said = [
        move.label for move in card_buttons(status, organizer=True, held=[], slot_count=3)
    ]
    assert said[-2:] == ["Back", "Refresh"]
    assert ("Lock the lineup" in said) is (status == OPEN)
    assert ("Open it for sign-ups" in said) is (status == LOCKED)
    assert not ("Lock the lineup" in said and "Open it for sign-ups" in said)
    assert ("Call it off…" in said) is (status in (OPEN, LOCKED))
    assert ("Put somebody in…" in said) is (status in (OPEN, LOCKED))
    assert ("Change two slots round…" in said) is (status in (OPEN, LOCKED))


def test_a_live_train_carries_neither_lock_button():
    said = [move.label for move in card_buttons(LIVE, organizer=True, held=[1], slot_count=3)]
    assert said == ["Back", "Refresh"]


def test_a_member_sees_only_the_move_that_is_theirs_to_make():
    alone = [move.label for move in card_buttons(OPEN, organizer=False, held=[2], slot_count=3)]
    assert alone == ["Give back slot #2", "Back", "Refresh"]
    many = [move.label for move in card_buttons(OPEN, organizer=False, held=[1, 2], slot_count=3)]
    assert many == ["Give an hour back…", "Back", "Refresh"]
    assert [row["position"] for row in slots_held(lineup(), 11)] == [1]


def test_give_back_and_give_an_hour_back_never_coexist():
    for count in range(0, 4):
        said = [
            move.label
            for move in card_buttons(
                OPEN, organizer=True, held=list(range(1, count + 1)), slot_count=4
            )
        ]
        assert not (
            any(one.startswith("Give back slot") for one in said)
            and "Give an hour back…" in said
        )


def test_no_row_on_a_card_ever_carries_more_than_five_controls():
    counted: dict[int, int] = {}
    for move in card_buttons(OPEN, organizer=True, held=[1], slot_count=4):
        counted[move.row] = counted.get(move.row, 0) + 1
    assert max(counted.values()) <= 5
    assert counted[2] == 4


def test_a_one_slot_train_is_never_offered_a_swap():
    said = [move.label for move in card_buttons(OPEN, organizer=True, held=[], slot_count=1)]
    assert "Change two slots round…" not in said


@pytest.mark.parametrize("status", [OPEN, LOCKED, LIVE, DONE, CANCELLED])
def test_take_somebody_off_only_renders_where_the_lineup_may_still_change(status):
    found = card_selects(status, organizer=True, claimable=True, has_taken=True)
    assert (TAKE_OFF_SELECT in found) is (status in (OPEN, LOCKED))
    assert (CLAIM_SELECT in found) is (status == OPEN)


def test_an_empty_lineup_is_never_offered_take_somebody_off():
    assert card_selects(OPEN, organizer=True, claimable=False, has_taken=False) == ()
    assert card_selects(OPEN, organizer=False, claimable=False, has_taken=True) == ()


@pytest.mark.parametrize("mode", ["off", "shadow", "on"])
def test_the_root_offers_start_only_when_the_feature_can_carry_a_new_train(mode):
    said = [
        move.label
        for move in root_buttons(organizer=True, staff=False, holds_any=False, mode=mode)
    ]
    assert ("Start a raid train" in said) is (mode != "off")
    assert said[-1] == "Refresh"


def test_a_member_never_reaches_the_staff_half_of_the_root():
    said = [
        move.label
        for move in root_buttons(organizer=False, staff=False, holds_any=False, mode="on")
    ]
    assert said == ["Refresh"]
    mine = [
        move.label
        for move in root_buttons(organizer=False, staff=False, holds_any=True, mode="on")
    ]
    assert mine == ["My slots…", "Refresh"]


def test_staff_reach_setup_and_logs_even_while_raid_trains_are_off():
    said = [
        move.label
        for move in root_buttons(organizer=True, staff=True, holds_any=False, mode="off")
    ]
    assert said == ["Setup…", "Logs", "Refresh"]
    assert root_selects(staff=True, has_trains=False) == (MODE_SELECT,)
    assert root_selects(staff=False, has_trains=True) == (TRAIN_SELECT,)


def test_the_train_select_names_the_train_and_the_state_it_is_in():
    found = train_options([train(), train(id=2, title="Sunday train", status=LOCKED)])
    assert found[0] == ("1", "#1 · open for sign-ups · Saturday train")
    assert found[1][0] == "2"
    assert "locked" in found[1][1]
    assert train_options(None) == ()


def test_the_slot_selects_split_the_open_hours_from_the_taken_ones():
    rows = lineup()
    assert [value for value, _ in slot_options(rows, OPEN_SLOTS)] == ["3"]
    assert [value for value, _ in slot_options(rows, TAKEN_SLOTS)] == ["1", "2"]
    assert [value for value, _ in slot_options(rows, ALL_SLOTS)] == ["1", "2", "3"]


def test_a_slot_option_says_the_hour_in_plain_words_and_names_its_holder():
    rows = lineup()
    assert slot_options(rows, TAKEN_SLOTS)[0][1] == "#1 · 19:00 UTC · alpha"
    assert slot_options(rows, TAKEN_SLOTS, names={11: "Alice"})[0][1].endswith("Alice")
    assert slot_options(rows, OPEN_SLOTS)[0][1] == "#3 · 21:00 UTC"


def test_a_holder_with_neither_a_name_nor_a_login_is_still_named_something():
    assert slot_options([slot(1, user_id=44)], TAKEN_SLOTS)[0][1] == "#1 · 19:00 UTC · member 44"
    assert slot_label({"position": 2, "starts_at": "not a time", "user_id": None}) == (
        "#2 · time unreadable"
    )


def test_my_slots_lists_one_option_per_train_however_many_hours_are_held():
    rows = [
        slot(1, user_id=11, train_id=5, train_title="Saturday train", train_status=OPEN),
        slot(2, user_id=11, train_id=5, train_title="Saturday train", train_status=OPEN),
        slot(1, user_id=11, train_id=6, train_title="Sunday train", train_status=LOCKED),
    ]
    found = mine_options(rows)
    assert [value for value, _ in found] == ["5", "6"]
    assert "Saturday train" in found[0][1]
    assert mine_options(()) == ()


def test_the_panel_length_is_a_setting_and_not_a_constant():
    store = SimpleNamespace(get=lambda guild_id, key: 12 if key == PANEL_MINUTES_KEY else None)
    assert panel_minutes(store, 7) == 12
    assert PANEL_MINUTES_KEY == "raidtrain_panel_minutes"


def test_the_gone_quiet_footer_is_a_whole_sentence_naming_the_command():
    assert PANEL_TIMEOUT_FOOTER.endswith("run /raidtrain again")


def test_every_card_move_has_exactly_one_home_in_the_move_table():
    said = [move.label for move in CARD_MOVES]
    assert len(said) == len(set(said))
    for status in STATUSES:
        for move in card_buttons(status, organizer=True, held=[1], slot_count=4):
            assert move.action in {one.action for one in CARD_MOVES}


# The Start draft's own gate (`docs/info/when-picker-design.md` §4). One sentence at a time, and
# the two numbers kept exactly as they were typed until they pass.

DRAFT_NOW = datetime(2026, 9, 10, 22, 7, tzinfo=UTC)


def train_draft(**kept):
    when = WhenDraft(zone="America/Phoenix", **kept.pop("when", {}))
    return rt.TrainDraft(
        when=when,
        title=kept.pop("title", "Saturday train"),
        description=kept.pop("description", ""),
        slot_minutes=kept.pop("slot_minutes", "60"),
        slot_count=kept.pop("slot_count", "4"),
    )


def test_a_train_draft_with_no_title_says_so_before_anything_about_the_time():
    fields, why = rt.draft_check(train_draft(title=""), DRAFT_NOW)

    assert fields is None
    assert why == rt.NO_TRAIN_TITLE


def test_a_titled_train_draft_with_no_time_says_what_is_left_to_pick():
    fields, why = rt.draft_check(train_draft(), DRAFT_NOW)

    assert fields is None
    assert "a day, an hour and a minute" in why


def test_a_complete_train_draft_comes_back_as_the_numbers_create_and_publish_takes():
    draft = train_draft(when={"day": date(2026, 9, 12), "hour": 19, "minute": 30})

    fields, why = rt.draft_check(draft, DRAFT_NOW)

    assert why == ""
    assert isinstance(fields, rt.TrainFields)
    assert fields.title == "Saturday train"
    assert (fields.slot_minutes, fields.slot_count) == (60, 4)
    assert fields.starts > DRAFT_NOW


def test_a_train_start_that_has_gone_by_reuses_the_events_sentence():
    draft = train_draft(when={"day": date(2020, 1, 1), "hour": 19, "minute": 30})

    fields, why = rt.draft_check(draft, DRAFT_NOW)

    assert fields is None and "already gone by" in why


def test_the_numbers_are_asked_last_so_the_time_is_never_hidden_behind_them():
    draft = train_draft(slot_minutes="abc")
    _fields, why = rt.draft_check(draft, DRAFT_NOW)
    assert "a day, an hour and a minute" in why

    draft.when.day, draft.when.hour, draft.when.minute = date(2026, 9, 12), 19, 30
    fields, why = rt.draft_check(draft, DRAFT_NOW)
    assert fields is None and "not a whole number" in why


def test_the_train_draft_card_shows_the_numbers_exactly_as_they_were_typed():
    said = "\n".join(
        rt.draft_lines(train_draft(slot_minutes="abc", slot_count=""), DRAFT_NOW, chosen=True)
    )

    assert "**Minutes per slot** — abc" in said
    assert "**How many slots** — (needed)" in said
    assert "**Title** — Saturday train" in said


def test_the_train_draft_card_says_the_time_once_and_never_twice():
    draft = train_draft()
    _fields, why = rt.draft_check(draft, DRAFT_NOW)

    said = "\n".join(rt.draft_lines(draft, DRAFT_NOW, chosen=True, why=why))

    assert said.count("a day, an hour and a minute") == 1
    assert "**Still needed:**" not in said


def test_a_settled_time_reads_as_the_day_and_the_clock_in_the_drafts_zone():
    draft = train_draft(when={"day": date(2026, 9, 12), "hour": 19, "minute": 30})

    said = "\n".join(rt.draft_lines(draft, DRAFT_NOW, chosen=True))

    assert "Sat Sep 12 · 7:30 PM" in said
    assert "America/Phoenix" in said


def test_the_bounds_are_one_home_now_rather_than_a_copy_in_the_cog():
    assert rt.read_numbers("60", "4") == (60, 4)
    assert "not a whole number" in rt.read_numbers("ten", "4")
    assert "15 to 720 minutes" in rt.read_numbers("5", "4")
    assert "1 to 24 slots" in rt.read_numbers("60", "99")
