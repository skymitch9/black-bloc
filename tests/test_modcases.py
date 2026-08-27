
import pytest

from black_bloc.automod import TIMEOUT_MAX_SECONDS
from black_bloc.modcases import (
    BAN_PURGE_MAX_DAYS,
    LINE_REASON_LIMIT,
    add_case,
    case_embed,
    case_line,
    cases_for,
    claim_case,
    clamp_purge_days,
    clamp_timeout,
    count_cases,
    describe_duration,
    dm_member,
    dm_text,
    duration_error,
    get_case,
    pages_under_limit,
    parse_duration,
    refusal_in_test_mode,
    set_case_log_message,
    set_case_outcome,
    warn_count,
)
from black_bloc.storage.db import Database

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


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "m.sqlite3")
    await database.connect()
    try:
        yield database
    finally:
        await database.close()


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
