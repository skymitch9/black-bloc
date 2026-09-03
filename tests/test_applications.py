import json

import pytest

from black_bloc.applications import (
    APPROVED,
    APPROVED_ON_RECORD,
    CARD_BUTTONS,
    DENIED,
    LABEL_MAX,
    LONG,
    MOVE_TARGETS,
    NO_ROLE,
    PANEL_OWN_LIST_KEY,
    PENDING,
    PLACEHOLDER_MAX,
    QUESTIONS_MAX,
    REMOVE_NEEDS_A_REASON,
    REMOVED,
    RESTORABLE,
    RETRY_DAYS_DEFAULT,
    SETTLED,
    SHORT,
    STATUSES,
    TITLE_MAX,
    TRANSITIONS,
    WITHDRAWN,
    ApplicationError,
    add_question,
    answers_json,
    application_id_from,
    application_lines,
    applications_for,
    card_buttons,
    check_name,
    check_title,
    cooling_until,
    counts_line,
    counts_of,
    create_application,
    create_form,
    decide_application,
    decision_lines,
    delete_form,
    edit_question,
    expires_days_of,
    form_lines,
    get_application,
    get_form,
    get_form_by_id,
    is_open,
    last_decision,
    list_forms,
    may_move,
    own_lines,
    owner_nudge,
    panel_shows_own_list,
    pending_count,
    question_lines,
    questions_for,
    read_answers,
    remove_application,
    remove_question,
    render_card,
    replace_questions,
    restore_application,
    retry_days_of,
    role_of,
    set_card,
    set_grant,
    set_panel,
    site_page_url,
    twitch_logins_for,
    update_form,
    validate_question,
    validate_questions,
)
from black_bloc.storage.db import Database

GUILD = 7
ROLE = 4242
STAFF = 1
MEMBER = 900


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "a.sqlite3")
    await database.connect()
    try:
        yield database
    finally:
        await database.close()


async def a_form(db, name="twitch-team", **kwargs):
    form_id = await create_form(db, GUILD, name, "Twitch Team", ROLE, STAFF, **kwargs)
    return await get_form_by_id(db, form_id)


def test_a_pending_application_may_only_move_to_the_three_settled_states():
    assert set(TRANSITIONS[PENDING]) == {APPROVED, DENIED, WITHDRAWN}
    assert TRANSITIONS[WITHDRAWN] == ()
    assert set(STATUSES) == {PENDING, APPROVED, DENIED, WITHDRAWN, REMOVED}
    assert may_move(PENDING, APPROVED) is True
    assert may_move(APPROVED, DENIED) is False
    assert may_move(None, APPROVED) is False


def test_an_approved_application_may_only_move_to_removed():
    assert TRANSITIONS[APPROVED] == (REMOVED,)
    assert may_move(APPROVED, REMOVED) is True
    assert may_move(PENDING, REMOVED) is False
    assert set(SETTLED) == {APPROVED, DENIED, WITHDRAWN, REMOVED}


def test_staff_can_leave_a_denied_or_removed_application_but_never_a_withdrawn_one():
    """Owner rule: no stored state staff cannot leave — except the one the member owns."""
    assert TRANSITIONS[DENIED] == (APPROVED,)
    assert TRANSITIONS[REMOVED] == (APPROVED,)
    assert may_move(DENIED, APPROVED) is True
    assert may_move(REMOVED, APPROVED) is True
    assert may_move(WITHDRAWN, APPROVED) is False
    assert RESTORABLE == (DENIED, REMOVED)


def test_a_form_name_is_a_slug_and_says_so_when_it_is_not():
    assert check_name("Twitch-Team") == "twitch-team"
    with pytest.raises(ApplicationError) as caught:
        check_name("twitch team")
    assert "lower-case letters" in str(caught.value)
    with pytest.raises(ApplicationError):
        check_name("-leading")
    with pytest.raises(ApplicationError):
        check_name("x" * 40)


def test_a_heading_longer_than_discord_shows_is_refused_with_the_number():
    assert check_title("  Twitch Team  ") == "Twitch Team"
    with pytest.raises(ApplicationError) as caught:
        check_title("t" * (TITLE_MAX + 1))
    assert str(TITLE_MAX) in str(caught.value)
    with pytest.raises(ApplicationError):
        check_title("   ")


def test_a_question_is_checked_against_discord_s_own_limits():
    found = validate_question("Twitch handle", LONG, False, "twitch.tv/…")
    assert found == {
        "label": "Twitch handle",
        "style": LONG,
        "required": 0,
        "placeholder": "twitch.tv/…",
    }
    with pytest.raises(ApplicationError):
        validate_question("x" * (LABEL_MAX + 1))
    with pytest.raises(ApplicationError):
        validate_question("Handle", SHORT, True, "p" * (PLACEHOLDER_MAX + 1))
    with pytest.raises(ApplicationError) as caught:
        validate_question("Handle", "essay")
    assert "`short`" in str(caught.value)


def test_a_form_may_not_hold_more_boxes_than_discord_shows():
    rows = validate_questions([{"label": f"Q{n}"} for n in range(QUESTIONS_MAX)])
    assert [row["position"] for row in rows] == list(range(1, QUESTIONS_MAX + 1))
    with pytest.raises(ApplicationError) as caught:
        validate_questions([{"label": f"Q{n}"} for n in range(QUESTIONS_MAX + 1)])
    assert str(QUESTIONS_MAX) in str(caught.value)


def test_answers_travel_with_the_wording_they_were_asked_in():
    raw = answers_json([("Twitch handle", "ada"), ("Why the Team", "")])
    assert json.loads(raw) == [
        {"label": "Twitch handle", "answer": "ada"},
        {"label": "Why the Team", "answer": ""},
    ]
    assert read_answers(raw)[0]["answer"] == "ada"


def test_an_unreadable_snapshot_shows_as_empty_rather_than_raising():
    assert read_answers("not json") == []
    assert read_answers(None) == []
    assert read_answers([{"label": "a", "answer": "b"}, "junk"]) == [
        {"label": "a", "answer": "b"}
    ]


async def test_form_crud_and_the_name_is_taken_once(db):
    form = await a_form(db)
    assert form["name"] == "twitch-team" and form["role_id"] == ROLE
    assert is_open(form) is True
    assert await create_form(db, GUILD, "twitch-team", "Again", ROLE, STAFF) is None
    assert await create_form(db, GUILD + 1, "twitch-team", "Other", ROLE, STAFF) is not None

    assert await update_form(db, GUILD, "twitch-team", title="The Team", open=False) is True
    fresh = await get_form(db, GUILD, "twitch-team")
    assert fresh["title"] == "The Team" and is_open(fresh) is False
    assert await update_form(db, GUILD, "nope", title="x") is False

    assert [row["name"] for row in await list_forms(db, GUILD)] == ["twitch-team"]
    assert await list_forms(db, GUILD, open_only=True) == []
    await delete_form(db, form["id"])
    assert await get_form(db, GUILD, "twitch-team") is None


async def test_questions_fill_the_next_free_slot_and_stop_at_five(db):
    form = await a_form(db)
    for n in range(QUESTIONS_MAX):
        assert await add_question(db, form["id"], f"Q{n}") == n + 1
    with pytest.raises(ApplicationError):
        await add_question(db, form["id"], "one too many")

    assert await remove_question(db, form["id"], 2) is True
    assert await remove_question(db, form["id"], 2) is False
    assert await add_question(db, form["id"], "back in the gap") == 2
    assert [row["position"] for row in await questions_for(db, form["id"])] == [1, 2, 3, 4, 5]


async def test_editing_a_question_keeps_what_it_was_not_told_to_change(db):
    form = await a_form(db)
    await add_question(db, form["id"], "Twitch handle", LONG, False, "twitch.tv/…")
    assert await edit_question(db, form["id"], 1, label="Your Twitch") is True
    row = (await questions_for(db, form["id"]))[0]
    assert row["label"] == "Your Twitch" and row["style"] == LONG and row["required"] == 0
    assert row["placeholder"] == "twitch.tv/…"
    assert await edit_question(db, form["id"], 3, label="nothing there") is False


async def test_replacing_the_list_stores_exactly_what_was_sent_in_order(db):
    form = await a_form(db)
    await add_question(db, form["id"], "old")
    await replace_questions(
        db, form["id"], [{"label": "first"}, {"label": "second", "style": LONG}]
    )
    rows = await questions_for(db, form["id"])
    assert [(row["position"], row["label"], row["style"]) for row in rows] == [
        (1, "first", SHORT),
        (2, "second", LONG),
    ]


async def test_only_one_application_per_person_per_form_is_open_at_a_time(db):
    form = await a_form(db)
    first = await create_application(db, GUILD, form["id"], MEMBER, answers_json([]))
    assert first is not None
    assert await create_application(db, GUILD, form["id"], MEMBER, answers_json([])) is None
    assert await pending_count(db, form["id"]) == 1

    assert await decide_application(db, first, WITHDRAWN, decided_by=MEMBER) is True
    assert await decide_application(db, first, APPROVED, decided_by=STAFF) is False
    assert await create_application(db, GUILD, form["id"], MEMBER, answers_json([])) is not None


async def test_a_decision_that_is_not_a_transition_is_refused_before_the_write(db):
    form = await a_form(db)
    made = await create_application(db, GUILD, form["id"], MEMBER, answers_json([]))
    with pytest.raises(ApplicationError):
        await decide_application(db, made, PENDING)


async def test_the_cooling_period_uses_the_form_s_own_wait(db):
    form = await a_form(db)
    await update_form(db, GUILD, form["name"], retry_days=30)
    form = await get_form_by_id(db, form["id"])
    made = await create_application(db, GUILD, form["id"], MEMBER, answers_json([]))
    await decide_application(db, made, DENIED, decided_by=STAFF, deny_reason="not yet")

    assert retry_days_of(form) == 30
    assert (await last_decision(db, form["id"], MEMBER))["id"] == made
    assert await cooling_until(db, form, MEMBER) is not None
    assert await cooling_until(db, form, MEMBER, 0) is None
    assert await cooling_until(db, form, MEMBER + 1) is None


async def test_a_withdrawn_application_never_starts_a_cooling_period(db):
    form = await a_form(db)
    made = await create_application(db, GUILD, form["id"], MEMBER, answers_json([]))
    await decide_application(db, made, WITHDRAWN, decided_by=MEMBER)

    assert await last_decision(db, form["id"], MEMBER) is None
    assert await cooling_until(db, form, MEMBER) is None


async def test_the_queue_lists_pending_first_and_filters_by_form_and_status(db):
    one = await a_form(db)
    two = await a_form(db, name="mod-team")
    waiting = await create_application(db, GUILD, two["id"], MEMBER, answers_json([]))
    decided = await create_application(db, GUILD, one["id"], MEMBER, answers_json([]))
    await decide_application(db, decided, APPROVED, decided_by=STAFF)

    rows = await applications_for(db, GUILD)
    assert [row["id"] for row in rows] == [waiting, decided]
    assert [row["id"] for row in await applications_for(db, GUILD, form_id=one["id"])] == [
        decided
    ]
    assert [
        row["id"] for row in await applications_for(db, GUILD, statuses=(PENDING,))
    ] == [waiting]
    assert await applications_for(db, GUILD, user_id=MEMBER + 1) == []


async def test_the_card_and_the_panel_ids_are_remembered_on_the_row(db):
    form = await a_form(db)
    made = await create_application(db, GUILD, form["id"], MEMBER, answers_json([]))
    await set_card(db, made, 111, 222)
    await set_grant(db, made, 5)
    row = await get_application(db, made)
    assert (row["card_channel_id"], row["card_message_id"], row["grant_id"]) == (111, 222, 5)

    await set_panel(db, form["id"], 333, 444)
    fresh = await get_form_by_id(db, form["id"])
    assert (fresh["panel_channel_id"], fresh["panel_message_id"]) == (333, 444)


async def test_the_card_shows_one_field_per_answer_and_the_form_s_own_footer(db):
    form = await a_form(db)
    made = await create_application(
        db,
        GUILD,
        form["id"],
        MEMBER,
        answers_json([("Twitch handle", "ada"), ("Why the Team", "")]),
    )
    embed = render_card(form, await get_application(db, made))

    assert embed.title == f"Application #{made} — Twitch Team"
    assert f"<@{MEMBER}>" in embed.description and f"<@&{ROLE}>" in embed.description
    names = [field.name for field in embed.fields]
    assert "Twitch handle" in names and "Why the Team" in names
    blank = next(field for field in embed.fields if field.name == "Why the Team")
    assert blank.value == "(left blank)"
    assert embed.footer.text == f"#{made} · twitch-team"


async def test_an_answer_longer_than_discord_shows_is_cut_at_the_field_limit(db):
    form = await a_form(db)
    made = await create_application(
        db, GUILD, form["id"], MEMBER, answers_json([("Why", "y" * 4000)])
    )
    embed = render_card(form, await get_application(db, made))
    assert len(next(f for f in embed.fields if f.name == "Why").value) == 1024


async def test_the_approved_wording_names_the_owner_and_the_next_step(db):
    form = await a_form(db)
    await update_form(
        db,
        GUILD,
        form["name"],
        owner_user_id=55,
        next_step="the Team owner sends your twitch.tv invite",
        approved_text="Welcome to the Team.",
        expires_days=0,
    )
    form = await get_form_by_id(db, form["id"])
    made = await create_application(db, GUILD, form["id"], MEMBER, answers_json([]))
    await decide_application(db, made, APPROVED, decided_by=STAFF)
    row = await get_application(db, made)

    card, said = decision_lines(form, row, guild_name="Black in a Flash!", member_name="Ada")

    assert "Ada" in card and "<@55> — next step:" in card
    assert "twitch.tv invite" in card
    assert "Welcome to the Team." in said and "twitch.tv invite" in said
    assert owner_nudge(form).startswith("<@55>")


async def test_a_next_step_with_nobody_named_still_says_what_it_is(db):
    form = await a_form(db)
    await update_form(db, GUILD, form["name"], next_step="somebody clicks the invite")
    form = await get_form_by_id(db, form["id"])
    assert owner_nudge(form) == "Next step: somebody clicks the invite"


async def test_a_form_with_no_next_step_adds_nothing_to_the_card(db):
    form = await a_form(db)
    assert owner_nudge(form) == ""


async def test_a_denied_application_is_told_the_reason_and_when_to_come_back(db):
    form = await a_form(db)
    await update_form(db, GUILD, form["name"], retry_days=30)
    form = await get_form_by_id(db, form["id"])
    made = await create_application(db, GUILD, form["id"], MEMBER, answers_json([]))
    await decide_application(db, made, DENIED, decided_by=STAFF, deny_reason="not enough hours")
    row = await get_application(db, made)

    card, said = decision_lines(form, row, guild_name="Black in a Flash!")

    assert card == "Denied, and they have been told why."
    assert "not enough hours" in said and "<t:" in said


async def test_a_role_that_could_not_be_added_says_so_on_the_card(db):
    form = await a_form(db)
    made = await create_application(db, GUILD, form["id"], MEMBER, answers_json([]))
    await decide_application(db, made, APPROVED, decided_by=STAFF)
    row = await get_application(db, made)

    card, _ = decision_lines(form, row, member_name="Ada", granted=False)

    assert "Discord refused to add the role" in card
    assert "/role grant" in card


async def test_an_expiry_is_said_out_loud_in_both_the_card_and_the_dm(db):
    form = await a_form(db)
    await update_form(db, GUILD, form["name"], expires_days=7)
    form = await get_form_by_id(db, form["id"])
    made = await create_application(db, GUILD, form["id"], MEMBER, answers_json([]))
    await decide_application(db, made, APPROVED, decided_by=STAFF)
    row = await get_application(db, made)

    card, said = decision_lines(
        form, row, member_name="Ada", until="2099-01-01T00:00:00+00:00"
    )

    assert expires_days_of(form) == 7
    assert "runs out <t:" in card and "runs out <t:" in said


async def test_a_withdrawn_application_tells_the_card_and_dms_nobody(db):
    form = await a_form(db)
    made = await create_application(db, GUILD, form["id"], MEMBER, answers_json([]))
    await decide_application(db, made, WITHDRAWN, decided_by=MEMBER)

    card, said = decision_lines(form, await get_application(db, made))

    assert "Taken back" in card and said == ""


async def test_a_form_with_no_wait_of_its_own_falls_back_to_the_server_default(db):
    form = await a_form(db)
    assert form["retry_days"] is None
    assert retry_days_of(form) == RETRY_DAYS_DEFAULT
    assert retry_days_of(form, 14) == 14


async def test_the_unique_index_catches_a_second_application_the_check_did_not_see(
    db, monkeypatch
):
    """The read-then-write is a race; the partial unique index is what actually holds.
    `open_application` is stubbed to `None` so the INSERT is the thing that loses."""
    import black_bloc.applications as module

    form = await a_form(db)
    first = await create_application(db, GUILD, form["id"], MEMBER, answers_json([]))

    async def sees_nothing(*args, **kwargs):
        return None

    monkeypatch.setattr(module, "open_application", sees_nothing)

    assert await module.create_application(db, GUILD, form["id"], MEMBER, answers_json([])) is None
    assert await pending_count(db, form["id"]) == 1
    assert (await get_application(db, first))["status"] == PENDING


# A form that keeps a list instead of handing a role over.


async def a_list_form(db, name="stream-team"):
    form_id = await create_form(db, GUILD, name, "Stream Team", None, STAFF)
    return await get_form_by_id(db, form_id)


def test_a_role_is_read_through_one_helper_that_answers_none_for_a_list():
    assert role_of({"role_id": 4242}) == 4242
    assert role_of({"role_id": None}) is None
    assert role_of({"role_id": 0}) is None
    assert role_of({}) is None
    assert role_of({"role_id": "nonsense"}) is None


async def test_a_form_may_be_created_with_no_role_at_all(db):
    form = await a_list_form(db)

    assert form["role_id"] is None
    assert role_of(form) is None


async def test_a_role_is_cleared_only_when_the_caller_spells_it_no_role(db):
    form = await a_form(db)

    assert await update_form(db, GUILD, form["name"], role_id=None) is True
    assert role_of(await get_form_by_id(db, form["id"])) == ROLE

    assert await update_form(db, GUILD, form["name"], role_id=NO_ROLE) is True
    fresh = await get_form_by_id(db, form["id"])
    assert fresh["role_id"] is None and fresh["title"] == "Twitch Team"

    assert await update_form(db, GUILD, form["name"], role_id=99) is True
    assert role_of(await get_form_by_id(db, form["id"])) == 99


async def test_the_card_on_a_list_form_names_the_form_rather_than_a_role(db):
    form = await a_list_form(db)
    made = await create_application(
        db, GUILD, form["id"], MEMBER, answers_json([("Twitch handle", "ada")])
    )

    embed = render_card(form, await get_application(db, made))

    assert embed.description == f"<@{MEMBER}> applied for **Stream Team**"
    assert "<@&" not in embed.description


async def test_an_approval_on_a_list_form_says_they_are_on_the_list(db):
    form = await a_list_form(db)
    await update_form(db, GUILD, form["name"], expires_days=7, approved_text="You're on it.")
    form = await get_form_by_id(db, form["id"])
    made = await create_application(db, GUILD, form["id"], MEMBER, answers_json([]))
    await decide_application(db, made, APPROVED, decided_by=STAFF)
    row = await get_application(db, made)

    card, said = decision_lines(
        form, row, member_name="Ada", until="2099-01-01T00:00:00+00:00", granted=None
    )

    assert card == APPROVED_ON_RECORD.format(name="Ada", title="Stream Team")
    assert "runs out" not in card and "runs out" not in said
    assert "Discord refused" not in card
    assert "You're on it." in said


async def test_a_removed_member_is_told_why_and_when_they_may_apply_again(db):
    form = await a_list_form(db)
    await update_form(db, GUILD, form["name"], retry_days=30)
    form = await get_form_by_id(db, form["id"])
    made = await create_application(db, GUILD, form["id"], MEMBER, answers_json([]))
    await decide_application(db, made, APPROVED, decided_by=STAFF)

    assert await remove_application(db, made, decided_by=STAFF, reason="stopped streaming")

    row = await get_application(db, made)
    assert row["status"] == REMOVED and row["deny_reason"] == "stopped streaming"
    assert row["decided_by"] == STAFF and row["decided_at"]
    card, said = decision_lines(form, row, guild_name="Black in a Flash!")
    assert card == "Taken off the list, and they have been told why."
    assert "stopped streaming" in said and "<t:" in said
    assert (await last_decision(db, form["id"], MEMBER))["id"] == made
    assert await cooling_until(db, form, MEMBER) is not None


async def test_only_an_approved_application_can_be_taken_off_the_list(db):
    form = await a_list_form(db)
    made = await create_application(db, GUILD, form["id"], MEMBER, answers_json([]))

    assert await remove_application(db, made, decided_by=STAFF, reason="no") is False
    assert (await get_application(db, made))["status"] == PENDING

    await decide_application(db, made, DENIED, decided_by=STAFF, deny_reason="not this time")
    assert await remove_application(db, made, decided_by=STAFF, reason="no") is False
    assert (await get_application(db, made))["status"] == DENIED


async def test_taking_somebody_off_the_list_needs_a_line_they_are_sent(db):
    form = await a_list_form(db)
    made = await create_application(db, GUILD, form["id"], MEMBER, answers_json([]))
    await decide_application(db, made, APPROVED, decided_by=STAFF)

    with pytest.raises(ApplicationError) as caught:
        await remove_application(db, made, decided_by=STAFF, reason="   ")

    assert str(caught.value) == REMOVE_NEEDS_A_REASON
    assert (await get_application(db, made))["status"] == APPROVED


async def test_the_whole_roster_s_twitch_logins_come_back_in_one_query(db):
    for user_id, login in ((MEMBER, "ada"), (901, "bee")):
        await db.conn.execute(
            "INSERT INTO golive_links(user_id, twitch_login, twitch_user_id, linked_at) "
            "VALUES (?, ?, ?, 'then')",
            (user_id, login, str(user_id)),
        )
    await db.conn.commit()
    counted = []
    original = db.conn.execute

    async def counting(sql, *args, **kwargs):
        counted.append(sql)
        return await original(sql, *args, **kwargs)

    db.conn.execute = counting
    try:
        found = await twitch_logins_for(db, [MEMBER, 901, 902, MEMBER])
    finally:
        db.conn.execute = original

    assert found == {MEMBER: "ada", 901: "bee"}
    assert len(counted) == 1
    assert await twitch_logins_for(db, []) == {}



# The panel's data — the button table, the third writer, and the five line builders.


@pytest.mark.parametrize("status", list(STATUSES))
def test_every_button_the_table_offers_is_a_move_transitions_allows(status):
    """§C's table is DATA, and the data is checked against `TRANSITIONS`, never trusted."""
    offered = {MOVE_TARGETS[move.action] for move in CARD_BUTTONS[status]}
    assert offered <= set(TRANSITIONS[status]), (status, offered)
    missing = set(TRANSITIONS[status]) - offered
    assert missing <= {WITHDRAWN}, (status, missing)


def test_a_card_offers_nothing_to_somebody_who_may_not_decide_it():
    for status in STATUSES:
        assert card_buttons(status, may_decide=False) == ()


def test_an_approved_role_form_points_at_role_revoke_rather_than_a_take_off_button():
    assert card_buttons(APPROVED, has_role=True) == ()
    assert [one.label for one in card_buttons(APPROVED, has_role=False)] == [
        "Take off the list"
    ]


def test_a_withdrawn_application_is_the_members_and_has_no_staff_move():
    assert card_buttons(WITHDRAWN) == ()
    assert TRANSITIONS[WITHDRAWN] == ()


async def test_only_a_denied_or_removed_row_can_be_restored(db):
    form = await a_form(db)
    denied = await create_application(db, GUILD, form["id"], MEMBER, "[]")
    await decide_application(db, denied, DENIED, decided_by=STAFF, deny_reason="no")

    assert await restore_application(db, denied, decided_by=STAFF) is True
    fresh = await get_application(db, denied)
    assert fresh["status"] == APPROVED and fresh["deny_reason"] is None
    assert fresh["decided_by"] == STAFF

    assert await restore_application(db, denied, decided_by=STAFF) is False
    assert (await get_application(db, denied))["status"] == APPROVED


async def test_restoring_never_touches_a_pending_or_withdrawn_row(db):
    form = await a_form(db)
    waiting = await create_application(db, GUILD, form["id"], MEMBER, "[]")

    assert await restore_application(db, waiting, decided_by=STAFF) is False
    assert (await get_application(db, waiting))["status"] == PENDING

    await decide_application(db, waiting, WITHDRAWN, decided_by=MEMBER)
    assert await restore_application(db, waiting, decided_by=STAFF) is False
    assert (await get_application(db, waiting))["status"] == WITHDRAWN


def test_a_number_is_read_off_a_card_with_or_without_the_hash():
    assert application_id_from("#12") == 12
    assert application_id_from(" 12 ") == 12
    assert application_id_from("#  12") == 12
    for junk in ("", None, "twelve", "12a", "-3", "#"):
        assert application_id_from(junk) is None


def test_a_members_own_lines_name_the_form_and_why_it_was_refused():
    forms_by_id = {1: {"title": "Twitch Team"}}
    rows = [
        {"form_id": 1, "status": PENDING, "deny_reason": None},
        {"form_id": 1, "status": DENIED, "deny_reason": "not yet"},
        {"form_id": 2, "status": APPROVED, "deny_reason": None},
    ]

    lines = own_lines(rows, forms_by_id)

    assert lines[0] == "**Twitch Team** — pending, waiting on staff"
    assert lines[1] == "**Twitch Team** — denied — not yet"
    assert lines[2] == "**form #2** — approved"


def test_a_form_line_says_list_rather_than_a_role_that_is_not_there():
    lines = form_lines(
        [
            {"name": "twitch-team", "role_id": 4242, "open": 1},
            {"name": "stream-team", "role_id": None, "open": 0},
        ]
    )

    assert lines == [
        "**twitch-team** — open, <@&4242>",
        "**stream-team** — closed, list",
    ]
    assert "<@&None>" not in " ".join(lines)


def test_an_application_line_carries_a_twitch_login_only_for_an_approved_list_row():
    rows = [
        {"id": 7, "user_id": MEMBER, "form_id": 2, "status": APPROVED, "submitted_at": None},
        {"id": 8, "user_id": MEMBER, "form_id": 1, "status": APPROVED, "submitted_at": None},
    ]

    lines = application_lines(
        rows, {1: "twitch-team", 2: "stream-team"}, listed=(2,), logins={MEMBER: "ada"}
    )

    assert "twitch.tv/ada" in lines[0] and "stream-team" in lines[0]
    assert "twitch.tv" not in lines[1]


def test_question_lines_say_which_slots_are_filled_and_which_may_be_left_blank():
    lines = question_lines(
        [
            {"position": 1, "label": "Twitch handle", "style": "short", "required": 1},
            {"position": 2, "label": "Why", "style": "long", "required": 0},
        ]
    )

    assert lines == [
        "**1.** Twitch handle — short",
        "**2.** Why — long, optional",
    ]


def test_the_counts_line_counts_the_forms_the_queue_and_the_lists():
    rows = [
        {"status": PENDING},
        {"status": PENDING},
        {"status": APPROVED},
        {"status": REMOVED},
        {"status": "nonsense"},
    ]

    assert counts_of(rows)[PENDING] == 2
    assert counts_of(rows)[APPROVED] == 1
    assert counts_line([{}, {}], rows) == "**2** form(s) · **2** waiting · **1** on a list"


def test_the_own_list_key_is_on_by_default_and_reads_back_as_a_bool():
    class Store:
        def __init__(self, value):
            self.value = value

        def get(self, guild_id, key):
            assert key == PANEL_OWN_LIST_KEY
            return self.value

    assert panel_shows_own_list(Store(True), GUILD) is True
    assert panel_shows_own_list(Store(None), GUILD) is False


def test_the_site_link_needs_an_origin_and_points_at_the_role_menus_page():
    assert site_page_url("") is None
    assert site_page_url("https://blackbloc.heygabi.ai/") == (
        "https://blackbloc.heygabi.ai/rolemenus.html"
    )
