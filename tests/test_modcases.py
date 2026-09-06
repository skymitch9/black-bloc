
import pytest

from black_bloc.automod import TIMEOUT_MAX_SECONDS
from black_bloc.modcases import (
    ADD_NOTE_MOVE,
    BACK_MOVE,
    BAN_PURGE_MAX_DAYS,
    CARD_REFRESH_MOVE,
    CASES_PER_PAGE,
    EDIT_NOTE_MOVE,
    EDIT_REASON_MOVE,
    EVERYONE_MOVE,
    JUMP_MOVE,
    LINE_REASON_LIMIT,
    LOGS_MOVE,
    NEWER_MOVE,
    OLDER_MOVE,
    PANEL_MINUTES_KEY,
    PICK_CASE_MOVE,
    RESTORE_MOVE,
    ROOT_REFRESH_MOVE,
    SITE_MOVE,
    VOID_MOVE,
    WHOSE_MOVE,
    Voided,
    add_case,
    card_buttons,
    case_embed,
    case_is_void,
    case_line,
    case_status,
    cases_for,
    claim_case,
    clamp_purge_days,
    clamp_timeout,
    clear_case_void,
    count_cases,
    describe_duration,
    dm_member,
    dm_text,
    duration_error,
    get_case,
    mark_case_void,
    page_count,
    pages_under_limit,
    panel_minutes,
    parse_duration,
    refusal_in_test_mode,
    root_buttons,
    set_case_log_message,
    set_case_outcome,
    set_case_reason,
    voided_of,
    wanted_page,
    warn_count,
    write_case_note,
)

GUILD = 7
USER = 900
MOD = 1


class FakeUser:
    def __init__(self, raises=None):
        self.id = USER
        self.dms = []
        self.raises = raises

    async def send(self, content=None, **kwargs):
        if self.raises is not None:
            raise self.raises
        self.dms.append((content, kwargs))


def test_durations_are_read_the_way_the_incumbent_writes_them():
    assert parse_duration("10m") == 600
    assert parse_duration("2h") == 7200
    assert parse_duration("1d") == 86400
    assert parse_duration("1h30m") == 5400
    assert parse_duration("45s") == 45
    assert parse_duration("1w") == 604800
    assert parse_duration("30") == 1800
    assert parse_duration("") is None
    assert parse_duration("soon") is None
    assert parse_duration("0m") is None


def test_durations_read_back_the_way_a_person_would_say_them():
    assert describe_duration(300) == "5m"
    assert describe_duration(5400) == "1h 30m"
    assert describe_duration(0) == "no time at all"


def test_discords_own_ceilings_are_clamped_at_the_act_site():
    assert clamp_timeout(TIMEOUT_MAX_SECONDS + 999) == TIMEOUT_MAX_SECONDS
    assert clamp_timeout(-5) == 0
    assert clamp_purge_days(30) == BAN_PURGE_MAX_DAYS
    assert clamp_purge_days(-1) == 0
    assert clamp_purge_days(3) == 3


def test_the_dm_says_only_what_the_setting_allows():
    assert dm_text("none", "Black Bloc", "warn", "spam") is None
    plain = dm_text("server_action", "Black Bloc", "timeout", "spam")
    assert "timed out" in plain and "spam" not in plain
    full = dm_text("server_action_reason", "Black Bloc", "ban", "spam")
    assert "banned" in full and "spam" in full
    assert dm_text("server_action_reason", "Black Bloc", "ban", "  ") == dm_text(
        "server_action", "Black Bloc", "ban", None
    )
    assert dm_text("server_action", "Black Bloc", "purge") is None


async def test_a_closed_dm_is_never_an_error():
    assert await dm_member(FakeUser(), None) is False
    assert await dm_member(FakeUser(raises=RuntimeError("closed")), "hi") is False
    user = FakeUser()
    assert await dm_member(user, "hi") is True
    assert user.dms[0][1]["allowed_mentions"].everyone is False


def test_the_case_card_never_pings_and_says_when_nothing_was_done():
    embed = case_embed(
        case_id=3,
        kind="automod",
        user_id=USER,
        reason="5 mentions in 30s",
        duration_s=300,
        applied=False,
        mode="shadow",
        detail="mention_spam",
    )
    assert embed.title == "Case #3 — automod"
    names = [field.name for field in embed.fields]
    assert names == ["Member", "Moderator", "For", "What tripped it", "Reason", "Not done"]
    assert embed.fields[1].value == "Black Bloc"
    assert "shadow" in embed.fields[-1].value

    applied = case_embed(case_id=4, kind="ban", user_id=USER, moderator_id=MOD)
    assert [field.name for field in applied.fields] == ["Member", "Moderator"]
    assert applied.fields[1].value == f"<@{MOD}>"


async def test_cases_round_trip_and_count(db):
    first = await add_case(db, GUILD, USER, "warn", moderator_id=MOD, reason="spam")
    second = await add_case(
        db, GUILD, USER, "automod", reason="5 mentions in 30s", mode="shadow", applied=False
    )
    await set_case_log_message(db, first, 55)
    await set_case_log_message(db, None, 55)

    row = await get_case(db, first)
    assert row["kind"] == "warn" and row["applied"] == 1 and row["log_message_id"] == 55
    assert (await get_case(db, second))["applied"] == 0
    assert await count_cases(db, GUILD, USER) == 2
    assert [r["id"] for r in await cases_for(db, GUILD, USER, 10)] == [second, first]
    assert await warn_count(db, GUILD, USER) == 1

    await set_case_outcome(db, second, ["warn", "timeout"], [])
    assert await warn_count(db, GUILD, USER) == 2
    assert (await get_case(db, second))["applied"] == 1
    assert await count_cases(db, GUILD, USER + 1) == 0


async def test_only_one_click_ever_applies_a_case(db):
    case_id = await add_case(db, GUILD, USER, "automod", mode="shadow", applied=False)

    assert await claim_case(db, case_id) is True
    assert await claim_case(db, case_id) is False
    assert (await get_case(db, case_id))["applied"] == 1

    await set_case_outcome(db, case_id, [], ["timeout"])

    assert (await get_case(db, case_id))["applied"] == 0
    assert await claim_case(db, case_id) is True


async def test_a_case_can_belong_to_a_channel_rather_than_a_member(db):
    case_id = await add_case(db, GUILD, None, "purge", moderator_id=MOD, channel_id=555)

    row = await get_case(db, case_id)

    assert row["user_id"] is None and row["channel_id"] == 555
    assert await cases_for(db, GUILD, USER, 10) == []
    assert await count_cases(db, GUILD, USER) == 0
    assert case_embed(case_id=case_id, kind="purge", user_id=None, channel_id=555).fields[
        0
    ].value == "<#555>"


async def test_a_case_line_names_the_case_the_kind_and_whether_it_happened(db):
    case_id = await add_case(
        db, GUILD, USER, "automod", reason="5 mentions in 30s", mode="shadow", applied=False
    )

    line = case_line(await get_case(db, case_id))

    assert f"#{case_id}" in line and "automod" in line and "(not done)" in line
    assert "5 mentions in 30s" in line


async def test_a_long_reason_is_cut_and_a_long_list_is_split_into_messages(db):
    case_id = await add_case(db, GUILD, USER, "warn", moderator_id=MOD, reason="x" * 400)

    line = case_line(await get_case(db, case_id))

    assert len(line) < 200 and line.endswith("…")

    pages = pages_under_limit([f"**#{n}** `warn` " + "y" * 150 for n in range(40)])

    assert len(pages) > 1
    assert all(len(page) <= 1900 for page in pages)
    assert pages_under_limit([]) == [""]
    assert LINE_REASON_LIMIT == 120


def test_the_card_says_what_actually_happened_when_only_half_of_it_did():
    embed = case_embed(
        case_id=9,
        kind="automod",
        user_id=USER,
        reason="5 mentions in 30s",
        applied=True,
        done=["warn"],
        failed=["timeout"],
    )

    names = [field.name for field in embed.fields]
    assert "Done" in names and "Refused" in names and "Not done" not in names
    assert embed.fields[names.index("Done")].value == "warn"
    assert "timeout" in embed.fields[names.index("Refused")].value


def test_the_automod_dm_says_it_was_a_timeout_and_for_how_long():
    said = dm_text("server_action_reason", "Black Bloc", "automod_timeout", "spam", duration_s=300)

    assert "timed out by the automatic filter" in said and "5m" in said
    assert "warned by the automatic filter" in dm_text(
        "server_action", "Black Bloc", "automod", "spam"
    )


def test_the_refusals_are_sentences_not_status_codes():
    assert "test mode" in refusal_in_test_mode("time out")
    assert "time out" in refusal_in_test_mode("time out")
    assert "28 days" in duration_error("forever")
    assert "forever" in duration_error("forever")


# --- the /mod panel ------------------------------------------------------------------------------


class FakeStore:
    def __init__(self, minutes=10):
        self.minutes = minutes

    def get(self, guild_id, key):
        assert key == PANEL_MINUTES_KEY
        return self.minutes


async def a_case(db, **rest):
    return await add_case(db, GUILD, USER, rest.pop("kind", "warn"), moderator_id=MOD, **rest)


async def test_only_one_press_ever_voids_a_case_and_only_one_ever_restores_it(db):
    case_id = await a_case(db, reason="spam")

    assert case_is_void(await get_case(db, case_id)) is False
    assert await mark_case_void(db, case_id, MOD, "wrong member") is True
    assert await mark_case_void(db, case_id, MOD + 1, "again") is False

    row = await get_case(db, case_id)
    assert case_is_void(row) is True
    assert (row["voided_by"], row["void_reason"]) == (MOD, "wrong member")
    assert voided_of(row) == Voided(MOD, row["voided_at"], "wrong member")

    assert await clear_case_void(db, case_id) is True
    assert await clear_case_void(db, case_id) is False

    row = await get_case(db, case_id)
    assert case_is_void(row) is False
    assert voided_of(row) is None
    assert (row["voided_by"], row["void_reason"]) == (None, None)


async def test_a_voided_warn_stops_counting_toward_the_threshold(db):
    """F-M2 (a): a warn staff have said was wrong must not still say the member is at three."""
    first = await a_case(db, reason="spam")
    await a_case(db, reason="spam again")

    assert await warn_count(db, GUILD, USER) == 2

    await mark_case_void(db, first, MOD, "wrong member")

    assert await warn_count(db, GUILD, USER) == 1

    await clear_case_void(db, first)

    assert await warn_count(db, GUILD, USER) == 2


async def test_a_reason_and_a_note_are_written_where_the_card_reads_them(db):
    case_id = await a_case(db, reason="spam")

    await set_case_reason(db, case_id, "y" * (500 + 40))
    await write_case_note(db, case_id, "n" * (500 + 40), MOD)

    row = await get_case(db, case_id)
    assert len(row["reason"]) == 500 and len(row["note"]) == 500
    assert row["note_by"] == MOD and row["note_at"]

    await write_case_note(db, case_id, "they apologised", None)

    row = await get_case(db, case_id)
    assert row["note"] == "they apologised" and row["note_by"] is None


async def test_a_voided_line_is_struck_through_and_a_live_one_is_byte_identical(db):
    case_id = await a_case(db, reason="spam")
    row = await get_case(db, case_id)
    before = case_line(row)

    assert not before.startswith("~~")

    await mark_case_void(db, case_id, MOD, "wrong member")
    after = case_line(await get_case(db, case_id))

    assert after == f"~~{before}~~"


async def test_the_status_word_says_voided_before_it_says_anything_else(db):
    case_id = await a_case(db, reason="spam")
    shadow = await add_case(db, GUILD, USER, "automod", mode="shadow", applied=False)

    assert case_status(await get_case(db, case_id)) == "warn"
    assert case_status(await get_case(db, shadow)) == "not done"

    await mark_case_void(db, shadow, MOD, "wrong")

    assert case_status(await get_case(db, shadow)) == "voided"


def test_the_card_gains_a_note_and_a_voided_field_and_is_unchanged_without_them():
    plain = case_embed(case_id=4, kind="ban", user_id=USER, moderator_id=MOD)

    assert [field.name for field in plain.fields] == ["Member", "Moderator"]

    marked = case_embed(
        case_id=4,
        kind="ban",
        user_id=USER,
        moderator_id=MOD,
        note="they apologised",
        voided=Voided(MOD, "2026-09-05T00:00:00+00:00", "wrong member"),
    )
    names = [field.name for field in marked.fields]

    assert names == ["Member", "Moderator", "Note", "Voided"]
    said = marked.fields[names.index("Voided")].value
    assert f"<@{MOD}>" in said and "wrong member" in said
    assert "does not undo" in said and "<t:" in said
    assert marked.colour.value == 0x99AAB5 and plain.colour.value != 0x99AAB5


def test_a_voided_field_survives_a_stamp_it_cannot_read():
    said = case_embed(
        case_id=4, kind="ban", user_id=USER, voided=Voided(None, "not a date", None)
    ).fields[-1].value

    assert "Black Bloc" in said and "<t:" not in said


async def test_the_card_row_never_offers_void_and_restore_at_once(db):
    case_id = await a_case(db, reason="spam")
    row = await get_case(db, case_id)

    assert card_buttons(row) == (
        EDIT_REASON_MOVE, ADD_NOTE_MOVE, VOID_MOVE, BACK_MOVE, CARD_REFRESH_MOVE
    )

    await write_case_note(db, case_id, "they apologised", MOD)
    row = await get_case(db, case_id)

    assert card_buttons(row) == (
        EDIT_REASON_MOVE, EDIT_NOTE_MOVE, VOID_MOVE, BACK_MOVE, CARD_REFRESH_MOVE
    )
    assert ADD_NOTE_MOVE not in card_buttons(row)

    await mark_case_void(db, case_id, MOD, "wrong")
    row = await get_case(db, case_id)

    assert card_buttons(row) == (
        RESTORE_MOVE, EDIT_REASON_MOVE, EDIT_NOTE_MOVE, BACK_MOVE, CARD_REFRESH_MOVE
    )
    assert VOID_MOVE not in card_buttons(row)
    assert len(card_buttons(row)) == 5


@pytest.mark.parametrize(
    ("has_rows", "page", "pages", "filtered", "has_site", "wanted"),
    [
        (False, 1, 1, False, False, (WHOSE_MOVE, JUMP_MOVE, ROOT_REFRESH_MOVE, LOGS_MOVE)),
        (
            True, 1, 1, False, True,
            (PICK_CASE_MOVE, WHOSE_MOVE, JUMP_MOVE, ROOT_REFRESH_MOVE, LOGS_MOVE, SITE_MOVE),
        ),
        (
            True, 1, 3, False, False,
            (PICK_CASE_MOVE, WHOSE_MOVE, OLDER_MOVE, JUMP_MOVE, ROOT_REFRESH_MOVE, LOGS_MOVE),
        ),
        (
            True, 3, 3, False, False,
            (PICK_CASE_MOVE, WHOSE_MOVE, NEWER_MOVE, JUMP_MOVE, ROOT_REFRESH_MOVE, LOGS_MOVE),
        ),
        (
            True, 2, 3, True, False,
            (
                PICK_CASE_MOVE, WHOSE_MOVE, NEWER_MOVE, OLDER_MOVE, EVERYONE_MOVE, JUMP_MOVE,
                ROOT_REFRESH_MOVE, LOGS_MOVE,
            ),
        ),
        (
            False, 1, 1, True, False,
            (WHOSE_MOVE, EVERYONE_MOVE, JUMP_MOVE, ROOT_REFRESH_MOVE, LOGS_MOVE),
        ),
    ],
)
def test_the_root_renders_only_the_moves_its_state_allows(
    has_rows, page, pages, filtered, has_site, wanted
):
    found = root_buttons(
        has_rows=has_rows, page=page, pages=pages, filtered=filtered, has_site=has_site
    )

    assert found == wanted
    assert len([move for move in found if move.row == 2]) <= 5


def test_a_page_is_the_same_ten_the_website_already_pages_by():
    assert CASES_PER_PAGE == 10
    assert page_count(0) == 1 and page_count(10) == 1 and page_count(11) == 2
    assert wanted_page(0, 3) == 1 and wanted_page(9, 3) == 3 and wanted_page("x", 3) == 1
    assert wanted_page(2, 3) == 2


def test_the_panel_reads_its_minutes_from_the_settings_key():
    assert PANEL_MINUTES_KEY == "mod_panel_minutes"
    assert panel_minutes(FakeStore(25), GUILD) == 25
