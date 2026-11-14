from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from black_bloc import timed_roles_by_hand as hand

GUILD = 7


def guild(entries, *, readable=True, me_id=1):
    perms = SimpleNamespace(view_audit_log=readable)

    def audit_logs(limit=1, action=None):
        async def walk():
            for one in entries:
                yield one

        return walk()

    return SimpleNamespace(
        id=GUILD, me=SimpleNamespace(id=me_id, guild_permissions=perms), audit_logs=audit_logs
    )


def entry(target_id, user_id, role_ids, *, ago=1):
    return SimpleNamespace(
        target=SimpleNamespace(id=target_id),
        user=SimpleNamespace(id=user_id),
        created_at=datetime.now(UTC) - timedelta(minutes=ago),
        after=SimpleNamespace(roles=[SimpleNamespace(id=one) for one in role_ids]),
    )


MEMBER = SimpleNamespace(id=900)


async def test_the_audit_entry_that_added_these_roles_recently_names_who():
    found = guild([entry(901, 55, [10]), entry(900, 56, [12]), entry(900, 57, [10, 11])])

    assert await hand.who_added(found, MEMBER, [10]) == (57, hand.FOUND)


async def test_an_old_entry_another_role_or_no_permission_names_nobody():
    assert await hand.who_added(guild([entry(900, 57, [10], ago=30)]), MEMBER, [10]) == (
        None,
        hand.SILENT,
    )
    assert await hand.who_added(guild([entry(900, 57, [11])]), MEMBER, [10]) == (
        None,
        hand.SILENT,
    )
    unreadable = guild([entry(900, 57, [10])], readable=False)
    assert await hand.who_added(unreadable, MEMBER, [10]) == (None, hand.UNREADABLE)


async def test_black_blocs_own_add_is_told_apart():
    assert await hand.who_added(guild([entry(900, 1, [10])]), MEMBER, [10]) == (None, hand.OURS)


async def test_a_post_is_waited_on_until_attached_and_attached_once(db):
    prompt_id = await hand.add_prompt(db, GUILD, 900, [11, 10], 55, hand.FOUND)

    assert await hand.waiting_roles(db, GUILD, 900) == {10, 11}
    assert hand.role_ids_of(await hand.get_prompt(db, prompt_id)) == [10, 11]
    assert await hand.mark_attached(db, prompt_id, 3, 1) is True
    assert await hand.mark_attached(db, prompt_id, 4, 1) is False
    assert await hand.waiting_roles(db, GUILD, 900) == set()
    assert (await hand.get_prompt(db, prompt_id))["attached_menu_id"] == 3


def test_the_custom_ids_round_trip_through_their_templates():
    import re

    assert re.fullmatch(hand.PICK_TEMPLATE, hand.pick_id(42))["prompt_id"] == "42"
    assert re.fullmatch(hand.NEW_TEMPLATE, hand.new_id(42))["prompt_id"] == "42"


async def test_an_entry_discord_writes_late_is_found_by_one_read_after_a_short_wait(monkeypatch):
    entries: list = []
    found = guild(entries)
    waited: list = []

    async def wait(seconds):
        waited.append(seconds)
        entries.append(entry(900, 57, [10]))

    monkeypatch.setattr(hand.asyncio, "sleep", wait)

    assert await hand.who_added_soon(found, MEMBER, [10]) == (57, hand.FOUND)
    assert waited == [hand.AUDIT_RETRY_SECONDS]


async def test_the_second_read_happens_only_when_the_first_found_nothing(monkeypatch):
    waited: list = []

    async def wait(seconds):
        waited.append(seconds)

    monkeypatch.setattr(hand.asyncio, "sleep", wait)

    assert await hand.who_added_soon(guild([entry(900, 57, [10])]), MEMBER, [10]) == (
        57,
        hand.FOUND,
    )
    assert await hand.who_added_soon(guild([], readable=False), MEMBER, [10]) == (
        None,
        hand.UNREADABLE,
    )
    assert await hand.who_added_soon(guild([]), MEMBER, [10]) == (None, hand.SILENT)
    assert waited == [hand.AUDIT_RETRY_SECONDS]
