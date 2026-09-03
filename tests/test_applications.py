import json

import pytest

from black_bloc.applications import (
    APPROVED,
    APPROVED_ON_RECORD,
    DENIED,
    LABEL_MAX,
    LONG,
    NO_ROLE,
    PENDING,
    PLACEHOLDER_MAX,
    QUESTIONS_MAX,
    REMOVE_NEEDS_A_REASON,
    REMOVED,
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
    applications_for,
    check_name,
    check_title,
    cooling_until,
    create_application,
    create_form,
    decide_application,
    decision_lines,
    delete_form,
    edit_question,
    expires_days_of,
    get_application,
    get_form,
    get_form_by_id,
    is_open,
    last_decision,
    list_forms,
    may_move,
    owner_nudge,
    pending_count,
    questions_for,
    read_answers,
    remove_application,
    remove_question,
    render_card,
    replace_questions,
    retry_days_of,
    role_of,
    set_card,
    set_grant,
    set_panel,
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
    assert all(TRANSITIONS[one] == () for one in (DENIED, WITHDRAWN, REMOVED))
    assert set(STATUSES) == {PENDING, APPROVED, DENIED, WITHDRAWN, REMOVED}
    assert may_move(PENDING, APPROVED) is True
    assert may_move(APPROVED, DENIED) is False
    assert may_move(None, APPROVED) is False


def test_an_approved_application_may_only_move_to_removed():
    assert TRANSITIONS[APPROVED] == (REMOVED,)
    assert may_move(APPROVED, REMOVED) is True
    assert may_move(PENDING, REMOVED) is False
    assert may_move(REMOVED, APPROVED) is False
    assert set(SETTLED) == {APPROVED, DENIED, WITHDRAWN, REMOVED}


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
