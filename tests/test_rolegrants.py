from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from black_bloc.rolegrants import (
    ADDED,
    APPROVAL,
    APPROVED,
    BY_HAND,
    DENIED,
    EXPIRED,
    MENU,
    PENDING,
    REMOVED,
    WITHDRAWN,
    add_grant,
    create_request,
    decide_request,
    due_grants,
    end_grant,
    expires_at,
    extend_grant,
    forget_change,
    get_grant,
    get_request,
    grants_for,
    last_denial,
    open_grant,
    open_grants,
    open_request,
    open_requests,
    pushed_back,
    record_added,
    record_removed,
    remember_change,
    requests_by_status,
    retry_at,
    set_request_card,
    stamp,
    still_cooling,
    was_ours,
)

GUILD = 7
MENU_ID = 3
MEMBER = 900
ROLE = 10


async def test_a_request_is_open_once_and_the_second_one_is_refused(db):
    request_id = await create_request(db, GUILD, MENU_ID, MEMBER, ROLE)

    assert request_id is not None
    assert await create_request(db, GUILD, MENU_ID, MEMBER, ROLE) is None

    row = await open_request(db, MENU_ID, MEMBER, ROLE)
    assert row["id"] == request_id and row["status"] == PENDING
    assert [r["id"] for r in await open_requests(db, GUILD)] == [request_id]


async def test_a_settled_request_lets_the_member_ask_again(db):
    first = await create_request(db, GUILD, MENU_ID, MEMBER, ROLE)
    await decide_request(db, first, DENIED, decided_by=1, deny_reason="not yet")

    second = await create_request(db, GUILD, MENU_ID, MEMBER, ROLE)

    assert second is not None and second != first
    assert await open_request(db, MENU_ID, MEMBER, ROLE) is not None
    denial = await last_denial(db, MENU_ID, MEMBER, ROLE)
    assert denial["id"] == first and denial["deny_reason"] == "not yet"


async def test_only_the_first_decision_lands(db):
    request_id = await create_request(db, GUILD, MENU_ID, MEMBER, ROLE)

    assert await decide_request(db, request_id, APPROVED, decided_by=1) is True
    assert await decide_request(db, request_id, DENIED, decided_by=2, deny_reason="no") is False

    row = await get_request(db, request_id)
    assert row["status"] == APPROVED and row["decided_by"] == 1
    assert row["deny_reason"] is None and row["decided_at"] is not None


async def test_the_queue_puts_pending_first_then_the_newest(db):
    old = await create_request(db, GUILD, MENU_ID, MEMBER, ROLE)
    await decide_request(db, old, WITHDRAWN)
    newer = await create_request(db, GUILD, MENU_ID, MEMBER, ROLE)
    other = await create_request(db, GUILD, MENU_ID, MEMBER + 1, ROLE)

    rows = await requests_by_status(db, GUILD)

    assert [row["id"] for row in rows] == [other, newer, old]
    assert [row["id"] for row in await requests_by_status(db, GUILD, (WITHDRAWN,))] == [old]


async def test_a_card_is_remembered_so_it_can_be_edited_later(db):
    request_id = await create_request(db, GUILD, MENU_ID, MEMBER, ROLE)

    await set_request_card(db, request_id, 500, 600)

    row = await get_request(db, request_id)
    assert (row["channel_id"], row["message_id"]) == (500, 600)


async def test_a_grant_is_open_until_it_is_ended(db):
    grant_id = await add_grant(db, GUILD, MEMBER, ROLE, APPROVAL, granted_by=1, until=None)

    assert (await open_grant(db, GUILD, MEMBER, ROLE))["id"] == grant_id
    assert await end_grant(db, grant_id, EXPIRED) is True
    assert await end_grant(db, grant_id, BY_HAND) is False
    assert await open_grant(db, GUILD, MEMBER, ROLE) is None

    row = await get_grant(db, grant_id)
    assert row["removed_reason"] == EXPIRED and row["removed_at"] is not None


async def test_a_bad_source_is_refused_before_anything_is_written(db):
    with pytest.raises(ValueError, match="source must be"):
        await add_grant(db, GUILD, MEMBER, ROLE, "whenever")
    assert await open_grants(db, GUILD) == []


async def test_only_grants_that_are_due_and_still_open_come_back(db):
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    ahead = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    due = await add_grant(db, GUILD, MEMBER, ROLE, MENU, until=past)
    await add_grant(db, GUILD, MEMBER, ROLE + 1, MENU, until=ahead)
    await add_grant(db, GUILD, MEMBER, ROLE + 2, MENU, until=None)
    closed = await add_grant(db, GUILD, MEMBER, ROLE + 3, MENU, until=past)
    await end_grant(db, closed, BY_HAND)

    rows = await due_grants(db, datetime.now(UTC).isoformat())

    assert [row["id"] for row in rows] == [due]


async def test_extending_only_moves_an_open_grant(db):
    ahead = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    grant_id = await add_grant(db, GUILD, MEMBER, ROLE, MENU, until=ahead)
    later = (datetime.now(UTC) + timedelta(days=9)).isoformat()

    assert await extend_grant(db, grant_id, later) is True
    assert (await get_grant(db, grant_id))["expires_at"] == later

    await end_grant(db, grant_id, EXPIRED)
    assert await extend_grant(db, grant_id, later) is False


async def test_grants_for_puts_the_open_ones_first_and_filters(db):
    closed = await add_grant(db, GUILD, MEMBER, ROLE, MENU)
    await end_grant(db, closed, EXPIRED)
    live = await add_grant(db, GUILD, MEMBER, ROLE, APPROVAL)
    elsewhere = await add_grant(db, GUILD, MEMBER + 1, ROLE + 1, MENU)

    assert [r["id"] for r in await grants_for(db, GUILD)] == [elsewhere, live, closed]
    assert [r["id"] for r in await grants_for(db, GUILD, user_id=MEMBER)] == [live, closed]
    assert [r["id"] for r in await grants_for(db, GUILD, role_id=ROLE + 1)] == [elsewhere]


async def test_recording_a_second_add_leaves_the_first_grant_standing(db):
    await record_added(db, GUILD, MEMBER, [ROLE], MENU, until=None)
    first = await open_grant(db, GUILD, MEMBER, ROLE)

    await record_added(db, GUILD, MEMBER, [ROLE], APPROVAL, until="2027-01-01T00:00:00+00:00")

    assert (await open_grant(db, GUILD, MEMBER, ROLE))["id"] == first["id"]
    assert len(await grants_for(db, GUILD, user_id=MEMBER)) == 1


async def test_recording_a_removal_closes_the_open_grant_and_ignores_the_rest(db):
    await record_added(db, GUILD, MEMBER, [ROLE], MENU)

    await record_removed(db, GUILD, MEMBER, [ROLE, ROLE + 5], BY_HAND)

    assert await open_grants(db, GUILD) == []
    assert (await grants_for(db, GUILD))[0]["removed_reason"] == BY_HAND


def test_expires_at_reads_days_and_refuses_nonsense():
    at = datetime(2026, 1, 1, tzinfo=UTC)
    assert expires_at(7, at=at) == datetime(2026, 1, 8, tzinfo=UTC).isoformat()
    assert expires_at(None) is None
    assert expires_at(0) is None
    assert expires_at(-3) is None
    assert expires_at("nope") is None


def test_extending_starts_from_the_later_of_now_and_the_end_it_had():
    now = datetime(2026, 1, 10, tzinfo=UTC)
    ahead = datetime(2026, 1, 20, tzinfo=UTC).isoformat()
    behind = datetime(2026, 1, 2, tzinfo=UTC).isoformat()

    assert pushed_back(ahead, 5, at=now) == datetime(2026, 1, 25, tzinfo=UTC).isoformat()
    assert pushed_back(behind, 5, at=now) == datetime(2026, 1, 15, tzinfo=UTC).isoformat()
    assert pushed_back(None, 5, at=now) == datetime(2026, 1, 15, tzinfo=UTC).isoformat()


def test_the_retry_stamp_is_the_denial_plus_the_menus_days():
    denied = datetime(2026, 1, 1, tzinfo=UTC)
    assert retry_at(denied.isoformat(), 7) == datetime(2026, 1, 8, tzinfo=UTC)
    assert retry_at("not a date", 7) is None
    assert retry_at(denied.isoformat(), 0) is None
    assert retry_at(denied.isoformat(), "seven") == datetime(2026, 1, 8, tzinfo=UTC)


def test_the_cooldown_only_bites_before_the_retry_moment():
    denied = datetime(2026, 1, 1, tzinfo=UTC).isoformat()

    assert still_cooling(denied, 7, at=datetime(2026, 1, 5, tzinfo=UTC)) is not None
    assert still_cooling(denied, 7, at=datetime(2026, 1, 9, tzinfo=UTC)) is None
    assert still_cooling(denied, 0, at=datetime(2026, 1, 1, tzinfo=UTC)) is None


def test_a_stamp_is_a_discord_timestamp_and_says_so_when_it_cannot_be_read():
    when = datetime(2026, 1, 1, tzinfo=UTC)
    assert stamp(when) == f"<t:{int(when.timestamp())}:F>"
    assert stamp(when.isoformat(), "R").endswith(":R>")
    assert stamp("half past") == "at an unreadable time"


def test_the_ledger_answers_once_and_only_for_what_the_bot_did():
    bot = SimpleNamespace()
    remember_change(bot, GUILD, MEMBER, [ROLE, ROLE + 1], ADDED)

    assert was_ours(bot, GUILD, MEMBER, ROLE, ADDED) is True
    assert was_ours(bot, GUILD, MEMBER, ROLE, ADDED) is False
    assert was_ours(bot, GUILD, MEMBER, ROLE + 1, REMOVED) is False
    assert was_ours(bot, GUILD, MEMBER + 1, ROLE + 1, ADDED) is False
    assert was_ours(bot, GUILD, MEMBER, ROLE + 1, ADDED) is True


def test_a_refused_edit_takes_its_entries_back_out_of_the_ledger():
    bot = SimpleNamespace()
    remember_change(bot, GUILD, MEMBER, [ROLE], ADDED)

    forget_change(bot, GUILD, MEMBER, [ROLE], ADDED)

    assert was_ours(bot, GUILD, MEMBER, ROLE, ADDED) is False


def test_a_stale_ledger_entry_stops_counting(monkeypatch):
    import black_bloc.rolegrants as rolegrants

    clock = {"now": 1000.0}
    monkeypatch.setattr(rolegrants.time, "monotonic", lambda: clock["now"])
    bot = SimpleNamespace()
    remember_change(bot, GUILD, MEMBER, [ROLE], ADDED)

    clock["now"] += rolegrants.LEDGER_SECONDS + 1

    assert was_ours(bot, GUILD, MEMBER, ROLE, ADDED) is False
    assert getattr(bot, rolegrants.LEDGER_ATTR) == {}
